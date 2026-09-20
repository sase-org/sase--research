# sase-core: Technical Debt and Maintainability Audit

**Researcher:** B (independent; peer report `__a` not consulted)
**Date:** 2026-09-20
**Repo:** `sase-org/sase-core` @ `9a5c568` (master, clean tree), version `0.34.70`
**Platform of measurement:** macOS (Darwin 25.5.0), Apple Silicon

---

## 1. Method and scope

Everything below is measured, not inferred. I opened the linked checkout via `sase repo open`,
read the four crate trees, and ran the repo's own gates (`scripts/check.sh`, `cargo build`,
`cargo clippy`, `cargo test`) plus scripted analyses over the source and git history.

Two caveats up front:

- **Line-attribution caveat.** My test-vs-production line split masks `#[cfg(test)] mod {...}`
  blocks by brace matching. Files that keep tests in a sibling `tests.rs` (9 such files,
  9,572 lines) or that have unbalanced braces inside string literals are misattributed. I flag
  any number affected by this where it appears. Aggregate ratios are reliable; per-function
  outlier rankings are not, so I do not report them.
- **I caused a side effect while measuring.** Running `cargo test --workspace` on this machine
  **deleted four entries under the real `/private/tmp`**, including the Claude Code session
  scratch directory. That is not a mishap on my part — it is finding #2 below, reproduced twice.
  Nothing outside `/tmp` was touched and no repo file was modified.

---

## 2. The repo at a glance

| Measure | Value |
|---|---|
| Crates | 4 (`sase_core`, `sase_core_py`, `sase_gateway`, `sase_xprompt_lsp`) |
| Rust files / total lines | 381 / 376,405 |
| Non-test lines | 253,307 |
| Inline `#[cfg(test)]` lines | 123,098 (32.7%) |
| Lines per crate | core 292,391 · py 35,166 · gateway 31,823 · lsp 17,025 |
| `#[test]` functions | 3,802 |
| Tests executed | 4,049 (4,027 pass, 22 fail, 2 ignored) — **on macOS** |
| Commits (since 2026-04-28) | 1,250, of which 296 are `chore: release` |
| Cargo.lock packages | 275 |
| Python API surface | 822 registered `#[pyfunction]`s |
| `sase_core` public items | 3,492 (1,221 documented — **35.0%**) |
| Prose documentation | 982 lines total, across 5 files |
| `TODO`/`FIXME`/`HACK` markers | 1 (and it is a snippet fixture string) |
| `#[allow(...)]` sites | 53 |
| Cold `cargo build --workspace --all-targets` | **5m 18s** |
| Warm `cargo clippy --workspace --all-targets -- -D warnings` | **1m 47s, 0 warnings** |
| Warm `cargo test --workspace --no-fail-fast` | **50s** |

The headline is that this is a **fast, lint-clean, low-cruft codebase with a small number of
very large structural problems**. There is almost no rot in the usual sense: no TODO graveyard,
no dead feature flags littering the tree, no slow test suite, no clippy debt. The debt is
concentrated in (a) two files that every change has to touch, (b) a platform blind spot in CI,
and (c) a set of hand-maintained manifests and documents that have quietly gone out of date.

---

## 3. Findings, ranked

### Finding 1 — Two hub files funnel a third of all commits (the single biggest agent-throughput tax)

`crates/sase_core_py/src/lib.rs` is **35,166 lines (1.3 MB) in one file**. It was modified by
**400 of ~1,250 commits (32%)**. `crates/sase_core/src/lib.rs` is 1,627 lines and was modified
by **343 commits (27%)**. These are the #1 and #2 churn hotspots by a factor of four over
anything else.

Inside `sase_core_py/src/lib.rs`, one new Python binding requires edits in **four separate
regions of the same file**:

| Region | Lines | What it holds |
|---|---|---|
| `//!` API manifest | 1–663 | hand-written list of exposed functions |
| `use` block | ~670–1,769 | ~1,100 lines of `use sase_core::<mod>::{... as core_...}` |
| Function bodies | ~1,770–19,925 | 822 `#[pyfunction]`s, median body **13 lines** |
| `#[pymodule]` registration | 19,929–21,280 | **1,352 lines** of `m.add_function(...)` |

Plus a fifth edit site in `sase_core/src/lib.rs`'s re-export block. Empirically, over the last
100 `feat` commits:

- **50% touched both hub files**
- **81% touched at least one**
- average 5.46 files changed per commit

For humans this is annoying. For **parallel agents it is close to a hard serialization
constraint**: two agents adding unrelated features have roughly even odds of conflicting in a
35k-line file, and the conflict lands in a 1,352-line append-only list where a naive merge
produces a duplicate or dropped registration that only surfaces as a missing Python symbol at
runtime.

The bindings are also highly mechanical and therefore highly compressible: **522 of 822 bodies
are ≤15 lines**, and **75 are pure `*_wire_schema_version()` constant getters**. The dominant
shapes are `dict -> serde_json -> core call -> json out` with
`PyValueError::new_err(error.to_string())` (557 occurrences).

**The repo already knows how to fix this.** `crates/sase_core/src/artifact_file/` is a
well-factored example: a 727-line module file plus five focused submodules, none over 806 lines.
`editor/` (18 files), `bead/` (14), `artifact_ref/` (14), `query/` (11) follow the same pattern.
The monoliths are the exception, not the house style.

Other files worth the same treatment (prod-line estimates; see the line-attribution caveat):

| File | Total | Est. prod | Notes |
|---|---|---|---|
| `sase_core_py/src/lib.rs` | 35,166 | ~21,186 | see above |
| `sase_core/src/agent_scan/index.rs` | 13,468 | ~6,615 | |
| `sase_core/src/bead/mutation.rs` | 11,316 | ~3,767 | already in a well-split dir |
| `sase_core/src/fleet_contract.rs` | 10,548 | ~7,436 | no subdirectory at all |
| `sase_gateway/src/routes.rs` | 10,062 | ~4,548 | no `routes/` subdirectory |
| `sase_xprompt_lsp/src/server.rs` | 9,939 | ~8,251 | 68% of the crate's non-test code |
| `sase_core/src/agent_launch/mod.rs` | 7,978 | ~5,439 | |

### Finding 2 — CONFIRMED: the `/tmp` safety guard is inert on macOS, and a unit test performs a live reap of the real `/tmp`

`crates/sase_core/src/managed_tmp.rs:900`:

```rust
fn validate_reap_root(root: &Path) -> Result<PathBuf, ManagedTmpReapError> {
    let resolved = root.canonicalize().unwrap_or_else(|_| root.to_path_buf());
    ...
    for unsafe_root in [Path::new("/"), Path::new("/tmp"), Path::new("/var/tmp")] {
        if resolved == unsafe_root { return Err(ManagedTmpReapError::UnsafeRoot(...)); }
    }
```

The root is **canonicalized** and then compared against a **non-canonicalized** denylist. On
macOS `/tmp` is a symlink to `private/tmp` and `/var` to `private/var`, so `resolved` is
`/private/tmp` or `/private/var/tmp` and **no denylist entry can ever match**. The module doc
comment on line 6 promises it "refuses broad roots". On macOS it refuses nothing.

The test that exists to catch this, `managed_tmp::tests::broad_cleanup_roots_are_rejected`
(line 1811), calls `reap_managed_tmpdir` with `root = "/tmp"` and the shared `request()` helper,
which sets **`apply: true`**, **`max_removals: 2000`**, and `default_horizon_seconds: 3 days`.
On Linux the guard fires first and nothing happens. On macOS the guard is skipped and the test
**executes a real reap of `/private/tmp`**.

I observed this twice. Actual output from the failure:

```
called `Result::unwrap_err()` on an `Ok` value: ManagedTmpReapResultWire {
  root: "/private/tmp", apply: true, scanned: 11, selected: 4, removed: 4,
  removed_directories: ["/private/tmp/claude-503/-Users-bbugyi-...-sase_11"], ... }
```

It deleted the running tool session's scratch directory, which broke several of my own tool
calls mid-investigation. With a fuller `/tmp` the blast radius is up to 2,000 entries older
than three days.

This is not only a test-hygiene problem. `reap_managed_tmpdir` is exported to Python as
`sase_core_rs.reap_managed_tmpdir(request: dict)` with a **caller-supplied `root`**
(`sase_core_py/src/lib.rs:2276`), and `validate_reap_root` is the only defense. On macOS that
defense does not exist.

**Severity: highest in this report.** It is also a ~5-line fix.

### Finding 3 — CI is Linux-only; 22 tests fail on the platform the project is actually developed on

All three jobs in `.github/workflows/ci.yml` are `runs-on: ubuntu-latest`. There is no macOS or
Windows runner — while `crates/sase_core_py/pyproject.toml` advertises
`Operating System :: MacOS :: MacOS X` and `:: Microsoft :: Windows` to PyPI.

`cargo test --workspace --no-fail-fast` on clean master, macOS: **4,027 passed, 22 failed**.

| Failing tests | Crate | Root cause |
|---|---|---|
| 19 | `sase_gateway::sudo_runner` | Linux-only procfs in production code |
| 2 | `sase_xprompt_lsp::server` | `Option::unwrap()` on `None` at `server.rs:5774` and `:5861` |
| 1 | `sase_core::managed_tmp` | Finding 2 |

The sudo_runner cluster is the serious one, because it is a **production portability defect, not
a test defect**. `sudo_runner.rs:1632`:

```rust
#[cfg(unix)]
fn process_identity_token(pid: u32) -> Result<String, SudoRunnerCliError> {
    let boot_id = fs::read_to_string("/proc/sys/kernel/random/boot_id")
        .map_err(|error| cli_error(RunnerError, format!("failed to read Linux boot id: {error}")))?;
    let stat = fs::read_to_string(format!("/proc/{pid}/stat"))...
```

It is gated `#[cfg(unix)]` but the body is Linux-specific procfs. macOS is `unix` and has no
`/proc`, so the anti-spoofing identity token — and with it the whole privileged-execution
path — fails with `RunnerError` on macOS. The `sase_sudo_runner` console script **is** installed
by the macOS wheel, and CI's `wheel-smoke` job only asserts that `--help` runs, so nothing
catches it.

The codebase gets this right elsewhere: `sase_core/src/host_liveness.rs:322` uses
`#[cfg(target_os = "linux")]` with a graceful non-Linux fallback. The ratio across the workspace
is **131 `#[cfg(unix)]` vs 6 `#[cfg(target_os = "linux")]`**, so the gate is worth auditing
broadly, not just at this one site.

### Finding 4 — Three hand-maintained manifests that have already drifted

The repo has a recurring pattern: a generated-looking artifact that is actually typed by hand,
with no test asserting it matches reality.

**4a. The `//!` API manifest — 23% drifted.** Lines 1–663 of `sase_core_py/src/lib.rs` are a
bulleted list of exposed Python functions with signatures. It documents **631 of the 822**
registered functions. **191 are missing** (`admission_unit_results`,
`artifact_link_cutover_*`, `agent_unit_dispatch_prompt`, …). Nothing is stale in the other
direction, which tells you the list is append-mostly and people forget the append. It is 663
lines of prose maintaining a fact the compiler already knows.

**4b. The root prelude — 48% dead.** `sase_core/src/lib.rs` declares 124 `pub mod`s and then
re-exports **~2,671 symbols** flat. **1,286 of them (48%) are referenced by no crate and no
integration test in the workspace** — including 711 `*Wire` types and 52 `*_SCHEMA_VERSION`
constants. Every one of those types is already reachable at its module path
(`sase_core::agent_archive::AgentArchiveSummaryWire`), so the prelude is pure duplication of the
public API surface, and it is the reason 27% of commits touch this file.

**4c. The gateway contract snapshot — unverified.** `sase_gateway/src/contract.rs` contains two
hand-written JSON snapshot builders (931 and 776 lines) describing the HTTP API. `routes.rs`
registers **38 distinct routes**; `contract.rs` mentions **29 `/api/v1...` path strings**. I
found **no test asserting the two agree**. The discrepancy may be legitimate (some routes are
unversioned), but nothing enforces it either way, and `routes.rs` is the #4 churn hotspot.

**4d. Cross-repo parity fixtures maintained by comment.** Five integration tests carry
instructions like:

> `agent_scan_parity.rs:9` — "The timestamp constants and JSON payloads are byte-for-byte
> equivalent to `sase_100/tests/agent_scan_golden/fixture_builder.py`. **If that file changes,
> mirror the change here.**"

Same pattern in `git_query_parity.rs`, `vcs_log_parity.rs`, `golden_corpus_parity.rs`, and
`config_parity.rs` (whose golden is "produced by the real Python `sase.config.core._deep_merge`"
and then frozen). These are human-enforced cross-repo invariants with zero automation. They also
reference **`sase_100`**, a repository name that no longer exists — 83 such references in Rust
and 13 in Markdown, with `vcs_log_parity.rs` already inconsistently using the new `sase/` path.

Worth noting the naming has outlived its meaning too: per the accepted decision record
`rust-core-required` ("no Python fallback and no env-var backend switch"), there is no Python
implementation left to be at parity *with*. These are now just golden-fixture tests with a
misleading name that implies a live counterpart.

### Finding 5 — The documentation actively contradicts the current architecture

This matters more than usual here, because the README is the first thing an agent reads.

`README.md` (305 lines) says:

- **"The Python `sase_100` repo remains the product shell"** — renamed repo.
- The **Layout** block lists three crates and omits `sase_xprompt_lsp` entirely (17,025 lines).
- **"Phase status: … Remaining work: 1F"** and **"The PyO3 binding for `scan_agent_artifacts`
  lands in Phase 3C"** — there are now 822 bindings.
- The **Python binding** section states `SASE_CORE_BACKEND=python` is **"the default"** and that
  `is_rust_available()` does opportunistic detection. The `rust-core-required` decision says the
  opposite. The README even contains a "superseded" notice two sections later — so the file
  contradicts *itself*, and a reader who stops at the earlier section gets the wrong answer.
  `SASE_CORE_BACKEND` and `is_rust_available` now appear **only** in documentation; they exist
  nowhere in the code.
- Points at `../sase_100/docs/mobile_mvp_runbook.md`.

The worst one is operational. `scripts/check.sh`'s own header says:

> "Agents and CI must both call this script (**never `cargo` directly** for clippy/test) so local
> verification cannot silently drift from what CI checks."

and `AGENTS.md` says:

> "**Never verify with `cargo test -p sase_core` alone**: it excludes the `sase_core_py` binding
> tests, which is how three stale schema-version fixtures reached master in `a509dcc`."

…while `README.md`'s **Build & test** section instructs the reader to run raw
`cargo test --workspace`, `cargo clippy --workspace --all-targets`, and
`cargo test -p sase_gateway push_subscription`. The README is teaching precisely the habit that
already caused a documented production incident.

`crates/sase_core_py/PYPI_README.md` — the text rendered on pypi.org for every user — also still
says the binding is "opt-in through `SASE_CORE_BACKEND=rust`".

**Coverage is thin overall.** 982 lines of prose total. `docs/` contains exactly one file, a
PyPI retention runbook. `AGENTS.md` is 21 lines covering only release-plz and verification.
Grepping all Markdown for "adding a new" / "to add a new" / "when adding" returns **zero hits** —
there is no written guidance anywhere for the most common task in the repo (add a core function,
expose it to Python). And `sase_core`'s 3,492 public items are **35% documented**, so an agent
that needs to learn the conventions has to reverse-engineer them from a 35k-line file.

### Finding 6 — The declared MSRV is false, and the check that would say so is switched off

`Cargo.toml` declares `rust-version = "1.78"` for the whole workspace. There are **8
`#[allow(clippy::incompatible_msrv)]`** sites in `prompt_stash/store.rs`, `procs/store.rs`,
`notifications/store.rs`, and `notifications/pending_actions.rs`, all silencing uses of
`File::lock()`/`File::unlock()` — **stable since Rust 1.89**.

`rust-toolchain.toml` pins `channel = "stable"` and CI reads that same channel, so nothing ever
builds at 1.78. The declared floor is both untrue and untested; the lint that detected it was
suppressed rather than acted on. Either raise `rust-version` to the real floor (1.89) or add a
CI job that builds at the declared version. Raising it is almost certainly right.

### Finding 7 — Dependency drift is carrying a duplicate HTTP stack

**21 packages resolve to two or more versions** in `Cargo.lock`, and the pattern is not random:

| Package | Versions | |
|---|---|---|
| `hyper` | 0.14.32, 1.9.0 | two complete HTTP stacks |
| `http` | 0.2.12, 1.4.0 | |
| `http-body` | 0.4.6, 1.0.1 | |
| `base64` | 0.21.7, 0.22.1 | |
| `thiserror` (+`-impl`) | 1.0.69, 2.0.18 | |
| `windows-sys` | 0.48, 0.52, 0.61 | |
| `hashbrown` | 0.14, 0.15, 0.17 | |

Root cause: `sase_gateway` pulls **`reqwest 0.11`** (hyper 0.14 / http 0.2 lineage) alongside
**`axum 0.7`** (hyper 1 / http 1). Moving to `reqwest 0.12` collapses the duplication and
removes a meaningful slice of the 5m18s cold build. `tokio-rustls 0.24` and `rustls-pemfile 1`
are in the same bucket.

Also aging: **`pyo3 0.22`** — old enough that clippy 1.95 now fires `useless_conversion` on its
macro expansion, worked around with a crate-level `#![allow(...)]` at
`sase_core_py/src/lib.rs:668`. The workspace is on `edition = "2021"`.

Two small manifest inconsistencies: `sase_core` declares `tempfile = "3"` and
`unicode-width = "0.2"` inline instead of via `[workspace.dependencies]` like every other
dependency; and `[workspace.dependencies]` pins `sase_gateway = { version = "0.34.0" }` while the
crate is at `0.34.70` (harmless under caret semantics, but it shows release-plz updates one pin
and not the other).

### Finding 8 — No type stubs for an 822-function Python module

`sase_core_rs` exposes 822 functions and ships **no `.pyi` file** — I found zero stubs in the
repo. Every Python consumer, and every agent writing Python against this API, gets no signatures,
no parameter names, no return types, and no editor completion. Given that the Python side is the
*only* real consumer, this is disproportionate leverage for the effort: a generated stub would
do more for day-to-day agent productivity than most of the Rust-side refactors.

### Finding 9 — The lint ceiling is low, and there is no supply-chain gate

The baseline is genuinely healthy: `cargo clippy --workspace --all-targets -- -D warnings` is
**clean (0 warnings)**, and there are only 53 `#[allow]` sites total (42 of them
`clippy::too_many_arguments`). That is better than most codebases this size.

But there is **no `[lints]` table in any manifest**, no `clippy.toml`, no `deny.toml`, no
`.cargo/config.toml`. The bar is exactly "clippy default," and `rustfmt.toml` sets only
`max_width = 80`. Nothing enforces module size, function length, doc coverage, or `unwrap` policy
— which is how a 35,166-line file and a 1,352-line function became possible without a single
warning.

There is also no `cargo audit` / `cargo deny` job, no `cargo doc` check, and no coverage
measurement, on a crate that publishes wheels to PyPI.

### Finding 10 — Panic-shaped error handling at the FFI and LSP boundaries

Outside inline `#[cfg(test)]` blocks: **1,083 `.unwrap()`**, 147 `.expect()`, 117 `panic!`,
11 `unreachable!`. Concentrations are `sase_xprompt_lsp/src/server.rs` (264),
`sase_core_py/src/lib.rs` (166), and `sase_gateway/src/sudo_runner.rs` (107). Treat these as
upper bounds — those three files hold test helpers my mask did not catch — but the shape is
confirmed by Finding 3: the two LSP failures are literally `Option::unwrap()` on `None` in
production paths.

This matters most at the PyO3 boundary, where a Rust panic reaches Python as
`pyo3_runtime.PanicException` rather than a catchable domain error, and in the LSP, where a
panic takes down the language server for the editor session.

### Finding 11 — 123 independent wire schema versions

`sase_core` defines **123 distinct `*_WIRE_SCHEMA_VERSION` constants**; `wire_schema_version`
appears 371 times in the binding crate; 75 bindings exist purely to return one of them. This is
a deliberate design (per-domain versioning lets domains evolve independently), and I am not
arguing it is wrong. But it is a real ongoing cost: every new domain adds a constant, a getter
binding, a registration line, a doc-manifest line, and a cross-repo assertion on the Python side.
It is worth deciding consciously whether 123 independently-versioned contracts is still earning
its keep, or whether related domains should share a version group.

---

## 4. What is *not* a problem (do not "fix" these)

Worth stating explicitly, because a cleanup effort can easily burn itself on the wrong things:

- **Test speed is excellent.** 4,049 tests in **50 seconds** warm. Do not shard, do not prune,
  do not introduce `nextest` for speed reasons.
- **Clippy is clean** at `-D warnings` with only 53 targeted allows. There is no lint backlog.
- **There is no TODO graveyard** — one marker in 376k lines, and it is a fixture string.
- **`scripts/check.sh` is a genuinely good pattern.** Single source of truth for CI and local
  gates, with the PyO3 interpreter-resolution problem solved once and documented with the
  incident that motivated it. This should be the model for the rest of the repo, not a target.
- **`sase_core`'s subdirectory modules are well factored.** `artifact_file/`, `editor/`,
  `bead/`, `query/`, `artifact_ref/` are all sensible. The monoliths are the deviation.
- **The `sase_core` / PyO3 separation is real and worth keeping.** `sase_core` has no PyO3
  dependency, exactly as the README claims. (One wrinkle: `sase_core_py` depends on
  `sase_gateway` — 30 `sase_gateway::` references — so the Python wheel bundles the gateway.
  That is intentional per `release-plz.toml`, just worth knowing.)
- **The release automation is thorough.** `release-plz.toml` with version groups,
  `check_cargo_version_edits.py`, PyPI quota/retention tooling with its own unit tests. This is
  more operational rigor than most projects this age have.

---

## 5. Recommended changes

Ordered by impact-per-unit-effort. The first four are small and high-value; the rest are real
projects.

### Tier 1 — Do this week (hours, not days)

**R1. Fix `validate_reap_root` and de-fang its test.** *(Finding 2 — safety)*
Canonicalize the denylist before comparing, or compare canonicalized-to-canonicalized:
```rust
for unsafe_root in ["/", "/tmp", "/var/tmp"] {
    let denied = Path::new(unsafe_root).canonicalize()
        .unwrap_or_else(|_| PathBuf::from(unsafe_root));
    if resolved == denied { return Err(...); }
}
```
Also add `/private/tmp`, `/private/var/tmp`, `$TMPDIR`, and the user's home directory to the
list. Separately, change `broad_cleanup_roots_are_rejected` to assert with `apply: false` so a
future guard regression cannot delete anything, and add cases for `/private/tmp` and `$TMPDIR`.
This is the only finding in the report that can destroy data.

**R2. Add `macos-latest` to the CI matrix.** *(Finding 3)*
One matrix line on the `rust-checks` job. It immediately surfaces all 22 failures and permanently
closes the "green in CI, red on the dev machine" gap. Expect to then either implement a macOS
`process_identity_token` (sysctl `KERN_PROCARGS`/`kinfo_proc` for start time, plus a boot-time
substitute from `kern.boottime`) or explicitly gate `sase_sudo_runner` off on macOS and stop
advertising macOS support for it. Either is defensible; silently shipping a broken console script
is not.

**R3. Audit `#[cfg(unix)]` vs `#[cfg(target_os = "linux")]`.** *(Finding 3)*
131 vs 6 today. Grep for `/proc/` inside `#[cfg(unix)]` blocks; `host_liveness.rs:322` already
shows the correct pattern. R2 will find these for you, but a targeted pass is faster.

**R4. Make the documentation true.** *(Finding 5)*
The cheapest high-leverage change in the report, because docs are what agents read first.
- Rewrite `README.md`'s **Build & test** section to say `just check` / `./scripts/check.sh` and
  delete the raw `cargo` invocations.
- Delete the **Phase status**, **Packaging decision (Phase 1E)**, and stale **Python binding**
  paragraphs; replace the Layout block with all four crates.
- Fix `PYPI_README.md` (it is user-facing on pypi.org).
- Global `sase_100` → `sase` sweep (83 Rust + 13 Markdown references).

### Tier 2 — The structural win (weeks, but this is the one that changes daily life)

**R5. Split `sase_core_py/src/lib.rs` and make registration derivable.** *(Finding 1 — highest
structural impact)*
Target shape, mirroring `artifact_file/`:
```
crates/sase_core_py/src/
  lib.rs              # <200 lines: mod decls + #[pymodule] that calls per-domain registrars
  convert.rs          # py_to_json_value / json_value_to_py / error mapping
  bindings/
    agent_scan.rs     # own `use` block, own fns, own `pub fn register(m) -> PyResult<()>`
    bead.rs
    fleet.rs
    ...
```
Two design points make or break this:
- **Each submodule owns its own `register(m)`**, so the 1,352-line append-only registration list
  disappears and new bindings stop colliding. `lib.rs` calls ~40 registrars.
- **Collapse the mechanical shapes with a `macro_rules!`.** Start with the 75
  `*_wire_schema_version()` getters (a one-line macro invocation each) and the
  `dict -> serde -> core -> json` shape, which covers a large share of the 522 bodies ≤15 lines.

Do it incrementally — one domain per PR, mechanical moves with no behavior change, verified by
`./scripts/check.sh` and the existing wheel-smoke job. The payoff is that two agents working on
unrelated domains stop touching the same file at all.

**R6. Retire the root prelude in `sase_core/src/lib.rs`.** *(Finding 4b)*
Delete the **1,286 re-exports (48%) that nothing references**; they are all still reachable at
their module paths. Then decide a policy for the rest — my recommendation is to drop the flat
prelude entirely and have consumers import from module paths, which eliminates the second hub
file and the "two names for every symbol" ambiguity. If a prelude is wanted, scope it to a
`pub mod prelude` with a documented, deliberately small membership rule. Mechanical, and the
compiler verifies every step.

**R7. Delete the `//!` API manifest; generate a `.pyi` instead.** *(Findings 4a + 8)*
Replace 663 lines of drifting prose with a short module doc that says "see the generated stub,"
and add a `.pyi` generated from the `#[pyfunction]` signatures (or hand-curated per domain once
R5 has split them, which makes it tractable). Gate it in CI so the stub cannot drift. This one
change converts the repo's largest documentation liability into its most useful artifact for
Python-side consumers and agents.

### Tier 3 — Steady-state hygiene

**R8. Add a workspace `[lints]` table.** *(Finding 9)* You are starting from zero warnings, so
you can afford to be ambitious. Suggested opening position in `[workspace.lints.clippy]`:
`too_many_lines`, `cognitive_complexity`, `missing_panics_doc`, `unwrap_used` (at `warn` for
now), plus `[workspace.lints.rust] missing_docs = "warn"` on `sase_core` to start moving the 35%
doc coverage. Set a per-file line budget informally in `AGENTS.md`; the existing subdirectory
pattern gives you a natural target.

**R9. Fix the MSRV.** *(Finding 6)* Raise `rust-version` to the real floor (1.89, given
`File::unlock`) and delete the 8 `#[allow(clippy::incompatible_msrv)]`. If the 1.78 floor is a
real commitment, add a CI job that builds at it instead — but nothing currently depends on it.

**R10. Collapse the duplicate HTTP stack.** *(Finding 7)* `reqwest 0.11 -> 0.12` removes
`hyper 0.14`, `http 0.2`, `http-body 0.4`, and a `base64` duplicate in one move, and measurably
cuts the 5m18s cold build. Then `pyo3 0.22 -> current`, which should also let you delete the
crate-level `#![allow(clippy::useless_conversion)]`.

**R11. Add `cargo deny` (or `cargo audit`) to CI.** *(Finding 9)* 275 transitive packages
shipping to PyPI with no advisory gate.

**R12. Add a contract-snapshot drift test.** *(Finding 4c)* Assert that every `.route()` path
registered in `routes.rs` appears in `api_v1_contract_snapshot()` (with an explicit, documented
allowlist for intentional exclusions). 38 routes vs 29 documented paths today, with nothing
checking either way.

**R13. Automate or honestly rename the parity fixtures.** *(Finding 4d)* Pick one:
(a) generate the fixtures from the Python source in CI so "mirror the change here" becomes
mechanical; (b) accept them as frozen goldens and rename `*_parity.rs` to `*_golden.rs`, deleting
the "mirror this" instructions — since per `rust-core-required` there is no Python implementation
left to be at parity with. **(b) is cheaper and more honest**; (a) is only worth it if the Python
fixtures still change.

**R14. Split the remaining monoliths** — `sase_xprompt_lsp/src/server.rs` (9,939),
`sase_gateway/src/routes.rs` (10,062 -> `routes/`), `sase_core/src/fleet_contract.rs` (10,548),
`sase_core/src/agent_scan/index.rs` (13,468). Same pattern as R5, lower urgency because they are
single-crate and churn less.

**R15. Write the missing agent guide.** *(Finding 5)* Expand `AGENTS.md` from 21 lines to cover:
the `*Wire` / `*_WIRE_SCHEMA_VERSION` / `core_*` import-alias conventions; how to add a core
function and expose it to Python (which will be a short list once R5 lands); which crate owns
what; and the "never `cargo` directly" rule that currently lives only in a shell-script comment.
This is the document that stops the next agent from learning the conventions by reading 35,000
lines.

---

## 6. Suggested sequencing

| Phase | Items | Why this order |
|---|---|---|
| **1. Stop the bleeding** | R1, R2, R3 | R1 is a data-loss bug. R2 makes R3's scope visible instead of guessed. |
| **2. Tell the truth** | R4, R15 | Cheap, and every later phase is easier when the docs and agent guide are correct. |
| **3. Break the funnel** | R5, then R6, R7 | The compounding win. Do R5 domain-by-domain; R6 and R7 fall out naturally once bindings are split. |
| **4. Raise the floor** | R8, R9, R10, R11 | Best done *after* R5, so new lints land on already-split files rather than blocking on a 35k-line one. |
| **5. Close the drift gaps** | R12, R13, R14 | Lower urgency; none of these is currently causing failures. |

**If you only do three things:** R1 (the `/tmp` guard), R2 (macOS in CI), and R5 (split the
binding crate). The first two are safety; the third is the one that changes what it feels like
to work in this repo — for humans and agents alike.

---

## 7. Appendix — reproducing the measurements

```bash
# Open the checkout (do not clone directly)
sase repo open sase-core -r "<reason>"

# Timings quoted in this report
cargo build --workspace --all-targets                        # 5m18s cold
cargo clippy --workspace --all-targets -- -D warnings        # 1m47s warm, 0 warnings
cargo test --workspace --no-fail-fast                        # 50s; 4027 pass / 22 fail / 2 ignored

# Churn hotspots
git log --since='1 year ago' --name-only --format='' -- 'crates/**/*.rs' \
  | grep -v '^$' | sort | uniq -c | sort -rn | head -10

# Hub-file co-change rate over the last 100 feature commits
git log --format='%h' --grep='^feat' -100 | while read c; do
  f=$(git show --name-only --format='' $c)
  echo "$(echo "$f" | grep -c 'sase_core_py/src/lib.rs')$(echo "$f" | grep -c 'sase_core/src/lib.rs')"
done | sort | uniq -c        # -> 50x "11", 27x "10", 4x "01", 19x "00"

# Binding-surface facts
grep -c '#\[pyfunction\]'  crates/sase_core_py/src/lib.rs   # 822
grep -c 'add_function'     crates/sase_core_py/src/lib.rs   # 849
grep -c '^//!'             crates/sase_core_py/src/lib.rs   # 663
grep -rho 'pub const [A-Z_]*WIRE_SCHEMA_VERSION' crates/sase_core/src | sort -u | wc -l   # 123

# Duplicate dependency versions
grep -c '^\[\[package\]\]' Cargo.lock                        # 275
```

**Safety note for anyone reproducing this:** on macOS, `cargo test --workspace` will delete
entries under the real `/private/tmp` until R1 lands. Back up anything you care about under
`/tmp` first, or run `cargo test --workspace -- --skip broad_cleanup_roots_are_rejected`.
