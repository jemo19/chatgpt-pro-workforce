# Installation lifecycle and safe uninstall

Use this reference for `help install`, `help uninstall`, or an explicit
`$chatgpt-pro-workforce uninstall` intent. Installation and removal are local
skill-lifecycle operations, not worker lanes.

## Standard install shape

The installable unit is one directory named exactly
`chatgpt-pro-workforce` containing `SKILL.md`, `agents/openai.yaml`, and only
the runtime references, assets, and scripts routed by the skill. Use the
currently discoverable user-scoped skill root selected by Codex configuration
and current skill-creator guidance. Respect an explicit user-selected active
root. Never install the skill into a project, vault, browser profile, system
skill root, or unrelated application directory merely because it is writable.

Before installation or replacement:

1. resolve the exact user-scoped destination and prove it is discoverable;
2. reject a symlinked destination or ambiguous same-name active copies;
3. validate a clean staged candidate with the current authoritative
   skill-creator validator and independent link/inventory checks;
4. preserve an existing installation in a timestamped, non-discoverable backup;
5. copy to a temporary sibling, validate it, and replace atomically where the
   filesystem supports that operation;
6. validate the installed copy and compare its complete byte inventory with
   the accepted stage;
7. state honestly when skill discovery requires a new Codex session.

Do not add a daemon, global package, shell startup edit, privileged installer,
browser security change, or external dependency just to install this skill.

## Uninstall intent

`$chatgpt-pro-workforce uninstall` starts a guided, recoverable uninstall. It
does not remove anything immediately. Treat uninstall as destructive even when
the user owns the files.

First perform the mandatory read-only invocation gate, then:

1. Resolve the exact active installation that supplied this skill. Verify its
   canonical directory name, `SKILL.md` frontmatter name, ownership where the
   platform exposes it, non-symlink identity, file count, byte count, and
   inventory digest. Never act on a glob, a merely similar name, an unresolved
   environment variable, a skill root, or more than one target.
2. Enumerate other active same-name copies and non-discoverable backups as
   separate evidence. Do not remove or replace any of them implicitly.
3. State what uninstall does **not** remove: research projects, Obsidian notes,
   worker downloads, accepted artifacts, run state, dashboard data, source
   bundles, build reports, and backups. Offer separate exact-path cleanup only
   after uninstall and only under the applicable retention and authorization
   rules.
4. Reconcile any managed dashboard process by exact recorded process/session,
   command, root, port, and start-time evidence. Offer to stop that verified
   process as part of the packet; never kill from a stale PID. Uninstall does
   not stop ChatGPT generations or active research runs. Recommend pausing and
   handing off an active run before removal.
5. Recommend a timestamped non-discoverable backup. Show the exact source,
   backup destination, file/byte counts, inventory digest, dashboard-process
   choice, rollback, and verification before asking for one explicit approval.
6. After approval, atomically rename the exact skill directory into the
   non-discoverable backup when same-filesystem rename is supported. Otherwise
   copy and verify the backup before removing only the exact source. Prefer a
   recoverable trash operation only when its exact behavior is known.
   Permanent deletion requires a separate explicit request.
7. Verify the original path is absent, the backup inventory matches, no other
   path changed, and the skill is no longer discoverable in a fresh capability
   inventory when the host can refresh it. If the current session cannot
   unload a skill, say so and ask the user to start a new Codex session for the
   final discovery check.

If target identity, ownership, active-copy selection, backup integrity, or
process identity is ambiguous, stop before mutation and ask one narrow
question. Never uninstall control plugins, MCP servers, Chrome integrations,
Computer Use adapters, Python, or other shared prerequisites as a side effect.

## Rollback

To restore a recoverable uninstall, first prove the original destination is
absent, the backup is the exact recorded inventory, and the destination remains
the intended user-scoped root. Move the backup to a temporary sibling, validate
it with the current authoritative validator, atomically place it at the exact
destination, validate again, and start a new Codex session if discovery cannot
refresh in place.

The dashboard may display the uninstall intent and a Copy button, but the page
must never execute removal, stop a process, call a local endpoint, or mutate
state. All inventory, confirmation, execution, and verification occur in Codex
chat under this procedure.
