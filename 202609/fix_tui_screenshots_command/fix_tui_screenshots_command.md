# `just fix-tui-screenshots`: Consolidated Research Report

- **Date:** 2026-09-18 · **Repo state examined:** `sase` at `f7ea41d3b2`
- **Inputs:** Researcher A (`fix_tui_screenshots_command__a.md`), Researcher B
  (`fix_tui_screenshots_command__b.md`), plus my own verification of every load-bearing
  claim in the working tree, CI workflows, and live GitHub run history.
- **Question:** Should the visual screenshot suite move from `just test-visual` to an
  auto-updating `just fix-tui-screenshots` run by `check-full`, explicit agent calls,
  and (check-only) CI? Is the plan sound, and what should change?

## TL;DR

The plan is directionally right and both researchers independently converged on the
same industry-standard shape (update locally, check-only in CI — Jest, insta,
Playwright, pytest-textual-snapshot all work this way). The evidence for acting is
stronger than "too much work": **the gate has already failed.** B measured `visual-test`
red in 60 of the last 60 scheduled Full CI runs; I spot-verified the latest runs and the
per-job breakdown. With ~56 commits/day landing and 587 of 674 ACE goldens being full
120×40 screens, any chrome change fans out across hundreds of PNGs and concurrent
agents invalidate each other's refreshes within hours.

Three adjustments to the stated requirements are justified (details in §4):

1. **`just check-full` should check, not mutate.** Run the non-mutating twin from
   `check-full`; reserve the auto-updating form for explicit invocation. (Adjusts your
   requirement; both the SASE monitor workflow and the `git add -A` finalizer make a
   mutating background stage actively dangerous.)
2. **Ship two recipes, not one CI-sniffing command:** `fix-tui-screenshots` (writes) and
   `lint-tui-screenshots` (check twin for CI and `check-full`), matching the repo's
   existing `fix-keep-sorted`/`lint-keep-sorted` convention.
3. **Add a post-landing backstop** — a scheduled GitHub Actions "screenshot ratchet"
   that regenerates goldens on master and pushes a golden-only commit with a
   human-readable report. Without it, master freshness still depends on every agent
   remembering, which is precisely what the 60/60 record shows does not happen. Needs
   your sign-off on bot commits to master (§6).

Recommended solution and rollout are in §7. A follow-up epic to shrink the corpus
(cropping full-screen snapshots to components) is what actually reduces the burden
long-term (§8).

## 1. Verified current state

Everything below was re-verified by me at `f7ea41d3b2` unless attributed.

- **Commands.** `just test-visual` runs `tools/run_pytest visual` over
  `tests/ace/tui/visual` + `tests/pager/visual`; `just update-visual-snapshots` re-runs
  it with `--sase-update-visual-snapshots`. `just fix` is formatters only (`fmt-py
  fmt-docs fmt-md fix-keep-sorted`). Neither `just check` nor `just check-full` touches
  the visual lane today; `check` ends in diff-scoped `test-scoped`, `check-full` in the
  full-suite `test-cost`. Every `check`/`check-full` stage is a non-mutating check
  wrapped in `tools/run_silent`, which discards output on success; the
  `print_scoped_summary` step demonstrates the "print the report outside the silent
  wrapper" pattern the new stage will need.
- **Update mechanics.** `assert_png_matches()` in `tests/ace/tui/visual/png_diff.py`
  with `update=True` is literally `write_bytes(...); return` — no comparison, no record
  of what changed, no failure artifacts, immediate per-test writes (so an interrupted
  run leaves a partially regenerated corpus). Compare mode writes rich
  expected/actual/diff/SVG/JSON artifacts and raises on first mismatch, so a
  multi-snapshot test under-reports drift. The pager suite reuses the same fixture.
- **Determinism rails.** Pinned renderer packages and font hashes
  (`renderer_env.json`), Linux-only update guard, pinned TERM/TZ/clocks. Comparison is
  **exact by default everywhere, including CI**: no workflow sets any
  `SASE_VISUAL_PNG_*` tolerance env, and `git log -S` shows none ever did. The
  `lint_and_test.md` claim that CI allows a ratio-only drift tolerance is stale —
  already tracked as ready task bead `sase-sl`, which I corroborated (+1) this turn.
- **Corpus.** 704 goldens (674 ACE + 30 pager), ~80 MB, ~120 KB each; 587 of the ACE
  goldens are full 120×40 screens including header/tab-bar/footer chrome.
- **Churn** (researchers' git-history measurements, windows differ but agree): A —
  since 2026-07-01, 710 of 5,105 commits (13.9%) touched golden PNGs, 14,914 PNG
  touches, median 3/commit, p90 ≈ 26, max 623. B — last 30 days: 162 of 1,675 commits
  touched goldens; six commits each rewrote 340–623 goldens (renderer/chrome changes).
- **History cost** (B): PNG blobs are ~1.6 GB of the repo's ~2.2 GB on-disk history,
  ~550 MB added in 30 days. PNGs neither delta-compress nor re-encode smaller.
- **CI.** `ci.yml` runs on `pull_request` and via `workflow_call` from `full.yml`
  (scheduled every 2 h). The dedicated `visual-test` job runs bare `just test-visual`
  (13.5 min on GitHub runners) and on failure builds/uploads an HTML report, job
  summary, and annotations via `tools/render_visual_snapshot_failure_report`. The
  per-SHA Master Gate intentionally excludes the visual lane
  (`decisions/ci-two-speed-split`). Verified live: the last completed Full CI runs are
  all `failure`, with `full / visual-test: failure` in the latest (105 stale-golden
  failures clustered on identical pixel signatures — real drift, not flakes). B's
  60/60-red measurement stands.
- **Structural tests.** `tests/test_github_actions_ci_workflow.py` asserts the
  `visual-test` job runs `just test-visual`; `tests/test_github_actions_ci_master_gate.py`
  forbids it in the Master Gate. Both must move with any rename.
- **Landing.** Host finalizers stage `git add -A`, then
  `git rebase --autostash origin/master` with a semantic conflict resolver that cannot
  merge binary PNGs (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`,
  verified). Concurrent golden refreshes therefore collide unmergeably.
- **Precedent for a ratchet.** `.github/workflows/shard-timings-ratchet.yml` exists:
  weekly cron, `SASE_RELEASE_TOKEN`, commits a refresh — but note it pushes a
  **branch**, not master directly. B's proposed direct master push goes one step beyond
  the existing precedent.

## 2. Critique of the plan

**What is right (unanimous):**

- Removing the visual lane from every agent's routine path. `just fix` is a
  seconds-long, install-free formatter pass; a 13-minute, visual-extra-dependent,
  ~960-test render lane does not belong there or in default `check`.
- Treating goldens as generated artifacts with an auto-materializing refresh command.
  Hand-copying hundreds of binaries is zero-value work, and the current update flag
  already auto-creates/overwrites — just blindly (§1).
- A non-mutating CI check that fails on drift. Every mature snapshot tool separates
  update from check.
- Keeping the tests. The failures are real product changes caught exactly as designed;
  the technique works, the process around it failed.

**Corrections both reports argue for, which I endorse:**

- **"Lint" is the wrong mental model** (B). This is not static analysis; it renders
  ~960 app-driving scenes. Filed as a lint, someone eventually adds it to `just lint` —
  which would silently drag 13 minutes into `just check` *and* the Master Gate's lint
  job, violating `decisions/ci-two-speed-split`. It belongs in the
  regenerate-a-committed-artifact family (`refresh-shard-timings`,
  `sync-completion-spec`, `fix-keep-sorted`). The `fix-*` name fits; do not wire it
  into `lint`.
- **Renaming does not by itself reduce enforcement** (A). If CI still fails on stale
  goldens, whoever lands the change still owes the update. The real wins are: one run
  that collects *every* change instead of stopping at the first mismatch; aggregate,
  reviewable output; transactional safe apply; stale-golden cleanup; and the backstop.
- **Auto-update is not auto-approval** (A). Snapshot value comes from someone judging
  the new image. The command may materialize files, but the report must make review
  easy and agent guidance must require inspecting it. Once updates are automatic, the
  report's quality is the whole point (B).
- **Stale goldens are drift too** (both). Deleting/renaming a test currently orphans
  its PNG forever. The command must report and (in fix mode, on full runs) remove
  orphans — the third leg alongside add and update.

## 3. Resolved disagreements

**(a) Should `check-full` mutate? — No (A wins, with B's cost gating).** This was the
sharpest conflict: A says `check-full` must stay non-mutating; B accepts a mutating,
diff-gated stage. I side with A, decisively, on repo-specific grounds: agents are
*required* to run `check-full` through `/sase_monitor` (it outruns a turn), and host
finalizers stage with `git add -A`. A mutating stage in a background monitor run means
hundreds of regenerated binaries get committed with **no agent ever seeing the
report** — which destroys the one safeguard (inspection) that makes auto-update
tolerable, and B's own requirement R6 (inspect every created golden) becomes
unsatisfiable. It also makes "check" non-reproducible and converts visual regressions
into passing runs. B's cost point survives, though: adding a 13.5-min lane
(+35–40% of `check-full`) unconditionally on a capacity-constrained host
(`decisions/two-speed-verification`) is wasteful for diffs that cannot affect pixels.
So: `check-full` runs the **check twin**, gated on a TUI-impact predicate
(reverse-import closure via `tools/select_tests` with the visual exclusion lifted, plus
fonts/`renderer_env.json`/visual-extra/conftest/`default_config.yml` paths), printing
`✓ tui screenshots (skipped: no TUI-rendering changes)` otherwise, with the drift
report printed outside `run_silent` and an exact remediation line
(`run: just fix-tui-screenshots, then inspect the report`).

**(b) One command with `--check`, or twin recipes? — Twin recipes (B wins).** A wanted
`fix-tui-screenshots --check` as canonical; B wanted an explicit `lint-tui-screenshots`
twin. The repo convention is unambiguous (`fmt-py`/`fmt-py-check`,
`fix-keep-sorted`/`lint-keep-sorted`), the workflow-structure tests assert exact recipe
strings, and every `check-full` stage is already a named check twin. Both agree on the
safety net both ways: the fix form refuses to write when `GITHUB_ACTIONS=true`; CI
never relies on env sniffing and always invokes the lint twin explicitly.

**(c) The ratchet backstop — adopt it (B's key contribution), with eyes open.** A's
design implicitly assumes the landing agent keeps master fresh; the 60/60 record and
the `sase-126` epic note (a just-repaired golden invalidated hours later by a
concurrent chrome change) show that model failing *today*, and A's own §"what does not
actually reduce enforcement" concedes the obligation doesn't move. Only something that
runs after landing, on master, closes the ownership/concurrency gap — and it moves the
regeneration cost onto free GitHub runners instead of the constrained host. Caveats I
add from verification: the existing shard-timings precedent pushes a branch, not
master, so B's direct-push design is a genuine policy extension needing Bryan's
explicit sign-off (fallback: PR + auto-merge; B argues PRs staled-by-volume, which is
fair at 56 commits/day but auto-merge mitigates it). The ratchet also is the moment the
visual lane fully converts from *gate* to *monitored changelog*: an unnoticed
regression becomes the new golden within one cycle, with the grouped commit-body report
as the only record. That is consistent with your stated goal, but it should be a
conscious choice, not a side effect. Guardrails: golden-only path guard (itself
tested), refuse on any test error, fail loudly on non-golden changes, `workflow_dispatch`
for manual runs.

**(d) Selectors on the fix command? — Allow them; orphan-prune only on full runs.** A
banned selectors in v1 (partial runs can't identify stale goldens); B allowed them. B's
form is right — an agent adding one snapshot test shouldn't pay 13 minutes — and A's
concern is fully addressed by restricting orphan detection/pruning to unselected full
runs.

**(e) Architecture: A's transaction + B's semantics — complementary, take both.** A
contributes the *shape*: a collection mode where fixtures write candidate PNGs +
manifest records to scratch space instead of comparing/writing goldens; the wrapper
compares the complete candidate inventory against both golden roots only after pytest
exits successfully, then applies add/update/remove atomically — so a mid-run crash
leaves the committed corpus byte-identical (today's update mode cannot promise this).
B contributes the *per-snapshot rules*: skip pixel-identical (not merely
byte-identical) captures; recapture once and refuse to write a non-deterministic frame;
never "fix" a test error or convergence timeout; emit a `change.json` (kind, pixel
stats, changed bbox in pixels *and terminal cells*, diff-mask hash) per change; collect
snapshot mismatches per test (soft assert) in check mode so drift is counted fully.

## 4. Requirement adjustments, called out explicitly

| # | Your requirement | Adjustment | Why |
|---|---|---|---|
| 1 | Not in `just fix` | **Kept as stated.** | Unanimous; cost/dependency mismatch. |
| 2 | Runs (mutating) in `check-full` | **Changed: `check-full` runs the non-mutating twin, diff-gated; only explicit invocations mutate.** | Monitor + `git add -A` finalizer would commit unreviewed binaries; verification stays reproducible (§3a). |
| 3 | Agents run it explicitly when they expect screenshot impact | **Kept**, plus a mechanical nudge: `just check` (and the gated `check-full` stage) print an advisory naming the exact command when the TUI-impact predicate fires. | "Remember to run it" is the part that demonstrably fails; put the nudge where agents already look. |
| 4 | One command | **Changed: `fix-tui-screenshots` + `lint-tui-screenshots` twins.** | Repo convention; structural tests assert recipe strings; no CI env-sniffing (§3b). |
| 5 | CI runs it and fails on needed updates | **Kept** (`visual-test` job → `just lint-tui-screenshots`), **plus** the scheduled ratchet so red heals within hours instead of standing forever. | Ownership/concurrency gap is the actual cause of today's permanent red (§3c). |
| 6 | Auto-create/update with good descriptive output | **Kept and extended: also detect/remove stale goldens; output must group cascades.** | One chrome change = hundreds of identical diffs; ungrouped output is unreadable (§5). |

## 5. Recommended command contract

- `just fix-tui-screenshots [selectors]` — full ACE+pager corpus by default; collects
  all candidates transactionally (§3e), then applies adds/updates/(full-run-only)
  removals atomically and prints the change report. Refuses on renderer-fingerprint
  skew, non-Linux host, or `GITHUB_ACTIONS=true`.
- `just lint-tui-screenshots` — same render and comparison, never writes; prints the
  same report plus the remediation command; retains changed candidate/diff artifacts.
- Shared exit codes: `0` fresh/applied · `1` drift (lint only) · `2` refused
  environment · `3` test/render execution failure. Distinct codes let CI and
  `check-full` say "stale" vs. "broken".
- **Report** (both modes; B's grouped format, backed by A's manifest requirements):
  one summary line (`704 goldens · 12 updated · 1 created · 2 deleted · 689
  unchanged`), then change **groups** keyed by diff-mask signature with terminal-cell
  regions (`[A] 9 goldens · rows 38–39 cols 0–72 (footer)`), a "Created (inspect —
  never compared)" section, a "Deleted (no test references them)" section, a contact
  sheet PNG (expected|actual|diff per group representative), a self-contained HTML
  report, and a JSONL manifest. Cap console listing for mass refreshes; report
  pre-existing dirty golden paths separately so the command never claims another
  change's diff as its own. Generalize `tools/render_visual_snapshot_failure_report`
  from "failure" to "change" (kinds `added`/`updated`/`stale`) rather than forking a
  second report pipeline; CI keeps uploading it.

## 6. Implementation and rollout

Phased epic (B's structure, incorporating A's transaction work and test list):

1. **Fixer core (medium).** Collection protocol + manifest records in
   `tests/ace/tui/visual/` (shared by pager); pixel-equal skip, recapture-once
   determinism check, `change.json`; soft-assert check mode; orphan inventory;
   transactional apply in a new `tools/fix_tui_screenshots`; generalized change-report
   tool with grouping + contact sheet; `fix-tui-screenshots`/`lint-tui-screenshots`
   recipes; `visual-test` job switches to `just lint-tui-screenshots` (keep the job id
   for branch protection); structural tests updated; `test-visual` becomes a
   short-lived stub pointing at the new names; `update-visual-snapshots` and
   `--sase-update-visual-snapshots` retired after transition; `test-visual-contention`
   kept as a diagnostic. Focused orchestration tests independent of the corpus (A's
   list): clean/missing/mismatched/stale cases in both modes, mid-run failure leaves
   goldens byte-identical, duplicate canonical path fails, path-escape rejected,
   non-Linux/fingerprint/CI refusals, report correctness, check mode leaves
   `git status` of golden roots unchanged.
2. **Agent integration (medium).** TUI-impact predicate on `tools/select_tests`; gated
   `check-full` stage (report outside `run_silent`); `just check` advisory line;
   rewrite `lint_and_test.md` PNG section (fixes `sase-sl` en passant) and
   `tui_screenshot.md` guidance via `/sase_memory_write`; update
   `docs/development.md` and the fonts README. Agent rule (A's wording, trimmed): run
   `just fix-tui-screenshots` after changes expected to alter rendered
   layout/styling/chrome/theme behavior or after adding/renaming/removing a snapshot
   assertion; inspect every reported add/update/removal (or the report/contact sheet)
   before finishing; `check-full` and CI check but never accept.
3. **Ratchet backstop (small; needs sign-off).** Scheduled workflow (~4–6 h cadence +
   `workflow_dispatch`) modeled on `shard-timings-ratchet.yml`: `install-visual`,
   `fix-tui-screenshots`, commit golden-only changes with the markdown report as body,
   push with `SASE_RELEASE_TOKEN` (direct or PR+auto-merge per your call), rebase-retry
   once, fail loudly otherwise. ~14 min GitHub runner time, zero host load;
   cross-host byte-exactness is already demonstrated by CI.
4. **Landing conflict rule (small, only after 3).** Golden-only rebase conflicts in the
   finalizer resolve to upstream's PNG; the ratchet regenerates afterward. Unsafe
   before the backstop exists.

Rollout checks between phases (A): run old and new check modes on one revision and
require identical drift detection; exercise add/update/delete/fingerprint-skew/mid-run
failure on a controlled branch before switching CI.

Not a feature-flag matter (dev recipes, not user-reaching behavior), but the
implementing agent should confirm against `sase_flags.md` before deleting `test-visual`.

## 7. Recommended solution

Yes — do it, with the adjustments of §4. Concretely: build transactional
`fix-tui-screenshots` + `lint-tui-screenshots` twins with grouped, cell-aware change
reporting and stale-golden handling; point the existing `visual-test` CI job and a new
diff-gated `check-full` stage at the **lint** twin; reserve the **fix** twin for
explicit agent/human runs prompted by judgment plus the mechanical `check` advisory;
and add the scheduled ratchet so master heals itself instead of depending on 56
commits/day of perfect agent discipline. The one decision only you can make is the
ratchet's push mode (direct bot commit to master vs. PR + auto-merge) — the rest is
engineering.

Be explicit with yourself about the trade: with auto-update plus a ratchet, the visual
suite stops being a blocking gate and becomes a well-instrumented changelog with
inspection points (agent reports, commit bodies, PR CI). Given that the "gate" has been
red for its entire recent history while still costing rebaseline commits weekly, that
trade is worth it.

## 8. The real fix is smaller blast radius (follow-up epic)

The command redesign fixes mechanics, not the fan-out that creates the work: 587 of 674
ACE goldens are full screens sharing header/footer chrome, so one hint change rewrites
hundreds of ~120 KB unmergeable binaries and history grows ~0.5 GB/month. After the
workflow lands: crop most snapshots to the component under test, keeping ~20
full-screen chrome goldens; prune high-churn, low-information snapshots toward semantic
assertions (A's heuristics: text-only diffs already asserted elsewhere, combinatorial
theme/viewport matrices, tests whose real contract is state/keys); optionally commit a
small plain-text screen dump beside each PNG so `git log -p` shows *what* changed.
Revisit LFS/out-of-repo storage or an SVG-golden hybrid only if growth persists after
cropping — B verified SVG diffs are unreadable anyway (Rich's content-hashed class
ids), and A notes migrating formats would discard the deterministic PNG renderer
investment.
