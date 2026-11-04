# Are agent publication errors still happening? (Nov 4 follow-up)

> **Research query:** Are we still experiencing agent publication errors? If so, why?
> Keep it concise and easy to understand.

_Observed on athena, 2026-11-04 at about 13:15 EST. Checked against sase `origin/master`
`d563b9da4d` and sase-core `origin/master`. This follows up the Nov 2 diagnosis in
[agent_publication_openai_key_false_positives](agent_publication_openai_key_false_positives/agent_publication_openai_key_false_positives.md),
which has the full mechanism, diagrams, and code history._

## Short answer

**Yes.** The bug the Nov 2 report diagnosed is still running, and it has grown. Nothing
has been fixed and no bead tracks a fix.

- **The error is the same one.** Every pass of the background `agent_publication` job
  (about every 45 s) reports bob-cli's parked requests as an error: `run withheld by
  publication protection` plus `prompt archive withheld …` clauses.
- **The cause is the same one.** sase-core's `openai-key` secret-scanner rule
  (`sk-[A-Za-z0-9_-]{20,}`) has no left boundary. It reads the `sk-` inside ordinary
  `task-…` filenames as an OpenAI key. The publisher parks those requests forever and
  counts them as an error on every pass. No real key is involved.
- **It is getting worse.** One more request is now stuck (5 instead of 4). The healthy
  bob-cli requests left waiting behind the error went from **10 to 46**.

## The numbers (Nov 2 12:56 → Nov 4 13:06 EST)

- **Error digest entries:** 3,247 across 53 digests. **3,235 (99.6%)** are
  `publication / agent_publication`, about 67 an hour.
- **Projects affected:** only `gh_bobs-org__bob-cli`. sase, tailnet, and actstat have
  0 active outbox rows and 0 new quarantines since Nov 2.
- **What the 3,235 entries say:**
  - **3,155:** only the "withheld" clauses. This is the main bug.
  - **23:** "withheld" plus `could not restore deferred prompt archive`. This is the
    known secondary bug.
  - **57:** `git pull --rebase failed: … Permission denied (publickey)`, Nov 4
    04:37–06:23 only. This was a transient GitHub SSH incident.
- **bob-cli outbox now:** 51 active rows.
  - 5 are stuck: retried every pass with `attempts=0`.
  - 46 have never been attempted: `updated_at == created_at`. The oldest is
    `bob-cli-fs.2` from Nov 2 06:30, about 55 hours ago.
- **Claimed hint files:** **152** in `bob-cli/agent_publication/`, up from 68.

## Why: three causes, one of which matters

### 1. The scanner false positive, still unfixed (about 98% of entries)

The five stuck requests:

- **`research.5n.mus`** (Nov 1 18:45): run withheld because its `meta.json` holds a
  `blocked-task-why-…` artifact path.
- **`bob-cli-fs.8.1.3`** (Nov 2 08:47): prompt archive withheld.
- **`bob-cli-fx.2`** ×2 (Nov 2 11:07–11:08): prompt archive withheld, primary and
  linked rows.
- **`bob-cli-g1.2`** (Nov 2 14:47): **new since the Nov 2 report.** Its prompt archive,
  `prompts/202611/bob-cli-g1.2.md`, was blocked at line 135. That line comes from the
  `bob-cli-g1.2--4` prompt, which quotes a `…f-task-…` filename. This added the fifth
  clause at 14:47.

**The evidence that this is still a false positive:**

- The bob-cli protection ledger gained **16 new `openai-key` blocks** since Nov 2. One
  was the g1.2 prompt archive. The other 15 were child members (`--mon`, `--N`)
  whose files are silently left out, so they cause no error.
- I scanned every `.md`, `.json`, and `.jsonl` file in bob-cli's runs from Nov 2–4.
  There are **9,615 `sk-` matches in 1,051 files**. **Every one** sits inside a word:
  8,351 are preceded by `ta` (`task-`) and 1,264 by another `a` (`…ask-`). None is a
  real key.

**Why it never stops** (unchanged from Nov 2):

1. The ledger pins the block to the exact content hash.
2. The withheld request is parked with no attempt charge, so it never quarantines.
3. `publication_job._drain_project` reports the park as a job error on every pass.

### 2. The error starves everything else in bob-cli

This is why the backlog keeps growing.

`src/sase/agents_sync/publication_job.py` still `break`s out of the hinted loop when
it hits an error. After that it skips the "drain the oldest ready rows" fallback,
because that loop only runs under `if not result.lock_busy and result.error is None`.

- The stuck rows hold their hints, so they come back into the hinted batch every pass.
- Rows that have no hint are never drained. These are mostly planner, `.land`, and
  research rows.
- New commits that arrive with a hint still sometimes get through: 117 error entries
  report `hood_drained` ≥ 1.

**Effect:** the agent and session pages for 46 bob-cli runs are not in bob-cli's
agents sidecar. These include all of `bob-cli-gr.1`–`.17`, `gm.land`, `gj.land`, and
`h3.land`.

### 3. Two smaller, separate problems

- **Deferred prompt-archive restore (23 entries).** `.land` coder runs keep their
  prompt only as `followup_prompt.md`, and the planner archive names the `--plan`
  member. The fail-closed gate therefore quarantines the row after three attempts.
  13 more bob-cli rows have been quarantined this way since Nov 2. This problem is
  self-limiting and unchanged.
- **SSH publickey denial (57 entries, now gone).** GitHub's Nov 4 SSH incident broke
  the job's sidecar `git pull --rebase` for about 1¾ hours. It cleared by itself because
  the job retries every pass. Epic `sase-1r5` (landed Nov 4 09:20) added credential
  retries for network git. `src/sase/agents_sync/` still has no credential retry, and
  the follow-up bead `sase-1r7` does not list the publication transaction path. This is
  low priority because the job's own cadence already retries it.

## Why nothing has fixed it

- **The code is unchanged.**
  - `crates/sase_core/src/note_attachment/scanner.rs:178` on sase-core master still
    has the unanchored `sk-[A-Za-z0-9_-]{20,}`.
  - `publication_job.py` was last changed Oct 30.
  - The 50+ sase commits since Nov 2 cover handoff staging, agent hijack, workspace
    retention, release steward, and SSH retries. None touches the scanner, the ledger,
    the no-charge park, or the drain loop.
- **No bead tracks the fix.** Since the Nov 2 report, no task bead has been filed for
  the `openai-key` false positive or for the drain head-of-line block.
  - `sase-1qh.7` ("Clear the already-stuck planner and research rows") has been
    `in_progress` since Oct 31. It is blocked at its own precondition and predates this
    bug.
  - `sase-1ot` (purge 27 historical scanner hits) is still `ready`. It should re-check
    those hits under a corrected rule first, because some are likely `task-` false
    positives.
- **The noise hides real errors.** Publication is 99.6% of digest entries. For example,
  the latest digest's `workspace_sdd_clone_recovery` failure for bob-cli's beads clone
  sits among 35 publication entries.

## What would stop it

These are the fixes the Nov 2 report proposed, ordered by impact. All are still
unimplemented.

1. **Anchor the rule in sase-core.** For example, use `(?:^|[^A-Za-z0-9_-])sk-…`. Add
   regression fixtures for `task-` names, then bump sase's `sase-core-revision.txt`
   pin. This stops new false blocks.
2. **Revalidate the five stored blocks through an audited path.** The rule fix alone
   does not free them, because the ledger keys on content hashes that will never
   change.
3. **Stop the head-of-line block.** On a hinted-batch error, exclude the failing keys
   and still run the fallback drain. Do not count a confirmed block as a job error.
   This alone would drain the 46 starved rows and stop most of the digest noise, even
   before 1 and 2 land.

Until then, expect about 65–80 digest entries an hour from bob-cli, and a bob-cli
backlog that grows with every hint-less run.
