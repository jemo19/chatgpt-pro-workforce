# Platform support and control readiness

## Preflight policy

The skill performs a safe read-only invocation gate every time it is invoked,
including help, status, and resume. First use, capability changes, and fault
recovery trigger a fuller baseline. Availability is recorded separately from
permission, and prior verification is treated as a hint until refreshed.

Each capability receives one truthful state such as `AVAILABLE_VERIFIED`,
`AVAILABLE_UNTESTED`, `NOT_AVAILABLE`, `DISABLED`, `NOT_AUTHORIZED`,
`MISCONFIGURED`, `DEGRADED`, or `UNKNOWN`.

The selected route is one of:

- `FULL_BROWSER_AND_DESKTOP`;
- `BROWSER_ONLY`;
- `BROWSER_WITH_MANUAL_DESKTOP`;
- `MANUAL_BROWSER_HANDOFF`;
- `LOCAL_CODEX_ONLY`;
- `BLOCKED`.

## Control hierarchy

For each action, choose the first authorized and verified option that can
complete it:

1. purpose-built connector, API, or CLI;
2. semantic built-in browser or signed-in Chrome control;
3. semantic third-party browser adapter;
4. accessibility-tree interaction;
5. explicit window targeting;
6. input synthesis with independently verified focus;
7. screenshots and visual reasoning;
8. raw coordinates only as the final fallback.

Desktop control is not required when browser semantics can complete the task.

## Linux

The Linux profile records these independently rather than treating them as one
generic adapter:

- signed-in Chrome control;
- Linux Computer Use MCP;
- Chrome DevTools MCP;
- Playwright-extension MCP.

For non-browser actions, the skill can use AT-SPI/accessibility trees, explicit
KWin/window identity, verified focus, portal screenshots, and bounded input
synthesis. It performs target/focus prechecks and semantic postcondition checks.
Transport success without an observed result is `OUTCOME_UNKNOWN`, not success.

Linux distributions, desktop environments, Wayland/X11 boundaries, portals,
and MCP configurations vary. No exact MCP namespace or binary is assumed until
discovered in the active environment.

## macOS

The preferred route remains semantic browser control. Desktop actions can
require separate macOS Privacy & Security grants such as Accessibility, Screen
Recording, Input Monitoring, or Automation. The skill inventories the actual
configured interfaces and permissions; it does not invent a connector or treat
one grant as authorization for another.

## Windows

The preferred route remains semantic browser control. Desktop fallbacks use
discoverable UI Automation/accessibility and explicit window/focus evidence.
The skill preserves UAC secure-desktop boundaries and does not bypass elevation
or synthesize input into an unverified target.

## Missing prerequisites

When a required layer is absent, the skill first offers a reduced or manual
route. If setup would materially help, it prepares an exact plan containing the
source, target, packages or extensions, permissions, configuration changes,
validation, rollback, and security impact. Installation or permission changes
occur only after the user approves that action boundary.

The skill never downloads software, changes services, weakens sandboxing,
enables sensitive browser access, changes groups/udev, or alters desktop
security merely because automation would become easier.

## Browser automation bars and screenshots

Chrome debugging or automation bars can change the content viewport and aspect
ratio. Screenshot lanes record outer-window and content-viewport geometry
separately, prefer semantic element/page capture, and remeasure after browser
chrome changes. A stale or wrong-target screenshot triggers a control recheck,
not coordinate guessing.
