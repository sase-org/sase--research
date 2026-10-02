# Memory history in the TUI: a time-aware Memory pane

Consolidated report for swarm `research.3c`, 2026-10-02. It merges five independent
reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem` in this directory) with the lead's
own verification on `master` at `8d1ac50c51`. That revision is three commits newer than
the `45f165b6d5` the researchers inspected; none of the three commits touches memory
history. The epic context is `sase-1dr` (closed 2026-10-01) and its approved plan,
`plan:202609/memory_history.md`.

## Decision brief

**Recommendation: make the Memory pane time-aware. Don't build a second pager.**

The left rail chooses *what* you look at. The card shows it *at a moment in time*. The
full-screen pager stays the deep reader, and every hand-off to it carries an exact
version pin, so you never land on "now" after looking at the past.

The design has five parts, ordered by value:

1. **Repair the front door first.** `H` and `C` are broken today: they fail silently on
   every press (verified, §1.1). Fix them, add key-press tests, and fix the History row's
   stale and failed states.
2. **Put time on the card (modeless).** A two-row time strip replaces the History
   property row. It shows the pager's pill, scrubber, and meaning row. `( ) { } =` step
   through and diff versions in place, using the pager's own pure renderers.
3. **Add two rail lenses.**
   - `@` turns the rail into the selected subject's **Timeline**: a list of versions with
     a live preview.
   - `C` turns the rail into a **Changes** review of changesets across subjects.
   - `Esc` returns to **Notes**, exactly where you left it.
4. **Fill in the catalog.** Add a one-glyph recency column to the rail, an
   **Instructions** group for `AGENTS.md` and its shims, and an opt-in **deleted**
   filter.
5. **Bridge from the Agents tab**: show "as seen by this agent" version chips
   (`sase-1e5`). Separately, add a core-owned review watermark to Changes (`sase-1e6`).

Defer three things:

- Embedding `PagerView` in the card, until the pager-body rewrite (`sase-1es`) and the
  PaneGrid split work (`sase-1eu`) land.
- Restore (`sase-1e7`).
- Split or side-by-side diffs inside the pane.

All five researchers agree on what not to build:

- no new top-level tab;
- no second history engine or store;
- no git IO in Python;
- no audit record for viewing history (plan decision D10).

They disagreed on how far in-pane reading should go and where Changes should live. §3
settles each disagreement with evidence.

---

## 1. What exists today (verified)

`sase-1dr` built a complete stack:

- a Rust index in `sase-core`;
- a thread-safe `HistoryService`;
- `sase memory history` (text, JSON, and pager output);
- a modeless pager time axis: pill, time band, scrubber, word diff, `@` picker with
  two-point compare, changes feed, version-pinned trail, and honest states.

The TUI got only a "front door":

- `H` pushes `PagerScreen` at now;
- `C` pushes the feed for every scope in the ring;
- a History row in the card's property grid shows `▁▂▁▅ 9 versions · changed 7d ago ·
  sase-1…`.

The user's instinct is right. **The pager is the only working history surface**, and
the reason is sharper than expected.

### 1.1 `H` and `C` never open anything

Both actions pass a coroutine to `run_worker(...)` without `thread=True`, so it runs on
the app's event loop. After `await asyncio.to_thread(build)`, the coroutine calls
`self.app.call_from_thread(...)` (`src/sase/ace/tui/modals/memory_pane_history.py` lines
244, 278, 362, 390). Textual raises `RuntimeError` when that method runs on the app
thread. The worker uses `exit_on_error=False`, so the error is swallowed. The failure
toast goes through the same call, so it never appears either.

The evidence:

- **Reproduced by two researchers.** `cdx` and `cld` each mounted a pane headlessly and
  pressed the keys. Both got `WorkerState.ERROR` with this message, and no screen was
  pushed.
- **Still on HEAD.** The lead confirmed the code is unchanged at `8d1ac50c51`.
- **Isolated to one file.** The lead's AST scan of `src/sase` found 27
  `call_from_thread` call sites. Only these four sit directly inside an `async def`, and
  all are in this file. `cld`'s count of 55 sites is not reproduced, but its proposed
  lint guard is cheap and fits.
- **No test presses `H` or `C`.** `tests/ace/tui/modals/test_memory_panel_history.py`
  checks bindings, formatting, and footer text only. The History golden injects its
  summary directly.

`grk`, `mus`, and `gem` worked from source reading and missed this; `mus` called the
pattern correct. It is the most important finding of the swarm. Today's "TUI support"
is a launcher that does not launch.

### 1.2 Other verified gaps

| Gap | Evidence |
| --- | --- |
| **The Memory pane's only production host is the Admin Center Config hub.** `gm` / `Ctrl+G m` open its Memory sub-tab. The standalone `MemoryPanel` modal is used only by tests. | `config_hub_catalog.py:76-88` is the only `MemoryPane(` constructor in `src`. `_prompt_bar_memory_panel.py` opens `ConfigHubEntry(subtab="memory")`. `cdx` was wrong that `gm` opens the modal; `cld` was right. |
| **History-row freshness.** A successful summary is never revalidated on refresh. A failed load shows a dim `…` forever. | `_history_renderable_for_node` returns `_history_latest` first. `_history_failed` keeps the placeholder until the scope reloads. Both are in `memory_pane_history.py:76-176`. `cdx` reproduced the refresh case. |
| **Web descriptors have no History row,** although `H` can resolve them. | The comment at `memory_pane_history.py:59` reads "Web descriptor rows carry no History row". |
| **The docs never mention the feature in the TUI guide.** | The Memory panel section of `docs/ace.md` has no mention of `H`, `C`, or the History row. `docs/memory_history.md` still advertises both keys. |
| **`Z` does not open the pager.** It hands the file to the artifact viewer, so it never gets the time axis, contrary to the original plan's assumption. | `docs/ace.md` (Memory panel, "Passive keys"); found by `grk`. |
| **Each pager lookup builds a new `HistoryService`.** The service memoizes only scopes, not timelines. | `memory_history_provider_factory()` calls `HistoryService()`. `service.py` memoizes only `project_scope`/`home_scope`. `gem` was wrong to call the service "memoized". |
| **The Agents tab ignores the captured evidence.** | `blob_oid` / `included_blob_oids` exist on read events (`_read_log_models.py:86-87`), and `workspace_head` / `instruction_snapshot` are captured at launch (`launch_evidence.py`). A grep of `src/sase/ace` finds zero uses. |
| **ACE reaches into a private pager module** for the sparkline. | `memory_panel_history.py:187` imports `sase.pager._time_band`. |
| **No embeddable pager precedent exists in ACE.** | All four ACE call sites push `PagerScreen`. `PagerView.pager_host` returns `self.screen`, which must satisfy `_PagerViewHost` (`paint_footer`, `close_view`, `focus_view`, `focus_other_view`, `show_in_other_view`). |
| **The pager is mid-rewrite.** | Today `sase-1es` phases 5–8 (virtual line model, Line-API `ScrollView` body swap, search, gates) and `sase-1eu` phases 3–8 (PaneGrid deck, pager on PaneGrid, three panes) are all IN_PROGRESS. |

### 1.3 Measurements (lead, warm, this checkout, in-process `HistoryService`)

The checkout has 139 subjects: 102 strands, 29 notes, 4 instruction subjects, 3 webs,
and 1 asset. The feed holds 489 changesets.

| Call | Time | Note |
| --- | --- | --- |
| scope build | 46 ms | |
| `sync` | 33–62 ms | The first call in the session took 3.8 s. |
| `subjects` | 31–36 ms | **Returns every subject with an empty `versions` list** |
| `timeline` (25 versions) | 57–60 ms on every repeat | No memo |
| `version(include_body)` | 39–41 ms | |
| `feed(limit=50)` | 36–48 ms | |
| `feed(limit=None)`, all 489 changesets | 42–44 ms | A per-subject "latest change" map builds from it in 0.5 ms |

These numbers settle three design points:

- **Stepping must use prefetched data.** At about 60 ms per timeline and 40 ms per body,
  a key that waits on the service misses the 16 ms ACE j/k budget and the 30 ms pager
  step budget.
- **The rail glance comes from one `feed()` per scope, not from `subjects()`.** The
  `cdx` claim that `subjects()` returns "all versions" and the `grk` plan to build the
  glance from `subjects()` both fail against the actual payload.
- **Each newly selected note costs about 100–120 ms today,** because the History row runs
  `sync` plus `timeline` per selection. A tip-keyed memo and sync coalescing pay off
  immediately.

### 1.4 Real geometry

`cld` reported a card of about 52×15 cells inside the Admin Center at 120×40. The lead's
headless probe did not reproduce that:

- The Admin Center chrome (title, tab strip, Config sub-tab strip, captions) takes about
  7 rows.
- The note rail is 32–52 columns, set by `_NOTE_RAIL_MIN_WIDTH` / `_NOTE_RAIL_MAX_WIDTH`
  and description length.
- The card gets the rest: about 68–87 columns at 120 wide and about 46–61 at 100 wide.
  More than 20 body rows stay visible at 40 rows.

The probe's container overflowed the screen in the test harness, so treat the heights as
approximate. The design point holds either way:

- the card is a reasonable reading surface, not a postage stamp;
- a third column (files + versions + preview) does not fit at 120 columns;
- at 80 columns the card is only about 46 wide.

## 2. Jobs the TUI should make easy

| Job | Frequency | Today | The design's answer |
| --- | --- | --- | --- |
| "Agents changed memory. What changed, and who changed it?" | Daily (about 3 changesets a day) | CLI only; `C` is broken | **Changes lens**: walk changesets with `j`/`k`, read word diffs and bead/agent/commit chips |
| "When did this rule appear? Why does the note say X?" | Weekly | CLI, or the pager on the file | `( )` on the card; the **Timeline lens** for scanning; `H` for a deep read |
| "Was this always core memory?" | Occasional | Pager | `⇧ reference → core` in the rail glance, the meaning row, and timeline rows |
| "Why did `AGENTS.md` change?" | Occasional | No TUI door | **Instructions group** with cause rows (`⟳ rendered · sources: …`) |
| "Which memory did this agent see?" | Whenever an agent misbehaves | Impossible | **Agents lens**: per-read version chips, plus `AGENTS.md as launched` |
| "Where did that note go?" | Rare | `git log` | **Include deleted** filter with tombstone cards |
| "Undo that change" | Rare | Manual git | Later: restore as an unpublished draft (`sase-1e7`) |

The TUI beats the CLI where a persistent selection, live state, and cross-links matter:
the first job and the agent job.

## 3. Where the reports disagreed, and the resolution

| Question | Positions | Resolution and why |
| --- | --- | --- |
| **How much reading happens in the pane?** | `gem`: port everything in place, including the band, folds, hunks, and splits. `cdx`: embed `PagerView` beside a version rail. `cld`/`grk`: an inline strip and stepping built from pure renderers, with the pager for deep reads. `mus`: no in-card reader at all, only a chooser plus pager deep links. | **Use pure renderers in the card; the pager stays the deep reader.** The pure kit already exists and is Textual-free: `build_moment`, `pill_forms`/`history_badge`, `render_scrubber`, `meaning_row`/`cause_row`, `honest_chip`, `build_diff_body` (returns Rich `Text`), `build_picker_rows`, `history_styles_for_theme`. That makes "same pixels everywhere" cheap and answers `mus`'s drift worry: nothing is re-implemented. Embedding `PagerView` now means adding a host adapter to a widget whose body is being replaced (`sase-1es.6`) and whose host is moving onto PaneGrid (`sase-1eu.6`/`.7`). That is a merge trap with no ACE precedent. `gem`'s full port duplicates search, labels, and fold expansion and conflicts with existing keys. `mus`'s chooser-only answer leaves the card blind and keeps every glance a round trip. |
| **Is plan decision D8 ("modeless; the pager is the reader") violated?** | `mus` treats it as binding. | **No.** D8 says time is an axis of *the document*, with `(`/`)` chosen because they already mean prev/next version in ACE. The Memory card *is* a document view, so modeless `( ) { } =` on it applies D8 rather than violating it. The original plan made the panel a front door because the TUI was out of scope. The user's request reopens that, and the deep reader stays the pager. |
| **Where does Changes live?** | `cld`: a new full-screen `MemoryChangesScreen`. `grk`, `gem`, `cdx`: swap the pane's rail. | **A rail lens inside the Memory pane.** The pane already gets nearly the full Admin Center width (§1.4). A lens reuses the pane's list/detail grammar, scope ring, filter, footer, and help, with no new screen or keymap scope. It keeps one mental model: the rail picks *what*, the card shows *when*. |
| **A visible version list, or only a scrubber plus a modal picker?** | `cdx`: the rail becomes a timeline. `cld`/`grk`/`mus`: `@` pushes a picker modal. | **`@` turns the rail into the Timeline lens.** Inside a pane that already has a list/detail layout, stacking a modal picker over a visible list is redundant (`cdx`). Its rows come from `build_picker_rows`, so the content matches the pager picker exactly. In the standalone pager, `@` keeps its modal. |
| **Default scope for Changes** | `C` currently shows all ring scopes. `grk`: the current scope. `cdx`: keep all, labeled. | **The current scope, plus an `All scopes` entry on the existing `p`/`P`/`Ctrl+P` ring, available only in the Changes lens.** The pane header already names one scope, so defaulting to it is what you'd expect. All scopes stays one key away, with no new binding. A failed or `NO VCS` scope shows as a chip, never silently dropped. |
| **Rail activity glyphs** | `gem`: a one-cell sparkline plus age. `grk`: class glyph plus age. `mus`: glyph, count, and age. | **Class glyph plus compact age, built from one `feed()` per scope.** A one-cell sparkline is noise; the current eight-cell golden already renders as a single blob. Show no counts, because width is scarce. |
| **Unread state** | `cld`: dots, `U`/`,j`/`,u`, and a sub-tab badge. `cdx`: no "unread" until `sase-1e6`. `mus`: an adapter now. | **Ship it with `sase-1e6`,** with watermark state in `sase-core` (the CLI needs it too) and explicit marking only. Opening the lens marks nothing. |
| **New key proposals** | `gem` proposed `.` (tombstones), `Tab` (feed toggle), `[`/`]` (hunks), `\`/`\|` (splits) for the pane. | **Reject them.** `.` is the fixed `.1`–`.9` chip prefix and `Tab` is `next_link`. Hunk navigation and splits belong in the pager (`sase-1eu`). `( ) { } = @` are all unbound in `ace.keymaps.memory`. |
| **Is the card small?** | `cld`: about 52×15. | Not reproduced (§1.4). Keep the strip compact anyway (2 rows, folding to 1) and shed width per the pager's order. |

## 4. The design

### 4.1 Principles

The plan's principles carry over: time is an axis, you always know when you are in the
past, you keep your place, meaning comes before mechanics, and the UI fails open. Add
these for ACE:

1. **The same verbs everywhere.** `( ) { } = @` mean exactly what they mean in the pager
   and the Artifacts Files pane.
2. **The same pixels everywhere.** Every history visual comes from the pager's pure
   renderers, promoted to a public kit module. ACE never formats `vK` itself.
3. **Glance in ACE, read deeply in the pager.** `H` always carries the exact pin:
   subject, ordinal or blob, view, and compare base.
4. **Never block, never lie, never fail silently.** No service call on a keystroke. No
   eternal `…`. Every honest state is shown. A key the user pressed that fails always
   toasts.
5. **The past is read-only.** `o` always edits *now*, and the footer says so.

### 4.2 Lens model

| Lens | Rail shows | Card shows | Entered by | Left by |
| --- | --- | --- | --- | --- |
| **Notes** (today's) | Note, web, and strand tree plus the recency glyph (plus the Instructions group, plus deleted rows when enabled) | The selected subject at the card's pin (now by default) | Default | n/a |
| **Timeline** | The selected subject's versions (`build_picker_rows`) | The cursor version, read or diff, with an optional comparison base | `@`, or clicking the time strip | `Esc` / `@` |
| **Changes** | Changesets for the scope (or all scopes), grouped by day | The selected changeset: provenance plus a diff per authored subject | `C` | `Esc` / `C` |

Leaving a lens restores the Notes cursor, filter, expansion, scroll, and focus from a
session snapshot. The header always names the lens, the scope, and (in Timeline) the
subject.

### 4.3 Notes lens: the time strip and inline stepping

The History property row goes away. A **two-row time strip** sits under the card's path
line for every note, web descriptor, strand, and instruction subject:

- **Row 1:** the pill (`history_badge`, the longest form that fits) and the scrubber
  (`render_scrubber`, with its playhead, diff range, dirty, and tombstone support).
- **Row 2:** the meaning row in the past; the latest change, dimmed, at now; the cause
  row for instruction subjects; or the honest-state chip.

The strip reserves its rows, so loading, failure, and stepping never move the body.
When the card is under about 14 rows, the strip folds to one row. This also completes
the panel half of `sase-1en`.

Here is the card after pressing `(` once. The mockup is illustrative: names, dates, and
counts are placeholders, and a heavy frame stands in for the violet past accent.

```text
 MEMORY · sase · 29 notes · scope 1/3
╭─────────────────────────────────╮┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
│ ● sase              ⟳  1h       │┃ M MEMORY  gotchas                                              sase ┃
│ ● gotchas           ⇧  8d       │┃ sase/memory/gotchas.md @ 1a2b3c4 · Tue Sep 22 2026 14:03           ┃
│ ◆ glossary          ◆  2d       │┃ ▐⟲ PAST · v24 of 25▌ v1 ▁▂▁▃▅▁▇▁▂▃▁▅▇[█]▂ ● now          1 newer   ┃
│ ○ cli_rules         ◆  1mo      │┃ ⇧ reference → core · § Default Keymap Config · +31w −4w · 10d     ┃
│ ○ dispatch          ✚  3mo      │┃ ────────────────────────────────────────────────────────────────── ┃
│ ○ lint_and_test     ◆  1w       │┃▏Default Keymap Config                                              ┃
│ ○ tui               ◆  3d       │┃▏When changing keymaps, leader mode keys, or any configuration      ┃
│ ▸ INSTRUCTIONS  AGENTS.md ≡ 4   │┃▏values, update src/sase/default_config.yml if necessary.           ┃
╰─────────────────────────────────╯┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
 ( v23 · ) v25 · } now · = diff · @ timeline · H open in pager · o edit now
```

**Behaviour**

- **Read view in the past.** The historical body renders through the same `Markdown`
  widget as now, with frontmatter stripped as at now. Past and present therefore look
  identical except for the violet chrome: frame, gutter `▏`, and pill.
- **Diff view.** `=` swaps the body for a `Static` holding `build_diff_body(...)`:
  inline insertions, struck deletions, the frontmatter semantic block
  (`⇧ type: reference → core — now loaded by every agent`), and fixed folds. The choice
  is sticky for the pane session, matching the pager. Expanding folds, searching, and
  following hunks are deep-read verbs and go through `H`.
- **Arrival rules.** Selecting another note shows it at now; small motions never carry a
  pin across subjects. Switching scope (`p`/`P`) resets to now. Opening the pane on a
  note shows it at now in the read view, as the plan's §4.5 arrival rule says.
- **`H` promotes the pin.** It opens `PagerScreen` at the card's exact pin and view.
  From now it behaves as today; from the past it opens that past.
- **Mutations.** While pinned, `e`, `d`, `a`, and `I` refuse with a one-line toast,
  `leave the past to edit · } now`. `o` always opens *now* in `$EDITOR`, and the footer
  reads `o edit now`. Generated subjects stay read-only.
- **Link chips while pinned.** Relations are computed from now, so following one from a
  past card would silently open today's target. Show the chips dimmed, and make `l` or
  `.N` toast `H to follow links at this revision`. The pager already resolves links at a
  past commit.
- **Strands.** Selecting a strand at now keeps today's audited read. Stepping into the
  past writes **no** audit (D10), and a dim `past · not audited` chip appears beside the
  pill. Pin this with a test.
- **`Esc` ladder.** `Esc` first closes an open filter, then returns a pinned card to
  now, then exits a lens, and only then follows the host's close behaviour.

**Strip states**, all in the pager's words:

| State | Strip |
| --- | --- |
| Index building | Dim `indexing…`, with the second row reserved. Steps pressed meanwhile queue, and the last one wins. |
| Clean now | `● NOW · v25` plus `≡ v25 · latest · 1mo ago` |
| Uncommitted | Amber `◌ NOW · uncommitted · on top of v25`. `=` shows the pending edit against HEAD. |
| Untracked / ignored | Amber `UNTRACKED · commit this file to start its history` |
| Home without chezmoi | Dim `NO VCS · home memory is not in git` |
| Home with chezmoi | A `TEMPLATE` chip; history follows the template source (D12) |
| Shallow clone | `SHALLOW · history truncated at <date>` |
| Deleted subject | `✖ DELETED · v12`. The last content is shown, and the notice lives in chrome, never in the body. |
| Failure | `history unavailable · <reason> · r retry`. The last good summary is kept. |

**The publish loop.** This is the moment the design is built around:

1. `e` edits a note, and the strip turns amber `◌ NOW · uncommitted`.
2. `=` shows the pending word diff.
3. `I` publishes.
4. On the next refresh, the strip settles to `● NOW · v26` and a new bar grows at the
   scrubber's right edge.

Durable memory edits become visible without any new concept.

### 4.4 Timeline lens (`@`)

```text
 MEMORY · sase › gotchas · timeline · 25 versions · 3 hidden
╭─────────────────────────────────╮┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
│   now   ≡ v25  clean            │┃ M MEMORY  gotchas                                              sase ┃
│   v25   Sep 30  ◆ § Keys    +6w │┃ ▐⟲ PAST · v24 of 25▌  Δ v23 → v24 · diff                           ┃
│ ▸ v24   Sep 22  ⇧ → core   +31w │┃ ⇧ reference → core · § Default Keymap Config · +31w −4w           ┃
│   v21   Sep 14  ◆ § Keys    +4w │┃ ────────────────────────────────────────────────────────────────── ┃
│   v12   Aug 30  ◆ § Perf   +88w │┃ ⇧ type: reference → core — now loaded by every agent               ┃
│   v1    Jul 02  ✚ created  210w │┃  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 14 unchanged lines ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄               ┃
│   · 3 reflows / moves hidden    │┃ When changing keymaps, [-leader keys-]{+leader mode keys, or any+} ┃
│                                 │┃ {+configuration values+}, update default_config.yml if necessary.  ┃
╰─────────────────────────────────╯┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
 j/k version · = read · b compare base · / filter · . hidden · ⏎ open in pager · esc notes
```

- **Rows** come from `build_picker_rows`: ordinal, date, class glyph, section or summary,
  and word delta. The `now` row and its `≡ vN` alias are always listed, and a hidden
  summary row counts reflows and moves. Long timelines load rows lazily.
- **The highlight moves at once.** The card preview follows through the existing 150 ms
  detail debouncer. While a preview loads, the row reads `loading`, but the card's pill
  keeps naming the content actually on screen. Never paint `v24` over a still-visible
  `v25` body.
- **Comparison.** A committed row previews its change against its parent by default,
  and `=` toggles read and diff. `b` marks a **comparison base**: a `◇` marker on that
  row and a `Compare v8 → v24 · b clear` chip on the card. The pair is always ordered
  older to newer. `now` and `STAGED` are distinct typed endpoints even though both carry
  ordinal 0. Picking the same version shows `Same version`. The base clears when the
  subject or scope changes.
- **`.`** reveals hidden versions, as in the pager picker. In this lens, chip shortcuts
  are inert because the card is pinned (§4.3), so `.` does not collide with the `.1`–`.9`
  chip prefix.
- **Navigation.** Rail motion is preview only and pushes no trail entries. `⏎`/`H` opens
  the pager at the cursor's pin and view, and closing the pager returns you to the same
  lens and row.

### 4.5 Changes lens (`C`)

```text
 MEMORY · sase · changes · last 100 of 489 · 9 regen-only folded
╭─────────────────────────────────╮╭────────────────────────────────────────────────────────────────────╮
│ ━ Today ━━━━━━━━━━━━━━━━━━━━━━━ ││ feat(goals): complete G1 acceptance                                │
│ ▸ 11:03 ✚ decisions:goal-ledger ││ Fri Oct 2 2026 11:03 · 2h ago · sase                               │
│         +2 more           180w  ││ ◈ sase-1bu.7   ⬡ athena.sase-1bu.7   ◉ 1a2b3c4                     │
│   10:41 ◆ dispatch   +44w −10w  ││ ─ ✚ decisions:goal-ledger · new decision · 180w ────────────────── │
│ ━ Yesterday ━━━━━━━━━━━━━━━━━━━ ││   A goal is its own Rust-owned domain, not a bead type…            │
│   18:29 ◆ README      +4w −4w   ││ ─ ◆ glossary:goal · § Definition · +20w −3w ────────────────────── │
│   14:19 ⇧ gotchas  ref → core   ││   A goal is a [-durable-]{+host-bound+} unit of intent that…       │
│ ━ Mon Sep 28 ━━━━━━━━━━━━━━━━━━ ││ ⟳ AGENTS.md §3.1 · README.md · shims regenerated                   │
│   ⋯ 5 regenerated-only          ││                                                                    │
╰─────────────────────────────────╯╰────────────────────────────────────────────────────────────────────╯
 j/k changeset · ⏎ open in pager (diff) · p/P scope · / filter · r refresh · esc notes
```

**The list**

- One row per changeset: time, class glyph, first authored subject plus `+N more`, a
  right-aligned word delta, and `⌂` for home.
- Day rules (`Today`, `Yesterday`, `Mon Sep 28`) are chrome, not rows.
- Changesets that only regenerate files collapse into one count line, as the feed
  already does.

**The card**

- The commit subject, absolute and relative time, and scope.
- Provenance chips that reuse the Artifacts tab's icons and accents: `◈` bead, `⬡`
  agent, `◉` commit. Memory changes then look like part of the same artifact family.
- One titled section per authored subject, rendered with `build_diff_body` and minimal
  context.
- One `⟳` line folding the generated consequences.

**Keys and loading**

- **Opening.** `⏎`/`H` opens the focused subject at that changeset's version in the
  pager's diff view (the feed's arrival rule). `.1`–`.9` pick a subject when a changeset
  has several.
- **Scope.** The current scope is the default. `p`/`P`/`Ctrl+P` cycle the ring, which
  gains an `All scopes` entry in this lens only. A scope that fails or is `NO VCS`
  appears as a header chip, never silently dropped.
- **Bounded loading.** A full `feed()` costs only about 43 ms for 489 changesets, so the
  bound exists for render cost, not query cost. Render the newest 100 and say
  `last 100 of N`. Add more on demand, and apply the filter to the loaded window.
  - `feed()` has no continuation cursor. Batch by limit and deduplicate by
    `(scope, commit, subject, ordinal)`.
  - If a real cursor is ever needed, it belongs in `sase-core`, pinned to per-scope tips.
    Never fake one from timestamps.
- **Shared view-model.** Extract the day grouping, row text, and regen folding into a
  pure `sase.memory.history.feed_model`. The pager's `build_feed_document` and this lens
  then share it and cannot disagree (`cld`).
- **Review watermark (`sase-1e6`, later phase).**
  - A `● N new` header and an explicit "mark reviewed" action.
  - Optionally a `05 MEMORY ●N` badge on the Config sub-tab.
  - State lives in `sase-core`, keyed per scope rather than per workspace clone.
  - Never marks anything automatically.

### 4.6 Rail glance, Instructions, deleted subjects

- **Recency column.** Each rail row ends with its newest **class glyph and compact age**
  (`⇧ 8d`, `◆ 3h`, `⟳ 1h`).
  - Source: one `feed(scope, limit=None)` per scope load and on refresh. That is 43 ms
    off-thread, and the map builds in 0.5 ms.
  - Shed the age first, then the glyph; never wrap the stem.
  - Promotions `⇧`/`⇩` keep their highlight, because they change what every later agent
    loads.
  - Show the dirty `◌` only where it is already known, for example the selected
    subject's timeline state. Never stat files per row.
- **Instructions group.** Add a synthetic, collapsed `INSTRUCTIONS` group, built from
  `subjects()` entries of kind `instructions`. This repo has four: the root `AGENTS.md`,
  `demos/tapes`, `src/sase/ace`, and `tools`.
  - Identical shims alias into one row; diverged shims (`diverged_count` > 0) show
    `⚠ diverged`.
  - Home sources carry `TEMPLATE`.
  - The strip shows cause rows. The rows are read-only, and `H`/`( )`/`@` work as for
    notes.
- **Deleted subjects.** An "include deleted" toggle lists tombstoned subjects. The key is
  a panel binding, not `.`.
  - **Source:** the same per-scope `feed()`. It carries `deleted`-class entries: 22
    entries across 21 subjects in this repo.
  - **Only current tombstones:** keep a subject only when its *latest* entry is a
    deletion. Some subjects were deleted and later recreated; for example, the root
    instructions subject has a `deleted` entry.
  - A tombstone card shows `✖ DELETED`, the deletion date and provenance, and the label
    "last content before deletion". It never calls that content `now`.

### 4.7 Agents lens (`sase-1e5`, TUI half)

```text
┌─ Context ────────────────────────────────────────────────┐
│ MEMORY  4 reads · 3 files · AGENTS.md as launched        │
│   ◇ AGENTS.md          v258 ⟲ 2 newer since launch   [2] │
│   10:02 ◇ gotchas        v25 ≡ now                   [3] │
│   10:04 ◇ dispatch       v12 ⟲ 2 newer               [4] │
└──────────────────────────────────────────────────────────┘
```

- **Chips.** Each audited read gets a chip derived from its `blob_oid`: dim `≡ now`, or
  past-accent `⟲ N newer`. The second is often exactly what you are debugging. Batch
  reads show one chip per entry in `included_blob_oids`.
- **Launch row.** A new first row, `AGENTS.md as launched`, resolves
  `instruction_snapshot` and falls back to `workspace_head`. If the bytes match no
  committed blob (a dirty checkout or a per-host render), open the stored snapshot as an
  honest pseudo-version, `◌ as launched · not in git`. Say `Snapshot unavailable` when
  the bytes are gone. Never substitute "the nearest commit before the timestamp".
- **The hint** opens the pager pinned to that version in the read view. From there, `}`
  goes to now and `=` diffs.
- **Core work.** This needs a blob-to-version lookup in `sase-core` (for example
  `resolve(at_blob)`), which `sase memory log` also needs. Chips load in the existing
  off-thread context loader and never delay the card.

### 4.8 The visual system

Beauty here means **the pager's language at catalog scale, with restraint**. The plan
already paid for this vocabulary; ACE should not invent a second one.

- **One palette.** `history_styles_for_theme(app.theme)` supplies the violet past accent,
  kept at least 60° in hue from amber; the insert and strike-through styles; pill pairs;
  and the scrubber ramp. Amber means only uncommitted or unpublished. Switching themes
  repaints. Text contrast is at least 4.5:1, and colour always has a matching glyph or
  label.
- **The past frame.** While pinned, the card border takes the past accent. This mirrors
  the pager's `history_past-frame` golden. It is the strongest "you are in the past"
  signal, and it costs zero rows.
- **No layout jumps.** The strip reserves its rows, and every state renders inside them.
- **One glyph table.** `✚ ◆ ⇧ ⇩ ▣ ⟳ ⚙ ≈ ↦ ✖ ◌ ⇡N` come only from
  `sase.memory.history.vocabulary`.
- **Typography.**
  - Subject names bold; secondary text uses the theme's secondary foreground, not bare
    `dim`, wherever it carries state.
  - Word deltas right-aligned so the eye can scan the numbers.
  - Relative day names in lists; absolute timestamps on the card.
  - Meaning first, then bead or agent, then SHA.
- **Width shedding**, in the pager's order:
  - Row 2 drops the bead or agent, then the age, then the section path.
  - Row 1 shortens the pill to `⟲ v24/25`, then `⟲ v24`, and keeps at least 8 scrubber
    cells.
  - Absolute dates appear only on the path line and are dropped first.
  - Below about 50 usable card columns, a lens shows one region at a time: the list, then
    a full-width preview.

### 4.9 Keys

The new bindings go in `ace.keymaps.memory`. All are free there today.

| Key | Action | Lens |
| --- | --- | --- |
| `(` / `)` | Older / newer version (hidden versions skipped; `)` from the newest goes to now) | Notes card, Timeline |
| `{` / `}` | First version / now (the tombstone for a deleted subject) | Notes card, Timeline |
| `=` | Toggle read and diff (sticky) | All |
| `@` | Open or close the Timeline lens | Notes |
| `H` | Open the pager at the exact pin and view (**changed**: previously always now) | All |
| `C` | Open or close the Changes lens (**changed**: previously pushed the pager feed) | Notes, Changes |
| `b` | Set or clear the comparison base | Timeline |
| `.` | Reveal hidden versions | Timeline (chips inert there) |

The precedent is already there: `files_next_version`/`files_prev_version` and
`next_card_block`/`prev_card_block` already use `( )`.

Plumbing follows the gotchas note: `MemoryPanelKeymaps`, `_MEMORY_BINDING_META`,
`src/sase/default_config.yml`, `config/sase.schema.json`, `docs/configuration.md`, the
conditional footer, and the help modal. A `Time` group in `?` adds the pill legend.
`docs/ace.md` gets a "History in the Memory pane" subsection.

## 5. Reliability and performance

1. **Fix the entry points correctly.** Inside the async worker, `await
   asyncio.to_thread(build)`, re-check selection, scope, and mount state, then call
   `push_screen` or `notify` directly; the coroutine is already on the loop.
   Alternatively, use `thread=True` with `call_from_thread`. Do not mix the two
   conventions.
   - Add headless key-press tests from the Config hub host. They must fail on today's
     code.
   - Add an AST lint that rejects `call_from_thread` lexically inside an `async def`
     under `src/sase/ace/tui`. Exactly four sites fail it today.
2. **One app-scoped service, `AceMemoryHistory`.**
   - Holds one `HistoryService`, also handed to the pager provider factory so lookups
     stop rebuilding it.
   - A timeline memo keyed by `(scope, subject, index tip)`; blob-keyed body LRUs and
     blob-pair-keyed comparison LRUs, all bounded.
   - Sync coalescing: one in-flight sync per scope, and the last request wins.
3. **Freshness.**
   - Revalidate on `r`, after publish, after returning from the editor, and when the
     scope inventory changes. Use stat-only change tokens (HEAD, ref, `packed-refs`) on
     idle ticks (`tui_perf` rule 14).
   - At now, the strip advances to the new version.
   - In the past, the pin holds and `N newer` updates. Pins carry commit and blob, so
     they re-resolve after an index rebuild.
   - Pseudo-versions carry content digests. If those drift, mark the preview `stale` and
     recompute; never swap bytes under an unchanged label.
4. **Keystroke discipline.** Steps use only prefetched data: ±2 neighbouring bodies and
   the parent comparison. Loads run through `spawn_pump_free_task` or thread workers
   with generation counters. Selection is re-read after every `await`; cancelling a
   worker is not enough (`tui_perf` rules 1, 2, 4, and 7).
5. **Warm the index quietly.** After ACE's startup stopwatch ends, sync the launch
   project scope and home during quiet time, so the first `H` never pays for a cold
   index (2.3 s documented; 3.8 s seen in this session). First paint must not wait on
   it (rule 9).
6. **Honest by construction.** States come from the timeline wire through `moment` and
   `honest_chip`. A missing response becomes `history unavailable: <reason>`, never
   "no history".
7. **Budgets.**
   - Pane first paint: unchanged.
   - `j`/`k` key to paint: p95 under 16 ms (`SASE_TUI_PERF=1`).
   - Warm `(`/`)` step: p95 within the pager's 30 ms.
   - Cold note selection: strip within about 200 ms (the 150 ms debounce plus one
     memoized timeline).
   - Changes lens open, warm: populated within 150 ms.
   - Zero `tui_stalls.jsonl` rows during rapid stepping.
   - Landing `sase-1ee` (about 9 git spawns per warm query) helps but does not block.

## 6. Architecture and the Rust boundary

```text
sase-core (index, classes, prose diff, feed; later: review watermark, resolve-at-blob)
        │  PyO3, GIL released
HistoryService ──► AceMemoryHistory (app-scoped: memo, LRUs, sync coalescing, tokens, warm-up)
        │                │
        │     ┌──────────┼──────────────┬────────────────────┐
        │   Notes card   Timeline lens  Changes lens         Agents lens
        │   strip+steps  picker rows    feed_model rows      read/launch chips
        │     └──────────┴──── public pure kit (sase.pager.history.kit) ─────┘
        └──► pager provider (shared service) ──► PagerScreen  ◄── exact VersionPin from every door
```

| Piece | Home | Why |
| --- | --- | --- |
| Review watermark state, `N new` | `sase-core` | The CLI feed header needs it too (`sase-1e6`) |
| Blob → version lookup | `sase-core` | `sase memory log` rows need it too (`sase-1e5`) |
| Per-scope feed diagnostics, a future feed cursor | `sase-core`, only when needed | A web or editor frontend would need the same semantics |
| Per-query git cost | `sase-core` (`sase-1ee`) | Latency everywhere |
| Moment, pill, scrubber, meaning row, diff body, picker rows | Python, the existing kit made public | `sase-1ef` kept the moment model in Python; the consumers are Python |
| `feed_model` (day grouping, row text) | Python, shared | Presentation shared by the pager feed and the lens |
| Caches, tokens, warm-up, lenses, keys | ACE | Event-loop and presentation policy |

**The kit.** Re-export the pure helpers from one public module (`sase.pager.history.kit`
or similar). Make the re-exports thin, and land them after `sase-1es.6` to avoid churn.
ACE then stops importing `sase.pager._time_band`, and Symvision can enforce "same pixels
everywhere".

**Embedding `PagerView` is deferred, not rejected.** Once `sase-1es` and `sase-1eu`
land, it can upgrade the card's read view with search, labels, historical link
following, and fold expansion. It would need an explicit host injection seam: a
host-adapter protocol with the screen as the default host. Revisit it only if the card
plus `H` proves too shallow in use.

**Flags.** Phase 1 is a bug fix and needs no flag. Each later phase should ship
complete. Per the flags convention, add a `beta` flag only if the planner splits a phase
so that half a lens would reach users; create it with `sase flag new`.

## 7. Phased plan

| Phase | Scope | Absorbs | Size | Done when |
| --- | --- | --- | --- | --- |
| **1. Trust floor** | Fix `H`/`C` with failure toasts; key-press tests from the Config hub; the AST guard; History-row revalidation and a settled `unavailable · r retry`; web descriptors get history; `AceMemoryHistory` plus the provider factory sharing one service with a tip memo; the public kit; `docs/ace.md` section | the §1.1 bug | S–M | `H`/`C` open from the Admin Center; the tests fail on the old code; repeated timeline calls are memoized |
| **2. Time on the card** | The strip (replacing the History row); `( ) { } =`; read and diff bodies through the kit; the past frame; `H` at the pin; mutation and link guards; strand no-audit; warm-up and change tokens; goldens | `sase-1en` (panel half) | M–L | §5 budgets measured; goldens reviewed in dark and light at 120×40 and 80×24, including Admin Center embedding |
| **3. Lenses** | Timeline lens (picker rows, base compare, lazy rows); Changes lens (`feed_model`, scope ring plus All, provenance chips, bounded rows); session restore | | L | Every changeset in the window is reviewable, and any version comparable, without leaving ACE |
| **4. Catalog completeness** | Rail recency glyphs; Instructions group; include-deleted toggle | | M | Every subject the index knows is reachable from the pane |
| **5. Agents lens** | Per-read chips, the launch row, pinned hints, the snapshot pseudo-version, core resolve-at-blob | `sase-1e5` (TUI half) | M | From any agent, open exactly what it read and see whether it has changed since |
| **6. Review watermark** | Core watermark, `● N new`, explicit mark-reviewed, optional sub-tab badge | `sase-1e6` | M–L | The watermark survives restarts and is shared across workspace clones |

Phases 4 and 5 touch different files and can run in parallel with phase 3. If only two
phases ship, ship 1 and 2. Together they turn a broken launcher into "the Memory pane
knows about time." `grk` argued for pairing phase 1 with the agent lens instead. That
has the highest debugging value per line, so it is a reasonable reordering if agent
debugging is the more pressing pain.

**Out of scope:**

- restore as an unpublished draft (`sase-1e7`);
- the age lens (`sase-1e8`);
- a plain git-file provider (`sase-1e9`);
- `path@rev`, side-by-side diffs, and per-host home rendering (`sase-1ea`);
- in-pane splits, because pager splits belong to `sase-1eu`.

## 8. Acceptance checks

- `H`, `C`, `@`, `(`, `)`, `=`, and `b` all work from the Admin Center-embedded pane. A
  build failure toasts, and moving the selection, switching scope, or hiding the hub
  during a slow build never opens a stale screen.
- A commit made while the pane is open appears after `r` or a token tick. A pinned card
  keeps its exact version and shows `N newer`.
- During rapid stepping, the highlight moves at once, the pill and body never disagree,
  and no other subject's bytes ever appear.
- `now` and `STAGED` rows (both ordinal 0) stay independently selectable.
- Renamed, deleted, and recreated subjects and diverged shims keep the right identity.
  Shallow, `NO VCS`, and `TEMPLATE` states stay explicit.
- Viewing a past strand writes no `memory_reads.jsonl` event; selecting it at now still
  does.
- Pinned link chips refuse and point to `H`. `o` always edits now.
- Golden coverage, in dark and light at 120×40 and 80×24, Admin Center embedded:
  - card at now, past, diff, dirty, untracked, indexing, unavailable, and tombstone;
  - the Timeline lens, with and without a base;
  - the Changes lens;
  - the Instructions group;
  - the agent chips.

  Review new and changed goldens by group. Generating a golden is not approving it.
- `sase tool run check` passes. `check-full` runs only when asked.

## 9. Risks and open questions for Bryan

1. **The Changes lens or a full-screen review screen?** The lens is recommended (§3). If
   Changes becomes a daily ritual and the Admin Center feels cramped, the shared
   `feed_model` makes promoting it to its own screen cheap.
2. **How loud should unreviewed changes be?** Recommended: the lens header plus an
   optional sub-tab badge, and no toasts. At about 3 changesets a day, louder signals
   would be noise.
3. **Should Memory leave the Admin Center?** Not for history's sake. Revisit if the
   lenses see heavy use; `gm` already makes it one chord away.
4. **Merge churn with the in-flight pager epics.** Mitigation: thin kit re-exports after
   `sase-1es.6`, and no `PagerView` embedding until both epics land.
5. **Key load in the pane.** The pane gains 8 bindings, all punctuation and all
   consistent with the pager. The Timeline-lens `.` relies on chips being inert there;
   if that ever changes, rebind it.

## 10. Evidence ledger

- **The five member reports in this directory.**
  - `cdx` and `cld`: the `H`/`C` reproductions; `cdx`: the refresh-invalidation probe;
    `cld`: warm timings.
  - `grk`: the `Z` artifact-viewer finding and the `docs/ace.md` omission.
  - `mus`: the constraint inventory and the case against a second reader.
  - `gem`: the tombstone and agent-bridge framing.
- **Lead verification on `8d1ac50c51`.**
  - Source: `memory_pane_history.py`, `memory_panel_history.py`, `config_hub_catalog.py`,
    `_prompt_bar_memory_panel.py`, `app_keymaps.py` and `default_config.yml`
    (`ace.keymaps.memory`), `pager/view.py` (`_PagerViewHost`),
    `pager/history/{diff,moment,styles}.py`, `memory/history/{service,timeline_picker}.py`,
    `pager_provider_core.py`, `_read_log_models.py`, `launch_evidence.py`, and the Memory
    panel section of `docs/ace.md`.
  - An AST scan of `call_from_thread` inside async functions.
  - In-process `HistoryService` timings and payload inspection (§1.3).
  - A headless Admin Center geometry probe (§1.4).
  - Visual inspection of the `memory_panel_history_dark_120x40` and
    `history_past-frame_dark_120x40` goldens.
  - Bead status of `sase-1dr`, `sase-1es`, `sase-1eu`, `sase-1en`, `sase-1e5`,
    `sase-1e6`, `sase-1e7`, and `sase-1ee`.
  - Plan decisions D1–D15 and §4.8 / §16 / §18 of `plan:202609/memory_history.md`.
  - The `tui_perf` and `sase_flags` memory notes.
- **External** (cited by `cdx`): the Textual worker guide and the
  `App.call_from_thread` contract; VS Code's file-timeline and select-for-compare
  pattern; W3C use-of-colour and contrast guidance.

## Recommended solution

**Build a time-aware Memory pane on the pager's pure renderers, and keep the pager as
the deep reader:**

1. **Fix `H`/`C` now.** They have never opened anything. Add the key-press tests, the
   `call_from_thread` guard, and honest History-row states.
2. **Replace the History row with a two-row time strip** (pill, scrubber, meaning or
   honest state), and make `( ) { } =` step and diff the card in place, behind a violet
   past frame. `H` opens the pager at that exact pin. `o` always edits now, and the past
   is read-only and never audited.
3. **Add two rail lenses.** `@` gives a Timeline of versions with live preview and an
   explicit comparison base. `C` gives a Changes review grouped by day, with provenance
   chips, per-subject word diffs, and the current scope by default (All scopes on the
   ring). `Esc` always returns to the same note.
4. **Complete the catalog** with a recency glyph per row (one `feed()` per scope), an
   Instructions group, and an opt-in deleted filter.
5. **Bridge from the Agents tab** with as-seen version chips and an `AGENTS.md as
   launched` row (`sase-1e5`). Then add a core-owned, explicit review watermark to
   Changes (`sase-1e6`).
6. **Back it with one app-scoped history service:** tip-keyed memos, bounded LRUs, sync
   coalescing, stat-only change tokens, quiet-time warm-up, and generation-guarded
   workers. Promote the kit to a public module, and defer `PagerView` embedding until
   `sase-1es` and `sase-1eu` have landed.

This is intuitive because it uses ACE's existing version verbs on the surface where
memory already lives. It is reliable because it adds no new engine, no git IO in
Python, no blocking keys, and no silent failure. It is beautiful because it speaks the
pager's proven visual language at catalog scale. Each phase ships value on its own.
