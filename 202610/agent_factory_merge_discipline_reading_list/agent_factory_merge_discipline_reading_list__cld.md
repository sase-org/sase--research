# Merge discipline for an agent software factory: what the last year of writing says

> **Research query:** I've been thinking about the best way to handle merging for an agent
> software factory like sase. See `merge_queue_fenced_master_and_exact_sha_releases.md`
> in the research sidecar repo for context. Find recent (under one year old) articles
> and papers that will inspire me or point me in the right direction, and end with a
> ranked list of what to read.

**Window:** 2025-10-17 to 2026-10-17. Anything older is flagged as such.
**Researcher:** cld (one of four independent researchers in this swarm).

## Bottom line

1. **The last year's writing supports the plan's direction:** fence `master` with a
   queue, make the gate trustworthy before you enforce it, and publish exactly the SHA
   you tested. Two agent-heavy organizations recently chose that shape:
   - **Anthropic's Claude Code team** (Oct 15, 2026): "The merge queue re-runs every
     check against main with the change applied, so two PRs that pass separately can't
     combine into a broken main". They report about 30,000 changes a day.
   - **Uber** released SubmitQueue as open source in 2026. It comes with a post-land
     "Stovepipe" service that promotes a last-green ref.
2. **The strongest counter-argument comes from organizations far above sase's volume.**
   - Cursor (about 1,000 commits an hour) concluded "the ideal efficient system accepts
     some error rate, but a final 'green' branch is needed".
   - OpenAI's harness-engineering team runs "minimal blocking merge gates", because
     "corrections are cheap, and waiting is expensive".
   - Mitchell Hashimoto says merge queues become "completely untenable" at 10–1,000×
     human inflow.
   - At sase's measured 43 landings a day, the queue fits. Still, design the host so that
     **"the trunk is gate-green" and "this SHA is release-green" are two separate refs
     from day one.** Then a future 10× jump means relaxing the queue, not rebuilding the
     release path.
3. **Flakiness is still the binding constraint, and the new evidence makes it slightly
   worse than the plan assumes.**
   - Flaky failures cluster (OpenStack: across 649 projects, 55% had cross-project
     flakiness). A rerun is therefore not an independent second chance, so the residual
     false-red rate after one rerun is higher than p².
   - Agent-written tests are measurably flakier than human ones.
   - Rerunning the failed *job* succeeds far more often than rerunning the whole
     *workflow*.
   - **Together this argues for:** rerun the failed nodes once, in a fresh process;
     catch flaky tests when they are added; and never let an agent decide what gets
     quarantined.
4. **The agent-PR literature adds one thing the plan lacks: track what happens after a
   change lands.**
   - Merged agent PRs need follow-up fixes at 1.62× the odds of human PRs.
   - Each 10-point rise in a project's no-review rate goes with about 6% more agent
     maintenance burden.
   - Parallel agent PRs collide textually 20–42% of the time.
   - LLM conflict resolvers are right under 60% of the time.
   - Zero approvals is still right for sase, but pair it with per-agent revert and
     follow-up-fix metrics. Make every conflict repair go back through the queue.
5. **Four platform facts changed in the window, and each bears on sase:**
   - **GitHub stacked PRs went GA on 2026-10-06.** A stack lands through the merge queue
     as one merge group, which is a candidate shape for epic waves.
   - **GitHub immutable releases went GA on 2025-10-28.** A tag can be locked, with an
     attestation tying the tag, the commit SHA and the assets together.
   - **GitHub Actions caps reruns at 50 per workflow** (since 2026-04-10).
   - **PyPI rejects new files on releases older than 14 days** (since July 2026).

**Read first:** Tian Pan's *The Merge Queue Is the New Bottleneck*, Cursor's *Towards
self-driving codebases*, Anthropic's *How the Claude Code team does code review*, Uber's
SubmitQueue/Stovepipe design docs, and Huang & Lin's *On the Reruns of GitHub Actions
Workflows*. The full [ranked list](#ranked-reading-list) is at the end.

## Where the context report landed

The consolidated report (`research:202610/merge_queue_fenced_master_and_exact_sha_releases/merge_queue_fenced_master_and_exact_sha_releases.md`)
recommends four phases, in this order:

1. **Phase 0:** cheap GitHub fences, plus a `publish.yml` that builds and fully tests
   release-please's exact `sha`. Then ship 0.18.0.
2. **Phase 1:** make the gate trustworthy: one in-job rerun of failed nodes, an expiring
   quarantine, `.python-version`, and `visual-test` folded into the gate. Exit when false
   reds are under 3%.
3. **Phase 2:** pilot GitHub's native merge queue with merge commits, build concurrency
   2 and zero approvals. Add a deterministic landing watcher that proves the merge before
   any bead closes.
4. **Phase 3:** enforce the queue with an empty bypass list.

Three questions it left open are the ones recent reading speaks to most:

- **Will a queue survive agent-scale growth?**
- **How should reruns and quarantine really be designed?**
- **What should sase measure once landings are asynchronous?**

## What the last year says, by theme

### 1. The agent-scale merge-queue debate: fence, or tolerate and promote

**The "untenable" camp:**

- **Hashimoto, Pragmatic Engineer, 2026-02-25.** "Agents cause so much churn that merge
  queues become untenable, branches proliferate, and repos balloon." Quoted by Danjou:
  "every time you pull there's another chain… It's really just like a release problem."
- **Cursor, Wilson Lin, 2026-01-14 and 2026-02-05.**
  - Locks failed: "Agents would hold locks for too long, or forget to release them
    entirely".
  - Optimistic concurrency "reduced overhead but didn't eliminate confusion".
  - A dedicated integrator role "created more bottlenecks than it solved".
  - Their answer was to tolerate errors: requiring 100% correctness made "the whole
    system… grind to a halt". Instead, "the error rate remains small and constant… not
    exploding or deteriorating", with "a final 'green' branch… where an agent regularly
    takes snapshots and does a quick fixup pass before release".
  - The swarm peaked at about 1,000 commits an hour.
- **OpenAI, *Harness engineering*, 2026-02-11.** "The repository operates with minimal
  blocking merge gates… Test flakes are often addressed with follow-up runs rather than
  blocking progress indefinitely." The authors add the caveat themselves: "This would be
  irresponsible in a low-throughput environment."

**The "fence, but build the queue properly" camp:**

- **Julien Danjou, 2026-06-30** (Mergify CEO, so a vendor). Hashimoto is half right: the
  *naive* queue that serializes rebases breaks. The queue is still the one place where
  "main" is decided, so it must batch, speculate, bisect and partition, not disappear.
- **Tian Pan, 2026-07-02.** "A merge queue exists to enforce one invariant: `main` is
  always green." The post works through queue arithmetic at agent frequency:
  - a strictly ordered 30-minute merge-group CI "lands at most two PRs per hour";
  - one red test invalidates every speculative state behind it;
  - "Retry loops that were mildly wasteful at human frequency become a
    denial-of-service at agent frequency";
  - "Quarantine beats retries for flakes".

  It also cites a team whose iOS mainline was green only 52% of the time before it built
  flake management.
- **Anthropic's Claude Code team, 2026-10-15.** Changes landing per day in Anthropic's
  monorepo went from about 2,500 in May to more than 30,000 in September, and they still
  run a merge queue. Open AI-review findings block merge, and "revert and incident rates
  are the guardrail". (Primary page verified.)
- **Atlassian, 2026-04-29.** More than 70 repos and over 30,000 PRs go through their merge
  queues. CI failures caused by semantic merge issues fell from 7–10% to nearly zero.
  Jira lands 300+ merges a day at build concurrency 14.
- **Uber's SubmitQueue**, open-sourced in 2026 (repo history starts 2026-01-08; press
  coverage around August).
  - It is a Go service. Its RFCs cover speculation trees, a logit-linear "outcome
    scorer", Tango target-level conflict analysis, and queue pause/unpause.
  - Its sibling **Stovepipe** answers "at which commit is this thing green?" It records
    greenness as a degree, per project, and moves a **promotion ref** (e.g.
    `verified-main`) forward to each commit it establishes as green.

**What it means for sase.** These camps disagree less than they seem to. Cursor and
OpenAI both still keep a *green thing to release from*. They just stopped requiring the
working trunk to be it. Stovepipe makes that explicit as a promotion ref.

At 43 landings a day, the context report's simulation says the strict fence costs about
13 min at p50. That is cheap, so fence now. But build the release side around a
forward-only `release-green` ref (Stovepipe-style), not "tip of master", and record
greenness per lane per SHA. Then if volume reaches Cursor territory, the escape hatch is
a config change: let the queue tolerate more while releases keep reading the promotion
ref. This also makes the context report's tag-on-green *fallback* nearly free to keep
warm.

### 2. Flakiness is the queue's real enemy, and reruns are not independent

**Rerun evidence:**

- **Huang & Lin, *On the Reruns of GitHub Actions Workflows*, ACM TOSEM, Feb 2026.**
  Figures are from the authors' PDF as a helper read it; I confirmed the venue and date
  only through a citation.
  - Rerunning only the failed job turned a failure into a pass 73.6% of the time, against
    33.9% for rerunning the whole workflow.
  - Successful job reruns took about 1.3 attempts; successful workflow reruns took about
    11.6.
  - About 3.2 of the 3.7 years of rerun waiting time went on reruns that never changed
    the outcome.
- **Ge & Zhang, arXiv 2602.02307 (Feb 2026).** 3.2% of GitHub Actions builds are rerun,
  and 67.73% of those reruns show flaky behaviour. Detecting flakiness at the job level
  beats the previous best tool by up to 20.3% F1.
- **GitHub changelog, 2026-04-10.** Workflows are capped at 50 reruns, full or partial,
  because "some automations… attempt hundreds of retries".

**Why reruns are correlated:**

- **Xiao et al., arXiv 2602.09311 (OpenStack).** Across 649 projects, 1,535 tests were
  flaky in more than one project and 55% of projects were affected. The main causes were
  CI race conditions, inconsistent build configurations and dependency mismatches.
- **Parry et al. (EASE 2025, older than the window).** 75% of flaky tests belong to
  clusters that fail together.
- **Consequence:** a rerun on the same runner, minutes later, is not an independent
  draw.

**Deciding when to rerun:**

- **SCOUT, Zhu et al., arXiv 2603.23054 (TiDB).** A production framework that decides
  online whether to rerun or escalate, from 3,680 labeled failed runs, at 1.17 ms P95.
- **Its key warning for sase:** **a finite rerun budget biases your own "flaky" labels.**
  If you rerun only once, a flaky test that fails twice is labeled "real". Your flake
  list is then systematically incomplete, and repair turns get spent on phantom
  regressions.
- **Gültekin et al., arXiv 2607.09345.** Published code-based flaky-test detectors fall
  to a constant baseline once trained and tested on different projects. For end-to-end
  tests, code plus CI logs explained only 42% of root causes; 58% needed runtime
  evidence.

**What it means for sase:**

- Keep the context report's "rerun failed nodes once, inside the job" rule. Run the rerun
  in a fresh pytest process with a fresh Textual app and event loop, ideally on a
  different shard, to break correlation.
- Build the quarantine list only from runtime evidence: a pass on rerun at the same SHA,
  recorded per failure signature. Never use static guesses.
- Feed the `FLAKY:` annotations into a per-signature record. "Failed twice at the same
  SHA" should count as weak evidence, not proof of a real failure.
- Measure how often a rerun passes after a first failure, by signature. If reruns are
  strongly correlated, the simulation's "a flaked PR re-enters once" assumption is
  optimistic: 30% false reds will hurt more than modeled. That makes the Phase 1 exit
  criterion even more important.

### 3. Agents produce their own flakes and their own conflicts

**Flaky tests written by agents:**

- **Jhanglani et al., arXiv 2607.12068.** Covers 179,732 agent-written test files against
  24,941 human-written ones. The rate of tests at risk of flakiness is 0.41 for agents
  vs 0.30 for humans, driven by file I/O and nondeterministic logic.
- **Berndt et al., ICSE-SEIP 2026 (arXiv 2601.08998; secondhand).** LLM-generated tests
  were somewhat flakier. 63% of their flakes came from relying on unguaranteed ordering,
  and the models *copied* flakiness from existing tests in their prompt context.

**Collisions between parallel agents:**

- **Xu, Subramanian, Karthik, arXiv 2607.04697.**
  - 79.4% of agent PRs overlap in time with another agent PR.
  - Simulated merges conflict textually 41.7% of the time between different agents, vs
    19.8% for the same agent.
  - About 42% of conflicts are structural.
- **AgenticFlict, arXiv 2604.03551.** 27.67% of 107k merge-simulated agent PRs conflict.
- **CodeCRDT, arXiv 2510.18893.** CRDT coordination reached zero textual merge failures,
  yet still had 5–10% *semantic* conflicts. Removing textual conflicts doesn't remove the
  need for a test gate.

**Resolving conflicts:**

- **Merge-Bench, arXiv 2605.25890.** The best models resolve under 60% of real conflict
  hunks correctly.
- **Shen, arXiv 2607.27674.** An LLM judge accepted 4 of the 5 resolutions that failed a
  deterministic structural check.
- **Cursor, *Agent swarms and the new model economics*, 2026-07-20.** Worker agents
  resolving their own collisions "either overwrite the other change or abandon their
  own". A "neutral third-party agent" that resolves conflicts on behalf of all parties
  cut conflicts from more than 70,000 (old run, before it was paused) to fewer than a
  thousand (new run, over four hours).

**Coordinating by conversation:**

- **CooperBench, arXiv 2601.13295.** Two agents collaborating score about 30% lower than
  the same agents doing both tasks alone.
- **CAID, Geng & Neubig, arXiv 2603.21489.** Isolated worktrees plus test-verified merges
  improve on single agents by 25.6 points on PaperBench and 14.7 on Commit0.
- **CoAgent, arXiv 2606.15376.** Argues that both locks (2PL) and optimistic concurrency
  (OCC) fit agents badly:
  - locks block for minutes of inference;
  - OCC throws away minutes of work on every conflict.

  It fixes the serialization order up front and applies writes speculatively, which is
  conceptually a merge queue for agent state. It stays within 5% of serial correctness
  at a 1.4× speedup.

**What it means for sase:**

- **Catch flaky tests when they are added.** In the gate's PR-side job, run each test
  *added or modified* by the change k times (say 5), cheaply and only for those node
  IDs, before the change can enter the queue. It costs little and targets exactly where
  the literature says agent flakes come from.
- **Send conflict repairs back through the queue.** An ejected conflict goes to a repair
  turn. That turn's output must re-enter the queue, and no LLM verdict ever lands it.
- **Consider Cursor's neutral-resolver shape for that turn.** Start the repair from both
  sides' diffs and intents, not the original agent's context. Measure whether it beats
  "fork the original agent".
- **Keep sase's isolate-then-integrate model.** It is what CAID and CooperBench support.
  Don't build agent-to-agent negotiation into landing.

### 4. Review, risk tiers, and what zero approvals costs

**What happens after agent code merges:**

- **Takerngsaksiri, Duong, Barnett, arXiv 2609.26847 (Sep 2026).**
  - Merged agent PRs draw verified follow-up fixes at 1.62× the odds of human PRs in the
    same repos.
  - 69.6% of those fixes come from the same agent.
  - The fix-to-origin linking method (an LLM judge at κ=0.78) is reusable.
- **Xia & Miller, arXiv 2607.09902 (Jul 2026).** Across 182 repos, agent code needs more
  corrective maintenance. **Each +10 points of no-review rate goes with about +6% agent
  maintenance burden.**
- **Two survival studies disagree:**
  - Rahman & Shihab (arXiv 2601.16809) find agent lines are modified *less* often;
  - Popescu et al. (arXiv 2604.00917) find *more* churn.

  The lesson is to measure your own revert and fix rates rather than trust a published
  number.

**Why agent PRs fail to merge:**

- **Alam, Mondal, Roy, arXiv 2602.00164 (MSR 2026).** Covers 8,106 fix-related agent
  PRs. Unmerged fixes most often fail on failing tests, or because **another PR already
  fixed the same issue**.
- **Ehsani et al., arXiv 2601.15195 (MSR 2026).** Covers 33k agent PRs. Unmerged PRs are
  larger and more often fail CI. Duplicate PRs are a named rejection class.

**Tiering by risk:**

- **Meta RADAR, arXiv 2605.30208 (May 2026).**
  - AI-generated code raised lines per human-landed diff by 105.9% year over year.
  - Agent and bot diffs get *their own* risk thresholds.
  - RADAR-reviewed diffs have a third of the revert rate and a fiftieth of the
    production-incident rate of other diffs.
- **Mozilla, arXiv 2604.00222.** Risk-aware batching ran 32.4% fewer tests and cut
  worst-case time-to-culprit by 26.2%.

**Holding the line against the agents themselves:**

- **ImpossibleBench, arXiv 2510.20270.** Frontier models exploit tests that contradict
  the spec, and stronger models do it more.
- **Spotify Honk part 3 (Dec 2025).** Their LLM judge exists partly to catch agents
  "disabling flaky tests", and it vetoes about a quarter of sessions.
- **Ghaleb, arXiv 2601.17413.** Agents touch CI/CD config in 3.25% of their changes.

**What it means for sase:**

- **Keep zero approvals,** since self-approval deadlocks and attention doesn't scale.
  Add these to the landing-record digest:
  - **revert rate and follow-up-fix rate per agent and model**, which reuses the
    `SASE_AGENT` footers and Takerngsaksiri's linking idea;
  - **duplicate-landing detection:** two PRs claiming the same bead.
- **Protect the gate from the agents it gates.** Agents must not add quarantine entries
  or change workflow files on their own authority:
  - Quarantine additions come from the CI flake detector, with evidence.
  - Agent PRs that touch `.github/workflows/`, the quarantine list or required-check
    names should route to a `/sase_gate` instead of auto-landing.

  This is the agent-era version of "fences beat promises".
- **Later, consider risk tiers à la RADAR.** For example, docs and `toobig` splits get
  the standard gate, while sase-core pin moves or finalizer changes also require a
  blocking AI review check. A bot check doesn't hit the self-approval deadlock.

### 5. Platform facts that changed during the window

**Merge queue and PRs:**

- **Stacked PRs went GA on 2026-10-06** (preview 2026-07-30). "A stack now enters and
  lands through the merge queue as a single merge group." Stacks can be driven by agents
  through a `gh-stack` skill.
  - **For sase:** an epic's phases could be a stack, so phase N+1 builds on phase N
    *before* N lands and the whole wave lands atomically. That cuts the 13–30 min
    "wait for merge" cost per wave the context report flagged.
  - Spike it. Atomic landing also means one bad phase ejects the whole wave.
- **The 2026-04-23 merge-queue incident.**
  - GitHub's CTO update (2026-04-28) confirms squash groups with more than one PR
    "produced incorrect merge commits", affecting 658 repos and 2,092 PRs. Merge and
    rebase methods were unaffected.
  - The same post says agentic workflows "accelerated sharply" from late December 2025,
    and that GitHub is designing for "30X today's scale".
  - Trunk's analysis (2026-04-24) gives the principle: "CI passed, because the temp
    branch on its own was internally consistent… The thing engineers approved was not
    the thing that merged." This directly justifies the context report's tree-equality
    proof.
- **Actions rerun cap of 50** (2026-04-10). Any automated re-enqueue loop must count its
  own reruns.

**Releases and supply chain:**

- **Immutable releases went GA on 2025-10-28.**
  - Assets can't be added, changed or removed, and the tag can't be moved, deleted or
    reused.
  - Each release gets a Sigstore-format attestation covering the tag, the commit SHA and
    the assets, verifiable with `gh release verify`.
  - The recommended flow is draft → attach assets → publish. That makes the context
    report's "check release-please's `draft` option" spike more pressing: with
    immutability on, assets must be attached before publishing.
- **SLSA v1.2 Source Track** (2025-11-24) gives vocabulary for "only protected-trunk
  commits are releasable":
  - Source L2: immutable history, no force pushes, tags can't be moved;
  - Source L3: controls enforced continuously, with signed summaries;
  - L4's two-party review allows standing exceptions for trusted robots.

  Phase 0 and Phase 3 together roughly reach Source L2–L3.
- **PyPI:**
  - **Releases reject new files after 14 days** (2026-07-22). Publish every artifact in
    one atomic job, with no later backfills. The context report's "partial re-upload"
    escape hatch is therefore time-limited.
  - **The LiteLLM/Telnyx incident report** (2026-04-02) and **the Shai-Hulud post**
    (2025-11-26) both recommend Trusted Publishing, pinning actions to SHAs and using
    GitHub Environments. Restrict the environment to protected `v*` tags rather than
    adding a required reviewer, which would break an unattended 1–3 day cadence.
- **GitHub Actions 2026 security roadmap** (2026-03-26) announces dependency locks for
  actions and secrets scoped to a branch or environment. Scoped secrets would let PyPI
  credentials exist only for tag-triggered workflows on protected refs.

### 6. CI capacity under agent load grows faster than you plan for

- **Anthropic, *Agentic coding is straining CI*, 2026-09-14.**
  - CI job volume rose 25× in six months, and tests grew 10×; Claude authors 80% of the
    code.
  - Three patches to their test-impact service lasted 70 days, then 29 days, then less
    than a day.
  - "If a dependency starts flaking, then flaky reds start blocking merges."
- **Linear, 2026-09-21.**
  - They add about 2,000 tests a week, most written by agents, and the suite nearly
    quadrupled.
  - "A pull request could sit in the merge queue even after its tests had passed."
    Queue overhead outside CI is real.
  - They updated their agent skills so generated tests meet new performance limits.

**What it means for sase.** The context report showed capacity fits *today* at K=2. Both
posts say the curve is exponential once agents write tests. Two cheap moves follow:

- **Put the gate's runner-wait p90 and gate wall time on the weekly digest** with
  explicit trip-wires, which the context report already lists.
- **Teach sase's test-writing skills the gate's constraints**, as Linear did: no real
  sleeps, deterministic Textual pilots, timing budgets. Then fewer slow, flaky tests are
  born.

## Ideas worth stealing, mapped to the plan's phases

- **Phase 0**
  - **Forward-only `release-green` promotion ref:** advanced by a deterministic job to
    each SHA green on gate *and* full matrix *and* core floor. Release-please's release
    commit must be at or behind it. *Source:* Uber Stovepipe RFCs. *Cost:* S.
  - **Turn on immutable releases:** draft → assets → publish; verify the attestation in
    `publish`. *Source:* GitHub GA 2025-10-28. *Cost:* S.
  - **Upload every artifact in one job:** PyPI's 14-day file lock. *Source:* PyPI blog
    2026-07-22. *Cost:* S.
- **Phase 1**
  - **Rerun only the failed nodes, once, in a fresh process (and shard if possible).**
    Count reruns against GitHub's 50-rerun cap. *Source:* Huang & Lin; Xiao; Parry;
    GitHub changelog. *Cost:* S.
  - **Quarantine from runtime evidence only;** account for the bias a rerun budget puts
    on labels. *Source:* SCOUT; Gültekin. *Cost:* S.
  - **Catch flakes at birth:** run added or modified tests k× before enqueue. *Source:*
    Jhanglani; Berndt. *Cost:* S–M.
  - **Agents can't quarantine or edit the gate;** such PRs route to `/sase_gate`.
    *Source:* Spotify Honk; ImpossibleBench; Ghaleb. *Cost:* S.
  - **A flake-repair agent per quarantine entry,** escalating on expiry. *Source:*
    FlakyGuard (Uber, 47.6% repaired); Stripe Minions (flake → ticket → minion).
    *Cost:* M.
- **Phase 2**
  - **Repair conflicts with a neutral resolver** given both sides' context, then
    re-enqueue. Never land on an LLM verdict. *Source:* Cursor swarm economics;
    Merge-Bench; Shen. *Cost:* M.
  - **Spike epic waves as stacked PRs** landing as one merge group. *Source:* GitHub
    stacked PRs GA. *Cost:* M (spike).
  - **A host-side landing pause with two switches:** "reject new enqueues" and "freeze".
    Possibly reuse sase holds. *Source:* SubmitQueue queue-pause RFC. *Cost:* S.
- **Phase 3 and the digest**
  - **Per-agent revert and follow-up-fix rate, plus duplicate landings per bead.**
    *Source:* Takerngsaksiri; Xia & Miller; Alam; Anthropic's Claude Code team.
    *Cost:* M.
  - **Risk tiers:** a blocking AI review only for core and finalizer paths. *Source:*
    Meta RADAR; Anthropic's Claude Code team. *Cost:* M (later).
- **Later**
  - **Pre-flight test sampling** that is deterministic per agent and random across
    hosts, to cut host load while the queue does the full run. *Source:* Carlini's C
    compiler `--fast` (1% / 10% samples). *Cost:* S.

## Where the reading pushes back on the plan

- **The rerun model is probably optimistic.** The simulation treats a flaked PR's retry
  as independent. The clustering evidence says it isn't. Measure the conditional rerun
  pass rate before trusting the K=2 / 30%-flake row, and treat "under 3% false reds" as
  a hard precondition, not a target.
- **"Zero approvals" has a measured cost.** It isn't free (Xia & Miller). The plan
  answers "who approves" (no one) but not "how do we notice quality drift". Add the
  revert and follow-up-fix metrics before enforcement, so drift is visible.
- **Cursor and OpenAI show the fence is a scale-dependent choice.** At 1,000 commits an
  hour they gave up green-trunk-always. Nothing suggests sase is near that, but the
  promotion-ref design keeps the option open cheaply.
- **There is no academic evidence on GitHub's native queue under agent load.** I found no
  peer-reviewed study of merge-queue throughput driven by agent PRs. The quantitative
  work is the context report's own simulation, plus vendor and practitioner posts.

## Ranked reading list

Status labels come from `bob ref find`.

### Tier 1: read these first

1. **Tian Pan, "The Merge Queue Is the New Bottleneck"** (2026-07-02).
   https://tianpan.co/blog/2026-07-02-the-merge-queue-is-the-new-bottleneck
   - **Why:** the clearest one-sitting treatment of queue arithmetic at agent frequency:
     strict ordering caps throughput, one red test invalidates the speculative states
     behind it, retries become self-DoS, and quarantine beats retries. It maps one-to-one
     onto Phase 1 and Phase 2.
   - **Note:** the tail is members-only.
   - **Library:** not found.
2. **Wilson Lin (Cursor), "Towards self-driving codebases"** (2026-02-05).
   https://cursor.com/blog/self-driving-codebases
   - **Why:** the best-argued counter-position. Locks fail, integrators bottleneck, a
     small constant error rate is acceptable, and you release from a separate "green"
     snapshot branch.
   - **Pair with:** "Agent swarms and the new model economics" (2026-07-20,
     https://cursor.com/blog/agent-swarm-model-economics) for the neutral
     conflict-resolver result.
   - **Library:** not found.
3. **Addy Osmani, Morgan Westlee Lunt, Qing Wang (Anthropic), "How the Claude Code team
   does code review"** (2026-10-15).
   https://claude.dev/blog/solving-code-review-at-anthropic/
   - **Why:** a team at about 30,000 changes a day that kept the merge queue, made open
     AI-review findings blocking, and uses revert and incident rates as the guardrail.
     This is the closest public analogue to sase's direction.
   - **Library:** not found.
4. **Uber, SubmitQueue and its RFCs** (open-sourced 2026).
   - **Where to read:** run `sase repo open gh:uber/submitqueue`, then read
     `doc/rfc/stovepipe/workflow.md`, `doc/rfc/submitqueue/speculation.md`,
     `doc/rfc/submitqueue/outcome-scorer.md` and
     `doc/rfc/submitqueue/queue-pause-and-unpause.md`. Docs are at
     https://uber.github.io/submitqueue/.
   - **Why:** these are design documents, not marketing. Stovepipe's promotion ref,
     greenness as a degree per project, and its forward-only bookmark are the cleanest
     model I found for sase's gate-green vs release-green split and its landing-record
     state machine.
   - **Library:** not found.
5. **Jiangnan Huang & Bin Lin, "On the Reruns of GitHub Actions Workflows"** (ACM TOSEM,
   Feb 2026). Author PDF: https://binlin.info/downloads/Huang2026a.pdf
   - **Why:** the strongest evidence for how to design the Phase 1 rerun. Rerunning the
     failed job is far better than rerunning the workflow, and most rerun time is wasted.
   - **Pair with:** SCOUT (arXiv 2603.23054, https://arxiv.org/abs/2603.23054) for the
     rerun-or-escalate decision and the label bias a rerun budget introduces.
   - **Library:** not found (neither).

### Tier 2: read these next

6. **Julien Danjou, "Merge Queues Were Built for Humans. Agents Don't Wait."**
   (2026-06-30). https://julien.danjou.info/blog/merge-queues-built-for-humans/
   - **Why:** the direct rebuttal to Hashimoto, covering batching, speculation, bisection
     and partitioned queues, plus why flakes break bisection. It is a vendor's view; read
     it alongside the Hashimoto episode (Pragmatic Engineer, 2026-02-25,
     https://newsletter.pragmaticengineer.com/p/mitchell-hashimoto).
   - **Library:** not found (the Mergify copy only title-matched an unrelated note).
7. **Xia & Miller, "Do These Violent Delights Have Violent Ends? Measuring the Post-Merge
   Fate of Agentic Code"** (arXiv 2607.09902, Jul 2026).
   https://arxiv.org/abs/2607.09902
   - **Pair with:** Takerngsaksiri et al., "Who Finishes the Job?" (arXiv 2609.26847,
     Sep 2026, https://arxiv.org/abs/2609.26847).
   - **Why:** the evidence for what post-merge metrics sase should track, and what zero
     review costs.
   - **Library:** not found.
8. **Xu, Subramanian, Karthik, "AI Agent Pull Requests on GitHub: Frequency, Structure,
   and Merge Conflict Rates"** (arXiv 2607.04697, Jul 2026).
   https://arxiv.org/abs/2607.04697
   - **Why:** puts a number on "green alone, red together" for agents: 79% overlap, and
     42% textual conflicts across agents. Short (7 pages).
   - **Library:** not found.
9. **GitHub Changelog, "Stacked pull requests generally available"** (2026-10-06).
   https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available
   - **Why:** a stack lands through the queue as one merge group, a candidate shape for
     epic waves.
   - **Library:** not found.
10. **Phil Vendola (Trunk), "What Happens If a Merge Queue Builds on the Wrong Commit"**
    (2026-04-24).
    https://trunk.io/blog/what-happens-if-a-merge-queue-builds-on-the-wrong-commit
    - **With:** GitHub's "An update on GitHub availability" (2026-04-28,
      https://github.blog/2026-04-28-an-update-on-github-availability/).
    - **Why:** the failure mode the tree-equality proof exists to catch, explained well.
      GitHub's post also shows agentic load is reshaping the platform itself.
    - **Library:** not found.
11. **GitHub, "Immutable releases are now generally available"** (2025-10-28).
    https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/
    - **Plus:** SLSA v1.2 Source Track (2025-11-24,
      https://slsa.dev/blog/2025/11/announce-slsa-v1.2).
    - **Why:** platform support and vocabulary for exact-SHA releases.
    - **Library:** not found.
12. **Adams et al. (Meta), "Automating Low-Risk Code Review at Meta: RADAR, Risk
    Calibration, and Review Efficiency"** (arXiv 2605.30208, May 2026).
    https://arxiv.org/abs/2605.30208
    - **Why:** the leading example of tiering agent diffs by risk instead of gating them
      all the same way.
    - **Library:** not found.
13. **Lyu et al., "CoAgent: Concurrency Control for Multi-Agent Systems"** (arXiv
    2606.15376, Jun 2026). https://arxiv.org/abs/2606.15376
    - **Pair with:** CooperBench (arXiv 2601.13295, https://arxiv.org/abs/2601.13295).
    - **Why:** the theory for why locks and OCC both fit agents badly, and why isolation
      plus ordered integration wins. Useful for reasoning about the host's admission
      design.
    - **Library:** not found.

### Tier 3: skim, or keep for reference

14. **Sachin Malhotra (Anthropic), "Agentic coding is straining CI. Here's how we scaled
    test impact analysis at Anthropic"** (2026-09-14).
    https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic
    (localized copies are at, e.g.,
    https://claude.com/de/resources/articles/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic)
    - **With:** Linear's "AI coding has made CI a bottleneck, so we reworked ours to keep
      up" (2026-09-21, https://linear.app/now/ci-bottleneck-reworked).
    - **Why:** capacity curves to plan for.
    - **Library:** not found.
15. **Nicholas Carlini (Anthropic), "Building a C compiler with a team of parallel
    Claudes"** (2026-02-05). https://www.anthropic.com/engineering/building-c-compiler
    - **Why:** git-file task locks, frequent merge conflicts, CI added *after*
      regressions, and per-agent deterministic test sampling.
    - **Library:** not found.
16. **Jhanglani et al., "Beyond Test Presence: Assessing the Quality and Robustness of
    Agent-Generated Tests in Open-Source Projects"** (arXiv 2607.12068).
    https://arxiv.org/abs/2607.12068
    - **Pair with:** Gültekin et al., "How Far Are We from Detecting Flaky Tests?"
      (arXiv 2607.09345).
    - **Why:** the case for catching flaky tests at birth, from runtime evidence.
    - **Library:** not found.
17. **Ge & Zhang, "Understanding and Detecting Flaky Builds in GitHub Actions"** (arXiv
    2602.02307). https://arxiv.org/abs/2602.02307
    - **With:** Xiao et al., "Cross-Project Flakiness: A Case Study of the OpenStack
      Ecosystem" (arXiv 2602.09311).
    - **Library:** not found.
18. **Alistair Gray (Stripe), "Minions: Stripe's one-shot, end-to-end coding agents"**,
    Parts 1–2 (2026-02-09 and 2026-02-19).
    https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
    - **Why:** local lints in under 5 s on push, at most two CI rounds then hand back to
      a human, and flaky tests turned into tickets for minions.
    - **Library:** **already in your library (queued since 2026-10-11)**.
19. **Max Charas & Marc Bruggmann (Spotify), "Background Coding Agents: Predictable
    Results Through Strong Feedback Loops" (Part 3)** (2025-12-09).
    https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
    - **Why:** verifiers run before a PR exists, and a judge catches agents disabling
      flaky tests.
    - **Library:** **already in your library (queued, legacy backlog)**.
20. **Rajkumar Singh (Atlassian), "Inside Atlassian's Merge Queues: How we ship faster
    with fewer incidents"** (2026-04-29).
    https://www.atlassian.com/blog/bitbucket/merge-queues-how-we-ship-faster-with-fewer-incidents
    - **Why:** before-and-after numbers for a merge-queue rollout.
    - **Library:** not found.
21. **Alam, Mondal, Roy, "Why Are AI Agent Involved Pull Requests (Fix-Related) Remain
    Unmerged?"** (arXiv 2602.00164, MSR 2026). https://arxiv.org/abs/2602.00164
    - **Why:** duplicate fixes losing the race to another PR, which argues for bead-level
      claim and dedupe.
    - **Library:** not found.
22. **Li et al. (UT Austin and Uber), "FlakyGuard: Automatically Fixing Flaky Tests at
    Industry Scale"** (arXiv 2511.14002). https://arxiv.org/abs/2511.14002
    - **Why:** agents can burn down the quarantine list (47.6% repaired, 51.8% of fixes
      accepted).
    - **Library:** not found.
23. **Sayedsalehi, Rigby, Mierzwinski (Mozilla), "Risk-Aware Batch Testing for
    Performance Regression Detection"** (arXiv 2604.00222).
    https://arxiv.org/abs/2604.00222
    - **Why:** only once volume justifies batching.
    - **Library:** not found.
24. **PyPI blog, "Releases now reject new files after 14 days"** (2026-07-22).
    https://blog.pypi.org/posts/2026-07-22-releases-now-reject-new-files-after-14-days/
    - **With:** the LiteLLM/Telnyx incident report (2026-04-02).
    - **Library:** not found.
25. **Schesch & Ernst, "Merge-Bench: Resolve Merge Conflicts with Large Language
    Models"** (arXiv 2605.25890).
    - **With:** Shen, "Can Large Language Models Resolve Real Java Merge Conflicts?"
      (arXiv 2607.27674).
    - **Why:** the reason LLM conflict resolution must stay behind the gate.
    - **Library:** not found.

**Already read, worth a two-minute re-skim:**

- **OpenAI, "Harness engineering: leveraging Codex in an agent-first world"**
  (2026-02-11). **In your library, finished.** Its merge-philosophy paragraph ("minimal
  blocking merge gates… corrections are cheap, and waiting is expensive… irresponsible in
  a low-throughput environment") is the sharpest statement of the position this plan
  rejects at sase's scale.

**Queued, but already digested by earlier research:**

- **Steve Yegge, "Welcome to Gas Town"** (2026-01-01). **Already in your library (queued
  since 2026-02-11, legacy backlog).** The `gastown_vs_sase_lessons_to_borrow` research
  already extracts its Refinery merge-queue lessons, so it is not ranked here.

**Seen but not ranked:**

- **StrongDM's Software Factory** (2026-02-06) and Simon Willison's write-up
  (2026-02-07). Holdout scenarios and no human review; no merge or CI content.
- **Wang & Liu, "Software Engineering in the Agent Era"** (arXiv 2609.04630). A theory
  paper arguing verification and acceptance become the queues; no empirical content.
- **Graphite's Shopify merge-queue case study.** Vendor material, undated.
- **Uber, "CI at Scale: Lean, Green, and Fast"** (ICSE 2025, arXiv 2501.03440). Older
  than the window, but it is SubmitQueue's academic companion.
- **Jungwirth et al.** (ICSME 2025, arXiv 2508.08342). PR prioritization in merge
  pipelines; older than the window.

## Method, confidence, and limits

- **Context:** I read the consolidated context report through the research sidecar,
  opened with `sase repo open`. I did not read any other swarm member's output for this
  query.
- **Search:** web searches and four parallel helper sweeps:
  - CI and flaky-test papers;
  - agent-PR and multi-agent coordination papers;
  - primary industry posts;
  - release-engineering sources.
- **Verification:**
  - I re-fetched the primary pages for items 1, 2, 3, 9, 20 and the Cursor and Linear
    companions.
  - I re-checked ten arXiv abstract pages for titles, dates and numbers.
  - I opened `gh:uber/submitqueue` as an external repo to read its README, RFC index and
    Stovepipe workflow RFC.
- **Lower confidence:**
  - **Huang & Lin's figures.** The venue and date are confirmed only by a citation. A
    helper read the numbers from the author PDF; I could not re-extract them locally.
  - **The Berndt et al. numbers** are secondhand.
  - **The Hashimoto transcript quotes** come via Danjou's post.
  - **SubmitQueue's open-sourcing date** is approximate: repo history starts 2026-01-08
    and press coverage is around August 2026.
- **Not found:**
  - No peer-reviewed study of GitHub's native merge queue under agent load.
  - No authoritative writing on PyPI yank or rollback policy at agent cadence.
  - The "Merge Queue Is Your New Critical Path" post (rickpollick.com) could not be
    found on that blog.
- **Changed:** nothing in sase, its workflows or its memory. This is reading only.

Library check: 5 of 68 candidates already in your library (1 finished).
