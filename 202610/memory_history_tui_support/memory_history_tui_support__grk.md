# Time-aware Memory catalog: excellent TUI support for memory file history

_Researcher `grk` · 2026-10-02 · Independent design research for TUI support of the
landed `sase-1dr` memory-history axis._

## Bottom line

The pager already *is* the history reader, and it is excellent after `sase-1dr` plus
`sase-1ef`. The TUI's job is not to grow a second pager. The TUI's job is to make
history **discoverable, glanceable, and reachable from the places a human already
lives**: the Memory panel catalog and the Agents tab.

Today the TUI only *launches* the pager. The Memory panel has `H` / `C` and a buried
History property-grid row. That is a front door, not support. A user who never presses
`H` never sees a version pill, a life strip, or a past body. The Agents tab, which is
where you debug "what did this agent see?", does not consume history at all.

**Recommended solution:** keep the pager as the only full reader, and make the Memory
panel a **time-aware catalog** that speaks the pager's vocabulary. Progressive
disclosure:

1. **Rail** — glance (class glyph, age, dirty, promotion).
2. **Card** — peek (version pill, compact life strip, `( ) { }` / `=` on the body).
3. **`H`** — deep read (full pager at the pin you are already looking at).
4. **`C`** — review (in-panel changes mode, then pager for a single changeset).
5. **Agents tab** — as-seen (open `AGENTS.md` and audited reads at the snapshot the
   agent actually loaded).

Do not add a Memory tab. Do not embed `PagerScreen` in the panel while `sase-1es`
(pager virtualization) and `sase-1eu` (three-pane splits) are in flight. Reuse
`VersionMoment`, `render_sparkline`, `history_palette_from_theme`, and
`HistoryService`. Absorb ready tasks `sase-1en` (shared pills), `sase-1e5` (as-seen),
and `sase-1e6` (review watermark) as phases of this work.

The detailed recommendation, mockups, and a five-phase epic sketch are at the end.

---

## 1. What landed, and what the TUI actually has

Epic `sase-1dr` (closed) shipped a complete history stack:

| Layer | Owner | Role |
| --- | --- | --- |
| Git | the checkout | the only store |
| `memory_history` index | sase-core | lineage, classification, provenance, cache |
| `HistoryService` | Python | scopes, thread-safe queries, CLI |
| Pager time axis | `src/sase/pager/` | read, diff, picker, feed, pills, band |
| Memory panel | `src/sase/ace/tui/modals/memory_pane_history.py` | `H`, `C`, History row |

The original research (`research:202609/memory_and_instruction_file_history`) and the
epic plan (`plan:202609/memory_history.md`) were explicit:

- The pager is the **single rendering surface** for reading one document through time.
- The Memory panel is a **front door**: `H` opens the pager at now, `C` opens the feed,
  and the card gets a History row loaded after paint.
- A dedicated Memory-panel history tab was considered and **rejected**.
- "Memory as seen by agent" was deferred (`sase-1e5`).

Phase `sase-1dr.11` implemented exactly that front door. `sase-1ef` then made the
*pager* tell you which version you are reading (`● NOW`, `◌ NOW · uncommitted`,
`⟲ PAST · vK of N`, `✖ DELETED`). It explicitly left the CLI text output and the
Memory panel History row on the old vocabulary (`sase-1en`).

So the user's instinct is right in spirit: **the only place you can actually read
history is the pager.** The TUI knows history exists; it does not yet *support* it.

### 1.1 The Memory panel today

The panel is a modal catalog (`gm` / `Ctrl+G m`), not a first-class ACE tab. It is a
reusable `MemoryPane` widget hosted by `MemoryPanel`, with an explicit comment that a
later Config hub can remount it. History is a mixin, not the product.

**`H` (`open_history`).** Builds a history `PagerDocument` off-thread via
`build_history_document(..., initial_revision="now", view="read")` and
`push_screen(PagerScreen(...))`. Always now, always read view. The Memory panel
disappears under a full-screen pager. `q` returns you to the catalog.

**`C` (`open_changes`).** Builds the cross-file feed for **every** scope in the ring,
not the current scope, and pushes another `PagerScreen`.

**History row.** A property-grid line under Type / Parent / Children:

```text
History   ▁▂▁▅▁▃▇▂  9 versions · changed 7d ago · sase-1bc.12
```

Loaded off-thread after paint, cached by `(scope, selector, tip)`, cancelled on
selection change. Web descriptor rows omit it. Failed loads freeze on dim `…` forever
(the miss is remembered so workers stop respawning). Untracked is amber. The row does
not use `VersionMoment` pills, does not mark dirty vs clean now, and does not carry a
playhead.

The dark-theme golden (`memory_panel_history_dark_120x40`) shows the practical result:
the sparkline collapses toward a filled cell, the count/age string sits in the metadata
stack, and the body is always the live file. The footer does advertise
`H history · C changes`, so the keys are not secret — they are just a launch.

**`Z` (`open_viewer`).** Does **not** open the pager. It hands the path to the artifact
file viewer (`open_artifact_path` → tmux pane or suspended rich viewer). The original
design said "Z keeps working, and its viewer gets the time axis automatically." That
assumption was wrong: the artifact viewer is a different surface. Only `PagerScreen`
discovers `sase_pager_history` providers.

**`?` help.** `MemoryPanelHelpModal` lists `H` as "History" and `C` as "Changes" via
`_MEMORY_BINDING_META`. No Time group, no destination footer, no pill legend.

**`docs/ace.md` Memory panel section.** Does not mention `H`, `C`, the History row, or
memory history at all. `docs/memory.md` and `docs/configuration.md` do. A TUI-native
reader of the ACE guide never learns the feature exists.

### 1.2 Where else the TUI could show history, and does not

| Surface | Today | History? |
| --- | --- | --- |
| Memory panel card body | live Markdown of now | no |
| Memory panel rail | stem + description | no recency |
| Agents `SASE CONTEXT / MEMORY` | audited-read list; numbered hint pages a **current** report | no version pin |
| Agents `V` metadata pager | pager, so memory paths in the document *can* attach the axis after paint | incidental, not as-seen |
| Artifacts Files `( )` | artifact-file versions | a different version axis |
| Instruction files | not in the Memory rail | unreachable from the catalog |
| Bead / plan links that open a memory path in the pager | provider recognition by path | yes, if you are already in the pager |

`HistoryService` already has the queries a TUI catalog needs, all GIL-releasing:

- `subjects(scope)` — list subjects, no bodies (rail)
- `timeline(scope, selector)` — one subject's versions (card strip)
- `version(..., include_body=True)` — one body (peek)
- `compare(...)` — word ops (in-panel `=`)
- `feed(scopes, ...)` — changesets (review mode)

Python must not reimplement lineage, classification, or diffing
(`rust_core_backend_boundary.md`). Presentation, keys, and layout stay in the TUI.

---

## 2. What "excellent TUI support" has to mean

Three qualities were requested. They pull in different directions if the design forks
the pager.

### Intuitive

SASE already has a version convention: `(` / `)` mean older / newer on the Artifacts
Files pane, on card blocks, and on the pager time axis. Four of five original
researchers wanted `[` / `]` for versions; the synthesis correctly kept `(` / `)`
because it is ACE's own word. The Memory panel currently leaves those keys unbound.
A TUI user who has learned the pager, or the Files pane, will press `(` in the Memory
panel and nothing will happen.

`H` opening **now** is also a small lie. The verb is "history"; the landing is the live
file. It is defensible once a life strip is on screen (the pager does this). It is
indefensible when `H` is a context switch to a different app whose first paint is
indistinguishable from `Z` except that `Z` is not even the pager.

The Agents tab is the other intuition: when an agent misbehaves, you are on Agents, not
in `gm`. "What did it see?" is the question memory history exists to answer. Capture
already landed in `sase-1dr.1`. No TUI consumes it.

### Reliable

`tui_perf.md` is non-negotiable: no git or file IO on the keystroke or render path;
workers off the pump; re-capture selection after every await; fail open with an honest
label. The current History row already follows some of this (off-thread, cancel on
move, fail-open) and then violates honesty by leaving `…` up after a failed load.

Warm `timeline()` is still over budget in core (`sase-1ee`: ~9 git spawns per warm
query, 45–90 ms vs a 30 ms fresh-check target). In-panel stepping must therefore reuse
the pager's prefetch model (bodies in memory, ±2 neighbours, generation counters), not
call `timeline()` on every `j`/`k`. Rail recency must use `subjects()` / `feed()` once
per scope, never N timelines.

Strand cards today record an audited `sase memory read` when selected. Stepping a
strand into the past **must not** write a read-audit event. Viewing history never
audits; that contract is already documented and must hold in the panel.

`o` / `e` / `a` / `d` / `I` always mutate **now**. A past pin is read-only. Generated
subjects stay non-editable. Restore stays out (`sase-1e7`).

### Beautiful

The pager earned a visual vocabulary and then a second epic (`sase-1ef`) to make
version identity unmistakable: a solid pill that never crops, a violet past (never
amber — amber is uncommitted / unpublished), a playhead scrubber, a narrow violet
gutter rail, destination-aware footer. The Memory panel still looks like a
pre-`sase-1ef` sketch: a metadata key named "History" and a sparkline that, at catalog
width, reads as a blob.

Beauty here is **the same language at catalog scale**, not a smaller copy of the full
time band. The catalog should feel like the same product when you press `H`.

---

## 3. Alternatives considered

### A. Do nothing but document `H` / `C`

Cheap. Fixes the `ace.md` hole. Leaves the feature as a pager launcher. Rejected as
the whole answer: documentation is a phase, not the product.

### B. New ACE "Memory" tab, Artifacts-pane grammar

A first-class tab with query bar, list/detail, and a History sub-tab would match
Beads/Files. The original research rejected a new tab, and that still holds: ACE tab
pressure is already high (Agents, Artifacts, Services, Admin Center, dynamic machine
tabs in `sase-1bc`); Memory is already a scoped modal catalog; history is an *axis*,
not a place. A tab would also freeze the pane as "the memory app" instead of letting
`MemoryPane` remount in a Config hub.

### C. Embed `PagerScreen` (or its body widget) in the card

One implementation, full chrome, splits, jump labels, search. Beautiful in the
abstract, dangerous now: `sase-1es` is rewriting the pager body into a virtualized
Line-API `ScrollView`, and `sase-1eu` is putting the pager on `PaneGrid` with
three-pane T layouts. Embedding the live screen into a modal catalog while those land
is a merge trap. Revisit **after** those epics, as an optional promotion of the peek
region, not as the v1 design.

### D. Duplicate a TUI-only time axis

A panel-specific stepper with its own ordinals, colors, and diff. Fast to sketch,
guaranteed to drift from `VersionMoment` (this is exactly why `sase-1en` exists).
Forbidden by the "one vocabulary" rule already in
`src/sase/memory/history/vocabulary.py`.

### E. Time-aware catalog + pager promotion (recommended)

The Memory panel becomes the catalog and the peek surface. The pager remains the deep
reader. Agents tab consumes as-seen evidence. Shared pure helpers, no second engine.

This is the only option that is intuitive (ACE version keys, same pills), reliable
(existing service + perf rules), and beautiful (pager language at catalog scale)
without fighting in-flight pager work.

---

## 4. Design: progressive disclosure on one axis

Think of history as one axis with three magnifications, like a map.

```text
  glance          peek                     deep read
  (rail)          (card)                   (pager)
 ────────        ────────                 ─────────
  ⇧ 3d            ● NOW · v25              full time band
  ◆ 7d            ▁▂▃▅▇█ playhead          @ picker
  ◌ dirty         ( ) { } = on body        \ | splits (sase-1eu)
                  H promotes →             word diff, jump labels
```

Small motions stay in the catalog. Jumps (`H`, feed subject, as-seen chip, `@`) push
the pager and record a version-pinned trail entry, the same jumplist rule the pager
already uses.

### 4.1 One identity model

Every TUI chrome that names a version reads `VersionMoment`
(`src/sase/pager/history/moment.py`). Nothing in the panel may format `vK` by
counting visible rows. Hidden versions (`≈`, `↦`) stay skipped while stepping and
counted in `of N`. Clean now **is** `≡ vN`. Dirty now is amber `◌`, never violet.

Pills use the pager's shedding forms, already pure in
`src/sase/pager/_chrome_history.py:pill_forms`:

| Kind | Full pill | Narrow |
| --- | --- | --- |
| clean now | `● NOW · v25` | `● NOW` |
| dirty now | `◌ NOW · uncommitted` | `◌ NOW` |
| past | `⟲ PAST · v24 of 25` | `⟲ v24` |
| deleted | `✖ DELETED · v12` | `✖ v12` |

Past accent is violet (`history_palette_from_theme`, hue ≥ 60° from warning). Amber
stays unpublished (session badge) and uncommitted (git). Those two ambers are already
distinct in copy (`⚠ UNPUBLISHED` vs `◌ uncommitted`); do not add a third.

### 4.2 Memory rail — glance

After the scope loads, one `subjects()` (and optionally a bounded `feed()`) fills a
per-node glance. `j` / `k` never wait on it: paint stems immediately, then patch the
glyph.

```text
 MEMORY · sase · 24 notes · scope 1/3                         ⚠ UNPUBLISHED
 ┌ notes ─────────────────────────────┐
 │ ● sase            always loaded     │  ⟳ 1h
 │ ● tui             TUI entry point    │  ◆ 3d
 │ ○ gotchas         perf + keymap      │  ⇧ 8d
 │ ◆ glossary        terms              │  ▾
 │   • stitch        VCS unit           │  ◆ 2d
 │   • patch         review unit        │  ◌
 │ ○ agent_hood      name prefix        │  ✚ 5mo
 └─────────────────────────────────────┘
```

Rules:

- Right column is a **class glyph** plus a compact age, or `◌` when dirty, or `…`
  while the scope summary is in flight, or a dim honest chip (`UNTRACKED`, `NO VCS`,
  `SHALLOW`) when that is the truth.
- `⇧` / `⇩` use the promotion highlight; this is the one glance that changes what
  every later agent loads.
- Generated notes keep `⚙` on the left (existing mark) and may show `⟳` on the right
  when the newest version is a regen.
- Width: the rail is already capped at 32–52 columns
  (`_NOTE_RAIL_MIN_WIDTH` / `_NOTE_RAIL_MAX_WIDTH`). Shed the age first, then the
  glyph. Never wrap the stem.
- Filter `/` gains an optional `~` (or a footer toggle) for "changed since last
  review" once the watermark exists. Default filter stays stem/description.

Do not draw a sparkline per rail row. At 8 cells it is noise, and the current golden
already proves it.

### 4.3 Memory card — peek

Promote history out of the property grid and into **card chrome**, matching the
pager's anatomy at catalog scale: pill in the title row, one-row life strip under the
title, body, then the existing badges and property grid (without a History row).

```text
 ┌ M MEMORY  gotchas.md          [● NOW · v9]          sase ┐
 │ sase/memory/gotchas.md · latest · 3d ago                  │
 │ ▁▂▁▃▅▁▇▁█▏→ now                                           │
 │                                                           │
 │ # TUI Performance Gotchas                                 │
 │ …body of now…                                             │
 │                                                           │
 │ REFERENCE · read on demand                                │
 │ Type     reference                                        │
 │ Parent   AGENTS.md                                        │
 │ Source   sase/memory/gotchas.md                           │
 └───────────────────────────────────────────────────────────┘
 ( v8 · ) — · } — · = diff · H pager · C changes · o edit now
```

In the past:

```text
 ┌ M MEMORY  gotchas.md     [⟲ PAST · v8 of 9]         sase ┐
 │ sase/memory/gotchas.md · Sep 22 · 8d ago · ⇧ promoted     │
 │ ▁▂▁▃▅▁▇▁█▏→ now     playhead on v8                        │
 ││ # TUI Performance Gotchas                                │
 ││ …body of v8…                                             │
 ││                                                          │
 │ ⇧ type: reference → core · +31w −4w · sase-1au.5          │
 └───────────────────────────────────────────────────────────┘
 ( v7 · ) now · } now · = diff · H pager · o edit now
```

The leading `│` on every body row is the pager's violet gutter rail, one cell wide,
full height of the body. Deleted subjects keep last content and a tombstone pill; the
notice lives in chrome, never as a body line, so line numbers (if shown) still match.

**Keys, panel-scoped (new fields on `MemoryPanelKeymaps`):**

| Key | Action | Notes |
| --- | --- | --- |
| `(` / `)` | older / newer | skip hidden; `)` from newest committed returns to now |
| `{` / `}` | first / now | tombstone for a deleted subject |
| `=` | read ↔ diff | sticky per panel session; arriving from `C` opens diff |
| `H` | promote to pager | **at the current pin**, not always now |
| `C` | changes mode | see §4.4 |
| `@` | timeline picker | push the **pager's** picker/screen at this pin; do not fork a panel picker in v1 |
| `o` | edit now | copy already says `E edit now` in the pager; keep that honesty |

`[` / `]` stay unassigned in the panel: ACE uses them to cycle tabs, and the panel
should not steal them. Hunk jumps are a deep-read concern; they live in the pager.

The card body widget stays the existing Markdown preview for the read view. The diff
view renders `word_ops` with the same insert/strike styles as the pager (pure helper,
already theme-tested). Unchanged-run folds can wait for pager promotion; the peek
diff of a typical note is short.

**Loading.** First paint of a newly selected note is always now from the in-memory
catalog body (zero IO). The strip shows `indexing…` or a dim `…` until the timeline
lands, then the pill and sparkline fill in. A `(` pressed during load queues, the
same as the pager. Past bodies come from `version(..., include_body=True)` on a
pump-free worker with a generation counter keyed by
`(scope, selector, ordinal, view)`. Prefetch ±2 after a step. Never block `j`/`k`.

**Mutations while pinned.** `e` / `d` / `a` / `I` refuse with a one-line toast:
`leave the past to edit now · } now`. `o` is the exception: it always opens **now**
in `$EDITOR`, matching pager `E`.

**Strands.** Selecting a strand still records an audited read of *now* (today's
contract: preview is attributable). Stepping to a past strand body uses history and
writes no audit. The `AUDITED` badge refers to the now-read, and a dim
`past · not audited` chip appears next to the pill while pinned.

**Web descriptors.** Give them a History strip too. `H` already resolves them by
path; the omitted row is an inconsistency, not a rule.

### 4.4 Changes mode — review

`C` currently dumps the whole ring into a pager feed. That is the right *document*
and the wrong *host*. Review is a catalog job: you want to walk today's memory
edits the way you walk notes.

`C` toggles the rail from the note tree to a **changeset rail** for the **current
scope** (not the whole ring). `p` / `P` still change scope. A second gesture —
`C` with the scope picker, or a footer `all scopes` chip — expands to the ring,
with home rows tagged `⌂` as they already are in the feed.

```text
 MEMORY · sase · changes · 6 since review                    [C notes]
 ┌ Oct 1 ────────────────────────────────┐
 │ 14:03  feat(tui): …      athena.12     │
 │   ◆ gotchas.md           +31w −4w      │
 │   ⇧ tui.md               reference→core│
 │ 09:11  chore: sase init  ⟳ 3 regen     │  ▸ expand
 ├ Sep 30 ───────────────────────────────┤
 │ 18:40  docs(memory): …   mus.4         │
 │   ◆ glossary:stitch      +12w          │
 └───────────────────────────────────────┘
 ⏎ / H open at version · = diff · C back to notes
```

Selecting a subject row peeks that version in the card **in the diff view**. `H` or
`Enter` promotes to the pager at `subject@version` in diff, which is already how the
feed's labels work. Regen-only changesets stay folded. `r` resyncs.

The review watermark (`sase-1e6`) lives here: a right-header
`N new since you last reviewed`, and an explicit `mark reviewed` (suggested: `M` in
this mode only, documented in `?`). Opening the mode does not silently advance the
watermark.

Keep `build_feed_document` as the pager document for the deep view. Do not
re-derive changeset grouping in the panel; consume `HistoryService.feed()`.

### 4.5 `H` as promotion, not teleport

`H` today always opens now. After the card has a pin:

- from now, `H` opens the pager at now (time band visible, same as today)
- from a past pin, `H` opens that pin
- from changes mode, `H` opens the highlighted subject@version in diff
- `@` is "I want the picker"; it may be implemented as `H` plus the pager's `@`
  auto-opened, to avoid a second picker widget

`Z` stays the artifact viewer. Document the split honestly:

- `o` — edit the bytes on disk
- `Z` — raw file viewer (no time axis)
- `H` — history reader (pager)

Do not silently retarget `Z` at the pager. That would surprise every other preview
modal that shares `SourceFileActionsMixin`.

### 4.6 Instruction files in the catalog

The Memory rail is notes, webs, and strands. Instruction history (`AGENTS.md` plus
shims) is the other half of the epic and has no TUI door except "open the file in
the pager somehow."

Add a synthetic **Instructions** group at the top of the rail, one row per
`sase memory agent-docs` inventory entry for this scope, collapsed by default:

```text
 ▸ INSTRUCTIONS · AGENTS.md ≡ CLAUDE.md · 259 versions
```

Expanding shows `AGENTS.md` and any **diverged** shim as its own row (`⚠ diverged`).
Identical shims stay aliased, matching core. Home templates carry the `TEMPLATE`
chip. `H` / `( )` / the card strip work the same. Generated instruction bodies stay
read-only.

This is the smallest way to make "instruction file history" exist in the TUI without
a new tab.

### 4.7 Agents tab — as-seen

This is the TUI-only gold. Capture already stores workspace HEAD and instruction
blob OIDs at launch, and `blob_oid` on each audited read. Nothing in ACE uses them.

**Header chip**, on an agent that has launch evidence:

```text
 as seen · AGENTS.md @ v247 · 2 newer
```

The chip is a numbered hint. Activating it opens the pager on `AGENTS.md` pinned to
the launch snapshot. The pager pill/band already know how to say PAST; add one
context string, reused from the original research:

```text
 as seen by athena.sase-1bc.12 · 2 versions behind now
```

If the blob is missing (shallow, rewritten, untracked at launch), fail open to now
with `history unavailable: launch snapshot not in this checkout` — never silently
show today's file as if it were then.

**`SASE CONTEXT / MEMORY` lane.** Each read row already has a numbered hint that
pages a generated report of the **current** bytes. Keep that report. Add a second,
history-aware target: the same number (or a `H` suffix in the hint overlay) opens
the selector at the recorded `blob_oid` / commit. Prefer the commit when the blob
still exists on that commit; if the blob was rewritten, open by blob OID and say so
in the band (`blob abcd · not at HEAD`).

**`V` metadata pager.** When the metadata document includes instruction paths, the
provider will attach the axis after paint (already true). Pin those sections to the
launch snapshot when evidence exists, so `V` then `(` is "what changed in
instructions since this agent started," which is the debugging motion.

This phase *is* `sase-1e5`. It should not remain a disconnected large task while the
catalog work ships; without it the TUI still cannot answer the question that
justifies the feature.

---

## 5. Visual grammar

Reuse, do not restyle.

| Token | Source | TUI use |
| --- | --- | --- |
| Class glyphs `✚◆⇧⇩▣⟳⚙≈↦✖◌` | `vocabulary.py` | rail glance, strip, changes rows |
| Pills | `pill_forms` / `VersionMoment` | card title, footer destinations |
| Sparkline | `render_sparkline` | **card strip only**, with playhead; not the rail |
| Past violet | `history_palette_from_theme` | pill, gutter rail, past age |
| Uncommitted amber | warning / existing unpublished | `◌`, never the past |
| Home tag `⌂` | `HOME_TAG` | changes mode |
| Footer separator ` · ` | Memory panel and Artifacts shell already agree | destination footer |

Card strip shedding (narrow catalog, ~50 columns of prose):

1. drop commit subject
2. drop `⇡N`
3. drop weekday/time, keep date
4. keep pill + sparkline down to 8 cells
5. at extremely tight heights, drop the sparkline and keep the pill (the pager
   already folds the band at 12 rows)

Light and dark goldens for every new chrome: rail glance, card now, card past with
gutter, card dirty, card untracked, changes mode, instructions group, as-seen chip.
`just fix-tui-screenshots` is mandatory; generation is not approval.

---

## 6. Reliability and performance

Copy the pager's non-negotiables (`plan:202609/memory_history.md` §5.4) onto the
panel.

1. **No git/file IO on keystroke or render.** `j`/`k` paint cached glance + now
   body. Timeline and past bodies are workers.
2. **Pump-free workers** with generation counters. Stale past-body results must not
   overwrite a newer selection. Re-read `_selected_row()` after every await.
3. **One timeline per selected subject**, not per keypress. Prefetch ±2 version
   bodies. Warm step target: 30 ms p95 in-panel, same as the pager (already met
   there at ~6 ms).
4. **Rail summary is one `subjects()` per scope** on scope entry and on `r`, cached
   by index tip. Do not call `timeline()` for every rail row.
5. **Honest states, never eternal `…`.** Map failures to `UNTRACKED` / `NO VCS` /
   `SHALLOW` / `history unavailable: <reason>` / `indexing…`. Scope reload clears
   the failure set (already true).
6. **Background git never fights agents.** `--no-optional-locks`,
   `GIT_TERMINAL_PROMPT=0`, no fetch, no commit-graph from a keypress. The service
   already does this; the panel must not grow a second git path.
7. **Past links** in a peeked body are not jump-labels (the card is not the pager).
   Following a `[[target]]` chip from a past peek either (a) stays on now-relations
   as today, or (b) is disabled while pinned, with a toast `H to follow at this
   revision`. Prefer (b) for correctness: the pager is the place that can resolve
   a link at a past commit. Do not silently open today's target.
8. **Strand audit.** Now-select audits; past-step does not. Tests must pin this.
9. **sase-1ee.** In-panel peek will feel the warm-query cost on first strip paint.
   That is acceptable if it is after first paint. Do not block this epic on the
   core git-spawn bug, but do not add more git probes per `j`/`k` either.

---

## 7. Sequencing against in-flight work

| Bead | Relation |
| --- | --- |
| `sase-1es` pager virtualization | **Do not embed** pager widgets until it lands. Peek uses the catalog Markdown widget + `HistoryService`. |
| `sase-1eu` three-pane splits | Deep compare (now vs past side by side) stays a pager concern. After it lands, `H` then `\` is the beautiful split; the catalog does not grow splits. |
| `sase-1en` shared pills | **Absorb** as phase 1 of this work. Shipping pills on the History row without moving history out of the property grid would paint the wrong surface. |
| `sase-1e5` as-seen | **Absorb** as a phase. Highest TUI-only value. |
| `sase-1e6` review watermark | **Absorb** into changes mode. |
| `sase-1ee` core query cost | Adjacent; do not block; do not worsen. |
| `sase-1e7` restore | Out. Read-only peek. |
| `sase-1e8` age lens | Out. Pager-only. |
| `sase-1e9` plain git-file provider | Out. Helps plans/skills later; not Memory. |
| `sase-1ea` path@rev, side-by-side, per-host home | Out of the catalog epic. `H` benefits if path@rev lands. |

Suggested epic size: **xlarge**, five phases, Memory pane scoped so a Config-hub
remount inherits the axis for free.

| Phase | Size | Ships |
| --- | --- | --- |
| 1. Same language, honest chrome | medium | `VersionMoment` pills on the **title row**, sparkline moved out of the property grid onto a one-row strip, honest states, web/instruction rows included, `ace.md` + `?` Time group + destination footer, `H` opens the **current pin** (now until phase 2). Absorbs `sase-1en`. |
| 2. In-panel time axis | large | `( ) { } =`, queued steps, prefetch, violet gutter, past bodies, mutation guards, strand no-audit, visual goldens for past/dirty/untracked. |
| 3. Changes mode | medium | `C` toggles changeset rail for current scope, diff peek, promote to pager, watermark (`sase-1e6`). |
| 4. Instructions group | small | Synthetic rail group from agent-docs inventory, shim aliasing, `TEMPLATE`. |
| 5. Agents as-seen | medium | Header chip, MEMORY-lane pin, `V` snapshot. Absorbs `sase-1e5`. |

Phase 1 is independently valuable and small enough to land while 2 is designed
against real goldens. Phase 5 can run in parallel with 3–4 (different files:
Agents header vs Memory pane).

Flag: follow `sase_flags` if a phase would expose a half-axis (for example pills
without destinations). Prefer shipping phase 1 complete rather than hiding it.

---

## 8. Implementation sketch (for the planner)

Stay inside existing modules; do not start a parallel history package.

- **Pure chrome:** extend `memory_panel_history.py` to wrap `build_moment` +
  `pill_forms` + `render_sparkline`. Delete `_format_history_row`'s ad-hoc
  "N versions · changed" string as the primary view.
- **Card layout:** `memory_panel_rendering.py` / `memory_panel_view.py` — title
  row gains the pill; a new strip `Static` sits above the Markdown body; drop
  History from the property grid.
- **Stepping:** `memory_pane_history.py` gains a pin (`ordinal` / `now` / `view`)
  per selected identity, reset on note change and on scope change. Workers call
  `HistoryService.version` / `compare`.
- **Rail glance:** one worker on scope load calls `subjects()`; patch row
  suffixes through the existing programmatic-selection guard.
- **Keys:** `MemoryPanelKeymaps` fields `older_version`, `newer_version`,
  `first_version`, `now_version`, `toggle_diff` with defaults
  `left_parenthesis`, `right_parenthesis`, `left_curly_bracket`,
  `right_curly_bracket`, `equals_sign`. Wire `default_config.yml`, schema,
  `configuration.md`, help meta.
- **Changes mode:** consume `feed()`; do not parse git log in the panel.
- **As-seen:** Agents header + `_agent_memory_reads.py`; pager opens via the
  same `build_history_document(..., initial_revision=...)` path `H` uses.
- **Tests:** expand `tests/ace/tui/modals/test_memory_panel_history.py` for
  pins, honest states, no-audit on past strands, `H` at pin. New visual
  goldens beside `memory_panel_history_{dark,light}_120x40`. Trace
  `j`/`k` with `SASE_TUI_PERF=1` to prove first paint unchanged.

---

## 9. Recommended solution

**Build a time-aware Memory catalog. Keep the pager as the only full history
reader. Teach the Agents tab to open the snapshot an agent actually saw.**

Concretely:

1. **Reject** a new ACE tab, a forked TUI time axis, and in-panel embedding of
   `PagerScreen` while pager internals are being rewritten.
2. **Treat the current `H` / `C` / History-row work as a front door that shipped,
   not as TUI support.** Keep the door; stop pretending it is the product.
3. **Make the Memory panel speak the pager's language** (`VersionMoment` pills,
   violet past, amber dirty, honest chips, destination footer, class glyphs).
   Move history from a property-grid row onto the card title and a one-row life
   strip. That is the beauty pass, and it is also `sase-1en` done in the right
   place.
4. **Put ACE's version keys on the card.** `( ) { } =` peek; `H` promotes the
   current pin into the pager; `C` reviews the current scope as a changeset
   rail; `@` is the pager picker. `o` always edits now. Past is read-only.
5. **Add an Instructions group** so `AGENTS.md` history is a catalog row, not a
   scavenger hunt.
6. **Wire as-seen on the Agents tab** from evidence that already exists. Without
   this, the TUI still cannot answer the question memory history was built for.
7. **Hold restore, age lens, path@rev, and side-by-side** on their existing
   beads. They make the *pager* better; they are not what makes the *TUI*
   support history.

If only one phase ships, ship **phase 1 (same language + honest chrome + docs) plus
phase 5 (as-seen)**. That pairing is the difference between "the pager has a
launcher in ACE" and "ACE knows about memory in time." The in-panel stepper is
what then makes it feel native.

The feature is already reliable in the pager. The TUI work is to stop hiding it.
