# Multi-Agent Collaboration for SASE Agents: Options and Recommended Solution

- **Researcher:** mus (independent, 3-researcher swarm)
- **Date:** 2026-09-21
- **Revision inspected:** sase @ `c6807d24c` (2026-09-21)
- **Question:** What is the best way to implement multi-agent collaboration between SASE agents?

## 0. Bottom line

**Recommended solution: keep SASE's artifact-plane coordination as the foundation, and add two narrow capabilities on top of it — (1) durable opt-in family channels with bounded next-shell delivery, implemented in host-owned state (Rust core), and (2) provider-pinned cross-vendor review (a model field on mentors/roles). Fix supervision continuation ownership alongside, not inside, the channel work. Defer live inter-agent messaging, group chat, and any broker.**

Collaboration between SASE agents should stay asynchronous and artifact-shaped: agents coordinate through beads, artifacts, `#fork` history, and monitor follow-ups — durable things that survive handoffs and crashes. What is genuinely missing is (a) a way for a finding, correction, or checkpoint to remain discoverable across shells without depending on someone remembering to `#fork` the right transcript, and (b) a way to say "have a *different* vendor review this work." Both are small, host-owned features. Neither requires live messaging, and live messaging would be the wrong first step: SASE agents are single-turn shells, so any "live" channel is next-shell delivery with marketing on top.

## 1. What "multi-agent collaboration" means here

This report is about collaboration *between SASE agents* (agent-to-agent), not about running many vendor CLIs (covered by the multi-CLI orchestration synthesis) and not about multi-user/multi-machine federation (covered by the collaboration-architecture report). Three distinct needs hide inside the word:

| # | Need | Example |
|---|---|---|
| N1 | **Sequential continuity** — carry state through a chain of shells | A supervision sequence survives a handoff failure; an operator correction posted mid-run reaches the next shell |
| N2 | **Parallel exchange** — share findings between concurrently running families | Two researchers compare notes; one family consumes another's checkpoint without re-doing the work |
| N3 | **Adversarial review** — an independent mind checks the work | A Codex agent reviews what a Claude agent wrote, tied to a Patch |

N1 is the most valuable and the least served today. N2 is partially served by beads/artifacts. N3 exists in weak form (mentors) but cannot express cross-vendor review.

A hard constraint shapes everything: **SASE agents are single-turn.** A run starts, does finite work, and ends; continuation is always a newly launched shell. So "sending a message to a running agent" really means one of three things: (i) it lands in some *later* shell's prompt, (ii) the running shell performs a finite read of a store, or (iii) a provider-specific mid-generation injection exists (not promised by any SASE provider path today). Any design that pretends otherwise — automatic acknowledgment on shell success, "the agent will change course immediately" — is overclaiming.

## 2. What SASE has today (code-verified at `c6807d24c`)

Inspected first-hand; paths relative to the sase repo:

- **Families** (`src/sase/history/chat_fork/family.py`): sequential chains — each member continued the previous member's work. `#fork` renders the chain as attributed transcript text. This is N1's current carrier, and it works only if the next shell names the right source.
- **Clans** (`src/sase/history/chat_fork/clan.py`): prompt-only summaries with transcript links ("read a listed transcript only when needed") — a bounded-context pattern already in the codebase.
- **Tribes** (`src/sase/xprompts/tribe.md`): a user-managed grouping tag (`%id(tribe=…)`), no messaging semantics.
- **Swarms** (`src/sase/agent/_xprompt_swarm_parsing.py`, `xprompt_swarm.py`, `multi_prompt_launcher.py`): fan-out with scripted parallelism — N2's launch mechanism, but with no shared channel once running.
- **`%wait`, `#fork(a, b)`, multi-parent forks, pipes, monitor follow-ups** (`src/sase/monitor/followup_prompt.py`, `src/sase/xprompts/fork.yml`): scripted asynchronous coordination. Monitor `--next` text is literal (wrapped in a disabled region), so follow-up bodies do not expand macros — coordination through them must be explicit.
- **Beads and artifacts**: the durable work store and the audited reference system. Usable as an ad-hoc board today (short entries + payload references), with no subscription, delivery, or receipt semantics.
- **Mentors** (`src/sase/config/mentor.py`): scheduler-driven automated review on Patches. `MentorConfig` has `mentor_name`, `role`, `focus_areas` — **no model field**, so "review by a different vendor" is inexpressible.
- **Gates, notifications, questions**: the attention plane is machine-local and single-user; dismissing a notification must never count as acknowledging a family message.

Gaps, stated plainly: no live inter-agent messaging (family channels remain a design; only the `fakey` test provider mentions channels); no subscription or receipt state anywhere; review cannot be pinned to a provider; and continuation ownership has known holes (a monitor startup ends its caller's turn, so "schedule the next monitor, then keep working" silently drops the work).

## 3. Options considered

### Option A — Status quo: scripted async coordination only

Swarms + `%wait` + `#fork` + beads + monitor follow-ups, with conventions (e.g. a board-kept-in-a-bead) instead of machinery.

- *Pros:* zero new code; matches single-turn execution perfectly; every coordination act is already a durable artifact.
- *Cons:* continuity depends on prose memory — the next shell must know which transcript/bead to fork. The `016` supervision experiment showed exactly this failure: handoffs broke because no durable subscription said "this family cares about that board." Operator corrections can silently vanish at a handoff. Conventions also rot: placeholder fields, stale inventories, and 110 KB prompt dumps when a board is rendered naively (per prior channel research measurements).

Verdict: necessary but insufficient. Keep it as the substrate; it does not solve N1.

### Option B — Xprompt-only board (`#board` over bead notes)

A `#board(...)` workflow modeled on `#fork`, with no core or runner change: render a bounded view over existing notes.

- *Pros:* cheap experiment in prompt size and readability; exercises rendering before committing to storage.
- *Cons:* it cannot provide what the feature promises. A new workflow does not inherit `fork`'s deferred-launch behavior (`LAUNCH_DEFERRED_XPROMPT_NAMES` singles out `fork` in `src/sase/xprompt/processor.py`); monitor `--next` text is literal so `#board(...)` inside a successor body does not invoke; timestamp-filtered cursors are unsafe against the event store's own ordering guarantees (appended events can carry earlier timestamps); subscriptions carried only in prose do not survive a fresh pipe. It is a renderer wearing a subscription's clothes.

Verdict: accept as an optional display convenience or disposable experiment; **reject as the collaboration implementation.**

### Option C — Narrow durable family channels (recommended core)

Explicit named channels with opt-in family subscriptions; small immutable message envelope (ID, channel, monotonic sequence, sender provenance, kind, body, artifact refs, reply/supersede links); durable per-family progress with explicit receipt acknowledgment; bounded host-composed injection at the next shell (aggregate budget, fair batching, overflow pointers); human-visible pending/included/acknowledged states. Storage in `sase-core` (SQLite outside ephemeral workspaces), orchestration/adapters in Python. This is the family-channel synthesis's recommendation, and my independent code reading confirms its two load-bearing corrections: subscription/delivery state must be host-owned (not prose, not a bead type), and delivery must be snapshot-after-admission, as close to provider invocation as practical.

- *Pros:* solves N1 directly — a correction posted mid-run is pending, then included, then acknowledged, each state honestly defined. Solves the N2 subset that matters (independent subscriber progress per family). Small enough to trial with real acceptance criteria. Reuses proven pull-consumer semantics (durable cursors, at-least-once + dedupe keys) instead of inventing a protocol.
- *Cons:* new subsystem with real consistency obligations (crash between prompt-persist and inclusion-record must replay, not skip; acknowledgment means receipt, never comprehension). Requires Rust-core work per the backend-boundary rule.

Verdict: **build this**, scoped exactly as described. One shared board plus the smallest human post/status surface first; no early wake, no implicit per-run mailboxes, no thread trees, no cross-machine transport until usage demands them.

### Option D — Live messaging: inbox, group chat, @mentions, broker

The Orca/Maestro/NTM end of the spectrum: agent inboxes, moderated group chat, wake-on-post, a deployed broker or general forum.

- *Pros:* lowest latency; matches the "team chat" mental model; best for interactive driving.
- *Cons:* fundamentally mismatched to single-turn execution — every "live" semantic degrades to next-shell delivery plus a wake mechanism, at much higher complexity. Traffic evidence does not justify it (single-digit messages per hour in the prototypes). Waking has sharp edges: interrupting an arbitrary build/test monitor on someone's post, one-active-shell-per-family violations, timeout/post races, and launch-admission bypasses. A broker is distributed-systems machinery for a problem currently measured in messages per hour. Anthropic's own forum experiments show coordination failures and premature consensus alongside the benefits — more communication is not monotonically better.

Verdict: **defer.** Revisit only on observed latency pain (explicit-wait usage + receipt-latency measurements from Option C), never speculatively.

### Option E — Provider-pinned cross-vendor review (recommended complement)

Add a model field to `MentorConfig` (and, by extension, to role harnesses), so policy can say "a different vendor than the author reviews this Patch." This is the Agent Orchestrator pattern SASE currently cannot express, and it directly serves N3.

- *Pros:* tiny change (config + scheduler plumbing), large payoff: independent-vendor review is the cheapest inter-agent collaboration with proven defect-finding value. Composes with channels (review requests/replies travel as messages; the work linkage stays in beads).
- *Cons:* multiplies provider load; needs the provider-parity work (usage/tool-call/thinking capture gaps differ by provider, so a reviewer's observability depends on who reviews).

Verdict: **build with channels.** Ship the model field plus one default cross-vendor profile.

### Option F — Native session-portability handoff (adopt, don't build)

casr-style canonical session conversion, Skillsync-style full-session moves, or ACP `session/resume` — carrying tool traces across CLIs instead of SASE's text-replay `#fork`.

- *Pros:* makes cross-provider continuation lossless where SASE's text replay loses tool traces; ACP would additionally commoditize breadth (41 registry agents).
- *Cons:* external fast-moving surface; building a converter is a project in itself.

Verdict: **track and integrate, don't reimplement.** Fix SASE's own cheap continuation bugs first (Claude interrupt starts a fresh session despite `--resume` already being wired for wait-continuation; Codex rebuilds context by hand under a stale "no session persistence" assumption; drain discards in-flight progress). Adopt ACP `session/resume`/`usage_update` via a generic provider plugin when the multi-CLI track lands it; study casr/txcript formats before designing any cross-provider fork format.

## 4. How the options compare

| Criterion | A status quo | B xprompt board | C family channels | D live/broker | E pinned review | F portability |
|---|---|---|---|---|---|---|
| N1 continuity across handoffs | ✗ (prose memory) | ✗ (no durable state) | ✅ | ✅ (overkill) | — | ◐ (same-CLI only) |
| N2 parallel exchange | ◐ (manual) | ◐ (manual view) | ✅ (per-family cursors) | ✅ | — | — |
| N3 independent review | ◐ (same-vendor) | — | ◐ (transport) | — | ✅ | — |
| Fits single-turn execution | ✅ | ✅ | ✅ (designed for it) | ✗ (pretends live) | ✅ | ✅ |
| Honest failure semantics | ✅ | ✗ (skips on overflow) | ✅ (pending/replay visible) | ◐ | ✅ | ◐ |
| Implementation cost | zero | small, misleading | medium (core+Python) | large | small | external |
| Risk of overclaim | low | **high** | medium (managed by acceptance tests) | high | low | medium |

## 5. Recommended solution (phased)

**Phase 1 — the narrow slice (both parts, one release):**

1. **Family channels, minimal:** explicit channel create/post/read; family subscribe/unsubscribe; monotonic sequences + stable message IDs; durable batches with exact message IDs; explicit batch acknowledgment; bounded next-shell injection (aggregate budget, e.g. ~8 KiB / 10 entries as a tuning hypothesis, fair across channels, overflow stays visible and never auto-acknowledged); human timeline + pending/included/acknowledged view. **Keep beads for work and notifications for attention** — a message may request work via a linked bead but never assigns, launches, or retitles anything by itself. Sender provenance recorded by the host, never by author-string override; peer posts are evidence, not authorization.
2. **Provider-pinned review:** model field on `MentorConfig`; one default cross-vendor profile (author vendor ≠ reviewer vendor).
3. **Continuation-ownership repair (parallel, separate):** every turn-ending branch records the next action; prefer host-owned scheduling for recurring supervision with non-overlap and dedupe. Reliable messages cannot keep an unscheduled sequence alive, so this ships alongside — but as its own fix, not as channel code.

**Phase 2 — only on measured pain:** explicit channel wait (subscribe-then-recheck, coalesced bursts, one active shell per family, timeout/post races settle once); MCP/hook sync so shared context actually spans CLIs.

**Explicitly deferred:** broker/general forum, implicit mailboxes, thread trees, semantic search, auto-task-creation, cross-machine live transport, urgent-cancel-over-channel (cancellation stays on existing control surfaces — a board cannot beat the next shell).

**Acceptance before trusting it for real steering:** human post during a provider run reaches the next shell; post during a runner-slot wait lands in the post-admission snapshot; subscriptions survive fresh pipe, monitor/gate handoff, promotion, and workspace recovery; two families hold independent cursors; concurrent posts/identical timestamps/retries neither lose nor duplicate; crash-before/after-persist yields explainable pending-or-replay; author override cannot impersonate human steering; dead family / pending gate / drained provider reads as unattainable, not eventually-delivered.

**Trial metrics:** missed messages, replay rate, receipt latency, prompt bytes, manual reminders avoided, duplicate consequential actions (must be zero — dedupe keys cover posts, idempotency keys or result-inspection cover actions), and whether communicated information changed the next cycle's decisions. Continue investing if automatic delivery reduces manual coordination and survives a forced handoff failure; otherwise stop at bounded manual views.

## 6. Risks and caveats

- My code inspection was a bounded first-hand pass (family/clan formatting, tribe xprompt, swarm parsing, fork workflow, mentor config, monitor follow-up surface) plus audited reads of the two prior syntheses; I did not re-verify competitor claims or star counts and take no position on them beyond what the lead synthesis established.
- The channel design inherits the family-channel synthesis's open tuning questions (budgets, retention, SQLite durability policy — WAL with `synchronous=NORMAL` can lose recent commits, so durable-post claims need `FULL` plus tested recovery).
- Cross-user collaboration (identity join keys, inbound review ingestion, attention routing) is out of scope here and covered by the collaboration-architecture report; nothing above crosses a user boundary except as an artifact, per that report's rule.

## 7. Key sources

- Context (read via `sase artifact read` before writing): `research:202609/multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md` (lead synthesis, 2026-09-21); `research:202609/family_channel_delivery/family_channel_delivery.md` (lead synthesis, 2026-09-07); `research:202609/sase_collaboration_architecture.md` (2026-09-04).
- Code (sase @ `c6807d24c`): `src/sase/history/chat_fork/family.py`, `clan.py`; `src/sase/xprompts/tribe.md`, `fork.yml`; `src/sase/agent/_xprompt_swarm_parsing.py`, `xprompt_swarm.py`, `multi_prompt_launcher.py`; `src/sase/config/mentor.py`; `src/sase/monitor/followup_prompt.py`; `src/sase/xprompt/processor.py` (deferred names, via prior synthesis).
- External patterns cited: NATS JetStream pull consumers / acknowledgments; PostgreSQL LISTEN/NOTIFY subscribe-then-inspect; Anthropic multi-agent forum research (benefits alongside coordination failures — argues for a measured trial, not maximal messaging).
