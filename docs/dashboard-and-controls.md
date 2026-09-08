# Dashboard and controls

## Purpose

The optional dashboard is a read-only view of sanitized durable run state. It
sits beside the compact in-chat progress card; it is not another orchestrator
and cannot keep work alive after the active session ends.

The top summary uses exact registered ratios for scope, workers, artifacts,
validation, and acceptance. Unknown denominators remain named states rather
than guessed percentages. Detailed sections show lanes, readiness, artifacts,
decisions, warnings, and the next safe action.

## Safety properties

- Binds to a verified loopback address only.
- Serves a dedicated owner-only directory, never a project, vault, Downloads,
  artifact, or home root.
- Uses restrictive file modes and rejects symlinks, unexpected owners, multiple
  links, permissive roots, traversal, dotfiles, and unsafe Host headers.
- Serves a strict content security policy, frame denial, and no-store headers.
- Reads size-bounded files through descriptor identity checks.
- Polls sanitized JSON and renders with text-safe DOM operations.
- Requires status schema version 2 and a monotonically increasing revision;
  stale or conflicting revisions do not replace the last good view.
- Exposes copy buttons only; there is no pause, resume, delete, uninstall, or
  arbitrary-command endpoint.

Each server start creates a new random instance ID. The dashboard URL is shown
only after the helper matches that ID and verifies the requested run page, run
ID, HTML shell, schema, and snapshot hash. When Chrome control is available,
the skill also opens that URL and checks the visible run identity and connection
banner. A remembered or dead URL is not reused.

## Refresh behavior

The skill refreshes the public snapshot after the invocation readiness gate and
on material state transitions observed during the active turn. The browser page
polls that snapshot while open. Polling does not prove that orchestration is
still running, so freshness and last-observed time remain visible.

The projection strip distinguishes loading, current, reconnecting, stale,
malformed/unsupported data, and an unavailable server. A connection failure
keeps the last-known-good snapshot visible and retries on a bounded 1, 2, 4, 8,
16, then 30 second schedule with small jitter. The diagnostics disclosure shows
last attempt, last success, schema, failure count, and next retry without
exposing host secrets or unrelated browser state.

## Chat controls

The page includes complete explanations and copyable forms for:

```text
$chatgpt-pro-workforce status RUN_ID
$chatgpt-pro-workforce tell me more RUN_ID
$chatgpt-pro-workforce pause RUN_ID
$chatgpt-pro-workforce resume RUN_ID
$chatgpt-pro-workforce continue RUN_ID
$chatgpt-pro-workforce stop RUN_ID
$chatgpt-pro-workforce review discovered topics RUN_ID
$chatgpt-pro-workforce change allocation RUN_ID
$chatgpt-pro-workforce change concurrency RUN_ID FINITE_MAXIMUM
$chatgpt-pro-workforce dashboard RUN_ID
$chatgpt-pro-workforce dashboard troubleshoot RUN_ID
$chatgpt-pro-workforce dashboard stop RUN_ID
$chatgpt-pro-workforce export explorer RUN_ID
$chatgpt-pro-workforce help
$chatgpt-pro-workforce uninstall
```

Pasting one into Codex returns control to the skill's permission and state
checks. The page itself never interprets or executes it.

## Start on demand

Choose `ON_DEMAND` during guided setup, then request the dashboard for a run.
The helper prints a loopback URL and server instance ID, and the skill verifies
both before showing the link. An updated HTML shell can be installed atomically
without changing the run's status or revision. If the page fails,
`dashboard troubleshoot` separates server, instance, root, run-page, shell,
schema, and snapshot faults. It may make one bounded restart of an
identity-matched skill-owned process; it never kills an unknown port owner.
Closing the server removes the live page, but the durable run state remains.

## What it looks like

The live page uses a deep navy working surface with blue for current work,
violet for accepted work, amber for attention, and coral for failure. The layout
keeps run identity, snapshot trust, the next safe action, five separate ratios,
and worker state near the top.

Status labels include their words and borders, so color is never the only cue.
Titles stay compact, corners stay close to square, and identifiers, timestamps,
ratios, and hashes use tabular monospace. The companion completed-research page
uses warm paper and reading typography while keeping the same IDs and state
language.

The Chrome automation or debugging bar can take height away from the content
viewport and change the apparent aspect ratio. Review the measured content
viewport, not just the outer browser window; the dashboard has a reduced-height
layout for that case.

Current examples:

- [Run overview](images/dashboard-overview-v1.2.jpg)
- [Copyable controls](images/dashboard-controls-v1.2.jpg)
