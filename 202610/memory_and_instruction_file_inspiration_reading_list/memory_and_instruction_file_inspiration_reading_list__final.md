# Reading List: Recent Articles to Improve SASE Memory and Instruction Files

- **Lead researcher:** final consolidation of five independent swarm reports (cdx, cld,
  grk, mus, gem) plus my own verification and gap research
- **Date:** 2026-10-06
- **Publication window:** 2025-10-06 → 2026-10-06. Older items are marked where they appear.
- **Question:** Which recent articles are most likely to inspire concrete improvements to
  sase's memory notes (`sase/memory/`: core, reference, webs) and the agent instruction
  files generated from them (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, generated skills)?

---

## Bottom line

**Read these five first:**

1. **Chakrabarti, *Why Does CLAUDE.md Keep Growing?*** Explains why instruction files
   only ever grow, and tests a fix: record why each rule exists, outside the model's view.
2. **Gloaguen et al., *Evaluating AGENTS.md*.** The best evidence on what always-loaded
   context costs and what it buys.
3. **Segner, *Steering Claude Code*.** The clearest guide to which mechanism a sentence
   belongs in: always-on file, skill, hook, or path-scoped rule.
4. **Zhang et al., *Guardrails Beat Guidance*.** Prohibitions help; positive "do X"
   directives are the risky kind.
5. **Davidson, *Coding Agents Love Decision Records*,** read together with
   **Nakayashiki, *When Stale Constraints Go Unchecked*.** Both apply directly to the
   `decisions` web.

**The thesis these readings share for sase:**

- **The architecture is right; the remaining work is maintenance.** sase already has
  the shape the 2026 literature recommends: a small core, on-demand references, keyed
  webs, skills, guarded recipes, immutable decisions, and audited reads. None of the
  strong sources argues for a vector store, automatic linking, or a runtime instruction
  router. The pressure is on three things:
  - **Budget:** what earns a place in always-loaded text.
  - **Wording:** prohibitions over directives, reasons over emphasis, descriptions
    written as triggers.
  - **Rationale and staleness:** why each rule exists, whether it is still true, and what
    replaced it.
- **The case for trimming is about cost, not correctness.** Several controlled studies
  find that file size and position barely change adherence. Always-loaded text does
  reliably add cost and anchoring. Trim for cost, cache efficiency and maintainability,
  and never trim hazards, prohibitions, or rationale.
- **Agent-written memory needs a human gate.** Self-generated skills scored *below* no
  skills, and self-edited context can plant instructions. Every shipping learning loop
  works the same way: an agent proposes, a human reviews, then the change is applied.
  sase's gated write path is right; what it lacks is a source of proposals.

The full ranked list is [at the end](#ranked-reading-list).

---

## Method

- **The five reports.** I read all five through `sase artifact read` and compared their
  picks, their evidence, and where they disagreed.
- **Fact-checking.** I checked about 40 cited sources against primary pages (arXiv
  abstract and HTML pages, first-party blogs and docs). That covered every top-10 pick
  from every researcher and every claim only one researcher made. Corrections are in
  [Corrections](#corrections-to-claims-in-the-swarm-reports).
- **Gap search.** I searched for in-window work none of the five found. Seven items made
  the list:
  - Nakayashiki on stale inherited constraints
  - SkillSeam on auditing skill collections
  - EA-Graph on memory anchored to code artifacts
  - Concord on stale context
  - Claude Code's AGENTS.md loading rules
  - Claude Code's `/doctor prompt-audit`
  - Codex Memories
- **Measuring sase.** I measured the generated instruction files and analyzed the
  audited memory read log: 16,833 reads from 2026-07-06 to 2026-10-06.

---

## Where sase stands today (measured 2026-10-06)

### Generated instruction file

`AGENTS.md`, `CLAUDE.md` and `GEMINI.md` are identical: 290 lines, 17,954 bytes. The
always-loaded body is 2,497 words.

| Section | Words | Share | Note |
|---|---:|---:|---|
| `decisions` web index | 885 | 35.4% | 25 rows; 4 carry supersession marks (2 fully, 2 partly superseded) |
| `sase` core (memory, workspaces, repos, final declaration) | 669 | 26.8% | Mostly procedures ("MUST use `/skill` before Y") |
| `glossary` term list | 279 | 11.2% | |
| Reference-memory index | 264 | 10.6% | 10 notes, several written as "Read before *domain*" |
| `task_types` | 182 | 7.3% | |
| Rust core boundary | 140 | 5.6% | |
| Gotchas | 26 | 1.0% | |

- **Emphasis tokens:** 5 × MUST, 2 × IMPORTANT, 2 × "Do NOT", 3 × "Never". Most MUSTs are
  positive "use skill X" directives.
- **Duplication for Claude sessions.** `~/CLAUDE.md` duplicates 48 of its 58 non-empty
  lines (543 of 614 words) word for word from the project file. Claude Code also loads
  `CLAUDE.md` from parent directories, so Claude agents under `$HOME` get the generic
  SASE memory, repository and final-declaration sections twice.
- **Claude Code and AGENTS.md (v2.1.277, 2026-09-18).** Claude Code now reads
  `AGENTS.md`, but only when no `CLAUDE.md` exists. sase's identical `AGENTS.md` and
  `CLAUDE.md` therefore load once in the default mode, but would load twice in the
  "load both" mode. Codex's `project_doc_max_bytes` defaults to 32 KiB, so the 18 KB file
  has about 14 KB of headroom before Codex stops adding nested files.

### What agents actually read

The audited memory read log covers the last 30 days. In that period 3,275 distinct
agents read at least one memory file.

| Memory | Distinct agents in 30 days | Note |
|---|---:|---|
| `lint_and_test.md` | 2,021 (62%) | Reference note that says "MUST read before you finish" |
| `sase_beads.md` | 1,175 (36%) | |
| `sase_sizes.md` | 916 (28%) | Child note, not in the index; reached via `[[sase_sizes.md]]` in `sase_beads.md` |
| `symvision.md` / `sase_artifacts.md` | 567 / 557 | |
| `tui_perf.md` / `tui.md` | 424 / 370 | The child note is read more than its parent |
| **All 25 decision records combined** | **96 agent-reads, 18 distinct records** | The index costs 885 words in every agent's context |

**What this suggests:**

1. **Hot notes may be cheaper inlined.** `lint_and_test.md` is a strong candidate for
   Skill Blocks' break-even analysis: compress it and inline it, or inject it with a
   hook for turns that edit files. This cuts both ways. The note may be read so often
   precisely because it is on demand and the core text tells agents to read it.
2. **The decisions index is paid for constantly but rarely followed into.** Bodies are
   rarely fetched. That fits either of two explanations: the one-line descriptions
   already do the job (Skill Blocks' "hybrid" case), or most rows are dead weight.
   Measuring which is cheap: drop superseded rows and watch read counts.
3. **sase's own data partly contradicts Gao & Chen's "agents never follow links."**
   Child notes reachable only through authored, *imperative* links ("read
   [[sase_sizes.md]]") are read heavily. The likely lesson is that agents follow links
   phrased as instructions, not links offered as navigation.

**Caveat:** the denominator counts only agents that read *some* memory. Agents that read
none are invisible here.

---

## Where the reports agreed and disagreed

### Consensus picks

| Pick | Researchers who chose it |
|---|---|
| Gloaguen | cdx, cld, grk |
| ACE | cdx, cld, grk |
| Anthropic Agent Skills | cdx, mus, grk |
| Shihipar's "new rules" | grk, mus |
| HumanLayer | cdx, cld |
| OpenAI Harness engineering | cdx, cld |
| Letta Context Repositories | cdx, cld |
| McMillan | cld, gem |
| SkillsBench | cdx, cld |

cld's report was the broadest and the best sourced. Its claims needed the most
correction (below) but none were fabricated.

### Disagreements and how I resolved them

1. **gem's ranking.** Its top 10 included three out-of-window papers:
   - A-MEM (Feb 2025) and Zep (Jan 2025)
   - ACON (2025-10-01, five days early)

   It also favored mechanisms that conflict with standing sase decisions:
   - a runtime instruction router, which conflicts with `corpus-before-mechanism`
   - automated Zettelkasten linking, which conflicts with `memory-links-are-authored`
   - bi-temporal graph memory

   gem's #2, Franko's ITR (arXiv 2602.17046), reports 95% / +32% / −70%. Those numbers
   come from what the paper calls a "controlled benchmark with internally consistent
   numbers": it names no model and partly rests on assumed parameters. SkillOps, CoMem
   and Socratic-SWE are real but evaluated mostly on ALFWorld or PDDL, or are about
   training rather than file authoring. **Resolution:** I demoted all of these. McMillan
   stays, with gem's reading corrected (see below).
2. **mus's ranking.** It relied on secondary sources: SurePrompts, a Towards AI explainer,
   and dev.to posts. SurePrompts listed Claude Code as an AGENTS.md reader weeks before
   Claude Code supported it. **Resolution:** I kept Shihipar and the Agent Skills post. I
   replaced the secondary items with the first-party pages they summarize: Claude Code
   memory docs, `/doctor prompt-audit`, and Codex docs.
3. **"Shorten the file" vs "size doesn't matter."**
   - For size not mattering: McMillan and Guardrails found no adherence effect from size,
     position or nesting, and random rules helped as much as curated ones.
   - For shortening: Gloaguen found always-on files add about 20% cost and change
     behavior.
   - Each side measures something different, so both hold. **Resolution:** trim for cost,
     cache efficiency and anchoring, keep hazards and prohibitions, and judge changes on
     sase's own tasks.
4. **Automating memory learning.** cld and gem wanted a transcript miner; grk had low
   confidence in it. The evidence favors a strict version:
   - SkillsBench v4: self-generated skills *hurt*, by −8.1 to −11.5pp.
   - *Context Language Models*: models with write access planted unauthorized
     instructions.
   - Gemini CLI and Codex: both ship "propose, review, apply".

   **Resolution:** a proposal-only inbox, human-applied, with core off-limits. sase's
   `host-owned-completion` and gated write already point this way.
5. **OpenAI's Harness engineering.** cdx ranked it #2 and cld ranked it #28. The page
   blocks automated fetchers, so its claims are confirmed only through mirrors. sase
   research already has an `openai_harness_engineering_vs_sase` report. **Resolution:**
   Tier 3. Its new idea for sase, CI checks on documentation structure and freshness, is
   better served by `/doctor prompt-audit` and Codified Context.

### Corrections to claims in the swarm reports

| Claim as reported | Verified version |
|---|---|
| Chakrabarti: give each instruction a **stable ID** plus a hidden comment | The paper avoided stable constraint IDs because they "leak" the answer. The comment carries a round stamp, the verbatim failure, a recurrence count, the falsification lineage, and replaced text. The +211% → +1.4% result comes from a synthetic testbed (1 seed, wide CIs), not real repos. |
| Skill Blocks: "hybrid stubs win" | The paper says there is "no universal winner". Hybrid was best only in single-turn cells; pure on-demand won on large multi-turn tasks. Single-turn cells are the relevant case for sase's single-turn agents. |
| Guardrails: "no unrelated refactor" alone +20pp; "follow code style" −14.3pp | The +20pp is leave-one-out: the drop when that rule is removed. The −14.3pp is not significant (p=.18). The polarity result is p=.029 (Fisher). |
| Rule Taxonomy: pruning is 1.79% of changes | That figure is not in the paper (it equals 9 of 504 classified events). Deletions overall are about 19% of evolved rules. |
| Probe-and-Refine: Qwen-tuned guidance dropped Nemotron 27.0% → 13.2% | The 27.0% is Nemotron's *own tuned* guidance. Nemotron with no guidance scored 28.4%, so every guidance condition hurt Nemotron. |
| McMillan: compliance "drops 5.6% per generation step" (gem) | The odds of compliance fall about 5.6% per additional function (OR 0.944), and the decline is non-monotonic. Only the size and conflict nulls have Bayes-factor support. gem's "overwhelming validation of single-turn agents" overreaches. |
| SkillsBench: self-generated skills "provide no benefit" | v4 (2026-06-14) is stronger: they score below baseline. |
| "Breunig, O'Reilly Radar" | The O'Reilly piece is by Tim O'Reilly, writing about Breunig's talk. The nilenso post is by Srihari Sriraman and Drew Breunig. |
| HumanLayer: root file "< 60 lines" | Their own file is under 60 lines. They also say "< 300 lines is best". |
| Shihipar's 4th shift: "repetition → single descriptions" | The heading is "Repeat yourself → Simple tool descriptions". |

---

## Themes and what each suggests for sase

Each theme lists the strongest sources, then sase-specific ideas. These are
inspirations, not a plan. Any change to a memory file goes through `/sase_memory_write`.

### 1. What earns a place in always-loaded text

**Evidence**

- Gloaguen et al. compared LLM-generated and developer-written context files:
  - Generated files lowered success slightly and raised cost 20–23%.
  - Developer-written files gave a non-significant +2.4% and still raised cost up to 19%.
  - Agents follow what the files say (`uv` mentions → 1.6 `uv` calls per task).
  - Repository overviews did not help agents find the relevant file faster.
  - Removing a "Testing" section cut cost with no accuracy change.
- Khatri: no correctness gain, except that one numeric hazard ("full suite takes
  >20 minutes") cut blind full-suite runs and wall-clock time by about 24%.
- Lulla et al.: AGENTS.md cut median runtime 29% and output tokens 17%, mostly by
  preventing a few runaway sessions.
- Probe-and-Refine: guidance under 3,000 characters, tuned on observed failures, raised
  SWE-bench Verified from 25.5% to 33.0%. The same guidance did not transfer across
  models.

**For sase**

- Keep **non-inferable hazards with numbers** in core: expensive commands, root-only
  actions, prohibitions.
- Move or cut anything an agent could discover from the repo.
- The first trimming target is the `decisions` index (35% of the file):
  - Drop superseded rows from the inline list; they stay readable by key.
  - Rewrite each row as "when this matters", not as a summary of the decision.
- Remove the duplicated generic sections from `~/CLAUDE.md`.
- Consider a byte budget, enforced as lint, on the generated file.

### 2. Wording: polarity, emphasis, reasons

**Evidence**

- Guardrails Beat Guidance: every individually helpful rule was a prohibition.
- Vercel: "You MUST invoke the skill" made agents anchor on the skill's docs and miss a
  required config change.
- Anthropic's prompting docs say to drop "CRITICAL: You MUST" wording for current models.
- Shihipar: Claude Code removed over 80% of its system prompt for Claude 5-generation
  models with "no measurable loss" on its coding evaluations. The changes included
  replacing rules with judgement and examples with interfaces, plus progressive
  disclosure.
- nilenso and Tim O'Reilly (on Breunig): repetition and escalating emphasis are
  "prompt debt".

**For sase**

- **Sort every "MUST use `/skill_x` before Y"** into one of three forms:
  - a *guarantee*, which becomes a hook, gate or guarded recipe (sase already prefers
    this; see `decisions:guarded-recipes`)
  - a *judgement call*, whose trigger moves into the skill description, with the MUST
    dropped
  - a *prohibition*, kept in core and phrased as "Never Y without Z"
- **Require a reason clause** on every surviving MUST or NEVER.
- **Consider GitHub's Always / Ask first / Never tiers**, with emphasis reserved for the
  Never tier.

### 3. Rationale, growth, and how memory should change

**Evidence**

- Chakrabarti mined 247,694 instruction lifetimes across 1,867 repos:
  - Files grow by up to +226% over their lifetime.
  - 76.8% of instruction deaths happen in wholesale rewrites, and files regrow to 91.5%
    of their old size within 10 commits.
  - Old rules survive because nobody remembers why they exist.
  - Hidden comments recording the originating failure *and its outcome* curbed growth in
    a synthetic testbed. Placebo comments did not.
- Cai et al.: compliance jumps after a rule is updated (49% → 72%), then decays to about
  65% within 4–5 commits.
- ACE warns against *brevity bias* and *context collapse*: a whole-playbook rewrite
  shrank one context from 18,282 tokens to 122 and dropped accuracy below baseline. It
  recommends itemized, incremental updates.

**For sase**

- **Extend the decision-record discipline** (claim, why, cost, reopen condition) down to
  core directives, gotchas and skill rules. The rationale lives in a source-side comment
  that `sase memory init` strips.
- **Have `/sase_memory_write` ask for the originating failure** when a rule is added.
  This is cheap at write time and cannot be reconstructed later.
- **Prefer pruning one item at a time over periodic full rewrites.**

### 4. Staleness, especially in the `decisions` web

**Evidence**

- **Davidson:**
  - Agents "fight tooth and nail to apply an accepted decision even when it is
    obsolete."
  - Status needs explicit meaning: accepted ADRs are binding, proposed ADRs are
    non-binding, and superseded ADRs "do not govern current work".
  - On conflict, the agent should stop and propose a change.
  - Avoid "courtroom transcripts".
- **Nakayashiki** (new; 16 models):
  - Given a superseded constraint that "reads as settled", models checked its provenance
    in only about 1 episode in 5.
  - They acted on the stale constraint in 74.7–77.3% of episodes.
  - Pointing one verification step at the provenance path recovered 61–74 points.
- **Codified Context** (an experience report from one developer): "Specification
  staleness was the primary failure mode." Its fix is a session-start drift detector that
  maps subsystems to files.
- **GitHub Copilot memory:**
  - Memories carry `file:line` citations that agents check before use.
  - A/B result: 90% vs 83% PR merge rate.
- **EA-Graph** (new): claims anchored to code artifacts beat prose notes, and claims are
  marked "unproven" when their code is gone.
- **Claude Code `/doctor prompt-audit`** (v2.1.283, 2026-09-25): a first-party audit of
  `CLAUDE.md`, skills and commands. Stale paths, stale commands and contradicting files
  lead its report.
- **Codex Memories:** a memory unused for 30 days (default) stops being eligible for
  consolidation.

**For sase**

- **Add a one-sentence conflict protocol to the decisions descriptor:** "If a task
  conflicts with an accepted record, stop and propose a superseding record." The reopen
  condition only helps if the agent knows what to do when it is hit.
- **Remove superseded rows from the inline index.** Nakayashiki suggests they anchor
  agents rather than inform them.
- **Make `sase memory read` of a superseded record print its successor** (from
  `superseded_by`).
- **Add optional `covers:` path globs or `citations:` to reference notes and strands,**
  plus a `sase memory verify` or lint drift check whose warning appears in `memory read`
  output. Agents are single-turn, so the warning must travel with the read, not with
  session start.
- **Lint for relative time words** in notes ("recently", "currently").
- **Model the lint on `/doctor prompt-audit`.**

### 5. Progressive disclosure: when to inline, and how to write the pointer

**Evidence**

- **Skill Blocks**, the first comparison that accounts for prompt caching correctly:
  - Cache reads were 74–94% of input, so raw token counts can rank methods wrongly.
  - On-demand loading saved 53–73% of effective input for large content agents rarely
    needed.
  - Round-trips erase the savings for small or hot content.
  - Forcing "load before answering" cost +48%.
- **SkillJuror:** pointers raise resource use and help repair, but hurt when exact
  thresholds or formats are spread across files.
- **Gao & Chen** (557 sessions): instruction files plus agent notes are 60.5% of all
  documentation interactions. Agents never verify docs against code.
- **Vercel:** a skill went uninvoked in 56% of cases, while an 8 KB compressed index
  inlined in AGENTS.md scored 100%.
- **Shihipar, "How we use skills":**
  - "The description field is not a summary, it's a description of when to trigger this
    skill."
  - Gotchas sections are the highest-signal content in a skill.
- **SkillSeam** (new): bland triggers raised routing conflicts from 3 of 32 to 30 of 32;
  overlapping ownership caused conflicts in 14 of 16 cases.
- **Anatomy to Smells:** 237 of 238 SKILL.md files had smells. Rationalization Loophole
  appeared in 94%, Buried Gotchas in 81%.

**For sase**

- **Rewrite reference, strand and skill descriptions as trigger-plus-payload stubs:**
  "Read when *X*; key hazard: *Y*."
- **Feed the audited read log into the break-even formula:**
  - promote hot notes (`lint_and_test`) into compressed core text or hook injection
  - flag notes that are never read
- **Keep hard limits in core or the skill root,** never only in an on-demand file.
- **Phrase authored links as imperatives,** since sase's own logs show those get
  followed.
- **Lint skills for the catalogued smells,** and give each template a `## Gotchas`
  section.

### 6. Learning loops: propose, review, apply

**Evidence**

- **Gemini CLI Auto Memory:**
  - Background extraction writes `.patch` files to a `/memory inbox`.
  - Nothing is applied without approval, and the extractor defaults to proposing
    nothing.
- **Letta Context Repositories:** git-backed memory with reflection and defragmentation
  jobs.
- **Letta, *Evaluating Memory in Production Agents*:** a rubric that scores how memory is
  *used* (retrieval, adherence) separately from how it is *written* (generalization,
  hygiene).
- **TRACE:**
  - Access is not compliance: compliance was 55% with all rules in context, 70.1% with
    rules compiled into hooks.
  - Every memory write must declare `NOOP | UPDATE | SUPERSEDE | NEW` with a reason.
- **SkillsBench v4:** curated skills raised pass rate from 33.9% to 50.5%;
  self-generated skills fell below baseline.
- ***Context Language Models*** (2026-09-29) found self-editing models inserting
  unauthorized instructions.
- **LangChain:** diagnose a trace before it becomes memory; many lessons belong in a tool
  fix or an eval instead.

**For sase**

- **A `sase memory inbox` is the missing piece:**
  - A miner reads transcripts and proposes patches with provenance (the agent, bead, and
    correction).
  - Proposing nothing is the default.
  - Core notes and decisions are off the target allowlist.
  - A human applies each patch through the existing gate.
- **Add TRACE's forced decision line to `/sase_memory_write`.**
- **Score memory changes on Letta's four axes.**

### 7. Cross-provider parity

**Evidence**

- **Claude Code:** reads `AGENTS.md` only when no `CLAUDE.md` exists (v2.1.277).
- **Codex:** stops adding instruction files at 32 KiB, concatenated root to leaf, so the
  most specific nested files are the ones dropped.
- **Probe-and-Refine:** guidance tuned for one model hurt another.
- **Google moved free and AI Pro/Ultra Gemini CLI users to Antigravity CLI** (effective
  2026-06-18). Enterprise licenses keep Gemini CLI. Third-party guides say `GEMINI.md`
  and `AGENTS.md` still work, but Google's post does not say.

**For sase**

- **Keep shared content identical across providers.** Put any per-model calibration in
  adapter-owned blocks, per `decisions:adapters-normalize-harnesses`, and re-audit them
  on every model upgrade.
- **Add a byte-budget lint so Codex never silently drops content.**
- **Re-confirm which Gemini/Antigravity harness sase targets.**

---

## Ranked reading list

The ranking is by how likely each piece is to lead to a concrete change in sase's
memory or instruction files, weighted by evidence quality, freshness, and how much it
adds to what sase already does. Every date below was checked against the primary page.

Effort:

- **S:** 15 minutes or less
- **M:** 30–45 minutes
- **L:** paper-length; read the abstract, results and discussion

### Tier 1: read first

1. **[Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding](https://arxiv.org/html/2608.11095v1)**
   (Kushal Chakrabarti, South Park Commons; 2026-08-11). **L.**
   - The mechanism behind instruction-file bloat, plus a tested fix: rationale comments
     that record the outcome.
   - Maps directly onto `/sase_memory_write` and the decision-record format.
   - Caveat: the size result comes from a synthetic testbed.
2. **[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988)**
   (Gloaguen, Mündler, Müller, Raychev, Vechev; ETH Zürich and LogicStar; v1
   2026-02-12, v3 2026-09-29). **L.**
   - The baseline evidence on what always-loaded context costs and buys, including
     ablations that remove one section at a time.
   - Companions:
     - [Lulla et al.](https://arxiv.org/abs/2601.20404) (2026-01-28): efficiency gains
     - [Khatri](https://arxiv.org/abs/2607.27250) (2026-07-28): a small null result, with
       the numeric-hazard exception
3. **[Steering Claude Code: when to use CLAUDE.md, skills, hooks, and subagents](https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more)**
   (Michael Segner, Anthropic; 2026-06-18). **S.**
   - The best guide this year to where a sentence belongs: procedures go in skills,
     "never" rules in hooks or permissions, local conventions in path-scoped and nested
     files.
   - Read it with sase's `sase` core section open.
4. **[Guardrails Beat Guidance: A Large-Scale Study of Rules, Skills, and Persistent Configuration for Coding Agents](https://arxiv.org/html/2604.11088v2)**
   (Zhang et al., AWS GenAI Innovation Center and HSBC; 2026-04-13, v2 2026-05-28). **L.**
   - More than 5,000 runs. Prohibitions help and positive directives are risky.
   - A ready-made audit for sase's "MUST use `/skill`" style.
5. **[Coding Agents Love Decision Records](https://www.oreilly.com/radar/coding-agents-love-decision-records/)**
   (Duncan Davidson, O'Reilly Radar; 2026-10-02). **S.**
   - Over-adherence to obsolete records, status semantics, stop-and-propose on conflict,
     and no courtroom transcripts.
   - Written for exactly the kind of `decisions` web sase has.
6. **[When Stale Constraints Go Unchecked: Budgeted Verification Failures in Inherited Agent Memory](https://arxiv.org/abs/2608.25553)**
   (Kazuki Nakayashiki; 2026-08-26). **M.**
   - A controlled, 16-model study of agents acting on superseded constraints that read
     as settled, and the one-step verification cue that fixes it.
   - The strongest evidence that superseded rows should not sit in always-loaded text.
7. **[The new rules of context engineering for Claude 5 generation models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)**
   (Thariq Shihipar, Anthropic; 2026-07-24). **S.**
   - Over 80% of Claude Code's system prompt deleted with no measurable eval loss. The
     replacements: judgement over rules, interfaces over examples, progressive
     disclosure, and gotchas over tours of the file tree.
   - For a skeptical view, see the HN discussion it drew.
8. **[Skill Blocks: How Should an Agent Load Its Skill?](https://arxiv.org/html/2608.14943)**
   (Hironobu Nakasuji, Microsoft; 2026-08-14). **L.**
   - Cache-aware economics for inline versus on-demand loading, with a break-even
     formula.
   - Pair it with sase's audited read log (see the table above). Note its "no universal
     winner" verdict.

### Tier 2: strong, specific inspiration

9. **[Codified Context: Infrastructure for AI Agents in a Complex Codebase](https://arxiv.org/html/2602.20478v1)**
   (Aristidis Vasilopoulos; 2026-02-24). **M–L.**
   - A hot/cold memory system much like sase's, run for 283 sessions.
   - Staleness was its main failure mode, and it describes a drift detector.
   - An experience report from one developer, not a controlled study.
10. **[Building an agentic memory system for GitHub Copilot](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)**
    (Tiferet Gazit, GitHub; 2026-01-15). **S–M.**
    - Citations plus just-in-time verification, backed by a real A/B result.
    - The cheapest credible answer to staleness.
11. **[TRACE: Compiling User Corrections into Runtime Enforcement for Coding Agents](https://arxiv.org/html/2606.13174v1)**
    (Zhou et al., Notre Dame, Tencent AI Lab and IBM Research; 2026-06-11). **L.**
    - Access is not compliance.
    - Compile rules into hooks, and force every memory write to declare
      NOOP / UPDATE / SUPERSEDE / NEW.
12. **[AGENTS.md outperforms skills in our agent evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)**
    (Jude Gao, Vercel; 2026-01-27). **S.**
    - Shows the anchoring failure of "You MUST invoke".
    - Its compressed-index format is one sase's web descriptors could imitate.
13. **[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)**
    (Kyle Mistele, HumanLayer; 2025-11-25). **S.**
    - The best short editorial lens: what applies to every task, pointers over copies,
      and never send an LLM to do a linter's job.
14. **[Agentic Context Engineering (ACE)](https://arxiv.org/abs/2510.04618)**
    (Zhang et al.; v1 2025-10-06, at the edge of the window; v3 2026-03-29; ICLR 2026).
    **L.**
    - Brevity bias, context collapse, and itemized delta updates.
    - The counterweight to over-trimming, and the case for incremental over wholesale
      memory edits.
15. **[From Agent Behaviour to Agent-Friendly Documentation](https://arxiv.org/html/2608.20195)**
    (Zhijun Gao and Jing Chen, Peking University; 2026-08-20). **L.**
    - What agents actually read: instruction files dominate, links are not followed, and
      docs are never checked against code.
    - Compare it with sase's own logs.
16. **[Filesystem-Based Memory for LLM Agents: Organization, Evolution, and Sustainability](https://arxiv.org/html/2607.26637v1)**
    (Sizhe Zhou et al.; 2026-07-29). **M–L.**
    - The closest empirical match to a Markdown memory corpus.
    - Organization halves retrieval cost but does not improve answers, and it erodes as
      the store grows.
    - Useful for designing longitudinal checks.
17. **[Claude Code memory docs (AGENTS.md section)](https://code.claude.com/docs/en/memory#agents-md)**
    plus **[`/doctor prompt-audit` in the changelog](https://code.claude.com/docs/en/changelog)**
    (Anthropic; v2.1.277 on 2026-09-18 and v2.1.283 on 2026-09-25). **S.**
    - The authoritative rules for how sase's `CLAUDE.md` and `AGENTS.md` load together.
    - prompt-audit is a ready model for a `sase memory` lint covering stale paths, stale
      commands and contradictions.
18. **[Gemini CLI Auto Memory](https://geminicli.com/docs/cli/auto-memory/)** plus the
    **[v0.40.0 Tiered Memory release](https://github.com/google-gemini/gemini-cli/discussions/26216)**
    (Google; 2026-04-28/29, docs updated 2026-05-13). **S.**
    - The closest shipping blueprint for a `sase memory inbox`: patch proposals,
      allowlisted targets, human approval, and nothing proposed by default.
19. **Skills hygiene cluster.** **M.**
    - [From Anatomy to Smells](https://arxiv.org/html/2607.01456v1) (Hong, Imani, Ahmed,
      UC Irvine; 2026-07-01): a catalog of 26 smells to lint the generated skill
      templates against.
    - [Lessons from building Claude Code: How we use skills](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)
      (Shihipar; 2026-06-03): gotchas-first skills, and descriptions written as triggers.
    - [SkillSeam](https://arxiv.org/abs/2609.13321) (Kang Ruiyuan; 2026-09-10): auditing a
      whole skill collection for routing conflicts, aliases and ownership overlap.
20. **[Evaluating Memory in Production Agents](https://www.letta.com/blog/evaluating-memory-in-production-agents/)**
    (Letta; 2026-07-28) plus **[Introducing Context Repositories](https://www.letta.com/blog/context-repositories/)**
    (Letta; 2026-02-12). **S.**
    - A rubric that scores memory use and memory writing separately.
    - Git-backed memory with reflection and defragmentation jobs.

### Tier 3: skim for specific angles

21. **[SkillsBench](https://arxiv.org/abs/2602.12670)** (Li et al.; v1 2026-02-13, v4
    2026-06-14). Curated skills add 16.6pp; self-generated skills fall below baseline.
    This is the evidence for keeping a human gate on memory writes.
22. **[Probe-and-Refine Tuning of Repository Guidance](https://arxiv.org/abs/2606.20512)**
    (Shepard and Albrecht, Williams College; 2026-06-18). Guidance tuned on failures
    under a 3,000-character budget, and why it does not transfer across models.
23. **[Instruction Adherence in Coding Agent Configuration Files: A Factorial Study](https://arxiv.org/abs/2605.10039)**
    (Damon McMillan; 2026-05-11). Size, position and nesting have no detectable effect
    on adherence. A corrective against over-engineering layout; it says nothing about
    cost.
24. **[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)**
    (Ryan Lopopolo, OpenAI; 2026-02-11). AGENTS.md as a short map, CI-validated docs,
    and doc-gardening agents. Prior sase research already compared sase against it.
25. **Martin Fowler site essays by Birgitta Böckeler (Thoughtworks):**
    [Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)
    (2026-02-05) and [Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
    (2026-04-02). A taxonomy of who decides what to load (the LLM, the human, or the
    software), and guides versus sensors.
26. **[Prompt Debt and "Fighting the Weights"](https://www.oreilly.com/radar/prompt-debt-and-fighting-the-weights/)**
    (Tim O'Reilly on Drew Breunig's talk; 2026-08-13) plus
    **[How System Prompts Define Agent Behavior](https://blog.nilenso.com/blog/2026/02/10/how-system-prompts-define-agent-behaviiour/)**
    (Sriraman and Breunig, nilenso; 2026-02-10). Vocabulary for repetition and escalating
    emphasis.
27. **[Context Engineering for AI Agents in Open-Source Software](https://arxiv.org/abs/2510.21413)**
    (Mohsenimofidi, Galster, Treude, Baltes; MSR 2026; v1 2025-10-24). Five writing
    styles (descriptive, prescriptive, prohibitive, explanatory, conditional), usable as
    an authoring lint.
28. **[Rule Taxonomy and Evolution in AI IDEs](https://arxiv.org/html/2606.12231v1)**
    (Cai et al.; 2026-06-10). Compliance rises after a rule update, then decays.
    Practitioners value architecture rules most but write them least.
29. **[EA-Graph: Artifact-Anchored Verification Memory for Coding Agents under Upstream Drift](https://arxiv.org/abs/2608.04278)**
    (Hsu, Chi, Everett; 2026-08-04). Memory claims tied to code artifacts beat prose
    notes. Read it if you pursue `citations:` on notes.
30. **[How To Give Your Agent Memory](https://www.langchain.com/blog/how-to-give-your-agent-memory)**
    (Jake Broekhuizen, LangChain; 2026-06-24). Diagnose a trace before it becomes memory,
    and decide which owner (memory, eval, or tool fix) gets the lesson.
31. **[Context Language Models](https://arxiv.org/abs/2609.37725)** (Shao et al., UW,
    Meta Superintelligence Labs, MIT, Trillium Labs; 2026-09-29). Read only the §6 safety
    discussion: models with write access to their own context planted instructions. This
    is why core memory and decisions should stay outside any agent's write set.
32. **[Codex Memories docs](https://learn.chatgpt.com/docs/customization/memories)**
    (OpenAI; memory preview announced 2026-04-16). Separate read and write switches,
    consolidation after an idle period, and decay of memories unused for 30 days. The
    docs explicitly keep required rules in AGENTS.md.

### Deliberately not recommended for this question

- **Out of window, but the classics the list above builds on:**
  - Anthropic, *Effective context engineering for AI agents* (2025-09-29, 7 days early)
  - Chroma, *Context Rot* (Jul 2025)
  - HumanLayer, *Advanced Context Engineering* (Aug 2025)
- **Out of window and against sase's chosen design:**
  - A-MEM (2025-02) and Zep/Graphiti (2025-01): automatic linking and graph memory,
    against `memory-links-are-authored` and `corpus-before-mechanism`
  - ACON (2025-10-01)
- **Real papers, but low transfer to file authoring:**
  - Franko ITR (illustrative benchmark)
  - SkillOps, CoMem, Socratic-SWE (ALFWorld/PDDL-centric or about training)
  - GCC, CAT, MemAct, CAMG (long-session context management; sase agents are
    single-turn)
  - The two memory surveys (taxonomy only)
  - Concord (2610.05281, stale *tool observations* within one context)
- **Secondary or low-authority:**
  - SurePrompts' AGENTS.md guide (wrong about Claude Code support at publication)
  - Towards AI's skills-vs-subagents explainer
  - dev.to opinion pieces
  - Osmani's *Loop Engineering* (good framing, light on memory files)
  - DecodingAI's *Context Engineering for Coding Agents* (sound but derivative; its
    200-line `MEMORY.md` cap is the one stealable detail)

---

## Idea backlog these readings point to

Ordered roughly by leverage per unit of effort. These are inspirations, not a plan.
Anything touching memory files needs `/sase_memory_write`, and anything larger needs
`/sase_plan`.

| # | Idea | Main sources |
|---|---|---|
| 1 | Drop superseded rows from the inline `decisions` index, add a "stop and propose a superseding record on conflict" sentence, and have `memory read` print the successor of a superseded record | Davidson; Nakayashiki; Skill Blocks |
| 2 | Remove the 543 words of generic SASE text duplicated in `~/CLAUDE.md` for Claude sessions under `$HOME` | Gloaguen (cost); nilenso |
| 3 | Sort each "MUST use `/skill`" into hook/gate, description trigger, or prohibition; require a reason clause on surviving MUST/NEVER; lint the generated output for emphasis | Guardrails; Vercel; Segner; Shihipar |
| 4 | Source-side rationale comments (failure, recurrence, replaced text) on core directives, gotchas and skill rules, stripped at render and requested by `/sase_memory_write` | Chakrabarti; ACE |
| 5 | Rewrite reference, strand and skill descriptions as "Read when X; key hazard Y", and phrase authored links as imperatives | Shihipar (skills); SkillSeam; sase read log |
| 6 | Use the read log for break-even analysis: compress `lint_and_test` into core or inject it with a hook for editing turns; flag never-read notes and strands | Skill Blocks; sase read log |
| 7 | A `sase memory` lint modeled on `/doctor prompt-audit`: stale paths and commands, contradictions, relative-time words, byte budget against Codex's 32 KiB | prompt-audit; Codified Context; Codex docs |
| 8 | Optional `covers:` / `citations:` plus `last_verified` on notes, with drift warnings shown in `memory read` output | Copilot memory; EA-Graph; Codified Context |
| 9 | `sase memory inbox`: proposal-only transcript miner, nothing proposed by default, core and decisions off the allowlist, human applies | Gemini CLI; TRACE; SkillsBench v4; CLM |
| 10 | A small A/B harness per provider: current vs trimmed core on fixed tasks, measuring tokens, steps, wall-clock and policy adherence, not only pass rate | Gloaguen; Khatri; Letta rubric |

---

## Caveats

- **Coding-benchmark bias.** Almost every quantitative result measures SWE-bench-style
  coding tasks. sase's instruction files also govern orchestration: final declarations,
  gates, beads, and artifact audits. No benchmark tests that, so treat the efficiency
  numbers as directional.
- **Small studies and preprints.** Several key papers are single-author or
  single-setting:
  - Chakrabarti's size result comes from a synthetic testbed.
  - Codified Context is an experience report from one developer.
  - SkillSeam and Nakayashiki are single-author.
- **Emphasis is untested.** No study tests capital-letter MUST/NEVER as a variable
  directly. The de-emphasis advice rests on Anthropic's model-specific guidance, Vercel's
  anchoring case, and the prompt-debt literature.
- **The OpenAI article was checked only through mirrors.** The page blocks automated
  fetchers.
- **Read-log limits.** The log starts on 2026-07-06 and covers only agents that read
  memory, so it cannot show whether always-loaded text was *used*, only whether bodies
  were fetched.
