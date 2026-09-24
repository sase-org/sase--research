# sase-core P1 guardrails: implement a trimmed, redesigned P1, not the plan as written

**Researcher:** cld · **Date:** 2026-09-24

**Evaluated:** §7 "P1: guardrails (one epic; before any further restructuring)" of
`research:202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md`. That report was consolidated on
2026-09-21 against sase-core `8886406`.

**Measured at:** sase-core `eef7ca4` (master, 29 commits after `8886406`, 23 of them touching Rust) and sase master
`075225d53`. Static analysis used Python scripts over `git show`/the working tree. Each gate design was replayed over
every Rust-touching commit in `8886406..eef7ca4`. One compiler experiment ran on a `git archive` copy of the real tree
(§3.2).

---

## 0. Bottom line

**Verdict: yes, implement P1, but a smaller, redesigned version.** About a third of the plan is right as written, a third
needs redesign, and a third should be dropped or moved to P2. The case for guardrails is stronger now than when the
report was written. In the three days since then, with P0's new `AGENTS.md` rules already in force, the tree drifted in
exactly the ways P1 targets:

- **Size.** Rust lines grew by 12,650 (+3.3%). Files over 1,500 lines went from 41 to 44. 16 of the already-oversized
  files grew, and one new file was born at 1,517 lines.
- **Coupling.** A new module, `agent_clan_record` (`7fc3501`, 09-22), closed a new cycle with `agent_scan`, so the
  `agent_scan`/`agent_runtime` knot grew from 2 to 3 modules.
- **Hubs.** The prose-only "do not add root names or `core_*` aliases" rule leaked: root re-exports went 2,674 → 2,677,
  and aliases 654 → 657.
- **Flakes.** All five sase-core flakes named in P1 (`sase-15d`–`15h`) are still open. `sase-15g` collected 4
  corroborations in about 2 days, and a new one was filed (`sase-17n`).

**The plan has three problems that the evidence exposes:**

1. **The registration-completeness gate is redundant: the compiler already enforces it.** Bindings are private (or
   `pub(crate)`) functions in private modules, so rustc's `dead_code` lint flags any `#[pyfunction]` that no
   `wrap_pyfunction!` references. `just check` runs clippy with `-D warnings`, so the omission fails the gate. I
   verified this on a copy of the real tree: deleting the registration of `py_bead_snooze` fails
   `check.sh clippy -p sase_core_py` with `error: function 'py_bead_snooze' is never used`. This covers 834 of 839
   bindings. The source report's §4.3 row and sase-core `AGENTS.md` (recipe step 4, "The compiler does not check
   this") are both wrong.
2. **The size ratchet as written would fail most commits.** Replayed over the 23 post-report Rust commits, the rule
   "budgets only shrink, new files ≤1,500" fails **17 of 23 (74%)**. Counting non-test lines only, it still fails 8 of 23
   (35%). A redesigned ceiling fails **1 of 23 (4%)**, and that one is a real signal: `provider_usage/store.rs` grew by
   348 non-test lines to 2,254 in one commit.
3. **Three items would rebuild the shared hubs the report says to delete, and one would remove a safety check:**
   - a checked-in generated binding inventory, which about 41% of feat/fix commits would have to edit
   - a hand-kept `WIRE_SCHEMA_VERSIONS` table: there are 165 schema constants, 74 of them added in the last month
   - a committed `docs/MODULES.md`
   - "Python reads the registry instead of its copies" removes sase's reader-side version pins. Those pins are the
     check that caught `sase-oq`.

**Recommendation (details in §5).**

- **A. One small structure gate.** A new `./scripts/check.sh structure` step (<0.5 s) with four checks: a redesigned size
  ceiling, a module-cycle ratchet, a hub-count freeze, and module-root `//!` summaries. Add the route↔contract test and
  break the new cycle. This is a 2-phase epic, or one medium task.
- **B. Burn down the flakes as independent task launches now,** not as epic phases.
- **C. Fix the false "compiler does not check registration" text in `AGENTS.md` today.**
- **D. Optional, sase-side:** replace the schema registry with a check that compares sase's mirror constants against
  same-named core getters, in both the dev and floor-smoke environments.
- **E. Move to P2:** the generated inventory and stubs, the syn "move items" tool, and the `*_parity.rs` rename.
- **F. Drop:** the registration gate, `MODULES.md`, and the 1,200-line warning.

---

## 1. What changed since the plan was written

The P0 epic **`sase-165`** landed all seven phases on 09-22. The land agent is closing three small gaps
(`plan:202609/sase_core_p0_land_gaps.md`). Several P0 outcomes change the P1 picture:

| P0 outcome | Effect on P1 |
|---|---|
| The `//!` binding manifest was **deleted** (`035851e`); "nothing parses it" (P0 plan) | P1's "delete the manifest" is done. Its "generated inventory replaces it" half has no consumer (§3.3) |
| `just modules` prints every top-level module's `//!` line, "fresh by construction"; `check.sh` says "P1 decides whether to commit a generated map" | A committed `MODULES.md` would add a staleness gate for no new information (§3.5) |
| All 114 top-level `sase_core` modules now have a `//!` summary | A module-root doc rule starts green and costs one regex |
| `AGENTS.md` (97 lines) now reaches agents. It says: import by module path, add no root `pub use` names or `core_*` aliases, and keep new files ≤1,500 lines | These are P1's rules in prose form. §3.1 and §3.7 measure how well prose alone held |
| cargo-hakari workspace-hack plus a `features` drift gate (`1d129cd`) | Precedent for the P1 step: a Python-in-`check.sh` gate with its own CI step |
| MSRV is 1.89 and true | Removes one "invisible invariant" from the §4.3 list |

The P0 plan's "Out of scope" list names P1 as: size ratchet, registration and schema-registry gates, generated binding
inventory, module-doc gate, flake burn-down. That list matches the report's P1 table, which is what this report
evaluates.

---

## 2. Item-by-item verdicts

| # | P1 item | Verdict | One-line reason |
|---|---|---|---|
| 1 | File-size ratchet | **Keep, redesign** | Drift is real, but "budgets only shrink" on total lines fails 74% of commits and penalises inline tests. Use non-test lines, a 2,000-line ceiling, and grandfathered per-file ceilings: 4% |
| 2 | Registration completeness | **Drop** | Already enforced by `dead_code` under clippy `-D warnings` (verified). Fix the docs instead |
| 3 | Generated binding inventory (sase's lists consume it) | **Move to P2** | Nothing consumes it. sase's lists are *consumer requirements* checked against the built module, so feeding them the supplier's list would make the check tautological. A checked-in inventory would be a hub for about 41% of commits |
| 4 | Schema-version registry | **Rework, move to sase, optional** | A hand table of 165 fast-growing constants is a new hub. Python must *keep* its constants as reader pins. The valuable part is a sase-side comparison (52 pairs today) |
| 5 | Module docs + generated `MODULES.md` | **Keep the root rule, drop `MODULES.md`** | Module roots are 114/114 documented. `just modules` is already fresh by construction |
| 6 | Acyclic module graph | **Keep** | A new cycle appeared within 2 days. It is cheap, and it is P2 step 4's exit criterion and P3's precondition |
| 7 | Root-prelude freeze | **Keep, and extend to `core_*` aliases** | The prose rule leaked +3 names and +3 aliases in 3 days. The check is a counter comparison |
| 8 | Route ↔ contract-snapshot test | **Keep, low priority** | `AGENTS.md` admits "no test ties those two together". Routes are rarely added now (the router has 1 commit since 07-21) |
| 9 | `*_parity.rs` → `*_golden.rs` rename | **Move to P2 or drop** | Cosmetic, touches 14 actively edited test files, and conflicts with concurrent epics |
| 10 | Flake burn-down (`sase-15d`–`15h`) | **Do now, as tasks** | Highest agent-time payoff in P1. These are independent root causes, not structure work |
| 11 | syn "move items" tool | **Move to P2 phase 0** | Only needed if P2/P3 run. The report itself makes it conditional |

---

## 3. Evidence per item

### 3.1 File-size ratchet: keep the goal, change the rule

**Drift since the report** (`8886406` → `eef7ca4`, 3 days):

| Measure | `8886406` | `eef7ca4` |
|---|---|---|
| Rust lines | 381,675 | 394,325 (+12,650) |
| Files >1,500 total lines | 41 | 44 |
| Files that crossed 1,500 | — | `provider_policy/tests.rs` 1,500→1,986; `provider_usage/mod.rs` 1,466→1,620 (all non-test); new `agent_clan_record.rs` 1,517 |
| Over-1,500 files that grew | — | 16 of 41. The largest: `provider_usage/store.rs` +348 (→2,254), `project_spec.rs` +252, `query/tests.rs` +192, `bead_event_parity.rs` +112 |
| Largest file | 2,699 | 2,723 (`agent_ownership/planner.rs`) |

The prose rule "Keep new files at or under 1,500 lines" was in `AGENTS.md` from 09-22, and it was breached at least
twice within a day. So a mechanical check is justified.

**The rule as written is too strict.** "A checked-in budget per file currently over 1,500 lines. Budgets only shrink;
new files must be ≤1,500" means that *any* growth of any of 44 files fails the gate. The replay over all 23
Rust-touching commits since `8886406`:

| Rule | Commits failing |
|---|---|
| **As written** (total lines, per-file budget, shrink-only, new ≤1,500) | **17 / 23 (74%)** |
| The same, counting non-test lines only (code before the first `#[cfg(test)] mod`) | 8 / 23 (35%) |
| Non-test lines; files over 1,500 may grow at most +50 per commit | 3 / 23 (13%) |
| **Recommended:** non-test lines, a 2,000 ceiling for every non-test source file, and grandfathered files capped at their baseline rounded up to the next 250 | **1 / 23 (4%)** |

The one failure under the recommended rule is `cfe1902`, which took `provider_usage/store.rs` from 1,906 to 2,254 non-test
lines. That is exactly the kind of commit a size gate should stop.

**Why the rule as written misfires:**

- **It counts inline tests.** The report says 25 of the 41 oversized files are oversized only because of inline tests,
  and that these "should stay next to the private code they test". A total-lines ratchet fails a feature *for adding
  tests*. At HEAD only 13 source files exceed 1,500 **non-test** lines. `agent_clan_record.rs` is 1,517 lines in total
  but only 793 non-test.
- **Shrink-only forces a split into most feature commits.** Agents facing that will do one of three things: bump the
  budget, which kills the ratchet; split mid-feature, which is scope creep during a velocity of about 10 commits a day;
  or golf lines. The report itself says that further splits "should be driven by evidence, not a quota". A shrink-only
  budget is a quota.
- **"Warn at 1,200" is noise.** 80 files are already over 1,200 lines, and agents ignore warnings in a passing gate.
  Report that band from a metrics command instead.

**Where the 2,000 figure comes from.** It is Claude's default `Read` window. A file whose code fits in one read is the
reading unit P7 cares about. Keep `AGENTS.md`'s 1,500 as the *target* for new code, and make 2,000 the *gate*.

At land time, three files would be grandfathered: `editor/frontmatter.rs` (2,440 non-test lines, cap 2,500),
`config/axe.rs` (2,265, cap 2,500) and `agent_ownership/planner.rs` (2,142, cap 2,250). `provider_usage/store.rs` is now at
2,254, so it is either grandfathered at 2,500 or split first. Test-only files (`tests.rs`, `tests/`) get a separate cap
of 3,000 total lines; none exceeds it today (the largest is `bead_event_parity.rs` at 2,294).

### 3.2 Registration completeness: the compiler already does this

The P1 rule is "Every `#[pyfunction]` appears in exactly one `wrap_pyfunction!` in its domain's `register_*`". Its premise,
as stated in the report's §4.3 and in sase-core `AGENTS.md` step 4, is that the compiler does not check registration.
**That premise is false for this crate.**

- **Visibility.** All 839 bindings are private (776) or `pub(crate)` (65) functions inside private modules (`mod beads;`
  and so on in `lib.rs`), with no `allow(dead_code)` anywhere in `sase_core_py`. rustc's dead-code analysis therefore
  applies to every binding.
- **Probe crate (pyo3 0.22.6).** An unregistered private `#[pyfunction]`, an unregistered `pub(crate)` one, and one
  called only from a `#[cfg(test)]` test all failed `cargo clippy --all-targets -- -D warnings` with
  `function … is never used`.
- **The real tree.** On a `git archive` copy of `eef7ca4`, I commented out
  `m.add_function(wrap_pyfunction!(py_bead_snooze, m)?)?;` and ran `./scripts/check.sh clippy -p sase_core_py`. It
  failed with `error: function 'py_bead_snooze' is never used --> crates/sase_core_py/src/beads/mod.rs:713:4` in 104 s.
  `just fast` shows the same message as a warning, so an agent sees it in the inner loop too.
- **Today's state.** 839 bindings and 839 registrations, with no binding unregistered and none registered twice.
- **The only escape hatch:** 5 bindings are also called from other non-test code, so the lint would not fire if they
  were unregistered. They are `py_append_proc`, `py_prune_procs`, `py_read_procs_snapshot`, `py_update_proc` and
  `provider_routing_context_from_parts`. If anyone cares, the fix is tiny: move the shared body into a plain helper
  function that the binding calls.

A text-level registration gate would therefore duplicate the compiler for 99.4% of bindings and add a parser to
maintain. Drop it. **Do fix the docs**: `AGENTS.md` step 4 currently teaches agents that nothing catches the mistake,
which invites the hand-counting rituals the report found (sase-14s.1 counted "827 = 827" by hand).

### 3.3 Generated binding inventory: no consumer yet, and a hub risk

The P1 row says: "Delete the `//!` manifest. Generate the names, `#[pyo3(name)]`, parameter names and docs from the
syn-parsed signatures, and gate staleness. sase's three hand lists consume the same artifact."

- **Deletion is done** (P0, `035851e`). The P0 plan records that "nothing parses it".
- **sase's lists are requirements, not supply.**
  - `tools/check_sase_core_rs_bindings` scans sase's own `require_rust_binding("…")` call sites and checks those names
    against the **installed module**.
  - `tools/validate_sase_core_rs`'s `REQUIRED_BINDINGS` and its behaviour probes do the same, and the tool's docstring
    says feature detection "has to probe behavior".
  - If these consumed a core-generated list of what the core *provides*, they would check the core against itself.
  - The real redundancy is sase-side: the 333-name `REQUIRED_BINDINGS` list overlaps the call-site scan. That is a sase
    clean-up, not sase-core P1.
- **For agents, the source is already the index.** `rg 'name = "<python name>"' crates/sase_core_py/src` finds any
  binding in one step, because `#[pyo3(name)]` strings are literal.
- **A checked-in inventory is a hub.** The report measured that about 41% of sase-core feat/fix commits add a binding.
  Each of those would regenerate one shared file, and many agents commit in parallel to an unprotected master. This
  is the merge-hazard pattern the report warns about in §2.1.

The inventory's real use is **`.pyi` stub generation for typed Python access**, which the report already places in P2
(§4.5, P2.6). Build it there, generated at wheel-build or on-demand time rather than checked in. If an agent-facing
listing is wanted sooner, add a `just bindings` recipe that prints name → file, as `just modules` does. It is fresh by
construction and needs no gate.

### 3.4 Schema-version registry: the diagnosis is right, the design is wrong

The P1 design is: "One `WIRE_SCHEMA_VERSIONS` table plus a test that every `*_WIRE_SCHEMA_VERSION` constant is in it.
One binding exports it; Python reads it instead of its copies; the per-value getters retire over time."

**Four problems:**

1. **Python's copies are deliberate.** A sase constant such as `ARTIFACT_REF_WIRE_SCHEMA_VERSION = 5`
   (`src/sase/artifact_ref_wire.py`) states *which version this Python reader understands*. sase code compares incoming
   payloads against it, and `validate_sase_core_rs` compares the core's getters against its own expected values. If
   Python read the core's registry instead, a core bump would be accepted silently and misparsed later. The
   `sase-oq` failure ("probe requires schema version 5: got 6") was this check **working**: the linked core was ahead
   of sase's reader.
2. **A hand table would be a hot hub.** The tree has 165 `*SCHEMA_VERSION*` constants: 125 `*_WIRE_SCHEMA_VERSION`, plus
   40 store, index and min/max constants that the table rule would miss. On 2026-08-24 there were 91, so 74 were added in
   a month. A single hand-kept table would be edited by several commits a day.
3. **The incidents are cross-repo floor skew, and a core-side table does not close them.**
   - `sase-km` (canceled 08-14 as "one preventive gate", with 3 corroborations), `sase-kx`, `sase-wg` and `sase-10d`
     are all cases where a sase reader and the *published* core disagreed.
   - As `sase-km` put it, "floor gates probe binding names" but not schema versions.
   - Closing that gap is a sase floor-probe change.
4. **Literal versions in Rust tests are intentional.** There are 73 `assert_eq!(…schema_version…, N)` assertions and 25
   non-Rust fixtures carrying `schema_version`. These are goldens, meant to force a conscious update when a version
   changes, and a registry does not remove them.

**What would help (sase-side, no sase-core change):**

- Add one test or validator step that pairs each sase `*_SCHEMA_VERSION` constant with the same-named core getter
  (`FOO_WIRE_SCHEMA_VERSION` ↔ `foo_wire_schema_version()`) and asserts they are equal.
  - **52 of sase's 192 schema constants already pair by name** with one of the 85 core getters.
  - The rest are sase-owned schemas with nothing to compare.
- Run it in the dev environment, which catches `sase-oq`-style skew with a precise message, and in CI's floor-smoke
  venv (the minimum published wheel), which catches `sase-km`-style skew.
- A single `schema_versions()` binding can come later, if at all, to retire the 85 getters. It should be generated at
  build time and never hand-kept.

This is not sase-core structure work, so file it as a separate sase task. Given the owner's earlier triage of
`sase-km`, treat it as optional, and do it now only if another floor-skew incident happens.

### 3.5 Module docs and `docs/MODULES.md`

- **Top-level module roots:** 114 of 114 have a `//!` summary, and `just modules` shows no empty lines. All four modules
  added since P0 (`agent_clan_record`, `agent_session`, `fleet_agent_session`, `project_tag`) arrived documented, so
  copying the neighbours worked.
- **Per-file coverage is uneven:** `sase_core` 306/423, gateway 12/45, LSP 1/15. It is not worth a gate. The report
  itself rejects bulk doc campaigns.
- **Recommendation:** add one rule, "every top-level module root starts with a `//!` line", so `just modules` stays
  complete. Do **not** commit `MODULES.md`. `just modules` already answers "what lives where" without a staleness gate,
  and a committed map would be one more shared file that every new module must edit.

### 3.6 Acyclic module graph: keep it, since drift has already happened

I re-derived the graph with a text-level extractor. It handles `crate::<mod>` paths, `crate::{…}` groups, mapping of
root re-exports back to their modules, and the root forwarder; tests and comments are stripped. It reproduces the
report closely:

| | Modules | Edges | Multi-module SCCs |
|---|---|---|---|
| `8886406` | 112 | 147 (the report says 149) | 6: the artifact/bead/plan knot (6), `editor`↔`host_bridge`, `agent_launch`↔`hold_directive`, `agent_runtime`↔`agent_scan`, the fleet knot (5), `axe_chop`↔`config` |
| `eef7ca4` | 114 | 151 | The same 6, but `agent_runtime`/`agent_scan` became **`agent_clan_record`/`agent_runtime`/`agent_scan`** |

The cause is `agent_clan_record.rs`. It imports `crate::agent_scan::wire::{AgentClanContextWire, AgentMetaWire}`, while
`agent_scan/scanner.rs:154` and `agent_scan/index/query.rs:407` call
`crate::agent_clan_record::apply_clan_records_to_context`. The natural fix is to make it `agent_scan::clan_record`, a
small move.

**The gate.** Store today's SCC membership in a baseline. Fail when a new multi-module SCC appears or when an existing
SCC gains a member. Treat the root forwarder as an edge. Replayed over the 23 commits, it fires once (`7fc3501`). The
extractor is about 80 lines and takes about 0.1 s. It only earns its keep if P2 step 4 (cut the keystone edges) and the
P3 crate split remain the direction. They do in the report, and a cycle is far cheaper to refuse than to cut later.

### 3.7 Root-prelude freeze: keep it, and freeze the alias layer too

| Revision | Root `pub use` names | `core_*` aliases in `sase_core_py/src/prelude.rs` |
|---|---|---|
| `8886406` / `035851e` (the `AGENTS.md` rule lands) | 2,674 | 654 |
| `4b536cd` (tool_run observe) | 2,678 | 655 |
| `cfe1902` (adaptive admission) | 2,678 | 657 |
| `eef7ca4` | 2,677 | 657 |

The prose rule mostly held, but two or three commits after it still grew a hub: `4b536cd` (+4 names, +1 alias),
`4300166` (+1 name) and `cfe1902` (+2 aliases). A counter check (the count may not exceed the baseline) would have
caught each of them, and the fix is always the same: import by module path. The in-flight `sase-17m` rename renamed names in place without changing the counts, so the freeze does not get in
its way. Once P2 deletes both layers, the check becomes "must be 0".

### 3.8 Route ↔ contract-snapshot test: keep it, at low priority

- `AGENTS.md`'s "Add a gateway route" recipe says: "No test ties those two together, so do both."
- Route additions have been rare since the routes split: `routes/router.rs` has one commit since 07-21, while
  `contract.rs` has 24, mostly shape changes.
- **Recommended form: a behaviour test, not a text diff.** For every `(method, path)` declared in the mobile and fleet
  contracts, a request through the real router must not come back 404 or 405. Axum 0.7 cannot list its routes, so this
  is the direction a test can check. Use the existing `routes/tests/support.rs` state builders.

It is a small addition to the structure-gate epic's second phase.

### 3.9 `*_parity.rs` → `*_golden.rs`: move to P2 or drop

- There are 14 `*_parity.rs` files under `crates/sase_core/tests/`, plus about 10 "Mirrors the Python …" comments.
- The name is stale now that the Rust core is required, but it misleads no gate.
- The files are hot: `bead_event_parity.rs` grew by 112 lines in 3 days.
- Renaming them during the `sase-17m` rename epic invites conflicts.
- P2 rewrites these files' `sase_core::{…}` root imports anyway, so rename them in the same pass.

### 3.10 Flake burn-down: the highest-value item, but not a structure phase

| Bead | Test | Size | Signal |
|---|---|---|---|
| `sase-15g` | gateway fleet routes hit read/refresh deadlines under load | L | **+4** in about 2 days (`sase-16h.land`, `sase-170.land`, …), and the family grew (`fleet_enrollment_and_hello`) |
| `sase-15h`, `15e`, `15f` | `sudo_runner`: ETXTBSY on the fake sudo, an empty `worker.pid`, a leftover cwd | L / S / L | Likely one fixture-lifecycle cluster; worth one investigation first |
| `sase-15d` | telemetry concurrent writers | L | |
| `sase-17n` (new) | `tool_run` store `private_argv_is_not_serialized_on_queries` | — | Filed by `sase-17m.2.1.2` |

For agents, "a flaky gate is worse than a slow one" (the source report, §4.1). Each hit costs a ~5-minute rerun plus
triage turns, and phase agents keep filing corroborations. These are separate root causes needing load reproduction.
They are not text-level structure work, and as epic phases they would serialize behind unrelated checks. **Launch them
now as tasks** (`sase bead work <id>` from their TaskTriage gates), starting with `15g` and then the `sudo_runner` trio.
Make the KPI "no sase-core flake bead corroborated in the last 14 days" rather than "0 open", because new ones keep
arriving.

### 3.11 syn "move items" tool: belongs to P2

The report makes it conditional: "if P2/P3 go ahead". It replaces the brittle per-phase `/tmp/split_*.py` scripts that
the split epics used. No P1 item needs it. Make it P2's phase 0.

---

## 4. Design rules the P1 epic should follow

These rules turn the verdicts above into acceptance criteria.

1. **Set a friction budget and measure it by replay before landing.** Replay the gate over recent history, as §3.1
   does, and treat the two kinds of failure separately.
   - **Structural failures** (size, cycles) need a real code move. Budget them at no more than about 10% of
     Rust-touching commits, with every hit a real signal. Over the 23 replayed commits there were 2 (9%): `cfe1902`
     (`provider_usage/store.rs` at 2,254 lines) and `7fc3501` (the new cycle).
   - **Freeze failures** are fixed by changing an import path. The replay has 2–3 of them: `4b536cd` (+4 root names,
     +1 alias), `cfe1902` (+2 aliases), and possibly `4300166` (+1 root name).
   - Those are 3–4 distinct commits in total (13–17%). The rate should fall once agents learn the rule from the gate's
     message.
2. **Add no new hubs.** No check may require a shared, append-mostly file that ordinary feature commits must edit. The
   baseline file (a few grandfathered ceilings, the SCC list and two counters) changes only when a file is split, a
   cycle is cut, or P2 lowers a counter. Nobody should be *required* to lower a baseline; stale slack is harmless and
   can be reported by metrics.
3. **Use errors, not warnings, with messages that name the fix.** For example: "`provider_usage/store.rs` has 2,254
   non-test lines (limit 2,000). Move a cohesive group of items into a sibling module; see `AGENTS.md` 'Split a file'."
   Add that three-line recipe to `AGENTS.md`.
4. **Keep it text-level and fast.** Use Python stdlib only, following the `features` precedent, so it is portable to the
   macOS CI leg. Run it **first** in `check.sh all` and as its own CI step, because CI calls each `check.sh` step
   separately. The prototype of the size, docs and counter checks ran in 0.21 s over the tree, and the graph adds about
   0.1 s.
5. **Self-test it.** Put fixture-based unit tests alongside the existing `script-test` step, so a regex change cannot
   silently turn a gate into a no-op.
6. **Compute the baseline at land time.** `sase-17m` (the agent-session rename) is in progress, and its sase-core
   contract flip (`sase-17m.8`) is still open. A baseline taken at plan time will be stale by landing.

---

## 5. Recommended solution

**Implement P1, trimmed and redesigned as follows.**

### A. `sase-core` structure gate: a small epic (2 phases) or one medium task

**Phase 1, `structure-gate` (medium).** Add `./scripts/check.sh structure`, backed by a stdlib Python script with
unit tests, and a checked-in baseline. Wire it first into `cmd_all` and as a CI step.

| Check | Rule |
|---|---|
| Size ceiling | Non-test source files: at most 2,000 non-test lines (lines before the first `#[cfg(test)] mod`). Grandfathered files are capped at their land-time size rounded up to the next 250. Test-only files: at most 3,000 total lines. No warning tier |
| Module cycles | The multi-module SCCs among top-level `sase_core` modules must be a subset of the baseline, with no SCC gaining members. The root forwarder counts as an edge |
| Hub freeze | The root `pub use` name count and the `core_*` alias count must not exceed the baseline |
| Module-root docs | Every top-level `sase_core` module root has a `//!` first line |

Also in phase 1, update `AGENTS.md`:

- Correct recipe step 4: clippy's `dead_code` lint fails `just check` if a binding is not registered, unless other code
  also calls it.
- Add a "Split a file" recipe.
- Name the new gate in the `just check` step list, and add the size rule's non-test counting to Conventions.

*Exit:* `just check` runs the gate, and it passes at land. A replay over the previous 50 or more Rust commits shows
structural (size or cycle) failures in at most about 10% of them, each for a real reason. Every rule has a fixture
test.

**Phase 2, `route-contract-and-cycle` (small).**

- A gateway behaviour test: every contract `(method, path)` resolves through the real router (not 404 or 405).
- Fold `agent_clan_record` into `agent_scan` (for example as `agent_scan::clan_record`), so the cycle baseline starts
  from the report's original six SCCs and does not bless the new one.

### B. Flakes, in parallel and starting now

Launch `sase-15g`, then the `sudo_runner` cluster (`15h`/`15e`/`15f`), then `15d` and `17n`, as independent task
workers from their existing beads. They are not phases of A.

### C. Correct the docs now, whether or not A runs

The `AGENTS.md` step-4 sentence is a one-line docs fix. It removes a false belief that costs agents hand-counting
effort. If A is scheduled soon, fold it into phase 1.

### D. Optional, sase-side: a schema-version skew check (not the registry)

In sase, one check pairs each `*_SCHEMA_VERSION` constant with its same-named core getter (52 pairs today) and asserts
they are equal. Run it in the dev validator and in the floor-smoke venv. Keep Python's constants: they are the reader's
contract. Do this only if floor or schema skew recurs, consistent with the earlier `sase-km` triage.

### E. Move to P2

- The binding inventory and `.pyi` stubs, generated rather than checked in.
- The syn "move items" tool, as phase 0.
- The `*_parity.rs` → `*_golden.rs` rename, done in the same pass as the root-import rewrite.

### F. Drop

- The registration-completeness gate.
- The committed `docs/MODULES.md`.
- The 1,200-line warning.
- "Python reads the registry instead of its copies."

### Timing and sequencing

- **A can start now.** It adds new files plus one CI line, so it barely conflicts with `sase-17m`. Compute its baseline
  at land.
- **P2 should wait for `sase-17m` to land.** Both edit `lib.rs`, the prelude and the binding domains, and P2 is where the
  freeze counters and the cycle allowlist pay off.
- The report's rule "P1 before any further restructuring" still holds for this trimmed version. The freeze keeps P2's
  target from moving, and the cycle ratchet is P2 step 4's exit test.

### Expected effect

| KPI | Today | After A–C |
|---|---|---|
| Rust commits that re-grow a file past the reading unit | 16 of 41 oversized files grew in 3 days; 1 non-test jump of +348 | Blocked at 2,000 non-test lines (1 of 23 replayed commits) |
| New module cycles | +1 in 3 days | Blocked |
| Root names and `core_*` aliases added after the freeze rule | +3 and +3 | 0 |
| Agent beliefs that "the compiler doesn't check registration" | In `AGENTS.md` | Corrected |
| sase-core load flakes corroborated in the last 14 days | 6 open, `15g` +4 | Target 0 |
| New shared hubs created by P1 | 3 in the plan as written | 0 |

---

## 6. Method and limits

- **Replay.**
  - Gate designs were replayed per commit (parent → commit) over `git rev-list --no-merges 8886406..eef7ca4`, which is
    23 Rust-touching commits.
  - That is only three days of history. Treat the percentages as indicative. The ordering between the designs (74% →
    35% → 13% → 4%) is robust, but the exact rates are not.
  - Non-test lines are counted as the lines before the first `#[cfg(test)]` + `mod` pair. A file whose test module is
    not at the end would be over-counted; I saw no such case among the files near the limits.
- **Module graph.** The text-level extractor reproduces the report's graph within 2 edges (147 vs 149) and gives the
  same six SCCs. It can miss edges made through glob imports or `super::super` paths that cross top-level modules.
  Those are false negatives, which are acceptable in a ratchet.
- **Compiler experiment.** It used a standalone pyo3 0.22.6 probe crate and a `git archive` copy of `eef7ca4` with a
  separate target directory. The linked sase-core checkout was not modified.
- **Beads** (`sase-165`, `sase-17m`, `sase-15d`…`15h`, `sase-17n`, `sase-oq`, `sase-km`, `sase-kx`, `sase-wg`,
  `sase-10d`) were read with audited `sase bead read`. The P0 plans were read with `sase artifact read`.
- **Not verified:**
  - the runtime of the route behaviour test
  - whether the three `sudo_runner` flakes share one root cause
  - the replay rate over a longer window, which should be re-run on 50+ commits before landing (design rule 1)
