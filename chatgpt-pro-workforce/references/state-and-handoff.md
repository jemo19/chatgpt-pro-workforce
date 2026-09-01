# State and resumability

Every non-trivial run must survive context compaction, a new Codex turn, browser
reconnection, page reload, worker timeout, partial return, and lanes finishing
at different times.

## Contents

- [Aggregate run state](#aggregate-run-state)
- [Lane state](#lane-state)
- [State transitions](#state-transitions)
- [Integration handoff](#integration-handoff)

## Aggregate run state

Create one note from `assets/run-state-template.md`. It is authoritative for:

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
is still current. A requested allocation change may occur in any nonterminal
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
  exact files were retained/trashed/deleted/skipped/failed?
- What note/vault/research-root/topic/index state exists, and are native
  artifacts indexed rather than duplicated?
- Is the optional dashboard healthy, stale, stopped, or unavailable; what was
  its last snapshot; and should the link be shown after a fresh health check?
- Was a completed-research explorer requested; which accepted data and template
  produced it; did mechanical, semantic, browser, offline, and print checks
  pass; and do the run-owned and human-facing copies still match their hashes?

A handoff must be sufficient for another Codex turn to continue without
reconstructing state from browser memory.
