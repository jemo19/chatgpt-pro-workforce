# Research interface design system

Blue Hour Archive is two related local surfaces: a midnight operations ledger
for a live run and a warm evidence folio for accepted research. Both make IDs,
state words, rules, and provenance easy to scan. The dashboard answers “what
is happening now?”; the explorer answers “what did we learn, and why?”

## Principles

- Put snapshot trust, run identity, the next safe action, and five independent
  registered ratios in the first view. Never invent an overall percentage.
- Use flat, ruled regions and compact labels instead of floating-card grids.
  No glass, elevation, gradients, glow, or decorative hero treatment.
- Every status has words and a border or other non-color cue; controls copy
  skill intents but never execute them.
- Keep the last validated snapshot on screen while reconnecting. The explorer
  is a reading copy; accepted files, source notes, hashes, and checks remain
  the record.

## Tokens

- **Live canvas:** ink `#0B1020`, raised `#12192B`, soft `#18233A`, and trust
  strip `#0D1426`; lines `#34415B` and `#60708E`.
- **Live type and action:** paper `#F5F7FC`, muted `#B9C3D6`, quiet `#8E9AB2`,
  cobalt `#8AB4F8`, strong cobalt `#5F93ED`, focus amber `#F2C66D`.
- **Live status:** cobalt means loading/current/reconnecting and active work;
  violet `#C6A9FF` means accepted/good; amber `#F2C66D` means
  attention/stale/data error; coral `#FF8D85` means unavailable/bad.
- **Explorer paper:** canvas `#F2EFE8`, paper `#FBFAF7`, soft paper
  `#EAE6DE`, ink `#192133`, muted `#4F5A6E`, neutral `#626C7F`, rules
  `#C7C0B4` and `#81796D`.
- **Explorer links and states:** link `#245CA6`, strong link `#173F78`, blue
  soft `#DCE8FA`; violet `#65449B`/`#E9E0F7` for accepted, approved, and high;
  amber `#7A4B00`/`#F7E9BE` for open, deferred, and medium; danger
  `#8A2F2F`/`#F5DCDA` for rejected and low; strong link/blue soft for bounded,
  answered, and unresolved.
- **Type:** interface text is `ui-sans-serif, system-ui, -apple-system,
  BlinkMacSystemFont, "Segoe UI", sans-serif`; identifiers, hashes, ratios,
  and diagnostics use `"SFMono-Regular", Consolas, "Liberation Mono",
  monospace` with tabular figures. The explorer’s reading and major headings
  use `ui-serif, Georgia, Cambria, "Times New Roman", serif`.
- **Shape:** dashboard surfaces use 6px corners; compact controls and explorer
  fields use 3–4px; tags and copy controls can reach 8px. Never exceed 8px.
  Borders, not shadow, create separation.
- **Scale:** body copy is 1rem at 1.5–1.62 line height; tight headings use
  negative tracking. All main titles cap at 2rem / 32px.

## Layout and responsiveness

The dashboard begins as a continuous two-column ledger: run situation and next
action left; the five progress rails right. Lanes and attention begin below.
At 960px it stacks; at 650px labels and ratios stay together and rails take a
full row. Detail grids, system panels, and control groups similarly collapse.

The explorer is a 1540px three-rail reading layout: contents, report, trace.
The trace drops at 1100px; at 760px the contents become a horizontal local
index and report metadata, records, source grids, and provenance stack. Its
toolbar moves from many columns to four, then two. At desktop heights below
720px, sticky rails shorten and header spacing contracts. Review the measured
content viewport: browser automation/debug bars reduce usable height.

## Status, interaction, and accessibility

The dashboard trust strip has six display states: `loading`, `current`,
`reconnecting`, `stale`, `data_error`, and `unavailable`. Successful reads reset
the retry sequence; failure waits 1, 2, 4, 8, 16, then 30 seconds with small
jitter. Unsupported or malformed data is not a dead server. Diagnostics show
the schema, last attempt and success, failure count, retry timing, and relative
snapshot URL.

Use semantic landmarks, visible text labels, keyboard-visible 3px focus rings,
and sufficient contrast. Progress tracks expose labels to assistive technology;
the explorer stays readable without JavaScript. Respect reduced motion by
removing smooth scroll and reducing animation/transition duration. Print the
explorer as a clean, unfiltered reading copy.

Refresh and retry are read-only GETs. Copy confirmation says “Copied — no
action executed.” No remote assets, analytics, write endpoints, or hidden
execution controls belong on either surface; the local dashboard consumes only
sanitized state and the explorer does not fetch in the background.

## Provenance

Blue Hour Archive interprets the operator’s compact `stats.png` reference and
the committed Impeccable seed `61ffdee4`. The final concept came from a
logged-in ChatGPT Pro lane; Codex retained local review of safety, data,
accessibility, and the dependency-free implementation.
