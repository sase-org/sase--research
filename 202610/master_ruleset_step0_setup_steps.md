# Steps to create the Step 0 `master` ruleset

> **Question:** I'm getting ready to create the "master ruleset" described by
> [`merge_queue_fence_reassessment_explained.md`](merge_queue_fence_reassessment_explained.md).
> Give me a concise numbered list of the steps I need to take.

The "master ruleset" is **Step 0** of the
[reassessment](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md).
It is a human admin change for today, and it is not part of any epic. It does two things:
it **blocks force pushes** and it **blocks deletion** of `master`. Nothing else.

I checked the repo through the API on 2026-10-17. `sase-org/sase` is **public**, and
`master` has **no rulesets and no classic branch protection** (`/rulesets` returns `[]`,
and `/branches/master/protection` returns 404). You have admin rights. The org is on the
**Free** plan, so org-level rulesets return 403. Create the ruleset at the **repo**
level; repo rulesets work on public repos on Free.

## Steps

1. **Keep the scope to two rules.** The ruleset needs only `deletion` ("Restrict
   deletions") and `non_fast_forward` ("Block force pushes"). Leave these for later:
   - the merge-queue, linear-history, required-PR and required-check rules, which are
     Epic D's D2 and D5. Turning any of them on today would refuse the agents' direct
     pushes to `master`;
   - the `v*` **tag** ruleset, which waits per N12.
2. **Record the "before" state** (optional, about 10 seconds):
   `gh api repos/sase-org/sase/rulesets` should print `[]`.
3. **Create the ruleset.** In GitHub, go to **sase-org/sase → Settings → Rules →
   Rulesets → New ruleset → New branch ruleset**, then set:
   - **Name:** something like `master-integrity`.
   - **Enforcement status:** **Active**.
   - **Bypass list:** **empty**. N9 says never to relax these two protections, so don't
     add yourself.
   - **Target branches:** **Add target → Include by pattern → `master`** (or "Include
     default branch"). Do **not** target all branches. release-please force-updates its
     own release-PR branch, and it must keep working.
   - **Rules:** check **Restrict deletions** and **Block force pushes**, and make sure
     every other rule is unchecked.
   - Click **Create**.

   The same thing from the CLI:

   ```bash
   gh api -X POST repos/sase-org/sase/rulesets --input - <<'EOF'
   {
     "name": "master-integrity",
     "target": "branch",
     "enforcement": "active",
     "bypass_actors": [],
     "conditions": {"ref_name": {"include": ["refs/heads/master"], "exclude": []}},
     "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]
   }
   EOF
   ```
4. **Verify by reading the rules back.** This is the reassessment's only sanctioned
   check:

   ```bash
   gh api repos/sase-org/sase/rules/branches/master --jq '.[].type'
   # expect exactly: deletion, non_fast_forward
   gh api repos/sase-org/sase/rulesets --jq '.[] | {name, enforcement}'
   # expect: master-integrity, "active"
   ```
5. **Don't test it destructively.** Never try `git push origin :master` or a force push
   on production. If the ruleset is wrong, that test deletes or rewrites `master`. Save
   destructive tests for Epic C's sandbox repo.
6. **Confirm normal landings still work.** Watch for the next ordinary agent push to
   `master` and the Master Gate run it triggers. The reassessment checked that nothing in
   sase force-pushes `master`, so fast-forward pushes should go through unchanged.
7. **Leave this ruleset alone when the queue arrives.** At D2 the maintainer goes on a
   bypass list for the pilot. Put the queue rules in a **separate** ruleset; don't add
   them here. A ruleset's bypass list exempts its actors from *every* rule in that
   ruleset. If the queue rules and the bypass were added to this ruleset, the pilot would
   quietly relax force-push and deletion protection, which N9 forbids. *(This step is my
   own inference from how GitHub rulesets work, not a statement in the reassessment.)*

## Sources

- [`merge_queue_fence_reassessment_explained.md`](merge_queue_fence_reassessment_explained.md):
  "Before the epics: Step 0" and the N9 and N11 rows. Read via `sase artifact read`.
- [`merge_queue_fence_reassessment_and_epic_split.md`](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md):
  "Step 0 - human admin change today" (the read-back command and the "not yet: `v*` tag
  ruleset" note), the N9 and N12 requirements, the rejected "delete `master` as a test"
  idea, and D2's bypass-list plan. Read via `sase artifact read`.
- Read-only GitHub API checks run on 2026-10-17: `repos/sase-org/sase` (visibility,
  permissions), `/rulesets`, `/rules/branches/master`, `/branches/master/protection`, and
  `orgs/sase-org/rulesets`.
