# Operating model

## Authority

ChatGPT Pro browser conversations are bounded external workers, not authorities.
Codex owns scope, permissions, prompt construction, lane ownership, control
targeting, artifact recovery, validation, integration, lineage, and acceptance.

Every run begins with project/durable-state inspection and a decision about
whether external workers add enough value to justify transfer and verification.
Simple, tightly coupled, or local-mutation-heavy work stays with Codex.

## Modes

The skill supports eight modes:

- research;
- visual review;
- code review;
- document review;
- data/calculation;
- adversarial review;
- synthesis;
- artifact production.

A run can use multiple modes, but each lane has one bounded outcome, stable ID,
input packet, output contract, conversation, and owner. Only one writer owns a
file or module scope. Blind review uses a fresh conversation; corrections and
continuations normally stay in the same conversation unless its state is
contaminated or repeatedly failing.

Durable state has one active writer and a monotonic revision. Before typing a
worker prompt, Codex records a send intent with the lane, conversation, attempt,
and prompt hash. It then records the observed result as acknowledged, not sent,
or outcome unknown. A timeout is never treated as proof that nothing happened.
Linux can enforce this through the bundled transactional helper. macOS,
Windows, and failed-helper routes use single-writer immutable, hash-chained
revision files and stop browser input if ownership or commit verification is
not available.

## Pro/Codex allocation

The user can change the allocation for future work at any time:

| Profile | ChatGPT Pro role | Relative Codex usage |
|---|---|---|
| Pro-heavy | Most bounded research, drafting, analysis, and artifacts | Lowest |
| Balanced | Parallel research and specialist review with Codex integration | Moderate |
| Codex-heavy | Narrow specialist or adversarial lanes | High |
| Local-only | No external workers | Codex only |

Codex's permission, verification, integration, and acceptance duties never move
to a worker.

## Concurrency

Two simultaneous ChatGPT Pro workers is the safe default. Active and
outcome-unknown conversations count against the limit. A lower user, project,
or route ceiling always wins.

A proposed third-or-later worker is suppressed until the user acknowledges the
full throttling/chat-loss warning for an exact finite limit in the current run.
There is no unlimited setting. Lowering the limit affects future launches and
never closes an existing chat automatically.

## Evidence and acceptance

Worker prompts are complete, self-contained packets. Returned artifacts are
preserved immutably before transformation and inventoried with size and SHA-256.
Acceptance has separate gates:

1. Mechanical validation: presence, format, archive safety, links, schema,
   hashes, and deterministic checks.
2. Semantic validation: relevance, correctness, source support, omissions,
   consistency, and fit to the requested outcome.
3. Independent Codex verification: reproduce important claims, calculations,
   or behavior without treating worker confidence as proof.

Small deterministic repairs may be local. Material corrections go back to the
responsible worker with preserved evidence and a bounded correction prompt.

Archive intake is bounded before extraction. Unsafe names, traversal, aliases,
duplicates, symlinks, special files, encrypted entries, excessive expansion,
and compression-ratio bombs are rejected. A durable intake intent is written
before raw or extracted bytes so interrupted and rejected material remains
traceable. Cleanup uses an exact recorded plan and rechecks identity and hash
immediately before moving a run-owned file into recoverable quarantine.

## Pause and resume

Pause stops new submissions and waits for a durable checkpoint; it does not
interrupt healthy workers merely because they are slow. Usage limits produce a
limit-paused state with the provider's displayed reset time when one exists.

Resume re-reads durable run/lane state, refreshes readiness, reconciles active
and outcome-unknown conversations, suppresses duplicate prompt hashes, verifies
artifacts, and continues from the recorded next action. Context compaction or a
fresh Codex turn does not require recreating worker lanes from memory.
