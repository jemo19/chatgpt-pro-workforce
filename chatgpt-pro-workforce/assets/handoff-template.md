---
id: "{{HANDOFF_ID}}"
entity_type: handoff
project_id: "{{PROJECT_ID}}"
run_id: "{{RUN_ID}}"
status: "{{STATUS}}"
max_concurrent_pro_workers: "{{FINITE_INTEGER_DEFAULT_2}}"
created_at: "{{ISO_8601}}"
---

# Handoff — {{RUN_ID}}

## Requested outcome

{{OUTCOME}}

## Current status

`{{DRAFT|READY|ACTIVE|PAUSING|PAUSED|LIMIT_PAUSED|RESUMING|PARTIAL|BLOCKED|ACCEPTED|REJECTED|STOPPED|SUPERSEDED}}`

- Aggregate run state: `{{PATH}}`
- Allocation profile: `{{PRO_HEAVY|BALANCED|CODEX_HEAVY|LOCAL_ONLY}}`
- Qualitative Codex-usage band: `{{LOWEST|MODERATE|HIGH|CODEX_ONLY}}`
- Allocation effective at / future-work rule: {{ISO_8601}} / `preserve-active-lane-ownership`
- Scope expansion policy: `{{ASK_BEFORE_ADDING|AUTO_ADD_IN_SCOPE|FIXED_SCOPE}}`
- Reporting cadence: `{{VERBOSE|STANDARD|QUIET}}`
- Last status freshness/as-of: `{{CURRENT|STALE|UNKNOWN}}` — {{ISO_8601}}
- Pause reason: `{{NONE|USER_REQUEST|USAGE_LIMIT|CONTROL_LOSS|EXTERNAL_BLOCKER}}`
- Provider-shown reset / resume-not-before: {{VALUE_OR_NONE}}
- Healthy workers possibly still active: `{{yes|no|unknown}}`
- Maximum simultaneous Pro workers / active-or-unknown count: `{{FINITE_INTEGER_DEFAULT_2}}` / `{{NONNEGATIVE_INTEGER_OR_UNKNOWN}}`
- Concurrency gate / acknowledged exact maximum: `{{OPEN|HIGH_RISK_ACK_REQUIRED|ACKNOWLEDGED_FOR_EXACT_LIMIT|CAPACITY_BLOCKED|UNKNOWN}}` / `{{FINITE_INTEGER_OR_NONE}}`
- High-risk acknowledgment time/scope: {{ISO_8601_OR_NONE}} / `{{CURRENT_RUN_EXACT_LIMIT_OR_NONE}}`

## Capability route

- Preflight report: [[{{CAPABILITY_REPORT}}]]
- Last invocation preflight ID / level / trigger / result: `{{ID}}` / `{{INITIAL_BASELINE|INVOCATION_GATE|FAULT_DIAGNOSTIC|FULL_RECHECK}}` / `{{FIRST_INVOCATION|EVERY_INVOCATION|RESUME|CONTROL_FAULT|CONFIGURATION_CHANGE|POST_SETUP}}` / `{{PASS|DEGRADED|BLOCKED}}`
- Capability delta / last verified route: {{DELTA_OR_NONE_OBSERVED}} / `{{ROUTE_OR_UNKNOWN}}`
- Selected route: `{{ROUTE}}`
- Workload prerequisite status: `{{STATUS}}`
- Prerequisite setup ID / plan: `{{SETUP_ID_OR_NONE}}` / `{{PATH_OR_NONE}}`
- Remaining setup/manual action: {{ACTION_OR_NONE}}
- Screenshot geometry/Chrome-infobar limitation: {{DETAIL_OR_NOT_APPLICABLE}}
- Current limitations: {{LIMITATIONS}}
- Control-fault diagnostic / repair count / disposition: `{{ID_OR_NONE}}` / `{{0|1}}` / `{{RESOLVED|MANUAL_HANDOFF|SETUP_REQUIRED|BLOCKED|NOT_APPLICABLE}}`

## Lane inventory

| Lane | Mode | Conversation | Status | Next action |
|---|---|---|---|---|
| [[{{LANE_ID}}]] | {{MODE}} | {{URL}} | {{STATUS}} | {{NEXT_ACTION}} |

## Artifact inventory

| Artifact | Raw path | Candidate path | Bytes | SHA-256 | Gate disposition |
|---|---|---|---:|---|---|
| `{{NAME}}` | `{{RAW_PATH}}` | `{{CANDIDATE_PATH}}` | {{BYTES}} | `{{HASH}}` | `{{DISPOSITION}}` |

## Storage, cleanup, and notes

- Run-owned download root / manifest: `{{PATH}}` / `{{PATH}}`
- Retention / cleanup status / plan: `{{POLICY}}` / `{{STATUS}}` / `{{PATH_OR_NONE}}`
- Cleanup outcomes: {{RETAINED_TRASHED_DELETED_SKIPPED_FAILED_OR_NONE}}
- Note policy / vault / research root: `{{POLICY}}` / `{{PATH_OR_NOT_APPLICABLE}}` / `{{PATH_OR_NOT_APPLICABLE}}`
- Locator source / recommended path / confirmation: `{{SOURCE_OR_NONE}}` / `{{PATH_OR_NONE}}` / `{{CONFIRMED|REJECTED|PENDING|NOT_APPLICABLE}}`
- Topic slug / folder / index: `{{SLUG_OR_NONE}}` / `{{PATH_OR_NONE}}` / `{{PATH_OR_NONE}}`
- Native artifacts indexed without duplication: `{{yes|no|not-applicable}}`

## Local dashboard

- Policy / dedicated root: `{{DISABLED|ON_DEMAND|ENABLED}}` / `{{PATH_OR_NOT_APPLICABLE}}`
- Health / checked at: `{{HEALTHY|UNHEALTHY|STOPPED|UNKNOWN|DISABLED}}` / {{ISO_8601_OR_NEVER}}
- Verified URL / snapshot time/hash: `{{URL_OR_NONE}}` / {{ISO_8601_OR_NEVER}} / `{{HASH_OR_NONE}}`
- Managed process/session identity and stop/restart caution: {{IDENTITY_OR_NONE}}

## Verification performed

### Mechanical

{{COMMANDS_AND_RESULTS}}

### Semantic

{{ASSERTIONS_AND_RESULTS}}

### Independent Codex work

{{INDEPENDENT_CHECKS}}

## Rejected or unresolved material

- {{ITEM}}

## Recovery attempts not to repeat

- {{ATTEMPT_AND_REASON}}

## Exact next action

{{NEXT_ACTION}}

- Required resume prechecks: {{CHECKS_OR_NONE}}
- Detailed status: `$chatgpt-pro-workforce tell me more {{RUN_ID}}`
- Dashboard: `$chatgpt-pro-workforce dashboard {{RUN_ID}}`
- Change allocation: `$chatgpt-pro-workforce change allocation {{RUN_ID}}`
- Change concurrency: `$chatgpt-pro-workforce change concurrency {{RUN_ID}}`

## User decision or approval required

{{NONE_OR_EXACT_DECISION}}
