# Five-round task-bead cleanup: how the epic chain went

Researcher: `research.30.grk` (independent). Written 2026-11-02 from live beads,
approved plans, lander notes, and `sase bead stats`. I did not read peer swarm
reports.

**Question.** Bryan ran five batches of task-bead cleanup, one epic per batch,
and pointed at `sase-1qt` as the breadcrumb. How did that chain actually go,
and what should change in the starting prompt before trying it again?

**Short answer.** The numbered chain (`sase-1pm` → `sase-1pn` → `sase-1pu` →
`sase-1qn` → `sase-1qt`) did real work: about 26 seed task beads closed, plus
a handful of verified duplicates and dormant flakes. It did not drain the
backlog. Non-closed task counts stayed in the high 300s the whole time, and
`sase bead stats` now shows **368 ready** tasks. Two structural defects in the
continuation rule cost a full landing twice. Keep the five-bead cap and the
`keep_five_seeds` opt-out. Stop making the next epic's `sase plan propose` the
last action of the lander. Give the next round a stop condition, dual-host
ranking, and a recurrence protocol.

---

## 1. What `sase-1qt` is a breadcrumb for

`sase-1qt` is **Task backlog epic 5**, closed done (after one reopen) on
2026-11-02. Its plan is `plan:202611/task_backlog_epic_5.md`. The parent-plan
link is `plan:202611/task_backlog_epic_4.md`. Walking that parent chain
backwards yields the five numbered rounds:

| Round | Epic bead | Plan | Created | Closed | Landed by |
| ----- | --------- | ---- | ------- | ------ | --------- |
| 1 | `sase-1pm` | `plan:202610/task_backlog_epic_1.md` | 2026-10-29 01:44 EDT | 2026-10-29 10:33 EDT | `sase-1pm.land` (agent `15r` proposed it) |
| 2 | `sase-1pn` | `plan:202610/task_backlog_epic_2.md` | 2026-10-29 10:44 EDT | 2026-10-29 19:08 EDT | `sase-1pn.land` |
| 3 | `sase-1pu` | `plan:202610/task_backlog_epic_3.md` | 2026-10-29 19:19 EDT | 2026-11-01 14:23 EST | `sase-1pu.land` |
| 4 | `sase-1qn` | `plan:202611/task_backlog_epic_4.md` | 2026-11-01 14:34 EST | 2026-11-01 17:50 EST | `sase-1qn.land` |
| 5 | `sase-1qt` | `plan:202611/task_backlog_epic_5.md` | 2026-11-01 18:08 EST | 2026-11-02 09:28 EST (after reopen) | `sase-1qt.land`, then `sase-1qt.land--4` |

Each lander was required to re-list every non-closed task bead, close only
verified duplicates or obsolete items, pick the next five by fleet-wide cost,
write an epic of at most five phases, copy the continuation rule verbatim, and
**propose that epic with `/sase_plan` as the last action of the landing turn**.
That last clause is the chain's original prompt, and it is the part that
failed.

Epic 6 was authored (`task_backlog_epic_6.md`, seeds `sase-1oy`, `sase-1em`,
`sase-zo`, `sase-1pw`, `sase-1ce`) and never approved. The redo landing of
epic 5 chose `chain_continuation = defer_to_owner` on purpose, so the chain
is currently stopped with a refreshed ranking and no live successor.

---

## 2. The chain is older than the five numbered rounds

The five-at-a-time "keep going until the backlog is empty" idea did not start
on 2026-10-29. Three layers sit under `sase-1qt`:

### 2.1 August 2026: recursive monitor prompt

`plan:202608/task_backlog_top5.md` (`sase-ns.6`) already selected five beads
and told the lander: if any ready/open task beads remain, start a `sleep 1`
pseudo-monitor whose `--next` action repeats the exact user prompt:

1. Review all open (not in-progress) sase task beads.
2. Close beads that are no longer relevant.
3. Select the five of highest impact.
4. Propose a plan that marks them in progress, notes the work, closes
   finishable beads, and **repeats this prompt**.
5. Consolidate `TASK NEEDS APPROVAL` notes.
6. Terminate.

That is the ancestor of the later "Mandatory: continue the backlog chain"
block. The continuation mechanism later changed from a monitor `--next` to
`sase plan propose`, but the goal ("until no workable task bead remains")
stayed.

### 2.2 26–30 October: precursor chain `sase-1oh` then `sase-1ou`

On 2026-10-26 the project had **555 open task beads**. A read-only triage
(eight slices, artifact `file:explicit:accb34387e533e1c0cc7aca8`) closed 156
(143 verified fixed, 2 obsolete, 11 duplicates) and left about 401. That
triage produced `plan:202610/backlog_epic_top_five_task_beads.md` /
`sase-1oh`:

| Phase | Seed | Outcome |
| ----- | ---- | ------- |
| `.1` | `sase-1of` Full CI visual-test | closed done |
| `.2` | `sase-14r` shard-timings drift | closed done |
| `.3` | `sase-1nw` stuck bead read-model | closed done |
| `.4` | `sase-yo` closed-as-done stranded work | closed done (child epic `sase-1oh.4.1`) |
| `.5` | `sase-1dp` unscanned sidecar transcripts | closed done (child epic `sase-1oh.5.1`) |

Human-reviewed decisions: `secret_scan = build`, `dormant_flakes = close`.
The lander then closed **28 more** beads (27 dormant flakes plus `sase-12s`)
and proposed epic 2.

`sase-1ou` / `plan:202610/backlog_epic_2_top_five_task_beads.md` took
`sase-1og`, `sase-18t`, `sase-12f`, `sase-1a7`, `sase-1ot`. Four of five
closed done. `sase-1ot` (history purge) stayed open after the owner rejected
the execution gate. `sase-1a7` recurred in Full CI and forced child epic
`sase-1ou.6`. This lander also hit the first copy of the continuation bug
(section 5).

When `sase-1ou` finally closed on 2026-10-30, its lander found **the numbered
chain already running** as `sase-1pu` and explicitly refused to fork a second
parallel backlog chain.

### 2.3 29 October: a second full triage started the numbered chain

While `sase-1ou` was still in flight, agent `15r` re-read **398 non-closed**
task beads at master `dd59c28f44`, closed 8 (6 obsolete, 2 duplicates), and
proposed `task_backlog_epic_1.md`. That is why the numbered sequence calls
itself "epic 1" even though `sase-1oh` already used that name.

So the five batches Bryan remembers are the numbered `1pm`–`1qt` sequence.
They inherited the continuation contract from `sase-1oh`, ran **in parallel
with** `sase-1ou` for two days, and are the right object of this
retrospective.

---

## 3. Round-by-round outcomes of the numbered chain

### Epic 1 — `sase-1pm` (same day, 2026-10-29)

Human-reviewed: `import_budget = first_party`, `rebase_gate = imports`.

| Phase | Seed | What landed |
| ----- | ---- | ----------- |
| `.1` receipt | `sase-1nh` | SHA receipts count as successful commits (`45ded07c14`) |
| `.2` term | `sase-1ll` | session-wide `TERM` pin so rendering tests are hermetic (`bcddb9edb3`) |
| `.3` audit | `sase-1p5` | five snapshot dir-op sites reviewed (`4d22ceefa5`) |
| `.4` import-budget | `sase-1ic` | first-party cap 2844 (`24561602cc`) — **reopened twice, came back in epic 4** |
| `.5` rebase-gate | `sase-1cb` | imports-only pre-push checker, plus child epic `sase-1pm.5.1` |

All five seeds closed. Re-list: **384** non-closed. No extra closures; the
"likely closable" leads (`sase-1nr`, apollo hint cluster, `sase-v4`) could
not be proved. Proposed epic 2. Plan-status `done` edits were at risk because
the legacy plan handoff skipped host finalization — already a warning.

### Epic 2 — `sase-1pn` (same day)

Auto-approved: `claude_tools = inbound_and_async`, `slot_refusal = quarantine`,
`toolchain_source = pin_extras`.

| Phase | Seed | What landed |
| ----- | ---- | ----------- |
| `.1` | `sase-163` | Claude inbound refuse + async tool deny |
| `.2` | `sase-1p9` | workspace-slot quarantine on preservation refusal |
| `.3` | `sase-o7` | close guard unions local + default-branch Justfile (`8bea2e8414`) — **recurred, came back in epic 4** |
| `.4` | `sase-1cs` + `sase-vr` | pin ruff/mypy/Textual in `.[dev]` |

All five closed. The lander still had to write a medium tale for: baseline-aware
epic-symbol reconciliation, moving slot-refusal policy into Rust, and a stale
contract-manifest collision. Follow-up triage **created** `sase-1po`,
`sase-1pp`, `sase-1pq`, `sase-1pr` (all large flakes of unknown cause) and
closed `sase-1pg` as already fixed. Re-list: **385** non-closed — one *higher*
than after epic 1.

### Epic 3 — `sase-1pu` (2026-10-29 to 2026-11-01)

Auto-approved: `optional_scope = keep_five_seeds`. Slowest numbered round
(about 67 hours). Phase `.5` grew nested epics `sase-1pu.5.1` and
`sase-1pu.5.1.5`.

| Phase | Seed | What landed |
| ----- | ---- | ----------- |
| `.1` | `sase-1os` | scan prompt migrations; no-replay GH013 recovery |
| `.2` | `sase-12v` | waiter wake recovers from `NameCollisionError` |
| `.3` | `sase-1mv` | marker-audit selection for marker-writer changes |
| `.4` | `sase-120` | isolate nested pytest temps; no timeout raise |
| `.5` | `sase-1cc` | publish terminal run-state; bounded repair |

Epic-caused integration breakage had to be repaired in landing: the miniature
scoped-repo omitted a new helper (`ModuleNotFoundError` in five suite-gate
nodes), contract-manifest staleness, and missing completion kinds for
`agent/sync:state_*`. Those were declined as already fixed by
`86bec79ca4` / `8f982c8ae9` by the time the lander ran.

Re-list: **388** non-closed. Closed one extra (`sase-rh` superseded by
`sase-o7`). Proposed epic 4. Still deferred the apollo hint cluster.

### Epic 4 — `sase-1qn` (2026-11-01, ~3.5 hours of landing)

Seeds were the two recurrences plus the next three fleet-wide flakes:

| Phase | Seed | What landed |
| ----- | ---- | ----------- |
| `.1` | `sase-o7` ↺ | epic-symbol freshness preflight before check / check-full / symvision (`5585fadefd` + core `e60f3e16`) |
| `.2` | `sase-1ic` ↺ | import budget became a **source-footprint** cap, 12,162,484 B (`5d7a79c3c0`) — the first-party *count* ratchet from epic 1 had failed |
| `.3` | `sase-1gz` | FederationLock unlocks on Drop (core `02eb6961`) |
| `.4` | `sase-13a` | PTY helper always prepends a test-owned `sase` (`0760eb0100`) |
| `.5` | `sase-19m` | AGY probe drains pipes before/after kill (`34a8638ee0`) |

Re-list: **387** non-closed. First lander to actually reproduce the
hint/prompt-render cluster **on apollo** (7–9 of 30 failed; 30/30 on athena
at the same SHA). That became epic 5. Next-in-line named: `sase-1q3`,
`sase-zo`, `sase-1em`, `sase-1oy`.

### Epic 5 — `sase-1qt` (2026-11-01 to 2026-11-02, one lost landing)

Three phases, five seeds plus related `sase-1i9`:

| Phase | Seed | Phase fix that stayed landed |
| ----- | ---- | ---------------------------- |
| `.1` apollo-prompt-render | `sase-1ia`, `sase-1l3`, `sase-1hy` (+ `sase-1i9` closed as obsolete) | prompt selection, sase `d26baecb05` + core `45c6a260` |
| `.2` agents-sync-drain | `sase-xo` (already reopened twice) | bounded drain, sase `3e6c19ee37` + core `f061f5f6` |
| `.3` sudo ETXTBSY | `sase-15h` | fixture publication lock, core `b0a63dc3` |

The **seed fixes landed**. The **landing repairs did not**, the first time:

1. Required-Rust cleanup policy (Python 1.0 fallback removed).
2. Spawn-only sudo fixture lock with deterministic ETXTBSY proofs.
3. Startup footprint back under the unchanged cap (lazy `agents_sync`,
   11,893,373 B vs cap 12,162,484).

The tale coder finished those repairs, closed beads, then proposed epic 6.
The provider was SIGTERMed (exit 143). The EpicApproval gate failed with
"workspace claim is no longer owned by the creating agent". No finalizer
ran. Workspace reuse reset sase to `origin/master` and re-cloned sase-core.
Only one untracked test file survived in a stash.

`sase-1qt` was reopened, the repairs were redone from
`plan:202611/redo_1qt_landing.md`, and the epic closed again with
`chain_continuation = defer_to_owner`. Follow-ups: wheel-cache proposal
declined; drain-accounting leak routed to active `sase-j7`; lost-work
handoff recorded as DISCOVERED ISSUE on `sase-1pj.7.1`; cold keymap
isolation filed as new `sase-1qu`.

---

## 4. Did the backlog shrink?

Non-closed task-bead counts recorded by landers:

| When | Count | What just happened |
| ---- | ----- | ------------------ |
| 2026-10-26 triage start | 555 open | before any of this |
| After 2026-10-26 triage | ~401 | 156 closed as fixed/obsolete/dup |
| After `sase-1oh` land + dormant sweep | ~375 | +28 extra closures |
| 2026-10-29 numbered-chain triage | 398 | **new full count, overlapping `sase-1ou`** |
| After epic 1 | 384 | 5 seeds, 0 extra |
| After epic 2 | 385 | 5 seeds, **4 new large flakes filed** |
| After epic 3 | 388 | 5 seeds, 1 duplicate closed |
| After epic 4 | 387 | 5 seeds (2 of them recurrences) |
| 2026-11-02 `sase bead stats` | **368 ready** + 10 open + 3 snoozed | plus 218 in_progress across all types |

Store-wide: 1,386 task beads exist; 7,656 issues of every type are closed;
next id counter is 2263. The ready queue is still huge.

The chain was never going to empty 400 beads at five per round. Five rounds
close ~25 seeds. In the same window landers and other epics **filed**
`sase-1po`, `sase-1pp`, `sase-1pq`, `sase-1pr`, `sase-1pc`, `sase-1pd`,
`sase-1pe`, `sase-1pf`, `sase-1pg`, `sase-1p6`, `sase-1pb`, `sase-1ot`,
`sase-1qu`, `sase-1px`/`1py`/`1pz`/`1q0`, and more. Inflow from "phase
worker saw a flake in `just check`" roughly matches outflow from "backlog
epic closed five seeds."

Dormant close *did* move the needle when it ran (`sase-1oh`: 27;
`sase-1ou`: 10 of 96 flakes, 86 left). The numbered chain **dropped** the
`dormant_flakes` decision after epic 1's landing contract, and then almost
never closed extras. Epic 1's lander closed none of its "likely closable"
leads. Epic 3 closed one duplicate. Epic 4 closed none.

---

## 5. The continuation rule lost landings twice

The contract every numbered epic copied:

> Propose it with `/sase_plan`. Proposing ends the land agent's turn, so do
> it last.

`sase plan propose` is a turn-ending handoff. On the legacy path
(`staged_handoffs` off) it **skips host finalization**. Uncommitted landing
repairs die with the turn. This is not theoretical:

| Incident | When | What vanished | Recovery |
| -------- | ---- | ------------- | -------- |
| `sase-1ou.land` | 2026-10-28 | sase-core `sase-1p6` busy-handler fix + flake-baseline reconciliation. `sase-1p6` was closed done; master did not contain the commits. Noted by `research.5f.cld`. | Separate recovery epic `sase-1ph` restored both. |
| `sase-1qt.land` | 2026-11-01 | Entire landing-repair tree in sase and sase-core after a SIGTERM during epic-6 proposal. Gate: workspace claim lost. Workspace reset + core re-clone on reuse. | Reopen + `plan:202611/redo_1qt_landing.md`. Seed task closes were valid; integration repairs had to be rewritten. |

`sase-1ou.6.land--3` already diagnosed this and refused to propose a
successor *because* `staged_handoffs` was still false. Epic 5's first lander
did it anyway, and lost the work. The redo plan's default decision is now
`chain_continuation = defer_to_owner`: refresh and validate the next draft,
do not `sase plan propose` from the landing turn, finish through
`/sase_final`.

That is the single most important process lesson in this chain. It was
learned in round 2 of the *precursor*, forgotten by numbered round 5, and
re-learned at the cost of a full redo.

A related, milder form showed up in epic 1: plan-status `done` edits on
`task_backlog_epic_1.md` / `rebased_stitch_gate.md` were left for epic 2 to
re-check because the legacy handoff skipped finalization.

---

## 6. Ranking was good on cost, blind on host, and sticky on recurrences

### What ranking got right

Fleet-wide cost (breaks every agent's check or CI, wastes landings, security
/ data-loss, heavy +1) is the right primary key. The seeds that actually
shipped were mostly that class:

- SHA-receipt matcher breaking every prepared completion (`sase-1nh`).
- `TERM=dumb` breaking 16 rendering nodes in every agent shell (`sase-1ll`).
- Claude cross-session messaging (`sase-163`).
- Dev toolchain drift that blocked a release (`sase-1cs` / `sase-vr`).
- Stale `--epic-symbol` rows failing *every* `just check` at lint
  (`sase-o7`, +25).
- Import-budget weekly rebreak (`sase-1ic`, +35).

`keep_five_seeds` as an owner opt-out for adjacent feature/memory work is
also right. Auto-approval consistently picked it. Phase workers stayed
inside the five seeds more often than not; landers declined most adjacent
proposals.

Disjoint-file parallel phases worked when the seeds really were disjoint.
Epics 1, 2, and 4 ran their phases in parallel and landed the same day or
the next.

### What ranking got wrong

**Athena-only "every agent" until round 5.** The hint/prompt-render cluster
(`sase-1ia`, `sase-1l3`, `sase-1hy`, `sase-1i9`) was in the seed list from
epic 1's landing notes. Every lander through epic 4 deferred it because it
passed on athena. Epic 4's lander finally copied a scratch tree to apollo
and got 7–9 failures of 30 at the same SHA. Four rounds of "fleet-wide cost"
had been measuring one host. The epic 5 plan had to ship a full apollo
reproduction recipe (git-archive, uv venv, scp'd abi3 wheel, `env -i`
controls). That recipe is worth keeping in the next prompt as a *ranking*
requirement, not only a phase recipe.

**Same bead, same class of fix, reopen.**

- `sase-1ic` closed 2026-10-26 (triage), reopened, closed in epic 1 by
  switching the cap to first-party *module count*, reopened after toobig
  splits, closed in epic 4 by switching the cap to *source footprint*.
  +35 corroborations. Two closes in this chain were not two independent
  bugs; they were one ratchet that kept measuring the wrong thing.
- `sase-o7` closed in epic 2 by unioning the default-branch Justfile,
  reopened 2026-10-30 when rows keyed to already-closed phases still
  reached master, closed in epic 4 by a freshness preflight *before*
  check. The close-guard was necessary and not sufficient.
- `sase-xo` had already been "fixed" twice before epic 5 took it.

The continuation prompt says "pick the 5 most important remaining." It does
not say "if this bead is back, the last fix class is disallowed." That is
why epic 4 spent two of its five slots on recurrences.

**Cheap deterministic beads waited behind expensive flakes.** After epic 4,
the lander named `sase-1q3` (small, 7/44 fail under `SASE_MODEL_OVERRIDE`,
xsmall isolation scrub) as first in line for epic 5, then skipped it for
the apollo cluster. `sase-zo` (+10, small, `sase repo open` display-name
mismatch) has been "next ranking" since epic 2. Both are still `ready` on
2026-11-02. A cost-then-fix-cost ranking that actually applied the second
key would have mixed one of these into an earlier round.

**Full re-list of ~380 beads every landing is expensive and low-yield.**
Numbered-chain landers closed 0, 0, 1, 0 extra beads from those sweeps.
The useful ranking inputs were selection-health full-run records (epic 5)
and +1 counts, not a fresh read of every dormant flake.

---

## 7. Nested child epics and landing tales multiplied cost

The "at most five phases" cap is real at the *plan* layer and fake at the
*execution* layer. Whenever a phase could not finish, the system grew a
child epic or a landing tale:

- `sase-1oh.4.1`, `sase-1oh.5.1`
- `sase-1ou.6` (Files ctrl+j recurrence after the parent had already
  "landed")
- `sase-1pm.5.1` (rebase-gate follow-through)
- `sase-1pu.5.1` and `sase-1pu.5.1.5` (published-state repair)
- `plan:202611/finish_1qt_landing.md` then `plan:202611/redo_1qt_landing.md`

Those children did needed work. They also meant a "five-bead round" was
often a small program of epics, with landers writing DISCOVERED ISSUE notes
onto still-active parents (`sase-j7`, `sase-1pj`, `sase-1om`, …) and filing
new large flakes when the cause was unknown.

Unknown-cause large flakes (`sase-1po` JSON EOF, `sase-1pp` pager
notification, `sase-1pq` custom-gate timeout, `sase-1pr` unloaded-session
dismissal) are a poor output for a cleanup round. They refill the ready
queue with items the next round will not pick (no mechanism, size large).

---

## 8. What is still open that the chain already ranked

All of these were `ready` when read on 2026-11-02. Epic 5's redo lander
(`sase-1qt.land--4`) re-read them at 14:30 UTC while refreshing the unapproved
epic 6 draft.

| Bead | Size | Type | Why it keeps showing up |
| ---- | ---- | ---- | ----------------------- |
| `sase-1q3` | small | ci | Pytest inherits `SASE_MODEL_OVERRIDE`; 7 fail / 44 pass. Control run without the env is green. Named first-in-line by epic 4's lander. |
| `sase-zo` | small | bug | `sase repo open` rejects configured sidecars when inventory uses the display name. **+10**. Half-fixed (`open <name>`), `sase repo list -p sase` still exits 2. |
| `sase-1em` | large | flake | Registry-rebuild pending-claim node fails under the full parallel lane. **+5**. In epic 4's "leave for next ranking." |
| `sase-1oy` | small | flake | Sudo-ledger settlement `settled` vs `deferred` when the lock holder self-releases under load. **+2**. Epic 6 draft seed. |
| `sase-1pw` | medium | bug | Pytest worker-token waiters starve; a 4-token waiter times out after 45 minutes while later runs take freed tokens. Epic 6 draft seed. Directly burned epic 3 phase `.3`'s check (UNDETERMINED). |
| `sase-1ce` | small | bug | `$EDITOR` temp file unlinked on non-zero exit; typed prompt lost. Epic 6 draft seed. |
| `sase-1qu` | small | ci | Cold keymap-defaults cache; filed by the epic 5 lander the same morning. |

Still excluded on purpose: `sase-j0` (`in_progress` under its own holder),
`sase-1ot` (owner rejected the purge gate), `sase-lk` / `sase-1nr` /
`sase-v4` (dormant or unprovable), beads owned by active epics
(`sase-1qj` / `sase-1qi` under `sase-1qk`, drain-accounting under `sase-j7`).

`sase bead ready` still leads with older flakes (`sase-lk`, `sase-lx`,
`sase-ni`, `sase-nr`, …) that the chain repeatedly judged dormant or
lower-cost than the fleet-wide reds. That list is the queue a naive
"pick five ready beads" would hit. The chain's ranking rule is why it
*didn't* spend five rounds on those, and that part should stay.

---

## 9. Anatomy of the prompt that started the numbered chain

The operational prompt is the **Landing → Mandatory: continue the backlog
chain** block, copied from `sase-1oh` into every successor. Compressed:

1. Re-list every non-closed task (`sase bead list -t task -n 0`). Close
   only proved duplicates or obsolete beads. Never close epic-owned or
   snoozed beads. Dormant stays open.
2. Pick the five highest fleet-wide-cost remaining beads, then by cost to
   fix.
3. Write an epic with at most five phases and five task beads. Use
   decisions sparingly; always give the owner an opt-out for feature and
   memory work.
4. Copy this entire continuation rule into the new plan, until no
   non-closed task beads remain.
5. Propose with `/sase_plan`. **Proposing ends the lander's turn, so do it
   last.**

What this prompt optimized for: a self-driving queue that never needs Bryan
to re-launch.

What it actually produced: five solid cleanup epics, two lost landings, a
parallel overlapping chain, two recurrences that consumed later slots, a
ready queue that barely moved, and a sixth epic that exists only as an
unapproved draft.

Human review happened on `sase-1oh` and numbered epic 1 (`sase-1pm`).
Everything after that was auto-approved, including the continuation itself.
That is fine for `keep_five_seeds`. It is not fine for "keep going until
the tracker is empty."

---

## 10. Recommendations (change the prompt before trying this again)

Do another round. Do not restart the unbounded chain as written.

### Change 1 — Split landing and continuation (required)

Delete "Propose it with `/sase_plan`. Proposing ends the land agent's turn,
so do it last."

Replace with the decision already proven on the epic 5 redo:

- **Default: `chain_continuation = defer_to_owner`.** The lander re-lists,
  re-ranks, writes and `sase plan validate`s the next draft, attaches it,
  notes that it awaits owner proposal, and finishes through `/sase_final`
  so sase, sase-core, and plans actually commit.
- **If Bryan wants in-turn proposal:** `propose_after_backup` from
  `plan:202611/redo_1qt_landing.md` — attach a full working-tree patch of
  every dirty repo including untracked files, `git apply --check` on a
  scratch copy, *then* propose. This is the fallback, not the default.

Never run `sase plan propose` from a tree that still holds the landing
repairs. The 2026-10-28 and 2026-11-01 losses are the same bug.

### Change 2 — Put a stop condition in the prompt (required)

Replace "until no non-closed task beads remain" with an explicit halt.
Suggested text:

> Run at most **two** further five-bead epics, or stop earlier when a
> re-rank finds no remaining bead that (a) currently breaks `just check` or
> Full CI on **both athena and apollo**, (b) is a security or data-loss
> risk, or (c) has ≥10 +1s. Report the ranked leftovers; do not invent work
> to keep the chain alive.

Five more unbounded rounds will file as many new flakes as they close.

### Change 3 — Dual-host ranking, not dual-host as a phase recipe (required)

Add to the ranking rules:

> A bead that fails on any fleet host and passes on the lander's host still
> counts as fleet-wide. Before deferring a cluster as "athena-green,"
> reproduce once on apollo (or the other way around) with the epic 5
> scratch recipe: `git archive` + scratch venv + current abi3 wheel, never
> inside a numbered SASE workspace.

That would have pulled `sase-1ia`/`1l3`/`1hy` into epic 2 instead of epic 5.

### Change 4 — Recurrence protocol (required)

If a candidate was closed `done` in a previous backlog epic and is open
again:

- It may be selected, but **the previous fix class is out of scope**
  (do not raise the same cap, do not extend the same close-guard in the
  same way).
- The phase must name the earlier close SHA and say what new mechanism
  will be used.
- Prefer converting a ratchet that keeps re-breaking (`sase-1ic`) into a
  measure that is invariant to the churn (epic 4's footprint cap is the
  model).

Without this, epic *n+1* spends slots on epic *n*'s incomplete fixes.

### Change 5 — Do not start a second chain while one is active (required)

The lander (or the owner prompt) must `sase bead list --type plan --tier epic
--status in_progress` and search titles for `backlog`. If a backlog epic is
already in progress, attach ranking notes to *that* lander and do not
propose a sibling chain. `sase-1ou`'s lander had to paper over this after
`15r` started the numbered sequence on 2026-10-29.

### Change 6 — Cheap re-triage instead of reading 368 beads (should)

Keep "close only proved duplicates/obsolete." Drop the obligation to
re-read every non-closed task every round. Replace with:

1. Selection-health full-run records (the epic 5 method: ≤5 failures per
   run, ignore failures inside the run's own changed files).
2. Ready beads with +1 ≥ 3, or size small/medium and type `ci`/`bug`.
3. The previous round's named next-in-line list.
4. A 30-day dormant sweep **only if** `dormant_flakes = close` is on.

Restore `dormant_flakes = close | keep` as a decision on the *next* epic,
default `close`, with the `sase-1ou` evidence bar (selection-health +
ToolRun + CI + +1 dates, not the full-run store alone).

### Change 7 — Mix one cheap deterministic seed into each round (should)

Cost-to-fix is the stated secondary key and was underused. Each round
should include **at least one** size-small deterministic `ci`/`bug` that
already has a repro in the bead (`sase-1q3`, `sase-zo`, `sase-1ce`,
`sase-1qu` are the current examples) so the round produces a same-day close
even if a large flake phase slips into a child epic.

### Change 8 — Cap nested explosion and follow-up filing (should)

- Phase workers still do not create beads.
- Landers may file follow-ups, but **at most two new task beads per round**,
  and not at size large when the cause is unknown. Unknown-cause flakes go
  as `PROPOSED FOLLOW-UP` notes or +1s on an existing umbrella (`sase-j7`
  for process-global test state, etc.).
- Child epics are for "the seed recurred after its phase closed" or "the
  approved decision cannot be implemented in-phase." They are not a default
  overflow.

### Change 9 — Keep these parts of the prompt unchanged

- At most five phases and five task beads; one phase may own several
  related beads.
- `optional_scope = keep_five_seeds | required_scope_only`, default
  `keep_five_seeds`.
- Phase workers record `TASK RESOLVED:` and `PROPOSED FOLLOW-UP:` on the
  phase bead; the lander closes task beads.
- No assertion weakening, no timeout raises, no flake-baseline entries as
  the fix, no `just check-full` from agents.
- Rust-core boundary and `/sase_repo` before editing sase-core.
- "Never close a bead an active epic owns. Never close a snoozed bead
  early."
- Selection-health as an *input* to ranking (keep the epic 5 paragraph).

### Change 10 — Suggested seeds for the next *single* epic (not a chain)

If Bryan launches one more five-bead epic by hand, from this research the
highest-leverage mix is:

1. `sase-1q3` — small, deterministic, isolation scrub. Same-day close.
2. `sase-zo` — small, +10, still blocks audited `sase repo open` for
   display-name sidecars.
3. `sase-1pw` — medium, waiter starvation; this is how epic 3 lost a
   verification cycle.
4. `sase-1oy` — small flake with a stated mechanism (lock holder
   self-releases).
5. `sase-1ce` **or** `sase-1qu` — both small, both already diagnosed.
   Prefer `sase-1ce` if data-loss ranking still outranks test isolation.

Leave `sase-1em` (large, still no mechanism after +5) for a dedicated flake
epic, not a cleanup round. Leave `sase-1ot` and `sase-j0` alone.

---

## 11. Sources

Primary:

- Beads: `sase-1qt`, `sase-1qn`, `sase-1pu`, `sase-1pn`, `sase-1pm`,
  `sase-1oh`, `sase-1ou`, leftover seeds `sase-1q3`, `sase-zo`,
  `sase-1em`, `sase-1oy`, `sase-1pw`, `sase-1ce`, `sase-1qu`, recurrences
  `sase-1ic`, `sase-o7`.
- Plans: `plan:202611/task_backlog_epic_5.md`,
  `plan:202611/task_backlog_epic_4.md`,
  `plan:202610/task_backlog_epic_{1,2,3}.md`,
  `plan:202610/backlog_epic_top_five_task_beads.md`,
  `plan:202610/backlog_epic_2_top_five_task_beads.md`,
  `plan:202611/redo_1qt_landing.md`,
  `plan:202608/task_backlog_top5.md`.
- `sase bead stats` on 2026-11-02: 368 ready, 10 open, 3 snoozed, 1,386
  tasks, 8,255 issues.
- Lander notes quoted in place, especially `sase-1qt` #6/#8 (lost landing
  and redo), `sase-1ou` #3/#10 (first lost-edit and consolidation into
  `sase-1pu`).

Not used: peer swarm reports from this run; the athena-local
`~/.sase/plans/202611/task_backlog_epic_6.md` draft (absent on this
workspace; contents recovered from the redo plan's seed list and the
redo lander's bead reads).
