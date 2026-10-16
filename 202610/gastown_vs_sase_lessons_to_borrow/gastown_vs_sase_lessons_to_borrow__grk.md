---
create_time: 2026-10-16
updated_time: 2026-10-16
status: complete
researcher: grk
tags:
  [
    research_swarm,
    gastown,
    sase,
    multi-agent,
    orchestration,
    comparison,
  ]
sources:
  - gh:gastownhall/gastown@649b832b7672bc7a2dbef26f5983aba6198b819b
  - sase docs in the current project checkout
---

# Where Gas Town beats SASE

**Question.** Compare SASE with [Gas Town](https://github.com/gastownhall/gastown), with particular focus on the things Gas Town does better. Rank those advantages, then rank recommended SASE changes that follow from them.

**Researcher.** grk (`research.1u.grk`). Independent report. I did not read peer reports from this swarm.

**Checkout studied.** `gh:gastownhall/gastown` at `649b832b` (2026-07-23, `v1.2.1-304-g649b832b`). GitHub API on 2026-10-16: 18,390 stars, 1,687 forks, 506 open issues, default branch still at that July commit.

## Bottom line

Gas Town is a **living town of specialized agents** whose work, identity, and mail live outside any one context window. SASE is a **cockpit for one developer supervising many single-turn agents** across real repos, with host-owned landing. Those are different products. Gas Town is still the clearer sketch of several primitives SASE has not built: durable assignment hooks with a propulsion contract, typed inter-agent mail, persistent named worker identity with a CV, cheap worktree sandboxes under a town/rig HQ, a three-tier AI watchdog, a dedicated merge-queue role, session recovery (`gt prime` / `gt seance`), and operator-overridable formula checklists.

Yegge later stopped running Gas Town as his own harness, and `main` has been quiet since 2026-07-23. That is a warning about cost, vibe-designed complexity, and agents that nibble the orchestrator. It does not erase the primitives. The useful move for SASE is to steal those primitives in SASE shape: durable work and supervision that survive a turn, without making always-on tmux Claude sessions the default runtime.

## Method and sources

I opened the Gas Town GitHub repo through `sase repo open`, read the README, overview, architecture, polecat lifecycle, mail protocol, convoys, molecules, escalation, scheduler, hooks, identity, heartbeats, propulsion, Wasteland, Dolt storage, role directives, plugin tree, formulas, `gt prime` / `gt seance` implementations, and CHANGELOG. I compared those against SASE's public docs (agents, workspaces, beads, plans, patches, AXE, monitors, macros, instruction bundles, doctor, auto-restart, pipe, chat, telemetry, commit workflows) and SASE's own Gas Town discussion in `docs/blog/posts/why-coding-agents-need-orchestration.md`. External context: Yegge's launch essay, Maggie Appleton's field analysis, GitHub API metadata, and later reporting on Yegge's shutdown and successor orchestrator.

I treated design docs marked "planned" or "not yet implemented" as intent, not capability. Capability routing, HOP federation, sandboxed polecat backends, and Witness-as-Agent-Teams are in that bucket. Plugins, mail, prime, seance, doctor `--fix`, convoys, sling, and the watchdog chain have code and changelog evidence.

## What each system is

### Gas Town

Gas Town (`gt`, Go, MIT, first commit 2025-12-16, open-sourced 2026-01-01) is Steve Yegge's multi-agent workspace manager. A **town** (`~/gt/`) holds many **rigs** (git projects). Persistent AI roles run in tmux: a town-wide **Mayor** (coordinator you talk to) and **Deacon** (patrol supervisor), plus per-rig **Witness** (worker lifecycle) and **Refinery** (merge queue). **Polecats** are named workers with permanent identity and ephemeral sessions; **crew** are long-lived human-managed clones. Work is **beads** in a per-town Dolt SQL server. Assignment is a **hook**. Coordination is **mail** plus **nudge**. Batch tracking is a **convoy**. Repeatable jobs are **formulas** rendered by `gt prime`.

Yegge's launch line: you are a product manager, Gas Town is an idea compiler, and the Mayor is the concierge. The operating law is GUPP: if work is on your hook, you run it. NDI (nondeterministic idempotence) is the reliability bet: unreliable agents plus persistent ledger plus watchers eventually finish the work.

The tree I studied is large: about 475k lines of Go, 457 files under `internal/cmd/`, ~50 bundled formulas, 13 plugins. Latest release `v1.2.1` (2026-06-06). Homebrew formula, Docker Compose HQ, web dashboard, `gt feed` TUI, OTEL export, Wasteland federation (Phase 1).

### SASE

SASE is a local control surface for delegated coding agents. A prompt or macro launches a **single-turn agent** in an isolated numbered **workspace** (full clone). Related turns can chain as a **session**; parallel runs group as **clans** and **tribes**. Work records are **beads**, **plans**, **goals**, **patches**, and **stitches**. The **host** commits, lands, and runs finalizers. **AXE** runs script-only scheduler jobs. **Gates** collect human decisions without blocking the agent that created them. **Macros** are programmable prompt workflows (agent, Bash, Python). **Instruction bundles** deliver per-invocation memory. The TUI, Telegram, and CLI are how a person supervises the fleet.

SASE already credits Beads and Gas Town as influences, then asks a narrower product question: the right local interface for one developer supervising many agents across real diffs, plans, and PRs.

## Comparison frame

A fair comparison has to hold two facts at once.

**Gas Town's architecture is more ambitious about autonomous multi-agent physics.** Specialized living roles, git-backed assignment, mail, identity, and a merge factory are designed as one machine. SASE's architecture is more ambitious about *supervision*: isolation, provenance of launches, host-owned landing, verification receipts, memory audit, and a cockpit that stays understandable when many models run.

**Gas Town's implementation is a cautionary tale.** Appleton called it vibe-designed as well as vibe-coded: overlapping metaphors, baptism-by-fire onboarding, thousands of dollars a month, agents that stall and invent their own rules. Yegge warned people not to use it, then later stopped using it himself; secondary reporting in September 2026 (Latent Space AINews citing Dan Luu) said he shut the personal town down after Gas Town was the main thing the spend produced. On 2026-10-07 he posted that he had made a better orchestrator and was working on open-sourcing it, with Beads still central. `gastownhall/gastown` `main` has had no commit since 2026-07-23. Kilo shipped a hosted "Gas Town by Kilo" in May 2026, so the *product category* is still alive even if this repo is quiet.

The rest of this report ranks **architectural advantages that are real in the Gas Town design and, where noted, shipped in the July 2026 tree**. It does not recommend cloning the Mad Max taxonomy or the always-on tmux bill.

## How Gas Town is stronger

### 1. Work is a hook, and the contract is to run it

Gas Town's most important idea is smaller than Mayor/Polecat folklore. Each agent has a **hook**: a pinned assignment that survives crash, compaction, and session recycle. GUPP says the hook *is* the assignment. Startup is: check hook, execute; if empty, check mail; if still empty, escalate. `gt prime` reprints role, identity, formula checklist, and pending mail. `gt handoff` is a normal way to cycle a filled context window. Session death is expected.

SASE already has bead claims, `%wait`, monitors, pipe, and host-owned successors. Those are launch-time and turn-boundary mechanisms. The assignment lives in the prompt and the bead store; the running agent does not wake up, look at a hook, and continue without a new mechanical turn. Auto-restart exists, and it is narrow: update-skew healer, one retry per lineage, rate-limit deaths declined. There is no first-class "this identity has hooked work, so the next turn must execute it immediately."

That gap shows up as idle, over-asking, and stranded in-progress beads. Gas Town spent a lot of code fighting the same failure (agents announcing themselves and waiting). The primitive still looks right: **durable assignment plus a no-wait contract**, with watchers that treat hooked-and-silent as a GUPP violation.

### 2. Agents talk to agents through mail and nudge

Gas Town splits communication into two layers that match two physics:

- **`gt mail`**: persistent, Dolt-backed, typed. Message beads survive restarts. The protocol is operational, not chatty: `POLECAT_DONE`, `MERGE_READY`, `MERGED`, `MERGE_FAILED`, `REWORK_REQUEST`, `RECOVERED_BEAD`, `RECOVERY_NEEDED`, `HELP`.
- **`gt nudge`**: immediate injection into a living tmux session. The documented rule is explicit: never print "Hey @name" into a terminal the other agent cannot see.

Hooks inject mail on `UserPromptSubmit` and re-prime on `SessionStart` / `PreCompact`. Cross-rig delivery uses bead prefix routing.

SASE's counterparts are strong for *humans and successors*: artifact references (`@agent:…`), `sase pipe`, questions, gates, notifications, bead notes, clan `%wait`. They assume the next reader is a new turn or a person. There is no mailbox addressed to `sase/polecats/toast` that a later turn of that identity drains on startup. Living-session nudge is mostly unavailable because SASE agents are single-turn.

Mail is the piece I would steal first. It works even if agents stay single-turn: the next member of an identity reads the inbox during instruction-bundle / prime.

### 3. Identity persists; sessions die

Gas Town separates three layers that SASE still partly conflates:

| Layer | Gas Town | Lifecycle |
| --- | --- | --- |
| Identity | Agent bead, `BD_ACTOR`, mailbox, CV | Permanent |
| Sandbox | Git worktree / branch | Per assignment |
| Session | tmux + model context | Ephemeral, cycled on purpose |

A polecat named Toast keeps a CV across jobs. Git author is `gastown/polecats/toast`; email is the overseer. Beads store `created_by` / `updated_by`. Events carry `actor`. `bd audit --actor=…` and `bd stats --actor=…` are the intended quality loop. Capability-based routing is still planned; the ledger that would feed it is already being written.

SASE run names (`research.1u.grk`, numbered workspaces) are excellent for *this turn's* provenance. Host-owned stitches record which agent produced a commit. Git author is still the human. There is no durable worker named Toast whose Go-refactor batting average you can query, and no environment convention that stamps every bead and commit with `project/role/name` automatically.

Appleton's summary of this pattern matches Anthropic's long-running-agent harness advice: keep identity and tasks outside the window, kill sessions freely. SASE already kills sessions (single-turn). It does not yet keep a first-class worker identity on the other side of that kill.

### 4. The town is one HQ; workers are worktrees

A Gas Town HQ is a multi-project control plane:

- Town beads (`hq-*`) for mail, convoys, Mayor/Deacon identity.
- Rig beads (`gt-*`, `bd-*`, …) behind prefix routes in `routes.jsonl`.
- One Dolt SQL server, all agents `USE` the right database, write `main` under transactions, see each other's writes immediately.
- Polecats and refinery are **worktrees** of `mayor/rig`. Crew are full clones for humans.
- `.beads/redirect` makes every worktree share the canonical ledger.

SASE projects are first-class, and a full bead ID can route to another enabled project's store. Each agent still gets a **full numbered clone**, plus nested linked/sidecar/external clones. That isolation is a real safety feature. It is also why "comfortably 20–30 agents" is a Gas Town slogan and a SASE cost center: clone time, disk, and eviction/rescue policy all sit on the workspace allocator.

Worktrees plus a shared live ledger are how Gas Town makes swarming cheap. SASE's event-sourced bead store (JSONL streams, sidecar clones, pull-based sync, machine-link writes off the primary) is more careful about workspace identity and git. It is slower to converge as a *multi-writer bulletin board* than Dolt-on-port-3307.

### 5. Specialized supervisors are agents, not only scripts

Gas Town's watchdog chain is:

```
Go daemon (heartbeat ~3 min)
  → Boot (AI triage dog)
    → Deacon (AI town patrol)
      → Witness / Refinery (AI per-rig)
        → Polecats (AI workers)
```

Witness looks at self-reported session heartbeats, tmux activity, and hooked work. Stuck-agent-dog cross-checks stores so a stale heartbeat file plus a live pane is "heartbeat-write divergence," not a kill. Quota-limit signatures apply backoff instead of burning the crash-loop budget; `quota_dog` rotates accounts. `gt feed --problems` groups GUPP violations, stalled, zombie, working, idle, and binds keys to nudge or handoff.

SASE's AXE orchestrator is a serious process supervisor: routines, jobs, crash restart, Patch lifecycle, mentors, waits, housekeeping. Jobs are **script-only**; they may *propose* agent launches, and the runner launches them. Auto-restart heals update-skew. Doctor is mostly read-only (two narrow `--fix-*` flags). The Agents tab shows run state, queue load, and holds. There is no AI Witness whose job is "walk this rig, find hooked-and-silent workers, recover or escalate."

Yegge's later complaint — agents spent too much time tinkering with the orchestrator — is a reason to keep SASE's "scripts propose, runner launches" split. It is also a reason to add **bounded patrol turns** with a fixed formula, not a reason to skip supervision-as-work.

### 6. Landing is a factory role

Polecats are forbidden to push `main`. The contract in `mol-polecat-work.formula.toml` is: work the checklist, pre-verify after rebase, `gt done` (push branch, submit to merge queue, retire the session). Refinery owns main health, batch-then-bisect (Bors-style), conflict rework mail, and issue close after merge.

SASE landing is host-owned and that is a feature: `/sase_final` → `builtin@commit` → stitch / Patch, mentors, lander macros, review gates. What Gas Town still does better is **separating implementer from merger as roles**, plus a queue that bisects a red stack instead of failing the whole batch. SASE can grow a Refinery-shaped lander without giving workers push access.

### 7. Recovery is a product surface: prime and seance

`gt prime` is a 1,476-line command that rebuilds role context, directives, overlays, formula checklist, hook, and mail. Agents are told to run it after compaction, clear, or new session. SessionStart and PreCompact hooks run it for them.

`gt seance` discovers predecessor sessions from `.events.jsonl` and can spawn `claude --fork-session --resume <id>` so the new agent *asks the old one* where it put things. That is a different object from a transcript file.

SASE instruction bundles already inject a high-quality per-invocation brain. `sase chat list/show` and the agents sidecar store transcripts. Pipe can fork with inherited chat. None of those is "reload my live assignment" or "interview the predecessor session's full context." After compaction or a killed turn, SASE's next agent rereads docs and chats; Gas Town's next agent is told it is still Toast, still on issue `gt-abc`, with mail waiting.

### 8. Formulas are the current job, with operator overrides

Gas Town formulas are TOML checklists bound to the hooked assignment. `gt prime` inlines the steps. Root-only wisps keep high-frequency patrols from exploding the ledger; `pour = true` materializes checkpoints for expensive flows (releases). Town and rig **role directives** (Markdown) and **formula overlays** (replace / append / skip steps, with DAG repair on skip) let an operator change "post the GitHub review" to "report back" without forking the binary. Contrib harnesses include a polecat-PR-flow that swaps Refinery for GitHub review.

SASE macros are more powerful as programs: they mix agent, Bash, and Python, branch, parallelize, and validate. They are launch-time workflow, not the worker's in-session checklist, and they lack CSS-like per-project step overlays with an authority marker ("Rig Policy — overrides formula instructions where they conflict").

### 9. Convoys, escalation, and capacity are named objects

Three operational objects Gas Town named that SASE covers only in pieces:

- **Convoy** (`hq-cv-*`): a persistent tracker over beads in many rigs. Lands when all issues close, notifies subscribers, can reopen if you add work. Cross-rig "when does this batch land?" SASE epics, clans, and patches are close; they are not a first-class cross-project landing object with subscribers.
- **Escalation**: `gt escalate -s HIGH "…"`. Severity routes (bead + mail + email + SMS), ack, stale threshold (default 4h), automatic re-escalation with severity bump, plugin and patrol sources. SASE gates and notifications are a better *human* attention bus. Agents still lack a first-class "I am stuck, page the chain, re-page if ignored."
- **Scheduler**: `scheduler.max_polecats` turns `gt sling` into deferred dispatch. Sling-context beads track the queue without mutating the work bead. Daemon heartbeat step 14 dispatches under capacity after health checks. Circuit breaker on repeated dispatch failure. SASE runner slots cap *running agents*. Gas Town caps *spawned workers against a work queue and API budget*.

### 10. The default UX is "talk to the Mayor"

Gas Town's recommended loop is MEOW: tell the Mayor what you want; it creates a convoy, slings beads, spawns polecats, and summarizes when the convoy lands. Discussion #282 (Crew as per-rig context, Mayor as sling coordinator) is the community refinement: Mayor stays relatively context-free; crew holds domain knowledge.

SASE's TUI is a better cockpit for inspecting prompts, diffs, patches, and gates. Activation energy is higher: compose a prompt or macro, pick models, launch a stack, follow rows. There is no always-available coordinator session whose only job is to turn English into slung work across projects.

### 11. Doctor `--fix`, OTEL, and quota-aware recovery

`gt doctor --fix` mutates: orphan sessions, wisps, beads redirects, tmux env, daemon, CLAUDE.md, foreign remotes, misnamed sessions. SASE doctor is deliberately read-only except for two confirmation-gated Patch/link repairs. For a machine that runs many agents, auto-repair of *harness* rot is a real advantage.

Gas Town emits session lifecycle, sling/nudge/done, mail, polecat spawn, formula instantiation, convoy create, and daemon restarts to any OTLP backend. SASE telemetry is excellent *locally* (SQLite in the Rust core, health thresholds, Admin Center stats). It does not ship an ops-style OTLP stream of agent operations.

Quota handling in the July tree is specific: stuck-agent-dog reads usage-limit signatures in the tmux pane, backs off, and lets account rotation work. SASE tracks usage windows and can auto-disable a provider at a limit. It does not rotate accounts or treat a usage pause as a healthy stall.

### 12. Things that look like advantages and are weaker than the README

Honesty check, because a ranked "Gastown is superior" list that copies the README would be wrong:

- **Wasteland / federation.** Phase 1 wild-west on DoltHub. HOP-style federated `bd list --remote` is still planned. Portable reputation is a good idea; it is not a reason to build a work market before SASE's local fleet is healthy.
- **Capability routing.** Documented as planned. The CV ledger is the actual asset.
- **Sandbox / Daytona / satellites.** Design docs and issue #2801. Current polecats run as the user in tmux with full host credentials. SASE numbered workspaces plus repo-open audit are *safer isolation today*.
- **Plugin system design doc** says "not yet implemented"; `plugins/` and CHANGELOG show stuck-agent-dog, quota, dolt-backup, git-hygiene, and others in production. Treat the directory as source of truth.
- **Merge-queue phases** in `architecture.md` still list some beads as in progress. `gt done` + Refinery + rework mail exist; do not assume a finished Bors clone of Chromium's queue.
- **Scale slogan (20–30 agents).** Hardware, tmux, and token cost are the real limiter. Appleton's cost band ($2k–$5k/month in early 2026, with anecdotes of ~$100/hour) is part of the design. SASE's runner-slot budget is the more adult default.

## Ranked ways Gas Town is superior to SASE

Rank is "how much this would change SASE outcomes if stolen well," given SASE's existing cockpit, beads, macros, and host-owned landing. Shipped-in-July unless marked.

1. **Durable hook + GUPP (propulsion).** Assignment survives the session; hooked work is mandatory. SASE's next turn is a new prompt. This is the largest behavioral gap.
2. **Typed persistent agent mail.** Operational messages between identities, drained on prime. SASE hands context to successors and humans; agents do not have a mailbox.
3. **Persistent named identity + CV + git/bead attribution.** Toast remains Toast. SASE attributes *runs* well and *git authors* as the human.
4. **Cheap worktree workers under a town/rig HQ with live shared ledger.** Swarming is an allocation problem. SASE full clones and pull-synced bead stores make 20 workers expensive and eventually consistent.
5. **AI supervisor chain with a problems view (GUPP / zombie / stalled).** AXE scripts and auto-restart do not patrol hooked-and-silent work.
6. **`gt prime` + `gt seance` as normal recovery.** Instruction bundles and `sase chat` are weaker at "you are still this role, here is your hook, ask your predecessor."
7. **Implementer / merger split with a bisecting merge queue.** SASE host landing is safer; Gas Town's Refinery role and batch-bisect are the missing factory.
8. **Mayor as the default conversational dispatcher.** Lower activation energy than composing a TUI stack for every swarm.
9. **Formulas-as-current-job plus directives/overlays.** Operator policy without forking macros; in-session checklist after crash.
10. **Convoy as cross-project landing tracker with notify-on-land.**
11. **Agent-initiated severity escalation with stale re-page.** Complements SASE gates rather than replacing them.
12. **Work-queue capacity governor (`max_polecats`, sling contexts).** Complements runner slots (process cap) with dispatch cap.
13. **`gt doctor --fix` for harness rot.**
14. **Immediate nudge into a living session.** Only a Gas Town win while sessions are long-lived; still the right idea for SASE session members.
15. **OTLP export of agent operations, plus quota-pause as a healthy state.**
16. **Docker-compose HQ.** Useful packaging; SASE's host-native TUI/Telegram story is already richer for daily use.
17. **Wasteland-style federated wanted board.** Interesting, early, and below the local-fleet gaps.

## Ranked recommended changes for SASE

These are SASE-shaped. They keep single-turn agents, host-owned completion, and non-blocking gates. They steal Gas Town's durable-work and supervision physics. Rank is implementation leverage versus risk.

1. **Hooked work as a first-class bead/agent state, with a GUPP successor.** When a bead is hooked to an identity, the next turn of that identity (or a designated worker slot) starts with the hook, mail, and formula/checklist already in the instruction bundle, and is told to execute immediately. Treat hooked-and-silent past a threshold as a problems-view row, not as a healthy idle agent. This is GUPP without always-on tmux.

2. **Agent mailboxes.** Typed, persistent messages addressed to `project/role/name` or a session identity. Drain on launch (bundle section) and on session-member start. Start with a small closed vocabulary: `DONE`, `REWORK`, `HELP`, `HANDOFF`, `RECOVERED`. Keep `sase pipe` for same-workspace succession; use mail for cross-run and cross-project coordination.

3. **Durable worker identities with CVs.** A named worker (role + slot) that outlives `sase_18`-style workspace numbers. Stamp stitches, bead events, and optionally `GIT_AUTHOR_NAME` with that identity while keeping the human email and host commit. Expose `sase agent cv <id>` from existing stitch/bead/run records before building a new store.

4. **Worktree workspaces for polecat-class jobs.** Keep full clones for crew-class / human-adjacent work and for repos that need independent remotes. Add a workspace flavor that is a git worktree of a canonical project clone, with beads redirected to the project store. This is the scalable path to double-digit parallel workers on one machine.

5. **Patrol agents as AXE-launched, formula-bound turns.** A Witness job (per project) and a Deacon job (fleet) that run on a cadence, read hooked/queued/zombie state, and may propose redispatches, mail, or escalations. Keep "scripts propose, runner launches." Give each patrol a poured-or-inline checklist so it cannot wander into rewriting SASE. Yegge's later failure mode — agents gardening the harness — is the constraint.

6. **Problems-first fleet view.** On the Agents tab (and `sase agent problems`): hooked with no progress, waiting on a dead dependency, zombie process, usage-limit pause, idle with empty hook, merge-conflict rework. Bind nudge (mail + optional session inject) and reprime. `gt feed --problems` is the model; SASE already has the richer cockpit to hang it on.

7. **Prime as a recovery verb.** `sase agent prime` (and SessionStart equivalent for session members) reprints identity, hook, mail, relevant formula/macro checklist, and open escalations. Instruction bundles stay the delivery channel; prime is the *assignment* slice that today is only in the original prompt.

8. **Seance.** Given a prior run, spawn a short-lived ask-only turn that loads that transcript (and, where the provider supports `--resume` / fork-session, the provider session) to answer "where did you leave X?" Store the answer as mail or an artifact on the original bead. `sase chat show` is the archive; seance is the interview.

9. **Host-owned Refinery / lander with batch-then-bisect.** A lander that takes a stack of ready Patches, runs the project's `just check` (or configured gates) on the merged tip, and bisects on red. Workers still declare; the host still commits. Polecats never need `git push` to main.

10. **Mayor session as an optional UX, not a new ontology.** A long-lived coordinator session (or a dedicated `#mayor` macro) whose tools are: create convoy, sling to worker identities, read problems, summarize landed work. The TUI remains the cockpit. The Mayor is how you *talk* to the cockpit in English.

11. **Convoys.** A bead type or artifact that tracks a set of beads/patches across projects, notifies on land, and shows 3/7 done. Wire it to existing epic/plan/clan objects rather than inventing a fourth work unit.

12. **Agent escalation.** `sase escalate -s high "…"` creates a tracked record, notifies (TUI / Telegram), and re-notifies on stale unacked. Route through patrol → Mayor session → human. Do not block the escalating agent. Distinct from gates (which approve commands) and from task beads (which capture follow-up work).

13. **Role directives and formula overlays.** Per-project Markdown that is injected with an authority marker, plus TOML/YAML step overrides (replace/append/skip) for bundled macros used by `sase bead work` and patrols. This is how you stop workers from posting `gh pr review` when the project policy is "report back."

14. **Dispatch queue in front of runner slots.** `sase sling <bead> [worker]` enqueues work. AXE dispatches when hook slots and `max_running_agents` allow. Store queue state on a sidecar context object so the work bead stays clean (Gas Town's sling-context lesson).

15. **Doctor `--fix` for harness rot, behind existing sudo/gate patterns.** Repair orphan workspaces, stale tmux/service units, broken sidecar redirects, missing instruction-bundle pins. Keep code-level doctor read-only.

16. **Usage-limit as a stall, with optional account/provider rotation.** When a pane or stream shows a provider usage pause, mark the worker stalled-healthy, backoff, and let routing pick another provider or account instead of declining auto-restart as a hard death.

17. **OTLP export of agent operations.** Session start/end, sling, mail, done, patrol, escalate, lander bisect. Keep the local SQLite telemetry; add an opt-in exporter for people who already run VictoriaMetrics / Grafana.

18. **Skip for now.** Wasteland, capability auto-routing, Daytona sandboxes, meme-coin-adjacent federation, and copying Gas Town's role names. Build the ledger and hooks; routing can be derived later. Isolation should stay SASE workspaces (with a worktree flavor), not "run as the user in tmux."

## What SASE should not copy

Gas Town's always-on tmux Claude processes, agent-pushed main, and vibe-grown taxonomy are the parts that burned money and attention. SASE's single-turn contract, host-owned commits, audited memory, and cockpit are the reasons a human can still be responsible for the tree. Yegge's own later move — a private, application-specific orchestrator that still had Beads, planners, workers, reviewers, messaging, and a merge processor — is evidence that the **primitives** survive even when the **product** does not.

Steal the primitives. Keep the cockpit.

## Sources

- Gas Town repo `gastownhall/gastown` @ `649b832b` (2026-07-23): `README.md`, `docs/overview.md`, `docs/why-these-features.md`, `docs/glossary.md`, `docs/design/architecture.md`, `docs/design/mail-protocol.md`, `docs/design/escalation.md`, `docs/design/scheduler.md`, `docs/design/dolt-storage.md`, `docs/design/directives-and-overlays.md`, `docs/design/sandboxed-polecat-execution.md` (proposal), `docs/design/witness-at-team-lead.md` (not implemented), `docs/concepts/{convoy,heartbeats,identity,molecules,polecat-lifecycle,propulsion-principle}.md`, `docs/HOOKS.md`, `docs/WASTELAND.md`, `CHANGELOG.md`, `internal/cmd/{prime.go,seance.go}`, `internal/formula/formulas/mol-polecat-work.formula.toml`, `plugins/`.
- GitHub API `gastownhall/gastown` (2026-10-16): 18390 stars, 1687 forks, 506 open issues, created 2025-12-16, latest default-branch commit 2026-07-23.
- SASE docs: `docs/concepts/agents.md`, `docs/guides/{run-agents-in-parallel,recover-interrupted-agent,hand-a-result-to-another-agent,plan-multi-agent-change,diagnose-with-doctor}.md`, `docs/reference/{agents/workspaces,agents/agent-clans,automation/scheduler,automation/notifications,work-units/index,work-units/bead-storage,vcs/commit-workflows,providers/usage,runner-slots,agent-auto-restart,cli/pipe,cli/chat,cli/doctor}.md`, `docs/contribute/telemetry.md`, `docs/blog/posts/why-coding-agents-need-orchestration.md`.
- Steve Yegge, "Welcome to Gas Town" (2026-01-01); "Gas Town Emergency User Manual"; "Welcome to the Wasteland"; yegge.ai/gastown.html.
- Maggie Appleton, "Gas Town’s Agent Patterns, Design Bottlenecks, and Vibecoding at Scale" (https://maggieappleton.com/gastown).
- GitHub discussion #282 (crew vs mayor context); issue #2801 (multi-machine / sandbox, design).
- Latent Space AINews 2026-09-17 / Dan Luu 2026-09-15 (personal shutdown reporting); @Steve_Yegge 2026-10-07 (successor orchestrator, Beads still central).
- tomrochette.com Gas Town status note (repo quiet since 2026-07-23; HN footprint).
