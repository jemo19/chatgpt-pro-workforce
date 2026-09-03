# Failure catalog and recovery policy

Use observable evidence to classify failures. Preserve screenshots, timestamps,
exact messages, hashes, and command output needed to support the classification.

## Contents

- [Failure matrix](#failure-matrix)
- [Retry rule](#retry-rule)
- [User-decision threshold](#user-decision-threshold)

## Failure matrix

| Failure | Evidence | Safe response | Conversation policy |
|---|---|---|---|
| Transient ChatGPT internal error | Error banner plus generation state and output-growth history | Continue observing if generation is active; do not reload | Same conversation |
| Active generation with error banner | Active control or growing output despite banner | Wait and record; classify terminal only after generation stops | Same conversation |
| Terminal response without completion marker | Generation stopped; marker absent | Preserve output; issue bounded continuation/diagnostic prompt | Same unless context is corrupted |
| Stopped response with partial artifacts | Some expected files/sections exist | Recover everything, inventory gaps, request only missing work | Same conversation |
| Attachment visible but download blocked | Attachment card/link visible; browser action fails | Try browser URL, authorized desktop dialog, ZIP, then bounded Base64 | Same conversation |
| Download blocked by extension/policy | Exact browser/extension error | Use another authorized recovery route; do not disable security extensions silently | Same conversation |
| Native dialog invisible to browser automation | Download action opens inaccessible dialog | Use verified desktop adapter or manual handoff | Same conversation |
| Browser tab hidden or not exposed | Controller cannot enumerate target tab | Reconnect; use explicit window targeting; verify before input | Same conversation if found |
| Browser-control disconnect | Tool connection lost | Reconnect and re-identify target; do not resubmit | Same conversation |
| Linux Computer Use unavailable | Capability matrix shows absent/disabled/misconfigured | Continue browser-only, use configured third-party adapter, or manual handoff | No forced relaunch |
| Expected platform support layer missing | Current-OS platform-stack record is absent, disabled, unauthorized, or misconfigured | State the exact missing browser/desktop/accessibility/window/screenshot/input layer; offer bounded setup, manual/reduced route, or workload revision | No invented interface or silent setup |
| DevTools/Playwright context differs from signed-in browser | Auxiliary route cannot prove the intended authenticated ChatGPT context | Keep it auxiliary; reacquire the signed-in Chrome/in-app route or use manual handoff | Never copy cookies/tokens or treat contexts as interchangeable |
| macOS privacy grant missing | Exact Accessibility, Automation, Input Monitoring, Screen Recording, or Files/Folders grant is not present | Request only the needed grant through a manual System Settings handoff, then re-probe | No Full Disk Access shortcut or automated consent |
| Windows elevation or secure-desktop boundary | Target is elevated, locked, or behind UAC/credential secure desktop | Preserve no-input state and use a bounded manual handoff or reduced route | Never weaken UAC, Defender, SmartScreen, or policy |
| Third-party adapter misconfigured | Safe probe fails with concrete configuration error | Record exact error; offer an exact permission-gated prerequisite plan, manual/reduced route, or stop | Retry only after an approved change and full preflight |
| Required prerequisite is missing | Workload map marks the absent capability `required` | Record `MISSING`, offer bounded setup/manual/reduced choices, and launch no dependent lane | No launch until verified preflight or accepted alternative |
| Setup awaits exact approval | A plan exists but its source, targets, changes, permissions, validation, and rollback are not all approved | Use `AWAITING_APPROVAL`; perform no mutation | Resume setup only from the approved packet |
| Setup exposes a broader target or permission | Installer, extension, OS prompt, or command requests access beyond the approved packet | Stop before approval/input, record the delta, and revise or reject the plan | No silent acceptance or scope expansion |
| Native privacy, portal, credential, or UAC dialog appears | OS-owned consent surface requires a user decision | Use `MANUAL_ACTION_REQUIRED` with exact bounded handoff; never synthesize consent or credentials | Re-probe only after the user completes or declines it |
| Approved setup fails | Exact command/UI result or verification contradicts the expected postcondition | Preserve safe error, stop broadening, use stated rollback when appropriate, and mark `FAILED` | Retry only with new evidence and a newly approved changed packet |
| Post-setup preflight fails | Setup step completed but required capability is not `AVAILABLE_VERIFIED` | Keep the route unready; diagnose, roll back, offer manual/reduced route, or stop | Never promote from command success alone |
| Account shows Pro but target conversation mode is unverified | Profile/plan evidence proves entitlement only; no selected model and maximum-power proof exists at the composer | Suppress input, semantically inspect the exact model and thinking-power controls, and ask for manual selection if required | Never treat the account badge as per-conversation mode proof |
| Target conversation is not at maximum Pro power | Semantic state shows the wrong model, `High`, a collapsed `Pro` button without the open selector proof, or another lower setting | If already authorized, select the declared model and maximum power, close/reopen the selector, and re-read the postcondition; otherwise request the smallest user action | No prompt submission until `PRO_MAX_POWER_VERIFIED` is established |
| Pro selector is unavailable, ambiguous, or localized beyond safe interpretation | Current semantic state cannot unambiguously prove the declared model and exact maximum-power value | Record `PRO_UNAVAILABLE`, `PRO_AMBIGUOUS`, or `UNKNOWN`; preserve lane state and ask the user | Never guess from coordinates, URL, defaults, or response quality |
| Provider limit or fallback changes Pro mode | Visible limit/fallback state or changed model control invalidates the prior proof | Record `PRO_LIMITED_OR_FALLBACK`, pause the lane, and recheck after capacity or mode restoration | Never silently continue under a reduced or automatic model |
| Resume, reload, or target recovery invalidates mode evidence | Conversation identity or selected-state evidence is older than the relevant transition | Re-identify the exact target and run the Pro submission gate again | Previous verification is not transferable |
| Black or stale screenshot | Image is blank, old, or wrong target | Re-target capture; verify dimensions and timestamp | Same conversation |
| Chrome automation/debugging infobar changes screenshot geometry | Browser chrome consumes top space or outer-window and content-viewport aspect ratios differ | Record capture surface, both geometries, device scale, top inset/crop; prefer page/content capture and exclude browser chrome from app findings | Same target; do not disable the bar merely for capture |
| Stale conversation context | Worker references old scope or prior files | Freeze evidence; start a clean conversation with self-contained inputs | Fresh conversation |
| Accidental text in composer | Composer contains unintended text before submission | Verify ownership; clear safely; re-render final prompt | Same conversation |
| Duplicate detected before submission | Lane ID, prompt hash, and conversation match an active or completed message | Suppress submission; select one canonical lane and record the duplicate check | Canonical conversation only |
| Duplicate prompt submission | Two identical user messages or duplicate active runs | Do not cancel blindly; choose one canonical lane and mark duplicate | Keep canonical; quarantine duplicate |
| Incorrect model or mode | Visible model/mode conflicts with prompt | Stop before submission when possible; otherwise preserve and relaunch correctly | Fresh conversation if material |
| Missing upload | Prompt references file not visibly attached | Do not submit; attach exact file and verify identity | Same conversation before launch |
| Truncated output | Response ends mid-structure or stated counts do not reconcile | Recover partial; request continuation from exact boundary | Same conversation |
| Invalid ZIP | Archive test fails | Preserve raw bytes; request a new native archive or deterministic recovery | Same conversation first |
| ZIP contains traversal, absolute, duplicate, symlink, special, encrypted, or unexpected members | Pre-extraction inventory detects unsafe or out-of-contract members | Quarantine raw bytes; do not extract; request a clean bounded packet | Same conversation first |
| Checksum mismatch | Recovered bytes differ from manifest | Preserve all versions; retry recovery, never normalize silently | Same conversation if source exists |
| Source URL inaccessible | Worker or verifier cannot reach source | Seek authoritative alternative; mark unresolved if none | Same or fresh research lane |
| Licensed/paywalled source | Access requires unauthorized account/data | Do not bypass; use permitted metadata/secondary evidence or mark unavailable | Same lane or blocked |
| Worker claims test passed without evidence | No command/output/artifact supports claim | Treat as unverified; run locally or request exact evidence | Same conversation |
| Mechanically valid but semantically rejected | Parsers/checkers pass; claims fail evidence review | Freeze rejected candidate; issue precise semantic correction | Same for bounded repair, fresh for broad rebuild |
| Post-validation mutation | Candidate hash changes after checks | Reject acceptance; rerun both gates on one frozen candidate | Same work product, new candidate ID |
| Lost transient files | Claimed artifact no longer recoverable | Search bounded known locations/logs; mark `NOT_RECOVERABLE` if absent | Diagnostic turn; do not recreate bytes |
| Contradiction between parallel lanes | Accepted-looking lanes disagree materially | Preserve both; launch adjudication or inspect primary evidence | Fresh independent reviewer |
| Proposed third-or-later concurrent Pro worker | Active/outcome-unknown count plus proposed launch exceeds two | Suppress launch; show the exact high-risk throttling/chat-loss warning and require a current-run, exact-limit acknowledgment | Never close an existing chat; changed limit affects future launches only |
| First-use baseline missing or untrusted | No accepted `INITIAL_BASELINE`, workforce profile, or exact interface inventory exists | Run the full safe baseline before worker launch; persist unknowns honestly | No worker action during baseline |
| Invocation readiness gate detects drift | Current interface, targetability, route, or permission evidence differs from the prior invocation | Record the delta, freeze dependent actions, and run the affected full recheck | Continue only on a freshly accepted route |
| Control fault has an affected safe repair | Diagnostic evidence identifies a stale connection, target binding, semantic handle, or focus proof | Freeze input, perform one bounded non-destructive repair, re-preflight on state/route change, then reconcile postcondition | Never duplicate an unknown submission/action |
| Control fault needs a new capability or permission | One bounded repair cannot restore a required route and a new install, extension, daemon, permission, or security change is needed | Offer exact prerequisite/manual/reduced choices; ask before mutation | No dependent worker or desktop action |
| Status evidence is stale or controller is disconnected | Durable last-observed time predates the requested status and no safe refresh succeeded | Report `STALE` or `UNKNOWN`; show persisted evidence and do not infer current worker state | Status only; do not resume implicitly |
| Multiple run IDs could match a control intent | More than one active or paused durable run exists | Show safe run IDs/outcomes and ask one identifying question | No mutation until selected |
| Scope denominator grows after approved discovery | New approved scope IDs increase the registered total | Record `scope_change: +N`, recompute the ratio, and explain the shorter bar | Continue only under stored policy |
| Worker suggests an unapproved topic | Suggestion lacks a persisted approval or policy basis | Store it as pending/deferred; do not create a lane | User decision or fixed-scope record |
| Provider usage or capacity limit | Visible provider message or control state establishes the limit | Use `LIMIT_PAUSED`; preserve shown reset evidence; do not bypass, switch accounts, or duplicate | Resume only after recheck |
| Aggregate run state missing or corrupt | Run record cannot be parsed or disagrees with durable lane/artifact evidence | Reconstruct only from trustworthy records; use `UNKNOWN` for gaps or `BLOCKED` when unsafe | No browser-memory reconstruction |
| Resume would repeat a submitted or unknown action | Prompt hash, conversation state, artifact presence, or desktop postcondition is unreconciled | Remain `RESUMING`; reconcile first and suppress duplicates | No input until known |
| Progress update cadence creates noise | Cards repeat without state, ratio, evidence, blocker, or decision change | Honor configured cadence and omit redundant updates | Internal monitoring continues separately |
| Dashboard server is absent or health fails | Recorded process/port exists but the exact loopback health check fails | Omit the link, preserve text detailed status, reconcile process identity, and attempt at most one authorized restart | Dashboard only; do not resume a run |
| Dashboard snapshot fails validation or atomic write | Unknown/sensitive/oversized fields, run-ID mismatch, or filesystem error rejects the new public snapshot | Preserve the prior valid snapshot, mark it stale, and report the local error without raw sensitive data | No unsafe schema widening |
| Dashboard data is stale while page polls | `updated_at` exceeds the declared freshness window and no invocation/material observation refreshed it | Show `STALE`; explain that polling does not keep orchestration alive | Use status invocation for a fresh gate |
| Dashboard port or root conflicts | Port belongs to another process or configured root is broad, symlinked, unavailable, or mismatched | Do not kill/serve; select an explicit dedicated root or free loopback port and health-check again | One bounded dashboard repair |
| Download cleanup target is unsafe or changed | Target is a directory, symlink, glob, traversal, out-of-root path, ambiguous owner, in use, or hash differs from approved manifest | Record `SKIPPED`/`FAILED`, perform no deletion, and require a new exact manifest if still needed | No scope widening |
| Cleanup would remove unhanded-off evidence | Accepted export, raw lineage decision, artifact index, or handoff is missing | Keep the file and complete acceptance/handoff before a new cleanup decision | No deletion |
| Obsidian/research root is unknown or unapproved | Note policy requests writing but no exact root and creation authority are stored | Suggest a research-specific root and ask for the exact path/creation decision | No folder or note creation |
| Obsidian locator finds multiple plausible vaults | Registry/project/marker evidence does not produce one unambiguous candidate | Show the bounded candidates and evidence; ask the user to confirm one | No auto-selection or note read/write |
| Obsidian registry is malformed, oversized, or schema-unknown | Known config exists but bounded JSON parsing or exact field extraction fails | Record the registry source unusable and continue with explicit/marker candidates | Do not dump or heuristically mine config contents |
| Remembered vault path is missing or changed | Confirmed path no longer resolves to the expected directory/marker | Re-run bounded discovery and ask to confirm the new recommendation | No broad home crawl or silent root change |
| Discovered topic folder would precede approval | Proposed topic is pending, deferred, rejected, or out of bounds | Record the proposal only; create no folder or lane | User decision or fixed-scope record |
| Allocation change could disrupt active ownership | New profile would retask an active lane/writer or duplicate pending work | Keep active ownership, record effective future profile/usage band, and plan an explicit safe transition if requested | No silent interruption or duplicate |
| Tool exists but action is not authorized | Discovery succeeds but current instructions do not cover target or effect | Record `NOT_AUTHORIZED`; do not probe by mutation or infer permission | No launch until authority changes |
| Desktop focus cannot be independently verified | Window/control identity is absent, stale, or contradictory | Send no input; re-identify once or use manual handoff | Same target only after a fresh precheck |
| Adapter discovery command exposes broad unrelated desktop state | Guessed flag or unscoped enumeration returns unrelated windows/apps/content | Stop, discard it from reports, and use trusted schemas plus target-scoped probes | No retry with the same broad probe |
| KDE/Wayland portal awaits a user choice | Portal dialog is observable and no action occurred | Record `NOT_ATTEMPTED`; give a bounded manual handoff and re-probe only the affected layer | No automated approval input |
| Portal unavailable, denied, cancelled, or expired | Exact portal result and no postcondition | Record `NOT_ATTEMPTED` if action did not occur; otherwise `OUTCOME_UNKNOWN` until reconciled; use one target-scoped re-probe or manual handoff | No identical portal retry |
| X11/XWayland/native-Wayland protocol mismatch | Session or target protocol contradicts the selected adapter | Record `NOT_ATTEMPTED`; select an already configured compatible layer or manual handoff | No input through the mismatched layer |
| Missing, partial, or stale AT-SPI tree | Named target/control is absent, incomplete, or unchanged after a target-scoped refresh | Classify the layer `DEGRADED`; use a current bounded screenshot or manual handoff | One read-only refresh; no blind semantic action |
| Desktop target ambiguous or unrelated-window exposure required | Selector matches zero/multiple windows or only a broad inventory could disambiguate | Record `NOT_ATTEMPTED`; request a user-designated target or use manual handoff | No input and no broad capture |
| Focus changes between check and action | Immediate pre-input focus observation no longer matches the planned target/control | Record `NOT_ATTEMPTED`; reacquire once and repeat the full target/focus gate | No input until fresh proof |
| Screenshot black, stale, wrong-target, or portal-blocked | Target identity, timestamp/sequence, dimensions, or visible content fails | Discard the capture; re-target one bounded capture or use manual handoff | No coordinate action from rejected evidence |
| Native dialog inaccessible to semantic control | Dialog is expected/visible but has no authorized targetable surface | Record `MANUAL_HANDOFF`; provide exact action and postcondition | No guessed coordinates |
| Desktop adapter disconnects before action | No side-effecting method began and postcondition is absent | Record `NOT_ATTEMPTED`; reconnect once, reacquire target/focus, and reconsider necessity | One materially changed recovery |
| Desktop adapter disconnects during or after action | Call boundary is uncertain or response is lost | Record `OUTCOME_UNKNOWN`; reconnect and inspect the postcondition before any decision | Never repeat unknown input |
| Desktop postcondition absent or contradictory | Target continuity is known but expected result is not observed | Record `VERIFIED_FAILED` when failure is proven, otherwise `OUTCOME_UNKNOWN`; change route for one recovery or hand off | No identical repeat |
| Desktop retry ceiling exhausted | Initial plus one materially changed recovery did not produce `VERIFIED_SUCCEEDED` | Record `MANUAL_HANDOFF` when available, otherwise `BLOCKED` | Stop automation |
| Manual handoff unavailable | Current-session user availability is absent or unknown and no safe automated layer remains | Record `BLOCKED` with the exact action and missing route | Stop |

## Retry rule

A retry must change at least one material element: prompt, conversation context,
control route, recovery method, evidence set, or validator. Never repeat an
identical failed approach merely because time passed.

For one desktop action, allow only the initial attempt plus one materially
changed recovery attempt. Never retry an `OUTCOME_UNKNOWN` action until the
postcondition, duplicate state, or recovered output is reconciled. After the
ceiling, use manual handoff or stop.

## User-decision threshold

Request user input only when a consequential choice, new permission, credential
entry, paid/licensed access, or unresolvable ambiguity is genuinely required.
Do not use clarification as a substitute for bounded diagnostic work.
