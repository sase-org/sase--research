# Red master and the blocked 0.18.0 PyPI release

_Researcher: grk. Date: 2026-09-28. Independent of the other swarm reports._

## Verdict

Two independent red layers are keeping `sase` off PyPI. The one that actually prevents a wheel from uploading is a **published-core skew**: master Python already calls ten `sase_core_rs` bindings that are not in the latest PyPI `sase-core-rs==0.35.1`. The next core release (`v0.36.0`) is itself blocked by two macOS-only tests. Separately, **Master Gate has been continuously red since 2026-09-18** (888 failing runs in the sampled window, last green `f90c6b549f6e`), and **Full CI has been red since the last sase release on 2026-08-29**.

Last published `sase` is still **0.17.1**, uploaded 2026-08-29T23:22:14Z. Master `pyproject.toml` and `.release-please-manifest.json` still say `0.17.1`. Release-please already opened [PR #299](https://github.com/sase-org/sase/pull/299) `chore(master): release 0.18.0`; the Publish workflow “succeeds” every three hours because it only refreshes that unmerged PR.

## How release actually works

CI is two-speed ([decision `ci-two-speed-split`](../../memory/decisions/ci-two-speed-split.md)):

| Lane | Workflow | Trigger | Role |
| --- | --- | --- | --- |
| Fast gate | `.github/workflows/master-gate.yml` | every master push | lint + 8 shards of the non-visual fast suite, 20 min ceilings |
| Heavy lane | `.github/workflows/full.yml` → `ci.yml` | every 2 hours | 3.12/3.13/3.14 tests, visual goldens, contention, perf floors, coverage contexts |
| Release | `.github/workflows/publish.yml` | every 3 hours | release-please PR +, only when a release is created, build/smoke/PyPI upload |

`publish.yml` does **not** wait for Master Gate or Full CI. It runs `googleapis/release-please-action@v5`, then `sync-release-metadata` (ratchets the published `sase-core-rs` window on the pending release branch), and only builds/uploads when `release_created==true`. That flag is true after the release PR merges and release-please cuts a GitHub Release.

The release PR skips the source lanes (`ci.yml` excludes `release-please--branches--master` from `build-core` / lint / tests). The **only CI job that actually runs on PR #299** is `release-core-floor-smoke`: install `sase` editable against the **exact published PyPI floor**, then `tools/check_sase_core_rs_bindings`. That job exists because sase 0.11.0 shipped calling an unreleased binding and every PyPI install crashed on first TUI clan render. Local `just install` never sees this class of bug because it builds from the sibling `sase-core` checkout.

GitHub reports **no branch protection** on `master` (404). Merging #299 is a social/process gate, not a required-check gate. Shipping 0.18.0 before `sase-core-rs` 0.36.0 is on PyPI would recreate the 0.11.0 crash class.

## Layer 1 — PyPI cannot ship until `sase-core-rs` 0.36.0 exists

### What the floor smoke said

[PR #299 CI run 36382098532](https://github.com/sase-org/sase/actions/runs/36382098532), job `release-core-floor-smoke`:

```
sase-core-rs floor confirmed: 0.35.1
sase_core_rs 0.35.1 is missing 10 of 725 required binding(s):
  build_agent_tab_catalog
  canonicalize_agent_tab_name
  launch_scratch_liveness_wire_schema_version
  managed_tmp_roots_list
  managed_tmp_roots_register
  managed_tmp_roots_wire_schema_version
  observe_launch_scratch_liveness
  tool_run_briefs
  tool_run_live_glance
  tool_run_node_summaries
```

Those names match Python `require_rust_binding` sites plus the explicit `REQUIRED_BINDINGS` table in `tools/check_sase_core_rs_bindings`. Master Gate does **not** fail this check: it installs a wheel built from `sase-core-revision.txt` (`cbe70f66fb28a6b14a023a1458f26cf0f75de911`), which already contains the bindings.

### Core pin vs published tag

Linked `sase-core` HEAD / sase pin `cbe70f6` is **13 commits after** tag `v0.35.1` (`2fb5c57`, published 2026-09-27T13:35:10Z). Workspace Cargo version is still `0.35.1`; the unreleased commits include two `feat!` breaks (`agent_tab` on scan wire schema 11; shell→turn rename), so the next PyPI version is correctly **0.36.0**, not a 0.35.2 republish (those filenames are burned).

sase currently requires `sase-core-rs>=0.35.0,<0.36.0`. Once 0.36.0 is on PyPI, `publish.yml`’s `sync-release-metadata` job (`tools/ratchet_core_window`) is supposed to move that window on the release-please branch in one commit. Do not have a feature agent edit `pyproject.toml` for this; docs/rust_backend.md assigns the window to that job.

### Why 0.36.0 itself cannot publish yet

[sase-core PR #315](https://github.com/sase-org/sase-core/pull/315) `chore: release v0.36.0` is MERGEABLE but **UNSTABLE**. Ubuntu CI, maturin smoke, and release-script checks pass. macOS CI fails ([run 36382645360](https://github.com/sase-org/sase-core/actions/runs/36382645360)):

```
failures:
    launch_scratch_liveness::tests::live_holder_matches_environ_path
    managed_tmp_roots::tests::missing_roots_are_pruned_on_next_write
```

Both are in the exact new modules sase is waiting on:

1. `live_holder_matches_environ_path` — `assert result.candidates[0].live` on macOS 26 arm64. The probe is `/proc`-shaped; Darwin does not look like Linux procfs, so a live holder is classified dead.
2. `missing_roots_are_pruned_on_next_write` — left `/private/var/folders/.../kept`, right `/var/folders/.../kept`. macOS `TMPDIR` is a symlink into `/private`; the test compares lexical paths instead of `realpath`.

Until those two tests pass (or are correctly gated to Linux), release-plz will not merge #315, will not tag `v0.36.0`, and will not upload wheels. sase-core Release-plz runs on master currently **succeed** the same way sase Publish succeeds: they refresh the unmerged PR.

PyPI storage is **not** the current blocker. After the 0.34.0–0.34.9 deletion, `sase-core-rs` is ~2.49 GiB of 10 GiB; 0.35.1 is five files / 82 MiB. Headroom is enough for several 0.36.x publishes.

## Layer 2 — Master Gate is the “always red” the user sees

Sample: [run 36398634120](https://github.com/sase-org/sase/actions/runs/36398634120) on `89e4882803` (2026-09-28T08:39Z). `core-wheel` and shards 1 and 8 passed. Failed: **lint**, shards **2, 3, 4, 5, 6, 7**. Deploy Docs is green on the same SHAs.

Last green Master Gate in a 900-run window: **2026-09-18T02:24:06Z**, SHA `f90c6b549f6e`, [run 35299164480](https://github.com/sase-org/sase/actions/runs/35299164480). Every sampled master-gate run since then is failure or still in flight.

`just check` does **not** run `toobig`. Agents land on a red master because their default gate never sees the lint job that CI runs.

### Lint (`just toobig`)

```
ERROR: VIOLATION: src/sase/core/tool_run.py has 1154 lines (limit: 1000)
ERROR: VIOLATION: src/sase/tool/executor.py has 1175 lines (limit: 1000)
```

Also warning-band: `disk_footprint_inventory.py` 890, `plan_direct_approval.py` 960.

- `executor.py` is already [sase-1a9](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1a9/README.md) (filed at 1168 lines; now 1175).
- `tool_run.py` 1154 has **no dedicated CI bead**.
- Splits are owned by the `toobig_split` routine (`#!sase/toobig_split`), not by a random feature agent. `just check` / `just check-full` deliberately omit this gate.

### Fast-suite failures on that SHA (29 nodes)

Grouped by what to do. Counts are from the 89e4882803 Master Gate logs.

#### Mechanical allowlist / snapshot / docs (do these first; hours, not design)

| Node | Failure | Existing bead |
| --- | --- | --- |
| `tests/test_agent_artifact_marker_path_passing_audit.py::test_tracked_marker_path_passing_sites_are_reviewed` | extra unreviewed sites `finalizers/cli.py:_target_for_dir`, `axe/run_agent_directive_metadata.py:session_root_tab` | **sase-1by** |
| `tests/test_docs_getting_started_providers.py::test_getting_started_muse_grok_wording_separates_provider_selection` | docs no longer enumerate `@small/@medium/@large/@xlarge`; test still wants the old sentence | **sase-1as** (+3) |
| `tests/completion/test_kind_coverage.py` | uncaptioned slots `tool/receipt:tool_receipt_tool`, `tool/receipts:tool_receipts_days` | called out on **sase-1ab.10.2** follow-up; no dedicated open CI bead |
| `tests/completion/test_snapshot.py::test_checked_in_snapshot_has_no_drift` and `test_current_structural_view_matches_checked_in_snapshot` | argparse tree drifted; `just sync-completion-spec` rewrites the snapshot | covered in spirit by **sase-18s**; not a product bug |
| `tests/test_config_schema_tools.py::test_project_sase_yml_matches_public_schema` | `sase/sase.yml` `tools.check.receipt` is unexpected under `additionalProperties: false` | **untracked**. `src/sase/config/sase.schema.json` `toolDefinition` has no `receipt` property even though `docs/tool.md` documents the E4 policy and the project file already has `receipt: {accept: [pass, no_new_failures], ttl: 2h}` |
| `tests/ace/tui/actions/test_prompts_overlay_entry_points.py::test_open_action_opens_overlay_on_stash_with_trash_count` | `assert 100 == 20` after 919ba740e raised the trash limit | **sase-1bq** |
| `tests/test_timezone_display_guard.py::test_no_system_clock_display_sites` | `datetime.fromtimestamp` / `datetime.now()` in `tool_runs/blocks.py`, `update_gear.py`, `update_panel_state.py`, `tool/view_vocabulary.py` | **sase-1bp** (gear/panel); extra sites beyond that bead |

#### Tests that still assume pre-`%tab` completion

These fail because `%tab` (and related agent-tab / named-proc completion) now appears in candidate lists the tests still expect to be empty or singleton.

| Node | Symptom |
| --- | --- |
| `tests/ace/tui/test_agent_completion.py::test_build_agent_completion_candidates_enriches_visible_named_agents` | extra `'@review'`-style / tab candidates |
| `…::test_agent_session_completion_candidate_attaches_cached_plan_preview` | preview is `None` |
| `…::test_agent_session_completion_candidate_build_does_not_resolve_plan_or_bead_io` | `'main' == 'ship'` |
| `…::test_build_agent_completion_candidates_humanizes_vcs_badge_and_searches_raw` | `assert None is not None` |
| `…::test_completion_inserts_bare_local_names_and_searches_raw_alias` | extra `'main'` |
| `…::test_build_agent_completion_candidates_derives_ordered_groups` | group order includes tab |
| `…::test_named_proc_completion_candidate_uses_exact_proc_id` | extra `'main'` |
| `…::test_named_proc_is_not_also_offered_as_a_plain_agent_candidate` | extra `'tab'` |
| `…::test_build_agent_completion_candidates_omits_empty_clan` | leftover candidate |
| `tests/ace/tui/widgets/test_directive_completion_candidates.py::test_removed_auto_approval_directives_are_absent_from_completion` | `%approve`/`%plan`/`%tale`/`%epic` still offered (as snippets) |
| `…::test_removed_tribe_spellings_are_absent_from_completion` | `%t` now matches **`%tab`**, so `assert candidates == []` is obsolete |

sase-1bc.6.1.6.1 notes already describe “Reconcile clean-base completion assertions with `%tab` candidates”. No dedicated open CI bead for the nine `test_agent_completion.py` nodes.

#### Mock / field skew

`tests/test_axe_run_agent_exec_repeat_env.py` — six tests, all `AttributeError: Mock object has no attribute 'agent_meta'`. `run_execution_loop` now reads `ctx.agent_meta` in `_export_exec_agent_tab` (agent-tabs epic). The mocks use `spec=AgentExecContext` and never set `agent_meta`. **Untracked.** Fix is adding `ctx.agent_meta = {}` (or dropping `spec=` tightness) in that file.

#### TUI behavior that needs a real decision, not a snapshot bump

| Node | Failure | Bead |
| --- | --- | --- |
| `tests/ace/tui/widgets/test_agent_header_panel.py::test_expanded_overflowing_header_claims_half_page_scroll` | `assert 2.0 == 0.0` — `pin_to_bottom` settles async | **sase-1b8** (+4), size large |
| `tests/ace/tui/command_line/test_chrome_layout.py::test_chrome_recomposes_and_stays_aligned_on_resize[…]` | `assert 134 > 134` | **sase-1a6** |
| `…::test_frame_width_cap_and_full_height_toggle_keep_the_labels` | `assert 200 == 96` | **sase-1a6** |
| `tests/ace/tui/widgets/decks/test_deck_spread_pilot.py::test_files_ctrl_j_scrolls_page_anchor_to_top` | `wait_for` 5s timeout | **sase-1a7** (filed as flake; it also fails Master Gate) |

## Layer 3 — Full CI extras (release freshness)

Last green Full CI in the sampled window: **2026-08-29T16:02:53Z**, SHA `25565fca1232`, [run 33261893215](https://github.com/sase-org/sase/actions/runs/33261893215) — the same calendar day as PyPI 0.17.1. Every Full CI run since then is red (156 failures before that one success).

Latest Full CI [run 36382114111](https://github.com/sase-org/sase/actions/runs/36382114111) on `e771faa853`:

| Job | Result | Notes |
| --- | --- | --- |
| `full / lint` | fail | same toobig pair |
| `full / test (3.12)` | fail | same fast-suite nodes plus coverage leg |
| `full / test (3.14)` | fail | same |
| `full / test (3.13)` | cancelled | cost-budget leg cancelled after siblings failed |
| `full / visual-test` | fail | `just fix-tui-screenshots --check` (step 4). Open CI beads already cover large golden drift: sase-15t, sase-16o, sase-176, sase-19z, sase-1ba, plus flakes sase-19w / sase-1a3 / sase-1bb / sase-1bh |
| `full / perf-floors` | fail | both “Run slow tests” and “Run view-hints regression floor” |
| `full / contention-test` | fail | harness **cancelled** (SIGTERM), not a demonstrated product failure |
| `full / coverage-contexts` | cancelled | follow-on |
| `full / ace-page-group-isolation` | success | |
| `full / build-core` | success | |

`ci_watch` (decision text) wants both a green per-SHA Master Gate **and** a Full CI run younger than `heavy_max_age_hours`. That lumberjack lives in operator AXE config, not in this repo’s `default_config.yml`. Even if someone force-merged #299, a ci_watch-gated human release would still refuse.

## What is *not* blocking PyPI

- Quota on `sase-core-rs` (2.49 GiB used).
- Docs deploy (green).
- Publish workflow health (green, but it never creates a release).
- A missing release-please PR (it exists: #299, files are changelog / version / lock only).
- Branch protection (none).
- Need to republish 0.35.1 (filenames already used; next version is 0.36.0).

## Recommended solution

Do this in order. Skipping step 1 and merging sase 0.18.0 produces a PyPI wheel that crashes on the ten missing bindings — the failure mode `release-core-floor-smoke` exists to prevent.

### 1. Unblock and publish `sase-core-rs` 0.36.0 (critical path)

Work in the linked `sase-core` checkout.

1. Fix the two macOS tests on PR #315’s tree:
   - Canonicalize managed-tmp paths with `realpath` / `std::fs::canonicalize` before compare (`/var` vs `/private/var`).
   - Make `live_holder_matches_environ_path` pass on Darwin (use `libproc` / `sysctl` KERN_PROC, or skip/cfg the `/proc` assertion on non-Linux with a Linux-only live-holder test). Do not weaken the Linux probe; sase-1bw is a different fail-closed SSH issue.
2. Re-run sase-core CI until macOS is green; let release-plz merge #315 and upload the five 0.36.0 artifacts.
3. Confirm `https://pypi.org/pypi/sase-core-rs/0.36.0/json` lists all five files before touching sase.

### 2. Let sase’s release branch pick up 0.36.0

Do not hand-edit `pyproject.toml` on master. Either wait for the next `publish.yml` schedule (cron `17 */3 * * *`) or dispatch Publish with `publish_existing=false`. `sync-release-metadata` should commit `chore: sync release metadata` on `release-please--branches--master`, moving `sase-core-rs>=0.36.0,<0.37.0` and `uv.lock`. Then `release-core-floor-smoke` on #299 must go green (bindings present on the published floor, contract pytest against that wheel).

### 3. Turn Master Gate green (required for an honest 0.18.0)

A green floor-smoke PR still publishes **current master source**. Users would get the TUI/completion/timezone bugs those tests catch. Batch the work:

**Wave A — mechanical (one or two small PRs, no product decisions)**

- Split `src/sase/tool/executor.py` and `src/sase/core/tool_run.py` via `#!sase/toobig_split` (closes sase-1a9; file a CI bead for `tool_run.py` if the split lands as its own change).
- Add the two marker-path sites to the reviewed allowlist **or** stop passing marker paths there (sase-1by).
- Update `tests/test_docs_getting_started_providers.py` to the generated-table wording (sase-1as).
- Caption `tool/receipt` and `tool/receipts` in `src/sase/completion/kinds.py` (or `argparse` choices / `value_hint`).
- Run `just sync-completion-spec`.
- Add `receipt` to `toolDefinition` in `src/sase/config/sase.schema.json` (and any generated-schema path `load_config_schema` actually reads) to match `docs/tool.md` and `sase/sase.yml`.
- Pin the overlay trash assertion at 100 (sase-1bq).
- Route the four timezone sites through the configured-tz helper (sase-1bp plus `tool_runs/blocks.py` and `tool/view_vocabulary.py`).
- Set `ctx.agent_meta = {}` on the six `test_axe_run_agent_exec_repeat_env.py` mocks.

**Wave B — completion tests vs `%tab` (one focused PR)**

Rewrite `tests/ace/tui/test_agent_completion.py` and the two directive-completion “removed spelling” tests so `%tab` is a first-class expected candidate and `%t` is no longer required to be empty. Confirm `%approve`/`%plan`/`%tale`/`%epic` are actually gone from the catalog; if they still appear as snippets, that is a product leak, not a test update.

**Wave C — TUI behavior (needs an owner, not a golden bump)**

- sase-1b8: wait for pin settle **or** stop claiming half-page header scroll. Four independent +1s; this has been red for ~21h of landing agents.
- sase-1a6: chrome resize math.
- sase-1a7: treat as flake only after a focused pass; it failed the fast gate too.

Do not wait for Full CI visual goldens before Wave A/B. Visual is a heavy-lane problem; Master Gate does not run it.

### 4. Cut 0.18.0

When Master Gate is green on a SHA **and** #299’s `release-core-floor-smoke` is green against `sase-core-rs==0.36.0`:

1. Merge [sase PR #299](https://github.com/sase-org/sase/pull/299) (or let release-please auto-merge).
2. Next `publish.yml` run should set `release_created=true`, `uv build`, run both install-smoke jobs (latest core and exact floor), then `pypa/gh-action-pypi-publish` with `skip-existing: true`.
3. Confirm `https://pypi.org/pypi/sase/0.18.0/json` and `sase-core-rs>=0.36.0,<0.37.0` in that release’s `requires_dist`.
4. Optionally `just pypi-smoke` from `smoke/pypi/`.

### 5. Full CI after the cut (or in parallel once Master Gate is green)

Visual goldens and perf floors are a month stale. They are a **freshness** prerequisite for the next release after 0.18.0 if `ci_watch.heavy_max_age_hours` is enforced, and they are the reason Full CI has been red since 0.17.1. Contention on the sampled run was cancelled, not independently failed — re-evaluate after lint/tests are green.

A dedicated visual pass (`just fix-tui-screenshots` locally, inspect the report, land goldens) plus the open visual CI beads (sase-15t, sase-16o, sase-176, sase-19z, sase-1ba) is the right follow-up epic, not a blocker to *starting* step 1.

## Suggested ownership split

| Work | Where | Size |
| --- | --- | --- |
| macOS liveness + tmp-path canonicalize | sase-core, unblocks PR #315 | small/medium, Darwin-specific |
| Floor ratchet | automatic on next Publish after 0.36.0 | none |
| Wave A mechanical sase fixes | sase master | medium, many independent files |
| Wave B `%tab` completion tests | sase, agent-tabs fallout | small |
| Wave C TUI (sase-1b8, sase-1a6) | sase ACE | large (already sized) |
| toobig splits | `#!sase/toobig_split` | owned by that routine |
| Visual/perf Full CI | after Master Gate is green | large, many existing beads |

## Evidence (primary)

- Master Gate fail logs: GitHub Actions run `36398634120` (SHA `89e4882803`)
- Floor smoke: run `36382098532` job `release-core-floor-smoke` on [PR #299](https://github.com/sase-org/sase/pull/299)
- sase-core macOS: run `36382645360` on [PR #315](https://github.com/sase-org/sase-core/pull/315)
- Last green Master Gate: `f90c6b549f6e` @ 2026-09-18T02:24:06Z
- Last green Full CI: `25565fca1232` @ 2026-08-29T16:02:53Z
- Last sase PyPI: 0.17.1 @ 2026-08-29T23:22:14Z
- Latest sase-core-rs PyPI: 0.35.1 @ 2026-09-27T13:35:10Z
- Pin: `sase-core-revision.txt` = `cbe70f66fb28a6b14a023a1458f26cf0f75de911` (13 commits past `v0.35.1`)
