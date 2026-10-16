"""CI discovery entry for sbtd-runtime R1.2a event store tests."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "sbtd-runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

SPEC = importlib.util.spec_from_file_location(
    "sbtd_runtime_event_store_tests",
    RUNTIME / "tests" / "test_event_store.py",
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("sbtd-runtime event store tests could not be loaded")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

for _name, _obj in vars(MODULE).items():
    if isinstance(_obj, type) and issubclass(_obj, unittest.TestCase):
        globals()[_name] = _obj
del _name, _obj
