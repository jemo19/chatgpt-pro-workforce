#!/usr/bin/env python3
"""Dependency-free structural validator for the published skill."""

from pathlib import Path
import hashlib
import json
import re
import stat
import sys

ROOT = Path(sys.argv[1]).resolve()
EXPECTED_NAME = sys.argv[2] if len(sys.argv) > 2 else ROOT.name
EXPECTED = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/capability-preflight.md",
    "references/local-control-profile.md",
    "references/linux-control-options.md",
    "references/platform-control-stacks.md",
    "references/modes.md",
    "references/orchestration.md",
    "references/prompt-contract.md",
    "references/monitoring-and-recovery.md",
    "references/evidence-and-verification.md",
    "references/obsidian-research-vault.md",
    "references/security-and-authority.md",
    "references/failure-catalog.md",
    "references/state-and-handoff.md",
    "references/guided-start.md",
    "references/progress-and-controls.md",
    "references/prerequisite-setup.md",
    "references/artifact-storage-and-cleanup.md",
    "references/local-status-dashboard.md",
    "references/installation-and-uninstall.md",
    "assets/capability-report-template.md",
    "assets/worker-prompt-template.md",
    "assets/review-prompt-template.md",
    "assets/correction-prompt-template.md",
    "assets/research-note-template.md",
    "assets/source-note-template.md",
    "assets/iteration-note-template.md",
    "assets/lane-state-template.md",
    "assets/handoff-template.md",
    "assets/kickoff-brief-template.md",
    "assets/run-state-template.md",
    "assets/progress-card-template.md",
    "assets/prerequisite-plan-template.md",
    "assets/cleanup-plan-template.md",
    "assets/workforce-profile-template.md",
    "assets/status-dashboard-template.html",
    "assets/status-data-template.json",
    "scripts/obsidian_locator.py",
    "scripts/status_dashboard.py",
}


def parse_simple_mapping(source: str) -> dict[str, object]:
    """Parse the narrow mapping-only YAML shape used by this skill.

    This is intentionally not a general YAML parser. It accepts nested mappings
    with two-space indentation and either JSON-quoted or plain scalar strings.
    The public validation suite therefore needs no downloaded dependencies.
    """

    root: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, root)]
    for number, raw in enumerate(source.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ValueError(f"line {number}: indentation must use two spaces")
        line = raw.strip()
        if ":" not in line:
            raise ValueError(f"line {number}: expected key/value mapping")
        key, value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise ValueError(f"line {number}: unsupported key {key!r}")
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        value = value.strip()
        if not value:
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
        elif value.startswith('"'):
            decoded = json.loads(value)
            if not isinstance(decoded, str):
                raise ValueError(f"line {number}: scalar must be a string")
            parent[key] = decoded
        else:
            parent[key] = value
    return root


def heading_slugs(text: str) -> set[str]:
    slugs = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            slug = match.group(1).strip().lower()
            slug = re.sub(r"[^\w\- ]", "", slug)
            slugs.add(re.sub(r"\s+", "-", slug))
    return slugs


def main() -> int:
    errors: list[str] = []
    files = sorted(path for path in ROOT.rglob("*") if path.is_file() or path.is_symlink())
    rels = {path.relative_to(ROOT).as_posix() for path in files}
    if rels != EXPECTED:
        errors.append(
            f"runtime inventory mismatch missing={sorted(EXPECTED - rels)} "
            f"unexpected={sorted(rels - EXPECTED)}"
        )

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            errors.append(f"unsafe file type: {rel}")
            continue
        data = path.read_bytes()
        if not data:
            errors.append(f"empty file: {rel}")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"not UTF-8: {rel}")
            continue
        if not text.endswith("\n"):
            errors.append(f"no final newline: {rel}")
        if re.search(r"(?im)\b(?:TODO|TBD|FIXME)\b", text):
            errors.append(f"unfinished marker: {rel}")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON: {rel}: {exc}")

    runtime_scripts = [path for path in files if "/scripts/" in f"/{path.relative_to(ROOT).as_posix()}"]
    if [path.relative_to(ROOT).as_posix() for path in runtime_scripts] != [
        "scripts/obsidian_locator.py",
        "scripts/status_dashboard.py",
    ]:
        errors.append("unexpected runtime script inventory")
    else:
        for runtime_script in runtime_scripts:
            try:
                compile(runtime_script.read_text(), str(runtime_script), "exec")
            except SyntaxError as exc:
                errors.append(f"runtime helper syntax error: {runtime_script.name}: {exc}")

    skill_text = (ROOT / "SKILL.md").read_text()
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
    if not frontmatter_match:
        errors.append("SKILL.md frontmatter missing")
    else:
        try:
            frontmatter = parse_simple_mapping(frontmatter_match.group(1))
        except (ValueError, json.JSONDecodeError) as exc:
            frontmatter = {}
            errors.append(f"invalid SKILL.md frontmatter: {exc}")
        if set(frontmatter or {}) != {"name", "description"}:
            errors.append(f"frontmatter fields={sorted((frontmatter or {}).keys())}")
        if frontmatter.get("name") != EXPECTED_NAME:
            errors.append(
                f"frontmatter name mismatch expected={EXPECTED_NAME!r} "
                f"observed={frontmatter.get('name')!r}"
            )
        description = frontmatter.get("description", "")
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            errors.append("invalid description length")
        for phrase in (
            "explicitly requests",
            "Do not use for ordinary browser work",
            "simple questions",
        ):
            if phrase not in description:
                errors.append(f"description missing discrimination: {phrase}")

    agent_source = (ROOT / "agents/openai.yaml").read_text()
    try:
        agent = parse_simple_mapping(agent_source)
    except (ValueError, json.JSONDecodeError) as exc:
        agent = {}
        errors.append(f"invalid agents/openai.yaml: {exc}")
    if set(agent or {}) != {"interface"} or set((agent or {}).get("interface", {})) != {
        "display_name",
        "short_description",
        "default_prompt",
    }:
        errors.append("agents/openai.yaml schema mismatch")
    else:
        interface = agent["interface"]
        if not all(isinstance(value, str) for value in interface.values()):
            errors.append("UI values must be strings")
        if not 25 <= len(interface["short_description"]) <= 64:
            errors.append("short_description length invalid")
        prompt = interface["default_prompt"]
        if "$chatgpt-pro-workforce" not in prompt:
            errors.append("default_prompt lacks explicit invocation")
        if "guided kickoff" not in prompt or "no concrete task" not in prompt:
            errors.append("default_prompt lacks bare-invocation guidance")
    for line in agent_source.splitlines():
        if re.match(r"^\s+(display_name|short_description|default_prompt):", line) and not re.match(
            r'^\s+\w+:\s+"(?:[^"\\]|\\.)*"\s*$', line
        ):
            errors.append(f"unquoted UI line: {line}")

    link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    direct_links: set[str] = set()
    for path in (item for item in files if item.suffix == ".md"):
        for raw_target in link_pattern.findall(path.read_text()):
            target = raw_target.strip().split()[0].strip("<>")
            if re.match(r"^[a-z]+://", target) or target.startswith("mailto:") or "{{" in target:
                continue
            path_part, _, anchor = target.partition("#")
            destination = (path.parent / path_part).resolve() if path_part else path.resolve()
            try:
                destination.relative_to(ROOT)
            except ValueError:
                errors.append(f"link escapes root: {path.relative_to(ROOT)} -> {target}")
                continue
            if path_part and not destination.is_file():
                errors.append(f"broken link: {path.relative_to(ROOT)} -> {target}")
                continue
            if anchor and anchor.lower() not in heading_slugs(destination.read_text()):
                errors.append(f"broken anchor: {path.relative_to(ROOT)} -> {target}")
            if path == ROOT / "SKILL.md" and path_part:
                direct_links.add(destination.relative_to(ROOT).as_posix())

    required_direct = {
        rel
        for rel in EXPECTED
        if rel.startswith("references/")
        or rel.startswith("assets/")
        or rel.startswith("scripts/")
    }
    if not required_direct <= direct_links:
        errors.append(f"detached runtime resources={sorted(required_direct - direct_links)}")

    for path in (ROOT / "references").glob("*.md"):
        lines = path.read_text().splitlines()
        if len(lines) > 100 and "## Contents" not in "\n".join(lines[:30]):
            errors.append(f"long reference lacks early Contents: {path.name}")

    all_text = "\n".join(
        path.read_text()
        for path in files
        if path.suffix in {".md", ".yaml", ".html", ".json", ".py"}
    )
    for prefix in ("/home/", "/mnt/"):
        if prefix in all_text:
            errors.append(f"machine-specific absolute path present: {prefix}")
    if re.search(r"(?i)\btrading\b", all_text):
        errors.append("trading-specific runtime content")

    guided = (ROOT / "references/guided-start.md").read_text()
    if "Ask one short question at a time" not in guided:
        errors.append("guided start lacks one-question pacing")
    lane_state = (ROOT / "assets/lane-state-template.md").read_text()
    for field in ("Desktop action ID:", "Attempt:", "Action outcome:", "Next safe route:"):
        if field not in lane_state:
            errors.append(f"lane state lacks {field}")
    linux_options = (ROOT / "references/linux-control-options.md").read_text()
    if "Input reports success but no semantic postcondition appears | `STALLED` or `TERMINAL_INCOMPLETE`" in linux_options:
        errors.append("desktop action still uses generation vocabulary")
    if "otherwise `OUTCOME_UNKNOWN`" not in linux_options:
        errors.append("unknown postcondition rule missing")

    progress = (ROOT / "references/progress-and-controls.md").read_text()
    progress_card = (ROOT / "assets/progress-card-template.md").read_text()
    run_state = (ROOT / "assets/run-state-template.md").read_text()
    skill_flat = " ".join(skill_text.split())
    for intent in (
        "$chatgpt-pro-workforce status [RUN_ID]",
        "$chatgpt-pro-workforce tell me more [RUN_ID]",
        "$chatgpt-pro-workforce pause [RUN_ID]",
        "$chatgpt-pro-workforce resume [RUN_ID]",
        "$chatgpt-pro-workforce change concurrency [RUN_ID]",
        "$chatgpt-pro-workforce uninstall",
        "$chatgpt-pro-workforce help",
    ):
        if intent not in progress:
            errors.append(f"progress controls missing intent: {intent}")
    for profile in ("PRO_HEAVY", "BALANCED", "CODEX_HEAVY", "LOCAL_ONLY"):
        if profile not in progress or profile not in run_state:
            errors.append(f"allocation profile missing from contract/state: {profile}")
    for policy in ("ASK_BEFORE_ADDING", "AUTO_ADD_IN_SCOPE", "FIXED_SCOPE"):
        if policy not in progress or policy not in run_state:
            errors.append(f"scope policy missing from contract/state: {policy}")
    for run_status in ("PAUSING", "PAUSED", "LIMIT_PAUSED", "RESUMING"):
        if run_status not in progress or run_status not in run_state:
            errors.append(f"run status missing from contract/state: {run_status}")
    if "cannot by itself create a" not in progress or "native hover tooltip" not in progress:
        errors.append("native tooltip boundary missing")
    if "background scheduler" not in progress or "after the active Codex run ends" not in progress:
        errors.append("background-reporting boundary missing")
    if "filled_cells = floor(10 * numerator / denominator)" not in progress:
        errors.append("deterministic bar formula missing")
    if "unknown, or intentionally open-ended" not in progress or "[active] —/—" not in progress:
        errors.append("unknown-denominator behavior missing")
    if "Do not average the categories into a subjective overall percentage" not in progress:
        errors.append("subjective overall-percent prohibition missing")
    if "More: $chatgpt-pro-workforce tell me more {{RUN_ID}}" not in progress_card:
        errors.append("compact card lacks visible tell-me-more intent")
    if "A status or help request is read-only" not in skill_flat:
        errors.append("SKILL status/help mutation boundary missing")
    if "scope_change: +" not in progress:
        errors.append("scope denominator-change disclosure missing")
    for field in (
        "allocation_profile:",
        "codex_usage_band:",
        "scope_expansion_policy:",
        "reporting_cadence:",
        "status_freshness:",
        "Exact resume cursor:",
    ):
        if field not in run_state:
            errors.append(f"run state lacks {field}")

    workforce_profile = (ROOT / "assets/workforce-profile-template.md").read_text()
    kickoff = (ROOT / "assets/kickoff-brief-template.md").read_text()
    handoff = (ROOT / "assets/handoff-template.md").read_text()
    capability = (ROOT / "references/capability-preflight.md").read_text()
    security = (ROOT / "references/security-and-authority.md").read_text()
    storage = (ROOT / "references/artifact-storage-and-cleanup.md").read_text()
    cleanup_plan = (ROOT / "assets/cleanup-plan-template.md").read_text()
    obsidian = (ROOT / "references/obsidian-research-vault.md").read_text()
    obsidian_locator = (ROOT / "scripts/obsidian_locator.py").read_text()
    monitoring = (ROOT / "references/monitoring-and-recovery.md").read_text()
    dashboard = (ROOT / "references/local-status-dashboard.md").read_text()
    dashboard_html = (ROOT / "assets/status-dashboard-template.html").read_text()
    dashboard_script = (ROOT / "scripts/status_dashboard.py").read_text()
    dashboard_data = json.loads((ROOT / "assets/status-data-template.json").read_text())
    platform_stacks = (ROOT / "references/platform-control-stacks.md").read_text()
    install_lifecycle = (ROOT / "references/installation-and-uninstall.md").read_text()
    orchestration = (ROOT / "references/orchestration.md").read_text()

    concurrency_text = re.sub(
        r"\s+", " ", re.sub(
            r"(?m)^>\s*", "", "\n".join(
                (progress, workforce_profile, run_state, kickoff, handoff, orchestration, monitoring)
            )
        )
    )
    for term in (
        "max_concurrent_pro_workers: 2",
        "likely to increase throttling",
        "interrupted, closed, disconnected, or inaccessible",
        "unsaved or unverified work may be lost",
        "current-run",
        "exact-limit",
        "Never auto-close existing chats",
        "future launches",
        "active or unknown",
    ):
        if term not in concurrency_text:
            errors.append(f"Pro concurrency guardrail missing: {term}")
    for template_name, template in (
        ("workforce profile", workforce_profile),
        ("run state", run_state),
        ("kickoff", kickoff),
        ("handoff", handoff),
    ):
        if "maximum" not in template.lower():
            errors.append(f"Pro concurrency maximum not persisted in {template_name}")
    if "$chatgpt-pro-workforce change concurrency {RUN_ID}" not in dashboard_html:
        errors.append("dashboard lacks copy-only change-concurrency control")

    for level in ("INITIAL_BASELINE", "INVOCATION_GATE", "FAULT_DIAGNOSTIC", "FULL_RECHECK"):
        if level not in capability or level not in run_state:
            errors.append(f"preflight level missing from procedure/state: {level}")
    for trigger in (
        "FIRST_INVOCATION",
        "EVERY_INVOCATION",
        "RESUME",
        "CONTROL_FAULT",
        "CONFIGURATION_CHANGE",
        "POST_SETUP",
    ):
        if trigger not in capability or trigger not in run_state:
            errors.append(f"preflight trigger missing from procedure/state: {trigger}")
    if "Before handling any invocation" not in skill_text or "including bare kickoff" not in skill_text:
        errors.append("SKILL lacks every-invocation readiness gate")
    if "must not create a new conversation, type, submit" not in capability:
        errors.append("invocation gate lacks read-only mutation boundary")
    for term in (
        "Freeze new submissions",
        "Recheck the browser chain",
        "Recheck desktop layers only",
        "one bounded non-destructive repair",
        "new install, permission, daemon, extension",
    ):
        if term.lower() not in monitoring.lower():
            errors.append(f"fault diagnostic missing: {term}")

    for profile, band in (
        ("PRO_HEAVY", "LOWEST"),
        ("BALANCED", "MODERATE"),
        ("CODEX_HEAVY", "HIGH"),
        ("LOCAL_ONLY", "CODEX_ONLY"),
    ):
        if profile not in guided or band not in guided or profile not in progress or band not in progress:
            errors.append(f"allocation usage gradient missing: {profile}/{band}")
    if "may change allocation at any time" not in progress.lower():
        errors.append("allocation is not explicitly changeable at any time")
    if "not measured tokens" not in progress or "quota" not in progress:
        errors.append("allocation usage caveat missing")

    for term in (
        "DEDICATED_RUN_FOLDER",
        "REVIEW_BEFORE_DELETE",
        "exact hash-bound run manifest",
        "reject symlinks",
        "Never broadly clean Downloads",
    ):
        if term.lower() not in (storage + "\n" + security).lower():
            errors.append(f"artifact cleanup contract missing: {term}")
    for term in (
        "Exact cleanup target manifest",
        "TRASHED",
        "SKIPPED",
        "FAILED",
    ):
        if term not in cleanup_plan:
            errors.append(f"cleanup plan missing: {term}")
    for term in (
        "NO_NOTES",
        "ASK_EACH_RUN",
        "YES_EXISTING_ROOT",
        "CREATE_RESEARCH_ROOT_AFTER_APPROVAL",
        "Research Index.md",
        "must not create a folder until",
        "do not create detached notes",
    ):
        if term.lower() not in (obsidian + "\n" + workforce_profile).lower():
            errors.append(f"research-note contract missing: {term}")
    for term in (
        "platform-known",
        "`.obsidian` marker",
        "Never default to crawling",
        "Do not auto-select",
        "ask",
    ):
        if term.lower() not in obsidian.lower():
            errors.append(f"Obsidian locator workflow missing: {term}")
    for term in (
        "obsidian.json",
        ".obsidian",
        "max_depth",
        "follow_symlinks=False",
        "vault_id",
        "recommendation",
    ):
        if term not in obsidian_locator:
            errors.append(f"Obsidian locator helper missing: {term}")
    if "rglob(" in obsidian_locator or "Path.home().rglob" in obsidian_locator:
        errors.append("Obsidian locator contains an unbounded recursive glob")
    for term in (
        "DEFAULT_DIRECTORY_LIMIT",
        "DEFAULT_ENTRY_LIMIT",
        "PER_DIRECTORY_ENTRY_LIMIT",
        "DEFAULT_MAX_SECONDS",
        "marker_root_too_broad",
        '"complete": not ceiling_hit',
    ):
        if term not in obsidian_locator:
            errors.append(f"Obsidian locator breadth bound missing: {term}")

    for term in (
        "DISABLED",
        "ON_DEMAND",
        "ENABLED",
        "On every skill invocation",
        "127.0.0.1",
        "atomically replace",
        "never show a remembered link",
        "read-only",
    ):
        if term.lower() not in dashboard.lower():
            errors.append(f"dashboard contract missing: {term}")
    if set(dashboard_data) != {
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
    }:
        errors.append("dashboard data template top-level schema mismatch")
    if dashboard_data.get("run", {}).get("codex_usage_band") != "MODERATE":
        errors.append("dashboard data template lacks qualitative Codex usage")
    for term in (
        "os.replace",
        "127.0.0.1",
        "SAFE_RUN_ID",
        "TOP_FIELDS",
        "no-store",
        "healthz",
        "is_loopback",
    ):
        if term not in dashboard_script:
            errors.append(f"dashboard helper missing safety mechanism: {term}")
    if "0.0.0.0" in dashboard_script:
        errors.append("dashboard helper contains all-interface bind")
    if ".innerHTML" in dashboard_html:
        errors.append("dashboard injects data with innerHTML")
    if "fetch(`status.json" not in dashboard_html or 'cache: "no-store"' not in dashboard_html:
        errors.append("dashboard does not poll local status with cache disabled")
    if re.search(r"<(?:script|link)[^>]+(?:src|href)=[\"']https?://", dashboard_html, re.I):
        errors.append("dashboard loads an external script or stylesheet")
    for term in ("prefers-reduced-motion", "focus-visible", "aria-live", "direct-user-reference-stats-v1"):
        if term not in dashboard_html:
            errors.append(f"dashboard craft/accessibility marker missing: {term}")
    for term in (
        "$chatgpt-pro-workforce uninstall",
        "copy-command",
        "Copy-only controls",
        "GOOD_STATES",
        "BAD_STATES",
        "WARNING_STATES",
    ):
        if term not in dashboard_html:
            errors.append(f"dashboard control/tone contract missing: {term}")
    if re.search(r"/ACCEPTED\|PASS\|READY|/RECOVERED\|ACCEPTED", dashboard_html):
        errors.append("dashboard uses unsafe substring state classification")

    for term in (
        "chrome:control-chrome",
        "mcp__computer_use_linux__*",
        "mcp__chrome_devtools__*",
        "mcp__playwright_extension__browser_*",
        "all four separately",
        "macOS could not be live-tested",
        "Windows could not be live-tested",
    ):
        if term not in platform_stacks and term not in capability:
            errors.append(f"platform control stack contract missing: {term}")

    for term in (
        "$chatgpt-pro-workforce uninstall",
        "timestamped non-discoverable backup",
        "Never act on a glob",
        "research projects",
        "Permanent deletion requires a separate explicit request",
        "new Codex session",
    ):
        if term not in install_lifecycle:
            errors.append(f"safe uninstall contract missing: {term}")

    prerequisite = (ROOT / "references/prerequisite-setup.md").read_text()
    prerequisite_plan = (ROOT / "assets/prerequisite-plan-template.md").read_text()
    capability = (ROOT / "references/capability-preflight.md").read_text()
    capability_report = (ROOT / "assets/capability-report-template.md").read_text()
    modes = (ROOT / "references/modes.md").read_text()
    orchestration = (ROOT / "references/orchestration.md").read_text()
    handoff = (ROOT / "assets/handoff-template.md").read_text()
    kickoff = (ROOT / "assets/kickoff-brief-template.md").read_text()
    security = (ROOT / "references/security-and-authority.md").read_text()
    for platform in ("Chrome", "Linux", "macOS", "Windows"):
        if platform not in prerequisite or platform not in guided:
            errors.append(f"guided prerequisite coverage missing platform: {platform}")
    for term in (
        "exact target host/surface",
        "trusted source",
        "permissions",
        "Security impact",
        "Success criteria",
        "Exact rollback",
        "Post-setup full preflight",
    ):
        if term.lower() not in prerequisite_plan.lower() and term.lower() not in prerequisite.lower():
            errors.append(f"prerequisite packet missing: {term}")
    for state in (
        "AWAITING_APPROVAL",
        "MANUAL_ACTION_REQUIRED",
        "VERIFIED",
        "DECLINED",
        "BLOCKED",
    ):
        if state not in prerequisite or state not in run_state:
            errors.append(f"setup state missing from runtime/state: {state}")
        if state not in kickoff:
            errors.append(f"kickoff prerequisite state missing: {state}")
    if "AVAILABLE_UNTESTED" not in prerequisite or "safe probe first" not in prerequisite:
        errors.append("untested capability is not probed before setup offer")
    if "complete read-only capability preflight" not in prerequisite:
        errors.append("post-setup full preflight gate missing")
    if "setup state such as" not in orchestration or "is not\nlaunch readiness" not in orchestration:
        errors.append("worker launch is not gated on verified prerequisites")
    if "Never install or reconfigure control software in this skill workflow" in all_text:
        errors.append("obsolete categorical setup prohibition remains")
    if "Never install, enable, or reconfigure control software silently" not in skill_text:
        errors.append("SKILL lacks no-silent-setup boundary")
    if "does not authorize later browser submissions" not in security:
        errors.append("setup permission is not separated from runtime permission")
    for text_name, text_value in (
        ("capability preflight", capability),
        ("capability report", capability_report),
        ("visual mode", modes),
    ):
        for term in ("content viewport", "automation", "debugging", "infobar"):
            if term.lower() not in text_value.lower():
                errors.append(f"{text_name} lacks capture-geometry term: {term}")
    if "outer browser/window dimensions" not in capability_report.lower() or "device scale" not in capability_report.lower() or "top inset" not in capability_report.lower():
        errors.append("capability report lacks outer/content/scale/inset geometry")
    if "do not treat browser chrome as" not in modes.lower():
        errors.append("visual mode lacks browser-chrome non-defect rule")
    if "Prerequisite setup ID / plan" not in run_state or "Prerequisite setup ID / plan" not in handoff:
        errors.append("run state/handoff does not persist prerequisite plan")
    for forbidden in ("weaken UAC", "disable Defender", "bypass UAC"):
        if forbidden.lower() in prerequisite.lower() and "never" not in prerequisite.lower():
            errors.append(f"unsafe prerequisite policy: {forbidden}")

    manifest_lines = []
    for path in sorted(item for item in files if item.is_file() and not item.is_symlink()):
        data = path.read_bytes()
        manifest_lines.append(
            f"{path.relative_to(ROOT).as_posix()}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}"
        )
    inventory_hash = hashlib.sha256(("\n".join(manifest_lines) + "\n").encode()).hexdigest()

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"INVENTORY_SHA256={inventory_hash}")
        print("RESULT=FAIL")
        return 1

    checks = (
        f"all {len(EXPECTED)} required files and no unexpected files",
        "no symlinks, special files, or unjustified runtime scripts",
        "every file non-empty, UTF-8, newline-terminated, and free of scaffold markers",
        "SKILL.md name/frontmatter/description activation boundary",
        "agents/openai.yaml schema, quoted strings, UI lengths, and guided default prompt",
        "every Markdown relative link and heading anchor resolves",
        "every runtime reference and asset directly linked from SKILL.md",
        "long-reference progressive-disclosure contents blocks",
        "no machine-specific absolute paths or trading-specific runtime content",
        "guided-start pacing and ready-to-start resources",
        "resumable desktop action ID/attempt/outcome fields",
        "desktop action vocabulary regression",
        "progress control intents and non-mutating status/help boundary",
        "allocation profiles and first-pass scope-expansion policies",
        "finite registered-ratio bars and unknown-denominator behavior",
        "pause, usage-limit, resume, freshness, and visible tell-me-more state",
        "cross-platform permission-gated prerequisite setup and launch-readiness gate",
        "Chrome automation-infobar-aware content viewport capture geometry",
        "four independently recorded Linux control layers and macOS/Windows truth boundaries",
        "copy-only dashboard help controls and confirmation-gated recoverable uninstall",
    )
    for check in checks:
        print(f"PASS: {check}")
    print(f"INVENTORY_SHA256={inventory_hash}")
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
