# Linux browser and desktop control options

## Contents

- [Runtime rule](#runtime-rule)
- [Known Codex Linux support stack](#known-codex-linux-support-stack)
- [Browser-control adapters](#browser-control-adapters)
- [Desktop-control adapters](#desktop-control-adapters)
- [Session compatibility](#session-compatibility)
- [Desktop-action precheck](#desktop-action-precheck)
- [Execution and postcheck](#execution-and-postcheck)
- [Action outcomes and attempts](#action-outcomes-and-attempts)
- [Troubleshooting](#troubleshooting)
- [Manual handoff](#manual-handoff)
- [Preference order](#adapter-preference-order)
- [Adapter record](#required-adapter-record)

This reference describes adapter classes the skill may discover and use on
Linux. It is not an installation script and does not itself authorize
installation, privilege changes, or use. A missing workload prerequisite may
enter the exact, permission-gated process in
[prerequisite setup](prerequisite-setup.md).

## Runtime rule

Do not assume that Linux lacks native browser support or that it has native
arbitrary desktop control. Inspect the current ChatGPT/Codex host first. Platform
support changes over time, and workspace policy may differ from product support.

Host support and policy change over time. Therefore:

1. check the native browser path first;
2. check native Computer Use separately;
3. use a configured third-party adapter only for gaps;
4. preserve a manual handoff route.

Browser success does not prove arbitrary desktop control, and a desktop adapter
does not make desktop use necessary. Before probing a CLI, inspect its trusted
schema or documentation: do not assume `--help` is non-executing. Some adapter
subcommands may ignore that flag and enumerate applications, windows, or other
unrelated state.

## Known Codex Linux support stack

Follow [platform control stacks](platform-control-stacks.md) and recognize these
four exact families when the active inventory exposes them:

1. `chrome:control-chrome` through `agent.browsers.get("chrome")`;
2. `mcp__computer_use_linux__*`;
3. `mcp__chrome_devtools__*`;
4. `mcp__playwright_extension__browser_*`.

Record them independently on first use and re-check exposure on every
invocation. For Linux Computer Use, begin with the narrowest safe
`mcp__computer_use_linux__get_app_state` readiness request appropriate to the
named target; omit screenshots and verbose diagnostics unless they are needed,
authorized, and safe. Do not retain unrelated application/window data. Treat
DevTools and Playwright as auxiliary until their browser context is proven;
neither automatically shares the authenticated Chrome controller.

## Browser-control adapters

### Native ChatGPT/Codex browser or Chrome control

Prefer the host-provided browser interface when it exposes semantic tabs,
page elements, uploads, downloads, and screenshots. Full Chrome DevTools
Protocol access is a distinct, sensitive capability; do not require or enable
it merely to type into ChatGPT.

Official references:

- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/6825453-chatgpt-release-notes

### Chrome DevTools MCP

`chrome-devtools-mcp` exposes Chrome DevTools capabilities to coding agents
through MCP or a CLI. It can be appropriate when a semantic live-Chrome
controller is already installed and configured.

- Project: https://github.com/ChromeDevTools/chrome-devtools-mcp
- Product overview: https://developer.chrome.com/blog/chrome-devtools-mcp

Discovery guidance:

- inspect the current MCP tool inventory for the exact server/tool names;
- prefer a read-only page list, title, or snapshot as the probe;
- do not launch a new browser profile when the workflow requires the user's
  existing authenticated ChatGPT session unless the user configured that path;
- do not enable remote debugging on an exposed interface.

### Microsoft Playwright MCP or Playwright CLI

Playwright MCP provides browser automation using structured accessibility
snapshots. It may be used when already configured and able to reach the intended
authorized browser context.

- Project: https://github.com/microsoft/playwright-mcp
- Documentation: https://playwright.dev/mcp/

A fresh isolated Playwright browser is not equivalent to the user's logged-in
Chrome session. Record whether the adapter uses an isolated context, a browser
extension, or an explicitly configured persistent profile.

## Desktop-control adapters

### Native Computer Use

Classify host-provided Computer Use separately from configured MCP servers,
CLIs, accessibility services, or input tools. A name containing "computer use"
does not make an adapter native. Record the exact exposure surface, supported
platform, target-selection method, and current safe probe.

### AT-SPI / dogtail

Dogtail uses Linux accessibility technologies to inspect and automate desktop
applications. This is preferred over coordinate-only control when the target
application exposes a useful accessibility tree.

- Project: https://gitlab.com/dogtail/dogtail
- Background: https://fedoramagazine.org/automation-through-accessibility/

Probe by enumerating an application, window, and harmless control. Do not click
or type during preflight. Some applications expose incomplete accessibility
metadata; classify that as `DEGRADED`, not as a reason to jump immediately to
coordinates.

### ydotool

`ydotool` uses Linux input facilities to synthesize keyboard and mouse events.
It can work beyond X11, but normally relies on a daemon and `/dev/uinput`
configuration. Treat it as a low-level fallback because it does not itself
prove that the correct window has focus.

- Project: https://github.com/ReimuNotMoe/ydotool

Never start a daemon, change groups, create udev rules, or relax permissions
silently or during a worker action. If this layer is truly required, create an
exact prerequisite packet naming the package/source, daemon, device access,
group/udev/permission effect, validation, rollback, and manual steps; execute
only after explicit approval and then run a complete preflight. Pair input
synthesis with an independent window/focus check and post-action verification.

### xdotool

`xdotool` targets X11 and uses XTEST/Xlib. It is not a dependable native Wayland
solution.

- Project: https://github.com/jordansissel/xdotool

Use only when the current session and target are actually X11/XWayland-compatible
and the target can be identified before input.

### wtype

`wtype` synthesizes keyboard input through a Wayland virtual-keyboard protocol.
Compositor support varies, and it is primarily a typing tool rather than a full
semantic desktop controller.

- Project: https://github.com/atx/wtype

Treat availability of the executable as insufficient. Verify compositor
support in a disposable target before relying on it.

## Session compatibility

- **KDE Plasma/Wayland:** prefer configured KWin and portal-mediated paths.
  Capture, input, or native dialogs may require a user portal choice. Global
  coordinate and X11 assumptions are invalid.
- **Other native Wayland sessions:** discover the compositor and portal path;
  do not assume a tool documented for a different compositor can list or focus
  windows.
- **X11:** require one unique stable X11 target plus an independent focused
  window/control observation before input.
- **XWayland:** determine the target's actual protocol when observable. Presence
  of an X11 tool or `DISPLAY` does not prove it can control a native Wayland
  window.

Session discovery is evidence only. Never switch sessions, enable compositor
extensions, or change portal/accessibility settings merely as a fallback.
Any proposed prerequisite change needs an exact approved packet, must preserve
a manual route, and requires a complete post-change preflight. Prefer avoiding
session switches because they disrupt browser state and active work.

## Desktop-action precheck

Run this gate only when browser semantics cannot complete an authorized action.

1. Assign a stable action ID and record the specific browser limitation plus
   exact desktop action needed.
2. Confirm current instructions authorize that action, target application,
   artifact, and side effect. Tool availability is not permission.
3. Discover the exact registered adapter and method names. Read their current
   schemas before calling them; do not invent flags or probe commands.
4. Inspect OS, desktop environment, display protocol, accessibility readiness,
   screenshot backend, window-targeting backend, input backend, and privilege
   requirements using the narrowest read-only readiness result.
5. Assign one allowed capability state to accessibility, window targeting,
   screenshots, input, and focus verification separately.
6. Identify the intended application/window from a user-designated target or a
   narrow selector. Avoid broad application/window enumeration when a precise
   target is already known, and never retain unrelated titles or content.
7. Define the precondition, semantic target, and observable postcondition before
   acting. If any is ambiguous, use manual handoff rather than exploratory input.
8. Select the least powerful verified layer. Do not continue merely because a
   lower-level fallback exists.

Presence-only evidence supports at most `AVAILABLE_UNTESTED`. A safe readiness
probe can verify the adapter layer, but input remains untested until a
disposable target and independently verifiable focus are used.

## Execution and postcheck

For each desktop action:

1. Re-run the adapter's required readiness call if the desktop session, tool
   connection, target window, or permission state may have changed.
2. Resolve the exact window using stable fields the adapter actually exposes,
   such as a current window handle plus application/class/title constraints.
3. Prefer an accessibility action or value operation. Use explicit window
   focus only when needed and authorized.
4. Before keyboard or pointer synthesis, independently verify the target window
   and focused control. Treat inability to verify focus as a hard no-input gate.
5. Record attempt 1 and perform one bounded action. Do not batch a sequence
   whose intermediate state cannot be checked.
6. Inspect the cheapest semantic postcondition: focused editable control,
   changed value, dialog state, file presence, or target-scoped screenshot.
7. If the postcondition is absent or contradictory, preserve evidence and
   diagnose; do not blindly repeat the input.

Crop screenshots to the target when possible. Confirm timestamp, dimensions,
target identity, and non-blank content before using them. When scale or
coordinate dimensions differ, use adapter-reported conversion metadata; never
guess display scaling.

For Chrome screenshots, distinguish the outer browser window from the content
viewport. Detect any automation, debugging, or control infobar at the top and
record device scale, top inset, and crop. Prefer a semantic page/element or
content-viewport capture. The bar-induced aspect-ratio change is capture
environment metadata, not an application defect; do not close or disable the
bar just to normalize a screenshot.

## Action outcomes and attempts

Use only these desktop-control outcomes:

- `NOT_ATTEMPTED`
- `VERIFIED_SUCCEEDED`
- `VERIFIED_FAILED`
- `OUTCOME_UNKNOWN`
- `MANUAL_HANDOFF`
- `BLOCKED`

Action outcomes are separate from the eight capability states and the worker
generation states; never substitute one vocabulary for another.

Allow at most two automated attempts for one action: the initial attempt plus
one recovery attempt using materially changed evidence, target method, or
route. Never repeat input after `OUTCOME_UNKNOWN`. After any disconnect or tool
timeout, reacquire the target and test the expected postcondition before
deciding that an action remains necessary. A send, submit, overwrite, delete,
or download with unknown outcome cannot be repeated until duplicate/output
state is reconciled. After the ceiling, use manual handoff or stop.

## Troubleshooting

| Symptom | Classification | Safe response |
|---|---|---|
| Adapter is configured but its tool is absent or policy-disabled | `DISABLED`, `MISCONFIGURED`, or `UNKNOWN` from evidence | Record the exact discovery gap; offer a bounded prerequisite plan, manual/reduced route, or stop. Do not mutate without exact approval. |
| Accessibility bus is ready but the target exposes no useful tree | `DEGRADED` | Try one target-scoped refresh; use screenshots/manual handoff, or offer an exact approved prerequisite plan if trusted current instructions identify a bounded fix. |
| Wayland window listing/focus is unavailable | `DEGRADED` or `NOT_AVAILABLE` | Use an already configured compositor/portal backend, manual handoff, or an exact approved prerequisite plan; never switch sessions opportunistically. |
| An X11-only tool is present under native Wayland | `AVAILABLE_UNTESTED` or `DEGRADED` | Do not assume XWayland compatibility; choose a Wayland/compositor path or handoff. |
| Portal prompt is awaiting a choice | `AVAILABLE_UNTESTED` | Use manual handoff for the exact portal choice; do not synthesize approval input. |
| Portal prompt is denied, dismissed, expired, or disconnected | `NOT_AUTHORIZED` or `DEGRADED` | Record `NOT_ATTEMPTED` when no action occurred; otherwise reconcile the postcondition and use `OUTCOME_UNKNOWN` until proven. |
| Screenshot is blank, stale, wrong-window, or exposes excessive scope | `DEGRADED` | Discard it, re-target a bounded capture, and withhold input until target identity is established. |
| Chrome automation/debugging infobar changes the visible aspect ratio | Preserve C15 state from the actual capture | Record outer and content-viewport geometry plus top inset/crop; review the content region and do not classify the browser bar as an app defect. |
| Focused window/control differs from the intended target | `DEGRADED` | Send no input. Re-identify and, if authorized, focus explicitly; verify again. |
| Input reports success but no semantic postcondition appears | `VERIFIED_FAILED` only when failure is proven; otherwise `OUTCOME_UNKNOWN` | Preserve the worker-generation state separately, inspect current state, and never repeat unknown input; use one changed recovery only after evidence proves the action failed. |
| Native dialog is invisible to browser and desktop semantics | `AVAILABLE_UNTESTED` or `NOT_AVAILABLE` for automation | Use the manual-handoff packet; do not click guessed coordinates. |
| Adapter disconnects before the action | Preserve capability classification separately | Record `NOT_ATTEMPTED`; reconnect once, reacquire target/focus, and re-evaluate necessity. |
| Adapter disconnects after or during the action | Preserve capability classification separately | Record `OUTCOME_UNKNOWN`; reconnect, reacquire target, and inspect the postcondition before any retry. |
| The next fix requires a daemon, group/udev change, extension, privilege, or session change | `NOT_AUTHORIZED` until exact approval | Pause orchestration; offer a prerequisite packet with source, target, permissions, validation, rollback, and manual alternative. Never relax security. |
| A guessed help/discovery command unexpectedly executes or returns broad state | `DEGRADED` | Stop that probe, discard unrelated output from reports, and use registered schemas or trusted documentation. |

## Manual handoff

When automation cannot safely target a native dialog or control, give the user a
bounded handoff containing the intended application/window, exact action, file
or destination, expected postcondition, and what Codex will verify afterward.
Never request passwords, cookies, tokens, or private keys. After handoff, re-run
only the affected readiness and postcondition checks.
If current-session manual availability is unknown, record it as
`AVAILABLE_UNTESTED` or `UNKNOWN`; never assume the user can take over.

## Adapter preference order

Use the first authorized, verified option capable of the action:

1. purpose-built API, connector, or CLI;
2. native semantic browser control;
3. configured semantic browser MCP/CLI;
4. Linux accessibility-tree interaction;
5. explicit native window targeting;
6. keyboard/mouse synthesis with focus verification;
7. screenshot plus visual reasoning;
8. raw coordinate clicking as a last resort.

Screenshots are evidence and orientation, not permission to skip semantic
targeting or focus verification. Raw coordinates require a disposable or
otherwise explicitly authorized target, current bounded screenshot, known
coordinate transform, and immediate post-action verification.

## Required adapter record

For every adapter used, record:

- exact name and version when observable;
- where it was discovered;
- control class;
- safe probe and result;
- browser profile or desktop-session assumptions;
- permissions and privilege requirements;
- target-selection method;
- upload/download behavior;
- failure signatures;
- whether the user must intervene;
- exact precheck and postcondition used for every desktop action;
- stable action ID, attempt number, and one allowed action outcome;
- disconnects, focus mismatches, and failed approaches that must not be retried
  unchanged.

Do not treat a third-party project link as evidence that the adapter is installed
or safe in the current environment.
