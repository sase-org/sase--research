# Turning TUI Screenshot Tests into a Safe Generated-Artifact Lint

Date: 2026-09-18  
Repository state examined: `sase` at `c2befdbb3e`

## Executive conclusion

The proposed direction is good, with one important correction: expose screenshot
maintenance as a generated-artifact fixer, but do **not** let `just check-full`
silently accept new visual output. `check-full` and CI should run the same command in
an explicit, non-mutating `--check` mode. Agents should run the updating form
explicitly when they expect a pixel-visible change or add a screenshot case.

Recommended interface:

```text
just fix-tui-screenshots          # render the full corpus, report, then apply changes
just fix-tui-screenshots --check  # render and report, never write goldens; fail on drift
```

`just check-full` should invoke `just fix-tui-screenshots --check`; the dedicated CI
job should do the same. Neither `just fix` nor ordinary `just check` should invoke it.
The updater should be transactional: render all candidates into scratch space, compare
and build a report, and update the committed corpus only if the entire visual run
succeeds. It should handle additions, modifications, **and stale/deleted goldens**.

This preserves the useful regression gate while making the maintenance operation
one-shot and legible. It also avoids turning an exhaustive verification command into a
snapshot-approval command.

## What exists today

The requested behavior is closer to the current system than the command names imply:

- `just test-visual` runs the visual subset through `tools/run_pytest visual`.
- `just update-visual-snapshots` reruns that subset with
  `--sase-update-visual-snapshots`, which already creates missing PNGs and overwrites
  changed PNGs.
- The visual suite is excluded before collection from `just test`, `just test-cov`,
  and `just test-scoped`.
- `just fix`, `just check`, and `just check-full` currently do not run the visual
  suite.
- CI already has a dedicated Linux/Python 3.12 `visual-test` job. On failure it
  publishes expected/actual/diff PNGs, SVG source, structured JSON, an HTML report,
  GitHub annotations, and a job-summary table.
- The renderer is unusually well controlled: exact-pinned packages, bundled fonts,
  a committed renderer fingerprint, fixed terminal/color/time environment, and a
  Linux-only update guard. Exact equality is the default.

The main gaps are therefore not basic rendering or CI diagnostics. They are command
semantics, update reporting, transactional safety, orphan cleanup, and agent guidance.

### Scale and churn

At the examined revision:

- There are 704 committed PNG goldens, about 82 MiB across the ACE and pager visual
  trees.
- The two visual trees contain 159 `test_*.py` files and roughly 602 literal
  `assert_page_png`/`assert_png` call sites; loops and parametrization account for the
  larger runtime corpus.
- From 2026-07-01 through the examined revision, 710 of 5,105 commits (13.9%) touched
  at least one screenshot PNG.
- Those commits account for 14,914 PNG file touches. The median was 3 PNGs per commit,
  the approximate 90th percentile was 26, and the maximum was 623.
- Several renderer or shared-chrome changes refreshed 396-623 images in a single
  commit.

These measurements support the complaint: screenshot upkeep is a material workflow
cost, not an occasional edge case. They also make unconditional acceptance dangerous:
one subtle global change can rewrite most of the corpus.

## Critique of the plan

### What is sound

1. **Removing screenshots from the routine agent path is appropriate.** A PNG render
   lane with optional dependencies and hundreds of scenes does not belong in `just
   fix` or the default diff-scoped `just check`.
2. **Treating goldens as generated artifacts is a clearer user model.** The public
   operation is “make the checked-in screenshot corpus agree with the current UI,”
   even though pytest remains a sensible internal execution engine.
3. **Keeping a non-mutating CI gate is essential.** Otherwise a missing or stale
   golden becomes invisible.
4. **Automatic creation and replacement is reasonable after a complete successful
   render.** Manually copying hundreds of binaries is low-value work.
5. **Putting a screenshot check in `check-full` matches the meaning of exhaustive
   verification**, provided that it checks rather than approves.

### What does not actually reduce enforcement

If CI still fails whenever a golden is stale, the contributor or agent that wants to
land the change still has to update the corpus. Renaming the lane from “test” to “lint”
does not remove that obligation. The real gains come from:

- one command that collects every change instead of stopping at the first mismatch in
  a test;
- actionable aggregate output;
- safe automatic application;
- running it only for likely visual work and exhaustive verification; and
- reducing redundant snapshot coverage over time.

This distinction matters because the plan otherwise risks promising a maintenance
reduction while mostly moving the same work to a differently named command.

### Automatic update is not automatic approval

Snapshot tests derive their value from someone deciding whether the new image is
correct. Textual's own guidance says to inspect the generated report before updating
and warns that update mode establishes the new ground truth. Its CI recommendation is
to export the HTML comparison report as an artifact. [Textual testing guide](https://textual.textualize.io/guide/testing/#snapshot-testing)

Playwright makes the same separation: an absent golden is written for inspection but
the first run fails; updates require `--update-snapshots`; and changed snapshots should
be committed and reviewed. [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)

Therefore the command may automatically **materialize** accepted files, but its output
must make review easy, and the instructions should still require inspection of changed
images or the visual report.

### `check-full` should remain non-mutating

Making bare `just check-full` rewrite goldens would have three bad effects:

1. A visual regression would be converted into a passing verification result.
2. SASE agents normally hand the long `check-full` run to a monitor. A background
   verification run could then alter and eventually commit hundreds of binaries with
   no agent examining them.
3. “Check” would cease to be reproducible: its exit status and worktree effect would
   depend on whether generated output happened to drift.

**Justified requirement adjustment:** run `fix-tui-screenshots --check` from
`check-full`; reserve the mutating default for an explicit agent/human invocation. If a
single command name is a hard requirement, the mode flag preserves it. If automatic
update during a broader workflow is still desired, give that workflow a mutating name
such as `fix-and-check-full` rather than changing `check-full`'s contract.

### Stale goldens are part of drift

The stated requirements mention create/update but not deletion. Removing or renaming a
snapshot assertion currently can leave an unreferenced PNG forever. A generated-corpus
lint should report all three set differences:

- candidate only: add;
- both, different bytes: update;
- committed only: stale/remove.

Insta offers a useful precedent: its unreferenced-snapshot `auto` mode deletes locally
and rejects in CI, but it warns that this is safe only after running the full test set.
[Insta CLI documentation](https://insta.rs/docs/cli/#test) The new command should
likewise always own the complete visual corpus when orphan detection is enabled.

## Recommended command contract

### Local update mode

`just fix-tui-screenshots` should:

1. Require the canonical pinned visual environment and Linux, as update mode already
   does.
2. Run the complete ACE and pager visual corpus. Do not offer arbitrary pytest
   selectors in the first version; partial runs cannot safely identify stale goldens.
3. Collect every rendered candidate without failing early merely because a snapshot is
   missing or different.
4. Abort without touching committed PNGs if collection, rendering, convergence, or any
   non-snapshot assertion fails.
5. Compare the complete candidate inventory with both committed golden roots.
6. Generate human-readable and machine-readable reports.
7. Atomically add, update, and remove goldens only after all prior steps succeed.
8. Exit zero after a successful apply, whether it changed zero or many files.

The default should refuse to update when a recognized CI environment is present unless
an explicit override is supplied. CI should never depend on that heuristic; it should
always pass `--check` explicitly.

### Check mode

`just fix-tui-screenshots --check` should perform the same render and comparison but
never modify the golden roots. It should:

- exit 0 when the corpus is current;
- exit 1 when additions, updates, or removals are needed;
- use a distinct nonzero exit for setup or test-execution failure if practical;
- print the exact local remediation command; and
- retain changed candidate/diff artifacts for inspection.

An optional `just check-tui-screenshots` alias can improve discoverability, but the
requested `fix-tui-screenshots --check` form should be the canonical path used by
`check-full` and CI.

### Output

Successful local output should be concise but specific, for example:

```text
TUI screenshots: 704 rendered; 698 unchanged; 4 updated; 1 added; 1 stale
 U tests/ace/tui/visual/snapshots/png/agents_list_120x40.png
   3,182 / 768,000 pixels changed (0.414323%); 1,104 material pixels
 A tests/pager/visual/snapshots/png/pager_search_100x30.png
 D tests/ace/tui/visual/snapshots/png/old_panel_120x40.png
report=.pytest_cache/sase-visual-report/visual-snapshot-changes.html
manifest=.pytest_cache/sase-visual-report/manifest.jsonl
```

For a large renderer-wide refresh, cap the console list and point to the complete
manifest/report. Report pre-existing dirty golden paths separately so the command never
misrepresents all final `git diff` entries as changes created by this invocation.

The existing HTML report and JSON sidecars are a strong base. Generalize their model
from “failure” to “change” with kinds `added`, `updated`, and `stale`; keep expected,
actual, diff, source SVG, test node/location, dimensions, exact changed-pixel counts,
and material-pixel counts. In CI, continue publishing the self-contained HTML report,
job-summary table, annotations, and raw artifacts.

## Transactional implementation

The tempting minimal implementation is to run current pytest update mode and then show
`git diff --stat`. I would not recommend stopping there:

- update mode currently writes each golden immediately and returns without comparing
  it, so it cannot report what changed;
- a test failure halfway through leaves a partially regenerated corpus;
- binary `git diff --stat` does not explain the visual magnitude;
- the current assertion raises on mismatch in check mode, so a test containing several
  screenshots may stop before later candidates are rendered; and
- no current mechanism identifies stale goldens.

Instead, add a collection mode beneath the public command.

### Collection protocol

1. The wrapper allocates a run-specific directory under
   `.pytest_cache/sase-visual-candidates/` and invokes the existing visual pytest mode
   with a private candidate-directory option.
2. `AcePngSnapshotFixture` renders exactly as today, but collection mode writes the
   candidate PNG plus a small manifest record instead of comparing against or writing
   the committed golden. The pager fixture uses the same protocol.
3. Each record includes a corpus identifier, canonical repo-relative golden path,
   snapshot name, node id, test source location, PNG hash, dimensions, and optional SVG
   path. Paths rather than bare snapshot names are the global identity, because ACE and
   pager have separate roots.
4. Records are xdist-safe. Duplicate writes to one canonical path from different test
   nodes are an error, even if the bytes happen to match; otherwise future changes are
   ambiguous.
5. Pytest mismatches never interrupt collection, but ordinary test/assertion failures
   still fail the run. This mirrors Insta's ability to force snapshot assertions to
   pass long enough to collect a complete review set. [Insta advanced snapshot workflow](https://insta.rs/docs/advanced/#disabling-assertion-failure)
6. Only after pytest exits successfully does the parent comparator inventory committed
   PNGs, compare bytes/pixels, detect unreferenced files, and write reports.
7. Check mode stops there and returns based on drift. Update mode applies the computed
   plan with atomic file replacement and deletion limited to the two resolved golden
   roots.
8. Remove unchanged candidates after comparison and keep only changed artifacts (or
   clear the whole candidate run on a clean result) so many concurrent SASE workspaces
   do not each retain another permanent ~82 MiB corpus.

This collector can coexist temporarily with the current assertion mode, which is useful
for unit tests and a compatibility alias. Once the new path is proven, retire
`--sase-update-visual-snapshots` and `update-visual-snapshots` rather than maintaining
two acceptance mechanisms.

### Likely code/documentation changes

- `Justfile`
  - add `fix-tui-screenshots *args` with `_setup-visual`;
  - invoke `fix-tui-screenshots --check` from `check-full`, not `check` or `fix`;
  - remove or temporarily deprecate `test-visual` and
    `update-visual-snapshots` as public workflows;
  - retain the contention recipe as an explicitly diagnostic test harness.
- `tools/fix_tui_screenshots` (new)
  - own argument parsing, candidate-run lifecycle, pytest invocation, inventory,
    comparison, report generation, transactional apply, and exit codes.
- `tests/conftest.py`, the ACE/pager visual `conftest.py` files, and
  `tests/ace/tui/visual/png_diff.py`
  - add the private collection protocol and manifest records while preserving the
    renderer and convergence checks.
- `tools/render_visual_snapshot_failure_report`
  - either generalize it to both failures and planned changes or extract shared report
    rendering. Do not fork a second HTML/annotation implementation.
- `.github/workflows/ci.yml`
  - change the dedicated job's command to `just fix-tui-screenshots --check`;
  - keep the existing job id initially if branch protection may name `visual-test`;
  - keep uploads under `if: failure()` and publish the generalized report.
- Contract tests
  - update Justfile dry-run tests and CI workflow tests so visual work is present only
    in `check-full`/the dedicated job, never routine test/check/fix lanes.
- `docs/development.md`, `sase/memory/lint_and_test.md`, and
  `sase/memory/tui_screenshot.md`
  - document the new public contract and tell agents when to run it. Memory edits must
    follow the project's memory-write procedure and regenerate provider instructions.

### Required focused tests

The orchestration deserves tests independent of the expensive visual corpus:

- clean corpus: no writes, exit 0 in both modes;
- missing golden: update adds; check reports/fails without writing;
- mismatched golden: update replaces; check reports/fails without writing;
- stale golden: update removes; check reports/fails without writing;
- multiple changes from one test are all collected;
- pytest/render failure after staged changes leaves committed goldens byte-identical;
- duplicate canonical snapshot path fails;
- malicious absolute/`..` snapshot paths cannot escape a golden root;
- non-Linux update is refused, while canonical check behavior remains documented;
- renderer fingerprint mismatch writes nothing;
- report counts, JSON, pixel statistics, and GitHub annotations are correct;
- pre-existing unrelated worktree changes are untouched;
- check mode leaves `git status --porcelain -- <golden roots>` unchanged.

## CI and verification placement

Use one authoritative visual execution per CI workflow, as today. The Python version
matrix should continue excluding visual tests; otherwise renderer-sensitive output can
redden several redundant jobs. The existing dedicated job is the right home for exact
Linux rendering and artifacts.

The master-push fast gate explicitly excludes the visual lane to protect shared host
capacity; this proposal need not change that. PR CI and scheduled Full CI already call
the reusable workflow containing the dedicated visual job. `check-full` is the local
exhaustive contract and can add the check-mode stage without forcing `just check` to
install the visual stack.

Place the screenshot stage late enough that cheap lint/setup failures do not waste a
visual run, but ensure its failure remains visible rather than swallowed. A useful
`check-full` label is `lint (TUI screenshots)`, which communicates generated-corpus
drift even though pytest renders the scenes internally.

## Agent guidance

The instruction should be judgment-based, not “all TUI edits must run screenshots.”
A concise rule would be:

> Run `just fix-tui-screenshots` after a change that is expected to alter rendered TUI
> layout, styling, focus/selection chrome, modal composition, theme/viewport behavior,
> shared renderer inputs, or after adding/renaming/removing a PNG snapshot assertion.
> Inspect every reported addition/update/removal (or the HTML report) before finishing.
> Do not run it for behavior that is fully covered by state, text, key-handling, or
> widget-contract tests and is not expected to change pixels. `just check-full` and CI
> check the corpus without accepting it.

This matches the repository's existing development guidance: use visual tests for
layout/styling/focus/composition and prefer semantic tests for model state, rendered
text, selection identity, keys, and small widget contracts.

## Longer-term maintenance reduction

The command redesign improves mechanics but does not address the root corpus size. A
separate audit should identify high-churn, low-information snapshots and replace them
with semantic assertions. Useful heuristics are:

- many snapshots differing only in text content already asserted elsewhere;
- combinatorial theme/viewport/state matrices where a smaller representative set
  covers the layout boundary;
- tests whose intended contract is state or key routing, not pixels;
- shared-header or global-renderer changes that force hundreds of nearly identical
  updates.

Keep PNG coverage for visually meaningful boundaries and a few renderer/font smoke
scenes. If repository size and binary review remain painful after pruning, consider a
future hybrid in which most goldens are Textual SVGs and a smaller PNG subset proves
rasterizer/font fidelity. Textual's official snapshot plugin uses SVG output and a
visual comparison report, showing that this is viable, but migrating formats now would
discard substantial investment in the deterministic PNG renderer and should not be
bundled with the workflow change.

## Rollout

1. Add the transactional collector and unit tests while retaining current commands.
2. Run old check mode and new `--check` mode on the same revision; require identical
   drift detection and zero committed changes.
3. Exercise one addition, update, deletion, renderer mismatch, and mid-run failure in a
   controlled branch; verify reports and no partial writes.
4. Switch CI to `fix-tui-screenshots --check`, preserving the existing job id until
   branch-protection requirements are confirmed.
5. Add the check-mode stage to `check-full` and update SASE agent memory/docs.
6. Deprecate the old public recipes for one short transition, then remove them and the
   direct update flag once callers have migrated.
7. Measure runtime, artifact size, number of changed goldens per invocation, and how
   often CI catches an omitted explicit agent run. Use those data to decide whether
   `check-full` should retain the full screenshot stage or whether only CI needs it.

## Recommended solution

Implement `just fix-tui-screenshots` as a transactional, full-corpus
generated-artifact synchronizer with a mandatory explicit `--check` mode for
verification. Run `--check` from `just check-full` and the existing dedicated CI job;
keep both `just fix` and ordinary `just check` free of the visual lane. Collect all
candidates before applying anything, report additions/updates/stale removals with pixel
statistics and reusable HTML artifacts, and never mutate goldens after an incomplete or
failed test run. Update agent instructions to invoke the mutating form only for likely
pixel-visible changes or snapshot-test changes and to inspect the report.

This is a good idea as a workflow/UX change, but not as silent auto-approval. The
non-mutating `check-full` adjustment and stale-golden detection are necessary. To
actually reduce long-term maintenance rather than merely rename it, follow the command
work with a deliberate pruning of redundant visual snapshots in favor of semantic
tests.
