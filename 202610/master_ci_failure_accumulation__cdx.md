# Why `master` Is Red—and How to Keep It Green

**Independent CI investigation · 2026-10-01 · researcher `cdx`**

> **Bottom line:** this is not one mysterious CI or runner failure. `master` contains a growing set of real lint, collection, contract, and test regressions. They accumulate because the repository's comprehensive checks run *after* commits reach an unprotected `master`, while the normal local agent check runs only a diff-scoped test selection.

## What the evidence says

| Signal | Finding |
|---|---|
| Last green Master Gate | [`f90c6b549f6e`](https://github.com/sase-org/sase/actions/runs/35299164480), 2026-09-18 02:24 UTC |
| First subsequent red gate | [`5cb968c8cb30`](https://github.com/sase-org/sase/actions/runs/35300127953), 14 minutes later; a new screenshot test required the absent visual extra |
| Commits since last green | **1,107 first-parent commits** through `781063e38e9e` |
| Later green Master Gates | **None** as of 2026-10-01 14:31 UTC (GitHub's latest-success query still returns the September 18 run) |
| Latest completed gate | [`781063e38e9e`](https://github.com/sase-org/sase/actions/runs/36875333649): core build green; lint red; **7 of 8** test shards red |
| Scheduled exhaustive lane | [`3819d254b3fe`](https://github.com/sase-org/sase/actions/runs/36868405555): lint, all three Python test legs, slow/performance tests, and visual tests red |
| Repository enforcement | GitHub's branch-protection endpoint returns `404 Branch not protected`; the branch-rules endpoint returns `[]` |

The healthy core-wheel and docs jobs are useful controls: dependencies install, the pinned Rust core builds, and docs deploys complete. The red jobs fail on named source/test assertions and import errors, not on a broad GitHub outage.

## What is failing now

The latest Master Gate exposes several independent, mostly deterministic regressions:

1. **Static analysis:** Symvision reports three public symbols with no production caller: `HandoffSubmitResult`, `StarterResolution`, and `owner_ref`.
2. **Broken test-module facade:** `tests/ace/tui/widgets/test_agent_header_panel.py` still imports `test_hint_document_forces_expansion`, renamed on September 30 to tests for the new “remain collapsed in hint mode” behavior. This collection error also poisons the contract-manifest, slow, and visual lanes.
3. **New memory-history surface without its companion contracts:**
   - `memory history` was added, but the top-level parser-help expectation was not updated;
   - `memory/history:at` has no completion kind or free-form value hint;
   - read-log JSON gained `blob_oid` and `included_blob_oids`, but its exact-event test still expects the old shape.
4. **Launch API changed without updating callers' doubles:** `launch_agents_from_cwd(..., history_text=...)` now passes the new keyword everywhere, but force-reuse assertions and a partial-launch fake still model the old signature.
5. **Changed invariants without changed audits:** `quarantine_local_object` moves files but is absent from the reviewed destructive-operation inventory; home-mode marker bookkeeping now performs four index updates while its test still asserts three.
6. **Help/schema expectation drift:** the sidecar schema generalized the explicit agents path to `<role>`, and `--images` gained choices that alter argparse's rendered option string; their tests still assert the previous text.

The scheduled Full CI adds version- and timing-sensitive failures: a Python 3.14 import-startup budget overrun (`3491 < 3485`), several TUI wait timeouts, a slow tool-run smoke failure, and many visual failures. Two UI failures also appeared in one latest fast run but not its immediate predecessor, so those should be treated as suspected flakes until reproduced under the contention harness—not hidden by merely rerunning CI.

## Why this happened

### 1. The gate observes a broken `master`; it does not protect `master`

[`master-gate.yml`](https://github.com/sase-org/sase/blob/781063e38e9ec75832c0dc70c80a77d7169911f5/.github/workflows/master-gate.yml) triggers only on `push` to `master`. By definition, its verdict arrives after the commit is already canonical. GitHub has no protection rule, required status check, pull-request requirement, or merge queue to stop the next commit.

This explains the otherwise surprising timeline: the first regression turned the branch red, unrelated work kept landing, later changes added more failures, and fixes repaired some earlier symptoms without ever returning the whole branch to green. “Master Gate” currently means *post-land telemetry*, not a gate.

### 2. The pre-landing verification surface is intentionally narrower

The documented agent default, `just check`, runs whole-repository lint but only **diff-scoped** tests. `just check-full` is explicitly non-default. I cannot determine from GitHub logs which local command every agent ran, but GitHub proves there is no independent pre-merge whole-suite check. Either skipped checks or selector false negatives can therefore land; the many stale cross-cutting contract tests are characteristic selector blind spots.

The missed cases are predictable: parser/completion inventories, compatibility facade imports, audit allowlists, exact wire shapes, and mocks of shared call seams do not necessarily execute the line that changed. Coverage-based selection alone is weakest at exactly these structural contracts.

### 3. A red branch has no circuit breaker

The workflow deliberately runs every SHA in its own non-cancelled concurrency group. That is good attribution when commits are admitted carefully, but costly once the branch is red. There is no automatic hold that says “only CI-repair work may land until HEAD is green,” so high commit throughput turns one regression into a moving recovery target and burns eight test jobs per SHA.

## Recovery plan

1. **Freeze ordinary landing now.** Designate one recovery branch/agent and stop unrelated pushes until the current HEAD is green.
2. **Repair deterministic failures as one reviewed recovery change.** Preserve intended new behavior and update its contracts together:
   - remove `owner_ref`; make the two internal result types private (and update tests), unless they are intentionally supported public API;
   - update the header-panel compatibility facade to export the two replacement hint tests;
   - add a completion hint for `memory history --at`, update memory help and raw-event expectations, and explicitly document hidden sidecar paths if that remains a public promise;
   - update launch mocks/assertions for `history_text=None` and the new fake signature;
   - review and add `quarantine_local_object` to the destructive-operation inventory;
   - reconcile marker-update count and argparse help assertions with the intended contracts.
3. **Triage the remaining non-deterministic failures separately.** Reproduce TUI waits with the existing contention harness, fix semantic waits/state transitions, and only then update visual goldens. Do not bless goldens from a run whose collection or semantic wait failed.
4. **Prove the repaired HEAD.** Run the exact fast gate (`just lint` plus the complete non-visual suite), the Python 3.12/3.13/3.14 matrix, the visual check, and the slow/performance lane. Require two consecutive fast-gate passes and one Full CI pass before lifting the freeze.

## Prevention design

### Make “green before canonical” mechanically true

Protect `master` and require a pull request or merge queue. Because SASE's host owns commits, the host finalizer should push each stitch to a short-lived staging ref, open/enqueue it, and advance `master` only after required checks pass. At minimum require:

- lint/validation/build;
- the full fast test suite on supported Python versions;
- visual tests for TUI-affecting changes (or always, if classification is not trustworthy);
- conventional title and docs build where applicable.

If direct host pushes must temporarily remain, add a host-side admission rule that refuses a non-repair commit whenever the latest Master Gate for `origin/master` is not green. This circuit breaker does not prevent the first regression, but it prevents the next 1,106 commits from piling onto it.

### Strengthen the cheap local gate where selection is structurally blind

Keep diff-scoped tests for speed, but add a small always-run “structural contracts” bundle to `just check`:

- `pytest --collect-only` (catches stale test facades immediately);
- parser/help and completion-kind coverage;
- contract-manifest consistency;
- destructive-operation and other reviewed-site inventories;
- config/schema generation and exact wire-shape contracts.

Then use the existing selection-health/backtest machinery to ingest every Full CI miss, measure recall, and expand dependency rules. A successful scoped run should be evidence about the changed surface, never the only barrier protecting the repository.

### Make red state loud and operational

Send one actionable notification when HEAD first turns red, assign a repair owner, suppress duplicate noise by failure signature, and prevent deploy/publish workflows from consuming an unverified SHA. Track two service-level facts: age of the latest green HEAD and number of commits ahead of it. The latter should never again exceed one.

## Recommended solution

**First, freeze `master` and land one focused recovery change that clears every deterministic contract/lint failure, then fix or quarantine the reproduced timing failures until the exact Master Gate and Full CI are green. Immediately afterward, protect `master` with a staging-ref/PR merge queue whose required checks run before the host advances the branch, plus a red-HEAD circuit breaker and a small always-run structural-contract suite inside `just check`.** This addresses both the present symptoms and the actual systemic defect: today CI reports damage after landing; it must become an admission control.
