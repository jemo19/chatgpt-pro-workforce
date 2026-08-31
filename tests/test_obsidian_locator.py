#!/usr/bin/env python3
"""Isolated integration tests for the bounded Obsidian vault locator."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


SKILL = Path(sys.argv[1]).resolve()
HELPER = SKILL / "scripts/obsidian_locator.py"
PASS = "LIVE_PASS"
FAIL = "LIVE_FAIL"
RESULTS: list[tuple[str, str, str]] = []


def record(case_id: str, passed: bool, evidence: str) -> None:
    RESULTS.append((case_id, PASS if passed else FAIL, evidence))


def run(env: dict[str, str], *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"command {args!r} returned {result.returncode}, expected {expected}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


def decode(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise AssertionError("locator output is not an object")
    return value


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workforce-obsidian-locator-") as temp_name:
        temp = Path(temp_name)
        home = temp / "home"
        config = temp / "config"
        home.mkdir()
        (config / "obsidian").mkdir(parents=True)
        env = os.environ.copy()
        env.update({"HOME": str(home), "XDG_CONFIG_HOME": str(config)})

        help_result = run(env, "--help")
        record(
            "OL01",
            "--project-candidate" in help_result.stdout and "--marker-root" in help_result.stdout,
            "bounded discovery options exposed",
        )

        registered = temp / "Registered Vault"
        (registered / ".obsidian").mkdir(parents=True)
        registry = config / "obsidian" / "obsidian.json"
        registry.write_text(
            json.dumps({"vaults": {"safe-id": {"path": str(registered), "open": True}}}),
            encoding="utf-8",
        )
        registry_result = decode(run(env))
        recommendation = registry_result["recommendation"]
        registry_ok = (
            isinstance(recommendation, dict)
            and recommendation.get("path") == str(registered)
            and recommendation.get("source") == "config_open"
            and recommendation.get("open") is True
            and recommendation.get("marker") is True
        )
        record("OL02", registry_ok, "open platform registry candidate ranked and marker verified")

        explicit = temp / "Explicit Project Vault"
        (explicit / ".obsidian").mkdir(parents=True)
        explicit_result = decode(run(env, "--project-candidate", str(explicit)))
        explicit_recommendation = explicit_result["recommendation"]
        record(
            "OL03",
            isinstance(explicit_recommendation, dict)
            and explicit_recommendation.get("path") == str(explicit)
            and explicit_recommendation.get("source") == "project_instruction",
            "trusted project candidate outranked registry",
        )

        marker_root = temp / "approved-marker-root"
        deep_vault = marker_root / "level-one" / "level-two" / "Marker Vault"
        (deep_vault / ".obsidian").mkdir(parents=True)
        depth_one = decode(run(env, "--marker-root", str(marker_root), "--max-depth", "1"))
        depth_three = decode(run(env, "--marker-root", str(marker_root), "--max-depth", "3"))
        paths_one = {item["path"] for item in depth_one["candidates"]}
        paths_three = {item["path"] for item in depth_three["candidates"]}
        record(
            "OL04",
            str(deep_vault) not in paths_one and str(deep_vault) in paths_three,
            "explicit marker search obeyed depth ceiling",
        )

        duplicate = decode(
            run(
                env,
                "--project-candidate",
                str(registered),
                "--marker-root",
                str(temp),
                "--max-depth",
                "2",
            )
        )
        duplicates = [item for item in duplicate["candidates"] if item["path"] == str(registered)]
        record(
            "OL05",
            len(duplicates) == 1
            and duplicates[0]["source"] == "project_instruction"
            and duplicates[0]["open"] is True,
            "duplicate path merged while preserving stronger source and open evidence",
        )

        unregistered = home / "unregistered-vault"
        (unregistered / ".obsidian").mkdir(parents=True)
        registry.unlink()
        no_default_crawl = decode(run(env))
        record(
            "OL06",
            no_default_crawl["recommendation"] is None and no_default_crawl["candidates"] == [],
            "home directory was not searched without an approved marker root",
        )

        registry.write_text("not-json", encoding="utf-8")
        malformed = decode(run(env))
        malformed_codes = {item["code"] for item in malformed["errors"]}
        record(
            "OL07",
            "config_malformed" in malformed_codes and malformed["recommendation"] is None,
            "malformed registry failed safely with structured evidence",
        )

        registry.write_bytes(b"{" + b"x" * (1024 * 1024 + 1))
        oversized = decode(run(env))
        oversized_codes = {item["code"] for item in oversized["errors"]}
        record(
            "OL08",
            "config_oversized" in oversized_codes and oversized["recommendation"] is None,
            "oversized registry rejected before parsing",
        )

        symlink_target = temp / "symlink-target"
        symlink_target.mkdir()
        symlink_root = temp / "symlink-root"
        symlink_root.symlink_to(symlink_target, target_is_directory=True)
        symlink_result = decode(run(env, "--marker-root", str(symlink_root)))
        symlink_codes = {item["code"] for item in symlink_result["errors"]}
        record(
            "OL09",
            "marker_root_invalid" in symlink_codes and symlink_result["recommendation"] is None,
            "symlink marker root rejected",
        )

        invalid_args = decode(run(env, "--max-depth", "9", expected=2))
        invalid_codes = {item["code"] for item in invalid_args["errors"]}
        record(
            "OL10",
            "invalid_arguments" in invalid_codes and invalid_args["recommendation"] is None,
            "argument ceiling failure remained machine-readable",
        )

        huge_root = temp / "huge-single-directory"
        huge_root.mkdir()
        for index in range(24):
            (huge_root / f"entry-{index:02d}").mkdir()
        huge_result = decode(
            run(
                env,
                "--marker-root",
                str(huge_root),
                "--entry-limit",
                "10",
                "--directory-limit",
                "100",
            )
        )
        huge_codes = {item["code"] for item in huge_result["errors"]}
        record(
            "OL11",
            huge_result.get("complete") is False
            and "entry_limit_reached" in huge_codes
            and huge_result["discovery"]["entries_examined"] == 10,
            "large single directory stopped at explicit total-entry ceiling",
        )

        wide_root = temp / "wide-no-markers"
        wide_root.mkdir()
        for index in range(18):
            (wide_root / f"branch-{index:02d}" / "leaf").mkdir(parents=True)
        wide_result = decode(
            run(
                env,
                "--marker-root",
                str(wide_root),
                "--directory-limit",
                "5",
                "--entry-limit",
                "100",
            )
        )
        wide_codes = {item["code"] for item in wide_result["errors"]}
        record(
            "OL12",
            wide_result.get("complete") is False
            and "directory_limit_reached" in wide_codes
            and wide_result["discovery"]["directories_visited"] == 5,
            "wide tree without markers stopped at explicit directory ceiling",
        )

        broad_codes: set[str] = set()
        for broad_root in (Path("/"), home, Path("/proc")):
            broad_result = decode(run(env, "--marker-root", str(broad_root)))
            broad_codes.update(
                item["code"]
                for item in broad_result["errors"]
                if item["source"] == "marker_search"
            )
        record(
            "OL13",
            broad_codes == {"marker_root_too_broad"},
            "filesystem root, resolved home, and mount root rejected",
        )

        excluded_root = temp / "excluded-profiles"
        hidden_vault = excluded_root / ".mozilla" / "profile" / "Hidden Vault"
        (hidden_vault / ".obsidian").mkdir(parents=True)
        visible_vault = excluded_root / "research" / "Visible Vault"
        (visible_vault / ".obsidian").mkdir(parents=True)
        excluded_result = decode(run(env, "--marker-root", str(excluded_root)))
        excluded_paths = {item["path"] for item in excluded_result["candidates"]}
        record(
            "OL14",
            str(hidden_vault) not in excluded_paths and str(visible_vault) in excluded_paths,
            "browser-profile exclusion is case-folded and normal research remains discoverable",
        )

        registry.unlink(missing_ok=True)
        registry.symlink_to(temp / "registry-target.json")
        (temp / "registry-target.json").write_text('{"vaults": {}}', encoding="utf-8")
        registry_symlink = decode(run(env))
        registry_symlink_codes = {item["code"] for item in registry_symlink["errors"]}
        record(
            "OL15",
            "config_symlink" in registry_symlink_codes,
            "registry symlink and ancestor-swap path rejected before descriptor read",
        )

    failures = [item for item in RESULTS if item[1] == FAIL]
    for case_id, classification, evidence in RESULTS:
        print(f"{case_id}|{classification}|{evidence}")
    print(f"TOTAL={len(RESULTS)}")
    print(f"LIVE_PASS={len(RESULTS) - len(failures)}")
    print(f"LIVE_FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
