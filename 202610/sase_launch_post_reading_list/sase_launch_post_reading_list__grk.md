# SASE launch-post reading: cockpit, goals, and the layer under the harness

Researcher: `grk` (independent swarm report)
Date: 2026-10-24
Scope: new reading to point SASE, and the launch post in particular, in the right direction
Input: finished `~/bob/ref/blogs/` and `~/bob/ref/papers/` notes from the last six months, plus the launch-post series in `docs/blog/`

This report is a reading brief, not a literature survey. The question is which unread pieces will sharpen the argument you are already making: SASE is the missing operating layer around coding-agent CLIs, the TUI is a cockpit rather than a window farm, and the human job is goals and gates rather than watching every agent.

---

## 1. What the last six months of reading already did

You finished 13 external blogs and 12 papers in `ref/blogs/` and `ref/papers/` since late April 2026. Strip the CV drafts out of the papers list and the remaining diet is unusually coherent. It is a diet of **harnesses, factories, memory, and goals**, with almost no classic human-factors work underneath the cockpit metaphor the posts already use.

### Finished blogs that matter for the post

| Finished | Title | What it did for SASE |
| --- | --- | --- |
| 2026-10-23 | [How the Claude Code team does code review](https://claude.dev/blog/solving-code-review-at-anthropic/) | Agent-authored PRs make review *noise* expensive. Your note on mentors is the same failure: a second agent that nits will spawn more work. The launch post's gates have to sit at approach altitude, not line altitude. |
| 2026-10-23 | [Agentic coding is straining CI](https://claude.com/resources/articles/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic) | Throughput of agent work is now a CI problem. Two-speed verification in SASE is the same shape. |
| 2026-10-21 | [Redesigning source control at Anthropic](https://www.anthropic.com/engineering/redesigning-source-control) | Agents are always-online clients. Your notes ("changesets are what patches should be", "superfans") are product notes, not launch-post notes. Useful later. |
| 2026-10-19 | [Gas Town Emergency User Manual](https://steve-yegge.medium.com/gas-town-emergency-user-manual-cf0e4556d74b) | The most important *negative* example. Yegge: stop everything and read each agent. You: "This feels wrong! You need to check on goals, not individual agents!" That disagreement is the spine of the launch post. |
| 2026-10-16 | [The Coming Loop](https://lucumr.pocoo.org/2026/6/23/the-coming-loop/) (Ronacher) | Agents that keep going. SASE's `%wait`, AXE, and host-owned completion are how a loop becomes a record. |
| 2026-10-10 | [The Dot and the Swarm](https://www.oneusefulthing.org/p/the-dot-and-the-swarm) (Mollick) | Swarm as a social form. SASE's clans/tribes/hoods are the engineering version. |
| 2026-10-03 | [Harness engineering](https://openai.com/index/harness-engineering/) (OpenAI) | Inner loop around Codex. SASE's bet is the *outer* loop around many inner harnesses. |
| 2026-10-03 | [Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) | OpenAI's orchestration spec. Competitor vocabulary, not SASE's. |
| 2026-06-11 | [Steve Kinney on agent memory](https://stevekinney.com/writing/agent-memory-systems) | Token-level memory topologies. Your `[[sase_memory]]` note already treats this as the wrong first abstraction. |

### Finished papers that matter for the post

| Finished | Title | What it did for SASE |
| --- | --- | --- |
| 2026-10-13 | [Goals as first-class abstractions](https://www.microsoft.com/en-us/research/wp-content/uploads/2026/04/2026-goals-as-first-class-abstractions-in-human-ai-collaboration-AutomationXP26_paper_0982.pdf) (Microsoft, AutomationXP26) | Heavily annotated. Goals at any altitude; situated in workflows, not dashboards; provenance; "no tool supports goal-guided agent orchestration" — "sase will!" This is the constructive version of the Gas Town disagreement. |
| 2026-10-10 | [An Architecture for Long-Horizon Agents](https://arxiv.org/abs/2609.19519) | Levels, ticks, cascaded intelligence. Your note: checkpoint a goal every 60 minutes. Host-owned progress, not a longer chat. |
| 2026-10-10 | [Harness Engineering: Anatomy of Eleven Systems](https://arxiv.org/abs/2609.00006) | Source-code study of inner harnesses. Confirms the OpenAI essay empirically. |
| 2026-10-03 | [The Log is the Agent](https://arxiv.org/abs/2605.21997) | Replay from the log. Your note: tool-call replay. Receipts and durable records, not vibes. |
| 2026-10-03 | EA-Graph, filesystem memory, human-inspired memory, Memory OS | Memory as store. Useful for later posts. The launch post should not become a memory paper. |

### What this diet is missing

You have read the **inner harness** (OpenAI, the eleven-system study), the **factory** (Anthropic review/CI/VCS, Gas Town), and the **goal** (Microsoft). You have not read the **cockpit**: distributed cognition, situation awareness, ironies of automation, levels of automation, or programming-as-theory-building.

That is the gap. The launch post already *sounds* like a cockpit paper — "window farm vs control tower", "the scrollback buffer is the database", "plans live in your head" — without citing the people who spent forty years on that exact operator problem. The namesake SASE paper (ACE as command environment, AEE as execution environment) is queued under `sase_blog` and still unread. The [00] draft already cites it. Finish that paper before you write another paragraph of philosophy; the new reading below is what to put *around* it.

---

## 2. The direction the launch post should keep

From `docs/blog/posts/structured-agentic-software-engineering.md` and the [00] draft `why-coding-agents-need-orchestration.md`, plus your Gas Town / goals annotations, the argument worth defending is:

1. **Wrap agent CLIs, do not replace them.** SASE is a control plane. Codex app is the product competitor. Cursor's harness work is the inner-loop competitor. Gas Town is the swarm competitor that watches workers instead of goals.
2. **Durable records outside the model context.** Prompt archives, beads, patches, goals, receipts. Chat is a working buffer. The cockpit remembers; the pilot does not have to.
3. **Human work sits at goal altitude.** Plan approval, launch approval, unread-done, goal markers. Not "read every transcript." Yegge is wrong on this, and Bainbridge / Endsley / Marquet will let you say why without sounding merely opinionated.
4. **Forks and fresh context beat forever-growing sessions.** LongHorizon-Harness now has measurements for that architecture.
5. **The operator's scarce resource is understanding**, not tokens. Karpathy's 2026 line and Geoffrey Litt's queued essay say the same thing Naur said in 1985.

Reading that pulls you toward a shinier inner harness, a Mayor-in-tmux, or "just watch the agents harder" is reading in the wrong direction. The list below is filtered for that.

---

## 3. Ranked new reading

Rank is "read this next if you are writing the launch post this week." Length is honest. Capture lines are for you, not for an agent to run.

### 1. Edwin Hutchins — How a Cockpit Remembers Its Speeds (1995)

- **URL:** [PDF](https://www.ida.liu.se/~729G12/mtrl/cockpit.pdf) · DOI [10.1016/0364-0213(95)90020-9](https://doi.org/10.1016/0364-0213(95)90020-9)
- **Length:** ~24 pages. One sitting.
- **Why:** This is the paper the launch post is already writing without knowing it. Hutchins's unit of analysis is the *cockpit system*, not the individual pilot. Speed bugs, cards, and callouts hold memory that no one person is "remembering." Your list of 😈s — scrollback as database, no notifications, plans in your head, seven windows and no answer to "which one needs me?" — is a cockpit with the instruments torn out. The TUI Agents tab is an attempt to put the instruments back: status glyphs, unread-done, provider badges, grouping by session/clan/tribe. Cite this when you introduce the control-tower diagram.
- **Direction:** Keeps you on "the system remembers" rather than "the operator should read more."
- **Capture:** `bob ref create https://www.ida.liu.se/~729G12/mtrl/cockpit.pdf -L`

Companion, if the Hutchins paper lands: Hollan, Hutchins, and Kirsh, [Distributed cognition: toward a new foundation for human-computer interaction research](https://dl.acm.org/doi/10.1145/353485.353487) (ACM TOCHI, 2000). Same lab, design implications.

### 2. Lisanne Bainbridge — Ironies of Automation (1983)

- **URL:** [PDF (Gwern host)](https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf) · DOI [10.1016/0005-1098(83)90046-8](https://doi.org/10.1016/0005-1098(83)90046-8)
- **Length:** 5 pages.
- **Why:** The designer removes the operator because the operator is unreliable, then leaves the operator the residual tasks the designer could not automate, which are exactly the hard ones, while the operator's skill atrophies from monitoring. That is Yegge's "when an agent finishes, stop everything and read it" and Anthropic's "if machines do most of the reading, how does anyone learn?" in one short paper. It is also why `%auto` and launch approval have to be *typed* gates, not a human staring at a transcript stream. Your mentor-noise annotation on the Anthropic review post is Bainbridge: the second pass is cheap for a person and expensive for an agent, and the person who only nits stops being able to see approach-level mistakes.
- **Direction:** Justifies "don't watch agents work; design the leftover human tasks so they keep the human competent."
- **Capture:** `bob ref create https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf -L`

2026 restatement, if you want a contemporary voice after the original: Margaret Mitchell, Avijit Ghosh, and Samir Passi, [AI Agents Push Humans Out of the Loop](https://arxiv.org/abs/2608.23642) (arXiv, Aug 2026). Position paper: current HITL degrades the overseer; design for the *situated goals of oversight*. Ranked just under Bainbridge because the original is shorter and better.

### 3. Peter Naur — Programming as Theory Building (1985)

- **URL:** [PDF](https://pages.cs.wisc.edu/~remzi/Naur.pdf) · HTML gist [onlurking/fc5c81d18cfce9ff81bc968a7f…](https://gist.github.com/onlurking/fc5c81d18cfce9ff81bc968a7fbd4294)
- **Length:** ~9 pages.
- **Why:** A program is a theory in the heads of the people who can explain and modify it. The text is a deposit of that theory, not a substitute. Revival from documentation alone is "strictly impossible." This is the deepest justification for (a) forks instead of one immortal session, (b) host-owned completion instead of "the chat is the work," and (c) Karpathy's 2026 line "you can outsource your thinking, but you can't outsource your understanding." The launch post should not claim SASE *stores* the theory. It should claim SASE keeps the theory from dying in scrollback while the human is still the one who has to have it.
- **Direction:** Stops the post from sliding into "agents write, humans rubber-stamp."
- **Capture:** `bob ref create https://pages.cs.wisc.edu/~remzi/Naur.pdf -L`

### 4. LongHorizon-Harness — Advancing Long-Horizon Agents for Real-World Tasks (Aug 2026)

- **URL:** [arXiv:2608.01964](https://arxiv.org/abs/2608.01964)
- **Length:** 29 pages; the MEA loop in the abstract and §2–3 is the payload.
- **Why:** This is the closest 2026 paper to SASE's actual architecture. Inner harnesses keep execution, task state, and "am I done?" inside a growing context; wrong self-assessments then poison later steps. LongHorizon-Harness puts **task state outside execution**, updates it only with environment-verified facts, and runs a Manage–Execute–Audit loop: a manager picks the next subtask, a **fresh-context executor** does it, a read-only auditor checks the world. `AgentAdapter` wraps native model/harness backends *without modifying their loops*. That is "SASE wraps agent CLIs, not models" with measurements (Qwen 3.7-Plus 51.8% → 80.7% on WeaveBench; Terminal-Bench 2.1 and OSWorld 2.0 also up).
- **Direction:** Empirical backing for host-owned state, `#fork`, and wrapping CLIs. Do not steal their inner-harness tricks; steal the *split*.
- **Capture:** `bob ref create https://arxiv.org/abs/2608.01964 -L`

### 5. Simon Willison — Embracing the parallel coding agent lifestyle (5 Oct 2025)

- **URL:** [simonwillison.net/2025/Oct/5/parallel-coding-agents](https://simonwillison.net/2025/Oct/5/parallel-coding-agents/)
- **Length:** ~15 minutes.
- **Why:** This is the status-quo post the launch post is answering. Multiple Claude Code / Codex CLI terminals, YOLO mode, skepticism that review is the bottleneck, fresh checkouts instead of worktrees, async agents on a phone. He is honest that he can only *land* one significant change at a time. Cite this as the window farm in the wild, then show what SASE adds: durable records, one surface, gates, `%wait`, unread-done. Pair with his earlier definition post, [An LLM agent runs tools in a loop to achieve a goal](https://simonwillison.net/2025/Sep/18/agents/) (18 Sep 2025) — one sentence, and the noun is **goal**.
- **Direction:** Names the problem without Gas Town's mythology.
- **Capture:** `bob ref create https://simonwillison.net/2025/Oct/5/parallel-coding-agents/ -L` and `bob ref create https://simonwillison.net/2025/Sep/18/agents/ -L`

His [Designing agentic loops](https://simonwillison.net/2025/Sep/30/designing-agentic-loops/) (30 Sep 2025) is the companion: the skill is designing the tools and the loop, not babysitting approvals. Macros are how SASE makes that skill portable.

### 6. Melanie Warrick — Durable, flexible multi-agent systems (Temporal, 6 Aug 2026)

- **URL:** [temporal.io/blog/durable-flexible-multi-agent-systems](https://temporal.io/blog/durable-flexible-multi-agent-systems)
- **Length:** ~11 minutes. Demo repo linked.
- **Why:** The sentence you want: **"Temporal isn't replacing your framework. It's the layer underneath it."** ADK and LangGraph become per-workload choices; durability, retries, and human wait live in the control plane. A human is "an async API" with terrible latency; the wait is durable state, not a blocked thread; "waiting on a human is a machine succeeding at doing nothing, correctly." Gates live in the workflow, not in an LLM tool. That is SASE's plan/launch approval story told with distributed-systems vocabulary instead of TUI vocabulary. Also: separate task queues so reasoning cannot starve the work, which is AXE/lumberjacks in another dialect.
- **Direction:** Strengthens "wrap CLIs / harnesses" and "a gate is not a chat."
- **Capture:** `bob ref create https://temporal.io/blog/durable-flexible-multi-agent-systems -L`

### 7. Andrej Karpathy — Software 3.0 (YC AI Startup School 2025; Sequoia Ascent 2026)

- **URL:** [Latent Space annotated transcript](https://www.latent.space/p/s3) (best single artifact). Software 2.0 background: [karpathy.github.io/2017/11/07/software-2-0](https://karpathy.github.io/2017/11/07/software-2-0/).
- **Length:** Talk + notes, one evening. You already finished his [llm-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
- **Why:** Prompts as programs; agents as a third consumer of software (humans get GUIs, computers get APIs, agents get something in between); **autonomy slider** and partial autonomy rather than demo-AGI; "you can outsource your thinking, but you can't outsource your understanding." The launch post's "scarcity is coming for our robot budgets" section should cite this instead of only the AI Daily Brief. Software 3.0's selection criterion is *verifiability* — tests, scores, proofs — which is why SASE's receipts, `just check`, and two-speed CI belong in the philosophy, not only in later posts.
- **Direction:** Autonomy slider ≡ `%auto` / plan vs epic vs YOLO. Understanding stays human ≡ goals and unread-done.
- **Capture:** `bob ref create https://www.latent.space/p/s3 -L`

### 8. When Sub-Agents Work in Parallel (arXiv:2610.10263, 7 Oct 2026)

- **URL:** [arXiv:2610.10263](https://arxiv.org/abs/2610.10263)
- **Length:** Empirical paper; skim the 13 failure modes and the "when it helps" conditions.
- **Why:** Matched Codex / Claude Code / Kimi runs with dynamic concurrency on or off, 354 tasks, 2,124 executions. On short tasks the model dominates; on long-horizon work **orchestration** dominates. Thirteen concurrency-specific failure modes. This is the evidence base for launch approval, clans, `%wait`, and "fan-out is a gate, not a default." It is a week old. Read it before the post freezes its multi-agent claims.
- **Direction:** Multi-agent as a scheduled policy, not a personality.
- **Capture:** `bob ref create https://arxiv.org/abs/2610.10263 -L`

### 9. Cursor — Continually improving our agent harness (30 Apr 2026)

- **URL:** [cursor.com/blog/continually-improving-agent-harness](https://cursor.com/blog/continually-improving-agent-harness)
- **Length:** ~11 minutes.
- **Why:** How a serious inner harness is actually improved: Keep Rate of generated code, LLM-judged user satisfaction, tool-error SLOs, per-model tool formats, "context anxiety," mid-chat model switching as a distribution-shift problem, **subagents as the way to switch models without poisoning history**. Closing claim: the multi-agent future "will live in the harness rather than any single agent." That last sentence is true *inside Cursor* and false as a product strategy for you. SASE's move is to let Cursor, Claude Code, Codex, agy, and Muse each keep their inner harness, and to own the outer coordination, records, and gates. Read this to know the competitor's best argument, then decline to become a second Cursor.
- **Direction:** Inner harness vs operating layer. Forks vs mid-chat model switching.
- **Capture:** `bob ref create https://cursor.com/blog/continually-improving-agent-harness -L`

### 10. Parasuraman, Sheridan, and Wickens — A model for types and levels of human interaction with automation (2000)

- **URL:** DOI [10.1109/3468.844354](https://doi.org/10.1109/3468.844354) · PubMed [11760769](https://pubmed.ncbi.nlm.nih.gov/11760769/)
- **Length:** ~12 pages.
- **Why:** Automation is not one knob. Four types — information acquisition, information analysis, decision and action selection, action implementation — each on a continuum from manual to full auto. A system can (and should) automate them at different levels. SASE already does this without the vocabulary: the TUI automates acquisition and analysis (who is waiting, who failed, who has a plan); plan/launch approval keep decision selection human; `%auto` moves selected decisions up the ladder; the provider CLI still implements actions. Use this table in the post or a later "gates" post instead of inventing a new autonomy taxonomy.
- **Direction:** Typed `%auto`, not a Mayor that either runs everything or nothing.
- **Capture:** `bob ref create https://doi.org/10.1109/3468.844354 -L`

### 11. Mica Endsley — Toward a Theory of Situation Awareness in Dynamic Systems (1995)

- **URL:** DOI [10.1518/001872095779049543](https://doi.org/10.1518/001872095779049543)
- **Length:** ~30 pages; the three-level model in the first third is enough.
- **Why:** SA1 perception, SA2 comprehension, SA3 projection. Working memory is the bottleneck; **goal-directed behavior** is how operators overcome it. A TUI that dumps every tool call is SA1 spam. Unread-done, PLAN/`?` glyphs, metric strip, and goal markers are SA2/SA3 instruments. This is the academic version of your Gas Town comment. Pair with Hutchins: Hutchins says the cockpit holds memory; Endsley says the display must be organized around goals or the operator will not see what matters.
- **Direction:** Check goals, not agents.
- **Capture:** `bob ref create https://doi.org/10.1518/001872095779049543 -L`

### 12. METR — Measuring AI Ability to Complete Long Tasks (2025, v4 Jul 2026)

- **URL:** [metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) · [arXiv:2503.14499](https://arxiv.org/abs/2503.14499)
- **Length:** Blog is enough; paper if you want the method.
- **Why:** 50% time-horizon doubling ~every seven months. The launch post's "tmux full of CLIs" problem gets worse on a clock: each doubling of autonomous duration is a doubling of state that will die in scrollback unless an operating layer holds it. Also the scarcity argument: human review time does not double.
- **Direction:** Why the operating layer is timely, not merely tasteful.
- **Capture:** `bob ref create https://arxiv.org/abs/2503.14499 -L`

---

## 4. One book, if you want a narrative analog

**L. David Marquet, *Turn the Ship Around!*** — intent-based leadership. "I intend to submerge the ship" instead of "request permission." Competence plus clarity, then release control. This is the management-story version of plan gates and goals. Your Gas Town note already wants this: the Mayor is not a watcher of sailors; the captain sets intent and the crew acts. Only worth a full read if the papers above are not enough metaphor. Not in the library.

Lucy Suchman's *Plans and Situated Actions* (1987) is the research-grade version of the same idea — plans are resources for action, not programs the world will execute. Useful for the SDD/beads post more than the launch post.

---

## 5. Already in your library — finish these first

These are not "new." They are the queued/started items that actually serve the launch post. Do them before adding more factory-of-agents papers.

| State | Item | Why it is in front of the new list for *this* post |
| --- | --- | --- |
| queued, parent `sase_blog`, high, scheduled 2026-10-19 | [Agentic Software Engineering: Foundational Pillars and a Research Roadmap](https://arxiv.org/abs/2509.06216) (Hassan et al.) | The namesake. ACE / AEE, SE for Humans vs SE for Agents, Merge-Readiness Packs, Consultation Request Packs. The [00] draft already cites it. You have 2 highlights. Finish it. |
| started, legacy `xprompt_ref` | [PDL: A Declarative Prompt Programming Language](https://arxiv.org/abs/2410.19135) | Already cited in [00] as the ancestor of YAML macro workflows. You started it in January and never finished. |
| started | [The AI-native SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook) | In progress as of today. Factory vocabulary from Anthropic; keep it from swallowing the cockpit argument. |
| queued | [Reality Is the Final Verifier](https://arxiv.org/abs/2609.12039) (Berkeley, Zaharia/Stoica) | Requirement gap vs model gap; human judgment as the scarce resource. Scheduled 2026-11-07. Aligns with receipts and "reality is the verifier," not with watching agents. |
| queued | [Understanding is the new bottleneck](https://www.geoffreylitt.com/2026/07/02/understanding-is-the-new-bottleneck) (Geoffrey Litt) | Same thesis as Naur/Karpathy, in a contemporary essay. |
| started, legacy | Jesse Vincent, [How I'm using coding agents in September 2025](https://blog.fsck.com/2025/10/05/how-im-using-coding-agents-in-september-2025/) | Architect/implementer split in two Claude sessions, worktrees, "do not deviate from the plan." Window-farm craft. Started Oct 2025 in the zorg backlog; either finish or drop. |
| queued | Stripe [Minions](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents), Mitchell Hashimoto [AI adoption](https://mitchellh.com/writing/my-ai-adoption-journey), Ronacher [Astra why](https://lucumr.pocoo.org/2026/9/7/astra-why/), Databricks [Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents) | Good, later. Minions/Omnigent are inner-harness/meta-harness pieces. Astra is Ronacher's "why another coding agent." None of them should delay Hutchins/Bainbridge/Naur. |
| started, legacy | [Toward Agentic Software Engineering Beyond Code](https://arxiv.org/abs/2510.19692) (Hoda) | Values and vocabulary beyond code. Useful for the series, not the front door. |

**Prequel, not in library:** Hassan et al., [Towards AI-Native Software Engineering (SE 3.0)](https://arxiv.org/abs/2410.06107) (2024, ACM version 2026). Cognitive overload of SE 2.0 copilots, intent-centric stack. Read *after* the namesake paper, as history.

**Survey, not in library:** He, Treude, and Lo, [LLM-Based Multi-Agent Systems for Software Engineering](https://arxiv.org/abs/2404.04834) (TOSEM 2025). 71 studies, mostly code-generation MAS. Use it to say SASE is not ChatDev-with-a-TUI.

---

## 6. What not to chase this week

- More Gas Town / Beads / Mayor operational detail. You finished the manual. Your disagreement is recorded. Further Yegge will pull the post toward swarm ops.
- More inner-harness engineering (Doc2Harness, RiseHarness, Self-HPO). You already finished the OpenAI essay and the eleven-system paper. Diminishing returns for a launch post.
- Enterprise "AI control plane" vendor blogs (MuleSoft, Fiddler, Preloop). Same metaphor, wrong altitude: MCP firewalls, not coding-agent cockpits.
- Memory papers. You finished four. The launch post should mention memory as a later post, which `[09]` already does.
- Compiler.next / intent-compilers. Fun, orthogonal, and it will make the post sound like SE 3.0 vapor.

---

## 7. Ranked list (compact)

Read in this order if the goal is the launch post:

1. Hutchins, *How a Cockpit Remembers Its Speeds* (1995) — the metaphor.
2. Bainbridge, *Ironies of Automation* (1983) — why watching is the wrong leftover task.
3. Naur, *Programming as Theory Building* (1985) — understanding stays human.
4. LongHorizon-Harness (arXiv:2608.01964, 2026) — state outside the harness, wrap native loops.
5. Willison, *Embracing the parallel coding agent lifestyle* + *tools in a loop to achieve a goal* (2025) — the window farm, named.
6. Temporal, *Durable, flexible multi-agent systems* (2026) — the layer under the framework.
7. Karpathy, Software 3.0 (Latent Space / Sequoia 2025–2026) — autonomy slider, verifiability, understanding.
8. *When Sub-Agents Work in Parallel* (arXiv:2610.10263, Oct 2026) — fan-out failure modes.
9. Cursor, *Continually improving our agent harness* (2026) — inner-loop competitor, decline to copy.
10. Parasuraman, Sheridan, Wickens (2000) — typed levels of automation.
11. Endsley, situation awareness (1995) — goal-directed displays.
12. METR long-task horizon (2025/2026) — why the layer is urgent.

**Do not skip, even though they are not new:** Hassan et al. namesake paper (queued, `sase_blog`); PDL (started); *Reality Is the Final Verifier* (queued); Litt, *Understanding is the new bottleneck* (queued).

Suggested captures for the new twelve:

```text
bob ref create https://www.ida.liu.se/~729G12/mtrl/cockpit.pdf -L
bob ref create https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf -L
bob ref create https://pages.cs.wisc.edu/~remzi/Naur.pdf -L
bob ref create https://arxiv.org/abs/2608.01964 -L
bob ref create https://simonwillison.net/2025/Oct/5/parallel-coding-agents/ -L
bob ref create https://simonwillison.net/2025/Sep/18/agents/ -L
bob ref create https://simonwillison.net/2025/Sep/30/designing-agentic-loops/ -L
bob ref create https://temporal.io/blog/durable-flexible-multi-agent-systems -L
bob ref create https://www.latent.space/p/s3 -L
bob ref create https://arxiv.org/abs/2610.10263 -L
bob ref create https://cursor.com/blog/continually-improving-agent-harness -L
bob ref create https://doi.org/10.1109/3468.844354 -L
bob ref create https://doi.org/10.1518/001872095779049543 -L
bob ref create https://arxiv.org/abs/2503.14499 -L
bob ref create https://arxiv.org/abs/2608.23642 -L
bob ref create https://arxiv.org/abs/2410.06107 -L
```

Library check: 13 of 40 unique candidates already in your library (0 finished).
