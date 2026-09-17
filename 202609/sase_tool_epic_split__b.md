# Splitting the `sase tool` work into epics

**Researcher B** · 2026-09-17 · host **apollo** · sase master `14403c1594` · core pin
`e210d18a80` (published `v0.34.47`)

**Question.** Where does the `sase tool` work start, is it genuinely large enough to
split into several epics that each produce a result a normal user can verify, and what
in-flight epic work conflicts with or complements it?

**Input reviewed.** `research:202609/sase_tool_control_plane/sase_tool_control_plane.md`
(the consolidated use-case/UX report, 2026-09-14, athena). Everything else below is my
own verification against today's tree, today's bead store, and a fresh measurement of
**apollo** — a second machine the earlier research never sampled.

---

## 1. Answer up front

**Yes — this is six epics, not one, and the cut lines are already visible in the code.**

The reason is not size alone. It is that the work contains six *different products* with
different evidence needs, different failure modes, and — critically — different
prerequisites in *calendar time*: prediction cannot be good until a corpus has
accumulated for weeks, and admission cannot be priced until prediction is calibrated.
Bundling them means the whole thing closes at the speed of its slowest, riskiest part.

| # | Epic | Size | User-verifiable result |
| --- | --- | --- | --- |
| **T1** | `sase tool` — catalogued commands with a durable run record | large (~10–11 phases) | `sase tool run check` runs with one line per stage; `sase tool runs` / `show` reprint the timeline afterwards; `sase tool list` shows last result + typical duration |
| **T2** | Failure triage: NEW vs KNOWN vs FLAKY | medium (~6) | a failed run labels each failure NEW or KNOWN; `sase tool failures` groups today's red-master signatures across agents |
| **T3** | Verification receipts and reuse | medium (~6–7) | the second `sase tool run check` on an unchanged tree returns instantly citing a receipt; `just install` no-ops; `sase tool receipt check` exits 0 |
| **T4** | Tool runs on the surfaces | medium (~6) | a live run shows on the owning agent's row in `sase tui`; its detail card shows stages and log tail; the old Tools panel is now **LLM Calls** and links to the run |
| **T5** | Forecast, overdue, and the inline-vs-hand-off decision | large (~8–9) | `sase tool run check-full` decides inline vs hand-off and says why in one line; rows show `6:12 / ~9m`; `sase tool stats` reports ≥80% interval coverage |
| **T6** | Fair admission for tools, agents, and workers (the `sase-zm` successor) | large (~10) | a second heavy run queues with an expected start instead of oversubscribing; the machine badge drill-down explains "why is apollo busy?" |

Optional **T7** (small): cross-machine prediction hints in `sase tool run -E`. Not
before T6.

Sequencing: **T1 → {T2, T3, T4 in parallel} → T5 → T6.** T2/T3/T4 are independent
consumers of T1's record; T5 wants ≥3 weeks of accumulated corpus; T6 wants T5's
calibration. On this project's measured epic cadence (parent epics `sase-zl` 2 days,
`sase-zt` 2 days, `sase-z4` 5 days, plus remediation chains) that is a few weeks of wall
clock, not a quarter.

Where to start is §8.

---

## 2. What exists today (verified, not assumed)

Knowing precisely what is already built changes the shape of the split, because three of
the six epics are mostly *integration* rather than construction.

**Already there, reusable:**

- **Three command runners already exist.** `sase proc run -- <argv>` (durable proc,
  `-w/--wait` streams and exits with the child's code), `sase monitor start -- <argv>`
  (agent-family member with `--next` follow-up, outcome profiles, prepared host
  completion), and `sase gate` (command-backed gates). `sase tool` is the **fourth**
  entry point for "run a command", and the only free name (`run`, `task`, `job`, `gate`
  are taken). A `sase tool` epic that adds a *fifth* supervisor would be a design
  failure; see D1 in §6.
- **The proc record already holds most of a ToolRun.** `~/.sase/procs/procs.jsonl` rows
  carry `argv`, `cwd`, `exit_code`, `created_at`/`started_at`/`finished_at`,
  `timeout_seconds`, `log_path`, `request_fingerprint`, `status`, `tags`,
  `concurrency_keys`, `workspace_num`.
- **Verification is already staged.** `just check` wraps **12** gates and
  `just check-full` **14** in `tools/run_silent "<stage name>"`, and `_lint-*` recipes
  are individually callable. `run_silent` already writes per-stage failure diagnostics
  (`stages/<id>.json`, `stage_output/`, byte quotas). It records **no timing and nothing
  on success** — a small, high-leverage gap.
- **A machine-local admission mechanism already runs in production** — in `tests/`.
  `tests/_suite_gate_lease.WorkerTokenLease` + `_suite_gate_env` implement a worker-token
  pool with a pool directory, 45-min default timeout, 30-min stale-heartbeat detection, a
  4-hour absolute max hold, a 30-second watchdog, and lease-env inheritance so
  descendants are not double-counted. T6 must *unify* this with `runner_capacity.rs`, not
  reinvent it.
- **Weighted agent admission is in Rust already**: `runner_capacity.rs`
  (`RUNNER_CAPACITY_POLICY_SCHEMA_VERSION = 5`) with records, holds, candidate
  evaluation, aging/deference; `sase.core.runner_slots` is the Python adapter;
  `max_running_agents: 10` is the single host budget.
- **Shared child supervision landed two days ago.** `src/sase/supervision/`
  (backoff, crash-loop, TERM→KILL, bounded log pump) was extracted on 2026-09-16 by
  `sase-11y.3`, and `detach_scope` (cgroup escape) landed the same day by `sase-11y.1`.
  Both are exactly what a tool executor needs, and both are *already closed phases*.
- **A tree-identity primitive exists**: `_observation_fingerprint()` in
  `src/sase/monitor/host_completion_state.py` keys on
  `(repo_id, head, head_tree, index_tree)` per repo — the natural seed for a receipt key.
- **Telemetry and stats scaffolding exist**: a metric catalog/subsystem registry
  (`src/sase/telemetry/`), a perf/stats query layer (`src/sase/stats/`), and SQLite
  already used inside core (`agent_scan/index.rs`, `agent_stats/activity.rs`).
- **A project config slot exists**: `sase/sase.yml` already declares
  `commit_hooks.before: "just fix"` and `vcs_provider.default_hooks: [just lint, just
  test]` — i.e. the repo already names its expensive commands in config, and those hooks
  are a natural later adoption point for the catalog.

**Not there at all:**

- No `sase tool` command (60 top-level commands; `tool` is unclaimed).
- **No load measurement anywhere.** Zero hits for `getloadavg`, `/proc/pressure`, or
  `loadavg` across `src/`, `tools/`, `tests/`. Nothing samples machine load today, so
  every load-conditioned claim in the consolidated report is un-backtestable until
  recording starts. This is the one thing that cannot be backfilled and is the strongest
  argument for T1 recording it before anyone needs it.
- No command reservation / tool demand: nothing in `src/` or `crates/` mentions a
  command reservation. `sase-zm` has landed **no code** (last commit naming it:
  2026-09-12; 14 phases, none closed).
- **No provider hook interception.** `src/sase/llm_provider/_tool_call_claude.py` is
  explicit that SASE no longer requests `--include-hook-events` or installs
  PreToolUse/PostToolUse hooks; Tools-panel rows come from stream-json events. So the
  consolidated report's "PreToolUse accelerator" is not a small opt-in — it means
  re-adopting a transport SASE deliberately dropped. **Instructions plus the wrapper are
  the only practical adoption lever**, which raises the stakes on T1 shipping the
  guidance changes with it (D5).
- A name collision: `src/sase/ace/tui/tools/` and `widgets/tools_panel.py` already mean
  *provider tool calls* (slow threshold `DEFAULT_SLOW_TOOL_CALL_THRESHOLD_SECONDS = 20`).
  "Tool" is currently taken inside the TUI.

---

## 3. Independent measurement: apollo, 14 days

The prior research measured athena. I measured apollo (2026-09-03 → 2026-09-17) from
`sase monitor list --all --json`, `~/.sase/procs/procs.jsonl`, and 230 agent-run
`tool_calls.jsonl` files (65 MB). Method and caveats in the appendix.

### 3.1 The premise replicates on a second machine

| Threshold | Bash calls | Share of calls | Share of Bash wall time |
| --- | --- | --- | --- |
| ≥ 5 s | 1,925 | 19.4% | **98.4%** |
| ≥ 20 s | 632 | 6.4% | **93.2%** |
| ≥ 60 s | 343 | 3.5% | 89.3% |
| ≥ 600 s | 108 | 1.1% | 73.7% |

9,921 duration-paired Bash calls, **71.5 wall hours**, p50 0.1 s / p90 12.4 s / p99 896 s
/ max 9,804 s. athena's figure was 88% of wall time in ≥20 s calls; apollo's is 93.2%.
**Wrapping only the slow commands captures essentially all of the wall time on both
machines.**

Wall hours by command (inline Bash, top rows): `just check` **42.26 h / 512 calls**
(59% of all Bash wall time), `just install` 5.78 h / 75, `just test` 5.63 h / 107,
`just check-full` **5.00 h / 41 calls inline** (the memory rule says monitor-only),
`pytest` 2.40 h / 605, `cargo test` 1.42 h / 70.

Agents choose badly in both directions, measurably:

- inline `just check` p75 = 113 s, **p90 = 1,412 s (23.5 min), max 4,503 s (75 min)** —
  turns held open for over an hour;
- three monitored `just check` hand-offs **failed in 4–7 seconds** — a whole agent-turn
  boundary and a follow-up agent spent on a 5-second lint failure.

That pair is the single cleanest justification for T5's automatic decision, and for
running cheap stages inline *before* handing off (T3).

### 3.2 Monitored verification on apollo is ~all waste, and the record can't even price it

- 69 monitors: 18 completed, 33 failed, 15 timeout, 2 stopped, 1 lost.
- **`just check-full`: 29 runs, zero reached `completed`** (18 failed, 10 timeout, 1
  lost). Of the 16 that recorded a duration: **16.24 hours, all of it in non-completing
  runs**, p50 742 s, p90 5,402 s, max 10,066 s (2.8 h).
- Hand-written continuation prose: **58 of 69 monitors carry `--next` text, median 1,778
  chars, max 5,803** (athena: 44%, median 1,450). This is the baseline-diff essay the
  consolidated report wants to delete.
- **Timeouts are guesses**: 14 distinct `timeout_seconds` values from 900 s to 28,800 s.
- **Opt-in features don't get adopted**: the `verify` outcome profile was used by **1 of
  69** monitors (athena: 1 of 1,054) and **prepared host completion by 0 of 69**
  (`host_completion_status` is null on every row). Prose rules and optional flags do not
  change agent behavior — the wrapper has to decide.
- **No concurrent duplicates**: zero repeated `request_fingerprint` values in 14 days,
  independently supporting the decision to defer single-flight joining.

**And a new finding: the durable record cannot answer "how long did it take".**
`elapsed_seconds` is present on only **30 of 69** terminal monitor rows, interleaved
across the whole window (rows as recent as 2026-09-15 lack it). Separately, **7,154 of
17,075 Bash `ToolUse` events (41.9%) never got a paired `ToolResult`** — agents killed
mid-call. Today SASE cannot price its own heavy work. Prediction (T5) therefore cannot be
built on the monitor or provider records; it needs T1's purpose-built record.

### 3.3 The proc store is disqualified as the corpus — measurably

`~/.sase/procs/procs.jsonl` holds exactly **101 rows** against
`procs.history_limit: 100`. The prediction corpus would be destroyed on a rolling basis
within days. T1 needs its own store with its own retention (D2).

### 3.4 Repeated verification is the largest addressable waste

Within single agent runs I found **236 repeated identical verification commands**
(`just check` 168 of them, plus `just install`, `just test`, `just test-visual`)
**totalling 37.2 wall hours** — against 71.5 total Bash hours.

Honest caveat, and it matters for how T3 is scoped: a repeat after an edit is *correct
behavior*, not waste. The wasteful subset is "repeat with an unchanged tree
fingerprint", and **that subset is unmeasurable today because nothing records a tree
fingerprint**. So 37.2 h is the *addressable population*, not a savings estimate — and
the fact that we cannot split it is itself the argument for recording fingerprints in T1
and shipping receipts as a separate, measured epic (T3) rather than assuming the payoff.

### 3.5 A confound that turns into T2's best feature

`just check-full` has been red on master since **2026-08-10** (`sase-j0`, task, size
large, +38 corroborations, reopened once: suite-cost budgets 3–18× over, plus two
ACE/Textual cause budgets). `sase-th` and `sase-10w` cover the red CI lanes and the
scoped lane escalating on stale coverage baselines.

So apollo's 16.24 wasted check-full hours are not 29 independent discoveries; they are
agents **repeatedly rediscovering one month-old known failure**, each one then writing a
~1,800-character essay to teach its successor how to tell it apart from a new failure.
That is precisely what NEW-vs-KNOWN signatures delete — and it is why I rank **triage
above prediction**, diverging from the consolidated report's phase order (§5).

Two direct consequences for planning:

1. **No epic's acceptance may require a green `just check-full`.** A month-old red master
   would otherwise block every exit gate. Design exit tests that are green-master
   independent.
2. The red master is a *free fixture* for T2: the KNOWN class can be demonstrated on real
   data on day one.

---

## 4. Why one epic would fail here (measured, not asserted)

I pulled every epic-tier bead (600 rows, 486 distinct root families) and measured the
remediation chains this project actually produces:

| Max chain depth in family | Families |
| --- | --- |
| 1 (closed without a remediation child epic) | 418 |
| 2 | 43 |
| 3 | 13 |
| 4 | 7 |
| 5 | 3 |
| 6 | 1 |
| 7 | 1 (`sase-xe`, 12 epic beads) |

86% of epics need no child epic; the 14% that do are concentrated in the big
infrastructure units — `sase-xe` (depth 7), `sase-ud` (6), `sase-z4`, `sase-11l`,
`sase-11e` (5), `sase-zw`, `sase-zt`, `sase-zr`, `sase-x7` (4). Phase counts of the
recent set: `sase-z4` 5, `sase-zt` 5, `sase-zw` 7, `sase-11y` 10, `sase-zl` 12,
**`sase-zm` 14 — the largest in the sample, and the only one with zero closed phases.**

What drives the deep chains is visible in the child titles — "Finish …", "Repair …",
"Ratchet the published core contract", "Perform the skipped-first live drill", "Deploy
and validate the … fleet". The recurring causes are (a) a landing audit finding
production requirements incomplete on a tree that moved underneath, (b) a **released**
core-wheel floor that must be ratcheted after the fact, and (c) **live, multi-machine
acceptance**. `sase-zl`'s own epic note is the archetype: "LANDING AUDIT — NOT READY TO
CLOSE … 20 proposed follow-up outcomes".

The planning lesson is not "fewer phases" but **"one epic, one released contract, one
acceptance surface"**: keep each epic's exit local (machine-local, CLI-visible), put
anything needing a published core floor early inside the epic that needs it, and never
put pixel-level TUI acceptance in the same unit as a supervision or admission cutover.
The architecture critique reached the same split conclusion from the design side
(`research:202609/command_capacity_epic_architecture_critique.md` §C1); the bead data
above is the independent empirical version of it.

---

## 5. Where I diverge from the consolidated report

The consolidated report's order is Record → **Predict** → Reuse/Triage → Admit. On
apollo's evidence I recommend Record → **Triage + Receipts (+ Surfaces)** → Predict →
Admit, for three reasons:

1. **Today's dominant waste is re-discovery, not mis-scheduling.** The measured
   populations are 37.2 h of repeated verification and 16.24 h of rediscovering one
   month-old known-red gate. Both are attacked by triage and receipts; neither needs a
   predictor.
2. **Prediction is gated on calendar time, not on engineering.** Load-conditioned
   quantiles need load samples, which do not exist yet (§2). Scheduling T5 third gives
   the corpus 3–6 weeks to fill *for free* while T2/T3/T4 ship. Starting T5 second means
   building a predictor against a backfilled corpus with no load dimension — exactly the
   uncalibrated guess the report warns against.
3. **Calibration is the honest gate for prediction, and it needs history to backtest.**
   `stats` reporting "≥80% of runs inside p10–p90, chronologically backtested" is a real
   exit criterion only if there is a chronology to test against.

I also fold the report's "cheap stages first" into **T3** rather than T5: the physical
stage order in `just check` is *already* cheap-first (12 lint gates before
`test-scoped`), so the missing behavior is not reordering — it is running the cheap
stages **inline before paying a hand-off**, and minting per-stage receipts the heavy
stage reuses. My 4–7 second failed hand-offs are the evidence.

---

## 6. Contract decisions to make *before* planning (this is the real "where to start")

Each of these is cheap to decide now and expensive to discover in phase 7. They are also
exactly where the in-flight epics collide, so §7 refers back to them.

- **D1 — One execution, one record; zero new supervisors.** A ToolRun is a *record*;
  execution is delegated to one of three existing executors: **inline** (child of the
  calling process), **monitor** (inside an agent — family member, `--next` follow-up,
  prepared completion), **proc** (outside an agent — detached, survives the shell). The
  record stores `executor` plus `monitor_id`/`proc_id`. Rule of thumb: *inside an agent,
  hand off to a monitor; outside an agent, hand off to a proc.*
- **D2 — A new per-machine, Rust-owned store with its own retention.**
  `~/.sase/tools/` (SQLite, like `agent_scan/index.rs`), ~180 days of run summaries and a
  much shorter horizon for logs, **registered as a `sase disk` owner in the same phase
  that creates it**, and kept out of Syncthing-replicated paths. Explicitly not the proc
  store (§3.3) and not procs retention.
- **D3 — Record everything from day one, use it later.** Fingerprints (tree +
  dirty-diff + declared inputs + toolchain + env allow-list), PSI/loadavg/ledger-load
  samples at start and every ~10 s, per-stage timings, normalized failure signatures.
  None of it is consumed in T1. All of it is impossible to reconstruct afterwards.
- **D4 — Free the word "tool" first.** Rename the TUI Tools panel to **LLM Calls**
  (widget, `src/sase/ace/tui/tools/` package, keymap entries in
  `src/sase/default_config.yml`, docs, and a glossary strand via `/sase_memory_write`) in
  T1's first phase. Otherwise every later phase, plan, and glossary strand equivocates
  between a provider tool call and a catalogued command. Also decide now that a provider
  Bash call that *is* a tool run links to the run instead of double-rendering it.
- **D5 — The wrapper decides, and the guidance lands with it.** Because provider hooks
  are gone (§2), adoption is instructions + the wrapper. `sase/memory/lint_and_test.md`
  and the `/sase_monitor` skill change **inside T1** (via `/sase_memory_write` and the
  skill source templates), and T1 carries an adoption metric computed from
  `tool_calls.jsonl` — which I verified is computable (§ appendix).
- **D6 — Admission is last, and `%hold` is the interim.** `sase-11l` is landing a
  durable, TTL-bounded, fail-open hold that makes selected WAITING/QUEUED agents wait
  without touching running work. A heavy tool run arming a hold is a cheap 80% stopgap
  that needs no ledger, and it keeps T6 honest: T6 is only worth building once
  predictions are calibrated.
- **D7 — Green-master-independent acceptance.** See §3.5. No epic exit may depend on
  `just check-full` being green.

---

## 7. Conflict and complement map with in-flight work

Ordered by how much they should change the plan. "Live" below means a commit naming the
epic landed within the last 48 hours.

### 7.1 `sase-11y` — Service host and Services tab (live; 10 phases, 2 closed)

The biggest interaction, and mostly a **complement**.

*Complements, already landed and usable today:* `src/sase/supervision/` (shared child
supervision: backoff, crash-loop detection, TERM→KILL, bounded log pump) and
`detach_scope` (systemd-run scope / setsid escape). A handed-off tool run **must** use
detach-scope, or a `sase service` restart will kill it.

*Real conflict:* phase `sase-11y.8` (`oneshots`) moves the TUI's `!` background commands
onto the durable proc store as **transient oneshot service procs with recorded exit codes
and durable rerun**, rendered in a dedicated Services-tab section with `▷/✓/✗` glyphs and
exit-code chips. That is, independently, "a recorded one-shot supervised command with a
rerun action" — the same sentence as a ToolRun. Two overlapping records of the same
execution is the failure mode to avoid.

*Recommended resolution (concrete):*

1. D1 stands: the tool epic adds **no** new supervisor and no new proc lifecycle.
2. **Keep the link on the tool side only.** Store `proc_id`/`monitor_id` on the ToolRun;
   do **not** add a `tool_run_id` field to the proc wire. `sase-11y.2` is already bumping
   the proc wire schema for its additive `service` block — a second concurrent additive
   field on the same wire is a gratuitous merge and floor-ratchet conflict.
3. Note the default-visibility trap: `sase-11y` hides rows carrying the `service` marker
   from the Procs tab and proc gear, and defaults the Procs query to `-service`. Tool
   procs are user-initiated work and must stay **visible**; do not reuse the `service`
   marker for them.
4. Sequencing: T1 can proceed during `sase-11y` because the supervision primitives it
   needs are the two *closed* phases. T4 (surfaces) should land **after**
   `sase-11y.7/.8` so the tool run card and the oneshot section are designed together
   rather than merged together.

### 7.2 The capacity family — `sase-zm` (stalled), `sase-z4`/`sase-zt` (closed), `sase-zp`, `sase-11l`, `sase-10h` (live)

All of T6, none of T1–T5. `runner_capacity.rs` (policy schema v5, with `agent_hold`
already wired into candidate evaluation) is the ledger T6 extends; `WorkerTokenLease` in
`tests/` is the second budget it must absorb; `sase-10h` ("gate approval never blocks on
weighted capacity") and `decisions:gates-never-block` constrain what T6 may block.
`sase-zp` is still renaming/threading queue capacity through bead work and approval — T6
must start after it settles or it will rebase continuously.

**`sase-zm` itself should be retired, not re-planned in place.** It has 14 phases, zero
closed, no landed code, and its own plan concedes drift risk. Its valuable content is the
keep-list already captured in the consolidated report §8. Recommended action in §8.

### 7.3 `sase-zw` / `sase-zw.8` — disk footprint and retention (live)

The epic's governing rule is that *every* class of disk SASE creates has an owner that
reclaims it on a bounded horizon, with `sase disk` visibility (`sase-zw.3` specifically
owns proc runtime retention). A new ~180-day tool store plus logs is a new disk class.
D2 puts its retention owner in the same phase as the store; do not defer it, or T1 lands
a leak into an epic actively hunting leaks.

### 7.4 `sase-zl` — Reliable monitor continuations (closed 2026-09-13)

Pure complement, and my apollo numbers reframe it: the machinery is *built and unused*
(verify profile 1/69, prepared host completion 0/69, hand-off prose median 1,778 chars).
`sase tool` is the adoption vehicle for it. T2 should make the tool's structured result —
outcome + NEW/KNOWN signatures + diagnostic refs — the **default** `--next` payload,
which is what finally deletes the essays. Note `sase-zm.5` was blocked on `sase-zl`; that
dependency dies with `sase-zm`.

### 7.5 Naming and vocabulary epics — `sase-113` (closed), `sase-11e` (live), `sase-lh`

Public names have moved: **ACE → TUI**, **AXE → Schedule**, background tasks → **procs**,
and `sase-11e` is mid-flight renaming lumberjacks/chops → **routines/jobs**. Consequences:
write every plan, CLI string, and glossary strand in the new vocabulary; keep T1–T4 out
of `src/sase/axe/**` while `sase-11e` is renaming there; and expect new glossary strands
(*Tool Run*, *Tool Catalog*, *Receipt*, *Failure Signature*) — all through
`/sase_memory_write`. D4's LLM Calls rename is one more instance of this house pattern.

### 7.6 `sase-x7` — Canonical-only across athena, mac, apollo (live)

Complement with a constraint: new wire types and stores should be born canonical (no
dual-format read compatibility, no legacy fallbacks), which is cheaper than what x7 is
paying to undo. Defer anything that *publishes tool data across machines* (T7) until x7's
shared-format cutover has settled.

### 7.7 TUI performance and freshness — `sase-124` (live), `sase-zu`, `sase-zn`, `tui_perf`

T4 constraint, not a blocker: chips and cards render from cached snapshots published with
change tokens, with no per-render filesystem access and no new polling loop. Land T4
after `sase-124` (Agents-tab freshness on large-archive hosts) so a new per-row field is
not added to a surface mid-repair.

### 7.8 `sase-s6` / `typed_launch_units`, `sase-kp`, `sase-rt`, `sase-j0`/`sase-th`/`sase-10w`

- `sase-s6` (stand-alone typed proc launch units, `%proc`, proc-shell UX;
  `typed_launch_units` beta flag is currently **on**): the path a non-agent `sase tool
  run -H` should use.
- `sase-kp`: the monitor machinery T1's in-agent hand-off leg rides.
- `sase-rt` (durable feature-flag controls in the Admin Center): helps roll each tool
  epic's beta flag on/off per machine from the TUI. Note there are already **13 open
  flags (4 beta)**; each tool epic owns exactly one and removes it before landing, per
  `sase_flags`.
- `sase-j0`/`sase-th`/`sase-10w`: see D7 and §3.5 — both the confound and T2's fixture.

---

## 8. Start here (concrete first moves)

1. **Retire `sase-zm` explicitly, before writing any plan.** It is the only in-progress
   epic whose scope the new epics take over, and leaving it open will keep drawing
   land-agent attention. Closing a plan bead with unclosed phases needs `--force` plus a
   non-`done` resolution:
   `sase bead close sase-zm --force -R superseded --reason "Superseded by the sase tool
   epic series (record-first); keep-list preserved in research:202609/sase_tool_control_plane/sase_tool_control_plane.md"`.
   Closing the epic parent is normally the land agent's job, so do this as the owner,
   deliberately. (`sase-zm.5`'s dependency on `sase-zl` disappears with it.)
2. **Write one decision record** (`decisions` web, via `/sase_memory_write`):
   *"Expensive commands are recorded before they are admitted"* — claim, the alternatives
   (admission-first `sase-zm`; recognition-by-profile; reusing the proc store), the costs
   (a new store, a new disk class, an adoption dependency on instructions), and the
   condition that would reopen it (a measured concurrent-duplicate or queue-starvation
   rate). This is the artifact that stops the next re-litigation, and it makes D1–D7
   citable from six plans.
3. **Land D4 (the LLM Calls rename) as a small stand-alone unit** — a task bead via
   `/sase_new_task`, or T1's first phase. It is independently user-verifiable ("the panel
   says LLM Calls") and it unblocks unambiguous writing everywhere else.
4. **Then write the T1 plan only** (via `/sase_plan`), with D1–D7 stated as invariants in
   its "Cross-cutting rules" section, and with T2–T6 named in it as successors so
   reviewers can see what T1 deliberately omits. Do not write six plans up front; T2–T6's
   content should be revised by what T1 measures.

---

## 9. The recommended epics in detail

Each epic below states its goal, a phase sketch, the flag it owns, its dependencies, the
**gesture a normal user performs to verify it**, and its **exit measurement**.

### T1 — `sase tool`: catalogued commands with a durable run record

*Goal.* Every expensive command in a project can be named in `sase/sase.yml`, run through
`sase tool run`, and afterwards answer "what ran, how long, which stage, why it failed,
where is the log" from the CLI.

*Phase sketch (~10–11).* (1) LLM Calls rename + glossary (D4). (2) Versioned Rust ToolRun
contract, state machine, and store + PyO3 bindings — **plus the published core floor
ratchet inside this epic**. (3) `tools:` catalog schema in `sase/sase.yml` +
`sase.schema.json` (`additionalProperties: false`, so this is a real schema change) +
loader. (4) `sase tool run` inline executor with byte-exact argv, mandatory `--` for
ad-hoc, preserved child stdout/stderr and exit status, and the compact agent-facing
summary. (5) Fingerprints (tree/dirty/inputs/toolchain/env allow-list), reusing
`_observation_fingerprint`'s tree identity. (6) Stage events: `tools/run_silent` gains
start/elapsed/success records; stage timeline persisted. (7) PSI/loadavg/ledger-load
sampling at start and every ~10 s (recorded, unused). (8) Hand-off leg `-H`: monitor
inside an agent, proc outside, via `detach_scope` and the existing supervisors (D1).
(9) `sase tool list` (bare default) / `runs` / `show --follow --log` / `status` / `stop`,
with versioned JSON on the control-plane views. (10) Retention owner + `sase disk`
integration (D2). (11) Backfill importer from `tool_calls.jsonl` + monitor records
(`source: imported`), guidance updates to `lint_and_test.md` and `/sase_monitor` (D5),
and the adoption/bypass metric.

*Flag.* `tool_runs` (beta, default off) → removed at the end of the epic.

*User verification.* `sase tool run check` prints one line per stage and a footer; after
it finishes, `sase tool show <id>` reprints the stage timeline with durations and a log
pointer; `sase tool runs` lists it; `sase tool list` shows `check`'s last result and
typical duration on this machine; `sase tool run -- echo hi` records an ad-hoc run and
still prints `hi` with exit 0.

*Exit measurement.* ≥80% of heavy (≥20 s) agent Bash wall time on apollo is wrapped,
computed from `tool_calls.jsonl` exactly as in the appendix; every completed run has a
duration (fixing the 30-of-69 gap in §3.2).

*Risk.* This is the largest unit. If planning pushes it past ~11 phases, split off
(11) as a small successor epic "**T1b — adoption and backfill**" whose own user-verifiable
result is `sase tool stats --adoption` plus the guidance change; do **not** split off (5)
or (7), because unrecorded data is unrecoverable.

### T2 — Failure triage: NEW vs KNOWN vs FLAKY

*Goal.* A failed run says which failures are new and which are the month-old known-red,
and one command groups them across agents.

*Phase sketch (~6).* (1) Signature normalization in Rust (strip `sase_<N>` workspace
paths, line numbers where unstable, worker ids). (2) pytest/lint diagnostic extraction in
repo tooling. (3) Classification against master/merge-base runs and
`just selection-health`'s flake baseline; verification-vs-infra split. (4)
`sase tool failures [TOOL]` with counts, affected agents, first-seen, and a
*suggested* (never auto-created) `ci`/`flake` bead via `/sase_new_task`. (5) Structured
`--next` payload replacing hand-written baseline prose (the `sase-zl` adoption leg).
(6) Docs + memory update.

*Flag.* `tool_failure_triage` (beta).

*User verification.* With master red exactly as it is today, `sase tool run check-full`
labels the suite-cost budget failures **KNOWN** and anything else **NEW**; `sase tool
failures` shows the `sase-j0` signature group with the number of agents that hit it and
when it was first seen.

*Exit measurement.* Median monitor `--next` length falls well below today's 1,778 chars;
every KNOWN signature in a week's runs maps to an existing bead.

*Why second.* §3.5. It is the cheapest large win available and it needs no predictor.

### T3 — Verification receipts and reuse

*Goal.* Work that has already passed on this exact tree is not paid for twice, and
failures that nothing has changed since are refused with an explanation.

*Phase sketch (~6–7).* (1) Receipt model and validity in Rust: scope `tree`
(shareable per machine) vs `workspace` (venv-local, for `install`), declared inputs, TTL.
(2) Minting on success + `sase tool receipt TOOL` (exit 0 iff a valid pass covers the
current tree/workspace) for scripts, finalizers, and landers. (3) Reuse path in `run`,
with `-R` to force; passes only — never reuse a failure. (4) Unchanged-since-failure
refusal ("nothing changed since this failed"). (5) `install` skip (the measured 5.78 h /
75 calls). (6) Cheap-stages-inline-before-hand-off with per-stage receipts the heavy
stage consumes. (7) `rerun RUN` as a linked attempt.

*Flag.* `tool_receipts` (beta).

*User verification.* `sase tool run check` twice on an unchanged tree: the second returns
in under a second citing the receipt and the run that minted it; touch a source file and
it runs for real; `just install` twice in a prepared workspace no-ops the second time.

*Exit measurement.* Measured hours avoided over two weeks, and — the honest one — the
share of §3.4's 236 repeats that had an unchanged fingerprint, now finally measurable.

*Caution to write into the plan.* Exit 0 is not proof of applicability (non-hermetic
tests, external services, time-dependent tests). Opt-in per tool, TTL'd, and
**host-completion policy — not the agent — decides whether a receipt satisfies a landing
gate**.

### T4 — Tool runs on the surfaces

*Goal.* A run in flight is visible where attention already is, and a finished run is one
keystroke from its evidence.

*Phase sketch (~6).* (1) Published snapshot contract with change tokens (the perf
contract from `tui_perf`). (2) Agent-row chip with reserved width
(`TESTING check 6:12`), amber overdue / red stalled once T5 exists. (3) Agent-detail
tool-run card: stage timeline, live log tail (reuse the monitor/proc-shell section
rendering), receipt, signatures, actions (stop, rerun, open log). (4) LLM Calls ↔ tool
run linkage (no double-rendering; managed runs use the richer source even under the 20 s
slow threshold). (5) A Tools pane (Runs view first; Stats/Failures views arrive with
T5/T2) + keymaps in `src/sase/default_config.yml`. (6) Visual snapshot coverage.

*Flag.* `tool_runs_tui` (beta).

*User verification.* Start a long `sase tool run` in one pane; the owning agent's row in
`sase tui` shows it live; `enter` opens the card with stage timings and a log tail; the
LLM Calls panel row for that Bash call links to the same card.

*Exit measurement.* No new per-render filesystem reads (the existing perf gates), and the
PNG snapshot matrix passes at the usual widths/themes.

*Dependency note.* Read-only consumer of T1 — genuinely parallel with T2/T3 — but land it
after `sase-124` and after `sase-11y.7/.8` (§7.1, §7.7).

### T5 — Forecast, overdue, and the inline-vs-hand-off decision

*Goal.* The tool decides how to run a command, and says what it expects, honestly.

*Phase sketch (~8–9).* (1) Load-bucket cohorts and empirical quantiles with transparent
fallback levels and sample counts (no ML). (2) Cheap covariates: selected-file count and
escalation flag from the test-selection store, which can price the scoped pytest stage
directly. (3) Conditional remaining time (survival-conditioned, never
`median − elapsed`), with right-censored timeouts reported as censor rates. (4) Overdue
and stalled states (`+4m over typical`, never a regenerated ETA). (5) `timeout: auto` =
`clamp(3 × p90, 10m, 3h)` per tool per machine — replacing the 14 hand-guessed values in
§3.2. (6) Automatic inline-vs-hand-off against the provider's inline budget, explained in
one stderr line. (7) `sase tool stats` with distributions, waste, change points, and
**calibration** (`--by bead|agent|epic`). (8) Notifications (finished / overdue / NEW
signature affecting ≥N agents) through the existing `dedup_key` store. (9) Stats view in
the Tools pane.

*Flag.* `tool_forecasts` (beta).

*User verification.* `sase tool run check-full` in an agent hands off and explains why in
one line; the same command with a small diff runs inline; `sase tool run -E` prints the
prediction, its basis, sample count, and the decision without side effects; `sase tool
stats check` shows p50/p90 by load bucket and the interval-coverage figure.

*Exit measurement.* ≈80% of runs fall inside the predicted p10–p90 band under
chronological backtest; predictions stay advisory until they do.

*Scheduling.* Start no earlier than ~3 weeks after T1 lands, so the corpus (including
load samples, which no backfill can supply) is real.

### T6 — Fair admission for tools, agents, and workers

*Goal.* One machine-local ledger admits agents, tool runs, and pytest workers, priced by
measurement.

*Phase sketch (~10).* (1) Absorb `WorkerTokenLease` and `runner_capacity` into one
accounting model with one meaning for "weight" (the command's own demand D). (2) Explicit
per-machine capacity in config + `sase init`/doctor. (3) Reservation ownership and
lifetime with boot and process-birth identity, keeping flock as the anti-leak floor.
(4) One fair queue with aging, expected start, and a finite default queue wait.
(5) `-w` demand, `-B` bypass (recorded as forced), `-W` max wait, with typed refusals
that print the executable retry command. (6) Suggested weights and a PSI-respecting
effective-capacity ceiling — recommended, never silently applied. (7) Backfill scheduling
for small requests that fit before a protected heavy one. (8) pytest concurrency drawn
from the shared grant. (9) Machine badge/meter drill-down: holders, queued demand, PSI
history, capacity source and freshness. (10) Coordinated rollout across athena, apollo,
mac + the break-glass runbook.

*Flag.* `tool_admission` (beta), plus a designed break-glass.

*User verification.* Start two heavy runs: the second reports a queue position and an
expected start rather than oversubscribing; selecting the machine badge in `sase tui`
explains why the machine is busy; `-B` runs anyway and the run is marked forced.

*Exit measurement.* Measured oversubscription episodes (PSI above threshold with >N heavy
runs) fall; no admission-caused starvation over a rollout window.

*Prerequisites.* T5 calibrated; `sase-zp`, `sase-11l`, `sase-10h` settled; D6's `%hold`
stopgap in place meanwhile. This is also the only epic with an inherently multi-machine
exit — the #1 driver of the deep remediation chains in §4 — so give it its own rollout
phase and expect one child epic.

### T7 (optional) — Fleet hints

Cross-machine predictions in `run -E` and the machine detail; **hints only** — no remote
dispatch, no cross-machine result caches (hermeticity is unestablished). After
`sase-x7`'s shared-format cutover.

---

## 10. Open questions for you

1. **Catalog placement.** `sase/sase.yml` (repo-owned, per project, no core release to
   tune) is what I recommend and what the consolidated report assumed. Confirm you want
   the catalog in the *repo* rather than machine config — it means a tool's price and
   stages are reviewed like code.
2. **Is `sase tool` the name?** It collides conceptually with provider "tool calls"
   (§2, D4). `sase tool` + the LLM Calls rename is my recommendation; the alternatives
   (`sase cmd`, `sase verify`) are each worse in a different way, and `run`/`task`/`job`
   are taken.
3. **`-w` for demand.** `sase proc run` already uses `-w` for `--wait`. If T6 wants `-w`
   for demand, that is a cross-command inconsistency worth choosing deliberately now
   (and `cli_rules` forbids making it a required option regardless).
4. **T1b.** Do you want adoption/backfill inside T1 (my recommendation: yes, because an
   unadopted wrapper measures nothing) or as a fast follow-on epic?
5. **T4 timing.** Surfaces third, or after T5 so chips ship with ETAs? I recommend third
   with elapsed-only chips; an invisible feature is an unadopted one.

---

## Appendix — measurement method and caveats

Everything in §3 is reproducible on apollo:

- **Monitors.** `sase monitor list --all --json --limit 500` → 69 rows,
  `20260903065322`–`20260917064712`. Grouped by substring of `command`; "wasted" = rows
  whose `monitor_state` is not `completed`. *Caveat:* `elapsed_seconds` is present on only
  30 rows, interleaved in time, so duration-weighted claims are restricted to those 30
  and are a lower bound; state-based claims (0 of 29 `check-full` completed) use all rows.
- **Procs.** `~/.sase/procs/procs.jsonl` → 101 rows against `procs.history_limit: 100`.
- **Bash calls.** 230 `tool_calls.jsonl` files under `~/.sase/projects/**`; pair
  `event: ToolUse` with `event: ToolResult` on `tool_use_id` within a file and difference
  `recorded_at`; discard negatives and anything over 6 h. 17,075 `ToolUse`, 9,921 paired,
  **7,154 unpaired (41.9%)** — agent killed mid-call or no result recorded, so totals are
  lower bounds. Runtimes present: codex 8,374, claude 7,150, grok 1,551. The same pairing
  is what T1's backfill importer and adoption metric should use.
- **Repeats.** Within one run, count the 2nd+ occurrence of an identical normalized
  command matching `just check|just test|just install|just lint` → 236 occurrences /
  37.2 h. *Caveat, restated because it matters:* a repeat after an edit is legitimate; the
  unchanged-tree subset is not measurable until T1 records fingerprints.
- **Red-master confound.** `sase bead show sase-j0` — `just check-full` red on master
  since 2026-08-10, +38 corroborations. Treat apollo's check-full failure rate as
  *rediscovery cost*, not as a new-defect rate.
- **Epic chain depth.** `sase bead list --tier epic --status all --limit 600`, grouped by
  root ID prefix; depth = max dotted components in a family. 600 rows, 486 families.
- **Absence claims.** `grep -rln "getloadavg\|/proc/pressure\|loadavg" src/ tools/ tests/`
  → no hits; `grep -rln "command_reservation\|CommandReservation\|tool_reservation"`
  across `src/` and `crates/` → no hits; `sase --full-help` → no `tool` command.
