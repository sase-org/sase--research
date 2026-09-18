# Quota-aware defaults for SASE size model aliases

**Researcher:** A  
**Date:** 2026-09-18  
**Scope:** Claude Code, Codex, and Grok Build subscription-backed SASE agents

## Executive conclusion

Reworking the built-in size aliases is worthwhile. The present defaults spend too much reasoning effort in the middle tiers, use retired or superseded models, and exclude Grok from the normal `large` rotation. Those choices make ordinary launches unnecessarily expensive and can strand capacity in one provider while the other two approach their weekly limits.

Alias tuning alone will not solve quota exhaustion, however. SASE currently balances *launch counts*, not token consumption or normalized subscription headroom. It also resolves an ordered fallback before launch; the fallback does not rescue the invocation that discovers a runtime usage limit. The best near-term change is therefore:

1. make each size a distinct workload class with conservative effort;
2. put all three providers in the ordinary pools, without universal static weights;
3. lower the implicit default from `@large` to `@medium`;
4. keep `@xlarge` explicit and rare; and
5. follow this with usage-aware routing and verified-failure escalation.

The final recommended definitions are at the end of this report.

## What exists today

At SASE commit `fa61906da0978519d060f62eacd7417acaf02cb0`, the built-ins are effectively:

| Alias | Current route |
|---|---|
| `xsmall` | Sonnet medium / GPT-5.5 medium / Grok 4.6 medium / Gemini Flash |
| `small` | Sonnet high / GPT-5.5 high / Grok 4.6 high |
| `medium` | GPT-5.5 xhigh / Sonnet xhigh / Grok 4.6 xhigh |
| `large` | Claude Opus xhigh or GPT-5.6 Sol xhigh; Grok only as an ordered fallback |
| `xlarge` | Claude Fable 5 xhigh or GPT-6 Astra xhigh; Grok only as an ordered fallback |

The defaults also set `default_model: @large`, so an unspecified launch selects a frontier model at `xhigh`. That is the opposite of a quota-conserving default. More surprisingly, `@medium` is not medium-cost at all: it uses every participating provider at `xhigh`.

The model roster has also moved. OpenAI says GPT-5.5 retires from Codex sign-in use on 2026-10-14, with GPT-5.6 Sol as the replacement, while Terra and Luna now cover balanced and high-volume work respectively. Its current guidance describes Astra as the hardest-task model, Sol for complex open-ended work, Terra for everyday work, and Luna for clear or repeatable work. It also says to use the lowest reasoning effort that succeeds and that most tasks do not require `max` or `ultra`. ([OpenAI model lineup](https://developers.openai.com/api/docs/models), [Codex model and effort guidance](https://learn.chatgpt.com/docs/models))

Anthropic's current ladder is Haiku 4.5, Sonnet 5, Opus 5, and Fable 5.1. List prices are respectively $1/$5, $2/$10, $5/$25, and $10/$50 per million input/output tokens, and Anthropic positions Fable 5.1 for demanding long-horizon tasks rather than as the ordinary default. ([Claude model overview](https://platform.claude.com/docs/en/models/overview)) The currently installed Claude Code version is new enough for Fable 5.1, whose supported CLI model ID is `claude-fable-5-1`. ([Claude Code model configuration](https://support.claude.com/en/articles/11940350-claude-code-model-configuration))

Grok Build currently exposes Grok 4.6 and 4.5, not a separate cheap/fast family. Grok 4.6 supports `low`, `medium`, `high`, and `xhigh`, so effort is the only useful within-provider size control. xAI prices the API at $2 input / $6 output per million tokens and positions 4.6 as its coding and agentic frontier model. ([Grok 4.6](https://docs.x.ai/developers/models/grok-4.6), [Grok reasoning levels](https://docs.x.ai/developers/model-capabilities/text/reasoning))

## Why the current policy burns quota

### 1. The tiers are effort labels, not cost/capability tiers

`small`, `medium`, and `large` currently climb rapidly from `high` to `xhigh` without introducing the providers' actual economy models. This makes the name `medium` misleading and gives callers no route to Terra, Luna, or Haiku.

Effort is a major cost lever. Anthropic reports that, on several research and knowledge-work evaluations, `low` surrendered only 1–3 points while cutting cost per task by roughly one-third to one-half; `medium` often matched default accuracy at lower cost. Long-horizon coding is a notable exception, so the right response is escalation for the hard tail rather than `xhigh` everywhere. These are vendor-run evaluations, not independent guarantees, but the direction is consistent with OpenAI's guidance. ([Anthropic cost/intelligence guidance](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence))

### 2. The `large` route is structurally unfair to Grok

SASE's `A | B` pool round-robins across available members. In `(A | B) || C`, `C` is selected only when every primary member is unavailable or hard-disabled. It is not a one-third participant. Since unspecified launches currently use `@large`, normal work alternates Claude and Codex while Grok remains idle until both are unavailable.

A point-in-time `sase usage list` snapshot on 2026-09-18 illustrated exactly that failure mode: Claude showed 2% weekly headroom, Codex 14%, and Grok 65%. One observation cannot determine universal weights, but the shape is strong evidence that Grok should be a primary `large` member rather than an emergency tail.

Independent testing also makes Grok a defensible `large` peer, though not an obvious `xlarge` equal. Artificial Analysis reported a 44 intelligence-index score for Grok 4.6 xhigh versus 48 for Opus 5 high, with mixed sub-benchmarks: Grok led AutomationBench while Opus led Terminal-Bench 4.0 materially. Grok's measured cost per task was lower. A single aggregate benchmark should not choose production routing, but it supports keeping Grok in the difficult-work pool and reserving the top tier for Fable/Astra. ([Artificial Analysis comparison](https://artificialanalysis.ai/models/comparisons/grok-4-6-xhigh-vs-claude-opus-5-high))

### 3. Equal launches are not equal consumption

Unweighted round-robin is neutral only if providers have similar plan capacity and tasks consume similar quota. Neither is true. One long agent can cost more than many short ones; plan quotas and reset windows differ; Claude Fable can have its own applicability and limit behavior; and Grok's subscription telemetry is less precise.

Static weights in the shipped defaults would merely encode one user's current plans. They would become wrong after an upgrade, a provider policy change, or a different workload mix. Built-ins should therefore remain unweighted. Fairness should eventually be computed from normalized remaining headroom, reset time, and recent burn rate.

### 4. Ordered fallback is not runtime failover

In current SASE semantics, `||` is resolved before an agent starts. A provider that is already hard-disabled is avoided, but a usage-limit error discovered by the current invocation does not cause the alias tail to take over that invocation. The provider may be disabled for future launches, yet the active job still fails unless a separate provider retry fallback is configured. The present Claude retry default is same-provider Sonnet, and Codex/Grok do not have a cross-provider runtime fallback by default.

Consequently, elaborate `||` expressions provide less resilience than they appear to. Pools are appropriate for normal routing; ordered fallback should mean “acceptable degraded capability when the preferred class is unavailable,” not “automatic retry after an error.”

## Is the plan a good idea?

Yes, as a first layer. The model spread is now wide enough that choosing Luna or Haiku for checkable mechanical work, Terra or Sonnet for ordinary work, and frontier models only for the hard tail can plausibly multiply effective subscription capacity. OpenAI's own local-client estimates span about 5–45 messages per five hours for Astra, 10–100 for Sol, 25–200 for Terra, and 250–2,000 for Luna, with wide variation from context, reasoning, tools, and caching. Those are estimates rather than guarantees, but the order-of-magnitude separation is exactly what size aliases should exploit. ([Codex pricing and usage limits](https://learn.chatgpt.com/docs/pricing))

I would not make alias selection the whole strategy. “Use the smallest model” is only a proxy for the real objective: minimize quota per *successful* task subject to acceptable quality and latency. A cheaper first attempt that fails can cost more than one successful frontier attempt. Anthropic's own results even show Fable 5.1 at low effort beating Sonnet 5 default on cost per solved coding task in one workload, while becoming much more expensive on a long-research workload. The correct ranking is workload-dependent. ([Anthropic cost/intelligence guidance](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence))

The target architecture should combine:

- **A conservative initial route:** select a size from task shape, not perceived prestige.
- **A verifier:** tests, lint, rubric, explicit acceptance criteria, or another cheap deterministic signal.
- **Escalation on verified failure:** retry only the failing tail at the next effort/model class.
- **Quota-aware provider choice:** choose among capable providers by normalized projected headroom rather than launch count.
- **Budgets and context hygiene:** compact between phases, clear unrelated sessions, constrain output, and avoid repeatedly injecting large instructions. All three providers charge quota for context and reasoning, not merely the visible answer.

This is also why I recommend lowering the implicit SASE default to `@medium`. Keeping `default_model: @large` would blunt most of the savings: callers that omit an explicit size would still consume the difficult-work pool. The change should be piloted against SASE's own task history because it is a deliberate quality/cost tradeoff.

## Adjustments I made to the stated requirements

1. **I treat a “size” as a workload-and-effort class, not literal model size.** Grok has no current small model, so `grok-4.6@low` can participate in a small class even though the underlying model is frontier-sized.
2. **I optimize fairness for subscription headroom, not equal launch counts.** Equal count remains the portable built-in behavior only because current SASE lacks a headroom-aware selector.
3. **I recommend changing `default_model` as well as the alias definitions.** Without that adjacent change, ordinary unspecified work remains unnecessarily expensive.
4. **I exclude `agy/gemini-3.8-flash-high` from the final core pools.** The request identifies Claude, Codex, and Grok as the active providers, and I did not evaluate the Google/AGY route. If it is intentional spare capacity, it should be benchmarked and restored as an additional `xsmall` or `small` member rather than retained accidentally.
5. **I use pinned current Claude IDs.** Generic `sonnet`/`opus` aliases are convenient but allow upstream model changes to silently alter SASE's built-in cost and capability. Versioned built-ins are more reproducible and can be deliberately refreshed with releases.

## Rollout and evaluation

Before making the definitions default, update the SASE provider catalog and usage applicability for `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5-1`, `gpt-5.6-terra`, and `gpt-5.6-luna`. The current catalog predates several of them, even when the provider CLI itself can accept an explicit model string.

Then run a two-week shadow or controlled trial using historical task classes. Record at least:

- first-pass success and final verified success;
- total launches and escalations per completed task;
- elapsed time and output size;
- provider/model/effort;
- starting and ending usage-window headroom; and
- failures attributable to quota, model quality, transport, or context length.

Compare cost as quota percentage per verified completion, including failed attempts. Do not promote a smaller route merely because it emits fewer tokens. A reasonable guardrail is to keep a tier only if final success remains within an agreed margin while quota per verified completion falls.

The next routing feature should calculate a provider score approximately as:

`projected_headroom_at_reset = remaining_fraction - recent_burn_rate * time_to_reset`

Choose the highest-score provider among models qualified for the requested tier, with hysteresis so a small telemetry change does not cause oscillation. If telemetry is missing, fall back to unweighted round-robin. Separately, add alias-preserving runtime retry: after a confirmed usage-limit error hard-disables a provider, re-resolve the *same named alias* once and continue with a different provider. That is more robust than hard-coding cross-provider model names in every provider retry setting.

## Recommended solution

The tier contract should be:

| Alias | Intended work |
|---|---|
| `xsmall` | Triage, lookup, formatting, tiny mechanical edits with obvious checks |
| `small` | Clear, bounded implementation or analysis with local verification |
| `medium` | Normal agentic work, moderate ambiguity, ordinary multi-file changes |
| `large` | Difficult debugging, architecture, cross-cutting or high-value work |
| `xlarge` | Proven hardest long-horizon work; explicit use only |

Grok belongs in the first four primary pools because otherwise its subscription capacity is stranded. Its `xlarge` position remains a last-resort degradation because available independent evidence puts it closer to Opus/Sol-class work than to an unambiguous Fable/Astra replacement. No shipped pool should have provider weights; users may apply a temporary priority or custom weight when their own usage windows are asymmetric.

Start with these defaults:

```yaml
llm_provider:
  default_model: "@medium"
  epic_lander_model: "@large"
  big_epic_lander_model: "@xlarge"

  model_aliases:
    builtin:
      xsmall: >-
        claude/claude-haiku-4-5-20251001 |
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
        (claude/claude-fable-5-1@xhigh |
        codex/gpt-6-astra@xhigh) ||
        grok/grok-4.6@xhigh
```
