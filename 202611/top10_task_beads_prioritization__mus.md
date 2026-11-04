# Top task beads to work next — prioritized research (mus)

Date: 2026-11-04. Researcher: mus (5-researcher swarm, independent report).
Scope: this project's task beads in the `sase` project bead store, ranked by
importance / impact for hands-on work starting now.

## Method

- Listed the live bead store: 8325 total beads; 12 open, 375 ready, 231
  in_progress, 7704 closed (1397 tasks total). `sase bead ready` currently
  returns ~150 unblocked ready task beads; `sase bead list --type task` shows
  ~200 active tasks with 191 hidden behind the limit.
- Read the full descriptions (via `sase bead read <id> -r`) of ~15
  high-impact candidates across CI/verification, agent reliability, data loss,
  publication, performance, and security.
- Reviewed running agents on this machine (`sase agent list -j`, 19 rows) and
  on athena over SSH (`ssh athena "sase agent list -j"`, 33 rows), plus
  `sase agent show` for the key runners and `sase bead read` for the active
  epics, to exclude anything an ongoing epic already owns.
- Deliberately did not open, read, or seek out any peer swarm report
  (`__cdx.md` / `__cld.md` / `__grk.md` / `__gem.md`); conclusions below are
  my own. I only listed filenames in `202611/` to pick a non-colliding name.

## Running-agent / conflict review

### This machine (apollo checkout, 19 agent rows)

- `cd--code` RUNNING (sase project, ws 10): implementing approved plan
  `202611/codex_exec_final_answer_integrity.md`. Narrow codex-exec scope;
  no conflict with the beads below.
- `bob-cli-h2.4` RUNNING plus `bob-cli-h2.5`, `bob-cli-h2.6`,
  `bob-cli-h2.land`, `bob-cli-h0.land` (bob-cli project clan work): different
  project (`bob-cli`), so no conflict with sase task beads.
- `research.3a.*` (cdx, cld, grk, gem, mus=self) RUNNING plus WAITING
  `research.3a.linker/image/final`: this research swarm itself. No bead work.
- Only 1 task bead is `in_progress` locally: `sase-j0` (just check-full red
  on master, untyped, large, +38). It has no live worker attached right now,
  but it overlaps the active green-CI epics (below), so I do **not**
  recommend starting it directly — see sequencing notes.

### athena (33 agent rows via SSH)

Active sase epics with live workers — treat as owned territory, sequence
around them:

1. `sase-1qz` Agent Hijack (IN_PROGRESS; phases .6/.7/.9/.10/.11 in
   progress). Owns agent stop/recovery/hijack UX. None of my top 10 touches
   hijack code, so no conflict.
2. `sase-1r8` Stop agent-publication false blocks (IN_PROGRESS; phases
   .4/.5/.6 in progress, plus an INSTALLING monitor `sase-1r8.4--mon`).
   Owns scanner-rules versioning, the drain loop, and parking of
   protection-withheld requests. Adjacent to my #9 (`sase-1or`, GH013
   unattributed rejections in the same publisher): different cause (secret
   rejections vs protection withholds) but same drain/replay code. Sequence
   #9 after `sase-1r8.5` lands or coordinate with its lander.
3. `sase-1r2` Green Full CI + v0.19.0 to PyPI (IN_PROGRESS; phases
   .5/.6/.7/.8 in progress, WAITING PYPI/GITHUB monitors `sase-1r2.5--mon`,
   `sase-1n6.11.4--mon`). Owns the current green-CI run and the release.
   Do not start a competing Full CI investigation while `sase-1r2.6` is
   measuring its green run. My CI-infra picks (#3 `sase-x4`, #4 `sase-1pw`)
   are follow-ups: queue them to start after `sase-1r2.6` reports, or work
   them as owned follow-ups of that epic.
4. `sase-1n6.11` E2 steward release (IN_PROGRESS; phase .4 in progress).
   Owns release-steward merge/train. The install-canary beads (`sase-1qw`
   family-install red, `sase-1r0` install_broken macos) sit in the release
   lane this epic and `sase-1r2` are driving through — check those epics'
   status before touching install reds (I excluded them from the top 10 for
   this reason).
- Also on athena: `18b`, `18a`, `sase-1qz.6.1.2--plan`, `bob-cli-h4.1/.2/.3`,
  `185--3` RUNNING. The bob-cli rows are the other project; the sase rows
  belong to the epics above.
- Closed/landed context: `sase-zn` (ACE typing lag on athena) is fully
  closed including child epic `sase-zn.9`, so typing-lag follow-ups are fair
  game but did not make my top 10. `sase-126` (Restore Master Gate) shows
  all four phases closed; `sase-1r2` is its live successor.

## Selection criteria

Ranked by: (a) blocks landing, verification, or release; (b) silent
data-loss or zombie-state risk; (c) frequency × blast radius on athena
(the main agent host); (d) freshness (recent regressions first where impact
ties); (e) independence from active-epic owned work. Pure flake-class beads
with passing-in-isolation signatures were deprioritized unless they block a
gate right now.

## Ranked list: 10 task beads to work

### 1. sase-1r4 — Signature-skew TypeErrors escape classification, leave staged monitors as zombies (READY, L, bug)

Justification: freshest silent-death report (filed 21h ago after three
athena runners died in one live-update window). Two gaps compound: the
update-skew healer and the swap explainer both miss `TypeError:
... unexpected keyword argument` shapes, so `skew_suspect=false`,
`agent_auto_restart` logs `nothing_eligible`, and nobody recovers. Worse,
the crashed agent's pre-created monitor sits in `monitor_state=staged`
with `pid=null` for 6+ hours — a zombie that still reads as Running — and
the dead row vanishes from `sase agent list -a`. This is the exact
"silent agent failure" class Bryan just researched
(`athena_silent_agent_failures_live_update_skew.md`).

Recommended solution: (i) add signature-mismatch shapes to
`src/sase/axe/runner_failure_facts.py` (`unexpected keyword argument`,
`missing N required ... argument`, `takes N positional arguments but M were
given`) and to `code_swap_explanation()` in `src/sase/ace/scheduler/...`
(`source_skew.py`), keyed off the existing W1 (boot code_identity !=
current) and W3 (`git log -S` names the mover) proofs; (ii) sweep
failed-adoption staged monitors into a terminal/failed state with a
`skew_victim` marker instead of leaving them staged forever; (iii) route
classified rows to the existing resume-in-place path (`sase-1jf`) and the
preload path (`sase-1jd`)/pinning path (`sase-1je`) as linked. Verify with a
staged-adoption fixture that renames a kwarg mid-run plus a zombie-monitor
regression test.

### 2. sase-1qj — Host restart strands %w waiters and land agents with no auto-recovery (READY, L, bug, +1 corroborated)

Justification: every host reboot stalls ~16 epic clans until manual `sase
bead work` per epic (27 FAILED waiters observed 11-01; still unrecovered
2.5 days later per the +1, with dead owners holding bead claims so fresh
`.f0` agents die with "already in_progress and assigned"). Auto-restart
covers live updates only. Reboots are routine (kernel updates, watchdog);
this is the highest-frequency total-stall risk.

Recommended solution: a boot-time steward (systemd unit or first-tick
reconciler) that enumerates agents whose PIDs are gone with no `done.json`,
releases dead bead claims, and requeues `%w`-waiters and land agents in
their original epic order; add a claim-lease so a dead owner can never pin
a bead past reboot. Verify by reboot-drill on a scratch epic with
waiters + land agent, asserting automatic requeue with no "already
in_progress" deaths.

### 3. sase-x4 — `just check-full` hangs silently at test-cost; holder watchdog never self-reclaims (OPEN, L, bug)

Justification: `just check-full` is the monitor-only landing gate, and this
hang burns the landing monitor's whole budget (2h and 5h timeouts observed
during the `sase-wn.10` landing) while wedging the host-wide suite-gate
lease for sibling workspaces. Phase tests passed in 11.5s in the same tree,
so the signal is pure infra loss. Deterministic reclaim test already
tracked in `sase-w7`.

Recommended solution: heartbeat-timeout + watchdog self-reclaim for the
cost-lease holder (fix the `sase-w7`
`test_waiter_reclaims_stale_live_holder` path first), plus periodic
progress output on the `test-cost` step so silence is diagnosable. Sequence
after `sase-1r2.6`'s green run so two investigators are not fighting over
the same lane. Verify with a contended-lease hang fixture and a live
`just check-full` under contention.

### 4. sase-1pw — Pytest worker-token waiters starve; 4-token waiter times out after 45m (READY, M, bug)

Justification: under sustained concurrent checks on athena, a scoped `just
check` can wait 45 minutes and exit 4 without running a single test while
later arrivals take freed tokens (89 "Waiting for grant" lines in evidence;
holder set rotated twice ahead of the waiter). Each starvation wastes a full
agent verification cycle. Same lease family as #3 but a distinct fairness
defect (waiter ordering, not holder reclaim).

Recommended solution: FIFO tickets/arrival-order reservations in
`tests/_suite_gate_lease.py` `WorkerTokenLease.acquire` (reserve next-freed
tokens for the longest waiter instead of greedy poll-wins). Unit-test with a
fake clock (waiter A starts, B arrives later, freed tokens go to A).
Sequence with #3 — both touch the suite-gate lease; land together or in
#3-then-#4 order.

### 5. sase-1qm — Prepared-completion fingerprint refusal after a passing check (READY, L, bug)

Justification: a phase agent passed `just check` (exit 0, dirty 19→19,
fingerprints matching on both repos) and host completion still refused the
unchanged intent with `stale_worktree_fingerprint`, forcing a manual fresh
declaration. Any recurrence taxes every landing with a confusing false
refusal at the last step. Root cause unconfirmed but localized
(`completion_eval.rs`, `followup_prompt.py`).

Recommended solution: align the sealed observation scope with the evaluated
scope for cross-repo intents (main + sase-core), or emit a fingerprint-diff
bundle on refusal (which repo, which paths/hashes diverged, time-of-check
vs sealed values) so the next refusal is actionable. Verify with the
recorded passing ToolRun fingerprints replayed against the refusal path.

### 6. sase-11d — Stale comment snapshots erase concurrent suffix updates (READY, M, bug)

Justification: deterministic lost update reproduced through the real parser:
two `set_comment_suffix` calls from stale snapshots, second erases the
first (running-agent marker or ZOMBIE error suffix lost) even under the
write lock, because the whole COMMENTS block is rebuilt from caller state.
Production consequence is erased running/ZOMBIE markers and duplicate
launches. Bounded, well-localized correctness work.

Recommended solution: transform current state under the owner lock (merge
suffix updates entry-wise, preserve disjoint entries) instead of wholesale
replace; cover stale caller lists and the analogous `remove_comment_entry`
fast path; keep shared semantics in the Rust core / owner API per the
boundary rule. Verify with the two-snapshot Alice/Bob interleaving as a
regression test.

### 7. sase-1hk — Full-history artifact-index query keeps `bead_claim_checks` at ~33s (READY, L, bug)

Justification: measured 11–12s full-history `query_agent_artifact_index`
(15.7k rows) + decode/add_many overhead on athena, paid every 10s `waits`
tick by `bead_claim_checks` (~33s/run), delaying claim reconciliation and
`epic_launch_flush`. Every other caller of the full-history query pays the
same 12s tax on a long-lived host. `sase-1hf` already moved sibling callers
off this route; this is the leftover.

Recommended solution (sase-core side per the Rust boundary): serve a narrow
pre-launch/claim projection or active-tier-only query for
`query_ace_run_index_records` in `_chop_bead_claim_scan.py`, as `sase-1hf`
did for `wait_checks`; alternatively fix the full-history query's
per-call decode/scan cost. Verify by timing the claim scan before/after on
a 15k-artifact host against the 10s `waits` budget.

### 8. sase-1qx — Commit-stage finalizer latency misses 60s targets (READY, L, bug)

Justification: installed re-prove (73 runs) shows 3.4× improvement yet
median provider_done→done 101s and finalizer p95 ~178–201s vs the 60s
targets. The residual is localized: `bead_pages` median 38s + `just fix`
hook median 21s, not the backgrounded hood enqueue (0.6s). Every athena
landing pays ~40s of avoidable synchronous commit-stage time.

Recommended solution: slim the `bead_pages` render/index substep and trim
or move the `just fix` before-commit hook off the synchronous commit path;
keep the background-enqueue win. Verify against the same 73-run
methodology (`/tmp/measure_reprove.py` evidence path in the bead) until
median <60s and p95 <60s.

### 9. sase-1or — Unattributed GH013 rejections re-push the same batch every drain (READY, M, bug)

Justification: when a secret-scan rejection names no path,
`recover_publication_push` returns `rebuild_clean` with empty
`blocked_paths`, both callers rebuild and re-push the identical batch, and
every future drain repeats the two rejected pushes — clean units for that
project never publish until the content leaves some other way. Bounded per
drain but unbounded over time; the plan that created it explicitly required
isolation.

Recommended solution: after an unattributed rejection + reset, replay
independently valid units (e.g. one hood per commit/push) with bounded
attempts per drain and park only the still-rejected unit with sanitized
accounting; never blame a clean row. Coordinate with the `sase-1r8.5` lander
(park protection-withheld requests) — same drain code, different trigger —
and land after `sase-1r8.5` or as a joint change. Regression test is the
bead's `test_no_location_rejection_resets_without_blaming_a_clean_row`
extended to assert isolation.

### 10. sase-vb — Dead-agent rows clog the active tier and starve DONE history (READY, L, bug, +2)

Justification: 3,180 of 10,426 index rows match the active predicate on a
real host (590 non-dismissed), but PID filtering later drops all but ~14
live agents — while the windowed read budgets completed candidates as
`requested_limit − active_candidates`, saturating to 0 DONE rows against a
126 viewport. The Agents tab shows no DONE history after restart. Well
measured, user-visible every day.

Recommended solution: repair the windowed budget math (this bead's scoped
fix) without terminalizing rows that still carry `workflow_state.json` or
waiting markers — that liveness design is explicitly deferred to `sase-zd`.
Verify with a 10k-row fixture (thousands of pidless no-done rows) asserting
DONE rows still fill the viewport.

## Explicitly excluded (and why)

- `sase-j0` (check-full red budgets, IN_PROGRESS, +38): real, but it is the
  standing in-progress task and its budget-recalibration overlaps the live
  `sase-1r2` green-CI epic. Let `sase-1r2.6` finish its measured run first.
- `sase-1qw` / `sase-1r0` (install-canary red, install_broken macos, both
  OPEN github mirrors): high impact if they persist, but the release lane is
  hot (`sase-1r2` driving v0.19.0, `sase-1n6.11` steward release). Confirm
  against those epics' next green before opening a parallel install
  investigation.
- `sase-11w` (Telegram inbound hardening): genuine robustness gaps, but
  deliberately deferred by owner decision with acceptable ack latency; less
  urgent than silent deaths and wedged gates.
- `sase-1ot` (rotate/purge 27 historical scanner hits): owner-approved and
  worth doing, but one-shot hygiene ranked just below the publication
  unblock (#9) it is linked to; do it with #9.
- `sase-zn` / `sase-126`: already closed — no work needed.
- Pure full-lane flakes (e.g. `sase-12b/c/d/e`, `sase-137/13c`, `sase-15k`,
  `sase-18u`, `sase-19b/t/u`): individually low leverage vs the systemic
  gate/lease fixes above; several are already covered by closed
  `sase-1r2.3/.4` lane work.

## Suggested work order

1. #1 (skew zombies) and #2 (reboot recovery) — stop silent losses first.
2. #3 + #4 (lease reclaim + token fairness) after `sase-1r2.6` reports.
3. #5 (completion fingerprint) alongside any landing work — it pays back
   immediately.
4. #6 (comment lost-update) — small, deterministic, independent.
5. #7 + #8 (claim-scan scale, commit latency) — athena throughput.
6. #9 + #10 (publication isolation, DONE history) — after `sase-1r8.5`
   for #9; #10 anytime.
