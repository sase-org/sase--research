# Running GLM 5.2 Under SASE

Research date: 2026-07-31. Investigated by an agent working in the `sase` repo (`sase_17` workspace), against
`sase==0.14.0` and Claude Code `2.1.220`.

## The question

You want to start using GLM 5.2 with SASE. What is the best way to wire it in so that it behaves like a first-class
SASE model — selectable per agent via `%model`, visible in the Models panel and agent headers, usable inside alias
pools like `@cheap`, and compatible with the hooks, skills, and commit workflow SASE already depends on?

Short answer: **do not point your global Claude Code config at Z.ai.** Register GLM as its own SASE LLM provider that
reuses the Claude Code CLI as a harness but injects Z.ai's Anthropic-compatible endpoint per subprocess. Details and
the reasoning are below.

---

## 1. What GLM 5.2 actually is

- Released **2026-06-13** by Zhipu AI / Z.ai as the successor to GLM-5.1 in the GLM-5 family. Mixture-of-Experts,
  roughly **753B total parameters with ~40B active per token**, shipped under an **MIT** license with downloadable
  weights.
- **1M-token context window**, up to ~128K output tokens. Two reasoning-effort levels: **High** and **Max** (Max is
  the recommended setting for complex coding).
- Purpose-built for coding, tool calling, and agentic loops. Supports Anthropic-compatible tool calling, structured
  output, context caching, and MCP.
- Two consumption models:
  - **GLM Coding Plan subscription** — Lite $18/mo, Pro $72/mo, Max $160/mo, Team. Quota is **prompt-based on a
    rolling 5-hour window** plus a weekly cap (Lite ≈ 80 prompts/5h and ≈ 400/week; Pro ≈ 400/5h and ≈ 2,000/week;
    Max ≈ 1,600/5h and ≈ 8,000/week). GLM-5.2 burns quota at a **2× multiplier off-peak and 3× during peak hours
    (14:00–18:00 UTC+8)**, with a promotion reportedly dropping off-peak to 1× through September 2026.
  - **Metered API** — approximately **$1.40 / 1M input, $0.26 / 1M cached input, $4.40 / 1M output**.

### Endpoints and model IDs

| Surface                            | Value                                     |
| ---------------------------------- | ----------------------------------------- |
| Anthropic-compatible base URL      | `https://api.z.ai/api/anthropic`          |
| OpenAI-compatible base URL         | `https://api.z.ai/api/coding/paas/v4`     |
| Flagship model ID                  | `glm-5.2`                                 |
| 1M-context variant (Claude Code)   | `glm-5.2[1m]` — brackets included         |
| Cheap/"haiku slot" models          | `glm-4.7`, `glm-4.5-air`                  |

Z.ai's own Claude Code documentation is a settings file that sets `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
`ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, and
`API_TIMEOUT_MS=3000000`. The `[1m]` suffix appears only in the model-switching guide, not the base setup page — treat
the bracketed form as the one to use when you want the full 1M window.

This is the key structural fact: **GLM is delivered through an Anthropic-shaped API**, so any harness that speaks the
Anthropic Messages protocol — Claude Code included — can drive it without a protocol adapter.

---

## 2. How SASE decides which model runs (verified against the code)

Everything below was read directly out of this workspace, not recalled.

**Providers are pluggy plugins.** `pyproject.toml:149` registers the `sase_llm` entry-point group; today it holds six
providers:

```toml
[project.entry-points."sase_llm"]
agy      = "sase.llm_provider.agy:AgyProvider"
claude   = "sase.llm_provider.claude:ClaudeCodeProvider"
codex    = "sase.llm_provider.codex:CodexProvider"
fakey    = "sase.llm_provider.fakey:FakeyProvider"
opencode = "sase.llm_provider.opencode:OpenCodeProvider"
qwen     = "sase.llm_provider.qwen:QwenProvider"
```

`src/sase/llm_provider/_hookspec.py` defines the full contract. A provider is essentially: one `llm_invoke` dispatch
hook plus ~14 metadata hooks (identity, known model names, short aliases, skill deploy path, CLI color, autodetect
priority and CLI name, auth evidence, install metadata, retry defaults, picker visibility).

**Model resolution.** `registry.py:312 resolve_model_provider_with_effort()` resolves a `%model` value in three
strategies, in order:

1. Configured alias (`@cheap`, `@coder`, …) → expanded target.
2. Explicit `provider/model` syntax → `("glm", "glm-5.2")`.
3. Implicit lookup in the plugin-supplied `model_to_provider` map → a bare `opus` finds `claude`.

Anything unmatched falls back to the default provider. So **a provider only becomes addressable once it is a
registered entry point** — there is no config-only path to a new backend.

**The Claude provider inherits ambient environment.** `claude.py:256` builds argv as:

```python
["claude", "-p", "--verbose", "--model", model_alias,
 "--output-format", "stream-json", "--dangerously-skip-permissions",
 "--session-id", session_uuid]
```

and `claude.py:329` calls `subprocess.Popen(args, …)` **with no `env=` kwarg** — the child inherits `os.environ`
verbatim. Two siblings already do better: `codex.py:463` yields a curated env with a shadow `CODEX_HOME`, and
`agy.py:575` copies and augments the env with `NO_COLOR`/`TERM`. **Per-provider env injection is an established
pattern in this codebase**, which is what makes the recommended design cheap.

**Skill deployment defaults are name-derived.** `_init_skills_sources.py:29` sets `primary = f".{provider}"` unless
the plugin overrides `llm_skill_deploy_subpath`. A provider named `glm` would therefore deploy SASE skills to
`~/.glm/skills` — invisible to a Claude Code process reading `~/.claude/skills`. This is the single most likely
silent failure in a naive implementation.

**Alias roles are where cost policy lives.** `model_alias_policy.py` defines the implicit aliases and their current
defaults:

```python
SMARTEST_MODEL_ALIAS_DEFAULT = "claude/claude-fable-5 || codex/gpt-5.6-sol"
CHEAP_MODEL_ALIAS_DEFAULT    = "claude/opus@medium | codex/gpt-5.5"
CHEAPER_MODEL_ALIAS_DEFAULT  = "claude/sonnet | codex/gpt-5.3-codex-spark"
CHEAPEST_MODEL_ALIAS_DEFAULT = "claude/haiku || codex/gpt-5.3-codex-spark"
```

`|` is a round-robin pool, `||` is ordered fallback. `xsmall_phase_worker → @cheaper`, `small_phase_worker → @cheap`,
`medium_phase_worker → @default@high`. **This is the natural insertion point for GLM**: it is the cheapest capable
coding model on the table, so it belongs in the `@cheap`/`@cheaper` pools long before it belongs at `@default`.

**Other integration points a new provider automatically picks up:**

- `SASE_GLM_PATH` executable override, derived by `_registry_metadata.py:10 provider_path_env_var()` — no hardcoded
  list to edit.
- `provider_cli_available()` gating for the ACE Models panel, driven by `llm_autodetect_cli_name`.
- Agent-name suffixes from `llm_provider_short_name` (e.g. `foo.cld`, `foo.opc`).
- `model_label.py` header rendering, which falls back to `provider_cli_status_color_map()` and a `#AF87D7` default for
  any provider that is not `claude` or `codex`.
- `sase doctor` provider readiness and auth-evidence rows, plus `sase agent-cli list` install/update handling.
- An automatic `@glm_coder` alias via `PROVIDER_CODER_ALIAS_SUFFIX`.

---

## 3. A verified gotcha: `%model:` truncates `glm-5.2[1m]`

Run in this workspace against installed `sase`:

```
'%model:claude/glm-5.2[1m]'   -> 'claude/glm-5.2'      effort=None
'%model:glm/glm-5.2[1m]@high' -> 'glm/glm-5.2'         effort=None     # <-- effort silently dropped too
'%model(claude/glm-5.2[1m])'  -> 'claude/glm-5.2[1m]'  effort=None     # parenthesized form survives
'%model:glm/glm-5.2@high'     -> 'glm/glm-5.2'         effort='high'
```

The colon form of the directive terminates its value at `[`, so the bracketed 1M model ID is **silently downgraded to
the standard-context model**, and any trailing `@<effort>` is swallowed with it. There is no error — you would just
quietly get a 200K-ish context agent that you believed had 1M.

**Consequence for the design:** never surface a model ID containing `[` to the `%model` layer. Expose a bracket-free
SASE-side name (`glm-5.2-1m`) and translate it to `glm-5.2[1m]` inside the provider when it builds argv. This is worth
a task bead independently — the truncation is a general directive-parser sharp edge, not a GLM-specific one.

---

## 4. Option space

### Option A — Point `~/.claude/settings.json` at Z.ai

Paste Z.ai's documented `env` block into the global Claude Code settings file.

- **Pro:** five minutes; zero code.
- **Con:** it is an all-or-nothing hijack. Every SASE agent, every `sase commit` finalizer, every one-shot invocation
  becomes GLM. `%model claude/opus` would still say "opus" in the ACE header and in chat metadata while actually
  running GLM — statistics, the Models panel, and the `@smartest`/`@cheap` pools all become lies. You also cannot run
  Claude and GLM concurrently, which defeats the point of load-balanced alias pools. And your `~/.claude/settings.json`
  is chezmoi-managed, so this fights your dotfiles.
- **Verdict:** acceptable as a 10-minute smoke test, unacceptable as the answer.

### Option B — Per-launch shell environment

`ANTHROPIC_BASE_URL=… ANTHROPIC_AUTH_TOKEN=… sase agent …` with `%model claude/glm-5.2`.

- **Pro:** no code, no global mutation, and it exercises the real path end to end.
- **Con:** still process-global for that agent; no alias integration; display still says `CLAUDE(glm-5.2)`; trivially
  forgotten; and it leaks your Anthropic credentials into the same process (see §6).
- **Verdict:** this is the right **spike**, not the right destination.

### Option C — A first-class `glm` provider that reuses the Claude Code harness ✅

Register `glm = "sase.llm_provider.glm:GlmProvider"` in the `sase_llm` group. It launches the same `claude` binary but
with a curated subprocess env pointing at `https://api.z.ai/api/anthropic`.

- **Pro:** everything SASE already knows how to do keeps working — hooks, skills, the stream-json parser, tool-call
  capture, usage artifacts, the commit finalizer, retry config, doctor, agent-cli update. Per-agent selection via
  `%model glm/glm-5.2-1m`, correct `GLM(glm-5.2-1m)` headers, real per-model statistics, and GLM as a pool member in
  `@cheap`/`@cheaper`. Anthropic and Z.ai run side by side.
- **Con:** ~250 lines of new provider code plus tests, doctor coverage, and default-config documentation.
- **Verdict:** recommended.

### Option D — Route through the existing `opencode` provider

OpenCode natively supports Z.ai as a provider, so `%model opencode/zai-coding-plan/glm-5.2` needs zero SASE code.

- **Pro:** genuinely zero implementation. Useful as a fallback if the Claude Code path hits a wall.
- **Con:** it is a different harness. OpenCode deploys SASE skills to `.config/opencode`, uses a different
  stream/JSON parser (`stream_and_parse_opencode_json_output`), a different effort flag (`--variant` rather than
  `--effort`), and a different hook surface. You would be running GLM in the runtime you have invested least in, and
  behavioral differences would be attributed to the model when they are really the harness.
- **Verdict:** viable escape hatch, not the primary plan.

### Option E — Adopt a new agent CLI (Z.ai's own tool, Crush, Pi, …)

- Maximum work: a whole new CLI to detect, update, parse, and teach SASE's hooks and skills about. No compensating
  benefit given GLM already speaks Anthropic. **Reject.**

### Option F — OpenRouter instead of Z.ai direct

Same mechanism, different base URL and key; per-token billing instead of a subscription quota.

- Worth keeping as a **second alias target** for overflow once the 5-hour Z.ai window is exhausted — e.g.
  `cheaper: "glm/glm-5.2-1m || glmor/glm-5.2"`. Not the starting point, because the subscription is where the cost
  advantage lives.

---

## 5. Recommended solution

**Add a `glm` LLM provider plugin in-repo that drives the Claude Code CLI against Z.ai's Anthropic-compatible
endpoint, then introduce GLM through the cheap alias pools rather than as `@default`.**

### 5.1 Provider sketch

New file `src/sase/llm_provider/glm.py`. It should reuse `ClaudeCodeProvider`'s invoke loop and stream parsing (the
stream-json event schema is emitted by the Claude Code client, not by the backend, so it is unaffected by swapping the
API host), overriding only identity, model names, and the subprocess environment.

| Hook                             | Value                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------- |
| `llm_provider_name`              | `"glm"`                                                                      |
| `llm_provider_short_name`        | `"glm"` (agent suffixes become `foo.glm`)                                    |
| `llm_known_model_names`          | `["glm-5.2-1m", "glm-5.2", "glm-4.7", "glm-4.5-air"]` — **no brackets**       |
| `llm_resolve_model_name`         | large → `glm-5.2-1m`, small → `glm-4.7`                                      |
| `llm_skill_deploy_subpath`       | **`".claude"`** — must be explicit, or skills land in `~/.glm`               |
| `llm_autodetect_cli_name`        | `"claude"`                                                                   |
| `llm_autodetect_priority`        | omit, or a large number (≥40) so `claude` still wins autodetect at priority 0 |
| `llm_cli_status_color`           | a distinct hue so `GLM(...)` headers are visually separable from `CLAUDE(...)` |
| `llm_auth_evidence`              | `api_key_env_vars: ["ZAI_API_KEY", "GLM_API_KEY"]`, no credential paths       |
| `llm_install_metadata`           | same npm package `@anthropic-ai/claude-code`, display name "Claude Code (GLM via Z.ai)" |
| `llm_default_retry_config`       | Claude's patterns plus Z.ai quota/rate-limit strings                          |

The one genuinely new piece of logic:

```python
_SASE_TO_ZAI_MODEL = {"glm-5.2-1m": "glm-5.2[1m]"}   # bracket-free names in, wire names out

def _glm_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    # Never forward Anthropic credentials to a third-party endpoint.
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
        env.pop(key, None)
    env["ANTHROPIC_BASE_URL"] = os.environ.get("SASE_GLM_BASE_URL", "https://api.z.ai/api/anthropic")
    env["ANTHROPIC_AUTH_TOKEN"] = _require_zai_key()
    env["API_TIMEOUT_MS"] = "3000000"
    return env
```

…and passing `env=` to `subprocess.Popen`, exactly as `codex.py:463` and `agy.py:575` already do.

Reasoning effort needs a narrower table than Claude's. GLM exposes **High** and **Max** only, so
`_EFFORT_CLI_ARGS` for this provider should map SASE's canonical levels onto those two rather than forwarding all five
and hoping Z.ai ignores the rest.

### 5.2 Configuration once the provider exists

```yaml
llm_provider:
  model_aliases:
    builtin:
      # GLM joins the cheap pools first; @default and @smartest stay untouched.
      cheap: "claude/opus@medium | glm/glm-5.2-1m"
      cheaper: "glm/glm-5.2-1m | codex/gpt-5.3-codex-spark"
    custom:
      glm:
        model: glm/glm-5.2-1m
        description: "GLM 5.2 with the 1M context window, via the Z.ai coding plan."
```

That yields `%model @glm` for explicit use, `%model glm/glm-5.2-1m` for the raw form, an automatic `@glm_coder` role,
and automatic GLM participation in extra-small and small phase-worker launches.

### 5.3 Suggested rollout

1. **Spike (Option B, ~30 min).** Export the Z.ai env vars in one shell and launch a single low-stakes SASE agent with
   `%model claude/glm-5.2`. Confirm the things that actually matter: SASE hooks fire, `/sase_*` skills resolve, the
   stop hook and commit workflow behave, usage artifacts populate, and `/status` inside an interactive session reports
   GLM rather than a silent fallback. This de-risks the whole plan before any code is written.
2. **Build the provider (Option C).** File it as an epic: `glm.py`, entry point, unit tests mirroring the existing
   Claude provider tests, doctor coverage, Models-panel/color wiring, and `default_config.yml` documentation. The
   `.claude` skill-subpath override and the credential-scrubbing behavior each deserve an explicit test.
3. **Introduce via `@cheaper` only.** Run a week of extra-small phase workers on GLM. Compare completion quality and
   watch the 5-hour quota — this is the real unknown.
4. **Expand or retreat** based on that data. Promote into `@cheap`, or add the OpenRouter fallback target if the
   subscription window turns out to be the binding constraint.

---

## 6. Risks and open questions

- **Credential leakage — handle this deliberately.** SASE launches the `claude` binary with the ambient environment.
  If your shell or a settings file exports `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, a naive implementation
  would hand your Anthropic credentials to a third-party host on every request. The provider must scrub them.
- **Where your prompts go.** Routing agents through Z.ai sends your full repository context — source, plans, bead
  contents, commit messages — to a third-party, China-based provider under their terms rather than Anthropic's. That
  is a policy decision, not a technical one, and it is worth making consciously before the first non-toy agent runs.
- **Quota model versus SASE's fan-out.** SASE's whole shape is parallel agents; GLM's plan meters **prompts per
  5 hours** with a 2–3× multiplier on GLM-5.2. A single epic swarm can plausibly exhaust a Lite window. Start on a
  tier with headroom, or confine GLM to `@cheaper`.
- **Settings-file precedence is unverified.** Claude Code merges `~/.claude/settings.json` `env` values with the
  process environment; which wins was not confirmed. If the settings file loses, process env is sufficient; if it
  wins, the provider should additionally pass `--settings '<json>'` (the CLI accepts a JSON string, confirmed via
  `claude --help` on 2.1.220). **Verify during the spike.**
- **Effort forwarding.** Whether Z.ai's Anthropic-compatible endpoint accepts, ignores, or rejects Claude Code's
  effort parameter at each of the five SASE levels is untested. Assume it needs a restricted mapping.
- **Cache-token accounting.** SASE records `cache_creation_input_tokens` / `cache_read_input_tokens` in its usage
  artifacts. GLM supports context caching but may not populate those fields identically, so cost statistics for GLM
  agents may read differently from Claude agents. Cosmetic, but worth knowing before someone files it as a bug.
- **`claude.py` ignores `SASE_CLAUDE_PATH`.** Detection honors the override (`detect.py:53`), but the invoke path
  hardcodes `"claude"` at `claude.py:257`. A GLM provider built on the same harness should read the resolved
  executable rather than inherit that inconsistency — and the Claude provider itself deserves a task bead for it.
- **Directive truncation.** See §3. Independent of GLM, `%model:` silently dropping everything from `[` onward
  (including a trailing `@effort`) is a latent correctness bug worth its own bead.

---

## Sources

- [GLM-5.2: Zhipu AI's 1M-Token Open-Weight Coding Model — Eigent](https://www.eigent.ai/blog/glm-5-2)
- [Zhipu Deploys GLM 5.2 to All GLM Coding Plan Tiers — AI Weekly](https://aiweekly.co/node/2946)
- [Zhipu AI's stock rockets after Chinese firm launches open-source GLM-5.2 — SCMP](https://www.scmp.com/tech/tech-trends/article/3357115/zhipu-ais-stock-rockets-after-chinese-firm-makes-glm-52-open-source)
- [Claude Code — Z.AI Developer Document](https://docs.z.ai/devpack/tool/claude)
- [How to Switch Models — Z.AI Developer Document](https://docs.z.ai/devpack/latest-model)
- [FAQ — Z.AI Developer Document](https://docs.z.ai/devpack/faq)
- [GLM Coding Plan — z.ai/subscribe](https://z.ai/subscribe)
- [GLM-5.2: Features, Setup, Benchmarks, and Model Switching Guide — DataCamp](https://www.datacamp.com/blog/glm-5-2)
- [Run GLM-5.2 Inside Claude Code: The Full Setup Guide — Digital Applied](https://www.digitalapplied.com/blog/run-glm-5-2-inside-claude-code-setup-guide)
- [How to Run GLM 5.2 in Claude Code, Pi & OpenCode (2026) — ExplainX](https://www.explainx.ai/blog/how-to-run-glm-5-2-coding-plan-agent-harnesses-2026)
- [How to Use GLM 5.2 in Claude Code — MindStudio](https://www.mindstudio.ai/blog/how-to-use-glm-5-2-in-claude-code)
- [GLM Coding Plan Pricing: Lite $18, Pro $72, Max $160 — AI Pricing Guru](https://www.aipricing.guru/z-ai-subscription-pricing/)
- [GLM 5.2 Coding Plan: Limits, Pricing & 3-Week Test — TECHSY](https://techsy.io/en/blog/glm-5-2-coding-plan)
- [GLM Coding Plan: Z.AI Pricing & Tiers 2026 — Layer3Labs](https://www.layer3labs.io/guides/glm-coding-plan-explained)
