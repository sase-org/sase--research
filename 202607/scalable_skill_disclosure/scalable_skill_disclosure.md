---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# Scalable Skill Disclosure: Bundles and a `/sase_search_skills` Gateway

Consolidated from two independent research passes ([A](./scalable_skill_disclosure__a.md),
[B](./scalable_skill_disclosure__b.md)) plus a third verification pass. It supersedes both, and supersedes the
recommendation in
[`xprompt_skill_description_progressive_disclosure.md`](../xprompt_skill_description_progressive_disclosure.md)
(2026-07-07), none of whose Phase 1 was implemented.

## Bottom line

Build it, but three things change relative to both source reports:

1. **The headroom is gone, not distant.** In this very session the Claude skill listing measures **~7,757 characters
   against a documented ~8,000-character default budget — ~97% used**. SASE is only **38%** of it; the other 62% is
   host/plugin skills that grow outside your control. Report B's "roughly 30 more skills until the cliff" is off by an
   order of magnitude because it measured only the SASE share.
2. **The always-listed unit should be a gateway whose description _is_ a bare-name index** — not a generic search
   description (A) and not one description per bundle (B). A skill name costs ~12 characters against ~171 for a
   description, a **14× compression that keeps the trigger tokens the model actually matches on**. This is the pattern
   the Claude Code harness itself ships for deferred tools.
3. **Deletion is a hard prerequisite, and it is verified missing.** `sase skill init` cannot remove a former top-level
   `SKILL.md`. Ship the manifest work _first_ or the first migration saves exactly zero.

Recommended split: **7 pinned + 1 gateway + 10 bundled leaves**, taking the SASE listing from 2,915 → ~1,502 chars
(**−48%**), or ~1,202 (**−59%**) with one free description trim. The durable win is the marginal cost of skill #18:
**~12 chars bundled vs ~171 pinned**.

## 1. Verified current state (2026-07-29)

All figures below were re-measured directly through `sase.main.init_skills_handler.load_skill_xprompts()`, not taken
from either report.

### The catalog

`sase skill list`: **18 sources → 5 providers → 85 generated targets** (70 current, 15 stale, 0 missing), deployed via
chezmoi. Sources arrive through **three** discovery channels, which the bundle mechanism must all reach:

| Channel        | Count | Example                                         |
| :------------- | ----: | :---------------------------------------------- |
| Package        |    16 | `src/sase/xprompts/skills/sase_beads.md`        |
| Home xprompt   |     1 | `/home/bryan/sase/xprompts/bob_query.md`        |
| Config overlay |     1 | `config_overlay:sase_athena.yml` → `sase_gmail` |

> Conflict resolved: Report B stated both `bob_query` and `sase_gmail` come from `~/sase/xprompts/`. Only `bob_query`
> does; `sase_gmail` is supplied by the `sase_athena.yml` config overlay, as Report A said. This matters — a
> frontmatter-only mechanism cannot reach a config-overlay skill cleanly, which is the strongest argument for B's
> proposed config-level override map.

The skill frontmatter surface is exactly two keys — `skill: bool | list[str]` and `log_skill_use: bool`
(`src/sase/xprompt/models.py:176-177`). Selection is a one-line truthy filter (`select_skill_xprompts()`,
`src/sase/main/_init_skills_sources.py:79-84`). No tiering, no per-run filtering, no search. The `sase skill` CLI group
is `{init, list, log, use}`.

### The measured cost (reconciling A and B)

The two reports quoted 2,951 and 2,900. Both are right; they measure different things.

| Measurement                                      |     Chars | Matches |
| :----------------------------------------------- | --------: | :------ |
| Descriptions, all 18 sources                     |     2,950 | A       |
| **Name + description, 17 _deployed_ sources**    | **2,915** | **B**   |
| Descriptions, 17 deployed sources                |     2,713 | —       |
| Name + description + source path (Codex form)    |    ~4,552 | A       |
| Bodies, all 18 (Level 2 — free until activation) |    73,820 | A       |

**2,915 is the operative number.** `sase_hg_commit` deploys nowhere (§1.3), so its 237 chars cost nothing today; A's
2,951 includes it. A's 4,552 is Codex-specific — Codex also discloses the source path.

Per-skill, sorted by Level-1 cost:

| Skill                | Desc chars | Body chars | `log_skill_use`   |
| :------------------- | ---------: | ---------: | :---------------- |
| `sase_repo`          |    **419** |      2,098 | false             |
| `sase_chats`         |        255 |      5,606 | true              |
| `sase_project`       |        251 |      1,419 | true              |
| `sase_git_commit`    |        245 |      7,108 | true              |
| `sase_hg_commit`     |        237 |      1,951 | true (undeployed) |
| `sase_gate`          |        224 |      6,882 | true              |
| `sase_notify`        |        223 |      3,850 | true              |
| `sase_memory_read`   |        175 |        917 | false             |
| `sase_agents_status` |        161 |      4,600 | true              |
| `sase_changespecs`   |        145 |      5,616 | true              |
| `sase_beads`         |        118 |     15,294 | true              |
| `sase_questions`     |         90 |      1,693 | true              |
| `bob_query`          |         82 |      1,033 | true              |
| `sase_run`           |         80 |      7,328 | true              |
| `sase_plan`          |         76 |      2,099 | false             |
| `sase_artifact_file` |         65 |        738 | true              |
| `sase_var`           |         60 |      3,592 | true              |
| `sase_gmail`         |         44 |      1,996 | true              |

### The finding neither report had: SASE is 38% of the problem

Both reports measured SASE's contribution against the host budget and concluded there was comfortable headroom — B
explicitly ("36% of budget… neither is close to overflow… roughly 30 more average skills would hit the cliff"). A was
more careful, noting the host "also has non-xprompt skills and its own framing," but did not measure them.

Measured from this session's actual skill listing (12 non-SASE skills present alongside the 17 SASE ones):

| Group                | Skills | Name + desc chars | Share |
| :------------------- | -----: | ----------------: | ----: |
| SASE xprompt skills  |     17 |             2,915 |   38% |
| Host / plugin skills |     12 |             4,842 |   62% |
| **Total listing**    | **29** |         **7,757** |  100% |

The two largest single entries in the whole listing are not SASE's: `dataviz` (1,135 chars) and `claude-api` (1,068)
together nearly equal the entire SASE catalog. `sase_repo` (419) is only the fourth-largest line item overall.

Against Claude Code's documented default listing budget (1% of context window ≈ 8,000 chars on a 200k model; Codex
allots 2% or 8,000), that is **~97% consumed, with roughly 240 characters — about 1.4 average SASE skills — of
headroom.**

Honest caveats: the non-SASE descriptions were transcribed from this session's context listing (±small transcription
error); host formatting overhead is _excluded_, so the true figure is higher, not lower; and a larger context window
raises the budget proportionally. A bare Codex agent would carry fewer host skills. But the direction is unambiguous and
it inverts B's framing. Two consequences:

- **The problem is present, not prospective.** The case for acting now no longer rests on projected growth.
- **SASE controls only 38% of the budget.** Bryan cannot trim `dataviz` or `claude-api`. Bundling the SASE catalog is
  the only lever he actually holds — which _raises_ the value of this work, because it must absorb pressure created
  elsewhere.

### Three defects worth fixing independently of bundles

1. **`sase_hg_commit` deploys nowhere.** It declares `skill: [gemini]`; registered providers are `agy`, `claude`,
   `codex`, `fakey`, `opencode`, `qwen`. Verified: `get_skill_target_providers()` returns empty for it. Flagged in the
   2026-07-07 report, still unfixed three weeks later. One-line fix to `[agy]`.
2. **`sase_repo`'s 419-char description is 15% of the SASE listing** and restates, nearly verbatim, a rule already in
   Tier-1 memory (`CLAUDE.md`/`AGENTS.md`, loaded by every agent). Trimming to a ~120-char pointer saves ~300 chars with
   no mechanism at all.
3. **Rust/Python frontmatter drift already exists.** `crates/sase_core/src/editor/frontmatter.rs:95` documents
   `keywords` as a valid xprompt field with active hover text, but Python retired it
   (`_RETIRED_FRONTMATTER_KEYS = frozenset({"keywords"})`, `src/sase/memory/notes.py:29`). This is concrete evidence for
   §5's Rust-first sequencing, not a hypothetical.

A fourth, non-defect: **`sase skill use` validates only name format and agent identity** (`src/sase/skills/cli_use.py`)
— nothing about deployment. Bundled, undeployed skills therefore remain fully auditable under the existing log. The
telemetry loop survives bundling unchanged.

### Usage distribution (`sase skill log`, 4,138 events / 1,956 agents)

`sase_git_commit` 1,825 (44.1%) · `sase_beads` 1,688 (40.8%) · `sase_repo` 121 · `sase_memory_read` 85 · `sase_chats` 74
· `sase_questions` 70 · `sase_changespecs` 58 · `sase_agents_status` 53 · `sase_var` 45 · `sase_project` 31 ·
`sase_plan` 29 · `sase_run` 19 · `sase_notify` 15 · `bob_query` 9 · `sase_gate` 8 · `sase_artifact_file` 6 ·
`sase_gmail` 0.

Two skills are 85% of invocations. Counts for `sase_repo`, `sase_memory_read`, and `sase_plan` are **lower bounds** —
all three now set `log_skill_use: false`, so their totals come from an earlier period. The log also contains 2 events
for the retired `sase_artifact` name. **Frequency is not the primary tiering axis** (§3).

## 2. What the runtimes give us

All five providers implement the [Agent Skills](https://agentskills.io) three-level model: Level 1 = name + description
(always loaded), Level 2 = body (on activation), Level 3 = referenced files. Levels 2 and 3 are already free — the
73,820 body characters are not the problem. **Level 1 is the entire problem**, and no runtime defers it; they differ
only in how they degrade at the cliff. Claude shortens then silently drops descriptions for least-invoked skills; Codex
shortens then silently omits skills. The failure is invisible, and a skill absent from the listing cannot tell the model
it exists.

### The trap in the obvious shortcut

Claude's `disable-model-invocation: true` removes a description from context entirely while keeping `/name` autocomplete
— apparently free. **It does not work here.** The flag blocks the _Skill tool_, not just the menu, and `sase_git_commit`
is invoked _by the agent_, prompted by `src/sase/llm_provider/commit_finalizer_prompting.py` ("use your /sase_git_commit
skill"). Setting it would break 44% of skill traffic.

Applying the test across the catalog: **no skill qualifies for a typed-only tier today.** Even `bob_query`, which looks
like a purely human-typed personal tool, has 9 agent-driven uses. This is a valuable negative result — it eliminates the
cheap shortcut and justifies building a real mechanism. Keep the lever documented as a future per-provider _rendering_
of a sase-level `invocation: user-only` concept, with bundling as the uniform fallback for runtimes lacking the flag, so
it does not violate the uniform-runtimes rule.

Two other Claude mechanisms, informative but not build-on-able: **nested `.claude/skills/`** loads lazily but keys on
filesystem locality rather than topic and is Claude-only; **plugin skills** are namespaced but their descriptions are
still listed in full — namespacing, not context. Note also that Claude Code already uses "bundled skills" for its own
built-ins, so keep "bundle" in sase's user-facing language but never let the word leak into generated descriptions.

### The precedent that settles the design question

Neither report noticed that **the Claude Code harness running this session already ships the exact mechanism under
design**, and its shape is a third option:

- **Level 1** — full name + description for the hot tool set.
- **Level 1.5** — the deferred set is disclosed as **bare names only**:
  `CronCreate, CronDelete, DesignSync, LSP, Monitor, WebFetch, WebSearch, …`. No descriptions, no schemas.
- **Level 2** — `ToolSearch` fetches full schemas on demand (`select:<name>` or keyword query).

This is neither A's opaque gateway nor B's per-bundle descriptions. It is a **gateway whose description is a bare-name
index**, and it is shipped, load-bearing production behavior. §3 adopts it.

### Prior art

The 2025–2026 literature converged on retrieval over flat listing, and specifically on _grouped_ retrieval:
[SkillFlow](https://arxiv.org/html/2504.06188) finds description-only selection inaccurate at scale and moves to BM25 +
dense retrieval + rerank over full skill _content_; [Group of Skills](https://arxiv.org/abs/2605.06978) replaces the
flat list with a compact role-labeled context built from anchor-centered groups;
[Graph-of-Skills](https://arxiv.org/abs/2604.05333) retrieves a bounded dependency-aware set, reporting **+25.6% peak
reward and −56.7% total tokens** versus loading all skills, consistent across libraries of 200–2,000 skills. (Citations
carried from Report B; the two 2026 papers were not independently re-verified in this pass.) The consistent finding —
group structure beats flat lists on _accuracy_, not just tokens — is the load-bearing one, and it is what makes
retrieval-at-time-of-need preferable to launch-time prediction.

## 3. The design question: what is the always-listed unit?

Not "should we defer?" — yes — but what stays in Level 1.

| Option                                    | Level-1 entries   | Level-1 chars | Trigger quality                                           |
| :---------------------------------------- | :---------------- | ------------: | :-------------------------------------------------------- |
| Status quo                                | O(skills)         |         2,915 | Good until the host truncates, then silently degrades     |
| **A** — generic gateway, hidden bundles   | O(core + 1)       |         1,552 | Weak: model must _think_ to search; poor semantic overlap |
| **B** — one description per bundle        | O(core + bundles) |         2,194 | Strong: domain triggers match user phrasing               |
| B without gateway                         | O(core + bundles) |         1,926 | Strong, but no cross-bundle fallback                      |
| **Recommended** — gateway _as name index_ | O(core + 1)       |     **1,502** | Strong: the names _are_ the trigger tokens                |
| … + `sase_repo` trim                      | O(core + 1)       |     **1,202** | Same                                                      |

A's objection to B is correct: per-bundle umbrellas keep startup growing with bundle count, and at 17 skills more than
three bundles begins inverting the savings (B concedes this). B's objection to A is also correct: _discoverability
inversion_ — a generic "search the extended skill catalog" description has poor semantic overlap with any concrete task,
and recall then depends on agent diligence, the one variable we cannot control.

**Both objections dissolve if the gateway's description is the name index.** A single Level-1 entry:

> Search and load SASE workflows not listed above: agents_status, artifact_file, changespecs, chats, gate, notify,
> project, var, bob_query, gmail. Use when no listed skill above clearly covers the task.

That is 200 description chars + 18 name chars = **218 characters carrying ten distinct trigger tokens**. It costs less
than _one_ of B's bundle descriptions (~214) while beating A's opaque gateway on recall: a user asking about "the
notification I just got" hits the literal token `notify` sitting in Level 1. Per bundled skill the cost is **~12
characters instead of ~171 — 14× compression with the trigger preserved**, versus B's ~4.5× on its best bundle.

**Growth path.** The name index is the right regime while the bundled set is small (roughly < 40 names ≈ 500 chars).
Past that, collapse names into bundle names — which is exactly B's design — and past _that_, the pure gateway, which is
A's. The three proposals are not competitors; they are the same design at three scales. Build the mechanism so the
gateway description is _generated_ from the catalog, and moving between regimes becomes a rendering policy rather than a
redesign.

Named bundles remain worth having for authorship, filtering, ownership, staged rollout, and search scoping — they just
should not each buy a Level-1 entry at today's size.

### The tiering rubric

Report B's framing is the better one and should be adopted verbatim, with one correction:

- **Prohibitive** — exists to stop the agent doing the wrong thing by default (`sase_repo`: never web-fetch a repo;
  `sase_git_commit`: never raw `git commit`; `sase_run`: never spawn agents directly). If it never fires, the agent does
  the wrong thing and _never learns it was wrong_. **Pin regardless of frequency** — `sase_repo` is only 2.9% of uses.
- **Permissive** — helps once the agent already knows what it wants (`sase_chats`, `sase_notify`). Deferral is safe;
  worst case is one extra hop.

Secondary axes: **demand-triggered by an explicit user question** (the user's words become the retrieval query —
bundling is nearly free); **named by machinery or launch prompts** (invoked by name, not discovered — bundling is free,
but verify the invocation path still resolves). Frequency is a tiebreaker only: hot skills should be pinned because the
extra hop is paid often.

> **Conflict resolved — `sase_run`.** A pins it; B bundles it in `sase_agent_io`. **A is right, and B contradicts its
> own rubric.** `sase_run`'s description is "Request a SASE agent launch through LaunchApproval **instead of spawning
> directly**" — textbook prohibitive. At 80 chars it is also cheap to pin. B's classification appears driven by cohesion
> of the `agent_io` grouping rather than by the prohibitive/permissive test it had just established.

## 4. Audit of all 18 skills

**Pinned — 7 skills, 1,284 chars (name + description)**

| Skill              |  Uses | Chars | Why it stays                                                                   |
| :----------------- | ----: | ----: | :----------------------------------------------------------------------------- |
| `sase_git_commit`  | 1,825 |   245 | Machinery-invoked by the commit finalizer; prohibitive; 44% of traffic         |
| `sase_beads`       | 1,688 |   118 | 41% of traffic; cheapest description-per-use in the catalog                    |
| `sase_repo`        |   121 |   419 | Prohibitive — enforces a Tier-1 MUST; failure is silent and wrong. **Trim it** |
| `sase_memory_read` |   85+ |   175 | Gate for all Tier-2 memory reads; named by `AGENTS.template.md`                |
| `sase_questions`   |    70 |    90 | Replaces a disabled native tool — an agent unaware of it cannot ask            |
| `sase_plan`        |   29+ |    76 | Replaces disabled plan mode; named by memory templates and plan machinery      |
| `sase_run`         |    19 |    80 | **Prohibitive** — governs launch authorization; prevents direct agent spawning |

**Bundled — 10 skills, 1,631 chars removed from Level 1**

| Skill                | Uses | Chars | Bundle                | Rationale                                                  |
| :------------------- | ---: | ----: | :-------------------- | :--------------------------------------------------------- |
| `sase_chats`         |   74 |   255 | `agent_observability` | Read-only; demand-triggered ("what did agent X say?")      |
| `sase_project`       |   31 |   251 | `project_admin`       | Lifecycle/selection; distinctive vocabulary                |
| `sase_notify`        |   15 |   223 | `agent_observability` | Read-only inbox; strong "notification" trigger term        |
| `sase_gate`          |    8 |   224 | `agent_runtime`       | **Semi-prohibitive** — migrate last, after trigger evals   |
| `sase_agents_status` |   53 |   161 | `agent_observability` | Read-only live-agent inspection                            |
| `sase_changespecs`   |   58 |   145 | `project_admin`       | Specialized PR/ChangeSpec inspection                       |
| `bob_query`          |    9 |    82 | `personal_data`       | Personal, read-only; proof case for home-authored xprompts |
| `sase_artifact_file` |    6 |    65 | `agent_runtime`       | Narrow; almost always named by the launching xprompt       |
| `sase_var`           |   45 |    60 | `agent_runtime`       | Narrow handoff mechanism; usually named, not discovered    |
| `sase_gmail`         |    0 |    44 | `personal_data`       | Never used; proof case for config-overlay-supplied skills  |

**Fix, do not bundle:** `sase_hg_commit` — repair `[gemini]` → `[agy]`. Commit skills are resolved by name from
machinery and must never be bundle members.

Two members deserve their caveats carried forward. `sase_gate` is semi-prohibitive: if it never fires the agent falls
back to asking plainly — degraded but not harmful — so it is the _last_ migration, gated on trigger-pair evals.
`personal_data` saves almost nothing today (126 chars), but it is the sharpest instance of the user's actual complaint —
every coding agent in this repo pays for Gmail and Obsidian descriptions it will never use — and it is the proof case
for the two non-package discovery channels, which is where the catalog will actually grow.

**Net effect**

| State                            | Level-1 chars |             Δ |
| :------------------------------- | ------------: | ------------: |
| Today                            |         2,915 |             — |
| 7 pinned + name-index gateway    |         1,502 |          −48% |
| … + `sase_repo` description trim |         1,202 |          −59% |
| Marginal cost of skill #18       |           ~12 | vs ~171 today |

The percentage is pleasant; the last row is the point.

## 5. The blocking prerequisite: deployment cannot prune

Report A identified this; Report B missed it entirely. **Verified in this pass, and it is decisive:**

- `build_skills_inventory()` (`src/sase/skills/inventory.py:150-194`) enumerates targets by rendering the _current_
  xprompt set. A deployed file whose source xprompt no longer selects it is **never enumerated**. Orphan detection is
  structurally impossible, not merely unimplemented — so `sase skill list`'s "15 stale" means "content differs from what
  would be rendered," never "orphaned."
- The word `delete` appears **zero times** in `init_skills_handler.py` and `_init_skills_rendering.py`. The
  `InitOperation` vocabulary includes `"delete"`, but the skills path never emits it.
- `_SkillDeployManifest` (`src/sase/main/_init_skills_manifest.py:31-52`) records exactly three fields: `source_commit`,
  `xprompt_set_sha256`, `deployed_at` — one aggregate hash, **no managed paths, no per-file hashes**.

**Consequence, and it changes the phase order.** Report B's Phase 2 proposes shipping Bundle A alone and measuring. If
that ran today, the five members' 25 existing `SKILL.md` files (5 skills × 5 providers) would remain deployed and every
host would keep injecting their descriptions. The measured saving would be **exactly zero**, and the experiment would
read as "bundling doesn't work."

The fix is a **manifest v2** recording schema version, source commit, and for every managed target: relative path,
provider, skill, exposure tier, bundle, and content hash. Deletion may target only a path recorded as SASE-managed and
must refuse — surfacing drift — if the live file no longer matches its recorded hash. Unknown user-authored skills must
never be pruned. Deletions appear in `--diff`/`--dry-run` and participate in the same deploy lock, provenance commit,
and `chezmoi apply` transaction as writes.

**Ship this before moving any leaf.** It is also independently valuable: it closes the 15-stale/orphan blind spot that
exists today.

## 6. Implementation map

### Rust core first — enforced, not merely preferred

The frontmatter contract crosses the boundary, and the ordering is enforced by a validator:
`validate_top_level_fields()` (`crates/sase_core/src/editor/frontmatter.rs:435-451`) emits an
`unknown_xprompt_frontmatter_field` diagnostic — _"Unknown xprompt frontmatter field `X` will be ignored"_ — for any key
absent from `TOP_LEVEL_FIELD_DOCS`, which today holds exactly
`name, input, tags, description, skill, snippet, log_skill_use, keywords, xprompts`.

So B's plan of adding `bundle:` to `sase.schema.json` and `models.py` alone would leave **every bundled xprompt flagged
in the editor with an actively false message**. Severity is Information, so nothing breaks — but it is exactly the drift
that already produced the retired-`keywords` mismatch (§1.3).

In `sase-core`:

- Add the field to `TOP_LEVEL_FIELD_DOCS` (hover text), a `validate_skill_bundle()` alongside `validate_log_skill_use`,
  and a `PANEL_FIELD_SCHEMA` entry for the editor frontmatter panel.
- Extend the xprompt catalog record and wire (`xprompt_catalog.rs`, which already carries `is_skill` and parses `skill`
  at lines 1826-1848) with bundle membership and exposure tier.
- Add deterministic skill search/scoring — **none exists today**; `xprompt_catalog.rs` has no search, score, or rank
  function. Put it here so CLI, ACE TUI, editor, and any future web surface agree.

**Field name: `skill_bundle`, not `bundle`.** It sits next to `skill` and `log_skill_use` in a flat top-level namespace
shared with non-skill fields; the `skill_`-prefixed name follows the existing `log_skill_use` precedent and avoids
implying that non-skill xprompts can be bundled. Semantics: `skill` continues to mean "this is a provider skill" and
continues to select providers; absent `skill_bundle` means pinned (so the change is additive and back-compatible);
`skill_bundle` requires a truthy `skill`; `sase_search_skills` is reserved and cannot be bundled; a bundled skill
remains usable as an xprompt (`#sase_gmail`) even though `/sase_gmail` leaves the native catalog.

**Also add a config-level `skill_bundles:` map** in `~/.config/sase/sase.yml` assigning skills to bundles without
editing source. This is required, not optional: `sase_gmail` comes from a config overlay and `bob_query` from a
chezmoi-managed home file, and it mirrors Claude's own rationale for `skillOverrides` ("for skills whose SKILL.md you
don't want to edit").

### Python

Carry `skill_bundle` through `XPrompt`, the file/config/plugin loaders, namespace copies, prompt-frontmatter
serialization, and `sase xprompt list`. Split selected skill xprompts into pinned and bundled targets _after_ existing
first-wins precedence resolution. Render the gateway plus provider-filtered leaf references. Extend `sase skill list`
with exposure and bundle columns, and report Level-1 char cost per tier so the budget is visible.

### Retrieval and loading

```text
sase skill search QUERY [--bundle NAME] [--limit N] [--json]
sase skill show NAME --reason TEXT [--json]        # A's "load"; B's auto-logging name
sase skill bundle list|show [NAME] [--json]
```

Merging the two proposals: use **B's `show`, which records the use automatically** — a strict improvement over today's
self-reported `sase skill use` directive, since retrieval and audit become the same action — with **A's security
constraints**: accept only a name present in the generated catalog (no path traversal), verify the leaf targets the
invoking provider, return only that leaf's provider-rendered body wrapped as identifiable skill content, report bundle
and source provenance, and avoid reinjecting a leaf already loaded in the current run.

Start with deterministic lexical retrieval (BM25 or an equivalent in-memory scorer) over weighted fields: exact/prefix
name highest, description high, bundle name medium, **body low but present** — SkillFlow's central finding is that
description-only matching is what fails at scale. Return a plain no-match rather than falling back to an unrelated
skill. Add embeddings only when the log shows misses lexical search cannot address.

**Search a generated snapshot, not the live checkout** (A's point, and the important security property).
`sase skill init` emits:

```text
sase_search_skills/
├── SKILL.md
└── references/
    ├── catalog.json
    └── <leaf>.md …
```

Reference files must not be named `SKILL.md`, or a host with recursive scanning will re-expose them as ordinary skills.
The snapshot contains only leaves eligible for that provider, rendered from the same merged catalog and source commit as
the pinned skills. `search`/`show` resolve the invoking provider through existing agent metadata and read the deployed
snapshot — never rescanning xprompts from the working directory, which would let any checkout inject hidden instructions
into a global skill search.

**Keep B's inline threshold.** If a bundle's total member body size is under ~6 KB, inline member bodies into the
bundle/gateway reference and skip the second hop. `personal_data` qualifies (1,033 + 1,996 = 3.0 KB);
`agent_observability` does not (~14 KB). This makes small bundles strictly no worse than today — one hop, not two.

Current xprompt skills are instruction-only, so this suffices for v1. Before a bundled leaf can own scripts or assets,
the generator must copy those resources and preserve a safe relative base path.

## 7. Phasing

1. **Free wins, no mechanism.** Fix `sase_hg_commit` (`[gemini]` → `[agy]`). Trim `sase_repo` to a pointer at the Tier-1
   rule. Reconcile the retired `keywords` field between Rust and Python. Together: ~−300 chars and two real bugs closed.
2. **Manifest v2 and managed-target inventory** — no exposure changes. **This is the gate; nothing below works without
   it** (§5).
3. **Gateway infrastructure.** `skill_bundle` in Rust then Python, config override map, search/show, the generated
   snapshot, and `/sase_search_skills` — while leaving every leaf pinned. Validate that former targets actually
   disappear on a test migration.
4. **Low-risk migration.** `personal_data` (inlined), then `sase_artifact_file` and `sase_var`. Verify across all five
   providers.
5. **Domain migration.** `agent_observability`, then `project_admin`, then `sase_gate` last, after trigger-pair evals.
6. **Instrument and iterate.** Bundle grouping and per-tier char cost in `sase skill list`; a counter for searches
   returning nothing — the signal that a description or bundle boundary is wrong. Promote a leaf to pinned when repeated
   searches justify it; demote a cold pinned skill only when missing it is recoverable.

**Evaluation.** Build an activation eval set with one direct and one indirect positive prompt per bundled leaf;
confusing pairs (live agent vs. prior chat, notification vs. custom gate, project vs. ChangeSpec, artifact vs.
variable); negatives that should hit a pinned skill without the gateway; and negatives that should use no SASE skill.
Track gateway activation recall, correct-leaf@1 and @5, false-positive gateway activation, no-match rate, extra tool
round trips, and startup catalog characters before and after each migration.

The generated-skill memory and deployment docs must be updated as part of implementation. That memory update requires
explicit user authorization at the time; this research does not modify memory.

## 8. Risks

| Risk                                             | Mitigation                                                                                              |
| :----------------------------------------------- | :------------------------------------------------------------------------------------------------------ |
| Model never invokes the gateway                  | The name index puts real trigger tokens in Level 1; positive/negative evals; pin all prohibitive skills |
| Search returns a plausible but wrong leaf        | Weighted lexical search including bodies, top-k output, explicit no-match, confusing-pair evals         |
| Extra round trip for bundled skills              | Inline threshold makes small bundles single-hop; pinned set covers 93% of recorded traffic              |
| **Former leaf stays installed → zero saving**    | **Manifest v2 managed paths + transactional pruning, shipped first (§5)**                               |
| Gateway description bloats as names accumulate   | Generate it from the catalog; switch to bundle names past ~40 leaves (§3 growth path)                   |
| Checkout injects hidden instructions into search | Search the deployed provider snapshot, never the working tree                                           |
| Provider sees an ineligible leaf                 | One filtered catalog per provider, re-verified on load                                                  |
| Loss of native `/leaf` autocomplete              | `#leaf` xprompt use survives; `sase skill bundle show`; pin anything Bryan types often                  |
| Prohibitive skill bundled by mistake             | The prohibitive/permissive test (§3) as a review checklist gate for every new bundle                    |
| Bundled skills lose native frontmatter           | Verified none in use — sase skills carry only `name`/`description`/`skill`/`log_skill_use`              |
| Non-SASE skills consume the freed budget         | Unavoidable; make it visible via per-tier char reporting in `sase skill list`                           |

## 9. Sources

Runtime docs: [Claude Code — Skills](https://code.claude.com/docs/en/skills) (listing budget, `skillOverrides`,
`skillListingBudgetFraction`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`, `skillListingMaxDescChars`, the
`disable-model-invocation`/`user-invocable` table, nested skills, plugin namespacing) ·
[Agent Skills specification](https://agentskills.io/specification) ·
[client implementation guide](https://agentskills.io/client-implementation/adding-skills-support) ·
[description optimization](https://agentskills.io/skill-creation/optimizing-descriptions) ·
[Codex — Agent Skills](https://developers.openai.com/codex/skills) ·
[OpenAI — Build skills](https://learn.chatgpt.com/docs/build-skills) ·
[Gemini CLI — Skills](https://geminicli.com/docs/cli/skills/)

Literature: [SkillFlow](https://arxiv.org/html/2504.06188) · [Group of Skills](https://arxiv.org/abs/2605.06978) ·
[Graph-of-Skills](https://arxiv.org/abs/2604.05333) ·
[Skill Retrieval Augmentation for Agentic AI](https://arxiv.org/html/2604.24594v1)

Prior sase research:
[`xprompt_skill_description_progressive_disclosure.md`](../xprompt_skill_description_progressive_disclosure.md)
(2026-07-07) · source reports [A](./scalable_skill_disclosure__a.md) · [B](./scalable_skill_disclosure__b.md)

Repo anchors (verified 2026-07-29; line numbers drift): `src/sase/main/_init_skills_sources.py:79-84`,
`src/sase/main/_init_skills_manifest.py:31-52`, `src/sase/main/init_skills_handler.py`,
`src/sase/main/parser_skills.py`, `src/sase/skills/{inventory,cli_list,cli_log,cli_use,use_log}.py`,
`src/sase/xprompt/models.py:176-177`, `src/sase/memory/notes.py:29`,
`src/sase/llm_provider/commit_finalizer_prompting.py`, `src/sase/config/sase.schema.json`,
`../sase-core/crates/sase_core/src/editor/frontmatter.rs:20-100,424-455`,
`../sase-core/crates/sase_core/src/xprompt_catalog.rs:1826-1848`.

Measurements taken 2026-07-29 via `sase skill list`, `sase skill log --json` (4,138 events), direct character counts
through `load_skill_xprompts()`, and the live skill listing of this session's Claude agent.

## Recommended solution

**Ship `/sase_search_skills` as a single always-listed gateway whose description is a bare-name index of the bundled
leaves, backed by named `skill_bundle` groups, a provider-rendered catalog snapshot, and deterministic
`sase skill search` / `sase skill show` commands.**

Concretely, in order:

1. **Free wins now.** Fix `sase_hg_commit`'s dead `[gemini]` selector, trim `sase_repo`'s 419-char description to a
   pointer at the Tier-1 rule it duplicates, and reconcile the retired `keywords` field across the Rust/Python boundary.
   ~−300 chars, two real bugs, no mechanism.
2. **Ship manifest v2 before touching exposure.** Record every managed path with its content hash and add hash-guarded
   deletion. Without this, the first migration saves nothing and the experiment reads as failure. This is the single
   most important sequencing decision in the report.
3. **Add `skill_bundle` in `sase-core` first** — field docs, validator, panel schema, catalog wire, and the search
   scorer — then thread it through Python. The `unknown_xprompt_frontmatter_field` validator makes Rust-first mandatory,
   not stylistic. Add a `skill_bundles:` config map so the mechanism reaches the home-file and config-overlay skills it
   otherwise cannot.
4. **Pin 7, bundle 10.** Keep `sase_git_commit`, `sase_beads`, `sase_repo`, `sase_memory_read`, `sase_questions`,
   `sase_plan`, and `sase_run` — the last by the prohibitive test, not by frequency — plus `sase_hg_commit` once
   deployable. Migrate `personal_data` (inlined), `agent_runtime`, `agent_observability`, `project_admin`, and
   `sase_gate` last, in that order, each gated on activation evals.

This takes the SASE listing from 2,915 to ~1,202 characters (−59%) and, more importantly, makes the marginal cost of
skill #18 about **12 characters instead of 171**. It preserves every focused leaf workflow, strengthens the audit trail
by making retrieval and logging the same action, and stays uniform across all five runtimes without depending on any one
host's truncation or enable/disable behavior.

The finding that should drive the priority is not the percentage. It is that **the listing measured in this session is
already at ~97% of the documented default budget, and SASE controls only 38% of it.** The remaining 62% grows on someone
else's schedule. Bundling the SASE catalog is the only lever available, and its real job is to absorb pressure created
elsewhere.
