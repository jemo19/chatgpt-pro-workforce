# Platform browser and computer-control stacks

## Contents

- [Truth boundary](#truth-boundary)
- [Shared browser layers](#shared-browser-layers)
- [Linux](#linux)
- [macOS](#macos)
- [Windows](#windows)
- [First-use and invocation checks](#first-use-and-invocation-checks)
- [Setup and verification](#setup-and-verification)

Use this reference during first-use readiness, on every invocation's platform
gate, after a control fault, and when the user asks to complete or troubleshoot
the recommended support stack.

## Truth boundary

Platform guidance describes the layers to discover; only the active tool
inventory and a safe current-session probe establish an interface's exact name
and state. Never invent `mcp__computer_use_macos__*`,
`mcp__computer_use_windows__*`, or any other plausible name. The reference Linux
host exposed exact names that can be recognized elsewhere; the macOS and Windows
desktop layers below are documentation-backed requirements, not live-tested
Codex interfaces.

Use only the eight capability states from
[capability preflight](capability-preflight.md). Presence without a safe probe
is at most `AVAILABLE_UNTESTED`. Tool availability never grants permission.

## Shared browser layers

Check these independently on all platforms:

| Layer | Exact recognized interface when exposed | Role and boundary |
|---|---|---|
| In-app browser | `browser:control-in-app-browser` through `agent.browsers.get("iab")` | Separate browser state. OpenAI currently documents the desktop built-in browser for macOS and Windows; do not assume it shares Chrome authentication. |
| Signed-in Chrome | `chrome:control-chrome` through `agent.browsers.get("chrome")` | Primary route when the lane needs the user's existing Chrome profile and logged-in ChatGPT session. |
| Signed-in Edge | A currently exposed Edge-capable browser controller through `agent.browsers.get("edge")` | Windows alternative only when the exact skill/runtime supports it and the user selects or authorizes that browser family. |
| Chrome DevTools | `mcp__chrome_devtools__*` | Auxiliary inspection, screenshot, console, network, performance, and local-page testing. Treat full CDP/developer access as sensitive. |
| Playwright extension | `mcp__playwright_extension__browser_*` | Auxiliary structured browser inspection/testing. Verify whether it controls an extension-mediated, persistent, or isolated context. |

The DevTools and Playwright families do not automatically share the signed-in
Chrome controller's context. Never substitute them for authenticated ChatGPT
work until current target and session identity are safely verified. Never read
cookies, tokens, passwords, profiles, unrelated tabs, or unrelated history.

Current primary references:

- OpenAI built-in browser and Chrome distinction:
  https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app
- Chrome DevTools for agents:
  https://developer.chrome.com/docs/devtools/agents
- Playwright MCP:
  https://playwright.dev/mcp/

## Linux

The recommended Linux support stack recognizes four exact interface families
that were exposed on the reference workstation:

| Readiness record | Exact interface | Purpose |
|---|---|---|
| `LINUX_SIGNED_IN_CHROME` | `chrome:control-chrome` / `agent.browsers.get("chrome")` | Authenticated semantic ChatGPT route. |
| `LINUX_COMPUTER_USE_MCP` | `mcp__computer_use_linux__*` | Desktop readiness plus AT-SPI, window/focus, screenshot, and input layers. Begin this family with `mcp__computer_use_linux__get_app_state`. |
| `LINUX_CHROME_DEVTOOLS_MCP` | `mcp__chrome_devtools__*` | Auxiliary Chrome debugging and visual inspection. |
| `LINUX_PLAYWRIGHT_EXTENSION` | `mcp__playwright_extension__browser_*` | Auxiliary extension-mediated semantic browser testing. |

Record all four separately on first use and re-check exposure on every
invocation. A complete recommended Linux stack has all four discoverable, but
route readiness remains action-specific: Chrome is required for authenticated
Pro lanes; Linux Computer Use is required only for an automated desktop gap;
DevTools and Playwright are auxiliary unless a lane explicitly needs them.

`mcp__computer_use_linux__*` is an exact MCP interface, not a hypothetical
adapter and not automatically native Computer Use under C17. Use the readiness
result's actual accessibility, compositor/window, portal/screenshot, input, and
focus backends. Follow [Linux control options](linux-control-options.md) before
any non-browser action.

## macOS

macOS could not be live-tested in this build. During `INITIAL_BASELINE`, create
separate records for:

| Readiness record | Required discovery |
|---|---|
| `MAC_BROWSER` | Current in-app browser, signed-in Chrome, DevTools, and Playwright-extension interfaces from the shared table. |
| `MAC_COMPUTER_USE` | Exact host-native or configured Computer Use interface name, if exposed; otherwise `NOT_AVAILABLE` or `UNKNOWN` from evidence. |
| `MAC_ACCESSIBILITY` | Exact adapter using the macOS Accessibility/AXUIElement hierarchy; prove one harmless target tree before `AVAILABLE_VERIFIED`. |
| `MAC_WINDOW_FOCUS` | Exact application/window identity and focus-observation methods, preferably PID plus bundle/window identity. |
| `MAC_SCREEN_CAPTURE` | Target-scoped capture method and current Screen & System Audio Recording authorization. |
| `MAC_INPUT` | Exact semantic action or input method, independently verified focus, and postcondition; input presence alone remains `AVAILABLE_UNTESTED`. |
| `MAC_MANUAL_CONSENT` | User handoff for System Settings privacy grants, native credential dialogs, or other OS-owned consent. |

Apple documents Accessibility, Automation, Input Monitoring, Screen & System
Audio Recording, and Files & Folders as distinct privacy controls. Ask only for
the grant required by the selected action; do not request Full Disk Access as a
shortcut. Accessibility clients can use AXUIElement semantics when the target
supports them, but incomplete application accessibility is `DEGRADED`, not a
reason for blind coordinates.

Current primary references:

- Apple Privacy & Security controls:
  https://support.apple.com/guide/mac-help/change-privacy-security-settings-on-mac-mchl211c911f/mac
- Apple AXUIElement API:
  https://developer.apple.com/documentation/applicationservices/axuielement_h

## Windows

Windows could not be live-tested in this build. During `INITIAL_BASELINE`,
create separate records for:

| Readiness record | Required discovery |
|---|---|
| `WINDOWS_BROWSER` | Current in-app browser, signed-in Chrome or Edge, DevTools, and Playwright-extension interfaces from the shared table. |
| `WINDOWS_COMPUTER_USE` | Exact host-native or configured Computer Use interface name, if exposed; never infer one from platform support. |
| `WINDOWS_UI_AUTOMATION` | Exact adapter using Microsoft UI Automation/accessibility patterns; prove one harmless target tree/control. |
| `WINDOWS_WINDOW_FOCUS` | Exact HWND/application identity, foreground/focus observation, and target continuity. |
| `WINDOWS_SCREEN_CAPTURE` | Exact target-scoped Windows Graphics Capture, PrintWindow, or other reported capture method and its limitations. |
| `WINDOWS_INPUT` | Prefer UI Automation Invoke/Value patterns; use input injection only with immediate foreground/focus proof and an observable postcondition. |
| `WINDOWS_MANUAL_CONSENT` | User handoff for UAC secure-desktop prompts, credentials, browser permission prompts, or unavailable elevated targets. |

UI Automation exposes application controls as a semantic tree, while standard
input injection can affect the foreground desktop. Keep UAC and the secure
desktop outside automated consent; never disable UAC, Defender, SmartScreen, or
organization policy. Do not request administrator rights merely to make a
desktop route easier.

Current primary references:

- Microsoft UI Automation providers:
  https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-providersoverview
- Microsoft Windows app UI Automation and foreground-input safeguards:
  https://learn.microsoft.com/en-us/windows/apps/dev-tools/winapp-cli/ui-automation

## First-use and invocation checks

On first invocation, show the relevant platform records, current states, which
ones the proposed workload actually needs, and the recommended complete-stack
gaps. Do not ask the user to know interface names. Ask whether they want to set
up a missing optional support layer only after explaining its value,
permissions, security impact, manual alternative, and rollback.

On every invocation, re-check exact tool/skill exposure and the volatile
requirements for the last route. Do not repeat side-effecting probes. On a
fault, freeze new submissions/input, re-check the browser chain, then only the
desktop layers required by the failed action. Persist capability deltas and
never carry a macOS/Windows simulated result forward as current-host proof.

## Setup and verification

Follow [prerequisite setup](prerequisite-setup.md). Installation, extension
connection, OS privacy grants, browser developer access, elevation, services,
drivers, groups, and security-setting changes always require an exact plan and
separate approval. The skill may guide the user through manual OS consent, but
must never click or type approval for them.

After any approved setup, run `FULL_RECHECK`. Promote only the layers whose
exact current-session probes succeed. Preserve a browser-only, manual desktop,
manual browser, local-only, or blocked route when the full stack is unavailable.
