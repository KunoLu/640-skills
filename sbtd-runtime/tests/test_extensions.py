"""R1.2b extension value normalization.

Scenario text lives in spec/r1.2b-host-adapter-scenarios.md. This repository
does not create .feature files. The consumer seam is normalize_extensions.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contract_eval import validate_events  # noqa: F401  (schema seam reuse)
from extensions import MAX_EXTENSION_KEYS, normalize_extensions


class NormalizeExtensionsTests(unittest.TestCase):
    def test_scalars_are_kept(self) -> None:
        extensions, drops = normalize_extensions(
            {"s": "text", "n": 3, "f": 1.5, "b": True, "z": None}
        )
        self.assertEqual(
            extensions, {"s": "text", "n": 3, "f": 1.5, "b": True, "z": None}
        )
        self.assertEqual(drops, [])

    def test_bool_is_not_treated_as_number(self) -> None:
        extensions, _drops = normalize_extensions({"flag": False})
        self.assertIs(extensions["flag"], False)

    def test_nested_objects_flatten_with_dot_keys(self) -> None:
        extensions, drops = normalize_extensions(
            {"args": {"count": 3, "ok": True}, "top": "x"}
        )
        self.assertEqual(extensions, {"args.count": 3, "args.ok": True, "top": "x"})
        self.assertEqual(drops, [])

    def test_deep_nesting_flattens_to_full_path(self) -> None:
        extensions, _drops = normalize_extensions({"a": {"b": {"c": 1}}})
        self.assertEqual(extensions, {"a.b.c": 1})

    def test_arrays_are_dropped_not_flattened(self) -> None:
        extensions, drops = normalize_extensions({"items": [1, 2], "keep": 1})
        self.assertEqual(extensions, {"keep": 1})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("items", "dropped-array")],
        )

    def test_long_strings_are_dropped_not_truncated(self) -> None:
        extensions, drops = normalize_extensions({"blob": "x" * 257, "keep": "y"})
        self.assertEqual(extensions, {"keep": "y"})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("blob", "dropped-too-long")],
        )

    def test_string_at_limit_is_kept(self) -> None:
        extensions, drops = normalize_extensions({"exact": "x" * 256})
        self.assertEqual(extensions["exact"], "x" * 256)
        self.assertEqual(drops, [])

    def test_non_finite_numbers_are_dropped(self) -> None:
        extensions, drops = normalize_extensions(
            {"nan": math.nan, "inf": math.inf, "keep": 2}
        )
        self.assertEqual(extensions, {"keep": 2})
        self.assertEqual(
            sorted((drop.key, drop.reason) for drop in drops),
            [("inf", "dropped-non-finite"), ("nan", "dropped-non-finite")],
        )

    def test_secret_keys_are_dropped_before_storage(self) -> None:
        extensions, drops = normalize_extensions(
            {
                "apiKey": "x",
                "x-api-key": "y",
                "authToken": "z",
                "client_secret": "s",
                "cookies": "c",
                "token_count": 5,
                "input_tokens": 7,
            }
        )
        self.assertEqual(extensions, {"token_count": 5, "input_tokens": 7})
        self.assertEqual(
            sorted(drop.key for drop in drops),
            ["apiKey", "authToken", "client_secret", "cookies", "x-api-key"],
        )
        self.assertTrue(all(drop.reason == "dropped-secret" for drop in drops))

    def test_nested_secret_key_is_dropped(self) -> None:
        extensions, drops = normalize_extensions({"headers": {"Authorization": "v"}})
        self.assertEqual(extensions, {})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("headers.Authorization", "dropped-secret")],
        )

    def test_flatten_first_then_dot_separated_secret_match(self) -> None:
        # Researchy addendum: flatten nested extensions first; "." counts as a
        # word separator, so a.github_token after flatten is a secret key.
        extensions, drops = normalize_extensions(
            {"a": {"github_token": "x"}, "a.b": {"clientSecret": "y"}, "keep": 1}
        )
        self.assertEqual(extensions, {"keep": 1})
        self.assertEqual(
            sorted((drop.key, drop.reason) for drop in drops),
            [
                ("a.b.clientSecret", "dropped-secret"),
                ("a.github_token", "dropped-secret"),
            ],
        )

    def test_overlong_string_drops_field_not_event(self) -> None:
        # Researchy addendum: >256-char strings drop only their field; the
        # rest of the event payload survives normalization.
        extensions, drops = normalize_extensions(
            {"blob": "x" * 300, "exit_code": 0}
        )
        self.assertEqual(extensions, {"exit_code": 0})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("blob", "dropped-too-long")],
        )

    def test_over_limit_drops_by_priority_then_alphabetical(self) -> None:
        raw = {f"k{i}": i for i in range(10)}
        extensions, drops = normalize_extensions(raw, priority=("k7", "k3"))
        self.assertEqual(len(extensions), MAX_EXTENSION_KEYS)
        self.assertEqual(
            list(extensions),
            ["k7", "k3", "k0", "k1", "k2", "k4", "k5", "k6"],
        )
        self.assertEqual(
            sorted((drop.key, drop.reason) for drop in drops),
            [("k8", "dropped-over-limit"), ("k9", "dropped-over-limit")],
        )

    def test_exactly_at_limit_keeps_everything(self) -> None:
        raw = {f"k{i}": i for i in range(MAX_EXTENSION_KEYS)}
        extensions, drops = normalize_extensions(raw)
        self.assertEqual(len(extensions), MAX_EXTENSION_KEYS)
        self.assertEqual(drops, [])

    def test_none_and_empty_input(self) -> None:
        self.assertEqual(normalize_extensions(None), ({}, []))
        self.assertEqual(normalize_extensions({}), ({}, []))

    def test_unknown_scalar_like_values_are_dropped(self) -> None:
        extensions, drops = normalize_extensions({"when": object(), "keep": 1})
        self.assertEqual(extensions, {"keep": 1})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("when", "dropped-unsupported")],
        )

    def test_flatten_collision_keeps_first_and_reports(self) -> None:
        extensions, drops = normalize_extensions({"a.b": 1, "a": {"b": 2}, "keep": 3})
        self.assertEqual(extensions, {"a.b": 1, "keep": 3})
        self.assertEqual(
            [(drop.key, drop.reason) for drop in drops],
            [("a.b", "dropped-collision")],
        )

    def test_extreme_nesting_is_dropped_not_recursed(self) -> None:
        raw: dict = {}
        node = raw
        for index in range(40):
            node["k"] = {}
            node = node["k"]
        node["v"] = 1
        extensions, drops = normalize_extensions(raw)
        self.assertEqual(extensions, {})
        self.assertTrue(
            any(drop.reason == "dropped-unsupported" for drop in drops),
            drops,
        )


if __name__ == "__main__":
    unittest.main()
