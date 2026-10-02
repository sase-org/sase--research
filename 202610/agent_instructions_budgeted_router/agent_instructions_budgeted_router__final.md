# Shrinking SASE's Agent Instruction Files to ≤100 Lines: A Budgeted Router, Not a Trim

_Lead researcher (consolidated) · 2026-10-02 · sase checkout `6cca547014` · inputs: five
independent reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`) plus my own
verification. Scope: the generated root `AGENTS.md` of the `sase` repo and its four
byte-identical provider copies (`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`)._

## 1. Bottom line

- **Yes, do it, but treat it as an architecture rule, not a cleanup.** All six analyses
  agree on this. The current file is 283 lines and about 4,300 tokens. It holds roughly
  eight hard rules and ten useful read triggers, plus about 150 lines of catalogs and
  explanation that most turns never use. Getting to 85–93 lines (about 1,200–1,400
  tokens) removes no rule and no trigger. cld got 93 lines and ~1,205 tokens by running
  a mock through the project's own formatter.
- **The one-time trim matters less than the mechanism that stops regrowth.** The file
  was trimmed by hand to 227 lines on 2026-08-29 and grew back to 283 by 2026-09-28.
  Almost all of that growth came from the decisions roster (§2.2). It has been trimmed
  and regrown several times since February (105 → 361 → 227 → 283). Without an
  always-on budget check, any trim lasts a few weeks.
- **The bloat is in the generator, not in your notes.** Flat notes are already mostly
  reference memory and work well. The 283 lines come from three renderer defaults:
  1. always-inlined memory-web rosters (51% of the file);
  2. the long shared `sase.md` template (76 rendered lines);
  3. multi-line reference descriptions.

  Fix those three. Don't move rules into new places.
- **Requirement changes I recommend (§6):**
  - Budget lines and tokens together: ≤100 lines at the configured 88-column width and
    ≤1,600 tokens.
  - Aim for about 85–90 lines.
  - Enforce the budget as a ratchet in `sase memory init --check`.
  - State the invariant as "router, not encyclopedia".
  - Judge success by agent behavior, not by `wc -l`.
- **Recommended mechanism (§9):**
  - Add two web roster densities: `names` and `none`. Leave superseded strands out of
    always-loaded rosters. Set `decisions` to `none`, and `glossary` and `task_types`
    to `names`.
  - Rewrite the shared `memory-sase.template.md` as a short runtime contract.
  - Make every reference trigger one line.
  - Add a budget check that reports cost per section.
  - Record a new decision that partly supersedes `webs-render-in-their-own-section`.
  - All of this is Python-only. No new retrieval mechanism.

## 2. What loads today (verified)

### 2.1 Anatomy of the 283 lines

All five root files are byte-identical (same md5): 283 lines, 17,285 bytes, and about
4,316 tokens by `sase memory list`'s `chars/4` heuristic. That heuristic is not a real
tokenizer count.

| Rendered section | Lines | ≈Tokens | Notes |
| --- | ---: | ---: | --- |
| Title and core intro | 6 | 37 | template |
| `sase.md`: memory-system explainer | 22 | 299 | generated from shared `memory-sase.template.md` |
| `sase.md`: workspace dirs | 10 | 139 | 〃 |
| `sase.md`: repos and cross-repo rule | 34 | 477 | 〃 |
| `sase.md`: final declaration | 10 | 138 | 〃 |
| `gotchas.md` | 6 | 62 | core |
| `rust_core_backend_boundary.md` | 17 | 240 | core |
| Reference index (10 notes) | 33 | 517 | `description:` frontmatter |
| Memory Webs intro | 6 | 61 | `_WEB_MEMORY_INTRO` in `src/sase/amd/_memory.py` |
| **Decisions descriptor and 24-row list roster** | **90** | **1,572** | `roster: list`, 36% of tokens |
| Glossary descriptor and 66-term inline roster | 27 | 477 | `roster: inline` with aliases |
| Task types and "file discovered work" rule | 23 | 289 | generated from a template |

Section sizes are from cld and cross-checked against my own heading slices: Core 103,
Reference 33, Webs 145.

### 2.2 Where the regrowth came from

I compared the 2026-08-29 trim (`b726d0a18c`) with today.

| Section | 2026-08-29 | Today |
| --- | ---: | ---: |
| Core | 99 | 103 |
| Reference | 76 | 33 |
| Webs | 56 | 145 |

The decisions subsection went from 4 lines to 90. In other words, the reference index
was cut in half, and a single linearly-growing roster ate all of those savings plus 56
more lines. **A roster that grows with its corpus does not belong in the always-loaded
file.** That observation decides the decisions-web question in §8.

### 2.3 Roster densities, measured with the real renderer

I ran `render_strand_roster` and `format_generated_memory_markdown` on the live webs:

| Web | `list` | `inline` |
| --- | ---: | ---: |
| decisions (24) | 79 lines / ~1,425 tok | 26 lines / ~542 tok |
| glossary (66) | 66 lines / ~651 tok | 18 lines / ~364 tok |
| task_types (5) | 8 lines / ~118 tok | 1 line / ~15 tok |

This confirms cld's claim: switching decisions from `list` to `inline` is a
**zero-code, one-line frontmatter change worth 53 lines**. Even so, `inline` still
grows linearly and still renders superseded tombstones. Two of the 24 rows are fully
superseded (`v1-import-retired`, `two-speed-verification`).

### 2.4 What else agents load (the "file" is not the unit)

- **Claude agents also load the home `~/CLAUDE.md`, which is an ancestor file.** It is
  74 lines and about 967 tokens. Roughly 45 of those lines repeat the same `sase.md`
  contract. A Claude agent's real instruction load is therefore about 357 lines and
  about 5,300 tokens. Codex reads only from the git root to the working directory, so it
  never sees the home file.
- **Grok loads `AGENTS.md` and `CLAUDE.md` both,** so the project instructions arrive
  twice. This is documented in `docs/agent_providers.md`, "Instruction double-load".
  gem's claim that Antigravity/Gemini double-loads `AGENTS.md` and `GEMINI.md` is
  **not documented anywhere in SASE, and I could not verify it**. Measure it before
  acting on it.
- **Adapters already inject the single-turn directive.** Claude gets it through the
  appended system prompt (`_SINGLE_TURN_DIRECTIVE`, `src/sase/llm_provider/claude.py`),
  Codex through `developer_instructions`, and Muse through a prompt prefix. The
  final-declaration paragraph partly repeats it.
- **Two existing knobs do not solve the problem:**
  - A custom `memory.agents_template` cannot just drop sections. Required variables
    and structural validation in `src/sase/amd/_template.py` and `_memory.py` forbid
    it.
  - The existing `AGENTS.minimal.template.md` renders **only** title and core. It
    drops the reference triggers, which are the most valuable part of the file, so it
    is the wrong tool.

### 2.5 How big is this relative to a whole turn? (new)

mus asked whether the instruction file is even a significant part of the context.
Nobody measured it, so I did. Across 284 recent Claude sessions in sase workspaces, the
first API call's total prompt size (input plus cache-create plus cache-read tokens) was:

- minimum about 25.2k tokens;
- 10th percentile 26.6k;
- median 30.1k;
- 90th percentile 40.3k.

The median session made **41 API calls**.

The fixed floor is about 25k tokens: harness system prompt, tool schemas, skill
listing, both instruction files, and a short prompt. Home plus project instructions are
**about 5.3k of that floor, roughly 20%**. The fix proposed here saves about 3k tokens
per call, or about 12% of the floor. Over a median session that is roughly 120k fewer
re-read tokens.

These are mostly cache reads, so the money or quota saving is real but modest. That
matches cld's framing: **the stronger reasons are rule adherence and stopping growth,
not cost.** It also shows that the other ~20k tokens (system prompt, tools, skill
descriptions) form a bigger sibling budget, which is out of scope here (§6H).

## 3. How agents actually use this content (audit log, corrected)

Source: `~/.sase/projects/gh_sase-org__sase/memory_reads.jsonl`, 2026-09-01 to
2026-10-02, 1,460 events. I counted distinct runs per target family, where a run is a
unique `artifacts_dir`. A run counts as "research" if its agent name starts with
`research`. The window has about 1,370 `ace-run` directories.

| Target | Non-research runs | Research runs | Always-loaded cost today |
| --- | ---: | ---: | --- |
| `lint_and_test.md` | 437 | 14 | 3-line trigger |
| `sase_sizes.md` (child of beads) | 220 | 9 | 0 (reached via parent) |
| `sase_beads.md` | 198 | 23 | 4-line trigger |
| `tui_perf.md` (child of tui) | 137 | 35 | 0 |
| `symvision.md` | 121 | 0 | 2-line trigger |
| `tui.md` | 108 | 31 | 2-line trigger |
| `glossary:*` | 58 | 56 | 27 lines |
| `sase_flags.md` | 57 | 14 | 3-line trigger |
| `sase_artifacts.md` | 50 | 48 | 2-line trigger |
| `decisions:*` | **20** | 51 | **90 lines** |
| `tailnet.md` (home, Claude-only) | 22 | 6 | via `~/CLAUDE.md` |
| `task_types:*` | 10 | 2 | 23 lines |
| `dispatch.md` | 2 | 1 | 2-line trigger |

**Correction to grk.** grk reported 727 distinct-agent hits for glossary and 214 for
decisions. Those numbers count every resolved strand as a separate hit; one batched
glossary read touches many strands. Counted per run, which is how cld counted, decisions
were opened by about 20 non-research runs in a month, about 1.5% of runs.

Conclusions:

1. **Short triggers work.** A 2–4 line "read X before Y" line brings in hundreds of
   runs. Child notes like `sase_sizes.md` and `tui_perf.md` get heavy traffic at zero
   always-loaded cost because their parent's read appends `## Children`. Every
   reference trigger stays.
2. **The decisions roster does not pay its way.** It costs 36% of the file and drives
   1.5% of runs to open a record. Its value as a passive warning is mostly redundant:
   - `check-full-is-explicit` and `guarded-recipes` are already stated and linked in
     `lint_and_test.md`, which 437 runs read.
   - `guarded-recipes` is also enforced mechanically (`_require-tool-run` in the
     `Justfile`).
   - `single-turn-agents` is injected by the adapters.
   - `host-owned-completion` lives in the `/sase_final` skill.
3. **The glossary roster works as a recognition index.** Seeing "Stitch" in the list
   tells an agent the word is a defined SASE term. Keep the names. Drop the alias
   parentheticals, since reads still resolve aliases.
4. **The task-type list is rarely used**, but the "file discovered work through
   `/sase_new_task`" rule inside its descriptor is a hard rule and must survive.

## 4. External evidence (checked)

| Source | What it supports | Status |
| --- | --- | --- |
| Anthropic, [Claude Code memory](https://code.claude.com/docs/en/memory) | Target under 200 lines per `CLAUDE.md` because longer files reduce adherence. `@imports` load at launch and do not reduce context cost. All ancestor files are concatenated. | Verified |
| Anthropic, [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Smallest set of high-signal tokens; minimal does not mean shortest. | Cited by cdx, cld, grk |
| OpenAI, "Harness engineering" (2026-02) | Replaced one big `AGENTS.md` with roughly 100 lines that serve "primarily as a map", plus a versioned docs system of record and lint keeping it valid. This is essentially the SASE design. | Cited by cld (quotes taken from a mirror) |
| Gloaguen et al., [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) | Context files do not generally improve success and add over 20% inference cost. Instructions are followed well; repository overviews do not help. Recommends "minimal requirements". | Verified |
| Khatri, [Two-agent ablation](https://arxiv.org/abs/2607.27250) (2026-07) | 288 runs with Claude Code and Codex comparing no context, always-on context, and **selective on-demand wiki**. Context strategy does not measurably move correctness (bounded to ≤10–15pp). Failures were implementation skill, not missing knowledge. | **New; verified.** On-demand disclosure did not hurt correctness. |
| [Probe-and-refine tuning](https://arxiv.org/abs/2606.20512) (2026-06) | A compact (≤3,000-character) guidance file tuned against probe tasks beat a larger static knowledge base (33.0% vs 28.3% resolve rate). | **New; verified.** Compact guidance tuned on behavior beats bulk. |
| Vercel, [AGENTS.md outperforms skills](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals) (2026-01) | A passive 8 KB **index** scored 100%. Skills scored at most 79%, and in 56% of cases the skill was never invoked. | Verified. Strongest argument for keeping pointers always loaded. |
| Jaroslawicz et al., IFScale (arXiv:2507.11538) | Adherence degrades as instruction count grows; omissions dominate; primacy bias. | Cited by cld, grk |
| Agent READMEs (arXiv:2511.12884) | Context files grow by frequent small additions with few deletions. The median Claude file is about 485 words; SASE's is about 2,450. | Cited by cld |

Two caveats:

- None of these studies shows that 100 lines is an empirical optimum. It is a
  practitioner convention (OpenAI's map, agent-config.com, AgentPatterns.ai).
- The benchmarks measure task correctness. Most of SASE's file is a **workflow
  contract** (`/sase_final`, `/sase_repo`, memory routing) that an agent cannot infer
  from code. That is exactly the "minimal requirements" category the papers say to
  keep.

**Read together:** keep the contract and the pointers; move catalogs and explanations
on demand. Doing so is unlikely to hurt correctness, and evidence against the
encyclopedic parts is consistent.

## 5. Critique: is ≤100 lines a good idea?

**Yes. Reasons, in order of weight:**

1. **Adherence.** The roughly eight rules that must hold on every turn compete with 90
   lines of decision summaries and a 66-term glossary. The file has 5 MUST, 2
   IMPORTANT, and 3 NOT/Never markers. As Anthropic's best-practices page puts it: "if
   you emphasize many lines, none of them stands out."
2. **Accretion.** Each new note or decision is a local choice with a global cost that
   nobody sees in total. A budget forces where something lives to be an explicit
   trade-off.
3. **The map pattern already works here.** The audit log shows routers bringing agents
   to deep content. Shrinking the always-loaded layer makes it more like the pattern
   SASE already uses well.
4. **Cost.** It's real, at about 20% of the per-call floor, but secondary because it is
   mostly cached.

**Where the plan as stated is weak:**

- **Lines alone are gameable.** Raising `markdown.print_width`, packing paragraphs, or
  adding `@imports` all "pass" without saving anything. SASE has done this before:
  between April and June 2026 the file was 8–46 lines only because it imported its
  notes or relied on dynamic memory, which was later removed.
- **"The file" is the wrong object.** What matters is what each provider actually loads:
  Claude's ancestor home file, Grok's double load, nested files that some providers
  load and others don't.
- **A one-time cleanup won't last** (§2.2). The enforcement is the deliverable.
- **Over-pruning is the real danger.** Progressive disclosure fails on the *read* side:
  if a trigger is gone, the note is effectively gone (Vercel: 56% never invoked). A
  rule needed *before* an action can't live behind a read. For example, the
  repo-access rule can't be hidden behind a repo-access read.

**Would I take a different approach?** Same destination, different emphasis. The
architecture is already right: core, reference, and web memory, audited reads, and
parent/child notes. I would not add a new memory kind, a retrieval engine
(`decisions:corpus-before-mechanism`), `@imports`, or a move of everything into skills.
I would:

1. make the renderer emit a router;
2. make the budget a lint ratchet with per-section attribution;
3. record the policy as a decision, so the next well-meant roster can't quietly
   re-inline itself.

## 6. Requirement adjustments (explicitly flagged)

> **A. Scope.** The budget applies to the generated **root `AGENTS.md`**. The four
> provider copies inherit it because they are byte-identical. Nested files (`tools/`,
> `src/sase/ace/`, `demos/tapes/`) and the home file are separate. The nested files are
> already small; the home file shrinks automatically through the shared template
> (§9.2).

> **B. Units.** Require **≤100 lines at the configured 88-column width _and_ ≤1,600
> tokens** using `sase memory list`'s estimate. `@imports` count toward the budget.
> Also *report* each provider's effective total (Claude adds home; Grok doubles)
> without failing on it.

> **C. Headroom.** Aim for **about 85–90 lines.** A file sitting at exactly 100 breaks
> on the next core note, and the easy "fix" is then to raise the limit.

> **D. Enforcement is the deliverable.** `sase memory init --check` fails over budget
> and prints a line and token table per section, so the author sees what to demote.
> Use a **ratchet, not a cliff**: set the limit at the current size when the check
> lands, and lower it as each phase lands. The limit goes up only through a reviewed
> config change.

> **E. Invariant: "router, not encyclopedia."** Every always-loaded line must be one
> of two things:
>
> - a rule that applies on most turns *and* is not already enforced mechanically, or
> - a trigger that routes to on-demand content.
>
> Every reference note keeps a trigger. Superseded records never render into
> always-loaded context.

> **F. Hard rules are never demoted.** These eight stay always loaded:
>
> 1. `/sase_final` as the last action; `/sase_monitor` for long work.
> 2. `/sase_repo` before touching any other repo, over any transport.
> 3. `sase artifact read` for sidecar artifacts.
> 4. `/sase_memory_read` and `/sase_memory_write` routing.
> 5. Stay in the workspace and keep `sase_<N>` out of plans.
> 6. Read `lint_and_test.md` after changing tracked files.
> 7. The Rust-core litmus test.
> 8. File discovered work through `/sase_new_task`.

> **G. (New) Mechanically enforced rules get one line, not a paragraph.** Guarded
> recipes, host-owned completion, and adapter-injected single-turn text already fail
> closed or arrive through the harness. Prose belongs to rules that cannot be enforced.

> **H. Success is behavioral.** Meeting the line count is necessary but not enough.
> Trigger health and contract compliance must not regress (§9.5). Out of scope, but
> track each as a separate bead:
>
> - the skill-description budget, the larger sibling cost in §2.5;
> - Grok's double load;
> - Symvision text duplicated in `tools/AGENTS.md`.

## 7. Options considered

| Option | Verdict | Why |
| --- | --- | --- |
| Compress renderer output: roster density, short `sase.md`, one-line triggers | **Adopt** | Removes the measured cost while keeping every trigger. All Python and templates. |
| Budget ratchet with per-section attribution | **Adopt** | The only thing that stops §2.2 from happening again. |
| New decision record ("always-loaded instructions are a budgeted router") | **Adopt** | `webs-render-in-their-own-section` explicitly reopens for "a new, explicitly scoped opt-out mechanism" once inlining becomes a token-budget problem. That has now happened. |
| Link decisions from heavily read reference notes (`[[decisions:…]]`) | **Adopt (incremental)** | Shows a decision where agents already go, e.g. artifacts → `machine-link-writes-off-primary`. `lint_and_test.md` already does this. |
| Global `memory.web_context: index` switch (cdx) | Reject in favor of per-web density | Too coarse. The glossary names list earns its place (§3) and decisions does not. Per-web density fits the decision's "scoped" wording. |
| `inline_in_agents: false`, a per-web opt-out to the reference section (grk option C) | Defer | Equivalent to `roster: none` plus a short descriptor, but adds a placement axis that brings back the `type:` confusion. Revisit when there are 5+ webs. |
| `AGENTS.minimal.template.md` | Reject | Drops reference triggers. |
| `@imports` / one-line shims | Reject | Still loaded by Claude, not expanded by Codex. Already tried in April–June 2026. |
| Move rules or catalogs into skills | Reject as the main lever | Skills under-trigger, and their descriptions are another always-loaded catalog. |
| Keyword or dynamic retrieval, embeddings | Reject | Built and removed three times (`corpus-before-mechanism`). Existing `sase memory web show <web> "<pattern>"` covers discovery. |
| Nested or path-scoped files as the main mechanism | Reject | Loading differs by provider; Codex at the root never loads them. |
| Move contract text into adapter-injected system prompts | Later, partial | Carries more weight and is SASE-run-only, but it is invisible to memory review and not uniform across adapters. Drop duplicated "never wait" prose only once every adapter injects it. |
| Claude adapter `claudeMdExcludes` for the home file (cld) | Don't, for now | 22 non-research runs read the home-only `tailnet.md` this month, so home memory is in use. The shared template rewrite roughly halves the home overhead anyway. |
| Do nothing | Reject | Underestimates the adherence cost and ignores growth. |

## 8. Where the researchers disagreed, and how I resolved it

| Question | Positions | Resolution and evidence |
| --- | --- | --- |
| What happens to web rosters? | cdx and gem: index only, no rosters. cld: titles-only for every web. grk: `roster: index` plus a cap. mus: top-N plus a list view. | **Per web.** Decisions: `none` (O(1) pointer). It drives 1.5% of runs to a read, its pre-action rules arrive through `lint_and_test.md` or the harness, and it caused the regrowth. Glossary: `names` (it works as a recognition index). Task types: `names` on one line plus the hard rule. |
| Does the work cross the Rust boundary? | cdx: budget and projection policy in `sase-core`. cld and grk: Python-only. | **Python-only.** `src/sase/amd`, `src/sase/memory`, and `init_memory` have no `sase_core_rs` call sites. Rendering instruction files is a generator, not runtime behavior another frontend must match. Revisit only if a web or TUI surface starts showing budget data. |
| Hard fail or warn first? | cld: lint failure. grk: warn, then block later. | **Blocking ratchet from day one,** with the limit set to the current size and lowered each phase. Nothing is held hostage, and nothing stays advisory forever. |
| Token ceiling | 1,500 (gem), 1,600 (cld, mus), 2,000 (cdx, grk) | **1,600.** That's what a readable 100-line file at 88 columns comes to (cld's mock: 101 lines ≈ 1,379 tokens). 2,000 would let 100 lines get dense. |
| Is the file a meaningful part of context? | mus: maybe not; measure. | **Measured (§2.5):** about 20% of a Claude call's fixed floor. Meaningful, but the case rests on adherence and growth. |
| Glossary and decision usage | grk: 727 and 214 hits. cld: 109 and 69 agents. | **cld is right** (§3). grk counted strand resolutions, not runs. |
| Antigravity double load | gem: 566 lines loaded | **Unverified.** Only Grok's double load is documented. |
| Prompt-cache stability as a reason | gem: strong | **Weak.** Each workspace's system prompt already differs (cwd), and SASE sessions are short-lived. Stability within a session holds either way. |

## 9. Recommended solution

**Make the generated `AGENTS.md` a budgeted router.** That means hard rules, one-line
triggers, and constant-size web entries. Enforce it with a ratchet and govern it with a
decision record.

**Target:** about 85–93 lines and about 1,200–1,400 tokens. The hard ceiling is 100
lines and 1,600 tokens. cld's formatter-measured mock (`__cld` Appendix A, with the
decisions roster replaced by a pointer) is 93 lines and about 1,205 tokens, and it keeps
every trigger.

All memory edits below go through `/sase_memory_write`: an approved plan that names
each file, with confirmation from the user. `sase/memory/sase.md` and `task_types.md`
are generated, so they change only through their templates.

### 9.1 Phase 0: content only, no code (about 283 → 190 lines)

1. `sase/memory/decisions.md`: change `roster: list` to `inline` (measured: −53 lines).
   Cut the descriptor prose to two lines. The guidance on how to write decisions belongs
   in `/sase_memory_write`, not in every turn.
2. Reference notes: rewrite each `description:` as one imperative trigger of 90
   characters or less ("Read before …"). Keep `lint_and_test.md` as the only MUST.
3. Shorten `rust_core_backend_boundary.md` to about 5–7 lines: litmus test, binding,
   pin. Fold `gotchas.md` into one bullet. Do **not** demote either one.
4. Add the missing `description:` values for `glossary` and `task_types`.
   `sase memory web list -f json` currently shows `null` for both.

### 9.2 Phase 1: renderer and templates, one small Python epic (→ about 85–93 lines)

1. **Rewrite the shared `src/sase/main/init_memory/templates/memory-sase.template.md`**
   from 76 rendered lines to about 18–20: a four-to-six-bullet runtime contract.
   - Linked repos render as names only; `sase repo list` has the descriptions.
   - Transport details and the explanation of memory kinds move into the skill bodies
     that already contain them.
   - Because this template is shared, the change also shrinks every other SASE project
     and the home root (`~/CLAUDE.md`, 74 → about 35 lines). That is a deliberate
     product change.
2. **Roster density** in `src/sase/memory/web/models.py` (`WebRosterStyle`) and
   `roster.py`:
   - Add `names`: titles or keywords only, no aliases or summaries.
   - Add `none`: renders as "N strands; browse with `sase memory web show <web>`".
   - Always-loaded rosters leave out **fully** superseded strands; partly superseded
     strands keep their marker. `sase memory web show` still lists everything.
   - Set `decisions: none`, `glossary: names`, and `task_types: names`, keeping the
     2-line `/sase_new_task` rule in the task-types template.
3. **Validation and intros:**
   - Shorten `_LONG_MEMORY_INTRO` and `_WEB_MEMORY_INTRO` in `src/sase/amd/_memory.py`
     to one sentence each, with one shared "how to read" line.
   - Their first sentences are structural anchors, so update the checks in `_memory.py`
     and `_template.py` at the same time. Do not hide content in comments to satisfy
     the validators.
4. **Budget check.** Add `memory.instructions_budget: {max_lines, max_tokens}` to the
   `sase/sase.yml` schema.
   - `sase memory init` prints a line and token table per section.
   - `--check` fails over budget.
   - `sase memory list` and `sase doctor` *report* each provider's effective total
     (home ancestors, Grok double load).
   - Start the limits at the measured size and lower them as each step lands.
5. **Tests:**
   - `none` and `names` rosters leak no summaries;
   - superseded strands are omitted;
   - the core and reference sets are complete;
   - provider copies stay identical;
   - the budget failure path works;
   - custom templates and the home overlay still render.

### 9.3 Phase 2: governance and routing

1. New decision record, "Always-Loaded Instructions Are A Budgeted Router". It records
   the invariant (§6E), the budget, and the per-web density mechanism. It marks
   `webs-render-in-their-own-section` **partly** superseded, for its Cost clause only.
   Descriptors still render in their own section, just compactly.
2. Add `[[decisions:…]]` links from heavily read reference notes to the decisions that
   govern their domains, so decisions show up where agents already are.

### 9.4 What I would not do

- Revive keyword or dynamic memory.
- Put `type:` back on web descriptors.
- Use `@import` shims.
- Move hard rules into reference notes or skills.
- Make 100 lines a cliff in the same PR that changes the generator.
- Apply one budget to every instruction file in the repo.

### 9.5 Measuring it and rolling back

The audit log (`memory_reads.jsonl`) is already the measuring tool. Compare the two
weeks before and after the change:

- **Trigger health.** `lint_and_test.md` reads per code-changing run must not fall
  (baseline: 437 runs per month). Non-research glossary lookups should stay around 50 or
  more per month.
- **Decision discovery.** Non-research decision reads (baseline about 20 per month)
  should not fall, and should rise once the domain links land.
- **Contract compliance.** Turns ending without a `/sase_final` declaration, and
  other-repo access outside `/sase_repo`, should hold steady.
- **Optional spot check.** Run a handful of scripted scenarios before and after: typo
  fix, keymap change, Rust-owned feature, linked-repo read, bead filing, long-command
  handoff, incomplete turn. Use cdx's list.

**Rollback is per line, not per file.** If one trigger's reads collapse, restore that
line.

**What would change my mind:** non-research decision reads or `/sase_final` compliance
dropping noticeably after the decisions roster goes. In that case, add a "decisions
every agent must honor" list of five or six titles to core, for about 6 lines:
`host-owned-completion`, `check-full-is-explicit`, `guarded-recipes`,
`gates-never-block`, `rust-core-required`.

### 9.6 Follow-up beads (separate from this effort)

1. A budget for skill descriptions. SASE-deployed skill descriptions are about 1k tokens
   and growing, and sit inside the larger ~20k-token harness floor.
2. Grok double load: stop *injecting* `CLAUDE.md` into the Grok subprocess while still
   generating it on disk.
3. `tools/AGENTS.md`: point to `symvision.md` instead of duplicating it.
4. Verify Antigravity's actual instruction-file loading.

## Appendix: target line budget

| Block | Lines |
| --- | ---: |
| Title, section headings, one-sentence intros | 8–10 |
| Runtime contract (from `sase.md`) | 18–20 |
| Rust boundary | 6–7 |
| Gotchas | 2–3 |
| Reference index (10 one-line triggers and one intro line) | 18–22 |
| Memory Webs intro and read syntax | 3 |
| Decisions: heading, 2-line purpose, `none` pointer | 5 |
| Glossary: heading, 1 line, `names` roster | 13–15 |
| Task types: heading, `/sase_new_task` rule, names | 5–6 |
| **Total** | **≈ 85–93** |
