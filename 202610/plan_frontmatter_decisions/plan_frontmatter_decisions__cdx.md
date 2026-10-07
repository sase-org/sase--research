# Plan approval decisions in frontmatter: scoped consent and durable choices

Researcher: **cdx**. Date: 2026-10-07. Independent research for the plan/gate design swarm.

## Assessment

**This is a good idea when plan review produces a durable, typed implementation contract.** It becomes a poor idea if it embeds arbitrary executable gates in Markdown or leaves the coder to interpret unchecked prose as permission.

I recommend one optional `approval` frontmatter block, shared by tales and epics, declaring a small list of typed decisions. Render those decisions inside the existing plan approval gate. Keep launch/save/reject/feedback actions host-owned. Submit action, decision values, and reviewed revision together; preserve the outcome in the existing acceptance system and pass a resolved contract to every implementing agent.

The motivating cases have different semantics:

- **Memory change:** a scoped permission to perform a named operation, granted when a human submits approval. Its default is only a proposed checkbox state.
- **Implementation question:** a bounded preference whose alternatives must already be specified sufficiently for the coder to implement either answer.

This report recommends a design; it does not implement it or change the current memory policy. I independently examined source and primary documentation. I did not consult another swarm researcher's report, transcript, or findings.

## Existing SASE behavior

The inspected primary checkout was at `142636c528c5a109f8eb06ee9e4864bce6f4ba7d`; the opened `sase-core` checkout was at `4b3831fd8d00fb1405e70e974a8fa1070ba22b90`. Source paths below are relative to their named repository, so they remain useful outside this research workspace.

| Existing behavior | Source evidence | Consequence |
| --- | --- | --- |
| Strict plan validation is Rust-owned; accepted common/tale/epic/phase fields are enumerated and unknown fields rejected. | `sase-core: crates/sase_core/src/plan/validate.rs`, constants and `validate_top_level_keys` at line 566; adapter `src/sase/sdd/plan_validate.py` | Adding YAML alone will fail. Extend core schema, normalized wire, bindings, then callers. |
| Tale query is `(approve AND commit) OR reject OR feedback`; epic query is `approve OR reject OR feedback`. | `src/sase/_plan_gate_metadata.py:39` | Preserve the small, tier-aware action vocabulary. |
| `AND` allows any nonempty subset of one branch. | `src/sase/notification_gates/selection.py:37`; audited glossary:Sase Gate | Appending a permission to the action branch permits actionless resolution. |
| Plan validation pins exact query, option IDs, command resources, groups, edit operation, and gate-turn contract. | `src/sase/notification_gates/kind_validation/plan.py:43` | Do not relax trusted commands to accept arbitrary author-supplied executable options. |
| Gates already have bool/enum inputs, labels, defaults, help, and compiled JSON Schema. | `src/sase/notification_gates/model_inputs.py`, especially `compile_gate_input_schema` at line 311 | Reuse input machinery with plan-specific scope metadata. |
| Shared and per-option input contracts coexist. | `src/sase/notification_gates/model_results.py:97`, `effective_response_input` | Consume effective input through the adapter, not an assumed `response["input"]`. |
| Plan options currently all declare `default_selected: true`; auto resolution selects primary-branch defaults. | `src/sase/plan_gate.py:225`; `src/sase/notification_gates/adapters.py:46` | New permission defaults must never become automatic consent. |
| Requests/resources are hashed; accepted edits increment `review_revision`. | `src/sase/notification_gates/hashing.py`; `src/sase/notification_gates/edits.py:154` | Bind the accepted decisions to the exact reviewed revision. |
| Edit refresh validates and updates hashes; adapter preview regeneration is currently a no-op. | `src/sase/notification_gates/edits.py:185`; `src/sase/notification_gates/adapters.py:330` | An edited approval block must also recompile controls and input schemas. |
| Gate decision identity includes request hash, selected IDs, input identity, and feedback identity; replay/conflict handling precedes slow work. | `sase-core: crates/sase_core/src/gate_decision/policy.rs:58` and module contract | Extend existing acceptance/receipt machinery rather than a second decision store. |
| Tale coders start with fresh context, receiving a plan reference and approval instruction. | `src/sase/axe/run_agent_exec_plan_accept.py:218`, particularly lines 545–553 | Choices only shown to the planner or UI will disappear unless carried explicitly. |
| Epic creation validates normalized phases, creates phase beads, and applies explicit dependencies. | `src/sase/bead/epic_from_plan.py:67` | Carry decisions through publication, phase launch, and resume. Conditional phase deletion is additional graph behavior. |
| Gate turns outlive their creator and own follow-up policy. | `src/sase/plan_gate_turn/create.py`; audited `decisions:gates-never-block` | Reuse this lifecycle; no waiting agent or polling loop is needed. |

The current `sase_memory_write` skill allows an explicit user request, an approved plan naming the change, or an assigned bead describing it. For an unrequested memory change in a proposed plan, it requires a questions handoff before proposal. This feature could replace that extra interaction with consent during plan review. It must also replace the broad assumption that plan approval authorizes every memory-related sentence in its body.

## Comparable designs

These are analogies, not recommendations to import another system's implementation.

**Argo separates a human decision value from downstream work.** Its intermediate-input example pauses a workflow, obtains YES/NO, and conditions a subsequent step on the output; text and dropdown inputs are supported. My inference: review should yield typed data rather than several little approval commands. SASE already has an appropriate gate-turn continuation model. [Argo intermediate parameters](https://argo-workflows.readthedocs.io/en/latest/intermediate-inputs/).

**Terraform saved-plan mode executes the decisions in the saved plan and disallows additional planning options at apply time.** My inference: the implementing agent should consume a frozen resolved configuration instead of silently choosing an alternative after review. SASE prose cannot enumerate all eventual edits as Terraform does, so this supports revision binding rather than a claim of deterministic implementation. [Terraform apply](https://developer.hashicorp.com/terraform/cli/commands/apply).

**GitHub deployment review separates declaring protected work from permission to proceed.** Reviewed jobs advance after approval and other protection rules. My inference: memory permission belongs in host policy at the execution/publication boundary, rather than in an agent's account of what its gate meant. [GitHub deployment review](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments).

**Form design distinguishes one choice from independent selections.** GOV.UK uses radios for one choice and checkboxes for multiple selections or a toggle, and cautions against preselection because users may submit unintended answers. Requested-memory preselection would be a deliberate exception reflecting prior intent; visibly explain it. Unrequested permissions start off. [GOV.UK checkboxes](https://design-system.service.gov.uk/components/checkboxes/), [GOV.UK radios](https://design-system.service.gov.uk/components/radios/).

**Group labels matter independently of item labels.** W3C recommends grouping related controls visually and semantically. My inference: give each decision a readable heading and each permission a concrete action label. Color and glyphs cannot explain authorization alone. [W3C grouping controls](https://www.w3.org/WAI/tutorials/forms/grouping/).

**JSON Schema expresses validity, not a pleasant plan-authoring language.** Conditional vocabulary includes property dependencies and `if`/`then`/`else`; presence dependencies are not automatically bidirectional. My inference: compile a small typed authoring vocabulary into schema. A property being present is not equivalent to its boolean value being true. [JSON Schema conditionals](https://json-schema.org/understanding-json-schema/reference/conditionals).

## Critique

### The gains are real

One review can approve implementation, decline incidental memory churn, and answer a small design question. The planner finishes useful work before the human is available. Preferences become replayable data rather than transient messages. Epic workers need not rediscover decisions made during proposal review.

Frontmatter is a reasonable location because it is portable, versioned with the plan, and already validated. Detailed alternatives should remain in Markdown, so the header describes review controls instead of swallowing the entire design.

### Conditional plans can become hard to reason about

Five independent toggles allow 32 configurations; choice fields multiply that space further. Every allowed configuration needs a coherent implementation. A validator can verify types and references, but cannot establish that arbitrary prose is coherent for all combinations.

Use embedded decisions for small, local alternatives already designed. Use questions or feedback/replanning if an answer changes architecture, invalidates estimates, creates unknown work, or reshapes the phase dependency graph. Planning before an answer is useful only when the planner knows how to implement the possible answers responsibly.

### A memory checkbox needs scope

“Update memory” says little about targets, operations, or future instructions. The human should see exact canonical files and concise change descriptions; later turns need evidence of the accepted scope. A broad checkbox can otherwise authorize unrelated durable instructions.

There is an enforcement limit: inspecting a Git diff before commit prevents unauthorized work from landing, but cannot prevent an unrestricted process from writing a file earlier. Filesystem prevention requires an actual file/tool access boundary. V1 should promise host-enforced publication/commit coverage plus clear agent instructions, not stronger protection than it implements.

Path coverage also cannot prove semantic conformance to a summary. A grant for a note does not authorize arbitrary instructions in that note. Encourage proposed replacement wording for substantive policy changes. Requiring exact patches for every memory edit would strengthen enforcement, but exceeds the requested planning feature.

### Defaults cannot prove explicit user intent

“Default on iff explicitly requested” is a good UX rule but not perfectly machine-decidable for free text. An authored `requested_by_user: true` is not evidence. Even a real quote is an attribution the reviewer can assess, rather than a proof of intent.

Use conservative preselection with recorded request evidence; ambiguous cases begin off. Require human submission for memory permissions regardless of preselection. This avoids automatic authorization if a planner misreads the request.

### Mandatory planning has a cost

A one-line memory correction becomes plan authoring, validation, and review. That is defensible for durable agent instructions. Make the small case a short `xsmall` tale with concrete targets and proposed wording, not an epic or a gate per file. Bundle related requested edits when they form one action.

## Intentional requirement adjustments

1. **Embed decisions, not full executable gate requests.** Authors declare values and permissions, not shell commands, resource bundles, successor prompts, arbitrary query expressions, or replacements for approve/reject behavior.
2. **Separate default state from authorization.** Requested-memory preselection affects presentation; human acceptance creates the grant.
3. **Make memory human-only by host policy.** No authored `human: false` or auto setting can relax this. Human provenance comes from a trusted ingress, not a caller-supplied `source` string.
4. **Require concrete canonical scope.** Each memory change names repository, path, operation, and summary; no blanket `sase/memory/**` opt-in. Renames include both paths.
5. **Keep v1 alternatives bounded and epic graphs fixed.** Defer conditional phase deletion, arbitrary predicates, and a workflow programming language until actual plans need them.
6. **Keep existing memory policy until the replacement is enforced.** When this feature becomes authoritative, planned human grants replace direct-request and bead-only shortcuts for authored memory edits. Generated skill templates and published instructions must change together.
7. **Define a narrow generated-output exception.** Host-owned catalog projections and rendering derived from approved canonical edits should not recursively need plans for their own output. The owning generator defines the exception; an agent cannot label its own template edits “generated.”

These are proposed policy changes, not permissions granted by this research request.

## Proposed authoring contract

Call the block `approval`, and its entries `decisions`: they are choices made while approving the plan, not additional executable actions. The UI still renders familiar gate controls.

The following is **proposed syntax**, unsupported by today's validator:

```yaml
---
tier: tale
title: Add durable cache storage
goal: Cache entries survive restarts without changing the public API.
size: medium
approval:
  version: 1
  decisions:
    - id: cache_store
      type: choice
      label: Which cache store should the implementation use?
      required: true
      choices:
        - value: sqlite
          label: SQLite
          section: cache-sqlite
          summary: One local database; no external service to operate.
        - value: postgres
          label: PostgreSQL
          section: cache-postgres
          summary: Reuse the existing service; configure connection credentials.

    - id: write_memory
      type: memory
      label: Update the cache reference note
      default: requested
      section: cache-memory
      changes:
        - repo: project
          path: sase/memory/cache.md
          operation: update
          summary: Document the selected store and its local recovery procedure.
---
```

No default for `cache_store` means the question must be answered before implementation approval. The planner can recommend SQLite in prose; that recommendation is not a submitted value. If the user delegates the choice, a declared valid scalar default is appropriate, with the outcome recorded as default-derived.

An optional enhancement uses:

```yaml
- id: include_migration_helper
  type: toggle
  label: Include a migration helper for existing cache entries
  default: false
  section: migration-helper
```

| Type | Result | Default | Rules |
| --- | --- | --- | --- |
| `toggle` | Explicit boolean | `false` when omitted | Local optional work with a referenced body section. |
| `choice` | One stable string | Absent unless authored | Unique values; every alternative implementable; required means a value must be supplied. |
| `memory` | Explicit boolean, plus host grant if true | Fixed policy `requested` | Concrete canonical changes; human acceptance required; literal true cannot override policy. |

IDs follow the existing input convention `^[a-z][a-z0-9_]*$`; labels are presentation, never stored values. Reserve action/transport names such as `approve`, `commit`, `reject`, `feedback`, `coder_model`, and `wait`. Reject unknown fields, duplicate YAML mapping keys/IDs, invalid defaults, unsupported versions, unknown operations, and missing section references.

`section` points to a unique ordinary Markdown heading anchor, with collision detection during validation. The section describes implementation and acceptance criteria. The body can say “Apply only when `write_memory = true`”; the host renders the same activation label. A section reference is navigation, not permission evidence.

Keep required metadata focused: memory entries supply `changes`, choices supply `choices`, toggles supply a section. Avoid nested groups, inherited labels, arbitrary expressions, free-text answers, runtime-generated choices, secret inputs, and per-option commands in v1. Other gates can handle those cases when needed.

### Requested-memory preselection

`default: requested` is a policy marker. The host attaches review metadata from recorded human input: request reference, a short real quotation, and proposed target match. A planner may nominate evidence, but it must match actual human input and appear as an attribution, not a proven fact.

If context is absent, agent-authored, or ambiguous about the specific operation, initialize false. A broad request to implement cache storage does not imply a request to modify durable memory. For a requested edit, show “Preselected because your request asks to update the cache note,” with the quote available in details. For incidental work, show “Suggested by the planner; off by default.”

An aggregate memory option is preselected only when all its named changes were explicitly requested. Split mixed requested/unrequested changes. A parent's existing grant may propagate within its exact scope; inheritance is not a fresh claim of a new human request.

## An intuitive and beautiful review

The plan remains the visual center, with a compact decision rail. On narrow screens, stack the same groups above the final action. Preferences come first; durable memory permissions get a distinct, plainly labeled group.

```text
Add durable cache storage                         Tale · medium

Implementation choices
  Cache store                         Select one
  ( ) SQLite      One local database
  ( ) PostgreSQL  Reuse the existing service

Memory changes
  [ ] Update the cache reference note
      sase/memory/cache.md · update
      Document storage and local recovery
      Suggested by planner · Off by default
      View planned change

Plan preview
  Cache / SQLite                 active when cache_store = sqlite
  Cache / PostgreSQL             active when cache_store = postgres
  Cache / Memory                 excluded until enabled

  [✓] Launch coder    [✓] Save plan
  [Approve and launch]     [Send feedback]     [Reject]
```

This sketches interaction, not a new theme. Build on existing review modals.

- Explain constraints in words: “Select one,” “Optional,” “Requires human approval.” Use radios for choices, checkboxes for independent toggles and permissions.
- Keep memory scope and consequence visible beside the control. Large excerpts/diffs belong behind a readable detail action, never an unexplained glyph.
- Mark included/excluded sections without rewriting the source plan or executing its prose. Excluded alternatives remain discoverable.
- Update an outcome sentence: “Launch coder with PostgreSQL; do not change memory; save this plan.” It catches accidental defaults and mixed action meanings.
- Preserve existing focus and shortcut conventions. Space changes a toggle; arrow keys change radios; submission uses the established action shortcut. Show inline validation before submission.
- After settlement, show actual values and provenance, not initial `default_selected` states. A reviewer-enabled default-off permission must render as enabled in history.
- TUI, CLI, mobile, and Telegram submit the same action, decisions, and expected revision. A surface unable to collect required fields should offer a review link or reject that attempt, never silently drop fields.

Saving without launching may retain draft configuration for later review, but must not mint implementation authorization. Feedback and rejection require no answers and grant nothing. Maintain the existing independence of tale launch/save actions.

## Runtime contract

### Compile into trusted input

Preserve existing built-in action queries. Compile plan decisions into typed input for `approve`, with scope/section metadata attached to the normalized model. Existing bool/enum input controls provide primitives; memory behavior remains plan-specific host policy.

Illustrative submission:

```json
{
  "selected_option_ids": ["approve", "commit"],
  "expected_review_revision": 3,
  "expected_request_hash": "<current reviewed request hash>",
  "option_inputs": {
    "approve": {
      "decisions": {"cache_store": "postgres", "write_memory": false}
    },
    "commit": {}
  }
}
```

These new fields are proposed semantics, not existing API assertions. Follow current input contracts during implementation. A frontend-facing flat form may compile into nested `decisions` if current renderers require it; retain one normalized result.

Do not use `(approve AND commit AND write_memory)`: today's subset semantics would allow `write_memory` alone to resolve it. Several independent radio questions also fit poorly into disjoint branches without duplicating IDs or enumerating combinations. Typed parameters solve both while keeping trusted commands narrow.

### Authored plan, accepted decision, resolved contract

Keep authored schema/defaults unchanged. Store normalized accepted values, stable plan identity, authored content digest, request hash, revision, acceptance ID, reviewer identity, source, timestamp, and permission scope in the host-owned acceptance system. Extend the existing receipt; if a companion immutable resource is needed, hash/reference it from the receipt instead of establishing another source of truth.

The resolved implementation contract contains every value, including explicit false; included/excluded sections; exact memory targets/operations; denied proposed changes; accepted plan identity; and human/automated provenance. Supply it alongside the exact approved plan to tale coders and phase workers.

Use a host-owned instruction to apply only that configuration and stay within grants. Labels, summaries, excerpts, and feedback are labelled data, not interpolated instructions. Coders cannot infer results from initial defaults or the planner's chat.

### Edits, stale review, and failure

Compare submitted hash/revision under the acceptance lock. Verifying bundle bytes against current hashes does not prove that the reviewer saw those bytes; the reviewer must submit the version they saw. Reject old TUI/mobile forms after an edit.

An accepted edit atomically validates the plan, recompiles decisions/input schema, refreshes previews, increments revision, and republishes the request hash. Retain draft values by ID only if types/choices still match. Clear permission selections when scope changes. Accepted grants never transfer silently to edited content. Rejected origin drafts preserve the last reviewed bundle.

Record the accepted decision before launching work. Use existing replay/conflict and execution-owner rules so retrying acceptance or a failed launch cannot choose different values or create duplicate coders. Idempotent acceptance is not a proof of exactly-once external effects.

Timeout, cancellation, rejection, and feedback mint no grants or implementation continuation. Missing/corrupt decision records fail closed for decision-bearing plans, rather than degrading to “implement everything.”

Machine-added plan headers, timestamps, associations, and bead links need special handling: preserve an authored snapshot/digest separately from these projections, or define the authored representation in core. Hashing a mutable current archived file indiscriminately would invalidate legitimate epic follow-ups. Author changes to prose/decisions remain review-significant; generated link refreshes do not expand scope.

### Epics and direct entry points

Resolve epic decisions once, before publication/launch. Every phase and resume references the same accepted configuration. Permissions propagate only as subsets of exact parent scope, never as a blanket assertion that the epic was approved.

Keep all declared phases in v1. Small sections inside fixed phases may depend on answers. If a choice removes all substantive work from a phase or changes downstream dependencies, restructure or replan rather than create empty phase beads. Conditional phase deletion introduces skipped-dependency and graph-validity policy and should be a later feature.

Audit direct routes such as `sase bead work --from-plan`, epic creation, and resume helpers. Decision-bearing plans require verified acceptance irrespective of launch route. Validation, a saved plan copy, or a bead description is not a receipt. Caller-supplied values cannot impersonate review.

### Automatic approval

For preferences, `%auto` may use valid declared defaults when the human has delegated the choice. Record automated provenance. A required choice with no answer/default leaves review pending instead of guessing.

**Any plan declaring memory permissions should remain pending for human review under `%auto` in v1.** Even a default-off proposal deserves an explicit outcome under this initial policy. Later, a host-controlled automation mode could strip all optional memory work and approve a coherent remainder. That is a separate capability, not an implicit consequence of `default: false`.

### Memory enforcement

Resolve logical repo names through project inventory. Accept normalized repo-relative canonical paths; reject unknown repos, absolute paths, traversal, wildcards, and symlink escape after canonicalization. Include create/update/delete and both sides of rename. A path in another repo is not covered by an identically named project path.

At host finalization, compare changed canonical memory paths/operations with applicable human grants across primary, linked, and home configuration repos. Refuse uncovered or broader changes before publication/commit, with a concrete reason and recovery route. A confirmation gate cannot retrospectively expand the original receipt.

Generator-defined instruction rendering from approved sources is covered derivatively. Handwritten changes to generated AGENTS/provider shims remain invalid. A template change that changes durable instructions is authored work and requires scoped review; rendering is not a loophole for its template.

This enforces a publication boundary. It does not stop unrestricted filesystem writes or prove that prose matches its summary. Those stronger guarantees need additional access controls or exact-patch review and should not be claimed for this feature.

## Implementation and rollout

Shared parsing, normalization, validation, acceptance, and grant matching belong in `sase-core`; Python adapts wire data and orchestrates I/O; Textual renders. All frontends consume the same normalized model. This follows the project's explicit Rust boundary.

Three deliverables keep the scope controlled:

1. **Complete decision vertical slice:** core schema/wire/bindings, trusted plan inputs, primitive controls, persistence, edit recompilation, revision assertions, tale handoff, and fixed-graph epic propagation. Do not ship checkboxes whose values disappear at handoff.
2. **Memory enforcement:** human-only scope grants, finalizer coverage, direct launch/resume checks, and generated-output policy. Only then update generated skill templates and published instructions to retire the separate pre-proposal question requirement and broad memory authorization shortcuts.
3. **Polish and measured expansion:** compact review across transports, live consequence summaries, section navigation, and resolved history. Let actual difficult proposals justify dependencies between decisions, optional phases, or richer inputs.

A new binding requires moving `sase-core-revision.txt` past its core commit. Wire-version changes require coordinated constants, mirrored fixtures, and compatibility checks in both repositories. Old plans without `approval` keep their existing flow. Older clients must reject unsupported decision-bearing plans instead of dropping fields. Plan-wire and gate-request versions are separate compatibility contracts; do not bump every protocol reflexively.

No new top-level CLI command is required. Existing validate/propose/approve/answer paths can accept the typed contract. A later read-only resolved-review display may help if current show/debug surfaces are inadequate. Implementation must read the relevant CLI, generated-skills, TUI, flags, and bead memories before changing those domains; this report makes no such code or policy changes.

### Acceptance tests

- Legacy tales/epics validate, review, and launch unchanged.
- Duplicate keys/IDs, unknown fields, invalid defaults/choices/operations, invalid scope paths, and missing sections yield actionable diagnostics.
- Memory starts off without a matching request; scoped requests preselect visibly; mixed requested/unrequested changes never all preselect.
- Human approval with memory false launches coherent base work and denies its memory edit. True grants only named repo/path/operations and derived rendering.
- Required unanswered choices cannot launch. Valid defaults resolve identically across transports.
- `%auto` cannot grant or silently bypass a memory decision; missing choices are not guessed.
- Save-only, reject, feedback, timeout, and cancel create no implementation grants.
- Scope edits refresh controls/schema and reject stale submissions; invalid origin drafts preserve reviewed bytes.
- Replay stays idempotent; conflicts fail; launch recovery keeps the accepted choices.
- Every phase and resumed/direct launch consumes the verified contract; missing evidence fails before work.
- Machine associations preserve authored identity; real authored edits invalidate approval.
- Unauthorized memory diffs cannot be committed by the normal finalizer. Tests distinguish that boundary from filesystem prevention.

UI snapshots should cover narrow/wide pending and resolved states, multi-choice plans, provenance, long scopes, and stale review errors. Implementation uses standard project verification; this report only requires research and artifact checks.

## Alternatives

| Approach | Benefit | Weakness | Decision |
| --- | --- | --- | --- |
| Questions gate before every proposal | Existing mechanism; good for fundamental uncertainty | Extra human round trip/replanner; weak association between answer and scoped work | Keep for material uncertainty. |
| Full executable custom gate in frontmatter | Very expressive | Executable Markdown, weakened trusted contract, lifecycle/auto complexity, bulky headers | Reject here. |
| Append checkboxes to action AND branch | Small-looking change | Actionless subsets; preferences become commands; multiple radio questions fit poorly | Reject. |
| Write results back into authored defaults | Easy to read a final file | Blurs proposal/result, mutates identity, makes provenance forgeable | Store results host-side and render a projection. |
| General conditional plan language/phase DAG | Broad variation | Combination explosion, skipped-dependency policy, hard review | Defer. |
| Typed decisions inside existing plan gate | Clear authoring, familiar controls, durable result | Needs careful propagation, editing, enforcement, and transport parity | Recommend. |

Source inspection cannot establish whether users notice optional memory work or understand a mixed decision rail. Evaluate with representative real plans before enlarging the schema. The complete inventory of launch routes and memory generators also needs an implementation audit; the paths identified here are useful starting points, not an exhaustive proof.

## Recommended solution

**Build optional `approval.version: 1` frontmatter with `toggle`, `choice`, and scoped `memory` decisions, compiled into the existing host-owned plan approval gate.** Preserve the action query, submit one atomic decision against the reviewed revision, integrate with existing receipts, and pass a resolved contract to tale coders and every epic phase.

Preselect memory only with explicit scope-matching request evidence, always require human submission, and enforce canonical scope before host publication. Keep epic graphs fixed and route substantial uncertainty through questions or replanning. This delivers the convenience of planning before an answer while making consent concrete and keeping the interface small enough to remain intuitive and beautiful.
