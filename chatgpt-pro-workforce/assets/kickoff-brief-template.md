---
entity_type: workforce-kickoff
run_id: "{{RUN_ID}}"
status: "{{DRAFT|READY|STARTED|BLOCKED|SUPERSEDED}}"
max_concurrent_pro_workers: "{{FINITE_INTEGER_DEFAULT_2}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# Workforce kickoff — {{RUN_ID}}

## Outcome

- Requested result: {{RESULT}}
- Audience/use: {{AUDIENCE_OR_USE}}
- Completion criteria: {{CRITERIA}}
- Time, freshness, or deadline: {{REQUIREMENT_OR_NONE}}

## Inputs and boundaries

- Supplied inputs: {{PATHS_URLS_ARTIFACTS_OR_NONE}}
- Still needed: {{ITEMS_OR_NONE}}
- Exclusions/non-goals: {{EXCLUSIONS}}
- Privacy/customer/licensing/production constraints: {{CONSTRAINTS_OR_NONE}}

## Recommended approach

- Mode(s): `{{MODES}}`
- Why this mode set: {{RATIONALE}}
- Work allocation: `{{PRO_HEAVY|BALANCED|CODEX_HEAVY|LOCAL_ONLY}}`
- Qualitative Codex-usage band: `{{LOWEST|MODERATE|HIGH|CODEX_ONLY}}`
- Allocation rationale: {{RATIONALE}}
- Usage caveat shown: `actual usage varies; no token/quota/time/cost promise`
- Allocation change rule: `changeable-any-time; future-work-only; preserve-active-lanes`
- External-worker value: `{{MATERIAL|MARGINAL|NONE}}`
- Recommended execution: `{{WORKFORCE|LOCAL_CODEX_ONLY}}`
- Maximum simultaneous Pro workers: `{{FINITE_INTEGER_DEFAULT_2}}`
- Current active or outcome-unknown count: `{{NONNEGATIVE_INTEGER_OR_UNKNOWN}}`
- High-risk concurrency acknowledgment: `{{NOT_REQUIRED|PENDING|ACKNOWLEDGED_CURRENT_RUN_EXACT_LIMIT}}`

## Discovery and reporting preferences

- Scope expansion: `{{ASK_BEFORE_ADDING|AUTO_ADD_IN_SCOPE|FIXED_SCOPE|NOT_APPLICABLE}}`
- First-pass discovery: `{{NOT_REQUESTED|PLANNED|SKIPPED}}`
- Reporting cadence: `{{VERBOSE|STANDARD|QUIET}}`
- Aggregate run-state path: `{{PATH}}`
- Workforce profile path: `{{PATH}}`
- Visible help: `$chatgpt-pro-workforce help`

## Local storage, notes, and dashboard

- Download storage policy / run root: `{{POLICY}}` / `{{PATH_OR_PENDING}}`
- Retention / cleanup approval: `{{POLICY}}` / `{{ASK_FOR_EXACT_MANIFEST|EXPLICIT_RUN_OWNED_TEMP_POLICY|NO_CLEANUP}}`
- Note policy / research root: `{{NO_NOTES|ASK_EACH_RUN|YES_EXISTING_ROOT|CREATE_RESEARCH_ROOT_AFTER_APPROVAL}}` / `{{PATH_OR_PENDING_OR_NOT_APPLICABLE}}`
- Obsidian locator source / recommended path / confirmation: `{{SOURCE_OR_NONE}}` / `{{PATH_OR_NONE}}` / `{{CONFIRMED|REJECTED|PENDING|NOT_APPLICABLE}}`
- Topic slug / folder authority: `{{SLUG_OR_PENDING}}` / `{{approved-within-confirmed-root|ask-each-topic|not-authorized}}`
- Dashboard policy / dedicated root: `{{DISABLED|ON_DEMAND|ENABLED}}` / `{{PATH_OR_PENDING_OR_NOT_APPLICABLE}}`
- Dashboard startup / current health: `{{AUTHORIZED|ON_DEMAND|DISABLED}}` / `{{HEALTHY|UNHEALTHY|STOPPED|UNKNOWN|DISABLED}}`

## Lane plan

| Lane ID | Objective | Conversation policy | Inputs | Deliverable | Independent check |
|---|---|---|---|---|---|
| `{{LANE_ID}}` | {{OBJECTIVE}} | `{{fresh|same|blind|manual}}` | {{INPUTS}} | {{OUTPUT}} | {{CHECK}} |

- Parallel/blind-review rule: {{RULE_OR_NONE}}
- File/module writers: {{OWNERSHIP_OR_NOT_APPLICABLE}}

## Control and permissions

- Capability report: `{{PATH_OR_PENDING}}`
- Invocation preflight ID / level / trigger / result: `{{ID}}` / `{{INITIAL_BASELINE|INVOCATION_GATE|FULL_RECHECK}}` / `{{FIRST_INVOCATION|EVERY_INVOCATION|RESUME|CONFIGURATION_CHANGE|POST_SETUP}}` / `{{PASS|DEGRADED|BLOCKED}}`
- Capability delta / last verified route: {{DELTA_OR_NONE_OBSERVED}} / `{{ROUTE_OR_UNKNOWN}}`
- Proposed route: `{{FULL_BROWSER_AND_DESKTOP|BROWSER_ONLY|BROWSER_WITH_MANUAL_DESKTOP|MANUAL_BROWSER_HANDOFF|LOCAL_CODEX_ONLY|BLOCKED|PENDING_PREFLIGHT}}`
- Workload prerequisite status: `{{READY|MISSING|OFFERED|AWAITING_APPROVAL|IN_PROGRESS|MANUAL_ACTION_REQUIRED|VERIFIED|FAILED|DECLINED|BLOCKED|NOT_NEEDED}}`
- Prerequisite setup ID / plan: `{{SETUP_ID_OR_NONE}}` / `{{PATH_OR_NONE}}`
- Missing required / optional layers: {{LAYERS_OR_NONE}}
- Exact desktop action, if any: {{ACTION_OR_NONE}}
- Manual handoff, if any: {{HANDOFF_OR_NONE}}
- Authorized actions: {{ACTIONS}}
- Actions not authorized or still requiring confirmation: {{ACTIONS_OR_NONE}}
- Screenshot capture geometry/infobar limitation: {{DETAIL_OR_NOT_APPLICABLE}}

## Deliverables and acceptance

- Deliverables: {{FILES_OR_RESULTS}}
- Mechanical checks: {{CHECKS}}
- Semantic checks: {{CHECKS}}
- Independent Codex verification: {{METHOD}}

## Ready-to-start summary

- Open decisions: {{DECISIONS_OR_NONE}}
- Recommended next action: {{NEXT_ACTION}}
- User start decision: `{{PENDING|START|REVISE|STOP}}`
- Detailed-status intent: `$chatgpt-pro-workforce tell me more {{RUN_ID}}`
- Dashboard intent: `$chatgpt-pro-workforce dashboard {{RUN_ID}}`
- Allocation-change intent: `$chatgpt-pro-workforce change allocation {{RUN_ID}}`
- Concurrency-change intent: `$chatgpt-pro-workforce change concurrency {{RUN_ID}}`
