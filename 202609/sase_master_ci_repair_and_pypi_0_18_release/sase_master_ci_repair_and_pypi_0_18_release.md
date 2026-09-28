# Getting sase master green and shipping 0.18.0 to PyPI

**Consolidated report** · 2026-09-28 · snapshot ~10:10Z · sase master `5b409a5aa`,
sase-core master `33b0250`

**Sources.** Five independent researcher reports (`__cdx`, `__cld`, `__grk`, `__mus`,
`__gem` in this directory), taken at master `89e4882803` (~08:40–09:40Z), plus the lead
researcher's own checks. I re-inventoried Master Gate at the newest HEAD, read the
sase-core test code, looked at the last six sase-core CI runs, measured Full CI job
durations, read the `ci_watch` gate code and config, checked branch protection and the
`publish.yml` semantics, and surveyed the open CI bead backlog.

---

## Bottom line

PyPI has served `sase` **0.17.1** since 2026-08-29. Since then 1,676 commits have
landed, and release-please PR **#299 (`chore(master): release 0.18.0`)** has been open
since 08-30. Three gates stand between master and PyPI. They are listed in dependency
order, and the first two can be worked in parallel:

| # | Gate | State now | Size of fix |
| --- | --- | --- | --- |
| 1 | **`sase-core-rs` 0.36.0 must be on PyPI.** #299's `release-core-floor-smoke` installs the published floor, and 0.35.1 lacks the bindings master calls. | Core release PR #315 is blocked by **two macOS tests that fail on every run**. Both come from one path-canonicalization bug on macOS (`/var` vs `/private/var`). | Small. One Rust fix plus one test fix. |
| 2 | **Master Gate green on HEAD.** | Lint and **all 8 shards are red, with 49 failing tests.** An hour earlier it was 29 failures in 6 shards. The count grows with every landing. | Medium. About a third clears with one pin bump. Most of the rest are 1–3 line test or allowlist fixes. About 7 need real TUI debugging. Two oversized files need splitting. |
| 3 | **Full CI green and ≤6h old.** `ci_watch` needs this before it will auto-merge #299. | Red on every run since 08-29 (1 green out of ~171 runs). Three telemetry lanes **cannot pass as configured**: two always hit their timeouts and one kills its runner. | Small workflow change, plus real perf-floor and visual fixes. |

**Recommendation (§7):**

1. Declare a short stop-the-line window.
2. Fix the sase-core macOS bug and publish 0.36.0.
3. In parallel, bump the sase core pin, then clear the Master Gate clusters in waves.
4. Move the three measurement lanes out of the release-gating Full CI.
5. Let Publish ratchet #299 to `sase-core-rs>=0.36.0,<0.37.0`, then merge and verify
   `sase==0.18.0`.

If the Full CI work would take more than about a day, a one-time manual merge of #299 is
a defensible bypass, under the strict criteria in §7.4.

---

## 1. How a release actually happens (verified)

```text
agents land on master by direct push (no branch protection: API 404, no rulesets)
  ├─ every push ─► Master Gate: core-wheel from sase-core-revision.txt → lint + 8 fast shards
  ├─ cron 17 */2 ─► Full CI (full.yml → ci.yml): 3.12 cov / 3.13 cost / 3.14, visual,
  │                 perf-floors, contention, coverage-contexts
  └─ cron 17 */3 ─► Publish: release-please refreshes PR #299
                    └─ sync-release-metadata: tools/ratchet_core_window moves the
                       sase-core-rs window on the release branch to the newest complete
                       PyPI core
PR #299 CI: build-core, lint, tests, and visual are all SKIPPED for the release branch.
            Only release-core-floor-smoke runs: sase + the EXACT published core floor
            + check_sase_core_rs_bindings + contract tests.
ci_watch (bugyi-chops, athena AXE, every 5 min, merge_enabled: true) merges #299 only if:
  (a) Master Gate is green on HEAD, (b) the newest completed Full CI is green and ≤ 6h old,
  (c) #299 is MERGEABLE + CLEAN with every check green, (d) no publish/release-please
  run is in flight
next Publish run: release_created=true → uv build → install-smoke (latest core) +
  install-smoke-core-floor (exact floor) → PyPI trusted publish (skip-existing)
```

Facts that settle points the researchers disagreed on:

- **There is no branch protection.** The only thing that holds #299 back is `ci_watch`'s
  fail-closed gate (`plan_release_merge`, `_release_gate_reason`,
  `_evaluate_heavy_lane`, with `heavy_max_age_hours: 6` in chezmoi `sase_athena.yml`). A
  human can merge #299 at any time. mus's assumption that branch protection is involved
  is wrong.
- **`publish_existing=true` cannot ship 0.18.0.** It checks out master and builds "the
  existing release version recorded on master". That version is 0.17.1, so
  `skip-existing` turns the run into a no-op, or worse, rebuilds 0.17.1 from different
  source. It is a recovery path for an already-cut release whose upload failed.
  mus's fallback suggestion should be discarded.
- **Don't hand-edit the `sase-core-rs` window on master.** `docs/rust_backend.md` ("Who
  owns the published version window") assigns it to `sync-release-metadata` on the
  release branch. cld and gem suggested ratcheting master by hand; that contradicts the
  project's rules. The CI **source pin** (`sase-core-revision.txt`) is a different thing,
  and agents are supposed to move it.
- `release-core-floor-smoke` is **working as designed**. It exists because 0.11.0 shipped
  calling an unreleased binding and crashed on every PyPI install. Do not weaken it,
  skip it, or widen the range to an unpublished core.

## 2. Gate 1: publish `sase-core-rs` 0.36.0

**What is missing.** At HEAD, `check_sase_core_rs_bindings` counts 741 required bindings.
Published 0.35.1 lacks **13** of them:

- the 10 bindings in #299's last floor-smoke log: `build_agent_tab_catalog`,
  `canonicalize_agent_tab_name`, `launch_scratch_liveness_*` (2),
  `managed_tmp_roots_*` (3), `tool_run_briefs`, `tool_run_live_glance`,
  `tool_run_node_summaries`;
- 3 goal bindings that `17d2beb76` (sase-1bu.6, 09:36Z) now requires: `goal_card_view`,
  `goal_card_markdown`, `goal_citation_line`.

All 13 are on sase-core master. Its HEAD `33b0250` (v0.35.1+14) includes two `feat!`
wire breaks, so the next version is correctly **0.36.0**. Release PR **#315** (head
`5bb80ccb`, which contains `33b0250`) passes Ubuntu, maturin build/import smoke, and the
release scripts. **Only macOS fails.**

**The macOS failures are deterministic.** cld said they were not, and that is refuted:
the same two tests failed on **all six** recent sase-core CI runs, on both master
(`c32f88d`, `cbe70f6`, `33b0250`) and the release branch (runs 36363326101 →
36405594754).

1. `launch_scratch_liveness::tests::live_holder_matches_environ_path`
   (`launch_scratch_liveness.rs:558`).
   - The test builds a **fake procfs root** under `tempdir()`, so grk's theory that
     Darwin lacks `/proc` is wrong.
   - It writes `TMPDIR=<candidate>/nested` into a fake `environ`. That `nested`
     directory does not exist.
   - `normalize_path` (line 387) canonicalizes only paths that exist. So the candidate
     becomes `/private/var/...`, the nonexistent descendant stays `/var/.../nested`,
     `is_at_or_under` returns false, and a live holder is reported dead.
   - This is a **real product bug on macOS**, not a test artifact.
   - **Fix:** canonicalize the deepest existing ancestor and re-append the missing
     suffix. That puts existing and future paths on the same prefix. Do not gate the
     test to Linux.
2. `managed_tmp_roots::tests::missing_roots_are_pruned_on_next_write`
   (`managed_tmp_roots.rs:351`).
   - `validate_root_candidate` stores the canonical `/private/var/...` path, while the
     test expects the logical `/var/...` spelling.
   - Canonical storage is the safer contract: dedup, broad-root refusal, and reaping all
     work on one identity.
   - **Fix:** compare against `kept.canonicalize()`, and correct the misleading comment
     ("Canonicalize for comparison only") so it says storage is canonical.

**After the fix:**

1. Land it on sase-core master and let release-plz refresh #315.
2. Once all checks are green, dispatch `release-plz.yml` with `dry_run=false` rather
   than waiting for the daily 07:41 cut.
3. Confirm that `pypi.org/pypi/sase-core-rs/0.36.0/json` lists every wheel plus the
   sdist.

PyPI quota is not a blocker: about 2.5 of 10 GiB is used. Watch item: cld saw a Linux
`sase_gateway ... python_hosted_launcher_preserves_isolated_module_prefix` flake on
09-27. It did not appear in the last six runs.

## 3. Gate 2: Master Gate at HEAD `5b409a5aa`

Run 36405319366 (09:43Z) failed `lint` and all 8 shards. The last green run was
`f90c6b549f` on **2026-09-18 02:24Z**. The latest completed runs got steadily worse:

| Run | SHA | Failing tests |
| --- | --- | --- |
| 36398634120 | `89e4882` | 29 |
| 36404463252 | `8c134b8` | 23* |
| 36404623628 | `17d2beb` | 34* |
| 36405319366 | `5b409a5` | **49** |

\* Several shards in those two runs died in setup (`uv pip install` hit **PyPI 503s**
fetching `tree-sitter-html`). Failure sets therefore vary between runs, so a test that
drops out of the list has not necessarily been fixed. No researcher reported this.

### 3.1 Lint is masked in layers

`just lint` runs its steps in order and stops at the first failure:

1. It fails first at **"Check pinned core bindings"**: the CI-built core from pin
   `cbe70f66` lacks the 3 goal bindings.
2. Behind that sits **`toobig`**:
   - `src/sase/core/tool_run.py` has 1,154 lines and `src/sase/tool/executor.py` has
     1,175, against a 1,000-line limit. Only `executor.py` has a bead (sase-1a9).
   - In the warning band: `plan_direct_approval.py` (960), `tool_runs/view.py` (938),
     `disk_footprint_inventory.py` (890), `_agent_tabs.py` (880).
3. Behind that, `just validate`, `validate-committed-plans`, and `build-check` **have not
   run on master for days**. Expect new findings once `toobig` passes.
4. `just check` omits `toobig` altogether (`Justfile:765`), so agents never see it
   locally.

### 3.2 Test failures by cluster (49 at HEAD)

| Cluster | # | Cause | Fix | Bead |
| --- | --- | --- | --- | --- |
| **Stale core pin**: `tests/goals/test_goal_artifact_kind.py` (10), `artifact_refs/test_{aliases,parsing,context}.py` (5), `test_check_sase_core_rs_bindings_tool.py` (1) | 16 | `17d2beb76` landed 9 min before its sase-core commit `33b0250`, and the pin never moved | Bump `sase-core-revision.txt` to `33b0250f91b81ebe9913796574e5faf787f741cf` (expected to clear all 16; confirm) | none |
| **`%tab` fallout**: `test_agent_completion.py` (9), `test_directive_completion_candidates.py` removed-spelling tests (2) | 11 | `372ecc97c3` `%tab` adds a default `('tab','main')` group, and `%t`/`%ta` now legitimately match `%tab` | Update the expectations, or suppress the `main` tab group when no tabs exist. Assert the removed names (`%tale`, `%tribe`) explicitly instead of empty prefix results. If `%approve`/`%plan` still show up as snippets, that is a product leak | none (noted on sase-1bc.6.1.6.1) |
| **Mock skew**: `test_axe_run_agent_exec_repeat_env.py` | 6 | `_export_exec_agent_tab` reads `ctx.agent_meta`, which `Mock(spec=AgentExecContext)` lacks | Set `ctx.agent_meta = {}` in the fixture | none |
| **Admin Center Tools pane**: `test_admin_center_selection_resume[updates]`, `test_log_panel_keymap` alphabetical, `test_xprompt_browser_load_keymap` digits, `test_plugins_browser_pane_loading` "seven tabs", `test_config_center_resume` timeout | 5 | `8c134b816` added a tab, which breaks tab-count, order, and index assumptions (likely cause for the last two) | Update the tab-model expectations. Reproduce the two `wait_for` timeouts before touching them | none |
| **CLI completion**: `test_kind_coverage`, `test_snapshot` ×2 | 3 | `281147666b` `sase tool receipt(s)` | Add kinds or hints for `tool_receipt_tool` and `tool_receipts_days`, then run `just sync-completion-spec` | none |
| **Public schema**: `test_config_schema_tools` (`tools.check.receipt`), `test_config_schema` (`ace.keymaps.tool_runs`) | 2 | Receipt policy and Tools-pane keymaps were added to config but not to `sase.schema.json` | Add both properties to the schema | none |
| **Timezone guard**: `test_no_system_clock_display_sites` | 1 | 7 sites: `tool_runs/blocks.py:164`, `update_gear.py:80,81,111`, `update_panel_state.py:142,143`, `tool/view_vocabulary.py:131` | Route them through `sase.core.time`. **Don't** extend the allowlist | sase-1bp (partial) |
| **Marker path audit** | 1 | New unreviewed sites `finalizers/cli.py:_target_for_dir` and `axe/run_agent_directive_metadata.py:session_root_tab` | Review each site, then add it to the reviewed set | sase-1by |
| **Docs wording** | 1 | `docs/getting_started.md` rewrite (`90d6138504`) | Assert the current contract, not the old sentence | sase-1as |
| **Prompt trash limit** | 1 | `919ba740e` raised the limit from 20 to 100 | Update the assertion | sase-1bq |
| **TUI behavior**: header half-page scroll (`2.0 == 0.0`), files deck Ctrl-J 5s timeout | 2 | `pin_to_bottom` settles asynchronously, plus a load-sensitive `wait_for` | Wait for the pin to settle. Reproduce Ctrl-J before calling it a flake | sase-1b8, sase-1a7 |

Also expect `test_chrome_layout` resize nodes (sase-1a6). They failed at `89e4882` but
not at HEAD, so they are load-sensitive rather than fixed.

**The attribution matters.** Almost every cluster traces to one feature commit from
the last 72h that left its tests, allowlists, or schema out of date.

## 4. Gate 3: Full CI cannot pass as configured

These are measured from the last four completed runs (09-27 14:04Z → 09-28 05:29Z). No
Full CI has completed since 05:29Z: the 2-hour schedule is firing late, so the lane is
already outside `ci_watch`'s 6h window.

| Job | Outcome on all 4 runs | Root cause | Kind |
| --- | --- | --- | --- |
| `test (3.13)` = `just test-cost` | **cancelled at exactly 90m** | The cost-attribution lane no longer fits its ceiling. grk's "cancelled after siblings failed" is wrong: `fail-fast` is false | Structural |
| `coverage-contexts` | **cancelled at exactly 60m** | Suite outgrew the timeout. It also starves the diff-scoped selector's baseline: cld measured `context-baseline-stale` firing 570×, with 71.7% of scoped runs escalating to the full suite | Structural |
| `contention-test` (`SASE_CONTENTION_REPEAT=3`) | fails at ~32m: "runner has received a shutdown signal" | 3 full-suite repeats with many xdist workers on a 2-CPU runner. Runner death is probably memory (inferred) | Structural |
| `perf-floors` | fail | Three real problems: (1) tmux socket path "File name too long" in `test_sase_screenshot_cli_captures_png_with_tmux` (sase-18w); (2) two `tools/smoke_sase_tool_runs` harness cases drifted (`test-visual` now in catalog, replay stream-order diagnostic, DoD-8 live monitor); (3) `view-hints-perf-check` floor (cdx: 15.0 ms p50 vs 12 ms floor) | Real |
| `visual-test` | fail | Mix of golden drift and flakes: the SUNSET wait in `config_center_flags_narrow`; per cld, chop-run info panel ordering and narrow top-bar usage (sase-18n). The backlog includes sase-x5, 15t, 16o, 176, 19z, 1ba | Real + flake |
| `lint`, `test (3.12)`, `test (3.14)` | fail (30 / 32 tests) | Same as Master Gate. **3.12 `test-cov` takes 74–79m of its 90m ceiling**, so it is next in line to time out | Regression |

`_evaluate_heavy_lane` checks the **workflow** conclusion. A telemetry lane hitting its
timeout therefore blocks a release exactly as a real regression would. That is the
design flaw: `test-cost`, `coverage-contexts`, and `contention` are measurement and soak
tools, not correctness gates.

This is why automatic release has been impossible since 08-29, including 08-29 → 09-18,
when Master Gate was still green. Note also that the `contention-test` job only runs
when `event_name == 'schedule'`, so a manually dispatched Full CI skips it.

## 5. Why master stays red (systemic causes)

1. **Nothing owns a red master, and the discovery-to-repair loop is broken.**
   - About 85 commits land per day by direct push.
   - `ci_watch` only notifies. Its contract says it "never creates gates, launch
     requests, repair agents".
   - There are **62 open `ci` task beads** (oldest about a month, 22 older than 10 days)
     and **89 open `flake` beads**. Agents file the failures reliably; nobody drains
     them.
2. **The local gate cannot keep master clean.**
   - `just check` excludes `toobig`.
   - The whole-repo invariant tests (completion snapshot and kinds, config schema,
     marker audit, docs wording) are not in `tests/contract_manifest.txt`. The scoped
     selector reaches them only through import closure.
   - cld measured about **8% `succeeded`** across the last 1,000 `sase tool run check`
     runs. With master red, a clean check is unreachable, so "my part looks fine" has
     become the landing norm.
3. **Broken windows via KNOWN.** `test_timezone_display_guard` is already in the contract
   set and has been red since `3786032efb`. New violation sites keep landing under the
   same failing test ID and are classified as known.
4. **Cross-repo landing race.** `17d2beb76` landed in sase before its sase-core commit
   existed on master, so the pin could not move with it. One unsynchronized commit broke
   16 tests plus lint.
5. **Wasted runners.**
   - `core-pin-ratchet.yml` has left **17 superseded PRs** (#302–#318). Master already
     pins past most of them.
   - Each PR runs the full `ci.yml`, about 5 runner-hours.
   - They compete with Master Gate and Full CI, and help explain why Full CI fires late.
6. **Core/app release skew only shows up at release time.**
   - `just check` does run `tools/probe_core_floor --advisory`, but only as a warning.
   - The hard floor check runs only on #299, weeks after the skew began.

## 6. Disagreements between the reports, resolved

| Question | Resolution | Evidence |
| --- | --- | --- |
| Are the core macOS failures flaky? (cld: yes) | **No.** They fail on every run, on master and the release branch, with the same `/private/var` vs `/var` diff | 6/6 recent sase-core CI runs |
| Is `live_holder...` failing because Darwin lacks `/proc`? (grk) | **No.** The test uses a fake proc root. The cause is `normalize_path` on a nonexistent descendant (cdx is right) | `launch_scratch_liveness.rs:387,538-559` |
| Does branch protection block #299? (mus) | **No.** Master is unprotected. The gate is `ci_watch` | `gh api .../protection` → 404 |
| Is `publish_existing` a usable fallback? (mus) | **No.** It republishes master's recorded version, 0.17.1 | `publish.yml:9-12,126,353` |
| Does Full CI gate the release? (mus: out of scope; cld: yes) | **Yes, for automatic merge.** `heavy_workflows: ["Full CI"]`, max age 6h | chezmoi `sase_athena.yml:140-147`; `ci_watch.py:702` |
| Why is `test (3.13)` cancelled? (grk: siblings failed) | **90-minute timeout**, on every run | Job durations of exactly 90m; `fail-fast: false` |
| Should master's `pyproject.toml` window be ratcheted by hand? (cld, gem) | **No.** That is `sync-release-metadata`'s job; only bump the CI source pin | `docs/rust_backend.md` §"Who owns the published version window" |
| How many bindings are missing? (10 in most reports) | **13 at HEAD** (10 + 3 goal bindings) | HEAD lint log |
| Failure count / shard spread | **49 in 8/8 shards at HEAD**, not 29 in 6/8 | Run 36405319366 |

## 7. Recommended solution

### 7.0 Today: stop the treadmill (human, about 30 minutes)

- **Pause feature landings until Master Gate is green.** Arm a SASE hold on non-repair
  launches, or simply stop launching feature epics. At the current landing rate, 20
  failures appeared in the hour this research took.
- **Close the 17 superseded `core-pin-ratchet-*` PRs** (#302–#318), and decide what to do
  with stale #300 and #301. This frees runner capacity for Master Gate and Full CI.

### 7.1 Track A: sase-core 0.36.0 (1 agent, runs in parallel with 7.2)

1. In the linked sase-core checkout, make `normalize_path` canonicalize by
   deepest existing ancestor, and fix the canonical-storage test and comment (§2).
2. Pass sase-core's check recipe, land on master, and let release-plz refresh #315 until
   **all** checks are green.
3. Dispatch `release-plz.yml` with `dry_run=false`, then verify that the 0.36.0 files are
   complete on PyPI.

### 7.2 Track B: green the Master Gate (1–2 repair agents, in waves)

Tell the repair agents explicitly that `just check-full` is authorized. Per the
`check-full-is-explicit` decision, this is exactly the CI-repair case it is meant for.

1. **Wave 1, pin bump.** Set `sase-core-revision.txt` to `33b0250f…`, or to the later
   sase-core commit that carries the macOS fix. This should clear the lint pinned-binding
   step and about 16 tests.
2. **Wave 2, mechanical.** No product decisions needed:
   - add the completion kinds and sync the spec;
   - add the two schema properties (`tools.*.receipt`, `ace.keymaps.tool_runs`);
   - set `agent_meta` on the mock;
   - update the trash-limit, docs-wording, and Admin Center tab-model expectations;
   - review the marker-audit sites;
   - convert the 7 timezone sites to `sase.core.time`.
3. **Wave 3, `%tab` tests.** Rewrite the agent-completion and directive-completion
   expectations to treat `%tab`/`main` as first-class. Check that no removed directive
   still leaks as a snippet.
4. **Wave 4, `toobig`.** Split `tool_run.py` and `executor.py` along existing seams, for
   example ledger projections and settlement/reporting helpers. Then fix whatever
   `validate`, `validate-committed-plans`, and `build-check` report once they finally
   run.
5. **Wave 5, TUI behavior.** Fix header-scroll settle (sase-1b8) and Ctrl-J anchor
   (sase-1a7). Reproduce the two Admin Center `wait_for` timeouts and chrome-layout resize
   (sase-1a6). Read the `tui` reference memory first, and do not bump snapshots without
   understanding the behavior.
6. **Done when:** Master Gate is green on HEAD. Re-inventory from the newest run before
   each wave, because failure sets shift with PyPI install flakes and new landings.

### 7.3 Track C: make Full CI a meaningful, passable release gate (1 agent, 1 workflow PR plus fixes)

- **Move `test-cost`, `coverage-contexts`, and `contention` into a separate scheduled
  `CI Telemetry` workflow** with realistic timeouts: cost about 3h, contexts about 90m,
  contention at 1 repeat with fewer workers or a curated subset.
  - In Full CI, run plain `just test` on 3.13 so the version matrix stays covered.
  - `ci_watch` needs no change (`heavy_workflows` still says `"Full CI"`), and the
    `ci-two-speed-split` intent is preserved: Full CI stays a correctness gate.
- **Fix the real perf-floor regressions:**
  - use a short `TMUX_TMPDIR` or `mkdtemp` socket dir (sase-18w);
  - update the `smoke_sase_tool_runs` cases for the new catalog entry, the replay
    diagnostic, and DoD-8;
  - rerun the view-hints floor on the final SHA and optimize if it stays at about 15 ms.
- **Visual:** reproduce the semantic timeouts first. Rebaseline only the goldens whose
  drift is intended, working through the existing visual beads. Do not bulk-accept.
- Shard `test-cov` or raise its ceiling before it becomes the fourth permanent timeout.

### 7.4 Cut 0.18.0

1. When 0.36.0 is on PyPI, dispatch `publish.yml` with `publish_existing=false`. This
   refreshes #299 from current master and ratchets it to
   `sase-core-rs>=0.36.0,<0.37.0` plus `uv.lock`.
2. Require #299's `release-core-floor-smoke` to pass against 0.36.0.
3. **Preferred:** with Master Gate green and a green Full CI ≤6h old, let `ci_watch`
   merge #299 on its next tick.
4. **Pragmatic bypass, one time only,** if Track C will take more than about a day.
   Merge #299 manually only when **all** of these hold:
   - Master Gate is green on HEAD;
   - #299's floor smoke is green;
   - a dispatched Full CI on that SHA shows the Python legs green, with the only reds
     being the structural telemetry lanes and pre-existing visual/perf items that
     already have beads.

   Risk is bounded: Publish still runs `install-smoke` against both the latest core and
   the exact floor before uploading. **Never bypass Track A.** A 0.18.0 wheel built
   against 0.35.1 crashes at runtime on the 13 missing bindings.
5. Dispatch Publish again instead of waiting up to 3h for `release_created`. Then verify:
   - PyPI JSON for 0.18.0 and `requires_dist` show `sase-core-rs>=0.36.0,<0.37.0`;
   - `pip install sase==0.18.0` works in a clean venv;
   - `sase version` and `sase core health --json` are correct.

### 7.5 Keep it green (follow-ups; file them after the release)

1. **Stop-the-line automation.** If Master Gate on HEAD stays red for more than N hours,
   arm a hold on non-repair launches and launch a single "build-cop" repair agent seeded
   with the failing jobs and the matching `ci` beads. This reverses `ci_watch`'s
   "never launches repair agents" contract, so it needs a **new decision record**. It is
   also the most important item here: the 62-bead backlog shows that detection alone
   does not work.
2. **Put the cheap whole-repo invariant tests in `tests/contract_manifest.txt`:**
   completion snapshot and kinds, config schemas, marker audit, docs-wording guards.
3. **Make `toobig` visible to `just check`** for touched files, at least as a warning.
4. **Stop KNOWN from masking new violations.** Key guard-test failure signatures on the
   violation payload, not only the test ID.
5. **Enforce cross-repo landing order.** A sase commit whose code requires unpinned
   sase-core bindings should be refused, or held until the pin can move in the same
   landing.
6. **Fix `core-pin-ratchet.yml`.** Reuse one branch and PR and close superseded ones, or
   retire it, since agents already move the pin on master.
7. **Promote core-floor skew from advisory to visible CI.** Add a non-blocking Master Gate
   job running `check_sase_core_rs_bindings` against the newest published core, so
   "needs a core release" surfaces the day it happens.
8. **Budget CI lanes.** Alert when a job's duration passes 80% of its timeout.
9. **Harden the install step against PyPI 503s:** uv retries, cache, or a pre-resolved
   lock artifact.

## 8. Confidence and gaps

- **High confidence**, verified directly this turn:
  - the HEAD failure inventory and its attribution across the four latest Master Gate
    runs;
  - that the macOS failures are deterministic, with the root cause read in code;
  - the `ci_watch` gate logic and config;
  - no branch protection;
  - `publish_existing` semantics;
  - Full CI timeouts;
  - the PR and bead backlogs.
- **Medium confidence:**
  - that the pin bump clears all 16 goal and artifact-ref failures (the lint log and
    error messages point there, but I did not run it);
  - the Admin Center attribution for the two `wait_for` timeouts;
  - the contention runner-death cause.
- **Unverified:**
  - what `validate`, `validate-committed-plans`, and `build-check` report once `toobig`
    passes;
  - the exact visual-test failure set at HEAD;
  - Full CI durations after the telemetry split;
  - cld's ToolRun success-rate and selector-health figures, which I did not re-measure.
