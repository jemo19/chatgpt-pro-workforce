# Dashboard and controls

## Purpose

The optional dashboard is a polished, read-only view of sanitized durable run
state. It complements the compact in-chat progress card; it is not another
orchestrator and cannot keep work alive after the active session ends.

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
- Exposes copy buttons only; there is no pause, resume, delete, uninstall, or
  arbitrary-command endpoint.

The dashboard URL is displayed only after a current health check. A remembered
or dead URL is omitted.

## Refresh behavior

The skill refreshes the public snapshot after the invocation readiness gate and
on material state transitions observed during the active turn. The browser page
polls that snapshot while open. Polling does not prove that orchestration is
still running, so freshness and last-observed time remain visible.

## Chat controls

The page includes complete explanations and copyable forms for:

```text
$chatgpt-pro-workforce status RUN_ID
$chatgpt-pro-workforce tell me more RUN_ID
$chatgpt-pro-workforce pause RUN_ID
$chatgpt-pro-workforce resume RUN_ID
$chatgpt-pro-workforce change allocation RUN_ID
$chatgpt-pro-workforce change concurrency RUN_ID FINITE_MAXIMUM
$chatgpt-pro-workforce help
$chatgpt-pro-workforce uninstall
```

Pasting one into Codex returns control to the skill's permission and state
checks. The page itself never interprets or executes it.

## Start on demand

Choose `ON_DEMAND` during guided setup, then request the dashboard for a run.
The helper prints a verified loopback URL only after initialization and health
validation. Closing the server or ending its host session removes that live
surface; the durable run state remains the source for a future refresh.
