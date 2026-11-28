"""Compare isolated Codex/OMP check and plan captures at the same fixture paths.

Usage: python tests/compare_rc3_host_captures.py CAPTURE_DIR RC2_BASELINE RC3_BASELINE
Supply baseline IDs from each package's inventory, not from the captures under test.
No host is invoked. No paths, timestamps, advice, or arbitrary JSON fields are masked.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path


def compare(directory: Path, host: str, action: str, baselines: tuple[str, str]) -> None:
    old, new = (
        json.loads((directory / f"{version}-{host}-{action}.json").read_bytes())
        for version in ("rc2", "rc3")
    )
    # §7: the optional Graft tool and its wiring plan disappear. The replacement
    # report is additive and must not claim any targets in this empty fixture.
    tool = old.pop("graft")
    old.pop("graftWiring")
    if action == "check":
        if old["tools"].count(tool) != 1 or tool["name"] != "graft":
            raise ValueError("unexpected rc.2 tool inventory")
        old["tools"].remove(tool)
    retirement = new.pop("graftRetirement")
    if retirement["blocked"] or retirement["items"] or retirement["targetsToRetire"]:
        raise ValueError("empty fixture yielded a retirement target or blocker")
    for capture, expected in zip((old, new), baselines, strict=True):
        # Content alignment hashes package bytes, including the removed runtime.
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", expected):
            raise ValueError("invalid independently supplied inventory baseline")
        if capture["contentAlignment"].pop("baseline") != expected:
            raise ValueError("capture does not identify its own package inventory")
    # Dict equality loses output order and treats JSON true as equal to 1.
    before, after = (json.dumps(obj, ensure_ascii=False, indent=2) for obj in (old, new))
    if before != after:
        raise ValueError("\n".join(difflib.unified_diff(
            before.splitlines(), after.splitlines(), "rc.2", "rc.3", lineterm="",
        )))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("rc2_baseline")
    parser.add_argument("rc3_baseline")
    args = parser.parse_args()
    for host in ("codex", "omp"):
        for action in ("check", "plan"):
            compare(args.captures, host, action, (args.rc2_baseline, args.rc3_baseline))
            print(f"{host} {action}: matched")
