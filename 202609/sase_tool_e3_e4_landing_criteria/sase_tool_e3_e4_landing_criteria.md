# `sase tool` E3 and E4 after E2: revalidated scope and exact landing criteria

**Consolidated report** · 2026-09-24 · host athena · sase master `9676df028` · core pin
`6d0d0e6d5c`

**Sources.** Four independent researcher reports, in this directory:

- `__cdx.md`: failure facts, a two-axis classification, and narrow exact-reuse receipts.
- `__cld.md`: a ledger-measured case for retargeting E3 and turning E4 into proof.
- `__mus.md`: keep both epics roughly as written; absorb `sase-145`.
- `__gem.md`: keep both as written; serialize them; add a deterministic-failure refusal.

Plus the roadmap they revalidate
(`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`, §1 and §4), the E2
plan (`plan:202609/tool_e2_durable_handoff.md`), and my own verification against
athena's ToolRun ledger, monitor store, test-selection store, bead store, the sase tree,
and the pinned `sase-core` (see the appendix).

**Question.** E2 (`sase-17p`) is nearly done. Are E3 ("Failure triage: NEW vs KNOWN vs
FLAKY") and E4 ("Verification receipts and staged reuse") still correct and
appropriate? What should change? What exactly must each epic show before it may land,
stated so the agents that plan, implement, and land it cannot disagree?

**Audience.** Agents that plan, implement, or land E3 or E4 should treat §4.8 and §5.6 as
the landing gates. §3 lists claims from the four source reports that turned out to be
wrong. Do not cite those claims.

---

## 1. Answer up front

**E3: yes. Plan it next. It needs four changes first.** The live data says E3 is worth
more than the roadmap assumed, but for a different workload:

1. **Target `check`, not `check-full`.** `decisions:check-full-is-explicit` removed
   `check-full` from agents' default path. Athena recorded 1 `check-full` run and 497
   sase `check` runs in 4.3 days. **86% of those `check` runs failed** (426 of 497). Only
   37 passed, and none passed on 2026-09-24 (0 of 73).
2. **Add KNOWN-gated stage continuation ("unmasking").** `just check` is fail-fast, and
   master-red lint stages run first. As a result, `test (scoped)` executed in only **20%**
   of `check` runs and in 11.5% of failed ones. Of 322 agents, **76% ended their session
   on a run whose tests never executed**. A KNOWN label with no continuation tells the
   agent "not yours" and still gives it no test signal.
3. **Use a precise witness-based KNOWN rule, and gate landing on a measured precision
   backtest.** A wrong KNOWN label tells an agent to ignore its own bug. The rule must
   be deterministic, carry its evidence, and default to UNKNOWN.
4. **Drop `rerun` attempt chains from E3.** FLAKY evidence already arrives passively from
   same-fingerprint repeats. An "attempt N of run X" also conflicts with E2's one-shot
   claim (`AlreadyClaimed`).

**E4 as written: no. Its own go/no-go measurement has now been run, and the answer is
no.** The roadmap deferred E4's payoff estimate until E1 recorded fingerprints. They are
recorded now:

- **Pass-receipt reuse would have saved nothing.** There were **zero** re-runs of an
  already-passing fingerprint in 527 fingerprinted `check` runs. I re-ran the count with
  a **content-addressed** key, which catches a verified dirty tree that is later committed
  and re-checked at the new commit, whether in the same or another workspace. It is still
  **zero**, even with toolchain and environment ignored. The "lander re-runs the phase
  worker's exact tree" waste does not occur.
- **Refusing to re-run after an unchanged-tree failure would be wrong where it matters.**
  In sase-core, 9 of 11 identical-fingerprint repeats after a failure *passed* (flaky
  tests). Those failures had `terminal_cause: exited` with a nonzero code, exactly the
  case gem's "deterministic-only" guard would still refuse.
- **The "cheap" lint stages are not cheap.** The median time from the first stage to the
  start of `test (scoped)` is **247 s**, while `test (scoped)` itself has a 52 s median.
- **Install is barely wrapped (1 run), and `_setup` already skips repairs when nothing is
  stale.**

**Recommended E4: re-scope it into "Verified completion: fingerprint-bound verdict
receipts" and plan it after E3 lands.** A receipt proves that this exact tree passed, or
finished with no NEW failures (using E3's verdict). It never skips execution. Its
consumer is prepared host completion. That path exists to land verified work with no
extra agent turn, yet on athena it has **never committed**: 6 uses, 5 failed on a
master-red `check`, and 1 hit a recovery error. This E4 depends on one policy decision
only you can make (§7 Q1). If the answer is no, **defer E4 entirely**. E5–E8 do not
consume receipts. The reuse leg (instant reuse, `install` no-op, per-stage receipts,
cheap-stages-inline) becomes a conditional **E4b** with a measured reopen trigger (§5.8).

**Sequencing:**

1. Land E2. All six phases are closed; the epic bead awaits its land agent.
2. Land the prerequisites `sase-182` (linked-repo identity) and `sase-114` (fixture
   stage-event leak, §2.4).
3. Plan and run E3.
4. Plan E4 only after E3's precision backtest passes, and only on a "yes" to §7 Q1.
5. Do not run E3 and E4 concurrently. Both change `sase-core`'s `tool_run` store and
   bindings, and E4 consumes E3's verdict.

---

## 2. What changed since the roadmap (2026-09-17)

### 2.1 State of the substrate

- **E1 is closed.** `sase-135` closed 2026-09-20. It delivered the ledger, catalog,
  fingerprints, stage events, samples, retention, and `list`/`run`/`runs`/`show`.
- **E1.5 is closed.** `sase-16h` delivered guarded recipes, monitor wrapping, and
  linked-repo catalogs. Nearly every agent `check` is now a ToolRun.
- **All six E2 phases are closed.** `sase-17p` delivered reservation, claim, `-H`,
  stop/follow/wait, typed `terminal_cause`, `settled_by`, and one-delivery. `.6` removed
  the `tool_handoff` flag in `c91690efc`. Only the epic land remains.
- **The E2 fields are new, so almost no history carries them.** `terminal_cause` and
  `settled_by` are set on only **36 of 648** ledger rows. All 648 rows show
  `executor: inline`, and no `-H` hand-off run has been recorded yet. E3 must map legacy
  rows (§4.3), and any claim about hand-off latency has no post-E1 data yet.
- **E2's wire rule binds both epics.** E2 plan decision 6: additive only,
  `schema_version` stays 1, only nullable columns or new tables, and no new values in
  existing enums. Several sase venvs share `~/.sase/tools/runs.sqlite`.
- **Catalog changes are expensive.** `ToolDefinitionWire` is `deny_unknown_fields`, and
  `ToolDefinitionIdentity` hashes name, argv, stages, inputs, env, args, and the
  fingerprint spec. A new catalog field is rejected by older cores and moves every
  definition digest unless it is deliberately excluded from the identity.
- **`parent_run_id` means nesting, not retry.** It is set when a ToolRun runs inside
  another ToolRun (`src/sase/tool/ownership.py`). The store has an `attempts` table, but
  E2's claim is one-shot. A retry lineage would need its own new field.

### 2.2 `check` is red almost always, and the red hides the tests

Measured on athena, sase `check` (definition digest `12b1748a5c…`), from 2026-09-20 07:26
to 2026-09-24 15:33. These numbers reproduce cld's figures at a later cutoff.

| Measure | Value |
| --- | --- |
| Runs | 497: 37 succeeded, 426 failed, 22 lost, 12 signaled |
| Daily passes | 09-20: 1 · 09-21: 14 · 09-22: 19 · 09-23: 3 of 151 · 09-24: 0 of 73 |
| `test (scoped)` executed | 101 of 497 runs (20%). Only 49 of 426 failed runs reached it |
| Agents that ran `check` | 322. Their last run executed tests in 77 cases (24%) and passed in 36 (11%) |
| First failing stage | `lint (symvision)` 237 (56%) · `lint (mypy)` 73 · `test (scoped)` 49 · `fmt (python)` 20 · `lint (pyscripts)` 17 · `lint (feature flags)` 13 · other 17 |
| Time from the first stage to the start of `test (scoped)` | median 247 s (n = 101) |
| Passing-stage medians | SASE validation 66 s · feature flags 59 s · test (scoped) 52 s · mypy 40 s · symvision 32 s · test waits 19 s · pyscripts 19 s · fmt (markdown) 11 s · the rest under 6 s |

Stage order is fmt, then ten lint stages, then validation, committed plans, and finally
`test (scoped)`. Symvision runs 11th, after about 2.5 minutes of earlier stages. The
problem is not the ordering; it is that a failure the agent did not cause cannot be
passed. The user's own bead `sase-180` describes the same masking. cld's chronological
replay (§4.3 rule, prior evidence only) labeled 72% of failure items KNOWN, 7% NEW, and
21% UNKNOWN, and gave 47% of failed runs an all-KNOWN verdict. I did not re-run that
replay; it is a feasibility estimate, and E3's DoD-5 is the real gate.

### 2.3 Receipts: the payoff E4 was waiting to measure is about zero

| Measure | Value |
| --- | --- |
| `check` runs with complete fingerprints (all repos) | 527 |
| Re-runs of an already-passed fingerprint (digest-keyed, as cld measured) | **0** |
| Re-runs of an already-passed tree, **content-addressed** (HEAD tree plus dirty content, any workspace, any commit; my measurement) | **0**, and still 0 with toolchain and env ignored |
| Repeats after a non-pass | 25–30, all in the same workspace at the same HEAD |
| sase-core repeats on an identical fingerprint | 9 of 11 flipped from fail to pass (open flakes `sase-15d`–`15h`, `17n`) |
| sase repeats on an identical fingerprint | 19 of 19 failed again, about 1.4 h per 4 days |
| `install` runs recorded | 1. `install` is unguarded, and `_setup` already runs `validate_test_environment` and repairs only what is stale |
| `check` toolchain fingerprint | python, just, and sase-core-rs only. It lacks ruff, mypy, symvision, and prettier (`sase-vr`: lint verdicts depend on install date) |
| External state `check` reads without fingerprinting it | symvision `--epic-symbol` bead statuses and flag-bead lint |

With only 37 passes in the window, a greener master would create more pass *candidates*.
But nothing in the data shows agents re-verifying identical content after a pass, and
host completion already verifies in the monitor that commits.

### 2.4 Two data defects E3 must not inherit

1. **Linked-repo runs are recorded under the host project's identity (`sase-182`,
   ready).** 51 linked-repo `check` runs are labeled `gh_sase-org__sase`: 39 sase-core, 5
   telegram, 4 github, and 3 research-artifacts. Their fingerprint `repos[0].identity`
   is also wrong. Keyed on (project, tool), E3 would mix sase's deterministic failures
   with sase-core's flaky ones.
2. **Test fixtures write fake stages into the enclosing run (`sase-114`, ready; I added
   the ToolRun evidence as a +1).**
   - `tests/monitor/test_continuation_baseline.py` runs `tools/run_silent` with
     `{**os.environ, …}`, so its synthetic `stage one` exit-7 failure lands in the parent
     ToolRun's stage timeline.
   - **37 of the 101** `check` runs that reached `test (scoped)` carry nested fixture
     stage rows. One *succeeded* run contains a failed stage row.
   - gem's "stage one (smoke): 38 failures" and "test (scoped): 129 failures" are this
     contamination, not real failures.

### 2.5 Host completion and continuation prose

- **Prepared host completion has never committed.** All 6 uses were between 2026-09-23
  21:07 and 2026-09-24 11:43. Five failed because `check` exited 1, and one completed
  but hit `requires active finalizer turn metadata`.
- **Completion requires exit 0.** Prepared completion is "prepared no-model monitor
  success" (`src/sase/monitor/host_completion.py`), so on a red master it cannot fire.
  Meanwhile the ordinary `/sase_final` path commits on the agent's own "unrelated"
  judgment, with no verification gate.
- **The roadmap's `--next` metric is dead.** Its E3 exit metric was "median `--next`
  falls below 1,778 chars". cld found post-E1 verify-monitor prose at a median of 1,052
  chars, and it is mostly task-specific instructions, not baseline essays. Do not use
  that metric.

### 2.6 An existing pytest evidence store that none of the reports used

`~/.sase/test-selection/<project>/` holds **1,846 full-run records** (918 with failures;
156 since 2026-09-20) with 30-day retention. Each record carries `head`, `workspace`,
`changed_files`, `tree_dirty`, and the failing node ids. `tools/selection_health`
already builds on it:

- the reproducible-flake oracle, plus `tests/reproducible_flake_baseline.txt` (471
  lines, entries require a bead);
- `attributable_dirty_failures`;
- a git-ancestor oracle.

This is witness-shaped pytest evidence. It exists even when a ToolRun's test stage was
masked, and the tests that did run under other entry points recorded it. E3 must consume
it for FLAKY and may consume it as KNOWN witnesses (§4.3). It must not build a competing
flake store.

---

## 3. Disagreements, resolutions, and claims to discard

### 3.1 Resolutions

| Topic | cdx | cld | mus | gem | **Resolution** (why) |
| --- | --- | --- | --- | --- | --- |
| Is E3 still right? | yes, large | yes, retarget | yes, medium | yes | **Yes, large (7 phases).** Unanimous. Size follows cdx/cld: the core contract plus continuation outgrow "medium" |
| E3 target workload | generic | `check` | `check`/`test` | `check-full` + `sase-j0` demo | **`check`.** 497 vs 1 run; `check-full` is explicit-only |
| KNOWN reference | eligible run at merge-base, with explicit reasons | cross-workspace witness at an ancestor HEAD | master/merge-base signature | merge-base run **or an active bead mapping** | **cld's witness rule plus cdx's eligibility and reason codes (§4.3).** A strict merge-base reference yields almost all UNKNOWN: all 15 clean-tree runs failed, and runs rarely sit exactly at the merge base. **Beads are never KNOWN evidence** (cdx and cld; gem rejected) |
| Classification shape | two axes (kind × disposition) | single class set plus INFRA/ENVIRONMENT | NEW/KNOWN/FLAKY/INFRA | NEW/KNOWN/FLAKY/INFRA | **Two axes**: run-level `failure_kind` × item-level class, plus a four-value run verdict (§4.3) |
| `rerun` | new linked ToolRun | drop, with a reopen condition | attempt chain on the same id | linked attempt | **Drop from E3** (§4.9). If it reopens: a new run id plus a new `retry_of_run_id`, never attempt N and never `parent_run_id` |
| `sase-145` durable diagnostics | implied by "failure facts" | — | fold in as phase 0 | — | **Fold into E3 phase 1**, which closes `sase-145` |
| Stage continuation | — | add, KNOWN-gated | — | — | **Adopt.** Tests run in 20% of runs today; without continuation, `no_new_failures` is impossible to earn |
| Stable stage key | new catalog `stage_key` | stage description, no catalog change | — | — | **Top-level stage description, no catalog change** (avoids moving the definition digest and the `deny_unknown_fields` rollout); plus a nesting guard (§4.4) |
| E4 shape | narrow exact whole-tool reuse, `check` only, shadow first | proof for host completion, or defer | as written | as written, plus refusal | **Proof-shaped E4 (cld), conditional on §7 Q1; otherwise defer.** Reuse opportunity measured at zero twice (§2.3); refusal wrong on flaky repos |
| E3/E4 ordering | serial | serial | parallel | serial | **Serial.** Both change the same Rust store and bindings (the pin ratchet collided in `sase-17p` note #1), and E4 consumes E3's verdict |

### 3.2 Claims from the source reports that are wrong or stale; do not cite them

- **gem, "490 of 556 `check` runs failed (88%)."** 490 is failures across *all* tools.
  For sase `check`, 426 of 497 failed.
- **gem, "71% of stage failures are in cheap stages taking 0.2–45 s", and "E4's
  cheap-stages-first eliminates the tail."** It takes 247 s to reach tests. mypy (40 s),
  feature flags (59 s), symvision (32 s), and validation (66 s) dominate.
- **gem, "phase worker → land agent re-runs the exact tree; 100% waste."** Zero
  content-addressed repeats after a pass (§2.3).
- **gem, "`just install` 74.5 h over 1,798 invocations."** This does not appear in the
  ToolRun ledger (1 run). It predates E1, and `_setup` already skips.
- **gem, KNOWN acceptance on `check-full` with a `sase-j0` bead mapping.** `check-full`
  is explicit-only, and bead mapping is not evidence.
- **gem, `terminal_cause` values `stopped`/`lost`/`crashed`.** The real values are
  `exited`, `signal`, `interrupt`, `stop_requested`, `timeout`, `launch_failed`,
  `owner_lost`, and `wrapper_lost`.
- **gem, the "stage one" and 129 `test (scoped)` stage failures.** These are fixture
  contamination (§2.4).
- **mus, "E3 and E4 start in parallel."** Rejected (§3.1).
- **mus, retries as "attempt chains on that id."** This conflicts with E2's one-shot
  claim.
- **Roadmap, "cheap-stages-inline saves the 4–7 s failed hand-off."** That was apollo
  data from before E1. Athena has no post-E1 verify failure under 87 s (cld), and no `-H`
  run has been recorded yet.
- **Roadmap, E3 as "the adoption vehicle for `sase-zl`'s built-but-unused machinery."**
  Stale. E1.5 enforces adoption, and E2 owns hand-off. E3 justifies itself through triage.

---

## 4. E3: "Failure triage: every failure labeled, no KNOWN failure hides the rest"

### 4.1 User-verifiable result

With master red exactly as it is on any given day, an agent's `sase tool run check`:

1. **runs past every stage whose failures are all KNOWN or FLAKY**, so the scoped tests
   run behind a master-red symvision stage;
2. **labels every failure item** NEW, KNOWN, FLAKY, or UNKNOWN, with its evidence
   (witness runs, agent counts, first seen) and, where one exists, a *possible* owning
   bead;
3. **ends with one verdict line**, for example
   `verdict: no_new_failures — 26 KNOWN, 1 FLAKY; exit 1 because KNOWN failures remain`;
4. **exits with the same code** that fail-fast `just check` would have returned.

In addition, `sase tool failures` shows the machine's current red-master signature
groups, with agent counts and first and last seen. A verify monitor's follow-up prompt
carries the verdict and the NEW and UNKNOWN items, with no hand-written baseline prose.

### 4.2 Scope

**In:**

- durable failure facts and diagnostics (closing `sase-145`);
- extractors and normalization;
- the classification and verdict contract;
- continuation (`-k`/`-x`, and KNOWN-gated continuation as the agent default);
- the compact footer, `show -j`, `sase tool failures`, and verify-monitor evidence;
- owner *suggestions*;
- the precision backtest;
- docs, memory, and flag removal.

**Out:**

- `rerun` (§4.9);
- automatic bead creation or `+1`;
- receipts, or any change to landing or completion policy (E4);
- cross-machine or CI evidence;
- TUI (E5 owns the Failures view);
- any `ToolDefinitionWire` or catalog schema change;
- fixing any master-red item;
- symvision's *internal* stage masking (`sase-180`).

**Prerequisites that must be closed before the named phase:**

| Prerequisite | Needed before | Note |
| --- | --- | --- |
| E2 `sase-17p` landed | E3 phase 1 | All phases closed today |
| `sase-182` linked-repo identity | E3 phase 2 | The E3 plan may fold it in as a first step if it is still open at planning time |
| `sase-114` fixture stage-event leak | E3 phase 3 | E3 also adds a recorder-side nesting guard (§4.4), so a future leak cannot recur silently |

### 4.3 Classification contract (precise v1 rules)

All of this is a **pure Rust function** in `sase-core`. Python supplies only these
inputs:

- the bounded ancestry list (`git rev-list --first-parent`, at most 2,000 commits);
- the flake-baseline entries and the selection-health reproducible-flake set;
- optionally, selection-health full-run witness rows;
- bead candidates for owner suggestion.

The output is deterministic under any reordering of its input rows.

**Identity.**

- **Tool identity** `T` = (catalog repo identity, tool name), after `sase-182`.
- **Evidence runs** are settled, non-ad-hoc ToolRuns of the same `T` with the same
  `extra_args_digest` and a complete `fingerprint_before`, settled within the lookback
  `L` (7 days).
- An item `i` carries:
  - its stage (the top-level description);
  - its extractor name and version;
  - its signature digest `s(i)`;
  - its locator paths `P(i)`, repo-relative.

**Run-level `failure_kind`** (a string in a new table; no new values in existing enums):

| Kind | When | Items produced? |
| --- | --- | --- |
| `control` | `terminal_cause` ∈ {`stop_requested`, `interrupt`, `timeout`} | no |
| `infrastructure` | `terminal_cause` ∈ {`launch_failed`, `owner_lost`, `wrapper_lost`, `signal`} | no |
| `environment` | exited nonzero before any stage completed, with a recognized `_setup` marker (missing binding, `uv` resolution, …) | one environment item with a remedy hint (`just install` / `sase update`) |
| `verification` | exited nonzero with a failed stage, or with unparseable failure output | yes |
| `none` | exit 0 | no |

Pre-E2 rows (`terminal_cause` NULL; 612 of 648 today) map through a documented table
over `state`, `exit_code`, `signal`, `interruption_reason`, and `lost_reason`. Anything
ambiguous maps to `infrastructure` with the reason `legacy_unmapped`, never to
`verification`.

**Definitions used by the item rules:**

- **touched(i, R)**: `P(i)` intersects run `R`'s dirty paths in the catalog repo.
- **base(R)**: `fingerprint_before.repos[catalog repo].head`.
- **Witness `W`** for `s` relative to `R` must satisfy all of:
  - `W ≠ R`;
  - `W` is from a different workspace, or ran on a clean tree;
  - `s ∈ items(W)`;
  - not touched(`s`, `W`);
  - base(`W`) is an ancestor of, or equal to, base(`R`);
  - `W` settled within `L`.

  A selection-health full-run record can serve as a pytest witness under the same
  conditions, using `changed_files` as its touched set.
- **Clearing run `C`** must satisfy all of:
  - base(`C`) lies on the ancestor chain between the newest witness's base and base(`R`);
  - `C` completed the item's stage;
  - `s ∉ items(C)`, and not touched(`s`, `C`).

**Item classes** (for `verification` runs; first match wins):

1. **FLAKY** if either:
   - `s` is in the repo's flake baseline or selection-health's reproducible-flake set;
     or
   - two runs with the same complete fingerprint digest disagree on `s`: one has it, and
     the other completed the stage without it.

     This second clause **applies only to test-stage items** (pytest and cargo test).
     Lint stages read unfingerprinted state: tool versions (`sase-vr`) and bead state. A
     same-fingerprint flip there is not flake evidence.
2. **KNOWN**: at least one witness exists, and no clearing run is newer than the newest
   witness.
3. **NEW**: no FLAKY or KNOWN evidence, and either:
   - touched(`s`, `R`); or
   - a *pass witness* exists: a run at base(`R`) or a recent ancestor that completed the
     stage without `s` and did not touch `P(s)`.
4. **UNKNOWN**: everything else. Agent guidance: **UNKNOWN is yours.**

Never KNOWN:

- a bead or task title match;
- ad-hoc runs, as subjects or witnesses;
- a witness with a different `extra_args_digest`;
- evidence from another machine.

**Run verdict** (evaluated in order):

| Verdict | Condition |
| --- | --- |
| `pass` | exit 0 |
| `undetermined` | `failure_kind` ∈ {`control`, `infrastructure`, `environment`} |
| `new_failures` | at least one NEW item |
| `undetermined` | any UNKNOWN item; or a failed stage with no parsed item (it becomes one generic UNKNOWN item); or **no finish event** (some stage never ran; §4.5) |
| `no_new_failures` | every item KNOWN or FLAKY, and the recipe reached its finish event |

**Every label carries evidence refs:**

- witness run ids;
- distinct agent and workspace counts;
- first-seen time;
- the clearing run id, if any;
- the baseline file line or flake-oracle source;
- for UNKNOWN, the ordered rejection reasons (for example `no_witness`,
  `witness_cleared`, `untouched_no_pass_witness`, `extractor_generic`).

**Advisory REPEAT line.** When `R`'s fingerprint equals a prior failed run's fingerprint
with the same item set, the footer adds `REPEAT of <run>`. This is an annotation and
never a refusal. It serves sase's 19-of-19 deterministic repeats without harming
sase-core's flaky ones.

### 4.4 Signatures, extractors, and stage identity

**Extractors** are pure Rust over bounded stage output. They are auto-detected by output
shape, so v1 needs **no catalog change**. Minimum v1 set:

| Extractor | Signature key | Locator paths |
| --- | --- | --- |
| symvision | category + symbol + path | path |
| mypy | path + error code + message with quoted names masked; no line number | path |
| ruff, fmt (python, markdown), keep-sorted | rule or check + path | path |
| pytest (`FAILED` / `ERROR` lines) | node id without parametrization | test file |
| toobig | path | path |
| cargo test | crate::test path | none |
| environment (`_setup` markers) | marker kind | none |
| generic fallback | stage + hash of the normalized last ~40 lines | none |

**Normalization** strips:

- ANSI escapes, timestamps, durations, PIDs, and hex ids;
- workspace roots (`…/sase_<N>/`, `…/sase/repos/linked/<repo>/`);
- cargo target dirs and `/tmp` paths;
- line and column numbers, wherever the item kind is not positional.

Each extractor is versioned, and signatures from different versions are never compared
unless an explicit reclassification exists. Display text is bounded to 512 characters,
redacted, and never contains an absolute checkout path or an environment value.

**Stage identity.**

- The stable stage key is (`T`, top-level stage description).
- The random `stage_id` stays an execution-local address.
- Renaming a stage description breaks history continuity by design. Document it.
- **Nesting guard:** a `run_silent` stage's child processes cannot append stage events to
  the enclosing ToolRun. Either `run_silent` strips `SASE_TOOL_RUN_EVENTS` and
  `SASE_TOOL_RUN_ID` from the child environment, or the recorder drops events marked as
  nested. The mechanism is the planner's choice; the property is the gate.

### 4.5 Continuation ("unmasking") semantics

- **Humans and CI are unaffected.** `tools/run_silent` stays byte-for-byte fail-fast
  unless `sase tool run` exports `SASE_TOOL_CONTINUE`.
- **Modes.**
  - `never` is today's behavior.
  - `always` is `-k/--keep-going`.
  - `known` becomes the default for agent-invoked runs of `stages: run_silent` catalog
    tools once the flag is removed.
  - `-x/--fail-fast` forces `never`.
- **Decision in `known` mode.** On a stage failure, `run_silent` prints ✗ and the
  captured output exactly as today. It then calls a hidden internal verb
  (`sase tool _triage-stage`, like `_adopt`) that extracts, records, and classifies that
  stage's items.
  - The verb answers `continue` only when every item is KNOWN or FLAKY.
  - The call has a timeout of at most 10 s and is **fail-safe to stop**.
  - The decision and its evidence are recorded as a stage event.
- **Exit codes cannot be laundered.**
  - A final recipe line (`tools/run_silent --finish`) emits the finish event and exits
    with the first continued failure's code.
  - If the child exits 0 while the ledger holds a continued stage failure and no finish
    event, `sase tool run` records the run `failed` and exits 1 with a diagnostic.
  - This is the only deliberate exception to "preserve the child's exit status", and it
    applies only to continuation the wrapper itself enabled.
- **Cost.**
  - Always-continue would add about 125 s per failed run at the median, roughly +29% of
    `check` wall time (cld's estimate).
  - KNOWN-gated continuation spends that time only where earlier failures are not the
    agent's.
  - Record the extra seconds per run so the landing note can report the real number.

### 4.6 Surfaces

- **Compact footer of `sase tool run`:**
  - one line per failed stage, with class counts and a `continued`/`stopped` marker;
  - up to N items per class, NEW and UNKNOWN first;
  - "possible owner";
  - the REPEAT line;
  - the verdict line.

  `-T` keeps working.
- **`sase tool show RUN [-j]`** gains a versioned `triage` object: kind, items, classes,
  evidence refs, verdict, and continuation decisions. It must still work after the run's
  logs are reaped.
- **`sase tool failures`** lists signature groups for the current project, sorted by
  agent count. Columns: CLASS, TOOL/STAGE, SIGNATURE, RUNS, AGENTS, FIRST, LAST, OWNER.
  - Options, in help order: `-a/--all` (all projects), `-c/--class`, `-d/--days`
    (default 7), `-j/--json`, `-n/--limit`, `-t/--tool`.
  - An empty result prints "no recorded failures" and exits 0.
  - Aggregation runs in Rust.
- **`sase tool run`** gains `-k/--keep-going` and `-x/--fail-fast`.
- **Subcommand order** becomes `failures, list, run, runs, show, stop, wait`. Every
  option needs a short alias, per `cli_rules`.
- **Verify-monitor evidence.** When a monitor owns a ToolRun, its result evidence
  includes the triage object. The follow-up prompt shows the verdict, then NEW and
  UNKNOWN items first. This covers both E2-reserved runs and E1.5-wrapped raw
  `just check`.
- **Owner suggestion.** Match each item's locator token against open `ci`, `flake`, and
  `bug` task beads.
  - Show at most two matches, labeled "possible owner".
  - Show closed matches only as "possibly fixed by `<id>` — your HEAD may predate the
    fix".
  - Never create a bead or `+1` one.

### 4.7 Phases (7; one beta flag, `tool_failure_triage`)

Each phase that adds a binding sase calls also moves `sase-core-revision.txt` in that
same phase.

| # | Slug | Repo | Size | Content | Depends on |
| --- | --- | --- | --- | --- | --- |
| 1 | `core-failure-facts` | sase-core | large | New tables for items and durable finish diagnostics (**closes `sase-145`**); extractor registry, normalization, and golden fixtures from real redacted athena logs; retention under `tool_run_retention` (matching detail retention); bindings; pin | E2 landed |
| 2 | `core-classification` | sase-core | large | §4.3 as a pure function; verdict; `failures` aggregation; evidence refs; legacy-row mapping | 1, `sase-182` |
| 3 | `record-and-render` | sase | medium | Extraction at stage end and at settle (`stages: none` and linked repos at settle); nesting guard; footer; `show -j`; owner suggestion; REPEAT. Behind the flag | 2, `sase-114` |
| 4 | `keep-going` | sase | medium | `run_silent` continuation protocol, `--finish`, executor safety net, `-k`/`-x`. Opt-in and complete by itself, so no flag | E2 landed (may run in parallel with 1–3) |
| 5 | `known-gated-continuation` | sase | medium | `_triage-stage`; bounded fail-safe decision; `known` as the agent default behind the flag; recorded decisions | 3, 4 |
| 6 | `failures-and-continuations` | sase | medium | `sase tool failures`; triage in verify-monitor evidence and follow-up prompts (flat `monitor_*` field names; mind the in-flight `sase-17m` rename) | 3 |
| 7 | `backtest-acceptance-governance` | sase | medium | `tools/tool_triage_backtest`, the audit, live athena acceptance, flag removal, docs, memory, glossary, decision record | 1–6 |

### 4.8 E3 landing criteria: all must hold, and none may require a green `check`

- [ ] **DoD-0: prerequisites.** `sase-182` and `sase-114` are closed. `sase-145` is
  closed by phase 1 with a close note citing the E3 commit.
- [ ] **DoD-1: signatures.**
  - Every extractor in §4.4 has at least one golden fixture from a real athena log.
  - The same failure observed from two different workspaces yields one digest.
  - Collision fixtures prove that different node ids, symbols, error codes, or paths
    yield different digests.
  - Display text is at most 512 characters and contains no absolute checkout path or
    environment value.
  - Extractor versions are stored, and cross-version comparison is refused.
- [ ] **DoD-2: durable facts.** On a settled run whose retained logs have been reaped,
  `sase tool show RUN -j` still shows its items, classes, and evidence. The run also
  explains its own spawn 127/126 reason, stage-ingest diagnostics, and log-write facts
  (`sase-145`'s acceptance).
- [ ] **DoD-3: run kinds.**
  - Fixtures for `timeout`, `stop_requested`, `interrupt`, `owner_lost`,
    `wrapper_lost`, `launch_failed`, and `signal` each produce the kind in §4.3 and
    **no item labels**.
  - A `_setup` failure with a missing binding produces `environment` with a remedy.
  - Pre-E2 legacy rows map per the documented table, and unmapped rows get
    `legacy_unmapped`.
- [ ] **DoD-4: classification fixtures.** A fixture ledger produces exactly these
  results:
  - (a) an item witnessed by another workspace at an ancestor HEAD → KNOWN, citing the
    witness;
  - (b) touched, with no witness → NEW;
  - (c) listed in the flake baseline → FLAKY;
  - (d) a pytest fail→pass on an identical complete fingerprint → FLAKY;
  - (e) the same flip in a **symvision** stage → **not** FLAKY;
  - (f) untouched with no evidence → UNKNOWN, with reason `untouched_no_pass_witness`;
  - (g) a witness cleared by a newer ancestor run that completed the stage → not KNOWN;
  - (h) an ad-hoc run, or a different `extra_args_digest`, is never a witness;
  - (i) an open bead whose title matches the item, with no witness → UNKNOWN, not KNOWN;
  - (j) a sase-core item never witnesses a sase item, and the reverse also holds.
- [ ] **DoD-5: precision backtest. This is the gate.** `tools/tool_triage_backtest`
  replays athena's ledger chronologically using only prior evidence. The landing note
  publishes all of the following:
  - the label distribution;
  - a random, hand-audited sample of at least 50 KNOWN labels, with **at least 95%
    judged pre-existing**;
  - **zero** KNOWN labels on items in files that the run's own diff *added*;
  - every KNOWN-but-touched item, each dispositioned.

  If precision is below 95%, tighten the rule (for example, require two independent
  witnesses or a clean-tree witness). Never relax the audit.
- [ ] **DoD-6: continuation safety.**
  - Human and CI `just check` output is byte-identical to the pre-epic output (golden).
  - Under `-k`, a fixture `[fail, pass, fail, pass]` records all 4 stages and exits with
    stage 1's code.
  - A property test shows that no combination of stage outcomes, missing `--finish`, or
    helper timeout or crash yields exit 0 when any stage failed.
  - `-x` restores fail-fast.
- [ ] **DoD-7: gated continuation.**
  - In the agent default mode, a stage whose items are all KNOWN or FLAKY continues.
  - Any NEW or UNKNOWN item stops the run.
  - A helper timeout (over 10 s, simulated) or crash stops the run.
  - Each decision appears in `show -j` with its evidence.
- [ ] **DoD-8: honest surfaces.**
  - The exit code of `sase tool run` equals the child's in every fixture, except for the
    DoD-6 safety net.
  - The verdict is one of the four values.
  - `no_new_failures` is never printed without a finish event or with any UNKNOWN item.
  - The footer, `show -j`, `failures -j`, and monitor evidence agree on ids and labels.
  - Every JSON surface carries a schema version.
- [ ] **DoD-9: `failures` on real data.**
  - On athena, `sase tool failures` lists the current red-master groups, with agent
    counts that match a direct ledger query recorded in the landing note.
  - Linked-repo groups never appear under sase's `check`.
  - An empty result exits 0.
- [ ] **DoD-10: continuations.** A `sase monitor start -p verify … -- sase tool run check`
  on a red-master tree delivers a follow-up prompt with the verdict and the NEW and
  UNKNOWN items, and the starter supplied no baseline prose. This holds for both a
  monitor-reserved ToolRun and a wrapped raw `just check`.
- [ ] **DoD-11: no automatic writes.** A test asserts that E3's code paths create and
  `+1` zero beads. Suggestions contain only the "possible owner" wording.
- [ ] **DoD-12: compatibility.**
  - Wire `schema_version` stays 1: only new tables or nullable columns, and no new
    values in existing enums.
  - An older pinned core still opens the store.
  - `ToolDefinitionWire` is unchanged, and the sase `check` definition digest is
    unchanged by E3.
  - The pin moves in the same phase as each new binding.
- [ ] **DoD-13: governance.** Every memory change goes through `/sase_memory_write`.
  - The `tool_failure_triage` flag is removed, and its flag bead is closed.
  - `docs/tool.md` documents kinds, classes, rules, continuation, verdicts, and
    `failures`.
  - `sase/memory/lint_and_test.md` says:
    - UNKNOWN is yours;
    - never call a failure "unrelated" without a KNOWN or FLAKY label or equivalent
      evidence;
    - never `+1` a bead for an item E3 already linked.
  - The symvision memory notes that master-red items are labeled KNOWN.
  - New glossary strands exist for **Failure Signature** and **Triage Verdict**.
  - A new decision record exists: *"Triage annotates; it never changes an exit code, and
    KNOWN requires an independent witness."*
- [ ] **DoD-14: green-master independence.** Acceptance uses fixture ledgers and fixture
  recipes plus the live red master. The epic's own new tests pass. Pre-existing
  master-red items are not landing blockers.

**Post-landing measurement** (an owner check, not a gate). After 7 days, report:

- the share of failed `check` runs that reached `test (scoped)` (baseline 11.5%);
- the share of agents whose final run executed tests (baseline 24%);
- extra continuation wall time per day;
- the re-run backtest.

### 4.9 E3 risks, reopen conditions, and decisions the planner must settle

- **False KNOWN is the dangerous error.** Mitigations:
  - the independence and clearing rules;
  - DoD-5;
  - UNKNOWN as the default;
  - evidence refs shown in the footer, so an agent can check a label.
- **Masked evidence feeds itself.** Before E3, most runs never reached later stages, so
  early evidence exists mostly for lint stages. The selection-health witness source
  (§2.6) partly compensates, and continuation fixes it over time.
- **Thin ledgers.** apollo and mac will be mostly UNKNOWN. That is correct.
- **`rerun` reopens** if the ledger shows more than about 2 h/week of manual re-runs of
  FLAKY-labeled items. It would then be a new ToolRun with a new `retry_of_run_id`
  (immediate predecessor), `retry_root_run_id`, and ordinal, for opted-in named tools
  only (cdx's design). It must never be attempt N of a settled run and never reuse
  `parent_run_id`.
- **CI evidence reopens** if UNKNOWN stays above about 40% of items on a machine. Master
  Gate's per-SHA results would then become a second witness source.
- **Planner must settle:**
  1. the helper mechanism for `known` mode (recommended: the hidden-verb subprocess);
  2. `L` and the ancestry depth (recommended: 7 days and 2,000 commits);
  3. whether selection-health full-run records are witnesses in v1 (recommended: yes,
     through the same pure function);
  4. footer item caps;
  5. the legacy-row mapping table.

---

## 5. E4, re-scoped: "Verified completion: fingerprint-bound verdict receipts"

### 5.1 Why not as written

| Roadmap E4 element | Evidence | Disposition |
| --- | --- | --- |
| Second `check` on an unchanged tree returns instantly | 0 opportunities, both digest-keyed and content-addressed (§2.3) | Defer to E4b |
| `just install` no-ops | 1 wrapped run; `install` is unguarded by decision; `_setup` validator already skips | Defer to E4b |
| Lint failure stops before the heavy stage | Already true by stage order; the lint prefix *is* the heavy part (247 s) | Drop |
| Cheap stages inline before hand-off, per-stage receipts | No `-H` runs recorded yet; stages declare no inputs, outputs, or DAG; would change E2's prompt `-H` contract | Defer to E4b |
| Unchanged-since-failure refusal | Wrong in 9 of 11 sase-core repeats; gem's `exited`-only guard does not help | Drop; E3's advisory REPEAT replaces it |
| `receipt TOOL` for scripts and landers; host policy decides sufficiency | Valuable, as proof | **Keep** |

Building reuse with a measured payoff of zero is the corpus-before-mechanism error that
`decisions:record-before-admit` exists to prevent. `decisions:guarded-recipes` also warns
against a receipt silently changing what a run does.

### 5.2 What survives, and its consumer

A durable, fingerprint-bound record that *this exact tree* was verified, with verdict
`pass` or E3's `no_new_failures`. Its value is **proof**, not skipped work:

1. **Prepared host completion** commits the verified tree only if a receipt covers it
   with an acceptable verdict, and refuses if the tree changed after verification.
   Today it fires only on exit 0, so on a red master it never fires (§2.5).
2. **Landers and scripts** use `sase tool receipt check` to ask "has this exact tree
   passed, or passed modulo KNOWN?", with exit 0 or 1 and a typed reason.
3. **Audit trail.** Host commits and bead closes carry the covering receipt (run id,
   verdict, KNOWN list) or say "unverified". Verified landings become distinguishable
   from asserted ones. This is non-blocking on the ordinary `/sase_final` path.

This depends on a **policy change you must approve (§7 Q1)**: host completion may commit
when failures remain but every one is KNOWN or FLAKY. It is *stricter* than today's
ordinary `/sase_final` path, which commits on the agent's unaudited "unrelated" judgment.
But it is a mechanical commit on a red run.

### 5.3 Receipt contract

- **Mint** at settle, in both the foreground executor and the hand-off worker, only when
  all of the following hold:
  - the named tool's catalog policy opts in;
  - `fingerprint_before` and `fingerprint_after` are complete and equal
    (`mutated_input = false`);
  - `settled_by = wrapper`;
  - the run is not ad-hoc and not bypassed;
  - the verdict is in the policy's accepted set: `pass` always, and `no_new_failures`
    only if the policy lists it.

  Never mint from `control`, `infrastructure`, or `environment` kinds, from
  `new_failures`, or from `undetermined`.
- **A receipt holds:**
  - tool identity (catalog repo + name + definition digest);
  - `extra_args_digest` and the fingerprint digest;
  - the verdict and its KNOWN/FLAKY signature refs;
  - the source run id;
  - minted and expiry times;
  - the policy version.

  It contains digests and metadata only, never argv secrets, environment values, or
  output bytes.
- **Invalidation.** A later non-success of the same identity and fingerprint blocks an
  older receipt until a later eligible success (cdx). Expiry is a miss, not a deletion.
- **Lookup** (Rust): `receipt_lookup(identity, current fingerprint, accept)` returns
  either `covered(receipt)` or a typed refusal: `no_receipt`, `fingerprint_changed`
  (with the changed paths), `expired`, `incomplete_fingerprint`, `verdict_insufficient`,
  `definition_changed`, or `invalidated_by_later_run`.
- **Catalog policy block.**
  - Add a `receipt:` policy block (`{accept: [pass, no_new_failures], ttl: 2h}`),
    **excluded from `ToolDefinitionIdentity`** so policy edits do not reset TYPICAL or
    E6's corpus. The same rule applies to `sase-17e`'s duration class and E7's demand.
  - `ToolDefinitionWire` is `deny_unknown_fields`, so the core floor that accepts the
    block must ship and be pinned **before** any catalog uses it. Document the rollout
    order.
  - Each tool carries a literal TTL: at most 2 h for `check`, because of unfingerprinted
    bead state, unless the bead-state probe below lands. There is no global fallback.
- **Hermeticity.**
  - Add lint-tool version probes (ruff, mypy, symvision, prettier) to the `check` and
    `check-full` toolchains, and coordinate with `sase-vr`.
  - Either add a bounded probe that digests the bead state the lints read, or rely on
    the TTL, and document which.
  - These fingerprint-spec changes **do** move the definition digest. That is correct,
    happens once, and the plan must state it.
- **No skipping, ever, in E4.** Every `sase tool run` spawns its child.

### 5.4 Completion gating

- A prepared-completion intent gains an `accept` policy. The default is `pass`, which is
  byte-identical to today.
- With `accept: no-new`, the verify-monitor outcome policy treats a ToolRun verdict of
  `no_new_failures` as completion-eligible.
- At commit time, the host re-fingerprints the checkout and commits only if
  `receipt_lookup` returns `covered`. Otherwise it launches the ordinary recovery
  follow-up with the typed refusal.
- The commit and bead-close notes carry the receipt id and the KNOWN list.
- **Precision precondition:** E4's first phase re-runs E3's backtest. `no-new` acceptance
  stays unavailable if KNOWN precision has fallen below 95%.

### 5.5 Phases (5; one beta flag, `tool_receipts`; start after E3 lands)

| # | Slug | Repo | Size | Content |
| --- | --- | --- | --- | --- |
| 1 | `hermetic-fingerprints` | sase + linked catalogs | medium | Lint-tool version probes; bead-state probe or TTL rationale; probe overhead within E1's budgets (at most 1 s per probe, 2 s total); E3 backtest re-run |
| 2 | `core-receipts` | sase-core | large | Receipt table (additive); mint, invalidation, and lookup with typed refusals; `receipt:` policy block excluded from identity; retention and `sase disk` coverage; bindings; pin |
| 3 | `receipt-cli` | sase | medium | `sase tool receipt TOOL [-a/--accept {pass,no-new}] [-j/--json]` (exit 0 covered, 1 not covered, 2 usage); `sase tool receipts [-d/--days N] [-j/--json]` (receipts plus the **content-addressed** reuse-opportunity report that decides E4b); minting in both executor paths |
| 4 | `verdict-gated-completion` | sase | large | §5.4; recovery refusals; commit and bead-close provenance; non-blocking provenance on the ordinary `/sase_final` path |
| 5 | `acceptance-and-adoption` | sase | medium | Live athena demo; flag removal; docs; `lint_and_test.md`; `sase_final` and `sase_monitor` skill sources (preview with `sase skill init --diff`, per `generated_skills`); glossary **Receipt**; decision record *"Receipts prove before they skip; reuse waits for measured opportunity."* |

### 5.6 E4 landing criteria: all must hold

- [ ] **DoD-1: hermeticity.**
  - A fixture shows that changing the ruff (or mypy, or symvision) version makes
    `receipt check` exit 1 with `fingerprint_changed` or `definition_changed`.
  - A fixture shows that closing an epic-symbol bead makes it exit 1 with the matching
    reason, or else that the TTL lapse does.
- [ ] **DoD-2: minting.** Each of these has a negative test asserting no receipt row:
  - ad-hoc, bypassed, `mutated_input = true`, incomplete-fingerprint, and
    `settled_by ≠ wrapper` runs;
  - `control`, `infrastructure`, and `environment` kinds;
  - `new_failures` and `undetermined`;
  - `no_new_failures` for a tool whose policy does not accept it.
- [ ] **DoD-3: invalidation.** A later same-fingerprint non-success blocks an older
  receipt until a later eligible success. TTL expiry is tested with an injectable clock,
  with no long sleeps.
- [ ] **DoD-4: query.**
  - On a just-verified tree, `sase tool receipt check` exits 0 and prints the receipt,
    run, verdict, and age.
  - After touching any tracked file, it exits 1 with `fingerprint_changed: <path>`.
  - `-j` is versioned.
  - No output claims a landing gate is "satisfied".
- [ ] **DoD-5: completion gating.** Fixtures cover all of these, plus one live athena
  demonstration:
  - With `accept: no-new` and a `no_new_failures` run, completion commits exactly the
    verified tree.
  - It does **not** commit when:
    - any NEW or UNKNOWN item exists;
    - the tree changed after verification;
    - the receipt expired;
    - the receipt was invalidated.
  - Each refusal hands off to the recovery follow-up with its typed reason.
  - With the default `accept: pass`, behavior is byte-identical to today (golden).
- [ ] **DoD-6: never skips.** A test asserts that every `sase tool run` spawns its
  child, even when a covering receipt exists.
- [ ] **DoD-7: compatibility.**
  - Additive wire at schema 1.
  - An older core opens the store.
  - The `receipt:` block does not move any definition digest.
  - The core floor accepting the block is pinned before any catalog uses it.
  - Retention never leaves a dangling receipt reference without an explanation.
- [ ] **DoD-8: reuse-opportunity report.** `sase tool receipts` reports covered repeats
  (runs, hours, top tools) computed **content-addressed**, not by HEAD-keyed digest. A
  fixture in which a verified dirty tree is committed and then re-checked at the new
  commit counts as one covered repeat.
- [ ] **DoD-9: governance.** The flag is removed and its flag bead closed. Docs, memory,
  skill sources, the glossary strand, and the decision record exist per phase 5, and
  every memory change goes through `/sase_memory_write`.

**Post-landing measurement** (an owner check). After 14 days, publish:

- the reuse-opportunity report;
- the number of prepared-completion commits (baseline 0);
- each completion refused for `fingerprint_changed` (a real integrity catch).

### 5.7 Explicitly out of E4

- skipping execution, including `-R/--force` and "returns instantly";
- `install` reuse;
- cheap-stages-inline and per-stage receipts;
- unchanged-since-failure refusal;
- cross-machine receipts;
- any redirect of raw `just check`.

### 5.8 E4b (reuse) reopen trigger

Plan a reuse epic only when all of the following hold:

- `sase tool receipts` (or the appendix's offline query) shows **at least 2 h/week of
  content-addressed covered repeats** for one tool on one machine;
- this holds for **two consecutive weeks**;
- the tool has passed DoD-1 hermeticity.

Reuse then ships opt-in per tool, never as a silent change to raw recipes.

- **Install reuse** additionally requires `install` to be wrapped, and evidence that
  `_setup`'s validator misses real work.
- **Per-stage reuse** additionally requires declared stage inputs and outputs.
- **Cheap-stages-inline** requires post-E2 data showing material `-H` failures that
  complete under about 60 s.

### 5.9 If the answer to §7 Q1 is no: defer E4

What remains without the completion policy is small: the `receipt` query, audit
provenance, and the opportunity report. None of E5–E8 needs it.

- File the lint-tool version probes (`sase-vr`) as ordinary tasks; E3 does not depend on
  them (§4.3, rule 1).
- Keep the appendix query as the E4b trigger.
- You give up the only route found to making prepared completion usable while master is
  red.

---

## 6. Cross-epic rules for E3, E4, and their successors

1. **Wire discipline.** Additive only, `schema_version` 1, only new tables or nullable
   columns, and class and kind strings live in new tables. No new values in existing
   enums.
2. **Pin ratchet in-phase.** Every phase that adds a binding sase calls moves
   `sase-core-revision.txt` in the same phase (`docs/rust_backend.md`). `sase-17p` shipped
   with its pin behind its own bindings, and `validate_sase_core_rs` refused pinned
   builds.
3. **Policy fields never move the definition digest.** This covers E4's `receipt:`,
   `sase-17e`'s duration class, and E7's demand. Changes to execution identity (inputs,
   toolchain probes) *should* move it. `deny_unknown_fields` means the core floor ships
   before any catalog uses a new field.
4. **Tool identity is the catalog's repo** (`sase-182`) everywhere evidence is keyed:
   triage, receipts, forecasts, admission.
5. **Stage identity is the top-level stage description.** Nested stage events are never
   recorded.
6. **Honesty invariants.**
   - Exit codes are the child's, except for E3's anti-laundering net.
   - Nothing unknown is presented as known.
   - Nothing is auto-created.
   - Human and JSON output are two views of the same stored facts.
7. **Green-master independence and fixture-based acceptance.** No DoD requires a green
   `check`.
8. **Continuation changes whole-run durations.** E6 must forecast from stage-level
   durations, or condition on the recorded `continued` flag.
9. **One beta flag per epic.** Its old branch must be real, and it is removed before
   landing.
10. **Vocabulary.**
    - New monitor and session fields follow E2's flat `monitor_*` convention and the
      in-flight `sase-17m` rename.
    - `parent_run_id` keeps meaning "nested run".
    - Glossary strands change only through `/sase_memory_write`.

**Interactions:**

- **`sase-180`** (toobig splits redden symvision) is complementary: E3 contains the
  damage, and `sase-180` removes a cause.
- **`sase-j0`, `sase-th`, and `sase-10w`** (red lanes) are fixtures, not blockers.
- **`sase-17e` and `sase-17g`** are orthogonal except for rule 3.
- **E5** can proceed after `sase-124`, but its Failures view renders E3's contract, so
  that view waits for E3.
- **E6** still starts on corpus age, about three weeks after E1 (around 2026-10-11).

---

## 7. Open questions for Bryan

1. **May prepared host completion commit when every failure is KNOWN or FLAKY
   (`no_new_failures`), per intent and opt-in?**
   - This decides E4. Recommended: **yes**, because it is stricter than today's ordinary
     `/sase_final` path.
   - No → defer E4 (§5.9).
2. **Continuation default for agents.** KNOWN-gated (recommended), always-on (+29% wall
   time, simplest), or opt-in `-k` only (cheapest, but opt-in features historically go
   unadopted)?
3. **Drop `rerun` from E3**, with the §4.9 reopen condition? Three of the four
   researchers kept it. The evidence (passive same-fingerprint FLAKY detection, E2's
   one-shot claim) says drop.
4. **Write the E3 decision record now or at landing?** *"Triage annotates; KNOWN requires
   an independent witness."* Now prevents re-litigation during planning.
5. **Amend the roadmap?** §8 provides replacement rows. The planner should cite this
   report either way.

---

## 8. Replacement roadmap rows

| # | Epic | Size | User-verifiable result |
| --- | --- | --- | --- |
| **E3** | Failure triage: every failure labeled, no KNOWN failure hides the rest | large (7) | On a red master, an agent's `sase tool run check` runs past all-KNOWN/FLAKY stages to the tests, labels every item NEW/KNOWN/FLAKY/UNKNOWN with evidence, prints one verdict, and keeps the child's exit code; `sase tool failures` groups the machine's red-master signatures |
| **E4** | Verified completion: fingerprint-bound verdict receipts *(conditional on §7 Q1; otherwise deferred)* | medium-large (5) | `sase tool receipt check` proves this exact tree passed or had no NEW failures; prepared completion commits exactly that tree and refuses on drift, expiry, or NEW/UNKNOWN; nothing is ever skipped |
| **E4b** | Receipt reuse *(conditional)* | TBD | Opens only on the §5.8 trigger |

**Revised sequencing:** E1 → E2 → prerequisites (`sase-182`, `sase-114`) → E3 → {E5 when
`sase-124` allows; E4 after E3's backtest and Q1} → E6 (corpus age) → E7 → E8.

---

## Appendix: method, verification, and caveats

**Ledger** (read-only SQLite on `~/.sase/tools/runs.sqlite`, 648 runs, 2026-09-20 07:26
to 2026-09-24 15:33, `meta.schema_version = 1`):

- **sase `check` subset.** Definition digest `12b1748a5c…`.
- **Stage reach and first failing stage.** Taken from the `stages` rows.
- **Prefix time.** The first stage's `started_ts` to the start of `test (scoped)`, over
  the 101 runs that reached it.
- **Digest repeats.** SHA-256 over the fingerprint identity fields, mirroring
  `fingerprint_digest()` in `sase-core` `tool_run/fingerprint.rs`, on complete
  fingerprints only.
- **Content-addressed repeats** (470 complete sase `check` fingerprints, 200 distinct
  HEADs):
  - Let `U` = the union of the paths changed between any HEAD and the oldest HEAD, plus
    every dirty path (3,529 paths).
  - A run's content key is, over `U`: the dirty `content_hash` where the path is dirty,
    otherwise the HEAD blob. Blobs of ever-dirty paths are converted to SHA-256 via
    `git cat-file --batch`.
  - I confirmed that `content_hash` is the SHA-256 of the file bytes.
  - The key was computed with and without `extra_args_digest`, env, and toolchain.
  - Result: 0 repeats after a pass in both variants.
- **Fixture contamination.** Runs whose stage descriptions fall outside the recipe's 15
  top-level stages, or repeat.

**Other stores:**

- `sase monitor list -a -j`: 1,378 rows.
  - Prepared completion is a non-null `completion_ref` or `host_completion_status`: 6
    rows.
  - The store holds 209 verify-profile monitors over its lifetime: 130 failed, 62
    completed, 17 timed out.
- `~/.sase/test-selection/gh_sase-org__sase/`: 3,843 records, of which 1,846 are
  full-run records.

**Code read:**

- sase:
  - `Justfile` (`check`, `check-full`, `_setup`);
  - `tools/run_silent`;
  - `tools/selection_health` and `tests/_test_selection_health_{store,records}.py`;
  - `tests/reproducible_flake_baseline.txt`;
  - `tests/monitor/test_continuation_baseline.py`;
  - `src/sase/tool/ownership.py`;
  - `src/sase/monitor/host_completion.py`.
- sase-core (pin `6d0d0e6d5c`):
  - `tool_run/catalog.rs` (`ToolDefinitionIdentity`);
  - `fingerprint.rs`;
  - `wire.rs` (attempt fields);
  - `handoff_wire.rs` (`ToolRunTerminalCauseWire`, `AlreadyClaimed`);
  - `store/handoff.rs`.

**Beads read:** `sase-17p`, `sase-182`, `sase-145`, `sase-180`, `sase-vr`, `sase-17e`,
`sase-17g`, `sase-114`. I added a +1 to `sase-114` with the ToolRun-ledger evidence; no
new bead was filed.

**Artifacts:**

- the roadmap (`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md`);
- the E2 plan (`plan:202609/tool_e2_durable_handoff.md`, decision 6 and the catalog
  note);
- the four researcher reports in this directory.

**Decision records:** `check-full-is-explicit`, `guarded-recipes`, `host-owned-completion`,
and `corpus-before-mechanism`, plus `cli_rules.md`.

**Caveats:**

- **Athena only.** apollo's and mac's ledgers are unmeasured. Re-run the E3 backtest and
  the content-addressed repeat query there before E4 is planned.
- **Short window, red master.** The window is 4.3 days, and the red master suppresses
  passes: 37 in total.
- **cld's replay was not re-run.** Its 72/7/21 split and 47% figure are feasibility
  estimates.
- **Remaining cld numbers were not re-derived.** The continuation cost (+125 s, +29%),
  the verify-failure floor (87 s), and the `--next` length (1,052 chars) are cited from
  cld.
- **Untracked files.** They are included in fingerprints as `untracked` entries with
  content hashes, and the content key treats them like dirty paths.
