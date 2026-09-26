# Prompt recall tabs and stash trash: consolidated design research

**Date:** 2026-09-26  
**Question:** Should SASE combine its prompt stash and prompt history pickers, and how should a bounded trash for deleted stash entries work?

## Recommendation in brief

Yes. Build one **Prompts** overlay with three unnumbered sub-tabs: **Stash | History | Trash**. Each tab keeps its own data, keys, and state. Existing shortcuts open the same tab they effectively open today. Trash is a recovery buffer for deliberately discarded *stash entries*; it does not collect successful stash restores or prompt-history deletions.

Keep Stash's current `d`/`D` **mark, then Enter** gesture. A trash entry can be evicted immediately when the limit is full, so making `d` an instant action would imply more safety than the feature guarantees. The Trash tab should restore entries to Stash; loading them into the prompt bar remains a separate Stash action.

Implement the active-to-trash transition, restore, purge, and retention in `sase_core` using **one lock and one atomic file replacement**. The Rust store returns authoritative active/trash snapshots, and the TUI updates only after success. Set `ace.prompt_stash.trash_limit: 20`; zero explicitly disables recovery. Count entries, including a multi-pane bundle as one entry. Add glossary strands for **Prompt Stash** (alias **stash**) and **Stash Trash**.

## Evidence and current behavior

I compared the four independent reports ([cdx](prompt_recall_tabs_and_stash_trash__cdx.md), [grk](prompt_recall_tabs_and_stash_trash__grk.md), [mus](prompt_recall_tabs_and_stash_trash__mus.md), [gem](prompt_recall_tabs_and_stash_trash__gem.md)) with the current `sase` and linked `sase-core` code. The decisive observations are:

- `StashedPromptsModal` is a small list/preview picker. `1`–`9`/`0` restore by row; `Tab` marks restores; `Space` pins; `d`/`D` mark deletion; `Enter` applies. Unpinned restore removes an entry; pinned restore keeps it. A stored row may contain an ordered bundle of prompt panes. Failed launches can also add live stash entries. Sources: `src/sase/ace/tui/modals/stashed_prompts_modal.py`, `src/sase/ace/tui/actions/agent_workflow/_prompt_bar_stash_restore.py`, `crates/sase_core/src/prompt_stash/wire.rs`.
- `PromptHistoryModal` has a focused filter, project-aware selection, paging, and separate submit/load/edit/copy actions. Its store uses monthly `YYMM.json` shards, not the stash JSONL. There is no TUI `d` action, although CLI history deletion/pruning exists; calling history an immutable audit log overstates its guarantee. Sources: `src/sase/ace/tui/modals/prompt_history_modal.py`, `src/sase/history/prompt_store.py`, `src/sase/ace/tui/actions/agent_workflow/_entry_prompt_history.py`.
- The stash store already uses a shared/exclusive file lock and atomic temporary-file replacement for rewrites. Current disk rows have no file-level version tag; Rust/Python snapshot wires have schema version 1. `pop`, pin, and rewrite parse rows and then rewrite the file. Sources: `crates/sase_core/src/prompt_stash/store.rs` and `wire.rs`; `src/sase/core/prompt_stash_wire.py`.
- The present partial-delete path removes rows from the visible modal immediately after posting `DeleteRequested`, *before* the asynchronous `pop_prompt_stash` call succeeds. If persistence fails, the error toast appears while the open picker remains wrong. This is a concrete reliability defect to fix in the new flow.
- `PanelTabStrip` already supports clickable tabs, compact labels, and no numeric shortcuts. The current TUI performance guidance requires lazy off-thread I/O, pump-free async work, and rechecking selection after awaits. Sources: `src/sase/ace/tui/widgets/panel_tab_strip.py` and the audited TUI performance memory.

The merge is good information architecture: all three tabs answer “where is a prompt I wrote?” It becomes a poor design if their records or `Enter` meanings are flattened into one list. A separate main TUI tab would also be a larger destination than this picker needs.

## Decisions and justified changes to the request

| Decision | Reason |
| --- | --- |
| Call the third tab **Trash**, not Archive. | Automatic eviction makes “archive” a false durability promise. |
| Only `d`/`D` deletion from **Stash** enters Trash. | Restoring an unpinned draft is taking it back, and history has a different store and lifecycle. |
| Interpret `N` as stash **rows/bundles**, default 20; `0` means permanent deletion. | It matches the selectable unit, preserves bundle integrity, and gives a clear opt-out. Do not add an arbitrary maximum such as 200 without evidence. |
| Preserve `id`, text, frontmatter, project, source, cursor, pane order, creation time, and pin. | A recovery action must be lossless. A pinned row can be trashed, but needs a more explicit confirmation. Pins do not exempt trash rows from eviction. |
| Order and evict by **time of deletion**, not original creation. | “Last N deleted” is otherwise violated when an old draft is deleted today. Use a deterministic tie break for a batch. |
| Keep `d` as a mark and `Enter` as commit; `D` marks all. | This preserves muscle memory and gives the user a chance to see overflow and pinned-row consequences before committing. |
| Trash `Enter`/digits restore to **Stash** and remain in the overlay. | Recovery should not unexpectedly replace a live prompt bar or launch a prompt. |
| Open the overlay even when Stash is empty. | Today's empty-stash toast would make Trash inaccessible through stash shortcuts. Preserve the bare-`@` single-live-entry fast path. |
| Do not add a new global Trash shortcut for v1. | `[` wraps from Stash to Trash, the strip is clickable, and the existing shortcut map remains stable. |

An entry-count limit is **not a byte limit**. Twenty large bundled prompts can still consume substantial space. Document that fact; add a byte policy only if actual usage warrants it.

## Interaction and visual design

Use a single stable frame titled **Prompts** with `PanelTabStrip`, a one-line tab caption, a list/preview body, and one contextual footer. Keep the list/preview split in the same columns on every tab; collapse the preview at narrow widths as the current stash picker does. Lazy-load and cache each child pane. In particular, opening Stash must not scan history shards. Keep each pane's highlight, scroll, filter, loaded pages, and uncommitted marks when switching.

The unnumbered order **Stash | History | Trash** puts the working drafts first and the destructive destination last. `[`/`]` cycle, including wraparound, and clicking a tab selects it. Do not use `1`/`2`/`3` as tab shortcuts because stash digits already restore rows. The History filter currently owns normal typing; give tab cycling an explicit priority handler and test it while the filter is focused. `Esc` always closes; `q` closes only outside a text input so it can still be typed into the History filter.

| Tab | Primary and secondary keys |
| --- | --- |
| **Stash** | `Enter` or `1`–`9`/`0` restore to prompt bar; `Tab` marks restore, `a` marks all for restore, `Space` toggles pin; `d` marks one for Trash, `D` marks all; `Enter` applies marks. Preserve `j`/`k` and preview scrolling. |
| **History** | Keep the current filter, `Enter` submit, `Tab` load to prompt bar, `Ctrl+G` edit, `Ctrl+Y` copy, `Ctrl+J`/`Ctrl+K` page, and `Ctrl+X` cancelled toggle. No history deletion key. |
| **Trash** | `Enter` or `1`–`9`/`0` restore to Stash; `Tab` marks restore, `a` marks all for restore; `d` marks one for permanent deletion, `D` marks all; `Enter` applies marks. `Ctrl+Y` may copy without changing lifecycle. Pin editing is unavailable. |

Each footer must spell out its `Enter` verb: “restore to bar,” “submit,” or “restore to Stash.” Destructive Trash marks should turn red and explicitly say “permanently delete”; the resting Trash tab can use amber, Stash the existing orchid, and History the current cool accent. Avoid depending on wide emoji glyphs; compact tab labels and text must remain legible in narrow terminals. Show `Stash 3` and `Trash 2/20`; do not pay for an exact, potentially expensive History count.

The empty Stash state should say how to stash a draft and point to Trash when it contains entries. Empty Trash should say where discarded drafts appear. When the limit is zero, explain that Trash is disabled. A full Trash count is useful but insufficient warning: before a bulk Stash operation that will evict rows, show the expected permanent-loss count. The Rust outcome reports the actual evictions, which the success toast must name because another process can race the preview. A pinned row among the marks also triggers an explicit confirmation. No automatic jump to Trash after a Stash deletion.

Existing entry points deep-link into the overlay: `@`/`,@`/`Ctrl+G p`/stash chip/empty `Ctrl+S` open Stash (with the existing lone-live-entry `@` fast path); `Ctrl+K`/`,.`/`,>` open History with their existing seed, home/MRU, and cancelled-state behavior. `,Ctrl+G` may retain its direct edit-newest path. The two present History callers use different result callbacks for a live prompt bar versus the main TUI. The new shell must carry that **origin context** through tab switches; merely reusing the initial modal callback would produce wrong launch/load behavior after switching from Stash to History.

## Persistence design and the disagreement between reports

The cdx and grk reports favor one stash file; mus also favors in-band trash; gem favors a separate trash file. The separate file keeps old active readers simple and isolates data, but **taking two locks does not make two file renames atomic**. A crash after removing a live row and before writing trash loses it; reversing the order can duplicate it. A separate-file design needs a write-ahead journal and recovery protocol, which is disproportionate for this bounded feature. Choose one physical `prompt_stash.jsonl` lock domain with two logical record kinds.

Keep existing active-row JSONL records readable. Represent trash as a distinct tagged envelope, for example `{"kind":"trash","trashed_at":"...","entry":{...}}`. A plain `trashed_at` field on an otherwise normal active row is unsafe: today's serde reader ignores unknown fields and would present that row as live. The new Rust parser must return separate active/trash collections. Its reader and every existing mutator (`append`, `pop`, `set_pinned`, `rewrite`) must preserve trash; `pop` and pin operate only on active IDs. In particular, `rewrite` is currently a merge in which caller rows win by ID: a stale active snapshot must never overwrite or resurrect an ID already in Trash. Reject that conflict or ignore the stale input under the lock.

Add core operations for trash, restore, purge, and limit reconciliation. Each mutation takes the existing exclusive lock, reads once, transforms by stable IDs, atomically replaces the file, and returns both snapshots plus changed and evicted IDs. Unknown or already-transitioned IDs are no-ops. Produce `trashed_at` once in UTC at the transition; re-trashing a restored entry gets a new time. Prune the oldest Trash entries within the same transaction until `len(trash) <= N`. Reconcile a lowered limit on the first trash-aware open or write after config reload, off-thread, and report any evictions. A batch larger than N may evict some of its own oldest entries; confirmation text must make this clear.

The new parser must also account for malformed or future record kinds without silently discarding their bytes during a rewrite; preserve opaque lines or fail the mutation. This extends an existing weakness: the current parser counts malformed rows but typed rewrites omit them.

**Upgrade boundary:** schema version 1 is a *wire* version, not an on-disk gate. A tagged trash envelope is invalid to the old Rust reader, and an old `pop`/pin/rewrite can silently discard it when rewriting the file. The one-file design therefore requires a coordinated `sase-core` binding, Python wire, and `sase-core-revision.txt` cutover; running old and new TUI processes against the same stash after the first trash write is unsafe. Specify restart guidance and a recoverable backup/migration step before enabling the new format. Test this explicitly rather than claiming effortless backward compatibility. The separate-file alternative avoids this old-reader hazard but replaces it with a cross-file crash hazard unless journaled.

## Configuration, glossary, and delivery

Put `ace.prompt_stash.trash_limit: 20` in the bundled default and JSON schema (`integer`, minimum `0`), with a defensive accessor that accepts only real nonnegative integers, rejects booleans, and falls back to 20 for malformed config. Pass the value into Rust; Rust should not parse `sase.yml`. This path is appropriate for the current ACE picker, although a future CLI trash command should read the same setting rather than inventing a second one. Update configuration and keymap documentation. If a new global action is introduced later, update `src/sase/default_config.yml` with its default keymap.

Add glossary strands through the SASE memory-write workflow during implementation:

> **Prompt Stash** (alias **stash**): the per-user collection of saved, unsubmitted prompt drafts. A stash entry is one atomic row, possibly containing an ordered bundle of panes; pinned entries stay in Stash when loaded into the prompt bar. Discarding an entry moves it to Stash Trash.
>
> **Stash Trash**: the bounded recovery collection of Prompt Stash entries discarded from the Stash tab. It preserves the full entry and the deletion time; restoring returns the entry to Stash. Entries beyond the configured limit are permanently removed. It does not contain prompt-history records or successful stash restores.

These two strands should link to each other. Do not use **archive** or bare **trash** as a glossary alias: both would imply a broader or longer-lived collection. “Prompt History” can be added separately if the team wants the trio defined, but it is not required by this request.

Implement in this order: (1) Rust lifecycle operations, backward-format and concurrency tests, PyO3 registration; (2) Python wire/facade, config/schema/docs, and core revision pin; (3) shared modal shell and existing History/Stash child panes; (4) Trash pane, transactional refresh, empty states, and entry-point routing; (5) glossary, Help text, demo, narrow/wide visual snapshots. Ship the user-visible cutover with recovery available at the same time that `d` starts trashing.

Acceptance tests should cover the full field-preserving active → trash → active round trip; N of 20, 1, and 0; lowering N; a bulk operation larger than N; equal timestamps; pinned and bundled entries; concurrent append/trash/restore; stale rewrite protection; malformed/unknown lines; binding/schema parity; persistence failure leaving rows and marks visible; all original entry points and History callbacks; empty Stash with nonempty Trash; focused-filter tab navigation; and responsive first paint. Follow SASE's pump-free worker pattern and measure before/after key-to-paint latency if the modal refactor affects navigation.

## Recommended solution

Build the **Prompts** overlay as **Stash | History | Trash**, preserving each tab's behavior and existing entry shortcuts. Make `d`/`D` in Stash stage a move to bounded Trash, then commit on `Enter`; show confirmations for pinned rows and real retention loss. Restore from Trash to Stash, and reserve permanent deletion for Trash. Keep a default of 20 recoverable stash entries, configurable at `ace.prompt_stash.trash_limit`, with zero as an explicit opt-out. Put the transaction and retention in the Rust stash store under one lock and one atomic rewrite, and repaint the TUI only from the transaction result. Add the two requested glossary terms and the coordinated upgrade safeguards.
