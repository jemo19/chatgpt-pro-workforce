# Local control profile

## Contents

- [Profile metadata](#profile-metadata)
- [Browser-control adapter](#preferred-browser-control-adapter)
- [Platform support stack](#platform-support-stack)
- [Linux control layers](#linux-control-layers)
- [Artifact recovery](#download-and-artifact-path)
- [Manual handoff](#manual-handoff)
- [Discovery notes](#optional-discovery-notes)

This file is a user-editable registry of control interfaces that may already be
available on one workstation. It is not proof that an adapter is currently
working, and it does not grant permission to use it. Keep volatile build- or
run-session evidence in the capability report; update this profile only when
the owner intends to retain a stable local convention.

Use only these layer states: `AVAILABLE_VERIFIED`, `AVAILABLE_UNTESTED`,
`NOT_AVAILABLE`, `DISABLED`, `NOT_AUTHORIZED`, `MISCONFIGURED`, `DEGRADED`, or
`UNKNOWN`.

## Profile metadata

```yaml
profile_version: 1
owner: local-user
platform:
  os: "<linux|other>"
  distribution: "<distribution-or-unknown>"
  desktop_environment: "<desktop-or-unknown>"
  display_protocol: "<wayland|x11|unknown>"
reported_state: UNKNOWN
last_verified_at: "<ISO-8601 timestamp>"
verified_by: "<Codex run or person>"
```

## Preferred browser-control adapter

Replace the placeholders after checking the actual skill/tool inventory.

```yaml
browser_adapter:
  id: "<exact discovered skill, MCP server, connector, or CLI name>"
  state: "<AVAILABLE_VERIFIED|AVAILABLE_UNTESTED|NOT_AVAILABLE|DISABLED|NOT_AUTHORIZED|MISCONFIGURED|DEGRADED|UNKNOWN>"
  class: "<native-browser|chrome-cdp|playwright|other-semantic-browser>"
  exposed_through: "<Codex skill|MCP|connector|CLI|desktop app>"
  discovery_evidence: "<where its exact name was observed>"
  safe_probe: "<read-only tab/page/title/snapshot action>"
  authenticated_session_policy: "reuse the user's logged-in browser session; never read cookies or tokens"
  upload_supported: "<yes|no|unknown>"
  download_supported: "<yes|no|unknown>"
  screenshots_supported: "<yes|no|unknown>"
  last_current_session_verification: "<ISO-8601 timestamp or never>"
  known_limitations:
    - "<limitation>"
```

## Platform support stack

Use [platform control stacks](platform-control-stacks.md) to record the current
OS's separately discovered browser, desktop/accessibility, window/focus,
screenshot, input, and manual-consent layers. On Linux, retain the exact
recognized `chrome:control-chrome`, `mcp__computer_use_linux__*`,
`mcp__chrome_devtools__*`, and `mcp__playwright_extension__browser_*` records.
On macOS or Windows, record the exact desktop interface exposed by that host;
do not fill a plausible MCP name from this template.

```yaml
platform_support_stack:
  platform: "<linux|macos|windows|other>"
  last_inventory_check: "<ISO-8601 timestamp or never>"
  browser_interfaces: ["<exact names or none>"]
  desktop_interface: "<exact name or unknown>"
  accessibility_interface: "<exact name or unknown>"
  window_focus_interface: "<exact name or unknown>"
  screenshot_interface: "<exact name or unknown>"
  input_interface: "<exact name or unknown>"
  manual_consent_route: "<exact route or unknown>"
```

## Linux control layers

Record each layer independently; one adapter may implement several layers. Use
semantic accessibility or explicit window targeting before input synthesis.
Machine-specific populated values belong in the per-run capability report or an
operator-owned inventory, not in this packaged template.

```yaml
desktop_layers:
  accessibility_tree:
    id: "<exact discovered name or unknown>"
    state: "<one allowed capability state>"
    exposed_through: "<MCP|CLI|desktop app|unknown>"
    session_compatibility: "<Wayland|X11|XWayland|desktop-specific|unknown>"
    method: "<exact target-scoped snapshot/action method or unknown>"
    safe_probe: "<target-scoped read-only probe>"
    target_method: "<stable semantic selector or unknown>"
    limitations: ["<limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
  window_targeting:
    id: "<exact discovered name or unknown>"
    state: "<one allowed capability state>"
    session_compatibility: "<value>"
    method: "<exact narrow list/target method or unknown>"
    safe_probe: "<target-scoped read-only probe>"
    target_method: "<window handle plus app/class/title constraints or unknown>"
    limitations: ["<limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
  focus_verification:
    id: "<exact discovered name or unknown>"
    state: "<one allowed capability state>"
    method: "<exact focused-window/control method or unknown>"
    safe_probe: "<read-only focus observation>"
    limitations: ["<limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
  input_synthesis:
    id: "<exact discovered name or unknown>"
    state: "<one allowed capability state>"
    session_compatibility: "<value>"
    method: "<exact keyboard/pointer method or unknown>"
    safe_probe: "<disposable target plus independent focus proof, or not run>"
    privilege_requirements: "<none|existing user service|other|unknown>"
    limitations: ["<limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
  screenshot_capture:
    id: "<exact discovered name or unknown>"
    state: "<one allowed capability state>"
    session_compatibility: "<value>"
    method: "<exact target-scoped capture method or unknown>"
    safe_probe: "<fresh bounded non-blank capture probe>"
    capture_surface: "<page|element|content-viewport|browser-window|application-window|display-region|unknown>"
    outer_window_dimensions: "<width x height or unknown>"
    content_viewport_dimensions: "<width x height or unknown>"
    device_scale: "<value or unknown>"
    chrome_automation_debug_infobar: "<present|absent|unknown|not-applicable>"
    top_inset_and_crop: "<value or none>"
    limitations: ["<portal prompt, scale, crop, or other limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
  native_computer_use:
    id: "<exact host-native name or unknown>"
    state: "<one allowed capability state>"
    method: "<exact method or unknown>"
    limitations: ["<limitation>"]
    last_current_session_verification: "<ISO-8601 timestamp or never>"
authorization_boundary: "each desktop action requires current task authority and the per-action gate"
```

## Download and artifact path

These interface paths do not define retention or deletion authority. Store
those choices in the workforce profile and follow
[artifact storage and cleanup](artifact-storage-and-cleanup.md).

```yaml
artifact_recovery:
  browser_download_directory: "<path or unknown>"
  native_dialog_handler: "<adapter id or manual>"
  quarantine_directory: "<path for untrusted downloads>"
  accepted_artifact_directory: "<project-specific path>"
  hashing_command: "<exact discovered command or unknown>"
  archive_list_command: "<exact discovered command or unknown>"
  archive_test_command: "<exact discovered command or unknown>"
```

## Manual handoff

```yaml
manual_handoff:
  state: "<AVAILABLE_VERIFIED|AVAILABLE_UNTESTED|NOT_AVAILABLE|DISABLED|NOT_AUTHORIZED|MISCONFIGURED|DEGRADED|UNKNOWN>"
  available: "<true|false|unknown>"
  last_current_session_verification: "<ISO-8601 timestamp or never>"
  allowed_for:
    - login or reauthentication
    - sensitive approval prompts
    - native dialogs that no authorized adapter can access
    - final confirmation for consequential external actions
  never_request:
    - passwords in chat
    - session cookies
    - authentication tokens
    - private keys
```

## Optional discovery notes

Record only information needed to select the correct control path. Do not store
browser-profile secrets, cookie databases, token values, or unrelated history.
Do not use an unverified `--help`, discovery, window-list, application-list, or
full-screen command when it may execute work or expose unrelated desktop state;
inspect the adapter's registered tool schema or trusted local documentation
first, then request the narrowest target-scoped result.

```text
Exact browser adapter discovered:
Exact desktop adapter discovered:
Current display protocol:
Current ChatGPT tab/conversation identification method:
Current download recovery method:
Current screenshot surface/viewport/infobar geometry:
Last successful safe probes:
Known failure signatures:
```
