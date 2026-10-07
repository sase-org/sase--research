# Make `%auto` a typed autonomy policy selector

Independent research by **cdx**, 2026-10-07. This report was produced without consulting the other reports or researcher conversations in this swarm. All syntax and configuration marked **proposed** below describe a design, not existing functionality.

**My recommendation is to expand `%auto`, but keep its immediate job focused on SASE workflow decisions.** Introduce a small, typed policy selected by named profiles or explicit keyword arguments, evaluate it in the Rust core, and apply decisions through the existing gate executor. Separate plan execution, plan archival, preference answers, and agent delegation. Treat filesystem, shell, network, and connector permissions as a separate enforcement project that can later use the same policy vocabulary.

This is a useful change if the goal is fewer unnecessary interruptions with predictable control. A larger `%auto` grammar that merely tells the model to behave differently would deliver convenience while overstating what it controls. The most valuable improvement is an inspectable, durable effective policy; the directive is its compact user interface.

**Evidence and limits.** I inspected the current SASE checkout at `ca5eff431f6963318e0eae15827775d6b2fde86c` and the independently opened `sase-core` checkout at `4b3831fd8d00fb1405e70e974a8fa1070ba22b90`. The SASE CI pin currently names `f8d05efc58310eca985f2112afc89379ff7a6636`, so the inspected core tree and CI-pinned core are distinct. I read relevant project memory through audited `sase memory read`, inspected source and existing tests, ran a read-only parser probe, and consulted official external documentation. I did not execute any approval, privileged command, deployment, or successor launch to establish behavior. Findings about complete workflow effects below are source-traced; the parser outputs are directly observed.

**What `%auto` actually controls today.** The public documentation says it requests automatic notification-gate resolution, retaining an opaque argument for interpretation by the eventual gate adapter. The parser stores three overlapping representations: `auto_enabled`, `auto_argument`, and legacy `auto_mode`. Bare `%auto`, `%a`, and `%auto+` map to a compatibility mode of `plan`; arbitrary values such as `%auto:foo` survive parsing. Duplicate `%auto` occurrences, including aliases, raise an error. There is no typed per-capability policy in these fields. See [directive parsing](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/macro/_directive_values.py#L505) and [current tests](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/tests/test_directives_flags.py#L9).

| Gate or behavior | Current source-traced behavior | Consequence for the redesign |
| --- | --- | --- |
| Tale plan | Accepts bare/default, `plan`, and `tale`; selects default-selected options in the primary branch | Specify action IDs explicitly; do not derive authority from visual defaults |
| Epic plan | Accepts bare/default, `epic`, and `epic_plan`; approval follows the epic execution path | Bound the execution authority behind this one decision, including any fan-out |
| Question | Automatic input selects the first listed option for each question | Choosing a preference and granting permission must have separate semantics |
| Launch | Automatic resolution is forbidden; its spec hardcodes `auto: false` | Supporting automatic delegation requires a deliberate host change, not a new spelling |
| Sudo, HITL, custom, task/flag/plugin gates | The registered adapters forbid automatic resolution | Preserve explicit handling until each kind has a reviewed automation contract |
| Provider tool access | Claude and Codex invocation paths include permission/sandbox bypass flags independently of `%auto` | `%auto` is not an OS or provider-native access restriction |
| Monitor continuation | Reconstructs `%auto` from legacy metadata fields | Policy must persist as structured session state instead of being recovered from strings |

The gate behaviors are visible in [adapter resolution and registration](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/notification_gates/adapters.py#L46), [launch construction](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/agent/launch_request_gate.py#L250), and [question default construction](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/user_question_actions.py#L403). Provider bypass flags appear in [Claude invocation](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/llm_provider/claude.py#L434) and [Codex invocation](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/llm_provider/codex.py#L464). Inheritance evidence is [monitor continuation](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/monitor/continuation_delivery.py#L216).

**Two implementation findings deserve attention before extending the grammar.** First, parenthesized `%auto` currently has a silent argument-loss hazard. The generic collector parses named arguments, but `%auto` has no special handling for them and retains only the first positional argument. I ran the workspace's Python parser using the installed SASE interpreter and runtime dependencies, with workspace `src` first on `sys.path`:

```python
from sase.macro.directives import extract_prompt_directives
_, d = extract_prompt_directives('%auto(plan=ask, questions=ask)\nInspect only')
# Observed: auto_enabled=True, auto_mode='plan', auto_argument=None

_, d = extract_prompt_directives('%auto(plan, epic)\nInspect only')
# Observed: auto_enabled=True, auto_mode='plan', auto_argument='plan'

_, d = extract_prompt_directives('%auto:off\nInspect only')
# Observed: auto_enabled=True, auto_mode='off', auto_argument='off'
```

Thus the first example strips both intended restrictions and behaves as bare `%auto` at the parser boundary. `off` is an opaque enabled argument, not a supported disable switch. The Rust editor metadata currently advertises only colon, bare, and plus forms for `%auto`, so these parenthesized examples are not a documented feature. Nevertheless, silently interpreting them as permission to automate is a poor failure mode. Unknown keys, extra positionals, duplicate keys, and unsupported forms must be rejected rather than discarded. Source: [generic collection](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/macro/_directive_collect.py#L116), plus the `auto` record in `crates/sase_core/src/editor/directive/metadata.rs` in the inspected core checkout.

Second, the current source and documentation disagree about the plan default. The docs describe bare `%auto` as normal tale approval and distinguish `plan` from `tale`. However, `build_plan_approval_gate_spec` sets the tale primary branch to `approve, commit`, `_plan_gate_option` gives every option `default_selected: true`, and `resolve_auto_selection` returns those default-selected primary options for every accepted tale auto argument. Selection therefore resolves to **both coder launch and plan commit** on this constructor path, including bare/default and `plan`. The existing plan-spec test explicitly asserts those defaults. This is a source-traced mismatch, not a claim that I executed and observed a real plan commit. See [plan gate construction](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/plan_gate.py#L170), [option defaults](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/plan_gate.py#L225), and [the test assertion](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/tests/test_plan_gates.py#L146).

Migration should establish the intended contract with end-to-end characterization before changing either branch. Do not promise that preserving an old spelling preserves a no-commit guarantee that the current constructor does not implement.

**The existing architecture is a good foundation.** Automatic creation writes a durable gate bundle and calls `execute_gate_selection` with source `auto_resolution`; it does not bypass the executor. Automatic and manual resolution can therefore continue sharing validation, command execution, receipts, side effects, and settlement. The acceptance layer already separates durable acceptance from potentially slow execution, uses a verified request hash, and delegates replay/conflict policy to the Rust core. Reuse this machinery instead of building another approval path. See [gate service](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/notification_gates/service.py#L214) and [decision acceptance](https://github.com/sase-org/sase/blob/ca5eff431f6963318e0eae15827775d6b2fde86c/src/sase/notification_gates/decision.py#L1).

An important limitation remains: creation-time automation currently assumes a binary enabled state before allocating a notification. A richer evaluator needs to return an outcome before deciding whether to publish a pending review. A policy miss must produce a usable manual gate, not fail halfway through an automatic creation path or erase the request.

**What other systems contribute.** These comparisons identify design patterns; they are not proposed verbatim provider mappings.

| System | Verified pattern | Lesson for SASE |
| --- | --- | --- |
| Codex | Separates sandbox restrictions from approval policy; supports automatic review of eligible approval requests | Keep execution access, decision routing, and reviewer choice independent. [Official security documentation](https://learn.chatgpt.com/docs/agent-approvals-security) |
| Codex execution rules | Matches argument-vector prefixes, combines matches by restrictive decision, exposes rule checks, and handles compound shell syntax conservatively | Provide an explain/test interface; avoid shell-string prefix matching as a security mechanism. [Rules documentation](https://learn.chatgpt.com/docs/agent-configuration/rules) |
| Claude Code | Evaluates deny, then ask, then allow; permission rules and sandboxing have distinct coverage | Make precedence explicit and expose which restriction wins. [Permission documentation](https://code.claude.com/docs/en/permissions) |
| Gemini CLI | Uses typed allow/deny/ask rules, conditions, modes, and source tiers with numeric priorities | Separate mode selection from rules, but avoid copying a large priority system without a need. Its docs currently warn that workspace policies are non-functional. [Policy engine documentation](https://geminicli.com/docs/reference/policy-engine/) |
| Cedar | Models principal, action, resource, context; matching forbid overrides permit, and no permit means denial | Use typed action requests and restrictions that cannot be silently overridden. A policy language dependency is unnecessary for the initial small schema. [Authorization model](https://docs.cedarpolicy.com/auth/authorization.html) |
| MCP | Requires clients to treat tool annotations as untrusted unless they come from trusted servers | A plugin's claim that an action is read-only is insufficient authority for an automatic grant. [Tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |

The inference I draw is that the transferable idea is **explicit decisions over typed actions**, not a universal autonomy ladder. SASE also differs from interactive harnesses: an agent must end its turn through a gate handoff when human input is needed. An `ask` result should use that existing lifecycle; it must never wait inside the provider turn.

**Critique of the proposed direction.** Making `%auto` more configurable is a good idea, but “more powerful” should mean composable authority over known decisions. A user should be able to approve implementation while keeping design questions interactive, permit plan archival without starting execution, or delegate a small amount of work without authorizing an unlimited swarm.

I would avoid four approaches:

1. A numbered autonomy ladder such as `0..5`: plan execution, publishing, privileged commands, questions, and delegation are not naturally ordered. A single level cannot communicate all of those tradeoffs.
2. A global `%auto:all`: every future gate kind would become a potential implicit grant. Adding a plugin must not silently expand what an existing policy permits.
3. A prompt-only permission DSL: the agent can ignore instructions or reach the same side effect through shell, native tools, or an integration. This would improve cooperative behavior but would not enforce a resource boundary.
4. A general policy language or LLM risk assessor in the first release: both introduce substantial operational and explanation costs before the action catalog is stable. A reviewer can be added later behind deterministic restrictions; its availability or judgment should not become the source of authority.

A completely separate `%permissions` directive would be reasonable for actual provider/OS access profiles, but I would not replace `%auto` merely to gain keyword arguments. Keep the familiar surface for automatic workflow decisions and let a separate execution-access profile arrive when there is real coverage to back its claims.

**Explicit adjustments to the requirements.** These are deliberate changes to the user's broad brief, not assumptions that the user already requested them.

| Adjustment | Justification |
| --- | --- |
| Define v1 as workflow autonomy, not a claim of general hard permissions | Existing provider launches bypass native checks; many actions do not pass through SASE gates |
| Give question answering a separate policy, defaulting to human input | The first option can represent a preference, missing information, or permission; those are different decisions |
| Separate plan approval from plan archival and epic approval | Current values mix tier, durable writes, and downstream execution |
| Require strict validation and an effective-policy preview | A mistyped restriction must never silently enable automation |
| Require scope and bounded inheritance | One SASE session can span multiple provider turns, monitors, replanners, and children |
| Keep sudo, arbitrary custom commands, plugin installation, and novel gate kinds manual initially | Each requires its own action/effect contract before automation can be meaningful |
| Preserve old spellings through an explicit compatibility translation, with characterization of the plan mismatch | Silent changes to existing macros would defeat predictable control |
| Make enforcement coverage visible | A workflow restriction that relies on agent cooperation must be distinguishable from a broker or sandbox check |

**Proposed user interface.** Use named profiles for everyday launches and parenthesized keyword overrides for deliberate exceptions. Preserve `%a` as an exact alias. Keep one `%auto` per launch unit initially, matching today's duplicate check; there is no need for order-sensitive permission accumulation.

```text
%auto:develop
%auto(profile=develop, questions=ask)
%auto(plan=approve, epic=ask, questions=ask, scope=session)
%auto(plan=archive, questions=ask, scope=turn)
%auto(plan=approve_archive, epic=ask, questions=default, scope=session)
%auto:off
```

`develop` and `off` are **new proposed profile names**, not currently supported modes. `off` means “do not automatically resolve workflow gates”; it does not prevent ordinary file edits or undo a user's explicit authorization. The UI must say that directly.

A small initial schema can cover the useful dimensions:

| Field | Proposed values | Precise meaning |
| --- | --- | --- |
| `profile` | Trusted configured name | Loads a versioned set of defaults; unknown names fail launch validation |
| `plan` | `ask`, `approve`, `archive`, `approve_archive` | Tale gate selection: manual; coder only; archive only; coder plus archive |
| `epic` | `ask`, `approve` | A separate choice because epic approval authorizes a broader execution workflow |
| `questions` | `ask`, `default` | Manual answers, or declared defaults for eligible preference questions only |
| `scope` | `turn`, `session` | Current logical agent turn, or mechanical continuation within the same agent session |

Omitted new-style fields default to `ask`. The shipped `develop` profile should initially set `plan=approve`, `epic=ask`, `questions=ask`, `scope=session`. A user who frequently wants preference defaults can explicitly override `questions=default` or create a trusted profile. `archive` means the existing plan-sidecar archive operation, including its publication behavior; it must not be rendered merely as “save locally.” Neither plan archival nor `%auto:off` modifies the separate host finalizer policy governing code commits and pushes.

For new syntax, select explicit option IDs, such as `['approve']` or `['approve', 'commit']`. Do not follow `primary_branch`, `default_selected`, colors, option order, or recommended labels when deciding permission. Plan tier remains authored in the plan document; the directive does not reinterpret a tale as an epic.

**Question handling needs a small schema improvement.** Add stable option IDs, an explicit `default_option_id`, and a purpose such as `preference`, `required_input`, or `authorization`. `questions=default` may answer a preference question only if a valid default exists and no missing data must be invented. Free-text-only questions, malformed defaults, required inputs, and authorization questions remain manual. With multiple questions, use an all-or-manual result initially, preserving the current complete-form response contract.

An agent-authored purpose field is only a convenience hint, not a security guarantee. A response to a question must never mint a launch grant, sudo approval, publishing authorization, or other host authority. Those operations require their own typed request checks even if a question was mislabeled as a preference. Existing first-option behavior can survive in the frozen legacy translation, but should not be the new default mechanism.

**Profiles and precedence.** Store profile definitions in SASE's existing configuration system, with a small new schema section, rather than introducing a new configuration file ecosystem. A conceptual entry is:

```yaml
# Proposed additions, not a currently valid configuration schema.
autonomy:
  version: 1
  default_profile: manual
  profiles:
    manual:
      plan: ask
      epic: ask
      questions: ask
      scope: session
    develop:
      plan: approve
      epic: ask
      questions: ask
      scope: session
```

Avoid arbitrary inheritance chains and numeric rule priority in v1. Resolve an approved profile plus explicit per-run overrides, then apply a separately defined host ceiling and inherited parent restrictions. An omitted default is not an explicit prohibition: a trusted user's `plan=approve` can override the default `ask`. An explicit host or parent restriction cannot be loosened by a run-local field. Within constraints, use restrictive composition: deny exceeds required-human review, which exceeds automatic selection. This distinction avoids the mistake where a global default `ask` accidentally prevents every valid user override.

Repository-provided profiles and macro-expanded directives should count as requested configuration until a trusted launch surface authorizes them. An agent-edited config file must not widen an already-running session. Freeze the resolved profile, version, digest, source provenance, and ceiling at admission. Trusted human updates can revoke or narrow later authority; automatic widening waits for an explicit new grant. This improves reliability under the current shared-user environment but cannot by itself create an adversarial security boundary against an agent that can modify host state.

**Core design and integration.** Implement a small pure policy function in the existing `sase_core` domain style, alongside the gate-decision domain or in a dedicated autonomy module. Its inputs should be versioned wire structures, not Python-only dictionaries with ad hoc flags:

```text
EffectiveAutonomyPolicyWire:
  schema_version, profile_id, policy_digest, resolved_fields,
  authorized_source, scope, session_id, parent_constraints

ActionRequestWire:
  authenticated_actor, project, repo_ids, gate_kind,
  request_hash, proposed_selection, derived_effects, continuation_relation

AutonomyDecisionWire:
  auto | ask | deny,
  selected_option_ids, validated_input,
  reason_code, policy_digest, applicable_constraints
```

These shapes are illustrative. Runtime code must derive the actor from host execution context and derive effects from registered host adapters; a caller's claim about its identity or the harmlessness of a script is not trusted input. Keep preference default resolution separate from authorization of side effects even if both appear in one decision response.

The integration sequence should be:

1. Parse and validate the directive; resolve the trusted effective policy before launch and persist its snapshot.
2. On a gate request, have the adapter describe valid selections and all resulting effects. Include archive publication, coder launch, epic execution, and follow-up actions, not just the immediate option command.
3. Ask the Rust evaluator for an outcome. Match the complete intended selection; if an AND combination includes an ungranted effect, keep the whole requested combination manual rather than silently executing part of it.
4. For `auto`, pass the exact selection and input into the existing executor. For `ask`, create the normal pending gate and hand off through its shell. For `deny`, execute no effect and return a typed refusal through an appropriate continuation; do not synthesize a user's rejection answer unless the adapter declares that meaning.
5. Persist policy provenance with the accepted decision and journal. Continue to use existing request hashing, replay/conflict handling, execution validation, and settlement.

Move shared resolution, restrictions, propagation rules, and explain output to Rust. Python remains responsible for adapter IO, durable storage integration, and invocation glue; Textual remains presentation. Update PyO3 bindings and the SASE CI core pin when the new binding lands. The Rust typed launch extractor, editor directive metadata, macro LSP, and Python parser must accept and reject the same forms.

**Inheritance is part of the feature, not follow-up polish.** Session-scoped authority should survive a monitor, feedback replanner, or approved coder transition using a structured policy reference. Do not regenerate `%auto` strings from `approve` and `auto_approve_plan_action`, as the monitor path does today. Independent sibling sessions do not inherit by adjacency or clan name. A new delegated child receives an explicitly derived policy constrained by its parent's authority, with a provenance link. Child prompt text may narrow the policy but cannot enlarge it.

A `turn` scope expires on handoff into the next logical turn. A `session` scope survives mechanical continuations until settlement or revocation. This needs to be shown in the launch preview because SASE provider turns are single-turn: hidden expiration would otherwise surprise users. A one-next-gate grant can be added later, but must use an atomic consumption record shared by concurrent continuations, not a boolean in an environment variable.

**Bounded delegation is the next useful extension.** I would add automatic launch approval after the above contract is stable, before broad shell-policy work. Proposed later syntax could be `%auto(profile=develop, launch=bounded, max_children=2, max_depth=1)`. The host must check the actual expanded launch plan, selected projects, allowed provider/model identities, dispatch destinations, child authority, and fan-out. Defaults should stay within the originating project and local execution unless the user explicitly grants a wider scope.

`max_children` should mean a cumulative launch budget across the session lineage, not just simultaneously running agents; runner capacity is a different control. Reserve that budget atomically before acceptance. Persist a reservation identity so retries do not spend the budget twice, define refunds for failed dispatch, and ensure two children cannot each consume the same last slot. Prefer model and launch-count bounds to a pretend exact dollar cap unless reliable live pricing and usage accounting exist.

Epic approval and plan-to-coder transitions must disclose and account for their own derived launch effects. A generic helper-launch restriction cannot be a back door around a smaller epic or coder budget. Where the host cannot bound the expanded effect graph, remain manual. This is substantially more work than adding a `launch=true` flag, but it is also where a more powerful `%auto` would produce clear value.

**How to keep broader permissions honest.** An expanded gate policy checks only routed requests. If shell commands, native app tools, or direct CLI invocations can reach the same effect without that check, a denied capability is a workflow constraint, not a hard access denial. Today, environment variables and agent metadata are also readable and writable by the same user running the agent. A digest detects differences; it does not prevent that agent from rewriting a policy and its digest.

A future execution-access layer should constrain filesystem roots, process execution, network destinations, external writes, and credentials through a sandbox and/or a host broker, keeping sensitive authority outside the agent's execution environment. Provider adapters should report capabilities they can enforce and reject a requested mandatory restriction when unsupported. Do not silently map a narrow SASE policy to a provider's bypass-all mode. For providers that cannot enforce the same constraints, show advisory coverage or require a brokered execution path.

This can share the typed action vocabulary without making `%auto` an enormous universal directive. Generic shell parsing, URL allowlists, symlinks, interpreters, redirected writes, subprocesses, and MCP effects all create distinct coverage problems. A rule that permits `git status` text is not proof that an arbitrary shell script is read-only. Scope that work separately and do not delay useful workflow configuration until it is solved.

**Visibility and acceptance criteria.** Provide an effective-policy view before implementation ships, not after. Proposed read-only interfaces are `sase agent policy show <agent> --json` and a policy explanation command accepting a recorded gate or synthetic action. Names are illustrative; any actual CLI addition must follow the project's CLI rules.

The human view should read like: “Coder launch automatic; plan archive asks; epic asks; questions ask; helper launches ask; sudo asks; scope session; source explicit launch override.” A separate coverage line should identify which checks are host-enforced and which remain cooperative workflow restrictions. Preserve the same representation across CLI, TUI, mobile, and Telegram. Do not show a reassuring green “restricted” badge while provider execution has unrestricted shell access.

Record automatic decisions without producing a pending approval notification for each allowed action. A durable activity entry should include request hash, effective policy digest, selected action IDs, reason, authorized source, and whether execution completed. Acceptance is not execution success. An explain result must agree with real evaluation on the same request.

Meaningful verification should cover:

- Parser rejection of unknown keys, extra positionals, duplicate keys, malformed parentheses, contradictory fields, unknown profiles, and policy versions.
- Python/Rust/LSP/completion parity for `%auto` and `%a`, including fences, disabled directive regions, macro expansion, alternatives, repeats, and session attachment.
- Explicit tale selections for coder only, archive only, and both; separate epic handling; characterization of current legacy selection before migration.
- Question defaults unaffected by option reordering; missing or invalid defaults remain manual; preference answers confer no action authority.
- No silent authority increase from project config edits, injected directive text, unsupported adapters, or a new gate kind.
- Monitor/replanner continuation fidelity, turn-scope expiration, child narrowing, revocation, and no inheritance into unrelated sessions.
- Gate concurrency, stale request hashes, replay, conflicting selections, partial command failure, and no extra successor from creator-live automatic settlement.
- For delegation, cumulative and depth limits, concurrent reservation, retry identity, failed-dispatch recovery, and expanded fan-out accounting.

Measure interruption rate by gate kind, policy misses, explain/runtime disagreement, unexpected side effects, and recovery failures. Count fewer unnecessary questions as success only if they are not replaced by incorrect defaults or accidental authority.

**Migration and implementation sequence.** Start with a characterization step: establish real executor behavior for legacy bare, `plan`, `tale`, and `epic`, and settle the docs/source mismatch. Reject unsupported parenthesized forms immediately until they have implemented semantics. This parser correction is small but materially improves the failure mode.

Then introduce versioned policies, explicit new syntax, named profiles, frozen session metadata, and explanation output. Keep the old spellings on an explicit legacy translation. Do not map them opportunistically to whichever profile happens to be configured under the same name. In particular, reserving `plan`, `tale`, and `epic` as compatibility names avoids collisions with user profiles.

Next route plan, epic, and eligible question automation through the evaluator and existing executor. Stop passing one opaque `%auto` argument to every gate kind. A scoped plan policy should simply produce `ask` for unrelated kinds rather than fail because a question adapter cannot interpret `tale`. Preserve manual restrictions on sudo, custom commands, plugin installation, and unreviewed kinds.

Only then add bounded delegation with launch-preview review and durable budget accounting. Treat true provider/sandbox access profiles as a separate stage. Read the project's feature-flag and compatibility memory before any actual behavioral migration, and follow the shared Rust boundary and core-pin procedure. This research makes no source changes and does not propose bypassing those implementation requirements.

The external primary sources linked above were accessed on 2026-10-07. They support the comparative patterns; the detailed proposed schema, rollout, and tradeoffs are my recommendations. No benchmark establishes a precise effort estimate, and no full gate execution was run for this report.

**Recommended solution.** Implement a **small Rust-owned autonomy policy selected by `%auto`**, with named profiles and strict keyword overrides. In the first release, separate tale coder launch, plan archival, epic execution, and preference defaults; default new-style unspecified decisions to human input; expose the frozen effective policy; and use the existing hashed gate bundles, acceptance receipts, executor, and handoff lifecycle. Preserve legacy behavior through an explicit characterized translation rather than broadening bare `%auto`. Add bounded delegation next. Keep general execution-access permissions separate until a sandbox or broker can enforce them. This offers substantially more useful control while keeping every automatic grant understandable and avoiding a false promise of hard permissions.
