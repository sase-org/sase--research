# E3 (failure triage) and E4 (receipts + staged reuse): still correct, with scoped adjustments

**Researcher mus · 2026-09-24 · sase master at workspace `sase_43`**
**Question.** Now that E1 (`sase-135`, closed 2026-09-20) has landed and E2 (`sase-17p`, 5/6 phases closed, `.6` in progress) is almost complete, are the E3 and E4 epics in `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` still correct and appropriate? What should change, and what exactly counts as "landed" for each?

**Sources (all read directly):** the consolidated roadmap §1–§8; `sase bead read sase-135`, `sase-17p`, `sase-17p.6`, `sase-145`, `sase-146`, `sase-17e`, `sase-17g`; `docs/tool.md`; `src/sase/tool/` (executor, stage_protocol, observe, sample, query, control); `sase/sase.yml` catalog; `sase tool --help / list / runs / show`; `sase-core` `tool_run/` tree (canonical, fingerprint, store, wire); flake-baseline references in `tests/test_selection_health_tool.py`; `sase-core-revision.txt`. I did **not** read the sibling `__a.md` / `__b.md` phase sketches or any `__cdx/__cld/__gem` peer report; conclusions below are my own from the roadmap plus today's tree and bead store.

---

## 1. Answer up front

**Yes. E3 and E4 are still the right next epics, in the right order, at roughly the right size — keep them as two separate medium epics, startable in parallel as soon as E2.6 lands.**

- E1 delivered what E3/E4 need: versioned Rust ToolRun/store contracts, `tools:` catalog in `sase/sase.yml`, foreground execution with child-passthrough, `list/run/runs/show`, fingerprints, `run_silent` stage events, PSI/loadavg sampling (recorded, unused), retention + `sase disk` ownership, guarded recipes, and the adoption report. Verified: `sase-135` closed with 7/7 phases done; `sase tool list` shows LAST/TYPICAL; no `failures`/`rerun`/`receipt` verbs exist yet.
- E2 delivered (or is delivering) what E3/E4 assume: one ToolRun id with explicit hand-off to monitor/proc executors, `stop` / `show --follow` / `wait` facades, crash/settlement reconciliation, one settlement notification. Verified: `sase-17p.1`–`.5` closed; only `.6` (prove contract end-to-end, docs/skills/memory, remove `tool_handoff` flag) remains; `sase tool stop/wait` already in `--help`.
- No code for E3/E4's core contracts exists yet: no `receipt`, `signature`, or triage logic anywhere under `src/sase/tool/` or `sase-core/.../tool_run/` (only unrelated `uv_tool` receipts and agent-scan hits). So both epics are still greenfield, not6142 already half-built.
- The roadmap's sequencing argument still holds: E3/E4 attack **re-discovery and repetition** (the measured dominant waste: repeated verification commands re-discovering known-red master), need no predictor, and fill the ~3-week corpus-accumulation window E6 waits on. Neither is gated on `sase-11y`, `sase-x7`, or E6 calibration.

**Recommended adjustments (scoped, not structural):**

1. **Keep E3 and E4 separate.** Do not merge into one ~12-phase "intelligence" epic. The roadmap §7 already warns this repeats the `sase-zm` (14 phases, 0 closed, superseded) size failure. They also have different released contracts (E3: signature + classification; E4: receipt + reuse) and different acceptance surfaces (E3: failure output; E4: skip/reuse output) — the project's own "one epic, one released contract, one acceptance surface" lesson.
2. **E3 must absorb `sase-145` (durable finish diagnostics) as its phase 0.** Triage cannot classify what the ledger cannot explain: today `canonical_event` strips `diagnostics` and `tool_run_finish` stores none, so typed spawn-failure reasons (127/126), stage-ingest diagnostics (torn `events.jsonl`), and log-write facts are printed once and lost (`sase tool show` cannot explain a settled run). `sase-145` is READY and explicitly out-of-scope for E1 because it changes the frozen V1 stored record — that is exactly E3's first schema change.
3. **Both epics' deterministic logic belongs in Rust (`sase-core`), per the Rust core backend boundary.** Signature normalization, classification, receipt mint/match, and TTL/input scoping are reusable domain logic any frontend (CLI, TUI, web) must agree on. `sase-146` (adoption-report aggregation still in Python, READY) is the cautionary precedent: E3/E4 must not repeat "ship in Python to avoid a cross-repo change" and then file the Rust move as a follow-up. Each epic ratchets the published core floor inside the epic that needs it and bumps `sase-core-revision.txt`.
4. **Draw the routing boundary explicitly against `sase-17e` / `sase-17g` (both READY).** Those beads own *run-level* inline-vs-monitor routing (duration classes + ceiling; `--detach`/`wait`/`--join` escalation). E4 owns *stage-level* cheap-inline-before-hand-off **plus per-stage receipts**; E6 owns calibrated prediction and automatic routing. E4 must consume 17e/17g (or declare them out of scope with a link), never re-implement run-level routing or a predictor.
5. **E3 owns `failures` + `rerun` verbs and attempt chains; E2's invariant stands.** One semantic run = one ToolRun id; retries are explicit attempt chains on that id (or linked ids), never silent duplicate runs, never a second log copy. E3 must not add fields to the proc wire — the link lives on the tool side only (same rule E2 adopted for `sase-11y.2`).
6. **Keep the roadmap's negative rules:** no auto-created `ci`/`flake` beads (suggest only); exit 0 is not proof of applicability; receipts mint on success only, never reuse failures; host-completion policy (not the agent) decides whether a receipt satisfies a landing gate; green-master-independent acceptance (master is still red: `sase-j0` +38).

---

## 2. Ground truth checked today

- **E1 (`sase-135`) CLOSED** 2026-09-20, 7/7 phases closed. Catalog: `check`, `check-full`, `install`, `test`, `test-visual` in `sase/sase.yml` `tools:`. CLI: `list/run/runs/show` (+ `_adopt` hidden); E2 has since added `stop/wait`.
- **E2 (`sase-17p`) IN_PROGRESS, 5/6 closed.** `.1` reservation/adoption/settlement contract, `.2` `-H` plain-proc leg, `.3` monitor-start reservation, `.4` stop/follow/wait, `.5` crash settlement — all closed. `.6` open: extend smoke harness with hand-off fault matrix, update docs + `sase_monitor` skill + memory, remove `tool_handoff` flag (flag bead `sase-17w`). Known E2-landing residue (notes on `sase-17p`): completion snapshot drift (`stop`/`wait` vs `cli_spec.json`), parser-test verb list drift, one monitor-start test double missing `tool_run_id`, one sleep-pragma lint, flag-name `sase-17v` vs `sase-17w` mismatch. E3/E4 plans must assume these are fixed by E2.6, not re-fix them.
- **Store shape today** (`sase tool runs -n 3 -j`): `definition_digest`, `extra_args_digest`, `fingerprint_before/after` with declared `inputs` (Justfile, pyproject, uv.lock, sase-core-revision.txt content hashes), `evidence_completeness`, `executor: inline`, `exit_code`, `duration_ms`, per-stage rows, retained output with explicit truncation. `diagnostics: []` is present but empty — the `sase-145` gap.
- **No triage/receipt verbs:** `sase tool --help` lists only `list/run/runs/show/stop/wait` (+ hidden `_adopt`). No `failures`, `rerun`, or `receipt` verb. `docs/tool.md` (221 lines) documents catalog provenance, stream fidelity, retention, incomplete evidence, failure semantics, rerunnable harness (`tools/smoke_sase_tool_runs`), guarded recipes, monitor wrapping, adoption measurement — but no signature, classification, or receipt sections. Correct: those are E3/E4's docs to write.
- **Flake baseline exists as a concept with a concrete source:** `tools/run_silent "flake baseline"` gate in `just check-full` (`tests/test_justfile_lint.py`) and `tools/selection-health --flake-baseline` (`tests/test_selection_health_tool.py`). E3's FLAKY class has something to compare against; the epic must name that source, not invent a second baseline.
- **Red master still available as E3's KNOWN fixture:** `sase-j0` open with +38 corroborations; `just check-full` red since 2026-08-10 per roadmap. E3 acceptance can demo on real data day one — and must not require green `check-full` to pass.
- **Guarded recipes + monitor wrapping already landed** (`docs/tool.md` §§ Guarded recipes / Monitor wrapping): `just check`/`check-full` refuse outside `sase tool run <name>` for that root (or explicit `SASE_TOOL_BYPASS`); `verify`-profile monitors wrap argv. E4 receipt reuse must preserve this: a reused (skipped) run still satisfies the guard by named identity + root, and ad-hoc `--` runs stay receipt-less.

---

## 3. E3 — Failure triage: revised scope and landing criteria

### 3.1 Still-correct core

Rust signature normalization (strip workspace paths, unstable line numbers) → verification-vs-infra split → classification against master/merge-base and the flake baseline → `failures` + `rerun` attempt chains → structured NEW/KNOWN `--next` payloads replacing hand-written baseline essays → suggested (never auto-created) `ci`/`flake` beads. User-verifiable result stands: **a failed run labels each failure NEW or KNOWN; `sase tool failures` groups today's red-master signatures across agents.**

### 3.2 Required scope changes vs the roadmap paragraph

1. **Phase 0: land `sase-145` inside E3.** Persist typed finish diagnostics (spawn 127/126 reason, stage-ingest diagnostics, log-write facts) on the stored ToolRun record with a versioned schema bump. Acceptance: `sase tool show RUN -j` on a settled spawn-failure / torn-events / capped-log run explains itself without re-running. Without this, every E3 classifier test is unfalsifiable.
2. **Normalization + classification live in `sase-core`.** New Rust module (e.g. `tool_run::signature`), versioned normalization rules, PyO3 bindings, unit tests with golden signatures. Python owns only CLI rendering and `--next` payload assembly. Include the redaction rule from E1 planning (protected execution argv separate from display argv, no env dumps) — signatures must never leak secrets.
3. **Name the comparison sources exactly:** (a) merge-base / master HEAD ToolRun signatures for the same tool + definition digest; (b) the flake-baseline source (`selection-health --flake-baseline` data, not a new list); (c) the run's own attempt chain. KNOWN = matches master/merge-base signature; FLAKY = matches flake baseline (or flaps within attempt chain); NEW = neither. Infra (spawn, OOM-killed wrapper → `lost`, torn events, unwritable store) is a separate top-level class from verification failures — never labeled NEW/KNOWN.
4. **Attempt-chain semantics (preserve E2 invariants):** `sase tool rerun RUN` (or `run --retry` — E3 planning picks one, not both) creates a new attempt on the same semantic run family with an explicit attempt number; `sase tool failures` groups by signature across runs/agents for today (default) with `-j` versioned JSON. One process owner, one log owner, one continuation graph — no second copied log.
5. **`--next` payload replaces the essay, adopts `sase-zl`.** Structured NEW/KNOWN payload (signature id, class, evidence pointers to ToolRun ids, suggested scope for the next run) is the default continuation content; the median-1,778-char hand-written baseline essay is the thing that disappears. Measured by the adoption report family, not by assertion.
6. **Bead suggestion, never creation.** On NEW verification failures the output may suggest `sase bead create` with a prefilled title/classification; it must not create beads. Covered by a negative test.

### 3.3 E3 landing criteria (crystal clear — every line must hold)

**Verbs & output (DoD-T1).**
- `sase tool run check` (or `test`) on a failing tree prints, per failure, `NEW` or `KNOWN` (or `FLAKY` / `INFRA`) with a stable signature id, on both human and `-q` compact output, without changing the child's exit code.
- `sase tool failures` (default: today, current project) groups failed signatures across agents with counts, one example ToolRun id per group, and class labels; `-j` emits a versioned envelope; empty state prints "no recorded failures" (exit 0), never an error.
- `sase tool rerun RUN` (or the chosen spelling) re-executes with an explicit attempt number visible in `show -j`; `show RUN -j` exposes the attempt chain.

**Correctness (DoD-T2).**
- Golden signature tests: same logical failure under different workspace paths / PIDs / timestamps / line-number noise → identical signature; genuinely different failures → different signatures. Normalization rules versioned; rule change bumps version and is noted in the plan.
- Classification tests on real fixtures: (a) a failure whose signature matches master/merge-base history → KNOWN; (b) a failure matching the flake-baseline input → FLAKY; (c) a novel failure → NEW; (d) spawn-127 / torn-events / `lost` wrapper → INFRA, never NEW/KNOWN. At least one KNOWN case demos on the live red master (`sase-j0` family) without requiring `check-full` to go green.
- Fingerprint-incomplete runs (`evidence_completeness.complete: false`) classify as `UNKNOWN` with a typed reason, never guessed NEW/KNOWN.

**Negative & boundary cases (DoD-T3).**
- Ad-hoc runs (`sase tool run -- …`) get signatures but are excluded from KNOWN matching by default (no catalog identity) — documented, tested.
- Extra-args runs only match history with the same `extra_args_digest` family or an explicitly documented args-insensitive rule.
- No auto-created beads: a test asserts `rerun`/`failures` create zero beads; suggestion text contains the exact `sase bead create` command a human would paste.
- `--next` payload test: a failed run's structured payload round-trips through the `sase-zl` continuation consumer (or its named successor) without hand-editing.

**Store, retention, docs (DoD-T4).**
- New signature/classification rows live in the Rust-owned store with bounded retention declared alongside `tool_run_retention` (same `sase disk` ownership pattern as E1); `sase disk list/reap` covers the new rows.
- `docs/tool.md` gains Failure triage (§: signature, classes, `failures`/`rerun`, `--next`); compact help and `sase/sase.yml` reference updated; one beta flag for the epic, removed before landing per `sase_flags`.
- Harness: `tools/smoke_sase_tool_runs` (or the E3-named extension) covers T1–T3 hermetically plus one live red-master KNOWN case; `just check` green (green-master-independent: full-lane reds owned by other beads don't block, but the epic's own tests pass).

**Explicit non-goals for E3:** no receipts or skipping (E4); no duration prediction or auto-routing (E6); no capacity queues or refusals (E7); no TUI surfaces (E5); no cross-machine signatures (E8).

---

## 4. E4 — Receipts and staged reuse: revised scope and landing criteria

### 4.1 Still-correct core

Tree- vs workspace-scoped receipts with declared inputs + TTL → mint on success only → reuse in `run` with `-R` force → unchanged-since-failure refusal → `install` skip → cheap-stages-inline-before-hand-off with per-stage receipts → `receipt TOOL` for scripts/landers → host-completion policy decides landing-gate sufficiency. User-verifiable result stands: **second `sase tool run check` on an unchanged tree returns instantly citing a receipt; `just install` no-ops when nothing changed; a lint failure stops before the heavy stage.**

### 4.2 Required scope changes vs the roadmap paragraph

1. **Receipts are a new Rust-owned entity with an explicit schema version.** E1 froze the V1 wire; E4 declares the receipt record (tool name, definition digest, extra-args digest, fingerprint digest, scope, inputs, TTL, producing run id, timestamps) in `sase-core`, with bindings + floor ratchet + `sase-core-revision.txt` bump. No Python-only receipt store.
2. **Scope semantics pinned down (planning must not re-litigate):**
   - *Tree-scoped*: valid for any workspace at the same commit + same definition/args digests + complete fingerprints equal.
   - *Workspace-scoped*: additionally bound to the workspace (path/machine); used when inputs include untracked or machine-local state.
   - Receipt declares its inputs (reuse of E1 fingerprint `inputs` list); any input outside the declared set invalidates reuse. TTL per tool (catalog-declared, capped default); expired receipt = absent.
3. **Mint/use rules (no exceptions):** mint on success only (exit 0 + complete evidence); never mint on failure, `lost`, incomplete evidence, ad-hoc runs, or bypassed runs; reuse requires (a) live receipt, (b) fingerprints complete and unchanged per `fingerprints_mutated`, (c) no failure recorded for that identity since the receipt minted ("unchanged-since-failure refusal" — a later failure poisons the receipt even if the tree matches). `-R`/`--force` (or the catalog's chosen spelling — one spelling only) bypasses reuse and records that it did.
4. **Boundary against 17e/17g and E6:** E4 consumes run-level routing as-is. Its new behavior is (a) per-stage receipts for `run_silent` stages (lint → heavy stages), (b) cheap-stages-inline-before-hand-off: when a hand-off was requested (`-H` or monitor/proc owner), cheap stages still execute inline first and their receipts are minted/reused, so a lint failure fails fast without paying a 4–7 s hand-off. No ETA, no quantile, no automatic inline-vs-hand-off decision — those are E6. If `sase-17e`/`17g` land first, E4 integrates; if not, E4 documents the seam and does not build its own run router.
5. **`install` skip is a receipt reuse with honest output**, not a silent no-op: prints `install: no-op (receipt <id>, inputs unchanged, TTL …)` and exits 0. Same guard rule as §2: reuse still satisfies `require_tool_run` by named identity + root.
6. **`receipt TOOL` verb is for scripts and landers:** `sase tool receipt check` prints the live receipt (or "no live receipt + why": none/expired/poisoned/incomplete/TTL) with `-j` JSON. Host-completion/landing policy reads it; the agent never treats exit 0 + receipt as proof the gate is satisfied. Document the policy callout explicitly so land agents don't shortcut `just check`.

### 4.3 E4 landing criteria (crystal clear)

**Reuse behavior (DoD-R1).**
- Second `sase tool run check` with no fingerprint change exits 0 in well under a fresh run (harness asserts wall-clock bound, e.g. <10 s where fresh is minutes) and prints `reused receipt <id>` + producing run id + scope/TTL. `show` on the reusing run points at the producing run; no child is spawned (assert via spawn counter or argv log in tests).
- `sase tool run check --force` (`-R` spelling per plan — exactly one) re-executes even with a live receipt and records `forced: true`.
- After a failure for identity X, a subsequent unchanged-tree `run X` does **not** reuse any older success receipt (poisoned) — it re-executes. Test: success → receipt → failure → success-again requires fresh execution, then mints a new receipt.
- Failures, `lost`, incomplete-evidence, ad-hoc, and bypassed runs never mint: each has a negative test asserting no receipt row.

**Stages (DoD-R2).**
- A `check` (or fixture catalog tool with cheap+heavy stages) whose lint stage fails under a hand-off request fails fast without delegating the heavy stage: assert heavy stage never started (no proc/monitor leg created) and total time avoids the measured 4–7 s hand-off tax.
- Per-stage receipts: re-running after fixing only the heavy stage reuses the cheap stage's receipt (stage timeline shows `reused` for lint, `executed` for the heavy stage). Stage receipt TTL and inputs documented per stage.

**Install + receipt verb (DoD-R3).**
- `sase tool run install` with unchanged inputs prints the no-op line with receipt id and exits 0; with changed inputs it executes.
- `sase tool receipt <tool>` human + `-j` output covers: live receipt (id, scope, TTL remaining, producing run, inputs digest) and each non-live reason (no receipt / expired / poisoned by failure at <ts> / incomplete evidence / ad-hoc never mints). Scripts can branch on the JSON without parsing prose.

**Safety & policy (DoD-R4).**
- TTL expiry tested with a short-TTL fixture tool (no wall-clock sleeps over seconds; injectable clock or TTL override in test only).
- Scope tests: tree-scoped receipt reuses across two fixture workspaces at the same commit; workspace-scoped does not.
- Secret hygiene: receipts contain digests + metadata only, never argv secrets, env values, or output bytes; a test asserts no secret-shaped fixture leaks into the receipt row or `-j`.
- Landing-gate doc test: `docs/tool.md` states host-completion policy decides sufficiency; a test or lint asserts no `receipt` output claims "gate satisfied".

**Store, flags, docs (DoD-R5).**
- Receipt rows in the Rust store with retention + `sase disk` coverage (same pattern as E1); versioned JSON from first release; one beta flag, removed before landing; `docs/tool.md` gains Receipts (§: scopes, TTL, mint/use rules, `receipt` verb, guard interaction, policy boundary); catalog reference documents per-tool TTL/scope knobs.
- Harness: receipt hermetic suite (mint/reuse/force/poison/TTL/scope/ad-hoc/bypass) + live two-run timing case; `just check` green under the same green-master-independent rule as E3.

**Explicit non-goals for E4:** no failure classification (E3); no forecasting, `run -E`, `stats` calibration, `timeout: auto`, or auto-routing (E6); no queues, expected-start, or refusals (E7); no agent-row chips or Admin Center panes (E5); no cross-machine receipt reuse or remote dispatch (E8 — hints only, later).

---

## 5. Sequencing, dependencies, and what to plan first

- **Start E3 and E4 in parallel once E2.6 closes.** Neither needs E6's corpus; both *feed* it (E1 already records fingerprints/timings/load; E3 adds classified outcomes; E4 adds reuse/force/poison signals). E6's "~3 weeks after E1" clock (E1 landed 2026-09-20 → calibration window ~mid-October) is filled by E3–E5, exactly as the roadmap intends.
- **E3 phase 0 is `sase-145`; E4 has no equivalent prerequisite** beyond E2.6's contract proof. If `sase-145` proves larger than one phase, split it (diagnostics persistence vs. `show -j` surfacing) rather than letting E3 bloat.
- **Coordinate with READY beads, don't absorb them silently:** `sase-146` (Rust-ify adoption aggregation) informs E3/E4's Rust-first rule but stays separate; `sase-17e`/`17g` (routing) are consumers/neighbors of E4's stage receipts — E4's plan must name which it assumes and link the other as related. `sase-17w` (retire `tool_handoff` flag) closes with E2.6; E3/E4 each get their own fresh beta flag.
- **Plan one epic at a time** (roadmap §6 rule, still wise): write the E3 plan first (it has the schema-change risk), then E4, each stating the §1 cross-epic invariants as rules and naming the other as successor. Do not write E5–E8 plans up front; revise them from what E3/E4 measure.
- **Core-floor discipline:** each epic that touches `sase-core` ratchets the published floor inside that epic and moves `sase-core-revision.txt` past its `sase-core` commit (per `docs/rust_backend.md`). E3 and E4 both will. Never batch both epics' core changes under one pin bump.

---

## 6. Open questions for Bryan (E3/E4 only)

1. **Keep E3/E4 separate (recommended) or merge into one "intelligence" epic?** Merging saves one planning cycle but buys back the 12-phase size profile that produced `sase-zm` and the `sase-zl` 20-follow-up landing audit. Recommendation: separate.
2. **Rerun spelling:** `sase tool rerun RUN` vs `sase tool run --retry RUN`? Pick one in E3 planning; both must not ship.
3. **Force spelling:** roadmap says `-R`; confirm `-R` (and its long form) doesn't collide with current/future `run` flags before E4 planning locks it.
4. **Per-tool TTL defaults:** a single global default (e.g. 24 h for `check`, longer for `install`) vs per-tool catalog values from day one? Recommendation: catalog-declared with a capped global default, so price is reviewed like code.
5. **Does `install`'s receipt cover `just install` invoked raw (outside the wrapper)?** Recommendation: no — receipts key on named-identity runs only; raw `just install` neither mints nor reuses (same guard philosophy).

---

## 7. Verification appendix (what I actually ran)

- `sase bead read sase-17p / sase-17p.6 / sase-135 / sase-145 / sase-146 / sase-17e / sase-17g` (audited reads with reasons).
- `sase tool --help`, `sase tool list`, `sase tool runs -n 3 -j`, `sase tool show --help`: confirmed verbs, LAST/TYPICAL, fingerprint/input shape, empty `diagnostics`.
- `src/sase/tool/` listing + `grep` for `receipt|failures|rerun|flake|triage|KNOWN|signature`: no E3/E4 implementation.
- `sase-core/.../tool_run/` listing + `grep` for `receipt|signature|triage|flake`: no E3/E4 implementation.
- `sase-core-revision.txt` pin read; `docs/tool.md` full read (221 lines); `sase/sase.yml` catalog section read.
- Deliberately did not open `sase_tool_epic_roadmap__a.md` / `__b.md` or any `__cdx/__cld/__gem/__mus` peer report.

**Bottom line for the lead synthesizer:** E3 and E4 survive contact with the landed E1 and nearly-landed E2. Approve both as medium epics with the adjustments in §1 (E3 absorbs `sase-145`; both go Rust-first; E4's stage-receipt vs run-routing boundary is explicit), and hold planners to the DoD checklists in §3.3 and §4.3 — those are the crystal-clear landing gates.
