# Red master, no PyPI release: what blocks `sase` 0.18.0 and how to unblock it

_Researcher: cld · 2026-09-28 · snapshot taken ~09:00Z against sase master `89e4882803`_

## TL;DR

`sase` has not reached PyPI since **0.17.1 (2026-08-29)**. Since then **1,676 commits**
have landed, and release PR **#299 (`chore(master): release 0.18.0`)** has been open since
2026-08-30. The PR is merged only by the `ci_watch` routine, and only when **all four** of
these conditions hold at once:

| # | `ci_watch` / publish precondition | State today | Red since |
| --- | --- | --- | --- |
| 1 | `Master Gate` green on master HEAD | **Red.** lint (`toobig`, 2 files) plus **29 failing tests** across 6 of 8 shards | 2026-09-18 (847 commits ago) |
| 2 | `Full CI` green, finished within the last 6h | **Red, and structurally unable to pass.** Two jobs time out every run and one kills its runner every run | 2026-08-29 (1 green out of ~171 runs) |
| 3 | Release PR checks green and `mergeStateStatus == CLEAN` | **Red.** `release-core-floor-smoke`: published `sase-core-rs` 0.35.1 lacks 10 bindings master calls | since the core pin moved past 0.35.1 |
| 4 | A `sase-core-rs` release on PyPI that contains those bindings | **Blocked.** sase-core CI is red too (macOS/Linux test flakes), so release-plz won't merge its v0.36.0 PR #315 | 2026-09-27 |

Condition 2 alone has made an automatic release impossible for a month. The heavy lane
has timed out in the same two jobs on every run since the day of the last release, so
even while Master Gate was still green (until 09-18), `ci_watch` could never merge.

**Recommendation (details in §6):**

1. Pause feature landings briefly.
2. Get `sase-core-rs` 0.36.0 published (fix or quarantine three sase-core test flakes,
   then dispatch the release cut).
3. Fix the ~13 small, deterministic Master Gate clusters. 26 of the 29 failures
   reproduce locally in 36s, each traceable to one recent commit.
4. Split the measurement/soak lanes (`test-cost`, `contention`, `coverage-contexts`) out of
   the release-gating `Full CI` workflow, and fix its real regressions.
5. Release. If waiting on step 4 is unacceptable, merge #299 manually once 1–3 are green.

Then add stop-the-line and invariant-test guards so master cannot silently stay red
again.

---

## 1. How a `sase` release actually happens

```
agents land on master (host-owned finalizers, direct push; master is NOT branch-protected)
        │
        ├─ push ──► Master Gate (.github/workflows/master-gate.yml): per-SHA lint + 8 test shards
        ├─ every 2h ─► Full CI (.github/workflows/full.yml → ci.yml, workflow_call): heavy lane
        │
Publish (.github/workflows/publish.yml, cron '17 */3 * * *')
        ├─ release job: release-please updates PR #299 on branch release-please--branches--master
        └─ sync-release-metadata: tools/ratchet_core_window + uv lock on that branch
                (ratchets `sase-core-rs>=X,<0.(minor+1).0` to the newest *complete* PyPI release)
        │
PR #299 CI (ci.yml on pull_request): every source lane is skipped for the release branch;
        only `release-core-floor-smoke` (+ PR title) runs. It installs sase with the EXACT
        published core floor and runs tools/check_sase_core_rs_bindings, validate, smokes,
        and the contract set.
        │
ci_watch (bugyi-chops `bugyi_chop_ci_watch`, athena AXE routine, every 5 min,
          chezmoi home/dot_config/sase/sase_athena.yml):
        gating_workflows[sase] = ["Master Gate"]   → HEAD must be green
        heavy_workflows[sase]  = ["Full CI"]       → newest completed run green and ≤ 6h old
        plan_release_merge(): PR MERGEABLE, mergeStateStatus CLEAN, every check COMPLETED+green
        → guarded `gh pr merge --merge`, max 1 merge per tick
        │
next Publish run: release-please creates tag/GitHub release → build → install-smoke
        (latest core) + install-smoke-core-floor (exact floor) → pypa publish (skip-existing)
```

`sase-core-rs` has its own release pipeline (`sase-core/.github/workflows/release-plz.yml`).
Pushes and the six-hourly heal keep release PR **#315 (`chore: release v0.36.0`)**
updated. Only the daily `41 7 * * *` cron, or a `workflow_dispatch` with `dry_run=false`,
runs `release-plz-merge`, which waits for the PR's checks to go green before merging.

**Consequence:** a `sase` release needs a green sase-core release PR first, then a
ratchet, then all of sase's own gates.

## 2. Evidence snapshot

- **PyPI**
  - `sase`: 0.17.0 (08-29 17:35Z) and 0.17.1 (08-29 23:22Z) are the latest.
  - `sase-core-rs`: 0.35.1 (09-27 14:09Z) is the latest. Storage is 2.68 GB of the
    10 GB quota, so quota is not a blocker.
- **Master Gate**
  - The last 400 runs all failed.
  - Last green: `f90c6b549f` on 2026-09-18 02:24Z.
  - Master has had continuous red since then across ~85 commits/day.
- **Full CI**
  - Since 08-27: 1 success (08-29 16:02Z, which is exactly what let 0.17.0/0.17.1 ship),
    156 failures, and 14 cancellations.
- **Release PR #299**
  - `mergeable=MERGEABLE`, `mergeStateStatus=UNSTABLE`.
  - The only substantive check, `release-core-floor-smoke`, fails:

    ```
    sase_core_rs 0.35.1 is missing 10 of 725 required binding(s):
      build_agent_tab_catalog, canonicalize_agent_tab_name,
      launch_scratch_liveness_wire_schema_version, managed_tmp_roots_list,
      managed_tmp_roots_register, managed_tmp_roots_wire_schema_version,
      observe_launch_scratch_liveness, tool_run_briefs, tool_run_live_glance,
      tool_run_node_summaries
    ```

  - Release notes are 65 KB. That's too big for a PR body, but below GitHub's
    release-body limit, so it's not a blocker.
- **sase master core pin**
  - `sase-core-revision.txt` = `cbe70f66…`, which is sase-core `origin/master` HEAD.
  - The pin is 13 commits past `v0.35.1`, including two `feat!` wire breaks (schema 11,
    fleet contract v7), so the next core is **0.36.0**.
  - sase's `pyproject.toml` still says `sase-core-rs>=0.35.0,<0.36.0`. The release branch
    says `>=0.35.1,<0.36.0`.
- **sase-core CI**
  - Red on master since `297bc1e3` (09-27 19:35Z). The failures change from run to run:
    - clippy (`manual_repeat_n`, `too_many_arguments`) for several commits;
    - then macOS `launch_scratch_liveness::tests::live_holder_matches_environ_path` and
      `managed_tmp_roots::tests::missing_roots_are_pruned_on_next_write`;
    - then Ubuntu
      `sase_gateway sudo_runner::tests::cli::python_hosted_launcher_preserves_isolated_module_prefix`
      ("worker did not record Python-hosted argv").
  - At master HEAD `cbe70f66`, macOS passed while the release-PR run of the same code
    (`d2aedc03`) failed macOS, so the macOS pair is **nondeterministic**.
  - PR #315's last three CI runs all failed on the macOS pair.
- **Open PR debris**
  - 17 `core-pin-ratchet-*` PRs (#302–#318), all superseded. Master already pins
    `cbe70f66`, the target of the newest one.
  - Each of those PRs ran the full `ci.yml`: #318's run spent about 5 runner-hours (3.13
    at 90 min, 3.12 at 82, 3.14 at 51, visual, perf, lint).
  - #300 (shard timings, 08-31) and #301 (08-20) are stale.

## 3. Blocker A: Master Gate (fast gate) at HEAD `89e4882803`

Run `36398634120`: `lint` failed, shards 2/3/4/5/6/7 failed, 1 and 8 passed.

### A.1 `lint`: only `toobig` fails

ruff, mypy, symvision, flag registry, and the other gates all passed.

```
ERROR: VIOLATION: src/sase/core/tool_run.py has 1154 lines (limit: 1000)
ERROR: VIOLATION: src/sase/tool/executor.py has 1175 lines (limit: 1000)
```

`just lint` aborts at `toobig`, so the later steps in that job (`just validate`,
`validate-committed-plans`, `build-check`) have **not run on master for days**. Expect
some new findings once `toobig` is fixed.

`toobig` is deliberately excluded from `just check` and `just check-full`. The
`toobig_split` routine owns splits, so agents can't see these violations locally. That
routine clearly lags the landing rate: `executor.py` was already over the limit in the
05:29Z Full CI run.

### A.2 Test failures

26 of the 29 reproduce locally and deterministically:
`pytest -n 4` on the 15 affected files, `26 failed, 134 passed in 36.51s`. Every cluster
traces to one recent feature commit whose tests or guard allowlists weren't updated.

| Cluster | Failing test(s) | Cause | Introduced by | Likely fix |
| --- | --- | --- | --- | --- |
| Agent completion (9) | `tests/ace/tui/test_agent_completion.py::*` | A new `('tab','main')` candidate group now leads every list (`['main','abc123def456']`, `('tab','main') != ('clan','review')`) | `372ecc97c3` feat(xprompt): `%tab` directive (09-27) | Update the expectations, or suppress the default `main` tab group when no tabs exist |
| Directive completion (2) | `test_directive_completion_candidates.py::test_removed_{auto_approval_directives,tribe_spellings}_are_absent_from_completion` | `%tab` matches prefixes the tests expect to be empty | `372ecc97c3` | Tighten the test query, or accept `%tab` explicitly |
| Exec agent tab (6) | `tests/test_axe_run_agent_exec_repeat_env.py::*` | `_export_exec_agent_tab` reads `ctx.agent_meta`; the tests' `Mock(spec=…)` lacks it | `aff4fc082f` feat(tabs): inherit agent tab across launches (09-27) | Add `agent_meta` to the test ctx, or make the export tolerate its absence |
| CLI completion (3) | `tests/completion/test_snapshot.py` ×2, `test_kind_coverage.py` | New `sase tool receipt` / `tool receipts` args: completion snapshot not regenerated, and `tool_receipt_tool` / `tool_receipts_days` have no ValueKind or hint | `281147666b` feat(tool): receipt execution CLI (09-26) | Regenerate the completion snapshot; add kinds or hints |
| Config schema (1) | `test_config_schema_tools.py::test_project_sase_yml_matches_public_schema` | `sase/sase.yml` `tools.check.receipt` isn't in the public JSON schema (`additionalProperties: false`) | `4e85d4bc05` feat(tool): adopt catalog receipt policy (09-26) | Add `receipt` to the tool schema |
| Timezone guard (1) | `test_timezone_display_guard.py::test_no_system_clock_display_sites` | New `datetime.fromtimestamp` display sites | `3786032efb` feat(gear): update-failure gear (09-27) in `update_gear.py:80,81,111`; `89e4882803` feat(runs-card) (09-28) in `tool_runs/blocks.py:153` | Route through the tz-aware display helper |
| Prompts overlay (1) | `test_prompts_overlay_entry_points.py::test_open_action_opens_overlay_on_stash_with_trash_count` | `_trash_limit` 100 ≠ test's 20 | `919ba740e6` 100-row trash (09-27) | Update the test |
| Header panel (1) | `test_agent_header_panel.py::test_expanded_overflowing_header_claims_half_page_scroll` | `scroll_y` 2.0 ≠ 0.0 | Recent deck/card-host work (`83dc078e33` Tools deck two card hosts, 09-28, or `2d8f2f0566` FINAL deck) | Investigate the scroll reset on expand |
| Marker audit (1) | `test_agent_artifact_marker_path_passing_audit.py` | Unreviewed site `src/sase/scripts/_agent_chat_from_name_failure.py:_resolve_failed_agent_transcript` | Identifier renames in `33e41c72e2` / `786539e6a6` (09-24) | Review the site and update the audit allowlist |
| Docs wording (1) | `test_docs_getting_started_providers.py::test_getting_started_muse_grok_wording_…` | Guarded sentence about Grok Build and `@small/@medium/@large/@xlarge` no longer in `docs/getting_started.md` | Docs refresh on 09-27 (`90d6138504` / `8b877f99f9` / `1ec4569d87`) | Restore the sentence, or update the guard to the new wording |
| Chrome layout (2) | `command_line/test_chrome_layout.py::test_chrome_recomposes…[wide0-narrow0]`, `::test_frame_width_cap_and_full_height_toggle_keep_the_labels` | `134 > 134`, `200 == 96` | Pass locally, so likely load-sensitive | Deflake (wait on a layout predicate) |
| Deck spread (1) | `decks/test_deck_spread_pilot.py::test_files_ctrl_j_scrolls_page_anchor_to_top` | 5s `wait_for` timeout | Pass locally, so a flake | Deflake |

The last three rows are the load-sensitive or flaky ones that pass locally. Full CI's
3.12 and 3.14 legs show the same set, plus `test_agent_list_watch_highlighted`,
`test_link_follow_entry_points::test_matrix_archived_plan_via_links_panel`,
`test_top_bar_indicators::test_busy_cluster_compacts_narrow_and_restores_wide`, and
`test_deck_block_spread_pilot`. Those pass locally at HEAD; some were likely fixed after
`e771faa853`, and some are flakes.

## 4. Blocker B: Full CI (heavy lane) cannot pass as designed

Job outcomes across the 12 most recent Full CI runs (09-25 → 09-28), plus a sample back
to 08-29:

| Job | Outcome pattern | Root cause | Kind |
| --- | --- | --- | --- |
| `test (3.13)`, which runs `just test-cost` | **Cancelled at the 90-min timeout on every run since 08-29** (reaches only ~56%) | The serial-ish cost-attribution lane over a ~49k-test suite no longer fits 90 min. It was added 08-10 (`ee9603d31e`); the suite has grown past it | Structural |
| `coverage-contexts` (`just test-contexts`) | Cancelled at the 60-min timeout on almost every run (85–97% done) | The suite outgrew the timeout | Structural |
| `contention-test` (`SASE_CONTENTION_REPEAT=3 just test-contention`) | Fails on every run: "The runner has received a shutdown signal", ~32 min in, during repeat 1/3 | 26 xdist workers pinned to 2 CPUs × 3 full-suite repeats. It can't finish in 90 min even if it survives, and the runner dies (most likely memory exhaustion) | Structural |
| `perf-floors` | Fails on every run | (a) `test_ace_terminal_smoke::test_sase_screenshot_cli_captures_png_with_tmux`: tmux socket path `/var/tmp/sase-d1260045/pytest-of-runner/pytest-0/popen-gw2/test_sase_screenshot_cli_captu0/tmux/tmux-1001/default` exceeds the AF_UNIX path limit ("File name too long"). (b) `test_sase_tool_runs_smoke` ×2 reproduce locally: `dod-1-catalog-sase` now also lists `test-visual` in the catalog; `dod-2-exact-execution` replay stderr now contains "no total order between the retained stdout and stderr streams"; `dod-8-live-monitor` fails too | Real harness drift plus a test-infra bug |
| `visual-test` (`--check`) | Fails on every run, status `failed` (not drift) | Consistent: `test_axe_chop_run_info_panel_png_snapshot` ("expected ChopItem at idx 2, got Lumb…"), `test_top_bar_usage_attention_narrow_png_snapshot`, `test_top_bar_usage_badges_crowded_narrow_png_snapshot`. Flaky: `test_config_center_flags_narrow_png_snapshot` (SUNSET wait) | Regressions plus 1 flake |
| `lint` | Fails | Same `toobig` as Master Gate | Regression |
| `test (3.12)` (`test-cov`), `test (3.14)` | Fail: 30 and 32 failures | The same clusters as §3. The 3.12 leg takes 79 min against a 90-min ceiling, which is close | Regressions |

Because `ci_watch._evaluate_heavy_lane` looks at the **workflow** conclusion of the newest
completed `Full CI` run, a telemetry lane timing out (cost, contention, contexts) blocks a
release just as surely as a real regression. Those three lanes are measurement tools,
not correctness gates:

- `coverage-contexts` feeds the selector's baseline;
- `test-cost` feeds the cost budgets;
- `contention` is a soak.

Mixing them into the release gate is the main design flaw.

`coverage-contexts` never completing also has a knock-on effect: the diff-scoped selector's
baseline goes stale. `tools/selection_health` shows `context-baseline-stale` firing 570
times and 71.7% of scoped runs escalating to the full suite. That makes local
`just check` slower and more contended.

## 5. Why master stays red: the systemic causes

1. **Landing rate far exceeds repair rate, and nothing stops the line.**
   - ~85 commits/day land by direct push from host-owned finalizers.
   - Master has no branch protection.
   - `ci_watch` only notifies. Its description says it "never creates gates, launch
     requests, repair agents". No routine is assigned to fix a red master.
   - Every cluster in §3 is a 1–3-line test or allowlist fix, yet they accumulate because
     nobody owns them.
2. **Local verification doesn't prevent landing.** Of the last 1,000 local
   `sase tool run check` ToolRuns (09-22 → 09-28, ~94% in sase):

   | State | Share |
   | --- | --- |
   | `failed` | ~77% |
   | `signaled` | ~14% |
   | `succeeded` | **~8%** |

   34 of the latest 40 failed runs were triaged `new_failures`, meaning failures
   attributed to the agent's own change, not KNOWN ones. With master red, a clean check is
   unreachable for everyone, so agents are conditioned to land on "my part looks fine".
3. **Whole-repo invariant tests aren't always selected, and once red they absorb new
   violations.**
   - The completion snapshot, kind coverage, config schema, marker audit, and docs
     wording guards are **not** in `tests/contract_manifest.txt`. The diff-scoped
     selector reaches them only by import closure.
   - `test_timezone_display_guard` **is** in the always-run contract set, yet it has been
     red since `3786032efb` (09-27). Today `89e4882803` added a second violation site
     under the same already-failing test ID. That is the broken-windows mechanism in
     action.
4. **The heavy lane has been red for a month, so its signal is ignored.** Three of its
   jobs can't pass by construction (§4), so a Full CI failure carries no information.
5. **Runner capacity is being wasted.**
   - `core-pin-ratchet.yml` opens a new `core-pin-ratchet-<sha>` branch and PR for every
     sase-core HEAD and never closes superseded ones. Meanwhile agents bump
     `sase-core-revision.txt` on master directly.
   - Each such PR runs the full `ci.yml`, about 5 runner-hours. 17 PRs is ≈85
     runner-hours in a week, competing with Master Gate and Full CI for the org's
     concurrent-job cap.
   - Full CI's 2-hourly schedule is actually firing only every ~5h.
6. **Core and app release trains are coupled, but CI doesn't show it until release
   time.** Master CI builds sase-core from the source pin, so it's always consistent. The
   only place the published floor is checked is the release PR, weeks later. By then the
   core has taken breaking (`feat!`) changes, needs a new minor (0.36.0), and its own CI
   has to be green on the day of the cut.

## 6. Recommended solution

### Phase 0: Stabilization window (same day, ~30 min of human time)

- **Pause feature landings** until Phase 2 is green. Stop launching feature epics, or arm
  a SASE hold for non-repair launches. At ~85 commits/day, fixing 29 failures while new
  ones land is a treadmill: the clusters in §3 all arrived in the last 72h.
- **Close the 17 superseded core-pin PRs (#302–#318).** Master already pins `cbe70f66`.
  This frees roughly 5 runner-hours per PR re-run. Also decide on #300 (stale shard
  timings) and #301.

### Phase 1: Publish `sase-core-rs` 0.36.0 (hard prerequisite for any sase release)

1. In sase-core, fix or quarantine the three nondeterministic tests:
   - **macOS** `launch_scratch_liveness::tests::live_holder_matches_environ_path` and
     `managed_tmp_roots::tests::missing_roots_are_pruned_on_next_write`. Suspect
     `/var` ↔ `/private/var` canonicalization of `tempdir()` paths, or cross-test env
     interference. The fix is to canonicalize both sides, or `#[cfg(target_os = "linux")]`
     the procfs-shaped test.
   - **Linux** `sase_gateway sudo_runner::tests::cli::python_hosted_launcher_preserves_isolated_module_prefix`,
     which is a timing race on the worker recording argv.
2. Get PR #315 (`release v0.36.0`) checks green. A re-run of the failed macOS job may
   suffice as a stopgap, but fix the flakes too.
3. Dispatch sase-core `release-plz.yml` with `dry_run=false` rather than waiting for the
   07:41 cut, which GitHub has been delaying by hours. Confirm on PyPI that 0.36.0 is
   *complete* (every expected wheel and the sdist).
4. In sase master, run `tools/ratchet_core_window` to move the dependency to
   `sase-core-rs>=0.36.0,<0.37.0` and refresh `uv.lock`. The release branch ratchets
   itself on the next Publish run via `sync-release-metadata`. Ratchet master too, so
   the two don't diverge.

### Phase 2: Green the Master Gate (1–2 focused agents, a few hours)

- Work the table in §3.2, cluster by cluster. Each cluster maps to one commit and one
  owner-sized fix: 9 + 2 tests for `%tab`, 6 for exec agent tab, 3 for the completion
  snapshot and kinds, 1 schema, 1 timezone guard, 1 trash limit, 1 header scroll, 1
  marker audit, 1 docs wording.
- Deflake the 3 load-sensitive TUI tests.
- Split `src/sase/core/tool_run.py` and `src/sase/tool/executor.py` below 1,000 lines.
  Then expect and fix whatever `just validate`, `validate-committed-plans`, and
  `build-check` surface, since they haven't run on master in a while.
- Verify with Master Gate on the resulting HEAD. A local `just check-full`, explicitly
  requested, is appropriate here because this is the CI-failure repair case the
  check-full decision reserves it for.

### Phase 3: Make `Full CI` passable, and keep it meaningful

- **Split the measurement lanes out of the release gate.** Move `test-cost` (today's
  `test (3.13)` leg), `contention-test`, and `coverage-contexts` into a separate scheduled
  workflow (for example `CI Telemetry`, nightly or weekly), with timeouts sized to
  reality: cost ≈ 3h, contexts ≈ 90 min.
  - Run a plain `just test` on 3.13 in Full CI so the version matrix stays covered.
  - Keep `ci_watch`'s `heavy_workflows[sase] = ["Full CI"]`. That way no change to
    bugyi-chops is needed, and the gate keeps meaning "correctness on the full matrix".
- **Right-size contention.** One repeat, a curated subset (the tests that have actually
  flaked), and fewer workers (e.g. 8 on 2 CPUs). As configured it can't finish in its
  timeout and kills the runner.
- **Fix the real heavy-lane regressions:**
  - `perf-floors`: set a short `TMUX_TMPDIR` (or `tmux -S` with a `mkdtemp` under
    `/tmp`) in the terminal-smoke fixture. Update `tools/smoke_sase_tool_runs` case
    expectations for `test-visual` in the catalog, the replay-order diagnostic, and live
    monitor DoD-8.
  - `visual-test`: fix the chop-run info panel ordering and the two narrow top-bar usage
    snapshots (probably crowding from the new update gear); deflake the SUNSET wait.
- Watch `test (3.12)` (`test-cov`) at 79/90 min. Shard it or raise the ceiling before it
  becomes the next permanent timeout.

### Phase 4: Cut 0.18.0

- **Preferred path:** once Phases 1–3 are green, trigger Publish with
  `gh workflow run publish.yml -f publish_existing=false`. That regenerates #299 and
  ratchets the floor. Then:
  1. `release-core-floor-smoke` should pass.
  2. `ci_watch` merges #299 on its next tick.
  3. The next Publish run creates the tag, builds, runs both install smokes, and uploads.
  4. Dispatch Publish again instead of waiting up to 3h.
- **Pragmatic path, if Phase 3 is going to take days:** after Phases 1 and 2, a
  **manual** merge of #299 is a defensible one-time bypass of the stale-heavy-lane
  condition. Do it only when #299's own checks are green and Master Gate at HEAD is
  green, and run Full CI once via `workflow_dispatch` so you know that the only reds are
  the three structural telemetry lanes. The publish job still builds and runs install
  smokes against both the latest core and the exact floor before uploading, so risk is
  bounded. Don't bypass Phase 1: a wheel against 0.35.1 would crash at runtime on the 10
  missing bindings.
- Verify afterwards: `pip install sase==0.18.0` in a clean venv, then
  `sase core health --json` and `sase version`.

### Phase 5: Keep it green (prevention)

1. **Stop-the-line automation.** When Master Gate on HEAD has been red for more than N
   hours (say 2), have a routine:
   - arm a landing or launch hold for non-repair work, and
   - launch or assign a single "build-cop" repair agent seeded with the failing job
     list.

   This contradicts `ci_watch`'s current "never launches repair agents" contract, so it
   needs a deliberate decision record. The current contract is exactly why 29 trivial
   failures accumulated.
2. **Always run the cheap whole-repo invariant tests in `just check`.** Add the
   completion snapshot and kind coverage, the config-schema test, the marker audit, and
   the docs-wording guards to `tests/contract_manifest.txt`. They are seconds of runtime
   and account for 6 of today's 29 failures. A 7th, the timezone guard, is already in
   the set; see the next item.
3. **Stop KNOWN from masking new violations.** A failing test ID that already fails on
   master shouldn't downgrade a *new* message payload to KNOWN. Today's timezone guard
   gained a second site under an already-red ID. Key the failure signature on the
   violation list, or treat guard tests as always-UNKNOWN when touched.
4. **Make `toobig` visible before landing.** Either run `toobig` on touched files in
   `just check`, or make CI's `toobig` warn-only and leave enforcement to the
   `toobig_split` routine. Today it's invisible locally but blocking in CI, which is the
   worst combination.
5. **Fix `core-pin-ratchet.yml`.** Reuse one branch (`core-pin-ratchet`, force-pushed)
   and one PR, and close superseded PRs. Or retire it, since agents already bump the pin
   on master.
6. **Catch core/app release skew continuously.** Add a cheap non-blocking job to Master
   Gate or Full CI that runs `tools/check_sase_core_rs_bindings` against the newest
   *published* `sase-core-rs` in the window. That way "needs a core release" shows up the
   day it happens, not weeks later at release time.
7. **Budget the heavy lane.** Record Full CI job durations against their timeouts and
   alert at 80%. The 3.13 and contexts lanes crossed their ceilings silently a month ago.

## 7. Confidence and gaps

- **High confidence.** The release-gating mechanics were read directly from
  `publish.yml`, `ci.yml`, `master-gate.yml`, the `ci_watch` config in chezmoi, and
  `bugyi_chops/ci_watch.py` (`plan_release_merge`, `_release_gate_reason`,
  `_evaluate_heavy_lane`). The missing-binding list comes verbatim from #299's CI log. The
  26 local reproductions are deterministic.
- **Medium confidence.**
  - The per-cluster fix suggestions: I did not implement them.
  - The contention runner-death cause: memory exhaustion is inferred from the symptom,
    not observed.
  - That the sase-core macOS failures are nondeterministic: inferred from HEAD passing
    on master while the same code failed on the release PR.
- **Not verified.**
  - Whether `just validate`, `validate-committed-plans`, and `build-check` are clean
    (masked by `toobig`).
  - Whether the sase-core clippy failures seen on 09-27 are fixed at HEAD. They didn't
    appear in the latest runs.
  - Exact Full CI run durations once the telemetry lanes are split out.
