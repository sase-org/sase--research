# Keeping SASE master green without making releases wait for every agent

Independent research by **cdx**, 2026-10-17 UTC.

**Recommendation:** adopt a protected `master`, host-created short-lived PRs, and a
GitHub merge queue that runs a bounded integration gate. Keep exhaustive CI off the
ordinary merge path, but require exhaustive verification and package smoke tests for
the **exact revision and distribution files being released**. Repair the existing red
baseline before enforcing normal green-only admission. Do not make a custom SASE merge
queue or permanent acceptance of known failures the first implementation.

PRs are not mathematically necessary for safe integration. They are the best default
here because GitHub already supplies enforcement, candidate testing, queue persistence,
and a usable audit interface. Mandatory human approval of every agent change is a
separate choice; I would not introduce that bottleneck for routine changes.

## Scope and evidence

I read the requested [Gas Town comparison](gastown_vs_sase_lessons_to_borrow/gastown_vs_sase_lessons_to_borrow.md)
through `sase artifact read`. I did not consult any other report, transcript, or findings
from this research swarm. Gas Town-specific implementation claims below are attributed
to that shared input, not presented as a new audit of Gas Town.

I independently inspected:

- SASE checkout `134d3bcf5a60d3355ad50fce1e99c94c75614521`, including CI, release,
  finalizer, and Git commit code.
- Linked `sase-github` checkout `8712c153aa969eef55bccbabe2e0e94a50764a68`.
- Linked `chezmoi` checkout `f870d35f8afd79aa4a6af0580d9cf00e572b218a`, specifically
  the configured `ci_watch` policy. I did not inspect its external script implementation
  or prove that the deployed machine has exactly this configuration.
- Live GitHub repository settings, workflow runs, job conclusions, releases, and open
  PR metadata around 01:45–01:57 UTC on October 17. These are snapshots, not continuous
  monitoring or a controlled benchmark.
- Official GitHub and PyPA documentation. URLs appear alongside relevant claims.
- Audited SASE decisions `ci-two-speed-split`, `check-full-is-explicit`,
  `host-owned-completion`, and `receipts-prove-before-they-skip`, plus the completion
  and evidence glossary terms.

No repository settings or implementation files were changed. This report is decision
research, not an executed migration or a verified fix for the observed CI failures.

## What is actually wrong today

### The fast gate detects failures after admission

The live repository is public and organization-owned. GitHub returned an empty ruleset
list and `404 Branch not protected` for master protection. Auto-merge is disabled;
merge commits are enabled; squash and rebase merges are disabled.

The current `Master Gate` runs on `push` to `master` and manual dispatch. It builds the
pinned Rust core, checks docs and lint/package validation, and runs eight shards of the
whole non-visual fast suite. Its SHA-specific concurrency avoids canceling one master
commit's evidence when a newer commit arrives. This is useful detection, but it runs
**after master has advanced**. [Local source: Master Gate](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/.github/workflows/master-gate.yml).

The direct commit path commits, synchronizes with the default branch, then pushes. On a
push race it fetches, rebases, and retries; that retry loop does not run the integration
gate. An earlier successful check therefore does not establish that the newly combined
tree passes. Ordinary final declarations explicitly record absent receipt evidence as
`unverified`, without refusing completion. Prepared completion with receipts is a useful
specialized path, not a universal master admission policy.
[Git dispatch](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/src/sase/vcs_provider/plugins/_git_commit_dispatch.py),
[declaration provenance](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/src/sase/finalizers/declaration.py).

This is a mechanical gap, not something stronger agent instructions can reliably close.
A change can pass on base A, encounter concurrent change B, rebase cleanly, and still
break their combination. Clean Git merges establish textual compatibility, not behavior.

### Recent results show that repairing master has not made it stay green

I queried the newest 100 Master Gate runs and newest 30 Full CI runs on master:

| Workflow sample | Window, UTC | Success | Failure | In progress | Median elapsed, completed runs |
| --- | --- | ---: | ---: | ---: | ---: |
| Master Gate, 100 runs | Oct 14 08:42 through Oct 17 01:47 | 27 | 71 | 2 | 12.5 minutes |
| Full CI, 30 runs | Oct 14 20:42 through Oct 17 00:31 | 0 | 29 | 1 | 109.4 minutes |

Elapsed here is `updated_at - created_at`, including queue delay and possible API update
lag. It is not CPU time or a clean measurement of gate service time. Successful Master
Gate runs alone had a 12.4-minute median and a 21.8-minute nearest-rank-style p90
(the script selected sorted index `int(n * .9)`). October 16 contained 62 gate runs
for 62 distinct SHAs; local first-parent history also contained 62 commits that day.

For example, [Master Gate run 38990563833](https://github.com/sase-org/sase/actions/runs/38990563833)
failed lint and five test shards while docs and the core build passed.
[Full CI run 38980994819](https://github.com/sase-org/sase/actions/runs/38980994819)
failed visual checks and all three Python test jobs while lint and several other jobs
passed. This is not simply a missing status label.

These counts **do not prove 71 independent regressions**. One persistent defect can
redden many successive runs; flakes, environment failures, and timeouts need separate
classification. I did not reproduce these failures. The justified conclusion is that
the current gate signals are too persistently red to serve as routine release evidence.

### Release safety is a second, distinct problem

The release system already has useful components: Release Please, package metadata
validation, fresh-environment wheel installation, published Rust-core floor probes,
and a PyPI publishing job using OIDC permissions. This is an improvement task, not a
reason to replace the release stack.

However, three gaps matter:

1. **Recent exhaustive success is not exact-candidate success.** The checked-in chezmoi
   policy requires `Master Gate`, `Full CI`, and a six-hour heavy-result freshness
   bound for SASE. It also describes guarded merging of green release PRs. That is an
   operational policy outside `publish.yml`; freshness alone does not establish that
   all intervening changes were tested exhaustively.
2. **Release PR CI intentionally differs from ordinary CI.** `build-core.yml` skips
   the source-built Rust job for `release-please--branches--master`, propagating skips
   to dependent jobs. The release PR instead receives a valuable published-core-floor
   smoke and contract lane. Its green result is not a full test of the eventual
   integrated release tree.
3. **Publishing does not itself enforce exact full-CI evidence.** `publish.yml` builds
   with the workflow's default checkout rather than an explicitly resolved Release
   Please tag SHA. Its publish prerequisites are build/install checks, not a matching
   exhaustive CI run. Scheduled processing can run at a revision later than the release
   commit, and `publish_existing` can use master’s recorded version without proving
   that its bytes are the already-certified release. This is a source-selection risk
   visible in code; I did not reproduce a mispublished release.

Sources: [Publish workflow](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/.github/workflows/publish.yml),
[CI workflow](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/.github/workflows/ci.yml),
[Build Core](https://github.com/sase-org/sase/blob/134d3bcf5a60d3355ad50fce1e99c94c75614521/.github/workflows/build-core.yml).
The configuration evidence is `chezmoi@f870d35f`:
`home/dot_config/sase/sase_athena.yml`, `ci_watch` section.

The latest GitHub release returned was `v0.17.1`, dated August 29. PyPI also listed
0.17.1 distribution files uploaded August 29, while the open Release Please PR was
[#299, release 0.18.0](https://github.com/sase-org/sase/pull/299).
This supports the user's concern about release cadence, without proving CI is the only
cause. [PyPI project and release files](https://pypi.org/project/sase/).

## Adjustments to the requirements

I would explicitly change the proposed requirements as follows:

| Original aspiration | More precise requirement | Why |
| --- | --- | --- |
| Ensure master stays green | Every ordinary master update must pass a defined integration gate against the current base; detect and repair escapes promptly | Tests cannot guarantee absence of every defect or future external outage |
| Publish more often once master is green | Certify an immutable release candidate independently of the moving master tip | Otherwise continuous development can keep invalidating release readiness |
| Maybe use PR-only | Require one mechanically enforced admission path; choose automated PRs and a queue as its implementation | PR presence alone does not test interactions or prevent bypass |
| More discipline might mean more review | Separate mechanical checks from human review; require human attention for sensitive changes and exceptions | A lone maintainer should not become a click-per-agent throughput limit |
| Reuse existing green signals | Bind evidence to source revision, dependency versions, gate policy, and final artifact digests | A nearby or recent green SHA is not evidence about different bytes |
| Keep throughput unchanged | Measure completed safe integrations and release lead time, then size capacity | Cheap unchecked pushes are not an appropriate success baseline |

I would not require exhaustive CI before every master update. I would require it before
every public release. Ordinary agent verification remains `just check`; this research
does not authorize agents to run `just check-full` routinely.

Short-lived PRs also fit trunk-based development: they need not introduce a permanent
`develop` branch or weeks of feature-branch divergence. Aim for independently useful
changes that land within hours. [Short-lived feature branches](https://trunkbaseddevelopment.com/short-lived-feature-branches/).

## Critique of the Gas Town-inspired landing proposal

The shared report's strongest ideas are worth preserving: test the integrated result,
serialize admission against moving master, prove publication, and stop normal admission
when master breaks. Its suggested implementation needs qualification.

**A local lease is not a global admission boundary.** A machine-local lock cannot
serialize another machine, a human push, or an independent bot. A custom system needs
one authoritative writer and server-side enforcement. If master advances during a
candidate's verification, abandon that candidate or reconstruct and retest it. Never
rebase during push retry and retain the earlier verdict.

**`just check` cannot promise that Master Gate stays green.** It is a scoped local
verification lane, whereas CI intentionally runs the whole fast suite. Using the former
as the only landing gate preserves the known possibility of selector misses and
cross-change failures. Keep it for developer feedback; use the broader bounded gate
for admission. That respects the two-speed distinction without pretending the lanes
prove the same thing.

**A no-new-failures ratchet is a recovery tool, not the destination.** Comparing failures
against a baseline is meaningful only with equivalent test coverage, environments,
dependency revisions, and independently witnessed signatures. Fail-fast execution can
hide later failures. A broken test collector can yield fewer failures by running fewer
tests. A new bug can share an existing failure signature. A known failure cannot turn
an incomplete run into evidence of green behavior.

If an emergency ratchet is needed while repairing master, restrict it to repair work,
record the exact baseline and candidate, expire exceptions, and reject unknown or
incomplete evidence. Do not accept unchanged failure sets indefinitely. For the first
recovery, reducing concurrent changes and landing a small set of coordinated repairs
may be faster and clearer than building generalized failure-set arbitration.

**Publication proof is necessary but distinct from tests.** Confirm that the real
remote default branch contains the expected merge result before declaring integration
complete. Preserve submitted source-SHA provenance when squash or rebase changes
ancestry. The actual merge result and the artifact being released must remain traceable.

**Do not move a 100-minute gate into a serial queue.** The existing two-speed decision
already identifies capacity as the constraint. Native queuing changes ordering and
safety; it does not manufacture runners or erase flaky-test cost.

## Which approach should SASE choose?

| Approach | What it buys | Main limitation | Assessment |
| --- | --- | --- | --- |
| Current direct pushes plus post-push CI | Low admission latency, per-SHA diagnosis | Master advances before evidence | Insufficient |
| PR-only, weak/stale status requirements | Visibility and optional review | Independently green PRs can interact badly | Insufficient |
| Protected PRs with strict up-to-date checks | Validates against current base; relatively simple | Repeated base updates and reruns under concurrency | Good transitional fallback |
| Protected PRs with GitHub merge queue | Managed integration candidates, ordering, rejection and audit | CI/event migration; shared runner capacity | Recommended target |
| Protected direct pushes from one custom SASE lander | Can verify and promote an exact commit without PR ceremony | Must own durable queue, multi-host exclusion, retries, enforcement, recovery and UI | Viable alternative, higher maintenance |
| Separate release/stable branch only | Releases can use an older qualified revision | Leaves master unreliable; cherry-pick and drift burden | Release technique, not primary remedy |

GitHub supports required checks independently of PR requirements. Consequently,
PR-only is not logically necessary: a sole writer can test a candidate branch, then
advance protected master to the verified descendant without altering it. The challenge
is making every writer obey that protocol. GitHub's strict check mode requires an
up-to-date base; its loose mode permits incompatible changes to slip through after
other merges. [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

The native queue is available for public organization repositories, which matches
SASE's observed repository type. It tests the candidate together with master and
preceding queued changes. It requires `merge_group` workflow support. Its merge-size
settings do **not** by themselves combine CI builds into one cheap batch; budget the
actual generated candidates. [Managing a merge queue](https://docs.github.com/en/enterprise-cloud%40latest/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

I favor the native queue because SASE's differentiator is agent coordination, while
GitHub already implements this repository-admission mechanism. A custom implementation
would be reasonable for a demonstrated provider-neutral requirement or if a measured
native-queue trial cannot meet capacity needs. Neither justifies building it first.

## Proposed integration design

### 1. Preserve host ownership; change where completed work is published

An agent still submits its declaration. The host commits its work to a durable branch,
creates or updates the associated PR, and requests queue entry once eligible. An agent
turn does not remain alive waiting for GitHub. Host reconciliation observes later
outcomes and schedules repair only when needed.

Use one PR per coherent change, not necessarily one PR for every intermediate agent
turn. Dependent work can share an explicit integration branch or wait for the
prerequisite's actual merge. Avoid collecting unrelated work into giant PRs merely to
reduce CI counts.

Separate three facts in the host's data model and UI:

```text
agent finished -> change durably submitted -> change actually integrated
                                            |
                                            +-> rejected / needs repair
```

Dependent work that requires mainline availability must wait for the last state. Do not
reinterpret every existing “agent completed” event as “merged.” A durable PR is enough
to release the agent's workspace, but not enough to claim master contains its work.

There is a concrete compatibility issue: `sase-github`'s
`workspace/submit.py::_submit_via_pr_merge` calls `gh pr merge --merge --delete-branch`,
then treats exit zero as a merge and calls `finalize_submission`. The documented CLI
behavior for a queue can instead mean auto-merge enabled or PR added to the queue.
The host must observe `MERGED`, capture the merge commit, and verify default-branch
publication before final submission state or dependent completion. Use the expected PR
head SHA when requesting admission, and handle a head update as new work.
[Inspected plugin source](https://github.com/sase-org/sase-github/blob/8712c153aa969eef55bccbabe2e0e94a50764a68/src/sase_github/workspace/submit.py),
[`gh pr merge` semantics and head matching](https://cli.github.com/manual/gh_pr_merge).

Shared admission/completion state belongs in `sase_core` under SASE's existing backend
boundary. GitHub API adaptation belongs in `sase-github`; Python and the TUI should
consume those outcomes. This does not require moving GitHub's queue implementation
into SASE.

### 2. Add one unambiguous integration check

Refactor the current fast gate into reusable jobs shared by PR and merge-group callers.
Require one uniquely named aggregate check, for example `integration-ready`, with
explicit dependencies on core construction, lint/package checks, docs, and all fast
suite shards. Do not depend on generic `lint` names repeated across workflows.

Both event shapes must work:

```yaml
on:
  pull_request:
    branches: [master]
  merge_group:
    types: [checks_requested]
```

For a PR, test the combined PR/base checkout. For a merge group, test the synthetic
candidate SHA supplied by GitHub. Do not explicitly check out the original PR head in
the merge-group job. Preserve the pinned Rust source revision and record the Python,
Rust, dependency, and gate revisions used by the run.

The aggregate should run with `if: always()` and fail unless every expected prerequisite
actually succeeded. Missing, failed, canceled, timed-out, and unexpectedly skipped jobs
must not pass admission. Avoid workflow-level path filters for required checks. GitHub
can regard skipped jobs as successful, whereas an entirely filtered-out workflow can
leave required checks pending indefinitely.
[Required-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).

Apply the same contract to generated release and dependency PRs. The existing
release-branch skip must not accidentally satisfy the new aggregate. PR-only metadata
checks also need a deliberate queue policy: do not blindly mark `Conventional PR title`
required if it never reports on merge groups. Fold metadata validation into the queue
contract using the group's member PRs, or keep that separate check advisory initially.

Do not run today's entire heavy PR matrix on every agent PR after introducing the
queue. That would multiply the current load before integration even begins. Replace
ordinary PR CI with the reusable fast gate; keep heavy checks scheduled, explicitly
requested for appropriate investigation, and mandatory for release certification.

During rollout keep the existing master push gate as an independent audit. That costs
additional runs, so measure it. Removing duplicate post-merge execution later requires
an explicit evidence mapping and an updated consumer policy; do not attach a prior
check's success to a different SHA as a shortcut. This does not change SASE receipts
into execution-reuse authorization.

### 3. Enforce the route at GitHub

Target the literal `master` branch with a repository ruleset or protection rule:

- Require PRs and the integration check from the intended check-producing App.
- Require the merge queue once its event path has been exercised.
- Block force pushes and deletion; ordinary agents and automation receive no bypass.
- Keep a narrowly controlled, audited human recovery path outside normal agent access.
- Leave blanket human-review counts at zero initially; use deliberate review policy
  for workflows, credentials, admission policy, publishing and other sensitive changes.

Keep merge commits initially. The repository and plugin already use that method, and
it preserves existing commit/stitch provenance. Squashing can be considered separately
with explicit attribution and Release Please validation. Linear history is not a
requirement for green master.

Select required checks only after they have run, and validate effective enforcement
using an intentionally rejected candidate. Server rules close the ordinary bypasses;
a local hook or prompt instruction alone does not.

Use host-held GitHub App credentials for automated branch/PR operations where practical.
Keep publisher authority separate from test jobs. Current GitHub behavior for
`GITHUB_TOKEN`-created or updated PRs can require approval before their CI runs; App
installation tokens support automatic triggering. Smoke-test the real authentication
path instead of relying on older folklore about event recursion.
[Workflow triggering and tokens](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

The existing lint lane also consumes a sidecar bootstrap token. Before making it a
public required PR gate, decide how fork PRs obtain read-only validation inputs without
secret access. Do not solve that by executing fork code with privileged
`pull_request_target` credentials.
[GitHub's event security guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).

### 4. Size the queue from measurements

Start with one active candidate while verifying correctness, then consider two after
measuring runner occupancy and end-to-end queue delay. Keep each queue entry required
to pass; do not use a later passing group to conceal an earlier failing entry.
[Queue rule controls](https://docs.github.com/en/enterprise-cloud%40latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

A rough serial estimate illustrates the constraint. At the successful-run median of
12.4 minutes, 62 changes consume about **12.8 hours** of serialized gate time; 90 changes
consume about **18.6 hours**. This is elapsed-time arithmetic, not billed runner-hours:
each gate fans out over many jobs. A 12-hour burst of 62 changes arrives faster than a
single 4.8-changes/hour lane can serve. Failed prefix rebuilds and runner contention
make this worse.

Tune from p95/p99 observations; do not pick a queue timeout equal to a single job's
20-minute ceiling when there are sequential job dependencies and runner waits. A
conservative initial 60-minute queue check timeout is a proposed setting, not a measured
optimum. Reserve capacity for release certification so an active merge queue cannot
starve publishing.

Batching is a later optimization. First reduce repeated environment setup, preserve
correct cache keys, and eliminate unnecessary duplicate heavy runs. Increase queue
parallelism only when runner capacity supports it. Never silently weaken the gate to
make the queue dashboard look healthy.

## Proposed release design: qualify a revision, then publish its bytes

Keep Release Please for versions and release notes. Change the publication contract:

```text
release metadata merged through integration gate
  -> resolve immutable release SHA C
  -> exhaustive CI on C + build distributions from C
  -> test those distributions in clean installation environments
  -> publish those exact distributions with recorded digests
```

1. Resolve the release tag to its commit, verify its relationship to the intended
   release PR/default-branch history, and pass that immutable SHA to every relevant
   checkout. All version sources and the requested release version must agree.
2. Run exhaustive CI for C, including the supported Python matrix and visual/contract
   lanes. A recent green run for C's ancestor is insufficient. Pin C while master
   continues advancing; do not keep restarting qualification for the newest tip.
3. Build wheel and sdist once from C. Verify metadata, install the wheel outside the
   source tree, and also exercise an install/build from the sdist. Retain the existing
   public-command, Rust binding, and published-floor probes. Exercise supported
   platform combinations needed by the release support promise.
4. Test the **published** `sase-core-rs` dependency resolution, including the declared
   minimum and a normal resolution within its supported range. Source-based CI against
   `sase-core-revision.txt` is useful but cannot prove that PyPI supplies compatible
   bindings. Publish required core versions before qualifying SASE; a pending core PR
   is not sufficient.
5. Make the publish job depend on successful exact-candidate qualification and smoke
   jobs. Pass immutable build artifacts and checksums between jobs; do not rebuild at
   upload time. Keep Trusted Publishing/OIDC and the `pypi` environment.
6. Replace a broad `publish_existing` escape with an explicit version/tag retry that
   resolves and verifies the same C. For a partial-upload retry, compare already-uploaded
   file digests to the recorded build; `skip-existing: true` alone is not proof that
   the missing sdist and existing wheel came from the same source.

PyPA documents the build-artifact/upload separation and Trusted Publishing approach.
The current workflow already follows part of it; extend it with exact-revision
qualification rather than replacing it.
[PyPA publishing guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).
PyPI attestations establish publisher identity and artifact integrity, not that tests
passed; release eligibility remains SASE's responsibility.
[PyPI attestation scope](https://docs.pypi.org/attestations/publish/v1/).

If exhaustive qualification finds a product regression, hold publishing, identify the
responsible change, and prioritize repair or revert. If the failure is infrastructure,
keep the unsuccessful result visible and retry only under a bounded diagnosis policy.
A newly qualified candidate can replace C, but do not mutate C or its build artifacts.
A GitHub release/tag may exist before PyPI publication; expose that distinction rather
than reporting the GitHub release event as a successful package release.

This lets frequent safe releases coexist with continued development. After restoring
baseline health, begin with an automated daily opportunity to publish eligible changes,
with manual on-demand qualification for urgent fixes. Publish only when there are
changes and the candidate qualifies. Increase frequency from evidence; a PyPI release
per agent commit is not the objective.

## Migration order and acceptance criteria

### First: recover a usable baseline and protect release identity

Temporarily limit ordinary master landings while repairing the known failures. Group
failures by job/signature and distinguish product defects from tests, infrastructure,
and noise. Revert a recent cause when that is the shortest trustworthy route. Avoid
hundreds of concurrent repair pushes against a moving baseline.

Reach a genuinely passing fast gate and a passing exhaustive candidate. When repeated
runs are needed to establish flakiness, run them deliberately, not until one happens to
be green. Any quarantine needs a demonstrated flaky test, owner, expiry and visible
coverage reduction. A blanket “known red” exemption does not count as recovery.

In parallel, make release SHA selection and publication prerequisites explicit. This
improves release assurance even before PR migration is complete.

### Second: exercise admission before turning on its enforcement

Implement reusable fast CI, aggregation, host PR persistence and asynchronous merge
observation. Test ordinary PRs, release PRs, dependency PRs, conflicting changes, and a
pair of individually passing changes that fail together. Verify token/event behavior.
Migrate all ordinary direct-push writers before enabling protection so failed finalizers
do not strand completed work.

Strict protected PRs are an acceptable short transitional stage. When queue events work,
require the queue. The migration itself needs a coordinated cutover; simply clicking
“protect master” today would break the current default commit finalizer.

### Third: run the queue and certify releases

Keep the scheduled exhaustive lane, introduce exact-candidate release qualification,
and change `ci_watch` to consume these explicit states. The checked configuration's
six-hour freshness bound can remain a health signal, but it must not be the final
permission to upload unrelated source bytes.

The recommendation intentionally revisits the prior `ci-two-speed-split` rejection of
a GitHub merge queue. Its capacity warning remains valid. The changed proposal is a
bounded fast integration queue plus occasional exhaustive release certification,
replacing today's expensive ordinary PR matrix. This is a policy change to evaluate,
not a claim that the existing decision already mandates a queue. The continued red
samples justify reopening the choice; they do not prove the queue will meet throughput.

### Tests that establish the new contract

| Scenario | Required outcome |
| --- | --- |
| Failing candidate with no conflict | Master does not move |
| A and B pass separately but fail together | Combined candidate is rejected |
| Master/base or PR head changes after a pass | Previous evidence cannot admit changed contents |
| One shard fails; aggregate dependencies skip | Aggregate fails |
| Missing, canceled or timed-out check | No merge |
| Release PR uses its special CI path | Required coverage is explicit; skipped core jobs do not grant success |
| Queue request returns zero, PR is still open | State is queued, not integrated; dependencies remain blocked |
| Host restarts while a PR is queued | Durable work survives and state reconciles without duplicate PRs |
| Ordinary agent tries direct push | Server rejects it |
| Master advances while C is being qualified | Release still tests/builds/publishes C |
| Recent Full CI passes on a different SHA | Publish remains blocked |
| Published core floor lacks a binding or wheel | Candidate is rejected before upload |
| Partial PyPI retry has different file digests | Retry stops instead of silently mixing artifacts |

Suggested initial operating targets, to be tuned after a two-week pilot:

- Every ordinary master update has admission evidence; no unaudited bypasses.
- Zero published releases without matching revision and artifact qualification.
- Track master red minutes, new-regression escapes, flake rate, queue age, runner
  minutes per accepted change, and human interventions.
- Aim for p95 ready-to-merge latency below 45 minutes at the actual arrival rate;
  treat that as a starting objective, not a promised capacity result.
- On a confirmed new master regression, halt ordinary admissions and prioritize
  repair/revert, aiming to recover within an hour where feasible.
- Keep release qualification capacity available; target daily eligible releases after
  the initial recovery, rather than optimizing raw commit throughput.

## Recommended solution

**Yes, better merge discipline is a good idea, and protected master is worth adopting.
Use automated short-lived PRs and GitHub's native merge queue as the normal integration
path. Run the whole bounded fast gate on the integrated candidate; keep exhaustive CI
scheduled and require it for the exact release candidate.**

Do not make universal human approval, a custom distributed lander, or permanent
no-new-failures acceptance prerequisites. Preserve SASE's host-owned completion model,
fix its distinction between queued and merged, and make releases consume verified
immutable artifacts. Recover the current red baseline, prove the admission contract in
a small pilot, then enforce it. If the native queue demonstrably cannot meet measured
capacity needs, retain protected PRs while optimizing the fast gate before taking on a
custom integration service.
