---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# Viewing, Copying, and Referencing SASE Artifacts

## Question

How should SASE improve the way users **view**, **copy**, and **reference** artifacts — the commits, plans, chat
transcripts, bugs, PRs, and agent-produced files that the system already persists? What is the best path forward, and in
what order should the work happen?

**Short answer: the panel does not need more features so much as it needs one shared noun.** SASE already stores six
kinds of artifact behind six unrelated models, six bespoke keymaps, and two disjoint UI surfaces that share no verb.
Two universal primitives for fixing that already exist in the tree and are each used for exactly one thing:
`ArtifactEntryTarget` — a typed identity tuple already computed for every non-PR artifact row, currently used only to
restore scroll position — and `plans:` logical references in the Rust core, a drift-tolerant resolver locked to a single
kind. Promoting those two into a real **artifact reference** unlocks copy, CLI, agent access, and cross-linking at once.

Alongside that, one concrete defect is worth fixing on its own merits: **copy mode (`%`) and marks (`m`) are hard-gated
off on four of the five Artifacts sub-tabs.** They are absent from the `NON_PRS_ARTIFACT_ACTIONS` allow-list, so on
Commits, Plans, Chats, and Bugs there is no copy mode at all — not even `%s`, the tmux snapshot copy that works
everywhere else in the app.

---

## 1. Verified current state (2026-07-29)

### 1.1 There are two disjoint things called "artifacts"

| | **The Artifacts tab** | **Artifact files** |
| :--- | :--- | :--- |
| What | Commits, Plans, Chats, Bugs, PRs | Agent-produced images, markdown, PDFs, videos, explicit files |
| Where | `sase ace` → Artifacts (`src/sase/ace/tui/widgets/artifacts/`) | Agents tab → `a` (`src/sase/ace/tui/modals/artifact_files_modal.py`) |
| Model | 5 unrelated types | `ArtifactFile` (`src/sase/core/artifact_file_types.py:51`) |
| Storage | Repos, SDD sidecars, bead store, chats catalog | `~/.sase/artifacts/` + `index.jsonl` |
| Viewer | Textual modals (source text) | Rich terminal viewer: `kitten icat`, `mpv`, markdown→PDF→PNG paging, tmux side pane |
| Copy | 1 target per sub-tab | contents (`y`) + path (`Y`) |
| Marks | none | yes (`m`) |
| Reachable from the other | **no** | **no** |

The two surfaces never meet. `action_open_artifact_files` early-returns unless the Agents tab is active
(`src/sase/ace/tui/actions/agents/_panel_artifact_files.py:558`), and `check_action` disables the action outright
(`src/sase/ace/tui/app.py:362`). The best artifact viewer SASE has cannot be opened from the panel named "Artifacts".

The naming collision is not cosmetic. When the user says "the Artifacts panel," the surface they get has none of the
viewing and copying affordances that the thing actually named `ArtifactFile` already has.

### 1.2 Per-sub-tab capability matrix

Sourced from `src/sase/default_config.yml:181-231` and the five action modules under `src/sase/ace/tui/actions/`.

| Sub-tab | View | Copy | Open external | Reference / hand-off | Marks | `%` copy mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Commits** | `enter` → `CommitViewModal` (message + diff + linked plan) | `y` → **full SHA only** | — | — | — | **disabled** |
| **Plans** | `enter` → `PreviewPanelModal`; `l`/`h` expand | **none** | — | `w` launch epic, `o` open bug | — | **disabled** |
| **Chats** | `enter` → `PreviewPanelModal` | `y` → **absolute path** | `o` → `$EDITOR` | `a` → jump to agent | — | **disabled** |
| **Bugs** | `enter` → activate link | `y` → `#N <url>` | `o` → browser | `a` → seed agent prompt | — | **disabled** |
| **PRs** | `v` view files, `d` diff | `%` → **6 targets** | — | `a` → axe item | `m` yes | **enabled** |

Three observations fall straight out of this table:

**(a) Copy mode is unavailable on 4 of 5 sub-tabs.** `copy_tab_content` is bound to `%`
(`src/sase/ace/tui/bindings.py:189`) but is not in `NON_PRS_ARTIFACT_ACTIONS`
(`src/sase/ace/tui/actions/artifacts.py:39-74`), and `check_action` returns `False` for any action outside that
allow-list when a non-PR sub-tab is active (`src/sase/ace/tui/app.py:371-377`). `toggle_mark` is absent for the same
reason. The dispatcher underneath was never taught about sub-tabs either — `_handle_copy_key` branches on
`self.current_tab` only (`src/sase/ace/tui/actions/clipboard/_core.py:47-54`), and the Artifacts tab's internal id *is*
`"changespecs"` (`src/sase/ace/tui/tab_order.py:18`), so even if the gate were lifted today, `%n` on the Chats sub-tab
would copy the selected **PR's** ChangeSpec name. The config has exactly three key sets — `changespecs`, `agents`, `axe`
(`src/sase/default_config.yml:361-381`) — and no notion of an artifact sub-tab.

**(b) Each sub-tab picked one copy target and stopped.** Commits copies the 40-char SHA and nothing else
(`src/sase/ace/tui/widgets/artifacts/commits_detail.py:157-165`) — not the subject, not the message, not a
`repo@sha` pair, not the linked plan the modal already loads. Plans copies nothing at all. Chats copies the raw
absolute path, while the artifact-file modal's `Y` copies a workspace- or home-relative path
(`src/sase/ace/tui/modals/artifact_files_modal.py:107-131`) — two different answers to the same question in one app.

**(c) The same key means different things per sub-tab.** `o` is open-bug (Plans), open-in-`$EDITOR` (Chats), and
open-in-browser (Bugs). `a` is open-agent (Chats), seed-agent (Bugs), and toggle-all-projects (Commits). `y` is
copy-SHA, copy-path, copy-issue — and elsewhere in the app, plain refresh.

### 1.3 The full-screen viewer is a source-code pager

`PreviewPanelModal` is the primary read surface for Plans and Chats. Its entire binding set is scroll and close
(`src/sase/ace/tui/modals/preview_panel_modal.py:19-29`): **no copy, no search, no open-in-editor, no follow-link, no
rendered-markdown mode.** Content goes through `lazy_renderable(...)` — a Rich `Syntax` block with `line_numbers=True`
and the `monokai` theme (`preview_panel_modal.py:58-65`), so a plan or a chat transcript is displayed as raw Markdown
source with a gutter of line numbers.

This is inconsistent in two directions at once. The Plans *detail pane* on the same screen already uses the Textual
`Markdown` widget for rendered prose (`src/sase/ace/tui/widgets/artifacts/plans_navigation.py:8`,
`plans_pane.py:10`) — so pressing `enter` to see *more* of a plan renders it as *less*. And the terminal artifact-file
viewer renders the same Markdown to a typeset PDF and pages through it as PNGs
(`src/sase/ace/tui/graphics/viewer.py`, documented at `docs/ace.md:786`). Three renderers, three fidelities, one
document type.

`CommitViewModal` is the exception that proves the rule: it has copy, plan/commit toggling, next/prev traversal, and
`CopyModeForwardingMixin` (`src/sase/ace/tui/modals/commit_view_modal.py:41-57`). It is the only artifact reader that
behaves like a reader, and it was built for exactly one sub-tab.

### 1.4 The reference story: create-only, with no way to read back

`sase artifact-file` has exactly one subcommand — `create` (`src/sase/main/parser_artifact_file.py:22`), gated on
`SASE_AGENT=1` and `SASE_ARTIFACTS_DIR` (`src/sase/main/artifact_file_handler.py:26-42`). There is no `list`, `show`,
`path`, or `open`. An agent can *produce* an artifact and can print its id, but neither an agent nor a human can
*discover*, *read*, or *resolve* one from the CLI. The `sase_artifact_file` skill documents only creation
(`src/sase/xprompts/skills/sase_artifact_file.md`).

Compare the neighbours: `sase chat list|show` ships JSON output (`src/sase/main/parser_chat.py`), and
`sase plan list|search` supports `--kind {tale,epic,prompt,research}` (`src/sase/main/parser_plan.py:340-345`). Chats
and plans are addressable from the CLI; artifact files are not.

Artifact ids are stable and unique but not human-usable: `default:52895d68931185056fd0e49f`,
`explicit:d6320835d3f26b74c58ef424`. There is no short form, no display of the id anywhere in the UI, and no resolver.

### 1.5 Two universal primitives already exist — each used for one thing

**`ArtifactEntryTarget`** (`src/sase/ace/tui/widgets/artifacts/entry_navigation.py:11`) is a `tuple[str, ...]` that
every non-PR pane already computes for every row:

| Sub-tab | Target | Source |
| :--- | :--- | :--- |
| Commits | `("commit", repo, full_sha)` | `commits_timeline.py:21-23` |
| Chats | `("chat", absolute_path)` | `chats_list.py:31-34` |
| Bugs | `("bug", project_key, number)` | `bugs.py:382-384` |
| Plans | `(kind, project, identity)` | `plans_list.py:54-63` |

That is a discriminated, project-scoped, cross-refresh-stable identity for every artifact in the panel. It is currently
consumed by exactly one caller — `select_relative_entry`, which uses it to keep the cursor on the same row across a
refresh (`entry_navigation.py:36-66`). It is never rendered, never copied, never persisted, never resolved back to a
payload.

**`plans:` logical references** (`../sase-core/crates/sase_core/src/plan/refs.rs`) are the Rust core's answer to
"name an artifact durably." `parse_plan_reference` / `render_plan_reference` / `resolve_plan_reference` resolve a
logical path against *ordered roots*, accept four legacy path shapes, and include drift recovery that re-finds a file by
name when it has moved between month directories (`refs.rs:104-120`). It is deliberately locked to one kind —
`render_plan_reference` errors on anything but `"plans"` (`refs.rs:52-62`), so `research:202607/x.md` is rejected today
(`refs.rs:301`) even though `research` is a first-class SDD kind everywhere else (`src/sase/sdd/_paths.py:11`,
`../sase-core/crates/sase_core/src/plan/read.rs:36`).

The document-level counterpart already generalizes further: SDD provenance header blocks carry `PLAN`, `PROMPT`,
`PARENT`, `BEAD`, `AGENTS`, and `COMMITS` sections
(`../sase-core/crates/sase_core/src/plan/artifact_link.rs:26-33`). The vocabulary for cross-artifact linking exists; it
just stops at the document boundary and never reaches the UI or the CLI.

### 1.6 Corpus size — this is not a hypothetical

Measured on this host:

| Corpus | Count | Notes |
| :--- | ---: | :--- |
| Artifact files (`~/.sase/artifacts/index.jsonl`) | **3,984** | 3,775 image · 184 markdown · 25 file; **187 explicit** |
| — total on disk | **619 MB** | |
| — distinct producing agents | **532** | |
| Agent runs (`agent_artifact_index.sqlite`) | **5,072** | |
| Chat transcripts (`chats_catalog.sqlite`) | **10,311** | |

Every one of those 3,984 artifact files is reachable only by first locating its producing agent among 5,072 runs in the
Agents tab and pressing `a`. There is no list, no search, no cross-agent browse, and no CLI.

### 1.7 Adjacent gaps worth noting

- **Research reports are invisible in the panel.** Both plan-archive loaders hardcode `kinds=("tale", "epic")`
  (`src/sase/ace/tui/widgets/artifacts/plans_data_sources.py:176`, `:207`), so the `research` kind — a first-class SDD
  sidecar with its own repo, its own `#research` xprompts, and `sase plan search --kind research` — has no view in ACE.
  This document will not be visible in the Artifacts panel.
- **Jump All excludes artifacts.** The `` ` `` modal's "Artifacts" section is built from ChangeSpecs only
  (`src/sase/ace/tui/modals/jump_all_modal.py:128-133`), and `jump_to_all_entries` is not in
  `NON_PRS_ARTIFACT_ACTIONS` anyway.
- **The footer never mentions artifacts.** `KeybindingBindingsMixin` has no non-PR sub-tab branch
  (`src/sase/ace/tui/widgets/_keybinding_bindings.py`), and `update_copy_bindings` handles only the three legacy tab
  names (`src/sase/ace/tui/widgets/_keybinding_modes.py:390-430`).
- **The mobile gateway exposes `artifact_dir` as an opaque host path** and serves no artifact content
  (`docs/mobile_gateway.md:461`), so no non-TUI surface can view artifacts either.
- **Nothing is in flight.** 73 commits have touched the Artifacts panel since May, but exactly one bead is open
  (`sase-an`, a flaky-test fix). This is a clear field.

---

## 2. Diagnosis

The panel's problems are not five independent feature gaps. They are one missing abstraction plus one gating bug.

**The missing abstraction.** Six artifact kinds, six models, six keymaps, six copy semantics — and no type that says
"this is an artifact." Every new sub-tab pays full freight: its own identity function, its own copy action, its own
detail renderer, its own key vocabulary. That cost is why Plans shipped with no copy verb at all and why Chats copies a
differently-formatted path than the artifact-file modal. The abstraction that would collapse this is already computed on
every row (`ArtifactEntryTarget`) and already resolved durably in Rust for one kind (`plans:` refs). Nothing needs to be
invented — two existing primitives need to be joined and promoted.

**The gating bug.** `NON_PRS_ARTIFACT_ACTIONS` is an allow-list, so every app-level action is denied by default on
non-PR sub-tabs. That was the right call for `add_axe_item`; it silently swallowed `copy_tab_content` and `toggle_mark`.
The user-visible result is that the app's general-purpose copy verb — including `%s`, which has nothing to do with
ChangeSpecs — simply does not respond on four of five sub-tabs.

**Where the work belongs.** Per the `rust_core_backend_boundary` rule: reference parsing, rendering, resolution, and
artifact-index queries are core backend logic — a web app or editor integration would need identical semantics — and
belong in `../sase-core` alongside `plan/refs.rs`. Keymaps, modal bindings, footers, and rendering stay in this repo.

---

## 3. Ranked recommendations

Ordered by (value × confidence) ÷ cost. Items 1–3 are independently shippable and each stands alone; 4–7 compound on
them; 8–10 are follow-on polish.

### 1. Restore copy mode and marks on every Artifacts sub-tab — *S, immediate*

Add `copy_tab_content` and `toggle_mark` to `NON_PRS_ARTIFACT_ACTIONS`; add a
`copy_mode.keys.artifacts.{commits,plans,chats,bugs}` block to `default_config.yml`; branch `_handle_copy_key` on
`current_artifacts_subtab` before falling through to `current_tab`; extend `update_copy_bindings` to accept a sub-tab.

Give each sub-tab a real menu instead of one hardcoded target — Commits: `%%` sha · `%m` message · `%r` `repo@sha` ·
`%p` linked plan ref · `%s` snapshot. Plans: ref · path · title · body. Chats: path · agent name · transcript body.
Bugs: `#N` · url · title · agent-ready prompt.

This is the highest-confidence item on the list: it is a small, well-bounded change; it fixes a defect users can hit
today (`%s` not responding); and it multiplies copy targets from 4 total to roughly 20 without introducing any new
concept. Do this first even if nothing else on this list happens.

### 2. Promote `ArtifactEntryTarget` into a first-class artifact reference — *L, keystone*

Generalize `plan/refs.rs` into `sase_core::artifact_ref` with a kind-tagged grammar over the tuples the panel already
produces:

```
commit:<repo>@<sha>      chat:<path>          bug:<project>#<n>
plans:<path>             research:<path>      file:<artifact-id>
```

Keep everything `plan/refs.rs` already does right — ordered-root resolution, legacy path acceptance, drift recovery —
and add per-kind resolvers. Expose `parse` / `render` / `resolve` through the binding; make `render_plan_reference`
accept `research` on the way past (it is already a `read.rs` kind).

Then wire it in three places: `%` yields a ref (item 1), the CLI resolves one (item 4), and agents can paste one into a
prompt (item 9). This is the keystone — items 4, 6, and 9 are cheap once it lands and expensive without it — but it is
also the largest single piece, and it crosses the Rust boundary. Sequence it after item 1 so the panel is already
usable while this is built.

### 3. Make `PreviewPanelModal` a real reader — *M, high daily value*

Add to the modal that Plans and Chats both open: `y` copy contents · `Y` copy path · `%` copy ref · `/` in-document
search with `n`/`N` · `o` open in `$EDITOR` · `R` toggle rendered Markdown (the Textual `Markdown` widget the Plans
detail pane already uses) · `Z` hand off to the rich terminal viewer (item 5). Adopt `CopyModeForwardingMixin`, which
`CommitViewModal` already uses.

`CommitViewModal` is the working template — this is mostly bringing the other two readers up to the standard one sub-tab
already sets. The rendered-Markdown toggle alone removes the oddity that pressing `enter` on a plan makes it *less*
readable than the detail pane behind it.

### 4. Ship `sase artifact` as a read CLI, and extend the agent skill — *M, unblocks agents*

`sase artifact list [--kind] [--project] [--agent] [--since] [-j]`, `show <ref>`, `path <ref>`, `open <ref>`, backed by
`~/.sase/artifacts/index.jsonl` and the item-2 resolver. Then extend `sase_artifact_file.md` from create-only to
create-and-read.

Today an agent can write into a 3,984-file / 619 MB store it cannot read, and a human has no CLI path to it at all. This
also gives the TUI a tested backend to call rather than growing a second query path, and it is the natural place to add
cross-agent search. `sase chat list -j` is the precedent to match.

### 5. Reach the rich artifact-file viewer from the Artifacts panel — *M*

Either add a sixth **Files** sub-tab backed by the global index, or lift the `current_tab != "agents"` gate so the `a`
picker opens with the panel's project scope applied. The viewer itself — `kitten icat`, `mpv`, markdown→PDF paging,
tmux side pane — needs no changes; only its reachability does.

Prefer the sub-tab: it makes the store browsable by project and kind rather than by "which of 5,072 agent runs produced
this," and it is the surface where `%`/marks/preview from items 1–3 apply for free.

### 6. Marks and bulk actions across artifact sub-tabs — *M*

Once item 1 admits `toggle_mark`, use `ArtifactEntryTarget` as the mark identity (it is already stable across refresh —
that is what it was built for). Then: copy all marked refs, open all marked in the viewer, seed one agent prompt from a
marked set. The artifact-file modal already proves the pattern end to end (`m` mark, `A` open all, marked-set copy).

### 7. Surface `research` in the Plans sub-tab — *XS*

Change `kinds=("tale", "epic")` to include `"research"` in both loaders
(`plans_data_sources.py:176`, `:207`) and add a kind facet to the plan filter bar. The plan-search facade, the Rust
reader, and the sidecar all support it already; this is a two-line change plus a filter chip. Small enough to land with
item 1.

### 8. Normalize the per-sub-tab key vocabulary — *S, do it with item 1*

Fix the meanings that currently collide: `o` = open externally (everywhere), `y` = copy primary (everywhere),
`a` = agent hand-off (everywhere), and move Commits' `a` (toggle-all-projects) to a filter-bar facet. Breaking, so bundle
it with the item-1 keymap change and one `docs/ace.md` update rather than shipping it separately.

### 9. Artifact refs in the prompt bar — *M, depends on item 2*

Let `@`-completion offer artifact refs from the index alongside file-reference history, and expand refs to concrete
paths in `process_file_references` at launch. Add `%`-to-prompt so a copied ref can be dropped straight into a new agent
prompt. This is the payoff that makes item 2 worth its cost: artifacts stop being things you look at and become things
you hand to an agent.

### 10. Extend Jump All and the footer to cover artifacts — *S, polish*

Add commit/plan/chat/bug entries to the `` ` `` modal (it already groups by tab and already labels the group
"Artifacts") and add non-PR sub-tab branches to the keybinding footer so the panel's own keys are discoverable without
opening help. Real but small; do it last.

---

## What I would not do

- **Do not add a web or GUI artifact viewer.** The terminal viewer already handles image, video, Markdown, PDF, and text
  with tmux integration. The problem is reachability (item 5), not capability.
- **Do not introduce a new artifact storage format or a second index.** `index.jsonl` plus
  `agent_artifact_index.sqlite` are adequate for 3,984 rows; the gap is a query API (item 4), not a schema.
- **Do not build a generic artifact plugin system yet.** Five kinds is not enough to justify the indirection. Revisit
  after item 2 has proven the reference grammar across all of them.

## Open questions for the user

1. **Ref syntax.** Should refs reuse the existing `plans:` colon form (`commit:sase@abc123`) or adopt the `#`-sigil
   convention that xprompts already own? The colon form is consistent with what the Rust core resolves today; the
   `#` form is more familiar in prompts but risks collision with xprompt parsing.
2. **Files sub-tab vs. lifted gate** for item 5 — a sixth sub-tab is more work but makes the 619 MB store genuinely
   browsable, which the picker never will be.
3. **Does item 1 need to wait for item 2?** Recommended sequencing says no: ship per-sub-tab copy with literal values
   now, and let the ref become one more `%` target once item 2 lands.
