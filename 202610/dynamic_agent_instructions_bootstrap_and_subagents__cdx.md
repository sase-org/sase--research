# Dynamic agent instructions: fresh-clone bootstrap and native subagent delivery

Independent research by **cdx** · 2026-10-05

## Decision to make

Adopt the previous report's per-invocation memory compiler and adapter delivery design, with two additions:

1. **Make a small, committed bootstrap mandatory in public repositories.** It tells a raw CLI how to obtain current instructions, supplies useful fallback orientation, and works before SASE is installed. Prefer rendering instructions to stdout and reading that result over generating a missing `CLAUDE.md` during an already-running session.
2. **Treat provider-native helpers as a separate instruction audience and lifecycle.** Deliver the same project and memory rules, but give completion responsibility only to the SASE invocation's root. Verify fresh helpers and history forks separately; never assume that the root's prompt channel reaches both.

The prior design is sound. Its optional public stub and brief Claude-only subagent paragraph are insufficient as the complete answer to these two concerns.

## Scope, evidence, and limits

I read the supplied [consolidated baseline](sase_md_instruction_delivery/sase_md_instruction_delivery.md) through `sase artifact read research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`. I did not read or seek the other reports in the current swarm or their transcripts.

Repository findings below were checked against SASE commit `b6114d4f954f4ed990511254e7e46e6160513fc0`. Codex inheritance findings were checked against the source tag matching the installed CLI, `rust-v0.160.0`, commit `a956835d020762cb2b570053af06f643a11c0ecc`, after opening upstream through `sase repo open gh:openai/codex`. Other provider evidence comes from current official documentation, installed CLI help, and Grok's installed vendor documentation. No model runs, paid API calls, configuration changes, or implementation changes were performed.

**Evidence levels:** source-verified behavior is stronger than a documented interface; neither substitutes for an actual model-context integration test. Where helper inheritance is unestablished, this report says so rather than promising compatibility. Gemini CLI is not currently a registered production SASE provider: the registry has **Antigravity (`agy`)**, Claude, Codex, Grok, Muse, OpenCode, and Qwen, plus the test provider Fakey. Gemini documentation must not be used as proof of Antigravity behavior. See [the registry](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/pyproject.toml#L208).

## Preserve the accepted architecture

Keep memory notes as the authored content, with core/reference/web behavior and audited reference reads. Keep `SASE.md`, if used, as an optional composition specification. Render after the execution provider is resolved, freeze the result, and deliver it through the adapter. Keep launch facts closed and host supplied; no new `%tag` mechanism is needed for this work.

There is already a natural implementation seam: `_invoke.py` resolves the execution provider and calls `provider.invoke` at line 436. Recovery paths also invoke providers directly, so a hook attached only to the initial launch would miss them. See [invocation](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/llm_provider/_invoke.py#L338), [declaration recovery](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/finalizers/declaration_recovery.py#L83), and [commit repair](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/finalizers/commit_repair_conflict.py#L409).

The current snapshot implementation reads instruction files from disk. It does not establish which text a provider or helper received. Retain that evidence as discovery evidence, but add compiled and observed context evidence. See [capture_instruction_snapshot](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/axe/launch_evidence.py#L166).

## Issue 1: useful instructions immediately after a fresh clone

### Why “generate the file if missing” cannot be the only mechanism

An absent instruction file cannot tell an agent to create itself. A README instruction helps humans, but it does not make every raw CLI load the README before work. Something discoverable must ship in the clone.

There is also a timing problem: generating a file after the provider started is not equivalent to supplying it before startup. Codex's official guide describes instruction discovery at launch, with root-to-cwd precedence and a default 32 KiB limit. A newly generated file must be read explicitly in the current session or picked up in a new session; writing it alone does not provide a portable reload contract. [OpenAI AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

A command guarded only by file existence also perpetuates stale files. Freshness depends on memory content, compiler/schema versions, audience, provider, and selected configuration—not whether `CLAUDE.md` happens to exist.

### Recommended bootstrap layout

Commit a small `AGENTS.md` containing a **bootstrap protocol**, rather than another full compiled instruction projection. It should explain:

- This is the SASE repository; `README.md`, `CONTRIBUTING.md`, and `docs/rust_backend.md` provide orientation and installation guidance.
- If a SASE launch bundle has already been supplied, use it and skip interactive bootstrapping.
- Otherwise, obtain the interactive project instructions before substantive work and read the returned Markdown as repository guidance.
- If the renderer is unavailable, use the contribution/setup docs to resolve the prerequisite; do not silently assume full SASE instructions were delivered.
- Native helpers report results to their parent; they do not finalize the enclosing SASE run.

Keep the stub short and stable. Put the actual evolving conventions and reference-read triggers in memory. Check the bootstrap against the source it points to so it cannot drift into obsolete command advice.

Also commit **`CLAUDE.md` containing `@AGENTS.md`**. This tiny import handles Claude installations with a personal ancestor `CLAUDE.md`, older versions, and disabled AGENTS support. Current Claude documentation explicitly supports this import and describes deduplication when both names are eligible. Its default AGENTS fallback can be suppressed by an ancestor Claude instruction file, so shipping only `AGENTS.md` is weaker than it first appears. [Claude memory documentation](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).

For other providers, ship only the small entry point actually needed by their verified discovery behavior. OpenCode uses `AGENTS.md` and offers Claude compatibility as a fallback; a full `OPENCODE.md` adds no value. Antigravity and Qwen entry points should route to the same bootstrap, with provider-specific import behavior tested instead of assumed. Grok's installed `12-project-rules.md` says it requires project trust and reads all recognized names, including both `CLAUDE.md` and `AGENTS.md`. Therefore the bootstrap must be idempotent if encountered twice, and raw untrusted Grok should receive a visible README setup path. Do not grant trust merely to make SASE-managed launches load a bootstrap.

**This is an explicit clarification of the baseline's “no SASE-owned native file” invariant:** no full SASE memory projection loads natively in managed runs. A tiny committed bootstrap may be discovered, but it must short-circuit when the compiled bundle is present. Its existence is not a duplicate copy of the memory contract. Audit bootstrap discovery and compiled section delivery separately.

### What command the bootstrap should request

The examples below are **proposed interfaces**, not commands implemented by this research:

```bash
# Installed SASE; stdout is the Markdown instruction bundle.
sase instructions render --mode interactive --scope project

# SASE contributors: use the checked-out source and its locked dependencies.
uv run --frozen sase instructions render --mode interactive --scope project
```

Specify the provider in the small provider-specific entry point when needed, or render a provider-neutral interactive core with a separately validated adapter overlay. Do not guess the provider from the task's wording.

The essential behavior is **render and read**. Do not run `sase memory init` as the raw-session bootstrap: it is a mutation-oriented initializer with broader effects than obtaining current instructions. Do not require project registration, configured home identity, sidecar clones, service startup, or finalizer state just to render the project instructions. The render operation should work from an ordinary, unregistered Git checkout.

The user's suggested `uvx run sase` mixes two uv interfaces. For an isolated published tool, use `uvx sase ...`, equivalently `uv tool run sase ...`; for this checked-out development project, use `uv run sase ...`. A published-tool fallback must require a version supporting the instruction schema, rather than quietly choosing an old cached release. [uv tools guide](https://docs.astral.sh/uv/guides/tools/).

The checkout currently requires Python 3.12+ and a `sase-core-rs` dependency. A missing or incompatible Rust wheel is a real setup failure, not a reason to add a Python renderer fallback. The existing setup docs provide the remedy. See [dependencies](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/pyproject.toml#L10), [contribution setup](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/CONTRIBUTING.md#L5), and [required extension](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/docs/rust_backend.md#L778).

### Offer deterministic interactive delivery as the preferred path

The bootstrap makes a literal `git clone` followed by `claude` useful. It is still a model-mediated bootstrap; it cannot guarantee execution under every tool restriction or custom provider setting.

For users wanting guaranteed preparation before the first model request, provide an interactive launcher using the same compiler and delivery hooks as managed launches. Extend `sase tmux-agent` accordingly and offer a direct foreground launch surface, rather than making tmux mandatory. The interface name can be chosen during CLI design; the important contract is:

1. Resolve checkout, provider, and `mode: interactive` without creating a SASE agent turn.
2. Compile project guidance, plus explicitly selected user preferences.
3. Install the provider's root and helper delivery plan before executing the interactive CLI.
4. Preserve normal interactive permissions and provider behavior.

The interactive audience must omit turn-bound SASE final declarations, host-owned commit assumptions, and mechanical handoff instructions. Installation of SASE or presence of SASE environment variables does not itself mean that a raw interactive session owns a SASE turn.

An optional `sase instructions sync` can still materialize local files for tools that need them. It should write a separate managed cache/import target, rather than replace a tracked bootstrap in the developer's working tree. Avoid placing a full `AGENTS.override.md` in checkouts reused for SASE launches: Codex would discover it again. Freshness, no-overwrite behavior for user files, and cleanup must be explicit.

### Hooks are optional integration, not the public bootstrap

Claude's `SessionStart` and `SubagentStart` hooks can inject additional context; `SubagentStart` receives child identity/type and can add context before the child's first task. It cannot block child creation. Hooks can improve direct interactive use, but they require working dependencies and enabled/trusted configuration. Do not treat a hook as proof that every raw CLI receives instructions. [Claude hooks reference](https://code.claude.com/docs/en/hooks#subagentstart).

For v1, use the committed bootstrap as the portable fallback and the interactive launcher as the deterministic route. Add an opt-in hook integration only if it uses the same renderer, freezes a session bundle, suppresses duplicate native loads, and has its own conformance test.

## Issue 2: equivalent or improved instructions for provider-native subagents

### Distinguish three execution identities

| Execution | Project and memory rules | Completion responsibility | Snapshot policy |
| --- | --- | --- | --- |
| SASE-managed root invocation | Full selected bundle | Own SASE declaration and authorized handoffs | New render at invocation/provider selection |
| Another agent launched through SASE | Its own full selected bundle | Its own SASE declaration | New render for that separate invocation |
| Provider-native helper or history fork | Same applicable project/memory core, specialized role and helper lifecycle | Return work and evidence to parent | Inherit the parent's frozen instruction inputs; adapt role/scope without taking a new live memory snapshot |

A provider's native helper is not a new SASE-managed turn merely because it shares the root's cwd or environment. It has no independent workspace claim or finalizer contract. Read the project decisions `host-owned-completion`, `adapters-normalize-harnesses`, and `rust-core-required` through the audited memory interface when implementing this change.

**Equivalent does not mean byte-identical.** A helper should preserve repository rules, memory-read requirements, path triggers, and authorized task constraints. It should replace root lifecycle obligations with a handback contract. Copying today's unconditional `/sase_final` rule to a helper reproduces a bug.

### Structure the instruction compiler around shared rules and lifecycle overlays

Use independent facts rather than making one overloaded `role` field stand for everything:

```yaml
mode: sase | interactive
actor: root | native-helper
context: fresh | full-fork | partial-fork
purpose: general | research | review | implementation
completion_owner: sase-root | human-session | parent
```

These are conceptual values, to be folded into the existing closed fact schema rather than added as a second directive parser. The host/adapter establishes actor and ownership; project content cannot opt a helper into owning the parent's finalizer.

Compile a **lifecycle-neutral shared core** and separate root/helper overlays. Include the root-only finalization block in a root-specific transport channel. For a fresh helper, deliver the core plus helper overlay. If a provider already supplies the core through an inherited global instruction file, deliver only the missing helper overlay.

A helper's lifecycle should say that it must return findings, changed paths, verification results, and blockers to its parent; it must not submit the parent's final declaration, commit, or start a SASE handoff that terminates the parent. Long work or a missing approval becomes a parent decision. The root waits for its helpers and collects their evidence before declaring completion.

For full forks that necessarily inherit the root's instructions, make every root lifecycle instruction actor-qualified. Include explicit helper identity in the provider's child channel or delegation message. Do not attempt to “subtract” inherited system instructions with a lower-priority user sentence.

A finalization backstop should bind privileged lifecycle operations to the actual root execution identity using provider/host evidence. A shared `SASE_*` environment variable is inadequate evidence: children may inherit it. This is a focused completion-ownership safeguard, not a new general permission framework.

### Provider findings and recommended delivery

| Provider | Established behavior or interface | Recommended implementation | Confidence / remaining work |
| --- | --- | --- | --- |
| **Claude** | Fresh helpers use their own system prompt; most receive the Claude instruction hierarchy, while Explore and Plan skip it. A dedicated append flag covers fresh/nested helpers. Forks reuse the parent prompt. | Append the full neutral core plus helper overlay through the subagent file flag when managed native discovery is suppressed. Root gets its own append file. Handle forks with actor-qualified root rules and verified child identity. | Documented interfaces; test installed-version prompts, exclusions, forks, compaction, and helpers without Bash. |
| **Codex** | 0.160.0 source shows parent-derived configuration, role overrides, and a multi-agent v2 developer-instruction override for helpers, including fork-history rewriting. | Keep the neutral core in the run's shadow Codex home. Put root lifecycle in root developer instructions; supply helper lifecycle via the v2 child override. Preserve and adapt custom-role instructions. | Source verified at installed release; feature/version sensitive and not established by the public guide. Requires v1/v2 and fork conformance tests. |
| **Grok** | Installed docs describe fresh child sessions, CLI agent definitions, personas, and spawn-time persona instruction files. They do not establish inheritance of root `--rules`. | Use a tested child definition/persona overlay or child-start hook when it covers every enabled helper type. Until then, provide a delegation bootstrap and keep unsupported helper paths outside the guaranteed mode. | Root `--rules` is established; child propagation remains unverified. An optional persona is not a universal child policy. |
| **Muse** | Installed help exposes ephemeral `--agents` definitions; the SASE adapter currently prefixes root instructions. No consulted evidence establishes that this prefix reaches fresh children. | Prove a child overlay through the supported definition/session interface; retain native helper defaults. Otherwise route guaranteed delegation through SASE-managed launches. | Child instruction schema and inheritance need a focused probe. Do not advertise root-prefix delivery as a helper guarantee. |
| **Antigravity (`agy`)** | Official docs distinguish custom fresh agents and `self`, which shares the caller's system instructions. Markdown bodies define custom system prompts. | Use a tested custom-agent or invocation hook overlay, retaining existing role prompts. Test `self` and fresh research agents separately; do not rely on a root user-prefix for fresh children. | Documented authoring surface; installed print-mode propagation unverified. |
| **Qwen** | Named helpers have configured prompts and fresh histories; forks reuse the exact parent system prompt. It can also delegate to external Claude/Codex runtimes. | Adapt supported named definitions and give forks explicit helper identity. External-executor helpers need that executor's delivery plan, not just Qwen's root instructions. | Documented distinctions; root append behavior is not evidence of fresh helper delivery. |
| **OpenCode** | Global/project rule files and configured `instructions` coexist with per-agent prompts. | Use run-local configuration for shared rules and helper role prompts, retaining original role content and permissions. Verify built-in and custom helper assembly. | Configuration documented; universal child-rule inheritance not proven in this research. |

Sources for the table: [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Qwen subagents](https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/), [Antigravity subagents](https://www.antigravity.google/docs/subagents/), [OpenCode agents](https://opencode.ai/docs/agents/), and [OpenCode rules](https://opencode.ai/docs/rules/). Grok evidence is its installed vendor guide `~/.grok/docs/user-guide/16-subagents.md`; Muse evidence is installed `muse --help` / `muse exec --help` and [the SASE Muse adapter](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/llm_provider/muse_provider.py#L309).

### Claude: a concrete implementation path

For managed `-p` runs, compose two files outside the checkout:

```text
root.md       = neutral core + root lifecycle
helpers.md    = neutral core + helper lifecycle
```

Then deliver them using:

```bash
claude -p \
  --append-system-prompt-file /run-artifacts/root.md \
  --append-subagent-system-prompt-file /run-artifacts/helpers.md \
  ...
```

The helper file flag requires Claude Code 2.1.261+. The dedicated helper flags apply to non-interactive runs and exclude forks. Do not assume they also solve interactive-launcher helpers. For interactive sessions, a verified `SubagentStart` integration or adapted custom definitions provides fresh-child delivery. [Claude CLI reference](https://code.claude.com/docs/en/cli-reference).

Keep existing provider system prompts and tool guidance. A compiler should append the common contract or adapt a custom definition while retaining its original role text, rather than replace every built-in specialist with a generic SASE agent. Disabled native SASE files must stay disabled in the child as well; test this explicitly.

### Codex: a stronger solution than “children probably inherit AGENTS.md”

The installed-release source establishes these specific behaviors:

- `build_agent_shared_config` clones effective parent settings and copies developer instructions.
- In multi-agent v2 it applies `subagent_developer_instructions` before role overrides.
- A role's `developer_instructions` can replace those inherited instructions.
- Fork construction rewrites the parent's developer-instruction fragment when a child override or applicable role is configured.

See [child configuration](https://github.com/openai/codex/blob/a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/core/src/agent/child_config.rs#L132), [role overrides](https://github.com/openai/codex/blob/a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/core/src/agent/role.rs), [fork construction](https://github.com/openai/codex/blob/a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/core/src/agent/control/spawn.rs#L951), and [feature configuration schema](https://github.com/openai/codex/blob/a956835d020762cb2b570053af06f643a11c0ecc/codex-rs/features/src/feature_configs.rs#L282).

The corresponding version-specific configuration path is `features.multi_agent_v2.subagent_developer_instructions`. Use it only when the selected runtime/model supports v2; do not enable a new multi-agent mode as a side effect of rendering instructions. A capability check must distinguish v1, v2, and disabled delegation.

Preserve the existing disposable shadow home. Replace only SASE-owned global projection content with the neutral core; preserve the declared policy for user-owned Codex instructions. Its existing symlink fallback and copied config are in [the SASE Codex adapter](https://github.com/sase-org/sase/blob/b6114d4f954f4ed990511254e7e46e6160513fc0/src/sase/llm_provider/codex.py#L207).

Custom roles need special care because their developer instructions can override the helper default. Adapt selected role content in the run-local config, or establish a child-start hook that covers those roles. Do not claim that setting one default proves every custom child receives the helper lifecycle. For older/v1 paths, use a demonstrated role/hook route or the explicit unsupported-path policy below.

### Define the fallback honestly

Adapters should declare root and helper capabilities separately, including fresh, forked, custom-role, resumed, and isolated-workspace cases. “Has a prompt prefix” is only a root capability.

If an adapter cannot prove delivery to an enabled helper path:

- In **best-effort interactive use**, the bootstrap tells the parent to include a helper-specific render or a read instruction in each delegation. This depends on the model and the child's tools, so label it best effort.
- In **guaranteed managed use**, mechanically disable that unsupported native helper path where possible and use the existing SASE launch workflow for independently managed agents. If the adapter cannot enforce the limit, refuse to claim conformance and expose the limitation before launch.

This avoids pretending all providers offer the same control surface. It also permits Claude and Codex support to ship before the less observable adapters are solved, without weakening the managed completion contract.

## Lifecycle, freshness, and audit details that decide whether this works

### Freeze the source snapshot, not just the root file

A root and its helpers should use the same project/home/plugin input digests and schema version. A child that starts after the parent edited memory should not silently receive different global rules. Render its actor/role overlay from frozen inputs, not mutable workspace files.

If child cwd, worktree, or actual execution provider changes, resolve those facts explicitly. Path-scoped reference triggers should remain available even when a helper lacks shell access: preload the required note through the host's audited read path or give the child a tool that performs that read. A command-based instruction is ineffective when the required command cannot be executed.

Native helpers should not independently discover the research sidecar or other linked checkout through ad hoc paths. They retain the same audited repo/artifact access obligations as the root. Their capabilities may be narrower, never assumed broader.

### Resumed provider sessions are a distinct delivery boundary

Claude documents recorded system prompts surviving `--resume`/`--continue` until compaction, so changing append text on a later CLI invocation may not change the effective prompt immediately. A render at every subprocess call does not itself ensure fresh effective instructions. [Claude resumed-prompt semantics](https://code.claude.com/docs/en/cli-reference#system-prompt-flags-in-resumed-conversations).

Recommended policy: resume a provider conversation only with its original frozen instruction snapshot; if new SASE instructions are required, start a new conversation or use a separately tested refresh mechanism. Apply the same explicit policy to resumed helpers. Interactive sessions keep their initial snapshot until the user deliberately refreshes it.

A last-known-good fallback must match provider, mode, actor, project, and compatibility requirements. Never give a helper a cached root bundle. Report fallback use and fail if no compatible instruction set exists.

### Strengthen “exactly once” into a measurable contract

Record planned content and observed delivery separately:

```text
invocation id, provider version, actor, parent/native child id
input digests, selected section ids, rendered digest, delivery channels
native files observed, effective root/child context evidence, conformance verdict
```

Check section identity and actual inclusion, not merely a hash string the model could echo. “Once” means once in the effective instruction assembly for a given root/helper request. Provider replay across requests or deliberate reinjection after compaction is normal and should not produce a false duplicate verdict.

If a provider does not expose its assembled prompt, record **unverified**, along with available transport evidence and behavioral smoke results. Do not turn an invisible-context provider into a verified one by inspecting only the bytes SASE wrote.

## Implementation order and acceptance tests

1. **Define audience and completion ownership first.** Factor the common memory contract from root-only lifecycle text. Preserve unconditional reference-read triggers across purposes.
2. **Build the compiler and root delivery seam.** Include direct recovery invocations; keep source digests and provider-version evidence. Put deterministic schema, validation, selector, and ownership decisions in `sase-core`; keep Python Markdown assembly and provider I/O as the thin adapter layer agreed in the baseline.
3. **Ship the public bootstrap and interactive render path together.** Remove full generated projections only once the new bootstrap command is available. Document and test the source-checkout and published-tool routes. Keep a minimal useful fallback when SASE cannot run.
4. **Implement Claude and Codex helpers with their strongest channels.** Add actor-qualified fork behavior and a root-only finalizer backstop. Preserve custom role content, tools, and permissions.
5. **Prove remaining adapters independently.** Until a path passes, use the declared best-effort/guaranteed fallback rather than silently inheriting unknown behavior.
6. **Migrate home/nested files and local sync.** Maintain path-trigger coverage, explicit home-layer selection, and no workspace instruction churn. Apply memory and generated-skill changes through their established workflows.

Acceptance tests should exercise behavior that could fail, rather than mirror the renderer's implementation:

| Scenario | Required result |
| --- | --- |
| Fresh clone, no SASE home/project registration, raw Claude/Codex | Bootstrap discovered; instructions obtained from checkout; no turn-bound finalizer instructions; useful diagnostic if prerequisites are missing |
| Raw Claude with an ancestor `CLAUDE.md` | Committed import still makes the repo bootstrap available |
| Existing stale local projection, memory edited | Fresh invocation uses new compiled inputs; stale native full projection does not duplicate or override them |
| Managed root + fresh helper + full/partial fork | Same applicable core exactly once; helper knows it reports to parent; only root submits the final declaration |
| Claude Explore/Plan and shell-less custom helper | Memory/repo rules arrive despite skipped native hierarchy or unavailable Bash |
| Codex v2 default and custom role; v1 fallback | Correct child lifecycle survives role resolution; unsupported paths are explicitly handled |
| Provider retry, provider fallback, declaration recovery | Correct provider overlay and snapshot used at every actual delivery boundary |
| Helper in isolated worktree or changed cwd | Correct scope triggers and repo access policy; no dependence on a root-only local file path |
| Provider resume and compaction | Declared snapshot policy holds; no accidental root instruction reuse or missing reinjection |
| Two concurrent agents and reused workspace | No shared global-config mutation, overwritten files, or generated tracked changes |
| Child attempts root finalization or handoff | Host/adapter rejects wrong ownership; parent can continue and finalize |
| Provider context unavailable | Verdict says unverified rather than fabricating observed delivery |

Use inexpensive deterministic fixtures for compiler/channel assembly and a small installed-provider smoke suite for inheritance semantics. Provider upgrades should run the latter. Do not make paid full-provider sweeps part of every ordinary code edit.

## Alternatives and tradeoffs

| Option | Assessment |
| --- | --- |
| Delete every discoverable file and tell agents to regenerate if missing | Circular bootstrap; reject |
| Keep committed full compiled instruction files | Useful offline, but recreates churn and unsuppressible duplicate/audience content; reject as default |
| Commit only `AGENTS.md`, relying on all providers to support it | Good starting point, insufficient for current Claude ancestor behavior and provider trust differences |
| Committed bootstrap + render to stdout | Best portable fresh-clone default; depends on the model following a short first-action instruction |
| Interactive launcher + explicit root/helper delivery | Strongest preparation guarantee; requires invoking SASE instead of a literal raw provider command |
| Project hooks as the only bootstrap | Useful opt-in integration; insufficient across providers, disabled hooks, trust, or missing dependencies |
| Copy the full root bundle into every native child | Restores shared rules but also copies invalid completion duties and duplicates inherited sections |
| Disable all native subagents permanently | Enforces a simpler model but sacrifices provider specialists/cache benefits unnecessarily; reserve disabling for unverified paths |

## Recommended solution

**Proceed with per-invocation, memory-backed compilation and explicit adapter delivery. Make the public bootstrap a required part of that migration, and make native-helper delivery a separately tested capability.**

For a new developer running literal `claude`, commit a small `AGENTS.md` bootstrap and a one-line `CLAUDE.md` import. The bootstrap requests a read-only interactive render and consumes its stdout; it does not rely on creating an absent file or automatic mid-session reload. Provide an interactive SASE launcher for deterministic pre-start delivery. Keep full instruction content in memory and avoid modifying tracked bootstrap files during ordinary rendering.

For native subagents, compile shared project/memory rules separately from lifecycle. Claude gets a dedicated fresh-helper append file; Codex v2 gets a helper developer-instruction override, with custom-role handling and version checks. Forks require actor-qualified root rules and verified helper identity. Other adapters must prove their own child channel or use an explicit fallback to SASE-managed delegation. Only the root owns the SASE final declaration and handoffs.

This preserves the baseline's low-churn, exactly-once instruction design while giving fresh clones an entry point and helpers the instructions they actually need to finish their assigned work safely and correctly.
