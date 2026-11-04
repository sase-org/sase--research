# The Ten Task Beads to Work Next (2026-11-04)

_Researcher `cld`, research swarm `3a`. Snapshot taken 2026-11-04, 19:30–20:45 UTC, at sase
master `34b09fa219`. I checked live agents on apollo (this machine) and athena before
ranking anything._

## Bottom Line

The sase project has **391 non-closed task beads**. About **ten of them deserve work now**.
Most of the rest are dormant, low-signal, or already owned by an epic that is running.

**What I recommend:**

- **Start four now:** sase-1r4, sase-1al, and the small-fix batch (sase-zo, sase-1ce, sase-1q3).
- **Plan two now, but land them after the Agent Hijack epic (sase-1qz) closes:** sase-1qj
  and sase-12u. They share a host-liveness design, and the hijack epic is rewriting the
  restart path they would touch.
- **Make one owner decision:** sase-j0.

| #   | Bead         | Type · size        | Why it is on the list                                                                                                    | Start?                         |
| --- | ------------ | ------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------ |
| 1   | **sase-1r4** | bug · large        | A live `sase update` kills running agents silently. 3 died in 2.5 min on 11-03, and work downstream stalled for about 6 h. | Now                            |
| 2   | **sase-1qj** | bug · large        | A host restart strands every `%w` waiter and land agent. 27 runs failed on 11-01, and sase-1r2 had to add a cron watchdog. | Plan now, land after sase-1qz  |
| 3   | **sase-12u** | bug · large        | 39 of the 120 in-progress epics have every child closed. These zombies hide the real stalls.                             | Same epic as #2                |
| 4   | **sase-1al** | flake · large      | The most-recurring flake that no epic owns. It failed 13 of 26 apollo full runs, including a clean-base run.             | Now                            |
| 5   | **sase-zo**  | bug · small        | +10. `sase repo list/open/path -p sase` (the display name) still fails. I reproduced it today.                            | Now (small batch)              |
| 6   | **sase-1ce** | bug · small        | When `$EDITOR` exits non-zero, everything typed in it is deleted. This loses user data.                                   | Now (small batch)              |
| 7   | **sase-172** | ci · large         | +4. Fails deterministically when run alone on master; I reproduced it today. Every landing that selects the file has to triage it again. | Now                            |
| 8   | **sase-1q3** | ci · small         | `SASE_MODEL_OVERRIDE` leaks into pytest, so any agent on a fallback model sees 7 false test failures.                    | Now (small batch)              |
| 9   | **sase-1pw** | bug · medium       | Pytest worker-token waiters starve, burning 45 min and then exiting 4. This happened in 2 of 622 athena tool runs in the last week. | Now                            |
| 10  | **sase-j0**  | untyped · large    | +38, the most corroborated task. Its claim is stale. The CI Telemetry `test-cost` job is cancelled at its 180-min cap on every run. | Owner decision first           |

Ranks 1–4 are clear. Ranks 5–8 are cheap fixes with a high payoff. Ranks 9–10 matter, but
they are infrastructure work you should scope deliberately.

---

## 1. What Is Running Right Now (Conflict Map)

### apollo (this machine)

| Agent             | What it is doing                                                                                                   | Task beads to keep away from                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| `cd--code` (muse) | Implementing `plan:202611/codex_exec_final_answer_integrity.md` in `src/sase/llm_provider/_subprocess_codex.py` and `codex.py` | **sase-1e2** (the Codex `web__run` / exec tool-call capture uses the same stream parser) |
| `research.3a.*`   | This swarm                                                                                                         | —                                                             |
| `bob-cli-*`       | A different project (bob-cli)                                                                                      | —                                                             |

### athena

| Epic or agent                                                         | Live phases                                       | What it touches                                                                                                                                                                                                                                       | Task beads it owns or overlaps                                                                                                                                                  |
| --------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **sase-1qz** Agent Hijack, with nested **sase-1qz.6.1**               | .6, .7, .9, .10, .11; nested .2 and .4–.7         | Agent stop protocol, workspace custody, `done.json` loaders, `sase agent restart` on hijacked targets, crash reconciliation, the Agents tab, the recovery panel, the prompt bar                                                                        | **sase-1qi** (restart cannot find crash-killed agents) and **sase-1me** (SIGTERM claim release) sit on the same code. The restart half of sase-1qj overlaps too.               |
| **sase-1r8** Agent publication false blocks                           | .4, .5, .6                                        | The agents-sync publication drain and scanner rules in sase-core                                                                                                                                                                                      | **sase-1or**, **sase-187**, **sase-1ot**, **sase-1r7**                                                                                                                          |
| **sase-1r2** Green Full CI and v0.19.0                                | .5 (core), .6 (full-ci), .7, .8                   | Full CI jobs, flakes in the blocking lanes, the core pin, the release                                                                                                                                                                                 | Took over **sase-1ql, 1ny, 1oy, 1mu, 1gg, xh** (sase-1r2.3 note #2). It will hit **sase-1q0** if Full CI is red there. It excludes **sase-1r0** by name, and **sase-1qw** depends on its core work. |
| **sase-1n6.11** Steward completion                                    | .4                                                | The release steward and the first steward-run release                                                                                                                                                                                                 | —                                                                                                                                                                               |
| `18a` (opus, planning)                                                | —                                                 | sase-core release-plz force-pushes that break the daily core release cut                                                                                                                                                                              | — (sase-core workflow only)                                                                                                                                                     |
| `18b` (opus, planning)                                                | —                                                 | Diagnosing `Cleanup task failed: Object of type AgentWorkspaceRetention is not JSON serializable` after a kill or dismiss (screenshot `~/tmp/screenshots/20261104_151315.png`) | Adjacent to the dismiss beads **sase-1ds** and **sase-1pr**, but none of my picks                                                                                               |

None of the ten picks edits the files these agents are changing, with one exception:
**sase-1qj and sase-12u** must wait for the hijack epic's restart and crash-reconciliation
work before they change `sase agent restart` or the agent lookup.

**Stale "in progress" noise:** 120 plan beads are `in_progress`, but only the five above have
live agents. That gap is the subject of pick #3.

---

## 2. How I Ranked

1. **Census.** Of the 391 non-closed tasks, 375 are ready, 12 open, 3 snoozed, and 1 in
   progress. By type: 143 bug, 102 feature, 90 flake, 30 memory, 12 ci, 7 flag, 5 untyped
   legacy, and 2 mirrored GitHub issues with no task type (sase-1qw, sase-1r0).
   - 310 of the 391 have **zero** +1s.
   - Only 20 of the 250 defect beads have ≥3 +1s.
   - 156 of the 250 defects are sized large.
2. **Recurrence across hosts.** I scanned the selection-health full-run records on both
   hosts:
   - athena: 625 records since 10-21.
   - apollo: 26 records, 14 of them since 10-28.

   I counted a failing node only when it was not in that run's own changed files. Runs with
   more than 5 failures were counted separately. That keeps the rule from the Nov 2
   backlog-chain review (`research:202611/task_backlog_cleanup_chain_review/task_backlog_cleanup_chain_review__final.md`):
   **a failure on any host counts.**
3. **Owner rules from that review.**
   - Treat an in-progress task whose holder is dead as unowned.
   - Prefer defects that fit in one phase.
   - Flag design-shaped work separately.
   - Never select beads that an active epic owns.
4. **Validity checks at `34b09fa219`.**
   - I reran repros where I could: sase-zo, sase-172.
   - I read the code for sase-1ce, sase-1q3, sase-1pw, sase-1r4, sase-v6, and sase-1l0.
   - I checked the GitHub Actions state for sase-j0, sase-1qw, and sase-1r0.
5. **Score.** Impact (agent work lost, user data lost, fleet time wasted) × frequency ×
   tractability. Anything that conflicts with a live epic was moved out.

---

## 3. The Ranked List

### #1 · sase-1r4 — Live-update signature skew kills agents silently

**Why it matters.** `sase update` fast-forwards the editable primary checkout many times a
day; the AXE scheduler restarted 8 times on 11-03. Runners that booted before an update
then lazily import new modules. If a commit changed a function signature, the staged-handoff
adoption raises a `TypeError`, and the agent dies.

On 11-03 at 10:56, `ced5901dd5` removed `require_capture` and `persist_chat`:

- `sase-1n6.11.1`, `178.w0--plan`, and `17a--3` all crashed within 2.5 minutes.
- Their staged successors never launched, and their work was never committed.
- The auto-restart healer logged `nothing_eligible` every 70 s for six hours.

The full incident is in `research:202611/athena_silent_agent_failures_live_update_skew.md`.
This is the most damaging defect that recurs and has no owner. Every live update is a fresh
chance to lose in-flight work.

**Still valid.** `src/sase/axe/runner_failure_facts.py` still has only the
`cannot import name` / `no module named` / `partially initialized module` patterns. It has
none for signature skew.

**Conflicts.** None. The hijack epic changes runner custody, not failure classification or
the auto-restart healer. Keep the scope off `sase agent restart`.

**Recommended solution (one tale, about 2 phases):**

1. **Classify signature skew, but only with proof that the code moved.**
   - Add a `TypeError` signature-mismatch shape: `unexpected keyword argument`,
     `missing N required … argument`, `takes N positional arguments but M were given`.
   - Count it as skew **only** when the bead's W1 evidence also holds: the runner's boot
     `code_identity` differs from the current checkout. Optionally require W3 as well: the
     named parameter appears in `git log -S` between the two.
   - This keeps real TypeErrors out of the healer. Put the classification predicate in
     sase-core if the healer's rules already live there (Rust boundary rule).
2. **Explain it.** Extend `source_skew.code_swap_explanation()` to the same shapes, so the
   FAILED notification says "the sase checkout moved under this runner."
3. **Clean up after a failed adoption.**
   - A staged monitor whose adopter died should settle to a terminal state (failed or
     orphaned) instead of staying `staged` / `Running`.
   - The crashed row must still appear in `sase agent list -a`.
4. **Leave the structural fixes out of scope:** sase-1jd (preload), sase-1jf (resume in
   place), and sase-1je (per-process releases).

**Done when** replaying the 11-03 signature is classified `skew_suspect=true`, the healer
admits the row, a real non-skew TypeError stays ineligible, and a staged monitor orphaned by
a failed adoption settles within one healer pass.

### #2 · sase-1qj — A host restart strands waiters and land agents

**Why it matters.** The 11-01 reboot left 27 waiters FAILED (16 land, 11 phase), with dead
PIDs and no `done.json`. Each epic had to be recovered by hand with `sase bead work`.
sase-1r2 now installs a self-removing hourly **crontab watchdog per epic** to work around
this, which shows how often it bites.

**Conflicts.** The hijack epic changes `sase agent restart`, the `done.json`-driven status
loaders, and dead-PID crash reconciliation (plan lines 242, 465–512, 580, 690). Plan this
now; land it after sase-1qz.7 and sase-1qz.11 close. **sase-1qi** (restart cannot find
crash-killed agents) belongs in the same epic once hijack lands.

**Recommended solution.** Build a **host-owned epic-liveness reconciler** in sase-core,
shared with #3, and run it at AXE scheduler start and on a slow tick.

- **Restart detection.** After a `boot_id` change, find in-progress epic beads whose phase,
  land, or `%w` runner rows have dead PIDs and no `done.json`.
- **Relaunch.** Recover them through the existing `sase bead work <epic>` path. It already
  reassigns every non-closed bead and never touches closed phases. Do this once per epic
  per boot, with a durable marker so it is exactly-once.
- **Notify.** Post one inbox notice per recovered epic.
- **Retire the workaround.** Once this works, drop the per-epic crontab watchdog from the
  epic templates.

**Done when** a simulated reboot in a fakey or fixture host relaunches every stranded epic
exactly once, and a second scheduler start does nothing.

### #3 · sase-12u — Zombie epics bury the real stalls

**Why it matters.** I counted **39 in-progress plan beads whose every child is closed**, for
example sase-zu, sase-126, sase-1ah, sase-1q4, and sase-j7. In total, 120 plans are
`in_progress` but only about five have live agents. That noise hides real stalls: the last
backlog chain skipped sase-j0 for weeks because of a stale claim. It also inflates every
"what's active" query that agents and you rely on.

**Conflicts.** Same as #2 for the relaunch half. The report-only triage has no conflicts.

**Recommended solution.** Put it in the same epic as #2.

1. **One-time, report-only pass.** List every in-progress plan with all children closed,
   plus its last land-agent outcome.
2. **You decide per row:** relaunch the land agent or close the epic as superseded or
   canceled. Do not cascade-close blindly. The bead says so, and an epic's land agent owns
   its close.
3. **Ongoing invariant.** The reconciler from #2 relaunches the parent's land agent when
   all of its children are closed and no land agent is live.

**Done when** the zombie count is 0, or every remaining zombie has an owner decision, and
the reconciler test covers the "child epic closed, parent idle" case.

### #4 · sase-1al — Command-line panel pilot trio flakes, mostly on apollo

**Why it matters.** The trio is `test_empty_panel_semicolon_hops_to_palette_and_back`,
`test_empty_panel_escape_follows_the_hide_panel_binding`, and
`test_panel_escape_keeps_draft_across_reopen`, all in
`tests/ace/tui/command_line/test_panel_shell_pilot.py`.

- It failed in **13 of 26 apollo full-run records since 10-21**, including run
  `20261104T034217`, a **clean-base workspace with zero changed files**.
- On athena it failed in 1 of 625.
- None of the failing runs touched `command_line/`.
- Hijack phase workers keep reporting it as a PROPOSED FOLLOW-UP (sase-1qz.4 and
  sase-1qz.8 notes).
- It has 5 +1s, and sase-1ew was already closed into it as a duplicate.

This is the "rank across hosts" lesson again: green on athena, red on apollo. sase-1r2 did
not take it over.

**Likely mechanism.** The tests wait 5 s for `is_command_line_grammar_pending()` to clear.
The grammar loader shells out to build an approximately 0.5 MB spec in a worker thread
(`grammar.py::_load_command_line_grammar_sync` → `ensure_command_line_spec`). On apollo,
which is smaller and slower than athena, that subprocess can take longer than 5 s under load.

**Recommended solution.**

1. Reproduce on apollo under `-n 8` alongside `tests/ace/tui/`.
2. Give these tests a session-scoped **pre-built grammar fixture**: build the spec once,
   then install the handle. Only the loader-specific test (the one that already
   monkeypatches `_load_command_line_grammar_sync`) should exercise the async load.
3. Keep the assertions. Do not raise timeouts.
4. **Check the product side too:** if `;` cannot hop while the grammar is pending, a slow
   host feels the same lag. Consider letting the hop proceed and filling in completion
   later.

**Done when** the three nodes pass 20× serially and 3× under `-n 8` alongside
`tests/ace/tui/` **on apollo**.

### #5 · sase-zo — `-p <display name>` fails for repo commands (+10)

**Status.** The original `match_repo_record` half was fixed in `e57d76c79b` (09-13), and
`sase repo open sase-core` works now. The remaining half still reproduces today:

```
$ sase repo list -p sase
Project 'sase' has no WORKSPACE_DIR in /home/bryan/.sase/projects/sase/sase.sase.
```

`sase repo path plans -p sase` fails the same way. The cause is that
`main/workspace_handler_context.py::resolve_project_context` passes `-p` straight to
`get_project_file_path`, which only understands the directory key. Agents are told to use
`sase repo`, and the display name is what every surface shows them (decision
`project-labels-never-keys`). The command exits 2, so agents fall back to a slower path
or skip `-p` entirely.

**Recommended solution.**

- Canonicalize `-p` through the project registry, the same resolver `sase project show`
  and aliases use. Accept a display name, an alias, or the canonical key.
- Fail with the list of candidates when a display name is ambiguous.
- Add a regression test where the display name differs from the canonical key.

Size: small.

### #6 · sase-1ce — `$EDITOR` exit non-zero deletes the typed prompt

**Still valid.** In `src/sase/ace/tui/actions/agent_workflow/_editor.py`, `run_editor`
returns `None` when `returncode != 0`, and the `finally` block always runs
`os.unlink(temp_path)`. The workflow-YAML editor has the same shape. Exiting nvim with
`:cq`, or having it crash or get killed, throws away everything typed. That breaks the
"never lose a user prompt" guarantee from sase-1ca.

**Recommended solution.**

- On a non-zero exit, compare the file with the initial content. If it changed, keep the
  text: stash it with a recovery source through the existing Stash path, and toast where
  it went.
- Unlink only on success or when nothing changed.
- Apply the same fix to the YAML editor.

**Conflicts.** None. The hijack prompt-bar phase (sase-1qz.10) does not touch the editor
path; I grepped its plan.

Size: small.

### #7 · sase-172 — The MRU pruning test fails deterministically when run alone

**Reproduced today on apollo at `34b09fa219`:**

```
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_vcs_macro_mru_pruning.py::test_load_launchable_prunes_provider_mismatched_prefix
E  AssertionError: assert ['#gh:sase'] == ['#gh:sase', '#git:otherproj']
```

It passes inside the full suite, which makes it order-dependent. That explains why the
full-run records never show it. It also explains why four landing agents re-hit it, between
10-03 and 10-14, whenever their scoped selection included the file.

The narrowing in the bead points at `_vcs_prefix_provider_mismatched` and
`_workflow_and_ref_for_prefix` iterating `get_ref_patterns()`. Their order depends on the
installed provider plugins (sase-github). If that is the cause, it is a **product bug too**:
on a host with sase-github installed, genuine bare-git `#git:<proj>` MRU entries get pruned.

**Recommended solution.**

1. Make prefix-to-provider resolution independent of plugin order. Match the explicit
   `#git:` / `#gh:` sigil before falling back to pattern iteration.
2. Make the test hermetic about which plugins are installed.
3. Add a variant that runs with sase-github's patterns registered first.

### #8 · sase-1q3 — `SASE_MODEL_OVERRIDE` leaks into pytest

**Still valid.** `tests/_conftest_environment.py` scrubs `SASE_AGENT*` and
`SASE_MODEL_ALIAS_OVERRIDES` but not `SASE_MODEL_OVERRIDE`. The runner sets that variable
exactly when an agent falls back to another model (`axe/run_agent_exec_retry.py:494`,
`run_agent_retry_spawn.py:299`). Any agent running on a fallback model therefore sees 7
false failures in its checks. sase-1pj.5.1.land isolated this cleanly: 51 pass without the
variable, 7 fail with it.

**Recommended solution.**

- Add `SASE_MODEL_OVERRIDE` to the autouse scrub, keeping explicit per-test
  `monkeypatch.setenv` working.
- Add a regression test that sets the variable at session level and asserts the scrub.

Size: xsmall to small. Batch it with #5 and #6.

### #9 · sase-1pw — Pytest worker-token waiters starve

**Why it matters.** `tests/_suite_gate_lease.py::WorkerTokenLease.acquire` polls with no
ticket and grows greedily, so later scoped runs take freed tokens ahead of an earlier
waiter. On athena, **2 of 622 tool runs since 10-28** hit
`Timed out waiting for a SASE pytest worker-token grant … after 2700s`. Each one cost an
agent 45 minutes and a full verification cycle, and the epic-3 chain reported an
UNDETERMINED check from the same contention. The code is unchanged.

**Recommended solution.**

- Add FIFO tickets to the lease file: an arrival-ordered waiter queue under the same lock.
- A waiter at the head of the queue reserves freed tokens up to its floor, and later
  arrivals cannot take them.
- Keep greedy growth only for the head of the queue.
- Prove it with a fake-clock unit test of the starvation sequence the bead already sketches.

Size: medium.

### #10 · sase-j0 — `check-full` and CI Telemetry `test-cost` budgets (+38, stale claim)

**Why it is here.** It is the most-corroborated task in the store, and it is still
`in_progress` under a holder that has been dead since at least 10-26. Its impact has
changed since August:

- `check-full` is now explicit-only (decision `check-full-is-explicit`), so landers no
  longer trip on it.
- athena's newest local cost recording is from **2026-09-19**. Nobody exercises the gate
  locally.
- The **CI Telemetry** workflow (every 6 h) is red on every run since at least 11-01 (7 of
  7). On 11-04, its `test-cost` job was **cancelled at the 180-minute cap**, `contention-test`
  failed (that is **sase-11b**), and `coverage-contexts` failed with an xdist worker crash
  (below).

That is about 3 runner-hours burned on every telemetry run with no data out.

**Recommended solution (decide first, then one tale):**

1. Release the stale claim. As the owner, set sase-j0 back to `ready`; agents must not
   hand-edit status.
2. Choose one:
   - **(a) Retire hard budgets.** Keep `just test-cost` as an on-demand report.
   - **(b) Recalibrate.** Judge only per-worker, CPU-normalized keys. The 08-17 note showed
     the wall-derived keys are host-contention artifacts. Rebuild the budgets from recorded
     history, and shard or scope the CI job so it finishes under its cap.

   I lean toward (b): the cause budgets (`ace_page_enter`, `textual_app_run_test_enter`)
   are the only signal guarding ACE test cost.
3. Fold in **sase-11b** and the unowned `coverage-contexts` crash, so the deliverable is
   "CI Telemetry is green."

---

## 4. Not Picked, and Why

**Owned by an active epic (do not touch):**

- sase-1ql, 1ny, 1oy, 1mu, 1gg, xh: taken over by sase-1r2.3.
- sase-1q0 (footprint `bump()` microbench): it fails Full CI's lane, which sase-1r2.6 must
  turn green.
- sase-1r0 and sase-1qw (macOS install broken, install canary red): issues #325 and #324
  are still open today. The canary's macOS job is cancelled while the ubuntu job passes.
  Recheck after sase-1r2.5 publishes a complete sase-core-rs.
- sase-1e2: the Codex parser, which `cd--code` is editing.
- sase-1or, 187, 1ot, 1r7: publication work under sase-1r8.
- sase-1qi and 1me: the restart and SIGTERM-claim code under sase-1qz.

**High +1 count but no longer recurring (dormant):**

- sase-lk (+13): every +1 dates from August. Its node IDs were split, and its last note
  says the gate debt it tracked no longer exists. Close it as obsolete after a quick
  recheck.
- sase-yn (+7): a sase-core node that fails only under a redirected TMPDIR. No evidence
  since 09-09.
- sase-t6, sase-si, sase-ni: no hits in 14 days of full-run records on either host.

**Partly fixed or dormant:**

- sase-v6: `e5c09c19f5` fixed the target-dir half. The recipe still ignores cp/mv failures,
  which is a 2-line fix. Fold it into any Justfile work.
- sase-1g1: apollo's primary sase-core checkout is clean and at today's HEAD.
- sase-1l0: size aliases do not route to the codex `small` tier.

**Real but design-shaped, or rare (runners-up, in order):**

1. sase-1kp: `beads.db` is both Rust's mutation lock file and Python's WAL mirror, so lost
   POSIX locks could corrupt the mirror. It needs a lock-protocol decision.
2. sase-1db: the private attachment store is never checked for being private before a
   push. The doctor check exists; the preflight is still missing.
3. sase-15o: the agy trajectory allowlist is stuck at 1.0.10, so agy no-progress detection
   is silently off.
4. sase-1n0: a Muse agent re-submitted its final declaration in a loop for 20 min.
5. sase-1nl: the sudo receipt check rejects output that contains `token=`, which strands
   gates.
6. sase-1qv: sase-1pn's lost Rust-boundary landing.
7. sase-1em: the registry-rebuild flake, 5 athena hits in 14 days. Its mechanism is
   unknown, so it needs its own epic.
8. sase-1qm and sase-1he.

**Feature, memory, and flag beads (132):** not seeds. A separate one-time owner pass, as
the Nov 2 review recommended.

---

## 5. Findings to Route (I did not file these)

- **For sase-1r2 (blocking-flakes follow-through).**
  `tests/test_sudo_ledger_settlement.py::test_sudo_answer_waits_for_concurrent_reclaimer_without_failure`
  failed on apollo at `734731d603`, which **contains** the de-flake commit `26b50ca525`,
  on 11-04 at 04:17Z. It also failed on a clean base at `83cd8deffe`. The fix covered the
  sibling `defers_after_long_lock_timeout` node.
- **For sase-1qz (possible regression).** `test_app_import_budget` failed on apollo's
  dirty-tree runs on 11-03 and 11-04 (hijack phase workspaces). Its last athena failure
  was 11-02. Check whether the hijack modules pushed the source-footprint budget over.
- **Unowned (new ci/flake candidate).** CI Telemetry `coverage-contexts` crashes an xdist
  worker at
  `tests/ace/tui/test_kill_and_edit_last_launch_dispatch.py::test_inflight_handler_does_no_synchronous_disk_or_proc_store_work`
  (run 41789161504). No bead matches. File it through `/sase_new_task`, or fold it into #10.

## 6. Suggested Execution Order

| Batch | Beads                    | Shape                                    | When                                    |
| ----- | ------------------------ | ---------------------------------------- | --------------------------------------- |
| A     | sase-1r4                 | One tale, about 2 phases                 | Now                                     |
| B     | sase-zo, 1ce, 1q3        | One small-fix tale with disjoint files   | Now                                     |
| C     | sase-1al, 172, 1pw       | Test-infra tale, verified on apollo      | Now                                     |
| D     | sase-1qj, 12u (+1qi)     | Epic: host-owned epic liveness (sase-core) | Plan now; land after sase-1qz closes    |
| E     | sase-j0 (+11b, coverage crash) | Decision, then one tale             | After your budget decision              |

A, B, and C have no shared files with each other or with the live epics, so they can run
in parallel.
