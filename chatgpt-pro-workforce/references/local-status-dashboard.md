# Local status dashboard

Use this reference when the user enables, opens, refreshes, troubleshoots, or
stops the optional localhost dashboard. The dashboard is a read-only projection
of durable run evidence. Chat remains the control plane.

Use an explicitly discovered Python 3.10-or-newer interpreter path for the
bundled helper; never assume `python3.12` or another minor-version name. Record
the actual path and version in durable capability evidence when the dashboard
is enabled.

## Contents

- [First-use choice](#first-use-choice)
- [Lifecycle](#lifecycle)
- [Public status schema](#public-status-schema)
- [Safe launch and link](#safe-launch-and-link)
- [Refresh semantics](#refresh-semantics)
- [Controls reference](#controls-reference)
- [Security boundary](#security-boundary)
- [Failure and recovery](#failure-and-recovery)

## First-use choice

Store one profile policy:

- `DISABLED` — do not create dashboard files or start a server;
- `ON_DEMAND` — recommended; prepare or start it only when the user asks for a
  dashboard during a run;
- `ENABLED` — maintain a sanitized snapshot for each active run and start or
  reconnect its loopback server when the current runtime permits.

Ask for or recommend a dedicated dashboard root. On Linux, an appropriate
example is a `chatgpt-pro-workforce/dashboard` subdirectory under the user's
local state directory. Do not use the home directory itself, a project root,
Downloads, Desktop, a vault, or an artifact/download root. Record the policy,
dedicated root, and whether automatic current-run startup is authorized in the
[workforce profile](../assets/workforce-profile-template.md).

`ENABLED` authorizes only the local files and managed loopback process described
here. It does not authorize firewall, service, login-startup, browser-security,
or system configuration changes.

## Lifecycle

On every skill invocation:

1. perform the invocation readiness gate;
2. load the matching durable run state without exposing unrelated runs;
3. if dashboard policy is not `DISABLED`, build a fresh public snapshot from
   the allowlisted fields in
   [status data template](../assets/status-data-template.json);
4. atomically replace that run's `status.json` with
   [status dashboard helper](../scripts/status_dashboard.py);
5. if the policy or user intent calls for a link, verify the exact loopback
   server, requested run page, and sanitized snapshot with the helper's
   `verify` command;
6. when the verified Chrome/browser route is available, open the exact run URL
   and semantically confirm the expected run ID, title, freshness, and visible
   connection state before presenting it as browser-verified;
7. show the URL only after local verification succeeds; otherwise show the text
   detailed-status intent and record the dashboard as unavailable or stale.

Also refresh the snapshot after a material transition while the active Codex
turn continues: lane submission/terminal change, artifact recovery, gate result,
scope change, pause/resume/limit, readiness delta, blocker, or user decision.
Do not write an unchanged snapshot merely to create the appearance of activity.

## Public status schema

The JSON snapshot contains only these top-level keys:

```text
schema_version run progress lanes readiness artifacts gates decisions
storage notes alerts
```

Use the exact field sets demonstrated by the template. Reject unknown keys,
oversized records, negative/non-finite counts, a mismatched run ID, and invalid
state values. Redact rather than abbreviate sensitive content. Safe summaries
may identify a lane, state, checked artifact name/hash, interface name, decision,
and next action. They must not include:

- prompt bodies or raw worker responses;
- cookies, tokens, credentials, account identifiers, or browser-profile data;
- unrelated tabs, windows, history, files, or applications;
- private artifact contents or source passages;
- shell transcripts, environment dumps, or secrets-bearing errors.

Use these exact state vocabularies; do not pass free-form state strings:

```text
run.status: DRAFT READY ACTIVE PAUSING PAUSED LIMIT_PAUSED RESUMING PARTIAL BLOCKED ACCEPTED REJECTED STOPPED SUPERSEDED
run.allocation_profile: PRO_HEAVY BALANCED CODEX_HEAVY LOCAL_ONLY
run.codex_usage_band: LOWEST MODERATE HIGH CODEX_ONLY
run.route: UNKNOWN FULL_BROWSER_AND_DESKTOP BROWSER_ONLY BROWSER_WITH_MANUAL_DESKTOP MANUAL_BROWSER_HANDOFF LOCAL_CODEX_ONLY BLOCKED
run.freshness: CURRENT STALE UNKNOWN
progress.state: OPEN ACTIVE COMPLETE BLOCKED UNKNOWN
readiness.state: AVAILABLE_VERIFIED AVAILABLE_UNTESTED NOT_AVAILABLE DISABLED NOT_AUTHORIZED MISCONFIGURED DEGRADED UNKNOWN
artifact.state: EXPECTED RECOVERED RAW CANDIDATE ACCEPTED REJECTED DUPLICATE TEMPORARY NOT_RECOVERABLE UNKNOWN
gate.state: PENDING NOT_RUN PASS FAIL BLOCKED
decision.state: PENDING APPROVED DEFERRED REJECTED NOT_REQUIRED MANUAL_ACTION_REQUIRED
storage.state / notes.state: UNSET READY HEALTHY DEGRADED BLOCKED UNKNOWN
alert.level: info warning error
```

Lane state uses the canonical monitoring and acceptance vocabulary from
[monitoring and recovery](monitoring-and-recovery.md), including healthy,
slow, transient-error, stalled, disconnected, partial-return, mechanical,
semantic, accepted, rejected, blocked, and superseded states. The helper
enforces the exact tokens.

The helper validates structure and these vocabularies; it cannot infer whether
an otherwise allowed summary contains a secret. Before writing a snapshot,
build it from an allowlist rather than raw serialization and run a synthetic
secret-canary check against that builder. Assert that fake cookie, bearer-token,
password, browser-profile, private-path, and prompt-body canaries are absent
from the encoded output. Never put public status JSON on the process command
line.

`codex_usage_band` is qualitative: `LOWEST`, `MODERATE`, `HIGH`, or
`CODEX_ONLY`. Explain that actual Codex usage varies with scope, failures, and
required verification; it is not a quota, billing, or token prediction.

## Safe launch and link

Discover and record the actual Python interpreter path before use. Do not
download dependencies. Use the helper's `--help` for the installed syntax, then
perform the equivalent of:

```text
<python-path> scripts/status_dashboard.py init --root <dedicated-dashboard-root> --run-id <RUN_ID> --template assets/status-dashboard-template.html
<python-path> scripts/status_dashboard.py update --root <dedicated-dashboard-root> --run-id <RUN_ID> --status-file <sanitized-status-json>
<python-path> scripts/status_dashboard.py serve --root <dedicated-dashboard-root> --bind 127.0.0.1 --port <PORT>
<python-path> scripts/status_dashboard.py health --host 127.0.0.1 --port <PORT> --expected-root <dedicated-dashboard-root>
<python-path> scripts/status_dashboard.py verify --host 127.0.0.1 --port <PORT> --expected-root <dedicated-dashboard-root> --run-id <RUN_ID>
```

On Linux, the dedicated root, `runs`, and run directory must be owned by the
current user with mode `0700`; served `index.html` and `status.json` must be
owned by that user, regular non-symlink single-link files with mode `0600`.
The sanitized input file supplied by `--status-file` must also be private
`0600`; prefer standard input when no private staging file is needed. Reject an
existing permissive path with exact remediation rather than silently changing
its permissions. The bundled helper does not claim macOS ACL or Windows DACL
verification; until a platform-specific private-root check is authoritatively
available, use the chat detail view and record the dashboard as unavailable on
those platforms.

Run `serve` in a host-managed execution session when available. Record the
dashboard root, port, managed process/session identity, health time, and last
snapshot time. Never daemonize through a system service or claim the process
will survive the current host/session.

Treat `health` as server-identity diagnosis, not sufficient proof that one run
page works. `verify` must confirm the server identity, exact HTML shell,
requested run ID, status schema, and status hash. After successful `verify`,
put this exact style of line directly under the compact progress card:

```text
Dashboard: http://127.0.0.1:<PORT>/runs/<RUN_ID>/
```

The link is local and read-only. Never show `localhost` when the server is bound
to another interface, and never show a remembered link without a current exact-
run verification. Prefer the literal `127.0.0.1` URL so the binding is clear.
When Chrome/browser control is available, open that URL and confirm the visible
run ID plus connection/freshness banner. Record `browser_visible: VERIFIED` or
the exact limitation. Do not use screenshots alone when semantic page state is
available. Account for any Chrome debugging/automation infobar by measuring the
actual content viewport after navigation rather than assuming the outer window
height.

## Refresh semantics

The page polls its own `status.json` with cache disabled while it is open. The
page may update immediately after a skill invocation or material state change
because the helper replaces the JSON atomically. Polling does not create new
orchestration observations and cannot keep Codex, a worker, or a browser-control
session alive.

Display both:

- `updated_at`: when the durable evidence changed; and
- browser-local fetch time: when the page last loaded the snapshot.

If evidence is older than its declared freshness window, show `STALE`; if time
or source is unavailable, show `UNKNOWN`. Never advance progress from elapsed
time. A new invocation should refresh readiness evidence even when run progress
is unchanged.

## Controls reference

Keep a complete, visually grouped control reference below the detailed status
content and a visible `View controls` anchor near the top of the page. It must
cover guided start, compact and detailed status, pause, resume, continue,
discovered-topic review, allocation and Pro-concurrency changes, dashboard
start/refresh, troubleshoot and stop, explicit run stop, safe uninstall, and help. Describe
the effect and safety boundary of each.

Show each intent as exact selectable text with a `Copy` button. After a valid
snapshot loads, replace only the literal `{RUN_ID}` placeholder with the
server-validated current run ID. Copying may write that text to the local
clipboard after a user click; it must never execute the intent, call a worker,
change durable state, start or stop a process, or send browser/desktop input. If
clipboard access fails, keep the command visible for manual selection and say
so without opening a remote page.

The controls are a detailed equivalent of `$chatgpt-pro-workforce help`, not a
second control plane. Chat remains the only place where an intent is interpreted
and applicable confirmation or authorization gates run.

For concurrency, show the copy-only
`$chatgpt-pro-workforce change concurrency {RUN_ID}` intent, the default maximum
of two, and the full warning that a maximum above two is high risk, is likely to
increase throttling, can leave chats interrupted/closed/disconnected/inaccessible,
and may lose unsaved or unverified work. State that chat requires a current-run,
exact-limit acknowledgment and never auto-closes an existing chat. When the
configured limit, observed count, or acknowledgment affects the run, project it
into a sanitized `warning` alert or decision row so the status page reports it
without adding a command endpoint.

For uninstall, show `$chatgpt-pro-workforce uninstall` as a copy-only intent and
explain that chat will inventory one exact active installation, offer a
recoverable backup, exclude research data and shared control tooling, and ask
for explicit confirmation. Read
[installation lifecycle and safe uninstall](installation-and-uninstall.md);
the page must expose no removal endpoint.

## Security boundary

- Bind only to `127.0.0.1` or `::1`; never `0.0.0.0`, a LAN address, or a
  remotely reachable tunnel.
- Serve only the dedicated dashboard root and deny directory listing, traversal,
  symlink escapes, dotfiles, and unexpected file types.
- Use no CDN, external font, analytics, telemetry, cookie, local-storage, or
  third-party request.
- Use text-safe DOM APIs for status data; never inject JSON through `innerHTML`.
- Keep the surface operationally read-only. Refresh may reload local status and
  a user-clicked Copy button may write visible command text to the local
  clipboard. No page control may execute an intent, pause, resume, submit,
  delete, install, start/stop a process, or send browser/desktop input.
- Do not place raw artifacts, download roots, vaults, source repositories, or
  sensitive reports under the served root.

## Failure and recovery

If update fails, preserve the previous valid snapshot, mark dashboard evidence
stale in durable state, and keep the chat status path available. If `verify` or
browser-visible loading fails, enter `DASHBOARD_FAULT_DIAGNOSTIC`:

1. run local-root `health` to distinguish a missing/unsafe root from a server
   problem;
2. verify the recorded root, port, managed process/session identity, and
   loopback bind; never trust a stale PID by itself;
3. run `verify` and classify exactly one primary fault:
   `SERVER_UNREACHABLE`, `SERVER_IDENTITY_MISMATCH`, `RUN_PAGE_UNAVAILABLE`,
   `RUN_PAGE_INVALID`, `STATUS_SNAPSHOT_UNAVAILABLE`, or
   `STATUS_SNAPSHOT_INVALID`;
4. reconcile whether the recorded process ended before starting another;
5. attempt at most one bounded restart of a skill-owned, identity-matched
   process when the profile/current intent authorizes it. If the recorded port
   is occupied by an unknown process, select a free loopback port and update
   durable dashboard state instead of killing anything;
6. run `verify` again. When Chrome/browser control is available, open the exact
   page and semantically confirm the run ID and connection banner;
7. show the link only on success. Otherwise report the classified fault, the
   attempted repair, and the text fallback
   `$chatgpt-pro-workforce tell me more RUN_ID`.

Do not restart on a browser-only rendering failure until the HTTP and snapshot
checks have established that the local service is healthy. Do not loop: one
diagnostic pass and one bounded restart are the ceiling for the same fault.

Never kill a process from a stale PID alone. Match the managed process identity,
command, root, and port before a stop. A port collision, unsupported host process
lifetime, or unavailable interpreter degrades only the dashboard unless the
requested workflow separately depends on that capability.
