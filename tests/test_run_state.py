#!/usr/bin/env python3
"""Live integration tests for the durable workforce run-state helper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


SKILL = Path(sys.argv[1]).resolve()
HELPER = SKILL / "scripts/run_state.py"
PASS = "LIVE_PASS"
FAIL = "LIVE_FAIL"
RESULTS: list[tuple[str, str, str]] = []
sys.dont_write_bytecode = True


def record(case_id: str, passed: bool, evidence: str) -> None:
    RESULTS.append((case_id, PASS if passed else FAIL, evidence))


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd="/",
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"command {args!r} returned {result.returncode}, expected {expected}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


def document(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    return json.loads(result.stdout)


def load_helper():
    spec = importlib.util.spec_from_file_location("workforce_run_state", HELPER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load run-state helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    helper = load_helper()
    prompt_hash = hashlib.sha256(b"bounded fixture prompt").hexdigest()
    with tempfile.TemporaryDirectory(prefix="workforce-run-state-test-") as temp_name:
        temp = Path(temp_name)
        root = temp / "state"

        initialized = document(
            run("init", "--root", str(root), "--run-id", "RUN-STATE-01", "--session-id", "SESSION-A")
        )
        database = root / "run-state.sqlite3"
        lock = root / ".run-state.lock"
        modes_ok = (
            stat_mode(root) == 0o700
            and stat_mode(database) == 0o600
            and stat_mode(lock) == 0o600
            and database.stat().st_nlink == 1
            and lock.stat().st_nlink == 1
        )
        record(
            "RS01",
            initialized["run"]["revision"] == 1 and modes_ok,
            "explicit root initialized; root 0700 and state files 0600/single-link",
        )

        released = document(
            run(
                "release", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-A", "--expected-revision", "1",
            )
        )
        claimed = document(
            run(
                "claim", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "2",
            )
        )
        competing = run(
            "claim", "--root", str(root), "--run-id", "RUN-STATE-01",
            "--session-id", "SESSION-C", "--expected-revision", "3", expected=2,
        )
        record(
            "RS02",
            released["run"]["owner_session"] is None
            and claimed["run"]["owner_session"] == "SESSION-B"
            and "already owned" in competing.stderr,
            "exclusive ownership rejects a competing session",
        )

        stale = run(
            "release", "--root", str(root), "--run-id", "RUN-STATE-01",
            "--session-id", "SESSION-B", "--expected-revision", "2", expected=2,
        )
        record(
            "RS03",
            "stale revision" in stale.stderr and "current revision is 3" in stale.stderr,
            "stale mutation rejected with current monotonic revision",
        )

        intent = document(
            run(
                "send-intent", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "3",
                "--logical-work-id", "WORK-ALPHA", "--lane-id", "L01",
                "--conversation-id", "CHAT-01", "--prompt-hash", prompt_hash,
            )
        )
        reopened = document(run("show", "--root", str(root), "--run-id", "RUN-STATE-01"))
        record(
            "RS04",
            intent["action"] == "SEND_INTENT_COMMITTED"
            and intent["browser_input_permitted"] is True
            and "not exactly once" in intent["delivery_guarantee"]
            and reopened["logical_work"][0]["state"] == "SEND_INTENT",
            "committed SEND_INTENT survives a process boundary before browser acknowledgement",
        )

        suppressed = document(
            run(
                "send-intent", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "1",
                "--logical-work-id", "WORK-ALPHA", "--lane-id", "L99",
                "--conversation-id", "CHAT-99", "--prompt-hash", prompt_hash,
            )
        )
        unchanged = document(run("show", "--root", str(root), "--run-id", "RUN-STATE-01"))
        item = unchanged["logical_work"][0]
        record(
            "RS05",
            suppressed["action"] == "SUPPRESSED"
            and suppressed["automatic_resend_allowed"] is False
            and item["lane_id"] == "L01"
            and item["conversation_id"] == "CHAT-01"
            and unchanged["run"]["revision"] == 4,
            "logical work deduplicates across changed lane/conversation even from a stale caller",
        )

        unknown = document(
            run(
                "outcome-unknown", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "4",
                "--logical-work-id", "WORK-ALPHA",
            )
        )
        suppressed_unknown = document(
            run(
                "send-intent", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "5",
                "--logical-work-id", "WORK-ALPHA", "--lane-id", "L02",
                "--conversation-id", "CHAT-02", "--prompt-hash", prompt_hash,
            )
        )
        record(
            "RS06",
            unknown["logical_work"][0]["state"] == "OUTCOME_UNKNOWN"
            and suppressed_unknown["action"] == "SUPPRESSED"
            and "do not automatically resend" in suppressed_unknown["guidance"],
            "unknown browser outcome blocks automatic resend",
        )

        not_sent = document(
            run(
                "reconcile", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "5",
                "--logical-work-id", "WORK-ALPHA", "--resolution", "NOT_SENT",
            )
        )
        retry = document(
            run(
                "send-intent", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "6",
                "--logical-work-id", "WORK-ALPHA", "--lane-id", "L02",
                "--conversation-id", "CHAT-02", "--prompt-hash", prompt_hash,
                "--confirmed-not-sent",
            )
        )
        record(
            "RS07",
            not_sent["logical_work"][0]["state"] == "NOT_SENT"
            and retry["attempt"] == 2
            and retry["revision"] == 7,
            "retry requires explicit NOT_SENT reconciliation and records a new attempt",
        )

        paused = document(
            run(
                "pause", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-B", "--expected-revision", "7",
            )
        )
        resumed = document(
            run(
                "resume", "--root", str(root), "--run-id", "RUN-STATE-01",
                "--session-id", "SESSION-C", "--expected-revision", "8",
            )
        )
        history = document(run("history", "--root", str(root), "--run-id", "RUN-STATE-01"))
        revisions = [event["revision"] for event in history["events"]]
        record(
            "RS08",
            paused["run"]["status"] == "PAUSED"
            and paused["run"]["owner_session"] is None
            and resumed["run"]["status"] == "ACTIVE"
            and resumed["run"]["owner_session"] == "SESSION-C"
            and revisions == list(range(1, 10)),
            "pause/resume changes owner without discarding history; revisions remain contiguous",
        )

        prior_cwd = Path.cwd()
        try:
            os.chdir("/")
            with helper.RunStateStore(root) as store:
                try:
                    store.connection.execute("UPDATE events SET event_type = 'TAMPERED' WHERE event_seq = 1")
                except sqlite3.IntegrityError as exc:
                    append_only = "append-only" in str(exc)
                else:
                    append_only = False
                quick_check = store.connection.execute("PRAGMA quick_check").fetchone()[0]
                index = store.list_runs()
        finally:
            os.chdir(prior_cwd)
        record(
            "RS09",
            append_only and quick_check == "ok" and index["run_count"] == 1,
            "functions work outside repo CWD; quick_check passes; append-only trigger and canonical index hold",
        )

        unsafe_mode_root = temp / "unsafe-mode"
        unsafe_mode_root.mkdir(mode=0o755)
        unsafe_mode_root.chmod(0o755)
        unsafe_mode = run(
            "init", "--root", str(unsafe_mode_root), "--run-id", "RUN-X", "--session-id", "SESSION-X",
            expected=2,
        )
        target = temp / "symlink-target"
        target.mkdir(mode=0o700)
        symlink_root = temp / "symlink-root"
        symlink_root.symlink_to(target, target_is_directory=True)
        unsafe_symlink = run(
            "init", "--root", str(symlink_root), "--run-id", "RUN-X", "--session-id", "SESSION-X",
            expected=2,
        )
        record(
            "RS10",
            "mode 0700" in unsafe_mode.stderr and "symbolic links" in unsafe_symlink.stderr,
            "permissive and symlinked state roots are rejected",
        )

        hardlink_root = temp / "hardlink-state"
        run("init", "--root", str(hardlink_root), "--run-id", "RUN-H", "--session-id", "SESSION-H")
        os.link(hardlink_root / "run-state.sqlite3", temp / "database-peer")
        hardlink = run("show", "--root", str(hardlink_root), "--run-id", "RUN-H", expected=2)

        symlink_db_root = temp / "symlink-db-state"
        run("init", "--root", str(symlink_db_root), "--run-id", "RUN-S", "--session-id", "SESSION-S")
        real_database = temp / "moved-database"
        (symlink_db_root / "run-state.sqlite3").rename(real_database)
        (symlink_db_root / "run-state.sqlite3").symlink_to(real_database)
        symlink_database = run("show", "--root", str(symlink_db_root), "--run-id", "RUN-S", expected=2)
        record(
            "RS11",
            "exactly one hard link" in hardlink.stderr and "opened safely" in symlink_database.stderr,
            "hard-linked and symlinked database paths are rejected",
        )

        too_long = "R" * 129
        bounded = run(
            "init", "--root", str(temp / "bounded"), "--run-id", too_long,
            "--session-id", "SESSION-X", expected=2,
        )
        bad_hash = run(
            "send-intent", "--root", str(root), "--run-id", "RUN-STATE-01",
            "--session-id", "SESSION-C", "--expected-revision", "9",
            "--logical-work-id", "WORK-BETA", "--lane-id", "L03",
            "--conversation-id", "CHAT-03", "--prompt-hash", "A" * 64, expected=2,
        )
        record(
            "RS12",
            "1-128" in bounded.stderr and "lowercase hexadecimal" in bad_hash.stderr,
            "identifier and digest inputs are bounded and strictly validated",
        )

        old_event_limit = helper.MAX_EVENTS_PER_RUN
        old_event_reserve = helper.EVENT_SAFETY_RESERVE
        bounded_root = temp / "bounded-events"
        try:
            helper.MAX_EVENTS_PER_RUN = 6
            helper.EVENT_SAFETY_RESERVE = 4
            with helper.RunStateStore(bounded_root, create=True) as store:
                store.initialize_run("RUN-B", "SESSION-B")
                committed = store.send_intent(
                    "RUN-B", "SESSION-B", 1, "WORK-B", "L01", "CHAT-B", prompt_hash
                )
                at_capacity = store.show("RUN-B")
                try:
                    store.send_intent(
                        "RUN-B", "SESSION-B", 2, "WORK-C", "L02", "CHAT-C", prompt_hash
                    )
                except helper.RunStateError as exc:
                    ordinary_stopped = "ordinary event budget" in str(exc)
                else:
                    ordinary_stopped = False
                unknown_at_capacity = store.outcome_unknown(
                    "RUN-B", "SESSION-B", 2, "WORK-B"
                )
                reconciled_at_capacity = store.reconcile(
                    "RUN-B", "SESSION-B", 3, "WORK-B", "NOT_SENT"
                )
                released_at_capacity = store.release("RUN-B", "SESSION-B", 4)
                bounded_history = store.history("RUN-B")

            terminal_root = temp / "bounded-terminal"
            with helper.RunStateStore(terminal_root, create=True) as store:
                store.initialize_run("RUN-T", "SESSION-T")
                store.send_intent(
                    "RUN-T", "SESSION-T", 1, "WORK-T", "L01", "CHAT-T", prompt_hash
                )
                blocked_at_capacity = store.terminal(
                    "RUN-T", "SESSION-T", 2, "BLOCKED", "bounded fixture",
                    "fixture-evidence", "UNKNOWN"
                )

            complete_root = temp / "bounded-complete"
            with helper.RunStateStore(complete_root, create=True) as store:
                store.initialize_run("RUN-C", "SESSION-C")
                store.send_intent(
                    "RUN-C", "SESSION-C", 1, "WORK-C", "L01", "CHAT-C", prompt_hash
                )
                store.reconcile("RUN-C", "SESSION-C", 2, "WORK-C", "COMPLETED")
                completed_at_capacity = store.terminal(
                    "RUN-C", "SESSION-C", 3, "COMPLETE", "bounded fixture accepted",
                    "fixture-acceptance", "CLEAR"
                )

            paused_root = temp / "bounded-paused-recovery"
            with helper.RunStateStore(paused_root, create=True) as store:
                store.initialize_run("RUN-P", "SESSION-P")
                store.send_intent(
                    "RUN-P", "SESSION-P", 1, "WORK-P", "L01", "CHAT-P", prompt_hash
                )
                paused_at_capacity = store.pause("RUN-P", "SESSION-P", 2)
                resumed_for_recovery = store.resume("RUN-P", "SESSION-R", 3)
                reconciled_after_resume = store.reconcile(
                    "RUN-P", "SESSION-R", 4, "WORK-P", "COMPLETED"
                )
                try:
                    store.send_intent(
                        "RUN-P", "SESSION-R", 5, "WORK-NEW", "L02", "CHAT-NEW", prompt_hash
                    )
                except helper.RunStateError as exc:
                    recovery_send_blocked = "ordinary event budget" in str(exc)
                else:
                    recovery_send_blocked = False
                completed_after_resume = store.terminal(
                    "RUN-P", "SESSION-R", 5, "COMPLETE", "recovery-only resume accepted",
                    "fixture-recovery-acceptance", "CLEAR"
                )
                paused_history = store.history("RUN-P")

            paused_closed_root = temp / "bounded-paused-closed"
            with helper.RunStateStore(paused_closed_root, create=True) as store:
                store.initialize_run("RUN-PC", "SESSION-PC")
                store.send_intent(
                    "RUN-PC", "SESSION-PC", 1, "WORK-PC", "L01", "CHAT-PC", prompt_hash
                )
                store.reconcile("RUN-PC", "SESSION-PC", 2, "WORK-PC", "COMPLETED")
                paused_closed = store.pause("RUN-PC", "SESSION-PC", 3)
                resumed_closed = store.resume("RUN-PC", "SESSION-PC2", 4)
                try:
                    store.send_intent(
                        "RUN-PC", "SESSION-PC2", 5, "WORK-PC2", "L02", "CHAT-PC2",
                        prompt_hash,
                    )
                except helper.RunStateError as exc:
                    paused_closed_send_blocked = "ordinary event budget" in str(exc)
                else:
                    paused_closed_send_blocked = False
                completed_paused_closed = store.terminal(
                    "RUN-PC", "SESSION-PC2", 5, "COMPLETE",
                    "capacity-bound paused run accepted", "fixture-paused-closure", "CLEAR",
                )
                paused_closed_history = store.history("RUN-PC")

            released_closed_root = temp / "bounded-released-closed"
            with helper.RunStateStore(released_closed_root, create=True) as store:
                store.initialize_run("RUN-RC", "SESSION-RC")
                store.send_intent(
                    "RUN-RC", "SESSION-RC", 1, "WORK-RC", "L01", "CHAT-RC", prompt_hash
                )
                store.reconcile("RUN-RC", "SESSION-RC", 2, "WORK-RC", "COMPLETED")
                released_closed = store.release("RUN-RC", "SESSION-RC", 3)
                claimed_closed = store.claim("RUN-RC", "SESSION-RC2", 4)
                try:
                    store.send_intent(
                        "RUN-RC", "SESSION-RC2", 5, "WORK-RC2", "L02", "CHAT-RC2",
                        prompt_hash,
                    )
                except helper.RunStateError as exc:
                    released_closed_send_blocked = "ordinary event budget" in str(exc)
                else:
                    released_closed_send_blocked = False
                completed_released_closed = store.terminal(
                    "RUN-RC", "SESSION-RC2", 5, "COMPLETE",
                    "capacity-bound released run accepted", "fixture-released-closure", "CLEAR",
                )
                released_closed_history = store.history("RUN-RC")
        finally:
            helper.MAX_EVENTS_PER_RUN = old_event_limit
            helper.EVENT_SAFETY_RESERVE = old_event_reserve
        record(
            "RS13",
            committed["action"] == "SEND_INTENT_COMMITTED"
            and at_capacity["event_capacity"]["rollover_required"] is True
            and at_capacity["new_sends_permitted"] is False
            and ordinary_stopped
            and unknown_at_capacity["logical_work"][0]["state"] == "OUTCOME_UNKNOWN"
            and reconciled_at_capacity["logical_work"][0]["state"] == "NOT_SENT"
            and released_at_capacity["run"]["status"] == "READY"
            and released_at_capacity["run"]["owner_session"] is None
            and blocked_at_capacity["run"]["status"] == "BLOCKED"
            and completed_at_capacity["run"]["status"] == "COMPLETE"
            and [event["revision"] for event in bounded_history["events"]] == list(range(1, 6))
            and paused_at_capacity["run"]["status"] == "PAUSED"
            and resumed_for_recovery["ownership_mode"] == "RECOVERY_ONLY"
            and resumed_for_recovery["new_sends_permitted"] is False
            and reconciled_after_resume["logical_work"][0]["state"] == "COMPLETED"
            and reconciled_after_resume["new_sends_permitted"] is False
            and recovery_send_blocked
            and completed_after_resume["run"]["status"] == "COMPLETE"
            and [event["revision"] for event in paused_history["events"]] == list(range(1, 7)),
            "ordinary capacity preserves reconciliation, exit, and recovery-only resume through terminal closure",
        )
        record(
            "RS23",
            paused_closed["run"]["status"] == "PAUSED"
            and paused_closed["logical_work"][0]["state"] == "COMPLETED"
            and resumed_closed["ownership_mode"] == "RECOVERY_ONLY"
            and resumed_closed["new_sends_permitted"] is False
            and paused_closed_send_blocked
            and completed_paused_closed["run"]["status"] == "COMPLETE"
            and completed_paused_closed["run"]["owner_session"] is None
            and [event["revision"] for event in paused_closed_history["events"]]
            == list(range(1, 7)),
            "a capacity-bound PAUSED run with no pending browser work can be reclaimed only to close",
        )
        record(
            "RS24",
            released_closed["run"]["status"] == "READY"
            and released_closed["logical_work"][0]["state"] == "COMPLETED"
            and claimed_closed["ownership_mode"] == "RECOVERY_ONLY"
            and claimed_closed["new_sends_permitted"] is False
            and released_closed_send_blocked
            and completed_released_closed["run"]["status"] == "COMPLETE"
            and completed_released_closed["run"]["owner_session"] is None
            and [event["revision"] for event in released_closed_history["events"]]
            == list(range(1, 7)),
            "a capacity-bound released READY run can be reclaimed only to close",
        )

        escaped = run(
            "show", "--root", str(root), "--run-id", "BAD\x1b[31mID", expected=2,
        )
        record(
            "RS14",
            "\x1b" not in escaped.stderr
            and "Traceback" not in escaped.stderr
            and len(escaped.stderr) < 1000,
            "controlled diagnostics strip terminal controls and omit tracebacks",
        )

        secret_marker = b"THIS PROMPT MUST NOT BE STORED"
        record(
            "RS15",
            secret_marker not in database.read_bytes()
            and "prompt" not in _schema_columns(database, "events"),
            "state stores prompt hashes and bounded identifiers, never prompt bodies",
        )

        abandoned_root = temp / "abandoned-state"
        child_code = (
            "import importlib.util,sys,time;sys.dont_write_bytecode=True;"
            f"s=importlib.util.spec_from_file_location('rs',{str(HELPER)!r});"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            f"store=m.RunStateStore({str(abandoned_root)!r},create=True);"
            "store.initialize_run('RUN-ABANDONED','SESSION-DEAD');"
            f"store.send_intent('RUN-ABANDONED','SESSION-DEAD',1,'WORK-OLD','L01','CHAT-OLD',{prompt_hash!r});"
            "print('STATE_COMMITTED',flush=True);time.sleep(60)"
        )
        killed = subprocess.Popen(
            [sys.executable, "-c", child_code],
            cwd="/",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            marker = killed.stdout.readline().strip() if killed.stdout is not None else ""
            killed.kill()
            killed.wait(timeout=10)
        finally:
            if killed.poll() is None:
                killed.kill()
                killed.wait(timeout=10)
        abandoned = document(
            run("show", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED")
        )
        normal_claim = run(
            "claim", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "2", expected=2,
        )
        record(
            "RS16",
            marker == "STATE_COMMITTED"
            and killed.returncode is not None
            and abandoned["run"]["owner_session"] == "SESSION-DEAD"
            and abandoned["logical_work"][0]["state"] == "SEND_INTENT"
            and "already owned" in normal_claim.stderr,
            "a killed owner leaves durable ownership and SEND_INTENT; normal claim cannot steal it",
        )

        mismatched_takeover = run(
            "takeover", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "2",
            "--expected-owner-session", "SESSION-WRONG",
            "--reason", "verified prior process terminated",
            "--evidence-ref", "process-check-20260907T230000Z", expected=2,
        )
        stale_takeover = run(
            "takeover", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "1",
            "--expected-owner-session", "SESSION-DEAD",
            "--reason", "verified prior process terminated",
            "--evidence-ref", "process-check-20260907T230000Z", expected=2,
        )
        missing_evidence = run(
            "takeover", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "2",
            "--expected-owner-session", "SESSION-DEAD",
            "--reason", "verified prior process terminated", expected=2,
        )
        unchanged_abandoned = document(
            run("show", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED")
        )
        record(
            "RS17",
            "does not match" in mismatched_takeover.stderr
            and "stale revision" in stale_takeover.stderr
            and "--evidence-ref" in missing_evidence.stderr
            and unchanged_abandoned["run"]["owner_session"] == "SESSION-DEAD"
            and unchanged_abandoned["run"]["revision"] == 2,
            "takeover requires exact prior-owner identity, evidence, and an unchanged revision",
        )

        takeover = document(
            run(
                "takeover", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
                "--session-id", "SESSION-NEW", "--expected-revision", "2",
                "--expected-owner-session", "SESSION-DEAD",
                "--reason", "verified prior process terminated",
                "--evidence-ref", "process-check-20260907T230000Z",
            )
        )
        blocked_new_send = run(
            "send-intent", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "3",
            "--logical-work-id", "WORK-NEW", "--lane-id", "L02",
            "--conversation-id", "CHAT-NEW", "--prompt-hash", prompt_hash, expected=2,
        )
        preserved = document(
            run("show", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED")
        )
        record(
            "RS18",
            takeover["takeover"]["reconciliation_required"] is True
            and takeover["takeover"]["new_sends_permitted"] is False
            and preserved["logical_work"][0]["state"] == "SEND_INTENT"
            and preserved["run"]["recovery_required"] is True
            and "reconciliation is required" in blocked_new_send.stderr,
            "takeover preserves unresolved intent and gates every new send until reconciliation",
        )

        reconciled_old = document(
            run(
                "reconcile", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
                "--session-id", "SESSION-NEW", "--expected-revision", "3",
                "--logical-work-id", "WORK-OLD", "--resolution", "NOT_SENT",
            )
        )
        new_intent = document(
            run(
                "send-intent", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
                "--session-id", "SESSION-NEW", "--expected-revision", "4",
                "--logical-work-id", "WORK-NEW", "--lane-id", "L02",
                "--conversation-id", "CHAT-NEW", "--prompt-hash", prompt_hash,
            )
        )
        reconciled_new = document(
            run(
                "reconcile", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
                "--session-id", "SESSION-NEW", "--expected-revision", "5",
                "--logical-work-id", "WORK-NEW", "--resolution", "COMPLETED",
            )
        )
        record(
            "RS19",
            reconciled_old["run"]["recovery_required"] is False
            and reconciled_old["new_sends_permitted"] is True
            and new_intent["action"] == "SEND_INTENT_COMMITTED"
            and reconciled_new["logical_work"][0]["state"] == "COMPLETED",
            "verified reconciliation clears recovery gating before a distinct new send",
        )

        unclear_desktop = run(
            "complete", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "6",
            "--reason", "all registered work accepted", "--evidence-ref", "acceptance-report-sha256",
            "--desktop-state", "UNKNOWN", expected=2,
        )
        completed = document(
            run(
                "complete", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
                "--session-id", "SESSION-NEW", "--expected-revision", "6",
                "--reason", "all registered work accepted", "--evidence-ref", "acceptance-report-sha256",
                "--desktop-state", "CLEAR",
            )
        )
        terminal_send = run(
            "send-intent", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED",
            "--session-id", "SESSION-NEW", "--expected-revision", "7",
            "--logical-work-id", "WORK-LATE", "--lane-id", "L03",
            "--conversation-id", "CHAT-LATE", "--prompt-hash", prompt_hash, expected=2,
        )
        terminal_history = document(
            run("history", "--root", str(abandoned_root), "--run-id", "RUN-ABANDONED")
        )
        takeover_event = next(
            event for event in terminal_history["events"]
            if event["event_type"] == "OWNERSHIP_TAKEOVER"
        )
        complete_event = terminal_history["events"][-1]
        record(
            "RS20",
            "desktop state CLEAR" in unclear_desktop.stderr
            and completed["run"]["status"] == "COMPLETE"
            and completed["run"]["owner_session"] is None
            and "not owned" in terminal_send.stderr
            and takeover_event["prior_owner_session"] == "SESSION-DEAD"
            and takeover_event["reason"] == "verified prior process terminated"
            and complete_event["event_type"] == "RUN_COMPLETE"
            and complete_event["desktop_state"] == "CLEAR",
            "completion requires reconciled work and verified clear desktop state, then closes ownership",
        )

        pending_root = temp / "pending-completion"
        run("init", "--root", str(pending_root), "--run-id", "RUN-PENDING", "--session-id", "SESSION-P")
        run(
            "send-intent", "--root", str(pending_root), "--run-id", "RUN-PENDING",
            "--session-id", "SESSION-P", "--expected-revision", "1",
            "--logical-work-id", "WORK-P", "--lane-id", "L01",
            "--conversation-id", "CHAT-P", "--prompt-hash", prompt_hash,
        )
        premature_complete = run(
            "complete", "--root", str(pending_root), "--run-id", "RUN-PENDING",
            "--session-id", "SESSION-P", "--expected-revision", "2",
            "--reason", "incorrect early close", "--evidence-ref", "fixture",
            "--desktop-state", "CLEAR", expected=2,
        )
        blocked = document(
            run(
                "block", "--root", str(pending_root), "--run-id", "RUN-PENDING",
                "--session-id", "SESSION-P", "--expected-revision", "2",
                "--reason", "browser unavailable after bounded recovery", "--evidence-ref", "incident-17",
                "--desktop-state", "UNKNOWN",
            )
        )
        record(
            "RS21",
            "requires all browser sends" in premature_complete.stderr
            and blocked["run"]["status"] == "BLOCKED"
            and blocked["logical_work"][0]["state"] == "SEND_INTENT",
            "pending browser work blocks COMPLETE while explicit BLOCKED preserves unresolved evidence",
        )

        migration_root = temp / "migration-state"
        migration_root.mkdir(mode=0o700)
        lock_descriptor = os.open(
            migration_root / ".run-state.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        os.close(lock_descriptor)
        migration_database = migration_root / "run-state.sqlite3"
        v1_schema = helper.SCHEMA.replace(
            "    recovery_required INTEGER NOT NULL DEFAULT 0 CHECK (recovery_required IN (0,1)),\n",
            "",
        )
        for v2_column in (
            "    prior_owner_session TEXT,\n",
            "    reason TEXT,\n",
            "    evidence_ref TEXT,\n",
            "    desktop_state TEXT,\n",
        ):
            v1_schema = v1_schema.replace(v2_column, "")
        migration_connection = sqlite3.connect(migration_database)
        try:
            migration_connection.executescript(v1_schema)
            migration_connection.execute(
                "INSERT INTO configuration(key, value) VALUES ('schema_version', '1')"
            )
            migration_connection.execute(
                "INSERT INTO runs VALUES (?, 1, 'ACTIVE', ?, ?, ?)",
                ("RUN-V1", "SESSION-V1", "2026-09-07T00:00:00Z", "2026-09-07T00:00:00Z"),
            )
            migration_connection.execute(
                """INSERT INTO events(
                       run_id, revision, event_type, occurred_at, session_id
                   ) VALUES (?, 1, 'RUN_INITIALIZED', ?, ?)""",
                ("RUN-V1", "2026-09-07T00:00:00Z", "SESSION-V1"),
            )
            migration_connection.commit()
        finally:
            migration_connection.close()
        migration_database.chmod(0o600)
        migrated = document(
            run("show", "--root", str(migration_root), "--run-id", "RUN-V1")
        )
        migrated_history = document(
            run("history", "--root", str(migration_root), "--run-id", "RUN-V1")
        )
        record(
            "RS22",
            migrated["schema_version"] == 2
            and migrated["run"]["recovery_required"] is False
            and migrated_history["events"][0]["event_type"] == "RUN_INITIALIZED"
            and {"prior_owner_session", "reason", "evidence_ref", "desktop_state"}.issubset(
                _schema_columns(migration_database, "events")
            ),
            "the additive v1-to-v2 migration preserves prior event history and private state",
        )

    failures = [item for item in RESULTS if item[1] == FAIL]
    for case_id, status, evidence in RESULTS:
        print(f"{case_id} {status}: {evidence}")
    print(f"TOTAL={len(RESULTS)} LIVE_PASS={len(RESULTS) - len(failures)} LIVE_FAIL={len(failures)}")
    return 1 if failures else 0


def stat_mode(path: Path) -> int:
    return path.stat(follow_symlinks=False).st_mode & 0o777


def _schema_columns(database: Path, table: str) -> set[str]:
    connection = sqlite3.connect(database)
    try:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
