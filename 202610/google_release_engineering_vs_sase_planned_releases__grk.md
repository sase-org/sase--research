# Google release engineering compared with SASE's planned merge-queue and exact-SHA process

> **Research query:** How does SASE's planned release process (merge-queue-fenced `master`, exact-SHA PyPI publishes, four-epic delivery) compare with Google's release process? What should SASE borrow? Ranked list of changes to the plan.

**Independent report** · researcher `grk` · 2026-10-18.

**Inputs:** the two named context reports, live SASE workflows and decision records, and Google's public release-engineering literature. Peer reports from this swarm were not consulted.

## Bottom line

SASE's planned process already copies the *right half* of Google's model: a snapshot identified by revision, two-speed tests, a release train, a check inventory, and "publish the bytes that passed." That is Rapid plus TAP's test-size split, translated onto GitHub and PyPI. It is closer to Google than a typical GitHub Python project, and closer than SASE's current path (unprotected `master`, post-push Master Gate, `publish.yml` building whatever `master` is when the job runs).

The remaining reliability gap is not the merge queue. The queue is a sound GitHub adaptation of "do not land an untested combination." Google itself often *lands first* and finds culprits after, because Piper commits are atomic and TAP is huge. For a 43-landing-a-day GitHub repo with overlapping pushes, testing the stacked result *before* it becomes `master` is the correct local translation.

The remaining gap is Rapid's *promotion, selection, hermeticity, hotfix, and rollback* machinery, which Google treats as the actual release process:

1. **Select last-known-green, then promote those bytes.** Exact-SHA is the *mechanism*. Last-known-green is the *policy*. The plan still reads as "pick a SHA, then qualify it." Rapid cuts a snapshot from the last continuous-build green revision and never rebuilds that snapshot as it walks toward production.
2. **Hermetic, pinned toolchains.** Today's Master Gate builds sase-core with `dtolnay/rust-toolchain@stable`. A rebuild of last month's tag can pick this month's compiler. Google treats that as a release bug.
3. **Cherry-pick onto a frozen snapshot.** When production is wrong, Google does not wait for HEAD. It branches at the released revision, cherry-picks, re-tests *that* branch, and pushes those artifacts.
4. **Canary before 100% of users.** PyPI has no traffic split. The Google-shaped substitute is TestPyPI plus a real-machine install of the *same wheel bytes*, then public PyPI, with yank as rollback.
5. **Revert the culprit; do not run another "make CI green" epic.** TAP's response to postsubmit red is culprit-finding and auto-rollback. SASE's eight repair epics since September are the opposite habit.

Approvals, a monorepo, and Borg canaries should stay out of the plan. Mechanical admission (the queue) is the justified substitute for Critique, because agents push under the maintainer account and GitHub will not let that account approve its own PRs.

**In one line:** keep the queue and the exact-SHA candidate record; change the plan so a release is a *promoted, hermetic snapshot of last-known-green*, with a cherry-pick hotfix path, a pre-PyPI canary of the same bytes, an installability freeze, and revert-the-culprit as the postsubmit response.

## What "Google's release process" means here

Google is not one process. Three public families exist:

| Family | Who uses it | Cadence | What a "release" is |
| --- | --- | --- | --- |
| **Piper + Critique + TAP + Rapid + MPM** | Most internal services (Search, Ads, …) | Hours to every other day | A hermetic snapshot at a changelist, labeled `dev` / `canary` / `production` |
| **Chrome / Android trains** | Client products with store constraints | Weeks | A branch cut, bake, staged store rollout |
| **Workspace / GKE channels** | Hosted products | Rapid vs scheduled tracks | A feature flag or channel, not a Git tag |

This report uses the first family. That is the process a Google SWE on an Ads or infrastructure team actually ran: send a changelist, get it reviewed, pass presubmit, land on mainline, let TAP certify a green head, and let Rapid build *that* revision into a package that is canaried and then labeled production. Push-on-green ([Kle14], [Betser15]) is the Ads/SRE variant of the same stack.

It is the wrong comparison to import Chrome's four-week train, Android's long-lived branches, or Play Store percentage rollouts as if they were "how Google released." Those exist because *clients cannot yank a binary from a phone*. SASE is a PyPI CLI. Rapid-plus-TAP is the matching analog; Play-style staged rollout is only useful as a metaphor for TestPyPI / canary-host / yank.

## The planned SASE process, restated

The two context reports, taken together, recommend this architecture (the reassessment's six requirement changes and four-epic split are treated as the current plan):

**Admission (landings)**

- GitHub native merge queue on `sase` `master`, PRs as host-created tickets, zero approvals.
- Rebase, one commit per PR, linear history (this reversed the original's merge-commit choice).
- Gate-green = Master Gate contents on the *integrated* candidate.
- Gate made trustworthy (bounded rerun, expiring quarantine, false-red target under 3%) before enforcement.
- Drift handling: base-red witness, circuit breaker, queue jump, shifted-clock canary.
- Landing mode is per-project config (`push` \| `queue`), not a feature flag.
- Beads still close as today; *dependency waits* become landing-aware.
- Merge limit 1 in the pilot; build concurrency 2.
- Step 0: block force-pushes and deletion now. Epic C proves the product on a sandbox. Epic D cuts `sase/master` over.

**Release (PyPI)**

- Two tiers of green: gate-green (admission) and release-green (packaging + 3.13/3.14 + install smokes) on the *same SHA*.
- Visual, perf, and tutorial checks are advisory with an owner and a 48-hour clock.
- Bind a candidate record (version, tag, peeled SHA, tree, core pin, policy, run IDs, sha256 digests). Retries resume those files. A rebuild is a new candidate. Tags never move.
- The train *creates* the sase-core release it needs. Retention must not delete a `sase-core-rs` version inside the declared range of the last N ≥ 2 published sase releases.
- Installability is requirement zero and lives on Track 0 (`sase-16p` / `sase-10d` / `sase-1lh`), outside this program.
- Cadence target: 7 days at first, then 1–3 days. "Under 24 h" is an objective, not the first epic's bar.

**What is true of the tree today, and why the plan exists**

- `master` has no branch protection (`…/protection` 404, rulesets `[]`).
- `builtin@commit` rebases and pushes without testing the combined tree. Master Gate reports breakage after the fact.
- `.github/workflows/publish.yml` `build` job uses `actions/checkout@v4` with no `ref:`, so a scheduled or `publish_existing` run builds whatever `master` is at that moment.
- `skip-existing: true` on the PyPI publish step can mix files from two builds.
- PyPI `sase` is 0.17.1 (2026-08-29). Bare `pip install sase` recently resolved to 0.1.0 because the 0.17.1 core window was deleted from PyPI.
- Master Gate and Full CI have been mostly red; eight "green then ship 0.18.0" epics decayed in about a day and a half.

Those facts are the right problem statement. Google would recognize every one of them as a release-engineering defect, not a "CI is flaky" complaint.

## Side-by-side

| Concern | Google (TAP + Rapid + MPM) | SASE plan | Fit |
| --- | --- | --- | --- |
| What may land on mainline | Presubmit: fast, reliable, *project-local* tests. Mid-air collisions are accepted; TAP finds them after. Human review via Critique is required. | Merge queue tests the stacked result *before* land. Zero approvals. Whole-repo fast suite, not affected-target selection. | Queue is *stricter* than TAP on combinations, *weaker* than Critique on review. Correct tradeoff for agent landings. |
| What "green" means | Two heads: *true head* and *green head* (last CB-verified). Releases cut from green. 100% green is explicitly rejected ("CI is alerting"). | Gate-green vs release-green on one SHA. Original slogan "no deterministic break can reach `master`" is stricter than Google. Reassessment already softened this. | Keep two tiers. Drop the slogan. |
| How a release is chosen | Last successful continuous-build revision, or an explicit Rapid integration CL. | A SHA is chosen, then qualified. Tag-on-green was a fallback in the original, not the default. | **Change this.** Selection policy should be last-known-green. |
| How a release is built | Hermetic Blaze at that revision, with the *then-current* version of the compiler as checked in. Same inputs → identical outputs. | Checkout the SHA (A1). Toolchains are still floating (`rust-toolchain@stable`, `setup-uv`, `uv python install 3.12`). | **Change this.** Pin tools into the candidate. |
| How a release is promoted | One MPM package, unique hash, labels (`dev`, `canary`, `production`) move onto the same bytes. No rebuild between stages. | Plan records sha256 and forbids silent rebuilds. It does not yet *promote* those bytes through TestPyPI and a host canary before public PyPI. | **Change this.** Labels, not rebuilds. |
| Hotfix | Branch at the released revision. Cherry-pick. Re-test the branch (which exists nowhere on mainline). Never merge the branch back. | Wait for `master`, or qualify "newest gate-green plus version bump." No Rapid-style release branch. | **Add cherry-pick onto the last candidate.** |
| Rollback | Move the `production` label back, or Borg-restart the previous MPM. First response, not a forward-fix. | Yank is available but unpracticed. Previous sase versions were *uninstallable* after core retention. N/I starts to fix retention. | Keep retention. Add a rehearsed yank. |
| Canary | Small production population, compared with control, gated on SLIs, then exponential rollout. | Install smokes in GHA against the built wheel. No production-like host, no TestPyPI promotion, no post-publish prober. | **Add a same-bytes host canary.** |
| Flakes | Do not run unreliable tests on presubmit. Quarantine with expiry. Flake-aware culprit finding. Auto-rollback at ~98% culprit accuracy. | Bounded rerun, expiring quarantine, false-red SLO, then enforce. No automatic revert. | Quarantine matches. Add revert. |
| Slow / large tests | Postsubmit TAP, then a final comprehensive suite at Rapid promotion. Teams configure which tests are presubmit. | N1 inventory: admission / release-blocking / advisory. Visual stays off the gate by default. Full CI cadence moves later. | Good match. Do not fold visual into the queue. |
| Dependencies | One-Version / live-at-head inside the monorepo. Library owners update *callers*. Deleted versions do not exist. | Two repos, a PyPI version window, and a retention script that already deleted the 0.17.1 floor. Train will *cut* the core release it needs. | Retention invariant is the Google lesson. Live-at-head is not portable to PyPI. |
| Config and flags | Binary release and feature launch are separate. Flags roll independently. Config is versioned and often packaged next to the binary. | SASE already has flag beads and `default_config.yml`. The plan does not say "a PyPI cut must not wait on a flag" or "a flag flip is its own canary." | State it. |
| Identity | Every binary prints build date, revision, and Rapid build id. | `sase version` inventories installed packages and can probe git in editable checkouts. A PyPI wheel does not obviously carry the candidate SHA. | **Bake the candidate into the wheel.** |
| Provenance | MPM packages are hashed and signed. Rapid archives the CL list with the artifacts. | Candidate record is the internal form. Trusted publishing to PyPI (OIDC) already exists. No public attestation binding wheel digest to SHA. | Cheap SLSA L1/L2 add-on. |
| Who is on the hook | Build cop drops everything for a red project. Release engineering is a job; Rapid is self-service so SWEs do not file tickets to cut. | D6 mentions a build-cop turn and a 48-hour advisory clock. The train still looks like `ci_watch` plus a human. | Make the train self-service; page only on failure. |
| Failure of HEAD | Expected. Cut from green head. Roll back the culprit. Error budget can freeze *launches*. | Original treated green HEAD as the release precondition. Reassessment decoupled them, then still needs HEAD-ish green for a train cut. | Decouple fully: a red tip must not block a qualified snapshot. |

## Where the plan already matches Google

These should stay. They are the parts of the plan a Google release engineer would sign.

**1. Two-speed tests, with only fast reliable tests on the landing path.**
SWE book ch. 23: presubmit is "only fast, reliable ones"; you accept some coverage loss and catch the rest on postsubmit plus rollback. SASE's Master Gate vs Full CI (`decisions:ci-two-speed-split`) and the reassessment's N1 inventory (admission / release-blocking / advisory) are that split. Folding `visual-test` (~30 min) into a 20-minute gate would violate it.

**2. Publish the artifact that was tested, not "whatever HEAD is now."**
Rapid re-runs tests on the *release branch* and archives an audit trail that those tests passed in the context of what is actually shipping. Today's `publish.yml` checkout-without-`ref` is the canonical Google anti-pattern ("unique snowflake builds"). Epic A1–A3 (export SHA from the winning release-please retry, checkout it, record digests, resume those files) is the fix.

**3. A check that can block a *release* need not block every *merge*.**
TAP groups tests into *projects* so a team can release when unrelated tests are red. The original's Adjustment F ("anything that can block a release must also block merges") was Google-wrong at SASE's scale: it would put a 30–76 minute lane on every landing. N1's replacement is the TAP project split. Keep it.

**4. Trust the gate before you enforce it.**
Google will not run flakes on presubmit because they tax every engineer. A 30–40% false-red Master Gate is a random-rejection engine; the queue simulation in the original report shows p95 roughly doubling at that rate. Bounded rerun plus expiring quarantine is TAP hygiene, not bureaucracy.

**5. A train with "no binary is perfect" and a deadline.**
SWE book ch. 24, Search: every-other-day train, "if you miss it the next one is hours away," KPIs with thresholds so imperfect features still ship. SASE's 1–3 day train and Track 0's "ship from newest gate-green plus version bump if HEAD cannot be held" are that idea. Keep "0.18.0" out of the fence program.

**6. Fences beat promises.**
Google enforces review, presubmit, and who may cut a Rapid project in configuration, not in a wiki. Unprotected `master` plus "please do not push red" is the thing Rapid was invented to abolish. Step 0 (block force-push and deletion) is the smallest Google-shaped fence and should happen regardless of the queue.

**7. Feature flags separate launch from binary.**
SWE book ch. 24 and the SRE workbook: flag-guard new work so a binary can ship with the feature off, and a bad feature can be disabled without a new package. SASE already has flags and flag beads. The release train should assume unfinished work is flagged off.

**8. Mechanical, self-service cutting.**
Rapid's philosophy is self-service: teams decide when to release; engineers are involved only when something fails. Host-created PRs with zero approvals, plus a nightly train, are that philosophy on GitHub. Adding required human review would deadlock agents and would not make the *package* safer.

**9. Linear history as the changelog's input.**
Google's Piper history is linear by construction. The June release-please duplicates and drops under merge commits are the Git equivalent of giving Rapid a nonlinear CL list. Rebase (with squash as fallback) is the Google-shaped choice on GitHub, incident footnote notwithstanding. Merge limit 1 (N8) covers the 2026-04-23 GitHub queue incident's group-size exposure.

## Where the plan diverges, and which divergences are justified

### Justified: no Critique, no monorepo, no Borg canary

- **Zero approvals.** At Google, Critique is the real admission control; presubmit is a linter in front of it. SASE agents push as the maintainer, and GitHub refuses self-approval. Substituting a server-enforced integration test for human review is the only admission control that can actually run. Record that substitution in the decision record so a later reader does not "fix" it by adding reviewers.
- **Two repositories instead of Piper.** Live-at-head and the One-Version Rule ([SWE ch. 16](https://abseil.io/resources/swe-book/html/ch16.html), [opensource.google oneversion](https://opensource.google/documentation/reference/thirdparty/oneversion)) assume one tree. SASE publishes two PyPI packages. The portable lesson is *not* "merge sase-core into sase." It is: a published sase version must keep its declared `sase-core-rs` window installable, and the train must *cut* that core release rather than hope it exists. That is already in revised requirement I. It is the entire reason 0.17.1 is currently a museum piece.
- **No production traffic split.** A CLI on PyPI cannot send 1% of `pip install` to the candidate. Mapping Borg canaries onto "install smokes in GHA" is incomplete, but mapping them onto Play Store percentages is theatre. The workable analog is below (same-bytes host canary + yank).

### Not justified: rebuilding, floating toolchains, hotfix-by-waiting, repair-epics, green-HEAD as selector

These are the places the plan is still "GitHub Actions doing Rapid's job with Rapid's safety rails left off."

**Selection vs mechanism.** Rapid's default is: take the revision the continuous build last marked green, branch there, build, test, package. Emergency pushes may cut from true head with a *minimal* extra suite. The original report listed "exact release commit" vs "tag-on-green" as a split and picked exact-SHA *now*, tag-on-green as fallback. The reassessment sharpened the candidate record (good) and made "given a SHA, publish exactly that SHA's files, or refuse" Epic A's bar (also good). It still under-specifies *which* SHA the train proposes. Google's answer is boring: the newest SHA that already has a complete, unexpired candidate record. If tonight's HEAD failed qualification, last night's candidate is what you publish. Walking forward from a red tip is how SASE spent seven weeks not shipping.

**Promotion vs checkout.** Pinning `actions/checkout` to the tag SHA stops the current "build whatever master is" bug. Google's stronger rule is: the *bytes* do not change after qualification. MPM applies a new label to the same hashed package. The plan's digest record and "a rebuild is a new candidate" are the internal form of that rule. The external form is missing: those bytes should be uploaded to TestPyPI (or a GitHub artifact that is the sole upload source), installed on a real host, then uploaded to PyPI. `skip-existing: true` without a digest check is how two builds become one "release." Revised E already says "existing filename accepted only after digest match." Make promotion of those bytes a named A-phase, not a footnote.

**Hermeticity.** SRE book ch. 8: "If two people attempt to build the same product at the same revision number on different machines, we expect identical results." "A project built last month won't use this month's version of the compiler." Master Gate's core-wheel job uses `dtolnay/rust-toolchain@stable`. `publish.yml` uses `astral-sh/setup-uv@v4` and `uv python install 3.12`. `just` is pinned by sha256 in the gate (good) and not obviously pinned in publish. sase-core is pinned by `sase-core-revision.txt` (good — that comment even records the unpinned-checkout incident). The compiler that *builds* that pin is not. Hermeticity is not Bazel-or-nothing; it is "the candidate record names every tool hash."

**Hotfix path.** Rapid's branch "never merge changes from the branch back into the mainline. Bug fixes are submitted to the mainline and then cherry picked into the branch." That sentence is the difference between "we can ship a one-line fix this afternoon" and "we will ship when HEAD is kind." SASE's Track 0 already contemplates "newest gate-green plus version bump" when HEAD cannot be held. That is half of Rapid. The other half is: given a *already published* 0.18.1 that is bad, produce 0.18.2 from the 0.18.1 snapshot plus cherry-picks, re-qualify that branch, and publish those bytes, while `master` continues. release-please wants the version bump on `master`; that is compatible: the hotfix branch is for the *package*, and the bump CL still lands on `master` so the next train does not reuse the version. Do not invent a long-lived `release` branch that never merges back — that fights release-please. Do invent a *snapshot branch per candidate* that lives long enough to cherry-pick.

**Postsubmit response.** TAP Postsubmit does not open an epic. It culprit-finds, then auto-rollbacks at high accuracy ([Henderson et al. 2023/2024](https://hackthology.com/speculative-testing-at-google-with-transition-prediction.html)). SASE's eight repair epics, each giving a 36-hour green window, are what a Google build cop is paid to *stop*. The merge queue will prevent many combination bugs from landing. It will not prevent time bombs, runner-image drift, or the next `f2a7b802f9`-style fixture. N3's circuit breaker and queue jump are the admission-side response. The missing piece is: when a landed SHA is the culprit, revert *that* SHA (or the small set FACF names), do not "fix forward" across 40 unrelated landings.

**Error budget.** The SRE workbook's canary chapter frames shipping as spending error budget. SASE's user-visible SLO is "a clean machine can `uv tool install sase` and `sase core health` passes." That SLO has been at zero for weeks while landings continued at 43/day. Google would freeze *launches that can make it worse* (dependency and packaging landings) until the SLO recovered. The plan's "days with installs broken = 0" metric is the SLO. It needs a freeze, not only a dashboard.

**CI is alerting.** Titus Winters' interlude in SWE ch. 23: 100% green CI is as expensive as 100% uptime; a test failure that does not violate a user invariant should be disabled, not used to block every commit. The original report's expected outcome, "no deterministic break can reach `master` by any path," fights that paragraph. The queue should refuse *untested combinations* and *known-red required checks*. It should not be asked to prove the absence of all deterministic defects (the reassessment already said no suite can). Advisory lanes being red must not freeze the train.

## Inspiration worth stealing, mapped onto SASE objects

Google practice → SASE object, if adopted:

| Google | SASE object |
| --- | --- |
| Green head vs true head | A durable `release/latest-qualified` ref or candidate pointer, updated only when a candidate record is complete. The train publishes that pointer. `master` may be red. |
| MPM labels | The same wheel/sdist sha256, stored as a GitHub Actions artifact, uploaded to TestPyPI, installed on apollo or athena, then uploaded to PyPI. Labels are states of one digest, not new builds. |
| Rapid cherry-pick branch | `release/snapshot/<tag>` created at qualify-time, protected from force-push, used only for hotfix cherry-picks. Version bump still lands on `master` via release-please. |
| Canary vs control | Host canary: install the candidate wheel into a fresh venv on a real machine, run `sase core health`, `sase version --json`, and a short doctor/smoke. Compare against the currently published version on the same machine. GHA smokes stay as the cheap first stage. |
| Build cop | One on-call-shaped job (already sketched in D6): a 48-hour clock on advisory red, a page when the install canary is red, authority to pause admission via the N3 hold. |
| Auto-rollback | A postsubmit watcher: when Master Gate or the release-blocking set newly fails on a landed SHA, bisect against the last green, open a revert PR that jumps the queue (N3). Humans confirm only if the culprit finder is below a stated confidence. |
| Hermetic Blaze | Candidate record fields: `python`, `uv`, `just`, `rustc`, `maturin` versions *and* hashes; `sase-core-revision.txt`; the wheel digest. `rust-toolchain@stable` is forbidden in release and gate jobs. |
| Binary `--version` | Wheel metadata or a generated `_build_info.py`: package version, git SHA, core SHA, candidate id, build timestamp. `sase version --json` prints them for a PyPI install, not only for an editable checkout. |
| Signed MPM | GitHub artifact attestations (already adjacent to OIDC trusted publishing) binding those fields to the wheel digest. SLSA Build L1 now, L2 because GHA is a hosted platform. |
| Error-budget freeze | If the daily install canary is red, the train does not cut, and landings that touch `pyproject.toml`, `uv.lock`, `sase-core-revision.txt`, or packaging workflows are held. Other landings may continue. |
| Flag-guarded launch | A PyPI cut is never blocked on an unfinished flag. A flag default-on is its own canary (host + a subset of projects), not a reason to hold the wheel. |
| Change report | Keep release-please's changelog, which is Rapid's CL list, *provided* history stays linear (N2). |
| Self-service Rapid | Qualification green on a candidate is sufficient to publish. `ci_watch` becomes the failure pager, not the success button. |

## What not to copy

- **A global submit queue at TAP scale, or affected-target selection via Bazel.** SASE's suite is already the "project." Running the whole fast suite on each stacked candidate is the small-repo version of TAP presubmit. Do not spend an epic on RTS.
- **Required human review.** Deadlocks the maintainer-as-agent model. Mechanical admission replaces it.
- **Merging sase-core into sase to chase One-Version.** The cost is a new monorepo program. The portable invariant is retention-plus-train-cuts-core.
- **Long-lived release branches that never merge back.** Rapid can do this because Piper + Rapid own the version number. release-please owns SASE's version number on `master`. Snapshot branches are for hotfixes, not for the version bump.
- **Play Store / GKE channel mechanics.** No traffic fraction exists on PyPI. Yank + previous-version-still-resolves is the rollback; TestPyPI + host install is the canary.
- **"Push every green build" for a CLI.** Search and Ads push on green because a Borg job can be reverted in minutes. A yanked PyPI wheel has already been installed by humans. A 1–3 day train of *qualified* snapshots is the Search-train analog, which Google itself used when the binary was large and the cost of a bad push was high.
- **100% green as a moral requirement.** SWE ch. 23 spent pages killing this. The queue's job is tested combinations and trustworthy required checks, not theological cleanliness.

## Ranked changes to the planned process

Ranked by expected reliability gain per unit of implementation cost, as modifications to the *current* (reassessment) plan. Items the plan already contains are omitted.

### 1. Make last-known-green the selection policy; keep exact-SHA as the publish mechanism

Epic A currently says: given a SHA, publish exactly those files or refuse. Add the missing sentence: **the train's input is the newest SHA that already has a complete candidate record, not `master` HEAD.**

If tonight's HEAD failed qualification, publish last night's candidate (or refuse). Walking forward from a red tip is how 0.18.0 aged 49 days. This is Rapid's green-head cut. Tag-on-green is not a fallback; it *is* the policy. Exact-SHA is how you implement it without `publish.yml` racing HEAD.

Acceptance: a documented pointer (`release/latest-qualified`, or a candidate object the watcher already understands) that moves only when qualification of the release-blocking set is complete. The nightly train reads that pointer. A red `master` does not block it.

### 2. Promote one digest: GitHub artifact → TestPyPI → host canary → PyPI

Extend A3. After digests are recorded:

1. The wheel and sdist in the candidate record are the only files that may be uploaded anywhere.
2. Upload them to TestPyPI (or keep them as the sole Actions artifact; do not rebuild).
3. On a real host (athena or apollo), in a clean venv, install *those bytes* (not "sase from PyPI"), run `sase core health`, `sase version --json`, and the existing public-command smoke.
4. Only then upload the same bytes to PyPI, with "existing filename" accepted only on digest match (already in E). Delete `skip-existing: true` as a substitute for that check.
5. After PyPI, a daily install canary from *public* PyPI (Track 0 / revised A) stays green.

This is MPM labels. GHA install-smokes stay as stage 0; they do not see real `SASE_HOME`, real plugins, or real core wheels the way a host does. PyPI is the 100% population; it must not be the first population.

### 3. Pin every toolchain into the candidate; forbid `@stable` on gate and publish

Hermeticity is the SRE book's third release-engineering principle and the plan's largest unstated hole.

- Pin `rustc` (and `rust-toolchain.toml` / a hash), `uv`, CPython, `just`, `maturin`. Master Gate already sha256-pins `just`; copy that pattern.
- Replace `dtolnay/rust-toolchain@stable` in `.github/workflows/master-gate.yml` (and any publish/core-wheel path) with the pin recorded in the candidate.
- A cherry-pick rebuild of tag `v0.17.1` must recover 0.17.1's toolchain, not today's.

Without this, A1's "checkout the SHA" still produces a snowflake whenever GitHub runners or `@stable` move. That is exactly the class of bug that reddens a green SHA without any landing (N3's drift), and Rapid's answer was "the build tools are versioned based on the revision of the project being built."

### 4. Add a snapshot-branch hotfix path

When a published version is wrong, or HEAD cannot be held, Rapid cherry-picks onto the released revision.

- At qualify-time, create `release/snapshot/<tag>` at the candidate SHA. Protect it like `master` (no force-push, no deletion).
- Hotfixes: land the fix on `master` (so the next train contains it), cherry-pick onto the snapshot, re-run the release-blocking set on the snapshot, publish those bytes as the next patch version.
- release-please still bumps on `master`. The snapshot is not a second source of version truth.

Track 0's "newest gate-green plus version bump" is the first use. The second use is the first yanked 0.18.x. Without this path, every production incident waits on a red merge queue.

### 5. Give the installability SLO a freeze, not only a metric

Revised C adds "days with installs broken = 0." Google would spend error budget *and stop spending it* when the SLO is exhausted.

When the daily public-PyPI install canary is red:

- The train does not cut.
- Landings that modify `pyproject.toml`, `uv.lock`, `sase-core-revision.txt`, packaging workflows, or sase-core retention are held (N3 hold, already designed).
- Other landings may continue. Freezing *all* admission is how you turn an install outage into a 43-PR queue storm.

This is the SRE workbook's "shipping spends error budget," applied to the only SLO users actually hit.

### 6. Make revert-the-culprit the postsubmit default

Replace "open a repair epic" with TAP's loop:

- When a required check newly fails on a landed SHA, and the N3 base-red witness says the *base still passes*, bisect (even a linear walk is enough at 43/day).
- Open a revert PR that jumps the queue (N3 already has jump for the base fix; use it for the culprit too).
- Quarantine only after the revert, if the test is flaky rather than causal.
- Advisory-lane failures still file a `ci` bead with a 48-hour clock (N1); they do not revert product changes by default.

Eight decay-in-36h repair epics are the empirical proof that fix-forward cannot keep this tree releasable. Google's auto-rollback papers exist because humans do not win this race at this landing rate.

### 7. Bake candidate identity into the published wheel

SRE book: every binary prints build date, revision, and build id. `sase version` is already a rich inventory for editable checkouts; a PyPI install should answer the same question without a git tree.

Generate, at A1 build time, a small module or dist-info field with: version, git SHA, core pin SHA, candidate id, tool pins, wheel digest. `sase version --json` must show them after `uv tool install sase`. Support incidents otherwise begin with "which bytes are on apollo?"

### 8. Rehearse yank, and make previous versions remain resolvable

Rollback is Google's first response. On PyPI that is yank, plus the retention invariant already in I.

Add a drill, owned by Epic A, on TestPyPI or a throwaway project: publish, yank, confirm the previous version still installs, confirm the yanked version stops resolving. Put the production runbook next to D7's queue-outage rehearsal. A retention invariant that is not drilled will fail the same way it failed for 0.17.1: silently, weeks later.

Do not treat "forward-fix on `master` and wait for the train" as rollback.

### 9. Make the train self-service; page only on failure

Rapid is self-service so that cutting a release is not a ticket. SASE's `ci_watch` currently behaves like a human-in-the-loop gate.

Once A2/A3 exist: a complete candidate record *is* authorization to publish. The human (or a build-cop agent) is involved when qualification fails, the install canary is red, or the freeze in (5) trips. Success is silent. That is also how you get 1–3 day cadence without a person remembering to press `publish_existing`.

### 10. Treat CI as alerting in the decision record; do not resurrect "HEAD is always green"

When the new decision supersedes the merge-queue clause of `ci-two-speed-split`, write Winters' paragraph into it:

- The queue's contract is: every landed SHA was an integrated candidate whose *required* checks passed.
- Advisory red does not freeze the train.
- 100% green is not a goal; false-red rate, landing p50/p95, and installability are.
- A test that does not violate a user invariant is disabled or demoted, not used to block 43 landings.

The original report's closing sentence ("no deterministic break can reach `master` by any path") should not return as an epic slogan. The reassessment already replaced it; keep the replacement.

### 11. Say out loud that a PyPI cut must not wait on a flag, and a flag flip is its own canary

This is cheap policy, not an epic. SWE ch. 24's entire point is that binary velocity and feature launch are different knobs. SASE already has the knobs. The train should refuse to wait on an unfinished flag, and a default-on flip should go through the host canary (item 2) rather than "it shipped in 0.18.x so it is on."

### 12. Keep C and D split; do not add a host-side landing lane

This is a non-change, recorded because Google's TAP *does* land first and repair after, which can be misread as support for a host landing lane.

A host-side serial `just check` (12 min p50, 59 min p90, two machines, 3–6% pass rate) is not TAP. TAP is a distributed hermetic farm with culprit finding. GitHub's merge queue is the farm SASE actually has. C (sandbox product) and D (production cutover) prove different things in different places; merging them soaks a product flag for weeks. Google would call C the Rapid blueprint on a scratch project and D the production rollout. Keep them split.

---

Items 1–6 are the ones I would not ship the four-epic program without. Items 7–11 are cheap and prevent the next class of "we published the right SHA and still could not tell what we published / could not undo it / waited on a flag." Item 12 is a recommendation to *not* reopen rejected alternatives.

## Alternatives considered

- **"Just do what TAP does: land, then revert."** Rejected as the *admission* design. Piper landings are atomic and globally ordered; GitHub pushes from two hosts are not. The original's 40% overlap figure is the mid-air collision rate TAP accepts and then spends half its compute hunting. A merge queue at this size is cheaper than FACF.
- **"Push on green every Master Gate pass."** Rejected for a PyPI CLI. Borg rollback is minutes; PyPI yank does not uninstall. A train of qualified snapshots matches Search's every-other-day model, which Google used when a bad binary was expensive.
- **"Required reviewers, like Critique."** Rejected: self-approval deadlock. Mechanical admission is the substitute.
- **"Monorepo sase + sase-core."** Out of scope. Retention + train-cuts-core is the One-Version lesson that actually caused user pain.
- **"Host landing lane as Rapid."** Rejected in the original for good reasons (local signal, two hosts, not a fence). Rapid is a *server-side* hermetic builder, which on this stack is GitHub Actions plus a candidate record, not apollo's `just check`.

## Method, confidence, and limits

**Read through audited channels:**

- `research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`
- `research:202610/merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md`
- Decision records `ci-two-speed-split`, `check-full-is-explicit`, `host-owned-completion`, `receipts-prove-before-they-skip`

**Read in the sase checkout:**

- `.github/workflows/publish.yml` (checkout without `ref:`, `skip-existing: true`)
- `.github/workflows/master-gate.yml` (`dtolnay/rust-toolchain@stable`, `sase-core-revision.txt` pin, sha256-pinned `just`)
- `release-please-config.json`
- `src/sase/__init__.py` (`__version__ = "0.17.1"`)
- `src/sase/version/` (`sase version` inventory; git probe is checkout-oriented)

**Google sources** are the public SRE book, SRE workbook, *Software Engineering at Google*, TAP/Rapid talks and papers, SLSA, and the One-Version policy. I did not have access to internal `go/` links, Rapid blueprints, or Bryan's team's actual pushmaster config. Ads/Commerce push-on-green is represented by the public Kle14 / Betser15 papers, which match the SRE-book description.

**High confidence:** the planned SASE architecture as restated from the two context reports; the `publish.yml` and Master Gate defects; the Rapid/TAP/MPM public model; the ranked mapping of green-head, hermeticity, cherry-pick, canary, and revert.

**Medium confidence:** exact false-red percentages and queue-simulation numbers, which I took from the context reports and did not re-derive. How closely Bryan's Google team matched textbook Rapid vs a local push-on-green variant.

**Not claimed:** that implementing items 1–6 would have shipped 0.18.0 in August. Track 0 (core floor, retention, one gate-green SHA) still has to exist. The claim is that without 1–6, the four epics will reproduce Rapid's *shape* without Rapid's *safety*, and the next stall will look like this one: right SHA, wrong bytes, uninstallable previous version, fix-forward epics.

**Not done:** no workflows, rulesets, memory, or beads were changed. No TestPyPI canary was run. Peer swarm reports were not read.

## Sources

**SASE plan (context):**

- [Merge-queue-fenced `master` and exact-SHA PyPI releases](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md)
- [Fence reassessment and four-epic split](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md)

**SASE code and decisions:**

- `.github/workflows/publish.yml`, `.github/workflows/master-gate.yml`, `release-please-config.json`
- `decisions:ci-two-speed-split`, `decisions:check-full-is-explicit`

**Google, primary:**

- Dinah McNutt, [Release Engineering](https://sre.google/sre-book/release-engineering/), *Site Reliability Engineering* ch. 8 — Rapid, hermetic builds, cherry-pick branches, MPM labels, self-service, high velocity
- Alec Warner and Štěpán Davidovič, [Canarying Releases](https://sre.google/workbook/canarying-releases/), *SRE Workbook* ch. 16 — canary vs control, error budget, do not rebuild, SLI-gated promotion
- Rachel Tannenbaum, [Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html), *Software Engineering at Google* ch. 23 — TAP, presubmit vs postsubmit, green head vs true head, "CI is alerting," flake quarantine, hermetic tests
- Narayan, Jones, Shipe, Owens, [Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html), *Software Engineering at Google* ch. 24 — trains, "no binary is perfect," flag guards, faster is safer, A/B of the deployment itself
- Titus Winters, [Version Control and Branch Management](https://abseil.io/resources/swe-book/html/ch16.html) and [Dependency Management](https://abseil.io/resources/swe-book/html/ch21.html) — One-Version, live-at-head, short-lived branches
- [One Version Rule](https://opensource.google/documentation/reference/thirdparty/oneversion), Google Open Source

**Google, supporting:**

- McNutt, [Release Engineering Best Practices at Google](https://www.usenix.org/conference/lisa15/conference-program/presentation/mcnutt), LISA15
- Klein et al., [Making “Push On Green” a Reality](https://research.google/pubs/making-push-on-green-a-reality-issues-actions-involved-in-maintaining-a-production-service/) (USENIX ;login: / Kle14)
- John Micco, [Advances in Continuous Integration Testing @ Google](https://storage.googleapis.com/gweb-research2023-media/pubtools/4183.pdf) — TAP scale, project-level greenness, 50% of test compute is postsubmit
- Henderson et al., [Flake Aware Culprit Finding](https://hackthology.com/flake-aware-culprit-finding.html) (2023) and [Speculative Testing / Auto Rollback](https://hackthology.com/speculative-testing-at-google-with-transition-prediction.html) (2024–2025)
- [SLSA Build track](https://slsa.dev/spec/v1.0/levels) — provenance exists (L1), hosted signed provenance (L2)

**Industry analog already in the plan's sources, not re-litigated here:** GitHub merge-queue docs, the 2026-04-23 queue incident, Uber "Keeping master green," GitLab quarantine. Those informed the *queue* design. This report asks what Rapid would add *on top of* a working queue.
