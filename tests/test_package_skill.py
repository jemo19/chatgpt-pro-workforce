#!/usr/bin/env python3
"""Runtime regression tests for deterministic, fail-closed release packaging."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(sys.argv[1]).resolve()
HELPER = ROOT / "scripts/package_skill.py"
RESULTS: list[tuple[str, bool, str]] = []
sys.dont_write_bytecode = True


def record(case_id: str, passed: bool, detail: str) -> None:
    RESULTS.append((case_id, passed, detail))


def load_helper():
    spec = importlib.util.spec_from_file_location("workforce_package_skill", HELPER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load package helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(skill: Path, output: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), str(skill), "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"package returned {result.returncode}, expected {expected}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


def verify(output: Path, expected: int = 2) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), "--verify-only", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"verify returned {result.returncode}, expected {expected}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return result


def forge_release(
    output: Path,
    *,
    skill_name: str,
    records: list[object],
    members: list[tuple[str, bytes, int]] | None = None,
    raw_manifest: bytes | None = None,
) -> None:
    if members is None:
        members = []
        for record in records:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                continue
            data = str(record["path"]).encode("utf-8")
            record["bytes"] = len(data)
            record["sha256"] = hashlib.sha256(data).hexdigest()
            members.append((f"{skill_name}/{record['path']}", data, 0o100644))
    archive_buffer = bytearray()
    with tempfile.SpooledTemporaryFile() as stream:
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for member, data, mode in members:
                info = zipfile.ZipInfo(member, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (mode & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        stream.seek(0)
        archive_buffer.extend(stream.read())
    archive_bytes = bytes(archive_buffer)
    digest = hashlib.sha256(archive_bytes).hexdigest()
    manifest = {
        "schema_version": 2,
        "release_id": digest,
        "skill": skill_name,
        "files": records,
        "archive": {
            "path": output.name,
            "bytes": len(archive_bytes),
            "sha256": digest,
        },
    }
    output.write_bytes(archive_bytes)
    output.with_suffix(".manifest.json").write_bytes(
        raw_manifest
        if raw_manifest is not None
        else (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8")
    )
    output.with_suffix(".zip.sha256").write_text(
        f"{digest}  {output.name}\n", encoding="ascii"
    )


def main() -> int:
    helper = load_helper()
    with tempfile.TemporaryDirectory(prefix="workforce-package-test-") as name:
        temp = Path(name)
        skill = temp / "example-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: example-skill\n---\n", encoding="utf-8")
        (skill / "LICENSE").write_text("test distribution license\n", encoding="utf-8")
        (skill / "agents").mkdir()
        (skill / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Example"\n', encoding="utf-8"
        )
        (skill / "references").mkdir()
        payload_path = skill / "references" / "payload.md"
        payload_path.write_text("version one\n", encoding="utf-8")

        output = temp / "release" / "example-skill.zip"
        run(skill, output)
        first = output.read_bytes()
        manifest = json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(first).hexdigest()
        with zipfile.ZipFile(output) as archive:
            expected_members = [
                f"example-skill/{item['path']}" for item in manifest["files"]
            ]
            members_match = all(
                hashlib.sha256(archive.read(f"example-skill/{item['path']}")).hexdigest()
                == item["sha256"]
                and len(archive.read(f"example-skill/{item['path']}")) == item["bytes"]
                for item in manifest["files"]
            ) and archive.namelist() == expected_members
        record(
            "PK01",
            members_match
            and "example-skill/LICENSE" in expected_members
            and manifest["archive"]["sha256"] == digest
            and output.with_suffix(".zip.sha256").read_text(encoding="ascii")
            == f"{digest}  example-skill.zip\n"
            and helper.verify_release(output)["release_id"] == digest,
            "archive, manifest, digest, and source inventory describe identical bytes",
        )

        run(skill, output)
        record("PK02", output.read_bytes() == first, "repeated packaging is byte deterministic")

        records = helper.inventory(skill.resolve())
        output.write_bytes(b"accepted previous release")
        previous = output.read_bytes()
        payload_path.write_text("mutated after inventory\n", encoding="utf-8")
        try:
            helper.write_archive(skill.resolve(), output, records)
            mutation_rejected = False
        except ValueError as exc:
            mutation_rejected = "changed after inventory" in str(exc)
        record(
            "PK03",
            mutation_rejected and output.read_bytes() == previous,
            "post-inventory source mutation is rejected before replacing an accepted archive",
        )

        target = temp / "outside-target.zip"
        target.write_bytes(b"outside sentinel")
        symlink_output = temp / "release" / "symlink.zip"
        symlink_output.symlink_to(target)
        try:
            helper._prepare_output_path(symlink_output, skill.resolve())
            symlink_rejected = False
        except ValueError as exc:
            symlink_rejected = "symbolic link" in str(exc)
        record(
            "PK04",
            symlink_rejected and target.read_bytes() == b"outside sentinel",
            "output symlink is rejected without touching its target",
        )

        sidecar_target = temp / "outside-manifest.json"
        sidecar_target.write_text("sentinel\n", encoding="utf-8")
        sidecar_directory = temp / "release-sidecar"
        sidecar_directory.mkdir()
        sidecar_output = sidecar_directory / "example-skill.zip"
        sidecar_output.with_suffix(".manifest.json").symlink_to(sidecar_target)
        try:
            helper._prepare_output_path(sidecar_output, skill.resolve())
            sidecar_rejected = False
        except ValueError as exc:
            sidecar_rejected = "symbolic link" in str(exc)
        record(
            "PK05",
            sidecar_rejected and sidecar_target.read_text(encoding="utf-8") == "sentinel\n",
            "manifest sidecar symlink is rejected without following it",
        )

        inside = skill / "generated" / "skill.zip"
        try:
            helper._prepare_output_path(inside, skill.resolve())
            alias_rejected = False
        except ValueError as exc:
            alias_rejected = "outside the skill source tree" in str(exc)
        record(
            "PK06",
            alias_rejected and not inside.parent.exists(),
            "source/output alias is rejected before creating paths inside the source tree",
        )

        manifest_path = output.with_suffix(".manifest.json")
        digest_path = output.with_suffix(".zip.sha256")
        old_release = {
            output: b"old archive",
            manifest_path: b"old manifest\n",
            digest_path: b"old digest\n",
        }
        for path, content in old_release.items():
            path.write_bytes(content)
        transaction_records = helper.inventory(skill.resolve())
        original_replace = helper.os.replace
        publish_count = 0

        def fail_second_publish(source_path, target_path):
            nonlocal publish_count
            target = Path(target_path)
            if target in old_release:
                publish_count += 1
                if publish_count == 2:
                    raise OSError("synthetic manifest publish failure")
            return original_replace(source_path, target_path)

        helper.os.replace = fail_second_publish
        try:
            try:
                helper.write_release(skill.resolve(), output, transaction_records)
                transaction_failed = False
            except OSError:
                transaction_failed = True
        finally:
            helper.os.replace = original_replace
        record(
            "PK08",
            transaction_failed
            and all(path.read_bytes() == content for path, content in old_release.items()),
            "mid-publish failure restores the prior archive, manifest, and digest",
        )

        source_link = temp / "linked-skill"
        source_link.symlink_to(skill, target_is_directory=True)
        linked_output = temp / "release" / "linked.zip"
        linked = run(source_link, linked_output, expected=2)
        record(
            "PK07",
            "skill source must not traverse a symbolic link" in linked.stderr
            and not linked_output.exists(),
            "symlinked source root fails closed",
        )

        hardlink_source = temp / "outside-source.md"
        hardlink_source.write_text("outside\n", encoding="utf-8")
        source_alias = skill / "references" / "hardlinked.md"
        os.link(hardlink_source, source_alias)
        hardlink_output = temp / "release-hardlink" / "example-skill.zip"
        hardlink_result = run(skill, hardlink_output, expected=2)
        source_alias.unlink()
        record(
            "PK09",
            "single-link regular file" in hardlink_result.stderr,
            "source hard links are rejected before packaging",
        )

        collision_a = skill / "references" / "Case.md"
        collision_b = skill / "references" / "case.md"
        collision_a.write_text("A\n", encoding="utf-8")
        collision_b.write_text("B\n", encoding="utf-8")
        collision_output = temp / "release-collision" / "example-skill.zip"
        collision_result = run(skill, collision_output, expected=2)
        collision_a.unlink()
        collision_b.unlink()
        record(
            "PK10",
            "ambiguous portable member paths" in collision_result.stderr,
            "case-folded portable path collisions are rejected",
        )

        # Verify that a failed rollback retains the recovery bytes instead of
        # deleting the only copy of the prior generation.
        for path, content in old_release.items():
            path.write_bytes(content)
        failure_records = helper.inventory(skill.resolve())
        publish_count = 0

        def fail_publish_and_archive_rollback(source_path, target_path):
            nonlocal publish_count
            source = Path(source_path)
            target = Path(target_path)
            if target in old_release and ".backup." not in source.name:
                publish_count += 1
                if publish_count == 2:
                    raise OSError("synthetic publish failure")
            if target == output and ".backup." in source.name:
                raise OSError("synthetic rollback failure")
            return original_replace(source_path, target_path)

        helper.os.replace = fail_publish_and_archive_rollback
        try:
            try:
                helper.write_release(skill.resolve(), output, failure_records)
                rollback_failed = False
                rollback_message = ""
            except OSError as exc:
                rollback_failed = True
                rollback_message = str(exc)
        finally:
            helper.os.replace = original_replace
        retained = list(output.parent.glob(f".{output.name}.backup.*"))
        record(
            "PK11",
            rollback_failed
            and "backups retained" in rollback_message
            and any(path.read_bytes() == old_release[output] for path in retained),
            "incomplete rollback retains and reports recoverable backup bytes",
        )

        # Re-establish a coherent release, then exercise two real packaging
        # processes against the same destination. The writer lock serializes
        # commit-marker publication and the final reader must accept one full set.
        run(skill, output)
        processes = [
            subprocess.Popen(
                [sys.executable, str(HELPER), str(skill), "--output", str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        concurrent_results = [
            process.communicate(timeout=20) + (process.returncode,)
            for process in processes
        ]
        record(
            "PK12",
            all(item[2] == 0 for item in concurrent_results)
            and helper.verify_release(output)["release_id"]
            == hashlib.sha256(output.read_bytes()).hexdigest(),
            "concurrent publishers serialize and leave one reader-verifiable generation",
        )

        hostile_paths = [
            ("../escape.md", "non-canonical release member path"),
            ("/absolute.md", "non-canonical release member path"),
            ("references\\backslash.md", "unsafe release member path"),
            ("references/control-\x01.md", "unsafe release member path"),
            ("references//double.md", "non-canonical release member path"),
            ("references/e\u0301.md", "not NFC canonical"),
            ("references/CON.txt", "non-portable release member path"),
        ]
        path_rejections = []
        for hostile_path, expected_error in hostile_paths:
            hostile_records: list[object] = [
                {"path": "SKILL.md", "bytes": 0, "sha256": ""},
                {"path": "agents/openai.yaml", "bytes": 0, "sha256": ""},
                {"path": hostile_path, "bytes": 0, "sha256": ""},
            ]
            forge_release(
                output,
                skill_name="example-skill",
                records=hostile_records,
            )
            result = verify(output)
            path_rejections.append(
                expected_error in result.stderr and "Traceback" not in result.stderr
            )
        record(
            "PK13",
            all(path_rejections),
            "verify-only rejects traversal, absolute, backslash, control, non-canonical, and non-portable manifest paths",
        )

        identity_rejections = []
        normal_records: list[object] = [
            {"path": "SKILL.md", "bytes": 0, "sha256": ""},
            {"path": "agents/openai.yaml", "bytes": 0, "sha256": ""},
        ]
        forge_release(output, skill_name="other-skill", records=normal_records)
        identity_rejections.append("unexpected skill name" in verify(output).stderr)

        malformed_records: list[object] = [
            {"path": "SKILL.md", "bytes": 0, "sha256": "", "unexpected": True},
            {"path": "agents/openai.yaml", "bytes": 0, "sha256": ""},
        ]
        forge_release(output, skill_name="example-skill", records=malformed_records)
        identity_rejections.append("malformed record" in verify(output).stderr)

        duplicate_records: list[object] = [
            {
                "path": "SKILL.md",
                "bytes": len(b"skill"),
                "sha256": hashlib.sha256(b"skill").hexdigest(),
            },
            {
                "path": "SKILL.md",
                "bytes": len(b"skill"),
                "sha256": hashlib.sha256(b"skill").hexdigest(),
            },
            {
                "path": "agents/openai.yaml",
                "bytes": len(b"agent"),
                "sha256": hashlib.sha256(b"agent").hexdigest(),
            },
        ]
        forge_release(
            output,
            skill_name="example-skill",
            records=duplicate_records,
            members=[
                ("example-skill/SKILL.md", b"skill", 0o100644),
                ("example-skill/agents/openai.yaml", b"agent", 0o100644),
            ],
        )
        identity_rejections.append("duplicate member path" in verify(output).stderr)

        collision_records: list[object] = [
            {"path": "SKILL.md", "bytes": 0, "sha256": ""},
            {"path": "agents/openai.yaml", "bytes": 0, "sha256": ""},
            {"path": "references/Case.md", "bytes": 0, "sha256": ""},
            {"path": "references/case.md", "bytes": 0, "sha256": ""},
        ]
        forge_release(output, skill_name="example-skill", records=collision_records)
        identity_rejections.append("ambiguous portable" in verify(output).stderr)

        unexpected_root_records: list[object] = [
            {"path": "LICENSE", "bytes": 0, "sha256": ""},
            {"path": "SKILL.md", "bytes": 0, "sha256": ""},
            {"path": "agents/openai.yaml", "bytes": 0, "sha256": ""},
            {"path": "tests/private-fixture.txt", "bytes": 0, "sha256": ""},
        ]
        forge_release(
            output, skill_name="example-skill", records=unexpected_root_records
        )
        identity_rejections.append(
            "unexpected top-level release directory" in verify(output).stderr
        )

        # JSON object keys are part of the signed manifest contract too. A
        # parser that silently keeps the last duplicate can validate a meaning
        # different from the bytes an auditor inspected.
        forge_release(output, skill_name="example-skill", records=normal_records)
        valid_manifest = output.with_suffix(".manifest.json").read_text(encoding="utf-8")
        duplicate_key_manifest = valid_manifest.replace(
            '"schema_version": 2,', '"schema_version": 2, "schema_version": 2,', 1
        ).encode("utf-8")
        output.with_suffix(".manifest.json").write_bytes(duplicate_key_manifest)
        identity_rejections.append("duplicate key" in verify(output).stderr)
        record(
            "PK14",
            all(identity_rejections),
            "verify-only rejects unexpected skill identity, malformed and duplicate records, portable collisions, unexpected roots, and duplicate JSON keys",
        )

        type_rejections = []
        for unexpected_mode in (0o120777, 0o010644):
            typed_records: list[object] = [
                {
                    "path": "LICENSE",
                    "bytes": len(b"license"),
                    "sha256": hashlib.sha256(b"license").hexdigest(),
                },
                {
                    "path": "SKILL.md",
                    "bytes": len(b"skill"),
                    "sha256": hashlib.sha256(b"skill").hexdigest(),
                },
                {
                    "path": "agents/openai.yaml",
                    "bytes": len(b"agent"),
                    "sha256": hashlib.sha256(b"agent").hexdigest(),
                },
            ]
            forge_release(
                output,
                skill_name="example-skill",
                records=typed_records,
                members=[
                    ("example-skill/LICENSE", b"license", 0o100644),
                    ("example-skill/SKILL.md", b"skill", unexpected_mode),
                    ("example-skill/agents/openai.yaml", b"agent", 0o100644),
                ],
            )
            type_rejections.append("unexpected entry type" in verify(output).stderr)
        record(
            "PK15",
            all(type_rejections),
            "verify-only rejects symbolic-link and special-file ZIP entries even when their bytes match the manifest",
        )

    failures = [item for item in RESULTS if not item[1]]
    for case_id, passed, detail in RESULTS:
        print(f"{case_id}|{'LIVE_PASS' if passed else 'LIVE_FAIL'}|{detail}")
    print(f"TOTAL={len(RESULTS)} PASS={len(RESULTS) - len(failures)} FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
