# Finalizer Observability in the Agents Tab — Consolidated Report

**Date:** 2026-09-10
**Repo:** `sase-org/sase` @ `3260f6a42` (reports measured @ `f5a3f5c99`)
**Inputs:** `agents_tab_finalizer_panel__a.md` (interaction design, observation
protocol, degraded states) and `agents_tab_finalizer_panel__b.md` (host corpus
measurements, wire-contract constraints, TUI-perf grounding), plus lead verification of
every load-bearing claim against the sase and sase-core checkouts.

---

## 1. Executive Summary

The Agents tab shows nothing about finalizers today, even though nearly everything the
user asked for is already on disk unread: `finalizer_plan.json` (what was selected),
`agent_meta.json["finalizers"]` (a compact mirror), `final_context.json` (per-instance
trigger decisions), `finalizers/<id>/attempt-N.*` (terminal output), and
`finalizer_result.json` (verdicts, attempts, refusals, deferrals, evidence,
diagnostics). The two genuine gaps are **live status** and **live output** — the
controller keeps its active instance, attempt, and timing in local variables, and
`bounded_subprocess` buffers streams in memory until exit.

The gap matters more than the request implies. Measured on this host (1,219 finalizer
runs): 23.9% of runs spend **more than 30 seconds** in the finalizer phase and 13.4%
spend **more than five minutes** (stitch hooks, and `commit_repair.py` can invoke the
LLM again on conflicts). For that entire window the row reads `RUNNING`,
indistinguishable from a thinking model. Meanwhile 6.7% of runs end non-success across
16 distinct diagnostic codes, all currently invisible.

**Recommendation in one sentence:** ship a *finalizer phase* — a `FINALIZING` status
word, a `⛭` row chip for non-success only, a foldable `FINALIZERS` section in the
detail panel, and an output modal for the long tail — fed by two additive, non-wire
artifacts (a small append-only `progress.jsonl` lifecycle journal and a bounded
per-attempt `.live` log on the monitor logging contract), reconciled into one
Rust-core projection with strict source precedence, delivered in three flag-gated
increments (status → diagnosis → live output).

Both researchers independently converged on the placement (foldable metadata section;
both rejected a permanent pane, a new tab, agent-tree child rows, tools-timeline reuse,
and modal-only), on progressive disclosure, on "no live progress without new
artifacts," on a JSONL transition journal, on a subprocess live sink, on Rust-core
reconciliation, and on read-only v1. They disagreed on four mechanism points; §4
resolves each with code evidence.

---

## 2. Verified Ground Truth

Lead verification confirmed every decisive claim from both reports:

| Claim | Verdict |
| --- | --- |
| Attempt artifacts are written `exclusive=True`; collision raises | ✅ `executor_command.py:160–187`, `executor_plugin.py:240–253`, `artifacts.py:64–93` |
| Wire schema v2 has no `Running`, no timestamps on attempts, `deny_unknown_fields` throughout | ✅ `sase-core/crates/sase_core/src/finalizer/wire.rs:4,255–278` (19 `deny_unknown_fields` structs) |
| `agent_meta.json["finalizers"]` block written at plan seal; `run_finalizers` runs inline in the runner turn | ✅ `llm_provider/_invoke.py:154–304` |
| `finalizers_drift` is published to `agent_meta.json` and **read by nothing** | ✅ sole reference is the writer, `controller.py:91` |
| `AgentMetaWire` is a fixed-field dataclass; an additive field is the cheap row-level channel | ✅ `core/agent_scan_wire_markers.py:112` |
| Section/fold machinery exists exactly as described (`append_fold_section_heading`, `MONITOR_SECTION_ID="monitor"`, `shells`/`wait`/`gate`/`bead` sections, `_agent_slow_tools.py` precedent) | ✅ `ace/tui/widgets/prompt_panel/` |
| Per-lane cadence machinery exists for the detail header (e.g. slow-tools lane refreshes at 5 s) | ✅ `_agent_display_header_summary.py:84–88` |
| Surface-token refresh (`event_refresh/_surface_tokens.py`) and bounded log/tail helpers (`logs/_bounded.py`, `monitor/logs.py`, `read_tail_seek`, `artifact_files_cache.py`) exist for reuse | ✅ |
| `workflow-artifacts/` has a 14-day reap horizon covering new run-artifact files | ✅ `core/managed_tmp_reaper.py:42,70` |
| `bounded_subprocess._reader` drains in chunks — the exact insertion point for a live sink | ✅ `bounded_subprocess.py:74–96` |

Caveat on the corpus numbers: they come from one host where effectively one finalizer
instance (`commit`, 1,212 of 1,216 instance results) has ever run. The duration and
failure-mix figures are directional, not universal — but they are the only empirical
data available and they all point the same way.

---

## 3. Empirical Findings That Shape the Design (B, adopted)

1. **The invisible minutes are the feature's justification.** Wall-time from attempt
   start to aggregate result: p50 2.0 s, p75 13.6 s, p90 812 s. Recent precisely-timed
   samples: 32/37/40/41/158/191/273/302 s.
2. **Failures are diverse and mute.** 16 diagnostic codes in the wild
   (`stitch_failed` 24, `dirty_after_commit_decisions` 12, `commit_refused` 9,
   `controller_exception` 7, `plan_integrity_failed` 4, …). Every one is a message a
   human wants and none reaches the UI.
3. **One result file is 3.32 MB** (1,786 near-duplicate diagnostics —
   `ledger.record()` and `remember_result()` extend lists across up to 8 controller
   cycles with no dedupe). The reader needs a pre-parse size ceiling and
   render-time dedupe; the writer should eventually dedupe too.
4. **`dirty_work_discarded` (severity `error`) appears in droves inside successful
   runs** (1,041 rows). Severity must render relative to the instance's terminal
   status and latest attempt (the scoping `ledger.is_retryable_result()` already uses)
   — otherwise the panel is permanently red.
5. **16% of runs have zero attempts** (`trigger: not_triggered`, clean tree). This is
   the most common non-trivial state and must render as a calm `○ not triggered`,
   never as an error or an empty box.
6. **93% of runs succeed.** Silence is the reward: success earns one section line and
   zero row glyphs. Only the 6.7% earn a mark.
7. **One finalizer exists in practice.** v1 is a commit-finalizer panel and should be
   excellent at that job (sha, tree, hook output, deferral paths, retry budget) —
   while rendering multi-instance pipelines well enough to make a second finalizer
   (`check`) attractive to configure.

---

## 4. Resolved Disagreements

### 4.1 Current-state snapshot file — **rejected; journal + `agent_meta` field wins**

A proposed both an atomically-replaced `finalizer_state.json` snapshot and an event
journal; B proposed the journal plus an additive `finalizers.phase/status` field on
`agent_meta.json`. Adopt B's leaner shape:

- The row-level signal **must** live in `agent_meta.json` regardless: `AgentMetaWire`
  is the fixed-field scan contract, and adding a new marker *file* to the scan is a
  contract change while adding a field to an already-parsed file is additive and free.
- The journal is tiny — events only at semantic transitions (phase/instance/attempt
  start/finish), so replaying it to derive current state costs microseconds. A second
  current-state writer is redundant state that can drift from the journal.
- The journal's mtime doubles as the refresh surface token; the snapshot's only
  claimed advantage (cheap freshness checks) is already covered.

A's *semantics* survive the cut: the journal must carry `plan_digest` and run identity
so a leftover journal from a superseded run is never trusted, and timestamps are
wall-clock with durations computed by the writer.

### 4.2 Live output files — **separate bounded `.live` log wins; no promotion**

A proposed teeing to `*.stdout.live`/`*.stderr.live` and atomically *promoting* them
to the canonical attempt names on completion. Verification kills the promotion leg:
`attempt-N.stdout`/`.stderr` are written with `exclusive=True` and a collision raises
`FinalizerExecutionError` — that immutability is load-bearing evidence. Adopt B: the
`.live` file is a **separate, disposable cache** on the monitor bounded-log contract
(`logs/_bounded.py`, 2 MiB cap + one rotation), and the immutable per-stream artifacts
are still written at exit, evidence contract untouched. Bonus: a finalizer killed at
its 1,800 s hard timeout currently loses *all* output; the live sink fixes that.

A's stream-fidelity caveat is retained: reader threads cannot promise exact
cross-stream ordering, so the live log's interleaving is approximate. Tag lines by
stream, present it as a live tail, and keep the canonical per-stream artifacts as the
authority for postmortems.

### 4.3 Section placement — **after `SHELLS`/`WAIT`, before `BEAD`**

A said "above the prompt/context bulk"; B said "immediately after the `SHELLS`/`WAIT`
block." These are compatible; adopt B's more specific answer. Finalizers are *how the
turn ends*, so they group with lifecycle (shells, wait, monitor, gate), above content.
All cited section IDs verified.

### 4.4 State vocabulary — **B's glyph/palette, A's semantic distinctions**

Merged vocabulary (glyph + word + color always together, so state reads without color
and is searchable in screenshots):

| State | Glyph | Source | Notes |
| --- | --- | --- | --- |
| selected | `◌` dim | plan exists, phase not started | A's "selected for this run," never "enabled" — the global registry may have drifted |
| pending | `◌` dim | journal: phase active, instance not started | dependency/order blocked |
| running | `●` gold | journal: unmatched `attempt_started` + live runner | show operation/substep + elapsed |
| retrying | `●` gold + gauge | journal + `max_attempts` | attempt gauge `▰▱` only when budget > 1 |
| success | `✓` green | result wire | |
| failed | `✗` red | result wire | latest-attempt diagnostics hot, earlier dim |
| refused | `⊘` magenta | result wire | a decision, not an error |
| deferred | `⏸` amber | result wire | typed reason + the specific paths |
| not triggered / skipped | `○` dim | `final_context.json` trigger | calm, 16% of runs |
| not run | `–` dim | projection-derived | planned but controller ended first; show `blocked by X` |
| interrupted | `!` amber | journal ends mid-attempt + runner dead | never a forever-spinner, never `failed` |
| unavailable | `⚠` | integrity/parse/size failure | show why; keep raw-artifact access |

Colors and heading styles come from the existing monitor-section palette — no new
palette. "Pending" is never used as a blanket word for selected/queued/retrying.

### 4.5 Non-disagreements worth recording

Both reports independently ruled out: changing the wire (`Running` variant would force
a v2→v3 bump across Rust, the Python mirror, provider result-schema digests, and the
historical-refusal corpus, for a purely presentational need); modeling finalizers as
shells or family members (contradicts `decisions:host-owned-completion` and
`decisions:single-turn-agents`); streaming into `live_reply.md`; a top-level
Finalizers tab; a raw JSON viewer; and any new per-agent poller.

---

## 5. The Recommended Experience

Organizing principle: **one glyph in the row, one section in the detail, one modal for
the long tail** — three zoom levels mapped onto the user's three questions, each
affordable at its own frequency.

### 5.1 Layer 0 — the agent row (free)

While `run_finalizers()` executes, the status word becomes **`FINALIZING`** (bucketed
under `Running` so ordering, filtering, and capacity accounting never change). This is
the highest value-per-line change in the whole design: it converts a multi-minute
ambiguous silence into a legible phase. A `⛭` lane chip appears next to the existing
monitor/gate chips **only** for running (`⛭ commit` or `⛭ 2/3`), failed (`⛭✗`),
deferred (`⛭⏸`), and refused (`⛭⊘`). Success renders no chip.

### 5.2 Layer 1 — the `FINALIZERS` section (one debounced worker on selection)

A new `_agent_finalizer_section.py` built with `append_fold_section_heading`, so
`z a`/`z A`/`z 1-3` and section navigation work for free. Placed after `SHELLS`/`WAIT`.
Rendered whenever a sealed plan exists — before, during, and after the phase; omitted
for legacy runs with no plan; `⚠ unavailable` (never "0 finalizers") when the plan
fails authentication.

Level 1 (collapsed, default): `▸ FINALIZERS · 2 selected · commit ✓ 1.8s · check ● 0:42`

Level 2 (workhorse): one aligned row per instance in dependency order — glyph ·
instance id (accent) · provider ref (dim) · attempt gauge · right-aligned duration ·
the single most useful evidence value (commit sha, command). `└ after commit`
continuation lines only when non-empty, so a real pipeline reads as a pipeline. Header
carries plan digest, counts, and the `⚠ config drifted since this plan was sealed`
line sourced from the already-published, currently-unread `finalizers_drift` field.

Level 3 (diagnosis): per-attempt breakdown with per-attempt durations (from the
journal — the wire has none), deduped attempt-scoped diagnostics (`+N earlier
diagnostics` dim), refusal reason, typed deferral with the actual protected paths,
evidence table, and — only for a running or terminal-non-success instance — a ≤12-line
output tail via `read_tail_seek`. Failed instances start logically expanded
(GitHub-Actions precedent) but an explicit user fold choice is never overridden, and
new output never moves focus or scroll.

Section footer: `1 configured · 1 default · 0 required · sase final list` — the global
"what is enabled" question is answered by pointing at the existing CLI table, not by a
second UI.

### 5.3 Layer 2 — the output modal (explicit keypress)

`⏎` on the section (plus a leader chord, e.g. `,F`) opens a `ModalScreen` with
`PanelTabStrip` tabs per instance, attempt selector, stdout/stderr/inputs tabs,
rendered through the same cached `render_axe_output(..., "ansi")` monitors use — so
finalizer output looks like monitor output looks like axe output. While an instance
runs, the modal follows the `.live` tail; scrolling up pauses follow with a quiet
`↓ N new lines` indicator and returning to the bottom resumes (Grafana live-tail
rule). `E` opens `$EDITOR` on the real file. Provider (`executor_plugin`) stdout is
protocol JSON, not a human log: show the provider's structured messages/diagnostics by
default and treat raw protocol output as developer detail.

### 5.4 The calm rules

- **5-second gate:** no live tail renders for an instance until it has run ~5 s
  (config `ace.finalizer_live_tail_after_seconds`). With p50 = 2.0 s, streaming every
  run would read as flicker; fast finalizers simply go `● → ✓`.
- **Bounded everywhere:** 2 MiB on disk (rotating), seek-based tail reads (12 lines in
  section, ~500 in modal), 1 MiB pre-parse ceiling on `finalizer_result.json` with an
  explicit `⚠ result too large — press E` fallback.
- **Selected-agent only:** tail fetches happen only when the Agents tab is focused,
  this agent is selected, the phase is active, and the surface token drifted. A
  background agent finalizing elsewhere costs zero.
- **Sanitized:** subprocess output passes through the existing ANSI renderer, never
  raw Rich markup; no control-sequence, hyperlink, or markup injection; no tails
  copied into app logs, telemetry, or notifications.

---

## 6. Mechanism Changes (all additive, no wire bump)

1. **`src/sase/finalizers/progress.py`** — append-only JSONL at
   `finalizers/progress.jsonl`, written by the controller at semantic transitions:
   `phase_started`, `instance_started`, `attempt_started`, `attempt_finished`,
   `instance_finished`, `phase_finished`, with timestamps, `plan_digest`, and run
   identity. Crash-legible by construction: an unmatched `attempt_started` plus a dead
   runner renders `interrupted`. Readers ignore unknown events and tolerate a
   truncated final line. Journal writes are best-effort — an observability I/O failure
   must never change a finalizer verdict. (~120 lines + call sites.)
2. **`agent_meta.json["finalizers"].phase/status`** — additive field on the already-
   scanned file, mirrored as an additive `AgentMetaWire` field (+ Rust scan field +
   contract-manifest test update). Drives the status word and chip at zero extra file
   opens in the list path.
3. **`live_sink` on `run_bounded_subprocess`** — optional callback invoked in the
   existing `_reader` chunk loop; executors bind it to a bounded rotating
   `attempt-N.live` via the monitor log contract. Caps, timeout, process-group
   termination, returned buffers, and the exclusive terminal artifacts are all
   unchanged. Sink errors are swallowed. (~20 lines + ~15 per executor.)
4. **`FinalizerRunSnapshotWire` in `sase-core/crates/sase_core/src/finalizer/`** — one
   projection reconciling plan + journal + `final_context` + result + live-file
   metadata for the TUI, `sase final show --runs`, and any future web view
   (`decisions:rust-core-required`). It owns the size ceiling, diagnostic dedupe,
   attempt scoping, ordering, and **source precedence**: authenticated plan is
   authoritative for selection/order/policy; a valid terminal result dominates
   everything including a stale journal; the journal is authoritative for runtime
   phase only while run identity and `plan_digest` match and the runner is live;
   attempt/live files supply content, never status; live runner absent + no terminal
   result = `interrupted`, never `failed` or `running`. Every planned instance
   receives an explicit disposition — absence from the result renders `not run`
   (with `blocked by X` where derivable), never silent success or eternal pending.
5. **TUI wiring** — a `finalizers` lane in the detail-header summary (per-lane cadence
   machinery already exists), loaded off-thread with mtime caching and stale-
   generation rejection; a `finalizers` refresh surface whose token is
   `mtime(progress.jsonl) + mtime(<live tail>)` for the selected agent only,
   piggybacked on the existing auto-tick probe; `DetailPanelDebouncer` respected; no
   stat/glob in render paths; no full agent-list rebuilds for log chunks.

---

## 7. Delivery Plan

Gate phases A–C behind one `beta` flag (`ace_finalizer_panel`, default off, created
via `sase flag new` per `sase/memory/sase_flags.md`; both states tested; Off branch
deleted when C lands).

- **Phase A — kill the invisible minutes** (ships alone, useful alone): progress
  journal + controller call sites; `agent_meta` phase field + `AgentMetaWire`;
  `FINALIZING` status word + chip; `FINALIZERS` section at fold levels 1–2 from
  existing artifacts (with the size ceiling and dedupe from day one); surface the
  drift warning. Answers "what's enabled" and "what happened" from authoritative data
  and makes the phase legible.
- **Phase B — diagnosis + the shared projection**: fold level 3 (attempts, durations,
  scoped diagnostics, deferral paths, evidence, terminal-output tail); move
  reconciliation into `FinalizerRunSnapshotWire` with Python as a thin adapter;
  `sase final show --runs` over the same snapshot.
- **Phase C — live**: `live_sink` + bounded `.live` logs; refresh surface + 5 s tail
  gate; the output modal with follow/pause.
- **Phase D — polish** (each independently optional): Config Center Finalizers tab;
  a notification on finalizer `failed`/`refused` (~4/day at current rates; `deferred`
  never notifies); write-time diagnostic dedupe in `ledger.record()`/
  `remember_result()` so no future 3.32 MB artifact exists; family aggregation
  (group by member, never merge same-named finalizers across members; pinned attempts
  read only their own artifacts) and bounded remote projection.

Read-only throughout: no cancel/retry controls in v1 — they carry authorization and
fixed-point semantics that must not be smuggled into a display feature.

### Key risks and their tests

| Risk | Mitigation / test |
| --- | --- |
| 3.32 MB result freezes the panel | pre-parse ceiling + dedupe; synthetic 4 MB fixture asserting no parse |
| `severity: error` floods successful runs red | attempt-scoped severity; test against the real `dirty_work_discarded` corpus shape |
| Forever-spinner after runner death | journal + liveness → `interrupted`; test by truncating the journal |
| Tail flicker on 2 s finalizers | 5 s elapsed gate |
| Idle-CPU / j/k regressions | zero surfaces reloaded on quiet tick (`SASE_TUI_TRACE=1`); `bench_tui_jk.py` p95 unchanged; no artifact I/O in render/navigation paths |
| Live sink deadlocks the drain | sink called inside existing reader thread, errors swallowed; test with raising sink + 10 MB producer |
| Cross-agent stale data | selection-generation rejection; late tail from agent A never renders on agent B |

Plus projection fixtures for every state in §4.4 (including digest mismatch, unknown
schema, truncated journal, commit reactivation across fixed-point cycles, early
failure with explicit `not run`), snapshot tests at 120/80/60 columns in both themes,
and an end-to-end fake finalizer that emits slowly, retries, then passes/fails/dies.
`sase/memory/lint_and_test.md` verification before landing anything.

---

## 8. Open Questions for Bryan

1. **`FINALIZING` word vs `RUNNING ⛭` suffix** — both researchers and the lead
   recommend the distinct word (the clarity *is* the feature); it touches every
   status-bucket set once.
2. **Notify on finalizer failure by default?** (~4/day at current rates.) Recommended
   yes for `failed`/`refused` in Phase D, never for `deferred`.
3. **Configure a second finalizer (`check`) as part of this work?** The panel is far
   more compelling with a real pipeline and `builtin@command` supports it today, but
   it adds latency to every agent turn — a separate decision from this feature.
4. **Journal retention** — keep with the run artifact under the existing 14-day
   horizon (recommended); compact into the terminal result only if storage pressure
   ever materializes.
