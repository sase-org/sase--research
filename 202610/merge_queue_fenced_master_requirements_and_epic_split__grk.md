# Reassessment: merge-queue-fenced `master`, exact-SHA releases, and epic split

> **Research query:** Reassess the solution in
> `merge_queue_fenced_master_and_exact_sha_releases.md`. Change requirements where
> warranted (call each change out). Recommend a single epic or multiple epics, with
> justification and independent verification steps if split.

**Researcher:** grk · **Date:** 2026-10-17 · **Checkout:** sase `60718e5b1b`

**Source proposal:**
`research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
(consolidated lead report, sase `4cb33feae9`).

**Verdict:** keep the architecture (native merge queue + exact-SHA publish + a
trustworthy gate). Split the work into **three epics**. Do not ship it as one epic, and
do not put “publish 0.18.0” inside any of them.

---

## Bottom line

1. **The proposal’s architecture is still right.** `master` is unprotected, agents
   rebase-and-push without testing the combined tree, `publish.yml` builds whatever
   `master` is at job start, and Full CI has not produced a green run in the last 30
   samples. A GitHub merge queue with zero approvals is the fence. Exact-SHA
   qualification is the release path. A host-side landing lane is not a fence.
2. **Several requirements in the proposal should change.** The important ones:
   do not fold `visual-test` into Master Gate; do not treat “ship 0.18.0” as part of
   this design; do not call `ci.yml` as a reusable workflow on `github.ref` of
   `master`; do not claim `decisions:ci-two-speed-split`’s reopen trigger is fully
   met; defer tag protection until landings use a non-maintainer identity; cap
   merge-group size at 1 for the pilot.
3. **This is three epics, not one.** They share a sequence, not a workstream. Each
   has its own product, repos, failure mode, and proof. Bundling them would collide
   with the in-flight 0.18.0 repair epic (`sase-1lh`) and would make the lander
   own unrelated SLO, GitHub, and sase-core work at once.

**In one line:** keep the native queue and exact-SHA publish; drop the “release
checks must all block merges” rule and the 0.18.0 cargo; implement as three epics
(honest publish, trustworthy gate, merge-queue fence).

---

## Method

Independent reassessment. I did not read the original swarm’s `__cdx` / `__cld` /
`__gem` / `__grk` / `__mus` inputs, and I did not read this swarm’s peer reports.

**Audited reads**

- `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
- `research:202610/gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md`
- `research:202610/github_native_merge_queue_primer/github_native_merge_queue_primer__final.md`
- `research:202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`
- `decisions:ci-two-speed-split`, `check-full-is-explicit`,
  `receipts-prove-before-they-skip`, `rust-core-required`,
  `triage-annotates-does-not-change-exit-codes`, `host-owned-completion`
- `sase_flags.md`, `sase_beads.md`, `sase_artifacts.md`

**Code (this checkout, plus `sase repo open sase-github`)**

- `.github/workflows/{publish,master-gate,ci,full}.yml`
- `tests/test_github_actions_{publish,ci_master_gate,ci_workflow}.py`
- `tools/_release_watch_{api,engine}.py`
- `src/sase/vcs_provider/plugins/_git_commit_dispatch.py`
- `sase-github` `src/sase_github/workspace/submit.py`

**Live measurements, 2026-10-17**

- `GET …/branches/master/protection` → 404; `GET …/rulesets` → `[]`
- PyPI `sase` **0.17.1**, uploaded 2026-08-29T23:22Z (49 days)
- PR **#299** still open; `release-core-floor-smoke` **SUCCESS** at 15:41Z
- Repo: public; merge commits on; squash/rebase off; **`allow_auto_merge`: false**;
  `delete_branch_on_merge`: false
- Master Gate last 100 runs on `master`: **9 / 97 completed succeeded (9.3%)**;
  wall p50 **12.5 min**, p90 **19.3 min**; interarrival p50 **17.0 min**, mean
  **27.3 min** ≈ **53 landings/day**; **42.4%** of gaps shorter than 12.5 min
- Newest completed gate (`f2a7b802f9`, run 39061530695): lint/docs/core-wheel and
  shards 1–7 green; **shard 8 red** (flake-shaped)
- Three Master Gate runs overlapping at 19:53–19:55Z (two in progress, one queued)
- Full CI last 30 runs: **0 successes**, 29 failures, 1 in progress
- No committed `.python-version`

**External**

- GitHub Docs: [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue);
  [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)
- [Merge queue GA](https://github.blog/changelog/2023-07-12-pull-request-merge-queue-is-now-generally-available/)
  (public org-owned repos)
- [2026-04-23 incident `zsg1lk7w13cf`](https://www.githubstatus.com/incidents/zsg1lk7w13cf)

---

## What I independently confirmed

The proposal’s factual core still holds, hours after it was written.

| Claim | Independent check | Result |
| --- | --- | --- |
| No branch protection / rulesets | `gh api` protection 404, rulesets `[]` | Confirmed |
| `publish.yml` builds the tip, not the release SHA | `build` job is `actions/checkout@v4` with no `ref:`; `release` outputs only `release_created` | Confirmed. The only `ref:` in the file is the pending `release-please--branches--master` checkout in `sync-release-metadata` |
| `ci.yml` cannot be aimed at a SHA | `on.workflow_call` has **no inputs**; concurrency is `ci-${{ github.ref }}` with `cancel-in-progress: true` | Confirmed, and this is a design hole in Phase 0 as written |
| Master Gate is post-push only | `on: push` / `workflow_dispatch` only; contract test `test_master_gate_triggers_on_master_pushes_and_manual_dispatch_only` **forbids** other triggers | Confirmed. Adding `merge_group` is a contract-test change |
| Gate jobs ≤ 20 min | `test_master_gate_jobs_stay_within_the_twenty_minute_ceiling` | Confirmed |
| `visual-test` is a 45-minute Full CI job | `ci.yml` `timeout-minutes: 45`; comment cites a 30m7s first pass | Confirmed. It cannot join Master Gate without breaking the 20-minute ceiling |
| Release watch looks up gates by branch | `_run_list("master-gate.yml", branch="master")` and the same for `full.yml` | Confirmed |
| Watcher still requires a green Master Gate at HEAD | `_check_master_gate` → `MASTER_GATE_RED` after `max_red_gate_minutes` | Confirmed |
| Agent landings are direct pushes | `_push_current_branch_with_rebase_retry` does `git push origin <current-branch>` with rebase retries | Confirmed. This is **not** the sase-github `gh pr merge` path |
| `gh pr merge` exit 0 treated as merged | `_submit_via_pr_merge` finalizes on return code 0, prints “PR merged successfully” | Confirmed for the Patch-submit plugin. It is **not** today’s agent landing path |
| Merge commits only | API: `allow_merge_commit` true, squash/rebase false | Confirmed |
| Auto-merge is off | `allow_auto_merge: false` | Confirmed. Phase 2’s `gh pr merge --auto` needs this flipped |
| PyPI stall / PR #299 | 0.17.1 since 2026-08-29; #299 open; floor smoke green today | Confirmed |
| Queue is available | Public org-owned repo | Confirmed against the GA changelog |
| Capacity math | 53/day × 12.5 min ≈ **11 gate-hours/day**; K=2 supplies 48 | Confirmed. Capacity is not the constraint. Flakes are |
| April 2026 incident | Status page resolved text: squash multi-PR groups were wrong; **merge-method groups were not named as affected** | Confirmed enough to keep merge commits. See [Adjustment P](#adjustment-p---pilot-merge-limit-1) |

**Where my numbers differ from the proposal**

- Newest-100 Master Gate pass rate is **9.3%** here, not 27%. The last twelve
  completed runs are all red. The Oct 13–15 green window has closed.
- Landing cadence in this 45-hour window is **~53/day**, not 42.9. Overlap at
  42.4% still matches.
- Three Master Gate runs were in flight at once, so today’s push path already
  exceeds K=2 concurrency. A queue with `max_entries_to_build: 2` **caps**
  concurrency relative to now; it does not increase it.

---

## Requirement adjustments

Each item is a change to the source proposal. Unchanged requirements are listed
after this section.

### Adjustment K — do not fold `visual-test` (or 3.13/3.14, or perf-floors) into the merge gate

- **As proposed (Phase 1.4 and Adjustment F):** “Make the release gate part of
  the merge gate. Fold `visual-test` (check mode, sharded) into the gate.”
  Adjustment F: “Anything that can block a release must also block merges.”
- **Adjusted requirement:** **Every release-blocking check has exactly one home:
  the merge gate, or exact-SHA qualification.** Visual, the 3.13/3.14 matrix,
  tutorial tests, and perf-floors stay on qualification. They get an owner and a
  deadline there. They do not become required merge-queue checks.
- **Why:**
  - Master Gate’s contract is a **20-minute** per-job ceiling.
    `visual-test` is a **45-minute** job whose last cited first pass was 30m7s.
  - `decisions:ci-two-speed-split` moved the exhaustive lane off the push path
    on purpose. Putting it back into every landing restores the capacity problem
    that split was written to end.
  - Visual PNG equality is already a dominant flake source. Folding it into the
    queue would **raise** the false-red rate the queue cannot tolerate.
  - Literal Adjustment F contradicts the same document’s “Do not put Full CI in
    the queue.”
- **This is the largest requirement change.**

### Adjustment L — ship 0.18.0 is out of scope

- **As proposed (Phase 0.5):** finish `sase-1lh` Full CI repairs, merge #299,
  qualify, publish 0.18.0.
- **Adjusted requirement:** **This design does not ship a version.** 0.18.0
  already has an in-progress epic (`sase-1lh` and descendants). A new epic that
  also “ships 0.18.0” will race it, inherit its red Full CI, and never land.
- **Why:** Repairing today’s Full CI and changing the landing/release machinery
  are different products. The new machinery must be able to publish *a* SHA; it
  must not be the 0.18.0 release train.

### Adjustment M — qualification must not share `ci.yml`’s cancel-in-progress group

- **As proposed (Phase 0.2):** “Add a `qualify` job: call `ci.yml` as a reusable
  workflow on that SHA, which needs a `ref` input.”
- **Adjusted requirement:** Qualification is a **SHA-keyed** workflow. It may
  reuse job definitions, but it must not run under `concurrency.group:
  ci-${{ github.ref }}` with `cancel-in-progress: true` while `github.ref` is
  `refs/heads/master`.
- **Why:** `full.yml` already calls `ci.yml`. A scheduled Publish on `master`
  would share `ci-refs/heads/master` with Full CI and **cancel the heavy lane**
  (or be cancelled by it). `ci.yml` currently has **no** `workflow_call` inputs,
  so “needs a `ref` input” is a larger change than the proposal’s wording
  suggests: every job that checkouts must honor it, and `GITHUB_SHA` in a
  scheduled Publish run is the tip, not the tag.
- **Preferred shape:** a dedicated `qualify.yml` (or `workflow_dispatch` on a
  SHA) with `concurrency: qualify-${{ sha }}` and `cancel-in-progress: false`,
  which `uses:` the same reusable jobs. Publish then `needs:` that run by SHA.

### Adjustment N — tag rulesets wait for a non-maintainer landing identity

- **As proposed (Phase 0.1):** add a `v*` tag ruleset so only the release
  identity can create tags.
- **Adjusted requirement:** **Do not add a tag ruleset in the first epic.** Add
  it in the merge-queue epic’s later phase, **after** landings use a GitHub App
  (or other identity that agents do not hold). Until then the maintainer’s
  credentials are every agent’s credentials, so the ruleset is theatre.
- **Why:** the proposal already says this “only helps once the release identity
  differs.” Putting it in “this week / Phase 0” implies a fence that does not
  exist.

### Adjustment O — `ci-two-speed-split`’s reopen trigger is only partly met

- **As proposed:** the decision’s reopen trigger has been met, so a new record
  should replace the merge-queue rejection.
- **Adjusted requirement:** **Write a new decision because the rejected
  alternatives no longer describe this queue, not because p50 “no longer fits
  the cadence.”** Keep the rest of `ci-two-speed-split` (per-SHA fast gate,
  heavy lane off the push path, `ci_watch` freshness).
- **Why:** p50 wall is still 12.5 min; p50 interarrival is 17 min. A 42% overlap
  is the never-cancelled per-SHA design working, not a gate that cannot keep up.
  The August rejection was “no attributable per-SHA signal, or it eats the
  account.” A queue that builds one group commit per PR **does** produce a
  per-SHA signal, and 11 gate-hours/day at K=2 is well under 48. That is the
  argument. Overstating the reopen trigger will make the new record easy to
  attack.

### Adjustment P — pilot merge limit 1

- **As proposed:** group size min 1, max 5, 0–1 min wait; method merge;
  concurrency 2; `ALLGREEN`.
- **Adjusted requirement:** **During the pilot, `max_entries_to_merge` is 1.**
  Raise it only after the watcher has proven landed SHA = tested group SHA on
  real sase traffic.
- **Why:** GitHub’s own post-incident write-up says internal tests “primarily
  exercised single-PR merge queue groups.” Docs also say a successful later
  group can land the whole prefix in one `master` update. Max 1 keeps
  attribution and the tree-equality proof trivial. The primer already
  recommended this. Concurrency 2 can stay; that is how many groups **build**,
  not how many land at once.

### Adjustment Q — auto-merge is a real prerequisite, and it is currently off

- **As proposed (Phase 2 repo settings):** enable auto-merge.
- **Adjusted requirement:** **Flip `allow_auto_merge` on as part of the
  merge-queue epic’s GitHub settings work, before any agent uses `gh pr merge
  --auto`.** Treat it as a checked prerequisite, not a footnote.
- **Why:** live API returns `allow_auto_merge: false`. Without it, `--auto`
  cannot arm the queue.

### Adjustment R — agent landings and Patch submit are different paths

- **As proposed:** “sase-github treats queued as merged” is presented as the
  landing bug, and the queue mode is described as a commit-finalizer change in
  the same breath.
- **Adjusted requirement:** **Queue mode is a new `builtin@commit` path**
  (commit, push `sase/land/<agent>`, `gh pr create`, `gh pr merge --auto
  --match-head-commit`, prove queued, end the turn). **Patch submit’s
  `_submit_via_pr_merge` is a separate bug** on the human GitHub-PR flow. Fix
  both in the merge-queue epic; do not treat the plugin bug as today’s agent
  lander.
- **Why:** agents land through `_push_current_branch_with_rebase_retry`.
  `submit.py` is not on that path. Confusing them will make the first
  implementation edit the wrong file and leave the finalizer pushing `master`.

### Adjustment S — 3% false-red is an **enforcement** gate, not a pilot gate

- **As proposed (Phase 1 exit, then Phase 2 alongside):** under 3% false reds
  for 7 days before (or while) piloting.
- **Adjusted requirement:** **Pilot on a traffic allowlist (docs, `toobig`,
  ratchet bots) at the current flake rate, with measurement.** **Do not enforce
  (empty bypass list, default-on flag, drop push-triggered gate) until false
  reds are under 3% for 7 days on that allowlist.**
- **Why:** the simulation is right that 30% false reds double p95 and eject
  good changes. A low-traffic pilot is how you measure that on *queue* builds,
  which are `merge_group` runs, not `push` runs. Waiting for 3% on today’s
  post-push gate before any `merge_group` wiring delays the only experiment
  that can falsify the simulation.

### Adjustment T — “a release-qualified SHA under 24 h old” is a later SLO

- **As proposed (Adjustment A):** a release-qualified SHA under 24 h old exists
  and gets published on a cadence.
- **Adjusted requirement:** **Keep the cadence SLO (≤ 7 days, then 1–3 days)
  as a goal of the whole program.** Do not make “24 h old qualified SHA” an
  acceptance criterion of the first epic. The first epic’s bar is: **given a
  SHA, the pipeline builds, qualifies, and publishes that SHA and no other.**
- **Why:** Full CI is 0/30 in this sample. A 24-hour qualified SHA cannot exist
  until the heavy lane is actually green. That is `sase-1lh`’s job. Exact-SHA
  machinery must be provable on a SHA that *would* qualify, including a
  deliberately failing one.

### Adjustment U — landing records live in `sase-core`; queue mode is a beta flag

- **As proposed:** landing-record state machine in `sase_core`, GitHub adapter
  in sase-github, Python/TUI consume; queue mode behind a feature flag.
- **Adjusted requirement:** **Keep this, and make the flag rule explicit.**
  Create the flag with `sase flag new` (`beta`, default off). Off = today’s
  direct push (only legal while the ruleset is disabled). On = queue landing.
  Removing the flag deletes the Off branch. Tests cover both states. The
  landing record is core because TUI, CLI, and any later frontend must agree
  on queued / merged / ejected / superseded (`decisions:rust-core-required`).
- **Why:** `sase_flags.md` forbids hand-rolled flags. Off-branch reachability
  is the outage hatch the proposal wants. Core placement matches the litmus
  test already in the proposal; it also means the merge-queue epic includes a
  sase-core pin bump.

---

## Requirements I would keep

These stay, with the adjustments above applied around them.

- **A (cadence, not “HEAD is always green”)** — keep as a program SLO; see T.
- **B (two tiers: gate-green vs release-green on one SHA)** — keep. Release-green
  is qualification, not the merge queue.
- **C (service levels, not “always”)** — keep the numbers; attach 3% to
  enforcement (S).
- **D (one server-enforced admission path; PRs as plumbing; zero approvals)** —
  keep. Self-approval deadlock is real: agents push as the maintainer.
- **E (publish exactly the qualified files)** — keep. Also replace
  `publish_existing` with an explicit tag/SHA input and digest check. Keep
  `skip-existing: true` only after the digest check, or a partial re-upload
  can mix two builds.
- **G (trustworthy gate before enforcement)** — keep, scoped by S.
- **H (landed ≠ agent finished; beads and `%w(bead=…)` wait for merge proof)** —
  keep. This is the real host work. It fits `host-owned-completion` (the
  **host** opens the PR) and `single-turn-agents` (the turn ends at queued;
  a chop/service reconciles; the agent does not wait).
- **I (releasable includes published `sase-core-rs` floor)** — keep.
- **J (admission covers every writer)** — keep. Empty bypass list. Break-glass
  is disabling the ruleset, which GitHub audits.
- **Merge method MERGE** — keep. Incident resolved text did not blame merge
  commits; merge commits keep the agent SHA as a parent.
- **No human approvals, no LLM merge verdicts, no host-side `just check` as
  the fence, no Full CI in the queue, no `stable` branch for release-please,
  no third-party queue at this volume** — keep.

---

## What I would not do (additions)

- **Do not reopen a host landing lane as a stepping stone.** Local `check` is
  still a pre-flight only. Receipts remain proof, not skip
  (`decisions:receipts-prove-before-they-skip`). A per-host flock still cannot
  order athena against apollo (the proposal’s 649 vs 73 footer split still
  applies in spirit; I did not re-count footers).
- **Do not require “up to date” without a queue.** At 42% overlap it is a
  rebase mill.
- **Do not launch another “green CI then ship 0.18.0” epic.** `sase-1lh` is
  already that epic. Eight predecessors failed for lack of a fence; a ninth
  without a fence will too. The fence is Epic 3. The 0.18.0 ship is `sase-1lh`.
- **Do not drop the push-triggered Master Gate in the same change that adds
  `merge_group`.** Keep it as an audit until SHA lookups are proven.

---

## Epic recommendation: three epics

### Why not one epic

A single epic that ran Phases 0–3 would mix:

- a **publish-pipeline** change (`publish.yml`, qualification, watcher SHA
  lookups) that can land and help PyPI **with `master` still directly pushed**;
- a **test-infra** change (rerun-once, expiring quarantine, `.python-version`)
  whose proof is a 7-day flake SLO;
- a **distributed landing** change (sase-core records, sase-github adapter,
  commit finalizer, GitHub ruleset, bead-close-on-merge) whose proof is a
  scratch-repo drill plus a flagged pilot.

Those have different sizes (S–M, M, L), different repos, different rollback
stories, and different “we are done” tests. One lander cannot honestly close
that. `sase_sizes.md` already says work that large belongs in an epic *plan*,
not a single medium implementation; this is larger than one epic.

A single epic also swallows 0.18.0 (Adjustment L) and will sit behind Full CI
reds that are not its scope.

### Why not five

Cheap force-push/delete protection is too small to be an epic; it is a phase of
Epic 3 (it only matters once admission is server-side). Watcher SHA lookups
belong with the consumer: release qualification (Epic 1) and landing
reconciliation (Epic 3). Decision records belong in the epic that makes them
true. Pilot vs enforce are **phases of Epic 3**, because a forever-pilot with
no owned cutover is how fences rot. Enforce has its own verification list
below; it is not a fourth epic unless the pilot has to sit in production for
weeks under a different owner.

### Sequencing (depends-on, not same-epic)

```text
Epic 1  Exact-SHA publish        ── independent; unblocks honest releases
Epic 2  Trustworthy Master Gate  ── independent; can start in parallel
Epic 3  Merge-queue fence        ── may start its scratch-repo + merge_group
                                    wiring in parallel; enforcement waits
                                    on Epic 2’s flake SLO (Adjustment S)
sase-1lh  ship 0.18.0            ── already in flight; not in this program
```

Epic 1 does not wait for a green `master`. Epic 3’s **pilot** does not wait
for 3% flakes. Epic 3’s **enforcement** does.

---

## Epic 1 — Exact-SHA PyPI qualification

**Goal.** Given a release SHA, build it once, run the heavy matrix on **that**
SHA, publish **those** files, and refuse to publish any other tree.

**Size.** S–M.

**In**

- Plumb `release-please-action`’s `sha` (and tag/version) through `publish.yml`
  job outputs.
- `build` checks out `ref: ${{ needs.release.outputs.sha }}` and asserts tag,
  SHA, `pyproject.toml`, and `__version__` agree.
- A SHA-keyed **qualify** workflow (Adjustment M) runs the current Full CI
  contents on that SHA. Publish `needs:` qualify plus both install smokes.
- Pass dist files as artifacts; record digests; republish checks digests
  before `skip-existing`.
- Replace boolean `publish_existing` with an explicit tag or SHA input.
- Release watcher: look up Master Gate / Full CI / Publish **by SHA**. Relax
  “fresh Full CI on some recent SHA” to “qualification of the exact candidate.”
  Surface “GitHub release exists, PyPI does not” as its own state.
- Keep `CORE_FLOOR_BLOCKED` until the published `sase-core-rs` floor matches
  the SHA (Adjustment I).
- Decision record: “PyPI publishes exactly the qualified release SHA.”

**Out**

- Shipping 0.18.0 / merging #299 (Adjustment L).
- Tag ruleset (Adjustment N).
- Merge queue, rulesets on `master`, finalizer changes.
- Folding visual into Master Gate (Adjustment K).

**Depends on.** Nothing in this program. May land while `master` is red.

**Independent verification** (none of this requires a queue or a flake SLO):

1. Contract tests: `build` / qualify / publish jobs pin `ref` to the release
   SHA; `release` job outputs `sha`; no checkout of implicit `github.sha` on
   those jobs.
2. Contract tests: qualify concurrency is SHA-keyed and does not use
   `ci-${{ github.ref }}` with `cancel-in-progress: true`.
3. A `workflow_dispatch` of Publish on a **known historical SHA** while
   `master` HEAD is a **different** SHA produces artifacts whose
   `sase --version` / embedded version / recorded SHA match the historical
   SHA, not HEAD. Prove with artifact digests.
4. Dispatch qualify on SHA A while Full CI is running on `master`; Full CI is
   not cancelled.
5. Qualify of a SHA that is red on visual or 3.14 **blocks** publish.
6. Digest mismatch on a republish **blocks** upload.
7. Watcher unit tests: a green Full CI on SHA B does not satisfy qualification
   of SHA A; a missing `master-gate.yml` run for branch=`master` does not
   make the watcher blind if a SHA-keyed run exists.
8. `just check` on the workflow and watcher tests.

**Done when.** A human can point Publish at one SHA and the system either
publishes that SHA’s files or refuses. HEAD color is irrelevant to that proof.

---

## Epic 2 — Trustworthy Master Gate

**Goal.** The fast per-SHA gate is a signal: false reds are rare enough that a
later queue will not become a random ejector. Local Python/core parity stops
lying.

**Size.** M.

**In**

- Inside each Master Gate test shard: on failure, if the failed-node count is
  small (cap ~3), rerun those node IDs **once**, serially. A pass-on-rerun
  annotates `FLAKY:` and files or `+1`s a `flake` bead by failure signature.
  This is a CI policy, recorded as its own decision next to
  `triage-annotates-does-not-change-exit-codes` (CI may change the **job**
  conclusion after a successful rerun; local ToolRun triage still must not
  change the child’s exit code).
- Expiring quarantine list: node, bead, owner, expiry ≤ 14 days. Quarantined
  nodes still run in a non-required job. Expired entries fail lint.
- Commit `.python-version` = `3.12`; `just install` honors it.
- Fail fast when the local core checkout differs from `sase-core-revision.txt`.
- `if: always()` on Master Gate steps that a red `just lint` currently skips
  (`validate`, `validate-committed-plans`, `build-check`), so later gates
  still report.
- Measure false-red rate from `FLAKY:` annotations for 7 days.

**Out**

- Folding `visual-test` into Master Gate (Adjustment K). Jobs stay ≤ 20
  minutes. `test_master_gate_jobs_stay_within_the_twenty_minute_ceiling`
  remains true.
- Moving Full CI from every 2 h to nightly. That is a capacity tweak for
  Epic 3, not gate trust. Do it in Epic 3 if runner waits grow, not here.
- Merge queue, rulesets, finalizer, 0.18.0.

**Depends on.** Nothing. Can parallelize with Epic 1.

**Independent verification**

1. A fixture shard that fails once then passes is green, emits `FLAKY:`, and
   does not fail the job. A shard with >3 failed nodes does **not** rerun and
   stays red.
2. A quarantined node does not fail `integration` of the required jobs; it
   still runs in the non-required job. An expired entry fails a lint/contract
   test without waiting for CI.
3. `.python-version` is `3.12`; a contract test pins it. Local install without
   3.12 fails fast in a unit test of the installer hook.
4. Core-mismatch fail-fast has a unit test on a fake revision file.
5. Master Gate YAML: no `visual-test` job; every job `timeout-minutes <= 20`;
   triggers still `{push, workflow_dispatch}` until Epic 3.
6. Operational: 7 consecutive days of Master Gate on `master` with
   false-red-per-build **< 3%**, computed from `FLAKY:` vs residual reds that
   rerun still failed. Publish the series. This SLO is Epic 3 **enforcement**’s
   input, not Epic 2’s only done-when (the mechanism can land earlier).

**Done when.** The rerun/quarantine/parity mechanisms are in production and
measurable. The 7-day SLO is a follow-on observation, not a reason to keep the
epic open if the mechanism is proven.

---

## Epic 3 — Merge-queue landing fence

**Goal.** No deterministic break reaches `master` by any writer. “Landed” is
proven merge, not a successful `git push` or a `gh pr merge` exit 0.

**Size.** L. Phases: (1) scratch rehearsal + wiring, (2) flagged pilot,
(3) enforce. One epic so the cutover has an owner.

**In**

- Scratch public repo in `sase-org` to pin undocumented behaviors.
- `master-gate.yml`: add `pull_request` + `merge_group: types: [checks_requested]`;
  aggregate `integration-ready` with `needs:` of every required job and
  `if: always()`; on `pull_request`, skip expensive jobs at **job** `if:`
  (skipped job = Success per GitHub docs); **no path filters** on the
  required workflow (skipped workflow = Pending). Update
  `test_master_gate_triggers_on_master_pushes_and_manual_dispatch_only`.
- Drop `ci.yml` `pull_request` for ordinary agent PRs, or every landing starts
  the ~100 min heavy lane. Keep `workflow_call` for Full CI and Epic 1
  qualify. Keep `release-core-floor-smoke` as an explicit required check on
  the release PR (it is `if:`’d on the release-please branch name today, which
  **does not exist** on `merge_group`).
- Repo settings: enable auto-merge (Adjustment Q); delete-branch-on-merge;
  merge-commit message “PR title and description”; method MERGE; build
  concurrency 2; **merge max 1** (Adjustment P); `ALLGREEN`; 60 min timeout.
- Ruleset on `master`: required PRs with **0 approvals**; require merge queue;
  require check `integration-ready`; block force-push and deletion; **empty
  bypass list**. Force-push/delete protection can land at the start of this
  epic; the require-queue rule lands at enforcement.
- `sase flag new` for queue landing mode (Adjustment U).
- `builtin@commit` queue path (Adjustment R): push `sase/land/<id>`, create PR,
  `gh pr merge --auto --merge --match-head-commit <sha>`, prove **queued**,
  end the turn.
- Landing records in `sase-core`; GitHub adapter in sase-github; watcher as an
  axe chop or service (no LLM). States: queued → merged | ejected |
  superseded. Merge proof: PR `mergedAt` + `mergeCommit`; agent SHA is an
  ancestor; `master` tree equals the tested group commit (under max 1 this is
  SHA equality). Only then close the bead, resolve `%w(bead=…)`, update
  STITCHES.
- Ejection: conflict → existing repair turn; known flake signature →
  re-enqueue once; deterministic → one or two forked repair turns; then a
  `/sase_gate`. Agents never wait.
- Fix `_submit_via_pr_merge` (queued ≠ merged) in the same epic.
- SHA lookups in `ci_watch` / any remaining branch-keyed consumers.
- Decision: “`master` lands only through the merge queue,” superseding only
  the merge-queue clause of `ci-two-speed-split` (Adjustment O). Refines
  `host-owned-completion`: queued completes the **turn**; merged completes the
  **landing**.
- Optional, if Epic 2’s runner waits grow: move Full CI to nightly +
  candidates.

**Out**

- Exact-SHA publish (Epic 1).
- Flake rerun/quarantine (Epic 2), except Epic 3 **enforcement** consumes
  Epic 2’s SLO.
- 0.18.0.
- Tag ruleset until App identity exists (Adjustment N). Add a follow-up phase
  or `PROPOSED FOLLOW-UP` for the App identity + tag ruleset + maintainer
  bypass that agents do not inherit.

**Depends on.** Enforcement depends on Epic 2’s flake SLO (Adjustment S).
Wiring and scratch rehearsal do not.

### Independent verification — scratch repo (no sase production traffic)

1. Required check runs on `merge_group` and reports `integration-ready`.
2. A PR whose `pull_request` jobs are skipped still cannot land until
   `merge_group` actually ran the expensive jobs. A job-level `if:` that
   skips the expensive jobs on `merge_group` must **fail** this test
   (that is the dangerous Success-on-skip case).
3. Direct `git push origin master` with maintainer credentials is refused
   once the PR + queue rules are on. Record the exact GitHub error.
4. Two PRs that each pass against `master` but fail together: the second is
   ejected; `master` does not move.
5. A failing required check ejects the PR; `master` SHA is unchanged.
6. After a simulated host restart, the watcher re-reads queue state and does
   **not** open a second PR for the same head SHA.
7. `gh pr merge --auto --merge` exit 0 leaves the PR **open/queued**, not
   merged; the watcher reaches `merged` only after `mergedAt`.
8. Landed `master` SHA equals the tested `merge_group` SHA (max 1).

### Independent verification — flagged pilot on sase (allowlist traffic)

1. Flag off: behavior is today’s direct push (ruleset still not requiring the
   queue). Both-states tests exist.
2. Flag on for allowlisted agents: beads stay open while queued; `%w(bead=…)`
   does not resolve; STITCHES does not flip to landed.
3. On merge: bead closes; waiters resolve; `master` contains the agent SHA;
   tree equals the group commit.
4. On flake ejection: at most one automatic re-enqueue; a second failure
   files a flake bead and stops.
5. On deterministic ejection: a repair turn is launched; no silent close.
6. Metrics for ≥ 7 days: landing p50/p95, ejections by class, runner wait p90,
   false-red rate **on `merge_group` builds**.
7. Push-triggered Master Gate still runs and is compared to the queue result
   (audit, not admission).

### Independent verification — enforcement

Do not start until Epic 2’s 7-day < 3% false-red series exists **or** the
pilot’s own `merge_group` false-red rate is under 3%.

1. Ruleset required; bypass list empty; a direct push by an agent is refused.
2. Queue mode is the default (flag On is unconditional, or the Off branch is
   deleted when the flag is removed — only after the outage hatch is
   documented as “disable the ruleset”).
3. A failing candidate never moves `master`.
4. Combined-tree failure still ejects (repeat of scratch test on sase).
5. Host restart still reconciles without duplicate PRs.
6. Watchers no longer query `--branch master` for gate greenness; SHA lookup
   is the only path. Then, and only then, drop the push-triggered Master Gate.
7. `just check` in sase, sase-github, and sase-core (pin ratcheted). No
   `just check-full` unless this epic is explicitly told to.

**Done when.** Enforcement checks 1–6 pass, the three decision records exist,
and a routine landing needs zero human intervention.

---

## Capacity and flake (sanity check, not a new simulation)

I did not rerun the proposal’s discrete-event sim. I checked the load it was
built on, with a later sample:

- ~53 landings/day × 12.5 min p50 ≈ **11.0 gate-hours/day**
- K=2 hosted concurrency → **48 gate-hours/day** of gate slots
- 42% overlap matches the proposal
- Newest red is a **single shard** on an otherwise green gate

Directionally the sim is right: **capacity is fine; a 30% false-red rate is
not.** I would not treat its exact p95 minutes (27–34 at 3–10% flakes) as a
promise. They assume FIFO, independent service times, and a 2% real-break
rate. Use them as a planning bound; believe the pilot’s measured p95.

GitHub docs confirm the sim’s costly rule: “Merge limits do not combine
`merge_group` builds.” Failure of the head PR rebuilds everyone behind it.
That is why Adjustment K (keep visual off the gate) and Adjustment S (do not
enforce at 30% flakes) matter more than K=2 vs K=1.

---

## Decision records (still three, ownership split)

| Record | Epic |
| --- | --- |
| “PyPI publishes exactly the qualified release SHA.” | Epic 1 |
| “CI reruns a failed node once, and quarantines flakes with an expiry.” | Epic 2 |
| “`master` lands only through the merge queue.” | Epic 3 (enforcement) |

Write them through `/sase_memory_write` when the epic makes them true, not in a
fourth paperwork epic.

---

## Risks that would change this split

- **If Epic 1 cannot qualify without a green HEAD** because release-please
  only tags `master` tip, keep Epic 1 but add a “qualify SHA then tag” step
  rather than merging it into Epic 3. Tag-on-green (hatch-vcs) remains the
  fallback the proposal already named, still inside Epic 1.
- **If `merge_group` cannot be required without also requiring the same named
  check on `pull_request`**, the cheap-PR-then-expensive-group design needs a
  different aggregate job. That is Epic 3 wiring, discovered on the scratch
  repo, not a reason to merge epics.
- **If false reds stay above ~10% after Epic 2**, delay Epic 3 enforcement;
  do not invent a host queue. Optionally turn `ALLGREEN` off (`HEADGREEN`) as
  a measured experiment, accepting weaker attribution.
- **If GitHub has another merge-queue correctness incident**, the flagged Off
  branch plus a disabled ruleset is the hatch. That is why the flag’s Off
  branch stays until soak, and why merge commits + max 1 stay.

---

## Sources

**This checkout** (`60718e5b1b`) and live GitHub/PyPI, 2026-10-17.

**Prior research (audited):** the source proposal; Gas Town comparison; merge
queue primer `__final`; Oct 1 master-CI-red report.

**Decisions:** `ci-two-speed-split`, `host-owned-completion`,
`receipts-prove-before-they-skip`, `rust-core-required`,
`check-full-is-explicit`, `triage-annotates-does-not-change-exit-codes`.

**Beads (collision check only):** `sase-1lh` and descendants still in
progress to green gates and ship 0.18.0; `sase-um` (two-speed CI) closed.

**External:** GitHub merge-queue docs and required-check troubleshooting;
merge-queue GA changelog; incident `zsg1lk7w13cf`.
