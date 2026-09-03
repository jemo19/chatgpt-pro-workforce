---
entity_type: capability-report
run_id: "{{RUN_ID}}"
created_at: "{{ISO_8601}}"
selected_route: "{{ROUTE}}"
---

# Capability report — {{RUN_ID}}

## Preflight identity

- Preflight ID: `{{PREFLIGHT_ID}}`
- Level: `{{INITIAL_BASELINE|INVOCATION_GATE|FAULT_DIAGNOSTIC|FULL_RECHECK}}`
- Trigger: `{{FIRST_INVOCATION|EVERY_INVOCATION|RESUME|CONTROL_FAULT|CONFIGURATION_CHANGE|POST_SETUP}}`
- Started / completed: {{ISO_8601}} / {{ISO_8601_OR_PENDING}}
- Result: `{{PASS|DEGRADED|BLOCKED}}`
- Previous / current route: `{{ROUTE_OR_UNKNOWN}}` / `{{ROUTE_OR_UNKNOWN}}`
- Capability delta: {{DELTA_OR_NONE_OBSERVED}}
- Read-only gate preserved: `{{yes|no_with_reason}}`

## Host

- Surface: `{{desktop-app|cli|ide|cloud|other}}`
- OS/distribution: `{{VALUE}}`
- Desktop environment: `{{VALUE_OR_UNKNOWN}}`
- Display protocol: `{{wayland|x11|xwayland|unknown}}`
- Browser: `{{VALUE_OR_UNKNOWN}}`
- Workspace/admin restrictions observed: `{{VALUE_OR_NONE}}`

## Discovered control interfaces

| Exact discovered name | Layer/class | State | Session/target compatibility | Safe probe effect | Authorization boundary | Verified this session |
|---|---|---|---|---|---|---|
| `{{ADAPTER}}` | `{{CLASS}}` | `{{STATE}}` | {{COMPATIBILITY}} | {{READ_ONLY_OR_REVERSIBLE_EFFECT}} | {{BOUNDARY}} | {{ISO_8601_OR_NO}} |

## Workload prerequisite readiness

Use setup states only here: `NOT_NEEDED`, `READY`, `MISSING`, `OFFERED`,
`AWAITING_APPROVAL`, `IN_PROGRESS`, `MANUAL_ACTION_REQUIRED`, `VERIFIED`,
`FAILED`, `DECLINED`, or `BLOCKED`.

| Workload action | Requirement | Exact interface | Capability state | Setup state | Manual/reduced route | Setup ID / plan path |
|---|---|---|---|---|---|---|
| {{ACTION}} | `{{required|optional|not-needed}}` | `{{EXACT_NAME_OR_NONE}}` | `{{CAPABILITY_STATE}}` | `{{SETUP_STATE}}` | {{ALTERNATIVE_OR_NONE}} | `{{SETUP_ID_OR_NONE}}` / `{{PATH_OR_NONE}}` |

## Capability matrix

Allowed states only: `AVAILABLE_VERIFIED`, `AVAILABLE_UNTESTED`,
`NOT_AVAILABLE`, `DISABLED`, `NOT_AUTHORIZED`, `MISCONFIGURED`, `DEGRADED`,
`UNKNOWN`. User reports and historical success belong in evidence, not State.

| ID | Capability | State | Probe | Evidence / limitation |
|---|---|---|---|---|
| C01 | Local file and shell access | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C02 | Skill/tool discovery | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C03 | Authenticated ChatGPT session | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C04 | Native built-in browser control | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C05 | Chrome/compatible signed-in control | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C06 | Intended ChatGPT tab identification | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C07 | Multiple conversation/tab distinction | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C08 | Semantic page inspection | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C09 | Composer targeting | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C10 | New-conversation creation | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C11 | Existing-conversation reuse | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C12 | File upload | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C13 | Native attachment download | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C14 | Browser-managed download | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C15 | Screenshot capture | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C16 | Download-directory discovery | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C17 | Native Computer Use | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C18 | Third-party semantic browser adapter | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C19 | Linux accessibility control | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C20 | Explicit window enumeration/targeting | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C21 | Keyboard/mouse input synthesis | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C22 | Independent focus verification | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C23 | Manual native-dialog handoff | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C24 | Hashing and archive validation | `{{STATE}}` | {{PROBE}} | {{EVIDENCE}} |
| C25 | ChatGPT Pro account entitlement | `{{STATE}}` | {{PROBE}} | {{SAFE_VISIBLE_ENTITLEMENT_EVIDENCE}} |
| C26 | Target conversation Pro model and maximum thinking power | `{{STATE}}` | {{PROBE}} | {{DECLARED_MODEL_SELECTED_AND_PRO_5_OF_5_EVIDENCE}} |

## ChatGPT Pro submission evidence

Repeat this record for each submission attempt. Account-level evidence does not
replace target-conversation mode evidence.

| Lane | Target conversation identity | Account entitlement | Declared model / selected state | Thinking-power label | Reopen postcondition | Observation | Verified at | Submission allowed |
|---|---|---|---|---|---|---|---|---|
| `{{LANE_ID}}` | {{SAFE_IDENTITY}} | `{{AVAILABLE_VERIFIED|OTHER_CAPABILITY_STATE}}` | {{MODEL_AND_SELECTED_STATE_OR_UNKNOWN}} | {{PRO_5_OF_5_OR_OBSERVED_VALUE_OR_UNKNOWN}} | {{CLOSED_REOPENED_AND_REREAD_OR_UNKNOWN}} | `{{PRO_MAX_POWER_VERIFIED|PRO_LOWER_POWER|PRO_MODEL_NOT_SELECTED|PRO_UNAVAILABLE|PRO_AMBIGUOUS|PRO_LIMITED_OR_FALLBACK|UNKNOWN}}` | {{ISO_8601}} | `{{yes|no}}` |

## Platform support stack

Use the current-OS record names from
`references/platform-control-stacks.md`. Do not copy a simulated or another-
platform state into this report.

| Platform record | Exact interface | State | Required/optional/not needed | Current-session evidence or limitation |
|---|---|---|---|---|
| `{{RECORD_ID}}` | `{{EXACT_DISCOVERED_NAME_OR_NONE}}` | `{{STATE}}` | `{{REQUIREDNESS}}` | {{EVIDENCE}} |

On Linux, include `LINUX_SIGNED_IN_CHROME`, `LINUX_COMPUTER_USE_MCP`,
`LINUX_CHROME_DEVTOOLS_MCP`, and `LINUX_PLAYWRIGHT_EXTENSION`. On macOS or
Windows, include every browser plus desktop/accessibility, window/focus,
screenshot, input, and manual-consent record required by the platform reference.

## Screenshot capture geometry

Write `NOT_NEEDED` when no screenshot or visual work is planned.

- Capture surface: `{{page|element|content-viewport|browser-window|application-window|display-region|NOT_NEEDED}}`
- Target identity/region: {{TARGET_OR_NOT_NEEDED}}
- Capture timestamp/sequence: {{VALUE_OR_NOT_NEEDED}}
- Outer browser/window dimensions: `{{WIDTH_X_HEIGHT_OR_UNKNOWN_OR_NOT_NEEDED}}`
- Content viewport dimensions: `{{WIDTH_X_HEIGHT_OR_UNKNOWN_OR_NOT_NEEDED}}`
- Device scale: `{{VALUE_OR_UNKNOWN_OR_NOT_NEEDED}}`
- Chrome automation/debugging/control infobar: `{{present|absent|unknown|not-applicable}}`
- Top inset consumed by browser chrome/infobar: `{{PIXELS_OR_DESCRIPTION_OR_NONE}}`
- Applied crop: {{CROP_OR_NONE}}
- Portal/scale limitation: {{LIMITATION_OR_NONE}}
- Browser chrome excluded from application-defect review: `{{yes|not-applicable}}`

## Selected route

`{{FULL_BROWSER_AND_DESKTOP|BROWSER_ONLY|BROWSER_WITH_MANUAL_DESKTOP|MANUAL_BROWSER_HANDOFF|LOCAL_CODEX_ONLY|BLOCKED}}`

Rationale: {{RATIONALE}}

## Desktop-action plan

Write `NOT_NEEDED` when browser semantics cover the run.

| Action ID | Browser-gap evidence | Selected layer/method | Target proof | Focus proof | Expected postcondition | Max attempts | Fallback/stop |
|---|---|---|---|---|---|---:|---|
| `{{ACTION_ID}}` | {{GAP_OR_NOT_NEEDED}} | {{LAYER_METHOD}} | {{TARGET_EVIDENCE}} | {{FOCUS_EVIDENCE_OR_NOT_REQUIRED}} | {{POSTCONDITION}} | 2 | {{FALLBACK_OR_STOP}} |

Allowed action outcomes only: `NOT_ATTEMPTED`, `VERIFIED_SUCCEEDED`,
`VERIFIED_FAILED`, `OUTCOME_UNKNOWN`, `MANUAL_HANDOFF`, `BLOCKED`.

## Resumable desktop-action evidence

| Action ID | Attempt | Timestamp | Target continuity | Action outcome | Postcondition evidence | Exact error | Next safe route |
|---|---:|---|---|---|---|---|---|
| `{{ACTION_ID}}` | {{1_OR_2}} | {{ISO_8601}} | {{EVIDENCE}} | `{{OUTCOME}}` | {{EVIDENCE}} | {{ERROR_OR_NONE}} | {{NEXT_ROUTE}} |

- Unrelated window/tab/application state retained: `none`
- Sensitive or broad screenshots retained: `none`

## Troubleshooting findings

- {{SYMPTOM_CLASSIFICATION_REPROBE_AND_STOP_OR_NONE}}

### Control-fault diagnostic, when applicable

- Diagnostic ID / trigger: `{{ID_OR_NONE}}` / {{TRIGGER_OR_NONE}}
- Frozen submissions and desktop input: `{{yes|no|not-applicable}}`
- Browser chain result: {{CONTROLLER_TARGET_COMPOSER_SCREENSHOT_UPLOAD_DOWNLOAD_RESULT}}
- Desktop chain result: {{ADAPTER_WINDOW_TREE_FOCUS_SCREENSHOT_RESULT_OR_NOT_NEEDED}}
- Repair / count: {{BOUNDED_NONDESTRUCTIVE_REPAIR_OR_NONE}} / `{{0|1}}`
- Postcondition and duplicate reconciliation: {{RESULT_OR_NONE}}
- Final disposition: `{{RESOLVED|MANUAL_HANDOFF|SETUP_REQUIRED|BLOCKED|NOT_APPLICABLE}}`

## Approvals intentionally not inferred

- {{APPROVAL_OR_NONE}}

## Expected limitations

- {{LIMITATION_OR_NONE}}

## Re-probe triggers

- every skill invocation performs a proportional read-only gate;
- first invocation or missing/untrusted baseline;
- browser or MCP reconnect;
- new, reused, resumed, rebound, or reloaded ChatGPT conversation;
- model/mode control change or provider limit/fallback notice;
- desktop-session/display-protocol change;
- adapter update or configuration change;
- repeated target-selection, upload, download, or screenshot failure;
- new privilege or approval boundary.
