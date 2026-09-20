# sase-core: Technical Debt & Maintainability — Consolidated Audit

**Date:** 2026-09-20 · **Repo:** `sase-org/sase-core` @ `9a5c568` (master, clean) ·
**Version:** `0.34.70` · **Measured on:** macOS (Darwin 25.5.0), Apple Silicon

Consolidates two independent researcher reports ([`__a`](./sase_core_maintainability_audit__a.md),
[`__b`](./sase_core_maintainability_audit__b.md)) with a third verification pass by the lead
researcher. Every number below was re-measured in a fresh checkout; where the source reports
disagreed or were wrong, §7 records the adjudication.

---

## 1. Headline

This is **not a rotting codebase**. Clippy is clean at `-D warnings`, there is one TODO marker
in 376k lines, the warm test suite is fast, and `scripts/check.sh` is a genuinely good
single-gate pattern. The debt is narrow and deep, concentrated in five places:

1. **A live data-loss bug** — the `/tmp` reap guard is inert on macOS, and a unit test triggers a
   real, destructive reap of `/private/tmp` on every `cargo test --workspace` run.
2. **CI is Linux-only**, so 22 tests that fail on the machine the project is actually developed
   on are invisible — including a production portability defect in the privileged-execution path.
3. **The edit cycle is slow for the wrong reason.** `sase_core` is a single 292k-line crate;
   touching any leaf in it costs a **5m46s** workspace rebuild. This is the largest recurring tax
   on both humans and agents, and **neither source report found it**.
4. **Two hub files funnel ~81% of feature commits**, which for parallel agents is close to a hard
   serialization constraint.
5. **The docs actively contradict the architecture**, and docs are what an agent reads first.

**If you do three things:** fix the reap guard (§3.1), add macOS to CI (§3.2), and adopt
`cargo check` as the inner loop (§3.3). All three are hours, not weeks.

---

## 2. The repo at a glance (verified)

| Measure | Value |
|---|---|
| Crates | 4 — `sase_core`, `sase_core_py`, `sase_gateway`, `sase_xprompt_lsp` |
| Rust files / total lines | 381 / 376,405 |
| Production lines / inline `#[cfg(test)]` lines | 253,688 / 123,098 (32.7% test) |
| Lines per crate | core **292,391** · py 35,166 · gateway 31,823 · lsp 17,025 |
| `#[test]` functions | 3,802 (4,049 executed) |
| Test result on macOS | **4,027 pass / 22 fail / 2 ignored** |
| Python API surface | **822** `#[pyfunction]`s, 849 `add_function` calls, **0** `.pyi` stubs |
| `sase_core` root re-exports | **2,672** (only **416** consumed via the root path) |
| `sase_core` public items documented | 1,220 / 3,486 (**34%**) |
| Prose docs | 982 lines across 5 files; `docs/` holds exactly 1 file; `AGENTS.md` is 21 lines |
| Commits since 2026-04-28 | 1,250 (296 are `chore: release`), single author |
| `#[allow(...)]` sites | **54** — 42 `too_many_arguments`, 8 `incompatible_msrv` |
| `[lints]` tables / `clippy.toml` / `deny.toml` / `.cargo/config.toml` | **none** |
| Duplicate-version packages in `Cargo.lock` | 21 of 275 |
| `TODO`/`FIXME`/`HACK` | 1 (a fixture string) |

**Edit-cycle cost (newly measured, warm target dir):**

| Edit | Rebuild cost |
|---|---|
| One leaf module in `sase_core` → `cargo build --workspace` | **5m 46s** |
| Same edit → `cargo check --workspace` | **45s** |
| `sase_core_py/src/lib.rs` (the 35k-line monolith) → `cargo build -p sase_core_py` | **12s** |
| One leaf in `sase_gateway` → `cargo build --workspace` | **31s** |
| Cold `cargo build --workspace` + full test run | ~20 min wall |

---

## 3. Findings, ranked

### 3.1 CRITICAL — the `/tmp` reap guard is inert on macOS, and a test performs a live reap

`crates/sase_core/src/managed_tmp.rs:901`:

```rust
let resolved = root.canonicalize().unwrap_or_else(|_| root.to_path_buf());
...
for unsafe_root in [Path::new("/"), Path::new("/tmp"), Path::new("/var/tmp")] {
    if resolved == unsafe_root { return Err(ManagedTmpReapError::UnsafeRoot(...)); }
}
```

The root is **canonicalized**, then compared against a **non-canonicalized** denylist. On macOS
`/tmp` → `/private/tmp` and `/var` → `/private/var`, so **no denylist entry can ever match**.
The module doc promises it "refuses broad roots"; on macOS it refuses nothing. The secondary
`resolved == cwd || cwd.starts_with(&resolved)` guard does not fire either, because a dev's cwd
is not under `/private/tmp`.

The test that exists to catch this — `broad_cleanup_roots_are_rejected` (`managed_tmp.rs:1810`)
— passes `root = "/tmp"` through the shared `request()` helper, which sets **`apply: true`**,
**`max_removals: 2000`** and `default_horizon_seconds: 3 days`. On Linux the guard fires and
nothing happens. On macOS the guard is skipped and the test **executes a real reap of
`/private/tmp`**. Researcher B reproduced this twice; it deleted a live tool-session scratch
directory mid-investigation:

```
removed: 4, removed_directories: ["/private/tmp/claude-503/-Users-bbugyi-...-sase_11"]
```

**Calibrating the blast radius honestly.** `reap_managed_tmpdir` *is* exported to Python with a
caller-supplied `root` (`sase_core_py/src/lib.rs:2276`), and `validate_reap_root` is the only
defense. But all three production callers in the `sase` repo —
`scripts/sase_chop_managed_tmp_reap.py`, `core/disk_footprint_reap_managed_tmp.py`,
`axe/run_agent_runner_scratch.py` — pass `managed_tmpdir_root()`, a dedicated directory. So the
**realized** harm today is "every macOS `cargo test --workspace` destroys up to 2,000 entries
under `/private/tmp`", and the **latent** harm is an unguarded public API. Both warrant the fix;
neither is "production is deleting `/tmp` right now."

**Fix (~5 lines).** Canonicalize the denylist before comparing, and add `/private/tmp`,
`/private/var/tmp`, `$TMPDIR` and `$HOME`. Separately, change the test to assert with
`apply: false` so a future guard regression cannot delete anything, and add `/private/tmp` and
`$TMPDIR` cases.

> **Until this lands, anyone running the suite on macOS should use**
> `cargo test --workspace -- --skip broad_cleanup_roots_are_rejected`.

### 3.2 HIGH — CI is Linux-only; 22 tests fail on the development platform

All three jobs in `.github/workflows/ci.yml` are `runs-on: ubuntu-latest`, while
`sase_core_py/pyproject.toml` advertises macOS and Windows support on PyPI. Verified on clean
master, macOS: **4,027 pass, 22 fail**.

| Failures | Crate | Cause |
|---|---|---|
| **19** | `sase_gateway::sudo_runner` | Linux-only procfs in **production** code |
| **2** | `sase_xprompt_lsp::server` | `Option::unwrap()` on `None` at `server.rs:5774`, `:5861` |
| **1** | `sase_core::managed_tmp` | §3.1 |

The sudo_runner cluster is a **production portability defect, not a test defect**.
`sudo_runner.rs:1632` gates `process_identity_token` with `#[cfg(unix)]` but the body reads
`/proc/sys/kernel/random/boot_id` and `/proc/{pid}/stat`. macOS *is* `unix` and has no `/proc`,
so the anti-spoofing identity token — and the whole privileged-execution path — fails with
`RunnerError` on macOS. The `sase_sudo_runner` console script **is** installed by the macOS
wheel, and CI's `wheel-smoke` job only asserts `--help` runs.

The workspace gets this right elsewhere: `sase_core/src/host_liveness.rs:325` reads `/proc/{pid}`
under `#[cfg(target_os = "linux")]` with a non-Linux fallback. The ratio is **131 `#[cfg(unix)]`
vs 6 `#[cfg(target_os = "linux")]`**, so the gate is worth a targeted audit — grep for `/proc/`
inside `cfg(unix)` blocks. (Only `sudo_runner.rs` is currently mis-gated; `fleet_family.rs` and
`contract.rs` mention `/proc` as data, not filesystem reads.)

Adding `macos-latest` to the `rust-checks` matrix is one line and permanently closes the
"green in CI, red on the dev machine" gap. You then choose: implement a macOS
`process_identity_token` (`sysctl` `kinfo_proc` for start time, `kern.boottime` for the boot
substitute), or explicitly gate `sase_sudo_runner` off on macOS and stop advertising it. Either
is defensible; silently shipping a broken console script is not.

### 3.3 HIGH — the edit cycle is dominated by `sase_core` being one 292k-line crate

**This is the finding neither source report made, and it reorders the priority list.**

Rust's compilation unit is the crate. `sase_core` is **292,391 lines in one crate** with 107
flat `pub mod`s, and `sase_gateway`, `sase_core_py` and `sase_xprompt_lsp` all depend on it. So:

- Touch **any** leaf module in `sase_core` → **5m 46s** full workspace rebuild.
- Touch a leaf in `sase_gateway` (a leaf crate) → **31s**.
- Touch the 35k-line `sase_core_py/src/lib.rs` → **12s**.

Report A implied the binding monolith carries the recompile cost. It does not — at 12s
incremental it is one of the *cheapest* files in the repo to edit. The 5m46s cascade belongs to
`sase_core`, and 140 of the last 300 commits touch `sase_core/src/lib.rs` alone, every one of
them paying it.

**Two levers, in cost order:**

1. **Free, today: make `cargo check` the inner loop.** The same edit costs **45s** under
   `cargo check --workspace` — a **7.7× speedup** with zero refactoring. There is no `check`-only
   fast target in the `justfile` (its `check` recipe runs the full gate) and no
   `.cargo/config.toml`. Add `just fast` → `cargo check --workspace --all-targets`, document it
   in `AGENTS.md`, and keep `just check` as the pre-commit gate. There is also no
   `[profile.dev]` section; `debug = "line-tables-only"` typically buys another meaningful cut on
   macOS link time.
2. **Expensive, later: split `sase_core` into a few crates.** The natural seams already exist in
   the tree (`bead/` at ~30.6k lines, `agent_scan/`, `editor/`, `query/`, `artifact_*`,
   `fleet_*`). This is the only change that converts a 5m46s cascade into a 30s one for most
   edits. Treat it as a standing direction, not a next-sprint project — and note it composes
   with the Rust-core boundary rule the `sase` repo already follows.

### 3.4 HIGH — two hub files funnel ~81% of feature commits

`crates/sase_core_py/src/lib.rs` is **35,166 lines (1.3 MB) in one file**, modified by
**184 of the last 300 commits**. `crates/sase_core/src/lib.rs` (1,627 lines) was modified by
**140**. Nothing else comes within a factor of four. Over the last 100 `feat` commits
(reproduced exactly):

- **50%** touched **both** hub files
- **81%** touched at least one
- only **19%** touched neither

Adding one Python binding requires edits in **four regions of the same file**, plus a fifth in
`sase_core/src/lib.rs`:

| Region | Lines | Contents |
|---|---|---|
| `//!` API manifest | 1–663 | hand-written list of exposed functions |
| `use` block | 683–1,761 | 103 `use sase_core::<mod>::{... as core_...}` statements |
| Function bodies | ~1,770–19,925 | 822 `#[pyfunction]`s, median body 13 lines |
| `#[pymodule]` registration | 19,929–21,280 | **1,352 lines** of `m.add_function(...)` |

For humans this is annoying. For **parallel agents it is near-serializing**: two agents adding
unrelated features have roughly even odds of colliding in a 35k-line file, and the collision
lands in a 1,352-line append-only list where a naive merge silently produces a duplicate or
dropped registration that surfaces only as a missing Python symbol at runtime. The file also
cannot fit in an agent's context, which pushes agents toward blind appends — exactly how god
files grow.

The bindings are highly compressible: **522 of 822 bodies are ≤15 lines**, **74** are pure
`*_wire_schema_version()` constant getters, and the dominant shape is
`dict → serde_json → core call → json out` with `PyValueError::new_err(e.to_string())`
(**557 occurrences**).

**The repo already knows how to fix this.** `sase_core/src/artifact_file/` is a 727-line module
file plus five submodules, none over 806 lines; `editor/` (18 files), `bead/` (14),
`artifact_ref/` (14) and `query/` (11) follow the same pattern. **The monoliths are the
deviation, not the house style.**

Target shape:

```
crates/sase_core_py/src/
  lib.rs              # <200 lines: mod decls + #[pymodule] calling ~40 registrars
  convert.rs          # py_to_json_value / json_value_to_py / error mapping
  bindings/
    agent_scan.rs     # own `use` block, own fns, own `pub fn register(m) -> PyResult<()>`
    bead.rs
    fleet.rs
    ...
```

Two design points make or break it: **each submodule owns its own `register(m)`**, so the
append-only registration list disappears and new bindings stop colliding; and **collapse the
mechanical shapes with `macro_rules!`**, starting with the 74 version getters and the
`dict → serde → core → json` body. Land it **one domain per PR** — mechanical moves, no behavior
change, verified by `./scripts/check.sh` and the existing `wheel-smoke` job.

Do this for merge-conflict, reviewability and agent-context reasons. Do **not** justify it on
compile time — see §3.3.

### 3.5 MEDIUM–HIGH — the root prelude is 84% redundant

`sase_core/src/lib.rs` declares 107 `pub mod`s and re-exports **2,672 symbols** flat via 107
`pub use` statements. Measured precisely:

- Only **416 (16%)** are ever consumed through the root path (`sase_core::Name`, `crate::Name`,
  or a root-brace `use`).
- **2,256 (84%)** are never used via the root path — including **1,015 `*Wire` types** and
  **110 `*_SCHEMA_VERSION` constants**. Each is already reachable at its module path, so the
  prelude is pure duplication of the public API surface.
- Only **60 (2%)** are genuinely referenced nowhere in the workspace at all.

The migration is small and bounded, because consumers have already voted:

| Consumer | Module-path refs | Root-path refs |
|---|---|---|
| `sase_core_py` | 95 | **1** |
| `sase_gateway` | 53 | **185** |
| `sase_xprompt_lsp` | 3 | **27** |

The binding crate already imports by module path almost exclusively. Delete the 2,256 redundant
re-exports and migrate gateway + LSP's 212 root-path references to module paths. Every step is
compiler-verified. This removes the second hub file, eliminates the "two names for every symbol"
ambiguity, and — as a bonus — cuts the 140-commit churn on the file that triggers the 5m46s
cascade. If a prelude is still wanted, scope it to a `pub mod prelude` with a documented,
deliberately small membership rule.

### 3.6 MEDIUM — three hand-maintained manifests have already drifted

A recurring pattern: a generated-*looking* artifact that is actually typed by hand, with no test
asserting it matches reality.

**(a) The `//!` API manifest — 23% drifted, verified exactly.** Lines 1–663 of
`sase_core_py/src/lib.rs` document **631 of 822** registered functions. **191 are missing**
(`admission_unit_results`, `artifact_link_cutover_*`, `agent_unit_dispatch_prompt`, …), and
**0 are stale in the other direction** — the list is append-mostly and people forget the append.
663 lines of prose maintaining a fact the compiler already knows.

**(b) No type stubs for an 822-function Python module.** `sase_core_rs` ships **zero `.pyi`
files**. Every Python consumer — and every agent writing Python against this API — gets no
signatures, no parameter names, no return types, no completion. Given the Python side is the
*only* real consumer, this is the highest leverage-per-hour item in the report.

(a) and (b) are the same fix: **delete the manifest, generate a `.pyi` from the `#[pyfunction]`
signatures, and gate it in CI so it cannot drift.** That converts the repo's largest
documentation liability into its most useful artifact.

**(c) The gateway contract snapshot is unverified.** `sase_gateway/src/contract.rs` holds two
hand-written JSON snapshot builders (931 and 776 lines). `routes.rs` registers **38 distinct
routes**; `contract.rs` mentions **29 `/api/v1...` paths**. No test asserts they agree. The gap
may be legitimate (some routes are unversioned) but nothing enforces it either way. Add a drift
test asserting every registered route appears in the snapshot, with a documented allowlist.

**(d) Cross-repo parity fixtures maintained by comment.** Five integration tests
(`agent_scan_parity.rs`, `git_query_parity.rs`, `vcs_log_parity.rs`, `golden_corpus_parity.rs`,
`config_parity.rs`) carry instructions like *"byte-for-byte equivalent to
`sase_100/tests/.../fixture_builder.py`. If that file changes, mirror the change here."* —
human-enforced cross-repo invariants with zero automation, referencing a repo name
(`sase_100`) that no longer exists.

Note the naming has outlived its meaning: per the accepted decision record `rust-core-required`
("no Python fallback and no env-var backend switch"), **there is no Python implementation left to
be at parity with**. These are now frozen goldens with a misleading name. Renaming
`*_parity.rs` → `*_golden.rs` and deleting the "mirror this" instructions is cheaper and more
honest than automating a mirror of something that no longer moves.

### 3.7 MEDIUM — the documentation contradicts the current architecture

This matters more than usual, because `README.md` is the first thing an agent reads. Verified:

- **"The Python `sase_100` repo remains the product shell"** — repo renamed. **63 `sase_100`
  references across 23 `.rs` files, 13 in Markdown**, with `vcs_log_parity.rs` already
  inconsistently using the new path.
- The **Layout** block lists three crates, omitting `sase_xprompt_lsp` (17,025 lines).
- **"Phase status: … Remaining work: 1F"** and *"The PyO3 binding for `scan_agent_artifacts`
  lands in Phase 3C"* — there are now 822 bindings.
- The **Python binding** section states `SASE_CORE_BACKEND=python` is **"the default"** and that
  `is_rust_available()` does opportunistic detection. `rust-core-required` says the opposite, and
  **both identifiers appear 0 times in the code.** The README contains a "superseded" notice two
  sections later, so it contradicts *itself* — a reader who stops early gets the wrong answer.
- `crates/sase_core_py/PYPI_README.md` — **rendered on pypi.org for every user** — still says the
  binding is "opt-in through `SASE_CORE_BACKEND=rust`".

**The worst one is operational.** `scripts/check.sh`'s own header says *"Agents and CI must both
call this script (never `cargo` directly for clippy/test)"*, and `AGENTS.md` says *"Never verify
with `cargo test -p sase_core` alone: it excludes the `sase_core_py` binding tests, which is how
three stale schema-version fixtures reached master in `a509dcc`."* Meanwhile **`README.md`'s
Build & test section instructs the reader to run raw `cargo test --workspace`,
`cargo clippy --workspace --all-targets`, and `cargo test -p sase_gateway push_subscription`.**
The README teaches precisely the habit that already caused a documented incident.

**Coverage is thin overall.** 982 lines of prose total; `docs/` holds one file (a PyPI retention
runbook); `AGENTS.md` is 21 lines covering only release-plz and verification. Grepping all
Markdown for *"adding a new"* / *"when adding"* returns **zero hits** — there is no written
guidance anywhere for the most common task in the repo (add a core function, expose it to
Python). And `sase_core`'s 3,486 public items are **34% documented**. An agent learning the
conventions has to reverse-engineer them from a 35k-line file.

### 3.8 MEDIUM — the declared MSRV is false, and the check that would say so is switched off

`Cargo.toml` declares `rust-version = "1.78"`. There are **8 `#[allow(clippy::incompatible_msrv)]`**
sites (`prompt_stash/store.rs`, `procs/store.rs`, `notifications/store.rs`,
`notifications/pending_actions.rs`) silencing `File::lock()`/`File::unlock()` — **stable since
1.89**. `rust-toolchain.toml` pins `channel = "stable"` and CI reads the same channel, so nothing
ever builds at 1.78. The declared floor is both untrue and untested, and the lint that detected
it was suppressed rather than acted on. Raise `rust-version` to 1.89 and delete the 8 allows.

### 3.9 MEDIUM — a duplicate HTTP stack is carried in the dependency graph

**21 of 275 packages resolve to two or more versions**, and the pattern is not random:

| Package | Versions |
|---|---|
| `hyper` | 0.14.32, 1.9.0 — two complete HTTP stacks |
| `http` / `http-body` | 0.2.12 + 1.4.0 / 0.4.6 + 1.0.1 |
| `base64` | 0.21.7, 0.22.1 |
| `thiserror` (+`-impl`) | 1.0.69, 2.0.18 |
| `hashbrown` | 0.14.5, 0.15.5, 0.17.0 |
| `windows-sys` | 0.48.0, 0.52.0, 0.61.2 |

Root cause: `sase_gateway` pulls **`reqwest 0.11`** (hyper 0.14 / http 0.2 lineage) alongside
**`axum 0.7`** (hyper 1 / http 1). Moving to `reqwest 0.12` collapses the duplication in one
change and measurably cuts cold build time. `tokio-rustls 0.24` and `rustls-pemfile 1` are in the
same bucket. **`pyo3 0.22`** is old enough that clippy 1.95 fires `useless_conversion` on its
macro expansion, worked around with a crate-level `#![allow(...)]` at `sase_core_py/src/lib.rs:668`.

Two small manifest inconsistencies: `sase_core` declares `tempfile = "3"` and
`unicode-width = "0.2"` inline rather than via `[workspace.dependencies]`; and
`[workspace.dependencies]` pins `sase_gateway = { version = "0.34.0" }` while the crate is at
`0.34.70` (harmless under caret semantics, but it shows release-plz updating one pin and not the
other).

### 3.10 MEDIUM — no lint ceiling and no supply-chain gate

The baseline is healthy — `cargo clippy --workspace --all-targets -- -D warnings` is **clean**,
with only **54** `#[allow]` sites. But there is **no `[lints]` table in any manifest, no
`clippy.toml`, no `deny.toml`, no `.cargo/config.toml`**, and `rustfmt.toml` sets only
`max_width = 80`. The bar is exactly "clippy default" — which is how a 35,166-line file and a
1,352-line function became possible without a single warning.

Because you start from zero warnings, you can afford to be ambitious:
`[workspace.lints.clippy]` with `too_many_lines`, `cognitive_complexity`, `missing_panics_doc`
and `unwrap_used` (at `warn`), plus `[workspace.lints.rust] missing_docs = "warn"` on `sase_core`
to start moving the 34% doc coverage. Land it **after** the binding split, so the new lints apply
to already-split files rather than blocking on a 35k-line one.

There is also **no `cargo audit` / `cargo deny` job**, no `cargo doc` check and no coverage
measurement, on a crate publishing wheels to PyPI with 275 transitive packages.

**Note on `max_width = 80`:** the 80-column setting inflates every line count in this report by
roughly 1.3–1.5× relative to a 100-column codebase. The *rankings* are unaffected, but "35,166
lines" is not directly comparable to line counts from other projects.

### 3.11 MEDIUM — panic-shaped error handling at the FFI and LSP boundaries

Strictly excluding inline `#[cfg(test)]` blocks, `tests/` directories and sibling `tests.rs`
files, production code holds **628 `.unwrap()`, 142 `.expect()`, 95 `panic!`**. The concentration
is extreme and tells you exactly where to look:

| File | `unwrap` | `panic!` |
|---|---|---|
| `sase_xprompt_lsp/src/server.rs` | **264** | **90** |
| `sase_core_py/src/lib.rs` | **166** | 0 |
| `sase_gateway/src/sudo_runner.rs` | **107** | 1 |
| `sase_core/src/sections.rs` | 32 | 0 |

Three files hold **85%** of production unwraps. This matters most at the PyO3 boundary, where a
Rust panic reaches Python as `pyo3_runtime.PanicException` rather than a catchable domain error,
and in the LSP, where a panic takes down the language server for the editor session. §3.2's two
LSP failures are literally `Option::unwrap()` on `None` in production paths — the risk is already
realized, not theoretical.

Relatedly, **389 production `Result<_, String>` sites** persist despite `thiserror` being the
house standard (126 derive sites). They cluster in `agent_scan/index.rs` (113),
`telemetry/store.rs` (50), `notifications/store.rs` (33) and `notifications/pending_actions.rs`
(21). Convert the worst files to `thiserror` enums and do the unwrap pass in the same sitting —
it's largely the same set of files.

### 3.12 LOW — 123 independent wire schema versions

`sase_core` defines **123 distinct `*_WIRE_SCHEMA_VERSION` constants**; `wire_schema_version`
appears 371 times in the binding crate; 74 bindings exist purely to return one. This is a
deliberate design — per-domain versioning lets domains evolve independently — and it is not
wrong. But every new domain adds a constant, a getter binding, a registration line, a
doc-manifest line and a cross-repo assertion on the Python side.

The cheap mitigation is a **central `VERSIONS.md` registry** (domain, version, what bumps it,
last bump commit) plus a test asserting versions change only alongside an explicit registry diff,
so bumps are deliberate rather than accidental. This is process debt more than code debt. The
larger question — whether related domains should share a version group — is worth deciding
consciously rather than by accretion.

### 3.13 LOW — copy-pasted store/lock boilerplate and a blurry core/gateway seam

~18 `store.rs` files match `rusqlite|StoreLock|store_lock` (`prompt_stash`, `procs`, `tool_run`,
`telemetry`, `bead/*`, `agent_archive`, `feature_flag_state`, …), each re-implementing
open/lock/txn boilerplate. Separately, fleet logic is split across `sase_core::fleet_*` and
`sase_gateway::fleet_*` with a one-function bridge (`fleet_reads::resync_item`) that hints at an
unclear seam, and `sase_core_py` depends on `sase_gateway` (30 `sase_gateway::` references,
e.g. `fleet_store_error_to_pyerr`) — so the Python wheel bundles the gateway. That is intentional
per `release-plz.toml`, but it blurs the pure-core/gateway split the README claims. Extract a
shared store helper; draw the fleet seam explicitly (core owns facts and catalog math, gateway
owns HTTP and auth) and shrink the `py → gateway` dependency to re-exported wire types.

### 3.14 LOW — the remaining monoliths

| File | Lines | Has a sibling directory? |
|---|---|---|
| `sase_core/src/agent_scan/index.rs` | 13,468 | yes (7 siblings) |
| `sase_core/src/bead/mutation.rs` | 11,316 | yes (14 siblings) |
| `sase_core/src/fleet_contract.rs` | 10,548 | **no** |
| `sase_gateway/src/routes.rs` | 10,062 | **no `routes/`** |
| `sase_xprompt_lsp/src/server.rs` | 9,939 | **no** — 68% of the crate's non-test code |
| `sase_core/src/agent_launch/mod.rs` | 7,978 | yes (6 siblings) |
| `sase_core/src/editor/completion.rs` | 7,260 | yes (18 siblings) |
| `sase_core/src/xprompt_catalog.rs` | 4,850 | **no** |

Same treatment as §3.4, lower urgency because they are single-crate and churn far less (21–34
commits each in the last 300, versus 184). `routes.rs` deserves priority among them — it mixes
routing, ~45 async handlers and inline tests, carries the workspace-high 141 production
`.clone()`s, and pairs with the unverified contract snapshot in §3.6(c). `server.rs` deserves
priority for the panic density in §3.11.

---

## 4. What is *not* a problem — do not "fix" these

A cleanup effort can easily burn itself on the wrong things.

- **Test speed is fine.** ~4,000 tests run in **~50s warm**. Do not shard, do not prune, do not
  adopt `nextest` for speed. *(Report A recommended a documented fast-vs-slow test split on the
  assumption the suite "will get slower." The measurement contradicts the premise. If you want a
  faster inner loop, §3.3's `cargo check` is the lever — the tests are not the bottleneck.)*
- **Do not bulk-move inline `#[cfg(test)]` modules to `tests/`.** Report A recommended this to
  shrink production files. It is the wrong mechanism: Rust inline test modules can reach private
  items, so moving them to `tests/` forces you to widen visibility purely to satisfy the test
  harness — trading a formatting problem for a real API-surface problem. Split the *production*
  file by subdomain and the tests follow their code naturally.
- **Clippy is clean** at `-D warnings` with 54 targeted allows. There is no lint backlog to pay
  down — only a ceiling to raise (§3.10).
- **There is no TODO graveyard** — one marker in 376k lines, and it is a fixture string.
- **`scripts/check.sh` is a genuinely good pattern.** One source of truth for CI and local gates,
  with the PyO3 interpreter-resolution problem solved once and documented with the incident that
  motivated it. Make the rest of the repo look like this; do not touch it.
- **`sase_core`'s subdirectory modules are well factored.** `artifact_file/`, `editor/`, `bead/`,
  `query/`, `artifact_ref/` are the model. The monoliths are the deviation.
- **The `sase_core` / PyO3 separation is real.** `sase_core` has no PyO3 dependency, exactly as
  the README claims.
- **The release automation is thorough and earned.** 272 releases in 63 days at ~75 MB each
  filled the 10 GB PyPI quota, which is why there is now a daily cadence, a completeness gate, a
  quota pre-check, a retention tool and a runbook — with `.github/scripts` carrying its own
  unittest suite, already gated in `check.sh`. **Leave the design alone**; just schedule the
  existing retention pruning.

---

## 5. Recommended change set

Ordered by impact per unit effort.

### Tier 1 — this week (hours)

| # | Change | Finding |
|---|---|---|
| **R1** | **Fix `validate_reap_root`**: canonicalize the denylist before comparing; add `/private/tmp`, `/private/var/tmp`, `$TMPDIR`, `$HOME`. Change `broad_cleanup_roots_are_rejected` to `apply: false` and add `/private/tmp` + `$TMPDIR` cases. | §3.1 |
| **R2** | **Add `macos-latest` to the `rust-checks` CI matrix.** One line; surfaces all 22 failures permanently. | §3.2 |
| **R3** | **Adopt `cargo check` as the inner loop.** Add a `just fast` recipe, a `[profile.dev] debug = "line-tables-only"` section, and document both in `AGENTS.md`. 5m46s → 45s, zero refactoring. | §3.3 |
| **R4** | **Audit `#[cfg(unix)]` vs `#[cfg(target_os = "linux")]`** (131 vs 6). Grep `/proc/` inside `cfg(unix)`; `host_liveness.rs:325` is the correct pattern. Then fix or explicitly gate off `sudo_runner`'s macOS path. | §3.2 |
| **R5** | **Make the docs true.** Rewrite README's Build & test to `just check`; delete the Phase-status / Packaging / stale Python-binding sections; list all four crates; fix `PYPI_README.md`; global `sase_100` → `sase` sweep (63 Rust + 13 Markdown). | §3.7 |
| **R6** | **Write the missing agent guide.** Expand `AGENTS.md` beyond 21 lines: the `*Wire` / `*_WIRE_SCHEMA_VERSION` / `core_*` alias conventions, how to add a core function and expose it to Python, which crate owns what, and the "never `cargo` directly" rule that today lives only in a shell-script comment. | §3.7 |

### Tier 2 — the structural win (weeks)

| # | Change | Finding |
|---|---|---|
| **R7** | **Split `sase_core_py/src/lib.rs` into per-domain binding modules**, each owning its own `register(m)`; collapse the 74 version getters and the `dict → serde → core → json` shape with `macro_rules!`. One domain per PR, mechanical, behavior-neutral. | §3.4 |
| **R8** | **Delete the `//!` API manifest; generate a `.pyi` and gate it in CI.** Converts the largest doc liability into the most useful artifact for Python consumers and agents. | §3.6(a,b) |
| **R9** | **Retire the root prelude.** Delete the 2,256 root re-exports never used via the root path; migrate gateway's 185 and LSP's 27 root-path references to module paths. Compiler-verified at every step. | §3.5 |

### Tier 3 — raise the floor (after R7 lands)

| # | Change | Finding |
|---|---|---|
| **R10** | Add a workspace `[lints]` table (`too_many_lines`, `cognitive_complexity`, `missing_panics_doc`, `unwrap_used` at warn; `missing_docs` on `sase_core`). Also retire the 42 `too_many_arguments` allows by introducing parameter objects — the existing `*Wire` request types are the natural shape. | §3.10 |
| **R11** | Raise `rust-version` to 1.89; delete the 8 `incompatible_msrv` allows. | §3.8 |
| **R12** | `reqwest 0.11 → 0.12` (collapses hyper/http/http-body/base64 duplication in one move), then `pyo3 0.22 → current` (lets you delete the crate-level `useless_conversion` allow). | §3.9 |
| **R13** | Add `cargo deny` (or `cargo audit`) to CI. | §3.10 |
| **R14** | Typed-error + production-unwrap pass on the three hot files (`lsp/server.rs`, `sase_core_py/lib.rs`, `gateway/sudo_runner.rs`) and the four worst `Result<_, String>` files. Same sitting; largely the same code. | §3.11 |

### Tier 4 — close the drift gaps

| # | Change | Finding |
|---|---|---|
| **R15** | Contract-snapshot drift test: assert every `.route()` path appears in `api_v1_contract_snapshot()`, with a documented allowlist. (38 vs 29 today.) | §3.6(c) |
| **R16** | Rename `*_parity.rs` → `*_golden.rs` and delete the "mirror this" instructions — per `rust-core-required` there is no Python implementation left to be at parity with. | §3.6(d) |
| **R17** | Central `VERSIONS.md` registry + a test making schema bumps deliberate. | §3.12 |
| **R18** | Split the remaining monoliths (`routes.rs` → `routes/` first, then `server.rs`, `fleet_contract.rs`, `agent_scan/index.rs`). Shared store/lock helper; draw the core/gateway fleet seam explicitly. | §3.13, §3.14 |
| **R19** | **Standing direction:** split `sase_core` into several crates along the seams the tree already has. The only change that makes the 5m46s cascade structurally go away. Not a next-sprint project. | §3.3 |

### Sequencing

| Phase | Items | Why this order |
|---|---|---|
| 1. Stop the bleeding | R1, R2, R3, R4 | R1 is data loss. R2 makes R4's scope visible instead of guessed. R3 is free and pays back every subsequent phase. |
| 2. Tell the truth | R5, R6 | Cheap, and every later phase is easier once docs and the agent guide are correct. |
| 3. Break the funnel | R7 → R8, R9 | The compounding win. R8 and R9 fall out naturally once bindings are split. |
| 4. Raise the floor | R10–R14 | After R7, so new lints land on already-split files. |
| 5. Close drift gaps | R15–R18 | Lower urgency; none is currently causing failures. |
| — | R19 | Standing direction, revisited when the 5m46s cascade outweighs the refactor. |

---

## 6. Risks and caveats

- **Velocity is the main constraint on restructuring.** 1,250 commits since April, single author,
  ~430/month. Any restructure must be mechanical (moves + re-exports) and land fast, or it will
  conflict with in-flight work. R7, R9 and R18 all qualify; R19 does not, which is why it is a
  direction rather than a task.
- **Timings are machine- and load-dependent.** The 5m46s / 45s / 12s / 31s figures were taken on
  one Apple Silicon machine with a warm target directory. The *ratios* are the finding; the
  absolute numbers will differ elsewhere. Cold build + full test was ~20 min wall on this host,
  versus a ~50s warm test run — so "the suite is fast" is a statement about warm runs only.
- **Line counts are inflated by `max_width = 80`** (§3.10). Rankings hold; cross-project
  comparisons do not.
- **Some counts are syntactic.** Test-vs-production splits mask `#[cfg(test)]` blocks by brace
  matching, which misattributes files whose tests live in a sibling `tests.rs` (9 files, 9,572
  lines) or that have unbalanced braces inside string literals. File-level rankings are robust;
  exact per-function numbers are not.
- **Every change in this list needs a green `./scripts/check.sh` run** — and on macOS, until R1
  lands, run the suite with `-- --skip broad_cleanup_roots_are_rejected`.

---

## 7. Adjudication — where the source reports diverged

Recorded so the consolidated numbers can be trusted over the originals.

| Claim | Report A | Report B | Verified | Verdict |
|---|---|---|---|---|
| Non-test `.unwrap()` | ~5,900 | 1,083 | **628** (strict: excludes `tests/`, `tests.rs`, inline `cfg(test)`) | **A wrong** — raw grep, tests unmasked. A's "`sase_core_py` 2,328" is really **166**. B close; strict count lower still. |
| Test-suite trajectory | "will get slower; add a fast subset" | "50s warm — do not shard" | ~50s warm | **A wrong.** Premise contradicted by measurement. |
| Move inline tests to `tests/` | recommended | not raised | — | **Reject** — inline tests need private access; moving them widens the API surface. |
| Root re-exports dead | not raised | 1,286 (48%) "referenced by no crate" | **2,256 of 2,672 (84%)** never used via root path; only **60 (2%)** unreferenced anywhere | **B directionally right, numerically wrong** — and the opportunity is ~1.8× larger than claimed. Correct framing: *redundant with module paths*, not *unreferenced*. |
| Compile-time driver | implies the binding monolith | not raised | binding file **12s**; `sase_core` leaf **5m46s** | **Both missed it.** New finding §3.3; it reorders the priority list. |
| `#[allow]` sites | ~50, "30+" `too_many_arguments` | 53, 42 | **54**, **42** | B. |
| `incompatible_msrv` allows | 5 | 8 | **8** | B. |
| `pub mod` in `sase_core/src/lib.rs` | 112 | 124 | **107** (`pub mod`); 112 including private `mod` | Neither exactly; A counted all `mod`, B over-counted. |
| `#[pyfunction]` count | "~850", "1681 markers" | 822 | **822** | B. |
| `//!` manifest drift | not raised | 631 of 822 documented, 191 missing | **exactly 631 / 822 / 191**, 0 stale the other way | B, precisely. |
| `#[pymodule]` registration block | not raised | 1,352 lines (19,929–21,280) | **confirmed** (822 registrations; later `add_function` hits are inside `mod tests`) | B. |
| macOS failures | not raised | 22 (19 sudo_runner + 2 LSP + 1 managed_tmp) | **confirmed exactly** | B. |
| `/tmp` reap guard bug | **missed entirely** | CONFIRMED with reproduction | **confirmed by code inspection**; `request()` does set `apply: true`, `max_removals: 2000` | B — the most important finding in either report. |
| Reap production blast radius | n/a | implies caller-supplied `root` is exposed | API does accept one, but **all 3 production callers pass `managed_tmpdir_root()`** | **Both incomplete** — severity is real but is "destroys dev data on every macOS test run" + latent API hole, not "production deletes `/tmp` today." |
| Hub-file co-change (last 100 `feat`) | 79/200 commits touch py lib.rs | 50% both, 81% ≥1 | **50 both / 27 py-only / 4 core-only / 19 neither**; 184/300 recent commits touch py lib.rs | B, reproduced exactly. |
| Routes vs contract paths | "verify it's snapshot-tested" | 38 vs 29, no test | **38 vs 29, no test** | B (A independently flagged the risk). |
| `cfg(unix)` vs `cfg(target_os)` | not raised | 131 vs 6 | **131 vs 6** | B. |
| Doc coverage | not raised | 3,492 items, 35% | **3,486 items, 34%** | B. |
| Duplicate dep versions | not raised | 21 of 275 | **21 of 275**, table matches | B. |
| `Result<_, String>` | 545 (raw) | not raised | **389** production | A directionally right; aggregate inflated, file ranking correct. |
| Release machinery | "leave it alone, prune" | "thorough, keep" | — | **Agree** — both right. |

**Net:** Report B is the stronger document — it ran the gates, found the one bug that destroys
data, and its counts reproduce almost exactly. Report A contributed the store/lock duplication
and core/gateway fleet-seam observations (§3.13) and the wire-version registry idea (§3.12),
which B did not raise, but its panic-hygiene and test-strategy sections rest on unmasked greps
and a premise the measurements contradict. The lead pass added the compile-cascade finding
(§3.3), the corrected prelude numbers (§3.5), and the blast-radius calibration for the reap bug
(§3.1).

---

## 8. Appendix — reproducing the measurements

```bash
sase repo open sase-core -r "<reason>"        # never clone directly

# SAFETY: on macOS, until R1 lands, always skip the destructive test
cargo test --workspace --no-fail-fast -- --skip broad_cleanup_roots_are_rejected

# Edit-cycle cascade (warm target dir)
cargo build --workspace                                   # warm up
touch crates/sase_core/src/host_liveness.rs
time cargo build --workspace                              # 5m46s
touch crates/sase_core/src/host_liveness.rs
time cargo check --workspace                              # 45s
touch crates/sase_core_py/src/lib.rs
time cargo build -p sase_core_py                          # 12s
touch crates/sase_gateway/src/push.rs
time cargo build --workspace                              # 31s

# Hub-file co-change over the last 100 feature commits
git log --format='%H' --grep='^feat' -100 | while read c; do
  f=$(git show --name-only --format='' $c)
  echo "$(echo "$f" | grep -c 'sase_core_py/src/lib.rs')$(echo "$f" | grep -c 'sase_core/src/lib.rs')"
done | sort | uniq -c      # -> 50 "11", 27 "10", 4 "01", 19 "00"

# Binding surface
grep -c '#\[pyfunction'  crates/sase_core_py/src/lib.rs   # 822
grep -c 'add_function'   crates/sase_core_py/src/lib.rs   # 849 (27 are inside mod tests)
grep -c '^//!'           crates/sase_core_py/src/lib.rs   # 663

# Prelude redundancy: re-exported names vs names consumed via the ROOT path
#   2,672 re-exported; 416 root-consumed; 2,256 (84%) redundant
grep -o 'sase_core::[a-z_0-9]*::' crates/sase_gateway/src/*.rs | wc -l    # 53 module-path
grep -oE 'sase_core::[A-Z][A-Za-z0-9_]*' crates/sase_gateway/src/*.rs | wc -l  # 185 root-path

# Platform gates and lint ceiling
grep -rc '#\[cfg(unix)\]' crates/*/src -r | awk -F: '{s+=$2} END{print s}'     # 131
grep -rc 'cfg(target_os = "linux")' crates/*/src -r | awk -F: '{s+=$2} END{print s}'  # 6
grep -rn '\[lints' Cargo.toml crates/*/Cargo.toml                             # none
```
