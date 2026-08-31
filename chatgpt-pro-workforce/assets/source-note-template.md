---
id: "{{SOURCE_ID}}"
entity_type: source
status: "{{STATUS}}"
source_type: "{{primary|official|paper|dataset|secondary|other}}"
title: "{{TITLE}}"
author_or_publisher: "{{AUTHOR_OR_PUBLISHER}}"
publication_date: "{{DATE_OR_UNKNOWN}}"
event_date: "{{DATE_OR_NOT_APPLICABLE}}"
version: "{{VERSION_OR_UNKNOWN}}"
retrieved_at: "{{ISO_8601}}"
url: "{{URL_OR_LOCAL_PATH}}"
supports:
  - "[[{{CLAIM_OR_FINDING_ID}}]]"
contradicts:
  - "[[{{CLAIM_OR_FINDING_ID_OR_NONE}}]]"
---

# {{SOURCE_ID}} — {{SHORT_TITLE}}

## Identity and access

- Canonical URL/path: {{URL_OR_PATH}}
- Access state: `{{AVAILABLE|PAYWALLED|LICENSED|INACCESSIBLE|LOCAL}}`
- Rights/licensing note: {{SOURCED_RIGHTS_FACT_OR_NOT_ESTABLISHED}}
- Archived/captured at: {{CAPTURE_PATH_OR_NONE}}

## Relevant evidence

{{BOUNDED_EXCERPT_OR_STRUCTURED_FACTS}}

## Claim mapping

| Claim ID | Relationship | Exact support or contradiction | Limitations |
|---|---|---|---|
| {{CLAIM_ID}} | {{supports|contradicts|context-only}} | {{ENTAILMENT}} | {{LIMITATION}} |

## Reliability notes

{{METHOD_VERSION_TEMPORAL_AND_BIAS_NOTES}}
