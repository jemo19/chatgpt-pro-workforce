# Artifact storage, retention, and cleanup

Use this reference during first-use setup, before recovering worker files, when
the user changes storage policy, and at run close when cleanup is possible.

## Contents

- [First-use choice](#first-use-choice)
- [Storage policies](#storage-policies)
- [Run-owned layout](#run-owned-layout)
- [Recovery and ownership](#recovery-and-ownership)
- [Bounded intake helper](#bounded-intake-helper)
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

## Bounded intake helper

Use the bundled [artifact store helper](../scripts/artifact_store.py) for
run-scoped file, Base64, and ZIP intake when its Linux/POSIX private-root checks
are available. Discover an explicit Python 3.10-or-newer interpreter, run the
helper's `--help`, and initialize only the exact approved run directory:

```text
<python-path> scripts/artifact_store.py init --run-root <run-owned-root> --run-id <RUN_ID>
<python-path> scripts/artifact_store.py ingest-file --run-root <run-owned-root> --run-id <RUN_ID> --artifact-id <ARTIFACT_ID> --source-name <DISPLAY_NAME> --source-kind <SOURCE_KIND> --lane-id <LANE_ID> --conversation-id <CONVERSATION_ID> --source <exact-file>
```

`SOURCE_KIND` is exactly one of `BROWSER_ATTACHMENT`, `BROWSER_DOWNLOAD`,
`BASE64_RECOVERY`, or `LOCAL_FIXTURE`. Use `ingest-base64` only for a bounded
file containing Base64 returned through the recovery path; never place the
payload itself on the command line. The helper stores one content-addressed,
read-only raw object by SHA-256, writes a separate provenance manifest for each
artifact ID, and identifies duplicate content without discarding its distinct
lane/conversation provenance.

Every intake first writes a durable, run- and artifact-bound transaction under
`manifests/intake-state/`. That intent names the expected content hash, raw
object path, optional extraction root, provenance, and whether either
destination already existed. Only then may the helper publish raw bytes or an
extraction. A normal intake ends as `COMMITTED`; a caught validation or
extraction failure ends as `REJECTED_RETAINED`. Rejected raw bytes remain
immutable and durably attributed for review—they are not an accepted artifact
and are not silently deleted.

Use `inspect-zip` for a read-only inventory when extraction is not yet needed.
Use `ingest-zip` only after choosing the run-owned store; it performs the same
complete inventory checks before extraction. The defaults cap the source and
compressed data at 64 MiB, each file at 64 MiB, total expansion at 256 MiB,
member count at 256, and expansion ratio at 100:1. It rejects absolute,
backslash, dotted/traversing, non-canonical, case-fold/Unicode-colliding, or
overlong member paths; duplicates; file/directory conflicts; encrypted
members; unsupported compression; symlinks; and special files. Raise a limit
only from trusted task evidence and record the changed bound; a rejected
archive is not partially extracted.

If the process is interrupted or its result is uncertain, do not retry the
artifact ID. Reconcile the transaction first:

```text
<python-path> scripts/artifact_store.py reconcile-intake --run-root <run-owned-root> --run-id <RUN_ID> --artifact-id <ARTIFACT_ID>
```

Reconciliation serializes against new intake, verifies any committed manifest
and exact raw object, checks an interrupted extraction's paths, types, sizes,
CRC values, and immutable modes against the durable intent, and removes only
abandoned helper-created staging trees whose names are bound to the intended
digest. It does not remove a content-addressed raw object or a published extraction:
either may be shared by another provenance record. An interrupted transaction
with retained bytes becomes `OUTCOME_UNKNOWN_RETAINED`; one with no intended
bytes becomes `DEFINITELY_NOT_PUBLISHED`. Use a new artifact ID after an
unknown or rejected result unless a separately verified workflow deliberately
adopts those exact retained bytes.

The helper's raw objects and extracted files are immutable inputs, not accepted
outputs. Never edit them in place. Put deterministic repairs or conversions in
`candidates/`, preserve parent hashes in lineage, and promote separately only
after the mechanical and semantic gates pass.

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

Prefer a recoverable move. The bundled helper implements cleanup as an atomic
move into private run-owned quarantine, not permanent deletion. A verified
platform trash route may be used instead when its exact target and postcondition
are stronger. Permanent purge is a separate later action that needs a new exact
inventory, authorization, and implementation; `apply-cleanup` never purges.

Process files individually or as the exact hash-bound run manifest. After each
helper action, record `QUARANTINED`, `QUARANTINED_RECONCILED`,
`QUARANTINED_IDENTITY_CHANGED`, `BLOCKED_IDENTITY_CHANGED`, or the other exact
reported outcome. Verify both source and quarantine state, preserve the cleanup
record, and report bytes retained, quarantined, and blocked. Never compensate
for a failed cleanup by widening the target or removing the whole parent.

For explicitly authorized helper-managed cleanup, use its two-phase interface:

```text
<python-path> scripts/artifact_store.py plan-cleanup --run-root <run-owned-root> --run-id <RUN_ID> --plan-id <PLAN_ID> --target <exact-target> --reason <bounded-reason> --authorization-state AUTHORIZED_EXACT_MANIFEST --authorization-reference <approval-evidence>
<python-path> scripts/artifact_store.py apply-cleanup --run-root <run-owned-root> --run-id <RUN_ID> --plan-id <PLAN_ID>
```

Repeat `--target` for each exact file. The helper accepts only single-link
regular files under `incoming/`, `candidates/`, or `raw/`; binds each target to
path, size, SHA-256, device, and inode; serializes plan/apply/reconcile; rechecks
content at the action boundary; moves the exact candidate to
`manifests/cleanup/quarantine/<PLAN_ID>/`; and rehashes it there. It never
deletes a directory, follows a symlink, expands a glob, purges quarantined
bytes, or acts outside the run-owned root.

Before each move it durably records `OUTCOME_UNKNOWN`. If the source changes,
it is retained and blocked. If the quarantined bytes differ after the move,
they remain recoverable and are reported as identity-changed. If interrupted,
run `reconcile-cleanup` before any further cleanup. A retained, missing, or
identity-changed target requires a new exact plan; never reuse or broaden the
old one. A `PENDING_EXPLICIT_AUTHORIZATION` plan is review evidence only and
cannot be applied; after approval, create a new uniquely identified authorized
plan rather than editing the existing manifest.

## Resume and failure handling

Persist storage root, run directory, retention policy, intake-transaction and
cleanup-plan paths, approval evidence, per-file outcome, and the next safe
action. On resume, reconcile any nonterminal or uncertain intake before
creating another artifact record, then reconcile the filesystem against the
cleanup manifest before any cleanup. Never repeat an action with an unknown
outcome.

If a file changed after planning, a path escaped the root, an accepted export
is missing, ownership is ambiguous, or another process is using a target, mark
cleanup `BLOCKED` or `PARTIAL` and ask only for the decision or new authority
actually needed.
