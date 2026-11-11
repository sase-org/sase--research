# The next seven task beads: recover unlanded work, then stop work from stranding

_Researcher `cld`, swarm `4a`. Snapshot taken 2026-11-11, 21:00–21:55 UTC, on apollo and
athena. sase `master` was at `671ff5bde0` (release 0.19.0). Bead data comes from
`sase bead list -f json -s all` (8,466 beads). Live agents come from `sase agent list -j`
on both hosts. Run evidence comes from athena's `~/.sase/projects/*/artifacts/ace-run/202611`,
`sase tool failures -j -d 7`, and `~/.sase/logs/tui_stalls.jsonl`._

## Bottom line

**What happened to the last list.** The Nov 4 "next ten" report became epic **`sase-1ra`**.
Seven of its twelve phases closed within hours. Two of those seven never landed:

- `sase-1ra.1` is the `sase-zo` fix. `sase repo list -p sase` still exits 2 on master today.
- `sase-1ra.7` is the Python half of `sase-1r4`, the signature-skew fix.

Both phase beads say **closed · done**. Neither change is on any git ref. Both diffs are
still uncommitted in athena workspaces `sase_21` and `sase_29`.

**The rest of the epic is stuck.** Phases `.8`–`.12` and the land agent have had no live
process since athena rebooted at **2026-11-07 06:03**. That includes the boot reconciler,
which is the phase meant to fix reboot stranding. Because the land agent never ran, eight
beads that *are* fixed on master are still listed as `ready`. Two more (`sase-1by`,
`sase-1hr`) pass on master too.

**The epic backlog is mostly unstaffed.** Of 127 `in_progress` plan beads, only **8** have
a live agent (all of them release or CI epics). **39** have every child closed (zombies).
**80** have open children and nobody working on them.

**Two newer problems are live right now:**

- **`sase-1o1` is no longer latent.** A bob-cli land session on athena is carrying a
  **708,391-byte** `authored_local_request`. The Rust validator still rejects anything over
  262,144 bytes. I re-ran the binding today to confirm.
- **`sase-1nc` is a constant TUI tax.** In a 2.5-hour window today, athena's TUI logged
  **46 main-loop stalls of 5 s or more** (max 8.5 s) and **38 main-thread GC pauses of
  5 s or more**.

| #   | Bead                                    | Type · size  | One-line reason                                                                                         | How to start                                                                                     |
| --- | --------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | **sase-zo** (ride-along: sase-1r4 Python half) | bug · S      | +10, the most-corroborated open bug. A verified fix exists, but only uncommitted in athena `sase_21`     | Salvage both diffs now, before workspace retention reclaims them                                 |
| 2   | **sase-1o1**                            | bug · L      | Continuation capture grows roughly quadratically. One live session is now 2.7× over the 256 KiB cap, so long land and monitor sessions dead-end | Plan now; touches sase-core and sase                                                            |
| 3   | **sase-1qj**                            | bug · L      | The second reboot in six days stranded `sase-1ra` itself. Only epics with hand-made watchdogs came back   | Resume `sase-1ra.11.1` (plan already approved); drop its `sase-1r2` gate                         |
| 4   | **sase-1nc**                            | bug · L      | A 5–11 s TUI freeze every few minutes on athena; nobody owns TUI performance right now                 | Now; measurement-first plan                                                                     |
| 5   | **sase-12u**                            | bug · L      | 119 of 127 in-progress plans have no live agent, which hides real stalls (including `sase-1ra`)          | Comes with #3 via `sase bead work sase-1ra`; start with the report-only pass                     |
| 6   | **sase-1qm**                            | bug · L      | Host completion refuses checks that passed. It recurred on 11-07 and 11-10, and each refusal throws away a full `just check` | Now; three fresh repro runs are available                                                        |
| 7   | **sase-1re**                            | bug · M      | Finished monitors with a stale `followup_pending` own their beads forever, so the stranded detector can't see four of the zombies | Now; Rust classifier plus a root-cause check                                                    |

**One action covers most of this.** `sase bead work sase-1ra` relaunches the stranded
phases, which covers #3, #5, and the zombie half of `sase-1r4`. Run it right after #1. That
way its land agent closes the ten fixed-but-`ready` beads and the backlog is accurate
again. Before running it, re-scope `sase-1ra.11.1`'s gates (see #3).

---

## 1. What the last ten picks turned into

`sase-1ra` ("Next-ten task beads: honest update-skew failures, reboot recovery, and the
false-red test backlog") was created on Nov 4 at 22:59 UTC. Phase status:

| Phase       | Source bead(s)               | Bead status | On master?                          |
| ----------- | ---------------------------- | ----------- | ----------------------------------- |
| .1          | sase-zo                      | closed done | **No.** No commit; diff dirty in athena `sase_21` |
| .2          | sase-1ce                     | closed done | yes, `522b07a009`                     |
| .3          | sase-1q3, sase-1qe           | closed done | yes, `394ff93ff5`                     |
| .4          | sase-1pw                     | closed done | yes, `0c677302d9`                     |
| .5          | sase-1qu, sase-172, sase-1i6 | closed done | yes, `45bcf6fe39` (its `monkeypatch.undo()` regression was later fixed by sase-1r2.6) |
| .6          | sase-1al                     | closed done | yes, `02e93fd261`                     |
| .7          | sase-1r4 (Python half)       | closed done | **No.** No commit; diff dirty in athena `sase_29` |
| .8          | sase-1r4 (zombie half)       | in_progress | no live agent since the 11-07 reboot |
| .9          | sase-1r4 (core half)         | in_progress | no live agent                        |
| .10         | sase-1jd                     | in_progress | no live agent                        |
| .11 / .11.1 | sase-1qj                     | in_progress | child epic planned, then stranded    |
| .12         | sase-12u                     | in_progress | no live agent                        |

### 1.1 How two closed phases lost their code

Both runs used Muse (`muse-spark-1.3-contributor`). Each one detached its `just check` with
`-H` and staged a monitor to join it. Each monitor then crashed at launch with the same
error.

| Run                                    | Staged monitor             | Error                                                                                  |
| -------------------------------------- | -------------------------- | -------------------------------------------------------------------------------------- |
| `ace-run/202611/04/20261104180108`     | `sase-1ra.1--mon`          | `MonitorError: tool run 7603580e… already has a stop request; nothing to join`          |
| `ace-run/202611/04/20261104180113`     | `sase-1ra.7--mon` (`fwh140`) | `MonitorError: tool run dd4cfab4… already has a stop request; nothing to join`          |

What athena's records show:

- **The check was stopped before the monitor could join it.** `sase tool show` reports
  both ToolRuns as `CAUSE stop_requested` and "detached by agent … (stopped when that
  agent's turn ends unless joined)". The turn-end stop won the race against the join.
- **Completion believed the work was handed off.** The commit finalizer reported
  `status: success` with `carried_repo` evidence, meaning the dirty work was passed to the
  successor. The successor never started.
- **Nothing reopened the beads.** The agents had already closed their beads in-turn. The
  existing stranded-close guard (`sase-1oh.4`) reopens a bead only when a host commit
  *fails*. It does not cover work carried to a successor that never adopted it.
- **The work is still there.** `git status` on athena shows `sase_21` (3 files, including
  the new `tests/main/test_project_ref_canonicalization.py`) and `sase_29` (8 files,
  including `tests/test_agent_auto_restart_signature_skew_replay.py`) still dirty. Each
  run's `main_diff.txt` also holds a copy.
- **The same failure hit two more runs that day.** `18p--code` and `18v--code` (Nov 5) hit
  the identical error. Their work was recovered by hand. Nobody noticed the `sase-1ra`
  pair because their beads said done.
- **The race itself is fixed.** `c65055eff6` ("fix(monitor): preserve staged joined tool
  runs", `sase-1rg.6`, Nov 6) closed it, and no runs hit the error after Nov 5. The
  stranded-close gap remains for any successor that dies before adopting. `sase-1r4`'s
  11-03 incident (13 bob-cli files left uncommitted) is the same shape.

I recorded this as a `DISCOVERED ISSUE` note on epic `sase-1ra`, not as a new task. The bead
policy routes issues caused by an active epic to that epic, and phase `sase-1ra.8`
("settle a staged monitor whose adopter died") is the natural place for the guard.

### 1.2 Beads that are fixed but still `ready`

These beads are fixed on master but still `ready`, because the `sase-1ra` land agent that
would close them never ran:

- `sase-1ce`, `sase-1q3`, `sase-1qe`, `sase-1pw`, `sase-1qu`, `sase-172`, `sase-1i6`, `sase-1al`.

These two also pass on master now. I ran them through `sase tool run` (16 passed):

- `sase-1by` (`test_tracked_marker_path_passing_sites_are_reviewed`).
- `sase-1hr` (`test_macro_string_literals_avoid_xprompt_terms`).

The pass is good news, but it also means any "what's ready?" ranking keeps resurfacing
finished work. That's why none of these appear in my seven.

---

## 2. What is live right now (conflict screen)

| Host   | Live owner                                                                                 | Area                                                       |
| ------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| athena | `sase-1rq.2.1` and its nested contention epics (`…4.1.5.3.1`), plus `sase-1rq.land`        | Hosted contention lane; every red sase workflow           |
| athena | `sase-1r2.land` waiting on `sase-1r2.6`                                                    | One fully green Full CI run (red at `671ff5bde0`: `tests/ace/tui/test_launch_context_source.py:620`) |
| athena | `sase-1n6.11.land` and `.4--mon-1`                                                         | Release steward (E2)                                       |
| athena | `sase-1s7.7.*` (DONE today), `chop.refresh_docs.sase`, and `1bk` (queued, prompt unknown)  | 0.19.0 release, docs refresh                               |
| athena | ~30 bob-cli agents                                                                         | Another project, but its land sessions are hitting #2 and #6 |
| apollo | `research.4a.*`, `dd--code` (bob-cli)                                                      | This swarm; another project                                |

None of the seven picks touch the files those owners are changing:

- `repo_handler_common.py` and `workspace_handler_context.py` (#1)
- `continuation_capture/*` and sase-core `continuation/schema.rs` (#2)
- boot recovery (#3)
- `ace/tui/util/gc_policy.py` (#4)
- sase-core `continuation/completion_eval.rs` (#6)
- sase-core `stranded_work/classify.rs` (#7)

Flake beads are another matter. The contention epic (`sase-1rq.2.1.4.*`) is actively
triaging the contention flake family and has read `sase-1s2`/`sase-1s4` repeatedly, so
**I left those flakes to it.**

#2, #6, and #7 need sase-core changes, so they need a published core and a pin move. Line
those up with the steward train (`sase-1n6.11`) rather than racing it.

**Re-run `sase agent list -j` locally and on athena before launching anything.**

---

## 3. The ranked list

### 1 · sase-zo: salvage the verified `-p <display name>` fix (ride-along: sase-1r4's Python half)

**Why first:**

- **It is the most-corroborated open bug (+10)** and still reproduces on master:

  ```text
  $ sase repo list -p sase
  Project 'sase' has no WORKSPACE_DIR in /home/bryan/.sase/projects/sase/sase.sase.
  ```

- **It misleads agents daily.** Agents are told to use `sase repo`, and decision
  `project-labels-never-keys` makes the display name the thing every surface shows them.
- **The work is already done.** A complete, verified fix exists:
  - `-p` is canonicalized through the project registry, accepting a key, display name, or
    alias, case-insensitively. Ambiguous names exit 2 and list the candidates.
  - It has 7 new regression tests, 66 related tests pass, and every lint stage was green.
- **It is the cheapest high-impact item in the backlog**, because the fix only needs to
  reach master.
- **It is time-sensitive.** The two workspaces are held, but the disk-retention work
  (`sase-zw` chain) exists precisely to reclaim old held state. Every day risks losing the
  diffs.

**Ride-along.** Salvage `sase-1ra.7`'s 8-file diff in `sase_29` the same way. It adds
signature-mismatch shapes (`unexpected keyword argument` and friends) to
`_SKEW_MESSAGE_PATTERNS`, gated on the runner's code having moved. It also adds
`source_revision_moved()` and the checkout-moved explanation. Master still has only the
import-shaped patterns (`runner_failure_facts.py` lines 43–56). The skew deaths themselves
haven't recurred since 11-03 (three error reports from Nov 1–3, none after), so this is
cheap insurance rather than an emergency.

**How:**

1. Rebase each `main_diff.txt` onto master. The bases were `99932634cd` (`sase_21`) and
   `0cc9fad474` (`sase_29`). `workspace_handler_context.py` and `source_skew.py` may have
   drifted.
2. Re-run the focused tests, then `just check` under `sase tool run`, and commit with
   `SASE_BEAD=sase-zo` / `sase-1r4`.
3. Extend phase `sase-1ra.8`. When a turn's commit obligation was `carried_repo` to a staged
   successor that never adopted it, reopen the predecessor's closed bead with a
   `STITCH FAILED`-style note naming the held workspace, mirroring `sase-1oh.4`. This is the
   guard whose absence lost these two fixes.

**Done when:**

- `sase repo list -p sase`, `-p SASE`, and `-p gh_sase-org__sase` all resolve.
- The signature-skew replay test is on master.
- `sase_21` and `sase_29` are clean.
- A fixture where the carried successor never launches leaves the predecessor's bead
  reopened, not done.

### 2 · sase-1o1: continuation capture grows past its cap and dead-ends long sessions

**Why second:**

- **The cause.** `persist_agent_delta` records the `#fork`-expanded step prompt as
  `authored_local_request`. Replay then renders it as the parent's user block, so every
  session member nests all of its ancestry.
- **The cap is still enforced.** I called `validate_agent_delta` through the installed
  binding today:

  | `authored_local_request` size | Result                                       |
  | ----------------------------- | -------------------------------------------- |
  | 200,000 bytes                 | accepted                                     |
  | 270,000 bytes                 | `authored_local_request is too large … exceeds 262144` |
  | 708,391 bytes                 | rejected                                     |

- **The trend.**
  - **Oct 24 (bead filed):** largest session 126 KB. "Latent, at roughly half the cap."
  - **Nov 6:** bob-cli `hj.6--r` at **254,178 bytes**, 97% of the cap.
  - **Nov 11:** bob-cli `kb.land--c`, a live land-agent session member, has a prepared
    prompt carrying **708,391 bytes**. When its turn ends, agent-delta capture fails. The
    next monitor follow-up then settles `not-launchable` until someone runs
    `sase monitor resume` by hand.
- **It hits the sessions that matter most.** Long land and monitor sessions are now how
  every epic lands, and growth is superlinear in session length. Nothing on master has
  touched `authored_local_request` since the bead was filed.

**Recommended solution:**

- Capture only the local, pre-fork request.
- Have replay walk the parent chain instead of re-reading nested authored text. Storing
  the field by text ref, like segments, is the fallback.
- Keep fork-replay output byte-stable. Add a 20-member regression test that stays under
  the cap.
- Add a one-shot repair for in-flight sessions that are already over the cap. At minimum,
  emit an explicit capture error instead of a silent `not-launchable` dead-end.

The validator lives in sase-core, so this needs a core release and pin.

### 3 · sase-1qj: reboot recovery, by resuming the plan that already exists

**Why:**

- **Two reboots in six days.**
  - **11-01:** 27 FAILED waiters (16 land, 11 phase). They were still unrecovered 2.5
    days later. 7 of 8 manual relaunches died on "already in_progress and assigned".
  - **11-07 06:03:** athena rebooted again (`who -b`). Every epic that came back had a
    hand-made relaunch: `sase-1r2.land` at 06:27, `sase-1n6.11.land` at 06:29, and
    `sase-1rq.land` at 07:49.
- **The reboot stranded the epic built to fix reboots.** `sase-1ra` came back with nothing.
  Its `sase-1ra.11.1.1` agent had handed itself to a `-w 0` monitor that polled its gates
  every 15 minutes, and that monitor did not survive the reboot either.
- **The +1 evidence explains why waiters die without a trace.** systemd SIGKILLed waiters
  after "Stopping timed out". The runner's own soft SIGTERM handler only sets a flag, so a
  waiter in `%wait` never writes `done.json` before the kill.

**The plan is already written and approved.** `sase-1ra.11.1` has five phases:

- Rust boot-recovery policy
- replacing claims held by owners that died in a previous boot
- durable per-epic recovery with deduplicated notices
- AXE startup reconciliation
- incident verification

It is gated on `sase-1qz.6.1`, `sase-1qz.7`, `sase-1r2`, and `sase-1ra.9`. The two
`sase-1qz` gates are now **closed**. `sase-1r2` is down to its last phase (one green Full
CI run), which has nothing to do with boot recovery. That gate is overly broad and should
be dropped or narrowed to `sase-1r2.5` (published core, already closed).

**Also recommended:** have the runner's `%wait` loop honor SIGTERM by writing a terminal
"interrupted by shutdown" marker within systemd's stop timeout. That turns "dead PID, no
`done.json`" into a state the reconciler can trust.

### 4 · sase-1nc: the TUI freezes for 5–11 s every few minutes

**Why it ranks this high.** This is the most user-facing problem in the backlog, and
nobody owns it. Every TUI-performance epic (`sase-132`, `sase-124`, `sase-zn`) is stalled
or a zombie. Measured today from `tui_stalls.jsonl`:

| Host   | Log window     | Main-loop stalls ≥ 5 s | GC pauses ≥ 5 s                      | Max      |
| ------ | -------------- | ---------------------- | ------------------------------------ | -------- |
| athena | 14:28–16:55 EST | **46**                 | 38, all on `MainThread` (36 `idle`, 2 `rss_backstop`) | 8.5 s    |
| apollo | last 24 h      | 8                      | 17 (10 on `MainThread`, all `automatic`) | 11.4 s   |

On athena that works out to about one ≥ 5 s freeze every three minutes.

**What the measurements suggest:**

- The `idle` trigger means the policy starts a gen-2 collection while you're idle and
  can't bound it when you start typing again. That is exactly the bead's
  "idle gating does not bound a collection after input resumes."
- The apollo rows show CPython's *automatic* collector also stopping the main thread for
  more than 5 s. So the root problem is heap size and cyclic garbage, not only the policy.

**Plan.** The bead's own plan is right: find the retained cyclic producer
(fleet projection, recurring snapshots, and the capacity walk heaps that `sase-1q9`
links), compare Python 3.14.7 on athena with 3.12.3 on apollo, and do not just raise
thresholds. **Rotate the stall log less aggressively first.** Athena's log covers only
the last 2.5 hours, which makes the "before and after" comparison the plan needs
impossible.

### 5 · sase-12u: zombie and unstaffed epics hide real stalls

**Why.** I classified every `in_progress` plan bead against both hosts' live agents:

| Class                                              | Count | Examples                                                                      |
| -------------------------------------------------- | ----- | ----------------------------------------------------------------------------- |
| Active (a live agent in the epic)                  | **8** | sase-1rq.*, sase-1r2, sase-1n6/.11                                            |
| Zombie (every child closed, no live agent)         | **39** | sase-lh (Aug 13), sase-zn, sase-126, sase-kp, sase-th (Nov 10), sase-j7        |
| Stalled (open children, no live agent)             | **80** | sase-1ra, sase-x7 (10 open phases), sase-zw.8.7.8 (7), sase-1nf, sase-1i5 (the *previous* "top ten" epic) |

This is a fleet whose in-progress list is almost all noise. That noise is why `sase-1ra`
could sit idle for four days without anyone noticing. Two consecutive "highest-impact
task" epics, `sase-1i5` (Oct 17) and `sase-1ra` (Nov 4), are both sitting in the stalled
column.

**Recommended solution (already scoped as `sase-1ra.12`):**

1. **A report-only pass.** List each zombie and stalled epic with its last land outcome
   and last live member, and let the owner decide each row: relaunch, close, or snooze.
   Do not cascade-close.
2. **A host-owned invariant in sase-core.** When every child of a plan is closed and no
   land agent is live, relaunch the land agent. When an epic has open children and no
   live member for more than N hours, raise one inbox notice. `sase-1nz` (notify on
   first stranding) is the natural delivery path.

### 6 · sase-1qm: completion refuses checks that passed

**Why.** A refusal throws away a full `just check` (30–60 minutes under athena's load)
and costs the agent another turn. The bead was filed from one instance on 11-01. I found
more on athena:

- **Pure `stale_worktree_fingerprint` refusals in sase** (the bead's exact shape):
  `19b--mon-0` on 11-07 and `1au--mon-0` on 11-10. Both went to `recovery`.
- **Seven bob-cli monitors this month, six of them today** (`k3.2.1.3`, `k7.1`,
  `k3.4.1.2`, `ka.2`, `kd.2`, `kf.6`), were refused with `stale_worktree_fingerprint`
  *plus* `missing_required_stage:{formatting,ruff,mypy,validation,scoped_tests}`. These
  may be legitimate (a monitored command that wasn't a full check), but six in one day
  is worth confirming as part of the same investigation.
- **The monthly count is rising:** 5 runs in October, 11 so far in November.

**Recommended solution:**

- Diff the sealed observation against the host-time observation for the three sase runs.
  The bead suspects a cross-repo scope mismatch: the intent covers main plus sase-core.
- Make the refusal record name *which* fingerprint component differed. Right now the
  agent can only guess.
- Then fix the scope or the time-of-check.

The location is sase-core `continuation/completion_eval.rs` plus
`src/sase/monitor/followup_prompt.py`.

### 7 · sase-1re: done monitors own their beads forever

**Why.**

- **The bug.** A monitor member that is `done` but still reports
  `followup_pending = true` (a stale `next_action` with no `followup_outcome`) is
  classified `owned/monitor` forever. Its bead therefore never shows as STRANDED.
- **It is confirmed on live data.** It was reproduced on 11-05, after the
  delivered-staged-handoff fix, for `sase-1ih.2`, `sase-kp`, `sase-ru.6`, and `sase-s5`.
  `sase-kp` and `sase-s5` are in my zombie list. `sase-ru` (open phases) is in my stalled
  list.
- **It undermines #3 and #5.** The stranded detector and the ACE stranded view are what
  should surface these stalls, and this classifier blind spot hides them.

**Recommended solution.** It is a medium-size change in sase-core
`stranded_work/classify.rs`. Treat a cold done member with no outcome as stranded *after*
the bead's requested root-cause check: why did the follow-up never launch?

---

## 4. Considered and not picked

| Bead(s)                         | Why not in the seven                                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| sase-1s2 (S), sase-1s4 (L)      | Real and precise. The runner installs a soft SIGTERM handler at import, which 80 test files inherit. But production impact is mostly pytest teardown, and the live contention epic is actively tracking both |
| sase-1n0 (Muse final-declaration loop) | No recurrence: zero November runs on athena had ≥ 5 accepted final submissions in one turn            |
| Flakes: sase-lk (+13), sase-xo (+9), sase-1em (+6, +1 today), sase-1s1 (+2 today), sase-1pr | The contention epic (`sase-1rq.2.1.4.*`) is systematically working this family. Corroborate there rather than launching parallel fixers. `test_production_paths_keep_parity_with_marker_only_population` failed in 6 runs from 11-05 to 11-10 **with no bead**; flag it to that epic |
| sase-j0 (+38)                   | An owner decision, not agent work (see below)                                                            |
| sase-1jf, sase-1jd              | Already owned by stranded `sase-1ra` phases; resuming the epic covers sase-1jd                          |
| sase-1r7, sase-167, sase-1db    | Real, but no incident since the last ranking                                                            |
| sase-spotify onboarding storm   | Resolved: no `agent_publication` digests on athena since 11-08 08:45                                    |

## 5. Owner decisions (not agent work)

- **Resume `sase-1ra`.** First trim `sase-1ra.11.1`'s gate list (drop `sase-1r2`). Then run
  `sase bead work sase-1ra`. Its land agent will close the ten fixed-but-`ready` beads. If
  you would rather not relaunch the whole epic, close those ten by hand with a note
  pointing at the master commits in §1.
- **sase-j0 (+38).** It is still `in_progress` under a holder that died on 10-26.
  `check-full` is now explicit-only (decision `check-full-is-explicit`). Either retire the
  hard test-cost budgets or re-key them per worker, and release the dead claim.
- **The 80 stalled epics.** The `sase-12u` report gives you the list. Many (for example
  `sase-x7`'s canonical-only migration, with 10 open phases) are decisions about whether
  you still want that work, not engineering.

## Method notes and caveats

- **Live-agent classification is by name prefix**, matching agent names against bead
  IDs. A waiting agent registered under a different name would count as "no live agent".
  I spot-checked `sase-1ra` by hand.
- **I read the GC and stall data from rotating logs.** Athena's covers only about 2.5
  hours, so its rate is a sample, not a weekly average.
- **The 708 KB figure is the prepared-prompt field of an in-flight run.** I verified that
  the validator rejects that size. I did not wait for that run's turn to end and fail
  capture.
- **I did not open the sase-core checkout.** Core-side claims (validator cap, classifier
  location) come from the beads plus a live call to the installed binding.
