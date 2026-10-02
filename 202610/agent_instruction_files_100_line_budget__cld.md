# Shrinking SASE's Agent Instruction Files to ≤100 Lines: Evidence, Critique, and a Recommended Path

_Researcher: cld · 2026-10-02 · scope: the generated `AGENTS.md` / `CLAUDE.md` /
`GEMINI.md` / `OPENCODE.md` / `QWEN.md` at the root of the `sase` repo._

## 1. Bottom line

- **Yes, do it.** Cap the always-loaded instructions at about 100 lines. The evidence
  backs a small file, and so does SASE's own usage data. The file has also shown it
  will grow back without a guard: 33 lines in May, 361 in August, 283 today.
- **No category of information has to go.** I rendered a mock with the project's own
  Markdown formatter (Appendix A).
  - It keeps every core rule, all 10 reference-note triggers, and all three web
    rosters.
  - It is **101 lines, about 1,380 tokens**, down from 283 lines and about 4,300
    tokens.
  - Making the decisions roster a pointer (one line instead of a title list) gets it
    to **93 lines, about 1,200 tokens**.
  - The savings come from compression, not removal: titles-only rosters, one-line
    reference triggers, and a much shorter generated `sase.md`.
- **Change the requirement in two ways** (details in §6):
  1. Budget the **rendered, per-provider loaded content**, measured in tokens as well
     as lines. A line count alone can be gamed by changing the wrap width or using
     `@imports`. Claude agents also load `~/CLAUDE.md`, so they see about 357 lines
     today, not 283.
  2. Make the budget a **lint failure**, not a one-time cleanup.
- **Biggest single lever:** the decisions roster is 90 lines (32% of the file, about
  1,570 tokens). Over the last month only about 19 non-research agents read a decision
  record. Switching it to the existing inline roster is a one-line frontmatter change
  (90 → about 35 lines). Going titles-only needs a small renderer flag (about 16
  lines). The decision titles are already written as claims, so most of the passive
  value survives.
- **Don't** shrink the file by moving triggers into skills or `@imports`:
  - Skills are often never invoked. Vercel measured 56% of cases.
  - Imports still load into context. Codex does not expand them at all.
  - SASE's own history includes a 33-line file that only looked small because of
    imports.

## 2. What the file contains today (measured)

All five root shims are byte-identical: 283 lines, 17,263 bytes, about 4,300 tokens.
The renderer wraps prose at the configured Markdown width (88 columns).

| Section (rendered)                      | Source                               | Lines | ≈Tokens | Share |
| --------------------------------------- | ------------------------------------ | ----: | ------: | ----: |
| Title + Core Memory intro               | template                             |     6 |      37 |    2% |
| SASE Memory explainer                   | generated `sase.md`                  |    22 |     299 |    8% |
| Workspace directories                   | generated `sase.md`                  |    10 |     139 |    4% |
| Repositories + repo-access rule         | generated `sase.md`                  |    34 |     477 |   12% |
| Final declaration                       | generated `sase.md`                  |    10 |     138 |    4% |
| Gotchas                                 | `gotchas.md` (core)                  |     6 |      62 |    2% |
| Rust core boundary                      | `rust_core_backend_boundary.md`      |    17 |     240 |    6% |
| Reference Memory index (10 notes)       | note `description:` fields           |    33 |     517 |   12% |
| Memory Webs intro                       | renderer constant                    |     6 |      61 |    2% |
| **Decisions descriptor + 24-row roster** | `decisions.md` (`roster: list`)      |    90 |   1,572 |  **36%** |
| Glossary descriptor + inline roster     | `glossary.md` (`roster: inline`)     |    27 |     477 |   11% |
| Task types + "file discovered work"     | generated `task_types.md`            |    23 |     289 |    7% |

(Shares are of tokens.) The webs make up 51% of the file. The generated `sase.md`
alone is 76 lines, and the same template feeds every SASE project and the home root.

Other facts that matter:

- **History of growth.** Sampled from `git log -- AGENTS.md`:

  | Date       | Lines | Note                                                       |
  | ---------- | ----: | ---------------------------------------------------------- |
  | 2026-02-24 |   104 |                                                            |
  | 2026-03-29 |   142 |                                                            |
  | 2026-05-31 |    33 | Short only because it `@`-imported its core notes          |
  | 2026-06-28 |   150 |                                                            |
  | 2026-08-09 |   333 |                                                            |
  | 2026-08-22 |   361 | Peak                                                       |
  | 2026-09-28 |   283 | Today                                                      |

  The 33-line version did not cut context cost. Claude expanded the imports, and Codex
  never saw that content at all.
- **The decision record already anticipated this.** The `webs-render-in-their-own-section`
  decision lists the cost "a web descriptor's body is now always paid for on every
  turn". It says it reopens when "unconditionally inlining every descriptor becomes a
  real token-budget problem". This goal is that trigger, so the change should come with
  a new decision record (§9, Phase 2).
- **Claude agents load more than the project file.** Claude Code loads `CLAUDE.md` from
  every ancestor directory. Every Claude agent in a sase workspace also loads
  `/home/bryan/CLAUDE.md` (74 lines), so its real load is about 357 lines.
  - About 45 of those 74 lines repeat the SASE Memory explainer, the repo-access rule,
    and the final declaration.
  - It does have an effect: 27 sase-project agents read the home-only `tailnet.md` this
    month.
  - Codex reads only from the git root down to the cwd, so it never sees the home file.
- **Nested instruction files behave differently per provider.**
  - Files: `src/sase/ace/CLAUDE.md` (48 lines), `tools/CLAUDE.md` (81),
    `demos/tapes/CLAUDE.md` (4).
  - Claude loads them lazily when it touches files there. Gemini loads them
    just-in-time.
  - Codex agents launched at the repo root never load them.
  - `tools/CLAUDE.md` also repeats much of the `symvision.md` reference note.
- **Each rule is stated twice.** Most core rules restate the description of a skill
  that is always listed: `/sase_final`, `/sase_repo` (including its web-fetch clause),
  `/sase_memory_write`, `/sase_new_task`. The longer explanations are already in the
  skill bodies.
- **Some instructions are injected already.** The provider adapters inject a
  single-turn "never end your turn to wait" directive: Claude via
  `--append-system-prompt`, Codex via `developer_instructions`, and Muse via a prompt
  prefix. The final-declaration paragraph partly repeats it.

## 3. How agents actually use this content

Source: the audited memory-read log, `~/.sase/projects/gh_sase-org__sase/memory_reads.jsonl`.

- Window: 2026-09-01 to 2026-10-02.
- 1,460 read events from 609 distinct agents.
- For scale: about 1,370 `ace-run` artifact directories in the same window, used as a
  rough proxy for agent runs.
- I counted an agent as a "research agent" if its name starts with `research`. That
  split is approximate.

| Memory                   | Distinct agents | of which research | Always-loaded cost        |
| ------------------------ | --------------: | ----------------: | ------------------------- |
| `lint_and_test.md`       |             415 |                14 | 3-line trigger            |
| `sase_sizes.md` (child)  |             216 |                 9 | 0 (reached via parent)    |
| `sase_beads.md`          |             205 |                23 | 4-line trigger            |
| `tui_perf.md` (child)    |             150 |                32 | 0                         |
| `tui.md`                 |             124 |                28 | 2-line trigger            |
| `symvision.md`           |             118 |                 0 | 2-line trigger            |
| **glossary strands**     |         **109** |            **53** | 27 lines                  |
| `sase_artifacts.md`      |              95 |                46 | 2-line trigger            |
| **decisions strands**    |          **69** |            **50** | **90 lines**              |
| `sase_flags.md`          |              67 |                14 | 3-line trigger            |
| `xprompts.md`            |              41 |                13 | 2-line trigger            |
| `cli_rules.md`           |              36 |                 9 | 2-line trigger            |
| `tailnet.md` (home)      |              27 |                 6 | Claude-only, via `~/CLAUDE.md` |
| `generated_skills.md`    |              24 |                11 | 4-line trigger            |
| task_types strands       |              12 |                 2 | 23 lines                  |
| `dispatch.md`            |               3 |                 1 | 2-line trigger            |

What I take from this:

1. **Short triggers work.** A 2–4 line "read X before Y" entry brings in hundreds of
   agents. `lint_and_test.md` was read by 415 agents. Children reached through a
   parent note get heavy traffic without costing a single always-loaded line:
   `sase_sizes.md` (216) and `tui_perf.md` (150). The reference index is the most
   valuable part of the file, so cuts must keep its triggers.
2. **The decisions roster does not pay for itself as a trigger.** It is 36% of the
   file, yet only about 19 non-research agents opened any decision in a month.
   - Its passive value is real but mostly carried by the **titles**. The titles are
     claims: "Completion Is Host-Owned", "The Rust Core Is Required", "Check-Full Is
     Explicit-Only".
   - The full rows add summaries and alias-laden detail that only matter to someone
     working on that subsystem.
   - Two rows are **fully superseded** (`v1-import-retired`, `two-speed-verification`).
     They are rendered into every turn anyway, which is pure cost and mildly
     misleading.
3. **The glossary roster works as an index.** About 56 non-research agents looked up
   terms. Keep a compact roster. Dropping the aliases takes it from 18 roster lines to
   11; `sase memory read` still resolves aliases.
4. **The task types list is rarely used** (12 agents). `/sase_new_task` already walks
   agents through it. One line is enough.

## 4. External evidence

Full URLs are in Appendix B.

- **Anthropic, Claude Code memory docs.**
  - "Target under 200 lines per CLAUDE.md file. Longer files consume more context and
    reduce adherence." The CLI warns above that size.
  - "Imports … don't reduce its context cost." `CLAUDE.md` is delivered as a user
    message after the system prompt, and "there's no guarantee of strict compliance".
- **Anthropic, best practices.**
  - "For each line, ask: 'Would removing this cause Claude to make mistakes?' If not,
    cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"
  - "If you emphasize many lines, none of them stands out." SASE's file currently has 5
    MUST, 2 IMPORTANT, and 3 Never/NOT markers.
- **OpenAI, "Harness engineering"** (Feb 2026). A "one big AGENTS.md" approach "failed
  in predictable ways": it crowds out the task, "when everything is 'important,'
  nothing is", it rots, and it can't be verified. Their fix was "a short AGENTS.md
  (roughly 100 lines) … serves primarily as a map", with `docs/` as the system of
  record, plus lint/CI that keeps the knowledge base valid. SASE's reference memory
  plays the same role as their `docs/`.
- **Gloaguen et al., ETH SRI.** "Evaluating AGENTS.md" (arXiv:2602.11988).
  - Context files "do not generally improve task success rates, while increasing
    inference cost by over 20%". Repository overviews "are not helpful".
  - Recommendation: human-written files should "describe only minimal requirements".
  - Caveat: the study used SWE-bench-style tasks. SASE's file is mostly workflow
    contract that an agent *cannot* infer from the code (`/sase_final`, `/sase_repo`),
    which is exactly the "minimal requirements" category. The study argues against the
    encyclopedic parts (decision summaries), not the contract.
- **Jaroslawicz et al., "How Many Instructions Can LLMs Follow at Once?"** (IFScale,
  arXiv:2507.11538). Even the best models degrade as instruction count grows. Primacy
  bias peaks around 150–200 instructions, and failures are mostly omissions. The
  harness system prompt and the skill listing already use part of that budget.
- **Vercel, "AGENTS.md outperforms skills in our agent evals"** (Jan 2026).
  - A passive 8 KB **index** in AGENTS.md scored 100%. Skills scored 53% by default
    and 79% with explicit instructions.
  - "In 56% of eval cases, the skill was never invoked."
  - This is the strongest **counter-evidence to over-pruning**: keep pointers and
    triggers always loaded, and move only the bodies out.
- **Skill under-triggering.** Corroborated by Scott Spence's sandboxed evals (50–55%
  activation without a forcing hook) and Anthropic's skill-creator post ("too narrow
  and it never fires").
- **Growth pattern.** "Agent READMEs" (arXiv:2511.12884) studied 2,303 context files:
  they grow through "frequent, small additions", with median additions of 57 words per
  commit and deletions under 15. The median Claude file is 485 words. SASE's file is
  about 2,450 words, roughly 5× that median.
- **Size caps.** Codex stops concatenating at `project_doc_max_bytes` (32 KiB by
  default). The current 17 KB is safe, so truncation is not the reason to act.

## 5. Critique: is ≤100 lines a good idea?

**Mostly yes, for these reasons:**

- **Adherence, more than tokens.** At about 4.3K mostly-cached tokens, the dollar cost
  is small. The real cost is that the five rules that must hold every turn compete
  with 90 lines of subsystem history:
  1. finish with `/sase_final`;
  2. use `/sase_repo` for other repos;
  3. use `/sase_memory_write` for memory files;
  4. read `lint_and_test.md` before finishing;
  5. respect the Rust boundary.
- **Fighting accretion.** This file has been rebuilt by hand several times: the
  glossary alone "moved between core and reference tiers four times". Without a
  budget, each new note is a local decision with a global cost and no one sees the
  total. A number turns tier placement into an explicit trade-off.
- **The audit log favors routers over content.** Short triggers are what bring agents
  to the deep content.

**Where the plan as stated is weak:**

1. **"Lines" is the wrong unit on its own.** At 88 columns, 100 lines is about 1,400
   tokens. Raise `markdown.print_width` and you get "100 lines" without removing a
   word. Turn an inline paragraph into a bullet list and you add lines without adding
   tokens.
2. **"The file" is the wrong object.** The model consumes everything that loads
   together:
   - `@imports` expand in Claude, and Codex ignores them.
   - Claude adds ancestor `CLAUDE.md` files.
   - Nested files load lazily for some providers and never for others.
   A ≤100-line `AGENTS.md` that imports 200 lines is the May 2026 trap again.
3. **A one-time cleanup won't last.** The data shows growth by small additions. The
   enforcement is the actual deliverable.
4. **Over-pruning is a real risk.** Removing triggers to hit the number would cost more
   than it saves (Vercel: 56% never-invoked). Every reference note keeps an
   always-loaded trigger line.

**Would I take a different approach?** Mostly no. SASE already has the right
architecture: core, reference, and web memory, audited reads, and parent/child
reference notes. That is the "map plus system of record" pattern OpenAI arrived at.
The file is long because three renderer defaults are verbose, not because the design
is wrong:

- list-style web rosters with aliases and summaries;
- a long generated `sase.md`;
- multi-line reference descriptions.

So I would **not** add new mechanisms: no retrieval engine (see
`corpus-before-mechanism`), no imports, and no skills-only migration. I would:

1. compress what the renderer emits;
2. add a budget check with per-section cost attribution;
3. record the policy as a decision.

## 6. Requirement adjustments (explicitly flagged)

> **Adjustment A — budget the rendered, provider-effective content, in tokens as well
> as lines.**
>
> - Hard ceilings: **≤100 lines at the configured print width _and_ ≤1,600 tokens**
>   (about 6.4 KB at 4 bytes per token) for the rendered root `AGENTS.md`.
> - `@imports` count toward the budget.
> - Report Claude's effective total separately: project file plus ancestor
>   `CLAUDE.md` files.

> **Adjustment B — aim for about 85 lines, not 100.** A file sitting exactly at the
> ceiling breaks on the next core note, and the easy fix becomes "raise the limit".
> Leave about 15% headroom.

> **Adjustment C — enforce it.** `sase memory init --check` (already part of the lint
> path) should fail when over budget. It should print a per-section line and token
> breakdown, so whoever adds content sees what to demote.

> **Adjustment D — the invariant is "router, not encyclopedia", not the number.** Every
> always-loaded line must be one of:
>
> - a rule that applies to most turns, or
> - a trigger that routes the agent to on-demand content.
>
> Every reference note keeps a trigger. Superseded records never render into
> always-loaded context.

> **Adjustment E (optional) — include the shared `sase.md` template in scope.** It is
> the single biggest piece of core text. It also renders into every SASE project and
> the home root, so compressing it shrinks `~/CLAUDE.md` too, from 74 lines to roughly
> 30–40. That is Claude's ancestor-file overhead.

## 7. Options considered

| Option | Verdict | Why |
| --- | --- | --- |
| **Compress the renderer output** (titles-only rosters, terse `sase.md`, one-line triggers) | **Adopt** | Gets to about 100 lines while keeping every trigger and roster (Appendix A). Mostly frontmatter, templates, and constants. |
| **Budget lint with per-section attribution** | **Adopt** | The only thing that stops the growth shown in §2. Cheap, because Python already parses the rendered document. |
| **Decision record for the budget and router invariant** | **Adopt** | Required by `webs-render-in-their-own-section`'s reopen clause, and it keeps future agents from re-inlining. |
| **Link decisions from domain reference notes** (`[[decisions:…]]`) | **Adopt (incremental)** | Shows a decision exactly when an agent reads the related heavily-used note (artifacts → `machine-link-writes-off-primary`, `lint_and_test` → `check-full-is-explicit` / `guarded-recipes`). Uses the existing link mechanism. |
| Nest low-traffic reference notes under a related parent (e.g. `dispatch.md`, 3 reads/month) | Optional | Zero code (`parent:` already works). Saves 2 lines per note. Only worth it where a natural parent exists. |
| Move runtime-contract text into adapter-injected system prompts | Partial / later | Arguably the correct scope: the contract applies only when SASE runs the agent, and system prompt text carries more weight than a user-message `CLAUDE.md`. But it is invisible to memory review, has to be built per adapter (not every provider injects today), and splits the source of truth. Keep the one-line `/sase_final` rule in `AGENTS.md`. Only remove the duplicated "never wait" detail once every adapter injects it. |
| Claude adapter passes `claudeMdExcludes` for ancestor files above the workspace | Optional, ask Bryan | Makes Claude match Codex and removes about 74 lines from Claude's load. Trade-off: project agents stop seeing home-root memory (tailnet, obsidian), which 27 of them used this month. |
| `@imports` to shorten the file | Reject | Imports still cost context in Claude and are not expanded by Codex. Already tried (May 2026). |
| Move triggers into skill descriptions only | Reject | Skills under-trigger (Vercel: 56% never invoked; Spence: 50–55%). Keep a one-line pointer in `AGENTS.md`, with detail in the skill body. |
| Nested or path-scoped instruction files | Reject as the main mechanism | Provider-specific: Claude and Gemini load them lazily, Codex at the root never does. Reference memory with triggers is the provider-neutral way to load content on demand. |
| Keyword or dynamic retrieval of memory | Reject | Built and removed three times (`corpus-before-mechanism`). |
| Do nothing (4.3K tokens is small for a 200K–1M window) | Reject | Underestimates the adherence cost and ignores growth. The fix is cheap. |

## 8. Proof that it fits

I built Appendix A by hand from the current notes and ran it through
`sase.main.init_memory.formatting.format_generated_memory_markdown`, the function the
renderer itself uses, at the configured width. It uses full `sase/memory/…` paths,
because the document parser requires them.

| Variant | Lines | ≈Tokens | Δ tokens |
| --- | ---: | ---: | ---: |
| Today | 283 | 4,315 | — |
| Zero-code changes only (estimate; Phase 0 below) | ~200 | ~3,000 | −30% |
| Phase 0 plus a project-level `memory.sase_template` override as a prototype (estimate) | ~145 | ~2,300 | −47% |
| Mock: all triggers, glossary and task types inline, decisions titles-only (superseded dropped) | **101** | **1,379** | **−68%** |
| Same, decisions roster replaced by `sase memory web show decisions` | **93** | **1,205** | **−72%** |

Where the cuts in the mock come from:

- **Generated `sase.md`: 76 → 18 lines.** It becomes four bold-lead bullets: finish
  with `/sase_final`, stay in your workspace, reach other repos only via `/sase_repo`
  (repo names only), and memory files are special. The transport details and the
  explanation of memory kinds move to skill bodies that already contain them.
- **Reference index: 33 → 22 lines.** Each trigger becomes a one-line imperative. The
  domain verbs stay; the parenthetical lists go.
- **Decisions: 90 → 16 lines.** Inline roster, titles only, fully superseded strands
  omitted.
- **Glossary: 27 → 15 lines.** Inline roster without aliases.
- **Task types: 23 → 5 lines.** An inline roster plus the "always run `/sase_new_task`
  first" rule.
- **Rust boundary: 17 → 7 lines.**

## 9. Recommended solution

**Goal.** A rendered root `AGENTS.md` (and shims) of about 85 lines, at most 100 lines
and 1,600 tokens. Every reference trigger and every web roster stays present. The
budget is enforced in lint and governed by a decision record.

**Authorization note.** Every step below edits memory (or generated memory). Per
`/sase_memory_write`:

- It needs an approved plan that names each file.
- Whoever authors that plan must confirm the memory changes with `/sase_questions`
  before `sase plan propose`.
- `sase/memory/sase.md` and `task_types.md` are generated, so they change through
  their templates in `src/sase/main/init_memory/templates/`, never by direct edit.

### Phase 0: content-only (no code), about 283 → 200 lines

1. In `decisions.md` frontmatter, change `roster: list` to `roster: inline`. The roster
   region shrinks from 79 to 26 lines (measured). Trim its intro paragraph to two
   lines.
2. Rewrite each reference note's `description:` as a single imperative of at most 90
   characters, starting with "Read before/when …". Keep the trigger verbs. Make
   `lint_and_test.md` the only "MUST".
3. Shorten `rust_core_backend_boundary.md` to about 5 lines of prose. Fold `gotchas.md`
   into a one-line bullet.
4. Optional: make `dispatch.md` (3 reads/month) a child of the closest related
   reference note.
5. Optional prototype: point `memory.sase_template` in `sase/sase.yml` at a terse
   project copy of the `sase.md` template, which brings the file to about 145 lines.
   This forks the shared template, so treat it as a trial of Phase 1.1 and delete it
   once that lands.

### Phase 1: renderer changes (one small epic, Python-only)

`src/sase/amd`, `src/sase/memory/web`, and `src/sase/main/init_memory` are all Python.
No `sase_core_rs` call sites are involved, so there is no Rust-boundary work here.

1. **Shared `memory-sase.template.md`.** Rewrite it as the 4-bullet runtime contract in
   Appendix A.
   - Linked repos render as a comma-separated list of names; `sase repo list` gives
     the descriptions.
   - This also shrinks the home root and every other project's file.
2. **Roster controls.**
   - Inline rosters can drop aliases, through a descriptor key such as
     `roster_aliases: false`.
   - Always-loaded rosters omit **fully** superseded strands by default. They stay
     readable and listed in `sase memory web show`. Partly superseded strands keep
     their short marker.
3. **Generated task types note.** Switch to the inline roster plus a 2-line "file
   discovered work, always via `/sase_new_task`" rule.
4. **Intro constants.** Shorten `_LONG_MEMORY_INTRO` and `_WEB_MEMORY_INTRO` to one
   sentence each. Their first sentences are structural anchors that the renderer
   checks, so update those checks with them.
5. **Budget.**
   - Add `memory.instructions_budget: {max_lines: 100, max_tokens: 1600}` in
     `sase/sase.yml`.
   - `sase memory init` prints a per-section line/token table.
   - `--check` fails when over budget, as a blocker on the existing lint path.
   - Optionally, `sase doctor` reports Claude's effective total, including ancestor
     `CLAUDE.md` files.

### Phase 2: governance and routing

1. **New decision record.** "Always-Loaded Instructions Are A Budgeted Router":
   - States the invariant from Adjustment D and the budget.
   - Marks `webs-render-in-their-own-section` as partly superseded, only for its Cost
     clause. Descriptors still render in their own section, just compactly.
2. **Domain links.** Add `[[decisions:…]]` links from the heavily-read reference notes
   to the decisions that govern their domains. Decisions then surface where agents
   already go, instead of in every turn.
3. **Nested files.** Decide on `src/sase/ace/CLAUDE.md` and `tools/CLAUDE.md`, which
   Codex never loads from the root. Either make them reference notes with triggers or
   accept they are Claude- and Gemini-only. In either case, remove the Symvision text
   that duplicates `symvision.md`.

### Phase 3 (optional): Claude's ancestor overhead

If Bryan agrees, the Claude adapter excludes ancestor `CLAUDE.md` files above the
workspace root (`claudeMdExcludes` passed via `--settings`). This is the same pattern
as `adapters-normalize-harnesses`. Otherwise, Phase 1.1 already cuts that overhead by
about half.

### Measuring whether it worked

`memory_reads.jsonl` is already the instrument. Compare two weeks before and after:

- **Trigger health.** Reference-note reads per agent that changes code, especially
  `lint_and_test.md`, should not fall. Glossary lookups by non-research agents should
  stay at about 50 or more per month.
- **Decision discovery.** Non-research decision reads should rise once domain links
  land, or at least not fall.
- **Contract compliance.** The rate of turns ending without a `/sase_final`
  declaration, and of reads of other repos outside `/sase_repo`.

If a trigger's reads collapse, restore that line, not the whole file.

**What would change my mind:** non-research decision reads or `/sase_final` compliance
dropping noticeably after the decisions summaries go. In that case, keep a 5–6 item
"decisions every agent must honor" list in core. The candidates are
`host-owned-completion`, `check-full-is-explicit`, `guarded-recipes`,
`gates-never-block`, and `rust-core-required`. It would cost about 6 lines.

## Appendix A — measured mock of the rendered file (101 lines, ≈1,379 tokens)

```markdown
# Structured Agentic Software Engineering (SASE) - Agent Instructions

## 1. Core Memory

### 1.1 SASE Runtime Contract (sase)

- **End every turn with `/sase_final`.** Use it as the last action before any normal
  response that ends this provider turn, including incomplete-status responses. Never
  end a turn to wait: nothing can wake you, so hand long commands to `/sase_monitor`
  before starting them. Only an executed plan, monitor, pipe, or questions handoff is
  exempt.
- **Stay in your workspace.** You run in an ephemeral `sase_<N>` clone of this repo. Do
  not run commands outside it, and never name it in `/sase_plan` plans.
- **Reach other repos only through `/sase_repo`.** Before reading or modifying any repo
  other than this checkout (linked repos, sidecars, other projects, or any GitHub repo,
  including over the web), use `/sase_repo` and work only in the path it prints. Read
  sidecar artifacts only with `sase artifact read <ref> "<reason>"`. Linked:
  `sase-github`, `sase-telegram`, `sase-nvim`, `sase-research-artifacts`; sidecar:
  `sase--research`.
- **Memory files are not ordinary files.** Notes under `sase/memory/` render into this
  file. Read reference notes and web strands only with `/sase_memory_read`; use
  `/sase_memory_write` before creating, editing, or deleting one, or planning to.

### 1.2 Rust Core Backend Boundary (rust_core_backend_boundary)

Shared backend and domain behavior belongs in the `sase_core` crate of the linked
`sase-core` repo; call it from Python/TUI through `sase_core_rs` or a thin adapter,
never reimplement it. Litmus test: if another frontend would need the behavior to match
the TUI, it is core; presentation-only Textual code stays here. New bindings also need
`sase-core-revision.txt` bumped (see `docs/rust_backend.md`).

### 1.3 Gotchas (gotchas)

- When changing keymaps, leader-mode keys, or config values, update
  `src/sase/default_config.yml` too.

## 2. Reference Memory

Read these with `/sase_memory_read` when their trigger applies; never open them
directly.

1. **`sase/memory/lint_and_test.md`** - MUST read before finishing a turn that changed a
   git-tracked file in this repo (not under `sase/repos/`).
2. **`sase/memory/cli_rules.md`** - Read when adding CLI subcommands or options.
3. **`sase/memory/dispatch.md`** - Read before dispatching agents to a remote machine
   with `%dispatch`.
4. **`sase/memory/generated_skills.md`** - Read before changing sase agent skills or
   their `src/sase/xprompts/skills/` sources.
5. **`sase/memory/sase_artifacts.md`** - Read before creating, resolving, linking, or
   retaining artifact references.
6. **`sase/memory/sase_beads.md`** - Read before creating, updating, closing, or
   querying sase beads.
7. **`sase/memory/sase_flags.md`** - Read before adding or removing a feature flag, or
   deprecating user-reaching behavior.
8. **`sase/memory/symvision.md`** - Read before fixing Symvision lint failures.
9. **`sase/memory/tui.md`** - Read before changing the TUI, its screenshots or
   snapshots, or UI performance paths.
10. **`sase/memory/xprompts.md`** - Read before xprompts, prompt directives, or git/gh
    VCS workflow blocks.

## 3. Memory Webs

Read strands on demand, batching selectors:
`sase memory read <web>:<keyword> [...] -r "<why>"`.

### 3.1 Decisions (decisions)

Accepted architecture decisions: read one before changing the area it governs or
proposing to reverse it.

**DECISIONS:** A Gate Never Blocks An Agent; Adapters Normalize Harnesses; Agents Are
Single-Turn; Agents-Sync Is Publish-Only, The Import Leg Is Deleted; Check-Full Is
Explicit-Only; CI Is Two-Speed; Completion Is Host-Owned; Expensive Commands Are
Recorded Before They Are Admitted; Explicit Handoff Fails Closed; Goal Ledger; Goals
Host Binds; Guarded Recipes Refuse Raw Agent Runs; Hold Admission Uses Pull Evaluation
With Fail-Open TTL; Machine Artifact-Link Writes Stay Off the Primary; Memory Links Are
Authored; Memory Webs; Memory Webs Render In Their Own Section; No Retrieval Mechanism
Before Its Corpus; Receipts Prove Before They Skip; Size Aliases Descend The Effort
Ladder; The Rust Core Is Required; Triage Annotates; It Never Changes an Exit Code

### 3.2 Glossary Terms (glossary)

Read a term before relying on it; batch every term you need in one command.

**GLOSSARY TERMS:** Agent Clan; Agent Data Card; Agent Data Card Block; Agent Data Deck;
Agent Hood; Agent Instruction File; Agent Neighbor; Agent Node; Agent Relation Jump
Target; Agent Tab; Agent Tribe; Agent Turn; Artifact; Artifact Markdown File; Artifact
Reference; Core Memory; Current Project; Deck Panel; Failure Signature; Feature Flag;
Flag Bead; Gate Turn; Goal; Job; LLM Calls; Machine Tab; Memory Strand; Memory Web;
Named Proc; Nav Item; Nav Section; Node Panel; Oneshot Service Proc; Patch; Proc;
Project Tag; Prompt Stash; Receipt; Reference Memory; Required Plugin; Routine; Sase
Agent; Sase Agent Session; Sase Gate; Sase Monitor; Sase Node; Sase Project; Sase Repo;
Sase Scheduler; Sase Service; Sase Turn; Sase Workspace; Service Proc; Stash Trash;
Stitch; Strand Keyword; Task Type; Tool Catalog; Tool Run; Triage Verdict; Usage Window;
Xprompt; Xprompt Memory; Xprompt Part; Xprompt Swarm; Xprompt Workflow

### 3.3 Task Bead Types (task_types)

Capture discovered follow-up work as task beads unless your prompt forbids it (epic
phase workers record `PROPOSED FOLLOW-UP:` notes instead); always run `/sase_new_task`
first. **TASK TYPES:** Bug; CI failure; Feature; Flaky test; Memory.
```

## Appendix B — sources

- Claude Code memory docs: https://code.claude.com/docs/en/memory. Covers the
  under-200-lines guidance, imports still costing context, ancestor and lazy loading,
  `claudeMdExcludes`, and native AGENTS.md support (v2.1.277+).
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
- Claude Code skills: https://code.claude.com/docs/en/skills. The listing budget is 1%
  of context.
- Anthropic, "Effective context engineering for AI agents" (2025-09-29):
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic Agent Skills overview (progressive disclosure levels):
  https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
  (2026-02-11): https://openai.com/index/harness-engineering/. Quotes were taken from
  a verbatim mirror because openai.com returned 403.
- Codex AGENTS.md discovery and the 32 KiB `project_doc_max_bytes` cap:
  https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Gemini CLI GEMINI.md loading: https://geminicli.com/docs/cli/gemini-md/
- Vercel, "AGENTS.md outperforms skills in our agent evals" (2026-01-27):
  https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- Gloaguen et al., "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful
  for Coding Agents?", arXiv:2602.11988. The figures quoted are from v1; v3 numbers
  may differ.
- Jaroslawicz et al., "How Many Instructions Can LLMs Follow at Once?" (IFScale),
  arXiv:2507.11538
- Chatlatanagulchai et al., "Agent READMEs: An Empirical Study of Context Files for
  Agentic Coding", arXiv:2511.12884
- HumanLayer, "Writing a good CLAUDE.md" (2025-11-25):
  https://www.humanlayer.dev/blog/writing-a-good-claude-md
- Scott Spence, skill-activation evals (2026-02-08):
  https://scottspence.com/posts/measuring-claude-code-skill-activation-with-sandboxed-evals
- Chroma, "Context Rot" (2025-07-14): https://www.trychroma.com/research/context-rot

## Appendix C — method notes

- **Section sizes.** Sliced from the current `CLAUDE.md`. Token figures are bytes ÷ 4.
- **Read statistics.** From the project's `memory_reads.jsonl`. Multi-selector reads
  were expanded per resolved target. "Research" means the agent name starts with
  `research`.
- **History.** Sampled every 12th commit of `git log -- AGENTS.md`.
- **Mock.** Rosters were generated from the live webs via `ordered_web_strands`, with
  fully superseded strands dropped using `parse_strand_supersession(...).partial`. The
  file was formatted with the renderer's own `format_generated_memory_markdown`.
- **Not verified.**
  - Whether the current Claude Code build still wraps `CLAUDE.md` in a "may or may not
    be relevant" reminder. It is documented only in GitHub issues.
  - Gemini's exact ancestor boundary under its newer "trusted root" wording.
- **Memory changes.** None were made in this turn. Every recommendation that touches
  memory needs the authorization route described in §9.
