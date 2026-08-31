---
id: "{{ITERATION_ID}}"
entity_type: iteration
project_id: "{{PROJECT_ID}}"
run_id: "{{RUN_ID}}"
status: "{{STATUS}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
part_of:
  - "[[{{PROJECT_NOTE}}]]"
---

# {{ITERATION_ID}} — {{TITLE}}

## Purpose and scope

{{PURPOSE}}

## Capability preflight

- Report: [[{{CAPABILITY_REPORT}}]]
- Selected route: `{{ROUTE}}`
- Limitations: {{LIMITATIONS}}

## Lanes

| Lane | Mode | Conversation | Status | Owner | Output |
|---|---|---|---|---|---|
| [[{{LANE_ID}}]] | {{MODE}} | {{URL}} | {{STATUS}} | {{OWNER}} | {{OUTPUT}} |

## Inputs

- {{INPUT_WITH_HASH_OR_VERSION}}

## Progress history

| Timestamp | Lane | Observation | Classification | Action |
|---|---|---|---|---|
| {{ISO_8601}} | {{LANE_ID}} | {{OBSERVATION}} | {{STATE}} | {{ACTION}} |

## Gate results

### Mechanical

{{COMMANDS_AND_EXACT_RESULTS}}

### Semantic

{{ASSERTIONS_AND_RESULTS}}

## Accepted, rejected, and unresolved

- Accepted: {{ITEMS}}
- Rejected: {{ITEMS}}
- Unresolved: {{ITEMS}}

## Next action

{{NEXT_ACTION}}
