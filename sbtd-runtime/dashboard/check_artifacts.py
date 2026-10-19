"""Check committed dashboard artifacts against the ADR 0002 size budget.

Usage: python3 sbtd-runtime/dashboard/check_artifacts.py
Exit code 0 when every check passes; 1 with a per-violation message.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


def main() -> int:
    budget = json.loads((HERE / "artifact-budget.json").read_text(encoding="utf-8"))
    budgets = budget["budgets"]
    failures: list[str] = []

    if not STATIC.is_dir():
        failures.append(f"missing committed artifacts directory: {STATIC}")
    else:
        files = [p for p in STATIC.rglob("*") if p.is_file()]
        if not files:
            failures.append("static/ contains no files")
        total = sum(p.stat().st_size for p in files)
        if total > budgets["static_total_bytes"]:
            failures.append(
                f"static total {total} bytes exceeds budget "
                f"{budgets['static_total_bytes']}"
            )
        for path in files:
            size = path.stat().st_size
            if size > budgets["single_asset_bytes"]:
                failures.append(
                    f"{path.relative_to(HERE)} is {size} bytes, exceeds "
                    f"single-asset budget {budgets['single_asset_bytes']}"
                )

    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print(
        f"OK: {len(files)} files, {total} bytes "
        f"(budget {budgets['static_total_bytes']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
