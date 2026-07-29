---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# Viewing, Copying, and Referencing SASE Artifacts

**Consolidated from two independent research passes** (`__a` = codex/gpt-5.6-sol, `__b` = claude/opus) plus a
verification pass over the sase, sase-core, and bead corpora.

---

## Bottom line

Both researchers converged on the same diagnosis from opposite directions: **an artifact in SASE is a path, and a path
is not a durable name.** `__a` framed it as a missing identity/registry layer; `__b` framed it as a missing shared noun
across six unrelated artifact models. They are the same finding.

Where they diverged — *build a new artifact registry in `sase-core` with a `sase://` URI scheme* (`__a`) versus
*generalize the `plans:` reference resolver that already exists and add a query API over the existing index* (`__b`) —
the evidence resolves decisively in favor of `__b`, for two reasons neither report found:

1. **SASE already built `__a`'s registry and deleted it.** The unified artifact graph — SQLite store, SQL-backed
   search, paged detail contracts, batched summary contracts, ingestion from agent artifacts / ChangeSpecs / commits /
   beads / thoughts, graph export — was written on **2026-05-05** and removed on **2026-05-06** in `b455124`,
   **12,898 deletions across 11 files**, including 967 lines of PyO3 bindings. It lived roughly 24 hours and never
   reached a user.
2. **SASE also already solved this exact problem once, correctly, two days ago.** Epic `sase-9z` — *"Make bead plan
   linkage durable with logical `plans:` references"* — closed **2026-07-27** with five phases and repaired
   **227 stored links that no longer resolved.** That is a proven, end-to-end playbook for making one artifact kind
   durably referenceable, and it is directly reusable for the rest.

So the path forward is not a new subsystem. It is: **fix three small live defects, then run the `sase-9z` playbook a
second time over a kind-tagged reference grammar, then spend the resulting reference in the TUI, the CLI, and the
prompt bar.**

---

## 1. Verified current state

Every claim in this section was re-verified against the working tree on 2026-07-29. Where the two reports disagreed or
were incomplete, the resolution is noted inline.

### 1.1 Two disjoint things are called "artifacts"

| | **The Artifacts tab** | **Artifact files** |
| :--- | :--- | :--- |
| What | Commits, Plans, Chats, Bugs, PRs | Agent-produced images, markdown, PDFs, videos, explicit files |
| Where | `sase ace` → Artifacts (`src/sase/ace/tui/widgets/artifacts/`) | Agents tab → `a` (`src/sase/ace/tui/modals/artifact_files_modal.py`) |
| Model | 5 unrelated types | `ArtifactFile` (`src/sase/core/artifact_file_types.py:51`) |
| Storage | Repos, SDD sidecars, bead store, chats catalog | `~/.sase/artifacts/` + `index.jsonl` |
| Viewer | Textual modals (raw source text) | `kitten icat`, `mpv`, markdown→PDF→PNG paging, tmux side pane |
| Copy | 1 hardcoded target per sub-tab | contents (`y`) + path (`Y`) |
| Marks | none | yes (`m`) |
| Reachable from the other | **no** | **no** |

`action_open_artifact_files` early-returns unless the Agents tab is active, and `check_action` disables it outright
(`src/sase/ace/tui/app.py:362`). **The best artifact viewer SASE has cannot be opened from the panel named
"Artifacts."** This is the naming collision at the root of the request: when the user says "the Artifacts panel," the
surface they get has none of the affordances the thing actually named `ArtifactFile` already has.

*(`__a` described the artifact-file picker's capabilities — marks, multi-select, always-opens — and `__b` described the
Artifacts tab's lack of them. Both are correct; they are different surfaces.)*

### 1.2 Copy mode and marks are hard-gated off on 4 of 5 sub-tabs — **confirmed defect**

`copy_tab_content` is bound to `%` and `toggle_mark` to `m` (`src/sase/ace/tui/bindings.py:189,169`), but neither
appears in `NON_PRS_ARTIFACT_ACTIONS` (`src/sase/ace/tui/actions/artifacts.py:39-74`), and `check_action` is
deny-by-default for any action outside that allow-list while a non-PR sub-tab is active
(`src/sase/ace/tui/app.py:371-377`). On Commits, Plans, Chats, and Bugs there is **no copy mode at all** — not even
`%s`, the tmux pane snapshot (`clipboard/_core.py:170`) that is otherwise tab-independent and works everywhere else.

Lifting the gate alone is not sufficient. `_handle_copy_key` branches on `self.current_tab` only
(`clipboard/_core.py:47-54`), and the Artifacts tab's internal id **is** `"changespecs"`
(`src/sase/ace/tui/tab_order.py:18`), so `%n` on the Chats sub-tab would route into `_handle_changespecs_copy_key` and
copy the selected **PR's** name. The keymap config has exactly three key sets — `changespecs`, `agents`, `axe` — and no
notion of an artifact sub-tab.

### 1.3 Per-sub-tab capability matrix

| Sub-tab | View | Copy | Open external | Reference / hand-off | Marks | `%` copy mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Commits** | `enter` → `CommitViewModal` (message + diff + linked plan) | `y` → **full SHA only** | — | — | — | **disabled** |
| **Plans** | `enter` → `PreviewPanelModal`; `l`/`h` expand | **none** | — | `w` launch epic, `o` open bug | — | **disabled** |
| **Chats** | `enter` → `PreviewPanelModal` | `y` → **absolute path** | `o` → `$EDITOR` | `a` → jump to agent | — | **disabled** |
| **Bugs** | `enter` → activate link | `y` → `#N <url>` | `o` → browser | `a` → seed agent prompt | — | **disabled** |
| **PRs** | `v` view files, `d` diff | `%` → **6 targets** | — | `a` → axe item | `m` yes | **enabled** |

Two consequences fall out. **Each sub-tab picked one copy target and stopped** — Commits copies the 40-char SHA and not
the subject, the message, a `repo@sha` pair, or the linked plan the modal already loads; Plans copies nothing at all;
Chats copies a raw absolute path while the artifact-file modal's `Y` copies a *relative* one, two answers to one
question in one app. And **the same key means different things per sub-tab** — `o` is open-bug / open-`$EDITOR` /
open-browser; `a` is open-agent / seed-agent / toggle-all-projects; `y` is copy-SHA / copy-path / copy-issue, and plain
refresh elsewhere in the app.

### 1.4 The full-screen reader is a source-code pager

`PreviewPanelModal` is the primary read surface for both Plans and Chats. Its entire binding set is scroll and close
(`preview_panel_modal.py:19-29`): **no copy, no search, no open-in-editor, no follow-link, no rendered-markdown mode.**
Content goes through `lazy_renderable(...)` — a Rich `Syntax` block, `line_numbers=True`, `monokai` — so a plan or chat
transcript renders as raw Markdown source with a line-number gutter.

This is inconsistent in two directions at once. The Plans *detail pane on the same screen* already uses the Textual
`Markdown` widget for rendered prose (`plans_pane.py:10,85`), so pressing `enter` to see *more* of a plan renders it as
*less*. Meanwhile the artifact-file viewer typesets the same Markdown to PDF and pages it as PNGs. Three renderers,
three fidelities, one document type.

`CommitViewModal` is the exception that proves the rule: copy, plan/commit toggling, next/prev traversal, and
`CopyModeForwardingMixin` (`commit_view_modal.py:41-57`). It is the only artifact reader that behaves like a reader,
and it was built for exactly one sub-tab.

### 1.5 References: create-only, with no way to read back

`sase artifact-file` has exactly one subcommand — `create` (verified: `sase artifact-file --help` →
`{create}`), gated on `SASE_AGENT=1` and `SASE_ARTIFACTS_DIR`. There is no `list`, `show`, `path`, or `open`. Neither
an agent nor a human can discover, read, or resolve an artifact from the CLI. Compare the neighbours: `sase chat
list|show` ships JSON, and `sase plan list|search` supports `--kind {tale,epic,prompt,research}`.

Artifact ids are stable and unique but not human-usable — `default:52895d68931185056fd0e49f` — and are displayed
nowhere in the UI.

### 1.6 The corpus, measured today

| Corpus | Count | Notes |
| :--- | ---: | :--- |
| Artifact files (`index.jsonl`) | **3,985** | 3,775 image · 185 markdown · 25 file; **188 explicit** |
| — on disk | **3,987 files / 622 MB** | |
| — distinct producing agents | **533** | |
| Agent runs (`agent_artifact_index.sqlite`) | **5,076** | |
| Chat transcripts (`chats_catalog.sqlite`) | **10,311** | |

Every one of those 3,985 files is reachable only by first locating its producing agent among 5,076 runs and pressing
`a`. No list, no search, no cross-agent browse, no CLI.

### 1.7 Two primitives already exist, each used for one thing

**`ArtifactEntryTarget`** (`widgets/artifacts/entry_navigation.py:11`) is a typed identity tuple that every non-PR pane
already computes for every row: `("commit", repo, sha)` · `("chat", path)` · `("bug", project, n)` ·
`(kind, project, identity)` for plans. It is a discriminated, project-scoped, refresh-stable identity for every artifact
in the panel — consumed by exactly one caller, `select_relative_entry`, to keep the cursor on the same row across a
refresh. Never rendered, never copied, never persisted, never resolved.

**`plans:` logical references** (`../sase-core/crates/sase_core/src/plan/refs.rs`) are the Rust core's answer to naming
an artifact durably: `parse` / `render` / `resolve` against *ordered roots*, four legacy path shapes accepted, plus
drift recovery that re-finds a file by name when it has moved between month directories. It is deliberately locked to
one kind — `render_plan_reference` errors on anything but `"plans"` — so `research:202607/x.md` is rejected today even
though `research` is a first-class SDD kind everywhere else.

### 1.8 Adjacent gaps

- **Research reports are invisible in the panel.** Both plan-archive loaders hardcode `kinds=("tale", "epic")`
  (`plans_data_sources.py:176,207`), so the `research` kind — with its own sidecar repo, `#research` xprompts, and
  `sase plan search --kind research` — has no view in ACE. *This document will not appear in the Artifacts panel.*
- **Jump All excludes artifacts.** The `` ` `` modal's "Artifacts" section is built from ChangeSpecs only
  (`jump_all_modal.py:128-133`), and `jump_to_all_entries` is not in the allow-list anyway.
- **The footer never mentions artifacts.** No non-PR sub-tab branch in `KeybindingBindingsMixin`;
  `update_copy_bindings` handles only the three legacy tab names.
- **The mobile gateway exposes `artifact_dir` as an opaque host path** and serves no artifact content
  (`docs/mobile_gateway.md:461`) — the first non-TUI consumer already exists and is already blocked on the same
  missing resolver.

---

## 2. New evidence this consolidation adds

These five findings are absent from both source reports and change the recommendation.

### 2.1 The artifact graph was a 24-hour experiment, not a mature subsystem that decayed

`git log` on `crates/sase_core/src/artifact/` shows the entire graph — 21 commits — landing on **2026-05-05** and
being removed on **2026-05-06**. The removed `mod.rs` exported `artifact_search`, `artifact_show_paged`,
`artifact_summary`, `artifact_detail`, `artifact_doctor`, an `ArtifactStore` over SQLite, ingestion from seven sources,
and dot/mermaid/json export.

This cuts two ways. It confirms `__a`'s advice not to rebuild a graph — but it also means `__a`'s *own* proposal (a
`sase-core` registry with a store, minted IDs, query APIs, and a resolver) overlaps substantially with what was just
deleted. The removal is evidence about scope discipline, and it applies to the recommendation as much as to the
alternative it rejects.

### 2.2 `sase-9z` is a finished, proven playbook for exactly this problem

Epic **`sase-9z` · "Make bead plan linkage durable with logical `plans:` references"** closed **2026-07-27**:

| Phase | | Size |
| :--- | :--- | :--- |
| `sase-9z.1` | Canonical `plans:` reference scheme in the Rust core | medium |
| `sase-9z.2` | Route every plan-reference resolver through the shared API | medium |
| `sase-9z.3` | Persist `plans:` references on new beads | small |
| `sase-9z.4` | Show the logical reference *and* its resolved path | small |
| `sase-9z.5` | Validate and repair stored plan links (`sase bead doctor`, `--fix-design-refs`) | large |

Its description records that phase 5 **repaired 227 stored links that no longer resolved.** `sase bead show` already
renders the pattern the whole panel needs:

```
PLAN
  plans:202607/durable_plan_refs.md
  → /home/bryan/.../sase/repos/plans/202607/durable_plan_refs.md
```

Two implications. First, **path-rot in SASE is measured, not hypothetical** — 227 links had already broken for one
artifact kind. Second, the extension to more kinds is a *known-shape* project with a five-phase decomposition already
validated, not the "L, keystone, crosses the Rust boundary" unknown `__b` sized it as. Reinforcing that: `plans:` refs
are **already wired through the Python binding** (`src/sase/plan_documents.py:12-13,75,88`,
`src/sase/workflows/commit/plan_paths.py`, `src/sase/scripts/sase_clan_summary_plan.py`), so generalizing the grammar
requires no new binding plumbing.

### 2.3 The field is *not* clear at the core level

`__b` concluded "nothing is in flight — 73 commits since May, one open bead." That holds for the Python panel (verified:
`sase-an`, a flaky-test fix, is the only open bead) but is wrong for the reference substrate, which has had a burst of
investment in the last eight days:

- **2026-07-21** `3513a0b feat(plan): add document-level artifact link contract` → `artifact_link.rs`, now **62 KB**
- **2026-07-27** `1136e72 feat(plan): add durable plan reference contract (sase-9z.1)` → `refs.rs`
- **2026-07-28** `105b597` structured header block contract · `4d70c1c` canonical parent header migration ·
  `c81b144` reciprocal bead header sections

New reference work should be sequenced *with* the `sase-ag` / `sase-ai` header-block direction, not started beside it.

### 2.4 Path rot is measurable right now — and `Y` emits a path with no anchor

Scanning all 3,985 index records:

| | |
| :--- | ---: |
| Stored `path` still exists | **3,985 / 3,985 (100%)** |
| `source_path` still exists | **2,760 / 3,985 (69%)** |
| **`source_path` is gone** | **1,225 (31%)** |
| — of which explicit artifacts | 10 / 188 (5%) |

The managed store is perfectly healthy; **31% of remembered source paths are already dead.** Explicit artifacts fare far
better because they land in persistent SDD sidecars rather than ephemeral workspaces.

Worse than dead is *silently wrong*. `_artifact_file_clipboard_path` (`artifact_files_modal.py:107-131`) tries
workspace-relative on the **stored** path first — but stored paths live under `~/.sase/artifacts/`, which is never
inside a workspace, so that branch essentially never fires. It therefore falls through to the **`source_path`** branch,
and `_workspace_relative_path` returns `relative.as_posix()` — a **bare relative path with no workspace identity**, e.g.
`tests/ace/tui/visual/snapshots/png/foo.png`. Pasted anywhere, that resolves against whatever directory the recipient
happens to be in. And `sase_<N>` workspaces are recycled (`sase repo open` prints *"Cleaning workspace… Updating
workspace to origin/main"*), so the same relative path can later name a *different* file in a reused checkout.
`__a` flagged that `Y` "may copy a path that no longer exists"; the stronger and more accurate statement is that
`Y` commonly copies a path that resolves to the wrong thing.

### 2.5 Identity, digest, and record fields — settling `__a` vs `__b` on the registry

`artifact_file_id` (`src/sase/core/artifact_file_helpers.py:64-80`) is:

```
sha256( project | workflow | raw_timestamp | agent_artifacts_dir | resolved_path | label )[:24]
```

So identity **is** location-derived (`__a` correct) **and** provenance-scoped, but is **not** content-derived. Two
consequences:

- **The digest is already computed and thrown away.** `artifact_file_explicit.py:208` does `hash_file(source)[:12]` to
  build the stored filename — the full SHA-256 exists in memory and only 12 hex chars survive. Persisting the full
  digest for the 188 explicit artifacts costs ~0. The 3,797 default artifacts would need a fresh read.
- **The index record is already ~65% of `__a`'s proposed registry.** Verified fields at `schema_version: 1`:
  `agent_artifacts_dir, agent_name, created_at, explicit, id, kind, label, path, project, raw_timestamp, source_path,
  workflow, workspace_dir`. Provenance, origin, and both locations are present. **Missing: `sha256`, `size_bytes`,
  `mime_type`, and an availability state.**

This is what makes `__b`'s "the gap is a query API, not a schema" the right call — with a three-field amendment. A new
store is not needed; three fields and a resolver are.

### 2.6 Two smaller corrections

- **The `cat` safety gap is real but narrower than `__a` framed it.** `artifact_text_viewer_command`
  (`graphics/_viewer_loop_media.py:30-43`) invokes `bat --paging=always --color=always --decorations=always --
  <path>` when available — argument-boundary hygiene is *already present* on that branch, and `bat` itself refuses to
  print binary content to a terminal. The fallback is bare `["cat", str(expanded)]`: no `--`, no binary detection, no
  control-sequence neutralization. So the exposure is precisely "`bat` not installed" — which is exactly the minimal,
  SSH-ish, non-Kitty environment where the rest of the media pipeline is already degraded.
- **Clipboard transport has no OSC 52 path.** `copy_to_system_clipboard` (`src/sase/core/clipboard.py:47-62`) is
  subprocess-only. Textual is pinned at **8.0.1**, whose `App.copy_to_clipboard()` provides an OSC 52 route that works
  over SSH without a local clipboard binary — and it is not used anywhere in the tree. Today, *every* copy in ACE
  silently fails on a host without `pbcopy`/`wl-copy`/`xclip`/`xsel`.

---

## 3. Diagnosis

The panel's problems are not independent feature gaps. They are **one missing abstraction plus two live defects.**

**The missing abstraction.** Six artifact kinds, six models, six keymaps, six copy semantics, and no type that says
"this is an artifact." Every new sub-tab pays full freight: its own identity function, copy action, detail renderer, and
key vocabulary. That cost is why Plans shipped with no copy verb at all. The abstraction that collapses it is already
computed on every row (`ArtifactEntryTarget`), already resolved durably in Rust for one kind (`plans:` refs), already
bound into Python, and already proven end-to-end by a closed epic (`sase-9z`). **Nothing needs to be invented.**

**The gating bug.** `NON_PRS_ARTIFACT_ACTIONS` is an allow-list, so every app-level action is denied by default on
non-PR sub-tabs. That was right for `add_axe_item`; it silently swallowed `copy_tab_content` and `toggle_mark`.

**The path-copy bug.** `Y` returns an unanchored relative path derived from a `source_path` that is dead 31% of the
time and ambiguous the rest of the time.

**Where the work belongs.** Per `rust_core_backend_boundary`: reference parsing, rendering, resolution, and index
queries are core backend logic — the mobile gateway and any future web or editor client need identical semantics — and
belong in `../sase-core` alongside `plan/refs.rs`. Keymaps, modal bindings, footers, and rendering stay in this repo.

---

## 4. Resolving the three disagreements

| Question | `__a` | `__b` | Resolution |
| :--- | :--- | :--- | :--- |
| **New core registry?** | Yes — new record, minted location-independent IDs, store + resolver | No — `index.jsonl` is adequate; the gap is a query API | **`__b`, with a 3-field amendment.** The graph was built and deleted in 24 h (§2.1); the index already carries 9 of ~14 proposed fields (§2.5). Add `sha256`, `size_bytes`, `mime_type` + a resolver + a query API. Do not add a store. |
| **Ref syntax** | `sase://artifact/v1/file/<id>#L12-L18` | `commit:<repo>@<sha>` · `chat:<path>` · `file:<id>` | **`__b`'s colon form**, because `plans:` already parses, renders, resolves, is persisted on beads, is rendered in `sase bead show`, and has 227 migrated links behind it. A second scheme fragments a live one. **Adopt `__a`'s fragment anchors** (`#L12-L18`, `#page=3`, `#t=92.5`) — they layer onto the colon form cleanly. **Drop `__a`'s `/v1/` segment**: `refs.rs` already handles evolution via legacy-shape acceptance and drift recovery, which is the mechanism that actually worked. |
| **Web/HTML viewer** | Later layer, after the resolver | Do not build one | **Not now, either way.** But note the mobile gateway already exposes `artifact_dir` as an opaque path and serves no content — the first non-TUI consumer exists today, which is an argument for putting the resolver in core (both reports agree), not for building a viewer. |

**On priority order**, `__b` is right that the copy-mode gate is item #1 — it is a confirmed, user-visible defect with a
small blast radius. But `__a`'s `cat` fix and path-labeling fix are equally cheap and `__b` missed them entirely. They
belong in one first tranche. Conversely `__a`'s ranking of the registry at #1 would start with the largest,
highest-uncertainty item, immediately after a 12,898-line deletion in the same area.

---

## 5. Ranked recommendations

Ordered by (value × confidence) ÷ cost. Items 1–3 are independently shippable; 4–7 compound on them; 8–9 are polish.

### 1. Tranche zero: four small, independent defect fixes — *S, immediate, highest confidence*

Ship these together; none depends on any other item.

- **Restore copy mode and marks on every sub-tab.** Add `copy_tab_content` and `toggle_mark` to
  `NON_PRS_ARTIFACT_ACTIONS`; add a `copy_mode.keys.artifacts.{commits,plans,chats,bugs}` block to
  `default_config.yml`; branch `_handle_copy_key` on `current_artifacts_subtab` *before* falling through to
  `current_tab`; extend `update_copy_bindings` to accept a sub-tab. Give each sub-tab a real menu instead of one
  hardcoded target — Commits: `%%` sha · `%m` message · `%r` `repo@sha` · `%p` linked plan · `%s` snapshot.
  Plans: ref · path · title · body. Chats: path · agent · transcript. Bugs: `#N` · url · title · agent-ready prompt.
  Multiplies copy targets from 4 to ~20 with no new concept.
- **Fix `Y`.** Prefer the **stored** path (it exists 100% of the time); never emit a bare relative path without a
  workspace anchor; label the result as source or stored in the toast. This is a correctness fix, not cosmetics —
  today's output is wrong 31% of the time and ambiguous the rest (§2.4).
- **Stop raw `cat`.** Replace the `bat`-absent fallback with a bounded read + binary/UTF-8 detection +
  control-character neutralization, and add `--` for argument-boundary parity with the `bat` branch (§2.6).
- **Surface `research` in Plans.** Change `kinds=("tale", "epic")` to include `"research"` at
  `plans_data_sources.py:176` and `:207`, plus a kind facet in the filter bar. The plan-search facade, the Rust reader,
  and the sidecar all support it already — two lines and a chip.

**Do this first even if nothing else on this list happens.**

### 2. Extend `plans:` into a kind-tagged artifact reference, following the `sase-9z` playbook — *M–L, keystone*

Generalize `plan/refs.rs` into `sase_core::artifact_ref` over the tuples `ArtifactEntryTarget` already produces:

```
commit:<repo>@<sha>      chat:<path>          bug:<project>#<n>
plans:<path>             research:<path>      file:<artifact-id>
```

Keep everything `refs.rs` already does right — ordered-root resolution, legacy path acceptance, drift recovery — and add
per-kind resolvers plus optional fragment anchors (`#L12-L18`, `#page=3`, `#t=92.5`). Let `render_plan_reference` accept
`research` on the way past; it is already a `read.rs` kind.

Reuse the closed epic's five-phase shape verbatim (§2.2): core scheme → route every resolver through the shared API →
persist refs on new records → **show the logical ref and its resolved path** in the UI → validate and repair with a
doctor. Sequence it with the in-flight `sase-ag`/`sase-ai` header-block work (§2.3), not beside it. Python binding
plumbing already exists, so this is smaller than a greenfield estimate suggests.

### 3. Ship `sase artifact` as a read CLI, and add three record fields — *M, unblocks agents and the TUI*

`sase artifact list [--kind] [--project] [--agent] [--since] [-j]`, `show <ref>`, `path <ref>`, `open <ref>`, backed by
`index.jsonl` and the item-2 resolver. Match `sase chat list -j` as the precedent. Extend `sase_artifact_file.md` from
create-only to create-and-read.

Alongside it, bump the record to add **`sha256`** (already computed and discarded for explicit artifacts — §2.5),
**`size_bytes`**, and **`mime_type`**, behind a `schema_version` bump with backfill. These are the only genuine gaps in
`__a`'s registry proposal that survive scrutiny.

Today an agent can write into a 3,985-file / 622 MB store it cannot read, and a human has no CLI path at all. This also
gives the TUI a tested backend rather than a second query path.

### 4. Make `PreviewPanelModal` a real reader — *M, highest daily value per line changed*

Add to the modal Plans and Chats both open: `y` copy contents · `Y` copy path · `%` copy ref · `/` in-document search
with `n`/`N` · `o` open in `$EDITOR` · `R` toggle rendered Markdown (the Textual `Markdown` widget the Plans detail pane
already uses) · `Z` hand off to the rich terminal viewer. Adopt `CopyModeForwardingMixin`, which `CommitViewModal`
already uses.

`CommitViewModal` is the working template — this is mostly bringing two readers up to the standard a third already sets.
The rendered-Markdown toggle alone removes the oddity that pressing `enter` on a plan makes it *less* readable than the
pane behind it.

### 5. Reach the rich artifact-file viewer from the Artifacts panel — *M*

Add a sixth **Files** sub-tab backed by the index, rather than merely lifting the `current_tab != "agents"` gate. The
viewer itself — `kitten icat`, `mpv`, markdown→PDF paging, tmux side pane — needs no changes; only its reachability
does. Prefer the sub-tab over the lifted gate: it makes 622 MB browsable by project, kind, and time instead of by
"which of 5,076 agent runs produced this," and it is the surface where `%`/marks/preview from items 1 and 4 apply for
free.

### 6. Unified "Copy as…" palette — *S–M, after 2 and 3*

Once a ref exists, replace the growing set of fixed keys with one palette: **reference** (default) · Markdown link
`[Label](ref)` · selected excerpt with anchor · full contents (text-like, size-capped) · **stored** path · **source**
path (explicitly labeled, with a missing-source warning) · metadata JSON. For a marked set, the same palette yields a
Markdown list, a newline-separated path list, concatenated text with boundaries, or a JSON array. Keep today's keys as
accelerators. Always name what was copied — *"Copied 3 references"* — and on failure leave the generated text
selectable rather than discarding it.

Pair this with **Textual's `App.copy_to_clipboard()` as the first transport**, falling back to the existing subprocess
adapter (§2.6) — that is what makes copy work at all over SSH.

### 7. Marks and bulk actions across artifact sub-tabs — *M*

Once item 1 admits `toggle_mark`, use `ArtifactEntryTarget` as the mark identity — it is already stable across refresh,
which is precisely what it was built for. Then: copy all marked refs, open all marked in the viewer, seed one agent
prompt from a marked set. The artifact-file modal already proves the pattern end to end.

### 8. Artifact refs in the prompt bar — *M, depends on 2*

Let `@`-completion offer artifact refs from the index alongside file-reference history, and expand refs to concrete
paths in `process_file_references` at launch. Add `%`-to-prompt so a copied ref drops straight into a new agent prompt.
**This is the payoff that justifies item 2's cost:** artifacts stop being things you look at and become things you hand
to an agent.

### 9. Vocabulary, footer, and Jump All — *S, polish, bundle with 1 or 4*

Fix the colliding key meanings (`o` = open externally, `y` = copy primary, `a` = agent hand-off, everywhere; move
Commits' `a` to a filter facet). Add non-PR sub-tab branches to the keybinding footer. Add commit/plan/chat/bug entries
to the `` ` `` Jump All modal, which already groups by tab and already labels a group "Artifacts." Breaking changes
here should ride with the item-1 keymap change and one `docs/ace.md` update.

---

## 6. What not to do

- **Do not build a new artifact store, registry, or second index.** `index.jsonl` + `agent_artifact_index.sqlite` are
  adequate for 3,985 rows, and the last attempt at a core artifact store was deleted one day after it was written
  (§2.1). Add three fields, a resolver, and a query API — not a substrate.
- **Do not introduce a `sase://` URI scheme alongside `plans:`.** One live, migrated grammar beats two.
- **Do not mint new location-independent artifact IDs yet.** Existing IDs are location-derived (§2.5), but the stored
  location is SASE-managed and 100% intact today. Re-minting is a migration with real cost and no current symptom;
  revisit only if the store layout is ever relocated.
- **Do not add a web or GUI artifact viewer.** The terminal viewer already handles image, video, Markdown, PDF, and
  text with tmux integration. The problem is reachability (item 5), not capability.
- **Do not build a generic artifact plugin system.** Six kinds is not enough to justify the indirection. Revisit after
  item 2 has proven the grammar across all of them.

## 7. Validation cases

Worth testing explicitly, because each one currently exposes a path or terminal assumption:

- An explicit artifact whose source workspace was recycled *and reused* — does the copied path resolve to the wrong file?
- Two byte-identical artifacts from different agents (distinct provenance, identical digest).
- A ref resolving after the file drifts between month directories (the `refs.rs` drift path, now across kinds).
- A missing or corrupt stored object; a broken ref reported by a doctor rather than passing silently.
- A file containing ANSI/OSC control sequences, on a host **without** `bat`.
- Filenames beginning with `-`, non-UTF-8 names, and spaces.
- SSH + tmux, with and without OSC 52; a host with no `pbcopy`/`wl-copy`/`xclip`/`xsel` at all.
- Narrow terminals and terminals without Kitty graphics.

## 8. Open questions for the user

1. **Anchor syntax.** The colon grammar is settled by precedent, but do fragments use `#L12-L18` (GitHub-like, and
   `__a`'s proposal) or something that cannot collide with `bug:<project>#<n>`? The `#` already carries meaning in both
   bug refs and xprompt parsing — this is the one syntactic decision that most affects item 2's shape.
2. **Digest backfill scope.** Persist `sha256` only for the 188 explicit artifacts (free — already computed), or read
   and hash all 3,987 files / 622 MB once to backfill?
3. **Does item 2 wait on the `sase-ag`/`sase-ai` header-block work now landing?** Recommended: coordinate rather than
   serialize — item 1 makes the panel usable meanwhile, and item 2 should reuse whatever header/link vocabulary those
   epics settle on.
4. **Files sub-tab vs. lifted gate** for item 5. A sixth sub-tab is more work but makes 622 MB genuinely browsable,
   which the agent-scoped picker never will.

---

## Appendix: source reports

- **`artifact_refs_and_inspector__a.md`** — codex/gpt-5.6-sol. Strongest on the conceptual separation of path / digest /
  reference, external-system comparison (GitHub Actions, GitLab, W&B, JupyterLab, OSC 8), the raw-`cat` safety issue,
  clipboard transport vs. representation, and the "Copy as…" model. Weakest on repository history — it cites the graph
  removal but proposes a registry that substantially overlaps what was removed.
- **`artifact_refs_and_inspector__b.md`** — claude/opus. Strongest on verified current state: the copy-mode gating
  defect and its dispatcher consequences, the per-sub-tab capability matrix, the two dormant primitives, and the
  corpus measurements. Weakest on the in-flight core work — its "the field is clear" conclusion holds for the Python
  panel but not for `sase-core`, where the reference substrate has been under active construction for eight days.
