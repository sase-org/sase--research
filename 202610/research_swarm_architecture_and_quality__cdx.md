---
title: Improving the SASE research swarm
create_time: 2026-10-01
updated_time: 2026-10-01
status: complete
tags:
  - sase
  - research-swarm
  - multi-agent-systems
  - deep-research
---

# Improving the SASE research swarm

## Bottom line

`#research_swarm` already gets several unusually important things right: genuinely blind
parallel researchers, model-provider diversity, durable artifact handoffs instead of
transcript scraping, a centralized lead, explicit dependency edges, and resource-aware
queueing. Its main weakness is not too little parallelism. It is that the parallelism is
largely undirected and the quality contract is underspecified. Every researcher receives
nearly the same broad instruction, research reports have no required evidence schema,
and after synthesis the only current downstream reviewer is an editor who is explicitly
forbidden to correct substantive errors.

The strongest next architecture is therefore:

```text
optional scope and clarification
              |
              v
blind generalist + complementary specialist researchers
              |
              v
evidence-weighted synthesis into a draft
              |
              v
fresh-context claim and coverage audit
              |
              v
adjudicating publisher -> canonical report
```

This should not become a many-round conversational debate. Research on agent systems
shows that collaboration helps when work is decomposable, but hurts sequential tasks and
can amplify errors without centralized verification. Research on debate also shows that
conformity and majority aggregation can move correct agents toward an incorrect
consensus. The right design preserves the current swarm's independence, adds purposeful
diversity before synthesis, and uses evidence rather than votes to resolve disagreement.

## What I inspected

I reviewed the current plugin source on `master` at `a21dc49`, the installed xprompt
rendering, relevant SASE xprompt and artifact-link machinery, and the xprompt's recent
history. The important implementation facts are:

- The default swarm has Codex and Claude researchers plus an `@xlarge` lead; Grok, Muse,
  and Gemini researchers are opt-in. Every worker gets the same research request plus
  isolation and filename instructions (`src/sase_research_artifacts/xprompts/research_swarm.md`,
  lines 127-238).
- Workers are prevented from reading one another's reports. This is a real strength,
  because it preserves independent error paths before aggregation.
- Every worker writes and registers a snapshot. The lead discovers them through
  `wait.artifacts`, matches producer names and suffixes, and uses audited
  `sase artifact read` calls rather than predecessor transcripts (lines 242-309).
- The lead is asked to research gaps and disagreements, but is also the sole substantive
  judge, researcher, synthesizer, and writer (lines 245-295).
- The optional linker performs strong editorial preservation and URL-availability checks,
  but it is explicitly prohibited from adding evidence, settling open questions, or
  correcting the lead (lines 357-457). Its link check establishes reachability, not
  whether a cited page supports a claim.
- The history contains a useful prior design. Commit `59fdf94` added an opt-in,
  fresh-context critique agent that formed a checklist before reading the lead, checked
  primary evidence, reviewed synthesis fidelity, and wrote a companion critique. Commit
  `bf8deb9` later replaced that stage with the linker. Much of the old critic prompt is
  reusable, but a companion critique alone is not enough: corrections need a route into
  the canonical report.
- SASE's current automatic research-lineage derivation still recognizes only `__a` and
  `__b` siblings (`src/sase/artifact_links/derive/_research_lineage.py`), while the plugin
  now creates `__cdx`, `__cld`, `__grk`, `__mus`, and `__gem`. Thus the current naming
  scheme no longer receives the automatic `derives-from` coverage the feature describes.
- When neither `linker` nor `image` is enabled, the lead writes the canonical report but
  does not explicitly register it. The source drafts have immutable snapshots; the most
  valuable output does not receive the same explicit snapshot contract in that branch.

## What good research-agent swarms need

### Architecture must follow the task

The most directly applicable controlled study is Kim et al.'s 2026 work on scaling agent
systems. Across 260 configurations, multi-agent performance ranged from a large gain on
decomposable financial reasoning to a 70% loss on sequential planning; architectures
without centralized verification propagated more errors. Their selector chose the best
architecture for 87% of held-out configurations. The practical lesson is not that every
research request needs more agents, but that the swarm should distinguish breadth,
decomposability, logical depth, tool load, and risk before choosing a topology.
([paper](https://arxiv.org/abs/2512.08296))

The current swarm always applies essentially the same topology and changes only the
number and provider of researchers. That is appropriate for broad, parallelizable
landscape research, but wasteful for a narrow factual lookup and weak for a deeply
sequential proof or design argument.

### Perspective diversity matters more than repeated copies

STORM's pre-writing system discovers different perspectives, asks questions from those
perspectives, and builds an outline before writing. Relative to an outline-driven RAG
baseline, experienced editors rated 25 percentage points more of its articles organized
and 10 points more broad in coverage. Its limitations are equally relevant: perspective
search can transfer source bias and can over-associate unrelated facts.
([Shao et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.347/))

The current swarm has provider diversity, which is valuable, but provider identity is
not a research charter. Giving five models the same prompt often buys five overlapping
search paths. A better design combines:

- at least one blind, end-to-end generalist, preserving an unframed replication;
- query-specific specialist charters that partition perspectives, subquestions, source
  types, or alternatives;
- one deliberately disconfirming charter that seeks counterexamples and the strongest
  case against the likely recommendation; and
- model/provider diversity, with role assignment rotated or varied so a provider is not
  permanently confounded with one role.

The generalist is important. A single scoper can itself frame the problem incorrectly;
one researcher should remain independent of that decomposition and answer the original
request directly.

### Research quality is claim-and-evidence quality

DeepResearch Bench evaluates both report quality and retrieval through effective
citation count and citation accuracy, rather than treating fluent length as quality.
([paper](https://arxiv.org/abs/2506.11763)) ResearchRubrics uses fine-grained, weighted
criteria spanning factual grounding, reasoning, and clarity. Its leading evaluated
systems remained below 68% average rubric compliance, with implicit reasoning and
synthesis responsible for roughly half of failures.
([paper](https://arxiv.org/abs/2511.07685)) CLAIM-BENCH similarly found substantial
limitations in mapping scientific claims to evidence, while multi-pass and one-claim-at-
a-time prompting improved claim-evidence linking at additional cost.
([paper](https://aclanthology.org/2025.ijcnlp-long.127/))

The current worker prompt does not require source quality, citation completeness,
claim-source entailment, freshness, counterevidence, or calibrated uncertainty. The
lead therefore receives prose that is expensive to compare and difficult to audit. A
common report contract should require, proportionally to the task:

1. A direct answer and explicit scope assumptions.
2. A compact coverage checklist tied to the assigned charter.
3. A load-bearing claim ledger: claim, supporting source, source type, relevant date or
   version, whether the source directly supports or merely informs the claim, and
   confidence.
4. Counterevidence and credible alternatives, not just supporting material.
5. Unresolved questions and the evidence or experiment that would settle each.
6. A source-quality note distinguishing primary evidence, authoritative documentation,
   secondary synthesis, and inference.

This need not become a giant table for every sentence. It should cover the claims on
which the answer or recommendation actually depends.

### Verification must be independent and actionable

The MAST study of 1,642 multi-agent traces identifies failures in system design,
inter-agent alignment, and task verification. Its observed modes include failure to
clarify assumptions, ignoring or withholding information, premature termination, and
missing or incorrect verification. A workflow change giving the appropriate role final
authority improved one studied system's success rate by 9.4%, illustrating that topology
and decision rights matter, not just stronger prompts.
([Cemri et al.](https://arxiv.org/html/2503.13657v3))

An independent audit after the lead is more useful than asking the lead to self-review.
It should start in a fresh context, ideally with a different provider, form its rubric
before reading the draft, and then atomize only the load-bearing claims. For each it
should check:

- source existence and authority;
- actual entailment, not merely URL liveness;
- date and version freshness;
- whether two apparent sources are genuinely independent;
- whether the synthesis dropped minority evidence, caveats, or disagreements; and
- whether confidence matches the evidence.

The prior `59fdf94` critic prompt already implements much of this discipline. The key
change is to insert an adjudicating publisher after it. That publisher should receive
the lead draft, the audit, and the worker artifacts, then either incorporate each
material correction or record why it was rejected. The current linker can be evolved
into this publisher while retaining its excellent structural and link-preservation
checks.

### Do not optimize for consensus

Free-MAD reports that repeated consensus-seeking can propagate errors through LLM
conformity and that majority voting can degrade reasoning; it replaces consensus with a
score-based, anti-conformity design.
([Cui et al., ACL 2026](https://aclanthology.org/2026.findings-acl.1600/)) Related work
finds vanilla debate can underperform simple voting when initial viewpoints lack
diversity and confidence is not communicated.
([Zhu et al., ACL 2026](https://aclanthology.org/2026.findings-acl.1694/))

For `#research_swarm`, this argues against letting workers read and debate one another
before they have produced independent artifacts. It also argues against treating the
number of reports making a claim as its strength. The lead should construct a claim
matrix with columns for each report, but adjudicate by evidence quality and independent
support. A well-supported minority claim can beat a repeated unsupported claim.

### Iteration helps when roles and selection criteria are explicit

Google's Co-Scientist uses specialized generation, reflection, ranking, evolution,
proximity, and meta-review agents under a supervisor, with asynchronous execution and
iterative critique. Its domain and objective differ from general desk research, so it
is not a template to copy wholesale, but it reinforces two transferable principles:
specialized roles and explicit evaluation/refinement stages are more meaningful than a
flat collection of identical workers.
([paper](https://arxiv.org/abs/2502.18864))

## A concrete v2 design

### Stage 0: Select a profile

Expose a small set of understandable profiles rather than equating quality with agent
count:

| Profile | When to use | Shape |
| --- | --- | --- |
| `quick` | Narrow, low-risk, readily verifiable request | One strong researcher; optional link audit |
| `ensemble` | Judgmental but poorly decomposable question | Two or three blind end-to-end answers, then lead |
| `decompose` | Broad, parallelizable research | Scoper, blind generalist, specialist charters, lead |
| `audit` | High-stakes, durable, or implementation-driving report | `decompose` plus claim auditor and adjudicating publisher |

Initially make the caller choose the profile, with `balanced`/`ensemble` as a safe
default. An automatic selector is worth adding only after an evaluation corpus shows
that its task classification is reliable.

### Stage 1: Scope and clarify

An optional `research.<id>.scope` agent should produce a small JSON object containing:

- normalized question and non-goals;
- task classification and why it is or is not decomposable;
- a weighted answer rubric, including likely implicit requirements and negative
  criteria;
- source policy and freshness cutoff;
- one charter per enabled researcher; and
- stopping criteria.

If ambiguity would materially change the answer, it should use SASE's existing question
gate to ask the user rather than silently choosing an interpretation. This directly
addresses MAST's clarification failure mode. The scoper should publish the object with
`sase var set --json`; waited worker prompts can read it through SASE's existing
`agents[...]` Jinja namespace. No transcript inheritance is needed.

The scope should not be treated as truth. The generalist receives the original prompt
and the rubric but not a narrow specialist charter; every worker may identify a bad
assumption in the scope.

### Stage 2: Blind parallel research

Retain the current peer-isolation language. Add a role-specific charter and the shared
evidence contract. For a five-worker run, useful default role shapes are:

1. **Generalist replication** — answer the original request end to end.
2. **Primary-evidence analyst** — find authoritative sources and test load-bearing facts.
3. **Alternatives and counterevidence analyst** — steelman credible alternatives and
   search for disconfirming cases.
4. **Implementation and constraints analyst** — costs, compatibility, failure modes,
   migration, and existing mechanisms.
5. **Coverage scout** — seek missing stakeholder, historical, cross-domain, or edge-case
   perspectives.

These are role families, not fixed mappings to cdx/cld/grk/mus/gem. The scoper should
adapt them to the question and vary provider-role assignment across runs.

Each worker should register its Markdown report as it does now and publish a small
machine-readable summary through `sase var`: charter covered, confidence, open
questions, primary-source count, and report ref. The Markdown remains the substantive
record; the variables let the lead detect incomplete handoffs without parsing prose.

### Stage 3: Evidence-weighted lead synthesis

The lead should create a private synthesis worksheet before drafting:

- rubric item -> which reports cover it;
- load-bearing claim -> support, contradiction, and source quality;
- report disagreement -> what evidence resolves it;
- missing area -> targeted follow-up search; and
- confidence -> reason and residual uncertainty.

Then it should do only gap-targeted research, rather than independently repeating the
whole search by default. The final report should disclose material disagreements and
why one view won. It should never infer consensus merely from repeated wording.

The lead should always register its output, not only when a downstream linker is
enabled. After registration it should create explicit `derives-from` links from the
lead report to every worker report with `sase artifact link add`. This uses today's SASE
feature and avoids depending on the stale `__a`/`__b` filename heuristic.

### Stage 4: Fresh-context audit

Restore the old critique concept under a clearer name such as `verify` or `audit`, and
run it by default in the `audit` profile. It should not converse with the lead and should
not seek agreement. It should emit a compact issue manifest:

```text
severity | lead section | claim | verdict | evidence | proposed correction | effect
```

It should verify the claims that change the conclusion first and stop when the remaining
unchecked claims cannot change the recommendation. This keeps cost bounded and reduces
style criticism masquerading as research.

### Stage 5: Adjudicating publisher

Evolve the current linker into a publisher with two modes:

- `preserve`: today's behavior for runs without an audit;
- `adjudicate`: integrate the lead and audit, recording disposition of every critical or
  major audit item before publishing `<name>.md`.

Preserve the current inventory-before-editing step, URL checks, anchor checks, and
image embedding. Add semantic citation checks already completed by the auditor and a
short provenance note or machine-readable disposition artifact. Register the canonical
report and link it `derives-from` the lead draft and audit; the lead draft in turn links
to worker reports.

## Better use of existing SASE features

| Need | Existing SASE primitive | Recommended use |
| --- | --- | --- |
| Dynamic charters and rubrics | Cross-agent JSON output variables via `sase var set`; waited-agent `agents[...]` namespace | Scoper publishes assignments; workers and lead consume structured state |
| Clarification | Question gate and `/sase_questions` | Scoper asks only when ambiguity changes the research plan |
| Parallelism and ordering | `%wait`, `%queue`, weights, priorities, clans | Express the staged DAG and keep expensive audits opt-in/profile-driven |
| Clean handoffs | `wait.artifacts` plus `sase artifact read` | Continue artifact-only transfer; do not regress to transcript inheritance |
| Provenance | `sase artifact create` and `sase artifact link add ... derives-from ...` | Register every stage and explicitly connect outputs to inputs |
| Bias control | Fresh agent segments versus `#fork` | Fresh context for auditor and publisher; use `#fork` only where context continuity is desired, such as image production |
| Controlled experiments | `%alt` and `%repeat` | Compare prompt/topology variants and gather replicate runs under matched budgets |
| Observability | Clan/tribe grouping, archived prompts, agent metadata, output variables | Preserve a run-level view and collect completion, cost, latency, and quality summaries |

The prompt should also correct the sentence “SASE derives your plan's links” in the lead
and linker instructions. These outputs are research reports, not plans, and current
research lineage is filename-derived rather than inferred from audited reads.

## New SASE features that may be justified

Most improvements need no new core feature. Two additions have a credible cross-workflow
case:

### Settled or quorum joins

Named waits currently release on successful completion. One failed provider can leave
the lead permanently parked even when four strong reports exist. Add an explicit join
policy such as “continue when all dependencies settle, provided at least N succeeded,”
with terminal statuses and artifacts exposed to the consumer. The strict current wait
should remain the default. Research swarms, test matrices, benchmark shards, and
redundant builds all benefit from a typed quorum/settled join.

Until that exists, keep the retry-by-same-name recovery path and make the operational
state visible; do not silently drop an expected researcher.

### Data-driven runtime fan-out

A scoper cannot currently return an arbitrary list of charters that becomes an arbitrary
number of agent launch units. A typed `map`/fan-out over a JSON variable could make
topology truly task-adaptive. This is more invasive and should not be built yet. First
test fixed `quick`, `ensemble`, `decompose`, and `audit` profiles. Add runtime fan-out
only if the evaluation shows that fixed slots materially waste compute or miss coverage.

A special research evidence store is not yet justified. Markdown reports, small output
variables, explicit snapshots, audited reads, and typed artifact links are sufficient
to test the design.

## Evaluation plan

Prompt changes should not be judged from one impressive report. Build a regression set
of roughly 30-50 prompts stratified along the ResearchRubrics dimensions of conceptual
breadth, logical nesting, and exploration, plus categories important to SASE:

- current technical facts and API/version questions;
- repository and architecture research;
- comparative product or design decisions;
- historical synthesis;
- ambiguous prompts that should trigger clarification;
- narrow prompts for which a swarm should decline to scale; and
- adversarial cases with misleading or mutually dependent sources.

For each prompt, author hidden weighted criteria and negative criteria. Compare current
and proposed profiles under matched model, time, and token budgets, using replicated
runs. Score:

1. Required and implicit rubric coverage.
2. Load-bearing claim accuracy.
3. Citation existence, entailment, freshness, and primary-source quality.
4. Effective source diversity, discounting multiple pages that repeat one origin.
5. Correct handling of disagreement and uncertainty.
6. Recommendation actionability.
7. Human preference from blinded paired review.
8. Completion rate, degraded-run recovery, wall time, tokens, and cost.
9. Artifact correctness: snapshots, producer identity, `derives-from` coverage, and no
   overwrite or orphaned publisher.

Use an evaluator with atomic criteria, not a single holistic “which report is better?”
prompt; holistic judges are vulnerable to verbosity. Manually audit a sample of the
highest-impact claims and any cases where automated judges disagree. SASE's `%repeat`,
`%alt`, archived prompts, clans, artifacts, and output variables are enough to build the
first harness without new orchestration machinery.

## Ranked improvements

1. **Add a shared evidence contract and load-bearing claim audit.** Require scope,
   primary-source preference, claim-source support, freshness, counterevidence,
   uncertainty, and open questions from workers; make semantic verification a distinct
   stage. This addresses the largest present quality gap.
2. **Introduce task-aware scoping and complementary charters while retaining one blind
   generalist.** Use `sase var` for the rubric and assignments, and a question gate for
   consequential ambiguity. This creates purposeful diversity without surrendering
   independent replication.
3. **Restore a fresh-context critic and put an adjudicating publisher after it.** Reuse
   the strongest ideas from commit `59fdf94`, but ensure critical corrections can reach
   the canonical report instead of living only in a companion critique.
4. **Build a rubric-based A/B evaluation harness before adding more agents.** Measure
   claim accuracy, citation entailment, coverage, actionability, completion, cost, and
   latency across task types under matched budgets.
5. **Make artifact provenance complete.** Always register the lead/canonical report,
   explicitly add `derives-from` links, and update automatic lineage beyond historical
   `__a`/`__b` suffixes to the current provider suffixes or, preferably, producer
   metadata.
6. **Offer architecture profiles rather than a single fixed swarm.** Start with
   `quick`, `ensemble`, `decompose`, and `audit`; reserve the most expensive stages for
   broad or high-stakes work and keep a strong solo path for sequential tasks.
7. **Replace consensus thinking with evidence-weighted adjudication.** Keep researchers
   blind until their artifacts exist, preserve minority findings, and resolve conflicts
   by independent support and source quality rather than report count.
8. **Add a typed settled/quorum wait to SASE.** Let a lead proceed transparently after
   terminal provider failures when a configured success threshold is met, while keeping
   strict successful waits as the default.
9. **Consider data-driven runtime fan-out only after fixed-profile experiments justify
   it.** It is the most plausible larger SASE feature, but current primitives are enough
   to validate nearly all of the proposed quality gains first.
