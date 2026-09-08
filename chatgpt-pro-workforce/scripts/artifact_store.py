#!/usr/bin/env python3
"""Bounded, run-scoped intake and cleanup for untrusted worker artifacts.

The module intentionally uses only the Python standard library.  It never
extracts an archive until the complete central-directory inventory has passed
all configured limits and path/type checks.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, Callable, Iterable, NoReturn
import unicodedata
import zipfile

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None


SCHEMA_VERSION = 1
SAFE_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
DRIVE_PATH = re.compile(r"^[A-Za-z]:")
SOURCE_KINDS = {"BROWSER_ATTACHMENT", "BROWSER_DOWNLOAD", "BASE64_RECOVERY", "LOCAL_FIXTURE"}
AUTHORIZATION_STATES = {"PENDING_EXPLICIT_AUTHORIZATION", "AUTHORIZED_EXACT_MANIFEST"}
CLEANABLE_AREAS = {"incoming", "candidates", "raw"}
TERMINAL_CLEANUP_STATES = {
    "QUARANTINED",
    "QUARANTINED_RECONCILED",
    "QUARANTINED_IDENTITY_CHANGED",
}
INTAKE_STATES = {
    "INTENT",
    "COMMITTED",
    "REJECTED_RETAINED",
    "OUTCOME_UNKNOWN_RETAINED",
    "DEFINITELY_NOT_PUBLISHED",
}
SUPPORTED_ZIP_COMPRESSION = {
    zipfile.ZIP_STORED,
    zipfile.ZIP_DEFLATED,
    zipfile.ZIP_BZIP2,
    zipfile.ZIP_LZMA,
}
MAX_MEMBER_NAME_BYTES = 4096
MAX_MEMBER_COMPONENT_BYTES = 255


class ArtifactStoreError(ValueError):
    """A bounded error that is safe to show to a local operator."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {_safe_text(message)}\n")


@dataclass(frozen=True)
class Limits:
    max_members: int = 256
    max_source_bytes: int = 64 * 1024 * 1024
    max_compressed_bytes: int = 64 * 1024 * 1024
    max_expanded_bytes: int = 256 * 1024 * 1024
    max_ratio: int = 100
    max_file_bytes: int = 64 * 1024 * 1024
    max_base64_bytes: int = 96 * 1024 * 1024

    def validate(self) -> None:
        for field, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ArtifactStoreError(f"{field} must be a positive integer")
        if self.max_file_bytes > self.max_expanded_bytes:
            raise ArtifactStoreError("max_file_bytes must not exceed max_expanded_bytes")


@dataclass(frozen=True)
class Provenance:
    source_name: str
    source_kind: str
    lane_id: str
    conversation_id: str

    def validate(self) -> None:
        _bounded_label(self.source_name, "source_name", 255)
        if self.source_kind not in SOURCE_KINDS:
            raise ArtifactStoreError("source_kind is unsupported")
        _safe_id(self.lane_id, "lane_id")
        _bounded_label(self.conversation_id, "conversation_id", 255)


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    size: int
    sha256: str


def _safe_text(value: object, limit: int = 320) -> str:
    text = str(value).encode("ascii", "backslashreplace").decode("ascii")
    text = " ".join("".join(char if 32 <= ord(char) < 127 else " " for char in text).split())
    return text[:limit] + ("..." if len(text) > limit else "")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value) or value in {".", ".."}:
        raise ArtifactStoreError(f"{field} is not a safe identifier")
    return value


def _bounded_label(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ArtifactStoreError(f"{field} must be a non-empty string of at most {maximum} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ArtifactStoreError(f"{field} contains control characters")
    return value


def _canonical_path(path: Path) -> Path:
    candidate = Path(os.path.abspath(os.fspath(path)))
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ArtifactStoreError("path could not be resolved safely") from exc
    if candidate != resolved:
        raise ArtifactStoreError("path contains a symbolic-link component")
    return candidate


def _private_dir(path: Path, *, create: bool = False) -> Path:
    path = _canonical_path(path)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = path.lstat()
    except OSError as exc:
        raise ArtifactStoreError("required private directory is unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ArtifactStoreError("private storage path is not a real directory")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ArtifactStoreError("private storage directory has a different owner")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ArtifactStoreError("private storage directory permits group or other access")
    return path


def _create_private_dir(path: Path) -> Path:
    parent = _private_dir(path.parent)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    return _private_dir(parent / path.name)


def _read_exact_file(
    path: Path,
    maximum: int,
    *,
    require_single_link: bool = True,
    after_read_hook: Callable[[], None] | None = None,
) -> Snapshot:
    if maximum <= 0:
        raise ArtifactStoreError("read limit must be positive")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    # Opening a FIFO for read without a writer blocks before fstat can reject
    # it. O_NONBLOCK is harmless for regular files and makes that validation
    # boundary fail closed instead of hanging.
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        before_path = path.lstat()
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ArtifactStoreError("source is unavailable or is not a safe regular file") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before_path.st_mode):
            raise ArtifactStoreError("source is not a regular file")
        if (before.st_dev, before.st_ino) != (before_path.st_dev, before_path.st_ino):
            raise ArtifactStoreError("source identity changed before intake")
        if require_single_link and before.st_nlink != 1:
            raise ArtifactStoreError("source must have exactly one filesystem link")
        if before.st_size > maximum:
            raise ArtifactStoreError("source exceeds the configured byte limit")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > maximum:
            raise ArtifactStoreError("source exceeds the configured byte limit")
        if after_read_hook is not None:
            after_read_hook()
        after = os.fstat(descriptor)
        try:
            after_path = path.lstat()
        except OSError as exc:
            raise ArtifactStoreError("source identity changed during intake") from exc
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if identity_before != identity_after:
            raise ArtifactStoreError("source changed during intake")
        if (after.st_dev, after.st_ino) != (after_path.st_dev, after_path.st_ino):
            raise ArtifactStoreError("source path was replaced during intake")
        if len(data) != before.st_size:
            raise ArtifactStoreError("source length changed during intake")
        return Snapshot(data=data, size=len(data), sha256=hashlib.sha256(data).hexdigest())
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    _private_dir(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags, mode)
        view = memoryview(data)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise ArtifactStoreError("exclusive file write made no progress")
            view = view[count:]
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
    except FileExistsError as exc:
        raise ArtifactStoreError("exclusive destination already exists") from exc
    except OSError as exc:
        try:
            if descriptor is not None:
                os.close(descriptor)
                descriptor = None
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ArtifactStoreError("exclusive file write failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    _fsync_dir(path.parent)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    parent = _private_dir(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _fsync_dir(parent)
    except OSError as exc:
        raise ArtifactStoreError("atomic state write failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    _write_exclusive(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _fsync_dir(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _cleanup_lock(root: Path):
    """Serialize cleanup planning, application, and reconciliation per store."""
    cleanup_dir = _ensure_area(root, "manifests/cleanup")
    lock_path = cleanup_dir / ".cleanup.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(lock_path, flags, 0o600)
        info = os.fstat(descriptor)
        path_info = lock_path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(path_info.st_mode)
            or (info.st_dev, info.st_ino) != (path_info.st_dev, path_info.st_ino)
            or info.st_nlink != 1
        ):
            raise ArtifactStoreError("cleanup lock is not a safe regular file")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise ArtifactStoreError("cleanup lock has a different owner")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ArtifactStoreError("cleanup lock is not private")
        if fcntl is None:
            raise ArtifactStoreError("cleanup serialization is unavailable on this platform")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked_info = os.fstat(descriptor)
        locked_path = lock_path.lstat()
        if (locked_info.st_dev, locked_info.st_ino) != (locked_path.st_dev, locked_path.st_ino):
            raise ArtifactStoreError("cleanup lock identity changed while acquiring serialization")
        yield
    except OSError as exc:
        raise ArtifactStoreError("cleanup serialization failed") from exc
    finally:
        if descriptor is not None:
            if fcntl is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(descriptor)


@contextmanager
def _intake_lock(root: Path):
    """Serialize intake publication and reconciliation within one store."""
    intake_state = _ensure_area(root, "manifests/intake-state")
    lock_path = intake_state / ".intake.lock"
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(lock_path, flags, 0o600)
        info = os.fstat(descriptor)
        path_info = lock_path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(path_info.st_mode)
            or (info.st_dev, info.st_ino) != (path_info.st_dev, path_info.st_ino)
            or info.st_nlink != 1
        ):
            raise ArtifactStoreError("intake lock is not a safe regular file")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise ArtifactStoreError("intake lock has a different owner")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise ArtifactStoreError("intake lock is not private")
        if fcntl is None:
            raise ArtifactStoreError("intake serialization is unavailable on this platform")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked_info = os.fstat(descriptor)
        locked_path = lock_path.lstat()
        if (locked_info.st_dev, locked_info.st_ino) != (locked_path.st_dev, locked_path.st_ino):
            raise ArtifactStoreError("intake lock identity changed while acquiring serialization")
        yield
    except OSError as exc:
        raise ArtifactStoreError("intake serialization failed") from exc
    finally:
        if descriptor is not None:
            if fcntl is not None:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(descriptor)


def _load_json(path: Path, maximum: int = 8 * 1024 * 1024) -> dict[str, Any]:
    snapshot = _read_exact_file(path, maximum, require_single_link=True)
    info = path.lstat()
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ArtifactStoreError("stored JSON has a different owner")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ArtifactStoreError("stored JSON is not private")
    try:
        value = json.loads(snapshot.data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactStoreError("stored JSON is malformed") from exc
    if not isinstance(value, dict):
        raise ArtifactStoreError("stored JSON must be an object")
    return value


def init_store(run_root: Path, run_id: str) -> dict[str, Any]:
    """Initialize or verify one private run-owned artifact store."""
    _safe_id(run_id, "run_id")
    root = _canonical_path(run_root)
    if root.exists():
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ArtifactStoreError("run root is not a real directory")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise ArtifactStoreError("run root has a different owner")
    else:
        root.mkdir(mode=0o700, parents=True)
    root = _private_dir(root)
    manifests = root / "manifests"
    if not manifests.exists():
        _create_private_dir(manifests)
    else:
        _private_dir(manifests)
    marker = manifests / "artifact-store.json"
    if marker.exists():
        state = _load_json(marker, 64 * 1024)
        if state.get("schema_version") != SCHEMA_VERSION or state.get("run_id") != run_id:
            raise ArtifactStoreError("run root belongs to a different or unsupported store")
        return state
    state = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": _now()}
    _exclusive_json(marker, state)
    return state


def _open_store(run_root: Path, run_id: str) -> Path:
    root = _private_dir(run_root)
    marker = root / "manifests" / "artifact-store.json"
    state = _load_json(marker, 64 * 1024)
    if set(state) != {"schema_version", "run_id", "created_at"}:
        raise ArtifactStoreError("artifact store marker has an unsupported schema")
    if state["schema_version"] != SCHEMA_VERSION or state["run_id"] != run_id:
        raise ArtifactStoreError("run root does not match the requested run")
    return root


def _safe_member_name(info: zipfile.ZipInfo) -> tuple[str, bool]:
    original = getattr(info, "orig_filename", info.filename)
    if not isinstance(original, str) or not original or "\x00" in original:
        raise ArtifactStoreError("archive contains a malformed member name")
    if any(ord(char) < 32 or ord(char) == 127 or unicodedata.category(char) == "Cs" for char in original):
        raise ArtifactStoreError("archive contains a malformed member name")
    try:
        encoded_name = original.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ArtifactStoreError("archive contains a malformed member name") from exc
    if len(encoded_name) > MAX_MEMBER_NAME_BYTES:
        raise ArtifactStoreError("archive member name exceeds the configured safety bound")
    if "\\" in original:
        raise ArtifactStoreError("archive member uses a backslash path")
    if original.startswith("/") or DRIVE_PATH.match(original):
        raise ArtifactStoreError("archive member uses an absolute path")
    is_directory = info.is_dir() or original.endswith("/")
    trimmed = original[:-1] if is_directory else original
    parts = PurePosixPath(trimmed).parts
    if not trimmed or not parts or any(part in {"", ".", ".."} for part in parts):
        raise ArtifactStoreError("archive member path is empty, dotted, or traversing")
    if any(len(part.encode("utf-8")) > MAX_MEMBER_COMPONENT_BYTES for part in parts):
        raise ArtifactStoreError("archive member path component exceeds the filesystem safety bound")
    normalized = "/".join(parts)
    if normalized != trimmed:
        raise ArtifactStoreError("archive member path is not canonical")
    return normalized, is_directory


def inspect_zip_bytes(data: bytes, limits: Limits) -> dict[str, Any]:
    """Validate all ZIP metadata and return a deterministic inventory."""
    limits.validate()
    if len(data) > limits.max_source_bytes or len(data) > limits.max_compressed_bytes:
        raise ArtifactStoreError("archive exceeds a configured source or compressed-byte limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArtifactStoreError("source is not a valid ZIP archive") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > limits.max_members:
            raise ArtifactStoreError("archive exceeds the configured member-count limit")
        exact: set[str] = set()
        folded: dict[str, str] = {}
        types: dict[str, bool] = {}
        total_compressed = 0
        total_expanded = 0
        members: list[dict[str, Any]] = []
        for info in infos:
            name, is_directory = _safe_member_name(info)
            collision_key = unicodedata.normalize("NFC", name).casefold()
            if name in exact:
                raise ArtifactStoreError("archive contains a duplicate destination")
            if collision_key in folded:
                raise ArtifactStoreError("archive contains a case-fold or Unicode destination collision")
            exact.add(name)
            folded[collision_key] = name
            types[name] = is_directory
            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ArtifactStoreError("archive contains a symbolic link or special file")
            if file_type == stat.S_IFDIR and not is_directory:
                raise ArtifactStoreError("archive member type conflicts with its path")
            if file_type == stat.S_IFREG and is_directory:
                raise ArtifactStoreError("archive directory has regular-file metadata")
            if info.flag_bits & 0x1:
                raise ArtifactStoreError("encrypted archive members are unsupported")
            if info.compress_type not in SUPPORTED_ZIP_COMPRESSION:
                raise ArtifactStoreError("archive uses an unsupported compression method")
            if info.file_size < 0 or info.compress_size < 0:
                raise ArtifactStoreError("archive contains invalid size metadata")
            if is_directory and (info.file_size or info.compress_size):
                raise ArtifactStoreError("archive directory contains data")
            if not is_directory and info.file_size > limits.max_file_bytes:
                raise ArtifactStoreError("archive member exceeds the configured per-file limit")
            total_compressed += info.compress_size
            total_expanded += info.file_size
            if total_compressed > limits.max_compressed_bytes:
                raise ArtifactStoreError("archive exceeds the configured compressed-byte limit")
            if total_expanded > limits.max_expanded_bytes:
                raise ArtifactStoreError("archive exceeds the configured expanded-byte limit")
            if info.file_size and (info.compress_size == 0 or info.file_size > info.compress_size * limits.max_ratio):
                raise ArtifactStoreError("archive member exceeds the configured expansion ratio")
            members.append(
                {
                    "path": name,
                    "kind": "DIRECTORY" if is_directory else "FILE",
                    "compressed_bytes": info.compress_size,
                    "expanded_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                }
            )
        folded_types = {
            unicodedata.normalize("NFC", name).casefold(): is_directory
            for name, is_directory in types.items()
        }
        for name, is_directory in types.items():
            parts = name.split("/")
            for index in range(1, len(parts)):
                ancestor = "/".join(parts[:index])
                folded_ancestor = unicodedata.normalize("NFC", ancestor).casefold()
                if folded_ancestor in folded_types and not folded_types[folded_ancestor]:
                    raise ArtifactStoreError("archive has a file/directory destination conflict")
            folded_prefix = unicodedata.normalize("NFC", name).casefold() + "/"
            if not is_directory and any(
                other.startswith(folded_prefix) for other in folded_types if other != folded_prefix[:-1]
            ):
                raise ArtifactStoreError("archive has a file/directory destination conflict")
        members.sort(key=lambda item: (item["path"].casefold(), item["path"]))
        return {
            "member_count": len(members),
            "compressed_bytes": total_compressed,
            "expanded_bytes": total_expanded,
            "members": members,
            "limits": asdict(limits),
        }


def inspect_zip_path(path: Path, limits: Limits) -> dict[str, Any]:
    snapshot = _read_exact_file(path, min(limits.max_source_bytes, limits.max_compressed_bytes))
    inventory = inspect_zip_bytes(snapshot.data, limits)
    return {"source_size": snapshot.size, "source_sha256": snapshot.sha256, **inventory}


def _ensure_area(root: Path, relative: str) -> Path:
    current = root
    for part in relative.split("/"):
        current = current / part
        if not current.exists():
            _create_private_dir(current)
        else:
            _private_dir(current)
    return current


def _store_blob(root: Path, snapshot: Snapshot) -> tuple[Path, bool]:
    blob_dir = _ensure_area(root, f"raw/sha256/{snapshot.sha256[:2]}")
    destination = blob_dir / snapshot.sha256
    if destination.exists():
        existing = _read_exact_file(destination, snapshot.size + 1, require_single_link=True)
        info = destination.lstat()
        if existing.sha256 != snapshot.sha256 or existing.size != snapshot.size:
            raise ArtifactStoreError("existing content-addressed raw object failed identity verification")
        if stat.S_IMODE(info.st_mode) != 0o400:
            raise ArtifactStoreError("existing raw object is not private and read-only")
        return destination, True
    _write_exclusive(destination, snapshot.data, mode=0o400)
    return destination, False


def _intake_state_path(root: Path, artifact_id: str) -> Path:
    return _ensure_area(root, "manifests/intake-state") / f"{artifact_id}.json"


def _validate_intake_state(state: dict[str, Any], run_id: str, artifact_id: str) -> None:
    required = {
        "schema_version", "run_id", "artifact_id", "created_at", "updated_at",
        "state", "detail", "kind", "source", "expected", "archive_inventory", "observation",
    }
    if set(state) != required or state.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactStoreError("intake transaction has an unsupported schema")
    if state.get("run_id") != run_id or state.get("artifact_id") != artifact_id:
        raise ArtifactStoreError("intake transaction does not match the requested run and artifact")
    if state.get("state") not in INTAKE_STATES or state.get("kind") not in {"FILE", "ZIP"}:
        raise ArtifactStoreError("intake transaction state is malformed")
    source = state.get("source")
    if not isinstance(source, dict):
        raise ArtifactStoreError("intake transaction source is malformed")
    digest = source.get("sha256")
    size = source.get("size_bytes")
    if (
        not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
    ):
        raise ArtifactStoreError("intake transaction source identity is malformed")
    expected = state.get("expected")
    if not isinstance(expected, dict) or set(expected) != {
        "raw_stored_path", "raw_preexisting", "extraction_root", "extraction_preexisting"
    }:
        raise ArtifactStoreError("intake transaction destinations are malformed")
    expected_raw = f"raw/sha256/{digest[:2]}/{digest}"
    expected_extraction = f"raw/extracted/{digest}" if state["kind"] == "ZIP" else None
    if (
        expected.get("raw_stored_path") != expected_raw
        or expected.get("extraction_root") != expected_extraction
        or not isinstance(expected.get("raw_preexisting"), bool)
        or not isinstance(expected.get("extraction_preexisting"), bool)
    ):
        raise ArtifactStoreError("intake transaction destinations do not match its source")
    if not isinstance(state.get("detail"), str) or not isinstance(state.get("observation"), dict):
        raise ArtifactStoreError("intake transaction observation is malformed")
    archive_inventory = state.get("archive_inventory")
    if state["kind"] == "FILE" and archive_inventory is not None:
        raise ArtifactStoreError("file intake transaction contains archive inventory")
    if state["kind"] == "ZIP" and (
        not isinstance(archive_inventory, dict)
        or not isinstance(archive_inventory.get("members"), list)
    ):
        raise ArtifactStoreError("ZIP intake transaction lacks archive inventory")
    observation = state["observation"]
    if observation and (
        set(observation) != {"raw", "extraction", "abandoned_staging_trees_removed"}
        or observation.get("raw") not in {"MISSING", "EXACT", "IDENTITY_CHANGED"}
        or observation.get("extraction") not in {
            "NOT_APPLICABLE", "MISSING", "EXACT", "EXACT_TO_INTENT", "IDENTITY_CHANGED"
        }
        or isinstance(observation.get("abandoned_staging_trees_removed"), bool)
        or not isinstance(observation.get("abandoned_staging_trees_removed"), int)
        or observation["abandoned_staging_trees_removed"] < 0
    ):
        raise ArtifactStoreError("intake transaction observation is malformed")


def _observe_raw(root: Path, state: dict[str, Any]) -> str:
    expected = state["expected"]
    source = state["source"]
    path = root.joinpath(*PurePosixPath(expected["raw_stored_path"]).parts)
    try:
        _private_dir(path.parent)
        info = path.lstat()
    except FileNotFoundError:
        return "MISSING"
    except ArtifactStoreError:
        return "IDENTITY_CHANGED"
    except OSError:
        return "IDENTITY_CHANGED"
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_ISLNK(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o400
    ):
        return "IDENTITY_CHANGED"
    try:
        snapshot = _read_exact_file(path, source["size_bytes"] + 1, require_single_link=True)
    except ArtifactStoreError:
        return "IDENTITY_CHANGED"
    if snapshot.size != source["size_bytes"] or snapshot.sha256 != source["sha256"]:
        return "IDENTITY_CHANGED"
    return "EXACT"


def _observe_extraction(root: Path, state: dict[str, Any], manifest: dict[str, Any] | None) -> str:
    relative = state["expected"]["extraction_root"]
    if relative is None:
        return "NOT_APPLICABLE"
    path = root.joinpath(*PurePosixPath(relative).parts)
    try:
        _private_dir(path.parent)
        info = path.lstat()
    except FileNotFoundError:
        return "MISSING"
    except ArtifactStoreError:
        return "IDENTITY_CHANGED"
    except OSError:
        return "IDENTITY_CHANGED"
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        return "IDENTITY_CHANGED"
    if manifest is None:
        try:
            _validate_intended_extraction_tree(root, path, state["archive_inventory"])
        except ArtifactStoreError:
            return "IDENTITY_CHANGED"
        return "EXACT_TO_INTENT"
    archive = manifest.get("archive")
    members = archive.get("members") if isinstance(archive, dict) else None
    if not isinstance(members, list):
        return "IDENTITY_CHANGED"
    try:
        _validate_extraction_tree(root, path, members)
    except ArtifactStoreError:
        return "IDENTITY_CHANGED"
    return "EXACT"


def _discard_intake_staging(root: Path, digest: str) -> int:
    """Remove only abandoned helper staging trees bound to one intended digest."""
    extracted_root = root / "raw" / "extracted"
    try:
        extracted_root.lstat()
    except FileNotFoundError:
        return 0
    _private_dir(extracted_root)
    removed = 0
    prefix = f".{digest}."
    for candidate in sorted(extracted_root.iterdir(), key=lambda item: item.name):
        if not candidate.name.startswith(prefix):
            continue
        _discard_private_staging(candidate)
        removed += 1
    return removed


def _intake_observation(
    root: Path,
    state: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    removed = _discard_intake_staging(root, state["source"]["sha256"])
    return {
        "raw": _observe_raw(root, state),
        "extraction": _observe_extraction(root, state, manifest),
        "abandoned_staging_trees_removed": removed,
    }


def _write_intake_outcome(
    path: Path,
    state: dict[str, Any],
    outcome: str,
    detail: str,
    observation: dict[str, Any],
) -> dict[str, Any]:
    if outcome not in INTAKE_STATES:
        raise ArtifactStoreError("intake outcome is unsupported")
    updated = {
        **state,
        "updated_at": _now(),
        "state": outcome,
        "detail": _safe_text(detail),
        "observation": observation,
    }
    _atomic_json(path, updated)
    return updated


def _prior_content_ids(root: Path, digest: str) -> list[str]:
    intake = root / "manifests" / "intake"
    if not intake.exists():
        return []
    _private_dir(intake)
    result: list[str] = []
    for path in sorted(intake.iterdir(), key=lambda item: item.name):
        if path.suffix != ".json":
            continue
        manifest = _load_json(path)
        source = manifest.get("source")
        if (
            isinstance(source, dict)
            and source.get("sha256") == digest
            and isinstance(manifest.get("artifact_id"), str)
        ):
            result.append(manifest["artifact_id"])
    return result


def _discard_private_staging(path: Path) -> None:
    """Remove only a helper-created private staging tree, without following links."""
    try:
        path.lstat()
    except FileNotFoundError:
        return
    _private_dir(path)
    for current_root, directories, files in os.walk(path, topdown=False, followlinks=False):
        current = Path(current_root)
        for name in files:
            child = current / name
            info = child.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise ArtifactStoreError("private extraction staging contains an unexpected entry")
            child.unlink()
        for name in directories:
            child = current / name
            info = child.lstat()
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise ArtifactStoreError("private extraction staging contains an unexpected entry")
            child.rmdir()
    path.rmdir()


def _validate_extraction_tree(root: Path, destination: Path, results: list[dict[str, Any]]) -> None:
    expected_paths = {item["stored_path"] for item in results}
    destination_relative = destination.relative_to(root)
    for item in results:
        path = PurePosixPath(item["stored_path"])
        for parent in path.parents:
            if parent == PurePosixPath(destination_relative.as_posix()):
                break
            expected_paths.add(parent.as_posix())
    observed_paths: set[str] = set()
    _private_dir(destination)
    for current_root, directories, files in os.walk(destination, followlinks=False):
        current = Path(current_root)
        for name in directories:
            child = current / name
            _private_dir(child)
            observed_paths.add(child.relative_to(root).as_posix())
        for name in files:
            child = current / name
            relative = child.relative_to(root).as_posix()
            expected = next((item for item in results if item["stored_path"] == relative), None)
            if expected is None or expected["kind"] != "FILE":
                raise ArtifactStoreError("existing extraction contains an unexpected entry")
            snapshot = _read_exact_file(child, expected["expanded_bytes"] + 1)
            if snapshot.size != expected["expanded_bytes"] or snapshot.sha256 != expected["sha256"]:
                raise ArtifactStoreError("existing extracted member failed identity verification")
            if stat.S_IMODE(child.lstat().st_mode) != 0o400:
                raise ArtifactStoreError("existing extracted member is not private and read-only")
            observed_paths.add(relative)
    if observed_paths != expected_paths:
        raise ArtifactStoreError("existing extraction does not match the archive inventory")


def _validate_intended_extraction_tree(
    root: Path,
    destination: Path,
    inventory: dict[str, Any],
) -> None:
    """Verify an interrupted extraction against the durable pre-publication inventory."""
    members = inventory.get("members") if isinstance(inventory, dict) else None
    if not isinstance(members, list):
        raise ArtifactStoreError("intake archive inventory is malformed")
    destination_relative = destination.relative_to(root)
    expected: dict[str, dict[str, Any]] = {}
    expected_paths: set[str] = set()
    for item in members:
        if not isinstance(item, dict):
            raise ArtifactStoreError("intake archive member inventory is malformed")
        name = item.get("path")
        kind = item.get("kind")
        expanded = item.get("expanded_bytes")
        crc32 = item.get("crc32")
        if (
            not isinstance(name, str)
            or kind not in {"FILE", "DIRECTORY"}
            or isinstance(expanded, bool)
            or not isinstance(expanded, int)
            or expanded < 0
            or not isinstance(crc32, str)
            or not re.fullmatch(r"[0-9a-f]{8}", crc32)
        ):
            raise ArtifactStoreError("intake archive member inventory is malformed")
        relative = (destination_relative / PurePosixPath(name)).as_posix()
        if relative in expected:
            raise ArtifactStoreError("intake archive inventory contains a duplicate destination")
        expected[relative] = item
        expected_paths.add(relative)
        for parent in PurePosixPath(relative).parents:
            if parent == PurePosixPath(destination_relative.as_posix()):
                break
            expected_paths.add(parent.as_posix())
    observed_paths: set[str] = set()
    _private_dir(destination)
    for current_root, directories, files in os.walk(destination, followlinks=False):
        current = Path(current_root)
        for name in directories:
            child = current / name
            _private_dir(child)
            relative = child.relative_to(root).as_posix()
            explicit = expected.get(relative)
            if explicit is not None and explicit["kind"] != "DIRECTORY":
                raise ArtifactStoreError("interrupted extraction member type changed")
            observed_paths.add(relative)
        for name in files:
            child = current / name
            relative = child.relative_to(root).as_posix()
            metadata = expected.get(relative)
            if metadata is None or metadata["kind"] != "FILE":
                raise ArtifactStoreError("interrupted extraction contains an unexpected file")
            snapshot = _read_exact_file(child, metadata["expanded_bytes"] + 1)
            actual_crc = f"{binascii.crc32(snapshot.data) & 0xFFFFFFFF:08x}"
            if snapshot.size != metadata["expanded_bytes"] or actual_crc != metadata["crc32"]:
                raise ArtifactStoreError("interrupted extraction member failed identity verification")
            if stat.S_IMODE(child.lstat().st_mode) != 0o400:
                raise ArtifactStoreError("interrupted extraction member is not private and read-only")
            observed_paths.add(relative)
    if observed_paths != expected_paths:
        raise ArtifactStoreError("interrupted extraction does not match its durable inventory")


def _extract_members(root: Path, archive_digest: str, data: bytes, inventory: dict[str, Any], limits: Limits) -> list[dict[str, Any]]:
    extracted_root = _ensure_area(root, "raw/extracted")
    destination_root = extracted_root / archive_digest
    staging_root = Path(tempfile.mkdtemp(prefix=f".{archive_digest}.", dir=extracted_root))
    os.chmod(staging_root, 0o700)
    expected = {item["path"]: item for item in inventory["members"]}
    results: list[dict[str, Any]] = []
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
        with archive:
            for info in sorted(archive.infolist(), key=lambda item: _safe_member_name(item)[0]):
                name, is_directory = _safe_member_name(info)
                metadata = expected[name]
                staging_target = staging_root.joinpath(*name.split("/"))
                final_target = destination_root.joinpath(*name.split("/"))
                if is_directory:
                    _ensure_area(staging_root, name)
                    results.append({**metadata, "sha256": None, "stored_path": final_target.relative_to(root).as_posix()})
                    continue
                _ensure_area(staging_root, "/".join(name.split("/")[:-1])) if "/" in name else None
                with archive.open(info, "r") as member:
                    payload = member.read(limits.max_file_bytes + 1)
                    if member.read(1):
                        raise ArtifactStoreError("archive member exceeds its validated size")
                if len(payload) != info.file_size or len(payload) > limits.max_file_bytes:
                    raise ArtifactStoreError("archive member size disagrees with validated metadata")
                digest = hashlib.sha256(payload).hexdigest()
                _write_exclusive(staging_target, payload, mode=0o400)
                results.append({**metadata, "sha256": digest, "stored_path": final_target.relative_to(root).as_posix()})
        if destination_root.exists():
            _validate_extraction_tree(root, destination_root, results)
            _discard_private_staging(staging_root)
        else:
            os.rename(staging_root, destination_root)
            _fsync_dir(extracted_root)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise ArtifactStoreError("archive extraction failed after metadata validation") from exc
    finally:
        if staging_root.exists():
            _discard_private_staging(staging_root)
    return results


def ingest_snapshot(
    run_root: Path,
    run_id: str,
    artifact_id: str,
    snapshot: Snapshot,
    provenance: Provenance,
    *,
    kind: str,
    limits: Limits,
    after_raw_hook: Callable[[Path, bool], None] | None = None,
    after_extract_hook: Callable[[Path], None] | None = None,
    after_manifest_hook: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    _safe_id(artifact_id, "artifact_id")
    provenance.validate()
    limits.validate()
    root = _open_store(run_root, run_id)
    if snapshot.size > limits.max_source_bytes:
        raise ArtifactStoreError("artifact exceeds the configured source-byte limit")
    archive_inventory: dict[str, Any] | None = None
    if kind == "ZIP":
        # Complete archive inspection deliberately precedes raw publication and
        # any member extraction.
        archive_inventory = inspect_zip_bytes(snapshot.data, limits)
    elif kind != "FILE":
        raise ArtifactStoreError("artifact kind is unsupported")
    with _intake_lock(root):
        intake = _ensure_area(root, "manifests/intake")
        manifest_path = intake / f"{artifact_id}.json"
        state_path = _intake_state_path(root, artifact_id)
        if manifest_path.exists() or state_path.exists():
            raise ArtifactStoreError("artifact_id already has an intake transaction; reconcile it before reuse")
        expected_raw = f"raw/sha256/{snapshot.sha256[:2]}/{snapshot.sha256}"
        expected_extraction = f"raw/extracted/{snapshot.sha256}" if kind == "ZIP" else None
        source_record = {
            **asdict(provenance),
            "size_bytes": snapshot.size,
            "sha256": snapshot.sha256,
        }
        created_at = _now()
        state = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "artifact_id": artifact_id,
            "created_at": created_at,
            "updated_at": created_at,
            "state": "INTENT",
            "detail": "publication intent recorded before raw or extracted bytes",
            "kind": kind,
            "source": source_record,
            "archive_inventory": archive_inventory,
            "expected": {
                "raw_stored_path": expected_raw,
                "raw_preexisting": root.joinpath(*PurePosixPath(expected_raw).parts).exists(),
                "extraction_root": expected_extraction,
                "extraction_preexisting": bool(
                    expected_extraction
                    and root.joinpath(*PurePosixPath(expected_extraction).parts).exists()
                ),
            },
            "observation": {},
        }
        _atomic_json(state_path, state)
        try:
            prior = _prior_content_ids(root, snapshot.sha256)
            raw_path, reused = _store_blob(root, snapshot)
            if after_raw_hook is not None:
                after_raw_hook(raw_path, reused)
            archive: dict[str, Any] | None = None
            if kind == "ZIP":
                assert archive_inventory is not None
                archive = {
                    **archive_inventory,
                    "members": _extract_members(root, snapshot.sha256, snapshot.data, archive_inventory, limits),
                }
                if after_extract_hook is not None:
                    after_extract_hook(root / f"raw/extracted/{snapshot.sha256}")
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "artifact_id": artifact_id,
                "recorded_at": _now(),
                "source": source_record,
                "raw": {
                    "stored_path": raw_path.relative_to(root).as_posix(),
                    "immutable_mode": "0400",
                    "content_reused": reused,
                    "same_content_artifact_ids": prior,
                },
                "archive": archive,
            }
            _atomic_json(manifest_path, manifest)
            if after_manifest_hook is not None:
                after_manifest_hook(manifest_path)
            observation = _intake_observation(root, state, manifest)
            _write_intake_outcome(state_path, state, "COMMITTED", "intake manifest committed", observation)
            return manifest
        except Exception as exc:
            try:
                observation = _intake_observation(root, state)
                failure_outcome = "OUTCOME_UNKNOWN_RETAINED" if manifest_path.exists() else "REJECTED_RETAINED"
                _write_intake_outcome(
                    state_path,
                    state,
                    failure_outcome,
                    f"intake stopped before transaction completion: {type(exc).__name__}",
                    observation,
                )
            except ArtifactStoreError:
                # The immutable INTENT is still durable lineage if outcome
                # observation itself cannot be persisted safely.
                pass
            raise


def reconcile_intake(run_root: Path, run_id: str, artifact_id: str) -> dict[str, Any]:
    """Reconcile a committed, rejected, or interrupted intake transaction."""
    _safe_id(artifact_id, "artifact_id")
    root = _open_store(run_root, run_id)
    with _intake_lock(root):
        state_path = _intake_state_path(root, artifact_id)
        state = _load_json(state_path)
        _validate_intake_state(state, run_id, artifact_id)
        manifest_path = _ensure_area(root, "manifests/intake") / f"{artifact_id}.json"
        manifest = _load_json(manifest_path) if manifest_path.exists() else None
        observation = _intake_observation(root, state, manifest)
        if observation["raw"] == "IDENTITY_CHANGED" or observation["extraction"] == "IDENTITY_CHANGED":
            raise ArtifactStoreError("intake transaction bytes failed identity reconciliation")
        if manifest is not None:
            source = manifest.get("source")
            raw = manifest.get("raw")
            if (
                manifest.get("schema_version") != SCHEMA_VERSION
                or manifest.get("run_id") != run_id
                or manifest.get("artifact_id") != artifact_id
                or not isinstance(source, dict)
                or source.get("sha256") != state["source"]["sha256"]
                or source.get("size_bytes") != state["source"]["size_bytes"]
                or not isinstance(raw, dict)
                or raw.get("stored_path") != state["expected"]["raw_stored_path"]
                or observation["raw"] != "EXACT"
                or observation["extraction"] not in {"EXACT", "NOT_APPLICABLE"}
            ):
                raise ArtifactStoreError("committed intake manifest failed transaction reconciliation")
            outcome = "COMMITTED"
            detail = "committed manifest and stored bytes reconciled"
        elif state["state"] == "REJECTED_RETAINED":
            outcome = "REJECTED_RETAINED"
            detail = "rejected intake remains durably attributed and retained"
        elif observation["raw"] == "MISSING" and observation["extraction"] in {"MISSING", "NOT_APPLICABLE"}:
            outcome = "DEFINITELY_NOT_PUBLISHED"
            detail = "no intended raw or extracted bytes are present"
        else:
            outcome = "OUTCOME_UNKNOWN_RETAINED"
            detail = "interrupted intake bytes are retained under durable intent for review"
        return _write_intake_outcome(state_path, state, outcome, detail, observation)


def ingest_path(
    run_root: Path,
    run_id: str,
    artifact_id: str,
    source: Path,
    provenance: Provenance,
    *,
    kind: str,
    limits: Limits,
    after_read_hook: Callable[[], None] | None = None,
) -> dict[str, Any]:
    snapshot = _read_exact_file(source, limits.max_source_bytes, after_read_hook=after_read_hook)
    return ingest_snapshot(run_root, run_id, artifact_id, snapshot, provenance, kind=kind, limits=limits)


def ingest_base64_path(
    run_root: Path,
    run_id: str,
    artifact_id: str,
    source: Path,
    provenance: Provenance,
    *,
    limits: Limits,
) -> dict[str, Any]:
    if provenance.source_kind != "BASE64_RECOVERY":
        raise ArtifactStoreError("base64 intake requires BASE64_RECOVERY provenance")
    encoded = _read_exact_file(source, limits.max_base64_bytes)
    try:
        compact = b"".join(encoded.data.split())
        decoded = base64.b64decode(compact, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ArtifactStoreError("base64 recovery input is malformed") from exc
    if len(decoded) > limits.max_file_bytes or len(decoded) > limits.max_source_bytes:
        raise ArtifactStoreError("decoded base64 artifact exceeds the configured byte limit")
    snapshot = Snapshot(decoded, len(decoded), hashlib.sha256(decoded).hexdigest())
    return ingest_snapshot(run_root, run_id, artifact_id, snapshot, provenance, kind="FILE", limits=limits)


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return candidate != root
    except ValueError:
        return False


def _cleanup_identity(root: Path, target: Path) -> dict[str, Any]:
    target = _canonical_path(target)
    if not _inside(root, target):
        raise ArtifactStoreError("cleanup target is outside the run-owned root")
    relative = target.relative_to(root)
    if not relative.parts or relative.parts[0] not in CLEANABLE_AREAS:
        raise ArtifactStoreError("cleanup target is not in an eligible run-owned area")
    snapshot = _read_exact_file(target, 1024 * 1024 * 1024, require_single_link=True)
    info = target.lstat()
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise ArtifactStoreError("cleanup target has a different owner")
    return {
        "path": relative.as_posix(),
        "size_bytes": snapshot.size,
        "sha256": snapshot.sha256,
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def plan_cleanup(
    run_root: Path,
    run_id: str,
    plan_id: str,
    targets: Iterable[Path],
    *,
    reason: str,
    authorization_state: str,
    authorization_reference: str | None,
) -> dict[str, Any]:
    _safe_id(plan_id, "plan_id")
    _bounded_label(reason, "reason", 500)
    if authorization_state not in AUTHORIZATION_STATES:
        raise ArtifactStoreError("authorization_state is unsupported")
    if authorization_state == "AUTHORIZED_EXACT_MANIFEST":
        _bounded_label(authorization_reference or "", "authorization_reference", 500)
    elif authorization_reference:
        raise ArtifactStoreError("pending cleanup must not claim an authorization reference")
    root = _open_store(run_root, run_id)
    with _cleanup_lock(root):
        identities = [_cleanup_identity(root, Path(target)) for target in targets]
        if not identities:
            raise ArtifactStoreError("cleanup plan must contain at least one exact target")
        paths = [item["path"] for item in identities]
        if len(paths) != len(set(paths)):
            raise ArtifactStoreError("cleanup plan contains a duplicate target")
        identities.sort(key=lambda item: item["path"])
        cleanup_dir = _ensure_area(root, "manifests/cleanup")
        plan_path = cleanup_dir / f"{plan_id}.json"
        plan = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "plan_id": plan_id,
            "created_at": _now(),
            "reason": reason,
            "authorization_state": authorization_state,
            "authorization_reference": authorization_reference,
            "total_bytes": sum(item["size_bytes"] for item in identities),
            "targets": identities,
        }
        _exclusive_json(plan_path, plan)
        return plan


def _validate_plan(root: Path, run_id: str, plan_id: str) -> tuple[Path, dict[str, Any]]:
    _safe_id(plan_id, "plan_id")
    plan_path = root / "manifests" / "cleanup" / f"{plan_id}.json"
    plan = _load_json(plan_path)
    required = {
        "schema_version", "run_id", "plan_id", "created_at", "reason",
        "authorization_state", "authorization_reference", "total_bytes", "targets",
    }
    if set(plan) != required or plan.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactStoreError("cleanup plan has an unsupported schema")
    if plan.get("run_id") != run_id or plan.get("plan_id") != plan_id:
        raise ArtifactStoreError("cleanup plan does not match the requested run and plan")
    if plan.get("authorization_state") != "AUTHORIZED_EXACT_MANIFEST":
        raise ArtifactStoreError("cleanup plan lacks explicit exact-manifest authorization")
    _bounded_label(plan.get("authorization_reference", ""), "authorization_reference", 500)
    targets = plan.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ArtifactStoreError("cleanup plan targets are malformed")
    paths = [_validate_cleanup_record(record) for record in targets]
    if len(paths) != len(set(paths)):
        raise ArtifactStoreError("cleanup plan contains duplicate targets")
    total = plan.get("total_bytes")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ArtifactStoreError("cleanup plan total is malformed")
    if total != sum(record["size_bytes"] for record in targets):
        raise ArtifactStoreError("cleanup plan total does not match its targets")
    return plan_path, plan


def _validate_cleanup_record(record: Any) -> str:
    if not isinstance(record, dict) or set(record) != {"path", "size_bytes", "sha256", "device", "inode"}:
        raise ArtifactStoreError("cleanup target record has an unsupported schema")
    relative = record.get("path")
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or PurePosixPath(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in PurePosixPath(relative).parts)
    ):
        raise ArtifactStoreError("cleanup target path is malformed")
    for field in ("size_bytes", "device", "inode"):
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ArtifactStoreError("cleanup target identity is malformed")
    digest = record.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ArtifactStoreError("cleanup target hash is malformed")
    return relative


def _matches_identity(root: Path, record: dict[str, Any]) -> tuple[Path, bool]:
    relative = _validate_cleanup_record(record)
    candidate = root / PurePosixPath(relative)
    try:
        actual = _cleanup_identity(root, candidate)
    except ArtifactStoreError:
        return candidate, False
    return candidate, actual == record


def _initial_cleanup_state(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": plan["run_id"],
        "plan_id": plan["plan_id"],
        "updated_at": _now(),
        "outcomes": [
            {
                "path": record["path"],
                "quarantine_path": _quarantine_relative(plan["plan_id"], index, record),
                "outcome": "PENDING",
                "detail": "not attempted",
            }
            for index, record in enumerate(plan["targets"])
        ],
    }


def _quarantine_relative(plan_id: str, index: int, record: dict[str, Any]) -> str:
    return f"manifests/cleanup/quarantine/{plan_id}/{index:04d}-{record['sha256']}"


def _validate_cleanup_state(state: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    required = {"schema_version", "run_id", "plan_id", "updated_at", "outcomes"}
    if set(state) != required or state.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactStoreError("cleanup state has an unsupported schema")
    if state.get("run_id") != plan["run_id"] or state.get("plan_id") != plan["plan_id"]:
        raise ArtifactStoreError("cleanup state does not match the plan")
    outcomes = state.get("outcomes")
    if not isinstance(outcomes, list):
        raise ArtifactStoreError("cleanup state outcomes are malformed")
    allowed = {
        "PENDING", "OUTCOME_UNKNOWN", "QUARANTINED", "QUARANTINED_RECONCILED",
        "QUARANTINED_IDENTITY_CHANGED", "RETAINED_RECONCILED",
        "BLOCKED_IDENTITY_CHANGED", "BLOCKED_ARTIFACT_MISSING",
    }
    records = {record["path"]: (index, record) for index, record in enumerate(plan["targets"])}
    for item in outcomes:
        if not isinstance(item, dict) or set(item) != {"path", "quarantine_path", "outcome", "detail"}:
            raise ArtifactStoreError("cleanup state outcome has an unsupported schema")
        if (
            not isinstance(item["path"], str)
            or item["path"] not in records
            or item["outcome"] not in allowed
            or not isinstance(item["detail"], str)
        ):
            raise ArtifactStoreError("cleanup state outcome is malformed")
        index, record = records[item["path"]]
        if item.get("quarantine_path") != _quarantine_relative(plan["plan_id"], index, record):
            raise ArtifactStoreError("cleanup state quarantine path is malformed")
    expected = {record["path"] for record in plan["targets"]}
    observed = [item["path"] for item in outcomes]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ArtifactStoreError("cleanup state does not match the plan")
    return outcomes


def _quarantine_match(root: Path, record: dict[str, Any], relative: str) -> str:
    """Return EXACT, CHANGED, or MISSING without blocking on special files."""
    path = root.joinpath(*PurePosixPath(relative).parts)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "MISSING"
    except OSError:
        return "CHANGED"
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_nlink != 1:
        return "CHANGED"
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        return "CHANGED"
    try:
        snapshot = _read_exact_file(path, record["size_bytes"] + 1, require_single_link=True)
    except ArtifactStoreError:
        return "CHANGED"
    actual = {
        "path": record["path"],
        "size_bytes": snapshot.size,
        "sha256": snapshot.sha256,
        "device": info.st_dev,
        "inode": info.st_ino,
    }
    return "EXACT" if actual == record else "CHANGED"


def apply_cleanup(
    run_root: Path,
    run_id: str,
    plan_id: str,
    *,
    after_unlink_hook: Callable[[Path], None] | None = None,
    after_intent_hook: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    """Move authorized bytes into private quarantine without irreversible deletion."""
    root = _open_store(run_root, run_id)
    with _cleanup_lock(root):
        _, plan = _validate_plan(root, run_id, plan_id)
        state_path = root / "manifests" / "cleanup" / f"{plan_id}.state.json"
        if state_path.exists():
            state = _load_json(state_path)
            outcomes = _validate_cleanup_state(state, plan)
            if any(item["outcome"] == "OUTCOME_UNKNOWN" for item in outcomes):
                raise ArtifactStoreError("cleanup has OUTCOME_UNKNOWN state; reconcile before continuing")
        else:
            state = _initial_cleanup_state(plan)
            _exclusive_json(state_path, state)
            outcomes = _validate_cleanup_state(state, plan)
        records = {record["path"]: record for record in plan["targets"]}
        for outcome in outcomes:
            current_outcome = outcome["outcome"]
            if current_outcome in {"RETAINED_RECONCILED", "BLOCKED_IDENTITY_CHANGED", "BLOCKED_ARTIFACT_MISSING"}:
                raise ArtifactStoreError("reconciled cleanup requires a new exact plan before any retry")
            if current_outcome in TERMINAL_CLEANUP_STATES:
                record = records[outcome["path"]]
                target = root.joinpath(*PurePosixPath(record["path"]).parts)
                if target.exists() or target.is_symlink():
                    raise ArtifactStoreError("completed cleanup postcondition no longer holds")
                quarantine_state = _quarantine_match(root, record, outcome["quarantine_path"])
                if current_outcome in {"QUARANTINED", "QUARANTINED_RECONCILED"} and quarantine_state != "EXACT":
                    raise ArtifactStoreError("quarantined cleanup bytes changed after completion")
                if current_outcome == "QUARANTINED_IDENTITY_CHANGED" and quarantine_state == "MISSING":
                    raise ArtifactStoreError("changed quarantined artifact is missing")
        # Validate the whole exact manifest before moving any target.
        for outcome in outcomes:
            if outcome["outcome"] in TERMINAL_CLEANUP_STATES:
                continue
            _, matches = _matches_identity(root, records[outcome["path"]])
            if not matches:
                raise ArtifactStoreError("cleanup target identity changed after planning; target preserved")
        quarantine_dir = _ensure_area(root, f"manifests/cleanup/quarantine/{plan_id}")
        for outcome in outcomes:
            if outcome["outcome"] in TERMINAL_CLEANUP_STATES:
                continue
            record = records[outcome["path"]]
            target, matches = _matches_identity(root, record)
            if not matches:
                raise ArtifactStoreError("cleanup target identity changed immediately before quarantine; target preserved")
            quarantine = root.joinpath(*PurePosixPath(outcome["quarantine_path"]).parts)
            if quarantine.parent != quarantine_dir or quarantine.exists() or quarantine.is_symlink():
                raise ArtifactStoreError("cleanup quarantine destination is not empty")
            outcome["outcome"] = "OUTCOME_UNKNOWN"
            outcome["detail"] = "quarantine move authorized; postcondition not yet reconciled"
            state["updated_at"] = _now()
            _atomic_json(state_path, state)
            if after_intent_hook is not None:
                after_intent_hook(target)
            # Rehash after intent. A FIFO or same-inode rewrite is rejected by
            # nonblocking descriptor validation and remains at its source path.
            _, matches = _matches_identity(root, record)
            if not matches:
                outcome["outcome"] = "BLOCKED_IDENTITY_CHANGED"
                outcome["detail"] = "source changed after cleanup intent; preserved without moving"
                state["updated_at"] = _now()
                _atomic_json(state_path, state)
                return state
            try:
                os.rename(target, quarantine)
                _fsync_dir(target.parent)
                _fsync_dir(quarantine_dir)
            except OSError as exc:
                raise ArtifactStoreError("cleanup quarantine move failed; outcome requires reconciliation") from exc
            # The historical hook name remains for deterministic interrupted-
            # transaction tests; the action is now a recoverable rename, not unlink.
            if after_unlink_hook is not None:
                after_unlink_hook(target)
            if target.exists() or target.is_symlink():
                raise ArtifactStoreError("cleanup source still exists after quarantine move")
            quarantine_state = _quarantine_match(root, record, outcome["quarantine_path"])
            if quarantine_state == "EXACT":
                outcome["outcome"] = "QUARANTINED"
                outcome["detail"] = "exact approved bytes moved to private recoverable quarantine"
            else:
                outcome["outcome"] = "QUARANTINED_IDENTITY_CHANGED"
                outcome["detail"] = "moved entry differs from approved bytes and was preserved in quarantine"
            state["updated_at"] = _now()
            _atomic_json(state_path, state)
            if quarantine_state != "EXACT":
                return state
        return state


def reconcile_cleanup(run_root: Path, run_id: str, plan_id: str) -> dict[str, Any]:
    root = _open_store(run_root, run_id)
    with _cleanup_lock(root):
        _, plan = _validate_plan(root, run_id, plan_id)
        state_path = root / "manifests" / "cleanup" / f"{plan_id}.state.json"
        state = _load_json(state_path)
        records = {record["path"]: record for record in plan["targets"]}
        outcomes = _validate_cleanup_state(state, plan)
        for outcome in outcomes:
            if outcome["outcome"] != "OUTCOME_UNKNOWN":
                continue
            record = records[outcome["path"]]
            target = root.joinpath(*PurePosixPath(record["path"]).parts)
            target_present = target.exists() or target.is_symlink()
            quarantine_state = _quarantine_match(root, record, outcome["quarantine_path"])
            if not target_present and quarantine_state == "EXACT":
                outcome["outcome"] = "QUARANTINED_RECONCILED"
                outcome["detail"] = "exact approved bytes are present in private recoverable quarantine"
            elif not target_present and quarantine_state == "CHANGED":
                outcome["outcome"] = "QUARANTINED_IDENTITY_CHANGED"
                outcome["detail"] = "quarantined entry differs from approved bytes and was preserved"
            elif target_present and quarantine_state == "MISSING":
                _, matches = _matches_identity(root, record)
                if matches:
                    outcome["outcome"] = "RETAINED_RECONCILED"
                    outcome["detail"] = "original target remains; a new plan is required before retry"
                else:
                    outcome["outcome"] = "BLOCKED_IDENTITY_CHANGED"
                    outcome["detail"] = "source path changed and was preserved without moving"
            else:
                outcome["outcome"] = "BLOCKED_ARTIFACT_MISSING"
                outcome["detail"] = "cleanup postcondition is ambiguous; no deletion is claimed"
        state["updated_at"] = _now()
        _atomic_json(state_path, state)
        return state


def _limits_from(args: argparse.Namespace) -> Limits:
    return Limits(
        max_members=args.max_members,
        max_source_bytes=args.max_source_bytes,
        max_compressed_bytes=args.max_compressed_bytes,
        max_expanded_bytes=args.max_expanded_bytes,
        max_ratio=args.max_ratio,
        max_file_bytes=args.max_file_bytes,
        max_base64_bytes=args.max_base64_bytes,
    )


def _add_limits(parser: argparse.ArgumentParser) -> None:
    defaults = Limits()
    parser.add_argument("--max-members", type=int, default=defaults.max_members)
    parser.add_argument("--max-source-bytes", type=int, default=defaults.max_source_bytes)
    parser.add_argument("--max-compressed-bytes", type=int, default=defaults.max_compressed_bytes)
    parser.add_argument("--max-expanded-bytes", type=int, default=defaults.max_expanded_bytes)
    parser.add_argument("--max-ratio", type=int, default=defaults.max_ratio)
    parser.add_argument("--max-file-bytes", type=int, default=defaults.max_file_bytes)
    parser.add_argument("--max-base64-bytes", type=int, default=defaults.max_base64_bytes)


def _add_store(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)


def _add_provenance(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-kind", choices=sorted(SOURCE_KINDS), required=True)
    parser.add_argument("--lane-id", required=True)
    parser.add_argument("--conversation-id", required=True)


def _parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="initialize one private run-owned store")
    _add_store(initialize)
    inspect = commands.add_parser("inspect-zip", help="inspect a ZIP without extracting it")
    inspect.add_argument("--source", type=Path, required=True)
    _add_limits(inspect)
    for name in ("ingest-file", "ingest-zip", "ingest-base64"):
        ingest = commands.add_parser(name, help=f"run-scoped {name.replace('-', ' ')}")
        _add_store(ingest)
        _add_provenance(ingest)
        ingest.add_argument("--source", type=Path, required=True)
        _add_limits(ingest)
    plan = commands.add_parser("plan-cleanup", help="create one exact hash-bound cleanup plan")
    _add_store(plan)
    plan.add_argument("--plan-id", required=True)
    plan.add_argument("--target", type=Path, action="append", required=True)
    plan.add_argument("--reason", required=True)
    plan.add_argument("--authorization-state", choices=sorted(AUTHORIZATION_STATES), required=True)
    plan.add_argument("--authorization-reference")
    apply = commands.add_parser(
        "apply-cleanup",
        help="move exact authorized targets to recoverable private quarantine",
    )
    _add_store(apply)
    apply.add_argument("--plan-id", required=True)
    reconcile = commands.add_parser("reconcile-cleanup", help="reconcile interrupted cleanup state")
    _add_store(reconcile)
    reconcile.add_argument("--plan-id", required=True)
    intake_reconcile = commands.add_parser(
        "reconcile-intake", help="reconcile committed, rejected, or interrupted intake state"
    )
    _add_store(intake_reconcile)
    intake_reconcile.add_argument("--artifact-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = init_store(args.run_root, args.run_id)
        elif args.command == "inspect-zip":
            result = inspect_zip_path(args.source, _limits_from(args))
        elif args.command in {"ingest-file", "ingest-zip", "ingest-base64"}:
            provenance = Provenance(args.source_name, args.source_kind, args.lane_id, args.conversation_id)
            if args.command == "ingest-base64":
                result = ingest_base64_path(
                    args.run_root, args.run_id, args.artifact_id, args.source, provenance,
                    limits=_limits_from(args),
                )
            else:
                result = ingest_path(
                    args.run_root, args.run_id, args.artifact_id, args.source, provenance,
                    kind="ZIP" if args.command == "ingest-zip" else "FILE",
                    limits=_limits_from(args),
                )
        elif args.command == "plan-cleanup":
            result = plan_cleanup(
                args.run_root, args.run_id, args.plan_id, args.target,
                reason=args.reason,
                authorization_state=args.authorization_state,
                authorization_reference=args.authorization_reference,
            )
        elif args.command == "apply-cleanup":
            result = apply_cleanup(args.run_root, args.run_id, args.plan_id)
        elif args.command == "reconcile-cleanup":
            result = reconcile_cleanup(args.run_root, args.run_id, args.plan_id)
        else:
            result = reconcile_intake(args.run_root, args.run_id, args.artifact_id)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ArtifactStoreError as exc:
        print(f"artifact_store: error: {_safe_text(exc)}", file=sys.stderr)
        return 2
    except OSError:
        print("artifact_store: error: operating-system failure within the requested bounded path", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("artifact_store: interrupted; reconcile any pending intake or OUTCOME_UNKNOWN cleanup state", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
