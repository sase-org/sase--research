# A Generic ACP Provider for SASE: Consolidated Research

- **Type:** consolidated research report (lead), merging two independent reports and the
  lead's own research
- **Date:** 2026-09-21
- **Question:** The
  [multi_cli_orchestration_vs_sase](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
  report (§7.4, item 1) recommended "Add a generic ACP provider plugin". This report
  answers five questions:
  - What is the best way to implement it?
  - Is it a good idea?
  - Would a different approach be better?
  - Which requirements should change?
  - What do we recommend?
- **Inputs:**
  - [acp_provider_design__cld.md](acp_provider_design__cld.md) (**cld**): the broadest
    report. It covers the protocol, fit for 16 agents, peer implementations (Vibe Kanban,
    Multica, acpx, Goose), a profile schema and a rollout plan.
  - [acp_provider_design__mus.md](acp_provider_design__mus.md) (**mus**): SASE-side
    facts verified in code, launch commands from the registry, and a "spike before you
    commit" discipline.
- **Lead's own research** targeted the reports' gaps and disagreements:
  - **A live ACP spike on athena.** A throwaway stdlib client drove the three installed
    ACP-native CLIs: OpenCode 1.18.31, Grok 1.0.40 and Qwen Code 0.24.3. It ran
    `initialize`, `session/new` and a prompt, killed the process, started a fresh one,
    called `session/resume` and prompted again.
  - **SASE code and history:** `git log` over the provider interrupt path, a search of
    every linked repo, and the continuation design research.
  - **ACP checkouts:** the spec, the registry `.protocol-matrix/latest.md` and the Python
    SDK, all at HEAD on 2026-09-21.
- **Confidence labels:**
  - **(verified):** read first-hand in code or schema, or observed in the spike.
  - **(reported):** cited by a researcher; not re-checked by the lead.
  - **(unverified):** open.

---

## 1. Bottom line

1. **Yes, build ACP support, but as a transport, not "a generic ACP provider".** It has
   three parts:
   - a small, synchronous Python ACP client in core;
   - a typed profile per agent;
   - a rule that each profile becomes a first-class provider **named after the agent**
     (`opencode`, `copilot`), never an `acp` or `acp-<agent>` id.

   Both researchers reached this shape independently. They differed only on naming, and
   the naming question has a clear answer (§5).
2. **The source report overstated what ACP delivers.** Four of its five claims needed
   correcting:
   - **Usage.** Stable `usage_update` reports how full the context window is, not token
     counts.
   - **agy.** It has no ACP mode.
   - **Resume.** It works only for some agents.
   - **Grok.** Its probe calls a vendor extension, which is not standard ACP.
3. **New finding: the "lossless interrupt" benefit is moot today.** Both reports sold it
   as a headline win. SASE has had **no producer of mid-run interrupts since 2026-03-28**
   (verified; §3.1). The interrupt monitor and the "Work So Far" replay in every provider
   are dead code.
4. **New finding: ACP's real continuity value is in successor agents.** Monitor
   continuations, gate and question follow-ups, and pipes all start a **fresh provider
   process** today and re-render history as text.
   - ACP `session/resume` can reuse the prior session instead.
   - **The lead verified this for OpenCode.** After the process was killed, a new process
     resumed the session and still recalled a codeword from the first prompt. 13,824 of
     14,084 tokens were prompt-cache reads (§3.2).
   - This is the same "provider reuse" optimisation that
     [monitor_continuation_design](../monitor_continuation_design/monitor_continuation_design.md)
     found for Claude (`--resume --fork-session`) and Codex (`exec resume`). **Design one
     session-reuse contract for all three, not an ACP-only mechanism.**
5. **Priority: worth doing, but not urgent.**
   - ACP's immediate beneficiaries are OpenCode and Qwen, which are in no size-alias
     pool, and Grok, whose native driver already works.
   - Of the ACP-only agents, none is installed on athena (Copilot, Cursor, Goose, Kimi,
     Droid).
   - What the investment buys is (a) a much better OpenCode and (b) a cheap way to add
     any future agent.
6. **Recommended path** (§8):
   1. an ACP transport epic that **replaces** the native OpenCode driver (the spike shows
      it wins on every column);
   2. a provider session-reuse contract, with Claude, Codex and ACP backends;
   3. Grok over ACP only if it reaches parity;
   4. new agents strictly on demand.

---

## 2. The recommendation, claim by claim

| Source claim | Verdict | Evidence |
|---|---|---|
| "One client would cover Cursor, Copilot, Droid, Amp, Goose, Kimi, Junie, Cline, Pi" | **True only of the transport.** Each agent still needs a profile and a conformance run | Launch commands differ per agent (§4.2). Cline loses its rules and skills loader in ACP mode, Cursor sends blocking vendor requests, Pi and Amp report no usage (reported, cld) |
| "Gives SASE standard `session/resume`" | **Partly true.** The method is stable, but support is per agent and the benefit is same-agent only | Registry probe: `session/resume` works for 11 of 35 agents (verified, `.protocol-matrix/latest.md`). Nothing crosses providers, while SASE's drain and pool rotation move work *between* providers |
| "…and `usage_update`" | **Misleading** | `UsageUpdate` = `{used, size, cost?}`: tokens currently in context, window size, cumulative cost (verified, `schema/v1/schema.json`). Per-turn tokens exist only in the **unstable** `PromptResponse.usage`. OpenCode does send it (verified, spike) |
| "Could eventually replace Qwen, OpenCode and agy" | **OpenCode: yes, plan for it. Qwen: after parity. agy: no** | `agy` has no ACP mode. The registry's `antigravity-acp` is a separate binary with its own login, and Google's terms threaten suspension for third-party access (reported, cld) |
| "Keep native Claude, Codex, Muse" | **Correct, and add agy** | The Claude and Codex ACP paths are third-party adapters (startup lag, open headless bugs); Muse has no ACP (reported, cld) |
| "`usage/grok.py` already speaks ACP" | **True, but it doesn't transfer** | It is a probe using the vendor extension `_x.ai/billing`. Its `JsonLineSession` "never services unsolicited requests" (verified, `usage/transport.py:40-46`), so it cannot drive a turn |
| "Six of seven providers" are in the registry | **Only three are first-party** (Qwen, OpenCode, Grok) | Claude and Codex come through adapters, Antigravity through a separate server (verified, registry `agent.json`) |

---

## 3. New evidence from the lead

### 3.1 Mid-run interrupts have had no producer since March (verified)

- **The only writer is gone.** The Agents-tab `m` keymap wrote `interrupt_request.json`.
  Commit `1a46198f1` ("Remove `m` (message) keymap from Agents tab", 2026-03-28) deleted
  it, along with `AgentInterruptMixin` and `AgentInterruptModal`.
- **Nothing else writes the file.** Searches of `sase`, `sase-core`, `sase-telegram`,
  `sase-nvim` and `sase-github` find only the reader in `_subprocess_plain.py:40-70`.
- **So every provider's interrupt branch is unreachable.** That is the "Work So Far"
  relaunch in seven providers.
- **Claude's dead branch is also buggy.** It restarts with a fresh session whose prompt is
  *only* the interrupt message, dropping the original task (`claude.py:460-468`).
- **Consequences:**
  - cld's "lossless mid-run interrupts … for free" and mus's REQ-6 deliver nothing until
    SASE brings back mid-run messaging.
  - The source report's "interrupts rebuild context from text" criticism is also about
    dead code.
  - **Decision for you:** either bring mid-run messaging back as its own feature (ACP
    then makes it cheap: `session/cancel` plus a re-prompt in the live session), or
    delete the dead monitor. Don't build ACP cancel wiring for a feature that doesn't
    exist.

### 3.2 Live ACP spike on athena (verified, 2026-09-21)

**Client posture:**
- `protocolVersion: 1`;
- `clientCapabilities: {fs: {readTextFile: false, writeTextFile: false}, terminal: false}`;
- permission requests auto-answered by option kind;
- scratch directory `/tmp/acp_spike/ws`.

| | OpenCode 1.18.31 (`opencode acp`) | Grok 1.0.40 (`grok --no-auto-update agent --always-approve stdio`) | Qwen 0.24.3 (`qwen --acp --experimental-skills`) |
|---|---|---|---|
| Advertised capabilities | `loadSession`; sessions: `close`, `fork`, `list`, `resume` | `loadSession`; sessions: `list`, `resume`, `close`; many `x.ai/*` `_meta` extensions | `loadSession`; sessions: `list`, `resume` |
| Auth | Stored login; no `authenticate` call needed | `authenticate {methodId: cached_token}` succeeds | Only `openai` advertised |
| Config options at `session/new` | `model`, `mode`. **No effort knob** | `model` plus `reasoning_effort` (category `thought_level`) | `mode` (plan, default, auto-edit, auto, yolo), `model` plus `reasoning_effort` (`thought_level`). This confirms cld's unverified note that Qwen exposes an effort option SASE's native driver says doesn't exist |
| Prompt result | `end_turn`, with `usage {inputTokens, outputTokens, totalTokens, cachedReadTokens}`; `usage_update` gave `used` 13,875 / `size` 200,000 / `cost` $0 | `-32603 "Internal error"`. The real cause, **402 "Grok Build usage balance exhausted"**, appears **only on stderr** | `-32603 "Internal error"`. The real cause, **403 "Access to model denied"**, is in `error.data.details`. Native `qwen -p` fails the same way, so it's the account, not ACP |
| Cross-process resume | **Works.** A fresh process resumed the session and answered the codeword from the first prompt; 13,824 of 14,084 tokens were cache reads | `session/resume` succeeded; recall untested (quota) | `session/resume` succeeded; recall untested (account) |
| Mini conformance (one prompt) | **Passed:** `AGENTS.md` marker loaded into instructions; every `sase_*` skill listed, including `sase_final`; `echo` ran through the shell tool with **0 permission requests**; streamed 3 `tool_call`, 10 `tool_call_update`, 65 `agent_thought_chunk` and 1 `usage_update` | not run | not run |
| Startup to first prompt | ~2.5 s warm, ~12 s cold | ~1–2 s | ~5 s |

**Design consequences:**
1. **Usage-limit detection must read JSON-RPC `error.data` and a stderr ring buffer.**
   Both quota failures surfaced as a generic `-32603`. This confirms cld's point that
   ACP errors must be flattened into the text `detect_usage_limit()` matches.
2. **Effort is a standard config option where it exists** (`thought_level`), and absent
   for OpenCode. The profile must say which, and SASE's contract applies: an explicit
   unsupported effort raises, a default is skipped.
3. **The conformance probe is cheap** (~20 s), so gating every profile on it is
   practical.

### 3.3 Where continuity actually hurts: successors, not interrupts

- **Every SASE continuation is a new provider process with text-rendered history.** That
  covers monitor continuations, plan, question and gate follow-ups, forks and pipes
  (verified: `history/chat_fork/`, `continuation_baseline.py`, `continuation_budget*`).
- **Earlier research reached the conclusion this design needs.**
  [monitor_continuation_design](../monitor_continuation_design/monitor_continuation_design.md)
  concluded that "provider reuse is an optimization, not the durable source of truth",
  and that native reuse exists but SASE doesn't use it:
  - Claude: `--resume` plus `--fork-session`;
  - Codex: `exec resume`.
- **This is the continuity ACP can generalise**, but only across processes, so mus's
  concern was the right one. OpenCode passes (§3.2).
- **Linear vs branching successors need different methods:**
  - `session/resume` *continues* the parent session. It fits linear successors (monitor
    continuation, pipe).
  - It is wrong for branches. Two children resuming one parent would interleave, so
    branching successors (forks, fan-out) need `session/fork`.
  - `session/fork` is **unstable** and 9 of 35 agents support it; OpenCode advertises it.
    Otherwise fall back to text replay.
- **No beads exist yet** for native session reuse or ACP (verified, `sase bead search`).

### 3.4 What is installed on athena (verified)

| Installed | Not installed |
|---|---|
| `claude` 2.1.278, `codex` 0.155.1, `agy` 1.2.7, `muse` 1.3.0, `grok` 1.0.40, `opencode` 1.18.31, `qwen` 0.24.3 | `copilot`, `cursor-agent`, `goose`, `kimi`, `droid` |

- Only three installed CLIs are first-party ACP (OpenCode, Grok, Qwen).
- Of those, only OpenCode works end to end today.
- Any "new agent" phase means adopting a new vendor account, which is a product decision,
  not an engineering one.

---

## 4. Facts that shape the design (merged)

### 4.1 SASE's provider contract (verified by both reports and the lead)

- **Providers are already plugins.**
  - There is one `sase_llm` entry point per provider (`pyproject.toml`): `agy`,
    `claude`, `codex`, `fakey`, `grok`, `muse`, `opencode`, `qwen`.
  - The hooks are defined in `_hookspec.py`.
  - A new provider reuses `invoke_agent()`, routing, disable state, retry and usage-limit
    config, skill deployment (`llm_skill_deploy_subpath`) and the TUI.
- **Identity is the entry-point name everywhere.** Disable windows, priorities, pools,
  usage-limit windows, colours (`provider_styles.py`), badges (`provider_badges.py`),
  query profiles (`_agents_shared.py`) and doctor checks (`checks_providers.py`) all key
  on it.
- **Model-name resolution is last-writer-wins.** `_registry_catalog.py:39` does
  `model_to_provider[model] = name`. If a Copilot profile lists `claude-opus-*`, it
  silently takes over implicit `%model:opus` resolution.
- **Providers run synchronously on threads**, with `start_interrupt_monitor` and
  `start_completion_watchdog`. There is no asyncio in the runtime and no pydantic
  dependency.
- **Bespoke providers are expensive.** They cost 500–1,755 core lines each, plus 8–21
  commits in their first 90 days (cld's table). OpenCode has no tool-call capture: there
  is no `_tool_call_opencode.py`.
- **Transport lives in Python; deterministic decisions live in Rust.** The Grok billing
  normaliser says so: "Probe transport stays in Python. This module owns … decisions"
  (`sase_core/src/provider_usage/grok.rs:3`).
- **Plugin policy:** `docs/plugins.md:631` says "Additional providers belong in external
  plugin packages".

### 4.2 ACP as a headless client sees it (verified unless noted)

- **Versions.**
  - The wire `protocolVersion` is `1`.
  - There are two tag series. The Rust crate is `v1.9.1`; the schema is
    `schema-v1.23.0`. Both were released 2026-09-18, so cld and mus were each quoting
    one of them.
  - Twelve schema releases shipped between 2026-06-16 and 2026-09-18, all additive.
  - A v2 draft changes how turn completion is signalled (reported, cld).
- **Methods.**
  - Stable: `initialize`, `session/new|prompt|cancel|load|resume|list|close|delete`,
    `session/set_config_option` (categories `mode`, `model`, `thought_level`).
  - Unstable: `session/fork`.
  - `session/set_model` was removed from the spec, but 17 agents still answer it.
- **Client capabilities.** If a client leaves `fs` or `terminal` un-advertised, agents
  **MUST NOT** call those methods (`file-system.mdx:29`, `terminals.mdx:26`). Advertise
  neither. mus's "decline-or-service `fs/*`" is unnecessary.
- **Permissions.** Clients "MAY automatically allow" (`tool-calls.mdx:191`). Choose by
  option `kind`, never by position.
- **Cancellation.**
  - After `session/cancel`, the client **MUST** answer pending permission requests with
    `cancelled` (`prompt-turn.mdx:328`).
  - `$/cancel_request` is a stable but **optional** notification. When the agent sends it
    for a request still pending on the client, the client must still answer that request
    (`cancellation.mdx`).
- **Registry reality** (35 agents probed on 2026-09-21):
  - `initialize` succeeded for 34;
  - `session/new` returned `auth_required` for 22 in credential-less CI;
  - `session/resume` was supported by 11, `session/fork` by 9, `session/list` by 22.
- **Launch commands differ per agent** (registry `agent.json`):
  - subcommand: `opencode acp`, `goose acp`, `kimi acp`, `cursor-agent acp`;
  - flag: `copilot --acp`, `cline --acp`, `junie --acp=true`,
    `qwen --acp --experimental-skills` (**skills are experimental in Qwen's ACP mode**);
  - bespoke: `grok agent stdio`, and
    `droid exec --output-format acp-daemon` plus two auto-update env vars (mus's version
    is correct);
  - adapters: `claude-agent-acp`, `codex-acp`, `pi-acp`.

  So "generic" still means a per-agent profile.

### 4.3 Agent fit (condensed)

The Resume column is the registry probe. The lead's spike adds the verified notes.

| Agent | Resume (registry) | Usage over ACP | Verdict |
|---|---|---|---|
| OpenCode | load, list, fork, resume | Tokens in `PromptResponse.usage` plus `usage_update` (verified) | **Pilot, then replace the native driver** |
| Grok | load, list, resume | `_meta` only (reported) | **Second candidate.** Parity spike blocked today by quota |
| Qwen | load, list, resume | `usage_update` plus `_meta.usage` (reported) | Candidate. Account currently gets 403 |
| Claude, Codex | load, list, fork, resume (adapters) | Partial | **Keep native** |
| agy, Muse | agy: separate server; Muse: none | none | **Keep native** |
| Copilot CLI | load, list | Yes, ≥1.0.78 (reported) | Best new agent **if you get a plan** |
| Kimi, Droid, Junie | resume advertised | context-only or unverified | Needs a spike on demand |
| Cursor, Cline, Pi, Goose | load (and list) only | none, or low value | Weak fit. Cline fails skills; Cursor sends blocking requests; Goose is itself a multi-model harness |

### 4.4 How peers built it (reported, cld; spot-verified in source by cld)

- **The field has settled on a hybrid.** Vibe Kanban and Multica use native protocols for
  Claude and Codex and ACP for agents that ship it natively.
- **"Generic" still costs code per agent.** Multica's shared ACP layer is about 1.2k
  lines, but each agent backend is still 598–792 lines. It tracks *which* usage fields
  were present, because "a zero value alone cannot tell us whether a runtime explicitly
  reported zero or omitted the bucket".
- **Goose shows the switchover risk.** After moving to `claude-acp`/`codex-acp` it saw
  regressions: all-zero usage, skills not loading, and startup timeouts.
- **acpx is a useful knowledge base, not a runtime dependency.** Its default Claude runs
  exclude user settings, which would probably hide SASE's user-level skills.

---

## 5. Where the reports disagreed, resolved

| Topic | cld | mus | Resolution |
|---|---|---|---|
| **Provider identity** | Agent-named providers (`copilot`); a transport switch on existing providers | Additive `acp-<agent>` entry points alongside the natives | **cld.** Disable and usage-limit state is keyed by provider name, but the quota belongs to the *account*. With both `opencode` and `acp-opencode`, a usage limit on one leaves the other routable into the same exhausted account. Names would also churn when a native driver is retired |
| **Pilots** | OpenCode + Grok (A/B against the native drivers) | OpenCode + Goose | **OpenCode** (spike-verified). Grok is second once its quota resets. Goose is not installed and adds little |
| **fs and terminal** | Advertise neither | Decline or service them | **cld**, per spec MUSTs. The spike received 0 fs or terminal requests |
| **Cancellation** | Answer pending permissions with `cancelled` | "Answer `$/cancel_request`" | cld's wording is the spec MUST; `$/cancel_request` is optional. **Low priority either way** (§3.1) |
| **Where resume helps** | In-process interrupts and wait nudges; resume → load → replay on restart | Cross-process persistence per agent, spike first | **mus's framing matters**, because successors are new processes. cld's fallback chain is the right mechanism. OpenCode passes |
| **Profile format** | Declarative YAML plus a factory hook | Python descriptor table plus thin subclasses | **Typed Python profiles first.** A config-defined agent is a real feature, but defer it until a third profile exists (`corpus-before-mechanism`) |
| **Usage** | Three-valued (reported, partial, unknown) with a presence mask | Only vendor extensions give usage; `usage_update` → continuation budget | **Both.** Presence-masked tokens from `PromptResponse.usage` or `_meta`; context occupancy feeds `continuation_budget*`. Missing is never 0 |
| **Permission responder** | Policy engine; deny `git commit`/`push`/`gh pr create` by default | Auto-allow, and keep the posture visible | **Always answer deterministically by kind** (required). The deny rule is cheap but rarely fires: OpenCode made **0** permission requests even for a shell command. Don't present it as enforcing `host-owned-completion` |
| **Client size** | ~500 lines; phases 1–2 ~2,000–2,500 lines with tests | 300–500 lines on `JsonLineSession` | Consistent. Budget ~1,000–1,500 lines of runtime (connection, run, normaliser, responder, provider) plus a similar amount of tests |

**Where both agreed, and the lead concurs:**
- Hand-roll a sync client; don't take the asyncio/pydantic SDK as a runtime dependency.
  Use the SDK as a test oracle.
- No Rust ACP client.
- No floating `npx -y` at run time.
- Don't build on `session/fork` while it is unstable, beyond an opportunistic
  capability-gated use.
- MCP injection and live TUI streaming stay out of scope.
- A fake ACP agent test harness, extending the `grok_acp_cli.py` fixture.
- `sase agent-cli` install metadata and doctor auth evidence for every profile.

---

## 6. Critique: is this a good idea?

**Yes, but it is worth less than the source report implied, and it isn't the most
valuable continuity work.**

### What ACP genuinely buys SASE

1. **A far better OpenCode, now.** It gains:
   - tool-call capture, which the native driver lacks;
   - reasoning text;
   - per-turn tokens;
   - cross-process resume.

   All four were observed in one 20 s spike.
2. **A per-agent cost that no longer grows with every CLI.** A profile is tens to low
   hundreds of lines plus a conformance run. A bespoke driver is 900–1,750 lines plus a
   tail of fixes. Break-even is the second agent.
3. **A standard session model.** SASE gets `sessionId`, stop reasons and cancel,
   instead of inferring turn state from process exit.

### What it doesn't buy

- **Cross-provider handoff (D6):** ACP sessions are private to one agent.
- **Usage steering (D7):** no standard per-turn tokens.
- **Interrupts:** no producer (§3.1).
- **Breadth you'll use:** none of the ACP-only agents is installed, and adding one means
  adopting a new vendor account.

### Would I take a different approach? Three changes, not a different technology

1. **Make continuity a provider-neutral contract, with ACP as one backend.**
   - The largest continuity win is session reuse for *successor* agents. The daily
     providers (Claude, Codex) can already do it natively and SASE doesn't use it.
   - Building ACP-specific resume plumbing first would create a second mechanism to
     reconcile later.
   - Put the "may this successor reuse the parent's provider session?" decision into the
     continuation records that `monitor_continuation_design` already places in Rust (the
     Rust-core boundary rule applies: every frontend must agree on it).
   - Each provider then implements "try resume or fork, else fall back to replay":
     - Claude: `--resume --fork-session`;
     - Codex: `exec resume`;
     - ACP: `session/resume` for linear successors, `session/fork` when advertised.
2. **Treat the OpenCode pilot as a replacement, not an open-ended A/B.** The spike
   already shows ACP beating the native driver on every observable column.
   - Per the flag conventions, a temporary switch that ends in replacement is `beta`
     scaffolding that the epic removes when it lands.
   - A permanent `transport: native | acp` config field would make the choice something
     users pick forever. That is the wrong default and doubles the maintenance.
3. **Keep new agents strictly demand-driven,** and build config-defined agents only when
   a third profile exists.

### Alternatives considered and rejected

- **One `acp` provider:** it collapses disable windows, quota, pools and colours for N
  vendors into one.
- **Official SDK or acpx as a runtime dependency:** asyncio, pydantic, a Node middle
  layer, and middle-layer defaults that can hide SASE skills.
- **A Rust client in `sase-core`:** `sase_core` has no tokio; the crate went through
  1.0 → 2.2 in three months; and every other provider transport is Python.
- **A "headless CLI template" provider:** no standard for sessions, cancel or tool calls.
  Keep it only as a stopgap for a CLI without ACP.
- **SASE as an ACP agent (server)** is worth its own research item, not a competitor to
  this work. It would let Zed, JetBrains Air and other ACP clients drive SASE agents,
  addressing reach (D10) rather than breadth.

---

## 7. Requirement adjustments (explicit)

| # | Original | Adjusted | Status | Why |
|---|---|---|---|---|
| R1 | "A generic ACP provider plugin" | **An ACP transport in core** (`sase.llm_provider.acp`) plus typed per-agent profiles. **Each profile is a first-class provider named after the agent** | CHANGED | Identity, quota and history are keyed by provider name (§5). Built-in OpenCode can't depend on an external package, so this is a documented exception to `docs/plugins.md:631` |
| R2 | ACP gives "standard `usage_update`" | **Usage is presence-masked and three-valued** (reported, partial, unknown), taken from `PromptResponse.usage` or profile `_meta` paths. `usage_update` occupancy feeds the continuation budget. **Missing never becomes 0** | CHANGED | Stable `usage_update` is context occupancy (§2) |
| R3 | "Eventually replace Qwen, OpenCode, agy" | **Replace OpenCode within the epic. Qwen and Grok only on a green parity row. Never agy** | CHANGED | Spike evidence for OpenCode; agy has no ACP and carries terms-of-service risk |
| R4 | "Standard `session/resume`" | **Resume serves successor agents through a provider-neutral session-reuse contract** (linear → resume, branch → fork when advertised, else text replay), shared with native Claude and Codex reuse. Text replay stays the durable source of truth | CHANGED (lead) | Continuations are new processes (§3.3). Avoids a second, ACP-only mechanism |
| R5 | (implied) lossless interrupts | **Dropped from scope.** Decide separately whether to bring back mid-run messaging or delete the dead interrupt monitor | DROPPED (lead) | No producer since 2026-03-28 (§3.1) |
| R6 | (absent) | **Conformance probe gates every profile:** `AGENTS.md` loaded; `sase_final` discoverable; a shell command runs with no permission stall; model and effort applied; clean stop reason; usage shape recorded; cross-process resume tested. Its output is the parity matrix | ADDED (both) | The completion protocol depends on skills (Cline fails). The probe takes ~20 s |
| R7 | (absent) | **Full-duplex client.** Always answer permission requests by option kind; vendor requests by profile table or `-32601`; decline elicitation; advertise no `fs`, `terminal` or elicitation | ADDED (both) | Unanswered requests hang the turn |
| R8 | (absent) | **Error mapping.** JSON-RPC `error.message`, `error.data` and a stderr tail are flattened into the usage-limit matcher and diagnostics. An empty `end_turn` with errors counts as a failure | ADDED (lead) | Quota failures arrived as a generic `-32603` (§3.2) |
| R9 | (absent) | **ACP-backed providers register model names for explicit `provider/model` use only.** Implicit collisions are refused with a doctor warning | ADDED (cld) | `model_to_provider` is last-writer-wins |
| R10 | (absent) | **No floating `npx -y` at run time.** Pinned installs go through `sase agent-cli`, with `sha256` for binaries | ADDED (cld) | Latency, reproducibility and the install-review stance |
| R11 | Cover Cursor, Copilot, Droid, Amp, Goose, Kimi, Junie, Cline, Pi | **v1 covers OpenCode only; Grok is next.** Other agents only when you hold an account. Config-defined agents after a third profile | CHANGED | None of those agents is installed (§3.4) |
| R12 | (absent) | **Negotiate v1 only, and keep "turn finished" detection behind one function** | ADDED (cld) | The v2 draft changes completion signalling |

---

## 8. Recommended solution

### 8.1 Shape

```text
src/sase/llm_provider/acp/
  connection.py  # AcpConnection: spawn in its own process group; NDJSON framing; reader
                 #   thread; id correlation; services inbound requests; byte bounds reused
                 #   from usage/transport.py; stderr ring buffer; deadlines
  run.py         # AcpRun: initialize(v1) → authenticate only if the profile says →
                 #   new | resume | fork | load → set_config_option (mode/model/effort) →
                 #   prompt → close; stop-reason and error classification; turn-end in one place
  normalize.py   # pure dict→record functions: text, thought, tool_call(_update) →
                 #   tool_calls.jsonl v2 (source="acp"), presence-masked usage,
                 #   error+stderr → usage-limit text
  responder.py   # permission (by option kind), vendor-request table, elicitation decline
  profiles.py    # AcpProfile dataclass + built-in profiles (opencode first)
  provider.py    # AcpProvider(LLMProvider): hookimpls derived from the profile;
                 #   completion-watchdog wiring; session-reuse hook
```

**How the pieces fit:**
- **Existing providers switch in place.** `OpenCodeProvider` delegates to `AcpProvider`
  under the epic's `beta` flag, and the native path is deleted when the epic lands.
- **Profiles carry only the per-agent facts** the spike showed actually vary:
  - argv and env, with a `SASE_<AGENT>_PATH` override;
  - auth policy;
  - the non-interactive mechanism: argv flag, mode value or `_meta`;
  - model and effort via config-option category or argv;
  - usage sources;
  - skill deploy subpath;
  - vendor-request table;
  - usage-limit patterns;
  - startup timeout.
- **Normalisation stays as pure functions** so it can move behind `sase_core_rs` if
  another frontend ever needs raw ACP events.

### 8.2 Phases

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Finish the spike** (hours) | Re-run the lead's spike on Grok after its quota resets: resume recall, `--always-approve`, the `_meta` usage shape, `reasoning_effort`. Record OpenCode and Grok transcripts as fixtures | Go/no-go on Grok. OpenCode is already a go |
| **1. ACP transport + OpenCode** (epic, `beta` flag created with `sase flag new`) | The `acp/` package; a stdlib fake ACP agent (streaming, permissions with shuffled option ids, blocking vendor request, `auth_required`, slow start, `-32603` plus stderr quota, empty `end_turn`, oversized line, cumulative cost); the conformance probe as a test and doctor check; install and auth metadata | The OpenCode parity row is ≥ native on every column (text, tool calls, reasoning, usage, usage-limit detection, skills, instructions) |
| **2. Land by replacing native OpenCode** | Delete the native OpenCode subprocess path and the flag's Off branch; close the flag bead | One `opencode` provider; no flag |
| **3. Provider session reuse** (separate epic; can run before or alongside 1–2) | Parent session record (provider, model, session id, cwd, capabilities, agent version) in the Rust continuation records; the successor prompt builder renders both a **delta** prompt and the full **replay** prompt; providers try resume (linear) or fork (branch), else replay. Backends: Claude `--resume --fork-session`, Codex `exec resume`, ACP `session/resume`/`session/fork` | A monitor continuation on Claude, Codex and OpenCode reuses the session when possible, falls back cleanly when the session is missing or moved, and measurably cuts input tokens |
| **4. Grok over ACP** (only if phase 0 is a go) | Grok profile (`cached_token` auth, `--always-approve`, `_meta` usage); A/B against native under a `beta` flag | Usage, billing probe and drain behaviour no worse than native. Otherwise keep native Grok and close the flag |
| **Later, on demand** | New agents (Copilot CLI first, if you get a plan); config-defined profiles once three profiles exist; bring back mid-run messaging (if wanted); SASE-as-ACP-agent research | Each new profile passes conformance and appears correctly in pickers, pools, the Agents tab and `sase agent-cli` |

**Pool membership:** keep ACP-backed providers explicit-only, or in `@xsmall`/`@small`,
until their parity row has been green for a while. This mirrors `agy` today.

**If you only do one thing this quarter,** do phase 3's Claude and Codex backends. They
serve the providers you run every day. **If you want breadth next,** phases 1–2 are a
self-contained, well-evidenced epic that also gives phase 3 its third backend.

---

## 9. Risks and open questions

**Risks:**
- **Spec churn** (about one schema release a week, and a v2 draft). Mitigations:
  negotiate v1 only, parse tolerantly, keep turn-end detection behind one function, pin
  agent versions, and re-run conformance on upgrades.
- **Process leaks from adapters** (reported for `claude-agent-acp`). Mitigation: process
  groups plus SASE's existing descendant sweep.
- **Terms of service.** Google is the risky vendor (keep agy native). Per-agent
  subscription-vs-API billing must be confirmed before any new profile ships.
- **Stale reuse.** A reused session carries old workspace context and more history
  tokens. Keep text replay authoritative, and never pick a session by "last" in
  concurrent workspaces.

**Open questions for you:**
1. Mid-run messaging: bring it back (ACP and native resume make it cheap) or delete the
   dead interrupt monitor (§3.1)?
2. Do you plan to hold a Copilot, Cursor, Kimi or Droid plan? If not, the ACP value is
   OpenCode, possibly Grok, and future-proofing.
3. Order of work: session reuse (phase 3) before ACP (phases 1–2), or ACP first? The
   lead recommends session reuse first for daily-provider value. ACP first is fine if
   breadth matters more.
4. Should Qwen stay a provider at all, while the account is denied model access?

---

## 10. Sources

**SASE (repo-relative):**
- Provider layer:
  - `src/sase/llm_provider/`: `base.py`, `_hookspec.py`, `_registry_plugins.py`,
    `_registry_catalog.py:39`, `claude.py:395-500`, `qwen.py:285-299`,
    `_subprocess_plain.py:40-70`, `usage/transport.py`, `usage/grok.py`,
    `model_alias_defaults.yml`
- Other code:
  - `src/sase/main/_init_skills_sources.py`
  - `src/sase/history/chat_fork/`
  - `src/sase/continuation_baseline.py`
  - `pyproject.toml` (`sase_llm` entry points)
  - `docs/plugins.md:631`
- History: commit `1a46198f1` (2026-03-28)
- `sase-core`: `crates/sase_core/src/provider_usage/grok.rs`
- Memory: `sase_flags`; decisions `single-turn-agents`, `host-owned-completion`,
  `rust-core-required`, `corpus-before-mechanism`

**ACP (local checkouts via `sase repo open`, HEAD 2026-09-21):**
- `agentclientprotocol/agent-client-protocol`:
  - `schema/v1/schema.json`, `schema.unstable.json`, `CHANGELOG.md` and tags;
  - `docs/protocol/v1/cancellation.mdx`, `prompt-turn.mdx`, `tool-calls.mdx`,
    `file-system.mdx`, `terminals.mdx`
- `agentclientprotocol/registry`: `.protocol-matrix/latest.md` and per-agent
  `agent.json`
- `agentclientprotocol/python-sdk`: 0.12.1, `schema/VERSION` = `schema-v1.23.0`

**Lead's live spike:**
- A throwaway stdlib client at `/tmp/acp_spike/spike.py` and `spike2.py`, run on athena
  on 2026-09-21 against `opencode acp`, `grok agent stdio` and `qwen --acp`.
- Not committed.

**Prior research:**
- [multi_cli_orchestration_vs_sase](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
  §4.2, §7.2, §7.4
- [monitor_continuation_design](../monitor_continuation_design/monitor_continuation_design.md)
  (provider-reuse table)

**Researcher reports:**
- [acp_provider_design__cld.md](acp_provider_design__cld.md): peer implementations,
  vendor issue links and terms-of-service sources in its §11.
- [acp_provider_design__mus.md](acp_provider_design__mus.md): its §8.
