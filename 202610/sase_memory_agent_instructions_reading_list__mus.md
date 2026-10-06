# Inspiring sase's memory files and agent instruction files: recent reading list

Researcher: mus (`__mus.md`) — independent swarm report.
Date: 2026-10-06. Scope: articles published within the last year (after 2026-10-06 minus 12 months, i.e. roughly Oct 2025 → Oct 2026) most likely to inspire improvements to sase's memory files (`sase/memory/` core / reference / webs) and agent instruction files (`AGENTS.md`, provider shims, instruction bundles / delivery).

## How I judged

sase's current design (from this checkout's `AGENTS.md` + `sase/memory/`):

- Core memory inlined every turn (paid every turn), reference memory listed-by-description and read on demand, webs as descriptor + strands read via `sase memory read`.
- Instruction delivery split across root instruction file, provider shims, and on-demand reads — i.e. already a progressively-disclosed system, but with open questions about budgets, precedence, duplication, and auto-maintenance.

I ranked for: (a) direct transferability to those mechanisms, (b) recency + authority (first-party harness teams > synthesis > opinion), (c) falsifiability (measured shrinks, evals, byte budgets beat maxims). Publication dates verified via page fetch / search-index snippets on 2026-10-06; where I could not fetch the full primary, I say so.

## Ranked list (read in this order)

### 1. Anthropic — "The new rules of context engineering for Claude 5 generation models" (Jul 24, 2026)

- URL: `https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/` (originally `claude.com/blog/...`, now redirects to `claude.dev`; verified by fetch 2026-10-06)
- Author: Thariq Shihipar (Claude Code team). 7-min read.
- Claim: removed **>80% of Claude Code's system prompt** for Opus 5 / Fable 5 with "no measurable loss on coding evaluations."
- The six shifts: (1) rigid rules → judgment ("match surrounding comment density" beats "never write comments"); (2) worked examples → expressive interface design (enums hint usage better than examples); (3) all-upfront → progressive disclosure (verification/review become on-demand skills; deferred tool loading via ToolSearch); (4) repetition → single simple tool descriptions; (5) manual `CLAUDE.md` maintenance (`#` hotkey) → auto-memory; (6) plain-markdown specs → rich references (HTML artifacts, test suites, rubrics).
- Ships `claude doctor` (`/doctor`) to rightsize skills and `CLAUDE.md` files.
- Why #1 for sase: this is the strongestabandoned-80%-and-nothing-broke datum for exactly sase's problem — core memory + always-on instructions are the tax. Direct provocations: which `type: core` lines survive a Shihipar-style deletion pass? Which reference notes should become skills with deferred loading? Should sase get a `/doctor` equivalent (audit core-token cost, orphaned strands, conflicting directives)?
- Caveat companion (read next, not separately ranked): DevelopersDigest, "Anthropic Removed 80% of Claude Code's System Prompt. Here Is What They Learned" (Jul 26, 2026, `https://www.developersdigest.tech/blog/claude-5-context-engineering-rules-hn-analysis`) — summarizes the HN thread (197 pts / 133 comments): Simon Willison confirms "use your own judgement" works on Fable 5; skeptics warn about lock-in (logic moves from portable `.md` into Anthropic tooling), accidental deletions/regression anecdotes on Opus 5, and auto-memory cross-talk. Read it as the risk lens on #1.

### 2. Anthropic — "Equipping agents for the real world with Agent Skills" (Oct 16, 2025; open standard Dec 18, 2025)

- URLs: engineering post `https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills`; spec `https://agentskills.io/specification`, repo `https://github.com/agentskills/agentskills` (existence + dates corroborated via multiple secondary sources 2026-10-06; primary not full-fetched this session).
- Claim: skills as folders (`SKILL.md` + `scripts/` + `references/` + `assets/`) with **three-level progressive disclosure**: `name` + `description` (~30–50 tokens) always on → full `SKILL.md` on trigger → linked files on demand.
- Spec is "deliciously tiny" (Simon Willison's phrase, via EdibleByte Aug 2026 synthesis): six frontmatter fields, three optional dirs, one disclosure rule. Adopted within weeks by Codex CLI, VS Code, GitHub, Cursor, Gemini CLI, Goose; marketplaces index 400k+ skills by early 2026.
- Why #2 for sase: this is the industry's converged answer to sase's core/reference/web split. sase memory webs (descriptor always inlined, strands on demand) already rhyme with it — the article + spec give sase the vocabulary and conformance target: frontmatter discipline, description-as-retrieval-index quality, evaluation-driven skill creation ("find capability gaps by running representative tasks, then build skills" — not speculation). Most portable idea in the list.

### 3. Paul Iusztin / DecodingAI — "Context Engineering for Coding Agents" (Aug 25, 2026)

- URL: `https://www.decodingai.com/p/context-engineering-for-coding-agents` (Lesson 4 of "Building a Coding Agent From Scratch"; verified by fetch 2026-10-06).
- Claim: 4 harness components keep the window high-signal; system prompt assembled fresh each run from base prompt + active-agent prompt + memory files (`AGENTS.md` + `.decode/MEMORY.md`) + skills catalog (one line per skill). Memory is **two markdown files concatenated root-most → cwd-most, with `MEMORY.md` explicitly size-capped**; every tool schema costs tokens (Pydantic AI evidence).
- Terminal-Bench hook: harness-only change moved same model from ~30th to top 5.
- Why #3: the most buildable mental model for sase's assembler. Steal: size caps on writable memory, layering rule stated as override semantics, per-skill one-liner catalog discipline, tool-count budgeting. Also the course's Lesson 5 ("Subagents Are Context Engineering") pairs with #6.

### 4. Addy Osmani — "Loop Engineering" (Jun 7–8, 2026)

- URL: `https://addyosmani.com/blog/loop-engineering/` (date + five-blocks anatomy corroborated via multiple 2026 digests 2026-10-06; primary not full-fetched this session).
- Claim: stop hand-prompting agents; "replacing yourself as the person who prompts the agent" via loops with five building blocks + external memory (Automations + Worktrees + Skills + Plugins + Sub-agents + State). Boris Cherny (Claude Code head, Apr–Jun 2026 talks) and Peter Steinberger's viral Jun 7 2026 formulation are the backdrop.
- Why #4: reframes sase instruction files from "text users read" to "state the loop loads." If sase instructions are loop state, then staleness, lifecycle (TTL/holds), and verification belong in the file design — directly relevant to sase beads/holds/goals machinery and to the `sase loop` direction. Read with the LangChain companion "The Art of Loop Engineering" (Sydney Runkle, Jun 2026) for the four-loop stack if time permits.

### 5. SurePrompts Editorial — "AGENTS.md: The Instruction File Every Coding Agent Reads (2026)" (Aug 24, 2026)

- URL: `https://sureprompts.com/blog/agents-md-guide-2026` (verified by fetch 2026-10-06).
- Facts: one file read by ~2 dozen tools; no schema; **nearest-file-wins** nesting for monorepos; explicit chat instruction overrides file (policy, not guardrail); stewardship: Agentic AI Foundation (Linux Foundation, formed Dec 2025) anchors `AGENTS.md` + MCP + goose; 60k+ repos adopted by late 2025.
- Editorial judgments most useful for sase: the **commands section + definition of done are the two highest-value, most-missing sections**; **length is a per-turn cost** (unlike skill bodies) — keep root short, push depth to nested files/skills/docs.
- Why #5: the best single 9-minute brief to hand anyone touching sase's root `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` parity problem. Pair with the open-standard history (OpenAI Aug 2025 → LF Dec 9 2025) for the "why one file won" context.

### 6. Remy B. — "Claude Code Skills vs Subagents vs Hooks vs Workflows: Which to Use in 2026" (Sep 2026, Towards AI)

- URL: `https://pub.towardsai.net/claude-code-skills-vs-subagents-vs-hooks-vs-workflows-which-to-use-in-2026-120db6ae5b3c` (redirect-blocked on fetch 2026-10-06; contents corroborated via search snippets + `dev.to` mirror `https://dev.to/remybuilds/claude-code-skills-vs-subagents-vs-hooks-vs-workflows-which-to-use-in-2026-5bcf`).
- Claim: decision guide across the four layering primitives (defaults cited: 20 subagents, 3 nesting layers). Practitioner rules quoted: Willison (Jul 2026) "use judgement to pick a lower-power model and delegate typing to a subagent"; Osmani (Jun 2026) "subagents burn tokens, spend them where a second opinion is worth paying for."
- Why #6: sase's recurring confusion is "which mechanism owns this behavior — memory line, skill, subagent, hook, workflow?" This is the only ranked piece that answers that as its thesis. Use it to triage proposals that currently default to "add a core-memory line."

### 7. Robert Adamson — "The More Context You Give Your AI Coding Agent, the Worse It Can Get" (Oct 3, 2026, dev.to)

- URL: `https://dev.to/robertadam987_/the-more-context-you-give-your-ai-coding-agent-the-worse-it-can-get-4d40` (verified by fetch 2026-10-06; posted "Oct 3" — freshest item on the list).
- Claim: practitioner argument for **progressive context** ("let the agent earn more context as the task requires"): start with scout/search, load full context only at edit time. Frames the failure as measurable context rot, not just cost.
- Why #7: newest + most opinionated counterweight to "just add it to memory." Good stimulator for a sase deletion/graduation review, though lighter on evals than #1–#3 — hence ranked below them.

### 8. Simon Willison + Claude Code "mods" — AGENTS.md native support note (Sep 18, 2026) and skills-portability framing

- Key links: `https://simonwillison.net/2026/Sep/18/thariq-shihipar/` (via search corroboration; primary not fetched); context `https://github.com/venables/skills/blob/HEAD/skills/optimize-agents-md/RESEARCH.md`; portability quote via `https://mcp.directory/blog/cross-agent-skills-cursor-codex-cline-antigravity-gemini-mastra-portability`.
- Facts: Claude Code added native `AGENTS.md` fallback ("if no `CLAUDE.md`, check `AGENTS.md`; toggle in `/config`", Thariq Shihipar Sep 18 2026); Willison: "now I can stop dropping `CLAUDE.md` files which just contain `@AGENTS.md`." Standing Willison line: skills are "a new layer in the stack," portable day-one across Codex/Gemini ("point CLI at `SKILL.md` and it works").
- Why #8: directly informs sase's provider-parity / symlink strategy (`AGENTS.md` canonical vs `CLAUDE.md`/`GEMINI.md` shims) and the "which file wins if both exist" question Matt Pocock et al. raised. Small, fast read with an immediate sase action (audit shim duplication).

### 9. OpenAI Codex instruction hierarchy + byte-budget docs, and the `dropped` truncation X-ray (2026 tooling)

- Key links: Codex base instructions `https://github.com/openai/codex/blob/63d213884daea50e4f74efc192cdc44f549b67d5/codex-rs/protocol/src/prompts/base_instructions/default.md`; Codex issue `@include` discussion `https://github.com/openai/codex/issues/17401` (`project_doc_max_bytes` truncation); tool `https://github.com/phrypy/dropped` ("byte-exact truncation X-ray for `AGENTS.md`/`CLAUDE.md`"; `dropped --target codex --ci .` fails builds on truncation).
- Facts (via secondary research notes 2026-10-06; Codex primaries not full-fetched): Codex defines the concrete hierarchy — global → project root → directories down to cwd — plus `AGENTS.override.md` and fallback filename lists, with provenance and **byte budgets**; instruction files that exceed budget are silently truncated.
- Why #9: the only ranked item about **silent truncation as a failure mode** — sase's "budgeted router" and preloaded-memory-size work should read this before designing any new always-on bundle. The `dropped` CI-gate pattern (fail the build when instructions would be cut) is directly stealable for sase lint.

## Deliberately excluded / honorable mentions

- Anthropic, "Effective context engineering for AI agents" (Sep 29, 2025, `https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`) — the canonical "smallest set of high-signal tokens / finite attention budget" framing (compaction, structured notes, JIT retrieval, subagent isolation). Foundational, but **7 days outside the 12-month window** (verified date Sep 29 2025 vs cutoff ~Oct 6 2025), so not ranked; read it as the prequel to #1.
- Mem0 (Apr 2026 paper `arXiv:2504.19413`), Zep/Graphiti temporal graphs, Letta/MemGPT self-editing memory, LangMem comparisons (e.g. `https://agentmarketcap.ai/blog/2026/04/10/agent-memory-vendor-landscape-2026-letta-zep-mem0-langmem`) — valuable if sase ever moves beyond markdown files to vector/graph memory, but lower transferability to sase's current markdown-file architecture than anything ranked; revisit only if that boundary changes (cf. `rust_core_backend_boundary` litmus).
- Medium "Skills Are the New Standard" (EdibleByte, Aug 2026) and SwirlAI "Agent Skills: Progressive Disclosure as a System Design Pattern" — good syntheses of the Dec 18 2025 standard moment, but downstream of #2; use as onboarding handouts, not primary inspiration.

## What I'd steal first (for the lead's synthesis)

1. A Shihipar-style deletion pass over `type: core` + root instructions, with coding-eval guardrails (#1).
2. A `/doctor`-like auditor: core-token cost, conflict detection ("leave docs as appropriate" vs "DO NOT add comments"), orphaned strands, truncation risk (#1, #9).
3. Frontmatter + description-quality bar for memory webs treated as skills (#2).
4. Explicit hierarchy + byte-budget + precedence doc, with a `dropped`-style CI gate (#5, #9).
5. A "which layer owns it" triage (memory line vs skill vs subagent vs hook vs workflow) before any new always-on text (#6), defaulting to progressive context (#7) and loop-owned state (#4).

## Sources consulted (method note)

Web searches on 2026-10-06 for: `AGENTS.md` best practices; `MEMORY.md` / context engineering 2026; Claude Code `CLAUDE.md` / system-prompt 2026; context rot / progressive disclosure 2025–2026; Agent Skills open standard Dec 2025; AGENTS.md open standard / Agentic AI Foundation; instruction hierarchy / byte budgets; Osmani loop engineering; "more context … worse". Full-fetch verified: Anthropic new-rules post (via `claude.dev` redirect target), DecodingAI Lesson 4, DevelopersDigest HN analysis, SurePrompts AGENTS.md guide, Adamson dev.to piece. Partially verified (search-snippet + secondary corroboration, primary not full-fetched): Agent Skills engineering post/spec, Osmani loop essay, Towards-AI skills-vs-subagents guide, Codex hierarchy docs. No peer swarm reports (`__cdx`/`__cld`/`__grk`/`__gem`) were opened or consulted.
