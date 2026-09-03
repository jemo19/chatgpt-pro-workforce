---
entity_type: lane
run_id: "{{RUN_ID}}"
iteration_id: "{{ITERATION_ID}}"
lane_id: "{{LANE_ID}}"
mode: "{{MODE}}"
status: "{{STATUS}}"
owner: "{{OWNER}}"
selected_route: "{{ROUTE}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# Lane {{LANE_ID}} state

## Objective

{{OBJECTIVE}}

## Conversation and prompt

- Conversation URL: {{URL_OR_NOT_CREATED}}
- Safe tab/window identity: {{IDENTITY_OR_UNKNOWN}}
- Conversation policy: `{{same|fresh|blind|manual}}`
- Prompt path: `{{PATH}}`
- Prompt SHA-256: `{{HASH}}`
- Submitted at: {{ISO_8601_OR_NOT_SUBMITTED}}

## ChatGPT Pro submission gate

- Account entitlement state/evidence: `{{CAPABILITY_STATE}}` / {{SAFE_VISIBLE_EVIDENCE}}
- Target conversation model/power state: `{{CAPABILITY_STATE}}`
- Declared model / selected-state proof: {{MODEL_AND_CURRENT_SELECTED_CHECKED_STATE_OR_UNKNOWN}}
- Thinking-power control / observed label: {{CONTROL_IDENTITY_AND_PRO_5_OF_5_OR_OBSERVED_VALUE}}
- Selector close/reopen postcondition: {{REREAD_RESULT_OR_UNKNOWN}}
- Pro observation: `{{PRO_MAX_POWER_VERIFIED|PRO_LOWER_POWER|PRO_MODEL_NOT_SELECTED|PRO_UNAVAILABLE|PRO_AMBIGUOUS|PRO_LIMITED_OR_FALLBACK|UNKNOWN}}`
- Verified at / target conversation: {{ISO_8601_OR_NEVER}} / {{SAFE_IDENTITY_OR_UNKNOWN}}
- Gate result: `{{ALLOW_SUBMISSION|BLOCK_SUBMISSION|REVERIFY_REQUIRED}}`
- Recheck trigger: `{{NEW|REUSE|RESUME|REBIND|RELOAD|MODE_CHANGE|LIMIT_OR_FALLBACK|CONTROL_FAULT|PRE_SUBMISSION}}`

## Inputs

- {{INPUT_WITH_HASH_OR_VERSION}}

## Expected outputs

- `{{FILENAME}}` — {{ROLE}}

## Progress

- Last observed: {{ISO_8601}}
- Last progress summary: {{SUMMARY}}
- Worker state: `{{RUNNING_HEALTHY|RUNNING_WITH_TRANSIENT_ERROR|SLOW_NO_FAILURE_EVIDENCE|STALLED|BROWSER_DISCONNECTED|TERMINAL_PARTIAL_ARTIFACT_RETURN|TERMINAL_INCOMPLETE|RETURNED|OTHER}}`

## Recovered artifacts

| Raw path | Filename | Bytes | SHA-256 | Disposition |
|---|---|---:|---|---|
| `{{PATH}}` | `{{NAME}}` | {{BYTES}} | `{{HASH}}` | `{{STATUS}}` |

## Visual capture evidence

- Capture surface/target: {{SURFACE_AND_TARGET_OR_NOT_APPLICABLE}}
- Outer window / content viewport: {{OUTER_AND_VIEWPORT_OR_NOT_APPLICABLE}}
- Device scale / top inset / crop: {{SCALE_INSET_CROP_OR_NOT_APPLICABLE}}
- Chrome automation/debugging/control infobar: `{{present|absent|unknown|not-applicable}}`
- Browser chrome excluded from app findings: `{{yes|not-applicable}}`

## Desktop action evidence

- Browser-semantic limitation: {{NOT_NEEDED_OR_EXACT_GAP}}
- Desktop action ID: `{{NOT_NEEDED_OR_ACTION_ID}}`
- Adapter/method: {{NOT_NEEDED_OR_EXACT_NAME}}
- Attempt: `{{NOT_RUN|1|2}}`
- Target/focus precheck: {{NOT_RUN_OR_EVIDENCE}}
- Bounded action: {{NOT_RUN_OR_ACTION}}
- Action outcome: `{{NOT_ATTEMPTED|VERIFIED_SUCCEEDED|VERIFIED_FAILED|OUTCOME_UNKNOWN|MANUAL_HANDOFF|BLOCKED}}`
- Semantic postcondition: {{NOT_RUN_OR_RESULT}}
- Next safe route: {{NOT_NEEDED_OR_ROUTE}}
- Unrelated desktop state retained: `none`

## Gate results

- Mechanical: `{{NOT_RUN|PASS|FAIL}}` — {{EVIDENCE}}
- Semantic: `{{NOT_RUN|PASS|FAIL}}` — {{EVIDENCE}}

## Recovery and retries

- Retry count: {{N}}
- Failure classification: `{{NONE_OR_CLASS}}`
- Failed approaches not to repeat: {{ITEMS}}

## Next action

{{NEXT_ACTION}}
