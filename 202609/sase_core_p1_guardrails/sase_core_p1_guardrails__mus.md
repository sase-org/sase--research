# P1 guardrails: should we implement them? (independent assessment)

**Researcher:** mus · **Date:** 2026-09-24 · **Question:** are the recommendations in
`P1: guardrails (one epic; before any further restructuring)` of
`sase_core_agent_maintainability.md` worth implementing, and if so, with what changes?

**Independence note:** this report was written without opening the `__cld` / `__gem` /
prior `__mus` swarm reports. I read only the consolidated base document
(`sase_core_agent_maintainability.md`, §7 P1 plus §§4–6 for context) and verified
claims directly against the `sase-core` checkout (`eef7ca4`) and the sase checkout in
this workspace.

**Sources inspected:**
- Consolidated report §7 P1 (7 checks + 4 "also in P1" items), §§4.2–4.3, §4.6–4.8, §6 option E.
- `sase-core` @ `eef7ca4`: `crates/sase_core_py/src/lib.rs` (90 lines),
  `prelude.rs` (1,107 lines), `scripts/check.sh`, `justfile`, `AGENTS.md` (109 lines),
  `CLAUDE.md`/`GEMINI.md` shims, `docs/`, `crates/sase_gateway/contracts/`,
  `crates/sase_core/tests/` (18 entries, mostly `*_parity.rs`), schema-version
  references (216 files), `//!` coverage spot-check.
- sase side: `tools/validate_sase_core_rs` (2,786 lines), `tools/check_sase_core_rs_bindings`
  (295 lines) — both still present.

## Bottom line

**Yes, implement P1 — but not as written.** The direction (make invariants
machine-checked before restructuring) is right, and five of the seven gates are
cheap text-level checks with high agent-leverage. As written, though, the plan is
stale in two places, oversized for "one epic," and contains two scope errors that
would make the epic fail or drag:

1. **Stale:** the manifest deletion and the feature-unification gate the plan
   assumes are future work have **already landed** (lib.rs is 90 lines, not 736;
   `check.sh features` + `sase_workspace_hack` exist). The plan's inventory and
   `-p` language needs updating, not re-implementation.
2. **Oversized:** flake burn-down (5 load flakes) and cross-repo sase consumption
   do not belong in the same epic as 7 fast text gates. They have different skills,
   different verification (nondeterministic vs deterministic), and different owners.
3. **Scope errors:** the size ratchet as specified (raw lines ≤1,500, no test
   exemption) punishes the inline-test pattern the same report says to keep (§4.8);
   and the "move items" tool should be built on first P2 need, not speculatively in P1.

**Recommended solution in one paragraph:** run a rescoped **P1a** (core-side,
text-level, deterministic: size ratchet on non-test lines, registration
completeness, generated inventory + staleness gate, schema registry + test,
module-docs staleness, graph allowlist, prelude freeze, route↔snapshot test —
each with an actionable message and a seconds-scale budget) **before** P2; move
flake burn-down and sase-side consumption of the inventory into a parallel
**P1b** with per-item exits; drop the parity rename as a gate (do it
opportunistically or not at all); defer the move-items tool to the first P2 phase
that needs it. Details and per-check amendments are below.

## What P1 proposes (for reference)

| # | Check / item | Rule as written |
|---|---|---|
| 1 | File-size ratchet | Per-file budget over 1,500 lines; budgets only shrink; new files ≤1,500; warn at 1,200 |
| 2 | Registration completeness | Every `#[pyfunction]` in exactly one `wrap_pyfunction!` in its domain `register_*` |
| 3 | Generated binding inventory | Delete `//!` manifest; generate names/`#[pyo3(name)]`/params/docs from syn signatures; gate staleness; sase's three hand lists consume it |
| 4 | Schema-version registry | One `WIRE_SCHEMA_VERSIONS` table + test that every `*_WIRE_SCHEMA_VERSION` is in it; one exporting binding; Python reads it; per-value getters retire |
| 5 | Module docs | New modules start with `//!`; `docs/MODULES.md` generated from them grouped by layer, gated |
| 6 | Acyclic module graph | Fail on any new `crate::<mod>` edge closing a cycle; SCC allowlist only shrinks; root forwarder counts as edge |
| 7 | Root-prelude freeze | Root `pub use` count may only fall |
| 8 | Route↔snapshot test | Gateway route ↔ contract-snapshot test |
| 9 | Parity rename | `*_parity.rs` → `*_golden.rs`, delete "mirror this" comments |
| 10 | Flake burn-down | `sase-15d/e/f/g/h` |
| 11 | Move-items tool | One tested syn-span tool if P2/P3 go ahead |

All behind one `./scripts/check.sh structure` step in `just check`, fast and text-level,
with actionable failures.

## What changed since the consolidated report (HEAD `8886406` → `eef7ca4`)

These change what P1 needs to do — the plan is not wrong, but it describes a tree
that no longer exists in two spots:

- **Manifest: already deleted.** `sase_core_py/src/lib.rs` is 90 lines with the
  explicit comment "Nothing parses this header, so do not grow it back into a
  binding list." The report's "664 of 736 lines" figure is gone. So P1 item 3's
  "delete the manifest" is done; what remains is the *generate + gate + consume*
  half, which is the harder half (cross-repo). The plan should say so.
- **Feature unification: already landed.** `check.sh features` (tool-free
  `cargo tree`/`cargo metadata` drift gate) and `sase_workspace_hack` exist, and
  the `-p` scope comment in `check.sh` now explains the invariant. The P0 exit
  "no-edit `-p` switch ≤5 s" mechanism is in place.
- **Partially landed:** `AGENTS.md` is 109 lines (was 36), `CLAUDE.md`/`GEMINI.md`
  shims exist, `check.sh modules` / `just modules` exists (fresh-by-construction
  module map). But `docs/MODULES.md` as a checked-in gated file does not exist —
  only the generator command. So item 5 is half-done.
- **Not landed (verified):** no `check.sh structure` subcommand; `*_parity.rs`
  files still named parity (13+ files); no `WIRE_SCHEMA_VERSIONS` global table
  (only a per-domain `SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS` precedent); no graph
  check; no prelude freeze; ~37 files still >1,500 lines (vs 41 at report time —
  same order); `prelude.rs` still 1,107 lines; sase-side hand lists still present
  (`validate_sase_core_rs` 2,786 lines).

Net: P1a work is smaller than the plan implies on items 3 (delete done) and 5
(generator done), unchanged elsewhere.

## Per-item assessment

### 1. File-size ratchet — implement, with one amendment

**Worth it: yes.** This is the cheapest guardrail and the one that protects the
finished split epics. New files are still born large (`agy.rs` arrived at 1,204
lines per the report; current max 2,723). Without a ratchet, P2/P3 edits regrow
what sase-14s/15b cut. Cost is a ~30-line script plus a checked-in budget file.
Runtime is milliseconds.

**Amendment (important): measure non-test lines, or exempt inline `#[cfg(test)]`.**
At HEAD ~25/37 oversized files are oversized only because of inline tests (report
§4.7; my spot-check confirms the pattern persists). The same report says inline
tests should stay next to private code (§4.8, "moving inline tests to tests/" is
explicitly "not worth a campaign"). A raw-line ratchet therefore punishes the
recommended pattern and will push agents to move tests out just to satisfy the
gate — the opposite of the intent. Options: (a) count with `#[cfg(test)]` modules
stripped, or (b) two budgets (code vs test). Either is a small addition to the
script. Keep "budgets only shrink, new files ≤1,500 (non-test), warn at 1,200."

### 2. Registration completeness — implement as written

**Worth it: yes, highest value-per-hour in P1.** A missing registration is a
runtime `AttributeError`, invisible to the compiler — exactly the failure class
agents handle worst (§2.2 P3). With the manifest deleted, there is one fewer
redundant list to catch the omission by accident, so this check becomes *more*
important, not less. Text-level implementation (parse `#[pyfunction]` /
`#[pyo3(name=…)]` fns vs `wrap_pyfunction!` refs per domain module) is a day's
work including the actionable message ("`py_foo` defined in `beads/mod.rs` is not
registered in `register_beads`; add `wrap_pyfunction!(py_foo, m)?`"). Edge cases
to pin in the spec: `#[pyo3(name)]` renames, non-exposed helpers without the
attribute, and the `query/`-style shared modules. No cross-repo dependency.

### 3. Generated binding inventory — implement in two halves, fix the promise

**Worth it: yes, but split it.** Deletion is done; generation + staleness gate is
core-side and deterministic (syn-parse signatures → checked-in inventory file,
gate diffs it). That half is P1a and unblocks everything downstream. Consumption
(sase's three hand lists reading the same artifact) is sase-side, needs format
stability, versioning, and sase-owner review — that half is P1b and must not gate
P1a or P2.

**Amendment:** do not promise `.pyi`/mypy leverage in this item. The consolidated
report's own §4.5 correction stands: as long as sase calls through
`require_rust_binding(name) -> Any`, stubs type-check ~1% of calls. The inventory's
P1 value is *existence-checking* (replacing hand lists), not typing. Typed access
stays a P2 sase-side item. Write the spec that way so the epic is not judged on
type-coverage it cannot deliver.

### 4. Schema-version registry — implement, narrowed

**Worth it: yes.** Stale version copies caused real incidents (`a509dcc`,
`sase-oq` hardcoded 5-vs-6). The `procs` crate already shows the pattern
(`SUPPORTED_PROC_WIRE_SCHEMA_VERSIONS`), so this is generalizing a proven local
solution, not inventing one. 216 files reference versions — the drift surface is
large and hand-checked today.

**Amendments:** (a) phase the getter retirement: the registry + completeness test
("every `*_WIRE_SCHEMA_VERSION` appears in the table") and the single exporting
binding land in P1a; retiring 74–88 per-value getters is a mechanical follow-up,
not part of the gate's exit criteria — requiring full retirement in one epic
re-risks a guardrail epic with a migration. (b) Python switching to the export is
P1b (same cross-repo reasoning as item 3). Exit for P1a: table exists, test fails
on an unregistered constant with the constant's name and file in the message.

### 5. Module docs (`//!` + generated `MODULES.md`) — implement, lightweight

**Worth it: yes, cheap.** The generator (`check.sh modules`) already exists; the
remaining work is checking in the output, grouping by layer, and gating
staleness + new-file `//!` presence. Current coverage is already ~86% in my
sample (362/423 files with `//!`), so a retroactive full-coverage gate would be
gratuitous churn — gate *new files* and *staleness*, not the backlog. Dependency
to note: "grouped by layer" needs the P0 ownership table; if P0.5 slips, ship
ungrouped first and add grouping when the table lands. Do not block P1a on it.

### 6. Acyclic module graph — implement, with hardening

**Worth it: yes, as P2/P3 insurance.** Six cycles closed by 1–3 single-use
back-edges plus the root-forwarder knot (§4.6) are exactly what P2 keystone cuts
will fix; without a guardrail, concurrent features re-close them at 430
commits/month faster than P2 opens them. The allowlist-may-only-shrink design is
right.

**Amendments:** (a) do not implement edge extraction with regexes over
`crate::` paths — the report's own method section admits the analysis was
regex/brace-aware scripts, and productionizing that invites false positives
(`crate::{a, b}` groups, root re-export mapping, `#[cfg]`-gated edges). Use a
syn-based extractor or `cargo`-emitted metadata, and run the new gate in
warn-then-deny (one cycle of warnings before hard failure) to flush out parser
gaps without blocking the tree. (b) The "empty allowlist" exit belongs to P2
(item: cut keystone edges), not P1 — P1's exit is "allowlist exists and no new
cycle passes."

### 7. Root-prelude freeze — implement immediately, sunset it

**Worth it: yes, trivial cost, real protection.** One integer (`pub use` count in
`lib.rs`, currently ~107 blocks) that may only fall. It protects the #1 churn
file during the exact window when P2 rewrites its ~700 consumers. Add the sunset
clause the plan omits: the check is deleted when the prelude itself is deleted
in P2 — otherwise it becomes permanent gate cruft guarding a file that no longer
exists.

### 8. Gateway route ↔ contract-snapshot test — implement

**Worth it: yes.** Small, deterministic, high-signal: sase-14s.5 did this diff by
hand, and `contracts/` (`api_v1`, `api_fleet_v1`) plus `contract.rs` give it a
natural home. No amendments except: keep it in P1a (it is a drift test, same
family), and have it print the missing/extra route names on failure.

### 9. Parity → golden rename — drop as a gate, allow opportunistically

**Weakest item in P1; do not gate on it.** The value is removing "mirror this"
comments that invite copy-paste drift, but the rename itself touches 13+ test
files, churns blame/history, and verifies nothing. If the comments are the
problem, delete the comments (one small patch). Rename files only if the team
wants the vocabulary — opportunistically, file by file, not as an epic exit
criterion.

### 10. Flake burn-down (5 load flakes) — move out of the guardrails epic

**Worth doing, wrong container.** Telemetry concurrent-writers, three
`sudo_runner` flakes, and gateway fleet-route deadlines are load-dependent,
nondeterministic, and each needs its own reproduction + fix + soak
verification. Bundling them into a deterministic text-gate epic guarantees one of
two outcomes: the epic waits weeks on soak time, or the flakes get "fixed" by
re-running until green. Move to P1b as five separately-tracked fixes with
per-flake exits (repro + fix + N clean gated runs), possibly with quarantine
marking first so they stop poisoning the verify signal while the fixes land.

### 11. Syn-span "move items" tool — defer, do not pre-build

**Defer to first P2 need.** Building a tested refactoring tool speculatively,
before the first P2 phase has concrete move operations to drive its requirements,
risks building the wrong tool. State the intent in P1 ("P2 phases will share one
move tooling rather than per-phase scripts") and build it when P2.1 scopes its
first moves.

## Cross-cutting points

- **"One epic" is too big as written.** Deterministic text gates (items 1–8
  core-side) are days of work with second-scale verification. Flakes (10),
  sase-side consumption (3b, 4b), and getter retirement are weeks with
  nondeterministic or cross-repo verification. One epic with one exit criterion
  cannot cover both. Split as P1a/P1b below.
- **`structure` step budget:** the whole point is a fast pre-restructure signal.
  Specify it: `check.sh structure` runs in seconds (no `cargo`, text/syn only),
  and each check prints the file, the rule, and the exact fix (which line to add,
  which command regenerates the artifact). The report says "actionable failure
  messages" — enforce it per check in review.
- **Ordering holds: guardrails before restructuring.** Items 1, 6, 7 are
  explicitly P2/P3 preconditions (ratchet stops regrowth, graph allowlist frames
  keystone cuts, prelude freeze protects the deletion). P1a must land before P2.1.
  Nothing in my verification contradicts the E-before-F-before-G sequence (§6);
  I would only add that P1a does not need to wait for the P0 instruction-delivery
  half (different files, different owners) — run them in parallel.
- **What I did not verify:** wall-time cost of the `structure` step (no gate
  exists to time); Codex/Muse instruction-loading (same gap the report notes);
  exact false-positive rate of a syn vs regex graph extractor (recommendation
  above hedges it with warn-then-deny).

## Recommended solution

**Adopt P1 with the rescope below. Do not adopt it verbatim.**

**P1a — core-side guardrails (one epic, before P2; deterministic, text-level):**
1. Size ratchet on **non-test** lines (budgets file, new files ≤1,500, warn at 1,200).
2. Registration completeness per domain module, with fix-instructing message.
3. Generated binding inventory (core side) + staleness gate. Manifest deletion
   already done — do not re-plan it.
4. Schema-version registry + completeness test + single exporting binding.
   Getter retirement follows mechanically, not as an exit.
5. `docs/MODULES.md` checked in, staleness-gated; new-file `//!` required.
   Layer grouping added when the P0 ownership table lands.
6. Graph allowlist (syn-based extractor, warn-then-deny for one cycle;
   root forwarder counted as an edge). Exit: allowlist exists, no new cycles.
7. Prelude count freeze, with written sunset on prelude deletion.
8. Route ↔ snapshot test.
- Step: `check.sh structure`, seconds-scale, in `just check`, every failure
  naming file + rule + fix. Exits are per-item above; epic exits when all eight
  gates run in the step.

**P1b — parallel track (separate exits, does not block P2.1):**
- Sase consumes the inventory artifact (retire the three hand lists).
- Python reads the schema export (retire per-value getters gradually).
- Five flakes fixed individually with soak exits; quarantine first.

**Explicitly out:** parity rename as a gate (delete the comments if they sting;
rename opportunistically); speculative move-items tool (build on P2.1 demand).

**Why this beats as-is:** P1a keeps the "before restructuring" safety property
with a shippable size and deterministic verification; P1b stops the
nondeterministic and cross-repo work from holding P2 hostage; the two amendments
(test-line counting, warn-then-deny graph) prevent the gates from punishing
recommended patterns or misfiring on parser gaps. Expected cost: P1a is days
(mostly items 3, 4, 6); P1b is weeks dominated by flakes, as it should be —
and visible as such instead of hidden inside "one epic."
