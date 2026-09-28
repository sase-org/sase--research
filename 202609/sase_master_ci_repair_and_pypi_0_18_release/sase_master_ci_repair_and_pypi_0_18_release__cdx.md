# Recovering SASE CI and the 0.18.0 PyPI release

Research snapshot: 2026-09-28, approximately 09:40 UTC. This report separates the
latest completed CI evidence from runs that were still in progress at the cutoff.

## Executive finding

The next release is already staged as SASE PR
[#299, `chore(master): release 0.18.0`](https://github.com/sase-org/sase/pull/299),
but two independent gates prevent a responsible release:

1. The release PR's exact-floor smoke test installs the published
   `sase-core-rs==0.35.1`, which lacks ten bindings now required by SASE. Those
   bindings exist on current `sase-core` master, but the pending 0.36.0 core release
   is blocked by two macOS path-normalization tests.
2. SASE master remains red. The latest completed Master Gate at the research cutoff
   failed with roughly thirty test failures across six of eight shards plus two
   file-size lint violations. The latest completed scheduled Full CI also failed in
   lint, tests, visual, performance, and contention lanes, although that run was
   already stale and the contention lane appears to have been terminated by runner
   shutdown rather than by a code assertion.

The fastest safe path is therefore a two-track repair: release `sase-core-rs` 0.36.0
after fixing its two macOS failures, while simultaneously repairing SASE's current
Master Gate and then validating a fresh Full CI run at the final release SHA. Merging
the SASE release PR before the core wheel exists cannot work: the release-branch smoke
test deliberately tests the lowest published core version in its dependency window.

## Release state and mechanics

- PyPI currently serves SASE
  [0.17.1](https://pypi.org/project/sase/0.17.1/), uploaded 2026-08-29. Master still
  declares 0.17.1; release-please owns the 0.18.0 version changes on PR #299.
- PR #299 updates the changelog, `pyproject.toml`, `src/sase/__init__.py`, and
  `uv.lock` for 0.18.0. It was mergeable but `UNSTABLE` at the cutoff because
  `release-core-floor-smoke` failed.
- The release branch currently requires `sase-core-rs>=0.35.1,<0.36.0`. Its failed
  smoke job installed exactly 0.35.1 and found these ten missing bindings:

  ```text
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

- The scheduled Publish workflow is healthy as orchestration, but a successful
  workflow run does not itself mean a package was published. Its ordinary scheduled
  path updates release metadata; build, install-smoke, and trusted PyPI publishing run
  only when release-please creates a GitHub release (or when the explicit
  `publish_existing` recovery path is manually requested).
- Once a new core version is on PyPI, `tools/ratchet_core_window
  --allow-transitive-lock-refresh` is designed to update the release branch and lock
  file. The expected next window is `>=0.36.0,<0.37.0`; the exact-floor smoke must then
  pass with the published 0.36.0 wheel before PR #299 is merged.
- The publish workflow does not encode a direct dependency on the scheduled Full CI
  workflow. Consequently, keeping a red master from releasing is presently a release
  discipline decision, not a guarantee provided by `publish.yml`. A fresh green Full
  CI result should be treated as an explicit release criterion.

## Immediate blocker: `sase-core-rs` 0.36.0

Current `sase-core` master contains all ten missing bindings. The open core release PR
[#315, `chore: release v0.36.0`](https://github.com/sase-org/sase-core/pull/315)
successfully passed Ubuntu, release-script, and maturin build/import-smoke checks, but
failed macOS with two tests. The same macOS failure pattern has kept core master red
since the launch-scratch work landed; it is not an isolated release-PR failure.

### 1. Nonexistent descendants are normalized inconsistently

`launch_scratch_liveness::tests::live_holder_matches_environ_path` compares an existing
temporary directory against `candidate.join("nested")`. On macOS, an existing path
canonicalizes from `/var/...` to `/private/var/...`, while the nonexistent descendant
cannot be canonicalized and remains `/var/.../nested`. The code then concludes that a
live holder is not live.

This should be fixed in the normalization primitive, not papered over in the test.
Normalize a nonexistent path by finding its deepest existing ancestor, canonicalizing
that ancestor, and appending the missing suffix. That gives both existing and future
descendant paths the same macOS-resolved prefix and follows the repository's rule that
both sides of a path comparison must be canonicalized consistently.

### 2. Managed-root storage has an unresolved logical-versus-canonical contract

`managed_tmp_roots::tests::missing_roots_are_pruned_on_next_write` expects the logical
`/var/...` spelling, while `validate_root_candidate` canonicalizes and persists the
resolved `/private/var/...` spelling. The current implementation's behavior is the
safer contract: canonical storage makes broad-root checks, deduplication, and later
reaping operate on one identity. Update the test and nearby contract comment to expect
the canonical value. If preserving the caller's spelling is a product requirement,
the alternative is to retain both raw and canonical forms; simply comparing raw and
canonical paths ad hoc would recreate the first bug.

After both fixes, run the core repository's normal check recipe on macOS and Linux,
land the changes, allow release PR #315 to refresh, and require its full check set to
pass before publishing 0.36.0. The core release workflow explicitly watches PR checks
before merge, so this is a hard blocker rather than optional cleanup.

## SASE master: latest completed Master Gate

The latest completed run inspected was
[Master Gate 36398634120](https://github.com/sase-org/sase/actions/runs/36398634120)
at `89e48828033154d528684db50a9bc0dfae9487a1`; it failed. By the cutoff master had
advanced twice, to `17d2beb7677cecb357680a93312b105f526620c2`, and
[Master Gate 36404623628](https://github.com/sase-org/sase/actions/runs/36404623628)
was still in progress. The newer run must supersede the inventory below once complete.

The completed failures fall into three useful buckets.

### Mechanical drift and contract synchronization

These should be repaired first because they are localized and will reduce CI noise:

| Failure | Likely action |
|---|---|
| `src/sase/core/tool_run.py` is 1,154 lines and `src/sase/tool/executor.py` is 1,175 lines | Split coherent responsibilities into smaller modules; do not weaken the 1,000-line guard. |
| Completion kind coverage lacks captions for `tool/receipt:tool_receipt_tool` and `tool/receipts:tool_receipts_days` | Add the missing kind metadata and its focused tests. |
| Two CLI completion snapshots differ from the argparse tree | Regenerate `tests/completion/snapshots/cli_spec.json` with `tools/sync_completion_spec`, then review the diff. |
| `sase/sase.yml` contains `tools.check.receipt`, but the JSON schema rejects `receipt` | Add the intended schema contract and schema tests. |
| Six repeat-environment tests use a mock without `agent_meta` | Bring the fixture up to the current runner input contract. |
| A docs test asserts an obsolete exact Grok Build sentence | Assert the current documented contract or a stable semantic fragment, not superseded prose. |
| Prompt Trash test expects 20 while the intended implementation now retains 100 | Update the stale expectation/config-derived assertion. |
| Tests asserting no `%ta` or `%t` candidates now see the new `%tab` directive | Test absence of the removed directive names themselves; a shared prefix can legitimately match `%tab`. |
| Agent completion tests did not account for the intentional built-in `main` tab candidate | Update ordering/grouping assertions to the new tab model, while preserving explicit tests for I/O and caching behavior. |

Two audit failures require review rather than automatic allowlisting:

- The artifact-marker path audit found new path-passing contexts in
  `src/sase/finalizers/cli.py:_target_for_dir` and
  `src/sase/axe/run_agent_directive_metadata.py:session_root_tab`. Confirm the paths are
  intentionally tracked and safe before adding them to the reviewed set.
- The timezone-display guard found direct `datetime.fromtimestamp`/`datetime.now` use
  in tool-run blocks, update gear/state, and tool view vocabulary. Route those displays
  through `sase.core.time`; extending the allowlist would preserve inconsistent local
  timezone behavior.

### Behavior-level TUI failures

These need reproduction and diagnosis; updating expected values without understanding
the interaction would be risky:

- expanded agent-header page-scroll positioning (`scroll_y` 2 instead of 0);
- files-deck Ctrl-J anchor-to-top timeout;
- command-line recompose width and frame-width invariants;
- several agent-completion enrichment and grouping behaviors associated with the new
  tab foundation.

The implementation agent should read the TUI reference memory before changing these
paths, reproduce each focused test, and fix shared layout/state causes before touching
snapshots.

## Scheduled Full CI: useful but stale evidence

The latest completed scheduled run inspected was
[Full CI 36382114111](https://github.com/sase-org/sase/actions/runs/36382114111)
at `e771faa...`, several commits behind the cutoff master. It failed in the following
lanes:

- **Python tests:** 30 failures on 3.12 and 32 on 3.14, substantially overlapping the
  current Master Gate failures. A few older TUI failures may already have moved, so
  this list must not be treated as current without a rerun.
- **Visual tests:** four failures. At least one was a semantic timeout waiting for the
  `SUNSET` sentinel in the narrow Config Center Flags view, not merely a changed image.
  Reproduce first; do not bulk-accept golden images.
- **Performance floors:** cached repeat rendering of view hints measured a 15.004 ms
  p50, above both the 12 ms absolute floor and the 12.758 ms relative ceiling. Repeat
  this benchmark on the final SHA and optimize if stable rather than immediately
  loosening the floor.
- **Contention:** the job received shutdown/SIGTERM after about 31 minutes and ended as
  an operation cancellation. That result is inconclusive infrastructure evidence, not
  a demonstrated code failure. Rerun it on a healthy runner.
- **Lint:** overlapped the file-size problem above.

Because the scheduled suite is the only place covering the cross-version matrix,
visual suite, performance floors, and contention behavior together, a release should
require a fresh run at the final candidate SHA. A green sharded Master Gate alone does
not exercise these lanes.

## Risk and sequencing observations

- Do not broaden SASE's core dependency range to an unpublished revision or remove the
  exact-floor smoke. That smoke caught the real packaging error: source-master tests
  can pass against a locally built core even though a clean PyPI installation cannot.
- Do not use the Publish workflow's `publish_existing=true` option to bypass the
  release PR. It is a recovery path for an already-created GitHub release whose PyPI
  upload was missed.
- PR #299 was based on an older master commit at the cutoff. Release-please should
  refresh/rebase its generated metadata after CI repairs; verify that its changelog,
  version, core window, and lock file reflect the actual final master.
- The newest master runs were still active during research. Start implementation by
  refreshing the run inventory; close items only on evidence from the newest SHA.

## Recommended solution

Run two repair tracks in parallel, then converge on one immutable release candidate:

1. **Unblock core 0.36.0.** Implement ancestor-aware canonicalization for nonexistent
   descendants on macOS; make managed-root storage explicitly canonical; pass the core
   checks on macOS and Linux; merge/refesh core PR #315; publish and verify
   `sase-core-rs==0.36.0` on PyPI.
2. **Make current SASE master green.** Refresh the latest Master Gate inventory. Land
   the low-risk contract/snapshot/schema/fixture repairs first, split both oversized
   modules, review the two marker-path audit additions, route every new display-time
   conversion through the shared time adapter, then diagnose the remaining TUI
   scroll/layout failures as behavior rather than snapshot drift. Use the normal
   `just check` recipe during repair; reserve `just check-full` for an explicit need.
3. **Prove the release candidate.** Require a green Master Gate on the final SHA, then
   manually dispatch or await a fresh scheduled Full CI on that same SHA. Require all
   Python versions, visual tests, performance floors, and a non-cancelled contention
   lane to pass. Treat stale or cancelled jobs as needing rerun, not as green evidence.
4. **Refresh and merge the release PR.** After core 0.36.0 is published, let
   `sync-release-metadata` ratchet PR #299 to `>=0.36.0,<0.37.0` and refresh its lock
   file/changelog against current master. Require the release PR's exact-floor smoke to
   install 0.36.0 successfully, then merge it.
5. **Publish and verify.** Let release-please create `v0.18.0`; let the Publish workflow
   build wheel and sdist, run both install smokes, and publish through PyPI trusted
   publishing. Finally verify the PyPI JSON metadata, artifacts, a clean-environment
   `pip install sase==0.18.0`, the installed version, and core health before declaring
   the release complete.
