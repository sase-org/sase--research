# Reassessing the merge-queue-fenced `master` plan: revised requirements and a four-epic delivery

> **Research query:** Reassess the solution proposed by
> `merge_queue_fenced_master_and_exact_sha_releases.md` in the research sidecar repo. Make
> any changes to its requirements that are warranted, and call each change out clearly.
> Then recommend whether the work should be a single epic or multiple epics, with
> justification and independent per-epic verification steps if multiple are warranted.

**Consolidated report** · lead researcher · 2026-10-17 · sase `master` at `2cae86a1aa`.
Inputs: four independent reassessments
([cdx](merge_queue_fence_reassessment_and_epic_split__cdx.md),
[cld](merge_queue_fence_reassessment_and_epic_split__cld.md),
[grk](merge_queue_fence_reassessment_and_epic_split__grk.md),
[gem](merge_queue_fence_reassessment_and_epic_split__gem.md)) and my own checks.

**Report under review ("the original"):**
[`merge_queue_fenced_master_and_exact_sha_releases.md`](../merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md),
written at `4cb33feae9` earlier the same day.

## Bottom line

1. **Keep the architecture.** All four reassessments and my own checks agree on its core:
   - `master` is protected by GitHub's native merge queue.
   - Approvals are zero, and the PRs are admission tickets the host creates, not
     review requests.
   - PyPI publishes exactly the release commit that was qualified.
   - The gate is made trustworthy before it is enforced.

   The rejected alternatives stay rejected:
   - a host-side landing lane;
   - required PRs without a queue;
   - "must be up to date";
   - human approvals.
2. **Six requirement changes alter what gets built.** Each is backed by evidence the
   original did not have. All of them, with smaller corrections, are in
   [Requirement changes](#requirement-changes).
   - **Installability comes first (new).**
     - `pip install sase` resolves to **sase 0.1.0** today. The latest release (0.17.1)
       needs a `sase-core-rs` window that PyPI retention deleted.
     - cld found this, and I reproduced it.
     - The original never mentions it.
   - **Land with linear history (rebase, one commit per PR), not merge commits. This
     reverses the original.**
     - When PRs landed as merge commits in June, release-please listed three changes
       twice and dropped one agent commit. The evidence is sase's own `CHANGELOG.md`.
     - Today's history is linear: all 294 commits since Oct 10 have one parent.
   - **The queue fences landings, not drift (new).**
     - Time bombs, upstream releases and runner changes redden the base without any
       landing. When that happens, every merge group fails.
     - The design needs four additions: a base-red witness, a circuit breaker, a way to
       jump the queue with the fix, and a canary run under a shifted clock.
   - **Landing mode is per-project configuration, not a feature flag.**
     - SASE's flag rules forbid flags for choices users keep forever.
     - Beads keep closing the way they do today. Every *dependency* consumer becomes
       landing-aware.
   - **The release-blocking set becomes an explicit inventory.**
     - These block a release: the gate's checks, packaging checks, and tests on every
       supported Python version.
     - Visual, perf-floor and tutorial checks are advisory, each with an owner and a
       clock, until they are promoted.
     - `visual-test` does not join the merge gate by default.
   - **"Ship 0.18.0" leaves this program.** Existing beads own it.
3. **Deliver the work as four epics, plus two items that are not epics.**

   The two items outside the epics:
   - **Step 0**, a human admin change today: a ruleset that blocks force pushes and
     deletion on `master`.
   - **Track 0**, existing work: restore installability. It is owned by `sase-16p`,
     `sase-10d` and the `sase-1lh` chain.

   The four epics:
   - **A.** Exact-candidate releases and install guards.
   - **B.** A trustworthy gate.
   - **C.** Queue-aware landing as a SASE product feature, proven on a sandbox repo.
   - **D.** Cut `sase/master` over to the queue.

   How they fit together:
   - A, B and C run in parallel.
   - D starts once B's mechanisms are live and C passes its sandbox suite.
   - D's enforcement step waits for a measured soak.

   Two researchers (grk, gem) merged C and D into one epic. I keep them separate:
   - They prove different things in different places: C on a sandbox, D in production.
   - D is gated by human GitHub admin changes and by a soak that single-turn agents
     cannot wait out.

   Plan D at the same time as C, so the cutover has an owner from day one. That
   addresses grk's concern.

**In one line:** keep the native queue and exact-SHA publishing; switch to rebase; add
drift handling, an installability guard and landing-aware waits; drop 0.18.0 from scope;
and ship as A, B and C in parallel, then D.

## What changed since the original was written

Measured 2026-10-17, 20:10–20:40 UTC, unless a bead is cited.

- **The newest release cannot be installed.**
  - *Evidence:*
    - `uv pip compile` of bare `sase` on Python 3.12 resolves to `sase==0.1.0`.
    - `sase==0.17.1` fails: "only sase-core-rs>=0.34.23 is available and
      sase>=0.17.1 depends on sase-core-rs>=0.32.16,<0.33.0".
    - PyPI holds 51 core versions, the oldest being 0.34.23.
  - *Tracking:*
    - `sase-16p` (ready, +3, since Sep 22) and `sase-10d` (ready, +6).
    - The cause was epic `sase-13t`'s retention deletion.
  - *What it changes:* installability is requirement zero. Retention needs an invariant,
    and detection needs an install canary.
- **Sase's pinned core commit is in no published release.**
  - *Evidence:*
    - sase pins sase-core `916d5e3a`, the commit that adds `mobile_pairing_issue`.
    - No sase-core tag contains it; the newest tag is v0.41.0.
    - `pyproject.toml` still declares `sase-core-rs>=0.35.0,<0.36.0`.
  - *What it changes:* a release needs a sase-core release first. A core-floor smoke
    only detects this; it does not fix it.
- **Master Gate is worse.**
  - *Evidence:* 8 green of the 98 completed runs among the newest 100. The current red
    streak is 22 runs. The original counted 27 of 100.
  - *What it changes:* gate-trust work is more urgent, and enforcement is further off.
- **Full CI's failures moved.**
  - *Evidence:*
    - 0 of the last 29 runs were green.
    - `visual-test` *passed* in each of the last four failed runs, taking about 30 min (29–31).
    - The failures are `test (3.12/3.13/3.14)`, at 64–76 min each.
  - *What it changes:*
    - "Visual red in every run" (original) and "270 of 271" (gem) are stale.
    - Visual is still about 30 min against the gate's 20-minute per-job ceiling.
- **Merge commits already corrupted the changelog.**
  - *Evidence:* `master` has 103 merge commits (Feb–Aug), and release-please's June 0.1.x changelogs cover several of them. Three changes are
    listed twice, once under the merge commit and once under the agent commit:
    - "honor active venv…" in 0.1.1 (`b98e55c` and `0224105`);
    - "use PR terminology…" in 0.1.2 (`bbe05e9` and `90b8261`);
    - "validate setup dependency groups" in 0.1.4 (`d445153` and `02ccc79`).

    In 0.1.2, "reserve planned multi-prompt agent names" appears only under merge
    commit `5418147`; the agent commit `c6cb0f4` was dropped. The repo's merge-commit
    settings today are `PR_TITLE` / `PR_BODY`.
  - *What it changes:* this confirms cld's release-please reading on real sase history.
    Merge-method landings would make changelog entries nondeterministic.
- **History is linear.**
  - *Evidence:* all 294 commits since Oct 10 have one parent, at about 42 landings a
    day.
  - *What it changes:* the merge method would double the commit count and add
    non-linear history. History tools that read only first parents also exist
    (`tool/triage_inputs.py:87`).
- **Agents close their own beads.**
  - *Evidence:*
    - Templates tell agents to run `sase bead close` during the turn
      (`default_config.yml:2217`, `:2239`, `:2291`).
    - The finalizer closes the bead for both `create_commit` and `create_pull_request`
      (`workflow.py:645-661`).
    - Epic phases are sequenced on agent-done waits, not bead state
      (`work_prompt.py:207-212`); the land agent waits on `%w(bead=…)` for every phase bead (`:248`).
  - *What it changes:* "Beads close only on proof of merge" contradicts the bead
    lifecycle. The *waits* should change instead.
- **More code pushes to `master` than the finalizer.**
  - *Evidence:*
    - `ace/revert_agent_transaction.py:121` and `post_write_operations.py:74` (the TUI
      save-macro path);
    - humans running `sase stitch create`;
    - `ci_watch`, which lives in `bugyi-chops`: `ci_watch.py:1297-1302` runs
      `gh pr merge --merge --match-head-commit`, with a configurable merge method.
  - *What it changes:* the writer inventory must cover all of these.
- **sase-core retention does not protect consumers.**
  - *Evidence:* `.github/scripts/pypi_retention.py` keeps the newest 30 versions, plus
    any version named by hand with `--keep-version`.
  - *What it changes:* sase-core needs an automatic rule: never delete a version that a
    published sase release still needs.
- **GitHub's own documentation settles three questions.**
  - *Evidence:*
    - A PR enters the queue only "once [it] has passed all required branch protection
      checks".
    - Moving a PR to the top of the queue causes "a full rebuild of all in-progress
      pull requests".
    - The April 23 incident summary names "squash … when the merge group contained more
      than one PR", says merge and rebase groups were unaffected, and a later update
      names rebase too. "Existing test coverage primarily exercised single-PR merge
      queue groups".
  - *What it changes:*
    - The aggregate check must depend on the event.
    - The agent's turn ends when auto-merge is armed, not when the PR is "queued".
    - Merge limit 1 during the pilot.
- **Repo settings.**
  - *Evidence:*
    - Merge commits only.
    - `allow_auto_merge: false`.
    - No rulesets, and no classic protection.
    - Release-please uses `SASE_RELEASE_TOKEN`, so release-PR workflows do trigger.
  - *What it changes:* auto-merge is a prerequisite to check. The release PR is not
    blocked by `GITHUB_TOKEN` trigger rules.

The original's other code findings still hold, and every researcher confirmed them:

- `publish.yml` builds the event SHA, not the release SHA, and exports only
  `release_created`.
- `ci.yml` has no `workflow_call` inputs and uses `ci-${{ github.ref }}` with
  `cancel-in-progress: true`.
- `release_watch` looks up runs with `branch="master"` (`_release_watch_api.py:927`,
  `:1019`).
- A contract test forbids new Master Gate triggers.
- sase-github's `_submit_via_pr_merge` treats `gh pr merge` exiting 0 as "merged".

## What survives from the original

- **The diagnosis.** Nothing refuses a red landing. Master Gate reports breakage after
  the push, and green windows decay in about a day and a half.
- **The rejected alternatives.**
  - A host-side lane runs on a local signal that is slow and red 96% of the time. It
    also cannot order athena against apollo.
  - Required PRs alone test a stale base.
  - "Up to date" churns at 40% overlap.
  - Approvals deadlock on self-authored PRs.
- **The sequencing principle.** Release honesty and gate trust come before
  enforcement.
- **The capacity conclusion, as a planning bound.** Flakiness, not runner capacity, is
  the binding constraint. grk's later sample gives about 11 gate-hours a day against 48
  available at K=2. Treat the simulated p95 figures as hypotheses for the pilot to
  measure, not as promises (cdx, grk).
- **The code placement.**
  - The landing record lives in `sase_core`.
  - The GitHub adapter lives in sase-github.
  - Python and the TUI only consume them.
  - The reconciler is deterministic, with no LLM verdicts on merges.
- **The three decision records**, owned by the epics that make them true (grk).

## Requirement changes

The original labels its requirements A–J. Every original requirement appears below with
a status, followed by the new requirements. "Origin" names the researcher who raised a
change; "lead" means it came from my own checks or from resolving a conflict.

### Changes to original requirements A–J

- **A, a release-qualified SHA under 24 h: MODIFIED.**
  - *Revised requirement, in two tiers:*
    1. The newest PyPI release installs in a clean environment, checked daily.
    2. Release lag is at most 7 days at first, then 1–3 days.

    "Under 24 h" becomes a program objective, not the first epic's acceptance bar.
    Epic A's bar is: "given a SHA, publish exactly that SHA's qualified files, or
    refuse".
  - *Why:* installs have been broken since about Sep 20. A 24-hour qualified SHA cannot
    exist while Full CI is 0 of 29.
  - *Origin:* cld, grk.
- **B, two tiers (gate-green and release-green on one SHA): KEPT, with the release tier
  made explicit (see N1).**
  - *Origin:* all.
- **C, service levels instead of "always": MODIFIED.**
  - *Revised requirement:*
    - Replace "zero deterministic failures admitted" with: "every ordinary landing
      carries successful evidence for the declared integration policy on its
      integrated candidate".
    - Keep the numeric targets.
    - Add two more: days with installs broken = 0; and core lag (the gap between what
      HEAD needs and what PyPI has), which is reported but does not gate.
    - Every rate is published with its numerator, denominator and adjudication method.
      Unknown failures are never relabelled to improve a metric.
  - *Why:* no test suite proves the absence of deterministic defects. The new service
    levels track the failures that actually stopped users.
  - *Origin:* cdx, cld.
- **D, one admission path the server enforces, with zero approvals: KEPT.**
  - *Initial scope:* `sase` `master` only (see N10).
  - *Origin:* all.
- **E, publish exactly what was tested: KEPT and SHARPENED.**
  - *Revised requirement:* bind one candidate record and thread it through every
    checkout, including nested `build-core.yml`. The record holds:
    - version, tag and peeled SHA;
    - tree, and the core pin;
    - the policy version;
    - run IDs and attempts;
    - artifact sha256 digests.

    Rules for retries and uploads:
    - Retries resume with the original qualified files.
    - An existing filename is accepted only after its digest matches.
    - A rebuild is a new candidate and must be qualified again.
    - Tags never move.
  - *Why:* "add one `ref`" does not reach nested checkouts. `skip-existing` alone can
    mix two builds.
  - *Origin:* cdx, grk.
- **F, anything that can block a release must also block merges: REPLACED by N1.**
  - *Why:* applied literally, it puts a 30–76 min lane on every landing. That
    contradicts the original's own "no Full CI in the queue".
  - *Origin:* grk, cdx, cld.
- **G, a trustworthy gate before enforcement: KEPT, with the threshold attached to
  enforcement.**
  - *Revised requirement:*
    - The pilot needs B's mechanisms live, not a soak.
    - Enforcement needs a false-red rate under 3% over at least 7 days *and* a declared
      minimum sample of gate builds.
  - *Why:* the pilot is the only experiment that measures `merge_group` builds.
    Statistically, zero failures in about 100 builds only bounds the rate near 3%.
  - *Origin:* grk, cdx.
- **H, "landed" is its own state; beads close only on proof of merge: MODIFIED.**
  - *Revised requirement:*
    - "Landed" is a host-owned record.
    - Beads close as today; closing means the work is done.
    - A core predicate, `delivered(bead) = closed ∧ every landing obligation merged`,
      gates every dependency consumer: `%w(bead=…)`, epic-segment agent waits, blocker
      and ready computation, and land-agent checks.
    - A landing that ends without merging (closed unmerged, or repair budget exhausted)
      makes the host reopen or flag the bead.
    - `keep` and non-code work keep their own semantics.
  - *Why:*
    - Agents and the finalizer close beads during the turn.
    - Moving closure would rewrite at least three templates and the `bead_action`
      contract.
    - A blanket rule would break research-only, canceled and superseded work.
  - *Origin:* cld; cdx (scope and reopen).
- **I, "releasable" includes a published core floor: MODIFIED.**
  - *Revised requirement:*
    - The release train *creates* the core release it needs. It checks the candidate's
      pinned core against published bindings, reports `CORE_LAG`, and requests a
      sase-core release within the daily cut.
    - Retention never deletes a `sase-core-rs` version inside the declared range of
      the last N ≥ 2 published sase releases, and fails closed when it cannot compute
      that set.
  - *Why:* detection without a remedy has recurred: `sase-10d`, `CORE_FLOOR_BLOCKED`,
    and today's unpublished `mobile_pairing_issue`.
  - *Origin:* cld; lead verified.
- **J, admission covers every writer: KEPT, MADE CONCRETE.**
  - *Revised requirement:* inventory every path that writes `sase` `master`, with its
    credential and route:
    - the commit finalizer on both hosts;
    - `revert_agent_transaction`;
    - `post_write_operations` (TUI saves);
    - `sase stitch create`;
    - `ci_watch` release merges;
    - ratchet PRs;
    - sase-github Patch submit;
    - human CLI and web merges.

    Each one honors the landing mode. SDD bookkeeping sidecars keep direct pushes.
  - *Why:* several paths push today, and an empty bypass list refuses all of them.
  - *Origin:* cld, cdx.

### New requirements

- **N1. A versioned check inventory: every check has exactly one blocking home.**
  - *Requirement:* three classes.
    1. **Admission, which blocks merge and release:** the Master Gate contents.
    2. **Release-blocking, which blocks publishing but not merges:** install smokes on
       the built wheel *and* sdist, the core-floor smoke, and the `test (3.13)` and
       `test (3.14)` jobs. The wheel declares support for those Python versions.
    3. **Advisory release checks:** `visual-test`, `perf-floors`, `tutorial-tests` and
       `ace-page-group-isolation`. They run on every candidate, file a `ci` bead with an
       owner, and get a 48-hour build-cop clock.

    A check changes class only by an explicit edit to the inventory, backed by
    measured runtime and false-red data. `visual-test` enters the gate only if it is
    sharded to 20 min or less per job *and* its false-red rate is below the gate
    target.
  - *Why:*
    - A heavy lane that blocks releases but not merges is what stalled PyPI for 49
      days.
    - A broken supported-Python version, on the other hand, ships a broken artifact.
    - Visual is about 30 min, against the gate's 20-minute contract test.
  - *Origin:* lead, resolving cld (gate plus packaging), grk and cdx (full
    qualification), and the original (fold visual in).
- **N2. Linear history: the rebase method, one commit per PR. "Require linear history"
  is on; squash is the fallback; merge commits are rejected.**
  - *Requirement:*
    - The landing record maps the PR head SHA to the landed SHA.
    - The host republishes stitch and agent-page references when a change lands.
    - Repair turns amend and force-push the PR, so it stays one commit.
    - `ci_watch` switches its configured `merge_method`.
    - The sandbox runs release-please against its own history and must show exactly
      one entry per change.
  - *Why:*
    - The [June changelog evidence](#what-changed-since-the-original-was-written) shows
      both duplicates and drops.
    - Today's history is linear, and first-parent tools assume it.
    - The incident text names squash, and in one update rebase too, *for groups of
      more than one PR*. Merge limit 1 (N8) covers that.
    - A permanent changelog defect outweighs an incident GitHub fixed within hours.
  - *Origin:* cld; lead confirmed on sase history. **This reverses the original.**
- **N3. Drift handling: base-red witness, circuit breaker, queue jump, shifted-clock
  canary.**
  - *Requirement:*
    - **Witness:** before any repair turn, check whether the failing node also fails
      on the base. A KNOWN classification needs an independent witness.
    - **Circuit breaker:** after N consecutive ejections with the same signature
      (start at 3), hold admission: the host stops arming new PRs, through a durable
      hold modeled on `hold-pull-fail-open`. Raise one build-cop turn and one
      notification. Agents never wait.
    - **Queue jump:** the base fix jumps the queue, accepting the full rebuild.
    - **Canary:** a nightly gate run on the tip, plus one run under a clock shifted
      about +30 days.
  - *Why:*
    - A red base fails every merge group.
    - Without the witness, about 43 queued landings a day would each spawn repair turns
      for a failure none of them caused.
    - The shifted-clock run would have caught the `f2a7b802f9` healer-fixture time
      bomb.
  - *Origin:* cld.
- **N4. Landing mode is per-project configuration** (for example,
  `landing.mode: push | queue`), owned by the workspace provider.
  - *Requirement:*
    - The default is `push`; sase-github implements `queue`.
    - A `beta` flag may exist only as epic scaffolding inside Epic C, removed before C
      lands.
    - Emergency fallback is a config change, never a flag.
  - *Why:*
    - The flag rule (`sase_flags.md`): "Do not flag anything users are meant to choose
      forever; that is a config field."
    - Most SASE projects will never have a queue.
    - An existing `create_pull_request` method and a merged-PR poller can be extended.
  - *Origin:* cld. **This rejects grk's long-lived beta flag.**
- **N5. An event-aware required aggregate.**
  - *Requirement:* `integration-ready` is a job that is never skipped, and it checks the
    expected jobs for each event.
    - On `pull_request`, cheap eligibility checks pass and expensive jobs are skipped.
    - On `merge_group`, every integration job must be `success`.
    - An empty matrix, a setup failure, a cancellation, a timeout, a skipped mandatory
      job or a zero-test collection never yields success.
    - Negative tests cover each case.
    - There are no path filters on the required workflow.
  - *Why:*
    - The original's aggregate ("fail unless every dependency succeeded") fails on
      `pull_request`, where the expensive jobs are skipped, so no PR could ever enqueue.
    - Running the full gate on both events (cdx's default) doubles load at about the
      20-job cap.
  - *Origin:* cld, cdx, grk.
- **N6. SHA-keyed qualification.**
  - *Requirement:*
    - Qualification runs under `qualify-<sha>` with `cancel-in-progress: false`.
    - It never shares `ci-${{ github.ref }}`.
    - Every source-consuming job emits the SHA it checked out.
  - *Why:* a qualify run on `master` would otherwise cancel Full CI, or be cancelled by
    it.
  - *Origin:* grk, cdx.
- **N7. Durable landing protocol.**
  - *Requirement:*
    - Record intent before any network effect.
    - Track distinct states: prepared, submitted/armed, queued, merged pending proof,
      landed, ejected (with a class), superseded, abandoned.
    - The turn ends at a durable *armed* submission.
    - Idempotent PR lookup by operation ID.
    - Reconcile across hosts without duplicate effects.
    - Retry and repair budgets persist per operation and head.
    - Evidence is selected by workflow, event, head SHA, attempt and conclusion, never
      by "latest green with this name".
    - The merge proof compares the landing's historical base update, never the moving
      tip.
  - *Why:*
    - A PR must pass its checks before it can be queued, so "queued" cannot be proven
      when the turn ends.
    - Two hosts land changes.
    - SHA-only lookups can match the wrong run.
  - *Origin:* cdx; lead (from the docs).
- **N8. Pilot merge limit 1; raise it only after real traffic proves the mapping.**
  - *Requirement:* build concurrency stays 2. Raise the merge limit only after the
    mapping from landed SHA to tested group has been proven on real traffic.
  - *Why:* the incident affected groups of more than one PR, and a limit of 1 keeps the
    proof trivial.
  - *Origin:* grk.
- **N9. Ordinary rollback keeps the fence.**
  - *Requirement:*
    - In an outage, pause admission with a hold, or revert the host mode while keeping
      protected PR admission.
    - An unfenced direct push is a documented, human, audited emergency step that is
      rehearsed on the sandbox.
    - Never relax the force-push or deletion protections.
  - *Why:* the original's "flagged push fallback with the ruleset disabled" silently
    removes the fence.
  - *Origin:* cdx.
- **N10. Scope and ordering across repositories.**
  - *Requirement:*
    - Enforcement covers `sase` `master` only.
    - The pinned core lands and is reachable before the dependent sase PR is armed.
    - The published core floor is proven separately from the source pin.
  - *Why:*
    - Mixed declarations already order linked repos before the primary
      (`commit_revision_pin`).
    - The SDD sidecars must not queue their own bookkeeping.
  - *Origin:* cdx, gem.
- **N11. Human-gated GitHub changes.**
  - *Requirement:*
    - Rulesets, queue enablement, auto-merge, bypass edits and sandbox-repo creation are
      proposed through `/sase_gate` at epic boundaries.
    - Agents never apply them unasked.
  - *Why:* they face outward and are hard to reverse.
  - *Origin:* cld.
- **N12. One owner per goal.**
  - *Requirement:*
    - "Ship 0.18.0" and "restore installability" belong to Track 0.
    - The tag ruleset waits for a release identity that agents don't hold.
    - "Tagged, not on PyPI" is an explicit, honest state.
    - Evaluate release-please `draft` in a spike before relying on it.
  - *Why:*
    - The `sase-1lh` chain is on its third nested child epic.
    - A tag ruleset enforced with the maintainer's credentials, which every agent uses,
      is theatre.
  - *Origin:* grk, cld, cdx; gem (phantom tags).
- **N13. Acceptance, not calendars.**
  - *Requirement:*
    - Drop "this week", "ship 0.18.0" and "7 days, then enforce".
    - A soak is evidence for a human-gated decision, not automatic acceptance.
    - Persistent qualification failure triggers repair, not an automatic switch to
      hatch-vcs.
  - *Why:* the original's own "small Phase 0" contains a release protocol.
  - *Origin:* cdx.

Other researchers' proposed changes that I **rejected**:

- **gem, epic integration branches.** They land intermediate phases ungated, which
  reopens the hole. The cost of waiting on each wave is real (13–30 min per wave). Track
  it as a metric, and treat it as a reason to reopen this decision if it grows.
- **gem, re-testing PRs behind a failed group standalone.** The native queue already
  rebuilds them without the failing PR.
- **gem, demoting local `just check` to a lint under 2 minutes.** That is out of scope
  and governed by `check-full-is-explicit` and `guarded-recipes`.
- **gem, deleting `master` on production as a test (`git push origin :master`).** If the
  ruleset is wrong, that deletes `master`. Verify through a rules API read-back, and test
  destructive behavior only on the sandbox.
- **cld, folding `visual-test` into the gate within Epic B.** It is about 30 min against
  the 20-minute contract. N1 makes promotion a measured option instead.
- **cld, a production fallback rehearsal (disable the ruleset and direct-push).** Move it
  to the sandbox (N9).
- **cdx, allowlist-only retries.** At a 30–40% false-red rate, retrying only known
  signatures barely moves the rate. Use one bounded rerun for any failure set of three
  nodes or fewer, but:
  - never rerun harness or collection errors;
  - retain the first attempt;
  - count recovered novel signatures separately.
- **grk, a pilot with the ruleset not requiring the queue.** GitHub configures a queue
  through the "Require merge queue" rule. A pilot therefore needs the rule *on*, with a
  bypass for traffic still in push mode. The sandbox must confirm how a bypass actor's
  direct push and `gh pr merge --auto` behave.

## Recommendation: four epics, plus Step 0 and Track 0

### Why not one epic

1. **Releases would be held hostage.** Installs are broken now, and exact-SHA publishing
   ships value within days. Bundled with the queue migration, which is the largest and
   riskiest piece, publishing fixes could not close until cutover did.
2. **Soaks and human gates belong at epic boundaries.** SASE agents are single-turn. An
   epic whose later phases are week-long waits and admin approvals sits open for 4–6
   weeks, and its unrelated phases cannot close cleanly.
3. **The failure boundaries differ:**
   - a release-safety failure pauses publishing;
   - a gate failure blocks one merge;
   - a reconciliation doubt withholds delivery but keeps the work;
   - a queue outage pauses admission.

   One epic blurs which promise has actually been kept.
4. **Repos and owners differ:**
   - A: sase, plus sase-core retention.
   - B: sase tests and CI.
   - C: sase-core, sase-github and sase.
   - D: sase workflows, GitHub settings, `bugyi-chops` and chezmoi.

### Why not three (C and D merged, as grk and gem propose)

grk's argument is that one epic gives the cutover an owner. That is a real risk, because
a pilot that never gets cut over leaves the fence rotting. I still split them:

- **Different proof, different venue.** C is entirely provable on a sandbox. D is
  provable only on production `sase/master`. If GitHub behaves differently on the
  sandbox, C's verdict arrives before any production change, and D's plan changes
  without reopening C.
- **Flag hygiene and lifetime.** C must land complete: any scaffolding removed, the
  config defaulting to `push`. Merged with D, scaffolding lives through weeks of pilot
  and soak.
- **C outlives the cutover.** It is a product feature for every SASE project that wants
  a queue, even if `sase/master` were never enforced.
- **The owner risk has a cheaper fix.** Plan D now, with dependency edges on B and C and
  written entry criteria, so its land agent owns the cutover from day one.

If the project strongly prefers three epics, merging C and D is acceptable only if:

- the merged epic stays open through enforcement and the soak;
- A is never merged into it;
- a flagged queue mode is never called "`master` fenced" (cdx).

### Why not more

- **Splitting C by repo leaves pieces nothing can verify:** a core record with no
  adapter, or an adapter with no landing-aware waits.
- **Merging A and B was considered and rejected.** A is urgent. B's value is measured
  over weeks, and B has its own decision record.
- **Step 0 is too small for an epic.** Track 0 already has owners.

### Map and ordering

```text
Step 0  (human, today)     ruleset: block force pushes and deletion on master
Track 0 (existing beads)   restore installability: sase-16p / sase-10d / sase-1lh chain

Epic A  exact-candidate releases + install guards ─────────────┐
Epic B  trustworthy gate ─────── mechanisms live ──┐           │
Epic C  queue-aware landing ──── sandbox suite ok ─┴─► Epic D ◄┘ (D's release train needs A)
                                                       cut sase/master over
```

**Ordering rules:**

- **Land A1 first if at all possible.** It is tiny, and it should precede Track 0's
  publish. If Track 0 publishes before A1, verify after the fact: download from PyPI,
  and compare the version and commit with the tag.
- **Relax the release watcher's rule late.** Replace "fresh Full CI on some SHA" before
  merge only after A2 and A3 are deployed. Otherwise there is a window with neither
  protection (cdx).
- **File ownership, to avoid conflicts:**
  - A owns `publish.yml`, the `ci.yml` `workflow_call` inputs and checkouts, the
    `build-core.yml` ref plumbing, and `tools/release_watch*`.
  - B owns the test infrastructure, Master Gate test steps and the quarantine file.
  - C owns the finalizer, waits, the sase-core landing record and sase-github.
  - D owns the Master Gate triggers and aggregate, the `ci.yml` `pull_request` trigger,
    `ci_watch` and GitHub settings.
  - B's visual study (B6) runs after A2, because both touch `ci.yml`.
- **Verification is never deferred to a later epic.** Every epic retains its own
  acceptance evidence. Local verification is `just check` through `sase tool run`; no
  epic runs `just check-full` unless explicitly told to.

### Step 0: human, today (not an epic)

- **Action:** add a `master` ruleset that blocks force pushes and branch deletion.
  Nothing in sase force-pushes `master` (checked), so today's flow is unaffected.
- **Verify:** read back `gh api repos/sase-org/sase/rules/branches/master` and confirm
  the `deletion` and `non_fast_forward` rules. Do **not** attempt a deletion on
  production.
- **Not yet:** the `v*` tag ruleset, per N12.

### Track 0: restore installability (existing work, not an epic of this program)

- **Owners:** `sase-16p` and `sase-10d`, run by the active `sase-1lh.7.5` chain or a
  focused successor. Box it to this critical path:
  1. Cut a `sase-core-rs` release containing `916d5e3a`.
  2. Ratchet the floor on the release PR.
  3. Get one gate-green release commit.
  4. Publish.
- **If HEAD cannot be held green:** cut the release from the newest gate-green SHA plus
  the version-bump commit, qualified through A's exact-SHA path (cld).
- **Exit:** in a clean environment, `uv tool install sase` reports the new version, and
  `sase core health` passes.

### Epic A: exact-candidate releases and install guards

**Scope:**

- **Repos:** sase, plus sase-core for retention.
- **Size:** medium–large.
- **Start:** now.
- **Decision record:** "PyPI publishes exactly the qualified release SHA."

**Phases:**

- **A1. Exact build.**
  - The `release` job exports the SHA, tag and version from whichever release-please
    retry (`release1/2/3`) actually succeeded.
  - `build` checks out that SHA and asserts tag = SHA = `pyproject` = `__version__`.
  - Build the wheel and sdist once, and record their sha256 digests.
  - Missing outputs when publication was requested is an error.
- **A2. SHA-keyed qualification (N6).**
  - `ci.yml` gains a `ref` input, threaded through every checkout and into
    `build-core.yml`.
  - Qualification runs the N1 release-blocking set on the candidate. The advisory set
    also runs and files beads.
  - `publish` needs every blocking job, including install smokes run against the
    *built* wheel and sdist.
- **A3. Publish and recover by candidate.**
  - Replace `publish_existing` with an explicit tag input.
  - Resume uploads from the retained qualified artifacts. Accept an existing PyPI file
    only on a digest match. A rebuild is a new candidate.
  - Never retag.
  - Confirm after publishing: download from PyPI, compare digests, and run a clean
    install.
- **A4. Honest release states.**
  - `release_watch` models: prepared, qualifying, failed, qualified, publishing/partial,
    and published-and-confirmed.
  - Lookups go by workflow, event and SHA.
  - Relax the pre-merge Full CI rule only after A2 and A3 are deployed.
  - A GitHub release alone never counts as delivered.
- **A5. Core lag and the retention invariant.**
  - The train checks the candidate's pin with `tools/check_sase_core_rs_bindings`,
    reports `CORE_LAG`, and requests a sase-core release.
  - `pypi_retention.py plan` automatically keeps every version inside the declared
    ranges of the last N ≥ 2 published sase releases, and fails closed when it cannot
    compute that set.
  - Optional: ask PyPI to raise the project size limit, as a complement.
- **A6. Install canary.** A daily clean `uv tool install sase` asserts that the
  installed version equals the latest on PyPI, then runs `sase core health`. A failure
  raises a `ci` bead or a notification.
- **A7.** The decision record and docs.

**Independent verification** (needs neither a queue nor a healthy gate):

- **V-A1, moving tip.** In a fixture, pick release commit A, then advance `master` to B
  before the build. Every source-consuming job, including the nested core build with a
  different pin, reports A. The wheel's metadata matches A, and the digests from
  `build` equal the TestPyPI upload.
- **V-A2, retries.** release-please succeeding at each retry position yields the same
  candidate tuple. A no-release run publishes nothing. An empty SHA blocks publication.
- **V-A3, negative qualification.** Fail each blocking class in turn: a gate test,
  `test (3.14)`, the wheel smoke, the sdist smoke and the core floor. Include skipped
  and cancelled jobs. `publish` must not be eligible in any case. When only an advisory
  check fails, publishing proceeds and a bead is filed.
- **V-A4, concurrency.** Qualify SHA A while Full CI runs on `master`. Neither run
  cancels the other, and they exchange no artifacts.
- **V-A5, partial upload.** On TestPyPI, interrupt after one file:
  - resuming with identical files succeeds;
  - an existing filename with a different digest is refused;
  - expired artifacts are reported, not silently rebuilt;
  - two concurrent retries do not conflict.
- **V-A6, core lag.** Against today's HEAD, the train reports `CORE_LAG` naming
  `mobile_pairing_issue`, and dispatches only in dry-run mode.
- **V-A7, retention.** A dry-run plan keeps every version in the last two sase ranges. A
  planted plan that deletes one fails. A PyPI metadata outage fails closed.
- **V-A8, canary.** Run now, it **fails**, because it resolves 0.1.0. That proves it
  detects the outage. It passes after the next release.
- **Exit:** V-A1–A8 pass, and the production workflow has handled one real candidate
  in one of two ways:
  - it published, with PyPI digests equal to the qualified digests and the tag SHA equal
    to the qualified SHA;
  - it refused, naming the failing checks. Record this as a limitation; the program's
    production-release proof then moves to V-D6.

### Epic B: a trustworthy gate

**Scope:**

- **Repo:** sase.
- **Size:** medium.
- **Start:** now.
- **Decision record:** "CI reruns a failed node once and quarantines flakes with an
  expiry", beside `triage-annotates-does-not-change-exit-codes`.

**Phases:**

- **B1. Bounded rerun.**
  - When 3 or fewer nodes fail, rerun them once, serially.
  - Collection or harness errors and a zero-test collection never rerun.
  - Retain first-attempt results.
  - A pass on rerun emits `FLAKY:` and files a `flake` bead, or `+1`s an existing one.
  - Recovered novel signatures are counted separately.
- **B2. Expiring quarantine.**
  - Each entry names a node, a bead, an owner, and an expiry of 14 days or less.
  - Quarantined tests still run in a non-required job.
  - Expired, duplicate or invalid entries fail lint.
  - Seed it with the original's repeat offenders.
- **B3. Parity.**
  - Commit `.python-version` = 3.12.
  - Fail fast when the local core differs from `sase-core-revision.txt`.
  - Apply `if: always()` selectively, to the reporting steps a red `just lint` skips.
- **B4. Drift canaries (N3).** A nightly gate run on the tip, plus one run with the clock
  shifted about +30 days.
- **B5. False-red digest.** Weekly, for each build:
  - raw reds;
  - reds recovered by rerun;
  - residual reds;
  - unknowns;
  - red minutes per day;
  - time bombs caught.

  Each figure is published with its numerator, denominator and adjudication method.
- **B6. Visual promotion study (N1).** Measure `visual-test` sharded wall time and its
  false-red rate. Record a promote or keep decision; don't fold it in by default.

**Out of scope:** queue wiring, gate triggers, and changing Full CI's cadence (all in D).

**Independent verification:**

- **V-B1, planted flake.** A planted flake (it fails on its first attempt via a marker
  file) leaves the job green and emits `FLAKY:`. The first-attempt failure is retained,
  and a flake bead is filed or `+1`ed.
- **V-B2, nothing real is masked:**
  - a planted deterministic failure stays red;
  - more than 3 failures means no rerun;
  - a collection error does not rerun;
  - zero collected tests fails.
- **V-B3, quarantine:**
  - an expired or duplicate entry fails lint;
  - a quarantined failing test still runs and reports in the non-required job.
- **V-B4, time bomb.** Re-introduce the pre-`f2a7b802f9` fixture on a scratch branch.
  The normal gate passes, and the shifted-clock run fails and is flagged as a time bomb.
- **V-B5, parity.** A mismatched core revision fails fast, naming both revisions. A
  contract test pins `.python-version`.
- **V-B6, contracts:**
  - the gate's trigger contract still holds (`push` and `workflow_dispatch`);
  - every job takes 20 minutes or less;
  - no visual job joins the gate unless B6 recorded a promotion.
- **Exit:** the mechanisms are live, and the digest has a published baseline. The
  7-day false-red soak is **D's entry criterion, not B's exit**, because it depends on
  the whole project's traffic (cld, grk).

### Epic C: queue-aware landing as a SASE product feature

**Scope:**

- **Repos:** sase-core, sase-github and sase, plus a public sandbox repo in `sase-org`,
  created by a human (N11).
- **Size:** extra-large, 6–7 phases.
- **Start:** now.
- **Decision record:** "Landed is a host-owned state distinct from turn completion",
  refining `host-owned-completion`.

**Phases:**

- **C1. Core landing record (N7).**
  - The state machine, wire format, API and bindings, plus the `delivered(bead)`
    predicate (H).
  - Move the `sase-core-revision.txt` pin.
- **C2. sase-github adapter.**
  - Idempotent PR create and lookup by operation ID.
  - Arm the PR with the expected head: `gh pr merge --auto --match-head-commit`, or
    GraphQL `enqueuePullRequest` with `expectedHeadOid`.
  - Poll for merged and ejected outcomes.
  - Fix `_submit_via_pr_merge`: exit 0 means *armed*, not merged.
- **C3. Landing mode (N4).** Under `queue`, the finalizer:
  - records intent;
  - pushes `sase/land/<op>`;
  - opens a one-commit PR, with the title taken from the subject and the body from the
    message body *without* the subject;
  - arms it, then ends the turn.

  The other writers (J) honor the mode. Core-then-pin ordering is preserved (N10).
- **C4. Deterministic reconciler**, run as an axe chop with no LLM.
  - **Proof chain:** source head → PR → successful `merge_group` run and attempt →
    resulting base update → completion effects.
  - **On merge:** map the landed SHA and republish stitch and agent pages.
  - **Waits:** make every dependency consumer landing-aware.
  - **Abandoned landings:** reopen or flag the bead.
  - **Hosts:** two hosts converge without duplicate effects.
- **C5. Drift-safe ejection (N3).** Classify each ejection as a conflict, a flake, a
  deterministic failure, or a red base (the last only with a witness).
  - **Conflicts** go to the existing conflict-repair turn.
  - **Flakes** re-enqueue once.
  - **Deterministic failures** get at most 2 repair turns, with budgets that persist
    across restarts.
  - **A red base** starts no repair.
  - **Circuit breaker:** hold admission, raise one build-cop turn, and send one
    notification.
  - Credential, rate-limit and ambiguous-API failures never become "repair the code".
- **C6. Sandbox and harness.**
  - A ruleset requiring the queue: rebase method, linear history, K=2, merge limit 1.
  - An event-aware aggregate (N5).
  - A toy gate with tests that pass, fail, flake, or explode on a timer.
  - A scripted end-to-end harness.

**Independent verification** (all on the sandbox; nothing touches `sase/master`):

- **V-C1, happy path.**
  - The turn ends with the landing record `armed`.
  - The bead closes, but a dependent `%w(bead=…)` and the next epic segment resolve
    only after the merge.
  - Stitch and agent pages show the landed SHA.
  - release-please over the sandbox's history shows **one** entry per change.
- **V-C2, pending checks.** Required checks are pending when `gh pr merge` exits 0. The
  record says armed, never merged, and no dependent is released.
- **V-C3, crashes and restarts.**
  - Inject a crash before and after each of: the branch push, PR creation, arming, the
    merge, proof persistence, and the completion effects.
  - On restart there is exactly one PR, no lost change, and no duplicate effect.
  - Run reconcilers on two hosts against the same operation. Kill the originating host
    and recycle its workspace; the surviving host completes the landing.
- **V-C4, combined failure.** A and B each pass alone but fail together.
  - B is ejected and classified deterministic, and A lands.
  - B's repair force-push keeps the PR at one commit.
  - Proof from the stale head never qualifies the new head.
- **V-C5, drift.** Detonate the time bomb.
  - The ejection is classified red-base, and no repair turn starts.
  - After N ejections, the breaker holds admission and raises one gate.
  - The base fix jumps the queue and lands, and admission resumes.
- **V-C6, unmerged outcomes.** Change the head after arming, close the PR unmerged,
  supersede it, and inject transient API errors. In none of these cases is a dependent
  released. Abandoned landings reopen or flag the bead.
- **V-C7, cross-repo declaration.** One declaration spans core, the main repo and a
  bookkeeping sidecar.
  - The main repo waits until the core commit is reachable.
  - The pin is correct.
  - `keep` survives.
  - The sidecar creates no queue cycle.
- **V-C8, push mode.** Push mode is unchanged: the existing finalizer suite passes, and
  a sandbox project in push mode lands exactly as today.
- **V-C9, settle the unknowns.** Determine on the sandbox:
  - whether the new base SHA equals the `merge_group` head under rebase with merge
    limit 1;
  - whether "require merge queue" alone refuses a direct push;
  - what a bypass actor's direct push does, and what their `gh pr merge --auto` does;
  - whether a skipped job satisfies a required check on a PR;
  - whether `jump` needs elevated permissions;
  - how workflows trigger for PRs opened with the maintainer's credentials.
- **V-C10, repo checks.** Run `just check` (via `sase tool run`) in sase, sase-github and
  sase-core, plus binding round-trips, with the pin moved.
- **Exit:** a repeatable scripted run of V-C1–C9 passes. Any beta scaffolding has been
  removed, and the config default is `push`.

### Epic D: cut `sase/master` over

**Scope:**

- **Repos:** sase (gate triggers, `ci.yml` triggers, `release_watch`), `bugyi-chops`
  (`ci_watch`), chezmoi (`sase_athena.yml`), and GitHub settings via human gates.
- **Size:** medium, with two human-gated phases and a monitored soak.
- **Entry:** B's mechanisms are live, and C has passed its exit. Plan D now, with those
  dependency edges.

**Phases:**

- **D1. Workflows.**
  - Add the `merge_group` trigger and the N5 aggregate to `master-gate.yml`, updating
    the trigger contract test.
  - Drop `ci.yml`'s `pull_request` trigger for ordinary PRs. Keep the floor smoke on
    the release PR as an early warning.
  - Keep the push-triggered gate as a separately named audit.
- **D2. Enable the queue (human gate).**
  - Repo settings: allow auto-merge and rebase merges, and delete branches on merge.
  - Ruleset: require the queue (rebase, K=2, merge limit 1, `ALLGREEN`, 60-minute
    timeout), require linear history, and require `integration-ready` from the
    expected producer.
  - Put the maintainer in the bypass list for the pilot, as validated in V-C9.
- **D3. Pilot.**
  - Traffic: an allowlist (docs, `toobig`, ratchets) using `landing.mode=queue`
    overrides, from both hosts.
  - Measure: ejection classes, landing p50 and p95, runner wait at K=2 against the
    shared 20-job cap, and the `merge_group` false-red rate.
  - Prove the mapping for every pilot landing.
- **D4. Writers and watchers.**
  - Build the writer and credential matrix (J).
  - `ci_watch` arms the release PR with rebase, and looks up heavy checks by SHA.
  - `release_watch` looks up by SHA.
  - Move Full CI to nightly plus candidates **only** if measured runner waits warrant
    it. Then update `ci_watch`'s 6-hour freshness rule and its 2-hour stale dispatch
    together.
- **D5. Enforce (human gate).**
  - Entry: a false-red rate under 3% over at least 7 days and a declared sample, with
    unknowns retained.
  - Empty the bypass list.
  - Set the sase project's `landing.mode` to `queue`.
  - Raise the merge limit only after the mapping is proven on real traffic.
- **D6. Simplify and record.**
  - Retire the push audit's heavy work once V-D3 holds; keep lightweight provenance
    checks.
  - Run the nightly release train: the core step (A5) → arm the release PR → qualify →
    publish → confirm.
  - Give the heavy lane an owner: a build-cop turn, and a high-severity notification
    after 48 h red.
  - Write the decision record "`master` lands only through the merge queue". It
    supersedes the queue clause of `ci-two-speed-split` *on the merits*: a queue
    produces a per-SHA signal and fits capacity. Do not claim the reopen trigger fired;
    the gate's p50 is about 12.5 min against a 17-minute arrival gap (grk). The record
    also notes the refinement to `host-owned-completion`.
  - Write the incident runbook.

**Independent verification** (production):

- **V-D1, effective rules.** Export the effective rules and confirm that they match:
  - target `master`;
  - PRs required, with 0 reviews;
  - the queue required, with the D2 settings;
  - one required check from the expected producer;
  - linear history;
  - force pushes and deletion denied;
  - an empty bypass list after D5.

  Export before and after.
- **V-D2, safe canaries.**
  - A direct push of a harmless docs-only commit with agent credentials is refused.
  - A canary PR with a failing test does not move `master`.
  - Of two PRs that fail only in combination, the second is ejected.
- **V-D3, every commit was tested.** A script over `gh api` maps every post-cutover
  `master` commit to a successful `merge_group` run of `integration-ready` for that
  head SHA. Zero exceptions.
- **V-D4, service levels over the window.**
  - Landing p50 under 30 min and p95 under 60 min.
  - Runner-wait p90 under 5 min.
  - A false-red rate under 3%.
  - Zero dependents released before their landing merged, per the landing records.
  - Zero human interventions per day for routine landings.
- **V-D5, restarts.** A host restart during real pending work on both hosts reconciles
  with no duplicates.
- **V-D6, release train.** At least one release goes through the nightly train with no
  human action:
  - PyPI digests equal the qualified digests;
  - the install canary stays green;
  - days since the last release is 7 or fewer at first, then 3 or fewer.
- **V-D7, outage.** Rehearse a queue outage: pausing admission keeps the fence and loses
  no obligations. The emergency path is the one rehearsed on the sandbox (N9), and any
  emergency push is recorded and verified after the event.
- **Exit:** V-D1–D7 pass. The epic stays open if enforcement or the soak cannot be
  demonstrated.

## Where the reports split, and how I resolved it

- **Number of epics**
  - *Positions:* cdx 4; cld 4, plus Step 0 and Track 0; grk 3; gem 3.
  - *Resolution:* **4**, plus Step 0 and Track 0.
- **Merge method**
  - *Positions:* the original, cdx, grk and gem chose merge commits; cld chose rebase.
  - *Resolution:* **rebase**, with squash as the fallback. sase's own changelog
    settles it.
- **`visual-test` in the gate**
  - *Positions:* the original and cld fold it in; cdx measures first; grk says no; gem
    runs it in shadow mode.
  - *Resolution:* **not by default.** It is promoted only by the measured B6 study.
- **The release-blocking set**
  - *Positions:* the original, cdx and grk block on the full matrix; cld blocks on the
    gate plus packaging.
  - *Resolution:* **the gate, packaging, and 3.13/3.14 tests block.** Visual, perf and
    tutorial checks are advisory (N1).
- **Landing mode**
  - *Positions:* the original and grk use a flag; cld uses config.
  - *Resolution:* **per-project config.**
- **Bead closure**
  - *Positions:* the original, grk and gem close on merge; cdx defers the close; cld
    keeps closure and makes waits landing-aware.
  - *Resolution:* **cld's model**, plus reopening on abandonment (cdx).
- **Where the turn ends**
  - *Positions:* the original and grk end it at a proven "queued"; cdx ends it at a
    durable submission.
  - *Resolution:* **at armed**. GitHub's documentation requires PR checks to pass first.
- **0.18.0**
  - *Positions:* the original and gem keep it in scope; cdx, cld and grk take it out.
  - *Resolution:* **out**; Track 0 owns it.
- **Pilot gating**
  - *Positions:* the original requires under 3% first; cld requires 10% or less for 7
    days; grk pilots at the current rate.
  - *Resolution:* **the pilot needs B's mechanisms and C's exit.** Enforcement needs
    under 3% with a declared sample.
- **Full CI cadence**
  - *Positions:* the original moves it to nightly in Phase 1; cld does so in B; grk and
    cdx defer it.
  - *Resolution:* **in D, only if runner waits warrant it**, with `ci_watch` updated in
    step.
- **Drift handling and installability**
  - *Positions:* only cld raised them.
  - *Resolution:* **adopted**, as N3 and A, and verified independently.

## Risks and what would change this recommendation

- **The sandbox shows that a bypass actor cannot push to a queue-required branch.** Then
  D2 and D5 collapse into one hard cutover, and the pilot moves entirely to the sandbox.
  The epic split is otherwise unchanged.
- **Rebase in the queue misbehaves.** For example, the landed SHA is not the group head,
  or footers are lost. Then use squash, with the PR body excluding the subject. Do not
  return to merge commits unless release-please moves to `changelog-type: github` *and*
  the first-parent tools are fixed.
- **False reds stay above about 10% after B.** Delay D. A, B and C keep their value
  without it. Do not invent a host-side queue.
- **The automated core step proves unreliable.** Reasons could include sase-core's own
  red `master`, or the daily cut. Then adopt the stronger rule cld considered: the gate
  refuses landings whose core pin is unpublished.
- **Per-wave latency hurts epic throughput.** If queue waits stretch epic wall-clock
  time badly, revisit batching phases (gem's integration branches) as a new decision,
  with a fence on the integration branch.

## Method, confidence and limits

**Read through audited channels:**

- the four reports and the original, via `sase artifact read`;
- the memories `sase_flags.md`, `sase_beads.md`, `decisions:ci-two-speed-split` and
  `decisions:host-owned-completion`, via `sase memory read`;
- the beads `sase-10d`, `sase-16p`, `sase-1m4`, `sase-1lh` and `sase-1lh.7`, via
  `sase bead read`;
- `sase-core` and `bugyi-chops`, via `sase repo open`.

**Measured or checked directly (high confidence):**

- PyPI metadata, and resolution of `sase` and `sase==0.17.1` with `uv pip compile`;
- repo settings, rulesets and #299;
- Master Gate (newest 100 runs) and Full CI (newest 30 runs, with job durations for 4
  failed runs);
- changelog duplicates and drops, cross-checked against merge-commit parents, release
  tags and the bootstrap SHA;
- parent counts since Oct 10;
- sase-core tags containing `916d5e3a`;
- the line references cited above.

**From researchers, spot-checked but not re-derived:**

- cld's release-please source walk and simulation (the June history independently
  confirms it);
- the original's queue simulation and capacity figures;
- cld's four classes of failure from bead notes.

**From GitHub's documentation, via a fetch helper:** the queueing preconditions, the
cost of jumping the queue, merge limits, and the incident text. The `enqueuePullRequest`
reference page did not load, so the permissions `jump` needs remain open (V-C9).

**Not done:**

- no rulesets, workflows, memory, beads or plans were changed;
- no sandbox was created, and no CI was run;
- no beads were filed, because installability is already tracked by `sase-16p` and
  `sase-10d`.

## Sources

**SASE, at `2cae86a1aa` and the live APIs:**

- Workflows: `.github/workflows/{publish,master-gate,ci}.yml`
- Contract tests: `tests/test_github_actions_ci_master_gate.py`
- Config and history: `release-please-config.json`, `CHANGELOG.md`, `pyproject.toml`
- Code:
  - `src/sase/workflows/commit/{workflow,bead_hooks}.py`
  - `src/sase/bead/work_prompt.py`
  - `src/sase/default_config.yml`
  - `src/sase/{post_write_operations,ace/revert_agent_transaction,tool/triage_inputs}.py`
  - `tools/_release_watch_api.py`
- Live data: `gh run list`, `gh api …/jobs`, `gh pr view 299`, `gh api repos/sase-org/sase`
- PyPI JSON for `sase` and `sase-core-rs`

**sase-core `916d5e3a`:** `.github/scripts/pypi_retention.py` and tags.
**bugyi-chops `5828753`:** `src/bugyi_chops/ci_watch.py`.

**Research:**

- [The original](../merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md)
- The four reassessments linked in the header

**GitHub:**

- [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue)
- [Incident `zsg1lk7w13cf`](https://www.githubstatus.com/incidents/zsg1lk7w13cf)
- [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)
- [`gh pr merge`](https://cli.github.com/manual/gh_pr_merge)
