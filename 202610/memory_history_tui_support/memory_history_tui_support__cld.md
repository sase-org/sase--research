# Memory history in the ACE TUI: design research and recommendation

- **Researcher:** cld (swarm `research.3c`)
- **Date:** 2026-10-02
- **Context:** epic `sase-1dr` (closed 2026-10-01), plan `plan:202609/memory_history.md`, and the follow-ups it filed
  (`sase-1e5`…`sase-1ee`, `sase-1en`).
- **Checkout examined:** `master` at `45f165b6d5`.

## TL;DR

1. **You're right that the pager is the only working memory-history surface, but for a sharper reason than
   expected.** The epic did ship TUI entry points: `H` (history) and `C` (changes) in the Memory pane, plus a
   History row on note cards. However, **`H` and `C` are silently broken.** Each one builds its document and then
   dies with `RuntimeError: The call_from_thread method must run in a different thread from the app`. The failure
   toast uses the same call, so nothing appears on screen. I reproduced this headlessly (§1.2). No test presses
   either key, and `docs/memory_history.md` (lines 6 and 143) still advertises both.
2. **Even with that fixed, the TUI story is thin:**
   - The Memory pane is buried. You reach it with `#` → `1 Config` → `05 Memory`, or `gm` from the prompt bar.
   - At 120×40 the note card is only about 52×15 cells.
   - The History row is an 8-cell sparkline that falls apart for short histories.
   - Every surface builds its own `HistoryService`; the pager provider builds a new one on every lookup.
   - The Agents tab, where you actually spend your time, knows nothing about memory versions. The epic already
     records the evidence it would need: `blob_oid` on every read and `instruction_snapshot` at launch.
3. **Recommendation: one model, one reader, four doors.** The pager stays the single deep reader. ACE gets
   native surfaces you can read at a glance and that show time. All of them:
   - render through the same pure presentation kit the pager already uses (pill, scrubber, meaning row, word
     diff, picker, palette);
   - share one app-scoped history service;
   - hand off to the pager with an **exact version pin**. You never land at "now" after looking at the past.

   The four doors:
   1. **A time strip and inline time axis on the Memory card.** `( ) { } = @` step through versions inside the
      card, a violet frame marks the past, and `H` opens the pager at the same moment.
   2. **A Memory changes review screen** (`C`): a full-screen list-and-detail view of memory changesets. Move with
      `j`/`k`, read word diffs and bead/agent/commit chips, and track new changes with unread dots backed by a
      review watermark.
   3. **An agent lens on the Agents tab.** Each MEMORY-lane row, plus a new `AGENTS.md as launched` row, says
      which version the agent saw and whether it has changed since. The hint opens the pager pinned at that
      version.
   4. **The pager everywhere**, as today: memory paths opened anywhere already get the time axis. It now runs on
      the shared warm service, so it opens instantly.
4. **Phases:** **P0** reliability floor (the fix, a shared service, end-to-end key tests) → **P1** note lens →
   **P2** changes review → **P3** agent lens → **P4** polish (restore as draft, an `AGENTS.md` root row, deleted
   notes, unread dots on the note list). Each phase ships value on its own.

---

## 1. What exists today

### 1.1 Inventory

| Surface | Where | State |
| --- | --- | --- |
| Pager time axis | `src/sase/pager/_screen_history*.py`, `_screen_time_band.py`, `_screen_diff*.py`, `_timeline_picker.py`, and `history/` | **Works well.** It has the pill (`● NOW · v25`, `⟲ PAST · v24 of 25`, `◌ NOW · uncommitted`, `✖ DELETED`), the playhead scrubber, meaning and cause rows, the word diff with folds, the `@` picker with two-point compare, the trail with version pins, and split panes. Warm step p95 is about 6 ms. |
| `sase memory history` CLI | `src/sase/memory/history/cli_history*.py` | Works, with `text`, `json` and `pager` output. Ends with about 1.1–1.8 s of interpreter start-up. |
| Pager feed | `src/sase/memory/history/feed_document.py` | Works from the CLI. From ACE it is only reachable through `C`, which is broken. |
| Memory pane `H` / `C` | `src/sase/ace/tui/modals/memory_pane_history.py:189-397` | **Broken** (§1.2). |
| Memory card History row | `memory_panel_history.py` and `memory_panel_rendering.py:_build_note_property_grid` | Loads off-thread. Its 8-cell sparkline says little: two versions render as one block glyph, and the bead name is cut off (see golden `memory_panel_history_dark_120x40.png`). Web descriptor rows get no row at all. |
| Agents tab MEMORY lane | `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_reads.py` | Lists audited reads. Hints open the raw path or a report that re-resolves the **current** note. Nothing under `src/sase/ace/` reads the captured `blob_oid` / `included_blob_oids` (`memory/_read_log_models.py:86-87`) or `agent_meta.instruction_snapshot` (`axe/launch_evidence.py:248-262`). |
| Pager opened on a memory path anywhere in ACE | path-triggered provider (`pager_provider_core.py:52-104`) | Works. Each lookup builds a new `HistoryService` (`pager_provider_core.py:444`, called from `pager/history/provider.py:124-146` every time). |

### 1.2 The broken entry points (evidence)

`action_open_history` and `action_open_changes` each run an `async def` coroutine through `run_worker(...)` without
`thread=True`. That coroutine executes on the app's own thread. After `await asyncio.to_thread(_build)`, it calls
`self.app.call_from_thread(_push)` at `memory_pane_history.py:278` and `:390`. The failure path calls
`self.app.call_from_thread(self.notify, ...)` at `:244` and `:362`.

Textual raises an error whenever `call_from_thread` runs on the app thread
(`.venv/.../textual/app.py:1748-1751`). Because the worker uses `exit_on_error=False`, the exception disappears.

I mounted `MemoryPanel` headlessly with `AcePage`, used a fake service, stubbed the builder, and pressed the
actions:

```text
H: built: {'called': True}  pushed: {}
   worker state: WorkerState.ERROR  error: RuntimeError('The `call_from_thread` method must run in a different thread from the app')
C: pushed: {}
   worker state: WorkerState.ERROR  error: RuntimeError('The `call_from_thread` method must run in a different thread from the app')
```

The tests in `tests/ace/tui/modals/test_memory_panel_history.py` only check bindings, footer text and row
formatting. The History golden injects its summary straight into `_history_latest`. Nothing exercises the actions
themselves. `src/sase/ace/tui` contains 55 `call_from_thread` call sites, which deserve a cheap audit (§5.7).

**Proposed bug bead, for the lead to file after deduplication:** "Memory pane `H`/`C` call `call_from_thread`
from an app-thread async worker; neither the pager nor the failure toast ever appears."

### 1.3 Other gaps that shape the design

- **It is buried, and the card is small.** The Memory pane's only production host is the Admin Center Config hub
  (`config_hub_catalog.py:76-88`). The standalone `MemoryPanel` modal is used only by tests. I rendered the hub at
  120×40 (§8.2): the rail is about 52×15 cells and the card about 52×15. Inline history has to stay compact, and
  serious reading belongs in the full-screen pager.
- **Each service call costs real time.** Measured warm on this checkout (139 subjects, 1186 versions, 51 hidden):

  | Call | Time |
  | --- | --- |
  | scope build | 40 ms |
  | `sync` | 46 ms |
  | `subjects` | 31 ms |
  | `timeline` | 53–54 ms, repeated calls included (no in-process memo) |
  | `feed(limit=50)` | 32 ms |

  The cold index takes about 2.3 s per `docs/memory_history.md`. The first CLI run in this session took 19.4 s
  wall-clock but only 2.5 s of CPU, so that cold build was mostly waiting, probably on a lock. Bug `sase-1ee`
  tracks the roughly 9 git spawns behind each warm query. ACE has to treat history as asynchronous, cache it by
  tip, and warm the index early.
- **Overlapping open beads:**

  | Bead | Status | Topic |
  | --- | --- | --- |
  | `sase-1en` | READY | Panel row should use the pill vocabulary and `≡ now` via `moment.py` |
  | `sase-1e5` | READY | Memory as seen by an agent |
  | `sase-1e6` | READY | Review watermark |
  | `sase-1e7` | READY | Restore as an unpublished draft |
  | `sase-1ee` | READY | Per-query git cost |
  | `sase-1es` | IN_PROGRESS | Virtualized pager body |
  | `sase-1eu` | IN_PROGRESS | PaneGrid three-pane splits |

  The design below absorbs the TUI half of 1en, 1e5 and 1e6, and leaves room for 1e7.
- **`PagerView` cannot be dropped into another widget today.** It is a real widget, but `pager_host` is
  hard-wired to `self.screen` and must satisfy the `_PagerViewHost` protocol (`view.py:58-94`: `paint_footer`,
  `close_view`, `focus_view`, `focus_other_view`, `show_in_other_view`). Its bindings, key routing and CSS live on
  `PagerScreen`. Embedding it is possible, but that is a project of its own (§4, option C).

## 2. Jobs to be done

| # | Job | How often | Today | Desired |
| --- | --- | --- | --- | --- |
| F1 | "Agents changed memory. What changed, and who changed it?" | Daily. The feed holds 499 changesets in about 5½ months. | CLI feed only (`C` is broken) | Scan changesets with `j`/`k`, see word diffs and provenance, know what is new since you last looked. |
| F2 | "Why does this note say X? When did that rule appear?" | Weekly | CLI, or the pager on the file | Step versions right where the note is shown, then deep-read in the pager. |
| F3 | "Why did this agent behave like that? Which memory did it see?" | Whenever you debug an agent | Not possible | From the agent, open the exact version it read, see whether it has changed since, and compare. |
| F4 | "Undo that memory change." | Rare | Manual git | Restore a past version as an unpublished draft (`sase-1e7`), then publish. |

F1 and F3 are where a TUI can beat a CLI. They need a list with a selection, live state, and cross-links to agents
and beads.

## 3. Design principles for history in ACE

The epic's principles still hold: time is an axis, not a mode; you always know when you are in the past; you keep
your place; meaning before mechanics; fail open. ACE adds six of its own:

1. **Same verbs everywhere.** `(`/`)` already step versions or blocks in three places: Agents-deck card blocks,
   Artifacts Files versions, and the pager. Wherever a memory document is shown, `( ) { } = @` mean exactly what
   they mean in the pager.
2. **Same pixels everywhere.** Every history visual in ACE is drawn by the same pure functions the pager uses:
   pill, scrubber, meaning row, honest-state chip, word diff, picker rows and history palette. Nothing is
   reimplemented, so the surfaces cannot drift apart.
3. **Glance natively, read deeply in the pager.** ACE surfaces are sized to be scanned. Any deep read, search,
   label, split or fold expansion goes to the full-screen pager, carrying the exact pin: subject, ordinal and
   blob, view, and compare base.
4. **Never block, never lie, never fail silently.** There is no git on the keystroke path. A cold index shows
   `indexing…` in the space it will later fill. Every honest state appears (UNTRACKED, IGNORED, NO VCS, SHALLOW,
   TEMPLATE, unavailable). A key the user pressed that fails always produces a toast. That last rule is the lesson
   of §1.2.
5. **Calm by default.** History shows up where memory already shows up. There is no history mode, no new main
   tab, and no mandatory notifications.
6. **Review is explicit and reversible.** Unread state works like the Agents tab (`U`, `,j`, `,u` with undo).
   Opening the screen marks nothing as read.

## 4. Options considered

| Option | Intuitive | Reliable | Beautiful | Cost | Verdict |
| --- | --- | --- | --- | --- | --- |
| **A. Fix `H`/`C` and stop there** (launcher only) | ◐ The Memory card still can't step through time | ✓ | ◐ The History row stays weak | S | **Necessary but not enough.** Becomes P0. |
| **B. Inline time axis in the Memory card, built from the pure kit** | ✓ The same `( )` idiom as Reply-card blocks and Files versions | ✓ Pure layers, no new git paths | ✓ Pill, scrubber, violet frame | M | **Recommend** (P1). |
| **C. Embed `PagerView` as the card body** | ◐ Pager-letter labels (0-9a-z) collide with pane keys, and focus gets subtle | ◐ Needs a new host adapter, key forwarding and CSS | ◐ Card shows line-numbered source instead of rendered Markdown; pager chrome repeats the card title in a 15-row card | M–L | **Defer.** Revisit after `sase-1eu` (PaneGrid) settles, if ACE wants an embeddable reader more widely. |
| **D. Memory changes as a new Artifacts-tab pane** | ✓ Main tab, with relations to agent, bead and stitch | ✓ Host features (query bar, relations) come free | ✓ | **L+.** Every existing pane runs to 10–15 modules (`widgets/artifacts/*`), and memory changesets are not sidecar artifacts. | **Defer.** P2's feed model could back such a pane later. |
| **E. Promote Memory to a fourth main tab** | ✓ Roomy | ✓ | ✓ | L, and changes ACE's whole layout | **Don't.** You placed memory under Config deliberately. History doesn't justify moving it. |
| **F. Memory changes review as a full-screen ACE screen** | ✓ ACE's list-and-detail idiom (`j`/`k` with an instant detail) | ✓ Built on the feed wire and the pure diff renderer | ✓ Day rules, unread dots, provenance chips | M–L | **Recommend** (P2). |
| **G. Keep the review inside the pager feed and lean on pager splits** (`\|` then `ctrl+w` plus a label) | ◐ Two or three keys per item, no cursor, no unread state | ✓ | ◐ | S | The pager feed stays for the CLI. ACE gets F. |

## 5. Recommended design

### 5.1 Architecture: one model, one reader, four doors

```text
                    sase-core (index, classes, prose diff, feed, resolve, review watermark*)
                                              │  PyO3, GIL released
                         HistoryService (thread-safe; add a tip-keyed timeline/compare memo)
                                              │
            ┌─────────────────────────────────┴──────────────────────────────────┐
            │  AceMemoryHistory (app-scoped, one per ACE process)                │
            │  • one HistoryService shared with the pager provider factory       │
            │  • per-scope sync coalescing + cheap change tokens (HEAD/ref stat) │
            │  • caches: timeline[(scope,subject,tip)] · body[blob] · cmp[blobs] │
            │  • warm-up after startup in quiet time · generation-guarded loads  │
            └───────┬────────────────────┬────────────────────┬──────────────────┘
                    │                    │                    │
          Door 1: Memory card    Door 2: Memory changes  Door 3: Agents lens        Door 4: pager
          strip + ( ) { } = @    review screen (C)       MEMORY lane + launch row   (path-triggered)
                    │                    │                    │                          │
                    └──────────── exact VersionPin handoff ───┴──────────────► PagerScreen (the reader)

  Shared presentation kit (pure, no IO): build_moment/step_target/boundary_notice, pill_forms/history_badge,
  render_scrubber, meaning_row/cause_row, honest_chip, build_diff_body, build_picker_rows +
  TimelinePickerScreen, history_styles_for_theme, the vocabulary glyphs, and a new feed view-model.
  (* = new core state; see §5.10.)
```

**Promote the kit to a public module.** One candidate is `sase.pager.history.kit`, re-exporting the pieces above.
Today ACE reaches into private modules (`sase.pager._time_band.render_sparkline`), which is fragile and something
Symvision flags. Promoting the kit is also what makes "same pixels everywhere" enforceable.

### 5.2 Door 1: the Memory card's time strip and inline time axis (P1)

A two-row **time strip** sits under the card's path line for every note, web descriptor and strand. It replaces the
History property row. The strip always takes two rows when the card is at least 14 rows tall, so stepping through
versions never moves the body. In shorter cards it folds into one row.

**Now, clean** (Admin Center at 120×40; versions, dates and names are illustrative):

```text
┌────────────────────────────────────────────┐ ┌──────────────────────────────────────────────────────┐
│ ● gotchas  Code conventions and gotchas.   │ │ M MEMORY  dispatch                              sase │
│ ○ dispatch  Read before %dispatch to a     │ │ sase/memory/dispatch.md                              │
│   remote machine.                          │ │ ▐● NOW · v14▌ v1 ▁▂▁▅▁▃▇▂▁▃▁▅▇█ ● now                 │
│ ○ lint_and_test  Read before finishing a   │ │ ◆ last: § Remote dispatch · +6w −6w      athena · 3d │
│   turn.                                    │ │                                                      │
│ ○ tui  Entry point for SASE TUI work.      │ │ Read before dispatching agents to a remote machine.  │
│                                            │ │                                                      │
│                                            │ │ Remote dispatch                                      │
│                                            │ │ Use %dispatch(<alias>) to run an agent on another    │
│                                            │ │ tailnet machine. The alias must appear in…           │
└────────────────────────────────────────────┘ └──────────────────────────────────────────────────────┘
 ( ) history · = diff · @ timeline · H open in pager · C changes · e edit · ? keys
```

**The past, read view.** Press `(` twice. The card frame turns violet (the past accent; drawn heavy here because
the mockup has no colour). The path line gains `@ sha · date`, the playhead moves along the scrubber, and the
meaning row tells this version's story:

```text
┌────────────────────────────────────────────┐ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
│ ● gotchas  Code conventions and gotchas.   │ ┃ M MEMORY  dispatch                              sase ┃
│ ○ dispatch  Read before %dispatch to a     │ ┃ sase/memory/dispatch.md @ 4c1e9a2 · Sep 27 2026      ┃
│   remote machine.                          │ ┃ ▐⟲ PAST · v12 of 14▌ v1 ▁▂▁▅▁▃▇▂▁▃▁[▅]▇█ ● now       ┃
│ ○ lint_and_test  Read before finishing a   │ ┃ ◆ § Remote dispatch · +44w −10w      sase-1bc.5 · 5d ┃
│   turn.                                    │ ┃ ──────────────────────────────────────────────────── ┃
│ ○ tui  Entry point for SASE TUI work.      │ ┃ Remote dispatch                                      ┃
│                                            │ ┃ Use %dispatch(<alias>) to run an agent on another    ┃
│                                            │ ┃ machine. Aliases come from sase machine list…        ┃
│                                            │ ┃                                                      ┃
└────────────────────────────────────────────┘ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
 ( v11 · ) v13 · } now · = diff · @ timeline · H open in pager · e edits now
```

**The past, diff view** (`=`). The scrubber highlights the compared range; the body becomes the pager's word diff
with folded unchanged runs. Here `[-…-]{+…+}` stands in for strike-through and the insert tint:

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ M MEMORY  dispatch                              sase ┃
┃ sase/memory/dispatch.md @ 4c1e9a2 · Sep 27 2026      ┃
┃ ▐⟲ PAST · v12 of 14▌ v1 ▁▂▁▅▁▃▇▂▁▃[▃▅]▇█ ● now       ┃
┃ ◆ § Remote dispatch · diff vs v11 · +44w −10w     5d ┃
┃ ──────────────────────────────────────────────────── ┃
┃  ┄┄┄┄┄┄┄┄┄┄┄┄┄ 6 unchanged lines ┄┄┄┄┄┄┄┄┄┄┄┄┄       ┃
┃ Use %dispatch(<alias>) to run an agent on another    ┃
┃ [-tailnet-]{+machine; aliases come from+}            ┃
┃ {+sase machine list.+} The alias must…               ┃
┃ − 2 lines removed                                    ┃
┃  ┄┄┄┄┄┄┄┄┄┄┄┄ 31 unchanged lines ┄┄┄┄┄┄┄┄┄┄┄┄┄       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
 ( v11 · ) v13 · } now · = read · @ timeline · H open in pager (diff) · e edits now
```

**Strip anatomy.** Each piece comes from the kit:

- **Row 1:** the pill (`history_badge`, longest form that fits), then the scrubber (`render_scrubber`, with diff
  range, dirty and tombstone support built in). At now it adds an age.
- **Row 2:**
  - in the past: the meaning row (`meaning_row` — class glyph, section path, word delta, frontmatter phrase, with
    bead or agent and age on the right);
  - at now: the latest change in dim;
  - for instruction subjects: the cause row (`⟳ rendered · sources: …`);
  - otherwise: the honest-state row.

**States.** Every state reuses the pager's words:

| State | Strip |
| --- | --- |
| Index building | dim `indexing…` in row 1, with row 2 reserved. Keys pressed meanwhile are queued, last one wins, as in the pager. |
| Uncommitted / unpublished | amber `◌ NOW · uncommitted`; `=` shows your pending edit against HEAD |
| Untracked or ignored | amber `UNTRACKED · commit this file to start its history` |
| Home without chezmoi | dim `NO VCS · home memory is not in git` |
| Home with chezmoi | `TEMPLATE` chip; history follows the chezmoi template source |
| Shallow clone | `SHALLOW · history truncated at <date>` |
| Failure | dim `history unavailable: <reason>`. The card keeps working, and an explicit key press toasts the reason. |

**The publish loop.** This is the moment the design is built around:

1. Edit a note with `e`. The strip flips to amber `◌ NOW · uncommitted`.
2. `=` shows your pending word diff.
3. `I` publishes.
4. On the next change-token tick, the strip settles to `● NOW · v15` and a new bar grows at the scrubber's right
   edge.

It shows that memory edits are durable, on screen, without any new concept.

**Keys** (Memory pane scope only, all currently free there):

| Key | Verb |
| --- | --- |
| `(` / `)` | Older / newer version. Hidden versions are skipped. `)` from the newest version returns to now. |
| `{` / `}` | First version / back to now |
| `=` | Read ↔ diff. Read is the default, as in the pager. An explicit `=` stays in effect for the rest of the pane session. |
| `@` | Timeline picker: the pager's `TimelinePickerScreen` with `build_picker_rows`. `⏎` jumps there; `=` compares with the open version. |
| `H` | Open the full pager at this exact pin and view. It previously always opened at now. |
| `y` / `Y` in the past | Copy that version's body / copy `sha:path` |
| `e` in the past | Edits the live note; the footer says "e edits now" |

**Behaviours:**

- **Selection.** `j`/`k` to another note shows that note at now. Small motions never carry a pin across notes.
- **Trail.** Chip travel (`⏎`, `.1`–`.9`) pushes a trail entry that records the pin. `Backspace` restores the
  exact moment, as the pager's trail does.
- **Scope switch.** `p`/`P` resets to now.
- **Strands.** History views never record an audited read (decision D10). The strand's now-view keeps its
  existing audited-read gate.
- **Frontmatter.** It is stripped from past read bodies so they match the now-view. Changes to it appear as the
  semantic block (`⇧ type: reference → core — now loaded by every agent`).
- **Generated notes** show `⟳ regenerated` and remain read-only.
- **Renames** show `↦ renamed from build_and_run.md (63%)` on row 2 while you're on a version from before the
  rename.
- **Returning from the pager.** When you close a pager you opened with `H`, the card adopts the pager's final pin
  for the same subject, so where you ended up in the pager is where the card stands (P4 nicety).

**Width shedding** follows the pager's order:

- Row 2 drops bead or agent first, then age, then the section path.
- Row 1 shortens the pill to `⟲ v12/14` then `⟲ v12`, and shrinks the scrubber to no fewer than 8 cells.
- Absolute dates live only on the path line and are dropped first.

### 5.3 Door 2: the Memory changes review screen (P2)

`C` in the Memory pane opens a full-screen `MemoryChangesScreen` (no longer the pager feed). So do a command-palette
entry ("Review memory changes") and the Admin Center sub-tab badge.

```text
 ▤ MEMORY CHANGES  ·  sase + home  ·  last 30 days  ·  41 changesets  ·  9 regen-only hidden                  ● 3 new
┌─ Changesets ───────────────────────────────────┐ ┌─ ◆ 3 subjects ──────────────────────────────────────────────────┐
│ ━━ Today ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │ feat(goals): complete G1 acceptance (sase-1bu.7)                │
│ ● 11:03 ✚ decisions:goal-ledger  +2 more  180w │ │ Fri Oct 2 2026 11:03 · 2h ago · project sase                    │
│ ● 10:41 ◆ dispatch               +44w −10w     │ │ ◈ sase-1bu.7   ⬡ athena.sase-1bu.7   ◉ 1a2b3c4                  │
│ ━━ Yesterday ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │                                                                 │
│ ● 18:29 ◆ README                  +4w −4w      │ │ ─ .1 ✚ decisions:goal-ledger · new decision · 180w ──────────── │
│   14:19 ⇧ gotchas         reference → core     │ │   A goal is its own Rust-owned domain, not a bead type. State   │
│ ━━ Mon Sep 28 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │   is immutable events plus live markers through the hidden…     │
│   09:02 ◆ glossary:artifact       +20w −3w     │ │ ─ .2 ✚ decisions:goals-host-binds · new decision · 150w ─────── │
│   08:40 ◆ dispatch     ⌂          +6w −6w      │ │   The host binds every LLM turn to exactly one goal before…     │
│   ⋯ 5 regenerated-only changesets       a show │ │ ─ .3 ◆ glossary:goal · § Definition · +20w −3w ──────────────── │
│                                                │ │   A goal is a [-durable-]{+host-bound+} unit of intent that…    │
│                                                │ │                                                                 │
│                                                │ │ ⟳ AGENTS.md §3.1 (+2 entries) · README.md · decisions roster    │
└────────────────────────────────────────────────┘ └─────────────────────────────────────────────────────────────────┘
 j/k move · ⏎ open .1 in pager · .1-.9 subject · tab chips · U unread · ,j next unread · ,u all read · / filter · ? keys
```

**The list** (left). Each nav item is one changeset (one commit):

- a `●` unread dot, the same dot the Agents block rail uses for unseen arrivals;
- the time;
- the class glyph and first authored subject, plus `+N more`;
- the word delta, right-aligned and dim;
- `⌂` for home-scope changes.

Day rules are chrome, not nav items, and read `Today`, `Yesterday`, then `Mon Sep 28`. Changesets that only
regenerate files collapse into one count line (`a` toggles them), as the feed already does.

**The detail** (right) is drawn the way a deck lays out a multi-card spread:

- A header with the commit subject (conventional prefix dimmed), absolute and relative time, and scope.
- **Provenance chips** using the Artifacts tab's own icons and accents: `◈` bead `#D787FF`, `⬡` agent `#0062FF`,
  `◉` stitch `#FFD700`. Memory changes then look like part of the same artifact family.
- One section per authored subject, each under a titled rule. Each section holds `build_diff_body` output with
  one line of context so changesets stay scannable; brand-new subjects show their opening words instead.
- One `⟳` line folding the generated consequences.

**Keys:**

| Key | Verb |
| --- | --- |
| `j`/`k`, `g`/`G` | Move through changesets. The detail is debounced; the highlight never is. |
| `⏎` | Open the focused subject (default `.1`) in the pager at that version, in the diff view (the pager's arrival rule for feeds) |
| `.1`–`.9` | Open subject N, reusing the Memory pane's numbered-chip prefix |
| `tab` / `shift+tab` | Move the chip cursor across subjects, bead, agent and commit. `⏎` follows: bead and agent chat go through the pager's existing resolvers; a commit opens the stitch view where one exists, otherwise copies. |
| `ctrl+d` / `ctrl+u` | Scroll the detail |
| `/` | Filter over subject, agent, bead and commit subject |
| `S` | Cycle scope: all → project → home |
| `a` | Show regen-only changesets |
| `U` | Toggle unread on this changeset |
| `,j` | Jump to the next unread changeset and mark it read |
| `,u` | Mark everything read; press again within 10 s to undo |
| `r` | Refresh (re-sync) |
| `?` | Help |
| `esc` / `q` | Close |

`U`, `,j` and `,u` match the Agents tab exactly. P2 must confirm the `,` leader dispatches inside this modal; if
it can't, bind the same verbs without the leader and document them.

**The review watermark** (`sase-1e6`):

- **What it stores:** one watermark per scope key (`project:sase`, `home`), not per workspace checkout, so all
  `sase_<N>` clones share it. Each watermark is the newest reviewed changeset (commit plus committer time), plus a
  small set of changesets marked read above it. The watermark advances once everything below a changeset is read.
- **Rewritten history:** if the watermark's commit is no longer reachable after a force-push, fall back to
  committer time and say so in the header.
- **Where it shows:**
  - the review header (`● 3 new`);
  - the Admin Center sub-tab label (`05 Memory ●3`);
  - later, a dot on the note-list rows of notes with unreviewed changes (P4).
- **What it never does:** no mandatory notifications. An opt-in toast setting is an open question (§7).

**Data and performance:**

- The list comes from one `feed(scopes, since=30d, limit=200)` call (32 ms per 50 changesets, warm).
- `load older` appears at the end of the list.
- Detail comparisons call `compare` once per subject. They are cached by blob pair, which never goes stale, and
  the neighbouring changesets (±1) are prefetched.
- Pure builders turn the feed wire into list rows. Extract `sase.memory.history.feed_model` (day grouping, row
  text, regen folding) and have both the pager feed document and this screen use it, so the two can never
  disagree.

### 5.4 Door 3: the agent lens on the Agents tab (P3; the TUI half of `sase-1e5`)

The Context card's MEMORY lane gets a version chip on every read, plus a first row for the instruction file the
agent launched with:

```text
┌─ Context ────────────────────────────────────────────────┐
│ MEMORY  4 reads · 3 files · AGENTS.md as launched        │
│   ◇ AGENTS.md          v258 ⟲ 2 newer since launch   [2] │
│   10:02 ◇ gotchas        v25 ≡ now                   [3] │
│         Need keymap conventions before editing bindings  │
│   10:04 ◇ dispatch       v12 ⟲ 2 newer               [4] │
│         Remote launch rules for %dispatch                │
│   10:05 ◇ glossary:goal  v3 ≡ now                    [5] │
│         Confirm goal vocabulary                          │
└──────────────────────────────────────────────────────────┘
```

- **`≡ now`** (dim) means the agent read today's text. **`⟲ N newer`** (past accent) means memory has changed since
  the agent read it, which is often exactly what you are debugging.
- **The hint** opens the pager pinned at the version read, in the read view. From there `}` jumps to now and `=`
  diffs. The band's `⟲ PAST · v12 of 14 · 2 newer` repeats the story.
- **The `AGENTS.md` row** resolves `instruction_snapshot.blob_oid`, falling back to `workspace_head`. If the
  snapshot matches no committed blob (a dirty checkout at launch, or a per-host home render), the pager opens the
  stored bytes from `~/.sase/instruction_snapshots/<oid>` as an honest pseudo-version: `◌ as launched · not in
  git`. `=` compares it with the nearest committed version.
- **Batch reads** (`included_blob_oids`) show one chip per included file inside the generated report.
- **Loading:** chips load in the existing off-thread context loader, through the app-scoped service and its
  tip-keyed timelines. They render empty first and fill in, so they never delay the card (`tui_perf` rule 7).

### 5.5 Door 4: the pager everywhere

Nothing new for users. Two changes underneath:

- The provider factory reuses the process-wide `HistoryService` instead of building one per lookup.
- In ACE, it reuses the app-scoped caches.

Every door states its **arrival rule** (it extends the pager's §4.5):

| From | Opens at | View |
| --- | --- | --- |
| Memory card `H` | the card's pin | the card's view |
| Review screen `⏎`, `.N` | that subject at that changeset's version | diff |
| Agents lane hint | the version the agent read, or the launch snapshot | read |
| Any memory path elsewhere | now | read |

### 5.6 The visual system ("beautiful")

- **One palette.** `history_styles_for_theme(app.theme)` supplies:
  - the past accent (violet, seeded near `#9d7cd8`), kept at least 60° of hue away from amber, which already
    means uncommitted or unpublished;
  - the inserted-word tint and the struck-through delete style;
  - pill pairs, gutter marks and the scrubber ramp.

  Contrast is enforced at 4.5 for text and 3.0 for marks. ACE passes the live theme, so light and dark themes
  both work, and switching themes repaints.
- **Shapes that already mean something in ACE:**
  - solid capsule pills, the same shape as the block rail's `▐…▌` active pill;
  - `●` unread dots, the same as block-rail arrivals;
  - titled rules between sections, the same as a deck spread;
  - Artifacts icons and accents for provenance.
- **The past frame.** While pinned to a past version, the card's border takes the past accent, mirroring the pager's
  `history_past-frame` golden. It is the strongest possible "you are in the past" signal, and it costs zero rows.
- **No layout jumps.** The strip reserves its rows. Loading, failure and honest states render inside them.
  Entering the past never pushes the body down.
- **One glyph table:** `✚ ◆ ⇧ ⇩ ▣ ⟳ ⚙ ≈ ↦ ✖ ◌ ⇡N` from `sase.memory.history.vocabulary`. ACE never defines its own.
- **Typography:**
  - subject names bold;
  - metadata dim;
  - word deltas right-aligned so the eye can scan the numbers;
  - relative day names (`Today`, `Yesterday`) in the list, absolute timestamps in the detail and on the path line.

### 5.7 Reliability engineering

1. **Fix the entry points correctly.** In an async worker, `await asyncio.to_thread(build)` and then call
   `push_screen` / `notify` directly, since the code is already on the loop. The alternative is a thread worker
   plus `call_from_thread`. Every failure produces a toast with the reason.
2. **Test by pressing keys.** Add headless `AcePage` tests that press `H`, `C`, `(`, `)`, `=` and `@` against a fake
   service and assert on the resulting screens and states. Add one generic guard: an AST test that flags
   `call_from_thread` inside an `async def` handed to `run_worker` without `thread=True` under `src/sase/ace/tui`,
   and audit the 55 existing call sites once.
3. **App-scoped service, `AceMemoryHistory`:**
   - one `HistoryService`, built off-thread, also handed to the pager provider factory;
   - a tip-keyed in-process memo for `timeline` and `version` (warm repeats drop from about 54 ms to about 0);
   - LRU caches keyed by blob (bodies) and by blob pair (comparisons);
   - `sync` coalescing: one in-flight sync per scope, last request wins.
4. **Change tokens, not polling git.** On idle ticks, stat the scope's `HEAD`, the current ref and `packed-refs`
   (the same approach as ACE's `ace_refresh_tokens`, `tui_perf` rule 14). Re-sync only when the token drifts, then
   repaint visible strips:
   - **At now:** the strip moves to the new version.
   - **In the past:** the pin stays put and "N newer" updates. Ordinals are stable; pins also carry commit and
     blob, so they re-resolve after a rebuild.
5. **Warm the index early.** After ACE's startup stopwatch ends, during quiet time, sync the launch project scope
   and home. First paint is never delayed (`tui_perf` rule 9). Opening the Memory pane later then finds a warm
   index instead of a 2–19 s cold build.
6. **Keystroke discipline.** Steps use only prefetched data: the ±2 neighbouring versions and the parent
   comparison. Loads go through `spawn_pump_free_task` or thread workers with generation counters, and selection
   is re-read after every `await` (`tui_perf` rules 1, 2 and 4).
7. **Honest by construction.** States come from the timeline wire through the kit's `honest_chip` and `moment`.
   ACE never infers "no history" from a missing response; it says `history unavailable: <reason>`.

### 5.8 Performance budgets

| Interaction | Budget | How it's met |
| --- | --- | --- |
| Memory pane first paint | unchanged | The strip paints `indexing…` or cached data. Loads come after paint. |
| `(`/`)` in the card, warm | p95 < 16 ms key-to-paint (ACE's j/k bar; the pager's is 30 ms) | Prefetched bodies and comparisons plus pure renderers. Checked with `SASE_TUI_PERF=1`; no `tui_stalls.jsonl` rows during rapid stepping. |
| Selecting a note, cold cache | strip within ~200 ms | 150 ms debounce plus one timeline call (about 54 ms today, under 30 ms after `sase-1ee`) |
| Review screen open, warm | under 150 ms to a populated list | One feed call; the detail fills in after it |
| Agents lane chips | never delay the card | Load off-thread in the existing context loader and fill in afterwards |

### 5.9 Keymap and config plumbing

The core gotchas note requires updating every place a key is defined:

- **Memory scope** (`ace.keymaps.memory`): add `history_older: "left_parenthesis"`,
  `history_newer: "right_parenthesis"`, `history_first: "left_curly_bracket"`,
  `history_now: "right_curly_bracket"`, `history_toggle_diff: "equals_sign"` and `history_timeline: "at"`.
  These follow the existing names in `default_config.yml`, such as `files_next_version: "right_parenthesis"`.
- **New `ace.keymaps.memory_changes` scope** for the review screen.
- **Plumbing:** `MemoryPanelKeymaps` (`keymaps/app_keymaps.py`), `_MEMORY_BINDING_META` (`keymaps/metadata.py`),
  `config/sase.schema.json`, the keymap table in `docs/configuration.md`, the conditional footer
  (`build_panel_footer`) and the help modal.
- **Settings, kept minimal:**
  - `ace.memory_history.warm_on_start` (default `true`);
  - `ace.memory_history.review_window_days` (default `30`).

### 5.10 The Rust-core boundary

Apply the litmus test: would another frontend need the same behaviour?

| Piece | Home | Why |
| --- | --- | --- |
| Review watermark state and "N new" | **sase-core** (state schema plus `memory_history_review_*` bindings) | The CLI's `sase memory history` header needs it too (`sase-1e6`). |
| Version for a blob (`resolve` gains `at_blob`) | **sase-core** | `sase memory log` rows need the same lookup (`sase-1e5`). |
| Per-query git cost | **sase-core** (`sase-1ee`) | First-view latency everywhere |
| Moment, pill, scrubber, meaning row, diff body | Python (existing kit) | The `sase-1ef` land decided to keep the moment model in Python until a non-Python frontend exists. ACE is Python. |
| Feed view-model (day grouping, row text) | Python (`sase.memory.history.feed_model`) | Presentation, shared by the pager feed and ACE |
| App caches, change tokens, warm-up | Python (ACE glue) | Event-loop policy |

## 6. Phased plan

| Phase | Scope | Absorbs | Size | Done when |
| --- | --- | --- | --- | --- |
| **P0 Reliability floor** | Fix `H`/`C` with failure toasts. Key-press e2e tests and the `call_from_thread` AST guard. Process-wide `HistoryService` for the provider factory and ACE, with a tip-keyed memo. Public kit module. Palette entry. Correct `docs/memory_history.md` if behaviour moves. | the §1.2 bug | S–M | `H`/`C` open the pager inside ACE from the Admin Center; the e2e tests fail on the old code; pager provider lookups reuse one service; repeated `timeline` calls in one tip are memoized. |
| **P1 Note lens** | Time strip, inline `( ) { } = @`, past frame, pinned `H`, honest states, the publish loop, width shedding, warm-up and change tokens. Remove the History property row. PNG goldens for now, past, diff, dirty, untracked, indexing and narrow, in dark and light. | `sase-1en` (panel half) | M–L | §5.8 budgets measured; goldens reviewed; `just check` green. |
| **P2 Changes review** | `MemoryChangesScreen`, shared `feed_model`, core watermark, sub-tab badge, unread verbs, filter and scope, goldens | `sase-1e6` | L | Every changeset in a 30-day window is reviewable without leaving ACE. Watermark survives restarts and is shared across workspaces. |
| **P3 Agent lens** | MEMORY lane version chips, `AGENTS.md as launched` row, pinned hints, snapshot pseudo-version, core `resolve(at_blob)` | `sase-1e5` (TUI half) | M | From any agent you can open exactly what it read and see whether it has changed since. |
| **P4 Polish** | Restore as unpublished draft from the past card (`sase-1e7`; never for generated subjects). `AGENTS.md` and instruction root row in the note list, with cause rows. Optional "deleted" group. Unreviewed dots on note-list rows. Pending-diff summary in the publish modal. Pager-exit pin flowing back to the card. Revisit embedding `PagerView` after `sase-1eu`. | `sase-1e7` | M | Taken one at a time |

**Sequencing:**

- `sase-1es` (virtualized pager body) and `sase-1eu` (PaneGrid) are in flight inside the pager. P0's kit
  promotion should be thin re-exports, landed after `sase-1es.6`, to avoid merge churn.
- Landing `sase-1ee` before or alongside P1 makes cold-cache strips feel instant. It is not a blocker, because
  ACE's tip-keyed caches hide most of the cost.

## 7. Risks and open questions

**Decisions for you:**

1. **A native review screen, or just a fixed pager feed?** I recommend the native screen (option F). It is the
   part that makes the TUI better than the CLI. If you'd rather keep scope tight, P0 plus P1 alone are a
   coherent "excellent" floor.
2. **How loudly should unreviewed memory changes announce themselves?** I recommend the Admin Center sub-tab badge
   and the review header only. An ACE header chip or an opt-in toast could come later, once you know the volume
   (roughly 3 memory changesets a day).
3. **Should Memory leave the Admin Center?** Not for history's sake. Revisit if P2 sees heavy use.
4. **No audit for history in ACE.** I recommend D10 hold in ACE too: past strand versions are shown without an
   audited read, while the now-view keeps its gate.

**Risks:**

- **Card space** at 120×40 (about 52×15). Mitigations: a two-row strip, fold-in below 14 rows, and `H` always one
  key away.
- **Merge churn with in-flight pager epics.** Mitigation: thin re-exports and sequencing (§6).
- **Unread fatigue.** Mitigation: nothing is ever marked automatically, and `,u` has undo.
- **Agent-lens cost** across many agents. Mitigation: only the selected agent loads, its chips are cached by tip,
  and the card renders before them.

## 8. Evidence appendix

### 8.1 Measurements on this checkout (warm, `HistoryService` in-process)

```text
scope build 40ms · sync 46ms (fresh; 139 subjects, 1186 versions, 51 hidden; upstream_ahead 0)
subjects 31ms · timeline(gotchas) 53ms (25 versions) · timeline(tui) 54ms · repeat 54ms (no memo)
feed(limit=50) 32ms · AGENTS.md subject: 5 alias paths, diverged_count 22
```

### 8.2 Probes

These were throwaway scripts outside the repo, run with an isolated `SASE_HOME`.

- **`H`/`C` probe:** mounted `MemoryPanel` through `AcePage`, injected a fake service, stubbed
  `build_history_document`, spied on `push_screen`, called the actions, then read the worker's state and error
  (§1.2).
- **Geometry probe:** opened the Admin Center at `ConfigHubEntry(subtab="memory")` at 120×40 and rendered it to
  PNG. The rail and the card each measured about 52×15 cells.

### 8.3 Key code references

- **Broken actions:** `src/sase/ace/tui/modals/memory_pane_history.py:189-285` (`H`) and `:287-397` (`C`).
- **History row:** `src/sase/ace/tui/modals/memory_panel_history.py`.
- **Card rendering:** `memory_panel_view.py:172-269` and `memory_panel_rendering.py:361-402`, `:515-562`.
- **Hosts:** `config_hub_catalog.py:76-88`, `actions/agent_workflow/_prompt_bar_memory_panel.py` (`gm`) and
  `tab_order.py:30`.
- **Kit candidates:**
  - `src/sase/pager/history/moment.py`
  - `src/sase/pager/_chrome_history.py` (`pill_forms`, `history_badge`, `honest_chip`, `time_verbs_for_moment`)
  - `src/sase/pager/_time_band_vocab.py:224` (`render_scrubber`)
  - `src/sase/pager/_time_band_render_meaning.py` (`meaning_row`, `cause_row`)
  - `src/sase/pager/history/diff.py:311` (`build_diff_body`)
  - `src/sase/pager/history/styles.py` (`history_styles_for_theme`)
  - `src/sase/pager/_timeline_picker.py:211` and `src/sase/memory/history/timeline_picker.py:101`
- **Service and provider:** `src/sase/memory/history/service.py`, `pager_provider_core.py:444` and
  `pager/history/provider.py:124-146`.
- **PagerView host contract:** `src/sase/pager/view.py:58-94`, `:118`.
- **Agents lens inputs:**
  - `src/sase/ace/tui/widgets/prompt_panel/_agent_memory_reads.py`
  - `src/sase/ace/tui/memory_reads.py:210`
  - `src/sase/axe/launch_evidence.py:248-262`
  - `src/sase/memory/_read_log_models.py:86-87`
- **ACE precedents reused:**
  - deck block rail and arrival dots: `src/sase/ace/tui/widgets/decks/block_rail.py`
  - Files versions with `( )`: `actions/artifacts_files.py:311-319`
  - Artifacts icons and accents: `src/sase/ace/tui/_artifact_tab_model.py`
  - unread verbs: `docs/ace.md`, Agents `U`, `,j`, `,u`
