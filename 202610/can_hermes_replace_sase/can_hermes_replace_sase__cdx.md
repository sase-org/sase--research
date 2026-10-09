# Hermes versus SASE: feature parity, substitution, and a defensible engineering role

Researcher: **cdx**. Assessment date: **2026-10-09**. Independent report for the five-researcher swarm; no peer report or peer findings were consulted.

## Assessment

**The literal claim that Hermes can do everything SASE can is not supported by the current feature sets. The practical claim that most general agent users should start with Hermes is much stronger.** Hermes already covers substantially more of SASE's engineering territory than a comparison of “personal assistant” versus “coding-agent orchestrator” suggests. It has durable multi-agent tasks, dependencies, isolated worktrees, review loops, a swarm topology helper, automation, artifacts, local quality gates, and required-check enforcement for declared GitHub PR tasks.

SASE's remaining case is specific: a coordinated engineering system around several native coding-agent runtimes, with host-owned repository completion, explicit verification evidence, typed provenance, and approved executable plans. Those differences can matter to users other than Bryan. They do not establish that SASE is the best default for ordinary coding, research, or personal automation, and they do not establish a large market merely because the features exist.

A better version of the proposed claim is:

> Hermes already supplies the agent capabilities and durable coordination most people need. Add SASE only when its particular engineering workflow contracts remove a recurring operational problem.

That is my inference from the evidence below, not an empirical measurement of how many users fall into each category.

## Scope and method

“Hermes” means **Nous Research's Hermes Agent**, not the Hermes model family or unrelated projects using that name. This comparison excludes popularity, adoption, stars, community size, and investment. It also excludes speculative performance or price advantages: I did not run matched workload benchmarks or measure onboarding time.

I inspected official documentation and local source checkouts, opened through `sase repo open`:

- SASE: revision `96dd8ed27023e63f107d145b8391fd4cfa86dda2` in the supplied workspace.
- Hermes Agent: revision `1e0c7730d791f5ce855c5c78935cfea6fb1e43a9`, whose latest commit is dated 2026-10-08.

The comparison includes documented shipped options and named integrations, while distinguishing them from defaults. In particular, Hermes Kanban requires setup and suitable profiles; its optional Codex app-server runtime has compatibility limits. SASE's GitHub and Telegram workflows use integrations, and its own README describes the product as alpha. Neither “configurable” nor “documented” proves production reliability. [SASE overview](https://sase.sh/), [Hermes runtime documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime).

Three meanings of “can” must be separated:

1. **Equivalent outcome:** can the product produce a patch, review, scheduled report, or multi-agent result?
2. **Supported workflow:** does the product already supply the relevant lifecycle, ownership, recovery, and evidence handling?
3. **Programmable possibility:** could shell scripts, plugins, MCP, or a new integration recreate it?

Both products are extensible. Counting any behavior a programmer could implement would make almost every comparison meaningless; Hermes could even invoke SASE. Conversely, differing object names are not evidence of a meaningful gap. A Hermes task with dependencies and handoffs can replace many uses of a SASE bead without copying its exact schema.

## Feature comparison

“Overlap” means the user-level capability exists in both; it does not promise identical semantics. “SASE distinction” means an examined supported contract is more specific in SASE, not that Hermes is incapable of implementing it.

| Capability | Hermes Agent, as examined | SASE, as examined | Implication |
|---|---|---|---|
| Coding, research, shell and file work | Agent runtime with built-in terminal/file/web/browser/media tools; additional capabilities through MCP and plugins | Coordinates authenticated coding-agent CLIs and inherits their task abilities | Hermes is already sufficient for most individual tasks; SASE is primarily another layer of coordination |
| Different model providers | Extensive inference-provider registry, custom endpoints and local-model options | Several native coding-agent providers plus model/effort routing | Provider choice is not uniquely SASE's advantage; native harness choice is the relevant distinction |
| Parallel workers | Delegated children, specialist profiles/Bots, and durable Kanban workers | Parallel agents in separately claimed numbered workspace clones | Strong overlap |
| Isolated coding checkouts | Automatic worktree mode and worktree-backed Kanban tasks | Managed workspace clones with lifecycle/ownership rules | Isolation alone does not justify SASE |
| Durable tasks and dependencies | Kanban task/run/event records, dependency gating, review/rework, retries and claims | Beads, executable epic phases, dependency waves and final landing work | Strong overlap; different planning and landing conventions |
| Research swarms | Kanban helper builds parallel workers, verifier, synthesizer, and shared blackboard atomically | Prompt fan-out, named groups, artifact references and downstream workflows | A research swarm is not an exclusive SASE capability |
| Scheduling and event automation | Cron, script-only jobs, webhook triggers, Bot routines | Scheduler/service host, recurring jobs, hooks, mentors and workflow launches | Strong overlap; Hermes has a broader general assistant surface |
| Persistent memory and reusable procedures | Curated memory, session recall, reusable/self-authored skills, profiles and memory-provider integrations | Project/home instruction memory, audited reference reads, webs, published provider instructions and history | Different emphasis: personal continuity versus project instruction/provenance management |
| Reusable execution workflows | Skills/bundles, scripts, hooks, programmatic tool calling, Kanban graphs | Typed macros and a YAML workflow executor mixing agent, shell, Python, branches, loops, parallelism and approval | SASE supplies a more explicit integrated workflow language; Hermes can achieve many of the same outcomes |
| Human review and permission | Command approvals, clarification, Kanban human review, profile configuration and managed scope | Durable command-backed gates and plan approvals, shared across supported decision surfaces | Both support human decisions; SASE's gate/continuation protocol is more specialized |
| Local verification before completion | `/goal gate` executes shell checks before allowing the judge to finish a goal | Named ToolRuns plus prepared host completion bound to an exact verification command | Neither is merely “ask the model if tests passed”; SASE ties evidence to its landing protocol |
| Remote PR acceptance | Explicit Kanban PR contract checks required GitHub evidence at the current PR head | Tracked Patch/commit/PR workflows and review state | Hermes has substantive deterministic PR acceptance; SASE should not be presumed stronger without specifying the policy |
| Repository landing | Agents and configured workflows can commit/publish; Kanban separately governs task completion | Host finalizers consume validated declarations and perform tracked commits/proposals/PR actions for obligated repositories | SASE distinction: one cross-provider completion protocol for repository effects |
| Artifact retention | Durable task attachments, completion metadata, session records and desktop artifacts | Explicit immutable snapshots, canonical artifact identities, audited reads and typed relationship graph | Outcome overlap; SASE supplies a richer examined engineering provenance contract |
| Long commands and continuation | Background terminal/process work, notifications, goal parking, durable Kanban dispatch | Detached monitors, frozen continuation state, explicit outcome handling and prepared no-model host completion | Overlap in waiting and supervision; distinction in integration with host landing |
| Remote execution | SSH/cloud terminal backends and connections to remote Hermes instances/Bots | Enrolled remote agent dispatch and project-oriented fleet controls | Both can operate remotely; Hermes's shared Kanban board is documented as single-host |
| User interfaces and platforms | CLI/TUI, desktop, web dashboard, many messaging adapters; documented native Windows support | Keyboard-oriented engineering TUI/CLI; Linux/macOS only in the examined README | Hermes has the stronger general-access feature set |

Evidence for the table: [Hermes tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools), [provider resolution](https://hermes-agent.nousresearch.com/docs/developer-guide/provider-runtime), [delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation), [worktrees](https://hermes-agent.nousresearch.com/docs/user-guide/git-worktrees), [Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban), [cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron), [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory), [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode), [desktop](https://hermes-agent.nousresearch.com/docs/user-guide/desktop), [managed scope](https://hermes-agent.nousresearch.com/docs/user-guide/managed-scope); [SASE workflows](https://sase.sh/workflow_spec/), [beads](https://sase.sh/beads/), [memory](https://sase.sh/memory/), [commit workflows](https://sase.sh/commit_workflows/), [ToolRuns](https://sase.sh/tool/), [artifact links](https://sase.sh/artifact_links/), [monitors](https://sase.sh/monitors/), [remote dispatch](https://sase.sh/remote_dispatch/).

## The strongest evidence supporting the claim

### 1. Hermes already coordinates durable engineering work

A comparison based only on Hermes's ephemeral `delegate_task` children would materially understate the product. Kanban records task lifecycle outside the conversation, launches separate worker processes, supplies prior handoffs and attempt history, and has explicit completion, blocking, review, and changes-requested operations. Durable collaboration is not something a Hermes user must invent from scratch.

The source's `complete_task` boundary checks dependencies again during the terminal transaction and protects active run ownership. These are real coordination rules rather than just suggested prompt instructions. See the examined [completion implementation](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/hermes_cli/kanban_db.py#L2658).

The shipped swarm helper is particularly relevant to this request: it constructs worker → verifier → synthesizer dependencies and writes a shared blackboard using the existing Kanban kernel. SASE cannot justify itself merely by making multi-model research or dependency-ordered agents possible. [Swarm implementation](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/hermes_cli/kanban_swarm.py).

### 2. Hermes has completion checks stronger than “the agent said done”

Hermes's `/goal gate` runs user-specified shell checks at eligible turn boundaries. A failed check prevents goal completion, supplies actual error output to continuation, and has bounded retries. Source inspection confirmed that `_check_gates` executes the commands rather than accepting a prose assertion. [Goal gate implementation](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/hermes_cli/goals.py#L1301).

For declared PR tasks, Kanban has a separate GitHub acceptance contract. It binds the published PR, reads required contexts/checks, and refuses unsuitable evidence. Acceptance receipt persistence rechecks task/run/contract ownership before the terminal write. This is a serious counterexample to a simplistic “Hermes has tools, SASE has engineering guarantees” argument. [Acceptance collection](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/hermes_cli/kanban_pr_acceptance.py), [receipt persistence](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/hermes_cli/kanban_pr_acceptance_store.py).

These contracts are configured, not universal defaults: ordinary or undeclared Kanban tasks use `local-only`. A completion-time GitHub read also is not a continuous post-completion guarantee. The repository includes tests for failed, missing, stale, changed-head, and reclaimed-run evidence; I inspected those tests but did not execute them. [Acceptance tests](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/tests/hermes_cli/test_kanban_pr_acceptance.py).

### 3. A broad class of users gets more directly useful features from Hermes

Hermes supplies an agent with browser automation, web extraction, media handling, memory, scheduling and multiple interactive surfaces. SASE supplies coordination around another authenticated agent runtime. For someone whose actual work is researching, editing a few files, operating a personal assistant, or running scheduled reports, SASE adds concepts without demonstrating a necessary missing capability. This is an inference about task fit, not a measured usability result. [Hermes tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools), [SASE getting started](https://sase.sh/getting_started/).

Hermes also offers security features relevant to organizational deployment, including sandbox backends, approval policy, and administrator-pinned configuration. There is no basis for treating “professional use” or “enterprise” as an automatic SASE advantage. [Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security), [managed scope](https://hermes-agent.nousresearch.com/docs/user-guide/managed-scope).

## Where literal feature parity breaks down

### 1. Several native coding-agent harnesses under one engineering lifecycle

SASE's supported providers run Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code and Grok Build. Its coordination and finalization happen around those provider invocations. The user's benefit is preserving actual runtime behavior, tooling and supported integration while using common project workflows. This is distinct from switching a Claude, Gemini, or other inference model inside one agent's own loop. [SASE agent providers](https://sase.sh/agent_providers/), [commit finalizer](https://sase.sh/commit_workflows/#commit-finalizer).

Hermes substantially narrows this difference: the optional Codex app-server runtime hands execution to native Codex, and the source also contains a Copilot ACP provider. Therefore it would be inaccurate to call Hermes exclusively a single proprietary tool loop. [Codex runtime](https://hermes-agent.nousresearch.com/docs/user-guide/features/codex-app-server-runtime), [Copilot ACP provider](https://github.com/NousResearch/hermes-agent/blob/1e0c7730d791f5ce855c5c78935cfea6fb1e43a9/plugins/model-providers/copilot-acp/__init__.py).

However, Hermes's own worker-lane documentation says general external CLI lanes still require integration work. Its Codex runtime also omits direct `delegate_task`, `memory`, `session_search`, and `todo` tools, while supporting Kanban and background memory/skill review through other paths. The reviewed feature set does not establish a ready-made equivalent to SASE's full native-provider matrix and uniform finalizer behavior. [Worker-lane boundary](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-worker-lanes).

**Practical importance:** high for an operator deliberately mixing native coding-agent products; low for a user satisfied with Hermes's runtime and model registry. This is an integration advantage that can erode, not a fundamental technical moat.

### 2. Host-owned landing of declared repository work

SASE uses a host-issued final context, a typed declaration covering changed repositories, and host-owned finalizers. Submission rejects stale context; execution treats post-declaration repository mutations as protocol violations. The model supplies intent and messages, while the host performs tracked repository actions.

Its prepared completion path seals a declaration plus an exact verification command and repository observations. Successful eligible verification can lead directly to host completion without another model turn; failures or stale observations lead to recovery. It records completion evidence to avoid repeating proven commits and surfaces ambiguous outcomes. [SASE finalizer protocol](https://sase.sh/commit_workflows/#commit-finalizer), [prepared completion implementation](https://github.com/sase-org/sase/blob/96dd8ed27023e63f107d145b8391fd4cfa86dda2/src/sase/finalizers/_prepare_completion.py).

Hermes's task ownership, local quality gates and PR acceptance protect different boundaries. They are meaningful substitutes for parts of the outcome, but I did not find a documented equivalent of this combined all-obligated-repositories, predeclared host landing protocol. Recreating it through hooks or plugins is plausible; it is additional engineering work, not demonstrated current parity.

**Practical importance:** high when an operator wants consistent completion across repositories and native providers. It should not be oversold as universal safety: ordinary SASE final declarations can be recorded as unverified, and the protocol is not a security boundary against arbitrary code running with the user's filesystem permissions.

### 3. Verification as a durable project evidence domain

SASE's named ToolRuns retain command identity, execution/stage outcomes, before/after fingerprints and failure evidence. Its triage distinguishes NEW, KNOWN, FLAKY and UNKNOWN without rewriting the child exit code. KNOWN requires an independent witness; insufficient evidence remains UNKNOWN. Eligible named-tool receipts can support an explicitly configured `no-new` host completion policy. [SASE ToolRuns and failure triage](https://sase.sh/tool/).

Hermes records tool/session and task events and can run tests deterministically. That does not establish the same reusable project-level failure classification and fingerprint/receipt policy. The comparison is evidence modeling and completion integration, not whether Hermes can execute `pytest`.

This is also SASE's least safe area to overstate. Receipt coverage depends on project configuration, complete observations and expiry; the examined documentation identifies external state omitted from fingerprinting. Thin ledgers yield many UNKNOWN classifications. Receipts do not skip test execution. They are useful scoped evidence, not complete hermetic proofs. [SASE receipt policy](https://github.com/sase-org/sase/blob/96dd8ed27023e63f107d145b8391fd4cfa86dda2/docs/tool.md#fingerprinted-toolchain-and-external-state-e4-hermetic-baseline).

**Practical importance:** meaningful for parallel engineering where test failures and repository changes need attribution. Often unnecessary for a developer satisfied with ordinary CI and a human reviewing the PR.

### 4. A linked, portable engineering record rather than only durable task/chat state

SASE supplies typed artifact identities and relations connecting plans, research, agents, tasks, Patches, stitches and snapshots. Prompt citations and audited reads record consumption. Executable epics preserve approved plans and associate phases with work and commits. That makes questions such as “which evidence informed this change?” directly representable. [Artifact references](https://sase.sh/artifact_references/), [artifact links](https://sase.sh/artifact_links/), [spec-driven development](https://sase.sh/sdd/).

Hermes already preserves attachments, handoffs and task events, and has context references. Therefore “durable artifacts” or “context injection” alone is no differentiation. I did not find an equivalent integrated typed engineering relationship graph in the examined core paths. A graph built through an external memory service or custom plugin could close this gap; it should be evaluated as that additional configured system. [Hermes context references](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-references).

SASE's explicit YAML workflow executor is another concrete distinction: its shell/Python/agent steps, typed outputs and control flow are executed by the workflow system. Hermes's skill bundles group instructions; they are not, by themselves, the same executor. Hermes can compose scripts, hooks and task graphs to produce similar results, so the advantage is packaged structure and shared lifecycle rather than exclusive computational ability. [SASE workflow specification](https://sase.sh/workflow_spec/), [Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [event hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks).

**Practical importance:** strongest for long-lived, repeated engineering pipelines or research-to-implementation work. Low for short, self-contained tasks whose existing issue tracker and repository history are sufficient.

## Similar names and tempting claims that do not prove an advantage

- **Goals mean different things.** Hermes `/goal` is primarily a single-session automatic continuation loop with optional quality checks. SASE's examined goal ledger is a person-owned outcome record with separate identity, history and settlement authority. These can complement rather than replace one another. I did not count future SASE goal features advertised in documentation as implemented. [Hermes goals](https://hermes-agent.nousresearch.com/docs/user-guide/features/goals), [SASE goals](https://sase.sh/goals/).
- **Remote capability is shared.** Hermes can use remote terminal environments and remote Bots. Its Kanban documentation explicitly excludes a shared cross-host board; multi-gateway deployment alone does not remove that limitation. SASE has an enrolled remote-dispatch feature. This supports a narrower difference, not a blanket claim that only SASE works across machines. [Hermes Kanban deployment](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-multi-gateway), [SASE remote dispatch](https://sase.sh/remote_dispatch/).
- **Many agents do not imply many human collaborators.** Neither examined workflow should be promoted as a complete shared enterprise engineering platform solely because it coordinates multiple workers. Team identity, access control, tenancy guarantees and shared review ergonomics require separate evaluation.
- **Self-improvement is a procedure, not demonstrated intelligence growth.** Hermes can persist memory and create/update skills. That is useful functionality; this research supplies no evidence that every generated skill is correct or that task quality improves monotonically.
- **More machinery is not automatically better.** A typed graph, finalizer and verification ledger are benefits only when they replace work the user actually does. If they simply accompany tasks already handled by Hermes and CI, they are overhead.

## Does SASE realistically have a role for many users?

**Yes, as a specialized engineering control plane used by a repeatable class of operators.** The feature evidence supports that possibility; it does not prove future adoption or a large addressable population.

The target user is a developer or engineering operator running several independent changes or multi-phase efforts, often across repositories and native agent runtimes, who needs to answer four recurring questions:

1. What is the authorized plan and what work remains blocked?
2. Which agent/runtime changed which repository, and what evidence did it use?
3. What actually verified the change, including existing failures and uncertainty?
4. Who or what may land the result, and how is a failed or ambiguous landing recovered?

These needs arise in product engineering, infrastructure/toolchain changes, multi-repository maintenance, and long-running research-to-code projects. They do not depend on Bryan's dotfiles or private terminology. SASE bundles an answer to these questions that spans provider, work, evidence and repository lifecycle. That combination, rather than any one isolated feature, is its defensible role.

The counterargument is substantial: a user operating one runtime on one repository with existing CI may get everything needed from Hermes Kanban, review profiles, quality gates and PR contracts. Installing SASE for such a user can be redundant. Even for the target cohort, an existing CI/orchestration setup could be cheaper to extend in terms of complexity; no measured cost advantage is established here.

For SASE to become a tool many such users can reasonably choose, its product should emphasize a small explicit value proposition: **run native coding agents under one reviewable engineering lifecycle**. A first-use path should demonstrate an approved dependency graph, independent workspace work, failed-check recovery, and verified host landing using common repositories and minimal configuration. Personal macros should be optional recipes, not prerequisites for understanding the system. These are product recommendations inferred from the feature comparison, not additional current capabilities.

There is a credible complementary design: Hermes handles conversational intake, general assistance and messaging; SASE handles the engineering pipeline. This requires an actual maintained integration and should not be claimed to exist merely because shell commands or MCP make it possible. If native worker integration and SASE's evidence/landing contracts can be supplied inside Hermes with less total complexity, contributing those capabilities to Hermes may be the better strategy. SASE's distinct role must earn its separate installation.

## What would change this conclusion?

The literal parity claim would become much stronger if Hermes shipped supported lanes for the relevant native coding agents, a common multi-repository landing contract, equivalent verification evidence policies, and integrated artifact lineage. SASE's case would weaken if these distinctions remained difficult to use or delivered no practical benefit over Hermes plus existing CI.

A useful decision experiment would apply both configured products to the same four workflows: a small issue-to-PR task; a dependency-ordered effort with a failed worker and review rework; a cross-repository change whose verified inputs become stale; and a research swarm whose report must be consumed by a later implementation. Judge them on surviving records, recovery behavior, verification policy and custom integration required. This report did not execute that experiment, so it makes no comparative reliability, latency or cost claim.

## Recommendation

**Recommend Hermes first for general assistant work, research, automation, ordinary coding, and many durable multi-agent coding workflows. Do not add SASE merely to obtain parallel agents, memory, scheduling, isolation, review, or a task board: Hermes already provides those capabilities.**

**Reject the absolute “Hermes does everything SASE does” claim. Choose SASE when the user's recurring requirements specifically include several native coding-agent runtimes, host-owned multi-repository landing, project-level verification evidence, or a typed chain from approved plan and research to landed change.** That is a realistic role beyond Bryan, especially for engineering operators managing sustained parallel work. It is a specialized role, not a reason to recommend SASE to almost every agent user.

For SASE's wider product direction, concentrate on making that engineering lifecycle easy to demonstrate and operate. If its distinctive contracts cannot justify the extra system compared with Hermes plus existing CI, integrate them into Hermes rather than maintaining a broad competing general agent product.
