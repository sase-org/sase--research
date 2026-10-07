# Impact Audit: Task Beads Created or +1ed in the Last 48 Hours (sase)

Researcher: `cld` (research swarm 3y) · Written 2026-10-07 ~12:25–13:45 EDT · sase master
`38f48d7575`

## 1. Scope and Method

**Window.** 2026-10-05 16:25 UTC → 2026-10-07 16:25 UTC (48 h before the audit started).

**Selection.** Every `task` bead in the sase project store (1,111 total, any status) that
was either **created** in the window or received at least one **`+1` evidence entry**
(`plus_one_evidence[].timestamp`) in the window. The beads sidecar was fresh (last commit
12:21 EDT today, in sync with `origin/main`). I cross-checked the selection against the
beads repo's git log: there were 11 `create` commits and 17 `+1` commits in the window,
covering 13 distinct beads. Those numbers match the JSON filter exactly.

| Set                                   | Count  |
| ------------------------------------- | ------ |
| Created in window                     | 11     |
| +1ed in window (created earlier)      | 12     |
| Created **and** +1ed in window        | 1      |
| **Total audited**                     | **23** |

Mix: 9 `bug`, 7 `flake`, 4 `ci`, 3 `flag`. Statuses: 20 `ready`, 3 `open` (the three
flag beads). Sizes: 10 small, 4 medium, 9 large. The set carries 60 lifetime +1s.

**What "impactful" means here.** I rank by the **marginal value of doing the bead's
remaining work now**. The factors are blast radius, how often the problem bites, how
severe it is, whether it is still live at master HEAD, and leverage (does it unblock other
work?), set against cost (size). A bead whose fix has already landed has little remaining
impact, even if the original problem was large. Those beads are called out separately as
close-only housekeeping.

**Evidence sources** (every live-state claim below was re-verified today, not copied from
the bead text):

1. `sase bead read` of all 23 beads (audited reads), including notes and +1 evidence.
2. **ToolRun failure ledger.** I ran `sase tool show -j` on all 117 `check` runs that
   failed or were signaled in the window (111 failed, 6 signaled), and pulled
   `sase tool failures` groups for 14 days. This is the best available measure of how
   often each defect hits the agent fleet.
3. **Live repro at master `38f48d7575`.** I rebuilt the workspace venv with
   `sase tool run install` because the editable `sase_core_rs` was unbuilt, then ran the
   bead-named test nodes and import probes.
4. **PyPI resolution** (`uv pip compile`) and the PyPI JSON metadata for `sase` and
   `sase-core-rs`.
5. LaunchApproval journals under `~/.sase/interaction_requests/launch/`.
6. `git log` and `git show` in sase, plus a read-only `sase repo open sase-core`.

## 2. Headline Findings

1. **No `sase tool run check` passed in the window.** 119 check runs started: 111 failed,
   6 were signaled, 2 were still running, and **none succeeded**. Two beads in this set,
   **sase-1h6** (symvision) and **sase-13p** (import budget), are standing master-red
   causes, not flakes. sase-1h6 alone fails 82% of the check runs that reach the
   symvision stage (60 of 73). In 21 runs (19% of all failed checks) it was the only
   specific failure.
2. **Every approved `/sase_run` LaunchApproval since 2026-09-30 has failed to dispatch.**
   That is 2 of 2: `launch-91a45f24…` on 10-04 and `launch-ac9ca583…` on 10-06, both
   `dispatch_status: failed` with the sase-1h2 circular `ImportError`. It still
   reproduces at HEAD.
3. **`pip install sase` silently installs `sase==0.1.0` today.** Published sase 0.17.1
   (2026-08-29) pins `sase-core-rs>=0.32.16,<0.33.0`, a window PyPI retention deleted.
   This is sase-10d, which has been READY for 23 days.
4. **Four beads are already fixed (or mostly fixed) but still READY.**
   - **sase-1h5:** fixed by `7615e253d8` (sase-1h8.6).
   - **sase-1fy:** almost certainly fixed by `69b492c278`.
   - **sase-1gs:** the crash was mitigated by `c604426d1f`.
   - **sase-17r:** mostly fixed. Clone p50 is now 3.2 s, and the remaining root cause is
     in flight in epic sase-1h8.

   Closing them stops agents from rereading them as duplicate candidates. sase-1fy alone
   has 13 such reads.

## 3. Inventory of All 23 Beads

"Ledger" = failing `check` runs on athena that contain the node or finding. "48h" counts
are out of the 111 failed check runs in the window; "14d" counts come from
`sase tool failures -d 14`.

| Bead     | Type · size  | Why in set           | +1 (total / in window) | Live at HEAD?                                                                     | Ledger                         | Tier                |
| -------- | ------------ | -------------------- | ---------------------- | --------------------------------------------------------------------------------- | ------------------------------ | ------------------- |
| sase-1h6 | ci · S       | created 10-06, +1    | 1 / 1                  | **Yes**: `_runs.py` still imported cross-file, 9 src import statements           | 60/111 (48h); 64 runs/55 agents | **Critical**        |
| sase-1h2 | bug · S      | created 10-06        | 0 / 0                  | **Yes**: cold import still raises                                                 | n/a; 2 of 2 LaunchApprovals failed | **Critical**     |
| sase-10d | bug · S      | +1 10-06             | 6 / 1                  | **Yes**: PyPI resolves `sase==0.1.0`                                              | n/a                            | **Critical (ext.)** |
| sase-13p | ci · L       | +1 10-07 (reopened)  | 13 / 1                 | **Yes**: `assert 3570 < 3570`                                                     | 14/111; 67 runs/65 agents      | High                |
| sase-1f0 | flake · L    | +1 10-05             | 5 / 1                  | Yes (last fail 10-07 08:34)                                                       | 4/111; 38 runs/38 agents       | High                |
| sase-14o | ci · S       | +1 10-06             | **15** / 1             | **Yes**: both nodes plus the plan-candidates sibling fail                         | not in governed lane           | Medium-high         |
| sase-1gx | bug · M      | created 10-05        | 0                      | Yes: `get_read_view → get_project → init_beads(commit=True)`                      | n/a                            | Medium              |
| sase-1h1 | bug · L      | created 10-05        | 0                      | Yes: comma/paren splitting at `_macro_arg_assist_detection.py:574–618`            | n/a                            | Medium              |
| sase-1br | flake · L    | +1 10-05             | 2 / 1                  | Yes (last fail 10-07 09:13)                                                       | 2/111; 15 runs (+13 sibling node) | Medium           |
| sase-18v | ci · S       | +1 10-06             | 2 / 1                  | **Yes**: all 3 nodes fail under agent basetemp                                    | not in governed lane           | Medium              |
| sase-1h0 | bug · S      | created 10-05        | 0                      | Yes: only self, export table, stubs, tcss and tests reference the modals          | n/a                            | Low-medium          |
| sase-1em | flake · L    | +1 10-06             | 1 / 1                  | Intermittent                                                                      | 1/111; 3 runs                  | Low-medium          |
| sase-1gp | flake · L    | +1 10-05             | 1 / 1                  | No recurrence since 10-05 11:25                                                   | 0/111; 19 runs before          | Low                 |
| sase-15h | flake · M    | +1 10-05             | 2 / 1                  | Intermittent (sase-core)                                                          | not extracted                  | Low                 |
| sase-1gz | flake · L    | created 10-05        | 0                      | Seen once (sase-core)                                                             | not extracted                  | Low                 |
| sase-1gy | bug · M      | created 10-05        | 0                      | Yes: Justfile still writes `sdd/plans/2026xx/perf_artifacts/`                     | n/a                            | Low                 |
| sase-1gv | flag · S     | created 10-05        | 0                      | Live flag; sunset waits on the E1 readout                                         | n/a                            | Low (scheduled)     |
| sase-1gw | flag · S     | created 10-05        | 0                      | Live flag; sunset waits on the E1 readout                                         | n/a                            | Low (scheduled)     |
| sase-1h4 | flag · S     | created 10-06        | 0                      | Live flag; sunset waits on the E2/E3 readout                                      | n/a                            | Low (scheduled)     |
| sase-1fy | flake · L    | +1 ×3 in window      | 6 / 3                  | **Probably fixed**: the deterministic 2-file serial repro now passes 19/19        | 2/111 (both pre-fix); 47 runs before | Close-only (verify) |
| sase-1gs | bug · L      | +1 ×3 in window      | 4 / 3                  | **Mitigated**: reads and link adds work; one malformed trailer edge is dropped with a warning | n/a                | Close-only / narrow |
| sase-17r | bug · M      | +1 10-06             | 2 / 1                  | **Mostly fixed**: 59 clones in window, p50 3.2 s, p90 13.5 s (was p50 22 s)        | n/a                            | Fold into sase-1h8  |
| sase-1h5 | bug · S      | created 10-06        | 0                      | **Fixed** by `7615e253d8` (O(n) grouping; `on_refresh(force=False)`)              | n/a                            | Close-only          |

## 4. Ranked List: The 10 Most Impactful Task Beads

### 1. sase-1h6: `just symvision` red on master (private module `sase.instructions._runs`)

**Why it matters most:** it is the single biggest source of failed agent verification
right now, and the fix is a small, mechanical rename.

- In the window, **60 of 111 failed check runs** carried the two `_runs` findings. Over
  their lifetime those findings span **64 runs, 55 distinct agents and 9 workspaces**
  (first seen 10-05 18:06, last 10-07 11:56).
- Of runs that reached the symvision stage, 82% failed on it. In **21 runs it was the only
  specific failure**: those checks would have been green without it.
- The cost goes beyond red gates:
  - Every phase of epic sase-1h3 misattributed the failure to two unrelated files.
  - One agent (0xo) described it as the failure "that made every monitor fail".
  - A permanently red symvision stage masks *new* unused or private-symbol regressions
    behind a stage that is already red.
- **Scope update for whoever works it:** the bead lists 5 import sites, but HEAD now has
  more. Later splits added three more src modules: `coverage_diff.py`,
  `coverage_sessions.py` and `coverage_summary.py`. There is also a new test,
  `tests/instructions/test_scoreboard_sessions.py`, and `checks_instructions.py` and
  `instructions_handler.py` still have their function-local imports. Rename the module
  (for example to `runs.py`) and update every `from sase.instructions import _runs` site.

### 2. sase-1h2: Cold import of `prompt_store_mutations` breaks LaunchApproval dispatch

**Why:** it silently breaks a core SASE feature (`/sase_run` → LaunchApproval) for
*every* approved request. The fix is small.

- **Measured failure rate: 100%.** Two LaunchApproval requests have been created since the
  regression (`ad7f3a19a3`, 2026-09-30). Both were approved and both failed with
  `cannot import name 'add_or_update_prompt' from partially initialized module`.
- The 10-06 failure blocked the E1 (sase-1gu) acceptance probes.
- Reproduced today at HEAD:
  - `import sase.history.prompt_store_mutations` fails.
  - `import sase.history.prompt_store` followed by the mutations import works.
- The lazy callers (`launch_cwd_agents.py:67` and `launch_cwd_bead_work.py:72`) are
  unchanged, so `sase bead work` launches from a cold process are exposed too.
- A user approving a launch that then never happens erodes trust in the gate system.
  Agents that requested help also proceed without it.
- Fix shape (from the bead): make the import order-independent, then add a
  fresh-interpreter regression test.

### 3. sase-10d: Cut a sase-core release and raise the sase-core-rs floor (PyPI sase is uninstallable)

**Why:** it is the project's public front door and a hard blocker for any sase release.
It ranks below #1–2 only because publishing is an owner-gated, outward-facing action
rather than agent-launchable work.

- Re-verified today:
  - `uv pip compile` of `sase` resolves to **`sase==0.1.0`**, a year-old release.
  - `sase==0.17.1` fails outright, because its `sase-core-rs>=0.32.16,<0.33.0` window was
    deleted by PyPI retention (sase-13t).
  - The plugin ecosystem is affected the same way: sase-telegram and sase-github
    silently downgrade, and sase-research-artifacts fails to resolve (per the 09-20
    escalation note).
- **The gap is wider than the bead's latest notes suggest:**
  - The checkout's `pyproject.toml` declares `sase-core-rs>=0.35.0,<0.36.0`, but the dev
    toolchain is running core **0.37.0**.
  - The source pin `26ec2d61` is **not** in `v0.37.0`; the pin is 11 commits ahead of the
    newest tag.
  - sase-1eq.12.land counted 95 capabilities missing from the declared floor.
- The required sequence: cut a sase-core release that contains the pin, run
  `just ratchet-core-window` (the window must move past `<0.36.0`), publish sase, then
  raise the sase-research-artifacts floor.
- 9 distinct agents have read this bead as a candidate duplicate. It keeps absorbing new
  "published floor lags pin" reports.

### 4. sase-13p: TUI app import budget saturated (`assert 3570 < 3570`)

**Why:** it is the second standing master-red cause, and the bead reopens whenever it is
closed. The real work is a sustainable budget policy, not another one-off trim.

- Reproduced today at HEAD: `import sase.ace.tui.app` loads **exactly 3570 modules**
  against `_MAX_MODULE_COUNT = 3570` with a strict `<`.
- It re-saturated around 10-06 18:57. Since then it failed **14 of the 31** failed check
  runs that reached the test stage. Lifetime: **67 runs, 65 agents**.
- Because the bead was closed between 10-01 and 10-07, the ledger classified many
  recent occurrences as **NEW** with no owner. Agents were invited to treat it as their
  own regression.
- History:
  - The closure grew 3290 → 3570 (+8.5%) in 17 days.
  - The cap has been raised at least three times: 3290 → 3400 → 3485 → 3530 → 3570.
  - The bead has been closed twice and reopened twice.
- Leverage: fixing it properly (a ratchet, an explicit `<=` decision, plus actual
  deferral of eager imports) removes a recurring gate breaker. It also bounds TUI
  startup cost, which users feel.

### 5. sase-1f0: `test_foreground_run_records_context_usage_and_grant` records `peak_tree_rss_kib == 0`

**Why:** it is the highest-frequency *intermittent* failure in this set, and it sits in
the ToolRun demand-measurement code.

- Ledger: **38 failing check runs across 38 agents** since 10-01, including 4 in the
  window. The latest was 10-07 08:34 (sase-1h9.1).
- 5 independent +1s, one in the window. 6 agents have read it as a duplicate candidate.
- The hypothesized cause is that a short-lived child exits before the tree-RSS sampler
  takes a non-zero sample.
- **My inference, not verified:** if that is right, production ToolRun records for fast
  commands may also store `peak_tree_rss_kib: 0`. That data feeds the demand and
  admission corpus (see decision `record-before-admit`). Fixing the sampler, rather than
  relaxing the assertion, may matter beyond the test.

### 6. sase-14o: Bead-store tests leak to the host's live store and fail in every agent workspace

**Why:** it has the most +1s of any bead in the set (**15**), it is deterministic, it is
small, and it taxes nearly every land agent.

- Reproduced today at HEAD with raw pytest:
  - `test_project_beads_skips_when_store_is_absent` fails `'OK' == 'SKIP'`.
  - `test_bead_candidates_without_a_store_returns_empty_list` returns 16 live bead
    candidates.
  - The sibling `test_plan_candidates_emit_canonical_references` (plan resolver leak,
    noted in the sase-1ev and sase-1h3 +1s) also fails.
- It never shows in the governed lane, so `check` stays green on it. Every agent running
  `tests/completion` or `tests/doctor` directly sees red nodes unrelated to its diff.
- **13 agents** have spent audited reads deciding whether their failure duplicates this
  one.
- The fix pattern already exists: isolate the resolver, as sase-ml and sase-ql did.
  Cover the plan resolver in the same change.

### 7. sase-1gx: Read-only bead paths auto-initialize stores and attempt SDD-init commits

**Why:** it is a correctness and safety defect, where read-only display paths can
*write and commit* into whatever checkout cwd resolves to. It is still live, and its
blast radius is every caller of `get_read_view()`.

- Verified at HEAD: when `resolve_beads_location(require_existing=True)` is not
  read-only, `get_read_view()` falls through to `get_project()`. That path
  re-resolves with `materialize=True` and calls
  `init_beads() → ensure_bare_git_sdd_initialized(commit=True)`.
- The attachment doctor and the plan-archive doctor reach it.
- The stray-root-sdd cleanup plan only isolated the known leaky tests. This is the
  remaining root.
- It is medium-sized and well specified ("read-only resolution never initializes or
  commits"). Unwanted commits in unrelated repos are expensive to clean up, so the value
  per hour is high.

### 8. sase-1h1: TUI macro-arg detection is wrong after a quoted `,` or `)`

**Why:** it is a user-facing correctness bug in the prompt bar, which Bryan uses daily.
It is also a Rust-core boundary violation: the TUI disagrees with both the runtime binder
and the LSP.

- Verified at HEAD: `_macro_arg_assist_detection.py` still uses `body.split(",")`,
  `value.count(",")` and `")" in body` (lines 468, 574–618).
- The bead's repros are concrete. `#m:"a,b",` offers the `flag` menu instead of `env`.
  `#m("a)b",s` opens no menu at all.
- The proper fix reuses core structural spans (`macro_argument_spans`) and adds golden
  fixtures. That removes a duplicated Python parser, the kind of drift the
  `rust_core_backend_boundary` rule exists to prevent.
- It is large, so it ranks below the cheaper, broader items.

### 9. sase-1br: `test_block_spread_bracket_top_aligns` scroll-settle flake

**Why:** it is a live flake in the deck pilot suite, it fails even in isolation (1 in 6
serial runs), and it has a sibling.

- Ledger: **15 failing check runs** in 14 days, 2 of them in the window. The latest was
  10-07 09:13.
- The sibling node in the same file, `test_scroll_derived_cursor_and_streaming_stays…`,
  has **13 more runs**. The linked sase-1a7 shares the scroll-settle wait.
- One root-cause fix to how deck pilots wait for the anchor scroll to settle would
  likely clear 2–3 nodes. That leverage puts it above the other flakes despite its large
  size.

### 10. sase-18v: Snippet and restart CLI tests assert full tmp paths that Rich truncates under the agent basetemp

**Why:** it is deterministic in every agent workspace, small, and the fix pattern is
known (sase-13u fixed 11 TUI nodes of the same class).

- Reproduced today at HEAD: all three named nodes fail with raw pytest.
  - `test_add_rich_format_states_created_action`
  - `test_delete_rich_format_prints_restore_and_removed_path`
  - `test_wipe_failed_exits_1_and_prints_recovery_dir`
- Like sase-14o, it is invisible in the governed lane but red for any agent running these
  files directly. +1ed twice in the last 3 days.
- It is cheap to bundle with sase-14o as a single "host and basetemp leakage in tests"
  task.

## 5. Notable Beads Outside the Top 10

**Already fixed or mitigated (close or verify, do not launch full work):**

- **sase-1h5** (Beads pane O(epics×issues) refresh): **fixed** by `7615e253d8`
  (2026-10-06 22:35, epic phase sase-1h8.6).
  - `beads_data.py` now groups phases in one dict pass.
  - `BeadsPane.on_refresh` calls `_request_load(force=False)`.
  - Close as done, with sase-1h8.6 as evidence.
- **sase-1fy** (prompt_tab_focus_steal under xdist): **very likely fixed** by
  `69b492c278` ("childless frontmatter mount", 2026-10-05 12:48).
  - Its ledger groups (47 runs, 45 agents) were last seen 10-05 13:20 and have not
    recurred in ~2 days of heavy check traffic.
  - The 2 window hits are from 10-05, on trees that predate the fix.
  - The deterministic repro recorded by sase-1eq.5.1.land (macro-browser keymap file
    followed by the focus-steal file, serial) now **passes 19/19**.
  - The window +1s were relays of 10-05 observations.
  - Recommendation: one confirmatory xdist run, then close. If that run fails, this bead
    belongs at about #5 in the ranking.
- **sase-1gs** (artifact link validation error broke `bead read` and `link add`):
  **mitigated** by `c604426d1f` (2026-10-06 06:40). That commit drops invalid projected
  edges with a warning.
  - I traced the culprit to a single malformed commit trailer,
    `SASE_BEAD=[sase-1g4.2.1.5]` in `8c8c47f720`, which is missing the `[1]` footnote.
    It is 1 of 1,312 trailers since September.
  - What remains is cosmetic: a `dropping projected edge…` warning on link listings, plus
    optional parser hardening. Narrow the bead or close it.
- **sase-17r** (beads sidecar clone slow because of `--dissociate` repack): in the
  window, 59 beads clones ran with **p50 3.2 s, p90 13.5 s, max 17 s**, down from p50 22 s
  and max 47 s.
  - Hidden-clone gc landed in sase-1h8.3 (`69ecdace02`).
  - The root cause, the per-mutation `issues.jsonl` commit, is phase **sase-1h8.11**,
    which is in progress.
  - Fold into or close against epic sase-1h8.

**Live but lower impact:**

- **sase-1h0** (dead `InputItemModal` and `MacroItemModal`): pure maintenance cost.
  Deleting them is easy, and a good #11.
- **sase-1em** and **sase-1gp** (parallel-lane TUI/registry flakes): 1/111 and 0/111 in
  the window.
- **sase-15h** and **sase-1gz** (sase-core `sase_gateway` flakes, each seen about 1–3
  times in two weeks): the ledger does not extract sase-core test names, so their
  frequency cannot be quantified beyond the bead notes.
- **sase-1gy** (perf recipes regrow a gitignored `sdd/` tree): local clutter only.
- **sase-1gv, sase-1gw, sase-1h4** (flag sunsets): scheduled cleanup with remove-by dates
  of 2027-01-03/04. They are gated on E1/E2 readouts, so the work cannot start yet.

## 6. Cross-Cutting Observations

1. **Fix the two master-red causes first.** sase-1h6 and sase-13p together account for
   most of the 0% check pass rate. Until both are green, the KNOWN/NEW triage signal for
   every other failure is degraded. Also, sase-13p's closed-then-reopened cycle
   produced "NEW, no owner" verdicts.
2. **Host-leakage test debt is cheap and high-volume.** sase-14o and sase-18v (plus the
   plan-candidates sibling) are all "green in the governed lane, red for agents running
   raw pytest". Together they hold 17 +1s and drew 15 duplicate-triage reads.
   One small task could clear all of them.
3. **Stale READY beads cost agent attention.** sase-1fy, sase-1h5, sase-1gs and sase-17r
   drew 13, 1, 3 and 4 `read-by` duplicate checks respectively. Closing fixed beads
   promptly cuts that triage traffic.
4. **Context outside this set.** The most frequent non-bead failures in the window were
   the `%wait` directive-completion nodes (about 7–11 runs each, coinciding with epic
   sase-1h7) and `test_macro_terminology` (16 runs). Those belong to active epics, not to
   these beads.

## 7. Caveats

- The ToolRun ledger is machine-local, covering athena only. Run counts include repeated
  runs by the same agent; the distinct-agent counts are the better impact measure.
- "Live at HEAD" means reproduced in workspace `sase_12` at `38f48d7575` after
  `sase tool run install`. Flake verdicts come from ledger history, not new loops, except
  for the sase-1fy serial repro.
- The sase-1f0 production-data concern is an inference from the bead's hypothesized
  mechanism. I did not verify it against real ToolRun records.
- One `grep` I ran over `~/.sase` listed a peer researcher's report filename. I did not
  open or read it, and this analysis is independent of it.
