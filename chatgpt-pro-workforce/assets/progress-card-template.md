# Workforce progress cards

## Compact card

Use ten cells only for a finite registered denominator. Use `[active] —/—`
when the denominator is unknown.

```text
{{RUN_ID}} · {{RUN_STATUS}} · {{ALLOCATION_PROFILE}} · Codex use {{LOWEST|MODERATE|HIGH|CODEX_ONLY}} · as of {{ISO_8601}} · {{CURRENT|STALE|UNKNOWN}}

Scope       {{BAR_OR_ACTIVE}}  {{N}}/{{DENOMINATOR_OR_DASH}}  {{SHORT_BASIS}}
Workers     {{BAR_OR_ACTIVE}}  {{N}}/{{DENOMINATOR_OR_DASH}}  {{SHORT_BASIS}}
Artifacts   {{BAR_OR_ACTIVE}}  {{N}}/{{DENOMINATOR_OR_DASH}}  {{SHORT_BASIS}}
Validation  {{BAR_OR_ACTIVE}}  {{N}}/{{DENOMINATOR_OR_DASH}}  {{SHORT_BASIS}}
Acceptance  {{BAR_OR_ACTIVE}}  {{N}}/{{DENOMINATOR_OR_DASH}}  {{SHORT_BASIS}}

Now: {{ACTIVE_WAITING_OR_PAUSED_SUMMARY}}
Concurrency: max {{FINITE_INTEGER_DEFAULT_2}} · active/unknown {{NONNEGATIVE_INTEGER_OR_UNKNOWN}} {{GATE_OR_WARNING_WHEN_RELEVANT}}
Prerequisite: {{READY_OR_BLOCKING_SETUP_MANUAL_DECISION}}
Next: {{NEXT_SAFE_ACTION_OR_USER_DECISION}}
{{DENOMINATOR_CHANGE_OR_NONE}}

{{DASHBOARD_LINE_ONLY_WHEN_CURRENT_HEALTH_CHECK_SUCCEEDED}}
More: $chatgpt-pro-workforce tell me more {{RUN_ID}}
Controls: $chatgpt-pro-workforce pause {{RUN_ID}} · $chatgpt-pro-workforce resume {{RUN_ID}} · $chatgpt-pro-workforce change allocation {{RUN_ID}} · $chatgpt-pro-workforce change concurrency {{RUN_ID}} · $chatgpt-pro-workforce help
```

Example finite bar shapes:

```text
0/10  ░░░░░░░░░░
3/10  ███░░░░░░░
7/10  ███████░░░
10/10 ██████████
```

The filled-cell count is always
`floor(10 * numerator / denominator)`. Omit non-applicable categories; do not
replace unknown denominators with guessed values.

Render the dashboard line exactly as
`Dashboard: http://127.0.0.1:<PORT>/runs/<RUN_ID>/` only after the exact server
passes a current health check. Otherwise omit the whole line; never show a dead
or remembered URL. `More:` remains visible in either case.

## Detailed card

```markdown
# Detailed workforce status — {{RUN_ID}}

- Run state: `{{RUN_STATUS}}`
- Status freshness/as-of: `{{CURRENT|STALE|UNKNOWN}}` — {{ISO_8601}}
- Requested outcome: {{OUTCOME}}
- Allocation / qualitative Codex use: `{{ALLOCATION_PROFILE}}` / `{{LOWEST|MODERATE|HIGH|CODEX_ONLY}}` — {{RATIONALE_AND_USAGE_CAVEAT}}
- Capability route: `{{ROUTE}}`
- Invocation preflight: `{{ID}}` / `{{LEVEL}}` / `{{TRIGGER}}` / `{{PASS|DEGRADED|BLOCKED}}`; delta {{DELTA_OR_NONE_OBSERVED}}
- Prerequisite readiness: `{{SETUP_STATE}}` — {{SETUP_ID_PLAN_OR_MANUAL_ROUTE}}
- Screenshot geometry/Chrome-infobar limitation: {{DETAIL_OR_NOT_APPLICABLE}}
- Scope expansion: `{{POLICY}}`; first pass `{{DISCOVERY_STATE}}`
- Reporting cadence: `{{VERBOSE|STANDARD|QUIET}}`
- Pro concurrency: max `{{FINITE_INTEGER_DEFAULT_2}}`; active-or-unknown `{{NONNEGATIVE_INTEGER_OR_UNKNOWN}}`; gate `{{OPEN|HIGH_RISK_ACK_REQUIRED|ACKNOWLEDGED_FOR_EXACT_LIMIT|CAPACITY_BLOCKED|UNKNOWN}}`; acknowledgment {{EXACT_LIMIT_TIME_SCOPE_OR_NONE}}

## Progress basis

| Category | Ratio/state | Registered basis | Change since prior card |
|---|---|---|---|
| Scope | {{RATIO_OR_ACTIVE}} | {{BASIS}} | {{CHANGE_OR_NONE}} |
| Workers | {{RATIO_OR_ACTIVE}} | {{BASIS}} | {{CHANGE_OR_NONE}} |
| Artifacts | {{RATIO_OR_ACTIVE}} | {{BASIS}} | {{CHANGE_OR_NONE}} |
| Validation | {{RATIO_OR_ACTIVE}} | {{BASIS}} | {{CHANGE_OR_NONE}} |
| Acceptance | {{RATIO_OR_ACTIVE}} | {{BASIS}} | {{CHANGE_OR_NONE}} |

## Lanes

| Lane | Mode | Worker state | Last observed | Latest evidence | Next action |
|---|---|---|---|---|---|
| `{{LANE_ID}}` | `{{MODE}}` | `{{STATE}}` | {{ISO_8601}} | {{EVIDENCE}} | {{NEXT_ACTION}} |

## Scope and discovered topics

- Approved scope addressed: {{ITEMS}}
- Pending discovery decisions: {{ITEMS_OR_NONE}}
- Deferred/rejected additions: {{ITEMS_OR_NONE}}

## Artifacts, gates, and acceptance

- Recovered artifacts and hashes: {{ITEMS_OR_NONE}}
- Mechanical checks: {{RESULTS}}
- Semantic checks: {{RESULTS}}
- Independent Codex verification: {{RESULTS}}
- Conflicts, rejected material, or unresolved gaps: {{ITEMS_OR_NONE}}

## Pause, capacity, and recovery

- Pause reason: `{{REASON}}`
- Capacity/reset evidence: {{EVIDENCE_OR_NONE}}
- Reconciliation or approaches not to repeat: {{ITEMS_OR_NONE}}
- Required approval or user decision: {{ITEMS_OR_NONE}}
- Control-fault diagnostic/repair: {{ID_EVIDENCE_COUNT_AND_DISPOSITION_OR_NONE}}

## Storage, notes, and local dashboard

- Download root / retention / cleanup: `{{PATH}}` / `{{POLICY}}` / `{{STATUS_AND_PLAN_OR_NONE}}`
- Notes / research topic: `{{POLICY}}` / `{{ROOT_TOPIC_INDEX_OR_NOT_APPLICABLE}}`
- Dashboard: `{{DISABLED|ON_DEMAND|ENABLED}}` / `{{HEALTHY|UNHEALTHY|STOPPED|UNKNOWN|DISABLED}}` / {{VERIFIED_URL_OR_NONE}}
- Dashboard snapshot / server lifetime: {{UPDATED_AT_HASH_OR_NONE}} / `best-effort-current-host-session`

## Next safe action

{{NEXT_SAFE_ACTION}}

Compact status: `$chatgpt-pro-workforce status {{RUN_ID}}`
Dashboard: `$chatgpt-pro-workforce dashboard {{RUN_ID}}`
Change allocation: `$chatgpt-pro-workforce change allocation {{RUN_ID}}`
Change concurrency: `$chatgpt-pro-workforce change concurrency {{RUN_ID}}`
Pause/resume help: `$chatgpt-pro-workforce help resume`
```
