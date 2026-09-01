# Artifact storage, retention, and cleanup

Use this reference during first-use setup, before recovering worker files, when
the user changes storage policy, and at run close when cleanup is possible.

## Contents

- [First-use choice](#first-use-choice)
- [Storage policies](#storage-policies)
- [Run-owned layout](#run-owned-layout)
- [Recovery and ownership](#recovery-and-ownership)
- [Retention policies](#retention-policies)
- [Cleanup gate](#cleanup-gate)
- [Cleanup execution](#cleanup-execution)
- [Resume and failure handling](#resume-and-failure-handling)

## First-use choice

If the durable workforce profile has no artifact policy, ask one short question:

> Where should files returned by ChatGPT Pro be stored, and how should temporary
> copies be handled after acceptance? I recommend a dedicated folder per
> research topic and run, with exact raw files retained through validation and
> a review-before-delete cleanup at handoff. You can choose another dedicated
> root, temporary storage with accepted-file export, keep everything, or manage
> the files yourself.

Resolve the exact writable root before the first download. If note-taking is
enabled, offer a topic-specific artifact folder or a separate native-artifact
root indexed from Obsidian. Do not assume the vault should contain large or
binary files.

Store the choice in the
[workforce profile](../assets/workforce-profile-template.md). A preference does
not grant access outside the selected root and is not blanket permission to
delete files.

## Storage policies

Use one:

- `DEDICATED_RUN_FOLDER` — recommended; one run-owned directory beneath the
  confirmed artifact or research-topic root.
- `USER_SELECTED_ROOT` — use an exact user-approved dedicated location and the
  same run isolation.
- `TEMPORARY_WITH_ACCEPTED_EXPORT` — recover into task-created temporary
  storage, export accepted deliverables to a confirmed durable root, then apply
  the cleanup gate.
- `USER_MANAGED` — leave browser-managed files in place, inventory exact paths,
  and give the user a cleanup manifest; never clean the general directory.

Do not use a general Downloads, Desktop, home, vault, or project root as a
recursive cleanup boundary. A browser may initially place a file in Downloads;
identify that exact file, copy or move it into the run-owned incoming area when
authorized, and track both identities without scanning or deleting unrelated
items.

## Run-owned layout

Use only the directories needed by the run:

```text
<artifact-root>/<topic-slug>/runs/<run-id>/
  incoming/
  raw/
  candidates/
  accepted/
  manifests/
```

- `incoming/` contains exact newly recovered bytes pending safety inspection.
- `raw/` contains immutable inspected worker returns.
- `candidates/` contains repaired or transformed derivatives with lineage.
- `accepted/` contains only hash-bound accepted deliverables.
- `manifests/` contains inventories, validation evidence, and cleanup plans.

When a completed-research explorer is enabled, build its first verified HTML
inside `accepted/`. A copy placed in an exact configured Downloads or other
human-facing output location is an accepted export, not temporary browser
staging. Hash both copies and never make the broad destination directory a
cleanup boundary. Read [completed research explorer](research-explorer.md).

Do not create an empty tree during preflight. Create the run directory only
after the root, topic, and run are approved and the task will recover files.

## Recovery and ownership

For every recovered file record:

- run, lane, conversation, and artifact IDs;
- exact source display name and recovered path;
- byte size, SHA-256, detected type, and archive inventory when applicable;
- whether the path is task-created, browser-created, user-supplied, or external;
- raw, candidate, accepted, rejected, duplicate, temporary, or unknown status;
- downstream notes, manifests, and accepted derivatives that depend on it.

Only task-owned or exactly identified browser-returned files are eligible for
cleanup. User inputs, pre-existing files, accepted deliverables, source trees,
unrelated downloads, and ambiguous paths are never cleanup candidates.

## Retention policies

Use one profile policy:

- `REVIEW_BEFORE_DELETE` — recommended; show the exact cleanup manifest at run
  close and wait for confirmation.
- `KEEP_ALL` — retain raw, candidates, and accepted deliverables; report disk
  use and paths.
- `KEEP_ACCEPTED_ONLY` — after acceptance and handoff, propose cleanup of exact
  rejected, duplicate, and temporary copies while preserving required raw
  evidence until the user accepts its deletion.
- `DELETE_TEMP_AFTER_ACCEPTANCE` — eligible only for a dedicated run-owned or
  task-created temporary root; accepted files must already be exported and
  verified. Still show the exact manifest and honor active approval policy.
- `USER_MANAGED` — perform no deletion; provide the manifest and suggested
  actions.

Retention policy is a stored preference, not proof that a particular deletion
is safe or currently authorized.

## Cleanup gate

Create a plan from
[cleanup plan template](../assets/cleanup-plan-template.md). Before any move to
trash or deletion:

1. Resolve every target to an exact regular file under the dedicated run-owned
   root; reject symlinks, traversal, unresolved variables, globs, directories,
   and paths outside that boundary.
2. Rehash and compare every target with the artifact inventory.
3. Confirm no validator, recovery, worker, or handoff process still uses it.
4. Confirm accepted deliverables exist at their durable locations, match their
   accepted hashes, and are linked from handoff or the research index.
5. Identify which raw evidence remains necessary for provenance, disputes,
   reproducibility, or future repair.
6. Show exact path, bytes, hash, disposition, reason, and total bytes for every
   proposed target.
7. Apply the active approval policy. Under `REVIEW_BEFORE_DELETE`, obtain
   explicit confirmation for this manifest. Under a previously explicit
   automatic policy, stop if scope, root, file class, or consequence differs.

An initial storage choice never authorizes broad or ambiguous cleanup.

## Cleanup execution

Prefer a recoverable move to the platform trash when a verified target-scoped
method exists. Use permanent deletion only when the user explicitly authorizes
it for the exact manifest or a valid task-owned temporary policy applies.

Process files individually or as the exact hash-bound run manifest. After each action,
record one outcome: `RETAINED`, `TRASHED`, `DELETED`, `SKIPPED`, or `FAILED`.
Verify the expected path state, preserve the cleanup record, and report bytes
retained and removed. Never compensate for a failed cleanup by widening the
target or deleting the whole parent directory.

## Resume and failure handling

Persist storage root, run directory, retention policy, cleanup-plan path,
approval evidence, per-file outcome, and the next safe action. On resume,
reconcile the filesystem against the manifest before any cleanup; never repeat
an action with an unknown outcome.

If a file changed after planning, a path escaped the root, an accepted export
is missing, ownership is ambiguous, or another process is using a target, mark
cleanup `BLOCKED` or `PARTIAL` and ask only for the decision or new authority
actually needed.
