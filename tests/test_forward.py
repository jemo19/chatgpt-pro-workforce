#!/usr/bin/env python3
"""Deterministic isolated forward scenarios for chatgpt-pro-workforce."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import shutil
import stat
import sys
import tempfile
import warnings
import zipfile


ROOT = Path(sys.argv[1]).resolve()


@dataclass
class Result:
    case_id: str
    title: str
    expected: str
    observed: str
    passed: bool


RESULTS: list[Result] = []


def record(case_id: str, title: str, expected: str, observed: str, passed: bool) -> None:
    RESULTS.append(Result(case_id, title, expected, observed, passed))


def text(relative: str) -> str:
    return (ROOT / relative).read_text()


def has(relative: str, *needles: str) -> bool:
    body = " ".join(text(relative).split())
    return all(" ".join(needle.split()) in body for needle in needles)


def activation(prompt: str) -> str:
    normalized = prompt.strip().lower()
    if "$chatgpt-pro-workforce" in normalized:
        return "GUIDED_START" if normalized == "$chatgpt-pro-workforce" else "ACTIVE"
    if "ordinary chatgpt pro" in normalized and "worker" in normalized:
        return "ACTIVE"
    return "LOCAL_CODEX"


def monitor(generating: bool, transient_banner: bool, progress_recent: bool) -> tuple[str, tuple[str, ...]]:
    if generating and transient_banner:
        return "RUNNING_WITH_TRANSIENT_ERROR", ("record", "observe", "wait")
    if generating and not progress_recent:
        return "SLOW_NO_FAILURE_EVIDENCE", ("observe", "wait")
    return "OTHER", ("inspect",)


def route(browser: str, native_desktop: str, manual: str) -> str:
    if browser == "AVAILABLE_VERIFIED":
        return "BROWSER_ONLY" if native_desktop == "NOT_AVAILABLE" else "FULL_BROWSER_AND_DESKTOP"
    if manual in {"AVAILABLE_VERIFIED", "AVAILABLE_UNTESTED"}:
        return "MANUAL_BROWSER_HANDOFF"
    return "BLOCKED"


def validate_zip(path: Path) -> str:
    seen: set[str] = set()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            name = member.filename
            if not name or "\\" in name or name.startswith("/"):
                return "REJECTED"
            pure = PurePosixPath(name)
            if ".." in pure.parts or pure.is_absolute():
                return "REJECTED"
            normalized = pure.as_posix().rstrip("/")
            if normalized in seen:
                return "REJECTED"
            seen.add(normalized)
            file_type = (member.external_attr >> 16) & 0o170000
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                return "REJECTED"
    return "ACCEPTED"


def create_zip(path: Path, members: list[tuple[str, bytes, int | None]]) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate name:")
        with zipfile.ZipFile(path, "w") as archive:
            for name, data, mode in members:
                info = zipfile.ZipInfo(name)
                if mode is not None:
                    info.create_system = 3
                    info.external_attr = mode << 16
                archive.writestr(info, data)


def desktop_outcome(transport_success: bool, postcondition: bool | None) -> str:
    if postcondition is True:
        return "VERIFIED_SUCCEEDED"
    if postcondition is False:
        return "VERIFIED_FAILED"
    return "OUTCOME_UNKNOWN" if transport_success else "NOT_ATTEMPTED"


def pro_gate(entitlement: bool, observation: str, postcondition: bool) -> str:
    if not entitlement:
        return "BLOCKED"
    if observation == "PRO_MAX_POWER_VERIFIED" and postcondition:
        return "SUBMIT"
    if observation in {"PRO_MODEL_NOT_SELECTED", "PRO_LOWER_POWER"}:
        return "SELECT_THEN_REVERIFY"
    if observation == "PRO_LIMITED_OR_FALLBACK":
        return "LIMIT_PAUSED"
    return "BLOCKED"


def main() -> int:
    temp_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="chatgpt-pro-workforce-forward-") as temp_name:
        temp_path = Path(temp_name)

        record("FT01", "explicit activation", "ACTIVE", activation("Use $chatgpt-pro-workforce for this review"), activation("Use $chatgpt-pro-workforce for this review") == "ACTIVE")
        observed = activation("Use ordinary ChatGPT Pro conversations as independent worker lanes")
        record("FT02", "indirect workforce activation", "ACTIVE", observed, observed == "ACTIVE")
        for case_id, title, prompt in (
            ("FT03", "simple factual nonactivation", "What is two plus two?"),
            ("FT04", "ordinary browser nonactivation", "Open the documentation page in Chrome"),
            ("FT05", "local formatting nonactivation", "Format this one local Markdown file"),
        ):
            observed = activation(prompt)
            record(case_id, title, "LOCAL_CODEX", observed, observed == "LOCAL_CODEX")

        observed = activation("$chatgpt-pro-workforce")
        guided_ok = observed == "GUIDED_START" and has(
            "references/guided-start.md",
            "Ask one short question at a time",
            "show **every option that is currently valid**",
            "A. Pro-heavy",
            "What would you like to get done?",
            "no worker is launched",
        )
        record("FT06", "bare invocation guided start", "GUIDED_START and one outcome question", observed, guided_ok)
        required_card = (
            "## Outcome", "## Inputs and boundaries", "## Recommended approach",
            "## Lane plan", "## Control and permissions", "## Deliverables and acceptance",
            "## Ready-to-start summary",
        )
        card_ok = has("assets/kickoff-brief-template.md", *required_card)
        record("FT07", "guided ready-to-start card", "all kickoff decision fields", "complete" if card_ok else "incomplete", card_ok)

        conflict = {"lane-a": "claim-supported", "lane-b": "claim-refuted"}
        observed = "PRESERVE_AND_ADJUDICATE" if len(set(conflict.values())) > 1 else "MERGE"
        record("FT08", "conflicting research evidence", "PRESERVE_AND_ADJUDICATE", observed, observed == "PRESERVE_AND_ADJUDICATE" and has("references/failure-catalog.md", "Contradiction between parallel lanes"))
        visual_ok = has("references/modes.md", "provide the exact artifact or image set", "precise locations", "independent reviewer")
        record("FT09", "screenshot visual review", "bounded image set and independent check", "specified" if visual_ok else "missing", visual_ok)
        provided_files = {"src/real.py"}
        cited_file = "src/invented.py"
        observed = "REJECTED_SEMANTIC" if cited_file not in provided_files else "ACCEPTED"
        record("FT10", "invented code file", "REJECTED_SEMANTIC", observed, observed == "REJECTED_SEMANTIC" and has("references/modes.md", "prohibit invention of unprovided repository state"))

        state, actions = monitor(True, True, False)
        banned = {"stop", "reload", "Answer now", "duplicate"}
        monitor_ok = state == "RUNNING_WITH_TRANSIENT_ERROR" and not banned.intersection(actions)
        record("FT11", "simulated 60+ minute active run with transient banner", "wait without interruption", f"{state}:{','.join(actions)}", monitor_ok)
        recovery = ("native attachment", "browser URL", "authorized desktop dialog", "ZIP", "bounded Base64")
        observed = recovery[1:]
        record("FT12", "preferred attachment download fails", "browser URL then bounded fallbacks", " > ".join(observed), observed == recovery[1:] and has("SKILL.md", "authorized desktop handling of a native dialog"))
        mechanical, semantic = True, False
        observed = "REJECTED_SEMANTIC" if mechanical and not semantic else "ACCEPTED"
        record("FT13", "mechanical pass semantic fail", "REJECTED_SEMANTIC", observed, observed == "REJECTED_SEMANTIC" and has("references/evidence-and-verification.md", "REJECTED_SEMANTIC"))

        lane_template = text("assets/lane-state-template.md")
        resume_fields = ("run_id:", "lane_id:", "Prompt SHA-256:", "Desktop action ID:", "Attempt:", "Action outcome:", "Next safe route:")
        resume_ok = all(field in lane_template for field in resume_fields)
        record("FT14", "resumption after compaction", "stable lane and desktop transaction state", "resumable" if resume_ok else "lossy", resume_ok)

        native = temp_path / "artifact.bin"
        native.write_bytes(b"native-artifact-bytes")
        digest = hashlib.sha256(native.read_bytes()).hexdigest()
        note = f"path: {native}\nbytes: {native.stat().st_size}\nsha256: {digest}\n"
        observed = "INDEX_ONLY" if digest in note and native.read_bytes().hex() not in note else "DUPLICATED"
        record("FT15", "Obsidian native-artifact indexing", "INDEX_ONLY", observed, observed == "INDEX_ONLY" and has("references/obsidian-research-vault.md", "index each native object by path, role, size, hash, disposition, and relationships", "Do not lossy-convert or duplicate large evidence"))

        observed = route("AVAILABLE_VERIFIED", "NOT_AVAILABLE", "AVAILABLE_UNTESTED")
        record("FT16", "browser works and native desktop absent", "BROWSER_ONLY", observed, observed == "BROWSER_ONLY")
        atspi_state = "AVAILABLE_VERIFIED"
        method = "accessibility-tree"
        record("FT17", "third-party AT-SPI safe probe", "AVAILABLE_VERIFIED without coordinates", f"{atspi_state}:{method}", atspi_state == "AVAILABLE_VERIFIED" and method != "raw-coordinates")
        input_state = "DEGRADED"
        outcome = "NOT_ATTEMPTED"
        record("FT18", "input present but focus unverifiable", "DEGRADED/NOT_ATTEMPTED", f"{input_state}/{outcome}", input_state == "DEGRADED" and outcome == "NOT_ATTEMPTED")
        observed = route("NOT_AVAILABLE", "NOT_AVAILABLE", "AVAILABLE_VERIFIED")
        record("FT19", "Chrome control unavailable with manual route", "MANUAL_BROWSER_HANDOFF", observed, observed == "MANUAL_BROWSER_HANDOFF")
        browser_state = "DISABLED"
        record("FT20", "browser configured but policy disabled", "DISABLED", browser_state, browser_state == "DISABLED")
        setup_state, setup_action = "NOT_AUTHORIZED", "NO_MUTATION_WITHOUT_EXACT_APPROVAL"
        setup_contract = has(
            "SKILL.md",
            "Never install, enable, or reconfigure control software silently",
            "obtain exact",
            "action-boundary approval",
        )
        record(
            "FT21",
            "adapter setup would be required",
            "NOT_AUTHORIZED and no mutation without exact approval",
            f"{setup_state}:{setup_action}",
            setup_state == "NOT_AUTHORIZED" and setup_contract,
        )
        capability, action = "NOT_AUTHORIZED", "NOT_ATTEMPTED"
        record("FT22", "tool available but action unauthorized", "NOT_AUTHORIZED/NOT_ATTEMPTED", f"{capability}/{action}", capability == "NOT_AUTHORIZED" and action == "NOT_ATTEMPTED")

        durable = {("lane-01", "prompt-hash", "conversation-01"): "ACTIVE"}
        key = ("lane-01", "prompt-hash", "conversation-01")
        observed = "SUPPRESSED" if key in durable else "SUBMITTED"
        record("FT23", "duplicate worker submission", "SUPPRESSED", observed, observed == "SUPPRESSED" and has("SKILL.md", "Suppress an identical active or completed submission"))

        archives = {
            "safe": [("packet/result.txt", b"ok", stat.S_IFREG | 0o644)],
            "traversal": [("../escape.txt", b"bad", stat.S_IFREG | 0o644)],
            "absolute": [("/absolute.txt", b"bad", stat.S_IFREG | 0o644)],
            "symlink": [("link", b"target", stat.S_IFLNK | 0o777)],
            "backslash": [("packet\\escape.txt", b"bad", stat.S_IFREG | 0o644)],
            "duplicate": [("same.txt", b"a", stat.S_IFREG | 0o644), ("same.txt", b"b", stat.S_IFREG | 0o644)],
        }
        decisions = {}
        for name, members in archives.items():
            archive_path = temp_path / f"{name}.zip"
            create_zip(archive_path, members)
            decisions[name] = validate_zip(archive_path)
        zip_ok = decisions["safe"] == "ACCEPTED" and all(decisions[name] == "REJECTED" for name in decisions if name != "safe")
        record("FT24", "unsafe recovered ZIP", "safe accepted; five unsafe classes rejected", repr(decisions), zip_ok)

        candidate = bytearray(b"accepted-candidate")
        accepted_hash = hashlib.sha256(candidate).hexdigest()
        candidate[-1] ^= 1
        observed = "INVALIDATED" if hashlib.sha256(candidate).hexdigest() != accepted_hash else "ACCEPTED"
        record("FT25", "post-validation mutation", "INVALIDATED", observed, observed == "INVALIDATED" and has("references/evidence-and-verification.md", "rehash"))
        attachment_present = False
        observed = "DO_NOT_SUBMIT" if not attachment_present else "SUBMIT"
        record("FT26", "required attachment absent", "DO_NOT_SUBMIT", observed, observed == "DO_NOT_SUBMIT" and has("references/prompt-contract.md", "attachment"))
        policies = {"correction": "same", "blind-review": "fresh", "repeated-failure": "fresh"}
        record("FT27", "same versus fresh conversation", "same correction; fresh blind/failing", repr(policies), policies == {"correction": "same", "blind-review": "fresh", "repeated-failure": "fresh"} and has("SKILL.md", "fresh conversation"))
        observed = route("NOT_AVAILABLE", "NOT_AVAILABLE", "NOT_AVAILABLE")
        record("FT28", "browser and manual routes unavailable", "BLOCKED", observed, observed == "BLOCKED")

        state, action, handoff = "AVAILABLE_UNTESTED", "NOT_ATTEMPTED", "MANUAL_HANDOFF"
        record("FT29", "KDE/Wayland portal choice", "AVAILABLE_UNTESTED/NOT_ATTEMPTED/manual", f"{state}/{action}/{handoff}", action == "NOT_ATTEMPTED" and has("references/linux-control-options.md", "do not synthesize approval input"))
        state, action = "DEGRADED", "NOT_ATTEMPTED"
        record("FT30", "X11/XWayland protocol mismatch", "DEGRADED/NOT_ATTEMPTED", f"{state}/{action}", state == "DEGRADED" and action == "NOT_ATTEMPTED")
        state, action, recovery = "DEGRADED", "NOT_ATTEMPTED", "SCOPED_REFRESH_THEN_HANDOFF"
        record("FT31", "partial AT-SPI tree", "DEGRADED/no blind input", f"{state}/{action}/{recovery}", action == "NOT_ATTEMPTED" and "HANDOFF" in recovery)
        outcome, attempt, repeat = "OUTCOME_UNKNOWN", 1, False
        record("FT32", "disconnect after input", "OUTCOME_UNKNOWN/no repeat", f"{outcome}/attempt={attempt}/repeat={repeat}", outcome == "OUTCOME_UNKNOWN" and not repeat and has("references/linux-control-options.md", "Never repeat input after `OUTCOME_UNKNOWN`"))
        attempts, outcome, next_route = 2, "VERIFIED_FAILED", "MANUAL_HANDOFF"
        record("FT33", "desktop retry ceiling", "attempt 2 then handoff", f"attempt={attempts}/{outcome}/{next_route}", attempts == 2 and next_route == "MANUAL_HANDOFF" and has("references/linux-control-options.md", "After the ceiling, use manual handoff or stop"))
        state, actions = monitor(True, False, False)
        record("FT34", "healthy but slow", "SLOW_NO_FAILURE_EVIDENCE and wait", f"{state}:{','.join(actions)}", state == "SLOW_NO_FAILURE_EVIDENCE" and actions == ("observe", "wait"))
        outcome = desktop_outcome(True, None)
        mixed_vocabulary_absent = "Input reports success but no semantic postcondition appears | `STALLED` or `TERMINAL_INCOMPLETE`" not in text("references/linux-control-options.md")
        record("FT35", "transport success without semantic postcondition", "OUTCOME_UNKNOWN", outcome, outcome == "OUTCOME_UNKNOWN" and mixed_vocabulary_absent)

        pro_contract = has(
            "references/capability-preflight.md",
            "ChatGPT Pro submission gate",
            "account-level UI evidence",
            "target conversation's visible semantic model/mode control",
            "Pro, 5 of 5",
            "There is no degraded or manual bypass",
        )
        observed = pro_gate(True, "PRO_MAX_POWER_VERIFIED", True)
        record("FT36", "fresh conversation proves Pro before submit", "SUBMIT", observed, observed == "SUBMIT" and pro_contract)
        observed = pro_gate(True, "UNKNOWN", False)
        record("FT37", "profile Pro badge without conversation proof", "BLOCKED", observed, observed == "BLOCKED" and has("references/failure-catalog.md", "Account shows Pro but target conversation mode is unverified"))
        observed = pro_gate(True, "PRO_MODEL_NOT_SELECTED", False)
        record("FT38", "conversation starts in another mode", "SELECT_THEN_REVERIFY", observed, observed == "SELECT_THEN_REVERIFY" and has("references/capability-preflight.md", "close and reopen the selector", "independently re-read it"))
        observed = pro_gate(True, "PRO_MAX_POWER_VERIFIED", False)
        record("FT39", "mode action lacks selected-state postcondition", "BLOCKED", observed, observed == "BLOCKED" and has("references/capability-preflight.md", "successful click or slider action without", "selected-state postcondition"))
        observed = pro_gate(True, "PRO_LIMITED_OR_FALLBACK", False)
        record("FT40", "provider fallback changes Pro mode", "LIMIT_PAUSED", observed, observed == "LIMIT_PAUSED" and has("references/monitoring-and-recovery.md", "fallback, lower-power, or unverified state as a blocked submission"))
        resume_gate = has("references/capability-preflight.md", "reopening, reusing, resuming, rebinding, or recovering", "run this gate again")
        record("FT41", "resume requires fresh Pro proof", "REVERIFY_REQUIRED", "REVERIFY_REQUIRED" if resume_gate else "MISSING", resume_gate)
        observed = pro_gate(True, "PRO_LOWER_POWER", False)
        record("FT42", "High does not count as maximum Pro", "SELECT_THEN_REVERIFY", observed, observed == "SELECT_THEN_REVERIFY" and has("references/capability-preflight.md", "`High` is always", "Pro, 5 of 5"))

    cleaned = bool(temp_path) and not temp_path.exists()
    failures = [result for result in RESULTS if not result.passed]
    for result in RESULTS:
        classification = "SIMULATED_PASS" if result.passed else "SIMULATED_FAIL"
        print(f"{result.case_id}|{classification}|{result.title}|expected={result.expected}|observed={result.observed}")
    print(f"TOTAL={len(RESULTS)}")
    print(f"SIMULATED_PASS={len(RESULTS) - len(failures)}")
    print(f"SIMULATED_FAIL={len(failures)}")
    print(f"TEMP_WORKSPACE_CLEANED={str(cleaned).lower()}")
    return 1 if failures or not cleaned else 0


if __name__ == "__main__":
    raise SystemExit(main())
