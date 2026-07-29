---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# `/sase_search_skills` and Scalable xprompt Skill Bundles

## Executive summary

The proposed `/sase_search_skills` direction is sound, but a “bundle” should not mean an OpenAI plugin or one
always-visible umbrella skill per domain. Neither makes the startup catalog constant-size: plugin-packaged skills remain
individual skills, while per-domain umbrellas still add one description per bundle.

The best design is a **single always-visible search gateway plus hidden, named bundles of leaf xprompt skills**:

1. Keep a small set of policy-critical or extremely frequent skills installed normally.
2. Add `skill_bundle: <name>` to xprompt source frontmatter. A bundled xprompt remains a real skill in SASE's catalog,
   but `sase skill init` no longer installs it as a top-level provider `SKILL.md`.
3. Install one normal `/sase_search_skills` skill. It searches a provider-rendered catalog generated alongside it,
   returns a few matches, and loads exactly one selected leaf's full instructions.
4. Preserve `sase skill use` telemetry for both the gateway and the loaded leaf.

This adds a second disclosure boundary:

```text
agent startup
  └─ core skill names/descriptions + sase_search_skills description
       └─ search returns top-k bundled names/descriptions
            └─ load returns one full leaf workflow
                 └─ leaf-specific resources load only if needed
```

For the current effective xprompt catalog, I recommend keeping eight skills top-level and moving ten into four initial
bundles. That changes the xprompt contribution from 18 visible skills to 9 (eight core plus the gateway), cutting
startup xprompt metadata by roughly 43–45% while keeping skills responsible for about 93% of recorded uses directly
visible.

## Scope and method

This audit covers every effective xprompt with `is_skill: true` returned by `sase xprompt list` on 2026-07-29:

- 16 package skill sources under `src/sase/xprompts/skills/`
- `bob_query`, supplied by a home xprompt file
- `sase_gmail`, supplied by the `sase_athena.yml` config overlay

It does not cover built-in system skills or plugin skills that are not xprompts.

The analysis used:

- the current Python loader, model, generator, inventory, manifest, and CLI code;
- the shared Rust frontmatter schema and xprompt catalog in `sase-core`;
- the current effective catalog and `sase skill log --json`;
- official OpenAI and Agent Skills documentation; and
- the earlier July 7 report,
  [Progressive Disclosure of xprompt Skill Descriptions](../xprompt_skill_description_progressive_disclosure.md).

Use counts below are directional, not a perfect popularity measure. The log is cumulative, includes two uses of the
retired `sase_artifact` name, and some foundational skills now set `log_skill_use: false`; their historical events
remain in the log.

## What has changed since the July 7 research

The earlier report reached the right architectural conclusion: retain a small core and put a single search skill in
front of the long tail. The current audit adds four important details:

1. The effective catalog grew from 14 package skills to **18 effective skills**.
2. Named bundles are useful for authorship, filtering, ownership, and staged rollout, but should sit _behind one
   gateway_, not each become another visible umbrella.
3. The current generator never deletes obsolete skill targets. Moving a skill into a bundle without adding managed
   pruning would leave its old top-level `SKILL.md` installed, defeating the design.
4. Search/load should use a generated catalog snapshot rather than rescan the current repository at activation time.
   This preserves deployment provenance and prevents a checkout from injecting hidden instructions into a global skill
   search.

## Current cost and failure mode

The 18 effective xprompt skills currently contribute:

| Measurement                                                         | Current value |
| ------------------------------------------------------------------- | ------------: |
| Effective xprompt skills                                            |            18 |
| Description characters                                              |         2,951 |
| Name + description + source-path characters, before host formatting |         4,552 |
| Full body characters                                                |        73,820 |
| Full body words                                                     |  about 10,684 |

The 73,820 body characters are not the startup problem. Agent Skills already loads bodies only after activation. The
problem is the first tier: every installed skill's name and description, and in Codex its path, is initially disclosed.

The [Agent Skills specification](https://agentskills.io/specification) describes roughly 100 tokens of startup metadata
per skill, then full instructions at activation and references only as needed. The
[client implementation guide](https://agentskills.io/client-implementation/adding-skills-support) gives a similar
50–100-token estimate and explicitly supports dedicated activation mechanisms.

OpenAI's current [skill-building guide](https://learn.chatgpt.com/docs/build-skills) says Codex caps the initial list at
2% of the context window, or 8,000 characters when the window is unknown. It first shortens descriptions and can then
omit skills. SASE's 4,552 unformatted characters do not establish that the complete host catalog is over budget—the
host also has non-xprompt skills and its own framing—but they already consume a meaningful fraction.

The practical failure is not simply token expense. Once the host shortens or omits descriptions, implicit activation
recall degrades. A skill that is absent from the initial catalog cannot tell the model that it exists.

## Current implementation constraints

### One xprompt currently means one installed skill

`XPrompt.skill` is `bool | list[str] | None`. `select_skill_xprompts()` selects every truthy entry, and
`render_skill_targets()` writes one provider `SKILL.md` per selected xprompt. Provider lists are already meaningful, so
overloading `skill: [a, b]` with bundle names would be ambiguous.

The clean extension is a separate scalar:

```yaml
---
name: sase_gmail
description: Read-only personal Gmail access through gog.
skill: true
skill_bundle: personal_data
---
```

Semantics:

- `skill` continues to mean “this is a provider skill” and continues to select providers.
- no `skill_bundle` means top-level/core exposure;
- `skill_bundle: <name>` means searchable leaf exposure;
- the winning xprompt after existing first-wins discovery determines both content and bundle;
- a bundled skill is still available as an xprompt (`#sase_gmail`) even though the provider's native slash/mention
  catalog no longer lists `/sase_gmail`.

### The frontmatter contract crosses the Rust boundary

The Python `XPrompt` model and loaders must retain `skill_bundle`, but the authoritative field schema, validation,
hover documentation, and editor wire live in `sase-core/crates/sase_core/src/editor/frontmatter.rs`. This is shared
domain behavior and should be added in Rust first, then exposed through the existing binding and consumed by the Python
frontmatter panel/serialization code.

The Rust xprompt catalog already carries `is_skill` and supports catalog filtering. It is the right home for bundle
filtering and deterministic search scoring so CLI, TUI, editor, and future web surfaces do not disagree.

### Deployment currently cannot prune a former top-level skill

The generated-skill plan supports create and overwrite, not delete. The provenance manifest stores a source commit and
one aggregate xprompt hash, but not the managed target paths or per-file hashes.

This is a blocking implementation detail. If `sase_gmail` becomes bundled but its former
`~/.<provider>/skills/sase_gmail/SKILL.md` remains, hosts will keep injecting its description.

The safe answer is a versioned manifest containing every generated relative path and content hash. Deletion may target
only a path recorded as SASE-managed, and should refuse or surface drift if the live file no longer matches its
recorded hash. Unknown user skills must never be pruned.

### “Plugin bundle” is a different concept

OpenAI recommends plugins for distributing related skills, but a plugin can contain several ordinary skills. Packaging
changes installation and distribution; it does not merge those skills into one startup metadata entry. SASE should use
“skill bundle” as an internal disclosure/catalog concept and avoid representing these bundles as plugins.

## Design options

| Option                                           | Startup growth                  | Trigger quality                              | Runtime uniformity                       | Assessment                                                                           |
| ------------------------------------------------ | ------------------------------- | -------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| Keep all skills visible and shorten descriptions | O(skills) until host truncation | Good initially, then degrades                | Superficially uniform; limits differ     | Useful hygiene, not a scaling design                                                 |
| One giant SASE skill                             | O(1)                            | Very broad trigger                           | Uniform                                  | Activating it loads too much unrelated procedure and violates focused-skill guidance |
| One umbrella skill per bundle                    | O(bundles)                      | Better than one giant skill                  | Uniform                                  | Reasonable interim organization, but not constant-size                               |
| Predict a per-run subset at launch               | O(predicted subset)             | Misses later task drift                      | Requires launch integration              | Helpful future seeding, unsafe as the only discovery path                            |
| Dynamically enable/disable native skills         | Small when curated              | Native explicit invocation retained          | Provider state and restart behavior vary | Operationally stateful and contrary to the uniform-runtime goal                      |
| One search gateway over hidden named bundles     | O(core + 1)                     | Depends on gateway recall and search quality | One SASE contract for every runtime      | Best backbone                                                                        |

## Proposed runtime model

### Tier 1: visible core plus `/sase_search_skills`

Only policy-critical, hard-to-recover, or extremely frequent skills remain ordinary installed skills.

The gateway description must be compact but deliberately broad and front-loaded. For example:

> Search and load optional SASE workflows for agent status/history, notifications, ChangeSpecs/projects,
> artifacts/variables/gates, Gmail, or Obsidian notes. Use when no listed skill clearly covers the task.

This is the only description that needs to advertise the bundled categories at startup.

### Tier 2: deterministic bundled search

The gateway runs something like:

```bash
sase skill search "inspect the notification I just received" --limit 5 --json
```

Results should contain only compact fields:

```json
{
  "query": "inspect the notification I just received",
  "matches": [
    {
      "name": "sase_notify",
      "bundle": "agent_observability",
      "description": "Inspect SASE notifications and notification inbox entries.",
      "score": 12.4
    }
  ]
}
```

Start with deterministic lexical retrieval over weighted fields:

- exact/prefix name match: highest weight;
- description: high weight;
- bundle name: medium weight;
- full body: low weight, primarily to recover command or domain terms missing from the description.

BM25 or an equivalent in-memory token scorer is sufficient initially. Do not add embeddings until representative evals
show misses that lexical retrieval cannot address. Search should return no match plainly instead of falling back to an
unrelated skill.

### Tier 3: explicit leaf load

After selecting a match, the gateway runs:

```bash
sase skill load sase_notify --reason "Inspect the notification referenced by the user"
```

`load` should:

- allow only a name in the generated catalog, preventing path traversal or arbitrary-file reads;
- confirm that the leaf targets the invoking provider;
- record the leaf's use when `log_skill_use` is enabled;
- return only that leaf's provider-rendered body, wrapped as identifiable skill content;
- report its bundle and source provenance; and
- avoid reinjecting a leaf already loaded during the current run when that state is available.

The wrapper should clearly say that the returned content is skill instruction and that relative resources resolve
against the generated bundle resource directory.

### Generated snapshot, not live checkout discovery

`sase skill init` should generate the gateway plus a provider-specific, non-discoverable resource set:

```text
sase_search_skills/
├── SKILL.md
└── references/
    ├── catalog.json
    ├── sase_agents_status.md
    ├── sase_artifact_file.md
    └── ...
```

The reference files must not be named `SKILL.md`; otherwise a host with recursive scanning may expose them as ordinary
skills again. Keeping references one directory below the gateway also follows the Agent Skills specification.

The snapshot should contain only bundled leaves eligible for that provider and should be rendered from the same merged
catalog and source commit as the visible skills. `sase skill search/load` should resolve the invoking provider through
existing SASE agent metadata and provider deploy-path interfaces, then read that deployed snapshot. It should not
rescan xprompts from the current working directory.

Current xprompt skills are instruction-only, so this is sufficient for the first version. Before a future bundled leaf
can own scripts/assets/references, the generator must copy those resources and preserve a safe relative base path.

## Complete current-skill audit

The log contained 4,138 total historical events, including two events for the retired `sase_artifact`. The proposed
eight-skill core accounts for 3,837 events (about 92.7%). The ten proposed bundled leaves account for 299 events (about
7.2%).

| Skill                |  Recorded uses | Recommendation                     | Bundle                | Rationale                                                                                                       |
| -------------------- | -------------: | ---------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------- |
| `bob_query`          |              9 | Bundle                             | `personal_data`       | Personal, read-only Obsidian/Dataview workflow; strong domain terms and low frequency                           |
| `sase_agents_status` |             53 | Bundle                             | `agent_observability` | Read-only live-agent inspection; closely related to chats and notifications                                     |
| `sase_artifact_file` |              6 | Bundle                             | `agent_runtime`       | Narrow, normally explicit artifact-publication request                                                          |
| `sase_beads`         |          1,688 | Keep top-level                     | —                     | Extremely frequent, central work-tracking workflow with a precise trigger                                       |
| `sase_changespecs`   |             58 | Bundle                             | `project_admin`       | Specialized PR/ChangeSpec inspection; searchable by distinctive domain vocabulary                               |
| `sase_chats`         |             74 | Bundle                             | `agent_observability` | Read-only prior-agent inspection and direct companion to agent status                                           |
| `sase_gate`          |              8 | Bundle, with gateway trigger evals | `agent_runtime`       | Specialized durable command-confirmation flow; low use, but its safety-related trigger must be tested carefully |
| `sase_git_commit`    |          1,825 | Keep top-level                     | —                     | Most-used skill and mandatory commit/finalizer boundary                                                         |
| `sase_gmail`         |              0 | Bundle                             | `personal_data`       | Personal, read-only integration supplied by config overlay; ideal long-tail example                             |
| `sase_hg_commit`     |              0 | Keep top-level when deployable     | —                     | Mandatory commit boundary for its intended provider; native provider filtering should remain                    |
| `sase_memory_read`   |  85 historical | Keep top-level                     | —                     | Audited access boundary required directly by instruction files                                                  |
| `sase_notify`        |             15 | Bundle                             | `agent_observability` | Read-only inbox inspection with strong “notification” trigger terms                                             |
| `sase_plan`          |  29 historical | Keep top-level                     | —                     | Replaces disabled native plan mode and performs a lifecycle handoff                                             |
| `sase_project`       |             31 | Bundle                             | `project_admin`       | Project lifecycle/selection workflow; related to ChangeSpec and multi-project inspection                        |
| `sase_questions`     |             70 | Keep top-level                     | —                     | Replaces disabled native question tooling and performs a lifecycle handoff                                      |
| `sase_repo`          | 121 historical | Keep top-level                     | —                     | Mandatory audit/trust boundary before accessing any other repository                                            |
| `sase_run`           |             19 | Keep top-level                     | —                     | Low frequency but governs launch authorization and prevents direct agent spawning                               |
| `sase_var`           |             45 | Bundle                             | `agent_runtime`       | Narrow inter-agent output/handoff mechanism, usually identifiable from explicit variable needs                  |

### Initial bundle definitions

```yaml
personal_data:
  - bob_query
  - sase_gmail

agent_observability:
  - sase_agents_status
  - sase_chats
  - sase_notify

agent_runtime:
  - sase_artifact_file
  - sase_gate
  - sase_var

project_admin:
  - sase_changespecs
  - sase_project
```

Bundle names organize the catalog and support filtering; they do not each generate a visible umbrella skill.

### Skills that should not be bundled initially

The top-level set should be:

- `sase_beads`
- `sase_git_commit`
- `sase_hg_commit` for its intended provider
- `sase_memory_read`
- `sase_plan`
- `sase_questions`
- `sase_repo`
- `sase_run`
- `sase_search_skills`

Frequency alone is not the criterion. `sase_run` is less used than several proposed bundled leaves, but a missed launch
authorization boundary is much more expensive than an extra search for a transcript or project record.

### Independent defect found

`sase_hg_commit.md` still says `skill: [gemini]`, while the registered provider is `agy`; the current skill inventory
therefore shows no target providers for it. This was already noted in the July 7 research and remains true. Fixing the
provider selector is independent of bundling, but the intended commit skill should remain top-level once deployable.

## Suggested source and CLI contracts

### Frontmatter

Add a scalar `skill_bundle` field rather than changing the existing `skill` value space:

```yaml
skill: true
skill_bundle: agent_observability
```

Validation rules:

- a non-empty, normalized bundle name;
- `skill_bundle` requires a truthy `skill`;
- bundle membership must not change provider-selection semantics;
- `sase_search_skills` is reserved and cannot itself be bundled;
- duplicate skill names continue to use the existing discovery precedence;
- diagnostics and hover text originate in `sase-core`.

### CLI

Recommended commands:

```text
sase skill search QUERY [--bundle NAME] [--limit N] [--json]
sase skill load NAME --reason TEXT [--json]
sase skill bundle list [--json]
sase skill bundle show NAME [--json]
```

`search` and `load` are agent-facing. `bundle list/show` make the authored grouping inspectable for humans, tests, and
future UIs.

`sase skill list` should gain exposure and bundle columns so it distinguishes:

- top-level/core generated targets;
- bundled/search-only leaves;
- the gateway;
- missing, stale, and orphaned managed files.

## Implementation map

### `sase-core`

- Add `skill_bundle` to the shared frontmatter field schema, hover docs, validation, and wire.
- Extend the xprompt catalog record and response wire with bundle membership.
- Add deterministic skill-only search/filter behavior in core so CLI, TUI, editor, and future frontends agree.
- Add query ranking and serialization tests, including provider filtering and exact-name boosts.

### Python xprompt and skill layers

- Carry `skill_bundle` through `XPrompt`, file/config/plugin loaders, namespace copies, prompt-frontmatter
  serialization, and `sase xprompt list`.
- Split selected skill xprompts into top-level and bundled targets after existing precedence resolution.
- Render provider-specific leaf references and the gateway catalog.
- Add `search`, `load`, and bundle inspection handlers under `sase skill`.
- Keep leaf use logging compatible with `log_skill_use`.

### Deployment and inventory

- Upgrade `.sase-skills-manifest.json` to record schema version, source commit, every managed path, provider, skill,
  exposure, bundle, and content hash.
- Plan create/overwrite/delete operations. Delete only previously managed, hash-matching paths.
- Show deletions in `--diff` and `--dry-run`.
- Treat modified former targets as drift requiring an explicit resolution; never erase an unknown user-authored skill.
- Include catalog/reference files in the same deploy lock, commit, provenance, and `chezmoi apply` transaction.

### Tests and evaluation

Unit/integration coverage should include:

- Rust/Python frontmatter and wire parity;
- file, config-overlay, plugin, and collision discovery;
- provider-specific bundle membership;
- current source rendering for all providers;
- search exact-name, synonym, no-match, and top-k ordering;
- load authorization, provider eligibility, wrapper formatting, and audit events;
- migration from top-level to bundled with safe deletion;
- manifest v1-to-v2 migration and locally modified target refusal;
- no nested `SKILL.md` under bundle resources;
- no catalog exposure when no bundled leaves exist.

The activation eval set should contain at least:

- one direct and one indirect positive prompt for each bundled leaf;
- confusing pairs such as live agent vs. prior chat, notification vs. custom gate, project vs. ChangeSpec, and artifact
  vs. variable;
- negative prompts that should use a core skill without invoking the gateway;
- prompts that should not use any SASE skill.

Track:

- gateway activation recall;
- correct leaf at top 1 and top 5;
- false-positive gateway activation;
- no-match rate;
- extra tool round trips;
- loaded-leaf use counts; and
- startup catalog characters before and after migration.

## Rollout

1. **Manifest groundwork.** Ship manifest v2 and managed-file inventory with no exposure changes. This establishes a
   safe prior target set for later pruning.
2. **Gateway infrastructure.** Add `skill_bundle`, search/load, the generated catalog snapshot, and
   `/sase_search_skills`, but leave existing leaves top-level while activation evals stabilize.
3. **Low-risk migration.** Move `personal_data`, `sase_artifact_file`, and `sase_var` first. Validate all providers and
   ensure former top-level targets disappear.
4. **Domain migration.** Move `agent_observability`, `project_admin`, and then `sase_gate` after trigger-pair evals pass.
5. **Usage-driven tuning.** Promote a bundled leaf when repeated searches or latency justify direct exposure. Demote a
   top-level leaf only when missing it is recoverable. Keep search lexical until measured misses justify a denser
   retriever.
6. **Optional later seeding.** If a launch prompt explicitly references a bundled `#name`, seed that leaf natively for
   the run. Keep the gateway as the fallback for unpredicted task drift.

The generated-skill memory and deployment documentation must be updated as part of implementation, following the
commit-first-then-deploy workflow. That memory update requires explicit user authorization at implementation time; this
research does not modify memory.

## Risks and mitigations

| Risk                                            | Mitigation                                                                                                    |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Agent never thinks to invoke the gateway        | Broad, front-loaded gateway description; positive/negative activation evals; keep policy-critical skills core |
| Search selects a plausible but wrong leaf       | Weighted full-content lexical search, top-k output, explicit no-match, confusing-pair evals                   |
| Extra search/load round trips                   | Keep frequent skills core; optional high-confidence launch seeding later                                      |
| Loss of native `/leaf` autocomplete             | Preserve `#leaf` xprompt use; expose bundle list/show; document explicit `/sase_search_skills leaf` path      |
| Former leaf remains installed                   | Manifest v2 managed paths and transactional pruning                                                           |
| Checkout injects or changes hidden instructions | Search/load deployed provider snapshot, never the current working tree                                        |
| Provider sees an ineligible leaf                | Generate one filtered catalog per provider and verify again on load                                           |
| Bundle becomes a dumping ground                 | Keep leaf workflows focused; bundles organize discovery, not instruction boundaries                           |
| Search index becomes large                      | Index is read by code, not injected; return only top-k metadata and one loaded body                           |
| Loaded instructions are lost during compaction  | Structured `<skill_content>` wrapper and, where supported, protected/deduplicated activation output           |

## Sources

- [Agent Skills specification](https://agentskills.io/specification)
- [Agent Skills client implementation guide](https://agentskills.io/client-implementation/adding-skills-support)
- [Agent Skills description optimization](https://agentskills.io/skill-creation/optimizing-descriptions)
- [OpenAI: Build skills](https://developers.openai.com/plugins/build/skills)
- [OpenAI/ChatGPT: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Earlier SASE progressive-disclosure research](../xprompt_skill_description_progressive_disclosure.md)

## Recommended solution

Implement `/sase_search_skills` as the **one visible gateway to named, hidden xprompt skill bundles**, backed by
provider-rendered catalog snapshots and deterministic `sase skill search/load` commands. Add a separate scalar
`skill_bundle` frontmatter field, keep the existing `skill` field solely responsible for skill/provider eligibility,
and put bundle schema/search semantics in `sase-core`.

Before moving any leaf, first ship a versioned managed-target manifest so `sase skill init` can safely remove former
top-level files. Then retain `sase_beads`, both commit boundaries, memory read, plan, questions, repo access, and agent
launch as core; migrate the ten audited long-tail skills into `personal_data`, `agent_observability`, `agent_runtime`,
and `project_admin` in measured stages.

This preserves the existing focused leaf workflows and audit trail while changing startup disclosure from
O(all skills) to O(core + 1). It is the most scalable design, the most faithful to Agent Skills progressive disclosure,
and the only option considered that remains uniform across providers without depending on each runtime's truncation or
enable/disable behavior.
