"""CI discovery entry for sbtd-runtime R1.2b host adapter tests."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "sbtd-runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

for _file in ("test_extensions.py", "test_omp_adapter.py", "test_codex_adapter.py"):
    _spec = importlib.util.spec_from_file_location(
        f"sbtd_runtime_{_file[:-3]}", RUNTIME / "tests" / _file
    )
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"sbtd-runtime adapter tests could not be loaded: {_file}")
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    for _name, _obj in vars(_module).items():
        if isinstance(_obj, type) and issubclass(_obj, unittest.TestCase):
            globals()[_name] = _obj

del _file, _spec, _module, _name, _obj
