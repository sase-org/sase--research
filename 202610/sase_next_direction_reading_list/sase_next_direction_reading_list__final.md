# Recent Reading to Steer SASE: Replay, Approvals, Parallel Landing, and Measured Harnesses

_Lead synthesis of swarm `research.3z` (cdx, cld, grk, mus, gem) plus independent lead
research. Compiled 2026-10-07._

## Bottom Line

Most of what the field published from June to early October 2026 falls on five threads
SASE already has open. For each, there is now at least one paper with a design you could
copy or a measurement that should change how you decide.

1. **Replay.** All five researchers found this thread, starting from your two
   annotations. *Chronicle* (Microsoft, 2026-09-17) is a small, copyable API for "re-run
   from step *k*, with earlier steps served from the record." *Ledger* (Hassan's group,
   2026-08-01) is the strongest evidence that a mechanically derived execution state
   helps coding agents. No bead tracks tool-call or workflow-step replay today; the only
   "replay" beads are the bead store's own event replay in `sase-1h8`.
2. **Approvals and receipts.** *Loopjacking* (2026-09-17) shows shipping frameworks
   running a different operation from the one the human approved. It applies directly to
   `sase-110` (sudo with terminal handoff), `sase-11t` (crash-safe gate handoff) and
   `sase-18i` (CLI plan approval). *Proof-or-Stop* is the closest outside design to E4
   (`sase-1ah`), and it adds the parts E4 does not obviously have yet.
3. **Parallel landing.** None of the five reports covered this one. Two independent
   papers on *Claim Plane* (July and August 2026), the *STALE* benchmark (EXPRESS '26) and
   *NP-Bench* (2026-10-05) all study agents that pass alone but break once merged. Their
   evidence favors declaring scope before writing, serializing overlap, and telling
   siblings about contract changes. It does not favor clever selective concurrency. That
   bears on today's dispatch conflict-repair work and on the stream of "split into
   modules" refactors.
4. **Harness measurement.** Two papers from the last week show that swapping the harness
   barely moves pass rates but changes cost by up to 3×. Model rankings can reverse
   across harnesses, and effort labels do not mean the same thing in every CLI. That
   argues for measuring size aliases, not hard-coding them, and for an adapter
   conformance bench.
5. **The human in ACE.** ACE work dominates recent commits (about 160 `feat(ace…)`
   commits since 2026-09-20). *ParallelPilot* (Microsoft Research, 2026-09-27) is a
   controlled study of a dashboard for supervising parallel agents. Read it with *The
   Work Behind Delegation* (KAIST/CMU).

If you read only three: **Chronicle**, **Ledger**, and **Loopjacking**. If you want the
paper SASE is named after, it is still queued in your library. Hassan et al. v3
(2026-06-24) added worked examples of every artifact it proposes (rank 5).

## How This Was Built

- **Inputs.** The five swarm reports; the reading-history report
  (`research:202610/sase_related_reading_history.md`); and the ranked lists of the three
  earlier reading lists (Goals round one, Goals round two, memory and instruction files),
  to avoid repeats. For SASE context: the last three weeks of commits, the docs on tools,
  architecture and development, and the epics the readings touch.
- **Lead research.** I searched for gaps in the five reports and found the
  parallel-landing cluster (Claim Plane ×2, STALE, NP-Bench), ParallelPilot and AgentGUI.
  I also checked the items only one researcher had reported, which included gem's
  Consort, ECT, MAGE and SWE-Router, and mus's Cognition follow-up.
- **Verification.** Fetch agents read the primary page for 30 candidates: the arXiv
  abstract plus HTML full text, or the original post. They quoted numbers verbatim and
  flagged mismatches. Targeted searches confirmed that ECT, MAGE, Consort, SWE-Router and
  Cognition's 2026 follow-up exist and checked their authorship. Several swarm claims
  needed correcting; see [Corrections](#corrections-to-the-swarm-reports).
- **Exclusions.** I left out anything you have finished and anything ranked in the three
  earlier lists. That dropped six of the swarm's picks (see
  [Considered and Left Out](#considered-and-left-out)). Started-but-unfinished items
  from your 2025 backlog are not presented as new.

## Where SASE Is Now, and What Bears on It

| Live thread (evidence) | Readings |
| --- | --- |
| Replay: two annotations, no bead; workflow launches already persist step state; ToolRuns are recorded before admission | Chronicle, Ledger, ESAA, Execution Lineage |
| Gates and approvals: `sase-110`, `sase-11t`, `sase-18i`, Telegram approvals | Loopjacking, CapLease, Oversight Has a Capacity |
| Verified completion: E4 `sase-1ah` landing; *Receipts Prove Before They Skip*; *Triage Annotates* | Proof-or-Stop, Evidence-Carrying Termination, Actions with Receipts, Reality Is the Final Verifier |
| Parallel landing: dispatch conflict repair and workflow resume (landed today); epics fanned out across workspaces; `toobig` splits | Claim Plane, STALE, NP-Bench, AI Agent PRs on GitHub |
| Providers: Grok provider core (10-05); instruction bundles shadow-rendered at the invoke boundary (10-06); *Size Aliases Descend The Effort Ladder* | What Does a Harness Buy?, Finding the Right Fit, Harness Engineering (eleven systems), Omnigent |
| ACE TUI: the dominant commit theme | ParallelPilot, The Work Behind Delegation, AgentGUI |
| CI and host capacity: `sase-126` and `sase-1c1` (Master Gate, Full CI); Apollo OOM research; `sase tool` admission and holds | Anthropic's CI post, AgentCgroup |
| Research swarms (this report) | Mo' Models, Mo' Problems; ArcticSwarm |
| Memory: *No Retrieval Mechanism Before Its Corpus* | VibeMemBench |
| A codebase almost entirely written by agents | Is Agent Code Less Maintainable?, SlopCodeBench |

## Themes

### 1. Replay: Separate Four Operations Before Building One

cdx's most useful contribution is a vocabulary that keeps "replay" from silently picking
up meanings SASE has deliberately refused:

| Operation | What it does | SASE today |
| --- | --- | --- |
| Inspect recorded output | Show evidence from a finished run | ToolRun output and transcripts already do this |
| Reconstruct control state | Restore ownership, settled outcomes, lineage | Monitors, `#fork`/`#resume`, and launch-journal replay cover parts of this |
| Replay observations in isolation | Feed recorded model/tool responses to reproduce a path | Missing; needs a capture boundary and a filesystem policy |
| Resume or selectively recompute | Do new work from step *k* or a changed artifact | Missing; needs dependency invalidation, fresh admission, and a side-effect policy |

*Chronicle* is the design for row 3, and its "live from the cut point" mode starts row 4:

- Developers mark boundaries (model calls, tool calls, routing).
- Each crossing records an immutable envelope, addressed by **(name, occurrence)**
  (`agent[1]`, `agent[2]`), not by global step number.
- A `ReplayPlan` chooses per crossing: `stub("agent", 1).live("place_order", 1)`.
- A stubbed boundary crossed more or fewer times than recorded makes replay raise, so it
  never passes silently.

Its own limits are what a SASE version must add: concurrent tool calls, streaming, and an
order-sensitive digest (a per-name count misses reorderings).

*Ledger* addresses something different: an agent forgetting which observations still
describe the repository. It derives *observed / modified / attempted* state from finished
steps, with no extra model calls, and uses it on two paths:

- **inform**: append a compact state view to the prompt;
- **govern**: reuse a still-valid result, or flag a redundant repeat.

The govern path suppresses repeated commands. That conflicts with *Receipts Prove Before
They Skip*, which never lets a receipt skip execution. So borrow the inform path and the
state representation first, and treat govern as a separate, measured question.

*ESAA* (Feb 2026) goes a step further than SASE's host-owned completion. Agents emit only
validated JSON intentions, a deterministic orchestrator applies every file write, and
`esaa verify` rebuilds state from the log and checks hashes. That "cold replay" check is a
cheap correctness test for any SASE projection. Whether SASE should host-own *every*
write, rather than only the land, is a real design fork, not a metaphor (grk).

### 2. Approvals Must Bind What Runs; Completion Must Bind What Was Proven

*Loopjacking* found three ways approval binding failed in shipping products:

- **Agno AgentOS:** seven releases executed a substituted operation 5/5 times. Its
  continuation path matched the call ID but never compared the arguments.
- **OpenClaw:** the approval view showed only `$0 "$1"` while the full argv ran.
- **LangGraph Agent Server:** under one custom auth policy, a non-approver could replace
  the pending call.

The OpenAI Agents SDK, the negative control, rejected the tampering. Two sections are
directly usable for SASE's gates:

- **§6.1, the canonical approval record:** every material argument, target, principal
  and scope, plus a digest of exactly what the human saw, a nonce, an expiry, and a
  consumption status.
- **§6.4, the regression suite:** unchanged A succeeds; denial has no effect; mutating a
  field after approval fails; the wrong scope fails; a consumed approval cannot be
  replayed.

*CapLease* (Aug 2026) covers what Loopjacking does not: crashes and retries. After an
uncertain outcome, agents re-proposed an equivalent action 39.8% of the time (58.0% after
a lost acknowledgement). Durable Issue–Prepare–Commit state prevented duplicates across
12,000 kill/restart schedules, but only with an idempotent destination. Any SASE replay
or automatic-recovery feature needs this property first.

On completion evidence, *Proof-or-Stop* (48 pages) is the closest outside match to E4:

- **Binding:** a `materialHash` over the canonical `git ls-tree`, plus separate **policy
  and command-set hashes**, so editing `just check` makes old receipts stale.
- **Independence:** verdicts differ in host, session, and signing key. Without a second
  host the run is marked degraded, and "degraded ⇒ FullAssurance = false."
- **Result:** hidden failures that got through fell from 31 of 1,800 injected cells
  under a compute-budgeted naive loop to 2 of 1,800 under the gated loop.
- **Limits:** one model family, 24 ablation tasks, local keys.

Two companions:

- **[ECT](https://arxiv.org/abs/2608.23623)** allows COMPLETE only when a typed
  certificate binds every claim to in-scope trace evidence that a deterministic replay
  reconstructs. That is a precise model for what `/sase_final` could eventually require.
- **[Actions with Receipts](https://arxiv.org/abs/2610.00327)** binds claim, source span,
  ordered execution prefix and source version together, and treats replay as a verifier.
  It also separates integrity from support: a structurally valid receipt does not prove
  the claim.

*Reality Is the Final Verifier* (Berkeley: Krentsel, …, Zaharia, Stoica) supplies the
theory. `just check` is an inner loop that can close only the *evaluation* gap. Two gaps
sit outside it and cannot generally be certified closed:

- the **requirement gap**, between the spec and what you actually want;
- the **model gap**, between the test environment and the world.

Adding reviewing agents that share the same incomplete artifacts cannot close them. That
is the case for keeping human settlement of goals as the outer loop.

### 3. Parallel Landing: Pre-Write Scope Beats Post-Hoc Repair, and Selectivity Is Hard

SASE fans epics out across many workspaces and lands them on one master. Today's commits
added dispatch conflict-repair resume. Four recent papers bear directly on that:

- **[AI Agent PRs on GitHub](https://arxiv.org/abs/2607.04697)** (cld, gem). Among *concurrently open* PR pairs:
  - two agent PRs from *different* agent products conflicted textually 41.7% of the time
    (48/115);
  - two from the *same* agent product, 19.8% (119/601);
  - about 42% of conflicts were structural (modify/delete 26.8%, add/add 15.1%), exactly
    the shapes file-splitting refactors produce.

  Caveats: the data covers December 2024 to July 2025, and cross-agent pairs are rare
  (2,896 of 580,913 co-active pairs).
- **[Claim Plane](https://arxiv.org/abs/2607.21909) and its
  [confirmatory study](https://arxiv.org/abs/2608.00947)** (Nikolaev). Each worker
  declares a versioned *ChangeIntent* before writing: base commit, typed resources,
  dependencies. A deterministic control plane admits compatible intents, serializes
  overlap, and fails closed on undeclared writes. The confirmatory study ran 30 pairs ×
  3 seeds × 4 arms:
  - static admission raised pair pass from 23.3% to 50.0% and integration success from
    65.6% to 96.7%, but only by serializing 96.7% of executions;
  - the selective, dynamic mode blocked 46 of 90 runs on undeclared scope, and pair pass
    fell to 22.2%.

  The honest lesson: serialization buys reliability, and keeping parallelism safely
  depends on accurate scope declarations that planners do not yet produce.
- **[STALE: Passes Alone, Fails Together](https://arxiv.org/abs/2609.25396)** (EXPRESS
  '26). Mined, real pairs of Django PRs almost never interfered semantically: 1 of 834
  runs. Constructed contract changes broke in 97% of blind runs. A ~130-token oracle
  message describing the sibling's change recovered 82%. For SASE, the cheap
  intervention is to push a short "contract changed" note to siblings, not a merge
  queue.
- **[NP-Bench](https://arxiv.org/abs/2610.07261)** (2026-10-05, single author). It
  partitions work into disjoint file scopes and orders merges producer-before-consumer,
  up front. Clean integrations rose from 1/9 to 9/9 and merge conflicts fell from 13
  to 0. The scenarios are hand-constructed with hand-declared scopes, so read it for the
  algorithm.

Together these suggest some cheap moves:

- declare file scope in epic phase beads;
- serialize phases whose scopes overlap, including `toobig` splits;
- run a pairwise `git merge-tree --write-tree` across in-flight phases before landing;
- give a sibling phase a short contract-change notice when an interface moves.

### 4. Harnesses Mostly Set the Bill, and Labels Do Not Travel

- **[What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433)** (2026-10-03):
  - On a 45-task hard subset, swapping the harness flips 13% of outcomes, the same as
    rerunning; swapping the model flips 22%.
  - Cost differs by up to 3×, driven by the fixed preamble paid on every step: 16,581
    tokens for Claude Code, 7,025 for OpenCode, 829 for mini-SWE-agent.
  - With 45 tasks, a 13-point gap is detected only half the time.
- **[Finding the Right Fit](https://arxiv.org/abs/2610.00917)** (NTU, 2026-10-01; 66
  configurations):
  - Claude leads GPT by 7.94 points under OpenHands but trails by 30.16 under PI.
  - The native CLI is not reliably best.
  - The same model scored 60.32% at $4.66 per task under one harness and 52.38% at
    $19.94 under another.
  - Every harness was set to "high" effort, but the paper notes the label "need not imply
    the same thinking budget across harnesses."
  - Whether a harness re-prompts after an output cap, or times out a hung shell, decided
    many outcomes.
- **[Harness Engineering: eleven systems](https://arxiv.org/abs/2609.00006)** (cld,
  grk):
  - None of the eleven imports an agent framework, and none uses vector retrieval.
  - Skills ship in 9 of 11; Codex copied Claude Code's hook names.
  - §9.7 catalogs each CLI's instruction-file discovery rules, which is exactly what
    instruction bundles must target.
- **[Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)**
  is the nearest peer to SASE's adapter layer. It offers stateful policies above the
  harness (after a new npm package, `git push` needs approval), session spend
  check-ins, an egress proxy that keeps the GitHub token from the agent, and a
  conformance bench.

### 5. Supervising Parallel Agents Is a Return-From-Wait Problem

- **ParallelPilot** (16-person within-subjects study):
  - Its ambient dashboard watches four cues: completion, error, input request, and
    prolonged inactivity.
  - Throughput rose 63% (0.445 vs 0.272 tickets per minute), and participants ran about
    one more agent at peak (3.25 vs 2.31).
  - Perceived control did **not** improve: "Knowing when to intervene does not
    necessarily mean knowing how to intervene."
  - Its run-logger keeps three granularities: raw JSON events, mid-length Markdown
    memory, and one-line cards.
  - It treats "completion" as a cue, not a correctness check.
- **The Work Behind Delegation** (19 developers plus Reddit) splits supervision into
  Plan, Monitor, Wait, Review, Teach, Manual Fix, and Update Assets. Review and Update
  Assets dominate the coded quotes. Developers spend Wait on other agents.

For ACE, these support three things:

- designing for return after Wait, not for watching;
- distinguishing "claims done" from "verified done";
- turning repeated gate answers into proposed assets.

*Oversight Has a Capacity* adds a simulated result: escalating everything is less safe
than load-aware escalation, and gate floods work as an attack.

### 6. Capacity, CI, and Evidence Discipline

- **Anthropic's CI post** (2026-09-14):
  - CI jobs rose 25× in six months.
  - The test-impact service had a single writer, and three patches lasted 70 days, then
    29 days, then less than a day.
  - The fix moved state out of the process: stateless workers append to a journal.
  - Advice: "always plan for the exponential"; make sure the number of CI jobs coming in
    equals the number going out.

  SASE already has a diff-scoped test lane with a coverage baseline and
  `just selection-backtest`. The transferable parts are the jobs-in/jobs-out health
  metric and the single-writer warning for ToolRun and CI telemetry stores.
- **AgentCgroup** measured Claude Code memory:
  - a ~185 MB baseline, plus 1–2 s tool bursts to 500 MB–2 GB;
  - pytest's P95 reached 518 MB, against 13.5 MB for git;
  - CPU stayed below 36% at the concurrency that memory allowed.

  Memory bursts, not CPU, cap agents per host. That points to a memory-limited scope per
  `sase tool run`, with memory pressure as an admission signal. It bears directly on the
  Apollo OOM wipeouts.
- **[Infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise)**
  (Anthropic, Feb 2026, from cdx): resource allocation alone moved Terminal-Bench scores
  by six points. Pin resources before comparing size aliases or swarm shapes on a shared
  server.

### 7. Swarms, Memory, and Agent-Written Code

- **Research swarms.** *Mo' Models, Mo' Problems* (NVIDIA; REALM at EMNLP 2026):
  - In practice, adding models to a pool "nearly always decreases performance," even
    though the theoretical oracle improves.
  - Correct answers overlap (r = 0.931), but errors do not (r = 0.384).
  - Selecting candidates within one model family worked best.

  *ArcticSwarm* measures this swarm's own design. Gated isolation during evidence
  gathering raised BrowseComp-Plus from 78.8% to 82.6%. Both papers argue for synthesis
  claim by claim, not by vote, and for giving researchers distinct angles. This report
  tries to follow that: the parallel-landing cluster came from no researcher, and
  single-source claims were checked rather than counted.
- **Memory.** *VibeMemBench* tested Mem0, SimpleMem, MemoryOS and A-MEM across three
  solvers on 111 real repository tasks. In 11 of 12 pairings, memory failed to beat the
  memory-off baseline. Directly injected verified experience helped a little, but every
  confidence interval crossed zero. That is *No Retrieval Mechanism Before Its Corpus*
  with numbers: measure delivery before building a memory mechanism.
- **Agent-written code.** *Is Agent Code Less Maintainable?* (NYU/CMU, v2 2026-09-29):
  - Building the next PR on agent-written code cut resolve rates by up to 13.1 points.
  - Refactoring was hit hardest.
  - Drift in input validation or error handling raised the odds that the human-based
    branch won (1.83×), and the drift persisted in 85.9% of follow-ups.

  That suggests a land-time check on changed exception types and validation, a sharper
  target than file length.

## Where the Reports Disagreed

| Disagreement | Resolution |
| --- | --- |
| **Which replay paper leads.** cld and gem put Chronicle #1; cdx put Ledger #1; grk put ESAA #2 and Ledger #3. | Chronicle first, because it is the design your annotations ask for and it is short. Its evidence is weak (six self-constructed incidents, simulated model calls). Ledger second, with the strongest evidence in the replay cluster (500 tasks, p < 0.01). ESAA as a companion. |
| **Which receipts paper.** cld: Proof-or-Stop; grk: Actions with Receipts; gem: ECT; cdx: Mnemosyne. | Proof-or-Stop leads because it maps onto E4's open questions: command-set hashes, independence, freshness. ECT and Actions with Receipts are companions. Mnemosyne goes to the next tier. |
| **Hassan v3's rank.** grk #1, gem #2, cld #15, cdx unranked. | Rank 5. It is the namesake and its vocabulary maps one-to-one onto SASE, but it is a vision paper. Its v3 Appendix A is the new, concrete part. |
| **Multi-agent framing.** mus ranked the 2025 Cognition/Anthropic debate #1. Others used 2026 measurements. | The 2026 evidence (Mo' Models, ArcticSwarm, Claim Plane, STALE) supersedes the debate for SASE's decisions. Cognition's April 2026 follow-up, "Multi-Agents: What's Actually Working," is a short optional update. The 2025 pieces are already started in your library. |
| **Merge queue.** gem proposed a Bors-style bisecting merge queue to "eliminate the 41.7% merge conflict rate." | Not supported. 41.7% is a textual-conflict rate between concurrent PRs from different agent products, from 2024–25 public GitHub data. A queue orders landings but does not prevent conflicts. Pre-write scope (Claim Plane, NP-Bench) and contract-change notices (STALE) target the cause, and SASE already has dispatch conflict repair. |
| **Evaluating AGENTS.md v3.** cdx ranked it #3. | Dropped. It was #2 on the October memory and instruction reading list, which already covered v3 (2026-09-29) and the Khatri companion. |

## Corrections to the Swarm Reports

| Report | Claim | What the primary source says |
| --- | --- | --- |
| gem | ECT is by "Hsu et al." | Sole author **Jason Liu, UC San Diego**. The 0/288 vs 252/288 result is confirmed; the model was Gemini 2.5 Flash. |
| gem | 19.8% is the rate for "sequential PRs from the same agent" | Both rates are for **concurrently open** pairs; 19.8% is pairs from the same agent product. |
| gem | Consort link `arXiv:2609.xxxxx` | Consort exists as a Databricks blog post and the `databricks-solutions/consort` repo. Cite the blog. |
| gem | SWE-Router summary names Claude 3.5 Sonnet and GPT-4o as the frontier tier | The paper (arXiv 2607.00053, listed at ICML 2026) exists. Those model names appeared in nothing I checked, so don't rely on gem's summary details. |
| cld | Proof-or-Stop cut hidden failures 31→2 "at 3.8× the tokens" | The 31→2 comparison was **compute-matched**; the 3.80× figure comes from a separate paired comparison. |
| cld | Chronicle killed "51 of 82 mutants" | 51 of **192** in total. The 82 are the mutants that change behavior on the recorded input. Model boundaries were simulated. |
| cld, grk | What Does a Harness Buy?: harness swap flips 13% | That figure is for the **45-task hard subset**. OpenCode's loss is only partly due to its missing re-prompt. The "32k" cap was not verifiable. |
| cld | Mo' Models used "23 open models" | "23 different LM agents"; "fewer models is better" holds for achieved performance only, and the oracle shows the opposite. |
| cld | AgentCgroup: pytest vs git P95 of 518 MB vs 13.5 MB | 518 MB is a Haiku-only P95, and 13.5 MB is git's average. The 144 tasks are 111 GLM plus 33 Haiku runs. Results come from trace replay of a prototype. |
| cld | Agent-code maintainability: "size did not predict" | Downstream line count was significant (1.88×). Only 20.6% of the drift both persisted and related to the failing test. |
| cld | Work Behind Delegation's quote counts | Taken from a 30-thread codebook subsample, not all 102 threads. |
| mus | SlopCodeBench: 2.2× verbosity, ~80% erosion | Those are v1 numbers. v2 (36 problems, best agent 14.8% of checkpoints) reports **2.3×** verbosity and erosion in **77%** of trajectories. |
| mus | "A Declarative Language for… Agent Workflows" (2512.19769) presented as new | Already **started** in your library. |

Claims I checked and found correct: Ledger's numbers (cdx, grk); ArcticSwarm; the
Anthropic CI post; Loopjacking's cases; Proof-or-Stop's binding and independence rules;
Actions with Receipts; VibeMemBench; Reality Is the Final Verifier; Finding the Right Fit;
Omnigent; Beads vs br; CapLease; MAGE and Consort exist.

## Ranked Reading List

**Ranking criteria, in order:**

1. how directly the reading bears on something SASE is building or has queued;
2. whether it gives a design to copy or a measurement that should change a decision;
3. strength of evidence;
4. reading cost.

Companions are short, or worth reading only alongside the lead item. Every item below was
checked against its primary source, and none is a finished read or a pick from an earlier
SASE reading list.

**1. [Chronicle: Cut-Point Replay for Regression Testing of LLM Agents](https://arxiv.org/abs/2609.20625)**
Chawla and Koul, Microsoft; 2026-09-17; code at `theagentplane/chronicle`. Short.
*Companion:* [ESAA](https://arxiv.org/abs/2602.23193) (Santos Filho, Feb 2026).
- **Why read it:** it is the most concrete answer to your two replay annotations. The
  pieces map onto SASE:
  - macro-workflow steps and `sase tool run` invocations are the boundaries;
  - ToolRun records are the envelopes;
  - host-owned completion means a replay turn can run with finalizers off.

  Its limitations list exactly what SASE must add: concurrent calls and an
  order-sensitive digest. ESAA contributes the "rebuild from the log and compare hashes"
  check, and it poses the open question of host-owning every write.
- **Read critically:** six self-constructed incidents with simulated model boundaries.
  This is a mechanism paper.

**2. [Turning Interaction History into Execution State: A Runtime Layer for Long-Horizon Coding Agents (Ledger)](https://arxiv.org/abs/2608.00808)**
Wang, Xu, Li, Peng, Adams, Hassan, Chen; Concordia, Tencent, Queen's; 2026-08-01.
- **Why read it:** the best-evidenced paper in the replay cluster:
  - on 500 SWE-bench Verified tasks, Pass@1 rose from 56.2% to 64.2% (GPT-5 mini) and
    from 75.8% to 81.0% (MiniMax M2.5), with costs 28.9% and 31.8% lower;
  - wrapped around Codex, it added 3.4 points at 24.4% lower cost;
  - it needs no extra model calls.

  Its observed/modified/attempted state is a candidate for successor and continuation
  context, mechanically derived rather than summarized. It comes from the same group as
  the SASE paper, a year later.
- **Read critically:** one run per instance, Python issue repair only. Keep the govern
  path's command suppression apart from receipt semantics.

**3. [Loopjacking: Hijacking Human-in-the-Loop Approval](https://arxiv.org/abs/2609.21081)**
Adithyan Arun Kumar; 2026-09-17; 17 pages.
*Companion:* [Beyond Single-Use Tokens (CapLease)](https://arxiv.org/abs/2608.01710) (Xu et al., 2026-08-03).
- **Why read it:** it is the most immediately actionable security read on the list:
  - `sase-110`, `sase-11t` and `sase-18i` are in progress now, and Telegram approval
    exists;
  - §6.1's approval record and §6.4's regression suite can be applied to SASE's gates
    before they harden. Check that sudo binds argv, cwd, env, user and script hash; that
    plan approval binds a plan-file hash; that a Telegram message which cannot show the
    whole command does not offer one-tap approval; and that a spent approval cannot be
    replayed across channels.

  CapLease adds crash-safe, durable consumption, which replay and automatic recovery
  will need.
- **Read critically:** one researcher's chosen sample, not a prevalence estimate.

**4. [Claim Plane: Reliability Gains and the Limits of Selective Concurrency for Parallel Coding Agents](https://arxiv.org/abs/2608.00947)**
Nikolaev; 2026-08-02.
*Companions:* the original [Claim Plane](https://arxiv.org/abs/2607.21909);
[Passes Alone, Fails Together (STALE)](https://arxiv.org/abs/2609.25396) (Xia, Wu, Park;
EXPRESS '26); [NP-Bench](https://arxiv.org/abs/2610.07261) (Muku, 2026-10-05);
[AI Agent PRs on GitHub](https://arxiv.org/abs/2607.04697) (7 pages).
- **Why read it:** SASE lands many parallel phases on one master, and conflict repair
  became a finalizer feature today. This cluster says where to intervene:
  - declare scope before writing, and serialize overlap;
  - tell siblings when a contract changes (STALE: ~130 tokens recovered 82%);
  - do not trust selective concurrency until scope declarations are accurate (dynamic
    admission fell to 22.2% pair pass).

  STALE's reassuring result also matters: mined real PR pairs almost never interfered
  semantically.
- **Read critically:** small samples, one author each for Claim Plane and NP-Bench;
  STALE's constructed failure rates "do not estimate how often these problems occur in
  practice."

**5. [Agentic Software Engineering: Foundational Pillars and a Research Roadmap (v3)](https://arxiv.org/abs/2509.06216)**
Hassan et al.; v3 2026-06-24. _Already in your library (queued since 2025-11-28, legacy
backlog)._
- **Why read it:** it is the paper that named SASE and ACE. Its artifacts map onto
  SASE's:
  - BriefingScript → plans;
  - LoopScript → macro workflows;
  - MentorScript → memory and skills;
  - Consultation Request Pack → gates;
  - Merge-Readiness Pack → final declaration plus receipts.

  v3's Appendix A adds worked examples. The Merge-Readiness Pack's five criteria are a
  ready rubric for what E4's successors should prove: functional completeness, sound
  verification, SE hygiene, clear rationale, and auditability.
- **Read critically:** a vision scaffold, not a system. If you already know v1, read
  Appendix A only.

**6. [Proof-or-Stop: Don't Trust the Agent, Trust the Evidence](https://arxiv.org/abs/2607.14890)**
Huang et al.; 2026-07-16; 48 pages.
*Companions:* [When May an Agent Stop? (ECT)](https://arxiv.org/abs/2608.23623) (Jason
Liu, UCSD); [Actions with Receipts](https://arxiv.org/abs/2610.00327) (Hu et al., UCAS).
- **Why read it:** it is the outside design closest to E4. It answers what E4 leaves
  open:
  - command-set hashes, so editing `just check` makes old receipts stale;
  - independence defined by host, session and key;
  - an explicit degraded mode that is never upgraded;
  - freshness rules, so an old PASS cannot hide a new FINDING.

  ECT shows what a typed completion certificate checked by replay would look like.
  Actions with Receipts shows how to make the claim-to-evidence association itself
  auditable.
- **Read critically:** one model family and local keys. Read the evidence model and the
  rejection codes, not all 48 pages.

**7. [What Does a Harness Buy? Tokens, Mostly](https://arxiv.org/abs/2610.04433)** with **[Finding the Right Fit](https://arxiv.org/abs/2610.00917)**
Liu and Han, Shandong, 2026-10-03; Li et al., NTU, 2026-10-01.
*Companion:* Anthropic's [infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise) post.
- **Why read it:** both are a week old and test two SASE decisions directly, *Size
  Aliases Descend The Effort Ladder* and *Adapters Normalize Harnesses*:
  - rankings flip across harnesses, and native CLIs are not reliably best;
  - effort labels are not portable;
  - fixed per-call text sets the bill;
  - whether a harness continues after an output cap, or times out a hung shell, decides
    outcomes.

  They point to adapter features: classifying why a run ended, adding continuation, a
  probe that the requested effort took effect, and fixed per-call tokens on the
  instruction scoreboard. They also warn against changing defaults on samples of 45
  tasks.
- **Read critically:** SWE-bench and Terminal-Bench, not campaigns. If you score SASE on
  pass-rate deltas, expect noise.

**8. [ParallelPilot: Supporting Coordination and Monitoring in Parallel AI Coding](https://arxiv.org/abs/2609.33113)** with **[The Work Behind Delegation](https://arxiv.org/abs/2609.24234)**
Long et al., Microsoft Research, 2026-09-27; Park et al., KAIST/CMU, 2026-09-21.
- **Why read it:** ACE is where most SASE commits are going. ParallelPilot is the only
  controlled study I found of a dashboard for supervising parallel coding agents. It
  covers four intervention cues, a three-granularity run log, and a planner that
  separates output dependencies from shared-file conflicts. Throughput rose 63%, but
  perceived control did not improve. Delegation's seven stages give a vocabulary for
  what ACE should optimize: coming back from Wait, Review, and Update Assets.
- **Read critically:** 16 mostly junior participants on 20-minute tasks, with no PR
  review or merge in the loop.

**9. [Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents (eleven systems)](https://arxiv.org/abs/2609.00006)** with **[Introducing Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)**
Barbaste et al., Wavestone, July 2026, 83 pages; Zaharia, Uhlenhuth, Zumar, Databricks,
2026-06-13.
- **Why read it:** this is the source-level map of the CLIs SASE wraps. §9.7, on
  instruction-file discovery per CLI, is a direct input to instruction bundles. Omnigent
  is the nearest public peer architecture: stateful policies above the harness,
  credentials kept out of the agent, and a conformance bench.
- **Read:** §9.7, the memory-governance and ACP sections, the Omnigent analysis, and the
  Databricks post.

**10. [Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering](https://arxiv.org/abs/2609.12039)**
Krentsel, Agarwal, Cemri, Liu, Sankhe, Mao, Zaharia, Stoica; UC Berkeley; 2026-09-10.
- **Why read it:** it gives *Receipts Prove Before They Skip*, *Triage Annotates*,
  two-speed CI and human goal settlement one framework. The inner loop
  (agent + `just check`) can close the evaluation gap. The requirement and model gaps
  need an outer assurance loop of human judgment and real-world evidence, and more
  reviewing agents cannot close them. Here "model" means the environment model, not the
  LLM.

**11. [Agentic coding is straining CI. Here's how we scaled test impact analysis at Anthropic](https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic)**
Sachin Malhotra, Anthropic; 2026-09-14. About ten minutes.
- **Why read it:** `sase-126` and `sase-1c1` are about a red master. This is the
  clearest field account of what agent volume does to CI: 25× more jobs in six months,
  and patches that each lasted less time than the one before. SASE already does
  diff-scoped selection; take the single-writer lesson, the journal, and the
  jobs-in = jobs-out metric.

**12. [VibeMemBench: Evaluating Memory Systems for Coding Agents on Real Repository Coding Tasks](https://arxiv.org/abs/2609.23570)**
Fan et al., SIAT/Alibaba; 2026-09-20.
- **Why read it:** it is the methodological follow-up to the memory papers you finished
  (MemoryOS, filesystem memory). It separates whether useful experience exists from
  whether a memory system delivers it, and finds that the four systems mostly do not.
  It is also a template for any SASE memory experiment.
- **Read critically:** targets were chosen where memory should help, and memory-side
  token costs are excluded.

**13. [AgentCgroup: Understanding and Controlling OS Resources of AI Agents](https://arxiv.org/abs/2602.09345)**
Zheng et al.; v3 2026-07-22. Read the
[blog post](https://eunomia.dev/blog/2026/02/17/agentcgroup-what-happens-when-ai-coding-agents-meet-os-resources/)
first.
- **Why read it:** it is the best measurement of what a coding agent does to a host.
  Memory bursts from tools, especially test runs, cap concurrency; CPU does not. It
  bears directly on the Apollo OOM wipeouts, on per-tool-call memory scopes for
  `sase tool run`, and on admitting work by memory pressure instead of CPU slots.

**14. [Mo' Models, Mo' Problems](https://arxiv.org/abs/2609.17306)** with **[ArcticSwarm](https://arxiv.org/abs/2609.01870)**
Marjanović et al., NVIDIA, REALM at EMNLP 2026; Yoon et al., 2026-09-01.
- **Why read it:** they test the shape of SASE's research swarm. Bigger mixed pools
  usually underperform their best member, errors are what decorrelate, and isolation
  during gathering measurably helps. Expect to change synthesis (by claim, not vote) and
  briefs (a distinct angle per researcher), and to check that the final beats the best
  single report.
- **Read critically:** short-answer QA and browsing, not coding.

**15. [Is Agent Code Less Maintainable Than Human Code?](https://arxiv.org/abs/2606.21804)**
Patel, Hou et al., NYU/CMU; v2 2026-09-29.
*Companion:* [SlopCodeBench v2](https://arxiv.org/abs/2603.24755).
- **Why read it:** SASE is almost entirely written and refactored by agents. This is
  the best controlled evidence on how agent code burdens the next agent. Refactoring is
  hit hardest, and the measurable risk is contract drift in validation and error
  handling. SlopCodeBench shows the long-horizon version: no agent finished any problem,
  and erosion rose in 77% of trajectories.

### Next Tier: Skim When the Topic Becomes Active

- **[Oversight Has a Capacity](https://arxiv.org/abs/2606.08919)** (Turan, 12 pages,
  simulation): load-aware gate routing, and gate floods as an attack. Read before
  tuning Telegram versus ACE-inbox routing.
- **[Beads vs br](https://gascity.com/guide/beads-vs-br/)** and
  **[Restoring Beads Classic](https://www.dolthub.com/blog/2026-04-02-restoring-beads-classic/)**:
  the failure modes Beads hit with SQLite plus JSONL in git, including resurrected
  deletes, stale-database overwrites, and split-brain. An acceptance checklist for what
  remains of `sase-1h8`. The guide is vendor-written.
- **[From Agent Loops to Deterministic Graphs: Execution Lineage](https://arxiv.org/abs/2605.06365)**
  (Rosen and Rosen): restart from a step with dependency invalidation that preserves
  unaffected work. Two tasks, three repeats.
- **[Model-Based Agentic Software Engineering (MAGE)](https://arxiv.org/abs/2608.25174)**
  (Davis et al.): the "governed engineering environment." In its DocAble case study, the
  ratio of infrastructure to production code rose from 0.85× to 3.68× over a
  540k-line agent-built system. A useful lens on SASE's own validators and gates.
- **[SWE-Router](https://arxiv.org/abs/2607.00053)** (listed at ICML 2026): a cheap model explores
  for a few turns, then a value head reads the partial trajectory to decide whether to
  escalate. Relevant if size aliases become dynamic.
- **[Harness Tokenomics](https://arxiv.org/abs/2609.28919v2)** (v2 2026-09-26): routing
  boundaries that are aware of cache payback (session start, subagent launch). The
  savings come from an emulation.
- **[Mnemosyne](https://arxiv.org/abs/2607.00269v3)**: agent output stays a proposal
  until deterministic admission against effective state, and repairs must re-enter
  admission. 60 pages; read the admission model only.
- **[Engineering Reliable Coding Agents](https://arxiv.org/abs/2608.13867)**, chapters
  9–10 (Jarmak; cld's pick, which I did not re-read): idempotency keys, fencing stale
  workers, and kill-point fault injection. The operational half of replay.
- **[Understanding Agent Scaling via Diversity](https://arxiv.org/abs/2602.03794)**: two
  diverse agents can match sixteen homogeneous ones under matched budgets. A companion
  to rank 14.
- **[GitSwarm](https://arxiv.org/abs/2610.04862)**: compounding inference through a
  shared git repo. "Ancestry coverage" (how much later work built on earlier work) could
  serve as a metric for epics and swarms.
- **[PROJECTMEM](https://arxiv.org/abs/2606.12329)**: an event-sourced coding memory
  with a pre-edit advisory drawn from recorded failures. Closest to beads plus "don't
  repeat a failed approach."
- **[Introducing Consort](https://www.databricks.com/blog/introducing-consort-test-driven-development-branching-database)**
  (Databricks): a spec frozen at a hashed gate, tests the coder cannot edit, and the
  coder never judges its own work.
- **[AgentGUI](https://arxiv.org/abs/2607.26300)** (ETH Zürich): a fleet GUI with an LLM
  manager that audits for drift. Small user study (N = 8).
- **[Complex Agents, Shallow Tests](https://arxiv.org/abs/2610.04921)** and
  **[Correct Is Not Governed](https://arxiv.org/abs/2608.12761)** (cld): mutation-test
  the declaration, receipt and triage parsers, and measure a gate's false-block rate
  before making it hard.
- **Cognition, ["Multi-Agents: What's Actually Working"](https://cognition.com/blog/multi-agents-working)**
  (April 2026): Cognition's own update to *Don't Build Multi-Agents*, which you started.

## Considered and Left Out

- **Already on an earlier SASE reading list:**
  - *Evaluating AGENTS.md* v3 (cdx #3);
  - Gao and Chen's *agent-friendly documentation* study (gem #7);
  - *Agentic Context Engineering* (grk #12);
  - *Levels, Ticks and Cascaded Intelligence* (grk #6);
  - Anthropic's *Harness design for long-running apps* (cdx #10);
  - *Scaling Managed Agents* (cdx #8);
  - Carlini's C compiler.
- **mus's standards picks:** Agent Skills/agentskills.io, the Agentic AI Foundation,
  Spec Kit/Kiro. These are 2025-era standards news. Skills and AGENTS.md were covered by
  the memory list, and spec-driven development by Goals round two.
- **mus's other picks:** SPL, Prompt Choreography and Quine are interesting but far from
  current SASE work. Prompt Choreography needs control over model serving that SASE does
  not have. The dev.to "verifiable receipts" spec is weaker than Proof-or-Stop.
- **gem:** Cao's *Agentic Software* is framing only.
- **grk:** the Restate Series A post is a funding announcement, and its Replit "10×
  durable actions" fact is secondhand. The progressive-disclosure report overlaps the
  memory list's *Skill Blocks*. *Swarms as Researchers* is framing that ranks 14 and 10
  already carry.
- **cdx:** Sander et al.'s scaling study covers sequential architectures, not SASE's
  concurrent workers. *Demystifying evals* is good but already queued in your library.
- **CodeRescue** (cld): withdrawn on 2026-07-30.

## Idea Backlog

These are ideas the readings point to, not filed beads.

| # | Idea | Source | SASE area |
| --- | --- | --- | --- |
| 1 | Record per-step envelopes (inputs, output, provider, model, effort, CLI version) for macro-workflow steps and `sase tool run`. Offer "re-run from step *k*" with earlier steps stubbed, addressed by (step, occurrence), failing loudly on divergence. Keep it separate from receipt reuse. | Chronicle, ESAA | Replay (new) |
| 2 | Add a mechanically derived execution-state view (observed, modified, attempted) to continuation and successor context. Measure stale reads and repeated work. | Ledger | Continuations, `#fork` |
| 3 | Audit gates against Loopjacking §6.1/§6.4: a canonical descriptor hash, single use across channels, no one-tap approval when the full command can't be shown, and post-approval mutation tests. | Loopjacking, CapLease | `sase-110`, `sase-11t`, `sase-18i` |
| 4 | Fingerprint receipts with a command-set hash; define a KNOWN witness as a different host or session; mark degraded mode explicitly; keep failed receipts in history. | Proof-or-Stop, Correct Is Not Governed | E4 successors |
| 5 | Declare file scope on epic phases; serialize overlapping phases and `toobig` splits; run pairwise `git merge-tree` before landing; send siblings a short contract-change notice. | Claim Plane, NP-Bench, STALE | Dispatch, finalizers |
| 6 | An adapter conformance bench: end-reason classification, continuation after an output cap, a probe that effort took effect, policy denial, and fixed per-call tokens on the scoreboard. | Harness papers, Omnigent | *Adapters Normalize Harnesses* |
| 7 | Size aliases as a measured (alias × task type) table, never changed on small samples and only with resources pinned. | Finding the Right Fit, infrastructure noise | *Size Aliases* |
| 8 | ACE attention cues (done, error, input needed, stalled), with "claims done" kept visibly separate from "verified done." | ParallelPilot | ACE TUI |
| 9 | A memory-limited scope for each `sase tool run`; admission on memory pressure; detect retry loops. | AgentCgroup | `sase tool`, Apollo |
| 10 | A jobs-in/jobs-out health metric for ToolRuns and CI; keep telemetry state out of single-writer processes. | Anthropic CI post | `sase-126`, `sase-1c1` |
| 11 | Swarm synthesis by claim; a distinct angle per researcher; a check that the final beats the best single report. | Mo' Models, ArcticSwarm | Research swarms |
| 12 | A land-time "contract drift" check for changed exception types, validation and silent fallbacks. | Is Agent Code Less Maintainable? | Land agents, `toobig` |

## Caveats

- Nearly everything here is an arXiv preprint. Several papers have a single author or
  small samples:
  - Chronicle: six incidents;
  - NP-Bench: K = 5 pilots;
  - Claim Plane: 30 pairs;
  - Execution Lineage: two tasks;
  - Oversight Has a Capacity: simulation only.
- Ledger and the harness papers use single runs or small hard subsets.
- Verification read abstracts and HTML full text through fetch agents, and the longest
  pages were truncated, so tail sections came from tool summaries. Numbers in this report
  come from verbatim text; the corrections table marks where a figure could not be
  confirmed. I did not re-read cld's monograph chapters or cdx's Mnemosyne, Tokenomics
  and diversity papers.
- Some arXiv dates disagree with their IDs, or with the paper's own header (for example,
  Proof-or-Stop says "June 2026" but was submitted 2026-07-16). This report gives the
  dates arXiv shows.
- Being absent from your Bob library does not mean you have not read something.

## Proposed Library Commands (Not Run)

```bash
bob ref create https://arxiv.org/abs/2609.20625   # Chronicle
bob ref create https://arxiv.org/abs/2608.00808   # Ledger
bob ref create https://arxiv.org/abs/2609.21081   # Loopjacking
bob ref create https://arxiv.org/abs/2608.00947   # Claim Plane confirmatory
bob ref create https://arxiv.org/abs/2609.25396   # STALE
bob ref create https://arxiv.org/abs/2607.14890   # Proof-or-Stop
bob ref create https://arxiv.org/abs/2610.04433   # What Does a Harness Buy?
bob ref create https://arxiv.org/abs/2610.00917   # Finding the Right Fit
bob ref create https://arxiv.org/abs/2609.33113   # ParallelPilot
bob ref create https://arxiv.org/abs/2609.00006   # Harness Engineering (eleven systems)
```

Add `-L` to also narrate.

Library check: 2 of 49 candidates already in your library (0 finished).
