# Completed research explorer

Use this reference when a research run is being configured, accepted, handed
off, resumed at completion, or exported for a human reader. The explorer is a
portable view of accepted research evidence. It is not a substitute for raw
worker returns, source notes, validation records, or the durable run state.

## Contents

- [First-use choice](#first-use-choice)
- [Accepted-data boundary](#accepted-data-boundary)
- [Build and verification](#build-and-verification)
- [Placement and handoff](#placement-and-handoff)
- [Interaction and fallback](#interaction-and-fallback)
- [Security and privacy](#security-and-privacy)
- [Resume and repair](#resume-and-repair)

## First-use choice

During guided setup, show every explorer policy and ask which one to store:

- `ALWAYS` — recommended for research runs; build the explorer after acceptance;
- `ASK_AT_COMPLETION` — offer it when the accepted packet is ready;
- `DISABLED` — do not build an explorer unless the user later changes this.

Explain that the explorer adds a human-readable HTML file and some Codex work
for data preparation and verification. It does not change worker ownership or
the run's evidence standard. The user may change the policy at any time; a
change affects future exports and must not mutate a previously accepted file.
Record the exact configured destination rather than assuming that Downloads or
another folder is safe for the final copy.

## Accepted-data boundary

Build from the allowlisted schema in
[research explorer data template](../assets/research-explorer-data-template.json).
Include only accepted or explicitly labeled unresolved material. Stable finding,
source, contradiction, lane, decision, recommendation, and artifact IDs provide
traceability. Preserve contradictions and limitations; never turn absence of a
contradiction into proof of consensus.

Do not embed raw prompts, raw worker responses, cookies, tokens, credentials,
private browser state, unrelated files, note bodies outside the run, or any
content excluded from the user's human-facing handoff. A source URL is evidence,
not permission to fetch it when the offline file is opened.

Before generation, run the normal mechanical and semantic gates against the
underlying accepted packet. The explorer may organize or index accepted, sanitized facts;
it may not repair, reinterpret, or upgrade them. If its structured data exposes
a material omission or conflict, return to the responsible gate or worker.

## Build and verification

Discover an available Python 3.10-or-newer interpreter and use the bundled
[research explorer helper](../scripts/research_explorer.py). Do not download
dependencies. Run its help first, then use the equivalent of:

```text
<python-path> scripts/research_explorer.py build --data <private-accepted-json> --template assets/research-explorer-template.html --output <exact-output.html>
<python-path> scripts/research_explorer.py verify --html <exact-output.html> --expected-run-id <RUN_ID>
```

The helper validates the exact schema, referential integrity, bounded sizes,
URLs, hashes, and enumerated states before it replaces an output atomically.
It embeds escaped JSON into one self-contained HTML file. Freeze and hash the
output, run the applicable HTML/accessibility/browser checks, rehash it, and
add the final bytes to the accepted artifact manifest. The source JSON may be
retained as a separate accepted machine-readable artifact when the user wants
it, but the HTML must work without it.

Mechanical acceptance requires: one regular non-symlink HTML file; a matching
run ID; valid embedded schema; no remote scripts, styles, fonts, analytics, or
network-fetch code; no broken internal finding/source references; and a stable
post-validation SHA-256. Semantic acceptance requires the rendered summary,
findings, confidence, citations, contradictions, limitations, and next steps to
match the same accepted evidence packet.

## Placement and handoff

Create the first verified explorer inside the run-owned `accepted/` directory.
When the profile calls for a user-facing Downloads result, copy the exact
verified bytes to one explicit configured final-output folder or exact filename,
then rehash both copies. Do not scan, clean, or treat the general Downloads
directory as run-owned. Record both locations, byte count, SHA-256, and whether
the exported copy is task-created.

Use a collision-resistant name such as
`<topic-slug>-research-explorer-<run-id>.html`. Never silently overwrite a
different or unverified file. Link the explorer from the run handoff and, when
notes are enabled, from the topic index without duplicating its contents into
Obsidian.

Include a relative artifact link only when that exact accepted artifact is
packaged at the corresponding relative location beside the exported HTML and
the link is verified. For a single-file handoff, show the artifact name, role,
size, and hash without a link rather than publishing a broken or machine-local
path.

## Interaction and fallback

The shipped page supports local search; category, confidence, and evidence
filters; source/finding trace links; expandable detail; source sorting; section
navigation; reset; and print. Every interaction is local to the open file and
must remain useful with a keyboard, visible focus, reduced motion, narrow
screens, and the content viewport reduced by a Chrome automation/debugging bar.

Core research content exists in semantic HTML before enhancement. If JavaScript
is blocked, the reader still sees the summary, every finding and source, all
contradictions and limitations, methodology, recommendations, and artifact
inventory. Interactive controls may be hidden or disabled with a direct note;
no content may disappear merely because filtering is unavailable.
Treat this as the required no-JavaScript reading path, not an optional browser
feature.

## Security and privacy

- Use no CDN, external font, analytics, telemetry, cookie, storage, service
  worker, remote image, or automatic network request.
- Treat embedded data as text. Never assign it through `innerHTML`.
- Permit only `https://` and `http://` source links, plus verified safe relative
  links for run-owned artifacts; reject script, data, file, credential-bearing,
  traversal, absolute-path, and protocol-relative links.
- Do not place an explorer containing sensitive accepted research in a public
  or synced location unless that exact disclosure is authorized.
- A local interactive file grants no permission to open sources, transmit
  content, delete artifacts, or perform workflow controls.

## Resume and repair

Persist explorer policy, data path/hash, template hash, accepted HTML path/hash,
export path/hash, validation result, and next action in run state. On resume,
reconcile those exact bytes before rebuilding. Do not regenerate an already
accepted explorer merely because the page was reopened.

For a deterministic presentation or broken-link defect, preserve the rejected
HTML and build one new candidate from the same accepted data. For a factual,
missing-evidence, or traceability defect, reject the explorer semantically and
return to the underlying research integration; do not repair the claim in the
presentation layer.
