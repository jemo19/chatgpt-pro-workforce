#!/usr/bin/env python3
"""Create, update, and safely serve a local workforce status dashboard.

The dashboard root is always explicit.  Each run is stored below
``runs/<run-id>/`` with an HTML entry point and a bounded, public-only JSON
status document.  This module intentionally depends only on Python's standard
library.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import unquote_to_bytes, urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_JSON_BYTES = 512 * 1024
MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
MAX_STRING_LENGTH = 4096
MAX_ITEMS = 256
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")

RUN_STATES = {
    "DRAFT", "READY", "ACTIVE", "PAUSING", "PAUSED",
    "LIMIT_PAUSED", "RESUMING", "PARTIAL", "BLOCKED", "ACCEPTED",
    "REJECTED", "STOPPED", "SUPERSEDED",
}
ALLOCATION_PROFILES = {"PRO_HEAVY", "BALANCED", "CODEX_HEAVY", "LOCAL_ONLY"}
CODEX_USAGE_BANDS = {"LOWEST", "MODERATE", "HIGH", "CODEX_ONLY"}
ROUTES = {
    "FULL_BROWSER_AND_DESKTOP", "BROWSER_ONLY", "BROWSER_WITH_MANUAL_DESKTOP",
    "MANUAL_BROWSER_HANDOFF", "LOCAL_CODEX_ONLY", "BLOCKED", "UNKNOWN",
}
FRESHNESS_STATES = {"CURRENT", "STALE", "UNKNOWN"}
PROGRESS_STATES = {"OPEN", "ACTIVE", "COMPLETE", "BLOCKED", "UNKNOWN"}
LANE_STATES = {
    "PLANNED", "PREFLIGHTED", "SUBMITTED", "RUNNING", "RUNNING_HEALTHY",
    "RUNNING_WITH_TRANSIENT_ERROR", "SLOW_NO_FAILURE_EVIDENCE", "STALLED",
    "BROWSER_DISCONNECTED", "RETURNED", "TERMINAL_PARTIAL_ARTIFACT_RETURN",
    "TERMINAL_INCOMPLETE",
    "MECHANICAL_ACCEPTED", "MECHANICAL_REJECTED", "SEMANTIC_ACCEPTED",
    "SEMANTIC_REJECTED", "ACCEPTED", "REJECTED", "PARTIAL", "BLOCKED",
    "NOT_RECOVERABLE", "SUPERSEDED",
}
READINESS_STATES = {
    "AVAILABLE_VERIFIED", "AVAILABLE_UNTESTED", "NOT_AVAILABLE", "DEGRADED",
    "UNKNOWN", "NOT_AUTHORIZED", "DISABLED", "MISCONFIGURED",
}
ARTIFACT_STATES = {
    "EXPECTED", "RECOVERED", "RAW", "CANDIDATE", "ACCEPTED", "REJECTED",
    "DUPLICATE", "TEMPORARY", "NOT_RECOVERABLE", "UNKNOWN",
}
GATE_KINDS = {"MECHANICAL", "SEMANTIC", "INDEPENDENT"}
GATE_STATES = {"PENDING", "NOT_RUN", "PASS", "FAIL", "BLOCKED"}
DECISION_STATES = {
    "PENDING", "APPROVED", "DEFERRED", "REJECTED", "NOT_REQUIRED",
    "MANUAL_ACTION_REQUIRED",
}
SUMMARY_STATES = {"UNSET", "READY", "HEALTHY", "DEGRADED", "BLOCKED", "UNKNOWN"}
ALERT_LEVELS = {"info", "warning", "error"}

TOP_FIELDS = {
    "schema_version",
    "run",
    "progress",
    "lanes",
    "readiness",
    "artifacts",
    "gates",
    "decisions",
    "storage",
    "notes",
    "alerts",
}
RUN_FIELDS = {
    "id",
    "title",
    "status",
    "allocation_profile",
    "codex_usage_band",
    "route",
    "freshness",
    "updated_at",
    "next_action",
}
PROGRESS_FIELDS = {"id", "label", "current", "total", "state", "detail"}
LANE_FIELDS = {
    "id",
    "name",
    "state",
    "owner",
    "summary",
    "last_observed_at",
    "next_action",
}
READINESS_FIELDS = {"id", "label", "interface", "state", "detail"}
ARTIFACT_FIELDS = {"id", "name", "state", "size_bytes", "sha256"}
GATE_FIELDS = {"id", "label", "kind", "state", "detail"}
DECISION_FIELDS = {"id", "label", "state", "detail"}
STORAGE_FIELDS = {
    "state",
    "summary",
    "used_bytes",
    "budget_bytes",
    "artifact_count",
    "detail",
}
NOTES_FIELDS = {"state", "summary", "count", "updated_at", "detail"}
ALERT_FIELDS = {"level", "title", "detail"}

STRING_LIMITS = {
    "id": 128,
    "state": 64,
    "status": 64,
    "level": 32,
    "kind": 64,
    "interface": 128,
    "owner": 128,
    "allocation_profile": 64,
    "codex_usage_band": 64,
    "freshness": 64,
    "updated_at": 128,
    "last_observed_at": 128,
    "sha256": 64,
}


class DashboardError(ValueError):
    """A safe, user-facing dashboard validation error."""


def _safe_diagnostic(value: object, limit: int = 300) -> str:
    """Make an exception message bounded and inert when printed to a terminal."""
    text = str(value).encode("ascii", "backslashreplace").decode("ascii")
    text = "".join(char if 32 <= ord(char) < 127 else " " for char in text)
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


class SafeArgumentParser(argparse.ArgumentParser):
    """Argparse variant that cannot reflect terminal-control input."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"{_safe_diagnostic(self.prog, 120)}: error: {_safe_diagnostic(message)}\n",
        )


def _require_verified_file_security() -> None:
    # This implementation verifies Linux/POSIX uid, mode, symlink, hard-link,
    # and descriptor invariants. Windows DACLs and macOS ACLs are different
    # security models and are intentionally not claimed or guessed here.
    if os.name != "posix" or not sys.platform.startswith("linux"):
        raise DashboardError(
            "private dashboard file security is verified only on Linux/POSIX; "
            "Windows and macOS ACL enforcement is unverified"
        )


def _verify_private_stat(result: os.stat_result, *, directory: bool, label: str) -> None:
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_type(result.st_mode):
        raise DashboardError(f"{label} has an unexpected file type")
    if result.st_uid != os.geteuid():
        raise DashboardError(f"{label} is not owned by the current user")
    expected_mode = 0o700 if directory else 0o600
    if stat.S_IMODE(result.st_mode) != expected_mode:
        raise DashboardError(f"{label} must have mode {expected_mode:04o}")
    if not directory and result.st_nlink != 1:
        raise DashboardError(f"{label} must have exactly one hard link")


def _verify_private_path(path: Path, *, directory: bool, label: str) -> os.stat_result:
    try:
        result = path.lstat()
    except OSError as exc:
        raise DashboardError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(result.st_mode):
        raise DashboardError(f"{label} must not be a symbolic link")
    _verify_private_stat(result, directory=directory, label=label)
    return result


def _safe_run_id(value: str) -> str:
    if not SAFE_RUN_ID.fullmatch(value) or value in {".", ".."}:
        raise DashboardError(
            "run ID must be 1-128 ASCII letters, digits, dots, underscores, or "
            "hyphens; it must start and end with a letter or digit"
        )
    return value


def _is_path_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _root_fingerprint(root: Path) -> str:
    """Return a stable, non-secret identity for a resolved dashboard root."""
    return hashlib.sha256(os.fsencode(str(root.resolve(strict=True)))).hexdigest()


def _validate_dashboard_root(raw_root: str, *, create: bool) -> Path:
    _require_verified_file_security()
    if not raw_root or not raw_root.strip():
        raise DashboardError("an explicit dashboard root is required")

    supplied = Path(raw_root).expanduser()
    if supplied.is_symlink():
        raise DashboardError("dashboard root must not be a symbolic link")
    root = supplied.absolute().resolve(strict=False)
    home = Path.home().resolve()

    if root == Path(root.anchor) or root == home:
        raise DashboardError("refusing to use the filesystem root or home directory")

    broad_names = {
        "desktop",
        "documents",
        "downloads",
        "home",
        "obsidian",
        "project",
        "projects",
        "public",
        "vault",
    }
    if root.name.casefold() in broad_names:
        raise DashboardError("refusing an obvious broad user or project directory")

    # An existing repository root is not a dedicated dashboard root.  A nested
    # directory named dashboard/status is fine; only the selected root itself
    # is examined.
    project_markers = (".git", "package.json", "pyproject.toml", "Cargo.toml")
    if root.exists() and any((root / marker).exists() for marker in project_markers):
        raise DashboardError("refusing to serve a project root broadly")

    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not root.exists() or not root.is_dir():
        raise DashboardError("dashboard root does not exist or is not a directory")
    _verify_private_path(root, directory=True, label="dashboard root")
    return root.resolve(strict=True)


def _run_directory(root: Path, run_id: str, *, create: bool) -> Path:
    run_id = _safe_run_id(run_id)
    runs = root / "runs"
    if runs.is_symlink():
        raise DashboardError("runs directory must not be a symbolic link")
    if create:
        runs.mkdir(mode=0o700, exist_ok=True)
    if runs.exists():
        _verify_private_path(runs, directory=True, label="runs directory")
    run_dir = runs / run_id
    if run_dir.is_symlink():
        raise DashboardError("run directory must not be a symbolic link")
    if create:
        run_dir.mkdir(mode=0o700, exist_ok=True)
    if not run_dir.exists() or not run_dir.is_dir():
        raise DashboardError(f"run does not exist: {run_id}")
    _verify_private_path(run_dir, directory=True, label="run directory")
    resolved = run_dir.resolve(strict=True)
    if not _is_path_within(resolved, root):
        raise DashboardError("run directory escapes the dashboard root")
    return resolved


def _clean_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise DashboardError(f"{field} must be a string")
    limit = STRING_LIMITS.get(field.rsplit(".", 1)[-1], MAX_STRING_LENGTH)
    if len(value) > limit:
        raise DashboardError(f"{field} exceeds {limit} characters")
    # Remove terminal/control formatting while preserving ordinary whitespace.
    cleaned = "".join(
        char if char in "\n\t" or ord(char) >= 32 else " " for char in value
    )
    cleaned = cleaned.replace("\x7f", " ")
    return cleaned


def _object(value: Any, field: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DashboardError(f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise DashboardError(f"{field} keys must be strings")
    unknown = set(value) - allowed
    if unknown:
        # Unknown keys are untrusted input. Do not echo them into a terminal.
        raise DashboardError(f"{field} contains {len(unknown)} unknown field(s)")
    if len(value) > len(allowed):
        raise DashboardError(f"{field} has too many fields")
    return value


def _count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DashboardError(f"{field} must be a non-negative integer")
    if value > 2**63 - 1:
        raise DashboardError(f"{field} is too large")
    return value


def _enum_string(value: Any, field: str, allowed: set[str]) -> str:
    result = _clean_string(value, field)
    if result not in allowed:
        raise DashboardError(f"{field} has an unsupported value")
    return result


def _string_object(
    value: Any,
    field: str,
    allowed: set[str],
    *,
    numeric_fields: set[str] | None = None,
    enum_fields: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    source = _object(value, field, allowed)
    numeric_fields = numeric_fields or set()
    enum_fields = enum_fields or {}
    result: dict[str, Any] = {}
    for key, item in source.items():
        item_field = f"{field}.{key}"
        if key in numeric_fields:
            result[key] = _count(item, item_field)
        elif key in enum_fields:
            result[key] = _enum_string(item, item_field, enum_fields[key])
        else:
            result[key] = _clean_string(item, item_field)
    return result


def _entry_list(
    value: Any,
    field: str,
    validator: Callable[[Any, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DashboardError(f"{field} must be an array")
    if len(value) > MAX_ITEMS:
        raise DashboardError(f"{field} exceeds {MAX_ITEMS} entries")
    return [validator(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _progress(value: Any, field: str) -> dict[str, Any]:
    result = _string_object(
        value,
        field,
        PROGRESS_FIELDS,
        numeric_fields={"current", "total"},
        enum_fields={"state": PROGRESS_STATES},
    )
    if "current" in result and "total" in result and result["current"] > result["total"]:
        raise DashboardError(f"{field}.current must not exceed total")
    return result


def _artifact(value: Any, field: str) -> dict[str, Any]:
    result = _string_object(
        value,
        field,
        ARTIFACT_FIELDS,
        numeric_fields={"size_bytes"},
        enum_fields={"state": ARTIFACT_STATES},
    )
    digest = result.get("sha256")
    if digest and not SHA256.fullmatch(digest):
        raise DashboardError(f"{field}.sha256 must be a 64-character hexadecimal digest")
    return result


def _lane(value: Any, field: str) -> dict[str, Any]:
    return _string_object(value, field, LANE_FIELDS, enum_fields={"state": LANE_STATES})


def _readiness(value: Any, field: str) -> dict[str, Any]:
    return _string_object(
        value, field, READINESS_FIELDS, enum_fields={"state": READINESS_STATES}
    )


def _gate(value: Any, field: str) -> dict[str, Any]:
    return _string_object(
        value,
        field,
        GATE_FIELDS,
        enum_fields={"kind": GATE_KINDS, "state": GATE_STATES},
    )


def _decision(value: Any, field: str) -> dict[str, Any]:
    return _string_object(
        value, field, DECISION_FIELDS, enum_fields={"state": DECISION_STATES}
    )


def _alert(value: Any, field: str) -> dict[str, Any]:
    return _string_object(
        value, field, ALERT_FIELDS, enum_fields={"level": ALERT_LEVELS}
    )


def _validate_status(payload: Any, run_id: str) -> dict[str, Any]:
    source = _object(payload, "status", TOP_FIELDS)
    if "schema_version" not in source or "run" not in source:
        raise DashboardError("status requires schema_version and run")

    version = source["schema_version"]
    if isinstance(version, bool) or not isinstance(version, (str, int)):
        raise DashboardError("schema_version must be a short string or positive integer")
    if isinstance(version, int):
        if version < 1 or version > 999:
            raise DashboardError("schema_version integer is out of range")
    else:
        version = _clean_string(version, "schema_version")
        if not version or len(version) > 16:
            raise DashboardError("schema_version string must contain 1-16 characters")

    run = _string_object(
        source["run"],
        "run",
        RUN_FIELDS,
        enum_fields={
            "status": RUN_STATES,
            "allocation_profile": ALLOCATION_PROFILES,
            "codex_usage_band": CODEX_USAGE_BANDS,
            "route": ROUTES,
            "freshness": FRESHNESS_STATES,
        },
    )
    if run.get("id") != run_id:
        raise DashboardError("run.id must exactly match --run-id")

    result: dict[str, Any] = {"schema_version": version, "run": run}
    list_specs: dict[str, Callable[[Any, str], dict[str, Any]]] = {
        "progress": _progress,
        "lanes": _lane,
        "readiness": _readiness,
        "artifacts": _artifact,
        "gates": _gate,
        "decisions": _decision,
        "alerts": _alert,
    }
    for name, validator in list_specs.items():
        if name in source:
            result[name] = _entry_list(source[name], name, validator)

    if "storage" in source:
        result["storage"] = _string_object(
            source["storage"],
            "storage",
            STORAGE_FIELDS,
            numeric_fields={"used_bytes", "budget_bytes", "artifact_count"},
            enum_fields={"state": SUMMARY_STATES},
        )
    if "notes" in source:
        result["notes"] = _string_object(
            source["notes"],
            "notes",
            NOTES_FIELDS,
            numeric_fields={"count"},
            enum_fields={"state": SUMMARY_STATES},
        )

    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise DashboardError(f"sanitized status exceeds {MAX_JSON_BYTES} bytes")
    return result


def _read_regular_file(
    path: Path,
    *,
    label: str,
    maximum: int,
    require_private: bool,
) -> bytes:
    """Read a stable regular file through a no-follow descriptor."""
    try:
        before = path.lstat()
    except OSError as exc:
        raise DashboardError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise DashboardError(f"{label} must be a regular, non-symlink file")
    if before.st_nlink != 1:
        raise DashboardError(f"{label} must have exactly one hard link")
    if require_private:
        _verify_private_stat(before, directory=False, label=label)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise DashboardError(f"{label} changed while it was opened")
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise DashboardError(f"{label} failed descriptor validation")
        if require_private:
            _verify_private_stat(opened, directory=False, label=label)
        if opened.st_size > maximum:
            raise DashboardError(f"{label} is too large")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > maximum:
            raise DashboardError(f"{label} is too large")
        return content
    finally:
        os.close(descriptor)


def _load_status(args: argparse.Namespace) -> Any:
    if args.status_file is not None:
        source = Path(args.status_file).expanduser()
        raw = _read_regular_file(
            source,
            label="status file",
            maximum=MAX_JSON_BYTES,
            require_private=True,
        )
    else:
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)

    if len(raw) > MAX_JSON_BYTES:
        raise DashboardError("status input is too large")
    if not raw.strip():
        raise DashboardError("status input is empty")
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardError(f"invalid JSON status: {exc}") from exc


def _atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    _verify_private_path(path.parent, directory=True, label="dashboard directory")
    if path.exists() or path.is_symlink():
        _verify_private_path(path, directory=False, label="existing dashboard file")
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = ""
        _verify_private_path(path, directory=False, label="dashboard file")
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        except OSError:
            directory_fd = -1
        if directory_fd >= 0:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _write_status(run_dir: Path, status_payload: Any, run_id: str) -> Path:
    sanitized = _validate_status(status_payload, run_id)
    content = (
        json.dumps(sanitized, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    target = run_dir / "status.json"
    _atomic_write(target, content)
    return target


def _default_status(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run": {"id": run_id, "status": "DRAFT", "freshness": "CURRENT"},
        "progress": [],
        "lanes": [],
        "readiness": [],
        "artifacts": [],
        "gates": [],
        "decisions": [],
        "storage": {"state": "UNKNOWN", "summary": "Not yet reported"},
        "notes": {"state": "UNKNOWN", "summary": "Not yet reported"},
        "alerts": [],
    }


def command_init(args: argparse.Namespace) -> int:
    run_id = _safe_run_id(args.run_id)
    root = _validate_dashboard_root(args.root, create=True)
    run_dir = _run_directory(root, run_id, create=True)

    template = Path(args.template).expanduser()
    template_bytes = _read_regular_file(
        template,
        label="HTML template",
        maximum=MAX_TEMPLATE_BYTES,
        require_private=False,
    )
    if b"\x00" in template_bytes:
        raise DashboardError("HTML template contains a NUL byte")

    index = run_dir / "index.html"
    status = run_dir / "status.json"
    if not args.force and (index.exists() or status.exists()):
        raise DashboardError("run is already initialized; use --force to replace it")

    has_status_source = args.status_file is not None
    payload = _load_status(args) if has_status_source else _default_status(run_id)
    # Validate both outputs before replacing either one.
    sanitized = _validate_status(payload, run_id)
    status_bytes = (
        json.dumps(sanitized, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    _atomic_write(index, template_bytes)
    _atomic_write(status, status_bytes)
    print(str(run_dir))
    return 0


def command_update(args: argparse.Namespace) -> int:
    run_id = _safe_run_id(args.run_id)
    root = _validate_dashboard_root(args.root, create=False)
    run_dir = _run_directory(root, run_id, create=False)
    target = _write_status(run_dir, _load_status(args), run_id)
    print(str(target))
    return 0


def _loopback_addresses(host: str) -> list[tuple[int, str]]:
    try:
        records = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise DashboardError(f"bind address cannot be resolved: {host}") from exc
    addresses: list[tuple[int, str]] = []
    for family, _kind, _proto, _canon, sockaddr in records:
        address = sockaddr[0]
        try:
            loopback = ipaddress.ip_address(address).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise DashboardError("serve bind must resolve only to loopback addresses")
        pair = (family, address)
        if pair not in addresses:
            addresses.append(pair)
    if not addresses:
        raise DashboardError("serve bind resolved to no usable loopback address")
    return addresses


def _host_matches_server(host_header: str, server_host: str, server_port: int) -> bool:
    """Accept one canonical loopback Host value for the actual listening port."""
    if not host_header or any(
        char.isspace() or ord(char) < 33 or ord(char) == 127 for char in host_header
    ):
        return False
    if any(char in host_header for char in "@,/?#\\"):
        return False

    if host_header.startswith("["):
        match = re.fullmatch(r"\[([0-9A-Fa-f:.]+)\]:([0-9]{1,5})", host_header)
        if match is None:
            return False
        host, port_text = match.groups()
    else:
        match = re.fullmatch(r"([^:]+):([0-9]{1,5})", host_header)
        if match is None:
            return False
        host, port_text = match.groups()
    try:
        port = int(port_text)
    except ValueError:
        return False
    if port != server_port:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        requested = ipaddress.ip_address(host)
        listening = ipaddress.ip_address(server_host)
    except ValueError:
        return False
    return requested.is_loopback and requested == listening


def _read_dashboard_file(root: Path, run_id: str, filename: str) -> bytes:
    """Open every dashboard component relative to verified directory fds."""
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    root_fd = os.open(root, directory_flags)
    descriptors = [root_fd]
    try:
        _verify_private_stat(
            os.fstat(root_fd), directory=True, label="dashboard root descriptor"
        )
        parent_fd = root_fd
        for component, label in (("runs", "runs directory"), (run_id, "run directory")):
            child_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            descriptors.append(child_fd)
            _verify_private_stat(
                os.fstat(child_fd), directory=True, label=f"{label} descriptor"
            )
            parent_fd = child_fd

        file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        file_fd = os.open(filename, file_flags, dir_fd=parent_fd)
        descriptors.append(file_fd)
        opened = os.fstat(file_fd)
        _verify_private_stat(opened, directory=False, label="dashboard file descriptor")
        maximum = MAX_TEMPLATE_BYTES if filename == "index.html" else MAX_JSON_BYTES
        if opened.st_size > maximum:
            raise DashboardError("dashboard file is too large")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(file_fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) > maximum:
            raise DashboardError("dashboard file is too large")
        return content
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _handler_for(root: Path) -> type[BaseHTTPRequestHandler]:
    root_fingerprint = _root_fingerprint(root)

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "LocalStatusDashboard/1"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            # Do not log request paths: query strings can accidentally contain
            # private data, and this helper has no need for access logs.
            return

        def _common_headers(self, content_type: str, length: int) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; "
                "style-src 'unsafe-inline'; connect-src 'self'; "
                "img-src 'self' data:; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'",
            )
            self.send_header(
                "Permissions-Policy",
                "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                "magnetometer=(), microphone=(), payment=(), usb=()",
            )
            if content_type.startswith(("application/json", "text/html")):
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")

        def _respond(self, status_code: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status_code)
            self._common_headers(content_type, len(body))
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(body)
                except OSError as exc:
                    if exc.errno not in {errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED}:
                        raise

        def _error(self, status_code: HTTPStatus) -> None:
            message = json.dumps({"status": "error", "code": int(status_code)}).encode("utf-8")
            self._respond(status_code, message, "application/json; charset=utf-8")

        def _request_file(self) -> tuple[str, str] | None:
            split = urlsplit(self.path)
            try:
                decoded = unquote_to_bytes(split.path).decode("utf-8", "strict")
            except (UnicodeDecodeError, ValueError):
                return None
            if "\\" in decoded or "\x00" in decoded or not decoded.startswith("/"):
                return None
            raw_parts = decoded.split("/")[1:]
            if any(part in {".", ".."} for part in raw_parts):
                return None
            if any(part == "" for part in raw_parts[:-1]):
                return None
            parts = [part for part in raw_parts if part]

            # Expose only the two public files created for a validated run.
            # In particular, never turn the dedicated root into a general file
            # server if an unexpected file is later placed below it.
            if any(part.startswith(".") for part in parts):
                return None
            if len(parts) not in {2, 3} or parts[0] != "runs":
                return None
            try:
                run_id = _safe_run_id(parts[1])
            except DashboardError:
                return None
            if len(parts) == 2:
                filename = "index.html"
            elif parts[2] in {"index.html", "status.json"}:
                filename = parts[2]
            else:
                return None
            return run_id, filename

        def _serve(self) -> None:
            host_values = self.headers.get_all("Host", [])
            server_host, server_port = self.server.server_address[:2]
            if len(host_values) != 1 or not _host_matches_server(
                host_values[0], str(server_host), int(server_port)
            ):
                self._error(HTTPStatus.FORBIDDEN)
                return
            if urlsplit(self.path).path == "/healthz":
                body = json.dumps(
                    {"status": "ok", "root_fingerprint": root_fingerprint},
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8") + b"\n"
                self._respond(
                    HTTPStatus.OK,
                    body,
                    "application/json; charset=utf-8",
                )
                return
            request_file = self._request_file()
            if request_file is None:
                self._error(HTTPStatus.NOT_FOUND)
                return
            run_id, filename = request_file
            content_type = (
                "text/html; charset=utf-8"
                if filename == "index.html"
                else "application/json; charset=utf-8"
            )
            try:
                body = _read_dashboard_file(root, run_id, filename)
            except (DashboardError, OSError):
                self._error(HTTPStatus.NOT_FOUND)
                return
            self._respond(HTTPStatus.OK, body, content_type)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            self._serve()

        def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
            self._serve()

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            self._error(HTTPStatus.METHOD_NOT_ALLOWED)

    return DashboardHandler


def command_serve(args: argparse.Namespace) -> int:
    root = _validate_dashboard_root(args.root, create=False)
    runs = root / "runs"
    if runs.exists() or runs.is_symlink():
        _verify_private_path(runs, directory=True, label="runs directory")
    addresses = _loopback_addresses(args.bind)
    family, address = addresses[0]

    class DashboardServer(ThreadingHTTPServer):
        address_family = family
        daemon_threads = True
        allow_reuse_address = True

        def handle_error(self, _request: object, _client_address: object) -> None:
            # Request data and local paths must never appear in terminal
            # tracebacks. Individual responses fail closed; access logs are
            # intentionally disabled by the handler as well.
            return

    server = DashboardServer((address, args.port), _handler_for(root))
    actual = server.server_address
    display_host = f"[{actual[0]}]" if family == socket.AF_INET6 else actual[0]
    print(f"http://{display_host}:{actual[1]}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def command_health(args: argparse.Namespace) -> int:
    if args.root:
        root = _validate_dashboard_root(args.root, create=False)
        runs = root / "runs"
        if runs.exists() or runs.is_symlink():
            _verify_private_path(runs, directory=True, label="runs directory")
        print(
            json.dumps(
                {"status": "ok", "root_fingerprint": _root_fingerprint(root)},
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0

    if not args.expected_root:
        raise DashboardError("remote health requires --expected-root")
    expected_root = _validate_dashboard_root(args.expected_root, create=False)
    expected_fingerprint = _root_fingerprint(expected_root)
    addresses = _loopback_addresses(args.host)
    family, address = addresses[0]
    display_host = f"[{address}]" if family == socket.AF_INET6 else address
    url = f"http://{display_host}:{args.port}/healthz"
    request = Request(url, headers={"Host": f"localhost:{args.port}"})
    try:
        with urlopen(request, timeout=args.timeout) as response:
            body = json.load(response)
            if (
                response.status != HTTPStatus.OK
                or not isinstance(body, dict)
                or body.get("status") != "ok"
                or body.get("root_fingerprint") != expected_fingerprint
                or set(body) != {"status", "root_fingerprint"}
            ):
                raise DashboardError("dashboard health response was not healthy")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise DashboardError(f"dashboard health check failed: {exc}") from exc
    print(
        json.dumps(
            {"status": "ok", "root_fingerprint": expected_fingerprint},
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


def _probe_url(url: str, *, port: int, timeout: float, label: str) -> tuple[bytes, str]:
    request = Request(url, headers={"Host": f"localhost:{port}"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_TEMPLATE_BYTES + 1)
            content_type = response.headers.get("Content-Type", "")
            if response.status != HTTPStatus.OK:
                raise DashboardError(f"{label}_unavailable: HTTP {response.status}")
    except HTTPError as exc:
        raise DashboardError(f"{label}_unavailable: HTTP {exc.code}") from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise DashboardError(f"{label}_unavailable: connection failed") from exc
    if len(body) > MAX_TEMPLATE_BYTES:
        raise DashboardError(f"{label}_invalid: response is too large")
    return body, content_type


def command_verify(args: argparse.Namespace) -> int:
    """Verify server identity, exact run page, and current sanitized snapshot."""
    run_id = _safe_run_id(args.run_id)
    expected_root = _validate_dashboard_root(args.expected_root, create=False)
    expected_fingerprint = _root_fingerprint(expected_root)
    addresses = _loopback_addresses(args.host)
    family, address = addresses[0]
    display_host = f"[{address}]" if family == socket.AF_INET6 else address
    base = f"http://{display_host}:{args.port}"

    health_body, health_type = _probe_url(
        f"{base}/healthz", port=args.port, timeout=args.timeout, label="server"
    )
    try:
        health = json.loads(health_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardError("server_identity_invalid: malformed health response") from exc
    if (
        "application/json" not in health_type
        or not isinstance(health, dict)
        or set(health) != {"status", "root_fingerprint"}
        or health.get("status") != "ok"
        or health.get("root_fingerprint") != expected_fingerprint
    ):
        raise DashboardError("server_identity_mismatch: wrong dashboard root or service")

    run_url = f"{base}/runs/{run_id}/"
    page_body, page_type = _probe_url(
        run_url, port=args.port, timeout=args.timeout, label="run_page"
    )
    if "text/html" not in page_type or b'data-dashboard-shell="workforce-status-v2"' not in page_body:
        raise DashboardError("run_page_invalid: expected dashboard shell was not served")

    status_body, status_type = _probe_url(
        f"{run_url}status.json",
        port=args.port,
        timeout=args.timeout,
        label="status_snapshot",
    )
    if len(status_body) > MAX_JSON_BYTES or "application/json" not in status_type:
        raise DashboardError("status_snapshot_invalid: wrong type or oversized response")
    try:
        payload = json.loads(status_body)
        sanitized = _validate_status(payload, run_id)
    except (UnicodeDecodeError, json.JSONDecodeError, DashboardError) as exc:
        raise DashboardError("status_snapshot_invalid: schema or run identity failed") from exc

    print(
        json.dumps(
            {
                "status": "ok",
                "run_id": run_id,
                "page_url": run_url,
                "root_fingerprint": expected_fingerprint,
                "status_sha256": hashlib.sha256(status_body).hexdigest(),
                "freshness": sanitized["run"].get("freshness", "UNKNOWN"),
                "updated_at": sanitized["run"].get("updated_at", ""),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


def _add_status_source(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--status-file", help="read public status JSON from a regular file")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=SafeArgumentParser
    )

    init_parser = subparsers.add_parser("init", help="initialize one run dashboard")
    init_parser.add_argument("--root", required=True, help="dedicated dashboard root")
    init_parser.add_argument("--run-id", required=True, help="safe public run ID")
    init_parser.add_argument("--template", required=True, help="HTML template to copy")
    init_parser.add_argument("--force", action="store_true", help="replace an existing run")
    _add_status_source(init_parser)
    init_parser.set_defaults(handler=command_init)

    update_parser = subparsers.add_parser("update", help="atomically update public status JSON")
    update_parser.add_argument("--root", required=True, help="dedicated dashboard root")
    update_parser.add_argument("--run-id", required=True, help="safe public run ID")
    _add_status_source(update_parser)
    update_parser.set_defaults(handler=command_update)

    serve_parser = subparsers.add_parser("serve", help="serve the dashboard on loopback")
    serve_parser.add_argument("--root", required=True, help="dedicated dashboard root")
    serve_parser.add_argument("--bind", default="127.0.0.1", help="loopback bind address")
    serve_parser.add_argument("--port", type=int, default=8765, help="loopback port; use 0 to select a free port")
    serve_parser.set_defaults(handler=command_serve)

    health_parser = subparsers.add_parser("health", help="check a root or running dashboard")
    health_group = health_parser.add_mutually_exclusive_group(required=True)
    health_group.add_argument("--root", help="check a local dashboard root")
    health_group.add_argument("--host", help="probe a running loopback dashboard")
    health_parser.add_argument(
        "--expected-root",
        help="required with --host; verify the server's exact dashboard root",
    )
    health_parser.add_argument("--port", type=int, default=8765, help="running dashboard port")
    health_parser.add_argument("--timeout", type=float, default=2.0)
    health_parser.set_defaults(handler=command_health)

    verify_parser = subparsers.add_parser(
        "verify", help="verify the exact server, run page, and status snapshot"
    )
    verify_parser.add_argument("--host", default="127.0.0.1", help="loopback host")
    verify_parser.add_argument("--port", type=int, default=8765, help="running dashboard port")
    verify_parser.add_argument("--expected-root", required=True, help="expected dedicated dashboard root")
    verify_parser.add_argument("--run-id", required=True, help="safe public run ID")
    verify_parser.add_argument("--timeout", type=float, default=2.0)
    verify_parser.set_defaults(handler=command_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    minimum_port = 0 if args.command == "serve" else 1
    if hasattr(args, "port") and not minimum_port <= args.port <= 65535:
        parser.error(f"--port must be between {minimum_port} and 65535")
    if getattr(args, "timeout", 1.0) <= 0 or not math.isfinite(getattr(args, "timeout", 1.0)):
        parser.error("--timeout must be a positive finite number")
    try:
        return int(args.handler(args))
    except DashboardError as exc:
        print(f"error: {_safe_diagnostic(exc)}", file=sys.stderr)
        return 2
    except OSError as exc:
        detail = os.strerror(exc.errno) if exc.errno in errno.errorcode else "operating system error"
        print(f"error: {_safe_diagnostic(detail)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
