# Multi-Agent Collaboration for SASE Agents: What to Build, and in What Order

- **Type:** consolidated research report (lead synthesis)
- **Date:** 2026-09-22
- **Question:** What is the best way to implement collaboration *between* SASE agents?
  The report ends with a recommended solution.
- **Inputs:** three independent researcher reports:
  - [cld](multi_agent_collaboration_strategy__cld.md): six-pattern taxonomy, the
    external evidence survey, and the discovery of Claude Code's native messaging
    side channel.
  - [mus](multi_agent_collaboration_strategy__mus.md): a compact options matrix and
    a narrow first-release scope.
  - [gem](multi_agent_collaboration_strategy__gem.md): a four-layer blueprint with a
    SQLite schema and an acceptance matrix.
- **Context read first** (through `sase artifact read`):
  - [`family_channel_delivery`](../family_channel_delivery/family_channel_delivery.md)
    (2026-09-07)
  - [`multi_cli_orchestration_vs_sase`](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
    (2026-09-21)
- **The lead's own work** focused on where the reports disagreed or relied on thin
  evidence:
  - a **usage corpus** from athena's run archive (§3.2). None of the reports measured
    what SASE agents actually do today.
  - first-hand code checks at sase `8acb66c44`;
  - a live probe of this session's Claude Code messaging surface;
  - primary-source checks of the Claude Code messaging docs, Codex `turn/steer`, the
    cross-model review paper, and gem's file-lease claim.

---

## 1. Bottom line

1. **Build collaboration as information the host carries between single-turn agents.
   Agents should not talk to each other live.** All three reports agree on this, and
   the evidence supports it:
   - SASE's single-turn and host-owned-completion invariants;
   - the external record: Cognition, Anthropic, Cursor, Google's scaling study, and the
     Agent Mail and Gas Town post-mortems;
   - how SASE agents actually collaborate today.
2. **Today, SASE collaboration happens overwhelmingly at launch time.** In about five
   weeks of runs on athena:
   - **44%** of prompts use `%wait`, 22% use `#fork`, and 8% declare a clan;
   - **32%** of runs write bead notes;
   - delegation through `/sase_run` appears in **0.5%** of runs;
   - agents used Claude's native `SendMessage` **once**;
   - no mentor has completed since 2026-08-09.

   So the first investments belong on the `%wait`/`#fork`/epic path, where the corpus
   is. New messaging machinery comes later.
3. **Stage 0: close two hygiene gaps now, whatever else you decide.**
   - Every SASE Claude agent can be steered mid-turn by any other bypass-mode Claude
     session, with nothing recorded in SASE. cld found this and the lead re-verified it.
   - Several vendor-native async tools are exposed even though their results can never
     arrive in a single-turn run.
   - Both fixes are launch-flag changes.
4. **Stage 1: close three information loops on existing seams, with no new store.**
   - a **cross-vendor review** constraint in core model routing, applied first where
     review actually runs (epic land agents, research critique) rather than to the
     dormant mentors;
   - **bounded reply bodies and outcomes in `%wait` context**;
   - a **delegation reply join** for `/sase_run`.
5. **Stage 2: then build the narrow durable family inbox from
   `family_channel_delivery`**, with two amendments:
   - the **host is its main producer** (replies, reviews, gate and monitor outcomes);
   - a pending `request` or `correction` may trigger **one host-launched successor**
     when a turn ends.
6. **Stage 3: gate everything live on evidence.** Mid-turn delivery through a
   SASE-installed Claude `PostToolUse` hook (and Codex `turn/steer` after an app-server
   migration) is now technically possible. But SASE built and then removed a "message a
   running agent" feature in March 2026. Ask why before rebuilding it.
7. **Do not build** any of these:
   - group chat or forums;
   - agent-side polling;
   - A2A;
   - LLM supervisors;
   - runtime file leases;
   - a `message` bead type;
   - gem's handoff-capsule protocol (`sase pipe --fresh` and continuation checkpoints
     already cover it).

---

## 2. What "collaboration" means for single-turn agents

The reports framed the problem differently, but their framings map onto each other.
cld's six patterns are the finest-grained, and mus's three needs sit inside them.

| # | Pattern (cld) | mus need | SASE today | External evidence of value |
|---|---|---|---|---|
| P1 | Independent fan-out + synthesis | N2 | Research swarms, `%{…}` fan-out, clans + `%wait` | **Strong**: Anthropic orchestrator-worker (+90%); independence avoids premature consensus |
| P2 | Delegation that returns an answer | — | `/sase_run` helpers; the reply comes back by DIY chain | **Strong** (manager-worker) |
| P3 | Independent review whose findings reach the author | N3 | Mentors (dormant), epic land agents, research critique | **Strongest**: Cognition's review loop, skeptical evaluators, cross-model review |
| P4 | Sequential continuity + human steering | N1 | Families, pipe/monitor/gate successors, message-board beads | **Moderate**: the `016` board experiment; low volume |
| P5 | Parallel writers on one codebase | — | Epics: DAG waves, isolated workspaces, land agent | **Mixed**: works with disjoint planner-assigned work; peer talk unsolved |
| P6 | Live peer discussion | N2 (partly) | None | **Weak or negative** outside open-ended search |

A seventh layer is orthogonal: **fan-out inside one provider turn** (Claude/Codex
subagents). SASE agents already use it (the `Agent`/`Task` tool appears in about 2% of
runs). It is compatible with single-turn execution *as long as the result returns
within the turn*. gem's "synchronous RPC is a fatal mismatch" holds only for blocking
on another *SASE agent*, or for vendor features that report after the turn ends
(§3.3).

---

## 3. What SASE has, and what is actually used

### 3.1 Mechanisms (code-verified)

**Launch-time and pull-based.**
- One agent's output reaches another only when the second agent *starts*:
  - through `%wait` plus template variables;
  - through `#fork`;
  - through a family successor.
- A running agent can *pull* with `sase chat show`, `sase var get`, bead notes and
  artifacts.
- Nothing pushes to a running agent through SASE.

**`%wait` context is thin.**
- `{{ wait.chats }}` returns transcript *paths*.
- For a clan it returns only the newest successful member's chat, although
  `wait.artifacts` spans every successful member (`src/sase/axe/run_agent_refs.py:195-240`).
- Only a `completed` outcome releases a wait. A failed dependency parks the waiter
  (`docs/xprompt.md:2329-2342`).

**Delegation has no reply join.**
- `/sase_run` supports only `resume_requester` and `terminal_handoff`
  (`src/sase/agent/launch_request_continuation.py`).
- `resume_requester` fires when the *LaunchApproval gate* settles, not when the child
  finishes (`src/sase/xprompts/skills/sase_run.md:135-141`).
- To get the child's answer, the requester has to chain turns by hand: a gate, a
  resumed requester whose only job is to start a monitor, a monitor running
  `sase agent wait`, and a third turn. That is cld's §2.3 finding, and it is confirmed.

**Review is not pinned to a vendor.**
- `MentorConfig` has `mentor_name`, `role` and `focus_areas`, and no model field
  (`src/sase/config/mentor.py`). Mentors invoke with `model_tier="large"`
  (`src/sase/workflows/mentor.py:336`).
- Two partial escape hatches exist. None of the reports noticed them:
  - **Mentor prompt directive (unverified end-to-end).** `invoke_agent` extracts
    `%model` from the *rendered* prompt (`src/sase/llm_provider/_invoke.py:162-205`),
    and the lead confirmed that `extract_prompt_directives` pulls `%model:` out of
    arbitrary rendered text. A `%model` directive in a mentor role or a project-local
    `#mentor` override is therefore likely to pin the reviewer. This was not tested
    through a real mentor run.
  - **Epic land model (verified).** Epic land agents already take a configurable model:
    - `epic_lander_model: "@large"` and `big_epic_lander_model: "@xlarge"` in
      `src/sase/default_config.yml:1415-1416`;
    - a plan bead's `-m` overrides it (`docs/beads.md:1248`);
    - the route is chosen in core (`select_epic_land_model`).
- Neither escape hatch can express *"not the author's vendor"*.

**Handoff compaction mostly exists already.**
- `sase pipe --fresh` starts a clean-context successor from a prompt the agent writes.
- Monitor handoffs record structured continuation checkpoints, and a budget preflight
  can reduce fork content (`continuation_budget_decision.json`, `reduction_candidates`,
  `local:continuation/checkpoints/…`).
- Together these cover most of gem's "handoff capsule" proposal.

**No messaging code has shipped.**
- Family channels remain a design.
- The message-board beads `sase-xs`, `sase-xt` and `sase-xu` are the only prototypes.
- A bead search finds nothing for "mailbox", "SendMessage", "crossSessionInbound",
  "cross-vendor" or "reply join".

**A mid-run steering feature was built and then removed.** None of the reports found
this.
- `739196a9c` (2026-03-14) added a TUI `m` key that sent a message to a running agent.
- `1a46198f1` (2026-03-28) removed the TUI side. Its plan records no rationale.
- The provider-side consumer still runs: `start_interrupt_monitor` watches
  `interrupt_request.json` (`src/sase/llm_provider/_subprocess_plain.py:40-65`).
- For Claude, an interrupt terminates the process and restarts with **only the user's
  message** in a fresh session (`src/sase/llm_provider/claude.py:456-468`).
- Nothing in the sase repo writes that file any more. One `interrupt_log.jsonl` exists
  among runs since August.

### 3.2 The usage corpus (lead, new)

**Scope:**
- every `ace-run` artifact directory across athena's projects dated
  2026-08-15 → 2026-09-22;
- 4,819 `tool_calls.jsonl` logs and 5,041 `raw_xprompt.md` prompts.

**Counts:**

| Signal | Count | Share |
|---|---|---|
| Prompts using `%wait` / `%w` | 2,220 prompts | 44% |
| Prompts using `#fork` | 1,124 | 22% |
| Prompts declaring `%clan` | 424 | 8% |
| Prompts using `#research` swarms | 201 | 4% |
| Runs writing bead notes (`sase bead note`, `update/close --note`) | 1,521 runs (3,039 commands) | 32% |
| Runs using `sase chat show` (pulling another agent's transcript) | 102 runs (202 commands) | 2% |
| Runs using the Claude `Agent`/`Task` subagent tools | ~112 runs (252 calls) | 2% |
| Runs using `/sase_run` (agent-initiated launch) | 23 runs (28 skill uses) | 0.5% |
| `sase agent wait` executions | 18 in 9 runs | 0.2% |
| Claude `SendMessage` calls | 1 | — |
| Claude `ListAgents` calls | 75 in 22 runs (the sampled ones were epic phase workers) | 0.5% |
| Mentor completions ever recorded | 17, all 2026-07-31 → 08-09 | — |
| "Wait dependency can never self-resolve" notifications | 79 in 8 days (2026-09-14 → 21); 71 involve epic land or phase waits | — |
| Measured `#fork` renders (total expanded bytes) | 315 renders: p50 10 KB, p90 63 KB, p99 227 KB, max 365 KB; none over budget | — |

**What this changes:**
- **Launch-time coordination and bead notes are SASE's collaboration corpus.** Under
  `decisions:corpus-before-mechanism`, improving `%wait` context and review routing has
  a much larger addressable base than delegation joins or messaging.
- **cld over-weighted the delegation loop.** It called it friction "every SASE user
  hits", but it touches about 0.5% of runs. The low count may partly reflect how painful
  the loop is today. It stays in Stage 1 because it is cheap and feeds Stage 2, but it
  is not first.
- **Mentors are the wrong first host for cross-vendor review.** They are effectively
  dormant on this host. Review happens today in epic land agents, research critique and
  synthesis, and ad-hoc reviewer launches.
- **Most wait-parking comes from epic retries.** 71 of the 79 notifications involve epic
  land or phase waits, where staying parked until a retry succeeds is partly intended.
  Failure propagation should be **opt-in** per wait, not a new default.
- **gem's "quadratic" fork accumulation is a tail risk, not a present failure.** The
  median fork is 10 KB, and the budget preflight has not tripped.
- **Epic phase workers already reach for peer discovery.** They made the `ListAgents`
  calls. This suggests latent demand for sibling awareness in P5, and shows the native
  side channel is within reach of real workloads.

### 3.3 The native Claude Code side channel (cld's finding, re-verified)

**In this session:**
- Claude Code **2.1.278** exports `CLAUDE_CODE_MESSAGING_SOCKET`.
- `ListAgents` named this session `sase-29-4e` and listed a live peer (`sase-25-ae`,
  interactive, in tmux).
- `claude.py` passes `--dangerously-skip-permissions` and disallows only
  `ScheduleWakeup` (`src/sase/llm_provider/claude.py:420-427`). It sets no
  `crossSessionInbound`.

**The Claude Code cross-session messaging docs (fetched 2026-09-22) confirm:**
- A `claude -p` session binds an inbox socket. Bare mode does not.
- A message is read "between tool calls during an active turn", or starts a new turn if
  the session is idle.
- A receiving session that bypasses permissions delivers a message **only when the
  sender also bypasses**. Otherwise it holds the message, and in `-p` a held message
  expires after `dialogExpiry` (5 minutes).
- `crossSessionInbound` accepts `accept`, `hold` or `refuse`, and a `--settings` value
  takes precedence over user settings.
- Deny rules can remove `SendMessage` and `ListAgents`. **Denying `SendMessage` also
  removes subagent messaging.**
- When no `crossSessionInbound` value applies, a message that comes from the session's
  **own child process** (for example a hook) is delivered.

Two consequences follow:

1. **Every SASE Claude agent can steer every other one mid-turn.** So can any
   `--dangerously-skip-permissions` Claude session you run by hand, and nothing reaches
   SASE's chats, artifacts or audit trail. Closing this takes
   `--settings '{"crossSessionInbound":"refuse"}'` plus `ListAgents` in
   `--disallowedTools`. Keep `SendMessage` so in-session subagents still work.
2. **The SASE host cannot use this socket as its own transport.**
   - The runner is the Claude process's *parent*, not its child, so a host post is an
     unverified peer message. A bypass session holds it and drops it after 5 minutes.
   - With `refuse` set, it is dropped immediately.
   - A **SASE-installed `PostToolUse` hook** is a child of Claude and returns
     `additionalContext` directly, so it is the clean mid-turn path. This settles
     cld's hook-versus-socket preference.

**A related hazard (lead):** this session also exposes vendor-native tools whose results
arrive *after* the turn ends:
- `Workflow`, which "runs in the background … a `<task-notification>` arrives when the
  workflow completes";
- `Monitor`;
- `CronCreate`;
- `RemoteTrigger`.

All of these are present even though `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` is set.
SASE currently polices them only through prompt text. That resolves cld's
[unverified] question: the environment variable does not remove them.

---

## 4. What the outside evidence says

Condensed from cld §3. cld marks most rows as primary sources it fetched ([V]). The lead
re-checked the rows marked ✓.

| Finding | Source | Consequence for SASE |
|---|---|---|
| Keep writes single-threaded; extra agents should contribute judgment, not actions. Coder and reviewer should share no context. Surfacing sibling discoveries is the open problem | Cognition, Apr 2026 | Put P3 first. Be cautious with P5 peer channels |
| Decompose by context, not phase: role pipelines are a "telephone game". Multi-agent costs 3–10× tokens | Anthropic, Jan 2026 | Build review loops, not role chains. Budget every wake |
| Forum swarms help open-ended search, but show premature consensus, polling storms (2.4M job requests, 117 accepted), collusion through back-channels, and quality that varies by model | Anthropic Frontier Red Team, Aug 2026 | P6 only as a scripted experiment. Never let agents poll |
| Independent agents amplify errors 17.2×; central coordination holds that to 4.4×. Sequential tasks lose 39–70% under multi-agent designs | Google Research, 2026 | A central synthesizer or verifier is load-bearing |
| **Claude reviewing Codex raised the pass rate from 71.6% to 89.7%; Codex reviewing Claude dropped it from 91.4% to 82.8%** ✓ | Xiang et al., arXiv 2607.21656 (2026-07-22) | Cross-vendor review helps **asymmetrically**. Make direction configurable and measure it on SASE's own data |
| Fresh-context review beats same-session review | Cross-Context Review, Mar 2026 | SASE reviewers already get fresh context |
| Hard locks collapsed 20 agents to the throughput of 2–3. Planners plus non-communicating workers plus a judge worked | Cursor, Jan–Feb 2026 | No lock service |
| Advisory "runtime informs, agent repairs" ordering beat locks and optimistic concurrency | CoAgent, Jun 2026 | If P5 needs anything, use deterministic advisories |
| Agent Mail's file reservations target agents **sharing one working tree**; no source gives gem's "reduced merge conflicts by over 80%" ✓ | mcp_agent_mail docs; lead search | gem's lease case does not transfer to SASE's isolated clones |
| Codex app-server `turn/steer` appends input to the in-flight turn (it needs `expectedTurnId`) ✓. **openai/codex#40805 (open, filed 2026-08-26):** it can return success before the input is persisted | Codex docs; GitHub issue | A mid-turn "accepted" is not a receipt. Inclusion bookkeeping must not trust it |
| Agent-driven polling fails: agents "call the tool once before ending" their turn | MCP Tasks SEP-1686 | The host owns delivery and wake-up |
| Orca #16903: prompt-based completion signalling broke, and coordinators waited forever | Orca issue | Completion stays a typed host event (`done.json`, finalizers) |

**Distilled rules** (cld, endorsed by mus and gem):
- independence before aggregation;
- the host owns delivery;
- use a durable mailbox, not live chat;
- completion is typed and host-verified;
- choose the injection boundary deliberately (launch, end of turn, tool boundary);
- peer messages are untrusted data;
- measure per model;
- keep the harness thin.

---

## 5. Where the reports disagreed, and how it resolves

| Topic | cld | mus | gem | Resolution |
|---|---|---|---|---|
| **What comes first** | Close the loops (reply join, review, wait output, side channel), then the inbox | Channels + pinned review together | Channels first, then capsules, debate, leases, TUI | **Loops first**, but re-weighted by the corpus (§3.2): wait-context fidelity and review routing lead, and the reply join follows. Channels come second, once Stage 1 gives them host-produced traffic |
| **Acknowledgment** | Explicit, via the final declaration or a CLI | Explicit batch ack | **Host auto-acks on successful turn** | **Explicit.** `family_channel_delivery` rejected ack-on-success, because exit status says nothing about receipt. Compromise: carry acks in the `/sase_final` declaration, which every agent already submits. A crash never acks. An included but unacknowledged batch is re-offered once, marked "previously included", and then surfaced in the TUI |
| **Budget overflow** | Never ack omitted ranges | Same | **Inject the newest, omit the older, advance the cursor to the highest injected ID** | **gem's rule silently skips messages.** Use contiguous oldest-first batches, an overflow notice, and never advance past omitted entries |
| **Budget size** | Aggregate | ~8 KiB / 10 entries | 4 KB | Both numbers are hypotheses. Start at an 8 KiB aggregate and measure prompt bytes |
| **File leases** | No lock service; plan-time overlap warning | Not covered | **`sase lease acquire`, TTL, AXE pre-dispatch checks** | **Reject runtime leases.** SASE workspaces are isolated clones, so leases would only *predict* landing conflicts. Cursor saw locks collapse throughput, and gem's 80% figure is unsourced. Declared phase paths plus a plan-time overlap warning, with the existing finalizer conflict-repair turn, get most of the value |
| **Handoff capsules** | — | Adopt native session portability; don't build | **`sase pipe --capsule` with a JSON schema** | **Don't build a new protocol.** `pipe --fresh`, continuation checkpoints and the fork budget preflight already exist. Anthropic warns that lossy summaries play telephone. Revisit if fork p99 grows past budget |
| **Clan / parallel channels** | Defer; route hazard notices to the land agent only | Not covered | Clan channels for siblings | **Defer.** Cognition and Cursor both keep workers from talking to each other. Sibling hazards go to the integrator |
| **Mid-turn delivery** | Optional capability tier (Claude hook, Codex steer) | "Not promised by any provider path" | Impossible ("cannot subscribe") | **cld is right that it is now possible.** It stays evidence-gated: the March `m`-key removal is the only prior trial, and it was abandoned |
| **Where cross-vendor review attaches** | Mentor `model` + `different_from_author` | Mentor model field | Mentor model + 2-round debate | **Put the constraint in core model routing, not in `MentorConfig` alone.** Apply it first to epic land agents and research critique, where review actually runs, and to mentors when they are re-enabled. Bound debate to N rounds with the human accept gate (cld and gem agree) |
| **SASE revision inspected** | `c6807d24c` | `c6807d24c` | `09c93253` (the older revision `family_channel_delivery` used) | gem's code claims were weighed as second-hand where they were not independently confirmed |

**What each report contributed:**
- **cld** had the broadest and best-sourced survey, and three original findings: the
  side channel, vendor mid-turn capabilities, and the delegation-loop analysis.
- **mus** had the tightest first-release scope and acceptance list, and the "adopt,
  don't build" stance on session portability.
- **gem** had a useful concrete schema sketch, a V1–V6 acceptance matrix, and a clear
  separation of human steering from peer notes. Two of its mechanisms contradict
  corrections already made in `family_channel_delivery`: auto-ack and newest-first
  truncation. Two of its components are unsupported or redundant: leases and capsules.

**What all three missed:**
- the usage corpus;
- that mentors are dormant;
- the existing escape hatches for pinning a reviewer model;
- the removed March steering feature;
- the fact that the host cannot use Claude's socket;
- the async vendor tools exposed in SASE sessions.

---

## 6. Recommended architecture

### 6.1 Five rules

1. **The host carries collaboration between turns.** Agents never poll, never wait in
   place, and never wake each other directly.
2. **Writes stay single-threaded per workspace.** Parallel writers are coordinated by
   the planner and integrator (the DAG, the land agent and the finalizer), not by peers.
3. **Independent judgment is the product.** Fan-out stays independent until synthesis.
   Review uses fresh context and, by policy, a different vendor.
4. **Every exchange is typed, attributed and durable.** Replies, reviews and messages
   are host-recorded events with provenance. Prompt text is never proof of delivery,
   receipt or authority.
5. **Every stage ships behind a flag with adoption metrics** (§8) and is removed if its
   metrics don't move.

### 6.2 Stage 0: hygiene (now; launch-flag changes)

- **Close the native messaging side channel.** Launch SASE Claude agents with
  `--settings '{"crossSessionInbound":"refuse"}'` and add `ListAgents` to
  `--disallowedTools`.
- **Remove async vendor tools that cannot deliver in a single turn.** Add `Workflow`,
  `Monitor`, `CronCreate`/`CronDelete` and `RemoteTrigger` to `--disallowedTools`,
  alongside `ScheduleWakeup`. SASE's own `/sase_monitor` and gates replace them.
- **Decide what to do with the orphaned interrupt consumer.** Either delete
  `interrupt_request.json` handling, or keep it as the Stage 3 seam and make it resume
  the session instead of starting a fresh one.

### 6.3 Stage 1: close three loops on existing seams (no new store)

**1a. `%wait` context fidelity.** This serves the 44% of prompts that already
coordinate this way.
- Add a bounded `wait.replies`: reply bodies capped with an artifact pointer.
- Return every clan member's chat, not only the newest.
- Add `wait.outcomes`.
- Add an **opt-in** per-wait failure policy, for example resuming the waiter with a
  failure bundle instead of parking. Keep parking as the default for epic retries.
- This is template and runner work next to the existing deferred-`fork` seam
  (`src/sase/xprompt/processor.py:80`).

**1b. Cross-vendor review as a routing constraint.**
- Add a core model-routing constraint such as
  `reviewer_provider: different_from_author` that filters a pool by the author's
  provider. It lives in sase-core, next to `select_epic_land_model`, per the Rust
  boundary.
- Apply it first to **epic land agents** and **research critique and synthesis roles**,
  then to `MentorConfig.model` when mentors are re-enabled.
- Route accepted findings back to the **author family** as a typed follow-up whenever
  that family can resume, instead of to an unrelated `make_mentor_changes` agent.
  Bound it to N rounds, and keep the human accept gate as the default.
- **Record the (author, reviewer) provider pair on every review.** The published
  asymmetry says Claude→Codex review helps and Codex→Claude review hurt. So
  direction-specific defaults should come from SASE's own data, not from a symmetric
  rule.
- Stopgap today: set the plan bead's `-m` (land model) to a different vendor, or try a
  `%model` directive in the reviewer prompt.

**1c. Delegation reply join.**
- Add a requester-continuation mode such as `resume_requester_on_completion`. It
  resumes the requester when the delegated child *settles* (success or failure) with a
  bounded bundle:
  - the outcome;
  - the reply body with an artifact pointer;
  - registered artifacts;
  - `sase var` outputs.
- It compiles onto existing pieces: the gate follow-up, `%wait`, and `wait.artifacts`
  rendering after admission. That replaces today's three-turn chain.
- Cheap, but low-corpus. Ship it after 1a and 1b.

**1d. (Optional) plan-time overlap warnings.**
- Let phase beads declare expected paths.
- Have `sase bead work` warn when two same-wave phases overlap.
- This replaces gem's leases.

### 6.4 Stage 2: the durable family inbox (build after Stage 1; trial it)

Implement the `family_channel_delivery` vertical slice in sase-core as specified there:
- immutable envelopes;
- a monotonic sequence assigned at commit;
- stable IDs and idempotency keys;
- family-owned subscriber progress;
- the pending → included → acknowledged → answered states;
- snapshot after admission;
- an aggregate budget that never acknowledges omitted ranges;
- SQLite outside workspaces with `synchronous=FULL` for durable-post claims;
- host-recorded provenance kept separate from the claimed author.

Add these amendments:

| Amendment | Why |
|---|---|
| **Host is a first-class producer.** It posts typed `reply` (from 1c), `review` (from 1b), and gate or monitor outcomes | Gives the inbox real traffic, and a provenance that cannot be forged, from day one. Answers the corpus objection that human-authored posts alone would be rare |
| **Addresses:** `family:<id>` (lazy per-family inbox) plus explicit `channel:<name>` boards with opt-in subscriptions. No clan or tribe addressing yet | Covers P4 steering and continuity. P5 sibling traffic goes to integrators only |
| **Kinds and delivery policy:** `info` and `checkpoint` go into the next shell only. `request` and `correction` can also trigger **one** host-launched successor at turn end if no continuation is scheduled, subject to admission, dedupe and a per-family budget | Closes the "pending message but the family is dead" gap without polling. Needs no amendment to `decisions:single-turn-agents` |
| **Acks carried in the `/sase_final` declaration** (§5) | Explicit receipt without a new agent chore |
| **Keep beads for work** | 32% of runs already write bead notes, such as `PROPOSED FOLLOW-UP` and phase evidence. Those are work records and stay there. The inbox is for steering and continuity that is not tied to a work item |

Use the acceptance list from `family_channel_delivery` (mus §5 and gem V1–V6 restate
it). Among other things, it checks posts during a runner-slot wait, subscription
survival across fresh pipes, handoffs and recovery, independent cursors, crash replay,
authors that cannot be impersonated, and honest reporting of dead families.

### 6.5 Stage 3: evidence-gated extensions

- **Mid-turn delivery.**
  - *Claude:* a SASE-installed `PostToolUse` hook, passed with `--settings`, returns
    pending `correction`/`request` entries as `additionalContext` and records
    inclusion. It works with inbound messaging refused and needs no socket trust
    (§3.3).
  - *Codex:* only after SASE moves Codex to the app-server, and never treating a
    `turn/steer` success as receipt (#40805).
  - Other providers fall back to end-of-turn delivery.
- **Channel-wait wakeups.** A monitor ends on a post or a timeout and launches one
  successor. It registers first and then rechecks, to avoid lost wakeups.
- **Epic hazard notices.** Phase workers post `info` tagged "affects interface X". It is
  delivered to the land agent and later dependents, never to running siblings. Trigger
  this only if land-agent reports show cross-phase surprises that 1d missed.
- **One scripted deliberation experiment.** Bounded rounds over a channel, with a
  moderator, mixed models and fixed budgets. It stays an xprompt, not a primitive.
- **Native session portability.** Adopt ACP `session/resume`, `codex exec resume` and
  casr/txcript formats as the multi-CLI track lands them. Don't reimplement them
  (mus, and `multi_cli_orchestration_vs_sase` §7.4).

### 6.6 Not building

- group chat or forums;
- agent-side polling or "check your inbox" instructions;
- A2A endpoints;
- LLM watchdogs or supervisors;
- lock or lease services;
- a `message` bead type;
- native Claude teams or the messaging socket as the system of record;
- broadcast by default;
- a handoff-capsule protocol;
- a distributed broker.

---

## 7. Decisions only you can make

1. **Do you want to steer a running agent mid-turn?**
   - You removed the `m` key in March 2026 without a recorded reason.
   - If it was because interrupts discarded context, the hook-based Stage 3 path fixes
     that.
   - If mid-turn steering simply wasn't useful, drop Stage 3 mid-turn delivery and
     delete the orphaned interrupt consumer.
2. **Which review directions do you allow?**
   - One controlled study says Claude should review Codex, not the reverse.
   - Pick a default: symmetric `different_from_author`, or direction-specific.
   - Either way, recording provider pairs will settle it for your own workload.
3. **Should mentors come back?**
   - If yes, attach 1b to them as well.
   - If no, land agents and critique roles are the review surface, and `MentorConfig`
     changes can wait.
4. **Is there a live supervision or steering workflow to trial Stage 2 against?**
   - Without one, stop after Stage 1 and keep bead-note boards as the fallback.
   - That fallback is what `family_channel_delivery` recommends when messages rarely
     change decisions.

---

## 8. Metrics and kill criteria

| Stage | Keep investing if… | Stop or remove if… |
|---|---|---|
| 0 hygiene | — (security posture; no metric) | — |
| 1a wait context | Fewer `sase chat show` pulls by waiters; synthesizers cite every member; opt-in failure policies get used | Consumers ignore reply bodies |
| 1b review routing | Findings per Patch or epic and the accept rate hold; post-land fixes drop; provider-pair data shows which directions help | Cross-vendor pairs underperform same-vendor pairs, or accept rates are low |
| 1c reply join | Helper round-trips drop from ~3 requester turns to 1 | `/sase_run` stays near 0.5% of runs and nobody uses the mode |
| 2 inbox | Missed human corrections go to 0; manual reminders drop; delivered messages change the next shell's decisions; prompt bytes stay within budget; duplicate consequential actions = 0 | Messages rarely change decisions, or receipts add nothing over bead notes |
| 3 mid-turn | Corrections arriving mid-shell would measurably have prevented wasted work | Never triggered in a month of Stage 2 use |

---

## 9. Method, caveats and provenance

**Method.**
- The lead read the three researcher reports and both context syntheses through
  `sase artifact read`, and read no predecessor chat transcripts.
- **Code checks (sase `8acb66c44`):**
  - `MentorConfig` and the mentor invocation;
  - `invoke_agent` directive handling, plus a direct `extract_prompt_directives` test;
  - the epic land model selection and its defaults;
  - `/sase_run` continuation modes;
  - `run_agent_refs.py` wait resolution;
  - `%wait` failure semantics in `docs/xprompt.md`;
  - `sase pipe --help`;
  - continuation budget artifacts;
  - the Claude launch flags and interrupt loop;
  - `git log -S interrupt_request`.
- **Live probe:** this session's messaging environment variables, `ListAgents` output,
  and exposed tool list.
- **Corpus:** Python scans of the `ace-run` artifacts and `~/.sase/notifications`.
- **Web:** the Claude Code cross-session messaging and hooks docs, arXiv 2607.21656,
  Codex `turn/steer` search results, openai/codex#40805, and an Agent Mail search.

**Caveats.**
- The corpus covers one host (athena), one user and about five weeks. Its counts are
  regex-based over prompts and tool-input summaries, so small miscounts are possible.
- Counts measure *current* behaviour, which is shaped by current friction. Low
  delegation use may partly reflect how painful the loop is today.
- The `%model`-in-mentor-role stopgap is unverified end-to-end.
- Whether hooks fire in every `claude -p` configuration SASE uses was not re-tested.
- Codex hook injection capabilities are unverified.
- External numbers not marked ✓ rely on cld's fetched sources.
- **Discovered follow-up:** the Stage 0 side-channel and async-tool closure is a
  concrete task independent of this decision. The lead filed it as task bead
  **`sase-163`** (cld had deferred filing to the lead).

**Inputs.** Matched by dispatch `wait_name` and existing suffix, not by list order. Each
was read before relocation; stored snapshots and other workspaces were not modified.

| Input | Preserved report | Original canonical reference | Immutable snapshot |
|---|---|---|---|
| `research.26.cld` | [cld](multi_agent_collaboration_strategy__cld.md) | `research:202609/multi_agent_collaboration_design__cld.md` | `file:explicit:d966eccbf716422a9a0729ec` |
| `research.26.mus` | [mus](multi_agent_collaboration_strategy__mus.md) | `research:202609/sase_multi_agent_collaboration__mus.md` | `file:explicit:d6d5cd0a4c8f4a07e5fd7ddb` |
| `research.26.gem` | [gem](multi_agent_collaboration_strategy__gem.md) | `research:202609/multi_agent_collaboration_architecture__gem.md` | `file:explicit:efd5284fcc54f41cf893959a` |

## 10. Key sources

**SASE (repo-relative, `8acb66c44`):**
- `src/sase/config/mentor.py`
- `src/sase/workflows/mentor.py:52-133, 336`
- `src/sase/llm_provider/_invoke.py:60-205`
- `src/sase/xprompt/directives.py:84`
- `src/sase/llm_provider/model_launch_settings.py:386-402`
- `src/sase/default_config.yml:1415-1416, 1792-1885`
- `src/sase/agent/launch_request_continuation.py`
- `src/sase/xprompts/skills/sase_run.md:135-165`
- `src/sase/axe/run_agent_refs.py:164-253`
- `docs/xprompt.md:873-887, 2311-2342`
- `docs/beads.md:1248`
- `src/sase/llm_provider/claude.py:420-427, 456-468, 527`
- `src/sase/llm_provider/_subprocess_plain.py:40-65`
- commits `739196a9c`, `1a46198f1`
- beads `sase-xs`, `sase-xt`, `sase-xu`

**Prior research:**
- [`family_channel_delivery`](../family_channel_delivery/family_channel_delivery.md)
- [`multi_cli_orchestration_vs_sase`](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md)
- [`sase_collaboration_architecture`](../sase_collaboration_architecture.md), cited
  by all three researchers for its three-plane framing

**External:**
- Claude Code: [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) ·
  [hooks](https://code.claude.com/docs/en/hooks)
- Codex: [app-server](https://learn.chatgpt.com/docs/app-server) ·
  [openai/codex#40805](https://github.com/openai/codex/issues/40805)
- Cross-model review: [Xiang et al., arXiv 2607.21656](https://arxiv.org/abs/2607.21656)
- Agent Mail: [mcp_agent_mail](https://github.com/dicklesworthstone/mcp_agent_mail) ·
  [mcpagentmail.com](https://mcpagentmail.com/)
- Research and industry evidence (full list in [cld §10](multi_agent_collaboration_strategy__cld.md)):
  - [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  - [Anthropic multiagent systems research](https://www.anthropic.com/research/multiagent-systems)
  - [Cognition: multi-agents working](https://cognition.com/blog/multi-agents-working)
  - [Cursor: scaling agents](https://cursor.com/blog/scaling-agents)
  - [Google: towards a science of scaling agent systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)
  - [MAST](https://arxiv.org/abs/2503.13657)
  - [CoAgent](https://arxiv.org/abs/2606.15376)
  - [MCP Tasks SEP-1686](https://modelcontextprotocol.io/seps/1686-tasks)
  - [Orca #16903](https://github.com/stablyai/orca/issues/16903)

---

## Recommended solution

**Implement multi-agent collaboration as host-carried information between single-turn
agents, staged by evidence. Agents do not converse.**

1. **Now (Stage 0, launch flags only):**
   - launch SASE Claude agents with `crossSessionInbound: refuse` and a `ListAgents`
     deny;
   - disallow `Workflow`, `Monitor`, `CronCreate` and `RemoteTrigger`;
   - decide whether to delete or repurpose the orphaned interrupt consumer.
2. **Next (Stage 1, existing seams, no new store), in this order:**
   - **(a)** bounded reply bodies, full clan coverage, outcomes and an opt-in failure
     policy in `%wait` context;
   - **(b)** a `different_from_author` reviewer constraint in core model routing,
     applied to epic land agents and research critique first. Findings route back to
     the author family, and every review records its provider pair;
   - **(c)** a `/sase_run` continuation mode that resumes the requester when the child
     settles, with a bounded result bundle;
   - optionally **(d)** plan-time overlap warnings for same-wave epic phases.
3. **Then (Stage 2): the narrow durable family inbox in sase-core, as specified in
   `family_channel_delivery`.**
   - The host posts replies, reviews and gate or monitor outcomes into it.
   - Acks travel in the final declaration.
   - Batches are contiguous and oldest-first.
   - A pending `request` or `correction` can trigger one budgeted successor at turn end.
   - Trial it against that report's adoption criteria, on a real steering workflow.
4. **Only on evidence (Stage 3):**
   - mid-turn delivery through a SASE-installed Claude `PostToolUse` hook, and Codex
     `turn/steer` after an app-server move;
   - channel-wait wakeups;
   - epic hazard notices routed to the integrator;
   - one scripted deliberation experiment.
5. **Never:**
   - peer group chat;
   - agent polling;
   - A2A;
   - LLM supervisors;
   - lease or lock services;
   - a message bead type;
   - a new handoff-capsule protocol.

This keeps SASE's differentiators: single-turn agents, host-owned completion,
provider-neutral landing and durable state. It spends tokens where collaboration is
known to pay, on independent cross-vendor judgment and results that actually return.
And it puts each new mechanism in front of a corpus that exists, or that the previous
stage creates.
