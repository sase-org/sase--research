# Gastown vs SASE: Where Gastown Is Better

Researcher: mus (independent swarm report, `__mus`).
Date: 2026-10-16. Method: static study of the gastown checkout
(`gh:gastownhall/gastown` at `649b832b`, 2026-07-23) — README, `docs/`,
command inventory (`internal/cmd`, 457 files), and selected implementation
headers — compared against the sase workspace (v0.17.1+), its docs, and live
`sase --help` output. No live gastown town was booted; claims about runtime
behavior are marked where they rest on docs/code rather than observation.
Peer swarm reports were not consulted.

## The two philosophies in one paragraph

Gastown builds a town that runs itself: a Mayor coordinates, per-rig
Witnesses supervise worker agents (polecats), a Deacon patrols the whole town,
Dogs do infra chores, and a Refinery merges finished work through a queue —
all over tmux, with git worktrees, beads, and a Dolt SQL backend underneath.
SASE builds a team you supervise: parallel agents in isolated numbered
workspaces, launched and watched from a keyboard-driven TUI, with Patches,
beads, macros, ToolRuns, Goals, and the AXE scheduler tracking everything for
human review. Gastown optimizes for **autonomous multi-agent operation**;
SASE optimizes for **dependable human-supervised engineering**. Nearly every
gastown advantage below is a consequence of that choice — and the
recommendations ask which of those SASE wants without abandoning its
human-in-the-loop core.

## Ranked: ways gastown is superior to sase

### 1. Autonomous agent supervision (Witness / Deacon / Dogs + heartbeats)

Gastown's three-tier watchdog is its single biggest structural advantage.
Each rig has a persistent **Witness** (polecat lifecycle manager: detects
stuck agents, triggers recovery, manages session cleanup); a town-wide
**Deacon** runs continuous patrol cycles across all rigs; **Dogs** are
short-lived infra workers the Deacon dispatches (e.g. Boot triages Deacon
health, stuck-agent-dog cross-checks heartbeats against tmux activity before
escalating). Liveness rests on **three distinct heartbeat stores**
(`docs/concepts/heartbeats.md`: Deacon heartbeat file, per-session state
store, agent-bead `heartbeat:` label) with an explicit rule to never declare
an agent stuck from a single store. SASE supervises through the human-driven
TUI plus AXE scheduler jobs (hook checks, wait checks, error digests) — good
coverage, but there is no dedicated per-project lifecycle manager whose *job*
is noticing a stranded agent and recovering it. When SASE's human looks away,
nothing is on watch; in gastown, something always is.

### 2. A real merge pipeline (Refinery + Bors-style merge queue)

Finished polecat work flows through a per-rig **Refinery**: `gt done` pushes
the branch and submits to the merge queue (`internal/cmd/mq.go`: submit,
retry, reject, status, post-merge cleanup), the Refinery batches requests,
runs verification gates, and merges with a Bors-style bisecting queue —
failed MRs are isolated and either fixed inline or re-dispatched, and
`mq integration` manages integration branches for epic-scale batch work.
SASE's `sase stitch create` dispatches a commit/proposal/PR and host-owned
finalizers act on it, but there is no autonomous verification-gated landing
queue: every landing is effectively a human-reviewed PR event. At 20–30
parallel agents, gastown's queue is load-bearing infrastructure; SASE has no
equivalent and would serialize on human review bandwidth.

### 3. First-class inter-agent communication (mail + nudge + handoff)

Gastown agents talk to each other without a human relay: `gt mail` is a full
agent messaging system (send, inbox, read, peek, reply, thread, archive,
claim/release queue semantics, broadcast, groups — see `internal/cmd/mail*.go`
and `docs/design/mail-protocol.md` with typed protocol messages
`POLECAT_DONE` / `MERGE_READY` / `MERGED` / `MERGE_FAILED` forming the
polecat→Witness→Refinery completion chain), and `gt nudge` delivers a message
directly into another agent's live session. SASE agents have TUI-visible chats
and patch comments, but those are human-observation surfaces and review
artifacts — there is no agent-to-agent mailbox, no typed completion protocol,
no way for one run to signal another. SASE's coordination topology is
hub-and-human; gastown's is a mesh with a protocol.

### 4. Universal identity, attribution, and agent work history (CVs + costs)

Every gastown agent has a slash-path identity (`gastown/polecats/toast`,
`gastown/crew/joe`, `{rig}/witness`) stamped via `BD_ACTOR` into git commits
(author = agent, email = overseer), beads records, and event logs
(`docs/concepts/identity.md`, `docs/why-these-features.md`). Identity is
permanent across sessions (polecat lifecycle's identity layer: agent bead, CV
chain, mailbox — never deleted), queryable (`bd audit --actor=…`,
`bd stats --actor=… --tag=go`), and costed (`gt costs` sums Claude transcript
tokens with per-role/per-rig breakdowns plus digest beads). SASE tracks runs,
Patches, ToolRuns, and provider-level subscription usage (`sase usage`), and
has a permanent agent-name registry — but attribution answers "which run,"
not "which agent, and is it any good." Gastown's ledger turns agent quality
into data (including A/B-testing models on completion rates); SASE cannot do
that analysis today.

### 5. Session recovery designed as the normal path (prime + seance + handoff)

`gt prime` is the recovery ritual: after any compaction, clear, or new
session the agent runs one command and gets role context, assignment, and the
inline formula checklist back (SessionStart hook runs `gt prime --hook`,
`docs/HOOKS.md`). Predecessor interrogation is a feature (`gt seance --talk`:
resume a prior session's context to ask what it tried and where it got
stuck). Handoff markers preserve state across session cycles, and session
cycling mid-assignment is treated as *normal operation*, not failure
(`docs/concepts/polecat-lifecycle.md`). SASE has restart/resume/retry chains
and prompt persistence, but recovery is an operator action, not an
agent-executed ritual wired into session start. Gastown assumes sessions die
constantly and makes resurrection cheap and self-serve.

### 6. Crash-resilient workflow templates (molecules/formulas, pour heuristic)

Molecules separate template (Formula TOML) from instance, with two execution
modes behind one memorable heuristic — *"if you would curse losing the
progress after a crash, set `pour = true`"*: root-only wisps stay lightweight
(steps rendered inline at prime time, ~400 rows/day instead of ~6,000+), while
poured wisps materialize steps as sub-wisps with checkpoint recovery so work
resumes from the last checkpoint after a session death
(`docs/concepts/molecules.md`). SASE macros are arguably the stronger reuse
story (generated skills, catalog, graph, LSP), but they are prompt-reuse plus
orchestration, not crash-recovery semantics: a long macro workflow that dies
midway restarts, it does not resume. Gastown's contribution is the durability
model, not the templating.

### 7. Severity-routed escalation from agents to humans

`gt escalate -s CRITICAL|HIGH|MEDIUM` creates a tracked escalation bead routed
Deacon → Mayor → Overseer, each tier resolving or forwarding, with
stale-detection plus automatic re-escalation (capped) and out-of-band routes
(email, SMS, Slack) per severity (`docs/design/escalation.md`,
`~/gt/settings/escalation.json`). SASE's notifications are a sophisticated
human-facing inbox (rules, tabs, gates, mobile gateway) — but the direction
is system→human display, and nothing in SASE gives an *agent* a graded
"I'm blocked, come running / come soon / at your convenience" lever with
accountability when nobody answers. (Verified: sase-side "escalat*" hits are
signal-escalation and wait-budget blocks, unrelated.)

### 8. Batched cross-project tracking with landing semantics (convoys)

A **convoy** is a persistent unit tracking related issues across rigs with a
dashboard, auto-reopen on new arrivals, and auto-notification when everything
lands; the "swarm" is just the ephemeral worker set (`docs/concepts/convoy.md`,
`gt convoy create/status/list`, plus a web dashboard). Mountain-labeled
convoys add autonomous stall detection and smart skip for epic-scale runs.
SASE's Patches track PR-sized units superbly within a project and goals track
outcomes, but neither is a cross-project "tell me when this whole batch has
landed" object with its own lifecycle and notification. For multi-repo fan-out
— SASE's own headline scenario — convoys are the missing tracking shape.

### 9. Distribution and platform breadth

Gastown ships a single Go binary via Homebrew (`brew install gastown`
installs `gt` + `bd` + `dolt` together), `go install`, an npm package, and a
Docker Compose path, and documents Linux, macOS, *and* Windows paths. SASE
requires Python 3.12+ via `uv`, prebuilt `sase-core-rs` wheels, and is
explicitly POSIX-only ("Windows is not supported," README + INSTALL.md).
The honest counterweight: gastown's footprint is heavy (Go toolchain, Dolt
server on port 3307, tmux, sqlite3, ICU headers for source builds), while
`uv tool install sase` is lighter on its supported platforms. Breadth is the
win, not lightness.

### 10. Scriptable fleet-health surface for headless operation

`gt doctor --fix`, `gt health`, `gt vitals` (unified dashboard), tmux
`status-line`, `gt activity` / `feed` / `trail`, per-rig `witness`/`refinery`
status, and an OpenTelemetry data model (`docs/otel-data-model.md`) give a
composable CLI health story that works over SSH with no terminal UI. SASE's
`sase doctor` plus the TUI is excellent interactively, but the TUI is the
observability flagship — headless fleet checks are thinner. Gastown's
`--robot-*` flags on `bv` (triage/next/plan/alerts/insights as machine output)
show the same philosophy: every view an agent can read, a script can parse.

### 11. Capacity-governor ergonomics (not power — simplicity)

One config value flips the whole dispatch model: `scheduler.max_polecats`
unset means direct dispatch with near-zero overhead; set to N and every
`gt sling` (single, batch, convoy, epic) transparently becomes deferred,
daemon-dispatched work under the cap (`docs/design/scheduler.md`). SASE's AXE
is the more powerful scheduler (orchestrator + routines + script-jobs with
declarations, service host with systemd/launchd units, OOM-hardening) — this
is *not* a power gap. The gap is ergonomics: gastown's back-pressure story is
one knob with a sensible default; SASE's requires understanding the
routine/job tree. Worth stealing the knob, not the engine.

### 12. Maintenance-as-agents (dog/plugin pattern)

Infra chores are bounded agents with persistent identity, not just scripts:
stuck-agent-dog, compactor-dog, git-hygiene, quality-review, dolt-backup,
submodule-commit (`plugins/`). SASE scheduler jobs cover similar ground
(housekeeping routines, disk pressure, tmp reap), and jobs-that-propose plus
runner-launches-agents is a principled design — but gastown's framing (a dog
*is* an agent with a name, a CV, and attribution) means maintenance work is
audited the same way product work is. Small modeling choice, real
accountability dividend.

## Where sase is stronger (do not "fix" these)

Fairness requires the other side, briefly: SASE supports more providers
(Claude, Codex, Antigravity, Qwen, OpenCode, Muse, Grok vs gastown's Claude /
Copilot / Codex / Gemini / Cursor); per-invocation memory-built instruction
bundles are a deeper context story than `gt prime` role context; the TUI's
human supervision depth (retry chains, per-agent diffs, gates, patch review
pipeline with stitches) exceeds gastown's tmux+browser dashboard for
reviewability; and durable Goals plus the Rust-core boundary are architectural
assets gastown has no analogue for. Recommendations below deliberately avoid
trading these away.

## Ranked recommendations for sase

1. **Add a per-project agent supervisor to AXE.** A Witness-equivalent routine
   set — stuck-run detection (heartbeat + last-output-activity cross-check,
   per gastown's never-one-store rule), recovery (nudge/retry/respawn), and
   session cleanup — is the highest-leverage import. It covers SASE precisely
   when the human looks away. Fits AXE's routine/job model; start with
   detection + digest before auto-recovery.
2. **Give agents a graded escalation lever to the human.** Severity-routed
   blocked-runs (urgent/soon/convenience) with stale detection and
   re-escalation, delivered through the existing notification rules engine.
   Reuses `sase notify`; adds the missing agent→human urgency protocol.
3. **Add a scoped agent-to-agent mailbox.** Not full email: typed run signals
   (done/blocked/needs-input) plus claim/release queue semantics that the
   scheduler and `%wait` checks can consume. Closes the mesh gap without
   importing gastown's whole mail system; decide explicitly against
   free-text agent chat (phishing/loop risk SASE currently avoids by design).
4. **Grow the agent-name registry into persistent identity + CVs.** `sase agent
   names` already exists — attach per-name work history (patches landed,
   reviews, reliability), stamp agent identity into stitch commits, and extend
   `sase usage` from provider-level to per-agent cost attribution. Unlocks
   quality analytics and model A/B comparison.
5. **Prototype a verification-gated landing queue for stitches.** Batch +
   verify + bisect-on-failure behind a feature flag, for the multi-agent
   fan-out SASE advertises. Keeps human review as the default; the queue is
   the high-throughput option, not the replacement.
6. **Add a convoy-shaped batch tracker.** A cross-project "these issues,
   one landing" unit (epic-adjacent, with landing notification) for multi-repo
   fan-out. Likely a thin bead type + TUI panel + notify rule, not a new
   subsystem.
7. **Make recovery an agent-executed ritual.** A `prime`-equivalent: one
   command (or session-start hook content) that restores role, assignment, and
   next steps after compaction, plus predecessor notes via prompt history
   (seance-lite). Pairs with recommendation 6's checkpoint idea.
8. **Add checkpoint-resume semantics to long macro workflows.** A `pour`
   equivalent: materialize step state so a dead workflow resumes instead of
   restarting. Start with long-running built-ins (release, migration) where
   crash cost is highest.
9. **Ship a scriptable fleet-health CLI surface.** Machine-readable
   vitals/health output (JSON) covering agents, scheduler, service procs, and
   disk — the headless complement to the TUI, in the spirit of `--robot-*`.
10. **Add a one-knob capacity governor.** A single config flip between direct
    dispatch and queued dispatch under a concurrency cap, layered over the
    existing runner slots — AXE keeps the power, operators get the knob.
11. **Revisit distribution deliberately — and probably decline Windows.**
    The POSIX-only stance looks increasingly costly next to a brew-installable
    single binary, but SASE's tmux/systemd/launchd-adjacent assumptions run
    deep. Recommendation: document the decision and its cost (this report is
    input), consider a static-binary or container story for Linux/macOS first,
    and treat Windows as an explicit non-goal until a sponsor appears.
12. **Model infra maintenance as named agents.** When scheduler jobs act
    (housekeeping, triage, digests), attribute the action to a persistent
    named identity with history — dogs in spirit, AXE jobs in implementation.

## Caveats

- No live gastown town was run; lifecycle, merge-queue, and escalation
  behavior is attested by docs + code, not observed. Several gastown features
  are honestly marked planned/not-implemented in their own docs
  (capability routing, federation/HOP, Witness-on-Agent-Teams) and were
  excluded from the rankings above.
- Dolt-as-sole-backend (SQL server per town, no embedded/SQLite mode) is
  gastown's deepest architectural bet and its biggest ops liability; SASE's
  git-portable beads + Rust core is the more conservative, more portable
  store. None of the recommendations import Dolt.
- Single-researcher, single-evening study: rankings reflect judgment about
  what matters to SASE's stated mission (dependable supervised engineering),
  not a feature count.
