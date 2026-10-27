# Stuck epics on athena: why they stalled and how to restart them (Oct 27, 2026)

I checked everything below live on Oct 27 between 13:40 and 14:45 EDT. Sources: bead-store
dumps, `sase agent list` on athena and apollo, agent artifact records, SASE's own
stranded-work collector (`sase.bead.stranded`), and GitHub Actions.

## Short answer

- **sase has 115 in-progress epic beads, but only 7 units have a live agent.** Counting
  each "Finish X" continuation chain as one unit gives 73 units. The other 66 units (102
  beads) have no live agent, and SASE's collector says "nothing resumes it" for every
  one. bob-cli has 9 more dormant units, and in all of them every phase is already closed.
- **Two live chains are blocked by fixable problems.** Fix these first (§1):
  1. sase-core v0.43.0 never reached PyPI. Its macOS wheel build outgrew the 45-minute
     job cap. This holds up `sase-1oe` and, behind it, `sase-1n6` (E2).
  2. athena has no `/usr/bin/time`. A canary failed on it, and phase `sase-1nv.5.1.4`
     ended without closing. That holds up `sase-1nv`, then `sase-1nf.10.1.9.1`, then
     `sase-1nf`. Eight waiting agents sit behind it.
- **Root cause: nothing restarts an epic whose lander or phase agent stops without
  closing it.** When a lander finds gaps, it hands off to a child epic or a tale and
  exits. 18 such chains, up to 7 levels deep, died at the leaf. The dead epics still show
  as in progress, so new `DISCOVERED ISSUE` notes keep getting routed into them: 27 in the
  last 14 days.
- **Plan:** fix the 2 live blockers. Relaunch 10 recent sase units and 8 bob-cli units
  (§3a). You make 9 calls (§3b). Triage agents close or supersede the other 46 (§3c).
  `sase-zw` settles through `sase-11h`. File 5 fixes so this stops happening (§4).

## 1. Unblock the live chains (today)

| # | Blocker and evidence | What it holds up | Action | Who |
|---|---|---|---|---|
| 1 | The sase-core `macos universal2` wheel build has grown from 36.4 min (v0.42.6) to 41.6 min (v0.42.7). Release-plz runs 40515162745 and 40537517760 then hit `timeout-minutes: 45` and were cancelled, so "publish to PyPI" was skipped. PyPI's newest is still 0.42.7, although v0.43.0 is tagged and contains pin `800caef4`. `runner-starvation-retry` skipped both runs, because a timeout isn't starvation. | `sase-1oe.4--mon` keeps reporting `CORE_LAG`, which holds up `sase-1n6.10` and `sase-1n6` | Raise the cap to 75 at sase-core `.github/workflows/release-plz.yml:284` and land it. Then merge release PR #340 (v0.43.1) so the publish runs under the new cap. Re-running the old runs reuses the 45-min cap and will probably time out again. | agent edits sase-core; you merge |
| 2 | `sase-1nv.5.1.4` canary at 02:30Z: "wrapper exit 127 … `/usr/bin/time: not found`". The phase ended without closing and has been stranded since 02:49Z. SASE alerted Oct 26 at 22:51 EDT. | `sase-1nv.5.1.{5,6,7}` and `.land` (all WAITING) → `sase-1nv` → `sase-1nf.10.1.9.1` "Check 1" → `sase-1nf.10.1` → `sase-1nf` | In the TUI: Agents → Enter on `sase-1nv.5.1.4` → **Continue (fork)**. Tell it to time the run with bash `TIMEFORMAT` or Python UTC stamps, which is its own `PROPOSED FOLLOW-UP`. Optional: `sudo apt install time` on athena. | you |
| 3 | `RELEASE_STEWARD_MERGE_ENABLED` is still unset, and the `pypi` environment still has its `master` rule (`sase-1n6.10` audit, 13:18Z today). | `sase-1n6.10--mon` (WAITING CUTOVER) | Wait for #1. Then `sase-1oe.4` raises a handover gate that actually carries out the steps. Approve it. | you |
| 4 | `sase-1nv.1` ended with `keep` on Oct 24. SASE alerted Oct 26 at 21:54 EDT. | `sase-1nv.land` | When the GC fixes in `sase-1nf.14.1` (running now) land, either Continue `sase-1nv.1` or close it as superseded by `sase-1nf.14.1`. | you or an agent |

After `sase-1nv` lands, check that phase `sase-1nf.10.1.9` actually closed. Its closure
was delegated to the `sase-1nf.10.1.9.1` landing, and no agent is assigned to that
landing now.

These are moving and need no action: `sase-1ou`, `sase-1ox`, the `sase-1nf.14.1` branch,
`sase-1oj` (its lander is running on apollo), bob-cli batch 18 (`bob-cli-an.…6.6`), and
`bob-cli-d3` (its lander is running on apollo).

## 2. Why the backlog is dormant

What SASE's collector reports for the leaves of the 66 dormant sase units:

| Leaf verdict | Units | What happened |
|---|---|---|
| stranded / unclosed | 31 | The last turn ended without closing the bead. Usually a lander wrote `LANDING INTERRUPTED`, proposed a tale or child epic, and exited, and nothing finished the close. |
| unknown / no_records | 10 | No agent records exist on athena. 7 of these ran on apollo or mac, and nothing is live there. |
| stranded / lost | 8 | The process died without writing a done record. |
| "owned", but no live agent | 8 | **Collector bug.** `z3, th, ru, 11t, kp, s5, 126, 124.8.4.3` show as owned even though their PIDs are dead or missing, so they never appear as stranded. |
| blocked / waiting | 5 | Waiting on phases whose agents are gone. |
| stranded / kept | 4 | The last turn declared `keep`. |

`sase-yx`, `sase-rt`, and `sase-y2` never ran at all. Their bead history ends at
`epic_work_preclaimed`, and no agent records exist for them.

Systemic causes:

1. **Nothing resumes unclosed work.** This is by design: "nothing relaunches a phase left
   open", and a lander's tale has to close the epic itself. The collector does detect
   these cases, but it only alerts when a *live* waiter is blocked. A fully dead chain
   never alerts. The collector also takes about 2 minutes per project.
2. **Each chain depends on its leaf.** Ancestors close only if the leaf's lander succeeds
   and walks back up the `parent_bead` links (`bd/land_epic`). The 18 dormant chains:
   `19i` (7 levels), `11e` (5), `124`/`zw`/`1hi` (4), `12w`/`1i5`/`yy`/`n4` (3), and 9
   with 2 levels.
3. **Landers keep spawning child epics for a budget that never passes.** In 2 days,
   `sase-19i` nested 6 "Finish/Cut/Pass/Land the Node Finder open budget" epics inside
   one another. Every landing re-measured open p95 at 102–569 ms against a <50 ms target.
4. **Dead epics absorb new issues.** `/sase_new_task` attaches causally related issues to
   the "active" epic. In the last 14 days, 27 `DISCOVERED ISSUE` notes went to 11 dormant
   epics, 10 of them to `sase-1jz`. The currently dormant epics hold 310 such notes in
   total.
5. **Stale ownership hides work.** Besides the 8 false "owned" leaves, the project file
   still holds 7 `ace-gate` workspace claims from Sep 20–25 whose PIDs are dead (#15,
   #26, #27, #30, #31, #43, #45).

## 3. Backlog recovery (mostly agents)

Rules:

- Act only on the chain's **leaf**. When its lander succeeds, it closes the ancestors.
- Before closing anything, run every unresolved `DISCOVERED ISSUE` / `PROPOSED FOLLOW-UP`
  note through `/sase_new_task`.
- athena's load average was 10–14 during these checks. Launch at most 5 units at a time.

### 3a. Relaunch now (recent units with real remaining work)

`sase bead work` reassigns every bead that isn't closed and never touches closed phases.
When every phase is already closed, it only relaunches the lander.

```bash
# sase workspace
sase bead work sase-1jz sase-11h sase-10h sase-sk sase-116.5 --yes
sase bead work sase-1ih sase-1j1 sase-w3 sase-1hi.10.7.6 --yes
sase bead open sase-1e3.7 && sase bead work sase-1e3 --yes  # lander: 1e3.7's commit e5ee3ca exists nowhere

# bob-cli workspace (every phase is closed, so these relaunch only the landers)
sase bead work bob-cli-9k.8 bob-cli-bj bob-cli-5w bob-cli-87 --yes
sase bead work bob-cli-3j bob-cli-8b bob-cli-66 bob-cli-28 --yes
```

`sase-11h`'s scope includes "settle the sase-zw epic chain", so don't touch `sase-zw`
separately. `bob-cli-d2`'s lander kept it open at 14:21Z today; read its last note
before acting.

### 3b. Your calls (9 units)

| Unit | Question | Suggested default |
|---|---|---|
| `sase-19i` chain (7 beads) | The Node Finder open budget is <50 ms, and every landing measured p95 at about 100 ms or more. Keep the budget? | Relax or drop it, then close the chain from the bottom up as `superseded`. File a perf task only if the latency still matters. |
| `sase-x7` (and `x7.5.1`) | Do you still want canonical-only SASE across athena, mac, and apollo? 15 phases have been open and untouched since Sep 12. | Cancel. If you still want it, re-plan it as a fresh epic. |
| `sase-yx`, `sase-rt`, `sase-y2` | These were preclaimed 48–67 days ago and never ran. Start them or drop them? | Cancel, unless the feature still matters. |
| `sase-th`, `sase-126`, `sase-10w` vs `sase-1jz` | Which epic owns "green CI"? | `sase-1jz`, since new notes go there. After harvesting, supersede the other three. `sase-10w` targets v0.17.2, which shipped long ago. |
| `sase-j7` | It was deliberately left open on Aug 11 and now works as a flake inbox (89 notes). Keep it? | Close it as superseded and move its retire criteria into one flake task. |

### 3c. Triage sweep: one agent per batch

| Batch | Units (act on the leaf) |
|---|---|
| B1 Agents tab / TUI | `124`, `132`, `13i`, `142`, `1bc`, `14j`, `11i`, `z3`, `zn`, `zu` |
| B2 Release, core, sudo, services | `1i5`, `165`, `s6`, `12w`, `11t`, `110`, `16e`, `16g`, `12o` |
| B3 Artifact links and beads | `yy`, `12y`, `t2`, `tj`, `112`, `zq`, `18i`, `1ah`, `169` |
| B4 AXE, naming, providers | `11e`, `kp`, `117`, `1ab`, `n4`, `mc`, `rr`, `zp`, `yz` |
| B5 August-era leftovers | `rj`, `s0`, `s5`, `ru`, `jx`, `lh`, `14t`, `158`, `so.5` |

All IDs carry a `sase-` prefix. Prompt for each batch (`sase run "<prompt>"`):

```text
Triage these dormant SASE epics for the owner, who authorizes you to close them and
their open phases: <units>. Nothing runs them, and the stranded-work collector confirms
nothing will resume them. For each unit, starting at its leaf:
1. `sase bead read` every member bead (-r "dormant-epic triage"), including all notes,
   especially the latest LAND AUDIT or LANDING INTERRUPTED note.
2. Check master (and sase-core where relevant) for the work the epic and its
   remaining-work notes describe.
3. Run every unresolved DISCOVERED ISSUE / PROPOSED FOLLOW-UP note through
   /sase_new_task.
4. Decide, leaf first and then each ancestor:
   DONE: retire `sase bead epic-symbols <id>`, then
   `sase bead close <id> --note "<evidence>"`.
   SUPERSEDED: `sase bead close <id> --force -R superseded --reason "<what replaced it>"`.
   STILL WANTED: file one sized task for the remainder with /sase_new_task, then close
   as superseded and cite that task.
Do not write plans, tales, or child epics, and do not launch agents. Finish with a
table: unit, decision, evidence, tasks filed or corroborated.
```

## 4. Stop it recurring (file each fix with `/sase_new_task`)

1. **Stranded supervisor.** A scheduled routine that runs the collector and raises one
   gate (Continue / Close / Supersede) for each leaf that has had no live owner for N
   hours. Today a fully dead chain alerts nobody.
2. **Route issues only to live epics.** `/sase_new_task` should attach issues only to
   epics with a live agent or recent activity, and otherwise create or corroborate a
   task.
3. **Collector accuracy and speed.** Stop reporting work as `owned` when the owner's PID
   is dead or missing (8 leaves today). Cut the 2-minute runtime per project. Release the
   7 stale `ace-gate` workspace claims.
4. **Cap child-epic depth.** At depth 2 or more, or when the same acceptance metric fails
   twice, the lander should raise a human gate instead of writing another child epic.
5. **sase-core release headroom.** Raise the macOS wheel-build time cap, and have
   `runner-starvation-retry` also cover timeouts. The pending decision `sase-14h`
   (arm64-only macOS wheel) would also shorten the build.

## Appendix: every dormant unit

Days quiet counts time since the last write to any member bead, notes included. Host is
athena unless shown.

| Unit | Leaf | Beads | Days quiet | Collector verdict | Action |
|---|---|---|---|---|---|
| `sase-124` | `sase-124.8.4.3` | 4 | 1 | owned/waiting (no live agent) | 3c triage B1 |
| `sase-1jz` | — | 1 | 1 | stranded/unclosed | 3a relaunch |
| `sase-10h` | — | 1 | 3 | stranded/unclosed | 3a relaunch lander |
| `sase-11h` | — | 1 | 7 | stranded/lost | 3a relaunch (also settles `sase-zw`) |
| `sase-12y` (apollo) | `sase-12y.4` | 2 | 7 | unknown/no_records | 3c triage B3 |
| `sase-j7` | — | 1 | 7 | stranded/lost | 3b decide |
| `sase-sk` | — | 1 | 7 | stranded/unclosed | 3a relaunch lander |
| `sase-w3` (apollo) | — | 1 | 8 | unknown/no_records | 3a relaunch lander |
| `sase-1i5` | `sase-1i5.9.1.2.1` | 3 | 8 | stranded/unclosed | 3c triage B2 |
| `sase-x7` | `sase-x7.5.1` | 2 | 14 | blocked/waiting | 3b decide |
| `sase-zw` | `sase-zw.8.7.8` | 4 | 15 | blocked/waiting | via `sase-11h` |
| `sase-1e3` (apollo) | — | 1 | 18 | unknown/no_records | 3a reopen `.7`, relaunch |
| `sase-1j1` | — | 1 | 18 | stranded/unclosed | 3a relaunch |
| `sase-1hi` (apollo) | `sase-1hi.10.7.6` | 4 | 18 | unknown/no_records | 3a relaunch lander |
| `sase-1ih` | — | 1 | 19 | stranded/unclosed | 3a relaunch |
| `sase-116` | `sase-116.5` | 2 | 20 | stranded/unclosed | 3a relaunch lander |
| `sase-yy` | `sase-yy.8.6` | 3 | 21 | stranded/unclosed | 3c triage B3 |
| `sase-z3` | — | 1 | 22 | owned/waiting (no live agent) | 3c triage B1 |
| `sase-s6` | — | 1 | 26 | stranded/unclosed | 3c triage B2 |
| `sase-1ab` | `sase-1ab.10` | 2 | 29 | stranded/unclosed | 3c triage B4 |
| `sase-1bc` | — | 1 | 29 | stranded/unclosed | 3c triage B1 |
| `sase-1ah` | — | 1 | 30 | stranded/unclosed | 3c triage B3 |
| `sase-19i` | `sase-19i.7.3.3.3.3.3` | 7 | 30 | stranded/unclosed | 3b decide |
| `sase-th` | — | 1 | 31 | owned/waiting (no live agent) | 3b decide |
| `sase-yz` | — | 1 | 31 | unknown/no_records | 3c triage B4 |
| `sase-10w` | — | 1 | 31 | stranded/lost | 3b decide |
| `sase-18i` | — | 1 | 33 | stranded/unclosed | 3c triage B3 |
| `sase-zq` | — | 1 | 34 | stranded/unclosed | 3c triage B3 |
| `sase-169` (apollo) | — | 1 | 35 | unknown/no_records | 3c triage B3 |
| `sase-16e` | — | 1 | 35 | blocked/waiting | 3c triage B2 |
| `sase-16g` | — | 1 | 35 | stranded/unclosed | 3c triage B2 |
| `sase-142` | `sase-142.5` | 2 | 35 | stranded/unclosed | 3c triage B1 |
| `sase-14j` | — | 1 | 35 | stranded/kept | 3c triage B1 |
| `sase-158` (apollo) | `sase-158.6` | 2 | 35 | unknown/no_records | 3c triage B5 |
| `sase-165` | — | 1 | 35 | stranded/kept | 3c triage B2 |
| `sase-14t` | — | 1 | 37 | stranded/unclosed | 3c triage B5 |
| `sase-13i` | — | 1 | 37 | stranded/lost | 3c triage B1 |
| `sase-12w` | `sase-12w.6.4` | 3 | 37 | stranded/lost | 3c triage B2 |
| `sase-mc` | — | 1 | 37 | stranded/unclosed | 3c triage B4 |
| `sase-12o` (apollo) | — | 1 | 39 | unknown/no_records | 3c triage B2 |
| `sase-132` | — | 1 | 39 | stranded/lost | 3c triage B1 |
| `sase-zu` (mac) | — | 1 | 39 | stranded/lost | 3c triage B1 |
| `sase-126` | — | 1 | 39 | owned/running (no live agent) | 3b decide |
| `sase-zn` (mac) | — | 1 | 40 | stranded/unclosed | 3c triage B1 |
| `sase-11e` | `sase-11e.8.6.5.4` | 5 | 40 | stranded/kept | 3c triage B4 |
| `sase-110` | — | 1 | 41 | blocked/waiting | 3c triage B2 |
| `sase-11t` | — | 1 | 41 | owned/waiting (no live agent) | 3c triage B2 |
| `sase-11i` | `sase-11i.6` | 2 | 41 | stranded/lost | 3c triage B1 |
| `sase-kp` | — | 1 | 42 | owned/monitor (no live agent) | 3c triage B4 |
| `sase-117` | `sase-117.5` | 2 | 42 | stranded/kept | 3c triage B4 |
| `sase-112` | — | 1 | 43 | stranded/unclosed | 3c triage B3 |
| `sase-n4` | `sase-n4.5.4` | 3 | 44 | unknown/no_records | 3c triage B4 |
| `sase-rr` | — | 1 | 44 | stranded/unclosed | 3c triage B4 |
| `sase-y2` | — | 1 | 44 | blocked/waiting | 3b decide |
| `sase-zp` | — | 1 | 46 | stranded/unclosed | 3c triage B4 |
| `sase-yx` | — | 1 | 48 | stranded/unclosed | 3b decide |
| `sase-rj` | — | 1 | 50 | stranded/unclosed | 3c triage B5 |
| `sase-rt` | — | 1 | 50 | stranded/unclosed | 3b decide |
| `sase-t2` | `sase-t2.7` | 2 | 54 | stranded/unclosed | 3c triage B3 |
| `sase-tj` | — | 1 | 62 | stranded/unclosed | 3c triage B3 |
| `sase-so.5` | — | 1 | 64 | unknown/no_records | 3c triage B5 |
| `sase-s0` | — | 1 | 66 | stranded/unclosed | 3c triage B5 |
| `sase-s5` | — | 1 | 66 | owned/monitor (no live agent) | 3c triage B5 |
| `sase-ru` | — | 1 | 66 | owned/waiting (no live agent) | 3c triage B5 |
| `sase-jx` | — | 1 | 72 | stranded/unclosed | 3c triage B5 |
| `sase-lh` | — | 1 | 75 | stranded/unclosed | 3c triage B5 |

bob-cli (run from the bob-cli workspace):

| Unit | Leaf | Beads | Days quiet | Collector verdict | Action |
|---|---|---|---|---|---|
| `bob-cli-d2` | — | 1 | 0 | stranded/kept | read last note first |
| `bob-cli-bj` (apollo) | — | 1 | 3 | unknown/no_records | 3a relaunch lander |
| `bob-cli-5w` (apollo) | — | 1 | 4 | unknown/no_records | 3a relaunch lander |
| `bob-cli-9k` | `bob-cli-9k.8` | 2 | 9 | stranded/kept | 3a relaunch lander |
| `bob-cli-87` | — | 1 | 9 | stranded/unclosed | 3a relaunch lander |
| `bob-cli-3j` (apollo) | — | 1 | 10 | unknown/no_records | 3a relaunch lander |
| `bob-cli-8b` (apollo) | — | 1 | 11 | unknown/no_records | 3a relaunch lander |
| `bob-cli-66` | — | 1 | 13 | stranded/kept | 3a relaunch lander |
| `bob-cli-28` | — | 1 | 20 | stranded/unclosed | 3a relaunch lander |
