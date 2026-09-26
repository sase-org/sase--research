# Merging the Prompt Stash and Prompt History Panels, Adding Stash Trash

Research report — `mus` researcher, swarm of four.
Date: 2026-09-26. Scope: design research for merging the prompt stash panel
with the prompt history panel (sub-tabs), adding a third "stash trash"
sub-tab with bounded retention (`<N>`, default 20, configurable), new
keymaps, and glossary terms ("prompt stash"/"stash", "stash trash").

## 1. What exists today

### 1.1 Prompt stash (drafts, never submitted)

- **Store:** per-user JSONL pile at `~/.sase/prompt_stash.jsonl` via
  `prompt_stash_path()` ([src/sase/core/paths.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/core/paths.py)).
  **This is Rust core backend logic** under the repo's Rust boundary rule:
  `crates/sase_core/src/prompt_stash/store.rs` (append/pop/rewrite/pin,
  file-locked, atomic rewrites) and `wire.rs`
  (`PromptStashEntryWire`: `id`, `created_at`, `text`, `frontmatter`,
  `project`, `source`, `pane_index`, `pinned`, `cursor`) in the linked
  `sase-core` checkout, reached from Python through the thin facade
  [src/sase/core/prompt_stash_facade.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/core/prompt_stash_facade.py)
  and [src/sase/core/prompt_stash_wire.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/core/prompt_stash_wire.py).
  Any trash behavior that must survive concurrent TUI instances belongs in
  Rust, not in the modal.
- **Panel:** `StashedPromptsModal`
  ([src/sase/ace/tui/modals/stashed_prompts_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/ace/tui/modals/stashed_prompts_modal.py)):
  newest-first list, one-line preview + preview pane, pin (`space`, persisted
  immediately via `PinToggled`), restore (`tab`/`1-9`/`0`/`enter`, pinned =
  keep-in-stash, unpinned = pop), **delete is permanent today**: `d` marks one
  row, `D` marks all, `enter` confirms; partial deletes post
  `DeleteRequested` and the app calls `pop_prompt_stash` in
  `_prompt_bar_stash_restore.py` (delete-while-open supported). Opened via
  `Ctrl+G p` / global `@` (`open_prompt_stash` / `restore_prompt_stash` in
  `default_config.yml`).
- **Semantics:** a stash row is a canonical single-row bundle (one pane as
  `text`, or panes joined with `\n---\n`). Failed launches also stash
  best-effort (`record_failed_launch_prompt`).

### 1.2 Prompt history (submitted prompts, append-only record)

- **Store:** Python-only, sharded monthly JSON (`~/.sase/prompt_history/YYMM.json`)
  in [src/sase/history/prompt_store.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/history/prompt_store.py)
  + mutations in
  [src/sase/history/prompt_store_mutations.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/history/prompt_store_mutations.py):
  dedup-by-text, `last_used` bump, `cancelled` flag (never downgrades a success),
  5-word minimum, per-segment recording for multi-prompts, writer lock +
  atomic shard saves. Corrupt shards are masked for reads, hard-fail for writes.
- **Panel:** `PromptHistoryModal`
  ([src/sase/ace/tui/modals/prompt_history_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/ace/tui/modals/prompt_history_modal.py)
  + `_prompt_history_*` helpers): filter input, `project:`-aware query,
  `Ctrl+J`/`Ctrl+K` paging with unload, `Ctrl+G` edit, `Ctrl+X` cancelled
  toggle. Read-only: **no delete keymap exists** — history rows are never
  destroyed from the UI.
- **Key conceptual difference:** stash = mutable working set of *drafts* (pin,
  restore, delete are all meaningful); history = immutable *record* of what was
  sent (filter, re-run, inspect). Merging their chrome is fine; merging their
  data models would be a mistake.

### 1.3 Precedents worth copying

- **Merged-panel pattern:** `ConfigCenterModal`
  ([src/sase/ace/tui/modals/config_center_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/ace/tui/modals/config_center_modal.py))
  is home-first with lazily mounted panes, a `PanelTabStrip` + `ContentSwitcher`,
  numbered keys/`Tab`/`Shift+Tab` navigation, and pane-local sub-tabs on
  `]`/`[`. This is the established in-repo idiom for exactly this shape of UI.
- **Trash-with-grace precedent:** artifact retention config already has
  `keep_per_label` + `trash_grace_days: 14` (`default_config.yml`). A bounded,
  restorable trash is an accepted concept; only the stash lacks one.
- **Fail-open numeric config:** `get_ace_page_size()` in
  [src/sase/ace/config.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_47/src/sase/ace/config.py)
  is the template for the new `<N>` field: hand-edited `sase.yml` must never
  crash the TUI; invalid/missing values fall back to the default.
- **Glossary:** memory web `sase/memory/glossary/` — one strand file per term
  with `keyword:` frontmatter (e.g. `stitch.md`, `proc.md`). New terms
  "prompt stash (stash)" and "stash trash" each get a strand; the descriptor
  roster line is generated. Neither term exists yet (verified: no matches).

## 2. Critique of the plan

**Is it a good idea? Yes, with adjustments.** The core insight — `d` today is a
surprising permanent destroy with no undo, on drafts the user explicitly cared
enough to stash — is right, and a bounded trash fixes the real footgun. The
merge is defensible: both panels answer "get me back a prompt I wrote," and two
near-identical pickers (`@`/`.`-adjacent keymaps, similar list+preview layout)
are harder to learn than one. But the request as written has five weak spots:

1. **Merge ≠ unify.** Stash rows (bundles with pins, project chips, restore
   semantics) and history rows (deduped submitted texts with filters and paging)
   need different list code, different preview panes, and different keymaps.
   The merged panel must be a *shell with three sub-tabs that host the existing
   panes*, not a rewrite of either pane. Otherwise this becomes a risky
   refactor of two stable, well-tested modals (there are ~15 stash/history test
   files) for no user-visible gain.
2. **"Archived/trashed" conflates two things.** Archive (intentional,
   long-lived, user-curated cold storage) and trash (accidental-delete safety
   net with automatic expiry) have opposite retention and opposite UX. The `d`
   flow needs *trash*, not archive. Do not build archive semantics (no expiry,
   manual curation) under the trash name — that guarantees a second feature
   request later. Recommendation: build trash now; leave archive as an explicit
   non-goal.
3. **N=20 with silent permanent deletion re-creates the footgun at row 21.**
   Eviction must be visible: a hint-line count ("Trash 20/20 — oldest evicted"),
   and ideally eviction only of the *oldest* trashed row. Also `0` should mean
   "trash disabled, delete permanently" (escape hatch for the paranoid), and
   negative/garbage config must fail open to 20.
4. **Pin + trash interaction is unspecified.** Pinned rows are templates the
   user explicitly kept; `d` on a pinned row should either refuse (toast "unpin
   first") or require the `D`-style explicitness. Silently trashing a pinned
   template violates the pin promise. Recommend: `d` on pinned = toast + no-op
   (or unpin-then-trash behind a confirm); trash rows lose their pin display
   but *retain* the flag so restore returns them pinned.
5. **Where trash lives is the biggest design decision, and the request punts
   it.** Options: (a) separate `prompt_trash.jsonl` store; (b) `trashed: bool +
   trashed_at` fields on stash rows in the same file. (b) keeps one lock, one
   atomic rewrite path, and makes "restore" trivial — but every existing
   reader (`read_prompt_stash_snapshot`, badge counts, single-restore `@`
   fast path) must filter trashed rows, and the Rust wire schema version must
   bump. (a) isolates the blast radius (existing readers untouched) at the cost
   of a second store + cross-store move transaction. I recommend (b) — the
   filter is one predicate in two or three call sites, the move is atomic under
   the existing exclusive lock, and eviction-by-N is a cheap tail-drop in the
   same write — but it *must* be implemented in `sase-core` (Rust), with the
   `sase-core-revision.txt` pin moved, per the Rust boundary rule. A Python-only
   trash racing two TUI instances against a Rust-owned file will corrupt or
   resurrect rows.

## 3. Recommended design

### 3.1 The merged panel: "Prompts" shell, three sub-tabs

- One modal, e.g. `PromptLibraryModal`, titled **Prompts**, with a tab strip:
  `1 Stash · 2 History · 3 Trash`. Each sub-tab hosts the existing pane code
  largely as-is (`StashedPromptsModal` internals → Stash pane; history modal →
  History pane; Trash pane reuses the stash row renderer + preview with its own
  keymap). Follow `ConfigCenterModal`: lazy-mount panes, cache per-tab
  selection, `Tab`/`Shift+Tab` or `]`/`[` to cycle, `1/2/3` to jump, `Esc`/`q`
  to close. Preserve existing entry points as deep links: `Ctrl+G p` opens
  Prompts-on-Stash, `.` (history) opens Prompts-on-History, `@` keeps its
  single-entry fast-restore behavior and only opens the panel (on Stash) when
  there are multiple rows.
- **Beauty details that make it feel like one panel, not three stapled
  together:** one shared header (counts: `Stash 7 · History 1.2k · Trash 3/20`),
  one shared preview-pane component and row typography, one hint-line region
  that swaps per tab, and a consistent empty-state illustration string per tab
  ("Stash is empty — stash the bar with `Ctrl+G s`", "No trashed prompts —
  deleted stash rows land here", etc.). Trash rows render dimmed with a
  relative "trashed 3d ago" age instead of the created age.

### 3.2 Stash trash semantics

- `d`/`D` on the **Stash** tab no longer pops rows; it *trashes* them
  (Rust: set `trashed=true`, `trashed_at=now`; ordering: trashed rows sort
  newest-trashed-first in the Trash tab). Toast confirms with undo affordance:
  `"Trashed 2 prompts — open Trash (3) to restore"`.
- **Trash** tab keymaps (mirroring stash idioms so they transfer):
  - `r` or `tab` — restore (back to Stash, unpinned-entry pops semantics:
    restore as live stash row; retain original `pinned` flag, `created_at`,
    `project`, `cursor` so nothing is lost round-trip).
  - `d` — delete permanently (the true destroy, now explicit and two steps
    removed from the original `d`); `D` — empty trash (confirm via `enter`
    when marked, same in-place pattern as today's `DeleteRequested`).
  - `1-9`/`0` — restore by index (parity with stash restore numbers).
  - `enter` with restore marks — restore all marked; with only delete marks —
    permanent-delete in place; nothing marked — restore highlighted row.
  - Keep `j/k`, preview scroll (`Ctrl+D`/`Ctrl+U`), `Esc`/`q` identical.
- **Bounded retention:** Trash keeps the last `<N>` trashed rows by
  `trashed_at`; the `(N+1)`-th trash permanently evicts the oldest. Eviction
  happens inside the same Rust write as the trash-insert (atomic, no
  Python-side race). The Trash title always shows `Trash (k/N)` so eviction is
  never a surprise. `N=0` = trash disabled (direct permanent delete, today's
  behavior — document it).
- **Config:** new field, e.g. `ace.prompt_stash_trash_limit` (near
  `ace.page_size`), default `20`, read through a `get_ace_*` accessor in
  `src/sase/ace/config.py` with the `get_ace_page_size` fail-open pattern
  (`type(value) is int and value >= 0`, else 20). Document in
  `default_config.yml` with a comment explaining `0` = disabled. Note: because
  enforcement lives in Rust, the Python layer passes the limit *per call*
  (parameter, not Rust-read config — the core store must not parse sase.yml),
  or a dedicated `trash_prompt_stash(ids, limit)` binding. Prefer the explicit
  parameter; it keeps the core hermetic and testable.
- **What trash must not touch:** history rows (no delete there, unchanged),
  badge counts (trashed rows excluded from the top-bar stash badge), `@`
  single-restore (ignores trashed rows), failed-launch stash path (new rows
  always land live).

### 3.3 Glossary

Add two strands (author new files, never edit the descriptor by hand beyond the
generated roster step):

- `sase/memory/glossary/prompt-stash.md` — `keyword: Prompt Stash`, alias
  `stash`: the per-user pile of stashed prompt drafts (`~/.sase/prompt_stash.jsonl`),
  restored/pinned/deleted from the Stash sub-tab of the Prompts panel.
- `sase/memory/glossary/stash-trash.md` — `keyword: Stash Trash`: the bounded
  (default last 20, `ace.prompt_stash_trash_limit`), restorable holding area
  for stash rows deleted with `d`; eviction past the limit is permanent.

### 3.4 Build order (thin vertical slices)

1. Rust: `trashed`/`trashed_at` wire fields (schema v2) + `trash_*` store ops
   with limit enforcement + parity tests; bump Python wire mirror + facade;
   move `sase-core-revision.txt`.
2. Python: `ace.prompt_stash_trash_limit` config + accessor; reroute Stash-tab
   `d`/`D` through trash ops; badge/fast-path filters.
3. TUI: Trash sub-tab pane + keymaps; then the Prompts shell hosting all three;
   repoint `Ctrl+G p`/`.`/`@` as deep links. Keep old modal names as aliases
   until tests migrate.
4. Glossary strands + docs; empty-state strings and hint lines last (they're
   the visible "beautiful" layer — write them once the flows are frozen).

## 4. Recommended solution (TL;DR)

**Do it, but as a shell-not-rewrite:** build a `Prompts` panel with Stash /
History / Trash sub-tabs on the `ConfigCenterModal` pattern, reusing both
existing panes; implement trash as `trashed` flags in the Rust stash store
(schema bump) with atomic limit enforcement (default 20, `ace.prompt_stash_trash_limit`,
`0` = disabled, fail-open); give Trash restore/permanent-delete/empty keymaps
that mirror the Stash tab; refuse-or-confirm `d` on pinned rows; keep history
read-only and the `@` fast path trash-blind. Explicitly *don't* build archive
semantics, don't merge the data models, and don't implement trash in Python
against a Rust-owned file. That yields the intuitive part (one place for old
prompts, undo for fat-finger `d`), the reliable part (atomic cross-instance
moves, no silent loss before row 21 thanks to the visible `k/N` count), and
then the beauty part (one header, one preview language, three calm empty
states) almost falls out.
