# Task-bead backlog epic chain review: five rounds from sase-1pm to sase-1qt

Swarm report by researcher `mus`. Written independently; no peer report
(`__cdx` / `__cld` / `__grk` / `__gem`) was located, opened, or consulted.
Sources are the epic beads themselves, their plan files, the histories of two
repeatedly closed task beads, and current bead-store counts.

## Scope and method

The user ran "5 batches of task bead cleanup rounds with an epic for each
round". The five are the `task_backlog_epic_1..5` chain:

- sase-1pm (epic 1) -> sase-1pn (epic 2) -> sase-1pu (epic 3) ->
  sase-1qn (epic 4) -> sase-1qt (epic 5), 2026-10-29 through 2026-11-02.

Two precursor epics used the same mechanism under an older name and are
included as prologue: sase-1oh ("backlog, epic 1", 2026-10-26) and sase-1ou
("backlog, epic 2", 2026-10-27). The breadcrumb in the request (the sase-1qt
bead) leads to plan `sase/repos/plans/202611/task_backlog_epic_5.md`, whose
PARENT link walks back through the whole chain, so every round below is
verified from primary sources, not reconstructed from memory.

Evidence consulted, all via audited `sase bead read -r`:

- All seven epic beads with every note (closeout, triage, and landing notes).
- All five `task_backlog_epic_*.md` plan files plus the two precursor plans.
- `sase bead history` tails for sase-o7 and sase-1ic (both were closed twice).
- Current counts: `sase bead list -t task -n 0` (382 non-closed) and
  `sase bead stats`.

Limits: no test or check was re-run; all verification claims below are the
landers' recorded evidence (ToolRun IDs and SHAs are quoted so they can be
re-checked). The linked `sase-core` and `sase--agents` checkouts were not
opened.

## The chain at a glance

| Epic | Window | Seeds worked | Outcome |
| ---- | ------ | ------------ | ------- |
| sase-1pm (epic 1) | 10-29 01:44 -> 14:33 (~13 h) | sase-1nh, sase-1ll, sase-1p5, sase-1ic, sase-1cb | All 5 closed; child rebase-gate epic; reviewer-approved decisions |
| sase-1pn (epic 2) | 10-29 10:44 -> 23:08 (~12.5 h) | sase-163, sase-1p9, sase-o7, sase-1cs+sase-vr | All 5 closed; landing tale; filed sase-1po/1pp/1pq/1pr; +1 on sase-19m, sase-1oo; closed sase-1pg |
| sase-1pu (epic 3) | 10-29 19:19 -> 11-01 19:23 (~72 h) | sase-1os, sase-12v, sase-1mv, sase-120, sase-1cc | All 5 closed; nested epics .5.1/.5.1.5; closed sase-rh as duplicate of sase-o7; epic-caused breakage repaired in-epic |
| sase-1qn (epic 4) | 11-01 14:34 -> 22:50 (~8 h) | sase-o7, sase-1ic, sase-1gz, sase-13a, sase-19m | All 5 closed; fastest clean round; only duplicate closure (sase-rh -> sase-o7) |
| sase-1qt (epic 5) | 11-01 18:08 -> 11-02 03:39, reopened, reclosed 11-02 14:28 (~20 h total) | sase-1ia, sase-1l3, sase-1hy, sase-xo, sase-15h (+ related sase-1i9) | All 6 closed, but first landing's integration repairs were lost to infra failure; redo tale required |
| sase-1oh (precursor 1) | 10-26 -> 10-27 (~21 h) | sase-1of, sase-14r, sase-1nw, sase-yo, sase-1dp | All 5 closed; dormant-flakes sweep closed ~28 quiet flakes; filed sase-1ot |
| sase-1ou (precursor 2) | 10-27 -> 10-30 (~3 d) | sase-1og, sase-18t, sase-12f, sase-1a7, sase-1ot | All 5 closed; child epic .6 finished sase-1a7; filed sase-1pc/1pd/1pe/1p6/1pf/1pg |

Durations are wall-clock from bead creation to close. Note sase-1pu and
sase-1ou each took ~3 days despite "five small beads": nested child epics and
epic-caused integration repair dominate the tail, not the seed fixes.

## How each round went

**sase-1pm — the template, executed cleanly.** The plan's Context section
re-listed 398 non-closed tasks, split them into eight category slices, closed
8 (6 obsolete + 2 duplicates), and ranked the rest by fleet-wide cost. All
five phases touched disjoint files and ran in parallel. Landing verified each
`TASK RESOLVED` note against master `cddea47cc6`, ran 54 focused tests plus a
full ToolRun (58,777 passed), and left a ranked seed list for epic 2. This is
the round to copy. Its one blemish became a recurring theme: three plan files
were left `status: wip` in an uncommitted tree and had to be repaired by the
next lander.

**sase-1pn — clean seeds, self-inflicted integration wound, repaired
same-turn.** The five seeds closed with evidence. The epic itself broke
`test_fix_routes_generated_docs_to_their_declared_venvs` (phase .4's ruff pin
vs. the test's fake-ruff stub) and collided with a deliberate contract-marker
removal; the landing tale fixed both, moved quarantine decisions behind the
Rust binding, and passed a 108-minute full check plus 5,616 core tests.
Follow-up triage was exemplary: 4 genuinely new flakes filed (sase-1po, 1pp,
1pq, 1pr), exact-duplicate corroboration via +1 instead of new beads, and an
explicit refusal to infer causal ownership from topical overlap.

**sase-1pu — the most expensive round, and the strongest verification.** Three
days, two nested epics, ~100 non-epic commits reviewed for drift, 91 + 422
focused tests and a 59,580-test full lane. Phase .3's helper import broke five
scoped suite-gate nodes and Full CI on every Python version; the breakage was
epic-caused and was repaired inside the epic (86bec79ca4) rather than filed
away. Correct handling, but note the pattern: the *phase* broke the gate and
the *lander* paid for it.

**sase-1qn — the best round.** Eight hours, five seeds, one duplicate closure
(sase-rh superseded by sase-o7), only corroborating +1s otherwise. The ranking
was explicit and checkable (per-bead +N counts, recurrence dates). No new
tasks were warranted — the sign of a round where triage, not filing, did the
work.

**sase-1qt — seeds fixed, landing lost, recovered by redo.** The three phases
landed (apollo prompt-render fixed on both hosts, drain bounded, ETXTBSY
fixture reworked with deterministic regressions). Then the process failed:
the landing-tale coder finished all repairs and proposed `task_backlog_epic_6`
as its last step; the provider was SIGTERMed (exit 143), the EpicApproval
gate failed with "workspace claim is no longer owned", no finalizer ran, and
on reuse the workspace was reset to origin/master and the linked core
checkout re-cloned — every repair evaporated. Only an untracked test file
survived (in a stash). The epic was reopened and a redo tale re-implemented
everything from the surviving evidence plus the detailed notes. Final
verification passed (core check 4a9213fc, root check bfa36032). Two things
were permanently lost: a day, and the drafted epic-6 plan (never approved).

**Precursors sase-1oh / sase-1ou** prove the mechanism predates the numbered
chain and already worked: 10 seeds closed, plus oh's dormant-flake decision
that closed ~28 quiet flakes with +1-reopen safety. ou's sase-1a7 needed a
child epic (.6) — the first evidence that five phases are sometimes six.

## Cross-cutting findings

1. **Gross success, net treadmill.** 25 of 25 seeds closed across the five
   epics (35 of 35 counting precursors), every one with commit/test evidence,
   no `--force`, scope discipline (`keep_five_seeds`) honored throughout. But
   the re-list counts tell the real story: 398 (pm plan, 10-29) -> 384 (pn)
   -> 385 (pu plan) -> 388 (pu closeout) -> 387 (qn closeout) -> **382 today**.
   Net progress over four days is about −16 against 25 closes, because each
   round files genuine new flakes nearly as fast as it closes seeds. Five at a
   time, serially, never converges on a 382-deep backlog.

2. **Guard and ratchet fixes do not stick the first time.** sase-o7 was
   closed by sase-1pn's close-guard extension and recurred on 10-30 (sibling
   rows from other workspaces); sase-1qn had to re-fix it at the lifecycle
   point that actually admits the row. sase-1ic was closed by sase-1pm's
   first-party count and re-broke after mechanical toobig splits; sase-1qn
   re-fixed it as a source-footprint (byte) budget. sase-xo "fixed" 10-21,
   recurred twice more. Closing these on focused-test green is premature; the
   acceptance must replay the recurrence sequence.

3. **Verification culture is the chain's best asset.** Every landing re-read
   all phase notes, reviewed non-epic drift commits (up to ~100), re-ran
   focused suites plus a full `sase tool run check` in each touched repo, used
   loaded loops for flakes, reproduced apollo-only failures on apollo with a
   documented recipe, and triaged every `PROPOSED FOLLOW-UP` through
   `/sase_new_task` with duplicate search. Do not dilute any of this.

4. **Landing pays for phase-caused breakage.** sase-1pn.4 (ruff stub) and
   sase-1pu.3 (miniature-repo import) both broke gates outside their seeds;
   both were repaired by the lander in a tail. The cost is visible in the
   3-day landings. Phases should run affected neighboring lanes before phase
   close.

5. **The chain rule is load-bearing and fragile.** The "Mandatory: continue
   the backlog chain" section (re-list, close only provable duplicates /
   obsolete, rank by fleet-wide cost, ≤5 phases / ≤5 beads, carry the rule
   verbatim, propose via `/sase_plan` last) is the de facto prompt that
   drove all five rounds — it survived verbatim from epic 1 to epic 5 with
   only formatting changes. It worked. But it has two failure modes now
   demonstrated: (a) plan `status: wip` repeatedly failed to commit, forcing
   the next lander to repair it; (b) sase-1qt's draft epic-6 plan died with
   its workspace, and the redo closeout explicitly set
   `chain_continuation=defer_to_owner` — **the chain is currently stopped**,
   awaiting exactly the owner's decision this request contemplates.

6. **Autopilot crept in.** sase-1pm and sase-1oh had reviewer-approved
   decisions (via ACE TUI). sase-1pn, sase-1pu, sase-1qn, and sase-1qt were
   all `decided_by: auto`. The `keep_five_seeds` default is safe, but four
   consecutive unreviewed scope decisions is not a habit to keep.

7. **Ranking got better over time — keep the latest version.** sase-1pm
   ranked qualitatively; sase-1qt ranked with selection-health full-run
   records (630 runs, ≤5 failures, excluding each run's own changed files).
   That objectivity is worth templating.

## Recommendations (before the next run)

1. **Checkpoint the next-epic proposal before final verification.** The
   sase-1qt loss happened because the epic-6 draft existed only in a
   workspace that was reset. Propose (or at least commit the plan file to the
   sidecar) *before* the long final check, not as the last step of a turn
   that a SIGTERM can erase.
2. **Do not start the next chain until stranded-workspace retention lands**
   (sase-1pj.7.1, which already owns the sase-1qt lost-work issue) — or
   explicitly accept a repeat of the redo. Nothing in the current template
   protects a finished landing from a dead workspace.
3. **Anti-rework rule for guard/ratchet-class beads:** at most one per epic,
   and acceptance must include a recurrence replay (sase-1qn's sibling-row
   reconstruction is the model), not just focused-test green. sase-o7 and
   sase-1ic each cost two epics; sase-xo cost three landings.
4. **Make net-backlog accounting mandatory.** Every closeout already re-lists
   non-closed tasks; require the closeout note to print opened-vs-closed
   since the previous epic. Seeds-closed is a vanity metric on a treadmill.
5. **Break the treadmill or bless it.** At net −4/day against 382 open, a
   single serial chain is maintenance, not cleanup. Either (a) re-authorize a
   dormant-close sweep like sase-1oh's `dormant_flakes = close` (28 closed,
   +1 reopens on recurrence — it worked), or (b) run two chains by category
   (deterministic cost-savers vs. flakes), or (c) widen to more than five
   where phases are provably disjoint. Do not simply re-run the identical
   template and expect convergence.
6. **Restore human review on scope decisions.** Route at least the
   `optional_scope` decision through the reviewer (ACE TUI) as sase-1pm did.
   Four straight `auto` epics is how scope creep would arrive unnoticed.
7. **Phase-owned integration.** Add to the phase rules: before a phase bead
   closes, run the full-lane neighbors its files touch (scoped suite-gate,
   contract manifest, kind coverage — the three sase-1pu.3 victims). The
   lander's tail should integrate drift, not repair the phase.
8. **Template the two best inventions.** Copy sase-1qt's apollo reproduction
   recipe (git-archive snapshot, scratch venv, cached wheel, never inside an
   apollo workspace, clean up afterwards) and its selection-health ranking
   method into the chain template verbatim.
9. **Close the hygiene loop.** Set plan `status: done` in the landing commit
   itself (three epics in a row left it `wip`); resolve `epic-symbols`
   before proposing the next epic; record `chain_continuation`
   (continue vs. defer_to_owner) explicitly every time — sase-1qt's explicit
   deferral is the reason the owner knows the chain stopped.
10. **Suggested seeds for the next epic already exist** in the recorded
    rankings (re-verify, do not trust blindly): sase-1q3 (model-override
    flakes, xsmall, "first in line"), sase-zo (partially fixed sidecar
    inventory), sase-1em, sase-1oy. Start with a fresh re-list plus a
    duplicate/obsolete pass — the re-list is where sase-1qn found its only
    cheap win (sase-rh).

## Bottom line

The chain did what its prompt asked: 25 verified seed closes in four days
with disciplined scope and excellent triage. It did not do what its name
promises: the backlog stands at 382, two seeds needed re-fixing inside the
chain, one landing was destroyed by infrastructure and cost a day to redo,
and the chain is now parked awaiting owner approval. Re-run the mechanism —
the prompt, the ranking, and the verification bar are all worth keeping —
but fix the proposal checkpoint, add the anti-rework and net-accounting
rules, and decide up front whether the goal is convergence (then add a
dormant sweep or a second chain) or steady-state maintenance (then say so
and stop grading it on backlog size).
