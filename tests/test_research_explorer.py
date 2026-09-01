#!/usr/bin/env python3
"""Bounded integration tests for the completed-research explorer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


SKILL = Path(sys.argv[1]).resolve()
HELPER = SKILL / "scripts/research_explorer.py"
TEMPLATE = SKILL / "assets/research-explorer-template.html"
DATA_TEMPLATE = SKILL / "assets/research-explorer-data-template.json"
RESULTS: list[tuple[str, bool, str]] = []


def record(case_id: str, passed: bool, detail: str) -> None:
    RESULTS.append((case_id, passed, detail))


def run(*args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"unexpected exit {result.returncode} for {args!r}: {result.stderr}"
        )
    return result


def write_private(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workforce-explorer-test-") as name:
        root = Path(name)
        data = json.loads(DATA_TEMPLATE.read_text(encoding="utf-8"))
        source = root / "accepted-research.json"
        output = root / "research-explorer.html"
        write_private(source, data)

        built = run(
            "build", "--data", str(source), "--template", str(TEMPLATE),
            "--output", str(output),
        )
        build_result = json.loads(built.stdout)
        raw = output.read_bytes()
        html = raw.decode("utf-8")
        record(
            "RE01",
            build_result["run_id"] == data["report"]["run_id"]
            and build_result["sha256"] == hashlib.sha256(raw).hexdigest()
            and 'data-research-explorer="workforce-research-v1"' in html
            and "__RESEARCH_EXPLORER_DATA__" not in html,
            "self-contained explorer built with matching run ID and hash",
        )

        verified = run(
            "verify", "--html", str(output),
            "--expected-run-id", data["report"]["run_id"],
        )
        verification = json.loads(verified.stdout)
        record(
            "RE02",
            verification["findings"] == 1 and verification["sources"] == 1,
            "embedded schema and finding/source counts verified",
        )

        record(
            "RE03",
            ".innerHTML" not in html
            and "fetch(" not in html
            and not any(token in html for token in ('src="http', "href=\"//", "https://fonts")),
            "template uses text-safe local-only rendering",
        )

        preserved_hash = hashlib.sha256(raw).hexdigest()
        existing = run(
            "build", "--data", str(source), "--template", str(TEMPLATE),
            "--output", str(output), expected=2,
        )
        record(
            "RE04",
            "output exists" in existing.stderr
            and hashlib.sha256(output.read_bytes()).hexdigest() == preserved_hash,
            "existing output rejected without force and bytes preserved",
        )

        hostile = json.loads(json.dumps(data))
        hostile["unexpected"] = "do not accept"
        hostile_source = root / "hostile.json"
        hostile_output = root / "hostile.html"
        write_private(hostile_source, hostile)
        rejected = run(
            "build", "--data", str(hostile_source), "--template", str(TEMPLATE),
            "--output", str(hostile_output), expected=2,
        )
        record(
            "RE05",
            "unknown field" in rejected.stderr and not hostile_output.exists(),
            "unknown schema field rejected before output",
        )

        traversal = json.loads(json.dumps(data))
        traversal["artifacts"][0]["relative_link"] = "../private.txt"
        traversal_source = root / "traversal.json"
        write_private(traversal_source, traversal)
        rejected = run(
            "build", "--data", str(traversal_source), "--template", str(TEMPLATE),
            "--output", str(root / "traversal.html"), expected=2,
        )
        record("RE06", "safe relative link" in rejected.stderr, "artifact traversal rejected")

        dangling = json.loads(json.dumps(data))
        dangling["findings"][0]["source_ids"] = ["S404"]
        dangling_source = root / "dangling.json"
        write_private(dangling_source, dangling)
        rejected = run(
            "build", "--data", str(dangling_source), "--template", str(TEMPLATE),
            "--output", str(root / "dangling.html"), expected=2,
        )
        record("RE07", "unknown reference" in rejected.stderr, "dangling evidence reference rejected")

        wrong_run = run(
            "verify", "--html", str(output), "--expected-run-id", "RUN-WRONG",
            expected=2,
        )
        record("RE08", "expected run ID" in wrong_run.stderr, "wrong-run verification fails closed")

        fallback_markers = (
            "<noscript", "Executive summary", "Key findings", "Sources",
            "Contradictions", "Method", "Artifacts",
        )
        record(
            "RE09",
            all(marker in html for marker in fallback_markers),
            "core research sections and no-JavaScript explanation are present",
        )

    failures = [item for item in RESULTS if not item[1]]
    for case_id, passed, detail in RESULTS:
        print(f"{case_id}|{'SIMULATED_PASS' if passed else 'SIMULATED_FAIL'}|{detail}")
    print(f"TOTAL={len(RESULTS)} PASS={len(RESULTS) - len(failures)} FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
