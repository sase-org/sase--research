# sase-core P1 Guardrails: Implement a Trimmed, Redesigned Structure Gate, Not the Plan as Written

Date: 2026-09-24. This is the lead researcher's consolidation of three independent reports on the
`P1: guardrails (one epic; before any further restructuring)` section of
`research:202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md` (consolidated 2026-09-21 against
sase-core `8886406`). I re-checked every claim the reports disagreed on against sase-core `eef7ca4` (still
`origin/master` at writing), sase `329d4049b`, and the live bead store. That included an independent compiler
experiment and a replay of each size-gate design over post-split history.

| Dependency | Preserved report | Immutable snapshot | Main contribution |
| --- | --- | --- | --- |
| `research.2g.cld` | [cld](sase_core_p1_guardrails__cld.md) | `file:explicit:348be65dfc8b2e87e4cf1d79` | Found that the compiler already enforces registration. Replayed each gate design over every post-report commit. Showed three P1 items would create new shared hubs. Measured drift since the report. Gave the most detailed redesign |
| `research.2g.mus` | [mus](sase_core_p1_guardrails__mus.md) | `file:explicit:276a20a95474796295e56d40` | Split the work into a deterministic gate epic and a parallel track. Proposed sunset clauses and per-check exit criteria. Pointed out that `.pyi` stubs do not buy type coverage |
| `research.2g.gem` | [gem](sase_core_p1_guardrails__gem.md) | `file:explicit:536a5d0ce74916f9d4fc7ecd` | Limited the `//!` rule to module roots, so agents are not pushed to write filler docs. Kept per-value getters as forwarders during migration. Made the case for unbundling the flakes by domain |

No predecessor chat transcripts were read.

---

## Bottom line

**Yes, implement P1, but not as written.** All four analyses agree on the direction: make the invariants
machine-checked before any further restructuring (P2 de-hub, P3 crate split). They also agree on three changes:

1. The size ratchet must count **non-test lines**.
2. The **flake burn-down** leaves the epic and runs in parallel.
3. The syn **"move items" tool** is deferred to P2.

Where the three reports disagreed, the evidence settled each question, mostly in `cld`'s favor:

| Question | cld | mus / gem | Lead verdict (evidence in §2) |
| --- | --- | --- | --- |
| Registration-completeness gate | Drop: the compiler already enforces it | Implement: "invisible to the compiler" | **Drop.** I reproduced `dead_code` firing on an unregistered binding. Fix `AGENTS.md` step 4 instead |
| Size rule | Ceiling of 2,000 non-test lines, grandfathered caps | Keep shrink-only budgets and warn at 1,200, but count non-test lines | **Ceiling.** mus/gem's amended rule still fails 35% of commits; the ceiling fails on one real violation |
| Generated binding inventory | Move to P2, never checked in | Check it in, gate staleness, have sase consume it | **P2, not checked in.** sase's checker must probe the *installed floor wheel*, which a source inventory cannot describe |
| Schema-version registry | Rework as an optional sase-side check | Implement the table plus one exporting binding | **Rework.** sase's constants are reader pins, and a hand table of 164 fast-growing constants would become a hub |
| `docs/MODULES.md` | Drop; keep only the module-root `//!` rule | Check it in and gate staleness | **Drop.** `just modules` is already fresh by construction |
| Cycle extractor | Text-level with a baseline | mus: syn-based, warn-then-deny | **Text-level with a baseline**, plus a replay and fixture tests before landing |
| `*_parity.rs` rename | P2 or drop | gem: include; mus: drop as a gate | **Leave out of P1**; do it in P2's import rewrite |

**The trimmed P1 is one small sase-core epic** (two phases, or one medium task). It adds a single `check.sh structure`
step (under 0.5 s) with a size ceiling, a module-cycle ratchet, a hub-count freeze and module-root docs, plus a route ↔
contract test. Three things sit outside it: a one-line `AGENTS.md` correction to make today, the six flake tasks
launched now, and an optional sase-side schema-skew check. That gives about a third of the plan as written, and adds
no new shared files for ordinary feature commits to edit.

---

## 1. Why guardrails are worth it now

The P0 epic (`sase-165`) landed all seven phases on 09-22 and is still in `in_progress` land. Several of its outcomes
change what P1 has to do:

- The `//!` binding manifest is deleted, with the note "nothing parses this header".
- `check.sh features` and the hakari workspace-hack are in place. They set the precedent for a Python gate inside
  `check.sh`.
- `just modules` prints every module root's summary.
- `AGENTS.md` now reaches agents. It states P1's rules in prose: import by module path, add no root `pub use` names or
  `core_*` aliases, and keep new files ≤1,500 lines.

**The prose rules leaked within days, so a mechanical check is justified.** Measured from `8886406` to `eef7ca4`
(three days, 23 Rust-touching commits); I re-verified every figure:

| Drift | Evidence |
| --- | --- |
| Size | Rust lines +12,650 (to 394,325). Files over 1,500 total lines went from 41 to 44 (80 are over 1,200). `provider_usage/store.rs` gained +348 non-test lines in one commit (`cfe1902`), reaching 2,254 |
| Coupling | A new cycle. `agent_clan_record.rs:22` imports `agent_scan::wire`, and `agent_scan/scanner.rs:154` and `agent_scan/index/query.rs:407` call back into `agent_clan_record`. The `agent_runtime`/`agent_scan` knot grew from 2 to 3 modules |
| Hubs | Despite the `AGENTS.md` rule, root `pub use` names went 2,674 → 2,677 and `core_*` aliases 654 → 657 |
| Flakes | All five named flakes are still `ready` and untriaged. `sase-15g` collected 4 corroborations from 4 different land agents in 2 days, and a new one arrived (`sase-17n`) |

---

## 2. The disagreements, resolved

### 2.1 Registration completeness: the compiler already does it (lead-verified)

mus called a missing registration "invisible to the compiler". gem said it "compiles completely clean … no build
warning". The source report's §4.3 and sase-core `AGENTS.md` recipe step 4 ("The compiler does not check this") say the
same. **For this crate, that is false.**

- **Why the compiler catches it.** Every binding is a private or `pub(crate)` function inside a private module. No
  `#[pyfunction]` is `pub`, and there is no `allow(dead_code)` anywhere in `sase_core_py`. So rustc's `dead_code` lint
  covers every binding. `just check` runs clippy with `-D warnings`, which turns the warning into a gate failure.
- **cld's experiment.** On a copy of `eef7ca4`, unregistering `py_bead_snooze` failed
  `check.sh clippy -p sase_core_py` with `function 'py_bead_snooze' is never used`.
- **My independent experiment** (another `git archive` copy, a separate target dir, and different bindings in other
  domains), run with `./scripts/check.sh check -p sase_core_py`:
  - Unregistering the private `py_telemetry_prune` gave `warning: function 'py_telemetry_prune' is never used`.
  - Unregistering the `pub(crate)` `py_artifact_link_event_schema_version` gave the same warning. That binding is
    *still called from a test*, and the warning fires anyway, because the lib target does not see test code.
  - Unregistering `py_update_proc` produced **no warning**. It is one of the escape hatches, since `procs/mod.rs:190`
    calls it.
- **The escape hatch is exactly 5 bindings.** A scan confirms `cld`'s list: `py_append_proc`, `py_update_proc`,
  `py_prune_procs`, `py_read_procs_snapshot` and `provider_routing_context_from_parts`. Each is called from other
  non-test code.
- **What else a text gate would add.** It would also catch duplicate registration and registration in the wrong
  domain. Both are harmless, because every domain registers into the same module.

**Verdict:** drop the gate.

- Correct `AGENTS.md` step 4 today. It currently teaches agents to hand-count, as `sase-14s.1` did ("827 = 827").
- Optionally move the 5 shared bodies into plain helpers so the lint covers every binding (about 839).
- The compiler's guarantee rests on two assumptions: no `pub fn` bindings and no `allow(dead_code)` in `sase_core_py`.
  A two-regex check in the structure gate keeps both true. That check is cheaper and more robust than a registration
  parser.

### 2.2 Size ratchet: non-test lines are necessary but not enough; use a ceiling

All four analyses agree that inline tests must not count. At HEAD, 25 of the 44 files over 1,500 lines are over only
because of inline tests, and the source report itself says those tests should stay beside the code. mus and gem kept
the rest of the rule: shrink-only budgets, new files ≤1,500, and a warning at 1,200. cld replaced it with a ceiling.
I replayed each design over every Rust-touching commit from `8886406` to `eef7ca4`:

| Rule | Commits failing (of 23) |
| --- | --- |
| As written: total lines, per-file budgets that only shrink, new files ≤1,500 | 17 (74%) |
| mus/gem amendment: the same rule, counting non-test lines | 8 (35%) |
| Lead variant: a gate at 1,500 non-test lines, grandfathered files capped at their baseline rounded up to the next 250 | 6 (26%) |
| **cld: every source file ≤2,000 non-test lines, grandfathered files capped at their baseline rounded up to the next 250, test-only files ≤3,000 total lines** | **2 (9%): `cfe1902` and `1a2a752`, the same over-cap file (`provider_usage/store.rs`)** |

- **The ceiling design has one real violation.** cld counted 1 of 23; my 2 is the same violation counted twice, since
  the file stays over its cap until someone splits it. That file is exactly what a size gate should stop.
- **A 1,500 gate is too tight today.** `fleet_attention.rs` and `provider_usage/mod.rs` crossed 1,500 non-test lines in
  ordinary feature commits.
- **Why 2,000.** It is the default read window, so a file whose code fits in one read is the unit agents actually work
  with. Keep 1,500 as the prose target.
- **Lead addition:** also require *newly created* files to be ≤1,500 non-test lines, matching `AGENTS.md`. That added
  zero failures in the replay, and it stops a new file from being born at 1,999.
- **Grandfathered at HEAD:** `editor/frontmatter.rs` (2,439 non-test lines), `config/axe.rs` (2,264),
  `provider_usage/store.rs` (2,254) and `agent_ownership/planner.rs` (2,141). The largest test-only file is
  `bead_event_parity.rs` at 2,294 total lines.
- **Drop the 1,200 warning.** 80 files are already over 1,200, and agents ignore warnings in a passing gate. gem's
  "advisory only" is still noise. Report that band from a metrics command instead.
- **Limit of the replay.** A longer window is not representative. The 256 Rust commits since 09-06 show a 68–84%
  failure rate under *every* design, driven by the pre-split monolith `sase_core_py/src/lib.rs`. So re-run the replay
  on the first 50 or more post-land commits, and do not trust these percentages to more than their ordering.

### 2.3 Generated binding inventory: P2, generated rather than checked in

mus and gem want a syn-generated inventory, checked in and staleness-gated. gem's phase 3 would make sase's
`check_sase_core_rs_bindings` read the file. **That would weaken the one gate that exists for cross-repo skew.**

- **The checker probes the installed wheel, not the source.** Its docstring says it verifies that "the installed
  `sase_core_rs` exposes every binding sase requires" (`hasattr` on the imported module). CI runs it in the exact-floor
  venv (`publish.yml`, `install-smoke-core-floor`, which pins `sase-core-rs==${core_minimum}`). The gate was created
  after sase 0.11.0 shipped calling a binding the floor wheel lacked.
- **A source inventory describes the wrong thing.** It describes sase-core HEAD, not the published floor. The sase
  lists are consumer requirements checked against what is actually installed. Feeding them the supplier's list would
  make the check tautological (cld).
- **A checked-in inventory is a hub.** About 41% of sase-core feat/fix commits add a binding, and each would have to
  regenerate the same file on an unprotected, high-velocity master.
- **Grep already finds bindings.** `rg 'name = "<python name>"' crates/sase_core_py/src` works because the
  `#[pyo3(name)]` strings are literal. If a listing is wanted, add a `just bindings` recipe that is fresh by
  construction, like `just modules`.
- **The inventory's real consumer is `.pyi` typed access.** That is already a P2 item, and mus rightly warns that stubs
  help only after a typed accessor exists. Generate the inventory there, at build time.

### 2.4 Schema-version registry: right diagnosis, wrong design

mus and gem endorse the `WIRE_SCHEMA_VERSIONS` table plus one exporting binding (gem would keep the getters as
forwarders). The evidence favours cld's rework:

- **Python's copies are reader pins, not duplicates.** For example, `src/sase/artifact_ref_wire.py:63` rejects any
  payload whose version is not the constant it understands. If Python read the core's registry instead, a core bump
  would be accepted silently and then misparsed. The `sase-oq` failure ("probe requires 5: got 6") was this check
  working.
- **A hand table would be a hot hub.** The core has 124 `*_WIRE_SCHEMA_VERSION` constants plus 40 other
  schema-version constants, 164 in total. On 2026-08-24 there were 90. A table keyed on `*_WIRE_SCHEMA_VERSION` would
  also miss the other 40.
- **gem's figures are wrong.** There are **85** schema-version getter bindings, not 21. So there are 85 getters to
  retire, not a handful to forward.
- **The incidents were cross-repo floor skew** (`sase-km`, `sase-kx`, `sase-wg`, `sase-10d`). A core-side table does
  not reach them.

**What would actually help is sase-side.**

- Add a check that pairs each sase constant with its same-named core getter (`FOO_WIRE_SCHEMA_VERSION` ↔
  `foo_wire_schema_version()`). Run it in the dev validator and in the floor-smoke venv. **52 pairs** exist today, and
  the 79 same-named constants present in both repos all agree at source level.
- **Lead finding:** `tools/validate_sase_core_rs` also hardcodes about 20 literal expected versions (for example
  `!= 5`, `!= 9`, `{"vcs_log_wire_schema_version": 4}`). That is a *third* hand copy. The pairing check can replace
  those literals with sase's own constants, which removes a copy while keeping the pins.
- The owner cancelled `sase-km` ("one preventive gate"), so treat this as optional: a small sase task, done when
  convenient or on the next skew incident. It is not part of sase-core P1.

### 2.5 Module docs: keep the root rule, drop `MODULES.md`

- **The root rule.** All 114 top-level module roots already have a `//!` line, and the four modules added since P0
  arrived documented. Gate it (it starts green).
- **Why not every file.** gem is right that requiring `//!` on *every new file* would produce filler such as
  `//! Implementation of scanner`.
- **Why not `docs/MODULES.md`.** A committed copy duplicates `just modules`, adds a staleness gate, and becomes one more
  file that every new module must edit. "Grouped by layer" also depends on a layer table that does not exist yet.

### 2.6 Module-cycle ratchet: text-level, baseline-relative

All four analyses keep this check, because the new `agent_clan_record` cycle shows drift is already happening. mus
wanted a syn or cargo-metadata extractor with a warn-then-deny rollout. I side with cld and gem for three reasons:

- **Existing false positives are absorbed.** The baseline is computed by the same extractor, so any false edges in
  today's code are already in it.
- **Misses are cheap.** False negatives (missed edges) are acceptable in a ratchet.
- **syn would break the gate's design.** It needs a Rust tool compiled in the gate, which breaks the "fast, stdlib
  Python" precedent set by `check.sh features`.

cld's extractor reproduces the source report's graph within 2 edges and fired exactly once in the replay: the real
cycle. Replace warn-then-deny with two landing conditions: a history replay showing zero false positives, and fixture
tests for each extractor case (`crate::{…}` groups, root re-export mapping, the root forwarder). mus is right that an
*empty* allowlist is P2's exit, not P1's.

### 2.7 Root-prelude freeze: count names, include aliases, add a sunset

- **Count names, not blocks.** Freeze the number of root `pub use` **names** (2,677), not blocks. gem's proposed
  `grep -c 'pub use crate::'` counts the 107 blocks, and a name added to an existing block leaves that count unchanged.
- **Include the aliases.** Extend the freeze to the 657 `core_*` aliases in `sase_core_py/src/prelude.rs` (cld), which
  leaked in the same window.
- **Sunset it.** mus's sunset clause applies: when P2 deletes both layers, the check becomes "must be 0" or is deleted.

### 2.8 Smaller items (near-consensus)

- **Route ↔ contract test.** Keep it, at low priority. `routes/router.rs` has had one commit since 07-21. Write it as a
  behaviour test (cld): every `(method, path)` in the `api_v1` and `api_fleet_v1` contracts resolves through the real
  router, not 404 or 405. On failure, print the missing and extra routes (mus). The fixtures already exist
  (`routes/tests/support.rs`).
- **`*_parity.rs` → `*_golden.rs`.** Leave it out of P1. It touches 14 hot test files, conflicts with the in-flight
  `sase-17m` rename, and checks nothing. Do it in P2's root-import rewrite, which edits those files anyway.
- **syn "move items" tool.** Defer it to P2 phase 0. The plan itself makes it conditional, and building it before real
  move operations exist risks building the wrong tool (mus).
- **Flakes.** All four analyses agree: take them out of the epic. gem's ID mapping is wrong. The bead store says:

| Bead | Test | Size | Signal |
| --- | --- | --- | --- |
| `sase-15g` | Gateway fleet routes hit read/refresh deadlines under load | L | **+4 corroborations** (`sase-16h`, `170`, `16z`, `17m.2.1` land agents) |
| `sase-15h` | `sudo_runner`: fake sudo exec fails with ETXTBSY | M | Likely a shared fixture-lifecycle cluster with 15e and 15f |
| `sase-15e` | `sudo_runner`: empty `worker.pid` | S | |
| `sase-15f` | `sudo_runner`: cwd left behind under load | L | |
| `sase-15d` | Telemetry concurrent writers | L | |
| `sase-17n` | `tool_run` store `private_argv_is_not_serialized_on_queries` | L | New today |

All six are `ready` and waiting on their TaskTriage gates. mus's "quarantine first" is not needed while the triage
path is open. Revisit it only if `15g` keeps hitting land agents.

---

## 3. Errata in the inputs

| Claim | Source | Finding |
| --- | --- | --- |
| A missing registration is invisible to the compiler | mus, gem, source §4.3, `AGENTS.md` step 4 | **Wrong** for all but 5 of the ~839 bindings (§2.1) |
| 21 schema getters | gem | **85** |
| ~37 files over 1,500 lines | mus | **44** (cld and gem agree) |
| `sase-15h` is the gateway flake; `15e/f/g` are `sudo_runner` | gem | **`15g` is the gateway flake; `15e`, `15f` and `15h` are `sudo_runner`** |
| Freeze by `grep -c 'pub use crate::'` ≤ 107 | gem | Counts blocks and misses names added to existing blocks. Count names (2,677) |
| Per-check runtime table (~225 ms total) | gem | Estimated, not measured. cld's prototype measured 0.21 s for size, docs and counters, plus about 0.1 s for the graph |
| Sase's hand lists should consume a generated inventory | source P1 row, mus, gem | That would replace an installed-wheel probe with a source description (§2.3) |
| "Python reads the registry instead of its copies" | source P1 row | It would remove reader pins (§2.4) |
| cld's ceiling design fails 1 of 23 commits | cld | My replay fails two commits, both on the same over-cap file. Consistent with cld's conclusion |

---

## 4. Recommended solution

**Implement P1, trimmed and redesigned as follows. Do not adopt it verbatim.**

### Now, independent of any epic

1. **Correct `AGENTS.md` recipe step 4.** It should say that clippy's `dead_code` lint fails `just check` when a
   binding is unregistered, unless other non-test code also calls it. This is a one-line docs fix.
2. **Launch the flakes as tasks from their TaskTriage gates.** Start with `sase-15g`. Then take the `sudo_runner`
   cluster (`15h`, `15e`, `15f`) as one investigation first, then `15d` and `17n`. Use this KPI: *no sase-core flake
   bead corroborated in the last 14 days*, not "0 open".

### Epic: sase-core structure gate (2 phases, or one medium task)

**Phase 1: `structure-gate` (medium).** Add `./scripts/check.sh structure`, backed by a stdlib Python script with
fixture unit tests (next to `script-test`) and a baseline file computed **at land time**, because `sase-17m` is still
moving names. Run it first in `cmd_all` and as its own CI step.

| Check | Rule |
| --- | --- |
| Size | Non-test lines are those before the first `#[cfg(test)] mod`. Source files are capped at 2,000 non-test lines, and new files at 1,500. Grandfathered files are capped at their land-time size rounded up to the next 250. Test-only files are capped at 3,000 total lines. No warning tier |
| Module cycles | The multi-module SCCs among top-level `sase_core` modules must be a subset of the baseline, and no SCC may gain members. The root forwarder counts as an edge |
| Hub freeze | The root `pub use` name count and the `core_*` alias count may not exceed the baseline. Sunset: in P2 this becomes "= 0" |
| Module-root docs | Every top-level `sase_core` module root starts with a `//!` line |
| Binding-lint soundness (lead addition) | No `pub fn` `#[pyfunction]` and no `allow(dead_code)` in `sase_core_py`. This keeps the compiler's registration check sound |

- **Rules for the gate.**
  - Every failure message names the fix. For example: "`provider_usage/store.rs` has 2,254 non-test lines (limit
    2,000); move a cohesive group into a sibling module, see `AGENTS.md` 'Split a file'".
  - No check may require a shared, append-mostly file that ordinary feature commits must edit.
  - Nobody is ever *required* to lower a baseline.
- **`AGENTS.md` updates:** add a three-line "Split a file" recipe, list the new gate in the `just check` steps, and
  state that the size rule counts non-test lines.
- **Exit criteria:**
  - The gate passes at land.
  - Every rule has a fixture test.
  - A replay over all post-`8886406` Rust commits (50 or more by then) shows structural failures (size or cycle) in
    no more than about 10% of commits, each for a real reason, and zero cycle false positives.

**Phase 2: `route-contract-and-cycle` (small).**

- Add the gateway behaviour test: every contract `(method, path)` resolves through the real router.
- Fold `agent_clan_record` into `agent_scan` (as `agent_scan::clan_record`) and lower the cycle baseline to the
  original six SCCs.
- Schedule this move after `sase-17m`'s sase-core phases land. Both edit `agent_scan`, and the phase-1 baseline
  tolerates the 3-module SCC in the meantime.

### Optional, sase-side (separate small task)

Add the schema-skew pairing check (§2.4):

- It compares 52 constant ↔ getter pairs in the dev validator and in the floor-smoke venv.
- It replaces the validator's ~20 literal expected versions with sase's own constants.
- Keep the constants: they are the reader's contract.
- Do it when convenient, or on the next skew incident, consistent with the `sase-km` triage.

### Move to P2

- The binding inventory and `.pyi` stubs, generated at build time and never checked in.
- The syn "move items" tool, as phase 0.
- The `*_parity.rs` rename, folded into the root-import rewrite.

### Drop

- The registration-completeness gate.
- The committed `docs/MODULES.md`.
- The 1,200-line warning.
- The hand-kept `WIRE_SCHEMA_VERSIONS` table.
- "Python reads the registry instead of its copies".
- sase consuming a source-generated binding list.

### Sequencing

- **The structure gate can start now.** It adds new files and one CI line, so it barely conflicts with `sase-17m`.
- **P2 should wait for both** the gate and `sase-17m`. The freeze counters and the cycle baseline are what keep P2's
  target from moving, which is why "guardrails before restructuring" still holds for the trimmed P1.
- **Update the source report's KPI rows.**
  - Replace "Open sase-core load flakes: 0 (P1)" with the 14-day corroboration KPI.
  - Replace "Hand-kept lists without a drift test: 0 (P1)" with a count that treats the compiler-checked registration
    lists and sase's reader pins as intentional.

### Expected effect

| KPI | Today | After the trimmed P1 |
| --- | --- | --- |
| Commits that grow a file past the reading unit | +348 non-test lines to 2,254 in one commit | Blocked at 2,000 non-test lines (and 1,500 for new files) |
| New module cycles | +1 in 3 days | Blocked |
| Root names and `core_*` aliases added after the prose rule | +3 and +3 | 0 |
| Agents told "the compiler doesn't check registration" | Yes, in `AGENTS.md` | Corrected |
| New shared hubs created by P1 | 3 in the plan as written (inventory, schema table, `MODULES.md`) | 0 |
| Friction | 74% of commits under the rule as written | About 9% structural failures in the replay, each real, plus a few import-path freeze fixes |
| sase-core flakes corroborated in the last 14 days | 6 open; `15g` +4 | Target 0 |

---

## 5. Method and limits

- **The three reports** were read through `sase artifact read`. Their registered snapshots match the moved copies byte
  for byte (sha256).
- **Compiler experiment.** It ran on a `git archive` copy of `eef7ca4` with a separate `CARGO_TARGET_DIR`, using
  `./scripts/check.sh check -p sase_core_py`. The first build took 1 min 53 s and the rebuild 3 s. The linked sase-core
  checkout was not modified.
- **Size replay.** A Python script ran over `git rev-list --no-merges 8886406..eef7ca4 -- 'crates/**/*.rs'`, comparing
  each commit with its parent and checking against a fixed baseline for the ceiling rules. It is only three days of
  post-split history, so the ordering between designs is robust but the exact rates are not.
- **Static counts** were taken at `eef7ca4`: bindings, getters, escape hatches, schema constants, prelude names and
  aliases, and file sizes. sase-side schema pairing was checked at sase `329d4049b`.
- **Beads** were read with an audited `sase bead read`: `sase-15d`–`15h`, `sase-17n`, `sase-165`, `sase-17m` and
  `sase-17m.10`.
- **Not verified:**
  - I did not re-run the module-cycle replay; I accepted cld's result and verified the new cycle's edges by hand.
  - The runtime of the route behaviour test.
  - Whether the three `sudo_runner` flakes share one root cause.
