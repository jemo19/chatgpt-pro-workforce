# Progress reporting and run controls

Use this reference for guided setup choices, compact progress cards, detailed
status, scope-expansion decisions, pause/usage-limit/resume behavior, allocation
changes, and help.

## Contents

- [Interface boundary](#interface-boundary)
- [Control intents](#control-intents)
- [Work allocation](#work-allocation)
- [Pro worker concurrency](#pro-worker-concurrency)
- [First-pass scope expansion](#first-pass-scope-expansion)
- [Evidence-based progress](#evidence-based-progress)
- [Reporting cadence](#reporting-cadence)
- [Compact and detailed status](#compact-and-detailed-status)
- [Local detail dashboard](#local-detail-dashboard)
- [Pause and usage limits](#pause-and-usage-limits)
- [Resume and continue](#resume-and-continue)
- [Help behavior](#help-behavior)
- [Existing-run migration](#existing-run-migration)

## Interface boundary

This skill can render status cards in chat, recognize user intent following an
explicit `$chatgpt-pro-workforce` invocation, and optionally serve a read-only
loopback detail page. It cannot by itself create a native hover tooltip,
register true subcommands, guarantee a server after the host session ends, run
a background scheduler, or send notifications after the active Codex run ends.

Treat the patterns below as conversational invocation intents, not shell or UI
commands. Put the visible `tell me more` hint under every compact status card;
that hint is the portable replacement for a tooltip. If the host supports an
expandable details surface, it may also be used, but the visible invocation
must remain.

Periodic reporting is best-effort during an active Codex turn. Never imply that
a timer, worker monitor, or notification continues after control returns to the
user, a turn ends, or usage capacity prevents work.

## Control intents

Recognize these forms and close natural-language equivalents:

```text
$chatgpt-pro-workforce status [RUN_ID]
$chatgpt-pro-workforce tell me more [RUN_ID]
$chatgpt-pro-workforce status more [RUN_ID]
$chatgpt-pro-workforce pause [RUN_ID]
$chatgpt-pro-workforce resume [RUN_ID]
$chatgpt-pro-workforce continue [RUN_ID]
$chatgpt-pro-workforce review discovered topics [RUN_ID]
$chatgpt-pro-workforce change allocation [RUN_ID] [PRO_HEAVY|BALANCED|CODEX_HEAVY|LOCAL_ONLY]
$chatgpt-pro-workforce change concurrency [RUN_ID] [1|2|FINITE_MAXIMUM]
$chatgpt-pro-workforce dashboard [RUN_ID]
$chatgpt-pro-workforce dashboard troubleshoot [RUN_ID]
$chatgpt-pro-workforce dashboard stop [RUN_ID]
$chatgpt-pro-workforce export explorer [RUN_ID]
$chatgpt-pro-workforce stop [RUN_ID]
$chatgpt-pro-workforce uninstall
$chatgpt-pro-workforce help [status|dashboard|explorer|modes|allocation|concurrency|resume|controls|prerequisites|install|uninstall]
```

Resolve a missing run ID only when exactly one active run or one most recently
paused run is unambiguous from durable state. Otherwise ask one concise
identifying question using safe run ID and outcome text only.

- `status` reads durable state and emits the compact card.
- `tell me more` and `status more` emit the detailed card.
- `pause` checkpoints orchestration without routinely stopping healthy workers.
- `resume` reloads and reconciles a paused or capacity-limited run.
- `continue` resumes when paused; when active, it continues the existing
  bounded lane without creating a duplicate.
- `review discovered topics` shows the first-pass expansion decision packet.
- `change allocation` may be used at any time and applies a newly selected
  profile only to future work.
- `change concurrency` may be used at any time and applies a finite maximum to
  future worker launches. Values above two require the current-run, exact-limit
  risk warning and acknowledgment; lowering the limit never closes active chats.
- `dashboard` creates/refreshes and, when needed, starts the run's authorized
  loopback status surface; `dashboard stop` stops only its verified managed
  process and leaves durable state intact.
- `dashboard troubleshoot` runs the exact-root/run/snapshot diagnostic,
  verifies the rendered page through the available Chrome/browser route, and
  may perform at most one authorized bounded restart of an identity-matched
  skill-owned process. It never kills an unknown port owner.
- `export explorer` reads the completed-research explorer policy and accepted
  run state, then builds or re-verifies the exact human-readable HTML export.
  It never launches a worker or promotes unaccepted data. If the run is not
  ready, report the missing acceptance gate instead of building a provisional
  file that looks final.
- `stop` requires explicit intent, persists final state, and must not be
  confused with a recoverable pause.
- `uninstall` opens the exact-target, confirmation-gated, recoverable procedure
  in [installation lifecycle and safe uninstall](installation-and-uninstall.md).
  It is never executed merely because help or the dashboard displays it.
- `help` explains these intents and their boundaries.

A status or help request must not implicitly resume, submit, upload, download,
send desktop input, or otherwise mutate the run. A fresh read-only observation
may be used only when already authorized and safely targetable. If no refresh
is possible, report persisted evidence as `STALE` or `UNKNOWN`.
Atomically rewriting the optional sanitized dashboard projection is permitted;
it is reporting output and must not change authoritative run state.

## Work allocation

Allocation is separate from operating mode. A research lane can use any
allocation profile; `research`, `review`, and `synthesis` describe the work,
while allocation describes which capability performs it.

Use exactly one run-level profile:

| Profile | Qualitative Codex usage | ChatGPT Pro role | Codex role |
|---|---|---|---|
| `PRO_HEAVY` | `LOWEST` | Most research, analysis, drafting, and artifact-production lanes | Scope, permission gates, prompt contracts, monitoring, recovery, mechanical and semantic acceptance, risk-proportionate independent verification, integration, and handoff |
| `BALANCED` | `MODERATE` | Parallel research, specialist analysis, independent review, and bounded drafts | Meaningful local evidence checks, contradiction resolution, synthesis, artifact integration, and all fixed acceptance duties |
| `CODEX_HEAVY` | `HIGH` | Bounded specialist, blind, adversarial, or second-opinion lanes | Primary analysis, research, calculations, synthesis, production, and verification |
| `LOCAL_ONLY` | `CODEX_ONLY` | No worker launch | Complete locally or report why the requested workforce route is unnecessary |

Recommend `BALANCED` unless task shape or explicit user preference supports
another choice. The closest safe equivalent to “Pro does the work and Codex
only orchestrates” is `PRO_HEAVY`; Codex's fixed authority, recovery, lineage,
verification, and final-acceptance duties never disappear.

These usage bands describe relative task allocation, not measured tokens,
subscription quotas, time, or cost. Actual Codex usage varies with task size,
worker quality, failures, artifact recovery, and the independent checks required
for acceptance. Show that caveat during setup and whenever the user compares
profiles.

The user may change allocation at any time. An allocation change affects only
future work. Preserve active lane ownership: do not silently abandon,
interrupt, retask, or duplicate an active lane. Record the old/new profile and usage band, effective time, which pending
responsibilities move, and the provenance and acceptance standard for completed
work. If the requested change would alter an active writer or consequential
action, explain the transition and obtain the applicable approval before it
takes effect.

## Pro worker concurrency

Default to a maximum of two simultaneous ChatGPT Pro worker conversations.
Before each submission, follow the reconciliation and launch gate in
[orchestration and lane design](orchestration.md). Show its exact high-risk
warning before accepting any finite maximum above two. The user must explicitly
acknowledge the warning for the current run and exact maximum; a preference or
old acknowledgment is insufficient.

Report the configured maximum, safely observed active-or-unknown count, and
whether a high-risk acknowledgment applies in compact status when it affects
the next action, and always in detailed status. If the run is already above two
without a valid acknowledgment, continue non-destructive monitoring/recovery
but launch nothing new. Never close conversations automatically. A changed
limit applies only to future launches and remains subject to verified route
capacity and provider state. A lower user, project, or verified-route maximum
always wins; the two-worker default and a high-risk acknowledgment never
override it.

The short user-facing rules are: **Never auto-close existing chats.** Treat
active or unknown generation outcomes conservatively. Warn that unsaved or
unverified work may be lost before accepting the risk.

## First-pass scope expansion

For research or another discovery-heavy run, ask during guided setup how to
handle meaningful topics, information types, or categories found during the
first pass. Store one policy:

- `ASK_BEFORE_ADDING` — recommended; pause at a coverage checkpoint and ask.
- `AUTO_ADD_IN_SCOPE` — add only clearly bounded items that require no new
  permission, system, sensitive input, consequential action, or material cost.
- `FIXED_SCOPE` — retain the approved scope and record useful adjacent topics
  as deferred.

Workers may propose discovered topics but may not pursue them unless the stored
policy permits it. Assign stable IDs such as `D01`. Each proposal must include:

- topic or category;
- why it is materially relevant to the requested outcome;
- evidence that exposed the gap;
- likely value and expected deliverable impact;
- estimated lane or effort cost without invented precision;
- overlap with approved work;
- proposed lane and exclusions.

Use first-pass discovery states `NOT_REQUESTED`, `PLANNED`, `RUNNING`,
`READY_FOR_DECISION`, `DECIDED`, or `SKIPPED`.

Under `ASK_BEFORE_ADDING`, move to `READY_FOR_DECISION`, show the proposal
packet, and launch no new topic lane until the user approves, defers, or rejects
each item. Topic records use:

```text
origin: INITIAL | DISCOVERED
decision: PENDING | APPROVED | DEFERRED | REJECTED
work_state: NOT_STARTED | IN_PROGRESS | ADDRESSED | BLOCKED
acceptance: NOT_REVIEWED | ACCEPTED | REJECTED
```

`AUTO_ADD_IN_SCOPE` never expands authority. A discovered topic that crosses a
boundary becomes `PENDING` regardless of policy. Avoid topic inflation: a
synonym, duplicate, interesting tangent, or unsupported suggestion is not a new
coverage item.

## Evidence-based progress

Status bars summarize registered units, not subjective completion, elapsed
time, response length, worker confidence, or an ETA.

Use these cross-mode categories:

| Category | Numerator | Denominator |
|---|---|---|
| `Scope` | Approved scope items with `work_state: ADDRESSED` | Currently approved initial and discovered scope items |
| `Workers` | Terminal non-superseded lanes | Registered non-superseded lanes |
| `Artifacts` | Expected artifacts recovered with exact identity | Registered expected artifacts |
| `Validation` | Required mechanical, semantic, and independent checks passed | Registered required checks |
| `Acceptance` | Accepted lanes or acceptance milestones | Registered required acceptance units |

“Terminal” for `Workers` includes accepted, rejected, partial, blocked, and
unrecoverable lanes. It measures lane disposition, not success; `Acceptance`
shows success separately.

For each finite category, fill a ten-cell bar using:

```text
filled_cells = floor(10 * numerator / denominator)
```

Always show the exact ratio. A percentage is optional and may appear only when
derived from that finite ratio; label it “of registered items,” never “percent
done.” If the denominator is zero, unknown, or intentionally open-ended, show
`[active] —/—` or a named state rather than a bar or percentage.

Do not average the categories into a subjective overall percentage. An overall
row is allowed only when it is the exact ratio of satisfied to registered
acceptance milestones.

Scope expansion may increase a denominator and visually shorten a bar. Record
the change, for example `scope_change: +2 approved`, and explain it in the next
card instead of describing it as lost work. A rejected check or reopened
artifact may also reduce a numerator; preserve the reason and candidate
identity.

An ETA may be shown only when based on a provider-displayed reset time or an
observable, stated rate. Label it as an estimate and preserve the source.

## Reporting cadence

Ask for one cadence during setup and store it in run state:

- `VERBOSE` — compact card after every meaningful monitoring observation.
- `STANDARD` — recommended; card on material transition, blocker, user
  decision, or after no more than two unchanged monitoring observations.
- `QUIET` — card only for transitions, blockers, decisions, pause/resume, and
  terminal status.

Always report pause, capacity-limit, blocker, required user decision, and
terminal transitions promptly during an active turn. Internal non-disruptive
monitoring remains separate and may still occur every 45–90 seconds. Status
cadence never justifies interrupting a healthy worker or producing repetitive
cards with no new evidence.

## Compact and detailed status

Use [progress card template](../assets/progress-card-template.md).

The compact card contains:

- run ID, run state, allocation profile, as-of time, and freshness;
- the concurrency limit and active-or-unknown Pro count when relevant;
- applicable progress categories with exact ratios;
- active, waiting, paused, or blocked lanes;
- any prerequisite decision or manual action currently blocking launch/resume;
- the next safe action or user decision;
- the exact visible `tell me more` invocation;
- the verified `127.0.0.1` dashboard link when configured and healthy;
- brief pause/resume/help controls.

The detailed card adds:

- requested outcome, capability route, allocation, scope policy, and cadence;
- every lane's state, last-observed time, prompt/conversation identity when
  safe, latest evidence, and next action;
- scope registry plus pending discovery decisions;
- artifact paths, sizes, hashes, and dispositions when useful;
- mechanical, semantic, and independent verification results;
- conflicts, rejected material, capacity state, approvals, blockers, and
  approaches not to repeat;
- the configured concurrency maximum, active-or-unknown count, proposed next
  count, warning/acknowledgment scope, and whether the launch gate is open;
- required/optional prerequisite readiness, setup ID/state/plan, post-setup
  preflight result, manual alternative, and capture-geometry limitations;
- progress denominators and any changes since the prior card;
- exact resume cursor and next safe action.

The detailed card also states dashboard policy, root label, health, last
snapshot time, and whether its server lifetime is currently managed or unknown.

Use `CURRENT`, `STALE`, or `UNKNOWN` for status freshness. Do not expose
unrelated conversation titles, windows, browser state, or sensitive content to
make a status look more current.

Prerequisite setup states are workflow evidence, not a sixth progress bar. They
affect `Validation` only when an exact readiness/preflight check was registered
before work began; never award progress merely because an installer exited
successfully.

## Local detail dashboard

Read [local status dashboard](local-status-dashboard.md) and use the
[dashboard page](../assets/status-dashboard-template.html),
[status data template](../assets/status-data-template.json), and
[dashboard helper](../scripts/status_dashboard.py).

The compact card keeps the five evidence categories; the page may expand them
into readiness, lanes, artifacts, validation, decisions, storage, and notes.
Its prominent top summary must show run state, allocation profile, qualitative
Codex-usage band, freshness, last durable update, and the next safe action.

Below the status content, show a complete polished controls reference matching
this document's help behavior. Include exact commands, concise effect and safety
notes, the current validated run ID, and copy buttons. Copying command text is
allowed only on an explicit user click and never executes the command; all
control interpretation and authorization remains in chat.

Include the copyable `$chatgpt-pro-workforce uninstall` intent. Label it as a
guided local lifecycle operation that first inventories one exact active
installation, offers a recoverable backup, excludes research data and shared
control tooling, and asks for explicit confirmation. The page itself must not
delete, rename, stop, or call an uninstall endpoint.

Include a copyable `$chatgpt-pro-workforce export explorer RUN_ID` intent for
research runs. Explain that it builds a self-contained human-readable file only
from accepted data, or reports which acceptance checks are still missing. The
dashboard itself never creates or overwrites that file.

Include a copyable `$chatgpt-pro-workforce change concurrency RUN_ID` intent.
State that two is the safe default, values above two are high risk and require
an explicit current-run acknowledgment, and changing the setting never closes
active chats. The page only copies the intent.

On every invocation, atomically refresh the run's sanitized snapshot when the
dashboard policy is not `DISABLED`. A page already open polls this file with
cache disabled. This is data refresh, not background orchestration. Show a URL
only after the exact server, run-page, and snapshot verification succeeds;
when Chrome/browser control is available, also confirm the expected run ID and
connection state in the rendered page. When verification fails or the process
has ended, run the bounded dashboard fault diagnostic, omit the URL, and keep
`$chatgpt-pro-workforce tell me more RUN_ID` visible.

The dashboard is read-only. Starting/stopping its managed local process never
implies resume, pause, worker submission, cleanup, setup, or desktop input.

## Pause and usage limits

Run status uses exactly:

```text
DRAFT READY ACTIVE PAUSING PAUSED LIMIT_PAUSED RESUMING PARTIAL BLOCKED
ACCEPTED REJECTED STOPPED SUPERSEDED
```

A normal `pause` is a safe orchestration checkpoint:

1. Stop new worker submissions and new control actions.
2. Persist the run record, lanes, prompt hashes, conversation identities,
   artifacts, gates, desktop actions, and exact next safe action.
3. Do not press stop, reload, or interrupt a healthy ChatGPT worker merely to
   reach a paused state.
4. If a worker may still be generating, use `PAUSING`, state that fact, and
   state that no background monitoring is promised after the active turn ends.
5. Use `PAUSED` when the durable checkpoint is complete and no immediate
   outcome reconciliation is pending.

Stopping active workers is different from pausing orchestration. Require clear
user intent, explain potential output loss, and obey the active browser or
desktop action-time confirmation rules.

When a provider usage or capacity limit is visibly established:

- use `LIMIT_PAUSED` when no useful in-scope work can continue;
- preserve the exact safe visible evidence and any reset time actually shown;
- use `UNKNOWN` for an unshown reset time; never guess;
- record `resume_not_before` only when established;
- do not evade the limit, switch accounts, create another profile, spam retry,
  or duplicate a submitted prompt;
- offer a user decision to wait or change future allocation when that would
  materially change the plan.

Use pause reasons `NONE`, `USER_REQUEST`, `USAGE_LIMIT`, `CONTROL_LOSS`, or
`EXTERNAL_BLOCKER`.

## Resume and continue

Before changing a paused run to active:

1. Load the run-state record, kickoff, lane states, iteration notes, artifacts,
   and handoff. Do not reconstruct state from browser memory alone.
2. Re-read current instructions and recheck authorization, capability deltas,
   stale inputs, and any established `resume_not_before`.
3. Re-identify intended conversations non-destructively.
4. Reconcile returned artifacts, active generations, duplicate prompt hashes,
   and every `OUTCOME_UNKNOWN` action before input.
5. Recompute registered progress units and explain denominator changes.
6. Preserve failed approaches and suppress duplicate submissions.
7. Set `RESUMING`, then `ACTIVE` only after reconciliation.

If the usage limit persists, remain `LIMIT_PAUSED`. If durable state is missing
or corrupt, reconstruct only from trustworthy kickoff, lane, artifact, and
handoff evidence; otherwise report `BLOCKED` rather than inventing history.

## Help behavior

`$chatgpt-pro-workforce help` shows:

- the invocation intents from this reference;
- plain-language examples;
- the current safe run ID when unambiguous;
- operating modes versus work-allocation profiles;
- the qualitative Codex-usage gradient, its uncertainty, and the always-
  available `change allocation` intent;
- the default two-worker concurrency guard, the exact warning/acknowledgment
  rule for three or more, and the `change concurrency` intent;
- status versus detailed status;
- soft pause versus explicit stop;
- resume/continue and first-pass topic review;
- workload prerequisite readiness and the difference between discovery, a
  setup offer, exact approval, manual OS consent, and verified preflight;
- the native-interface boundary: these are recognized chat intents, not
  registered UI commands or background notifications.
- the optional loopback dashboard, its current health, and the fact that it is
  a read-only best-effort process rather than a permanent service.
- the standard user-scoped install shape and recoverable, exact-target uninstall
  flow; link to [installation lifecycle and safe uninstall](installation-and-uninstall.md)
  for `help install` or `help uninstall`.

Topic-specific help such as `help status`, `help modes`, or `help resume`
should be short and contextual. Help never launches or resumes a worker.

## Existing-run migration

Older runs may have lane and handoff state but no aggregate run-state record.
On the first status or resume request:

- create a schema-version-2 run record from durable kickoff, iteration, lane, artifact, and
  handoff evidence;
- preserve existing files and submitted prompt hashes;
- use `UNKNOWN` or `NOT_REQUESTED` for unavailable historical fields;
- use migrated defaults `BALANCED`, `ASK_BEFORE_ADDING`, and `STANDARD` only
  when no contrary evidence exists, and label them as migrated defaults;
- derive `MODERATE` only from the migrated `BALANCED` profile, set dashboard
  policy to `ON_DEMAND` without starting a process, and leave storage/note roots
  unknown until confirmed;
- set the migrated concurrency maximum to `2`, with no high-risk
  acknowledgment, without closing or interrupting any already active chat;
- never invent historical progress ratios or rewrite a submitted prompt.
