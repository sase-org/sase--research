# Planning E1 of the `sase tool` roadmap: the ToolRun ledger, with a landing contract you can test

**Researcher B** · 2026-09-19 · host **apollo** · sase master `59c82a36e8` · core pin
`8d5341a4d5` (core HEAD `4a8c6d4`, latest release `v0.34.58`, published floor
`sase-core-rs>=0.34.48`)

**Question.** How should the first epic of
`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` ("E1 — Named tools and
the ToolRun ledger") be implemented? And how do we make sure the epic's land agent hands
back concrete deliverables that Bryan can test himself?

**Inputs.** The roadmap and its two source reports, the control-plane report, today's
sase and sase-core trees, the bead store, the built-in phase-worker and land-agent
prompts, recent remediation plans, and fresh measurements taken on apollo today. I did
not consult the other researcher in this swarm.

---

## 1. Answer up front

**The roadmap's three pre-planning moves are already done. The next move is to write the
E1 plan, and the plan itself has to supply what the land agent lacks: a fixed checklist
of results to judge against.**

- `sase-zm` was closed as `superseded` on 2026-09-17.
- The `decisions:record-before-admit` record landed in `85d6fc74bb`.
- The **LLM Calls** rename landed on 2026-09-18 in `868abb2467`, which moved
  `src/sase/ace/tui/tools/` to `llm_calls/`. E1 therefore no longer needs a rename phase.

**Recommended shape:** seven phases, all `medium`, run one after another, with **no beta
flag**. The backfill importer is deferred. Two things carry every user-testable result:

1. A committed, runnable acceptance harness, `tools/tool_ledger_acceptance`, with a
   pytest twin. Every phase adds its own cases to it. You run it, and so do the acceptance
   phase and the land agent.
2. A closed, numbered **Definition of Done** in the plan body. Each item is a command and
   the result you should see. The plan tells the land agent to judge completion against
   that list and nothing else.

| # | Phase id | What lands | What you can try once it lands |
| --- | --- | --- | --- |
| 1 | `core-ledger` | Rust ToolRun/catalog contracts, SQLite store, state machine, retention, queries, PyO3 bindings, golden fixtures, core pin moved | A Python round-trip through the real bindings. Nothing user-facing yet. |
| 2 | `catalog` | `tools:` in `sase/sase.yml` plus the schema, whole-entry loader, the repo's own catalog, `sase tool` / `sase tool list` | `sase tool` prints the delegation notice and lists `check`, `check-full`, `install`, `test`, `test-visual` |
| 3 | `foreground-run` | Foreground executor, `run TOOL [-- ARGS]`, `run -- ARGV…`, `-q/-T`, `runs`, `show`, `show -l`; reconciliation of dead runs; fail-open recording; enclosing monitor/proc owner; disk row and reap step | Run a passing, failing, Ctrl-C'd and `kill -9`'d command, then inspect each with `sase tool show` |
| 4 | `stage-timeline` | Start and elapsed events from `tools/run_silent`; timeline ingestion; "unattributed" time; monitor stage JSON gains timings | `sase tool run check`, then `sase tool show <id>` lists every stage with its duration |
| 5 | `run-evidence` | Tree fingerprints taken before and after the run, dirty diff, inputs, toolchain, env allow-list; PSI/loadavg sampling every 10 s; nested-run parent ids; telemetry | `show` gains fingerprint and load sections; dirtying a file changes the fingerprint |
| 6 | `agent-adoption` | `docs/tool.md` "Try it", glossary strands, `lint_and_test` and `/sase_monitor` guidance, `tools/tool_adoption_report` with the baseline recorded | `tools/tool_adoption_report -d 7` shows how much heavy Bash time is wrapped versus bypassed |
| 7 | `acceptance` | Harness hardened and run against both the workspace build and the deployed `sase`; `check-full` run via a monitor, wrapped in `sase tool run`, under a named known-red rule; evidence artifact | `tools/tool_ledger_acceptance` prints PASS for every Definition of Done item |

The rest of this report gives the evidence (§2–§4), the contract decisions a planner must
settle (§5), phase detail (§6), the Definition of Done and harness (§7), risks (§8),
where I differ from the roadmap (§9), and the recommended solution with a draft prompt
for `/sase_plan` (§10).

---

## 2. What changed since the roadmap was written (2026-09-17 → today)

| Item | Roadmap assumption | Today |
| --- | --- | --- |
| `sase-zm` | "retire first" | **Done.** CLOSED, resolution `superseded`, 2026-09-17T19:30Z |
| Decision record | "write one" | **Done.** `decisions:record-before-admit` (`85d6fc74bb`) |
| LLM Calls rename | "E1's first phase or a preceding task" | **Done.** `868abb2467`; glossary strand `llm-calls` exists |
| `sase-11y` | 2/10 phases closed | **5/10 closed** (`.1`, `.2`, `.3`, `.4`, `.6`). `.8` (oneshot service procs) is still in progress, which matters to E2, not E1 |
| `sase-zw` | in progress | Phases `.1`–`.7` closed; child epic `sase-zw.8` in progress. It touches the `sase disk` inventory, which E1's phase 3 also edits |
| `sase-124`, `sase-x7`, `sase-11e`, `sase-11l`, `sase-zp`, `sase-10h`, `sase-j0` | in progress | All still in progress. `sase-j0` (`check-full` red on master) is still open with +38 |
| sase-core | pin `e210d18a80` | Pin `8d5341a4d5`; core HEAD `4a8c6d4` is 13 commits ahead. Nothing named `tool_run`/`ToolRun` exists in either repo |

**Verdict:** nothing in flight blocks E1. The only seam it shares with active work is
the `sase disk` inventory (`sase-zw.8`), and that is a small additive edit.

---

## 3. Fresh apollo measurements and what they mean for E1

All numbers come from today, on apollo. The method is in the appendix.

### 3.1 Heavy Bash commands, last 7 days (2026-09-12 → 09-19)

- **Volume:** 188 `tool_calls.jsonl` files, 12,974 Bash calls, **89.85 wall-hours**.
  Only 3 calls had no result row. The 09-17 report found 41.9% unpaired; that gap is gone
  in this window, so the adoption metric can now be computed reliably.
- **Premise holds again:** calls of 20 s or more are **6.5% of calls but 94.3% of Bash
  wall time**. Calls of 600 s or more are 1.0% of calls and 74.6% of wall time.
- **`just check` is the main target by a wide margin:** 157 inline calls, **51.1 h (57%
  of all Bash wall time)**. Inline durations: p50 **931 s (15.5 min)**, p75 1,809 s, p90
  2,675 s, max 5,150 s. The median is about eight times the p75 that researcher B measured
  a week earlier; apollo is much busier.
- **The rest of what could go into the catalog:** `just test` 57 calls / 6.7 h,
  `just install` 33 / 3.5 h, inline `just check-full` 2 / 3.0 h, `just test-visual`
  47 / 1.6 h, `pytest` 293 / 2.0 h, `cargo test` 53 / 1.4 h. Tools that `sase/sase.yml`
  can name account for **about 82% of heavy (≥20 s) Bash wall time**. That is the ceiling
  for any adoption target.
- **Agents already build their own compact output.** 32 verification calls (4.1 h) were
  hand-wrapped as `just check > /tmp/…log 2>&1; tail -n 220 "$log"`. A wrapper `-q`
  (quiet) option with `-T` (tail lines) should replace this directly.
- **Provider timeouts kill runs.** 29 calls ended at 120 ± 3 s and 11 at 600 ± 3 s. Today
  these look like ordinary completed calls. Under the wrapper they become recorded
  `interrupted`/`lost` runs with a duration, which gives SASE its first measurement of
  "killed by the provider."
- **Heavy calls by runtime:** codex 545, claude 250, grok 50. Codex wraps every command as
  `/usr/bin/zsh -lc '…'`, so any bypass classifier has to unwrap that. My first pass got
  this wrong and misfiled 92% of heavy calls.

### 3.2 Monitors (90 rows, 2026-09-03 → 09-18)

- **`just check-full` never passes:** 37 monitors, **0 completed** (25 failed, 11 timeout,
  1 lost), 27.2 recorded hours. `just check`: 29 monitors, 10 completed.
- **The `verify` profile is catching on:** 16/90 now, up from 1/69. Prepared host
  completion is still **0/90**.
- **Durations are often missing:** `elapsed_seconds` is present on only 51/90 rows.
- **Hand-written follow-up prose is still standard:** 74 monitors carry `--next` text,
  median **1,721 chars**.

### 3.3 Where `just check` time goes, estimated from existing monitor diagnostics

`tools/run_silent` stamps only an *end* time per stage. Subtracting consecutive end
stamps in 42 monitor diagnostic directories gives a rough profile. Treat it as noisy:
reruns in the same directory pollute the first stage of each run.

| Stage | p50 | p90 |
| --- | --- | --- |
| test (scoped) | ~1,219 s | ~1,578 s |
| test cost (`check-full`) | ~7,146 s | ~8,582 s |
| SASE validation | ~105 s | ~137 s |
| lint (symvision) | ~86 s | ~194 s |
| lint (feature flags) | ~81 s | ~110 s |
| lint (mypy) | ~52 s | ~90 s |
| lint (test waits) | ~40 s | ~51 s |

So roughly 7 minutes of lint and validation run before a scoped test lane of about 20
minutes. Nobody can see this breakdown today without this kind of reconstruction, which
is the concrete payoff of the `stage-timeline` phase. It is also the evidence E4 will
need for "cheap stages first."

### 3.4 How much the wrapper costs

- **sase startup:** 0.9–1.7 s cold (`sase --help` 0.92–1.15 s; `sase proc list`
  1.53–1.67 s). This is the fixed cost of wrapping. It is irrelevant for the 20 s+ tools
  E1 targets. It is also why the guidance should not tell agents to wrap sub-second
  commands.
- **Fingerprint:** `git status --porcelain=v1 --untracked-files=all` plus `rev-parse` plus
  `write-tree` take about 30–40 ms on this 10,651-file repo.
- **Load sample:** reading `/proc/pressure/{cpu,memory,io}` plus `os.getloadavg()` takes
  about 0.2 ms. PSI is available on apollo.

**Takeaway:** recording is cheap enough to always be on. The acceptance criterion should
be "wrapper overhead within 0.5 s of `sase proc list` cold start," not a zero-overhead
claim.

---

## 4. Why "the land agent delivers something testable" does not happen by default

### 4.1 The mechanics, verified in today's tree

- **Plan schema.** The Rust validator (`sase-core …/plan/validate.rs`) allows only
  `id, title, depends_on, description, size, model` per phase. Unknown fields are errors.
  **There is no `acceptance:`, `verification:` or `demo:` field.** The only structured
  outcome is the top-level `goal`, which becomes the epic bead's description.
- **Phase-worker prompt** (`bd/work_phase_bead`, `src/sase/default_config.yml:1807`): "Read
  its description and design file, do the work, and close only this bead with
  `sase bead close … --note "<what you verified>"`." It says nothing about demos or tests.
  Workers never create beads; they write `PROPOSED FOLLOW-UP:` notes.
- **Land-agent prompt** (`bd/land_epic`, `default_config.yml:1734`). It is a judgment
  audit: "confirm the work previous agents reported complete really is." Unresolved issues
  "caused by this epic remain epic work: plan and finish them before closing." It names
  **no verification command and no live or demo step**. If remaining work turns up, it
  plans a child epic.
- **Auto-approval.** Every phase segment and the land segment carry `%auto`, so a land
  agent's remediation plan is approved and launched with no human review.
- **Land-agent model.** `@large`, or `@xlarge` at 5 or more phases, unless the plan
  declares a top-level `model`.
- **Flags.** Nothing in `bd/land_epic` checks that an epic's beta flag was removed.
  `tools/check_feature_flags` catches only a *closed* flag bead whose definition still
  exists.

### 4.2 How recent epics went wrong under these mechanics

- **Focused tests that skip the real path (`sase-zt`).** The land audit "passed 92 focused
  tests, but reproduced these gaps using actual source and bindings." The real scanner
  path lost fields that preconstructed fixtures hid. This produced remediation epic
  `sase-zt.6`, which ended with its own `acceptance` phase.
- **Open-ended finish lines (`sase-11e`).** `research:202609/sase_11e_nested_landing_loop.md`
  traced four nested rounds to three themes that kept returning:
  - clauses like "audit every reachable message";
  - acceptance whose full gate never ran green, because of `sase-j0`;
  - an external PyPI wait treated as code work.

  Its prescription is explicit: "Epic plans should end with a numbered, checkable
  definition of done… Land agents judge completion against that list and treat anything
  beyond it as a follow-up."
- **Silent success on external waits.** The overnight stall study
  (`overnight_epic_stall_prevention.md`, 2026-09-18) found phase agents that "hit a
  blocker outside [their] control (a PyPI release, a red host-wide gate), record a
  `PROPOSED FOLLOW-UP`, keep [their] bead open, and exit green."
- **Contracts held only in prose (`sase-zm`).** The architecture critique (C6) recommended
  extracting inter-phase contracts into schema and fixture files "so cross-phase agreement
  is enforced by CI rather than by 14 readings of the same prose."

### 4.3 Rules for the E1 plan that follow from this

- **L1 — A closed Definition of Done.** Number every item. Each is a command plus the
  observable result. No item may be open-ended ("every", "all reachable"). The plan body
  addresses the land agent directly: *judge completion against DoD-1…DoD-N; send anything
  else to `/sase_new_task`.*
- **L2 — Acceptance is code, not prose.** Commit `tools/tool_ledger_acceptance` plus a
  pytest twin. Each phase adds its DoD cases. The acceptance phase and the land agent
  *rerun* it. You can run it against either the workspace build or your deployed `sase`.
- **L3 — Real-path tests only, for anything a DoD item depends on.** That means a
  subprocess `sase` CLI talking to the real Rust binding and the real SQLite file,
  checked through `sase tool show -j`. No hand-built record objects.
- **L4 — Contracts as fixtures from phase 1.** Golden JSON for the ToolRun wire, the
  catalog wire and `show -j`. Later phases test against them and change them only by
  bumping the version.
- **L5 — No calendar waits inside the epic.** Adoption over 7 days, PyPI releases and
  `sase update` are measured or triggered *after* landing, never phase work. Moving
  `sase-core-revision.txt` to the phase's pushed core commit is enough for CI. The
  published floor ratchets itself at release time: `publish.yml` runs
  `tools/ratchet_core_window` in its "Reconcile release metadata" step.
- **L6 — Evidence in close notes.** Every phase close note includes
  `DEMO: <command> → <observed result>` lines for the DoD items it delivered.
- **L7 — A known-red rule is written down before the gate runs.** The acceptance phase
  runs `check-full` through a monitor. The plan names in advance which failures count as
  pre-existing: the `sase-j0` suite-cost budgets. This follows D7 in the roadmap.

---

## 5. Contract decisions the E1 plan must settle

These are the roadmap's "first planning session" questions plus a few found today. For
each I give a recommendation and the main alternative I rejected.

### D1 — Store: a Rust-owned SQLite entity store at `~/.sase/tools/tool_runs.sqlite`

- **Copy the telemetry store** (`sase_core/src/telemetry/store.rs`). Its first commit,
  `646cb0c`, touched only five files: `lib.rs`, `telemetry/{mod,store,wire}.rs` and
  `sase_core_py/src/lib.rs`. Reuse its conventions:
  - a `meta` schema-version row, refusing to open a DB newer than the code;
  - WAL mode entered with BUSY retry, and a bounded busy timeout;
  - `Immediate` write transactions;
  - retention run inside every write transaction;
  - quarantine of a corrupt DB to `.corrupt-<nanos>` plus recreation.
- **Tables:**
  - `runs` — one row per ToolRun, with the summary columns;
  - `stages`;
  - `samples` — a bounded series per run;
  - `meta`.
- **Paths:** Python resolves the path from `sase_home()`. The core never resolves
  `~/.sase` itself; that is the house rule.
- **Rejected: JSONL like procs.** The procs store rewrites the whole file on every write
  and prunes by count (`history_limit: 100`). Neither fits 180 days of indexed history
  read by `list` summaries and `runs` filters.

### D2 — The Rust/Python split, per `rust_core_backend_boundary`

- **Rust (`sase_core::tool_runs`)** owns:
  - the wire types (`ToolDefinitionWire`, `ToolRunWire` and sub-wires, schema v1);
  - catalog normalization (`tools:` mapping → typed definitions plus diagnostics);
  - state transitions (`begin`, `record_stages`, `record_samples`, `finish`, and
    `reconcile` given liveness facts), all idempotent;
  - queries (`runs` with filters, get by id or unique prefix, per-tool summary with last
    outcome and typical duration from the median/p90 of recent successful runs);
  - retention;
  - fingerprint hashing, domain-tagged canonical JSON like `continuation::worktree_fingerprint`.
- **Python** owns:
  - the CLI;
  - the executor and signal handling;
  - git observation (reuse `finalizers/prepare.py::observe_completion_repositories` and
    `dirty_path_fingerprints`);
  - PSI/loadavg sampling;
  - reading `run_silent` events;
  - the disk row and reap step;
  - rendering.
- **Why:** a future web or TUI surface would need identical catalog parsing, identical
  outcomes and the same "typical duration."

### D3 — Executor and output: pipes plus a log, bytes preserved

- **Existing runners do not fit.** None preserves separate streams: `sase proc run -w`
  waits on a *detached* supervisor that merges stderr into stdout. `run_silent` and the
  monitor supervisor also merge.
- **Default mode.** Spawn the child with separate stdout/stderr pipes, pumped by threads
  (reuse `supervision.pump_output`). Write each chunk unchanged to the wrapper's own
  stdout/stderr and to one ToolRun-owned log with stream tags.
- **Lifecycle text.** Wrapper messages go to **stderr only**, as one header line and one
  footer line: run id, outcome, duration, `sase tool show <id> -l`.
- **`-q/--quiet`.** Child output goes only to the log. The wrapper prints the header, one
  line per stage, and the footer. On failure it also prints the last `-T/--tail-lines N`
  lines (default about 200). This replaces the 32 hand-wrapped `> log; tail` calls.
- **Known limitation, documented rather than solved in E1:** the child sees pipes, not a
  TTY, so colors drop on a human terminal. A pty mode is a later enhancement. Agents never
  have a TTY anyway.
- **Rejected alternatives:**
  - reuse `proc run`: detached, merged streams, and the proc store's retention;
  - pty by default: merges streams and adds complexity;
  - pure passthrough everywhere: `show -l` and `-q` would be impossible.

### D4 — Outcomes, exit codes and reconciliation

- **States E1 produces:**

  | State | Meaning |
  | --- | --- |
  | `running` | Run in progress |
  | `succeeded` | Child exited 0 |
  | `failed` | Child exited non-zero |
  | `signaled` | Child killed by a signal |
  | `interrupted` | Wrapper received SIGINT/SIGTERM and forwarded it |
  | `lost` | Wrapper died without settling; set by reconciliation |

  The enum is versioned. Later epics add `timed_out`, `reused`, `queued` and `refused`.
- **Exit status:**
  - the child's code, or 128+n for a signal;
  - 130 for Ctrl-C;
  - 2 for wrapper usage or catalog errors, printed with a diagnostic.
  - E1 does not claim the reserved code 75 from the control-plane report; that belongs to
    refusal and queueing, which are E7.
- **Liveness facts.** Each `running` row stores the host `boot_id`, the wrapper pid and
  its start time from `/proc/<pid>/stat`.
- **Reconciliation.**
  - When: before any `runs`/`list`/`show` read and at each `run` start.
  - Rule: a `running` row whose wrapper is gone becomes `lost`, with reason "runner exited
    without settling."
  - Why it matters: this is how SIGKILLs from provider timeouts become visible.
- **Recording fails open.** If the store cannot be opened or written, the command still
  runs. The wrapper prints one warning line (`run not recorded: <reason>`) and exits with
  the child's code. If the start insert failed, the wrapper retries once at finish with a
  single late insert.

### D5 — Enclosing owners and one log owner (a cheap head start on E2)

- **Record the enclosing owner.** Monitors export `SASE_MONITOR_ID`
  (`monitor/supervise.py:216`) and procs export `SASE_PROC_ID`
  (`procs/supervisor.py:384`). E1 records `owner: monitor:<id> | proc:<id> | foreground`
  from these.
- **One log owner.** When an enclosing owner exists, the wrapper **does not create its own
  log**. It passes output straight through and records `log_owner` as the monitor or proc.
- **Result:** `sase monitor start -p verify -- sase tool run check-full` records
  `check-full` in the ledger today, with no duplicate log. That covers the 27 h of
  check-full monitor time the corpus would otherwise miss. E2 still owns *creating*
  hand-offs (`-H`).
- **Also:** export `SASE_TOOL_RUN_ID` to the child, so nested `sase tool run` calls record
  a `parent_run_id`. This is cheap now, and E7's nested grants will need it.
- **Leave `-f` alone.** Do **not** change prepared host completion in E1.
  `continuation/completion.rs:510` accepts only an exact `just check` or `just check-full`
  command. Guidance must keep `-f` flows on the raw commands (host completion is used by
  0/90 monitors). Extending that contract belongs to E2.

### D6 — Catalog: project-owned, whole entries, validated in Rust

- **Where it comes from.** Read `tools:` only from the **project layer** (`sase/sase.yml`)
  in E1.
- **Why not the merged config.** `merge_config_sources` deep-merges maps. A user or
  overlay layer could then combine one layer's `argv` with another layer's `stages`
  without anyone noticing. The loader therefore reads per-layer through
  `load_config_layers()` and takes whole entries. User-level personal tools can be added
  later.
- **E1 entry fields:**
  - `argv` (a list, no implicit shell);
  - `description`;
  - `stages: run_silent | none`;
  - `inputs` (paths, recorded in the fingerprint);
  - `env` (an allow-list of variable names whose values are recorded);
  - `args: allow | deny` (whether `run TOOL -- extra…` may append arguments; `test`
    needs `allow`).
- **Validation.** Per-entry `additionalProperties: false`. Unknown fields are rejected
  with a diagnostic; later epics add `receipt`, `handoff`, `cheap_stages`, `timeout` and
  `weight` by version bump.
- **Schema.** Add the `tools` key to `src/sase/config/sase.schema.json`, whose top level
  is `additionalProperties: false`. Note that config is **not** schema-validated at
  runtime (`config/file_hooks.py:41`), so the Rust normalizer is the real validator.
  Add a test that validates the repo's own `sase/sase.yml` catalog.
- **Initial sase catalog** (from §3.1): `check`, `check-full`, `install`,
  `test` (args allowed), `test-visual`.
- **Identity.** Record extra arguments in the run. "Typical duration" groups only runs
  with no extra arguments.

### D7 — Stage timeline

- **`run_silent` events.** When `SASE_TOOL_RUN_EVENTS` is set, `tools/run_silent` appends
  one JSONL event per stage. Fields: stage name, start and end epoch, elapsed, exit code,
  status and output byte count. Lines are small `O_APPEND` writes.
- **Monitor stage JSON.** Also add `started_at_epoch` and `elapsed_seconds` to the
  existing monitor `stages/<id>.json`, so monitors benefit too.
- **Ingestion.** The wrapper ingests the events at finish, and on reconciliation for
  `lost` runs.
- **Unattributed time.** Steps outside `run_silent` (`probe_core_floor`,
  `print_scoped_summary`) show up as `unattributed = total − Σ stages`.
- **Do not touch the Justfile.** `tests/test_justfile_lint.py` asserts its lines word for
  word.

### D8 — Run evidence (recorded, not yet used)

- **Fingerprints before and after the run.** The roadmap specifies only a pre-run
  fingerprint. The post-run one costs about 40 ms. It detects a tree that changed during
  the run (for example `just fix`), which E4 needs to refuse receipts safely.
- **Fingerprint components:** tree (`HEAD`, `HEAD^{tree}`, index tree), dirty-diff digest
  and file count, inputs digest, toolchain (Python version, sase version,
  `sase_core_rs.__version__`, resolved `argv[0]`), and allow-listed env values. Agents
  set `SASE_PYTEST_WORKERS` and `SASE_TEST_GATE_DISABLED` inline, so those belong on the
  allow-list.
- **Load samples** at start, every 10 s and at end:
  - PSI `cpu`/`memory`/`io` `some avg10`/`avg60`;
  - loadavg;
  - `nproc`;
  - the count of concurrently running ToolRuns.

  Store a bounded series (downsampled past about 720 points) plus per-run summary
  columns.
- **macOS.** There is no PSI, so record loadavg and `psi: null`. A unit test covers this
  path; live Mac verification is out of scope.
- **Telemetry.** Add a `sase_tool_run_duration_seconds` histogram and a
  `sase_tool_runs_total` counter, labeled by tool and outcome only.
  - Update `METRIC_DEFS` and the catalog prefix.
  - `tests/telemetry/test_metrics.py` pins the count at 37.
  - The `tool` handler must call `init_telemetry` and `register_flush_on_exit`, because
    the CLI entry point does not.

### D9 — Retention and disk ownership, landing with the first writer

- **Rust retention** runs from phase 1, in every write transaction:
  - run summaries: 180 days;
  - samples and stages: 60 days;
  - logs: 14 days with a total byte cap.

  It returns the log ids to delete.
- **Machine config.** Horizons live under a new top-level key, `tool_runs:`, in user
  config, *not* under the project's `tools:` catalog. Machine policy and project identity
  stay separate.
- **Phase 3 wiring** (the first phase that writes logs):
  - a `DiskFootprintRow` in `sase_state_rows`;
  - a `DiskReapStep` modeled on `disk_footprint_reap_proc.py`;
  - re-sync hooks for tests that monkeypatch `disk_footprint`.

  Coordinate with `sase-zw.8` through a bead note if it is still open.

### D10 — No beta flag; the command stays unadvertised until the adoption phase

- **The flag rule.** `sase_flags.md` allows an epic beta flag "only when a landed phase
  would otherwise expose part of an unfinished feature."
- **Why E1 does not need one.** E1 changes no existing behavior. From phase 2 on, every
  landed state is coherent: phase 2 lists the catalog; phase 3 adds the ability to run
  and inspect it.
- **The one unfinished-looking exposure is advertising.** Leave `tool` out of
  `_COMPACT_ROOT_COMMANDS` (`main/parser_root_help.py`) and out of the guidance until
  phase 6.
- **What this avoids:**
  - a flag bead;
  - tests for both flag states;
  - a removal step the land agent never checks — a forgotten flag would leave the
    feature off by default, which is the worst result for "deliverables I can test."
- **If you prefer strict policy,** use a `tool_ledger` beta flag. Put its removal in the
  acceptance phase's DoD and list the flag bead id in the plan.

### D11 — Defer the backfill importer

- **Low value.** Imported rows carry no fingerprints, stages or load samples. They only
  prefill "typical duration."
- **Short to replace.** At 157 `just check` runs a week on apollo, E1's own corpus fills
  `list` within a day of the guidance change.
- **High cost.** It adds a second `source` meaning to every query and test.
- **Where it could go.** If E6 later wants priors, the importer belongs in E6's first
  phase. By then there will be 3 weeks of real rows to compare against.

### D12 — Adoption: measure in E1, judge after landing, and watch the deploy lag

- **The report.** `tools/tool_adoption_report [-d DAYS] [-j]` reuses the pairing logic
  from the appendix, including unwrapping the shell prefix. It prints, per catalog tool,
  the heavy Bash wall time that went through `sase tool run` versus raw invocations.
  Keep it a repo tool, not a new verb; E6's `stats` can absorb it later.
- **Deploy lag.** Agents run the **deployed** `sase`. On apollo that is an editable uv
  tool install: Python from the primary `sase` checkout, and `sase_core_rs` built from
  the primary `sase-core` checkout (the `.so` was last rebuilt at 00:28 today).
  - Python can therefore be ahead of the compiled extension.
  - A new `require_rust_binding("tool_run_…")` then raises "stale wheel."
- **Guidance must degrade safely.** If `sase tool` reports it is unavailable, fall back
  to the raw command. The adoption phase prints a one-line binding check that the
  acceptance phase runs against the deployed binary. If it fails, the evidence records
  "run `sase update`" as an owner action; it is not code work.
- **The target is judged a week after landing, not at landing.** I suggest at least 70%
  of heavy `just check` wall time wrapped within 7 days. The land agent records the
  baseline (about 0%) in its close note. You rerun the report a week later, and E2's plan
  starts from that number.

### D13 — The plan lists what E1 does not do

The plan should name each of these so the land agent treats them as successor epics,
not remediation:

- hand-off (`-H`), `stop`, `show --follow`, and the prepared-completion contract (E2);
- NEW/KNOWN/FLAKY (E3);
- receipts, reuse and cheap-stages-first (E4);
- TUI chips, cards and panes (E5);
- predictions, `stats`, `-E` and automatic routing (E6);
- admission, `-w`, `-B` and `-W` (E7);
- fleet surfaces (E8);
- the importer;
- a pty mode;
- user-level catalogs;
- Mac live verification.

---

## 6. The recommended phases in detail

All phases are `medium`, and each depends on the previous one. Parallel phases would
collide in the executor and in the `show` renderer, so none are proposed. Every phase:

- adds its DoD cases to `tools/tool_ledger_acceptance` and its pytest twin;
- runs `just check`;
- writes `DEMO:` lines in its close note.

**1. `core-ledger`**, in sase-core, opened with `sase repo open sase-core`

- New `crates/sase_core/src/tool_runs/{mod,wire,store,catalog,fingerprint}.rs`,
  declared in `lib.rs` in alphabetical order.
- Wires carry `schema_version` from v1. States are as in D4. SQLite follows D1.
  Transitions, queries and retention follow D2 and D9.
- Golden fixtures in `crates/sase_core/tests/fixtures/tool_runs/`, plus a
  `tool_runs_contract.rs` integration test.
- Bindings in `sase_core_py/src/lib.rs`, including `tool_runs_wire_schema_version`, using
  the `py.allow_threads` and error-mapping patterns, with binding round-trip tests.
  Run the whole-workspace `just check`, because `cargo test -p sase_core` skips the
  binding tests.
- On the sase side:
  - a thin adapter, `src/sase/tool/_core.py`, with literal `require_rust_binding` calls;
  - `tools/validate_sase_core_rs` probes;
  - move `sase-core-revision.txt` to the pushed core commit, without regressing later
    contracts other epics have pinned.
- **DEMO:** a real-binding round trip (begin, then finish, then get) in a temp SASE_HOME,
  plus a corrupt-DB quarantine test.

**2. `catalog`**

- Schema key, per-layer whole-entry loader, Rust normalization, diagnostics.
- The repo's catalog in `sase/sase.yml`.
- Parser group `sase tool` with `list` as the bare default: `parser_tool.py`,
  `parser_registry.py`, `parser_full_registrars.py`, `entry.py`, `tool_handler.py`.
- Refresh the completion spec, update `docs/cli.md`, and update the parser guard tests
  `test_parser_narrowing.py` and `test_parser_command_defaults.py`.
- `list` shows name, argv, stage mode and provenance. The LAST and TYPICAL columns
  render `—` until phase 3.
- **DEMO:** `sase tool` prints the delegation notice and the five tools. An invalid entry
  prints a diagnostic naming the field.

**3. `foreground-run`**

- The D3 executor and the D4 states and reconciliation.
- `run TOOL [-- ARGS]`, `run -- ARGV…` (ad-hoc runs are recorded with `tool: null`),
  `-q`, `-T`.
- Attribution from `SASE_AGENT_NAME`, `SASE_AGENT_WORKSPACE_NUM`, `SASE_BEAD_ID`, the
  project and cwd.
- D5 owners.
- `runs` (`-t` tool, `-s` state, `-A` agent, `-a` all projects, `-n` limit, `-j`),
  `show RUN` (`-j`, `-l` log), and live LAST/TYPICAL in `list`. Every option gets a short
  alias, and help stays sorted.
- D9 disk row and reap step.
- **DEMO:** pass, fail, signal, Ctrl-C, `kill -9` leading to `lost`, and a read-only
  store that still runs the command.

**4. `stage-timeline`**

- D7 `run_silent` events and monitor stage timings.
- A stage table in `show`. In `-q` mode, one stderr line per stage as it finishes.
- **DEMO:** a fixture tool with three `run_silent` stages (fast pass, 2 s sleep, fail).
  Then a real `sase tool run check` whose `show` lists at least 12 stages plus
  unattributed time.

**5. `run-evidence`**

- D8 fingerprints (before and after), toolchain and env allow-list, the load sampler
  thread, `parent_run_id`, and telemetry.
- Fingerprint and load sections in `show`.
- **DEMO:** dirtying a file changes the dirty digest and count. Roughly `duration / 10`
  samples are recorded. A nested `sase tool run` shows its parent.

**6. `agent-adoption`**

- `docs/tool.md` with a "Try it" section that mirrors the DoD.
- Glossary strands for **Tool Run** and **Tool Catalog**, via `/sase_memory_write`.
- The `sase/memory/lint_and_test.md` update: inline verification uses
  `sase tool run check`; `-q` replaces hand-made log/tail wrappers; `check-full` runs as
  `sase monitor start -p verify … -- sase tool run check-full`; `-f` prepared-completion
  flows keep the raw `just` commands; fall back to the raw command if `sase tool` is
  unavailable.
- The `src/sase/xprompts/skills/sase_monitor.md` template update, then regenerate the
  skills.
- Add `tool` to the compact root help.
- `tools/tool_adoption_report`, with today's baseline recorded as an artifact.
- **DEMO:** the report runs on apollo, and the memory read shows the new guidance.

**7. `acceptance`**

- Run the harness against `.venv/bin/sase` and against the deployed `sase`
  (`--sase PATH`). Run `sase tool run check` for real.
- Run `sase monitor start -p verify -- sase tool run check-full` through `/sase_monitor`
  with `TESTING`/`TESTED`, and cite that run's ToolRun id as evidence.
- Apply the L7 known-red rule and measure wrapper overhead.
- Snapshot the transcript as an artifact with `sase artifact create`.
- **Request an explicit `model:`** at land-agent strength when you prompt the planner.
  The nested-landing study found stronger auditors keep finding what `@medium`
  implementers missed. The plan schema allows a phase `model` only when the user's prompt
  asks for it.

---

## 7. Definition of Done and the acceptance harness

Put this list, verbatim in spirit, in the plan body under "Definition of Done (land agent:
judge against these items only)". Everything runs on apollo.

1. **DoD-1** `sase tool` prints the delegation notice, then lists `check`, `check-full`,
   `install`, `test` and `test-visual` with LAST and TYPICAL columns. An invalid catalog
   entry produces a diagnostic naming the entry and field, with exit 2.
2. **DoD-2** `sase tool run -- sh -c 'printf out; printf err >&2; exit 3'` behaves as
   follows:
   - stdout is exactly `out`;
   - stderr contains `err` plus the wrapper header and footer;
   - the exit status is 3;
   - `sase tool show <id> -j` reports `failed`, exit 3, a duration and a log locator.
3. **DoD-3** A child killed by SIGTERM exits 143 and is recorded `signaled`. Ctrl-C
   during `sase tool run -- sleep 30` exits 130 and is recorded `interrupted`.
4. **DoD-4** `kill -9` of the wrapper during `sase tool run -- sleep 30` leaves no
   `running` row. The next `sase tool runs` shows `lost`, with reason "runner exited
   without settling."
5. **DoD-5** With the store unwritable, `sase tool run -- echo hi` prints `hi`, exits 0
   and prints exactly one `run not recorded` warning.
6. **DoD-6** In the sase repo, `sase tool run check` shows its usual `✓` stage lines.
   `sase tool show <id>` then lists every `run_silent` stage with its duration,
   unattributed time and total, before/after tree fingerprints with dirty count, the
   toolchain, and load samples (about one per 10 s, with PSI fields on Linux). After
   three runs, `sase tool list` shows `check` with LAST and TYPICAL filled in.
7. **DoD-7** `sase tool run -q test -- <failing test path>` prints only the header, the
   stage/footer lines, the last `-T` lines of output and the `sase tool show <id> -l`
   pointer. `show -l` prints the full log.
8. **DoD-8** `sase monitor start -p verify -- sase tool run check-full` produces a ToolRun
   with `owner monitor:<id>` and `log_owner monitor`, and no ToolRun log file. A nested
   `sase tool run` inside a tool run records `parent_run_id`.
9. **DoD-9** `sase disk list` shows the tool-runs row with its owner and horizon.
   `sase disk reap` in dry-run mode reports the prunable logs and runs. Retention
   horizons come from `tool_runs:` config.
10. **DoD-10** `sase tool runs -j` and `show -j` carry `schema_version`. The phase-1
    golden fixtures still pass.
11. **DoD-11** `tools/tool_ledger_acceptance` exits 0 and prints PASS for DoD-1…10. It
    runs against an isolated SASE_HOME and a temp git project, with both
    `--sase .venv/bin/sase` and the deployed `sase` after `sase update`. Its pytest twin
    runs in CI.
12. **DoD-12** `tools/tool_adoption_report -d 7` runs. Its baseline output is recorded
    in the land agent's close note. `sase memory read lint_and_test.md` shows the new
    guidance, including the fallback sentence and the unchanged `-f` rule.
13. **DoD-13** The gates:
    - `just check` is green;
    - `sase tool run check-full` has run through a verify monitor, and its failures are
      confined to the `sase-j0` suite-cost budgets named in the plan (compared by
      stage/budget name);
    - any other failure is either epic work or goes to `/sase_new_task` if unrelated, as
      the land agent's own rules already say;
    - wrapper overhead is within 0.5 s of `sase proc list` cold start.

**Harness design.** `tools/tool_ledger_acceptance` is a Python script with these options:

- `--sase PATH` (the default is `sase` on PATH);
- `--live`, which adds the slow DoD-6 and DoD-8 cases in the current repo;
- `--keep`, which keeps the temp directories;
- `-j`, for a JSON summary.

It builds a temp git project whose `sase/sase.yml` defines four tools:

| Tool | Behavior |
| --- | --- |
| `ok` | passes |
| `fail` | exits non-zero |
| `staged` | three `run_silent` stages |
| `slow` | `sleep` |

It sets `SASE_HOME` to a temp directory, drives the real CLI through subprocesses and
signals, and asserts only on `show -j` and `runs -j`. The output is a PASS/FAIL table
keyed by DoD number. Because the harness is black-box and takes `--sase`, it is the one
artifact that tests the same thing in the phase worker's workspace, in the land agent's
audit and on your deployed install.

**Post-landing, not land-agent work:** rerun the adoption report after 7 days. If
wrapped heavy `just check` wall time is below about 70%, tighten the guidance before
planning E2.

---

## 8. Risks and conflicts specific to E1

| Risk | Why it is real | Mitigation in the plan |
| --- | --- | --- |
| Stale compiled extension on the deployed install | apollo's `sase` is editable. Python can land before the `.so` is rebuilt, and then `require_rust_binding` raises. | D12 fallback sentence, a binding check in acceptance, "run `sase update`" treated as an owner action |
| Core pin drift | Several epics move `sase-core-revision.txt`. `sase-zt.6` had to "advance the core pin without losing later contracts." | Phase 1 moves the pin forward only, to a core commit containing all later pinned contracts, and records the SHA |
| `check-full` known-red (`sase-j0`) | 0/37 check-full monitors completed on apollo | L7 plus DoD-13: a written, name-based known-red rule |
| Field loss hidden by fixtures | The `sase-zt` precedent | L3: real-path subprocess tests only |
| Open-ended finish lines | The `sase-11e` precedent | L1: closed DoD, no "every"/"all" items |
| Waits on PyPI or calendar | The overnight stall study | L5: the floor ratchets itself at release; adoption is judged after landing |
| Editing `sase disk` alongside `sase-zw.8` | Both touch `disk_footprint_inventory.py` and `disk_footprint_reap.py` | Additive row and step; a coordination note on `sase-zw.8` |
| Merged-config leakage of `tools:` | `deep_merge` mixes fields across layers | D6: read the project layer as whole entries |
| Justfile word-for-word tests | `tests/test_justfile_lint.py` | D7: change only `tools/run_silent`, never the Justfile |
| Telemetry metric count pinned | `test_metrics.py` asserts 37 | Update the pin in phase 5 |
| Prepared-completion regression | `completion.rs` accepts only exact `just check` / `check-full` | D5: keep `-f` flows on raw commands until E2 |
| Colors lost for humans | Pipes are not a TTY | Documented limitation; pty is a follow-up |
| The planner needs your consent for memory edits | `/sase_memory_write` requires it when the user "did not ask for it" | Name the memory changes in your planning prompt (§10) |

---

## 9. Where I diverge from the roadmap

1. **No rename phase.** It already landed (`868abb2467`).
2. **No beta flag** (D10). This goes against the roadmap's "every epic owns exactly one
   beta flag." Keeping `tool` unadvertised until phase 6 is enough, and it removes a
   removal step the land agent never checks.
3. **Importer deferred** (D11). E1's own corpus replaces it within about a day.
4. **Seven phases instead of 8–9.** The rename and importer are gone. Retention folds
   into the phases that write data, per the roadmap's own "retention with the first
   writer" invariant.
5. **"Compact agent output" becomes a specific `-q/-T`.** The evidence is 32 hand-wrapped
   `> log; tail` calls. The default stays byte-exact passthrough.
6. **Runs inside monitors and procs are recorded in E1** (D5), via `SASE_MONITOR_ID` and
   `SASE_PROC_ID`. The expensive `check-full` population enters the corpus weeks before
   E2, and the one-log-owner invariant holds.
7. **Fingerprints before and after the run, not just before** (D8). It costs about 40 ms
   and makes E4's receipts safe against trees that change mid-run.
8. **Landing criteria and the success metric are separated.** The roadmap's E1 exit
   measurement ("≥80% of heavy agent Bash wall time wrapped") cannot be observed at
   landing. It would push the land agent into planning another child epic. It becomes a
   post-landing check against a recorded baseline. The realistic ceiling is about 82%
   (§3.1), so the target should start around 70% for `check`.

---

## 10. Recommended solution

**Plan E1 now as a 7-phase serial epic, with a closed Definition of Done and a committed
black-box acceptance harness. Settle D1–D13 in the plan text before any phase runs.**

1. Contracts: SQLite ToolRun store owned by Rust; catalog read from the project layer as
   whole entries; executor with separate pipes and a log; `lost` reconciliation;
   recording that fails open.
2. Recording: enclosing-owner recording so there is one log owner; pre/post fingerprints
   plus PSI/loadavg sampling.
3. Scope: no flag; importer deferred; adoption measured in E1 but judged after landing.

You get testable deliverables in three layers:

- **Per phase:** you can try each phase's results as soon as it lands (§1 table,
  `DEMO:` close-note lines).
- **At landing:** `tools/tool_ledger_acceptance --sase "$(which sase)"` against your
  deployed install, plus `docs/tool.md` "Try it."
- **After landing:** `tools/tool_adoption_report -d 7`.

**Draft prompt for the planning agent** (hand it to `/sase_plan`):

```text
Plan epic E1 of research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md —
"Named tools and the ToolRun ledger" — using
research:202609/sase_tool_e1_ledger_plan__b.md as the design input (read both with
`sase artifact read`). Honor decisions:record-before-admit.

Structure: exactly these serial phases, all size medium: core-ledger, catalog,
foreground-run, stage-timeline, run-evidence, agent-adoption, acceptance. Give the
acceptance phase `model: <land-agent model>` (I am explicitly requesting that model).
No beta feature flag; keep `tool` out of the compact root help until agent-adoption.
Defer the tool_calls.jsonl backfill importer.

Settle in the plan body, as binding contracts: D1–D13 from the design input (store,
Rust/Python split, executor/output, states/exit codes/reconciliation, enclosing owners
and one log owner, project-layer whole-entry catalog, run_silent stage events,
pre/post fingerprints and load sampling, retention/disk ownership, no flag, importer
deferral, adoption measurement with deploy-lag fallback, explicit out-of-scope list).
Phase 1 must produce golden contract fixtures that later phases test against.

The plan body MUST contain:
1. "Definition of Done (land agent: judge against these items only)" — DoD-1..DoD-13
   from the design input, each a command plus observable result, nothing open-ended.
2. A rule that every phase adds its DoD cases to tools/tool_ledger_acceptance (black-box,
   --sase PATH, isolated SASE_HOME, real CLI + real Rust store, asserts only on -j output)
   and its pytest twin, uses real-path tests only, and writes `DEMO: <command> →
   <observed>` lines in its close note.
3. The known-red rule for check-full: failures confined to the sase-j0 suite-cost
   budgets (named) are pre-existing; anything else is epic work or /sase_new_task.
4. "Out of scope — successor epics, not remediation": E2–E8 items, importer, pty mode,
   user-level catalogs, Mac live verification, and the prepared-completion (-f) contract.
5. "No calendar or release waits": core pin moves in-phase; the published floor
   ratchets at release; the 7-day adoption target is measured after landing.

Memory changes I authorize for this plan (name them in the relevant phase steps):
update sase/memory/lint_and_test.md to teach `sase tool run check`, `-q`, wrapping
check-full inside verify monitors, the unchanged -f rule, and the fallback when
`sase tool` is unavailable; add glossary strands "Tool Run" and "Tool Catalog"; update
the sase_monitor skill source template; regenerate with `sase memory init`.
```

---

## Appendix — method and evidence

- **State checks.**
  - `sase bead show sase-zm` gives CLOSED, `superseded`, 2026-09-17T19:30:44Z.
  - `git show --stat 868abb2467` shows the `ace/tui/tools` → `llm_calls` move plus the
    glossary strand. `85d6fc74bb` adds `decisions/record-before-admit.md`.
  - `sase bead show` on `sase-11y`, `-zw`, `-124`, `-x7`, `-11e`, `-11l`, `-zp`, `-10h`
    and `-j0` gives the statuses in §2.
  - `sase bead search "ToolRun"` returns nothing. A grep of the core for tool/ToolRun
    returns nothing.
- **Bash baseline (§3.1).**
  - Source: every `~/.sase/projects/*/artifacts/ace-run/*/*/*/tool_calls.jsonl` with mtime
    within 7 days (188 files, 47.7 MB).
  - Pairing: `ToolUse` (`tool_name == "Bash"`) is paired with `ToolResult` on
    `tool_use_id`. Duration comes from `duration_ms` when present, otherwise the
    difference in `recorded_at`. Negatives and runs over 6 h are dropped.
  - Command normalization strips `/usr/bin/(zsh|bash|sh) -lc '…'`, leading `cd …&&`,
    `env -u X`, `VAR=…` prefixes and `timeout N`, then classifies by leading command.
  - "Hand-wrapped" means the command matches `just check` and also a log redirect or
    `tail -n N`.
  - The script is at `/tmp/tc_baseline.py`, reproducible on apollo. The same logic is the
    specification for `tools/tool_adoption_report`.
- **Monitors (§3.2).** `sase monitor list --all --json --limit 500` returned 90 rows,
  `20260903065322`–`20260918200758`, grouped by command substring.
- **Stage estimate (§3.3).** 47 monitor `stages/` directories under `ace-run`. Stage JSON
  files were sorted by `recorded_at_epoch`, and consecutive differences were taken; 42
  directories had at least 8 stages. These are estimates only: `run_silent` records end
  times but no start times.
- **Overhead (§3.4).** Three cold runs each of `sase --help`, `sase proc list` and
  `sase disk list` via `subprocess.run`. `/usr/bin/time` on the git fingerprint commands.
  A Python timing of PSI plus loadavg reads.
- **Mechanics (§4).**
  - `src/sase/default_config.yml:1734-1825` (`bd/land_epic`, `bd/work_phase_bead`).
  - sase-core `crates/sase_core/src/plan/validate.rs` (allowed phase fields; unknown
    fields are errors).
  - `src/sase/bead/work.py` (`%auto` on phase and land segments).
  - `sase/repos/plans/202609/queue_capacity_landing_repairs.md` (the `sase-zt.6`
    acceptance phase and "92 focused tests" audit).
  - Research notes `sase_11e_nested_landing_loop.md`,
    `overnight_epic_stall_prevention.md`, `command_capacity_epic_architecture_critique.md`
    (C6) and `command_capacity_epic_critique.md` (S2).
- **Code seams (§5–§6).**
  - Parser registry and default-list wiring: `src/sase/main/parser_registry.py`,
    `parser_root_defaults.py:58`, `entry.py`.
  - Config layers: `src/sase/config/loading.py:197`, `layers.py`, `core.py:540`.
  - Schema: `sase.schema.json`, top-level `additionalProperties: false`.
  - `tools/run_silent`: end-only `recorded_at_epoch`, merged streams.
  - Proc runner: `procs/supervisor.py:281` (stderr→STDOUT, detached).
  - Monitor env: `monitor/supervise.py:212-216`.
  - Supervision library: `src/sase/supervision/`.
  - Disk inventory: `core/disk_footprint_inventory.py:271`, `disk_footprint_reap_proc.py`.
  - Telemetry: `telemetry/metrics.py` `METRIC_DEFS`; the count of 37 is pinned in
    `tests/telemetry/test_metrics.py:61`.
  - Fingerprint sources: `finalizers/prepare.py::observe_completion_repositories`,
    `commit_finalizer_git_status.py::dirty_path_fingerprints`.
  - Core: `telemetry/store.rs` (the SQLite pattern), `continuation/completion.rs:510`
    (exact-command completion), `sase_core_py/src/lib.rs` (the binding pattern).
  - Release: `.github/workflows/publish.yml:100-111` (floor ratchet at release),
    `core-pin-ratchet.yml`.
- **Deploy stack.** `~/.local/share/uv/tools/sase/uv-receipt.toml` shows an editable
  `sase` from the primary checkout. `sase_core_rs` loads from the primary `sase-core`
  checkout (`.so` modified 2026-09-19 00:28). The deployed version is `sase 0.17.1`,
  `sase-core-rs 0.34.58`.
