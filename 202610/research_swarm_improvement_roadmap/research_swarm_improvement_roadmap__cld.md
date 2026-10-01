# Making `#research_swarm` produce better research

- **Question.** How can `#research_swarm` produce better research? How can it make better
  use of what SASE already provides, and which new SASE features, if any, are justified?
  The report ends with a ranked list of improvements.
- **Date.** 2026-10-01. Researcher `cld`, in a five-researcher swarm.
- **Evidence base.**
  - `sase-research-artifacts` at `a21dc49`, which owns `#research_swarm` and the other
    `#research*` xprompts.
  - `sase` at `a35f3e4162`, which owns launch preprocessing, `%wait`, `sase var`, and
    the provider launchers.
  - A read-only analysis of the run archive: 634 `research.*` agent runs, forming 138
    swarms from 2026-07-09 to 2026-10-01 (`~/.sase/projects/*/artifacts/ace-run/`).
    The current swarm, `research.37`, is excluded.
  - Prior SASE research, read with `sase artifact read`:
    [`research_swarm_linker_agent`](../../202609/research_swarm_linker_agent/research_swarm_linker_agent.md),
    [`multi_agent_collaboration_strategy`](../../202609/multi_agent_collaboration_strategy/multi_agent_collaboration_strategy.md),
    and [`xprompt_swarm_goals`](../../202609/xprompt_swarm_goals.md).
  - External work on multi-agent research systems, listed under [Sources](#sources).

## Bottom line

**Keep the shape of the swarm.** Researchers work independently, never talk to each
other, and hand their reports to one lead. The best external evidence supports exactly
this design:

- Majority voting explains most of the gains attributed to multi-agent debate.
- A central coordinator holds error amplification to 4.4×, against 17.2× when agents run
  independently with no coordinator.

Do not add debate rounds, messaging between researchers, or more default researchers.

**The weak points are what flows through that shape.**

- **Researchers get no brief.** Each one receives the user's raw prompt, an independence
  preamble, and file-writing instructions. That is all. There is no output contract, no
  guidance on sources or tools, and no instruction to check SASE's own prior research.
  Anthropic's research system shows that this is where delegation quality comes from.
- **The lead is told to merge, not to validate.** Deep-research agents fail mainly at
  evidence integration and verification, not at understanding the task. The lead
  prompt asks it to "merge the strongest findings", and has no verification protocol.
- **Nothing measures quality.** No signal shows whether a swarm, or any one researcher,
  is getting better. The five-researcher `rsa` default has never been tested against the
  two-researcher `rs` default.

**Fix two verified defects first.**

1. **SASE's prompt formatter corrupts the lead's input.** At launch, prettier rewrites
   the `__` in report labels and paths to `**`. This affected all 39 Era-B lead prompts
   and all 4 linker prompts (see [the details](#the-handoff-list-is-corrupted-at-launch)).
   The same bug corrupts any prompt with two `__` tokens in one paragraph.
2. **Codex researchers cannot search the web.** `codex exec` is launched without web
   search. Zero of 105 `cdx` researcher runs made a web call.

Most of the improvements are prompt changes in the plugin and need no new SASE
machinery. Two SASE changes are clearly justified: the prettier fix and codex web
access. A third, an opt-in failure-tolerant wait, is defensible. The
[ranked list](#ranked-improvements) is at the end.

## How the swarm works today

`src/sase_research_artifacts/xprompts/research_swarm.md` authors eight segments in one
clan, `research.<N>`:

| Segment | Default | What it does |
| --- | --- | --- |
| `.cdx`, `.cld` | on | Codex and Claude researchers (`codex/gpt-6.1-sol@xhigh`, `claude/opus@xhigh`). |
| `.grk`, `.mus`, `.gem` | off | Grok, Muse, and Gemini researchers. The user's `rsa` snippet turns all three on. |
| `.final` | on | The lead (`@xlarge`, currently `opus@xhigh`). It waits on every researcher and reads their registered reports through `wait.artifacts` and `sase artifact read`. |
| `.image` | off | Infographic. Forks the lead. |
| `.linker` | off | Restructures and link-checks the lead's `__final.md` into the published `<name>.md`. |

Each researcher segment is the same 23 lines, repeated five times. They differ only in
the provider suffix. Each one says three things:

1. Who the peers are.
2. Stay independent of them.
3. `{{ prompt }} #research(suffix=<short>)`. The `#research` xprompt only says where to
   write the file and how to register it.

The prompts come almost entirely from the user's own snippets:

- `rs` is `#research_swarm:: $1`.
- `rsa` adds `gemini`, `grok`, `muse`, and `image`.
- `dor` adds "…helping me decide the best way to implement this? End your analysis with
  a recommended solution."
- `dorr` adds a "critique this plan" block to `dor`.

## What 138 past swarms show

Era A runs from 2026-07-09 to 2026-09-20: codex and claude researchers, the lead, and
image. Era B runs from 2026-09-21 onward, when mus, gem, and grk were added. It covers 41
swarms.

| Signal | Value |
| --- | --- |
| Swarms per week | 2–29; 29 in the week of 2026-09-21 |
| Era-B researcher mix | All five in 18 swarms; cld+mus+gem in 13; other mixes in 10 |
| Prompt type (n=135, rough) | 93 design or decision for a SASE feature; 18 plan critiques; 10 debugging; 9 external surveys; 6 other |
| Prompt length | Median 624 characters; p90 2,427 |
| Researcher duration, median | cdx 16.5 min; cld 14.8 → **28.4** min (Era A → B); grk 14.1; mus 9.1; gem 11.2 |
| Slowest researcher in Era B | cld in 27 of 40 swarms. Its tool calls rose from a median of 83 to 217. |
| First launch to lead done, Era B | Median 46.7 min; p90 86.8 |
| Researchers that used **no** web | cdx **105 of 105**; cld 74 of 109; grk 19 of 22; mus 34 of 39; gem not observable (no `tool_calls.jsonl`) |
| `sase artifact read` share of cdx tool calls | 2% |
| Lead `sase artifact read` calls, Era B | Median 4; 27 of 37 leads read at least one per researcher |
| Failures (25 total) | 18 commit, finalizer, or workspace problems; 6 provider problems such as weekly limits or expired OAuth; **0 research-quality failures** |
| Lead never ran because a researcher failed | 4 swarms; research.0d sat parked about 9 hours |
| User kills | 72, all from the TUI; 33 of them image agents |
| Median tokens per run (claude family) | cld 4.6M input (mostly cached), 46.8k output; lead 2.4M / 31.6k. Codex and agy record no usage. |

What these numbers mean:

- **Most prompts are SASE design decisions.** For those, the main evidence is code,
  docs, beads, and prior research, and the web matters less. But the `dorr` critique
  prompt ("Would you take a different approach?") calls for prior art. That is where
  researchers with no web access cost quality.
- **The swarm already fails gracefully on quality and badly on plumbing.** Every
  observed failure was infrastructure. When a researcher fails, its lead stays parked
  until someone intervenes.
- **The added researchers are cheap and fast; whether they help is unknown.** mus and
  gem finish in 9–11 minutes. No data shows whether they contribute findings that the
  lead keeps.

## Two defects to fix first

### The handoff list is corrupted at launch

Here is the lead prompt research.34.final actually received, from its
`workflow-*-main_prompt.md`:

```text
- wait_name=research.34.cdx label=research:202610/master_ci_failure_accumulation**cdx.md
  source_path=/home/bryan/.../research/202610/master_ci_failure_accumulation**cdx.md
  path=/home/bryan/.sase/artifacts/agents/gh_sase-org**sase/2026.../...**cdx-6fb73c1492e6.md
```

**The mechanism.** `sase/llm_provider/preprocessing.py` runs launch preprocessing in a
fixed order:

1. Step 5 renders top-level Jinja, which fills in the swarm's `{% raw %}`
   `wait.artifacts` loop.
2. Step 6 runs `format_agent_prompt_markdown`, which is prettier.

Prettier reads `a__cdx.md … b__cdx.md` as `__strong__` emphasis and normalizes it to
`**`. SASE's `_unescape_prettier_underscores` repairs the escape `\_\_` (one `__` alone)
but cannot repair this. I reproduced it with the installed prettier 3.8.1.

**The impact.**

- Every Era-B lead, and every linker, receives labels and paths that do not exist. Only
  the `ref=file:explicit:…` field survives intact.
- The linker's step 1 says "find exactly one entry … whose label has the form
  `research:<YYYYMM>/<name>/<name>__final.md`; if not, stop". A literal-minded model
  would stop.
- The leads have coped by improvising, which is fragile.

**This is a general SASE bug.** Run this sentence through the same step:

> Compare topic__cdx.md with topic__cld.md

The agent receives `topic**cdx.md with topic**cld.md`. The same applies to any path that
contains `gh_sase-org__sase`.

**Fix in the plugin now (minutes).** Render every field as inline code. Prettier leaves
code spans alone; I verified this.

```jinja
- wait_name=`{{ a.wait_name }}` label=`{{ a.label }}` source_path=`{{ a.source_path }}` path=`{{ a.path }}` ref=`{{ a.ref }}`
```

Apply this to both loops: the lead's and the linker's.

**Fix in SASE.** Stop prettier from rewriting emphasis in agent prompts. There are three
options:

- Format only the authored prompt, before runtime Jinja fills in machine values.
- Protect `__…__` spans the same way fenced blocks are protected.
- Drop the formatting step from the launch path, and keep it as an editor action.

### Codex researchers cannot search the web

- **The launch command.** `sase/llm_provider/codex.py` launches `codex exec --model …
  --dangerously-bypass-approvals-and-sandbox --json …`. It passes no `--search` flag and
  no web-search config. `~/.codex/config.toml` sets none either.
- **The capability exists.** `codex --help` documents `--search` ("Enable live web
  search").
- **It is never used.** Zero of 105 `cdx` researcher runs made a web call; about 10 used
  `curl` instead. None of 177 codex session logs since 2026-09-25 contains a
  `web_search` item. That count includes non-research runs.

Part of the cost is hidden by the prompt mix, since most prompts are about SASE itself.
But one of the two default researchers is blind to prior art, vendor docs, and papers.
This very prompt asks what makes a good research swarm, which is a question about
external work.

**Recommendation.**

- Enable web search for researcher launches. Use whichever switch `codex exec` 0.159
  honors (`--search`, or a `-c` web-search override). Ideally expose it as a provider
  capability an xprompt can request, so web access is not tied to `SASE_LLM_*_ARGS`
  environment variables.
- Normalize codex `web_search` items in `_tool_call_codex.py` so the use is visible.
- Add `tool_calls.jsonl` capture for agy. Today gem's research is a black box.
- If web access was turned off on purpose, for cost or safety, record why in a decision
  note and tell the `cdx` researcher it has no web access.

## What makes a research swarm good

| Principle | Evidence | `#research_swarm` today |
| --- | --- | --- |
| **Independent drafts, then aggregate. Vote; don't debate.** | Majority voting accounts for most of the gains credited to multi-agent debate. Debate is a martingale: on average it does not move belief toward the truth ([Choi et al., NeurIPS 2025](https://arxiv.org/abs/2508.17536)). | ✅ Strict independence, no peer contact. Keep it. |
| **The aggregator must validate, not just merge.** | Independent multi-agent systems amplify errors 17.2×; centralized ones contain this to 4.4× because the orchestrator is a validation bottleneck ([Google Research, 2025](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)). Deep-research agents fail at "evidence integration, verification, and reasoning-resilient planning", not at task comprehension ([FINDER/DEFT](https://arxiv.org/abs/2512.01948)). | ⚠️ The lead is told to "merge the strongest findings … resolve conflicts". It has no verification protocol. |
| **Diversity has to be engineered. A different vendor is only partial independence.** | Models agree on about 60% of the cases where both err, and larger models are more correlated, across providers too ([Kim et al., ICML 2025](https://arxiv.org/abs/2506.07962)). In about 25% of split decisions the minority held the right answer ([Minority Sentinel, 2026](https://arxiv.org/abs/2606.29270)). Mixing in weaker models often lowers quality; Self-MoA beat mixed MoA by 6.6% on AlpacaEval 2.0 ([Li et al.](https://arxiv.org/abs/2502.00674)). | ⚠️ Every researcher gets an identical prompt, so diversity comes only from the vendor. `rsa` adds a flash-tier model (gem) without measuring it. |
| **Delegate with an objective, an output format, tool and source guidance, and boundaries.** | Anthropic's research system: each subagent needs "an objective, an output format, guidance on the tools and sources to use, and clear task boundaries" ([Anthropic, 2025](https://www.anthropic.com/engineering/multi-agent-research-system)). | ❌ Researchers get the raw prompt only. |
| **Ground claims and check that citations support them.** | Anthropic adds a dedicated citation pass. FACT scores citation accuracy. Factored verification (Chain-of-Verification) cut hallucinations 50–70% ([Dhuliawala et al.](https://aclanthology.org/2024.findings-acl.212/)). | ⚠️ The linker checks that links resolve, not that sources support the claims. Reports carry no claim ledger. |
| **Don't let the judge favor itself.** | LLM evaluators recognize and favor their own generations ([Panickssery et al., NeurIPS 2024](https://arxiv.org/abs/2404.13076)). | ⚠️ The lead (`opus@xhigh`) is the same model as the `cld` researcher. |
| **Measure on a small set of real queries.** | Anthropic started with about 20 real queries and an LLM judge scoring factual accuracy, citation accuracy, completeness, source quality, and tool efficiency. | ❌ No eval exists. 138 past prompts are available for one. |
| **Scale effort to the question.** | Anthropic: one agent for fact-finding, 2–4 for comparisons, more for complex research. | ✅ Roughly, through the user's choice of `rs` or `rsa`. |
| **Scope before searching.** | OpenAI Deep Research asks clarifying questions; Gemini shows an editable plan ([OpenAI](https://help.openai.com/en/articles/10500283-deep-research-faq), [Google](https://blog.google/products/gemini/tips-how-to-use-deep-research/)). STORM discovers perspectives before asking questions ([Shao et al.](https://arxiv.org/abs/2402.14207)). | Partial. The user's prompts are already specific (median 624 characters), so a separate scoping step is [not recommended yet](#considered-and-not-recommended-now). |

## Recommended improvements

### Give researchers a delegation contract

**What.** Append a fixed method and report contract to every researcher segment. Here is
a draft:

```text
How to research:
- Start from what SASE already knows. Search prior research with
  `sase plan search --kind research "<keywords>"`, read the relevant hits with
  `sase artifact read`, and read the memory notes your topic touches with
  `sase memory read`. Build on earlier conclusions, and say where you disagree.
- Ground every claim your recommendation rests on in a source you checked this
  turn: `path:line` in a checkout opened with `/sase_repo`, a primary doc, spec,
  or paper, or a command and its output. Label anything you did not check as
  inference.
- Use web search for anything outside the checkouts: prior art, other tools,
  vendor docs, and papers. Prefer primary sources to blogs and summaries.
- Spend your effort where the decision is uncertain.

Write the report in this order, with unnumbered headings:
1. Bottom line: the answer and your recommendation in at most five sentences,
   with your confidence.
2. Findings, most decision-relevant first, each with its evidence.
3. Alternatives you weighed, and why they lost.
4. Risks, costs, and open questions, each with what would settle it.
5. Claim ledger: a table of the 5–10 claims your recommendation rests on
   (claim | evidence | checked or inferred | confidence).
Keep it as short as the evidence allows.
```

**Why.**

- This is the delegation recipe from Anthropic's research system.
- It matches the research README's own standard ("record the question, evidence,
  alternatives, and a clear recommendation").
- It turns SASE's corpus into an input. 32 past prompts pointed at an earlier report by
  hand, yet researchers almost never run `sase artifact read` (2% of cdx calls). Reads
  made through `sase artifact read` also record `read-by` links automatically, so the
  lineage graph grows for free.
- The claim ledger gives the lead aligned, comparable units to vote on and verify.

**Add a `kind` input as well.** It would be a typed enum input
(`auto | decide | critique | survey | debug`, default `auto`) that swaps section 1 and
section 4 of the contract:

| Kind | Section 1 asks for | Section 4 adds |
| --- | --- | --- |
| `decide` | Decision criteria plus an options matrix | — |
| `critique` | A verdict on the plan, with adjusted requirements called out | — |
| `debug` | The root cause, with reproduction evidence | Prevention |
| `survey` | The landscape, with source quality | — |

The prompt mix is 93 decide, 18 critique, 10 debug, and 9 survey, so `auto` can infer
the kind from `dor` or `dorr` phrasing. Each snippet could also pin the kind:
`dor` → `decide`, `dorr` → `critique`.

**Implement it once.** The researcher preamble is copied five times, and the copies have
already drifted. Every researcher is told not to read "the other researcher's report",
even with four peers. Move the shared body into a helper xprompt, such as
`#research/_member(short=cdx, peers="cld,grk")`, whose `peers` value is rendered by
Jinja in the swarm. This works because inline xprompt references inside an xprompt
swarm body expand later, in the agent runner (`docs/xprompt.md`, "Rules and
Limitations"). Each segment then shrinks to its directives and one reference. Do this
first, since every other researcher-prompt change gets cheaper.

### Make the lead a validator, not a merger

**What.** Keep the lead's report-identification and file-moving steps. Replace step 2
("research the request yourself…") and step 4 ("merge the strongest findings…") with
this protocol:

```text
1. Before opening any report, write down for yourself the questions a complete
   answer must settle and the evidence that would settle each. Judge the reports
   against that list, so that no single report's framing becomes yours.
2. Read every report (as today). Map the load-bearing claims: which reports assert,
   contradict, or omit each one.
3. Treat agreement as weak evidence: these models share training data and make
   correlated mistakes. Treat a claim made by one report as a lead to check, not an
   outlier to drop. Weigh claims by their evidence, never by which provider wrote
   them.
4. Verify against primary sources, one claim at a time and without relying on the
   reports' wording: every claim the recommendation depends on, every disagreement,
   and every single-report claim that would change the recommendation if true.
5. Write the report: bottom line and recommendation first; findings; alternatives;
   a "Where the reports disagreed" table with your ruling and its evidence;
   confidence; what would change the recommendation; open questions. Use unnumbered
   headings. Credit unique findings to the report that found them.
```

**Why each step.**

- **Step 1** is the anti-anchoring step from the removed critique agent, and the cheapest
  part of it worth keeping.
- **Step 2** makes the majority signal explicit, because voting is where the
  multi-agent gain comes from.
- **Step 3** guards against correlated errors and minority truth. Weighing claims by
  evidence also blunts self-preference: the lead is the same model as `cld`.
- **Step 4** is factored verification, which is what the centralized-validation result
  rewards.
- **Unnumbered headings in step 5** fix the doubled section numbers in the Highlights
  PDF even when the linker is off. 69 of 88 consolidated reports in 2026-09 had
  hand-numbered headings. This gives up a byte-identical default render, deliberately.

The strongest past syntheses I read already work this way. Both
[`research_swarm_linker_agent`](../../202609/research_swarm_linker_agent/research_swarm_linker_agent.md)
and
[`multi_agent_collaboration_strategy`](../../202609/multi_agent_collaboration_strategy/multi_agent_collaboration_strategy.md)
rule on each disagreement in a table and check the contested claims against code. This
change makes that the norm instead of luck.

### Measure before adding researchers

**What.** Two cheap instruments.

1. **A contribution ledger.** The lead ends with `sase var set contributions --json
   '{...}'`. For each suffix it records:
   - `unique_kept`: findings in the final report that only this researcher had;
   - `errors_caught`: this researcher's claims that turned out wrong;
   - `recommendation_adopted`: a boolean.

   Output variables are already stored in `agent_meta.json` and shown in the TUI's
   OUTPUT VARIABLES section. A one-page script can sum them across swarms. No new SASE
   feature is needed.
2. **A small eval set.** Take 15–20 past prompts across the four kinds, re-run variants,
   and compare the final reports:
   - pairwise and blind;
   - judged by a model from a different vendor than the lead;
   - against Anthropic's rubric: factual accuracy, citation accuracy, completeness,
     source quality, and tool efficiency;
   - with "actionability" added;
   - backed by the user's own preference on a few pairs.

**Why.** There is no evidence today that `rsa`'s five researchers beat `rs`'s two. Self-MoA
and the correlated-errors results make that a real question, not a formality. gem is a
flash-tier model, and mus carries a trains-on-your-data advisory. The ledger answers the
question over time at almost no cost. The eval set lets you test prompt changes, such
as the contract or lenses, before changing defaults. Fill the observability gaps
first: codex web calls and agy tool calls are invisible today.

### Decorrelate researchers with lenses

**What.** Add an opt-in `lenses: bool`, default `false`. Every researcher still answers
the whole question and gives its own bottom line, which keeps the voting signal. Each
also gets one primary emphasis to go deeper on:

- what the codebase and SASE's records show;
- prior art and external practice;
- the strongest case against the obvious answer;
- cost, operations, and migration.

Assign lenses by position in Jinja's `researchers` list, so any subset of providers
still covers the most important lenses first.

**Why.** It is STORM's perspective-guided questioning, applied across agents. It attacks
correlated errors directly: different evidence paths fail differently, while different
vendors reading the same files fail alike. Leave it off by default and A/B it on the
eval set. Lenses can also cut coverage of the main question, and only measurement will
show which effect wins.

### Let the lead proceed when a researcher fails

**What.** This needs a new, opt-in SASE `%wait` mode. Something like
`%wait(research.N.cdx, …, settle=true)`, which releases once every dependency is
terminal, whether it completed or failed. `wait.artifacts` already lists only what
exists. The lead's step 1 then changes from "stop on a missing report" to "proceed with
the reports present, and name the missing researchers in the report".

**Why.**

- Four swarms never got a lead because a researcher failed, and one sat parked for 9
  hours.
- Seven "Wait dependency can never self-resolve" notifications involved research clans.
- With five researchers, one provider limit or expired OAuth token stalls the whole
  swarm.

The prior collaboration research concluded that failure propagation should be
opt-in per wait, not a new default, and this proposal follows that. Wait semantics live
in core, so the change belongs in `sase-core` with a binding, per the Rust-core
boundary. Use it on the lead only. The linker's wait on the image agent should stay
strict, because that strictness is the publication barrier.

### Smaller items

- **Fix the lineage deriver.** Bead `sase-15r` is still open:
  `derive_research_swarm_lineage` recognizes only the retired `__a` and `__b` suffixes,
  so no `derives-from` links exist for current swarms.
- **Finish the linker rollout.** Only 5 linker runs exist, all of them under the `**`
  corruption. After the backtick fix, run the planned diff-based fidelity check, then
  decide on the default.
- **Name the goal's claimer when goals reach swarms (G4).** The lead, or the linker when
  it runs, should claim. The image agent never should. With `image=true` today, the
  host's role rule would hand the claim to image or linker
  ([`xprompt_swarm_goals`](../../202609/xprompt_swarm_goals.md), gap 1).
- **Hand off to action, optionally.** 13 swarms produced 26 forked follow-ups
  (`.f0`, `--plan`, `--code`). The lead could `sase var set next_step="<one-line plan
  prompt>"`, so the TUI shows a ready follow-up. A gate on every swarm would be noise.

## Considered and not recommended now

- **Debate rounds or messaging between researchers.** Debate adds little over voting
  and invites conformity. Independence is the swarm's best property.
- **A brief or scoping agent before the researchers.** It adds a serial step. It gives
  every researcher the same framing, which raises error correlation. The user's prompts
  are already specific. The lead's step-1 checklist and the contract's "bottom line plus
  open questions" cover most of the benefit. Revisit if the eval shows researchers
  answering the wrong question.
- **Starting the lead on a quorum to beat the straggler.** The straggler is usually
  `cld`, which may be a top contributor; the ledger will tell. Research runs
  asynchronously, and a median 47 minutes to the lead's report is not the binding
  constraint.
- **Reviving critique as a companion file.** It failed because its output never reached
  the reading path: one real run, and excluded from the PDF. Verification belongs inside
  the lead and the published report. If the eval later shows the lead missing errors,
  add a cross-vendor verifier whose corrections the linker must integrate. Do not add
  another side file.
- **More default researchers.** Wait for the contribution ledger.

## Ranked improvements

| Rank | Improvement | Where | Effort | Why this rank |
| --- | --- | --- | --- | --- |
| 1 | **Backtick the `wait.artifacts` fields** in the lead and linker loops; file and fix the prettier `__`→`**` rewrite in launch preprocessing | plugin (minutes); `sase` | XS + S | A verified correctness bug in every Era-B handoff, and a general prompt-corruption bug |
| 2 | **Researcher delegation contract**: method, source and tool guidance, prior-research search, report structure, claim ledger. Add a `kind` enum. Factor the five segments into one helper first. | plugin | S–M | The biggest gap against established practice; nothing new is needed in SASE |
| 3 | **Lead-as-validator protocol**: checklist first, agreement map, weigh evidence not provider, factored verification, disagreement table, unnumbered headings | plugin | S | Integration and verification are where research agents fail; the lead is the validation bottleneck |
| 4 | **Web search for codex researchers**, made observable; agy tool-call capture | `sase` providers | S | One of two default researchers is blind to the web; two providers are invisible to measurement |
| 5 | **Contribution ledger** via `sase var set`, plus a 15–20-prompt blind eval set | plugin + script | S + M | Turns default choices (`rs` vs `rsa`, models, lenses) into decisions backed by data |
| 6 | **Opt-in lenses**, A/B-tested on the eval set | plugin | S | Cheapest way to decorrelate researchers; unproven here, so measure first |
| 7 | **Opt-in failure-tolerant `%wait`** for the lead | `sase-core` + plugin | M | Recovers about 3% of swarms that otherwise stall; the only new SASE feature on the list |
| 8 | **Fix lineage derivation** (`sase-15r`) | `sase` | S | Restores `derives-from` links for every current swarm |
| 9 | **Finish the linker rollout** after rank 1 | plugin | S | The PDF is what the user reads; current linker evidence is tainted by the bug |
| 10 | **Goal claimer rule for swarms** (G4) and an optional `next_step` output variable | `sase` / plugin | S | Cleaner signals and handoffs once goals reach swarms |

## Open questions

- **Was codex web search left off on purpose?** For example, for cost or for
  prompt-injection exposure. If so, rank 4 becomes "tell the researcher" plus a decision
  note.
- **What key does the `agents` namespace use for keyed swarm names?** Rank 5 reads the
  ledger offline, which is safe either way. A Jinja table inside the lead or linker
  prompt would need this checked: `_agent_key_for_output_variables` uses the template
  base only for `@` templates.
- **Does self-preference matter at this scale?** The eval set can test it cheaply: blind
  the lead to suffixes in one variant, using neutral labels and moving files by label
  afterwards.

## Sources

- Anthropic, "How we built our multi-agent research system" (2025):
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- Google Research, "Towards a science of scaling agent systems" (2025):
  <https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/>,
  paper <https://arxiv.org/abs/2512.08296>
- Choi, Zhu, Li, "Debate or Vote" (NeurIPS 2025): <https://arxiv.org/abs/2508.17536>
- He et al., "Minority Sentinel" (2026): <https://arxiv.org/abs/2606.29270>
- Kim, Garg, Peng, Garg, "Correlated Errors in Large Language Models" (ICML 2025):
  <https://arxiv.org/abs/2506.07962>
- Li et al., "Rethinking Mixture-of-Agents" (Self-MoA): <https://arxiv.org/abs/2502.00674>
- "How Far Are We from Genuinely Useful Deep Research Agents?" (FINDER/DEFT):
  <https://arxiv.org/abs/2512.01948>
- DeepResearch Bench (RACE/FACT): <https://arxiv.org/abs/2506.11763>
- Dhuliawala et al., "Chain-of-Verification Reduces Hallucination" (ACL Findings 2024):
  <https://aclanthology.org/2024.findings-acl.212/>
- Panickssery, Bowman, Feng, "LLM Evaluators Recognize and Favor Their Own Generations"
  (NeurIPS 2024): <https://arxiv.org/abs/2404.13076>
- Shao et al., "STORM" (NAACL 2024): <https://arxiv.org/abs/2402.14207>
- OpenAI, "Deep research in ChatGPT" FAQ: <https://help.openai.com/en/articles/10500283-deep-research-faq>
- Google, "Tips for Gemini Deep Research": <https://blog.google/products/gemini/tips-how-to-use-deep-research/>
- SASE code:
  - `sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md`
  - `sase/src/sase/llm_provider/preprocessing.py` (steps 5–6)
  - `sase/src/sase/file_references.py` (`format_agent_prompt_markdown`)
  - `sase/src/sase/llm_provider/codex.py` (the `codex exec` argv)
  - `sase/src/sase/agent/output_variable_context.py`
  - `sase/src/sase/artifact_links/derive/_research_lineage.py`
  - `sase/docs/xprompt.md` (waits, output variables, xprompt swarms)
