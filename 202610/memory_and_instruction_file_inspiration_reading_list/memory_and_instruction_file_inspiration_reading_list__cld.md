# Recent Articles to Improve SASE Memory and Agent Instruction Files (cld)

- **Researcher:** cld (Claude Opus 5.5), one of five researchers working the same question
  independently
- **Date:** 2026-10-06
- **Publication window:** 2025-10-06 → 2026-10-06. Older pieces are flagged where they come up.
- **Question:** Which articles from the last year are most likely to inspire concrete
  improvements to sase's memory notes (`sase/memory/`) and the agent instruction files
  generated from them (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and the generated skills)?

---

## TL;DR

Writing about agent instruction files changed character in 2026. It used to be
practitioners trading opinions. Now there are controlled studies, mining studies of
hundreds of thousands of instruction lifetimes, and vendor A/B tests. Five findings matter
most for sase:

1. **Always-loaded context rarely changes whether a task succeeds, but it reliably changes
   cost and behavior.**
   - Context files gave no significant success gain and added roughly 20% inference cost
     ([Gloaguen et al.](https://arxiv.org/abs/2602.11988)).
   - Correctness did not move in a two-agent ablation
     ([Khatri](https://arxiv.org/html/2607.27250v1)).
   - What does pay off is non-inferable knowledge: hazards, prohibitions, conventions, and
     stated rationale.
2. **Positive "do X" directives are the risky kind. Prohibitions are the helpful kind.**
   Every individually helpful rule was a negative constraint, and every harmful one was a
   positive directive ([Guardrails Beat Guidance](https://arxiv.org/html/2604.11088v2)).
   - sase's core text leans heavily on "MUST use `/skill_x` before Y".
   - Vercel found that exactly this wording makes agents anchor on the skill and miss
     project context
     ([Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)).
   - Anthropic's own prompting docs tell authors to dial emphatic language back.
3. **Rationale is what keeps instruction files from growing without bound.**
   - "Catastrophic remembering": a rule whose reason has been lost cannot be safely
     deleted, so files only grow.
   - Comments recording each rule's originating failure, kept out of the prompt the model
     sees, held prompts at near-optimal size
     ([Chakrabarti](https://arxiv.org/html/2608.11095v1)).
   - sase's `decisions` web already does this for architecture. Core directives and skill
     rules do not.
4. **Staleness is the main failure mode, and the fix is mechanical.**
   - "Agents trust documentation absolutely and out-of-date specs cause silent failures"
     ([Codified Context](https://arxiv.org/html/2602.20478v1)).
   - The fixes being tried are drift detectors that map memory to code paths, code
     citations verified just in time
     ([GitHub Copilot memory](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)),
     and invalidating facts instead of deleting them.
5. **Learning loops are converging on "propose, review, apply".**
   - Gemini CLI's memory inbox, Letta's reflection and defrag subagents, Claude Code's
     Auto Dream, Anthropic's Managed Agents memory with audit and rollback, and TRACE's
     correction-to-hook compiler all fit this shape.
   - Agent-written knowledge without a human gate tends to hurt: self-generated skills
     scored below no skills in [SkillsBench](https://arxiv.org/abs/2602.12670v1).
   - sase's gated memory-write design is well placed. It lacks the miner and the inbox.

**If you only read five:**
1. [Why Does CLAUDE.md Keep Growing?](https://arxiv.org/html/2608.11095v1)
2. [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)
3. [Guardrails Beat Guidance](https://arxiv.org/html/2604.11088v2)
4. [Coding Agents Love Decision Records](https://www.oreilly.com/radar/coding-agents-love-decision-records/)
5. [Skill Blocks](https://arxiv.org/html/2608.14943)

The full ranked list of 30 is [at the end](#ranked-reading-list).

---

## Method and Confidence

- **Search.** About 45 web searches across five areas:
  - empirical studies of AGENTS.md/CLAUDE.md
  - skills and progressive disclosure
  - memory consolidation and learning loops
  - wording and prompt debt
  - decision records and staleness
- **Reading.** About 40 sources were read through parallel fetch agents. Each reader was
  given a description of sase's memory model and asked for dates, designs, numbers, and
  sase-specific implications. I spot-checked the numbers against each other.
- **Read only partly:**
  - McMillan's factorial study ([2605.10039](https://arxiv.org/abs/2605.10039)): abstract
    only, because the PDF did not extract.
  - OpenAI's "Harness engineering" post: returned HTTP 403. Its summary here comes from
    search snippets and secondary write-ups.
  - Anthropic's "dreaming" for Managed Agents: news coverage only. I could not retrieve
    the announcement itself.
- **Measuring sase.** I measured the current instruction files in this checkout (see the
  next section). I did not open other researchers' reports or prior research reports.

---

## Where sase Stands Today

These are measured from this checkout on 2026-10-06. They matter because several articles
give budgets or smells that can be checked directly against them.

| Fact | Value | Why it matters |
|---|---|---|
| Generated project `AGENTS.md` (identical `CLAUDE.md`/`GEMINI.md`) | 290 lines, 2,547 words, ~18 KB | Above HumanLayer's "< 60 lines" and Vaughan's "< 150 lines" guidance. Far above Probe-and-Refine's ~3,000-character budget. |
| Largest always-loaded section | `decisions` web index: 885 words (~35% of the file) | The descriptor lists all 25 records, including **4 superseded** ones. |
| Other always-loaded sections | `sase` core 669 words, reference index 264, glossary 279, task types 182, Rust boundary 140, gotchas 26 | Core proper is small. The webs and indices dominate. |
| Emphatic tokens in generated file | 5 × MUST, 2 × IMPORTANT, plus "Do NOT"/"never" in prose | Moderate rather than extreme, but most are positive "MUST use skill X" directives. |
| Claude sessions in workspaces under `$HOME` | 543 of 614 words in `~/CLAUDE.md` duplicate lines in the project `CLAUDE.md` verbatim | The generic SASE memory, repository and final-declaration sections reach Claude agents twice per turn. Repetition is the "fighting the weights" smell nilenso and Breunig describe. |
| Mandatory-read reference note | `lint_and_test.md`: "you MUST read this note before you finish your turn" | Read on almost every coding turn. Skill Blocks' break-even math says notes needed this often are cheaper inlined or hook-injected than fetched. |
| Skills | 19 generated skill templates plus a frame template | One template smell gets copied to every provider. |
| Reads | Audited: `sase memory read -r "<why>"` | This is the usage telemetry several articles wish they had. |

---

## Themes, Evidence, and What Each Suggests for sase

### 1. What belongs in always-loaded memory: less, sharper, and non-inferable

**Evidence**

- **[Gloaguen et al., *Evaluating AGENTS.md*](https://arxiv.org/abs/2602.11988)** (ETH
  Zürich and LogicStar; v1 Feb 2026, v3 Sep 2026). Four agent/model pairs on SWE-bench Lite
  and a new benchmark of 138 tasks from repos that ship developer-written context files.
  - LLM-generated files lowered success slightly (−0.5% and −2%) and **raised cost 20–23%**.
  - Developer-written files gave +2.4%, not significant, but still added up to 19% cost.
  - Instructions *are* followed: a file mentioning `uv` produced 1.6 `uv` calls per task,
    versus about 0 without it.
  - Repository overviews did not shorten the time to reach the relevant file.
  - Removing the "Testing" section cut cost significantly with no accuracy change.
  - The authors' reading: extra instructions "make the task harder".
- **[Khatri, *Do Context Files Help Coding Agents?*](https://arxiv.org/html/2607.27250v1)**
  (Jul 2026). Claude Code and Codex, compared with no context, always-on AGENTS.md, and
  "selective" topic wiki files read on demand.
  - Correctness did not move. Agents fail on "implementation skill … not missing
    repository knowledge."
  - The one behavioral effect was an operational hazard with a number in it: "the full
    test suite takes >20 minutes". It cut blind full-suite runs and wall-clock time by
    about 24%.
  - The on-demand variant used fewer cache-creation tokens.
- **[Lulla et al.](https://arxiv.org/abs/2601.20404)** (ICSE JAWs 2026). On small PRs,
  AGENTS.md cut median wall-clock time by 29% and output tokens by 17%, mostly by
  preventing a few runaway sessions.
- **[Shepard & Albrecht, *Probe-and-Refine*](https://arxiv.org/abs/2606.20512)** (Jun 2026).
  - Guidance tuned on observed failures, capped at **≤3,000 characters**, raised SWE-bench
    Verified resolves from 25.5% to 33.0%. The gain came from helping the agent find the
    right file.
  - The refined content was procedural (47%), structural paths (30%), and quality gates
    (23%), e.g. "Show actual test output, not fabricated summaries".
- **[HumanLayer, *Writing a good CLAUDE.md*](https://www.humanlayer.dev/blog/writing-a-good-claude-md)**
  (Nov 2025) and
  **[GitHub, *Lessons from 2,500 repositories*](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)**
  (Nov 2025) are the practitioner versions of the same message:
  - Only include what applies to every task.
  - "Prefer pointers to copies."
  - "Never send an LLM to do a linter's job."
  - Use three-tier boundaries: **Always / Ask first / Never**.

**What this suggests for sase**

- **Audit core and the always-inlined webs for "discoverable" content**, meaning anything
  the agent could learn by reading the repo. Keep non-inferable hazards with numbers, such
  as slow suites, expensive commands, and root-only actions, plus prohibitions and
  conventions.
- **Make the decisions index the first trimming target.** It is the single biggest
  always-loaded block.
  - Drop superseded records from the inline list. They stay readable by key.
  - Consider rewriting each one-liner as "when this matters" rather than a summary of the
    decision (see theme 4).
- **Fix the home-plus-project duplication** for Claude sessions. One option is to
  generate `~/CLAUDE.md` without the generic SASE sections when every workspace is a
  sase project with its own generated file.
- **Put an explicit character or token budget on the generated file** and fail
  `sase memory init` or a lint when it is exceeded. The rendered README already reports
  approximate tokens; a budget turns that report into a ratchet.

### 2. Wording: polarity, emphasis, and "explain the why"

**Evidence**

- **[Zhang et al., *Guardrails Beat Guidance*](https://arxiv.org/html/2604.11088v2)**
  (AWS and HSBC; Apr–May 2026). 679 scraped rule files and more than 5,000 Claude Code +
  Opus 4.6 runs.
  - *Any* rules helped, by 6.9–13.8pp. Random rules did as well as curated ones, which the
    authors attribute to "context priming".
  - Helpful individual rules were all prohibitions. "No unrelated refactor" alone was worth
    +20pp.
  - Harmful ones were all positive directives: "follow code style" −14.3pp, "read test
    files" −14.3pp.
  - Their summary: *constrain what agents must not do rather than prescribe what they
    should.*
  - The polarity split is "suggestive" (p≈0.03–0.13 depending on the threshold).
- **[Anthropic, Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)**
  and **[Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)**
  (living docs).
  - "Where you might have said 'CRITICAL: You MUST use this tool when...', you can use
    more normal prompting like 'Use this tool when...'."
  - Blanket "If in doubt, use [tool]" causes overtriggering.
  - Explain the reason: "Claude is smart enough to generalize from the explanation."
  - On Opus 5, explicit "double-check" instructions cause over-verification.
- **[Vercel, *AGENTS.md outperforms skills*](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)**
  (Jan 27, 2026).
  - "You MUST invoke the skill" made the agent read docs first and anchor on them, so it
    missed a required config change.
  - "Explore the project, then invoke the skill" did better.
- **[Breunig via O'Reilly, *Prompt Debt and "Fighting the Weights"*](https://www.oreilly.com/radar/prompt-debt-and-fighting-the-weights/)**
  (Aug 13, 2026) and
  **[nilenso, *How System Prompts Define Agent Behavior*](https://blog.nilenso.com/blog/2026/02/10/how-system-prompts-define-agent-behaviiour/)**
  (Feb 10, 2026).
  - Agent system prompts repeat the same instruction 5–7 times, escalating "through
    IMPORTANT to CRITICAL to MANDATORY".
  - The prompt-debt smells are repeated instructions, one-off patches, and increasingly
    desperate wording. Those rules belong in evals or harness code.
  - The companion post on
    [weird system-prompt artefacts](https://blog.nilenso.com/blog/2026/02/12/weird-system-prompt-artefacts/)
    shows patches nobody can delete because no rationale was recorded.

**What this suggests for sase**

- **Lint the generated output for emphatic tokens.** Require every surviving MUST, NEVER
  or IMPORTANT to carry a one-clause reason, as Anthropic's own samples do.
- **Reclassify each "MUST use `/skill_x` before Y" directive into one of three forms:**
  - A **guarantee**: move it into a hook, gate or guarded recipe. sase already prefers
    this per `decisions:guarded-recipes`.
  - A **judgement call**: put the trigger into the skill's description and drop the MUST.
  - A **prohibition**: rewrite it as "Never Y without Z" and keep it in core.
- **Adopt GitHub's Always / Ask first / Never tiers** for the hard boundaries in `sase.md`
  and the gotchas note. Reserve emphasis for the Never tier.

### 3. Rationale, growth, and pruning: the "catastrophic remembering" problem

**Evidence**

- **[Chakrabarti, *Why Does CLAUDE.md Keep Growing?*](https://arxiv.org/html/2608.11095v1)**
  (South Park Commons, Aug 2026). The most directly sase-relevant paper this year.
  - **Mining:** 247,694 instruction lifetimes across 1,867 repos. Files grow +226% over
    their lifetime, gaining about 4.9 net instructions per commit.
  - **Rewrites don't fix it:** 76.8% of deletions happen in wholesale rewrites, and files
    regrow to 91.5% of their old size within 10 commits.
  - **Deletion risk falls with an instruction's age**, more so in files with many authors.
    Rules are kept not because they are fresh but because nobody remembers why they exist.
  - **The controlled fix is comments.** Each instruction gets a stable ID and a comment
    the executing model never sees, recording:
    - the round it was added
    - the verbatim failure that prompted it, with a recurrence count
    - approaches already tried and disproven
    - the text of any instruction it replaced
  - **Result:** comments cut excess prompt size from +211% to +1.4% with no loss of
    correctness. Placebo comments did not help. Comments without *outcomes* were the worst
    arm.
- **[Cai et al., *Rule Taxonomy and Evolution in AI IDEs*](https://arxiv.org/html/2606.12231v1)**
  (Jun 2026). 7,310 rules and 1,540 rule-change events.
  - Pruning is 1.79% of changes.
  - Compliance jumps from 49% to 72% after a rule update, then decays back toward about
    65% within 4–5 commits.
  - Practitioners value architecture rules most but write them least.
- **[Agent READMEs](https://arxiv.org/html/2511.12884v1)** (Nov 2025, 2,303 files). Files
  behave like configuration code: they grow by about 57 words per commit and deletions
  stay under 15. Median CLAUDE.md readability is "very difficult".

**What this suggests for sase**

- **Extend the decision-record discipline (claim, why, cost, reopen condition) down to
  individual core directives, gotchas and skill rules.** One concrete option:
  - Give each directive a stable ID and an HTML or YAML comment block in the source note
    with `added`, `failure` (verbatim), `recurred`, and `supersedes`.
  - Strip the block during `sase memory init`, so the agent never pays for it.
- **Have `/sase_memory_write` require the originating failure** when a directive is
  added. At write time this is almost free; later it cannot be reconstructed.
- **Prefer pruning one item at a time, guided by its rationale, over periodic full
  rewrites.** The data says rewrites regrow.

### 4. Decision records: sase is ahead, with two specific gaps

**Evidence**

- **[Davidson, *Coding Agents Love Decision Records*](https://www.oreilly.com/radar/coding-agents-love-decision-records/)**
  (author's blog Sep 1, 2026; O'Reilly Radar Oct 2, 2026).
  - Agents "fight tooth and nail to apply an accepted decision even when it is obsolete."
    In one case an agent stacked a new layer on top of an outdated abstraction instead of
    flagging the mismatch.
  - Statuses need explicit meaning: accepted ADRs are binding, proposed ADRs are
    non-binding context, and superseded ADRs "do not govern current work."
  - When a task conflicts with an accepted ADR, the agent should **stop and propose a
    change**.
  - Avoid "courtroom transcripts": no amendment logs inside a record, because git is the
    changelog. "State each rule once in the ADR that owns it."
- **[Hindsight, *The Consolidation Problem in Agent Memory*](https://hindsight.vectorize.io/blog/2026/05/21/agent-memory-consolidation)**
  (May 2026) recommends "recency-wins with explicit invalidation": old facts are marked
  invalid rather than deleted. sase's `superseded_by` already follows this.

**What this suggests for sase**

- **Add a one-sentence conflict protocol to the decisions descriptor:** "If a task
  conflicts with an accepted record, stop and propose a superseding record rather than
  working around it." sase's reopen-condition field only helps if the agent knows what to
  do when the condition is hit.
- **Remove superseded records from the always-inlined index**, as noted in theme 1. They
  cost tokens, and they invite exactly the anchoring Davidson describes.
- **Guard against over-litigated prose when agents edit decision records.** sase's
  "immutable once accepted" rule already prevents amendment logs, so this is mostly
  covered.

### 5. Progressive disclosure economics: what to inline, what to defer, how to point

**Evidence**

- **[Nakasuji, *Skill Blocks*](https://arxiv.org/html/2608.14943)** (Microsoft, Aug 2026).
  This is the first study of always-loaded versus on-demand loading that accounts for
  prompt caching correctly.
  - Cache reads were 74–94% of raw input in multi-turn runs, so raw token counts can rank
    the methods wrongly.
  - On-demand loading saved 50–73% of effective tokens for large, mostly-unused content.
  - For small or frequently needed content, the extra round-trips "erase the savings".
  - Forcing "load before answering" raised cost by 48%.
  - "Hybrid" loading (inline stubs plus fetch on demand) won when the stubs were good
    enough that the agent rarely needed to fetch.
  - It gives a break-even formula. In words: you save the size of the blocks you skip,
    minus the cost of the extra round-trips and the tool definition.
- **[Chen et al., *SkillJuror*](https://arxiv.org/html/2606.11543v1)** (Jun 2026).
  - A short root file that points to supporting files led agents to touch 3.85 resources
    per trajectory instead of 1.18. Late-phase repair use roughly doubled.
  - It *hurt* where success depended on exact formats or thresholds, which the paper calls
    a "fanout tax": hard limits spread across files get missed.
  - "Specifying exactly when and why to access a file anchors the agent's tool-use loop."
- **[Gao & Chen, *From Agent Behaviour to Agent-Friendly Documentation*](https://arxiv.org/html/2608.20195)**
  (Peking University, Aug 2026). 557 real sessions.
  - Agent instruction files plus the agent's own notes are **60.5%** of all documentation
    interactions.
  - Following a link from one doc to another is "**entirely unattested**".
  - Reading a doc is *not* followed by checking the code against it.
  - Reading docs is the first recovery step in only 5.4% of failures.
- **[Vercel](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)**
  (Jan 2026).
  - A skill went uninvoked in 56% of cases.
  - An 8 KB **compressed pipe-delimited docs index** inlined in AGENTS.md scored 100%,
    with the directive "Prefer retrieval-led reasoning over pre-training-led reasoning".
- **[Cursor, *Dynamic context discovery*](https://cursor.com/blog/dynamic-context-discovery)**
  (Jan 6, 2026) and
  **[Letta, *Context Repositories*](https://www.letta.com/blog/context-repositories/)**
  (Feb 12, 2026). Files are the primitive. Letta puts a frontmatter description on every
  memory file, always shows the file tree, and pins files by moving them into `system/`.
- **[Böckeler, *Context Engineering for Coding Agents*](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)**
  (Feb 5, 2026). Her taxonomy sorts context by who decides to load it:
  - the LLM (skills: "uncertain if the LLM will actually load the context")
  - the human (slash commands)
  - the agent software (hooks, path-scoped rules)

**What this suggests for sase**

- **Use the audited `sase memory read` log as the input to the break-even formula.**
  Compute how often each reference note and strand is loaded.
  - Notes loaded in most sessions are candidates for promotion to core in compressed
    form. `lint_and_test` is the obvious first case.
  - Notes never loaded are candidates for deletion, or need a better description.
- **Rewrite reference and strand one-liners as trigger plus payload stubs:** "Read when
  *X*; key hazard: *Y*." Today several say what the note *is*, not when to read it. That
  makes them weaker hybrid stubs and weaker trigger text.
- **Keep hard limits in core or in the skill root, never only in an on-demand file.**
  Examples: root-only rules, exact formats, numeric thresholds.
- **Make each strand self-contained**, since agents don't follow links. `sase memory read`
  could append the one-line descriptions of linked strands, an inline version of what
  `link_rendering: reference` does now.
- **Add more software-triggered loading.** One option is path-scoped notes rendered as
  nested `AGENTS.md`/`CLAUDE.md` files, which several harnesses load just in time when a
  file under that path is read
  ([Harness Engineering, 11 systems](https://arxiv.org/html/2609.00006v1)). That moves
  some notes from the LLM-decides category into the software-decides category.

### 6. Staleness and verification

**Evidence**

- **[Vasilopoulos, *Codified Context*](https://arxiv.org/html/2602.20478v1)** (Feb 2026).
  A 108K-line C# system built in 283 Claude Code sessions, organized much like sase:
  - a ~660-line hot "constitution"
  - 19 specialist agent specs
  - 34 cold specs served by keyword search
  - Findings:
    - "Specification staleness was the primary failure mode."
    - A session-start **context drift detector** compares recent commits against a
      subsystem-to-file map and warns when code changed but its spec didn't.
    - Two of the author's guidelines: "If you explained it twice, write it down" and
      "Route automatically or forget constantly."
- **[GitHub, *Building an agentic memory system for Copilot*](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)**
  (Jan 15, 2026).
  - Each memory carries `subject`, `fact`, `citations` (file:line) and `reason`.
  - Agents verify the citations before using a memory, fix it if the code contradicts it,
    and re-save it to refresh its timestamp.
  - GitHub deliberately rejected an offline curation service because verification is
    "easy". The pool self-healed from planted false memories.
  - A/B result: PR merge rate 90% with memory vs 83% without (p<0.00001).
- **[Tessl on Claude Code Auto Dream](https://tessl.io/blog/anthropic-tests-auto-dream-to-clean-up-claudes-memory)**
  (Mar 26, 2026). The consolidation pass converts relative dates to absolute ones, merges
  duplicates and contradictions, and rebuilds the index.

**What this suggests for sase**

- **Add optional `covers:` path globs or `citations:` to reference notes and strands.**
  `sase memory verify` (or lint) would flag notes whose cited paths or symbols vanished,
  or whose covered files changed since the note last did.
  - sase agents are single-turn, so the warning has to appear in the
    `sase memory read` output or in the generated file, not at session start.
- **Record `last_verified` (a commit or date)** whenever an agent confirms a note against
  the code. Staleness is then measured from the last confirmation, not from creation.
- **Lint for relative time words** ("recently", "currently", "last week") in memory notes.

### 7. Learning loops and consolidation: propose, review, apply

**Evidence**

- **[Gemini CLI Auto Memory](https://geminicli.com/docs/cli/auto-memory/)** (docs updated
  May 2026) and
  **[v0.40.0 Tiered Memory](https://github.com/google-gemini/gemini-cli/discussions/26216)**
  (Apr 29, 2026). The closest analogue to sase's gate.
  - A background extractor reads finished sessions (idle at least 3 hours, at least 10
    user messages).
  - It writes `.patch` files and draft `SKILL.md`s into an `.inbox/`.
  - It cannot edit project `GEMINI.md` directly. Patches are target-allowlisted, dry-run,
    and applied atomically only after approval in `/memory inbox`.
  - "It defaults to creating no artifacts unless the evidence is strong."
- **[Letta Context Repositories](https://www.letta.com/blog/context-repositories/)**
  (Feb 2026). Git-backed memory with three built-in jobs:
  - *reflection*: background review of recent sessions
  - *defragmentation*: back up, then split, merge and restructure into "15–25 focused
    files"
  - *initialization*: fan out over past Claude Code and Codex histories
- **[Anthropic, Memory for Claude Managed Agents](https://claude.com/blog/claude-managed-agents-memory)**
  (Apr 23, 2026).
  - Memories are files.
  - "All changes are tracked with a detailed audit log, so you can tell which agent and
    session a memory came from", with rollback and redaction.
  - Netflix keeps human corrections in memory "instead of manually updating prompts and
    skills."
  - "Dreaming" (May 2026, per news coverage) adds scheduled consolidation.
- **[Zhou et al., TRACE](https://arxiv.org/html/2606.13174v1)** (Notre Dame, Tencent and
  IBM; Jun 2026).
  - **Access ≠ compliance:**
    - all rules in context: 55.0% compliance
    - Mem0: 42.5%
    - rules compiled into hooks and verifiers: 70.1%
  - Every memory write must declare `NOOP | UPDATE <id> | SUPERSEDE <id> | NEW — because
    <reason>`, or it is aborted.
  - Superseded rules are archived, not deleted.
- **[Zhang et al., *Library Drift*](https://arxiv.org/html/2605.19576v1)** (May 2026) and
  **[*Experience Compression Spectrum*](https://arxiv.org/html/2604.15877v2)** (Apr–Jun
  2026).
  - Unmanaged accumulation pushes agents *below the no-skill baseline*, silently.
  - **The single most valuable control is a strict authoring template** for new entries.
    Removing it cost 43% of the gain.
  - Harsh pruning was worse than no skills at all.
  - Create a new entry only after about 3 failures that share a pattern.
- **[SkillsBench](https://arxiv.org/abs/2602.12670v1)** (Feb 2026). Curated skills gave
  +16.6pp. Self-generated skills were negative.

**What this suggests for sase**

- **A `sase memory inbox` is the missing piece.**
  - A post-turn or nightly miner over agent transcripts proposes note patches, with
    provenance: session or bead, the user correction, and the agent action it corrects.
  - Proposing nothing is the default.
  - Core notes are off the target allowlist.
  - A human applies or rejects each patch through the existing gate.
- **Adopt TRACE's forced decision line inside `/sase_memory_write`.** A NOOP that only
  adds evidence to an existing note's provenance is a cheap importance signal.
- **Enforce one authoring template per memory kind** (core directive, reference note,
  glossary strand, decision record) in the write skill and in lint.

### 8. Enforcement over prose, and per-model calibration

**Evidence**

- **[McMillan, factorial study](https://arxiv.org/abs/2605.10039)** (May 2026; abstract
  only).
  - File size, instruction position, single vs nested file architecture, and conflicting
    instructions had **no detectable effect** on adherence.
  - Compliance fell about **5.6% per additional function generated** within a session.
- **[Destefanis, *Authoring Agent Skills*](https://arxiv.org/html/2607.25032v1)** (UCL,
  Jul 2026). "A standing instruction in a skill body, however firmly worded, is something
  the model may read, defer, or skip". When a guarantee matters, use a hook.
- **[Böckeler, *Harness engineering for coding agent users*](https://martinfowler.com/articles/harness-engineering.html)**
  (Apr 2026). Guides act before the agent does, sensors after. Sensor output should be
  written for the LLM.
- **Probe-and-Refine.** Guidance tuned on Qwen dropped Nemotron's resolve rate from 27.0%
  to 13.2%: "guidance encodes model-specific behavioral calibration, not transferable
  repository knowledge."
- **nilenso.** Swapping Codex's system prompt into Claude Code changed the *workflow
  style* while keeping success constant.

**What this suggests for sase**

- **Put a "how is this enforced?" field on every Never-tier rule:** a hook, gate, guarded
  recipe, lint, or "prose only". Rules marked prose only that recur in transcripts are the
  backlog for new hooks.
- **Reserve prose for judgement and rationale.**
- **Let most content be identical across providers, but allow per-provider calibration
  blocks** rendered only into that provider's file. Re-audit them on every model upgrade.
  This fits `decisions:adapters-normalize-harnesses`: quirk patches belong with the
  adapter, not in shared memory.
- **Keep generated files byte-stable**, with volatile content last, so many short-lived
  agents share the cached prompt prefix. Claude Code, OpenHands and Hermes all split
  prompts at a static/dynamic cache boundary (Harness Engineering, 11 systems).

### 9. Skills hygiene, since the generated skills are instruction files too

**Evidence**

- **[Hong et al., *From Anatomy to Smells*](https://arxiv.org/html/2607.01456v1)** (UC
  Irvine, Jul 2026). 238 SKILL.md files, of which 237 had smells, 10.5 on average. Smells
  "rarely disappear once introduced." The most common:
  - **Rationalization Loophole** (94%): nothing discourages skipping required steps
  - **Buried Gotchas** (81%)
  - Execute Without a Plan (78%)
  - No Progress Tracking (71%)
  - No Validation Step (69%)
  - **Confusing Description** (32%): missing what it does, when to use it, or keywords
- **[Thariq Shihipar, *How we use skills*](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)**
  (X thread Mar 2026; claude.dev page Jun 3, 2026).
  - "The highest-signal content in any skill is the Gotchas section."
  - "The description field is not a summary, it's a description of when to trigger this
    skill."
  - Track skill usage to catch skills that trigger less often than expected.
- **[Anthropic, *Improving skill-creator*](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)**
  (Mar 3, 2026).
  - Tells "capability uplift" skills apart from "encoded preference" skills. Most sase
    skills are the second kind.
  - Run evals *without* the skill: if the base model passes, the skill is "no longer
    necessary".
  - Uses trigger evals to tune descriptions.

**What this suggests for sase**

- **Add a static smell lint to skill generation:**
  - names ≤64 characters
  - descriptions ≤1,024 characters, with no XML, in the third person, and containing
    what, "Use when…", and keywords
- **Add an LLM-checked pass** for Rationalization Loophole, Buried Gotchas and missing
  validation.
- **Give every template a `## Gotchas` section** that grows from observed failures.
- **Build a small trigger-eval set** of should-fire and shouldn't-fire prompts per skill,
  rerun on model upgrades.

### Counter-evidence: don't over-trim

- **[ACE, *Agentic Context Engineering*](https://arxiv.org/abs/2510.04618)** (v1 Oct 6,
  2025, so right at the edge of the window; ICLR 2026). It warns about **brevity bias**,
  where summarizing drops domain insight, and **context collapse**, where repeated
  rewrites erode detail. It recommends itemized playbooks updated incrementally rather
  than by wholesale rewrites, which agrees with Chakrabarti on avoiding rewrites.
- **Guardrails Beat Guidance.** Pass rates were flat from 0 to 50 rules.
- **McMillan.** Size and position were null for adherence.

Taken together, the case for trimming sase's always-loaded text rests on **cost, cache
efficiency, maintainability, and avoiding anchoring**, not on correctness. Never trim
prohibitions, hazards, or rationale.

---

## Idea Backlog

These are traced to sources and ordered roughly by leverage over effort. They are
inspirations, not a plan. Several would need `/sase_memory_write` or `/sase_plan` before
anyone acts on them.

| # | Idea | Main sources |
|---|---|---|
| 1 | Drop superseded decision records from the always-inlined `decisions` index, and add a "stop and propose a superseding record on conflict" sentence to the descriptor. | Davidson; Skill Blocks |
| 2 | Remove the generic SASE sections duplicated between `~/CLAUDE.md` and project files for Claude sessions under `$HOME` (543 duplicated words today). | nilenso/Breunig; Gloaguen (cost) |
| 3 | Emphasis/polarity lint on generated output. Every MUST/NEVER needs a reason clause. Each "MUST use skill X before Y" becomes a hook/gate, a description trigger, or a prohibition. | Anthropic docs; Guardrails; Vercel |
| 4 | Hidden rationale comments with stable IDs (`added`, `failure`, `recurred`, `supersedes`) on core directives and skill rules, stripped at render and required by `/sase_memory_write`. | Chakrabarti; nilenso artefacts |
| 5 | Rewrite reference/strand descriptions as "Read when X; key hazard Y" stubs, and add trigger evals. | Thariq; skill-creator; Skill Blocks (hybrid); Khatri |
| 6 | Use the audited read log to compute per-note load probability, promote hot notes (e.g. `lint_and_test`) into compressed core text or hook injection, and flag never-read notes. | Skill Blocks; Codified Context; Library Drift |
| 7 | Hard character/token budget for the generated file, enforced in `sase memory init` or lint. | Probe-and-Refine; HumanLayer; OpenAI harness |
| 8 | `covers:`/`citations:` plus `last_verified` on notes, and a `sase memory verify` drift check surfaced in `memory read` output. | Codified Context; GitHub Copilot memory |
| 9 | `sase memory inbox`: a transcript miner proposes patches with provenance; propose-nothing default; core off the allowlist; human applies. | Gemini CLI; Letta; Managed Agents; TRACE |
| 10 | Forced decision line (NOOP/UPDATE/SUPERSEDE/SPLIT/NEW plus reason) in the write skill, and one authoring template per memory kind. | TRACE; Library Drift |
| 11 | "Enforced by:" field on Never-tier rules; recurring prose-only rules become the hook backlog. | TRACE; Destefanis; Böckeler |
| 12 | Skill smell lint (static plus LLM) and Gotchas sections in skill templates. | Anatomy to Smells; Thariq |
| 13 | Small A/B harness: core vs no core vs trimmed core on fixed tasks *per provider*, measuring steps, tokens, wall-clock and tail cost, not only pass rate. | Gloaguen; Khatri; Lulla; skill-creator |
| 14 | Per-provider calibration blocks owned by adapters, re-audited on model upgrades. Byte-stable generation for prompt caching. | Probe-and-Refine; nilenso; Harness study |

---

## Ranked Reading List

The ranking is by how likely each piece is to lead directly to a concrete change in sase's
memory notes or instruction files, weighted by evidence quality and freshness. Effort is
**S** (≤15 min), **M** (30–45 min) or **L** (paper-length; skim the abstract, results and
discussion).

### Tier 1: read these first

1. **[Why Does CLAUDE.md Keep Growing? Catastrophic Remembering in Agentic Coding](https://arxiv.org/html/2608.11095v1)**
   (Kushal Chakrabarti, South Park Commons; arXiv, Aug 2026). **L.**
   - Gives the mechanism behind instruction-file bloat and a tested fix (outcome-bearing
     hidden rationale comments) that maps directly onto sase's note and decision-record
     model.
2. **[Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?](https://arxiv.org/abs/2602.11988)**
   (Gloaguen, Mündler, Müller, Raychev, Vechev; ETH Zürich and LogicStar; Feb 2026, v3
   Sep 2026). **L.**
   - The baseline evidence on what always-loaded context costs and buys, including the
     category-removal ablation.
   - Short companion: [Upsun, "your AGENTS.md is probably too long"](https://developer.upsun.com/posts/ai/agents-md-less-is-more).
3. **[Guardrails Beat Guidance: A Large-Scale Study of Rules, Skills, and Persistent Configuration for Coding Agents](https://arxiv.org/html/2604.11088v2)**
   (Zhang et al., AWS GenAI Innovation Center and HSBC; Apr–May 2026). **L.**
   - The prohibitions-versus-directives result is a direct audit tool for sase's "MUST use
     skill X" style.
4. **[Coding Agents Love Decision Records](https://www.oreilly.com/radar/coding-agents-love-decision-records/)**
   (Duncan Davidson; O'Reilly Radar Oct 2, 2026; also on
   [duncandavidson.com](https://duncandavidson.com/agents-love-decisions), Sep 1). **S.**
   - Practical lessons on over-adherence, status semantics and "courtroom transcripts",
     written for exactly the kind of `decisions` web sase has.
5. **[Skill Blocks: How Should an Agent Load Its Skill? A Caching-Correct Comparison…](https://arxiv.org/html/2608.14943)**
   (Hironobu Nakasuji, Microsoft; Aug 2026). **L.**
   - Gives sase a quantitative, cache-aware rule for core vs reference vs strand. Pair it
     with the audited read logs.
6. **[Codified Context: Infrastructure for AI Agents in a Complex Codebase](https://arxiv.org/html/2602.20478v1)**
   (Aristidis Vasilopoulos; Feb 2026). **M–L.**
   - A hot/cold memory system much like sase's, run for 283 sessions. Its drift detector
     and "staleness was the primary failure mode" are the lessons sase hasn't
     operationalized yet.
7. **[Getting Better at Working With You: Compiling User Corrections into Runtime Enforcement for Coding Agents (TRACE)](https://arxiv.org/html/2606.13174v1)**
   (Zhou et al., Notre Dame, Tencent AI Lab and IBM Research; Jun 2026). **L.**
   - "Access ≠ compliance", the forced decision line for memory writes, and compiling
     rules into hooks. Directly relevant to the gate design.
8. **[Building an agentic memory system for GitHub Copilot](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/)**
   (Tiferet Gazit, GitHub; Jan 15, 2026). **S–M.**
   - Citations plus just-in-time verification is the cheapest credible answer to memory
     staleness, and it comes with a real A/B result.

### Tier 2: strong, specific inspiration

9. **[AGENTS.md outperforms skills in our agent evals](https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals)**
   (Jude Gao, Vercel; Jan 27, 2026). **S.**
   - Always-on index vs skills, the anchoring failure of "You MUST invoke", and a
     compressed-index format sase's webs could imitate.
10. **[Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)**
    and **[Prompting Claude Opus 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5)**
    (Anthropic; living docs covering current models). **M.**
    - Official guidance on de-escalating emphasis, explaining the why, overtriggering and
      over-verification for the models sase actually runs.
11. **[Prompt Debt and "Fighting the Weights"](https://www.oreilly.com/radar/prompt-debt-and-fighting-the-weights/)**
    (Tim O'Reilly on Drew Breunig's talk; Aug 13, 2026) together with
    **[How System Prompts Define Agent Behavior](https://blog.nilenso.com/blog/2026/02/10/how-system-prompts-define-agent-behaviiour/)**
    (Srihari Sriraman and Drew Breunig, nilenso; Feb 10, 2026). **S + M.**
    - Vocabulary and metrics for prompt debt: repetition, escalating emphasis, and edit
      history.
12. **[From Agent Behaviour to Agent-Friendly Documentation](https://arxiv.org/html/2608.20195)**
    (Zhijun Gao and Jing Chen, Peking University; Aug 2026). **L.**
    - Shows what agents actually read: instruction files dominate, links are never
      followed, and docs are never checked against code. This should change how strands
      and reference notes are written.
13. **[Gemini CLI Auto Memory](https://geminicli.com/docs/cli/auto-memory/)** plus the
    **[v0.40.0 Tiered Memory release notes](https://github.com/google-gemini/gemini-cli/discussions/26216)**
    (Google; Apr–May 2026). **S.**
    - A shipping design for an extraction miner, a patch inbox, a target allowlist and
      human approval, the closest blueprint for a `sase memory inbox`.
14. **[From Anatomy to Smells: An Empirical Study of SKILL.md in Agent Skills](https://arxiv.org/html/2607.01456v1)**
    (Hong, Imani, Ahmed; UC Irvine; Jul 2026). **M.**
    - A ready-made catalog of 26 smells to lint sase's generated skill templates against.
15. **[Probe-and-Refine Tuning of Repository Guidance for Coding Agents](https://arxiv.org/abs/2606.20512)**
    (Asa Shepard and Jeannie Albrecht, Williams College; Jun 2026). **M–L.**
    - A failure-driven tuning loop with a 3,000-character budget, and the cross-model
      transfer failure that argues for per-provider calibration.
16. **[SkillJuror: Measuring How Agent Skill Organization Changes Runtime Behavior](https://arxiv.org/html/2606.11543v1)**
    (Chen et al.; Jun 2026). **M.**
    - When pointer-based disclosure helps (code, tests, repair) and when it hurts (exact
      thresholds and formats). Pointers should say when and why to read the target.
17. **[Introducing Context Repositories: Git-based Memory for Coding Agents](https://www.letta.com/blog/context-repositories/)**
    (Letta; Feb 12, 2026). **S.**
    - Git-backed memory with reflection and defrag subagents working in worktrees. Close
      to sase's architecture and a good source of consolidation ideas.

### Tier 3: useful context, worth skimming

18. **[Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html)**
    (Feb 5, 2026) and
    **[Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)**
    (Apr 2, 2026), both by Birgitta Böckeler (Thoughtworks, on martinfowler.com). **M.**
    - The "who decides to load" taxonomy and the guides-versus-sensors framing.
19. **[Lessons from building Claude Code: How we use skills](https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/)**
    (Thariq Shihipar, Anthropic; Mar 2026 thread, Jun 2026 page). **S.**
    - Gotchas-first skills, descriptions as triggers, and usage tracking.
20. **[Improving skill-creator: Test, measure, and refine Agent Skills](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)**
    (Anthropic; Mar 3, 2026). **S.**
    - Capability skills vs preference skills, testing without the skill, and trigger
      evals.
21. **[Library Drift](https://arxiv.org/html/2605.19576v1)** (May 2026) and
    **[Experience Compression Spectrum](https://arxiv.org/html/2604.15877v2)** (Apr–Jun
    2026), both by Zhang et al. (AWS and HSBC). **M.**
    - Lifecycle governance and the finding that the authoring template matters most. A
      useful framework for when knowledge should be memory, a skill, or a rule.
22. **[Rule Taxonomy and Evolution in AI IDEs: A Mining and Survey Study](https://arxiv.org/html/2606.12231v1)**
    (Cai, Li, Liang, Li, Shahin; Jun 2026). **M.**
    - How rules evolve and decay, and the gap between the rules practitioners value and
      the rules they write.
23. **[Do Context Files Help Coding Agents? A Two-Agent Ablation Study](https://arxiv.org/html/2607.27250v1)**
    (Prakhar Khatri; Jul 2026). **M.**
    - Always-on vs on-demand wiki on Claude and Codex, and a lesson in how many tasks you
      need to evaluate memory changes.
24. **[Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents](https://arxiv.org/html/2609.00006v1)**
    (Wavestone AI Lab; Jul–Sep 2026). **L; read §7.2 and §9 only.**
    - How 11 harnesses load instruction files, split prompts around the cache boundary,
      and govern memory writes.
25. **[The Consolidation Problem in Agent Memory](https://hindsight.vectorize.io/blog/2026/05/21/agent-memory-consolidation)**
    (Ben Bartholomew, Hindsight/Vectorize; May 21, 2026). **S.**
    - Invalidate rather than delete, and decay that steps on events rather than time.
26. **[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)**
    (Kyle, HumanLayer; Nov 25, 2025). **S.**
    - The canonical practitioner essay on lean root files and progressive disclosure.
27. **[Anthropic tests "auto dream" to clean up Claude's memory](https://tessl.io/blog/anthropic-tests-auto-dream-to-clean-up-claudes-memory)**
    (Paul Sawers, Tessl; Mar 26, 2026) plus
    **[Memory for Claude Managed Agents](https://claude.com/blog/claude-managed-agents-memory)**
    (Anthropic; Apr 23, 2026). **S.**
    - How Anthropic itself handles consolidation, audit and rollback.
28. **[Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)**
    (Ryan Lopopolo, OpenAI; Feb 11, 2026). **M.**
    - AGENTS.md as a ~100-line map over a `docs/` system of record, with CI-validated
      docs and doc-gardening agents.
    - Ranked lower only because sase research already compared sase against it, and the
      page blocked my fetch.
29. **[How to write a great agents.md: Lessons from over 2,500 repositories](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)**
    (Matt Nigh, GitHub; Nov 19, 2025). **S.**
    - The Always / Ask first / Never boundary tiers, and commands placed early.
30. **[Instruction Adherence in Coding Agent Configuration Files: A Factorial Study](https://arxiv.org/abs/2605.10039)**
    (Damon McMillan; May 2026). **M.**
    - Structure nulls and within-session decay. A useful corrective against
      over-engineering file layout. I read only the abstract.

### Also seen (lower priority for this question)

- **[Agent READMEs: An Empirical Study of Context Files](https://arxiv.org/html/2511.12884v1)**
  (Nov 2025). Growth and readability statistics.
- **[On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents](https://arxiv.org/abs/2601.20404)**
  (Jan 2026). Efficiency gains on small PRs.
- **[Authoring Agent Skills: A Software-Engineering Approach](https://arxiv.org/html/2607.25032v1)**
  (Jul 2026). A good comparison table of memory files vs skills vs hooks.
- **[Dynamic context discovery](https://cursor.com/blog/dynamic-context-discovery)**
  (Cursor, Jan 6, 2026). Files as the primitive, with 46.9% token savings on MCP tools.
- **[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)**
  (Anthropic, Nov 26, 2025). Progress files, structured feature lists, and why JSON
  resists overwriting better than Markdown.
- **[SkillsBench](https://arxiv.org/abs/2602.12670v1)** (Feb 2026). Curated skills
  +16.6pp; self-generated skills negative.
- **[Agentic Context Engineering (ACE)](https://arxiv.org/abs/2510.04618)** (Oct 2025, at
  the edge of the window). The brevity-bias counterpoint.
- **[Agent Instruction Files: AGENTS.md, CLAUDE.md, and Cross-Tool Portability](https://codex.danielvaughan.com/2026/05/27/agent-instruction-files-agents-md-claude-md-cross-tool-portability-codex-cli/)**
  (Daniel Vaughan, May 2026, updated Oct 2026) and the same author's
  [four-studies synthesis](https://codex.danielvaughan.com/2026/07/26/do-auto-generated-agents-md-files-actually-help-codex-cli-init-research-evidence-context-engineering/)
  (Jul 2026). Good secondary summaries.
- **Out of window, but the classics everything above cites:**
  - Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025)
  - Manus, "Context Engineering for AI Agents" (Jul 2025)
  - Chroma, "Context Rot" (Jul 2025)
  - "How Many Instructions Can LLMs Follow at Once?" (arXiv 2507.11538, Jul 2025)

---

## Caveats

- **Small, single-setup studies.** Most of the empirical papers use one or two models,
  one benchmark family, and modest sample sizes. Several are single-author preprints that
  have not been peer reviewed. Several authors call their polarity, comment and
  progressive-disclosure effects "suggestive" or "exploratory".
- **Coding-benchmark bias.** Almost every quantitative result measures SWE-bench-style
  coding tasks. sase's instruction files also govern orchestration behavior (final
  declarations, gates, beads, artifact audit), which no benchmark tests. Treat the
  efficiency numbers as directional for that part of sase.
- **Emphasis is untested.** No study directly tests capital-letter emphasis (MUST/NEVER)
  as a variable. The de-emphasis recommendation rests on Anthropic's model-specific
  guidance, Vercel's anchoring anecdote, and the prompt-debt literature.
- **Partly read sources.** These were read only in part, as noted under Method and
  Confidence: McMillan (abstract only), OpenAI harness engineering (fetch blocked), and
  Managed Agents "dreaming" (news coverage only).
