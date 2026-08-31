---
entity_type: workforce-prerequisite-plan
run_id: "{{RUN_ID}}"
setup_id: "{{SETUP_ID}}"
setup_status: "{{NOT_NEEDED|READY|MISSING|OFFERED|AWAITING_APPROVAL|IN_PROGRESS|MANUAL_ACTION_REQUIRED|VERIFIED|FAILED|DECLINED|BLOCKED}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
---

# Prerequisite setup — {{SETUP_ID}}

## Workload need and current evidence

- Target host/surface: {{TARGET}}
- Platform/session: {{OS_DESKTOP_DISPLAY_OR_BROWSER_CONTEXT}}
- Planned workload requiring this capability: {{WORKLOAD}}
- Capability ID/layer: {{CAPABILITY}}
- Exact discovered interface or missing layer: {{INTERFACE_OR_NONE}}
- Current capability state: `{{STATE}}`
- Read-only evidence: {{EVIDENCE}}
- Manual or reduced route available: {{ROUTE_OR_NONE}}

## Proposed bounded change

- Trusted source/current documentation: {{SOURCE}}
- Exact package/extension/component/version or setting: {{CHANGE}}
- Exact files/configuration/services affected: {{TARGETS}}
- Exact commands or manual UI changes: {{COMMANDS_OR_STEPS}}
- Network/download effects: {{EFFECTS_OR_NONE}}
- Administrator/elevation required: `{{yes|no|unknown}}`
- Native user action required: {{ACTION_OR_NONE}}
- Requested permissions/privacy grants: {{PERMISSIONS_OR_NONE}}
- Least-privilege alternative considered: {{ALTERNATIVE}}

## Security and authority

- Security impact: {{IMPACT}}
- Controls that will not be weakened: {{BOUNDARIES}}
- Explicit approvals received: {{APPROVALS_OR_NONE}}
- Approvals still required: {{APPROVALS_OR_NONE}}
- Approval scope and timestamp: {{SCOPE_AND_ISO_8601_OR_PENDING}}
- Credentials/secrets retained: `none`

## Validation

- Before-state evidence: {{EVIDENCE}}
- Harmless readiness probe: {{PROBE}}
- Disposable functional test: {{TEST_OR_NOT_AUTHORIZED}}
- Success criteria: {{CRITERIA}}
- Post-setup full preflight path: `{{PATH}}`

## Rollback

- Exact rollback command/manual steps: {{ROLLBACK}}
- Rollback verification: {{CHECK}}
- Material data that must be preserved: {{ITEMS_OR_NONE}}

## Outcome

- Applied changes: {{CHANGES_OR_NONE}}
- Manual steps completed: {{STEPS_OR_NONE}}
- Validation result: `{{NOT_RUN|PASS|FAIL|PARTIAL}}`
- Final capability state after re-preflight: `{{STATE}}`
- Remaining limitations: {{LIMITATIONS_OR_NONE}}
- Next safe action: {{NEXT_ACTION}}
