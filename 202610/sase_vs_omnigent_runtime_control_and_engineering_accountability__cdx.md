# SASE versus Omnigent: preserve engineering accountability, improve runtime control

Author: **cdx**, independent researcher in the requested five-researcher swarm.  
Research date: **2026-10-07**.  
Scope: the project the request calls “omniagent” is **Omnigent**, at the supplied omnigent-ai/omnigent repository.

**My conclusion:** SASE should borrow Omnigent's explicit runtime capabilities, selective action policies, and accessible session interfaces while retaining its own durable engineering model. Omnigent is a broad meta-harness organized around a conversation; SASE is an opinionated engineering coordinator organized around isolated work, review records, outcomes, and host-verified completion. Converting SASE into another general-purpose chat server would sacrifice useful differentiation. The highest-return changes are extensions to existing SASE mechanisms, rather than a replacement architecture.

For Bryan's current single-developer, multiple-provider use, I would start with a provider conformance model, an opt-in policy and budget layer, and meaningful execution profiles. A browser control surface comes next. Enterprise collaboration and disposable cloud hosts become more valuable if SASE's audience or deployment needs expand.

## Evidence and limits

This report independently examines source checkouts, maintained documentation, and first-party website documentation. I did not locate or read any peer report, transcript, or summary. No provider was installed, no live model benchmark was run, and no sandbox penetration test was performed. Implementation references establish what code and contracts exist; they do not establish universal enforcement, production reliability, or superior task success rates.

The checkouts inspected were:

| Project | Exact revision examined | Role in this comparison |
| --- | --- | --- |
| SASE | `6e2bc577260805ecec2695b93697cd5bfe3f66ac` | Current workspace documentation, provider adapters, integration and workflow contracts |
| Omnigent | `ee2488aee1d458033f854871b40bf3107d2fb748` | External checkout opened through SASE's repository access command |
| sase-core | `d2a56b4ca928c602379619bb35869d133df9800e` | Linked checkout; current Rust gateway routes and architecture |

The sase-core checkout is a separately observed revision, not proof of which core revision a released SASE installation uses. The website is mutable and can differ from the pinned tree. Both repositories describe themselves as alpha in their inspected READMEs; that label is not a measured comparison of maturity. [S1][O1]

Negative findings below mean “not found in the inspected implementation and documentation,” not a claim that no plugin or future branch can supply the behavior. Recommendations, effort estimates, and priority judgments are my inferences.

### Primary source index

References use immutable repository links where possible. Website references were checked on the research date.

- **S1 — SASE positioning and launch path:** [README][S1], [architecture][S2].
- **S3 — Provider behavior:** [provider base contract][S3], [provider result types][S4], [Claude invocation][S5], [Codex invocation][S6], [Grok invocation][S7].
- **S8 — Existing diagnostics and instructions:** [provider documentation][S8], [instruction bundles][S9].
- **S10 — Existing remote interfaces:** [mobile gateway][S10], [remote dispatch][S11], [public integration facades][S12], [Rust gateway router][C1].
- **S13 — Existing engineering controls:** [mentors][S13], [ToolRuns][S14], [finalizer configuration and completion][S15], [plugin system][S16].
- **S17 — Workflow and onboarding surfaces:** [macros][S17], [initialization][S18], [getting started][S19], [telemetry][S20].
- **O1 — Omnigent product and configuration:** [README][O1], [agent YAML spec][O2].
- **O3 — Capability model and verification:** [HarnessCapabilities][O3], [conformance suite usage][O4], [DENY probe][O5], [verdict reconciliation][O6].
- **O7 — Policy implementation:** [policy guide][O7], [engine][O8], [enforcement contracts][O9], [cost policies][O10], [loop detection][O11].
- **O12 — Execution isolation:** [sandbox contract][O12], [credential proxy][O13].
- **O14 — Concrete orchestration:** [Polly configuration][O14], [cross-review skill][O15], [session PR registry][O16], [runtime prompt composition][O17].
- **O18 — Delivery and recovery:** [runner event delivery][O18], [runner recovery measurement guide][O19].
- **W1 — First-party website:** [programmatic usage][W1], [shared server architecture][W2], [contextual policy overview][W3], [install guide][W4].

[S1]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/README.md
[S2]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/architecture.md
[S3]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/src/sase/llm_provider/base.py
[S4]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/src/sase/llm_provider/types.py
[S5]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/src/sase/llm_provider/claude.py
[S6]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/src/sase/llm_provider/codex.py
[S7]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/src/sase/llm_provider/grok.py
[S8]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/agent_providers.md
[S9]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/instruction_bundles.md
[S10]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/mobile_gateway.md
[S11]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/remote_dispatch.md
[S12]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/integrations.md
[C1]: https://github.com/sase-org/sase-core/blob/d2a56b4ca928c602379619bb35869d133df9800e/crates/sase_gateway/src/routes/router.rs
[S13]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/mentors.md
[S14]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/tool.md
[S15]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/configuration.md
[S16]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/plugins.md
[S17]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/macros.md
[S18]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/init.md
[S19]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/getting_started.md
[S20]: https://github.com/sase-org/sase/blob/6e2bc577260805ecec2695b93697cd5bfe3f66ac/docs/telemetry.md
[O1]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/README.md
[O2]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/docs/AGENT_YAML_SPEC.md
[O3]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/harness_capabilities.py
[O4]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/tests/harness_bench/README.md
[O5]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/tests/harness_bench/probes/policy_deny.py
[O6]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/tests/harness_bench/verdict.py
[O7]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/docs/POLICIES.md
[O8]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/runtime/policies/engine.py
[O9]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/policies/types.py
[O10]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/policies/builtins/cost.py
[O11]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/policies/builtins/safety.py
[O12]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/inner/sandbox.py
[O13]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/inner/credential_proxy.py
[O14]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/examples/polly/config.yaml
[O15]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/examples/polly/skills/cross-review/SKILL.md
[O16]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/runner/session_prs.py
[O17]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/runtime/prompt.py
[O18]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/omnigent/runner/transports/ws_tunnel/event_delivery.py
[O19]: https://github.com/omnigent-ai/omnigent/blob/ee2488aee1d458033f854871b40bf3107d2fb748/docs/runner-recovery-measurement.md
[W1]: https://omnigent.ai/docs/programmatic
[W2]: https://omnigent.ai/docs/deploy/overview
[W3]: https://omnigent.ai/docs/policies/overview
[W4]: https://omnigent.ai/quickstart/install

## What each project optimizes

| Dimension | SASE, at the examined revisions | Omnigent, at the examined revision | My assessment |
| --- | --- | --- | --- |
| Primary organizing unit | Project work, agent turns, Patches, goals, beads, and artifacts | Persistent conversations with agents, child sessions, tools, and resources | Different products with substantial overlap |
| Provider abstraction | CLI providers, invocation options, retry/routing, provider metadata and usage probes | Native, SDK, and protocol harnesses with explicit feature axes | Omnigent's capability representation is a useful model |
| Durable continuation | Sequential successors; monitor and gate handoffs; host-owned completion | Saved sessions, queued messages, runtime wake notices and runner reattachment | Preserve SASE's contract; borrow interface continuity |
| Parallel implementation | Numbered full-clone workspaces and tracked change workflows | Polly fanout and worker-owned worktrees/PRs | SASE already has first-class isolation and engineering records |
| Human decisions | Durable reviewed gate bundles, commands and shared projections | Policy ASK and tool approvals surfaced through session interfaces | Extend SASE gates to additional enforcement points |
| Action restrictions | Some adapter guards; broadly permissive inspected production CLI invocations | OS sandbox backends plus request/tool policy interception | A meaningful additional runtime-control layer exists upstream |
| Usage controls | Subscription windows, provider disable/routing, token information and host capacity admission | Session, subtree, daily/period cost policies and loop detection | Monetary budgets and capacity limits solve different problems |
| Interfaces | TUI, editor/plugin facades, paired mobile gateway and authenticated remote fleet operations | Terminal, browser, mobile, desktop, REST and Python client | Omnigent has a more obvious browser/automation product surface |
| Team collaboration | Reviewed contracts emphasize one developer and owned machines/devices | Session sharing and multiple access levels | Worth pursuing only if collaborator demand exists |
| Extension packaging | Existing entry-point groups and provider/config/macro plugins | YAML agents combining prompts, tools, subagents, policies and OS access | Package SASE recipes more accessibly; avoid a second workflow language |

Evidence: SASE's documented boundaries and integration contracts [S1][S2][S8][S10][S11][S12][S16][S17]; Omnigent's configuration, harness model, orchestration, and APIs [O1][O2][O3][O14][O15][W1].

## Findings that change the recommendation

### 1. SASE's engineering state is a strength to preserve

SASE keeps proposed changes and review state outside a chat transcript. Patches carry lifecycle state and change records; mentors produce structured findings; ToolRuns record execution outcomes, stages, and repository fingerprints. The host resolves selected finalizers and checks completion after the model supplies its declaration. Together these give SASE a stronger explicit engineering-accountability model in the material reviewed. This is an architectural judgment, not a measured quality advantage. [S1][S2][S13][S14][S15]

Omnigent does support engineering workflows. Polly delegates implementations to workers, uses independent review, and leaves PR merging to the human. Its session PR registry records created, worked-on, attached, and inferred PR relationships with atomic file updates and observation deduplication. It would be inaccurate to call Omnigent “just chat” or to assume it lacks source-control tracking. The difference is how centrally engineering completion is modeled. [O14][O15][O16]

SASE's single-turn behavior should remain intact. A richer browser conversation can show agent, monitor, and gate turns together while each provider invocation still ends and infrastructure starts any successor. Omnigent's runtime wake machinery is evidence of its own continuation design, not a reason for SASE agents to start depending on provider-native background wake-ups. [S2][S17][O17]

### 2. Capabilities should become one declared, testable contract

Omnigent's HarnessCapabilities records integration mode, elicitation mechanism, resume behavior, reasoning family, model family, authentication, subagents, interrupt, streaming, steering, queueing, images, compaction, history transfer, and instruction delivery. Unknown capability values are representable. The important idea is explicit support and limitation, rather than the number of supported harness names. [O3]

The conformance bench reconciles observed behavior against declarations and reports drift separately from missing evidence. Its documentation makes a valuable distinction: a successful default exit can mean no mismatch was found even when live probes never ran; automation must explicitly require live, complete observations. The DENY probe also requires the tool-call path to be exercised, avoiding a false pass from denying the entire request before the tool is attempted. I inspected these implementations but did not execute them. [O4][O5][O6]

SASE already has substantial groundwork: provider metadata and hooks, readiness diagnostics, usage capability declarations, per-provider synchronous ceilings, stream parsers, and instruction verification against provider session records. Its base invoke contract is still much narrower than Omnigent's capability record, and support facts appear in several provider-specific places. The change should consolidate these facts and generalize existing probes. It should not replace doctor or invent an unrelated diagnostics subsystem. [S3][S4][S8][S9]

### 3. Isolation, approvals, and prompts are separate controls

The inspected SASE adapters invoke Claude with permission skipping, Codex with approval and sandbox bypass, and Grok with bypassPermissions. They also have useful normalization and helper protections. Numbered repository clones reduce concurrent edit collisions; they do not establish an OS filesystem or network boundary. This makes unattended research, third-party code exploration, and accidental access outside the claimed workspace relevant use cases for opt-in execution restrictions. [S5][S6][S7][S8]

Omnigent has an actual sandbox contract with read/write roots, masking, environment allowlists, networking and egress settings, credential-source protection, and control-socket restrictions. Its YAML spec supports platform-default selection and explicit disabling. Its documented Windows mode provides process containment without equivalent filesystem/network isolation. Consequently, blanket claims that every configuration or platform provides the same protection would be too strong. [O1][O2][O12]

The credential proxy is a further, distinct mechanism: real secrets stay outside the sandbox, while permitted requests receive credentials at the proxy. Optional synthetic tokens accommodate clients that insist on a local token; the mapping is host-scoped. This is more powerful than redacting a secret after it appears in output, but requires an egress path and has its own integration burden. It is a later extension for SASE, not a prerequisite for every first execution profile. [O13]

### 4. Contextual policies are valuable, but their semantics need precise limits

Omnigent policies operate at request, response, tool-call, tool-result, and LLM boundaries. Runtime contracts distinguish pre-action phases that fail closed on unavailable evaluation from post-action/advisory phases; denying a tool result cannot undo an already incurred side effect. Builtins include tool-call limits and repeated identical-call detection using a bounded history of hashes. [O7][O9][O11]

Its cost policies contain useful subtleties that SASE should make explicit. The session policy evaluates accumulated cost at request and tool-call boundaries; a costly turn can overshoot before updated usage is available. Expensive-model selection can turn a configured threshold into a downgrade gate, while blocking every model requires different configuration. Actual evaluation code asks for acknowledgment when tokens are present but pricing is unavailable, and allows untracked continuation after that approval. A subscription utilization percentage, an estimated API cost, and an actual bill are different observations. [O10]

Documentation is not sufficient proof of policy behavior. The website says the first deciding policy wins, while the examined engine continues after ALLOW, accumulates ASK, and short-circuits DENY. The cost module's introductory comments describe unpriced usage as DENY, while its actual session evaluator returns ASK. These discrepancies are reasons to copy the executable contract and its verification approach, not to repeat simplified claims. [W3][O8][O10]

SASE already has reviewed, durable gates and guarded named tool execution. What I did not find in the reviewed SASE sources was a unified session/subtree dollar-budget policy or a provider-wide pre-tool enforcement contract. Some usage is unavailable: InvokeResult permits optional usage and the inspected Codex invocation documents usage as None. A useful first version must record unavailable data honestly and enforce only at boundaries it can actually control. [S4][S6][S10][S14][S15]

For SASE, a policy ASK should use an existing gate turn and a mechanically defined continuation. A native harness may be able to interrupt or reject a tool call; that does not automatically mean SASE can replay that exact tool safely after approval. Unsupported interception or continuation must be reported as unsupported. Session/project restrictions can tighten trusted host policy; lower-trust configuration should not be able to weaken it.

### 5. The interface gap is smaller than it looks, but still matters

Omnigent separates server, runner, and UI. The server maintains conversations, resources and policies; tool execution can remain on a connected host. Its REST and Python client surfaces expose session creation, history, events and lifecycle operations. This makes the product approachable to browser users and automation authors. [W1][W2]

SASE already has a paired, authenticated mobile gateway; launch/kill/retry and gate actions; fixed integration facades; and remote machine enrollment, catalog, content, mutation and attention routes. The examined Rust router confirms both mobile and fleet API families. “Add remote access” or “build a REST API” would therefore be poorly scoped recommendations. The opportunity is a supported browser client and a clearer public client contract over existing capabilities. [S10][S11][S12][C1]

Reconnection also needs honest semantics. SASE's mobile SSE buffer is in memory and sends resync_required when history cannot be replayed. Omnigent's programmatic stream documentation says live events do not replay history. Separately, its runner delivery implementation waits for server acknowledgments before advancing forwarder source cursors, with bounded queues and retransmission. That is a useful delivery pattern, not evidence of end-to-end exactly-once execution. Its recovery measurement guide distinguishes stream reconnection from completed work. [S10][W1][O18][O19]

A SASE browser should present durable state as authoritative and streaming updates as a convenience. Start with viewing work and answering existing gates. Multi-user sharing needs a separate authorization design; device enrollment is not equivalent to a collaborator's read, edit, or manage grant.

### 6. Ship more task-shaped entry points, using the existing language

Omnigent's YAML agents combine instructions, executor settings, tools, policies and subagents. Polly and its cross-review skill give users a named workflow instead of requiring them to assemble an orchestration strategy from primitives. The review recipe pins an immutable diff snapshot plus its acceptance contract, excludes the implementer's transcript, runs deterministic checks first, and sends blocking fixes back to the original implementer. These are useful packaging and review ideas. They remain partly prompt/skill instructions, not proof that the host mechanically guarantees every step. [O2][O14][O15]

SASE already supports typed macro inputs, YAML workflows, model directives, swarms, plugins, mentors and generated skills. Its initialization command coordinates config, machine, memory, repositories, service and skills. Therefore, a second “agent YAML” interpreter would largely duplicate machinery. Better packaging means a few documented, configurable engineering recipes with a visible expansion and known completion behavior. [S13][S16][S17][S18]

The cross-review independence criterion should use the resolved model vendor/family and context supplied, rather than just a different harness name. OpenCode, Pi, or Cursor can reach models from overlapping vendors; different wrapper names alone do not establish independent review. Independence can reduce correlated mistakes but does not prove correctness. [O3][O14][O15]

## Changes I would defer

- **Replacing SASE's durable stores with a central conversation database:** Omnigent's model serves sharing well, but SASE's work records, goals, artifacts and completion controls are already valuable. Add projections and clients around them first.
- **A large list of new harnesses or cloud providers:** Each brings authentication, interruption, instruction-delivery and update compatibility work. Add one only for a concrete workload; provider count is a poor quality metric.
- **Automatic semantic memory ingestion:** No demonstrated comparison-specific gap justifies a new retrieval system. SASE's existing audited memory and artifact reads are an asset; new recall machinery should follow a demonstrated corpus need.
- **Mandatory independent-model review for every tiny edit:** It can add latency, quota use and low-value findings. Make contract-focused review easy and selectable, then measure its value.
- **A native desktop shell before a usable browser client:** Omnigent's shell is useful distribution, but the underlying interface and contract are the more transferable work.

These are scope judgments, not claims that Omnigent's choices are wrong for its broader audience.

## Ranked recommended changes

The ranking is for Bryan's present SASE usage. Effort is an approximate engineering scope, not a calendar promise. Recommendations 1–3 strengthen reliability and control; 4 improves daily access; 5–6 improve workflow use; 7–8 are conditional expansion. Cross-frontend policy, aggregation and wire semantics should live in sase-core, with Python adapters and presentation calling through the Rust boundary.

1. **Unify provider capabilities and make conformance evidence visible.**  
   **Why first:** SASE depends on fast-moving CLI behavior across several providers. A false capability assumption can break launch, instructions, cancellation or completion; this foundation also determines which later policies can actually work. Extend existing metadata and doctor/instruction probes into a versioned declaration for instruction delivery, streaming, images, interruption, usage, helper protection, pre-tool interception and synchronous ceilings. Keep declared support separate from observed support, and record provider version, model, probe time, coverage and evidence. Start with offline validation and the existing fakey/fixture tests; use selected opt-in live probes for real guarantees.  
   **Acceptance:** one matrix distinguishes supported, partial, unknown, skipped and observed drift; a missing probe never counts as a pass; an explicit unsupported launch requirement fails before spawning; instruction verification and CLI/TUI labels derive from the same declarations. **Effort:** medium. **Evidence:** [O3][O4][O5][O6][S3][S8][S9].

2. **Add a small, opt-in policy layer for launch, continuation and controlled actions, including budget accounting.**  
   **Why second:** capacity limits and subscription disable rules do not prevent retry loops or budget overruns across a swarm. Start at SASE-owned boundaries—launches, successors, named tools and finalizers—then add native tool hooks only where recommendation 1 verifies them. Initial policies should cover maximum descendants/continuations, repeated failed actions and optional spend thresholds. Build a deduplicated usage rollup across a root and its children; show measured tokens, estimated priced cost, subscription utilization and unavailable data separately. Use existing gate turns for decisions requiring human input. Separate “stop launching more expensive work” from “interrupt the current provider”; only offer the latter when supported.  
   **Acceptance:** two concurrent children cannot silently consume the same remaining admission budget; retry/monitor successors retain the relevant policy state; repeated delivery does not double-count usage; unknown pricing is visibly unknown; approval is bound to the reviewed action and policy revision; no claim of an exact dollar cap is made without bounded in-flight spend. **Effort:** medium to large. **Evidence:** [O8][O9][O10][O11][S4][S6][S10][S14][S15].

3. **Offer verified execution profiles with OS boundaries, beginning with restricted research.**  
   **Why third:** a full clone plus permissive provider flags is useful for autonomy but does not constrain filesystem/network access. Introduce profiles such as read-only source research and writable isolated implementation, with explicit access to linked repositories, runtime state, dependency caches and required services. Avoid mapping “read-only” to the provider's planning mode alone. Separate the provider process from the host finalizer so restricted research does not need general write access merely to finish. Begin with Linux and document macOS parity explicitly.  
   **Acceptance:** real shell and tool paths cannot write an undeclared repository or read a forbidden sentinel; escaping symlinks and helper processes are exercised; finalization and audited artifact/repository operations still work; incompatible providers fail clearly before launch; trusted unrestricted runs remain an explicit choice. **Effort:** large, with a narrow first profile. **Evidence:** [O2][O12][S5][S6][S7][S8].

4. **Build a lightweight browser control surface on the existing gateway and public facades.**  
   **Why fourth:** Omnigent makes supervision and sharing visibly accessible; SASE already owns much of the backend needed for personal cross-device control. First ship agent/session viewing, diffs, durable artifact links, ToolRun outcomes and pending gates. Add launch/retry/fork/stop through existing operations. Present agents, monitor work and human decisions in one understandable sequence without changing the single-turn execution model. Reuse current mobile/fleet contract and snapshot-resync behavior; extend the contract only for missing views.  
   **Acceptance:** the same pending gate and work result are recognizable in CLI, TUI and browser; reconnect/restart performs a correct state refresh; duplicate clicks do not duplicate reviewed actions; opening a view requires no arbitrary host path or shell access. **Effort:** medium to large. **Evidence:** [W1][W2][O18][O19][S10][S11][S12][C1].

5. **Make independent, contract-focused review an explicit option in the existing mentor/workflow system.**  
   **Why fifth:** SASE already has reviewers; the incremental gain is pinned review input and explicit independence. Supply an immutable base/head diff and acceptance contract, keep the implementation transcript out of the initial review, select a different resolved model family/vendor when available, and persist structured blocking findings. Associate review evidence with the exact change so subsequent edits invalidate an earlier clean review. Keep automatic repair cycles bounded and user-configurable.  
   **Acceptance:** the reviewer cannot edit the implementation checkout; a different harness using the same underlying vendor is identified accurately; stale review evidence cannot qualify a changed diff; no independent model available produces a visible limitation rather than a fabricated review. **Effort:** medium. **Evidence:** [O14][O15][S13][S14].

6. **Ship a small catalog of task-shaped recipes and simplify the path to the first useful result.**  
   **Why sixth:** Omnigent's named agents make composition understandable. Package existing SASE macros/workflows into a few clear entries: investigate without edits, implement with independent review, parallel implementation, and independent research with synthesis. Show inputs, provider requirements, restrictions, expected artifacts and completion behavior before launch. Use existing configuration, generated skill sources and initialization paths; avoid a competing YAML runtime. Preserve user authorization without adding routine confirmation prompts.  
   **Acceptance:** a fresh user with one ready provider can run one useful recipe and find its artifact without mastering SASE's entire glossary; multi-provider recipes report missing requirements; previews match actual expanded launches; installed recipe provenance identifies its source version. **Effort:** small to medium. **Evidence:** [O2][O14][O15][S16][S17][S18][S19].

7. **Broker selected external credentials outside restricted agent processes.**  
   **Why seventh:** this meaningfully improves restricted workflows, especially repository exploration and unattended automation, but follows the execution boundary rather than preceding it. Start with one necessary integration, such as narrowly scoped repository API access, and minimize environment inheritance. Prefer a host-owned fixed operation when it satisfies the need; use a host-scoped egress broker when arbitrary permitted HTTP clients must authenticate. Do not require every provider's existing login to migrate at once.  
   **Acceptance:** the agent cannot read the underlying token; a credential placeholder sent to the wrong host is rejected; source failures and expiry produce a clear failure; tokens do not enter prompts or durable logs; an allowed service operation still works. **Effort:** large. **Evidence:** [O12][O13][S5][S6][S11].

8. **Add collaborator permissions and one managed execution-host integration only after demand is concrete.**  
   **Why eighth:** these are real Omnigent advantages for teams and cloud use, but less urgent for one developer already operating enrolled machines. For collaboration, begin with scoped, revocable viewing of a work session, then distinguish steering from approval/commit authority. For disposable execution, extend SASE's existing dispatch/provider mechanisms with one backend, durable launch identity, bounded provisioning and explicit cleanup. Keep durable artifacts and host completion independent of the disposable host. Treat these as separate features even if they share contracts.  
   **Acceptance:** a read-only collaborator cannot steer, answer gates or commit; revocation affects subsequent requests; an unavailable/provisioning host is distinguishable from an active run; lost execution reports uncertainty rather than success; retries cannot create duplicate hosts or duplicate completion actions. **Effort:** large and conditional. **Evidence:** [W1][W2][O1][O18][O19][S11][S16][C1].
