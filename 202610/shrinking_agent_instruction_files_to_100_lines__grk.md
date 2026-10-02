---
create_time: 2026-10-02
updated_time: 2026-10-02
status: research
researcher: grk
topic: shrinking SASE agent instruction files to ≤100 lines
---

# Shrinking SASE agent instruction files to ≤100 lines

## Verdict

**Yes: shrink the always-loaded project instruction file. Treat ≤100 lines as a soft operational budget for the generated project-root `AGENTS.md`, not as a law of physics and not as the only metric.**

The idea is directionally right and overdue. The current 283-line / ~4,300-token project `AGENTS.md` is an encyclopedia with a table of contents glued on, and the encyclopedia is the always-inlined **memory-web descriptor bodies** (especially the 24-decision list roster). SASE already has the progressive-disclosure machinery the user is pointing at. Agents already use it: `lint_and_test.md` was read 490 times by 415 agents. The missing piece is the will to stop inlining catalogs that have outgrown the always-loaded budget.

I would **not** implement this as "move everything into memory files and hope agents look." I would implement it as: make `AGENTS.md` a pointer map of hard rules plus indexes, compact the generated `sase.md` template (it is already 81 lines by itself), collapse web rosters, and put a ratchet on `sase memory init --check`. Do **not** revive keyword-triggered dynamic memory, and do **not** invent a new retrieval engine. That path was tried, deleted three times, and is locked behind `decisions:corpus-before-mechanism`.

The 100-line number is a good *proxy*. The real budget is **attention**: unique always-loaded tokens, unique hard rules, and provider-specific duplication (Grok currently loads `AGENTS.md` and `CLAUDE.md` as identical copies).

---

## 1. Is this a good idea?

Yes, with the adjustments in §4.

### Why the instinct is right

1. **Always-loaded context is paid on every turn.** Anthropic's context-engineering note is still the right frame: find the smallest set of high-signal tokens that produce the desired behavior. Instruction files are not documentation; they are occupancy on every sample.

2. **The file is already past community practice.** 2026 vendor/community guidance clusters around:
   - Claude Code: under **200 lines** per `CLAUDE.md` (soft). `MEMORY.md` auto-memory is hard-capped at 200 lines / 25 KB; `CLAUDE.md` is not truncated, which is why bloat hurts adherence rather than getting clipped.
   - Codex: **32 KiB combined** default (`project_doc_max_bytes`), silent truncation.
   - Cursor: under **500 lines** per rule, split above that.
   - Practitioner "pointer map" writing (agent-config.com, AgentPatterns.ai, verified 2026-09/10): **~100 lines**, maybe 120 with many hard rules.

   SASE's project-root file is 283 lines / 17,285 bytes / ~4,316 tokens. Home adds 74 lines / 3,882 bytes / ~967 tokens. Combined unique instruction text is already 21 KB. Grok double-loads the project and home shims (`docs/agent_providers.md`, "Instruction double-load"), so that provider can see **~42 KB** of duplicated instruction text — **over Codex's 32 KiB cap** if the same bytes were fed to Codex.

3. **SASE already decided this would happen.** `decisions:webs-render-in-their-own-section` (accepted 2026-08-30) says a web descriptor is always paid for, and **reopens when unconditionally inlining every descriptor becomes a real token-budget problem.** Three webs, 66 glossary terms, and 24 decision summaries with supersession markers *is* that problem. This research is the reopen condition, not a new architecture.

4. **Instruction following is an attention budget, not a line budget.** IFScale (Jaroslawicz et al., 2025, arXiv:2507.11538) showed 2025 frontier models degrading past ~150–250 simultaneous instructions, with a primacy bias toward earlier rules. 2026 replications (Arize) show the ceiling moved up an order of magnitude for the best models, but the *mechanism* is unchanged: extra rules compete, middle rules get dropped first, and superseded or nice-to-know catalog lines are the first casualties. A 90-line decision roster in the middle of `AGENTS.md` is exactly the kind of content that dilutes the hard rules above it (`/sase_final`, `/sase_repo`, don't mention `sase_<N>` in plans).

5. **This project already proved the smaller shape.** `sase-core`'s hand-written `AGENTS.md` is 118 lines of commands, conventions, and recipes — close to the 97-line target called out on `sase-165`. Nested `tools/AGENTS.md` is 81 lines. Home `AGENTS.md` is 74. The sase *product* repo is the outlier because generation inlines catalogs.

### Why a naive "≤100 lines, dump the rest into memory" would fail

Progressive disclosure has a failure mode SASE has already paid for: **the agent never learns the source exists.** Dynamic/keyword memory was built 2026-04-12 and removed 2026-05-31; episode recall was built 2026-05-23 and removed 2026-06-15; `keywords:` frontmatter died 2026-07-13. `decisions:corpus-before-mechanism` exists so we do not build a fourth retrieval toy.

Reference memory works *because the always-loaded file still names the note and says when to read it.* `lint_and_test.md` is 160 lines / ~2,382 tokens of procedure. It is `type: reference`. Its AGENTS.md blurb says MUST-read-before-finish. Result: 490 audited reads, 415 distinct agents. That is the pattern to copy, not "delete the pointer too."

If we shrink to 100 lines by deleting the index, agents will stop reading `symvision.md`, `sase_flags.md`, and `xprompts.md`. If we shrink by moving **hard rules** (`/sase_final`, `/sase_repo`, `/sase_memory_write`, `just check`) into reference notes, those rules will be followed only by diligent agents. Hard rules belong in the always-loaded file. Catalogs do not.

---

## 2. Current measured surface (2026-10-02, workspace `sase_19`)

### 2.1 What actually loads

From `sase memory list` on this checkout:

| Surface | Lines | Approx tokens | Bytes | Role |
| --- | ---: | ---: | ---: | --- |
| Project `AGENTS.md` (and each shim) | 283 | 4,316 | 17,285 | Always-loaded project instructions |
| Home `~/AGENTS.md` (and each shim) | 74 | 967 | 3,882 | Always-loaded home instructions |
| Unique loaded files (dashboard) | 357 | 5,283 | — | Project + home + inlined notes counted as sources |
| `tools/AGENTS.md` | 81 | — | 5,084 | Nested; loads when the agent works under `tools/` |
| `src/sase/ace/AGENTS.md` | 48 | — | 1,987 | Nested; ACE-specific |
| `demos/tapes/AGENTS.md` | 5 | — | 236 | Nested; vhs regen rule |

Provider shims (`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`) are **byte-for-byte copies** of `AGENTS.md` (same md5, different inodes). This is intentional as of `sase-5b.3`: some providers do not read `AGENTS.md`, and some do not honor `@AGENTS.md` imports. Legacy one-line `@AGENTS.md` shims are migrated *to* full copies (`src/sase/amd/constants.py`).

Grok is the ugly case: it reads `AGENTS.md` natively **and** treats `CLAUDE.md` as project instructions, so it pays twice. SASE currently accepts that rather than omit `CLAUDE.md` and break a human running `claude` in the same tree.

### 2.2 Where the 283 lines go

| Section | Lines | What it is |
| --- | ---: | --- |
| `## 1. Core Memory` | 103 | Inlined `sase.md` (81 source lines) + `gotchas.md` (10) + `rust_core_backend_boundary.md` (21) |
| `## 2. Reference Memory` | 33 | Index of 10 top-level `type: reference` notes |
| `## 3. Memory Webs` | 145 | Always-inlined descriptors: decisions list roster (~90), glossary inline roster (~25), task_types list + "file discovered work" rule (~25) |

**Memory Webs are 51% of the file.** Core is 36%. The reference index — the actual progressive-disclosure surface — is 12%.

The generated core note `sase/memory/sase.md` is itself 81 lines. A 100-line budget for the *whole* `AGENTS.md` leaves 19 lines for gotchas, rust-core, the reference index, three web descriptors, and section chrome unless `sase.md` shrinks. That is the binding constraint, and it is a **generator** problem, not an authoring-discipline problem.

### 2.3 Core vs reference vs webs today

Flat notes:

| Note | Type | Lines | Tokens | In AGENTS.md? |
| --- | --- | ---: | ---: | --- |
| `sase.md` | core (generated) | 81 | 1,057 | Inlined |
| `gotchas.md` | core | 10 | 68 | Inlined |
| `rust_core_backend_boundary.md` | core | 21 | 242 | Inlined |
| `lint_and_test.md` | reference | 160 | 2,382 | Pointer only |
| `xprompts.md` | reference | 166 | 2,969 | Pointer only |
| `sase_beads.md` | reference | 150 | 2,024 | Pointer only |
| `sase_artifacts.md` | reference | 108 | 1,116 | Pointer only |
| `symvision.md` | reference | 107 | 1,281 | Pointer only |
| `sase_flags.md` | reference | 77 | 1,025 | Pointer only |
| `generated_skills.md` | reference | 74 | 837 | Pointer only |
| `dispatch.md` | reference | 60 | 731 | Pointer only |
| `cli_rules.md` | reference | 33 | 384 | Pointer only |
| `tui.md` | reference | 17 | 109 | Pointer only |
| `sase_sizes.md` | reference, child of beads | 40 | 473 | Not listed (via `## Children`) |
| `tui_perf.md` | reference, child of tui | 128 | 2,148 | Not listed |
| `tui_screenshot.md` | reference, child of tui | 99 | 1,446 | Not listed |

Webs (descriptor always inlined; strand bodies never):

| Web | Strands | Roster style | Descriptor lines | Tokens |
| --- | ---: | --- | ---: | ---: |
| `decisions` | 24 | `list` (title + summary each) | 110 | 1,651 |
| `glossary` | 66 | `inline` (semicolon names) | 39 | 518 |
| `task_types` | 5 | `list` + a behavioral rule in the body | 34 | 310 |

Existing knobs: `type: core|reference` on flat notes; `roster: list|inline` on webs; `priority` on core notes and web descriptors; nested `parent:` so children stay off the top-level index. **There is no knob that keeps a web descriptor *out* of `AGENTS.md`.** That is exactly the cost named in `webs-render-in-their-own-section`.

### 2.4 Audited reads prove progressive disclosure already works

`sase memory log --json` on this project: **1,459 reads, 115 paths, 608 agents.**

Grouped:

| Target | Reads | Distinct-agent hits | Interpretation |
| --- | ---: | ---: | --- |
| `glossary:*` | 769 | 727 | Inline name roster is doing its job |
| `lint_and_test.md` | 490 | 415 | MUST-read pointer works |
| `decisions:*` | 250 | 214 | List roster is used, but a lot of this is research agents dumping the whole web |
| `sase_sizes.md` | 245 | 216 | Child note, **not** in the AGENTS.md index; found via `sase_beads.md` `## Children` |
| `sase_beads.md` | 231 | 205 | Index pointer works |
| `tui_perf.md` | 180 | 150 | Child of `tui.md`, not in the index |
| `tui.md` | 146 | 124 | Index pointer works |
| `symvision.md` | 134 | 118 | Index pointer works |
| `sase_artifacts.md` | 102 | 95 | Index pointer works |
| `dispatch.md` | 3 | 3 | Rare; correctly reference |

The important counter-example: `sase_sizes.md` and `tui_perf.md` are **not** in the always-loaded index and still get heavy traffic, because their parents' audited reads append `## Children`. The top-level AGENTS.md list does not need to enumerate every child. It needs to name the parent and the trigger.

`lint_and_test.md` is the gold standard of SASE progressive disclosure: a 160-line procedure that would wreck the always-loaded file, kept alive by one MUST sentence in the index, actually read.

### 2.5 Skills are a second always-loaded tax

This is in scope because shrinking `AGENTS.md` while ignoring skills would miss half the occupancy.

21 Grok-deployed SASE skills. Frontmatter descriptions total **~4,204 characters / ~1,050 tokens** always in context (Agent Skills level 1). Bodies total 2,742 lines and load only on activation (level 2). Prior research (`research:202607/xprompt_skill_description_progressive_disclosure.md`) already recommended a two-tier skill catalog plus `sase_skill_find` so descriptions stay O(core). That is a **sibling** problem. Do not solve instruction-file bloat by stuffing more procedure into skills; skill *descriptions* are also always-loaded.

Lifecycle skills (`sase_final`, `sase_memory_read`, `sase_memory_write`, `sase_repo`, `sase_monitor`, `sase_plan`, `sase_new_task`) must stay core-tier. Their bodies are long (`sase_gate` 371 lines, `sase_monitor` 245, `sase_final` 187) and that is fine: they are not in `AGENTS.md`.

---

## 3. Industry landscape (what "≤100 lines" actually means in 2026)

### 3.1 The 100-line number is community practice, not a vendor cap

| Source | Number | Kind |
| --- | --- | --- |
| agent-config.com (verified 2026-09-07 vs Claude Code 2.1.263 / Codex 0.153.4) | ~100, maybe 120 | Pointer-map AGENTS.md |
| AgentPatterns.ai (2026-10-02) | ~100 | Pointer map into versioned `docs/` |
| Anthropic Claude Code docs | under 200 / file | Soft target for `CLAUDE.md` |
| Anthropic auto-memory `MEMORY.md` | 200 lines or 25 KB | Hard cap, first-N-lines |
| Cursor | 500 / rule | Split above that |
| Codex | 32 KiB combined | Hard, silent truncate |
| Copilot | "under two pages" | Soft |
| Median of 922 Claude Code files (Alex Dunlop / 2,303-file study) | ~485 words ≈ 60–100 lines | Empirical |
| sase-core `AGENTS.md` | 118 lines | In-house, already near the target |

The 200-line figure people quote as a Claude hard cap belongs to **`MEMORY.md`**, not `CLAUDE.md`. `CLAUDE.md` loads in full (until a 4 MiB skip). That is why length is an adherence problem, not a truncation problem.

### 3.2 What the good 100-line files contain

Convergent template, five sections:

1. What this repo is (a few lines).
2. Commands (`just check`, not a novel about the test pyramid).
3. Hard rules (5–8 non-negotiables).
4. Links / index into deeper docs.
5. Where plans and decisions live.

SASE already has (4) and (5) as Reference Memory + Memory Webs. The defect is that (5) inlines the decision *bodies' summaries* instead of naming the web.

### 3.3 Progressive disclosure is the standard answer

Three layers, same shape everywhere:

| Layer | Agent Skills | Claude Code memory | SASE today | SASE if we do this well |
| --- | --- | --- | --- | --- |
| Always | skill name + description | `CLAUDE.md` / first 200 of `MEMORY.md` | core notes + **entire web descriptors** | hard rules + indexes |
| On activation | `SKILL.md` body | topic files | `sase memory read <note>` | same |
| On demand | referenced files | deeper notes | strand bodies, child notes | same |

Anthropic moved code-review and verification *out* of the Claude Code system prompt into skills, and deferred MCP tool definitions behind ToolSearch (~85% tool-overhead reduction). The same move applies to SASE's decision roster: keep the finder (web name + how to read), drop the encyclopedia.

### 3.4 `@`-imports do not save tokens

Claude Code `@path` imports load at launch. Splitting 400 lines into six files and importing all six is the same bill, harder to see. SASE's full-copy shims exist because some providers cannot even do that composition. **Do not** "fix" bloat by restoring `@AGENTS.md` shims and calling it progressive disclosure. For Grok it would still double-load unless one of the two files goes away.

### 3.5 Prior SASE research this should inherit, not repeat

- `research:202604/agents_md_token_optimization.md` — already recommended under-200, procedures-to-skills, "would the agent get this wrong without the line?"
- `research:202604/dynamic_memory_critique.md` and `decisions:corpus-before-mechanism` — do not rebuild launch-time keyword injection.
- `research:202605/sase_memory_read_agent_usefulness.md` — `sase memory read` needs a catalog/search mode so agents can find notes without a perfect path. Still true; still not a reason to inline the corpus.
- `research:202607/xprompt_skill_description_progressive_disclosure.md` — skill-description bound is a sibling budget.
- `research:202604/opus_4_7_prompt_too_long.md` — CLAUDE.md-like prose inflated ~1.45× under a newer tokenizer. Always-loaded instruction text is on the expensive side of tokenization.

---

## 4. Adjustments to the stated requirements

Call-outs. These are changes I would make to the user's request before implementing.

### Keep

- **Goal: project-root generated `AGENTS.md` ≤ 100 lines.** Good operational proxy, visible in `wc -l` and in review.
- **Use existing memory progressive disclosure.** Do not add a new kind of memory.
- **Keep provider shims generated from one source.** One canonical file, copies for providers that need a native name.

### Change

1. **Budget unique tokens and unique hard rules, not only lines.** A 100-line file of 40-token wrapped paragraphs is ~1,500 tokens; a 100-line file of glossary soup can be 3,000. Add a token budget: **project `AGENTS.md` ≤ 2,000 tokens**, **project+home unique always-loaded instruction ≤ 3,000 tokens**. Lines are the PR-visible ratchet; tokens are the real cost. `sase memory list` already prints both.

2. **The 100-line budget applies to the generated project-root `AGENTS.md` only.** Nested files (`tools/`, `src/sase/ace/`, `demos/tapes/`) and home `AGENTS.md` are separate budgets. Nested files should stay small (they already are). Home should lose the duplicated SASE-memory explainer (see §6). Do not force home down to 100 if it is already 74 of mostly-contract text.

3. **Do not move hard rules into reference memory.** Always-loaded:
   - `/sase_final` as last action; `/sase_monitor` for long commands; no "I'll resume later"
   - `/sase_repo` before other-repo I/O; `sase artifact read` for sidecar artifacts
   - `/sase_memory_write` before memory mutation; `/sase_memory_read` for reference/strands
   - If you changed tracked files in *this* repo, read `lint_and_test.md` and run `just check`
   - Rust-core litmus test (short form)
   - File discovered work via `/sase_new_task` unless the prompt forbids it
   - Do not mention `sase_<N>` workspace paths in plans

   These are the 8 rules. If they do not fit in 100 lines with an index, the index is too fat, not the rules.

4. **Reopen `webs-render-in-their-own-section` for a roster-density knob, not for `type:` on descriptors.** The decision forbids putting `type: core|reference` back on webs. It explicitly allows "a new, explicitly scoped opt-out mechanism designed for that purpose." The right mechanism is **roster density**, not opting the whole web out of the instruction file.

5. **Treat 100 as a ratchet, not a day-one CI red.** Land the generator/content changes, then `sase memory init --check` warns above 100 / 2,000 tokens, then (later) blocks. A hard fail on the current 283-line file would make the first PR a hostage.

6. **Count Grok duplication as in-scope.** Shrinking to 100 lines and still shipping identical `AGENTS.md`+`CLAUDE.md` to Grok leaves ~200 lines of duplicate project instructions in that provider's window. The instruction-file project should either accept that as a known Grok tax or add a provider-specific suppression that is *not* "stop generating `CLAUDE.md`."

7. **Do not fold this into the skill-catalog problem.** Separate bead. Skill descriptions are ~1k always-loaded tokens and growing.

---

## 5. Approaches I considered

### A. Content-only compaction (no product change)

Use knobs that already exist:

- Switch `decisions` (and `task_types`) from `roster: list` to `roster: inline`, like glossary.
- Shorten `sase/memory/sase.md` by editing `memory-sase.template.md`: one short memory paragraph, a compact repo bullet list, keep the four hard-rule blocks.
- Demote `gotchas.md` and/or `rust_core_backend_boundary.md` to `type: reference`.
- Tighten reference descriptions to a single trigger clause.

**Estimate:** decisions `list` → `inline` saves ~70–80 lines by itself (145-line Memory Webs section → ~60). Compacting `sase.md` 81 → ~45 saves another ~35. Demoting rust-core saves ~15. Landing zone **~140–160 lines**, not 100.

**Pros:** no AMD renderer change; reversible; matches "use memory we already have."
**Cons:** misses the 100-line target; inlining 24 decision *names* still grows linearly; demoting rust-core is a behavior risk (agents will reimplement Python backends). I would **not** demote rust-core or the final-declaration paragraph.

This is the right *first* PR, not the whole solution.

### B. Pointer-map `AGENTS.md` + roster density (recommended)

Keep the three-section generated shape (core / webs / reference). Change what a web section is allowed to contain:

- New roster style `roster: index` (or `names`): keywords only, no summaries, no aliases, wrap to a few lines. Glossary can stay `inline` (aliases are the point). Decisions should be `index`.
- Cap inlined roster lines (e.g. 12). Overflow: "N more; `sase memory web show <web>`."
- Hide `superseded` strands from the AGENTS.md roster (keep them in `sase memory web show` and in the descriptor file on disk). Always-loading "Legacy V1 Agent Transport Is Read-Only History" is paying rent on a tombstone.
- Rewrite `memory-sase.template.md` to ~40 lines of hard rules + a one-line memory legend. Move the per-repo blurb list into a generated **reference** note (`sase/memory/repos.md` or fold into the existing repo paragraph as names-only).
- Keep the reference index; allow one-line descriptions; do not list children.

**Estimate:** 70–95 lines. Hits ≤100 without a new retrieval system.

### C. Web-descriptor opt-out (`inline_in_agents: false`)

The literal reopen clause of `webs-render-in-their-own-section`. A web would appear in Reference Memory as a single pointer, like a flat note.

**Pros:** unbounded web growth with O(1) AGENTS.md cost per web.
**Cons:** one more axis; easy to hide a web the agent needed to know existed; invites the `type:` confusion the decision retired.

Use this later, if a fourth or fifth web appears. Three webs do not justify it if roster density is fixed.

### D. Move procedure into skills

Anthropic's own move. SASE already did this for final/monitor/repo/memory/plan. Remaining AGENTS.md bloat is **indexes**, not procedures. Putting "here are 24 decision names" into a skill description just relocates always-loaded tokens into the skill catalog, which already has no budget.

Reject as the primary strategy. Skills stay for workflows.

### E. Launch-time / keyword retrieval (dynamic memory v2)

Rejected. `corpus-before-mechanism`. The corpus that needs a mechanism is "the agent must know *that* the decisions web exists," which a 6-line index already solves. It does not need embedding search.

### F. Restore `@AGENTS.md` shims to "save" copies

Rejected as a token fix. Copies on disk are free. Tokens in the window are not, and Grok loads both files. Claude Code `@import` also inlines at launch. The copy design is there because Gemini/agy and others need a native filename and some runtimes ignore `@`.

A *narrow* Grok-only mitigation (don't feed `CLAUDE.md` to the Grok subprocess, leave it on disk for `claude`) is worth a follow-up bead. It is not how you get to 100 lines.

### G. Nested-only / path-scoped rules

Cursor globs, Claude path-scoped rules. SASE already has nested `AGENTS.md` for `tools/`, ACE, and tapes. Do not explode that into per-package files; the root file is the problem.

---

## 6. Recommended solution

**Adopt B, with A as the first landing PR, and a doctor/init ratchet so the budget cannot silently regress.**

### 6.1 Target shape of project-root `AGENTS.md`

About 80–100 lines, three H2s, no decision summaries, no 66-term wall of aliases if it does not fit, no duplicated memory-system tutorial.

Sketch (illustrative, not a patch):

```markdown
# Structured Agentic Software Engineering (SASE) - Agent Instructions

## Core Memory

You run in an ephemeral `sase_<N>` clone. Do not mention that path in plans.
Other repos: `/sase_repo` first. Sidecar artifacts: `sase artifact read`.
Memory files: `/sase_memory_read` to read, `/sase_memory_write` to change.
End every normal turn with `/sase_final`. Long commands: `/sase_monitor`.
If you changed tracked files in this repo (not `sase/repos/`), read
`lint_and_test.md` and run `just check` (`just check-full` only when asked).
Shared backend belongs in linked `sase-core` (`sase repo open sase-core`).
Litmus: if another frontend would need the behavior, it is core.
File discovered follow-up as task beads via `/sase_new_task` unless forbidden.
Keymap/config changes also update `src/sase/default_config.yml`.

Linked/sidecar: `sase-github`, `sase-telegram`, `sase-nvim`,
`sase-research-artifacts`, `sase--research`.

## Reference Memory

Read with `/sase_memory_read`. Do not open `sase/memory/` files directly.

1. `lint_and_test.md` — MUST before finishing if you changed this repo
2. `sase_beads.md` — beads, sizes, close/note semantics
3. `sase_artifacts.md` — artifact refs and retention
4. `tui.md` — TUI, screenshots, perf (children: tui_perf, tui_screenshot)
5. `sase_flags.md` — feature flags
6. `xprompts.md` — xprompts and launch
7. `cli_rules.md` — new CLI
8. `generated_skills.md` — skill generation
9. `dispatch.md` — `%dispatch`
10. `symvision.md` — unused-symbol lint

## Memory Webs

Descriptors name the collection; strand bodies stay on disk.
`sase memory read <web>:<keyword> [<keyword> ...] -r "<why>"` (batch it).

- **glossary** (66): product terms. Example: `glossary:stitch`
- **decisions** (24): accepted ADRs. `sase memory web show decisions`
- **task_types** (5): `bug`, `ci`, `feature`, `flake`, `memory`
```

That is ~55 lines of substance plus wrapping. Headroom for the generated section numbers and a slightly longer repo list.

### 6.2 Phased implementation

**Phase 0 — measure (half day, no behavior change)**

- Snapshot `sase memory list` lines/tokens for project, home, nested roots.
- Add a hidden/JSON field if needed so agents and CI can read `agents_lines` / `agents_tokens` without scraping the dashboard.
- Record Grok's double-load as a known loaded-token multiplier in the same snapshot.

**Phase 1 — content, existing knobs (one PR, user-authorized memory edit)**

- `decisions.md`: `roster: list` → `roster: inline` (or wait for Phase 2's `index` if it ships in the same epic).
- `task_types.md`: keep the "file discovered work" rule in the descriptor body (it is a hard rule); collapse the 5-type list to one line.
- `memory-sase.template.md`: cut the memory-system tutorial to 4–6 lines (the skill + this file already teach the rest); name repos as a comma list; keep workspace / repo-open / artifact-read / final-declaration paragraphs, compressed.
- Home `sase.md` template: stop inlining the same SASE-memory essay the project file already carries when both load. Home should be *home* facts (chezmoi, tailnet pointer) plus the four hard rules that must survive even if project files are missing.
- Do **not** demote `rust_core_backend_boundary.md`. Compress it to the litmus + `sase repo open sase-core` (it is already close).
- `gotchas.md` can stay core; it is 10 lines and has no other home.

Expected landing: ~140–160 lines. Ships value even if Phase 2 slips.

**Phase 2 — product: roster density + budget (the actual ≤100 hit)**

- Add `roster: index` (`names` is a fine alias): keyword list, no summaries, no alias parentheticals, markdown-wrapped.
- Optional `roster_max_lines:` on the descriptor (default unlimited for back-compat; project `decisions` sets 8).
- AGENTS.md roster omits `metadata.status: superseded` strands; `sase memory web show` still lists them with the marker.
- `sase memory init --check` / `sase doctor`: warn when project-root `AGENTS.md` exceeds `--agents-max-lines` (default 100) or `--agents-max-tokens` (default 2000). Start as warning; promote to blocker after one release of green snapshots.
- Document the reopen of `webs-render-in-their-own-section` as "roster density and overflow, not `type:` on descriptors." Write a new decision strand; mark the reopen condition satisfied-in-part.

Expected landing: **≤100 lines, ≤2,000 tokens.**

**Phase 3 — follow-ups, separate beads**

- Grok double-load: keep generating `CLAUDE.md` on disk; stop *injecting* it for the Grok provider (or teach Grok `[compat.claude] agents = false` if a future Grok build honors it — it does not today).
- Skill-description two-tier catalog (already researched 2026-07). Independent budget.
- `sase memory read` with no args prints the catalog (researched 2026-05). Helps after the index gets shorter.
- Nested `tools/AGENTS.md` still duplicates a chunk of `symvision.md`. Point at the reference note instead of restating the whitelist rules.

### 6.3 What I would not do

- Revive dynamic/keyword memory or add embeddings over notes.
- Put `type: core|reference` back on web descriptors.
- Make 100 lines a `just check` blocker in the same PR that changes the generator.
- Move `/sase_final`, `/sase_repo`, or `just check` out of always-loaded text.
- Replace full-copy shims with `@AGENTS.md` as a token-saving trick.
- Count shim copies as extra *lines to delete*. Disk duplication is the compatibility layer. Window duplication is the Grok bug.
- Dump the decision corpus into a skill.
- Set the budget on "all instruction files in the repo summed." Nested files are path-scoped and small.

### 6.4 Success criteria

After Phase 2:

| Check | Target |
| --- | --- |
| Project-root `AGENTS.md` lines | ≤ 100 |
| Project-root approx tokens (`sase memory list`) | ≤ 2,000 |
| Unique project+home loaded instruction tokens | ≤ 3,000 |
| Hard rules listed in §4 still present verbatim-enough to follow | 8/8 |
| `lint_and_test.md` still in the reference index with MUST language | yes |
| `sase memory read glossary:stitch` and `decisions:single-turn-agents` still work | yes |
| Audited reads of `lint_and_test.md` per landing agent stay high (don't "optimize" the pointer away) | no regression in landing traces |
| `sase memory init --check` reports the budget | warn, then block |

A/B the old vs new file on a handful of real landing traces (final declaration present, `just check` run, no `sase_<N>` in plans, rust-core boundary respected). The reset test from the 2026-04 research still applies: if deleting a line does not change behavior, it should not be always-loaded.

### 6.5 Risks

- **Discoverability of decisions.** The list roster is how agents learn a decision *exists*. Mitigation: keep the web named, keep `sase memory web show decisions` in the index line, keep keyword-addressable reads. Usage data says many decision reads are research dumps of the whole web, not coding agents consulting one ADR. Coding agents need the *name of the web*, not 24 summaries.
- **Home + project overlap.** Compressing project `sase.md` without compressing home leaves Grok paying for two copies of the contract. Phase 1 must touch both templates.
- **Generator rigidity.** `sase.md` is generated and currently refuses hand-edits. The shrink has to go through `memory-sase.template.md` (and the home counterpart). That is the right place; don't fight `sase memory init`.
- **Section numbering.** Shorter files still get `## 1. / ## 2. / ## 3.` If Memory Webs become tiny, consider putting webs *after* reference (index then catalogs) so the MUST-read list sits higher. Primacy bias: hard rules first, MUST pointers second, catalogs last. Today Memory Webs are last already; keep that, but don't let them dwarf the file.
- **Silent Codex truncation.** At 17 KB the project file is fine; at 21 KB with home it is fine; Grok's 42 KB duplicate is already past 32 KiB. Shrinking helps Codex-shaped limits even if we never hit them on Claude.

---

## 7. Critique of the plan in one page

The user's plan: reduce agent instruction files to ≤100 lines, relying on SASE memory progressive disclosure.

| Claim | Assessment |
| --- | --- |
| 100 lines is a reasonable target | **Yes**, as a soft budget for project-root `AGENTS.md`. Aligns with 2026 pointer-map practice. Aggressive vs current 283, achievable if web rosters and `sase.md` shrink. |
| Memory files are the right offload | **Yes.** Already working. 1,459 audited reads. Do not invent a parallel store. |
| Just move more notes to `type: reference` | **Incomplete.** Flat notes are already mostly reference. The bloat is **always-inlined web descriptors**, which cannot use `type:`. |
| Skills can eat the rest | **No**, not as the main move. Skill descriptions are always-loaded too. |
| Do this as a one-shot rewrite of AGENTS.md | **No.** `AGENTS.md` is generated. Edit `memory-sase.template.md`, web `roster:` frontmatter, and the AMD renderer. Hand-editing `AGENTS.md` will be overwritten. |
| 100 lines for every instruction file | **No.** Nested and home files have different jobs. `tools/AGENTS.md` at 81 is already in budget and should stay local. |

**Would I take a different approach?** Same destination, different first move: measure, then compact generated `sase.md` + switch the decisions roster off `list`, then add `roster: index` and a check-mode ratchet. I would not start with a new memory kind, a retrieval engine, or a skill dump.

**The one-sentence strategy:** make `AGENTS.md` the map SASE's memory system already claims it is, and stop generating the territory into the map.

---

## 8. Sources

### In-tree (measured 2026-10-02)

- Project `AGENTS.md` (283 lines, 17,285 bytes, ~4,316 tokens)
- `sase/memory/sase.md`, `gotchas.md`, `rust_core_backend_boundary.md`
- `sase/memory/decisions.md` (`roster: list`), `glossary.md` (`roster: inline`), `task_types.md`
- `sase/memory/decisions/webs-render-in-their-own-section.md` (reopen condition)
- `sase/memory/decisions/corpus-before-mechanism.md`
- `src/sase/main/init_memory/templates/memory-sase.template.md`
- `src/sase/amd/templates/AGENTS.template.md`
- `src/sase/amd/constants.py` (full-copy shims; legacy `@AGENTS.md`)
- `src/sase/memory/web/models.py` (`roster: inline | list` only)
- `docs/agent_providers.md` (Grok instruction double-load)
- `docs/memory.md`
- `sase memory list` / `sase memory log --json` (1,459 reads / 608 agents)
- Linked `sase-core/AGENTS.md` (118 lines)
- Home `~/AGENTS.md` (74 lines)

### Prior SASE research

- `research:202604/agents_md_token_optimization.md`
- `research:202604/dynamic_memory_critique.md`
- `research:202604/opus_4_7_prompt_too_long.md`
- `research:202605/sase_memory_read_agent_usefulness.md`
- `research:202607/xprompt_skill_description_progressive_disclosure.md`

### External

- Anthropic, *Effective context engineering for AI agents* (2025-09-29): <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Anthropic / Thariq Shihipar, progressive disclosure of skills and deferred tools (Claude 5-generation context-engineering notes, 2026)
- agent-config.com, *Your AGENTS.md is too long* (updated 2026-09-07): <https://agent-config.com/learn/writing-agents-md/>
- AgentPatterns.ai, *AGENTS.md as a Table of Contents* (2026-10-02): <https://agentpatterns.ai/instructions/agents-md-as-table-of-contents/>
- Jaroslawicz et al., *How Many Instructions Can LLMs Follow at Once?* (IFScale), arXiv:2507.11538 (2025-07)
- Arize, IFScale replication on 2026 models: <https://arize.com/blog/llm-instruction-following-benchmark-2026/>
- Unblocked, bloated CLAUDE.md audit (2026-07-31): Anthropic under-200, Cursor 500, Codex 32 KiB
- Codex `project_doc_max_bytes` 32 KiB default, silent truncation
- Claude Code: `MEMORY.md` 200 lines / 25 KB hard cap; `CLAUDE.md` loads in full, skip above 4 MiB
- Agent Skills standard: name+description always, body on activation, referenced files on demand
