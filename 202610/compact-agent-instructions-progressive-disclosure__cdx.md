# Compact SASE agent instructions: preserve the contract, disclose the catalogs

Researcher: **cdx**  
Date: **2026-10-02**  
SASE checkout examined: `6cca547014bdb14afcaa80db5a772af29f3460aa`  
Linked sase-core checkout examined: `4f0bfd33e70b2a347d555a427f00a47fcc83bd11`

This report was researched independently. No peer report, peer transcript, or peer findings were consulted. Evidence consists of the local implementation, audited SASE memory reads, current official provider documentation, and primary research papers. No instruction files, memory files, or application behavior were changed. The sample below is an illustrative target, not a tested generator output. I did not run a behavioral experiment on SASE agents.

## Decision

**Yes, reduce the always-loaded instructions, but treat 100 lines as a maintainability constraint rather than a proven optimum for agent performance.** The best first implementation is a shorter core template plus an explicit option to render memory webs as compact discovery entries instead of complete descriptors and rosters. SASE already has the needed discovery and audited-read commands.

Keep the few rules an agent must know before its first action in the root instructions. Keep concise, concrete triggers for task-specific memory reads. Leave bodies, catalogs, decision histories, and operational recipes on demand. Do not introduce embeddings, automatic keyword injection, an additional retrieval agent, or a requirement to read one giant replacement handbook at startup.

The largest opportunity is specific and measurable: the root instruction file spends over half its lines on memory webs. Moving catalogs on demand is more consequential than changing Markdown layout.

## What the current implementation actually loads

The root files were measured from their bytes in this checkout. Blank lines count.

| File or section | Lines | UTF-8 bytes | Interpretation |
| --- | ---: | ---: | --- |
| Root `AGENTS.md` | 283 | 17,285 | Canonical generated instructions |
| Core Memory section | 103 | 5,530 | Already exceeds the desired whole-file ceiling |
| Reference Memory section | 33 | 2,071 | Ten useful domain-specific read triggers |
| Memory Webs section | 145 | 9,610 | Main compression opportunity |
| Root title, separator, and section-ending newlines | 2 | 74 | Remaining accounting bytes/lines |
| Each of `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md` | 283 | 17,285 | Verified byte-for-byte equal to `AGENTS.md` |
| `tools/AGENTS.md` | 81 | 5,084 | Already meets the proposed line ceiling |
| `demos/tapes/AGENTS.md` | 4 | 236 | Already meets the proposed line ceiling |

Section bytes above were measured after joining section lines without their final newline; the section byte totals therefore differ slightly from the whole-file total. The Memory Webs section accounts for **51.2% of root lines and approximately 55.6% of root bytes**.

The live inventory reports **24 decision strands, 66 glossary strands, and five task-type strands**. The glossary roster includes aliases, and decision entries include summaries and supersession markers. The bodies of individual strands are deferred, but their catalogs are paid for on every turn. This is real progressive disclosure with a substantial discovery-layer cost.

`sase memory list` reports 4,316 approximate tokens for the project root and 967 for home instructions: **357 combined instruction lines and 5,283 approximate tokens**. Its approximation is `ceil(character_count / 4)`, not a model tokenizer. The inventory deliberately avoids counting inlined memory bodies twice. It inventories instruction files and inferred references; it is not proof of what each provider actually injected. These numbers exclude skill listings, provider/developer instructions, the user prompt, and tool schemas. [Inventory implementation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/inventory.py#L184), [token approximation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/inventory_references.py#L285), [launch evidence caveat](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/docs/memory.md).

### Important implementation constraints

1. **Generated outputs cannot be the authoring surface.** Core notes are rendered into `AGENTS.md`; provider shims are full copies. Generated `sase.md` itself comes from a template. Editing a generated instruction file, or merely changing its wrapping, will be undone at the next initialization. [Core rendering](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/amd/_memory.py#L235), [shim generation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/amd/_shared.py#L158), [shared core template](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/main/init_memory/templates/memory-sase.template.md).

2. **A custom root template cannot currently just omit the web section.** Required template variables and structural checks verify the expected core paths, reference paths, web paths, section anchors, and instruction paragraphs. A compact implementation must change the projection and the corresponding validation together. Hiding an interpolated variable in an HTML comment would still send its content to the model. [Template contract](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/amd/_template.py#L15), [rendered-document validation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/amd/_memory.py#L441), [configuration documentation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/docs/configuration.md#L606).

3. **`roster: inline` and `roster: list` are formatting choices.** Both generate all entries; neither means “do not include the roster in agent context.” Shortening a web descriptor's prose alone therefore leaves the catalog cost. The project needs a genuinely different instruction projection. [Roster renderer](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/web/roster.py#L90).

4. **Discovery already exists.** `sase memory web list -f json` lists collections, and `sase memory web show <web> "<pattern>" -f json` filters a strand index over keywords and aliases. `-b` additionally matches bodies. The default display includes summaries; `-f names` is useful when names alone suffice. The pattern is a positional argument, not a `--pattern` option. Default filtering does not search summaries or bodies, so no keyword match is not proof that no relevant policy exists. Browse the index or use a body-filtered index as a fallback, then audit the selected body read. This eliminates the need to invent a new search service for the present corpus. [Web index handlers](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/web/cli.py#L71).

5. **A bare web read is not a cheap descriptor read.** `sase memory read glossary` selects all glossary strands. The rendering path prints selected strand bodies, not the descriptor's introductory prose. Consequently, hiding a descriptor also hides any operational instructions that existed only in its prose unless they are moved to the short core or another reachable reference note. [Selector resolution](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/selector_web.py#L82), [web read rendering](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/memory/selector_render.py#L225).

6. **Descriptions need attention.** The current web-list JSON has a useful description for `decisions`, but `glossary` and `task_types` have null descriptions. An index-only projection cannot assume every descriptor already has enough routing metadata. The task-type descriptor is generated; update its source template/generation metadata, not its generated output. [Task-type generator](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/main/init_memory/root_rendering_task_types.py#L273), [task-type template](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/src/sase/main/init_memory/templates/memory-sase-task-types.template.md).

## What external research supports, and what it does not

**Current provider guidance supports contextual disclosure.** OpenAI advises short skill descriptions, a minimal router for skills with multiple workflows, and documentation reads tied to the task rather than a stack of prerequisite files before every edit. This supports reducing irrelevant instructions. It is provider guidance, not a measured result for SASE or every model SASE runs. [OpenAI: Rethinking skills and prompts, September 2026](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

**Discovery metadata is itself context.** OpenAI documents loading skill names/descriptions first and complete instructions on selection. It also documents budgeting, shortening, and potentially omitting entries from very large skill lists. Moving every memory into a new skill would shift the catalog burden and could weaken routing. Keep facts and policies in SASE memory; use skills for reusable workflows. [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills).

**Imports do not provide token savings.** Anthropic recommends keeping instruction files below 200 lines, moving scoped procedures to skills or path-specific rules, and warns that imported files still load at launch. Its context-engineering guidance also says sufficient concrete information must remain available; minimum useful context is not necessarily the shortest possible prompt. Neither source establishes 100 lines as an empirical threshold. [Claude Code memory](https://code.claude.com/docs/en/memory), [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

**Empirical findings are mixed, and length alone is a weak proxy.** Gloaguen et al.'s latest revision, dated September 29, 2026, finds no general task-success improvement from repository context files and over 20% average inference-cost growth. Crucially, it finds no clear dependency between context-file length and success or cost; additional prescribed exploration/testing helps explain cost. Its main evaluation focuses on Python task resolution, not all organizational policy compliance. This argues for reducing unnecessary obligations and measuring behavior, rather than promising that a shorter file will automatically improve accuracy. [Evaluating AGENTS.md, v3](https://arxiv.org/html/2602.11988v3).

**There is also positive efficiency evidence.** Lulla et al. study 124 pull requests across ten repositories and report 28.64% lower median runtime and 16.58% lower median output tokens with instruction files. Their paper explicitly leaves correctness and alignment evaluation to future work; median total tokens were slightly higher. This does not justify deleting all instructions or equating fewer tokens with correct work. [On the Impact of AGENTS.md Files, v2](https://arxiv.org/html/2601.20404v2).

**Provider loading behavior differs.** Codex documents a root-to-working-directory discovery chain and a default 32 KiB project-document ceiling. Claude documents different nested-file loading and instruction-file selection rules. A root-launched agent editing a deep path cannot be assumed to receive that path's instructions in every provider. Keep critical cross-cutting boundaries at the root, and verify actual adapter behavior before relying on nested files or changing shim delivery. [Codex AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude Code memory](https://code.claude.com/docs/en/memory).

## Critique and justified requirement adjustments

The objective is good: smaller startup instructions are easier to review, less likely to conflict, and leave room for task evidence. SASE's domain boundaries, audited reads, and progressive memory already make this feasible.

The main risk is **making necessary context harder to obtain**. A short prompt can appear efficient while an agent misses an obscure rule, repeatedly searches the same index, or loads the complete memory corpus to compensate. Rules required before an action must be discoverable before that action. A repository-access rule buried behind a repository-access read is circular. A finalization rule found only after finalizing is too late.

I recommend these explicit adjustments:

| Requested or implied requirement | Adjustment | Reason |
| --- | --- | --- |
| Instruction files at most 100 lines | Count the final formatted files, including blank lines; preserve readable wrapping and also track characters/bytes/tokens | Prevents meeting the ceiling with enormous physical lines |
| One size target determines success | Add no-regression checks for completion and critical SASE rules, plus whole-run cost/latency | Shorter files are not a behavioral guarantee |
| Reduce “this project's files” | Start with the root and its generated shims; retain the already-small nested files; measure home plus project together | The launch context includes more than the root file |
| Everything beyond the ceiling is deferred | Keep small pre-action reminders always loaded, even when they repeat a skill trigger | The agent needs to know when disclosure is required |
| Progressive disclosure means references everywhere | Keep one useful trigger/path per flat reference and one purpose/selector route per web | A hidden corpus without routing information is ineffective |
| This should simplify the memory system | Preserve note kinds, web/strand semantics, audited reads, aliases, and authored links | A compression project should not become a retrieval rewrite |
| Savings follow automatically from moving text | Evaluate full task traces, including retrieval output and additional reasoning/tool calls | Startup savings can be spent again during retrieval |

**Proposed starting budgets:** root and provider copies at most 100 formatted lines and roughly 2,000 approximate tokens, with a roughly 3,000-token target for the combined home-plus-project instruction chain. These are engineering targets to evaluate, not scientific thresholds. Keep a documented exception path when an essential invariant cannot be expressed adequately inside the budget. Aim around 70–85 root lines so ordinary growth does not immediately break the ceiling.

Do not replace the line ceiling with a giant mandatory “read this first” reference. That leaves effective startup content largely unchanged and adds a retrieval step. Likewise, do not assume prompt caching makes irrelevant instructions free: monetary savings, input-token savings, and quality effects are different measurements.

### What stays always loaded

- The single-turn lifecycle, finishing live commands, monitor routing, and final-declaration reminder.
- The repository-opening boundary across local and web transports, and audited sidecar artifact reads.
- The audited-memory-read route and authorization route for memory changes.
- The Rust backend boundary, binding/pin consequence, and the default-keymap gotcha.
- Concrete read triggers for the existing ten top-level reference notes.
- A short instruction to resolve SASE terminology through the glossary.
- The duty to record discovered follow-up work through `/sase_new_task`, including the prompt's exception. This currently lives inside the generated task-type descriptor and must not disappear when that descriptor stops inlining.

Detailed recipes and historical rationale belong in existing skills, reference notes, and strands. Do not add a note merely to restate a skill already doing the job. Retain task-type details in the generated catalog; consult its live CLI when filing.

## Recommended implementation design

### A narrow, explicit web projection

Introduce a **proposed** root-scoped configuration choice such as:

```yaml
memory:
  web_context: index  # Proposed field; not accepted by today's schema.
```

Values would be `full` and `index`; keep `full` as the compatibility default initially and opt this project into `index` after migrating its descriptors' operational instructions. This is a persistent user preference, so use ordinary configuration rather than a permanent feature flag. If an implementation epic exposes unfinished behavior, apply SASE's temporary-flag policy separately.

In index mode, keep the existing `Memory Webs` section and per-web heading identity, but emit a short description and a common index/read route. Do not inline descriptor bodies or strand rosters. Use existing descriptor `description` metadata; add useful descriptions where missing. Reject an opted-in compact generation if required routing metadata is absent instead of silently dropping a collection. The source descriptors, rosters, strands, and human browsing surfaces remain intact.

This is not a new `type:` for webs. It is a scoped instruction-rendering choice, separate from a collection's kind and from its roster's display style. Keep `roster: inline/list` unchanged.

A descriptor-body review must accompany enabling index mode. Move mandatory directives to a concise core reminder or an existing reachable reference note before suppressing that body. For this project, that includes the glossary-reading trigger and the task-follow-up rule. Pure descriptor explanation can remain human-facing. Any substantive policy that agents still need must have an explicit reachable destination; bare-web reads do not provide a descriptor-only escape hatch.

The audited decision `decisions:webs-render-in-their-own-section` explicitly names unconditional descriptor cost and allows reconsideration when it becomes a token-budget problem. This checkout is concrete evidence for reopening that narrow condition. Add a superseding decision as appropriate; do not rewrite an accepted decision's rationale in place. `decisions:corpus-before-mechanism` argues against speculative retrieval, and the existing filterable indexes meet this corpus's immediate needs. [Existing decisions](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/sase/memory/decisions/webs-render-in-their-own-section.md), [corpus-first decision](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/sase/memory/decisions/corpus-before-mechanism.md).

### Shorten the shared core at its source

Rewrite the packaged `memory-sase.template.md` around direct pre-action rules. Remove the repeated explanation of memory storage shapes, catalog enumeration, lengthy repository transport examples, and background prose. Retain one concise statement of each contract. Move any still-needed procedural detail into the existing `sase_repo`, `sase_memory_read`, `sase_memory_write`, `sase_monitor`, and `sase_final` skills.

Replace the always-loaded linked-repo catalog with the existing `sase repo list` discovery route where that catalog consumes space. Preserve immediately relevant architecture names, such as `sase-core`, in the specific boundary rule. A template's required placeholders should be deliberately revised when a catalog is no longer rendered; do not defeat validation with hidden text.

Shorten reference descriptions without removing their action-specific triggers. Keep generated sources authoritative. Skill source edits, if needed, belong under `src/sase/xprompts/skills/`; deployment follows the project's land-before-deploy rule. This research does not authorize changing global deployed skills or home instructions as a side effect.

### Respect the backend boundary

The Rust core must own new shared deterministic disclosure policy and validation, including the selected projection's coverage and budget facts that other frontends need to agree on. Expose the needed wire API through `sase_core_rs`; Python can assemble filesystem inputs, render Markdown, and update generated outputs.

The existing memory discovery/rendering is largely Python today. Do not turn this work into a wholesale port of that subsystem. Feed existing discovered metadata into a small Rust-owned projection/validation contract, then keep the Python adapters thin. A new binding requires the matching core commit to be included by `sase-core-revision.txt`. Pure template wording changes do not themselves require a new Rust API. [SASE boundary documentation](https://github.com/sase-org/sase/blob/6cca547014bdb14afcaa80db5a772af29f3460aa/docs/rust_backend.md), [sase-core instructions](https://github.com/sase-org/sase-core/blob/4f0bfd33e70b2a347d555a427f00a47fcc83bd11/AGENTS.md).

### Illustrative target: 70 lines

The following sample is **70 lines, 3,416 UTF-8 bytes, and 854 approximate tokens** using SASE's character-count heuristic. Its longest line has 86 characters. It preserves the current ten reference-note triggers and three web entry points. It requires the generation and validation changes above; it has not been run through SASE initialization or its formatter.

Compared with the current root's 4,316-token estimate, it removes roughly 80% of the root instruction text. With the currently reported home estimate unchanged, the combined estimate would be approximately 1,821 tokens rather than 5,283. These are static-text projections, not measured provider usage or promised cost savings.

```markdown
# SASE — Agent Instructions

## 1. Core Memory

### 1.1 SASE (sase)

- Work in the assigned workspace. Keep plans portable with repo-relative paths.
- A SASE agent runs for one turn. Finish and inspect commands you start.
  Never end a turn while a handoff command itself is still running.
- Use /sase_monitor for long commands and waits; nothing wakes an ended turn.
- Use /sase_final as the last action before a normal final response.
  Successful plan, monitor, pipe, or questions handoffs are exempt.
- Before accessing another repo through any transport, use /sase_repo.
  Read and write only the checkout path it prints; inspect that repo's AGENTS.md.
- Read sidecar artifacts with sase artifact read <ref> "<reason>".
- Consult reference memory with /sase_memory_read, using audited
  sase memory read <selector> [...] -r "<reason>"; batch relevant selectors.
  Do not open canonical reference-memory files directly.
- Use /sase_memory_write before memory changes or plans that change memory.
  AGENTS.md and provider shims are generated; change canonical sources.
- Capture discovered follow-up work through /sase_new_task unless forbidden
  by the prompt. Read bead rules before querying or changing beads.

### 1.2 Code Conventions and Gotchas (gotchas)

When changing keymaps or config defaults, update src/sase/default_config.yml.

### 1.3 Rust Core Backend Boundary (rust_core_backend_boundary)

Shared domain behavior belongs in sase-core; open it through /sase_repo.
Python/TUI callers use sase_core_rs or thin adapters. Changes to bindings need
sase-core-revision.txt advanced past the corresponding core commit.

## 2. Reference Memory

Read the applicable note before the indicated work with /sase_memory_read:

1. **`sase/memory/cli_rules.md`** - before adding CLI commands or options.
2. **`sase/memory/dispatch.md`** - before remote agent dispatch.
3. **`sase/memory/generated_skills.md`** - when working on SASE agent skills.
4. **`sase/memory/lint_and_test.md`** - before finishing with tracked SASE changes
   (excluding separate repositories under sase/repos/).
5. **`sase/memory/sase_artifacts.md`** - before artifact workflows.
6. **`sase/memory/sase_beads.md`** - before querying or changing beads.
7. **`sase/memory/sase_flags.md`** - before feature flags or compatibility changes.
8. **`sase/memory/symvision.md`** - before fixing Symvision lint failures.
9. **`sase/memory/tui.md`** - before TUI, screenshot, or UI performance changes.
10. **`sase/memory/xprompts.md`** - before xprompts, directives, or VCS launch blocks.

## 3. Memory Webs

Find relevant strands with sase memory web show <web> "<pattern>" -f json.
Read selected bodies with sase memory read <web>:<keyword> [...] -r "<reason>".
Omit the pattern to inspect an index. A bare web read loads every strand;
use it only when the entire collection is needed.

### 3.1 Decisions (decisions)

Before changing an architectural policy, find and read the relevant decisions.
Accepted records state alternatives, costs, and conditions for revisiting them.

### 3.2 Glossary Terms (glossary)

Before relying on SASE-specific terms, find and read their definitions.
Batch needed terms; the read command includes linked dependencies.

### 3.3 Task Bead Types (task_types)

Before filing discovered work, use /sase_new_task and the live task-type catalog.
Use sase bead task-type list and task_types:<slug> for the selected type.
```

The sample deliberately retains all three managed section anchors and the source-identifying core/web headings. Numbering, path coverage, and the exact introductory paragraphs still need coordinated validator changes; maintaining familiar headings alone does not make it a drop-in template.

### Why this approach beats the alternatives

| Approach | Assessment |
| --- | --- |
| Editorial shortening only | Useful first step, but rosters remain automatic and web catalogs still grow with every new strand |
| Index projection plus shorter core | Best fit: removes the measured catalog cost and reuses existing discovery/auditing |
| Group all reference notes under a new mandatory hub | Saves root rows but adds a retrieval dependency; unnecessary with only ten root references |
| Put all facts/policies in skills | Moves the discovery burden into another always-loaded catalog and duplicates memory |
| Use nested instruction files for every domain | Useful for local tooling rules, but provider loading differs and cross-cutting concerns do not fit one directory |
| Automatically inject memory based on prompt keywords | Creates relevance misses, maintenance work, and a new mechanism despite an adequate existing index |
| Hard-truncate or token-pack existing output | Risks dropping essential rules and games the metric |
| Replace provider copies with tiny imports | Organization change, not true context reduction; also changes a deliberate compatibility contract |

## Validation and rollout

Do the rollout in a sequence that keeps artifacts reviewable:

1. Record the current root/shim, home, and representative launch-context budgets. Classify each instruction as a pre-action invariant, a task trigger, a procedure, a catalog entry, or removable repetition.
2. Review and prepare the source changes together: shorter core template, descriptor summaries, relocation of descriptor-only mandatory rules, and the explicit index projection with matching validation. Keep full rendering available through configuration.
3. Add meaningful generator tests: index mode has every web's identity and description; full mode retains full descriptors; no strand roster leaks into index mode; core and reference coverage stays complete; missing summaries fail before writes; initialization remains idempotent; provider copies remain equal; home/project overlays and custom templates work.
4. Check the **formatted** instruction budget, including blank lines. Keep this as an assertion for this project's opted-in output rather than automatically truncating other projects. Update inventory semantics so a web's routing summary does not misleadingly claim its entire descriptor body was loaded.
5. Compare baseline and candidate instructions on a small representative task suite across the provider adapters and model classes actually used. Start with multiple repetitions per task; expand the suite if results are noisy. Do not treat a handful of runs as proof of rare-error safety.
6. Adopt index mode for this project after the pilot passes. Home already meets the line ceiling; revisit its duplicated shared prose as a separate, explicitly scoped optimization if the aggregate budget remains too high.

Suggested behavioral scenarios include a simple typo, keymap/default change, Rust-owned feature, linked-repo read, research artifact read/write, memory-policy proposal, bead query/creation, CLI option addition, TUI change, xprompt/skill edit, long-command handoff, and an incomplete task that still needs final declaration. Include ambiguous glossary aliases and a task with no relevant decision so agents are not rewarded for reflexively reading everything.

Score outcomes and process separately. Did the task complete correctly? Did the agent obtain the required rule before acting? Did it use the audited access route and finalizer? How many irrelevant notes or full-web reads occurred? Measure elapsed time, tool calls, cache-aware input usage, retrieval output, and total tokens. Missing a critical lifecycle or authorization rule in any pilot run is a reason to revise the candidate before adoption. Static savings alone are insufficient. [OpenAI's skill-evaluation approach](https://developers.openai.com/blog/eval-skills).

There is no need for a new evaluator service in the first implementation. Use deterministic checks for generator contracts and captured traces for behavior, following SASE's normal checked-tool workflow. The initial research has not run these tests because it changes only this report.

## Recommended solution

**Implement a shorter generated core and an opt-in, index-only projection of memory webs, using SASE's existing filterable indexes and audited selector reads. Target 70–85 readable root lines, enforce the requested 100-line ceiling after formatting, and measure the full instruction chain plus task outcomes.**

Retain pre-action invariants and the current reference triggers; remove always-loaded catalogs and explanations. Move descriptor-only mandatory rules before suppressing descriptors. Keep memory kinds, rosters, audit semantics, and provider copies stable. Put new shared policy/validation in sase-core and update the binding pin as needed. Reopen the specific always-inline-web decision using the measured corpus, without reviving speculative dynamic memory. Adopt the compact configuration only after the pilot confirms that instruction discovery and completion remain reliable.
