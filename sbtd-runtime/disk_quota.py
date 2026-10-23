"""One runtime writer's flat snapshots/ + exports/ admission (ADR 0003 §4/5)."""

from __future__ import annotations

import logging
import os
import re
import stat
import threading
from pathlib import Path

DEFAULT_DISK_QUOTA_BYTES = 2000000000
_CONFIG_ERROR = (
    "SBTD_RUNTIME_DISK_QUOTA_BYTES must be a positive ASCII decimal integer ([0-9]+)"
)


def parse_disk_quota() -> int:
    value = os.environ.get("SBTD_RUNTIME_DISK_QUOTA_BYTES")
    if value is None:
        return DEFAULT_DISK_QUOTA_BYTES
    try:
        if re.fullmatch(r"[0-9]+", value):
            parsed = int(value)
            if parsed > 0:
                return parsed
    except ValueError:
        pass
    raise ValueError(_CONFIG_ERROR)


class DiskQuotaExceeded(RuntimeError):
    def __init__(self, used_bytes: int, quota_bytes: int) -> None:
        super().__init__("DISK_QUOTA_EXCEEDED")
        self.used_bytes = used_bytes
        self.quota_bytes = quota_bytes


def file_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def exclusive_file(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        or (hasattr(os, "getuid") and info.st_uid != os.getuid())
    ):
        return None
    return info


class DiskQuota:
    """Shared lock covers store references, sweeps, admission and file publication.

    Construction requires the caller's single-writer ownership, as do the stores.
    serve obtains its instance lock first. Library callers must provide exclusivity.
    Rendering stays outside this lock; no future output bytes are reserved.
    """

    def __init__(self, home: Path, quota_bytes: int) -> None:
        if type(quota_bytes) is not int or quota_bytes <= 0:
            raise ValueError(_CONFIG_ERROR)
        self.home = Path(home).absolute()
        self.quota_bytes = quota_bytes
        # ponytail: one writer-wide lock; split only with a proven lock-order protocol.
        self.lock = threading.RLock()
        self.snapshot_sweep = None
        self.export_sweep = None
        self._directories: dict[Path, tuple[int, int]] = {}
        self._temps: dict[Path, tuple[int, int, int, int, int]] = {}
        self._active_temps: set[Path] = set()
        self.check_directories()
        for name, prefix in (("snapshots", ".snapshot-"), ("exports", ".export-")):
            directory = self.home / name
            if directory not in self._directories:
                continue
            for path in directory.iterdir():
                if path.name.startswith(prefix) and path.name.endswith(".tmp"):
                    info = exclusive_file(path)
                    if info is not None:
                        self._temps[path] = file_identity(info)

    def check_directories(self) -> None:
        # Local imports avoid merging the two stores' ownership/validation rules.
        from export_store import validate_export_home
        from report_snapshot import validate_snapshot_home

        validate_snapshot_home(self.home)
        validate_export_home(self.home)
        for name in ("snapshots", "exports"):
            path = self.home / name
            try:
                info = path.lstat()
            except FileNotFoundError:
                if path in self._directories:
                    raise ValueError("quota directory disappeared") from None
                continue
            identity = info.st_dev, info.st_ino
            if self._directories.setdefault(path, identity) != identity:
                raise ValueError("quota directory was replaced")

    def start_temp(self, path: Path) -> None:
        # Called under the shared lock immediately after mkstemp.
        self._active_temps.add(path)

    def finish_temp(self, path: Path) -> None:
        self._active_temps.discard(path)
        info = exclusive_file(path)
        if info is not None:
            self._temps[path] = file_identity(info)

    def sweep(self, *, now=None) -> None:
        with self.lock:
            self.check_directories()
            if self.export_sweep is not None:
                self.export_sweep(now=now)
            if self.snapshot_sweep is not None:
                self.snapshot_sweep(now=now)
            for path, identity in list(self._temps.items()):
                if path in self._active_temps:
                    continue
                self.check_directories()
                info = exclusive_file(path)
                if info is None or file_identity(info) != identity:
                    self._temps.pop(path, None)
                    continue
                try:
                    path.unlink()
                except OSError:
                    continue
                self._temps.pop(path, None)

    def used_bytes(self) -> int:
        with self.lock:
            self.check_directories()
            used = 0
            for directory in self._directories:
                for path in directory.iterdir():
                    info = path.lstat()
                    if stat.S_ISREG(info.st_mode) and not (
                        getattr(info, "st_file_attributes", 0)
                        & stat.FILE_ATTRIBUTE_REPARSE_POINT
                    ):
                        used += info.st_size
            self.check_directories()
            return used

    def admit(self, *, now=None) -> None:
        with self.lock:
            self.sweep(now=now)
            used = self.used_bytes()
            if 5 * used >= 4 * self.quota_bytes:
                logging.getLogger(__name__).warning(
                    "shared disk quota warning: used_bytes=%d quota_bytes=%d",
                    used,
                    self.quota_bytes,
                )
            if used > self.quota_bytes:
                raise DiskQuotaExceeded(used, self.quota_bytes)
