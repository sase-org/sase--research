# Finalizer Visibility in the ACE Agents Tab (Researcher B)

**Date:** 2026-09-10
**Repo:** `sase-org/sase` @ `f5a3f5c99`
**Question:** How should the Agents tab surface an agent's finalizers — what is enabled,
what is running (with live output), and what the terminal status and output were?

---

## 1. Executive Summary

The Agents tab currently shows **nothing at all** about finalizers. `agent_meta.json`
already carries a `finalizers` block; `finalizer_plan.json`, `final_context.json`,
`finalizers/<id>/attempt-N.*` and `finalizer_result.json` are all written to every
agent's artifact directory; **ACE reads none of them.** The only place a finalizer
verdict reaches a human today is `runner_reporting._finalizer_verdict()`, which
stringifies the result into an error report *after the run already failed*.

Measured on this host (1,219 finalizer runs; 406 in the last 7 days; 89 today):

| Metric | Value |
| --- | --- |
| Aggregate outcomes | 1,135 `success` / 72 `failed` / 9 `refused` — **6.7% non-success** |
| Distinct finalizer instances configured, ever | **1** (`commit`) — zero `builtin@command` in the wild |
| Runs with **zero** recorded attempts (nothing to do) | 191 (**16%**) |
| Runs needing a retry | 25 (24 × 2 attempts, 1 × 3) |
| Finalizer phase wall-time (attempt start → aggregate result) | p50 **2.0 s**, p75 13.6 s, **p90 812 s** |
| … exceeding 30 s | **23.9%** |
| … exceeding 5 min | **13.4%** |
| Real recent samples (submit accepted → result published) | 32 s, 37 s, 40 s, 41 s, 158 s, 191 s, 273 s, 302 s |
| Per-attempt stdout size | p50 552 B, p90 1.1 KB, max 4 KB |
| `finalizer_result.json` size | p50 773 B, p90 1.2 KB, p99 3.6 KB, **max 3.32 MB** |
| Worst result file | 1,786 diagnostics, nearly all byte-identical duplicates |

Two facts drive the whole design:

1. **The invisible minutes.** Finalization is not instantaneous. A quarter of runs spend
   more than 30 seconds and an eighth spend more than five minutes in the finalizer
   phase — `sase stitch create` runs before-commit hooks, and `commit_repair.py` can
   invoke the **LLM a second time** to resolve a conflict. Throughout that entire window
   the Agents tab shows a bland `RUNNING` row identical to an agent that is still
   thinking. The user cannot tell "the model is writing" from "the host is committing"
   from "the host is stuck retrying a stitch."
2. **The wire has no concept of "running."** `FinalizerInstanceStatusWire` is
   `pending | skipped | success | refused | deferred | failed`, and carries **no
   timestamps at all**. The Rust structs use `deny_unknown_fields` at schema version 2.
   Live status therefore cannot come from the result wire without a breaking bump.

**Recommendation (Section 7), in one sentence:** add a *finalizer phase* to the agent
lifecycle — one status word, one row chip, one fold-aware `FINALIZERS` section in the
detail panel, and one output modal for the long tail — fed by two **additive, non-wire**
artifacts (a bounded `progress.jsonl` journal and a bounded per-attempt `.live` log that
reuses the monitor logging contract verbatim), with the on-disk → display-ready
projection built in `sase-core` so a future web UI gets the same view.

---

## 2. What A Finalizer Actually Is, Mechanically

This matters because it rules out two otherwise-tempting designs.

Finalizers run **inside the agent's own runner process**, synchronously, immediately
after the provider turn returns:

```python
# src/sase/llm_provider/_invoke.py:296-311
invoke_result = provider.invoke(query, ...)
from sase.finalizers import run_finalizers
invoke_result = run_finalizers(provider=provider, ..., artifacts_dir=artifacts_dir, ...)
```

They are **not** shells (`glossary:sase-shell`), not procs, not family members. Per
`decisions:host-owned-completion`, the host owns them; per `decisions:single-turn-agents`,
attaching one as a shell would *terminate* the turn, which is the opposite of what a
finalizer does. A finalizer is a **phase inside one agent shell's turn**.

### 2.1 The artifact timeline (from a real run, `20260910141434`)

| Time | File | Written by |
| --- | --- | --- |
| 14:15 | `finalizer_plan.json` + `finalizer_plan.authority.json` | `resolve_and_persist_finalizer_plan()` at turn start |
| 14:15 | `agent_meta.json["finalizers"]` = `{plan_digest, selected: [...], raw_operations: [...]}` | `_invoke.py:161` |
| 14:46 | `final_submission.json`, `final_submission_host.json`, `final_submission_attempts.jsonl` | `sase final submit` (the `/sase_final` skill) |
| 14:46 | `finalizers/commit/attempt-1.main.{inputs.json,stdout,stderr}` | attempt artifacts, written **after** the attempt exits, `exclusive=True` |
| 14:47 | `finalizer_result.json` | `write_aggregate_result()` |
| 14:47 | `final_context.json` republished | `publish_final_context()` |

Note the last line: **`final_context.json` is rewritten after the run**, so its mtime is
useless as a phase-start signal. `final_submission_host.json` is the honest marker that
the declaration was accepted.

### 2.2 What each artifact can answer

| User question | Best source | Available today? |
| --- | --- | --- |
| What finalizers are *enabled* for this run? | `finalizer_plan.json` → `plan.entries[]` (instance_id, provider_ref, `policy.max_attempts`, `policy.refusal`, `after`), mirrored compactly in `agent_meta.json["finalizers"]["selected"]` | ✅ on disk, unread |
| What is enabled *globally*? | `sase final list` / `build_finalizer_inventory()` (instance, state, provider, source layer, health) | ✅ CLI only |
| Was an instance even going to fire? | `final_context.json` → `selected_instances[].trigger` (`not_triggered` / `always` / `dirty_repository` / `provider_requested`) and `.submission_required` | ✅ on disk, unread |
| Which are running right now? | — | ❌ **nothing exists** |
| Live output of a running finalizer | — | ❌ **nothing exists**; `run_bounded_subprocess` buffers in memory and only flushes at exit |
| Terminal status + why | `finalizer_result.json` → `status`, `instances[].status`, `refusal_reason`, `deferral{reason,paths}`, `diagnostics[]` | ✅ on disk, unread by ACE |
| Terminal output | `finalizers/<id>/attempt-N.stdout` / `.stderr` (bounded at 1 MiB each) | ✅ on disk, unread |
| Evidence (commit sha, tree, cwd, duration) | `instances[].evidence[]` — e.g. `commit_sha`, `commit_tree`, `cwd`, `result`, `duration_seconds` | ✅ on disk, unread |

The good news: **almost everything the user asked for is already on disk.** The two real
gaps are *live* status and *live* output. Everything else is a presentation problem.

### 2.3 The wire contract constrains the answer

`sase-core/crates/sase_core/src/finalizer/wire.rs` (schema v2):

- `FinalizerInstanceStatusWire`: `Pending, Skipped, Success, Refused, Deferred, Failed`.
  No `Running`.
- Every struct is `#[serde(deny_unknown_fields)]`.
- `FinalizerAttemptWire` = `{attempt, status, diagnostic_code?}` — **no timestamps, no
  duration**. Duration exists only as a `builtin@command` *evidence* string.
- `plan_digest` / `context_digest` / `config_digest` are authenticated
  (`plan.authenticate_resolved_finalizer_plan_full()` compares the model-visible plan to
  the host authority and fails closed). Anything that changes plan serialization changes
  those digests.

**Conclusion:** live progress must be carried *beside* the wire, not inside it. Adding a
`Running` variant would be a v2→v3 bump rippling through the Rust enum, the Python
mirror, provider result-schema digests, `tests/test_finalizers_provider_contract.py`,
`tests/test_finalizers_historical_refusal_corpus.py`, and every mixed-version reader —
all for a purely presentational need.

---

## 3. Empirical Findings That Change The Design

### 3.1 Finalization is slow far more often than anyone assumes

Recent, precisely-timed runs (submission accepted → result published):

```
20260910141701   15:42:03.378 → 15:45:14.485   191 s
20260910145300   15:39:35.269 → 15:44:08.139   273 s
20260910142835   15:07:35.055 → 15:12:37.130   302 s
20260910152512   15:39:51.142 → 15:42:29.211   158 s
20260910141438   15:44:07.887 → 15:44:48.768    41 s
20260910141437   15:31:08.196 → 15:31:48.365    40 s
20260910141435   15:05:15.634 → 15:05:52.631    37 s
20260910141436   15:13:46.268 → 15:14:18.309    32 s
```

Even the narrow "mutating attempt started → aggregate result" window is >30 s for 23.9%
of runs and >5 min for 13.4%. **This is the feature's real justification**, and it is
larger than the brief implies.

### 3.2 The failure modes are diverse and currently mute

Diagnostic codes observed across the corpus:

```
dirty_work_discarded 1041   stitch_failed 24   dirty_after_commit_decisions 12
commit_refused 9   controller_exception 7   stitch_retry_skipped_identical_inputs 7
plan_integrity_failed 4   missing_commit_declaration 4   second_unresolved_conflict 4
dirty_after_stitch 3   stitch_timeout 3   stale_conflict_checkpoint 3
protected_paths_exhausted 1   missing_commit_result 1   stitch_timeout_after_commit 1
```

Every one of these is a message a human would want to see, and every one is invisible
in ACE.

### 3.3 One result file is 3.32 MB of duplicated diagnostics

`20260826194335/finalizer_result.json` = 3,238 KB, 893 top-level + 893 instance
diagnostics, nearly all duplicates. Cause: `ledger.record()` and
`controller_results.remember_result()` both *extend* diagnostic and evidence lists across
controller cycles and attempts with **no dedupe**, and `MAX_CONTROLLER_CYCLES = 8`
multiplies it.

**Design consequence:** the reader must be defensive — a size ceiling before parsing, and
dedupe by `(code, instance_id, attempt, message)` before rendering. Naively feeding this
file to a Rich `Text` on the UI thread is a guaranteed multi-second freeze, exactly the
class of bug `tui_perf.md` rule 1 exists to prevent.

### 3.4 `dirty_work_discarded` at `severity: error` inside otherwise-normal runs

The message is *"Commit finalizer failed: dirty work vanished without an attributable
commit."* It is severity `error`, and it accounts for the overwhelming majority of
diagnostic rows. A UI that colors every `severity: error` diagnostic red will paint the
panel red constantly. **Severity must be rendered relative to the instance's terminal
status**, not absolutely: diagnostics belonging to a superseded attempt render dim, only
the diagnostics scoped to the *latest* attempt (the rule `ledger.is_retryable_result()`
already implements) render hot.

### 3.5 There is exactly one finalizer in the world

1,212 of 1,216 instance results are `commit`. No project has ever configured a
`builtin@command` finalizer. So:

- v1 of this panel is, in practice, **a commit-finalizer panel**. It should be excellent
  at that one job — commit sha, tree, hook output, deferral paths, retry budget.
- But its second job is to *make a second finalizer look attractive*. Once `check`
  (`just check`) or `publish` is one visible, timed, tail-able row next to `commit`, the
  configuration becomes obvious rather than theoretical. A panel that only ever shows one
  row is a panel nobody opens; a panel that shows a **dependency-ordered pipeline** is.

### 3.6 16% of runs have nothing to do

191 runs recorded zero attempts (`trigger: not_triggered` — clean tree, nothing to
commit). The panel must render this as a calm, correct `○ commit · not triggered`, never
as an error or an empty box. This is the single most common non-trivial state after
plain success.

---

## 4. Design Constraints

### 4.1 Performance (`sase/memory/tui_perf.md`)

- **Nothing new per row.** Full agent-list rebuilds are the most expensive UI operation
  (rule 6), and render paths must never stat or glob (rule 8). The list may consume only
  fields already parsed from `agent_meta.json`, which the scan already opens.
- **Detail data loads off-thread**, in the `AgentDisplayAgentWorkerMixin` shape:
  `run_worker(..., thread=True)` → typed result → `call_from_thread` apply, cached by
  mtime like `tools/cache.py::fetch_tool_calls_cached`.
- **Debounce the panel, never the highlight** (rule 7) — route through the existing
  `DetailPanelDebouncer` (150 ms).
- **Live refresh must not be a new poller** (rule 5, rule 14). Piggyback on the existing
  `refresh.auto_tick` surface-token probe (`actions/event_refresh/_surface_tokens.py`),
  adding a `finalizers` surface whose token is `mtime(progress.jsonl) + mtime(<live tail>)`
  for the *selected* agent only. A quiet tick must still reload zero surfaces.
- **Respect the NavigationGate** (rule 13) — no finalizer refresh while j/k is moving.

### 4.2 The agent-scan contract

`src/sase/core/agent_scan_wire_markers.py::AgentMetaWire` is a **fixed-field** projection
of `agent_meta.json`, part of the stable Python↔Rust scan boundary. Adding a new *marker
file* to the scan is a contract change; adding a *field to an already-scanned file* is
additive and cheap. This is decisive: the row-level signal must live in `agent_meta.json`.

### 4.3 Rust core boundary (`rust_core_backend_boundary`, `decisions:rust-core-required`)

Parsing, capping, deduping, ordering and status-deriving over finalizer artifacts is
backend behavior a web UI or `sase final` would need to match. It belongs in
`../sase-core/crates/sase_core/src/finalizer/`. Glyphs, colors, fold levels, keymaps and
Textual layout stay in Python. Concretely: a new `FinalizerRunSnapshotWire` produced by
Rust, consumed by a thin Python adapter and by `sase final` alike.

### 4.4 Immutability of attempt artifacts

`write_text_artifact(..., exclusive=True)` and `write_json_atomic(..., exclusive=True)`
deliberately refuse to overwrite an attempt artifact — that immutability is load-bearing
evidence (`FinalizerExecutionError` on collision). **A live log must therefore be a
different file**, not an incremental version of `attempt-N.stdout`.

---

## 5. The User Experience

### 5.1 The organizing principle

> One glyph in the row. One section in the detail. One modal for the long tail.

Three zoom levels, mapped exactly onto the three questions, each affordable at its own
frequency:

| Zoom | Cost | Answers |
| --- | --- | --- |
| Row chip + status word | free (already-parsed field) | *Is something finalizing / did it go wrong?* |
| `FINALIZERS` detail section, fold levels 1–3 | one debounced worker on selection | *What is enabled, what ran, what happened, why* |
| Finalizer output modal | explicit keypress | *Show me everything, including 1 MiB of stdout* |

### 5.2 Layer 0 — the agent row

**A new status word.** While `run_finalizers()` is executing, the row status becomes
`FINALIZING` instead of `RUNNING`, bucketed under `Running` so ordering, filtering and
capacity accounting are unchanged (`status_buckets.py` already maps display statuses to
buckets; `FINALIZING` joins `AUTO_APPROVE_ELIGIBLE_STATUSES`-style sets only where the
existing `RUNNING` is listed). This one change is the highest value-per-line in the whole
design: it converts an ambiguous multi-minute silence into a legible phase.

**A lane chip**, rendered next to the existing monitor `⏱n` / gate `⛨n` count chips in
`_agent_list_render_agent.py`, using `⛭` (U+26ED) as the finalizer glyph:

```
▶ FINALIZING   my-agent-1a      ⛭ commit                 ← running, single instance
▶ FINALIZING   my-agent-1b      ⛭ 2/3                    ← running, pipeline
✓ DONE         my-agent-1c                               ← success: no chip at all
✗ FAILED       my-agent-1d      ⛭✗                       ← failed finalizer
✓ DONE         my-agent-1e      ⛭⏸                       ← deferred (protected paths)
✓ DONE         my-agent-1f      ⛭⊘                       ← refused
```

**Success renders no chip.** 93% of runs succeed; silence is the reward and the glyph
budget in that row is already crowded (fold, clan chip, monitor, gate, bead, owner, file
change). Only the 6.7% that need attention earn a mark. This is the same discipline
`_GATE_FAILED_COUNT_GLYPH_STYLE` already applies.

### 5.3 Layer 1 — the `FINALIZERS` detail section

A new `prompt_panel/_agent_finalizer_section.py` with
`FINALIZER_SECTION_ID = "finalizers"`, built with `append_fold_section_heading()` so it
joins the existing ladder for free: `z a` cycles it, `z A` toggles it, `z 1/2/3` jumps
levels, and `_section_navigation.py` indexes it as a navigable anchor. Place it
immediately after the `SHELLS` / `WAIT` block — it is *how this turn ends*, so it belongs
with lifecycle, above `BEAD` and the content sections.

**Level 1 — COLLAPSED (one line, the default):**

```
▸ FINALIZERS · 2 selected · commit ✓ 1.8s · check ● 0:42
```

**Level 2 — EXPANDED (the workhorse):**

```
▾ FINALIZERS · plan c21e7df · 2 selected · 1 skipped
  ✓ commit    builtin@commit    ▰▱  1.8s    ce9d984
  ● check     builtin@command   ▰   0:42    just check-full
  ○ publish   builtin@command   ▱   —       not triggered
```

Columns, left to right: status glyph · instance id (accent) · provider ref (dim) ·
attempt-budget gauge · duration (right-aligned, `format_duration`) · the single most
useful evidence value. `after:` dependencies render as a dim `└ after commit` continuation
line only when non-empty, so a real pipeline reads as a pipeline.

The attempt gauge `▰▱` is worth the two cells: it answers "does this have a retry left?"
without a number, and it is the difference between "it failed" and "it failed and gave
up." Rendered only when `max_attempts > 1`.

**Level 3 — FULLY_EXPANDED (diagnosis):**

```
▼ FINALIZERS · plan c21e7df · 2 selected · 1 skipped
  ✗ commit    builtin@commit    ▰▰  2 attempts  47.3s
      Attempt 1  ✗ stitch_failed      12.1s
      Attempt 2  ✗ stitch_timeout     35.2s   (budget exhausted)
      Refusal    —
      Evidence   cwd  /…/workspaces/bobs-org/bob-cli/bob-cli_11
                 head fda8627
      ⚠ stitch timed out after 300s
      ── attempt-2.stderr · last 12 of 340 lines ────────────────
      error: recipe `check` failed on line 12 with exit code 1
      …
      press ⏎ for full output

  ⏸ publish   builtin@command   ▱   deferred · protected_paths · 3 paths
      .sase/config.yml
      secrets/prod.env
      +1 more
```

Three rules make this level trustworthy rather than noisy:

1. **Diagnostics are deduped and attempt-scoped.** Only diagnostics whose `attempt`
   matches the latest attempt render hot; earlier ones render dim and collapse to
   `+N earlier diagnostics`. This mirrors `ledger.is_retryable_result()`'s existing
   latest-attempt scoping, so the UI and the retry policy agree about what "the current
   problem" is.
2. **Output is a tail, never a body.** Twelve lines maximum in the section, from
   `read_tail_seek()`. The full body lives in the modal.
3. **Deferral and refusal are decisions, not errors.** `⏸`/`⊘` in yellow/magenta, never
   red, with the typed reason spelled out and the paths listed. This is the one place the
   TUI teaches something `sase final list` cannot: *which specific paths the host declined
   to commit, and under which of the four closed reasons*.

**Glyph and color language** (deliberately parallel to `_agent_monitor_section.py` so the
vocabulary transfers between monitors, gates, and finalizers):

| State | Glyph | Style |
| --- | --- | --- |
| running | `●` | `bold #FFD700` |
| success | `✓` | `bold #5FD75F` |
| failed | `✗` | `bold #FF5F5F` |
| refused | `⊘` | `bold #FF87FF` |
| deferred | `⏸` | `bold #FFAF5F` |
| skipped | `○` | `dim` |
| pending | `◌` | `dim #5F5F5F` |

Section heading `bold #D7AF5F underline` and field labels `bold #87D7FF`, matching MONITOR
and the rest of the panel exactly. No new palette.

### 5.4 Layer 2 — the finalizer output modal

Bound to `⏎` on the section (via `_section_navigation`) and to a leader chord
(`,F` — `,A`/`,m` are taken; leader is the right namespace for "open a modal about the
selected agent"). A `ModalScreen` using the existing `PanelTabStrip`:

```
┌─ Finalizers · my-agent-1a ───────────────────────────────────┐
│   ⛭ commit ✓   │   ⛭ check ●   │   ⛭ publish ○   │   all     │
├──────────────────────────────────────────────────────────────┤
│ attempt 1 ✗ 12.1s   [attempt 2 ✗ 35.2s]                      │
│ stdout │ stderr │ inputs                                     │
│                                                              │
│ 🔄 Running before commit hook: sase_git_fix                  │
│ 🔄 Dispatching create_commit to VCS provider...              │
│ ✅ create_commit completed successfully!                      │
│ ⚠️ Primary commit succeeded, but this project already has …   │
│                                                              │
│ ── live · following ──────────────────────── 1.2 KB / 1 MiB ─┤
└──────────────────────────────────────────────────────────────┘
```

Reuse `util/axe_log_renderer.render_axe_output(source_id, text, "ansi")` — the same
cached ANSI highlighter monitors already use, so finalizer output looks like monitor
output looks like axe output. While an instance is running the modal follows the tail
(`E` opens `$EDITOR` on the real file, exactly like the file panel's `E` affordance).

### 5.5 The live-output policy — how not to overwhelm the TUI

Four bounds, each already proven elsewhere in the codebase:

1. **Bounded on disk.** The live log is a `sase/logs/_bounded.py` rotating log with a
   2 MiB default cap and one `.1` rotation — byte-for-byte the monitor contract
   (`sase/monitor/logs.py`). Env override `SASE_FINALIZER_LOG_MAX_BYTES`.
2. **Bounded on read.** `read_tail_seek(path, lines)` seeks; it never reads the file.
   12 lines in the section, 500 in the modal.
3. **Bounded in time.** The live tail is fetched **only** when the Agents tab is focused,
   *this* agent is selected, the phase is active, and the surface token drifted. A
   background agent finalizing in another project costs zero.
4. **Bounded by relevance.** The section shows the tail only at fold level 3 and only for
   an instance that is running or terminal-non-success. A green `commit ✓` never expands
   into output the user did not ask for.

Additionally, **do not stream output for fast finalizers.** With p50 = 2.0 s, streaming
for every run would produce a flicker that reads as instability. Gate the live tail
behind an elapsed threshold (default 5 s, config `ace.finalizer_live_tail_after_seconds`)
— under that, the instance simply goes `● → ✓` and the tail appears only in history. This
single rule is what keeps the feature calm.

### 5.6 Answering "what is enabled" globally

Two audiences, two answers:

- *Per run* — the section header (`2 selected · 1 skipped`, plus the plan digest so a
  drift report is actionable). Sourced from `finalizer_plan.json`, which is authenticated
  against the host authority.
- *Globally* — `sase final list` already renders a good table (Instance / State /
  Provider / Source / After / Health). **Do not build a second modal for it.** Add a
  Finalizers tab to the existing Config Center (`open_config_center: "#"`) later, and in
  the section footer print the one-line pointer `1 configured · 1 default · 0 required ·
  sase final list` in `COLOR_EMPTY`, mirroring how the monitor section prints
  `sase monitor show <id> --follow`.

There is also a **drift signal already being published and thrown away**:
`controller._project_drift_to_agent_meta()` writes `agent_meta.json["finalizers_drift"]`
when the sealed config no longer matches live config. Nothing reads it. Surface it as a
`⚠ config drifted since this plan was sealed` line in the section header — free, and
exactly the kind of thing that silently breaks a run.

---

## 6. The Two Mechanism Changes (and why they are small)

### 6.1 A progress journal, not a wire change

New `src/sase/finalizers/progress.py`, a bounded append-only JSONL at
`<artifacts_dir>/finalizers/progress.jsonl`, written by `controller.py` at four points:

```json
{"ts":"2026-09-10T18:46:31.204Z","event":"phase_started","instances":["commit","check"]}
{"ts":"…","event":"instance_started","instance_id":"commit","provider_ref":"builtin@commit","max_attempts":2}
{"ts":"…","event":"attempt_started","instance_id":"commit","attempt":1}
{"ts":"…","event":"attempt_finished","instance_id":"commit","attempt":1,"status":"failed","diagnostic_code":"stitch_failed"}
{"ts":"…","event":"instance_finished","instance_id":"commit","status":"success"}
{"ts":"…","event":"phase_finished","status":"success","cycles":1}
```

Why this and not a `Running` status:

- **Zero wire risk.** No schema bump, no digest change, no provider-contract churn, no
  effect on `plan_digest`/`context_digest`/`config_digest`. Unknown future events are
  ignored by readers, so it is forward-compatible by construction.
- **It supplies the timestamps the wire lacks.** Durations today exist only as an
  evidence string for `builtin@command`; the journal gives per-attempt wall-time for
  *every* provider, which is what the section's duration column needs.
- **It is crash-legible.** If the runner dies mid-finalization, the journal ends with an
  unmatched `attempt_started` — the panel can honestly render `● commit · interrupted`
  rather than showing a permanently-spinning row. `finalizer_result.json` alone cannot
  express that.
- **It is the phase marker.** `phase_started` / `phase_finished` is what drives the
  `FINALIZING` status word and the row chip.

Cost: ~120 lines plus call sites, reusing `append_jsonl_record()` which already exists.

The row-level signal additionally needs one field on `agent_meta.json` —
`finalizers.phase = "running" | "settled"` and `finalizers.status` — added to
`AgentMetaWire` (additive dataclass field + Rust scan field + `tests/test_contract_manifest.py`
update). This keeps the list path at zero extra file opens.

### 6.2 A live sink on the bounded subprocess

`bounded_subprocess.run_bounded_subprocess()` already spawns two reader threads that
drain stdout/stderr incrementally with a cap and a truncation flag. Add one optional
parameter:

```python
def run_bounded_subprocess(argv, *, cwd, env, input_bytes, timeout,
                           stdout_cap=STDOUT_CAP_BYTES, stderr_cap=STDERR_CAP_BYTES,
                           live_sink: Callable[[str, bytes], None] | None = None):
```

and call `live_sink(name, chunk)` inside the existing `_reader` loop. `executor_command`
and `executor_plugin` bind it to
`append_bytes_locked(finalizers/<id>/attempt-N.live, ...)` through the monitor's bounded
contract. The immutable `attempt-N.stdout`/`.stderr` are still written exclusively at
exit — **the evidence contract does not change at all**, and the `.live` file is a
disposable cache a later artifact sweep may delete.

Cost: ~20 lines in `bounded_subprocess.py`, ~15 in each executor, one new module reusing
`sase/logs/_bounded.py`.

Note this also fixes a latent problem: today, if a `builtin@command` finalizer hangs for
its full 1,800 s hard timeout, **all of its output is lost** unless it exits. With a live
sink, a timed-out finalizer still leaves a readable log.

---

## 7. Recommended Solution

**Ship a finalizer *phase*, presented at three zoom levels, fed by two additive
artifacts, projected in Rust.**

### 7.1 Phase A — "the invisible minutes" (highest value, smallest surface)

No new contracts; ships alone and is useful alone.

- `finalizers/progress.py` + controller call sites (§6.1).
- `agent_meta.json["finalizers"].phase/status` + `AgentMetaWire` field.
- `FINALIZING` status word; row chip `⛭` for running and terminal-non-success only.
- `FINALIZERS` detail section at fold levels 1 and 2, reading `finalizer_plan.json`,
  `agent_meta.json`, `final_context.json` and `finalizer_result.json` through a debounced
  detail worker with a **1 MiB pre-parse ceiling** and diagnostic dedupe.
- Surface `finalizers_drift` in the header.

Files: `src/sase/finalizers/progress.py` (new),
`src/sase/finalizers/controller.py`, `src/sase/core/agent_scan_wire_markers.py`,
`src/sase/agent/status_buckets.py`,
`src/sase/ace/tui/widgets/prompt_panel/_agent_finalizer_section.py` (new),
`_agent_display_header_metadata.py`, `_agent_list_render_agent.py`,
`_agent_list_styling.py`, `models/_agent_state.py`,
`models/_loaders/_meta_enrichment_{common,filesystem,wire}.py`,
`src/sase/default_config.yml` (fold-mode section entry + the live-tail threshold).

### 7.2 Phase B — history and diagnosis

- Fold level 3: per-attempt breakdown, deduped attempt-scoped diagnostics, typed deferral
  with paths, evidence table, terminal-output tail via `read_tail_seek`.
- The `FinalizerRunSnapshotWire` projection moves to
  `sase-core/crates/sase_core/src/finalizer/runtime.rs`; Python becomes a thin adapter and
  `sase final show <instance>` gains a `--runs` view over the same snapshot. Per
  `decisions:rust-core-required` this is where the capping/dedupe/ordering rules must
  live so the TUI, the CLI and any future web view agree.

### 7.3 Phase C — live

- `live_sink` in `bounded_subprocess.py`; bounded `.live` logs (§6.2).
- `finalizers` refresh surface token; live tail behind the 5 s elapsed threshold.
- The finalizer output modal with `PanelTabStrip` tabs and `render_axe_output`.

### 7.4 Phase D — polish

- Config Center → Finalizers tab.
- A notification on finalizer `failed`/`refused` (the notification store already supports
  tags; `⛭` failures are exactly the class of event the inbox exists for).
- Dedupe diagnostics *at write time* in `ledger.record()` / `remember_result()` so no
  future run produces another 3.32 MB artifact.

### 7.5 Feature flag

Phases A–C span multiple landings and Phase A alone would expose a partial feature
(status + section, no live output). Per `sase/memory/sase_flags.md` this warrants one
`beta` flag, default off, created **only** with `sase flag new ace_finalizer_panel
--when-enabled … --when-disabled … --remove-when …`, removed by deleting the Off branch
when Phase C lands. Both states need tests.

### 7.6 What makes it beautiful

- It reuses the existing visual language completely — the same fold glyphs, the same
  heading style, the same field-label color, the same ANSI log renderer, the same
  `format_duration`. Nothing about it looks bolted on.
- It is quiet by default. A successful finalizer adds **one line** to the detail panel and
  **zero** glyphs to the row. The UI only gets louder when something needs a human.
- It has a real information hierarchy rather than a dump: glyph → line → row → attempt →
  tail → full output, each one keypress deeper, each one answering a question the previous
  level raised.
- The attempt gauge, the deferral path list, and the drift warning each tell the user
  something they genuinely could not have known — which is the difference between a
  status display and an instrument.

---

## 8. Alternatives Considered And Rejected

1. **A fourth `DetailPanelMode` (`AUTO → TOOLS → FINALIZERS → INFO`).** Rejected: the `]`
   cycle is already three deep, and mode-cycling hides content behind stateful keys. The
   finalizer payload is small and *belongs with* the other turn metadata, not in a
   competing full-height panel. It would also displace the file panel, which is the thing
   users actually stare at.
2. **Model finalizer runs as proc shells / family members.** Rejected: contradicts
   `decisions:host-owned-completion` (a shell implies agent ownership; finalizers are
   host-owned) and `decisions:single-turn-agents` (attaching a shell *terminates* the
   turn, whereas finalizers run inside it). It would also pollute `sase agent list` and
   the family roster with rows that have no independent lifecycle.
3. **Add `Running` to `FinalizerInstanceStatusWire`.** Rejected: a v2→v3 wire bump across
   Rust + Python + provider result-schema digests + the historical-refusal corpus, for a
   presentational need. §6.1's journal is additive and also supplies the missing
   timestamps.
4. **Stream finalizer output into the agent's `live_reply.md`.** Rejected: that file is
   the agent's *reply* and feeds chat transcripts and family fork context. Injecting
   host-owned subprocess output would corrupt transcripts and directly worsen the monitor
   prompt-bloat problem. A separate bounded log costs nothing extra.
5. **A top-level "Finalizers" tab.** Rejected: finalizers have no life independent of an
   agent turn; the tab would be empty most of the time. The Agents tab is the correct
   home — which is what was asked for.
6. **Render `finalizer_result.json` in a JSON viewer.** Rejected: the 3.32 MB outlier, and
   the format is designed for machines. A viewer would be a non-answer to "what happened."
7. **Poll `finalizer_result.json` on a timer for every visible agent.** Rejected outright
   by `tui_perf.md` rules 5, 8 and 14 — new refresh code paths, render-path stats, and
   idle ticks that reload unchanged surfaces. Surface tokens for the selected agent only.

---

## 9. Risks And Test Plan

| Risk | Mitigation |
| --- | --- |
| A 3.32 MB result file freezes the panel | Pre-parse size ceiling (1 MiB) + dedupe + `⚠ result too large — press E` row. Regression test with a synthetic 4 MB fixture asserting no parse. |
| `severity: error` diagnostics on successful runs paint everything red | Attempt-scoped severity, mirroring `is_retryable_result()`. Test with the real `dirty_work_discarded` corpus shape. |
| Live tail flickers on 2-second finalizers | 5 s elapsed threshold before any tail renders. |
| Spinner sticks forever if the runner is killed mid-phase | Journal's unmatched `attempt_started` + the existing stale-running cleanup path render `interrupted`. Test by truncating the journal. |
| New per-tick I/O regresses idle CPU | `refresh.auto_tick` counters must show zero extra surfaces reloaded on a quiet tick; add to `tests/perf/bench_tui_trace.py` and verify with `SASE_TUI_TRACE=1` per `docs/perf_runbook.md`. |
| j/k p95 regression from the new section | `pytest -s -m slow tests/ace/tui/bench_tui_jk.py`, target p95 < 16 ms unchanged. |
| Live sink deadlocks the subprocess drain | The sink is called inside the existing reader thread under the existing lock; sink errors must be swallowed. Test with a sink that raises and a 10 MB output producer. |

New tests: `tests/test_finalizer_progress_journal.py`,
`tests/test_agents_tab_finalizer_section.py`,
`tests/test_finalizer_live_output_sink.py`, plus fixtures for each of the seven instance
states and the three phase states. Both flag states per `sase_flags.md`.

Verification per `sase/memory/lint_and_test.md` before landing any of it.

---

## 10. Open Questions For The Lead

1. **Should `FINALIZING` be a distinct status word or a suffix on `RUNNING`?** A distinct
   word is clearer but touches every status-bucket set and every query filter. A suffix
   (`RUNNING ⛭`) is cheaper. I recommend the distinct word — the clarity is the feature.
2. **Where exactly does the section sit relative to `BEAD` and `PLAN`?** I recommend
   after `SHELLS`/`WAIT` (lifecycle grouping), but this is worth one look at a real panel.
3. **Should a failed finalizer raise a notification by default, or only when it fails the
   run?** 6.7% non-success on ~58 runs/day is ~4 notifications/day, which is tolerable;
   `deferred` should certainly not notify.
4. **Is a second finalizer (`check`) worth configuring as part of this work?** The panel
   is far more compelling with a real pipeline, and `builtin@command` already supports it
   — but it changes turn latency for every agent, so it is a separate decision.
