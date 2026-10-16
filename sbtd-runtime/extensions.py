"""Scalar-only extension normalization for host adapters (R1.2b).

The authoritative contract is contracts/event.schema.json: extensions allow at
most 8 keys and scalar values only (string <= 256 chars, number, boolean,
null). Host data rarely arrives in that shape, so adapters normalize before
building events. Every dropped key is reported with a reason so the ingest
receipt can name what was lost:

- nested objects flatten to dot-joined keys ("a.b"), in document order;
- nesting deeper than 32 levels drops the subtree as "dropped-unsupported";
- arrays drop as "dropped-array" (index keys are unstable and eat the key
  budget);
- strings over 256 chars drop as "dropped-too-long" (never truncated: a half
  string reads as a complete value);
- non-finite numbers drop as "dropped-non-finite";
- other non-scalar values drop as "dropped-unsupported";
- two sources flattening to the same key keep the first value; the later one
  drops as "dropped-collision";
- keys matching the #132 secret matcher drop as "dropped-secret" (the event
  store still rejects whole events with secret keys as a second layer);
- beyond MAX_EXTENSION_KEYS, keys are kept in declared priority order first,
  then alphabetically; the tail drops as "dropped-over-limit".
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from event_store import _secret_key

MAX_EXTENSION_KEYS = 8
MAX_STRING = 256
_MAX_DEPTH = 32


@dataclass(frozen=True)
class Drop:
    key: str
    reason: str


def _flatten(raw: Mapping[str, Any]) -> tuple[list[tuple[str, Any]], list[Drop]]:
    """Flatten nested mappings to dot keys in document order."""
    flat: list[tuple[str, Any]] = []
    drops: list[Drop] = []
    pending: deque[tuple[str, Any, int]] = deque(
        (str(key), value, 0) for key, value in raw.items()
    )
    while pending:
        key, value, depth = pending.popleft()
        if isinstance(value, Mapping):
            if depth >= _MAX_DEPTH:
                drops.append(Drop(key, "dropped-unsupported"))
                continue
            for child_key, child in value.items():
                pending.append((f"{key}.{child_key}", child, depth + 1))
            continue
        flat.append((key, value))
    return flat, drops


def _scalar(key: str, value: Any) -> Drop | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        if len(value) <= MAX_STRING:
            return None
        return Drop(key, "dropped-too-long")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return Drop(key, "dropped-non-finite")
        return None
    if isinstance(value, (list, tuple)):
        return Drop(key, "dropped-array")
    return Drop(key, "dropped-unsupported")


def normalize_extensions(
    raw: Mapping[str, Any] | None,
    priority: Iterable[str] = (),
) -> tuple[dict[str, Any], list[Drop]]:
    """Normalize host extension data to the scalar-only, 8-key contract."""
    if not raw:
        return {}, []
    flat, drops = _flatten(raw)
    kept: dict[str, Any] = {}
    for key, value in flat:
        if _secret_key(key):
            drops.append(Drop(key, "dropped-secret"))
            continue
        drop = _scalar(key, value)
        if drop is not None:
            drops.append(drop)
            continue
        if key in kept:
            drops.append(Drop(key, "dropped-collision"))
            continue
        kept[key] = value
    if len(kept) <= MAX_EXTENSION_KEYS:
        return kept, drops
    rank: dict[str, int] = {}
    order = list(dict.fromkeys(priority))
    for index, key in enumerate(order):
        if key in kept:
            rank[key] = index
    ordered = sorted(
        kept,
        key=lambda key: (
            rank.get(key, len(order)),
            key if key not in rank else "",
        ),
    )
    result: dict[str, Any] = {}
    for key in ordered:
        if len(result) >= MAX_EXTENSION_KEYS:
            drops.append(Drop(key, "dropped-over-limit"))
            continue
        result[key] = kept[key]
    return result, drops
