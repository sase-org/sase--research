# GLM-5.2 with SASE: integration and rollout recommendation

**Research date:** 2026-07-31  
**Scope:** Current SASE checkout, current Z.AI and OpenCode documentation, and two independent research reports.

## Bottom line

Use GLM-5.2 through SASE's existing `opencode` provider. For a low-commitment pilot, authenticate OpenCode's metered
Z.AI provider and select `opencode/zai/glm-5.2`. If the pilot succeeds and usage becomes regular, switch the alias to
the GLM Coding Plan model `opencode/zai-coding-plan/glm-5.2`. Expose `high` and `max` as explicit custom aliases and do
not add GLM to SASE's built-in role pools until it has passed a representative pilot.

This is the shortest path that preserves honest model identity, keeps Claude and Codex available side by side, exposes
GLM-5.2's native effort variants, and requires no SASE implementation change.

## What is being integrated

GLM-5.2 is Z.AI's long-horizon coding model. Z.AI documents a 1,000,000-token context window, 128K maximum output,
function calling, context caching, structured output, and MCP support. It exposes `high` and `max` reasoning effort;
Z.AI recommends `max` for complex coding. These characteristics make it plausible for SASE's long-running, tool-using
agents, but vendor benchmarks are not a substitute for a SASE-specific evaluation. See the
[GLM-5.2 model guide](https://docs.z.ai/guides/llm/glm-5.2) and
[model-switching guide](https://docs.z.ai/devpack/latest-model).

Z.AI supports both OpenCode and Claude Code as Coding Plan clients. The important architectural fact is that SASE does
not call an LLM API directly: it launches a supported coding-agent runtime and layers orchestration, workspace
isolation, directives, skills, interrupts, artifact capture, and finalization around it.

## Current SASE fit

At SASE commit `f55ce07d164d57b1c05d6585b191459adcc9e5e7`, OpenCode is already a registered, first-class LLM provider:

- `src/sase/llm_provider/opencode.py` invokes `opencode run --format json --model <provider/model> --dir <cwd>`.
- It maps SASE effort to OpenCode's provider-specific `--variant` flag.
- SASE preserves nested model IDs. For example, the provider prefix is `opencode` and the runtime-local model is
  `zai-coding-plan/glm-5.2`.
- It has explicit skill deployment, streamed-event parsing, usage collection, interrupt handling, install metadata,
  model-panel presentation, and the common SASE finalizer workflow.

The current Models.dev catalog identifies the subscription provider as `zai-coding-plan`, the metered provider as
`zai`, and GLM-5.2 as `glm-5.2`; it declares the model's 1M context and `high`/`max` reasoning options. OpenCode's own
tests cover those effort variants. OpenCode also documents Z.AI and Z.AI Coding Plan as separate choices in
`/connect`. See [OpenCode providers](https://opencode.ai/docs/providers/) and
[OpenCode authentication](https://opencode.ai/docs/cli/).

On this machine, Claude Code 2.1.220 is installed, while OpenCode is not. Installing one supported runtime is the only
extra integration step; no SASE code needs to be added.

## Resolving the two proposed architectures

The independent reports agreed that globally redirecting Claude Code to Z.AI is a poor durable configuration, but
disagreed on what should replace it.

| Route | Model isolation and identity | Work required | Assessment |
| --- | --- | ---: | --- |
| Existing SASE OpenCode provider | Clean per invocation; Claude/Codex remain independent | Install and authenticate OpenCode | **Best starting and durable path** |
| Global Claude Code redirect | Process-wide; Claude labels can conceal GLM routing | Small | Smoke test only |
| Per-shell Claude environment | Isolated to that launch, but still reported as Claude and awkward for mixed fan-out | Small | Diagnostic spike only |
| New `glm` provider around Claude Code | Can be clean if carefully implemented | Provider code, tests, maintenance | Contingency after evidence, not a prerequisite |
| Direct API provider inside SASE | Would need a complete agent harness | Large | Wrong abstraction level |
| Self-host GLM-5.2 weights | Requires a very large inference stack and agent harness | Very large | Not a sensible first route |

The case for a new Claude-backed `glm` provider is that it holds the harness constant when comparing Claude models to
GLM. That can matter in a controlled benchmark. It does not justify implementing and maintaining another provider
before the existing OpenCode path has been tried. OpenCode is already a supported SASE runtime with the same required
workflow capabilities, and Z.AI/OpenCode expose GLM as a native model with an accurate provider identity.

The Claude-provider research nevertheless found useful requirements for any future fallback implementation:

- Z.AI's official Claude route uses `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` and
  `ANTHROPIC_AUTH_TOKEN`. Those values must be injected only into the child process; changing
  `~/.claude/settings.json` would redirect unrelated Claude agents.
- A custom provider must remove ambient Anthropic credentials before calling a third-party endpoint and isolate its
  Claude config, ideally with Claude Code's documented `CLAUDE_CONFIG_DIR` support.
- Its skill deployment path must be `.claude`, not the provider-name default `.glm`.
- Claude Code requires the wire model `glm-5.2[1m]` plus `CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000` for the full
  context. SASE's colon-form `%model:` parser currently truncates a raw model at `[`, so such a provider should expose
  a bracket-free SASE name and translate it internally. OpenCode avoids this problem: its model ID is simply
  `glm-5.2`, with the 1M limit carried in model metadata.

These are good contingency requirements, not reasons to take on the contingency now.

## Billing and quota choice

There are two useful billing routes through the same OpenCode/SASE integration:

1. **Metered API:** use `opencode/zai/glm-5.2`. Z.AI currently lists $1.40 per million input tokens, $0.26 per million
   cached-input tokens, and $4.40 per million output tokens. This is the safer first pilot because it avoids buying a
   non-refundable, auto-renewing subscription before GLM has passed the workflow test. See
   [Z.AI API pricing](https://docs.z.ai/guides/overview/pricing).
2. **GLM Coding Plan:** use `opencode/zai-coding-plan/glm-5.2`. Monthly list prices are currently $18 Lite, $72 Pro,
   and $160 Max. It is likely easier to budget for sustained agent work, but fan-out can consume the rolling and
   weekly quotas quickly. See the [Coding Plan page](https://z.ai/subscribe) and
   [usage policy](https://docs.z.ai/devpack/usage-policy).

Quota documentation is in transition. The live Coding Plan overview currently specifies credit-based limits:
Lite 2,000 credits per five hours / 10,000 weekly; Pro 12,000 / 60,000; Max 28,000 / 140,000. It also says off-peak
model usage is charged at 50% of the standard credit rate. An [older FAQ](https://docs.z.ai/devpack/faq) still
describes approximate prompt counts.
Use the [current overview](https://docs.z.ai/devpack/overview) and the account's live usage dashboard for plan sizing;
do not design SASE concurrency around the stale prompt-count estimates.

The Coding Plan is restricted to supported coding tools and individual use. OpenCode is explicitly supported, and
SASE invokes the OpenCode CLI rather than using the plan as a general-purpose API. Do not put a Coding Plan key behind
a custom service, share it across users, or confuse its dedicated endpoint with the normal metered API.

## Security and data handling

- Prefer `opencode auth login` over an environment variable or repository config. OpenCode stores provider
  credentials in `~/.local/share/opencode/auth.json`; SASE already recognizes that file as OpenCode auth evidence.
- The catalog's environment variable is `ZHIPU_API_KEY`. SASE's current offline OpenCode auth check does not recognize
  that variable, so environment-only auth can produce a doctor false negative even if OpenCode itself works.
- Review what repositories may be sent to the model host. Z.AI's current API Data Processing Addendum says API prompt
  and generated content are processed in real time and not stored, and that customer data is generally processed in
  Singapore. That is a useful vendor representation, not a substitute for the user's own confidentiality, client, or
  employer policy. See the [Z.AI privacy policy and API DPA](https://docs.z.ai/legal-agreement/privacy-policy).
- Treat 1M tokens as capacity, not a target. Let the runtime retrieve relevant files instead of eagerly sending an
  entire repository; this improves latency and quota efficiency.

## Concrete rollout

### 1. Install OpenCode

```bash
npm install -g opencode-ai
```

The command is documented by [OpenCode's installation guide](https://opencode.ai/docs/). Confirm SASE sees it with:

```bash
sase agent-cli list -v
```

### 2. Start with a metered key

Run:

```bash
opencode auth login
```

Select **Z.AI** for the metered pilot. After authentication, verify the runtime independently:

```bash
opencode run --model zai/glm-5.2 --variant high "Reply with exactly: GLM52_OK"
```

Then perform a harmless read-tool task so authentication, model selection, reasoning variant, and tool calling are all
tested before SASE is involved.

### 3. Add explicit SASE aliases

Add these to the effective user `sase.yml` (or its chezmoi source if that file is managed there):

```yaml
llm_provider:
  model_aliases:
    custom:
      glm52_high:
        model: opencode/zai/glm-5.2@high
        description: "GLM-5.2 via OpenCode and the metered Z.AI API, high effort."
      glm52_max:
        model: opencode/zai/glm-5.2@max
        description: "GLM-5.2 via OpenCode and the metered Z.AI API, maximum effort."
```

Launch explicitly with `%model:@glm52_high` or `%model:@glm52_max`. Keep `@default`, `@smart`, `@cheap`, and the phase
worker aliases unchanged during the pilot.

For regular subscription use, authenticate **Z.AI Coding Plan** in OpenCode and change only the model targets:

```yaml
model: opencode/zai-coding-plan/glm-5.2@high
```

and:

```yaml
model: opencode/zai-coding-plan/glm-5.2@max
```

This explicit provider distinction prevents accidental use of the wrong billing route.

### 4. Run a representative pilot

Use at least five paired tasks against the current preferred SASE model: an architecture audit, bounded bug fix,
cross-file refactor, long-context task, and two concurrent agents. Compare completion and test pass rate, scope
discipline, tool failures, wall time, interrupt behavior, finalizer/skill compliance, usage, and quota consumption.
Use `high` for routine work and reserve `max` for difficult debugging or long-horizon changes.

Only after the pilot should GLM join a role pool. Start with a narrow, low-risk role such as an explicit research or
small-worker alias; observe a full quota cycle before considering `@cheap` or broader defaults.

## Sources

- [Z.AI GLM-5.2 model guide](https://docs.z.ai/guides/llm/glm-5.2)
- [Z.AI model-switching and effort guide](https://docs.z.ai/devpack/latest-model)
- [Z.AI Coding Plan overview](https://docs.z.ai/devpack/overview)
- [Z.AI Coding Plan FAQ](https://docs.z.ai/devpack/faq)
- [Z.AI Coding Plan usage policy](https://docs.z.ai/devpack/usage-policy)
- [Z.AI API pricing](https://docs.z.ai/guides/overview/pricing)
- [Z.AI privacy policy and API DPA](https://docs.z.ai/legal-agreement/privacy-policy)
- [OpenCode installation](https://opencode.ai/docs/)
- [OpenCode provider setup](https://opencode.ai/docs/providers/)
- [OpenCode CLI and authentication](https://opencode.ai/docs/cli/)
- Local SASE source at `f55ce07d164d57b1c05d6585b191459adcc9e5e7`
- Models.dev source at `499df6cc344356909419c225fa7d897da57e61d3`
- OpenCode source at `19231fce4b70aa5f7894a0a0eb20ff29bd417db5`

## Recommended solution

Install OpenCode and run GLM-5.2 through SASE's existing `opencode` provider. Begin with explicit `@glm52_high` and
`@glm52_max` aliases targeting the metered `opencode/zai/glm-5.2` model, complete a five-task SASE pilot, then switch
those aliases to `opencode/zai-coding-plan/glm-5.2` on a monthly Lite plan if usage is regular and the live quota
dashboard shows adequate headroom. Keep GLM out of SASE's built-in role pools until the pilot demonstrates quality,
workflow compatibility, and sustainable quota use. Build a separate Claude-backed `glm` provider only if controlled
testing later proves that the OpenCode harness—not GLM itself—is the limiting factor.
