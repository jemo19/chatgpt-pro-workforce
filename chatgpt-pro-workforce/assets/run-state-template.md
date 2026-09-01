---
entity_type: workforce-run
schema_version: 2
run_id: "{{RUN_ID}}"
run_status: "{{DRAFT|READY|ACTIVE|PAUSING|PAUSED|LIMIT_PAUSED|RESUMING|PARTIAL|BLOCKED|ACCEPTED|REJECTED|STOPPED|SUPERSEDED}}"
allocation_profile: "{{PRO_HEAVY|BALANCED|CODEX_HEAVY|LOCAL_ONLY}}"
codex_usage_band: "{{LOWEST|MODERATE|HIGH|CODEX_ONLY}}"
max_concurrent_pro_workers: "{{FINITE_INTEGER_DEFAULT_2}}"
scope_expansion_policy: "{{ASK_BEFORE_ADDING|AUTO_ADD_IN_SCOPE|FIXED_SCOPE}}"
first_pass_discovery: "{{NOT_REQUESTED|PLANNED|RUNNING|READY_FOR_DECISION|DECIDED|SKIPPED}}"
reporting_cadence: "{{VERBOSE|STANDARD|QUIET}}"
status_freshness: "{{CURRENT|STALE|UNKNOWN}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# Workforce run state — {{RUN_ID}}

## Outcome and controls

- Requested outcome: {{OUTCOME}}
- Workforce profile: `{{PATH}}`
- Kickoff brief: `{{PATH}}`
- Capability report: `{{PATH_OR_PENDING}}`
- Selected route: `{{ROUTE_OR_PENDING}}`
- Workload prerequisite status: `{{READY|MISSING|OFFERED|AWAITING_APPROVAL|IN_PROGRESS|MANUAL_ACTION_REQUIRED|VERIFIED|FAILED|DECLINED|BLOCKED|NOT_NEEDED}}`
- Prerequisite setup ID / plan: `{{SETUP_ID_OR_NONE}}` / `{{PATH_OR_NONE}}`
- Screenshot capture geometry: {{SURFACE_OUTER_VIEWPORT_SCALE_INFOBAR_INSET_CROP_OR_NOT_APPLICABLE}}
- Allocation rationale: {{RATIONALE}}
- Allocation effective at / applies to: {{ISO_8601}} / `future-work-only`
- Prior allocation / change reason: `{{PROFILE_OR_NONE}}` / {{REASON_OR_NONE}}
- Maximum simultaneous Pro workers: `{{FINITE_INTEGER_DEFAULT_2}}`
- Active or outcome-unknown Pro conversations: `{{NONNEGATIVE_INTEGER_OR_UNKNOWN}}`
- Proposed post-launch count: `{{NONNEGATIVE_INTEGER_OR_NOT_APPLICABLE}}`
- Concurrency gate: `{{OPEN|HIGH_RISK_ACK_REQUIRED|ACKNOWLEDGED_FOR_EXACT_LIMIT|CAPACITY_BLOCKED|UNKNOWN}}`
- High-risk warning version / acknowledged maximum: `{{VERSION_OR_NONE}}` / `{{FINITE_INTEGER_OR_NONE}}`
- High-risk acknowledgment time / scope: {{ISO_8601_OR_NONE}} / `{{CURRENT_RUN_EXACT_LIMIT_OR_NONE}}`
- Last compact status: {{ISO_8601_OR_NOT_EMITTED}}
- Last detailed status: {{ISO_8601_OR_NOT_EMITTED}}

## Invocation readiness

- Preflight ID: `{{PREFLIGHT_ID}}`
- Level / trigger: `{{INITIAL_BASELINE|INVOCATION_GATE|FAULT_DIAGNOSTIC|FULL_RECHECK}}` / `{{FIRST_INVOCATION|EVERY_INVOCATION|RESUME|CONTROL_FAULT|CONFIGURATION_CHANGE|POST_SETUP}}`
- Started / completed: {{ISO_8601}} / {{ISO_8601_OR_PENDING}}
- Result: `{{PASS|DEGRADED|BLOCKED}}`
- Previous / last verified route: `{{ROUTE_OR_UNKNOWN}}` / `{{ROUTE_OR_UNKNOWN}}`
- Capability delta: {{DELTA_OR_NONE_OBSERVED}}
- Current-session evidence path: `{{PATH}}`

## Control-fault diagnostic

- Diagnostic ID / trigger: `{{ID_OR_NONE}}` / {{TRIGGER_OR_NONE}}
- Frozen submissions/input: `{{yes|no|not-applicable}}`
- Affected capability chain: {{CAPABILITIES_OR_NONE}}
- Evidence before/after: {{EVIDENCE_OR_NONE}}
- Bounded repair / count: {{REPAIR_OR_NONE}} / `{{0|1}}`
- Postcondition and duplicate reconciliation: {{RESULT_OR_NONE}}
- Final route / disposition: `{{ROUTE_OR_UNKNOWN}}` / `{{RESOLVED|MANUAL_HANDOFF|SETUP_REQUIRED|BLOCKED|NOT_APPLICABLE}}`

## Scope registry

| Scope ID | Topic/category | Origin | Decision | Work state | Acceptance | Evidence or reason |
|---|---|---|---|---|---|---|
| `{{SCOPE_ID}}` | {{TOPIC}} | `{{INITIAL|DISCOVERED}}` | `{{PENDING|APPROVED|DEFERRED|REJECTED}}` | `{{NOT_STARTED|IN_PROGRESS|ADDRESSED|BLOCKED}}` | `{{NOT_REVIEWED|ACCEPTED|REJECTED}}` | {{EVIDENCE}} |

## Discovery proposals

| Discovery ID | Topic/category | Evidence gap | Likely value | Cost/overlap | Proposed lane | Decision |
|---|---|---|---|---|---|---|
| `{{DISCOVERY_ID}}` | {{TOPIC}} | {{EVIDENCE}} | {{VALUE}} | {{COST_AND_OVERLAP}} | `{{LANE_ID_OR_NONE}}` | `{{PENDING|APPROVED|DEFERRED|REJECTED}}` |

## Lane registry

| Lane ID | Mode | Conversation policy | Lane state path | Current disposition | Last observed | Next action |
|---|---|---|---|---|---|---|
| `{{LANE_ID}}` | `{{MODE}}` | `{{POLICY}}` | `{{PATH}}` | `{{STATE}}` | {{ISO_8601}} | {{NEXT_ACTION}} |

## Progress registry

Bars are derived only from the registered units below.

| Category | Numerator | Denominator | Basis | Previous ratio | Scope/change note |
|---|---:|---:|---|---|---|
| Scope | {{N}} | {{N_OR_UNKNOWN}} | Approved scope items addressed | {{RATIO_OR_NONE}} | {{CHANGE_OR_NONE}} |
| Workers | {{N}} | {{N_OR_UNKNOWN}} | Terminal non-superseded lanes | {{RATIO_OR_NONE}} | {{CHANGE_OR_NONE}} |
| Artifacts | {{N}} | {{N_OR_UNKNOWN}} | Exact expected artifacts recovered | {{RATIO_OR_NONE}} | {{CHANGE_OR_NONE}} |
| Validation | {{N}} | {{N_OR_UNKNOWN}} | Required checks passed | {{RATIO_OR_NONE}} | {{CHANGE_OR_NONE}} |
| Acceptance | {{N}} | {{N_OR_UNKNOWN}} | Required acceptance units satisfied | {{RATIO_OR_NONE}} | {{CHANGE_OR_NONE}} |

## Artifact and gate registry

| ID | Expected object/check | Path or command | SHA-256 or evidence | Disposition |
|---|---|---|---|---|
| `{{ID}}` | {{OBJECT}} | `{{PATH_OR_COMMAND}}` | {{HASH_OR_EVIDENCE}} | `{{EXPECTED|RECOVERED|PASS|FAIL|ACCEPTED|REJECTED|NOT_RUN}}` |

## Artifact storage and cleanup

- Storage policy / root: `{{DEDICATED_RUN_FOLDER|USER_SELECTED_ROOT|TEMPORARY_WITH_ACCEPTED_EXPORT|USER_MANAGED}}` / `{{PATH}}`
- Run download directory: `{{PATH}}`
- Browser staging / accepted export: `{{PATH_OR_CONTROLLER_MANAGED}}` / `{{PATH}}`
- Retention policy: `{{REVIEW_BEFORE_DELETE|KEEP_ALL|KEEP_ACCEPTED_ONLY|DELETE_TEMP_AFTER_ACCEPTANCE|USER_MANAGED}}`
- Cleanup status / plan: `{{NOT_PLANNED|PLANNED|AWAITING_APPROVAL|APPROVED|IN_PROGRESS|COMPLETE|PARTIAL|BLOCKED|DECLINED}}` / `{{PATH_OR_NONE}}`
- Cleanup authorization: {{ISO_8601_AND_SCOPE_OR_NONE}}
- Manifest and outcomes: {{EXACT_HASH_BOUND_FILES_AND_RETAINED_TRASHED_DELETED_SKIPPED_FAILED_OR_NONE}}

## Research notes

- Note policy: `{{NO_NOTES|ASK_EACH_RUN|YES_EXISTING_ROOT|CREATE_RESEARCH_ROOT_AFTER_APPROVAL}}`
- Vault / research root: `{{PATH_OR_NOT_APPLICABLE}}` / `{{PATH_OR_NOT_APPLICABLE}}`
- Locator source / recommendation / confirmation: `{{PROJECT_INSTRUCTION|OPEN_REGISTRY|REGISTRY|BOUNDED_MARKER|USER_SUPPLIED|NONE}}` / `{{PATH_OR_NONE}}` / `{{CONFIRMED|REJECTED|PENDING|NOT_APPLICABLE}}`
- Topic slug / folder: `{{SLUG_OR_PENDING}}` / `{{PATH_OR_PENDING}}`
- Topic-folder creation authority: `{{approved-within-confirmed-root|ask-each-topic|not-authorized}}`
- Native artifact store / index: `{{PATH_OR_NOT_APPLICABLE}}` / `{{PATH_OR_NOT_APPLICABLE}}`
- Last note path: `{{PATH_OR_NONE}}`

## Local status dashboard

- Policy: `{{DISABLED|ON_DEMAND|ENABLED}}`
- Dedicated root / run directory: `{{PATH_OR_NOT_APPLICABLE}}` / `{{PATH_OR_NOT_APPLICABLE}}`
- Bind / port / URL: `127.0.0.1` / `{{PORT_OR_NONE}}` / `{{VERIFIED_URL_OR_NONE}}`
- Managed process/session identity: {{IDENTITY_OR_NONE}}
- Health / checked at: `{{HEALTHY|UNHEALTHY|STOPPED|UNKNOWN|DISABLED}}` / {{ISO_8601_OR_NEVER}}
- Snapshot updated at / SHA-256: {{ISO_8601_OR_NEVER}} / `{{HASH_OR_NONE}}`
- Snapshot freshness / failure: `{{CURRENT|STALE|UNKNOWN}}` / {{ERROR_OR_NONE}}

## Completed research explorer

- Policy / status: `{{ALWAYS|ASK_AT_COMPLETION|DISABLED}}` / `{{NOT_PLANNED|PLANNED|BUILT|VERIFIED|ACCEPTED|REJECTED|BLOCKED|NOT_APPLICABLE}}`
- Accepted data path / SHA-256: `{{PATH_OR_NONE}}` / `{{HASH_OR_NONE}}`
- Template SHA-256: `{{HASH_OR_NONE}}`
- Run-owned HTML path / SHA-256: `{{PATH_OR_NONE}}` / `{{HASH_OR_NONE}}`
- Human-facing export path / SHA-256: `{{PATH_OR_NONE}}` / `{{HASH_OR_NONE}}`
- Companion JSON path / SHA-256: `{{PATH_OR_NONE}}` / `{{HASH_OR_NONE}}`
- Mechanical / semantic result: `{{NOT_RUN|PASS|FAIL|BLOCKED}}` / `{{NOT_RUN|PASS|FAIL|BLOCKED}}`
- Next action: {{ACTION_OR_NONE}}

## Pause, capacity, and resume

- Pause reason: `{{NONE|USER_REQUEST|USAGE_LIMIT|CONTROL_LOSS|EXTERNAL_BLOCKER}}`
- Healthy workers possibly still active: `{{yes|no|unknown}}`
- Safe visible capacity evidence: {{EVIDENCE_OR_NONE}}
- Reset time shown by provider: {{ISO_8601_OR_UNKNOWN}}
- Resume not before: {{ISO_8601_OR_NONE}}
- Last durable checkpoint: {{ISO_8601}}
- Reconciliation required before input: {{ITEMS_OR_NONE}}
- Failed approaches not to repeat: {{ITEMS_OR_NONE}}
- Exact resume cursor: {{NEXT_SAFE_ACTION}}
- Prerequisite reconciliation before resume: {{NONE_OR_SETUP_STATE_REPREFLIGHT_AND_MANUAL_STEP}}

## Pending user decisions

- {{DECISION_OR_NONE}}

## Visible controls

- Compact status: `$chatgpt-pro-workforce status {{RUN_ID}}`
- Detailed status: `$chatgpt-pro-workforce tell me more {{RUN_ID}}`
- Dashboard: `$chatgpt-pro-workforce dashboard {{RUN_ID}}`
- Change allocation: `$chatgpt-pro-workforce change allocation {{RUN_ID}}`
- Change concurrency: `$chatgpt-pro-workforce change concurrency {{RUN_ID}}`
- Pause: `$chatgpt-pro-workforce pause {{RUN_ID}}`
- Resume: `$chatgpt-pro-workforce resume {{RUN_ID}}`
- Export research explorer: `$chatgpt-pro-workforce export explorer {{RUN_ID}}`
- Help: `$chatgpt-pro-workforce help`
