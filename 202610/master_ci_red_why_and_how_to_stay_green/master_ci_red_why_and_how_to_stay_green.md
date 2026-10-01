# Why sase `master` is red, and how to keep it green

**Consolidated report** · 2026-10-01 · lead researcher plus five independent reports
([cdx](master_ci_red_why_and_how_to_stay_green__cdx.md),
[cld](master_ci_red_why_and_how_to_stay_green__cld.md),
[grk](master_ci_red_why_and_how_to_stay_green__grk.md),
[mus](master_ci_red_why_and_how_to_stay_green__mus.md),
[gem](master_ci_red_why_and_how_to_stay_green__gem.md))

> **Bottom line.** `master` has been red for 13 days and about 1,110 commits. No single
> bug causes it, and neither does a CI or runner problem. Thirteen small, deterministic
> breaks are live right now, introduced by 8 feature commits over the last 40 hours, and
> each one is a 5–30 minute fix. They pile up because **nothing on the landing path
> refuses a red change**. CI only reports after the push. The local `check` passes 2.6% of
> the time, so a red result carries no information. Repairs land without a freeze, so
> newer breaks overtake them. Fix the 13 breaks in one stop-the-line pass. Then make
> "green before it lands, and fix-or-revert when it is red" a mechanical rule, not
> etiquette.

---

## At a glance

| Signal                       | Value                                                                                                                                                                   |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Last green Master Gate       | [`f90c6b549f`](https://github.com/sase-org/sase/actions/runs/35299164480), 2026-09-18 02:24Z                                                                            |
| Commits since                | **≈1,110** first-parent commits, about **90 per day**                                                                                                                   |
| Recent gate history          | **198 of 198** runs failed (09-29 → 10-01). Since 09-01, 60 of 1,907 runs were green (3.1%)                                                                             |
| Latest completed gate        | [`90be0cff56`](https://github.com/sase-org/sase/actions/runs/36878015041): core-wheel ✅, **lint ❌**, shard 1 ✅, **shards 2–8 ❌**                                      |
| Full CI (scheduled, 2-hourly) | Also red: lint, the 3.12/3.13/3.14 test legs, visual, and perf-floors                                                                                                  |
| Branch protection            | None (`GET …/branches/master/protection` returns 404, and there are no rulesets)                                                                                        |
| Local `just check` (athena)  | **26 passes in the last 1,000 runs**. 762 failed, 199 were killed by signal, 12 were lost                                                                               |
| Open CI debt                 | **68 `ci` beads and 89 `flake` beads sit untriaged** in `ready`                                                                                                         |
| Cost so far                  | PyPI still serves **0.17.1** (2026-08-29). Release PR #299 (0.18.0) has been open since 08-30, because `ci_watch` will not release while the gate is red |

---

## 1. What is red right now

Every item below reproduces at the latest completed gate (`90be0cff56`) and fails the same
way on consecutive SHAs. Rerunning CI will not help.

| #   | Failure                                                                                       | Introduced by                     | Fix                                                                                                                            | Bead          |
| --- | --------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------- |
| 1   | **Lint:** symvision reports `HandoffSubmitResult`, `StarterResolution`, `owner_ref` as unused publics | `018061f6f2` (sase-1cx.3), 09-30  | Make them private or delete them. They have no production caller                                                              | sase-1dn      |
| 2   | **ImportError** collecting `test_agent_header_panel.py`. It cascades into `test_contract_manifest` (`--collect-only` exits 2) | `c6b802a647`, 09-30               | Facade: replace `test_hint_document_forces_expansion` with `test_hint_mode_keeps_collapsed_header_unchanged` and `test_hint_mode_numbers_expanded_header_first` | sase-1dh      |
| 3   | `test_partial_launch_cleanup` and `test_force_reuse_launch_seam_rejection` ×2 (`history_text`) | `ce0f61846c`, 09-30               | Launch fakes accept `**kwargs`. This bead was already reopened once (for `origin=`), so another one-kwarg patch would just break again | sase-1cm      |
| 4   | `test_kind_coverage` (`memory/history:at` has no caption) and `test_parser_command_help` (memory subcommand list) | `ebf070e16a` (sase-1dr.5), 10-01  | Add a value hint for `--at`, add `history` to the expected list, then `just sync-completion-spec`                              | (1dr leftover) |
| 5   | `test_memory_log_json_id_outputs_raw_event` (`blob_oid`, `included_blob_oids`) and runner started-at `4 == 3` | `297faf1d38` (sase-1dr.1), 10-01  | Confirm the new event shape and the 4th index write are intended, then update the pins                                         | (1dr leftover) |
| 6   | Artifact-directory audit: `bead/attachments/lifecycle.py:quarantine_local_object` was never reviewed | `ee1620e1b9`, 09-30               | Review it and add it to the reviewed set                                                                                        | sase-1de      |
| 7   | Config schema: the sidecar description lost the literal `…/repos/agents` path                 | `e300173faf`, 09-29               | Restore the path or pin the `<role>` wording, whichever is the intended contract                                               | sase-1de      |
| 8   | `test_show_images`: `'-i, --images' in help`                                                  | `56d5cd277e`, 09-29               | Assert `-i` and `--images` separately (see §2.4)                                                                               | none          |

Together these are 13 failing nodes (1 lint gate, 1 collection error, 11 tests), about
1–2 hours of work for one agent. Most were filed as beads 18 hours to 2 days ago and have
since collected 2–4 `+1`s each, but nobody has fixed them.

**Probably load- or timing-sensitive, not deterministic.** These come and go between
adjacent SHAs:

- `test_tui_app_import_stays_under_startup_budget` (`3486 < 3485`)
- `test_midword_peek_reveals_then_finishes_word` and `test_beads_sync_reports_visible_and_missing`, both seen only on `781063e38e`

Full CI adds TUI wait timeouts, visual-golden failures, and a Python 3.14 import-budget
overrun. Reproduce these under the contention harness before changing goldens, and never
bless goldens from a run that also had collection errors.

---

## 2. Why it keeps happening

Feature commits break pins all the time, and that is normal. The defect is that the
system has **no point where a red change is refused, and no one who owns a red
`master`**:

```text
  agent's check is red ──► "inherited, not mine" ──► lands anyway (no refusal)
        ▲     (97% of the time)                               │
        │                                                     ▼
  master stays red ◄── repair lands, gets overtaken ◄── Master Gate says red
                       (no freeze, no owner)              12.7 min later (post-push)
```

### 2.1 Nothing stands between an agent and `master`

- **Master Gate runs on `push` to `master`.** Its verdict arrives after the commit is
  already canonical, so today it is post-land telemetry, not a gate.
- **The finalizer does not require proof.** Ordinary `sase final submit` records
  `verdict_provenance: "unverified"` instead of refusing
  (`src/sase/finalizers/declaration.py:_verdict_provenance`). Where a receipt is used, the
  `check` policy accepts `[pass, no_new_failures]`, so known failures are allowed by
  design.
- **Cadence beats the verdict.** Gate wall time is 12.7 min at p50 and 31.5 min at p90.
  The median gap between pushes is 14.7 min, and **42% of pushes land before the previous
  commit's gate would have finished.**

### 2.2 The local signal is dead

On a red base, every `check` fails. "My part looks fine" therefore becomes the de facto
landing rule. cld traced the culprit agents' own records:

- `c6b802a647` and `ce0f61846c`: `check` was killed at about 538 s, with no verdict.
- `ee1620e1b9`: `check` stopped at an inherited lint failure, so its tests never ran.
- `018061f6f2`: five `check` runs, all failed.
- All of them landed.

Triage cannot rescue this. One inherited `test_kind_coverage` failure reached 39 agents,
and its newest triage label was NEW, so each of those agents was told the failure was its
own.

### 2.3 Test selection is mostly *not* the gap, with one real blind spot

cdx, grk, mus, and gem blamed diff-scoped selection; cld disagreed. **I replayed
`tools/select_tests --base <culprit>^` in clean worktrees at all 8 culprits, plus
`92c6337de8`. All 9 escalated to the full suite.** Six escalated on deterministic
change-set rules (`src-data-asset`, `justfile`, `packaging-config`). The broken tests were
in scope; the red results were ignored, killed, or lost among inherited failures.

There is one structural miss. With escalation disabled, the 708-file selection for
`c6b802a647` included `test_agent_header_panel_basic.py` but **not the facade that imports
it**, and not `test_contract_manifest`. Edges where one test file imports another are not
followed. The `contract-set-always` rule that the other reports propose to add already
exists and already fired.

### 2.4 Local ≠ CI

| Skew       | Local agent                                                  | Master Gate                         | Impact                                                                                                                         |
| ---------- | ------------------------------------------------------------ | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Python     | 3.14.7 (no `.python-version`; `requires-python >=3.12`)      | 3.12                                | **Verified:** 3.12 renders `-i {…}, --images {…}`, while 3.13 and 3.14 render `-i, --images {…}`. Failure #8 is invisible locally |
| Rust core  | `_setup` builds from the linked sase-core checkout           | `sase-core-revision.txt` pin        | Different binaries, plus slow, fragile setup (49 `_setup` failures in 7 days, per cld)                                         |
| Lint input | `_lint-flags` and `_lint-symvision` read live bead status    | Sidecars bootstrapped at CI time    | Lint can flip with no code change (a hazard read in code, not yet observed)                                                    |

### 2.5 Failures hide other failures

- The Master Gate `lint` job is fail-fast. A red `just lint` **skips** `validate`,
  `validate-committed-plans`, and `build-check`, with no `if: always()`.
- Symvision reports one error class at a time. `018061f6f2`'s three symbols hid behind
  a private-import error, so "first red run" attribution blamed the commit that fixed it.

### 2.6 Repairs without a freeze are a treadmill

cld found the treadmill in the run history:

- **The 09-29 repair:** `8c38eb6a9a` took the suite from 61 failing tests to 4. It landed
  red itself, and the count was back to 10 within 21 minutes.
- **Earlier repairs** ended the same way: 09-23, 09-24, and 09-28.
- **The 09-28 report's stop-the-line window** was never armed.

The same pattern shows in the open beads:

- **Repair epic stuck:** epic sase-1c1 (*Green master CI and ship 0.18.0*) and its observe
  phase sase-1c1.13 have been in progress for 3 days while product epics (sase-1dq,
  sase-1dr, toobig splits) keep landing.
- **Combined-tree check unbuilt:** sase-1cb (check the rebased combined tree before
  pushing) is still open.
- **Watcher only watches:** `ci_watch` notifies, but by contract it never repairs.

**A freeze is harder than it looks.** Per `decisions:hold-pull-fail-open`, a hold gates
only the *admission* of new runs. Agents already running still push when they finish. A
real freeze must therefore be enforced at landing, or the in-flight agents must be
allowed to drain first.

---

## 3. Where the reports disagreed

| Question                                     | Positions                                                                                    | Verdict                                                                                                                                                                                                                                                                                                       |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Did scoped selection miss the broken tests?  | Yes: cdx, grk, mus, gem. No: cld                                                              | **Mostly no** (9 of 9 culprits escalated, §2.3). Fix the test-to-test import edge. Do not build a new "contract pack"                                                                                                                                                                                         |
| GitHub branch protection or merge queue?     | Yes: cdx, gem, mus. No, it was rejected in `decisions:ci-two-speed-split`: cld                | **Not first.** A serial queue would need about 90 × 12.7 min ≈ 19 gate-hours a day, which saturates. Gate locally with receipts and use fix-or-revert. The decision's reopen trigger (gate p50 vs cadence) is now borderline (42%), so revisit it with batching if the local gate fails                          |
| Symvision culprit                            | `018061f6f2`: cld, grk, mus. `7d2c8e0caa` / `7884ffe854`: gem                                 | `018061f6f2` (`git log -S` for all three symbols)                                                                                                                                                                                                                                                            |
| Facade replacement names                     | `test_hint_mode_*`: cld, grk. `…_leaves_header_collapsed`: gem                                | `test_hint_mode_keeps_collapsed_header_unchanged` and `test_hint_mode_numbers_expanded_header_first`                                                                                                                                                                                                          |
| `--at` culprit                               | `ebf070e16a`: cld. `92c6337de8`: mus                                                          | `ebf070e16a` is the only commit that adds `"--at"` under `src/sase/main`                                                                                                                                                                                                                                      |
| Python fix direction                         | Pin local to 3.12: cld, gem. Or move the gate to 3.14: cld                                    | **Pin local to 3.12.** The gate should test the minimum supported version, and Full CI already covers 3.13 and 3.14                                                                                                                                                                                          |

---

## 4. Fix it now: one stop-the-line pass (about half a day)

1. **Freeze.** Arm a hold on non-repair launches and let in-flight landers drain (§2.6).
   Pause the sase-1dr, sase-1dq, and toobig work.
2. **One build-cop agent, explicitly authorized to run `just check-full`.** This is the
   CI-repair case `decisions:check-full-is-explicit` allows. It lands all 8 fixes from §1
   as one reviewed commit and closes sase-1dn, sase-1dh, sase-1cm, and sase-1de.
3. **Verify on CI, not only locally.** Local 3.14 cannot see #8. Run `gh workflow run`
   for Master Gate and Full CI on the fix SHA.
4. **Quarantine instead of leaving things red.** Anything not fixable today gets
   `xfail(strict=True, reason="sase-…")` through a reviewed list with an expiry. Timing
   failures are reproduced under contention, never blessed.
5. **Lift the freeze only on a green HEAD gate.** Then cut a sase-core release carrying
   the bindings master needs. cld found the published `sase-core-rs` 0.36.1 is missing 16
   of 784. After that, refresh PR #299.

---

## 5. Keep it green: ranked by leverage

**A. Refuse unverified landings.** This is a policy flip; the receipts machinery already
exists.

- **The rule:** for a push to `master`, the commit finalizer requires a covering `check`
  receipt on the committed tree. The verdict must be `pass`, or `no_new_failures` only
  where every KNOWN item is on the reviewed quarantine list.
- **The red-HEAD rule:** while the latest Master Gate on `origin/master` is red, refuse
  every landing not tagged as CI repair. That alone would have stopped the 1,100-commit
  pile-up after the first break.
- **Why it waits for green:** it only works on a green baseline. That is when "any failure
  is yours" becomes true again.

**B. Fix or revert on red.** When SHA X is red and its parent was green, `ci_watch` (which
already polls) arms the landing hold and launches one fix agent with X's diff and failing
jobs. If HEAD is still red after 60 minutes, it reverts X. This also catches semantic
conflicts from rebasing, which A cannot see, until sase-1cb ships.

**C. Parity.**

- Commit `.python-version` = `3.12` and have `just install` honor it.
- Build the local core from the pin, or fail fast when the linked checkout differs.
- Make bead-status lint read a committed snapshot.

**D. Unmask.**

- Give Master Gate's `validate`, plans, and `build-check` steps `if: always()`.
- Have symvision report every error class in one pass.
- Let `just check` continue to tests after an inherited lint failure, without changing
  the exit code (`decisions:triage-annotates-does-not-change-exit-codes`).
- Add test-to-test import edges to the selector, plus a cheap `pytest --collect-only`
  stage.

**E. Ownership and visibility.**

- Triage each `ci` bead within 24 hours: fix it, or quarantine it with an expiry.
- Show **"hours since last green"** and **"commits ahead of last green"** in ACE. The
  second number should never exceed 1.
- Send one notification per new failure signature, not one per SHA.

A and B change `decisions:host-owned-completion` and `ci_watch`'s notify-only contract.
Record a new decision ("`master` landings require green"), and ship both behind a feature
flag per `sase_flags.md`.

---

## Recommended solution

**Today:** freeze, let in-flight agents drain, and have one authorized build-cop land the 8
fixes in §1 as a single commit. Lift the freeze only when Master Gate is green on HEAD and
Full CI is green on the same tree.

**This week:** adopt a **green-or-revert landing contract**:

- **(A)** The commit finalizer refuses a `master` push without a covering `pass` receipt,
  and refuses every non-repair landing while HEAD is red.
- **(B)** A red per-SHA gate triggers fix-or-revert within 60 minutes.
- **(C)** Pin local Python to CI's 3.12.

**Next:** unmask the lint, symvision, and collection failures (D), and give CI debt an
owner and a clock (E).

Do not add a GitHub merge queue yet. At about 90 commits a day it would saturate. The
local gate plus revert gets the same guarantee without a serial bottleneck. Reopen
`decisions:ci-two-speed-split` only if A and B fail to hold the line.

---

### Method and confidence

**Lead verification (high confidence):**

- Gate inventory from `gh run view --log-failed` on `90be0cff56`.
- 198-run duration and cadence statistics.
- `tools/select_tests` replays at 9 culprits in clean worktrees, including the facade
  blind spot.
- An argparse render on Python 3.12, 3.13, and 3.14.
- The ToolRun ledger: 1,000 `check` runs.
- Bead counts and statuses.
- `git log -S` culprit checks.
- The finalizer and `sase.yml` receipt policy.
- The `master-gate.yml` step layout.
- The PyPI version and PR #299.

**From individual reports (medium to high confidence):**

- cld: culprit agents' per-run `check` records, 77-sample failure-lifetime series,
  repair-treadmill timings, missing core bindings.
- cdx: the first red run (`5cb968c8cb`, visual extra).
- grk: the sase-1cb rebase mechanism.
