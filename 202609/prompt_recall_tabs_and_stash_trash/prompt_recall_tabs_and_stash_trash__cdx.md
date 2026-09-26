# Prompt Library and Stash Trash: design research

**Researcher:** cdx  
**Date:** 2026-09-26  
**Scope:** Merge the prompt-history and prompt-stash pickers behind sub-tabs, add a
bounded trash for deleted stash entries, and recommend an implementation that fits
SASE's current TUI and Rust-core boundaries.

## Executive conclusion

This is a good product idea. History and stash are already two answers to the same
user question—“where is the prompt I want?”—and their separate modal frames create
unnecessary navigation and duplicate preview UI. A third recovery surface makes `d`
safer without turning the stash into a permanent archive.

The important qualification is that these collections must be merged at the
**presentation and navigation layer, not into one data model**. Prompt history is a
large, pageable record of launched prompts. The prompt stash is a mutable pile of
unlaunched drafts, some of which are pinned or contain multiple prompt panes. Stash
trash is a small, bounded recovery queue. Flattening those into one list or storage
schema would blur their meanings and weaken the useful guarantees each already has.

I recommend a new full-size **Prompts** modal with a clickable `PanelTabStrip` and
three cached child panes in this order:

> **History** │ **Stash** │ **Trash**

Existing entry points should select the relevant initial tab, but users can switch
without leaving the modal. The shared frame should standardize the split list/preview
geometry while allowing each child to retain its own controls, focus, filters, and
lazy-loading behavior.

For durability, keep active and trashed stash records in one lock domain and implement
their lifecycle in `sase_core`. A stash deletion should atomically change an active
record into a tagged trash record, assign `trashed_at`, prune the oldest trash records
past the configured limit, and return authoritative active/trash snapshots. Do not
implement this as a Python `pop` followed by an append to a second file: a crash between
those operations can lose the prompt, and concurrent SASE processes can interleave
them.

## What exists today

### Prompt history

`PromptHistoryModal` is a nearly full-screen modal with:

- off-thread identity and page loading;
- bounded pages controlled by `ace.page_size` (default 100);
- a project-aware text filter;
- a compact table plus rich preview and metadata panel;
- distinct submit, edit, load, copy, cancelled-visibility, load-more, and unload
  actions.

The implementation is already decomposed into list-state, interaction, row-rendering,
preview, and model modules under `src/sase/ace/tui/modals/_prompt_history_*`. It should
be refactored into a child pane rather than rewritten.

### Prompt stash

`StashedPromptsModal` is a smaller split-pane picker. It sorts drafts newest-first,
supports bundle rows, remembers a saved pane/cursor, debounces preview rendering,
collapses the preview on narrow terminals, and supports:

- direct restore by `1`–`9`/`0`;
- multi-row restore marks (`Tab` and `a`);
- persistent pinning (`Space`);
- staged row/all deletion (`d`/`D`, applied by `Enter`).

Stash persistence is already correctly owned by the linked `sase-core` repository.
`prompt_stash.jsonl` is protected by a bounded shared/exclusive lock, writes are
tempfile-and-rename atomic, and Python calls it through thin `sase_core_rs` facades.
That is the right foundation for trash lifecycle operations.

### The most important existing weakness

The current partial-delete path is visually optimistic. The modal posts
`DeleteRequested`, immediately removes the rows from its in-memory list, and only then
does the app asynchronously call `pop_prompt_stash`. If persistence fails, the user
sees an error toast but the still-open picker no longer matches disk. The new feature
is an opportunity to repair this: keep marks visible (optionally with a busy marker),
perform one off-thread core mutation, and repaint both panes and counts only from the
returned snapshot. On failure, preserve rows and marks so retry is safe and obvious.

## Product critique and requirement adjustments

### What is strong about the proposal

1. **The information architecture is coherent.** History, reusable drafts, and
   recently discarded drafts belong in one retrieval surface.
2. **Soft deletion matches the cost of the object.** Prompts can represent substantial
   thought and are easy to delete accidentally from a keyboard-driven picker.
3. **A count bound is better than an age-only policy.** It is predictable, cheap to
   render, and avoids creating another unbounded archive.
4. **A configuration default of 20 is reasonable.** It is enough to undo several
   cleanup sessions while keeping startup and visual density trivial.

### Adjustments I recommend

1. **Call it trash, not archive.** An archive implies intentional, durable retention.
   This collection automatically evicts entries and permits permanent deletion. Use
   **Trash** in the UI and **Stash Trash** in the glossary. Documentation may say
   “recently deleted,” but should not promise archival durability.
2. **Count deleted stash rows, not individual prompt segments.** A stash row is the
   unit selected by `d`; bundle rows must move, restore, and expire atomically. Thus
   `N=20` means 20 stash entries/bundles, even if one bundle contains several prompt
   panes.
3. **Allow a limit of zero.** `ace.prompt_stash.trash_limit: 0` should preserve the old
   permanent-delete behavior. This is useful for privacy-sensitive users and makes the
   setting complete rather than special-casing disablement elsewhere.
4. **Preserve pin and provenance metadata while trashed.** A restored formerly pinned
   draft should still be pinned. The pin does not exempt a trash record from the limit;
   otherwise the bound can be violated.
5. **Order and evict by deletion time, not creation time.** The tab represents recent
   deletions. Preserve `created_at` for provenance and add `trashed_at` for lifecycle
   ordering and display.
6. **Restore from Trash back to Stash, not directly into the editor.** This follows
   normal recycle-bin semantics and prevents an undo operation from unexpectedly
   replacing or appending to a live prompt stack. The user can then restore/load it
   from the Stash tab in the usual way.
7. **Make the merged modal useful even when the initial tab is empty.** `,@` and an
   empty-pane `Ctrl+S` should open the Stash tab with a polished empty state rather
   than toast and abort; History and Trash remain one key away. Preserve the global
   bare-`@` fast path that directly restores one stash entry.
8. **Move both `d` and `D` to trash.** The request names `d`, but retaining permanent
   delete-all on `D` in the Stash tab would be surprising and dangerous. Permanent
   deletion belongs only in Trash.

## Recommended interaction design

### Shared shell

Use a new `PromptLibraryModal` (or `PromptsModal`; “library” need not appear in the
user-facing title) containing:

1. a simple title, **Prompts**;
2. the existing reusable `PanelTabStrip`, with a distinct accent for each tab;
3. a `ContentSwitcher` holding cached child panes;
4. a shared, stable modal footprint matching the current history modal (approximately
   98% × 96%);
5. per-pane footer hints, rather than one union of every shortcut.

The strip should show live bounded counts where they are cheap and authoritative:
`Stash 5` and `Trash 2`. Do not force an expensive total-history count; the History
pane's existing “visible / loaded / total” label is sufficient. Suggested visual
accents are cyan/teal for History, orchid/pink for Stash (matching the existing stash
indicator), and amber for Trash. Reserve red for rows explicitly marked for permanent
deletion.

The two-column list/preview split should stay visually stationary across tabs. History
can retain its table headers and filter above the split; Stash and Trash can reuse the
current syntax-highlighted stash preview. On narrow terminals, collapse the preview as
the stash modal already does, but retain the tab strip, count, list, and complete footer
hints.

### Sub-tab navigation

Use the established SASE sub-tab convention:

- `[` / `]`: previous/next sub-tab;
- mouse click on the strip;
- preserve the selected tab, highlight, scroll position, filter, loaded pages, and
  unconfirmed marks when switching.

Do not number these sub-tabs: Stash already uses `1`–`9`/`0` for direct row restore.
The history filter should forward `[`/`]` to the host exactly as other nested panes do.

Opening shortcuts retain their meanings but select an initial tab:

- `Ctrl+K` from the prompt bar and `,.` globally → History;
- `Ctrl+G p`, empty-pane `Ctrl+S`, `,@`, or stash-indicator click → Stash;
- add configurable leader action `prompt_trash`, suggested default `,T` → Trash;
- add command-palette actions for all three initial-tab choices.

All paths should enter one app-level dispatcher so switching tabs does not leave the
modal with an incompatible callback. From a live prompt bar, History and Stash actions
retain that bar/pane as their origin. From the main TUI, selecting a History action
should lazily establish the same home/MRU launch context that `,.` uses today; selecting
a Stash action should retain its current home-bar behavior.

### Tab-specific keys

History should keep its current keys unchanged.

Stash should keep its current keys except for clearer copy:

| Key | Stash action |
| --- | --- |
| `1`–`9`, `0` | Restore that row to the prompt bar (pin-aware) |
| `Tab` | Toggle restore mark |
| `Space` | Toggle persistent pin |
| `a` | Toggle restore marks for all |
| `d` | Toggle “move to Trash” mark |
| `D` | Mark all for Trash |
| `Enter` | Apply marks; with no marks, restore highlighted row |
| `Ctrl+D` / `Ctrl+U` | Scroll preview |
| `Esc` / `q` | Close and discard unconfirmed marks |

The footer and marker vocabulary should say **trash**, never **delete**, on this tab.

Trash should mirror the learned multi-select grammar without exposing pin editing:

| Key | Trash action |
| --- | --- |
| `1`–`9`, `0` | Restore that row to Stash |
| `Tab` | Toggle restore-to-Stash mark |
| `a` | Toggle restore marks for all |
| `d` | Toggle permanent-delete mark |
| `D` | Mark all for permanent deletion |
| `Enter` | Apply marks; with no marks, restore highlighted row |
| `Ctrl+Y` | Copy highlighted prompt without changing lifecycle state |
| `Ctrl+D` / `Ctrl+U` | Scroll preview |
| `Esc` / `q` | Close and discard unconfirmed marks |

`D` followed by `Enter` should open a compact destructive confirmation when it would
purge more than one row. A single `d` is already a two-step mark/confirm gesture, but
its footer must turn red and explicitly say “Enter: permanently delete marked.”

After a successful Stash deletion, switch to neither tab automatically. Remove the row
from Stash, increment the Trash count, preserve the nearest highlight, and toast
“Moved N to Trash” (plus “· permanently removed M oldest” when retention pruned rows).
This keeps bulk cleanup fluid while making retention visible rather than silent.

### Empty, loading, and error states

- **Empty Stash:** “No saved drafts. Press Ctrl+S in the prompt bar to stash one.”
- **Empty Trash:** “Trash is empty. Prompts removed from Stash appear here.”
- **Limit zero:** “Trash is disabled by `ace.prompt_stash.trash_limit: 0`.”
- **Loading:** render a disabled row immediately; never delay modal paint.
- **Mutation error:** keep the row and its marks, show a specific error toast, and
  leave focus in place so Enter retries.

## Storage and backend design

### Configuration

Add this bundled default and JSON-schema field:

```yaml
ace:
  prompt_stash:
    # Maximum recently deleted stash rows retained for recovery; 0 disables trash.
    trash_limit: 20
```

Expose a defensive accessor such as `get_prompt_stash_trash_limit()` that accepts only
real integers `>= 0` and falls back to 20 for malformed or unloadable config. Update
`src/sase/default_config.yml`, the config schema, configuration documentation, and
tests together. Because it is a configuration value and the change includes new modal
actions, update the default keymap configuration and keymap documentation in the same
change.

### One lifecycle store, one lock, one atomic rewrite

Shared storage behavior belongs in `sase_core`, not the TUI. The safest representation
is one physical `prompt_stash.jsonl` lock domain containing two logical record kinds:

```json
{"id":"...","created_at":"...","text":"..."}
{"record_type":"trash","trashed_at":"...","entry":{"id":"...","created_at":"...","text":"..."}}
```

Existing active rows remain byte-shape compatible. A tagged trash envelope is
preferable to merely adding `trashed_at` to the existing entry: an older reader that
ignores unknown fields could otherwise surface a trashed prompt as active. An older
implementation will treat the envelope as an invalid row and skip it. Downgrade writes
may discard trash, so this compatibility behavior should be documented, but they will
not resurrect deleted drafts into the active stash.

The new core parser should retain active rows, trash envelopes, and parse statistics as
separate internal values. Existing APIs must become lifecycle-aware:

- `read_prompt_stash_snapshot` returns active rows only;
- `append_prompt_stash` appends active rows and preserves trash;
- `pop_prompt_stash` remains the hard-removal primitive used when an unpinned stash is
  restored to the prompt bar, and preserves unrelated trash envelopes;
- `set_prompt_stash_pinned` and `rewrite_prompt_stash` operate on active rows and
  preserve trash exactly.

Add explicit APIs and typed outcomes for:

- `read_prompt_stash_trash_snapshot` (bounded trash rows, newest deletion first);
- `trash_prompt_stash(path, ids, trashed_at, limit)`;
- `restore_prompt_stash_trash(path, ids)`;
- `purge_prompt_stash_trash(path, ids)`;
- a named reconciliation operation that enforces a newly reduced limit before the
  Trash tab first paints.

Every mutation must acquire the existing exclusive store lock, read once, transform
both logical collections, write one replacement file, fsync/rename, and return a
single outcome containing the active snapshot, trash snapshot, changed IDs, and
retention-purged IDs. Sort eviction candidates by `(trashed_at, created_at, id)` and
discard the oldest until `len(trash) <= limit`. Reapplying the same request should be
safe: unknown/already-transitioned IDs are no-ops.

This design is more reliable than two files and two renames, and it prevents Python or
the UI from reimplementing retention. The Python layer should add only wire dataclasses,
schema conversion, a thin binding facade, and user-facing error translation. After the
core commit lands, advance `sase-core-revision.txt` past it as required by the project
boundary.

### Timestamp and limit semantics

- `trashed_at` is generated once at the mutation boundary and stored in UTC/ISO form.
- Re-deleting a restored row gets a new `trashed_at` and becomes newest.
- Restoring preserves `id`, `created_at`, text, frontmatter, project, source, cursor,
  pane order, and pin state.
- Changing the limit downward is enforced on the next explicit reconciliation or
  trash mutation; opening Trash performs that reconciliation off-thread before showing
  rows, so the UI never advertises more than the configured maximum.
- Automatic retention is not undoable. The mutation outcome must report its purge
  count so the UI can say what happened.

## TUI architecture

Refactor toward composition:

```text
PromptLibraryModal
├── PanelTabStrip
└── ContentSwitcher
    ├── PromptHistoryPane
    ├── PromptStashPane
    └── PromptTrashPane
```

`PromptHistoryPane` should reuse the current history mixins and models.
`PromptStashPane` should reuse `prompt_stash_row.py`, `PromptStashPreviewPane`, bundle
segmentation, debounced preview, and selection behavior. `PromptTrashPane` should reuse
the same row/preview components but render deletion age and lifecycle actions instead
of pin actions. Avoid a giant modal class with tab conditionals; the shell owns only
navigation, lazy child construction, result dispatch, counts, and common responsive
geometry.

Each pane should load lazily on first activation and remain mounted thereafter.
History pages and filters, stash/trash highlight identities, and pending marks survive
tab switches. Workers must re-check the active pane and selected stable ID after every
`await`; an inactive child may update its cache and count but must not steal focus or
paint over the visible tab. Keep disk I/O in `asyncio.to_thread`/thread workers and
detail rendering behind the existing 150 ms debouncer. Cancel debouncers and pane
workers on unmount.

For mutations, share one app-level async stash-write lock, set a small pane-local busy
state, call one Rust transaction off-thread, then update both cached child panes and the
top-bar stash indicator from the returned snapshots. Do not independently reread after
success unless the backend explicitly reports a stale/conflict outcome.

## Glossary additions

Add these through the SASE memory-write workflow during implementation:

### Prompt Stash

> **Prompt Stash** (alias **stash**) — The per-user persistent collection of
> unsubmitted prompt drafts captured from the prompt bar. One stash entry is the
> atomic restore unit and may contain one prompt pane or an ordered bundle, plus its
> frontmatter, originating project, pin state, and optional editor cursor. It is
> distinct from Prompt History, which records submitted launches.

### Stash Trash

> **Stash Trash** — The bounded per-user recovery collection for entries removed from
> the Prompt Stash. A trashed entry preserves the complete stash entry and records when
> it was trashed; restoring returns it to the Prompt Stash. The oldest trashed entries
> are permanently removed when the configured trash limit is exceeded, so Stash Trash
> is not an archive.

These definitions should link to each other and to the existing relevant prompt/history
concepts if/when those glossary strands exist. “Archive” should not be added as an
alias.

## Verification strategy

### `sase_core`

- legacy active-row parsing and tagged trash-envelope parsing;
- atomic active → trash → active round trip with every field preserved;
- `limit=20`, `limit=1`, and `limit=0` retention behavior;
- deterministic tie handling and eviction by `trashed_at`;
- multi-ID transitions, unknown IDs, and idempotent retries;
- existing pop/pin/rewrite operations preserve trash envelopes;
- malformed lines remain accounted for and cannot become active records;
- lock contention and concurrent append/trash/restore tests;
- PyO3 round-trip tests and explicit binding registration.

### Python facade and configuration

- wire-schema mismatch and unknown-field behavior;
- lock-timeout translation;
- limit accessor defaults, zero, positive values, booleans, negative values, and
  malformed config;
- bundled default and JSON-schema agreement.

### TUI

- every legacy shortcut opens the merged modal on the correct initial tab;
- sub-tab clicks and `[`/`]` preserve per-pane state and focus;
- history loading remains pump-free and page/filter behavior is unchanged;
- stash delete success moves rows and refreshes both counts from the returned snapshot;
- failed mutation leaves rows/marks visible;
- trash restore, single purge, purge-all confirmation, retention toast, and `limit=0`;
- main-TUI versus prompt-bar result dispatch;
- empty/loading/error states;
- wide and narrow visual snapshots for all three tabs, both themes, marked destructive
  rows, bundle preview, and count changes.

Run focused tests while iterating, then the normal repository verification for each
changed repository. Add PNG snapshots for the merged frame rather than retaining
separate history/stash golden contracts that no longer represent user-visible screens.

## Suggested implementation sequence

1. **Core lifecycle:** tagged trash records, atomic transition/restore/purge/retention
   APIs, bindings, and tests in `sase-core`.
2. **SASE plumbing:** Python wires/facade, config accessor/default/schema/docs, and the
   core revision pin.
3. **Modal composition:** extract History and Stash child panes, add the shared shell
   and tab navigation without changing action semantics.
4. **Trash UX:** add the Trash child, authoritative mutation refresh, retention toasts,
   direct entry action, keymaps, command palette entries, and empty/error states.
5. **Polish:** glossary strands, docs, help text, performance checks, and visual
   snapshots.

This order makes the durable transaction available before any UI can pretend a row was
saved to trash, and it allows the panel refactor to be reviewed separately from the
lifecycle behavior.

## Recommended solution

Build one polished **Prompts** modal with cached **History**, **Stash**, and **Trash**
sub-tabs, opened on the tab implied by the user's existing shortcut. Preserve each
collection's existing semantics and state rather than combining their lists. Change
Stash `d`/`D` into move-to-Trash actions; make Trash restoration return the complete
entry to Stash; keep manual permanent deletion exclusive to Trash and visibly
destructive.

Add `ace.prompt_stash.trash_limit` with default `20` and valid range `>= 0`, where zero
disables recovery. Interpret the limit as stash rows/bundles, preserve pin/provenance,
and order/evict by `trashed_at`.

Implement active/trash lifecycle as tagged logical records in the existing
`prompt_stash.jsonl` lock domain, with Rust-owned atomic mutations and retention. Have
the TUI update only from returned authoritative snapshots, fixing the current
optimistic-delete inconsistency. This yields the intuitive merged experience the
request is aiming for without sacrificing the distinctions, concurrency safety, or
performance properties of the existing systems.
