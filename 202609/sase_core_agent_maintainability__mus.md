# sase-core agent-maintainability: beyond the file-size epics

**Researcher:** mus · **Date:** 2026-09-21 · **Swarm:** research.24 (independent report, `__mus` suffix)
**Baseline:** consolidated audit `research:202609/sase_core_maintainability_audit/sase_core_maintainability_audit.md`
(measured @ `9a5c568`, v0.34.70) and its two source reports `__a` / `__b`.
**Re-measured:** sase-core @ `b7af6b7` (mid-epic sase-15b: 6/10 phases closed, 4 in progress),
via the linked checkout opened with `sase repo open sase-core`.
**Epics:** sase-14s (CLOSED 2026-09-21, 10/10 phases) · sase-15b (IN_PROGRESS, 6/10 closed).

## TL;DR and recommended solution

**Finish sase-15b's four in-flight phases, then stop the line-count epic chain. Do not
launch a sase-15c/15d. Declare the `<=1500 lines` rule a success and replace it with a
split-on-evidence rule.**

The 14s/15b approach proved itself on the files it touched and should not be extended
as a standing program, because the remaining work has sharply diminishing
agent-maintainability value while the highest-leverage agent items from the audit are
still untouched. The next effort should be a small **agent-interface package**, ordered
by impact per hour, followed by **crate surgery as a designed project** (not an epic
chain) only if the fast inner loop proves insufficient.

Concretely, in order:

1. **Freeze the treadmill (this week).** Land 15b.7–15b.10. Then a moratorium on
   proactive line-count splits: split a file only when it causes a merge conflict,
   exceeds agent context on a real task, or churns with unrelated domains — never
   because a script lists it over N lines. The repo still has **45 files >1500 lines**
   after two ten-file epics; the list is regenerating, not converging.
2. **Land the agent-interface tier (next, weeks not months).**
   (a) Generate `.pyi` stubs from `#[pyfunction]` signatures and gate drift in CI —
   the single highest leverage-per-hour item for every Python-side agent.
   (b) Make the docs true and write the missing agent guide: rewrite README Build &
   test to `just check`, delete stale Phase/`SASE_CORE_BACKEND`/`sase_100` passages,
   and expand `AGENTS.md` (36 lines) with the `*Wire` / `*_WIRE_SCHEMA_VERSION` /
   `core_*` conventions, crate ownership map, and how to add a core function and
   expose it to Python.
   (c) Adopt `cargo check` as the inner loop: `just fast` + `[profile.dev]
   debug = "line-tables-only"`. This is the only change that attacks the 5m46s
   cascade without restructuring.
   (d) Retire the root prelude (107 `pub use`, still intact) by migrating gateway +
   LSP root-path references to module paths, or scope it to an explicit `prelude`
   module. This removes the second hub file and its churn on the 5m46s path.
   (e) Close the cheap drift gaps: gateway contract route-vs-snapshot test,
   `*_parity.rs` → `*_golden.rs` rename, central `VERSIONS.md` registry + bump test.
3. **Raise the floor in one batched pass (after 2).** Workspace `[lints]`
   (`too_many_lines`, `cognitive_complexity`, `missing_panics_doc`, `unwrap_used` at
   warn; `missing_docs` on `sase_core`), MSRV 1.78 → 1.89 with the 8
   `incompatible_msrv` allows deleted, `reqwest 0.11 → 0.12`, `pyo3 0.22 → current`,
   `cargo deny` in CI, and a typed-error + unwrap pass confined to the three hot
   files plus the four worst `Result<_, String>` files. Batch it so new lints land on
   already-split trees.
4. **Treat `sase_core` crate surgery as a design project, not the next epic chain.**
   The audit's standing direction (R19) is correct — only fewer, smaller crates turn
   the 5m46s cascade into ~30s edits — but it moves the public API, release-plz, and
   the Python binding surface together, so it needs a design doc with seam choices
   (bead, agent_scan, editor, query, artifact_*, fleet_*) and a migration order, not
   ten parallel split workers.

## 1. What "easy to maintain by sase agents" actually means

Human maintainability advice (short functions, low complexity) overlaps but does not
cover the agent case. An agent's bottleneck is different: limited context, no hallway
knowledge, parallel siblings editing the same tree, and verification through scripts
rather than intuition. From the audit's evidence plus the 14s/15b experience, seven
dimensions matter, roughly in order:

1. **Context fit and task locality.** Can the files relevant to one task fit in the
   window, and does one task touch one directory? A 35k-line file can never be read;
   agents then blind-append, which is how god files grow. But locality is about
   *domains*, not lines: ten 1400-line files with tangled cross-imports are worse
   than three well-bounded modules.
2. **Parallel-edit safety.** Can two agents add unrelated features without colliding?
   Hub files and append-only registration lists serialize work and produce silent
   merge damage (duplicate/dropped registrations surfacing only as missing Python
   symbols at runtime). Per-domain registration ownership fixes this structurally.
3. **Discoverability without tribal knowledge.** The agent reads README/AGENTS.md
   first, then greps. Stale docs are worse than no docs because they teach the exact
   habit that caused a past incident (README's raw-`cargo` instructions vs the
   `a509dcc` stale-fixture lesson). Conventions (`*Wire` types, `*_WIRE_SCHEMA_VERSION`,
   `core_*` aliases, which crate owns what) must be written, not reverse-engineered.
4. **Python-surface legibility.** The Python side is the only real consumer (822+
   bindings, 0 `.pyi` stubs). Without stubs there are no signatures, parameter names,
   return types, or completions for any Python-writing agent. A hand-maintained `//!`
   manifest (631/822 documented, 191 missing at audit time) is a liability, not an
   asset; generated artifacts gated in CI are the fix.
5. **Verification speed and fidelity.** The inner loop must be fast *and* be the same
   gate CI runs. `cargo check` at 45s vs `cargo build` at 5m46s (audit's warm
   measurement) is a 7.7× free speedup; `scripts/check.sh` as the single entry point
   is the pattern to extend, not bypass.
6. **Error clarity at boundaries.** `Result<_, String>` (389 production sites) and
   `.unwrap()` concentrations (85% in three files) convert diagnosable failures into
   `pyo3_runtime.PanicException` on the Python side or a dead LSP session. Typed
   errors are greppable, matchable, and documentable; strings are none of these.
7. **Mechanical-change safety.** Splits, renames, and prelude removals must be
   compiler-verified step by step (moves + re-exports, `just check` green per phase).
   Anything requiring simultaneous cross-repo edits or flag-day renames needs
   sequencing, not parallelism.

A proposal that improves (1) while regressing (2)–(5) is a net loss for agents. That
is the lens applied below.

## 2. Where the repo stands after 14s (+ partial 15b)

### 2.1 What the file-size epics achieved (real wins — credit them)

- **The binding monolith is gone.** `crates/sase_core_py/src/lib.rs` went from
  **35,166 lines to 736**, with ~30 domain directories (`beads/`, `agent_scan/`,
  `fleet/`, …) each owning its `register_<domain>(m)` (e.g. `beads/mod.rs:1326`
  `register_beads`), called from a ~30-line `#[pymodule]` body. This is almost
  exactly the audit's §3.4 target shape, including the critical design point (each
  submodule owns its registration, so the 1,352-line append-only list is gone).
  Merge-collision risk and blind-append pressure on the worst hub file are
  structurally reduced.
- **The LSP monolith is gone.** `sase_xprompt_lsp/src/server.rs` (9,939 lines, 264
  unwraps + 90 panics) is now `server/` with 8 files, max 782 lines
  (`completion.rs`), plus `catalog_cache.rs`, `lsp_convert.rs`, etc. Panic density
  is now addressable per file.
- **Core monoliths are facaded.** `agent_launch/mod.rs` is a documented facade of
  ~14 submodules with `pub use` re-exports; `bead/` gained `cli/`, `events/`,
  `mutation/` subtrees; `gateway/routes.rs` gained `routes/` (`router.rs`,
  `support.rs`, handlers, `tests/`). File counts rose **381 → 665**; every one of
  the 20 targeted trees is now ≤1500 lines per the epic notes.
- **Safety/CI fixes landed alongside (outside the split logic).** Verified this
  session: `managed_tmp.rs` now canonicalizes the denylist and covers
  `/private/tmp`, `/private/var/tmp`, `$TMPDIR`, `$HOME` (audit R1); CI
  `rust-checks` runs `ubuntu-latest` + `macos-latest` (R2); `AGENTS.md` grew 21 →
  36 lines with Platform-paths and macOS-verification sections (R6 partial).

### 2.2 What did not move — the higher-leverage half of the audit

Re-verified at `b7af6b7`:

| Audit item | Status now |
|---|---|
| `sase_core/src/lib.rs` root prelude (R9) | **Untouched: still 107 `pub mod` + 107 `pub use`.** Second hub file intact. |
| `.pyi` stubs + manifest retirement (R8) | **Untouched: 0 `.pyi` files, no generator, no gate.** `lib.rs` `//!` header still a hand-maintained function list. |
| `cargo check` inner loop (R3) | **Untouched: no `just fast`, no `[profile.dev]`** (only `[profile.release]` + `[profile.dev-update]`). `justfile` is still check/fmt/clippy/test. |
| Workspace `[lints]` ceiling (R10) | **Untouched: no `[lints]` table;** `too_many_arguments` allows still **42**, `rustfmt.toml` still only `max_width = 80`. |
| MSRV 1.78 (R11) | **Untouched: still 1.78, 8 `incompatible_msrv` allows present.** |
| Deps (R12) | **Untouched: `reqwest 0.11`, `pyo3 0.22`.** |
| Supply-chain/doc gates (R10/R13) | **No `deny.toml`, no doc/coverage gate.** |
| README truth (R5) | **Still stale:** `sase_100` references throughout (repo/product-shell/Phase passages), `SASE_CORE_BACKEND=python`-era packaging text, three-crate layout omitting the LSP crate, Phase 1D/1E/3B/3C status prose. `docs/` still one file. |
| Contract drift test (R15), parity rename (R16), VERSIONS registry (R17) | **No evidence of landing** (routes vs snapshot still ungated; `*_parity.rs` names intact; 216 files carry `_WIRE_SCHEMA_VERSION`). |
| Store boilerplate / fleet seam (R13–R14) | **~18 `store.rs` files persist;** `py → gateway` dependency intact. |
| Unwrap / `Result<String>` concentrations (R14) | Split across new files but **not yet typed**; the pass is still ahead. |

Pattern: the epic chain delivered the mechanical half of Tier 2 and none of Tiers
1-fast-loop, 1-docs, 1-prelude, 3, or 4. The reap guard and macOS CI — the two
highest-severity audit items — were fixed as small direct patches, not as splits.

### 2.3 The treadmill number: 45 files still over 1500

After *twenty* targeted splits, `find crates -name '*.rs' | xargs wc -l` still shows
**45 files above 1500 lines** (of 665 total, 381k lines). The current top includes
the four in-flight 15b targets (`provider_usage/tests.rs` 3368,
`editor/directive.rs` 2952, `runner_capacity.rs` 2938,
`tests/notification_store_parity.rs` 2825) — but behind them stand `frontmatter.rs`
2699, `agent_ownership/planner.rs` 2665, `agent_scan/scanner.rs` 2573,
`agent_hold.rs` 2567, `telemetry/store.rs` 2512, `sudo.rs`/`procs/store.rs` 2352,
and ~30 more between 1500–2300. Two full epics moved the maximum from ~13k to ~3.4k
without reducing the *count* of over-threshold files to anything like zero, because
ordinary development grows new ones. A 15c/15d/15e sequence converges
asymptotically at best, and each round pays merge-conflict risk against a ~430
commits/month velocity for progressively smaller context-fit gains (a 2300-line file
is already skimmable per-domain; a 35k-line file was not).

Worse, three of the remaining top-ten are *test* files (`tests.rs`, `*_parity.rs`).
Splitting test files by line count buys almost no agent-maintainability: tests follow
their production code (the audit's own §4 warning against bulk-moving inline tests
applies — widening visibility to satisfy a line metric trades a real API problem for
a formatting one). The parity files additionally carry the misleading
cross-repo-mirror instructions the audit says to delete, not to rehouse.

## 3. Assessment against the seven agent dimensions

- **Context fit (1): won where it mattered, exhausted elsewhere.** 14s fixed the
  files no agent could read (35k, 13k, 11k, 10k). The remaining 1500–3000-line files
  are an ordinary large-codebase distribution; further blind splits risk arbitrary
  seams (splitting a coherent 2300-line planner into two 1150-line halves with a
  shared private core) that hurt locality more than line counts help it.
- **Parallel safety (2): the binding win is real but incomplete.** Per-domain
  `register_*` removes the 1,352-line collision point. But `sase_core/src/lib.rs`
  (107 re-exports, touched by ~140/300 commits at audit time) remains the second
  funnel, and every touch still pays the crate-wide rebuild. Prelude retirement is
  now the binding for (2).
- **Discoverability (3): net negative from splits alone.** 284 new files with
  mechanical names (`support.rs`, `wires.rs`, `store.rs` × 18) increase the
  grep-and-navigate load while README/AGENTS.md still describe a three-crate,
  `sase_100`-era repo. An agent arriving today meets *more* files and *equally
  stale* maps. Docs must catch up before further subdivision.
- **Python legibility (4): unchanged.** Zero stubs means the entire binding win is
  invisible to Python-side agents. This single artifact dominates (4) and costs
  hours-to-days, not weeks.
- **Verification (5): unchanged and dominant.** File splits do not touch the
  5m46s/45s ratio — compilation unit is the crate, and `sase_core` is still one
  292k-line-class crate. `just fast` + dev-profile tuning is free and unclaimed.
- **Errors (6): now splittable, not yet fixed.** The hot files are small enough to
  convert one by one; the conversions themselves remain.
- **Mechanical safety (7): the house pattern is proven.** Facade `mod.rs` + `pub
  use`, one domain per PR, `just check` green per phase — keep this recipe for all
  future structural work, including prelude retirement and eventual crate surgery.

Net: the file-size program captured most of its available agent value in 14s and
will capture the rest in 15b.7–15b.10 (the genuinely large production files among
them). Everything after that is cost without corresponding agent gain.

## 4. Options considered

**A. Keep going: 15c/15d until zero files >1500 (or tighten to ≤1000/500).**
Rejected as the standing program. Evidence: 45 files remain after 20 splits; test
files are poor split targets; each round multiplies navigation surface (381 → 665
files and climbing) while leaving the 5m46s cascade, prelude churn, docs, stubs,
lints, MSRV, deps, and error typing untouched. Keep only as a reactive rule (split
on conflict/context/churn evidence, §5.1), never as a quota.

**B. Jump straight to crate surgery (split `sase_core` into bead/scan/editor/query/
artifact/fleet crates).** Correct eventual direction (only cure for the rebuild
cascade) but wrong as the *next* step. It is the highest-risk change on the list:
public paths, `sase_core_py` imports (95 module-path refs today), gateway/LSP root
imports, release-plz versioning, and wheel contents move together. Without the
agent-interface tier first (stubs to pin the Python surface, prelude retirement to
shrink the name space, contract tests to pin HTTP behavior), agents performing the
surgery will navigate by stale docs with no generated safety nets. Sequence it
after, with a design doc.

**C. Agent-interface package first (.pyi, docs/guide, fast loop, prelude, drift
tests), then lints/deps/errors, crate surgery last.** Recommended (§5). Every item
is small, compiler- or CI-verified, parallelizable per domain, and directly serves
dimensions (2)–(6). It also de-risks B.

**D. Tooling-only alternative (codegen the bindings, e.g. macro-collapse the
`dict → serde → core → json` shape + version getters, auto-generate registration).**
Worth doing *inside* C (the audit's `macro_rules!` suggestion for the 74 getters
and dominant body shape stands), but not as a substitute: codegen without stubs,
docs, fast loop, and prelude retirement leaves agents generating code they cannot
typecheck from Python, navigate by stale maps, or verify quickly. Adopt the macros
incrementally per domain during C; do not make codegen its own epic first.

## 5. Recommended solution (sequenced)

### 5.1 This week: close out and freeze the treadmill

- Land 15b.7–15b.10 as scoped: `provider_usage/tests.rs` (split tests *with* their
  production code, not as an isolated line exercise), `editor/directive.rs`,
  `runner_capacity.rs`, `notification_store_parity.rs` (fold in the R16 rename to
  `*_golden.rs` and delete the dead mirror instructions rather than rehousing
  them).
- Then record the moratorium explicitly (AGENTS.md one-liner + epic-bead note):
  **no new line-count epic until a file demonstrates harm** — a merge conflict
  between unrelated features, a real task that overflowed context, or churn
  coupling two domains. The `<=1500` rule becomes a smell threshold for review,
  not a work queue.

### 5.2 Next: the agent-interface tier (in this order — each is hours to days)

1. **`.pyi` generation + CI gate (R8 core).** Generate stubs from `#[pyfunction]`
   signatures (pyo3 stub-gen or a small AST extractor run in `check.sh`), check the
   generated file in, fail CI on drift. Delete the hand-maintained `//!` manifest
   progressively as the stub becomes the source of truth. Success metric: a
   Python-writing agent gets completions/signatures for all ~830 bindings.
2. **Docs truth + agent guide (R5/R6).** README: `just check` Build & test, four
   crates, delete Phase-status/Packaging/`SASE_CORE_BACKEND`-default sections, fix
   `PYPI_README.md`, sweep `sase_100` → `sase`. AGENTS.md: conventions
   (`*Wire`/`*_WIRE_SCHEMA_VERSION`/`core_*`), crate ownership map, add-core-function
   + expose-to-Python recipe, "never bare `cargo`, use `just check` / `just fast`"
   rule, release-plz note (already there). Success metric: grep for "adding a new"
   returns a maintained guide, not zero hits.
3. **`just fast` + dev profile (R3).** `cargo check --workspace --all-targets`
   recipe, `[profile.dev] debug = "line-tables-only"`, documented in AGENTS.md.
   Success metric: inner loop 45s-class on the reference machine; `just check`
   stays the pre-commit gate.
4. **Prelude retirement (R9).** Delete the 2,256 root re-exports never consumed via
   root; migrate gateway's ~185 and LSP's ~27 root-path uses to module paths;
   optionally keep a deliberate `pub mod prelude`. Compiler-verified per crate.
   Success metric: `sase_core/src/lib.rs` stops appearing in unrelated feature
   diffs.
5. **Drift-test trio (R15–R17).** Gateway route-vs-snapshot assertion with
   allowlist; parity→golden rename; `VERSIONS.md` registry + bump test. Each is a
   single test plus docs; together they convert three human-enforced invariants
   into CI.

### 5.3 Then: raise the floor in one batch (R10–R14)

Workspace `[lints]` (warn-level `too_many_lines`, `cognitive_complexity`,
`missing_panics_doc`, `unwrap_used`; `missing_docs` on `sase_core`), parameter
objects for the 42 `too_many_arguments` sites (the `*Wire` request types are the
natural shape), MSRV → 1.89, `reqwest 0.11 → 0.12`, `pyo3` upgrade with the
`useless_conversion` allow deleted, `cargo deny`, and the typed-error/unwrap pass
on exactly the files the audit names (no expansion). Land after 5.2 so lints apply
to split trees and stubs pin the surface being refactored.

### 5.4 Standing direction: crate surgery by design (R19)

When 5.2's fast loop is measured and found wanting for the common edit, commission
a short design doc (seams, new crate list, import-migration order, release-plz and
wheel implications, Python-surface pin via the 5.2 stubs), then execute seam by
seam with the proven facade + per-phase-green recipe. Not a ten-worker epic chain.

## 6. Risks, caveats, and what was not re-measured

- Line counts use `wc -l` on the linked checkout; the audit's `max_width = 80`
  inflation note applies equally, so *rankings and deltas* are the finding, not
  absolute widths.
- Timings (5m46s/45s/12s/31s) are the audit's warm Apple Silicon figures, not
  re-timed here; the ratio, not the seconds, motivates §5.2.3.
- Counts of `pub use`/`pub mod` (107/107), allows (42/8), versions in flight, and
  CI matrix were re-grepped at `b7af6b7`; test outcomes and doc coverage (34%)
  were not re-run/re-counted — no claim here depends on them changing.
- Single-author velocity (~430 commits/month) constrains any restructure to
  mechanical, fast-landing steps; that constraint favors C over B as the next move
  and is why §5.1 freezes the quota chain explicitly.
- This report deliberately does not consult the sibling `__cld` / `__gem` swarm
  reports; convergence or disagreement will be for the lead researcher to
  adjudicate.

## 7. Appendix: verification log (this session)

- `sase repo open research` + `sase repo open sase-core` (audit trail recorded).
- Audited reads: `research:202609/sase_core_maintainability_audit/sase_core_maintainability_audit.md`
  (head + tail windows covering §§1–7).
- Beads: `sase bead show sase-14s` (CLOSED, 10/10) and `sase-15b` (IN_PROGRESS,
  6/10; .7–.10 named above).
- Core @ `b7af6b7`: 665 `.rs` files / 381,369 lines; 45 files >1500; top
  `provider_usage/tests.rs` 3368 → `bead/wire.rs` 1893 at #24; `sase_core_py/src`
  ~30 domain dirs, `lib.rs` 736 lines, `register_*` per-domain calls confirmed;
  `server/` 8 files max 782; `sase_core/src/lib.rs` 107/107; no `.pyi`; no
  `[lints]`; MSRV 1.78; `reqwest 0.11`; `pyo3 0.22`; allows 42/8; CI matrix
  ubuntu + macos; reap guard fixed; `justfile` without `fast`; profiles without
  `[profile.dev]`.
