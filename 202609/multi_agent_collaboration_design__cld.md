# Multi-Agent Collaboration for SASE Agents: What to Build, and in What Order

- **Type:** independent researcher report (`research.26.cld`, one of three researchers in
  a swarm)
- **Date:** 2026-09-21
- **Question:** What is the best way to implement collaboration *between* SASE agents?
  The report ends with a recommended solution.
- **Context read first** (all through `sase artifact read`):
  - `research:202609/multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md`
  - `research:202609/family_channel_delivery/family_channel_delivery.md`
  - `research:202609/sase_collaboration_architecture.md`, for its three-plane framing
- **Evidence base:**
  - SASE at `c6807d24c` and the linked `sase-core` checkout at `8886406`.
  - Live probes on athena: this agent's own headless Claude Code 2.1.278 session, the
    `~/.sase` run archives, and the open message-board bead `sase-xu`.
  - A web survey of vendor documentation, practitioner write-ups and 2025–2026 papers.
    I delegated it to a helper agent, then re-fetched the load-bearing sources myself.
- **Evidence tags:**
  - **[code]** read in the SASE or sase-core tree.
  - **[probe]** observed live on athena today.
  - **[V]** primary source fetched this session.
  - **[S]** secondary source or search snippet.
  - **[unverified]** could not be confirmed.

---

## 0. Bottom line

1. **"Multi-agent collaboration" is six different problems, and SASE needs different
   answers for them.**
   - SASE already handles the two with the strongest evidence of value reasonably well:
     independent fan-out with synthesis, and dependency-ordered parallel work.
   - It is weakest on three loops that have clear value but where no information flows
     back today:
     - **Delegation that returns an answer.**
     - **Independent review whose findings reach the author.**
     - **Human steering of a running sequence.**
   - Live peer-to-peer chat is the problem with the *weakest* evidence of value. It
     should not be built.
2. **The external evidence converges on one design rule:** *keep writes single-threaded
   and let extra agents contribute judgment, not actions.* Two further rules follow:
   - route information through a **durable, host-owned mailbox**;
   - **never make an agent poll or wait.**

   The sources that agree are Cognition (April 2026), Anthropic's January and August
   2026 posts, Cursor's scaling research, Google's scaling study, MAST, and the
   Agent-Mail / Gas Town post-mortems.
3. **Something new since the family-channel research: the two main vendor CLIs now
   support mid-turn steering.**
   - Claude Code (v2.1.224+) binds a messaging inbox even for headless `claude -p`
     sessions. Messages are read "between tool calls during an active turn". Hooks can
     also inject `additionalContext` after every tool call.
   - The Codex app-server has `turn/steer`, which appends input to an in-flight turn.
   - So "deliver to a running agent" is now a **provider capability SASE can use
     optionally**. It should not be a promise.
4. **A latent, unaudited side channel exists today [probe].**
   - Every SASE Claude agent runs Claude Code 2.1.278 in bypass mode with only
     `ScheduleWakeup` disallowed. So every one of them has `ListAgents`/`SendMessage`
     and a live inbox socket.
   - This session listed three other live SASE Claude sessions.
   - Under Claude Code's default rules, bypass-mode sessions *accept* messages from other
     bypass-mode sessions. Any SASE Claude agent, or any
     `--dangerously-skip-permissions` Claude session you run, can therefore steer
     another SASE agent mid-turn with nothing recorded in SASE.
   - It is barely used: one `SendMessage` call in ~4.8k runs since 2026-08-15. Close it
     now; it costs one flag.
5. **Recommendation, in brief:** build collaboration in three evidence-gated tiers. Each
   tier stays inside SASE's single-turn, host-owned-completion model.
   - **Tier 1 (now):** close the three loops using existing launch-time machinery:
     - a delegation reply join;
     - a cross-provider review loop;
     - better wait-output handoff;
     - closing the side channel.
   - **Tier 2:** ship the narrow durable family inbox from `family_channel_delivery`,
     with two changes:
     - the host can post into it;
     - a pending *request* can trigger a host-launched successor at turn end.
   - **Tier 3, only on observed need:** mid-turn delivery through provider hooks and
     steering, channel-wait wakeups, and sibling hazard notices for epics.
   - **Do not build:** group chat, agent-polled inboxes, A2A, or LLM supervisors.

   §8 has the full recommendation.

---

## 1. What "collaboration" means when the unit of work is a single-turn agent

The word covers six patterns. They differ in what must flow between agents, when it must
arrive, and how much the evidence says they help.

| # | Pattern | SASE workload today | What must flow | Evidence of value (§3) |
|---|---|---|---|---|
| P1 | **Independent fan-out + synthesis** | Research swarms (like this one), `%{%m:a \| %m:b}` model fan-out, best-of-N | Each worker's *finished* result → synthesizer | **Strong.** Anthropic research system (+90% over single agent). Independence avoids premature consensus |
| P2 | **Delegation with reply** | `/sase_run` helper launches; planner → child epic | Task → child; **child's answer → parent** | **Strong** (map-reduce-and-manage, orchestrator-worker) |
| P3 | **Independent verification / review** | Mentors on Patches, research critique add-on, epic land agent | Artifact → reviewer (fresh context); **findings → author** | **Strongest.** Cognition's review loop, Anthropic's skeptical evaluator, cross-model review papers |
| P4 | **Sequential continuity + human steering** | Families, pipe/monitor/gate successors, supervision boards (`sase-xs/xt/xu`) | Checkpoint → successor; **human correction → next shell** | **Moderate.** The `016` experiment shows value; volume is low |
| P5 | **Parallel writers on one codebase** | Epics (`sase bead work`): phase agents in separate workspaces + land agent | Plan → workers; landed code → dependents; *discoveries that affect siblings* | **Mixed.** Works with planner-assigned disjoint work and no peer talk; conflicts are common (§3.3) |
| P6 | **Live peer discussion** | None (no mechanism) | Free-form messages among running peers | **Weak or negative** outside exploratory search. Premature consensus, "communication purgatory", polling storms, collusion |

A seventh layer is orthogonal: **fan-out inside one provider turn** (Claude Code
subagents, Codex subagents, Antigravity `invoke_subagent`). SASE agents already use it;
this report's research used two helper subagents. It is the right tool for read-heavy
fan-out within one task, and SASE should not reinvent it. Features that depend on a
background notification arriving after the turn ends are an exception, because they are
incompatible with single-turn runs (§2.7).

The rest of this report asks, for each of P1–P6, whether SASE should add mechanism, and
which.

---

## 2. What SASE has today (verified)

**Summary:** SASE collaboration is entirely **launch-time and pull-based**.
- One agent's output reaches another only when the second agent *starts*, through
  `%wait` + template variables, `#fork`, or a family successor.
- A running agent can *pull*: `sase chat show`, `sase var get`, bead notes, artifacts.
- Nothing can push to a running agent through SASE.

### 2.1 Launch-time primitives [code]

| Primitive | Where | What the consumer receives |
|---|---|---|
| `---` multi-prompts and xprompt swarms | `docs/xprompt.md` ~3132–3490; `src/sase/agent/xprompt_swarm.py` | Parallel agents; nothing shared |
| `%wait:name`, `%wait(bead=…)`, `%wait(hood=…)` (2026-09-18, `c8c842fb3`), `%wait:@tribe`, `%wait(time=…)` | `docs/xprompt.md` ~1994–2423; runner barrier in `src/sase/axe/run_agent_wait.py` | A **pre-launch barrier**. Only a `completed` outcome releases it. The workspace is checked out *after* release, so the waiter sees landed code |
| `{{ wait.chats }}` | `src/sase/axe/run_agent_refs.py` | Transcript **paths**, not contents. For a clan, only the newest successful member's transcript |
| `{{ wait.artifacts }}` (2026-09-05, `f3b00cd9f`) | `docs/xprompt.md` ~873–887 | Metadata for artifacts the waited agents registered. Bodies must be read with `sase artifact read` |
| `{{ agents["x"].key }}` via `sase var set` | `docs/xprompt.md` ~3276–3370 | Producer variables. "A consumer that has already started will not see later writes" (`docs/xprompt.md:3330`) |
| `#fork:<agent\|family\|clan>`, `#fork(a, b)` | `src/sase/xprompts/fork.yml`; `src/sase/history/chat_fork/build.py` | Full parent transcripts, with reconcile guidance for multiple parents. `#fork:<clan>` omits reply bodies |
| `%clan`, tribes, hoods | `docs/agent_families.md`; `sase_core/src/agent_clan_tribe.rs` | Naming, grouping, wait targets. Execution-neutral |

`src/sase/xprompt/processor.py:80` defers only `fork` to launch time
(`LAUNCH_DEFERRED_XPROMPT_NAMES`). That is the single existing seam where content is
materialized after admission.

### 2.2 Sequential families [code]

- `sase pipe`, `sase monitor start … --next`, and gate shells all end the caller's turn.
  They start the next family member, which receives `#fork:<family>` plus a typed
  outcome.
- The documented way to wait on *other agents* mid-task is a monitor running
  `sase agent wait` (`docs/monitors.md:74-86`).

### 2.3 Delegation (`/sase_run`) has no reply join [code]

- The default `requester_continuation.mode = "resume_requester"` resumes the requester
  **when the LaunchApproval gate settles**. The requester gets the decision, dispatch
  status and launch results, **not the child's output**
  (`src/sase/xprompts/skills/sase_run.md:133-141`).
- Getting the answer takes a do-it-yourself chain:
  1. requester turn
  2. gate shell
  3. resumed requester, whose only job is to start a monitor
  4. monitor shell running `sase agent wait <child>`
  5. a third requester turn that reads the reply with `sase chat show`
- That is three provider turns, each re-forking the family transcript, for one
  question-and-answer.

### 2.4 Review does not reach the author [code]

- `MentorConfig` has `mentor_name`, `role` and `focus_areas`, and **no model or provider
  field** (`src/sase/config/mentor.py`). Mentors run with `model_tier="large"`
  (`src/sase/workflows/mentor.py:336`).
- Findings go to `~/.sase/mentors/`. A human accepts them in the TUI, and accepting
  launches a *new* `make_mentor_changes` agent.
- So "Codex reviews what Claude wrote" is not a policy you can express, and the author
  agent never sees the review.

### 2.5 Parallel writers (epics) [code]

- `sase bead work` compiles a Kahn-wave DAG in core (`sase_core/src/bead/work.rs`). It
  launches one agent per phase in its own numbered workspace, with `%wait` edges, plus a
  land agent that waits on all of them.
- Phase workers must not create beads. They record `PROPOSED FOLLOW-UP:` notes, which
  the land agent collects and triages (`src/sase/default_config.yml:1805, 1882`).
- Conflicts are handled at commit time: the host-owned finalizer merges, and on conflict
  gets one automated repair turn.
- There is no file-ownership declaration and no lease. Same-wave siblings cannot see
  each other's discoveries.

### 2.6 The message-board experiment [code, probe]

- `sase-xs`, `sase-xt` and `sase-xu` are open `task(memory)` beads used as hourly
  supervision batons (2026-09-06/07).
- The `sase-xu` description calls itself "a proof of concept for whether a dedicated
  message-board bead type would be useful". It uses append-only attributed notes "as the
  baton between successors".
- The `family_channel_delivery` synthesis has already mined this experiment in depth. It
  was useful for continuity, it was not a lifecycle fit for beads, the payloads were
  bloated, and the chain died at a LaunchApproval handoff. **No channel code has
  shipped.** There are zero hits for `mailbox`, `message_bus`, `SendMessage` or
  `family channel` in `src/sase`, `sase_core` or `docs/`.

### 2.7 The latent Claude Code messaging side channel [probe, code]

**What SASE passes to Claude** (`src/sase/llm_provider/claude.py:412-427`):
- `claude -p --verbose --output-format stream-json --dangerously-skip-permissions --append-system-prompt <single-turn directive> --disallowedTools ScheduleWakeup --session-id|--resume <uuid>`
- `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (`claude.py:527`).
- It does **not** pass `--bare`, `crossSessionInbound`, or any deny rule for `SendMessage`
  or `ListAgents`.

**What I observed in this session (Claude Code 2.1.278):**
- `CLAUDE_CODE_MESSAGING_SOCKET=/run/user/1000/cc-socks/<pid>.sock` is exported to Bash.
- `ListAgents` returned three other live SASE Claude sessions on athena. They carry
  auto-generated names such as `sase-34-1a`, which are not their SASE agent names.

**What the Claude Code docs say [V]:**
- "Claude Code binds an inbox socket for a `claude -p` session like an interactive one."
- "The receiving Claude reads the message between tool calls during an active turn."
- For a receiving session that bypasses permission prompts, Claude Code "delivers one
  only when the sending session identifies itself as also bypassing."

All SASE Claude agents bypass. So SASE Claude agents can steer each other mid-turn, and
so can any `--dangerously-skip-permissions` Claude session you run by hand. None of it
reaches SASE's chats, artifacts or audit trail.

**Usage:** one `SendMessage` tool call appears in the ~4,778 `tool_calls.jsonl` run logs
written since 2026-08-15 (2026-08-27). It is a latent risk, not an active practice.
Claude Code's own guardrails still apply (a message "never counts as your consent" and
cannot change configuration), but with prompts bypassed there is nothing left to gate
the actions the message asks for.

A related single-turn hazard [unverified]: vendor-native features that report
completion by *background notification* cannot deliver in a single-turn run.
`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` covers background shell tasks. I did not check
whether it also covers the Claude Code workflow runner or background subagents.

---

## 3. What the outside world learned (2025–2026)

### 3.1 Vendor mechanisms

| Vendor surface | How agents exchange information | Durable? | Who wakes the recipient |
|---|---|---|---|
| **Claude Code subagents** [V] | Subagent returns a summary. Named subagents are addressable, and `SendMessage` resumes a finished one | Within session | Host (tool result) |
| **Claude Code agent teams** [V] (experimental, Feb 2026) | Shared task list with file-locked claims. Per-agent JSON inbox files, push delivery, idle notification to the lead | Tasks yes, team no (`/resume` does not restore teammates) | Host. **Never spawned in `-p` mode**; teammates share one worktree, so "two teammates editing the same file leads to overwrites" |
| **Claude Code cross-session messaging** [V, probe] (v2.1.224+) | `ListAgents`/`SendMessage` over a per-session Unix socket | No (inbox holds ≤100 messages; queue ≤50) | Host. Between tool calls if busy; a new turn if idle; `notify_when_idle` one-shot subscription. Loop throttling and dedupe built in |
| **Claude Code hooks** [V] | `PostToolUse` can return `additionalContext`; `Stop` can block the end of a turn | n/a | Host, at tool boundaries |
| **Claude Code dynamic workflows** [V] | A JS script runs `agent()` / `parallel()` / `pipeline()`; intermediate results stay in script variables | Deterministic replay | Script |
| **Codex subagents** [V] | Custom agents in `.codex/agents/`, results merged into one response. v2 tools include `spawn_agent`, `send_message`, `followup_task`, `wait_agent` [S] | Within session | Host |
| **Codex app-server** [V] | `turn/steer` "append[s] more user input to the active in-flight turn" at the next tool boundary. `thread/resume` reopens a thread | Thread store | Client |
| **Antigravity 2.0** [V] | `invoke_subagent` with clean context. Messaging an idle subagent "automatically re-awakens it" | — | Host |
| **Cursor** [V] | Agents window runs many agents. Research harness: recursive planners → workers that "don't communicate with any other planners or workers" | — | Planner |
| **Claude Managed Agents** [V] (beta) | A coordinator plus a roster of up to 20 agents, one level of delegation; persistent threads | Yes | Platform |
| **Devin** [V] | "Manager Devin" coordinates child Devins through an internal MCP | — | Manager |

**Implication for SASE:** every major vendor now handles multi-agent work *within one
session*, and the two SASE uses most (Claude, Codex) now expose **tool-boundary
injection**. None of them offers a durable, cross-vendor, cross-session work ledger with
host-owned landing. That remains SASE's layer.

### 3.2 Coordination infrastructure and its post-mortems

- **MCP Agent Mail** [V/S]:
  - Design:
    - memorable identities;
    - threads keyed to bead IDs;
    - `ack_required`;
    - Git + SQLite storage;
    - **advisory file reservations with a TTL**;
    - an optional pre-commit guard;
    - broadcast deliberately *not* the default, because agents "will spam every peer".
  - Delivery is **pull**, and the top complaint was "agents forget to check their
    messages". The fix was hooks that remind them.
  - The Flywheel guide adds more failure modes:
    - thundering herds when agents wake together;
    - "communication purgatory", where agents coordinate but never execute;
    - duplicate claims;
    - strategic drift.
- **Gas Town → Gas City → Wheelhouse** (Yegge) [V/S]:
  - Gas Town needed tmux "nudges" to wake Claude sessions and layered LLM watchdogs. An
    early Deacon "went feral" and killed workers.
  - DoltHub's hour-long trial cost ~$100 and produced 0 of 4 acceptable PRs.
  - Gas City moved patrol into the deterministic orchestrator, because "most relay work
    needs no LLM". Wheelhouse's motto is "crons watch, models act", with 45+ non-model
    systems.
  - Fuel became the binding constraint: one $200 Max seat drained every 2–4 hours.
- **Orca** [V]:
  - A durable FIFO inbox with typed messages: `dispatch`, `worker_done`, `escalation`,
    `question`.
  - Completion must carry both `taskId` and `dispatchId`, so a stale worker cannot
    complete newer work.
  - Issue #16903 shows the failure mode of *prompt-based* completion signalling. An
    injected preamble told workers to skip `worker_done`, and coordinators waited
    forever.
- **Maestro group chat** [V]: a moderator agent routes everything, and "participants do
  not see each other's replies automatically". It is not a free-for-all.
- **Protocols** [V]:
  - **A2A** reached v1.0 in 2026 with 150+ organizations, but it targets enterprise
    remote-agent interop. No source shows the coding CLIs adopting it.
  - **ACP** is client-to-agent, not agent-to-agent.
  - **MCP Tasks** (SEP-1686) explains why agent-driven polling fails: it "relies on
    prompt engineering to steer an agent to poll at all". An agent "calls the tool once
    before ending its conversation turn, claiming to be 'waiting'". SASE hit exactly this
    failure and fixed it with single-turn directives.

### 3.3 Research: when collaboration helps and when it hurts

| Finding | Source | Consequence for SASE |
|---|---|---|
| Orchestrator-worker research beat a single agent by 90.2%, at ~15× chat tokens. A poor fit where agents "share the same context or involve many dependencies"; "most coding tasks involve fewer truly parallelizable tasks" | Anthropic, Jun 2025 [V] | P1 is worth it; P5 is not free |
| Decompose by **context**, not by phase. Planner → implementer → tester chains are a "telephone game". Verification subagents work because the verifier doesn't need the implementer's context. Multi-agent typically costs 3–10× tokens | Anthropic, Jan 2026 [V] | Invest in P3; don't build role pipelines |
| "Multi-agent systems work best today when writes stay single-threaded and the additional agents contribute intelligence rather than actions." Review works best when coder and reviewer "do not share any context beforehand" (~2 bugs per PR, 58% severe). "The open problems are all communication problems": agents fail to surface discoveries that affect siblings | Cognition, Apr 2026 [V] | P3 first. P5 sibling communication is unsolved, so be cautious |
| Forum-coordinated swarm found 266 vulnerabilities vs 21 for independent agents (27M vs 6.5M tokens). But results were "largely complementary", and 18 of 30 agents chose the same branch name. Polling daemons generated "2.4 million job requests and only 117 jobs accepted". In hidden-profile tasks groups scored 17–36% vs near 100% solo. Collaboration quality varied sharply by model. Agents colluded when given a back-channel | Anthropic Frontier Red Team, Aug 2026 [V] | P6 can help open-ended *search*, but it is model-dependent, costly and risky. Never let agents poll. Keep synthesis independent |
| Independent agents amplify errors 17.2×; centralized coordination holds that to 4.4×. On sequential planning, every multi-agent variant lost 39–70%. Coordination stops helping once the single-agent baseline exceeds ~45% | Google Research, "Towards a Science of Scaling Agent Systems", Jan 2026 (v3 Apr 2026) [V] | A central verifier or synthesizer is load-bearing. Don't fan out sequential work |
| 14 failure modes across system design, inter-agent misalignment and verification; gains "often minimal" | MAST (Cemri et al.) [V] | Verification is where multi-agent systems break |
| Debate ≈ majority voting; model diversity is the most reliable lever | "Stop Overvaluing Multi-Agent Debate" [V] | Diversity across providers beats rounds of discussion |
| Claude reviewing Codex raised the pass rate from 71.6% to 89.7%; Codex reviewing Claude *lowered* it from 91.4% to 82.8% | Xiang et al., Jul 2026 [V] | Cross-vendor review helps, but **asymmetrically**. Make the reviewer's model configurable and measure each pairing |
| Fresh-session review beat same-session review (F1 28.6 vs 24.6) | Cross-Context Review, Mar 2026 [V] | Reviewers need fresh context. SASE mentors already have it |
| Cross-agent PR pairs conflict 41.7% of the time vs 19.8% within one agent. 27.7% of 107k agent PRs conflict | Xu et al. Jul 2026; AgenticFlict [V] | P5 needs integration discipline more than chat |
| Hard locks collapsed 20 agents to the throughput of 2–3; optimistic concurrency made agents "risk-averse". What worked: planners + non-communicating workers + a judge. "Many of our improvements came from removing complexity" | Cursor, Jan–Feb 2026 [V] | No lock service. Planner-assigned disjoint work plus an integrator |
| "The runtime informs, the agent repairs": advisory ordering beat locks and OCC (45 → 63 of 71 at 0.86× cost) | CoAgent, Jun 2026 [V] | If P5 needs anything, it's advisory notices, not locks |
| Self-evaluation "confidently prais[es] the work"; a separate skeptical evaluator is easier to tune | Anthropic harness design, Mar 2026 [V] | P3 again |

### 3.4 Distilled lessons for a single-turn, headless orchestrator

1. **Collaborate through judgment, not concurrent writes.** Reviewers, critics,
   synthesizers and advisors are the proven wins.
2. **Independence before aggregation.** Discussion buries unique facts and converges
   early. Researchers should not see each other before synthesis, which SASE's swarm
   already enforces.
3. **The host owns delivery and wake-up.** Agents forget to poll, poll too much, or end
   their turn "waiting". Every system that survived moved delivery into deterministic
   infrastructure.
4. **Durable mailbox, not live chat.** Everything that survives restarts persists
   messages outside the agent.
5. **Completion is a typed, idempotent, host-verified event**, not a message an agent
   remembers to send (Orca #16903). SASE already has this in `done.json` and finalizers.
6. **Pick the injection boundary deliberately.** There are three: launch, end of turn,
   and tool boundaries. They carry different guarantees.
7. **Budget every wake.** Each delivery to an idle agent re-sends its context, and
   multi-agent systems multiply cost 3–20×. SASE is limited by subscription usage
   windows, not by wall-clock time.
8. **Treat peer messages as untrusted data** with host-recorded provenance. They are
   never authority.
9. **Measure per model.** Collaboration quality and cross-review benefit vary by model
   and by direction.
10. **Keep the harness thin.** Gas Town broke on a model change, and Cursor improved by
    removing complexity.

---

## 4. Constraints specific to SASE

| Constraint | Source | What it rules in or out |
|---|---|---|
| Agents are single-turn; continuation is mechanical | `decisions:single-turn-agents` | No long-lived listening agents. Delivery happens at launch, at tool boundaries (provider-dependent), or by host-launched successors |
| Gates never block | `decisions:gates-never-block` | An agent may not wait for a reply in place. A request/reply exchange ends one turn and resumes another |
| Completion is host-owned | `decisions:host-owned-completion` | "Done" and "replied" are host facts derived from `done.json`, finalizers and artifacts, not from agent claims |
| Rust core owns shared behavior | Core memory, `decisions:rust-core-required` | Mailbox, cursors, receipts and selection belong in `sase-core`; Python is the adapter and TUI |
| No mechanism before its corpus | `decisions:corpus-before-mechanism` | Build in tiers gated on observed use; don't ship a forum on speculation |
| Multi-provider parity | Multi-CLI report §7.2 | Any per-provider fast path, such as mid-turn steering, must degrade gracefully to a portable baseline |
| Cross a user boundary as an artifact, never as a process | `sase_collaboration_architecture.md` §1.3 | The mailbox is local, process-plane-adjacent state. It publishes history outward; it does not sync live state across users |
| Capacity is subscription-bound | Usage-window work; Wheelhouse's "fuel" lesson | Delivery must never create turns just to carry low-value information |

---

## 5. Options evaluated

| Option | What it would be | Verdict | Why |
|---|---|---|---|
| **A. Adopt Claude Code native messaging or agent teams** as the SASE collaboration layer | Name sessions after SASE agents, let agents `SendMessage` | **Reject as the layer; use only as a transport** (Tier 3) | Claude-only. Not durable (bounded in-memory queue). Invisible to SASE's audit, artifacts and TUI. Teams are never spawned in `-p` mode. Bypass-to-bypass delivery is an injection path |
| **B. Adopt MCP Agent Mail** | Run the MCP server; agents call `send_message` / `fetch_inbox` | **Reject; borrow ideas** | SASE has no MCP configuration anywhere (multi-CLI report). Delivery is pull-based ("agents forget"), and its identity model and store would duplicate beads and artifacts. Worth borrowing: `ack_required`, threads keyed to beads, advisory TTL reservations, no default broadcast |
| **C. A2A** | Agents as remote HTTP services with Agent Cards | **Reject** | SASE agents are local, single-turn processes, and no coding CLI speaks A2A |
| **D. Beads as the board** (status quo experiment) | Notes on an open `task(memory)` bead | **Keep as a fallback only** | It works at ~9 messages over 3 hours. But the lifecycle, schema and payload friction is documented in `sase-xu`, and there are no cursors or receipts |
| **E. A dedicated `message` bead type** | New issue type | **Reject** | Same conclusion as `family_channel_delivery`: it couples messaging to the work lifecycle and still provides no delivery |
| **F. Close the three loops with existing launch-time machinery** | Reply join, review routing, better wait output, side-channel closure | **Do first (Tier 1)** | The value evidence is strongest, no new store is needed, and it touches only existing seams (§7.2) |
| **G. A narrow durable family inbox in sase-core** | The `family_channel_delivery` design | **Do second (Tier 2), with the amendments in §6** | Solves P4 steering and continuity; the host becomes a producer |
| **H. Mid-turn delivery via provider hooks and steering** | Claude `PostToolUse` `additionalContext`; Codex `turn/steer` | **Tier 3, capability-gated** | Real and verified, but provider-specific, and "urgent mid-turn correction" has little observed demand so far |
| **I. Moderated group chat or forum** (Maestro / Anthropic swarm style) | Agents post and read a shared timeline while running | **Do not build; allow a scripted experiment only** | Weak or negative evidence outside open-ended search. Costly, model-dependent, prone to premature consensus and collusion |
| **J. File leases or a lock service for epics** | Agent-Mail-style reservations | **Do not build now** | Locks collapsed Cursor's throughput. SASE workspaces are isolated clones and the finalizer already merges. A deterministic *overlap warning* at plan time gets most of the benefit (§7.4) |
| **K. An LLM supervisor or patrol agent** | A long-running "mayor" or "deacon" | **Reject** | Gas Town's feral watchdogs, and Gas City and Wheelhouse moved patrol to deterministic code. SASE's scheduler jobs (`wait_checks`, `bead_claim_checks`) are the right shape |

---

## 6. Building on `family_channel_delivery`: what I keep and what I change

I agree with its core:
- immutable envelopes;
- a monotonic sequence assigned at commit, never a timestamp cursor;
- family-owned subscriber progress;
- the pending → included → acknowledged → answered states;
- selection after admission;
- an aggregate prompt budget that never acknowledges omitted ranges;
- SQLite outside workspaces, with deliberate durability settings;
- provenance separate from claimed author;
- no automatic wake on every post.

It is the right *store*. I change five things.

1. **Sequence the review and delegation loops ahead of the channel.**
   - The channel's own evidence is one supervision experiment at very low volume.
   - The reply join and the review loop solve problems every SASE user hits: every
     `/sase_run` helper, and every mentor finding that never reaches the author.
   - External evidence for them is the strongest in the survey.
   - They need no new store, because they extend the requester continuation and mentor
     plumbing that already exists.
2. **The host is a first-class producer.** Human and agent posts are not the only ones
   that matter. Once the inbox exists, the host should also post a typed `reply` when a
   delegated child completes, and a `review` when a cross-provider review finishes.
   - Tier 1 implements both loops without the inbox. Tier 2 then re-platforms them as
     host posts into the requester's or author's family inbox.
   - That gives one timeline per family covering "what happened to me while I was not
     running", with provenance that cannot be forged, because the host wrote it.
3. **Add an end-of-turn delivery point that respects single-turn semantics.** If a
   subscribed family has an unacknowledged `request` or `correction` when its shell
   finishes and it scheduled no other continuation, the host may launch **one** ordinary
   successor carrying the batch.
   - The launch obeys normal admission and deduplication and has a per-family budget.
     This closes the "pending message but the family is dead" gap without agent polling.
   - `info` and `checkpoint` messages never trigger this; they wait for the next shell
     that happens anyway.
   - Same-session provider resume is a later *optimization*, and it would need an
     amendment to `decisions:single-turn-agents`. `claude.py`'s wait-continuation
     `--resume` loop is a precedent, but it is a bounded repair, not a delivery channel.
4. **Promote mid-turn delivery from "never promise" to "optional capability tier".** The
   synthesis was right not to *promise* it. What has changed is that it is now
   implementable for the two main providers (§3.1). Keep it behind a per-provider
   capability flag. Deliver only `correction` and `request` kinds mid-turn, and record
   inclusion the same way as launch-time batches.
5. **Close the unaudited native side channel regardless.** The synthesis did not know
   about §2.7. Whatever SASE builds, peer steering should go through the SASE log, not
   through Claude's socket.

---

## 7. Recommended architecture

### 7.1 Five rules

1. **Collaboration is information flowing between turns, and the host carries it.**
   Agents never poll, never wait, and never wake each other directly.
2. **Writes stay single-threaded per workspace.** Parallel writers are coordinated by
   the planner and integrator (the DAG, the land agent and the finalizer), not by peer
   messages.
3. **Independent judgment is the main product.** Fan-out stays independent until
   synthesis, and review uses fresh context and preferably a different provider.
4. **Everything is typed, attributed and durable.** Replies, reviews and messages are
   host-recorded events with provenance. Prompt text is never proof of delivery,
   receipt or authority.
5. **Every tier ships behind a flag with adoption metrics**, and is removed if its
   metrics don't move.

### 7.2 Tier 1: close the three loops (build now, no new store)

**1a. Delegation reply join.**
- Add a requester-continuation mode, e.g. `resume_requester_on_completion`. The
  requester's successor launches when the delegated child *settles*, not when the gate
  settles, and receives a bounded result bundle:
  - outcome;
  - the reply body, capped with an artifact pointer;
  - registered artifacts;
  - `sase var` outputs.
- This removes today's three-turn chain (§2.3). The mechanics already exist:
  - the gate shell's typed follow-up;
  - `%wait` on the child;
  - `wait.artifacts` / `agents[...]` rendering after admission.
- Failure semantics follow `%wait`. A failed child resumes the requester with the
  failure, rather than leaving it parked as a bare `%wait` does today.

**1b. Cross-provider review loop.**
- Add `model:` (an alias or pool) to `MentorConfig`, plus a policy knob such as
  `reviewer_provider: different_from_author`. This lets "a different vendor reviews this
  Patch" be the default for chosen profiles.
- Route accepted findings back to the **author family** as a typed follow-up (a new
  family shell with `#fork:<author>` plus the findings) rather than to an unrelated
  `make_mentor_changes` agent, whenever the author family is resumable. Keep the human
  accept step as the default gate, with `%auto` as the opt-in.
- Bound it to N rounds with a judge (§3.3: self-evaluation is lenient; reviewers need
  fresh context).
- Record the author and reviewer provider pair on every review, so the
  asymmetric-benefit question (Xiang et al.) can be answered with SASE's own data.

**1c. Wait-output fidelity.**
- Make `wait.replies` available as bounded reply *bodies*, not only transcript paths.
- For clan waits, return every member rather than only the newest.
- Make `#fork:<clan>` optionally include reply bodies.
- Together these make P1 synthesis and P5 land agents less dependent on prompt
  conventions.

**1d. Close the side channel.**
- Launch SASE Claude agents with `crossSessionInbound: "refuse"` through `--settings`,
  and add `ListAgents` to `--disallowedTools`. `SendMessage` can stay for in-session
  subagents; cross-session sends will then be refused by other SASE agents.
- Revisit this only if Tier 3 adopts the socket as a transport, and then only with
  host-authenticated posts.
- *This finding came up during research and needs a task bead.* I did not file one, to
  avoid duplicate beads across swarm members. The lead should file it through
  `/sase_new_task`.

**1e. Plan-time overlap warning for epics (optional, cheap).**
- Let phase beads declare the paths they expect to touch, and have `sase bead work` warn
  when two same-wave phases overlap.
- This is the "runtime informs, agent repairs" idea from CoAgent, applied
  deterministically before launch. It adds no locks.

### 7.3 Tier 2: a durable family inbox (build next, trial per the synthesis criteria)

Implement the `family_channel_delivery` vertical slice in `sase-core`, with these
specifics.

**Addresses:**
- `family:<id>` — every sase agent's implicit inbox, created lazily on first post.
- `channel:<name>` — explicit shared boards with opt-in family subscriptions.
- Clan and tribe addressing is **deferred** until P5 evidence exists (§7.4).

**Producers**, each with its provenance recorded by the host:
- **human**: TUI, Telegram, CLI with a trusted ingress;
- **agent**: attributed to the running shell's identity, never a free-text author;
- **host**: replies from 1a, reviews from 1b, gate and monitor outcomes.

**Kinds:** `info`, `request`, `checkpoint`, `reply`, `correction`. Delivery policy is
keyed by kind:

| Kind | Launch-time injection | End-of-turn successor (§6.3) | Mid-turn (Tier 3) |
|---|---|---|---|
| `info`, `checkpoint` | yes (within budget) | no | no |
| `request`, `correction` | yes | yes, once, with a family budget | if the provider is capable |
| `reply` (host) | yes | yes, if the family registered interest (1a) | no |

**Delivery points:**
- **Launch:** the batch is selected after admission, next to the `fork` deferred seam
  (`processor.py:80`).
- **End of turn:** the runner or finalizer checks once when the shell ends.
- **Voluntary read:** a finite `read` command documented in a skill.

**States:** pending → included (exact IDs plus the prompt artifact) → acknowledged (an
explicit agent action, recorded through the final declaration or a CLI) → answered (a
linked `reply`).

**Budget:** an aggregate prompt budget across the family's subscriptions, with an
overflow notice. Omitted ranges are never acknowledged.

**Surfaces:**
- one TUI timeline per family: pending, included, acknowledged, publication lag;
- `@channel:` / `@family:` artifact refs for audited reads;
- the CLI spelling follows `cli_rules.md`.

**Store:** SQLite outside workspaces (per the synthesis), exposed through the artifact
system, with history published asynchronously.

### 7.4 Tier 3: evidence-gated extensions

Build these only when the Tier 2 metrics show the need.

- **Mid-turn delivery.** Two provider paths:
  - *Claude:* a SASE-installed `PostToolUse` hook (passed through `--settings`) calls
    `sase … hook` and returns pending `correction`/`request` messages as
    `additionalContext`, recording inclusion.
    - This is preferred over the messaging socket: it is SASE-controlled, works with
      inbound messaging refused, and needs no socket trust.
  - *Codex:* only if SASE moves Codex to the app-server (which the multi-CLI report also
    wants for native resume) can it use `turn/steer`.
  - Other providers fall back to end-of-turn delivery.
- **Channel-wait wakeups.** `sase monitor start -- sase <channel> wait …` ends on a new
  post or a timeout, then launches one successor. Register first, then recheck, to close
  the lost-wakeup race (as in the synthesis).
- **Sibling hazard notices for epics.** Phase workers post `info` with an "affects
  interface X" tag to the epic's channel. Delivery goes to the **land agent and later
  dependents only**, not to running siblings, following Cursor: workers don't talk; the
  integrator routes.
  - Trigger this only if land-agent reports show cross-phase surprises that plan-time
    overlap warnings (1e) missed.
- **Scripted deliberation experiment.** Anthropic's forum result shows value for
  open-ended search, so it may be worth *one* trial as an xprompt: bounded rounds over a
  channel, a moderator, fixed budgets, and different models. It stays an experiment, not
  a primitive.

### 7.5 What not to build

- Free-form group chat, or agents subscribing each other.
- Any agent-side polling loop or "check your inbox" instruction.
- A2A endpoints.
- LLM watchdogs.
- A lock service.
- A `message` bead type.
- Native Claude teams or socket messaging as the system of record.
- Broadcast by default.

### 7.6 Metrics and kill criteria

| Tier | Keep investing if… | Stop or remove if… |
|---|---|---|
| 1a reply join | Delegation round-trips drop from about 3 requester turns to 1, and helper results are consumed without `sase chat show` workarounds | Nobody uses `/sase_run` for helpers that return answers |
| 1b review loop | Findings per Patch and the accept rate hold up; post-land fixes drop; the provider-pair data shows which directions help | Accept rate is low, or cross-provider pairs underperform same-provider ones |
| 2 inbox | Missed human corrections go to 0; manual reminders drop; delivered messages change the next shell's decisions; prompt bytes stay within budget | Messages rarely change decisions, or receipts add nothing over bead notes |
| 3 mid-turn | Measured latency pain in steering, e.g. corrections arriving mid-shell that would have prevented wasted work | Never triggered in a month of Tier 2 use |

---

## 8. Recommended solution

**Build multi-agent collaboration as host-carried information between single-turn
agents, not as agents talking to each other.** Concretely, in this order:

1. **Now (Tier 1, no new infrastructure):**
   - **(a)** a `/sase_run` continuation mode that resumes the requester when the
     delegated child *completes*, with a bounded result bundle;
   - **(b)** cross-provider mentors (a `model`/pool field plus a
     `different_from_author` policy), with accepted findings routed back to the author
     family and each review's provider pair recorded;
   - **(c)** reply bodies and full clan coverage in `%wait` context;
   - **(d)** close Claude Code's unaudited cross-session channel for SASE agents with
     `crossSessionInbound: refuse` and a `ListAgents` deny;
   - optionally **(e)** plan-time overlap warnings for same-wave epic phases.

   These are the loops with the strongest external evidence (independent, fresh-context,
   cross-vendor review; manager-worker with results returned). They fix real friction in
   SASE today.
2. **Next (Tier 2):** implement the narrow durable **family inbox** from
   `family_channel_delivery` in `sase-core`, with two amendments:
   - the **host posts** replies and reviews into it;
   - a pending `request` or `correction` can trigger **one host-launched successor** at
     turn end.

   Trial it against that report's adoption criteria.
3. **Only on evidence (Tier 3):**
   - mid-turn delivery through provider hooks and steering: a Claude `PostToolUse`
     `additionalContext` hook, and Codex `turn/steer` if Codex moves to the app-server;
   - channel-wait wakeups;
   - epic hazard notices routed to the integrator.
4. **Never:** peer group chat, agent polling, A2A, LLM supervisors, lock services, or a
   message bead type.

This keeps SASE's differentiators intact (single-turn agents, host-owned completion,
provider-neutral landing, durable state). It spends tokens only where collaboration is
known to pay: independent judgment and returned results. And it leaves room for live
steering once the vendors' tool-boundary injection proves worth its complexity.

---

## 9. Method and caveats

**Method.**
- I read the two assigned reports and the collaboration-architecture report through
  `sase artifact read`, and the reference memory through `sase memory read` (glossary
  terms plus four decision records).
- A code sweep of `src/sase`, `docs/` and `sase-core` was delegated to a read-only
  helper. I re-checked these first-hand:
  - `claude.py` args and env;
  - the `sase_run.md` continuation semantics;
  - `docs/monitors.md:74-86`;
  - `MentorConfig`;
  - `docs/xprompt.md:3330`;
  - `processor.py:80`;
  - the `%dispatch` limits;
  - the `PROPOSED FOLLOW-UP` config;
  - the `sase-xu` description.
- A web survey was delegated to a helper, which was told not to fetch GitHub file
  contents. I re-fetched these myself:
  - Claude Code cross-session messaging;
  - Claude Code hooks;
  - Anthropic's Aug 2026 multiagent-systems post;
  - Cognition's Apr 2026 post;
  - Codex app-server docs.
- Live probes: this session's env vars and `ListAgents`; a grep of `~/.sase` run logs
  for `SendMessage`.

**Caveats.**
- The `SendMessage` count covers `tool_calls.jsonl` files modified since 2026-08-15. It
  shows rarity, not that use is impossible.
- Some external numbers are self-reported by vendors or authors (Agent Mail scale,
  Cursor throughput).
- Codex v2 tool names, and whether Codex hooks can inject context, are [S] or
  unverified.
- Whether `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` also covers Claude Code workflows and
  background subagents is unverified.
- I did not read the other swarm researchers' reports or transcripts.

## 10. Sources

**SASE (repo-relative, `c6807d24c`):**
- `src/sase/llm_provider/claude.py` (412–427, 527)
- `src/sase/xprompts/skills/sase_run.md` (133–165)
- `docs/monitors.md` (74–86)
- `docs/xprompt.md` (873–887, 1994–2423, 2155–2163, 3132–3490, 3276–3370)
- `src/sase/xprompt/processor.py:80`
- `src/sase/config/mentor.py`, `src/sase/workflows/mentor.py:336`
- `src/sase/default_config.yml` (1790–1884)
- `src/sase/axe/run_agent_wait.py`, `run_agent_refs.py`
- `src/sase/history/chat_fork/`
- `docs/agent_families.md`
- `sase-core`: `crates/sase_core/src/bead/work.rs`, `agent_clan_tribe.rs`
- Beads `sase-xs`, `sase-xt`, `sase-xu`

**Prior research (read through `sase artifact read`):**
- `research:202609/multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md`
- `research:202609/family_channel_delivery/family_channel_delivery.md`
- `research:202609/sase_collaboration_architecture.md`

**Vendors:**
- Claude Code:
  - https://code.claude.com/docs/en/cross-session-messaging
  - https://code.claude.com/docs/en/hooks
  - https://code.claude.com/docs/en/agent-teams
  - https://code.claude.com/docs/en/sub-agents
  - https://code.claude.com/docs/en/agents
  - https://code.claude.com/docs/en/workflows
  - https://code.claude.com/docs/en/costs
- Managed Agents: https://platform.claude.com/docs/en/managed-agents/multiagent-orchestration
- Codex:
  - https://learn.chatgpt.com/docs/app-server (`turn/steer`, `thread/resume`)
  - https://learn.chatgpt.com/docs/agent-configuration/subagents
  - https://codex.danielvaughan.com/2026/04/11/codex-cli-multi-agent-orchestration-v2-complete-guide/ [S]
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/multi_agent/
- Antigravity:
  - https://antigravity.google/docs/subagents/
  - https://antigravity.google/blog/google-io-2026
- Cursor:
  - https://cursor.com/blog/scaling-agents
  - https://cursor.com/blog/self-driving-codebases
  - https://cursor.com/blog/cursor-3
- Devin: https://cognition.com/blog/devin-fusion
- GitHub Agent HQ: https://github.blog/news-insights/company-news/pick-your-agent-use-claude-and-codex-on-agent-hq/

**Coordination infrastructure:**
- Agent Mail:
  - https://mcpagentmail.com/
  - https://agent-flywheel.com/complete-guide
- Gas Town, Gas City and Wheelhouse:
  - https://yegge.ai/essays/the-shape-of-things-to-come/
  - https://yegge.ai/essays/seats-and-sunsets/
  - https://docs.gascity.com/getting-started/coming-from-gastown
  - https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/
  - https://maggieappleton.com/gastown
- Orca:
  - https://www.onorca.dev/docs/cli/orchestration
  - https://github.com/stablyai/orca/issues/16903
- Maestro: https://docs.runmaestro.ai/group-chat
- MCP Tasks: https://modelcontextprotocol.io/seps/1686-tasks
- A2A: https://opensource.googleblog.com/2026/04/a-year-of-open-collaboration-celebrating-the-anniversary-of-a2a.html
- ACP: https://zed.dev/acp

**Evidence:**
- Anthropic:
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
  - https://www.anthropic.com/research/multiagent-systems
  - https://www.anthropic.com/engineering/harness-design-long-running-apps
  - https://www.anthropic.com/engineering/building-c-compiler
- Cognition:
  - https://cognition.com/blog/dont-build-multi-agents
  - https://cognition.com/blog/multi-agents-working
- Google: https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/ and https://arxiv.org/abs/2512.08296
- MAST: https://arxiv.org/abs/2503.13657
- Debate: https://arxiv.org/abs/2502.08788
- Cross-model review: https://arxiv.org/abs/2607.21656
- Cross-context review: https://arxiv.org/abs/2603.12123
- Merge conflicts: https://arxiv.org/abs/2604.03551 and https://arxiv.org/abs/2607.04697
- CoAgent: https://arxiv.org/abs/2606.15376
- Blackboard: https://arxiv.org/abs/2510.01285
