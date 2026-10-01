# Improving the `#research_swarm` XPrompt Swarm

**Date:** 2026-10-01 · **Researcher:** mus (independent swarm member) ·
**Subject:** `#research_swarm` as defined in
`sase-research-artifacts` (`research_swarm.md`, 461 lines, checked at linked
checkout) plus SASE host machinery it runs on.

## Bottom line

The swarm's pipeline is sound — parallel independent researchers, artifact
snapshots as handoff, a lead that consolidates, an optional linker that
publishes — but its researchers are five identical prompts, not a team. Every
researcher receives the same request with no division of labor, no method
guidance, no output contract, and no pointer to SASE's own knowledge and
tooling. The lead then absorbs all of that variance in a single pass and fails
closed if any one report is missing. The gap between this and the best-known
external reference design (Anthropic's multi-agent research system) is almost
entirely in *delegation, contracts, and evaluation* — not in SASE machinery,
most of which already exists and is simply not invoked by the template. The
highest-value changes are: assign each researcher a distinct angle, give
researchers a short shared charter (method + output contract + SASE tooling),
restore the lost critique agent, and add a small eval loop. Details and ranking
at the end.

## Method and sources

- Read the full `#research_swarm` template source (`research_swarm.md`, all 461
  lines) and its sibling xprompts (`research.md`, `research/more`,
  `research/prompt`, `research/image`) in the `sase-research-artifacts` plugin,
  plus the plugin's `AGENTS.md`, `default_config.yml`, and `CHANGELOG.md.
- Read the swarm-expansion host machinery
  (`src/sase/agent/xprompt_swarm.py`, 360 lines) and the relevant reference
  memory (`xprompts.md`: directives, swarm expansion, launch semantics).
- Inspected git history of the template (`git log -S`, `git show 59fdf94`) to
  verify the critique-agent history firsthand.
- Primary external source: Anthropic, ["How we built our multi-agent research
  system"](https://www.anthropic.com/engineering/multi-agent-research-system)
  (Jun 2025), fetched and read directly. Confirmed figures: Opus-4 lead +
  Sonnet-4 subagents beat single-agent Opus 4 by 90.2% on their internal
  research eval; token use explains ~80% of BrowseComp variance; multi-agent
  runs cost ~15x chat tokens, so they must earn it.
- Prior swarm outputs used only as process evidence (output sizes, layout,
  published structure), not for topic content: e.g. the 202610
  `openai_harness_engineering_vs_sase` run kept five drafts (10–44 KB each) plus
  a 44 KB consolidated report and a published canonical file.

I did not consult any peer report from this swarm.

## How the swarm works today

One Jinja template renders 8 segments: five near-identical researcher segments
(cdx/cld/grk/mus/gem, each gated on its provider being hard-enabled), a lead
segment (`.final`, waits on all researchers, reads their artifact snapshots via
`wait.artifacts`, moves drafts into `<month>/<name>/`, writes the
consolidated report), and conditional image/linker segments. Researchers each
run `{{ prompt }} #research(suffix=<own>)`, i.e. the identical user prompt plus
write-and-register instructions. The lead does its own gap research inline and
synthesizes everything in one turn.

## Findings

### 1. Five identical prompts is duplication, not a swarm

Every enabled researcher gets byte-identical instructions apart from the suffix.
Provider diversity is real but weak: different labs' models trained on largely
overlapping data, browsing the same web, still share failure modes (same
SEO-dominated sources, same misreadings). Anthropic's central delegation lesson
applies verbatim: vague identical briefs ("research the semiconductor
shortage") produced subagents that duplicated each other's searches with no
division of labor. Their fix was to *teach the orchestrator to delegate* — each
subagent gets an objective, an output format, tool guidance, and clear task
boundaries. `#research_swarm` currently does none of this; its researchers
differ in provider only. Angle diversity (assign lenses: codebase internals,
external prior art, adversarial critique, SASE-feature fit, cost/UX) would buy
more independence than provider diversity does, and the two compose.

### 2. Researchers are denied the guidance the lead gets

The lead and linker segments instruct `sase artifact read` usage, link
validation via `curl`, anchor conventions for pandoc, and exact file layouts.
Researcher segments contain none of: consult project memory (`sase memory
read`), open repos through the repo workflow, register vs. move semantics,
source-quality standards, claim verification, or even a target length. This
asymmetry shows in output variance: in the prior 202610 harness run, drafts
ranged from 10 KB to 44 KB. Length variance is a proxy for contract variance,
and the lead pays for all of it at synthesis time. A compact shared
"researcher charter" block — method heuristics, SASE tooling pointers,
citation expectations, verification rule — rendered once into every researcher
segment would cost a few dozen tokens per member and remove the largest source
of synthesis friction.

### 3. No output contract, so synthesis is manual and lossy

Researchers are never told what shape to return. The lead must reconcile five
free-form reports with different structures, granularities, and implicit
confidence levels. Anthropic's subagents return condensed findings to the lead
(the compression function); that only works because the lead specified what
condensation looks like. A minimal contract — bottom line first, numbered key
findings, evidence links per claim, an explicit confidence/open-questions
section, and whatever closing the requester asked for (this very request's
"ranked list" lived only in the user prompt, invisible to the template) —
would make consolidation near-mechanical. A `format`/`brief` template input
could carry per-dispatch closing requirements instead of relying on the user
to append them to the prompt.

### 4. The lead is a single fat pass with no second round

The lead reads up to five full reports *and* does its own original research in
one context, then ships. Anthropic's lead instead loops: synthesize, identify
gaps, spawn follow-up subagents or refine strategy, repeat until sufficient.
SASE already owns the primitive for round two (`research/more`: extend a report
filling gaps), but the swarm never uses it. Moving gap research out of the
lead's context into one bounded follow-up round would both shrink the lead's
context and make gap coverage explicit and auditable.

### 5. Fail-closed on missing researchers

If the registered artifacts do not identify exactly one report per expected
suffix, the lead must "stop and report the missing or ambiguous input instead
of guessing." One failed researcher out of five therefore kills the whole
dispatch, discarding four good reports. Anthropic's reliability lesson runs
the other way: resume from where the work is, degrade gracefully, let the
agent adapt. Proceeding with N−1 reports while flagging the gap (and
optionally re-dispatching just the missing angle) strictly dominates
aborting. Partial-report tolerance is a small template change with large
robustness payoff.

### 6. No evaluation loop of any kind

Anthropic's recipe: start with ~20 real queries immediately (large effects show
up in small samples), grade with a single LLM-as-judge call on a rubric
(factual accuracy, citation accuracy, completeness, source quality, tool
efficiency), and keep humans in the loop for what automation misses (their
humans caught SEO-farm source bias). `#research_swarm` has no eval: no sample
query set, no rubric, no judge, no record of which dispatches produced good
finals. Every improvement proposed here would be argued on taste rather than
measured. A `research/eval` harness with a dozen pinned past requests and an
LLM-judge rubric is the highest-leverage *new* capability, and it is also the
one that makes all other improvements compound.

### 7. The critique agent was lost, not retired

History verifies this precisely: commit `59fdf94` ("add opt-in critique
agent") added `critique`/`critique_model` inputs and a `<clan>.critique`
agent writing `<name>__critique.md` without touching the lead report. The
later `bf8deb9` re-scaffold (the 0.2.0 plugin rename) dropped it; no commit
removes it deliberately and the current 461-line template contains no
"critique" string at all. Whether or not the critique design was ideal,
losing an opt-in verification stage by accident is a regression. Restoring it
— ideally wired so the lead must disposition each critique point
(accept/rebut) rather than merely filing the file beside the report — closes
the current gap where *nobody validates claims*: the linker validates links,
not truth.

### 8. Cost is unshaped: flagship effort everywhere, always all members

Every researcher defaults to `@xhigh`-class concrete models; the lead and
linker default to `@xlarge`. Anthropic's winning configuration was a strong
lead with *cheaper* workers (Opus lead, Sonnet subagents), and multi-agent
output costs ~15x chat, so it must earn its keep per query. The swarm has no
complexity routing: a trivia question and a deep investigation both launch
every enabled researcher at maximum effort. A `researcher_effort` input (or a
cheaper default with opt-up), plus documenting when a solo `#research` beats
the full swarm, would cut the expected token bill substantially. Relatedly,
each researcher redundantly rediscovers the same repo layout and conventions;
a small shared read-only context pack (repo map, key paths, glossary pointers)
preserves independence of *conclusions* while deleting 5x duplicated
*discovery*.

### 9. Template maintainability drags future changes

The five researcher blocks are ~40 lines of near-identical Jinja differing
only in suffix/provider/model; the peer-list logic already uses
`rejectattr`, proving a loop over `researchers` can generate them. At 461
lines with fivefold duplication, every charter/contract improvement in this
report costs 5x edits and risks drift (which is plausibly how the peer-list
wording stays correct today only by care). Refactoring to one loop is
low-risk *because* the plugin carries render tests (the critique commit
message itself attests "renders are byte-identical" as the invariant) — the
tests pin behavior while the structure simplifies, which is exactly the
condition under which to do it.

### 10. Small robustness gaps: stems, clarification, conflict resolution

- **Stems are nondeterministic.** Each researcher invents its own filename
  stem; the lead renames everything later. Two concurrent swarms in one month
  directory can collide, and the rename step is pure toil. Deriving the stem
  once (from a slug input or the clan id `{@1}`) and passing it into every
  segment eliminates the class.
- **No clarification step.** An ambiguous prompt yields N divergent
  interpretations and an incoherent synthesis. Routing ambiguous requests
  through a questions handoff *before* dispatch (or documenting that callers
  should) is cheaper than reconciling after.
- **No conflict-resolution rule.** When researchers disagree, the lead has no
  stated policy; the path of least resistance is majority vote. Evidence
  weighting (re-check the sources, prefer primary over secondary, say so in
  the final) should be explicit — Anthropic's judge rubric puts factual and
  citation accuracy first for the same reason.

## SASE features the swarm could use but doesn't

Already available, merely uninvoked by the template: reference-memory reads
for researchers (`sase memory read`), the repo workflow for cross-repo reads,
task beads for discovered follow-ups, `research/more` for round two,
`research/prompt` for prompt-shaped requests, the questions handoff for
ambiguity, the effort ladder for cost shaping, per-segment `%summary` for
TUI observability, and hold/queue controls beyond the current uniform
`%q(1.5x, w=0.25)`. The `%wait`/`wait.artifacts` handoff itself is the
template's best-used SASE feature and should be the model for the rest: host
machinery doing the plumbing, prompt text doing only what only text can do.

## Ranked list of improvements to consider

Ranked by expected research-quality gain per unit of implementation effort,
highest first:

1. **Assign each researcher a distinct angle.** Add an `angles` input (or a
   lead-authored decomposition step) so members investigate complementary
   lenses instead of the identical prompt. This is the single largest
   quality lever, directly supported by Anthropic's delegation findings.
2. **Give researchers a shared charter.** One rendered block in every
   researcher segment: method heuristics (start wide, then narrow; evaluate
   sources), SASE tooling pointers (memory read, repo workflow, artifact
   read), citation expectations, and a verify-before-claim rule.
3. **Mandate an output contract.** Bottom line, key findings, evidence links,
   confidence/open questions, plus a per-dispatch `format` input carrying
   closings like "ranked list" so they aren't lost in user prose.
4. **Restore the lost critique agent — and make the lead disposition it.**
   Re-add `critique`/`critique_model` (lost accidentally in `bf8deb9`), with
   the lead required to accept-or-rebut each point in the final.
5. **Degrade gracefully on missing reports.** Proceed with N−1 researchers,
   flag the gap, optionally re-dispatch only the missing angle. Never discard
   good reports because one member failed.
6. **Build the eval loop.** A pinned set of past requests plus an LLM-judge
   rubric (accuracy, citation accuracy, completeness, source quality, tool
   efficiency) so every other change here can be measured rather than argued.
7. **Add a bounded round-two for gaps.** Use `research/more`-style follow-ups
   driven by the lead's gap analysis instead of stuffing gap research into
   the lead's own context.
8. **Shape cost.** Cheaper default researcher effort (strong lead, economical
   workers), a documented solo-vs-swarm rule, and a shared read-only context
   pack to kill 5x redundant discovery.
9. **Refactor the template to a researcher loop.** One Jinja loop over
   `researchers` replacing five duplicated blocks; the existing
   byte-identical render tests make this safe and make all of the above
   cheaper to land.
10. **Close the small robustness gaps.** Deterministic filename stems passed
    to all segments; a pre-dispatch clarification step for ambiguous prompts;
    an explicit evidence-over-votes conflict-resolution rule for the lead.

## Caveats

- Angle assignment trades some independence for coverage; keep at least the
  lead (and optionally one unbriefed researcher) free to catch what the
  angles miss, or the swarm converges on the decomposition's blind spots.
- Cheaper researcher models trade per-report depth for budget; validate
  against the eval loop (item 6) before changing defaults, not after.
- I verified template contents, history, host machinery, and the Anthropic
  figures above by direct inspection; effort/cost rankings are judgment, not
  measurement — which is itself an argument for item 6.
