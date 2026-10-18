**What SASE should borrow from Google's release engineering: qualified artifacts, controlled exposure, and recoverability**

Independent research by **cdx**, 2026-10-18.

**Conclusion.** Keep the revised proposal's native merge queue, exact-candidate publication, separate integration and release checks, and four-epic structure. They fit the useful parts of Google's published approach well. The largest remaining opportunity is to make the release process prove that the packaged application works during real use and can be recovered safely. A protected branch and a successful upload establish only part of that promise.

I recommend changes, principally to Epic A's qualification and recovery contract and Epic D's operational acceptance criteria. They should not delay the existing effort to restore installability. The ranked recommendations conclude this report.

**Evidence and scope.** I read the supplied [original proposal](merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md) and [reassessment](merge_queue_fence_reassessment_and_epic_split/merge_queue_fence_reassessment_and_epic_split.md) through audited artifact reads. Where they disagree, the reassessment is the baseline. In particular, this report assumes rebase with one commit per PR; a versioned inventory separating admission, release-blocking, and advisory checks; an immutable candidate record; dependency retention; and four independently verifiable epics. Recommendations below identify additions to that baseline rather than re-proposing those features.

I independently checked the local SASE checkout at `7b9436bedeed0ba7a716a3a6a91ff55d776e09d6`, principally `publish.yml` and `pyproject.toml`. I did not rerun the earlier CI analysis, resolve today's public dependency graph, or inspect live administrative settings. The installability outage and CI statistics in the supplied reports remain **their dated observations**, not new measurements here. I did not consult any other report or conversation from this research swarm.

The Google comparison uses first-party publications: the original *Site Reliability Engineering* book, the 2018 *SRE Workbook*, the 2020 *Software Engineering at Google* and *Building Secure and Reliable Systems* books, Google's testing blog, and Chromium's channel documentation. These establish documented practices, not a uniform account of every Google team's internal process in October 2026. Google explicitly describes teams choosing different release frequencies and workflows. This is particularly relevant when comparing a Python application distributed through PyPI with a centrally operated Google service. [Google: Release Engineering](https://sre.google/sre-book/release-engineering/)

**The comparison.**

| Dimension | Google's documented approach | Revised SASE proposal | Assessment |
|---|---|---|---|
| Integration versus release | Fast, reliable presubmit checks; broader checks later; a distinction between true head and verified green head. [Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html) | Queue admission is separate from release qualification. | Strong match. Keeping Full CI off every landing is justified. |
| Release identity | Rapid records build identity; packages have unique hashes; release contents are traceable. [Release Engineering](https://sre.google/sre-book/release-engineering/) | Candidate records bind source, core pin, policy, runs, attempts, and distribution digests. | Strong match; the planned candidate record is a substantial improvement. |
| Build environment | Hermetic builds identify tools and dependencies rather than inheriting arbitrary workstation state. [Release Engineering](https://sre.google/sre-book/release-engineering/) | Exact source and files are specified; complete build/runtime inputs are less explicit. | Extend qualification to the actual dependency environment. |
| Exposure to users | Canary evaluation limits exposure and uses observations to decide whether rollout proceeds. [Canarying Releases](https://sre.google/workbook/canarying-releases/) | Upload confirmation and a daily clean-install canary. | Useful probes, but not yet a behavioral rollout canary. |
| Client distribution | Chrome offers distinct channels and separate user-data directories for parallel installations. [Chrome Release Channels](https://www.chromium.org/chrome-release-channels/) | A PyPI release plus local installations. | A small opt-in cohort and isolated state are more relevant than copying a server traffic percentage. |
| Cadence and release scope | Predictable trains have cutoffs; late features wait for another train. [Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html) | A nightly opportunity to release, with a 1–3 day eventual cadence target. | Keep the cadence; make selection, abandonment, and repair explicit. |
| Authority | Release controls include review, restricted operations, and proof about deployed artifacts. [Deploying Code](https://google.github.io/building-secure-and-reliable-systems/raw/ch14.html) | Zero routine PR approvals, deterministic evidence, shared maintainer credentials still acknowledged. | A reasonable scale adaptation, but not equivalent independent review or privilege separation. |
| Failure policy | An example error-budget policy redirects work toward reliability when user-facing objectives are missed. [Example Error Budget Policy](https://sre.google/workbook/error-budget-policy/) | Owners, repair turns, clocks, and notifications. | Add a bounded policy that actually changes work priorities. |

**Keep the separation between integration and release.**

Google's CI chapter explains why presubmit cannot economically run everything. It also describes release candidates being cut from verified code and promoted through environments without rebuilding their artifacts. That supports SASE's two verification tiers and its build-once proposal. It does not establish that every Google repository has an unbreakable trunk, or that Google uses GitHub-style merge queues. [Continuous Integration](https://abseil.io/resources/swe-book/html/ch23.html)

For SASE, the native queue addresses a concrete interaction problem: independently acceptable changes can fail when combined. Retain it. However, distinguish three outcomes throughout the product: a change **landed**, a candidate **qualified**, and a release **worked for users**. The reassessment already handles the first two carefully; the third needs stronger evidence.

Similarly, Google describes release branches and selected cherry-picks in Rapid. The transferable idea is that a release has a stable identity while development continues. SASE can obtain that property with its immutable candidate record without adopting permanent release branches or replacing release-please. A repair changes the candidate and requires new qualification. [Release Engineering](https://sre.google/sre-book/release-engineering/)

**Extend exact-source identity to the application that actually runs.**

The reassessment already goes well beyond “checkout the right SHA”: it includes nested checkouts, digests, run attempts, policy versions, partial-upload recovery, and rebuilds creating new candidates. Preserve all of that.

There is still an important distinction between these identities:

`SASE source revision → SASE distribution bytes → installed dependency set → configured, stateful application`

Equality at the first two positions does not imply equality at the last two. This is a direct concern here: the checked-out `pyproject.toml` has a range for `sase-core-rs`, a broad Textual requirement, and build requirements including `hatchling>=1.27` and an unversioned `hatch-fancy-pypi-readme`. Those declarations are not a complete reproducible environment. This observation alone does not prove a present build defect; it identifies inputs that source-SHA identity does not constrain. [Local source at the inspected revision](https://github.com/sase-org/sase/blob/7b9436bedeed0ba7a716a3a6a91ff55d776e09d6/pyproject.toml#L1)

My proposed amendment to A1/A2 is to record the build backend and tools, material build-environment identifiers, and exact dependency resolutions used for qualification. Pin the build toolchain and build dependencies; treat byte-for-byte reproducibility as a separately tested property, not something guaranteed by storing a manifest. For the Rust component, distinguish the source pin used by development CI from the **published binding distributions users install**. A passing test against an unpublished locally built extension is insufficient evidence about the published core floor. Test meaningful SASE behavior against that floor and against the normal public resolver result. The existing health and CLI smokes remain useful first checks.

Run two deliberate kinds of validation. A controlled dependency resolution gives repeatable release evidence. A fresh resolution against public package metadata detects changes that affect real new installations. Do not make both lanes frozen and thereby hide ecosystem drift; do not make both floating and thereby lose reproducibility. Record the resolved dependency set for each result.

The supported-runtime inventory should enumerate Python versions and supported operating-system/architecture combinations for install testing. Python 3.13 unit tests alone do not establish that the necessary native wheel exists for every supported target. Full application testing on every possible combination would be excessive; install/extension smokes can be broad while representative behavioral coverage remains selective.

The retention rule also needs a recovery dimension. “Last two SASE releases” is a useful minimum, but the protected set should include the designated rollback release and active candidates, even when they fall outside the latest N releases. Retain enough dependency distributions and configuration information to reinstall those environments on supported targets. Define a support horizon rather than silently promising that every historical version remains usable forever. Third-party package availability is outside SASE's full control, so a tested internal recovery bundle or mirror may be justified for the small rollback set.

**Add a real behavioral canary, and make its result useful.**

Google's workbook describes canaries as limited deployments evaluated before wider rollout. It stresses representative workloads, sufficient observations, and metrics scoped to the candidate. It also distinguishes synthetic testing from canarying real use. These distinctions matter more for SASE than choosing an arbitrary “5% for 30 minutes” rule. [Canarying Releases](https://sre.google/workbook/canarying-releases/)

A6's daily `uv tool install sase` plus `sase core health` is an excellent **installation probe**. It can catch resolver backtracking and missing dependencies. It cannot establish that a service restart preserves pending work, an agent completion is recorded correctly, or the TUI stays usable during an ordinary session.

My proposed small-scale rollout is:

1. Build and qualify the candidate distributions as already planned.
2. Install those exact final-version files in an isolated environment and run a compact behavioral suite. This is preproduction validation, not yet a real-use canary.
3. Give the exact same files to one explicitly opted-in installation or cohort for ordinary work, with a separate state root and a retained recovery environment.
4. Promote by uploading the identical distributions to PyPI when the cohort meets the declared acceptance policy.
5. Keep the public install probe and add confirmation that the expected version works after publication.

This is a proposal for future implementation, not authorization to update Bryan's current installation. It also needs protection against accidental shared external writes: separate local state does not by itself isolate GitHub, sidecars, or other remote systems. Use an appropriately scoped project and credentials for the exercise.

A representative SASE exercise might cover startup, one complete agent task, finalization, a service restart, a queued or pending operation, and TUI interaction. Count completed exercises and unexpected failures, record the candidate/dependency identities, and report candidate-specific latency and resource usage. A handful of successful tasks cannot establish a low rare-failure rate; call insufficient coverage **inconclusive**, rather than green. Use a maximum observation deadline that returns an explicit hold, not indefinite waiting or automatic approval.

The initial policy should be cheap enough to fit the release cadence. Expand it only when incidents demonstrate a missing scenario. An initial real-use cohort could remain manually enrolled while qualification and promotion are automated. A permanent four-channel Chrome clone, sophisticated experimentation service, or mandatory week-long soak would be unjustified.

Do not promise byte-identical promotion from a public `0.x.yrc1` wheel to `0.x.y`: changing the embedded version changes the artifact. The simplest route is to canary final-version bytes before their public upload. If public prereleases are desired later, treat the final-version build as a distinct candidate requiring its own qualification. Likewise, TestPyPI upload recovery tests prove publication mechanics; they do not by themselves prove the ordinary PyPI dependency environment.

**Prove recovery of state as well as packages.**

The revised N9 is about recovering the **landing mechanism** while preserving its fence. SASE also needs recovery from a bad **released application**. These are separate acceptance tests.

My proposed release requirement is: every candidate declares its compatible state/configuration range and demonstrates a recovery path using retained artifacts. Exercise upgrade from the supported stable release, restart, and either downgrade or an explicit alternative recovery procedure. Include the Rust binding and relevant plugin/configuration compatibility. For shared state or mixed-version hosts, test that combination or refuse it clearly.

Package rollback is unsafe if a new binary has irreversibly changed durable data. Prefer compatible, staged migrations when practical. Where downgrade cannot be supported, test backup restoration or forward repair and state the limitation before promotion. Never automatically restore a stale backup over legitimate work written since the upgrade. The recovery policy must say how those writes are preserved or reconciled.

After public distribution, recovery has different limits. PyPI yanking discourages new ordinary resolutions but exact version pins can still select a yanked release; it does not uninstall code already running. PyPI also prohibits filename reuse. SASE therefore needs a rehearsed combination of halting promotion, retaining the previous supported environment, yanking when appropriate, and shipping a corrected version. Deleting releases or moving tags is not a recovery strategy. [PyPI yanking](https://docs.pypi.org/project-management/yanking/), [PyPI filename reuse](https://pypi.org/help/#file-name-reuse)

**Keep advisory checks, but qualify their failures by user impact.**

The reassessment makes an important correction by separating release blockers from admission checks. I would refine N1, however. A check's runtime and false-red rate help decide where it runs; they cannot alone determine whether the defect it finds is acceptable to ship.

Google's delivery chapter describes release decisions based on explicit product-health thresholds and includes an example of delaying a release for a small affected user population. It does not suggest that every imperfection blocks release. The useful lesson is to define acceptable impact and apply that policy consistently. [Continuous Delivery](https://abseil.io/resources/swe-book/html/ch24.html)

For SASE, add a defect policy above the suite inventory. Confirmed corruption, lost work, broken supported installations, or severe regressions in essential workflows block promotion regardless of which suite found them. A cosmetic screenshot mismatch can remain advisory. A confirmed inability to interact with an essential screen cannot become harmless because it was discovered by `visual-test`.

Use narrow, recorded exceptions for known low-impact problems: affected check/case, evidence, reason, owner, expiry, and affected release scope. Avoid perpetual blanket permission for an entire suite. This is not a proposal to put Full CI back into the merge queue or to require every screenshot to pass before release. It is a proposal to keep known product defects from disappearing behind a coarse job classification. A suspected serious defect with incomplete evidence should hold promotion until bounded triage resolves it.

B1 needs a related measurement refinement. Rerunning three failed nodes serially can mitigate an unreliable signal, but it also changes concurrency and order. A pass on that rerun is **recovered on rerun**, not proof that the original failure was a harmless false red. Google's testing guidance explicitly identifies application races, test order, framework interference, and hardware/resource conditions as distinct sources of flakiness. [Google Testing Blog: Test Flakiness](https://testing.googleblog.com/2020/12/test-flakiness-one-of-main-challenges.html?hl=id)

Keep the proposed bounded retry and preserved first result. Count raw failure, recovery, adjudicated false rejection, and confirmed intermittent product defects separately. For repeat offenders, reproduce the relevant shard/order/concurrency before using “flaky” to justify quarantine. A green rerun should never erase a demonstrated lost-work race.

**Give release health an operational consequence.**

The planned owner, 48-hour clock, and notification are useful, but they do not guarantee that release-blocking work wins priority. The earlier reports describe recurring repairs without sustained delivery. My inference is that another notification alone risks preserving that pattern.

Google's published example error-budget policy ties breached user-facing objectives to restrictions on ordinary change and prioritization of reliability work. It is an example policy, not a mandate that SASE adopt its thresholds or its organization. [Example Error Budget Policy](https://sre.google/workbook/error-budget-policy/)

For SASE, begin with a small release-health policy: latest supported installation broken, serious canary regression, or repeated inability to produce a qualified candidate triggers one accountable repair effort and limits new feature work in the implicated area. Unknown infrastructure failures first need classification. A cosmetic advisory failure does not freeze the repository. Repair work and emergency/security releases remain possible under explicit criteria.

Measure publication and user outcomes alongside queue performance: age of the latest qualified candidate, changes accumulated since the working release, clean-install success by supported target, releases needing emergency repair, detection-to-containment time, and recovery-drill results. Treat small release counts as counts with denominators, not impressive-looking percentages. Preserve the existing landing latency and false-red measurements.

The release train also needs a firm cut: select an eligible source, freeze the candidate, and let later changes wait. If it fails, repair or discard that candidate explicitly. Do not repeatedly replace its contents with the moving tip during qualification. The reassessment already gives the necessary candidate identity; this adds scheduling semantics. With the original report's approximately 43 daily landings, a three-day interval can accumulate roughly 129 changes if volume remains similar. That is an illustration based on its historical arrival rate, not a current measurement. Track actual batch size before increasing frequency.

**Protect the rules that authorize a release.**

Zero human approvals on ordinary queue tickets is a practical choice for SASE. It is a deliberate departure from independent code review, and two agents using the same maintainer authority do not create a second trust boundary. Automated passing checks also cannot compensate for unrestricted ability to change which checks are required.

Google's secure-deployment guidance treats configuration and artifact provenance as part of the release system. Its provenance model includes build inputs and outputs, and it argues that deployment authorization should check the artifact's evidence rather than merely the identity requesting deployment. [Deploying Code](https://google.github.io/building-secure-and-reliable-systems/raw/ch14.html)

The inspected SASE publish job already uses a `pypi` environment and `id-token: write`; recommending “adopt OIDC” as if absent would be misleading. The next step is to verify the actual publisher identity, environment protections, alternate credentials, and who can modify publication and qualification policy. I have not audited those administrative settings. [Inspected publish job](https://github.com/sase-org/sase/blob/7b9436bedeed0ba7a716a3a6a91ff55d776e09d6/.github/workflows/publish.yml#L351)

Restrict publishing authority to the approved workflow and put changes to the release inventory, retention policy, and publishing authority under explicit maintainer control. This can be a narrow control-plane approval path without making every ordinary agent change wait for human review. If agents retain full administrative authority, document that the fence protects against mistakes but is not an independent privilege boundary.

Use available publish attestations to bind package digests to the publisher, while keeping qualification evidence separate. PyPI's own documentation cautions that Trusted Publishing and attestations do not prove the safety of the software or the quality of its tests. Signing a defective artifact does not make it release-qualified. [Trusted Publishing security model](https://docs.pypi.org/trusted-publishers/security-model/), [Attestation security model](https://docs.pypi.org/attestations/security-model/)

**One queue claim needs correction before implementation.**

The reassessment's N8 says merge limit 1 keeps the proof trivial and treats it as protection against multi-PR groups. GitHub documents that merge limits control how many PRs merge into the base together; they do not combine or define `merge_group` builds. A speculative build can include the preceding queued changes. Therefore, merge limit 1 with build concurrency 2 does not establish that each tested candidate contains only one PR's changes. [GitHub: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

Keep the sandbox experiment and treat the rebase SHA mapping as a measured property. Test at least two queued changes, an earlier failure, a rewritten head, and reordering. Do not assume raw SHA equality or infer immunity from a historical service incident from this setting. Exact artifact qualification remains valuable independently of queue provenance. There is no Google-derived reason here to change the selected merge method or build a custom queue.

**Scope discipline.** I would keep A, B, C, and D. Candidate/environment evidence, basic behavioral validation, and recovery contracts belong in A; retry semantics and quarantine evidence belong in B; cumulative queue proof belongs in C; production cohort operation, metrics, and release-health policy belong in D. D's release-train proof requires A, as the reassessment already states. A full canary platform need not become a fifth epic or a prerequisite for Track 0. If progressive rollout grows materially, deliver a later bounded extension after the minimum protocol works. I would not add Bazel adoption, a monorepo migration, Google's organizational roles, a permanent release branch, or a Google-scale rollout service to this program.

**Ranked changes to consider.** Ranked by expected reduction in SASE's release risk relative to implementation and operating cost; the ranking is my judgment, not a measured cost model.

1. **Add staged behavioral qualification using the exact release files.** Extend A2 and D6 beyond installability: representative packaged-app exercises, then an isolated opt-in real-use cohort before public publication. Preserve candidate-specific observations and an inconclusive outcome when coverage is insufficient. Start with a small suite and cohort, not a rollout platform. **Acceptance:** a candidate that imports successfully but fails a representative task or restart is withheld, and a passing candidate reaches PyPI with identical distribution digests. Keep Track 0 unblocked by the full rollout extension.

2. **Make recovery of application state a release contract.** Extend A3/A5 and D's rehearsal to retain a working environment, protect its dependency closure, and exercise upgrade plus downgrade or a declared alternative. Treat shared state and incompatible migrations explicitly. **Acceptance:** a deliberately bad candidate can be contained and a working supported environment restored without losing subsequent legitimate work; if downgrade is impossible, the tested recovery method is clearly recorded. This closes a gap that queue-outage recovery does not cover.

3. **Add a severity-based release veto above N1's check categories.** Preserve fast admission and advisory suites, but never let “advisory” authorize a confirmed severe product regression. Require scoped, expiring evidence for accepted failures. **Acceptance:** a cosmetic visual mismatch can be accepted with a record, while a confirmed essential-workflow failure found by the same suite blocks promotion. This balances delivery continuity against known user harm without restoring the all-or-nothing Full CI gate.

4. **Record and test the installed dependency environment, not only the source/core pin.** Extend A1/A2/A5 with build-tool identities, resolved runtime dependencies, published-core behavioral coverage, a declared platform matrix, and protected rollback dependencies. Keep both a reproducible lane and a fresh-public-resolution probe. **Acceptance:** qualification detects a published core missing a required API, a supported target missing a usable native package, or a public resolver drifting away from the tested environment. Do not require a wholesale build-system replacement.

5. **Turn release-health failures into a bounded repair policy.** Add explicit candidate cutoffs, disposition of failed candidates, and a scoped stop on unrelated feature work when installation or essential workflows remain broken. Measure qualified-candidate age, batch size, user failures, and containment time in addition to queue health. **Acceptance:** simulate repeated candidate failure and show that one repair owner is activated, the candidate remains fixed, and no duplicate repair swarm or indefinite notification-only state results. Thresholds should follow observed operation rather than copied Google percentages.

6. **Protect release policy and publishing authority separately from routine landing.** Keep zero approvals on ordinary queue tickets; verify the existing OIDC/environment configuration and reserve qualification-policy and publisher changes for explicit maintainer control. Retain artifact attestations as identity evidence, not test evidence. **Acceptance:** ordinary landing authority cannot directly publish an unqualified distribution or silently weaken the policy authorizing it. Where current credentials prevent that separation, state the limitation and make its removal an explicit follow-up boundary.

7. **Stop treating a successful isolated retry as proof of a false red.** Preserve B1's bounded rerun, but label its result accurately and investigate concurrency/order-dependent repeat offenders before counting them as harmless flakes. **Acceptance:** a planted intermittent product race remains visible as a defect after a passing rerun, while an independently established test-environment failure can be quarantined under the existing expiry policy. This makes the under-3% enforcement metric more credible.

8. **Correct N8 and strengthen the existing cumulative-queue proof.** Retain merge limit 1 as a conservative operational setting, but remove the claim that it guarantees single-change test candidates or trivial rebase provenance. **Acceptance:** C's sandbox demonstrates the complete source-to-tested-candidate-to-landed mapping with multiple queued changes, failure, and reordering before D relies on it. This is a bounded correctness amendment, not a reason to abandon the native queue.
