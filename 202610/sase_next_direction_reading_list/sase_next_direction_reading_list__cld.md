# Recent Reading to Steer SASE's Next Moves

_Researcher: cld (one of five in swarm `research.3z`). Compiled 2026-10-07._

## Bottom Line

I looked for work published in roughly the last four months (June to October 2026) that
bears on what SASE is building now. Most of it lands on six threads SASE already has open:

1. **Replay.** Two of your annotations ask for it, and no bead tracks it yet. *Chronicle*
   (Microsoft, September 2026) gives a small, copyable design for "replay from step N."
   Each recorded crossing is addressed by (name, occurrence), and a stub/live plan
   chooses what re-runs. It fails loudly when the run diverges from the recording.
2. **Gates.** *Loopjacking* (September 2026) shows shipping agent frameworks executing a
   different operation from the one the human approved. SASE has just built sudo gates,
   plan approvals, and Telegram approval, so it is a ready-made audit checklist.
   *Oversight Has a Capacity* adds that escalating everything is *less* safe than
   escalating according to the reviewer's current load.
3. **Completion evidence after E4.** *Proof-or-Stop* (July 2026) is close to E4's
   fingerprint-bound receipt design. It adds three things E4 does not obviously have:
   - a command-set hash, so editing `just check` makes old receipts stale;
   - independence defined as a different host, session, and signing key;
   - an explicit degraded mode that is never upgraded.
4. **CI under agent load.** Anthropic's 2026-09-14 post reports CI jobs up 25× in six
   months. Its fix was stateless writers appending to a journal, plus a "jobs in equals
   jobs out" health metric. That pairs with *AgentCgroup*: memory, not CPU, caps how
   many agents a host can run. Both apply directly to the red Master Gate, the Apollo OOM
   research, and `sase tool` admission.
5. **Harnesses and size aliases.** Two October 2026 papers find that swapping the
   harness barely moves pass rates but changes cost by up to 3×. Model rankings can
   *reverse* across harnesses, and the same "high" effort label means different things
   to different CLIs. SASE's size aliases should become measured fit tables, not fixed
   native pairings.
6. **Peer systems.** Databricks' *Omnigent* (June 2026) is the nearest public analogue
   to SASE's adapter layer. Beads' published account of leaving SQLite+JSONL is close to
   an acceptance checklist for the bead-store epic (`sase-1h8`) now in progress.

Two cautions for the research swarm itself. Five providers are not five independent
voices: sixteen models from ten families produced about 1.7 effective voices. Adding
models to a pool usually *lowered* the score, so synthesis should compare claim by
claim, not count votes.

The ranked list is at the end. Every item there was checked against its primary source,
and none duplicates your finished reads or the three earlier SASE reading lists (Goals ×
2, memory and instruction files).

## How I Chose

**Inputs.** I started from four things:
- the reading-history report (`202610/sase_related_reading_history.md`);
- the ranked lists of the three earlier reading-list reports in this repo;
- SASE's last ~4 weeks of commits;
- its open and recently closed plan beads.

**Web search.** I ran about 30 searches across eleven themes: parallel orchestration,
replay, completion evidence, human oversight, host scheduling, CI, harness design,
multi-model ensembles, code maintainability, skills and memory evolution, and peer
systems.

**Verification.** Every candidate in the ranked list was read on its primary page (the
arXiv abstract plus HTML full text, or the original blog post) by fetch agents told to
quote only verbatim text and to flag 404s and mismatches. The numbers below come from
that verbatim text. A few details came only from a tool-generated summary of an overlong
page; those are marked **[summary-derived]**.

**Exclusions:**
- Anything already in your reading history, or ranked in the Goals or memory reading
  lists, e.g. *The Log is the Agent*, *EA-Graph*, *Symphony*, *Harness engineering*,
  *Evaluating AGENTS.md*, *Steering Claude Code*.
- One paper withdrawn after submission (CodeRescue; see "Considered and Left Out").

**Library check.** All 40 candidates went through `bob ref find` in one batch. Only the
Hassan SASE paper is in your library, queued since 2025-11-28 in the legacy backlog.
Two "possible" title matches were different articles: *How We Use Claude* is not *How we
contain Claude*, and Andrew Ng's *Agentic Design Patterns* is not Willison's
*Agentic Engineering Patterns*.

## What SASE Is Working On Now

| Thread (evidence in repo) | Readings matched to it |
| --- | --- |
| Replay (your annotations on *The Log is the Agent* and Gas Town; no bead yet) | Chronicle; *Engineering Reliable Coding Agents* ch. 9–10; ESAA-Conversational |
| Verified completion: E4 receipts (`sase-1ah`, phases closed); finalizer repair hardening (`sase-1h9`); *Triage Annotates* | Proof-or-Stop; Correct Is Not Governed; Clean Scores, Buried Evidence; Complex Agents, Shallow Tests |
| Gates and sudo: typed sudo gates with terminal-handoff authentication (`sase-110`); crash-safe gate handoff (`sase-11t`); plan approval from the CLI (`sase-18i`); Telegram | Loopjacking; Oversight Has a Capacity; The Work Behind Delegation; Anthropic's containment post |
| CI and host capacity: Master Gate and Full CI repair (`sase-126`, `sase-1c1`); two-speed CI; `sase tool` inline-vs-monitor routing; hold admission; Apollo OOM research | Anthropic's CI post; AgentCgroup; HiveMind; Not All AI Agents Are Equal |
| Providers: Grok provider core (2026-10-05); Muse streaming; size aliases on an effort ladder; instruction bundles in shadow mode (E1/E2 closed) | Harness Engineering (eleven systems); Finding the Right Fit; What Does a Harness Buy?; Omnigent |
| Bead store: SQLite read model, freshness token, issues.jsonl off the commit path (`sase-1h8`, opened 2026-10-06) | Beads vs br; Restoring Beads Classic |
| Research swarms (5 providers plus a lead synthesis) | Mo' Models, Mo' Problems; Sixteen models, fewer than two voices |
| Many agents landing on one master: dispatch conflict-repair resume (today); a stream of "split into modules" refactors | AI Agent Pull Requests on GitHub (merge-conflict rates) |
| An almost entirely agent-written codebase: 500-line limit, `toobig` splits | Is Agent Code Less Maintainable Than Human Code? |

## Themes

### 1. Replay: Your Annotations Now Have a Design to Copy

Two annotations ask for this: "Support sase tool call replay?" and "Materialize steps in
workflow to enable replay starting at certain xprompt workflow steps?" Today, `sase bead
search replay` only finds the bead-store read-model work.

**[Chronicle](https://arxiv.org/abs/2609.20625)** (Chawla and Koul, Microsoft;
2026-09-17).

*How it works.*
- Developers mark *boundaries* (model calls, tool calls, routing decisions) with a
  one-line decorator.
- Each time a boundary runs, an immutable *envelope* records the input, the output, and
  drift metadata such as model version and sampling parameters.
- Envelopes are addressed by name and occurrence (`agent[1]`, `agent[2]`), not by global
  step number.
- A `ReplayPlan` stubs some crossings from the record and runs others live, e.g.
  `stub("agent", 1).live("place_order", 1).live("agent", 2)`.
- If a stubbed boundary is crossed more or fewer times than recorded, replay raises an
  error rather than passing silently.

*Results.*
- Recording cost a median 23 µs per crossing.
- Full replay showed 0 divergences over 20 repetitions.
- Cut-point tests killed 51 of the 82 mutants (62%) that change behaviour on the
  recorded input. Stubbing every boundary killed none.

*Admitted limits.*
- No streaming and no concurrent tool calls.
- A per-name count check cannot catch a reordering. The authors suggest, but have not
  shipped, an order-sensitive digest.

**[Engineering Reliable Coding Agents](https://arxiv.org/abs/2608.13867)** (Jarmak; a
314-page monograph, August 2026). Chapters 9–10 are the best general treatment of
replay I found:
- Re-execute only the portion that must change, starting from durable state before step
  N.
- Never overwrite: a replayed event names the event it supersedes and the replay that
  produced it.
- Treat transcripts as projections of the event log.
- Give each logical invocation one stable idempotency key, and fence out stale workers
  with an epoch number.
- If an earlier claim was never resolved, escalate. "It should never silently assume
  either success or failure."
- Test recovery by killing workers at five points around each external effect, with a
  naive restart-from-zero adapter as a negative control.

**[ESAA-Conversational](https://arxiv.org/abs/2606.23752)** (June 2026) is a small,
one-author system. It normalizes Codex, Claude, and Grok logs into one append-only event
file whose views are pure projections. Its future-work "cold replay" (rebuild every view
from a clean log and compare hashes) is a cheap correctness test for SASE's own
projections.

**What this suggests for SASE.** The pieces map cleanly:
- macro-workflow steps and `sase tool run` invocations are the boundaries;
- ToolRun records and transcripts are the envelopes and projections;
- host-owned completion already keeps commits out of agents' hands, so a replay turn can
  run with finalizers disabled.

A minimal first version would record each workflow step's envelope (inputs, output,
provider, model, effort, CLI version) and offer "re-run from step *k*, earlier steps
stubbed." Address steps by (step name, occurrence) and fail loudly on divergence.

### 2. Completion Evidence After E4

E4's phases are closed: the Rust receipt contract, receipts minted on both execution
paths, and completion gated on a covering receipt. The open questions now are:
- What exactly does a fingerprint cover?
- What counts as an *independent* witness?
- How do you stop an older verdict from hiding a newer failure?

**[Proof-or-Stop](https://arxiv.org/abs/2607.14890)** (Huang et al., July 2026,
48 pages) answers all three, with numbers.

*How evidence is bound.*
- `materialHash` is SHA-256 over the canonical `git ls-tree`, with lifecycle metadata
  excluded. Separate hashes cover the policy and the command set.
- A receipt's identity is ⟨cmd, args, cwd, exit, outputDigest⟩, signed with a local key.

*What counts as independent.* A different host, session, and signing key. If no second
host exists, the run is recorded as degraded, and "degraded ⇒ FullAssurance = false."

*Freshness rules.*
- A PASS from any signed run in the current round counts.
- An open FINDING requires the lane's *latest* run, because "Id-recency is therefore not
  itself a freshness predicate."
- A merge re-verifies the certificate against the exact commit using compare-and-swap.

*Results.*
- Shipped visible-pass/hidden-fail artifacts fell from 31/1800 to 2/1800, at 3.8× the
  tokens.
- 18 tamper classes were rejected with zero false accepts.
- The authors say the gain is concentrated in one trap task, and that a local-key trust
  model "does not defeat a compromised runner."

**[Correct Is Not Governed](https://arxiv.org/abs/2608.12761)** (August 2026) adds three
points:
- **Append-only receipts:** "a failed receipt remains in history; a successful retry
  creates a later receipt."
- **Dependency-scoped invalidation:** a policy change re-issued 3 tasks instead of
  rerunning 18.
- **A sobering negative result:** on independently written packets, its completeness
  contract had specificity 0.00, blocking all seven complete packets. "Determinism makes
  a rule reproducible; it does not make the rule valid." Measure the false-block rate
  before a gate becomes hard.

**[Clean Scores, Buried Evidence, and Confident Wrong](https://arxiv.org/abs/2609.15319)**
(September 2026) has two findings that bear on witnesses:
- 72% of wrong answers were stated at ≥80% confidence.
- Errors were correlated across labs (φ = 0.43, or 0.21 after rescoring). A second LLM's
  opinion is therefore a weak KNOWN witness; a host re-run on the same fingerprint, or
  flake history, is a stronger one.

Its line "a citation is a pointer the model asserts; a receipt is a pointer a third
party can verify against a frozen file" applies to research-swarm citations too.

**[Complex Agents, Shallow Tests](https://arxiv.org/abs/2610.04921)** (UIUC, Berkeley,
and Tsinghua; 2026-10-04) measured "LLM-dependent harness" code (code whose data or
control depends on model output) across ten open-source agents:
- 44% line coverage, 41% branch coverage, and a 33.6% mutation score;
- orchestration logic is the least tested.

SASE's equivalents are its final-declaration parser, receipt verifier, and triage-verdict
parser. Those deserve mutation testing, not just coverage.

### 3. Gates, Approvals, and the One Human

**[Loopjacking](https://arxiv.org/abs/2609.21081)** (Arun Kumar, 2026-09-17). An
approval is a security boundary only if the operation the human reviewed is the one that
runs. The paper shows three ways this failed in shipping products:
- **Agno AgentOS:** seven releases executed a substituted operation 5/5 times. The
  continuation path checked the call ID but never compared the arguments.
- **OpenClaw:** the approval view showed only `$0 "$1"` while the full argv ran.
- **LangGraph Agent Server:** in one in-memory configuration, a non-approver could
  update the pending thread.

The OpenAI Agents SDK, used as a negative control, rejected the tampering.

Its prescriptions are concrete:
- Render the complete canonical operation.
- Bind the decision to a hash of that descriptor and its scope.
- Allow each approval to be used once, across every channel.
- Make pending state unwritable by the agent.
- Add regression tests: mutate one field after approval, replay a spent approval, try
  the wrong scope.

For SASE this means auditing three things:
- that the sudo manifest binds argv, cwd, env, user, and a script hash;
- that a Telegram message which cannot show the whole command does not offer one-tap
  approve;
- that plan approvals bind to a hash of the plan file (relevant to `sase-18i`).

**[Oversight Has a Capacity](https://arxiv.org/abs/2606.08919)** (Turan, June 2026)
models a reviewer whose reliability decays as reviews pile up. In simulation, safety
peaks *below* 100% escalation:

| Reviewer capacity | Best escalation rate | Danger let through at that rate | At 100% escalation |
| --- | --- | --- | --- |
| 25 | 64% | 42% | 57% |
| 50 | 72% | 22% | 39% |

Under a flooding attack, a policy that escalates 88% of routine actions let the attack
through 40% of the time with 50 fillers. A load-aware 26% policy held at 0% until about
100 fillers.

Caveats: single-author labels, and simulation rather than a human study. The design
consequence for SASE is still clear: route gates by the human's current load. Push
high-risk gates to Telegram immediately, batch low-risk ones in the ACE inbox, and
rate-limit gates per agent.

**[The Work Behind Delegation](https://arxiv.org/abs/2609.24234)** (KAIST and CMU,
2026-09-21) studied 19 developers in think-aloud sessions plus 12,912 Reddit comments.
It splits supervision into seven stages: Plan, Monitor, Wait, Review, Teach, Manual Fix,
and Update Assets. In the coded quotes:
- Review (366) and Update Assets (230) dominate.
- Wait is when developers tend other agents.

This supports designing ACE around coming back from *Wait*, not around watching. It also
supports turning repeated identical gate answers into proposed rules or hooks.

**[How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude)**
(Anthropic, 2026-05-25) adds field data:
- Users approved about 93% of permission prompts.
- An OS sandbox cut prompts by 84%.
- In every incident, the standard isolation primitives held; Anthropic's own custom
  proxy was what failed.

### 4. Host Capacity and CI Under Agent Load

**[Agentic coding is straining CI](https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic)**
(Sachin Malhotra, Anthropic, 2026-09-14).

*The load.* Code per engineer is up 8×, Claude writes 80% of it, tests grew 10×, and CI
jobs rose 25× in six months.

*The bottleneck.* The test-impact service's listener was a single process, because
per-test history needed a single writer. Three patches each lasted less time than the
one before:
- doubling the cores lasted 70 days;
- per-package sharding lasted 29 days;
- daily restarts lasted under a day.

*The fix.* Stateless listener workers append to a journal, and a small consumer rolls it
into per-test history every few seconds. One engineer did it in three weeks.

*Its advice:*
- "always plan for the exponential";
- "ensure that the same number of CI jobs coming in equals the same going out";
- "Keep state out of the process from the start."

It also notes that agents push overnight and at weekends, which raises CI's baseline
load.

For SASE: the ToolRun store and `sase tool stats` are a natural listener, and jobs-in
versus jobs-out is a cheap health metric for admission. A "failing on master" list from
the full matrix, attached to fast-gate results, would tell agents which failures are not
theirs, the same idea as *Triage Annotates*.

**[AgentCgroup](https://arxiv.org/abs/2602.09345)** (Zheng et al.; v3 2026-07-22; blog
post updated 2026-07-31) instrumented Claude Code on 144 tasks:

| Finding | Value |
| --- | --- |
| Memory pattern | ~185 MB baseline plus tool bursts of 500 MB to 2+ GB lasting 1–2 s |
| `pytest` vs `git`, P95 memory spike | 518 MB vs 13.5 MB |
| Worst peak-to-average memory | 15.4× |
| CPU use at the concurrency limit memory imposes | below 36% |
| Correlation of output tokens with peak memory | −0.14 and +0.02 (no predictive value) |
| Tasks containing retry loops | 85–97% |

Bash use peaks in the late verify phase, so agents tend to hit the test suite at the
same time. The prototype controller gives each tool call its own child cgroup, using
`memory.high` to throttle, `memory.max` as the hard limit, and `cgroup.freeze`.

For SASE: run each `sase tool run` in its own memory-limited scope, so an OOM kills the
test, not the agent. Admit work based on memory pressure (PSI), not CPU slots.

**[HiveMind](https://arxiv.org/abs/2604.17111)** (April 2026) offers the matching
control-loop vocabulary:
- resizable admission (a condition variable, not a fixed semaphore);
- AIMD backpressure;
- a circuit breaker;
- centralized retry with jitter. In its ablation, disabling retry left 63.6% of agents
  failing.

**[Not All AI Agents Are Equal](https://arxiv.org/abs/2609.19947)** (Korea University and
Microsoft Research Asia, September 2026) warns against one CPU gate. Capping coding
tools at the core count *raised* coding latency 2.76× **[summary-derived]**.

### 5. Harnesses, Adapters, and Size Aliases

**[Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents](https://arxiv.org/abs/2609.00006)**
(Barbaste et al., Wavestone; 83 pages) studies the source code of eleven harnesses, pinned
to July 2026: Claude Code, Codex CLI, Gemini CLI, Mistral Vibe, OpenHands, Aider,
Mini-SWE-Agent, Hermes, Pi, OpenCode, and OpenClaw.

*Findings.*
- None imports a general agent framework, and none uses vector retrieval.
- SKILL.md skills ship in 9 of 11 harnesses, MCP in 8 of 11.
- ACP is now also used for *harness hosting*: OpenHands runs `claude-agent-acp`,
  `codex-acp`, or `gemini --acp` as interchangeable backends.
- Who writes and reviews persistent memory now distinguishes the systems.
- Codex adopted Claude Code's hook event names almost verbatim.

*Useful for SASE.*
- Section 9.7 catalogs each CLI's instruction-file discovery rules, which is exactly
  what instruction bundles must target.
- It analyzes Databricks' **Omnigent** as a meta-harness: 23 adapters, five integration
  modes, and a conformance bench. The bench probes basic turns, tool calls, streaming,
  interrupts, model override, and policy denial.

**[Introducing Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)**
(Zaharia, Uhlenhuth, Zumar; 2026-06-13) is the product view:
- a sandboxed runner with a uniform API ("messages and files in, text streams and tool
  calls out");
- *stateful* policies enforced above the agent, e.g. after an npm install, `git push`
  needs approval;
- per-session spending budgets;
- an egress proxy that adds the GitHub token only to approved requests, so the agent
  never sees it;
- live sessions shared by URL;
- YAML agent definitions with a one-line harness swap.

**[Finding the Right Fit](https://arxiv.org/abs/2610.00917)** (NTU, 2026-10-01) tested 66
model–harness configurations.

*Rankings flip.* On Terminal-Bench 4, Claude minus GPT is +7.94 points in OpenHands but
−30.16 in Pi.

*Native is not best.* Codex never gave GPT its top score.

*Cost does not track score.* GPT scored 60.32% at $4.66 per task under Pi, and 52.38% at
$19.94 under DeepSeek's harness.

*The harness decides how failures land.* 180 of 192 failure responses were started by
the model, but whether the harness returned the failure in a usable form decided the
outcome:
- Pi has no shell timeout, so 34 runs hung.
- openJiuwen re-prompts after an output cap, and 100 runs resumed.
- In all 35 failed openJiuwen–Kimi Terminal-Bench 4 runs that ended with a final report,
  the report claimed every requirement had been verified.

*Effort labels.* The same "high" effort label "need not imply the same thinking budget
across harnesses."

**[What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433)**
(2026-10-03) holds the model fixed and varies the harness.

*Pass rate barely moves.* Swapping the harness changes 13% of task outcomes, the same as
rerunning; swapping the model changes 22%.

*Cost moves a lot.* Cost differs by up to 3×, mostly because of the fixed text each
harness sends on every call: 16,581 tokens for Claude Code against 829 for
mini-SWE-agent.

*The one real loss came from a missing continuation.* OpenCode does not re-prompt after
the 32k output cap.

*Effort settings are fragile.* Effort is passed three different ways across the
harnesses, and one endpoint silently ignores `xhigh`.

*Small samples cannot tell harnesses apart.* 45 tasks detect a 12.9-point gap only half
the time.

For SASE, these suggest four changes:
- Treat size aliases as a measured (alias × task type) → (provider, model, effort) table.
- Have adapters classify why a run ended and add continuation where a CLI lacks it.
- Verify per provider that the requested effort actually took effect.
- Track each provider's fixed per-call tokens on the instruction scoreboard.

### 6. Swarms and Parallel Landing

**[Mo' Models, Mo' Problems](https://arxiv.org/abs/2609.17306)** (NVIDIA; EMNLP 2026
REALM workshop) tested 23 open models.

*Correct answers overlap, errors do not.* Mantel r = 0.931 for correct answers, but only
0.384 for errors.

*Bigger pools usually do worse.* "More models nearly always decreases performance."
Deliberately chosen mixed pools often scored below their best member.

*One model sampled several times helped.* On HLE, judge@5 reached 36.5% against a
pass@1 of 29.4%.

Caveat: short-answer QA with open models and no tools.

**[Sixteen models, fewer than two voices](https://arxiv.org/abs/2608.00285)** (v2
2026-09-18). Sixteen models from ten families had the diversity of 1.69 independent
contributions. One model's own reruns gave 1.43. The most divergent model changed with
panel composition.

Together these say that five-way agreement in a swarm is not five confirmations. The
lead should check single-source claims against their sources rather than outvote them. If
diversity is the goal, give each researcher a different angle rather than relying on
provider differences.

**[AI Agent Pull Requests on GitHub](https://arxiv.org/abs/2607.04697)** (7 pages, July
2026) studied 33,596 agent PRs:
- Two open PRs from the same agent conflicted 19.8% of the time; PRs from different
  agents conflicted 41.7% of the time.
- By conflict type: content 57.6%, modify/delete 26.8%, add/add 15.1%. These are textual
  conflicts only, so they are a lower bound.

SASE's stream of "split X into focused modules" refactors produces exactly the
modify/delete and add/add shapes. Two cheap mitigations:
- run `git merge-tree --write-tree` pairwise across in-flight epics before landing;
- serialize file-splitting refactors.

### 7. An Agent-Built Codebase and Self-Improving Assets

**[Is Agent Code Less Maintainable Than Human Code?](https://arxiv.org/abs/2606.21804)**
(NYU and CMU; v2 2026-09-29). Agents built the next PR on top of either agent-written or
human-written code. Building on agent code lowered resolve rates by up to 13.1 points.

*Refactoring suffered most:*

| Task type | Average drop (points) |
| --- | --- |
| Refactoring | −8.21 |
| Feature work | −6.25 |
| Bug fixes | −4.05 |

*Size and complexity metrics did not predict the drop.* What did was an agent changing
input validation or error handling (odds ratio 1.83), and that drift persisted into the
next change 85.9% of the time.

SASE's `toobig` splits are agent refactors of agent code. A land-time check for changed
exception types, new validation gates, and silent fallbacks would target the actual
risk. The paper never tested file-length caps, so it neither supports nor refutes the
500-line rule.

**[Self-Evolving Coding Agents](https://arxiv.org/abs/2608.03392)** (survey; v4
2026-09-24) catalogs how agents learn from experience.
- **"Phantom Guardrails":** in 15 of 60 runs, an agent installed persistent rules for
  failures that did not exist.
- **Human judgment is rarely the signal:** it drives updates in only 5 of the 108
  methods annotated.

This backs SASE's human-gated memory writes, and suggests requiring each new rule to
cite the failure behind it.

**[Skill Issue](https://arxiv.org/abs/2609.12742)** (JetBrains, 2026-09-11) mined
realistic tasks by reverting merged PRs at a single frozen commit, then optimized
SKILL.md files against them.
- The gain was +4.9 points, not statistically significant (best p = 0.29), at a cost of
  $2,014 and 69 hours.
- A maintainer's verdict: generic padding belongs in a global skill.

### 8. Peers and the Namesake

**[Beads vs br](https://gascity.com/guide/beads-vs-br/)** (Gas City guide, reviewed
2026-08-07) and **[Restoring Beads Classic](https://www.dolthub.com/blog/2026-04-02-restoring-beads-classic/)**
(DoltHub, 2026-04-02). Note that the guide is published by the company behind Beads,
so it is not neutral.

*Why Beads left SQLite+JSONL-in-git.* The guide lists:
- stale-database overwrites;
- deleted issues coming back;
- JSONL merge problems;
- split-brain.

It also says JSONL "cannot safely reconcile deletes or pruning."

*Current Beads.* Claim leases and heartbeats are node-local and create no history.

*`br`, the Rust fork that keeps the classic design,* guards against:
- conflict markers;
- stale databases;
- overwriting a non-empty JSONL file from an empty database.

*Embedded Dolt's single-writer pattern.* Each operation opens, runs one transaction, and
closes. Writers queue with unbounded backoff, read-only calls roll back, and an
exclusive lock covers schema init. The DoltHub author tested multi-process concurrency
anyway, because "if an agent CAN do something, an agent WILL do it."

`sase-1h8` is building something very close to what `br` preserves: event streams in git
plus a Rust SQLite read model. That makes this list of failure modes a ready acceptance
checklist. SASE's events-not-snapshots design should handle deletes as tombstones, which
is exactly what Beads says JSONL snapshots could not.

**[Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216)**
(Hassan et al.; v3 2026-06-24) is the paper that named SASE and ACE. The abstract is
unchanged since v1, but v3 adds:
- **Appendix A:** worked examples of a BriefingScript, a Consultation Request Pack (CRP),
  and a Merge-Readiness Pack (MRP);
- **updated evidence:** the AIDev dataset of 932,791 agent PRs, and a 2026 Claude Code
  study with an 83.8% merge rate.

The vocabulary maps closely onto SASE:

| Hassan et al. | SASE counterpart |
| --- | --- |
| BriefingScript | plan beads and plan files |
| LoopScript | macro workflows |
| MentorScript | memory and skills |
| CRP | gates and questions |
| MRP | final declaration plus receipts |
| VCR (the human's recorded resolution) | gate resolutions |

The MRP's five criteria are a good template for what E4's successors should prove:
1. functional completeness;
2. sound verification;
3. SE hygiene;
4. clear rationale;
5. full auditability.

## Ideas These Readings Point To

| # | Idea | Source | SASE area |
| --- | --- | --- | --- |
| 1 | Record per-step envelopes for macro workflows and `sase tool run`; add "re-run from step *k*" with earlier steps stubbed, addressed by (name, occurrence), failing loudly on divergence | Chronicle; Jarmak ch. 9–10 | Replay (new) |
| 2 | Add a `just check` recipe digest (command-set hash) to receipt fingerprints; define a KNOWN witness as a different host or session; make degraded mode explicit and never upgraded | Proof-or-Stop; Clean Scores | E4 successors; *Triage Annotates* |
| 3 | Bind every gate to a canonical-operation hash; single-use across Telegram and ACE; no one-tap approve when the full command can't be shown; post-approval mutation tests | Loopjacking | `sase-110`, `sase-11t`, `sase-18i` |
| 4 | Load-aware gate routing: measure the human's queue; batch low-risk gates in ACE; rate-limit gates per agent | Oversight Has a Capacity; The Work Behind Delegation | Notifications, Telegram |
| 5 | Run each `sase tool run` in its own memory-limited cgroup or systemd scope; admit on memory PSI; watch retry loops | AgentCgroup; HiveMind | `sase tool` admission; Apollo OOMs |
| 6 | A jobs-in versus jobs-out metric for ToolRuns and CI; test selection from ToolRun history for the fast gate; a "known failing on master" list on fast-gate results | Anthropic CI post | `sase-126`, `sase-1c1`, two-speed CI |
| 7 | An adapter conformance bench (basic turn, tools, streaming, interrupt, model override, policy denial, end-reason classification, effort-took-effect probe) | Harness Engineering; What Does a Harness Buy?; Finding the Right Fit | *Adapters Normalize Harnesses*; Grok and Muse |
| 8 | Size aliases as measured fit tables; never change defaults on small samples | Finding the Right Fit; What Does a Harness Buy? | *Size Aliases Descend The Effort Ladder* |
| 9 | Swarm synthesis by claim, not by vote; measure diversity (e.g., Vendi Score) across the five reports; assign distinct angles | Mo' Models; Sixteen models | Research swarms |
| 10 | Pairwise `git merge-tree` across in-flight epics; serialize split-into-modules refactors | AI Agent PRs on GitHub | Finalizers, dispatch |
| 11 | Land-time "contract drift" check on agent diffs (exception types, validation gates, silent fallbacks) | Is Agent Code Less Maintainable? | `toobig` splits, land agents |
| 12 | Use the Beads failure list (resurrected deletes, stale-database overwrite, empty-overwrites-non-empty, conflict markers) as `sase-1h8` acceptance tests | Beads vs br; Restoring Beads Classic | Bead store |
| 13 | Mutation-test the declaration, receipt, and triage parsers | Complex Agents, Shallow Tests | Finalizers |

## Considered and Left Out

- **CodeRescue** (arXiv 2607.19338), on cost-aware recovery routing: withdrawn on
  2026-07-30 at ByteDance's request. The v1 idea (a learned router choosing between
  reflect, replan, and escalate) is relevant to size aliases, but don't cite a withdrawn
  paper.
- **Cursor, "Scaling long-running autonomous coding"** (January 2026): out of window and
  widely covered. Its planner/worker/judge hierarchy is already visible in Gas Town and
  Symphony, which you have read.
- **Deterministic Replay for AI Agent Systems** (arXiv 2607.16200, the agrepl CLI): only
  the abstract was readable (HTML 404, PDF unreadable). The idea of capturing traffic at
  the transport layer and replaying with no network access is noted under Theme 1.
- **Attention-bottleneck essays** (Zack Proser; Kevin Riedl's *Focus Is the New
  Bottleneck*): same thesis as the oversight papers, with weaker evidence.
- **Gas City marketing pages:** the "Beads vs br" guide is the substantive one. For the
  record: Steve Yegge is listed as an advisor; the CEO is Chris Sells.
- **Simon Willison's *Agentic Engineering Patterns*:** a living guide begun in February
  2026, not a single article. It's worth bookmarking, but it would not move a specific
  SASE decision.

## Caveats

- **Reading depth.** I read papers through fetch agents, not cover to cover.
  - *Engineering Reliable Coding Agents:* only chapters 2, 5, and 8–10 plus parts of the
    introduction and chapter 11 were read.
  - *Harness Engineering:* its final recommendations section (§16) was truncated and not
    read.
  - *Sixteen models:* abstract only (HTML 404).
- **Dates that don't match their IDs.** Several arXiv IDs disagree with their listed
  submission dates, e.g. 2609.00006 submitted 2026-07-15, and 2608.12355 submitted
  2026-07-04. I report the dates arXiv shows.
- **Simulation and single-author evidence.** Oversight Has a Capacity is
  simulation-based with single-author labels. Loopjacking is one researcher's
  deliberately chosen sample, not a prevalence estimate. Proof-or-Stop's gains rest on
  one model family and are concentrated in one task.
- **Prior swarm reports.** I did not read this swarm's other reports. I did read the
  final ranked lists of earlier, completed swarms, to avoid repeating their picks.

## Ranked Reading List

Ranking criteria, in order:
1. how directly the reading bears on something SASE is building now or has queued;
2. whether it gives a design you can copy, not just a framing;
3. strength of evidence;
4. reading cost.

Pairs share a slot when the second item is a short companion.

**1. [Chronicle: Cut-Point Replay for Regression Testing of LLM Agents](https://arxiv.org/abs/2609.20625)**
Chawla and Koul, Microsoft; 2026-09-17; code at github.com/theagentplane/chronicle.
- **Why read it:** it is the concrete answer to the two replay annotations you've
  already written. Its (name, occurrence) addressing, stub/live replay plans, and
  fail-loudly divergence check are close to an API spec for "replay from macro workflow
  step *k*" and "replay a `sase tool run`." Its limitations section tells you what a
  SASE version must add: concurrent calls and an order-sensitive digest.
- **Read:** the design, the cut-point replay plans, and the limitations.

**2. [Loopjacking: Hijacking Human-in-the-Loop Approval](https://arxiv.org/abs/2609.21081)**
Arun Kumar; 2026-09-17; 17 pages.
- **Why read it:** SASE has just shipped typed sudo gates, Telegram approvals, and
  CLI plan approval. This paper shows approval binding failing in real frameworks, and
  gives a binding record (§6.1) and a regression-test list (§6.4) you can run against
  `sase-110`, `sase-11t`, and `sase-18i` before they harden. It is the most immediately
  actionable security read on this list.
- **Read:** the case studies, then §6: the binding record in §6.1 and the regression
  tests in §6.4.

**3. [Agentic coding is straining CI. Here's how we scaled test impact analysis at Anthropic](https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic)**
Sachin Malhotra, Anthropic; 2026-09-14; blog post.
- **Why read it:** this is the clearest account from a large, agent-heavy shop of what
  agent volume does to CI, and SASE's Master Gate and Full CI are red right now
  (`sase-126`, `sase-1c1`). Each patch bought less time than the last, and the answer
  was structural (stateless writers, a journal, jobs in = jobs out). That bears on
  ToolRun, `sase tool stats`, and the two-speed CI decision. It is a 10-minute read.

**4. [Proof-or-Stop: Don't Trust the Agent, Trust the Evidence](https://arxiv.org/abs/2607.14890)**
Huang et al.; 2026-07-16; 48 pages.
- **Why read it:** this is the paper closest to E4's fingerprint-bound receipts, built
  independently and with a tamper suite. Read it for what comes after E4:
  - command-set hashes;
  - signer and host independence with an explicit degraded mode;
  - freshness rules that keep an old PASS from hiding a new FINDING;
  - compare-and-swap re-verification at merge.

  These map directly onto *Receipts Prove Before They Skip*, *Triage Annotates*, and
  the finalizers.
- **Read:** the evidence model, the verifier's rejection codes, and the ablation.

**5. [Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents — A Source-Code Study of Eleven Systems](https://arxiv.org/abs/2609.00006)**,
with **[Introducing Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)**
as a companion.
Barbaste et al., Wavestone, July 2026, 83 pages; Zaharia et al., Databricks, 2026-06-13.
- **Why read it:** SASE drives five or more vendor CLIs through adapters and now
  compiles per-provider instruction bundles. This is the only source-level map of how
  those CLIs discover instructions (§9.7), load skills, name hooks, and govern memory, and
  how fast they are converging. Its analysis of Omnigent, plus Databricks' own post,
  shows the nearest peer architecture to SASE: stateful policies above the harness,
  credentials kept out of the agent by an egress proxy, and an adapter conformance
  bench.
- **Read:** §9.7, the memory-governance and ACP sections, the Omnigent analysis, and the
  Databricks post.

**6. [Oversight Has a Capacity: Calibrating Agent Guards to a Subjective, Fatiguing Human](https://arxiv.org/abs/2606.08919)**
Turan; 2026-06-08; 12 pages.
- **Why read it:** SASE has one human approving gates for dozens of agents. This short
  paper formalizes why "escalate everything" is less safe than load-aware escalation,
  and why gate floods are an attack. It gives you a vocabulary and a replayable
  evaluation (log risk scores against decisions) for tuning Telegram versus ACE-inbox
  routing.
- **Read:** the whole thing; it's short. Treat the numbers as simulation results.

**7. [Finding the Right Fit: Model–Harness Interactions across Agent Tasks](https://arxiv.org/abs/2610.00917)**,
with **[What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433)**
as a companion.
NTU, 2026-10-01; Liu and Han, 2026-10-03.
- **Why read it:** these two papers are about a week old and directly test SASE's *Size
  Aliases* and *Adapters Normalize Harnesses* decisions. Model rankings flip across
  harnesses, native CLIs are not reliably best, and effort labels are not portable.
  The harness mainly sets the bill, through fixed per-call text, and through whether it
  re-prompts after an output cap. Both papers point to concrete adapter features:
  end-reason classification, continuation, and an effort-took-effect probe.
- **Read:** the results and failure-analysis sections of both.

**8. [AgentCgroup: Understanding and Controlling OS Resources of AI Agents](https://arxiv.org/abs/2602.09345)**
(and its [blog post](https://eunomia.dev/blog/2026/02/17/agentcgroup-what-happens-when-ai-coding-agents-meet-os-resources/)),
with **[HiveMind](https://arxiv.org/abs/2604.17111)** as a companion.
Zheng et al., v3 2026-07-22; Agyemang et al., April 2026.
- **Why read it:** this is the best measurement of what a Claude Code agent does to a
  host, and it says memory bursts, not CPU, cap concurrency. That bears on the Apollo OOM
  wipeouts and on `sase tool` admission: per-tool-call cgroups, admission on memory
  pressure, and retry-loop detection. HiveMind supplies the control-loop pieces
  (resizable admission, AIMD, circuit breaker, centralized retry).
- **Read:** the AgentCgroup blog post first, then the paper's characterization section;
  skim HiveMind's five scheduling primitives.

**9. [The Work Behind Delegation: A Framework for Supervising AI Coding Agents](https://arxiv.org/abs/2609.24234)**
Park et al., KAIST and CMU; 2026-09-21.
- **Why read it:** it is the best empirical model of what supervising coding agents
  actually involves. Most time is spent *away* (Wait), and Update Assets is the
  second-largest activity. That speaks directly to ACE's design (built for returning,
  not watching) and to turning repeated gate answers into memory, hooks, or skills.
- **Read:** the seven-stage model and the strategies section.

**10. [Engineering Reliable Coding Agents: Evaluating and Operating the System Around the Model](https://arxiv.org/abs/2608.13867)**,
chapters 9–10 only.
Jarmak; August 2026; 314 pages overall.
- **Why read it:** if you build replay (item 1), these chapters are the operational
  half:
  - branch-on-replay and never overwrite;
  - idempotency keys per logical invocation;
  - fencing stale workers;
  - escalating unresolved claims;
  - kill-point fault injection.

  The same material applies to crash-safe finalizers (`sase-1h9`, `sase-11t`).
- **Read:** chapters 9–10, and dip into the practice catalog as needed.

**11. [Mo' Models, Mo' Problems: How to best select model pools when designing Multi-Agent Systems](https://arxiv.org/abs/2609.17306)**,
with **[Sixteen models, fewer than two voices](https://arxiv.org/abs/2608.00285)** as a
companion.
NVIDIA, EMNLP 2026 REALM workshop; Vega-Barbas et al., v2 2026-09-18.
- **Why read it:** SASE runs every research question through five providers and a lead
  synthesis. These two papers test that shape's assumptions: mixed pools usually score
  below their best member, errors are what decorrelate, and sixteen models give about
  1.7 voices. Expect design changes to the swarm: synthesis by claim, distinct angles,
  and a check that synthesis beats the best single report.
- **Read:** the results of the first; the abstract of the second.

**12. [Beads vs br](https://gascity.com/guide/beads-vs-br/)** and
**[Restoring Beads Classic](https://www.dolthub.com/blog/2026-04-02-restoring-beads-classic/)**.
Gas City guide, reviewed 2026-08-07; DoltHub, 2026-04-02.
- **Why read it:** `sase-1h8` (opened 2026-10-06) is rebuilding the bead store around
  git event streams and a Rust SQLite read model, the design `br` preserves and Beads
  abandoned. These two short pieces list the exact failure modes Beads hit, plus the
  guards and single-writer pattern that answer them. Treat them as an acceptance
  checklist. The guide is vendor-written, so read it as a field report, not a neutral
  comparison.

**13. [Is Agent Code Less Maintainable Than Human Code?](https://arxiv.org/abs/2606.21804)**
Patel, Hou, et al., NYU and CMU; v2 2026-09-29.
- **Why read it:** SASE is almost entirely agent-written and refactors itself
  constantly. This is the best controlled evidence on how agent code burdens the next
  agent: refactoring is hit hardest, and the cause is contract drift in validation and
  error handling, not size or complexity. It suggests a specific land-time check, and
  a more honest framing of what the 500-line rule does and does not buy.
- **Read:** the CodeThread setup, results, and regression analysis.

**14. [AI Agent Pull Requests on GitHub: Frequency, Structure, and Merge Conflict Rates](https://arxiv.org/abs/2607.04697)**
Xu, Subramanian, Karthik; July 2026; 7 pages.
- **Why read it:** this short paper quantifies the conflict risk of many agents landing
  in parallel. Different agents conflict about twice as often as one agent with itself,
  and about 42% of conflicts are structural (modify/delete, add/add). That is exactly
  the shape SASE's split-into-modules refactors produce, and today's dispatch
  conflict-repair work shows it is live. The `git merge-tree` method is directly
  reusable.

**15. [Agentic Software Engineering: Foundational Pillars and a Research Roadmap, v3](https://arxiv.org/abs/2509.06216)**
Hassan et al.; v3 2026-06-24. _Already in your library (queued since 2025-11-28, legacy
backlog)._
- **Why read it:** it is the paper SASE is named after, and v3 adds Appendix A: worked
  BriefingScript, CRP, and MRP examples. The MRP's five evidence criteria are a ready
  rubric for what SASE's final declaration plus receipts should eventually prove. The
  ACE inbox concept is a useful foil for ACE as built. If you read it before v3, skim
  Appendix A and §8.3 only.

### Next Tier (Worth a Skim if a Topic Becomes Active)

- **[Correct Is Not Governed](https://arxiv.org/abs/2608.12761):** append-only receipts,
  dependency-scoped invalidation, and a negative result on gate specificity. Read
  before hardening any new completion gate.
- **[Clean Scores, Buried Evidence, and Confident Wrong](https://arxiv.org/abs/2609.15319):**
  confident wrong answers, and errors correlated across labs. Relevant to KNOWN
  witnesses and research-swarm citations.
- **[Complex Agents, Shallow Tests](https://arxiv.org/abs/2610.04921):** how poorly
  harness code that depends on model output is tested. Motivates mutation tests on the
  finalizer parsers.
- **[How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude):**
  93% of prompts approved, an 84% prompt reduction from the sandbox, and "distrust custom
  components." Context for the sudo and gate work.
- **[Self-Evolving Coding Agents](https://arxiv.org/abs/2608.03392)** and
  **[Skill Issue](https://arxiv.org/abs/2609.12742):** governance of memory and skill
  updates (Phantom Guardrails), and an honest attempt to measure SKILL.md optimization.
- **[ESAA-Conversational](https://arxiv.org/abs/2606.23752):** a cross-provider event log
  with projection-only views and a "cold replay" hash check.
- **[Beyond the Payload](https://arxiv.org/abs/2608.30686)** (EMNLP 2026): in repository
  poisoning, "Run-Tests" was the most successful and least-alerted task (45.5% attack
  success). Relevant if SASE agents run `just check` on untrusted repos.
- **[Beyond Compaction](https://arxiv.org/abs/2606.11213)** and
  **[Toward Reliable Context Compression](https://arxiv.org/abs/2608.06503):**
  deterministic eviction instead of summaries, and evidence that summary compaction
  destabilizes the next actions. Background for `/sase_handoff` versus provider
  compaction.
- **[Humans are Missing from AI Coding Agent Research](https://arxiv.org/abs/2608.12355):**
  more than half of passing patches behave differently from the reference fix. Proposes
  interaction metrics (time to decision, turns to recover intent) that ACE could log.
- **[Spec-Driven Development for Agentic Software Engineering](https://arxiv.org/abs/2609.00252):**
  separates a "technical harness" (tooling, which loses value as models improve) from a
  "methodological harness" (team practice, which gains value). Useful framing for which
  SASE investments age well.
- **[Agent Team Work Zone](https://arxiv.org/abs/2607.22917):** file-based per-agent
  checkpoints and a liveness-by-fresh-ping rule for long-lived Claude Code teams.
- **[Not All AI Agents Are Equal](https://arxiv.org/abs/2609.19947):** different agent
  tasks bottleneck on different resources. Argues against a single CPU admission gate.

## Proposed Library Commands (Not Run)

```bash
bob ref create https://arxiv.org/abs/2609.20625
bob ref create https://arxiv.org/abs/2609.21081
bob ref create https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic
bob ref create https://arxiv.org/abs/2607.14890
bob ref create https://arxiv.org/abs/2609.00006
bob ref create https://arxiv.org/abs/2606.08919
bob ref create https://arxiv.org/abs/2610.00917
```

Library check: 1 of 40 candidates already in your library (0 finished).
