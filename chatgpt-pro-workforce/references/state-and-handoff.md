# State and resumability

Every non-trivial run must survive context compaction, a new Codex turn, browser
reconnection, page reload, worker timeout, partial return, and lanes finishing
at different times.

## Contents

- [State location and lookup](#state-location-and-lookup)
- [Writer ownership and revisions](#writer-ownership-and-revisions)
- [Select a state backend](#select-a-state-backend)
- [Durable state helper](#durable-state-helper)
- [Portable immutable-revision fallback](#portable-immutable-revision-fallback)
- [Capacity reserve and rollover](#capacity-reserve-and-rollover)
- [Aggregate run state](#aggregate-run-state)
- [Lane state](#lane-state)
- [Submission lineage and duplicate suppression](#submission-lineage-and-duplicate-suppression)
- [State transitions](#state-transitions)
- [Integration handoff](#integration-handoff)

## State location and lookup

The installable skill directory contains templates, never live run state. Pick
one durable state root and record it in the workforce profile and run index.
Resolve state in this order:

1. an explicit path in current trusted project/user instructions;
2. the exact state root recorded in a current project handoff or run index;
3. the confirmed research-note root for that project, using a dedicated
   `chatgpt-pro-workforce/` child;
4. the profile's already-confirmed user state root;
5. if none is trustworthy, ask for one path before creating state.

Never choose a run from a broad filesystem search, browser memory, a partial
title match, or the newest timestamp alone. Match the exact run ID. A bounded
project search may look only for the known run-index filename in the current
approved notes/state roots. If two records claim the same run ID, stop
mutation, hash both, and reconcile lineage before selecting either one.

The run index stores only safe run IDs, exact state paths, status, last
checkpoint revision/time, and a short outcome label. Do not put prompt bodies,
worker responses, credentials, or browser-profile data in it.

## Writer ownership and revisions

One Codex session owns aggregate run-state writes at a time. Before any
mutation, load the exact record, compare its recorded `state_revision` and
writer session with the last checkpoint, then claim it with a new safe session
ID. Every committed update increments the revision exactly once and records
the prior revision, writer, time, reason, and resulting file hash.

A different `CLAIMED` writer is a hard no-write gate. Do not decide it is stale
from elapsed time alone. Reconcile through current trusted session/process
evidence or ask the user which session should continue. `CHECKPOINTED` or
`RELEASED` state may be claimed only after re-reading the latest bytes and
checking the expected revision. On context compaction, pause, or handoff,
checkpoint before releasing ownership.

Status/help may read and project this state but never claim ownership or bump a
revision. Resume/continue must claim the record before migration or other
mutation. Use atomic replacement for machine-readable sidecars and preserve
the last accepted bytes if validation fails.

## Select a state backend

Run state is mandatory; this particular helper is not. Select exactly one
backend before claiming a material run:

- On Linux, use the bundled helper only after it successfully opens an explicit
  private state root and returns valid state. A helper error is a closed gate,
  not permission to bypass its checks.
- On macOS, Windows, or Linux where the helper security preflight fails, use the
  portable immutable-revision fallback below. The bundled helper intentionally
  rejects these unverified environments; do not patch around that rejection or
  claim its Linux privacy guarantees.
- If neither backend can verify exclusive ownership, durable revision commit,
  and post-write reread, freeze automated browser/desktop input. Continue
  read-only work or use an explicit manual handoff.

Record `LINUX_HELPER` or `PORTABLE_IMMUTABLE_REVISIONS`, platform, state root,
privacy-verification result, current revision/hash, and writer identity in the
aggregate mirror. Never switch backends within a run. A backend migration must
close or pause the old run and create a linked successor.

## Durable state helper

On Linux, use the bundled [run state helper](../scripts/run_state.py) as
the transactional ownership and browser-send kernel. It complements the
human-readable aggregate and lane notes; it does not replace their scope,
artifact, gate, decision, or handoff fields. Discover an explicit Python
3.10-or-newer interpreter and use one exact private `0700` state root whose
parent already exists:

```text
<python-path> scripts/run_state.py init --root <state-root> --run-id <RUN_ID> --session-id <SESSION_ID>
<python-path> scripts/run_state.py show --root <state-root> --run-id <RUN_ID>
<python-path> scripts/run_state.py history --root <state-root> --run-id <RUN_ID>
```

The helper verifies current-user ownership, exact private modes, no symlink
path components, and single-link `0600` state files. It serializes writers with
a bounded lock wait, uses full-synchronous SQLite transactions, and keeps an
append-only event row for each committed revision. It stores safe identifiers
and prompt hashes only—never prompts, responses, credentials, or browser
secrets. Its ownership, mode, link, and lock claims are Linux-only.

Treat the revision returned by every mutation as the only valid input to the
next mutation. `claim` requires a released `READY` run and the exact expected
revision. `pause` changes `ACTIVE` to `PAUSED` and releases ownership; `resume`
requires that exact paused revision and claims it for the new session. A normal
handoff uses `release`, which changes `ACTIVE` to `READY`. Never edit the
database, reuse a remembered revision, or bypass a conflicting owner.

If a prior Codex session ended without releasing an `ACTIVE` run, normal claim
and resume remain blocked. First establish trusted evidence that the exact
recorded owner is abandoned, then use the explicit compare-and-swap takeover:

```text
<python-path> scripts/run_state.py takeover --root <state-root> --run-id <RUN_ID> --session-id <NEW_SESSION_ID> --expected-revision <REVISION> --expected-owner-session <PRIOR_SESSION_ID> --reason <BOUNDED_REASON> --evidence-ref <SAFE_EVIDENCE_REFERENCE>
```

The expected revision and prior owner must both match. Takeover preserves all
work items and blocks new sends while any `SEND_INTENT`, `OUTCOME_UNKNOWN`, or
unresolved `ACK` remains. Reconcile those items semantically before continuing.
Never use elapsed time alone as abandonment evidence or edit ownership fields.

Before any browser typing or submit action, first commit the write-ahead send
intent:

```text
<python-path> scripts/run_state.py send-intent --root <state-root> --run-id <RUN_ID> --session-id <SESSION_ID> --expected-revision <REVISION> --logical-work-id <WORK_ID> --lane-id <LANE_ID> --conversation-id <CONVERSATION_ID> --prompt-hash <PROMPT_SHA256>
```

Proceed with browser input only when the result is
`SEND_INTENT_COMMITTED` and `browser_input_permitted` is true. After a semantic
browser check proves submission, record `ack` with the new revision. If input
may have happened but acknowledgment is unavailable, record
`outcome-unknown`; then inspect the intended conversation and use `reconcile`
with exactly `ACK`, `COMPLETED`, `FAILED`, or `NOT_SENT`. The helper does not
promise exactly-once browser delivery.

Reusing a logical work ID with the same prompt hash returns `SUPPRESSED`
without authorizing another send. A changed prompt hash under the same work ID
is rejected. Only a semantically established `NOT_SENT` result permits the
same logical work ID to be recommitted with `--confirmed-not-sent`; all new
work gets a new stable logical work ID. Mirror each helper transition and
revision in the aggregate/lane records so a future turn can reconcile both
representations.

Close an owned active run deliberately with `complete` or `block`, supplying
the exact revision, a bounded reason, a safe evidence reference, and the
observed desktop-action state. `complete` requires all browser work reconciled,
takeover recovery cleared, and `--desktop-state CLEAR`; it then releases the
owner. `block` records a terminal blocker and may preserve unresolved work as
evidence. Map helper `COMPLETE` to the human-facing accepted run disposition
only after the skill's full completion rule passes.

## Portable immutable-revision fallback

This fallback preserves the helper's safety semantics without pretending that
an untested platform has Linux `fcntl`, ownership, or mode behavior. Keep a
bounded run-owned directory with:

```text
current.json
revisions/
  00000001-<REVISION_SHA256>.json
  00000002-<REVISION_SHA256>.json
```

Each revision envelope contains the run ID, integer revision, prior revision
SHA-256, writer/owner session, run status, recovery gate, bounded logical-work
records, and exactly one append-only transition event. It contains prompt
hashes and safe identifiers, never prompt bodies, responses, credentials, or
browser secrets. `current.json` contains only run ID, revision, exact revision
filename, and SHA-256.

For every mutation:

1. Allow one writer session only. Reread `current.json` and the referenced
   immutable revision; verify the exact filename, hash, run ID, revision, prior
   hash chain, and expected owner. A conflicting claimed owner is a hard stop.
2. Construct revision `N+1` with one transition. Create its revision file as a
   new sibling without overwriting any path, flush it durably when the available
   platform interface supports that, reread the exact bytes, and verify its
   hash and schema.
3. Replace `current.json` atomically only through an already available,
   platform-appropriate replace operation, then reread and verify the pointer
   and referenced revision. Do not advertise the commit as durable or proceed
   to external input if exclusive creation, replacement, flush, or reread
   cannot be verified.
4. Never edit or delete an accepted revision. Update the Markdown mirrors only
   after the machine revision commits, recording its exact revision and hash.

The browser send protocol is identical to the helper: commit and verify a
`SEND_INTENT` revision before input; after input commit `ACK`,
`OUTCOME_UNKNOWN`, or a semantically verified reconciliation. Duplicate work
IDs suppress resend. Only a verified `NOT_SENT` transition permits an explicit
retry. A takeover requires the exact revision, prior owner, bounded reason, and
trusted evidence; it preserves pending work and gates all new sends until
reconciled.

If a crash leaves an unreferenced revision, a partial file, a broken hash chain,
or an ambiguous pointer, freeze new input. Preserve the bytes, compare only the
bounded run directory, classify the last send as unknown when external effect
cannot be disproved, and repair state only by adding a new evidence-bound
revision from the last fully verified chain. Never choose the highest filename
or newest timestamp by itself.

## Capacity reserve and rollover

The Linux helper reports `event_capacity` from `show` and `history`. Ordinary
mutations stop before the hard event limit. The remaining reserve exists only
for takeover, post-send outcome/reconciliation, pause/release, recovery-only
reclaim, and terminal `BLOCKED`/`COMPLETE` transitions. It must never authorize
another send, retry, ordinary claim, or ordinary resume.

When `rollover_required` is true, freeze new work in that run, reconcile every
pending browser effect, and pause, release, block, or complete it as the
evidence permits. If accepted scope remains, initialize a distinct successor
run and record both IDs, the predecessor's final revision/hash, the reason
`EVENT_CAPACITY_ROLLOVER`, unresolved items, and the exact resume cursor in both
handoffs. Never copy unresolved work into a state that could make it sendable;
carry it as reconciliation-only evidence.

If a capacity-bound run is unowned, it may use one reserved transition to
regain an owner in `RECOVERY_ONLY` mode: use `resume` for `PAUSED`, or `claim`
for a released `READY` handoff. This remains necessary when every browser
effect is already reconciled, because an owned `ACTIVE` run is required for a
terminal transition. Recovery-only ownership may reconcile existing work and
reach `BLOCKED` or `COMPLETE`, but it cannot commit a new send. Do not use a
recovery-only reclaim as a way around rollover.

Apply the same policy to the portable backend: set a finite ordinary revision
limit at creation, reserve at least three transitions per permitted logical
work item plus takeover and safe exit, and record the limits in every revision.
Once ordinary capacity closes, only reconciliation and safe-exit revisions may
be created before successor rollover.

## Aggregate run state

Create one note from `assets/run-state-template.md`. It is authoritative for:

- selected state backend/platform, its verified security properties, current
  revision/hash, capacity, and any predecessor/successor rollover link;
- run status, allocation profile, qualitative Codex-usage band, allocation
  change history, scope-expansion policy, first-pass discovery, reporting
  cadence, and status freshness;
- workforce-profile path/version and first-use setup completion state;
- current and prior preflight ID, level, trigger, start/completion time, result,
  capability delta, and last verified route;
- initial and discovered scope registries plus user decisions;
- lane, artifact, validation, and acceptance registries;
- exact progress numerators, denominators, and denominator-change history;
- pause reason, safe usage-limit evidence, provider-shown reset time, and
  `resume_not_before` when established;
- workload-prerequisite status, setup ID/plan path, exact approved packet,
  manual step, post-setup preflight result, and declined alternatives;
- visual capture surface plus outer-window/content-viewport geometry, device
  scale, automation/debugging-infobar inset, and crop when relevant;
- control-fault diagnostic ID, trigger, frozen actions, affected capabilities,
  repair evidence/count, route delta, and disposition;
- worker-download policy/root/run directory, immutable manifest, retention
  policy, cleanup plan/status/authorization, and per-file outcomes;
- Obsidian note policy, confirmed vault/research root, topic slug/folder,
  creation authority, locator source/recommendation/confirmation, safe vault ID
  when retained, native artifact store, index path, and last note path;
- dashboard policy, dedicated root, run directory, port, managed process/session
  identity, URL, health time, snapshot time/hash, and stale/failure state;
- completed-research explorer policy, accepted data/template/output hashes,
  run-owned and human-facing export paths, companion JSON choice, validation
  results, and next action;
- last durable checkpoint, reconciliation needs, failed approaches, pending
  user decisions, and exact resume cursor.

Run status uses `DRAFT`, `READY`, `ACTIVE`, `PAUSING`, `PAUSED`,
`LIMIT_PAUSED`, `RESUMING`, `PARTIAL`, `BLOCKED`, `ACCEPTED`, `REJECTED`,
`STOPPED`, or `SUPERSEDED`. Keep it separate from lane generation, capability,
desktop-action, and artifact states.

## Lane state

Create one note per lane from `assets/lane-state-template.md`. At minimum store:

- run ID;
- iteration ID;
- lane ID;
- mode;
- status;
- owner;
- selected capability route;
- conversation URL;
- safe browser tab/window identity;
- prompt path and hash;
- submitted timestamp;
- last observed timestamp;
- last progress summary;
- expected artifacts;
- recovered artifacts and hashes;
- visual capture surface, target, outer-window/content-viewport dimensions,
  scale, automation/debugging-infobar inset, and crop when applicable;
- mechanical-gate result;
- semantic-gate result;
- retry count;
- failure classification;
- desktop adapter/method, safe target identity, focus precheck, bounded action,
  and semantic postcondition when desktop control was required;
- next action.

Do not store credentials, cookies, tokens, private browser state, or secrets.

## Submission lineage and duplicate suppression

Keep an append-only submission ledger in the aggregate run record and mirror
the lane-specific entries in each lane note. Each row binds a sequence number,
lane ID, safe conversation identity, exact prompt SHA-256, observation time,
and disposition. Never edit an earlier row to make a retry look like the
original submission.

Immediately before send, re-read the latest revision and visible target
conversation. Commit the helper's `SEND_INTENT` before input and suppress the
send when the same stable logical work ID already has any active, returned,
terminal, or unknown outcome; mirror `SUPPRESSED_DUPLICATE` in the note ledger
and point it to the canonical sequence. A different prompt for a lane with
`SUBMITTED`, `RUNNING`, or `OUTCOME_UNKNOWN` work is also blocked until that
outcome is reconciled. A correction or intentional new request gets a new
logical work ID, prompt hash, and sequence plus the reason the prior result is
no longer canonical. Reuse the original work ID only when the helper has a
verified `NOT_SENT` state and the recommit explicitly says
`--confirmed-not-sent`.

## State transitions

Use:

```text
PLANNED -> PREFLIGHTED -> SUBMITTED -> RUNNING -> RETURNED
RETURNED -> MECHANICAL_ACCEPTED | MECHANICAL_REJECTED
MECHANICAL_ACCEPTED -> SEMANTIC_ACCEPTED | SEMANTIC_REJECTED
SEMANTIC_ACCEPTED -> ACCEPTED
any state -> PARTIAL | BLOCKED | NOT_RECOVERABLE | SUPERSEDED
```

Record the evidence for every transition. Do not infer `ACCEPTED` from a worker's
completion marker.

Run-level transitions include:

```text
DRAFT -> READY -> ACTIVE
ACTIVE -> PAUSING -> PAUSED
ACTIVE | PAUSED -> LIMIT_PAUSED
PAUSED | LIMIT_PAUSED | PARTIAL -> RESUMING -> ACTIVE
ACTIVE | RESUMING -> PARTIAL | BLOCKED | ACCEPTED | REJECTED | STOPPED
any nonterminal state -> SUPERSEDED
```

Before `RESUMING -> ACTIVE`, reconcile duplicate prompts, active or completed
conversations, returned artifacts, stale inputs, capability deltas, and every
`OUTCOME_UNKNOWN` desktop action. Also reconcile any `IN_PROGRESS`,
`MANUAL_ACTION_REQUIRED`, or `FAILED` prerequisite setup from its durable plan;
do not repeat installation or permission requests from memory. A pause does not
imply a healthy external generation was stopped.

Run the `INVOCATION_GATE` before any resume transition. Reconcile the exact
download/cleanup manifest, topic/index paths, and dashboard process identity;
never assume a remembered server PID, link, browser handle, or filesystem path
is still current. Read the selected backend's canonical state (`show` for the
Linux helper; the hash-verified `current.json` chain for the portable backend),
compare the mirrored revision, and resume only after the run is confirmed
`PAUSED` and unowned; claim a released `READY` handoff. Use evidence-bound
takeover only for a confirmed abandoned `ACTIVE` owner, and reconcile every
recovery gate it reports before a new send. A requested allocation
change may occur in any nonterminal
run state, but becomes effective only for future work and must preserve active
lane ownership.

## Integration handoff

The integration handoff must answer:

- What outcome was requested?
- Which lanes and conversations exist?
- What is still running?
- Which artifacts were returned, and where are the raw bytes?
- Which exact candidates passed or failed each gate?
- What independent verification was performed?
- What contradictions or open questions remain?
- What failed recovery attempts must not be repeated?
- What is the next concrete action?
- What user approval or decision, if any, is actually required?
- What allocation, expansion policy, cadence, run state, status freshness,
  pause reason, capacity evidence, and exact resume cursor apply?
- What qualitative Codex-usage band and allocation changes apply, and which
  active lanes retain their original ownership?
- What first-use profile, invocation gate, capability delta, and any control-
  fault diagnostic/repair apply?
- Which prerequisites were required, verified, declined, or left manual; what
  setup packet and post-setup preflight apply; and what capture-geometry limits
  affect visual evidence?
- Where are run-owned downloads, which cleanup decisions remain, and which
  exact files were retained, trashed, quarantined, identity-blocked, skipped,
  or failed?
- What note/vault/research-root/topic/index state exists, and are native
  artifacts indexed rather than duplicated?
- Is the optional dashboard healthy, stale, stopped, or unavailable; what was
  its last snapshot; and should the link be shown after a fresh health check?
- Was a completed-research explorer requested; which accepted data and template
  produced it; did mechanical, semantic, browser, offline, and print checks
  pass; and do the run-owned and human-facing copies still match their hashes?

A handoff must be sufficient for another Codex turn to continue without
reconstructing state from browser memory.
