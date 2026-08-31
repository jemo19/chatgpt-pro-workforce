#!/usr/bin/env python3
"""Safely discover likely Obsidian vaults without selecting or modifying one."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MAX_DEPTH = 4
HARD_MAX_DEPTH = 8
DEFAULT_CANDIDATE_LIMIT = 100
HARD_CANDIDATE_LIMIT = 1000
DEFAULT_DIRECTORY_LIMIT = 2000
HARD_DIRECTORY_LIMIT = 10000
DEFAULT_ENTRY_LIMIT = 20000
HARD_ENTRY_LIMIT = 100000
PER_DIRECTORY_ENTRY_LIMIT = 10000
DEFAULT_MAX_SECONDS = 5.0
HARD_MAX_SECONDS = 30.0
MAX_CONFIG_BYTES = 1024 * 1024

SKIP_DIRECTORY_NAMES_CASEFOLD = frozenset(
    {
        ".cache",
        ".git",
        ".hg",
        ".mozilla",
        ".svn",
        ".terraform",
        ".tox",
        ".venv",
        "brave-browser",
        "chrome",
        "chromium",
        "google-chrome",
        "mozilla",
        "profiles",
        "trash",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "proc",
        "sys",
        "dev",
        "run",
        "lost+found",
    }
)

SOURCE_PRIORITY = {
    "project_instruction": 4,
    "config_open": 3,
    "config": 2,
    "marker_search": 1,
}


class JsonArgumentParser(argparse.ArgumentParser):
    """Make argument failures machine-readable while retaining normal --help."""

    def error(self, message: str) -> None:
        payload = {
            "version": 1,
            "complete": False,
            "recommendation": None,
            "candidates": [],
            "errors": [{"code": "invalid_arguments", "source": "arguments", "detail": message}],
        }
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        raise SystemExit(2)


def bounded_int(name: str, minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"{name} must be between {minimum} and {maximum}")
        return number

    return parse


def bounded_float(name: str, minimum: float, maximum: float):
    def parse(value: str) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be a number") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"{name} must be between {minimum:g} and {maximum:g}")
        return number

    return parse


def skip_directory(name: str) -> bool:
    folded = name.casefold()
    return folded in SKIP_DIRECTORY_NAMES_CASEFOLD or folded.startswith(".trash")


def registry_files() -> list[tuple[str, Path]]:
    """Return only known Obsidian registry locations for the current platform."""

    home_value = os.environ.get("HOME")
    home = Path(home_value).expanduser() if home_value else None
    results: list[tuple[str, Path]] = []

    if sys.platform == "darwin":
        if home:
            results.append(
                ("macos_application_support", home / "Library/Application Support/obsidian/obsidian.json")
            )
    elif os.name == "nt" or sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            results.append(("windows_appdata", Path(appdata) / "obsidian/obsidian.json"))
    else:
        xdg_value = os.environ.get("XDG_CONFIG_HOME")
        if xdg_value:
            results.append(("linux_native", Path(xdg_value) / "obsidian/obsidian.json"))
        elif home:
            results.append(("linux_native", home / ".config/obsidian/obsidian.json"))
        if home:
            results.extend(
                [
                    (
                        "linux_flatpak",
                        home / ".var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json",
                    ),
                    (
                        "linux_snap",
                        home / "snap/obsidian/current/.config/obsidian/obsidian.json",
                    ),
                    (
                        "linux_snap",
                        home / "snap/obsidian/current/.config/Obsidian/obsidian.json",
                    ),
                ]
            )

    # Environment combinations can alias locations. Keep the first source label.
    seen: set[str] = set()
    unique: list[tuple[str, Path]] = []
    for source, path in results:
        key = os.path.normcase(os.path.abspath(os.fspath(path)))
        if key not in seen:
            seen.add(key)
            unique.append((source, path))
    return unique


def error(code: str, source: str, detail: str) -> dict[str, str]:
    return {"code": code, "source": source, "detail": detail}


def path_has_symlink(path: Path) -> bool:
    """Check existing components without following a candidate symlink."""

    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def normalize_candidate(raw_path: object) -> tuple[Path | None, str | None]:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "candidate path is missing or is not a string"
    if "\x00" in raw_path:
        return None, "candidate path contains a null byte"
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        return None, "candidate path must be absolute"
    try:
        if path_has_symlink(path):
            return None, "candidate path contains a symbolic link"
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError):
        return None, "candidate path could not be resolved"
    return resolved, None


def candidate_record(
    path: Path,
    source: str,
    *,
    vault_id: str | None = None,
    is_open: bool = False,
) -> dict[str, Any]:
    exists = path.exists()
    is_directory = path.is_dir() if exists else False
    marker = is_directory and (path / ".obsidian").is_dir() and not (path / ".obsidian").is_symlink()
    readable = is_directory and os.access(path, os.R_OK | os.X_OK)
    return {
        "vault_id": vault_id,
        "path": os.fspath(path),
        "open": bool(is_open),
        "source": source,
        "marker": bool(marker),
        "access": {
            "exists": bool(exists),
            "directory": bool(is_directory),
            "readable": bool(readable),
        },
    }


def read_registry(
    source_name: str, registry: Path
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not registry.exists():
        return [], []
    source = f"config:{source_name}"
    try:
        if not registry.is_absolute() or path_has_symlink(registry):
            return [], [error("config_symlink", source, "registry path is not a direct absolute path")]
        file_stat = registry.lstat()
    except OSError:
        return [], [error("config_unreadable", source, "registry metadata could not be read")]
    if stat.S_ISLNK(file_stat.st_mode):
        return [], [error("config_symlink", source, "registry is a symbolic link")]
    if not stat.S_ISREG(file_stat.st_mode):
        return [], [error("config_not_regular", source, "registry is not a regular file")]
    if file_stat.st_size > MAX_CONFIG_BYTES:
        return [], [error("config_oversized", source, f"registry exceeds {MAX_CONFIG_BYTES} bytes")]
    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(registry, flags)
        opened_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened_stat.st_mode)
            or opened_stat.st_dev != file_stat.st_dev
            or opened_stat.st_ino != file_stat.st_ino
            or opened_stat.st_size > MAX_CONFIG_BYTES
        ):
            return [], [error("config_changed", source, "registry identity changed during safe open")]
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            return [], [error("config_oversized", source, f"registry exceeds {MAX_CONFIG_BYTES} bytes")]
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError):
        return [], [error("config_unreadable", source, "registry could not be read as UTF-8")]
    except json.JSONDecodeError:
        return [], [error("config_malformed", source, "registry is not valid JSON")]
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    if not isinstance(data, dict) or not isinstance(data.get("vaults"), dict):
        return [], [error("config_schema", source, "registry does not contain a vault map")]

    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for raw_id, value in sorted(data["vaults"].items(), key=lambda item: str(item[0])):
        if not isinstance(value, dict):
            errors.append(error("config_vault_invalid", source, "vault entry is not an object"))
            continue
        path, problem = normalize_candidate(value.get("path"))
        if problem or path is None:
            errors.append(error("config_path_invalid", source, problem or "candidate path is invalid"))
            continue
        vault_id = str(raw_id) if isinstance(raw_id, (str, int)) else None
        is_open = value.get("open") is True
        candidates.append(
            candidate_record(path, "config_open" if is_open else "config", vault_id=vault_id, is_open=is_open)
        )
    return candidates, errors


def scan_for_markers(
    raw_root: str,
    max_depth: int,
    remaining: int,
    budget: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
    source = "marker_search"
    root, problem = normalize_candidate(raw_root)
    if problem or root is None:
        return [], [error("marker_root_invalid", source, problem or "marker root is invalid")], False
    home = Path.home().resolve(strict=False)
    if root == Path(root.anchor) or root == home or os.path.ismount(root):
        return [], [
            error(
                "marker_root_too_broad",
                source,
                "marker root must be an explicitly approved project or note-root directory, not a filesystem, mount, or home root",
            )
        ], False
    try:
        root_stat = root.lstat()
    except OSError:
        return [], [error("marker_root_unreadable", source, "marker root could not be read")], False
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        return [], [error("marker_root_not_directory", source, "marker root is not a directory")], False

    start_device = root_stat.st_dev
    pending: list[tuple[Path, int]] = [(root, 0)]
    found: list[dict[str, Any]] = []
    scan_errors: list[dict[str, str]] = []
    ceiling_hit = False

    def stop_for_limit(code: str, detail: str) -> None:
        nonlocal ceiling_hit
        ceiling_hit = True
        if not any(item["code"] == code for item in scan_errors):
            scan_errors.append(error(code, source, detail))

    while pending:
        if time.monotonic() >= budget["deadline"]:
            stop_for_limit("time_limit_reached", "marker discovery stopped at the approved wall-time ceiling")
            break
        if budget["directories_visited"] >= budget["directory_limit"]:
            stop_for_limit("directory_limit_reached", "marker discovery stopped at the approved directory ceiling")
            break
        directory, depth = pending.pop()
        try:
            directory_stat = directory.lstat()
        except OSError:
            continue
        if (
            stat.S_ISLNK(directory_stat.st_mode)
            or not stat.S_ISDIR(directory_stat.st_mode)
            or directory_stat.st_dev != start_device
        ):
            continue
        budget["directories_visited"] += 1
        per_directory_entries = 0
        try:
            scanner = os.scandir(directory)
        except OSError:
            # Inaccessible descendants are expected and disclose no path details.
            continue
        marker_found = False
        children: list[Path] = []
        with scanner:
            for entry in scanner:
                if time.monotonic() >= budget["deadline"]:
                    stop_for_limit("time_limit_reached", "marker discovery stopped at the approved wall-time ceiling")
                    break
                if budget["entries_examined"] >= budget["entry_limit"]:
                    stop_for_limit("entry_limit_reached", "marker discovery stopped at the approved total-entry ceiling")
                    break
                if per_directory_entries >= PER_DIRECTORY_ENTRY_LIMIT:
                    stop_for_limit(
                        "per_directory_limit_reached",
                        f"one directory exceeded the {PER_DIRECTORY_ENTRY_LIMIT}-entry inspection ceiling",
                    )
                    break
                budget["entries_examined"] += 1
                per_directory_entries += 1
                if entry.name == ".obsidian":
                    try:
                        marker_stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if (
                        stat.S_ISDIR(marker_stat.st_mode)
                        and not stat.S_ISLNK(marker_stat.st_mode)
                        and marker_stat.st_dev == start_device
                    ):
                        marker_found = True
                    continue
                if depth >= max_depth or skip_directory(entry.name):
                    continue
                try:
                    entry_stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if (
                    stat.S_ISDIR(entry_stat.st_mode)
                    and not stat.S_ISLNK(entry_stat.st_mode)
                    and entry_stat.st_dev == start_device
                ):
                    children.append(Path(entry.path))

        if marker_found:
            if len(found) >= remaining:
                stop_for_limit("candidate_limit_reached", "additional marker candidates were omitted")
                break
            found.append(candidate_record(directory, source))
            # A vault's internals are not searched for nested vaults.
            if ceiling_hit:
                break
            continue
        if ceiling_hit:
            break
        # Sorting is deterministic and bounded by PER_DIRECTORY_ENTRY_LIMIT.
        children.sort(key=lambda item: os.path.normcase(os.fspath(item)), reverse=True)
        pending.extend((child, depth + 1) for child in children)

    return found, scan_errors, ceiling_hit


def merge_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in candidates:
        key = os.path.normcase(item["path"])
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
            continue
        existing_priority = SOURCE_PRIORITY[existing["source"]]
        item_priority = SOURCE_PRIORITY[item["source"]]
        if item_priority > existing_priority:
            stronger, weaker = item, existing
            merged[key] = stronger
        else:
            stronger, weaker = existing, item
        stronger["open"] = bool(stronger["open"] or weaker["open"])
        stronger["marker"] = bool(stronger["marker"] or weaker["marker"])
        if stronger["vault_id"] is None and weaker["vault_id"] is not None:
            stronger["vault_id"] = weaker["vault_id"]

    def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        return (-SOURCE_PRIORITY[item["source"]], -int(item["marker"]), os.path.normcase(item["path"]))

    return sorted(merged.values(), key=sort_key)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(
        description=(
            "Read known Obsidian registries and explicitly approved locations to recommend, "
            "but never select or modify, a likely vault."
        )
    )
    parser.add_argument(
        "--project-candidate",
        action="append",
        default=[],
        metavar="ABSOLUTE_PATH",
        help="repeatable vault path named by trusted project instructions",
    )
    parser.add_argument(
        "--marker-root",
        action="append",
        default=[],
        metavar="ABSOLUTE_PATH",
        help="repeatable explicitly approved root to search only for .obsidian directories",
    )
    parser.add_argument(
        "--max-depth",
        type=bounded_int("max depth", 0, HARD_MAX_DEPTH),
        default=DEFAULT_MAX_DEPTH,
        help=f"marker-search depth (default {DEFAULT_MAX_DEPTH}, maximum {HARD_MAX_DEPTH})",
    )
    parser.add_argument(
        "--candidate-limit",
        type=bounded_int("candidate limit", 1, HARD_CANDIDATE_LIMIT),
        default=DEFAULT_CANDIDATE_LIMIT,
        help=f"maximum emitted candidates (default {DEFAULT_CANDIDATE_LIMIT})",
    )
    parser.add_argument(
        "--directory-limit",
        type=bounded_int("directory limit", 1, HARD_DIRECTORY_LIMIT),
        default=DEFAULT_DIRECTORY_LIMIT,
        help=f"maximum visited marker-search directories (default {DEFAULT_DIRECTORY_LIMIT}, maximum {HARD_DIRECTORY_LIMIT})",
    )
    parser.add_argument(
        "--entry-limit",
        type=bounded_int("entry limit", 1, HARD_ENTRY_LIMIT),
        default=DEFAULT_ENTRY_LIMIT,
        help=f"maximum examined marker-search entries (default {DEFAULT_ENTRY_LIMIT}, maximum {HARD_ENTRY_LIMIT})",
    )
    parser.add_argument(
        "--max-seconds",
        type=bounded_float("max seconds", 0.1, HARD_MAX_SECONDS),
        default=DEFAULT_MAX_SECONDS,
        help=f"marker-search wall-time ceiling (default {DEFAULT_MAX_SECONDS:g}s, maximum {HARD_MAX_SECONDS:g}s)",
    )
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.monotonic()
    budget: dict[str, Any] = {
        "directory_limit": args.directory_limit,
        "entry_limit": args.entry_limit,
        "directories_visited": 0,
        "entries_examined": 0,
        "deadline": started + args.max_seconds,
    }
    gathered: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    ceiling_hit = False

    for raw_path in args.project_candidate:
        path, problem = normalize_candidate(raw_path)
        if problem or path is None:
            errors.append(
                error("project_candidate_invalid", "project_instruction", problem or "candidate path is invalid")
            )
            continue
        gathered.append(candidate_record(path, "project_instruction"))

    for source_name, registry in registry_files():
        registry_candidates, registry_errors = read_registry(source_name, registry)
        gathered.extend(registry_candidates)
        errors.extend(registry_errors)

    # Deduplicate before scanning so the ceiling is based on emitted paths.
    gathered = merge_candidates(gathered)
    if len(gathered) > args.candidate_limit:
        gathered = gathered[: args.candidate_limit]
        ceiling_hit = True

    if not ceiling_hit:
        for raw_root in args.marker_root:
            remaining = args.candidate_limit - len(gathered)
            if remaining <= 0:
                ceiling_hit = True
                break
            found, scan_errors, scan_ceiling = scan_for_markers(
                raw_root,
                args.max_depth,
                remaining,
                budget,
            )
            gathered.extend(found)
            errors.extend(scan_errors)
            gathered = merge_candidates(gathered)
            if len(gathered) > args.candidate_limit:
                gathered = gathered[: args.candidate_limit]
                ceiling_hit = True
            ceiling_hit = ceiling_hit or scan_ceiling
            if ceiling_hit:
                break

    candidates = merge_candidates(gathered)[: args.candidate_limit]
    if ceiling_hit and not any(
        item["code"] in {
            "candidate_limit_reached",
            "directory_limit_reached",
            "entry_limit_reached",
            "per_directory_limit_reached",
            "time_limit_reached",
        }
        for item in errors
    ):
        errors.append(error("candidate_limit_reached", "discovery", "additional candidates were omitted"))

    payload = {
        "version": 1,
        "complete": not ceiling_hit,
        "recommendation": candidates[0] if candidates else None,
        "candidates": candidates,
        "errors": sorted(errors, key=lambda item: (item["code"], item["source"], item["detail"])),
        "discovery": {
            "directories_visited": budget["directories_visited"],
            "entries_examined": budget["entries_examined"],
            "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
            "limits": {
                "max_depth": args.max_depth,
                "candidates": args.candidate_limit,
                "directories": args.directory_limit,
                "entries": args.entry_limit,
                "per_directory_entries": PER_DIRECTORY_ENTRY_LIMIT,
                "seconds": args.max_seconds,
            },
        },
    }
    indent = 2 if args.pretty else None
    print(json.dumps(payload, indent=indent, sort_keys=True, separators=None if indent else (",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
