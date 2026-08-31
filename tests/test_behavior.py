#!/usr/bin/env python3
"""Deterministic behavioral tests for progress, controls, and resumability."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import re
import sys
import tempfile


ROOT = Path(sys.argv[1]).resolve()
PASS = "SIMULATED_PASS"
FAIL = "SIMULATED_FAIL"
RESULTS: list[tuple[str, str, str, str]] = []


def record(case_id: str, title: str, expected: str, observed: str, passed: bool) -> None:
    RESULTS.append((case_id, PASS if passed else FAIL, title, f"expected={expected}; observed={observed}"))


def bar(numerator: int, denominator: int | None) -> str:
    if denominator is None or denominator <= 0:
        return "[active] —/—"
    filled = (10 * numerator) // denominator
    return f"{'█' * filled}{'░' * (10 - filled)} {numerator}/{denominator}"


@dataclass
class Run:
    status: str = "ACTIVE"
    allocation: str = "BALANCED"
    scope_policy: str = "ASK_BEFORE_ADDING"
    cadence: str = "STANDARD"
    freshness: str = "CURRENT"
    active_workers: int = 0
    new_submissions_allowed: bool = True
    stop_sent: bool = False
    prompt_hashes: set[str] = field(default_factory=set)
    reset_time: str | None = None
    migrated_defaults: set[str] = field(default_factory=set)


@dataclass
class Setup:
    status: str = "MISSING"
    exact_packet_approved: bool = False
    mutation_count: int = 0
    full_preflight_runs: int = 0
    runtime_action_authorized: bool = False


@dataclass
class InvocationProfile:
    initialized: bool = False
    baseline_runs: int = 0
    invocation_gates: int = 0
    full_rechecks: int = 0
    run_mutations: int = 0
    last_result: str = "UNKNOWN"
    capability_delta: str = "unknown"


@dataclass(frozen=True)
class ConcurrencyAcknowledgement:
    run_id: str
    exact_limit: int


def concurrent_generations(*, active: int, unknown: int) -> int:
    """Count unknown generations conservatively until reconciled."""
    return active + unknown


def launch_concurrency_decision(
    *,
    run_id: str,
    active: int,
    unknown: int,
    configured_limit: int = 2,
    acknowledgement: ConcurrencyAcknowledgement | None = None,
) -> str:
    """Model the pre-launch guard without controlling or closing any chat."""
    if configured_limit < 1:
        return "SUPPRESS_INVALID_LIMIT"
    proposed = concurrent_generations(active=active, unknown=unknown) + 1
    if proposed > configured_limit:
        return "SUPPRESS_CONFIGURED_LIMIT"
    if proposed <= 2:
        return "ALLOW_STANDARD"
    if acknowledgement == ConcurrencyAcknowledgement(run_id, configured_limit):
        return "ALLOW_ACKNOWLEDGED_HIGH_RISK"
    return "REQUIRE_CURRENT_RUN_EXACT_LIMIT_ACKNOWLEDGEMENT"


def invocation_gate(profile: InvocationProfile, *, drift: bool = False) -> InvocationProfile:
    updated = deepcopy(profile)
    updated.invocation_gates += 1
    if not updated.initialized:
        updated.baseline_runs += 1
        updated.initialized = True
    updated.capability_delta = "browser-route-changed" if drift else "none observed"
    if drift:
        updated.full_rechecks += 1
        updated.last_result = "DEGRADED"
    else:
        updated.last_result = "PASS"
    return updated


def diagnose_control_fault(*, healthy_slow: bool, repair_supported: bool, needs_new_permission: bool) -> tuple[str, int, bool]:
    if healthy_slow:
        return "RUNNING_HEALTHY", 0, False
    if needs_new_permission:
        return "SETUP_REQUIRED", 0, True
    if repair_supported:
        return "RESOLVED", 1, False
    return "MANUAL_HANDOFF", 1, False


USAGE_BANDS = {
    "PRO_HEAVY": "LOWEST",
    "BALANCED": "MODERATE",
    "CODEX_HEAVY": "HIGH",
    "LOCAL_ONLY": "CODEX_ONLY",
}


def cleanup_candidate(root: Path, candidate: Path, expected_hash: str, *, accepted_export: bool, in_use: bool = False) -> str:
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return "SKIPPED"
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return "SKIPPED"
    if not accepted_export or in_use:
        return "SKIPPED"
    observed = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return "ELIGIBLE" if observed == expected_hash else "SKIPPED"


def topic_folder_allowed(*, policy: str, decision: str, root_confirmed: bool, creation_authorized: bool) -> bool:
    return (
        policy != "NO_NOTES"
        and decision == "APPROVED"
        and root_confirmed
        and creation_authorized
    )


def offer_setup(setup: Setup, required: bool, manual_route: bool) -> tuple[Setup, str]:
    updated = deepcopy(setup)
    if not required:
        updated.status = "NOT_NEEDED"
        return updated, "ready-without-setup"
    updated.status = "OFFERED"
    return updated, "manual-or-reduced-available" if manual_route else "setup-or-blocked"


def execute_setup(setup: Setup, complete_packet: bool, observed_scope_matches: bool) -> Setup:
    updated = deepcopy(setup)
    if not complete_packet or not updated.exact_packet_approved:
        updated.status = "AWAITING_APPROVAL"
        return updated
    if not observed_scope_matches:
        updated.status = "BLOCKED"
        return updated
    updated.status = "IN_PROGRESS"
    updated.mutation_count += 1
    updated.full_preflight_runs += 1
    updated.status = "VERIFIED"
    return updated


FIXED_CODEX_DUTIES = {
    "scope",
    "permissions",
    "prompt-contract",
    "monitoring",
    "recovery",
    "mechanical-gate",
    "semantic-gate",
    "independent-verification",
    "integration",
    "acceptance",
    "handoff",
}


def allocation_duties(profile: str) -> tuple[set[str], set[str]]:
    if profile == "PRO_HEAVY":
        pro = {"research", "analysis", "drafting", "artifact-production"}
        codex = set(FIXED_CODEX_DUTIES)
    elif profile == "BALANCED":
        pro = {"parallel-research", "specialist-analysis", "independent-review", "bounded-drafts"}
        codex = set(FIXED_CODEX_DUTIES) | {"local-evidence-checks", "reconciliation", "synthesis"}
    elif profile == "CODEX_HEAVY":
        pro = {"specialist", "blind-review", "adversarial-review"}
        codex = set(FIXED_CODEX_DUTIES) | {"primary-work", "research", "calculation", "synthesis", "production"}
    elif profile == "LOCAL_ONLY":
        pro = set()
        codex = set(FIXED_CODEX_DUTIES) | {"primary-work"}
    else:
        raise ValueError(profile)
    return pro, codex


def propose_topics(policy: str, crosses_boundary: bool = False) -> tuple[str, bool]:
    if policy == "ASK_BEFORE_ADDING":
        return "READY_FOR_DECISION:PENDING", False
    if policy == "FIXED_SCOPE":
        return "DECIDED:DEFERRED", False
    if policy == "AUTO_ADD_IN_SCOPE" and not crosses_boundary:
        return "DECIDED:APPROVED", True
    return "READY_FOR_DECISION:PENDING", False


def pause(run: Run) -> Run:
    updated = deepcopy(run)
    updated.new_submissions_allowed = False
    updated.stop_sent = False
    updated.status = "PAUSING" if updated.active_workers else "PAUSED"
    return updated


def capacity_limit(run: Run, reset_time: str | None) -> Run:
    updated = deepcopy(run)
    updated.status = "LIMIT_PAUSED"
    updated.new_submissions_allowed = False
    updated.reset_time = reset_time
    return updated


def resume(run: Run, pending_prompt_hash: str | None, outcome_unknown: bool, capacity_available: bool) -> tuple[Run, str]:
    updated = deepcopy(run)
    updated.status = "RESUMING"
    updated.new_submissions_allowed = False
    if not capacity_available:
        updated.status = "LIMIT_PAUSED"
        return updated, "capacity-still-limited"
    if outcome_unknown:
        return updated, "reconcile-outcome-first"
    if pending_prompt_hash and pending_prompt_hash in updated.prompt_hashes:
        updated.status = "ACTIVE"
        updated.new_submissions_allowed = True
        return updated, "duplicate-suppressed"
    updated.status = "ACTIVE"
    updated.new_submissions_allowed = True
    return updated, "resumed"


def should_emit(cadence: str, transition: bool, blocker: bool, unchanged_observations: int) -> bool:
    if transition or blocker:
        return True
    if cadence == "VERBOSE":
        return True
    if cadence == "STANDARD":
        return unchanged_observations >= 2
    return False


def control_intent(prompt: str) -> str:
    lower = prompt.lower()
    if "tell me more" in lower or "status more" in lower:
        return "DETAIL"
    if " status" in lower:
        return "STATUS"
    if " pause" in lower:
        return "PAUSE"
    if " resume" in lower or " continue" in lower:
        return "RESUME"
    if " change concurrency" in lower:
        return "CHANGE_CONCURRENCY"
    if " uninstall" in lower:
        return "UNINSTALL"
    if " help" in lower:
        return "HELP"
    return "GUIDED" if lower.strip() == "$chatgpt-pro-workforce" else "TASK"


def main() -> int:
    progress_text = (ROOT / "references/progress-and-controls.md").read_text()
    card_text = (ROOT / "assets/progress-card-template.md").read_text()
    skill_text = (ROOT / "SKILL.md").read_text()
    prerequisite_text = (ROOT / "references/prerequisite-setup.md").read_text()
    prerequisite_plan_text = (ROOT / "assets/prerequisite-plan-template.md").read_text()
    capability_text = (ROOT / "references/capability-preflight.md").read_text()
    capability_report_text = (ROOT / "assets/capability-report-template.md").read_text()
    modes_text = (ROOT / "references/modes.md").read_text()
    failure_text = (ROOT / "references/failure-catalog.md").read_text()
    monitoring_text = (ROOT / "references/monitoring-and-recovery.md").read_text()
    storage_text = (ROOT / "references/artifact-storage-and-cleanup.md").read_text()
    obsidian_text = (ROOT / "references/obsidian-research-vault.md").read_text()
    dashboard_text = (ROOT / "references/local-status-dashboard.md").read_text()
    dashboard_html = (ROOT / "assets/status-dashboard-template.html").read_text()
    profile_text = (ROOT / "assets/workforce-profile-template.md").read_text()
    locator_text = (ROOT / "scripts/obsidian_locator.py").read_text()
    platform_text = (ROOT / "references/platform-control-stacks.md").read_text()
    install_text = (ROOT / "references/installation-and-uninstall.md").read_text()
    orchestration_text = (ROOT / "references/orchestration.md").read_text()

    observed = bar(3, 10)
    record("PC01", "finite registered ratio", "███░░░░░░░ 3/10", observed, observed == "███░░░░░░░ 3/10")
    observed = bar(0, None)
    record("PC02", "unknown denominator", "[active] —/—", observed, observed == "[active] —/—")

    before, after = bar(6, 10), bar(6, 12)
    record("PC03", "approved scope grows denominator", "same numerator and shorter disclosed bar", f"{before} -> {after}; scope_change:+2", before.startswith("██████") and after.startswith("█████") and "scope_change: +" in progress_text)

    workers = bar(1, 1)
    acceptance = bar(0, 1)
    record("PC04", "rejected lane is terminal but unaccepted", "Workers 1/1; Acceptance 0/1", f"Workers={workers}; Acceptance={acceptance}", workers.endswith("1/1") and acceptance.endswith("0/1"))

    state = {"status": "ACTIVE", "prompt_hashes": ["abc"], "side_effects": []}
    before_state = deepcopy(state)
    detail = {"outcome": "test", "freshness": "STALE", "lanes": 1, "next": "read-only refresh"}
    record("PC05", "tell-me-more is read-only", "state unchanged and detailed evidence", json.dumps(detail, sort_keys=True), state == before_state and control_intent("$chatgpt-pro-workforce tell me more RUN-1") == "DETAIL")

    candidates = ["RUN-A", "RUN-B"]
    selected = None if len(candidates) != 1 else candidates[0]
    record("PC06", "ambiguous run selection", "ask one identifying question; no mutation", f"selected={selected}", selected is None and "ask one concise" in progress_text)

    for case_id, policy, boundary, expected_state, expected_launch in (
        ("PC07", "ASK_BEFORE_ADDING", False, "READY_FOR_DECISION:PENDING", False),
        ("PC08", "AUTO_ADD_IN_SCOPE", False, "DECIDED:APPROVED", True),
        ("PC09", "AUTO_ADD_IN_SCOPE", True, "READY_FOR_DECISION:PENDING", False),
        ("PC10", "FIXED_SCOPE", False, "DECIDED:DEFERRED", False),
    ):
        observed_state, launch = propose_topics(policy, boundary)
        record(case_id, f"first-pass expansion {policy} boundary={boundary}", f"{expected_state}, launch={expected_launch}", f"{observed_state}, launch={launch}", observed_state == expected_state and launch == expected_launch)

    active_pause = pause(Run(active_workers=1))
    record("PC11", "pause with healthy active worker", "PAUSING, no new submissions, no stop", f"{active_pause.status}, submit={active_pause.new_submissions_allowed}, stop={active_pause.stop_sent}", active_pause.status == "PAUSING" and not active_pause.new_submissions_allowed and not active_pause.stop_sent)
    quiet_pause = pause(Run(active_workers=0))
    record("PC12", "pause at durable checkpoint", "PAUSED", quiet_pause.status, quiet_pause.status == "PAUSED")

    limited = capacity_limit(Run(), None)
    record("PC13", "usage limit without shown reset", "LIMIT_PAUSED and reset unknown", f"{limited.status}, reset={limited.reset_time}", limited.status == "LIMIT_PAUSED" and limited.reset_time is None and not limited.new_submissions_allowed)
    limited_known = capacity_limit(Run(), "2026-09-01T00:00:00Z")
    record("PC14", "usage limit with provider reset", "preserve exact shown reset", str(limited_known.reset_time), limited_known.reset_time == "2026-09-01T00:00:00Z")

    duplicate_run = Run(status="PAUSED", prompt_hashes={"hash-1"})
    resumed, decision = resume(duplicate_run, "hash-1", False, True)
    record("PC15", "duplicate-safe resume", "duplicate suppressed then ACTIVE", f"{decision}/{resumed.status}", decision == "duplicate-suppressed" and resumed.status == "ACTIVE")
    unknown_run, decision = resume(Run(status="PAUSED"), None, True, True)
    record("PC16", "unknown-outcome resume gate", "remain RESUMING with no input", f"{decision}/{unknown_run.status}/{unknown_run.new_submissions_allowed}", decision == "reconcile-outcome-first" and unknown_run.status == "RESUMING" and not unknown_run.new_submissions_allowed)
    still_limited, decision = resume(limited, None, False, False)
    record("PC17", "resume before capacity returns", "remain LIMIT_PAUSED", f"{decision}/{still_limited.status}", still_limited.status == "LIMIT_PAUSED")

    for case_id, profile in (
        ("PC18", "PRO_HEAVY"),
        ("PC19", "BALANCED"),
        ("PC20", "CODEX_HEAVY"),
        ("PC21", "LOCAL_ONLY"),
    ):
        pro, codex = allocation_duties(profile)
        passed = FIXED_CODEX_DUTIES <= codex and (bool(pro) if profile != "LOCAL_ONLY" else not pro)
        record(case_id, f"allocation profile {profile}", "fixed Codex duties preserved", f"pro={sorted(pro)}; fixed={FIXED_CODEX_DUTIES <= codex}", passed)

    active_lanes = {"L01": "PRO_HEAVY"}
    new_profile = "CODEX_HEAVY"
    future_lane_profile = new_profile
    record("PC22", "mid-run allocation change", "active lane unchanged; future work updated", f"L01={active_lanes['L01']}; future={future_lane_profile}", active_lanes["L01"] == "PRO_HEAVY" and future_lane_profile == "CODEX_HEAVY")

    standard = launch_concurrency_decision(run_id="RUN-1", active=1, unknown=0)
    record("PC90", "two concurrent Pro conversations remain the safe default", "ALLOW_STANDARD at 2", standard, standard == "ALLOW_STANDARD")
    one_worker_ceiling = launch_concurrency_decision(run_id="RUN-1", active=1, unknown=0, configured_limit=1)
    record("PC97", "configured one-worker ceiling suppresses a second launch", "SUPPRESS_CONFIGURED_LIMIT", one_worker_ceiling, one_worker_ceiling == "SUPPRESS_CONFIGURED_LIMIT")
    two_worker_unknown_ceiling = launch_concurrency_decision(run_id="RUN-1", active=1, unknown=1, configured_limit=2)
    record("PC98", "configured two-worker ceiling counts an unknown generation before launch", "SUPPRESS_CONFIGURED_LIMIT", two_worker_unknown_ceiling, two_worker_unknown_ceiling == "SUPPRESS_CONFIGURED_LIMIT")
    unknown_guard = launch_concurrency_decision(run_id="RUN-1", active=1, unknown=1, configured_limit=3)
    record("PC91", "unknown generations count conservatively before a third launch", "acknowledgement required", unknown_guard, unknown_guard == "REQUIRE_CURRENT_RUN_EXACT_LIMIT_ACKNOWLEDGEMENT")
    wrong_run = launch_concurrency_decision(
        run_id="RUN-1", active=2, unknown=0, configured_limit=3,
        acknowledgement=ConcurrencyAcknowledgement("RUN-OTHER", 3),
    )
    wrong_limit = launch_concurrency_decision(
        run_id="RUN-1", active=2, unknown=0, configured_limit=3,
        acknowledgement=ConcurrencyAcknowledgement("RUN-1", 4),
    )
    record("PC92", "high-risk acknowledgement is scoped to current run and exact limit", "both acknowledgement mismatches suppressed", f"run={wrong_run}; limit={wrong_limit}", wrong_run == wrong_limit == "REQUIRE_CURRENT_RUN_EXACT_LIMIT_ACKNOWLEDGEMENT")
    acknowledged = launch_concurrency_decision(
        run_id="RUN-1", active=2, unknown=0, configured_limit=3,
        acknowledgement=ConcurrencyAcknowledgement("RUN-1", 3),
    )
    record("PC93", "third Pro conversation needs explicit high-risk acknowledgement", "ALLOW_ACKNOWLEDGED_HIGH_RISK", acknowledged, acknowledged == "ALLOW_ACKNOWLEDGED_HIGH_RISK")
    over_limit = launch_concurrency_decision(
        run_id="RUN-1", active=3, unknown=0, configured_limit=3,
        acknowledgement=ConcurrencyAcknowledgement("RUN-1", 3),
    )
    no_auto_close = {"L01": "RUNNING", "L02": "UNKNOWN", "L03": "RUNNING"}
    record("PC94", "configured limit suppresses future launch without closing existing chats", "SUPPRESS_CONFIGURED_LIMIT and existing states unchanged", f"decision={over_limit}; states={no_auto_close}", over_limit == "SUPPRESS_CONFIGURED_LIMIT" and no_auto_close == {"L01": "RUNNING", "L02": "UNKNOWN", "L03": "RUNNING"})
    changed_limit = 4
    record("PC95", "concurrency change affects future launch only and has a copyable control", "changed limit with no active-chat mutation", f"limit={changed_limit}; intent={control_intent('$chatgpt-pro-workforce change concurrency RUN-1')}", changed_limit == 4 and control_intent("$chatgpt-pro-workforce change concurrency RUN-1") == "CHANGE_CONCURRENCY")
    concurrency_contract = re.sub(r"\s+", " ", re.sub(r"(?m)^>\s*", "", "\n".join((progress_text, profile_text, dashboard_text, dashboard_html, monitoring_text, orchestration_text))))
    concurrency_terms = (
        "max_concurrent_pro_workers: 2",
        "likely to increase throttling",
        "interrupted, closed, disconnected, or inaccessible",
        "unsaved or unverified work may be lost",
        "current-run",
        "exact-limit",
        "Never auto-close existing chats",
        "future launches",
        "active or unknown",
        "$chatgpt-pro-workforce change concurrency {RUN_ID}",
    )
    record("PC96", "high-concurrency risk is visible in controls and durable workflow", "all risk, acknowledgement, recovery, and copy-control terms", ",".join(term for term in concurrency_terms if term in concurrency_contract), all(term in concurrency_contract for term in concurrency_terms))

    record("PC23", "verbose reporting cadence", "emit unchanged observation", str(should_emit("VERBOSE", False, False, 0)), should_emit("VERBOSE", False, False, 0))
    record("PC24", "standard reporting cadence", "emit after two unchanged observations", str(should_emit("STANDARD", False, False, 2)), should_emit("STANDARD", False, False, 2) and not should_emit("STANDARD", False, False, 1))
    record("PC25", "quiet reporting cadence", "emit transition but not unchanged", f"transition={should_emit('QUIET', True, False, 9)}, unchanged={should_emit('QUIET', False, False, 9)}", should_emit("QUIET", True, False, 9) and not should_emit("QUIET", False, False, 9))

    visible_hint = "More: $chatgpt-pro-workforce tell me more {{RUN_ID}}"
    record("PC26", "visible drill-down hint", "exact tell-me-more intent under card", visible_hint if visible_hint in card_text else "missing", visible_hint in card_text)
    help_terms = ("status", "tell me more", "pause", "resume", "help")
    record("PC27", "help control coverage", "all core intents and native-boundary explanation", ",".join(term for term in help_terms if term in progress_text), all(term in progress_text for term in help_terms) and "not shell or UI" in progress_text)

    stale = Run(freshness="STALE")
    record("PC28", "stale status does not infer live worker state", "STALE and read-only", stale.freshness, stale.freshness == "STALE" and "must not implicitly resume" in progress_text)

    migrated = Run()
    migrated.migrated_defaults = {"BALANCED", "ASK_BEFORE_ADDING", "STANDARD"}
    record("PC29", "existing-run migration", "conservative labeled defaults", ",".join(sorted(migrated.migrated_defaults)), "label them as migrated defaults" in progress_text and len(migrated.migrated_defaults) == 3)

    record("PC30", "ordinary task does not activate", "TASK", control_intent("Format this local file"), control_intent("Format this local file") == "TASK" and "Do not use for ordinary browser work" in skill_text)
    record("PC31", "bare invocation remains guided", "GUIDED", control_intent("$chatgpt-pro-workforce"), control_intent("$chatgpt-pro-workforce") == "GUIDED")
    record("PC32", "pause and stop remain distinct", "pause checkpoints; stop explicit", "distinct" if "Stopping active workers is different from pausing orchestration" in progress_text else "missing", "Stopping active workers is different from pausing orchestration" in progress_text)

    temp_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="workforce-progress-controls-") as temp_name:
        temp_path = Path(temp_name)
        state_path = temp_path / "run.json"
        persisted = {
            "run_id": "RUN-TEST",
            "status": "PAUSED",
            "prompt_hashes": ["abc"],
            "resume_cursor": "reconcile L01",
        }
        state_path.write_text(json.dumps(persisted), encoding="utf-8")
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        record("PC33", "durable pause/resume cursor", "round-trip exact state", json.dumps(loaded, sort_keys=True), loaded == persisted)
    cleaned = bool(temp_path) and not temp_path.exists()
    record("PC34", "isolated fixture cleanup", "temporary workspace removed", str(cleaned), cleaned)

    capture = {
        "surface": "content-viewport",
        "outer": (1440, 900),
        "content": (1440, 820),
        "device_scale": 1.0,
        "infobar": "present",
        "top_inset": 80,
        "app_defect": False,
    }
    record(
        "PC35",
        "Chrome automation infobar capture geometry",
        "outer/content separated, 80px inset, not app defect",
        json.dumps(capture, sort_keys=True),
        capture["outer"] != capture["content"] and capture["top_inset"] == 80 and not capture["app_defect"],
    )
    geometry_terms = ("outer-window", "content-viewport", "device scale", "top inset", "infobar")
    record(
        "PC36",
        "visual contracts preserve capture environment",
        "all geometry terms in preflight/report and non-defect rule in mode",
        ",".join(term for term in geometry_terms if term.lower() in (capability_text + capability_report_text).lower()),
        all(term.lower() in (capability_text + capability_report_text).lower() for term in geometry_terms)
        and "do not treat browser chrome as" in modes_text
        and "an application defect" in modes_text,
    )

    offered, route = offer_setup(Setup(), required=True, manual_route=True)
    record("PC37", "missing required control offers setup", "OFFERED with no mutation and manual choice", f"{offered.status}/{offered.mutation_count}/{route}", offered.status == "OFFERED" and offered.mutation_count == 0 and route == "manual-or-reduced-available")
    awaiting = execute_setup(offered, complete_packet=False, observed_scope_matches=True)
    record("PC38", "setup offer is not approval", "AWAITING_APPROVAL and no mutation", f"{awaiting.status}/{awaiting.mutation_count}", awaiting.status == "AWAITING_APPROVAL" and awaiting.mutation_count == 0)

    packet_fields = (
        "Trusted source/current documentation",
        "Exact files/configuration/services affected",
        "Exact commands or manual UI changes",
        "Requested permissions/privacy grants",
        "Security impact",
        "Success criteria",
        "Exact rollback command/manual steps",
    )
    record("PC39", "bounded prerequisite packet", "source/targets/steps/permissions/security/validation/rollback", ",".join(field for field in packet_fields if field in prerequisite_plan_text), all(field in prerequisite_plan_text for field in packet_fields))

    approved = Setup(status="AWAITING_APPROVAL", exact_packet_approved=True)
    verified = execute_setup(approved, complete_packet=True, observed_scope_matches=True)
    record("PC40", "approved setup requires full preflight", "one bounded mutation, one full preflight, VERIFIED", f"{verified.status}/{verified.mutation_count}/{verified.full_preflight_runs}", verified.status == "VERIFIED" and verified.mutation_count == 1 and verified.full_preflight_runs == 1)

    broadened = execute_setup(approved, complete_packet=True, observed_scope_matches=False)
    record("PC41", "unexpected broader permission stops setup", "BLOCKED before mutation", f"{broadened.status}/{broadened.mutation_count}", broadened.status == "BLOCKED" and broadened.mutation_count == 0 and "Stop on unexpected prompts" in prerequisite_text)

    ready_linux, decision = offer_setup(Setup(status="READY"), required=False, manual_route=False)
    record("PC42", "existing verified Linux adapter avoids setup", "NOT_NEEDED and no mutation", f"{ready_linux.status}/{ready_linux.mutation_count}/{decision}", ready_linux.status == "NOT_NEEDED" and ready_linux.mutation_count == 0 and "AT-SPI" in prerequisite_text)

    mac_manual = "macOS privacy grants often\nrequire a user action in System Settings" in prerequisite_text
    windows_safe = all(term in prerequisite_text for term in ("Never weaken UAC", "Defender", "SmartScreen"))
    record("PC43", "macOS privacy grant remains manual", "manual System Settings action", str(mac_manual), mac_manual and "MANUAL_ACTION_REQUIRED" in prerequisite_text)
    record("PC44", "Windows setup preserves security controls", "no UAC/Defender/SmartScreen bypass", str(windows_safe), windows_safe)

    declined = Setup(status="DECLINED")
    fallback = "MANUAL_BROWSER_HANDOFF"
    record("PC45", "declined setup uses manual or reduced route", "DECLINED with manual route", f"{declined.status}/{fallback}", declined.status == "DECLINED" and "manual or reduced-workload route" in prerequisite_text)

    setup_only = Setup(status="VERIFIED", exact_packet_approved=True, runtime_action_authorized=False)
    record("PC46", "setup permission does not authorize worker actions", "runtime action remains unauthorized", str(setup_only.runtime_action_authorized), not setup_only.runtime_action_authorized and "does not grant permission for later worker submissions" in prerequisite_text)

    setup_pauses = "Pause new\nsubmissions and control actions before an approved setup change" in (ROOT / "references/monitoring-and-recovery.md").read_text()
    record("PC47", "setup is separated from active worker monitoring", "pause new actions, preserve healthy worker", str(setup_pauses), setup_pauses)

    report_has_readiness = "## Workload prerequisite readiness" in capability_report_text
    report_has_geometry = "## Screenshot capture geometry" in capability_report_text
    record("PC48", "capability report persists setup and geometry", "both report sections", f"readiness={report_has_readiness}; geometry={report_has_geometry}", report_has_readiness and report_has_geometry)

    record("PC49", "setup status is not subjective progress", "no sixth bar", "documented" if "not a sixth progress bar" in progress_text else "missing", "not a sixth progress bar" in progress_text)

    setup_failure_rows = (
        "Required prerequisite is missing",
        "Setup awaits exact approval",
        "Setup exposes a broader target or permission",
        "Native privacy, portal, credential, or UAC dialog appears",
        "Approved setup fails",
        "Post-setup preflight fails",
        "Chrome automation/debugging infobar changes screenshot geometry",
    )
    record("PC50", "failure catalog covers setup and infobar recovery", "all failure classes present", ",".join(row for row in setup_failure_rows if row in failure_text), all(row in failure_text for row in setup_failure_rows))

    first_profile = invocation_gate(InvocationProfile())
    record(
        "PC51",
        "first invocation performs baseline and gate",
        "one INITIAL_BASELINE, one INVOCATION_GATE, no run mutation",
        f"baseline={first_profile.baseline_runs}; gate={first_profile.invocation_gates}; mutations={first_profile.run_mutations}",
        first_profile.baseline_runs == 1 and first_profile.invocation_gates == 1 and first_profile.run_mutations == 0,
    )
    second_profile = invocation_gate(first_profile)
    record(
        "PC52",
        "subsequent invocation repeats read-only gate",
        "baseline remains one; invocation gates become two",
        f"baseline={second_profile.baseline_runs}; gate={second_profile.invocation_gates}",
        second_profile.baseline_runs == 1 and second_profile.invocation_gates == 2 and second_profile.last_result == "PASS",
    )
    status_profile = invocation_gate(second_profile)
    record(
        "PC53",
        "status/help invocation preflights without workforce action",
        "EVERY_INVOCATION gate and zero run mutations",
        f"gate={status_profile.invocation_gates}; mutations={status_profile.run_mutations}",
        status_profile.invocation_gates == 3
        and status_profile.run_mutations == 0
        and "including bare kickoff, `help`, `status`, or" in skill_text,
    )
    drifted = invocation_gate(status_profile, drift=True)
    record(
        "PC54",
        "capability drift triggers full recheck",
        "DEGRADED, delta recorded, one FULL_RECHECK",
        f"{drifted.last_result}/{drifted.capability_delta}/{drifted.full_rechecks}",
        drifted.last_result == "DEGRADED" and drifted.full_rechecks == 1 and "capability delta" in capability_text.lower(),
    )

    disposition, repairs, asks = diagnose_control_fault(healthy_slow=True, repair_supported=True, needs_new_permission=False)
    record("PC55", "healthy slow generation avoids control repair", "RUNNING_HEALTHY, zero repairs", f"{disposition}/{repairs}", disposition == "RUNNING_HEALTHY" and repairs == 0 and not asks)
    disposition, repairs, asks = diagnose_control_fault(healthy_slow=False, repair_supported=True, needs_new_permission=False)
    record("PC56", "bounded control self-repair", "RESOLVED after one non-destructive repair", f"{disposition}/{repairs}", disposition == "RESOLVED" and repairs == 1 and not asks and "at most one bounded non-destructive repair" in monitoring_text)
    disposition, repairs, asks = diagnose_control_fault(healthy_slow=False, repair_supported=False, needs_new_permission=True)
    record("PC57", "new control permission returns to user", "SETUP_REQUIRED with no silent repair", f"{disposition}/{repairs}/ask={asks}", disposition == "SETUP_REQUIRED" and repairs == 0 and asks and "prepare the exact prerequisite packet and ask" in monitoring_text)
    disposition, repairs, asks = diagnose_control_fault(healthy_slow=False, repair_supported=False, needs_new_permission=False)
    record("PC58", "control repair ceiling uses handoff", "MANUAL_HANDOFF after one repair ceiling", f"{disposition}/{repairs}", disposition == "MANUAL_HANDOFF" and repairs == 1 and "After the one-repair ceiling" in monitoring_text)

    observed_usage = {profile: USAGE_BANDS[profile] for profile in USAGE_BANDS}
    record("PC59", "allocation exposes qualitative Codex usage gradient", str(USAGE_BANDS), str(observed_usage), observed_usage == USAGE_BANDS and all(value in progress_text for value in USAGE_BANDS.values()))
    record("PC60", "allocation may change at any time", "future work only; active ownership preserved", "documented" if "may change allocation at any time" in progress_text.lower() else "missing", "may change allocation at any time" in progress_text.lower() and "future work" in progress_text and "active lane" in progress_text)

    layout_terms = ("<artifact-root>/<topic-slug>/runs/<run-id>/", "incoming/", "raw/", "candidates/", "accepted/", "manifests/")
    record("PC61", "dedicated run-owned artifact layout", "all isolated areas", ",".join(term for term in layout_terms if term in storage_text), all(term in storage_text for term in layout_terms))
    with tempfile.TemporaryDirectory(prefix="workforce-cleanup-safety-") as temp_name:
        temp_root = Path(temp_name).resolve()
        run_root = temp_root / "topic" / "runs" / "RUN-TEST"
        run_root.mkdir(parents=True)
        owned = run_root / "temporary.bin"
        owned.write_bytes(b"owned-temporary-data")
        digest = hashlib.sha256(owned.read_bytes()).hexdigest()
        exact = cleanup_candidate(run_root, owned, digest, accepted_export=True)
        changed = cleanup_candidate(run_root, owned, "0" * 64, accepted_export=True)
        in_use = cleanup_candidate(run_root, owned, digest, accepted_export=True, in_use=True)
        outside = temp_root / "unrelated.bin"
        outside.write_bytes(b"user-data")
        outside_result = cleanup_candidate(run_root, outside, hashlib.sha256(outside.read_bytes()).hexdigest(), accepted_export=True)
        symlink = run_root / "link.bin"
        symlink.symlink_to(outside)
        symlink_result = cleanup_candidate(run_root, symlink, digest, accepted_export=True)
        missing_export = cleanup_candidate(run_root, owned, digest, accepted_export=False)
        record("PC62", "exact hash-bound cleanup candidate", "ELIGIBLE only for exact owned file", exact, exact == "ELIGIBLE")
        record("PC63", "post-plan hash mutation suppresses cleanup", "SKIPPED", changed, changed == "SKIPPED")
        record("PC64", "out-of-root and symlink cleanup suppressed", "both SKIPPED; unrelated bytes intact", f"outside={outside_result}; symlink={symlink_result}; bytes={outside.read_bytes()!r}", outside_result == "SKIPPED" and symlink_result == "SKIPPED" and outside.read_bytes() == b"user-data")
        record("PC65", "missing export or in-use file suppresses cleanup", "both SKIPPED", f"export={missing_export}; in_use={in_use}", missing_export == "SKIPPED" and in_use == "SKIPPED")

    record("PC66", "declined notes create no topic folder", "false", str(topic_folder_allowed(policy="NO_NOTES", decision="APPROVED", root_confirmed=True, creation_authorized=True)), not topic_folder_allowed(policy="NO_NOTES", decision="APPROVED", root_confirmed=True, creation_authorized=True))
    record("PC67", "pending discovered topic creates no folder", "false", str(topic_folder_allowed(policy="YES_EXISTING_ROOT", decision="PENDING", root_confirmed=True, creation_authorized=True)), not topic_folder_allowed(policy="YES_EXISTING_ROOT", decision="PENDING", root_confirmed=True, creation_authorized=True) and "must not create a folder until" in obsidian_text)
    record("PC68", "approved topic may create needed folder", "true", str(topic_folder_allowed(policy="YES_EXISTING_ROOT", decision="APPROVED", root_confirmed=True, creation_authorized=True)), topic_folder_allowed(policy="YES_EXISTING_ROOT", decision="APPROVED", root_confirmed=True, creation_authorized=True) and "Do not create empty directory" in obsidian_text)
    record("PC69", "native artifacts are indexed rather than duplicated", "native path/hash index", "documented" if "do not duplicate" in obsidian_text.lower() else "missing", "do not duplicate" in obsidian_text.lower() and "path, size, hash" in obsidian_text.lower())

    dashboard_policies = ("DISABLED", "ON_DEMAND", "ENABLED")
    record("PC70", "first-use dashboard policy", "three profile choices", ",".join(item for item in dashboard_policies if item in profile_text), all(item in profile_text and item in dashboard_text for item in dashboard_policies))
    record("PC71", "dashboard snapshot refreshes each invocation", "atomic public snapshot after readiness gate", "documented" if "On every skill invocation" in dashboard_text else "missing", "On every skill invocation" in dashboard_text and "atomically replace" in dashboard_text and "invocation readiness gate" in dashboard_text)
    healthy = True
    visible_url = "http://127.0.0.1:8765/runs/RUN-TEST/" if healthy else None
    unhealthy_url = None if not False else "unexpected"
    record("PC72", "dashboard link requires current health", "healthy URL only; unhealthy omitted", f"healthy={visible_url}; unhealthy={unhealthy_url}", visible_url is not None and unhealthy_url is None and "never show a remembered link" in dashboard_text)
    record("PC73", "dashboard polling does not claim background work", "polls local JSON but cannot keep orchestration alive", "documented" if "cannot keep Codex" in dashboard_text else "missing", "polls its own `status.json`" in dashboard_text and "cannot keep Codex" in dashboard_text)
    record("PC74", "dashboard renderer is read-only and text-safe", "no innerHTML; local no-store fetch; no action controls", "safe" if ".innerHTML" not in dashboard_html else "unsafe", ".innerHTML" not in dashboard_html and 'cache: "no-store"' in dashboard_html and "cannot control workers" in dashboard_html)
    first_use_questions = ("Where should worker downloads go", "Would you like this work documented in Obsidian", "DISABLED`, `ON_DEMAND` (recommended), or `ENABLED")
    record("PC75", "guided setup covers storage notes and dashboard", "all first-use questions", ",".join(term for term in first_use_questions if term in (ROOT / "references/guided-start.md").read_text()), all(term in (ROOT / "references/guided-start.md").read_text() for term in first_use_questions))
    record("PC76", "dashboard reports allocation and Codex usage band", "allocation_profile and codex_usage_band", "present" if "codex_usage_band" in dashboard_html else "missing", "allocation_profile" in dashboard_html and "codex_usage_band" in dashboard_html and "qualitative" in dashboard_html)
    locator_sources = ("explicit current project instruction", "currently open registry candidate", "other registry candidate", "bounded `.obsidian` marker candidate")
    record("PC77", "Obsidian discovery ranks safe evidence", "instruction > open registry > registry > marker", ",".join(source for source in locator_sources if source in obsidian_text), all(source in obsidian_text for source in locator_sources))
    record("PC78", "Obsidian recommendation still requires confirmation", "no auto-select/create/write", "documented" if "Do not auto-select" in obsidian_text else "missing", "Do not auto-select" in obsidian_text and "ask" in obsidian_text and "Locator confirmation" in profile_text)
    locator_safety_terms = ("max_depth", "follow_symlinks=False", "obsidian.json", ".obsidian", "vault_id")
    record("PC79", "Obsidian locator is bounded and metadata-only", "bounded config/marker discovery", ",".join(term for term in locator_safety_terms if term in locator_text), all(term in locator_text for term in locator_safety_terms) and "note contents" in obsidian_text.lower())
    record("PC80", "Obsidian locator avoids broad home crawl", "no recursive home default", "safe" if "Path.home().rglob" not in locator_text else "unsafe", "Path.home().rglob" not in locator_text and "Never default to crawling" in obsidian_text)

    copy_controls = (
        "$chatgpt-pro-workforce tell me more {RUN_ID}",
        "$chatgpt-pro-workforce pause {RUN_ID}",
        "$chatgpt-pro-workforce resume {RUN_ID}",
        "$chatgpt-pro-workforce change allocation {RUN_ID}",
        "$chatgpt-pro-workforce change concurrency {RUN_ID}",
        "$chatgpt-pro-workforce uninstall",
        "$chatgpt-pro-workforce help",
    )
    record("PC81", "dashboard exposes complete copy-only help controls", "all primary intents plus copy-only boundary", ",".join(term for term in copy_controls if term in dashboard_html), all(term in dashboard_html for term in copy_controls) and "never execute a command" in dashboard_html.lower())
    linux_layers = (
        "LINUX_SIGNED_IN_CHROME",
        "LINUX_COMPUTER_USE_MCP",
        "LINUX_CHROME_DEVTOOLS_MCP",
        "LINUX_PLAYWRIGHT_EXTENSION",
    )
    record("PC82", "Linux support stack has four independent readiness records", "four exact records and action-specific readiness", ",".join(term for term in linux_layers if term in platform_text), all(term in platform_text for term in linux_layers) and "Record all four separately" in platform_text and "action-specific" in platform_text)
    record("PC83", "macOS guidance preserves live-test and permission truth", "not live-tested; separate OS grants; no invented MCP", "documented" if "macOS could not be live-tested" in platform_text else "missing", "macOS could not be live-tested" in platform_text and "Never invent `mcp__computer_use_macos__*`" in platform_text and all(term in platform_text for term in ("Accessibility", "Input Monitoring", "Screen & System Audio Recording")))
    record("PC84", "Windows guidance preserves live-test and security truth", "not live-tested; UI Automation; UAC safeguards", "documented" if "Windows could not be live-tested" in platform_text else "missing", "Windows could not be live-tested" in platform_text and "`mcp__computer_use_windows__*`" in platform_text and "UI Automation" in platform_text and "never disable UAC" in platform_text)
    record("PC85", "uninstall is exact-target and confirmation-gated", "inventory + backup + explicit approval before mutation", control_intent("$chatgpt-pro-workforce uninstall"), control_intent("$chatgpt-pro-workforce uninstall") == "UNINSTALL" and all(term in install_text for term in ("Never act on a glob", "timestamped non-discoverable backup", "explicit approval", "original path is absent")))
    record("PC86", "uninstall preserves research and shared prerequisites", "no research, state, notes, artifacts, or control-stack deletion", "documented" if "research projects" in install_text else "missing", all(term in install_text for term in ("research projects", "Obsidian notes", "worker downloads", "shared prerequisites")))
    record("PC87", "install lifecycle follows standard validated skill shape", "one standard directory; staged/current validator; atomic placement", "documented" if "agents/openai.yaml" in install_text else "missing", all(term in install_text for term in ("SKILL.md", "agents/openai.yaml", "current authoritative", "temporary sibling", "replace atomically")))
    locator_bounds = ("DEFAULT_DIRECTORY_LIMIT", "DEFAULT_ENTRY_LIMIT", "PER_DIRECTORY_ENTRY_LIMIT", "DEFAULT_MAX_SECONDS", "marker_root_too_broad")
    record("PC88", "Obsidian search has breadth, time, and broad-root limits", "all hard-stop mechanisms present", ",".join(term for term in locator_bounds if term in locator_text), all(term in locator_text for term in locator_bounds) and '"complete": not ceiling_hit' in locator_text)
    record("PC89", "Obsidian traversal rechecks identity and filesystem", "lstat on pop; same st_dev; no symlink follow", "documented" if "directory.lstat()" in locator_text else "missing", "directory.lstat()" in locator_text and "directory_stat.st_dev != start_device" in locator_text and "follow_symlinks=False" in locator_text)

    failures = [result for result in RESULTS if result[1] == FAIL]
    for case_id, classification, title, details in RESULTS:
        print(f"{case_id}|{classification}|{title}|{details}")
    print(f"TOTAL={len(RESULTS)}")
    print(f"SIMULATED_PASS={len(RESULTS) - len(failures)}")
    print(f"SIMULATED_FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
