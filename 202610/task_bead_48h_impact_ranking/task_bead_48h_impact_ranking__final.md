# Task Beads Created or +1ed in the Last 48 Hours: Impact Ranking (sase)

Lead consolidation of five independent reports (cdx, cld, grk, mus, gem) plus fresh
verification. Written 2026-10-07 at sase master `38f48d7575`.

## Bottom line

Twenty-three task beads qualify. The most impactful live work is short and mostly small:

- **Two small fixes:** `sase-1h6` (symvision red) and `sase-1h2` (LaunchApproval
  dispatch).
- **One owner-gated release:** `sase-10d`.
- **One recurring gate breaker:** `sase-13p`.

The single most important fact in the window: **none of the 117 `check` runs passed.**
The last green check on athena was on 2026-10-04. Two beads in this set are standing
causes of that.

Four beads that most researchers ranked high are **already fixed or mitigated** but still
`ready`: `sase-1h5`, `sase-17r`, `sase-1fy` and `sase-1gs`. They need verification and
closure, not new workers.

## Scope and method

- **Window.** 2026-10-05 16:25:27 UTC to 2026-10-07 16:25:27 UTC.
- **Eligibility.** A task bead qualifies if its `created_at`, or any
  `plus_one_evidence[].timestamp`, falls in the window. `updated_at` and notes were not
  used.
- **Set.** I re-derived it from a fresh snapshot of all 1,111 task beads, and all five
  researchers agree on it.
  - 23 beads: 11 created, 13 +1ed, and 1 in both (`sase-1h6`). There were 17 +1 entries.
  - By type: 9 bug, 7 flake, 4 ci, 3 flag.
  - By status: 20 `ready`, 3 `open` (the flags).
  - Nothing changed between the cutoff and this report.
- **Ranking rule.** Beads are ranked by the **marginal impact of doing their remaining
  work now**. The factors are severity, how many agents or users it reaches, how often it
  bites, whether it is still live at HEAD, and leverage, weighed against size.
  - Four reports (cdx, grk, mus, gem) gave credit for work that has already landed. cld
    did not.
  - Ranking a fixed bead high would send a worker to redo it. Delivered work therefore
    gets its own section, with a note on where it would rank if credited.
- **Lead verification.** Every disputed claim was re-checked:
  - ToolRun ledger:
    - `sase tool show -j` on all 117 window check runs;
    - `sase tool failures -d 14`;
    - production `demand` records.
  - Fresh-interpreter import probes.
  - A three-run serial repro for `sase-1fy`.
  - Linked `bead read`s and the projected-edge warning for `sase-1gs`.
  - `git count-objects` on the hidden beads clone.
  - `uv pip compile` and PyPI metadata.
  - LaunchApproval journals.
  - Commit ancestry of the fix commits.

## Headline evidence

1. **Master check is 0% green.** 117 check runs started in the window: 111 failed and 6
   were signaled.
   - The `sase-1h6` `_runs` findings appear in **65** of them. In **21** runs it was the
     only failing signature, so those runs would have passed without it.
   - The symvision stage failed in 68 of the 78 runs that reached it.
   - `sase-13p` appears in 15 runs.
2. **LaunchApproval is broken.** The last two approved LaunchApprovals (10-04 and 10-06)
   both failed with the `sase-1h2` circular `ImportError`. Every earlier request launched.
   The cold import still fails at HEAD.
3. **`pip install sase` silently installs `sase==0.1.0`.** `sase==0.17.1` is
   unsatisfiable, because its `sase-core-rs>=0.32.16,<0.33.0` window was deleted from
   PyPI. That is `sase-10d`'s territory.
4. **Triage never names owners.** Across all 897 triage items in the window's check runs,
   `possible_owners` was empty, even where an open bead's `node_id` names the exact
   failing node (`sase-13p`, `sase-1f0`, `sase-1br`). I filed **`sase-1ha`** for this (see
   below).

## Ranked list: the 10 most impactful task beads

### 1. `sase-1h6` — `just symvision` red on master (private module `sase.instructions._runs`)

ci · small · created 10-06 and +1ed in window.

**Why it matters.** It is the biggest measured source of failed agent verification in the
window. The fix is a mechanical rename.

- **Volume.** The findings appear in 65 of 117 window check runs. Lifetime: 67 runs, 57
  agents and 9 workspaces since 10-05 22:06 UTC, still failing at 16:48 UTC today. In 21
  runs it was the sole failure.
- **Cost beyond the red gate:**
  - It blames two unrelated files that define local `_runs()` helpers.
  - Triage labels it KNOWN with no owner.
  - A permanently red symvision stage hides new unused or private-symbol regressions.
- **Scope has grown since filing.** HEAD now imports `_runs` from 6 src files and 5 test
  files:
  - src: `verify.py`, `coverage_{diff,sessions,summary}.py`,
    `doctor/checks_instructions.py`, `main/instructions_handler.py`;
  - plus the `tests/instructions/*` helpers.
- **Fix.** Rename the module to a public name and update every import. Do not rename the
  unrelated helpers or add suppressions.

### 2. `sase-1h2` — Cold import of `prompt_store_mutations` breaks LaunchApproval dispatch

bug · small · created 10-06.

**Why it matters.** It is a complete, silent failure of a core mechanism: a human approves
a `/sase_run` launch and no agent starts.

- **Evidence.**
  - 2 of 2 LaunchApprovals since the regression failed (`launch-91a45f24…`,
    `launch-ac9ca583…`).
  - The failure blocked the E1 acceptance probes.
  - Reproduced at HEAD: `import sase.history.prompt_store_mutations` fails, while
    importing `prompt_store` first works.
- **Exposure.** The same lazy import sits in `launch_cwd_agents.py` and
  `launch_cwd_bead_work.py`. Only LaunchApproval failures are actually observed, though;
  epic launches have kept working.
- **Fix.** Make the import order-independent and add a fresh-interpreter regression test.
  Warm test processes hide this bug.

**Why it ranks second.** `sase-1h6` hit 65 check runs in 48 hours, while `sase-1h2` hit 2
launches in two weeks, but it destroys the requested work each time. Both are small; do
both first.

### 3. `sase-10d` — Cut a sase-core release and raise the published `sase-core-rs` floor

bug · small · +1ed 10-06 · 6 lifetime +1s.

**Why it matters.** It is the public front door, and it is a hard prerequisite for any
sase release. It ranks below #1–2 only because publishing is an outward, owner-gated step.

- **Verified today.**
  - `sase` resolves to 0.1.0 on PyPI, and 0.17.1 cannot resolve.
  - Master declares `sase-core-rs>=0.35.0,<0.36.0`.
- **The gap.** cdx's fresh `probe_core_floor` run shows **100** missing capabilities. The
  10-06 +1's count of 95 is stale.
- **Correction to gem.** PyPI does publish `sase-core-rs` 0.36.x and 0.37.0. The blocker
  is that the source pin `26ec2d61` is in no release tag yet (cld and cdx).
- **The bead's recipe is stale.** Its title still says "containing 23f19f0". Follow the
  release-owned path:
  1. Cut a core release that contains the current pin.
  2. Ratchet the window past `<0.36.0` with `tools/ratchet_core_window` (`publish.yml`
     owns reconciliation).
  3. Publish sase.
  4. Move the plugin floors.

  Do not just raise master's metadata.

### 4. `sase-13p` — TUI import budget saturated (`assert 3570 < 3570`)

ci · large · +1ed today · 13 lifetime +1s.

**Why it matters.** It is the second standing master-red cause, and it comes back every
time someone bumps the cap.

- **Volume.** 68 runs and 66 agents in 14 days. It is still failing as of 17:05 UTC
  today.
- **Triage mislabels it.** The ledger labels it **NEW with no owner** in 7 window runs, so
  agents are told it is their own regression. This is partly because the bead was closed
  from 10-01 to 10-07, and partly because of `sase-1ha`.
- **Cap history.** The cap has been raised 3290 → 3400 → 3485 → 3530 → 3570. The bead has
  been closed and reopened twice.
- **Measured today (cdx).** 3,570 modules, about 2.45 s of CPU. The time budget passes;
  the count check fails.
- **Fix.** Adopt a budget policy (an explicit ratchet) and actually defer eager imports.
  gem's `<=` suggestion just declares success at equality, and the creep would resume.

### 5. `sase-1gx` — Read-only bead paths can auto-initialize stores and commit SDD scaffolding

bug · medium · created 10-05.

**Why it matters.** It breaks a correctness and safety rule: read APIs can write and
commit into whatever checkout cwd resolves to.

- **Path.** `get_read_view()` falls through to `get_project()`, which calls `init_beads()`,
  which calls `ensure_bare_git_sdd_initialized(commit=True)`. This is confirmed at HEAD.
- **Callers.**
  - attachment and attachment-doctor commands;
  - `bead history`, `refs` and `dep`;
  - `artifact create`;
  - agent bead display.
- **Narrower than gem claims.**
  - `sase bead list` is not a caller.
  - The harm needs a cwd with no existing store.
  - `_refuse_read_only_bead_store` guards some cases.
- **Fix.** Read-only resolution opens an existing store or reports it as unavailable. It
  never initializes and never commits. This is the same over-eager resolver as `sase-14o`
  (grk), so fix the two together.

### 6. `sase-14o` — Absent-store tests resolve the host's live bead store

ci · small · **15 lifetime +1s, the most in the set**.

**Why it matters.** The two tests fail deterministically for every agent that runs
`pytest tests/completion` or `tests/doctor` on a machine with beads. They are invisible in
the governed lane.

- **Cost.** 15 landings have paid the triage cost, and cld counted 13 duplicate-triage
  reads.
- **Sibling leak.** `test_plan_candidates_emit_canonical_references` (plan resolver) fails
  the same way and should be covered in the same change.
- **Fix.** The pattern already exists from earlier resolver-isolation fixes: patch the
  resolver, not just cwd.

### 7. `sase-1h1` — TUI macro-arg detection is wrong after a quoted `,` or `)`

bug · large · created 10-06.

**Why it matters.** It is a user-facing prompt-bar correctness bug, and a Rust-core
boundary violation: the TUI disagrees with the binder and the LSP.

- **Reproduced by cdx.**
  - `#m:"a,b",` offers `flag` instead of `env`.
  - `#m("a)b",s` offers no menu.
- **Cause.** Detection still uses `body.split(",")`, `value.count(",")` and `")" in body`.
- **Fix.** Reuse sase-core's structural `macro_argument_spans` and add golden fixtures.
  This removes a duplicated Python parser, the drift class that
  `rust_core_backend_boundary` exists to prevent.
- **Why not higher.** It reaches fewer users than the items above.

### 8. `sase-1f0` — `peak_tree_rss_kib == 0` flake in the demand-run test

flake · large · 5 lifetime +1s.

**Why it matters.** It is the most frequent intermittent failure in the set: 38 runs
across 38 agents since 10-01, 4 of them in the window, the latest at 12:34 UTC today.

- **Production data is clean.** cld worried that the same race corrupts production
  demand data. Of 632 recent production ToolRuns with usage data, the only zero-peak
  record was a `true` no-op.
- **What's left.** The impact is check-lane noise only. Decide whether the contract
  promises a nonzero peak for processes that exit before the first sample, then fix the
  sampler or the assertion accordingly.

### 9. `sase-1br` — Deck scroll-settle flake (`test_block_spread_bracket_top_aligns`)

flake · large.

**Why it matters.** It is live and fails even in isolation (about 1 in 6 serial runs).

- **Volume.** 15 runs in 14 days, the latest at 13:13 UTC today. Its sibling node
  `test_scroll_derived_cursor_and_streaming_stays…` adds 13 more runs.
- **Leverage.** One fix to how deck pilots wait for the anchor scroll to settle would
  likely clear 2–3 nodes. The linked `sase-1a7` shares the same wait.

### 10. `sase-18v` — Snippet and restart CLI tests assert tmp paths that Rich truncates

ci · small · 2 lifetime +1s.

**Why it matters.** All three nodes fail deterministically for agents running the files
directly (cld reproduced them at HEAD). They stay green in the governed lane because of a
shorter basetemp.

- **Fix.** The pattern is known (`sase-13u` fixed 11 nodes of the same class). Bundle it
  with `sase-14o` as one "host and basetemp leakage in tests" change.

## High-impact work already delivered: close or verify, don't relaunch

If delivered work were credited, `sase-1h5` and `sase-17r` would slot in at about #4–6,
which is where four reports put them. Their remaining value is verification and closure.

| Bead | What was wrong | Status at HEAD (verified) | Action |
| --- | --- | --- | --- |
| `sase-1h5` | Beads pane refresh took 2.8 s per 10 s tick, with an O(epics×issues) grouping that projects to about 48 s at 4× the store. | **Fixed** by `7615e253d8` (phase `sase-1h8.6`, closed): one-pass grouping, `on_refresh(force=False)`, and a single board snapshot. The leftover triple replay is covered by the closed phases `sase-1h8.7`–`.9`. | Remeasure pane latency once (nobody has since the fix), then close with `sase-1h8.6` as evidence. |
| `sase-17r` | A fresh beads clone took 22 s p50 (max 47 s) because of loose `issues.jsonl` objects. | **Mostly fixed.** Hidden-clone gc landed in `69ecdace02` (`sase-1h8.3`). The hidden clone now holds **234 loose objects (140 MiB) and 2 packs**, down from 2,293 loose (1.84 GiB) and 37 packs on 10-06. cld measured 59 clones in the window at p50 3.2 s and p90 13.5 s. | Fold into `sase-1h8`. The root cause (`issues.jsonl` on the per-mutation path) is phase `.11`, in progress. |
| `sase-1fy` | Prompt-tab focus tests cascaded into 5 failures plus 5 errors (`FrontmatterPanel` `NoMatches`, `DuplicateIds`). | **Very likely fixed** by `69b492c278` (10-05 16:48 UTC). Both window ledger failures ran on pre-fix tree `b6114d4f95`, and there has been no ledger hit since 10-05 17:20 UTC (47 runs before that). The deterministic serial repro failed 3 of 3 at `404b0e2ac2`; it **passed 3 of 3 runs (19 tests each)** for me today. | Do one confirmatory xdist run, then close. A `sase-1gt.land` +1 called it "distinct" from that fix, but its evidence came from pre-fix trees. |
| `sase-1gs` | `artifact link add` and linked `bead read` failed bead-id validation. | **Mitigated** by `c604426d1f` (10-06 10:40 UTC), which came after all four +1s. Linked reads of `sase-1g4` and `sase-1gt` succeed today, and real link adds succeeded today. The cause was one malformed trailer, `SASE_BEAD=[sase-1g4.2.1.5]` (cld). Its edge is still dropped with a warning. | Narrow the bead to parser hardening, or close it. gem's diagnosis ("dotted IDs rejected; widen the regex") is wrong: dotted IDs work. |

## The other nine, briefly

| Bead | Why it ranks lower |
| --- | --- |
| `sase-1h0` | Dead `InputItemModal` and `MacroItemModal`. Cheap cleanup with no user path; the natural #11. |
| `sase-1gp` | Config-center session flake. 19 runs, but none since 10-05 15:25 UTC, so it may already be quiet. |
| `sase-1em` | Registry-rebuild parallel flake. 3 runs in 14 days. |
| `sase-15h`, `sase-1gz` | sase-core gateway test flakes (ETXTBSY, and a socket/symlink check). The ledger doesn't extract core test names. These say nothing about a production IPC security problem. |
| `sase-1gy` | Perf recipes regrow a gitignored `sdd/`. Checkout hygiene only. |
| `sase-1gv`, `sase-1gw`, `sase-1h4` | Correctly `open` sunset flags. They wait on the E1/E2 readouts, with 2027-01 / 0.19.0 remove-by dates. Not workable this week. |

## Where the researchers disagreed, and how it was resolved

| Question | Positions | Resolution |
| --- | --- | --- |
| Rank delivered work? | cdx, grk, mus and gem: yes. cld: no. | Rank by remaining impact and list delivered work separately (above). |
| #1 | cdx, grk and mus: `1h2`. cld: `1h6`. gem: `1gx`. | `1h6` on measured breadth, with `1h2` a close #2 on severity. `1gx` is real but latent, with no incident in the window. |
| `sase-1fy` live? | Four reports: a live top-10 flake. cld: probably fixed. | Probably fixed: ledger ancestry plus a fresh serial repro pass. |
| `sase-1gs` live? | mus and gem: broken for every agent. cld, cdx and grk: reads work. | Mitigated. gem's root cause is wrong. |
| `sase-10d` details | 95 vs 100 missing; gem: "PyPI stuck at 0.35.0". | 100 is the fresher count. PyPI has 0.37.0; the problem is the unreleased pin plus an uninstallable `sase 0.17.1`. |
| `sase-1f0` production impact | cld: may corrupt demand data (an inference). | Not supported: 1 zero-peak record in 632 production runs, and it was a no-op. |
| Metadata | gem: `14o` has 11 +1s and is medium; `10d` is XS; `17r` is large; 10 bugs and 6 flakes. | Store values: `14o` 15 +1s and small; `10d` small; `17r` medium; 9 bugs and 7 flakes. |
| `sase-13p` remedy | gem: switch to `<=`. cdx and cld: no equality shortcut. | Adopt a budget policy and defer imports. Don't redefine success at the cap. |

## Cross-cutting observations

1. **Fix the master-red pair first.** `sase-1h6` and `sase-13p` are deterministic and
   account for most red check runs that a known bead explains. Until both are green, the
   KNOWN/NEW signal for everything else is degraded.
   - Other window failures outside this set: `test_macro_terminology` (17 runs), the
     `%wait` directive-completion nodes (8–9 runs each, in active epic territory),
     formatting (13 sole failures, likely agent-local) and `_lint-flags` (6).
2. **Owner matching in failure triage doesn't work, so I filed `sase-1ha`.**
   - **What I saw.** 0 of 897 window triage items had `possible_owners`. Diagnostics:
     29/117 runs `owner candidates timed out`, 5/117 `bead store unavailable`. The other
     83 runs still matched nothing.
   - **Evidence the matcher is at fault.** Over 14 days, 3 of about 1,000 failure groups
     ever had an owner. Calling `gather_owner_candidates()` directly returns the right
     beads in 0.75 s, with locators equal to the items' `locator_paths`. So the loss is in
     settle/matching or the timeout path.
   - **History.** This is despite closed plan `sase-18j.10` (2026-09-26), whose goal was to
     prove owner matching on athena.
   - **Why it matters here.** It amplifies every CI bead in this set: it produced
     `13p`'s NEW/no-owner label, and it is why agents spend +1s and duplicate-triage reads
     rediscovering owners.
   - **Filed.** `sase-1ha` (bug, large, ready), linked to `sase-18j.10` and `sase-13p`.
3. **Eager store resolution is one bug showing up in several places.** `sase-1gx` (product),
   `sase-14o` and `sase-18v` (tests) all come from resolution that prefers the live host
   store or environment over the caller's isolation. One coordinated change beats three
   patches.
4. **Stale READY beads cost attention.** `sase-1fy`, `sase-1gs`, `sase-17r` and `sase-1h5`
   keep drawing duplicate-candidate reads (cld counted 13, 3, 4 and 1). `sase-1h8`
   already owns the store-scaling cluster, so don't launch task workers beside its open
   phases.

## Recommended action order

1. **Now (both small).** `sase-1h6` (rename `_runs`) and `sase-1h2` (break the cycle and
   add a fresh-interpreter test).
2. **Housekeeping.**
   - Verify and close `sase-1h5` and `sase-1fy`.
   - Narrow or close `sase-1gs`.
   - Fold `sase-17r` into `sase-1h8`.
3. **Owner step.** `sase-10d`: cut the core release, ratchet the window, publish.
4. **Next.**
   - `sase-13p`, with a budget policy.
   - `sase-1gx` + `sase-14o` + `sase-18v` as one resolver-isolation change.
   - `sase-1ha` (triage owners).
   - `sase-1h1`.
   - `sase-1f0` and `sase-1br`.

## Caveats

- The ToolRun ledger covers athena only. Run counts include repeat runs by one agent;
  distinct-agent counts are the better measure.
- I did not remeasure Beads-pane or clone latency myself. The `sase-17r` clone figures are
  cld's, and the hidden-clone pack state is mine.
- The `sase-1gs` link-add check used real link writes made today (not a synthetic probe).
  `sase-1gx` was confirmed from source; nobody ran it destructively.
- The `sase-1fy` closure call rests on 3 serial runs plus about 2 days of ledger silence.
  One xdist confirmation is still recommended.

## Sources

- **Swarm reports.** `task_bead_48h_impact_ranking__{cdx,cld,grk,mus,gem}.md` in this
  directory.
- **Bead store.**
  - `sase bead list --type task --status all --limit 0 --format json` (1,111 tasks);
  - audited `sase bead read` of `sase-1fy`, `sase-1gs`, `sase-1g4`, `sase-1gt`, `sase-1h8`,
    `sase-13p`, `sase-1h6`, `sase-1f0` and `sase-1br`.
- **ToolRun ledger.**
  - `sase tool runs -t check -n 1000 -j`;
  - `sase tool show -j` for all 117 window runs;
  - `sase tool failures -d 14 -j`;
  - `sase tool runs -n 1000 -j` for production demand records.
- **Code and history.**
  - `src/sase/bead/cli_common.py`, `src/sase/tool/{triage_inputs,executor_triage}.py`,
    `tests/ace/tui/test_app_import_budget.py`;
  - commits `69b492c278`, `c604426d1f`, `7615e253d8`, `69ecdace02`.
- **Runtime.**
  - fresh-interpreter import of `sase.history.prompt_store_mutations`;
  - serial pytest of `test_macro_browser_load_keymap.py` followed by
    `test_prompt_tab_focus_steal.py`;
  - `git count-objects -vH` on the hidden beads clone;
  - `~/.sase/interaction_requests/launch/` journals.
- **PyPI.** `uv pip compile` of `sase` and `sase==0.17.1`, plus the PyPI JSON for `sase`
  and `sase-core-rs`.
