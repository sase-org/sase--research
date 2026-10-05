# Goals feature: ten recent articles worth reading

_Researcher mus · 2026-10-05 · project: sase_

**Brief.** The incomplete goals prompt (`~/tmp/incomplete_goals_prompt.md`) asks how to
implement a revised "goals" feature: lighter-weight goal creation, a first-tab Goals
TUI (Needs Review / Active / Permanent / Completed nav sections), `<enter><enter>`
plan-and-verification approval, goal hooks replacing file hooks, `%clan(goal=...)`
launched as its own unit, prompt/goal heartbeats in the right panel, and purging
Completed goals (dismissing their agents). Prior art consulted for context only: the
merged `research:202609/sase_goals_design` design and `research:202609/sase_goals_epic_roadmap`
roadmap syntheses, plus my own `__mus` roadmap report. I did not seek out any peer
`__cdx/__cld/__grk/__gem` report from this swarm.

**Method.** Web search + page fetch, cutoff: published or substantively updated within
1 year of 2026-10-05 (i.e. after 2026-10-05 minus 1y). Every ranked item's URL and date
was verified by fetching the page or by two independent search corroborations; where a
page blocked fetching, that is noted and the date is corroborated twice. Ranked by
expected leverage on the open questions in the incomplete prompt, not by general
quality.

## Ranked list

### 1. Addy Osmani — "Loop Engineering" (Jun 7, 2026)

https://addyosmani.com/blog/loop-engineering/

Defines a loop as "a recursive goal where you define a purpose and the AI iterates
until complete," and argues the job shifts from prompting agents to designing the
system that prompts them. Five loop pieces (scheduled automations, worktrees, skills,
plugins/connectors, sub-agents) plus out-of-conversation memory ("the agent forgets,
the repo doesn't"). Names three tensions: verification burden, knowledge rot,
cognitive surrender.

**Why read it.** This is the strongest external articulation of the "lighter goal
creation" instinct: goals as recursive, self-perpetuating loops rather than heavy
records. It directly informs the goal-hooks-replace-file-hooks TODO (hooks as loop
machinery), the heartbeat TODO (loops need observable state), and warns that lighter
creation pushes cost into verification — which is exactly what the Needs Review
section must absorb.

### 2. Anthropic — "Effective harnesses for long-running agents" (Nov 26, 2025)

https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Two-part recipe for multi-session agents: an initializer that sets up the environment
once, plus a coding agent told to make incremental progress every session and leave a
clean, merge-ready state. Documents two failure modes worth stealing: one-shotting
until context exhaustion (next session inherits a half-implemented mess), and a later
session surveying partial progress and prematurely declaring victory.

**Why read it.** Both failure modes map onto Active-goal semantics: what "leave the
goal in a clean state at heartbeat time" must mean, and why Completed needs a check
stronger than "the agent says so." The initializer/incremental split is also a useful
model for clan-goal vs plan-goal: one sets up the world, the other makes the next
increment.

### 3. Anthropic — "Demystifying evals for AI agents" (Jan 9, 2026)

https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

Task / trial / grader / transcript vocabulary; multi-trial runs because outputs vary;
grade outcomes *and* trajectories; the Opus 4.5 anecdote where the agent "failed" the
eval by finding a better solution than the test allowed.

**Why read it.** Goal verification (the second half of Needs Review) is an eval
problem, and this is the clearest recent statement of the discipline. Two concrete
takeaways: verify transcripts, not just end states (relevant to what a goal claim
should carry as evidence), and design the grader so a genuinely better outcome isn't
scored a failure (relevant to how strict Completed criteria should be).

### 4. OpenAI — "Unrolling the Codex Agent Loop" (Jan 2026; dated Jan 23, 2026 in two independent indexes)

https://openai.com/index/unrolling-the-codex-agent-loop/

Read Context → Plan → Execute → Validate → Commit (or Retry). The harness's job is to
make the Read and Validate steps as information-rich as possible. (Page fetch
returned 403 bot protection; loop shape and date corroborated by two independent
indexes and a mirrored reference copy.)

**Why read it.** This is the canonical industry loop behind the `<enter><enter>`
approval TODO: Plan is staged as a reviewable object *before* Execute, and Validate
is a first-class step before Commit. Compare SASE's planned approval UX against it —
in particular whether plan approval and verification approval should be one gate or
two, since Codex treats them as distinct steps.

### 5. design@tive — "Preventing Agent Drift" (Mar 8, 2026)

https://www.designative.info/2026/03/08/preventing-agent-drift-designing-ai-systems-that-stay-aligned-with-human-intent/

Proposes a four-stage intention lifecycle — Capture → Persist → Maintain → Validate —
as the mechanism that keeps an agent aligned with the human objective while
capabilities execute.

**Why read it.** This is the closest public analog to the goal ledger's lifecycle
thinking, and it pressures the design in a useful way: SASE's lifecycle is heavy on
Persist and Validate but thin on Maintain (what keeps a weeks-old Permanent goal
aligned as the project moves under it?). Read before freezing the Permanent Goals
semantics — drift maintenance may need its own hook or heartbeat rule.

### 6. Addy Osmani — "The New Software Lifecycle" (Jun 16, 2026; on Google's "The New SDLC With Vibe Coding" whitepaper, May 2026)

https://addyosmani.com/blog/new-sdlc-vibe-coding/

"An agent is a model plus a harness," roughly 10/90; the harness explicitly includes
hooks that run deterministic code at set points plus observability that tells you
when the agent is drifting. Cites harness-only gains on Terminal Bench 2.0 (same
model, top-30 → top-5) to argue most agent failures are configuration failures.

**Why read it.** Gives the goal-hooks decision its framing: hooks are harness, and
harness is where the leverage is. Supports replacing file hooks with goal hooks
*if* the goal lifecycle stages are the right deterministic choke points — and
challenges the team to enumerate exactly which goal transitions get a hook, rather
than attaching hooks opportunistically.

### 7. "Fleet of Agents" survey, wayintoai (Aug 10, 2026)

https://github.com/life-itself/wayintoai/blob/HEAD/posts/2026-08-10-fleet-of-agents-survey.md

Surveys multi-agent fleet tooling. Notable pattern: a Company → Project → Goal →
Task hierarchy where tasks carry goal ancestry, so an agent picking up a task
inherits the *why*, not just the *what*; plus governance (approval workflows,
budgets, pause/resume/terminate) as first-class fleet operations.

**Why read it.** Goal ancestry is the idea most relevant to `%clan(goal=...)` as its
own unit: a clan launched with a goal reference should inherit the goal's intent
without re-derivation. Also the only surveyed source tying a Goals-like hierarchy to
fleet governance (budgets, pause/resume/terminate) — useful input on what the
Active section's per-goal controls should offer beyond heartbeats.

### 8. NKKTech — "Multi-Agent Orchestration Patterns 2026" (updated May 24, 2026)

https://nkktech.com/blog/multi-agent-orchestration-patterns-2026

Catalogs handoff sub-patterns: trigger-handoff (condition met), suggest-handoff
(agent recommends, user accepts), continuous-handoff (LLM decides each turn); notes
OpenAI Swarm popularized the pattern.

**Why read it.** Direct input on the `%clan(goal=...)` unit question: which handoff
pattern should goal binding use? Suggest-handoff (agent proposes, human accepts)
looks like the natural shape for clan-goal creation under the "lighter approach,"
while trigger-handoff fits Completed-purge dismissal. Short, applied, easy to lift
concrete mechanics from.

### 9. Voiceflow — "AI Agent Orchestration" (updated Oct 1, 2026)

https://www.voiceflow.com/blog/ai-agent-orchestration

"Budget for state, memory, and observability, not the prompts — that is where
production orchestration actually breaks." Picks structural pattern first
(centralized router, hierarchical, handoff), then tooling; routing + handoff +
grounded answers beats raw multi-agent throughput for supervised surfaces.

**Why read it.** The freshest synthesis, and its warning RHymes with the Goals tab
plan: the tab's cost will be in state/observability (heartbeat freshness, lane
consistency across collapses), not in rendering. Also a useful skepticism check on
making Goals the *first* tab — it argues supervised surfaces earn primacy through
routing and grounding, so the tab should justify its position with triage function,
not inventory display.

### 10. WebProNews — "OpenAI's Persistent Codex Agent" (Aug 27, 2026)

https://www.webpronews.com/openais-persistent-codex-agent-from-chatbot-to-always-on-digital-colleague/

Reports (via The New Stack, Aug 26, 2026) on persistent agents that "continue
without step-by-step human guidance," framed as always-on digital colleagues rather
than session tools.

**Why read it.** The only item squarely about the Permanent Goals concept: agents
that outlive sessions and act without per-step guidance. Secondary reporting, so
weigh it lightly — its value is the product-shape provocation (standing brief +
standing permissions + check-in cadence), which maps neatly onto open questions
about what a Permanent goal owns besides text.

## Honorable mentions (did not make the ten)

- "Human-in-the-Loop Guardrails for AI Agents" (Medium, Apr 2026) — tiered approval
  gates, chain-length limits before mandatory review, plan-first-then-approve-level.
  Closest match to Needs Review triage policy; excluded only because Medium blocked
  verification fetching (date corroborated twice via index metadata).
- "Orchestrating AI Agents with LangGraph: The Supervisor/Worker Pattern" (Medium,
  Jun 2026) — the standard supervisor/worker reference for clan structure; same
  verification caveat.
- mission-control-style open-source agent dashboards (e.g. `rnstev26/mission-control`)
  — heartbeats, live activity feed, registration-to-retirement lifecycle. A project,
  not an article, but the closest existing UX to the planned right-panel heartbeats;
  worth a look before finalizing the Active section.
- Claude Code hooks guide (`code.claude.com/docs/en/hooks-guide`) — deterministic
  lifecycle enforcement and context reinjection; the reference implementation to
  compare goal hooks against.
- `planning-with-files`-style persistent file-based planning (Manus pattern) —
  crash-proof markdown plans with completion-verification stop hooks; a minimalist
  counterpoint to a ledger-backed design.

## Caveats

- Recency was enforced (all ranked items published/updated after 2026-10-05 minus
  1y); depth was not — vendor blogs (#8, #9) and secondary reporting (#10) should be
  mined for mechanics, not trusted for claims.
- Nothing above is TUI-specific; dashboard/heartbeat UX for agent fleets remains a
  gap in the recent literature, which itself suggests user-testing the Goals tab
  early rather than researching it further.
