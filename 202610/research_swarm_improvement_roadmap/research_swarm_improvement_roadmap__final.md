# Improving `#research_swarm`: better evidence, better synthesis, better use of SASE

- **Question.** How can `#research_swarm` produce better research? How can it use more
  of what SASE already provides, and which new SASE features are truly justified? The
  report ends with a ranked list of improvements.
- **Date.** 2026-10-01. Written by the lead, `research.37.final`, from five independent
  reports plus its own verification.
- **Inputs.**
  - The five reports:
    [cdx](research_swarm_improvement_roadmap__cdx.md),
    [cld](research_swarm_improvement_roadmap__cld.md),
    [grk](research_swarm_improvement_roadmap__grk.md),
    [mus](research_swarm_improvement_roadmap__mus.md), and
    [gem](research_swarm_improvement_roadmap__gem.md).
  - The plugin (`sase-research-artifacts` at `a21dc49`), `sase` at `a176e70328`, and
    `sase-core`.
  - The run archive for this swarm (`research.37`) and for a concurrent swarm
    (`research.36`).
  - Codex session logs.
  - A delegated check of all 14 external citations against their abstracts or full
    text.

## Bottom line

**Keep the shape.** Independent researchers who never talk, followed by one lead who
reads everything, is the design the evidence supports:

- Majority voting explains most of the gains credited to multi-agent debate.
- Centralized validation contains error amplification much better than independent
  agents with no checker.
- Strict independence is the swarm's best property. Do not add debate rounds, messaging
  between researchers, or more default researchers.

**What needs fixing is what flows through that shape.**

- **Researchers get no brief.** Each one receives the raw question and a write path,
  with no method, no report contract, and no prompt to reuse SASE's prior research.
- **The lead is told to merge, not to adjudicate.** Nothing requires it to verify the
  claims the recommendation rests on, or to preserve a correct finding that only one
  researcher made.
- **Nothing measures whether any of this works.** Two of the five providers are partly
  or wholly invisible to telemetry.

**Fix one verified defect first.** At launch, SASE's prettier step rewrites `__` to `**`
in every lead and linker handoff list. This report's own prompt arrived with labels like
`research:202610/…orchestration**cdx.md` and paths containing `gh_sase-org**sase`.

Most improvements are prompt changes in the plugin. Only one new SASE feature is
justified: a *settle* join that lets a lead proceed when a researcher fails. It should
reuse the settle semantics SASE already has in typed admission, not invent a new kind of
`%wait`. The [ranked list](#ranked-improvements) is at the end.

## What this swarm demonstrates about itself

This dispatch is itself a measurement. It asked five researchers the same question with
identical briefs.

| Researcher | Wall-clock | Words | Recorded web use | Notable unique contribution |
| --- | --- | --- | --- | --- |
| mus | 7.3 min | 1.8k | none; its `search` tool is local file search | Time-boxing; golden expansion tests over the toggle matrix |
| gem | 10.5 min | 4.1k | not observable: agy writes no `tool_calls.jsonl` (bead `sase-15o`) | Decision records and beads from research; deterministic verifier tool |
| grk | 15.7 min | 4.3k | none recorded, yet it cites five external papers | Static per-suffix briefs; unused frontmatter (82 of 91 canonical 2026-09 reports lack `status:`, which I confirmed) |
| cdx | 20.5 min | 4.9k | `web__run` search and open, invisible to `tool_calls.jsonl` | Evidence families; claim-ledger fields; compute-matched evaluation design |
| cld | 30.2 min | 4.6k | 9 searches, 4 fetches, 1 subagent | **The prettier corruption**; an analysis of 138 past swarms |

Five patterns stand out.

- **Convergence was high, and it rested on one shared source.** Every report found the
  identical briefs, the missing report contract, the lead parking when a researcher
  fails, and the unused `sase var`. All five reached those points by reading the same
  `research_swarm.md`. That is five model agreements on one evidence family, not five
  confirmations.
- **The most consequential finding came from one researcher.** Only cld found the
  prettier corruption, which I reproduced. A lead that weights claims by how many
  reports make them would have ranked it last. This is the swarm's own case of minority
  truth.
- **A single-source claim was half wrong.** cld reported that codex researchers cannot
  search the web, with "0 of 105" cdx runs making a web call. Codex can search: this
  swarm's cdx ran `web__run` searches and opened anthropic.com, arXiv, nature.com, PMLR,
  and the ACL Anthology. The calls are nested inside codex's code-mode `exec` tool, which
  SASE's normalizer (`_tool_call_codex.py`) does not surface. Across September and
  October codex logs, 15 of the 35 cdx-researcher sessions I could identify used
  `web__run`. The real defects are invisibility and discretionary use, not missing
  capability.
- **A researcher that skipped prior research contradicted a recorded decision.** gem's
  fourth-ranked fix is to drop the linker's wait on the image agent. The 2026-09 linker
  research accepted that strictness on purpose: Highlights fires once, on ADD, so the
  published `<name>.md` must appear after the infographic exists. gem also calls the
  linker's "publish without image" fallback unreachable. It is reachable: it covers an
  image agent that *completes* without producing a PNG.
- **Cost and latency are lopsided.** The lead could not start until cld finished, 30
  minutes in. cld alone read 11.4M cached input tokens and wrote 65k output tokens.
  grk read 2.1M cached tokens, and mus about 2.9M input tokens in total. Codex and agy
  record no usage. Nobody can yet say whether the three extra researchers paid for
  themselves.

A concurrent swarm adds an operational lesson. `research.36` launched an hour earlier
with a `prompt` argument of `:`. Only its cdx segment received the question text; the
other four researchers and the lead received `: #research(suffix=…)` or a "Research
request" of `:`. At 13:53, `research.36.cld` was still running at about 105 minutes and
786 tool calls, and its lead was parked behind it. Eight agents launched on a degenerate
prompt, and nothing stopped them.

## Defects to fix first

### Prettier corrupts the handoff list at launch

**The mechanism.** cld traced it, and I reproduced it with prettier 3.8.1 and
`format_agent_prompt_markdown`.

- Launch preprocessing renders top-level Jinja (step 5), which fills the swarm's
  `{% raw %}` `wait.artifacts` loop.
- It then runs prettier (step 6), in `src/sase/llm_provider/preprocessing.py:236-242`.
- Prettier reads `a__cdx.md … b__cdx.md` as `__strong__` emphasis and rewrites it to
  `**`.
- `_unescape_prettier_underscores` only undoes `\_` escapes, so it cannot repair this.

**The scope.** Only the `ref=file:explicit:…` field survives intact. Inline code spans
are untouched: I confirmed that backticked fields pass through prettier unchanged.

**The fix.**

- **Plugin, minutes.** Render every field in both loops (the lead's and the linker's) as
  inline code:
  `` wait_name=`{{ a.wait_name }}` label=`{{ a.label }}` … ``.
- **SASE.** Stop prettier from rewriting machine-filled values. Three options:
  - Format the authored prompt *before* runtime values are substituted.
  - Protect `__…__` spans the way fenced blocks are protected.
  - Drop formatting from the launch path and keep it as an editor action.

The bug is general: any agent prompt with two `__` tokens in one paragraph is affected,
including any path that contains `gh_sase-org__sase`. cld filed it as bead `sase-1dx`,
and I added an independent reproduction.

### Telemetry cannot see two providers' research

- **Codex.** `web__run` calls inside codex's `exec` tool never reach
  `tool_calls.jsonl`. This telemetry made cld's report wrongly conclude that codex has
  no web access.
- **agy (gem).** It writes no `tool_calls.jsonl` at all, which is bead `sase-15o`.
- **grok.** It recorded no web calls, yet the five 2026 papers it cites are real and
  support its claims as stated. Telemetry cannot tell whether it read them this turn or
  recalled them.

Any quality measurement depends on fixing this. Normalize codex `web__run` items as
WebSearch and WebFetch (new bead `sase-1e2`), fix `sase-15o`, and have researchers state how deeply they
inspected each source; see the claim ledger below.

## What makes a research swarm good

The delegated check confirmed every external claim below at its source. Caveats are
noted where the report wording overreached.

| Principle | Evidence | Today |
| --- | --- | --- |
| **Independent drafts, then aggregate. Vote or select; don't debate.** | Majority voting accounts for most of the gains attributed to debate, and debate is a martingale over beliefs ([Choi et al., NeurIPS 2025](https://arxiv.org/abs/2508.17536)). With budget matched, debate ties or loses to self-consistency sampling at 3.4× the tokens ([Ferreira et al., 2026](https://arxiv.org/abs/2609.35875)). | ✅ Strict independence. |
| **The aggregator must validate.** | Trace-level error amplification is 17.2× in independent multi-agent setups and 4.4× with a centralized coordinator ([Kim et al., Google, 2025](https://arxiv.org/abs/2512.08296)). The same group's [Nature MI study](https://www.nature.com/articles/s42256-026-01268-y) is one evidence family with it, not a second: across 260 configurations with compute held constant, the single-agent baseline was the strongest predictor of whether collaboration helps. Deep-research agents fail at "evidence integration, verification, and reasoning-resilient planning", not task comprehension ([FINDER/DEFT](https://arxiv.org/abs/2512.01948)). | ⚠️ The lead is told to "merge the strongest findings". |
| **Model diversity is not evidence independence.** | On one leaderboard dataset, models agree on 60% of the items both get wrong; larger models are more correlated, even across providers ([Kim et al., ICML 2025](https://arxiv.org/abs/2506.07962)). In about one in four split decisions, the minority is right ([Minority Sentinel, 2026](https://arxiv.org/abs/2606.29270)). Teams converge prematurely on shared evidence while unshared facts go unexplored ([Li et al., ICML 2026](https://proceedings.mlr.press/v306/li26ej.html)). | ⚠️ Identical briefs. All five reports here leaned on one source file. |
| **Select per claim and union coverage; don't blend.** | In single-round generate-then-select pipelines, judge-based selection beats MoA-style synthesis, which was preferred over baseline in 0 of 42 tasks ([Maryanskyy et al., 2026](https://arxiv.org/abs/2603.20324)). An aggregator that reads full traces recovers correct minority steps that voting discards ([Beyond Consensus, 2026](https://arxiv.org/abs/2605.29116)). Mixing in weaker models can hurt: Self-MoA beats mixed MoA by 6.6% on AlpacaEval 2.0 ([Li et al.](https://arxiv.org/abs/2502.00674)). | ⚠️ Not required of the lead. |
| **Delegate with an objective, output format, tool and source guidance, and boundaries.** | Anthropic's research system ([Anthropic, 2025](https://www.anthropic.com/engineering/multi-agent-research-system)). | ❌ Raw question plus a write path. |
| **A reachable citation is not a supporting citation.** | Answer correctness, fluency, and citation support are separate measurements ([ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/)). Anthropic adds a dedicated CitationAgent. | ⚠️ The linker checks that URLs resolve, not that they support claims. |
| **Compute is the main confound.** | In Anthropic's BrowseComp analysis, token usage alone explains 80% of performance variance, and three factors explain 95%. Multi-agent runs use about 15× the tokens of chat. | ❌ No comparison of `rs` with `rsa`, or with a strong single agent. |
| **Measure on about 20 real queries.** | Anthropic started with about 20 queries drawn from real usage. Granular rubrics catch omissions that holistic ratings miss ([DeepResearch Bench II](https://arxiv.org/abs/2601.08536)). | ❌ No eval. 138 past prompts are available. |
| **Don't let the judge favor itself.** | LLM evaluators recognize and favor their own generations ([Panickssery et al., NeurIPS 2024](https://arxiv.org/abs/2404.13076)). | ⚠️ The lead (`@xlarge`, Opus) is the same model family as cld. This report is an instance; see [open questions](#open-questions). |
| **Discover perspectives before writing.** | Perspective-guided questioning in the pre-writing stage improved organization by 25 points (absolute) and coverage by 10 ([STORM](https://arxiv.org/abs/2402.14207)). | Partial: users' prompts are specific (cld measured a median of 624 characters). |

A good swarm, in one sentence, lowers the chance that the user decides badly because
evidence was missed, misread, overgeneralized, or lost in synthesis. It does this by
separating coverage, grounding, reasoning, calibration, and operational reliability, as
cdx's framework does.

## Recommendations

### Give researchers a delegation contract, written once

All five reports call for this. Move the shared researcher body, now copied five times,
into a Jinja macro above the first `---` or a local helper xprompt. The copies have
already drifted: every researcher is warned about "the other researcher's report", even
with four peers. Then add the following.

- **Method.**
  - Start from what SASE already knows. Run `sase plan search --kind research
    "<keywords>"` and `sase artifact read` the hits you use. The 2026-09 linker decision
    that gem contradicted was one search away.
  - Use primary sources: code at a pinned revision, documentation, papers, and measured
    data.
  - Use web search for prior art and external practice.
  - Spend effort where the decision is uncertain.
- **A time box.** A complete partial report beats a perfect missing one. cld is the
  straggler in most swarms: 27 of 40 in cld's archive data, and in this one.
- **Report shape.** Use unnumbered headings, in this order:
  - bottom line and confidence;
  - findings, most decision-relevant first;
  - alternatives and why they lost;
  - risks and open questions, each with what would settle it;
  - unique findings and the strongest argument against your own recommendation.
- **A compact claim ledger.** A table of the 5–10 claims the recommendation rests on.
  Take its fields from cdx's design:
  - **claim**;
  - **type**: fact, inference, or recommendation;
  - **locator**: URL plus section, or `path:line` at a revision;
  - **inspection level**: full text, abstract, snippet, or recalled; this exposes the
    grok ambiguity above;
  - **evidence family**;
  - **confidence with a reason**.

  Skip source quotas, which encourage padding.
- **Frontmatter.** `status: draft` and topic `tags`. These feed the Research pane's
  status facet and grouping, which the plugin declares but almost nobody fills.
- **A small `sase var` digest** for indexing and telemetry: `summary`, `claims[]`,
  `open_questions[]`. The report stays the contract, and the var only accelerates.
  - Key spelling for keyed names is unverified. The docs map `%id:research.@.final` to
    `agents["research.final"]`, but how `research.{@1}.cdx` keys is untested.
  - gem's literal `"@1"` key is certainly wrong.
  - In the lead template, iterate `agents.items()` instead of constructing keys. Render
    it inside the same `{% raw %}` block as `wait.artifacts`: bead `sase-1dd` reports
    launch failures when prompts with `input:` use agent-run Jinja variables directly.

Put the method and report shape in `#research` itself, so solo runs and
`#research/more` inherit them. Fold in what `#research/prompt` already asks for.

### Make the lead an adjudicator, not a merger

Replace "research the request yourself…" and "merge the strongest findings…" with a
protocol:

1. **Before opening any report, write the questions a complete answer must settle.** This
   is the cheapest anti-anchoring step, and it preserves what the removed critique agent
   was meant to do.
2. **Map the load-bearing claims by claim, not by provider.** Classify each one:
   - agreed, with several independent evidence families;
   - agreed, but resting on one shared source;
   - a genuine disagreement;
   - an apparent disagreement caused by different versions or scopes;
   - unique to one report.
3. **Weigh evidence, not votes.** Treat a single-report claim as a lead to check, not an
   outlier to drop. In this swarm that rule surfaces the prettier bug and catches the
   codex-web error.
4. **Verify against primary sources.** Check every claim the recommendation depends on,
   every disagreement, and every unique claim that would change the recommendation if
   true.
5. **Write the report.**
   - Bottom line first.
   - A "where the reports disagreed" table with rulings and the deciding evidence.
   - Accept, reject, revise, or defer each consequential proposal.
   - Credit unique findings to the report that found them.
   - Use unnumbered headings: hand-numbered headings double-number in the Highlights
     PDF.
6. **Record provenance.** Run `sase artifact link add <final> derives-from <draft>` for
   each draft actually used, and set `status: final`.

The best past leads already work this way. cld found this pattern in the
`research_swarm_linker_agent` and `multi_agent_collaboration_strategy` syntheses. Making
it explicit turns luck into the norm. For consequential questions, add an optional
**cross-vendor verifier** that runs before publication and returns corrections the lead
must integrate, rather than writing a side file nobody reads. Keep it separate from the
linker, which must stay an editor that preserves the lead's meaning.

### Measure before changing defaults

- **A contribution ledger.** The lead ends with `sase var set contributions --json …`,
  recording per suffix:
  - `unique_kept`: findings in the final report that only this researcher had;
  - `errors_caught`: this researcher's claims that turned out wrong;
  - `recommendation_adopted`.

  These values persist in `agent_meta.json` and appear in the TUI, so a short script
  can sum them across swarms. For example, this swarm gives cld one unique finding kept
  and one error caught, and gives gem one error caught.
- **A 15–20-prompt eval set.** Sample across the prompt mix: design decisions, plan
  critiques, debugging, and surveys. Include:
  - a case where only one researcher can find the decisive fact;
  - a case where the "consensus" rests on one shared source.

  Compare four variants:
  - a strong single researcher;
  - `rs` (two researchers);
  - `rsa` (five researchers);
  - the contract-plus-adjudicator variant.

  Run each comparison twice: compute-matched, and at normal defaults. Judge pairwise
  and blind with a model from a different vendor than the lead, and add Bryan's own
  preference on a few pairs. Score:
  - support rate of consequential claims;
  - coverage;
  - retention of unique correct findings;
  - calibration;
  - usefulness of the recommendation;
  - cost.
- **Prerequisite.** Fix the telemetry gaps first, or the cost and tool-use columns are
  fiction.

### Stop one failure from stranding a swarm

**Today.**

- A named `%wait` releases only on a `"completed"` outcome (`docs/xprompt.md:2509`).
- Four past swarms never got a lead because a researcher failed; one sat parked for
  about 9 hours (cld's archive data).
- The user killed 33 image agents from the TUI. Each such kill now parks the linker when
  `image=true`.

**Now: prompt and plugin.**

- **Add a recovery runbook to the lead and linker docs.** A later successful run of the
  same name releases the wait. Otherwise, kill the waiter and relaunch it without the
  dead dependency.
- **Add a degenerate-prompt guard** for the `research.36` failure: an empty or
  punctuation-only `prompt` should stop the swarm, not launch eight agents.
  - The cheapest version is a Jinja check that renders a refusal.
  - Better is a non-empty validation for `text` inputs in SASE; today only `agent`
    inputs validate as non-empty.

**Later: one justified feature, smaller than the five reports assumed.** Every report
proposed a new settle or optional mode for `%wait`. SASE already has those semantics in
typed admission:

- A wait on an *external* agent resolves once that agent's `done.json` exists, whatever
  the outcome. The outcome reaches `%if::` predicates as `waited_outcomes[]`
  (`src/sase/agent/launch_admission_runtime.py:437-458`; sase-core `condition.rs`).
- A user's TUI or `sase run` launch of `#research_swarm` never takes that path. Typed
  admission is chosen only when the *raw* prompt contains `%if` or `%proc`
  (`src/sase/main/query_handler/_launch.py:281`;
  `src/sase/agent/direct_typed_launch.py:140`).

So the feature is an extension, built in `sase-core` per the Rust-core boundary:

- Logical waits on in-plan *agent* units resolve on terminal `done.json`, not on launch.
- Swarm waits can opt into settle semantics.
- `waited_outcomes` reaches the dependent's Jinja (for example, `wait.outcomes`), so the
  lead can name any researcher that failed.

Use it on the lead only. The linker's wait on the image agent stays strict.

**A risk to test now.** Within one typed plan, `%wait:X` on a sibling agent becomes a
Logical wait (`plan_resolution.rs:89-98`). It resolves once X is *eligible or launched*
(`admission.rs:594-603`), and the dispatched prompt carries no `%wait` line
(`agent_unit_dispatch_prompt`, `admission.rs:448-515`). Open bead `sase-11k` records the
same defect for proc units. `typed_launch_units` is enabled on this machine. If my code
reading is right, an *agent-initiated* `#research_swarm` started through LaunchApproval
would start its lead before the researchers finish. I did not reproduce this end to end.
Test it before relying on agent-launched swarms. I recorded this on `sase-11k` and as a
discovered issue on epic `sase-s6`.

### Write drafts where they belong, and record lineage explicitly

- **Pass `#research(report_target=…)` from the swarm.** Researchers then write straight
  into a dispatch-scoped directory, instead of the month root where the lead has to move
  them.
  - This dispatch's five researchers chose four different stems.
  - 12 orphaned drafts still sit at the 2026-09 month root.
  - Moving drafts breaks relative links: I had to fix three `../202609/` links in the
    cld report after moving it.
- **The trade-off is naming.** A default of `research-{@1}` is ugly but needs no input.
  An optional `name=` gives a readable directory. Freeze the month once in the swarm's
  Jinja, because `#research` evaluates `$(date +%Y%m)` separately in each agent, which
  breaks at a month boundary.
- **Prefer explicit lineage to filename inference.** The lead writes `derives-from`
  links. Fixing `sase-15r` (the deriver still keys on `__a`/`__b`) is still worth doing
  for older reports. Bead `sase-17s`, which projects awaits links for agent-to-agent
  waits, would add host-recorded edges for free.
- **Correct the lead preamble.** It says "SASE derives your plan's links from the
  artifacts you read". Audited reads create `read` evidence and suggestions, not
  `derives-from` lineage (cdx).

### Decorrelate researchers, opt-in and measured

Every report proposes some form of angles, lenses, or briefs. They disagree on the
default and on how to assign them. The resolution:

- **Opt-in** (`lenses: bool = false`) until the eval shows a gain.
- **Every researcher still answers the whole question** with its own bottom line, which
  keeps the voting signal. Each also gets one emphasis:
  - code and SASE records;
  - prior art and external practice;
  - the strongest case against the obvious answer;
  - cost, operations, and migration.
- **Assign emphases by position, not by provider.** That way any subset covers the most
  important ones, and a lens's quality is not confounded with one model. Rotate
  assignments across runs.
- **Use static emphases.** A planner segment, which `%wait`s and then `sase var set`s
  per-researcher briefs, needs no new SASE feature. It adds a serial step and shared
  framing, so try it only if static lenses prove too blunt.

## Where the reports disagreed

| Question | Positions | Ruling |
| --- | --- | --- |
| Can codex researchers search the web? | cld: no, 0 of 105 runs. | **Yes.** It is invisible to telemetry and used in about 15 of 35 sessions. Fix the normalization and tell researchers when to search. |
| Should the linker stop waiting on the image agent? | gem: decouple it. cld and grk: keep it strict. cdx: offer an optional join. | **Keep it strict.** This was a deliberate 2026-09 decision tied to Highlights firing once, on ADD. Add the recovery runbook. |
| Is settle-mode `%wait` a new feature? | All five: yes. | **Partly.** The semantics exist in typed admission, so extend that. It also exposes the possible launch-time resolution bug. |
| Lenses on by default? | gem: on, fixed per provider. cld: opt-in, by position. grk: static per-suffix. mus and cdx: optional. | **Opt-in, by position, rotated, and measured.** |
| A scoping or brief stage before the researchers? | gem: a new `%stage`. grk: a planner segment. mus: a `brief=` input. cld: not yet. | **No new directive.** An optional user `brief=` is cheap. A planner segment only if the eval shows researchers answering the wrong question. |
| Auto-create beads and decision records from research? | gem: yes, up to 3 beads, plus `decision=true`. cld: an optional `next_step` var. | **Opt-in only.** Automatic beads add noise, and decision records must go through `/sase_memory_write` authorization. |
| How large is the lead's input? | gem: 15–30k words, so "lost in the middle". | **19.7k words here.** The lead reads them one tool call at a time. Structure (claim ledgers) helps more than shrinking the input. |
| Do provider defaults matter? | mus: two labs beat one lab twice. grk and cld: gem is flash-tier, mus carries a "trains on your data" advisory. | **Let the contribution ledger decide.** Self-MoA warns against adding weaker proposers just for vendor diversity. |

## Considered and not recommended

- **Debate rounds or messaging between researchers.** Debate's gains reduce to voting at
  matched budget, and debate erodes independence.
- **A new `%stage` directive, or converting the swarm to a YAML workflow.** A
  markdown fan-out with `%wait`, `wait.artifacts`, and `sase var` already expresses
  every proposed shape.
- **A TUI provenance heatmap or consensus scores.** Consensus is not evidence; the
  disagreement table carries the useful part.
- **More default researchers, or starting the lead on a quorum.** Wait for the ledger.
  The straggler (cld) also produced the most consequential finding here.
- **Reviving critique as a companion file.** It failed because nobody read its output.
  Verification belongs inside the lead's reading path.

## Ranked improvements

The ranking weighs expected decision-quality gain, evidence strength, effort, and fit
with SASE. It is a judgment, not a measurement.

| Rank | Improvement | Where | Effort | Why this rank |
| --- | --- | --- | --- | --- |
| 1 | **Backtick the `wait.artifacts` fields** in the lead and linker loops. Fix prettier's `__`→`**` rewrite of launch-time values in SASE. | plugin; `sase` | XS + S | A verified correctness bug in every handoff, including this one. It also corrupts other agent prompts. |
| 2 | **A researcher delegation contract in one shared macro:** method, prior-research search, web guidance, time box, report shape, claim ledger with inspection level and evidence family, `status: draft`. | plugin (`#research_swarm`, `#research`) | S–M | The largest gap against established practice; all five reports agree. |
| 3 | **A lead adjudication protocol:** checklist first, claim map, evidence over votes, verification of load-bearing, disputed, and unique claims, a disagreement table, accept/reject/revise/defer, explicit `derives-from` links, unnumbered headings. | plugin | S | Integration and verification are where research agents fail. This swarm shows the minority-finding risk directly. |
| 4 | **Measurement:** a contribution ledger through `sase var`, a 15–20-prompt eval set against a strong single agent (compute-matched and at defaults, blind, cross-vendor judge). Fix codex `web__run` normalization and agy capture (`sase-15o`). | plugin + script; `sase` | S + M | Turns `rs` vs `rsa`, lenses, and model choices into data-backed decisions. Today, telemetry misled a researcher. |
| 5 | **Failure handling:** a recovery runbook and a degenerate-prompt guard now. Later, a settle join built on typed admission in `sase-core`, including terminal-outcome resolution of in-plan agent waits, with outcomes exposed to the lead. | plugin; `sase-core` + `sase` | XS now; M later | One failed or killed agent strands the swarm today. The only new SASE feature on this list, and smaller than proposed. |
| 6 | **Test agent-initiated swarms under typed admission.** If in-plan agent waits really resolve at launch, fix it with `sase-11k`. | `sase-core` | S to verify | A possible silent correctness bug for any swarm launched by an agent. |
| 7 | **Dispatch-scoped layout and provenance:** `report_target`, a frozen month, an optional `name=`, explicit lineage links, fix `sase-15r`, frontmatter `status`/`tags`. | plugin; `sase` | S–M | Removes the lead's file-clerk work, orphaned drafts, and broken relative links. Makes the corpus navigable. |
| 8 | **Opt-in lenses**, assigned by position and rotated across providers, A/B-tested on the eval set. | plugin | S | The cheapest way to decorrelate researchers, but unproven here, so it waits on rank 4. |
| 9 | **Model-mix decisions from data:** a cross-vendor lead or verifier for consequential runs, whether `rsa`'s extra researchers pay for themselves, and whether gem should be flash-tier as a researcher. | config | S after rank 4 | Self-preference and correlated errors are real, but their size here is unknown. |
| 10 | **Hygiene:** golden expansion tests over the toggle matrix, a deterministic report checker as a named tool (links, headings, registration), CHANGELOG, the "other researcher's" drift, the "derives your plan's links" wording. Opt-in actionability: a `next_step` var, beads via `/sase_new_task` on request, and a goal claimer rule when goals reach swarms. | plugin | S each | Correctness and convenience, not research quality. |

## Open questions

- **How large is self-preference here?** This consolidation was written by Opus, the
  same family as cld. To limit the risk, I checked cld's two headline claims
  independently: one held, and one was half wrong. The eval set can test this directly,
  for example by blinding the lead to suffixes.
- **How did `research.36.grk` produce an on-topic report?** Its prompt was
  `: #research(suffix=grk)`. If it found the question in a sibling's prompt or
  transcript, that is a leak through the independence wall worth closing. I did not
  investigate.
- **Codex web policy.** Should codex researchers be told to search, or should web search
  be an explicit provider capability that an xprompt requests? Its use today is
  discretionary.

## Sources

**External.** All were checked against their source pages on 2026-10-01.

- Anthropic, "How we built our multi-agent research system" (2025):
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- Anthropic, "Demystifying evals for AI agents":
  <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>
- Choi, Zhu, Li, "Debate or Vote" (NeurIPS 2025): <https://arxiv.org/abs/2508.17536>
- Ferreira, Liu, Zheng, "Beyond Symmetric Agents" (2026):
  <https://arxiv.org/abs/2609.35875>
- Kim et al., "Towards a Science of Scaling Agent Systems" (2025):
  <https://arxiv.org/abs/2512.08296>
- Gu, Kim et al., "Capable language models can outgrow the benefits of collaboration"
  (Nature Machine Intelligence, 2026):
  <https://www.nature.com/articles/s42256-026-01268-y>
- Kim, Garg, Peng, Garg, "Correlated Errors in Large Language Models" (ICML 2025):
  <https://arxiv.org/abs/2506.07962>
- He et al., "Minority Sentinel" (2026): <https://arxiv.org/abs/2606.29270>
- Li, Naito, Shirado, "Systematic Failures in Collective Reasoning under Distributed
  Information in Multi-Agent LLMs" (HiddenBench, ICML 2026):
  <https://proceedings.mlr.press/v306/li26ej.html>
- Maryanskyy, Budnikov, Kaliyev, "When Agents Disagree: The Selection Bottleneck"
  (2026): <https://arxiv.org/abs/2603.20324>
- Fadnavis et al., "Beyond Consensus: Trace-Level Synthesis in Mixture of Agents"
  (2026): <https://arxiv.org/abs/2605.29116>
- Li et al., "Rethinking Mixture-of-Agents" (Self-MoA): <https://arxiv.org/abs/2502.00674>
- Zhang et al., "How Far Are We from Genuinely Useful Deep Research Agents?":
  <https://arxiv.org/abs/2512.01948>
- Cemri et al., MAST, "Why Do Multi-Agent LLM Systems Fail?":
  <https://arxiv.org/abs/2503.13657>
- Gao et al., ALCE (EMNLP 2023): <https://aclanthology.org/2023.emnlp-main.398/>
- DeepResearch Bench II: <https://arxiv.org/abs/2601.08536>
- Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations"
  (NeurIPS 2024): <https://arxiv.org/abs/2404.13076>
- Shao et al., STORM (NAACL 2024): <https://arxiv.org/abs/2402.14207>

**SASE, first-party.**

- `sase-research-artifacts`: `src/sase_research_artifacts/xprompts/research_swarm.md`
  and `research.md`.
- `sase`:
  - `src/sase/llm_provider/preprocessing.py` (steps 5–6)
  - `src/sase/file_references.py` (`format_agent_prompt_markdown`)
  - `src/sase/llm_provider/codex.py`
  - `src/sase/llm_provider/_tool_call_codex.py`
  - `src/sase/agent/output_variable_context.py`
  - `src/sase/agent/launch_admission_runtime.py`
  - `src/sase/agent/direct_typed_launch.py`
  - `src/sase/main/query_handler/_launch.py`
  - `docs/xprompt.md` (waits, typed admission, output variables)
- `sase-core`: `crates/sase_core/src/agent_launch/plan_resolution.rs` and
  `admission.rs`.
- Run archive: `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/01/`
  (`research.36.*` and `research.37.*`). Codex session logs under `~/.codex/sessions/`.
- Beads: `sase-1dx`, `sase-1e2`, `sase-15r`, `sase-15o`, `sase-11k`, `sase-17s`,
  `sase-1dd`, and epic `sase-s6`.
- Prior research:
  [`research_swarm_linker_agent`](../../202609/research_swarm_linker_agent/research_swarm_linker_agent.md),
  which records the image-failure coupling decision.
