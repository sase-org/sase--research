# `sase tool`: what a tool-call chokepoint unlocks, and the UX to build

Research date 2026-09-14 · host athena · SASE master `df58561174` · researcher B of a
two-researcher swarm.

**Question.** Once each SASE project's slowest tool calls run through a `sase` command,
what use-cases does that unlock beyond capacity admission? What is the best possible UX
for `sase tool`? The `sase-zm` epic is expected to be cancelled and re-designed, so this
report does not assume its shape.

**Inputs.**

- The `sase-zm` epic, its phase beads and `plan:202609/command_capacity.md`.
- Two earlier critiques of that epic: `research:202609/command_capacity_epic_critique.md`
  and `research:202609/command_capacity_epic_architecture_critique.md`.
- A code survey of the reusable infrastructure in this checkout.
- Web research on prior art.
- New measurements of 35 days of real tool-call and monitor history on athena.

Nothing was changed in any repository; this report is the only write.

---

## Summary

1. **The biggest opportunity is not the queue.** Its value is that `sase tool` becomes the
   one place where each expensive command is named, fingerprinted, timed, explained and
   remembered. Capacity admission is just one consumer of that record. The history on
   athena says most of the wasted time is not a capacity problem:
   - 61.3 of 67.2 monitored `just check-full` wall-hours went to runs that failed or timed
     out.
   - In 13 of the 23 recent failures with diagnostics, a lint gate failed first. Lint
     gates typically fail within seconds.
   - 44% of verification monitors carry hand-written prose telling the next agent how to
     tell pre-existing failures from new ones.
   - 176 times, a lane re-ran the same verification command right after it failed or
     timed out.

2. **Both of your ideas are right, and both get better with sharper framing.**
   - *Visibility:* treat a tool run as a first-class record. Show it on the Agents rows
     and in details, rather than adding a new top-level tab.
   - *End-time prediction:* feasible, and load visibly matters. Inline `just check`
     median duration goes 5.0 → 7.2 → 14.3 min as the number of overlapping heavy
     commands rises (0–2 → 2–5 → 5–10). But **no history on any surface today records
     machine load**, so recording has to start now.
   - The best uses of a prediction are not a countdown. They are:
     - deciding inline-vs-monitor automatically, so an agent never has to guess;
     - showing an expected start time for queued work;
     - backfill scheduling;
     - hang detection;
     - timeouts derived from evidence.

3. **The best use-cases you missed**, in order of evidence × leverage:
   1. Verification receipts and reuse, including skipping `just install` when its inputs
      are unchanged. Agents ran `just install` 1,798 times in 35 days, for 74.5
      wall-hours.
   2. Failure triage: NEW vs KNOWN vs FLAKY failure signatures, grouped across agents.
   3. Output sized for an agent's context window.
   4. Cheap-stages-first execution before reserving heavy capacity.
   5. Overdue/hang detection with evidence-derived timeouts.
   6. Weights calibrated from measured CPU/RSS/pressure, plus cost attribution per
      bead/epic.
   7. Duration-regression detection.

4. **Recommended UX, in brief.**
   - Each project declares named tools in `sase/sase.yml`.
   - Agents learn one verb: `sase tool run check -n '…'`. It decides reuse → inline →
     hand off → queue within a single turn and explains the decision on one line.
   - Bare `sase tool` is a per-tool dashboard.
   - Other subcommands: `runs`, `show`, `status`, `stop`, then `stats`, `receipt` and
     `failures`.
   - In the TUI:
     - a live `TESTING check 6:12 / ~9m` chip on agent rows;
     - a tool-run card in agent details;
     - an Admin Center **Tools** pane.

5. **Recommended sequencing: record first, admit last.**
   1. Backfill the new store from the history that already exists.
   2. Ship the recording wrapper.
   3. Add prediction and automatic hand-off.
   4. Add receipts and triage.
   5. Only then add the capacity ledger, calibrated by the recorded data.

   Step 2 is also the "observability first / shadow stage" that both earlier critiques
   asked for.

---

## 1. Starting point

- **`sase-zm` today.** It has 14 phases. `sase tool run/status` is one phase (`cli`)
  inside a larger capacity-ledger program. No `sase tool` code exists: `sase tool` is
  rejected as an invalid choice, and none of phases `.2`–`.14` has a progress note. Both
  of its prerequisites, `sase-z4` (weighted capacity) and `sase-zl` (monitor
  continuations), are now **CLOSED**, so a redesign can build on landed foundations.
- **Useful points from the earlier critiques,** adopted here rather than re-argued:
  - R7: the default should run inline if the command fits, and hand off otherwise.
  - R10: "weight" has three meanings across the command surface.
  - R11: `sase tool run` short options collide with `sase monitor start`'s letters.
  - R5: keep `flock` as the anti-leak floor under a durable ledger.
  - C1/C4: ship observability first, and add a shadow stage.
  - C3: provide a designed break-glass.
- **The framing shift in this report.** `sase-zm` treats the wrapper as an *admission*
  device that happens to record things. This report treats it as a *recording and
  decision* device that can admit later. Several of the critiques' concerns come from
  pricing and freezing the fleet without evidence. Those concerns shrink when the
  evidence arrives before the ledger does.

---

## 2. Evidence: what slow tool calls actually look like

### 2.1 Method

All measurements are from athena, read-only.

| Source | What was read | How |
| --- | --- | --- |
| Agent Bash calls | Every `tool_calls.jsonl` under `~/.sase/projects/` modified in the last 35 days: **4,564 files, 180,441 Bash calls with a duration** | Commands grouped into families with a regex (`just <recipe>`, `pytest`, `cargo <sub>`, `sase <group>`, …) |
| Monitor history | `sase monitor list -a -j`: **1,054 monitors** from 2026-08-13 to 2026-09-14 (sase 1,006, bob-cli 34, home 14) | Same grouping |
| Failure stages | The 60 most recent failed plain `just check` / `just check-full` monitors | `sase monitor show <id> --diagnostics` |
| Test-selection history | `tools/selection_health --json` | As reported |

Caveats:

- `duration_ms` is measured by the parser between the ToolUse and ToolResult events, so
  it is approximate.
- Grouping by regex over shell strings misassigns some compound commands.
- About 87,000 calls wrapped as `/bin/zsh -lc` with no recognizable family are left out
  of the table.
- All data comes from one host.
- Some recent monitor records have no `elapsed_seconds`.

### 2.2 Agents' own Bash calls (35 days)

**88% of all Bash wall time is spent in the 10,247 calls that took ≥20 s**, out of
180,441. That supports the premise: a small set of tool families dominates.

| Family | Calls | ≥20 s | Wall-hours | Median | p90 | Max | Projects |
| --- | --: | --: | --: | --: | --: | --: | --- |
| `just check` | 7,020 | 2,968 | **340.9** | 15 s | 610 s | 304 min | sase |
| `just install` | 1,798 | 884 | **74.5** | 19 s | 473 s | 27 min | sase |
| `just check-full` | 504 | 149 | 26.5 | 7 s | 445 s | 131 min | sase |
| `sase bead` | 10,919 | 832 | 25.5 | 3 s | 17 s | 130 min | sase, bob-cli |
| `pytest` | 7,404 | 766 | 18.9 | 4 s | 21 s | 12 min | sase |
| `just test-visual` | 805 | 289 | 16.5 | 16 s | 196 s | 34 min | sase |
| `just test-scoped` | 310 | 123 | 15.2 | 15 s | 537 s | 46 min | sase |
| `cargo test` | 1,131 | 459 | 11.1 | 12 s | 98 s | 8 min | sase, bob-cli (240) |
| `just fmt` | 928 | 110 | 8.3 | 10 s | 24 s | 32 min | sase, bob-cli |
| `just rust-install` | 124 | 53 | 6.5 | 13 s | 555 s | 24 min | sase |
| `just test` | 447 | 114 | 6.3 | 11 s | 114 s | 24 min | sase, bob-cli |

Observations:

- **Most heavy verification runs inline, not in monitors.** There were 7,020 inline
  `just check` calls and 709 of them ran ≥10 minutes. For comparison, there were 222
  `just check` monitors. Anything built only on monitors (including the monitor-based
  queueing in `sase-zm`) would see a small fraction of the real load.
- **The "only through a monitor" rule is not followed.** `lint_and_test.md` says
  `just check-full` must run only through `/sase_monitor`. Yet 504 `just check-full`
  calls ran inline, 50 of them for ≥10 minutes, the longest for 131 minutes. Prose rules
  do not steer agents reliably; a tool that decides for them would.
- **Durations cluster exactly at provider timeouts.** 28 `just check` calls ended within
  118–122 s, and a few calls ended at 598–602 s. That is consistent with a provider Bash
  tool timeout (Claude Code's Bash tool defaults to 2 minutes, 10 max) killing inline
  runs mid-flight. Those runs are paid for and then thrown away.
- **Fast `just check` calls mostly fail early.** The 15 s median suggests many calls die
  in a lint gate or setup step (see §2.4), not that `check` is fast.
- **`sase bead` itself shows up as a slow tool.** 832 calls took ≥20 s, and the longest
  took 130 minutes. Some of these may legitimately be long commands. Regardless, it
  shows that SASE's own CLI belongs in the corpus too.
- **The problem is not specific to the sase repo.** bob-cli contributes `cargo test`,
  `just fmt` and `just test` runs.

### 2.3 Monitored commands

| Command | Monitors | Completed | Failed | Timeout | Other | Successful-run duration |
| --- | --: | --: | --: | --: | --: | --- |
| `just check-full` | 318 | 30 | 264 | 19 | 5 | median 18.0 min · p10 11.2 · p90 25.9 (n=15) |
| `just check` | 222 | 59 | 157 | 5 | 1 | median 6.5 min · p90 19.0 (n=30) |
| `just install` | 40 | 10 | 28 | 2 | 0 | median 7.9 min (n=6) |

- **Wall time is overwhelmingly spent on runs that fail.** Of 67.2 wall-hours of
  `check-full` monitors, 61.3 were failed or timed-out runs. For `check`, it was 18.3 of
  22.9 hours.
- **Timeouts are guesses.**
  - `check-full` timeouts fired at limits of 45, 60, 90 and 120 minutes.
  - `check` monitors' timeouts fired at limits of 20–45 minutes.
  - 17 `check-full` monitors ended with exit −15 (SIGTERM).
- **176 re-runs.** In 176 cases, the same lane re-ran the same verification command right
  after the previous run failed or timed out.
- **Follow-up instructions are long.** The median `--next` action for a verification
  monitor is 1,450 characters (p90 3,105). **288 of 661 (44%)** verification monitors'
  reason or next-action text contains explicit reasoning about pre-existing, unrelated,
  flaky or "same N" failures. Two examples:
  - "If it reports the SAME 15 tests failing, treat as pre-existing; if ANY OTHER
    failures, stop…"
  - "Ignore failures clearly unrelated…"

  Agents are hand-writing baseline-diff logic as prose.
- **The existing profile is almost unused.** Only 1 of 1,054 monitors used `-p verify`;
  449 set `TESTING` by hand. Also, no recognizer attaches labels to commands.

### 2.4 Why verification runs fail

Sample: the 60 most recent failed plain `just check` / `just check-full` monitors. 37
had no captured stage diagnostics. The first failing stage of the other 23:

| First failing stage | Count |
| --- | --: |
| **Lint gates** (symvision 8, mypy 2, ruff 1, feature flags 1, toobig 1) | **13** |
| Test stages (full stage one 5, scoped tests 2, flake baseline 2) | 9 |
| Markdown fmt | 1 |

Individual diagnostics in the sample show the whole spectrum:

- a `check-full` landing gate that "failed in 12s on ruff F811";
- a `just install && just check` that died on an `ImportError` from a circular import in
  the tooling itself (an infra failure, not a verification one);
- a 45-minute `check-full` timeout that the next agent had to disambiguate against "the
  same 15 tests" failing on the baseline.

Two conclusions:

- Cheap-first ordering and fast failure feedback matter.
- Classifying *infra* vs *verification* failures, and *new* vs *known* failures, is the
  missing primitive.

### 2.5 Does machine load change duration?

Nothing records load, so as a stand-in I used the time-weighted number of *other* heavy
commands (inline `just check`, `just check-full`, `just test`, `just install`,
`just test-visual` calls of ≥30 s) that overlapped each run.

| Inline `just check` runs ≥60 s (n=2,087) | n | Median | p90 |
| --- | --: | --: | --: |
| 0–2 overlapping heavy commands | 1,581 | 5.0 min | 16.0 min |
| 2–5 | 437 | 7.2 min | 36.1 min |
| 5–10 | 69 | 14.3 min | 43.2 min |

The correlation is Pearson r = 0.31. For `just install` it is r = 0.16, with a flat
median (4.7 / 4.7 / 3.3 min). Install is mostly I/O and cache-bound; `check` is CPU-bound.

This is **confounded**: busy periods coincide with epic landings, larger diffs and
selection escalations. It is still consistent with contention, and it is large enough to
matter.

The monitor-only view shows almost no relationship (r = 0.04 for `check-full`), because
monitors miss most of the concurrent heavy work. **Lesson: load effects can only be
learned if load is recorded for every heavy run.** That argues for recording `/proc/pressure` and
capacity-ledger load at every wrapped run from day one.

The test-selection store on athena adds a second, pytest-level history:

- 2,346 scoped runs, of which **66% escalated**;
- scoped-run duration median 122 s, p90 649 s, max 3,779 s;
- 2,074 full runs;
- per-file timing tables.

The earlier `research:202609/test_feedback_speedup_decision.md` explains why escalation
is high. Its chain is a red CI baseline → missing coverage contexts → inflated selections
→ `serial-budget-exceeded`.

---

## 3. What already exists: reuse, don't rebuild

| Capability | Existing asset (file references from the code survey) | Gap for `sase tool` |
| --- | --- | --- |
| Supervised process, bounded log, durable record | Procs: Rust-owned `~/.sase/procs/procs.jsonl`, `src/sase/procs/supervisor.py` (2 MiB `BoundedLogPipe`). Monitors: `src/sase/monitor/`, `MonitorRecord` in `monitor/models.py:88-138` | **Proc history is pruned at `procs.history_limit: 100`** (`default_config.yml:81-84`), which would destroy a prediction corpus. Procs have no weight, agent-family or tree fingerprint |
| Per-stage diagnostics | `tools/run_silent` writes stage status and bounded failure output. `check`/`check-full` consist entirely of `run_silent` stages (`Justfile:649-687`) | No start time and no duration per stage |
| Per-test timings, flake evidence | Test-selection health store `~/.sase/test-selection/<project>/`: timings, `selection` and `full-run` records, cost records, `tests/reproducible_flake_baseline.txt` | pytest-only, sase-repo-only, and `full-run` records carry no duration |
| Observing agents' slow calls | `$SASE_ARTIFACTS_DIR/tool_calls.jsonl` (`llm_provider/_tool_call_*.py`), ACE Tools panel (`ace/tui/widgets/tools_panel.py`), slow-call reports (`ace/tui/tools/report.py`, 20 s threshold) | Observe-only after the fact, with approximate durations. **It is also a ready-made backfill corpus** |
| Metrics | Telemetry SQLite `~/.sase/telemetry/metrics.sqlite`, which already has `HOOK_DURATION`, `AGENT_RUN_DURATION` | No tool-run metrics |
| "Verified at tree X" | `sase final prepare` seals `head`/`head_tree`/`index_tree` plus the bound command. `monitor/host_completion_state.py` detects drift | No general, reusable receipt |
| Notifications | `notifications/store.py` with `dedup_key`, and `notify_workflow_complete` as a template | Monitors send no notifications |
| Capacity snapshot | Rust `runner_slots` (sum of claimed weights) | Measures reserved weight, not load |
| Machine health | Only `MemAvailable` in `tests/_suite_gate_budget.py` | **No loadavg or PSI sampling anywhere** in `src/`, `tests/` or `tools/` |
| Transparent interception | None. Claude runs with `--dangerously-skip-permissions`, Codex with `--dangerously-bypass-approvals-and-sandbox`, and SASE installs no PreToolUse hooks | SASE cannot rewrite an agent's `just check` today. Steering is instruction-only |

---

## 4. Use-case catalog

### 4.1 Your two ideas, sharpened

**U1. Surface tool runs in the TUI and CLI.** Yes, with one change of emphasis. Make the
*tool run* a first-class record, and render it where attention already is:

- the agent row that owns it;
- that agent's detail panel;
- the machine capacity detail;
- a history pane for looking back.

The data says inline runs are the majority, so the surface must show inline tool runs
*while they run*. Monitors alone are not enough. The TUI already turns proc and monitor
shells into Agent rows (`models/agent_proc_shells.py`, `_agent_monitor_section.py`), so
live output rendering exists to reuse.

**U2. Predict when a running command will finish.** Yes, it is feasible, and prior art
says simple predictors are enough:

- Tsafrir/Etsion/Feitelson's backfilling predictor is just the *average of the user's
  last two jobs*. It still cut wait time and slowdown by about 25%.
- Gaussier et al. show that penalizing underestimates beats symmetric error.
- Jenkins, GitLab and CircleCI present p50/p95 plus an "overdue" state rather than a
  live ETA bar.

Design notes:

1. **Key.** Use `(project, tool, machine)`, plus cheap covariates. For `check`, the
   selection manifest's selected-file count and escalation flag are known after the
   selection stage. Existing per-file timings let you estimate the scoped pytest stage
   directly: the sum of selected-file durations divided by workers. That beats a history
   median when selections range from 144 to 879+ files.
2. **Load conditioning.** At start, and every ~10 s, record:
   - PSI `cpu some avg10/avg60` and `memory some avg60` (Linux);
   - loadavg (all hosts; macOS falls back to loadavg and memory pressure);
   - ledger load/capacity;
   - the concurrent heavy tool count.

   Estimate quantiles from same-key runs in the same load bucket. Fall back to all
   buckets scaled by a learned load factor, then to the catalog default.
3. **Separate "if it passes" from "if it fails early".** Predict full-completion duration
   from runs that completed every stage. Show early failure as an outcome, not a missed
   prediction.
4. **Update in flight.** Remaining time is the sum of median durations of the remaining
   stages × the current load factor. Past p90, switch to **overdue**: show `+4m over
   typical` instead of inventing a new ETA. This is the Tsafrir-style "prediction grows
   as it is exceeded" behavior.
5. **Show ranges, not promises.**
   - On rows: `6:12 / ~9m`.
   - In details: `p50 8m · p90 14m · 42 similar runs · busy`.
   - Never a countdown to zero.
6. **Measure calibration.** `stats` reports what share of runs landed inside the
   predicted p10–p90 band (target ≈80%). Keep predictions advisory until calibrated.

The *best* consumers of a prediction are not the countdown. They are U8 (automatic
inline vs hand-off), U9 (expected start and backfill), and U7 (hang detection and
timeouts).

### 4.2 Use-cases you missed

**U3. Verification receipts and result reuse**, including skipping `just install`.

- *What.* Every successful run of a tool that declares its inputs mints a receipt keyed
  by a fingerprint:
  - git tree;
  - a hash of the dirty diff, including untracked non-ignored files;
  - the declared input files;
  - toolchain identity (Python, `uv.lock`, `sase-core-revision.txt`/wheel digest);
  - an allow-listed set of environment variables.

  A later identical request can reuse the pass (`✓ reused receipt`) instead of re-running.
- *Scopes.*
  - `tree` scope applies to verification tools. The receipt is shareable across
    workspaces on the machine.
  - `workspace` scope applies to environment-mutating tools such as `install`. The
    receipt is only valid in the workspace whose venv it built.
- *Evidence.*
  - 1,798 `just install` calls took 74.5 h. The p90 of 473 s is real rebuilds; the 19 s
    median shows how often it is cheap-but-not-free.
  - 176 re-runs after failure.
  - Epic landers re-verify trees that phase workers already verified.
- *Prior art.* Bazel "(cached)" test results with `--nocache_test_results`; Nx/Turborepo
  input hashing; Go `singleflight`; BuildBuddy action merging.
- *Guardrails.*
  - Reuse passes only.
  - Never reuse failures. Use them instead for a warning: "nothing changed since this
    failed 3 minutes ago — `-R` to re-run anyway".
  - Opt-in per tool.
  - Enforce a TTL.
  - The host-completion policy (not the agent) decides whether a receipt satisfies a
    landing gate.
  - Reuse `sase final prepare`'s observation fingerprint rather than inventing another.
- *Single-flight attach* (an identical run is already in flight, so wait on it instead of
  starting another): valuable in principle, but **unmeasured**. Monitor request
  fingerprints repeated only once, and they do not hash tree content. Record tree
  fingerprints first, measure how often duplicates occur, then decide. This follows
  `decisions:corpus-before-mechanism`.

**U4. Failure triage: NEW vs KNOWN vs FLAKY, across agents.**

- *What.*
  1. Normalize failures from stage diagnostics into stable signatures:
     - lint: rule + path + symbol;
     - pytest: nodeid + exception type + normalized message;
     - build: error code.

     Normalization strips `sase_<N>` paths and addresses.
  2. Classify each as *verification* (lint, assertion) or *infra* (tooling
     `ImportError`, exit 127, broken venv, core-binding mismatch, SIGTERM). This is
     Develocity Failure Analytics' split.
  3. Tag it NEW or KNOWN by comparing against recent runs of the same tool on the
     merge-base or master tree on this machine, and against the committed flake baseline.
  4. Tag it FLAKY when the same fingerprint has produced different outcomes.
- *Surfaces.*
  - `sase tool failures` shows "symvision: private import in `monitor/resume.py` — 6
    agents, last 2 h, first seen on master tree 3f2a". That is an early red-master alarm.
  - The agent-facing summary lists NEW failures first.
  - It suggests (does not auto-create) `ci` / `flake` task beads through the existing
    `/sase_new_task` flow.
- *Evidence.* 44% of verification monitors carry hand-written baseline-diff prose, and
  264 of 318 (83%) `check-full` monitors on athena failed.
- *Payoff.* `--next` instructions shrink from 1,450-character essays to "fix NEW failures".

**U5. Output sized for an agent's context window.**

- *What.* Inside an agent, the default output is:
  - a one-line header (tool, run ID, prediction);
  - one line per stage;
  - a footer with outcome, duration vs p50, NEW/KNOWN signatures, a bounded excerpt, and
    a log pointer.

  Reuse the monitor's existing `evidence_limits`: 8 KiB diagnostics, 4 KiB tail, 200
  lines. Human TTYs keep full streaming.
- *Evidence and prior art.*
  - Claude Code middle-truncates Bash output at about 30 k characters, so assertions in
    the middle are silently lost.
  - HumanLayer's `run_silent` pattern and Anthropic's compiler-harness guidance both say
    "a few lines, ERROR on one grep-able line, full log in a file".
  - PostToolUse hooks cannot rewrite output in Claude Code, so compaction must live in
    the wrapper.
- *Why the wrapper.* `tools/run_silent` does this per stage for this repo's `just`
  recipes only. The wrapper generalizes it to any project's tool, for example bob-cli's
  `cargo test`.

**U6. Cheap stages first.**

- *What.* The catalog declares stages with a cost class. `run` executes the cheap stages
  (lint, format check, type check) *inline, before* reserving heavy capacity or handing
  off to a monitor. A pass mints stage receipts that the heavy stage reuses.
- *Evidence.* In 13 of 23 diagnosed failures a lint gate failed first. Monitors show a
  `check-full` handed off and waiting only to fail in 12 s on ruff.
- *Cost.* Stage-callable recipes. This repo already has private `_lint-*` recipes.

**U7. Overdue and hang detection, and timeouts from evidence.**

- *What.*
  - A run is *overdue* past its load-conditioned p95. It is *stalled* when it is overdue
    **and** stage/pytest progress has stopped.
  - Default timeout = clamp(3 × p90, 10 min, 3 h) per tool per machine, instead of
    agent-guessed 20m/45m/2h.
  - Show amber in the TUI, and notify for human-started runs.
- *Evidence.* 19 `check-full` timeouts at 45–120-minute limits; 17 SIGTERM exits; the
  timeout clusters at 120 s and 600 s in §2.2.

**U8. Automatic inline-vs-hand-off: the killer application of prediction.**

- *What.* `sase tool run` knows the provider's inline budget (for example, Claude's Bash
  timeout) and the predicted p90.
  - If the predicted p90 fits within the budget and capacity fits, run inline.
  - Otherwise, hand off to a monitor with the given (or a default) `--next`.
  - An agent never has to choose between `just check` and `/sase_monitor`.
- *Evidence.* 504 inline `check-full` calls despite the rule; the 118–122 s clusters;
  `decisions:single-turn-agents`. The earlier critique's R7 asked for "inline if fits,
  hand off if not" for capacity reasons. Prediction makes the same rule work for *time*
  as well.

**U9. Scheduling that uses runtime estimates.**

- *What.*
  - Each queued request shows an **expected start** (like Slurm `squeue --start`).
  - Refusals say "capacity frees in ~4 min (tl7k2p check-full, p50)".
  - **Backfill:** admit a small tool request whose predicted p90 finishes before a
    protected heavy request is expected to fit.
- *Why it matters.* The earlier critique's R4 showed that `sase-zm`'s aging protection
  freezes the fleet because agents have no runtime estimates. Tool runs *do* have them,
  so backfill becomes possible for exactly the requests that cause head-of-line blocking.

**U10. Weights and capacity calibrated from measurement.**

- *What.* Record per-run child CPU seconds, peak process-tree RSS (via cgroup
  `memory.peak` when run in a transient scope, otherwise sampled), maximum concurrent
  processes, and PSI. From those, derive a *suggested* weight per tool per machine:
  `max(cpu_s / wall_s, peak_rss / unit_memory)`. Health data (PSI memory/CPU) can feed an
  effective-capacity ceiling.
- *Why it matters.* It answers the critiques' findings with data:
  - R1/C2: health-blind admission.
  - R2: the unpriced memory commitment of athena=32.
  - R15/R16: a hand-authored price table that lives in Rust.

  Price tables become versioned data with before/after evidence.

**U11. Cost attribution and waste accounting.**

- *What.* Machine-hours per tool, agent, bead, epic and Patch. Also "wasted" hours: failed
  or timed-out runs, and re-runs with an unchanged fingerprint. Show them on
  `sase tool stats --by bead` and optionally on bead pages.
- *Evidence.* 61.3 of 67.2 monitored `check-full` hours were failed or timed-out runs.
  Nobody can see today which epic burned them.

**U12. Duration-regression detection.**

- *What.* Take each tool's duration series, restricted to the quiet-load bucket, and run
  change-point detection on it (E-divisive / Hunter, as MongoDB does). Surface "`check`
  p50 stepped from 5 to 8 min after `abc123`" in `stats`, and suggest a bead.
- *Evidence.* The suite is growing (per the test-feedback report, roughly 1,800 new test
  lines landed in a day), and scoped-lane escalation is 66%.

**U13. Guardrails and nudges.**

- *What.*
  - Automatically hand off an inline `check-full`.
  - Warn on, or refuse, re-running after a failure with an unchanged fingerprint.
  - Skip `install` when nothing changed.
  - Report adoption: heavy Bash calls in `tool_calls.jsonl` that bypassed `sase tool`.

  This makes guidance in skills and memory measurable instead of hopeful.

**U14. Human notifications.**

- *What.* Notify when:
  - a human-started run finishes;
  - a run is overdue or stalled;
  - a NEW failure signature affects N or more agents.

  Use `dedup_key`, and let the Telegram plugin pass notifications through.

**U15. Cross-project catalog, and later cross-machine placement hints.**

- *What.* The same catalog shape works for bob-cli (`cargo test`) and for any project.
  Once per-machine history exists, `run --explain` can say "athena predicts 6 min;
  kellys_mbp predicts 25 min". Remote dispatch stays out of scope; this is a hint only.

**U16. Replay and audit.**

- *What.* `sase tool rerun <id>` re-executes the exact argv and cwd as a new operation.
  The typed argv history gives an audit trail of what agents ran, including forced runs.

### 4.3 Ranking

| # | Use-case | Evidence strength | Leverage | Build cost | Depends on |
| --- | --- | --- | --- | --- | --- |
| U1 | Live visibility | High (inline majority) | High | Low–Med | record |
| U5 | Agent-sized output | High | High | Low | record, stages |
| U8 | Auto inline/hand-off | High | High | Med | U2 |
| U3 | Receipts and install skip | High | High | Med | fingerprints |
| U4 | Failure triage | High | High | Med–High | stages, history |
| U2 | Prediction | Med–High (r=0.31) | Med (enabler) | Med | load samples |
| U6 | Cheap stages first | Med–High (13/23) | Med | Med | catalog stages |
| U7 | Overdue and timeouts | Med | Med | Low | U2 |
| U13 | Guardrails and adoption | High | Med | Low | record |
| U10 | Calibrated weights and health | Med (critiques) | High for admission | Med | resource samples |
| U9 | Expected start and backfill | Med | Med | Med | U2 + ledger |
| U11 | Cost attribution | High | Med | Low | record |
| U12 | Regression detection | Med | Low–Med | Low | history |
| U14 | Notifications | Low–Med | Low | Low | record |
| U15 | Cross-project/machine hints | Low–Med | Low (now) | Low | history |
| U16 | Replay and audit | Low | Low | Low | record |

### 4.4 Not yet

- **Cross-machine or remote result caches.** Test hermeticity is not established; the
  "Author identity unknown" class in the test-feedback report is exactly that.
- **Automatically filing beads.** Suggest them instead.
- **ML predictors.** Quantiles by load bucket are enough, per the prior art.
- **Profile matching by parsing arbitrary shell strings.** `sase-zm` rightly rejected
  this; named tools make it unnecessary.
- **A new top-level ACE tab.** Tabs are only agents/artifacts/axe. Use rows, details and
  an Admin Center pane.
- **Single-flight attach.** Wait until tree-fingerprint data shows duplicates are
  common.

---

## 5. UX principles

1. **Name the tool, not the shell string.** Tools are declared per project. Ad-hoc
   `-- argv` still works, but it is recorded as ad-hoc and never gets a receipt or a
   built-in price.
2. **One verb, one turn.** `run` decides reuse → inline → hand off → queue, prints one
   stderr line saying what it decided and why, and never leaves an agent to burn a turn
   discovering a refusal.
3. **Two audiences, one record.** Agents get compact summaries by default, human TTYs get
   streaming, and scripts get `-j` JSON. They are all views of the same `ToolRun`.
4. **Predictions are ranges, and honest about being overdue.** No fake precision, no
   countdowns.
5. **Recording fails open; admission fails closed, with a break-glass.** If the history
   store is broken, the command still runs and a warning is shown. The ledger's
   strictness must never take `just check` hostage (the earlier critique's C3).
6. **Every refusal is an executable next command.** This is the best idea in `sase-zm`;
   keep it.
7. **"Weight" means one thing: the command's own demand D.** The system, not the user,
   adds the agent's base B when a tool runs inline. With that rule, `-w` means the same
   thing inside an agent, inside a monitor and standalone. That resolves the earlier
   critique's R10 without new flag names.
8. **Shared concepts share letters with `sase monitor start`.** Use `-n` next, `-m`
   model, `-r` reason, `-t` timeout, `-i` idle timeout, `-C` cwd, `-f` completion, `-k`
   checkpoint, `-o` next-output, `-L` label, `-T` tail lines. New options take letters
   `monitor start` does not use (earlier critique's R11).
9. **Nouns read naturally.** `sase tool` is about *tools* (the catalog dashboard);
   *runs* are executions. Bare `sase tool` delegates to `list` per `cli_rules.md`.

---

## 6. Risks and open questions

- **False confidence from receipts.** Non-hermetic tests, external services and
  time-dependent tests can make a receipt wrong. Mitigations: receipts are opt-in per
  tool, carry a TTL, and landing-gate acceptance is host-completion policy.
- **Interception.** PreToolUse rewriting is provider-specific. Claude supports
  `updatedInput`; Codex has hooks whose details vary by version. It also struggles with
  compound strings (`just fmt && just check`) and would be a new provider contract. Lead
  with instructions and the catalog, add hooks as an opt-in accelerator, and track the
  bypass rate (U13).
- **Store growth and TUI performance.** The history store must not share proc pruning
  (limit 100). Summaries live in a Rust-owned store; the TUI reads cached snapshots off
  the pump. No per-keystroke scans, per `tui_perf` constraints.
- **Wrapper overhead.** The wrapper adds a Python CLI start on every call. It is
  negligible against minutes-long commands but noticeable on fast-failing ones. There is
  precedent for thin fast paths (`main/bead_fast_path.py`, `completion_fast_path.py`).
- **Portability.** PSI and cgroup peak memory are Linux-only. macOS needs loadavg and
  memory-pressure fallbacks, and history must be keyed by machine.
- **Duplicate records with monitors.** A tool run inside a monitor must produce *one*
  result record in the `sase-zl` continuation graph, not a parallel one. The tool's stage
  evidence should *become* the monitor's diagnostics.
- **Privacy.** argv and environment are recorded, so apply the existing redaction policy
  and never dump the whole environment.

---

## 7. Recommended solution

### 7.1 The shape in one paragraph

Build `sase tool` as a **per-project tool catalog plus one recording wrapper**:

- Every run of a declared tool produces a durable, Rust-owned `ToolRun` record: argv,
  attribution, fingerprint, stage timings, load and resource samples, the prediction made
  at start, outcome, and failure signatures.
- One verb, `sase tool run <tool>`, uses that history to decide in a single turn whether
  to reuse a receipt, run inline, or hand off to a monitor, and prints an agent-sized
  summary.
- The TUI shows live runs on the owning agent's row and history in an Admin Center Tools
  pane.
- Capacity admission comes **last**, as a consumer of measured weights and runtime
  estimates rather than the foundation.

### 7.2 Declare tools per project (`sase/sase.yml`)

```yaml
tools:
  check:
    argv: [just, check]
    labels: [TESTING, TESTED]
    stages: run_silent            # stage events from tools/run_silent (per-stage timing)
    cheap_stages: [lint, fmt]     # run inline before any heavy reservation/handoff
    receipt:
      scope: tree                 # shareable across workspaces on this machine
      inputs: [uv.lock, pyproject.toml, sase-core-revision.txt]
      env: [SASE_CORE_DIR]
      ttl: 24h
    weight: auto                  # recorded-evidence suggestion; explicit number allowed
    timeout: auto                 # clamp(3 × p90, 10m, 3h) once history exists
  check-full:
    argv: [just, check-full]
    labels: [TESTING, TESTED]
    stages: run_silent
    cheap_stages: [lint]
    receipt: { scope: tree, inputs: [uv.lock, sase-core-revision.txt], ttl: 12h }
    handoff: prefer               # always a monitor inside agents unless -I
  install:
    argv: [just, install]
    labels: [INSTALLING, INSTALLED]
    receipt:
      scope: workspace            # validates this workspace's venv only
      inputs: [uv.lock, pyproject.toml, sase-core-revision.txt]
```

Notes on the catalog:

- The catalog is data. The core owns its schema, fingerprint algebra, prediction and
  receipt validity. The repository owns names and inputs. Tuning never needs a
  `sase-core` release (earlier critique's R16).
- `default_config.yml` can ship an empty `tools: {}` and documented examples.
- `sase init` can offer to scaffold entries for detected `just`/`cargo`/`pytest`
  recipes, but it never guesses weights.

### 7.3 CLI

Subcommands, sorted alphabetically. Delivery phases are defined in §7.7.

| Subcommand | Purpose | Phase |
| --- | --- | --- |
| `sase tool failures [TOOL]` | Failure signatures across runs: NEW/KNOWN/FLAKY, count, affected agents, first seen, suggested bead | 3 |
| `sase tool list` *(bare default)* | Per-tool dashboard for the current project: last result, receipt for the current tree, typical duration on this machine, running/queued now | 1 |
| `sase tool receipt TOOL` | Exit 0 if a valid pass receipt exists for the current tree/workspace; print it (`-j`). Used by scripts, finalizers and landers | 3 |
| `sase tool rerun RUN` | Re-execute a recorded run's argv/cwd as a new operation (ignores receipts) | 3 |
| `sase tool run TOOL \| -- ARGV…` | Execute: reuse, inline, hand off or queue; record everything | 1 (auto-hand-off in 2, admission in 4) |
| `sase tool runs` | Run history plus running runs (`-a` all projects, `-A` agent, `-s` state, `-t` tool, `-j`) | 1 |
| `sase tool show RUN` | One run: stages with durations, prediction vs actual, load/resource samples, failure signatures, receipt, log (`--follow`, `--log`, `-j`) | 1 |
| `sase tool stats [TOOL]` | Duration p50/p90/p99 by machine and load bucket, outcome mix (lint/tests/infra), re-runs without change, wasted hours, calibration, change points (`--by bead\|agent\|epic`, `--since`) | 2 |
| `sase tool status` | This machine now: ledger load/capacity, PSI, running tools with elapsed/ETA, queued tools with expected start | 1 (queue parts in 4) |
| `sase tool stop RUN` | Stop a running or queued run; delegates to monitor stop or proc kill | 1 |

**`sase tool run` options.** The shared letters match `sase monitor start`; the new
letters avoid its alphabet.

| Option | Meaning |
| --- | --- |
| `-B, --bypass-capacity` | Start now even if capacity is full; recorded as forced. *(Phase 4)* |
| `-C, --cwd DIR` | Working directory (default: the agent's workspace, else `$PWD`) |
| `-E, --explain` | Dry run. Print the decision without side effects: catalog match, fingerprint, receipt hit/miss, prediction and basis, capacity fit, inline-vs-hand-off and why |
| `-f, --completion REF` | Bind a prepared host-completion intent (passed to the monitor on hand-off) |
| `-H, --handoff` | Always hand off to a monitor (the old `-q`); the queue wait happens inside the monitor |
| `-I, --inline` | Never hand off. Inside an agent, if the run does not fit or is predicted over budget, exit with a typed refusal and the exact retry command |
| `-i, --idle-timeout DURATION` | No-output timeout |
| `-j, --json` | Capture child output to the log instead of streaming it; print only the typed `ToolRun` result envelope on stdout |
| `-L, --label TEXT` | Row label override |
| `-m, --model MODEL` | Follow-up model on hand-off |
| `-n, --next TEXT` | Follow-up action on hand-off. Default inside agents: "Inspect the `<tool>` result and continue the interrupted task" |
| `-o, --next-output MODE` | As in `monitor start` |
| `-q, --quiet` | Summary only, even on a human TTY |
| `-R, --rerun` | Ignore any reusable receipt |
| `-r, --reason TEXT` | Why this run happens (shown in rows and follow-ups) |
| `-T, --tail-lines N` | As in `monitor start` |
| `-t, --timeout DURATION` | Execution timeout (default: catalog `auto`) |
| `-v, --verbose` | Stream full child output even inside an agent |
| `-W, --wait-timeout DURATION` | Maximum queue wait (default finite, per the earlier critique's R5). *(Phase 4)* |
| `-w, --weight UNITS` | The command's own demand D (required for ad-hoc argv only once admission is active) |

Rules for `run`:

- The delimiter `--` is required for ad-hoc argv, and argv after it is preserved exactly
  with no implicit shell (unchanged from `sase-zm`).
- Exit codes:
  - the child's status is preserved;
  - wrapper outcomes use one reserved code (75) **and** a typed record;
  - integrations must read the record, never the number alone.

**Specimen: agent, failure, compact by default.**

```text
$ sase tool run check
sase tool · check · run tl7k2p · athena 11/32 · predicted 5–16 min (busy) · inline
  ✓ fmt 8s  ✓ lint 51s  ✗ symvision 12s
✗ check failed in 1m11s at symvision (exit 1) — stopped before tests
  NEW    symvision private-import  src/sase/monitor/resume.py:88  _apply_resume_adoption
  Log    sase tool show tl7k2p --log   (212 lines)
```

**Specimen: agent, reuse.**

```text
$ sase tool run check
✓ check · reused receipt rc_9f3a — passed 7 min ago on identical tree 3f2a91c+dirty:7be0
  (sase-zm.3--2, 6m40s). Nothing to run. Use -R to run again.
```

**Specimen: agent, automatic hand-off by prediction.**

```text
$ sase tool run check-full -n 'Fix NEW failures, then reply to the user.'
sase tool · check-full · predicted 17–26 min > inline budget 2 min
  ✓ lint 58s (inline, cheap stage)
→ handing off tests to monitor sase-x--mon (TESTING); this agent's turn ends here.
```

**Specimen: human, bare `sase tool`.** Values are illustrative.

```text
gh_sase-org__sase · athena 19/32
TOOL        LAST RUN             THIS TREE             TYPICAL HERE         NOW
check       ✗ 4m ago · 1m11s     ✗ NEW 1 (symvision)   p50 5m · p90 16m     2 running
check-full  ✓ 2h ago · 18m03s    — no receipt          p50 18m · p90 26m    1 queued · starts ~6m
install     ✓ 1d ago · 47s       ✓ reusable (sase_25)  p50 19s · p90 8m     —
```

**Specimen: `sase tool status`.** Values are illustrative.

```text
athena · load 19/32 (agents 9 · tools 10) · PSI cpu 18% · mem 3%
RUNNING
  tl7k2p  check-full  sase-zm.3--mon   w15  12:04 / ~18m  ▰▰▰▰▰▰▱▱  tests (full)
  tq88aa  check       sase-10w.5--2    w1    3:10 / ~5m   ▰▰▰▰▰▱▱▱  scoped tests
QUEUED
  tz01bc  check-full  sase-zl.4--mon   w15  waiting 2m · expected start ~6m (after tl7k2p)
```

**Specimen: `sase tool stats check`.** The load-bucket values are from §2.5; the rest is
illustrative.

```text
check · athena · last 30 days · 2,087 runs ≥60s
duration   p50 5.0m · p90 16m · p99 43m
by load    quiet 5.0m · busy 7.2m · saturated 14.3m
outcomes   pass 31% · lint 36% · tests 27% · infra 4% · timeout 2%
waste      41 h on failed runs · 63 re-runs with unchanged fingerprint
forecast   78% of runs inside predicted p10–p90
changes    p50 5.0m → 7.9m after <commit> (<date>)
```

### 7.4 Agent integration

- **Guidance.** `lint_and_test.md` teaches `sase tool run check` and
  `sase tool run check-full -n '…'`. The "run `check-full` only via `/sase_monitor`" rule
  disappears, because the tool decides.
  - `/sase_monitor` remains for non-tool waits (sleep, CI watches, deploys).
  - `/sase_monitor` tells agents to use `sase tool run` for catalogued tools.
  - Change memory and skills through `/sase_memory_write` and source templates, as usual.
- **The inline budget** comes from provider configuration, for example Claude's Bash
  timeout and Codex's exec limits, with a conservative default when unknown.
- **Interception is opt-in, and second.** Later, SASE can install provider PreToolUse
  hooks where supported, rewriting exact catalog argv (`just check`) into
  `sase tool run check`. It does not rewrite compound strings. Instructions stay the
  primary mechanism, and the bypass rate from `tool_calls.jsonl` shows whether hooks are
  worth it.
- **Structured follow-ups.** A hand-off's default `--next` references the `ToolRun`
  result, including its NEW/KNOWN signatures, through the `sase-zl` result graph. That
  replaces hand-written baseline-diff prose.

### 7.5 TUI

1. **Agents rows.** An agent that has a running tool (inline *or* monitor) shows a chip:
   `TESTING check 6:12 / ~9m ▰▰▰▱`.
   - Amber `+4m over typical` when overdue.
   - Red `stalled` when overdue with no progress.
   - `w15` weight is shown only once admission exists.
   - The chip has a reserved-width ratio field so rows never reflow (earlier critique's
     R12).
2. **Agent detail → tool-run card.** Shows:
   - a stage timeline with durations;
   - live log tail, reusing `_agent_monitor_section` / `_agent_proc_shell_section`
     rendering;
   - prediction basis;
   - failure signatures with NEW/KNOWN/FLAKY badges;
   - receipt;
   - actions: stop, re-run, open log.

   The existing Tools panel (tool-call timeline) links to the card when a Bash call was a
   `sase tool run`.
3. **Machine capacity detail** (the capsule from the earlier meter design, if kept).
   Running and queued tools with ETA and expected start, PSI and load history, top
   consumers. This is how "why is athena busy?" gets answered.
4. **Admin Center → new Tools pane**, next to Procs and Statistics, with three sub-views:
   - *Runs:* filterable history;
   - *Stats:* per-tool distributions, load buckets, trend with change points, waste by
     epic;
   - *Failures:* signature groups with affected agents and a "suggest bead" action.

   Keymaps go in `src/sase/default_config.yml`.
5. **Notifications.** Finished (human-started runs only), overdue/stalled, and "NEW
   signature affecting ≥3 agents". Use `dedup_key` so repeats become `+1`s.
6. **Performance contract.** Chips and cards render from a cached snapshot published by
   the Rust store with change tokens. There is no per-render filesystem or network access
   and no new polling loop, per `tui_perf` constraints.

### 7.6 Data model and ownership

- **`ToolRun` wire record (Rust, versioned).**

  | Group | Fields |
  | --- | --- |
  | Identity | id; project; tool name and catalog digest (or `adhoc`); argv; cwd; workspace |
  | Attribution | agent / family / shell role; machine and boot identity |
  | Fingerprint | tree, dirty-diff, inputs, toolchain, env digest |
  | Prediction at start | p10/p50/p90, basis n, load bucket, inline budget, decision and reason |
  | Load samples | PSI, loadavg, ledger load, concurrent heavy tools; at start, periodic max, and end |
  | Resources | child CPU user/sys, peak RSS, maximum processes |
  | Stages | name, start, end, exit, diagnostic ref |
  | Outcome | typed wrapper outcome, child exit/signal, timeout kind |
  | Failure analysis | failure signatures and classification |
  | Receipt | minted/reused ref |
  | Capacity | demand, forced, queue wait *(phase 4)* |
  | Output | log ref |

- **Split of responsibilities.**
  - *Rust core:* fingerprint algebra, predictor, receipt validity, signature
    normalization, failure classification rules, stats aggregation, and later admission
    policy.
  - *Host adapters:* process supervision (reuse the proc/monitor supervisors), PSI and
    rusage sampling, log capture.
  - *Repository tooling:* stage events (`run_silent` gains start/elapsed), pytest failure
    extraction.
  - *Textual:* rendering only.
- **Storage.** A per-machine history store separate from procs pruning, for example
  `~/.sase/tools/` holding a SQLite database like telemetry.
  - Keep summaries for about 180 days and logs for less.
  - Also emit `TOOL_RUN_DURATION` telemetry.
  - Keep it out of Syncthing-replicated paths (earlier critique's R17).
- **Backfill.** A one-time importer turns 35+ days of `tool_calls.jsonl` Bash calls and
  monitor records into `ToolRun` rows. They are marked `source: imported`, carry no load
  samples, and have approximate durations. The dashboard and first predictions work on
  day one, and the importer doubles as the adoption metric.

### 7.7 Sequencing for the re-designed epic(s)

**Phase 1 — record.**

- Scope:
  - the catalog;
  - `run` as a recording wrapper with no admission (inline execution plus explicit
    `-H` hand-off through the existing monitor);
  - fingerprints, stage timing, load and resource sampling, compact agent output;
  - `list`, `runs`, `show`, `status`, `stop`;
  - Agents-row chips and the detail card;
  - the backfill importer;
  - guidance updates.
- Exit criterion: most heavy agent calls on athena go through `sase tool`, as measured
  from `tool_calls.jsonl`.

**Phase 2 — predict.**

- Scope:
  - load-bucket quantiles and in-flight updates;
  - overdue/stall states;
  - `timeout: auto`;
  - automatic inline-vs-hand-off (U8);
  - `stats` with calibration;
  - notifications.
- Exit criterion: about 80% of runs land inside the predicted p10–p90 band on athena.

**Phase 3 — reuse and triage.**

- Scope:
  - receipts (tree and workspace scope), including `install` skip;
  - "unchanged since failure" warnings;
  - `receipt`;
  - failure signatures with NEW/KNOWN/FLAKY;
  - `failures`, `rerun`;
  - cheap-stages-first;
  - the Admin Center Tools pane;
  - structured follow-ups.
- Exit criterion: measured hours saved by receipts, and a shorter median `--next`.

**Phase 4 — admit.**

- Scope: the command-reservation ledger, built with the recorded evidence:
  - measured, suggested weights (U10);
  - an effective-capacity ceiling that respects PSI;
  - expected start times and backfill (U9);
  - `-B` / `-W`, with the `flock` anti-leak floor and a designed break-glass;
  - fleet capacity meters.
- This is where `sase-zm`'s ownership, lifetime and nested-grant contracts belong. They
  would then be calibrated rather than guessed.
- Phase 1 has already run in shadow mode, so activation becomes a comparison, not a leap.

**Phase 5 — fleet hints (optional).** Cross-machine prediction in `run -E` and the
machine detail. No remote dispatch.

This ordering delivers value on every phase without the risky ledger. It turns the two
critiques' "observability first" and "shadow stage" into concrete scope. It also means
the eventual capacity numbers (athena 32, `check-full` +15) are backed by data.

### 7.8 What to keep from `sase-zm`, and what to change

**Keep:**

- the `--` argv contract with no implicit shell;
- typed refusal records with executable next commands;
- never inferring success from a shell string;
- one result graph with `sase-zl`;
- reservations tied to authoritative claim owners with boot and process-birth identity;
- no hold-and-wait upgrades;
- independent per-machine denominators;
- source-aware capacity initialization.

**Change:**

- Lead with recording, prediction, receipts and triage; admission comes last.
- Named catalog tools instead of profile matching.
- "Weight" always means command demand.
- Default to inline-if-it-fits, hand-off-otherwise, decided by capacity *and* predicted
  time.
- Option letters aligned with `sase monitor start`.
- A finite default queue timeout.
- Price tables as repository data calibrated by recorded CPU/RSS/PSI.
- A history store with its own retention instead of proc pruning.
- A TUI that puts live tool runs on the owning agent's row before building fleet meters.
