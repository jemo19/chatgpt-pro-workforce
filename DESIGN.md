# Dashboard design system

The status dashboard is an operations ledger: dense enough to be useful during
a long research run, calm enough to leave open, and explicit about whether its
local projection can be trusted.

## Principles

- Put projection trust, run identity, next action, and the five registered
  ratios in the first viewport.
- Show exact numerators and denominators. Never manufacture an overall score.
- Keep the last-known-good snapshot visible during a connection interruption.
- Use color as a redundant state cue, not as the only state label.
- Keep controls copy-only. The page reports state but does not orchestrate it.
- Prefer flat ruled regions, compact labels, and strong typography over card
  grids, gradients, glow, decoration, or oversized hero text.

## Visual tokens

- Backgrounds: graphite-green `#07110f`, raised `#0b1815`, soft `#10221e`.
- Text: mineral white `#edf8ef`, muted `#aec5b8`.
- State accents: mint for accepted/current, sky for active/reconnecting, amber
  for attention/stale, coral for unavailable/rejected.
- Borders: `#28423a` and `#45675b`; six-pixel corner radius; no elevation
  shadows.
- Type: system sans for interface text and system monospace for identifiers,
  hashes, timestamps, and diagnostics.

## Layout and responsive behavior

The desktop first viewport is a two-column run ledger: situation and next
action on the left, the five independent progress rails on the right. Lanes and
attention follow immediately. Below 960 pixels the ledger stacks; below 650
pixels progress labels and ratios remain together while rails take a full row.

Chrome automation or debugging bars can reduce the content viewport without
changing the outer window. Visual acceptance therefore uses the measured
content viewport, and the layout must remain useful at that reduced height.

## Projection trust states

The top strip exposes exactly six display states: `loading`, `current`,
`reconnecting`, `stale`, `data_error`, and `unavailable`. Successful reads reset
the bounded retry sequence. Failures retry after 1, 2, 4, 8, 16, then 30 seconds
with small jitter. A malformed or unsupported snapshot is distinct from a dead
server. Projection diagnostics disclose the schema, last attempt, last success,
failure count, retry timing, and relative snapshot URL.

## Interaction contract

Refresh and retry perform read-only GET requests. Copy buttons put exact skill
intents on the clipboard and confirm: “Copied — no action executed.” The help
area explains consequences and includes the bounded dashboard troubleshooting
intent. There are no remote assets, analytics, write endpoints, or hidden
execution controls.

## Provenance

The design interprets the operator's compact `stats.png` progress reference and
the assigned impeccable concept seed `4f4856a6`. A bounded ChatGPT Pro web lane
researched operational dashboards, accessibility, incident status patterns,
and stale-data behavior; Codex independently selected and implemented this
local, dependency-free design.
