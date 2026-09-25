# Finalizers on the Agents Tab: Design Research (`mus`)

- **Date:** 2026-09-25
- **Question:** how should the Agents tab visualize finalizers (lifecycle
  finalizers generally, not just the builtin `commit` finalizer), and what
  role — if any — should decks, cards, and card blocks play?
- **Prior context read:** `research:202609/agents_tab_finalizer_panel/agents_tab_finalizer_panel.md`
  (consolidated 2026-09-10 report) and
  `research:202609/agent_data_card_blocks/agent_data_card_blocks.md`
  (consolidated 2026-09-25 report), plus independent verification against the
  `sase` and `sase-core` checkouts noted below.
- **Scope:** Agents-tab presentation of finalizer state. No verdict on whether
  a second builtin finalizer (e.g. `check`) should be configured — that is a
  separate latency decision.

## 1. What I verified independently

I re-checked the load-bearing claims rather than taking the prior report on
faith. All hold at the current checkout:

1. **The artifacts already exist; the UI reads none of them.** `finalizer_plan.json`
   (`finalizers/plan.py:46`), `final_context.json`
   (`finalizers/declaration_manifest.py:40`), `finalizer_result.json`
   (`finalizers/artifacts.py:15`), per-instance `finalizers/<id>/attempt-N.*`
   terminal output, and the `finalizers_drift` mirror published to
   `agent_meta.json` (`finalizers/controller.py:91`) are all written. Nothing
   under `src/sase/ace/tui/` consumes them for display.
2. **The wire is closed.** `sase-core/.../finalizer/wire.rs` uses
   `deny_unknown_fields` throughout, so any row-level live signal that touches
   the wire forces a schema bump. An additive field on the already-scanned
   `agent_meta.json` / `AgentMetaWire` (`core/agent_scan_wire_markers.py:122`)
   is the cheap channel — consistent with the prior report's conclusion.
3. **Controller runs inline, keeps live state in locals.** `run_finalizers()`
   (`finalizers/controller.py:101`) drives the fixed-point loop in the runner
   turn; phase/instance/attempt liveness exists only as local variables. There
   is no live-status artifact today — the one genuine backend gap alongside
   live output.
4. **Attempt artifacts are immutable evidence** (`artifacts.py`
   `exclusive=True` writers). Any live-output design must therefore use a
   *separate disposable* live log, never mutation or promotion of the terminal
   artifacts.
5. **Fold-section machinery is real and reusable.** `append_fold_section_heading`
   with section IDs (`MONITOR_SECTION_ID="monitor"`, gate/shell/wait/bead
   siblings) under `ace/tui/widgets/prompt_panel/` gives folding, `z`-family
   navigation, and section jumping for free to any new section.
6. **Decks are exactly three, with fixed meaning.** `DeckId` in
   `ace/tui/widgets/decks/model.py` is `MAIN | FILES | TOOLS`; `MAIN` is
   Context + Reply (or Summary for clans/tribes). Deck cycling (`Ctrl+N/P`)
   visits every deck with nothing skipped, so a fourth deck would be visited
   on every cycle for every node — a tax paid by users who never configure a
   second finalizer.

## 2. What the user actually needs (three questions, three zoom levels)

Troubleshooting a finalizer means answering three questions in order, and each
wants a different surface:

| # | Question | Frequency | Right surface |
|---|----------|-----------|---------------|
| 1 | "Is it still working, or stuck?" (phase legibility) | every run with a slow finalizer | agent **row**: a status word + chip |
| 2 | "What ran, in what order, and how did each step end?" (diagnosis) | failures, refusals, deferrals, drift | **detail section**: one row per instance, expandable to attempts |
| 3 | "What did it actually print?" (forensics) | the long tail | **output modal** on explicit keypress |

The prior report's "one glyph in the row, one section in the detail, one modal
for the long tail" matches what I would design from scratch. I adopt the
three-layer shape and spend my independent judgment on *where layer 1 lives*
(decks vs cards vs sections vs blocks) and *how it stays generic* across
future finalizers.

## 3. The core decision: decks, cards, blocks, or a detail section?

### 3.1 Candidate placements

- **(a) A fourth deck** (e.g. `FINALIZERS` alongside MAIN/FILES/TOOLS).
- **(b) New card(s) in the Main deck** (e.g. a `Finalizers` card next to
  Context/Reply).
- **(c) A foldable `FINALIZERS` detail-panel section** alongside
  SHELLS/WAIT/MONITOR/GATE/BEAD sections.
- **(d) Card blocks** — finalizer instances (or attempts) as blocks inside the
  Reply card or a new card.

### 3.2 Recommendation: (c) — a detail section, not a deck or card

Finalizers are *how the turn ends*: lifecycle metadata in the same family as
shells, wait beads, monitors, and gates — every one of which is a foldable
detail section, not a deck or card. The arguments:

1. **Decks answer "what kind of data," not "which pipeline stage."**
   MAIN/FILES/TOOLS partition *content kinds* (conversation, diffs, tool
   calls). Finalizer state is orthogonal to all three — a commit finalizer's
   sha belongs with neither the Reply text nor the Files diffs conceptually,
   and a future `check` finalizer's lint output belongs with none of them
   either. A fourth deck would also be empty-or-trivial for the overwhelming
   majority of runs (93% success, one line), yet `Ctrl+N/P` would land on it
   every cycle. That is a permanent navigation tax for a usually-empty view.
2. **A Main-deck card pollutes the triage loop.** Paged decks keep a sticky
   preferred card (Reply) across `j/k` so one keypress per session shows each
   session's current output. Inserting a Finalizers card into that cycle means
   either it steals stickiness (bad: Reply is the triage target) or it is
   never seen (bad: the feature is undiscoverable). Cards are for content you
   page through; finalizer state is status you glance at.
3. **Sections already solve the exact problem.** Fold levels (collapsed
   summary → per-instance rows → per-attempt diagnosis), section navigation,
   `z`-family folding, and the SHELLS/WAIT/MONITOR/GATE grouping all exist.
   Finalizers group naturally with lifecycle: place `FINALIZERS` after
   SHELLS/WAIT (before BEAD/content), matching the "how the turn ends"
   mental model. A section also renders for every node kind uniformly,
   whereas cards vary by node kind (Summary cards for clans/tribes have no
   Reply at all).
4. **Family/clan aggregation stays sane.** Sections already have per-member
   aggregation precedents; a deck-level finalizer view would need to answer
   "whose finalizers?" across members with no existing pattern.

### 3.3 What role for card blocks? Deliberately none in v1

Card blocks (deck → card → block) solve a specific pain: a single card too
large to read, where the newest sub-unit is buried (multi-shell Reply). I
considered three ways finalizers could use them and reject all three for v1:

1. **Finalizer instances as Reply blocks — reject.** Blocks subdivide *card
   content*; finalizers are not Reply content. Mixing post-turn lifecycle
   into the conversation timeline corrupts both orderings (shell causal order
   vs finalizer dependency order) and the JUMP roster vocabulary, which is
   built from the shell list. The Reply's block rail showing `--plan/--gate/
   --code` must never suddenly show `commit · attempt 2`.
2. **Attempts as blocks inside a "Finalizers card" — reject (no such card,
   per §3.2).** If a card never exists, its blocks never exist.
3. **Per-instance blocks inside the FINALIZERS section — unnecessary.**
   Sections already have three fold levels, which express
   summary → instance → attempt without new machinery, new keys (`[`/`]`),
   new rails, or walker updates. The card-blocks report itself warns that
   every container walker must be taught about a new wrapper type (§1.5 of
   that report: digest, render-mode lower bound, hint caching, flatten/split
   all fail silently otherwise). Paying that cost to re-express what fold
   levels already do is mechanism ahead of need.

**Where blocks could matter later:** if a future finalizer routinely emits
thousands of lines of *content-like* output that users read as a document
(e.g. a `check` finalizer whose full lint report dwarfs its verdict), *that
output* — shown in the output modal — could be block-structured per attempt
or per check-group. That is a modal-content decision for Phase C/D, not a
v1 architecture decision. The v1 rule is simple: **finalizers live in a
detail section; blocks stay out of it.**

### 3.4 The one deck/card-adjacent piece worth taking: vocabulary, not structure

The decks project built a good visual language (accent-colored rules, title
pills, phase dividers like `─── ⚙ MONITOR ─── t2 ───`, dim evidence values,
glyph+word+color status). The FINALIZERS section should speak that language —
instance rows in dependency order with the shell accent conventions, a dim
`└ after X` continuation for ordering, the monitor/gate chip style for the
row chip — without becoming a deck or card. Consistency without structural
coupling.

## 4. Staying generic: designing past the `commit` finalizer

Today's corpus is ~100% `commit` instances, which tempts a commit-specific
panel (sha, tree state, hook output, deferral paths). The design must be
excellent at commit (it is the only finalizer users have) while treating
commit-specific fields as *one provider's evidence schema*, not the panel's
schema:

1. **Generic row, typed evidence.** Every instance row shows the same generic
   spine: glyph · instance id · provider ref (dim) · attempt gauge (only when
   budget > 1) · duration · one evidence value. The evidence value is
   provider-defined: `commit` shows the short sha; `builtin@command` shows the
   command; a future `check` shows e.g. `3 errors`. The section owns the
   spine; providers own the evidence string. No provider ever gets a bespoke
   row layout in v1.
2. **Generic attempt model.** Attempts (started/finished timestamps from the
   journal, exit status, scoped diagnostics, output tail) are identical across
   providers because they come from the executor layer, not the provider.
   Diagnosis UI (fold level 3) is therefore provider-agnostic by
   construction — the best hedge against overfitting.
3. **Refusals and deferrals are first-class, not commit quirks.** `refused`
   (`⊘`, a decision) vs `deferred` (`⏸`, typed reason + paths) vs `failed`
   (`✗`) must be distinct states in the vocabulary from day one, because a
   future permissions/safety finalizer will refuse far more often than commit
   does. Render calm states calmly: `○ not triggered` (16% of runs — the most
   common non-trivial state) and `– not run` (planned but controller ended
   first, with `blocked by X` where derivable) must never read as errors.
4. **Ordering comes from the plan, not the provider.** Instances render in
   sealed-plan dependency order with `after` edges shown; the panel never
   assumes a single-instance pipeline. A two-finalizer `commit → check`
   pipeline should read as a pipeline on day one, even before `check` ships.
5. **Config-vs-run split.** "What is enabled globally" is answered by pointing
   at the existing `sase final list` CLI table (section footer), never by a
   second registry UI. The panel shows *this run's sealed plan* (with a
   `⚠ config drifted since this plan was sealed` line from the already-
   published `finalizers_drift` field) — selected-for-this-run, never
   "enabled." This distinction is what keeps the panel correct when global
   config changes between runs.

## 5. Recommended solution

### 5.1 Experience (three layers)

- **Layer 0 — the agent row (cheapest, highest value).** While
  `run_finalizers()` executes, the status word becomes `FINALIZING`
  (bucketed under `Running` so ordering/filtering/capacity never change),
  converting multi-minute ambiguous silence into a legible phase. A `⛭` chip
  appears only for running, failed, deferred, and refused — success earns
  silence (one section line, zero glyphs). Glyph+word+color always together
  (readable without color, searchable in screenshots).
- **Layer 1 — the `FINALIZERS` detail section.** New section after
  SHELLS/WAIT via `append_fold_section_heading` (folding/navigation free).
  Three fold levels: collapsed one-liner (`▸ FINALIZERS · 2 selected ·
  commit ✓ 1.8s · check ● 0:42`); per-instance rows in plan order with
  evidence values; per-attempt diagnosis with journal-derived durations,
  attempt-scoped deduped diagnostics, refusal reasons, typed deferral paths,
  and a ≤12-line output tail for running/terminal-non-success instances only.
  Failed instances start logically expanded (GitHub-Actions precedent) without
  overriding explicit user folds; new output never moves focus.
- **Layer 2 — the output modal.** Explicit keypress (`⏎` on section + leader
  chord) opens per-instance tabs with attempt selector, rendered through the
  same ANSI pipeline as monitor/axe output. Live-follow while running with
  scroll-up-pauses-follow; `E` opens the real file. Provider-protocol stdout
  shows structured messages/diagnostics by default, raw protocol as developer
  detail.

### 5.2 Mechanism (all additive, no wire bump)

1. **Append-only `finalizers/progress.jsonl` lifecycle journal** written by
   the controller at semantic transitions only (phase/instance/attempt
   start+finish), carrying wall-clock timestamps, `plan_digest`, and run
   identity. Crash-legible: unmatched `attempt_started` + dead runner =
   `interrupted` (never forever-spinner, never `failed`). Best-effort writes;
   observability I/O never changes a verdict. Readers ignore unknown events
   and tolerate a truncated final line.
2. **Additive `phase/status` field on the already-scanned `agent_meta.json`**
   (+ `AgentMetaWire` + Rust scan field + contract-manifest test update).
   Zero extra file opens in the list path; drives status word + chip.
3. **Bounded `.live` log via a `live_sink` callback** in the existing
   `bounded_subprocess` reader loop, on the monitor bounded-log contract
   (2 MiB cap + rotation). Separate disposable cache; terminal artifacts keep
   their `exclusive=True` evidence immutability. Bonus: output now survives
   the 1,800 s hard-timeout kill, which today loses everything.
4. **One `FinalizerRunSnapshot` projection** (Rust core per
   `rust_core_backend_boundary` — any frontend would need the same
   reconciliation — with a thin Python adapter) merging plan + journal +
   `final_context` + result + live-file metadata. It owns source precedence
   (authenticated plan for selection/order; valid terminal result dominates
   everything; journal authoritative for runtime phase only while run
   identity + digest match and runner is live; files supply content, never
   status), the 1 MiB pre-parse ceiling on `finalizer_result.json`, and
   diagnostic dedupe with attempt scoping (severity renders relative to the
   instance's terminal status, so `dirty_work_discarded`-style error rows in
   successful runs don't paint the panel red).
5. **TUI wiring on existing cadence machinery:** a `finalizers` lane in the
   detail-header summary, off-thread loads with mtime caching and
   selection-generation rejection, refresh token of
   `mtime(progress.jsonl)+mtime(live tail)` for the *selected agent only*,
   5-second live-tail gate (p50 run is 2 s; streaming every run reads as
   flicker), seek-based tail reads, sanitized ANSI rendering, no stat/glob in
   render paths.

### 5.3 Delivery (flag-gated, each phase useful alone)

- **Phase A — kill the invisible minutes:** journal + call sites, `agent_meta`
  field + wire, `FINALIZING` + chip, section at fold levels 1–2 from existing
  artifacts (size ceiling + dedupe from day one), drift warning.
- **Phase B — diagnosis + shared projection:** fold level 3, snapshot
  projection with Python as thin adapter, `sase final show --runs` over the
  same snapshot.
- **Phase C — live:** sink + `.live` logs, refresh surface + 5 s gate, modal
  with follow/pause.
- **Phase D — optional polish:** notification on `failed`/`refused` (never
  `deferred`); write-time diagnostic dedupe so no future 3 MB artifact;
  family aggregation (group by member, never merge same-named finalizers);
  Config Center tab. Read-only throughout v1: no cancel/retry controls (they
  carry authorization and fixed-point semantics that must not ride along
  with a display feature).

### 5.4 What I explicitly do NOT recommend

- No fourth deck, no Main-deck Finalizers card, no blocks in v1 (§3).
- No wire `Running` variant (v2→v3 bump for a presentational need).
- No finalizers-as-shells/family-members (contradicts host-owned completion
  and single-turn-agent decisions), no streaming into `live_reply.md`, no
  top-level Finalizers tab, no raw JSON viewer, no new per-agent poller.
- No bespoke commit-panel schema: commit is the best-supported evidence
  provider, not the panel's data model (§4).

## 6. Risks and tests (highest-value first)

| Risk | Mitigation / test |
|------|-------------------|
| Oversized result freezes panel | pre-parse ceiling + render dedupe; synthetic 4 MB fixture |
| Error-severity rows flood successful runs red | attempt-scoped severity; test against real `dirty_work_discarded` shape |
| Forever-spinner after runner death | journal + liveness → `interrupted`; truncation test |
| Tail flicker on ~2 s runs | 5 s elapsed gate |
| j/k or idle-CPU regression | zero surfaces on quiet tick; existing TUI bench unchanged; no artifact I/O in render paths |
| Cross-agent stale tails | selection-generation rejection |
| Single-finalizer overfit | projection fixtures with 2–3 instances, `after` edges, early failure → explicit `not run`, digest mismatch, unknown schema |
| Snapshot tests | 120/80/60 columns × both themes; end-to-end slow fake finalizer (retry → pass/fail/die) |

## 7. Open questions for the lead

1. `FINALIZING` status word vs `RUNNING ⛭` suffix — I favor the distinct word
   (the clarity is the feature), touching every status-bucket set once.
2. Notify on `failed`/`refused` by default in Phase D? (Never `deferred`.)
3. Journal retention: keep with the run artifact under the existing 14-day
   reap horizon (favored); compact into the terminal result only if storage
   pressure materializes.
4. Should the output modal's large-output content (if a future finalizer
   emits document-scale reports) reuse card-block structure per attempt? Left
   explicitly to Phase C/D — v1 needs no answer.
