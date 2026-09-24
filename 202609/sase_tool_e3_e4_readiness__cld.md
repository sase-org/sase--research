# `sase tool` E3 and E4 after E2: are they still right, and what exactly must they land?

**Researcher cld** · 2026-09-24 · host athena · sase master `71736697d`
(`sase-17p.5` landed; `sase-17p.6` in progress) · core pin `6d0d0e6d5c`

**Question.** E2 (`sase-17p`) is nearly done. Are E3 ("Failure triage: NEW vs KNOWN vs
FLAKY") and E4 ("Verification receipts and staged reuse"), as defined in
`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` (§1, §4), still
correct and appropriate? What should change? And what are the landing criteria, stated
precisely enough that the planning, implementing, and landing agents cannot disagree
about them?

**Method.** I measured E1's ToolRun ledger on athena instead of reasoning from the
roadmap's 2026-09-17 premises: 638 runs, 2026-09-20 07:26 → 2026-09-24 14:25 local,
with every run's stage timeline, fingerprints, and retained logs. I also used athena's
monitor store (1,376 rows), the bead store, the E1/E1.5/E2 plans and landing notes, the
decision records, and the code on master plus the pinned sase-core. The appendix lists
every measurement and its caveats.

---

## 1. Answer up front

**E3: yes. Do it next. It is worth much more than the roadmap estimated, but three
changes are needed before it is planned.**

The roadmap motivated E3 with apollo's `check-full` re-discovery waste. That workload
has since disappeared: `decisions:check-full-is-explicit` landed mid-E1, and athena
recorded one `check-full` run in four days. The waste moved to plain `check`, and it is
worse than the roadmap assumed:

- **85% of sase `check` runs fail** (417 of 488). Only 37 passed in 4.2 days.
- **55% of failures stop at `lint (symvision)`.** In 79% of those, every reported symbol
  sits in a file the run's own diff never touched. The same items recur across 23–28
  distinct agents.
- **`just check` is fail-fast.** A master-red lint stage therefore hides every later
  stage. The scoped test stage executed in **21%** of `check` runs. Of 317 agents that
  ran `check`, **76% finished on a run whose tests never executed**, and only 11%
  finished on a passing run.

The user's own bead `sase-180` describes the same mechanism ("a red stage 1 then hides
stages 2 and 3 … every agent's `just check` stops before the test lane").

E3 therefore has to deliver three things:

1. **Retarget from `check-full` to `check`.**
2. **Add stage continuation past KNOWN failures ("unmasking").** Without it, a label says
   "not yours" but the agent still gets no test signal.
3. **Gate KNOWN on a measured precision backtest.**

A rough replay of the classification rule I recommend (§4.3), using only prior evidence,
labels 72% of failure items KNOWN, 7% NEW, and 21% UNKNOWN. It would give **47% of
failed runs** an honest "no NEW failures" verdict.

**E4: no, not as written. Its own go/no-go test has now been run, and it says no.**

The roadmap and its researcher B said the payoff of receipts was unmeasurable until E1
recorded tree fingerprints, and that E4 should ship as "a separate, measured epic." E1
now records them. The results:

- **Pass receipts would have saved nothing.** Across 518 fingerprinted `check` runs
  (all repos), **zero** re-ran a fingerprint that had already passed.
- **"Unchanged since failure" refusal would have been wrong most of the time where it
  would fire.** In sase-core, 9 of 11 re-runs of a failed fingerprint passed (flaky
  tests). In sase, 18 of 18 failed again, which is correct but low value (about 1.4
  hours in 4 days).
- **"Cheap stages first" is false for `check`.** The lint prefix takes about 4.3 minutes
  at the median; the scoped test stage takes 52 seconds.
- **Hand-offs do not fail fast.** No verify hand-off on athena failed in under 87
  seconds, so running cheap stages before a hand-off would not save a turn boundary.
- **`install` is not wrapped.** One recorded run in four days.
- **`check` is not hermetic with respect to its fingerprint.** Lint tool versions are
  missing from it (`sase-vr`), and symvision and feature-flag lint read bead-store
  state.

**Recommendation:** re-scope E4 to the part of the receipt idea that the data supports,
and sequence it after E3.

- **Receipts become fingerprint-bound proof.** A receipt records that this exact tree
  passed, or finished with **no NEW failures**. It is not a cache.
- **Host completion is the consumer.** Prepared completion is the documented way to land
  verified work "with no further turn", yet it has **never committed on athena since
  E1**: 6 uses, 5 failed on master-red `check`, and 1 hit a recovery error. It cannot
  work while `check` is almost never green.
- **Reuse is measured, not built.** An offline report can recompute repeat-after-pass
  opportunities from the ledger at any time. Reuse should become a follow-on epic only
  if that number crosses a stated threshold.

If you would rather not take on the policy question of committing under KNOWN-only
failures (§5.2), the honest alternative is to **defer E4 entirely**. Nothing downstream
depends on it: E5–E8 do not consume receipts.

**Prerequisite discovered and filed:** **`sase-182`** (bug, medium, ready). Linked-repo
ToolRuns are recorded under the host project's identity. All 51 sase-core, telegram,
github, and research-artifacts `check` runs on athena are labeled
`gh_sase-org__sase`, because `tool_project_identity()` prefers `SASE_PROJECT` over the
catalog's repo. E3 and E4 both key evidence on tool identity, and they would mix sase's
deterministic failures with sase-core's flaky ones. Fix it before E3's classification
phase.

**Sequencing:**

1. Finish E2 (`sase-17p.6`).
2. Land `sase-182`.
3. Plan and start E3 now. Its first phase is small and opt-in.
4. E5 follows E3, because its Failures view needs E3's contract.
5. Plan re-scoped E4 only after E3's precision backtest is in hand.
6. E6 still starts on corpus age (about three weeks after E1, i.e. around 2026-10-11),
   using stage-level durations (§6).

---

## 2. What changed since the roadmap (2026-09-17)

| Change | When | Consequence for E3/E4 |
| --- | --- | --- |
| E1 `sase-135` landed (named tools, ledger, fingerprints, stages, samples) | 2026-09-20 | Everything below is now measurable. The ledger is the evidence store E3 needs; no new corpus is required. |
| `decisions:check-full-is-explicit` (landers no longer run `check-full`) | mid-E1 | E3's roadmap demo ("`check-full` labels the suite-cost failures KNOWN") and apollo's 16.24 h `check-full` waste are obsolete. The target is `check`. |
| `decisions:ci-two-speed-split` (Master Gate per SHA, Full CI every 2 h) | earlier | A per-SHA CI baseline exists and could later serve as authoritative KNOWN evidence (§4.8), but it is remote. |
| E1.5 `sase-16h` (recipe guard, monitor wrapping, linked-repo catalogs) | 2026-09-22 | Nearly every agent `check` is now a ToolRun, so triage and receipts reach them all. Linked-repo catalogs exposed the `sase-182` identity bug. |
| `decisions:guarded-recipes` (partly supersedes record-before-admit) | 2026-09-22 | "Refuse, don't redirect". It warns that a receipt or auto-route must never silently change what a raw `just check` does. That constrains E4 reuse. |
| E2 `sase-17p` (reservation, claim, stop/wait/follow, typed `terminal_cause`, `settled_by`, one-delivery) | phases 1–5 landed 2026-09-24 | E3's verification-vs-infra split comes free from `terminal_cause`. Monitor ↔ ToolRun linkage (`tool_run_id`) lets E3 put triage into continuations. E2's at-most-once claim rule conflicts with the roadmap's `rerun` attempt chains (§4.9). |
| E2 kept the wire additive (schema 1, no new enum values) because several sase venvs share `~/.sase/tools/runs.sqlite` | E2 plan decision 6 | E3 and E4 must follow the same rule: new tables and nullable columns only, class strings in new tables, no new values in existing enums. |
| Recurring master-red lint (`sase-13l`, `-13s`, `-16l`, `-16u`, `-17c`, `-17j`, `-17l`, `-150`, `-15c`, `-16m`; `sase-180` names the masking) | the whole week | This is the main production workload E3 must handle. It is also a live fixture. |
| `sase-17e` (duration classes in the catalog), `sase-17g` (detach/join) | filed 09-23 | These are also catalog-field consumers. See the digest rule in §6. |

---

## 3. Evidence

All numbers are athena, sase-repo `check` (definition digest `12b1748a5c…`) unless
stated otherwise. The window is 4.2 days.

### 3.1 `check` is red almost always, and the red hides the tests

| Measure | Value |
| --- | --- |
| sase `check` runs | 488. 37 succeeded (7.6%), 417 failed (85.5%), 22 lost, 12 signaled |
| `check` wall time | 58.5 h. Median 211 s, p90 1,029 s. Passing median 274 s |
| Runs in which `test (scoped)` executed at all | **101 / 488 (21%)**. Only 49 of 417 failed runs reached it (12%) |
| Agents that ran `check` | 317. Their **last** run executed tests in 77 cases (24%) and passed in 36 (11%) |
| Daily passes | 09-20: 1 · 09-21: 14 · 09-22: 19 · 09-23: 3 of 151 · 09-24: 0 so far |
| Clean-tree runs (no dirty paths) | 15, **all failed** (8 at symvision) |

First failing stage among 433 failed `check` runs with a recorded failing stage:

| Stage | Runs | Share |
| --- | --- | --- |
| `lint (symvision)` | 239 | 55% |
| `lint (mypy)` | 77 | 18% |
| `test (scoped)` | 49 | 11% |
| `fmt (python)` | 19 | 4% |
| `lint (pyscripts)` | 17 | 4% |
| `lint (feature flags)` | 14 | 3% |
| other (fmt md, toobig, validation, test waits, ruff) | 18 | 4% |

A further 28 failed runs recorded no stages. These are the linked repos' `stages: none`
checks, plus `_setup` failures such as
`validate_sase_core_rs missing required binding(s): tool_run_claim, tool_run_request_stop`.

### 3.2 The "cheap lint stages" are not cheap

Median seconds for passing stages:

| Stage | Median (s) | Stage | Median (s) |
| --- | --- | --- | --- |
| SASE validation | 66 | `lint (test waits)` | 19 |
| `lint (feature flags)` | 59 | `lint (pyscripts)` | 19 |
| **`test (scoped)`** | **52** | `fmt (markdown)` | 11 |
| `lint (mypy)` | 40 | committed plans | 6 |
| `lint (symvision)` | 32 | the rest | < 6 each |

Everything before the test stage adds up to about **259 s**. The test stage is about
**52 s** unless it escalates to the full lane. Stage order in `just check` is already
"lint before tests". What is missing is the ability to get past a lint failure that is
not the agent's.

### 3.3 Most failures are pre-existing, and the ledger can prove it

For each failed stage I parsed the failure items from the retained log and checked
whether the run's own diff (`fingerprint_before.repos[].dirty_paths`) touched the item's
file:

| Stage | All items in untouched files | Mixed | All touched |
| --- | --- | --- | --- |
| symvision (205 parsed) | **162 (79%)** | 28 | 15 |
| mypy (70 parsed) | 37 | 2 | 31 |
| test (scoped) (44 parsed; path is the test file) | 43 | 0 | 1 |

- The ledger holds 500 distinct items; 146 were seen by at least 3 different agents.
- The top symvision items (for example `_CombinedInstallOutcome` in
  `plugins_browser_install_previews.py`, `ExpandedLaunchSegments`, and
  `delete_paths_in_background`) were each hit by **23–28 agents**.
- The top pytest nodes were each hit by 17–22 agents. Examples:
  `test_every_bead_free_text_option_is_classified`,
  `test_committed_table_measured_count_has_not_drifted_too_far` (`sase-14r`), and the
  `test_usage_config` pair.
- Only 13 of 44 failing scoped-test runs had any node in
  `tests/reproducible_flake_baseline.txt`. The dominant recurring nodes are
  deterministic master-red failures, not flakes.

"Untouched" alone does not prove KNOWN: a source edit can break an untouched test. That
is why §4.3 requires a witness from *another* workspace, not just an untouched path.

### 3.4 A replay of the recommended KNOWN rule

I replayed the ledger chronologically, using only evidence recorded before each run.

- **KNOWN rule:** the same item was seen failing in a *different* workspace, whose diff
  did not touch the item's file, at a HEAD that is an ancestor of or equal to this run's
  HEAD, within 7 days. The label is withdrawn if a newer ancestor run completed that
  stage without the item.
- **NEW:** the item is in a touched file and has no witness.
- **UNKNOWN:** everything else.

| | Count |
| --- | --- |
| Item observations | 3,334: **KNOWN 2,395 (72%)**, NEW 232 (7%), UNKNOWN 707 (21%) |
| Failed runs with parsed items | 307: **all-KNOWN 143 (47%)**, some NEW 74 (24%), some UNKNOWN but no NEW 90 (29%) |
| KNOWN items that the run's own diff touched | 5 (0.2%). These are the first audit targets |

This replay is a feasibility estimate, not the acceptance backtest. It sees only the
first failing stage (masking), parses only symvision, mypy, and pytest, and approximates
the clearing rule. The real backtest is E3's DoD-5.

### 3.5 Receipts: the payoff E4 was waiting to measure is about zero

| Measure (all 518 `check` runs with complete fingerprints, every repo) | Value |
| --- | --- |
| First-seen fingerprints | 483 |
| Re-runs of a fingerprint that had already **passed** | **0** |
| Re-runs after failure only | 30 (all in the same workspace), 2.26 h |
| sase: repeat outcome on an identical fingerprint | 18 of 18 failed again (deterministic) |
| sase-core: repeat outcome on an identical fingerprint | **9 of 11 flipped to pass** (flaky; open `sase-15d`–`15h`, `17n`) |
| Runs with `mutated_input = true` (tree changed during the run) | 30 |
| `install` runs recorded | 1. `install` is unguarded, so agents run it raw. `_setup` already skips rebuilds when nothing is stale |
| Toolchain in `check` fingerprint | python, just, sase-core-rs only. **Not** ruff, mypy, symvision, or prettier (`sase-vr`: "lint verdicts depend on install date") |
| External state read by `check` | symvision `--epic-symbol` bead statuses (`SASE_SYMVISION_BEAD_STATUS_ONLY=1 BD_COMMAND=tools/sase_bead`) and flag-bead lint. Neither is in the fingerprint |

Researcher B wrote the caveat for this case: "37.2 h is the *addressable population*, not
a savings estimate." Now that fingerprints are recorded, the savings have been measured,
and they are zero. Repeats happen after edits, which is correct behavior, not waste.

### 3.6 Hand-offs and host completion

- **Verify monitors since the E1 landing:** 47 (29 failed, 16 completed, 2 timed out).
  The fastest failure took 87 s; none failed in the 4–7 s range that apollo showed.
- **Continuation prose (`--next`):** median 1,052 chars, max 2,282. Only 19 of 47 mention
  a baseline, pre-existing failure, or "unrelated". Reading them shows task-specific
  instructions ("if passed: close only sase-17z.1 …; if failed: re-run these four
  suites"), not the baseline essays the roadmap wanted to delete. **The roadmap's E3 exit
  metric ("median `--next` falls well below 1,778 chars") no longer measures anything
  E3 does.**
- **Prepared host completion since E1:** 6 monitors. 5 failed because `check` was red; 1
  completed but hit a recovery error ("requires active finalizer turn metadata"). There
  were **zero host commits**. `/sase_final`'s own source promotes it "so passing work
  lands with no further turn", but on a red master nothing passes. Meanwhile the normal
  `/sase_final` path has no verification gate at all: the host commits whatever the
  agent declares after the agent's own judgment that the failures were unrelated.

### 3.7 Identity defect (`sase-182`)

| Definition digest | Repo | Runs recorded as `project = gh_sase-org__sase` |
| --- | --- | --- |
| `18dc41c8ba…` | sase-core | 39 |
| `a2f2a5c5d2…` | sase-telegram | 5 |
| `c0a5d0cbc9…` | sase-github | 4 |
| `f53749ed24…` | sase-research-artifacts | 3 |

The fingerprint's `repos[0].identity` also says `gh_sase-org__sase`, while its `head` is
the linked repo's commit. TYPICAL is keyed by `definition_digest`, so today's CLI mostly
hides the problem. E3 and E4 must key on the repo that owns the resolved catalog.

---

## 4. E3, revised: "Failure triage: every failure labeled, no KNOWN failure hides the rest"

### 4.1 User-verifiable result

With master red exactly as it is on any given day:

- **An agent's `sase tool run check` runs every stage whose failures are all KNOWN or
  FLAKY.** In practice the scoped tests now run behind a master-red symvision stage.
- **The compact footer labels every failure item** NEW, KNOWN, FLAKY, or UNKNOWN, and
  names a suggested owning bead where one exists.
- **The footer ends with one verdict line**, for example
  `verdict: no NEW failures — 26 KNOWN (sase-150), 1 FLAKY; exit 1 because KNOWN failures remain`.
- **The exit code is unchanged.**
- **`sase tool failures` shows the machine's current red-master groups**, with how many
  agents hit each one and when it first appeared.

### 4.2 Changes from the roadmap's E3

| Roadmap E3 element | Verdict | Why (evidence) |
| --- | --- | --- |
| Demo on `check-full` | **Change → `check`** | `check-full` is explicit-only; 1 run in 4 days vs 488 `check` runs (§2, §3.1) |
| Rust signature normalization (workspace paths, unstable line numbers) | **Keep, widen** | Item-level signatures per extractor, not per stage (§4.4). Cargo target dirs and `/…/sase_<N>/` roots appear in real logs |
| Verification-vs-infra split | **Keep, simplify** | E2's `terminal_cause` already types stop, timeout, launch, owner loss. Add ENVIRONMENT for `_setup` failures |
| Classification against master/merge-base and the flake baseline | **Keep, specify** | The ledger itself is the baseline (§4.3). No new baseline runs, no CI dependency in v1 |
| `failures` | **Keep** | §4.6 |
| `rerun` attempt chains | **Drop from E3** | FLAKY evidence arrives passively (§3.5: 29 same-fingerprint repeats in 4 days). "Attempt N of run X" conflicts with E2's "a run id executes at most once" claim invariant. Reopen condition in §4.9 |
| Structured `--next` payload (the sase-zl adoption leg) | **Keep, demote** | Put the triage object into verify-monitor evidence via `tool_run_id`. Drop the prose-length exit metric (§3.6) |
| Suggested (never auto-created) `ci`/`flake` beads | **Keep, reframe** | Suggest an existing owner by locator-token match (it works but is noisy, §4.5). Tell agents not to `+1` an item E3 already linked, because the ledger counts it |
| — | **Add: continuation past KNOWN-only stage failures** | 79% of agents' final runs never executed tests (§3.1); `sase-180` |
| — | **Add: precision backtest as a landing gate** | A wrong KNOWN label tells an agent to ignore its own bug. It is the dangerous label |
| — | **Add: prerequisite `sase-182`** | §3.7 |

### 4.3 Classification contract (precise v1 rules)

**Definitions:**

- **Tool identity** `T` = (catalog repo identity, tool name), after `sase-182`.
- **Evidence runs** = settled ToolRuns of the same `T` with a complete
  `fingerprint_before`, within the lookback `L` (default 7 days).
- **Item** `i` has a signature `s(i)`, locator paths `P(i)` (repo-relative), and the
  stage it came from.

**Rules:**

- **touched(i, run)** is true when `P(i)` intersects the run's dirty paths in the catalog
  repo.
- **base(run)** is `fingerprint_before.repos[catalog repo].head`.
- **Witness** `W` for `s` relative to run `R`:
  - `W ≠ R`, and `W` is from a different workspace (or `W` ran on a clean tree);
  - `s ∈ items(W)`;
  - not touched(`s`, `W`);
  - base(`W`) is an ancestor of or equal to base(`R`);
  - `W` settled within `L`.
- **Clearing run** `C` relative to `R`:
  - base(`C`) lies on the ancestor chain between the newest witness's base and base(`R`);
  - `C` *completed* the stage (it ran, and either passed or failed with other items);
  - `s ∉ items(C)`, and not touched(`s`, `C`).

**Classes, evaluated in this order (first match wins):**

1. **INFRA** (run level): `terminal_cause ∈ {timeout, stop_requested, owner_lost, wrapper_lost, launch_failed, interrupt, signal}`.
   No item labels are produced.
2. **ENVIRONMENT** (run level): failure before the first stage, recognized by the
   environment extractor (missing binding, `uv` resolution, and so on). The output
   carries a remedy hint (`just install`, `sase update`).
3. **FLAKY**: either
   - the repo-declared flake baseline lists `s` (sase: `tests/reproducible_flake_baseline.txt`),
     or
   - two runs with the *same complete fingerprint digest* disagree: one has `s`, and the
     other completed the stage without `s`.
4. **KNOWN**: at least one witness exists, and no clearing run is newer than the newest
   witness.
5. **NEW**: no FLAKY or KNOWN evidence, and either
   - touched(`s`, `R`), or
   - a *pass witness* exists: a run at base(`R`) or a recent ancestor that completed the
     stage without `s` and without touching `P(s)`.
6. **UNKNOWN**: everything else. Agent guidance: **treat UNKNOWN as yours**.

**Verdict (run level):**

| Verdict | Condition |
| --- | --- |
| `pass` | exit 0 |
| `no_new_failures` | nonzero exit; every stage ran; every item is KNOWN or FLAKY; no stage failure lacks items (an unparseable failure becomes one generic UNKNOWN item) |
| `new_failures` | at least one NEW |
| `undetermined` | any UNKNOWN, any masked stage, INFRA, or ENVIRONMENT |

**Properties the implementation must hold:**

- **Deterministic and pure.** Rust computes the classification from (items, evidence
  rows, ancestry list, flake baseline entries). Python supplies only the ancestry list
  (bounded `git rev-list`), the flake-baseline entries, and bead candidates.
- **Evidence carried.** Every label carries its evidence refs: witness run ids, distinct
  agent and workspace counts, first-seen time, clearing run id, baseline file line.
- **Machine-local.** Evidence comes only from this machine's ledger. On thin ledgers
  (apollo, mac) UNKNOWN is the correct answer. Cross-machine evidence belongs to E8,
  or to the CI option in §4.8.

### 4.4 Signatures and extractors

Extractors are pure Rust functions over bounded stage output. The repo emits only bytes,
never a parsed structure. The registry is auto-detected by output shape, so v1 needs
**no catalog schema change** and no definition-digest churn. Minimum v1 set, each with
golden fixtures made from real, redacted athena logs:

| Extractor | Signature key | Locator paths |
| --- | --- | --- |
| symvision | category (`unused public` / `private imported` / `private unused` / `pragma` / `epic-symbol`) + symbol + path | path |
| mypy | path + error code + message with quoted names masked (no line number) | path |
| ruff / fmt (python, markdown) / keep-sorted | rule or check + path | path |
| pytest (`FAILED` / `ERROR` lines) | node id without parametrization | test file |
| toobig | path | path |
| cargo test (`---- name stdout ----`, `failures:` block) | crate::test path | none (UNKNOWN unless witnessed) |
| environment (`_setup` markers) | marker kind | none |
| generic fallback | stage description + hash of the normalized last ~40 lines | none |

Normalization strips:

- ANSI escapes, timestamps, durations, PIDs, and hex ids;
- workspace roots (`…/sase_<N>/`, `…/sase_<N>/sase/repos/linked/<repo>/`);
- cargo target dirs (`~/.cache/sase/tmp/cargo-targets/*`);
- `/tmp` paths;
- line and column numbers wherever the kind is not positional.

**Fixture requirement:** the same failure observed from two different workspaces must
produce the same digest.

**Known limitation to document:** symvision masks its own later internal stages when
stage 1 fails (`sase-180`). E3 cannot see through that. It is an upstream symvision
concern.

### 4.5 Continuation ("unmasking") semantics

This part lives mostly in repo tooling. It must be conservative, because it touches what
`just check` does.

- **Humans and CI are unaffected.** `tools/run_silent` stays byte-for-byte fail-fast
  unless `sase tool run` exports `SASE_TOOL_CONTINUE`.
- **Modes:**
  - `never`: today's behavior.
  - `always`: `-k/--keep-going`.
  - `known`: the default for agent-invoked runs of catalog tools with
    `stages: run_silent`, once the flag is removed. `-x/--fail-fast` forces `never`.
- **Decision in `known` mode.** On a stage failure, `run_silent` prints ✗ plus the
  captured output exactly as today. It then asks a hidden helper
  (`sase tool _triage-stage`, a hidden internal verb like `_adopt`) to extract, record,
  and classify that stage's items.
  - The helper answers `continue` only when every item is KNOWN or FLAKY.
  - The decision has a bounded timeout (≤ 10 s) and is **fail-safe to stop**.
  - The decision and its evidence are recorded as a stage event (`continued: true`, plus
    the reason).
- **Exit codes cannot be laundered.**
  - A final recipe line (`tools/run_silent --finish`) exits with the first continued
    failure's exit code.
  - As a safety net, if the child exits 0 while the ledger holds a continued stage
    failure and no finish event, `sase tool run` records the run `failed` and exits 1
    with a diagnostic.
  - This is the only deliberate exception to E1's "preserve the child's exit status", and
    it applies only to continuation that the wrapper itself enabled.
- **Cost, stated honestly.** Continuing *every* failed run would add about 125 s at the
  median per failed run, roughly 17 h over the window (+29% of `check` wall time).
  KNOWN-gated continuation spends that only on runs whose earlier failures are not the
  agent's (about 47% of failed runs by §3.4), and those are exactly the runs where agents
  now re-run masked stages by hand or land without tests. Record the extra seconds per
  run so the landing note can report the real number.

### 4.6 Surfaces

- **Compact footer of `sase tool run`** (the agent-facing surface):
  - one line per failed stage, with class counts and a `continued`/`stopped` marker;
  - up to N items per class, NEW and UNKNOWN first;
  - the suggested owner;
  - the verdict line.
  - The existing `-T` failure tail stays available.
- **`sase tool show RUN [-j]`** gains a versioned `triage` object with items, classes,
  evidence refs, verdict, and continuation decisions.
- **`sase tool failures`**:
  - lists signature groups for the current project over the last 7 days, sorted by
    agent count;
  - columns: CLASS, TOOL/STAGE, SIGNATURE (display text), RUNS, AGENTS, FIRST, LAST,
    OWNER;
  - `-a/--all`, `-c/--class`, `-j/--json`, `-n/--limit`, and `-t/--tool`, sorted and each
    with a short alias per `cli_rules`;
  - aggregation happens in Rust.
- **Verify-monitor evidence.** When a monitor owns a ToolRun (E2's `tool_run_id`), its
  result evidence includes the triage object. The follow-up prompt shows the verdict and
  lists NEW and UNKNOWN items first, so no baseline prose is needed.
- **Owner suggestion.** Match each item's locator token against open `ci`, `flake`, and
  `bug` task beads (node id, `symbol in path`, toobig path).
  - Show at most two candidates, labeled "possible owner".
  - Show closed matches only as "possibly fixed by `<id>` (closed `<age>`) — your HEAD
    may predate the fix".
  - Never create or `+1` a bead automatically. Matching is noisy (§3.3's top tokens also
    hit closed phases and plans), so it stays a suggestion.

### 4.7 Phases (7; one beta flag, `tool_failure_triage`)

Each phase that touches sase-core ratchets the sase pin inside that phase.

1. **`continuation-opt-in`** (sase; medium). `tools/run_silent` continuation protocol
   (`never`/`always`) with the `--finish` step and the executor's safety net, plus
   `-k/--keep-going`. `-k` is opt-in and complete by itself, so it needs no flag. Depends
   on `sase-182` being closed, or folds it in.
   - *Exit:* fixture recipe `[fail, pass, fail, pass]` under `-k` records all four
     stages and exits with the first failure's code; human/CI `just check` output is
     unchanged; a recipe missing `--finish` cannot exit 0.
2. **`core-failure-items`** (sase-core; medium-large). Item wire and store tables
   (additive, schema 1, new tables only), the extractor registry with normalization and
   golden fixtures, retention matching detail retention (60 d) under the existing
   `tool_run_retention` disk owner, bindings, and the pin ratchet.
   - *Exit:* every extractor in §4.4 has at least one real-log fixture; the two-workspace
     digest-equality fixture passes; an older core still opens the store.
3. **`core-classification`** (sase-core; large). Evidence query, the §4.3 rules as a pure
   function, verdict computation, and `failures` aggregation.
   - *Exit:* fixtures (a)–(h) in DoD-4 pass; the output is deterministic under row
     reordering.
4. **`record-and-render`** (sase; medium). Extraction at stage end (helper) and at settle
   (for `stages: none` and linked repos), the footer, `show`/`-j`, and owner suggestion.
   Behind the flag.
5. **`known-gated-continuation`** (sase; medium). `known` mode as the agent default,
   `-x/--fail-fast`, the bounded fail-safe decision, and the recorded decision events.
   Behind the flag.
6. **`failures-and-continuations`** (sase; medium). `sase tool failures`, plus triage in
   verify-monitor evidence and follow-up prompts. Monitor meta fields use E2's flat
   `monitor_*` convention (the agent-session rename `sase-17m` is in flight).
7. **`backtest-acceptance-adoption`** (sase; medium). `tools/tool_triage_backtest`, the
   audited sample, live acceptance on athena, flag removal, docs, and memory (§4.8
   DoD-10).

### 4.8 E3 landing criteria (all must hold; none may require a green `check`)

- **DoD-1 — Signatures.**
  - Every extractor in §4.4 has at least one golden fixture from a real athena log,
    redacted and with workspace paths normalized.
  - The same failure from two workspaces yields one digest.
  - Item display text is bounded (≤ 512 chars) and never contains an absolute checkout
    path.
- **DoD-2 — Continuation safety.**
  - Human and CI `just check` is fail-fast and byte-identical to pre-epic output
    (golden).
  - Under `-k`, a fixture with a failure in stage 1 of 4 records 4 stages and exits with
    stage 1's code.
  - A property test shows no combination of stage outcomes, missing `--finish`, or helper
    timeout yields exit 0 when any stage failed.
  - `-x` restores fail-fast.
- **DoD-3 — Gated continuation.**
  - In the agent default mode, a stage whose items are all KNOWN or FLAKY continues.
  - A stage with any NEW or UNKNOWN item stops.
  - A helper that times out (> 10 s, simulated) or crashes stops.
  - Each decision is visible in `show -j` with its evidence.
- **DoD-4 — Classification fixtures.** A fixture ledger yields exactly:
  - (a) item witnessed by another workspace at an ancestor HEAD → KNOWN, citing the
    witness;
  - (b) touched, no witness → NEW;
  - (c) listed in the flake baseline → FLAKY;
  - (d) fail→pass on an identical complete fingerprint → FLAKY;
  - (e) untouched with no evidence → UNKNOWN;
  - (f) witness cleared by a newer ancestor run that completed the stage → not KNOWN;
  - (g) timeout, stop, owner-lost, or launch-failed runs → INFRA, with no item labels;
  - (h) a `_setup` failure with a missing binding → ENVIRONMENT, with a remedy.

  The CLI footer, `show -j`, `failures -j`, and monitor evidence all agree on the ids and
  labels.
- **DoD-5 — Precision backtest (the gate).** `tools/tool_triage_backtest` replays the
  athena ledger chronologically using only prior evidence. The landing note publishes:
  - the label distribution;
  - a random sample of ≥ 50 KNOWN labels, hand-audited, with **≥ 95% judged
    pre-existing**;
  - **zero** KNOWN labels on items in files that the run's own diff *added*;
  - the list of KNOWN-but-touched items, each dispositioned.

  If precision misses 95%, widen UNKNOWN (for example, require two independent
  witnesses). Never relax the audit.
- **DoD-6 — Honest surfaces.**
  - `sase tool run`'s exit code equals the child's in every fixture, except for DoD-2's
    safety net.
  - The verdict line is one of the four verdicts, and `no_new_failures` is never printed
    when any stage was masked.
  - `show -j` and `failures -j` carry a schema version.
- **DoD-7 — `failures` on real data.** On athena, `sase tool failures` lists the current
  red-master groups with correct agent counts, cross-checked against a direct ledger
  query. A sase-core `check` failure never appears under sase's `check`, and the reverse
  also holds (this depends on `sase-182`).
- **DoD-8 — Continuations.**
  - A verify monitor started with `sase monitor start -p verify … -- sase tool run check`
    on a red-master tree delivers a follow-up prompt that contains the verdict and the
    NEW and UNKNOWN items.
  - The starter supplied no baseline prose.
  - This holds for both a monitor-owned run (E2 reservation) and an E1.5-wrapped raw
    `just check`.
- **DoD-9 — Governance.** Every memory change goes through `/sase_memory_write`:
  - the `tool_failure_triage` flag is removed, and its flag bead is closed;
  - `docs/tool.md` describes classes, rules, continuation, and verdicts;
  - `sase/memory/lint_and_test.md` explains what each class means for the agent: UNKNOWN
    is yours; do not call a failure "unrelated" without a KNOWN or FLAKY label or
    equivalent evidence; do not `+1` a bead for an item E3 already linked;
  - new glossary strands exist for Failure Signature and Triage Class, and the
    `glossary:tool-run` strand is touched only if needed;
  - `sase/memory/symvision.md` mentions that master-red symvision items are labeled
    KNOWN;
  - a decision record exists: *"Triage annotates; it never changes an exit code, and
    KNOWN requires an independent witness."*
- **DoD-10 — Post-landing measurement** (an owner check, not a gate). Over 7 days,
  report:
  - the share of failed `check` runs that reached `test (scoped)` (baseline 12%);
  - the share of agents whose final run executed tests (baseline 24%);
  - extra continuation wall time per day.

**Explicitly out of E3:**

- changing exit codes or landing policy (that is E4);
- automatic bead creation or `+1`;
- cross-machine or CI evidence;
- `rerun`;
- TUI (E5 owns the Failures view);
- catalog schema fields;
- fixing any master-red item.

### 4.9 E3 risks, reopen conditions, and decisions for the planner

- **False KNOWN** (the dangerous error).
  - *Mitigation:* the independence requirement, the clearing rule, the DoD-5 audit,
    UNKNOWN as the default, and evidence refs shown in the footer so an agent can check a
    label.
- **Masked evidence feeds itself.** Before E3, most runs never reached later stages, so
  early KNOWN evidence exists mostly for lint stages. Continuation fixes this over time.
  The backtest should be re-run 7 days after landing.
- **`rerun` reopens** if the ledger shows agents paying for more than about 2 h/week of
  manual re-runs of FLAKY-labeled items. It would then be designed as a *new run* linked
  by `rerun_of`, not as attempt N of a run, to preserve E2's at-most-once claim.
- **CI evidence reopens** if UNKNOWN stays above about 40% of items on apollo or mac
  (thin ledgers). Master Gate's per-SHA lint and shard results (via sase-github /
  `ci_watch`) could then become a second witness source.
- **Planner must settle:**
  1. the helper mechanism for `known` mode. I recommend the hidden-verb subprocess over a
     parent-decision-file protocol: it is simpler and fail-safe, and it runs only on
     failure;
  2. lookback `L` (7 d recommended) and ancestry depth (≤ 2,000 first-parent commits);
  3. whether pytest locators also include the modules imported by the failing test file
     (v1: no, the test file only);
  4. footer item caps.

---

## 5. E4, revised: "Verification receipts: fingerprint-bound proof that host completion can check"

### 5.1 Why not as written

Each of the roadmap's E4 user-verifiable results fails on today's evidence (§3.5–3.6):

| Roadmap E4 result | Evidence |
| --- | --- |
| "The second `sase tool run check` on an unchanged tree returns instantly citing a receipt" | 0 opportunities in 518 fingerprinted runs |
| "`just install` no-ops" | `install` is unguarded and 1 run was recorded. `_setup` already skips when nothing is stale |
| "A lint failure stops before the heavy stage" | Already true by stage order. The lint prefix (about 259 s) is the heavy part |
| Cheap-stages-inline-before-hand-off | No sub-87 s hand-off failure on athena |
| Unchanged-since-failure refusal | Wrong in 9 of 11 sase-core repeats (flakes). Correct in sase's 18, but that is worth about 1.4 h per 4 days, and it belongs in E3 as an advisory `REPEAT` annotation, never a refusal |

Reuse is also where `decisions:guarded-recipes` warned about hidden behavior changes: a
cached receipt could end an agent's turn unasked. Building it with no measured payoff
would be the corpus-before-mechanism error that `decisions:record-before-admit` was
written to prevent.

### 5.2 What survives, and why it matters now

The durable, fingerprint-bound *record that a tree was verified* is valuable. Its value
is **proof**, not skipping work. Three consumers need it:

1. **Prepared host completion** is designed to commit verified work without another
   turn, and has committed nothing since E1: 6 uses, 0 commits (§3.6). With a receipt
   whose verdict is `no_new_failures` (from E3), the host can commit the exact tree that
   was verified, and refuse when the tree changed after verification or any NEW or
   UNKNOWN item exists.
   - **This is a policy change you must approve (§7 Q2).** Today's normal `/sase_final`
     path already commits under a red master on the agent's unverified judgment, so a
     mechanical, evidence-carrying verdict is *stricter* than the status quo, not looser.
2. **Landers and scripts:** `sase tool receipt check` answers "has this exact tree passed
   (or passed modulo KNOWN)?" with exit 0 or 1 and a reason.
3. **Commit and bead audit trail:** host-owned commits and bead closes can carry the
   covering receipt (run id, verdict, KNOWN list). A human can then tell verified landings
   from asserted ones.

### 5.3 Receipt contract

- **Eligibility to mint (at settle, in the wrapper or hand-off worker).** Every
  condition must hold:
  - a named tool whose catalog opts in;
  - complete `fingerprint_before` and `fingerprint_after`, and they are equal
    (`mutated_input = false`);
  - `settled_by = wrapper` (never an owner-recovered or reconciled run, since those lack
    after-fingerprints);
  - not bypassed or forced;
  - not ad-hoc;
  - verdict ∈ the tool's accepted verdicts (`pass` always; `no_new_failures` only when the
    catalog lists it).
- **A receipt holds:**
  - tool identity (catalog repo identity + name + definition digest);
  - fingerprint digest;
  - verdict, plus the KNOWN and FLAKY signature refs;
  - run id;
  - minted and expiry times (TTL; recommended ≤ 2 h for `check`, because of the
    bead-state input below);
  - hermeticity notes.
- **Catalog policy fields must not move the definition digest.** Add a `receipt:` policy
  block, e.g. `{accept: [pass, no_new_failures], ttl: 2h, scope: tree}`, *excluded* from
  `ToolDefinitionIdentity`. Otherwise every policy edit resets TYPICAL and E6's corpus
  continuity. The same rule applies to `sase-17e`'s duration class and E7's demand
  (§6).
- **Hermeticity:**
  - add lint-tool version probes (ruff, mypy, symvision, prettier) to the `check` and
    `check-full` toolchain;
  - either add a bounded probe that digests the bead state the lints read (epic-symbol
    bead statuses and flag beads), or rely on the short TTL, and document which;
  - these input changes *do* move the definition digest. That is correct, happens once,
    and must be stated in the plan.
- **Lookup** (Rust): `receipt_lookup(identity, current fingerprint, accept)` returns
  either `covered(receipt)` or typed refusals:
  - `no_receipt`;
  - `fingerprint_changed` (with the changed paths);
  - `expired`;
  - `incomplete_fingerprint`;
  - `verdict_insufficient`;
  - `definition_changed`.
- **Shadow accounting:** every named run records `shadow_receipt_id`, i.e. whether a
  valid receipt would have covered it. **No run is ever skipped in E4.**

### 5.4 Phases (5; one beta flag, `tool_receipts`; starts after E3 lands, because it consumes E3's verdict)

1. **`hermetic-fingerprints`** (sase and linked catalogs; medium). Lint-tool version
   probes, the bead-state input or its TTL rationale, and documented non-hermetic inputs.
   Measure the probe overhead against E1's observation budgets (≤ 1 s per probe, ≤ 2 s
   total).
2. **`core-receipts`** (sase-core; large). Receipt wire and table (additive), the
   `receipt:` policy block excluded from the definition digest, minting rules, lookup
   with typed refusals, shadow fields, retention, and the pin ratchet.
3. **`receipt-cli-and-shadow`** (sase; medium). `sase tool receipt TOOL [-a/--accept {pass,no-new}] [-j]`,
   the shadow report (for example `sase tool receipt --report [-d DAYS]`, verb shape
   subject to `cli_rules`), and minting wired into both executor paths (foreground and
   hand-off worker).
4. **`verdict-gated-completion`** (sase; large). Prepared completion gains an `accept`
   policy (default `pass`, which is exactly today's semantics). At commit time the host
   re-fingerprints the checkout and commits only if a receipt covers it with an
   acceptable verdict; otherwise it falls back to the follow-up agent with the typed
   reason. The commit and bead-close notes carry the receipt id and KNOWN list.
5. **`acceptance-and-adoption`** (sase; medium). Live demos, flag removal, docs, the
   `lint_and_test.md` update, and skill-source updates to `sase_final.md` and
   `sase_monitor.md` (previewed with `sase skill init --diff` per `generated_skills`).
   Also a glossary strand "Receipt" and a decision record: *"Receipts prove before they
   skip; reuse waits for shadow evidence."*

### 5.5 E4 landing criteria

- **DoD-1 — Hermeticity.**
  - A fixture proves that changing the ruff (or mypy, or symvision) version, or closing
    an epic-symbol bead (or letting the TTL lapse), makes `receipt check` exit 1 with the
    matching reason.
  - A receipt never covers a run with `mutated_input = true`, an incomplete fingerprint,
    or `settled_by ≠ wrapper`.
- **DoD-2 — Eligibility.** An ad-hoc run, a bypassed run, and a failed run whose verdict
  is `new_failures` or `undetermined` never mint. `no_new_failures` mints only for tools
  whose policy accepts it.
- **DoD-3 — Query.**
  - On a tree just verified, `sase tool receipt check` exits 0 and prints the receipt,
    run, verdict, and age.
  - After touching any tracked file, it exits 1 with `fingerprint_changed: <path>`.
  - `-j` is versioned. Exit codes are 0 covered, 1 not covered, 2 usage.
- **DoD-4 — Completion gating** (fixtures and one live athena demonstration).
  - A prepared completion with `accept no-new` and a verification run whose verdict is
    `no_new_failures` commits exactly the verified tree.
  - It does not commit when:
    - (a) any NEW or UNKNOWN item exists;
    - (b) the tree changed after verification;
    - (c) the receipt expired.
  - Each refusal hands off to the follow-up agent with the typed reason.
  - The default (`pass`) behavior is byte-identical to today.
- **DoD-5 — Shadow.** Every named run records shadow coverage. The report prints covered
  runs, hours, and the top covered tools over N days. Nothing is skipped.
- **DoD-6 — Governance.** Flag removed; docs, memory, skill sources, glossary, and the
  decision record per phase 5.
- **DoD-7 — Post-landing measurement** (an owner check). After 14 days, publish:
  - the shadow report;
  - the count of prepared-completion commits (baseline 0 since E1);
  - any completion refused for `fingerprint_changed` (a real integrity catch).

**Explicitly out of E4:**

- skipping execution or reuse (the `-R` force flag and the "returns instantly"
  behavior);
- `install` skip;
- cheap-stages-before-hand-off;
- refusal on unchanged-since-failure;
- cross-machine receipts;
- redirecting raw `just check` to a receipt.

**E4b (reuse) reopens** when the shadow report, or the equivalent offline ledger query in
the appendix, shows **≥ 2 h/week** of covered repeats for one tool on one machine for two
consecutive weeks. Reuse then ships as opt-in per tool, never as a silent change to raw
recipes, per `decisions:guarded-recipes`.

### 5.6 The alternative: defer E4

If you do not want host completion to accept `no_new_failures` (§7 Q2), the remaining E4
value (a `receipt` query, audit trailers, shadow accounting) is small enough to wait.
Nothing in E5–E8 depends on receipts. What you give up is the only route I found to
making prepared completion usable while master is red.

---

## 6. Cross-epic rules these epics must follow

1. **Wire discipline (E2 precedent).** Additive only, `schema_version` stays 1, new
   tables and nullable columns only, and no new values in existing enums. Older cores in
   sibling venvs share `runs.sqlite` and reject unknown enum strings.
2. **Pin ratchet in-epic.** Every phase that adds a binding sase calls also moves
   `sase-core-revision.txt` in the same phase. `sase-17p` shipped with the pin behind its
   own bindings, and `validate_sase_core_rs` refused pinned builds (`sase-17p` note #1).
3. **Policy fields do not move the definition digest.** `ToolDefinitionIdentity`
   currently hashes name, argv, stages, inputs, env, args, and the fingerprint spec.
   E4's `receipt:`, `sase-17e`'s duration class, and E7's demand must be excluded.
   Otherwise each epic resets TYPICAL and the corpus E6 calibrates on. Changes to
   execution identity (inputs, toolchain probes) *should* move it.
4. **Continuation changes whole-run durations.** E6 must forecast from stage-level
   durations or condition on the recorded `continued` flag. Stage timings themselves are
   unaffected.
5. **Tool identity is the catalog's repo** (`sase-182`) everywhere evidence is keyed:
   triage, receipts, forecasts, admission.
6. **Honesty invariants** from the roadmap stand: exit codes are the child's (except
   E3's anti-laundering net), nothing unknown is presented as known, and nothing is
   auto-created.
7. **Vocabulary.** New monitor and session fields follow E2's flat `monitor_*`
   convention and the `sase-17m` agent-session rename. New glossary strands go through
   `/sase_memory_write`.
8. **Green-master independence.** No DoD requires a green `check`. E3 exists because
   `check` is not green.

**Interactions:**

- **`sase-180`** (toobig splits redden symvision) is complementary. E3 contains the
  damage; `sase-180` removes a cause.
- **`sase-j0`, `sase-th`, `sase-10w`** (red CI lanes) are fixtures, not blockers.
- **`sase-17e`** (duration classes) and **`sase-17g`** (detach/join) are orthogonal
  except for rule 3.
- **`sase-146`** (adoption report to Rust) is independent.
- **E5** should follow E3 so its Failures view renders E3's contract rather than
  inventing one.

---

## 7. Open questions for Bryan

1. **Continuation default.** KNOWN-gated automatic continuation for agent runs
   (recommended), always-on for agents (+29% `check` wall time, simplest), or opt-in
   `-k` only (cheapest, but agents will not adopt it: see opt-in adoption history)?
2. **Should host completion ever commit on `no_new_failures`?** This is the pivot of the
   re-scoped E4. I recommend yes, per intent and opt-in, because the status quo already
   commits on unaudited agent judgment. If no, defer E4 (§5.6).
3. **E3 decision record.** Should "Triage annotates; KNOWN requires an independent
   witness" become a `decisions:` strand now (recommended, to stop re-litigation), or
   only at E3 landing?
4. **Owner linking.** Suggest-only with "possible owner" wording (recommended), or no
   bead linking in v1?
5. **Roadmap edit.** Should the consolidated roadmap's E3 and E4 rows be amended to
   match §4.1 and §5 (target `check`; add continuation; E4 = proof + shadow; E4 after
   E3), with the reuse leg recorded as conditional E4b?

---

## Appendix — method, commands, caveats

- **Ledger.** `sase tool runs -a -j -n 1000` (paged) → 638 rows; `sase tool show RUN -j`
  for every run (stages, samples, `unattributed_ms`); retained logs under
  `~/.sase/tools/logs/<run>/stdout.log`. The sase `check` subset is definition digest
  `12b1748a5c…` (488 runs, 2026-09-20 09:35 → 2026-09-24 14:25); 17 earlier runs use an
  older sase digest (`4d339b942b…`). Repo attribution of the other digests is by
  fingerprint input patterns (§3.7).
- **Stage and item parsing.** Failed stage = first stage with a nonzero `exit_code`. The
  item text is the segment of the retained stdout after `✗ <stage>` (run_silent dumps
  the captured output there). Symvision items match `^\s+NAME in PATH$` under category
  headers. mypy items match `path:line: error: msg [code]` with quoted names masked.
  pytest items match `FAILED|ERROR node`.
  - *Caveats:* 18 fmt(python), 12 feature-flags, 15 pyscripts, and a few other failures
    were not parsed (generic in E3). Masking means only first-failing-stage items are
    observable.
- **Touched.** Item path ∈ `fingerprint_before.repos[0].dirty_paths[].path` (working
  tree + index vs HEAD).
  - *Caveat:* commits made during a turn but before the run are not "dirty". Agents
    rarely commit (host-owned completion), so the error is small.
- **Backtest (§3.4).** Chronological. Witness = earlier run, different
  `workspace`/agent, untouched item, witness HEAD an ancestor of or equal to the current
  HEAD (first-parent `origin/master` index, falling back to
  `git merge-base --is-ancestor`), within 7 days, and not cleared by a newer ancestor run
  that completed the stage without the item. This is an approximation of §4.3 for
  feasibility only.
- **Repeats (§3.5).** Key = SHA-256 of the fingerprint's identity fields
  (`project_identity`, `definition_digest`, `extra_args_digest`, `repos`, `inputs`,
  `env`, `toolchain`), which mirrors `fingerprint_digest()` in sase-core
  `tool_run/fingerprint.rs`. Only `completeness.complete` fingerprints count. The same
  query is the offline E4b trigger.
- **Continuation cost (§4.5).** Sum of passing-stage medians after each failed run's
  first failing stage. This is an upper-bound estimate for always-continue.
- **Monitors.** `sase monitor list -a -j` → 1,376 rows; the window starts at the E1
  landing (2026-09-20 16:25). Verify profile: 47. Prepared completion = non-null
  `host_completion_status` or `completion_ref`: 6.
- **Code read.**
  - sase: `src/sase/config/tools.py`, `src/sase/tool/*`, `tools/run_silent`,
    `tools/_run_silent_record.py`, `Justfile` (`check`, `check-full`, `_setup`),
    `src/sase/finalizers/prepare.py`, `src/sase/monitor/profiles.py`,
    `tests/_test_selection_health_*.py`, `tests/reproducible_flake_baseline.txt`,
    `src/sase/xprompts/skills/sase_final.md`.
  - sase-core (pin `6d0d0e6d5c`): `crates/sase_core/src/tool_run/{wire,catalog,fingerprint}.rs`
    and `store/query.rs` (TYPICAL keyed by `definition_digest`).
- **Artifacts and beads consulted.**
  - `research:202609/sase_tool_epic_roadmap/{sase_tool_epic_roadmap,__a,__b}.md`
  - `research:202609/sase_tool_guarded_recipes_and_monitor_wrapping/sase_tool_guarded_recipes_and_monitor_wrapping.md`
  - `plan:202609/tool_e1_named_tools.md`, `plan:202609/tool_e2_durable_handoff.md`,
    `plan:202609/symvision_green_master.md`
  - beads `sase-135`, `sase-16h`, `sase-17p`, `sase-180`, `sase-vr`, `sase-17e`,
    `sase-146`, `sase-o7`
  - `decisions:{record-before-admit,guarded-recipes,check-full-is-explicit,ci-two-speed-split}`
- **Not measured.** apollo's and mac's ledgers. This report is athena-only. Athena is the
  busiest agent host, but E3's UNKNOWN rate and E4's shadow numbers should be re-checked
  on apollo before E4 is planned (the same two queries apply).
- **Filed during this research:** `sase-182` (bug, medium, ready). Linked-repo ToolRuns
  are recorded under the host project's identity. Related link to `sase-16h`.
