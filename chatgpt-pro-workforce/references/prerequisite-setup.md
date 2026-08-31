# Workload prerequisites and permission-gated setup

Use this reference after read-only capability preflight when the planned
workload needs a browser, upload/download, screenshot, or desktop-control layer
that is missing, disabled, misconfigured, or not authorized. An exposed but
`AVAILABLE_UNTESTED` interface should receive an authorized safe probe first;
offer setup only when that probe is unavailable for a known readiness reason or
it establishes a real defect.

## Contents

- [Boundary](#boundary)
- [Workload readiness](#workload-readiness)
- [Cross-platform discovery](#cross-platform-discovery)
- [Setup offer](#setup-offer)
- [Permission and change packet](#permission-and-change-packet)
- [Platform considerations](#platform-considerations)
- [Execution and verification](#execution-and-verification)
- [Failure and rollback](#failure-and-rollback)

## Boundary

Never silently install, enable, reconfigure, elevate, or broaden a control
layer. Missing prerequisites may enter a separate setup subflow only after the
user sees the exact proposed changes, permissions, security implications,
validation, rollback, and manual steps and explicitly approves the applicable
actions.

A broad statement such as “set up computer control” is sufficient to offer the
subflow, not to infer permission for an unknown package, administrator command,
browser extension, OS privacy grant, group/udev change, daemon, remote-debugging
endpoint, session switch, or security relaxation. Ask at the action boundary
once exact changes are known.

Do not request or store passwords, cookies, authentication tokens, recovery
codes, or private keys. Native credential and OS privacy dialogs remain a
bounded manual handoff unless an already-authorized semantic interface safely
handles them.

## Workload readiness

Map the proposed lanes to required and optional capabilities before offering
setup. Do not require desktop control when semantic browser control covers the
work.

| Workload need | Normally required | Optional fallback |
|---|---|---|
| Submit/reuse ChatGPT Pro lanes | Authenticated ChatGPT session, exact semantic browser/Chrome controller, target tab and composer identification | Manual browser handoff |
| Upload local inputs | Authorized browser upload plus visible attachment-presence check | Manual native dialog through bounded handoff |
| Recover native artifacts | Browser attachment/download path plus hashing/archive validation | Authorized desktop dialog, manual handoff, ZIP, bounded Base64 |
| Browser screenshots/visual review | Current target capture plus viewport/capture-geometry evidence | Target-scoped desktop capture |
| Native application/dialog work | Exact platform desktop interface, unique target, focus proof for input, and semantic postcondition | Manual handoff |
| Local verification | File/shell access plus actual validators, hashing, and safe archive tools | Manual artifact transfer to an authorized verifier |

Produce a readiness summary with each capability's exact discovered name,
state, required/optional role, limitation, and the smallest remediation that
would make the planned workload usable.

## Cross-platform discovery

Discover current interfaces from the actual skill/plugin/MCP/connector/CLI
catalog and trusted configuration. Do not invent a platform tool name.
Use [platform control stacks](platform-control-stacks.md) for the current OS and
preserve its live-versus-documentation truth boundary.

### Chrome and browser control

Look for the current signed-in Chrome/browser control interface and its skill
instructions. A surface may expose a name such as `chrome:control-chrome`, but
use that exact name only when it is actually discoverable. Determine whether it
connects to the user's authenticated browser context, an isolated browser, or
an extension-mediated context. Do not equate full CDP or remote debugging with
ordinary semantic Chrome control.

### Linux

Check the exact recognized `chrome:control-chrome`,
`mcp__computer_use_linux__*`, `mcp__chrome_devtools__*`, and
`mcp__playwright_extension__browser_*` families independently when exposed,
plus their actual semantic-browser, AT-SPI/accessibility, window-targeting,
focus, input, screenshot, and portal layers. The Linux Computer Use MCP is a
real known interface family but is not proof of host-native C17 support.

### macOS

Check the actual host for native Computer Use and configured semantic browser,
Accessibility, Screen Recording, Input Monitoring, window-targeting, and
screenshot interfaces. Do not invent an adapter. macOS privacy grants often
require a user action in System Settings; treat that as a specific manual step,
not blanket consent. Check the shared in-app/Chrome, DevTools, and Playwright
families when exposed. No exact macOS Computer Use MCP was live-verified in this
build, so discover and record its real name on the macOS host.

### Windows

Check the actual host for native Computer Use and configured semantic browser,
UI Automation/accessibility, window-targeting, focus, input, screenshot, and
file-dialog interfaces. Do not invent an adapter or assume administrator
rights. Never weaken UAC, Defender, browser protections, or organizational
policy to make automation easier. Check the shared in-app/Chrome-or-Edge,
DevTools, and Playwright families when exposed. No exact Windows Computer Use
MCP was live-verified in this build, so discover and record its real name on the
Windows host.

## Setup offer

When a required capability is not ready, tell the user:

- what planned work is unavailable or manual without it;
- the exact current capability state and evidence;
- whether a safe manual or reduced-workload route already exists;
- the smallest candidate setup or repair based on current trusted instructions;
- which permissions or native user actions it is likely to require;
- that no change will occur until the exact plan is approved.

Then ask one short question equivalent to:

> The planned workload needs {{CAPABILITY}}, but the current state is
> {{STATE}}. I can prepare and, where permitted, carry out a bounded setup with
> validation and rollback, or we can use {{MANUAL_OR_REDUCED_ROUTE}}. Would you
> like the setup plan?

Use setup states `NOT_NEEDED`, `READY`, `MISSING`, `OFFERED`,
`AWAITING_APPROVAL`, `IN_PROGRESS`, `MANUAL_ACTION_REQUIRED`, `VERIFIED`,
`FAILED`, `DECLINED`, or `BLOCKED`. These are setup-workflow states, not the
eight capability states.

## Permission and change packet

Create a packet from
[prerequisite plan template](../assets/prerequisite-plan-template.md) before
mutation. It must contain:

- exact target host/surface and workload need;
- exact missing interface/capability and evidence;
- trusted source or current installed documentation for the proposed setup;
- exact files, packages, extensions, configuration, services, permissions, or
  privacy settings that would change;
- whether administrator/elevated or native manual action is required;
- scope of browser/desktop access and least-privilege alternative;
- expected security impact and categorical no-weaken boundaries;
- exact validation probe and success criteria;
- rollback commands or manual reversal;
- download/network effects and artifacts retained;
- explicit approvals received and still missing.

Ask separately when targets or effects materially differ. Do not hide multiple
security-sensitive changes behind one yes/no question.

## Platform considerations

- **Browser extension/connect setup:** show the exact extension/plugin identity,
  source, requested permissions, browser context, and removal rollback. Do not
  enable broad remote debugging merely because it is convenient.
- **Linux:** package installation, daemon/service start, group/udev or uinput
  changes, portal/compositor configuration, and accessibility enablement need
  explicit exact approval. Prefer an already configured semantic or AT-SPI
  path. Validate the current display protocol and target compatibility.
- **macOS:** Accessibility, Screen Recording, Input Monitoring, Automation, and
  Files/Folders grants are distinct. Request only those required by the chosen
  route, give a manual System Settings handoff when needed, and recheck the
  actual grant afterward.
- **Windows:** installation, elevation, UI Automation/input privileges, browser
  extension permissions, firewall changes, and enterprise policy are distinct.
  Do not bypass UAC, Defender, SmartScreen, or organization controls.

If the environment's approval policy or administrator policy prohibits a
change, offer instructions/manual handoff or the reduced route; do not treat
technical capability as authorization.

## Execution and verification

After exact approval:

1. Reconfirm target, scope, source, version/channel when relevant, and rollback.
2. Preserve a before-state inventory without exposing secrets.
3. Perform only the approved bounded changes. Stop on unexpected prompts,
   targets, dependencies, privilege requests, or broader permissions.
4. Use manual handoff for native credential/privacy/extension confirmation
   dialogs when automation would be unsafe or self-approving.
5. Run the declared harmless readiness probe and a disposable functional test
   only when authorized.
6. Record output, state, exact interface name, version when observable, and
   limitations without credentials or unrelated desktop/browser content.
7. Re-run the complete read-only capability preflight and select the least
   powerful usable route.
8. Resume worker orchestration only after the required capabilities are
   `AVAILABLE_VERIFIED` or the user accepts a documented manual/degraded route.

Setup success does not grant permission for later worker submissions, uploads,
downloads, or desktop input; those remain governed by the run.

## Failure and rollback

On setup failure, preserve the exact safe error, stop before broadening changes,
and use the declared rollback where safe and authorized. Do not retry an
identical setup without new evidence. Mark the capability `MISCONFIGURED`,
`DEGRADED`, `NOT_AUTHORIZED`, or another exact capability state from the new
preflight, not from optimism.

If rollback itself is consequential, privileged, or ambiguous, stop and ask.
Retain the setup packet and link it from run state so pause/resume does not
repeat installation or permission requests.
