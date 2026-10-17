# Will the merge queue make me wait hours to test an agent's fix?

> **Question:** If I carry out
> [`merge_queue_fence_reassessment_and_epic_split.md`](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md),
> will I still be able to test an agent's change as soon as the agent finishes, or will
> a simple fix take hours or until the next day to reach me?

## Short answer

**No, it won't take hours or a day in normal operation.** You would wait **about 15 minutes
on a typical day and about 30 minutes on a bad one**, instead of zero. Longer waits come
only from a few failure modes, listed [below](#when-it-could-take-hours).

- **Nothing changes until the very last step.** Epics A, B and C, plus the pilot, leave your
  loop exactly as it is today. Only Epic D's enforcement step (D5) routes every `sase`
  change through the queue.
- **"Next day" applies only to PyPI releases.** You don't test from PyPI.
- **The plan has two gaps that would hurt your loop.** Both are cheap to fix before D5;
  see [What to add to the plan](#what-to-add-to-the-plan).

## How you test agent changes today

- Your global `sase` is an **editable install of the primary checkout**
  (`~/projects/github/sase-org/sase`); see `~/.local/share/uv/tools/sase/uv-receipt.toml`.
- When an agent finishes, its finalizer **pushes straight to `origin/master`**.
- `sase dev update` (or `git pull`) fast-forwards the checkout from `origin/master`. Seconds
  after the agent is done, you're running its code.

The queue changes only one thing: **when the commit reaches `origin/master`**. Everything
after that works the same.

## What changes, and when

| Stage | Effect on your test loop |
| --- | --- |
| Step 0 (block force pushes) | None. Nothing in sase force-pushes `master`. |
| Track 0, Epic A (releases) | None. These change PyPI publishing, not how changes land. |
| Epic B (gate reruns, quarantine) | None. CI changes only. |
| Epic C (queue-aware landing) | None. Built and proven on a **sandbox repo**; the config default stays `landing.mode: push`. |
| D1–D4 (workflows, queue on, pilot) | None for normal fixes. The pilot covers only allowlisted traffic: docs, `toobig`, ratchets. |
| **D5 (enforce)** | **Every `sase/master` landing goes through the queue.** |

D5 has a hard entry bar: a gate **false-red rate under 3% over at least 7 days**. If false
reds stay above about 10%, the plan says to delay D indefinitely. Master Gate is green on
only 8 of its last 98 runs, so enforcement is far off and gated on the gate being fixed.

The queue covers **`sase` only**. sase-core, plugins and chezmoi keep landing as they do today.

## After enforcement: how long until you can test

```text
agent finishes ─► PR armed (turn ends) ─► quick PR checks ─► queue ─► Master Gate run ─► lands on master ─► sase dev update
                  └──────────────────────────── ~13 min typical, ~28 min p95 ────────────────────────────┘
```

Source: the original report's simulation, which replayed the real landing times at the
planned build concurrency of 2:

| Gate false-red rate | Typical (p50) | Bad day (p95) | Worst seen (max) |
| --- | --- | --- | --- |
| 3% (the D5 entry bar) | 13 min | 28 min | 44 min |
| 10% | 13 min | 34 min | 58 min |
| 30% (roughly today's flakiness) | 19 min | 52 min | 90 min |

The plan also makes this a production pass/fail check (V-D4): landing **p50 under 30 min,
p95 under 60 min**. Add a few minutes to each number for the PR's own quick checks, which
the simulation did not model.

**Not in your path:**

- **Full CI** (64–76 min) stays out of the queue and never delays a landing.
- **PyPI releases** run on a nightly train (release lag of at most 7 days at first, then
  1–3 days). Your editable install never waits on them.

## When it could take hours

These are the only real "hours" cases:

1. **`master` goes red on its own.** A time bomb, an upstream release or a runner change
   can turn `master` red with no landing involved. The plan's circuit breaker then
   **holds all landings** until a build-cop fix jumps the queue and lands. Your fix waits
   behind that repair, and the plan sets no limit on how long it can take.
2. **GitHub's queue or Actions is down.** Landings pause. The only bypass is a manual,
   audited emergency push by you.
3. **The fix is actually broken.** The queue ejects it, and up to two repair turns run,
   each followed by another queue pass, which can add an hour or more. Today that broken
   fix would land and you'd only discover the problem while testing it.

**What would really cause day-long waits** is enforcing while the gate is as flaky as it
is today. The D5 entry bar exists to prevent exactly that. Treat it as non-negotiable.

## What to add to the plan

Two gaps affect you directly. Both belong in Epic C's requirements:

1. **"Agent done" would no longer mean "ready to test."** The agent's turn ends when its
   PR is *armed*, which is 15–30 minutes before the change reaches `master`. If you run
   `sase dev update` right after the agent finishes, it pulls nothing. The plan shows the
   landed SHA on stitch and agent pages but **never notifies you that a change landed**.
   - **Add:** a "landed" notification, plus a visible landing state (armed, queued,
     landed, ejected) on the agent's row.
2. **There's no supported way to try a change before it lands.**
   - **Don't** check out the PR branch in your primary checkout. Rebase landing gives the
     commit a new SHA (the plan's N2 maps PR head SHA to landed SHA). Your checkout would
     diverge from `master`, and `sase dev update`, which only fast-forwards, would refuse
     to update it.
   - **Add:** a preview command that runs `sase` from a throwaway worktree at the PR head.
     Optionally, also let you push an urgent fix to the front of the queue (the plan
     already does this for build-cop fixes). Jumping the queue restarts every build
     already in progress, so reserve it for real urgency.

Also, measure V-D4 **from when the agent finishes to when you can test it**, not from
when the PR enters the queue. That is the delay you actually experience.

## Bottom line

- **Safe to start:** Epics A, B and C don't touch your loop at all.
- **Before D5:** add the landed notification and a preview path.
- **Enforce only if the pilot shows the wait is short:** landing p95 under 60 minutes
  (ideally around 30), with false reds under 3%.

If those hold, a simple fix costs you a coffee break, not a day.

## Sources

- [`merge_queue_fence_reassessment_and_epic_split.md`](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md):
  epic ordering, D3 pilot scope, D5 entry criteria, N2/N3/N7/N9/N10, and V-C1/V-D4.
- [`merge_queue_fenced_master_and_exact_sha_releases.md`](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md):
  the queue simulation and gate durations (p50 12.5 min).
- sase at `0f91d5eed0`: `src/sase/dev_update/roots.py` (fast-forward-only update from
  upstream), and the uv tool receipt showing the editable install of the primary
  checkout.
