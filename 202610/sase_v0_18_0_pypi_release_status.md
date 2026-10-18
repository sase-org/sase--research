---
tags:
  - pypi-release-reliability
---

# sase v0.18.0 → PyPI: what is still blocking it?

_Checked 2026-10-13 ~15:40 UTC against master `1a638eac95`._

## Short answer

**`ci_watch` will not release v0.18.0 by itself yet.** The CI that is green is
**Master Gate** (the fast per-commit lane). `ci_watch` also needs a green **Full CI**
(the heavy scheduled lane), and Full CI has not passed since **2026-08-29**, the day
v0.17.1 shipped. Release PR #299 has been waiting since 2026-08-30.

Its latest report says exactly this:

```
sase-org/sase   #299   heavy workflow not green   406f3fd7ac8e
```

## The release pipeline, and where it stops

| # | Step | Owner | Status |
|---|------|-------|--------|
| 1 | release-please opens/refreshes PR #299 `chore(master): release 0.18.0` | `Publish` workflow (cron every 3h) | ✅ open, `CLEAN`/`MERGEABLE`, version 0.18.0, `sase-core-rs>=0.39.0,<0.40.0` (0.39.0 is on PyPI) |
| 2 | PR #299 checks green | GitHub | ✅ all pass |
| 3 | Master Gate green at the exact master HEAD | `ci_watch` `gating_workflows` | ✅ run 38417053274 at `1a638eac95` |
| 4 | **Newest completed Full CI on master is green and ≤ 6h old** | `ci_watch` `heavy_workflows` + `heavy_max_age_hours: 6` | ❌ **blocked here** |
| 5 | `ci_watch` merges #299 (`merge_enabled: true`, runs every 5 min) | `ci_watch` | ⏸ waiting on step 4 |
| 6 | Next `Publish` run sees the merged PR → tags `v0.18.0` → build → 2 install smokes → PyPI upload | `Publish` workflow | ⏸ automatic; the `pypi` environment has only a branch policy, so no manual approval |

After the merge there is nothing to do by hand. The only lag is waiting for the next
`Publish` cron (up to about 3h), unless you dispatch it yourself.

## Why Full CI is red

The latest run, 38359034330 (06:50 UTC, at `8ad526f8d0`), failed 5 of 10 jobs:

- **lint**: `toobig` limit hit by `tests/ace/tui/modals/test_new_project_source.py`
  (1198 lines). **Already fixed on master** (`3c08c4676f` split it to 81 lines).
- **test (3.12/3.13/3.14)**: about 6 deterministic failures (Archive/Node Finder/project
  label tests) plus a few flaky ones (`test_dismissed_modal_releases_snapshot_rows_without_gc`,
  a models-panel `wait_for` timeout, `test_stream_json_lines_dispatches_stderr_during_a_large_stdout_burst`).
  The deterministic ones were **probably fixed** by `0a1bdf5279` and `010185b0c4`: Master
  Gate went from red at `8ad526f8d0` to green at HEAD. Full CI has not run on those
  commits yet.
- **visual-test**: a PNG-snapshot timeout in a **different test every run**
  (`agents_decks_single_main_paged`, `agents_tab_strip_query_hides`,
  `config_center_flags_narrow`, …). Master Gate does not run this lane. This is the
  failure most likely to stay red.

Another problem: Full CI is scheduled for every 2h (`17 */2 * * *`), but GitHub has only
been firing it about every 5–8h. No run has started since 06:50 UTC (about 9h ago).

## Work already tracking this

- **Epic `sase-1jz`**, _Green Master Gate and Full CI with host-independent TUI goldens_,
  is in progress. Phases `.1` and `.2` are closed. Still open:
  - `.3`: deck capture races and timeouts (its last check timed out on 10-11)
  - `.4`: visual-lane rebaseline
  - `.5`: "dispatch and monitor Full CI … record same-SHA evidence"
- **`sase-16p`** (bug, READY): **PyPI's current `sase` 0.17.1 cannot be installed.** It
  requires `sase-core-rs<0.33`, and PyPI no longer has any 0.32.x or 0.33.x release, so
  `pip install sase` fails today. Publishing 0.18.0 is the fix, which makes this release
  urgent.

## What to do

**Option A: let `ci_watch` do it (the policy path).**
1. Land `sase-1jz` (`.3` → `.4` → `.5`) so visual-test stops flaking.
2. Get a fresh Full CI run instead of waiting for the cron:
   `gh workflow run full.yml -R sase-org/sase --ref master` (takes about 1.5–2h).
3. When it is green, `ci_watch` merges #299 within about 5 min, as long as Master Gate is
   green at the HEAD at that moment. The green run has to be ≤ 6h old when that happens.
4. Optional, to skip the wait for the 3h cron:
   `gh workflow run publish.yml -R sase-org/sase -f publish_existing=false`.

You can dispatch Full CI now to see which failures are left after today's fixes. Visual
flakes will probably still keep it red until `sase-1jz` lands.

**Option B: ship now (manual override).** The red lanes are test and golden issues, not
packaging. `Publish` still builds the wheel and smoke-installs it twice, against latest
core and against the exact core floor, before uploading. Because 0.17.1 can't be
installed (`sase-16p`), merging #299 by hand is a reasonable call:

```
gh pr merge 299 -R sase-org/sase --merge
gh workflow run publish.yml -R sase-org/sase -f publish_existing=false   # optional: don't wait for cron
```

**Recommendation:** Use **B** if getting a working `pip install sase` back matters more
than strict policy. Otherwise use **A**, and dispatch Full CI now so you know what is left.
