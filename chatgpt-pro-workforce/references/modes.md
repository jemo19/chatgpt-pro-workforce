# Operating modes

## Contents

- [Research](#1-research)
- [Visual review](#2-visual-review)
- [Code review](#3-code-review)
- [Document review](#4-document-review)
- [Data and calculation](#5-datacalculation)
- [Adversarial review](#6-adversarial-review)
- [Synthesis](#7-synthesis)
- [Artifact production](#8-artifact-production)

Select the smallest mode set that covers the requested outcome. A lane may use
more than one mode only when the relationship is stated in its charter.

## 1. Research

Use for broad or deep investigation across primary sources, papers, official
documentation, datasets, standards, and credible secondary sources.

Required behavior:

- define research questions and falsifiable subquestions;
- register the initially approved topics/categories as finite scope items when
  possible;
- when first-pass discovery is requested, identify meaningful missing or
  adjacent topics without pursuing them automatically;
- assign stable discovery IDs and return relevance, exposing evidence, likely
  value, cost/overlap, and a proposed lane for each suggestion;
- separate source discovery from evidence acceptance;
- preserve URL, author/publisher, publication date, event date, version, and
  retrieval date;
- prioritize primary sources;
- label inference separately from source-supported fact;
- preserve contradictory evidence and unresolved gaps;
- maintain a claim-to-source map;
- propose follow-up experiments without promoting them to findings.

Apply the run's `ASK_BEFORE_ADDING`, `AUTO_ADD_IN_SCOPE`, or `FIXED_SCOPE`
policy before turning a discovered topic into work. A worker suggestion never
expands permissions or scope authority.

Done when the scoped questions are answered to the requested evidence standard
or the remaining gaps are explicitly documented.

## 2. Visual review

Use for screenshots, websites, rendered documents, dashboards, charts, slides,
or desktop applications.

Required behavior:

- provide the exact artifact or image set;
- record capture surface, target identity, timestamp/sequence, outer-window and
  content-viewport dimensions when applicable, device scale, and crop;
- detect Chrome automation, debugging, or control infobars that consume the top
  of the window; record their inset and resulting content aspect ratio, prefer
  a page/element or content viewport capture, and do not treat browser chrome as
  an application defect;
- define review dimensions: hierarchy, legibility, accessibility, consistency,
  usability, responsive behavior, visualization integrity, and defects;
- separate observations from preference;
- give precise locations and reproducible descriptions;
- preserve before/after evidence when changes are authorized;
- require Codex or an independent reviewer to verify material visible claims.

## 3. Code review

Use for diffs, modules, architecture packets, tests, or proposed changes.

Required behavior:

- provide repository context, exact scope, relevant files or diff, contracts,
  and commands/checks;
- prioritize correctness, regressions, data integrity, security, concurrency,
  error handling, and missing tests;
- require file-and-line evidence where possible;
- prohibit invention of unprovided repository state;
- classify severity and confidence;
- reproduce or independently validate material findings;
- never let browser output directly mutate the repository.

## 4. Document review

Use for reports, specifications, contracts, policies, plans, and research
packets.

Required behavior:

- check internal consistency, completeness, traceability, evidence coverage,
  ambiguity, missing decisions, and unsuitable certainty;
- distinguish editorial repair from substantive change;
- preserve document provenance and version identity.

## 5. Data/calculation

Use for large calculations, tables, transformations, classifications, or
structured extraction.

Required behavior:

- define schema, units, clocks, rounding, missing-value behavior, and invariants;
- require machine-readable output;
- request checksums and row/member counts when practical;
- independently recompute samples or the full result;
- send major recalculation defects back to the responsible worker;
- never accept output merely because it parses.

## 6. Adversarial review

Use for falsification, red teaming, source-rights review, assumption testing,
leakage, temporal integrity, negative controls, security, or operational risk.

Required behavior:

- use a fresh conversation when independence matters;
- withhold prior conclusions when blind review is more useful;
- require concrete counterexamples, disconfirming evidence, and kill criteria;
- separate fatal defects, repairable defects, uncertainties, and suggestions;
- do not treat disagreement alone as proof.

## 7. Synthesis

Use for combining multiple accepted packets.

Required behavior:

- consume only identified accepted inputs;
- preserve provenance and version identity;
- expose conflicts rather than silently averaging them;
- distinguish accepted findings, hypotheses, rejected claims, and open questions;
- never upgrade evidence strength through synthesis alone.

## 8. Artifact production

Use to produce a bounded report, dataset, matrix, checklist, prompt, or other
deliverable.

Required behavior:

- define exact filenames, formats, schemas, encoding, and relevant size bounds;
- require a manifest and checksums for multi-file packets when practical;
- define mechanical and semantic acceptance checks;
- treat the artifact as provisional until recovered and verified locally.
