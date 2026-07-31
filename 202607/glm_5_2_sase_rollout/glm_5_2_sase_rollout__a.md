# Using GLM-5.2 with SASE

**Research date:** 2026-07-31  
**Question:** What is the best way to add GLM-5.2 to an existing SASE workflow?  
**Bottom line:** SASE should continue to orchestrate a coding-agent CLI. It does not need a new direct GLM API provider.

## Scope and method

This analysis combines:

- the current SASE checkout at commit `6e96deaf8fdb94af4e3080a92882f0394d4ded55`;
- read-only inspection of the agent CLIs installed on this machine;
- Z.AI's current GLM-5.2, Coding Plan, pricing, and integration documentation;
- OpenCode's current provider documentation; and
- the OpenCode/Models.dev catalog at commit `c00ef3ebfcf1105acd6956f74a769df9b5cf0518`.

No provider was installed, no API key was requested, and no paid request was made as part of this research.

## What GLM-5.2 offers

GLM-5.2 is Z.AI's flagship text model for long-horizon work. Its documented limits are a 1,000,000-token context and
131,072 output tokens. It supports tool calling, context caching, structured output, and two effective reasoning-effort
levels: `high` and `max`; deep thinking is enabled by default. These characteristics are unusually well aligned with
SASE's long-running, tool-using coding agents. See the [GLM-5.2 model guide](https://docs.z.ai/guides/llm/glm-5.2) and
[migration guide](https://docs.z.ai/guides/overview/migrate-to-glm-new).

Z.AI reports 81.0 on Terminal-Bench 2.1 and 62.1 on SWE-bench Pro, plus strong results on longer-horizon benchmarks.
Those are promising signals, but they are vendor-reported and harness-dependent; they do not substitute for a pilot on
SASE prompts, repositories, hooks, and verification rules. The model's main reason to test is not a leaderboard number
but its combination of long context, tool use, and explicit effort control. See Z.AI's
[release analysis](https://z.ai/blog/glm-5.2).

For direct API usage, Z.AI currently lists prices per million tokens of $1.40 input, $0.26 cached input, and $4.40
output. The separate GLM Coding Plan starts at $18/month for Lite, with Pro at $72/month and Max at $160/month; annual
billing currently advertises discounts. Prices, promotions, and quotas can change, so the live
[API pricing](https://docs.z.ai/guides/overview/pricing) and
[Coding Plan page](https://z.ai/subscribe) should be checked immediately before purchase.

The plan has rolling five-hour and weekly limits, and Z.AI recommends Lite for one project, Pro for one or two
concurrent projects, and Max for two or more. That matters for SASE because parallel agent fan-out can consume quota
and concurrency much faster than an interactive chat. The plan is also restricted to supported coding tools. OpenCode
and Claude Code are explicitly supported, so invoking either through SASE preserves the intended tool boundary. See
the [Coding Plan usage policy](https://docs.z.ai/devpack/usage-policy).

## The relevant SASE architecture

SASE does not call model APIs directly. It launches a supported coding-agent CLI through a thin provider adapter, then
adds common orchestration: prompt preprocessing, isolated workspaces, streamed output, usage capture, tool-call
artifacts, interrupts, retries, and provider-neutral commit finalization.

The current built-in LLM providers are Claude Code, Codex, Qwen Code, OpenCode, Antigravity, and the test-only Fakey
provider. The important local implementation details are:

- `src/sase/llm_provider/opencode.py` launches
  `opencode run --format json --dangerously-skip-permissions --model <provider/model> --dir <cwd>`.
- SASE translates a requested OpenCode effort to `--variant <level>`.
- Explicit nested model IDs are supported. Local resolution of
  `opencode/zai-coding-plan/glm-5.2@max` produced exactly
  `('opencode', 'zai-coding-plan/glm-5.2', 'max')`.
- A described custom alias makes an otherwise external model discoverable in SASE's completion and Models-panel
  surfaces.
- OpenCode runs receive the same SASE commit-finalizer and skill workflow as other runtimes.

This means GLM-5.2 already fits the SASE provider contract. The choice is which existing CLI should host it.

### Current machine state

The read-only `sase agent-cli list -v -j --offline` inventory showed:

| Runtime | State | Version |
| --- | --- | ---: |
| Claude Code | installed | 2.1.220 |
| Codex | installed | 0.146.0 |
| Qwen Code | installed | 0.21.2 |
| Antigravity | installed | 1.1.9 |
| OpenCode | **not installed** | latest catalog version 1.18.10 |

OpenCode therefore adds one installation and authentication step. It does not require a SASE implementation change.

## Integration options

| Option | Coexists with real Claude/Codex | Accurate SASE model identity | Native GLM effort/context | Setup | Verdict |
| --- | --- | --- | --- | --- | --- |
| OpenCode + Z.AI Coding Plan | Yes | Yes | Yes | Install and authenticate OpenCode | Best durable path |
| OpenCode + Z.AI direct API | Yes | Yes | Yes | Same runtime; metered key | Best short paid pilot or irregular use |
| Claude Code + Z.AI Coding Plan | Not cleanly with one global Claude config | Potentially confusing | Yes | Claude is already installed | Fast proof of concept, weaker long-term fit |
| OpenCode + OpenRouter/another host | Yes | Yes | Host-dependent | Extra intermediary | Useful fallback, not first choice |
| New SASE GLM provider plugin | Yes | Yes | Would need implementation | High | Unnecessary duplication |
| Self-host the open weights | Yes | Yes | Serving-stack-dependent | Very high | Impractical for ordinary home-server use |

### Option 1: OpenCode with Z.AI Coding Plan

This is the cleanest architectural fit. OpenCode is already a first-class SASE provider, while Z.AI and OpenCode both
document Z.AI Coding Plan authentication. The current provider/model selector is
`zai-coding-plan/glm-5.2`. The catalog declares a 1M context, 131,072 output limit, tool use, and `high`/`max` reasoning
variants. See the [OpenCode Z.AI provider instructions](https://opencode.ai/docs/providers) and the pinned
[provider catalog](https://github.com/anomalyco/models.dev/blob/c00ef3ebfcf1105acd6956f74a769df9b5cf0518/providers/zai-coding-plan/provider.toml).

This route has four advantages over redirecting an existing runtime:

1. GLM gets a distinct SASE identity: provider `opencode`, model `zai-coding-plan/glm-5.2`.
2. Existing Claude, Codex, Qwen, and Antigravity agents continue to use their current services.
3. SASE can select GLM per prompt, per alias, per phase, or as one branch of a multi-model fan-out.
4. OpenCode's native model metadata exposes the correct effort variants without pretending GLM is an Anthropic model.

The main drawback is that OpenCode is not yet installed. Also, SASE currently uses OpenCode's normal XDG data and
configuration directories rather than a shadow home. Initial multi-agent tests should therefore include concurrent
runs and inspection of session/tool artifacts, not only a single happy-path prompt.

### Option 2: OpenCode with the direct Z.AI API

OpenCode's direct metered selector is `zai/glm-5.2`; the Coding Plan selector is
`zai-coding-plan/glm-5.2`. The distinction is important because the plan and general API use different billing routes.
Z.AI documents `https://api.z.ai/api/coding/paas/v4` for OpenAI-compatible Coding Plan tools and
`https://api.z.ai/api/paas/v4` for the normal pay-as-you-go API.

The direct API is attractive for a small, deliberately capped evaluation because it avoids buying a non-refundable,
auto-renewing subscription before the model has passed a SASE-specific trial. It becomes less predictable for large
repositories and long agent trajectories, where input, cached-input, and output-token patterns vary substantially.
For regular SASE use, the Coding Plan is likely easier to budget, provided its rolling quota and concurrency limits are
acceptable.

### Option 3: Claude Code with Z.AI Coding Plan

Z.AI officially documents an Anthropic-compatible Claude Code route. It uses
`ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic`, an `ANTHROPIC_AUTH_TOKEN`, and model mappings such as
`glm-5.2[1m]`; the `[1m]` suffix plus `CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000` enables the million-token window.
Claude Code effort values `low` through `high` map to GLM `high`, while `xhigh` and `max` map to GLM `max`. See the
[current Claude Code setup](https://docs.z.ai/devpack/tool/claude) and
[GLM-5.2 switching guide](https://docs.z.ai/devpack/latest-model).

This route would probably produce the fastest first response on this machine because Claude Code is already installed
and SASE already passes `--model` and `--effort`. It is not the best durable configuration, however. The base URL and
authentication live in Claude Code's global settings. Redirecting that runtime to Z.AI can silently turn SASE prompts
that appear to request Claude into GLM calls, confuse provider/model statistics, and make side-by-side Claude-versus-GLM
evaluation awkward. A separate wrapper/config environment could isolate the two, but at that point OpenCode is simpler
and more explicit.

Claude Code is therefore a reasonable disposable proof of concept if replacing the machine's Claude route is
acceptable. It is not the recommended multi-provider SASE setup.

### Other routes

OpenRouter and other GLM hosts can also be reached through OpenCode. They are useful if Z.AI availability, regional
routing, or plan limits become problematic, but add another pricing, retention, routing, and compatibility boundary.
OpenRouter currently advertises GLM-5.2 with a 1M context and `high`/`xhigh` effort mapping, but its displayed price is
promotional and should not anchor a long-term design. See the
[current OpenRouter model page](https://openrouter.ai/z-ai/glm-5.2/api).

A new SASE `sase_llm` plugin that calls the Z.AI API directly would have to recreate an agent harness: tool execution,
permissions, streaming, interrupts, session behavior, skill discovery, and artifact normalization. That is the wrong
abstraction level when OpenCode and Claude Code already provide those capabilities and SASE already integrates both.

Although GLM-5.2's weights are MIT-licensed, its published model card reports roughly 753B parameters. Practical
self-hosting would require substantial multi-GPU infrastructure plus an inference and agent-harness stack. It is not
the sensible first route for this home server. See the official
[GLM-5.2 model card](https://huggingface.co/zai-org/GLM-5.2).

## Proposed OpenCode rollout

### 1. Choose the billing path

For a tiny evaluation, use a direct Z.AI API key and `zai/glm-5.2`. For continued SASE use, start with one month of the
Lite Coding Plan and `zai-coding-plan/glm-5.2`; upgrade only if rolling quota or concurrency is demonstrably limiting.
Avoid annual billing until the SASE pilot is complete.

### 2. Install and authenticate OpenCode

```bash
npm install -g opencode-ai
opencode auth login
```

Select **Z.AI Coding Plan** for a plan key, or **Z.AI** for a metered API key. Prefer OpenCode's credential store over
putting the key in a repository or command line. The interactive login writes
`~/.local/share/opencode/auth.json`, which SASE's offline auth doctor already recognizes.

An environment-only setup can use `ZHIPU_API_KEY`, but the current SASE OpenCode auth-evidence list does not recognize
that variable. This is only a doctor false negative—the runtime can still work. The gap was recorded as task bead
`sase-cs`; using `opencode auth login` avoids it today.

### 3. Verify OpenCode before involving SASE

For a Coding Plan key:

```bash
opencode run \
  --model zai-coding-plan/glm-5.2 \
  --variant max \
  "Reply with exactly: GLM52_OK"
```

A good smoke test should then require a harmless read tool call, not merely a text response. This separately verifies
authentication, the selected billing route, the model, tool calling, and final output.

### 4. Add explicit SASE aliases

Merge the following into the effective user `sase.yml` (or its chezmoi source if that is how the file is managed):

```yaml
llm_provider:
  model_aliases:
    custom:
      glm52:
        model: opencode/zai-coding-plan/glm-5.2@max
        description: GLM-5.2 via OpenCode and Z.AI Coding Plan, with maximum reasoning.
      glm52_high:
        model: opencode/zai-coding-plan/glm-5.2@high
        description: GLM-5.2 via OpenCode and Z.AI Coding Plan, with lower-cost reasoning.
```

For direct metered API use, replace `zai-coding-plan/glm-5.2` with `zai/glm-5.2`.

Launch with:

```text
%model:@glm52
```

or:

```text
%model:@glm52_high
```

Do not change `@default`, `@smart`, or `@smartest` during the pilot. An explicit alias prevents accidental broad
rollout and makes every GLM invocation visible in prompts, SASE metadata, the Agents tab, and statistics.

### 5. Run a representative SASE pilot

Use at least five tasks, ideally paired against the current preferred model:

1. a read-only repository architecture audit;
2. a bounded bug fix with a failing test;
3. a cross-file refactor with strict scope constraints;
4. a long-context research or migration task; and
5. two concurrent agents to expose quota, state, or session contention.

Evaluate completion rate, unnecessary edits, instruction adherence, test discipline, tool failures, wall-clock time,
token/cache usage, interrupt behavior, commit-finalizer compliance, and quota consumption. Use `high` for ordinary work
and reserve `max` for complex debugging, large refactors, and long-horizon tasks. The purpose of the pilot is to decide
where GLM belongs in SASE's role aliases, not merely whether it can answer a prompt.

## Operational cautions

- **Keep the endpoint and billing product aligned.** A Coding Plan key belongs on the Coding Plan route; a normal API
  key belongs on the general route. A mismatch can cause authentication, quota, or billing surprises.
- **Do not commit API keys.** Use OpenCode's auth store or a private secret-loading mechanism.
- **Treat 1M as capacity, not a target.** Sending unnecessary repository context increases latency, cache pressure, and
  quota consumption. Let the agent retrieve relevant files through tools.
- **Expect SASE fan-out to amplify usage.** Plan sizing should be based on concurrent agent behavior, not interactive
  prompt counts alone.
- **Check data policy before proprietary-code use.** Repository content and tool results are sent to the selected model
  host. Review Z.AI's current retention and privacy terms for the relevant product and region.
- **Watch OpenCode concurrency initially.** SASE's OpenCode adapter uses shared normal XDG state rather than isolated
  shadow homes. The built-in integration is designed for SASE, but a two-agent smoke test is still warranted.
- **Pin identity, not an old CLI.** Install the current OpenCode release and record its version in any benchmark notes;
  do not permanently pin the research-time version unless a regression requires it.

## Recommended solution

Install OpenCode and use SASE's existing `opencode` provider with the native
`zai-coding-plan/glm-5.2` model, exposed initially through explicit `@glm52` (`max`) and `@glm52_high` (`high`) custom
aliases. Start on a monthly Lite Coding Plan for regular agent work—or use `zai/glm-5.2` with the direct API for a small
capped smoke test before subscribing—then run a representative five-task pilot before changing any built-in SASE role
alias.

This is the best solution because it requires no SASE code or new provider plugin, preserves the machine's existing
Claude/Codex/Antigravity routes, gives GLM-5.2 an honest provider/model identity in SASE, supports its native 1M context
and `high`/`max` effort levels, and keeps rollback as simple as removing one custom alias and OpenCode credential.
