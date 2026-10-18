# Google's release process vs. sase's planned merge-queue release program

> **Research query:** I've been thinking about making some big changes to sase's release
> process with the goal of making them much more reliable (see
> `merge_queue_fenced_master_and_exact_sha_releases.md` and
> `merge_queue_fence_reassessment_and_epic_split.md`). I used to work at Google where our
> release process was pretty good. How does our planned release process compare to
> Google's release process? Is there any inspiration that sase can take from it? End with
> a ranked list of changes I should consider making to the planned change.

**Researcher:** cld · 2026-10-18 · sase `master` at `7b9436bede`

## Bottom line

1. **The plan shares Google's philosophy. It differs in mechanics, and the differences
   show where sase is under-invested.** The shared ideas:
   - one trunk and small changes;
   - a release train that leaves on time;
   - build once and ship the exact bits that were tested;
   - signed provenance;
   - flake hygiene;
   - an owner for a red build.

   The mechanics differ in one structural way:
   - **Google cannot serialize landings.** At "more than one a second" it lets changes
     land after a fast presubmit, then puts its heavy machinery after the merge:
     continuous post-submit testing, automated culprit finding, automatic rollback, and
     release candidates cut at *green* head.
   - **sase can serialize, so the plan puts nearly all its effort before the merge.**
     That is the merge queue.
2. **The serialized queue is a correct divergence; keep it.** *Software Engineering at
   Google* names serialized submits as what smaller projects do to avoid "mid-air
   collisions", which "happen most days at our scale". At about 42 landings a day, sase
   can afford what Google gave up.
3. **The release-blocking lane gets none of Google's post-merge machinery.** This is the
   gap that matters. The plan's N1 inventory deliberately keeps some checks out of the
   queue: `test (3.13)`, `test (3.14)`, the install smokes, and the core floor.
   - **For those checks, sase is exactly where Google is:** they are post-submit only.
   - **The plan backs them only lightly:** a `ci` bead, one build-cop repair turn, and a
     48-hour escalation. Epic D may also cut their cadence to nightly.
   - **Google's SRE book says the opposite**, word for word: "the continuous build test
     targets correspond to the same test targets that gate the project release," and
     "create releases at the revision number (version) of the last continuous test build
     that successfully completed all tests."
4. **New evidence: today the release lane is flaky-green, not red.** On Oct 18, Full CI
   ran six times on the *unchanged* SHA `ae9f044bb3` and passed three. Each failure was 1
   or 2 tests out of about 56,277, and the failing tests differed from run to run.
   - **Epic A, as written, would refuse about half of all good candidates.** It
     qualifies the release on one all-or-nothing run.
   - **The rerun planned for the gate wouldn't reach it.** Epic B's bounded rerun is
     scoped to the Master Gate, not to the `ci.yml` jobs that qualification uses.
5. **Three Google practices are missing outright:**
   - **A rollback or hotfix path for a bad release.** Google's preferred fix is the
     rollback.
   - **Provenance that names the commit that was built.** Today's PyPI attestations name
     the *workflow run's* commit. After Epic A, that will often not be the release
     commit.
   - **Running the artifact users install.** The fleet runs editable source installs.
     An agent filed "latest PyPI sase is uninstallable" (`sase-16p`) on Sep 22. Because
     no machine's daily use depends on that path, it stayed in the ready queue for about
     four weeks, while bare `pip install sase` resolved to 0.1.0.

**Recommendation:** none of this changes the architecture. Keep:

- the native queue;
- zero approvals;
- rebase landing;
- exact-SHA publishing;
- the four-epic split.

Add Google's post-merge discipline to the part of the pipeline that stays post-merge. The
[ranked list](#ranked-list-of-changes-to-consider) at the end has eight changes. The top
three:

1. Make qualification flake-aware.
2. Give the release-blocking lane continuous testing, culprit finding and revert-first.
3. Never claim a version before its exact candidate is release-green.

## Scope and caveats

- **"Google's release process" is not one process.** Teams choose their own cadence and
  tooling (the SRE book: "individual teams can decide how often and when to release new
  versions of their products"). I describe the common, publicly documented core:
  - **Piper**, one trunk;
  - **Critique** code review, with presubmits;
  - **TAP**, presubmit and post-submit testing;
  - **Blaze** hermetic builds;
  - **Rapid** release automation;
  - **MPM** packages and labels;
  - **canarying** and staged rollouts;
  - **Binary Authorization for Borg** (BAB);
  - **Build Cops**.

  Your Google team (Ads) may have run variants of these. Where your experience
  contradicts a public source, trust your experience and re-rank accordingly.
- **Sources** are the SRE book (ch. 8), the SRE Workbook (ch. 16), *Software Engineering
  at Google* (chs. 23–24), Google's BAB whitepaper, the Chrome developer blog, and
  DORA. Full links are in [Sources](#sources).
  - I could not retrieve the body of the 2016 "Flaky Tests at Google" post. Its
    statistics are quoted from secondary sources and flagged.
  - Chromium's CQ documentation returned HTTP 503, so I make no claims about CQ
    internals.
- **"The planned process"** means the reassessment's design (Step 0, Track 0, Epics
  A–D), plus the parts of the original design it kept. I found no beads filed yet for
  Epics A–D, so these changes can be folded into planning before work starts.

## The two processes in brief

### Google (public core)

1. **Land.** A change gets code review and runs a *fast* presubmit. Presubmit runs
   "only fast, reliable ones," usually "just those for the project where the change is
   happening." A change that passes "has a very high likelihood (95%+) of passing the
   rest of the tests, and we optimistically allow it to be integrated." Submits are
   **not** serialized.
2. **Post-submit.** "After a change has been submitted, we use TAP to asynchronously run
   all potentially affected tests, including larger and slower tests."
   - **Batching:** TAP batches changes, because it "can no longer run every test on
     every change."
   - **Culprit finding:** it "automatically splits a failing batch up into individual
     changes" and "reruns the tests against each change in isolation."
   - **Rollback:** it "automatically roll[s] back changes when it has high confidence
     that they are the culprit."
   - **Build Cop:** each team has one, who "drop[s] whatever they are doing and fix[es]
     the build." Rollback is "the preferred solution"; fixing forward is "a riskier
     proposition."
3. **Cut a release candidate.** "At Google, most teams cut these at green, as opposed to
   true, head." Rapid takes "the requested integration revision number (often obtained
   automatically from our continuous test system)" and creates a release branch from
   it. The branch is never merged back. Fixes are "submitted to the mainline and then
   cherry picked into the branch."
4. **Qualify the candidate.** "We re-run the unit tests using the release branch and
   create an audit trail showing that all the tests passed." Larger tests run "against
   the entire candidate." Builds are hermetic: the same revision built on different
   machines should give "identical results."
5. **Package and authorize.** MPM packages are "versioned with a unique hash, and
   signed." Labels mark a package's stage (`dev`, `canary`, `production`) and move from
   package to package. BAB checks signed provenance *at deploy time*. The emergency
   bypass requires a justification and notifies the security team and the service's
   owners.
6. **Roll out.** The candidate is canaried: "a partial and time-limited deployment of a
   change in a service and its evaluation." It is then rolled out in stages. Rollback
   means moving a label back to the previous package.
7. **Cadence.** Some teams build hourly and pick from the pool. Others use "Push on
   Green" and "deploy every build that passes all tests."
   - **Search:** went from weekly releases to "every other day".
   - **Chrome:** moved from four-week to two-week milestones in September 2026, because
     a "smaller scope minimizes disruption and simplifies post-release debugging."

### sase (planned)

- **Step 0.** A ruleset that blocks force pushes and deletion on `master`.
- **Track 0.** Restore installability and ship 0.18.0, using existing beads.
- **Epic A, exact-candidate releases:**
  - export the release SHA, tag and version, and build that SHA once;
  - record digests;
  - qualify the N1 release-blocking set on that SHA;
  - publish only the qualified files, never retag, and confirm after publishing;
  - check core lag and enforce a retention invariant;
  - run a daily install canary.
- **Epic B, a trustworthy gate:**
  - one bounded rerun when 3 or fewer nodes fail;
  - an expiring quarantine;
  - parity fixes;
  - a drift canary with the clock shifted about +30 days;
  - a false-red digest;
  - a study on promoting the visual tests.
- **Epic C, queue-aware landing as a product feature:**
  - a landing record in sase-core and an adapter in sase-github;
  - a per-project `landing.mode`;
  - a deterministic reconciler and a `delivered(bead)` predicate;
  - ejection classification and a circuit breaker;
  - a sandbox repo.
- **Epic D, cutover:**
  - `merge_group` triggers and an aggregate check;
  - a ruleset that requires the queue, with rebase, K=2 and merge limit 1;
  - a pilot, then enforcement at under 3% false reds;
  - a nightly train (core step → arm release PR → qualify → publish → confirm);
  - a build cop for the heavy lane, with a 48-hour notification.

## Side-by-side

- **Trunk**
  - *Google:* One trunk. Release branches are cut at a revision and never merged back.
  - *sase plan:* One `master`, with no release branches.
  - *Assessment:* Same model.
- **Landing gate**
  - *Google:* Review, plus a fast presubmit on the change. Not serialized.
  - *sase plan:* A native merge queue tests each change on the integrated tree. Zero
    approvals.
  - *Assessment:* sase is stronger on integration and deliberately weaker on review.
- **Post-submit**
  - *Google:* TAP runs every affected test and does automated culprit finding and
    automatic rollback. The Build Cop drops everything.
  - *sase plan:* Full CI runs every 2 h (D4 may move it to nightly). A failure gets a
    bead and one repair turn; escalation comes after 48 h.
  - *Assessment:* **The main gap** ([G1](#g1-the-release-blocking-lane-is-post-submit-only-and-under-equipped)).
- **Flakes**
  - *Google:* "A system for flake classification", "multiple attempts", and flaky tests
    temporarily removed from presubmit.
  - *sase plan:* B1 reruns up to 3 failed nodes once; B2 keeps an expiring quarantine.
    Both are scoped to the gate.
  - *Assessment:* Close, but it doesn't reach qualification
    ([G2](#g2-qualification-is-one-all-or-nothing-run)).
- **Choosing the release candidate**
  - *Google:* "Cut at green, as opposed to true, head", at the last fully green
    continuous build.
  - *sase plan:* The release PR is armed at true head each night and qualified after it
    merges.
  - *Assessment:* **Gap** ([G3](#g3-releases-are-cut-at-true-head-and-the-version-is-claimed-before-qualification)).
- **Qualifying the candidate**
  - *Google:* Re-run the tests on the release branch and keep an audit trail.
  - *sase plan:* Run the release-blocking set on the exact SHA and record the digests.
  - *Assessment:* Same idea.
- **Artifact identity**
  - *Google:* Hashed, signed MPM packages; labels move between them.
  - *sase plan:* Build once, record sha256 digests, never retag.
  - *Assessment:* Same idea.
- **Provenance and deploy policy**
  - *Google:* BAB checks signed provenance at deploy time, and the audited emergency
    bypass requires a justification.
  - *sase plan:* PyPI Trusted Publishing attestations already exist. The tag ruleset is
    deferred. N9 makes the emergency push an audited step.
  - *Assessment:* Close, with one defect ([G5](#g5-provenance-exists-but-will-name-the-wrong-commit)).
- **Rollout**
  - *Google:* Canary, then a staged rollout. Rollback means moving the label back.
  - *sase plan:* Publish to PyPI, confirm, and run a daily install canary.
  - *Assessment:* A different medium. **No rollback path**
    ([G4](#g4-there-is-no-rollback-or-hotfix-path)).
- **Who runs the artifact**
  - *Google:* System tests run against the packaged artifact, and the candidate is
    canaried on real traffic.
  - *sase plan:* The fleet runs editable source installs.
  - *Assessment:* **Gap** ([G6](#g6-nobody-runs-the-artifact-users-install)).
- **Cadence**
  - *Google:* Search went from weekly to every other day. Chrome moved to 2-week
    milestones. Some teams push on green.
  - *sase plan:* A nightly train, at most 7 days between releases at first, then 1–3.
  - *Assessment:* Aligned.
- **Metrics**
  - *Google:* DORA's five metrics, and TAP's mean time to clean up (MTTCU).
  - *sase plan:* False reds, landing latency, and days since the last release.
  - *Assessment:* Missing the instability side ([G7](#g7-metrics-measure-throughput-not-instability)).

## Where the plan already matches Google (keep these)

- **Build once, ship the exact bits, never retag.** This is MPM's model: a package is
  identified by hash, and only labels move. Epic A's candidate record also covers
  Rapid's audit trail and its "report of all changes since the last release."
- **Qualify the candidate itself, not a nearby commit.** Epic A's exact-SHA
  qualification is Rapid's "re-run the unit tests using the release branch" and *SWE at
  Google*'s "release candidate testing."
- **Keep the gate fast and push the rest after the merge.** N1 keeps `visual-test`
  (about 30 min) out of the gate until a measured study promotes it. That is Google's
  "only fast, reliable ones" rule for presubmit.
- **Expiring quarantine tied to a bead.** B2 is nearly the Takeout team's practice word
  for word: failing tests get a bug tag and are suppressed, and the tag is cleaned up
  automatically once the bug is fixed. Commenting tests out was rejected because it
  "would make the failures too easy to forget about."
- **The shifted-clock drift canary.** *SWE at Google* warns that hermetic setups are
  "still prone to some sources of nondeterminism, like system time." N3's +30-day clock
  run targets that class of failure.
- **No stop-the-line on red.** *SWE at Google* calls "'Nobody can commit if our latest
  CI results aren't green'" "probably misguided." The plan's circuit breaker is the
  right narrow version: it holds admission only after repeated ejections with the same
  signature, and the fix may jump the queue.
- **A release train that leaves on time.** "If you're late for the release train, it
  will leave without you," and "faster is safer." The nightly train, with a 1–3 day
  target, follows the same logic as Chrome's move to two-week milestones.
- **Automation by default, humans on exceptions.** The plan wants a nightly release with
  no human action (V-D6). Rapid's equivalent: "Releases are truly automatic, and only
  require engineer involvement if and when problems arise."
- **Audited break-glass.** N9 makes an unfenced push a documented, rehearsed, human
  step. That is BAB's emergency procedure, where the bypass is logged and notified.

## Where sase is right to differ from Google

- **A serialized merge queue instead of presubmit-on-a-snapshot.** Google accepts daily
  mid-air collisions because it must. *SWE at Google* names serializing submits as the
  small-project way to make "no difference between what is about to enter and what just
  did." The earlier queue simulation (K=2, p50 about 13 min) shows sase can afford it.
  The result is better than Google's own landing gate: every `master` SHA is a tested
  integration.
- **Zero approvals.** BAB requires "review and approval from at least one engineer
  other than the author." That doesn't carry over:
  - agents author nearly every change under the maintainer's account;
  - GitHub won't let you approve your own PR;
  - review at Google also does knowledge-sharing and readability work that has no analog
    here.

  The queue, the tests and host-owned completion are the substitute. Keep zero
  approvals, but be clear-eyed: sase has *no* second-party check on intent. That is a
  product risk, not a release-process one.
- **No percentage rollouts.** PyPI is pull-based, so there is no traffic to split, and
  users choose when to upgrade. Rollout safety has to come from three places instead:
  - qualifying before publishing (planned);
  - running the artifact before users do ([G6](#g6-nobody-runs-the-artifact-users-install));
  - a fast way to withdraw a bad release ([G4](#g4-there-is-no-rollback-or-hotfix-path)).
- **No release branch per release.** Rapid branches every release. Sase's version lives
  in source, and release-please commits the bump to `master`. A branch per release
  would need merge-backs, which is why the original rejected a `stable` branch. Reserve
  branches for hotfixes ([G4](#g4-there-is-no-rollback-or-hotfix-path)).
- **No affected-test selection or batching.** TAP needs both at Google's scale. A 12-min
  sharded gate at 42 landings a day does not.

## Where Google would push back

### G1. The release-blocking lane is post-submit only, and under-equipped

**What the plan does.** N1 keeps a class of checks that block release but not merge:

- the install smokes on the wheel and the sdist;
- the core-floor smoke;
- `test (3.13)` and `test (3.14)`. The Full CI legs run 45–96 min, measured on Oct 18.

These run in Full CI every 2 hours, and D4 may cut that to "nightly plus candidates." A
red result files a `ci` bead and launches one build-cop repair turn, and a
high-severity notification fires after 48 hours.

**Why Google would object.**

- **This is the only lane the queue doesn't protect, and it is what stalled PyPI.**
  Full CI was green 1 time in 271 runs from Aug 27, and 0 in 29 as of Oct 17. The
  stale `visual-test` golden stayed red for weeks.
- **At Google, this lane gets the most machinery:**
  - TAP runs it continuously;
  - TAP splits failures down to individual changes;
  - TAP rolls back high-confidence culprits automatically;
  - a Build Cop "drop[s] whatever they are doing."
- **"Velocity is a team sport" names the minimum set:** teams "set up CI testing,
  automatic rollbacks, and culprit finding to identify issues quickly."
- **The SRE book's first release-engineering recommendation contradicts D4's nightly
  option.** Continuous test targets should equal the targets that gate the release.
- **Cadence sets how many commits a culprit hunt must search.** Takeout moved its
  end-to-end tests to a post-submit run "every two hours," which "effectively cut the
  'culprit set' by 12 times." At about 42 landings a day:
  - every 2 h, a failure implicates about 3–4 commits;
  - nightly, about 42.
- **A repair turn is fix-forward.** *SWE at Google* calls that "a riskier proposition"
  than rollback.

**What to borrow.** Run the release-blocking class on every Full CI tick (keep 2 h, or
per N landings). Add three things around it:

1. **A deterministic culprit finder.** On a red, it reruns only the failing node IDs at
   each SHA since the last green, a few minutes per SHA. A2's new `ref` input on
   `ci.yml` makes that possible.
2. **Flake-aware confirmation.** The culprit fails k of k attempts, and its parent
   passes k of k.
3. **Revert first.** A high-confidence culprit gets an automatic revert PR through the
   normal landing path, and its bead reopens for a reland.
   - A fix-forward turn is the fallback, not the default.
   - Chromium does the same in public: its LUCI Bisection service is "the culprit
     finding service for compile and test failures for Chrome Browser."

Replace the 48-hour clock with a time-to-release-green service level, for example p90
under 6 h. Keep 48 h only as the human escalation.

### G2. Qualification is one all-or-nothing run

**New evidence (Oct 18).**

Full CI ran six times on the unchanged SHA `ae9f044bb3`, between 03:13Z and 11:13Z: three
greens and three reds. Each red job failed 1 or 2 tests out of about 56,277:

- **Run 39104985574**, three tests:
  - `test_J_switches_to_the_pulse_and_enter_returns_to_the_inbox`
  - `test_files_ctrl_j_scrolls_page_anchor_to_top`
  - `test_identical_contents_in_two_checkout_paths`
- **Run 39120426524**, one test: `test_files_ctrl_j_scrolls_page_anchor_to_top` again.
- **Run 39122381498**, two tests:
  - `test_app_export_body_tolerates_signal_task_prepare_error`
  - `test_muse_usage_probe_missed_mint_is_a_timeout_not_absence`

Every one of those tests passed on the same SHA in the green runs. By Google's
definition (both passing and failing results on the same code), they are flaky.

**What the plan does.**

- **Epic A** qualifies a release by running the release-blocking set on the candidate.
  `publish` needs every blocking job.
- **Epic B's rerun covers only "Master Gate test steps."** B owns those; A owns the
  `ci.yml` plumbing. No phase says the qualification lane gets the rerun.
- **The CI workflows have no reruns today.** `ci.yml` and `master-gate.yml` contain no
  test rerun at all.

**Why it matters.** With about 56k tests per job across three Python versions, even a
tiny per-test flake rate makes a red run likely. On this sample, Epic A would refuse
about half of all good candidates. That makes it a coin flip, and the nightly train
inherits the coin. Google's widely quoted 2016 figures point the same way:

- about 1.5% of test runs were flaky;
- about 16% of tests showed some flakiness;
- most pass→fail transitions involved a flaky test.

These are secondary-source figures (see [caveats](#scope-and-caveats)).

**What to borrow.** "A system for flake classification" and "multiple attempts":

- Apply B1's bounded in-job rerun to every release-blocking job in `ci.yml`, under the
  same rules:
  - rerun only when 3 or fewer nodes fail;
  - never rerun collection or harness errors;
  - keep the first-attempt results;
  - emit `FLAKY:`.
- A node that fails and then passes on rerun is FLAKY and does not block publication.
  A node that fails twice blocks it.
- Feed the rerun data to B2, so quarantine entries are *proposed* from measured flake
  rates instead of being written by hand.

### G3. Releases are cut at true head, and the version is claimed before qualification

**What the plan does.**

1. The nightly train arms the release-please PR at whatever head is current.
2. The PR lands through the queue; the queue runs only the gate on it.
3. release-please tags it on a later run.
4. Epic A builds and qualifies the tagged SHA.
5. If qualification fails, the version is already claimed: `master` carries the bump and
   the CHANGELOG entry, and the tag and GitHub release may exist. N12 handles this by
   making "Tagged, not on PyPI" an explicit, honest state.

**Why Google would object.**

- **The SRE book's second recommendation:** release "at the revision number (version) of
  the last continuous test build that successfully completed all tests." The reason it
  gives: this decreases "the chance that subsequent changes made to the mainline will
  cause failures during the build performed at release time."
- ***SWE at Google*:** most teams cut "at green, as opposed to true, head."
- **At Google, a failed candidate is simply not promoted.** No version name escapes.
- **The plan's design guarantees that a failed qualification burns a version number.**

**What to borrow, in one of two ways:**

- **(a) Qualify the release PR inside its merge group.** This is the smaller change.
  - Only the release PR's `merge_group` run executes the release-blocking set, plus a
    build of the wheel and sdist whose digests are retained.
  - Under rebase with merge limit 1, the landed SHA is the tested group head. V-C9
    already plans to verify that.
  - A failed qualification ejects the release PR. `master`, the tag and the version
    stay untouched, and the train retries the next night.
  - Publishing then just uploads the retained, digest-checked files for the tag.
  - Costs:
    - the queue is occupied for about 45–96 min once a day; run the train at a quiet
      hour, or shard 3.13 and 3.14 the way the gate shards 3.12;
    - the status-check timeout must cover qualification;
    - the aggregate check must recognize the release PR.
- **(b) Google's model outright.** Make the version a build-time stamp taken from the
  tag (for example `hatch-vcs`; sase already builds with `hatchling`). Tag the newest SHA
  that is release-green on post-submit runs. Then:
  - nothing in the queue is special;
  - a red tip never blocks a release;
  - the provenance problem in G5 disappears, because the run executes at the tag.

  The cost is retiring release-please's bump commit. That means reworking:
  - `release_watch` and `ci_watch`;
  - the CHANGELOG flow;
  - `__version__`;
  - the `sync-release-metadata` ratchet, which must land as a normal change before
    tagging.

**My recommendation.** Do (a) in Epic D, and prove it in Epic C's sandbox. Keep (b)
designed as a spike rather than a buried fallback. The reassessment's N13 says
persistent qualification failure triggers repair, not a switch to hatch-vcs. Google's
practice is evidence that tagging at green is the *normal* design, not the emergency one.

### G4. There is no rollback or hotfix path

**What the plan does.** The plan covers exact publication, partial-upload recovery and a
queue-outage runbook. It never says what happens when a *published* release is bad.

**Why Google would object.**

- **Rollback is the first tool:** "The most effective tool the Build Cop has is the
  rollback," and "Smaller, self-contained release artifacts make it cheaper and easier
  to roll back."
- **Release-branch fixes go through cherry-picks.** Rapid manages "release branches and
  cherry picks," and approves or rejects each one. Its tests re-run on the branch,
  because "the release branch may contain a version of the code that doesn't exist
  anywhere on the mainline."

**What to borrow, translated to PyPI:**

- **Yank first.** PEP 592: installers "MUST ignore yanked releases, if the selection
  constraints can be satisfied with a non-yanked version." Exact `==` pins still work.
  - Add a yank-then-fix-forward runbook.
  - Have `release_watch` propose a yank through `/sase_gate` when post-publish
    confirmation, the install canary or a severe regression fails. It must stay
    human-gated, because it faces outward.
- **A hotfix lane.** When a release is bad and `master` has moved on with unqualified
  work:
  1. branch `release/X.Y` from the tag;
  2. cherry-pick the fix from `master`;
  3. qualify that branch SHA through Epic A;
  4. publish `X.Y.(Z+1)`;
  5. never merge back.

  This needs release-please's maintenance-branch support, or option G3(b). Spike it in
  Epic A.
- **Fail loud, not old.** The installability outage silently resolved `pip install sase`
  to 0.1.0. A5's retention invariant is the real fix. The broader lesson is to prefer
  failures that are loud: an install canary that checks the version, and possibly
  yanking ancient releases that are no longer supported.

### G5. Provenance exists, but will name the wrong commit

**What exists today (verified).**

- **sase already publishes with PyPI Trusted Publishing.** `publish.yml` runs in
  environment `pypi` with `id-token: write`, using `pypa/gh-action-pypi-publish`.
- **The action has attached attestations by default since v1.11.0.** Both 0.17.1 files
  carry a PEP 740 publish attestation whose publisher is GitHub `sase-org/sase` /
  `publish.yml` / `pypi`.
- **The certificate names the triggering commit.** The Sigstore certificate's source
  repository digest is `d64219f0…`, which is the `v0.17.1` tag commit. The trigger was
  `schedule` on `refs/heads/master`.
- **That match was luck.** The digest comes from the run's OIDC token, so it names the
  commit that *triggered the workflow run*, not the one checked out. For 0.17.1 the tip
  happened to be the release commit.

**Why it will break.** Epic A makes `build` check out the release SHA. The scheduled or
dispatched run around it still executes at a later tip: about 5 landings per 3-hour
publish tick. So the PyPI attestation would certify a commit that was never built.

BAB's whole point is that the provenance check happens at deploy time and is truthful.
Its provenance describes "the sources and dependencies that went into the build, the
cryptographic hashes of any binaries."

**What to borrow:**

- **Run the uploading job at the release SHA.** Use a tag-push or a tag-ref dispatch, so
  that `github.sha` is the candidate. Then restrict the `pypi` environment's deployment
  refs to `v*` tags.
- **Verify after publishing.** Add a step to A3's confirmation: fetch PyPI's provenance
  for each file, and check that
  - the source digest equals the candidate SHA;
  - the workflow and environment equal the trusted publisher.
- **Optionally add SLSA build provenance** in `build` with
  `actions/attest-build-provenance`.
- **Tag-triggered publishing is safe enough before N12's release identity exists,
  because `publish` still requires qualification of that exact SHA.** Agents can push
  `v*` tags with the maintainer's credentials, but a tag alone never publishes.
- **Strengthen N9's emergency push with BAB's rule:** a written justification, a
  notification, and a reference to the exact snapshot.

### G6. Nobody runs the artifact users install

**Evidence.**

- **The fleet runs source, not releases.** On apollo, `uv tool` installs sase as
  *editable* from the primary checkout, with `sase-core-rs` overridden. Most sase
  plugins are installed editable the same way.
- **The broken release was caught, then sat.** A land agent filed `sase-16p`, "Latest
  PyPI sase (0.17.1) is uninstallable", on Sep 22. It is still a READY small bug with
  +3 corroborations, 26 days later.
- **The cost was silent.** Meanwhile bare `uv tool install sase` resolves to 0.1.0.
  Because no machine depends on the PyPI path day to day, a user-facing outage was
  triaged like a backlog bug.

**Google's equivalent.** Build artifacts "are then available for system testing and
canary deployments." System tests run "on packaged build artifacts." The thing
canaried is the thing shipped.

**What to borrow:**

- **Keep A6's daily clean-install canary,** and make it exercise a real no-LLM workflow,
  not only `sase core health`.
- **Run the same canary on each candidate's built wheel before publishing**, with
  dependencies resolved from PyPI.
- **Optionally put one machine on a release channel.** For example, the mac could run
  `uv tool install sase` from PyPI, upgraded by the train after each publish. Its health
  then feeds the G4 yank decision. Whether that is worth giving up tip-of-tree on that
  machine is your call.

### G7. Metrics measure throughput, not instability

**What the plan measures.** The digest tracks false reds, red minutes, landing latency,
runner waits and days since the last release.

**DORA's current model (Google Cloud's research program) has five metrics:**

- change lead time;
- deployment frequency;
- failed deployment recovery time;
- change fail rate;
- deployment rework rate.

**What to add.** Translate these to PyPI releases:

- **Lead time:** from landed to on PyPI, p50 and p90 per change.
- **Change fail rate:** releases yanked or hotfixed within 7 days.
- **Recovery time:** from a bad release to a good release or a yank.
- **Rework rate:** unplanned patch releases.

Add two Google-specific measures:

- **Time to release-green**, TAP's MTTCU analog. This is G1's service level.
- **Gate escape rate:** the share of release-blocking failures whose culprit passed the
  gate. Google justifies its lean presubmit with the "95%+" predictive figure. Sase
  should use the escape rate to decide N1 promotions, alongside runtime and false-red
  data.

### G8. Builds are not hermetic

**The gap.** Rapid relies on hermetic, reproducible builds. sase's `build` job is not
pinned that way:

- it uses floating `hatchling>=1.27`;
- it uses `astral-sh/setup-uv@v4` without pinning a uv version;
- it sets no `SOURCE_DATE_EPOCH`.

That is why Epic A must say "a rebuild is a new candidate."

**What to borrow.**

- Pin the build backend and uv, and stamp `SOURCE_DATE_EPOCH` from the commit.
- Then a rebuild can be *verified* against the qualified digests, which allows
  independent checks.
- This is low priority; Epic A's retained artifacts already cover the main risk.

## New evidence gathered for this report

- **Full CI on an unchanged SHA (Oct 18).**
  - *What I found:* `ae9f044bb3` went green, green, red, green, red, red. Each red job
    failed 1–2 of about 56,277 tests, and the failing tests differed between runs. The
    test jobs ran 45–96 min.
  - *Source:* `gh run list` and `gh run view --log-failed` for runs 39092843619,
    39097854068, 39104985574, 39112297316, 39120426524 and 39122381498.
- **Master Gate.**
  - *What I found:* the newest three SHAs are green (`9526d3bae3`, `ae9f044bb3`,
    `7b9436bede`). 11 of the newest 100 runs are green.
  - *Source:* `gh run list -w master-gate.yml`.
- **Releases.**
  - *What I found:* PyPI is still at 0.17.1, and #299 "chore(master): release 0.18.0"
    is still OPEN.
  - *Source:* PyPI JSON, `gh pr view 299`.
- **Test reruns.**
  - *What I found:* there are none in `ci.yml` or `master-gate.yml`.
  - *Source:* grep of the workflows.
- **PyPI provenance.**
  - *What I found:*
    - 0.17.1's wheel and sdist both have publish attestations, with publisher
      GitHub / `sase-org/sase` / `publish.yml` / `pypi`;
    - the certificate's source digest is `d64219f0…` (= `v0.17.1`), with event
      `schedule` and ref `refs/heads/master`.
  - *Source:* `https://pypi.org/integrity/sase/0.17.1/<file>/provenance`, with the
    statement and certificate decoded.
- **Fleet install mode.**
  - *What I found:* sase and most of its plugins are installed as editable from the
    primary checkout, with `sase-core-rs` overridden.
  - *Source:* the `uv tool` receipt on apollo.
- **The installability bead.**
  - *What I found:* `sase-16p` ("Latest PyPI sase (0.17.1) is uninstallable") was
    created 2026-09-22 and is still READY, small, +3.
  - *Source:* `sase bead read sase-16p`.
- **Full CI cadence.**
  - *What I found:* cron `17 */2 * * *`.
  - *Source:* `full.yml`.
- **Beads for Epics A–D.**
  - *What I found:* none yet.
  - *Source:* `sase bead search` for "merge queue", "exact-candidate" and "release
    qualification".

## Method, confidence and limits

- **Read through audited channels:**
  - both input reports, via `sase artifact read`;
  - the research sidecar, opened with `sase repo open research`;
  - the beads `sase-16p` and `sase-10d`, via `sase bead read`.
- **Measured directly (high confidence):**
  - every item in [New evidence](#new-evidence-gathered-for-this-report);
  - the `publish.yml`, `full.yml` and `master-gate.yml` contents at `7b9436bede`.
- **Google practice (high confidence on the quoted text, medium on how general it
  is):**
  - quotes come from the SRE book, the SRE Workbook, *SWE at Google*, the BAB
    whitepaper and the Chrome blog, via fetch helpers;
  - practices vary by team, and I did not use internal-only names or claims.
- **Not verified:**
  - the body of the 2016 flaky-tests post; its statistics are secondary-source;
  - Chromium CQ internals (the docs returned 503);
  - the details of LUCI Bisection's auto-revert safeguards;
  - whether option G3(a) works under GitHub's merge queue as described. That belongs
    in Epic C's sandbox (V-C9).
- **Not done:**
  - no workflows, rulesets, memory files or beads were changed;
  - no CI was triggered.

## Sources

**Google:**

- *Site Reliability Engineering*, ch. 8,
  [Release Engineering](https://sre.google/sre-book/release-engineering/): Rapid,
  branching and cherry-picks, hermetic builds, MPM labels, Push on Green, the two
  testing recommendations.
- *The Site Reliability Workbook*, ch. 16,
  [Canarying Releases](https://sre.google/workbook/canarying-releases/): the definition
  of canarying, reproducible builds, rollback.
- *Software Engineering at Google*,
  [ch. 23, Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html):
  presubmit and post-submit, mid-air collisions and serialized submits, culprit finding,
  automatic rollback, Build Cop, flakes, release candidate testing, "cut at green," the
  Takeout case study, the "CI is alerting" sidebar.
- *Software Engineering at Google*,
  [ch. 24, Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html):
  release trains, "faster is safer," flag-guarding, Search's cadence.
- [Binary Authorization for Borg](https://cloud.google.com/docs/security/binary-authorization-for-borg):
  signed provenance, deploy-time enforcement, emergency procedures, SLSA lineage.
- [Chrome's two-week release cycle](https://developer.chrome.com/blog/chrome-two-week-release)
  (2026-03-03).
- [Chromium tree sheriffs](https://www.chromium.org/developers/tree-sheriffs/) and the
  [LUCI Bisection README](https://chromium.googlesource.com/infra/luci/luci-go/+/HEAD/bisection/).
- [Flaky Tests at Google and How We Mitigate Them](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html)
  (the body could not be retrieved; the figures are from secondary summaries such as
  [this one](https://talent500.com/blog/google-flaky-test-mitigation-strategies/)).
- [Taming Google-Scale Continuous Testing](https://research.google/pubs/taming-google-scale-continuous-testing/)
  (ICSE 2017, abstract only).
- [DORA's software delivery metrics](https://dora.dev/guides/dora-metrics-four-keys/).

**Python packaging:**

- [PyPI attestations](https://docs.pypi.org/attestations/)
- [Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [gh-action-pypi-publish v1.11.0](https://github.com/pypa/gh-action-pypi-publish/releases/tag/v1.11.0):
  attestations on by default.
- [PEP 592](https://peps.python.org/pep-0592/): yanking.
- [SLSA levels](https://slsa.dev/spec/v1.0/levels)

**SASE:**

- `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
- `research:202610/merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md`
- `.github/workflows/{publish,full,master-gate,ci}.yml` and `pyproject.toml` at
  `7b9436bede`
- Live `gh` and PyPI data, as listed in [New evidence](#new-evidence-gathered-for-this-report).

## Ranked list of changes to consider

The ranking weighs how directly each change protects the plan's own goal, a qualified
release every 1–3 days, against its cost. All eight fit inside the existing four-epic
split. None reopens the queue, zero approvals, rebase landing or exact-SHA publishing.

1. **Make release qualification flake-aware** (Epic A, with B1's mechanism).
   - **What:** extend B1's bounded in-job rerun to every release-blocking `ci.yml` job:
     - rerun when 3 or fewer nodes fail;
     - never rerun harness or collection errors;
     - keep the first attempt;
     - emit `FLAKY:`.

     A node that fails twice blocks publication; a node that passes on rerun does not.
   - **Why first:** without it, Epic A refuses about half of good candidates on today's
     evidence (3 of 6 runs red on an unchanged SHA, 1–2 of about 56k tests each). It is
     also cheap.
   - **Google basis:** flake classification and "multiple attempts."
2. **Give the release-blocking lane Google's post-submit discipline** (a new phase in
   Epic B, after A2's `ref` input).
   - **What:**
     - keep the release-blocking class on the 2-hour Full CI tick, and drop D4's
       nightly-only option for it (advisory checks may go nightly);
     - add a deterministic, flake-aware culprit finder that reruns the failing nodes per
       SHA;
     - auto-revert a high-confidence culprit through the normal landing path and reopen
       its bead for a reland;
     - set a time-to-release-green service level (for example p90 under 6 h), with 48 h
       as the human escalation only.
   - **Google basis:** TAP's culprit finding and automatic rollback, rollback as "the
     preferred solution," the SRE book's "continuous build test targets correspond to
     the same test targets that gate the project release," and Takeout's 2-hour
     post-submit.
3. **Never claim a version before its exact candidate is release-green** (Epics C and
   D).
   - **What:** qualify the release PR inside its `merge_group` run with the
     release-blocking set, retain the digests, and publish those files after the merge.
     A failed qualification ejects the PR, with no tag, bump or CHANGELOG entry left on
     `master`.
   - **Also:** spike Google's own model, a build-time version plus tagging the newest
     release-green SHA. Treat it as a real design option, not a buried fallback.
   - **Google basis:** "cut at green, as opposed to true, head" and "create releases at
     the revision ... of the last continuous test build that successfully completed all
     tests."
4. **Make PyPI provenance name the qualified SHA, and verify it** (Epic A, A1 and A3).
   - **What:**
     - run the uploading job at the release SHA (tag-push or tag-ref dispatch);
     - restrict the `pypi` environment to `v*` tags;
     - after publishing, check that the attestation's source digest equals the
       candidate SHA and that the publisher identity is the expected one;
     - add BAB's justification and notification requirements to N9's emergency path.
   - **Why:** today's attestations name the triggering run's commit, and Epic A's
     exact-SHA build will usually differ from it. This costs almost nothing.
5. **Add a rollback and hotfix path for bad releases** (Epic A, plus a runbook).
   - **What:**
     - a yank-then-fix-forward runbook, with `release_watch` proposing a yank through
       `/sase_gate` when confirmation or the canary fails;
     - a `release/X.Y` hotfix branch from the tag, cherry-picked from `master`,
       qualified through Epic A and never merged back (a spike, given release-please);
     - a preference for failures that are loud over silently installing an old
       version.
   - **Google basis:** "the most effective tool ... is the rollback," and Rapid's
     cherry-pick branches.
6. **Exercise the shipped artifact, not just the source** (A6).
   - **What:** run a real no-LLM workflow in the install canary, on each candidate's
     built wheel before publishing and on PyPI daily. Optionally keep one machine on the
     PyPI release channel.
   - **Why:** the fleet's editable installs left a four-week user-facing outage
     (`sase-16p`, filed Sep 22) triaged like a backlog bug.
7. **Add DORA's instability metrics and a gate escape rate to the digest** (B5 and D).
   - **What:** lead time from landing to PyPI, change fail rate, recovery time, rework
     rate, time to release-green, and the share of release-blocking failures that
     escaped the gate. Use the escape rate in N1 promotion decisions.
8. **Pin the build toolchain for reproducible wheels** (Epic A, low priority).
   - **What:** pin `hatchling` and uv, and set `SOURCE_DATE_EPOCH`. A rebuild can then
     be verified against the qualified digests instead of being declared a new
     candidate.

**Not recommended**, despite being Google practice:

- required human approvals (they deadlock on self-authored PRs);
- percentage rollouts or a pre-release channel (PyPI has no traffic to split, and few
  external users);
- affected-test selection or batched post-submit (unnecessary at about 42 landings a
  day);
- a release branch for every release (only hotfixes need one);
- stop-the-line on any red (*SWE at Google* calls it "probably misguided").
