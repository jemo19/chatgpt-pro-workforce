#!/usr/bin/env python3
"""Create a deterministic, safely inventoried skill release archive."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Callable
import unicodedata
import zipfile

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows branch
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX branch
    msvcrt = None


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SKILL_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"|?*')
_PUBLISHABLE_ROOT_FILES = frozenset({"SKILL.md", "LICENSE"})
_PUBLISHABLE_ROOT_DIRECTORIES = frozenset(
    {"agents", "assets", "references", "scripts"}
)


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _validate_skill_name(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 63
        or _SKILL_NAME_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("release skill name is invalid")
    return value


def _expected_skill_name(output: Path) -> str:
    if output.suffix != ".zip":
        raise ValueError("release output must be named <skill-name>.zip")
    return _validate_skill_name(output.stem)


def _validate_member_path(value: object, *, allow_root_directory: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("release member path must be a non-empty string")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"release member path is not NFC canonical: {value!r}")
    if "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"unsafe release member path: {value!r}")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or pure.as_posix() != value
        or not pure.parts
    ):
        raise ValueError(f"non-canonical release member path: {value!r}")
    for component in pure.parts:
        if (
            component in {"", ".", ".."}
            or component.endswith((" ", "."))
            or any(char in _WINDOWS_FORBIDDEN_CHARACTERS for char in component)
            or component.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_NAMES
        ):
            raise ValueError(f"non-portable release member path: {value!r}")
    if len(pure.parts) == 1:
        if value in _PUBLISHABLE_ROOT_DIRECTORIES and allow_root_directory:
            pass
        elif value not in _PUBLISHABLE_ROOT_FILES:
            raise ValueError(f"unexpected top-level release member: {value!r}")
    elif pure.parts[0] not in _PUBLISHABLE_ROOT_DIRECTORIES:
        raise ValueError(f"unexpected top-level release directory: {pure.parts[0]!r}")
    return value


def _portable_member_key(relative: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", component).casefold()
        for component in PurePosixPath(relative).parts
    )


def _validate_inventory_records(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ValueError("release file inventory must be a non-empty list")
    records: list[dict[str, object]] = []
    exact_names: set[str] = set()
    portable_names: set[str] = set()
    for record in value:
        if not isinstance(record, dict) or set(record) != {
            "path",
            "bytes",
            "sha256",
        }:
            raise ValueError("release file inventory contains a malformed record")
        relative = _validate_member_path(record.get("path"))
        byte_count = record.get("bytes")
        digest = record.get("sha256")
        if type(byte_count) is not int or byte_count < 0:  # bool is not a byte count
            raise ValueError("release file inventory contains an invalid byte count")
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            raise ValueError("release file inventory contains an invalid SHA-256")
        portable = _portable_member_key(relative)
        if relative in exact_names:
            raise ValueError("release file inventory contains a duplicate member path")
        if portable in portable_names:
            raise ValueError(
                "release file inventory contains ambiguous portable member paths"
            )
        exact_names.add(relative)
        portable_names.add(portable)
        records.append(record)
    paths = [str(record["path"]) for record in records]
    if paths != sorted(paths):
        raise ValueError("release file inventory is not in canonical path order")
    if not {"SKILL.md", "LICENSE", "agents/openai.yaml"}.issubset(exact_names):
        raise ValueError("release file inventory is missing required skill files")
    return records


def _load_manifest(data: bytes) -> object:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"release manifest contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("release manifest is invalid") from exc


def _reject_symlink_components(path: Path, *, label: str, include_leaf: bool) -> None:
    """Reject existing symlinks without following the user-supplied path."""
    absolute = _absolute_without_resolving(path)
    parts = absolute.parts
    limit = len(parts) if include_leaf else len(parts) - 1
    current = Path(parts[0])
    for component in parts[1:limit]:
        current /= component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError(f"{label} must not traverse a symbolic link")


def _prepare_output_path(raw_output: Path, skill: Path) -> Path:
    output = _absolute_without_resolving(raw_output)
    _reject_symlink_components(output, label="output path", include_leaf=True)
    resolved_output = output.resolve(strict=False)
    try:
        resolved_output.relative_to(skill)
    except ValueError:
        pass
    else:
        raise ValueError("output archive must be outside the skill source tree")
    output.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(output, label="output path", include_leaf=True)
    resolved_output = output.parent.resolve(strict=True) / output.name
    if _expected_skill_name(resolved_output) != skill.name:
        raise ValueError("release output name must match the skill directory name")
    for target in (
        resolved_output,
        resolved_output.with_suffix(".manifest.json"),
        resolved_output.with_suffix(resolved_output.suffix + ".sha256"),
    ):
        if target.is_symlink():
            raise ValueError("release output must not be a symbolic link")
        if target.exists():
            metadata = target.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ValueError("release output must be a single-link regular file")
    return resolved_output


def _read_stable_regular(path: Path, *, label: str) -> bytes:
    before = path.lstat()
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise ValueError(f"{label} must be a single-link regular file")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
        ):
            raise ValueError(f"{label} changed while opening")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise ValueError(f"{label} changed while reading")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _validate_publishable_shape(skill: Path) -> None:
    allowed_roots = _PUBLISHABLE_ROOT_FILES | _PUBLISHABLE_ROOT_DIRECTORIES
    children = {path.name for path in skill.iterdir()}
    unexpected = children - allowed_roots
    if unexpected:
        raise ValueError("skill contains an unexpected top-level entry")
    required = {"SKILL.md", "LICENSE", "agents"}
    if not required.issubset(children) or not (
        skill / "agents" / "openai.yaml"
    ).is_file():
        raise ValueError("skill must contain SKILL.md, LICENSE, and agents/openai.yaml")
    if any(
        (skill / directory).exists() and not (skill / directory).is_dir()
        for directory in _PUBLISHABLE_ROOT_DIRECTORIES
    ):
        raise ValueError("publishable skill resource roots must be directories")
    skill_text = _read_stable_regular(skill / "SKILL.md", label="SKILL.md")
    try:
        text = skill_text.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("SKILL.md must be UTF-8") from exc
    marker = f"name: {skill.name}"
    if not text.startswith("---\n") or marker not in text.split("---", 2)[1]:
        raise ValueError("SKILL.md frontmatter name must match its directory")


def inventory(skill: Path) -> list[dict[str, object]]:
    if skill.is_symlink() or not skill.is_dir():
        raise ValueError("skill source must be a regular directory, not a symlink")
    records: list[dict[str, object]] = []
    portable_names: set[str] = set()
    for path in sorted(skill.rglob("*")):
        mode = path.lstat().st_mode
        relative = path.relative_to(skill).as_posix()
        relative = _validate_member_path(
            relative, allow_root_directory=stat.S_ISDIR(mode)
        )
        pure = PurePosixPath(relative)
        if "__pycache__" in pure.parts or path.suffix in {".pyc", ".pyo"}:
            raise ValueError(f"generated bytecode is not publishable: {relative}")
        if stat.S_ISLNK(mode):
            raise ValueError(f"symlink is not allowed: {relative}")
        if path.is_dir():
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"special file is not allowed: {relative}")
        portable = _portable_member_key(relative)
        if portable in portable_names:
            raise ValueError("skill contains ambiguous portable member paths")
        portable_names.add(portable)
        data = _read_stable_regular(path, label=f"source member {relative}")
        records.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return _validate_inventory_records(records)


def _read_inventory_member(skill: Path, record: dict[str, object]) -> bytes:
    relative = str(record["path"])
    path = skill / relative
    before = path.lstat()
    data = _read_stable_regular(path, label=f"source member {relative}")
    after = path.lstat()
    digest = hashlib.sha256(data).hexdigest()
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != record["bytes"]
        or digest != record["sha256"]
    ):
        raise ValueError(f"source member changed after inventory: {relative}")
    return data


def write_archive(skill: Path, output: Path, records: list[dict[str, object]]) -> None:
    records = _validate_inventory_records(records)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for record in records:
                relative = str(record["path"])
                data = _read_inventory_member(skill, record)
                info = zipfile.ZipInfo(f"{skill.name}/{relative}", (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        with zipfile.ZipFile(temporary) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise ValueError(f"archive integrity failure at {bad}")
            expected_names = [f"{skill.name}/{record['path']}" for record in records]
            if archive.namelist() != expected_names:
                raise ValueError("archive member inventory does not match the source inventory")
            for record in records:
                member = f"{skill.name}/{record['path']}"
                data = archive.read(member)
                if (
                    len(data) != record["bytes"]
                    or hashlib.sha256(data).hexdigest() != record["sha256"]
                ):
                    raise ValueError(
                        f"archive member does not match inventory: {record['path']}"
                    )
        if inventory(skill) != records:
            raise ValueError("skill tree changed after inventory")
        descriptor = os.open(temporary, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, output)
        _fsync_directory(output.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _stage_bytes(parent: Path, prefix: str, content: bytes) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(prefix=prefix, dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return temporary
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _publication_lock(output: Path):
    lock_path = output.parent / f".{output.name}.release.lock"
    _reject_symlink_components(lock_path, label="release lock", include_leaf=True)
    if lock_path.is_symlink():
        raise ValueError("release lock must not be a symbolic link")
    descriptor = os.open(
        lock_path,
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("release lock must be a single-link regular file")
        if os.name == "posix" and (
            metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ValueError("release lock must be current-user owned with mode 0600")
        if fcntl is not None:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        elif msvcrt is not None:  # pragma: no cover - Windows branch
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:  # pragma: no cover - unsupported runtime
            raise ValueError("no supported release-lock implementation is available")
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - Windows branch
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(descriptor)


def _publish_transaction(
    staged: list[tuple[Path, Path]],
    verifier: Callable[[], object] | None = None,
) -> None:
    """Publish data first and an atomic manifest commit marker last."""
    backups: dict[Path, Path | None] = {}
    published: list[Path] = []
    preserve_backups = False
    try:
        for _source, target in staged:
            if target.is_symlink():
                raise ValueError("release output changed to a symbolic link")
            if target.exists():
                metadata = target.lstat()
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    raise ValueError("release output changed to a non-single-link file")
            backups[target] = (
                _stage_bytes(
                    target.parent,
                    f".{target.name}.backup.",
                    _read_stable_regular(target, label=f"existing release file {target.name}"),
                )
                if target.exists()
                else None
            )
        for source, target in staged:
            os.replace(source, target)
            published.append(target)
            _fsync_directory(target.parent)
        if verifier is not None:
            verifier()
    except Exception as publish_error:
        rollback_errors: list[OSError] = []
        for target in reversed(published):
            backup = backups.get(target)
            try:
                if backup is None:
                    target.unlink(missing_ok=True)
                else:
                    os.replace(backup, target)
                _fsync_directory(target.parent)
            except OSError as exc:
                rollback_errors.append(exc)
        if rollback_errors:
            preserve_backups = True
            retained = ", ".join(
                str(path) for path in backups.values() if path is not None and path.exists()
            )
            raise OSError(
                f"release publish failed and rollback was incomplete; backups retained: {retained}"
            ) from publish_error
        raise
    finally:
        for source, _target in staged:
            source.unlink(missing_ok=True)
        for backup in backups.values():
            if backup is not None and not preserve_backups:
                backup.unlink(missing_ok=True)


def write_release(
    skill: Path, output: Path, records: list[dict[str, object]]
) -> dict[str, object]:
    descriptor, staged_name = tempfile.mkstemp(
        prefix=f".{output.name}.staged.", dir=output.parent
    )
    os.close(descriptor)
    staged_archive = Path(staged_name)
    staged_archive.unlink()
    staged_files: list[Path] = [staged_archive]
    try:
        write_archive(skill, staged_archive, records)
        archive_bytes = staged_archive.read_bytes()
        archive_digest = hashlib.sha256(archive_bytes).hexdigest()
        manifest: dict[str, object] = {
            "schema_version": 2,
            "release_id": archive_digest,
            "skill": skill.name,
            "files": records,
            "archive": {
                "path": output.name,
                "bytes": len(archive_bytes),
                "sha256": archive_digest,
            },
        }
        manifest_path = output.with_suffix(".manifest.json")
        digest_path = output.with_suffix(output.suffix + ".sha256")
        staged_manifest = _stage_bytes(
            output.parent,
            f".{manifest_path.name}.staged.",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        staged_files.append(staged_manifest)
        staged_digest = _stage_bytes(
            output.parent,
            f".{digest_path.name}.staged.",
            f"{archive_digest}  {output.name}\n".encode("ascii"),
        )
        staged_files.append(staged_digest)
        with _publication_lock(output):
            _publish_transaction(
                [
                    (staged_archive, output),
                    (staged_digest, digest_path),
                    # The manifest is the commit marker. Readers hold the same
                    # lock and bind all checks to one captured byte set.
                    (staged_manifest, manifest_path),
                ],
                verifier=lambda: _verify_release_locked(output),
            )
        return manifest
    finally:
        for staged_file in staged_files:
            staged_file.unlink(missing_ok=True)


def _verify_release_locked(output: Path) -> dict[str, object]:
    manifest_path = output.with_suffix(".manifest.json")
    digest_path = output.with_suffix(output.suffix + ".sha256")
    for path in (output, manifest_path, digest_path):
        _reject_symlink_components(path, label="release file", include_leaf=True)
    first_manifest = _read_stable_regular(manifest_path, label="release manifest")
    archive_bytes = _read_stable_regular(output, label="release archive")
    digest_bytes = _read_stable_regular(digest_path, label="release digest")
    second_manifest = _read_stable_regular(manifest_path, label="release manifest")
    if first_manifest != second_manifest:
        raise ValueError("release changed while it was verified")
    manifest = _load_manifest(first_manifest)
    archive_digest = hashlib.sha256(archive_bytes).hexdigest()
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "release_id", "skill", "files", "archive"}
        or manifest.get("schema_version") != 2
        or manifest.get("release_id") != archive_digest
        or not isinstance(manifest.get("archive"), dict)
        or digest_bytes != f"{archive_digest}  {output.name}\n".encode("ascii")
    ):
        raise ValueError("release archive, digest, and manifest do not agree")
    expected_skill = _expected_skill_name(output)
    if _validate_skill_name(manifest.get("skill")) != expected_skill:
        raise ValueError("release manifest contains an unexpected skill name")
    archive_record = manifest["archive"]
    if (
        set(archive_record) != {"path", "bytes", "sha256"}
        or archive_record.get("path") != output.name
        or type(archive_record.get("bytes")) is not int
        or archive_record.get("bytes") != len(archive_bytes)
        or not isinstance(archive_record.get("sha256"), str)
        or _SHA256_PATTERN.fullmatch(archive_record["sha256"]) is None
        or archive_record["sha256"] != archive_digest
    ):
        raise ValueError("release archive record is malformed or does not agree")
    records = _validate_inventory_records(manifest.get("files"))
    # Validate the exact archive bytes already bound to the manifest rather
    # than reopening a path that another process could replace mid-check.
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            expected_names = [
                f"{expected_skill}/{record['path']}" for record in records
            ]
            infos = archive.infolist()
            if (
                archive.namelist() != expected_names
                or len(infos) != len(expected_names)
                or archive.testzip() is not None
            ):
                raise ValueError("release ZIP members do not match the manifest")
            for record, member, info in zip(records, expected_names, infos, strict=True):
                mode = (info.external_attr >> 16) & 0xFFFF
                if (
                    info.filename != info.orig_filename
                    or info.filename != member
                    or info.is_dir()
                    or info.flag_bits & 0x1
                    or info.create_system != 3
                    or stat.S_IFMT(mode) != stat.S_IFREG
                    or stat.S_IMODE(mode) != 0o644
                    or info.file_size != record["bytes"]
                ):
                    raise ValueError("release ZIP contains an unexpected entry type")
                data = archive.read(info)
                if (
                    len(data) != record["bytes"]
                    or hashlib.sha256(data).hexdigest() != record["sha256"]
                ):
                    raise ValueError("release ZIP member identity does not match the manifest")
    except (KeyError, NotImplementedError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ValueError("release ZIP is invalid or unsupported") from exc
    return manifest


def verify_release(output: Path) -> dict[str, object]:
    """Verify one coherent release generation under the writer lock."""
    with _publication_lock(output):
        return _verify_release_locked(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill", nargs="?", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify an existing archive/manifest/digest generation",
    )
    args = parser.parse_args()
    try:
        if args.verify_only:
            output = _absolute_without_resolving(args.output)
            _reject_symlink_components(output, label="release output", include_leaf=True)
            output = output.parent.resolve(strict=True) / output.name
            manifest = verify_release(output)
            archive_record = manifest["archive"]
            assert isinstance(archive_record, dict)
            print(f"ARCHIVE={output}")
            print(f"FILES={len(manifest['files'])}")
            print(f"BYTES={archive_record['bytes']}")
            print(f"SHA256={archive_record['sha256']}")
            return 0
        if args.skill is None:
            parser.error("skill is required unless --verify-only is used")
        supplied_skill = _absolute_without_resolving(args.skill)
        _reject_symlink_components(
            supplied_skill, label="skill source", include_leaf=True
        )
        skill = supplied_skill.resolve(strict=True)
        output = _prepare_output_path(args.output, skill)
        _validate_publishable_shape(skill)
        records = inventory(skill)
        manifest = write_release(skill, output, records)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"package error: {exc}", file=sys.stderr)
        return 2
    archive_record = manifest["archive"]
    assert isinstance(archive_record, dict)
    print(f"ARCHIVE={output}")
    print(f"FILES={len(records)}")
    print(f"BYTES={archive_record['bytes']}")
    print(f"SHA256={archive_record['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
