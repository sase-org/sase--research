# SASE Usage Tracking: Design Research

Researcher: mus (independent swarm report).
Question: how should sase add detailed usage tracking so Bryan can (1) find
functionality he never uses and delete it, (2) keep TUI/CLI performance intact,
(3) keep stored data privacy-safe with a future opt-in upload path, and
(4) visualize usage beautifully?

## TL;DR recommendation

Do **not** build a new analytics subsystem. Extend the two systems that already
exist:

1. **Collection:** add a `Usage` event taxonomy to the existing
   `src/sase/telemetry/` pipeline (Rust `sase_core_rs` sqlite store, stub-before-init
   accumulators, 15 s batched flush). New counters record *which surface was used*
   (CLI command, TUI view, macro, flag bead, gate kind) — never *what the user typed*.
2. **Visualization:** add a `Usage` view to the existing Statistics system
   (`src/sase/stats/registry.py` + `sase stats usage` CLI, mirroring the `project`
   view precedent), whose headline widget is a **cold list**: surfaces with zero
   invocations in the selected range, ranked by maintenance cost. Time-range cycling
   (7d / 30d / 90d / all) reuses the existing stats range machinery.
3. **Upload (later):** `sase telemetry export --scrub` producing an inspectable local
   bundle plus an explicit opt-in consent record. No auto-send, no background upload,
   ever.

Details and justification below.

## 1. What already exists (and constrains the design)

I inspected the current tree before concluding anything. The relevant facts:

- **Local telemetry pipeline exists** (`src/sase/telemetry/`): stub metric
  singletons in `metrics.py` become real in-house accumulators on
  `init_telemetry()` (`_registry.py`); samples drain on a 15 s daemon flush or
  `atexit` (`register_flush_on_exit`) into a Rust-owned sqlite store at
  `~/.sase/telemetry/metrics.sqlite` via `telemetry_record_batch`, with
  `raw_seconds=48h`, `rollup_5m_seconds=30d`, `rollup_1h_seconds=365d` retention
  (`_config.py`). Query side is `query.py` (`query_snapshot`, `query_range`) over
  `telemetry_query_instant/range`. CLI surfaces: `telemetry list|snapshot|status|
  health|cleanup-test-data` (`parser_telemetry.py`, `telemetry_handler.py`).
- **What it tracks is backend health, not feature usage.** The catalog
  (`catalog.py`, `METRIC_DEFS`) covers Agent Lifecycle, LLM Provider, Axe,
  Hooks/Mentors/Workflows, VCS/Workspace, Finalizers, Gate Turn, Tool Runs — all
  counters/histograms of internal operations. Nothing records "user ran
  `sase bead sync-external`" or "user visited the Machines tab". The request's core
  need — *per-surface invocation coverage including negative space* — is absent.
- **A Statistics visualization system exists** (`src/sase/stats/`): immutable
  presentation-ready views (`views.py`), a view/grouping/legend registry
  (`registry.py`), TUI tab parity, and a CLI precedent (`sase stats project` with
  `-r/-p/-g` cycling and `-j` JSON output, `parser_stats.py`). Any new viz should be
  a view in this system, not a parallel dashboard.
- **TUI perf is a hard constraint with written rules** (`sase/memory/tui_perf.md`):
  no sync I/O or subprocess on the event loop or pump callbacks; selective updates;
  debounced detail panels; mtime-keyed caches; idle-tick frugality. Usage recording
  must satisfy all of these — this rules out naive "write an event row per action".
- **Rust-core boundary applies** (`sase/memory/rust_core_backend_boundary.md`,
  `docs/rust_backend.md`): storage/aggregation semantics belong in `sase-core`
  (`sase_core_rs` bindings); Python keeps adapters and presentation. A usage-taxonomy
  change therefore needs a `sase-core` change plus the `sase-core-revision.txt` pin
  move — plan for two-repo work, not one.
- **Privacy precedent is strict on labels:** `TOOL_RUN_*` metric docs already state
  "run ids are never labels" (`metrics.py`). High-cardinality or content-bearing
  label values are an established anti-pattern here, which is exactly the right
  instinct for this feature.

## 2. Critique of the plan as stated

**It is a good idea, with the stated goal being the right scope.** "Find dead
functionality to delete" is the highest-value use of usage data: it converts
telemetry into code deletion, which compounds (less code → faster TUI → fewer bugs).
Instrument-then-prune loops beat both never-instrumenting and instrument-everything.
I would keep the goal but adjust the requirements as follows.

### 2a. "Detailed usage tracking" needs redefinition (adjustment #1)

"Detailed" is doing dangerous work in the request. There are three distinct
resolutions, and only one is safe:

| Resolution | Example | Verdict |
|---|---|---|
| Surface invocation | `bead.sync_external ran, ok, cli` | Record this. Bounded cardinality (~hundreds of series). |
| Parameter shape | `bead.list --mine --sort=updated` | Record flag *presence* from an allowlist, never values. |
| Content | prompt text, argv free-text, paths, bead titles, repo URLs | Never record. Unbounded cardinality, sensitive, and unnecessary for the deletion goal. |

The deletion question — "is this surface used at all?" — is fully answered by
resolution 1 plus a zero-aware presentation layer (Section 4). Anything finer is
cost without benefit for this goal. I recommend the design record an explicit
non-goal: *usage tracking will never distinguish two invocations of the same
surface by their arguments' values*. If a future question needs parameter-shape
data (e.g. "which `sase stats` flags matter?"), that is a separate consented
study, not a standing tap.

### 2b. Usage ≠ value: the deletion review needs a second input (adjustment #2)

Zero invocations in 60 days does **not** mean safe to delete. Counter-examples that
certainly exist in sase: disaster-recovery paths (`sync-external --resolve-
conflicts`, stale-clone rescue), annual flows (release recipes), and
low-frequency/high-stakes gates (sudo approval, plan approval). Deleting the fire
extinguisher because there was no fire is the failure mode of this whole project.

Adjustment: the Usage view must join invocation counts against **two** other
signals before anything is labeled a deletion candidate: (a) static reachability —
sase already has Symvision unused-symbol analysis (`sase/memory/symvision.md`);
a surface that is *both* statically cold and dynamically cold is a far stronger
candidate than either alone; (b) an owner-annotated criticality tag
(`rare-but-keep`: recovery, safety, compliance). Concretely: three tiers —
`unused` (zero hits, not tagged) → propose deletion; `cold` (below threshold) →
review; `critical-rare` (tagged, any count) → never auto-flagged. The review UX
(Section 4) should show the tier, not a raw count.

### 2c. One month of data has a coverage problem (adjustment #3)

A 1–2 month window systematically misses quarterly and annual flows. The design
should therefore (a) default the Usage view range to 90d/all rather than 7d once
data exists, (b) record a *first-seen* watermark per surface so the review can say
"never observed **since tracking began on <date>**" instead of the false-precision
"never used", and (c) treat the 1h-rollup tier (365d retention, already configured)
as the source of truth for cold-list queries — **not** the 48h raw tier. Note the
existing raw retention (48h) is fine for health debugging but useless for this
goal; the design must not accidentally build the cold list on raw samples or it
will report everything as unused after two days. If rollup granularity (5m/1h)
cannot express a needed dimension (e.g. per-flag presence), add a **daily** rollup
tier in the Rust store rather than extending raw retention — daily rollups over a
year are tiny and exactly match the deletion-review cadence.

### 2d. The TUI-slowness worry is legitimate and shapes the mechanism (no change)

The request is right to flag this. The correct conclusion is that usage recording
must be **cheaper than the existing telemetry path, not a second path**: same
stub-before-init singletons (zero cost when disabled or pre-init), same in-memory
accumulators, same 15 s batched flush, no new threads, no per-action sqlite writes,
no TUI-thread I/O whatsoever. Keystroke/hover/scroll paths must never emit events
— only *committed* actions (command dispatched, tab selected and settled, macro
completed, gate resolved). A debounced "tab settled for >1 s" rule for TUI views
prevents tab-cycling from flooding counters.

## 3. Collection design

### 3a. Event taxonomy (allowlisted, bounded)

New `METRIC_DEFS` entries in `src/sase/telemetry/metrics.py`, all counters:

- `sase_usage_cli_total{command, subcommand, status}` — one increment per CLI
  dispatch in `src/sase/main/entry.py` + handler layer. `command`/`subcommand` come
  from the parser's own `dest` values (already a closed vocabulary — no free text).
- `sase_usage_tui_total{view, status}` — one increment per settled TUI view visit
  (emit from the existing navigation/refresh seam, debounced, off-thread per
  `tui_perf.md` rules 1–2; never from render or keystroke paths).
- `sase_usage_macro_total{macro, status}` — macro invocations by macro name
  (macro names are a closed catalog, safe as labels).
- `sase_usage_gate_total{gate_kind, outcome}` — gate resolutions by kind
  (plan/question/sudo/launch-approval), outcome allowlisted
  (approved/denied/deferred/expired).
- `sase_usage_flag_total{command, flag}` — presence-only flag usage for a small
  curated flag set per command (e.g. `bead.list --mine`), recorded as
  `{command, flag}` with **no values**. Curated, not automatic: automatic flag
  capture would ingest values and paths.

Explicitly out of taxonomy: prompt text, argv free-text, file paths, bead/macro
content, repo URLs, project display names in upload bundles (see 3c), LLM I/O,
timings beyond the existing duration histograms. Labels must pass a cardinality
review in code review — any label whose value set is not closed at authoring time
is rejected.

### 3b. Performance budget

- Disabled (`telemetry.enabled=false`) or pre-init: stub objects, single
  attribute-deref + no-op method call. Unmeasurable.
- Enabled: one in-memory counter increment per committed action (nanoseconds),
  flushed with the existing 15 s batch. Zero new syscalls on the action path, zero
  TUI-thread work (record synchronously into memory; the flusher thread already
  owns persistence).
- Storage: bounded series count (closed vocabularies, curated flags). Daily rollup
  tier keeps a year of cold-list data in kilobytes. The 48h raw tier is untouched.
- Verification: `SASE_TUI_PERF=1` key-to-paint p95 < 16 ms before/after on every
  tab; idle-tick `refresh.auto_tick` surface-reload counts unchanged;
  `bench_tui_jk.py` comparison per `docs/contribute/perf-runbook.md`. Any
  regression fails the change.

### 3c. Privacy design (local-first, upload-safe by construction)

1. **Closed vocabularies only.** Every stored string is either authored in the
   taxonomy or drawn from the parser/macro catalog. There is no code path that
   writes user-supplied text into the usage store. This is enforceable by test: a
   unit test asserts every emitted label value against its allowlist.
2. **Local project identity stays local.** Project/repo names are genuinely useful
   for "which project's flows are dead" but can name clients/employers. Rule: the
   local store may record them; any export bundle **buckets or drops** them
   (map to `project[0..n]` ordinals or aggregate away), and export defaults to
   dropping. Document this in the export preview.
3. **Opt-in upload, deferred.** Ship collection + local viz first with no network
   code at all. The upload story is: `sase telemetry export --since 30d --scrub`
   writes a human-readable JSON bundle to a user-chosen path and prints exactly
   what was included (series count, date range, scrub rules applied, sha256);
   sending it anywhere is a separate manual step until a consent record exists.
   When the server side is built: explicit `sase telemetry share --opt-in`
   creating a durable consent record (revocable via `share --revoke`), preview
   before every send, no background transmission, versioned schema with a
   documented retention/deletion policy on the server. The consent prompt must
   state what is technically *impossible* to include (no prompts, no paths, no
   content — by construction, Section 3a) rather than promising policy-level
   restraint.
4. **Kill switch and transparency.** `telemetry.enabled=false` disables usage
   recording with the usage path (same flag, no second flag to discover);
   `telemetry status` shows store size/freshness (exists); add `usage` coverage of
   "tracking active since <date>" so the cold list's denominator is visible.

## 4. Visualization UX (the part to get beautiful)

I thought hard about where this lives. Options considered: (a) standalone web
dashboard, (b) new TUI tab, (c) Statistics-system `Usage` view + `sase stats usage`
CLI. **Choose (c):** it reuses the registry/grouping/legend/range machinery, the
TUI+CLI parity contract, and the user's existing mental model ("Statistics is where
I learn about my sase"). A web dashboard is heavier to build/secure/host and splits
attention; a bespoke tab duplicates range/grouping/export code that `stats/` already
owns.

Proposed `Usage` view (TUI Statistics → Usage; CLI `sase stats usage [-r 7d|30d|
90d|all] [-g surface|command|project] [-j|--markdown]`):

1. **Cold list (hero widget).** "Unused in range, ranked by maintenance cost":
   zero-count surfaces joined with a cheap static-cost proxy (lines of handler
   code, test count, or Symvision symbol fan-in), each row offering the tier chip
   (`unused` / `cold` / `critical-rare`), first-seen watermark, and a one-key
   jump to the owning code (`go to handler`). This is the deletion-review workflow
   in one screen — it directly serves the stated goal, unlike a generic activity
   chart.
2. **Coverage heatmap (secondary).** Surfaces × weeks, cells shaded by invocation
   bucket (0 / 1–5 / 6–25 / 26+), zeros in a distinct hue — negative space must be
   visually loud, not the absence of color. Range cycling reuses the existing
   stats range control.
3. **Top/flat ranking (tertiary).** Simple bar ranking of most-used surfaces for
   orientation ("where does my time actually go"), plus a one-line summary:
   "142 surfaces tracked since 2026-10-01 · 37 unused in 90d · 4 tagged critical-rare".
4. **Legends and honesty.** Every existing stats view carries `MetricLegend`s
   (`registry.py`); the Usage view needs them most: define "used" (≥1 settled
   invocation), "tracked since", "critical-rare", and crucially "absence of evidence
   ≠ evidence of absence for flows younger than the tracking window".

Beauty guidance: keep the existing stats render primitives (`stats/render/`), the
`#FF87D7` statistics accent, and panel/table language — consistency *is* the beauty
here. The one novel visual element should be the cold-list tier chips with distinct
hues; everything else should look like it always belonged in Statistics.

## 5. Rollout plan

1. **Phase 1 — taxonomy + collection (two-repo).** Rust store: daily rollup tier
   (or confirm 1h tier suffices); `sase-core` metric registration; pin move in
   `sase-core-revision.txt`. Python: new `USAGE_*` singletons, CLI dispatch hook,
   gate/macro hooks, allowlist tests, `enabled=false` coverage.
2. **Phase 2 — local viz.** `Usage` view spec in `stats/registry.py`, view
   builders reusing `_view_builders.py` patterns, `sase stats usage` CLI with
   json/markdown/rich parity, TUI wiring through the existing Statistics tab
   (off-thread load, cached render — `tui_perf.md` rules 1, 5, 6).
3. **Phase 3 — review workflow.** Static-cost join (Symvision), criticality tags
   (config list, defaulting to recovery/safety surfaces), cold-list export to
   markdown for the deletion pass.
4. **Phase 4 (deferred) — opt-in share.** Export/scrub/preview UX first; server +
   consent only when there is a server. No network code in Phases 1–3.

Estimated shape: Phase 1 ~2–3 tasks (Rust + Python + tests), Phase 2 ~2 tasks,
Phase 3 ~1 task, Phase 4 a separate epic gated on a server design that does not
exist yet.

## 6. Risks and open questions

- **Behavior change under observation.** Tracked users explore more; first-month
  data overstates breadth. Mitigate by weighting toward the second half of the
  window in cold-tier thresholds.
- **Multi-machine identity.** Bryan runs across tailnet machines (athena, apollo,
  mac); per-machine stores will disagree. The Usage view should show "this
  machine" by default with an explicit merged-all-machines mode once export
  exists (export bundles are the merge vehicle — another reason to build export
  before any server).
- **Macro/skill-generated invocations.** Agent-driven macro runs will pollute
  "my usage" if counted equally. Record an `actor` label (`human` vs `agent`,
  already knowable at dispatch — cf. agent-session context) and default the Usage
  view to `actor=human`.
- **Open question for the lead:** should `actor=agent` usage count toward
  keep/delete at all? My view: yes for crash-safety-critical paths agents
  exercise, no for UX-surface breadth — hence the default filter, not exclusion.
- **Open question:** exact cold thresholds (e.g. 0 in 90d = unused; ≤3 = cold)
  should be config-tunable with the chosen defaults recorded in a decisions note.
