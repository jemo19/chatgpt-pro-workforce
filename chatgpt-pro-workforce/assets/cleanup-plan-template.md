---
entity_type: workforce-cleanup-plan
run_id: "{{RUN_ID}}"
cleanup_id: "{{CLEANUP_ID}}"
cleanup_status: "{{DRAFT|AWAITING_APPROVAL|AUTHORIZED|IN_PROGRESS|PARTIAL|COMPLETE|BLOCKED|DECLINED}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# Artifact cleanup — {{CLEANUP_ID}}

## Boundary and policy

- Dedicated run-owned root: `{{PATH}}`
- Storage policy: `{{POLICY}}`
- Retention policy: `{{POLICY}}`
- Cleanup approval policy: `{{POLICY}}`
- Cleanup method: `{{TRASH|PERMANENT_DELETE|NO_ACTION}}`
- Accepted artifact export and hash verified: `{{yes|no|not-applicable}}`
- Handoff/index links verified: `{{yes|no|not-applicable}}`
- Active process check: `{{CLEAR|IN_USE|UNKNOWN}}`

## Exact cleanup target manifest

| Artifact ID | Exact resolved path | Bytes | SHA-256 | Ownership | Current disposition | Proposed action | Reason |
|---|---|---:|---|---|---|---|---|
| `{{ID}}` | `{{PATH}}` | {{BYTES}} | `{{HASH}}` | `{{task-owned|exact-browser-return}}` | `{{raw|candidate|rejected|duplicate|temporary}}` | `{{RETAIN|TRASH|DELETE}}` | {{REASON}} |

- Proposed retained bytes: {{BYTES}}
- Proposed removed bytes: {{BYTES}}
- Raw evidence retention decision: {{DECISION_AND_REASON}}
- Symlinks, directories, globs, traversal, or out-of-root targets: `none`

## Authorization

- Exact manifest shown at: {{ISO_8601_OR_PENDING}}
- Authorization: `{{PENDING|APPROVED_EXACT_MANIFEST|APPROVED_RUN_OWNED_TEMP_POLICY|DECLINED}}`
- Authorization evidence/scope: {{EVIDENCE_OR_NONE}}
- New or broader target encountered: `{{yes|no}}`

## Outcome

| Artifact ID | Attempted at | Outcome | Postcondition evidence | Exact error / next action |
|---|---|---|---|---|
| `{{ID}}` | {{ISO_8601_OR_NOT_RUN}} | `{{RETAINED|TRASHED|DELETED|SKIPPED|FAILED|NOT_RUN}}` | {{EVIDENCE}} | {{ERROR_OR_NEXT_ACTION}} |

- Bytes retained: {{BYTES}}
- Bytes trashed/deleted: {{BYTES}}
- Unknown outcomes: `none`
- Resume reconciliation required: {{ITEMS_OR_NONE}}
