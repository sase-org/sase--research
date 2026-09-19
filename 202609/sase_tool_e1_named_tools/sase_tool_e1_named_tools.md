# Planning E1: named tools, the ToolRun ledger, and a lander you can actually test

**Consolidated report** · 2026-09-19 · host apollo · sase `59c82a36e8` · core pin
`8d5341a4d5` (opened core HEAD `4a8c6d40de`, published floor
`sase-core-rs>=0.34.48,<0.35.0`, deployed `sase 0.17.1` / `sase-core-rs 0.34.58`)

**Sources.** Researcher A (`sase_tool_e1_named_tools__a.md`, nine-phase contract and
executable-acceptance study), researcher B (`sase_tool_e1_named_tools__b.md`, seven-phase
ledger plan with a closed Definition of Done and a 7-day apollo measurement), the
roadmap (`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`), the
control-plane report (`research:202609/sase_tool_control_plane/sase_tool_control_plane.md`),
`decisions:record-before-admit`, the land-epic xprompt, today's sase and sase-core trees,
live beads, and independent remeasurement on apollo.

**Question.** How should the first epic of the `sase tool` roadmap — "E1 — Named tools
and the ToolRun ledger" — be implemented, and how do we make the land agent hand back
concrete deliverables Bryan can rerun himself?

---

## 1. Answer up front

**Write the E1 plan now as seven serial `medium` phases, with no beta flag and no
legacy importer.** The three roadmap pre-planning moves are already done (`sase-zm`
superseded, `decisions:record-before-admit` accepted, LLM Calls rename landed). Nothing
in flight blocks a foreground ledger. The lander will not invent a testable exit unless
the plan names one: put a closed Definition of Done in the plan body and a checked-in
black-box harness that every phase extends.

The product is one command path:

```text
sase tool list | run | runs | show
```

A named or ad-hoc command gets a durable ToolRun identity **before** it starts, runs
with exact argv and no implicit shell, preserves the child's streams and exit, and
records stages, start/end fingerprints, and load samples into a machine-local
Rust-owned SQLite store. Successors (hand-off, receipts, triage, admission, TUI) are
out of scope; the raw facts they need are recorded now because they cannot be
backfilled.

Two artifacts carry every user-testable result:

1. **`tools/smoke_sase_tool_runs`** — hermetic, `--sase PATH`, isolated `SASE_HOME`,
   real CLI talking to the real Rust store, asserts on `-j` envelopes. A pytest twin
   runs in CI. Every phase adds its DoD cases.
2. **A numbered Definition of Done in the plan body.** Each item is a command plus the
   observable result. The lander judges completion against that list and nothing else.

| # | Phase | What lands | What you can try |
| --- | --- | --- | --- |
| 1 | `core-ledger` | Rust wires, SQLite store, state machine, retention primitives, golden fixtures, PyO3 bindings, core pin moved | Binding round-trip in a temp `SASE_HOME`; corrupt-DB quarantine |
| 2 | `catalog` | Project-layer `tools:` in `sase/sase.yml`, schema, `sase tool` / `list` | `sase tool` lists `check`, `check-full`, `install`, `test`, `test-visual` |
| 3 | `foreground-run` | Exact-argv executor, `run`/`runs`/`show`, `-q`/`-T`, dead-runner `lost`, fail-open recording, disk owner | Pass, fail, SIGTERM, Ctrl-C, `kill -9` → `lost`, read-only store still runs |
| 4 | `stage-timeline` | `run_silent` start/finish events; `show` lists stages + unattributed time | `sase tool run check` then `show` lists every `run_silent` stage with duration |
| 5 | `run-evidence` | Pre/post fingerprints, PSI/loadavg samples, nested `parent_run_id`, telemetry | Dirtying a file changes the fingerprint; ~1 sample / 10 s |
| 6 | `agent-adoption` | `docs/tool.md` "Try it", glossary, `lint_and_test` + `/sase_monitor` guidance, compact-help, adoption report | `tools/tool_adoption_report -d 7` prints the baseline (about 0% wrapped) |
| 7 | `acceptance` | Harness against workspace and deployed `sase`; live `run check`; wrapped `check-full` monitor **start**; evaluation artifact | `tools/smoke_sase_tool_runs --sase "$(which sase)"` prints PASS for DoD-1…DoD-10 |

---

## 2. What changed since the roadmap (2026-09-17 → today)

| Roadmap assumption | Today (verified) |
| --- | --- |
| Retire `sase-zm` first | **Done.** CLOSED, resolution `superseded`, 2026-09-17T19:30:44Z |
| Write `record-before-admit` | **Done.** `85d6fc74bb`; memory strand `decisions:record-before-admit` |
| LLM Calls rename as E1's first phase or a preceding task | **Done.** `868abb2467` moved `ace/tui/tools/` → `llm_calls/`; glossary strand `llm-calls` exists |
| `sase-11y` 2/10 closed | **5/10 closed** (`.1`–`.4`, `.6`). `.8` (oneshot service procs) is still in progress — E2/E5, not E1 |
| `sase-zw` in progress | Phases `.1`–`.7` closed; child epic `sase-zw.8` still in progress. E1's disk row is an additive edit on the same inventory |
| `sase-j0` red `check-full` | Still open, **+38**. Landing cannot mean "the full suite is green" |
| No `sase tool` command; no ToolRun in core | Still true. `_COMMAND_REGISTRARS` has no `tool`. Core grep for `ToolRun`/`tool_run` is empty. Pin `8d5341a4d5` |
| Every epic owns exactly one beta flag | Still the roadmap's default. **This epic is the exception** — see §5.2 |

**Verdict:** plan E1 now. The only shared seam with active work is `sase disk`
inventory (`sase-zw.8`). Coordinate with a bead note; do not invent a second reaper.

---

## 3. Independent verification

### 3.1 Tree seams both reports named, rechecked today

- **No `tool` registrar.** `src/sase/main/parser_registry.py` has `proc`, `monitor`,
  `disk`, `telemetry` — not `tool`. Bare-group `list` defaulting already lives in
  `parser_root_defaults.py`. Compact root help (`_COMPACT_ROOT_COMMANDS`) does not
  mention `tool`.
- **`run_silent` is a producer, not a store.** It merges stdout+stderr, prints `✓`/`✗`,
  discards successful output, and writes monitor stage JSON with **end-only**
  `recorded_at_epoch` when `SASE_MONITOR_DIAGNOSTICS_DIR` is set. Diagnostic errors are
  non-fatal. `tests/test_justfile_lint.py` asserts Justfile lines word-for-word, so E1
  must not edit the Justfile.
- **Config deep-merge is real.** `config/loading.py::deep_merge` recursively merges
  nested maps. A user overlay could splice one layer's `argv` onto another's `stages`.
  `sase.schema.json` is `additionalProperties: false` at the top level, but runtime
  config is **not** schema-validated (`config/file_hooks.py`). Rust normalization of
  whole project-layer entries is the real validator.
- **Enclosing owners already export IDs.** `SASE_MONITOR_ID` in
  `monitor/supervise.py`; `SASE_PROC_ID` in `procs/supervisor.py`.
- **`pump_output` is combined-stream.** `supervision/logs.py` pumps one stream. E1
  needs two pipes and two pumps (or an equivalent), plus a ToolRun log. Do not reuse
  `proc run -w` (detached, stderr merged, history_limit 100).
- **Telemetry store is the SQLite pattern, not the destination.** WAL, `Immediate`
  transactions, bounded busy timeout, retention inside the write transaction,
  corrupt-DB quarantine. New root, new schema.
- **Disk inventory** is composed in `disk_footprint_inventory.py::sase_state_rows`.
  Reap steps follow `disk_footprint_reap_proc.py`. No ToolRun row exists.
- **Prepared completion is exact-command.** Core
  `continuation/completion.rs` accepts only `just check` or `just check-full`. E1 must
  not change `-f` flows.
- **Metric count is pinned.** `tests/telemetry/test_metrics.py` asserts
  `len(METRIC_DEFS) == 37`. Production code has no PSI/`getloadavg` sampling
  (`os.getloadavg` appears only in a TUI perf capture helper).
- **Artifact kind `tool` is unregistered.** Unregistered labels parse as live
  non-reserved kinds. Reserve `tool` now, `offered_in_completion: false`, and do not
  resolve `tool:<run-id>` until a redacted projection exists.
- **Land-epic xprompt has no Definition of Done.** `bd/land_epic` tells the lander to
  review child notes, integrate drift, run `epic-symbols`, and close. If the plan does
  not name commands and results, the lander "runs the tests" and files a child epic.
  Live evidence: `sase-zw.8`, `sase-11e`, `sase-124` are all landing-repair children.
- **Published floor ≠ pin.** `sase-core-revision.txt` is `8d5341a4d5`.
  `pyproject.toml` declares `sase-core-rs>=0.34.48,<0.35.0`. `publish.yml` runs
  `tools/ratchet_core_window` at release. Apollo's `sase` is an editable uv tool from
  the primary checkout; `sase-core-rs` loads from the primary sase-core checkout.

### 3.2 Seven-day Bash baseline, remeasured 2026-09-19

Method: every `~/.sase/projects/*/artifacts/ace-run/*/*/*/tool_calls.jsonl` with mtime
in the last 7 days (**190 files**). Pair `ToolUse` where `tool_name == "Bash"` with the
next `ToolResult` of the same `tool_use_id` **inside that file** (Codex reuses
`item_N` ids). Duration from `duration_ms` when positive, else `recorded_at` delta.
Strip `/usr/bin/(zsh|bash|sh) -lc`, then classify by leading recipe. Drop negative
durations and runs over 6 h.

| Fact | This remeasurement | Researcher B (same day) |
| --- | --- | --- |
| Bash uses / unpaired | 13,548 / **5** | 12,974 / 3 |
| Total wall | 92.5 h | 89.9 h |
| ≥20 s share | 6.4% of calls, **94.2% of wall** | 6.5% / 94.3% |
| `just check` | 183 calls, **53.7 h (58% of all Bash wall)** | 157 / 51.1 h / 57% |
| `just check` ≥20 s p50 | 1027 s | 931 s (inline) |
| Catalog tools' share of heavy wall | **74%** | ~82% |
| Provider-timeout clusters | **29 at 120±3 s, 11 at 600±3 s** | 29 / 11 (exact match) |
| Heavy-call runtimes | codex 564, claude 250, grok 54 | 545 / 250 / 50 |

The premise holds: wrapping the named catalog (`check`, `check-full`, `install`,
`test`, `test-visual`) covers the bulk of expensive agent time, and `just check` is the
dominant target. Use **74% of heavy wall** as the realistic ceiling for those five
names, not 82%. B's ≥70% of heavy `just check` wall, judged a week after landing, is
the right success metric — and it cannot be observed at landing.

Codex still wraps every command as `/usr/bin/zsh -lc '…'`. Any adoption classifier
must unwrap that; B's first pass misfiled 92% of heavy calls by missing it.

### 3.3 Monitors, remeasured today

`sase monitor list --all --json --limit 500` → **90 rows**.

- `just check-full`: **37** monitors. B's 0-completed claim is the planning fact to
  keep: this is a known-red corpus (`sase-j0`), not an E1 exit.
- `just check`: 29 monitors.
- `verify` profile: **16/90** (up from the roadmap's 1/69).
- `elapsed_seconds` present: **51/90**.
- `completion_ref` / `host_completion_status`: **0/90**.
- Follow-up text is still the default (next-action/output present on all 90; median
  length ~1.5 k chars).

### 3.4 Overhead (from B, not re-timed)

Cold `sase --help` / `sase proc list` is ~0.9–1.7 s. Git fingerprint (`status
--porcelain=v1 --untracked-files=all` + `rev-parse` + `write-tree`) ~30–40 ms. PSI +
`getloadavg` ~0.2 ms; PSI exists on apollo. Recording is cheap enough to always be on
for 20 s+ tools. Acceptance: wrapper overhead within 0.5 s of `sase proc list` cold
start, not "zero overhead."

---

## 4. Where both researchers already agree

Keep these as binding plan text. They are also the control-plane and
`record-before-admit` invariants:

1. **Record first, admit last.** E1 is the ledger. No queue, no ETA, no receipts, no
   TUI, no `-H`.
2. **Rust owns the store and the catalog algebra; Python owns effects.** CLI, spawn,
   signal handling, git observation, PSI sampling, disk row, rendering.
3. **New SQLite entity store**, conventions copied from telemetry, not the telemetry
   DB and not the proc store (`history_limit: 100`).
4. **Project-owned `tools:` catalog** in `sase/sase.yml` as whole entries. Machine
   policy (`tool_runs:` retention) is a separate top-level key. No deep-merged argv.
5. **Exact argv, mandatory `--` for ad-hoc, no implicit shell.** Child exit is the
   wrapper exit (128+n for signals). Recording fails **open**.
6. **Identity before spawn.** The child must not start before a durable `running` row.
7. **Record facts successors need:** start **and** end fingerprints, stage timings,
   PSI/loadavg samples. Do not consume them.
8. **One log owner.** Never a second copied log. Retention lands with the first writer
   and registers a `sase disk` owner.
9. **Green-master-independent acceptance.** `sase-j0` stays open. A failing E1 test is
   never waived because master is red.
10. **Guidance-led adoption**, via `/sase_memory_write` and skill **source** templates
    (`sase skill init --diff` only; no deploy from the epic workspace).
11. **Versioned `-j` envelopes.** Missing facts are `null` plus diagnostics, never
    guessed zeros.

---

## 5. Disagreements and resolutions

### 5.1 Nine phases (A) vs seven (B) → **seven serial**

A's extra phases were: a freeze-baseline split from the store, a separate "read
surfaces" phase, the importer, and a beta-flag removal step. The telemetry store's
first commit landed wires + SQLite + bindings together; `list`/`runs`/`show` are not
demoable without `run`; the importer and flag are dropped below. Parallel 5∥6 and 7∥8
would collide in the executor and the `show` renderer (B). Serial is the shape this
repo's landing history rewards.

Steal from A anyway: golden contract fixtures in phase 1, four disqualifying
outcomes, the evaluation-artifact schema, fingerprint completeness, and reserving the
`tool:` artifact kind.

### 5.2 Beta flag (A and the roadmap) vs none (B) → **no flag**

`sase_flags.md`: an agent creates a beta flag for an epic **only when a landed phase
would otherwise expose part of an unfinished feature**. E1 changes no existing
command. Each serial phase is coherent (list, then run, then stages, then evidence).
The unfinished-looking exposure is **advertising**: keep `tool` out of
`_COMPACT_ROOT_COMMANDS` until `agent-adoption`.

A forgotten flag would leave the feature off by default — the worst outcome for
"deliverables I can test." If a later phase ships a half-wired verb, add
`tool_run_ledger` then and put its removal in the acceptance DoD. Do not create it
speculatively.

### 5.3 Importer in E1 (A, roadmap) vs defer (B) → **defer**

Imported `tool_calls.jsonl` rows have no fingerprint, stages, or load. They only
prefill "typical duration." Apollo produces ~150+ `just check` runs a week; a day of
native rows replaces that prior. Imported rows also poison later receipts unless
every query surface remembers `source: imported`. If E6 wants historical priors, put
`sase tool import-legacy` in E6's first phase, with A's conservative recognizer
(exact `just check` / `check-full` / `install` only, idempotent source key, never
upgraded to native).

### 5.4 Stage protocol: inherited FD (A) vs JSONL file (B) → **JSONL, parent commits**

`run_silent` already appends JSONL diagnostics with `O_APPEND`. Small lines are
atomic under `PIPE_BUF`. Stages in `just check` are sequential, so concurrent
corruption is not the E1 risk.

The E1 risk is **lost runs**: if the wrapper is `kill -9`'d, an FD buffer dies with
it and reconciliation has no stage timeline. A JSONL file the child already wrote
survives. E1 therefore:

- exports `SASE_TOOL_RUN_EVENTS` to a ToolRun-owned events file;
- `run_silent` appends `started`/`finished` JSONL (name, epochs, elapsed, exit,
  output bytes) when that env is set;
- the **parent** validates and commits to SQLite at finish, and again on `lost`
  reconciliation;
- also add `started_at_epoch` and `elapsed_seconds` to existing monitor stage JSON.

Do not let `run_silent` open SQLite. Do not change the Justfile. E2 can add an FD or
tail the JSONL for `show --follow`; that is not E1.

### 5.5 Enclosing owners in E1 (B) vs "leave proc fields to E2" (A) → **record on the ToolRun**

A is right that E1 must not add fields to the proc wire (`sase-11y.2` already bumped
it) and must not supervise. B is right that recording `SASE_MONITOR_ID` /
`SASE_PROC_ID` on the ToolRun is not supervision. It is the cross-epic
**one-log-owner** invariant, and it is cheap now:

- `owner: monitor:<id> | proc:<id> | foreground`
- when an enclosing owner exists, **do not create a ToolRun log**; pass bytes through
  and store `log_owner: monitor|proc`
- export `SASE_TOOL_RUN_ID` so nested `sase tool run` records `parent_run_id`

That is how `sase monitor start -p verify -- sase tool run check-full` starts filling
the expensive corpus weeks before E2, without duplicating 27 h of logs. E2 still owns
creating hand-offs (`-H`), `stop`, and `show --follow`.

### 5.6 Compact-by-default in agents (A, control-plane) vs passthrough + `-q` (B) → **both**

B's 32 hand-wrapped `just check > log; tail -n 220` calls are real: agents already
want compact output. The control-plane ranked agent-sized output as use-case #2
(Claude middle-truncates ~30 k chars). Making `-q` opt-in adds an adoption hurdle.

- **Human, no `SASE_AGENT_NAME`:** byte-exact passthrough on the child's streams;
  wrapper header/footer on stderr.
- **Agent (`SASE_AGENT_NAME` set) or `-q`:** header, one line per stage, footer,
  last `-T/--tail-lines` (default 200) on failure, pointer at `sase tool show ID -l`.
- **`-v/--verbose`:** force full streaming even inside an agent.
- Known limitation, documented: the child sees pipes, not a TTY, so colors drop. Pty
  is a follow-up, not E1.

### 5.7 Extra argv on named tools (A forbids, B allows) → **`args: allow | deny`, default deny**

`sase tool run test -- tests/foo.py` is the natural command. `run TOOL` with no extra
argv would push every scoped test into ad-hoc mode and destroy "typical duration."
Default `deny` so `check` cannot silently pick up stray args. Record extra args on the
run; typical duration groups only no-extra-arg runs.

### 5.8 Catalog: three tools (A) vs five (B) → **five**

`check`, `check-full`, `install`, `test` (`args: allow`), `test-visual`. The last two
are 4+ hours of heavy wall in the 7-day window and are how agents actually invoke
pytest/visual.

### 5.9 Store layout

Use the control-plane path, with A's per-run log directory:

```text
~/.sase/tools/                  # 0700
  runs.sqlite                   # 0600, WAL
  logs/<run-id>/stdout.log
  logs/<run-id>/stderr.log
  logs/<run-id>/events.jsonl
```

Python resolves the path from `sase_home()`; core never expands `~/.sase`. Read-only
queries must not create an empty store. One tagged log file is acceptable if dual
files make `show -l` awkward; pick one in phase 3 and freeze it in the golden
fixtures.

### 5.10 State machine → **merge**

```text
created → running → succeeded | failed | signaled | interrupted | lost
```

- A's `created` then `running` **before spawn** is a disqualifying invariant.
- B's `signaled` / `interrupted` / `lost` split is how provider `kill -9` and Ctrl-C
  become measurable. `imported` is a **source**, not a state (A).
- E1 creates attempt 1 on every native run (A's `ToolAttempt` collection) so E3
  `rerun` does not break the shape. Executor kind is `inline` only; reserve the field.
- Do not add `queued`, `refused`, `timed_out`, `canceled`, `reconciling`.

Wrapper usage/catalog errors: exit 2 with a diagnostic. Do not claim reserved code 75
(refusal/queueing, E7).

### 5.11 Published-floor smoke (A) vs no calendar waits (B) → **script yes, lander-gate no**

A's `tools/smoke_sase_core_rs_tool_runs` matches the existing
`tools/smoke_sase_core_rs_*` matrix (see telemetry). It cannot pass for **new**
bindings against the current published floor (`>=0.34.48`) until a core release
contains them. Making that the lander gate is a PyPI wait — the overnight-stall
failure mode.

Phase 1: move `sase-core-revision.txt` forward only, to a commit that still contains
every later pinned contract; add the smoke script so it exists. Lander gate: workspace
binding round-trip + pin moved. The floor smoke becomes a real CI gate after the next
core release ratchets the window. Do not stall E1 for that release.

### 5.12 `check-full` as lander work (B DoD-13) vs evidence-only (A) → **start, don't wait**

B wants the acceptance phase to run `sase monitor start -p verify -- sase tool run
check-full` and treat a green-enough result as DoD. On apollo that job is hours and
currently **never completes**. Waiting for it is how landers stall overnight.

DoD: the monitor **starts**, a ToolRun exists with `owner monitor:<id>` and
`log_owner monitor`, and the harness `--live` case for enclosing owners passes. If the
monitor happens to finish during the lander turn, apply the known-red rule (failures
confined to the named `sase-j0` suite-cost budgets). Do not block close on a completed
`check-full`.

Live dogfood **is** `sase tool run check` (or the same command under a verify monitor
if it will outrun the turn). If `check` is red, the record must show that faithfully;
fix E1-caused failures, disposition the rest.

---

## 6. Binding contracts for the plan body

Settle these in the plan **before** any phase runs. They are the merge of B's D1–D13
and A's V1 records.

**Store (D1).** Rust-owned SQLite at `~/.sase/tools/runs.sqlite`. Tables: `runs`,
`attempts`, `events`, `stages`, `samples`, `meta` (schema version; refuse newer DBs).
Append an immutable event and update the current projection in one `Immediate`
transaction. Duplicate event ids are idempotent; conflicting duplicates are integrity
errors. Retention inside every write transaction: summaries 180 d, stages/samples
60 d, logs 14 d plus a byte cap; protect `running` rows; return log ids to delete.

**Rust / Python split (D2).** Rust: wire types (`schema_version` from v1), catalog
normalization, transitions (`begin`, `record_stages`, `record_samples`, `finish`,
`reconcile` given liveness facts), queries, retention, fingerprint hashing. Python:
CLI, executor, git observation (reuse
`finalizers/prepare.py::observe_completion_repositories` and dirty-path fingerprints —
do **not** reuse the compact `_observation_fingerprint` tuple), PSI/loadavg, event
ingestion, disk row, rendering. Bindings follow `sase_core_py` +
`require_rust_binding("tool_run_…")` with `py.allow_threads`.

**V1 records (A).** `ToolDefinition`, `ToolRun`, `ToolAttempt`, `ToolRunEvent`,
`ToolStage`, `ToolLoadSample`, versioned query envelopes (truncation/cursor,
diagnostics). Fingerprint components: project identity, definition digest, per-repo
HEAD / index tree / sorted dirty+untracked entries (status, kind, mode, content hash;
never the physical workspace path), declared-input hashes, bounded toolchain probes,
completeness bit plus typed missing/error reasons. A changed tree is `mutated_input`.
Incomplete fingerprints must be visible; E4 must never mint a receipt from one.

**Executor (D3).** Spawn exact argv in a new process group, separate stdout/stderr
pipes, no shell. Wrapper lifecycle on stderr only. Protected execution argv stays
under the private root and is absent from default JSON; display argv is redacted.
Never persist an env dump; snapshot allow-listed attribution
(`SASE_AGENT_NAME`, `SASE_AGENT_WORKSPACE_NUM`, `SASE_BEAD_ID`, project, cwd) and
allow-listed env names from the catalog (`SASE_PYTEST_WORKERS`,
`SASE_TEST_GATE_DISABLED` belong on that list).

**Reconciliation (D4).** Each `running` row stores host `boot_id`, wrapper pid, and
`/proc/<pid>` start time (the sudo runner already reads
`/proc/sys/kernel/random/boot_id`). Before `runs`/`list`/`show` and at each `run`
start: a `running` row whose wrapper is definitively dead becomes `lost` ("runner
exited without settling"). Never adopt or supervise the child.

**Catalog (D6).** Read `tools:` only from the project layer as whole entries. E1
fields: `argv` (list), `description`, `stages: run_silent | none`, `inputs`, `env`
(names), `args: allow | deny`, `fingerprint.repos` / `toolchain`.
`additionalProperties: false` per entry; unknown fields get a diagnostic naming the
entry and field. Do not predeclare `receipt`, `weight`, `timeout`, `handoff`,
`cheap_stages`. Add `tools` and `tool_runs` to `sase.schema.json`. Validate the
repo's own catalog in tests.

**CLI (A §3.4 + B phase 3).** Bare `sase tool` delegates to `list` through the central
default-list machinery and prints the delegation notice. `run TOOL [-- ARGS]` /
`run -- ARGV…` (ad-hoc has `tool: null`). `runs` filters: `-t` tool, `-s` state, `-A`
agent, `-a` all projects, `-n` limit, `-j`. `show RUN` (`-j`, `-l`). Every public long
option has a short alias; none is argparse-required; help stays alphabetized. Parser,
help-golden, and bare-default tests are acceptance, not cleanup.

**Out of scope, named so the lander does not "fix" them:** E2–E8 verbs and states;
importer; pty mode; user-level catalogs; Mac live verification; prepared-completion
(`-f`) contract; `tool:<run-id>` as a resolvable artifact (reserve the kind only).

---

## 7. Lander acceptance contract

Copy this into the plan under **"Definition of Done (land agent: judge against these
items only)"**. Anything else goes to `/sase_new_task`.

**Harness.** `tools/smoke_sase_tool_runs` (name matches the existing `smoke_sase_*`
tools; B's `tool_ledger_acceptance` is the same object). Options: `--sase PATH`
(default `sase` on PATH), `--live` (slow DoD-6 / enclosing-owner cases in the current
repo), `--keep`, `-j`. Builds a temp git project whose `sase/sase.yml` defines `ok`,
`fail`, `staged` (three `run_silent` stages), `slow`. Isolated `SASE_HOME`. Asserts
only on `show -j` / `runs -j` / exit codes / stream bytes. Pytest twin in CI. Every
phase adds its cases. Close notes include `DEMO: <command> → <observed>` lines.

**DoD-1.** `sase tool` prints the delegation notice and lists `check`, `check-full`,
`install`, `test`, `test-visual` with LAST and TYPICAL columns (em-dash until a native
run exists). An invalid catalog entry names the entry and field, exit 2.

**DoD-2.** `sase tool run -- sh -c 'printf out; printf err >&2; exit 3'`: stdout is
exactly `out`; stderr contains `err` plus header/footer; exit 3; `show -j` reports
`failed`, exit 3, duration, log locator.

**DoD-3.** SIGTERM → exit 143, state `signaled`. Ctrl-C of `run -- sleep 30` → exit
130, state `interrupted`.

**DoD-4.** `kill -9` of the wrapper during `run -- sleep 30` leaves no `running` row.
The next `sase tool runs` shows `lost` with reason "runner exited without settling."

**DoD-5.** Unwritable store: `run -- echo hi` prints `hi`, exits 0, one
`run not recorded` warning, no fabricated durable id.

**DoD-6.** In this repo, `sase tool run check` then `show` lists every `run_silent`
stage with duration, unattributed time, before/after fingerprints with dirty count,
toolchain, and load samples (~1 / 10 s, PSI fields on Linux). After three runs, `list`
shows LAST and TYPICAL for `check`. Ad-hoc argv with spaces and metacharacters is
passed literally.

**DoD-7.** `sase tool run -q test -- <failing path>` prints header, stage/footer
lines, last `-T` lines, and the `show -l` pointer. `show -l` is the full log.

**DoD-8.** `sase monitor start -p verify -- sase tool run check-full` **starts** a
ToolRun with `owner monitor:<id>` and `log_owner monitor`, and no ToolRun log file. A
nested `sase tool run` records `parent_run_id`. The lander does not wait for
`check-full` to finish.

**DoD-9.** `sase disk list` shows the tool-runs row. `sase disk reap` dry-run reports
prunable logs/runs. Horizons come from `tool_runs:` config. Running rows are
protected. Symlinks, missing stores, and byte accounting follow the repaired
`sase-zw` owner contract.

**DoD-10.** `runs -j` and `show -j` carry `schema_version`. Phase-1 golden fixtures
still pass. Concurrent short runs do not lose or cross-link stages or livelock on
SQLite.

**DoD-11.** `tools/smoke_sase_tool_runs` exits 0 against `--sase .venv/bin/sase` and
against the deployed `sase` after a binding check. If the deployed binary raises
stale-wheel, the evidence records "run `sase update`" as an **owner action**, not
code work. Pytest twin is green in CI.

**DoD-12.** `tools/tool_adoption_report -d 7` runs; baseline output is in the close
note. `sase memory read lint_and_test.md` shows `sase tool run check`, `-q`, wrapping
`check-full` inside verify monitors, the unchanged `-f` rule, and the fallback when
`sase tool` is unavailable.

**DoD-13.** `just check` is green for the combined tree. Wrapper overhead is within
0.5 s of `sase proc list` cold start. `sase bead epic-symbols` is clean.

**Four disqualifiers (any one fails the epic, even if tests are green):**

1. The child starts before the durable `running` transition.
2. Any named or ad-hoc command is executed through an inferred shell.
3. Recording failure changes whether or how the child runs, or changes its exit.
4. A query reports guessed load, fingerprint, or duration facts as known.

**Evaluation artifact** (`sase artifact create`), evidence not the test: SASE commit,
core commit, pin, installed versions; exact commands and exits; hermetic JSON report;
fixture and dogfood run ids; redacted `list`/`runs`/`show`/`disk list` JSON; store/log
sizes before and after isolated retention; adoption baseline; every known limitation
or unrelated failure with its existing owner. Bryan reruns
`tools/smoke_sase_tool_runs --sase "$(which sase)"` and inspects the same runs through
the product CLI.

**Verification policy.** Core `just check` in sase-core (bindings included — `cargo
test -p sase_core` skips them). Focused parser/config/store/execution tests plus the
harness. Re-run the harness after every landing repair; the artifact cites the
post-repair results. `check-full` global green is not an exit.

---

## 8. Risks the plan has to name

| Risk | Containment |
| --- | --- |
| Lander treats "tests passed" as done | Closed DoD + harness; disqualifiers; evaluation artifact |
| E1 grows into the roadmap | Named out-of-scope list; lander sends extras to `/sase_new_task` |
| Stale deployed `.so` on apollo | Fallback sentence; binding check; `sase update` as owner action |
| Core pin races other epics | Phase 1 moves the pin **forward only** and records the SHA |
| `sase-zw.8` still editing disk inventory | Additive row + reap step; bead note on `sase-zw.8` |
| `deep_merge` splices catalog fields | Project-layer whole entries, Rust diagnostics |
| Justfile goldens | Touch only `tools/run_silent` |
| Metric-count pin | Update `len(METRIC_DEFS) == 37` in phase 5 |
| Prepared-completion regression | Keep `-f` on raw `just check` / `check-full` |
| Calendar / PyPI wait | Pin in-phase; floor smoke is not a lander gate; 7-day adoption is post-landing |
| Forgotten beta flag | Do not create one |
| Imported rows poison E4/E6 | Do not import in E1 |
| Phase-local mocks hide composition bugs | Real-path subprocess tests only for DoD-backed behavior |

---

## 9. Recommended solution

**Plan E1 now as the seven-phase serial epic in §1.** Honor
`decisions:record-before-admit`. Do not wait for `sase-11y`, `sase-zw.8`, or a core
release.

Implementation shape:

- Rust-owned SQLite ToolRun ledger at `~/.sase/tools/`, event+projection, attempt 1,
  `created → running → {succeeded, failed, signaled, interrupted, lost}`.
- Project-layer whole-entry `tools:` catalog of five names; machine `tool_runs:`
  retention.
- Foreground exact-argv executor; fail-open recording; enclosing-owner log rule;
  JSONL stage events ingested by the parent; pre/post fingerprints; PSI/loadavg
  samples.
- No beta flag; no importer; `tool` unadvertised until adoption; `-f` untouched.

Testable deliverables in three layers:

- **Per phase:** the DEMO command in the close note, plus new harness cases.
- **At landing:** `tools/smoke_sase_tool_runs --sase "$(which sase)"` and
  `docs/tool.md` "Try it."
- **After landing:** `tools/tool_adoption_report -d 7`. Target: ≥70% of heavy
  `just check` wall time wrapped within 7 days. Tighten guidance before planning E2
  if it misses. Do not make the lander wait for that week.

### Draft prompt for `/sase_plan`

```text
Plan epic E1 of research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md —
"Named tools and the ToolRun ledger" — using
research:202609/sase_tool_e1_named_tools/sase_tool_e1_named_tools.md as the design
input (read both with `sase artifact read`). Honor decisions:record-before-admit.

Structure: exactly these serial phases, all size medium: core-ledger, catalog,
foreground-run, stage-timeline, run-evidence, agent-adoption, acceptance. Give the
acceptance phase `model: <land-agent model>` (I am explicitly requesting that model).
No beta feature flag; keep `tool` out of the compact root help until agent-adoption.
Defer the tool_calls.jsonl backfill importer.

Settle in the plan body, as binding contracts, the merged decisions in
research:202609/sase_tool_e1_named_tools/sase_tool_e1_named_tools.md §6 (store path
and event+projection schema, Rust/Python split, executor/output including agent
compact default plus -q/-T/-v, states created→running→succeeded|failed|signaled|
interrupted|lost, enclosing owners and one log owner, project-layer whole-entry
catalog of check/check-full/install/test/test-visual, run_silent JSONL stage events
with parent-only store commits, pre/post fingerprints and load sampling, retention/
disk ownership coordinated with sase-zw.8, no flag, importer deferral, adoption
measured in E1 and judged after landing, reserved but unresolved tool: artifact
kind, explicit out-of-scope list). Phase 1 must produce golden contract fixtures
that later phases test against and must move sase-core-revision.txt forward only.

The plan body MUST contain:
1. "Definition of Done (land agent: judge against these items only)" — DoD-1..DoD-13
   from the design input, each a command plus observable result, nothing open-ended.
2. The four disqualifiers from the design input.
3. A rule that every phase adds its DoD cases to tools/smoke_sase_tool_runs
   (black-box, --sase PATH, isolated SASE_HOME, real CLI + real Rust store, asserts
   on -j output) and its pytest twin, uses real-path tests only, and writes
   `DEMO: <command> → <observed>` lines in its close note.
4. Known-red rule: check-full failures confined to the sase-j0 suite-cost budgets
   (named) are pre-existing; the lander starts a verify-monitor wrapped check-full
   to prove enclosing-owner recording and does not wait for that monitor to
   complete; anything else is epic work or /sase_new_task.
5. "Out of scope — successor epics, not remediation": E2–E8 items, importer, pty
   mode, user-level catalogs, Mac live verification, and the prepared-completion
   (-f) contract.
6. "No calendar or release waits": core pin moves in-phase; the published floor
   ratchets at release; tools/smoke_sase_core_rs_tool_runs is added but is not a
   lander gate until the floor exports the bindings; the 7-day adoption target is
   measured after landing.
7. An evaluation-artifact schema for the acceptance phase (sase artifact create).

Memory changes I authorize for this plan (name them in the relevant phase steps):
update sase/memory/lint_and_test.md to teach `sase tool run check`, agent compact
output / `-q`, wrapping check-full inside verify monitors, the unchanged -f rule,
and the fallback when `sase tool` is unavailable; add glossary strands "Tool Run"
and "Tool Catalog"; update the sase_monitor skill source template; regenerate with
`sase memory init` / `sase skill init --diff` only — do not deploy generated skills
from the epic workspace.
```
