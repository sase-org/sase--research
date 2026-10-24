# Who is stalling the `sase-1n6` (E2) epic? Update for Oct 24, 2026

This updates `research:202610/sase_1n6_e2_stall_culprits.md` (Oct 23 ~13:30 EDT). The
stall it named, the `sase-1n6.5.1.5.2.1.2` session, was cleared: the phase was relaunched
Oct 23 at 13:51 and closed at 17:52. A different agent stalled the epic about 45 minutes
later.

## Short answer

| Agent | Role | Verdict |
| ----- | ---- | ------- |
| **`sase-1n6.5.1.5.2.1.3.1`** (codex/gpt-6-luna) | Phase "integrate a published core containing the current pin" | **Current stall.** At Oct 23 18:36 EDT it handed off to a blind `sleep 129600` monitor (`sca1qh8pnyat`, 36 h). The monitor wakes **Sun Oct 25 06:36 EDT**. As of Sat 17:20 EDT it has been idle for about 23 h, with about 13 h left. |
| `sase-1n6.5.1.5.2.1.land` (codex/gpt-6-astra) | Lander of the parent child-epic | **Set the stall up.** It didn't close its epic. It wrote child plan `reprove_published_qualification.md`, and that plan's first phase is literally "wait for the authorized daily core release". The plan gate approved it automatically, which made it the 5th nested epic under E2 (`sase-1n6.5.1.5.2.1.3`). |
| `sase-1n6.5.1.5.2.1.2` session | Earlier live-proof phase | Earlier stall, now resolved. See the prior report. |

Every other open agent in the epic is waiting correctly on `.3.1`:

```
sase-1n6.5.1.5.2.1.3.1     asleep: sleep 129600 until Sun 06:36   <- THE STALL
 └ .3.2      (muse-spark-1.3)  WAITING on .3.1
    └ .3.land (gpt-6-astra)    WAITING on .3.1, .3.2
       └ ...land chain back up through .5.1.5.2.1, .5.1.5.2, .5.1.5 (.5.1.5.land WAITING since Oct 20), .5.1, .5
          └ sase-1n6.6 (grok) -> .9 (muse) -> .10 (luna) -> sase-1n6.land (opus)   all WAITING since Oct 19
```

## What the sleeping agent missed

The monitor is a plain `sleep`. It doesn't poll, so nothing that happened after it went
to sleep can wake it:

| When (EDT) | Event |
| ---------- | ----- |
| Oct 23 18:36 | `.3.1` starts sleeping. It is waiting for a core tag that contains pin `58aca5fe` (the pin that adds `stranded_work_reduce`). |
| Oct 23 18:56 | **sase-core v0.42.3 is tagged and contains `58aca5fe`**, 20 minutes into the sleep. bbugyi200 merged PR #334. All 5 files are on PyPI by 19:42. |
| Oct 23 20:24 | **`sase-1nn.8.2` (grok-4.6) does `.3.1`'s job** in `dd0c6d8d19`: it pins `sase-core-rs==0.42.3`, and all 876 bindings pass. |
| Oct 24 08:30 | v0.42.4 is tagged. |
| Oct 24 09:25 and 11:48 | sase master moves the pin twice: `02cd3b39b6` sets `e80f08da`, then `7b1b437558` sets `7ec12d2d`. No tag contains either one. |
| Oct 24 09:23 | sase-core PR #336 (v0.42.5) opens. It contains `7ec12d2d`. Ubuntu CI is green; macOS was still running at 17:30. |

## Why it will probably stall again when it wakes

The monitor's recorded next action says: *"If at deadline no complete PyPI release tag
contains the **current** source pin, append an explicit blocker note…, leave this phase
open, and stop without extending the wait."*

- The current pin `7ec12d2d` is in no published tag.
- I ran `tools/check_sase_core_rs_bindings` against the current master tree. Both 0.42.3
  and 0.42.4 are **missing 2 of 879** required bindings: `autonomy_effective_record` and
  `classify_stale_publication_request`.
- Unless PR #336 merges before Sun 06:35, the agent will write a note and exit with the
  phase `IN_PROGRESS` and no owner. That is the same failure `.2--3` hit on Oct 22.

The root problem is a moving target. "Contains the current source pin" can't be met while
sase master bumps `sase-core-revision.txt` (3 times in the last 24 h) faster than core
releases ship. Every release this week (#333, #334, #335) shipped only when bbugyi200
merged it by hand.

## What to do

1. **Merge sase-core PR #336 (v0.42.5)** once macOS CI is green. It is the only release
   that contains the current pin.
2. **Wake `.3.1` now instead of Sunday.** Once 0.42.5 has its 5 files on PyPI:
   ```bash
   sase monitor stop sca1qh8pnyat     # stopping alone launches no follow-up
   sase monitor resume sca1qh8pnyat   # runs the recorded "release exists" path: verify, ratchet-core-pin, preflight, check, close
   ```
   If `resume` refuses a stopped monitor, fork `#fork:sase-1n6.5.1.5.2.1.3.1` with the
   same next action instead. If you skip both steps, expect an ownerless open phase on
   Sunday morning and relaunch it then.
3. **Fix the patterns behind both stalls.** These are candidate task beads, not filed:
   - **Poll instead of sleeping.** Both multi-day stalls on this epic were blind
     `sleep 129600` monitors: `2rwej36xa6fb` on Oct 20 and `sca1qh8pnyat` on Oct 23. A
     bounded poll loop (check `git tag --contains $PIN` and the PyPI file set every ~10
     min until the deadline) would have woken this agent 20 minutes in.
   - **Freeze the pin target.** The wait condition should name a pin fixed when the phase
     starts. Alternatively, accept the newest complete published core that passes the
     binding preflight at a chosen sase SHA. "The current master pin" is not a usable
     target.
   - **Own core release merges until `.9` lands.** The steward cutover (phase `.9`) is
     what automates them, and it sits behind `.5`. So E2 waits on manual merges that only
     E2 itself would automate.
   - **Gate deep child epics.** Lander-authored child plans are approved automatically,
     so each lander can add another nesting level with no human review. Require approval
     past some depth, or for any child plan whose first phase is a wait.

## Evidence

- **Beads:**
  - `sase-1n6` (notes #1–#10)
  - `sase-1n6.5.1.5.2` (notes through Oct 23 22:24Z)
  - `sase-1n6.5.1.5.2.1` (land audit notes)
  - `sase-1n6.5.1.5.2.1.3`, `.3.1` (readiness note at 22:35Z), `.3.2`
  - `sase-1nn.8.2` (closed Oct 24 00:22Z)
- **Transcripts:**
  - `gh_sase_org__sase-ace_run-sase_1n6_5_1_5_2_1_3_1__plan-261023_182850` (the monitor handoff)
  - `…_1_land__gate-20261023182541` (child plan approved automatically)
  - `…_1_land__mon-20261023182723` (child epic launch)
  - `…_1_2__1-261023_171448` (phase `.2` closed)
- **Monitor:** `sase monitor show sca1qh8pnyat` shows `sleep 129600`, state running,
  label `WAITING FOR CORE → CORE RECHECK`.
- **Agents (`sase agent list -a -j`):** `.3.1--mon` RUNNING (sleep). `.3.2`, `.3.land`,
  `.5.1.5.land`, `.6`, `.9`, `.10`, and `sase-1n6.land` are WAITING.
- **Core:**
  - v0.42.3 → `f726ca1e` (contains `58aca5fe`); v0.42.4 → `57d4a450`.
  - `git tag --contains 7ec12d2d` returns nothing; PR #336 head `8379440cc5` contains it.
  - PyPI has 5 files each for 0.42.3 and 0.42.4; 0.42.5 is absent.
- **Bindings:** `uv run --no-project --isolated --with sase-core-rs==0.42.{3,4} python tools/check_sase_core_rs_bindings`
  at sase `5e79f6405f` reports missing 2 of 879 for both versions.
