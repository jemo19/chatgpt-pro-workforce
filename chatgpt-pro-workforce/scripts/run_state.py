#!/usr/bin/env python3
"""Durable, local run ownership and browser-send intent tracking.

This helper deliberately does not claim exactly-once browser delivery.  It
commits a SEND_INTENT before browser input and suppresses reuse of the same
logical work ID until a human or semantic browser check reconciles the prior
outcome.  Only bounded identifiers, prompt hashes, and caller-supplied audit
references are stored; prompts, secret material, and raw evidence do not
belong in this state database.

The state root is always explicit.  Linux ownership, mode, symlink, and
hard-link checks are enforced before this helper calls its state private.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from typing import Any, Iterator
import unicodedata

try:
    import fcntl
except ImportError:  # Windows: retain controlled CLI/help behavior, but never open state.
    fcntl = None  # type: ignore[assignment]


SCHEMA_VERSION = 2
MAX_PATH_BYTES = 4096
MAX_ID_LENGTH = 128
MAX_RUNS = 256
MAX_EVENTS_PER_RUN = 2048
MAX_WORK_ITEMS_PER_RUN = 512
# Ordinary mutations stop early enough to preserve the longest valid post-send
# chain (OUTCOME_UNKNOWN -> ACK -> terminal reconciliation) for every possible
# work item, plus takeover and one safe ownership exit.  The reserve is
# deliberately unavailable to new sends and new ownership claims.
EVENT_SAFETY_RESERVE = 3 * MAX_WORK_ITEMS_PER_RUN + 2
MAX_REASON_LENGTH = 256
MAX_EVIDENCE_REF_LENGTH = 512
SAFE_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
WORK_STATES = {
    "SEND_INTENT",
    "ACK",
    "OUTCOME_UNKNOWN",
    "COMPLETED",
    "FAILED",
    "NOT_SENT",
}
TERMINAL_WORK_STATES = {"COMPLETED", "FAILED"}
RECONCILIATIONS = {"ACK", "COMPLETED", "FAILED", "NOT_SENT"}
TERMINAL_RUN_STATES = {"COMPLETE", "BLOCKED"}
UNRESOLVED_SEND_STATES = {"SEND_INTENT", "OUTCOME_UNKNOWN"}
PENDING_COMPLETION_STATES = {"SEND_INTENT", "OUTCOME_UNKNOWN", "ACK"}
RECOVERY_PENDING_STATES = PENDING_COMPLETION_STATES
DESKTOP_STATES = {"CLEAR", "ACTIVE", "UNKNOWN"}


class RunStateError(ValueError):
    """A bounded, user-facing state error."""


def _safe_diagnostic(value: object, limit: int = 300) -> str:
    text = str(value).encode("ascii", "backslashreplace").decode("ascii")
    text = "".join(char if 32 <= ord(char) < 127 else " " for char in text)
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{_safe_diagnostic(self.prog, 120)}: error: {_safe_diagnostic(message)}\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value) or value in {".", ".."}:
        raise RunStateError(
            f"{label} must be 1-{MAX_ID_LENGTH} ASCII letters, digits, dots, "
            "underscores, or hyphens and must start and end with a letter or digit"
        )
    return value


def _prompt_hash(value: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise RunStateError("prompt hash must be exactly 64 lowercase hexadecimal characters")
    return value


def _bounded_record_text(value: str, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RunStateError(f"{label} is required")
    if len(value) > limit:
        raise RunStateError(f"{label} must not exceed {limit} characters")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise RunStateError(f"{label} must not contain control characters")
    return value


def _require_linux_posix() -> None:
    if fcntl is None or os.name != "posix" or not sys.platform.startswith("linux"):
        raise RunStateError(
            "private run-state file security is verified only on Linux/POSIX; "
            "Windows and macOS ACL enforcement is unverified"
        )


def _verify_private_stat(result: os.stat_result, *, directory: bool, label: str) -> None:
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_type(result.st_mode):
        raise RunStateError(f"{label} has an unexpected file type")
    if result.st_uid != os.geteuid():
        raise RunStateError(f"{label} is not owned by the current user")
    required_mode = 0o700 if directory else 0o600
    if stat.S_IMODE(result.st_mode) != required_mode:
        raise RunStateError(f"{label} must have mode {required_mode:04o}")
    if not directory and result.st_nlink != 1:
        raise RunStateError(f"{label} must have exactly one hard link")


def _verify_private_path(path: Path, *, directory: bool, label: str) -> os.stat_result:
    try:
        result = path.lstat()
    except OSError as exc:
        raise RunStateError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(result.st_mode):
        raise RunStateError(f"{label} must not be a symbolic link")
    _verify_private_stat(result, directory=directory, label=label)
    return result


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            result = current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise RunStateError("state root path cannot be inspected safely") from exc
        if stat.S_ISLNK(result.st_mode):
            raise RunStateError("state root and its existing path components must not be symbolic links")


def _state_root(raw_root: str | os.PathLike[str], *, create: bool) -> Path:
    _require_linux_posix()
    raw = os.fspath(raw_root)
    if not raw or not raw.strip():
        raise RunStateError("an explicit state root is required")
    if len(os.fsencode(raw)) > MAX_PATH_BYTES:
        raise RunStateError("state root path is too long")
    supplied = Path(raw).expanduser().absolute()
    _reject_symlink_components(supplied)
    if supplied == Path(supplied.anchor):
        raise RunStateError("state root must not be a filesystem root")
    if create and not supplied.exists():
        parent = supplied.parent
        if not parent.is_dir():
            raise RunStateError("state root parent must already exist")
        try:
            os.mkdir(supplied, 0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise RunStateError("state root could not be created") from exc
    _verify_private_path(supplied, directory=True, label="state root")
    return supplied


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _open_private_file(path: Path, *, create: bool) -> int:
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise RunStateError(f"{path.name} could not be opened safely") from exc
    try:
        _verify_private_stat(os.fstat(descriptor), directory=False, label=path.name)
        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode):
            raise RunStateError(f"{path.name} must not be a symbolic link")
        _verify_private_stat(path_stat, directory=False, label=path.name)
        descriptor_stat = os.fstat(descriptor)
        if (path_stat.st_dev, path_stat.st_ino) != (descriptor_stat.st_dev, descriptor_stat.st_ino):
            raise RunStateError(f"{path.name} changed while it was opened")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _verify_database_sidecars(database: Path) -> None:
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = Path(str(database) + suffix)
        try:
            sidecar.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise RunStateError("run-state database sidecar cannot be inspected safely") from exc
        _verify_private_path(sidecar, directory=False, label="run-state database sidecar")


SCHEMA = """
CREATE TABLE IF NOT EXISTS configuration (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','READY','PAUSED','COMPLETE','BLOCKED')),
    owner_session TEXT,
    recovery_required INTEGER NOT NULL DEFAULT 0 CHECK (recovery_required IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS logical_work (
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    logical_work_id TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('SEND_INTENT','ACK','OUTCOME_UNKNOWN','COMPLETED','FAILED','NOT_SENT')),
    last_revision INTEGER NOT NULL,
    lane_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    PRIMARY KEY (run_id, logical_work_id)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS events (
    event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    revision INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    session_id TEXT,
    logical_work_id TEXT,
    lane_id TEXT,
    conversation_id TEXT,
    prompt_hash TEXT,
    prior_owner_session TEXT,
    reason TEXT,
    evidence_ref TEXT,
    desktop_state TEXT,
    UNIQUE (run_id, revision)
);
CREATE INDEX IF NOT EXISTS events_by_run ON events(run_id, event_seq);
CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;
"""


class RunStateStore:
    """A process-serialized, transaction-backed run-state store."""

    def __init__(self, root: str | os.PathLike[str], *, create: bool = False) -> None:
        self.root = _state_root(root, create=create)
        self._lock_fd: int | None = None
        self._connection: sqlite3.Connection | None = None
        try:
            lock_path = self.root / ".run-state.lock"
            self._lock_fd = _open_private_file(lock_path, create=create)
            deadline = time.monotonic() + 3.0
            while True:
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise RunStateError(
                            "run-state store is busy; retry after its current writer finishes"
                        ) from exc
                    time.sleep(0.05)
            _verify_private_stat(os.fstat(self._lock_fd), directory=False, label=lock_path.name)
            database = self.root / "run-state.sqlite3"
            database_created = not database.exists()
            if database_created and not create:
                raise RunStateError("run-state database does not exist; initialize it first")
            database_fd = _open_private_file(database, create=create)
            os.close(database_fd)
            before = _verify_private_path(database, directory=False, label="run-state database")
            _verify_database_sidecars(database)
            connection = sqlite3.connect(str(database), timeout=3, isolation_level=None)
            self._connection = connection
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA temp_store = MEMORY")
            _verify_database_sidecars(database)
            after = _verify_private_path(database, directory=False, label="run-state database")
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise RunStateError("run-state database changed while it was opened")
            if database_created:
                self._initialize_schema()
            self._verify_schema()
            if database_created:
                _fsync_directory(self.root)
        except Exception:
            self.close()
            raise

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RunStateError("run-state store is closed")
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if getattr(self, "_lock_fd", None) is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None

    def __enter__(self) -> "RunStateStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def _initialize_schema(self) -> None:
        connection = self.connection
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + SCHEMA
                + "\nINSERT INTO configuration(key, value) "
                + f"VALUES ('schema_version', '{SCHEMA_VERSION}');\n"
                + "COMMIT;"
            )
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise

    def _verify_schema(self) -> None:
        try:
            row = self.connection.execute(
                "SELECT value FROM configuration WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.Error as exc:
            raise RunStateError("run-state database schema is missing or invalid") from exc
        if row is not None and row["value"] == "1":
            self._migrate_v1_to_v2()
            row = self.connection.execute(
                "SELECT value FROM configuration WHERE key = 'schema_version'"
            ).fetchone()
        if row is None or row["value"] != str(SCHEMA_VERSION):
            raise RunStateError("run-state database schema version is unsupported")
        expected_columns = {
            "runs": {"recovery_required"},
            "events": {"prior_owner_session", "reason", "evidence_ref", "desktop_state"},
        }
        for table, required in expected_columns.items():
            present = {
                item["name"]
                for item in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if not required.issubset(present):
                raise RunStateError("run-state database schema is missing required columns")

    def _migrate_v1_to_v2(self) -> None:
        """Apply the bounded, additive v1 migration without rewriting event history."""
        connection = self.connection
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "ALTER TABLE runs ADD COLUMN recovery_required INTEGER NOT NULL DEFAULT 0 "
                "CHECK (recovery_required IN (0,1))"
            )
            connection.execute("ALTER TABLE events ADD COLUMN prior_owner_session TEXT")
            connection.execute("ALTER TABLE events ADD COLUMN reason TEXT")
            connection.execute("ALTER TABLE events ADD COLUMN evidence_ref TEXT")
            connection.execute("ALTER TABLE events ADD COLUMN desktop_state TEXT")
            connection.execute(
                "UPDATE configuration SET value = ? WHERE key = 'schema_version'",
                (str(SCHEMA_VERSION),),
            )
            connection.commit()
            _fsync_directory(self.root)
        except Exception as exc:
            if connection.in_transaction:
                connection.rollback()
            raise RunStateError("run-state database v1 migration failed safely") from exc

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
            _fsync_directory(self.root)
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _run(connection: sqlite3.Connection, run_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise RunStateError("run ID is not registered in this state root")
        return row

    @staticmethod
    def _check_revision(row: sqlite3.Row, expected_revision: int) -> None:
        if expected_revision < 1 or row["revision"] != expected_revision:
            raise RunStateError(
                f"stale revision: expected {expected_revision}, current revision is {row['revision']}"
            )

    @staticmethod
    def _check_owner(row: sqlite3.Row, session_id: str) -> None:
        if row["owner_session"] != session_id:
            raise RunStateError("run is not owned by this session")

    @staticmethod
    def _capacity(
        connection: sqlite3.Connection,
        run_id: str,
        *,
        work: bool = False,
        safety: bool = False,
    ) -> None:
        table = "logical_work" if work else "events"
        count = connection.execute(
            f"SELECT COUNT(*) AS count FROM {table} WHERE run_id = ?", (run_id,)
        ).fetchone()["count"]
        if work:
            limit = MAX_WORK_ITEMS_PER_RUN
        elif safety:
            limit = MAX_EVENTS_PER_RUN
        else:
            reserve = min(EVENT_SAFETY_RESERVE, max(0, MAX_EVENTS_PER_RUN - 1))
            limit = MAX_EVENTS_PER_RUN - reserve
        if count >= limit:
            label = "logical work item" if work else "event"
            if not work and not safety:
                raise RunStateError(
                    "run has reached its ordinary event budget; reconcile pending work, "
                    "pause/release/block/complete this run, then roll remaining work into "
                    "a new linked run"
                )
            raise RunStateError(f"run has reached its bounded {label} limit ({limit})")

    @staticmethod
    def _count_work_states(
        connection: sqlite3.Connection, run_id: str, states: set[str]
    ) -> int:
        placeholders = ",".join("?" for _ in states)
        row = connection.execute(
            f"SELECT COUNT(*) AS count FROM logical_work "
            f"WHERE run_id = ? AND state IN ({placeholders})",
            (run_id, *sorted(states)),
        ).fetchone()
        return int(row["count"])

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        *,
        run_id: str,
        revision: int,
        event_type: str,
        session_id: str | None,
        logical_work_id: str | None = None,
        lane_id: str | None = None,
        conversation_id: str | None = None,
        prompt_hash: str | None = None,
        prior_owner_session: str | None = None,
        reason: str | None = None,
        evidence_ref: str | None = None,
        desktop_state: str | None = None,
        safety: bool = False,
    ) -> None:
        RunStateStore._capacity(connection, run_id, safety=safety)
        connection.execute(
            """INSERT INTO events(
                   run_id, revision, event_type, occurred_at, session_id,
                   logical_work_id, lane_id, conversation_id, prompt_hash,
                   prior_owner_session, reason, evidence_ref, desktop_state
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                revision,
                event_type,
                _now(),
                session_id,
                logical_work_id,
                lane_id,
                conversation_id,
                prompt_hash,
                prior_owner_session,
                reason,
                evidence_ref,
                desktop_state,
            ),
        )

    def initialize_run(self, run_id: str, session_id: str) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        with self._transaction() as connection:
            if connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
                raise RunStateError("run ID is already registered")
            count = connection.execute("SELECT COUNT(*) AS count FROM runs").fetchone()["count"]
            if count >= MAX_RUNS:
                raise RunStateError(f"state root has reached its bounded run limit ({MAX_RUNS})")
            timestamp = _now()
            connection.execute(
                """INSERT INTO runs(
                       run_id, revision, status, owner_session, recovery_required,
                       created_at, updated_at
                   ) VALUES (?, 1, 'ACTIVE', ?, 0, ?, ?)""",
                (run_id, session_id, timestamp, timestamp),
            )
            self._append_event(
                connection,
                run_id=run_id,
                revision=1,
                event_type="RUN_INITIALIZED",
                session_id=session_id,
            )
        return self.show(run_id)

    def claim(self, run_id: str, session_id: str, expected_revision: int) -> dict[str, Any]:
        return self._ownership_change(
            run_id, session_id, expected_revision, "CLAIM", "ACTIVE", require="READY"
        )

    def resume(self, run_id: str, session_id: str, expected_revision: int) -> dict[str, Any]:
        return self._ownership_change(run_id, session_id, expected_revision, "RESUME", "ACTIVE", require="PAUSED")

    def takeover(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        expected_owner_session: str,
        reason: str,
        evidence_ref: str,
    ) -> dict[str, Any]:
        """Explicitly replace an abandoned owner while preserving uncertain work."""
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        expected_owner_session = _safe_id(expected_owner_session, "expected owner session ID")
        reason = _bounded_record_text(reason, "takeover reason", MAX_REASON_LENGTH)
        evidence_ref = _bounded_record_text(
            evidence_ref, "takeover evidence reference", MAX_EVIDENCE_REF_LENGTH
        )
        if session_id == expected_owner_session:
            raise RunStateError("takeover session must differ from the expected prior owner")
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_revision(row, expected_revision)
            if row["status"] != "ACTIVE":
                raise RunStateError("only an ACTIVE run can use abandoned-owner takeover")
            if row["owner_session"] != expected_owner_session:
                raise RunStateError("expected prior owner does not match the canonical run owner")
            unresolved_sends = self._count_work_states(
                connection, run_id, UNRESOLVED_SEND_STATES
            )
            recovery_pending = self._count_work_states(
                connection, run_id, RECOVERY_PENDING_STATES
            )
            revision = row["revision"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type="OWNERSHIP_TAKEOVER",
                session_id=session_id,
                prior_owner_session=expected_owner_session,
                reason=reason,
                evidence_ref=evidence_ref,
                safety=True,
            )
            connection.execute(
                """UPDATE runs
                   SET revision = ?, owner_session = ?, recovery_required = ?, updated_at = ?
                   WHERE run_id = ?""",
                (revision, session_id, 1 if recovery_pending else 0, _now(), run_id),
            )
        result = self.show(run_id)
        result["takeover"] = {
            "prior_owner_session": expected_owner_session,
            "reconciliation_required": bool(recovery_pending),
            "unresolved_send_count": unresolved_sends,
            "pending_recovery_count": recovery_pending,
            "new_sends_permitted": result["new_sends_permitted"],
        }
        return result

    def _ownership_change(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        event_type: str,
        status: str,
        *,
        require: str | None = None,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        recovery_only = False
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_revision(row, expected_revision)
            if row["owner_session"] is not None:
                raise RunStateError("run is already owned by another session")
            if require is not None and row["status"] != require:
                raise RunStateError(f"run must be {require} before {event_type.lower()}")
            recovery_pending = self._count_work_states(
                connection, run_id, RECOVERY_PENDING_STATES
            )
            event_count = connection.execute(
                "SELECT COUNT(*) AS count FROM events WHERE run_id = ?", (run_id,)
            ).fetchone()["count"]
            # Once ordinary capacity closes, an unowned run still needs one
            # bounded way to regain an owner so it can reconcile or terminate.
            # This applies to both a paused run and a released READY handoff,
            # even when no browser work remains pending. The reserved event
            # authorizes ownership for recovery/closure only; show() continues
            # to report new_sends_permitted=false at capacity.
            recovery_only = (
                event_type in {"CLAIM", "RESUME"}
                and event_count >= self._ordinary_event_limit()
            )
            revision = row["revision"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type=event_type,
                session_id=session_id,
                safety=recovery_only,
            )
            connection.execute(
                """UPDATE runs
                   SET revision = ?, status = ?, owner_session = ?, recovery_required = ?, updated_at = ?
                   WHERE run_id = ?""",
                (revision, status, session_id, 1 if recovery_pending else 0, _now(), run_id),
            )
        result = self.show(run_id)
        if recovery_only:
            result["ownership_mode"] = "RECOVERY_ONLY"
        return result

    def release(self, run_id: str, session_id: str, expected_revision: int) -> dict[str, Any]:
        return self._release_like(run_id, session_id, expected_revision, "RELEASE", "READY")

    def pause(self, run_id: str, session_id: str, expected_revision: int) -> dict[str, Any]:
        return self._release_like(run_id, session_id, expected_revision, "PAUSE", "PAUSED")

    def _release_like(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        event_type: str,
        status: str,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_owner(row, session_id)
            self._check_revision(row, expected_revision)
            if row["status"] != "ACTIVE":
                raise RunStateError("run must be ACTIVE before releasing or pausing")
            if status == "READY" and self._count_work_states(
                connection, run_id, PENDING_COMPLETION_STATES
            ):
                raise RunStateError("release requires all pending browser work to be reconciled")
            revision = row["revision"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type=event_type,
                session_id=session_id,
                safety=True,
            )
            connection.execute(
                """UPDATE runs
                   SET revision = ?, status = ?, owner_session = NULL,
                       recovery_required = 0, updated_at = ?
                   WHERE run_id = ?""",
                (revision, status, _now(), run_id),
            )
        return self.show(run_id)

    def terminal(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        status: str,
        reason: str,
        evidence_ref: str,
        desktop_state: str,
    ) -> dict[str, Any]:
        """Deliberately close an owned run with an auditable terminal transition."""
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        if not isinstance(status, str):
            raise RunStateError("terminal run status must be COMPLETE or BLOCKED")
        status = status.upper()
        if status not in TERMINAL_RUN_STATES:
            raise RunStateError("terminal run status must be COMPLETE or BLOCKED")
        reason = _bounded_record_text(reason, "terminal reason", MAX_REASON_LENGTH)
        evidence_ref = _bounded_record_text(
            evidence_ref, "terminal evidence reference", MAX_EVIDENCE_REF_LENGTH
        )
        if not isinstance(desktop_state, str):
            raise RunStateError("desktop state must be CLEAR, ACTIVE, or UNKNOWN")
        desktop_state = desktop_state.upper()
        if desktop_state not in DESKTOP_STATES:
            raise RunStateError("desktop state must be CLEAR, ACTIVE, or UNKNOWN")
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_owner(row, session_id)
            self._check_revision(row, expected_revision)
            if row["status"] != "ACTIVE":
                raise RunStateError("run must be ACTIVE before a terminal transition")
            pending = self._count_work_states(connection, run_id, PENDING_COMPLETION_STATES)
            if status == "COMPLETE":
                if pending:
                    raise RunStateError(
                        "completion requires all browser sends and acknowledged work to be reconciled"
                    )
                if row["recovery_required"]:
                    raise RunStateError("completion requires takeover reconciliation to be cleared")
                if desktop_state != "CLEAR":
                    raise RunStateError("completion requires desktop state CLEAR")
            revision = row["revision"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type=f"RUN_{status}",
                session_id=session_id,
                reason=reason,
                evidence_ref=evidence_ref,
                desktop_state=desktop_state,
                safety=True,
            )
            connection.execute(
                """UPDATE runs
                   SET revision = ?, status = ?, owner_session = NULL,
                       recovery_required = 0, updated_at = ?
                   WHERE run_id = ?""",
                (revision, status, _now(), run_id),
            )
        return self.show(run_id)

    def send_intent(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        logical_work_id: str,
        lane_id: str,
        conversation_id: str,
        prompt_hash: str,
        *,
        confirmed_not_sent: bool = False,
    ) -> dict[str, Any]:
        """Commit intent before input, or suppress a previously seen logical ID."""
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        logical_work_id = _safe_id(logical_work_id, "logical work ID")
        lane_id = _safe_id(lane_id, "lane ID")
        conversation_id = _safe_id(conversation_id, "conversation ID")
        prompt_hash = _prompt_hash(prompt_hash)
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_owner(row, session_id)
            if row["status"] != "ACTIVE":
                raise RunStateError("browser send intent requires an ACTIVE run")
            prior = connection.execute(
                "SELECT * FROM logical_work WHERE run_id = ? AND logical_work_id = ?",
                (run_id, logical_work_id),
            ).fetchone()
            if prior is not None:
                if prior["prompt_hash"] != prompt_hash:
                    raise RunStateError("logical work ID already exists with a different prompt hash")
                if not confirmed_not_sent:
                    return {
                        "ok": True,
                        "action": "SUPPRESSED",
                        "run_id": run_id,
                        "revision": row["revision"],
                        "logical_work_id": logical_work_id,
                        "work_state": prior["state"],
                        "automatic_resend_allowed": False,
                        "guidance": "inspect and reconcile the prior browser outcome; do not automatically resend",
                    }
                if prior["state"] != "NOT_SENT":
                    raise RunStateError("retry requires an explicitly reconciled NOT_SENT outcome")
            else:
                if confirmed_not_sent:
                    raise RunStateError("confirmed retry requires an existing NOT_SENT logical work item")
                self._capacity(connection, run_id, work=True)
            if row["recovery_required"]:
                raise RunStateError(
                    "takeover reconciliation is required before committing any new browser send"
                )
            self._check_revision(row, expected_revision)
            revision = row["revision"] + 1
            attempt = 1 if prior is None else prior["attempt"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type="SEND_INTENT",
                session_id=session_id,
                logical_work_id=logical_work_id,
                lane_id=lane_id,
                conversation_id=conversation_id,
                prompt_hash=prompt_hash,
            )
            if prior is None:
                connection.execute(
                    "INSERT INTO logical_work VALUES (?, ?, ?, 'SEND_INTENT', ?, ?, ?, ?)",
                    (run_id, logical_work_id, prompt_hash, revision, lane_id, conversation_id, attempt),
                )
            else:
                connection.execute(
                    """UPDATE logical_work
                       SET state = 'SEND_INTENT', last_revision = ?, lane_id = ?, conversation_id = ?, attempt = ?
                       WHERE run_id = ? AND logical_work_id = ?""",
                    (revision, lane_id, conversation_id, attempt, run_id, logical_work_id),
                )
            connection.execute(
                "UPDATE runs SET revision = ?, updated_at = ? WHERE run_id = ?",
                (revision, _now(), run_id),
            )
        return {
            "ok": True,
            "action": "SEND_INTENT_COMMITTED",
            "run_id": run_id,
            "revision": revision,
            "logical_work_id": logical_work_id,
            "attempt": attempt,
            "browser_input_permitted": True,
            "delivery_guarantee": "not exactly once; reconcile observed browser state after input",
        }

    def acknowledge(
        self, run_id: str, session_id: str, expected_revision: int, logical_work_id: str
    ) -> dict[str, Any]:
        return self._work_transition(
            run_id, session_id, expected_revision, logical_work_id, "ACK", {"SEND_INTENT", "OUTCOME_UNKNOWN"}
        )

    def outcome_unknown(
        self, run_id: str, session_id: str, expected_revision: int, logical_work_id: str
    ) -> dict[str, Any]:
        return self._work_transition(
            run_id, session_id, expected_revision, logical_work_id, "OUTCOME_UNKNOWN", {"SEND_INTENT"}
        )

    def reconcile(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        logical_work_id: str,
        resolution: str,
    ) -> dict[str, Any]:
        if resolution not in RECONCILIATIONS:
            raise RunStateError("reconciliation must be ACK, COMPLETED, FAILED, or NOT_SENT")
        allowed = {
            "ACK": {"SEND_INTENT", "OUTCOME_UNKNOWN"},
            "COMPLETED": {"SEND_INTENT", "ACK", "OUTCOME_UNKNOWN"},
            "FAILED": {"SEND_INTENT", "ACK", "OUTCOME_UNKNOWN"},
            "NOT_SENT": {"SEND_INTENT", "OUTCOME_UNKNOWN"},
        }[resolution]
        return self._work_transition(
            run_id, session_id, expected_revision, logical_work_id, resolution, allowed,
            event_type=f"RECONCILE_{resolution}",
        )

    def _work_transition(
        self,
        run_id: str,
        session_id: str,
        expected_revision: int,
        logical_work_id: str,
        state: str,
        allowed_from: set[str],
        *,
        event_type: str | None = None,
    ) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        session_id = _safe_id(session_id, "session ID")
        logical_work_id = _safe_id(logical_work_id, "logical work ID")
        if state not in WORK_STATES:
            raise RunStateError("invalid logical work state")
        with self._transaction() as connection:
            row = self._run(connection, run_id)
            self._check_owner(row, session_id)
            self._check_revision(row, expected_revision)
            if row["status"] != "ACTIVE":
                raise RunStateError("logical work can transition only while the run is ACTIVE")
            work = connection.execute(
                "SELECT * FROM logical_work WHERE run_id = ? AND logical_work_id = ?",
                (run_id, logical_work_id),
            ).fetchone()
            if work is None:
                raise RunStateError("logical work ID is not registered")
            if work["state"] not in allowed_from:
                raise RunStateError(f"logical work item cannot move from {work['state']} to {state}")
            revision = row["revision"] + 1
            self._append_event(
                connection,
                run_id=run_id,
                revision=revision,
                event_type=event_type or state,
                session_id=session_id,
                logical_work_id=logical_work_id,
                lane_id=work["lane_id"],
                conversation_id=work["conversation_id"],
                prompt_hash=work["prompt_hash"],
                safety=True,
            )
            connection.execute(
                "UPDATE logical_work SET state = ?, last_revision = ? WHERE run_id = ? AND logical_work_id = ?",
                (state, revision, run_id, logical_work_id),
            )
            recovery_pending = self._count_work_states(
                connection, run_id, RECOVERY_PENDING_STATES
            )
            recovery_required = 1 if row["recovery_required"] and recovery_pending else 0
            connection.execute(
                """UPDATE runs
                   SET revision = ?, recovery_required = ?, updated_at = ?
                   WHERE run_id = ?""",
                (revision, recovery_required, _now(), run_id),
            )
        return self.show(run_id, logical_work_id=logical_work_id)

    def show(self, run_id: str, *, logical_work_id: str | None = None) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        row = self._run(self.connection, run_id)
        query = "SELECT * FROM logical_work WHERE run_id = ?"
        if logical_work_id is None:
            query += " ORDER BY logical_work_id LIMIT ?"
            work_rows = self.connection.execute(query, (run_id, MAX_WORK_ITEMS_PER_RUN)).fetchall()
        else:
            logical_work_id = _safe_id(logical_work_id, "logical work ID")
            query += " AND logical_work_id = ?"
            work_rows = self.connection.execute(query, (run_id, logical_work_id)).fetchall()
        event_count = self.connection.execute(
            "SELECT COUNT(*) AS count FROM events WHERE run_id = ?", (run_id,)
        ).fetchone()["count"]
        return {
            "schema_version": SCHEMA_VERSION,
            "run": {
                "run_id": row["run_id"],
                "revision": row["revision"],
                "status": row["status"],
                "owner_session": row["owner_session"],
                "recovery_required": bool(row["recovery_required"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
            "logical_work": [self._work_view(item) for item in work_rows],
            "delivery_note": "browser delivery is not exactly once; unresolved intent requires inspection and reconciliation",
            "new_sends_permitted": row["status"] == "ACTIVE"
            and row["owner_session"] is not None
            and not bool(row["recovery_required"])
            and event_count < self._ordinary_event_limit(),
            "event_capacity": self._event_capacity_view(event_count),
        }

    @staticmethod
    def _ordinary_event_limit() -> int:
        reserve = min(EVENT_SAFETY_RESERVE, max(0, MAX_EVENTS_PER_RUN - 1))
        return MAX_EVENTS_PER_RUN - reserve

    @staticmethod
    def _event_capacity_view(event_count: int) -> dict[str, Any]:
        ordinary_limit = RunStateStore._ordinary_event_limit()
        return {
            "used": event_count,
            "ordinary_limit": ordinary_limit,
            "hard_limit": MAX_EVENTS_PER_RUN,
            "ordinary_remaining": max(0, ordinary_limit - event_count),
            "safety_remaining": max(0, MAX_EVENTS_PER_RUN - max(event_count, ordinary_limit)),
            "rollover_required": event_count >= ordinary_limit,
        }

    @staticmethod
    def _work_view(row: sqlite3.Row) -> dict[str, Any]:
        state = row["state"]
        if state in {"SEND_INTENT", "OUTCOME_UNKNOWN"}:
            next_action = "inspect browser state and reconcile before any retry"
        elif state == "NOT_SENT":
            next_action = "a retry is allowed only with explicit confirmed-not-sent"
        elif state in TERMINAL_WORK_STATES:
            next_action = "no resend; create a distinct logical work ID for new work"
        else:
            next_action = "monitor or record a verified outcome"
        return {
            "logical_work_id": row["logical_work_id"],
            "prompt_hash": row["prompt_hash"],
            "state": state,
            "last_revision": row["last_revision"],
            "lane_id": row["lane_id"],
            "conversation_id": row["conversation_id"],
            "attempt": row["attempt"],
            "automatic_resend_allowed": False,
            "next_safe_action": next_action,
        }

    def list_runs(self) -> dict[str, Any]:
        rows = self.connection.execute(
            """SELECT run_id, revision, status, owner_session, recovery_required, updated_at
               FROM runs ORDER BY updated_at DESC, run_id LIMIT ?""",
            (MAX_RUNS,),
        ).fetchall()
        return {
            "schema_version": SCHEMA_VERSION,
            "run_count": len(rows),
            "max_runs": MAX_RUNS,
            "runs": [dict(row) for row in rows],
        }

    def history(self, run_id: str) -> dict[str, Any]:
        run_id = _safe_id(run_id, "run ID")
        self._run(self.connection, run_id)
        rows = self.connection.execute(
            """SELECT event_seq, revision, event_type, occurred_at, session_id,
                      logical_work_id, lane_id, conversation_id, prompt_hash,
                      prior_owner_session, reason, evidence_ref, desktop_state
               FROM events WHERE run_id = ? ORDER BY event_seq LIMIT ?""",
            (run_id, MAX_EVENTS_PER_RUN),
        ).fetchall()
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "event_count": len(rows),
            "max_events": MAX_EVENTS_PER_RUN,
            "event_capacity": self._event_capacity_view(len(rows)),
            "events": [dict(row) for row in rows],
        }


def _base_parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_root(command: str, help_text: str) -> argparse.ArgumentParser:
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("--root", required=True, help="explicit private run-state directory")
        return child

    init = add_root("init", "initialize and claim a new run")
    init.add_argument("--run-id", required=True)
    init.add_argument("--session-id", required=True)

    add_root("list", "list the bounded canonical run index")

    for command, help_text in (
        ("show", "show one run and its logical work"),
        ("history", "show the append-only event history"),
    ):
        child = add_root(command, help_text)
        child.add_argument("--run-id", required=True)

    for command, help_text in (
        ("claim", "claim a released run"),
        ("release", "release run ownership"),
        ("pause", "pause and release a run"),
        ("resume", "resume and claim a paused run"),
    ):
        child = add_root(command, help_text)
        child.add_argument("--run-id", required=True)
        child.add_argument("--session-id", required=True)
        child.add_argument("--expected-revision", required=True, type=int)

    takeover = add_root("takeover", "explicitly reclaim an abandoned ACTIVE run")
    takeover.add_argument("--run-id", required=True)
    takeover.add_argument("--session-id", required=True)
    takeover.add_argument("--expected-revision", required=True, type=int)
    takeover.add_argument("--expected-owner-session", required=True)
    takeover.add_argument("--reason", required=True)
    takeover.add_argument("--evidence-ref", required=True)

    for command, help_text in (
        ("complete", "mark an owned run complete after all work is reconciled"),
        ("block", "mark an owned run blocked with bounded evidence"),
    ):
        child = add_root(command, help_text)
        child.add_argument("--run-id", required=True)
        child.add_argument("--session-id", required=True)
        child.add_argument("--expected-revision", required=True, type=int)
        child.add_argument("--reason", required=True)
        child.add_argument("--evidence-ref", required=True)
        child.add_argument(
            "--desktop-state",
            required=True,
            choices=sorted(DESKTOP_STATES),
            help="verified desktop action state; COMPLETE requires CLEAR",
        )

    send = add_root("send-intent", "commit write-ahead intent before browser input")
    send.add_argument("--run-id", required=True)
    send.add_argument("--session-id", required=True)
    send.add_argument("--expected-revision", required=True, type=int)
    send.add_argument("--logical-work-id", required=True)
    send.add_argument("--lane-id", required=True)
    send.add_argument("--conversation-id", required=True)
    send.add_argument("--prompt-hash", required=True)
    send.add_argument(
        "--confirmed-not-sent",
        action="store_true",
        help="retry only after reconciliation recorded NOT_SENT",
    )

    for command, help_text in (
        ("ack", "record verified browser submission acknowledgement"),
        ("outcome-unknown", "record uncertainty after browser input"),
    ):
        child = add_root(command, help_text)
        child.add_argument("--run-id", required=True)
        child.add_argument("--session-id", required=True)
        child.add_argument("--expected-revision", required=True, type=int)
        child.add_argument("--logical-work-id", required=True)

    reconcile = add_root("reconcile", "record a semantically verified browser outcome")
    reconcile.add_argument("--run-id", required=True)
    reconcile.add_argument("--session-id", required=True)
    reconcile.add_argument("--expected-revision", required=True, type=int)
    reconcile.add_argument("--logical-work-id", required=True)
    reconcile.add_argument("--resolution", required=True, choices=sorted(RECONCILIATIONS))
    return parser


def _dispatch(arguments: argparse.Namespace) -> dict[str, Any]:
    create = arguments.command == "init"
    with RunStateStore(arguments.root, create=create) as store:
        if arguments.command == "init":
            return store.initialize_run(arguments.run_id, arguments.session_id)
        if arguments.command == "list":
            return store.list_runs()
        if arguments.command == "show":
            return store.show(arguments.run_id)
        if arguments.command == "history":
            return store.history(arguments.run_id)
        if arguments.command == "claim":
            return store.claim(arguments.run_id, arguments.session_id, arguments.expected_revision)
        if arguments.command == "release":
            return store.release(arguments.run_id, arguments.session_id, arguments.expected_revision)
        if arguments.command == "pause":
            return store.pause(arguments.run_id, arguments.session_id, arguments.expected_revision)
        if arguments.command == "resume":
            return store.resume(arguments.run_id, arguments.session_id, arguments.expected_revision)
        if arguments.command == "takeover":
            return store.takeover(
                arguments.run_id,
                arguments.session_id,
                arguments.expected_revision,
                arguments.expected_owner_session,
                arguments.reason,
                arguments.evidence_ref,
            )
        if arguments.command in {"complete", "block"}:
            return store.terminal(
                arguments.run_id,
                arguments.session_id,
                arguments.expected_revision,
                "COMPLETE" if arguments.command == "complete" else "BLOCKED",
                arguments.reason,
                arguments.evidence_ref,
                arguments.desktop_state,
            )
        if arguments.command == "send-intent":
            return store.send_intent(
                arguments.run_id,
                arguments.session_id,
                arguments.expected_revision,
                arguments.logical_work_id,
                arguments.lane_id,
                arguments.conversation_id,
                arguments.prompt_hash,
                confirmed_not_sent=arguments.confirmed_not_sent,
            )
        if arguments.command == "ack":
            return store.acknowledge(
                arguments.run_id, arguments.session_id, arguments.expected_revision, arguments.logical_work_id
            )
        if arguments.command == "outcome-unknown":
            return store.outcome_unknown(
                arguments.run_id, arguments.session_id, arguments.expected_revision, arguments.logical_work_id
            )
        if arguments.command == "reconcile":
            return store.reconcile(
                arguments.run_id,
                arguments.session_id,
                arguments.expected_revision,
                arguments.logical_work_id,
                arguments.resolution,
            )
    raise RunStateError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    parser = _base_parser()
    try:
        result = _dispatch(parser.parse_args(argv))
    except (RunStateError, sqlite3.Error, OSError) as exc:
        print(f"run_state.py: error: {_safe_diagnostic(exc)}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
