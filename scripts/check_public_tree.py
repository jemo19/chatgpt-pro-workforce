#!/usr/bin/env python3
"""Fail when the proposed public repository contains unsafe local evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import stat
import subprocess
import sys
from urllib.parse import unquote


EXCLUDED_PARTS = {".git", ".codex", ".build", "dist", "__pycache__", ".pytest_cache"}
EXCLUDED_ROOT_FILES = {
    "PRODUCT.md",
    "BUILD_REPORT.md",
    "CAPABILITY_REPORT.md",
    "FORWARD_TEST_RESULTS.md",
    "FINAL_SKILL_MANIFEST.md",
}
FORBIDDEN_BASENAMES = {
    ".env",
    ".env.local",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
}
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TOKEN_PATTERNS = {
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{24,}\b"),
    "OpenAI-style secret": re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
PRIVATE_EVIDENCE_PATTERNS = {
    "absolute user-home path": re.compile(
        rb"(?<![A-Za-z0-9])/(?:home|Users)/[A-Za-z0-9._-]+/"
    ),
    "absolute mounted-data path": re.compile(
        rb"(?<![A-Za-z0-9])/mnt/[A-Za-z0-9._-]+/"
    ),
    "absolute Windows user path": re.compile(
        rb"\b[A-Za-z]:\\Users\\[^\\\r\n]+\\"
    ),
    "live ChatGPT conversation URL": re.compile(
        rb"https?://chatgpt\.com/c/[A-Za-z0-9_-]+"
    ),
    "timestamped local backup": re.compile(
        rb"(?:backup|disabled)-20[0-9]{6}T[0-9]{6}Z"
    ),
}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if len(relative.parts) == 1 and relative.name in EXCLUDED_ROOT_FILES:
            continue
        if path.is_file() or path.is_symlink():
            files.append(path)
    return files


def tracked_files(root: Path) -> set[str] | None:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        return None
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def check_markdown_links(root: Path, path: Path, text: str, errors: list[str]) -> None:
    for raw in MARKDOWN_LINK.findall(text):
        target = raw.strip().split()[0].strip("<>")
        if not target or target.startswith("#") or re.match(r"^[a-z]+://", target):
            continue
        path_part = unquote(target.partition("#")[0])
        destination = (path.parent / path_part).resolve()
        try:
            destination.relative_to(root)
        except ValueError:
            errors.append(f"link escapes repository: {path.relative_to(root)} -> {target}")
            continue
        if not destination.exists():
            errors.append(f"broken local link: {path.relative_to(root)} -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    files = candidate_files(root)
    tracked = tracked_files(root)

    if tracked is not None:
        for forbidden in EXCLUDED_ROOT_FILES | {"PRODUCT.md"}:
            if forbidden in tracked:
                errors.append(f"private authoring file is tracked: {forbidden}")
        for rel in tracked:
            if rel == ".codex" or rel.startswith(".codex/") or rel.startswith(".build/"):
                errors.append(f"private state is tracked: {rel}")

    for path in files:
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            errors.append(f"symlink is not allowed: {relative}")
            continue
        if not stat.S_ISREG(mode):
            errors.append(f"special file is not allowed: {relative}")
            continue
        if path.name in FORBIDDEN_BASENAMES or path.name.startswith(".env."):
            errors.append(f"credential-prone filename: {relative}")
        data = path.read_bytes()
        if len(data) > 2_000_000:
            errors.append(f"unexpected file larger than 2 MB: {relative}")
        for label, pattern in PRIVATE_EVIDENCE_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"possible {label} in {relative}")
        for label, pattern in TOKEN_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"possible {label} in {relative}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                errors.append(f"text file is not UTF-8: {relative}")
                continue
            if data and not data.endswith(b"\n"):
                errors.append(f"text file has no final newline: {relative}")
            if path.suffix.lower() == ".md":
                check_markdown_links(root, path, text, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"RESULT=FAIL errors={len(errors)}")
        return 1
    print(f"RESULT=PASS files_checked={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
