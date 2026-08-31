# Orchestration and lane design

## Contents

- [Conversation selection](#conversation-selection)
- [Work allocation profiles](#work-allocation-profiles)
- [Launch-readiness gate](#launch-readiness-gate)
- [Lane charter](#lane-charter)
- [Parallelism rules](#parallelism-rules)
- [Pro conversation concurrency gate](#pro-conversation-concurrency-gate)
- [Blind review](#blind-review)
- [Correction loop](#correction-loop)

## Conversation selection

### Continue the same conversation when

- continuity and retained artifacts matter;
- the worker is repairing its own bounded packet;
- the context remains manageable and internally consistent;
- the correction depends on facts established in that conversation.

### Start a fresh conversation when

- independence or blinding matters;
- the current context is too long, confused, or contaminated;
- the lane has a distinct scope;
- a prior conversation repeatedly fails;
- a clean-room, adversarial, source-rights, or alternative-solution review is
  needed.

### Use parallel conversations when

- lanes are genuinely independent;
- each lane has exclusive ownership of its outputs;
- the results can be integrated without hidden shared assumptions;
- current browser/agent capacity supports the planned concurrency;
- one integration owner is responsible for reconciliation.

### Prefer local Codex work when

- the task is cheaper to perform locally than to transfer and verify;
- local repository or system state is central;
- direct mutation is required;
- deterministic tooling already solves the problem;
- external context would add little independence or evidence value.

## Work allocation profiles

Select `PRO_HEAVY`, `BALANCED`, `CODEX_HEAVY`, or `LOCAL_ONLY` at kickoff using
the definitions in [progress reporting and run controls](progress-and-controls.md).
Show the qualitative Codex-usage band (`LOWEST`, `MODERATE`, `HIGH`, or
`CODEX_ONLY`) with the non-predictive usage caveat. Allocation changes who does
future substantive work, not authority or the required acceptance standard.

The user may change allocation at any time. When changing it mid-run:

- apply the change only to unsubmitted or newly created work;
- preserve active lane ownership, prompt hashes, and stopping conditions;
- do not abandon, retask, or duplicate a worker silently;
- state which remaining responsibilities move and why;
- keep Codex's fixed recovery, verification, integration, and acceptance duties;
- update the run state and next compact status card.

## Launch-readiness gate

Before creating or reusing a browser conversation, bind each lane action to the
capability report. Every required prerequisite must be `AVAILABLE_VERIFIED`,
covered by an explicitly accepted manual/degraded route, or made unnecessary by
the final lane design. A setup state such as `OFFERED`, `AWAITING_APPROVAL`,
`IN_PROGRESS`, `MANUAL_ACTION_REQUIRED`, or command-level “success” is not
launch readiness. After setup, require the full preflight result and update the
selected route before submission.

Do not add desktop control merely because it is available. If a missing
optional capability affects convenience only, record the limitation and use
the least-powerful ready route.

## Lane charter

Every lane charter must contain:

```yaml
run_id: RUN-YYYYMMDD-NNN
iteration_id: I00
lane_id: L01
mode: research
owner: root-codex
conversation_policy: fresh
objective: "One bounded question or deliverable"
inputs:
  - "Exact artifact or source"
outputs:
  - "Exact filename or response section"
exclusions:
  - "Explicit non-goal"
evidence_standard: "Primary-source, current, claim-level support"
mechanical_acceptance:
  - "Required file exists and parses"
semantic_acceptance:
  - "Claims are entailed by cited sources"
stopping_condition: "Accepted, bounded blocker, or explicit user decision"
```

## Parallelism rules

- Default to no more than two simultaneous ChatGPT Pro worker conversations.
  A lower user/project limit or verified browser capacity takes precedence.
  Never create concurrency merely to appear busy.
- One lane owns one ChatGPT conversation at a time.
- One file or module scope has one writer.
- Use stable lane IDs in prompts, filenames, state notes, and completion markers.
- Assign one integration owner before submission.
- Record shared inputs by immutable hash or version when possible.
- Do not let one lane silently overwrite another lane's accepted output.
- Treat a first-pass discovered topic as a proposal, not a lane, until the
  stored scope-expansion policy permits it and the decision is persisted.

## Pro conversation concurrency gate

The safe default is `max_concurrent_pro_workers: 2`. This is an operational
risk guard, not a claim about a guaranteed provider quota. Count a conversation
as concurrent after submission while generation may still be active or its
outcome is unknown. This includes submitted, running, healthy-slow,
transient-error, stalled, browser-disconnected, and otherwise nonterminal
outcome-unknown conversations. Do not count a conversation only after durable
evidence proves it terminal or never submitted. When evidence is ambiguous,
count it conservatively.

Immediately before every new submission:

1. Reconcile the durable lane registry with safely targetable conversation
   state without closing, reloading, or interrupting any chat.
2. Record the active-or-unknown count and the proposed post-launch count.
3. Apply the lower of the stored limit, verified route capacity, and any
   user/project limit as the effective limit.
4. If the proposed count exceeds that effective limit, suppress the launch.
   Neither the default of two nor a high-risk acknowledgment may override a
   lower user, project, or verified-route limit.
5. If the proposed count is at most two, is within the effective limit, and all
   other gates pass, proceed.
6. If the proposed count would be three or more but remains within the effective
   limit, suppress the launch unless a valid high-risk acknowledgment exists for
   this run and the exact selected maximum.

Show this warning verbatim before accepting a maximum above two:

> Running more than two ChatGPT Pro workers at once is high risk. It is likely
> to increase throttling and can leave chats interrupted, closed, disconnected,
> or inaccessible before their outputs are recovered. Unsaved or unverified
> work may be lost. Proceed at your own risk.

Require an explicit response that acknowledges the warning and selects a
finite maximum for the current run. Persist the warning text or version, exact
maximum, acknowledgment time, and scope. Do not infer acknowledgment from a
general request for speed, parallel research, or a previously accepted run.
A higher maximum, a new run, or materially changed provider/control conditions
requires a new acknowledgment. The acknowledgment does not bypass visible
provider limits, route capacity, authorization, or other launch gates.

If more than two conversations are already active or outcome-unknown without a
valid acknowledgment, continue safe observation and artifact recovery but
launch no additional worker. Never automatically close an existing chat,
discard a generation, or submit a duplicate to get under the limit. A user may
change the stored maximum at any time; the change applies only to future
launches and does not stop or retask active lanes. Do not offer `unlimited`.

In user-facing shorthand: **Never auto-close existing chats.** Report the
active or unknown count conservatively, and apply a changed limit only to
future launches. The warning means that unsaved or unverified work may be lost.

## Blind review

For blind or adversarial review:

- provide the evidence needed to perform the review but omit prior conclusions
  unless they are part of the object being reviewed;
- state the review question and acceptance standard;
- prohibit the reviewer from assuming unseen context;
- have the integration owner compare findings against the accepted source set;
- disagreement triggers investigation, not automatic rejection or acceptance.

## Correction loop

Use a correction turn in the original conversation for a bounded defect when:

- the exact rejected candidate is preserved;
- the defect and required repair are specific;
- the worker can reuse established context safely;
- the prompt freezes all unaffected content;
- the returned candidate will be fully revalidated.

Start fresh for major recalculation, new research, lost provenance, context
corruption, repeated noncompliance, or a required independent review.
