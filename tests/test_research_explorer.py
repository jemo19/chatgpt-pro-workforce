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
        timeout=15,
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
            "--template", str(TEMPLATE),
            "--expected-template-sha256", build_result["template_sha256"],
            "--expected-data-sha256", build_result["data_sha256"],
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

        encoded_traversal_results = []
        for index, unsafe_link in enumerate(
            ("%2e%2e/private.txt", "%252e%252e/private.txt", "reports/%00secret")
        ):
            encoded_traversal = json.loads(json.dumps(data))
            encoded_traversal["artifacts"][0]["relative_link"] = unsafe_link
            encoded_source = root / f"encoded-traversal-{index}.json"
            encoded_output = root / f"encoded-traversal-{index}.html"
            write_private(encoded_source, encoded_traversal)
            encoded_rejected = run(
                "build", "--data", str(encoded_source), "--template", str(TEMPLATE),
                "--output", str(encoded_output), expected=2,
            )
            encoded_traversal_results.append(
                "safe relative link" in encoded_rejected.stderr
                or "percent encoding" in encoded_rejected.stderr
            )
        record(
            "RE10",
            all(encoded_traversal_results),
            "single/double encoded traversal and encoded NUL links rejected",
        )

        harmless_fetch = json.loads(json.dumps(data))
        harmless_fetch["findings"][0]["detail"] = (
            "The JavaScript fetch() function was discussed in the accepted evidence."
        )
        harmless_source = root / "harmless-fetch.json"
        harmless_output = root / "harmless-fetch.html"
        write_private(harmless_source, harmless_fetch)
        harmless_built = run(
            "build", "--data", str(harmless_source), "--template", str(TEMPLATE),
            "--output", str(harmless_output),
        )
        harmless_build_result = json.loads(harmless_built.stdout)
        harmless_verified = run(
            "verify", "--html", str(harmless_output),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", harmless_build_result["template_sha256"],
            "--expected-data-sha256", harmless_build_result["data_sha256"],
        )
        record(
            "RE11",
            json.loads(harmless_verified.stdout)["findings"] == 1,
            "accepted prose mentioning fetch() does not trigger the executable-code guard",
        )

        contradiction_data = json.loads(json.dumps(data))
        contradiction_data["contradictions"] = [
            {
                "id": "C01", "title": "Open item", "summary": "Needs review",
                "status": "OPEN", "finding_ids": ["F01"], "source_ids": ["S01"],
            },
            {
                "id": "C02", "title": "Resolved item", "summary": "Reconciled",
                "status": "RESOLVED", "finding_ids": ["F01"], "source_ids": ["S01"],
            },
        ]
        contradiction_data["findings"][0]["contradiction_ids"] = ["C01", "C02"]
        contradiction_source = root / "contradictions.json"
        contradiction_output = root / "contradictions.html"
        write_private(contradiction_source, contradiction_data)
        run(
            "build", "--data", str(contradiction_source), "--template", str(TEMPLATE),
            "--output", str(contradiction_output),
        )
        contradiction_html = contradiction_output.read_text(encoding="utf-8")
        record(
            "RE12",
            "<dt>Open contradictions</dt><dd>1</dd>" in contradiction_html
            and 'class="state state-open">Open</span>' in contradiction_html
            and 'class="state state-resolved">Resolved</span>' in contradiction_html,
            "open count and contradiction state styling follow each accepted status",
        )

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
            "--template", str(TEMPLATE),
            "--expected-template-sha256", build_result["template_sha256"],
            "--expected-data-sha256", build_result["data_sha256"],
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

        record(
            "RE13",
            '.finding[hidden], .source[hidden] { display: block !important; }' in html
            and 'a[href^="#"]' in html
            and "target.classList.contains(\"source\")" in html,
            "print includes filtered records and internal links reveal filtered targets",
        )

        tampered = root / "tampered.html"
        tampered.write_text(
            html.replace("Accepted research", "Unverified replacement", 1)
            + "<script>globalThis.__unexpected = true;</script>",
            encoding="utf-8",
        )
        tampered.chmod(0o600)
        rejected = run(
            "verify", "--html", str(tampered),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", build_result["template_sha256"],
            "--expected-data-sha256", build_result["data_sha256"],
            expected=2,
        )
        record(
            "RE14",
            "canonical accepted rendering" in rejected.stderr,
            "visible or executable post-build tampering fails canonical verification",
        )

        marker_prose = json.loads(json.dumps(data))
        marker_prose["findings"][0]["detail"] = (
            "Literal markers __RESEARCH_EXPLORER_DATA__ and "
            "__RESEARCH_EXPLORER_CONTENT__ are inert research text."
        )
        marker_source = root / "marker-prose.json"
        marker_output = root / "marker-prose.html"
        write_private(marker_source, marker_prose)
        marker_build = json.loads(run(
            "build", "--data", str(marker_source), "--template", str(TEMPLATE),
            "--output", str(marker_output),
        ).stdout)
        run(
            "verify", "--html", str(marker_output),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", marker_build["template_sha256"],
            "--expected-data-sha256", marker_build["data_sha256"],
        )
        record("RE15", True, "literal template markers remain inert accepted prose")

        malformed_results = []
        for index, mutate in enumerate((
            lambda item: item.__setitem__("schema_version", True),
            lambda item: item["sources"][0].__setitem__("url", "http://[bad/"),
            lambda item: item["series"].append({
                "id": "N01", "title": "Huge", "unit": "u", "note": "",
                "points": [{"label": "x", "value": 10**1000}],
            }),
        )):
            malformed = json.loads(json.dumps(data))
            mutate(malformed)
            malformed_source = root / f"malformed-{index}.json"
            malformed_output = root / f"malformed-{index}.html"
            write_private(malformed_source, malformed)
            result = run(
                "build", "--data", str(malformed_source), "--template", str(TEMPLATE),
                "--output", str(malformed_output), expected=2,
            )
            malformed_results.append(
                not malformed_output.exists() and "Traceback" not in result.stderr
            )
        record(
            "RE16",
            all(malformed_results),
            "Boolean schema, malformed URL, and huge integer fail with controlled diagnostics",
        )

        linked_bytes = b"accepted artifact\n"
        linked_file = root / "accepted.txt"
        linked_file.write_bytes(linked_bytes)
        linked_file.chmod(0o600)
        linked = json.loads(json.dumps(data))
        linked["artifacts"][0].update({
            "name": linked_file.name,
            "media_type": "text/plain",
            "size_bytes": len(linked_bytes),
            "sha256": hashlib.sha256(linked_bytes).hexdigest(),
            "relative_link": linked_file.name,
        })
        linked_source = root / "linked.json"
        linked_output = root / "linked.html"
        write_private(linked_source, linked)
        linked_build = json.loads(run(
            "build", "--data", str(linked_source), "--template", str(TEMPLATE),
            "--artifact-root", str(root), "--output", str(linked_output),
        ).stdout)
        run(
            "verify", "--html", str(linked_output),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", linked_build["template_sha256"],
            "--expected-data-sha256", linked_build["data_sha256"],
            "--artifact-root", str(root),
        )

        separate_root = root / "separate-export"
        separate_root.mkdir(mode=0o700)
        mismatched_output = separate_root / "misbound.html"
        mismatched_build = run(
            "build", "--data", str(linked_source), "--template", str(TEMPLATE),
            "--artifact-root", str(root), "--output", str(mismatched_output),
            expected=2,
        )
        copied_output = separate_root / "copied.html"
        copied_output.write_bytes(linked_output.read_bytes())
        copied_output.chmod(0o600)
        mismatched_verify = run(
            "verify", "--html", str(copied_output),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", linked_build["template_sha256"],
            "--expected-data-sha256", linked_build["data_sha256"],
            "--artifact-root", str(root), expected=2,
        )
        record(
            "RE18",
            not mismatched_output.exists()
            and "must exactly match" in mismatched_build.stderr
            and "must exactly match" in mismatched_verify.stderr,
            "artifact validation is bound to the HTML directory at build and verify",
        )

        linked_file.write_bytes(b"changed artifact\n")
        changed = run(
            "verify", "--html", str(linked_output),
            "--expected-run-id", data["report"]["run_id"],
            "--template", str(TEMPLATE),
            "--expected-template-sha256", linked_build["template_sha256"],
            "--expected-data-sha256", linked_build["data_sha256"],
            "--artifact-root", str(root), expected=2,
        )
        record(
            "RE17",
            "accepted identity" in changed.stderr,
            "relative artifact links require exact existing accepted bytes",
        )

    failures = [item for item in RESULTS if not item[1]]
    for case_id, passed, detail in RESULTS:
        print(f"{case_id}|{'SIMULATED_PASS' if passed else 'SIMULATED_FAIL'}|{detail}")
    print(f"TOTAL={len(RESULTS)} PASS={len(RESULTS) - len(failures)} FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
