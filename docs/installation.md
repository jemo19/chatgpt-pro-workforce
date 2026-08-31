# Installation

## Recommended: use the Codex skill installer

In Codex, ask the installed skill installer to fetch the exact nested skill
directory:

```text
$skill-installer Install the skill from https://github.com/jemo19/chatgpt-pro-workforce/tree/main/chatgpt-pro-workforce
```

The installer downloads public repositories directly and falls back to Git
when necessary. It names the destination from the requested path basename, so
the installed directory remains exactly `chatgpt-pro-workforce`.

Start a new Codex session after installation so discovery refreshes.

## Direct helper invocation

If the system skill installer is available locally:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo jemo19/chatgpt-pro-workforce \
  --path chatgpt-pro-workforce
```

The standard destination is `${CODEX_HOME:-$HOME/.codex}/skills/chatgpt-pro-workforce`.
An existing destination is not silently overwritten.

## Manual installation

Manual installation is a fallback. Clone the repository, validate the nested
skill, and copy that directory—not the entire repository—into an active
user-scoped skill root:

```bash
git clone https://github.com/jemo19/chatgpt-pro-workforce.git
cd chatgpt-pro-workforce
python3 tests/validate_skill.py chatgpt-pro-workforce
```

Determine the active user skill root from current Codex configuration before
copying. Do not assume that a path used by another machine is active locally.
Keep only one discoverable copy of the same skill name.

## Verify

In a new Codex session, run:

```text
Use $chatgpt-pro-workforce. Do not launch workers yet. Run the every-invocation readiness gate, show the guided kickoff, and report the discovered browser and computer-control route.
```

A safe first live check should use a disposable ChatGPT conversation and
non-sensitive exact-response prompt. It must not inspect cookies, tokens,
passwords, browser-profile data, unrelated tabs, or unrelated files.

## Update

Pause and checkpoint active workforce runs before updating. Validate a new copy
outside the active installation, preserve the current installation as a
timestamped backup outside discoverable skill roots, then replace the directory
atomically where supported. Start a new session and repeat the readiness smoke.

Do not merge new files into an old installation: stale references can remain
discoverable and invalidate the clean runtime inventory.

## Uninstall

The guided path is:

```text
$chatgpt-pro-workforce uninstall
```

The skill inventories the exact active installation, offers a recoverable
backup, asks for explicit confirmation, and removes only that verified target.
It does not remove research state, notes, artifacts, downloads, dashboards,
browser connectors, or computer-control prerequisites.

If the skill cannot be invoked, manually identify the exact active installation
from current Codex configuration, move it to a non-discoverable backup path,
and start a new session. Never delete a broad skill root or similarly named
directories as a shortcut.
