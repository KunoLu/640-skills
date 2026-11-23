"""Package-owned notices added to standalone installations, never to upstream mirrors."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

NOTICE_DIR = "SBTD-NOTICES"


def notice_overlay(
    skill: str, source: Path, licenses: dict[str, Path], notices_root: Path
) -> dict[str, Path]:
    """Return installed relative paths and their sources, without writing a plan or staging tree.

    Callers resolve repository license mappings against the selected source root.
    An incoming upstream directory with our reserved name must never be overwritten.
    """
    if not licenses:
        raise RuntimeError(f"missing repository license for {skill}")
    if any(p.name.casefold() == NOTICE_DIR.casefold() for p in source.iterdir()):
        raise RuntimeError(f"{skill} already contains reserved {NOTICE_DIR}")
    files = dict(licenses)
    extra: tuple[str, ...] = ()
    if skill == "ui-ux-pro-max" and (source / "data/phosphor-icons-upstream.json").is_file():
        extra = ("phosphor-core-NOTICE", "phosphor-core-LICENSE")
    elif skill == "impeccable" and any((source / "reference" / name).is_file() for name in ("ios.md", "android.md")):
        extra = ("platform-design-skills-LICENSE",)
    if extra and (notices_root.is_symlink() or notices_root.resolve() != notices_root.absolute()):
        raise RuntimeError(f"unsafe supplemental notices directory: {notices_root}")
    for name in extra:
        if name in files:
            raise RuntimeError(f"duplicate notice name for {skill}: {name}")
        files[name] = notices_root / name
    if len({name.casefold() for name in files}) != len(files):
        raise RuntimeError(f"ambiguous notice names for {skill}")
    for name, path in files.items():
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", name) or path.is_symlink() or not path.is_file():
            raise RuntimeError(f"invalid notice file for {skill}: {name}")
    return {f"{NOTICE_DIR}/{name}": path for name, path in files.items()}


def copy_notices(destination: Path, overlay: dict[str, Path]) -> None:
    """Materialize a verified overlay in a fresh private stage, never in a live target."""
    (destination / NOTICE_DIR).mkdir()
    for relative, source in overlay.items():
        shutil.copyfile(source, destination / relative)
