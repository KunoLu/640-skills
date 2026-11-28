"""Native Windows file permissions for scoped retirement and recovery only.

The retained descriptor is self-relative, not an absolute pointer or SDDL.
Only owner, group and a supported DACL are replayed. A caller must keep the
bytes in private evidence and only apply them to its own unpublished file.
"""

from __future__ import annotations

import contextlib
import ctypes
import functools
import hashlib
import os
import stat
import struct
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NoReturn

from onboard_contracts import ContractError
from sbtd_project import TaskDataError, _reject_windows_reparse_points

_READ_CONTROL = 0x00020000
_WRITE_DAC = 0x00040000
_WRITE_OWNER = 0x00080000
_DELETE = 0x00010000
_READ_DATA = 0x0001
_GENERIC_WRITE = 0x40000000
_READ_ATTRIBUTES = 0x0080
_SHARE_ALL = 7
_OPEN_EXISTING = 3
_OPEN_REPARSE_POINT = 0x00200000
_OWNER_INFORMATION = 1
_GROUP_INFORMATION = 2
_DACL_INFORMATION = 4
# Integrity labels, resource attributes and central access policy identifiers.
_ACCESS_QUALIFIERS = 0x10 | 0x20 | 0x40
_DACL_PRESENT = 0x0004
_DACL_AUTO_INHERIT_REQ = 0x0100
_DACL_AUTO_INHERITED = 0x0400
_SELF_RELATIVE = 0x8000
_DACL_CONTROL = 0x950F  # self-relative, defaulted, present, inheritance, protection
_SACL_CONTROL = 0x2A30
_FILE_INFORMATION_BASIC = 0
_FILE_INFORMATION_RENAME = 3
_FILE_INFORMATION_DISPOSITION = 4
_FILE_INFORMATION_DISPOSITION_EX = 21
_FILE_INFORMATION_RENAME_EX = 22
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_SD = struct.Struct("<BBHIIII")
_ACL = struct.Struct("<BBHHH")
_ACE = struct.Struct("<BBH")
_MAX_DESCRIPTOR = 1 << 17


def _unproved(message: str) -> NoReturn:
    raise ContractError("permissions-unproven", message, exit_code=3)


def _sid_end(raw: bytes, offset: int, limit: int) -> int:
    if not _SD.size <= offset <= limit - 8 or offset % 4:
        _unproved("Windows security descriptor contains an invalid SID offset")
    count = raw[offset + 1]
    end = offset + 8 + 4 * count
    if raw[offset] != 1 or count > 15 or end > limit:
        _unproved("Windows security descriptor contains an unsupported SID")
    return end


def _parts(raw: bytes, *, native: bool = False) -> tuple[int, bytes, bytes, bytes]:
    if not isinstance(raw, bytes) or not _SD.size <= len(raw) <= _MAX_DESCRIPTOR:
        _unproved("Windows security descriptor is missing or malformed")
    revision, reserved, control, owner, group, sacl, dacl = _SD.unpack_from(raw)
    if revision != 1 or reserved or not control & _SELF_RELATIVE:
        _unproved("Windows security descriptor is not supported self-relative data")
    if native:
        # The OS returns only requested SACL qualifiers, not audit entries.
        if sacl:
            if not _SD.size <= sacl <= len(raw) - _ACL.size:
                _unproved("Windows access qualifiers could not be inspected")
            if _ACL.unpack_from(raw, sacl)[3]:
                _unproved("Windows file has an unsupported system access qualifier")
            sacl = 0
        control &= ~_SACL_CONTROL
    if sacl or control & ~_DACL_CONTROL:
        _unproved("Windows security descriptor control flags are not supported")
    if not control & _DACL_PRESENT:
        _unproved("Windows file has an absent DACL")
    if not dacl:
        _unproved("Windows file has a null DACL")
    if not _SD.size <= dacl <= len(raw) - _ACL.size or dacl % 4:
        _unproved("Windows security descriptor contains an invalid DACL offset")
    acl_revision, zero, size, count, zero2 = _ACL.unpack_from(raw, dacl)
    limit = dacl + size
    if acl_revision not in {2, 4} or zero or zero2 or size < _ACL.size or limit > len(raw):
        _unproved("Windows file has an unsupported DACL header")
    if not count:
        _unproved("Windows file has an empty DACL")
    owner_end = _sid_end(raw, owner, len(raw))
    group_end = _sid_end(raw, group, len(raw))
    spans = sorted({(owner, owner_end), (group, group_end), (dacl, limit)})
    if any(end > next_start for (_, end), (next_start, _) in zip(spans, spans[1:])):
        _unproved("Windows security descriptor components overlap")
    start = cursor = dacl + _ACL.size
    for _ in range(count):
        if cursor > limit - 16:
            _unproved("Windows DACL entry is truncated")
        kind, flags, ace_size = _ACE.unpack_from(raw, cursor)
        end = cursor + ace_size
        if kind not in {0, 1} or flags & ~0x1F or end > limit:
            _unproved("Windows DACL contains an unsupported access rule")
        # Basic allow/deny ACEs: four-byte header, DWORD mask, then one SID.
        if _sid_end(raw, cursor + 8, end) != end:
            _unproved("Windows DACL entry contains unsupported trailing data")
        cursor = end
    # Ignore ACL allocation slack and descriptor offsets, not ACE flags or order.
    acl = _ACL.pack(acl_revision, 0, cursor - dacl, count, 0) + raw[start:cursor]
    return control, raw[owner:owner_end], raw[group:group_end], acl


def _pack(control: int, owner: bytes, group: bytes, acl: bytes) -> bytes:
    a = _SD.size
    b = a + len(owner)
    c = b + len(group)
    return _SD.pack(1, 0, control, a, b, 0, c) + owner + group + acl


def digest(raw: bytes) -> str:
    """Stable proof of owner, group, descriptor control and ordered ACEs."""
    return hashlib.sha256(b"sbtd-win32-file-permissions-v1\x00" + _pack(*_parts(raw))).hexdigest()


@functools.cache
def _win32() -> Any:
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    pointer = ctypes.c_void_p
    out = ctypes.POINTER(pointer)

    def bind(dll: Any, name: str, result: Any, *arguments: Any) -> Any:
        function = getattr(dll, name)
        function.restype = result
        function.argtypes = arguments
        return function

    class RenameInformation(ctypes.Structure):
        _fields_ = [
            ("Flags", w.DWORD), ("RootDirectory", w.HANDLE),
            ("FileNameLength", w.DWORD), ("FileName", w.WCHAR * 1),
        ]

    class BasicInformation(ctypes.Structure):
        _fields_ = [
            ("CreationTime", ctypes.c_longlong), ("LastAccessTime", ctypes.c_longlong),
            ("LastWriteTime", ctypes.c_longlong), ("ChangeTime", ctypes.c_longlong),
            ("Attributes", w.DWORD),
        ]

    return types.SimpleNamespace(
        CreateFile=bind(kernel, "CreateFileW", w.HANDLE, w.LPCWSTR, w.DWORD, w.DWORD,
                        pointer, w.DWORD, w.DWORD, w.HANDLE),
        CloseHandle=bind(kernel, "CloseHandle", w.BOOL, w.HANDLE),
        FinalName=bind(kernel, "GetFinalPathNameByHandleW", w.DWORD, w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD),
        LocalFree=bind(kernel, "LocalFree", pointer, pointer),
        GetSecurity=bind(security, "GetSecurityInfo", w.DWORD, w.HANDLE, ctypes.c_int,
                         w.DWORD, out, out, out, out, out),
        SecurityLength=bind(security, "GetSecurityDescriptorLength", w.DWORD, pointer),
        BackupWrite=bind(kernel, "BackupWrite", w.BOOL, w.HANDLE, pointer, w.DWORD,
                         ctypes.POINTER(w.DWORD), w.BOOL, w.BOOL, out),
        SetFileInformation=bind(kernel, "SetFileInformationByHandle", w.BOOL, w.HANDLE,
                                ctypes.c_int, pointer, w.DWORD),
        RenameInformation=RenameInformation,
        BasicInformation=BasicInformation,
    )


def _native_path(path: Path) -> str:
    name = str(path)
    if (
        not path.is_absolute()
        or name.startswith(("\\\\?\\", "\\\\.\\"))
        or any(":" in part or "\x00" in part or part.endswith((".", " ")) for part in path.parts[1:])
    ):
        _unproved("Windows permissions require a canonical, unnamed-stream file path")
    return "\\\\?\\UNC\\" + name[2:] if name.startswith("\\\\") else "\\\\?\\" + name


@contextlib.contextmanager
def _file(path: Path, access: int = 0, *, share: int = _SHARE_ALL) -> Iterator[tuple[int, int]]:
    if os.name != "nt":
        _unproved("native Windows permissions are unavailable on this platform")
    import msvcrt

    native = _native_path(path)
    try:
        _reject_windows_reparse_points(path.parent, "retirement file parent")
    except (OSError, TaskDataError):
        _unproved("Windows file permissions cannot be inspected without following links")
    api = _win32()
    handle = api.CreateFile(native, _READ_CONTROL | _READ_ATTRIBUTES | access, share,
                            None, _OPEN_EXISTING, _OPEN_REPARSE_POINT, None)
    if handle in (None, _INVALID_HANDLE):
        _unproved("Windows file access could not be opened for permission proof")
    try:
        mode = os.O_RDWR if access & _GENERIC_WRITE else os.O_RDONLY
        fd = msvcrt.open_osfhandle(handle, mode | os.O_BINARY)
    except OSError:
        api.CloseHandle(handle)
        _unproved("Windows file handle could not be inspected")
    try:
        try:
            info = os.fstat(fd)
        except OSError:
            _unproved("Windows file identity could not be inspected")
        if (
            not stat.S_ISREG(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
            or info.st_nlink != 1
        ):
            _unproved("opened Windows file is not a single-link regular file")
        size = api.FinalName(handle, None, 0, 0)
        if not size:
            _unproved("Windows file path identity could not be verified")
        name = ctypes.create_unicode_buffer(size)
        result = api.FinalName(handle, name, size, 0)
        if not 0 < result < size or os.path.normcase(name.value) != os.path.normcase(native):
            _unproved("Windows file handle does not resolve to the selected physical path")
        yield handle, fd
    finally:
        os.close(fd)


def _read_handle(handle: int) -> bytes:
    api = _win32()
    descriptor = ctypes.c_void_p()
    flags = _OWNER_INFORMATION | _GROUP_INFORMATION | _DACL_INFORMATION | _ACCESS_QUALIFIERS
    status = api.GetSecurity(handle, 1, flags, None, None, None, None, ctypes.byref(descriptor))
    try:
        if status or not descriptor.value:
            _unproved("Windows owner, group, DACL or access qualifiers cannot be inspected")
        size = api.SecurityLength(descriptor)
        if not _SD.size <= size <= _MAX_DESCRIPTOR:
            _unproved("Windows security descriptor length is invalid")
        return _pack(*_parts(ctypes.string_at(descriptor, size), native=True))
    finally:
        if descriptor.value:
            api.LocalFree(descriptor)


def capture(path: Path) -> bytes:
    """Capture a replay candidate from an opened, no-follow Windows file."""
    with _file(path) as (handle, _):
        return _read_handle(handle)


def _apply_permissions(handle: int, fd: int, raw: bytes) -> None:
    if os.fstat(fd).st_size:
        _unproved("Windows permission replay requires an empty unpublished file")
    control, owner, group, acl = _parts(raw)
    desired = _pack(control, owner, group, acl)
    if _read_handle(handle) == desired:
        return
    # Ask the file system to retain AUTO_INHERITED rather than clear it on
    # the security write. Exact readback below remains the authority.
    if control & _DACL_AUTO_INHERITED:
        control |= _DACL_AUTO_INHERIT_REQ
    descriptor = _pack(control, owner, group, acl)
    # One WIN32_STREAM_ID: BACKUP_SECURITY_DATA | STREAM_CONTAINS_SECURITY.
    stream = struct.pack("<IIQI", 3, 2, len(descriptor), 0) + descriptor
    api = _win32()
    context = ctypes.c_void_p()
    written = ctypes.c_ulong()
    try:
        if not api.BackupWrite(
            handle, stream, len(stream), ctypes.byref(written), False, True, ctypes.byref(context),
        ) or written.value != len(stream):
            _unproved("Windows file permissions could not be replayed without elevation")
    finally:
        if context.value:
            api.BackupWrite(handle, None, 0, ctypes.byref(written), True, True, ctypes.byref(context))
    if _read_handle(handle) != desired:
        _unproved("Windows changed staged permission semantics during replay")


def _verify_staged(staged: Path, raw: bytes) -> None:
    # A previously granted handle would not prove the candidate can be reopened.
    with _file(staged, _READ_DATA) as (handle, _):
        if _read_handle(handle) != _pack(*_parts(raw)):
            _unproved("Windows staged file permission readback differs")


def stage_permissions(staged: Path, raw: bytes) -> None:
    """Apply and verify permissions on a caller-owned, private empty file."""
    with _file(staged, _GENERIC_WRITE | _WRITE_DAC | _WRITE_OWNER) as (handle, fd):
        _apply_permissions(handle, fd, raw)
        _verify_staged(staged, raw)


def _set_read_only(handle: int, attrs: int, *, enabled: bool) -> None:
    api = _win32()
    info = api.BasicInformation()
    readonly = stat.FILE_ATTRIBUTE_READONLY
    normal = stat.FILE_ATTRIBUTE_NORMAL
    info.Attributes = ((attrs & ~normal) | readonly) if enabled else ((attrs & ~readonly) or normal)
    if not api.SetFileInformation(handle, _FILE_INFORMATION_BASIC, ctypes.byref(info), ctypes.sizeof(info)):
        _unproved("Windows staged read-only attribute could not be set")


def _rename_handle(handle: int, target: Path, *, replace: bool, read_only: bool) -> None:
    api = _win32()
    name = _native_path(target).encode("utf-16-le")
    prefix = api.RenameInformation.FileName.offset
    size = max(ctypes.sizeof(api.RenameInformation), prefix + len(name) + 2)
    buffer = ctypes.create_string_buffer(size)
    info = api.RenameInformation.from_buffer(buffer)
    info.Flags = int(replace) | (0x40 if read_only else 0)  # IGNORE_READONLY_ATTRIBUTE
    info.FileNameLength = len(name)
    ctypes.memmove(ctypes.addressof(info) + prefix, name, len(name))
    kind = _FILE_INFORMATION_RENAME_EX if read_only else _FILE_INFORMATION_RENAME
    if not api.SetFileInformation(handle, kind, buffer, size):
        if not replace and ctypes.get_last_error() in {80, 183}:
            raise FileExistsError("Windows target appeared during publication")
        raise OSError("Windows file handle rename failed")


def _delete_handle(handle: int, *, read_only: bool) -> None:
    kind = _FILE_INFORMATION_DISPOSITION_EX if read_only else _FILE_INFORMATION_DISPOSITION
    # DELETE | POSIX_SEMANTICS | IGNORE_READONLY_ATTRIBUTE, or a plain BOOLEAN.
    flags = ctypes.c_ulong(0x13) if read_only else ctypes.c_ubyte(1)
    if not _win32().SetFileInformation(handle, kind, ctypes.byref(flags), ctypes.sizeof(flags)):
        raise OSError("Windows file handle deletion failed")
