# What are the entries on the Artifacts → Files sub-tab?

> **Research query:** What exactly are the entries on the "Files" sub-tab of the
> "Artifacts" tab? How are they created? Why is this tab useful?

## Short answer

Each row is an **indexed artifact file**: a file that SASE copied into its global artifact
store (`~/.sase/artifacts/`) or recorded as a verified pointer into version control. The
tab is **not a file browser** for your repos. It shows only files that something
deliberately registered, either an agent or SASE's own agent pipeline.

Each row is one *logical file*. If the same file was recorded several times, the row
holds every content version, and the row shows `Nv` when there is more than one.

## How rows get created

Every row has an **origin badge**. There are three origins:

| Badge | Origin | What creates it |
| --- | --- | --- |
| **C** | `created`: explicit snapshot | `sase artifact create -p <file> -l <label>`, usually run by an agent to save a deliverable such as a report. SASE also uses this path for its own bookkeeping: continuation nodes (`continuation-portable:*` labels), stored follow-up prompts such as "Full coder prompt", and conditional-completion files. Explicit snapshots are **immutable and permanent**. |
| **A** | `capture`: automatic | When an agent finishes, finalization collects the **images and videos it added or changed** (from local changes, untracked files, its commit diff) plus media paths **mentioned in its prompt**. A capture policy then picks one of three outcomes. *Store*: copy the bytes, up to 50 per run. *Reference*: a durable commit already holds identical bytes, so SASE records a VCS locator and copies nothing. *Skip*. |
| **R** | `ref`: prompt citation | A `@file:<path>` reference in a prompt. At launch the file is snapshotted into a workspace-local pool. When the prompt archive is published to the agents sidecar, a version row is appended. |

A row whose versions came from more than one origin shows a white **`+`** badge.

**Where the data lives:**

- `~/.sase/artifacts/index.jsonl` holds the explicit and automatic rows. Their bytes live
  under `~/.sase/artifacts/agents/…`, unless the row is VCS-backed.
- `~/.sase/artifacts/ref-files.jsonl` holds the `@file` ref versions. Their bytes are
  content-addressed objects in the agents sidecar.

The pane (`src/sase/ace/tui/widgets/artifacts/files_data.py`) merges both indexes and
groups rows by source path. It collapses identical content by SHA-256, sorts newest
first, loads the first 500 rows, and limits results to the selected project.

## What you can do with a row

- **Detail panel:** shows the `file:<id>` reference, then label, kind, version `i/N`,
  MIME type, size, SHA-256, and created time. It also shows the origin(s), project,
  workflow, producing agent, stored and source paths, and a preview.
- **Keys:** `enter` view · `Z` in-TUI viewer · `E` external app · `a` jump to the agent
  that produced it · `Y` copy path · `(` / `)` previous/next version · `z` cycle view kind
  (image / markdown / pdf / text / video) · `f` filters.
- **Query fields:** `kind:`, `origin:` (`ref` / `created` / `capture`), `project:`,
  `agent:`, `workflow:`, `since:` / `until:`, and free text over label and paths.
- **CLI equivalents:** `sase artifact list`, `show`, `open`, `path`, `read`, `stats`.

## Why it's useful

1. **Deliverables outlive workspaces.** Agents run in disposable `sase_<N>` clones, and
   the store keeps a permanent copy of what they produced.
2. **Provenance.** Every file links back to its agent (`a`), its project, and its typed
   artifact links, so "where did this screenshot come from?" takes one keypress to
   answer.
3. **Visual review in one place.** Screenshots and UI snapshot PNGs that agents produced
   can be browsed and opened without digging through ace-run directories.
4. **Stable, citable handles.** Each row has a ref like `file:explicit:<id>`. You can
   paste it into a later prompt as `@file:explicit:<id>`, or read it with an audit trail
   via `sase artifact read`.
5. **Version history.** Grouping by logical file shows how one output changed across
   runs.

## Things that may surprise you

- **It's narrower than "artifacts."** Plans, beads, Patches, commits, and agents have
  their own sub-tabs. This one only shows indexed *files*. It replaced the older "Other"
  pane, and old `other` settings still map to `files`.
- **SASE's own bookkeeping takes up a lot of the list.** Snapshot from this machine
  (2026-10-14):
  - **35,201 rows in total:** 17,676 explicit (431 MiB) and 17,525 automatic (2.3 GiB).
    9,421 of the rows are VCS-backed.
  - **Only 5 `@file` ref rows.**
  - **Mostly continuation nodes at the top:** of the newest 400 rows, about 208 were
    `continuation-portable:*` JSON nodes, and most of the rest were automatic PNG
    captures.
  - **Filtering helps:** `kind:markdown` or `origin:created` brings the human-meaningful
    deliverables to the top.
- **Retention is off by default** (`artifacts.retention.enabled: false`). When it is on,
  automatic captures older than 90 days or beyond the newest 3 per label move to
  restorable trash (14-day grace). Explicit snapshots, captures referenced by a bead,
  plan, or Patch, and the newest capture of each label are always kept. `sase artifact
  reclaim` can turn stored automatic copies into byte-free VCS references.
