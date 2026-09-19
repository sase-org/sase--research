# Planning E1: named tools and the ToolRun ledger

**Researcher A** · 2026-09-19 · independent implementation study

**Inspected state:** SASE `59c82a36e85f`; pinned sase-core
`8d5341a4d5e98b3b22b52395fffd267128bbf06a`; opened sase-core HEAD
`4a8c6d40de0f` (the pin is its ancestor); declared Python floor
`sase-core-rs>=0.34.48,<0.35.0`.

**Primary inputs:**
`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`,
`research:202609/sase_tool_control_plane/sase_tool_control_plane.md`, the current SASE
and sase-core trees, live bead state, and the landing history of comparable epics. I did
not inspect or obtain findings from the other researcher in this swarm.

## Answer up front

Plan the first roadmap epic as **nine medium phases** that deliver one product: a
foreground command obtains a durable ToolRun identity before it starts, runs without a
shell, reports stages, fingerprints and machine-load observations into a machine-local
Rust-owned ledger, preserves the child's output/exit semantics, and is queryable through
`sase tool list|run|runs|show`.

The implementation should be a thin Python execution adapter over two Rust-owned
contracts:

1. a provenance-aware, project-owned `tools:` catalog; and
2. an append-oriented SQLite ToolRun store with validated transitions and versioned
   query wires.

Do not put supervision, hand-off, prediction, receipts, failure classification,
admission, or TUI rendering into this epic. Do record the raw facts those successors
will need now, because fingerprints and load cannot be reconstructed later.

The lander must not be asked merely to “run the tests.” Its required deliverables should
be:

- a checked-in, hermetic `tools/smoke_sase_tool_runs` acceptance executable;
- a published-core-floor smoke that installs the exact released wheel and exercises the
  full ToolRun binding family;
- a real dogfood run of the repository's catalogued `check` tool;
- versioned JSON evidence from `list`, `runs`, `show`, and `disk list`; and
- a durable evaluation artifact containing those commands, outputs, run IDs, revisions,
  and any unrelated red-master disposition.

That combination gives Bryan a stable command to rerun, a real product path to inspect,
and immutable evidence of what the lander actually verified.

## 1. What changed since the roadmap was written

Two prerequisite moves in the roadmap are already complete:

- `sase-zm` is closed with resolution `superseded`; all fourteen old phases were swept
  closed and no old implementation needs preserving.
- The presentation collision is gone: commit `868abb2467` renamed the existing agent
  Tools panel/package to **LLM Calls**. Commit `85d6fc74bb` added the accepted
  `decisions:record-before-admit` record.

E1 therefore does not need prerequisite phases for either action. It should cite and
enforce the decision instead.

Other surrounding work has moved, but does not block the foreground ledger:

- `sase-11y` now has five of ten service-host phases closed, including the Rust service
  foundation and host runtime. E1 must avoid proc/service ownership fields entirely;
  those belong to E2.
- `sase-x7` is still changing canonical shared formats. ToolRuns must be born as one
  canonical V1 format with no legacy writer or dual backend, and remain machine-local.
- `sase-zw` is still in nested landing repair (`sase-zw.8.7`) after two landers found
  retention safety gaps. E1's disk-owner phase should integrate after or explicitly
  rebase over that work rather than independently inventing cleanup orchestration.
- `sase-j0` remains open with 38 corroborations: `just check-full` is still red on
  master. E1 acceptance cannot define success as “the global full suite is green.”
- `sase-11e` and `sase-124` are also in child landing epics after their authored phases
  closed. This is strong evidence that phase-local green tests are not a sufficient
  landing contract.

The current CLI has no `tool` registrar. It does have the right insertion points:
`src/sase/main/parser_registry.py` for lazy registration,
`src/sase/main/parser_root_defaults.py` for bare-group delegation to `list`, and
`src/sase/main/entry.py` for handler dispatch. The new group can follow existing
conventions without another parser framework.

## 2. Current seams that should determine the design

### 2.1 `run_silent` is a producer, not the ledger

`tools/run_silent` currently:

- knows the stage label and terminal exit code;
- emits only a terminal check/cross line, with no elapsed time;
- discards successful captured output;
- writes monitor-stage diagnostics only when monitor/artifact environment variables are
  present; and
- deliberately treats diagnostic-recording errors as non-fatal.

That behavior is valuable and should remain. E1 should add a small stage-event protocol
to it, not move command execution or ToolRun state into the Bash script. The parent
`sase tool run` process owns the ToolRun and log, while `run_silent` is one optional
structured producer. Tools without it still receive a top-level attempt timeline.

The stage protocol should be an inherited pipe/file descriptor, not repeated recursive
`sase` invocations and not concurrent JSON appends. `run_silent` writes framed
`started`/`finished` events to the descriptor when `SASE_TOOL_EVENT_FD` is present. The
parent validates and commits them. This keeps per-stage overhead tiny, centralizes store
writes, supports live readers, and prevents parallel writers from corrupting a shared
JSONL file.

### 2.2 Config provenance is already a solved pattern

`src/sase/service/config.py` and `crates/sase_core/src/service/config.rs` demonstrate the
desired boundary: Python discovers ordered `ConfigLayer` inputs; Rust owns composition,
validation, field provenance and actionable diagnostics; Python exposes typed records.
The tool catalog should reuse that shape with the provenance rule reversed:

- semantic tool definitions are accepted **only** from the current project's local
  `sase/sase.yml` layer;
- machine operational settings are accepted from defaults/user/machine overlay and
  ignored in project-local config with a diagnostic.

Keeping the concerns under separate top-level keys makes the rule obvious:

```yaml
tools:
  check:
    description: Fast repository verification
    argv: [just, check]
    cwd: .
    stages: run_silent
    fingerprint:
      repos: [primary, sase-core]
      inputs: [pyproject.toml, uv.lock, sase-core-revision.txt]
      toolchain:
        - [python, --version]
        - [just, --version]
  check-full:
    description: Exhaustive repository verification
    argv: [just, check-full]
    cwd: .
    stages: run_silent
    fingerprint:
      repos: [primary, sase-core]
      inputs: [pyproject.toml, uv.lock, sase-core-revision.txt]
  install:
    description: Install the repository environment
    argv: [just, install]
    cwd: .

tool_runs:
  retention:
    logs_days: 14
    samples_days: 30
    summaries_days: 180
```

`tools:` is repository identity. `tool_runs:` is machine policy. A user or machine
overlay must not silently change what the project name `check` means; a project must not
silently shorten the host's shared evidence horizon.

E1 should accept only fields it implements. In particular, do not predeclare
`receipt`, `weight`, `timeout`, `handoff`, or `cheap_stages`. Later epics can add them
with explicit schemas once their semantics exist. `stages: run_silent` selects an event
protocol; it does not duplicate the Justfile's stage list in YAML.

### 2.3 The existing telemetry store is a model, not a destination

The Rust telemetry store already establishes useful local SQLite conventions:
transactions, a bounded busy timeout, schema metadata, corruption quarantine, explicit
retention, query wires, and PyO3 adapters. Reuse the conventions, not the database.
Telemetry keeps aggregate metric samples and cannot reconstruct a ToolRun. The proc
store's history limit of 100 is even less suitable.

Use a distinct root such as:

```text
~/.sase/tool-runs/
  runs.sqlite
  logs/<run-id>/stdout.log
  logs/<run-id>/stderr.log
```

The directory is `0700`; databases and logs are `0600`. The database uses WAL, a
bounded busy timeout, explicit schema versioning, foreign keys, and transactional state
plus event updates. Read-only queries must not create an empty store.

The current disk inventory is composed in
`src/sase/core/disk_footprint_inventory.py`, and owner cleanup is under active repair by
`sase-zw`. Add the ToolRun store/log root as one explicit owner there and route pruning
through the same `sase disk reap` owner-delegation result contract. Do not add a private
background reaper or make reads prune implicitly.

### 2.4 Existing fingerprints are not complete enough for ToolRuns

Host completion already collects useful repository facts in
`src/sase/finalizers/prepare.py`: HEAD, HEAD tree, index tree, and per-dirty-path status,
mode and content hashes. But `_observation_fingerprint` in
`src/sase/monitor/host_completion_state.py` uses only repository/head/tree/index tuples;
unstaged and untracked content is not part of that compact comparison.

Do not reuse that compact tuple as the ToolRun fingerprint. Define one canonical Rust
fingerprint contract with these components:

- stable project identity and canonical tool-definition digest;
- each declared repository's HEAD, index tree, and sorted dirty/untracked entries
  (status, kind, mode, content hash; never the physical workspace path);
- hashes and presence/error facts for declared inputs, including ignored inputs when
  intentionally listed;
- bounded, explicitly declared toolchain probe outputs; and
- a completeness bit plus typed missing/error reasons.

Record both start and end fingerprints. A tool that changes its own inputs is visibly
`mutated_input`; a later receipt epic must never mint a receipt from an incomplete or
changed fingerprint. This is recording only in E1—no reuse decision belongs here.

### 2.5 Legacy LLM-call rows are approximate evidence

Normalized `tool_calls.jsonl` rows provide timestamps, duration, cwd, attribution and a
bounded command summary. They do not provide exact argv, a tree fingerprint, load,
stage events or necessarily complete command text. The importer must therefore never
pretend that those rows are native ToolRuns.

Backfill only conservatively recognized short commands (for example exact `just check`,
`just check-full`, and `just install`) as `source: imported`, with explicit quality
flags and a source-row idempotency key. Imported rows can seed a visibly approximate
historical duration when no native observations exist, but must be excluded from future
receipt validity and load-conditioned prediction by default.

Use an explicit, idempotent `sase tool import-legacy` operation rather than an implicit
scan on `list` or `runs`. A bounded checkpoint lets each host resume. The same scan can
report adoption observations—exact raw invocation versus exact wrapped invocation—but
must publish its denominator and excluded/unknown count. It is an adoption estimate,
not an execution recognizer.

## 3. Recommended V1 contracts

### 3.1 Rust-owned records

Define bounded, versioned wires and round-trip fixtures for:

| Record | Required V1 content |
| --- | --- |
| `ToolDefinition` | project, name, description, exact argv, repo-relative cwd, stage protocol, fingerprint specification, canonical definition digest, config provenance |
| `ToolRun` | run id, source (`native`/`ad_hoc`/`imported`), project, definition snapshot/digest, attribution, created/start/end timestamps, current outcome, current attempt id, recording health |
| `ToolAttempt` | attempt index (one in E1), executor kind `inline`, owner pid + boot/start identity, protected execution argv locator, redacted display argv, cwd identity, exit/signal outcome, log locators, start/end fingerprints |
| `ToolRunEvent` | monotonic per-run sequence, idempotency key, event kind, observed/recorded times, bounded payload |
| `ToolStage` | stable stage id, label, started/finished times, state, exit/signal, duration, output counts/capture error; one open stage may remain on interruption |
| `ToolLoadSample` | observed time, platform/source, loadavg, available PSI fields, memory-pressure facts, missing/error flags |
| query envelopes | schema version, generated-at/change token, records, truncation/cursor facts, diagnostics |

The store should append an immutable event and update the current run/stage projection in
one transaction. This gives `runs` cheap queries while retaining a trustworthy timeline
for E2 reconciliation and later attempt chains. A duplicate event id is idempotent; a
conflicting duplicate is an integrity error.

Keep E1's legal lifecycle small:

```text
created -> running -> succeeded | failed | interrupted
```

`imported` is a source/quality property, not an outcome. Do not add `queued`, `refused`,
`timed_out`, `canceled` or `reconciling` until an epic implements their authoritative
owner. Reserve fields for an executor reference, but E1 accepts only `inline`.

One ToolRun is the semantic request and owns an explicit attempt collection; E1 creates
attempt 1. This avoids a breaking shape when `rerun` arrives. Run IDs should be opaque,
sortable, collision-resistant and stable across query surfaces.

### 3.2 Security and redaction

Never persist an environment dump. Snapshot only allow-listed attribution keys such as
`SASE_AGENT_NAME`, `SASE_AGENT_TIMESTAMP`, `SASE_BEAD_ID`, project and workspace
identity.

Store protected execution argv separately from display argv. The protected form stays
under the private ToolRun root and is never emitted by default JSON; display argv is
redacted before entering ordinary rows. Catalogued argv should contain no secrets.
Ad-hoc runs need explicit redaction controls and a warning when a likely secret appears;
secret detection is a guardrail, not a guarantee. If an argument is deliberately not
recorded, mark replay unavailable rather than storing a fake command.

Reserve `tool` in the artifact-kind catalog now (not offered in completion) so a plugin
cannot claim it. Do not expose `tool:<run-id>` as a resolvable artifact until
`sase artifact read tool:<run-id>` has an authenticated, redacted projection. Stable run
IDs and `sase tool show` are sufficient for E1.

### 3.3 Foreground execution semantics

The Python adapter performs effects; Rust validates decisions and records state:

1. Resolve the project-only catalog or validate the ad-hoc `-- ARGV...` form.
2. Generate the run/attempt identity and fingerprint.
3. Commit `created`, then `running`, **before** spawning.
4. Spawn exact argv in a new process group with no implicit shell.
5. Pump stdout and stderr as bytes, preserving each stream and writing the sole ToolRun
   logs. On a human TTY, stream bytes through. Inside an agent, default to compact stage
   lines and keep the full child output in logs; a failure prints a bounded excerpt.
6. Consume validated stage events and sample load at start, approximately every ten
   seconds, and at end. Linux records PSI plus loadavg; other platforms record explicit
   fallbacks/unavailable fields rather than fabricated PSI.
7. Forward termination signals to the process group, reap it, record the exact numeric
   exit or signal, and finish the attempt transaction.

For ordinary numeric child exits, the wrapper exits with the same number. For a signal,
record the signal explicitly and use the shell-compatible `128 + signal` wrapper exit.
Recording failure is fail-open: warn clearly, run the child, and preserve its exit. It
must not print a run as durable if no row was committed. Admission is not present, so
there is no fail-closed branch.

Record the wrapper's owner process identity. On `list`, `runs`, `show`, or a subsequent
run, bounded reconciliation may mark a `running` inline attempt `interrupted` only when
the stored boot/start identity is definitively dead or mismatched. It never adopts or
supervises the child. That closes stale foreground rows without creating a fourth
supervisor.

### 3.4 Query semantics

- Bare `sase tool` delegates to `list` through the central default-list machinery.
- `list` shows catalog name, last native result, native sample count, median duration
  (not “typical” without `n`), and a separately labeled imported fallback if necessary.
- `runs` returns newest-first history with bounded default count and filters for tool,
  outcome and agent.
- `show RUN` renders definition snapshot, attribution, fingerprints, attempt and stage
  timelines, sample coverage, recording diagnostics and log locators.
- `run TOOL` accepts no extra argv in V1. `run -- ARGV...` is ad-hoc and the `--` is
  mandatory. No shell string is inferred.
- `list`, `runs`, and `show` expose versioned `-j/--json` envelopes. Protected argv and
  raw logs are absent. Timestamps are RFC 3339 UTC; durations are integer milliseconds;
  missing facts are `null` plus diagnostics, never guessed zeros.

Help and subcommands stay alphabetized; every public long option has a short alias; no
option is required. Parser, help golden and bare-default tests are acceptance, not
cleanup.

## 4. Phase plan

Nine `medium` phases keep every worker in direct implementation mode and give the
lander one integrated acceptance phase instead of forcing it to invent a child epic.

| # | Phase | Depends on | Concrete exit |
| --- | --- | --- | --- |
| 1 | **Freeze baseline and V1 contracts** | — | Deterministic old-behavior fixtures; shared JSON wires for definitions, runs, attempts, events, stages, samples and fingerprints; state-machine/property tests; explicit E1/non-E1 boundary. |
| 2 | **Implement the Rust ledger store** | 1 | SQLite schema/migrations, append+projection transactions, idempotency/conflict tests, concurrent writer/read tests, corruption/read-only behavior, retention primitives, PyO3 bindings. |
| 3 | **Compose the catalog and publish the core floor** | 1–2 | Rust layer composition/provenance, Python typed facade, config schema/default runtime policy, `check`/`check-full`/`install` catalog entries, exact released-wheel smoke, core revision/minimum/lock ratchet. |
| 4 | **Deliver the foreground runner** | 3 | Lazy CLI registration, bare default, named/ad-hoc execution, pre-spawn record, process-group/signal handling, protected/display argv, stream/log behavior, exact exit and fail-open tests. Beta flag gates user exposure. |
| 5 | **Record stage, fingerprint and load facts** | 4 | FD event protocol in `run_silent`, start/end fingerprints, linked-repo/input/toolchain coverage, PSI/loadavg sampler, open-stage interruption and mutation/incompleteness tests. |
| 6 | **Ship durable read surfaces** | 2, 4–5 | `list`, `runs`, `show`, stable JSON envelopes, median/sample provenance, pagination/filtering, no-create read behavior, owner-liveness reconciliation, compact agent output. |
| 7 | **Own retention and import legacy history** | 5–6 | ToolRun disk inventory row and reap owner, summaries/samples/log horizons, safe dry-run/apply tests, idempotent bounded `import-legacy`, quality flags and adoption/bypass denominator. Coordinate with/after `sase-zw`. |
| 8 | **Make the wrapper the documented path** | 6–7 | Update source instruction/memory/skill templates through the required memory-write workflow; preview generated skills only; examples use `sase tool run check`; bypass metric is visible. No deployment from the epic workspace. |
| 9 | **Prove and activate the combined product** | all | Checked-in acceptance executable, exact floor-wheel test, real dogfood run, store-failure/concurrency/crash matrix, disk/import tests, evaluation artifact, beta Off-branch deletion, flag bead close, no epic-symbol residue. |

Phases 5 and 6 may run in parallel after phase 4 if their file ownership is separated;
phases 7 and 8 may also run in parallel. Phase 9 is deliberately serial and depends on
every other phase. Do not split core contract and store work across parallel workers
that both edit the export/PyO3 registries.

Use one temporary beta flag, for example `tool_run_ledger`, only while early phases are
landed but incomplete. Create it through `sase flag new`, test both branches, and remove
the disabled branch before the epic closes. The catalog schema and retention settings
are permanent configuration, not flags.

## 5. The lander's executable acceptance contract

The recurring failure pattern in recent epics is not weak phase effort; it is acceptance
that proves components with mocks but misses their real composition. The `sase-zl`
lander found ancestry, recovery-call, reader-adoption and rollout failures after twelve
phases had closed. The `sase-zw.8` lander reproduced unsafe deletion, symlink, exit-code,
byte-accounting and cross-filesystem errors after six repair phases had closed. Current
`sase-11e` and `sase-124` likewise have child landing epics after all original phases
closed.

E1 should put the following contract in its plan, not leave it as lander discretion.

### 5.1 Checked-in repeatable deliverables

`tools/smoke_sase_tool_runs` should create a disposable SASE home and temporary Git
project with a local tool catalog, invoke the real CLI in subprocesses, and assert:

1. bare `sase tool` and explicit `list` behavior plus stable JSON schema;
2. a two-stage success, including ordered stage start/finish and nonzero durations;
3. a stage failure with exit 7, exact wrapper exit, bounded console output and complete
   stored failure/log evidence;
4. ad-hoc argv containing spaces and shell metacharacters is passed literally, proving
   no implicit shell;
5. stdout and stderr bytes remain on their original streams in human mode, while agent
   mode stays compact and the logs retain both;
6. signal interruption and dead-owner reconciliation produce `interrupted`, never
   success or an eternally running row;
7. many concurrent short runs produce no lost/cross-linked stages and no unbounded
   SQLite-lock failures;
8. an unavailable/read-only/corrupt store warns and still runs the child with its true
   exit, without fabricating a durable run;
9. fingerprints are stable across equivalent workspace paths and change for HEAD,
   index, dirty, untracked, declared-input, linked-repo, definition and toolchain
   changes; incomplete probes are explicit;
10. injected Linux/macOS/unavailable load samplers produce honest typed observations;
11. retention removes logs before samples before summaries, protects running rows, and
    reports byte/count outcomes through `sase disk list/reap`; and
12. importing the same legacy corpus twice is idempotent and never upgrades approximate
    rows to native evidence.

The executable must return nonzero on a failed assertion, print a short human summary,
and optionally emit one versioned JSON report. It must not read or mutate the real
`~/.sase` store.

Add a sibling `tools/smoke_sase_core_rs_tool_runs` to the existing published-floor smoke
matrix. It installs the declared minimum wheel into isolation and performs an actual
create/start/stage/finish/query round trip. A mock module or a locally built HEAD wheel
does not satisfy this gate.

### 5.2 Real product evidence

After the hermetic executable passes, the lander runs on the combined tree:

```text
sase tool list --json
sase tool run -- python -c <deterministic stdout/stderr/exit fixture>
sase tool run check
sase tool runs --json
sase tool show <fixture-run-id> --json
sase tool show <check-run-id> --json
sase disk list --json
```

The first run makes output/exit claims independently of repository health. The real
`check` run proves the project's catalog, Justfile, `run_silent`, core binding, Python
adapter and durable queries together. If `check` fails, the record must faithfully show
that failure; the lander fixes E1 failures and separately dispositions unrelated
pre-existing failures.

The evaluation Markdown registered with `sase artifact create` contains:

- SASE commit, core commit, pinned revision and installed distribution version;
- exact acceptance commands and exit codes;
- the hermetic JSON report;
- fixture and dogfood run IDs;
- redacted `list`/`runs`/`show`/`disk list` JSON;
- store/log sizes before and after isolated retention;
- import source-row counts, imported/native split and idempotency result;
- adoption numerator, denominator, excluded count and observation window; and
- every known limitation or unrelated test failure with its existing owner.

The artifact is evidence, not the test itself. Bryan can rerun the checked-in executable
and inspect the same runs through the product CLI.

### 5.3 Verification policy

- Run the core repository's complete Rust/PyO3 check and the exact published-floor
  smoke.
- Run focused parser/config/store/execution tests and the hermetic acceptance executable.
- Run the primary `just check` through `sase tool run check`, thereby dogfooding E1.
- A `check-full` run may be useful evidence, but its global green result is not an epic
  exit while `sase-j0` remains open. Classify failures by whether E1 introduced them;
  never waive a failing E1-focused test because master is red.
- Re-run the executable after every landing repair. The final artifact must refer to
  the post-repair results, not an earlier phase result.

The plan should name four disqualifying outcomes explicitly:

1. the child starts before the durable `running` transition;
2. any named/ad-hoc command is executed through an inferred shell;
3. recording failure changes whether or how the child runs, or changes its exit; and
4. a query reports guessed load/fingerprint/duration facts as known.

## 6. Main risks and how the plan contains them

| Risk | Containment |
| --- | --- |
| E1 grows back into the entire roadmap | Put the excluded verbs/states in the plan. No hand-off, stop/follow, receipts, failures, ETA, queue, admission or TUI. |
| Core/Python skew | Finish bindings and release first; exact minimum-wheel smoke; ratchet pin/minimum/lock in the owning phase. |
| Config meaning varies by host | Project-only semantic catalog, machine-only runtime policy, Rust provenance diagnostics. |
| SQLite contention changes command behavior | Short transactions, bounded timeout, parent-owned writes, fail-open execution, concurrent acceptance. |
| Stale `running` rows | Persist boot-aware owner identity and reconcile only definitive death; no adoption/supervision. |
| Logs or argv leak secrets | Private root, separate protected/display argv, no env dump, redacted JSON, explicit replay-unavailable state. |
| `run_silent` becomes a second store writer | FD events to the parent; parent alone validates and commits. |
| Imported data poisons later decisions | `source: imported`, quality flags, idempotent source key, excluded from receipts/calibration by default. |
| Retention repeats `sase-zw` mistakes | Integrate with the repaired owner framework; test symlinks, missing/malformed stores, concurrent writers, errors and exact byte accounting. |
| Phase tests pass while product composition fails | Checked-in real-subprocess acceptance plus real catalog dogfood and floor-wheel round trip. |

## 7. Alternatives rejected

- **Reuse telemetry SQLite.** It is aggregate-oriented and cannot preserve one semantic
  run, attempts, stages, attribution, logs and fingerprints.
- **Reuse the proc store.** Retention of 100 terminal rows destroys the corpus and E1
  foreground execution is not a proc supervisor.
- **Write ToolRuns from `run_silent`.** It excludes tools without that wrapper, creates
  multiple writers, loses top-level lifecycle ownership and makes exact command exit
  semantics harder to protect.
- **Declare every stage in YAML.** It duplicates the Justfile, drifts immediately and
  cannot represent dynamic scoped-test behavior. The runtime event protocol is the
  source of observed stages.
- **Let merged config override tool argv.** The same name would mean different work on
  different machines, invalidating fingerprints and later receipts/predictions.
- **Parse arbitrary shell strings during import.** The legacy rows contain bounded
  summaries, not exact argv. Conservative approximate rows are honest; reconstructed
  native-looking rows are not.
- **Make one green `check-full` the landing proof.** It is currently red independently
  of E1 and has repeatedly hidden whether a feature's own end-to-end path was actually
  exercised.
- **Ask the lander to devise acceptance.** Recent landing history shows that this turns
  missing integration tests into surprise child epics. The repeatable harness and
  evidence schema belong in the original plan.

## Recommended solution

Create E1 as the nine-phase epic above. Use the existing service-config composition
pattern for a strictly project-owned catalog, a separate machine-owned `tool_runs`
policy, and a new Rust SQLite ledger whose append events and current projections are
updated atomically. Let Python own only project/config discovery, fingerprint/load
observations, exact-argv subprocess execution, byte pumping and presentation. Extend
`run_silent` with a parent-owned FD event protocol. Record complete start/end facts now,
but leave all policy consumers to later epics.

Make the last phase a product acceptance/release phase with two checked-in smoke tools,
an exact published-core-floor round trip, a real `sase tool run check` dogfood run, and a
durable evaluation artifact. Treat that executable acceptance contract—not a globally
green `check-full`, closed phase beads, or a prose claim—as the condition for the epic
lander to close E1.
