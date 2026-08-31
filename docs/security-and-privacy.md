# Security and privacy model

## Trust boundaries

ChatGPT Pro conversations, browser pages, returned files, local adapters, and
dashboard inputs are untrusted capabilities. They may suggest actions or return
plausible-looking content, but they do not expand scope, grant permission, or
establish correctness.

Codex remains responsible for authorization, targeting, validation, lineage,
integration, and acceptance. A tool being installed or callable is not evidence
that it may be used for the current action.

## Sensitive data

The workflow must not inspect, expose, publish, or place in worker prompts or
dashboard state:

- cookies, authentication tokens, passwords, keys, or browser-profile secrets;
- unrelated browser history, tabs, windows, screenshots, files, or downloads;
- private/customer data beyond the explicitly authorized task;
- credential-bearing logs, hidden metadata, or unredacted local paths;
- raw prompt or artifact content in the sanitized dashboard projection.

Before sending material to a worker, classify it, minimize it, and verify that
the user's authorization covers disclosure to the ordinary ChatGPT account.

## Browser and desktop control

Browser actions identify the intended conversation and composer semantically.
Desktop actions additionally require the intended window, application, process,
and focus to be independently verified. Every input attempt has an action ID,
attempt number, expected semantic postcondition, and observed outcome.

Timeouts and disconnects freeze repeat input until outcome is reconciled. The
workflow does not routinely reload, duplicate submissions, type "answer now,"
or use raw coordinates when a semantic route exists.

## Artifacts and cleanup

Worker returns enter a run-owned incoming area, then immutable raw storage. The
workflow records path, type, size, SHA-256, source conversation/lane, retrieval
time, and validation state. Archive extraction rejects traversal, absolute
paths, ambiguous duplicates, symlinks, and special files.

Cleanup is never a broad Downloads sweep. A candidate must be inside the
configured run-owned root, have an accepted exported copy, match its planned
hash, be unused, and receive the configured confirmation. Hash changes,
symlinks, uncertainty, or unrelated ownership suppress deletion.

## Local dashboard

Only an allowlisted sanitized schema reaches the dashboard. The server is
loopback-only, has no action endpoint, and fails closed when ownership,
permissions, link count, Host header, path, or descriptor identity is unsafe.

See [SECURITY.md](../SECURITY.md) for private vulnerability reporting.
