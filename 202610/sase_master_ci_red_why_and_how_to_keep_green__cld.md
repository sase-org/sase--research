# Why sase master is red, and how to keep it green

**Researcher:** cld · **Snapshot:** 2026-10-01 ~14:40Z · **HEAD:** `781063e38e` (gate run
in progress); last completed run `36872281569` on `429d6577de`

---

## TL;DR

- **Master Gate has not been green since 2026-09-18 02:24Z** (`f90c6b549f`). That is
  ≈1,100 consecutive red runs. Since 2026-09-01 it has been green 60 times in 1,907
  runs (3.1%).
- **Right now the gate fails on 15 items: 3 symvision symbols, 11 tests, and 1
  collection error.** All 15 trace to **8 feature commits from the last ~40 hours**. Each
  fix is small.
- **The root cause is the system, not the individual commits.** About 90 commits a day
  land by direct push onto an unprotected branch, and landing records `unverified`
  instead of refusing. Meanwhile local `just check` passed only **26 times in its last
  1,000 runs**, so a red check carries no information. The authors of these breaks ran
  checks that came back red or got killed, and they landed anyway.
- **Repairs without a freeze are a treadmill.** The 2026-09-29 repair took master from
  61 failing tests to 4. It landed red itself, and the count was back to 9 within 18
  minutes. Four repair commits since 09-23 have ended the same way.
- **Recommendation:** stop the line once to reach zero. Then adopt a **green-or-revert
  landing contract**:
  1. The commit finalizer refuses `unverified` landings.
  2. A red per-SHA gate triggers fix-or-revert within an hour.
  3. Local verification runs the same Python and core as CI.

  Details in §5.

---

## 1. What is failing at HEAD, and who broke it

I found culprits by binary-searching Master Gate logs for each item's first failing run.
The search covered runs after the 09-29 repair, because several tests were fixed there
and then broke again. I then confirmed each culprit's diff explains the failure.

| # | Failure | Introduced by | Why | Fix (size) | Bead |
| --- | --- | --- | --- | --- | --- |
| 1 | **symvision:** `HandoffSubmitResult`, `StarterResolution`, `owner_ref` unused public | `018061f6f2` 09-30 15:42Z (sase-1cx.3) | New tool seams with no non-test consumer. Masked for ~6h behind another symvision error, then resurfaced on `60b2d3dfdb`, a commit that was *fixing* symvision (§3.5) | Privatize or delete (XS) | sase-1dn |
| 2 | **ImportError** collecting `test_agent_header_panel.py`. Cascades into `test_contract_manifest` (`pytest -m contract --collect-only` exits 2) | `c6b802a647` 09-30 18:34Z | Renamed `test_hint_document_forces_expansion` in `_basic.py`. The facade still re-exports the old name | Update the facade import and its name list (XS) | sase-1dh |
| 3 | `test_partial_launch_cleanup::…rolls_back_partial_multi_prompt_launch`, `test_force_reuse_launch_seam_rejection` ×2 | `ce0f61846c` 09-30 14:05Z | Launch callers now pass `history_text=None`. Fakes and `assert_called_with` still expect the old signature | Accept or expect `history_text` (XS) | sase-1cm |
| 4 | `test_kind_coverage` (`memory/history:at` uncaptioned), `test_parser_command_help` (memory subcommand list) | `ebf070e16a` 10-01 06:52Z (sase-1dr.5, apollo) | New `sase memory history` subcommand | Add a ValueKind or hint for `--at`, update the expected list, run `just sync-completion-spec` (S) | — |
| 5 | `test_memory_log_json_id_outputs_raw_event`, `test_axe_run_agent_runner_started_at` (`4 == 3`) | `297faf1d38` 10-01 02:44Z (sase-1dr.1, apollo) | Memory read events gained `blob_oid`/`included_blob_oids`, plus one extra artifact-index write | Confirm the change is intended, then update the expectations (S) | — |
| 6 | `test_agent_artifact_directory_operation_audit` | `ee1620e1b9` 09-30 02:10Z | Unreviewed site `bead/attachments/lifecycle.py:quarantine_local_object` | Review it and add it to the reviewed set (XS) | sase-1de |
| 7 | `test_config_schema_repositories::…intrinsic_agents_sidecar_contract` | `e300173faf` 09-29 22:13Z | The rewritten schema description dropped `~/.sase/projects/<project_key>/repos/agents` | Restore the wording (XS) | sase-1de |
| 8 | `test_show_images::test_parser_help_covers_images_and_open` | `56d5cd277e` 09-29 22:17Z | Asserts the **Python ≥3.13** argparse format `-i, --images`. Master Gate runs **3.12**, which prints `-i {…}, --images {…}`. **Passes locally on 3.14** | Assert the two flags separately (XS) | — |

All of this is about 1–2 hours of work for one agent. The beads in the last column were
filed between 18 hours and more than a day ago, and other agents have since `+1`'d them
2–4 times (§3.7).

---

## 2. Shape of the problem: a rotating set of breaks, not one big break

Median failing tests per Master Gate run, from 77 log samples taken since 09-17:

```text
09-18  ██▌                  6        09-25  ███▌                 9
09-19  ██▊                  7        09-26  ███████▊            19.5
09-20  ██████▍             16        09-27  ██████████████▏     35.5
09-21  ████████▌           21.5      09-28  ████                10
09-22  ██████▊             17        09-29  ███▏                 8   (61 → 4 at the repair)
09-23  ███▌                 9        09-30  ████                10
09-24  █████████▏          23        10-01  ████▊               12
```

- **725 distinct failing items** appeared in those samples. Median observed lifetime is
  about 3h and p90 about 23h; both are lower bounds, because samples are about 4h apart.
- **Individual breaks do get fixed. New ones land faster.** No sampled run since 09-18
  had zero failing tests.
- **Lint is part of the churn.** It was red in 44 of 75 sampled runs, with a different
  gate each time: symvision ×25, flags ×8, toobig ×6, mypy ×3, ruff, test-waits.

---

## 3. Why master stays red

### 3.1 Nothing stands between an agent and master

- **No branch protection.** `GET /branches/master/protection` returns 404, and there are
  no rulesets.
- **Direct pushes at high volume.** 1,146 linear commits since 09-17, about 90 per day.
- **Landing proceeds whatever the check said.** Ordinary `sase final submit` takes no
  covering receipt and records `"unverified"` instead of refusing
  (`src/sase/finalizers/declaration.py:_verdict_provenance`).
- **The bead-close rule is only prompt text.** "A check failure reproducing on the clean
  base tree does not block close" (`d5aa86dfc2`) is a judgment the agent makes, not a
  check the host enforces.
- **The gate always reports too late.** Master Gate is post-push and takes 7–15 minutes.
  The median gap between commits is 11 minutes, and 43% of gaps are under 9 minutes. So
  commit N's verdict usually arrives after commit N+1 has landed.

### 3.2 The local verification signal is dead

Here is the athena ToolRun ledger for `check`, covering 2026-09-24 to 10-01:

| Outcome | Runs | Share |
| --- | ---: | ---: |
| succeeded | 26 | **2.6%** |
| failed (exit ≠ 0) | 763 | 76% |
| killed by signal (174 of them at the ~538s inline ceiling, 537–540s) | 199 | 20% |
| lost | 12 | 1% |

- **Daily passes are near zero:** 0 of 138 on 09-27, 0 of 133 on 09-29, 2 of 129 on
  09-30.
- **Inherited failures dominate.** Failure triage weights 3,137 item-runs as KNOWN and
  only 1,335 as NEW.
- **One inherited failure reaches dozens of agents.** A single `test_kind_coverage`
  failure was seen by 39 different agents. Triage's newest label for it is **NEW**, not
  KNOWN, so each of those agents was told the failure was its own.

When every check is red, "my part looks fine" becomes the landing rule. The culprit
agents' own records show exactly that:

| Culprit | Agent's own `check` | Landed? |
| --- | --- | --- |
| `c6b802a647` | killed at 536s, no verdict | yes |
| `ce0f61846c` | killed at 539s, no verdict | yes |
| `ee1620e1b9` | exit 1. Stopped at an inherited `patch/stitch terminology` lint failure triaged UNKNOWN, **so tests never ran** | yes |
| `018061f6f2` | 5 runs, all failed. Three died in `_setup` before linting; two hand-off runs ended `recipe_not_finished` | yes |
| `e300173faf`, `56d5cd277e` | no `check` ToolRun recorded | yes |
| `ebf070e16a`, `297faf1d38` | ran on apollo, whose ledger I did not inspect | yes |

Kills fell from 61 a day (09-28) to 10–23 a day, and to 1 so far on 10-01, after
inline-then-escalate landed on 09-30. Pass rates did not move, because master's own
failures remain.

### 3.3 Test selection is *not* the gap

A natural guess is that diff-scoped selection skipped the broken tests. I replayed
`tools/select_tests --base <culprit>^` on six culprits. **All six escalated to the full
suite.** The fired rules were `serial-budget-exceeded`/`context-baseline-stale`,
`src-data-asset`, and `justfile`. Each broken test was in scope, so detection was not
what failed. The failure was ignored, killed, or lost among inherited failures.

### 3.4 Local ≠ CI: three skews

| Skew | Local agent | Master Gate | Proven impact |
| --- | --- | --- | --- |
| Python | 3.14.7 (ToolRun `TOOLCHAIN`) | 3.12 | Failure #8 is invisible locally. Reproduced: on 3.12 `'-i, --images' in help` is False, on 3.14 it is True |
| Rust core | `_setup` builds `sase_core_rs` from the workspace's **linked sase-core checkout**. The Justfile says dev installs do this "regardless" of the pin. sase-1cx.3's run spent 14 min on this build | builds `sase-core-revision.txt` | Different binaries. Slow, fragile setup: 49 recorded `_setup` failures in 7 days |
| Lint inputs | `_lint-flags` and `_lint-symvision` read **bead status** (`BD_COMMAND=tools/sase_bead`) | bead sidecar bootstrapped at CI time | Lint can turn red when a bead closes, with no code change (hazard, not proven for HEAD) |

### 3.5 Failures mask other failures

- **The Master Gate lint job is fail-fast.** `just lint` stops at the first red gate.
  On every red-lint run the next three steps are **skipped**: `SASE validation`,
  `Validate committed plans`, and `Build and verify package`. That was 44 of 75 sampled
  runs since 09-18.
- **Symvision reports one error class at a time.** `018061f6f2` surfaced 7 unused
  publics. Four were fixed. The other three were hidden behind a private-import error
  until `60b2d3dfdb` fixed that error. As a result, first-appearance attribution blames
  the fixer.
- **Local checks stop early too.** `just check` stops before the test stage on an
  UNKNOWN lint failure, even an inherited one (as with `ee1620e1b9`).
- **One import error fails two tests:** the module itself and the contract-manifest
  collector.

### 3.6 Repair without a freeze is a treadmill

The 09-29 repair `8c38eb6a9a` followed the playbook in the 09-28 report
(`research:202609/sase_master_ci_repair_and_pypi_0_18_release/…release.md`):

```text
21:59:11  0266fe4a12  61 failing tests
21:59:58  8c38eb6a9a   4  ← the repair, already red: 3 next-word tests + stale contract manifest
22:13:14  e300173faf   6
22:17:23  56d5cd277e   9
22:20:32  b07172cc1d  10
```

- **Earlier repairs ended the same way:** `c87c9d1aa9` (09-23), `0648306324` (09-24),
  and `ef7714508a` (09-28).
- **The 09-28 report recommended a stop-the-line window.** That window was never armed.
- **Of its keep-it-green list, only the telemetry split shipped** (`05c0e5886e`). There
  is still no build-cop or hold-on-red automation, lint is still fail-fast, and
  `check` still omits `toobig`.

### 3.7 Detection works; ownership does not

- **The backlog is large.** There are **68 open `ci` beads** and **91 open `flake`
  beads**; 33 `ci` beads were closed over the same window.
- **The current failures are already filed:** sase-1dh (+4), sase-1dn (+2), sase-1de
  (+2), sase-1cm (+2). Agents keep `+1`ing them instead of fixing them.
- **No automation repairs anything.** `ci_watch` only notifies; by contract it never
  launches repair agents.

### 3.8 The bill: no release for a month

- **PyPI is stale.** It still serves `sase` **0.17.1**, published 2026-08-29.
- **The release PR is blocked.** #299 (0.18.0) has been open since 08-30. `ci_watch`
  will not merge it while Master Gate is red.
- **The floor smoke is red too.** Its `release-core-floor-smoke` now fails because
  published `sase-core-rs` 0.36.1 is **missing 16 of 784** bindings that master
  requires.

---

## 4. Fix it now: one stop-the-line pass (≈half a day)

1. **Arm a hold on non-repair landings.** Pause feature epics until Master Gate is green
   on HEAD. Without this step, §3.6 repeats.
2. **Run one build-cop agent with an explicit `just check-full` authorization.** This is
   the CI-repair case `decisions:check-full-is-explicit` allows. Have it land the 8
   fixes in §1 as one commit and close sase-1dh, -1dn, -1de, and -1cm.
3. **Verify on CI, not only locally.** Run `gh workflow run master-gate.yml` on the fix
   SHA. Local 3.14 cannot see #8.
4. **Quarantine anything not fixable within the day, rather than leaving it red.** Mark
   it `xfail(strict=True, reason="sase-XXX")` through a reviewed quarantine list.
5. **Release the hold only on a green HEAD gate.** Then refresh #299 once a sase-core
   release carries the 16 bindings.

---

## 5. Recommended solution: a green-or-revert landing contract

Getting to green once is easy. Staying green requires that **a red change cannot land
unnoticed, and a red master cannot persist**. The parts below are ordered by leverage.
Parts A and B need new decision records, because they amend
`decisions:host-owned-completion` and `ci_watch`'s notify-only contract. Ship them
behind a feature flag, per the `sase_flags.md` memory.

**A. Refuse unverified landings (the gate).**

- **What changes:** the `builtin@commit` finalizer requires a covering `check` verdict
  receipt for the committed tree. The receipt must be `pass`, or `no-new` with zero
  NEW/UNKNOWN items.
- **What already exists:** receipts, fingerprints, and `accept: "no-new"` all exist.
  Today's default turns their absence into a recorded `unverified` (§3.1). This is a
  policy flip, not new machinery.
- **What it costs:** no new CI capacity, because agents already run 130–200 checks a
  day. Unlike the GitHub merge queue that `decisions:ci-two-speed-split` rejected, the
  gate runs locally.
- **Why A needs the stop-the-line pass first:** A only works on a green baseline. Then
  "any failure is yours" becomes true again, and KNOWN stops being a hiding place.

**B. Fix or revert on red (the safety net).**

- **Why it is needed:** Master Gate is already per-SHA so that failures are
  attributable. Nothing acts on that attribution yet.
- **What happens:** when SHA X is red and its parent was green, `ci_watch` (already
  polling every 5 minutes) arms a hold and launches one fix agent with X's diff and
  failing jobs.
- **The deadline:** if HEAD is not green within 60 minutes, it pushes `git revert X`.
- **What B catches:** semantic merge conflicts between concurrent agents, which A cannot
  see.

**C. Make local verification equal CI (parity).**

- **Python:** pin agent venvs to CI's version. Add `.python-version` = 3.12 and have
  `just install` honor it. The other option is to run Master Gate on 3.14 and leave 3.12
  to Full CI. Either way, the two must match.
- **Rust core:** build the local core from `sase-core-revision.txt`, or fail fast when
  the linked checkout differs from the pin. This also turns the 14-minute rebuild into a
  cache hit.
- **Lint inputs:** make bead-status-dependent lint read a committed snapshot, so lint is
  hermetic.

**D. Unmask.**

- **Master Gate:** run every lint gate and exit with a summary. Put `validate`, plans,
  and `build-check` in `if: always()` steps.
- **Symvision:** report every error class in one pass.
- **`just check`:** proceed to tests after an UNKNOWN lint failure and report both,
  without changing the exit code, in line with
  `decisions:triage-annotates-does-not-change-exit-codes`.

**E. Drain and quarantine.**

- **Age out stale `ci` beads.** One older than 24 hours gets either a fix or a reviewed
  quarantine entry with an expiry, so master is green or explicitly waived, never
  ambiently red.
- **Track it daily.** Report "hours since last green" in ACE.

**Order:** do §4 today. Ship **A + B + the Python half of C** this week, because they are
the three that break the treadmill. D, E, and the rest of C follow.

---

### Method and confidence

- **High confidence.** These come from GitHub Actions run history and logs (1,907 Master
  Gate runs since 09-01, and 196 run logs: 125 time samples plus about 70 bisect and
  repair-window probes). They also rest on local reproduction at HEAD:
  - 13 of 15 items fail on 3.14;
  - `test_contract_manifest` is the import error's cascade;
  - #8 fails only on 3.12.

  The rest comes from `select_tests` replays in a scratch worktree, the athena ToolRun
  ledger and triage groups, and code read in the current checkout.
- **Medium confidence:**
  - the culprits for #4 and #5, since those agents ran on apollo and their ledgers were
    not inspected;
  - the bead-status lint hazard, which is a mechanism I read in the code but did not
    observe flipping HEAD.
- **Prior work:** I built on the 2026-09-28 consolidated report. Its §5 diagnosis still
  holds. This report adds the culprit agents' own verification records, the selection
  replay, the Python and core skews, symvision masking, and a measurement of the repair
  treadmill.
