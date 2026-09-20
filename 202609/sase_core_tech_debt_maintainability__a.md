# sase-core technical debt & maintainability research (researcher A)

Scope: the `sase-core` linked repo (workspace root `repos/linked/sase-core`),
as cloned in workspace `sase_12`. Goal: identify the maintainability changes
with the most impact for human and agent maintainers. All counts below were
taken directly from that checkout (git HEAD `9a5c568`); commands used are
recorded in each section so findings can be re-checked.

## Method

- Counted files/lines (`find crates -name '*.rs'`, `wc -l`), lint
  suppressions (`allow(`), error-type patterns (`Result<_, String>`),
  `unwrap`/`clone`/`expect` loads, `wire_schema_version` sprawl, churn
  (`git log --name-only`), and doc drift (README vs tree).
- Read `AGENTS.md`, `Cargo.toml`, `justfile`, `scripts/check.sh`,
  `.github/workflows/ci.yml`, `release-plz.toml`, and the heads of the
  largest files. Did not run the full test suite (slow); no code changed.
- Did not consult the parallel `__b` report.

## Inventory (baseline numbers)

- **381** `.rs` files, **~376k** total lines across 4 workspace crates:
  `sase_core`, `sase_core_py`, `sase_gateway`, `sase_xprompt_lsp`.
- `sase_core/src/lib.rs`: **112** `pub mod` declarations, flat, no facades.
- `#[test]` count workspace-wide: **3802**.
- Velocity: **933 commits / 90 days**, **430 / 30 days**, single author.
  Churn leaders (last 200 commits): `sase_core_py/src/lib.rs` (79),
  `Cargo.toml`/`Cargo.lock` (67/66, release-plz churn), `sase_core/src/lib.rs`
  (53).
- Verification story is good: `scripts/check.sh all` (fmt-check + clippy
  `-D warnings` + workspace tests + `.github/scripts` unittests) is the
  single gate local and CI share, and `AGENTS.md` records real lessons
  (e.g. never verify with `cargo test -p sase_core` alone after `a509dcc`).

## Findings, ordered by expected impact

### 1. `sase_core_py/src/lib.rs` is a 35k-line single-file binding monolith
- **35,166 lines**, one file; ~**1323** `fn` items, **1681**
  `pyfunction|pymethods|pyclass` markers, **849** `m.add_function` calls,
  but only **2** `pyclass`es — the boundary is ~850 dict-in/dict-out
  functions over `serde_json::Value` (76 mentions).
- Touched in **79 of the last 200 commits**: nearly every feature pays the
  merge-conflict + recompile + review cost of this file.
- Human cost: unreviewable diffs, no ownership boundaries. Agent cost: the
  file can never fit in context; agents resort to blind appends, which is
  exactly how god files grow.
- **Recommendation (highest impact):** split into per-domain modules
  (`bindings/bead.rs`, `bindings/agent_scan.rs`, …) plus shared
  `convert.rs` (JSON<->Python helpers), with the `#[pymodule]` init kept
  as a thin registry. Pure move + re-export; behavior-neutral. Consider a
  generated `BINDINGS.md` index (function -> domain module) so agents can
  locate targets without grepping 35k lines.

### 2. God modules in `sase_core`
Largest files (`wc -l`): `agent_scan/index.rs` 13,468; `bead/mutation.rs`
11,316 (production ~3,800 + **~7,500 lines of inline `mod tests`** starting
at line 3816); `fleet_contract.rs` 10,548; `agent_launch/mod.rs` 7,978;
`editor/completion.rs` 7,260; `xprompt_catalog.rs` 4,850;
`gateway/sudo_runner.rs` 4,595. `bead/` alone totals **30,629** lines.
- 112 flat `pub mod`s in `lib.rs` means no documented domain map; related
  modules (`fleet_*`, `agent_*`, `artifact_*`) are siblings with no facade.
- **Recommendations:** (a) split the top 5 files by subdomain;
  (b) move giant inline test modules to `tests/` where they are
  integration-style (keeps production files reviewable); (c) add 2–3 facade
  modules or at least a module map in `lib.rs` docs.

### 3. `sase_gateway/src/routes.rs` (10k lines) mixes routing, handlers, tests
- 10,062 lines, 107 top-level fns, ~45 async handlers plus inline tests
  (~6k lines from ~line 3901 on); **354 `.clone()`s**, the workspace high.
  Siblings `federation_worker.rs` (3,953), `fleet_reads.rs` (3,371),
  `sudo_runner.rs` (4,595) are large but coherent; `contract.rs` (1,840) +
  `wire.rs` (1,909) + checked-in `contracts/*.json` snapshots form a triple
  source of truth for the API contract.
- **Recommendations:** split `routes.rs` per resource
  (`routes/fleet.rs`, `routes/agents.rs`, `routes/notifications.rs`, …) with
  handlers next to their stores; verify the contract JSON is snapshot-tested
  (if not, add the test — cheap, high value); audit the 354 clones, many of
  which look like handler-argument duplication.

### 4. Wire-schema-version sprawl: 79 version functions, 126 consts
- `grep wire_schema_version`: 380 hits, 79 `fn …_wire_schema_version`,
  126 `pub const …WIRE_SCHEMA_VERSION`. Every domain carries its own
  version plus a dedicated PyO3 getter — versioning tax on every port.
- **Recommendation:** a central `VERSIONS.md` registry (domain, version,
  what bumps it, last bump commit) plus a test asserting versions change
  only with an explicit opt-in (e.g. a registry file diff), so bumps are
  deliberate, not accidental. This is process debt more than code debt.

### 5. Stringly-typed error and JSON boundaries
- **545** `Result<…, String>` sites; `agent_scan/index.rs` alone has 114,
  `sase_core_py` 102, `telemetry/store.rs` 51. `thiserror` is already the
  house standard (126 derive sites) but adoption is uneven.
- The Python boundary passes `serde_json::Value` dicts; only 2 typed
  `pyclass`es exist. Each binding re-implements conversion + string errors.
- **Recommendations:** convert the worst `Result<_, String>` files to
  `thiserror` enums (start with `agent_scan/index`, `telemetry/store`,
  `agent_group_archive`); introduce typed PyO3 classes for the hottest
  paths while keeping dict wire at the edges; share one `pyerr.rs` helper
  (today each domain maps errors ad hoc).

### 6. `too_many_arguments` suppressions signal missing parameter objects
- ~50 `#[allow(…)]` sites; **30+ are `clippy::too_many_arguments`**
  (14 in `lib.rs` alone, 5 in `bead/mutation.rs`, plus ones in
  `agent_hold`, `agent_stats/run`, `query/profile`, `tool_run/store`,
  `plan/search`, `xprompt_catalog`, …). There is no workspace `[lints]`
  table; only default clippy with `-D warnings`.
- **Recommendations:** add `[workspace.lints]` (or per-crate `[lints]`)
  and turn on a small set of style lints (`pedantic` subset or at least
  `too_many_arguments`, `unwrap_used` as warn); replace the worst
  offender signatures with the existing `*Wire` request types as parameter
  objects instead of suppressing.

### 7. `unwrap` / `clone` load concentrates in production files
- 10,776 `.unwrap()`s total; ~**5,900 in non-test source**. File highs:
  `sase_core_py/lib.rs` 2,328, `bead/mutation.rs` 923,
  `agent_scan/index.rs` 548, `server.rs` 312, `routes.rs` 297.
  4,465 `.clone()`s; 261 `panic!/unimplemented!/todo!`s.
- Some unwraps are in tests, but production files dominate the list, so a
  panic-hygiene pass is warranted rather than assuming tests explain it.
- **Recommendation:** scoped pass over the top-5 files: replace
  production `unwrap()` with typed errors (ties into finding 5),
  `expect()` with context only at genuine invariants, and audit clones in
  `routes.rs` / `bead/mutation.rs` / `fleet_contract.rs` for `&str`/`Cow`
  or restructured ownership.

### 8. Test strategy works but carries dual-maintenance cost
- 3,802 tests; `AGENTS.md` + `check.sh` discipline is a genuine strength
  (parity-test lesson from `a509dcc` is written down, not tribal).
- Costs: (a) Python-parity fixtures embed Python output as strings so the
  crate builds without Python — correct choice, but fixtures rot silently
  (that was `a509dcc`); (b) giant inline test modules (mutation.rs ~7.5k
  lines) bloat the files agents must read; (c) no documented
  fast-vs-slow split — 3.8k tests through one `cargo test --workspace`
  will get slower, and agents will start skipping it.
- **Recommendations:** keep `check.sh` as the single gate; add a
  documented fast subset for iteration; move integration-style inline tests
  out of production files; add fixture-freshness CI (regenerate-or-verify
  job) for the parity fixtures.

### 9. Store/lock and fleet-read patterns are copy-pasted
- ~18 `store.rs` files match `rusqlite|StoreLock|store_lock`
  (`prompt_stash`, `procs`, `tool_run`, `telemetry`, `bead/*`,
  `agent_archive`, `feature_flag_state`, …). Fleet logic is split across
  `sase_core::fleet_*` and `sase_gateway::fleet_*` with a one-function
  bridge (`fleet_reads::resync_item`) that hints at an unclear seam.
  `sase_core_py` also depends on `sase_gateway` types
  (`fleet_store_error_to_pyerr`), blurring the pure-core/gateway boundary
  the README claims.
- **Recommendations:** extract a shared `store` helper (open/lock/txn
  boilerplate) used by all stores; draw the fleet seam explicitly
  (core owns facts/catalog math, gateway owns HTTP/auth) and shrink the
  `py -> gateway` dependency to re-exported wire types only.

### 10. Docs drift (cheap fixes, do first)
- `README.md` still says `sase_100` (repo renamed to `sase`), omits the
  4th crate (`sase_xprompt_lsp`) from Layout, and teaches raw
  `cargo fmt/test/clippy` invocations while `AGENTS.md` mandates
  `scripts/check.sh`. Only doc outside README is `docs/pypi-retention.md`
  (good). `routes.rs` (10k lines) has ~20 `///` comments.
- **Recommendations:** one small PR: rename references, fix Layout,
  point all commands at `check.sh`, add `ARCHITECTURE.md` (crate map +
  fleet seam + versioning policy), require rustdoc on new public items.

### 11. Release machinery is complex but justified — prune, don't rebuild
- History shows why it exists: 272 releases in 63 days at ~75 MB each
  filled the 10 GB PyPI quota → daily cadence, completeness gate, quota
  pre-check, retention tool + runbook. `.github/scripts` is 2,266 lines of
  Python with its own unittest suite (already gated in `check.sh`).
  Five `allow(clippy::incompatible_msrv)` sites hint at toolchain/MSRV
  friction (workspace `rust-version = 1.78`, `abi3-py312` needs modern
  Python).
- **Recommendation:** leave the design alone; schedule the existing
  retention pruning, keep the cadence test, revisit MSRV only if it blocks
  a needed dependency.

## Recommended change set (priority order)

Highest impact per unit effort, biased toward what helps agents too
(small files, explicit seams, machine-checkable invariants):

1. **Split `sase_core_py/src/lib.rs` into per-domain binding modules**
   (finding 1). Single biggest win for compile, review, conflicts, agents.
2. **Split `routes.rs` per resource; snapshot-test the contract JSON**
   (finding 3).
3. **Parameter objects + workspace `[lints]`** to retire most
   `too_many_arguments` suppressions (finding 6). Mechanical, wide benefit.
4. **Typed errors for the top `Result<_, String>` files** + production
   `unwrap` pass in the top-5 files (findings 5, 7). Do together; same
   files.
5. **Central wire-version registry + bump test** (finding 4). Small,
   prevents silent compat breaks.
6. **Move giant inline tests to `tests/`, document a fast test subset,
   add parity-fixture freshness check** (finding 8).
7. **Shared store/lock helper; clarify core/gateway fleet seam**
   (finding 9).
8. **Docs PR: README fixes + `ARCHITECTURE.md`** (finding 10). Do first
   chronologically — it is a half-day and unblocks the rest.
9. **Break up `agent_scan/index.rs`, `fleet_contract.rs`,
   `editor/completion.rs`, `xprompt_catalog.rs`** (finding 2). Largest
   remaining grind; sequence after the binding split establishes the
   pattern.
10. **Leave release machinery as-is; run retention pruning** (finding 11).

Explicitly out of scope: migrating the Python product shell, changing the
release cadence, or adopting UniFFI/WASM now — the pure-core/gateway split
already preserves those options.

## Risks / caveats

- Counts are syntactic (`grep`/`wc`), not semantic: `unwrap` totals include
  some test code, and function-length estimates are approximate where
  `mod tests` blocks sit between top-level fns. File-level rankings are
  robust; exact per-function numbers are not.
- Single-author, 400+ commits/month velocity means any restructure must be
  mechanical (moves + re-exports) and land quickly, or it will conflict
  with in-flight work. The binding split and routes split both qualify.
- I did not run `just check` (full workspace tests) to keep this
  read-only; the recommended changes each need a green `check.sh` run.
