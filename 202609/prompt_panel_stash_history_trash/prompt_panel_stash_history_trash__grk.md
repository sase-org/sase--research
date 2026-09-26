# Merged prompt panel: stash, history, and stash trash

- **Researcher:** grk (independent swarm report)
- **Date:** 2026-09-26
- **Scope:** TUI overlay for prompt stash + prompt history, plus a bounded stash-trash
  recovery surface. Persistence belongs in `sase-core`; presentation stays in sase.

## Verdict

The request is a good idea and should be built. Two near-identical list-plus-preview
overlays that both answer "give me a prompt back" are already one product surface
wearing two doors. A third door for "I deleted that by accident" belongs on the same
surface.

Do not flatten the three collections into one searchable list. Do not add a main TUI
tab. Do not send launched prompt-history rows into stash trash. Keep the overlay
picker, give it three sub-tabs with distinct keymaps, and make `d` on Stash a
recoverable trash instead of a hard pop.

The rest of this report is the design that makes that cutover intuitive, reliable, and
visually coherent.

---

## 1. Critique of the request

### 1.1 What is already right

- **Sub-tabs, not a soup.** Stash and history share a silhouette (list, preview, hints)
  and almost nothing else: primary action, dataset size, filter, paging, pins, numbered
  restore. Sub-tabs keep those contracts intact while giving them one chrome.
- **Trash is the right safety net.** Today's stash `d` is irreversible once confirmed.
  That is why the picker uses mark-then-Enter. A bounded trash lets `d` become a fluid
  key instead of a ritual.
- **Last-N beats a calendar window.** Drafts are not photos. Twenty recent discards is
  a better default than "30 days," and it has a hard disk bound the user can name.
- **Glossary terms are overdue.** "Prompt stash" / "stash" and "stash trash" are
  user-facing language that does not exist in the glossary web at all.
- **Config, not a feature flag.** The cap is a permanent user choice. That is a
  `sase.yml` field. A beta flag is only justified if a phase would ship a half-built
  overlay; the cutover below lands as one user-visible change.

### 1.2 Where the request is under-specified or risky

1. **History and stash have hostile keymaps.** History `Enter` *launches*. Stash
   `Enter` *restores*. History `Tab` loads into the input. Stash `Tab` marks a row.
   Stash `1`–`9` restore rows. Config/Artifacts use those digits for sub-tabs. A merged
   panel that pretends one keymap set works will launch a draft or steal restore keys.
2. **`d` today is a mark, not a delete.** The request says "deleted with the `d`
   keymap." In `StashedPromptsModal`, `d` only stages a mark; `Enter` commits, and a
   delete-only confirm keeps the picker open. Trash changes the cost of that extra
   step.
3. **Empty stash currently refuses to open.** `_open_prompt_stash_panel` toasts "No
   stashed prompts to restore" when the live pile is empty. After trash exists, that
   toast hides the recovery tab.
4. **Pop versus delete.** Unpinned restore already *pops* the row via
   `pop_prompt_stash`. That is "I took it back," not "I discarded it." Putting pops in
   trash would fill the 20 slots with successful restores.
5. **"Panel" in this codebase is an overlay modal.** Stash and history are
   `ModalScreen`s. Config Hub and Artifacts are persistent destinations. This feature
   is a picker that returns a result to the prompt bar. It must stay an overlay.
6. **Persistence is core, not Python.** Stash already lives in
   `sase_core::prompt_stash` as `~/.sase/prompt_stash.jsonl` behind a store lock.
   Trash that is "moved" in the TUI and "really deleted" in Python will race with
   failed-launch stashes and a second TUI.
7. **History already has a destructor.** `sase prompt delete` / `prune` operate on the
   monthly shard store. Funneling those into stash trash mixes a launch log with a
   draft pile.

### 1.3 Is merging history and stash actually a good idea?

Yes, with a hard boundary between *collections* and *chrome*.

| Collection | What it is | Primary action | Size |
| --- | --- | --- | --- |
| Stash | Drafts the user set aside | Restore to the prompt bar | Tiny JSONL pile |
| History | Prompts that were launched or cancelled | Submit / load / edit | Sharded, paged, filtered |
| Stash trash | Drafts the user discarded | Untrash, then maybe restore | Last N |

Users already treat `@`, `Ctrl+G p`, `Ctrl+K`, and `,.` as "prompt recall." Teaching a
third modal for trash would be worse than teaching a third sub-tab. The Help modal
(`[` / `]` + `PanelTabStrip` + `ContentSwitcher`) and Config Hub (lazy children +
caption under the strip) already prove this chrome in this TUI.

The alternative that is *not* worth it: keep history as its own modal and only add
Stash | Trash to the stash picker. That is smaller, and it is the right fallback if
the merge slips. It also leaves two overlays that still look like siblings and makes
trash undiscoverable from the history muscle-memory path. Merge them.

---

## 2. Justified requirement adjustments

These change the request. Each is deliberate.

| # | Adjustment | Why |
| --- | --- | --- |
| A1 | **`d` on Stash immediately trashes** the highlighted row. Drop mark-then-Enter for single-row delete. Keep `D` as "trash all" with a confirm. | Trash *is* the undo. The current two-step exists because delete was final. |
| A2 | **In-panel `u` undoes the last stash-tab trash** (and the last trash-tab purge) while the overlay is open. | Gmail-style snackbar, in a TUI: no extra modal, no auto-jump to Trash. |
| A3 | **Stash trash holds only stash discards.** History `sase prompt delete` / `prune` stay on the history store. History gets no `d` in this feature. | Different stores, different meaning. "Stash trash" is the glossary term for a reason. |
| A4 | **Unpinned restore continues to pop without trashing.** | Pop is take-back, not discard. |
| A5 | **Stay an overlay modal.** Do not add a main TUI tab or an Admin Center pane. | This is a picker with a result callback, like Help, not a destination like Config. |
| A6 | **Sub-tab order is `Stash · History · Trash`.** | Life of a prompt: draft, launched, discarded. Trash last, like every other trash UI. |
| A7 | **Do not number the sub-tabs.** Cycle with `[` / `]` (Help/Artifacts/Config already do). Clicks work. Stash/Trash keep `1`–`9`/`0` as row restore. | Digit collision is the merge's sharpest edge. |
| A8 | **Entry points land on a tab; they do not all open "the panel."** `Ctrl+K` / `,.` / `,>` → History. `@` / `,@` / empty `Ctrl+S` / stash chip / `Ctrl+G p` → Stash. No new global keymap for Trash in v1. | Muscle memory survives. |
| A9 | **An empty live stash still opens the overlay** on Stash, with a composed empty state. Auto-restore-single for `@` is unchanged when exactly one *live* row exists. | Otherwise trash is unreachable from the current empty-stash toast. |
| A10 | **Do not auto-switch to Trash after `d`.** Stay on Stash; toast "Moved to stash trash"; `u` undoes; the Trash tab shows a count. | Jumping tabs on every delete is nauseating. |
| A11 | **Config key is `prompt_stash.trash_max_entries`, default `20`.** `0` disables trash (today's hard delete). Clamp to `0..=200`. | This is store policy, used by failed-launch stash as well as the TUI, so it does not live under `ace.`. |
| A12 | **One user-visible cutover.** Core + facade may land first internally; do not ship trash without a recovery tab, or a merged chrome without trash. No beta flag if the overlay lands complete. | Half-states are worse than a slightly larger epic. |
| A13 | **Preserve pin, cursor, frontmatter, bundle, project, source, and id** across trash ↔ stash. Pins are not toggleable on Trash. | Restore must be lossless. |

---

## 3. What the product does today

### 3.1 Two overlays, one silhouette

**Prompt history** (`PromptHistoryModal`, `docs/ace.md` "Prompt History Modal"):

- Opened by `Ctrl+K` (prompt-bar, single-line, project-seeded filter), `,.` (unscoped),
  `,Ctrl+G` (edit newest), `,>` (cancelled visible).
- Filter input focused on mount. Grammar: optional leading `project:<value>` plus
  literal substring. Pages of `ace.page_size` (default 100) via `Ctrl+J` / `Ctrl+K`.
- `Enter` submits (launches). `Tab` loads into the input. `Ctrl+G` opens `$EDITOR`.
  `Ctrl+X` toggles cancelled. `Ctrl+Y` copies and closes.
- Store: monthly shards `~/.sase/prompt_history/YYMM.json`, sidecar lock, catalog IDs
  `ph_<sha256[:12]>`. Curated by `sase prompt delete` / `prune`. No TUI delete.

**Prompt stash** (`StashedPromptsModal`, called "the unified stashed-prompt picker" and
"prompt-stash panel" in docs):

- Opened by `@` (auto-restore a lone live row), `,@` / chip / empty `Ctrl+S` /
  `Ctrl+G p` (picker). Empty live stash toasts and does not open.
- Newest-first. `1`–`9`/`0` restore. `space` pins (persisted immediately). `Tab` marks
  restore. `d` / `D` mark delete. `Enter` confirms. Pinned restore keeps the row;
  unpinned restore pops it. Delete-only confirm stays open via `DeleteRequested`.
- Store: `~/.sase/prompt_stash.jsonl` through `sase_core_rs`
  (`read` / `append` / `pop` / `set_pinned` / `rewrite`). Failed launches also append
  (`stash_failed_launch_prompt`). Top-bar `stash: ≡ N` chip in orchid `#FF87D7`.
- `UpdatePinnedStashModal` (`gS`) stays a separate overwrite picker. Out of scope.

Both already split list/preview at 110 columns, debounce the preview, and share the
"thick `$primary` frame, hints under the list" look — with *different* CSS, heights,
and title treatments. History is `1fr` flexible; stash is a fixed 23-row body.

### 3.2 Sub-tab chrome that already exists

Reuse, do not reinvent:

- `PanelTabStrip` — clickable one-line strip with full/compact/micro reflow, optional
  numbers, per-tab accent, hover description.
- `ContentSwitcher` — Help modal, Config Hub, Projects pane, Artifacts view.
- `[` / `]` — Help overlay, Config Hub (even from filter inputs), Artifacts, Projects.
- Config Hub's **lazy child factory + one-line caption under the strip** is the
  closest "several different tools, one frame" pattern.
- Artifacts' **pane brief + footer-hint lane** is the closest visual grammar: stable
  slots that swap copy, never insert/remove rows.

### 3.3 Core store shape

`PromptStashEntryWire` today: `id`, `created_at`, `text`, `frontmatter`, `project`,
`source`, `pane_index`, `pinned`, optional `cursor`. Schema version **1**. `pop`
rewrites the JSONL atomically under an exclusive lock; unknown ids are ignored;
`rewrite` is a merge and cannot delete. A second TUI or a failed-launch append can
run concurrently.

Old readers that rewrote the file would drop unknown fields. Trash therefore cannot
be a silent extra key on schema 1.

---

## 4. Alternatives considered

| Approach | Verdict |
| --- | --- |
| **A. Merged overlay, three sub-tabs** (recommended) | One chrome, three contracts, trash discoverable, entry points preserved. |
| **B. Stash \| Trash only; history stays a second modal** | Smaller. Leaves two sibling overlays. Trash hidden from `Ctrl+K`. Fallback if the merge slips. |
| **C. One list with chips / a filter for kind** | Keymaps cannot share a list. History paging and stash digits will fight. |
| **D. Soft-delete in the stash list (dimmed rows)** | No separate tab. Mixes live drafts with discards. N-cap is harder to explain. The request wants a tab; it is also the clearer model. |
| **E. Undo toast only, no trash tab** | Elegant for the last delete, useless for "what did I trash yesterday." Need both. |
| **F. Main TUI tab or Admin Center pane** | Wrong object. This returns a prompt to the bar; it is not a place you live. |
| **G. Separate `prompt_stash_trash.jsonl`** | Old cores would ignore it (good) but a crash between pop and append can lose a row unless both files share one atomic rewrite. Same JSONL under one lock is simpler. |
| **H. Time-based retention (30 days)** | Wrong unit for drafts. Last-N is the request and the better default. |
| **I. History deletions also enter stash trash** | Mixes stores. History already has `sase prompt prune`. Out of scope. |

---

## 5. Recommended design

### 5.1 Object model

One overlay: **the prompt panel**. Three sub-tabs, three collections.

```
┌──────────────────────────────── prompt ────────────────────────────────┐
│  ≡ Stash 3  │  History  │  ◌ Trash 2                                   │
│  › Drafts you set aside. Pin, restore, or trash.                       │
│                                                                        │
│  [ list ]                              [ preview ]                     │
│                                                                        │
│  1-9/0 restore · space 📌 · tab ✓ · d trash · u undo · [ ] tabs        │
└────────────────────────────────────────────────────────────────────────┘
```

- **Stash** — live `PromptStashEntryWire` rows, `trashed_at` absent.
- **History** — existing prompt-history catalog. Unchanged store.
- **Trash** — the same stash rows with `trashed_at` set, newest-trashed first,
  capped at `prompt_stash.trash_max_entries`.

Name in the glossary and in copy: **prompt panel** for the overlay, **prompt stash**
(alias **stash**) for the live pile, **stash trash** for the discarded pile, **prompt
history** for the launch log. The window title is the short word `prompt`, in the
active tab's accent, so the strip — not a long title — does the talking.

### 5.2 Visual grammar

Steal the Artifacts "stable slots" rule. The overlay always has, in this order:

0. **Frame** — thick `$primary` border, 96% × max 156, same as today's stash picker
   (history currently uses a looser 90%-class modal; converge on the stash frame so
   `@` and `Ctrl+K` feel like the same object).
1. **Sub-tab strip** — `PanelTabStrip`, `uppercase_active=True`, **no numbers**,
   `reflow_to_fit=True`. Accents:
   - Stash: `#FF87D7` (existing chip; glyph `≡`)
   - History: `$accent` (existing history highlight; no glyph, or a small `◷`)
   - Trash: `#A890A0` ash-mauve (stash's hue, drained; glyph `◌`)
   Live counts sit in the label (`Stash 3`, `Trash 2`). History has no count (it is
   paged). A zero trash count still renders the tab, dim, so the slot never jumps.
2. **Caption** — one line, Config-Hub style, in the active accent:
   - Stash: `› Drafts you set aside. Pin, restore, or trash.`
   - History: `› Prompts you launched. Filter, load, or submit.`
   - Trash: `› Recently discarded drafts. Restore to stash or purge.`
   Compact fallbacks drop the second sentence. This slot never collapses.
3. **Body** — `ContentSwitcher` of three children. List | preview split at the
   existing 110-column stash threshold; preview hides in `-narrow`. **The preview
   pane is owned by the shell** and restyled per tab, so the right column does not
   jump when switching.
4. **Footer hints** — one lane, Artifacts separator `  ·  `, keys in the active
   accent, disabled keys dim. The whole line swaps with the tab. Never two hint
   rows.

Empty states occupy the list, not the whole overlay:

- Stash empty, trash empty: `Nothing stashed. Ctrl+S saves a draft. [ ] for history.`
- Stash empty, trash non-empty: `Nothing stashed. 2 in stash trash — ] to recover.`
- Trash empty: `Stash trash is empty. Discarded drafts land here.`
- History empty: keep today's quiet blank list + filter.

Do not close the overlay when the last live stash row is trashed. Show the empty
state. That is a behavior change from "picker closes when nothing remains" and it is
required once trash exists.

### 5.3 Entry points and tab routing

| Opened from | Initial tab | Extra |
| --- | --- | --- |
| `Ctrl+K` | History | Keep prompt-seed → `project:` filter |
| `,.` | History | Unscoped |
| `,>` | History | Cancelled visible (`Ctrl+X` state) |
| `,Ctrl+G` | History | Existing "edit newest" path; may still short-circuit before the overlay |
| `@` | Stash | Auto-restore if exactly one *live* row; else open. Empty live stash opens. |
| `,@`, chip, `Ctrl+G p` | Stash | Never auto-restore |
| Empty `Ctrl+S` | Stash | Same |
| After `d` | Stash | Stay; toast; do not jump |

Switching tabs remembers each child's highlight, filter text, and scroll. History's
loaded pages stay warm for the life of the overlay so `[` `]` is free.

### 5.4 Keymaps

Shell (always, including when History's filter is focused — same forwarding Config
Hub uses for `[` / `]`):

| Key | Action |
| --- | --- |
| `[` / `]` | Cycle sub-tabs |
| Click strip | Select tab |
| `Esc` / `q` | Close. Unconfirmed History filter is discarded. Already-trashed rows stay trashed. Pending `u` undo stack is dropped. |

**Stash** (today's picker, with A1/A2):

| Key | Action |
| --- | --- |
| `j` / `k` | Move |
| `1`–`9` / `0` | Restore that row (pin-aware pop/keep) and close |
| `space` | Toggle pin (persist immediately, as today) |
| `Tab` | Mark restore |
| `a` | Toggle restore-mark all |
| `d` | **Trash highlighted row immediately** |
| `D` | Trash all live rows after confirm |
| `u` | Undo last trash performed in this overlay |
| `Enter` | Restore marked set, or highlighted row if none marked |
| `Ctrl+D` / `Ctrl+U` | Preview half-page |

**History** (unchanged, plus shell `[` / `]`):

| Key | Action |
| --- | --- |
| type | Filter |
| `Enter` | Submit / launch |
| `Tab` | Load into the input |
| `Ctrl+G` | `$EDITOR` |
| `Ctrl+J` / `Ctrl+K` | Page / unload |
| `Ctrl+X` | Toggle cancelled |
| `Ctrl+Y` | Copy and close |

No `d` on History.

**Trash:**

| Key | Action |
| --- | --- |
| `j` / `k` | Move |
| `Enter` | **Untrash** to the live stash; stay on Trash; row vanishes |
| `Tab` | Load into the prompt bar and remove from trash (like a stash pop) |
| `1`–`9` / `0` | Same as `Tab` for that row |
| `d` | Permanently purge the highlighted row (confirm: one line, `y`/`Enter`) |
| `D` | Empty trash (confirm naming the count) |
| `u` | Undo last untrash *or* last purge performed in this overlay |
| `space` | No-op (pins are frozen) |

Footer copy must name the primary action in the tab's accent: Stash `enter restore`,
History `enter launch`, Trash `enter untrash`. That single word is the safety rail
against the `Enter` collision.

### 5.5 Stash-tab `d` semantics (the important behavior change)

Today: `d` marks `✗`, strikethrough, `Enter` commits, picker may stay open.

Recommended:

1. `d` calls core `trash_prompt_stash(ids, max_entries)` on a worker thread.
2. The row leaves the Stash list immediately (optimistic), highlight sticks to the
   next row, Trash tab count increments.
3. Toast: `Moved to stash trash` (singular/plural).
4. `u` reverses that core call (`restore_prompt_stash_trash`) while the overlay
   lives. One-deep undo is enough; a stack is nicer and cheap because N ≤ 200.
5. `D` opens the existing confirm modal (`ConfirmDeleteModal` family): "Move N
   stashed prompts to stash trash?" `y` / `Enter` confirms.

If `prompt_stash.trash_max_entries` is `0`, `d` is today's hard `pop` and the Trash
tab renders a caption `› Trash is disabled (prompt_stash.trash_max_entries: 0).`

Overflow: when trash grows past N, the oldest `trashed_at` rows are hard-deleted
inside the same locked rewrite. The toast for a trash that evicted says
`Moved to stash trash · oldest discard dropped` only when an eviction happened.

### 5.6 Persistence (sase-core)

**Same JSONL**, schema **2**.

```rust
pub struct PromptStashEntryWire {
    // existing fields...
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub trashed_at: Option<String>, // RFC 3339
}
```

Snapshot:

```rust
pub struct PromptStashSnapshotWire {
    pub schema_version: u32, // 2
    pub entries: Vec<PromptStashEntryWire>, // live only
    pub trash: Vec<PromptStashEntryWire>,   // trashed_at set, newest first
    pub stats: PromptStashStoreStatsWire,
}
```

New functions, all exclusive-lock + atomic rewrite:

- `trash_prompt_stash(path, ids, max_entries) -> PromptStashTrashOutcomeWire`
  — sets `trashed_at = now` on matching *live* rows; sorts trash by `trashed_at`
  desc; hard-deletes the tail beyond `max_entries`; `max_entries == 0` means pop
  (no trash). Unknown / already-trashed ids are ignored.
- `restore_prompt_stash_trash(path, ids) -> ...`
  — clears `trashed_at`, returns those rows to `entries`. Pins/cursors untouched.
- `purge_prompt_stash_trash(path, ids) -> ...`
  — hard-delete those trash rows. Empty `ids` is not "purge all"; the TUI passes
  every current trash id after confirm.
- `read_prompt_stash_snapshot` returns live + trash already split, so the TUI never
  filters in Python.

`pop_prompt_stash` remains hard-remove of *live* ids (restore-unpinned, and
`max_entries == 0`). It must not resurrect or scan-miss trash rows: read splits on
`trashed_at`, pop only the live set, write live+trash back.

Land the core commit and the sase pin (`sase-core-revision.txt`) together. Schema 1
Python will refuse schema 2; that is the existing ratchet, and it is the reason not
to sneak `trashed_at` onto schema 1.

Python: extend `prompt_stash_wire.py` / `prompt_stash_facade.py`; bindings next to
the existing `editor_content` prompt-stash functions; facade tests in
`tests/test_core_facade/test_prompt_stash.py`. TUI continues to use
`asyncio.to_thread` + the existing `_prompt_stash_write_lock`. Never touch the
JSONL on the UI thread (`tui_perf.md` rules 1 and 11).

### 5.7 Config

```yaml
prompt_stash:
  # Last-N discarded drafts kept in stash trash. 0 disables trash (hard delete).
  trash_max_entries: 20
```

- `src/sase/default_config.yml`
- `src/sase/config/sase.schema.json` (`integer`, `minimum: 0`, `maximum: 200`,
  default 20)
- `docs/configuration.md`
- Getter that clamps; pass the clamped value into every core trash call so a
  lowered N evicts on the next trash, not on a background sweeper.

This is not an `ace.*` field. Failed-launch stash and a future CLI must honor the
same cap.

Keymaps: add a focused scope `ace.keymaps.prompt_panel` only if Stash/History/Trash
bindings should be user-overridable. v1 can keep widget `BINDINGS` (today's stash
and history are not in a scope dataclass) and only document them. Do **not** add
`open_stash_trash` to leader maps in v1.

### 5.8 Glossary strands (implementation-time)

Three new strands under `sase/memory/glossary/`. Implementation uses
`/sase_memory_write`. Drafts:

**`prompt-stash.md`**

```yaml
---
keyword: Prompt Stash
aliases:
  - stash
---
```

The prompt stash is the per-user draft pile at `~/.sase/prompt_stash.jsonl`. Each
row is a prompt (or a bundled multi-pane prompt) the user set aside from sase's TUI
with `Ctrl+S` / `gs`, or that a failed launch preserved. It is not prompt history.
The live pile is the Stash sub-tab of the prompt panel; `@` restores a lone row and
opens that sub-tab when several remain. Pinned rows restore without leaving the
stash. Discarded rows move to [[glossary:stash-trash]].

**`stash-trash.md`**

```yaml
---
keyword: Stash Trash
aliases:
  - trash
---
```

Stash trash is the bounded recovery pile of prompt-stash rows the user discarded
with `d` on the Stash sub-tab. It lives in the same JSONL store, split by
`trashed_at`, and is the Trash sub-tab of the prompt panel. It keeps the last
`prompt_stash.trash_max_entries` discards (default 20); older rows are deleted.
Untrash returns a row to the prompt stash. Stash trash does not hold prompt-history
deletes.

**`prompt-history.md`** — add only if implementation wants the trio complete. The
term is widely used in docs and is currently missing from the glossary web. A short
strand pointing at `~/.sase/prompt_history/` and the History sub-tab would stop the
stash/history confusion the merge is meant to cure. Call this out as an optional
same-change glossary add, not a silent extra.

`trash` as an alias of stash trash is acceptable *inside this trio* because the
glossary is keyword-addressed and `glossary:trash` would otherwise be undefined.
Do not alias it on unrelated strands.

### 5.9 Badge, toasts, Help, demo

- Top-bar `stash: ≡ N` continues to count **live** rows only. A trash count on the
  chip would look like "you still have drafts." The Trash tab is the count.
- Toasts: `Moved to stash trash` / `Restored from stash trash` / `Purged from stash
  trash`, plus the existing restore wording. Stop saying "Deleted stashed prompt"
  when the row was trashed.
- Help modal + `docs/ace.md` + the prompt-history-stash demo tape
  (`demos/tapes/sase_ace_prompt_history_stash.tape`) need one scene that: opens
  History with `Ctrl+K`, `]` to Stash, `d` a row, `]` to Trash, `Enter` untrashes.
- `UpdatePinnedStashModal` is unchanged.

### 5.10 Implementation shape (suggested epic)

Internal sequence, one user-visible cutover at the end of the TUI phases:

1. **sase-core:** schema 2, split snapshot, `trash` / `restore` / `purge`, overflow,
   `pop` ignores trash, lock tests, concurrency test that append + trash do not drop
   rows.
2. **sase pin + facade + config + schema.**
3. **Prompt panel shell:** `PromptPanelModal` with strip, caption, shared preview,
   `[` / `]`, lazy children. History and Stash children are the current modals
   demoted to embedded panes (`-embedded` like Config Hub).
4. **Stash child:** `d`/`D`/`u` wired to core; empty-state; stay-open-on-last-trash.
5. **Trash child:** list, keymaps, confirms, lossless restore.
6. **Entry-point routing** and the empty-stash-opens change.
7. **Docs, glossary, Help, demo tape, visual snapshots / `just fix-tui-screenshots`.**

Do not load history shards when the overlay opens on Stash (Config Hub lazy
pattern). A stash snapshot read is required for tab counts; it is small and already
off-thread.

### 5.11 Tests that must exist

- Core: trash then restore round-trip preserves every field; overflow drops oldest
  `trashed_at`; `max_entries == 0` pops; `pop` of a live id leaves trash intact;
  concurrent append during trash does not drop either side (today's append+pop
  test, extended).
- Facade schema 2 rejection of schema 1 snapshots and the reverse.
- Modal: `d` removes from Stash list and increments Trash count without closing;
  `u` restores; `D` confirms; History `Enter` still submits; Stash `1` still
  restores a row when the History child is not focused; `[` from the History
  filter moves to Stash.
- App: empty live stash + non-empty trash opens the overlay; `@` with one live row
  still auto-restores; badge ignores trash.
- Visual snapshots of all three tabs, including Stash-empty-with-trash and
  Trash-empty, desktop and the 96-column `-narrow` path.

---

## 6. Risks

- **`Enter` means three different things.** Mitigation: caption + accented footer
  verb, never unify the actions, never number the tabs.
- **History filter swallows `[` / `]`.** Mitigation: the same parent-forwarding
  Config Hub already uses (`handle_config_hub_bracket_key`).
- **Schema 2 ratchet.** Mitigation: land core + sase pin in one cutover; do not
  write `trashed_at` that schema-1 rewrites would strip.
- **Optimistic TUI vs store failure.** Mitigation: on trash error, put the row
  back and toast; the existing pin/delete paths already notify on failure.
- **Large bundled prompts × 20.** JSONL can hold megabytes. v1 accepts that; a
  later `trash_max_bytes` is optional and not in the request.
- **Demo / screenshot drift.** The history+stash tape and any golden that matches
  `Select Prompt from History` will break on the new title/strip. Budget that in
  the docs phase, not as an afterthought.

---

## 7. What I would not do

- I would not keep mark-then-Enter for single-row stash delete once trash exists.
- I would not put this on a main tab.
- I would not send history deletes, or unpinned restores, into stash trash.
- I would not give the strip digit shortcuts.
- I would not auto-jump to Trash on `d`.
- I would not ship a beta flag for a complete overlay; I would slip to alternative
  B (Stash | Trash only) if the history merge is the thing that does not fit the
  epic, rather than ship a flag-gated half-panel.

---

## 8. Recommended solution

Build **one overlay prompt panel** with three sub-tabs — **Stash · History ·
Trash** — using `PanelTabStrip` + lazy `ContentSwitcher`, `[` / `]` to cycle, and
entry-point routing so `@` still opens Stash and `Ctrl+K` still opens History.

Keep each tab's interaction model. Make Stash `d` an immediate move into **stash
trash** (last `prompt_stash.trash_max_entries`, default 20, `0` = hard delete) with
in-panel `u` undo. Persist trash in the existing `sase-core` JSONL as schema 2
(`trashed_at` + split snapshot) under the same lock as live stash. Untrash with
`Enter` on Trash; load-into-bar with `Tab` / digits. History stays a launch log.

Add glossary strands for **prompt stash** (alias **stash**) and **stash trash**.
Stay an overlay. One user-visible cutover. That is the design.
