# Evidence and verification

## Contents

- [Mechanical gate](#mechanical-gate)
- [Semantic gate](#semantic-gate)
- [Independent verification](#independent-verification)
- [Immutable-candidate rule](#immutable-candidate-rule)
- [Local repair boundary](#local-repair-boundary)
- [Dispositions](#dispositions)

Every worker output is provisional until both the applicable mechanical and
semantic gates pass.

## Mechanical gate

Check, as applicable:

- required files exist;
- filenames, encoding, and schemas match;
- JSON, CSV, Markdown, or other formats parse;
- row, record, page, or archive-member counts reconcile;
- checksums and byte counts are correct;
- archives pass integrity checks;
- no forbidden extra members exist;
- completion markers are exact and unique;
- required project validators and tests pass;
- validator commands and exact outputs are recorded.

A zero-error structural checker does not prove semantic correctness.

For a completed-research explorer, mechanical acceptance also checks the
embedded schema and run ID, internal finding/source references, offline asset
boundary, safe relative artifact links, keyboard-visible interaction, print
layout, and stable post-validation hash. Semantic acceptance compares the
rendered summary, findings, confidence, contradictions, limitations, and
recommendations with the same accepted source packet; attractive presentation
never upgrades evidence.

## Semantic gate

Check, as applicable:

- each material claim is supported by its cited evidence;
- citations entail the whole claim, not merely a nearby topic;
- source identity, author/publisher, date, event date, version, and retrieval
  date are correct;
- units, clocks, timestamps, rounding, and calculations are sound;
- there is no look-ahead, temporal leakage, or version substitution;
- contradictions and negative evidence are represented;
- licensing, rights, access, and permitted-use statements are sourced;
- requested scope is genuinely complete;
- uncertainty is calibrated;
- no access, test, execution, or result is fabricated.

## Independent verification

Codex must review output in proportion to risk. For material research, medical,
legal, financial, security, infrastructure, or production-impacting claims:

- verify against current authoritative sources;
- recompute calculations or representative samples;
- inspect original artifacts rather than relying on a worker summary;
- reproduce material code findings where possible;
- use an independent reviewer when confirmation bias or context contamination is
  a concern.

## Immutable candidate rule

When acceptance depends on exact bytes:

1. freeze one candidate;
2. hash it;
3. run the mechanical gate against those bytes;
4. run the semantic gate against the same bytes;
5. rehash after all checks;
6. prohibit post-validation mutation;
7. store validator evidence with the candidate hash.

## Local repair boundary

Codex may make a small local repair only when it is deterministic,
provenance-preserving, and authorized, for example:

- formatting that does not alter meaning;
- an obvious filename or manifest correction;
- rebuilding an index from accepted underlying data;
- fixing a broken internal link;
- adding a hash derivable from exact bytes.

Attempt at most one local repair for the same candidate defect. Freeze the
repaired bytes under a new identity and rerun every invalidated mechanical and
semantic check. A second failure returns to the responsible worker or becomes
an explicit blocker; it is not permission for iterative local reinterpretation.

Return work to the worker for:

- major recalculation;
- new source research;
- missing provenance reconstruction;
- material reinterpretation;
- broad missing sections;
- contradiction resolution;
- replacement of fabricated or unsuitable evidence;
- regeneration of large structured output.

Never silently repair a rejected packet and call it the worker's accepted
original. Preserve parent, rejected, repaired, and accepted identities.

## Dispositions

Use:

- `ACCEPTED`
- `ACCEPTED_WITH_LIMITATIONS`
- `REJECTED_MECHANICAL`
- `REJECTED_SEMANTIC`
- `PARTIAL`
- `BLOCKED`
- `NOT_RECOVERABLE`
- `NOT_AVAILABLE`
- `SUPERSEDED`

The final report must state checks run, checks not run, exact failures, and the
current disposition.
