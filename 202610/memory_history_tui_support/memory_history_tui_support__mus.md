# Memory history in the TUI: design research and recommendation

Researcher: mus (`__mus`) — independent report in a 5-researcher swarm.
Date: 2026-10-02. Epoxy context: epic `sase-1dr` (Memory history) is landed/closed;
the pager is today the only full reader of memory history.

Methodology note: I did not open, read, or consult any peer swarm report
(`__cdx` / `__cld` / `__grk` / `__gem`). I listed the output directory only to
pick a non-colliding filename. All conclusions below are my own, drawn from the
epic bead, the plan `plan:202609/memory_history.md`, `docs/memory_history.md`,
`docs/pager.md`, `docs/memory.md`, the `HistoryService` / pager-provider / feed /
timeline-picker sources, and the live `MemoryPane` TUI code.

## 1. Question asked

Add excellent support for the recently added memory-file history functionality to
the TUI. The pager is believed to be the only surface that supports memory
history today. Lead the design: intuitive, reliable, and beautiful. End with a
recommended solution.

## 2. What "memory history" actually is (v1, as landed)

- **Scope:** every committed version of every SASE memory note, web descriptor,
  strand, and agent instruction file (`AGENTS.md` + provider shims, project and
  home). Git is the only store. A disposable incremental metadata index in
  `sase-core` provides speed; Python owns presentation.
- **Subject identity survives renames** (`note:` / `web:` / `strand:` /
  `instructions:` / `asset:`-listed-only). Shims alias into their `AGENTS.md` by
  blob equality; only diverged shims show separately.
- **Versions** carry ordinal (`v1` oldest), commit, times, path + blob OID at that
  commit, change kind/class, summary, provenance (agent, bead, subject line), and
  cause for instruction files. Pseudo-versions: `STAGED` (rare) and live `now`
  (`● NOW` clean vs `◌ NOW · uncommitted` dirty).
- **Changeset** = one commit's versions across subjects; the unit of the feed.
  Generated consequences fold under authored causes; regen-only changesets
  collapse.
- **Glyph vocabulary** (shared across CLI, band, picker, feed, Memory panel):
  `✚` created, `◆` authored edit, `⇧`/`⇩` type promote/demote, `▣`
  frontmatter-only, `⟳` regenerated/rendered, `⚙` config/renderer/regen-only,
  `≈` reflow (hidden), `↦` move/rename (hidden), `✖` deleted (tombstone), `◌`
  uncommitted (amber), `⇡N` ahead-on-remote marker. Hidden versions are skipped
  while stepping but never renumbered.
- **Query surface:** `sase memory history [SELECTOR] [-a] [-A REV] [-d]
  [-f {json,pager,text}] [-l N] [-p REF] [-s DATE] [-S {all,home,project}]`.
  No selector = cross-file changes feed. `-f json` emits the Rust wire unchanged
  for agents. Viewing history never writes an audited read.
- **Explicit non-goals deferred to follow-ups** (all beaded, all READY): as-seen
  UI (`sase-1e5`), feed review watermark (`sase-1e6`), restore-as-draft
  (`sase-1e7`), age lens (`sase-1e8`), plain git-file provider for
  plans/skills/xprompts/research (`sase-1e9`), `path@rev` / side-by-side /
  per-host home (`sase-1ea`), commit-graph doctoring (`sase-1eb`), decisions
  strand (`sase-1ec`), skill text (`sase-1ed`). Any TUI design must not
  re-scope these; it should leave clean hooks for them.

## 3. What the pager does today (the bar to match)

The pager is a complete, goldened time machine — this is why "just port it to
the TUI" is expensive:

- **Modeless punctuation time axis:** `(` / `)` step versions (hidden skipped;
  `)` from newest returns to now), `{` first / `}` now-or-tombstone, `=` sticky
  read/diff switch, `@` timeline picker, `[` / `]` prev/next change. Small
  motions push nothing onto the trail; jumps (picker, feed links, band links,
  links from a past version) push version-pinned trail entries so Backspace
  returns to the exact moment.
- **Subject-line state pill** (never cropped; steps through shorter fixed forms
  as width shrinks): `● NOW · v25` / `◌ NOW · uncommitted` / `⟲ PAST · v24 of
  25` / `✖ DELETED · v12`, plus dim context (`latest · 1mo ago`, `on top of
  v25`, violet age, `Δ v23 → v24` older→newer). Past versions gain a violet
  gutter rail; deleted subjects show a tombstone row in chrome and exact last
  content in the body so line numbers still match.
- **`#pager-time` band:** now = one-row life strip; past = timeline row
  (playhead scrubber with log-scaled `▁▂▃▄▅▆▇█` cells, absolute date, `vK`,
  newer-count, `⇡N`) + meaning row (class glyph, section path, word delta,
  frontmatter semantics, bead/agent/SHA jump labels). Instruction subjects get
  a cause row (`⟳ rendered · sources: …`, `⚙ config change`, `⚙ regenerated`,
  `◆ hand-edited`, `≡`/`⚠ diverged` chip). Shedding order is specified; at ≤12
  rows the band folds and the pill gains the short date. Chrome never pushes
  the body.
- **Timeline picker (`@`):** aligned non-wrapping table, `●` open / `▸` cursor
  markers, `now` + `≡ now` alias always listed, hidden-summary row, `⏎` open,
  `=` two-point compare (always older→newer), `.` hidden toggle, `/` filter
  over section/agent/bead/words, lazy rows for long timelines.
- **Diff view (`=`):** inline word insertions + struck-through deletions,
  reflow-insensitive word diffing, frontmatter semantic block, in-place fold
  expansion. Default base = parent version (worktree-vs-HEAD when dirty);
  picker/feed/cause/`-d` arrivals open diff, note/panel/plain arrivals open read.
- **Changes feed:** one section per day, authored subjects as labels opening
  `subject@version` in diff, folded consequences, collapsed regen-only counts,
  `⌂`-tagged home interleaving, `r` resync.
- **Honest states everywhere:** `UNTRACKED`, `IGNORED`, `NO VCS`, `SHALLOW`,
  `TEMPLATE`, `indexing…`, `history unavailable: <reason>` — always visible,
  fail open to the live document. Past links resolve at that revision or say so;
  never silently fall back to today.

Verified live: `sase memory history --help` exposes the full selector/option
surface above (flat names, repo-relative paths, `web:keyword`, instruction
paths, historical names; `-a/-A/-d/-f/-l/-p/-s/-S`).

## 4. What the TUI does today (the actual gap)

The claim "the pager is the only thing that supports memory history" is
*nearly* true, with one narrow exception. The TUI has exactly this:

1. **`H` — open selected note/web/strand in the pager at now**
   (`MemoryPaneHistoryMixin.action_open_history` → `build_history_document(
   scope, subject, initial_revision="now", view="read")` → `push_screen(
   PagerScreen(...))`). Selectors come from the rail node (notes by
   repo-relative path, strands as `web:slug`), scopes from the panel scope ring
   (`content_root`, never CWD). Async `asyncio.to_thread` build with
   selection-identity + scope-key staleness guards.
2. **`C` — open the cross-file changes feed** (`action_open_changes` →
   `service.feed(scopes, …)` → `build_feed_document` with a feed-aware
   `_resolve_ref` / `_refresh` closure → pager). Scopes = enabled ring entries
   via `history_scopes_for_ring`.
3. **History card row** in the note card (`memory_panel_rendering.py` appends a
   `("History", history)` row): per-selection summary via `fetch_history_summary`
   (sync + `timeline(include_hidden=True)`), rendered as text + an 8-cell
   sparkline (`render_sparkline` reuse), off-thread with `…` placeholder,
   `(scope, subject, tip)`-keyed cache, fail-open `None`, amber `yellow` for
   untracked/ignored, `dim` for loading/unavailable. Web-descriptor rows
   deliberately carry no History row (only notes and strands).
4. **Keymap/config wiring:** `memory.open_history = "H"`, `memory.open_changes
   = "C"` in `default_config.yml` (+ schema + help modal + footer hints).

That is the whole TUI surface. Consequences:

- Every real history interaction (step, diff, picker, feed follow, band links)
  ejects the user from the TUI modal into a fullscreen pager and back. Context
  (rail position, scope ring, filter, card state) is preserved only by luck of
  the screen stack, not by design.
- The Memory pane list itself is history-blind: no age, no version count, no
  dirty/ahead/stale signal at the row level. You must select each note and read
  the card row to learn it even has history.
- No TUI path exists for: instruction-file history (`AGENTS.md` at a project
  root or home), as-seen-at-launch (`sase-1e5` evidence is captured but
  unconsumed), review watermark (`sase-1e6`), restore (`sase-1e7`), age lens
  (`sase-1e8`), non-memory git files (`sase-1e9`), or home `NO VCS` guidance
  beyond a missing scope.
- Discoverability is weak: two letters + one card row, no footer preview of
  what `H`/`C` will open, no empty-state teaching ("this note has 1 version —
  history will grow as it is committed").

## 5. Constraints any design must respect

- **Rust boundary (litmus-tested):** `sase-core` owns index semantics + git IO
  (`prose_diff`, `file_history`, memory-history cache/query bindings, all
  GIL-releasing). Python/TUI owns presentation. The TUI must query only through
  `HistoryService` (`timeline` / `get_version` / `compare` / `feed` /
  `resolve_subject`), never spawn git itself. No new backend belongs in this
  repo.
- **Event-loop discipline:** every `HistoryService` call off the pump
  (`run_worker(thread=True)` / `asyncio.to_thread`), first paint unchanged,
  `indexing…`-style placeholders, generation/identity guards against stale
  worker overwrites (the current code already models this — keep the pattern).
  Warm step p95 ≈ 6 ms / 30 ms target is a pager number; the TUI equivalent is
  "selection → History row paints from cache, never blocks the rail."
- **Fail-open honest states:** any error → placeholder + live document, never a
  crash or a blocking spinner. `NO VCS` (home without chezmoi-git), shallow,
  untracked/ignored, template, and `history unavailable` each keep their chip;
  the TUI must render all of them, not just the happy path.
- **Keymap + config + schema + help contract:** new bindings go in
  `MemoryPanelKeymaps`, `default_config.yml`, the JSON schema, and
  `MemoryPanelHelpModal` together (cf. gotchas note on `default_config.yml`).
  Punctuation-only for time motions (jump-label alphabet is letters/digits).
- **Visual goldens + perf harness:** rendered TUI changes need PNG goldens
  (`tests/ace/tui/visual/…`, `just fix-tui-screenshots`; exact pixel equality;
  check-only in CI) and must not regress `SASE_TUI_PERF`/`SASE_TUI_TRACE`
  budgets. Pager history goldens already exist — reuse their fixtures where
  possible rather than inventing a second visual language.
- **"Pager is where history is read" is a decided constraint (D-plan §5), not
  just a habit.** Overturning it needs a real argument, not convenience. The
  design below deliberately keeps it: the TUI previews and routes; the pager
  reads.

## 6. Options considered

### Option A — Pager deep-link expansion only (cheapest, weakest)

Add `H`/`C`-style "open in pager at the right version" everywhere memory
appears in the TUI: agent detail (launch snapshot → `AGENTS.md@snapshot`,
`sase-1e5`), memory-log/glossary/agent-chat rows (exact version read), config
hub memory entries, instruction-file rows, bead/xprompt surfaces that cite
memory. No new TUI rendering; all reading stays in the pager.

- *Pros:* tiny; reuses every golden; honors the "single place" decision; each
  link is independently shippable; directly unblocks `sase-1e5`-class flows.
- *Cons:* context loss on every use; list-level blindness remains; feed has no
  home in the TUI (no watermark, no badge); discoverability barely improves;
  "excellent" is overselling — this is "adequate plumbing."
- *Verdict:* necessary but not sufficient. Do its highest-value links anyway
  (see recommendation), but do not stop here.

### Option B — Full TUI-native history reader (strongest, riskiest)

Port the time axis into the TUI: a history-capable document viewer with pill,
band, scrubber, picker, and diff, either inside `MemoryPane` or as a new modal.
Read without ever pushing `PagerScreen`.

- *Pros:* zero context loss; could be genuinely beautiful if done well.
- *Cons:* duplicates the most intricate rendering in the codebase
  (pill/step-forms, shed order, scrubber bucketing, picker table, word-diff
  folds, tombstone semantics, violet-vs-amber discipline, theme palette) —
  two readers to keep pixel-identical across dark/light, widths, and heights;
  doubles golden + perf burden; directly contradicts the landed D-decision and
  the plan's §5 without new evidence; highest risk of a half-finished second
  reader behind another flag. The follow-up beads (`sase-1e8` age lens,
  side-by-side diffs) would then need building twice.
- *Verdict:* reject for v1. Revisit only if measured data shows the
  pager round-trip itself (not the entry points) is the bottleneck.

### Option C — Inline timeline modal + diff preview in the TUI (middle, tempting)

Keep the pager as the reader, but add a TUI-native `@`-style timeline modal
(reusing the pure `timeline_picker.build_picker_rows` / `filter_picker_rows` /
`picker_footer_preview` builders against `HistoryService` data) and a small
read/diff preview inside the Memory pane. `⏎`/`=` in the modal deep-links into
the pager at the exact version/pair.

- *Pros:* glanceable (the top TUI complaint), reuses pure builders so row
  semantics can't drift; pager remains the only *reader*, modal is only a
  *chooser* — consistent with the D-decision.
- *Cons:* still a new focus system, new goldens, new perf surface; picker
  parity (lazy rows, `/` filter, `.` hidden, two-point compare preview) is real
  work; risk of "modal that is almost the pager but worse."
- *Verdict:* adopt *narrowly* (timeline chooser only, no diff preview — see
  below).

### Option D — History-aware Memory pane + routes (recommended core)

Keep the pager as the sole reader. Make the Memory pane the best *route* into
it: history-visible list rows, an expanded History card section, a feed route
with watermark hooks, and deep links everywhere, all rendered from cached
`HistoryService` summaries with the existing worker/placeholder discipline.

- *Pros:* fixes the actual gap (discovery + glance + routing) without a second
  reader; every piece reuses landed primitives (summaries, sparkline, feed
  document, pill vocabulary); shippable incrementally behind no new flag;
  leaves `sase-1e5…sase-1ed` hooks clean.
- *Cons:* users still round-trip through the pager for reading (accepted —
  that round-trip is the design, and the pager is genuinely good at reading).
- *Verdict:* adopt as the v1 TUI investment, composed with the best links from
  A and the chooser from C.

## 7. Recommended solution

**Keep the pager as the only history reader. Make the TUI the best place to
discover, preview, and arrive — never a second reader.** Three phases, in
order; each is independently landable and golden-covered.

### Phase 1 — History-visible Memory pane (the "intuitive" win)

1. **Row-level history signals.** Extend the rail row (not just the card) with
   a compact history suffix: glyph of newest class (`◆`/`⇧`/`✚`/…), version
   count, age (`3d`), and state color (amber `◌` dirty, violet past-ness is for
   the pager — in the list use neutral + amber-only-for-dirty). Untracked /
   ignored / `NO VCS` / `SHALLOW` / `TEMPLATE` rows keep distinct dim/amber
   chips rather than a fake count. Data comes from the same cached summaries
   already fetched for the card; no new queries on the keystroke path.
2. **Expanded History card section.** Promote today's single History row into a
   4-line section: state line (`● NOW · v25 · latest · 1mo ago` /
   `◌ NOW · uncommitted · on top of v25`), sparkline + `v24 → v25 · +31w −4w`
   last-change line, provenance line (bead/agent/SHA, each a pager deep-link
   target), and key-hint line (`H history · C changes · @ picker in pager`).
   Empty states teach: "v1 · only version — history grows with commits."
3. **Footer + help parity.** Footer previews destinations (`H v25 history · C
   feed`), help modal gains a "Time" group mirroring the pager's four-pill
   legend. Keymaps land in `MemoryPanelKeymaps` + `default_config.yml` + schema
   together.
4. **Scope honesty.** Home scope with no VCS shows `NO VCS · enable chezmoi
   with a git-backed source` with the CLI hint, not a dead `H`. Shallow clones
   show `SHALLOW` + the fetch hint. Both are already in the vocabulary — the
   TUI just has to render them instead of `…`.

### Phase 2 — Chooser modal + feed route (the "reliable + beautiful" win)

5. **TUI timeline chooser (`@` in the Memory pane).** A `ModalScreen` table
   built *only* from `timeline_picker.*` pure functions over a worker-fetched
   `HistoryService.timeline`: same markers (`●`/`▸`), ordinals, ages, glyphs,
   `now`/`≡ now`, hidden-summary row, `j/k/g/G`, `⏎` (open in pager at version,
   pushes a pager trail entry), `=` (open pager diff older→newer), `.` hidden,
   `/` filter. No body rendering, no diff rendering — the modal never reads,
   it only chooses. Lazy rows past ~200 versions. This is Option C fenced to a
   chooser, so it cannot rot into a second reader.
6. **Feed route with watermark hooks.** `C` keeps opening the pager feed today,
   but the pane gains a "Changes since…" line backed by a persisted per-scope
   watermark (the `sase-1e6` shape: `feed_watermark{scope_key: tip}`), showing
   `N new since last review` and advancing on `C`-then-`r`/explicit mark-read.
   Build the TUI against a tiny `FeedWatermark` adapter now so `sase-1e6`
   slots in without rework; ship the persisted watermark in this phase if
   `sase-1e6` hasn't already.
7. **Deep links that matter most (Option A, curated):**
   - Agent detail → `AGENTS.md` at launch snapshot (`sase-1e5` evidence:
     workspace HEAD + instruction blob OIDs) — label it `as seen by this
     agent`, never as current instructions.
   - Memory-log / glossary-read rows → exact version read via stored
     `blob_oid` where present.
   - Instruction-file rows (project `AGENTS.md`, home template with `TEMPLATE`
     chip) → their own timelines, including the cause row semantics.
   - Each link pushes a version-pinned pager trail entry so Backspace returns
     to the TUI moment.

### Phase 3 — Hooks, not scope creep (protect the follow-ups)

8. **Explicit non-commitments in this design:** restore-as-draft (`sase-1e7`,
   must route through `memory/mutation.py`, never for generated subjects),
   age lens (`sase-1e8`), plain-file provider (`sase-1e9`), `path@rev` /
   side-by-side / per-host home (`sase-1ea`) all stay separate beads. This
   design's only obligation to them: never close their UI seams (chooser
   `⏎`/`=` targets, feed subject labels, card provenance links, `E edits now`
   invariant — pinned views never gain an "edit this version" affordance).
9. **Reliability instrumentation:** extend the existing `SASE_TUI_PERF`/`TRACE`
   coverage to History-row cache-hit rate, summary latency, and chooser
   open-to-paint; add golden cases for tombstone, dirty, `NO VCS`, shallow,
   template, and `history unavailable` card states (the honest states are the
   beauty test — a dim `…` forever is a bug).
10. **Docs:** one `docs/` subsection ("Reading history from the TUI") linking
    `memory_history.md` — routes, chooser, watermark, honest states — plus the
    CLI reference row. No new concepts, no new glyphs; the vocabulary table
    stays single-sourced.

### Why this is the right shape

- **Intuitive:** history becomes visible where the user already browses
  (rail rows), previewable where they already read (card), choosable without
  leaving (modal), and readable where reading is best (pager). No modes, no
  second alphabet — `H`/`C`/`@` mean what they mean in the pager.
- **Reliable:** zero new git IO in the TUI (Rust boundary intact), zero new
  queries on input paths (cache + workers + staleness guards, as today),
  fail-open everywhere, past links pinned and version-addressed, `E` always
  edits now, trail entries version-pinned. The honest states are rendered, not
  hidden — which is precisely what makes the feature trustworthy.
- **Beautiful:** no new visual language. The TUI borrows the pager's proven
  one — pill shapes, violet-past/amber-dirty discipline, log-scaled sparkline,
  explicit secondary foregrounds, theme-aware palette, specified shed order —
  at glance density (rows + card + chooser) rather than reader density (band +
  body). Beauty here is consistency + restraint: the past is recognizable, the
  dirty is unmissable, and nothing flashes, wraps, or pushes.

### What I would explicitly not build

- No TUI body/diff renderer (rejects Option B outright for v1).
- No TUI diff preview inside the card (the highest drift-per-pixel surface;
  the chooser's `=` → pager diff covers the need).
- No new glyphs, pills, or colors — any proposal adding one must first argue
  why the shared vocabulary table is insufficient.
- No restore affordance until `sase-1e7` lands its `mutation.py` path; a
  "restore" button that bypasses publish would be worse than no button.

## 8. Acceptance sketch (for the implementing epic)

- Rail shows class/age/count or the correct honest chip for every row kind
  (tracked, dirty, untracked, ignored, shallow, template, `NO VCS`,
  unavailable) — golden-covered.
- Card History section renders now/past/tombstone/dirty/empty states with
  sparkline + provenance links; `H`/`C` destinations previewed in footer.
- `@` chooser opens from any note/strand, filters, toggles hidden, and lands
  the pager at the exact version (read) or pair (diff, older→newer);
  Backspace returns to the TUI moment.
- Agent-detail "as seen" link opens `AGENTS.md` at the launch snapshot;
  memory-log rows with `blob_oid` open the exact version.
- Watermark: `N new since last review` per scope, advancable, persisted.
- Perf: rail motion never blocks on history; History section paints from
  cache; chooser opens instantly on long timelines (lazy rows); traced and
  within the existing TUI budgets.
- `just check` green (not `check-full` — unrequested), new PNG goldens
  reviewed group-by-group (creations, removals, then updates), keymaps +
  schema + help updated together.

## 9. Sources consulted

- Bead `sase-1dr` (epic, closed) + land-triage note #3 (follow-ups
  `sase-1e5…sase-1ed`) and #4 (landing fixes); beads `sase-1e5…sase-1ed`
  descriptions.
- `sase/repos/plans/202609/memory_history.md` (§5 budgets/decisions incl.
  D2/D7/D8/D9/D13/D15, §18 non-goals; phase specs for pager-axis, diff,
  picker, feed, memory-panel).
- `docs/memory_history.md` (concepts, pill, band anatomy, keys, picker, diff,
  feed, glyphs, CLI, tracking scope, performance), `docs/pager.md`,
  `docs/memory.md` history sections.
- Code: `src/sase/memory/history/service.py` (`HistoryService`),
  `pager_provider*.py`, `feed_document.py`, `timeline_picker.py`,
  `vocabulary.py`; `src/sase/pager/_screen_history*.py`;
  `src/sase/ace/tui/modals/memory_pane.py` + `memory_pane_history.py` +
  `memory_panel_history.py` + `memory_panel_rendering.py` +
  `memory_panel_view.py` + `memory_pane_loading.py`; keymaps
  (`MemoryPanelKeymaps`, `default_config.yml` `memory.open_history/open_changes`).
- Live CLI: `sase memory history --help` (exit 0).
- Standing context: `sase/memory/tui.md` + `lint_and_test.md` via `sase memory
  read`.
