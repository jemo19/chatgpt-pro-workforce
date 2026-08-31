# Test-run monitoring

## What monitoring can do

During an active Codex session, monitoring can periodically inspect durable run
state and report only material changes. It can also trigger the skill's bounded
fault diagnostic when observed evidence indicates that browser or computer
control may be the cause of a stall.

Monitoring can check:

- run and lane states, active/unknown conversation count, and prompt hashes;
- last observation time, response growth, terminal markers, and transient UI
  errors;
- browser connection, intended ChatGPT tab, composer, and conversation identity;
- desktop adapter health, intended window/focus, screenshot freshness, and the
  last action's semantic postcondition;
- attachment presence, download recovery, raw/candidate/accepted inventories,
  hashes, and partial returns;
- mechanical, semantic, and independent acceptance gates;
- usage-limit state, displayed reset time, pause checkpoint, and next action;
- dashboard health and sanitized snapshot freshness.

Monitoring does not authorize new workers, new permissions, installations,
destructive recovery, private-data disclosure, or a broader target.

## Recommended disposable test

Use public or synthetic information and no consequential external action:

```text
Use $chatgpt-pro-workforce for a disposable test run. Do not use private data or consequential actions. Run the full readiness preflight, guide me through a harmless two-lane research task, enable the on-demand dashboard, show the run ID, and stop at the final acceptance gate so I can inspect the evidence.
```

Keep concurrency at two. Confirm the worker conversations are disposable and
that downloads, if any, use the configured run-owned test directory.

## Ask Codex to monitor

Once the run ID exists:

```text
Monitor RUN_ID during this active session. Use the run state and dashboard snapshot as hints, reconcile them with current browser/control evidence, report material changes at the configured cadence, and stop for my decision before any new permission, installation, destructive action, or broader target.
```

For an immediate read-only snapshot:

```text
$chatgpt-pro-workforce status RUN_ID
$chatgpt-pro-workforce tell me more RUN_ID
```

## Healthy versus faulty states

| State | Evidence | Monitoring response |
|---|---|---|
| Healthy but slow | Worker remains active; response or spinner changes; no terminal failure | Wait patiently and report only at cadence |
| Stalled | No meaningful change across bounded observations and no healthy signal | Freeze new submissions; inspect affected control chain |
| Transient UI/server error | Banner appears while response continues or recovers | Record and observe; do not routinely reload or duplicate |
| Disconnected control | Controller cannot identify the expected tab/window or transport drops | Mark outcome unknown; recheck readiness before input |
| Terminal incomplete | Worker ended without the contracted deliverable | Preserve return; validate partial output; issue bounded correction or fresh lane according to policy |
| Partial artifact return | Response references files that are missing or incomplete | Preserve what exists; verify attachments; use bounded recovery routes |

## Evidence to save for a defect

Save only sanitized evidence:

- skill version/commit and operating system;
- run/lane IDs and timestamps;
- selected route and capability states;
- expected versus observed state transition;
- exact error class and bounded redacted message;
- whether the outcome was verified, failed, or unknown;
- relevant artifact names, sizes, and hashes without private contents;
- whether manual handoff succeeded.

Do not publish conversation URLs, prompts, private artifacts, cookies, tokens,
browser profiles, local usernames, absolute paths, or unrelated screenshots.

## Lifetime boundary

The skill and dashboard do not create a permanent background monitor. Status
updates occur while Codex is actively working or when the user invokes status,
resume, or monitoring again. If the active session ends, durable state enables a
later safe resume; it does not prove that any observer remained running.
