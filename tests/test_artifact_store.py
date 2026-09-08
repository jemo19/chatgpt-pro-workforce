#!/usr/bin/env python3
"""Adversarial integration tests for the bounded artifact-store helper."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import time
import warnings
import zipfile


SKILL = Path(sys.argv[1]).resolve()
HELPER = SKILL / "scripts/artifact_store.py"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("artifact_store_under_test", HELPER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load artifact store helper")
store = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = store
SPEC.loader.exec_module(store)
RESULTS: list[tuple[str, bool, str]] = []


def record(case_id: str, passed: bool, detail: str) -> None:
    RESULTS.append((case_id, passed, detail))


def run_cli(*args: str, cwd: Path | None = None, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"unexpected exit {result.returncode} for {args!r}: {result.stdout} {result.stderr}"
        )
    return result


def zip_bytes(entries: list[tuple[zipfile.ZipInfo | str, bytes]], compression: int = zipfile.ZIP_STORED) -> bytes:
    stream = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(stream, "w", compression=compression) as archive:
            for name, payload in entries:
                archive.writestr(name, payload)
    return stream.getvalue()


def write(path: Path, data: bytes, mode: int = 0o600) -> Path:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)
    return path


def provenance(source_name: str = "worker-return.bin") -> object:
    return store.Provenance(source_name, "BROWSER_ATTACHMENT", "L01", "conversation-safe-01")


def expect_error(callable_object, phrase: str) -> bool:
    try:
        callable_object()
    except store.ArtifactStoreError as exc:
        return phrase in str(exc)
    return False


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="workforce-artifact-store-") as name:
        test_root = Path(name)
        run_root = test_root / "run"
        limits = store.Limits(
            max_members=8,
            max_source_bytes=2 * 1024 * 1024,
            max_compressed_bytes=2 * 1024 * 1024,
            max_expanded_bytes=2 * 1024 * 1024,
            max_ratio=20,
            max_file_bytes=1024 * 1024,
            max_base64_bytes=2 * 1024 * 1024,
        )
        initialized = store.init_store(run_root, "RUN-TEST-001")
        marker = run_root / "manifests/artifact-store.json"
        record(
            "AS01",
            initialized["run_id"] == "RUN-TEST-001"
            and stat.S_IMODE(run_root.stat().st_mode) == 0o700
            and stat.S_IMODE(marker.stat().st_mode) == 0o600,
            "store binds a private POSIX run root to one run ID",
        )

        safe_zip = zip_bytes([("docs/", b""), ("docs/report.txt", b"evidence\n"), ("data.csv", b"a,b\n1,2\n")])
        archive_path = write(test_root / "safe.zip", safe_zip)
        inspected = store.inspect_zip_path(archive_path, limits)
        record(
            "AS02",
            inspected["member_count"] == 3
            and [item["path"] for item in inspected["members"]] == ["data.csv", "docs", "docs/report.txt"]
            and not (run_root / "raw").exists(),
            "ZIP inventory is deterministic and inspection performs no extraction",
        )

        manifest = store.ingest_path(
            run_root, "RUN-TEST-001", "A001", archive_path, provenance("safe.zip"),
            kind="ZIP", limits=limits,
        )
        raw_path = run_root / manifest["raw"]["stored_path"]
        extracted = run_root / "raw/extracted" / inspected["source_sha256"] / "docs/report.txt"
        record(
            "AS03",
            raw_path.read_bytes() == safe_zip
            and raw_path.name == hashlib.sha256(safe_zip).hexdigest()
            and stat.S_IMODE(raw_path.stat().st_mode) == 0o400
            and extracted.read_bytes() == b"evidence\n"
            and stat.S_IMODE(extracted.stat().st_mode) == 0o400,
            "accepted ZIP is stored by digest and extracted exclusively as private read-only bytes",
        )

        hostile_names = {
            "absolute": "/escape.txt",
            "drive": "C:/escape.txt",
            "traversal": "../escape.txt",
            "nested traversal": "safe/../../escape.txt",
            "backslash": "safe\\escape.txt",
        }
        hostile_results = []
        for label, member_name in hostile_names.items():
            payload = zip_bytes([(member_name, b"x")])
            hostile_results.append(expect_error(lambda payload=payload: store.inspect_zip_bytes(payload, limits), "archive member"))
        control_name = zip_bytes([("bad\nname.txt", b"x")])
        long_name = zip_bytes([("x" * 300 + ".txt", b"x")])
        record(
            "AS04",
            all(hostile_results)
            and expect_error(lambda: store.inspect_zip_bytes(control_name, limits), "malformed")
            and expect_error(lambda: store.inspect_zip_bytes(long_name, limits), "component"),
            "absolute, drive, traversal, backslash, control, and overlong ZIP paths fail closed",
        )

        duplicate_zip = zip_bytes([("same.txt", b"one"), ("same.txt", b"two")])
        case_zip = zip_bytes([("Report.txt", b"one"), ("report.txt", b"two")])
        unicode_zip = zip_bytes([("caf\u00e9.txt", b"one"), ("cafe\u0301.txt", b"two")])
        conflict_zip = zip_bytes([("node", b"file"), ("node/child.txt", b"child")])
        folded_conflict_zip = zip_bytes([("Node", b"file"), ("node/child.txt", b"child")])
        record(
            "AS05",
            expect_error(lambda: store.inspect_zip_bytes(duplicate_zip, limits), "duplicate")
            and expect_error(lambda: store.inspect_zip_bytes(case_zip, limits), "collision")
            and expect_error(lambda: store.inspect_zip_bytes(unicode_zip, limits), "collision")
            and expect_error(lambda: store.inspect_zip_bytes(conflict_zip, limits), "conflict")
            and expect_error(lambda: store.inspect_zip_bytes(folded_conflict_zip, limits), "conflict"),
            "duplicate, case-fold, Unicode, and exact/folded ancestor destination collisions are rejected",
        )

        symlink_info = zipfile.ZipInfo("link")
        symlink_info.create_system = 3
        symlink_info.external_attr = (stat.S_IFLNK | 0o777) << 16
        fifo_info = zipfile.ZipInfo("pipe")
        fifo_info.create_system = 3
        fifo_info.external_attr = (stat.S_IFIFO | 0o600) << 16
        unsupported = bytearray(zip_bytes([("unsupported.bin", b"x")]))
        unsupported[8:10] = (99).to_bytes(2, "little")
        central_offset = unsupported.find(b"PK\x01\x02")
        unsupported[central_offset + 10:central_offset + 12] = (99).to_bytes(2, "little")
        record(
            "AS06",
            expect_error(lambda: store.inspect_zip_bytes(zip_bytes([(symlink_info, b"target")]), limits), "special file")
            and expect_error(lambda: store.inspect_zip_bytes(zip_bytes([(fifo_info, b"")]), limits), "special file")
            and expect_error(lambda: store.inspect_zip_bytes(bytes(unsupported), limits), "unsupported compression"),
            "ZIP symbolic links, special entries, and unsupported compression fail before extraction",
        )

        ratio_bomb = zip_bytes([("compressible.bin", b"A" * 300_000)], zipfile.ZIP_DEFLATED)
        many = zip_bytes([(f"f{index}.txt", b"x") for index in range(9)])
        large = zip_bytes([("large.bin", b"x" * 2048)])
        total_large = zip_bytes([("one.bin", b"x" * 700), ("two.bin", b"y" * 700)])
        small_file_limit = store.Limits(8, 2_000_000, 2_000_000, 2_000_000, 2, 1024, 2_000_000)
        total_limit = store.Limits(8, 2_000_000, 2_000_000, 1200, 20, 1024, 2_000_000)
        record(
            "AS07",
            expect_error(lambda: store.inspect_zip_bytes(ratio_bomb, small_file_limit), "per-file limit")
            and expect_error(lambda: store.inspect_zip_bytes(many, limits), "member-count")
            and expect_error(lambda: store.inspect_zip_bytes(large, small_file_limit), "per-file limit")
            and expect_error(lambda: store.inspect_zip_bytes(total_large, total_limit), "expanded-byte"),
            "member count, expanded size, per-file size, and compression-ratio metadata are bounded",
        )
        ratio_limits = store.Limits(8, 2_000_000, 2_000_000, 2_000_000, 2, 1_000_000, 2_000_000)
        record(
            "AS08",
            expect_error(lambda: store.inspect_zip_bytes(ratio_bomb, ratio_limits), "expansion ratio"),
            "high-ratio ZIP bomb metadata is rejected without member extraction",
        )

        plain = write(test_root / "plain.bin", b"same returned bytes")
        first = store.ingest_path(
            run_root, "RUN-TEST-001", "A002", plain, provenance("first.bin"), kind="FILE", limits=limits,
        )
        second = store.ingest_path(
            run_root, "RUN-TEST-001", "A003", plain, provenance("second.bin"), kind="FILE", limits=limits,
        )
        record(
            "AS09",
            first["raw"]["stored_path"] == second["raw"]["stored_path"]
            and second["raw"]["content_reused"] is True
            and second["raw"]["same_content_artifact_ids"] == ["A002"]
            and first["source"]["source_name"] != second["source"]["source_name"],
            "duplicate content reuses one immutable object while preserving separate provenance",
        )

        mutable = write(test_root / "mutable.bin", b"before")
        record(
            "AS10",
            expect_error(
                lambda: store.ingest_path(
                    run_root, "RUN-TEST-001", "A004", mutable, provenance(), kind="FILE", limits=limits,
                    after_read_hook=lambda: mutable.write_bytes(b"after!"),
                ),
                "changed during intake",
            )
            and not (run_root / "manifests/intake/A004.json").exists(),
            "same-inode source mutation is detected before raw storage or provenance commit",
        )

        source_link_target = write(test_root / "link-target.bin", b"source")
        source_symlink = test_root / "source-link.bin"
        source_symlink.symlink_to(source_link_target)
        source_hardlink = test_root / "source-hard.bin"
        os.link(source_link_target, source_hardlink)
        record(
            "AS11",
            expect_error(
                lambda: store.ingest_path(run_root, "RUN-TEST-001", "A005", source_symlink, provenance(), kind="FILE", limits=limits),
                "safe regular file",
            )
            and expect_error(
                lambda: store.ingest_path(run_root, "RUN-TEST-001", "A006", source_hardlink, provenance(), kind="FILE", limits=limits),
                "one filesystem link",
            ),
            "source symlinks and hardlinks fail closed",
        )

        encoded_payload = base64.b64encode(b"base64 recovered bytes") + b"\n"
        encoded_path = write(test_root / "artifact.b64", encoded_payload)
        base64_manifest = store.ingest_base64_path(
            run_root,
            "RUN-TEST-001",
            "A007",
            encoded_path,
            store.Provenance("artifact.b64", "BASE64_RECOVERY", "L02", "conversation-safe-02"),
            limits=limits,
        )
        invalid_b64 = write(test_root / "invalid.b64", b"%%not-base64%%")
        tiny_b64_limits = store.Limits(8, 1024, 1024, 1024, 20, 8, 12)
        record(
            "AS12",
            (run_root / base64_manifest["raw"]["stored_path"]).read_bytes() == b"base64 recovered bytes"
            and expect_error(
                lambda: store.ingest_base64_path(
                    run_root, "RUN-TEST-001", "A008", invalid_b64,
                    store.Provenance("invalid", "BASE64_RECOVERY", "L02", "conversation-safe-02"), limits=limits,
                ),
                "malformed",
            )
            and expect_error(
                lambda: store.ingest_base64_path(
                    run_root, "RUN-TEST-001", "A009", encoded_path,
                    store.Provenance("oversized", "BASE64_RECOVERY", "L02", "conversation-safe-02"), limits=tiny_b64_limits,
                ),
                "byte limit",
            )
            and expect_error(
                lambda: store.ingest_base64_path(
                    run_root, "RUN-TEST-001", "A010", encoded_path,
                    provenance("wrong-kind.b64"), limits=limits,
                ),
                "BASE64_RECOVERY",
            ),
            "base64 fallback validates syntax and bounds both encoded and decoded bytes",
        )

        incoming = write(run_root / "incoming/delete-me.tmp", b"temporary")
        pending = store.plan_cleanup(
            run_root, "RUN-TEST-001", "C001", [incoming], reason="temporary recovery copy",
            authorization_state="PENDING_EXPLICIT_AUTHORIZATION", authorization_reference=None,
        )
        record(
            "AS13",
            pending["targets"][0]["sha256"] == hashlib.sha256(b"temporary").hexdigest()
            and expect_error(lambda: store.apply_cleanup(run_root, "RUN-TEST-001", "C001"), "lacks explicit"),
            "cleanup plan binds exact path, size, hash, inode and explicit authorization state",
        )

        authorized_target = write(run_root / "incoming/authorized.tmp", b"authorized")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C002", [authorized_target], reason="user-approved temporary copy",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="current-turn exact manifest approval",
        )
        applied = store.apply_cleanup(run_root, "RUN-TEST-001", "C002")
        quarantined_path = run_root / applied["outcomes"][0]["quarantine_path"]
        record(
            "AS14",
            applied["outcomes"][0]["outcome"] == "QUARANTINED"
            and not authorized_target.exists()
            and quarantined_path.read_bytes() == b"authorized",
            "authorized cleanup moves exact reverified bytes into private recoverable quarantine",
        )

        changed_target = write(run_root / "incoming/changed.tmp", b"planned")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C003", [changed_target], reason="mutation test",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        changed_target.write_bytes(b"changed")
        record(
            "AS15",
            expect_error(lambda: store.apply_cleanup(run_root, "RUN-TEST-001", "C003"), "identity changed")
            and changed_target.read_bytes() == b"changed",
            "post-plan hash/identity mutation blocks the whole cleanup before quarantine",
        )

        external = write(test_root / "outside.tmp", b"outside")
        target_for_link = write(run_root / "incoming/link-target.tmp", b"inside")
        cleanup_symlink = run_root / "incoming/cleanup-link.tmp"
        cleanup_symlink.symlink_to(target_for_link)
        cleanup_hardlink = run_root / "incoming/cleanup-hard.tmp"
        os.link(target_for_link, cleanup_hardlink)
        record(
            "AS16",
            expect_error(
                lambda: store.plan_cleanup(
                    run_root, "RUN-TEST-001", "C004", [external], reason="escape",
                    authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test",
                ),
                "outside",
            )
            and expect_error(
                lambda: store.plan_cleanup(
                    run_root, "RUN-TEST-001", "C005", [cleanup_symlink], reason="symlink",
                    authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test",
                ),
                "symbolic-link",
            )
            and expect_error(
                lambda: store.plan_cleanup(
                    run_root, "RUN-TEST-001", "C006", [cleanup_hardlink], reason="hardlink",
                    authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test",
                ),
                "one filesystem link",
            ),
            "cleanup rejects outside-root, symlink, and hardlink targets",
        )

        interrupted_target = write(run_root / "candidates/interrupted.tmp", b"candidate")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C007", [interrupted_target], reason="interruption test",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        interrupted = False
        try:
            store.apply_cleanup(
                run_root, "RUN-TEST-001", "C007",
                after_unlink_hook=lambda _path: (_ for _ in ()).throw(RuntimeError("simulated interruption")),
            )
        except RuntimeError:
            interrupted = True
        state_path = run_root / "manifests/cleanup/C007.state.json"
        unknown = json.loads(state_path.read_text(encoding="utf-8"))["outcomes"][0]["outcome"]
        reconciled = store.reconcile_cleanup(run_root, "RUN-TEST-001", "C007")
        record(
            "AS17",
            interrupted and unknown == "OUTCOME_UNKNOWN"
            and reconciled["outcomes"][0]["outcome"] == "QUARANTINED_RECONCILED",
            "interrupted quarantine persists OUTCOME_UNKNOWN and reconciles the exact retained bytes",
        )

        retained_target = write(run_root / "candidates/retained.tmp", b"candidate")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C008", [retained_target], reason="retained reconciliation",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        plan = json.loads((run_root / "manifests/cleanup/C008.json").read_text(encoding="utf-8"))
        retained_state = store._initial_cleanup_state(plan)
        retained_state["outcomes"][0]["outcome"] = "OUTCOME_UNKNOWN"
        retained_state["outcomes"][0]["detail"] = "simulated pre-unlink interruption"
        store._exclusive_json(run_root / "manifests/cleanup/C008.state.json", retained_state)
        retained = store.reconcile_cleanup(run_root, "RUN-TEST-001", "C008")
        record(
            "AS18",
            retained["outcomes"][0]["outcome"] == "RETAINED_RECONCILED"
            and retained_target.exists()
            and expect_error(
                lambda: store.apply_cleanup(run_root, "RUN-TEST-001", "C008"),
                "requires a new exact plan",
            ),
            "unknown cleanup with the original file present reconciles without retrying the move",
        )

        linked_root = test_root / "linked-run"
        linked_root.symlink_to(run_root, target_is_directory=True)
        record(
            "AS19",
            expect_error(lambda: store.init_store(linked_root, "RUN-TEST-001"), "symbolic-link component"),
            "run-root symlink escape is rejected",
        )

        unrelated = test_root / "unrelated-cwd"
        unrelated.mkdir(mode=0o700)
        cli_result = run_cli(
            "init", "--run-root", str(run_root), "--run-id", "RUN-TEST-001", cwd=unrelated,
        )
        cli_source = write(test_root / "cli-source.bin", b"from unrelated cwd")
        cli_ingest = run_cli(
            "ingest-file",
            "--run-root", str(run_root),
            "--run-id", "RUN-TEST-001",
            "--artifact-id", "A011",
            "--source-name", "cli-source.bin",
            "--source-kind", "LOCAL_FIXTURE",
            "--lane-id", "L03",
            "--conversation-id", "local-fixture",
            "--source", str(cli_source),
            cwd=unrelated,
        )
        record(
            "AS20",
            json.loads(cli_result.stdout)["run_id"] == "RUN-TEST-001"
            and json.loads(cli_ingest.stdout)["artifact_id"] == "A011",
            "CLI initializes and ingests with explicit paths from an unrelated current directory",
        )

        bad_name = test_root / ("private-secret-" + "x" * 150 + ".zip")
        write(bad_name, b"not a zip")
        diagnostic = run_cli(
            "inspect-zip", "--source", str(bad_name), "--max-source-bytes", "16", expected=2,
        )
        record(
            "AS21",
            "Traceback" not in diagnostic.stderr
            and str(bad_name) not in diagnostic.stderr
            and len(diagnostic.stderr) < 500
            and diagnostic.stderr.startswith("artifact_store: error:"),
            "CLI failures use bounded controlled diagnostics without echoing sensitive paths",
        )

        public_root = test_root / "public-run-root"
        public_root.mkdir(mode=0o755)
        public_root.chmod(0o755)
        record(
            "AS22",
            expect_error(lambda: store.init_store(public_root, "RUN-PUBLIC"), "group or other access")
            and stat.S_IMODE(public_root.stat().st_mode) == 0o755,
            "existing non-private run roots are rejected without silently changing their permissions",
        )

        corrupt_bytes = bytearray(zip_bytes([("first.txt", b"first"), ("second.txt", b"second")]))
        with zipfile.ZipFile(io.BytesIO(corrupt_bytes), "r") as corrupt_reader:
            second_info = corrupt_reader.getinfo("second.txt")
            offset = second_info.header_offset
            name_length = int.from_bytes(corrupt_bytes[offset + 26:offset + 28], "little")
            extra_length = int.from_bytes(corrupt_bytes[offset + 28:offset + 30], "little")
            payload_offset = offset + 30 + name_length + extra_length
            corrupt_bytes[payload_offset] ^= 0x01
        corrupt_snapshot = store.Snapshot(
            bytes(corrupt_bytes), len(corrupt_bytes), hashlib.sha256(corrupt_bytes).hexdigest()
        )
        rejected_corrupt = expect_error(
            lambda: store.ingest_snapshot(
                run_root, "RUN-TEST-001", "A012", corrupt_snapshot, provenance("corrupt.zip"),
                kind="ZIP", limits=limits,
            ),
            "extraction failed",
        )
        corrupt_raw = run_root / f"raw/sha256/{corrupt_snapshot.sha256[:2]}/{corrupt_snapshot.sha256}"
        corrupt_state_path = run_root / "manifests/intake-state/A012.json"
        corrupt_state = json.loads(corrupt_state_path.read_text(encoding="utf-8"))
        corrupt_reconciled = store.reconcile_intake(run_root, "RUN-TEST-001", "A012")
        record(
            "AS23",
            rejected_corrupt
            and corrupt_raw.read_bytes() == corrupt_snapshot.data
            and corrupt_state["state"] == "REJECTED_RETAINED"
            and corrupt_state["observation"]["raw"] == "EXACT"
            and corrupt_state["observation"]["extraction"] == "MISSING"
            and corrupt_reconciled["state"] == "REJECTED_RETAINED"
            and not (run_root / "raw/extracted" / corrupt_snapshot.sha256).exists()
            and not (run_root / "manifests/intake/A012.json").exists()
            and not any(path.name.startswith(f".{corrupt_snapshot.sha256}.") for path in (run_root / "raw/extracted").iterdir()),
            "CRC failure retains exact raw bytes under durable rejected lineage and leaves no partial extraction",
        )

        interrupted_zip = zip_bytes([("interrupted.txt", b"interrupted")])
        interrupted_snapshot = store.Snapshot(
            interrupted_zip, len(interrupted_zip), hashlib.sha256(interrupted_zip).hexdigest()
        )
        interrupted_staging = run_root / "raw/extracted" / f".{interrupted_snapshot.sha256}.simulated-crash"

        def interrupt_after_raw(_raw_path: Path, _reused: bool) -> None:
            interrupted_staging.mkdir(mode=0o700, parents=True)
            staged = interrupted_staging / "partial.bin"
            staged.write_bytes(b"partial")
            staged.chmod(0o400)
            raise SystemExit("simulated abrupt process loss")

        interrupted_raised = False
        try:
            store.ingest_snapshot(
                run_root,
                "RUN-TEST-001",
                "A013",
                interrupted_snapshot,
                provenance("interrupted.zip"),
                kind="ZIP",
                limits=limits,
                after_raw_hook=interrupt_after_raw,
            )
        except SystemExit:
            interrupted_raised = True
        interrupted_state_path = run_root / "manifests/intake-state/A013.json"
        interrupted_before = json.loads(interrupted_state_path.read_text(encoding="utf-8"))
        interrupted_reconciled = store.reconcile_intake(run_root, "RUN-TEST-001", "A013")
        record(
            "AS24",
            interrupted_raised
            and interrupted_before["state"] == "INTENT"
            and interrupted_reconciled["state"] == "OUTCOME_UNKNOWN_RETAINED"
            and interrupted_reconciled["observation"]["raw"] == "EXACT"
            and interrupted_reconciled["observation"]["extraction"] == "MISSING"
            and interrupted_reconciled["observation"]["abandoned_staging_trees_removed"] == 1
            and not interrupted_staging.exists()
            and not (run_root / "manifests/intake/A013.json").exists()
            and expect_error(
                lambda: store.ingest_snapshot(
                    run_root,
                    "RUN-TEST-001",
                    "A013",
                    interrupted_snapshot,
                    provenance("retry.zip"),
                    kind="ZIP",
                    limits=limits,
                ),
                "reconcile it before reuse",
            ),
            "abrupt intake after raw publication is traceable, cleans bounded staging, and suppresses blind reuse",
        )

        extracted_zip = zip_bytes([("complete-before-crash.txt", b"complete")])
        extracted_snapshot = store.Snapshot(
            extracted_zip, len(extracted_zip), hashlib.sha256(extracted_zip).hexdigest()
        )
        extracted_interrupted = False
        try:
            store.ingest_snapshot(
                run_root,
                "RUN-TEST-001",
                "A014",
                extracted_snapshot,
                provenance("complete-before-crash.zip"),
                kind="ZIP",
                limits=limits,
                after_extract_hook=lambda _path: (_ for _ in ()).throw(SystemExit("simulated crash")),
            )
        except SystemExit:
            extracted_interrupted = True
        extracted_reconciled = json.loads(
            run_cli(
                "reconcile-intake",
                "--run-root", str(run_root),
                "--run-id", "RUN-TEST-001",
                "--artifact-id", "A014",
            ).stdout
        )
        record(
            "AS25",
            extracted_interrupted
            and extracted_reconciled["state"] == "OUTCOME_UNKNOWN_RETAINED"
            and extracted_reconciled["observation"]["raw"] == "EXACT"
            and extracted_reconciled["observation"]["extraction"] == "EXACT_TO_INTENT"
            and (run_root / f"raw/extracted/{extracted_snapshot.sha256}/complete-before-crash.txt").read_bytes() == b"complete"
            and not (run_root / "manifests/intake/A014.json").exists(),
            "abrupt intake after extraction is retained under durable intent and reconciles through the CLI",
        )

        final_bytes = b"manifest committed before interruption"
        final_snapshot = store.Snapshot(final_bytes, len(final_bytes), hashlib.sha256(final_bytes).hexdigest())
        manifest_interrupted = False
        try:
            store.ingest_snapshot(
                run_root,
                "RUN-TEST-001",
                "A015",
                final_snapshot,
                provenance("manifest-interrupted.bin"),
                kind="FILE",
                limits=limits,
                after_manifest_hook=lambda _path: (_ for _ in ()).throw(SystemExit("simulated crash")),
            )
        except SystemExit:
            manifest_interrupted = True
        manifest_before = json.loads(
            (run_root / "manifests/intake-state/A015.json").read_text(encoding="utf-8")
        )
        manifest_reconciled = store.reconcile_intake(run_root, "RUN-TEST-001", "A015")
        record(
            "AS26",
            manifest_interrupted
            and manifest_before["state"] == "INTENT"
            and (run_root / "manifests/intake/A015.json").is_file()
            and manifest_reconciled["state"] == "COMMITTED"
            and manifest_reconciled["observation"]["raw"] == "EXACT"
            and manifest_reconciled["observation"]["extraction"] == "NOT_APPLICABLE",
            "atomic manifest publication is recovered as committed after an abrupt pre-outcome interruption",
        )

        source_fifo = test_root / "source.fifo"
        os.mkfifo(source_fifo, 0o600)
        fifo_probe = subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "inspect-zip",
                "--source",
                str(source_fifo),
                "--max-source-bytes",
                "1024",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
        record(
            "AS27",
            fifo_probe.returncode == 2
            and "regular file" in fifo_probe.stderr
            and "Traceback" not in fifo_probe.stderr,
            "FIFO source validation fails safely without waiting for a writer",
        )

        replaced_source = write(test_root / "replace-before-open.bin", b"regular")
        real_open = store.os.open
        replaced_once = False

        def replace_before_open(path, flags, *args, **kwargs):
            nonlocal replaced_once
            if not replaced_once and Path(path) == replaced_source:
                replaced_once = True
                replaced_source.unlink()
                os.mkfifo(replaced_source, 0o600)
            return real_open(path, flags, *args, **kwargs)

        store.os.open = replace_before_open
        try:
            replacement_rejected = expect_error(
                lambda: store._read_exact_file(replaced_source, 1024),
                "regular file",
            )
        finally:
            store.os.open = real_open
        record(
            "AS28",
            replaced_once and replacement_rejected and stat.S_ISFIFO(replaced_source.lstat().st_mode),
            "regular-to-FIFO replacement between lstat and open is rejected without blocking",
        )

        intent_mutation = write(run_root / "incoming/intent-mutation.tmp", b"approved")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C009", [intent_mutation], reason="intent mutation",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        intent_result = store.apply_cleanup(
            run_root,
            "RUN-TEST-001",
            "C009",
            after_intent_hook=lambda path: path.write_bytes(b"changed!"),
        )
        record(
            "AS29",
            intent_result["outcomes"][0]["outcome"] == "BLOCKED_IDENTITY_CHANGED"
            and intent_mutation.read_bytes() == b"changed!",
            "same-inode mutation after durable intent is reported and preserved at the source path",
        )

        boundary_mutation = write(run_root / "incoming/boundary-mutation.tmp", b"approved")
        boundary_plan = store.plan_cleanup(
            run_root, "RUN-TEST-001", "C010", [boundary_mutation], reason="quarantine mutation",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        boundary_state = store._initial_cleanup_state(boundary_plan)
        boundary_quarantine = run_root / boundary_state["outcomes"][0]["quarantine_path"]

        def mutate_after_move(_source: Path) -> None:
            boundary_quarantine.write_bytes(b"changed after move")

        boundary_result = store.apply_cleanup(
            run_root, "RUN-TEST-001", "C010", after_unlink_hook=mutate_after_move,
        )
        record(
            "AS30",
            boundary_result["outcomes"][0]["outcome"] == "QUARANTINED_IDENTITY_CHANGED"
            and not boundary_mutation.exists()
            and boundary_quarantine.read_bytes() == b"changed after move",
            "post-move content mutation is never deleted and is reported in recoverable quarantine",
        )

        concurrent_target = write(run_root / "incoming/concurrent.tmp", b"concurrent")
        store.plan_cleanup(
            run_root, "RUN-TEST-001", "C011", [concurrent_target], reason="serialization test",
            authorization_state="AUTHORIZED_EXACT_MANIFEST", authorization_reference="test authorization",
        )
        first_inside = threading.Event()
        release_first = threading.Event()
        concurrent_results: list[dict[str, object]] = []
        concurrent_errors: list[BaseException] = []

        def first_apply() -> None:
            try:
                concurrent_results.append(
                    store.apply_cleanup(
                        run_root,
                        "RUN-TEST-001",
                        "C011",
                        after_intent_hook=lambda _path: (first_inside.set(), release_first.wait(2)),
                    )
                )
            except BaseException as exc:  # captured for deterministic assertion
                concurrent_errors.append(exc)

        def second_apply() -> None:
            try:
                concurrent_results.append(store.apply_cleanup(run_root, "RUN-TEST-001", "C011"))
            except BaseException as exc:  # captured for deterministic assertion
                concurrent_errors.append(exc)

        first_thread = threading.Thread(target=first_apply)
        second_thread = threading.Thread(target=second_apply)
        first_thread.start()
        entered = first_inside.wait(2)
        second_thread.start()
        time.sleep(0.1)
        second_waited = second_thread.is_alive()
        release_first.set()
        first_thread.join(2)
        second_thread.join(2)
        record(
            "AS31",
            entered
            and second_waited
            and not first_thread.is_alive()
            and not second_thread.is_alive()
            and not concurrent_errors
            and len(concurrent_results) == 2
            and all(result["outcomes"][0]["outcome"] == "QUARANTINED" for result in concurrent_results),
            "concurrent cleanup applications serialize and converge on one idempotent quarantine result",
        )

    failures = [item for item in RESULTS if not item[1]]
    for case_id, passed, detail in RESULTS:
        print(f"{case_id}|{'LIVE_PASS' if passed else 'LIVE_FAIL'}|{detail}")
    print(f"TOTAL={len(RESULTS)} PASS={len(RESULTS) - len(failures)} FAIL={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
