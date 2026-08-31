---
entity_type: workforce-profile
schema_version: 2
initialization_status: "{{UNINITIALIZED|READY|NEEDS_REVIEW}}"
max_concurrent_pro_workers: "{{FINITE_INTEGER_DEFAULT_2}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# ChatGPT Pro Workforce profile

This profile stores non-secret user preferences and durable first-use state.
Treat paths as untrusted hints until checked in the current invocation.

## Initialization and readiness

- Profile scope: `{{user|project}}`
- Profile path: `{{PATH}}`
- First-use setup completed: `{{yes|no}}`
- First baseline preflight ID/path: `{{PREFLIGHT_ID}}` / `{{PATH}}`
- First baseline completed at: {{ISO_8601_OR_PENDING}}
- Last invocation-gate ID/path: `{{PREFLIGHT_ID_OR_NONE}}` / `{{PATH_OR_NONE}}`
- Last invocation gate at: {{ISO_8601_OR_NEVER}}
- Last invocation result/capability delta: `{{PASS|DEGRADED|BLOCKED|UNKNOWN}}` / {{SUMMARY_OR_NONE}}
- Last verified route: `{{ROUTE_OR_UNKNOWN}}`
- Platform support-stack summary: `{{PLATFORM}}` / {{EXACT_INTERFACE_STATES_OR_PENDING}}
- Last platform-stack inventory check: {{ISO_8601_OR_NEVER}}

## Work allocation preference

- Preferred allocation: `{{PRO_HEAVY|BALANCED|CODEX_HEAVY|LOCAL_ONLY|ASK_EACH_RUN}}`
- Qualitative Codex-usage band: `{{LOWEST|MODERATE|HIGH|CODEX_ONLY|ASK_EACH_RUN}}`
- Usage caveat acknowledged: `{{yes|pending}}`
- Last preference change: {{ISO_8601_OR_NEVER}}
- Run override rule: `future-work-only; preserve active lane ownership`

## Pro worker concurrency preference

- Serialized default: `max_concurrent_pro_workers: 2`
- Default maximum simultaneous Pro workers: `2`
- Preferred maximum: `{{1|2|ASK_EACH_RUN}}`
- Values above two stored as a cross-run preference: `no`
- High-risk acknowledgment rule: `current-run-and-exact-limit-only`
- Existing chats automatically closed when lowering the limit: `no`

## Artifact storage and retention

- Storage policy: `{{DEDICATED_RUN_FOLDER|USER_SELECTED_ROOT|TEMPORARY_WITH_ACCEPTED_EXPORT|USER_MANAGED}}`
- Artifact root: `{{PATH_OR_PENDING}}`
- Browser download staging path: `{{PATH_OR_CONTROLLER_MANAGED_OR_UNKNOWN}}`
- Accepted export root: `{{PATH_OR_SAME_AS_ARTIFACT_ROOT_OR_PENDING}}`
- Retention policy: `{{REVIEW_BEFORE_DELETE|KEEP_ALL|KEEP_ACCEPTED_ONLY|DELETE_TEMP_AFTER_ACCEPTANCE|USER_MANAGED}}`
- Cleanup approval policy: `{{ASK_FOR_EXACT_MANIFEST|EXPLICIT_RUN_OWNED_TEMP_POLICY|NO_CLEANUP}}`
- Cleanup checkpoint: `{{RUN_CLOSE|SIZE_THRESHOLD|MANUAL}}`
- Size threshold, if selected: `{{BYTES_OR_NOT_APPLICABLE}}`

## Research notes

- Note policy: `{{NO_NOTES|ASK_EACH_RUN|YES_EXISTING_ROOT|CREATE_RESEARCH_ROOT_AFTER_APPROVAL}}`
- Obsidian vault root: `{{PATH_OR_NOT_APPLICABLE_OR_PENDING}}`
- Research root: `{{PATH_OR_NOT_APPLICABLE_OR_PENDING}}`
- Locator recommendation / evidence: `{{PATH_OR_NONE}}` / `{{PROJECT_INSTRUCTION|OPEN_REGISTRY|REGISTRY|BOUNDED_MARKER|USER_SUPPLIED|NONE}}`
- Safe vault ID / open flag: `{{ID_OR_NOT_RETAINED_OR_NONE}}` / `{{true|false|unknown}}`
- Locator confirmation: `{{CONFIRMED|REJECTED|PENDING|NOT_APPLICABLE}}`
- Last bounded locator run: {{ISO_8601_OR_NEVER}}
- Suggested root accepted: `{{yes|no|pending|not-applicable}}`
- Per-topic folders: `{{enabled|disabled|ask}}`
- Topic-folder creation authority: `{{approved-within-confirmed-root|ask-each-topic|not-authorized}}`
- Native artifact store: `{{PATH_OR_INDEX_EXTERNAL_ARTIFACT_ROOT_OR_PENDING}}`
- Research index path: `{{PATH_OR_PENDING}}`
- Topic layout version: `1`

## Local status dashboard

- Dashboard policy: `{{DISABLED|ON_DEMAND|ENABLED}}`
- Dedicated dashboard root: `{{PATH_OR_PENDING_OR_NOT_APPLICABLE}}`
- Current-run automatic startup authorized: `{{yes|no}}`
- Bind address: `127.0.0.1`
- Preferred port policy: `{{AUTO_FREE_LOOPBACK_PORT|FIXED_PORT_WITH_HEALTH_CHECK}}`
- External assets, telemetry, or non-loopback serving allowed: `no`
- Server lifetime expectation: `best-effort-current-host-session`

## Boundaries and review

- Credentials, cookies, tokens, and secrets retained: `none`
- Unrelated Downloads/Desktop/home content may be scanned or deleted: `no`
- Preference review triggers: {{HOST_CHANGE_PATH_UNAVAILABLE_POLICY_CHANGE_OR_OTHER}}
- Pending decisions: {{ITEMS_OR_NONE}}
