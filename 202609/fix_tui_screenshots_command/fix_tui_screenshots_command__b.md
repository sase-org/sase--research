# Turning `just test-visual` into `just fix-tui-screenshots` — Research Report (Researcher B)

- **Date:** 2026-09-18
- **Question:** How should SASE replace the `just test-visual` gate with an auto-updating
  `just fix-tui-screenshots` command that runs from `just check-full` and explicit agent
  calls, and runs in check mode in CI? Is this a good idea, and what would I change?
- **Method:** I read the Justfile, the visual pytest harness (`tests/ace/tui/visual/`,
  `tests/pager/visual/`), `tools/run_pytest`, the CI workflows and their structural tests,
  `docs/development.md`, the relevant SASE memory and decision records, and the related
  beads. I measured golden churn and repository cost from git history. I pulled the
  job-level results for the last 60 scheduled Full CI runs and the full log of the most
  recent `visual-test` job. I did **not** run the visual suite locally: it needs the
  visual extra installed, and the host was at load average ~23 on 16 CPUs. The runtime
  numbers below come from CI.

---

## TL;DR

1. **The diagnosis is correct, and the data is stronger than "too much work."** The
   gate has already stopped working. `full / visual-test` failed in **60 of the last 60**
   scheduled Full CI runs (2026-09-05 → 2026-09-18). In the last 30 days, 162 commits
   touched PNG goldens. At least 21 of them were pure "rebaseline / refresh / repair"
   commits. Six commits each rewrote **340–623** of the 674 ACE goldens. An agent-enforced
   pixel gate is not being enforced in practice.
2. **Your plan is directionally right.** It follows the model every mature snapshot tool
   uses: an update command locally and a no-write check in CI. `just fix` is correctly
   left out.
3. **On its own, though, the plan leaves the core failure mode in place.** Keeping
   master fresh still depends on each agent deciding to run a command, and today's
   evidence says that often doesn't happen. With ~56 commits/day landing concurrently,
   even diligent agents invalidate each other's goldens. The most important addition is
   a **non-agent backstop**: a scheduled GitHub Actions "screenshot ratchet" that
   regenerates the goldens on master and pushes a golden-only commit carrying a
   human-readable change report. This also moves the regeneration cost off the host,
   which is the resource `decisions/two-speed-verification` says is scarce.
4. **Adjustments I recommend (details in §5):**
   - Split the command into `fix-tui-screenshots` (writes) and `lint-tui-screenshots`
     (check-only, for CI), rather than one command that behaves differently under CI.
   - In `check-full`, run the fixer only when the diff touches the TUI rendering surface.
   - Have `just check` print an advisory when that surface is touched.
   - The fixer must never "fix" a crash or a non-deterministic capture.
   - The report groups cascaded changes, so 600 identical header diffs read as one
     change.
5. **Longer term, the burden comes from test design, not the command.** 587 of the 674
   ACE goldens are full 120×40 screens. Every header, footer or keymap-hint change
   therefore rewrites hundreds of ~120 KB binaries. PNG goldens already make up
   **~1.6 GB of the repo's ~2.2 GB on-disk history**, with ~550 MB added in the last 30
   days alone. Auto-updating will speed that growth up. Follow-ups: crop snapshots to
   the component under test, and commit a small text sidecar per snapshot so git diffs
   say *what* changed.

---

## 1. How it works today

| Piece | Today |
| --- | --- |
| Recipes | `just test-visual` runs `tools/run_pytest visual` (marker `visual`, paths `tests/ace/tui/visual` and `tests/pager/visual`). `just update-visual-snapshots` runs `test-visual -- --sase-update-visual-snapshots`. `just test-visual-contention` is a diagnostic. |
| Update mechanics | `assert_png_matches()` in `tests/ace/tui/visual/png_diff.py`: when `update` is true it **writes the PNG unconditionally and returns**. No record is made of what changed, and no failure artifacts are written. In compare mode, a missing golden or a mismatch writes `expected/actual/diff/actual.svg/summary.txt/failure.json` under `.pytest_cache/sase-visual/<node>/<snapshot>/` and raises. |
| Safety rails | `renderer_env.json` pins renderer package versions and font hashes. Updates are refused on a skewed fingerprint or a non-Linux host. Fixtures pin `TERM`/`COLORTERM`/`TZ`, animations, the app version and several `local_now` clocks. Comparison is **byte/pixel exact**. |
| Corpus | 674 ACE goldens (80 MB, ~120 KB each, 1482×1026 RGBA for 120×40) plus 30 pager goldens. 961 tests are collected in the visual lane, including ~273 renderer/glyph/fingerprint tests that assert no golden. |
| `just fix` | `fmt-py fmt-docs fmt-md fix-keep-sorted`. Uses the narrow `.venv-format`, takes seconds, and does not install sase. |
| `just check` / `check-full` | All lint gates, then `test-scoped` or `test-cost`. **Neither runs the visual lane today.** Stages run under `tools/run_silent`, which discards output on success. |
| CI | The `visual-test` job in `ci.yml` runs on PRs and the scheduled Full CI (every 2 h via `full.yml`). On failure it builds an HTML/markdown report with `tools/render_visual_snapshot_failure_report` and uploads artifacts. The per-SHA Master Gate intentionally runs **no** visual lane (`decisions/ci-two-speed-split`). |
| Structural tests | `tests/test_github_actions_ci_workflow.py::test_visual_suite_runs_only_in_dedicated_job` asserts that the `visual-test` job runs `just test-visual`. `tests/test_github_actions_ci_master_gate.py` forbids `test-visual`/`visual-test` in the Master Gate. |
| Agent guidance | Only `sase/memory/lint_and_test.md` ("PNG Snapshot Tests") and `sase/memory/tui_screenshot.md` ("Implementation Rules"), plus `docs/development.md` and `src/sase/ace/tui/fonts/README.md`. No xprompt or skill mentions the visual lane. |
| Landing | Host finalizers stage with `git add -A` and then `git rebase --autostash origin/master` (`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`). The semantic conflict resolver cannot merge binary PNGs. |

## 2. Evidence that the current model has failed

**CI signal.** Across the last 60 Full CI runs, the per-job failure counts were:

| Job | Failed runs (of 60) |
| --- | --- |
| visual-test | **60** |
| contention-test | 59 |
| test (3.14) | 51 |
| test (3.12) | 49 |
| coverage-contexts | 48 |
| lint | 37 |
| perf-floors | 20 |

Full CI is broadly red, so fixing visuals alone will not turn it green. Still,
`visual-test` is the one job that never passes. In the most recent run (commit
`3077904f3e`) it reported **105 failed / 855 passed in 13 min**. The failures were
stale goldens, not flakes: 99 mismatches clustered on near-identical pixel counts (41
exactly `2756/1520532`, 13 at `2732`, 11 at `2745`). That is one chrome change fanned
out across ~100 screens. A follow-up commit today (`eaa1cbf4de`) rebaselined 131 PNGs.

**Standing beads.** `sase-x5` has been READY since 2026-09-05 as a residual stale-golden
backlog, linked to the earlier `sase-up` and `sase-r5` reports. Epic `sase-126` ("Restore
Master Gate and Full CI") devoted a whole phase to "repair visual fixtures and regenerate
reviewed goldens". A note on that epic then records a golden it had *just* repaired being
invalidated by a concurrent change (a new `(p)` view hint). This is the concurrency
problem in its plainest form. The phrase "PROPOSED FOLLOW-UP: refresh … visual goldens"
recurs across phase beads (`sase-zt.6.5.4.3`, `sase-zt.6.4`, and others).

**Churn and fan-out (last 30 days).**

- 1,675 commits landed on master (~56/day). 162 of them touched PNG goldens.
- 24 commits touched ≥20 PNGs. Six touched 340–623 PNGs each:
  - `e2229a6803` show usage windows in header: 623
  - `ecfde919c5` Refresh panel docs + goldens: 620
  - `fd626ec222` repair snapshot contracts: 606
  - `1f21c4b846` restore green CI for v0.17.0: 371
  - `eaf4ea8919` rebaseline: 357
  - `72f93fb1fb` stabilize visual closeout: 344
- 587 of 674 ACE goldens are full 120×40 screens, so each one includes the header,
  tab bar, usage badges and footer hints. Any change to those rewrites nearly the whole
  corpus.

**Repository cost.**

- 15,128 distinct golden PNG blobs since the suite started (2026-05-09): 1.86 GB raw,
  **1.62 GB on disk**.
- 5,035 of those blobs (552 MB on disk) were added in the last 30 days.
- PNGs of every kind account for **88% (1.91 of 2.17 GB)** of the reachable on-disk
  history.
- PNGs don't delta-compress. Re-encoding doesn't help either: PIL `optimize=True` made a
  40-golden sample *larger* (4.77 → 5.36 MB). Anti-aliased text produces up to 1,508
  colors, so a lossless 256-color palette isn't possible; lossy palettes break exact
  comparison.

**Runtime cost.** On the same GitHub runner type, `visual-test` takes 13.5 min against
35.8 min for `test (3.14)`, which runs the whole fast suite. Running the visual lane
unconditionally in `check-full` would add roughly **35–40%** to the most expensive
command agents run, on a host whose capacity is the binding constraint.

## 3. Critique of the plan

### What is right

- **Auto-update plus a CI check is the standard, proven shape.** Jest updates with
  `-u`, and under `--ci` (which defaults on when a CI environment is detected) it
  refuses to write new snapshots and fails instead. Rust's `insta` defaults to
  `INSTA_UPDATE=auto`, which writes pending `.snap.new` files locally but not on CI.
  `pytest-textual-snapshot` (the Textual ecosystem's own tool) uses an explicit
  `--snapshot-update`. These tool behaviors are from my knowledge of their docs; I did
  not re-verify them in this session. Your plan puts SASE in line with all of them.
- **Keeping it out of `just fix` is correct.** `fix` is a seconds-long,
  sase-install-free formatter pass. The screenshot lane needs the full app, the pinned
  renderer extra, ~960 tests and a suite-gate lease.
- **Keeping the tests at all is right.** Exact comparison is working as designed: the
  failures are real product changes, not renderer noise. The value of the suite is being
  lost to process, not to the technique.

### Concerns

1. **It keeps the accountability gap.** The plan changes *how cheap* it is to refresh
   goldens. It does not change *who is responsible* for master being fresh. That is
   still "every agent that might affect the TUI, judging for itself". Agents are already
   told to run `test-visual` and update goldens, and the 60/60 red record shows how that
   goes. On top of that, 56 concurrent landings/day mean agent A's refreshed goldens are
   invalidated by agent B's footer change an hour later (the `sase-126` note shows this
   exact race). Only something that runs *after* landing, on master, can keep master
   fresh. **This is the gap I would close first.**
2. **Auto-accepting turns a regression gate into a changelog. Say so explicitly.** Once
   `check-full` rewrites goldens and passes, an unintended visual regression is baked in
   silently. The only remaining defense is someone reading the change report: the agent
   in its own turn, or a human skimming history. That trade-off is reasonable given the
   evidence, but it makes the **quality of the report** the whole point. It also means
   the fixer must refuse to "fix" anything that isn't a clean, deterministic pixel
   change.
3. **`check-full` is a verifier.** Every other stage in it is check-mode (`fmt-py-check`,
   `lint-keep-sorted`, …). Making one stage mutate the tree is acceptable and pragmatic
   (host finalizers commit with `git add -A`, so new and updated PNGs ride along), but
   two consequences need design:
   - `tools/run_silent` swallows the stage's output on success, so the change report
     would be invisible unless it is printed outside the silent wrapper. The existing
     `print_scoped_summary` step shows the pattern.
   - The cost is roughly +35–40% per `check-full`, even for diffs that cannot affect the
     TUI. Gate it on the diff instead.
4. **"Lint" is the wrong mental model, and could cause a costly mistake.** This isn't
   static analysis; it runs ~960 app-driving tests. If it is filed as a lint, the
   natural next step is to add it to `just lint`. That would silently put a 13-minute
   visual lane into `just check` *and* into the Master Gate's `lint` job, which runs
   `just lint`. That would contradict `decisions/ci-two-speed-split`. It belongs with
   the repo's regenerate-a-committed-artifact recipes (`sync-completion-spec`,
   `refresh-contract-manifest`, `refresh-shard-timings`, `fix-keep-sorted` /
   `lint-keep-sorted`). The name `fix-tui-screenshots` fits that family well.
5. **"Behave differently in CI" should be explicit, not sniffed.** A single command that
   updates locally but checks under `CI=true` is how Jest and insta work, so it's
   defensible. In this repo, though, the workflow structure is itself under test, and
   every other check has an explicit check twin (`fmt-py` / `fmt-py-check`,
   `fix-keep-sorted` / `lint-keep-sorted`). An explicit `lint-tui-screenshots` in
   `ci.yml` is clearer, locally reproducible and assertable. Keep env detection only as
   a safety net: the fixer refuses to write when `GITHUB_ACTIONS=true`.
6. **Binary conflicts during landing.** Landing rebases onto a moving master. Two agents
   that both regenerated chrome-affected goldens will collide on PNGs that can't be
   merged, and the landing fails with "Resolve the conflict…". The more agents
   auto-update, the more often this happens. Since goldens are derived data, the right
   resolution is to keep upstream's copy and let regeneration (the ratchet) catch up.
   That rule is only safe once a backstop exists.
7. **Fixer semantics the plan leaves implicit.** Each of these matters once writes are
   automatic:
   - (a) Test *errors* (exceptions, convergence timeouts, hard content asserts such as
     the `sase-yu` node) must still fail.
   - (b) A capture that isn't deterministic must not be written. Otherwise flaky frames
     ping-pong through history (`sase-yv` passed on rerun).
   - (c) Byte-different but pixel-identical captures should not be rewritten.
   - (d) Goldens whose test was renamed or removed are never cleaned up today.
   - (e) Multi-snapshot tests stop at the first mismatch in check mode, so CI
     under-reports how much would change.
8. **Growth.** Each full-corpus refresh adds ~80 MB of unmergeable, non-delta-able
   history. Making refreshes routine without reducing fan-out means the repo keeps
   growing at ~0.5 GB/month or faster. That isn't urgent, because CI checkouts are
   shallow and workspaces share objects via alternates. It is the one cost that never
   comes back.

## 4. Alternatives considered

| Option | Verdict |
| --- | --- |
| **A. Your plan as stated** (fixer runs in `check-full` and on explicit agent call; CI fails when stale) | Good core. Master still drifts whenever an agent forgets or races, so CI stays red much as it is now. Needs a backstop. |
| **B. Bot-only**: agents never run the suite; a scheduled job rebaselines master | Zero agent burden, and host capacity is spared. But new-test authors never inspect their first golden, and nobody checks visually that their change looks right. |
| **C. A + B (recommended)** | Agents use the fixer when it adds value (new tests, intentional UI changes, broad changes caught by `check-full`). The ratchet guarantees freshness. CI check stays as the user wants but heals itself. |
| D. Add a pixel tolerance | Rejected. The failures are real changes with identical signatures, not renderer noise. Tolerance hides changes without reducing work. |
| E. Put it in the Master Gate or `just lint` | Rejected. It contradicts the two-speed CI decision and adds ~13 min per push. |
| F. Switch the committed goldens to SVG | Tempting because SVG is text, but Rich's `export_svg` prefixes every class with a content-hash id (`terminal-<adler32>`). Any content change therefore rewrites every line unless normalized, so diffs aren't readable either. Prefer a **plain-text sidecar** (below) and keep PNG for pixels. |
| G. Git LFS or a separate golden repo | Solves history growth but complicates atomic code+golden commits, workspace alternates and CI quotas. Revisit only if growth continues after the fan-out work. |
| H. Scoped visual selection per diff | Visual tests import the whole app and share chrome, so selection is effectively all-or-nothing. Use a yes/no "TUI impact" predicate instead of per-test selection. |

## 5. Adjusted requirements (my changes are marked **[ADJ]**)

- **R1. `just fix-tui-screenshots [pytest selectors]`** replaces `test-visual` and
  `update-visual-snapshots`. It covers both the ACE and pager visual suites. It creates
  missing goldens and updates changed ones. On a *full-corpus* run it **[ADJ]** also
  deletes orphaned goldens. It prints a change report.
  - Exit codes: 0 = done (changed or not); 1 = test errors or non-deterministic capture;
    2 = refused (renderer fingerprint skew or non-Linux host).
  - **[ADJ]** It refuses to write when `GITHUB_ACTIONS=true`, as a safety net.
- **R2. [ADJ] `just lint-tui-screenshots`** is the explicit check twin that CI runs. It
  runs the same lane without writing, then prints the same report plus the exact
  remediation.
  - Exit codes: 0 = fresh; 1 = would create, update or delete goldens; 3 = test errors.
    The separate code lets CI say "stale" vs "broken".
  - **[ADJ]** In check mode, snapshot mismatches are collected per test and raised at
    teardown (a soft assert). The report then counts *every* snapshot that would change,
    not just the first one per test.
- **R3. Not part of `just fix`.** (Unchanged; agreed.)
- **R4. `just check-full` runs `fix-tui-screenshots`, gated [ADJ].** It runs only when the
  diff touches the TUI rendering surface; otherwise it prints
  `✓ tui screenshots (skipped: no TUI-rendering changes)`.
  - The rendering surface is: the reverse-import closure from changed files reaches any
    visual test (reuse `tools/select_tests` with the visual exclusion lifted, at the same
    depth); or the diff touches fonts, `renderer_env.json`, the `visual` dependency
    group, visual conftest/helpers or `src/sase/default_config.yml`.
  - The change report is printed **outside** `run_silent`.
  - On non-Linux hosts it skips with a warning instead of failing.
- **R5. [ADJ] `just check` prints a one-line advisory** when the same predicate fires, for
  example: "TUI rendering files changed → run `just fix-tui-screenshots` and inspect the
  report." It runs no suite. This replaces "agents should remember" with a mechanical
  nudge at the moment agents already look.
- **R6. Agents run it explicitly** when they add or rename screenshot tests or
  intentionally change visuals. The guidance should require them to *look at* every
  **created** golden and the contact sheet (see §6.3).
- **R7. CI fails when goldens are stale.** (Unchanged in spirit.) It runs through
  `lint-tui-screenshots` in the existing `visual-test` job on PRs and Full CI, never in
  the Master Gate.
- **R8. [ADJ] Backstop: a scheduled screenshot ratchet** regenerates on master and
  pushes a golden-only commit whose body is the change report. This is what makes R7's
  red self-healing rather than permanent.
- **R9. [ADJ] Golden-only rebase conflicts** resolve by taking upstream's PNG during
  landing. The ratchet regenerates afterwards. Enable this only after R8 ships.

## 6. Design details

### 6.1 Harness changes (`tests/ace/tui/visual/`, `tests/pager/visual/`)

- **Update path in `assert_png_matches`:**
  - Read the old golden. If the PNG is **pixel-identical** (not just byte-identical),
    don't write.
  - Otherwise, **recapture once**: export and rasterize again from the same converged
    page. Write only if the two captures are byte-identical. If they differ, fail with
    "non-deterministic capture".
  - For every created or updated golden, write the same artifact set compare mode writes
    (expected, actual, diff), plus a `change.json` record: kind, pixel stats, changed
    bbox in pixels and in terminal cells, and a diff-mask hash used as the grouping
    signature.
- **Session plugin:**
  - Every xdist worker records the snapshot names it asserted.
  - The controller aggregates them at `pytest_sessionfinish`.
  - On a full-corpus run with no selectors or `-k`, it diffs the recorded names against
    the files on disk, deleting orphans in fix mode and reporting them in check mode.
- **Soft assert in check mode (R2):** collect mismatches per test and fail once at
  teardown.
- **Cell mapping:** convert the diff bbox into rows and columns using the SVG export's
  character width, line height and terminal offset. That gives "rows 38–39, cols 0–72
  (footer)" instead of raw pixels.

### 6.2 Report tool

Generalize `tools/render_visual_snapshot_failure_report` into a change-report renderer
that reads both `failure.json` and `change.json`. It already emits HTML, the GitHub
summary, annotations and a JSONL manifest. Add:

- **Grouping** by diff signature, so cascades collapse. In the CI run above, the 41
  goldens with an identical 2,756-pixel change would have been one line.
- **A contact sheet**: one PNG showing expected | actual | diff for the representative of
  each group, capped at ~8 groups. Agents can open it as a single image.
- **Created / deleted** sections, with created goldens flagged "inspect: never compared".

Example stdout:

```
TUI screenshots: 704 goldens · 12 updated · 1 created · 2 deleted · 689 unchanged

Updated (3 change groups):
  [A] 9 goldens · rows 38–39 cols 0–72 (footer)
      agents_list_120x40, agents_selected_row_120x40, … (+7)
  [B] 2 goldens · rows 4–11 cols 40–119
      agents_family_panel_level_1_120x40, agents_family_panel_member_roster_120x40
  [C] 1 golden  · rows 0–0 cols 90–119 (header)
      models_panel_usage_120x40
Created (inspect — never compared):
  services_tab_controls_120x40  ← test_ace_png_snapshots_services.py::test_services_tab
Deleted (no test references them):
  old_refresh_panel_120x40, old_refresh_panel_60x30

Contact sheet: .pytest_cache/sase-visual-report/contact_sheet.png
Full report:   .pytest_cache/sase-visual-report/visual-change-report.html
```

### 6.3 Justfile, CI and guidance

- **Justfile:**
  - Add `fix-tui-screenshots` and `lint-tui-screenshots`, both depending on
    `_setup-visual` and both driving `tools/run_pytest visual`.
  - Delete `update-visual-snapshots`.
  - Replace `test-visual` with a stub that prints the rename and exits 2 for one or two
    weeks, because bead notes and agent habit reference it.
  - Keep `test-visual-contention` as a diagnostic.
  - Add the gated `check-full` stage (R4) and the `check` advisory (R5).
- **`ci.yml`:**
  - The `visual-test` job runs `just lint-tui-screenshots`.
  - Keep the failure-report steps, retitled as a "stale screenshots" report with a
    remediation line.
  - Update `tests/test_github_actions_ci_workflow.py` and
    `tests/test_github_actions_ci_master_gate.py` for the new recipe names.
- **Ratchet workflow** (`.github/workflows/tui-screenshots-ratchet.yml`), modeled on
  `shard-timings-ratchet.yml`:
  - Schedule: cron every ~4–6 h, plus `workflow_dispatch`.
  - Runs `just install-visual`, then `just fix-tui-screenshots`.
  - If only paths under `tests/**/visual/snapshots/png/` changed, it commits with the
    markdown report as the body and pushes to master with `SASE_RELEASE_TOKEN`,
    rebasing and retrying once. If anything else changed, or tests errored, it fails
    loudly and commits nothing.
  - I recommend a **direct golden-only push over a PR**. At ~56 commits/day, a PR that
    waits for a human merge goes stale within hours; the path guard is the safety.
  - Cost: ~14 min of GitHub runner time per run, zero host capacity.
  - Determinism across hosts is already demonstrated: 855 host-generated goldens
    compare byte-exact on `ubuntu-latest`.
- **Agent guidance** (memory edits must go through `/sase_memory_write`):
  - Rewrite `lint_and_test.md` "PNG Snapshot Tests" and the last bullet of
    `tui_screenshot.md` around R1/R2/R6: when to run the fixer, how to read the report,
    and that created goldens and the contact sheet must be inspected.
  - Update `docs/development.md` (command list, runner note, "Visual Snapshot
    Workflow").
  - Update `src/sase/ace/tui/fonts/README.md`.

## 7. Risks and open questions

- **Silent regression acceptance** is the accepted cost of this design. It is mitigated,
  not eliminated, by agent inspection of reports, the ratchet commit body, and the
  optional text sidecars below.
- **The TUI-impact predicate can miss.** A deep core change can alter displayed text
  beyond the closure depth. Full CI's check and the ratchet catch it within hours. This
  is the same two-speed trade-off the repo already accepts for `test-scoped`.
- **Release gating.** `ci_watch` requires a recent green Full CI. A stale-golden red now
  heals within one ratchet cycle rather than blocking until someone volunteers. Full CI
  is also red for many non-visual reasons, so this change alone won't unblock releases.
- **Bot pushes to master** need `SASE_RELEASE_TOKEN` push rights, which the shard
  ratchet already relies on to push branches. They also need a path guard that is itself
  tested. Please confirm you're comfortable with a bot-authored commit on master; the
  fallback is PR + auto-merge.
- **Feature-flag policy.** These are dev recipes, not user-reaching behavior, so I don't
  think a flag bead is required. The implementing agent should still confirm against
  `sase_flags.md` before removing `test-visual`.

## 8. Recommended solution

Implement **Option C** as one epic with four phases, then a follow-up epic.

1. **Fixer core** (medium)
   - Harness semantics: pixel-equal skip, recapture-before-write, `change.json`, orphan
     pruning on full runs, soft asserts in check mode.
   - A generalized change-report tool with grouping and a contact sheet.
   - `just fix-tui-screenshots` / `just lint-tui-screenshots`; retire `test-visual` and
     `update-visual-snapshots` behind a rename stub.
   - `ci.yml`'s `visual-test` job switches to `lint-tui-screenshots`.
   - Workflow structure tests and `docs/development.md` updated.
2. **Agent integration** (medium)
   - A TUI-impact predicate built on `tools/select_tests`.
   - The gated `check-full` stage, with its report printed outside `run_silent`.
   - The `just check` advisory.
   - Memory updates via `/sase_memory_write`.
3. **Ratchet backstop** (small)
   - A scheduled GitHub Actions workflow that pushes golden-only commits with the report
     as the commit body, guarded by a path check.
4. **Landing conflict rule** (small, after phase 3)
   - Golden-only rebase conflicts resolve to upstream in the git commit dispatcher's
     semantic-conflict path.

**Follow-up epic: reduce the burden at its source.**

- Crop most snapshots to the widget or region under test, and keep a small set (~20) of
  full-screen chrome goldens. This removes the 300–600-file cascades and most of the
  history growth.
- Commit a small per-snapshot plain-text screen dump next to each PNG. Then
  `git log -p`, the report and reviewers can see *what* text changed; style-only changes
  are flagged as such.
- Revisit PNG storage (LFS or out-of-repo) only if history growth stays above
  ~0.5 GB/month after cropping.

**Why this and not the plan as written:** the plan fixes the effort of refreshing
goldens. The evidence says the bigger problem is *ownership* and *concurrency*: 60/60
red runs, and repairs invalidated within hours. A post-landing ratchet is the only
mechanism that addresses both, and it does so off-host. Everything else in the plan
stands, with the explicit check twin, the diff gate and the stricter fixer semantics
added to keep auto-accept honest.
