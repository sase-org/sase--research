# Size-alias pools under a token budget: where SASE's subscription usage goes, and what `@xsmall`…`@xlarge` should be

Researcher B · 2026-09-18 · evidence from `apollo` (the machine this ran on), SASE source at
`master` (`fa61906da0`), and vendor documentation current as of September 2026.

## Bottom line

1. **The plan targets the right mechanism but the wrong setting.** Every SASE launch
   goes through the five size aliases, so they are the right place to act. But the
   data says the budget is not lost by giving small tasks big models. It goes to the
   **implementation tiers (`@medium`, `@small`) running at `xhigh` effort, and to one
   expensive, soon-to-be-retired model.**
   - `codex/gpt-5.5@xhigh`, the Codex member of `@medium`, alone consumed **78% of
     all Codex credits on apollo since Sep 1**, and **91% in the current weekly
     window**.
   - Per token, it costs 25–50% more than GPT-5.6 Sol and 2.5× more than GPT-5.6
     Terra.
   - It leaves Codex on **2026-10-14**.
2. **Load balancing cannot create capacity.** At current cost per launch, demand is
   roughly 1.5–2× what the three subscriptions supply. When one provider drops out,
   the survivors absorb its load and run out faster. After Claude was soft-disabled
   on Sep 17, Codex took ~47 launches/day and went from 0% to 87% of its weekly
   allowance in about 29 hours.
3. **Lower the effort before lowering the model tier.** Vendor data consistently
   finds `xhigh` is past the point of diminishing returns for coding. Anthropic's own
   measurements show Opus 5 at `low`/`medium` *dominates* Sonnet 5 at default: it
   solves more tasks at 30–60% of the cost. Fable 5.1 costs 43% less per solved task
   than the Fable 5 that SASE currently pins.
4. **Change what "fair" means:** fair should be *pace* (each provider's allowance
   lasts until its reset), not equal launch counts. Static weights cannot track
   pace. SASE already has the pieces to do it: usage windows, soft disables, and
   pools that prefer non-soft members.
5. **Recommended defaults** (details in §6):
   - replace gpt-5.5 with Terra/Luna;
   - move Claude's implementation members to Opus at `low`/`medium`;
   - use Fable 5.1 instead of Fable 5;
   - cap effort at each vendor's default except where evidence says otherwise.

   A rough estimate is that this about **halves the token cost per unit of work**.
   That is enough to close most of the gap, but only if a one-to-two-week A/B check
   confirms that quality holds.

## 1. What the size aliases actually control today

These are the mechanics that matter for a budget decision. All were verified in source.

- **Where launches route.**
  - Five aliases, shipped from `src/sase/llm_provider/model_alias_defaults.yml`.
  - Phase and tale sizes route through `@<size>` directly.
  - Launches with no `%model` go to `llm_provider.default_model` (`@large`).
  - Epic landers use `@large` or `@xlarge`.
  - Accepted tale plans hand their coder follow-up to the tale's size alias
    (`src/sase/axe/run_agent_exec_plan_accept_models.py`), so `large` planners
    already work like an "opusplan": a strong planner, then a sized coder.
- **`A | B` is weighted round-robin by launch count, not by tokens**
  (`src/sase/llm_provider/load_balancing.py`).
  - The cursor lives in `~/.sase/llm_lb.json` and advances once per real
    invocation.
  - It knows nothing about cost, allowance size, or reset times.
- **Soft vs hard disables.**
  - A **hard** disable, or a missing CLI, makes a member unavailable.
  - A **soft** disable only makes a pool member "sparing": it is used when no
    non-soft member is usable.
  - `||` chains ignore soft disables.
  - The `(pool) || tail` tail is used only when *every* pool member is hard-disabled
    or missing.
- **Disables are provider-scoped** (`src/sase/llm_provider/usage_limit_disable.py`,
  `claude.py` patterns such as `"you've hit your"`).
  - Hitting the **Fable-only weekly cap** disables all of `claude`, including Opus
    and Sonnet.
  - A same-provider `||` tail never helps, because it is disabled together with the
    primary.
- **Effort precedence** (`effort_resolution.py`): explicit `%effort` > alias-borne
  `@effort` > temporary effort override > `default_effort`.
  - Every shipped alias carries an effort, so the temporary effort override **cannot**
    act as an "economy mode" for size-alias launches.
- **Continuations inherit the parent's concrete model.**
  - Gate, monitor, and plan successors inherit it; they show `model_alias: null` with
    the parent's model.
  - This is correct for context and cache reuse, but it means an expensive initial
    pick has a long tail. Many `*--gate` and `*--mon` successors in the retained data
    ran on `claude-fable-5`.

**The live configuration.** Shipped defaults:

| Alias | Shipped target |
|---|---|
| `@xsmall` | `claude/sonnet@medium \| codex/gpt-5.5@medium \| grok/grok-4.6@medium \| agy/gemini-3.8-flash-high` |
| `@small` | `claude/sonnet@high \| codex/gpt-5.5@high \| grok/grok-4.6@high` |
| `@medium` | `codex/gpt-5.5@xhigh \| claude/sonnet@xhigh \| grok/grok-4.6@xhigh` |
| `@large` | `(claude/opus@xhigh \| codex/gpt-5.6-sol@xhigh) \|\| grok/grok-4.6@xhigh` |
| `@xlarge` | `(claude/claude-fable-5@xhigh \| codex/gpt-6-astra@xhigh) \|\| grok/grok-4.6@xhigh` |

Bryan's `~/.config/sase/sase.yml` differs from the shipped defaults as follows:

- It sets `default_effort: xhigh` globally.
- It overrides three aliases:
  - `medium` = `codex/gpt-5.5@xhigh | claude/sonnet@xhigh | 2 grok/grok-4.6@xhigh`
  - `small` = the shipped value plus grok weight 2
  - `xsmall` = `codex/gpt-5.5@medium | grok/grok-4.6`

  That `grok/grok-4.6` has no effort, so it inherits `xhigh` from `default_effort`.

## 2. Where the tokens actually go (apollo evidence)

**Provider state at 2026-09-18 21:47 UTC** (`~/.sase/llm_provider_usage.json`,
`llm_provider_disables.json`):

| Provider | Plan | Binding window | Used | Resets | Notes |
|---|---|---|---|---|---|
| Claude | (not reported) | weekly, all models | **97%** | Sep 20 00:00 | Fable weekly window at **96%**. Soft-disabled by hand in ACE since Sep 17 13:09 |
| Codex | `pro` | weekly (`codex:primary`, 7d) | **87%** | Sep 24 17:04 | The window opened only ~29h earlier. Earlier windows were cut short (resets Sep 17, 19, 22), which suggests reset credits are being spent |
| Grok | SuperGrok Heavy | included weekly | **35%** | Sep 25 13:19 | Period began 8h earlier. Billing diagnostic is `first_party_unstable` |

**Launch mix.** The retained agent metadata covers 512 agents, Sep 1–18. Of the 217
launches that recorded a size alias:

| Alias | Launches | Share |
|---|---|---|
| `@medium` | 104 | 48% |
| `@large` (incl. 19 via `default_model`) | 46 | 21% |
| `@small` | 42 | 19% |
| `@xlarge` | 23 | 11% |
| `@xsmall` | 2 | 1% |

`@xsmall` is almost irrelevant to the budget. `@medium` is the workhorse.

**Codex (152 rollouts in `~/.codex/sessions`).** Credits are computed from token
counts using OpenAI's published Codex credit rates:

| Model @ effort | Sessions | Total credits | Share | Median credits/session | Median turns | Median context/turn | Median minutes |
|---|---|---|---|---|---|---|---|
| gpt-5.5 @ xhigh | 71 | 28,911 | **78%** | 361 | 178 | 124k | 75 |
| gpt-5.5 @ high | 27 | 4,885 | 13% | 97 | 59 | 92k | 17 |
| gpt-5.6-sol @ xhigh | 41 | 2,478 | 7% | 43 | 30 | 84k | 7 |
| gpt-6-astra @ xhigh | 10 | 629 | 2% | 64 | 15 | 73k | 7 |

- **Implementation sessions are cheap per token but long.** A median `@medium`
  phase makes ~180 tool turns, re-reading ~124k tokens of context each time.
  Cached input is ~75% of its cost.
- **Planning and landing sessions** (`@large`, `@xlarge`, landers) are an order of
  magnitude cheaper per launch.
- **The fixed per-turn baseline** (instructions, memory, skills) is ~20k tokens for
  Codex and ~37k for Claude at the first turn.
- **Calibration against `used_percent`.** In the current window, apollo's 13,142
  credits correspond to 87% used, or **≈151 credits per 1%**. So one median
  gpt-5.5@xhigh phase costs about **2.4% of Codex's weekly allowance**, and a Sol
  planning session about 0.3%.
  - Earlier windows gave inconsistent ratios, from 45 to 126 credits per 1%. Other
    machines or surfaces sharing the account, or vendor metering changes, could
    explain that.
  - Treat absolute numbers as ±2×. The *relative* shares are robust.

**Claude (137 transcripts since Sep 1, API-equivalent dollars):**

| Period | Sonnet 5 | Opus 5 | Fable 5 | Total |
|---|---|---|---|---|
| Since Sep 1 | $325 (43%) | $171 (23%) | $255 (34%) | $751 |
| This week (Sep 13–18) | $156 (44%) | $112 (31%) | $89 (25%) | $357 |

- **Cache reads dominate cost:** they are 78% of Sonnet cost, 60% of Opus, and 52%
  of Fable.
- **Sonnet sessions are long:** a mean of 18.2M cache-read tokens per session,
  against 6.6M for Opus.
- **Every Fable request was served as `claude-fable-5`** (1,082 assistant messages
  this week). None were served as Fable 5.1.
- **This does not reconcile with the 96% Fable reading.** $89 of Fable against a Fable
  cap that is at most 50% of the weekly limit fits only if one of these is true:
  - Fable is metered well above its API-price share (third parties quote "~2×
    faster than Opus"); or
  - other surfaces (another machine, claude.ai) also drew on Claude this week.

  I can't separate the two from apollo's data.

**Grok.** Only 34 of 89 Grok agents wrote a non-empty `usage.json`. Those average about
15M cache-read tokens per `xhigh` session, roughly $9 API-equivalent each. Grok's cached
input costs $0.50/M, the same as Opus 5's, so Grok is **not** cheap per session.

**Summing up:** the implementation-tier members account for ≈$1,970 of ≈$2,520 in
measured API-equivalent spend, about **78%**. Those members are gpt-5.5, Sonnet 5 and
grok-4.6 (grok is partial). Planning-tier members (Sol, Astra, Opus, Fable) make up
the rest.

## 3. External facts that change the decision (Sept 2026)

These facts come from sub-research, with sources at the end. I checked the two most
decision-critical pages myself (**[verified]**).

- **Codex credit rates** per 1M input / cached / output tokens **[verified]**:
  | Model | Credit rates | Relative per-token cost |
  |---|---|---|
  | Astra | 250 / 25 / 1,250 | |
  | gpt-5.5 | 125 / 12.5 / 750 | |
  | Sol | 100 / 10 / 500 | |
  | Terra | 50 / 5 / 300 | 0.4× gpt-5.5 |
  | Luna | 5 / 0.5 / 30 | 0.04× gpt-5.5 |

  - Rates are exactly 25 credits per $1 of API list price.
  - Sol's rate reflects a temporary price cut, reportedly through Nov 21.
  - "GPT-5.5 retires from … Codex on all plans on **October 14, 2026**."
  - Estimated messages per 5h on Pro 20x: Astra 100–900, Sol 200–2,000, Terra
    500–4,000, gpt-5.5 300–1,600.
  - Terra and Luna are in apollo's Codex model cache (`~/.codex/models_cache.json`).
    Codex's default effort is `low` for Sol and `medium` for Terra and Astra.
- **Codex benchmarks** (secondary sources): Terminal-Bench 2.1 is Sol 88.8, gpt-5.5
  88.0, Terra 87.4, Luna 84.7.
  - Terra is "about as good as GPT-5.5 for less."
  - On Terminal-Bench 4.0, Astra `high` = `xhigh` = 57.9.
- **Anthropic's cost-per-solved-task data, SWE-bench Pro** **[verified]**:
  | Setup | Solve rate | Cost per solved task |
  |---|---|---|
  | Opus 5 @ low | 84.0% | $0.25 |
  | Sonnet 5 @ default | 77.4% | $0.84 |
  | Opus 5 @ default | 91.7% | $1.01 |
  | Fable 5.1 @ low | 88.6% | $0.54 |

  - Relative to default, Opus 5 at `medium` costs ~50% less for ~2 points; at `low`,
    ~75% less for ~8 points.
  - "Fable 5 to Fable 5.1: **43% less per solved task** at about the same score."
  - Running at `low` and re-running failures at default gives the same pass rate as
    all-default for half the cost. This needs a real failure signal.
  - Claude Code's default effort is `high`, not `xhigh`.
- **Claude plan rules:**
  - Fable can use at most 50% of the weekly limit on Max.
  - Fable 5.1 cache reads cost $0.25/M, against $1.00 for Fable 5 and $0.50 for Opus 5.
  - In Claude Code, `fable` resolves to Fable 5.1, `opus` to Opus 5, and `sonnet` to
    Sonnet 5.
  - The Claude Code weekly limit dropped ~17% on Sep 14, when the temporary boost
    ended.
- **grok-4.6:** $2 / $0.50 cached / $6. Efforts are `low`–`xhigh`, default `high`.
  Artificial Analysis Intelligence Index 61, about Sol max. SuperGrok Heavy is one
  weekly pool shared with grok.com, with no published size. The CLI offers only
  grok-4.6 and 4.5.
- **Gemini 3.8 Flash (agy):** cheap, $0.75 / $3.75 until Dec 31.
  - Artificial Analysis cost per task: high $0.58, medium $0.41.
  - There are Sep 18 reports of command looping and quota drain.
  - SASE caps the agy prompt at 122 KB (the argv transport limit).
- **Routing literature:**
  - Cascades and routers (FrugalGPT, RouteLLM) cut cost 2× or more on general tasks.
    A 2026 coding-agent router matched the best single model at ~5.5× lower cost per
    solve.
  - Accuracy on SWE-bench "peaks at intermediate cost and saturates."
  - Evidence on whether cheaper models create rework is thin and mixed. **Cost per
    accepted task, not price per token, is the metric to use.**

## 4. Critique of the plan

**What's right:**

- Size aliases are the single choke point for nearly all launches.
- Pools and last-resort tails are already expressive enough.
- The planner/coder split already exists: large planners hand off to sized coders.
- The per-launch cost of planning is small, so strong planners are affordable.

**What I'd change:**

1. **"Largest model I need" is a secondary lever.** The primary levers are effort
   and cost per token *within the implementation tiers*.
   - Everything runs at `xhigh`, above every vendor's default, and above where
     vendor curves flatten (Astra TB4: `high` = `xhigh`; Opus 5 FrontierCode peaks
     at `medium`).
   - Bryan's `default_effort: xhigh` quietly raises any member without an explicit
     effort.
2. **gpt-5.5 must go regardless.** It is the most expensive per-token model in the
   hottest pool, it is being retired in 26 days, and a same-quality successor (Terra)
   costs 40% as much.
3. **Round-robin balances launches, not budget.**
   - Allowances differ in size; per-launch cost differs by provider, model and
     effort; windows reset at different times.
   - Equal launch counts therefore exhaust the tightest provider first. The
     survivors then inherit its share and fail in turn — a correlated cascade
     visible on Sep 15, 17 and 18 (Codex 43–48 launches/day while Claude had 2–8).
   - No static weight vector fixes this. It needs a pace signal.
4. **Capacity is short in aggregate.**
   - Each provider appears to support only about 40–50 current-style `@medium`
     launches per week. Codex costs ~2.4% per gpt-5.5@xhigh phase; Grok's current
     reading is ~2% per launch, from 18 launches for 35%, which is low-confidence.
   - Against ~300 launches per week of demand, balancing alone just changes *which*
     provider runs dry first.
   - Reducing cost per unit of work is the only lever that increases throughput.
     Balancing only decides who pays.
5. **Model-scoped caps meet provider-scoped disables.** With Fable in any frequently
   used pool, hitting the Fable cap takes all of Claude offline, typically until the
   weekly reset. Fable should sit only in a rarely used tier, and disables should
   become model-scoped (follow-up F2).
6. **You can't size down safely without measuring outcomes.**
   - Codex agents write no `usage.json`: SASE records usage for Claude and Grok only.
   - There is no cost-per-landed-phase rollup.
   - "The smallest model that gets the job done" is a claim about outcomes, and SASE
     currently records only launch counts per alias member.
7. **Over-provisioning is a substitute for escalation.**
   - Anthropic's own data shows that "cheap first, re-run failures stronger" matches
     the pass rate of "strong always" at half the cost.
   - SASE has real failure signals (`just check`, lander failures, phase failure
     states) but relaunches only on *availability* failures.
   - An escalate-on-failure path would let every tier be set one notch lower with
     confidence. This is a feature, not an alias value (follow-up F5).

**Would I take a different approach?** Partly. I'd frame this as a budget-control
problem with three levers, in order of impact:

1. **Cost per unit of work.** This is set by the alias defaults: the implementation
   tiers first, effort before model.
2. **Pace-based distribution across providers.** Dynamic soft-disables, not
   hand-tuned weights.
3. **Demand shaping when all providers are running hot.** An effort ceiling or
   "economy mode", and fewer concurrent launches.

Model aliases are lever 1 and part of lever 2, so the plan is a good start, but only a
start.

## 5. Requirement adjustments (explicitly called out)

- **R1 — Effort is part of "size."** The goal becomes "the smallest *model and
  effort* that reliably lands the work." Default to at most each vendor's default
  effort, and exceed it only where evidence supports it.
- **R2 — "Fair" means pace, not equal counts.** The target is that each provider's
  binding window reaches ~90–100% at its reset. Static weights are only a starting
  prior.
  - This **deliberately departs** from the earlier consolidated capacity-UX research,
    which declined to route on usage projections.
  - My proposal uses the reading only as a *soft preference* with hysteresis, never
    as a block. A wrong guess changes pool order, not availability.
- **R3 — Shipped defaults vs personal overrides.**
  - Shipped defaults must not depend on the user's plan: equal weights, graceful
    skipping of missing CLIs, and no plan-size assumptions.
  - Bryan's weights belong in his config and should be calibrated from measured
    percent-of-allowance per launch.
- **R4 — Honor model-scoped caps.** Keep Fable out of high-volume pools until disables
  can be scoped to a model.
- **R5 — Hard deadline.** No shipped or personal alias may depend on `gpt-5.5` after
  2026-10-14.
- **R6 — Measure before and after.** Add per-agent cost for Codex and a per-alias cost
  rollup, so the change can be judged on cost per landed phase.

## 6. Recommended solution

### 6.1 Design rules

1. **Spend on planning, save on implementation.**
   - `@large` and `@xlarge` keep frontier models, because planning sessions are
     cheap and high-leverage.
   - `@small` and `@medium` get the cheapest model/effort pairs with near-frontier
     coding scores.
2. **Cap effort at the vendor default** (Claude `high`, Grok `high`, Codex Terra and
   Astra `medium`/`high`). Go above it nowhere by default. Go below it wherever the
   tier's task is simple.
3. **Within a provider, prefer a stronger model at lower effort** over a weaker model
   at higher effort. This is Anthropic's measured result for Opus@low vs Sonnet, and
   OpenAI's reported "Astra@low can beat Sol@high."
4. **Use Fable only in `@xlarge`, and only as Fable 5.1.**
5. **Grok stays a last-resort tail for planning tiers** and a full pool member for
   implementation tiers, matching the project's current trust judgement.
6. **Include agy only in `@xsmall`** because of the prompt-size cap and current
   looping reports.

### 6.2 Shipped defaults (`src/sase/llm_provider/model_alias_defaults.yml`)

```yaml
schema_version: 1
aliases:
  xsmall:
    target: "claude/sonnet@low | codex/gpt-5.6-luna@medium | grok/grok-4.6@low | agy/gemini-3.8-flash-medium"
    description: >-
      Extra-small launch alias for near-zero-reasoning tasks and tale follow-ups;
      cheapest model per provider at low effort.
  small:
    target: "claude/opus@low | codex/gpt-5.6-terra@medium | grok/grok-4.6@medium"
    description: >-
      Small launch alias for focused direct implementation; strong models at
      reduced effort.
  medium:
    target: "claude/opus@medium | codex/gpt-5.6-terra@high | grok/grok-4.6@high"
    description: >-
      Medium launch alias for ordinary implementation work; the highest-volume
      tier, tuned for cost per landed phase.
  large:
    target: "(claude/opus@high | codex/gpt-5.6-sol@high) || grok/grok-4.6@high"
    description: >-
      Large launch alias for planning-heavy work, default launches, and epic
      landers; Grok is last resort when Claude and Codex are unavailable.
  xlarge:
    target: "(claude/fable@high | codex/gpt-6-astra@high) || grok/grok-4.6@xhigh"
    description: >-
      Extra-large launch alias for epic planning and big-epic landing; the only
      tier that uses Fable, so the Fable weekly cap is not consumed by routine
      work. Grok is last resort.
```

Keep the scalars (`default_model: @large`, `epic_lander_model: @large`,
`big_epic_lander_model: @xlarge`) and the empty shipped `default_effort`. `@large` now
runs at `high`, so ad-hoc launches get cheaper too.

**Why each choice:**

- **`@medium`.**
  - Terra@high replaces gpt-5.5@xhigh at 0.4× the per-token credits, with equal
    reported TB2.1 quality and fewer reasoning tokens.
  - Opus@medium replaces Sonnet@xhigh. It scored higher (~90% vs 77% on SWE-bench
    Pro) at about 0.7× Sonnet-default's cost per attempt, per Anthropic's data.
  - If Terra's `@medium` output is visibly weaker, the fallback choice is
    `codex/gpt-5.6-sol@medium`. That is still ~40% cheaper per token than today, but
    re-check it when Sol's price cut ends.
- **`@small`.**
  - Opus@low scores 84% on SWE-bench Pro at ~$0.21 per attempt, against Sonnet
    default's 77% at ~$0.65.
  - Terra@medium is Codex's default setting for Terra.
- **`@xsmall`.** Per-token price dominates when turns are few, so this tier uses each
  provider's cheapest model: Sonnet, Luna, grok@low, and Flash-medium.
- **`@large`.**
  - `high` is Claude Code's default for Opus 5 and saves ~19% of tokens against
    `xhigh`.
  - Sol@high is still above Codex's `low` default for Sol, which suits planning.
- **`@xlarge`.**
  - `claude/fable` is Claude Code's floating alias, currently Fable 5.1, which costs
    43% less per solved task than Fable 5.
  - `high` rather than `xhigh`: Astra's TB4 score is flat between the two, and Fable
    5.1's code scores peak at `medium`.

### 6.3 Bryan's personal overrides (`~/.config/sase/sase.yml`)

- **Delete `default_effort: xhigh`.** Every alias now names its effort, and the global
  `xhigh` only inflates unspecified targets: custom aliases, and bare `%model` picks.
- **Replace the three gpt-5.5 overrides** before Oct 14. Either delete them and adopt
  the shipped values above, or, if you want Grok to absorb more load while it has the
  most headroom:

```yaml
llm_provider:
  model_aliases:
    builtin:
      xsmall: "codex/gpt-5.6-luna@medium | claude/sonnet@low | grok/grok-4.6@low"
      small: "claude/opus@low | codex/gpt-5.6-terra@medium | 2 grok/grok-4.6@medium"
      medium: "claude/opus@medium | codex/gpt-5.6-terra@high | 2 grok/grok-4.6@high"
```

- **Weights are a starting prior.**
  - After one week, set each member's weight in proportion to *launches per 1% of its
    provider's weekly allowance*, measured for that member.
  - Until pacing exists (F1), keep soft-disabling by hand any provider whose weekly
    used% is well ahead of elapsed%. You are already doing this for Claude, and it is
    the right instinct.
- **Keep the custom research aliases as they are.** They are rare and
  high-leverage.

### 6.4 Code and catalog changes the shipped defaults need

- **`codex.py` `llm_known_model_names`:**
  - Add `gpt-5.6-terra` and `gpt-5.6-luna`, with short aliases, e.g. `terra` and
    `luna`.
  - Flag `gpt-5.5` via `llm_model_advisories` as retiring on 2026-10-14.
  - Explicit `codex/gpt-5.6-terra` already resolves today; I verified this with the
    installed SASE.
- **`claude.py`:**
  - Add a `fable` model entry, or `claude-fable-5-1`. Today `fable` is only a
    display short alias for `claude-fable-5`; `claude/fable` resolves to
    `('claude', 'fable')`, which is passed through to the CLI.
  - Check whether Fable 5.1's model-specific usage window still reports as
    `weekly:claude-fable-5`. `default_config.yml`'s usage indicator hard-codes that
    key.
- **Documentation:**
  - Regenerate the `model-alias-defaults` block in `docs/llms.md`.
  - Refresh the `default_config.yml` grammar example, which still shows gpt-5.5
    targets.
- **Check the first live run:** confirm the `message.model` recorded in the transcript
  and rollout (`claude-fable-5-1`, `gpt-5.6-terra`) matches the intended model.

### 6.5 Expected impact (rough; state the assumptions)

These estimates apply vendor ratios to apollo's Sep 1–18 spend mix. They assume quality
holds, meaning no extra rework.

| Tier | Change | Est. cost vs today |
|---|---|---|
| `@medium` | gpt-5.5@xhigh → Terra@high; Sonnet@xhigh → Opus@medium; Grok xhigh → high | Codex ~0.35×, Claude ~0.6–0.7×, Grok ~0.8× |
| `@small` | gpt-5.5@high → Terra@medium; Sonnet@high → Opus@low; Grok high → medium | Codex ~0.35×, Claude ~0.35×, Grok ~0.8× |
| `@large` | `xhigh` → `high` | ~0.85× |
| `@xlarge` | Fable 5 → 5.1, `xhigh` → `high` | Claude ~0.45×, Codex ~0.8× |
| **Blended** | | **Codex ~0.4×, Claude ~0.55×, Grok ~0.8×; overall ~0.5×** |

The biggest uncertainties:

1. SWE-bench-to-SASE transfer for Opus@low/medium versus Sonnet.
2. Whether Claude's subscription meter charges each model in proportion to its API
   price.
3. Terra's real quality on SASE's own phases.

## 7. Follow-ups beyond alias values (ranked by expected payoff)

I did not file task beads. This is one of two parallel reports, and the lead's
synthesis should decide which of these become beads.

- **F1 — Pace-aware soft disables (Rust core).**
  - For each provider's binding window: `pace = used / max(elapsed, 0.05)`.
    Soft-disable (`source: pacing`) when pace > 1.15 and used > 25%; clear it when
    pace < 1.0.
  - This reuses the existing usage store and soft-disable semantics. Pools already
    prefer non-soft members, and `||` chains ignore soft disables, so the rule never
    blocks work.
  - Per the backend boundary, this logic belongs in `sase-core`.
- **F2 — Model-scoped usage-limit disables.** A Fable-cap hit should disable
  `claude/fable*` only, not Opus and Sonnet.
- **F3 — Cost accounting.**
  - Write `usage.json` for Codex from `token_count` events. Those events also carry
    the live `rate_limits` snapshot, which is a free usage observation.
  - Add cost (tokens and percent-of-window) to the alias-history rollup, so Launch
    Control shows cost per landed phase for each pool member.
  - This turns pools into a built-in A/B harness.
- **F4 — Effort-ceiling override ("economy mode").** A temporary, machine-wide cap
  that *clamps* alias-borne efforts downward. The existing temporary effort override
  ranks below alias efforts and cannot do this.
- **F5 — Escalate on failure.** Relaunch a phase that fails its checks at the next
  size up, or the same model at default effort. This is Anthropic's "low, then re-run
  failures" pattern, and it lets tiers be set lower safely.
- **F6 — Context hygiene for implementation phases.**
  - Cost scales with turns × context. The median `@medium` Codex phase re-reads ~124k
    tokens per turn, and the fixed baseline is 20–37k.
  - Terse `just check` failure output and smaller always-loaded instructions reduce
    every turn's cost linearly.

## 8. Validation plan (1–2 weeks)

1. **Baseline, 2–3 days, before switching.** Run the rollout and transcript
   aggregation used here (Codex `token_count` credits; Claude transcript usage at API
   rates) grouped by alias member.
2. **Switch `@medium` and `@small` first.** That is where ~78% of spend is.
3. **Leave `@large` and `@xlarge` for a later step.** Switch Fable 5 → 5.1
   immediately, since it has the same score at lower cost.
4. **A/B inside a pool for one week, if in doubt.** For example,
   `claude/sonnet@high | claude/opus@medium | codex/gpt-5.6-terra@high | …`. Compare
   each member's done/failed counts in alias history, and its cost from step 1.
5. **Success criteria:**
   - Percent-of-weekly-allowance per landed phase drops by ≥40%.
   - The rate of failed or rerun phases and lander fix-ups does not rise by more than
     a few points.
   - No provider reaches 100% more than a day before its reset.

## Sources

- Anthropic, pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Anthropic, cost vs intelligence data (verified directly):
  https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence
- Anthropic, effort: https://platform.claude.com/docs/en/build-with-claude/effort
- Anthropic, Fable 5.1: https://www.anthropic.com/claude-fable-and-mythos-5-1
- Claude Fable on plans:
  https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
- Claude Max plan: https://support.claude.com/en/articles/11049741-what-is-the-max-plan
- Claude Code model config and aliases: https://code.claude.com/docs/en/model-config
- Claude Code costs and limits messages: https://code.claude.com/docs/en/costs
- Claude Code weekly-limit change:
  https://www.bleepingcomputer.com/news/artificial-intelligence/anthropic-is-cutting-claude-codes-current-weekly-limits-by-17-percent/
- OpenAI Codex pricing, credits and gpt-5.5 retirement (verified directly):
  https://learn.chatgpt.com/docs/pricing
- OpenAI Codex models: https://learn.chatgpt.com/docs/models
- OpenAI API model pages: https://developers.openai.com/api/docs/models/gpt-5.6-terra ,
  https://developers.openai.com/api/docs/models/gpt-5.6-sol ,
  https://developers.openai.com/api/docs/models/gpt-6-astra
- Terra/Luna/Sol benchmarks (secondary):
  https://www.vellum.ai/blog/gpt-5-6-sol-terra-luna-explained
- Astra benchmarks and effort (secondary):
  https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra ,
  https://teendifferent.substack.com/p/astras-reasoning-effort-might-not
- xAI grok-4.6: https://x.ai/news/grok-4-6 , https://docs.x.ai/developers/models ,
  https://docs.x.ai/grok/faq ,
  https://artificialanalysis.ai/articles/grok-4-6-benchmarks-and-analysis
- Antigravity plans and Gemini 3.8 Flash: https://antigravity.google/docs/plans/ ,
  https://artificialanalysis.ai/articles/gemini-3-8-flash ,
  https://discuss.ai.google.dev/t/gemini-3-8-flash-in-antigravity-severe-latency-command-looping-quota-drain-api-503-billing-issues/183550
- Routing and cascades: https://arxiv.org/abs/2305.05176 (FrugalGPT),
  https://arxiv.org/abs/2406.18665 (RouteLLM),
  https://arxiv.org/html/2608.04804 (coding-agent routing),
  https://arxiv.org/abs/2604.22750 (token spend vs accuracy)
- Local evidence (apollo, read-only):
  - `~/.sase/llm_provider_usage.json`, `~/.sase/llm_provider_disables.json`,
    `~/.sase/llm_lb.json`
  - agent metadata under `~/.sase/projects/*/artifacts/ace-run/`
  - `~/.codex/sessions/2026/09/`, `~/.codex/models_cache.json`
  - `~/.claude/projects/*/*.jsonl`
  - `~/.config/sase/sase.yml`
- Prior SASE research consulted through `sase artifact read`:
  - `research:202609/subscription_capacity_experience/subscription_capacity_experience.md`
  - `research:202609/provider_subscription_usage/provider_subscription_usage.md`
