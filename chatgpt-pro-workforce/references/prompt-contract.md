# Worker prompt contract

Every worker prompt must be self-contained and testable. Use the templates in
`assets/` rather than composing a vague request directly in the browser.

## Mandatory fields

Include, as applicable:

1. **Identity** — project, run, iteration, and lane IDs.
2. **Role** — the worker's bounded function.
3. **Objective** — one precise outcome.
4. **Authoritative inputs** — exact filenames, hashes, versions, attachments,
   URLs, or embedded content.
5. **Context** — only what is needed to understand the task.
6. **Exclusions** — explicit non-goals and out-of-scope areas.
7. **Allowed actions** — research, analysis, generation, or review actually
   permitted.
8. **Prohibited actions** — deployment, messaging, purchases, account changes,
   secret access, repository mutation, or other unauthorized actions.
9. **Evidence rules** — acceptable source types, citation granularity, source
   hierarchy, and contradiction handling.
10. **Temporal/version boundary** — current date, as-of time, data cutoff,
    software version, or immutable parent identity.
11. **Output contract** — exact filenames, format, encoding, schema, ordering,
    and required sections.
12. **Mechanical acceptance** — parsers, counts, checksums, validators, markers,
    and forbidden extras.
13. **Semantic acceptance** — factual support, calculation correctness,
    completeness, uncertainty, and rights/licensing requirements.
14. **Provenance** — how sources, transformations, and artifact lineage must be
    recorded.
15. **Known gaps** — facts or files that must not be fabricated.
16. **Completion marker** — unique exact marker placed only after all outputs
    exist.
17. **Recovery path** — native attachment preferred; bounded fallback if native
    recovery fails.
18. **No false completion** — explicit instruction not to claim success unless
    every required artifact exists and has been checked.
19. **Discovery proposal policy** — when first-pass coverage discovery is in
    scope, exact proposal fields and an instruction not to pursue additions.
20. **Visual capture context** — for screenshot/visual lanes, the capture
    surface, target region, outer-window versus content-viewport dimensions,
    device scale, crop, and any Chrome automation/debugging-infobar inset. Tell
    the worker not to classify browser chrome or its aspect-ratio effect as an
    application defect.

## Prompt types

Use:

- `assets/worker-prompt-template.md` for initial work or continuation;
- `assets/review-prompt-template.md` for independent or blind review;
- `assets/correction-prompt-template.md` for deterministic repair, diagnostic
  recovery, major correction, or recalculation;
- a synthesis variant of the worker template for accepted packets only.

## Attachment truth

A browser worker cannot see a local path merely because Codex can. The prompt
must state which inputs are actually attached, pasted, or available at a public
or authorized URL. Before submission, verify that every referenced attachment
is visibly present in the target conversation.

## Prompt finalization

For material work:

- render the exact final prompt to a local Markdown file;
- hash it;
- record the hash and path in lane state;
- verify the composer contains the intended prompt once, with no stale text;
- submit once;
- never edit the stored prompt after submission; create a new revision instead.

## First-pass discovery proposal contract

When a lane may discover missing topics or categories, the prompt must state
the run's expansion policy and require proposals with stable IDs. Each proposal
contains topic, relevance, evidence exposing the gap, likely value, expected
cost/overlap, proposed lane, and exclusions.

The worker must not research, synthesize, or produce artifacts for a proposed
addition unless the prompt already identifies it as approved under the stored
policy. Under `ASK_BEFORE_ADDING`, all proposals remain pending for Codex and
the user. Under `AUTO_ADD_IN_SCOPE`, anything crossing a permission, sensitive
input, system, consequential-action, or material-scope boundary remains pending.
