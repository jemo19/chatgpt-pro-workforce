# Obsidian-compatible research vault

## Contents

- [Before writing](#before-writing)
- [Safe vault discovery](#safe-vault-discovery)
- [First-use note policy](#first-use-note-policy)
- [Suggested structure](#suggested-structure)
- [Entity types](#entity-types)
- [Typed relationships](#typed-relationships)
- [Status vocabulary](#status-vocabulary)
- [Required content](#required-laneiteration-content)
- [Native artifact rule](#native-artifact-rule)

Vault support is configurable. Never assume one universal absolute path.
Honor explicit user, project, and `AGENTS.md` paths.

A portable project pattern may be:

```text
<configured-vault-root>/<project-id>
```

Treat this as an example, not a default that overrides project instructions.

## Safe vault discovery

Before asking the user to type a vault path, run a bounded read-only discovery
with [Obsidian locator](../scripts/obsidian_locator.py). Use these evidence
sources in order:

1. explicit vault/research paths in current user/project instructions;
2. the current platform-known Obsidian application registry/config file;
3. `.obsidian` marker directories beneath explicit project note roots or other
   likely roots already approved for a bounded search;
4. a user-supplied candidate path.

Known registry locations include the XDG/native, Flatpak, or Snap Obsidian
config location on Linux; Application Support on macOS; and the Obsidian entry
under the roaming application-data location on Windows. Treat these as
discovery candidates, not guarantees. Inspect only a bounded JSON registry and
extract the safe vault identifier, path, and open flag when those exact fields
exist. An Obsidian vault ID is correlation metadata, not an authentication key;
never search for or expose credentials, sync tokens, license data, or secrets.

For marker discovery, use only an explicitly named root, a small depth bound,
the starting filesystem, and no symlink following. Never default to crawling
the whole home directory, mounted disks, or unrelated project trees. Skip
browser profiles, VCS metadata, caches, package trees, trash, and other
unrelated/sensitive directories. Do not read note contents, `.obsidian` plugin
data, workspaces, recent-file history, or unrelated filenames during discovery.

The bundled locator defaults to depth 4, 100 emitted candidates, 2,000 visited
directories, 20,000 examined entries, 10,000 entries in any one directory, and
5 seconds. Its hard ceilings are depth 8, 1,000 candidates, 10,000 directories,
100,000 entries, and 30 seconds. Apply the directory, entry, and time budgets
across all approved marker roots in one invocation. Reject filesystem roots,
the resolved home directory, and mount roots. A ceiling result sets
`complete: false` and emits a specific error; never present its recommendation
as complete discovery.

Run the helper with an explicitly discovered Python 3.10-or-newer interpreter;
do not assume a minor-version executable name. If no compatible interpreter is
available, skip automated marker search, report that capability honestly, and
ask the user to confirm an explicit path.

Deduplicate candidates by resolved path and rank them:

1. explicit current project instruction;
2. currently open registry candidate;
3. other registry candidate;
4. bounded `.obsidian` marker candidate.

Increase confidence when the directory exists, contains the marker, and is
accessible for the planned note operation. Do not auto-select, create, or write.
Show only the relevant candidate paths and safe evidence, then ask:

> I found this likely Obsidian vault from {{SOURCE}}: `{{PATH}}`. It is
> {{OPEN_OR_MARKER_EVIDENCE}}. Should I use it and place this research under
> `{{PROPOSED_RESEARCH_ROOT}}`, or would you prefer another location?

Persist the confirmed vault/research root and safe locator evidence in the
workforce profile. Re-run discovery when the path disappears, the platform or
project changes, or the user asks to locate a different vault.

## First-use note policy

During first-use guided setup, ask whether workforce research should create
Obsidian-compatible notes and which confirmed vault/research root to use. Store
one policy in the workforce profile:

- `NO_NOTES` — do not create vault notes;
- `ASK_EACH_RUN` — decide when each run is scoped;
- `YES_EXISTING_ROOT` — use an explicitly confirmed existing vault/research
  root;
- `CREATE_RESEARCH_ROOT_AFTER_APPROVAL` — propose a dedicated research root and
  create it only after the user approves the exact path.

When no root exists, recommend a research-specific folder rather than placing
run notes at the vault top level. Record `obsidian_vault_root`, `research_root`,
`note_creation_authorized`, and the indexing convention. A preference is not
authorization to create directories; the exact root and current project
instructions still govern.

For each approved research subject, derive a stable human-readable
`topic_slug`, show it to the user when naming is material, and store the exact
`topic_folder`. A discovered topic proposal must not create a folder until its
decision is `APPROVED`. Do not pre-create folders for deferred or rejected
topics.

## Before writing

Inspect:

- project `AGENTS.md`;
- vault `README.md`;
- knowledge map or index;
- current handoff;
- applicable iteration and lane notes;
- artifact catalog.

## Suggested structure

For a dedicated research root, prefer:

```text
<research-root>/
  README.md
  Research Index.md
  <topic-slug>/
    README.md
    00-governance/
    01-iterations/
    02-lanes/
    03-sources/
    04-findings/
    05-artifacts/
    06-decisions/
    07-handoffs/
```

An existing project with an established convention may instead use:

```text
README.md
00-governance/
01-iterations/
02-lanes/
03-sources/
04-findings/
05-experiments/
06-decisions/
07-architecture/
08-handoffs/
templates/
Artifact Catalog.md
Research Backfill Coverage.md
```

Create only folders needed by the active project. Do not create empty directory
trees for appearance. Within an approved topic folder, create a subfolder only
when the current run will write a corresponding note or index. Use the research
root's `Research Index.md` and the topic `README.md` as the durable entry points.

## Entity types

Use stable IDs and YAML frontmatter for:

- project;
- iteration;
- lane;
- prompt;
- conversation;
- source;
- capture;
- claim;
- finding;
- contradiction;
- experiment;
- artifact;
- decision;
- failure;
- handoff.

## Typed relationships

Use explicit fields such as:

- `part_of`
- `generated_by`
- `reviews`
- `supports`
- `contradicts`
- `supersedes`
- `derived_from`
- `tests`
- `blocks`
- `resolves`
- `stored_at`

## Status vocabulary

Use:

- `PLANNED`
- `RUNNING`
- `RETURNED`
- `ACCEPTED`
- `REJECTED`
- `PARTIAL`
- `BLOCKED`
- `NOT_RECOVERABLE`
- `NOT_AVAILABLE`
- `SUPERSEDED`

## Required lane/iteration content

Record:

- IDs and purpose;
- conversation URL;
- prompt path and SHA-256;
- submission, start, observation, and end timestamps;
- worker/model selection when visible;
- inputs and immutable identities;
- outputs and artifact hashes;
- progress history;
- failures and recovery attempts;
- mechanical-gate results;
- semantic-gate results;
- Codex's independent work;
- accepted findings;
- rejected claims;
- contradictions;
- open questions;
- next action;
- links to related notes and native artifacts.

## Native artifact rule

Keep exact CSV, JSON, ZIP, images, scripts, validators, and large raw logs in the
project artifact store. In the vault, index each native object by path, role,
size, hash, disposition, and relationships. Do not lossy-convert or duplicate
large evidence solely to make it Markdown.

Do not duplicate native artifacts merely for note taking; index their original
path, size, hash, role, and disposition so the evidence remains single-source
and verifiable.

Every new note must be linked from a knowledge map, index, lane, or handoff.
Do not create detached notes.

Keep native artifacts in the configured artifact store whenever practical.
`05-artifacts/` may contain small topic-owned native files only when that is the
confirmed project convention; otherwise it contains Markdown index records
pointing to exact native paths, sizes, and hashes. Never duplicate a ZIP, CSV,
image, or binary merely to make the vault appear self-contained.
