# Hermes Agent as a Fully Supported SASE Provider

> **Research query:** What is the best way to add Hermes
> ([`NousResearch/hermes-agent`](https://github.com/nousresearch/hermes-agent)) to SASE as a new, fully supported LLM
> provider? Review the earlier Hermes research file in the research sidecar repo, and end with a recommended solution.

![Infographic: Hermes in SASE. Bundle hermes (hrm) as an explicit opt-in provider using the public stream-json CLI and a SASE-owned profile per workspace; stable v0.22.2 runs the agent loop inside the CLI process while main/canary routes it through a gateway daemon; SASE owns the runtime boundary; Hermes adds value through Nous Portal, OpenRouter and local models; a Phase 0 trial decides between the public CLI and a foreground companion worker](hermes_agent_sase_provider_infographic.png)

## Bottom line

1. **Build it, as an eighth bundled provider: `hermes`, short name `hrm`, explicit-only.** All five reports agree that
   Hermes is worth wrapping. That fulfils the earlier "complement, not rival" verdict
   ([prior research](#prior-research)). Hermes contributes an agent loop over about 40 inference backends, including
   Nous Portal, OpenRouter and local models. SASE keeps workspaces, gates, handoffs and host-owned completion.
2. **The transport is the public CLI:**
   `hermes chat --oneshot --query-file - --format stream-json`. It is Hermes's documented orchestrator protocol, and
   its flags are identical on stable and `main` (see [command construction](#command-construction)).
3. **The CLI does not tell you how the turn executes, and that is the design's crux.** The lead verified this
   [timeline](#the-verified-timeline):
   - **Stable `v0.22.2`** runs the agent *in the CLI process*.
   - **`main`/canary** sends every `hermes chat` turn to a **background gateway daemon**. One daemon serves each
     `HERMES_HOME`. On that path, Ctrl-C detaches and leaves the turn running. The daemon also inherits the
     environment of whichever client happened to start it.
   - **`v0.22.1`** was accidentally released from `main`. `v0.22.2` was re-cut from the release branch to undo that.
   - **The next stable release will almost certainly carry the gateway.**

   Three reports (grk, mus, gem) missed this and assume a hermetic subprocess. That holds today and breaks on the next
   upgrade.
4. **Run every SASE invocation inside a SASE-owned, per-workspace Hermes profile home** (cld's key insight; see
   [the SASE-owned Hermes home](#the-sase-owned-hermes-home)). That one step makes the same adapter correct under both
   execution models:
   - **On stable,** it gives isolation from the user's personal Hermes: no SOUL, memory, cron, Kanban or session
     history.
   - **On `main`,** it turns the shared daemon into a **per-agent daemon**. That daemon inherits the agent's
     environment and cgroup, and SASE stops it when the turn ends.
5. **Normalize the harness mechanically,** as the Adapters Normalize Harnesses decision
   (`decisions:adapters-normalize-harnesses`) requires:
   - deliver the instruction bundle explicitly through Hermes's ephemeral *system* prompt
     ([instruction delivery](#instruction-delivery))
   - pass an explicit toolset allowlist
   - raise the foreground ceiling so Hermes never auto-backgrounds a command
   - add a Hermes single-turn directive and a wait guard ([single-turn conformance](#single-turn-conformance))
   - capture a tested-version window that is checked before any model call
6. **Gate the build on a short [Phase 0 spike](#phase-0-go-or-no-go-spike) of the gateway lifecycle.** If SASE cannot
   reliably own a per-agent daemon, swap only the *transport* for cdx's foreground companion worker (`AIAgent` run
   inside Hermes's own runtime). Keep the rest of the provider as designed. Ask [upstream](#upstream-asks) for a
   supervised-execution mode in parallel.

The full recommendation is [at the end](#recommended-solution).

## Evidence and limits

- **Question:** Add Hermes ([`NousResearch/hermes-agent`](https://github.com/nousresearch/hermes-agent)) as a new,
  fully supported SASE LLM provider. Research the best way to implement it, review the earlier Hermes research in the
  research sidecar, and end with a recommended solution.
- **Date:** 2026-10-19
- **Inputs:** five independent reports ([cdx](hermes_agent_sase_provider__cdx.md), [cld](hermes_agent_sase_provider__cld.md),
  [grk](hermes_agent_sase_provider__grk.md), [mus](hermes_agent_sase_provider__mus.md),
  [gem](hermes_agent_sase_provider__gem.md)), plus the lead's own verification against both source trees.
- **Pins:**
  - **Hermes `main`/canary:** `8f5693af41` (2026-10-19). `git describe` gives `v0.22.2+canary.20261019T071120Z-144`.
  - **Hermes stable:** `v0.22.2` = `d923a5eb48` (2026-10-15).
  - **SASE:** `e5f2d768ea`. The researchers used `4b7b981532` (release 0.18.0); the one later commit is a test fix.
- **Limits:** nobody ran an authenticated Hermes conversation, started a gateway, or drove a SASE finalizer through
  Hermes. cdx ran the unmodified stable stream-json emitter against synthetic callbacks. Every lifecycle claim is from
  the source code and is marked for the Phase 0 spike where it matters.

## Prior research

The Hermes research the user remembered is most likely
**[`202610/can_hermes_replace_sase`](../can_hermes_replace_sase/can_hermes_replace_sase.md)**, the five-researcher
consolidation from 2026-10-09. Two earlier comparisons also exist:
[`202609/sase_vs_hermes_agent`](../../202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md) and
[`202604/sase_vs_hermes_agent.md`](../../202604/sase_vs_hermes_agent.md).

What carries over from them:

- **The products are complements, not rivals.**
  - *Hermes is the agent:* it has its own tool loop.
  - *SASE is the control plane:* it supervises vendor CLIs as single-turn workers and owns commits, gates and records.
  - The earlier report explicitly proposed **Hermes as the eighth SASE provider**, which "would turn the main competitor
    in the overlap into a supplier."
  - It named `hermes chat --oneshot -q … --format stream-json` as "the shape a SASE provider needs." It also warned that
    "this requires a maintained integration… shell access alone does not make it exist."
- **A billing trap, re-verified at the current pin** (`website/docs/integrations/providers.md`). Hermes's native
  Anthropic OAuth path bills **only Max extra-usage credits**, never the base Max allowance. How ChatGPT/Codex OAuth
  counts against plan quota is "not currently documented."

**What has changed since then.** The October 9 report pinned Hermes before the unified gateway runtime merged
(`eb75627faf`, 2026-10-14). Its "clean headless mode" is therefore no longer a self-contained subprocess on `main`. The
protocol survives; the execution model behind it does not
([two execution models](#two-execution-models-behind-one-cli)).

## What Hermes is good for inside SASE

"Fully supported" does not make every route through Hermes a good idea.

- **Claude via Anthropic OAuth**
  - *Verdict:* **Avoid**
  - *Why:* Bills **only Max extra-usage credits** (verified in `providers.md`). SASE's `claude` provider uses the base
    allowance.
- **Codex via ChatGPT OAuth**
  - *Verdict:* Redundant
  - *Why:* Plan-quota semantics are undocumented, and it probably shares the pool SASE's `codex` already uses.
- **xAI via SuperGrok OAuth**
  - *Verdict:* Redundant
  - *Why:* SASE has `grok`. Hermes's docs flag HTTP 403s on some tiers.
- **Nous Portal**
  - *Verdict:* **Primary value**
  - *Why:* No other SASE provider reaches it.
- **OpenRouter and API-key models (Kimi, GLM, DeepSeek, MiniMax, …)**
  - *Verdict:* Good
  - *Why:* Overlaps OpenCode, but brings a different harness, credential pools and fallback chains.
- **Local models (llama.cpp, Ollama, vLLM)**
  - *Verdict:* Good
  - *Why:* Cheap or offline workers for small tasks.
- **Hermes's *harness* itself**
  - *Verdict:* Interesting
  - *Why:* Fuzzy-matching `patch`, syntax checks on write, LSP diagnostics. It adds harness diversity to swarms like
    this one.

## Two execution models behind one CLI

### The verified timeline

The lead checked each tag for `hermes_cli/gateway_chat.py` and read `cmd_chat` at each tag.

- **`v0.22.0`**
  - *Date:* 2026-10-13
  - *`chat --format stream-json` runs…:* in the CLI process (local `AIAgent`)
  - *Evidence:* No `gateway_chat.py`
- **`v0.22.1`**
  - *Date:* 2026-10-14
  - *`chat --format stream-json` runs…:* **in the gateway daemon**
  - *Evidence:* Built from `main` by mistake: `cmd_chat` calls `launch_gateway_chat`
- **`v0.22.2` (current stable)**
  - *Date:* 2026-10-15
  - *`chat --format stream-json` runs…:* **in the CLI process**
  - *Evidence:* Re-cut from `release/0.22.1`. The commit message reads: "v0.22.1 was built from main … instead of
    release/0.22.1 … Never merge this branch into main."
- **`main` / canaries**
  - *Date:* 2026-10-16 onward
  - *`chat --format stream-json` runs…:* **in the gateway daemon**
  - *Evidence:* `main.py:1697-1704`; `_chat_runs_at_gateway`: "Every `hermes` / `hermes chat` turn (classic view, `-q`,
    `-z`, TUI) executes in the gateway"

The parser is the same on both lines. `--oneshot`, `--query-file`, `--format`, `--yolo`, `--ignore-rules`, `--in`,
`--toolsets`, `--reasoning`, `--provider` and `--max-turns` all appear in `hermes_cli/_parser.py` at both `v0.22.2` and
`main`. **A familiar command line and version string prove nothing about the execution contract.** cdx made this point
first; it is the most important finding in the swarm.

The cld report dates the gateway to "v0.22.0". That is wrong in detail: `v0.22.0` predates it and `v0.22.2` reverted
it. Its analysis of the gateway path itself, however, checks out.

### What the gateway path does to a naive adapter

All of the following was verified at `8f5693af41`.

- **The CLI is only a WebSocket client.** `gateway_chat.py:1` reads: "Normal classic/one-shot launch through the
  canonical gateway, never AIAgent."
- **Interrupting the client detaches instead of cancelling.** On `KeyboardInterrupt` the client prints "Detached;
  accepted work continues at the gateway." and exits 130 (`gateway_chat.py`, in `launch_from_args`).
  - No SIGTERM handler is installed on this path, so SIGTERM simply kills the client.
  - That is inferred from the code: verify it in the spike.
- **The daemon inherits its launcher's environment.** If no daemon is running, the client spawns one detached
  (`gateway_runtime_start.py`, `spawn_unmanaged_gateway`).
  - Its environment is the **launching client's `os.environ`**, with provider credentials scrubbed and the
    `DAEMON_STRIPPED_ENV` launch flags and session-context variables removed. `SASE_*` variables survive.
  - It exits after `gateway.unmanaged_idle_exit_seconds` of idleness (600 s by default).
- **Later sessions get only an allowlist of the caller's environment** (`agent/session_client_env.py`). It covers a few
  behaviour variables (including `HERMES_EPHEMERAL_SYSTEM_PROMPT`), toolchain variables and configured extras.
  `SASE_*` names are not on it, and secret-looking names are refused.

What happens to each SASE mechanism against a shared or personal daemon:

- **Agent identity.** Tools need `SASE_ARTIFACTS_DIR`, the finalizer nonce, agent and workspace ids, and
  `SASE_LAUNCH_SCRATCH_KEY`.
  - *What happens against a shared or personal daemon:* Tools see the **daemon's** values: those of whichever SASE
    agent started it. Declarations, artifacts and gates get attributed to the wrong agent.
  - *Severity:* Critical
- **Containment.** A runner's `sase-agent-*` scope is swept when the runner exits (`src/sase/detach_scope.py`).
  - *What happens against a shared or personal daemon:* The daemon, and every tool it runs for *other* agents, lives
    in the first agent's cgroup. When that agent's runner exits, the sweep kills the others mid-turn.
  - *Severity:* Critical
- **Interrupt and continuation.** `process.terminate()` is followed by a continuation relaunch.
  - *What happens against a shared or personal daemon:* The old turn keeps running while the continuation starts a
    second writer on the same checkout.
  - *Severity:* High
- **Teardown watchdog.** It reaps descendants by `ppid` after the declaration.
  - *What happens against a shared or personal daemon:* It reaps the client but not necessarily the daemon. Work can
    outlive the turn.
  - *Severity:* Medium
- **Hermeticity.**
  - *What happens against a shared or personal daemon:* The default `~/.hermes` home brings the user's SOUL, memory,
    curator, plugins, MCP servers, history and any installed gateway *service*.
  - *Severity:* High
- **Global controls.**
  - *What happens against a shared or personal daemon:* `hermes gateway stop --all` ("Stop ALL gateway processes
    across all profiles") kills in-flight SASE turns.
  - *Severity:* Low; document it

**What this means for the design.** Any adapter shipped against `main` must either:

- **own** a per-agent daemon, which is what a SASE-owned profile home does; or
- **bypass** the gateway entirely, which is what cdx's companion worker does.

It must also refuse, before submitting work, any execution mode it has not validated.

## Options considered

- **A. Stream-json subprocess using the user's `~/.hermes` (the grk, mus and gem design)**
  - *Correct on stable?:* ✅ (leaks into the personal home)
  - *Correct on `main`?:* ❌ env misattribution, detached interrupts, cgroup cross-kill
  - *Data fidelity:* Text, tools, tokens
  - *Cost and coupling:* Low
  - *Verdict:* Reject as the shipping design
- **B. Stream-json subprocess inside a SASE-owned per-workspace profile home (cld)**
  - *Correct on stable?:* ✅
  - *Correct on `main`?:* ✅ *if* the spike confirms per-agent daemon ownership
  - *Data fidelity:* Text, tools, tokens; no reasoning or cost
  - *Cost and coupling:* Medium: adapter plus home manager
  - *Verdict:* **Recommended**
- **C. Foreground companion worker: a Hermes plugin command that runs one `AIAgent.run_conversation` (cdx)**
  - *Correct on stable?:* ✅
  - *Correct on `main`?:* ✅ by construction: no gateway, caller-chosen session id, `ephemeral_system_prompt` and
    `skip_*` kwargs
  - *Data fidelity:* Best: callbacks, reasoning, cost
  - *Cost and coupling:* High: pinned against volatile internals and private runtime-resolution helpers
  - *Verdict:* **Escalation path** if B fails the spike
- **D. ACP client (`hermes acp`)**
  - *Correct on stable?:* ⚠️
  - *Correct on `main`?:* ⚠️ the default `HermesACPAgent()` is also a gateway viewer
  - *Data fidelity:* Adds thought chunks and `session/cancel`
  - *Cost and coupling:* High: SASE has no ACP invocation client
  - *Verdict:* Reserve for a generic ACP provider
- **E. One shared SASE gateway plus `client_env_passthrough`**
  - *Correct on stable?:* —
  - *Correct on `main`?:* ❌ tools escape agent scopes; secret-like names (`*KEY*`) are refused
  - *Data fidelity:* Same as B
  - *Cost and coupling:* Medium
  - *Verdict:* Reject
- **F. `hermes -z` text mode**
  - *Correct on stable?:* ✅
  - *Correct on `main`?:* ✅ only with B's isolation
  - *Data fidelity:* Final text only, no tool rows
  - *Cost and coupling:* Low
  - *Verdict:* Fallback only
- **G. API server, TUI JSON-RPC, MCP, legacy `hermes-agent` runner, direct Nous inference API**
  - *Correct on stable?:* —
  - *Correct on `main`?:* —
  - *Data fidelity:* —
  - *Cost and coupling:* —
  - *Verdict:* Reject: no per-request cwd, internal, no prompt runner, or no agent loop

## Where the reports disagreed

- **Does stream-json run as a hermetic subprocess?**
  - *Positions:* grk, mus, gem: yes. cdx: stable yes, `main` no. cld: no, "since v0.22.0".
  - *Resolution:* **cdx is right.** Stable `v0.22.2` is local; `main` uses the gateway; `v0.22.1` was a mis-cut.
  - *Basis:* Lead verification ([two execution models](#two-execution-models-behind-one-cli))
- **Transport**
  - *Positions:* cdx: a companion foreground worker, with the stable CLI only as a prototype. Others: the
    stream-json CLI.
  - *Resolution:* **Stream-json CLI inside a SASE-owned home** is the primary design. The companion is the escalation
    path.
  - *Basis:* The CLI is public and identical across versions. `run_agent.py` saw 47 commits in 30 days, and upstream
    moved the CLI *away* from in-process `AIAgent`.
- **Packaging**
  - *Positions:* cdx: external `sase-hermes`. Others: bundled.
  - *Resolution:* **Bundled.**
  - *Basis:* "Fully supported" means editing core-only lists: `DIRECTIVE_PROVIDERS` and `_DIRECTIVE_SYMBOLS` in
    `instructions/directives.py`, the effort mirror, doctor fallbacks, the query enum and the verifier. It also needs a
    SASE-side `install_argv` extension. Grok and Muse were bundled.
- **Instruction channel**
  - *Positions:* cld: `HERMES_EPHEMERAL_SYSTEM_PROMPT`. grk, mus, gem: prefix the query file (the Muse pattern). cdx:
    a private file read by the companion.
  - *Resolution:* **The ephemeral system prompt is primary; the prompt prefix is the oversize fallback.**
  - *Basis:* See [instruction delivery](#instruction-delivery)
- **Sunset flag `hermes_explicit_instructions`**
  - *Positions:* grk, mus: yes. cld: no.
  - *Resolution:* **No sunset flag.**
  - *Basis:* The `sase_flags` memory reserves `sunset` for deprecation and backward compatibility, and no old Hermes
    branch exists. Explicit-only selection gates exposure, as it did for Grok and Muse.
- **`--source tool`**
  - *Positions:* grk, mus, gem: pass it. cld: don't.
  - *Resolution:* **Don't pass it.**
  - *Basis:* On `main`, `agent/oneshot_footprint.py:is_single_query_session()` decides one-shot status by
    `policy.source == "oneshot"`. `--source tool` silently drops the one-shot protections: `skill_manage` is hidden and
    delegation is capped. The SASE profile home already keeps runs out of the user's history.
- **`--ignore-user-config`**
  - *Positions:* gem: mandatory. grk, mus: avoid.
  - *Resolution:* **Avoid.**
  - *Basis:* It freezes code defaults and forces an explicit `--model`. On `main` it also triggers a "bypass launch"
    managed worker. Hermeticity comes from the SASE profile instead.
- **Skill deploy subpath**
  - *Positions:* gem: `.hermes`. mus: `.hermes/skills`. cld: a separate directory listed in `skills.external_dirs`.
  - *Resolution:* **A SASE-owned directory listed in `skills.external_dirs`.**
  - *Basis:* SASE deploys to `~/<subpath>/skills/<name>/SKILL.md` (`src/sase/main/_init_skills_sources.py:76`). So
    `.hermes` writes into the user's *default* profile, and `.hermes/skills` produces `~/.hermes/skills/skills/`.
- **Autodetect priority**
  - *Positions:* grk: a late priority (about 40). Others: none.
  - *Resolution:* **None in v1.**
  - *Basis:* A generic binary name and the behavioural surprise of inheriting a personal Hermes config. The doctor
    identity probe matches `Hermes Agent v` (`_startup_fast.py:203`).
- **Short name**
  - *Positions:* `hrm` (cdx, cld, grk) or `her` (mus, gem)
  - *Resolution:* **`hrm`.**
  - *Basis:* Both are free. `hrm` matches the consonant style of `grk`, `qwn` and `cdx`.
- **Sync ceiling**
  - *Positions:* grk: don't claim one. cld: export one. cdx: only if enforced.
  - *Resolution:* **Set it and declare it.** SASE sets `TERMINAL_MAX_FOREGROUND_TIMEOUT` and `terminal.timeout` in the
    owned home, so the ceiling is enforced, not guessed.
  - *Basis:* Hermes promotes any foreground command whose timeout exceeds the ceiling (600 s by default) to the
    background (`tools/terminal_tool.py`).
- **Delegation toolset**
  - *Positions:* cld: include it (one-shot caps it at two synchronous children). cdx, grk: off in v1.
  - *Resolution:* **Off in v1.**
  - *Basis:* Children receive no SASE instructions (`subagent: none`). Root-only declaration
    (`helpers-return-roots-declare`) is not yet proven for them.
- **Resume**
  - *Positions:* mus: use `--resume` for true continuation. cld: SASE resume is transcript-based.
  - *Resolution:* **Don't depend on native resume.**
  - *Basis:* On `main` the caller cannot choose the session id. Resume also re-enters a gateway-frozen route. SASE's
    continuation loop is enough. Revisit only after the spike.
- **Installer hangs without `install_argv`**
  - *Positions:* grk: yes
  - *Resolution:* **Overstated, but the extension is still needed.**
  - *Basis:* `scripts/install.sh` skips setup when `/dev/tty` cannot be opened. With a terminal, though, it runs
    `hermes setup` *and* `hermes gateway install --if-missing`, which installs a persistent gateway service. SASE
    supports `install_env` but not `install_argv`, and the installer's `--non-interactive` switch is a flag only.
- **gem's model catalog (`nous/hermes-3-llama-3.1-405b`, …)**
  - *Positions:* gem
  - *Resolution:* **Unverified. Do not seed from it.**
  - *Basis:* No other report or source check confirms these route strings.

## Recommended design

### Packaging and identity

- **Entry point:** add `hermes = "sase.llm_provider.hermes:HermesProvider"` to `pyproject.toml`. Use the Muse module
  split:
  - `hermes.py` (facade)
  - `_hermes_launch.py`
  - `_hermes_home.py` (**new compared with Grok and Muse**)
  - `_hermes_directive.py`
  - `_subprocess_hermes.py`
  - `_tool_call_hermes.py`
  - later, `usage/hermes.py`
- **Identity:** name `hermes`, short name `hrm`, `menu_key: "h"`, and an unused Nous gold or violet colour that is
  distinct from Grok cyan and Muse blue.
- **Selection:**
  - **Explicit only:** `%model:hermes/<route>`, `llm_provider.provider: hermes`, or `SASE_HERMES_PATH`.
  - Publish `llm_autodetect_cli_name = "hermes"` with **no** priority.
  - Keep Hermes out of the shipped `@xsmall`–`@xlarge` pools until it has soaked. Hermes is often metered, and those
    pools round-robin subscription CLIs.
- **No feature flag.** Grok and Muse set this precedent. If the epic lands phases that would expose a half-built
  provider, use a `beta` epic-scaffolding flag created with `sase flag new`, and delete it before the epic lands.

### Command construction

```sh
# per-invocation environment (the adapter sets these; never global)
HERMES_HOME=~/.hermes/profiles/sase-<workspace-hash>
HERMES_EPHEMERAL_SYSTEM_PROMPT=<SASE root instruction bundle>   # ≤ 120 KiB, else prefix fallback
TERMINAL_MAX_FOREGROUND_TIMEOUT=<sync ceiling>                  # reaches tools via the agent's own process/daemon

hermes chat --oneshot --query-file - --format stream-json \
  --yolo --ignore-rules --accept-hooks \
  [-m <route>] [--provider <backend>] [--reasoning <level>] \
  -t terminal,file,web,skills,todo \
  [SASE_HERMES_{LARGE,SMALL}_ARGS] < prompt
```

Why each choice:

- **`--query-file -`.** The prompt arrives verbatim on stdin. Nothing lands in argv and nothing is shell-interpreted.
- **`--yolo`.** The default `approvals.single_query_mode: deny` silently blocks `git`, `rm` and similar commands in
  finite sessions. Bypass is SASE's posture for every CLI; Hermes's hardline blocklist still applies.
- **`--ignore-rules`.** It skips `AGENTS.md`, `CLAUDE.md`, `.hermes.md`, SOUL, memory, subdirectory hints and
  preloaded skills, but it keeps the skills index. This is the explicit-delivery posture Grok and Muse use.
  - **Parity gap (cdx):** it also drops nested-directory rules files. That matches Grok and Muse today, so treat it as
    a known parity gap, not a blocker.
- **No `--source`, no `--max-turns`, no `-w`, no `--ignore-user-config`, no `--safe-mode`, no `--resume`.** The reasons
  are in [where the reports disagreed](#where-the-reports-disagreed). SASE's watchdogs bound the run. The reports
  disagree on Hermes's effective default turn budget (cld: unlimited; mus: 500), so record it in the spike.
- **The model route is opaque.** See [models and effort](#models-and-effort).

### The SASE-owned Hermes home

This is the one piece of new machinery compared with Grok and Muse.

**Bootstrap.**

- The user runs one setup command: `hermes profile create sase --clone`. It copies `config.yaml`, `.env` and skills.
- `sase doctor` and `sase agent-cli` check that the profile exists and print this command if it is missing.
- SASE never logs in on the user's behalf.

**Derivation, per workspace.**

- Create or refresh `~/.hermes/profiles/sase-<hash>`, where the hash is derived from the absolute workspace path. Clone
  it from the `sase` profile, then apply the overlay below.
- Re-derive the home when the `sase` profile's config fingerprint changes.
- Homes under `<root>/profiles/` are trusted as-is by the gateway spawner (lead-verified comment in
  `gateway_runtime_start.py`).
- Auth reuses the root `auth.json` read-only (cld, `hermes_cli/auth.py:486-530`). Verify in the spike that this covers
  OAuth refresh under concurrency.
- **Why per workspace:** a workspace is claimed by one agent at a time. Keying by workspace bounds the number of homes
  and keeps `state.db` warm. It also gives each agent its own daemon on `main`.

**Hermetic overlay.** Every key below exists in `hermes_cli/config_defaults.py`; the values are from cld, plus lead
additions.

- **`updates.check`, `plugins.auto_update_check_hours`**
  - *Value:* `false`, `0`
  - *Why:* No passive network checks. `hermes --version` otherwise performs a synchronous update check.
- **`curator.enabled`**
  - *Value:* `false`
  - *Why:* The skills curator runs from the gateway poll.
- **`memory.memory_enabled`, `memory.user_profile_enabled`**
  - *Value:* `false`
  - *Why:* No personal memory.
- **`memory.nudge_interval`, `skills.creation_nudge_interval`**
  - *Value:* `0`
  - *Why:* No self-improvement nudges.
- **`skills.external_dirs`**
  - *Value:* `[~/.hermes/sase-skills/skills]`
  - *Why:* SASE skills, deployed through `llm_skill_deploy_subpath → ".hermes/sase-skills"`.
- **`skills.project_discovery`**
  - *Value:* `false`
  - *Why:* No scan of untrusted `.agents/skills`.
- **`approvals.mode`**
  - *Value:* `off`
  - *Why:* Belt and braces with `--yolo`.
- **`agent.disabled_toolsets`**
  - *Value:* `[memory, session_search, cronjob, clarify, kanban, delegation, code_execution]`
  - *Why:* Defence in depth beside `-t`. Confirm the exact toolset names against `toolsets.py` in the spike.
- **`fallback_providers`**
  - *Value:* `[]`
  - *Why:* An explicit SASE route must not silently switch backend (cdx).
- **`terminal.timeout`**
  - *Value:* the sync ceiling
  - *Why:* The default is 180 s.
- **`terminal.env_passthrough`**
  - *Value:* e.g. `[GH_TOKEN, GITHUB_TOKEN]` if SASE workflows need them
  - *Why:* **Lead finding:** Hermes strips `GH_TOKEN` and `GITHUB_TOKEN` from *every* terminal subprocess
    (`_ALWAYS_STRIP_KEYS` in `tools/environments/local_env_policy.py`). `gh` authenticated through those variables
    would fail inside Hermes.
- **`agent.coding_context`**
  - *Value:* evaluate in the spike
  - *Why:* Hermes's coding brief and git snapshot may duplicate SASE context.
- **`gateway.unmanaged_idle_exit_seconds`**
  - *Value:* about 30–60
  - *Why:* A backstop in case SASE's own stop fails.

**Daemon lifecycle (`main` runtime only).**

- **At invoke start:** stop any live daemon for this home. On hosts without systemd scopes, a stale daemon would
  otherwise carry the previous agent's environment.
- **At invoke end** (success, error or interrupt): run `hermes gateway stop` with this `HERMES_HOME`, or signal the
  recorded pid, then confirm it exited.
- **On a SASE interrupt:** stop the daemon instead of calling `process.terminate()`, then let the existing continuation
  loop relaunch.
- **On stable:** none of this applies. Native SIGTERM performs a hard interrupt with a 1.5 s grace period
  (`cli_single_query.py:_interrupt_agent_for_signal` at `v0.22.2`).
- **Mode detection:** the adapter detects which runtime it faces from the version window (see
  [installation and doctor checks](#installation-and-doctor-checks)) and refuses unvalidated combinations before
  submitting any work.

**Cost.** Each running Hermes agent on `main` holds about 270 MB of RAM and pays a daemon cold start (cld; measure in
the spike). Track this against the apollo OOM history.

### Instruction delivery

**Primary channel: `CHANNEL_HERMES_ROOT = "hermes.ephemeral_system_prompt"`.** The plan is
`root: explicit, max_bytes ≈ 120 KiB`, `subagent: none`. Why this channel:

- **It is system-role text.** It is appended to the effective system prompt at API time
  (`agent/turn_context.py:1352`). That is the closest Hermes analogue to Claude's `--append-system-prompt-file`.
- **It is never written into Hermes's session history.** A prompt prefix would be.
- **It works on both runtimes.**
  - On stable, the CLI reads the variable directly (`cli_init_mixin.py:255`), and it takes precedence over
    `display.personality`.
  - On `main`, it is on the per-session `client_env` allowlist and is stripped from the daemon, so it never leaks
    between sessions.
- **It is bounded.** Linux rejects any single environment string over 128 KiB (`MAX_ARG_STRLEN`), the same limit Grok's
  argv guard protects. `main` also caps the forwarded map at 256 KiB.

**Fallback: the Muse pattern.** An oversized or empty bundle calls `report_fallback(...)` and delivers
`{bundle}\n\n--- User Prompt ---\n{prompt}` through the stdin query. That still survives compression, because Hermes
protects the first three messages (`protect_first_n=3`).

**Wiring.** Register Hermes in:

- `DIRECTIVE_PROVIDERS` and `_DIRECTIVE_SYMBOLS` (`instructions/directives.py`)
- `fingerprints.py`, `run_index.py` (plus a session finder), `readout.py`, `_verify_*`, `coverage_*`
- `instructions/cache.py`'s assumption about where directives live

Record the bundle digest and the Hermes session id in the instruction manifest.

### Single-turn conformance

**Disabled mechanically:**

- **Toolsets.** Use the allowlist `-t terminal,file,web,skills,todo` together with `agent.disabled_toolsets`. That
  removes `cronjob`, `kanban`, `clarify` (SASE owns questions), `memory`, `session_search`, `delegation`,
  `code_execution` (a policy bypass path, per cdx), `browser`, `computer_use`, `image_gen` and `tts`.
  - Re-enable `browser` or `delegation` only through extra args after soak.
- **Foreground ceiling.** Set it as described in [command construction](#command-construction) and
  [the SASE-owned Hermes home](#the-sase-owned-hermes-home), and declare it through `llm_sync_ceiling_seconds`.

**Named in a Hermes single-turn directive** (the Grok and Muse pattern):

- Never pass `background: true` to `terminal`, and never end a command with `&`.
- A command that returns a process id must be waited on with `process_manage` (`action: wait`).
- Anything that can outlast the turn goes to `/sase_monitor` *before* it starts.
- `/goal`, `/loop`, `/heartbeat` and cron do not exist here.
- Handoff commands (`sase monitor start`, `sase plan propose`, `sase questions`, `sase pipe`) can take up to a minute;
  wait for them.
- Do not commit; submit `/sase_final`.

**Bounded guard.** Reuse `_wait_signals.py` and `_wait_guard.py`. Flag any `terminal` call with `background: true`, and
any process-start event late in the turn. Use `SASE_HERMES_MAX_WAIT_CONTINUATIONS`, defaulting to 2.

**Known harness behaviour to neutralize.** Stable's one-shot path drains background completions and can run
*follow-up conversations* in the same process (`cli_single_query.py:_follow_up`). The directive and toolset policy
should leave nothing for it to drain. The spike should confirm that.

### Parsing the stream-json output

Hermes emits one JSON object per line, each with a `timestamp`: `system/init` → `text` deltas → `tool_use` and
`tool_result` → exactly one `result`. The events are flat, so the shared Claude-style Messages reader does not fit and
Hermes needs its own small parser.

- **Text.**
  - Deltas feed the live reply.
  - **`result.text` is the authoritative `InvokeResult.content`.** Never append it to the streamed deltas.
  - `replay_gap: true` means the deltas stopped early.
- **Completion.** Require both a terminal `result` *and* an acceptable process exit. Empty output, EOF, a successful
  tool call or non-empty prose are not proof of success.
- **Session id.** Take it from `result.session_id`, falling back to the stderr `Session:` line. On `main`,
  `init.session_id` is always empty, and compression can rotate the id.
- **Exit codes,** by runtime:
  - **`main`**
    - *0:* completed
    - *1:* failed, partial, budget hit, or init failed
    - *2:* unsupported option
    - *3:* needs a human, or the turn was lost to a daemon crash
    - *130:* interrupted
  - **stable**
    - *0:* completed
    - *1:* failed, partial or budget hit
    - *2:* —
    - *3:* —
    - *130:* interrupted
  - **Exit 3 should be impossible** under `--yolo` with `clarify` removed. Treat it as a loud adapter failure that
    names the session id.
  - Exit 75 (`EX_TEMPFAIL`) is a Kanban-worker path only.
- **Tool calls (`_tool_call_hermes.py`).**
  - Name map: `terminal`→`Bash`, `read_file`→`Read`, `write_file`→`Write`, `patch`→`Edit`, `search_files`→`Grep` or
    `Glob` (by `target`), `web_search`→`WebSearch`, `web_extract`→`WebFetch`, `todo_list`→`TodoWrite`,
    `skill_view`→`Skill`. Unmapped names pass through unchanged.
  - Input normalization: `path`→`file_path`.
  - Pair `tool_use` with `tool_result` by `tool_call_id`, falling back to name order.
  - `tool_result.output` is capped at 5,000 characters plus a truncation suffix.
- **Usage.** Map `result.tokens` → `input_tokens`, `output_tokens`, `cache_read_input_tokens` (from `cache_read`) and
  `cache_creation_input_tokens` (from `cache_write`), once per terminal result.
  - The stock emitter defaults missing counters to zero, so a zero is not proof of a measurement.
  - Auxiliary and helper calls, reasoning tokens and cost are *not* in the stream; the emitter drops `model`,
    `provider` and `estimated_cost_usd`.
  - Whether `input` includes cached tokens is unverified.
- **Fixtures.** Store them under `tests/fixtures/hermes_stream/<cli-version>/` (the Grok convention). Cover:
  - a no-tool turn
  - a tool turn with parallel same-name calls
  - a failure
  - a usage-limit failure
  - `replay_gap`
  - an init failure
  - malformed or unknown events
  - stderr flooding

### Models and effort

- **Three-layer identity (cdx).** The SASE provider is `hermes`; beneath it sit the Hermes backend and the backend's
  opaque model id.
- **Routing.** SASE strips the `hermes/` prefix and passes the remainder to `-m` unchanged.
  - Hermes itself splits `provider:model` when the left side is a known provider (`hermes_cli/models.py:849-876`). So
    `%model:hermes/openrouter:anthropic/claude-…` works without a new SASE grammar.
  - `--provider` is passed only from `SASE_HERMES_INFERENCE_PROVIDER` or extra args.
- **Catalog.**
  - Ship a short curated `models.yml` block. The manifest requires both a `large` and a `small` tier, each naming a
    listed model.
  - Use routes the user actually runs (Nous Portal, OpenRouter, local) and verify each at implementation time.
  - Document that the catalog is a default route, not a capability list.
- **Effort.**
  - Map SASE's `none…max` to `--reasoning <level>`, and register them in `_PROVIDER_SUPPORTED_EFFORTS["hermes"]`.
  - Add `hermes` to `_CLI_VALIDATED_PROVIDERS`: Hermes clamps per model and "only ever weakens."
  - Hermes's `ultra` has no SASE equivalent.
  - Record requested versus effective effort where Hermes exposes it (cdx).

### Retry, usage limits and interrupts

- **No whole-task retry while the previous worker might still run** (cdx). On `main`, stop the daemon first.
  - Treat a gateway "unknown admission" as an unknown outcome, never as a transient failure.
  - Do not multiply Hermes's internal API retries by SASE's invocation retries.
- **Retry patterns.** Make them Hermes-namespaced so they cannot collide with Codex's generic `429`:
  - `"Gateway connection/read failed"`
  - the "rate-limited every one of N attempts" family (`agent/turn_failure_copy.py`)
  - wording captured during the spike
- **Usage-limit patterns.**
  - Patterns: `"its usage limit resets in"` and `"Billing or credits exhausted"`.
  - Hermes prints "Limit resets at HH:MM (in Xh YYm)", so `parse_reset_hint` can work here, unlike for Grok.
  - **Scope caveat.** One `hermes` provider fronts many backends, so auto-disabling all of Hermes when OpenRouter
    credits run out is coarse. Accept that in v1 and document it.
- **Usage probe (phase 3).** `hermes usage --provider P --json` returns windows for `openai-codex`, `anthropic` and
  `openrouter` only. It needs:
  - a `sase-core` normalizer binding
  - a `sase-core-revision.txt` pin bump (the Muse precedent; see the Rust boundary memory)
  - a mapping from SASE's provider-oriented usage hook to multiple backend accounts
- **Rust core.** No other provider-specific `sase-core` change is needed: provider ids are free strings.

### Installation and doctor checks

**Install metadata.**

- **`manager`:** `"script"`
- **`install_script_url`:** `https://hermes-agent.nousresearch.com/install.sh`
- **`install_env`:** `{HERMES_INSTALL_CHANNEL: stable}`
- **`install_argv`:** `["--non-interactive"]` (**new SASE extension**)
- **`self_update_argv`:** `["update"]`
- **`version_regex`:** `Hermes Agent v(?P<version>\d+\.\d+\.\d+)`

Packaging notes:

- Hermes is not published on PyPI, npm or Homebrew.
- The installer accepts `--commit SHA`, which allows exact pinning.

**Doctor.**

- a `_PROVIDER_SETUP_FALLBACKS["hermes"]` entry: run `hermes setup` / `hermes model`, then
  `hermes profile create sase --clone`
- a `checks_deep_providers.py` identity probe for `Hermes Agent v`, run under the SASE profile so the probe makes no
  network update call
- a check that the `sase` profile exists
- a **tested-version window** that reports *runtime mode* (local or gateway) and warns before `agent-cli update` moves
  past the window
- a warning when the profile's default backend is Anthropic OAuth (the extra-usage billing trap)

**Auth evidence.**

- credential paths: `~/.hermes/auth.json`, `~/.hermes/.env`
- common key variables: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, plus the Nous key name once the
  spike confirms it

### Interactive CLI and skills

**Interactive CLI.** `menu_key: "h"`, `bypass_args: ["--yolo"]`, `model_args: ["-m", "{model}"]`, launched with the
`sase` profile.

**Skills.**

- **Deploy target.** Set `llm_skill_deploy_subpath → ".hermes/sase-skills"` and list the resulting
  `~/.hermes/sase-skills/skills` in each home's `skills.external_dirs`. This does not pollute the personal profile.
- **Template context:** `provider_name: "Hermes"`, `provider_tool_name: "Hermes Agent"`,
  `provider_native_ask_tool: "clarify"`.
- **Description truncation.** Hermes truncates skill descriptions to 60 characters in the prompt index. SASE's bundle
  names skills explicitly, so this is tolerable.
- **Unverified:** whether `/sase_final` slash-expansion works in a `-q` prompt on the gateway path.

### Files a full-support change touches

Every path below was spot-checked to exist at `e5f2d768ea`.

- **Entry point:** `pyproject.toml` `[project.entry-points."sase_llm"]`
- **Catalog:** `src/sase/llm_provider/models.yml`
- **Effort mirror:** `src/sase/llm_provider/model_policy.py`: `_PROVIDER_SUPPORTED_EFFORTS`, `_CLI_VALIDATED_PROVIDERS`
- **Instruction channel:** `src/sase/llm_provider/instruction_delivery.py`: a `CHANNEL_HERMES_ROOT` beside
  `CHANNEL_MUSE_ROOT`, matching `CHANNEL_RE`
- **Directive and verifier:** `src/sase/instructions/directives.py` (`DIRECTIVE_PROVIDERS`, `_DIRECTIVE_SYMBOLS`),
  `fingerprints.py`, `run_index.py`, `readout.py`, `_verify_*`, `coverage_*`, `cache.py`
- **Doctor:** `src/sase/doctor/checks_providers.py` (`_PROVIDER_SETUP_FALLBACKS`), `checks_deep_providers.py`
- **Install extension:** `src/sase/llm_provider/_registry_metadata.py`, `src/sase/agent_clis/{models,detect,install}.py`
- **Query enum:** `src/sase/ace/query_profile/profiles/_agents_shared.py` (`AGENT_PROVIDER_VALUES`)
- **Presentation:** `src/sase/integrations/provider_badges.py`, `provider_palette.py`, `_registry_catalog.py`
- **Config:** `src/sase/default_config.yml`: the provider-list comment (per the gotchas memory)
- **Closed-list tests:** `test_model_manifest.py`, `test_interactive_cli_metadata.py`, `test_provider_text_palette.py`,
  `tests/tmux_agent/test_shell_script_parity.py`, and others
- **Docs:** `docs/reference/providers/hermes.md` (modelled on `grok.md` and `muse.md`), `index.md`, `agent-clis.md`,
  `environment-variables.md`, the `docs/_meta/splits/llms.yml` row, nav, and model tables regenerated with `just fix`.
  Read the `docs_writing` memory note first.

Expect ACE screenshot goldens to change when a provider joins the menus. Inspect them; do not defer them silently.

## Phase 0 go or no-go spike

Run this before committing to the epic, against both stable `v0.22.2` and a pinned `main` canary. Use throwaway homes
and a cheap model.

1. **Capture fixtures** for the shapes listed in [parsing the stream-json output](#parsing-the-stream-json-output),
   plus exact failure wording for a bad model, a rate limit and a billing wall.
2. **Environment (`main`).** With a per-workspace `HERMES_HOME`, confirm that the daemon *and the tool subprocesses* see
   the agent's `SASE_*` variables (including `SASE_LAUNCH_SCRATCH_KEY` and the finalizer nonce) and
   `TERMINAL_MAX_FOREGROUND_TIMEOUT`. Confirm that `sase final context` works from Hermes's `terminal` tool.
3. **Ownership (`main`).** Confirm that `hermes gateway stop` scoped to that home stops an *unmanaged* idle-exit daemon
   and cancels its in-flight turn. Afterwards no process may still write to the workspace, and the `sase-agent-*` scope
   sweep must catch everything.
4. **Signals.** Record SIGTERM and SIGINT behaviour on both runtimes. On `main`, also check whether the descendant reap
   catches the daemon.
5. **Auth.** OAuth and API-key logins from the root home must work in `profiles/sase-*` homes, including two
   concurrent token refreshes.
6. **Instructions and skills.**
   - The bundle marker reaches the model context exactly once.
   - SASE skills are discoverable through `external_dirs`.
   - `/sase_final` is usable.
7. **End to end.** A real run must:
   - edit files
   - neither commit nor background anything
   - submit `/sase_final`, and separately perform one monitor handoff
   - show **no workspace activity after the turn ends**

**Decision rule.** If items 2–3 fail, or need pervasive workarounds, keep the [recommended design](#recommended-design)
but replace the transport with cdx's companion worker. Concretely, that is a Hermes plugin command (`hermes sase-exec`,
a proposed name) that:

- reads a private request file
- runs one `AIAgent.run_conversation` with `ephemeral_system_prompt`, `skip_context_files`, `skip_memory`,
  `skip_background_review`, a SASE-chosen `session_id` and `cwd`
- enforces the tool policy through `pre_tool_call` hooks
- emits the same stream-json vocabulary plus a version handshake

That trades gateway risk for maintaining a pinned bridge to Hermes internals.

## Rollout

This follows the Grok (`sase-l3`) and Muse (`sase-ha`) epic shape. Grok landed in 9 commits in one day and then took
about 25 follow-ups. Hermes will be larger because of the home manager and daemon lifecycle.

0. **Spike:** [The Phase 0 spike](#phase-0-go-or-no-go-spike). It decides between CLI-in-owned-home and the companion
   worker.
1. **Core provider:** The modules from [packaging and identity](#packaging-and-identity), the home manager and overlay,
   daemon lifecycle, the stream parser and tool map, the entry point, the `models.yml` block, the effort mirror, retry
   and usage-limit defaults, version-window gating, and tests at Muse/Grok density. Explicit-only.
2. **Full support:** Explicit instruction delivery and the verifier/directive registration, the single-turn directive
   and wait guard, skills deployment, doctor (fallback, identity, profile, version window), `install_argv` plus
   `sase agent-cli install/update hermes`, the interactive launcher, badges, palette, query enum, and docs. Read the
   `generated_skills`, `docs_writing` and `tui` memory notes first.
3. **Polish:** A usage probe (with the `sase-core` normalizer and pin bump), a thinking pane once upstream emits
   reasoning, opt-in `browser` and `delegation`, size-alias membership after soak (subscription-backed routes only),
   and an opt-in live smoke recipe.

Send the [upstream asks](#upstream-asks) in parallel with phase 1.

## Acceptance criteria for full support

What "fully supported" requires, by test family:

- **Routing:** Opaque and `provider:model` routes, aliases, effort defaults and overrides, no collisions with existing
  providers
- **Protocol:** Unicode and partial lines, stderr floods, malformed or unknown events, a missing or duplicate `result`,
  mismatched process and result codes, truncated tool output
- **Observability:** The final answer shown once; parallel tool ids paired; correct token scope; live artifacts usable
- **Instructions:** The bundle hash reaches model context once; no native `AGENTS.md` duplication; skills discoverable
- **Lifecycle:** SIGINT, SIGTERM, forced kill, process-tree and daemon cleanup; nothing writes to the workspace after
  teardown
- **Handoffs:** A real final declaration and real monitor, plan and questions handoffs, with no Hermes continuation
  afterwards
- **Native tools:** Background requests, timeout promotion, delegation, `execute_code`, MCP and hooks cannot bypass
  policy
- **Isolation:** Two concurrent turns keep distinct cwd, nonce, artifacts, sessions and daemons; the personal Hermes
  home is unchanged
- **Failure:** Auth failure, invalid model, rate limit, partial response, and a crash after editing all remain failures
  with preserved evidence
- **Management:** Missing binary, wrong identity, out-of-window version, missing profile, interactive launch,
  non-interactive install

Cover most of this with synthetic streams and fake executables. Add a small opt-in live suite for auth, environment and
lifecycle, because a fake stream cannot prove daemon isolation. Run `just check` through the managed tool workflow;
`check-full` stays explicit-only.

## Risks

- **Churn dominates.** Lead-verified figures:
  - 16,716 commits in the 30 days to the pin
  - `run_agent.py` touched 47 times in 30 days
  - stream-json moved to the gateway transport on 2026-09-16 (`49ee9d6c74`), a month after it first appeared
  - the stable/`main` split described in [two execution models](#two-execution-models-behind-one-cli)

  Mitigations: a tested-version window enforced before any model call, fixtures keyed by version, a conformance suite
  rerun on every bump, and installs pinned to the stable channel or an exact `--commit`.
- **The next stable release flips the runtime.** Ship gateway-path support (the daemon lifecycle) in phase 1, not
  later, so a routine `hermes update` cannot silently break running agents.
- **Resources.** About 270 MB and one cold start per concurrent Hermes agent on `main`.
- **Users' global controls reach SASE homes.** `hermes gateway stop --all` kills them. The scope of `hermes pause` is
  unverified. `hermes profile list` will show `sase-*` homes; doctor can prune homes whose workspace is gone.
- **Security posture** is unchanged from other providers: bypass mode, no sandbox, and detection plus a fail-closed
  finalizer for agent commits. Hermes's hardline blocklist may occasionally refuse a legitimate command; surface those
  refusals in tool rows.
- **Telemetry gaps.** There are no reasoning events, no cost, and no effective model or provider in `result` until
  upstream adds them. Usage-probe coverage is 3 of about 40 backends.

## Upstream asks

Upstream accepts this kind of contribution: the stream-json protocol itself came from a community PR (`1657a1ce2d`).

1. **A supervised finite mode,** for example `chat --oneshot --format stream-json --isolated`. It would run the turn in
   a child of the client that inherits the client's environment and process group, and cancel on client signals. This
   one change would remove the home manager's daemon lifecycle and the need for a companion worker. The machinery
   partly exists already: `--safe-mode` runs "managed workers."
2. **SIGTERM and SIGHUP cancel on the stream-json path,** still emitting a `result` record, as the classic `-q -Q` path
   already does.
3. **A richer protocol:**
   - `reasoning` events
   - `model`, `provider`, `estimated_cost_usd`, `turn_exit_reason`, `failure_reason` and `failure_resets_at` in
     `result`
   - a populated `init.session_id`, or a caller-supplied `--session-id`
4. **`--system-prompt-file`,** so large bundles are not bound by environment-string limits.
5. **A network-free `--version`** and a non-interactive installer variable (`HERMES_INSTALL_NONINTERACTIVE`).

## Recommended solution

**Add `hermes` as a bundled, explicit-only SASE provider (short name `hrm`).** Its transport is Hermes's public
`hermes chat --oneshot --query-file - --format stream-json --yolo --ignore-rules --accept-hooks [-m …] [--reasoning …]
-t terminal,file,web,skills,todo` CLI. It always runs inside a SASE-owned, per-workspace Hermes profile home.

1. **Isolate.**
   - Each workspace gets `~/.hermes/profiles/sase-<hash>`, cloned from a user-created `sase` profile so the user's model
     configuration and logins carry over.
   - Overlay the hermetic settings from [the SASE-owned Hermes home](#the-sase-owned-hermes-home): no memory, curator,
     update checks, project skill discovery, backend fallback or approvals; SASE skills through `external_dirs`; the
     sync ceiling; and the token passthrough SASE workflows need.
2. **Own the execution under both runtimes.**
   - **Stable `v0.22.2`** runs in-process, and native signals already work.
   - **On `main`,** the agent's own client starts that home's gateway, which inherits the agent's environment and
     cgroup. SASE stops any stale daemon at invoke start, stops the daemon at invoke end, and stops it on interrupt.
   - Gate runtime mode by a tested-version window, and refuse unvalidated combinations before any model call.
3. **Normalize the harness.**
   - Deliver instructions through `HERMES_EPHEMERAL_SYSTEM_PROMPT` (system role, 120 KiB guard), falling back to a
     prompt prefix.
   - Use subagent slot `none` and register in the directive and verifier lists.
   - Enforce the toolset allowlist, a raised foreground ceiling declared as the sync ceiling, a Hermes single-turn
     directive and a bounded wait guard.
   - Add no sunset flag.
4. **Parse and present.**
   - A dedicated flat-JSONL parser: `result.text` is the content, `result.tokens` is usage, and the session id comes
     from `result`.
   - A Hermes→canonical tool-name map.
   - Grok-template metadata, doctor, `agent-cli` (with a small `install_argv` extension), interactive launcher,
     presentation and docs.
5. **Scope the value.** Curate routes for Nous Portal, OpenRouter and local models. Document that Claude and Codex stay
   on SASE's native providers ([what Hermes is good for](#what-hermes-is-good-for-inside-sase)). Keep Hermes out of
   size-alias pools until it has soaked.
6. **De-risk.**
   - Run the [Phase 0 spike](#phase-0-go-or-no-go-spike) first. If SASE cannot reliably own a per-agent daemon, keep
     everything above but swap the transport for cdx's foreground companion worker running `AIAgent` inside Hermes's
     own runtime.
   - Push [upstream](#upstream-asks) for a supervised finite mode. Once it lands, the daemon lifecycle collapses to a
     flag and the home manager shrinks to a config overlay.

**What to keep in reserve:**

- **ACP,** in case SASE later wants a generic ACP provider.
- **The companion worker,** as the fallback transport.

Neither should be the first build. ACP costs more, and the companion couples SASE to Hermes's most volatile internals.

## Sources

### Lead verification

These were checked directly by the lead for this report.

- **Hermes `8f5693af41` and `v0.22.2`/`d923a5eb48`,** opened with `sase repo open gh:nousresearch/hermes-agent`.
  - `hermes_cli/main.py` (`cmd_chat` at `v0.21.0`, `v0.22.0`, `v0.22.1`, `v0.22.2` and `main`; `_chat_runs_at_gateway`)
  - `hermes_cli/gateway_chat.py`, `gateway_chat_startup.py`, `gateway_runtime_start.py`
  - the release commit message on `d923a5eb48`
  - `hermes_cli/_parser.py` (flag parity across both lines)
  - `agent/oneshot_footprint.py`, `gateway/session_finite.py`
  - `agent/turn_context.py:1340-1356`, `agent/system_prompt.py:772`, `hermes_cli/cli_init_mixin.py:255` at
    `v0.22.2`, `agent/session_client_env.py:23`
  - `agent/agent_init.py:1543` (`protect_first_n`)
  - `tools/environments/local.py`, `local_env_policy.py` (credential scrubs and `_ALWAYS_STRIP_KEYS`)
  - `run_agent.py` (`AIAgent.__init__` kwargs)
  - `hermes_cli/plugins.py:629` (`register_cli_command`), `scripts/install.sh` (channels, `--non-interactive`, `--commit`,
    setup and gateway stages)
  - `hermes_cli/_startup_fast.py:203`, `hermes_cli/config_defaults.py` (`fallback_providers`,
    `unmanaged_idle_exit_seconds`, `env_passthrough`), the `hermes gateway stop --all` help text
  - `website/docs/integrations/providers.md` (subscription billing table)
  - git history: `eb75627faf`, `49ee9d6c74`, `1657a1ce2d`, and the commit counts above
- **SASE `e5f2d768ea`.**
  - `pyproject.toml` entry points
  - `src/sase/instructions/directives.py`, `src/sase/llm_provider/instruction_delivery.py`
  - `src/sase/llm_provider/model_policy.py`
  - `src/sase/main/_init_skills_sources.py` (skill deploy path semantics)
  - `src/sase/agent_clis/` and `_registry_metadata.py` (`install_env` exists; there is no `install_argv`)
  - provider short names, `src/sase/env_contracts.py`, `src/sase/detach_scope.py`
  - the touchpoint paths in [files a full-support change touches](#files-a-full-support-change-touches)
- **SASE memory and decisions:** `sase_flags` (flag kinds), `adapters-normalize-harnesses`, `single-turn-agents`,
  `helpers-return-roots-declare`, `host-owned-completion`, `size-alias-effort-ladder`, `rust-core-required`.

### Swarm reports

- [cdx](hermes_agent_sase_provider__cdx.md): the execution-ownership finding, the companion worker, the acceptance
  matrix, and the retry and usage scope.
- [cld](hermes_agent_sase_provider__cld.md): the gateway analysis, the per-workspace home, the overlay, the
  touchpoint inventory, the tool map, the value table and the upstream asks.
- [grk](hermes_agent_sase_provider__grk.md): the "fully supported" checklist, the toolset policy, the install
  extension, and the risk and non-goal list.
- [mus](hermes_agent_sase_provider__mus.md): the transport comparison (`chat` versus `-z`, `--query-file` versus argv)
  and the spike checklist.
- [gem](hermes_agent_sase_provider__gem.md): the rejected-model analysis (direct API and daemon), the binary-collision
  caution, and the hook skeleton. Its model catalog and `--ignore-user-config` advice are not adopted.

### Prior research reports

- [`202610/can_hermes_replace_sase`](../can_hermes_replace_sase/can_hermes_replace_sase.md) (2026-10-09)
- [`202609/sase_vs_hermes_agent`](../../202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md)
- [`202604/sase_vs_hermes_agent.md`](../../202604/sase_vs_hermes_agent.md)
