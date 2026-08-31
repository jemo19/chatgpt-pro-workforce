---
id: "{{RESEARCH_NOTE_ID}}"
entity_type: research
project_id: "{{PROJECT_ID}}"
run_id: "{{RUN_ID}}"
iteration_id: "{{ITERATION_ID}}"
topic_slug: "{{TOPIC_SLUG}}"
topic_folder: "{{TOPIC_FOLDER}}"
status: "{{STATUS}}"
created_at: "{{ISO_8601}}"
updated_at: "{{ISO_8601}}"
part_of:
  - "[[{{PROJECT_OR_ITERATION_NOTE}}]]"
generated_by:
  - "[[{{LANE_NOTE}}]]"
---

# {{TITLE}}

- Research root: `{{RESEARCH_ROOT}}`
- Topic index: [[{{TOPIC_INDEX_NOTE}}]]
- Research index: [[{{RESEARCH_INDEX_NOTE}}]]
- Note policy / creation authority: `{{POLICY}}` / `{{AUTHORITY}}`

## Question

{{BOUNDED_RESEARCH_QUESTION}}

## Evidence standard

{{STANDARD}}

## Accepted findings

| Finding ID | Claim | Evidence | Confidence | Limitations |
|---|---|---|---|---|
| {{ID}} | {{CLAIM}} | [[{{SOURCE_NOTE}}]] | {{CONFIDENCE}} | {{LIMITATION}} |

## Rejected claims

| Claim | Reason rejected | Evidence |
|---|---|---|
| {{CLAIM}} | {{REASON}} | [[{{SOURCE_OR_REVIEW_NOTE}}]] |

## Contradictions

{{CONTRADICTIONS_OR_NONE}}

## Open questions

- {{OPEN_QUESTION}}

## Native artifacts

- Path: `{{PATH}}`
- Stored in: `{{NATIVE_ARTIFACT_STORE}}`
- SHA-256: `{{HASH}}`
- Role: {{ROLE}}
- Disposition: `{{DISPOSITION}}`

## Next action

{{NEXT_ACTION}}

This note must be linked from the topic and research indexes. Index native
artifacts by path, size, hash, role, and disposition; do not duplicate their
contents into Markdown.
