# ChatGPT Pro correction / recovery prompt

## Identity

- Project: `{{PROJECT_ID}}`
- Run: `{{RUN_ID}}`
- Iteration: `{{NEW_ITERATION_ID}}`
- Lane: `{{LANE_ID}}`
- Parent candidate: `{{PARENT_FILENAME_AND_SHA256}}`

## Correction type

`{{deterministic-repair|semantic-repair|major-recalculation|continuation|diagnostic|transport-recovery}}`

## Controlling evidence

The prior candidate and reviewer/validator evidence are immutable inputs:

- {{PARENT_ARTIFACT}}
- {{EXACT_VALIDATOR_OR_REVIEW_OUTPUT}}

## Exact defect to repair

{{ONE_BOUNDED_DEFECT_OR_EXPLICIT_DEFECT_LIST}}

## Freeze boundary

Preserve all unaffected claims, records, ordering, filenames, authority limits,
and conservative blockers unless the controlling evidence requires a stricter
result.

Do not:

- broaden scope;
- restart unrelated research;
- mutate the immutable parent in place;
- hide or delete contradictory evidence;
- claim that a rejected parent was accepted;
- make unrequested stylistic changes.

## Required repair

1. {{REPAIR_STEP_1}}
2. {{REPAIR_STEP_2}}
3. {{REPAIR_STEP_3}}

## Required outputs

Produce exactly:

- `{{OUTPUT_FILENAME}}`
- {{ADDITIONAL_OUTPUT_OR_NONE}}

## Acceptance

Mechanical:

- {{MECHANICAL_CHECK}}

Semantic:

- {{SEMANTIC_CHECK}}

Provide a concise change log that maps every changed location to the controlling
defect. Attach native files. End only after all outputs exist with:

```text
{{LANE_ID}}_CORRECTION_STATUS=COMPLETE
```

Otherwise return `PARTIAL` and identify exact remaining blockers.
