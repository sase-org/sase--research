# `sase tool`: a recorded control plane for expensive commands

**Consolidated report** · 2026-09-14 · host athena · SASE master `df58561174`
**Sources:** researcher A (`sase_tool_control_plane__a.md`, prior-art and forecast-design
survey), researcher B (`sase_tool_control_plane__b.md`, 35 days of measured athena
history), plus the lead researcher's own code verification and conflict resolution.

**Question.** Once each project's slowest tool calls run through `sase tool`, what
use-cases open up beyond capacity admission (the `sase-zm` epic, which will be cancelled
and re-designed)? And what is the best UX for the command?

---

## 1. Consolidated thesis

Both researchers converged, independently, on the same reframing: **the wrapper's value
is the record, not the queue.** `sase-zm` treats `sase tool run` as an admission device
that happens to record things. Invert that: every wrapped execution should produce a
durable, Rust-owned **ToolRun** record — identity, attribution, fingerprint, stage
timings, load samples, prediction, typed outcome, failure signatures, log reference —
and every consumer (CLI, ACE, agents, monitors, capacity admission, notifications) is a
view over that one record. Capacity admission becomes the *last* consumer to ship, and
by then it is calibrated by data instead of guessed.

B's measurements make this concrete. The waste on athena is mostly not a queueing
problem:

- **88% of all agent Bash wall time** (35 days, 180,441 calls) sits in the 10,247 calls
  that took ≥20 s — the premise of wrapping only slow tools holds.
- **61.3 of 67.2 monitored `just check-full` wall-hours** went to runs that failed or
  timed out. In 13 of 23 diagnosed failures, a *lint gate* failed first — usually within
  seconds of the heavy stage starting.
- **176 times** a lane re-ran the same verification command right after it failed or
  timed out; `just install` ran 1,798 times for 74.5 wall-hours.
- **44% of verification monitors** carry hand-written prose (median 1,450 chars)
  teaching the next agent how to distinguish pre-existing failures from new ones.
- **Most heavy verification runs inline**, not in monitors (7,020 inline `just check`
  vs 222 monitors; 504 inline `check-full` despite the "monitor only" rule), and inline
  durations cluster at provider Bash timeouts (118–122 s, 598–602 s) — paid-for runs
  killed mid-flight. Prose rules do not steer agents; a tool that decides for them
  would.

So the highest-leverage products of the wrapper are, in order: **failure-aware records
and receipts, decisions made for agents (reuse / inline / hand-off), and forecasts** —
with fair admission arriving last, on top of the evidence.

## 2. Direct answers to the three questions

**Surfacing runs in the TUI and CLI — yes,** but render them where attention already
is, and make the *tool run* (not the provider tool call) the first-class object. Inline
runs are the majority, so the surface must show runs while they execute, not just
monitors after the fact. See §6.

**End-time prediction — yes, feasible,** and load visibly matters: inline `just check`
median duration rises 5.0 → 7.2 → 14.3 min as overlapping heavy commands go 0–2 → 2–5 →
5–10 (r = 0.31). But **nothing on any surface records machine load today** (no loadavg
or PSI sampling anywhere in `src/`, `tests/`, `tools/`), so recording must start
immediately. Prior art says simple predictors suffice — Tsafrir et al.'s backfill
predictor is the average of the user's last two jobs and still cut wait/slowdown ~25%.
The countdown is the *least* valuable consumer of a prediction; the best consumers are
automatic inline-vs-hand-off, expected start for queued work, backfill, hang detection,
and evidence-derived timeouts. See §5.

**Missed use-cases — several,** the strongest being verification receipts and reuse,
failure triage (NEW/KNOWN/FLAKY), agent-sized output, cheap-stages-first, and automatic
inline-vs-hand-off. Full ranked catalog in §4.

## 3. Where the reports disagreed, and the resolutions

Both reports were verified against the tree at `df58561174`; the resolutions below are
grounded in checked code facts, not preference.

1. **Top-level ACE Tools tab (A) vs agent rows + Admin Center pane (B).** *Resolved for
   B.* ACE has exactly three top-level views — artifacts, agents, axe
   (`src/sase/ace/tui/_app_layout.py:65-67`) — and the Admin Center is the established
   home for fleet-operational panes (Procs, Statistics). Tool runs belong on the agent
   rows that own them (a chip), in the agent detail (a card), in the machine capacity
   drill-down, and in a new Admin Center **Tools** pane for history/stats/failures. A
   top-level tab is a structural change to revisit only if the pane proves too buried.
   **Keep A's orthogonal insight regardless:** the existing per-agent "Tools" panel
   (provider `tool_calls.jsonl`) and managed tool runs are different objects. Rename the
   existing panel **LLM Calls**, and when a provider Bash call *is* a `sase tool run`,
   link its row to the managed run instead of double-rendering the same work.
2. **Exact-argv-first with profile matching (A) vs named catalog tools (B).** *Resolved
   for B, keeping A's argv contract.* Only 1 of 1,054 monitors ever used the existing
   `-p verify` profile, and no recognizer attaches labels — recognition-by-matching has
   already failed in practice. Projects declare named tools in `sase/sase.yml`; agents
   run `sase tool run check`. Ad-hoc `run -- <argv…>` stays supported with A's rules
   (mandatory `--`, byte-exact argv, no implicit shell, never inferred success) but is
   recorded as ad-hoc and earns no receipt or built-in price.
3. **`plan` subcommand (A) vs `run -E/--explain` (B).** *Resolved for B* under the "one
   verb, one turn" principle: the preflight is `run -E`, printing everything A's `plan`
   would (catalog match, fingerprint, receipt hit/miss, prediction and basis, capacity
   fit, inline-vs-hand-off decision and why) with no side effects.
4. **`cancel`/`retry`/`watch`/`logs` (A) vs `stop`/`rerun`/`show --follow/--log` (B).**
   *Resolved for B:* `sase monitor` already uses `list/show/resume/start/stop`, its bare
   invocation defaults to `list` (wired centrally in `_default_list_subcommands()`), and
   `monitor show` shows a monitor *and its captured output*. Matching those conventions
   beats importing `gh run`'s verbs. `rerun` re-executes the recorded argv/cwd as a new
   attempt linked to the original run (absorbing A's attempt-chain idea).
5. **Single-flight joining: near-term priority (A) vs defer until measured (B).**
   *Resolved for B*, per `decisions:corpus-before-mechanism`: monitor request
   fingerprints repeated only once in 35 days, and today's fingerprints do not hash tree
   content, so the concurrent-duplicate rate is unknown. Receipts (reuse of a *completed*
   pass) already capture the measured waste — the 176 re-runs and the 74.5 install-hours.
   Record tree fingerprints from day one; if they show concurrent duplicates are common,
   ship joining with A's constraints: opt-in per tool, multi-consumer result delivery,
   and one consumer's cancellation never kills work another still needs.
6. **Sequencing.** Both said observability-first; B is stricter (admission dead last)
   and the failure-dominated waste data supports that. Adopt B's phases, folding in A's
   discipline: define the versioned Rust ToolRun contract *before* the UI, and gate any
   scheduling use of predictions on measured calibration. See §8.

One cli_rules tension both reports missed: "options must not be required," yet both make
`-w` (demand) mandatory for ad-hoc argv once admission exists. Resolution: never make
argparse require it — in the recording phases ad-hoc runs record without demand, and
once admission is active an ad-hoc run without `-w` gets a *typed refusal that prints
the executable retry command including `-w`*, consistent with the keep-item "every
refusal is an executable next command."

## 4. Use-case catalog, ranked by evidence × leverage

| # | Use-case | Evidence | Notes |
| --- | --- | --- | --- |
| 1 | **Live visibility** — runs on agent rows, details, machine drill-down, history pane | Inline runs are the majority; capacity badge becomes an explanation surface | The two views: `status` = "what is happening now", `runs` = "what ran" |
| 2 | **Agent-sized output** — one-line header, one line per stage, footer with outcome + NEW/KNOWN signatures + bounded excerpt + log pointer | Claude middle-truncates Bash output ~30 k chars; `run_silent` proves the pattern per stage | Humans on a TTY keep full streaming; compaction must live in the wrapper (PostToolUse hooks cannot rewrite output) |
| 3 | **Receipts and reuse** — a successful run of a tool that declares its inputs mints a receipt keyed by tree + dirty-diff + declared inputs + toolchain + allow-listed env; identical later requests reuse the pass | 1,798 installs / 74.5 h; 176 post-failure re-runs; epic landers re-verify trees phase workers verified | `tree` scope (verification, shareable per machine) vs `workspace` scope (`install`, valid only for its venv). Reuse passes only; failures instead trigger "nothing changed since this failed — `-R` to re-run". Opt-in per tool, TTL, host-completion policy decides landing-gate acceptance; reuse `sase final prepare`'s observation fingerprint. Also A's provenance angle: a terminal run is a citable `tool:<run-id>` receipt for beads, Patches, and final responses |
| 4 | **Failure triage: NEW vs KNOWN vs FLAKY** — normalize stage diagnostics into stable signatures (strip `sase_<N>` paths), classify *verification* vs *infra*, compare against master/merge-base runs and the flake baseline, group across agents | 44% of verification monitors hand-write this logic as prose; 83% of `check-full` monitors failed | `sase tool failures` becomes an early red-master alarm ("symvision private-import — 6 agents, 2 h"); suggests (never auto-creates) `ci`/`flake` beads via `/sase_new_task`; `--next` essays shrink to "fix NEW failures" |
| 5 | **Automatic inline-vs-hand-off** — `run` compares predicted p90 against the provider's inline budget and capacity, then reuses, runs inline, or hands off to a monitor, explaining itself in one stderr line | 504 inline `check-full` despite the rule; timeout clusters at 118–122 s / 598–602 s | The killer application of prediction; an agent never chooses between `just check` and `/sase_monitor` again |
| 6 | **Cheap stages first** — run declared cheap stages (lint, fmt) inline before reserving heavy capacity or handing off; passes mint stage receipts the heavy stage reuses | 13 of 23 diagnosed failures died in a lint gate; one `check-full` hand-off waited in queue to fail in 12 s on ruff | This repo already has stage-callable `_lint-*` recipes |
| 7 | **Overdue/stall detection and evidence-based timeouts** — *overdue* past load-conditioned p95 (show `+4m over typical`, never a new ETA); *stalled* = overdue with no stage progress; default timeout `clamp(3 × p90, 10m, 3h)` per tool per machine | Timeouts today are guesses: limits of 20–120 min, 19 `check-full` timeouts, 17 SIGTERMs | |
| 8 | **Cost attribution and waste accounting** — machine-hours and *wasted* hours (failed/timed-out runs, unchanged-fingerprint re-runs) by tool, agent, bead, epic, Patch | 61.3 of 67.2 `check-full` monitor-hours wasted; nobody can see which epic burned them | `stats --by bead\|agent\|epic` |
| 9 | **Calibrated weights and health-aware capacity** — record child CPU seconds, peak RSS, PSI; *suggest* per-tool per-machine weights and an effective-capacity ceiling | Answers the epic critiques' health-blind-admission and hand-authored-price-table findings with data | Recommend, never silently rewrite policy (A's feedback-loop guardrail) |
| 10 | **Expected start and backfill** — queued requests show expected start (Slurm `squeue --start` analogy); refusals say "capacity frees in ~4 min"; backfill admits small requests whose p90 fits before a protected heavy one | Tool runs have runtime estimates, which is exactly what `sase-zm`'s aging protection lacked | Queue-start and execution-finish are different promises: display them separately, show `unknown` rather than fabricate |
| 11 | **Duration-regression detection** — change-point detection on quiet-load-bucket duration series ("`check` p50 5 → 8 min after abc123") | Suite growth is real: 66% scoped-lane escalation | Correlational language only ("correlated with high I/O load"), never unevidenced causal claims |
| 12 | **Guardrails and adoption metrics** — auto-hand-off inline `check-full`, warn on unchanged-fingerprint re-runs, skip no-op installs; measure the bypass rate from `tool_calls.jsonl` | Makes memory/skill guidance measurable instead of hopeful | |
| 13 | **Notifications** — human-started run finished; overdue/stalled; NEW signature affecting ≥N agents | `notifications/store.py` with `dedup_key` exists; monitors send none today | One durable run publishes once; CLI/TUI/Telegram subscribe |
| 14 | **Cross-project catalog, cross-machine hints** — same catalog shape for bob-cli (`cargo test`, which already contributes measured hours); later `run -E` compares per-machine predictions | Placement *hints* only; remote dispatch and cross-machine result caches stay out of scope (hermeticity unestablished) | |
| 15 | **Replay and audit** — `rerun` re-executes typed argv; the record is an audit trail of what agents ran, including forced runs | | |

**Deferred:** single-flight joining (§3.5), ML predictors (load-bucket quantiles
suffice), auto-filed beads (suggest instead), profile matching over shell strings,
cross-machine caches, a new top-level ACE tab.

## 5. Prediction design (merged)

1. **Key and covariates.** Cohort on (project, tool/profile version, machine, worker
   bucket, load bucket), plus cheap covariates known after the selection stage — for
   `check`, the selected-file count and escalation flag; per-file timing tables already
   in the test-selection store can price the scoped pytest stage directly (sum of
   selected-file durations ÷ workers), which beats any history median when selections
   range 144–879+ files.
2. **Record load from day one.** At start and every ~10 s: PSI `cpu some avg10/avg60`
   and `memory some avg60` (Linux; macOS falls back to loadavg + memory pressure),
   loadavg, ledger load, concurrent heavy-tool count. Monitors alone see almost no load
   relationship (r = 0.04) precisely because they miss the inline majority — every
   wrapped run must sample.
3. **Empirical quantiles with transparent fallback, no ML.** Match completed runs on the
   full key; back off progressively (compatible profile versions → nearby load buckets →
   machine class → project-wide); report p50, an 80% interval, sample count, recency,
   and the fallback level used. Weight recent samples; down-rank history across
   toolchain discontinuities. Store distributions (mergeable histograms or raw rows),
   never just means.
4. **Three separate clocks.** Queue time (request → admission), execution time (start →
   process-tree exit), end-to-end. Queue forecasts compound uncertainty across running
   holders — show a wider interval or `unknown`, never a fabricated start.
5. **Remaining time is conditional on survival.** Never `median − elapsed`: estimate
   `P(remaining ≤ r | total > elapsed, cohort, live stage)`. Stage transitions tighten
   the cohort. Separate "duration if it passes" from early-failure outcomes. Treat
   timeouts/cancellations/still-running as right-censored — report censor rates beside
   the estimate rather than discarding or misclassifying them.
6. **Honest display.** Rows: `6:12 / ~9m`. Details: `p50 8m · p90 14m · n=42 · busy`.
   Past p90: **overdue** (`+4m over typical`), not a regenerated ETA. Real stage/unit
   progress when structured; elapsed + historical range when generic; never a fake
   percent bar, never a countdown to zero, and `ETA — · n=2` when data is insufficient.
7. **Calibration gates influence.** `stats` reports the share of runs inside the
   predicted p10–p90 band (target ≈80%), plus underprediction rate, chronologically
   backtested. Predictions stay advisory — no admission, backfill, or placement use —
   until calibrated, and an interval that covers only 50% gets degraded or hidden.

## 6. Recommended UX

### 6.1 Per-project catalog (`sase/sase.yml`)

The catalog is data: the core owns schema, fingerprint algebra, prediction, and receipt
validity; the repository owns names, stages, inputs, and tuning (no `sase-core` release
to tune). `sase init` may scaffold entries for detected recipes but never guesses
weights.

```yaml
tools:
  check:
    argv: [just, check]
    stages: run_silent            # per-stage events from tools/run_silent
    cheap_stages: [lint, fmt]     # run inline before any heavy reservation/hand-off
    receipt:
      scope: tree                 # shareable across workspaces on this machine
      inputs: [uv.lock, pyproject.toml, sase-core-revision.txt]
      ttl: 24h
    weight: auto                  # measured suggestion; explicit number allowed
    timeout: auto                 # clamp(3 × p90, 10m, 3h) once history exists
  check-full:
    argv: [just, check-full]
    stages: run_silent
    cheap_stages: [lint]
    receipt: { scope: tree, inputs: [uv.lock, sase-core-revision.txt], ttl: 12h }
    handoff: prefer               # monitors inside agents unless -I
  install:
    argv: [just, install]
    receipt:
      scope: workspace            # validates this workspace's venv only
      inputs: [uv.lock, pyproject.toml, sase-core-revision.txt]
```

### 6.2 CLI

Bare `sase tool` delegates to `list` via the central `_default_list_subcommands()`
wiring. Subcommands (alphabetical, per cli_rules; phases from §8):

| Subcommand | Purpose | Phase |
| --- | --- | --- |
| `failures [TOOL]` | Signature groups: NEW/KNOWN/FLAKY, count, affected agents, first seen, suggested bead | 3 |
| `list` *(bare default)* | Per-tool dashboard: last result, receipt validity for the current tree, typical duration here, running/queued now | 1 |
| `receipt TOOL` | Exit 0 iff a valid pass receipt covers the current tree/workspace; print it (`-j`) — for scripts, finalizers, landers | 3 |
| `rerun RUN` | Re-execute a recorded run's argv/cwd as a new attempt linked to the original (ignores receipts) | 3 |
| `run TOOL \| -- ARGV…` | Execute: reuse → inline → hand off → queue, decided in one turn and explained on one stderr line | 1 (auto-hand-off 2, admission 4) |
| `runs` | Run history and live runs; filters `-a` all-projects, `-A` agent, `-s` state, `-t` tool, `-j` | 1 |
| `show RUN` | One run: stage timeline, prediction vs actual, load/resource samples, signatures, receipt, attempts; `--follow`, `--log`, `-j` | 1 |
| `stats [TOOL]` | p50/p90/p99 by machine and load bucket, outcome mix, waste, re-runs without change, calibration, change points; `--by bead\|agent\|epic`, `--since` | 2 |
| `status` | This machine now: ledger load/capacity, PSI, running tools with elapsed/ETA, queued with expected start | 1 (queue parts 4) |
| `stop RUN` | Stop a running/queued run; facade over monitor stop / proc kill, never a second cancellation path | 1 |

`run` rules and options:

- **Shared letters match `sase monitor start`** (`-n` next, `-m` model, `-r` reason,
  `-t` timeout, `-i` idle-timeout, `-C` cwd, `-f` completion, `-o` next-output, `-L`
  label, `-T` tail-lines); new letters avoid its alphabet: `-E` explain (dry-run),
  `-H` hand-off always, `-I` inline only (typed refusal + exact retry command if it
  doesn't fit), `-R` ignore receipts, `-q` quiet, `-v` stream fully, `-w` demand,
  `-B` bypass-capacity (phase 4, recorded as forced), `-W` max queue wait (phase 4,
  finite default).
- "Weight" means exactly one thing: the command's own demand D. The system adds the
  agent's base B for inline runs, so `-w` reads the same inside an agent, a monitor, or
  standalone.
- Foreground runs preserve child stdout/stderr byte-for-byte and the child's exit
  status; wrapper lifecycle text goes to stderr and collapses to one line on a TTY.
  Wrapper outcomes use one reserved exit code (75) *plus* a typed record; integrations
  read the record, never the number. No `--json` on the foreground data plane — `-j`
  captures output to the log and emits only the typed result envelope; control-plane
  views (`-E`, `runs`, `show`, `stats`, `status`) expose versioned JSON.
- Recording fails open (a broken history store warns and still runs the command);
  admission fails closed with a designed break-glass. Every refusal prints an
  executable next command with a stable run ID — the run ID survives refusal and
  resume; `rerun` creates linked attempts.

Specimen (agent, compact by default):

```text
$ sase tool run check
sase tool · check · run tl7k2p · athena 11/32 · predicted 5–16 min (busy) · inline
  ✓ fmt 8s  ✓ lint 51s  ✗ symvision 12s
✗ check failed in 1m11s at symvision (exit 1) — stopped before tests
  NEW    symvision private-import  src/sase/monitor/resume.py:88  _apply_resume_adoption
  Log    sase tool show tl7k2p --log   (212 lines)

$ sase tool run check
✓ check · reused receipt rc_9f3a — passed 7 min ago on identical tree 3f2a91c+dirty:7be0
  (sase-zm.3--2, 6m40s). Nothing to run. Use -R to run again.

$ sase tool run check-full -n 'Fix NEW failures, then reply to the user.'
sase tool · check-full · predicted 17–26 min > inline budget 2 min
  ✓ lint 58s (inline, cheap stage)
→ handing off tests to monitor sase-x--mon (TESTING); this agent's turn ends here.
```

### 6.3 TUI

1. **Agent rows:** a fixed-width chip for the owning agent's live run (inline *or*
   monitor): `TESTING check 6:12 / ~9m ▰▰▰▱`; amber `+4m over typical` when overdue,
   red `stalled` when overdue with no progress. Reserved-width fields so rows never
   reflow.
2. **Agent detail → tool-run card:** stage timeline with durations, live log tail
   (reuse the existing monitor/proc-shell section rendering), prediction basis,
   NEW/KNOWN/FLAKY badges, receipt, actions (stop, re-run, open log). The renamed **LLM
   Calls** panel links a wrapping Bash call to this card instead of double-rendering it;
   managed runs use their richer source even below the 20 s slow-call threshold.
3. **Machine capacity drill-down:** selecting a fleet badge/meter answers "why is
   athena busy?" — holders and queued demand with ETA and expected start, PSI and load
   history, top consumers, capacity source and freshness. The meter itself stays a
   meter.
4. **Admin Center → Tools pane** (beside Procs and Statistics), three sub-views:
   *Runs* (filterable history), *Stats* (distributions, load buckets, change points,
   waste by epic), *Failures* (signature groups with affected agents and a suggest-bead
   action). Keymaps go in `src/sase/default_config.yml`.
5. **Performance contract:** chips and cards render from cached snapshots published by
   the Rust store with change tokens — no per-render filesystem access, no new polling
   loop, lazy output loading (per `tui_perf`).

### 6.4 Agent integration

`lint_and_test.md` teaches `sase tool run check` / `run check-full -n '…'` and the
"monitor only" prose rule disappears — the tool decides, using the provider's inline
budget (Claude's Bash timeout, Codex's exec limits, conservative default when unknown).
`/sase_monitor` remains for non-tool waits and points agents at `sase tool run` for
catalogued tools. Hand-offs default `--next` to a reference to the typed ToolRun result
(NEW/KNOWN signatures included) through the `sase-zl` continuation graph — replacing
the 1,450-character baseline-diff essays. A tool run inside a monitor produces *one*
result record; its stage evidence becomes the monitor's diagnostics. Provider
PreToolUse interception (rewriting exact catalog argv) stays an opt-in accelerator
measured against the bypass rate — instructions and the catalog lead. All memory/skill
changes go through `/sase_memory_write` and the source templates.

## 7. Data model, storage, and guardrails

- **Rust core owns** the versioned ToolRun schema and state machine (states including
  `refused`, `queued`, `running`, `succeeded`, `failed`, `timed_out`, `canceled`,
  `interrupted`, `reconciling`), fingerprint algebra, predictor, receipt validity,
  signature normalization, stats aggregation, and (later) admission. **Host adapters**
  own supervision (reusing proc/monitor supervisors), PSI/rusage sampling, log capture.
  **Repository tooling** owns stage events (`run_silent` gains start/elapsed) and
  pytest failure extraction. **Textual renders only** — no independent lifecycle or ETA
  logic in the TUI.
- **Storage:** a per-machine Rust-owned store (e.g. `~/.sase/tools/`, SQLite like
  telemetry), with its own retention (~180 days of summaries, shorter for logs) —
  explicitly *not* the procs store, whose `history_limit: 100` pruning would destroy
  the prediction corpus. Keep it out of Syncthing-replicated paths; emit a
  `TOOL_RUN_DURATION` telemetry metric.
- **Backfill:** a one-time importer turns the existing 35+ days of `tool_calls.jsonl`
  Bash calls and monitor records into `source: imported` rows (approximate durations,
  no load samples). The dashboard and first predictions work on day one, and the
  importer doubles as the adoption metric.
- **Privacy:** never store an environment dump; separate protected execution argv from
  redacted display argv; let the catalog mark secret-bearing arguments and
  non-recordable outputs; run secret detection over command and output while stating it
  is incomplete; never use raw argv/cwd/output as metric labels; keep checksums and
  typed summaries after logs expire.
- **Receipt honesty:** exit 0 is not proof of applicability — non-hermetic tests,
  external services, and time-dependent tests can invalidate a receipt. Opt-in, TTL'd,
  fingerprint-complete tools only; host-completion policy, not the agent, decides
  whether a receipt satisfies a landing gate.
- **No automatic policy feedback loops initially:** forecasts inform people and agents
  before they influence admission; weights, timeouts, and placement stay
  authored-with-suggestions until the estimator is calibrated — otherwise a transient
  slowdown raises prices, cuts concurrency, changes the observations, and locks in a
  bad model.

## 8. Sequencing for the re-designed epic(s)

**Record first, admit last.** This is the shape both epic critiques asked for
("observability first", "shadow stage"), made concrete:

1. **Record.** Versioned ToolRun contract *first*, then: the catalog; `run` as a
   recording wrapper (inline + explicit `-H` hand-off through existing monitors, no
   admission); fingerprints, stage timing, load/resource sampling, compact agent
   output; `list`, `runs`, `show`, `status`, `stop`; agent chips and the detail card;
   the backfill importer; guidance updates. *Exit:* most heavy agent calls on athena go
   through `sase tool`, measured from `tool_calls.jsonl`.
2. **Predict.** Load-bucket quantiles, in-flight conditional updates, overdue/stall
   states, `timeout: auto`, automatic inline-vs-hand-off, `stats` with calibration,
   notifications. *Exit:* ~80% of runs inside the predicted p10–p90 band.
3. **Reuse and triage.** Receipts (tree + workspace scope, install skip),
   unchanged-since-failure warnings, `receipt`, `failures`, `rerun`,
   cheap-stages-first, the Admin Center Tools pane, structured follow-ups. *Exit:*
   measured hours saved by receipts; shorter median `--next`.
4. **Admit.** The reservation ledger `sase-zm` wanted — now calibrated: measured
   suggested weights, a PSI-respecting effective-capacity ceiling, expected start and
   backfill, `-B`/`-W` with the flock anti-leak floor and a designed break-glass, fleet
   meters. `sase-zm`'s ownership/lifetime/nested-grant contracts land here, against
   shadow-mode data rather than guesses.
5. **Fleet hints (optional).** Cross-machine predictions in `run -E` and the machine
   detail; no remote dispatch.

**Keep from `sase-zm`:** the `--` argv contract with no implicit shell; typed refusals
with executable next commands; never inferring success from a shell string; one result
graph with `sase-zl`; reservations tied to authoritative claim owners with boot and
process-birth identity; no hold-and-wait upgrades; independent per-machine
denominators; source-aware capacity initialization; atomic hand-off before releasing
the provider's claim. **Change:** lead with recording/prediction/receipts/triage; named
catalog tools instead of profile matching; one meaning for "weight"; inline-if-it-fits
decided by capacity *and* predicted time; monitor-aligned option letters; a finite
default queue wait; price tables as repository data calibrated by measurement; a
history store with its own retention; live runs on agent rows before fleet meters.

## 9. Why this is the right bet

The consolidated evidence says the fleet's scarcest resources are agent turns and
wasted wall-hours, not queue slots. A recorded control plane attacks both directly:
receipts delete duplicate work that measurably cost ~75+ hours in a month, triage
deletes the hand-written failure-diff prose that pads 44% of hand-offs, agent-sized
output stops silently losing the assertion in the middle, and prediction turns the
inline-vs-monitor guess — which agents demonstrably get wrong hundreds of times — into
a one-line decision the tool makes. Admission still matters, but it lands last, priced
by evidence, exactly as both critiques of the original epic demanded. Every phase pays
for itself even if the next one never ships.
