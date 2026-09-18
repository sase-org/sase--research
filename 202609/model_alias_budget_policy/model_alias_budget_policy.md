# Model alias budget policy: spend less per completed task

Research synthesis · 2026-09-18 · Claude Code, Codex, and Grok Build

**Recommendation:** tune the aliases, starting with `small` and `medium`: replace
GPT-5.5 with Terra, lower routine reasoning effort, and reserve frontier models for
difficult work. Give Grok an ordinary share of `large` launches. Keep equal weights
as portable defaults, but do not describe round-robin as quota balancing. Measure
**total allowance consumed per verified completion**, including retries and repair.
The recommended definitions close this report; this research does not activate them.

Alias changes are a good first intervention, not a complete budget controller.
Long contexts, long tool loops, inherited expensive models, simultaneous agents,
and usage outside SASE all matter. Neither researcher establishes that a particular
replacement will halve subscription consumption on SASE's workload.

**Evidence and provenance.** The dispatch identifies exactly one A report from
`research.6.cdx` and one B report from `research.6.cld`. Both were read through their
canonical research references, then moved only within this opened research checkout.
Their bytes, including their original A/B identities, are preserved.

| Dispatch dependency | Preserved report | Original canonical reference | Registered immutable snapshot |
|---|---|---|---|
| `research.6.cdx` · A | [Quota-aware routing](model_alias_budget_policy__a.md) | `research:202609/size_alias_quota_aware_routing__a.md` | `file:explicit:d4703a47a0a3361ed6696bf8` |
| `research.6.cld` · B | [Token-budget routing](model_alias_budget_policy__b.md) | `research:202609/size_alias_token_budget_routing__b.md` | `file:explicit:4c814a2fb50a0d77b80e7ad4` |

My independent research checked current official provider documentation, SASE source
at `01f5cb9e3e0f231cd29440dc10fa1017fac2c04c`, and the prior
[subscription-capacity synthesis](../subscription_capacity_experience/subscription_capacity_experience.md),
also read through `sase artifact read`. The input reports inspected an earlier SASE
revision, `fa61906da0`. I did not read predecessor chats or reproduce B's transcript
aggregation. Its account measurements remain attributed observations, not fresh
measurements or a controlled comparison.

**The strongest shared finding is where to start.** Current shipped `small` members
use `high`; every `medium` member uses `xhigh`. Both include GPT-5.5. `large` and
`xlarge` rotate only Claude and Codex, with Grok as a last resort. Unspecified
launches default to `large`.
[Shipped alias definitions](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/model_alias_defaults.yml),
[launch defaults](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/default_config.yml)

B reports 217 retained launches with size metadata: 104 `medium`, 42 `small`, 46
`large`, 23 `xlarge`, and just two `xsmall`. Its estimated Codex credits attribute
78% of September consumption, and 91% of its current-window sample, to
GPT-5.5 at `xhigh`. These observations justify prioritizing implementation tiers;
optimizing only `xsmall` would miss the reported workload. They do **not** establish
that GPT-5.5 intrinsically needs more turns: its tasks differ from the shorter
planning tasks assigned to Sol and Astra. Unlabelled launches and other machines
also prevent treating this sample as the whole account.
[B's measurements and method](model_alias_budget_policy__b.md)

OpenAI's published credit rates make the model change unusually compelling:

| Codex model | Input / cached input / output credits per million tokens |
|---|---|
| GPT-5.5 | 125 / 12.5 / 750 |
| GPT-5.6 Luna | 5 / 0.5 / 30 |
| GPT-5.6 Terra | 50 / 5 / 300 |
| GPT-5.6 Sol | 100 / 10 / 500 |
| GPT-6 Astra | 250 / 25 / 1,250 |

At an unchanged token mix, Terra costs 40% of GPT-5.5's credits; this is arithmetic,
not a forecast of identical task outcomes. GPT-5.5 retires from Codex sign-in plans
on October 14, 2026; the API is unaffected. Sol's current promotional price is
promised at least through November 21. These credit rates are not a universal
conversion from tokens to percentage of included allowance.
[OpenAI pricing and usage](https://learn.chatgpt.com/docs/pricing)

OpenAI positions Luna for focused, high-volume work, Terra for everyday work, Sol
for harder work, and Astra for the most complex work. Its guidance explicitly
recommends the lowest successful effort and cautions that effort labels do not map
exactly between GPT-5.5 and GPT-5.6.
[OpenAI model selection](https://learn.chatgpt.com/docs/models)

**The Claude disagreement needs a local experiment.** A favors Sonnet for routine
work; B favors stronger Opus at reduced effort. Anthropic's internal coding subset
supports B's hypothesis: Opus 5 at low effort solved 84% at $0.25 per solved task,
and retrying low-effort failures at default effort roughly halved cost while
preserving the measured pass rate. But the subset is not the public leaderboard,
and the result requires a reliable verifier. It does not establish a universal
Opus-over-Sonnet rule or SASE subscription savings.
[Anthropic's measured cost/quality tradeoffs](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)

B also reports that cache reads make up 78% of Sonnet's estimated API-equivalent
cost. Current Sonnet and Opus cache-read prices are $0.20 and $0.50 per million
tokens. **My sensitivity calculation:** holding cached-token volume constant,
switching that workload to Opus creates a cache-only cost floor of
`0.78 × (0.50 / 0.20) = 1.95` times its entire previous cost. Even with every other
cost removed, cached volume would need to fall below about 51% of its old level
to break even. Lower effort can shorten loops, so this is a counterexample, not a
prediction. It explains why I retain Sonnet at reduced effort initially and make
Opus low/medium the first challenger to test.
[Claude prices](https://platform.claude.com/docs/en/about-claude/pricing),
[B's cache measurements](model_alias_budget_policy__b.md)

Fable 5.1 is a sensible replacement for explicitly selected Fable 5: its published
cache-read price is $0.25 rather than $1 per million. That is not permission to
move every Claude task to Fable. On Max and eligible premium seats, Fable has a
sub-limit of up to 50% of the shared weekly allowance; on Pro and standard seats,
it uses usage credits. A Fable-only cap does not mean other Claude models have
exhausted their allowance.
[Claude prices](https://platform.claude.com/docs/en/about-claude/pricing),
[Fable plan eligibility](https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan)

Use explicit versioned IDs for reproducibility. Claude Code's floating `fable`
alias can resolve differently by client version and gateway; Fable 5.1 requires
Claude Code 2.1.257 or later. In noninteractive `-p` mode, requests that require
usage credits bill without an interactive consent prompt. Verify the chosen
model's entitlement and billing policy before enabling the final configuration.
If Fable is not included, use the Opus substitution given below.
[Claude Code model configuration](https://code.claude.com/docs/en/model-config)

**Resolve the other disagreements explicitly.**

| Question | Consolidated decision |
|---|---|
| Lower `default_model` to `medium` now? | Keep `large` initially, at reduced effort. B's evidence identifies explicitly sized implementation as the main expense; strong planners may prevent expensive rework. Test unsized routine launches at `medium` separately. This declines A's simultaneous default change. |
| Put Grok in `large`? | Yes, as a measured rollout. A's proposed topology makes spare Grok capacity usable before both other providers hard-fail. It is a routing judgment, not proven quality parity. Track planning repair and completion quality. |
| Keep Grok as `xlarge` fallback? | Yes, with an explicit degraded-capability contract. Do not treat its result as interchangeable merely because routing succeeded; require the same acceptance checks. Tasks requiring a strict frontier floor should remove this tail. |
| Use `xhigh` for frontier models by default? | No: start Fable/Astra at `high`; reserve additional effort for demonstrated difficult cases. Grok's exceptional `xlarge` tail remains `xhigh`. |
| Include AGY/Gemini? | Exclude it from this three-provider recommendation. This deliberately changes today's `xsmall` membership. Retain it only in a separately evaluated personal pool. |
| Claim about twice the capacity? | No. B's 1.5–2× overload estimate and approximately 50% savings forecast rely on incomplete accounting and workload transfer. Treat them as hypotheses. |
| Use third-party benchmark rankings to choose peers? | No decisive ranking: the reports quote incompatible Grok index values without establishing the same benchmark version. Neither justifies a production quality-equivalence claim. |

Grok 4.6 offers `low`, `medium`, `high`, and `xhigh`, with `high` as its documented
default; reasoning cannot be disabled. Its low-effort member is therefore a
workload class, not a physically small model. Grok's weekly subscription pool is
shared across products, so activity outside Build can change available capacity.
[xAI reasoning controls](https://docs.x.ai/developers/model-capabilities/text/reasoning),
[Grok subscription FAQ](https://docs.x.ai/grok/faq)

**Fallback semantics constrain the recommendation.** The current implementation
establishes four distinct behaviors:

| Mechanism | Actual effect |
|---|---|
| `A \| B` | Round-robin among eligible members; integer weights count launches, not tokens or allowance. |
| Soft disable | A pool prefers non-soft members. If all usable members are soft-disabled, it still uses them. |
| `(A \| B) \|\| C` | Selects C only when the primary pool is unavailable. A soft-disabled primary pool still wins over C. |
| Runtime recovery | Separate from alias selection: provider retries and a conditional provider-drain restart path may act after errors. |

[Selector implementation](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/load_balancing.py)

This corrects A's overly broad suggestion that runtime recovery is absent. Current
code can submit a drain after a newly recorded hard disable when notification,
relaunch, and the provider-drain feature are enabled. The drain replans eligible
live/recently failed agents, skips pinned or otherwise unsuitable cases, and uses
the existing restart machinery. It is neither guaranteed recovery for every
failure nor an inline retry of the same API call. Extend and validate that path
before proposing a second retry orchestrator.
[Disable handling](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/usage_limit_disable.py),
[drain planning](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/agent/_drain_planning.py),
[drain eligibility](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/agent/_drain_selection.py)

Usage-error disables remain provider-scoped. Thus a classified Fable-cap error can
disable Claude as a whole; adding Sonnet after Fable in a SASE `||` chain does not
solve that. Model-cap scope should be preserved before frequently using Fable.
Likewise, a CLI being installed does not prove its account can access every model:
the availability check is not a model-entitlement probe.
[Disable handling](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/usage_limit_disable.py),
[target availability](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/model_alias_resolution_types.py)

**Fairness should mean useful work sustained until reset.** Equal launches are a
reasonable neutral starting point, not an optimal allocation. Do not hard-code
Grok weight 2 from a snapshot showing more headroom. Different plan capacities,
task costs, windows, external usage, and remaining time all matter.

I decline both A's uncalibrated projected-headroom ranking and B's immediate
`used / elapsed` soft-disable automation. The
[prior capacity research](../subscription_capacity_experience/subscription_capacity_experience.md)
correctly identifies the problems: percentages are not amounts of work; window
start cannot always be inferred; old readings and bursts distort pace. Making a
mistaken decision soft rather than hard reduces harm but does not validate it.

A future, opt-in router should consider **all applicable windows for each model**,
fresh observations, per-task consumption estimates, queued/running commitments,
and account activity outside SASE. For a confirmed fixed window, a useful
experimental quantity is:

```text
sustainable tasks/hour =
  (remaining fraction - reserve - estimated in-flight consumption)
  / (hours until reset × estimated fraction consumed per comparable task)
```

Take the tightest applicable window, reject unavailable or unqualified candidates,
and use the estimate only as a bounded preference with hysteresis. Missing or
unreliable inputs return to round-robin. This is a design hypothesis, not shipped
behavior or a guarantee that the next task fits. Shared routing/domain changes
belong in Rust core, with thin Python callers.

When all providers are short, balancing cannot create capacity. Defer low-priority
work, reduce unnecessary duplicate agents, or explicitly choose more paid capacity.
Lower concurrency alone mainly changes when quota is spent; it saves total tokens
only when it avoids wasted or overlapping work. The current all-soft behavior
cannot enforce a weekly budget.

**Requirements I would change.**

1. Optimize model **and effort** for verified completion, not the smallest model
   name or lowest token price. Include repair, escalation, and human review cost.
2. Treat size as difficulty, ambiguity, and consequence, not just file count or
   expected duration. A one-line security fix may deserve `large`.
3. Separate provider unavailability from inadequate output. Availability fallback
   stays within a suitable class; quality escalation uses a stronger effort/model
   after a meaningful failure signal, with a bounded retry budget.
4. Keep portable defaults independent of one person's plan weights, and make paid
   continuation/model entitlement explicit. No implicit API-billing rescue route.
5. Include effective personal configuration, continuation behavior, and context
   overhead in the change. Updating shipped aliases alone is insufficient.

B reports personal `small`, `medium`, and `xsmall` overrides plus a global
`default_effort: xhigh`. Remove or replace those overrides when adopting the new
values; otherwise they mask the shipped changes. Explicit effort wins over
alias effort, which wins over the temporary override and configured default. The
temporary override therefore cannot clamp an alias's explicit effort into an
economy mode. Audit actual resolved model and effort, not just the YAML edited.
[Effort precedence](https://github.com/sase-org/sase/blob/01f5cb9e3e0f231cd29440dc10fa1017fac2c04c/src/sase/llm_provider/effort_resolution.py),
[B's effective-config observations](model_alias_budget_policy__b.md)

Keep model/provider affinity inside an ongoing task where it preserves context and
cache value. Consider resizing at clear phase boundaries; do not expect a new alias
definition to resize a successor that inherits a concrete model. Trim unrelated
instructions and oversized tool output, and avoid repeated verification after
relevant checks pass. B's cache-heavy usage suggests this is a substantial lever
even when cache hit rates are already good.

**Rollout and decision rule.** First update the provider catalog, completions and
usage-window applicability for the explicit IDs below; the inspected catalog still
omits Terra/Luna and names the older Fable version. Verify client versions,
entitlements, effort acceptance, actual served models, and existing runtime
recovery. Update the source alias file and the explanatory examples in
`default_config.yml`; changing only the latter does not change shipped aliases.

Run a one-to-two-week stratified trial, beginning with `small`/`medium`. Compare
similar tasks within each provider; do not infer causality from different roles'
historical medians. Track task class, actual model/effort, tokens by cache category,
all attempts, verified completion, repair/review burden, elapsed time, and usage
observations with scope and timestamps. Overlapping work makes an individual
launch's before/after quota delta an attribution estimate, not ground truth.

Test Sonnet low/medium against Opus low/medium in matched Claude cohorts. Adding
both Claude candidates to a flat three-provider pool would accidentally double
Claude's launch share; use separate experiment cohorts or preserve provider totals.
Likewise, assess Grok's `large` work for plan quality and downstream repairs before
making its membership universal.

A proposed acceptance target is at least 30% less allowance per verified completion
with no material increase in repair burden or final failure. A three-percentage-point
quality margin is a starting policy choice, not a statistical result; small samples
cannot establish it. Roll back an individual member when quality regresses, and
increase effort before discarding an otherwise effective model. Use a verifier
appropriate to the task: passing existing tests alone does not validate research
claims, architecture, or missing test coverage.

**Recommended solution and definitions.** Use the following as the initial policy
to validate, retaining `large` for unsized launches and landers. The most important
changes are Terra replacing GPT-5.5 and routine tiers leaving `xhigh`. There are no
extra tails on the first four aliases because each already includes all three
providers; trying more models from a hard-disabled provider adds no capacity.

| Alias | Contract |
|---|---|
| `xsmall` | Lookup, classification, formatting, and tiny edits with obvious checks; Haiku/Luna must not inherit unrestricted implementation work. |
| `small` | Clear, bounded implementation or analysis with local verification. |
| `medium` | Ordinary implementation and analysis with moderate ambiguity. |
| `large` | Difficult debugging, planning, cross-cutting changes, and landers. |
| `xlarge` | Exceptional difficult work; explicit selection or big-epic landing, with a disclosed weaker last resort. |

The first four pools are unweighted. Haiku deliberately has no effort suffix;
the other members specify effort. Clear the global `xhigh` setting. For Fable use,
confirm included entitlement or an intentional usage-credit budget; otherwise
substitute `claude/claude-opus-5@high` for its `xlarge` member. If a strict frontier
quality floor matters more than availability, omit the Grok `xlarge` tail.

The YAML below is valid user-override syntax. To ship the same values, place each
target under `aliases.<size>.target` in
`src/sase/llm_provider/model_alias_defaults.yml`, with corresponding descriptions;
the scalar defaults remain in `src/sase/default_config.yml`. Syntax validation does
not constitute a live model-access or quality test.

```yaml
llm_provider:
  default_effort: ""
  default_model: "@large"
  epic_lander_model: "@large"
  big_epic_lander_model: "@xlarge"

  model_aliases:
    builtin:
      xsmall: >-
        claude/claude-haiku-4-5 |
        codex/gpt-5.6-luna@low |
        grok/grok-4.6@low
      small: >-
        claude/claude-sonnet-5@low |
        codex/gpt-5.6-terra@low |
        grok/grok-4.6@low
      medium: >-
        claude/claude-sonnet-5@medium |
        codex/gpt-5.6-terra@medium |
        grok/grok-4.6@medium
      large: >-
        claude/claude-opus-5@high |
        codex/gpt-5.6-sol@high |
        grok/grok-4.6@high
      xlarge: >-
        (claude/claude-fable-5-1@high |
        codex/gpt-6-astra@high) ||
        grok/grok-4.6@xhigh
```
