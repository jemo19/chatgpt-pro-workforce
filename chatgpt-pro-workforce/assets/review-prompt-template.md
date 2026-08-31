# Independent ChatGPT Pro review prompt

## Identity

- Project: `{{PROJECT_ID}}`
- Run: `{{RUN_ID}}`
- Review lane: `{{LANE_ID}}`
- Review type: `{{blind|adversarial|visual|code|document|source-rights|semantic}}`

## Role

Act as an independent reviewer. Do not assume the candidate is correct merely
because it passed a structural checker or was produced by another model.

## Review object

Review only these exact inputs:

- {{CANDIDATE_FILE_OR_ATTACHMENT_WITH_HASH}}
- {{CONTROLLING_SPEC_OR_ACCEPTANCE_CRITERIA}}
- {{AUTHORIZED_EVIDENCE_SET}}

Do not invent repository state, sources, files, tests, or prior decisions that
are not provided.

## Visual capture context (when applicable)

- Capture surface: `{{page|element|content-viewport|browser-window|application-window|display-region|not-applicable}}`
- Review target/region: {{TARGET_REGION_OR_NOT_APPLICABLE}}
- Outer window: `{{WIDTH_X_HEIGHT_OR_UNKNOWN}}`
- Content viewport: `{{WIDTH_X_HEIGHT_OR_UNKNOWN}}`
- Device scale: `{{VALUE_OR_UNKNOWN}}`
- Chrome automation/debugging/control infobar: `{{present|absent|unknown|not-applicable}}`
- Top inset/crop: `{{PIXELS_OR_DESCRIPTION_OR_NONE}}`

For a visual review, evaluate the stated content region. Do not classify
browser chrome, an automation infobar, or its aspect-ratio effect as a defect
in the reviewed application.

## Blinding policy

{{STATE_WHICH_PRIOR_CONCLUSIONS_ARE_WITHHELD_OR_INCLUDED}}

## Review questions

1. {{QUESTION_1}}
2. {{QUESTION_2}}
3. {{QUESTION_3}}

## Required evidence

- Cite exact file/line, page/region, record/field, source, or calculation for
  every material finding.
- Separate observed fact from inference and preference.
- Give concrete counterexamples and kill criteria where relevant.
- Preserve contradictory evidence.

## Finding classes

Classify every item as one of:

- `FATAL`
- `MATERIAL_REPAIRABLE`
- `MINOR`
- `UNCERTAINTY`
- `SUGGESTION`
- `NOT_A_DEFECT`

Include severity, confidence, evidence, impact, and smallest valid repair.

## Verdict

Return one:

- `ACCEPT`
- `ACCEPT_WITH_LIMITATIONS`
- `REJECT_MECHANICAL`
- `REJECT_SEMANTIC`
- `PARTIAL_REVIEW`

Do not edit or regenerate the candidate. End with:

```text
{{LANE_ID}}_REVIEW_STATUS={{VERDICT}}
```
