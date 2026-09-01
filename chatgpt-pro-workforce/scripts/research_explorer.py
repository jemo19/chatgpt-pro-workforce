#!/usr/bin/env python3
"""Build and verify a self-contained, human-readable research explorer."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from typing import Any, Callable
from urllib.parse import urlsplit


MAX_DATA_BYTES = 4 * 1024 * 1024
MAX_TEMPLATE_BYTES = 5 * 1024 * 1024
MAX_HTML_BYTES = 12 * 1024 * 1024
MAX_ITEMS = 2048
MAX_STRING = 32_768
DATA_MARKER = "__RESEARCH_EXPLORER_DATA__"
CONTENT_MARKER = "__RESEARCH_EXPLORER_CONTENT__"
SHELL_MARKER = 'data-research-explorer="workforce-research-v1"'
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")

TOP_FIELDS = {
    "schema_version", "report", "executive_summary", "findings", "themes",
    "sources", "lanes", "contradictions", "questions", "decisions",
    "recommendations", "artifacts", "tables", "timelines", "series",
}
REPORT_FIELDS = {
    "run_id", "title", "topic", "status", "scope", "methodology",
    "started_at", "completed_at",
}
FINDING_FIELDS = {
    "id", "title", "summary", "confidence", "categories", "source_ids",
    "contradiction_ids", "limitations", "detail",
}
THEME_FIELDS = {"id", "name", "summary", "finding_ids"}
SOURCE_FIELDS = {
    "id", "title", "publisher", "publication_date", "event_date",
    "retrieved_at", "url", "source_type", "quality", "finding_ids", "note",
}
LANE_FIELDS = {"id", "name", "owner", "status", "contribution"}
CONTRADICTION_FIELDS = {
    "id", "title", "summary", "status", "finding_ids", "source_ids",
}
QUESTION_FIELDS = {"id", "question", "status", "detail", "finding_ids"}
DECISION_FIELDS = {"id", "title", "status", "rationale", "finding_ids"}
RECOMMENDATION_FIELDS = {"id", "title", "detail", "priority", "finding_ids"}
ARTIFACT_FIELDS = {
    "id", "name", "media_type", "size_bytes", "sha256", "role",
    "relative_link",
}
TABLE_FIELDS = {"id", "title", "columns", "rows", "note"}
TIMELINE_FIELDS = {"id", "title", "events"}
TIMELINE_EVENT_FIELDS = {"date", "title", "detail", "finding_ids", "source_ids"}
SERIES_FIELDS = {"id", "title", "unit", "points", "note"}
SERIES_POINT_FIELDS = {"label", "value"}

REPORT_STATES = {"ACCEPTED", "ACCEPTED_WITH_LIMITATIONS"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNRESOLVED"}
SOURCE_TYPES = {"PRIMARY", "SECONDARY", "DATASET", "STANDARD", "OTHER"}
QUALITY = {"HIGH", "MEDIUM", "LOW", "UNRATED"}
LANE_STATES = {"ACCEPTED", "ACCEPTED_WITH_LIMITATIONS", "PARTIAL", "REJECTED"}
CONTRADICTION_STATES = {"OPEN", "RESOLVED", "BOUNDED"}
QUESTION_STATES = {"OPEN", "ANSWERED", "DEFERRED"}
DECISION_STATES = {"APPROVED", "DEFERRED", "REJECTED"}
PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


class ExplorerError(ValueError):
    """A bounded error safe to show to a local operator."""


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {_safe_text(message, 300)}\n")


def _safe_text(value: object, limit: int = 300) -> str:
    text = str(value).encode("ascii", "backslashreplace").decode("ascii")
    text = " ".join("".join(c if 32 <= ord(c) < 127 else " " for c in text).split())
    return text[:limit] + ("..." if len(text) > limit else "")


def _object(value: Any, field: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExplorerError(f"{field} must be an object")
    unknown = set(value) - allowed
    if unknown:
        raise ExplorerError(f"{field} contains {len(unknown)} unknown field(s)")
    return value


def _string(value: Any, field: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ExplorerError(f"{field} must be a string")
    if required and not value.strip():
        raise ExplorerError(f"{field} must not be empty")
    if len(value) > MAX_STRING:
        raise ExplorerError(f"{field} is too long")
    return "".join(c if c in "\n\t" or ord(c) >= 32 else " " for c in value).replace("\x7f", " ")


def _identifier(value: Any, field: str) -> str:
    result = _string(value, field, required=True)
    if not SAFE_ID.fullmatch(result) or result in {".", ".."}:
        raise ExplorerError(f"{field} is not a safe identifier")
    return result


def _enum(value: Any, field: str, allowed: set[str]) -> str:
    result = _string(value, field, required=True)
    if result not in allowed:
        raise ExplorerError(f"{field} has an unsupported value")
    return result


def _count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExplorerError(f"{field} must be a non-negative integer")
    if value > 2**63 - 1:
        raise ExplorerError(f"{field} is too large")
    return value


def _number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplorerError(f"{field} must be a number")
    if not (-1e100 < float(value) < 1e100):
        raise ExplorerError(f"{field} is out of range")
    return value


def _list(value: Any, field: str, convert: Callable[[Any, str], Any]) -> list[Any]:
    if not isinstance(value, list):
        raise ExplorerError(f"{field} must be an array")
    if len(value) > MAX_ITEMS:
        raise ExplorerError(f"{field} has too many entries")
    return [convert(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _strings(value: Any, field: str) -> list[str]:
    return _list(value, field, lambda item, item_field: _string(item, item_field, required=True))


def _ids(value: Any, field: str) -> list[str]:
    result = _list(value, field, _identifier)
    if len(result) != len(set(result)):
        raise ExplorerError(f"{field} contains duplicate identifiers")
    return result


def _required(source: dict[str, Any], field: str, keys: set[str]) -> None:
    missing = keys - set(source)
    if missing:
        raise ExplorerError(f"{field} is missing {len(missing)} required field(s)")


def _record(
    value: Any,
    field: str,
    allowed: set[str],
    *,
    required: set[str],
    ids: set[str] = frozenset(),
    strings: set[str] = frozenset(),
    id_lists: set[str] = frozenset(),
    string_lists: set[str] = frozenset(),
    enums: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    source = _object(value, field, allowed)
    _required(source, field, required)
    enums = enums or {}
    result: dict[str, Any] = {}
    for key, item in source.items():
        item_field = f"{field}.{key}"
        if key in ids:
            result[key] = _identifier(item, item_field)
        elif key in id_lists:
            result[key] = _ids(item, item_field)
        elif key in string_lists:
            result[key] = _strings(item, item_field)
        elif key in enums:
            result[key] = _enum(item, item_field, enums[key])
        else:
            result[key] = _string(item, item_field, required=key in required or key in strings)
    return result


def _safe_source_url(value: Any, field: str) -> str:
    result = _string(value, field, required=True)
    parsed = urlsplit(result)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ExplorerError(f"{field} must be an http or https URL")
    if parsed.username is not None or parsed.password is not None:
        raise ExplorerError(f"{field} must not contain credentials")
    return result


def _safe_relative_link(value: Any, field: str) -> str:
    result = _string(value, field)
    if not result:
        return ""
    if "\\" in result or result.startswith(("/", "//")) or ":" in result.split("/", 1)[0]:
        raise ExplorerError(f"{field} must be a safe relative link")
    path = PurePosixPath(result.split("#", 1)[0].split("?", 1)[0])
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ExplorerError(f"{field} must be a safe relative link")
    return result


def _unique_ids(items: list[dict[str, Any]], field: str) -> set[str]:
    values = [item["id"] for item in items]
    if len(values) != len(set(values)):
        raise ExplorerError(f"{field} contains duplicate ids")
    return set(values)


def _check_refs(values: list[str], known: set[str], field: str) -> None:
    unknown = set(values) - known
    if unknown:
        raise ExplorerError(f"{field} contains {len(unknown)} unknown reference(s)")


def validate_data(payload: Any, expected_run_id: str | None = None) -> dict[str, Any]:
    source = _object(payload, "research", TOP_FIELDS)
    _required(source, "research", {"schema_version", "report", "executive_summary", "findings", "sources"})
    if source["schema_version"] != 1:
        raise ExplorerError("schema_version must be 1")

    report = _record(
        source["report"], "report", REPORT_FIELDS,
        required={"run_id", "title", "topic", "status", "scope", "methodology", "started_at", "completed_at"},
        ids={"run_id"},
        enums={"status": REPORT_STATES},
    )
    if expected_run_id is not None and report["run_id"] != expected_run_id:
        raise ExplorerError("report.run_id does not match the expected run ID")

    findings = _list(source["findings"], "findings", lambda value, field: _record(
        value, field, FINDING_FIELDS,
        required={"id", "title", "summary", "confidence", "categories", "source_ids", "contradiction_ids", "limitations", "detail"},
        ids={"id"}, id_lists={"source_ids", "contradiction_ids"}, string_lists={"categories"},
        enums={"confidence": CONFIDENCE},
    ))
    sources = _list(source["sources"], "sources", lambda value, field: _record(
        value, field, SOURCE_FIELDS,
        required={"id", "title", "publisher", "publication_date", "event_date", "retrieved_at", "url", "source_type", "quality", "finding_ids", "note"},
        ids={"id"}, id_lists={"finding_ids"}, enums={"source_type": SOURCE_TYPES, "quality": QUALITY},
    ))
    for index, item in enumerate(sources):
        item["url"] = _safe_source_url(item["url"], f"sources[{index}].url")

    themes = _list(source.get("themes", []), "themes", lambda value, field: _record(
        value, field, THEME_FIELDS, required=THEME_FIELDS, ids={"id"}, id_lists={"finding_ids"},
    ))
    lanes = _list(source.get("lanes", []), "lanes", lambda value, field: _record(
        value, field, LANE_FIELDS, required=LANE_FIELDS, ids={"id"}, enums={"status": LANE_STATES},
    ))
    contradictions = _list(source.get("contradictions", []), "contradictions", lambda value, field: _record(
        value, field, CONTRADICTION_FIELDS, required=CONTRADICTION_FIELDS, ids={"id"},
        id_lists={"finding_ids", "source_ids"}, enums={"status": CONTRADICTION_STATES},
    ))
    questions = _list(source.get("questions", []), "questions", lambda value, field: _record(
        value, field, QUESTION_FIELDS, required=QUESTION_FIELDS, ids={"id"}, id_lists={"finding_ids"},
        enums={"status": QUESTION_STATES},
    ))
    decisions = _list(source.get("decisions", []), "decisions", lambda value, field: _record(
        value, field, DECISION_FIELDS, required=DECISION_FIELDS, ids={"id"}, id_lists={"finding_ids"},
        enums={"status": DECISION_STATES},
    ))
    recommendations = _list(source.get("recommendations", []), "recommendations", lambda value, field: _record(
        value, field, RECOMMENDATION_FIELDS, required=RECOMMENDATION_FIELDS, ids={"id"},
        id_lists={"finding_ids"}, enums={"priority": PRIORITIES},
    ))

    artifacts = _list(source.get("artifacts", []), "artifacts", lambda value, field: _artifact(value, field))
    tables = _list(source.get("tables", []), "tables", _table)
    timelines = _list(source.get("timelines", []), "timelines", _timeline)
    series = _list(source.get("series", []), "series", _series)

    finding_ids = _unique_ids(findings, "findings")
    source_ids = _unique_ids(sources, "sources")
    contradiction_ids = _unique_ids(contradictions, "contradictions")
    for name, items in (
        ("themes", themes), ("lanes", lanes), ("questions", questions),
        ("decisions", decisions), ("recommendations", recommendations),
        ("artifacts", artifacts), ("tables", tables), ("timelines", timelines),
        ("series", series),
    ):
        _unique_ids(items, name)
    for index, item in enumerate(findings):
        _check_refs(item["source_ids"], source_ids, f"findings[{index}].source_ids")
        _check_refs(item["contradiction_ids"], contradiction_ids, f"findings[{index}].contradiction_ids")
    for collection_name, items in (
        ("themes", themes), ("questions", questions), ("decisions", decisions),
        ("recommendations", recommendations),
    ):
        for index, item in enumerate(items):
            _check_refs(item["finding_ids"], finding_ids, f"{collection_name}[{index}].finding_ids")
    for index, item in enumerate(sources):
        _check_refs(item["finding_ids"], finding_ids, f"sources[{index}].finding_ids")
    for index, item in enumerate(contradictions):
        _check_refs(item["finding_ids"], finding_ids, f"contradictions[{index}].finding_ids")
        _check_refs(item["source_ids"], source_ids, f"contradictions[{index}].source_ids")
    for name, items in (("timelines", timelines),):
        for index, item in enumerate(items):
            for event_index, event in enumerate(item["events"]):
                _check_refs(event["finding_ids"], finding_ids, f"{name}[{index}].events[{event_index}].finding_ids")
                _check_refs(event["source_ids"], source_ids, f"{name}[{index}].events[{event_index}].source_ids")

    result = {
        "schema_version": 1, "report": report,
        "executive_summary": _strings(source["executive_summary"], "executive_summary"),
        "findings": findings, "themes": themes, "sources": sources, "lanes": lanes,
        "contradictions": contradictions, "questions": questions, "decisions": decisions,
        "recommendations": recommendations, "artifacts": artifacts, "tables": tables,
        "timelines": timelines, "series": series,
    }
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_DATA_BYTES:
        raise ExplorerError(f"sanitized research data exceeds {MAX_DATA_BYTES} bytes")
    return result


def _artifact(value: Any, field: str) -> dict[str, Any]:
    source = _object(value, field, ARTIFACT_FIELDS)
    _required(source, field, ARTIFACT_FIELDS)
    result = {
        "id": _identifier(source["id"], f"{field}.id"),
        "name": _string(source["name"], f"{field}.name", required=True),
        "media_type": _string(source["media_type"], f"{field}.media_type", required=True),
        "size_bytes": _count(source["size_bytes"], f"{field}.size_bytes"),
        "sha256": _string(source["sha256"], f"{field}.sha256"),
        "role": _string(source["role"], f"{field}.role", required=True),
        "relative_link": _safe_relative_link(source["relative_link"], f"{field}.relative_link"),
    }
    if result["sha256"] and not SHA256.fullmatch(result["sha256"]):
        raise ExplorerError(f"{field}.sha256 must be a lowercase SHA-256 digest")
    return result


def _table(value: Any, field: str) -> dict[str, Any]:
    source = _object(value, field, TABLE_FIELDS)
    _required(source, field, TABLE_FIELDS)
    columns = _strings(source["columns"], f"{field}.columns")
    rows = _list(source["rows"], f"{field}.rows", lambda row, row_field: _strings(row, row_field))
    if any(len(row) != len(columns) for row in rows):
        raise ExplorerError(f"{field}.rows must match the column count")
    return {"id": _identifier(source["id"], f"{field}.id"), "title": _string(source["title"], f"{field}.title", required=True), "columns": columns, "rows": rows, "note": _string(source["note"], f"{field}.note")}


def _timeline(value: Any, field: str) -> dict[str, Any]:
    source = _object(value, field, TIMELINE_FIELDS)
    _required(source, field, TIMELINE_FIELDS)
    events = _list(source["events"], f"{field}.events", lambda item, item_field: _record(
        item, item_field, TIMELINE_EVENT_FIELDS, required=TIMELINE_EVENT_FIELDS,
        id_lists={"finding_ids", "source_ids"},
    ))
    return {"id": _identifier(source["id"], f"{field}.id"), "title": _string(source["title"], f"{field}.title", required=True), "events": events}


def _series(value: Any, field: str) -> dict[str, Any]:
    source = _object(value, field, SERIES_FIELDS)
    _required(source, field, SERIES_FIELDS)
    points = _list(source["points"], f"{field}.points", lambda item, item_field: _series_point(item, item_field))
    return {"id": _identifier(source["id"], f"{field}.id"), "title": _string(source["title"], f"{field}.title", required=True), "unit": _string(source["unit"], f"{field}.unit"), "points": points, "note": _string(source["note"], f"{field}.note")}


def _series_point(value: Any, field: str) -> dict[str, Any]:
    source = _object(value, field, SERIES_POINT_FIELDS)
    _required(source, field, SERIES_POINT_FIELDS)
    return {"label": _string(source["label"], f"{field}.label", required=True), "value": _number(source["value"], f"{field}.value")}


def _read_file(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise ExplorerError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ExplorerError(f"{label} must be a regular non-symlink file")
    if before.st_nlink != 1 or before.st_size > maximum:
        raise ExplorerError(f"{label} is unsafe or too large")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ExplorerError(f"{label} changed while opening")
        data = b""
        while len(data) <= maximum:
            chunk = os.read(descriptor, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > maximum:
            raise ExplorerError(f"{label} is too large")
        return data
    finally:
        os.close(descriptor)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(_read_file(path, "research data", MAX_DATA_BYTES))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExplorerError(f"research data is invalid JSON: {exc}") from exc


def _atomic_write(path: Path, content: bytes, *, force: bool) -> None:
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if target.suffix.casefold() != ".html":
        raise ExplorerError("output filename must end in .html")
    if target.exists() or target.is_symlink():
        metadata = target.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ExplorerError("existing output must be a regular non-symlink file")
        if not force:
            raise ExplorerError("output exists; use --force only for the exact task-owned file")
    descriptor = -1
    temporary = ""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = ""
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _encoded_data(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def _h(value: object) -> str:
    return html.escape(str(value), quote=True)


def _empty(message: str) -> str:
    return f'<p class="empty-record">{_h(message)}</p>'


def _id_links(values: list[str], prefix: str, label: str) -> str:
    if not values:
        return '<span class="muted">None recorded</span>'
    return " ".join(
        f'<a class="evidence-id" href="#{prefix}-{_h(value)}" aria-label="{_h(label)} {_h(value)}">{_h(value)}</a>'
        for value in values
    )


def _render_content(data: dict[str, Any]) -> str:
    report = data["report"]
    summary = "".join(f"<p>{_h(item)}</p>" for item in data["executive_summary"])
    if not summary:
        summary = _empty("No executive summary was included in the accepted packet.")

    findings: list[str] = []
    for item in data["findings"]:
        search = " ".join((item["id"], item["title"], item["summary"], item["detail"], *item["categories"], *item["source_ids"]))
        categories = "|".join(item["categories"])
        category_tags = "".join(f'<span class="tag">{_h(category)}</span>' for category in item["categories"])
        detail = f'<details><summary>Read the supporting detail</summary><p>{_h(item["detail"])}</p></details>' if item["detail"] else ""
        findings.append(
            f'''<article class="finding record" id="finding-{_h(item['id'])}" data-search="{_h(search.casefold())}" data-confidence="{_h(item['confidence'])}" data-categories="{_h(categories)}" data-has-evidence="{'yes' if item['source_ids'] else 'no'}">
              <header><a class="record-id" href="#finding-{_h(item['id'])}">{_h(item['id'])}</a><span class="state state-{_h(item['confidence'].casefold())}">{_h(item['confidence'].title())} confidence</span></header>
              <h3>{_h(item['title'])}</h3><p class="claim">{_h(item['summary'])}</p>
              <div class="tags" aria-label="Finding categories">{category_tags or '<span class="muted">No category</span>'}</div>
              <dl class="record-links"><div><dt>Sources</dt><dd>{_id_links(item['source_ids'], 'source', 'Source')}</dd></div><div><dt>Contradictions</dt><dd>{_id_links(item['contradiction_ids'], 'contradiction', 'Contradiction')}</dd></div></dl>
              <p class="limitation"><strong>Limit:</strong> {_h(item['limitations'])}</p>{detail}
            </article>'''
        )

    themes = "".join(
        f'''<article class="relationship record" id="theme-{_h(item['id'])}"><header><span class="record-id">{_h(item['id'])}</span></header><h3>{_h(item['name'])}</h3><p>{_h(item['summary'])}</p><p><strong>Findings:</strong> {_id_links(item['finding_ids'], 'finding', 'Finding')}</p></article>'''
        for item in data["themes"]
    ) or _empty("No themes were registered in this accepted packet.")

    contradiction_records = "".join(
        f'''<article class="record contradiction" id="contradiction-{_h(item['id'])}"><header><a class="record-id" href="#contradiction-{_h(item['id'])}">{_h(item['id'])}</a><span class="state state-open">{_h(item['status'].title())}</span></header><h3>{_h(item['title'])}</h3><p>{_h(item['summary'])}</p><dl class="record-links"><div><dt>Findings</dt><dd>{_id_links(item['finding_ids'], 'finding', 'Finding')}</dd></div><div><dt>Sources</dt><dd>{_id_links(item['source_ids'], 'source', 'Source')}</dd></div></dl></article>'''
        for item in data["contradictions"]
    )
    question_records = "".join(
        f'''<article class="record question" id="question-{_h(item['id'])}"><header><span class="record-id">{_h(item['id'])}</span><span class="state state-{_h(item['status'].casefold())}">{_h(item['status'].title())}</span></header><h3>{_h(item['question'])}</h3><p>{_h(item['detail'])}</p><p><strong>Related findings:</strong> {_id_links(item['finding_ids'], 'finding', 'Finding')}</p></article>'''
        for item in data["questions"]
    )
    unresolved = contradiction_records + question_records or _empty("No contradictions or unresolved questions were recorded.")

    decisions = "".join(
        f'''<article class="record compact-record" id="decision-{_h(item['id'])}"><header><span class="record-id">{_h(item['id'])}</span><span class="state state-{_h(item['status'].casefold())}">{_h(item['status'].title())}</span></header><h3>{_h(item['title'])}</h3><p>{_h(item['rationale'])}</p><p><strong>Findings:</strong> {_id_links(item['finding_ids'], 'finding', 'Finding')}</p></article>'''
        for item in data["decisions"]
    ) or _empty("No decisions were registered.")
    recommendations = "".join(
        f'''<article class="record compact-record" id="recommendation-{_h(item['id'])}"><header><span class="record-id">{_h(item['id'])}</span><span class="state state-{_h(item['priority'].casefold())}">{_h(item['priority'].title())} priority</span></header><h3>{_h(item['title'])}</h3><p>{_h(item['detail'])}</p><p><strong>Findings:</strong> {_id_links(item['finding_ids'], 'finding', 'Finding')}</p></article>'''
        for item in data["recommendations"]
    ) or _empty("No recommendations were registered.")

    lanes = "".join(
        f'''<tr><th scope="row"><span class="record-id">{_h(item['id'])}</span> {_h(item['name'])}</th><td>{_h(item['owner'])}</td><td><span class="state state-{_h(item['status'].casefold())}">{_h(item['status'].replace('_', ' ').title())}</span></td><td>{_h(item['contribution'])}</td></tr>'''
        for item in data["lanes"]
    ) or '<tr><td colspan="4">No lane contributions were included.</td></tr>'

    sources: list[str] = []
    for item in data["sources"]:
        search = " ".join((item["id"], item["title"], item["publisher"], item["note"], *item["finding_ids"]))
        sources.append(
            f'''<article class="source record" id="source-{_h(item['id'])}" data-search="{_h(search.casefold())}" data-type="{_h(item['source_type'])}" data-quality="{_h(item['quality'])}" data-title="{_h(item['title'].casefold())}" data-date="{_h(item['publication_date'])}">
              <header><a class="record-id" href="#source-{_h(item['id'])}">{_h(item['id'])}</a><span class="state state-{_h(item['quality'].casefold())}">{_h(item['quality'].title())} quality</span></header>
              <h3><a href="{_h(item['url'])}" rel="noopener noreferrer" referrerpolicy="no-referrer">{_h(item['title'])}</a></h3>
              <p>{_h(item['publisher'])} · {_h(item['source_type'].title())}</p>
              <dl><div><dt>Published</dt><dd>{_h(item['publication_date']) or 'Not established'}</dd></div><div><dt>Event date</dt><dd>{_h(item['event_date']) or 'Not established'}</dd></div><div><dt>Retrieved</dt><dd>{_h(item['retrieved_at'])}</dd></div></dl>
              <p>{_h(item['note'])}</p><p><strong>Supports:</strong> {_id_links(item['finding_ids'], 'finding', 'Finding')}</p>
            </article>'''
        )

    artifacts = "".join(
        f'''<li class="artifact record" id="artifact-{_h(item['id'])}"><div><span class="record-id">{_h(item['id'])}</span><h3>{_h(item['name'])}</h3><p>{_h(item['role'])}</p></div><dl><div><dt>Type</dt><dd>{_h(item['media_type'])}</dd></div><div><dt>Size</dt><dd>{_h(item['size_bytes'])} bytes</dd></div><div><dt>SHA-256</dt><dd><code>{_h(item['sha256']) or 'Not supplied'}</code></dd></div></dl>{f'<a class="artifact-link" href="{_h(item["relative_link"])}">Open artifact</a>' if item['relative_link'] else '<span class="muted">Listed for provenance; no relative file link was provided.</span>'}</li>'''
        for item in data["artifacts"]
    ) or '<li class="empty-record">No accepted artifacts were listed.</li>'

    tables = "".join(_render_table(item) for item in data["tables"])
    timelines = "".join(_render_timeline(item) for item in data["timelines"])
    series = "".join(_render_series(item) for item in data["series"])
    comparisons = tables + timelines + series or _empty("No comparison tables, timelines, or series were included.")

    return f'''
      <header class="report-header" id="summary">
        <div><span class="state state-accepted">Accepted research</span><span class="run-id">{_h(report['run_id'])}</span></div>
        <h1>{_h(report['title'])}</h1><p class="topic">{_h(report['topic'])}</p>
        <dl class="report-meta"><div><dt>Status</dt><dd>{_h(report['status'].replace('_', ' ').title())}</dd></div><div><dt>Started</dt><dd>{_h(report['started_at'])}</dd></div><div><dt>Completed</dt><dd>{_h(report['completed_at'])}</dd></div></dl>
        <noscript><p class="noscript-note">Interactive search and filters are unavailable, but the complete accepted research remains below.</p></noscript>
      </header>
      <section class="report-section summary-section" aria-labelledby="summary-heading"><h2 id="summary-heading">Executive summary</h2><div class="reading-copy">{summary}</div><dl class="count-ledger"><div><dt>Findings</dt><dd>{len(data['findings'])}</dd></div><div><dt>Sources</dt><dd>{len(data['sources'])}</dd></div><div><dt>Open contradictions</dt><dd>{len(data['contradictions'])}</dd></div><div><dt>Accepted artifacts</dt><dd>{len(data['artifacts'])}</dd></div></dl></section>
      <section class="report-section" id="findings" aria-labelledby="findings-heading"><div class="section-heading"><h2 id="findings-heading">Key findings</h2><p id="finding-count" aria-live="polite">{len(data['findings'])} findings shown</p></div><div class="record-stack" id="finding-list">{''.join(findings) or _empty('No findings were included in the accepted packet.')}</div></section>
      <section class="report-section" id="themes" aria-labelledby="themes-heading"><h2 id="themes-heading">Themes and relationships</h2><div class="relationship-grid">{themes}</div></section>
      <section class="report-section" id="contradictions" aria-labelledby="contradictions-heading"><h2 id="contradictions-heading">Contradictions and unresolved questions</h2><div class="record-stack">{unresolved}</div></section>
      <section class="report-section" id="decisions" aria-labelledby="decisions-heading"><h2 id="decisions-heading">Decisions and next steps</h2><div class="split-ledger"><div><h3>Recorded decisions</h3>{decisions}</div><div><h3>Recommendations</h3>{recommendations}</div></div></section>
      <section class="report-section" id="methods" aria-labelledby="methods-heading"><h2 id="methods-heading">Method and lane contributions</h2><div class="reading-copy"><h3>Scope</h3><p>{_h(report['scope'])}</p><h3>Method</h3><p>{_h(report['methodology'])}</p></div><div class="table-wrap"><table><caption>Accepted lane contributions</caption><thead><tr><th>Lane</th><th>Owner</th><th>Status</th><th>Contribution</th></tr></thead><tbody>{lanes}</tbody></table></div></section>
      <section class="report-section" id="sources" aria-labelledby="sources-heading"><div class="section-heading"><h2 id="sources-heading">Sources</h2><p id="source-count" aria-live="polite">{len(data['sources'])} sources shown</p></div><div class="source-list" id="source-list">{''.join(sources) or _empty('No sources were included in the accepted packet.')}</div></section>
      <section class="report-section" id="comparisons" aria-labelledby="comparisons-heading"><h2 id="comparisons-heading">Comparisons and timelines</h2>{comparisons}</section>
      <section class="report-section" id="artifacts" aria-labelledby="artifacts-heading"><h2 id="artifacts-heading">Artifacts</h2><ol class="artifact-list">{artifacts}</ol></section>
      <footer class="provenance" id="provenance"><h2>Provenance</h2><dl><div><dt>Run</dt><dd>{_h(report['run_id'])}</dd></div><div><dt>Accepted status</dt><dd>{_h(report['status'].replace('_', ' ').title())}</dd></div><div><dt>Completed</dt><dd>{_h(report['completed_at'])}</dd></div></dl><p>Portable accepted record. Links may leave this file only when you choose to open them.</p></footer>
    '''


def _render_table(item: dict[str, Any]) -> str:
    headers = "".join(f"<th scope=\"col\">{_h(value)}</th>" for value in item["columns"])
    rows = "".join("<tr>" + "".join(f"<td>{_h(value)}</td>" for value in row) + "</tr>" for row in item["rows"])
    return f'<figure class="data-figure" id="table-{_h(item["id"])}"><figcaption><span class="record-id">{_h(item["id"])}</span> {_h(item["title"])}</figcaption><div class="table-wrap"><table><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div><p>{_h(item["note"])}</p></figure>'


def _render_timeline(item: dict[str, Any]) -> str:
    events = "".join(f'<li><time>{_h(event["date"])}</time><div><h3>{_h(event["title"])}</h3><p>{_h(event["detail"])}</p><p>{_id_links(event["finding_ids"], "finding", "Finding")} {_id_links(event["source_ids"], "source", "Source")}</p></div></li>' for event in item["events"])
    return f'<figure class="data-figure" id="timeline-{_h(item["id"])}"><figcaption><span class="record-id">{_h(item["id"])}</span> {_h(item["title"])}</figcaption><ol class="timeline">{events}</ol></figure>'


def _render_series(item: dict[str, Any]) -> str:
    maximum = max((abs(float(point["value"])) for point in item["points"]), default=0.0)
    bars = "".join(f'<li><span>{_h(point["label"])}</span><span class="series-track"><span style="width:{(abs(float(point["value"])) / maximum * 100) if maximum else 0:.2f}%"></span></span><strong>{_h(point["value"])} {_h(item["unit"])}</strong></li>' for point in item["points"])
    return f'<figure class="data-figure" id="series-{_h(item["id"])}"><figcaption><span class="record-id">{_h(item["id"])}</span> {_h(item["title"])}</figcaption><ol class="series">{bars}</ol><p>{_h(item["note"])}</p></figure>'


def _extract_data(html: str) -> dict[str, Any]:
    match = re.search(r'<script id="research-data" type="application/json">(.*?)</script>', html, re.S)
    if match is None:
        raise ExplorerError("HTML lacks the embedded research-data block")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ExplorerError("embedded research data is invalid") from exc


def command_build(args: argparse.Namespace) -> int:
    data = validate_data(_load_json(Path(args.data).expanduser()))
    template = _read_file(Path(args.template).expanduser(), "HTML template", MAX_TEMPLATE_BYTES).decode("utf-8")
    if template.count(DATA_MARKER) != 1 or template.count(CONTENT_MARKER) != 1 or SHELL_MARKER not in template:
        raise ExplorerError("HTML template has an invalid explorer marker")
    document = template.replace(CONTENT_MARKER, _render_content(data))
    document = document.replace(DATA_MARKER, _encoded_data(data))
    encoded = document.encode("utf-8")
    if len(encoded) > MAX_HTML_BYTES:
        raise ExplorerError("generated HTML is too large")
    output = Path(args.output).expanduser()
    _atomic_write(output, encoded, force=args.force)
    digest = hashlib.sha256(encoded).hexdigest()
    print(json.dumps({"output": str(output.resolve()), "bytes": len(encoded), "sha256": digest, "run_id": data["report"]["run_id"]}, sort_keys=True))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    path = Path(args.html).expanduser()
    raw = _read_file(path, "research explorer", MAX_HTML_BYTES)
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExplorerError("research explorer is not UTF-8") from exc
    if SHELL_MARKER not in html or DATA_MARKER in html:
        raise ExplorerError("research explorer shell is incomplete")
    if re.search(r'<(?:script|link|img)[^>]+(?:src|href)=["\'](?:https?:)?//', html, re.I):
        raise ExplorerError("research explorer contains a remote asset")
    if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(", html):
        raise ExplorerError("research explorer contains network request code")
    data = validate_data(_extract_data(html), args.expected_run_id)
    print(json.dumps({"html": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "run_id": data["report"]["run_id"], "findings": len(data["findings"]), "sources": len(data["sources"])}, sort_keys=True))
    return 0


def parser() -> SafeArgumentParser:
    result = SafeArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build one self-contained explorer")
    build.add_argument("--data", required=True, help="accepted research JSON")
    build.add_argument("--template", required=True, help="explorer HTML template")
    build.add_argument("--output", required=True, help="exact .html output path")
    build.add_argument("--force", action="store_true", help="replace the exact task-owned output")
    build.set_defaults(handler=command_build)
    verify = commands.add_parser("verify", help="verify one generated explorer")
    verify.add_argument("--html", required=True, help="generated explorer path")
    verify.add_argument("--expected-run-id", required=True, help="expected run ID")
    verify.set_defaults(handler=command_verify)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ExplorerError, OSError) as exc:
        print(f"research explorer error: {_safe_text(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
