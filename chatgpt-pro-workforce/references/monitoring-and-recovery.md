# Monitoring and artifact recovery

## Contents

- [Patient monitoring](#patient-monitoring-policy)
- [State classification](#state-classification)
- [User-facing progress](#user-facing-progress-reporting)
- [Pause, limits, and resume](#pause-limits-and-resume)
- [Control-fault diagnostic](#control-fault-diagnostic)
- [Desktop control-action record](#desktop-control-action-record)
- [Artifact recovery](#artifact-recovery-order)
- [Native recovery](#native-recovery-procedure)
- [Base64 fallback](#base64-fallback)
- [Recovery invariants](#recovery-invariants)

## Patient monitoring policy

Record before submission:

- run, iteration, and lane IDs;
- conversation URL and safe tab/window identity;
- prompt path and hash;
- submission timestamp;
- expected completion marker;
- expected artifacts and filenames;
- current capability route.

Immediately before submission, also reconcile active or unknown Pro
conversations and apply the concurrency gate in
[orchestration and lane design](orchestration.md). The serialized default is
`max_concurrent_pro_workers: 2`. A proposed third-or-later worker stays
suppressed until the exact warning is shown and a valid current-run,
exact-limit acknowledgment is persisted. Never auto-close existing chats; a
changed maximum affects future launches only.

During active generation:

- use non-disruptive inspection;
- check at bounded intervals, normally 45-90 seconds;
- treat 30-60+ minute runtimes as plausible for difficult work;
- use output growth, timestamps, active-generation controls, and page state as
  evidence;
- do not use `Answer now`, stop, reload, duplicate submission, or navigation
  while progress remains healthy;
- do not promise infinite unattended execution; maintain resumable state.

## User-facing progress reporting

Read [progress reporting and run controls](progress-and-controls.md). Maintain
one aggregate run-state record and emit a compact card using
`assets/progress-card-template.md` according to the selected cadence.

Progress cards are separate from the 45–90 second internal observation loop.
They must use registered ratios, include an as-of time and freshness, state the
next safe action, and show the exact `tell me more` invocation. Do not interrupt
healthy generation to make a bar move or send repetitive unchanged cards.

When the optional dashboard is configured, atomically refresh its sanitized
snapshot after the invocation readiness gate and every material state change.
Show its link only after a current loopback health check. Dashboard polling is
not a monitoring observation and never advances a worker state by itself.

## Pause, limits, and resume

On `pause`, stop new submissions and control actions, checkpoint durable state,
and preserve active-worker evidence. Use `PAUSING` while a healthy worker may
still be generating; do not routinely press stop. State that monitoring does
not continue in the background after the active turn ends.

For a visible provider usage/capacity limit, use `LIMIT_PAUSED`, preserve only
safe visible evidence, and record a reset time only when actually shown. Never
bypass a limit, switch accounts, guess a reset time, spam retry, or duplicate a
prompt.

On resume, re-read durable run/lane/handoff state, re-preflight volatile
capabilities, re-identify conversations, reconcile returned artifacts and
unknown outcomes, recompute registered denominators, and suppress duplicate
prompt hashes before returning to `ACTIVE`.

Prerequisite setup is not a worker-monitoring recovery action. Pause new
submissions and control actions before an approved setup change, persist the
setup ID/packet/status, and do not interrupt a healthy worker merely to perform
it. After the change or manual OS consent step, run the complete read-only
preflight and reconcile active/unknown worker outcomes before resuming. Setup
command success alone never changes the route to verified.

## Control-fault diagnostic

Enter `FAULT_DIAGNOSTIC` on controller loss/timeout, missing intended tab or
composer, stale/blank/wrong-target capture, unexpected upload/download-route
failure, focus/target mismatch, adapter error, or repeated UI failure. Do not
enter it merely because healthy generation is slow or a transient banner is
present while output continues.

1. Freeze new submissions, uploads, downloads, and desktop input.
2. Persist the lane, prompt hash, intended conversation, artifact inventory,
   prior postconditions, and any action whose outcome is unknown.
3. Recheck the browser chain in order: exact controller connection, intended
   tab/conversation identity, semantic page/composer state, screenshot
   freshness/geometry, upload route, and download route.
4. Recheck desktop layers only when the failed action truly requires them:
   exact adapter exposure, target window identity, accessibility tree,
   independent focus proof, screenshot/portal state, and manual alternative.
5. Attempt at most one bounded non-destructive repair based on new evidence:
   reconnect the registered interface, re-identify/rebind the intended target,
   refresh a stale semantic handle, reacquire verified focus, or move to an
   already-authorized safer route.
6. Re-run the complete preflight whenever capability state or route changes.
7. Reconcile the expected postcondition and duplicate prompt/artifact state
   before any input. Never repeat an `OUTCOME_UNKNOWN` action.
8. If resolution needs a new install, permission, daemon, extension, security
   setting, or broader target, prepare the exact prerequisite packet and ask the
   user. Do not self-authorize it.

Record diagnostic ID, trigger, affected capabilities, evidence before/after,
repair attempted, repair count, capability delta, final route, and disposition.
After the one-repair ceiling, use a verified manual/reduced route or report the
blocker; do not loop reconnects or blind retries.

## State classification

### `RUNNING_HEALTHY`

Generation control is active or output/progress changes over time. Wait and
record observations.

### `RUNNING_WITH_TRANSIENT_ERROR`

An error banner is visible, but generation remains active or output continues
to grow. Do not interrupt. Observe whether progress continues.

### `SLOW_NO_FAILURE_EVIDENCE`

No recent visible growth, but generation remains active and no terminal error
exists. Extend observation and compare multiple timestamps.

### `STALLED`

Generation appears active but no progress occurs across repeated checks and the
UI provides no healthy signal. Preserve evidence, attempt a non-destructive
reconnect or status check, and avoid duplicate submission.

### `BROWSER_DISCONNECTED`

The controller lost the browser, tab, or window. Reconnect and re-identify the
conversation before any input. Do not assume the run stopped.

### `TERMINAL_PARTIAL_ARTIFACT_RETURN`

The response stopped and some expected analysis or artifacts exist, but the
completion marker or required members are missing. Preserve all returned
material and use a continuation or diagnostic prompt.

### `TERMINAL_INCOMPLETE`

The response stopped with no usable required output. Preserve evidence and
choose a changed recovery tactic or fresh conversation.

Worker generation states above are separate from capability states and desktop
action outcomes. Run states such as `PAUSED` and `LIMIT_PAUSED` are also
separate; do not put them in the worker-generation field.

## Desktop control-action record

Before a non-browser desktop action, persist one resumable record containing:

- stable action and lane IDs plus timestamp;
- intended application, window, and semantic control identity;
- selected route and exact adapter/method;
- current authority and browser-gap evidence;
- precondition and expected postcondition;
- focus requirement and immediate pre-action evidence;
- attempt number (`1` or `2` maximum);
- one action outcome: `NOT_ATTEMPTED`, `VERIFIED_SUCCEEDED`,
  `VERIFIED_FAILED`, `OUTCOME_UNKNOWN`, `MANUAL_HANDOFF`, or `BLOCKED`;
- target-scoped screenshot hash or semantic evidence when retained safely;
- exact error, next safe route, or bounded manual instruction.

Allow the initial action plus at most one recovery attempt using materially
changed evidence, target method, or route. Never repeat input when the prior
outcome is `OUTCOME_UNKNOWN`. After disconnect, timeout, or missing response,
re-identify the target and test the expected postcondition before deciding
whether the action remains necessary. Reconcile duplicate submissions and
download/file presence before retrying an unknown send or recovery action.
After the ceiling, use manual handoff or stop.

## Artifact recovery order

1. native attachment download;
2. browser-accessible download URL;
3. authorized desktop handling of a native dialog;
4. exact ZIP packet;
5. bounded Base64 transport.

Do not paste large Base64 when a native file is recoverable.

Read [artifact storage and cleanup](artifact-storage-and-cleanup.md). Recover
only into the configured dedicated run directory and register every owned file
before any later cleanup decision.

## Native recovery procedure

For every recovered object:

1. save exact bytes into a quarantine/raw-return directory;
2. calculate SHA-256 and byte count;
3. record original display name and actual recovered filename;
4. identify MIME/type by inspection, not extension alone;
5. for archives, list members without extraction, reject traversal or unexpected
   members, then run an integrity test;
6. copy accepted bytes into a separate candidate directory;
7. never overwrite the raw return;
8. record the path and hash in lane state.

## Base64 fallback

Use only when native recovery paths have been exhausted and the packet size is
bounded.

Require:

- exact total encoded character count;
- expected decoded byte count and SHA-256;
- numbered chunks;
- exact per-chunk lengths;
- no prose inside chunk payloads;
- deterministic local reconstruction;
- decoded hash verification;
- a recovery log.

A mismatched length or hash means recovery failed. Do not guess missing bytes.

## Recovery invariants

- Raw returned bytes are immutable.
- Repaired derivatives have new filenames or lineage IDs.
- Accepted artifacts are hash-bound to their validation evidence.
- Downloads from browser workers remain untrusted until inspected.
- Cleanup targets come only from the exact hash-bound run manifest; never from
  a broad filesystem search, glob, directory target, or inferred ownership.
- Preserve the previous valid dashboard snapshot if a new snapshot fails
  validation or atomic replacement; mark it stale rather than corrupting it.
- Lost bytes, timestamps, validators, or unavailable sources are marked
  `NOT_RECOVERABLE`, `NOT_AVAILABLE`, or `NOT_ESTABLISHED`.
