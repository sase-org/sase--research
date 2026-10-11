# Pi vs SASE: comparative research (`__mus`)

- Date: 2026-10-11
- Subject: https://github.com/earendil-works/pi ("Pi is a minimal, extensible agent harness that you can make your own")
- Method: opened `gh:earendil-works/pi` via `sase repo open` as an external checkout; read README, AGENTS.md, `packages/coding-agent/docs/` (how-pi-works, extensions, skills, sessions, rpc, sdk, models, settings, configuration, security, containerization, compaction, cli, themes, packages, prompt-templates, tui, mcp), plus package READMEs for `ai`, `agent`, `tui`, `durable`, `chord`, `codemode`, `telemetry`; compared against the local sase checkout (README, `docs/architecture.md`, `agent_providers.md`, `macros.md`, `memory.md`). Did not consult peer swarm reports.

## 1. What pi actually is

Pi is a **single-agent harness you own and extend**, not a fleet coordinator. The monorepo (`pi-monorepo`, TypeScript, Node >= 22.19, MIT, by Mario Zechner / badlogicgames) contains:

| Package | Role |
|---|---|
| `@earendil-works/pi-coding-agent` | The `pi` CLI: interactive TUI, print/JSON/RPC modes, sessions, tools (`read`, `bash`, `edit`, `write`, plus `grep`, `find`, `ls`, `powershell`), slash commands |
| `@earendil-works/pi-ai` | Unified multi-provider LLM API (OpenAI, Anthropic, Google, Bedrock, Ollama/LM Studio/vLLM-compatible endpoints, llama.cpp router, OAuth, custom provider extensions, generated model catalog overlaid from pi.dev) |
| `@earendil-works/pi-agent-core` | Transport-agnostic agent runtime with tool calling and state |
| `@earendil-works/pi-tui` | Standalone differential-rendering terminal UI library (main + alternate screen, CSI 2026 sync, IME-aware editor, Kitty/iTerm inline images) |
| `@earendil-works/pi-codemode` | Model-written JS runs in a QuickJS-on-WASM sandbox whose only capability is calling injected tools; nested tool calls never enter LLM context |
| `@earendil-works/chord` | Standalone app-composition runtime: plugins/facets, services, replicated state, delta tracking, remote-service boundary (no dependency on other pi packages) |
| `@earendil-works/pi-durable` | Experimental durable agent harness: conversations/commits persisted before display, resume-after-crash, task graph, child tasks (built on pi-ai + chord) |
| `@earendil-works/pi-telemetry` | Vendor-neutral telemetry contracts + in-memory reference adapter; no exporter, no global span state |
| `protocol` / `client` / `server` / `mcp` / `env` / `evals` | RPC protocol, typed RPC client, server embedding, MCP stdio/HTTP client support, env abstraction, evals |

Design stance is explicit and opinionated: **minimal core, maximal extensibility**. Pi "ships with powerful defaults but skips features like sub-agents and plan mode. Ask Pi to build what you want, or install a package that does it your way." Customization layers, in increasing power: themes → prompt templates (`~/.pi/agent/prompts/*.md` become `/name` commands, shell-like arg substitution) → skills (Agent Skills spec `SKILL.md`, advertised by name+description, full body loaded on demand) → extensions (in-process TypeScript modules: tools, commands, shortcuts/flags, providers, MCP servers, virtual-model routers, event handlers, renderers, terminal UI) → pi packages (npm/git/local bundles of the above with dependency installation, discoverable via a package gallery).

Session model: persistent JSONL entries forming a **tree**. Returning to an earlier entry does not erase the branch left behind; `/tree` moves within the file, `/fork` and `/clone` split work into new files; leaving a branch can attach an auto-summary. Compaction inserts a summary entry (structured format, cumulative file-operation tracking) that replaces old messages in future requests while originals stay in the tree. Interfaces (interactive, print, JSON, RPC, SDK) all ride the same agent/session mechanism. RPC is strict JSONL over stdio with id-correlated responses, backpressure discipline, and an extension-UI forwarding channel; the SDK (`createAgentSession`) embeds the agent in-process in Node/Bun.

Trust and safety: project trust (`~/.pi/agent/trust.json`, `defaultProjectTrust: ask`) gates loading of `.pi/` settings/extensions/skills/prompts/themes/MCP/system-prompt — but pi is forthright that this is **not a security boundary**. There is deliberately **no built-in permission system**; tools run with the user's OS permissions. Isolation is documented as three container patterns (plain Docker, managed Docker sandboxes with host-held credential proxying, OpenShell policy sandbox) plus the Gondolin extension (host `pi`, tools + `!` commands routed into a micro-VM). Supply-chain posture is hardened explicitly: exact-pinned direct deps, lockfile as ground truth, pre-commit lockfile guard, install-lock for the installer path, `--ignore-scripts` installs, lifecycle-script allowlist, scheduled audit workflows.

## 2. Pi vs sase: the one-paragraph version

Pi and sase operate at **different layers and would compose rather than compete**: pi is a *do-the-work* agent harness (one session, one model, tools, context), while sase is a *coordinate-the-work* engineering layer (many agents, isolated workspaces, reviewable PR-sized Patches, beads/goals/artifacts, scheduler, keyboard-driven supervisory TUI) that deliberately does not implement its own model loop and instead drives third-party CLIs (Claude Code, Codex, OpenCode, Qwen, Grok Build, Antigravity, Muse). A sase user and a pi user want opposite defaults: the pi user wants the harness to get out of the way and be forked into their own shape; the sase user wants opinionated durable structure (workspace-per-agent, tracked runs, repeatable macros/workflows) wrapped around agents they already pay for. The honest comparison is therefore "pi's session vs sase's run", "pi's skills/extensions vs sase's macros/memory/workflows", "pi's providers vs sase's provider CLIs", "pi's trust vs sase's workspace isolation".

## 3. Detailed comparison

### 3.1 Layer and scope

- **Pi owns the model loop.** System prompt assembly, provider streaming, tool-call execution, turn scheduling, steering/follow-up queues, compaction, session persistence. Sase owns everything *around* model loops: launch, workspace claim, admission/queue budget, monitoring, diffs/chats/artifacts, Patch lifecycle, beads, goals, ToolRuns, scheduler/AXE, gates.
- **Consequence:** sase's hardest problems (multi-agent fan-out, review pipeline, durable cross-transcript state) are ones pi explicitly declines ("skips sub-agents and plan mode"). Pi's hardest problems (provider breadth, prompt-cache economics, context engineering, TUI latency) are ones sase inherits from whichever CLI it shells out to and cannot fix directly.
- **Overlap zone:** sessions/runs, context/memory, prompt reuse (skills+templates vs macros), extensibility (extensions vs plugins/macros/workflows), TUI, MCP, model selection, trust/isolation, telemetry/cost accounting, distribution (pi packages vs sase plugins/sidecars).

### 3.2 Agent execution and parallelism

- Pi: one agent per process. Parallelism is left to the user (multiple terminals, or OpenClaw-style embedding via RPC/SDK). The experimental `pi-durable` adds child tasks/task graphs *within* one harness, and `codemode` fans tool calls out without extra LLM context — but there is no fleet, no queue budget, no cross-session review queue.
- Sase: parallelism is the product. Numbered workspace clones, `%wait`/`%queue` admission, `max_running_agents`, swarm/repeat/alternative directives, single-prompt multi-model fan-out (Claude + Codex + Antigravity from one prompt), per-agent diffs/chats/artifact files, kill controls, retry chains. Nothing in pi resembles this; it is sase's durable moat.

### 3.3 Providers and model access

- Pi talks to providers directly (first-party API clients, OAuth + `/login`, env keys, `models.json` for compatible endpoints, llama.cpp router for local GGUF, provider extensions for anything custom, virtual-model routers, generated catalog with offline cache + `pi update --models`). Thinking levels (`off…max`) with per-model budgets, model cycling (`Ctrl+P`, scoped patterns), prompt-cache warming with a $0.05-savings gate.
- Sase talks to provider *CLIs*, not APIs: it needs at least one installed+authenticated CLI (Claude/Codex/OpenCode/Qwen/Grok/Antigravity/Muse) and routes `%model` directives across them, with usage-limit auto-disable (Claude 1 week, Grok 48h), doctor readiness checks, and instruction-bundle shadow manifests (E2: sase renders the bundle and exports `SASE_INSTRUCTIONS_FILE`, but current CLIs do not read it — delivery unverified).
- Trade-off: pi controls the request and therefore the economics (caching, compaction thresholds, thinking budgets) and works offline with local models; sase works with whatever account the user already holds and survives provider UI churn, but pays per-CLI overhead, cannot tune the context window, and cannot prove its instructions were loaded.

### 3.4 Sessions, branching, and context

- Pi's session tree is the best-designed artifact in the comparison: tree-preserving navigation, fork/clone semantics with a clear "stay together vs split" table, branch summaries on abandon, compaction with `reserveTokens`/`keepRecentTokens`/per-model overrides, branch-summary settings, extension hooks (`cache_warming_decision`), footer context meter, `/session` cost/token accounting. Session files are grouped by working directory, renameable, exportable (HTML/JSONL), shareable (Radius artifact or private gist), importable.
- Sase's equivalents are spread across runs, chats, ToolRuns, artifacts, Patches, and beads — durable and reviewable, but there is no single navigable tree per unit of work and no first-class "try the alternative without losing this branch" operation inside a run. Sase's strength (cross-transcript durability) is also its gap (within-run branch ergonomics).

### 3.5 Reuse: skills/templates/extensions vs macros/memory/workflows

- Pi's ladder (template → skill → extension → package) is cleanly separated by capability: text reuse vs on-demand instructions+bundled scripts vs executable integration vs distributable bundle. Skills follow the Agent Skills spec, so the ecosystem is portable. Extensions get a typed `ExtensionAPI` with ~15 integration points and a documented lifecycle (`session_start`/`session_shutdown`, `before_agent_start` → `agent_before_settle` actionable boundary → `agent_settled` notify-only), plus UI primitives (`select`/`confirm`/`input`/`editor`, `notify`, widgets, custom overlays, renderers).
- Sase's macros (Jinja2, typed inputs, `#name`/`#!name`, iterative expansion, directive extraction, project tags) + memory (core always-loaded vs reference on-demand, audited reads, TUI-backed edits, webs/strands) + YAML workflows (agent/bash/python/parallel/loop/human-checkpoint) + gates + plugins cover the same ground with more machinery and more durability, but a steeper authoring curve and no cross-harness spec compliance.

### 3.6 TUI and interfaces

- Pi's TUI is a *library* (`@earendil-works/pi-tui`, reusable outside pi) with differential rendering, synchronized output, IME-correct editor, theming (including a `system` theme that samples the terminal's ANSI palette and guarantees 4.5:1 body contrast, auto-switching on light/dark change), regular/fullscreen modes, scroll/copy/wheel semantics. Headless story is equally strong: print (pipe-friendly), JSON event stream, RPC subprocess protocol, in-process SDK, `pi --export`, CLI-integration guide for choosing among them.
- Sase's TUI is an *operations console*: Patches pipeline, Agents observability (live status, retry chains, diffs, chats, artifacts), Launch Control, scheduler/service views. Its job is supervision of many runs, not editing one transcript. Both are keyboard-driven; they solve different supervisory problems and could plausibly embed each other (pi transcript widget inside sase's agent view; sase run controls inside a pi extension).

### 3.7 Trust, isolation, and safety

- Pi: trust gates *configuration loading*, isolation is the user's job (documented container patterns), no permission prompts by design. Honest docs ("watching the transcript does not create a security boundary").
- Sase: isolation is structural (workspace-per-agent clones; a run cannot stomp a sibling's files), holds/admission gate execution, service-host + scheduler own background work, gates put humans back in the loop. Pi's AGENTS.md multi-session git rules (explicit-path staging, never `add -A`/`reset --hard`/`clean -fd`) read like a manual version of what sase's workspace claims enforce automatically.
- Net: sase is safer by construction for parallel-agent work; pi is lighter for single-session work and pushes sandboxing to the deployment layer.

### 3.8 Distribution and supply chain

- Pi packages (`pi install npm:|git:|local`, pinned versions, `pi list/remove/update`, gallery with `pi-package` keyword, per-invocation `-e` trial) are a smoother install story than sase's plugins/sidecars, and the supply-chain docs (pinned direct deps, install-lock, lifecycle-script allowlist, `--ignore-scripts` everywhere, audit CI) are more explicit than sase's.
- Sase's distribution unit is heavier (full workspace clone + linked repos + Rust core pin) because its guarantee is heavier (repeatable tracked work, not just a config bundle).

### 3.9 Telemetry, cost, and evals

- Pi: vendor-neutral telemetry contracts with no backend lock-in, conformance tests, per-session token/cost in `/session`, cache-miss/warming notices, prompt-cache economics gate, `evals` package. Cost visibility is per-session and immediate.
- Sase: ToolRuns with output/diagnostics, instruction-bundle manifests, `sase instructions verify` (reads providers' own session records), usage-limit auto-disable. Cost visibility is per-run/fleet and operational rather than per-token. Neither has a decisive lead; pi's is finer-grained, sase's is fleet-aware.

### 3.10 What sase has that pi lacks (do not regress)

Parallel workspaces, Patch review lifecycle with stitches/hooks/comments/mentors, beads/epics with dependency tracking, goals, ToolRun ledger, scheduler/AXE background orchestration, gates/human checkpoints, multi-CLI fan-out with routing policy, instruction bundles + memory webs with audited reads, workspace-claim concurrency safety, fleet-level usage-limit handling. None of these exist in pi, and pi's philosophy says most never will.

### 3.11 What pi has that sase lacks (opportunity list input)

Direct provider control with local-model support; session-tree branching; on-demand skill loading by description; one-command package install from npm/git; terminal-adaptive theming; RPC/JSON/SDK embedding story; codemode-style context-free tool fan-out; explicit compaction/branch-summary controls with per-model overrides; session export/share; `system`-style TUI library reuse; supply-chain hardening docs; multi-session git discipline codified in contributor rules.

## 4. How sase can learn from pi

1. **Treat pi as a compatible engine, not a rival.** The architectures compose: sase could add a pi provider that shells to `pi --mode json/rpc` the way it shells to Claude/Codex today. That gives sase users direct-model routing, local-model/offline runs, and per-token cost data without abandoning the fleet layer.
2. **Steal the extensibility ladder's clarity.** Pi's template→skill→extension→package separation (text vs instructions+scripts vs executable vs distributable) is easier to teach than sase's macros/memory/workflows/plugins matrix. Sase does not need fewer mechanisms; it needs that one-page "which tool for which job" table and skill-spec-compatible import.
3. **Steal the session tree.** Branch-preserving navigation with fork/clone semantics and abandon-summaries is the single biggest UX gap in sase runs. Even a read-only branch view plus "retry from here without losing this branch" would change how sase users explore.
4. **Steal context economics.** Per-model compaction overrides, thinking budgets, cache-warming gates, and footer-style context meters are things sase cannot do through third-party CLIs — which is itself the argument for a direct-provider lane (see 1).
5. **Steal distribution ergonomics.** `pi install` + pinned refs + per-invocation trial (`-e`) + gallery discoverability is the bar sase plugins should meet. A sase user should be able to try a macro pack without cloning a workspace.
6. **Steal embeddability.** Pi's RPC/JSON/SDK tiers answer "how do I drive this from my editor/phone/CI" with one page each. Sase's mobile gateway and editor bridges would benefit from a pi-style protocol-first treatment (framing, backpressure, id correlation spelled out).
7. **Adopt pi's supply-chain explicitness.** Pinned deps as reviewed code, lockfile-change guards, lifecycle-script allowlists, `--ignore-scripts` installs — most of this transfers directly to sase's Python/npm surface.
8. **Do not copy pi's minimalism.** No permission system, no fleet, no review pipeline, no durable cross-transcript state — those absences are pi's product decision and sase's reason to exist.

## 5. Ranked improvements to sase (for a pi user)

Ranked by appeal-to-a-pi-user × fit-with-sase-architecture. Earlier items win over later ones on that product, not on effort.

1. **Add a pi execution lane (`pi --mode json` provider).** Let sase launch `pi` as one more agent CLI: direct-model access, local Ollama/llama.cpp offline runs, skill/extension reuse inside sase workspaces, per-token cost attribution. This is the single move that turns "sase vs pi" into "sase runs pi", and it removes the biggest pi-user objection (abandoning their tuned `~/.pi` setup and provider logins).
2. **Session-tree branching inside runs.** Tree-preserving navigation, `/tree`-like movement, fork/clone of a run's transcript, auto-summary of abandoned branches, export/share (HTML/JSONL/upload link). Pi users will feel the absence of this on day one; it is also the most demoable sase-side improvement.
3. **Skill-spec-compatible macro packs with one-command install.** Accept `SKILL.md`-shaped skills as macro sources; add `sase macro install npm:|git:|local` with pinned refs and a no-persist trial flag (pi's `-e`). Publish a small gallery. Lowers the "try sase for one task" cost for pi users to near zero.
4. **Per-run context dashboard.** Live context meter, compaction-equivalent policy surfaced per provider CLI where knowable (or estimated where not), token/cost totals on every run view, cache/retry accounting. Pi users expect cost to be visible *during* the run, not reconstructed after.
5. **Context-free tool fan-out (codemode analogue).** A workflow step type that lets the model emit a script calling declared tools, with only the script's output/return re-entering context. Directly reduces token spend on mechanical multi-file work and is implementable without touching provider CLIs (run it as a sase-side step).
6. **Terminal-adaptive theming + TUI library hygiene.** Sample the terminal palette for a `system`-equivalent theme with contrast floors; document sase's TUI components for extension reuse the way pi documents `ctx.ui` + its component set. Cheap, visible, pi users notice theming in the first 30 seconds.
7. **Protocol-first embedding docs (RPC-style contract for sase runs).** One page each for driving sase from an editor, from a phone (mobile gateway), and from CI: framing, backpressure, id correlation, event catalog. Pi's rpc.md/json.md/cli-integration.md trio is the template.
8. **Supply-chain hardening pass.** Exact-pinned direct deps, lockfile-change CI guard, lifecycle-script allowlist, `--ignore-scripts` install paths, scheduled audit — modeled explicitly on pi's documented posture. Matters disproportionately to the self-hosting pi demographic.
9. **Project-trust prompt for foreign workspaces.** Before a sase agent loads a workspace's macros/memory/workflows from an unfamiliar repo, show pi-style trust (ask/always/never, saved per directory, CLI override, non-interactive default). Sase's workspace isolation already exceeds pi's safety; this adds the *legible* part pi users recognize.
10. **Multi-session git discipline in generated instructions.** Codify pi's AGENTS.md git rules (explicit-path staging only, never `add -A`/`reset --hard`/`clean -fd`/`stash`, conflict-ownership on rebase) into sase's workspace agent instructions. Near-free, prevents the exact cross-agent stomping pi documents and sase's parallelism invites.
11. **Local-model/offline lane as a consequence of (1).** Ollama/LM Studio/vLLM-compatible endpoints plus llama.cpp-style GGUF routing for air-gapped or cost-free runs, with catalog caching for offline use. Ranked below its parent because it falls out of the pi lane rather than needing its own project.
12. **Session export/share parity.** HTML/JSONL export of any run and upload-to-link sharing with a pre-share secrets reminder. Small, but pi users cite `/export`/`/share` as workflow glue (pasting into issues, archiving to Hugging Face datasets).

## 6. Notes and limits

- Pi is under active development (HEAD `96abe9a5a`, 2026-10-11; `pi-durable`, `chord`, virtual models, and Cloudflare codemode paths are marked experimental). Version numbers observed: workspace packages at `1.1.0`, coding-agent CLI `1.1.0`.
- Sase side read from the local checkout only (see §1 method); no live sase-vs-pi benchmark was run — the comparison is architectural and UX-based, not token-spend measured.
- Author identity: pi's packages credit Mario Zechner (badlogicgames); the repo requires Node 22.19+, ships install scripts plus Nix/NPM paths, and points real-world RPC/SDK integration at OpenClaw and `pi-chat` as reference consumers.
