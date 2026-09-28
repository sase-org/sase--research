# Why master is red and PyPI is stuck — and how to ship the next release

Report: independent research on sase's failing CI and blocked PyPI release.
All CI observations below were read from live GitHub Actions runs on
2026-09-28 (UTC); the lint failure was additionally reproduced in the local
checkout. No peer swarm report was consulted.

## TL;DR

- PyPI is stuck at **0.17.1** (2026-08-29). A **0.18.0** release-please PR has
  been pending since 2026-08-30 and cannot land because CI is red.
- The last **100/100 Master Gate runs on master are failures** (oldest sampled:
  2026-09-27). Master has no green SHA to release from.
- The latest master SHA (`89e4882`) fails in **two independent places**:
  `lint` (file-size gate) and **6 of 8** fast-test shards, with ~35 distinct
  failing tests. Full (scheduled) CI is red in the same ways plus
  visual/contention/perf lanes.
- Most failures look like **guard/audit tests doing their job** (new code not
  yet allow-listed) or **stale expectations after intentional behavior changes**
  — i.e. fixable without redesign. A smaller subset (mock breakage, layout
  math, a 5s-timeout UI test, a contention SIGTERM) needs real debugging.
- Recommended path: fix in layers (lint gate → mechanical allow-lists →
  real-breakage triage), get one green Master Gate SHA, then release 0.18.0
  via the pending release-please PR (fallback: `publish_existing` dispatch).

## 1. How the release pipeline is supposed to work

Three workflows cooperate (all verified by reading `.github/workflows/`):

| Piece | File | Trigger | Role |
|---|---|---|---|
| PR CI | `ci.yml` | PRs to master, callable | lint + docs-build + 3-Python test matrix + visual + coverage |
| Master Gate | `master-gate.yml` | every master push, per-SHA, never cancelled | lint + 8 fast-test shards (the "is this SHA green?" signal) |
| Full CI | `full.yml` → calls `ci.yml` | schedule every 2h | exhaustive lane: coverage contexts, slow/cost, contention, visual, perf floors |
| Publish | `publish.yml` | schedule every 3h + manual dispatch | release-please PR management → build wheel → smoke → PyPI |

Key mechanics:

- `release-please-config.json` (python type) bumps `pyproject.toml` version
  (`name = "sase"`, currently `0.17.1`) and opens the `release-please--branches--master`
  PR. That PR (`chore(master): release 0.18.0`, opened 2026-08-30) is still open.
- `publish.yml` only builds/publishes when `release_created == 'true'` (i.e. the
  release PR merged) or on a manual `publish_existing: true` dispatch.
- `ci.yml`'s `build-core` job **skips release-please branches**, so the release
  PR's own CI run fails fast (~27s, observed on runs 36382098532 et al.:
  `build-core: skipped`, everything downstream skipped except
  `release-core-floor-smoke: failure`). The release PR can therefore never go
  green itself — the gate that matters is **Master Gate on master SHAs**.
- Both `ci.yml` and `master-gate.yml` pin the Rust core via
  `sase-core-revision.txt` (currently `cbe70f66…`, sase-core 0.35.1 wheel),
  so a sase-core push alone cannot redden master.

## 2. Measured state: how red is master?

- `gh run list --branch master --workflow "Master Gate" --limit 100`:
  **0 success / 100 failure**, spanning 2026-09-27 → 2026-09-28.
  (`Deploy Docs` succeeds on the same SHAs, so this is test/lint signal, not infra.)
- `Full CI` scheduled run 36382114111 (2026-09-28): `lint`, `test (3.12)`,
  `test (3.14)`, `visual-test`, `contention-test`, `perf-floors` all failed.
- PyPI `sase` version is still **0.17.1** (checked via pypi.org JSON).
- The `0.18.0` release notes already exist on the release-please branch; only
  the merge + publish leg is blocked.

### Latest master SHA under the microscope

Run **36398634120** = Master Gate on `89e4882` ("tool run block anatomy…",
2026-09-28T08:39Z):

| Job | Result |
|---|---|
| core-wheel | success |
| lint | **failure** — `just lint` → `_lint-toobig` exit 1 |
| test shards 1, 8 | success |
| test shards 2, 3, 4, 5, 6, 7 | **failure** |

The lint failure reproduces locally (`./.venv/bin/toobig src 1000 850 700`):

- `ERROR: src/sase/core/tool_run.py` — **1154 lines** (limit 1000)
- `ERROR: src/sase/tool/executor.py` — **1175 lines** (limit 1000)
- warnings near the limit: `plan_direct_approval.py` (960), `_agent_tabs.py`
  (880), `disk_footprint_inventory.py` (890)

## 3. Failing-test inventory (same run, `gh run view … --log-failed`)

Grouped by theme, not by shard, since several themes span shards:

**A. Audit/guard tests flagging unreviewed new code (mechanical fixes).**
These guards exist to force explicit review; the "extra items" are the fix list:

- `test_tracked_marker_path_passing_sites_are_reviewed` (shard 4) — 2 new sites:
  `finalizers/cli.py:_target_for_dir`,
  `axe/run_agent_directive_metadata.py:session_root_tab`.
- `test_no_system_clock_display_sites` (shard 7) — 8 new `datetime.fromtimestamp`
  sites, mostly in `ace/tui/tool_runs/blocks.py`, `update_gear.py`,
  `update_panel_state.py`, `tool/view_vocabulary.py` (note: `57b5074` "configured-tz
  clocks" suggests some are intentional and need tz-aware remediation, not just
  allow-listing).
- `test_every_value_slot_is_kinded_choiced_or_hinted` (shard 3) — 2 new
  completion slots from new `tool receipt`/`tool receipts` commands:
  `tool/receipt:tool_receipt_tool`, `tool/receipts:tool_receipts_days`.
- `test_project_sase_yml_matches_public_schema` (shard 2) —
  `Additional properties are not allowed ('receipt' was unexpected)`: the same
  new receipt feature is missing from the public JSON schema.
- `test_checked_in_snapshot_has_no_drift` /
  `test_current_structural_view_matches_checked_in_snapshot` (shard 2) — CLI
  completion spec out of sync with the argparse tree (same new-command cause).

**B. Completion-behavior tests vs. new `%tab` / agent-completion behavior
(shards 2, 7).** ~13 failures in `test_agent_completion.py` plus:

- `test_removed_auto_approval_directives_are_absent_from_completion` and
  `test_removed_tribe_spellings_are_absent_from_completion` — `%tab` candidates
  now appear where the tests demand absence. Either the `%tab` directive revival
  is intentional (update tests) or it is a regression (remove the candidates).
  This is the one theme-merge decision the fixer must make deliberately.

**C. TUI layout/scroll goldens that moved with recent feature work
(shards 4, 5, 7).**

- `test_expanded_overflowing_header_claims_half_page_scroll` — `deck_scroll.scroll_y`
  is 2.0, expected 0.0.
- `test_chrome_layout` (3 cases) — width assertions (`assert 200 == 96`,
  `134 > 134`, `34 < 34`).
- `test_open_action_opens_overlay_on_stash_with_trash_count` — `_trash_limit`
  is 100, test expects 20.
- `test_files_ctrl_j_scrolls_page_anchor_to_top` — 5.0s `wait_for` timeout
  (could be a slow-shard flake; it sits next to a 108s-teardown test in shard 7,
  so re-run before "fixing").

**D. Mock-interface breakage (shard 6, needs real debugging).**
`test_axe_run_agent_exec_repeat_env.py` — 7 failures, all
`AttributeError: Mock object has no attribute 'agent_meta'` (suggests
`agent_model`). Something renamed/added `agent_meta` on a context object and the
tests' mocks were not updated — or production code reads an attribute the
factory never sets. Either way this is a genuine code/test contract mismatch,
not a stale golden.

**E. Docs wording test (shard 6).**
`test_getting_started_muse_grok_wording_separates_provider_selection` — the
getting-started doc now routes Grok through `@small/@medium/@large` pools;
the test demands "never auto-detects" wording. Docs-vs-test intent decision.

**F. Full-CI-only extras** (scheduled run 36382114111): `contention-test`
killed by SIGTERM (timeout under load?), `perf-floors` failure, `visual-test`
failure (PNG goldens — the `Justfile` `check-full` commentary already warns
goldens may not be current). These do **not** block the Master Gate or the
release, but they are the reason Full CI has no green baseline either.

## 4. Why this blocks PyPI (the deadlock)

1. Branch protection (presumed; consistent with all evidence) requires green CI
   to merge the `release 0.18.0` PR — but that PR's own CI can never pass
   (release-please branch is excluded from `build-core`, failing in ~27s), and
   master itself is red, so there is no green SHA to cut from.
2. `publish.yml` will not build wheels without `release_created == 'true'`.
3. Result: every 3h the publish scheduler finds a pending, unmergeable release
   PR and does nothing. PyPI stays at 0.17.1 while master accumulates ~4 weeks
   of unreleased features (0.18.0 notes file already exists).

The manual escape hatch exists: `publish.yml` `workflow_dispatch` with
`publish_existing: true` skips release-please and builds/publishes the recorded
version — but publishing a red SHA to PyPI without triage would ship the
untested breakage in themes B–D to users.

## 5. Recommended solution

**Phase 0 — stop the line from getting redder (process, 1 PR).**
Require `just check` (the agent-default scoped recipe) green before master
pushes land; keep `just check-full` for explicit CI-failure repair as the
project's own decision records already mandate. The failure cluster shows
several pushes landing audit-guard violations that a local `just check` would
have caught (toobig, completion kinds, schema).

**Phase 1 — unblock the lint gate (mechanical, 1–2 PRs).**
Split `src/sase/core/tool_run.py` (1154 lines) and `src/sase/tool/executor.py`
(1175 lines) into focused modules the way recent commits already did for
`bead_touch_index`, `cli_work_handler`, and `run_agent_directives` (same
500-line convention, same facade-preserving pattern). This alone turns the
`lint` job green and reproduces locally, so it is verifiable without CI.

**Phase 2 — clear the mechanical guard failures (1 PR, mostly allow-lists).**
In order: add the two `tool/receipt(s)` completion kinds (`completion/kinds.py`),
sync the checked-in completion snapshot, add `receipt` to the public
`sase.yml` schema, and review + register the 2 path-passing sites and the 8
clock-display sites (converting the tz ones to configured-tz calls per the
`sase-1b2` precedent rather than blanket allow-listing). Re-run Master Gate;
expect shards 2-partial, 3, 4-partial to flip green.

**Phase 3 — adjudicate the intentional-change failures (needs owner decisions,
1 PR per decision).**
(a) `%tab` directive completion: keep + update tests, or remove (revert).
(b) `_trash_limit` 20 → 100, header-scroll and chrome-layout math: confirm new
behavior is correct, then update goldens/expectations. (c) Docs provider
wording: pick the supported claim, update the other side. (d) `agent_meta`
mock breakage: fix whichever side of the contract is wrong. (e) Re-run the
5s-timeout deck test in isolation before changing it.

**Phase 4 — release.**
When one Master Gate run is fully green: merge the pending `release 0.18.0` PR
(normal path — `publish.yml` then builds, smokes, and publishes). Only if the
release-please branch mechanics keep failing use the fallback:
`workflow_dispatch` with `publish_existing: true`, then verify the PyPI
`0.18.0` page and `uv pip install sase==0.18.0` smoke (`sase version`,
`sase core health --json`).

**Explicitly out of scope for unblocking the release:** Full-CI-only lanes
(contention SIGTERM, perf floors, visual PNG rebaselining, coverage contexts).
They should be triaged after 0.18.0 ships so the release does not wait on the
heaviest lane; the Master Gate is designed to be the per-SHA release signal.

## 6. Risks and open questions

- I did not inspect branch-protection settings, so "release PR requires green
  checks" is inferred from workflow design + the month-long stall, not observed.
- Shard-7 slowness (108s teardown, several 5–30s tests) may indicate a
  resource/timeout flake class independent of the assertion failures.
- The `agent_meta` mock failures could indicate production code reading an
  attribute that only some factories set — worth one focused debugging session
  rather than a bulk mock update.
- Full CI's `contention-test` SIGTERM and `perf-floors` were not root-caused
  here; they are scheduled-lane-only and do not gate PyPI, but they will
  re-redden the "master is always red" perception if ignored post-release.

## Sources

- `.github/workflows/ci.yml`, `master-gate.yml`, `publish.yml`, `full.yml`,
  `release-please-config.json`, `.release-please-manifest.json`, `pyproject.toml`
  (all read from the local checkout).
- `gh run list --branch master` (Master Gate last-100: 0 green) and
  `gh run view 36398634120 --log-failed` / `36382114111 --log-failed` (failure
  texts quoted above).
- Local reproduction: `./.venv/bin/toobig src 1000 850 700`.
- PyPI state: `https://pypi.org/pypi/sase/json` → `0.17.1`.
