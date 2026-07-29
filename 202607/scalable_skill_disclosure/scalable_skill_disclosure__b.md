---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# Skill Bundles and a `/sase_search_skills` Meta-Skill

## Question

Every xprompt skill's `description` is injected into every agent's context, for every run. Can we introduce **skill
bundles** — author-defined groups whose members are hidden behind a single always-listed entry — plus a
`/sase_search_skills` meta-skill, so the skill catalog can grow without a matching growth in per-agent context? What is
the best shape for that mechanism, and which of today's 18 skills are good bundle candidates?

**Short answer: yes — and the right unit of deferral is the bundle, not a single global search skill.** Make the bundle
the thing that stays in the Level-1 listing (a domain-level trigger the model can actually match), hide its members at
Level 2, and ship `/sase_search_skills` as the cross-bundle safety net and the retrieval verb the bundle bodies delegate
to. Of today's 18 skills, **6 must stay pinned, 11 are sound bundle members across 3 bundles, and 1 is broken and
deploys nowhere.** Bundling today's set cuts the Level-1 listing by ~33% (~43% with one free description trim), but the
real payoff is the derivative: skill #19 onward costs ~0 instead of ~170 characters.

This report supersedes the recommendation in
[`xprompt_skill_description_progressive_disclosure.md`](../xprompt_skill_description_progressive_disclosure.md)
(2026-07-07), which proposed a flat two-tier catalog behind one `sase_skill_find` skill. That report's analysis of
runtime budgets and prior art still holds; what changed is (a) new evidence about how the deferral unit affects recall,
and (b) three verified facts about the current tree and the Claude runtime that were not in scope then. None of its
Phase 1 was implemented — this is still greenfield.

## 1. Verified current state (2026-07-29)

### The catalog

`sase skill list` reports **18 sources → 5 providers → 85 generated targets** (70 current, 15 stale), deployed via
chezmoi. Sixteen sources live in `src/sase/xprompts/skills/`; `bob_query` and `sase_gmail` come from Bryan's
chezmoi-managed `~/sase/xprompts/`, which matters — the growth vector for "infinite skills" is user-authored xprompts
outside this repo, so any bundle mechanism must reach them.

The skill frontmatter surface is still exactly two keys — `skill: bool | list[str]` and `log_skill_use: bool`
(`src/sase/xprompt/models.py:176-177`, schema `src/sase/config/sase.schema.json`). Selection is a one-line filter:
`select_skill_xprompts()` in `src/sase/main/_init_skills_sources.py` returns every xprompt where `xp.skill` is truthy.
There is no tiering, no per-run filtering, and no search. The `sase skill` CLI group is `{init, list, log, use}`
(`src/sase/main/parser_skills.py`).

### The measured cost

Measured over the 17 deployed `~/.claude/skills/*/SKILL.md` files:

| Level                       | Size            | Notes                                                     |
| :-------------------------- | :-------------- | :-------------------------------------------------------- |
| Level 1 (names + `description`) | **2,900 chars ≈ 725 tokens** | Paid by every agent, every run                |
| Level 2 (SKILL.md bodies)   | 72,980 chars ≈ 18,245 tokens | Free until invoked                           |

Claude Code's skill-listing budget defaults to **1% of the context window** (~8,000 chars on a 200k model), so we sit at
**36% of budget**. Codex allots 2% or 8,000 chars. Neither is close to overflow. Average marginal cost per skill today
is **~170 chars**; roughly 30 more average skills would hit Claude's default cliff, at which point Claude starts
*silently* dropping descriptions for the least-invoked skills and Codex silently omits skills entirely. The problem is
prospective, and the failure mode is invisible — that is the case for building this now rather than after it hurts.

### The usage distribution (`sase skill log`, 4,138 uses / 1,956 agents)

| Skill                | Uses  |     % | Cum %  | Distinct agents | Last used  |
| :------------------- | ----: | ----: | -----: | --------------: | :--------- |
| `sase_git_commit`    | 1,825 | 44.1% |  44.1% |           1,758 | 2026-07-29 |
| `sase_beads`         | 1,688 | 40.8% |  84.9% |             882 | 2026-07-29 |
| `sase_repo`          |   121 |  2.9% |  87.8% |             115 | 2026-07-28 |
| `sase_memory_read`   |    85 |  2.1% |  89.9% |              78 | 2026-07-28 |
| `sase_chats`         |    74 |  1.8% |  91.7% |              66 | 2026-07-28 |
| `sase_questions`     |    70 |  1.7% |  93.4% |              33 | 2026-07-29 |
| `sase_changespecs`   |    58 |  1.4% |  94.8% |              51 | 2026-07-29 |
| `sase_agents_status` |    53 |  1.3% |  96.0% |              42 | 2026-07-28 |
| `sase_var`           |    45 |  1.1% |  97.1% |              44 | 2026-07-28 |
| `sase_project`       |    31 |  0.7% |  97.9% |              31 | 2026-07-28 |
| `sase_plan`          |    29 |  0.7% |  98.6% |              28 | 2026-07-28 |
| `sase_run`           |    19 |  0.5% |  99.0% |              17 | 2026-07-23 |
| `sase_notify`        |    15 |  0.4% |  99.4% |              14 | 2026-07-28 |
| `bob_query`          |     9 |  0.2% |  99.6% |               9 | 2026-07-28 |
| `sase_gate`          |     8 |  0.2% |  99.8% |               7 | 2026-07-28 |
| `sase_artifact_file` |     6 |  0.1% | 100.0% |               6 | 2026-07-28 |
| `sase_artifact`      |     2 |  0.0% | 100.0% |               2 | 2026-07-17 |

Two skills are 85% of all invocations; the remaining fifteen share 15%. `sase_gmail` has never been used. (`sase_var`,
`sase_artifact_file`, and `sase_gate` carry `log_skill_use: true`, so these are true counts; `sase_repo`,
`sase_memory_read`, and `sase_plan` carry `log_skill_use: false` yet still appear, so their counts come from an earlier
period and are **under-reported** — treat them as lower bounds. `sase_artifact` is a retired name.)

The long tail is real. But **frequency is the wrong primary axis for tiering** — see §3.

### Three findings worth acting on independently

1. **`sase_hg_commit` still deploys nowhere.** It declares `skill: [gemini]`, but the registered providers are `agy`,
   `claude`, `codex`, `fakey`, `opencode`, `qwen`. `sase skill list` shows `–` providers and `–` status for it. This was
   flagged in the 2026-07-07 report and is unfixed three weeks later. It is a one-line fix (`[agy]`) and is orthogonal
   to bundles.
2. **`sase_repo`'s description is the single largest Level-1 line item at 419 chars** — 14% of the whole listing — and it
   restates, nearly verbatim, a rule that is already in Tier-1 memory (`CLAUDE.md` / `AGENTS.md`, which every agent
   loads). Trimming it to a ~120-char pointer saves ~300 chars with no mechanism at all: a 10% cut for a one-line edit.
3. **`sase skill use` validates nothing about deployment** (`src/sase/skills/cli_use.py` just normalizes the name), so
   bundled, undeployed skills remain fully auditable under the existing log. The telemetry loop survives bundling
   unchanged.

## 2. What the runtimes give us (and the trap in the obvious shortcut)

All five providers implement the [Agent Skills](https://agentskills.io) standard's three-level progressive disclosure:
Level 1 = name + description (always loaded), Level 2 = SKILL.md body (on activation), Level 3 = referenced files. Level
2 and 3 are already free. **Level 1 is the entire problem**, and no runtime defers it: Claude, Codex, and Gemini CLI all
inject every enabled skill's description at session start, differing only in how they degrade at the cliff.

Claude Code offers three relevant knobs today:

- **`skillOverrides`** in settings, with states `"on"`, `"name-only"`, `"user-invocable-only"`, `"off"`. Writable from
  the `/skills` menu.
- **`skillListingBudgetFraction`** / `SLASH_COMMAND_TOOL_CHAR_BUDGET` / `skillListingMaxDescChars` (per-entry cap 1,536
  chars).
- **Frontmatter `disable-model-invocation: true`** and **`user-invocable: false`**.

### The trap

`disable-model-invocation: true` looks like a free win. Claude's own table is explicit:

| Frontmatter                      | You can invoke | Claude can invoke | When loaded into context                                     |
| :------------------------------- | :------------- | :---------------- | :----------------------------------------------------------- |
| (default)                        | Yes            | Yes               | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes            | No                | **Description not in context**, full skill loads when you invoke |
| `user-invocable: false`          | No             | Yes               | Description always in context, full skill loads when invoked |

So a "typed-only" tier costs **zero** Level-1 context while keeping `/name` autocomplete. Tempting for
`sase_git_commit` (245 chars, and its own description exists mainly to tell the model *not* to use it).

**It does not work here.** The docs are equally explicit that `disable-model-invocation: true` blocks the **Skill tool**,
not just the `/` menu ("The `user-invocable` field only controls menu visibility, not Skill tool access. Use
`disable-model-invocation: true` to block programmatic invocation."). But `sase_git_commit` is invoked *by the agent*,
prompted by the commit finalizer — `src/sase/llm_provider/commit_finalizer_prompting.py:76` literally tells the agent to
use "your `/sase_git_commit` skill". Setting the flag would break 44% of all skill traffic.

Applying the same test across the catalog: **no skill in the current set qualifies for a typed-only tier.** Even
`bob_query`, which looks like a purely human-typed personal tool, has 9 agent-driven uses (e.g. `research.n.final`
verifying a task ledger). This is a useful negative result — it removes the attractive shortcut and justifies building a
real mechanism. Keep the lever documented for future skills that genuinely only Bryan ever types; it is a per-provider
*rendering* of a sase-level `invocation: user-only` concept, with bundling as the uniform fallback for runtimes that
lack the flag, so it does not violate the uniform-runtimes rule.

Two other Claude mechanisms are worth knowing but not building on: **nested `.claude/skills/`** directories load lazily
when Claude touches a file in that subtree and get directory-qualified names (`apps/web:deploy`) — genuine native
progressive disclosure, but keyed on filesystem locality rather than topic, and Claude-only. **Plugin skills** are
namespaced `plugin:skill` and exempt from `skillOverrides` — Claude's closest thing to a native bundle, but plugin skill
descriptions are still listed in full, so it buys namespacing, not context. Note also that Claude Code already uses
"bundled skills" to mean its own built-ins (`/debug`, `/code-review`); the vocabulary collides, so keep "bundle" in
sase's user-facing language but never let the word leak into generated descriptions.

### Prior art

The 2025–2026 literature has converged on retrieval over flat listing, and — importantly for this design — on **grouped**
retrieval specifically:

- [SkillFlow](https://arxiv.org/html/2504.06188) finds description-only selection inaccurate at scale; moves to BM25 +
  dense retrieval + rerank over full skill content.
- [Group of Skills (GoSkills)](https://arxiv.org/abs/2605.06978) changes "the agent-facing retrieval object from a flat
  skill list to a compact, role-labeled execution context" built from anchor-centered skill groups.
- [Graph-of-Skills](https://arxiv.org/abs/2604.05333) retrieves a bounded, dependency-aware **"skill bundle"** — the same
  word, though there it names a retrieval-time result set rather than an authoring-time group. On SkillsBench with
  GPT-5.2 Codex it reports **+25.55% peak reward and −56.72% total tokens** versus loading all skills, consistent across
  libraries of 200–2,000 skills.

The consistent finding: group structure beats flat lists, and it beats them on *accuracy*, not just tokens.

## 3. The design question that actually matters

Not "should we defer?" — the answer is yes — but **what is the always-listed unit?**

- **One global search skill** (the 2026-07-07 recommendation): Level-1 cost is O(1), the theoretical optimum. Its known
  weakness is *discoverability inversion* — the model must think to search, and a generic "search the extended skill
  catalog" description has poor semantic overlap with any concrete task. Recall depends on agent diligence, which is
  exactly the variable we cannot control.
- **One entry per bundle**: Level-1 cost is O(#bundles). A description like "Inspect SASE's own state: running agents,
  prior chats, notifications, ChangeSpecs, projects" has *real* semantic overlap with "what did agent X say?". The model
  matches a domain, then reads an index. Native `/bundle-name` invocation survives.

Bundles cost more than a lone search skill and buy back the thing that breaks silently. #bundles grows with *domains*,
not skills, so it is effectively bounded in practice even though it is formally sub-linear.

One honest caveat: the compression is real but not unlimited. If a bundle description has to enumerate every member's
trigger phrases, it saves nothing. The saving comes from the bundle description carrying **domain-level** triggers while
per-member detail moves to the (free) body. Empirically, §4 gets ~4.5x compression on the strongest group.

**Corollary for the audit rubric:** frequency is not the primary axis. The right question is whether a skill is
*prohibitive* or *permissive*:

- A **prohibitive** skill exists to stop the agent doing the wrong thing by default (`sase_repo`: never web-fetch a
  repo; `sase_git_commit`: never raw `git commit`). If the agent never sees it, it does the wrong thing and *never
  learns it was wrong*. These must stay pinned regardless of frequency — `sase_repo` is only 2.9% of uses.
- A **permissive** skill helps once the agent already knows what it wants (`sase_chats`, `sase_notify`). Deferral is
  safe; worst case is one extra hop.

Secondary axes: is it **demand-triggered by an explicit user question** (the user's own words then serve as the
retrieval query — bundling is nearly free)? Is it **named by machinery or launch prompts** (invoked by name, not
discovered — bundling is free, but check the invocation path still resolves)? Frequency is a tiebreaker: hot skills
should be pinned because the extra hop is paid often.

## 4. Audit of the existing catalog

### Tier P — Pinned (stay individually listed): 6 skills, 1,108 desc chars

| Skill              | Uses  | Chars | Why it cannot be bundled                                                              |
| :----------------- | ----: | ----: | :------------------------------------------------------------------------------------ |
| `sase_git_commit`  | 1,825 |   245 | Machinery-invoked (`commit_finalizer_prompting.py:76`); prohibitive; 44% of traffic     |
| `sase_beads`       | 1,688 |   118 | 41% of traffic; hot path; already the cheapest description per use in the catalog       |
| `sase_repo`        |   121 |   419 | **Prohibitive** — enforces a Tier-1 MUST; failing to fire is silent and wrong           |
| `sase_memory_read` |    85 |   175 | Gate for all Tier-2 memory reads; named by `amd/templates/AGENTS.template.md`           |
| `sase_questions`   |    70 |    75 | Replaces a disabled native tool — an agent that doesn't know it exists cannot ask       |
| `sase_plan`        |    29 |    76 | Replaces disabled plan mode; named by memory templates and plan machinery               |

The bottom four are cheap (75–419 chars) and structurally load-bearing. Only `sase_repo` is worth editing — trim its
description to a pointer at the Tier-1 rule (−~300 chars).

### Tier B — Bundle candidates: 11 skills, 1,590 desc chars → ~540

**Bundle A — `sase_introspect` (SASE state and history, read-only) — 5 members, 1,035 → ~230 chars (4.5x)**

| Member               | Uses | Chars |
| :------------------- | ---: | ----: |
| `sase_chats`         |   74 |   255 |
| `sase_project`       |   31 |   251 |
| `sase_notify`        |   15 |   223 |
| `sase_agents_status` |   53 |   161 |
| `sase_changespecs`   |   58 |   145 |

The flagship bundle: highest cohesion, highest saving, lowest risk. Every member is permissive, read-only, and
demand-triggered by an explicit user question ("what's running?", "what did agent X say?", "PR status?", "which projects
are enabled?"). Because the user supplies a concrete query, the retrieval hop is nearly free and the domain-level
description matches strongly. If only one bundle ships, ship this one.

**Bundle B — `sase_agent_io` (what a run emits, gates, and launches) — 4 members, 429 → ~200 chars (2.1x)**

| Member               | Uses | Chars |
| :------------------- | ---: | ----: |
| `sase_gate`          |    8 |   224 |
| `sase_run`           |   19 |    80 |
| `sase_artifact_file` |    6 |    65 |
| `sase_var`           |   45 |    60 |

Weaker cohesion and a modest saving; include it, but with two caveats. `sase_gate` is semi-prohibitive — it is "the easy
way" to propose dangerous commands, and if it never fires the agent falls back to asking plainly, which is degraded but
not harmful. `sase_var` and `sase_artifact_file` are nearly always named by the launching xprompt rather than
discovered, so deferral costs them almost nothing. An alternative split (move `sase_run` next to `sase_agents_status` in
an "agents" bundle) is defensible, but at 17 skills more than three bundles starts inverting the savings.

**Bundle C — `bryan_personal` (non-SASE personal integrations) — 2 members, 126 → ~110 chars (1.1x)**

| Member       | Uses | Chars |
| :----------- | ---: | ----: |
| `bob_query`  |    9 |    82 |
| `sase_gmail` |    0 |    44 |

Near-zero saving today — include it anyway, for two reasons. It is the **proof case for user-authored bundles** sourced
from `~/sase/xprompts/` rather than this repo, which is where the catalog will actually grow. And it is the sharpest
instance of "not ideal for all skills": essentially every coding agent in this repo pays for Gmail and Obsidian
descriptions it will never use. (These two also looked like ideal typed-only candidates until the telemetry showed
agent-driven `bob_query` use — see §2.)

### Tier X — Fix, do not bundle

`sase_hg_commit` — `skill: [gemini]` resolves to no registered provider, so it deploys nowhere. Fix to `[agy]`
independently. Commit skills are resolved by name from machinery and should never be bundle members.

### Net effect

| State                                   | Level-1 chars | Δ    |
| :-------------------------------------- | ------------: | :--- |
| Today                                   |         2,900 | —    |
| 6 pinned + 3 bundles + `/sase_search_skills` |    ~1,950 | −33% |
| …plus the `sase_repo` description trim  |        ~1,650 | −43% |
| Marginal cost of skill #19 (bundled)    |            ~0 | vs ~170 today |

The one-third cut is nice; the last row is the point.

## 5. Recommended solution

**Adopt bundles as the always-listed unit, with `/sase_search_skills` as the cross-bundle fallback and the retrieval
verb.** Six components:

### 5.1 `bundle:` frontmatter, plus a config-level override

Add `bundle: <name>` to the skill xprompt frontmatter (schema `sase.schema.json`, model `XPrompt` in
`src/sase/xprompt/models.py`). A skill with `bundle:` set is rendered and indexed but **not** deployed to provider skill
directories; `select_skill_xprompts()` in `_init_skills_sources.py` gains that filter. A skill without `bundle:` keeps
today's behavior exactly — pinned is the default, so this change is additive and back-compatible.

Also support a `skill_bundles:` map in `~/.config/sase/sase.yml` that assigns skills to bundles **without editing their
source**. This mirrors Claude's rationale for `skillOverrides` ("for skills whose SKILL.md you don't want to edit") and
is required for Bundle C, whose members live in chezmoi, and for any future third-party skill source.

### 5.2 Bundle definitions

A bundle is a new xprompt kind under `src/sase/xprompts/bundles/<name>.md` (or a config entry), carrying a `description`
— the domain-level trigger, the one piece of text that must be written well — and an optional body preamble.

### 5.3 Generated bundle skills

`sase skill init` emits **one SKILL.md per bundle**, reusing the existing `_render_skill` / `_build_output` /
`SKILL.frame.template.md` pipeline. The body is auto-generated: the preamble, then a member table (name + full
description + how to load), then the `sase skill show <member>` instruction. Member descriptions live at Level 2, so
they are free until the bundle fires.

**Inline threshold.** If a bundle's total member body size is under a threshold (~6 KB is a reasonable start), inline
the member bodies directly into the bundle SKILL.md and skip the second hop entirely. Bundle C qualifies (1.2 KB + 2.2
KB); Bundle A does not (~22 KB). This makes small bundles strictly free relative to today — one hop, not two.

### 5.4 `sase skill search` and `sase skill show`

- `sase skill search <query>` — lexical (BM25/keyword) retrieval over name + description + **body** of every skill,
  pinned and bundled alike. SkillFlow's finding is that description-only matching is the thing that fails at scale, so
  index bodies from day one. Returns ranked matches with ready-to-run `sase skill show` commands. Add embeddings later
  only if the log shows keyword search missing.
- `sase skill show <name>` — prints the fully rendered SKILL.md body for the invoking provider **and records the use in
  the existing audit log automatically**. This is a strict improvement over today's self-reported `sase skill use`
  directive, which an agent can skip; for bundled skills, retrieval and audit become the same action.

### 5.5 The `/sase_search_skills` skill

One generated skill whose body says: run `sase skill search "<what you need>"`, then `sase skill show <name>` on the
best match. It serves two roles — the safety net when no bundle description matched, and the verb the bundle bodies
delegate to for non-inlined members.

On naming: `/sase_skills` is shorter, reads as a noun, and is the natural sibling of the `sase skill` CLI group.
`/sase_search_skills` is fine and unambiguous; your call.

### 5.6 The feedback loop

Extend `sase skill list` to group by bundle and report Level-1 char cost per tier, so the budget is visible. Use `sase
skill log` for tiering decisions: promote a bundled skill to pinned when its use count justifies the hop, demote a cold
pinned skill into a bundle. Add a counter for searches that return nothing — that is the signal that a description or a
bundle boundary is wrong. This is why the mechanism should degrade *loudly*: a failed search is observable, whereas
Claude silently truncating descriptions is not.

### Rust core boundary

The **catalog model** (tier resolution, bundle membership, search) is domain behavior a web UI, the ACE TUI, or an
editor integration would all need to match, so per `CLAUDE.md` it belongs in `../sase-core/crates/sase_core` behind
`sase_core_rs`. It is small and pure — a good first seam. **Rendering and deployment** (`init_skills_handler.py`, the
Jinja frame, chezmoi provenance) are presentation/plumbing and stay in Python, calling through the binding.

### Phasing

1. **Free wins, no mechanism.** Fix `sase_hg_commit` (`[gemini]` → `[agy]`). Trim `sase_repo`'s description to a pointer
   at the Tier-1 rule. Together: ~−300 chars and one real bug closed.
2. **Bundles.** `bundle:` frontmatter + config override, bundle definitions, generated bundle skills with the inline
   threshold, `sase skill show`. Ship **Bundle A only** and measure — it is 65% of the available saving at the lowest
   risk. Keep everything else pinned.
3. **Search.** `sase skill search` + `/sase_search_skills`. Then land Bundles B and C.
4. **Instrument and iterate.** Bundle grouping and char-cost reporting in `sase skill list`; empty-search telemetry in
   `sase skill log`; promote/demote based on it.

Optional, later: a `invocation: user-only` sase concept rendered as `disable-model-invocation: true` on Claude and as
bundle membership elsewhere, for skills no agent ever needs (none today — see §2). Per-run skill seeding (the
2026-07-07 report's Option C) remains available on top; the Codex shadow `CODEX_HOME`, the `SASE_AGY_HOME` redirect, and
Claude's symlink-friendly skill directories are all viable injection points, but launch-time prediction is strictly
weaker than retrieval at the moment of need, so it is an optimization, not a foundation.

## 6. Risks

| Risk                                                                                   | Mitigation                                                                                            |
| :------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| Model never thinks to search / bundle description fails to match                        | Bundles carry domain triggers, not generic ones; `/sase_search_skills` as fallback; a one-line nudge in Tier-1 memory |
| Extra round trip for bundled skills                                                     | Inline threshold makes small bundles single-hop; member table is already at Level 2                    |
| Bundle description bloats until it re-enumerates every member                           | Cap bundle descriptions (~250 chars) and enforce it in `sase skill list`; split the bundle instead      |
| Bundled skills lose `/name` autocomplete                                                | Bundle's own `/name` still autocompletes; `sase skill show` resolves any member; pin anything Bryan types often |
| Bundled skills lose native frontmatter (`argument-hint`, `allowed-tools`, `context: fork`) | Verified: no current sase skill uses any of these — frontmatter is only `name`/`description`/`skill`/`log_skill_use`. Revisit if that changes |
| Prohibitive skill accidentally bundled → silent wrong behavior                           | The prohibitive/permissive rubric in §3 is the gate; encode it as a review checklist for new bundles    |

## 7. Sources

Runtime documentation:

- [Claude Code — Extend Claude with skills](https://code.claude.com/docs/en/skills) — listing budget (1% of context
  window), `skillOverrides` states, `skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`,
  `skillListingMaxDescChars`, the `disable-model-invocation` / `user-invocable` table, nested `.claude/skills/`,
  plugin namespacing, `/doctor` diagnostics
- [Claude Platform — Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Platform — Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Anthropic Engineering — Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Codex — Agent Skills](https://developers.openai.com/codex/skills) — 2% / 8,000-char budget, shorten-then-omit
- [Gemini CLI — Agent Skills](https://geminicli.com/docs/cli/skills/) — all enabled descriptions injected, no budget
- [Agent Skills open standard](https://agentskills.io)

Research literature:

- [SkillFlow: Scalable and Efficient Agent Skill Retrieval System](https://arxiv.org/html/2504.06188)
- [Group of Skills: Group-Structured Skill Retrieval for Agent Skill Libraries](https://arxiv.org/abs/2605.06978)
- [Graph-of-Skills: Dependency-Aware Structural Retrieval for Massive Agent Skills](https://arxiv.org/abs/2604.05333)
- [Skill Retrieval Augmentation for Agentic AI](https://arxiv.org/html/2604.24594v1)

Prior sase research:

- [`xprompt_skill_description_progressive_disclosure.md`](../xprompt_skill_description_progressive_disclosure.md)
  (2026-07-07)

Repo anchors (verified 2026-07-29; line numbers will drift): `src/sase/main/_init_skills_sources.py`,
`src/sase/main/_init_skills_rendering.py`, `src/sase/main/init_skills_handler.py`, `src/sase/main/parser_skills.py`,
`src/sase/main/skills_handler.py`, `src/sase/skills/{inventory,cli_list,cli_log,cli_use,use_log}.py`,
`src/sase/xprompt/models.py:176-177`, `src/sase/xprompt/loader_sources.py`,
`src/sase/llm_provider/commit_finalizer_prompting.py:76`, `src/sase/config/sase.schema.json`,
`src/sase/xprompts/skills/`, `src/sase/amd/templates/AGENTS.template.md`.

Measurements taken 2026-07-29 from `sase skill list`, `sase skill log --json` (4,138 uses), and direct character counts
over `~/.claude/skills/*/SKILL.md`.
