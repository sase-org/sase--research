---
title: "Making research_swarm produce stronger evidence and better decisions"
create_time: 2026-10-01T17:16:15+00:00
updated_time: 2026-10-01T17:16:15+00:00
status: draft
tags: [research-swarm, multi-agent, evidence-quality, sase]
researcher: cdx
swarm_id: research.37
---

# Making research_swarm produce stronger evidence and better decisions

The most valuable improvement is to turn the swarm's reports into an inspectable body of evidence, then make the lead explicitly evaluate that evidence before recommending anything. Keep the independent first round. Add a compact claim-and-source contract, a synthesis process that preserves disagreement and unique findings, and a small evaluation set that compares the swarm with a strong single researcher at comparable cost. More agents and more debate are secondary experiments.

Most of this can use existing SASE capabilities. The clearest candidates for new host behavior are explicit result validation and joins that distinguish required research from optional presentation work. These should be generic orchestration capabilities only if simpler plugin-level changes prove insufficient.

## Scope and method

This is an independent report by `research.37.cdx`, researched on 2026-10-01. I did not consult the reports, transcripts, summaries, or findings of this swarm's other researchers. I examined the current plugin source, SASE documentation and selected implementation files, and primary external publications. I did not run a competing swarm, measure research quality, or establish an optimal researcher count. Proposed budgets and evaluation sizes below are starting points for experiments.

The executable catalog reported `research_swarm` and `research` as coming from `plugin:sase_research_artifacts`; their catalog bodies exactly matched the opened plugin checkout. Code observations are pinned to:

- SASE: `a35f3e4162d1218891b87fc5fc37e31ce5106bc1`.
- `sase-research-artifacts`: `a21dc497ce43f15beec9aa718480fc116183839e`.

This establishes the implementation being analyzed without assuming that a similarly named file elsewhere is active. External findings are evidence about particular systems and tasks, not measured results for SASE. For HiddenBench, ALCE, and DeepResearch Bench II I relied on the authors' publication pages or abstracts; for the scaling study, MAST, and Anthropic engineering articles I also inspected relevant full-text sections.

## What the current swarm already does well

The plugin's [swarm definition](https://github.com/sase-org/sase-research-artifacts/blob/a21dc497ce43f15beec9aa718480fc116183839e/src/sase_research_artifacts/xprompts/research_swarm.md) has a sensible structure: independent provider researchers, a lead that researches gaps and consolidates, and optional infographic and editorial agents. Two researchers are enabled by default; five are supported. Every enabled researcher receives the same request and an explicit prohibition against reading peers' reports or obtaining their findings indirectly.

Keep these properties:

- Invocation-scoped `research.{@1}` names prevent overlapping swarms from stealing each other's dependencies. SASE documents this in its [keyed swarm markers](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/docs/xprompt.md#xprompt-swarms-library-defined-fan-out).
- Researchers write separate files and explicitly register immutable snapshots. The lead uses `wait.artifacts`, matches producer names and existing suffixes, and reads reports through audited artifact references. It rejects ambiguous or missing inputs instead of guessing. This is substantially better than discovering deliverables in transcripts.
- The lead is asked to do additional research on weak evidence, gaps, and disagreements. Consolidation is already more than concatenation.
- Hard-disabled providers are omitted; the template handles a solo lead when no researchers run.
- The linker has a clear editorial boundary: preserve the lead's meaning, introduce no new research, and validate links. It avoids silently changing conclusions during publication.
- Queue weights, model selection, durable artifacts, finalization, and the research tribe already provide useful orchestration and visibility.

The immediate task is to deepen these mechanisms, not replace the architecture wholesale.

## Concrete gaps visible in the implementation

| Observation | Why it matters | Confidence and boundary |
| --- | --- | --- |
| The independent prompts specify separation and file delivery, but no common evidence or claim schema. | The lead must reconstruct support, uncertainty, and source dependence from differently organized essays. | High confidence from the template; the user can supply stronger instructions in a particular request. |
| All researchers receive the whole request with essentially identical research instructions. | Provider diversity can still yield redundant search trajectories and repeated evidence. | High confidence about prompt structure; actual duplication is unmeasured. |
| The lead is told to merge every perspective and resolve conflicts, but has no explicit claim disposition or contradiction table. | Fluent synthesis can erase useful disagreement or include weak ideas merely to represent every researcher. | High confidence about the missing explicit contract; some leads may do this well spontaneously. |
| The linker checks URL reachability and preservation, and is forbidden to change a wrong lead conclusion. | A reachable citation can fail to support a claim; the linker is not a factual verifier. | High confidence; this editorial boundary should remain. See [linker instructions](https://github.com/sase-org/sase-research-artifacts/blob/a21dc497ce43f15beec9aa718480fc116183839e/src/sase_research_artifacts/xprompts/research_swarm.md#L357). |
| Automatic research lineage still recognizes only `__a` and `__b`. | Current `__cdx`, `__cld`, `__grk`, `__mus`, and `__gem` sources are not covered by that filename derivation. | High confidence for this code path; other deliberately authored links may exist. See [lineage implementation](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/src/sase/artifact_links/derive/_research_lineage.py#L8). |
| The template says SASE derives a plan's links from reads. Actual reads provide observational links and suggestion evidence, rather than automatic semantic derivation. | Reading something and deriving a report from it are different relationships. Researchers should not assume lineage is complete after an audited read. | High confidence from [read candidate semantics](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/src/sase/artifact_links/read_candidates.py) and [link suggestions](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/docs/artifact_links.md). |
| Explicit lead registration is conditional on running the linker. | Default publication relies on host capture rather than the same explicit snapshot contract used by workers and the linker. | High confidence; automatic finalizer capture can still preserve the default lead report. This is an asymmetry, not proof of lost output. |
| The lead moves and renames worker files into a chosen directory. | Relative links and attached assets can break; a canonical document path changes while the original snapshot stays stable. | A relocation risk, not an observed failure in this swarm. [Current move instruction](https://github.com/sase-org/sase-research-artifacts/blob/a21dc497ce43f15beec9aa718480fc116183839e/src/sase_research_artifacts/xprompts/research_swarm.md#L286). |
| Every role uses `%q(1.5x, w=0.25)` by default. | Admission treats a deep researcher, lead, and editor alike; queue capacity is not a token, search, or spending budget. | High confidence about authored values; resource adequacy requires measurement. |
| Named waits require successful completion, including the linker's optional image dependency. | One failed image can prevent publication of completed research. A failed researcher also parks the lead. | Documented behavior, not speculation. See [plugin recovery documentation](https://github.com/sase-org/sase-research-artifacts/blob/a21dc497ce43f15beec9aa718480fc116183839e/docs/xprompts.md#L154) and [SASE wait semantics](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/docs/xprompt.md#L2503). |

One additional edge case merits a small contract test: the external `wait` argument is applied to researcher segments, not the solo lead. If every researcher is disabled, the solo lead bypasses that dependency. Whether this is desirable should be made explicit; the current documentation describes it as gating only researchers.

## What the research literature supports

The evidence favors task-specific orchestration, explicit communication, and verification. It does not establish a universal advantage for larger teams.

**Parallel research can help, but spending more compute is a major confound.** Anthropic reports a 90.2% improvement for its multi-agent system over a single Opus 4 on an internal research evaluation, while emphasizing breadth, separate context windows, task decomposition, and high token consumption. Its engineering guidance also stresses clear assignments, effort limits, citation handling, tracing, and direct artifact outputs. This is a vendor's system-specific result, not a controlled estimate of the benefit of SASE's five-provider ensemble. [Anthropic research system](https://www.anthropic.com/engineering/multi-agent-research-system).

**Failures include coordination and verification, not just model weakness.** MAST analyzes over 1,600 traces across seven frameworks and identifies 14 failure modes across system design, inter-agent alignment, and task verification. Examples include repeated work, ignored information, unclear stopping, and absent or incorrect verification. Its heterogeneous task collection does not tell us how often those failures occur in this swarm. It provides a useful diagnostic vocabulary. [MAST paper, revised October 2025](https://arxiv.org/abs/2503.13657v3).

**Task structure and a strong baseline change the answer.** A 2026 controlled study varies coordination while holding tools, task prompts, and compute ceilings constant across 260 configurations. Outcomes depend strongly on the task and single-agent baseline. Preliminary mixed-model experiments do not establish that provider mixing reliably escapes diminishing returns. An important limitation: its independent topology uses synthesis without analytical comparison, unlike SASE's lead. Treat it as a reason to run local ablations, not as a verdict against this design. [Capable language models can outgrow the benefits of collaboration](https://www.nature.com/articles/s42256-026-01268-y).

**Unique information must be surfaced explicitly.** HiddenBench evaluates decision-making with distributed information. Its authors report premature convergence on shared evidence while critical unshared facts remain unexplored, and improvements from structured communication. Its 30.1% distributed versus 80.7% complete-information single-agent accuracy is not an equal-information comparison and should not become a slogan that teams are worse. My inference for SASE is narrower: the lead should explicitly inventory unique evidence before compressing reports. [ICML 2026 HiddenBench paper](https://proceedings.mlr.press/v306/li26ej.html).

**Citations need their own evaluation.** ALCE separates answer correctness, fluency, and citation quality; citations do not guarantee complete support. The practical distinction for this swarm is between a valid URL, a citation supporting a particular claim, and the claim being true. This older benchmark establishes the distinction, not the present error rate of current providers. [ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/).

**Good report evaluation is more granular than “this reads well.”** DeepResearch Bench II uses 132 grounded tasks and 9,430 criteria covering information recall, analysis, and presentation, developed with substantial human review. Its reported performance gap illustrates why holistic prose ratings can miss omissions and weak analysis. Its expert-article tasks are not a complete proxy for SASE design research, and the evaluation method is not infallible. [DeepResearch Bench II, September 2026 revision](https://arxiv.org/abs/2601.08536v3).

**Use complementary graders.** Anthropic's evaluation guidance recommends source groundedness, coverage, source quality, and calibration of model graders against human judgment. A small set of real failures is useful before building a large benchmark. This supports a practical local evaluation loop, with deterministic checks for delivery and references and human review for decision usefulness. [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

## A useful definition of a good research swarm

A good swarm reduces the chance that the user makes a bad decision because relevant evidence was missed, misread, overgeneralized, or lost during synthesis. Its useful output is a supported answer plus a clear account of what remains uncertain and what would change the recommendation.

Separate five dimensions:

| Dimension | What success looks like | A misleading proxy |
| --- | --- | --- |
| Coverage | Important aspects and credible alternatives have been investigated. | Number of queries or pages visited. |
| Grounding | Consequential claims are linked to inspected evidence with appropriate scope. | Number of citations. |
| Reasoning | Recommendations follow from evidence and the user's constraints. | A persuasive narrative. |
| Calibration | The report distinguishes facts, inference, proposal, and unresolved uncertainty. | A confidence score without justification. |
| Operational reliability | Correct artifacts arrive, provenance survives, and optional failures are explicit. | Every agent showing DONE. |

Model independence is not evidence independence. Five models can all find the same vendor article, all cite a secondary article summarizing it, or all infer more than it establishes. Agreement across researchers may be useful as a robustness signal; it is not five independent confirmations of the underlying claim.

The answer should distinguish model agreement, independent retrieval, and independent underlying evidence. For important claims, record the source family: the original experiment, dataset, vendor assertion, documentation version, or code revision. Two publications relying on the same experiment count as one underlying evidentiary family for that claim. Different sources on the same domain can still be independent; different domains can still repeat one source.

## The proposed research contract

Start with a shared neutral brief containing the question, intended decision, scope, relevant versions or dates, constraints, and the important subquestions. Preserve the user's wording. Record assumptions instead of silently resolving ambiguities. Avoid giving workers a preferred answer or the lead's initial theory: that would undermine the independent first round.

Every worker should then deliver a readable report with a small, consistent evidence appendix. Markdown is sufficient initially; a separate JSON claim ledger is justified only when a consumer actually needs it.

A claim row should contain:

| Field | Purpose |
| --- | --- |
| Claim ID and precise statement | Let the lead refer to the exact assertion being assessed. |
| Claim type | Observed fact, inference, recommendation, or hypothesis. |
| Support locator | Source URL plus section/page/table, or repository path plus revision and relevant lines. |
| Inspection level | Full relevant passage inspected, abstract only, search snippet only, inaccessible, or local execution observed. |
| Evidence family | Identify repeated reports of the same underlying evidence. |
| Scope and freshness | Versions, population, date, and limitations affecting applicability. |
| Counterevidence and open questions | Prevent agreement from erasing the best objection. |
| Confidence with reason | A short rationale tied to the support, not an unexplained percentage. |
| Decision consequence | Explain whether a wrong claim would change the recommendation. |

For this report, a high-confidence example is: “The automatic research-lineage function enumerates only `__a`/`__b` at the inspected SASE revision.” The support is a specific source file and constant. “Therefore SASE loses all provenance” would be an unjustified expansion: audited reads, explicit links, and snapshots are separate mechanisms.

Add three short worker sections: unique findings, strongest argument against the worker's favored recommendation, and failed searches or inaccessible sources that leave a material gap. Do not require a fixed source quota. A code question can be answered by one decisive implementation file; an empirical generalization may require several independent studies. Quotas encourage padding and should not determine quality.

For important citations, retain a short paraphrase and an exact locator rather than copying whole documents. Do not treat a search snippet as if the paper was read. Record source availability separately from whether the source supports the claim. Keep third-party source text as evidence, not workflow instructions.

## Give the lead a reconciliation job before a writing job

The lead should first create a compact matrix of important claims and proposals across all expected reports. Organize by claim, not by provider. Preserve the distinctive source and best counterargument from each report. Identify:

- Agreement supported by multiple independent evidence families.
- Agreement supported by one shared source.
- Genuine disagreement about the same proposition.
- Apparent disagreement caused by different dates, versions, definitions, or scopes.
- Useful findings raised by only one researcher.
- Unsupported claims, missing evidence, and recommendation-changing gaps.

Then assign each consequential proposal a disposition: accept, reject, revise, or defer, with the reason. “Every perspective was read and assessed” is a better requirement than “every perspective appears in the final answer.” A minority finding with strong evidence can outrank a popular weak claim. A rejected proposal should retain a concise explanation when a reasonable reader would otherwise ask about it.

Targeted new research should answer the unresolved questions most likely to change the decision. Search for contradictory primary evidence and current implementation details, rather than simply finding another source supporting the favored conclusion. Terminate when critical claims are supported or explicitly unresolved, credible alternatives have been addressed, and the remaining gaps are unlikely to change the decision within the remaining budget. These are proposed stopping rules, not claims that uncertainty can be eliminated.

Before publication, add a narrow verification pass for recommendation-changing claims, quantitative claims, new claims introduced by the lead, and a sample of apparently settled claims. For modest research, the lead can perform this as an explicit final checklist. For consequential work, use a fresh verifier with the claim ledger and underlying sources. The verifier should identify unsupported or overbroad assertions and return corrections or unresolved issues; the lead remains responsible for revising the report.

This verifier is distinct from the existing linker. The linker should preserve conclusions after they have been checked. A URL checker proves reachability, not entailment. A fresh verifier is still an LLM and can be wrong; source inspection and calibrated human spot-checks remain necessary.

## Preserve independence while adding useful specialization

Use mode choices rather than one topology for every request:

| Mode | Suggested pattern to test | Best fit |
| --- | --- | --- |
| Independent replication | Two whole-question researchers and one lead. | Uncertain questions where conflicting interpretations matter. This matches the current default closely. |
| Coverage-oriented research | Two whole-question independent researchers plus workers assigned distinct subquestions or source classes. | Broad questions that can be investigated in parallel. |
| Verification-oriented research | Independent first round, lead reconciliation, then a focused checker. | Decisions where incorrect citations or overgeneralization are costly. |
| Solo research | One researcher with explicit evidence and self-check requirements. | Narrow lookups or tasks with little meaningful parallel work. |

For a five-researcher design task like this one, plausible complementary lenses are implementation inspection, empirical literature, adversarial failure analysis, prior-art alternatives, and practical cost/reliability. These are attention assignments, not rigid personas. Every researcher should still be able to flag evidence outside its lens. Keep some overlap on the core decision so workers can catch each other's omissions after the independent round.

Do not permanently equate a provider with a role. Rotate assignments or compare alternatives; otherwise a role's output quality becomes confounded with its model. Record the resolved model and available tools, not just the requested alias. Diverse tools and source strategies may produce more useful diversity than diverse model names alone.

Continuous peer conversation is a poor default for this workflow: it consumes budget and can erase independence. If testing an additional exchange, make it a bounded, post-report challenge round using specific disputed claims and frozen initial artifacts. Do not launch an unlimited debate that ends when agents agree.

## Existing SASE capabilities to use more deliberately

| Capability already present | Concrete use | Important constraint |
| --- | --- | --- |
| `#research(report_target=...)` | Preallocate a common invocation directory and explicit worker targets, reducing later moves. | Today it is month-relative and expands the month independently; a frozen month/path contract still needs wiring. |
| Immutable snapshots and `wait.artifacts` | Pass exact report identities and use stored snapshots when canonical paths move. | Match producer and report role; do not infer authority from directory scans or artifact list order. |
| `sase_var` structured outputs | Publish a small result envelope with report identity, status, role, and gaps. | Variables are visible metadata with size limits, not storage for report bodies or secrets. |
| Audited artifact reads and typed links | Record consumption; explicitly add final-report `derives-from` worker-report relationships. | `read` is not automatically `derives-from`; semantic lineage needs deliberate evidence. |
| Provider aliases and queue settings | Tune model fallback and admission independently from research effort. | Queue weight is a scheduling signal, not a spending limit. |
| Markdown swarm stages | Add a fixed synthesis/check/publication sequence with scoped IDs and waits. | Existing named waits only release on successful completion. |
| YAML workflow outputs, conditions, and bounded repeats | Handle a genuinely dynamic gap list or deterministic validation stage. | Current parallel steps are fail-fast; YAML is not an existing “collect all failures” join. Parsing also has a text fallback. |
| Named ToolRuns and monitors | Record deterministic report-validation commands; hand off lengthy checks when needed. | A successful tool receipt is execution evidence, not proof that a research conclusion is correct. |
| Research provider metadata | Populate title, timestamps, `status`, and `tags` for discoverability. | Provenance and quality claims still need report-specific metadata and validation. |
| File hooks and the linker | Render and polish the checked canonical report. | The current hook selects ADD events; a later amended report cannot assume automatic PDF regeneration. |

The relevant contracts are documented in [template context and outputs](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/docs/xprompt.md), [workflow outputs and control flow](https://github.com/sase-org/sase/blob/a35f3e4162d1218891b87fc5fc37e31ce5106bc1/docs/workflow_spec.md), and the [research provider and file hook](https://github.com/sase-org/sase-research-artifacts/blob/a21dc497ce43f15beec9aa718480fc116183839e/src/sase_research_artifacts/provider.py).

An illustrative result envelope could be:

```json
{
  "schema_version": 1,
  "swarm_id": "research.<invocation>",
  "role": "cdx",
  "research_outcome": "supported",
  "report_ref": "research:<actual-repo-relative-path>",
  "snapshot_ref": "file:<actual-created-id>",
  "sha256": "<report-content-digest>",
  "scope_gaps": ["No local performance comparison was run"]
}
```

Publish it with the existing `sase var set research_result --json --value-file ...` mechanism after registration succeeds. The consumer should validate that the artifact was produced by the expected run, that its identity and digest agree, and that the role is expected. A free-form output variable is not itself a trusted completion certificate.

Use separate concepts for execution completion, report registration, and research outcome. A successfully delivered report can conclude “inconclusive.” A failed registration is an operational failure even if the report text is excellent. Neither should be hidden behind a generic success boolean.

For lineage, the immediate remedy is explicit `sase artifact link add <final-report-ref> derives-from <worker-report-ref> "<specific derivation reason>"` after targets are stable. Keep links only for sources actually used. The linker can similarly link its published report to the checked lead report. An eventual manifest can generate these relationships deterministically; simply expanding the old suffix tuple is a fragile intermediate fix because custom roles and intermediate `__final` reports complicate filename inference.

## Operational improvements and justified new features

Freeze the invocation's output directory, month, scope, expected roles, and template revision once. Pass repo-relative paths to all workers and subsequent stages. Existing `report_target` provides part of this; the swarm currently does not expose or coordinate it. A deterministic setup step can establish names without drafting substantive conclusions. Prefer writing directly into the final directory over moving completed reports and repairing their relative links afterward.

Register every canonical final report explicitly, including the default path without a linker. Keep human-readable canonical labels and immutable snapshot refs together. This makes consumer behavior consistent and preserves exactly what was assessed even after organization changes.

Add deterministic checks for one primary report per expected producer, correct suffix/role, valid metadata, registration identity, duplicate source records, and local reference integrity. These checks can live in the research plugin and run as normal commands or named tools. They do not require a new general framework. They can verify the delivery contract but cannot determine whether a claim is scientifically sound.

One new capability has a concrete current justification: an explicit host-owned join policy for optional dependencies. Research should not become unpublishable merely because an infographic failed. Possible policies include all required successes, wait for selected dependencies to settle and expose their outcomes, and a declared minimum set of successful research roles. The default successful-wait contract should remain strict.

Such a join must distinguish completed, failed, stopped, timed out, and unknown/lost outcomes; bind to the intended run generation; expose missing reports; apply a deadline; and produce a visibly partial result when permitted. A quorum is a delivery rule, not proof that omitted evidence is irrelevant. Required coverage roles can veto synthesis even if a numerical minimum was reached. Unknown state should never be silently treated as success.

The simpler alternative for images is to publish checked text first and run enrichment separately. If later enrichment changes the report, produce a new registered version and explicit supersession/rendering action, rather than silently mutating an immutable snapshot or relying on the ADD-only hook to rerender it. Test this path before creating a generic settled join solely for presentation.

A second potentially justified feature is a declarative artifact-output contract at a stage boundary: expected primary artifact role, kind, canonical identity, producer run, and optional schema. Prototype validation in the plugin first. Move it into shared SASE backend behavior only after more than one workflow needs it. Per this project's Rust boundary, generic join and output-contract domain behavior belongs in `sase_core`, with thin frontend bindings and the required revision pin updates.

I would defer live peer messaging, a vector search system for research history, a large claim graph, and a new all-purpose research orchestrator. The current artifacts, typed links, variables, and workflows are enough to test the valuable ideas. If targeted second-round research is useful, implement a bounded mode with explicit maximum rounds and per-question assignments before generalizing it.

## Measure improvement before selecting larger teams

Start with roughly 12–20 representative tasks, including code-backed design questions, broad literature synthesis, current factual comparisons, contradictory sources, and questions whose proper answer is uncertainty. Include a synthetic case where only one worker finds a decisive fact; test whether the lead preserves it. Include reused source families to test whether consensus is mistaken for independent corroboration.

For each task, specify a few verifiable critical facts, credible alternatives, important limitations, and what a decision-useful answer should enable. Do not define success as agreeing with a preferred architecture. Grade proposals as well as factual claims: does the recommended change solve the user's problem, use existing features, disclose tradeoffs, and include a practical way to assess it?

Compare a strong single researcher, the current two-researcher default, the current five-researcher configuration, and the evidence-contract variant. Compare both under a similar total resource budget and under their normal defaults; these answer different questions. Track actual token usage or other available capacity measures, elapsed time, source/tool work, and missing cost data. Subscription capacity reported by `sase usage` should not be mislabeled as per-task token cost.

For an initial study, repeat tasks at least twice to expose gross variability; larger trials are needed for modest effects. Randomize report order, hide provider labels from quality graders where practical, and use human-calibrated judges. Provider-blind presentation can reduce prestige effects without concealing provenance from the audit record. Hold task scope and evidence access fixed where possible. Use a frozen-source subset for reproducibility and a live-web subset for freshness.

Prioritize these measures:

- Support rate for consequential claims and the severity of unsupported claims.
- Coverage of required facts, alternatives, and counterevidence.
- Retention of distinctive correct findings through synthesis.
- Whether genuine contradictions are resolved with evidence or visibly left open.
- Calibration: uncertainty is preserved without turning every conclusion into vague hedging.
- Recommendation usefulness judged by Bryan or another informed reader.
- Registration, lineage, collision, and failure-recovery reliability.
- Quality relative to cost and time, rather than output length.

A useful design goal is Pareto improvement: fewer consequential errors or better coverage at the same cost, or comparable quality with less cost. Do not collapse all measures into a precision-looking score before deciding what tradeoffs the user actually accepts.

Test changes separately: contract alone, contract plus structured synthesis, specialization, verifier, and larger team. Include provider-disable, missing registration, duplicate primary artifact, optional-image failure, month rollover, and concurrent-invocation cases in orchestration validation. Existing plugin tests already cover many rendering and handoff contracts; behavioral research quality needs a separate evaluation layer.

## Ranked improvements to consider

The ranking weighs expected decision-quality benefit, strength of observed evidence, implementation cost, and fit with current SASE. It is my judgment, not a measured ordering.

1. **Add a compact evidence contract to every researcher report.** Require precise consequential claims, inspected source locators, inspection level, evidence families, limits, counterevidence, and explicit inference labels. Start in the shared prompt, with Markdown tables. Expected benefit: much less reconstruction and citation laundering during synthesis. Effort: low to medium. Measure support rate and coverage, not table completeness alone.

2. **Make synthesis explicitly reconcile claims, preserve unique findings, and verify consequential assertions.** Require a disagreement matrix and accept/reject/revise/defer decisions before final prose. Add a bounded fresh verifier for consequential work while leaving the linker editorial. Effort: medium; additional model cost only when justified. Measure minority-finding retention, unsupported high-impact claims, and whether corrections reach the published version.

3. **Build a small local research evaluation set with a strong single-agent baseline.** Compare the current default, five-worker mode, and the evidence-contract variant under comparable budgets and normal defaults. Use human-calibrated grading and repeated trials. Effort: medium and recurring. This prevents subsequent architecture changes from being chosen by output polish or provider count.

4. **Make report provenance explicit and repair the legacy lineage gap.** Add deliberate final-to-source `derives-from` edges; correct the misleading read-to-derivation wording; retain immutable snapshot refs alongside canonical paths. Use a manifest for future generalization rather than assuming modern suffixes trigger legacy derivation. Effort: low for the prompt/link fix, medium for a general contract. Measure whether every actual consolidation input is navigable from the final report.

5. **Standardize artifact delivery and small result envelopes across all stages.** Register the default lead report as well as linker outputs; expose primary report role, snapshot identity, research outcome, and scope gaps through `sase_var`; validate against `wait.artifacts`. Effort: low to medium. Measure delivery ambiguity, registration failures, and recoverability after renames.

6. **Offer complementary research modes while preserving the independent first round.** Keep two whole-question researchers as a conservative starting point; assign additional workers distinct source classes or subquestions for broad tasks. Rotate roles across providers. Effort: low to medium. Measure marginal unique correct evidence and final quality per added worker.

7. **Stop optional presentation failures from blocking completed research.** First test publishing checked text before enrichment. If optional joins are needed more generally, add an explicit host policy exposing terminal outcomes and partial coverage without weakening default `%wait`. Effort: medium to high for generic backend behavior. Measure publication after image failure and truthful reporting of missing required research.

8. **Preallocate one invocation directory and freeze path, month, and scope metadata.** Wire the existing `report_target` capability into the swarm, avoid moving worker assets, and test collisions and month boundaries. Effort: low to medium. Measure broken relative references and misassociated artifacts across concurrent runs.

9. **Make effort and admission proportional to the task and stage.** Introduce small, standard, and thorough research presets with clear stopping criteria and bounded follow-up work; tune queue weights using observed pressure rather than treating all roles identically. Treat budgets as soft instructions until enforcement exists. Effort: medium. Measure quality, elapsed time, and actual resource consumption together.

10. **Use bounded gap-driven follow-up and deterministic publication checks before adding general orchestration machinery.** Spend a second round only on recommendation-changing gaps; reuse YAML conditions and bounded repeats when a dynamic process is needed, accounting for fail-fast semantics. Validate metadata and local links deterministically, then retain the linker's meaning-preservation checks. Effort: medium. Measure gap closure and publication defects; defer a larger framework until repeated limitations justify it.
