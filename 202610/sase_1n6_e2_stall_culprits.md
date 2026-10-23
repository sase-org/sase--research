---
tags:
  - pypi-release-reliability
---

# Who stalled the `sase-1n6` (E2 release train) epic?

**Short answer:** one agent session, the live-proof phase worker
**`sase-1n6.5.1.5.2.1.2`** (codex/gpt-6-luna), across its three continuations:

| Agent                      | When (EDT)        | What went wrong                                                                                                                                                                                                                  |
| -------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sase-1n6.5.1.5.2.1.2--1`  | Oct 20 17:00–17:20 | Found the release.yml defect and fixed it locally. Then it kept the phase open ("Do not close this phase") instead of committing and closing, which the plan requires for a rehearse-path defect.                               |
| `sase-1n6.5.1.5.2.1.2--2`  | Oct 20 18:05–18:18 | **Main culprit.** `just check` was clean, but it never committed the fix. It started a 36 h `sleep 129600` monitor and set a wake gate requiring "the repair has landed on origin/master". The repair sat uncommitted in its own workspace, so the gate could not pass. |
| `sase-1n6.5.1.5.2.1.2--3`  | Oct 22 06:19–06:28 | Woke up, found the gate false (as built), committed the fix (`ba7ab4e96b`), then **ended with `bead_action: keep` and no monitor or successor**. The phase was left `IN_PROGRESS` with no owner, and nothing relaunches an open phase. |

The epic's critical path has made no progress since **Oct 20 17:20, about 68 h ago**: a
self-inflicted 36 h wait, then about 31 h with no owner.

## Why the whole epic is frozen

Every other open agent is waiting correctly on that one orphaned leaf:

```
sase-1n6.5.1.5.2.1.2  ← IN_PROGRESS, no live agent   (the stall)
 └ sase-1n6.5.1.5.2.1.land  WAITING (gpt-6-astra)
    └ sase-1n6.5.1.5.land    WAITING (gpt-6-astra) → resumes sase-1n6.5.1 → sase-1n6.5
       └ sase-1n6.6  WAITING on .5   (grok-4.6)
          └ sase-1n6.9  WAITING on .6   (muse-spark-1.3)
             └ sase-1n6.10 WAITING on .9   (gpt-6-luna)
                └ sase-1n6.land WAITING on all 10 phases (claude/opus)
```

## How the agents went off-plan

`plan:202610/deployed_qualification_proof.md`, live-proof step 8 ("Rehearse-path
defect") says: fix it, write `REPROOF REQUIRED:`, then *"Finish with the normal commit
declaration and close this phase, so the land agent schedules the reproof. **Never wait
for your own commit.**"* The plan also calls the core-pin containment gap *"Outer gap,
not ours"*. It belongs to `sase-1n6` DISCOVERED ISSUE #1.

The session broke both rules:

1. **It added a gate the plan rules out.** The first turn (Oct 20 16:54) wrote *"do not
   close this phase while that [containment] gap prevents trustworthy acceptance"*.
   Every later turn carried this forward as "wait for the next daily core cut."
2. **It waited on its own commit.** `--1` and `--2` both ended in monitor handoffs, and
   those do not commit the workspace. The fix sat in `sase_13` for 36 h behind a gate
   that required it to be on master already.
3. **It left the phase with no owner.** `--2` told `--3` to "keep the phase open and
   finish with `bead_action keep`" if either gate was false. `--3` did exactly that
   without arming a wake. The phase prompt itself warns that *"nothing relaunches a
   phase left open."*

## Contributing causes (not stalls themselves)

- **`sase-1n6.2`** (muse-spark-1.3) introduced the bug on Oct 19 in `110214f51c`. The
  inline Python version reader in release.yml's identity step was missing a `)`.
  Landing reviews missed it, and so did the unblock phase's local replay, which covered
  the build and published-core steps but not identity. The bug cost the Oct 20
  live-proof round (runs `39495874381`, `39495879106`).
- **sase-core PR #333 (v0.42.2 daily cut)** stayed open from Oct 20 01:37Z to Oct 23
  16:29Z. Nothing merged it until **bbugyi200 merged it today**. The steward that will
  eventually own that merge is still observe-only, and going live is phase `.9`, which
  is itself blocked behind `.5`.
- **Full CI `build-core`** was red until `sase-1nn.3` landed `b2a4c380cf` today (12:25).

## Status right now (Oct 23 ~13:30 EDT): every gate is clear

| Gate the agents were waiting on             | State                                                                                  |
| ------------------------------------------- | -------------------------------------------------------------------------------------- |
| release.yml identity fix on master          | ✅ `ba7ab4e96b` (Oct 22 06:28)                                                          |
| Core pin contained by a published tag       | ✅ pin `246e2874` is in **v0.42.2** (GitHub release + 5 PyPI files, 16:29Z today)        |
| Full CI can build core                      | ✅ run `39987573569` at `1a3a7022d1`: build-core and lint green, tests running at time of writing |

The containment window may not stay open. `sase-core-revision.txt` has moved 10 times
since Oct 19, and the next pin bump past v0.42.2 makes the containment gate false again.

## What to do

1. **Relaunch the live-proof phase now (recommended).** Fork `--3` (for example,
   `#fork:sase-1n6.5.1.5.2.1.2--3`) with an explicit instruction. It should run plan
   live-proof steps 1–10 immediately: aligned green rehearsal, 0.41.0 probe, and
   exact-SHA Full CI at current master. The prompt should also say three things:
   - containment is not this phase's gate (just restate that DISCOVERED ISSUE #1 is
     open);
   - do **not** author a child epic;
   - never hand off a long wait with uncommitted changes.

   The plan-literal alternative is to close `sase-1n6.5.1.5.2.1.2` citing the landed
   `REPROOF REQUIRED:` fix, so the waiting `.land` agent wakes. That agent would only
   propose more remaining work, which adds an 8th nesting level, so it is slower.
2. **Close the hole that allowed the orphan** (candidate task beads):
   - Flag any `IN_PROGRESS` phase bead whose session has ended with `bead_action: keep`
     and no live monitor or successor. Today that state is silent.
   - Warn when an agent starts a long monitor handoff (hours) with a dirty workspace and
     a `--next` that waits on master. That is the "wait on your own commit" deadlock.
3. **Unblock core cuts until `.9` hands over.** Someone (human or chop) needs to own
   merging sase-core release PRs. Otherwise any E2 gate that depends on a fresh core
   tag can sit for days.

## Evidence

- Beads: `sase-1n6`, `sase-1n6.5`, `.6`, `.9`, `.10`, `sase-1n6.5.1`, `.5.1.5`,
  `.5.1.5.2`, `.5.1.5.2.1`, `.5.1.5.2.1.1`, `.5.1.5.2.1.2` (notes #1–#5).
- Transcripts: `~/.sase/chats/202610/gh_sase_org__sase-ace_run-sase_1n6_5_1_5_2_1_2__{plan-261020_152722,1-261020_170011,2-261020_180503,3-261022_061916}.md`.
- Monitors: `9kyw3tsdcbq2` (run poll), `34j0635h63ge` (check), `2rwej36xa6fb`
  (`sleep 129600`, Oct 20 22:18Z → Oct 22 10:18Z).
- `sase agent list -a -j`: six `WAITING` agents above. No running agent for
  `sase-1n6.5.1.5.2.1.2`.
- Commits: `110214f51c` (bug, `sase-1n6.2`), `ba7ab4e96b` (fix, `--3`), `b2a4c380cf`
  (Full CI build-core, `sase-1nn.3`).
- `gh pr view 333 -R sase-org/sase-core`: merged 2026-10-23T16:29:06Z by bbugyi200.
  `git tag --contains 246e2874…` → `v0.42.2`.
