# SASE Blog Inspiration: New Reading Material

Researcher: mus (5-researcher swarm, independent report)
Date: 2026-10-24
Scope: review Bryan's recently-read `~/bob/ref/blogs/` + `~/bob/ref/papers/` (last ~6 months), then find new reading to inspire SASE work and the first SASE blog post (live-post rewrite at `structured-agentic-software-engineering`).

## Method

- Listed finished external refs via `bob ref list -o external -R finished -g -f json` and filtered to modern (2026) blogs/papers with explicit `finished` dates.
- Read Bryan's own annotations via `bob ref show <ref> -c -f markdown` for the SASE-relevant core set (not just titles).
- Read SASE context: `README.md` (one developer + agent team, TUI + AXE + macros + patches + goals + toolruns), the launch-outline research (`sase_launch_post_outline.md` base report), the `sase_blog_261019` note annotations, and the `sase_related_reading_history.md` synthesis (2026-10-07).
- Searched the open web for 2026 material in the same problem space, fetched each candidate to verify it exists, and ran one batched `bob ref find` so the library status below is honest.
- Did not seek out any peer swarm report. Prior reports in per-topic subdirectories were treated as background only; all conclusions below are my own.

## What you read in the last ~6 months (blogs + papers)

Finished dates are from the library. Items with `finished: None` below were still marked read via their ref task.

### Blogs (finished)

- **Agentic coding is straining CI** (Sachin Malhotra, Anthropic, 2026-09-14; finished 2026-10-23). Annotation: "What?" on the CI-jobs-in-equals-out line. Signal: you are tracking CI-at-agent-scale, but this one did not stick.
- **How the Claude Code team does code review** (Addy Osmani, 2026-10-15; finished 2026-10-23). 6 highlights / 6 comments. Key lines: risk-tier classifier + sensitive-path rules, merge queue + gradual release, "noise costs more when the author is an agent," 3-round cap + diff-only re-review + flag-the-class. You linked the noise problem to mentor loops. Direct SASE relevance: gates, reviewer comments, host-owned completion.
- **Redesigning source control at Anthropic** (Anthropic, 2026-10-13; finished 2026-10-21). 8 highlights / 8 comments. Key lines: git-as-centralized-system vs always-online clients, server-side diff/blame/merge, sparse + virtualized checkouts, changesets in a write-ahead log, per-node daemon + regional cache tiers, Claude "superfans" per component, Sapling/Mononoke pointer. You wrote: "Changesets are what 'patches' should be!" Direct SASE relevance: patches, workspaces, API-first VCS.
- **Gas Town Emergency User Manual** (Steve Yegge, 2026-01-16; finished 2026-10-19). 9 highlights / 9 comments. Mayor-only mode, "don't watch agents work / but read every finished response," crew rigs, `gt sling`, PR Sheriff, daily review-sweeps + bug-fix sweeps ("tending the invisible garden"). Your pushback is the interesting part: "This feels wrong! You need to check on goals, not individual agents!" and the tmux-mayor question. Direct SASE relevance: goals vs agents, AXE/scheduler, gates.
- **diataxis compass + how-to** (Daniele Procida; finished 2026-10-16). No annotations. Relevant to the docs redesign question sitting under `sase_memory_plan`.
- **karpathy/llm-wiki gist** (2026-04-04; finished 2026-10-16). 1 highlight. The compounding wiki pattern: raw sources stay raw, the model maintains index + log + pages, schema file tells it how. You will see this idea return in candidate #4.
- **The Coming Loop** (Armin Ronacher, 2026-06-23; finished 2026-10-16). No annotations. Loop/graph-flavored orchestration.
- **Reminders** (interconnected.org, 2026-01-15; finished 2026-10-11). Agents live where the work already is. Relevant to "why a TUI?" only by contrast.
- **The Dot and the Swarm** (Ethan Mollick, 2026-10-01; finished 2026-10-10). No annotations. Swarm framing.
- **Agent memory systems** (Steve Kinney digest of the Hu et al. survey; finished 2026-06-11). 2 highlights / 2 comments in the current snapshot (the older 29-highlight count lives in the pre-migration record). You linked the token-level passage to `sase_memory`. Core memory-systems framing: forms/functions/dynamics, flat → planar → hierarchical, experiential memory.

### Papers (finished)

- **Goals as First-Class Abstractions in Human-AI Collaboration** (Tankelevitch & Rintel, AutomationXP26, 2026-04; finished 2026-10-13). 13 highlights / 13 comments — your most annotated recent paper. Takeaways you kept: "at any altitude," coordination without tracking every action, persistence + self-regulation, bidirectional evals, no tool does goal-guided orchestration ("sase will!"), goals need provenance + what-if projection + situated cues, bead `goal` field. This is the intellectual backbone of SASE goals. The blog should cite it.
- **An Architecture for Long-Horizon Agents: Levels, Ticks and Cascaded Intelligence** (Nijkamp et al., arXiv 2609.19519; finished 2026-10-10). 1 highlight / 1 comment: per-level detector + judgment-free recovery maps to "log a checkpoint/summary every 60m" under `sase_goals`. Relevant to watchdog/retry design.
- **Harness Engineering** (Barbaste et al., arXiv 2609.00006; finished 2026-10-10). Source-code study of 11 systems. No annotations. You already have a comparison report for this; I treat it as background, not as a new recommendation.
- **EA-Graph** (arXiv 2608.04278), **Filesystem-Based Memory** (arXiv 2607.26637), **Human-Inspired Memory Architecture** (arXiv 2605.08538), **Memory OS** (arXiv 2506.06326), **The Log is the Agent** (arXiv 2605.21997) — all marked read via ref tasks. One annotation among them, and it matters: on *The Log is the Agent*, "Support sase tool call replay?" That plus your Gas Town "materialize steps for replay" comment makes replay the clearest design idea your reading keeps returning to.

### Taste in one paragraph

Your 2026 reading has three centers of gravity: (1) **fleet operations at scale** — CI under 30k merges/day, review pipelines, source control for always-online agents, Gas Town/Symphony/harness lore; (2) **goals and memory as durable state** — goals-first collaboration, memory tiers, filesystem memory, logs-as-agents, replay; (3) **docs and instruction files as the real interface** — Diataxis, Karpathy's wiki, Kinney. Engagement is highest where a piece touches SASE's open questions (goals provenance, patches-as-changesets, mentor noise, replay). The blog outline's open slots — "Why a TUI?", "what SASE generalizes," honesty/AI-slop/prompt-debt, vibe evals, token types, memory done right — are exactly where you have strong opinions but thin external citation. That is what the list below targets.

## Gaps I targeted

1. No hostile reading of the orchestrator genre to answer in the honesty section (Appleton on Gas Town is the named critique in the outline research).
2. Nothing current that separates memory *layers* (your core/reference/strand tiers need a 2026 citation that is not just "files good, vectors bad").
3. Nothing that quantifies the instruction-file question beyond Gao & Chen's queued paper (agents read `AGENTS.md` 60.5% of the time; guides help only with undocumented facts).
4. Nothing data-backed on merge queues at agent scale for the patches/host-owned-completion argument.
5. Nothing on harness token cost to ground the honesty section's numbers.
6. Nothing on the "predeployment evals are proxies" framing for vibe-evals and evals-through-goals.
7. No TUI-competitive context for "Why a TUI?" (every CLI grew a TUI in 2026; SASE's claim has to be cross-provider supervision, not panes).

## Ranked list: what to read next

Ordered by expected inspiration-per-hour for SASE + the blog post. Status labels come from the batched `bob ref find` (2026-10-24).

### 1. From Agent Behaviour to Agent-Friendly Documentation (Gao & Chen, arXiv 2608.20195, 2026-08-20) — already in your library (queued since 2026-10-15)

- URL: <https://arxiv.org/abs/2608.20195>
- What it is: behavior-grounded study — 557 SWE-chat sessions (94,813 events, 3,033 doc interactions) + 33,097 AIDev agent PRs. Finding: instruction files + working notes are 60.5% of doc interactions vs 10.6% classical docs and 1.3% API refs; consultation is self-initiated (70.2%), trails code (code first 4.7x), and is associated with *less* immediate testing; no explicit doc-validation sequence observed.
- Why first: it is the empirical spine for everything the blog wants to say about memory-built instruction files, `AGENTS.md` minimalism, and docs that agents actually read. It also complicates the story honestly (actionability/verifiability "lack consistent behavioural support"), which is exactly the register the honesty section needs.
- SASE angle: memory-built instruction files; `sase_memory_plan`; docs-as-managed-memory; agent-maintained docs.
- Blog slot: core-ideas section + honesty section (docs trail code; agents don't validate from docs).
- Note: queued under `sase_memory_plan`, not finished. Read it next; it strengthens the memory + docs chapters more than anything else on this list.
- Propose: `bob ref create https://arxiv.org/abs/2608.20195` (already captured — just read it).

### 2. Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering (Krentsel et al., arXiv 2609.12039, 2026-09-10) — already in your library (queued, blocked until 2026-11-07)

- URL: <https://arxiv.org/abs/2609.12039>
- What it is: the two-gap framework — requirement gap (intent vs recorded requirements) + model gap (deployment world vs evaluation model). Reward hacking exploits omissions; hallucination widens the gaps. The fix is an assurance–revision loop fed by deployment evidence, framed as resource allocation over human judgment, agent capability, and compute. Stoica keynoted it at HPTS 2026.
- Why second: it gives the blog's evals argument its cleanest sentence — predeployment evals are proxies; acceptable behavior in deployment is the test. That sentence carries the vibe-evals section, the prompt-debt section, and the "what it costs" section without extra machinery.
- SASE angle: evals-through-goals; receipts prove-before-they-skip; triage annotates (KNOWN needs a witness); goal ledger as deployment evidence.
- Blog slot: vibe evals + honesty/limitations. Quote the proxy line, then show what SASE keeps (receipts, witnesses, goal history) to narrow rather than close the gaps.
- Note: queued under `sase` (medium priority). Worth pulling forward; it pairs directly with #1 (docs don't verify) and #5 (guides only help on undocumented facts).

### 3. Gas Town's Agent Patterns, Design Bottlenecks, and Vibecoding at Scale (Maggie Appleton, ~Jan 2026) — not in your library

- URL: <https://maggieappleton.com/gastown>
- What it is: the visual essay the launch-outline research says readers will bring to the post. Four moves: design/planning becomes the bottleneck when agents write everything; the orchestration patterns buried in the chaos (specialized roles + hierarchy, persistent roles/tasks with ephemeral sessions, continuous work streams, merge queues + agent-managed conflicts); the extreme price; and the "Yegge never looks at code — when should we stop looking?" decision guide (domain, feedback loops, risk tolerance, greenfield vs brownfield, collaborators, experience).
- Why third: the blog outline explicitly reserves a slot for this critique and warns against inferring past it. Reading the primary source lets the post answer it precisely instead of straw-manning it — agree on patterns, differ on goals-vs-agents and on reviewability.
- SASE angle: your Gas Town annotations are the counter-argument (goals not agents; review sweeps as gates; PR Sheriff as merge-master). Appleton's pattern catalog maps cleanly onto "what SASE generalizes."
- Blog slot: honesty section + the one short dated respectful Gas Town paragraph (§2.3 in the outline). Read before drafting either.
- Propose: `bob ref create https://maggieappleton.com/gastown`

### 4. Which Layer Does Your Agent's Memory Belong In? (Remy, 2026-10-19) — not in your library

- URL: <https://redreamality.com/blog/agent-memory-layer-survey-2026-decision-framework/>
- What it is: an Oct 2026 survey + decision framework written the week TencentDB Agent Memory, OpenViking (`viking://` virtual filesystem: `resources/`, `user/{id}/memories/`, `skills/`, navigated by `ls`/`tree`/`read`/`grep`), Tencent Hunyuan Hy-Memory-30B, and CopilotKit threads-to-skills all landed. Thesis: "memory" is four jobs — in-task context, personal long-term memory, project/team knowledge, procedural memory — and the write path matters more than storage. Converging pattern: human-readable files as source of truth, vector index derived; the memory store becomes a trust boundary.
- Why fourth: it is the most current map of the exact territory SASE memory occupies, and its three views (layer-first diagnosis; write-path ceiling; files-first convergence + trust boundary) are things the blog can affirm, extend (gated writes, `/sase_memory_write` routing, memory task beads), and complicate (signed/verified memory, receipts).
- SASE angle: core vs reference vs strand tiers; memory webs; preloaded-memory size; gated writes; surfacing the trust-boundary problem SASE already feels (stale memory outliving code).
- Blog slot: memory section. Use the four-layer map to place SASE's tiers, then make the write-path point yours (gates, provenance, dedup).
- Propose: `bob ref create https://redreamality.com/blog/agent-memory-layer-survey-2026-decision-framework/`

### 5. When Coding Agent Guides Help, Hurt, or Do Nothing (Yahhi, DEV, 2026-10-22) — not in your library

- URL: <https://dev.to/yahhi/when-coding-agent-guides-help-hurt-or-do-nothing-28op>
- What it is: 438 tests across 9 configs (Opus/Sonnet/Haiku 5.5, Codex CLI, Antigravity). Result: guides that restate official docs change nothing (32/32 no-difference runs); guides with undocumented quirks flip hard tasks (Garmin heart-rate corridor: 3/8 → 16/16, small models match large ones). Phrasing matters ("colleague's note" beats "follow this guide"); unmentioned notes in a folder sometimes help on their own. (I verified the ClawdBytes summary at `clawdbytes.com` and traced it to this DEV original — cite the DEV original.)
- Why fifth: it turns the blog's `AGENTS.md` advice from taste into a number, and it justifies SASE's minimalism: instruction files should carry only non-standard, undocumented, project-specific facts, and they should be evaluated. Pairs with #1 (60.5% of interactions) and #8 (context files evolve like config code).
- SASE angle: memory-built instruction files; shipped size-alias defaults; skill design (procedural memory as the undocumented-quirk store).
- Blog slot: memory/instruction-file guidance + honesty (why SASE keeps instruction files small and measured).
- Propose: `bob ref create https://dev.to/yahhi/when-coding-agent-guides-help-hurt-or-do-nothing-28op`

### 6. State of Merge Queues 2026 (Mergify, 2026-07-27; report + blog) — not in your library

- URL: <https://mergify.com/blog/state-of-merge-queues-2026> (report: <https://mergify.com/reports/state-of-merge-queues-2026>)
- What it is: 153,000 merges across 160 teams over 90 days. AI-assisted PRs break main about half as often as human ones; breakage scales 16x with team size; private code breaks main 4.5x more than OSS; only ~6% of PRs ride in a batch (avg batch 4, max 16) — batching is the unused lever for CI cost on a busy queue.
- Why sixth: SASE's patches + host-owned completion + land agents need a data-backed merge story, and this is the freshest one. It also reframes the honesty section: agent PRs are not the quality disaster people expect; the disaster is queue throughput and CI spend — which is where batching, bisecting, and fenced masters earn their keep.
- SASE angle: patches lifecycle, merge-queue research threads, fenced master + exact-SHA releases, `just check` vs `just check-full`, CI strain (pairs with the Anthropic test-impact piece you just read).
- Blog slot: future-work / "what it costs" — one statistic, one mechanism (batching), one SASE answer (host-owned landing).
- Propose: `bob ref create https://mergify.com/blog/state-of-merge-queues-2026`

### 7. ToFu: A White-Box, Token-Efficient Agent Harness for Researchers (Ruan et al., arXiv 2607.11423, 2026-07-13) — not in your library

- URL: <https://arxiv.org/abs/2607.11423>
- What it is: an MIT-licensed white-box harness (reads code, edits, runs commands, integrates with dev tools) that claims best Pass@1 on SWE-bench Verified across three backbone LLMs with superior token efficiency and multilingual coverage. The research-object framing is the point: inspectable orchestration logic, tool-use behavior, and harness design.
- Why seventh: SASE is a coordination layer above harnesses, so it needs one open harness it can point at, instrument, and contrast with. ToFu's white-box stance matches SASE's reviewability thesis better than any closed CLI does — and its token-efficiency claims set up #9's cost argument from the other side.
- SASE angle: adapters normalize harnesses; provider parity work; token-budget visibility; a candidate harness for evals-through-goals experiments.
- Blog slot: brief contrast in the architecture paragraph (SASE does not replace harnesses; it supervises them) + a footnote for the token-types discussion.
- Propose: `bob ref create https://arxiv.org/abs/2607.11423`

### 8. Agent READMEs: An Empirical Study of Context Files for Agentic Coding (arXiv 2511.12884, Nov 2025) — already in your library (legacy `unread`, added 2026-01-18)

- URL: <https://arxiv.org/abs/2511.12884>
- What it is: first large-scale study of 2,303 `CLAUDE.md` / `AGENTS.md` / `copilot-instructions.md` files across 1,925 repos. Context files are not static docs but config-code-like artifacts: complex, hard to read, evolving through frequent small additions. (AAIF's writeup adds the actionable edge: specify non-standard practices only, and evaluate before adopting.)
- Why eighth: it is the "how files rot" companion to #1's "what agents read" and #5's "what helps." Three papers, one blog rule: keep instruction files small, non-obvious, and measured — which is precisely SASE's gated-writes + memory-task-bead story.
- SASE angle: instruction bundles vs readable `AGENTS.md`; memory webs vs flat files; lossless archival vs erosion.
- Blog slot: same memory/instruction-file passage as #1 and #5; cite once for the rot finding.
- Note: legacy `unread` under `ref/ai/agent_ref/agent_readmes`. Still worth reading despite the age; nothing newer replaces the corpus size.
- Propose: already captured — schedule it with #1 as a pair.

### 9. What Does a Harness Buy? Tokens, Mostly (Liu & Han, arXiv 2610.04433, 2026-10-03) — already in your library (dropped 2026-10-10; reopen with new reason)

- URL: <https://arxiv.org/abs/2610.04433>
- What it is: model-fixed comparison (Claude Code vs OpenCode vs mini-SWE-agent on SWE-bench Verified). On the 45 hardest tasks, swapping harnesses moves outcomes about as much as rerunning the same harness — the measurable harness effects are ways to *lose* tasks (output caps with no recovery, no compaction, broken offline search). Per-task cost differs up to ~3x; the preamble paid every step is ~16.5k / 7k / 0.8k tokens respectively. Oct 24 coverage ("fancy harnesses cost more, score the same") confirms the finding traveled.
- Why ninth despite the drop: the drop predates both the blog-outline's honesty-section requirements and the Oct 2026 reception. The new reason to reopen is specific: the blog needs a citable number for "what the harness costs," and SASE needs the engineering moral (put effort where the losses are: recovery, compaction, offline-capable search) rather than the leaderboard moral. That is a different reading than the one you dropped.
- SASE angle: preloaded-memory size visibility; token types; guarded recipes; `just check` discipline.
- Blog slot: honesty section — one paragraph, two numbers (preamble tokens, cost multiple), one turn (SASE spends its complexity budget on not-losing: gates, receipts, re-review caps).
- Note: labeled honestly as dropped; reopen only for this purpose.

### 10. Codex CLI's Terminal Rebuild for Parallel Agents (Sep 2026; via AlphaSignal, 2026-09-29) — not in your library

- URL: <https://alphasignal.ai/news/openai-s-codex-cli-rebuilds-the-terminal-to-run-parallel-coding-agents>
- What it is: full-screen TUI with pinned composer + unlimited scrollback, `/agents` across parallel Codex sessions, `/fork` into a git worktree, `/voice`. Corroborated by the 2026 CLI roundups (parallel sessions as table stakes; OpenCode's client/server TUI; Grok Build's mouse TUI + headless mode).
- Why tenth: "Why a TUI?" cannot be argued in a vacuum when every provider grew one. This gives the competitive snapshot in one link: the unit of competition is now the *session list + worktree fork*, which is exactly the layer SASE generalizes (tribes/clans/sessions metadata, cross-provider supervision, durable patches — not panes).
- SASE angle: "Why a TUI?" section; agents tab; supervision vs session-hunting (`Stop Hunting Through Terminal Tabs` makes the same point from the tmux side).
- Blog slot: "Why a TUI?" — concede the CLIs caught up on panes, then differentiate on durability and provider-independence.
- Caveat: secondary source (news digest, not OpenAI docs). Treat as a pointer to the Sep 2026 Codex CLI state, not as gospel; verify `/agents` + `/fork` against current Codex docs before quoting.
- Propose: `bob ref create https://alphasignal.ai/news/openai-s-codex-cli-rebuilds-the-terminal-to-run-parallel-coding-agents`

## Suggested reading order (if time is short)

1. #1 (Gao & Chen) + #5 (Yahhi) as a pair — the instruction-file argument, empirical both ways.
2. #3 (Appleton) before drafting the honesty section and the Gas Town paragraph.
3. #2 (Reality/Verifier) before drafting vibe-evals and limitations.
4. #4 (memory layers) before drafting the memory section.
5. #6 (merge queues) + #9 (harness cost) before drafting "what it costs" and future work.
6. #7, #8, #10 as background while implementing (adapters, instruction bundles, TUI).

## What I deliberately left out

- The Harness Engineering source-code paper (Barbaste et al.): already finished, with its own comparison report in the repo. No need to re-read for the blog.
- Stripe Minions 1+2, Omnigent, Databricks benchmarking, Mitchell Hashimoto's adoption journey, Astra: all `ready`, all reasonable, none beats the ten above on inspiration-per-hour for *this* post. Minions would be #11 (one-shot end-to-end agents as the extreme of "sessions are ephemeral").
- The `sase_next_direction` / memory / goals reading-list reports in per-topic subdirectories: used for orientation, not cited, to keep this report independent.

Library check: 4 of 10 candidates already in your library (0 finished) — 3 queued (#1, #2, #8) plus 1 dropped (#9, with a new reason to reopen). The other 6 (#3, #4, #5, #6, #7, #10) are new to the library.

Proposed captures (run these yourself — I did not write to the vault):

```bash
bob ref create https://maggieappleton.com/gastown
bob ref create https://redreamality.com/blog/agent-memory-layer-survey-2026-decision-framework/
bob ref create https://dev.to/yahhi/when-coding-agent-guides-help-hurt-or-do-nothing-28op
bob ref create https://mergify.com/blog/state-of-merge-queues-2026
bob ref create https://arxiv.org/abs/2607.11423
bob ref create https://alphasignal.ai/news/openai-s-codex-cli-rebuilds-the-terminal-to-run-parallel-coding-agents
```
