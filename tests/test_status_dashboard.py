#!/usr/bin/env python3
"""Bounded integration tests for the localhost workforce status dashboard."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SKILL = Path(sys.argv[1]).resolve()
HELPER = SKILL / "scripts/status_dashboard.py"
TEMPLATE = SKILL / "assets/status-dashboard-template.html"
PASS = "LIVE_PASS"
FAIL = "LIVE_FAIL"
RESULTS: list[tuple[str, str, str]] = []
sys.dont_write_bytecode = True


def record(case_id: str, passed: bool, evidence: str) -> None:
    RESULTS.append((case_id, PASS if passed else FAIL, evidence))


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
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


def payload(title: str, updated_at: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run": {
            "id": "RUN-DASHBOARD-TEST",
            "title": title,
            "status": "ACTIVE",
            "allocation_profile": "PRO_HEAVY",
            "codex_usage_band": "LOWEST",
            "route": "BROWSER_ONLY",
            "freshness": "CURRENT",
            "updated_at": updated_at,
            "next_action": "Reconcile lane L02",
        },
        "progress": [
            {"id": "scope", "label": "Scope", "current": 2, "total": 4, "state": "ACTIVE", "detail": "two addressed"}
        ],
        "lanes": [],
        "readiness": [
            {"id": "C05", "label": "Chrome", "interface": "fixture-controller", "state": "AVAILABLE_VERIFIED", "detail": "semantic target verified"}
        ],
        "artifacts": [],
        "gates": [],
        "decisions": [],
        "storage": {"state": "READY", "summary": "Dedicated run folder", "used_bytes": 0, "budget_bytes": 0, "artifact_count": 0, "detail": "review before delete"},
        "notes": {"state": "READY", "summary": "Confirmed vault", "count": 1, "updated_at": updated_at, "detail": "native artifacts indexed"},
        "alerts": [],
    }


def fetch(url: str, *, host: str | None = None) -> tuple[int, bytes, object]:
    headers = {"Host": host} if host else {}
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read(), response.headers
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers


def raw_http_status(port: int, host_lines: list[str]) -> int:
    request = "GET /healthz HTTP/1.1\r\n" + "".join(
        f"Host: {value}\r\n" for value in host_lines
    ) + "Connection: close\r\n\r\n"
    with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
        client.sendall(request.encode("ascii"))
        first_line = client.recv(256).split(b"\r\n", 1)[0]
    return int(first_line.split()[1])


def load_helper_module():
    spec = importlib.util.spec_from_file_location("workforce_status_dashboard", HELPER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load dashboard helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_enum_field(document: dict[str, object], field: str, value: str) -> None:
    group, key = field.split(".", 1)
    if group == "run":
        document["run"][key] = value
    elif group in {"progress", "lanes", "readiness", "artifacts", "gates", "decisions", "alerts"}:
        document[group][0][key] = value
    else:
        document[group][key] = value


def stat_mode(path: Path) -> int:
    return os.stat(path, follow_symlinks=False).st_mode & 0o777


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workforce-dashboard-test-") as temp_name:
        temp = Path(temp_name)
        root = temp / "private-status-root"
        status_file = temp / "status.json"
        status_file.write_text(json.dumps(payload("Initial fixture run", "2026-08-31T02:00:00Z")), encoding="utf-8")
        status_file.chmod(0o600)

        help_result = run("health", "--help")
        record("DB01", len(help_result.stdout) < 8000 and "--expected-root" in help_result.stdout, f"help_bytes={len(help_result.stdout)}")

        run(
            "init",
            "--root", str(root),
            "--run-id", "RUN-DASHBOARD-TEST",
            "--template", str(TEMPLATE),
            "--status-file", str(status_file),
        )
        run_dir = root / "runs" / "RUN-DASHBOARD-TEST"
        stored = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        record("DB02", stored["run"]["title"] == "Initial fixture run" and (run_dir / "index.html").is_file(), "initialized strict run files")

        private_modes = (
            stat_mode(root) == 0o700
            and stat_mode(root / "runs") == 0o700
            and stat_mode(run_dir) == 0o700
            and stat_mode(run_dir / "index.html") == 0o600
            and stat_mode(run_dir / "status.json") == 0o600
            and (run_dir / "index.html").stat().st_nlink == 1
            and (run_dir / "status.json").stat().st_nlink == 1
        )
        record("DB03", private_modes, "dashboard directories 0700 and served files 0600/single-link")

        previous_hash = hashlib.sha256((run_dir / "status.json").read_bytes()).hexdigest()
        invalid = payload("Unsafe widening", "2026-08-31T02:01:00Z")
        invalid["secret"] = "must reject"
        status_file.write_text(json.dumps(invalid), encoding="utf-8")
        rejected = run(
            "update", "--root", str(root), "--run-id", "RUN-DASHBOARD-TEST", "--status-file", str(status_file), expected=2
        )
        unchanged_hash = hashlib.sha256((run_dir / "status.json").read_bytes()).hexdigest()
        record("DB04", "unknown field" in rejected.stderr and unchanged_hash == previous_hash, "invalid update rejected; prior snapshot preserved")

        non_loopback = run("serve", "--root", str(root), "--bind", "0.0.0.0", "--port", "0", expected=2)
        record("DB05", "loopback" in non_loopback.stderr, "non-loopback bind rejected")

        unsafe_root = temp / "permissive-status-root"
        unsafe_root.mkdir(mode=0o700)
        unsafe_root.chmod(0o755)
        unsafe_result = run("health", "--root", str(unsafe_root), expected=2)
        record(
            "DB06",
            "mode 0700" in unsafe_result.stderr and stat_mode(unsafe_root) == 0o755,
            "pre-existing permissive root rejected without silent chmod",
        )

        valid_before_private_input = hashlib.sha256((run_dir / "status.json").read_bytes()).hexdigest()
        status_file.write_text(json.dumps(payload("Permissive input", "2026-08-31T02:01:30Z")), encoding="utf-8")
        status_file.chmod(0o644)
        unsafe_input = run(
            "update", "--root", str(root), "--run-id", "RUN-DASHBOARD-TEST", "--status-file", str(status_file), expected=2
        )
        record(
            "DB07",
            "mode 0600" in unsafe_input.stderr
            and hashlib.sha256((run_dir / "status.json").read_bytes()).hexdigest() == valid_before_private_input,
            "permissive status input rejected and accepted snapshot preserved",
        )
        status_file.chmod(0o600)

        helper_module = load_helper_module()
        enum_payload = payload("Enum fixture", "2026-08-31T02:01:45Z")
        enum_payload["lanes"] = [{"id": "L01", "name": "Lane", "state": "PLANNED", "owner": "fixture", "summary": "bounded", "last_observed_at": "2026-08-31T02:01:45Z", "next_action": "wait"}]
        enum_payload["artifacts"] = [{"id": "A01", "name": "artifact.bin", "state": "EXPECTED", "size_bytes": 0, "sha256": ""}]
        enum_payload["gates"] = [{"id": "G01", "label": "Gate", "kind": "MECHANICAL", "state": "NOT_RUN", "detail": "pending"}]
        enum_payload["decisions"] = [{"id": "D01", "label": "Decision", "state": "PENDING", "detail": "pending"}]
        enum_payload["alerts"] = [{"level": "info", "title": "Notice", "detail": "safe"}]
        enum_fields = {
            "run.status": helper_module.RUN_STATES,
            "run.allocation_profile": helper_module.ALLOCATION_PROFILES,
            "run.codex_usage_band": helper_module.CODEX_USAGE_BANDS,
            "run.route": helper_module.ROUTES,
            "run.freshness": helper_module.FRESHNESS_STATES,
            "progress.state": helper_module.PROGRESS_STATES,
            "lanes.state": helper_module.LANE_STATES,
            "readiness.state": helper_module.READINESS_STATES,
            "artifacts.state": helper_module.ARTIFACT_STATES,
            "gates.kind": helper_module.GATE_KINDS,
            "gates.state": helper_module.GATE_STATES,
            "decisions.state": helper_module.DECISION_STATES,
            "storage.state": helper_module.SUMMARY_STATES,
            "notes.state": helper_module.SUMMARY_STATES,
            "alerts.level": helper_module.ALERT_LEVELS,
        }
        accepted_tokens = 0
        rejected_foreign = 0
        all_tokens = set().union(*enum_fields.values())
        enum_ok = True
        for field, allowed in enum_fields.items():
            for token in allowed:
                candidate = deepcopy(enum_payload)
                set_enum_field(candidate, field, token)
                try:
                    helper_module._validate_status(candidate, "RUN-DASHBOARD-TEST")
                    accepted_tokens += 1
                except helper_module.DashboardError:
                    enum_ok = False
            for token in all_tokens - allowed:
                candidate = deepcopy(enum_payload)
                set_enum_field(candidate, field, token)
                try:
                    helper_module._validate_status(candidate, "RUN-DASHBOARD-TEST")
                    enum_ok = False
                except helper_module.DashboardError:
                    rejected_foreign += 1
            for token in ("UNHEALTHY", "NOT_READY", "NOT_ACCEPTED", "INCOMPLETE", "NOT_CURRENT", "ARBITRARY"):
                candidate = deepcopy(enum_payload)
                set_enum_field(candidate, field, token)
                try:
                    helper_module._validate_status(candidate, "RUN-DASHBOARD-TEST")
                    enum_ok = False
                except helper_module.DashboardError:
                    rejected_foreign += 1
        record(
            "DB08",
            enum_ok and accepted_tokens == sum(len(values) for values in enum_fields.values()),
            f"exact enum tokens accepted={accepted_tokens}; foreign/lookalike rejects={rejected_foreign}",
        )

        html_source = TEMPLATE.read_text(encoding="utf-8")
        def js_set(name: str) -> set[str]:
            match = re.search(rf"const {name} = new Set\(\[(.*?)\]\);", html_source, re.S)
            if match is None:
                return set()
            return set(re.findall(r'"([A-Za-z0-9_]+)"', match.group(1)))

        expected_good = {"ACCEPTED", "ACTIVE", "APPROVED", "AVAILABLE_VERIFIED", "COMPLETE", "FULL_BROWSER_AND_DESKTOP", "BROWSER_ONLY", "HEALTHY", "LOCAL_CODEX_ONLY", "MECHANICAL_ACCEPTED", "PASS", "READY", "RECOVERED", "RETURNED", "RUNNING", "RUNNING_HEALTHY", "SEMANTIC_ACCEPTED"}
        expected_bad = {"BLOCKED", "BROWSER_DISCONNECTED", "DISABLED", "FAIL", "MISCONFIGURED", "NOT_AUTHORIZED", "NOT_AVAILABLE", "NOT_RECOVERABLE", "REJECTED", "STALLED", "TERMINAL_INCOMPLETE", "MECHANICAL_REJECTED", "SEMANTIC_REJECTED"}
        expected_warn = {"AVAILABLE_UNTESTED", "BROWSER_WITH_MANUAL_DESKTOP", "CANDIDATE", "DEFERRED", "DEGRADED", "DRAFT", "DUPLICATE", "EXPECTED", "LIMIT_PAUSED", "MANUAL_ACTION_REQUIRED", "MANUAL_BROWSER_HANDOFF", "NOT_RUN", "OPEN", "PARTIAL", "PAUSED", "PAUSING", "PENDING", "PLANNED", "PREFLIGHTED", "RAW", "RESUMING", "RUNNING_WITH_TRANSIENT_ERROR", "SLOW_NO_FAILURE_EVIDENCE", "STALE", "SUBMITTED", "TEMPORARY", "TERMINAL_PARTIAL_ARTIFACT_RETURN", "UNKNOWN"}
        tone_sets_ok = (
            js_set("GOOD_STATES") == expected_good
            and js_set("BAD_STATES") == expected_bad
            and js_set("WARNING_STATES") == expected_warn
            and not ({"UNHEALTHY", "NOT_READY", "NOT_ACCEPTED", "INCOMPLETE", "NOT_CURRENT"} & (expected_good | expected_bad | expected_warn))
            and 'new Set(["RECOVERED", "ACCEPTED"])' in html_source
            and "/ACCEPTED|PASS|READY" not in html_source
        )
        record("DB09", tone_sets_ok, "exact token tone sets and exact recovered-artifact count verified")

        hostile_key = "\x1b[31m" + "X" * 600
        hostile = payload("Terminal canary", "2026-08-31T02:01:50Z")
        hostile[hostile_key] = "ignored"
        status_file.write_text(json.dumps(hostile), encoding="utf-8")
        status_file.chmod(0o600)
        hostile_result = run(
            "update", "--root", str(root), "--run-id", "RUN-DASHBOARD-TEST", "--status-file", str(status_file), expected=2
        )
        record(
            "DB19",
            "\x1b" not in hostile_result.stderr
            and hostile_key not in hostile_result.stderr
            and len(hostile_result.stderr) < 500,
            "terminal diagnostic escaped/suppressed hostile field name and remained bounded",
        )

        server = subprocess.Popen(
            [sys.executable, str(HELPER), "serve", "--root", str(root), "--bind", "127.0.0.1", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert server.stdout is not None
            base = server.stdout.readline().strip()
            if not base.startswith("http://127.0.0.1:"):
                raise AssertionError(f"unexpected server URL: {base!r}")
            port = base.split(":")[-1].rstrip("/")
            health_ok = False
            for _ in range(20):
                try:
                    check = run(
                        "health", "--host", "127.0.0.1", "--port", port, "--expected-root", str(root)
                    )
                    health_ok = json.loads(check.stdout)["status"] == "ok"
                    break
                except (AssertionError, OSError):
                    time.sleep(0.05)
            record("DB10", health_ok, "exact-root loopback health verified")

            status, page, headers = fetch(f"{base}runs/RUN-DASHBOARD-TEST/")
            required_headers = (
                headers.get("Cache-Control", "").startswith("no-store")
                and "default-src 'none'" in headers.get("Content-Security-Policy", "")
                and headers.get("X-Frame-Options") == "DENY"
            )
            record("DB11", status == 200 and b'data-dashboard-shell="workforce-status-v2"' in page and required_headers, "v2 page served with CSP/no-store/frame denial")

            verified = run(
                "verify", "--host", "127.0.0.1", "--port", port,
                "--expected-root", str(root), "--run-id", "RUN-DASHBOARD-TEST",
            )
            verified_payload = json.loads(verified.stdout)
            record(
                "DB21",
                verified_payload.get("status") == "ok"
                and verified_payload.get("run_id") == "RUN-DASHBOARD-TEST"
                and verified_payload.get("page_url", "").endswith("/runs/RUN-DASHBOARD-TEST/"),
                "exact server, run page, and snapshot verified",
            )

            missing_run = run(
                "verify", "--host", "127.0.0.1", "--port", port,
                "--expected-root", str(root), "--run-id", "RUN-MISSING",
                expected=2,
            )
            record("DB22", "run_page_unavailable" in missing_run.stderr, "missing run page classified")

            control_surface = all(
                term in page
                for term in (
                    b"Copy-only controls",
                    b"$chatgpt-pro-workforce tell me more {RUN_ID}",
                    b"$chatgpt-pro-workforce change concurrency {RUN_ID}",
                    b"$chatgpt-pro-workforce uninstall",
                    b"copy-command",
                )
            ) and b"<form" not in page and b"fetch(`status.json" in page
            record("DB12", control_surface, "complete copy-only help/concurrency/uninstall surface served without action endpoint")

            traversal_status, _, _ = fetch(f"{base}../status.json")
            dotfile_status, _, _ = fetch(f"{base}runs/RUN-DASHBOARD-TEST/.secret.json")
            arbitrary_status, _, _ = fetch(f"{base}unrelated.txt")
            record("DB13", traversal_status == 404 and dotfile_status == 404 and arbitrary_status == 404, f"traversal={traversal_status}; dotfile={dotfile_status}; arbitrary={arbitrary_status}")

            bad_host_status, _, _ = fetch(f"{base}healthz", host="example.invalid")
            record("DB14", bad_host_status == 403, f"bad_host={bad_host_status}")

            raw_host_results = [
                raw_http_status(int(port), []),
                raw_http_status(int(port), [f"localhost:{port}", f"localhost:{port}"]),
                raw_http_status(int(port), ["[::1]attacker.invalid:1"]),
                raw_http_status(int(port), ["localhost:attacker"]),
                raw_http_status(int(port), [f"user@localhost:{port}"]),
            ]
            record("DB15", raw_host_results == [403, 403, 403, 403, 403], f"malformed/missing Host results={raw_host_results}")

            status_file.write_text(json.dumps(payload("Refreshed fixture run", "2026-08-31T02:02:00Z")), encoding="utf-8")
            run("update", "--root", str(root), "--run-id", "RUN-DASHBOARD-TEST", "--status-file", str(status_file))
            status_code, current, headers = fetch(f"{base}runs/RUN-DASHBOARD-TEST/status.json")
            refreshed = json.loads(current)
            record("DB16", status_code == 200 and refreshed["run"]["title"] == "Refreshed fixture run" and headers.get("Cache-Control", "").startswith("no-store"), "live server observed atomic refreshed snapshot")

            served_status = run_dir / "status.json"
            served_status.chmod(0o644)
            permissive_served, _, _ = fetch(f"{base}runs/RUN-DASHBOARD-TEST/status.json")
            served_status.chmod(0o600)
            hardlink = temp / "status-hardlink.json"
            os.link(served_status, hardlink)
            hardlinked_served, _, _ = fetch(f"{base}runs/RUN-DASHBOARD-TEST/status.json")
            hardlink.unlink()
            run_dir.chmod(0o755)
            permissive_directory, _, _ = fetch(f"{base}runs/RUN-DASHBOARD-TEST/status.json")
            run_dir.chmod(0o700)
            record(
                "DB20",
                (permissive_served, hardlinked_served, permissive_directory) == (404, 404, 404),
                f"descriptor guard results={(permissive_served, hardlinked_served, permissive_directory)}",
            )

            wrong_root = temp / "other-private-status-root"
            wrong_root.mkdir(mode=0o700)
            wrong_root.chmod(0o700)
            wrong_health = run(
                "health", "--host", "127.0.0.1", "--port", port, "--expected-root", str(wrong_root), expected=2
            )
            record("DB17", "health check failed" in wrong_health.stderr, "wrong-root server identity rejected")

            valid_status_bytes = served_status.read_bytes()
            served_status.write_text("{malformed", encoding="utf-8")
            served_status.chmod(0o600)
            malformed = run(
                "verify", "--host", "127.0.0.1", "--port", port,
                "--expected-root", str(root), "--run-id", "RUN-DASHBOARD-TEST",
                expected=2,
            )
            served_status.write_bytes(valid_status_bytes)
            served_status.chmod(0o600)
            record("DB23", "status_snapshot_invalid" in malformed.stderr, "malformed snapshot classified without mutation")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        record("DB18", server.poll() is not None, "temporary dashboard server stopped")
        dead_server = run(
            "verify", "--host", "127.0.0.1", "--port", port,
            "--expected-root", str(root), "--run-id", "RUN-DASHBOARD-TEST",
            expected=2,
        )
        record("DB24", "server_unavailable" in dead_server.stderr, "stopped server classified")

    failures = [item for item in RESULTS if item[1] == FAIL]
    for case_id, classification, evidence in RESULTS:
        print(f"{case_id}|{classification}|{evidence}")
    print(f"TOTAL={len(RESULTS)}")
    print(f"LIVE_PASS={len(RESULTS) - len(failures)}")
    print(f"LIVE_FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
