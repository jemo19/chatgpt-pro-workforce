# Capability preflight

## Contents

- [Inputs](#1-inputs)
- [Invocation levels and triggers](#invocation-levels-and-triggers)
- [Capability states](#2-capability-states)
- [Capability matrix](#3-capability-matrix)
- [Discovery rules](#4-discovery-rules)
- [Safe probes](#5-safe-probes)
- [Route selection](#6-route-selection)
- [Required output](#7-required-preflight-output)
- [Stop conditions](#8-preflight-stop-conditions)

Run a safe readiness gate at the start of every skill invocation and the full
preflight before any ChatGPT Pro worker conversation is opened, reused, or
modified. Its purpose is to discover what is actually available and permitted
in the current host, not to prove that every possible control path works.

## Invocation levels and triggers

Use exactly these levels:

| Level | When | Required behavior |
|---|---|---|
| `INITIAL_BASELINE` | First invocation after install, missing/untrusted workforce profile, or no accepted baseline | Run safe discovery across C01-C26 plus the current-OS records in `platform-control-stacks.md`, persist the report and exact interface names, and do not launch a worker during the baseline. |
| `INVOCATION_GATE` | Every invocation, including bare kickoff, help, status, pause, and resume | Reconfirm current skill/tool exposure, required browser/controller presence, safely targetable run context when applicable, local validation access, and the last route's volatile prerequisites. It is read-only. |
| `FAULT_DIAGNOSTIC` | A browser/desktop/control symptom occurs | Freeze new submissions/input, preserve state, probe the affected dependency chain, and follow bounded repair in monitoring and recovery. |
| `FULL_RECHECK` | Capability/route/configuration/session changes, an approved prerequisite completes, or fault repair changes evidence | Re-run all workload-relevant C01-C26 probes and select the least powerful authorized route from fresh evidence. |

Use only these triggers: `FIRST_INVOCATION`, `EVERY_INVOCATION`, `RESUME`,
`CONTROL_FAULT`, `CONFIGURATION_CHANGE`, and `POST_SETUP`. Each record contains
`preflight_id`, `preflight_started_at`, `preflight_level`, `preflight_trigger`,
`preflight_result`, `capability_delta`, and `last_verified_route`.

Installation-time build evidence may demonstrate that a controller existed,
but it does not replace `INITIAL_BASELINE` in the user's actual invocation
session. An `INVOCATION_GATE` must not create a new conversation, type, submit,
upload, download, capture unrelated content, enumerate unrelated windows, or
send desktop input. For status/help, use a safe target-scoped observation only
when already authorized; otherwise report the relevant layer `UNKNOWN` or
`AVAILABLE_UNTESTED` and keep the request read-only.

## 1. Inputs

Inspect, in this order:

1. user and project instructions;
2. repository and parent `AGENTS.md` files;
3. the current host/surface: desktop app, CLI, IDE extension, cloud task, or
   other runner;
4. discoverable skills, plugins, connectors, MCP tools, and CLIs;
5. `references/platform-control-stacks.md` for the current OS;
6. `references/local-control-profile.md`;
7. previous lane-state, prerequisite-plan, or handoff notes for this run;
8. the workforce profile's previous baseline, invocation gate, and route.

Never infer a capability merely because it existed in an earlier run.

## 2. Capability states

Use only these states:

- `AVAILABLE_VERIFIED`: present and a safe current-session probe succeeded;
- `AVAILABLE_UNTESTED`: present, but no safe probe was possible or authorized;
- `NOT_AVAILABLE`: not exposed or not installed;
- `DISABLED`: present but turned off by user, admin, workspace, or host policy;
- `NOT_AUTHORIZED`: technically available but this run lacks permission;
- `MISCONFIGURED`: present but a safe probe failed for a known configuration
  reason;
- `DEGRADED`: usable with a material limitation;
- `UNKNOWN`: evidence is insufficient.

Do not collapse `NOT_AUTHORIZED`, `DISABLED`, and `NOT_AVAILABLE` into one state.
Capability-matrix state fields may contain only these eight values. User reports,
historical success, and executable presence belong in evidence; they never form
an additional state.

## 3. Capability matrix

Assess the following capabilities separately:

| ID | Capability | Minimum acceptable evidence |
|---|---|---|
| C01 | Local file and shell access | Current host exposes authorized file reads/writes and required local validator commands. |
| C02 | Skill/tool discovery | Codex can inspect currently available skills, plugins, connectors, MCP tools, and CLIs. |
| C03 | Authenticated ChatGPT session | A ChatGPT page is reachable in an authenticated context without reading credentials or unrelated history. |
| C04 | Native built-in browser control | The host-provided in-app browser is exposed; current-session interaction requires a separate probe. |
| C05 | Chrome or compatible signed-in browser control | The exact external-browser controller can bind to the intended authenticated browser family. |
| C06 | Intended ChatGPT tab identification | The controller can create or identify the target tab without guessing an ID or inspecting unrelated tabs. |
| C07 | Multiple conversation/tab distinction | Stable tab and conversation identities prevent lane crossover when more than one ChatGPT conversation exists. |
| C08 | Semantic page inspection | The controller can read current visible or accessibility state and target semantic elements. |
| C09 | Composer targeting | The intended conversation's composer can be located and checked for stale or duplicate text. |
| C10 | New-conversation creation | A disposable fresh conversation can be created without altering an unrelated conversation. |
| C11 | Existing-conversation reuse | An existing lane conversation can be re-identified from durable safe identity and claimed without guessing. |
| C12 | File upload | A supported upload action exists for authorized files and attachment presence can be verified before submission. |
| C13 | Native attachment download | A worker-created attachment can be activated and its recovered bytes identified. |
| C14 | Browser-managed download | A browser download event or browser-accessible URL can be recovered without desktop coordinates. |
| C15 | Screenshot capture | A browser or desktop path produces a current, non-blank, target-identified capture with timestamp/sequence, capture surface, outer-window and content-viewport dimensions when applicable, device scale, automation/debugging-infobar inset/crop, and portal limitations recorded. |
| C16 | Download-directory discovery | The actual recovery directory or controller-managed returned path can be identified without broad filesystem search. |
| C17 | Native Computer Use | A host-provided Computer Use capability is exposed and enabled for this platform; do not label a third-party MCP native merely from its name. |
| C18 | Third-party semantic browser adapter | A configured semantic browser MCP or CLI is exposed and its browser-context assumptions are known. |
| C19 | Linux accessibility control | An authorized AT-SPI/accessibility-tree adapter can enumerate a named harmless target; an absent or partial target tree is `DEGRADED` or `NOT_AVAILABLE` from evidence. |
| C20 | Explicit window enumeration/targeting | An authorized adapter can identify one unique target without retaining unrelated windows and without relying only on coordinates. |
| C21 | Keyboard or mouse input synthesis | An authorized adapter can input in a disposable controlled target; executable presence alone is insufficient. |
| C22 | Independent focus verification | A separate observation can prove the intended window/control has focus immediately before input and confirm the result afterward. |
| C23 | Manual native-dialog handoff | Current-session user availability for login, native upload/download dialogs, or sensitive prompts is verified, or remains `AVAILABLE_UNTESTED`/`UNKNOWN`. |
| C24 | Hashing and archive validation | Local tools can hash files, inventory archives without extraction, reject unsafe members, and run required validators. |
| C25 | ChatGPT Pro account entitlement | The target authenticated session exposes safe visible semantic evidence that the account has Pro. A remembered subscription, worker quality, or prior run is insufficient. |
| C26 | Target conversation Pro model and maximum thinking power | The exact target conversation exposes semantic proof that the declared model is selected and the thinking-power control reports `Pro, 5 of 5`. Account entitlement or a collapsed `Pro` label alone is insufficient. |

## 4. Discovery rules

### 4.1 Do not invent interfaces

Inspect the actual skill/tool catalog, MCP list, connector list, CLI help, or
configured local profile. Record exact discovered names. Never write a call for
a tool that has not been observed.

### 4.2 Prefer host-native capabilities

Check native built-in browser and Chrome/compatible signed-in control
separately. Full CDP or developer-mode access is not required for ordinary
semantic browser interaction; treat it as a separate sensitive capability that
may require explicit approval.

Check native Computer Use separately from browser use. A platform may support
browser actions while not supporting arbitrary desktop application control.

### 4.3 Check configured third-party adapters

On Linux, inspect the local profile and current MCP/CLI inventory for the
adapter categories described in `linux-control-options.md`. Presence does not
imply authorization. On macOS and Windows, likewise discover the actual native
Computer Use, semantic browser, accessibility/UI Automation, window/focus,
input, screenshot, and manual-handoff surfaces. Do not invent a platform
adapter from a generic product name.

Use [platform control stacks](platform-control-stacks.md) to create separate
current-OS readiness records. On Linux, explicitly recognize
`chrome:control-chrome`/`agent.browsers.get("chrome")`,
`mcp__computer_use_linux__*`, `mcp__chrome_devtools__*`, and
`mcp__playwright_extension__browser_*` when those exact families are exposed.
On macOS and Windows, recognize the shared browser families but discover the
exact desktop interface name at runtime; no platform-specific Computer Use MCP
name was live-discoverable in this build. Never carry Linux verification into a
macOS or Windows record.

Discovery is read-only. Do not install, start daemons, grant accessibility or
screen/input privileges, alter groups/udev/portals/sessions, enable sensitive
debugging, or change security settings during preflight. If a workload-required
capability is missing, classify it first and then use
[prerequisite setup](prerequisite-setup.md) to offer an exact permission-gated setup, a manual or
reduced route, or a workload change. After an approved setup, rerun this entire
preflight; do not promote capability state from setup-command success alone.

### 4.4 Map readiness to the workload

For every planned action, mark each relevant capability `required`, `optional`,
or `not needed`. A Pro lane requires authenticated ChatGPT access, verified Pro
account entitlement, verified declared-model selection and maximum `Pro, 5 of
5` thinking power in the exact target conversation,
an exact submission route, and an output-recovery route. Upload, native desktop,
or visual-capture layers are required only when the lane contract needs them.
Do not force arbitrary desktop control into a browser-only workload.

## 5. Safe probes

A safe probe is read-only or has a trivial, reversible effect in a controlled
context.

Every `INVOCATION_GATE` must, at minimum:

1. record the active host/surface and exact exposed browser and desktop-control
   interface names without trusting the prior catalog;
2. confirm local state/report access and hashing/validator availability;
3. when a Pro run is active or requested, confirm the configured browser
   controller is exposed and the intended ChatGPT target can be identified
   semantically without reading unrelated tabs;
4. confirm only the action-scoped desktop adapter layers needed by the current
   workload, without synthesizing input;
5. compare results with the previous accepted route and record a capability
   delta, including `none observed` when supported by evidence;
6. select `PASS`, `DEGRADED`, or `BLOCKED` for the invocation and preserve the
   next safe route.

The invocation gate may confirm that C25 and C26 can be checked, but it must not
change a model/mode selector during a read-only `status` or `help` request. The
submission-bound Pro gate below owns the final current-state proof.

On Linux, step 1 separately re-checks exposure of the four recognized support
families. On macOS and Windows, it separately re-checks the current built-in or
signed-in browser route plus the exact desktop/accessibility, window/focus,
screenshot, and input interface names discovered for that host.

Do not reuse `AVAILABLE_VERIFIED` solely because an executable, profile entry,
or old report still exists. Conversely, do not perform a live typing/download
smoke test on every invocation: keep the gate proportional and read-only, then
use `FULL_RECHECK` when the current evidence changed.

Preferred browser probe:

1. create a disposable tab when possible, or identify only a user-designated
   tab without enumerating unrelated tabs or history;
2. confirm the exact browser family, page URL/title, and stable tab handle;
3. read only the minimum semantic state needed to identify the composer;
4. confirm authenticated state without reading account secrets;
5. verify the composer can be targeted without typing;
6. if authorized and required, submit one harmless exact-response prompt in a
   fresh conversation and record the safe URL/identifier, time, response, and
   whether targeting was semantic. Honor any controller action-time
   confirmation policy.

### 5.1 ChatGPT Pro submission gate

Apply this gate to every ChatGPT Pro lane immediately before each prompt is
submitted. Run it after creating, reopening, reusing, resuming, rebinding, or
recovering a conversation, and again after a page reload, model-control change,
provider fallback/limit notice, or any evidence that the selected mode drifted.

1. Identify the exact target conversation and its composer semantically.
2. Read safe account-level UI evidence for C25. A profile or plan label may
   prove entitlement, but never proves the target conversation's mode.
3. Inspect the target conversation's visible semantic model/mode control. Use
   its accessible name and selected, current, checked, or pressed state. Discover
   the current labels; do not depend on a brittle selector or fixed coordinates.
   Verify all three independent facts: the account is entitled to Pro, the
   declared model is selected, and the thinking-power control reports exactly
   `Pro, 5 of 5`.
4. Classify the observation as exactly one of `PRO_MAX_POWER_VERIFIED`,
   `PRO_LOWER_POWER`, `PRO_MODEL_NOT_SELECTED`, `PRO_UNAVAILABLE`,
   `PRO_AMBIGUOUS`, `PRO_LIMITED_OR_FALLBACK`, or `UNKNOWN`. `High` is always
   `PRO_LOWER_POWER`; a collapsed button reading only `Pro` is ambiguous.
5. If Pro is available but the declared model or maximum power is not selected
   and browser interaction is already authorized, select the model semantically,
   move the thinking-power control to its maximum, close and reopen the selector,
   then independently re-read it. A successful click or slider action without
   the checked model and exact `Pro, 5 of 5` postcondition is `UNKNOWN`, not
   success. This reopened reading is the required selected-state postcondition.
6. Allow submission only when C25 and C26 are both `AVAILABLE_VERIFIED` and the
   final observation is `PRO_MAX_POWER_VERIFIED`. Persist the evidence before
   typing and repeat the selector verification immediately before submitting
   the prompt.

Never infer active maximum-power Pro from the account badge, a prior
conversation, remembered defaults, URL shape, prompt wording, response quality,
the collapsed `Pro` button, or the mere presence of a Pro option. Do not silently
accept `High`, an automatic or reduced model, a provider fallback, or an
ambiguous localized control as maximum-power Pro. If entitlement, selected
model, or exact `Pro, 5 of 5` power cannot be proved, freeze that lane before
input, report the minimal observed state, and ask the user to select or restore
Pro. After manual action, re-identify the target and run this gate again. There
is no degraded or manual bypass that may be labeled a maximum-power ChatGPT Pro
submission.

For multiple-conversation capability, prefer distinct disposable tab handles or
documented stable identities. Do not open unrelated user tabs merely to prove
enumeration. For upload and download, record API/tool support as
`AVAILABLE_UNTESTED` until an authorized harmless end-to-end probe succeeds.

Preferred screenshot probe:

1. identify whether the capture is a page/element, content viewport, browser
   window, application window, or display region;
2. capture one current browser or desktop image;
3. confirm it is not blank, stale, black, or the wrong target;
4. for Chrome/browser captures, detect browser chrome and any automation,
   debugging, or control infobar at the top; record outer-window dimensions,
   content-viewport dimensions, device scale, top inset, and crop when exposed;
5. prefer semantic page/element or content-viewport capture for visual review;
   do not treat an infobar-induced aspect change as an application defect and
   do not close or disable the bar merely to improve the capture;
6. record target identity, timestamp/sequence, and portal/scale limits;
7. delete it after the run if it contains sensitive context and retention is
   not required.

Preferred desktop accessibility probe:

1. enumerate the active application or a harmless test application;
2. identify one window and one non-sensitive control by semantic properties;
3. do not click, type, close, move, or resize anything.

Linux prechecks must also determine, without mutation:

- actual session display protocol independently of the desktop name;
- target protocol when observable rather than assuming X11/XWayland/Wayland;
- portal and target-scoped screenshot availability;
- whether the named target exposes a useful accessibility tree;
- unique window-targeting and independent focus-observation capability;
- screenshot freshness, dimensions, scale, and intended target;
- current-session manual-handoff availability.

Do not use broad application/window lists, full-screen captures, or guessed CLI
flags when a target-scoped probe exists. Treat partial trees, portal prompts,
and compatibility uncertainty as limitations, not permission to fall through
to coordinates.

Input-synthesis probe is optional and should normally be deferred until a real
authorized action is necessary. When used, target a disposable test window and
verify focus before and after the action.

Before any prompt submission, compare the final prompt hash, lane ID, and
conversation identity with durable lane state and the visible message list. If
an identical active or completed submission exists, select it as canonical and
suppress the duplicate.

## 6. Route selection

Select the least powerful route that can complete the authorized task.
Route selection is per action: purpose-built or browser control remains primary
for every supported action. A desktop layer is eligible only for one named
browser-semantic gap after its target/focus/postcondition gate passes.

| Route | Required capabilities | Meaning |
|---|---|---|
| `FULL_BROWSER_AND_DESKTOP` | C03, one verified semantic browser path, C06, C08-C09, an adequate upload/recovery path, and verified C19-C22 as needed | Browser remains primary; one or more named actions have action-scoped verified desktop fallbacks. This is never blanket desktop authority. |
| `BROWSER_ONLY` | C03, one verified semantic browser path, C06, C08-C09, and adequate in-browser upload/recovery | Expected work remains inside semantic browser control and browser-managed recovery. |
| `BROWSER_WITH_MANUAL_DESKTOP` | Verified browser submission plus C23 and C24 | Browser work is automated; the user handles native dialogs or local placement. |
| `MANUAL_BROWSER_HANDOFF` | C23 and C24 | Codex prepares prompts and verifies recovered outputs; the user performs browser actions. |
| `LOCAL_CODEX_ONLY` | C01 and C24 | External workers are unnecessary or unavailable; Codex completes the task locally. |
| `BLOCKED` | No authorized submission or recovery path | The requested external-worker workflow cannot proceed safely. |

Do not select `FULL_BROWSER_AND_DESKTOP` solely because low-level coordinate
clicking appears possible.

If the least sufficient route depends on a missing capability, do not select a
stronger route optimistically. Record the missing requirement and setup state,
then offer the permission-gated prerequisite, manual/reduced route, or workload
change. Only `VERIFIED` setup followed by a successful full preflight—or an
explicitly accepted manual/degraded route—can unblock worker launch.

## 7. Required preflight output

Create one report from `assets/capability-report-template.md` containing:

- preflight ID, level, trigger, start/completion timestamp, result, previous
  route, current route, and capability delta;
- timestamp and host/surface;
- OS, desktop, display protocol, and browser when observable;
- exact discovered adapter names;
- capability matrix with evidence and state;
- sensitive approvals that were not requested or not granted;
- selected route and rationale;
- separate accessibility, window-targeting, focus, input, screenshot/portal,
  and manual-handoff layer records;
- workload-required versus optional capabilities and the prerequisite setup
  ID, state, plan path, manual alternative, or declined choice;
- screenshot capture surface, outer-window versus content-viewport geometry,
  device scale, Chrome automation/debugging-infobar presence and inset/crop;
- any action-scoped desktop plan with target proof, focus proof, expected
  postcondition, attempt ceiling, and fallback/stop route;
- expected limitations;
- conditions that require re-probing.

## 8. Preflight stop conditions

Stop before external submission when:

- the target account or conversation cannot be identified safely;
- the only available method would require secrets, cookie extraction, or
  unrelated browser history inspection;
- the only path requires setup, privilege, a daemon, or a policy change that
  lacks exact approval or exceeds the approved prerequisite packet;
- the only path requires weakening a browser, OS, workspace, or security
  control;
- output recovery cannot be completed or handed off;
- the user requested a specific external-worker path and no authorized route
  exists.

A failed preflight is a documented capability result, not permission to
improvise. It may lead to a permission-gated setup offer, but the offer itself
does not authorize any mutation.
