# A Generic ACP Provider for SASE: Should We Build It, and How?

- **Type:** researcher report (cld), one of a 2-researcher swarm
- **Date:** 2026-09-21
- **Question:** The consolidated report
  [multi_cli_orchestration_vs_sase](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
  ranked "Add a generic ACP provider plugin" as SASE's highest-leverage multi-CLI
  improvement. This report asks four things:
  - What is the best way to implement it?
  - Is it a good idea at all?
  - Would a different approach be better?
  - Which requirements should change?

  It ends with a recommended solution.
- **Method:**
  - **SASE code, read first-hand:**
    - `src/sase/llm_provider/` and the registry, skills and usage modules;
    - `docs/plugins.md`, `docs/agent_providers.md` and `docs/llms.md`;
    - the `sase-core` crate;
    - the decision records `single-turn-agents`, `host-owned-completion` and
      `rust-core-required`.
  - **ACP spec and SDKs:** read from local checkouts opened with `sase repo open` (repo
    HEAD 2026-09-21), especially `schema/v1/schema.json`, `schema.unstable.json` and
    `meta.json`.
  - **Two web and source research passes:** one on the protocol, one on how well each
    agent works over ACP. They covered agentclientprotocol.com, vendor docs, GitHub
    issue and PR threads, and the checkouts listed below.
  - **Spot checks** of peer implementations: Vibe Kanban, Multica, acpx and Goose.
- **Confidence labels:**
  - **(verified):** I read it myself in code or schema.
  - **(reported):** it comes from a research pass with a cited source that I did not
    re-read.
  - **(unverified):** it could not be confirmed.

---

## 1. Bottom line

1. **Yes, build it, but not as the recommendation phrased it.** "One generic ACP
   provider plugin" should become three things:
   - a **thin ACP transport** inside SASE's existing provider layer;
   - an **agent profile** per ACP agent;
   - a rule that **each profile becomes a first-class SASE provider** (`copilot`,
     `cursor`, `kimi`, …), not an agent name hidden inside one `acp` provider.

   Transport is a property of a provider, not its identity. That rule also lets
   existing providers (OpenCode, Grok) switch to ACP without renaming anything.
2. **ACP buys less than the source report implies.**
   - **What it delivers:**
     - reach to about 40 agents;
     - one parser for text, reasoning ("thinking") and tool calls, so observability
       works the same across agents by construction;
     - lossless mid-run interrupts (cancel, then prompt again in the same live session);
     - same-agent session resume where the agent supports it;
     - a real permission hook.
   - **What it does not deliver:**
     - **Per-run token usage.** The stable `usage_update` reports how full the context
       window is plus a cumulative cost. It does not report input or output tokens.
       Per-turn token counts are still `UNSTABLE` (verified in the schema).
     - **Cross-provider continuity.** ACP sessions are private to each agent. That is
       SASE's actual continuity weakness: drains and pools move work *between*
       providers.
     - **Replacing `agy`.** The `agy` CLI has no ACP mode. Google ships a separate
       ACP server with its own login, and there is terms-of-service risk.
3. **"Generic" still means per-agent work.**
   - Every agent differs on:
     - how to switch off approvals;
     - how to select a model and effort;
     - where usage comes from;
     - authentication quirks;
     - blocking vendor requests that stall a generic client;
     - where its skills live.
   - Multica is the most mature multi-agent ACP client I found. Its shared ACP layer is
     ~1.2k lines, yet each ACP agent backend is still 600–800 lines (verified). Its
     Kimi backend even reads Kimi's on-disk session logs to get token usage, because ACP
     does not provide it.
4. **The industry has settled on a hybrid:**
   - Native protocols for Claude and Codex.
   - ACP for agents that ship ACP natively.

   Vibe Kanban and Multica both work this way (verified in their source). Goose
   deprecated its CLI providers in favour of ACP six months ago. They are still in its
   code, and the switch caused regressions: zero usage, skills not loading, and
   startup timeouts (reported).
5. **Recommended implementation:**
   - **Transport:** a hand-rolled, synchronous ACP client in Python (~500 lines),
     built on the JSON-line transport SASE already uses for its Grok ACP billing probe.
     Not the official Python SDK, not `acpx` as a subprocess, and not a Rust client in
     `sase-core`.
   - **Profiles:** declarative YAML, one per agent.
   - **Conformance probe:** gates every profile. It must prove that SASE's own
     completion skill (`/sase_final`) is discoverable, that approvals are off, and what
     usage the agent reports.
   - **Pilot:** start with **OpenCode and Grok as A/B pilots**, because both have native
     SASE drivers to compare against.
   - **New agents:** add them only when you actually hold an account for them.
6. **Priority.** This is a *breadth* investment plus uniform interrupts. For the
   providers you use every day (Claude, Codex, Grok, Muse), the cheaper continuity win
   is native:
   - `claude --resume` on interrupt (already wired for the wait-continuation path);
   - Codex `exec resume`.

   I would do those first or in parallel, and scope the ACP epic as described in §8.

---

## 2. What is being evaluated

The recommendation (§7.4 item 1 of the source report) says:

> Add a generic ACP provider plugin. One client would cover Cursor, Copilot, Droid, Amp,
> Goose, Kimi, Junie, Cline, Pi and more. It would give SASE standard `session/resume`
> and `usage_update`. It could eventually replace the bespoke Qwen, OpenCode and agy
> plugins. Keep native plugins where the headless path is richer (Claude, Codex, Muse).
> `src/sase/llm_provider/usage/grok.py` already speaks ACP to Grok Build for its billing
> probe.

---

## 3. Facts that shape the design

### 3.1 SASE's provider contract (verified)

| Aspect | What the code does | Consequence for ACP |
|---|---|---|
| Plugin identity | `build_llm_plugin_manager()` registers **one instance per `sase_llm` entry point**, constructed with no arguments. `create_provider(name)` looks the class up by entry-point name (`_registry_plugins.py:11-58`) | A single "generic" plugin cannot become N providers without either a registry change or one entry point per agent (§6.2) |
| Dispatch | `LLMProvider.invoke(prompt, model_tier, model_override, options) -> InvokeResult(content, usage)`, a single synchronous call per run (`base.py`) | An ACP session must fit inside one blocking `invoke`. That is natural: one `session/prompt` per run, plus mechanical re-prompts |
| Model names | `model_to_provider[model] = name` is **last writer wins** (`_registry_catalog.py:39`) | Cursor or Copilot profiles listing `claude-opus-*` or `gpt-5.*` would silently take over implicit `%model:opus`-style resolution. ACP-backed providers must not register colliding model names implicitly |
| Interrupts | `start_interrupt_monitor` terminates the process when `interrupt_request.json` appears (`_subprocess_plain.py:40`). **Six of seven providers** then relaunch with a `--- Work So Far ---` text replay (`qwen.py:295`, `opencode.py:302`, `grok.py:378`, `codex.py:481`, `muse.py:471`, `agy.py:563`). Claude instead starts a fresh session (`claude.py:467`) | ACP's `session/cancel` followed by a new `session/prompt` in the same live session is strictly better, and it comes for free for every ACP-backed provider |
| Wait continuation | Claude re-prompts a "you ended your turn waiting" nudge with `--resume` (`claude.py:405-496`) | ACP gives every agent this: a second `session/prompt` on the same session |
| Turn teardown | The completion watchdog kills a provider that is still alive 120 s after `final_submission.json` appears (`_subprocess_plain.py:104`) | It can be reused as is, sending `session/close` before the kill |
| Artifacts | `live_reply.md`, `usage.json` (input, output, cache-creation and cache-read tokens), a runtime-neutral `tool_calls.jsonl` (schema v2: `runtime`, `source`, `event`, `status`, `tool_name`, `tool_use_id`, summaries, `duration_ms`), and a thinking file (`_tool_call_common.py`, `_subprocess_artifacts.py`) | ACP `tool_call` and `tool_call_update` map almost 1:1. **ACP has no stable counterpart for the usage.json token fields** |
| Skills | Rendered per provider from a Jinja context (`provider_tool_name`, `provider_native_ask_tool`) into `~/<subpath>/skills/<name>/SKILL.md` (`_init_skills_sources.py`). `muse.py:222` warns that without its own subpath Muse "picks up SASE's Claude-rendered copies from `~/.claude/skills`" | Every new agent needs its own skill directory and template context. Several ACP agents also read `~/.claude/skills` for compatibility and would pick up Claude-specific wording |
| Usage limits | Pattern matching on error text per provider (`usage_limit_config.py`) | ACP errors arrive as JSON-RPC error objects or stop reasons. They must be flattened into the text the matcher sees |
| Hard-coded tables | Provider names appear in `ace/tui/provider_styles.py`, `integrations/provider_badges.py`, `ace/query_profile/profiles/_agents_shared.py` and `doctor/checks_providers.py` | Dynamic or new providers need defaults in these tables (small work) |
| Existing ACP code | `usage/grok.py` runs `grok agent stdio` through `JsonLineSession`, which "never services unsolicited requests" (`usage/transport.py:19-44`). Its Rust half says "Probe transport stays in Python. This module owns … decisions" (`sase_core/src/provider_usage/grok.rs:3`) | This is the precedent for transport in Python and deterministic decisions in Rust. But a real ACP client **must** answer requests such as `session/request_permission`, so `JsonLineSession` has to be extended, not reused as is |
| Plugin policy | `docs/plugins.md:585`: "Additional providers belong in external plugin packages" | In tension with using the ACP transport for built-in OpenCode and Grok. See adjustment R9 |

**What a bespoke provider costs today** (verified, `git log` since 2026-06-21):

| Provider | Core files (provider + subprocess + tool-call), lines | Commits in 90 days |
|---|---:|---:|
| agy | 1,755 | 13 |
| muse | 1,303 | 14 |
| codex | 1,323 | 18 |
| claude | 1,259 | 21 |
| grok | 902 | 12 |
| qwen | 885 | 8 |
| opencode | 500 (no tool-call capture) | 10 |

- These counts exclude usage collectors and tests.
- Grok's first commit alone was 352 provider lines plus 523 test lines, followed by
  about 12 follow-up commits in its first week (epic `sase-l3`).

### 3.2 ACP as a headless client sees it (September 2026)

| Surface | Status | Notes for SASE |
|---|---|---|
| stdio NDJSON JSON-RPC, `initialize` with integer `protocolVersion` = 1 | Stable | Wire version has been `1` throughout. The schema package went 1.0.0 → 1.9.1 between 2026-06-24 and 2026-09-18, all additive (reported) |
| `session/new {cwd, mcpServers}`, `session/prompt`, `session/cancel` | Stable | The prompt response is **only `{stopReason}`** in the stable schema (verified) |
| `stopReason` | Stable | `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled` |
| `session/load` (replays history), `session/resume` (no replay), `session/list`, `session/close`, `session/delete` | Stable | Support varies widely (see below) |
| `session/fork` | Unstable | |
| `session/update` kinds | Stable | `agent_message_chunk`, `agent_thought_chunk`, `tool_call`, `tool_call_update` (`toolCallId`, `title`, `kind`, `status`, `content`, `locations`, `rawInput`, `rawOutput`, and `name`, stabilized 2026-09-17), `plan`, `config_option_update`, `session_info_update` |
| **`usage_update`** | Stable | `{used, size, cost?}`, where `used` = "Tokens currently in context", `size` = "Total context window size", `cost` = "Cumulative session cost" (verified). **Context occupancy, not per-turn tokens** |
| `PromptResponse.usage` (`inputTokens`, `outputTokens`, `thoughtTokens`, cached read/write) | **Unstable** | Its field docs contradict each other: the object is "Token usage for this turn", but its fields say "across all turns" (verified). codex-acp reports only the last request (reported, codex-acp#447) |
| `session/request_permission` with options of kind `allow_once`, `allow_always`, `reject_once`, `reject_always` | Stable | A headless client must always answer, choosing by **kind**, never by position |
| Session modes (`session/set_mode`) | Stable but superseded | Removed in the v2 draft |
| Session config options (`session/set_config_option`, categories `mode`, `model`, `thought_level`, `model_config`) | Stable | Standard handles for bypass, model and effort. `session/set_model` was **removed** on 2026-06-01, but some agents still use it (Kiro, Gemini's `unstable_setSessionModel`) |
| Client `fs/*` and `terminal/*` | Stable | If the client doesn't advertise them, agents use their own tools. v2 removes them. **Advertise neither** |
| `elicitation/*` | Stable since 2026-07-24 | Don't advertise it |
| Auth | `authMethods` of type `agent` or `terminal` | Most agents reuse the CLI's stored login. `-32000` means "auth required" |
| ACP v2 | Draft, 2026-07-20 | `session/prompt` returns immediately; completion is signalled by an idle `state_update`. Negotiate v1 only, and isolate "turn finished" detection behind one function (reported) |

**Registry reality** (verified from the registry's `.protocol-matrix/latest.md` for
2026-09-21, 35 agents probed):
- `loadSession` is advertised almost everywhere.
- `session/resume` actually worked for **11 of 35**; `session/fork` for 9.
- `session/new` returned `auth_required` for 22 in the registry's credential-less CI.

So cross-run continuation must go resume → load (suppressing the replayed updates) →
text replay.

### 3.3 Agent-by-agent fit

- All rows are (reported) from the research pass unless noted, with issue links in §11.
- "Native" means the vendor ships ACP itself.

| Agent | ACP path | Runs fully non-interactive? | Usage over ACP | Resume | Fit for a SASE profile |
|---|---|---|---|---|---|
| **Claude Code** | Adapter `@agentclientprotocol/claude-agent-acp` (Agent SDK plus a bundled `claude` binary) | `bypassPermissions` mode, hidden when running as root unless `IS_SANDBOX` is set | `usage_update` with USD cost, plus unstable `PromptResponse.usage` | Yes | **Keep native.** Adapter lags upstream (pinned SDK, #1148). Open headless bugs: MCP via `session/new` (#883), orphaned children (#1011), prompts swallowed after a usage limit (zed#55501). Billing and terms are the same as `claude -p` |
| **Codex** | Adapter `@agentclientprotocol/codex-acp` driving `codex app-server` | Env `INITIAL_AGENT_MODE=agent-full-access` | Context-only `usage_update`; last-request-only prompt usage | Yes | **Keep native.** 16–18 s startup; `authenticate` hangs without a browser; an extra model call for titles |
| **agy (Antigravity)** | **None in the `agy` CLI.** A separate `agy_acp_server.par` has its own login | Modes reported | **None** (#1045) | Yes | **Keep native.** Google's terms explicitly threaten suspension for third-party access to its backends |
| **Qwen Code** | Native `qwen --acp` | Mode `yolo` | `usage_update` plus `_meta.usage` | Yes (verified in matrix) | Plausible replacement **candidate**. Reports `end_turn` on truncated output (#12113). Reportedly exposes a `reasoning_effort` option that SASE's Qwen driver says doesn't exist (unverified) |
| **OpenCode** | Native `opencode acp` | Mostly; `doom_loop` and `external_directory` still ask (override with `OPENCODE_PERMISSION`) | `usage_update` with cost, plus prompt usage | Yes, including fork (verified in matrix) | **Best pilot.** ACP gives tool calls, which SASE's native OpenCode driver lacks (no `_tool_call_opencode.py`, verified) |
| **Grok Build** | Native `grok agent [--always-approve] stdio`. SASE already speaks it for billing (verified) | `--always-approve` or `_meta.yoloMode` | Only in `PromptResponse._meta` | Yes (verified in matrix) | **Second pilot.** Gains lossless interrupts. Pins an old ACP crate; `x.ai/ask_user_question` stalls generic clients |
| **Muse Code** | **None.** Uses its own protocol (MSP, via `muse serve`); community adapters only | n/a | n/a | n/a | **Keep native** |
| Copilot CLI | Native `copilot --acp` (public preview) | `--allow-all` or `--yolo` | `usage_update` plus prompt usage (≥1.0.78) | load and list only | **Best new-agent candidate**, if you have a Copilot plan. `--model` is silently ignored if invalid (#4880); each prompt aborts background subagents (#4555) |
| Cursor | Native, hidden `agent acp` | **No complete bypass**: web search and fetch still prompt | **None** | load and list | Weak fit. Blocking `cursor/ask_question` and `cursor/create_plan` requests stall turns |
| Goose | Native `goose acp` | `auto` mode is the default | `usage_update` with cost, plus prompt usage | load and list | Good protocol fit, but Goose is itself a multi-model harness, so its value to SASE is low |
| Kimi Code | Native `kimi acp` | Must `set_mode yolo`; starts in manual approval | Context only | Yes | OK. Empty-reply `end_turn` bug |
| Factory Droid | Native `droid exec --output-format acp`, undocumented | `--skip-permissions-unsafe` | (unverified) | Yes | Needs a spike |
| Junie | Native `junie --acp=true`, closed source | `brave_mode` config option, which reportedly persists globally | (unverified) | Yes | Needs a spike |
| Cline | Native `cline --acp` | `--auto-approve true` | **None** | load only | **Fails SASE's needs:** in ACP mode the rules and skills loader never starts |
| Pi | Third-party `pi-acp` 0.0.33 ("MVP") | Pi has no approval system at all | **None** | load and list | Provider errors arrive as an empty `end_turn` |
| Kiro | Native `kiro-cli acp`, not in the registry | `--trust-all-tools` | Vendor `_meta` credits (unverified) | load only | Uses the removed `set_model`; no concurrent sessions |

**Takeaways from the table:**
- Among SASE's current seven providers, **only Qwen, OpenCode and Grok have first-party
  ACP.** The source report's "six of seven" counts third-party adapters for Claude and
  Codex, and a separate server for Antigravity.
- Among the new agents, usage reporting ranges from full to none. The profile layer must
  treat usage as **reported / partial / unknown**, never as zero.

### 3.4 How peers actually built it

- **Vibe Kanban** (verified, `crates/executors/src/executors/`):
  - ACP only for `copilot`, `qwen` and `gemini`.
  - Native executors for `claude`, `codex`, `cursor`, `droid`, `opencode` and `amp`.
  - Reported:
    - its ACP path fakes resume by pasting stored history into a new prompt;
    - it records no token usage;
    - it auto-selects `allow_always`;
    - OpenCode moved to ACP and then back off it (PR #1823).
- **Multica** (verified, `server/pkg/agent/`):
  - A shared ACP layer (`acp_session.go`, `acp_usage.go`, `acp_effort.go`, … ~1.2k
    non-test lines) sits under per-agent backends of 598 (Grok), 646 (Kiro) and 792
    (Kimi) lines.
  - `acp_usage.go` tracks which usage fields were present, because "Prompt results are
    frequently partial, so a zero value alone cannot tell us whether a runtime
    explicitly reported zero or omitted the bucket entirely."
  - Its Grok backend runs `grok agent stdio` with a daemon-owned `--always-approve`, as
    recommended here.
- **Goose** (reported):
  - Added `claude-acp`/`codex-acp` providers (PR #6605, merged 2026-03-10). The PR
    author wrote "Provider -> ACP is really awkward."
  - Deprecated its CLI providers, but they are still in the code.
  - Regressions reported after the switch: all-zero usage (#8132), skills not loaded
    (#7853), codex-acp too slow for a 10 s startup timeout (#12239).
- **acpx** (OpenClaw, MIT, 0.18.0; verified):
  - The closest thing to "SASE's use case as a CLI".
  - `acpx --format json --json-strict --approve-all <agent> exec "<prompt>"` emits raw
    ACP NDJSON.
  - It has a permission-policy engine and recipes for 26 agents.
  - Caveat: its built-in Claude runs **exclude user settings by default**
    (`resolveClaudeCodeSettingSources()` omits `"user"` unless
    `ACPX_CLAUDE_INCLUDE_USER_SETTINGS=1`; verified). SASE deploys its skills at the
    *user* level (`~/.claude/skills`), so under acpx defaults `/sase_final` would likely
    be invisible. That this setting governs user-level skills is my reading of Agent SDK
    semantics (unverified). Either way, it shows how a middle layer's defaults can
    silently break SASE's completion protocol.

---

## 4. Critique of the recommendation

### 4.1 What holds up

- **The breadth argument is right.**
  - Adding one bespoke provider is an epic: 900–1,750 lines, then a steady stream of
    fixes.
  - An ACP profile is tens to low hundreds of lines plus fixtures.
  - Break-even is roughly the second agent.
- **"Keep native plugins where the headless path is richer (Claude, Codex, Muse)" is
  right,** and should be extended (see §4.2).
- **Pointing at `usage/grok.py` is apt.** SASE already has a working, bounded ACP
  handshake and a Rust-side normaliser for Grok's ACP payload. The pattern exists.

### 4.2 What is overstated or wrong

1. **"It would give SASE standard … `usage_update`."**
   - Stable `usage_update` measures how full the context is and the cumulative cost. It
     does not give the input, output and cache token counts that `usage.json` records.
   - Per-turn tokens are `UNSTABLE` and inconsistent across agents. Multica had to read
     Kimi's private logs to get them.
   - ACP will not close the usage-parity gap the source report itself flagged (§7.2.3).
     It adds another agent-specific usage source.
2. **"It would give SASE standard `session/resume`."**
   - The method is stable, but only 11 of 35 probed agents actually support it.
   - More importantly, ACP sessions belong to one agent. SASE's continuity pain is
     cross-provider: a pool rotates, or a drain reroutes to another provider
     (`docs/llms.md` §Draining). ACP does nothing for that; only a canonical transcript
     format (casr/txcript-style) would.
   - ACP helps *same-agent* continuation: interrupts, wait nudges, restarts after a
     crash. That is real, but narrower than the claim.
3. **"It could eventually replace the bespoke … agy plugin."**
   - Wrong. `agy` has no ACP mode (antigravity-cli#31 is open).
   - Google's `agy_acp_server.par` is a separate binary with a separate login, no usage
     reporting, and browser OAuth that hangs headless.
   - Google's terms for its CLI name third-party wrappers as grounds for suspension.
   - Qwen and OpenCode are plausible replacements, but only after a parity check (R3).
4. **"One client would cover Cursor, Copilot, Droid, Amp, Goose, Kimi, Junie, Cline, Pi."**
   - True of the *transport*. Of that list:
     - **Cline** loses rules and skills in ACP mode, so SASE agents couldn't find
       `/sase_final`.
     - **Cursor** has no full bypass and sends blocking vendor requests.
     - **Pi** and **Amp** are third-party adapters with no usage reporting.
   - Each needs a profile and a conformance run before it can carry SASE work.
5. **The count "six of SASE's seven providers" is misleading.**
   - It counts two third-party adapters (Claude, Codex) and a separate Google binary.
   - First-party ACP covers three (Qwen, OpenCode, Grok).

### 4.3 What the recommendation leaves out

- **Provider identity.** SASE's registry maps one entry point to one provider. The
  recommendation doesn't say whether Cursor and Copilot become their own providers,
  with their own pools, disables, usage limits, short names and colours, or are hidden
  behind one `acp` id. This is the most important design decision (§6.2).
- **The completion protocol depends on skills.** A SASE run is only successful if the
  agent can find and follow `/sase_final`. Skill loading varies by agent: directory,
  format, and whether it happens at all under ACP. It is the gating requirement for
  every profile, and the recommendation doesn't mention it.
- **Permission handling is an opportunity.**
  - Every headless ACP client needs a permission responder anyway.
  - Some agents still ask even in bypass mode: Cursor web search, Claude safety checks,
    OpenCode's doom-loop guard.
  - That responder is a cheap, uniform place to enforce the `host-owned-completion`
    decision ("an agent never creates commits, branches, or PRs") for agents that route
    shell commands through permission requests.
  - The source report criticised SASE's permissive, bypass-everywhere posture (§7.2.7)
    but didn't connect it to this.
- **Supply chain and latency.**
  - The registry distributes many agents as `npx <pkg>`.
  - Running `npx -y` of a floating version on every run is slow (codex-acp takes
    16–18 s to start) and bypasses SASE's install-review stance: `sase agent-cli`
    shows the install script's URL and SHA-256 first.
- **Spec churn.**
  - About ten additive schema releases in three months.
  - `set_model` removed, `set_mode` deprecated, and a v2 draft that changes turn
    completion.
  - The client must be small and tolerant.
- **Model-name collisions** in `model_to_provider` (§3.1).
- **A test strategy.** Every agent quirk found above (empty `end_turn`, blocking vendor
  requests, auth hangs) needs a scripted fake-agent test. SASE already has a precedent:
  `tests/llm_provider/fixtures/usage_probe/grok_acp_cli.py`.

### 4.4 Is it a good idea?

**Yes, as a scoped epic.** The reasons:

1. It is the only credible way to reach new agents at a marginal cost that doesn't grow
   with every new CLI. Every serious competitor either does this or pays the bespoke
   cost at 25–35 CLIs.
2. It improves SASE's existing weaker providers: OpenCode gains tool calls and
   reasoning text; OpenCode and Grok gain lossless interrupts.
3. It gives SASE a standard session model (`sessionId`, stop reasons, cancel) where
   today it infers turn state from process exit.

**It is not the top priority on its own terms.** It helps breadth (D1), observability
parity (D8, for ACP agents) and same-agent continuity. It doesn't help:
- **Cross-provider handoff (D6).** The report's weakest dimension.
- **Usage steering (D7).** Needs token data ACP doesn't standardise.

If you only use Claude, Codex, Grok and Muse, the new-agent half of the value is
theoretical until you actually hold, say, a Copilot plan. So:
- Build the transport and pilot it on OpenCode and Grok, which is valuable either way.
- Make new agents **demand-driven**.

---

## 5. Requirement adjustments (explicit)

| # | Original requirement | Adjusted requirement | Why |
|---|---|---|---|
| **R1** | "A generic ACP provider plugin" | **An ACP transport plus a profile catalog. Each profile materialises as a first-class SASE provider named after the agent** (`copilot`, not `acp`, nor `acp-copilot`) | Pools, disables, usage-limit windows, short names, colours and agent history are all keyed by provider id. If a native driver later replaces the ACP one, names and history stay stable |
| **R2** | ACP "gives" `usage_update` | **Usage is three-valued per run: reported, partial or unknown.** Context used/size and cost go in new optional `usage.json` fields. Token counts come from unstable `PromptResponse.usage` or profile-declared `_meta` extractors when present. **Missing never becomes 0** | The stable schema has no per-turn tokens; Multica's field-presence tracking shows the failure mode |
| **R3** | "Eventually replace Qwen, OpenCode and agy" | **Drop agy.** Replacing Qwen or OpenCode requires a parity matrix (text, tool calls, reasoning, usage, interrupt, resume, skills, instructions, usage-limit detection) and **per-provider `transport: native \| acp` config** during the A/B period | agy has no ACP and carries terms risk. Replacement must be earned, not assumed |
| **R4** | (absent) | **A profile is "supported" only after passing a conformance probe:** `AGENTS.md` is loaded, SASE skills are discoverable (`/sase_final` is found), a shell command runs with no permission stall, bypass is applied, the model and effort were applied, the stop reason is clean, and the usage shape is recorded | The completion protocol depends on it. Cline already fails it |
| **R5** | (absent) | **The permission responder is a policy engine from day one.** Default policy = approve (today's posture). A built-in rule denies `git commit` / `git push` / `gh pr create` when the request carries the command. Unknown vendor requests (`cursor/*`, `x.ai/*`) get a deterministic answer or error, never silence | Some agents ask even in bypass mode. Enforcing host-owned completion mechanically costs almost nothing here |
| **R6** | (absent) | **Continuation semantics:** interrupts and wait nudges use `session/cancel` plus a re-prompt in the live session. A restart of the same provider uses `session/resume` → `session/load` (replayed updates suppressed from live output) → text replay. `acp_session.json` persists `{provider, agent_version, sessionId, cwd, capabilities}`. **Cross-provider handoff is out of scope** | Delivers what ACP can actually give, and says plainly what it can't |
| **R7** | (absent) | **No floating `npx -y` at run time.** Adapters and agents are installed, pinned and updated through `sase agent-cli`, with registry `sha256` checks for binary distributions | Latency, reproducibility, and SASE's install-review stance |
| **R8** | Cover "Cursor, Copilot, Droid, Amp, Goose, Kimi, Junie, Cline, Pi" | **v1 covers OpenCode and Grok (A/B pilots) plus one new agent you actually use** (Copilot CLI is the best-fitting candidate on the evidence). Other profiles land on demand. Config-only custom agents come in a later phase | Each profile costs conformance and maintenance work. SASE's own `corpus-before-mechanism` instinct applies: build for demonstrated need |
| **R9** | "plugin" (docs say additional providers belong in external packages) | **Transport and base provider live in core** (`sase.llm_provider.acp`), because built-in OpenCode and Grok use them. Built-in profiles ship as core data. External packages or config can add profiles through the factory hook (§6.2) | Built-in providers can't depend on an external plugin; profiles are data, not code |

---

## 6. Implementation options

### 6.1 Where the ACP client lives (transport)

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Hand-rolled synchronous Python client** (extend `usage/transport.py`'s `JsonLineSession` with a reader thread, request servicing and id correlation) | Matches the other seven providers: threads, `subprocess`, SASE's process-tree reaping and completion watchdog. No new dependencies. Tolerant parsing with raw dicts (vendor drift is normal: Grok pins an ACP 0.10 crate). About 10 methods and 8 update kinds. SASE already has the Grok handshake | SASE owns schema drift, so it must track the CHANGELOG | **Recommended** |
| **B. Official Python SDK** (`agent-client-protocol`, 0.12.1 stable, 1.0.0rc2 released 2026-09-21, Apache-2.0) | Typed models; v2 support in `acp.experimental.v2`; maintained by the ACP org | Brings asyncio and pydantic into a synchronous, pydantic-free codebase (`pyproject.toml` has neither). Mid-1.0 churn. Strict validation can reject drifted agents | Use as a **reference and test oracle**, not a runtime dependency. Revisit once 1.x stabilises |
| **C. Shell out to `acpx --format json --json-strict`** | Least code; 26 agent recipes; policy engine; raw ACP NDJSON output is easy to parse | Adds a Node layer in the middle, pre-1.0, with its own session store and opinions (the Claude user-settings exclusion above). Less control over `_meta` knobs, cancel semantics and permission answers. One more process in the tree | Use as a **knowledge base** (its `agents/*.md` quirk notes) and a manual debugging tool, not a runtime dependency |
| **D. Rust client in `sase-core`** via the `agent-client-protocol` crate (2.2.0) | Honours the Rust-core rule literally; typed | `sase_core` is synchronous with no tokio (tokio exists only in `sase_gateway` and the LSP crate). The crate was redesigned at 1.0 in June 2026 and is already at 2.2. Streaming callbacks across PyO3 are complex. Provider transport is Python everywhere else, including the Grok ACP probe ("Probe transport stays in Python") | Not now. **Deterministic pieces** can move to `sase-core` later if another frontend needs them |

**Rust boundary rationale.**
- The litmus test is "would another frontend need this to match the TUI?"
- Frontends consume the *runtime-neutral* artifacts (`tool_calls.jsonl`, `usage.json`),
  not ACP events. Normalising ACP events happens inside the runner, like the other seven
  providers' Python normalisers.
- Keep the normaliser as **pure `dict → record` functions**, so it can move behind a
  `sase_core_rs` wire later without redesign.

### 6.2 How ACP agents become SASE providers (identity)

| Option | Description | Verdict |
|---|---|---|
| 1. A single `acp` provider | The agent is encoded in the model (`acp/copilot:gpt-5.5`) | **Reject.** One disable, one usage-limit window and one colour for N vendors; pools can't express "Copilot, else Claude"; model-name collisions |
| 2. One entry point per built-in profile | `copilot = "sase.llm_provider.acp.builtin:CopilotProvider"`; each class is a tiny `AcpProvider` subclass bound to a profile id | **v1.** Zero registry changes; every metadata hook comes from the profile |
| 3. A factory hook | A new `sase_llm_factory` entry-point group (or a hook) yields `(name, instance)` pairs from `llm_provider.acp.agents` config plus external packages. `build_llm_plugin_manager` and `create_provider` consult it. The metadata cache already keys on a config fingerprint (`_registry_metadata.py:_config_fingerprint`) | **Phase 4.** Config-only custom agents (a config field, not a feature flag) |
| 4. Transport as a property of existing providers | `llm_provider.providers.opencode.transport: acp` makes `OpenCodeProvider` delegate `invoke` to the ACP engine with an OpenCode profile | **v1, for the A/B pilots.** Gated by a `beta` flag as epic scaffolding |

**Model-name rule:**
- ACP-backed providers register model names for **explicit `provider/model` addressing
  only**.
- The catalog builder should refuse (with a doctor warning) any implicit name that
  collides with a model another provider already owns.

### 6.3 Alternatives to ACP itself

- **Keep writing bespoke providers.** Highest fidelity, but it costs about one epic per
  CLI and caps SASE's breadth at whatever you can afford to maintain. Still correct for
  Claude, Codex, Muse, agy and (for now) Grok.
- **A "headless CLI template" provider** (argv plus a known stream dialect, e.g. the
  Claude-style `stream-json` that Qwen, Cursor and others imitate).
  - Cheaper than ACP and keeps the one-shot model.
  - But it has no standard for sessions, cancel, permissions or tool-call schemas, and
    each imitation drifts silently.
  - Not recommended as the primary path. It could be a stopgap for a CLI with no ACP.
- **SASE as an ACP *agent* (server).** This is the reverse direction: Zed, JetBrains
  Air, Toad and the 100+ ACP clients could drive SASE agents with routing, memory and
  host-owned landing from an editor.
  - It addresses a different weakness: reach and interactive use (D10, §7.2.6 of the
    source report).
  - It doesn't compete with the provider plugin. **Worth a separate research item** once
    the client exists, because both would share the same schema knowledge.
- **Per-session MCP injection.** ACP requires agents to accept stdio MCP servers in
  `session/new`. That gives SASE a uniform channel to inject a SASE tools server:
  - This could become the fallback for agents whose skill loading is weak.
  - It is speculative: claude-agent-acp#883 shows MCP servers passed in `session/new`
    not reaching the model, and Cline ignores them.
  - Treat it as an experiment, not a dependency.

---

## 7. Recommended design

### 7.1 Shape

```text
src/sase/llm_provider/acp/
  transport.py    # AcpConnection: spawn (own process group), NDJSON framing, reader thread,
                  #   id correlation, request servicing, bounded buffers, deadlines, stderr ring
  session.py      # AcpRun: initialize → auth check → new/resume/load → apply config →
                  #   prompt → (cancel/re-prompt)* → close; stop-reason classification
  normalize.py    # pure functions: session/update → live text, thinking, tool-call records,
                  #   plan, usage snapshot; JSON-RPC error → diagnostic text
  permissions.py  # policy engine: choose by option kind; deny rules; vendor-request table
  profiles.py     # AcpProfile schema + loader (built-in YAML + config + factory, later)
  profiles.yml    # built-in profiles (opencode, grok, copilot, … as they pass conformance)
  provider.py     # AcpProvider(LLMProvider): every hookimpl derived from the profile;
                  #   interrupt monitor + completion watchdog wiring; usage-limit mapping
_tool_call_acp.py # ACP tool_call → runtime-neutral record (schema v2), reusing _tool_call_common
```

### 7.2 Profile schema (illustrative)

The values below come from the research pass and must be confirmed in the spike.

```yaml
copilot:
  display_name: GitHub Copilot CLI
  vendor: GitHub
  short_name: cop
  command: ["copilot", "--acp"]
  install: {manager: npm, package: "@github/copilot", pin: "1.0.86"}
  auth:
    authenticate: never            # rely on the CLI's stored login; -32000 → doctor hint
    evidence: {credential_paths: ["~/.copilot"], api_key_env_vars: ["GH_TOKEN"]}
  non_interactive:                 # exactly one mechanism per profile
    argv: ["--allow-all"]          # alternatives: mode: {category: mode, value: ...},
                                   #   env: {...}, meta: {...} (e.g. Grok _meta.yoloMode)
  model:
    via: argv                      # Copilot: no model config option at session/new
    argv: ["--model", "{model}"]
    known: ["..."]                 # explicit provider/model addressing only
  effort:
    via: config_option             # category thought_level; values validated at runtime
    map: {low: low, medium: medium, high: high, xhigh: high}
  usage:
    sources: [prompt_response_usage, usage_update]   # or meta paths, e.g. grok: _meta.usage
  skills: {deploy_subpath: ".copilot", template_context: {provider_tool_name: "Copilot CLI"}}
  instructions: ["AGENTS.md"]
  vendor_requests: {}              # e.g. cursor/ask_question: error, x.ai/ask_user_question: error
  startup_timeout_s: 60
  usage_limit_patterns: ["..."]
  capabilities_expected: {resume: false, load: true}
```

### 7.3 Run lifecycle (one `invoke`)

1. **Spawn** the profile's argv in its own process group, with stdin and stdout pipes
   and stderr kept in a ring buffer. Start the interrupt monitor and completion watchdog
   against the *connection*, not a bare `Popen`.
2. **`initialize`**:
   - `protocolVersion: 1`;
   - `clientCapabilities: {fs: {readTextFile: false, writeTextFile: false}, terminal: false}`,
     with no elicitation and no `auth.terminal`;
   - `clientInfo: {name: "sase", version}`.

   Record `agentInfo`, capabilities and `authMethods` in the run metadata.
3. **Auth.** Don't call `authenticate` unless the profile says so (Grok uses
   `cached_token`; Codex hangs if you call it). Map `-32000` to an actionable
   "run `<cli> login`" failure.
4. **Session.** Use `session/new {cwd: workspace, mcpServers: []}`. For a continuation
   of the same provider, use `session/resume` when advertised, else `session/load`
   (flagging replayed updates so they are *not* appended to `live_reply.md`), else a new
   session with text replay.
5. **Configure.** Apply bypass, model and effort through the profile mechanism.
   - Validate against the returned `configOptions`.
   - Keep SASE's explicit-vs-default effort contract: an explicit unsupported effort
     raises; a default is logged and skipped (`_effort_args.effort_cli_args`).
   - Map through the Rust-backed effort resolution already in use.
6. **`session/prompt`** with one text block (the preprocessed SASE prompt).
7. **Stream updates** through `normalize.py` (§7.4). Service every inbound request:
   - permission → policy;
   - `fs/*`, `terminal/*` → `-32601`;
   - elicitation → decline;
   - `_vendor` requests → profile table, else `-32601`.
8. **Stop reason:**
   - `end_turn` → success, **unless** the reply is empty and stderr or JSON-RPC errors
     show a provider failure (a quirk seen in Pi, Kimi and Qwen);
   - `max_tokens` / `max_turn_requests` → a "truncated" failure class;
   - `refusal` → failure;
   - `cancelled` → the interrupt path.
9. **Interrupt.** Send `session/cancel`, answer any pending permission with
   `cancelled`, wait up to N seconds for `stopReason: cancelled`, then send a new
   `session/prompt` with the user's message **in the same session**. If the agent
   doesn't settle, kill it and fall back to step 4's resume chain.
10. **Wait nudge.** Reuse the Claude wait-state classifier idea: if the reply ends by
    waiting on something that can't happen, re-prompt in the same session (bounded).
11. **Teardown.** After `final_submission.json` plus the grace period: `session/close`,
    close stdin, then SIGTERM the process group. Write `acp_session.json`.

**Fit with the single-turn decision.** All re-prompts in steps 9–10 are host-mechanical
and happen inside one runner turn. That is exactly how today's interrupt relaunches and
the Claude wait continuation work, so the `single-turn-agents` decision is respected.

### 7.4 Normalisation map

| ACP | SASE artifact |
|---|---|
| `agent_message_chunk` (text) | `live_reply.md` plus timestamps; `InvokeResult.content` |
| `agent_thought_chunk` | Thinking artifact. **Closes the reasoning-capture gap for ACP agents** |
| `tool_call` / `tool_call_update` | `tool_calls.jsonl` v2: `runtime=<provider>`, `source="acp"`, `tool_use_id=toolCallId`. `tool_name` = `name` if present, else a normalised `kind`/`title`. `pending`/`in_progress` → started; `completed`/`failed` → finished with status. Summaries come from `rawInput`/`rawOutput` (falling back to `content` text or diffs), using `_tool_call_common`'s redaction. Duration comes from observed timestamps |
| `plan` | Optional plan artifact; otherwise ignored |
| `usage_update` | `context_used`, `context_size`, cumulative `cost` (per-prompt delta computed for re-prompts) |
| `PromptResponse.usage` (unstable) / profile `_meta` paths | Input, output and cache token fields, **with a presence mask**; `usage_completeness: reported \| partial \| unknown` |
| JSON-RPC errors, stderr tail, `refusal` | Error text fed to `detect_usage_limit()` and to the diagnostics shown to the user |
| `session_info_update`, `available_commands_update`, `config_option_update`, `current_mode_update` | Run metadata; not user-visible |

### 7.5 Skills and instructions

- **Each profile declares a skill deploy subpath and template context.**
  - The skills generator already iterates registered providers, so ACP providers get
    rendered skills automatically once they're registered (§3.1).
  - Prefer each agent's own skill directory over `~/.claude/skills`, to avoid
    Claude-specific wording (the Muse lesson).
- **Instructions:** `AGENTS.md` covers nearly every ACP agent. Add a shim file only where
  an agent demonstrably doesn't read `AGENTS.md`.
- **The conformance probe (R4) checks all of this** by asking the agent to name the
  description of `sase_final`, and by checking an `AGENTS.md` marker.

### 7.6 Install, doctor and probe

- **Install metadata.** Derive `llm_install_metadata` from the profile: `npm` for
  npx-distributed agents, pinned; registry binary archives with `sha256`, which may need
  a small new `manager` kind.
- **`sase doctor -C llm.auth`** uses profile auth evidence.
- **Conformance probe.** Add a bounded check under `sase doctor` (or a
  `sase agent-cli probe <provider>` subcommand; see the `cli_rules` memory before adding
  it). It:
  - runs initialize and `session/new` in a temporary directory;
  - caches the agent's `configOptions` (model and effort catalogs), so
    `llm_known_model_names` stays I/O-free;
  - runs the canned conformance prompt;
  - writes a capability row: resume, load, usage shape, reasoning, `rawInput`, skills
    and bypass.

  That capability row doubles as the **provider parity matrix** the source report asked
  for (§7.4 item 3).

### 7.7 Testing

- **A scripted fake ACP agent** (Python, stdlib only), extending the
  `grok_acp_cli.py` fixture precedent, with scenarios for:
  - streaming text, reasoning and tool calls;
  - permission requests with shuffled option ids;
  - blocking vendor requests;
  - `auth_required`;
  - slow start;
  - cancel mid-tool;
  - crash after `end_turn`;
  - empty `end_turn` with an error on stderr;
  - oversized lines;
  - `session/load` replay;
  - cumulative cost across re-prompts.
- **Recorded real transcripts** per profile and version, as fixtures, like the
  `grok_stream/*.jsonl` fixtures.
- **Both states of the `beta` scaffolding flag** during the epic, per the flag
  conventions.

---

## 8. Rollout plan

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Spike** (1–2 days, throwaway) | A minimal client drives `opencode acp` and `grok agent stdio` on athena; capture transcripts; measure startup; check skills and `AGENTS.md` loading | Go/no-go: both run a real SASE task to a successful `/sase_final` over ACP |
| **1. Transport + OpenCode A/B** | `acp/` package, fake agent, normaliser, permissions, `AcpProvider`, `transport: acp` for `opencode` behind a `beta` flag (created with `sase flag new`) | Parity matrix: OpenCode-over-ACP ≥ native on every column (it should win on tool calls and reasoning) |
| **2. Grok over ACP + continuation** | Grok profile (`--always-approve`, `_meta` usage); lossless interrupt; wait nudge; `acp_session.json`; resume chain on restart | Interrupt keeps full context; Grok usage and billing are no worse than native; the drain/usage-limit path is unchanged |
| **3. First new agent** | One agent you actually hold a plan for (Copilot CLI recommended); install metadata, doctor, conformance probe, defaults in the hard-coded tables | Passes conformance; appears correctly in pickers, pools, the Agents tab and `sase agent-cli` |
| **4. Factory + config-defined agents** | The factory hook (§6.2 option 3); `llm_provider.acp.agents` config field; docs; remove the `beta` flag | A custom agent defined only in config passes the probe |
| **Later** | Decide whether to retire native OpenCode or Qwen from the parity data; consider an opt-in stricter permission policy, MCP injection, and SASE-as-ACP-agent research; re-evaluate v2 when it stabilises | |

**Effort estimate:**
- Phases 1–2: ~2,000–2,500 lines including tests.
- Each further profile:
  - ~50–200 lines plus fixtures and a probe run to "work";
  - more to reach full usage parity. Multica's 600–800-line backends are the upper
    bound.

---

## 9. Risks and open questions

**Risks:**
- **Spec churn.** Mitigations:
  - negotiate v1 only;
  - keep turn completion behind one function;
  - use tolerant parsing;
  - watch the schema CHANGELOG (about one release every 9 days).
- **Adapter lag and agent bugs.** Mitigations:
  - conformance-gated profiles;
  - pinned versions;
  - diagnostics that name the profile and version.
- **Terms of service.**
  - Google is the dangerous vendor; this is another reason to keep agy native.
  - Anthropic's position is unchanged from `claude -p`, and Claude stays native anyway.
  - OpenAI appears permissive (reported).
- **Process leaks.** Adapters spawn grandchildren (claude-agent-acp#1011). Use process
  groups plus SASE's existing descendant sweep.
- **Opportunity cost.** Native Claude and Codex resume-on-interrupt are cheaper wins for
  daily use.

**Open questions for you:**
1. Which additional agents do you actually have plans or accounts for (Copilot, Cursor,
   Kimi, Droid, Junie)? That decides whether Phase 3 happens now.
2. Should ACP-backed providers default to profile bypass (parity with today) or to the
   approve-by-default policy responder with the commit/push deny rule (R5)? I recommend
   the responder, with the rule enabled.
3. Should OpenCode and Grok join any size-alias pools after the pilot, or stay
   explicit-only?

---

## 10. Recommended solution

1. **Build an ACP transport, not "an ACP provider."**
   - A small, synchronous, hand-rolled Python client in `sase.llm_provider.acp`,
     extending the JSON-line transport SASE already uses for Grok's ACP billing probe.
   - It advertises no fs, terminal or elicitation capabilities.
   - It always answers permission and vendor requests through a policy engine that
     approves by default and denies commit/push when it can see the command.
   - Keep normalisation as pure functions so it can move to `sase-core` if another
     frontend ever needs it.
2. **Describe agents with declarative profiles**, each covering:
   - launch;
   - bypass mechanism;
   - model and effort mapping;
   - usage sources;
   - auth policy;
   - skill subpath;
   - vendor-request table;
   - timeouts;
   - usage-limit patterns.
3. **Materialise every profile as a first-class SASE provider named for the agent.**
   - v1: one entry point per built-in profile, plus a `transport: native | acp` switch
     on existing providers.
   - Later: a factory hook for config-defined agents.
   - ACP providers never claim implicit model names that collide with other providers.
4. **Deliver what ACP really offers:**
   - lossless in-session interrupts and wait nudges;
   - a same-agent resume → load → replay chain;
   - uniform text, reasoning and tool-call capture;
   - three-valued usage with a presence mask.

   Leave cross-provider handoff and token-usage parity to separate work.
5. **Gate every profile with a conformance probe** that proves `/sase_final` is
   discoverable, bypass is applied and the usage shape is known. Its output is the
   provider parity matrix.
6. **Roll out:**
   1. a 1–2-day spike;
   2. an OpenCode A/B pilot;
   3. Grok over ACP (lossless interrupts);
   4. one new agent you actually use (Copilot CLI is the best fit);
   5. config-defined agents.

   Keep Claude, Codex, Muse and agy native. Decide Qwen and OpenCode retirement only
   from parity data.
7. **In parallel, do the cheap native continuity fixes:** Claude `--resume` on
   interrupt and Codex `exec resume`. They serve your daily providers more directly than
   the ACP epic does.

---

## 11. Sources

**SASE (repo-relative):**
- Provider layer:
  - `src/sase/llm_provider/base.py` · `_hookspec.py` · `_registry_plugins.py` ·
    `_registry_catalog.py` · `_registry_metadata.py` · `registry.py`
  - `qwen.py` · `grok.py` · `claude.py` · `codex.py` · `opencode.py` · `muse.py` ·
    `agy.py`
  - `_subprocess_plain.py` · `_subprocess_qwen.py` · `_tool_call_common.py`
  - `usage/grok.py` · `usage/transport.py` · `model_alias_defaults.yml`
- Other code: `src/sase/main/_init_skills_sources.py` · `pyproject.toml`
- Docs: `docs/plugins.md` §LLM Plugins · `docs/agent_providers.md` · `docs/llms.md`
  §Draining
- `sase-core`: `crates/sase_core/src/provider_usage/grok.rs` · `Cargo.toml`
- Decision records: `single-turn-agents`, `host-owned-completion`, `rust-core-required`.
  Memory: `sase_flags`.

**ACP spec and SDKs** (local checkouts via `sase repo open`):
- `gh:agentclientprotocol/agent-client-protocol`: `schema/v1/schema.json`,
  `schema.unstable.json`, `meta.json`, CHANGELOG, RFDs
- `gh:agentclientprotocol/python-sdk` (0.12.1 on main; 1.0.0rc2 on PyPI) ·
  `gh:agentclientprotocol/rust-sdk` (2.2.0, `yopo`)
- `gh:agentclientprotocol/registry` (`.protocol-matrix/latest.md`, 2026-09-21)

**Protocol pages:**
- https://agentclientprotocol.com/protocol/v1/prompt-turn
- https://agentclientprotocol.com/protocol/v1/session-config-options
- https://agentclientprotocol.com/protocol/v1/tool-calls
- https://agentclientprotocol.com/rfds/session-usage
- https://agentclientprotocol.com/rfds/end-turn-token-usage
- https://agentclientprotocol.com/rfds/v2/client-filesystem-terminal-capabilities
- https://agentclientprotocol.com/announcements/acp-v2-draft
- https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json

**Adapters and agents:**
- `gh:agentclientprotocol/claude-agent-acp` (issues #883, #896, #1011, #1019, #1148)
- `gh:agentclientprotocol/codex-acp` (#447, #215, PR #485)
- Other trackers:
  - Antigravity: `google-antigravity/antigravity-cli#31`, `#1045`
  - Qwen: `QwenLM/qwen-code#12113`
  - Copilot: `github/copilot-cli#4555`, `#4880`
  - Cline: `cline/cline` (`apps/cli/src/main.ts`)
  - Pi: `svkozak/pi-acp#98`
  - Kimi: `MoonshotAI/kimi-code#1485`
  - Kiro: `kirodotdev/Kiro#6640`
  - Grok: `getpaseo/paseo#3490`
- Vendor docs:
  - Cursor ACP: https://cursor.com/docs/cli/acp
  - Copilot ACP: https://github.blog/changelog/2026-01-28-acp-support-in-copilot-cli-is-now-in-public-preview/
  - Kiro ACP: https://kiro.dev/docs/cli/acp/
  - Junie ACP: https://junie.jetbrains.com/docs/junie-cli-acp.html

**Peer implementations:**
- `gh:BloopAI/vibe-kanban` (`crates/executors/src/executors/`)
- `gh:multica-ai/multica` (`server/pkg/agent/acp_*.go`, `grok.go`, `kimi.go`, `kiro.go`)
- `gh:openclaw/acpx` (`agents/*.md`, `docs/output-formats.md`, `docs/permissions.md`,
  `src/acp/agent-command.ts`)
- `gh:aaif-goose/goose` (PR #6605; issues #5593, #8132, #7853, #12239, #9113)

**Terms and policy:**
- https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- https://code.claude.com/docs/en/legal-and-compliance
- https://zed.dev/blog/anthropic-subscription-changes
- https://geminicli.com/docs/resources/tos-privacy/
- https://developers.openai.com/community/codex-for-oss

**Source report:**
[multi_cli_orchestration_vs_sase.md](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
§4.2, §7.2, §7.4
