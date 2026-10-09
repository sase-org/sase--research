# Can Hermes Replace SASE? A Feature-Set Verdict on "Just Use Hermes"

**Date:** 2026-10-09
**Lead researcher:** consolidated from five independent reports (cdx, cld, grk, mus, gem) plus the lead's own
verification against the source checkouts.
**Claim under test:** "Hermes can do everything that SASE can, so the smart move, for just about any user except me,
is not to bother with SASE."
**Scope:** This compares feature sets only. Popularity, adoption, stars and community size are excluded, as the request
asked. Nobody ran matched workloads, so this report makes no claims about speed, reliability or code quality.

---

## Bottom Line

The claim bundles two different claims, and they get different verdicts.

1. **"Hermes can do everything SASE can": refuted.** All five researchers reached this verdict independently. The lead's
   verification confirmed the gaps that decide it.
   - Hermes covers SASE's *operational* half at parity or better: parallel isolated workspaces, durable task graphs,
     scheduling, chat reach and usage-limit routing.
   - Hermes has no core equivalent for SASE's *governance* half:
     - vendor coding CLIs run as supervised workers
     - host-owned commits with provenance
     - typed, durable human gates on any agent turn
     - a work-and-memory record stored in git
     - verification evidence in a ledger
   - The most important of these follow from opposite design choices, not from a backlog Hermes will clear next month.
2. **"Skip SASE, for just about any user": supported. The exception is defined by features, not by being Bryan.** Most
   people who want an AI agent are better served by Hermes, or by a single vendor coding CLI. That includes most
   professional developers. Hermes's Kanban is now a real coding pipeline, and on *checking work before calling it
   done* it is ahead of SASE. SASE also costs every user something: it is alpha and POSIX-only, has no sandbox, has a
   large vocabulary to learn, and has shipped no release since 0.17.1.
3. **SASE has a real role, and it is narrower than "engineering" and wider than "Bryan".** SASE is the **vendor-neutral
   control plane for a developer who runs a fleet of frontier coding CLIs as a supervised engineering team, on trusted
   repositories.** In that slot Hermes is not a drop-in substitute. Hermes's own docs say it lacks the piece SASE is
   built around: external CLIs as Kanban workers are "*not yet a paved path*".

**The sentence that survives the evidence:**

> Hermes, or a single vendor coding CLI, is the right default for almost everyone, including most developers. Hermes
> cannot do everything SASE does. SASE only pays off for someone who has moved from *using* a coding agent to
> *managing several* of them, and serving that person is SASE's role.

---

## 1. Scope, Pins and Method

**"Hermes"** means Nous Research's **Hermes Agent**, the self-hosted agent harness. It is not the Hermes model family.

| Project | Pin |
| ------- | --- |
| Hermes Agent | All five researchers used `1e0c7730d7` (2026-10-08). The lead re-verified at `908e4a4b44` (2026-10-08 22:17, 6 commits later). Tag: `abandoned-rc.3-v0.21.7`. Latest stable: v0.21.6. The plugin catalog has about 510 entries. |
| SASE | `96dd8ed270` (2026-10-09). Declared and last released version: **0.17.1**, tagged 2026-08-29. Master is about 2,260 commits past that tag. |

**What "can do" means.** Hermes is a general agent with a shell. If "can" means "an LLM could be prompted into doing
it", the claim is trivially true, and it is just as true of a bare terminal. Hermes could even run SASE. So each
capability is graded by how *Hermes the product* provides it. This scale is cld's; cdx draws the same distinction
between equivalent outcome, supported workflow and programmable possibility.

| Grade | Meaning |
| ----- | ------- |
| ✅ Core | Ships in Hermes core, either on by default or set through first-class configuration |
| 🟡 Opt-in | Ships, but is opt-in or experimental, or lives in an official-tier catalog plugin |
| 🟠 Approx. | Available only through a community-tier plugin, or by the Hermes LLM improvising with skills and its shell; nothing enforces it |
| ❌ Absent | No equivalent found |

Comparing *jobs* would be a different and weaker test. Getting the same job done in Hermes is job substitution, not
feature equality (grk). The claim under test is about features.

---

## 2. Two Different Kinds of Product

Every researcher reached the same point first, and most of what follows depends on it.

- **Hermes *is* the agent.** It runs its own tool-calling loop over about 40 model providers, including local models.
  Its own `AGENTS.md` says: "a personal AI agent that runs the same agent core across a CLI, a messaging gateway…, a TUI,
  and an Electron desktop app. It learns across sessions (memory + skills), delegates to subagents, runs scheduled jobs,
  and drives a real terminal and browser."
- **SASE *wraps* agents.** It has no LLM loop of its own. It runs seven vendor coding CLIs as single-turn workers in
  numbered workspace clones: Claude Code, Codex, Antigravity, Qwen Code, OpenCode, Muse Code and Grok Build. Its README
  says: "sase does not replace coding agents; it makes agent-driven engineering dependable." If you "want a standalone
  agent instead of a coordination layer, use those CLIs directly."

The two products point in opposite directions. Hermes ships `hermes import-agent`, which imports a Claude Code or Codex
setup *into Hermes*: a migration path **off** those CLIs. SASE keeps those CLIs as the execution engines and puts a
shared launch, workspace, commit and review path around them.

The products overlap in exactly one area: **running several agents on real repository work under durable
supervision.** The comparison has to be decided there.

---

## 3. Forward Test: SASE's Capabilities Against Hermes

This merges cld's 20-row audit with the matrices from cdx, grk, mus and gem. Rows the lead re-checked against the
source are marked †.

| # | SASE capability | Hermes equivalent (October 2026) | Grade |
| - | --------------- | -------------------------------- | ----- |
| 1 | **Vendor coding CLIs as supervised workers.** Seven harnesses run headless, each in its own clone. | Codex can run as Hermes's runtime through an opt-in app-server. On that runtime `delegate_task`, `memory`, `session_search` and `todo` are unavailable. Claude, Antigravity and Grok are reachable only as **model providers** under Hermes's own loop: through an *experimental* official-tier Claude plugin, and community plugins for the `agy` and `grok` CLIs (the `agy` plugin removes agy's built-in tools). Using an external CLI as a Kanban worker "is *not yet a paved path*" (`kanban-worker-lanes.md:121`). † | 🟡 / 🟠 |
| 2 | **One prompt fanned out** to several harnesses side by side, each in its own clone | Mixture-of-Agents and the community `hermes-council` plugin *merge* answers from several models. Nothing runs several vendor harnesses side by side. | 🟠 |
| 3 | **Isolated workspace per agent** (numbered clones, claims, rescue bundles) | Per-task git worktrees, `hermes -w`, `/worktree` | ✅ |
| 4 | **Durable dependency-ordered work** (beads, `%wait`, `%queue`, waves) | Kanban stored in SQLite: links, a dispatcher, claims, retries, attempt history, swarms | ✅ |
| 5 | **Scheduling, and follow-up on long commands** (scheduler, monitors) | cron with natural-language schedules and delivery to any channel; `/goal`, `/loop`, `/heartbeat` | ✅ (broader than SASE) |
| 6 | **Supervision from phone or chat** (Telegram plugin, Android client) | About 20 or more messaging platforms, a desktop app and a web dashboard | ✅ (superset) |
| 7 | **Routing around subscription limits** (size aliases with round-robin and fallback; auto-disable on a limit) | Credential pools that rotate on "usage limit reached"; reset-aware fallback providers; `/usage` reads account and model windows (`agent/account_usage.py`). † | ✅ (SASE switches whole harnesses; Hermes switches models under one loop) |
| 8 | **Review and checks before completion** | Built-in Kanban review lane; `/goal` quality gates that must exit 0; a PR contract that requires GitHub's required checks | ✅ (Hermes is **ahead**) |
| 9 | **Typed durable human gates on any agent turn** (plan, question, launch approval, sudo, triage). Asking ends the turn; the answer, days later, starts a new turn with a receipt. | A Kanban `kanban_block(needs_input)` card waits indefinitely, and a human unblocks it later. That pause is durable †. It is not typed, though, and exists only for Kanban cards. Per-command approvals and `clarify` block a live thread. Approvals time out after 300 s by default and fail closed †. Durable approvals were merged and reverted on 2026-10-01 (`e57fa350cb` / `afc47d6e4f`) †. | 🟡 |
| 10 | **Host-owned commits with provenance.** Agents declare their changes; the host makes the commit with `SASE_BEAD`/`SASE_AGENT` trailers; stale or after-the-fact changes fail closed. | The worker LLM runs `git` and `gh` itself. The community `git-hook` plugin auto-commits and pushes after each turn, which is the opposite policy. | ❌ |
| 11 | **Plan approval → epic → sized phases → automatic land agent** | A flat Kanban graph, swarms (workers → verifier → synthesizer) and auto-decompose. `/plan` is prompt-only. Plan approval exists only in the community `plan-mode` plugin. The docs describe a *manual* reconciliation-card pattern backed by an optional `agent-merge-conflict-arbiter` skill. † | 🟠 |
| 12 | **Work state stored in git.** Beads, plans and research live in repo sidecars, so a clone carries them. | `~/.hermes/kanban.db` is local SQLite. "Kanban is deliberately single-host" (`kanban.md:1449`). † | ❌ |
| 13 | **Curated project memory**, versioned, rendered into every vendor's instruction file, read with an audit trail | Memory is *about the user*, kept per profile and written by the agent. Only **one** project context type is loaded, first match wins: `.hermes.md` → `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`. † | ❌ (a different paradigm) |
| 14 | **Audited reads and a typed artifact provenance graph** linking plans, research, agents, beads and commits | Session transcripts, Kanban events and attachments, context references | 🟠 |
| 15 | **Typed macros and a YAML workflow executor** (agent, bash, python, parallel, loop and human-in-the-loop steps) | Skills used as slash commands, and hooks. The community `hermes-workflows` plugin is a JSON DAG runner with gates that survive restarts. | 🟠 |
| 16 | **ToolRun evidence**: fingerprints, failure triage into NEW, KNOWN, FLAKY or UNKNOWN, and verdict receipts | Goal gates and the PR contract report pass or fail. Nothing records failures in a ledger or classifies them. | ❌ |
| 17 | **Remote dispatch** into one agent list (`%dispatch`) | Remote terminal backends and remote Hermes instances. A Kanban board cannot span hosts. | 🟡 |
| 18 | **One skill source deployed to all seven vendor CLIs** | Skills target Hermes only | ❌ |
| 19 | **An operations console over runs from different harnesses** | Kanban dashboard and desktop subagent panes | 🟡 |

**Tally:** 6 ✅, 4 🟡, 4 🟠, 5 ❌.

- Rows 3–8, the operational half, are at parity, and on row 8 Hermes is ahead.
- Every row in the governance and identity half (rows 10–16 and 18) is 🟠 or ❌.
- Row 1 reaches 🟡 only through the opt-in Codex runtime and plugins that turn a vendor CLI into a *model*.

The weights matter more than the count. A user who needs none of rows 1 and 9–16 loses nothing by choosing Hermes.

---

## 4. Reverse Test: What Hermes Has That SASE Lacks

SASE lacks every item below **on purpose**: its README sends standalone-agent users elsewhere. These gaps are why the
practical half of the claim holds.

- **An agent loop of its own, with many models.** About 40 providers, local llama.cpp, Ollama and vLLM among them,
  plus fallback chains and credential pools.
- **Personal-agent breadth.** Voice with a wake word, browser and computer use, vision, image generation, about 20 or
  more messaging platforms, cron delivery to any of them, and a desktop app.
- **Self-improvement.** Memory and skills the agent writes itself, a Curator that prunes them, and full-text search
  over past sessions.
- **Containment.** Seven terminal backends (Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox, local), an egress
  proxy, a hardline command blocklist, a guardian-LLM approval mode and prompt-injection scanning.
  - SASE, by contrast, runs every vendor CLI with its permission bypass on: `--dangerously-skip-permissions`,
    `--dangerously-bypass-approvals-and-sandbox`, `--yolo` and the like (`docs/llms.md`) †.
  - The only opt-in sandbox in SASE is Muse's (`SASE_MUSE_SANDBOX=on`).
- **Coding-loop extras SASE lacks.** A per-task review lane, a PR gate that waits on required CI checks, `/goal`
  judge loops with quality gates, opt-in `/rollback` checkpoints, and LSP diagnostics after each edit.
- **Interop.** An MCP client and server, ACP for IDEs, an OpenAI-compatible API server, A2A, and a plugin catalog of
  about 510 entries.
- **Platforms and packaging.** Native Windows, WSL2, macOS, Linux, Android via Termux, Docker and Nix, with frequent
  releases.
  - SASE supports Linux and macOS only.
  - Its last release is 0.17.1. Goals, ToolRuns, Plan Decisions and more exist only on master.

---

## 5. Steelman: The Strongest Case for "Just Use Hermes"

The claim deserves its best version, and that version is strong (cld, cdx).

1. **Hermes Kanban is a credible coding pipeline.**
   - It already has:
     - claims with TTLs
     - an exit-code failure taxonomy and retries
     - a worktree per task
     - auto-decompose
     - a review column that spawns a reviewer
     - swarms with an independent verifier and synthesizer
     - a PR contract that will not close a card until GitHub's required checks pass at the current head
   - The completion transaction rechecks dependencies and run ownership (cdx read `kanban_db.py`).
   - On *verification before completion* Hermes is ahead of SASE, which has no per-bead review lane and no
     required-checks gate for `#pr` Patches.
2. **The community catalog closes much of the gap on paper.**
   - `crew`: a coordinator owns each card until a proof command exits 0.
   - `hermes-workflows`: DAG gates that survive the end of a session.
   - `plan-mode`: plan approval.
   - `git-hook`: automatic commits.
   - `hermes-council`: multi-model deliberation.
3. **Subscription access is better than it looks.** Hermes can bill Claude to a subscription through the experimental
   official-tier `claude-subscription-directsdk` plugin. Codex runs on ChatGPT auth. Community plugins drive the `agy`
   and `grok` CLIs on their subscriptions †.
4. **SASE's costs fall on every user; its benefits fall on few.**
   - SASE is alpha and POSIX-only, needs a Rust extension, runs with no sandbox and has no recent release.
   - Its vocabulary is huge: beads, Patches, stitches, macros, clans, sessions, tribes, gates, gate turns, webs,
     artifacts, ToolRuns.
5. **Some SASE guarantees are softer than they sound.**
   - Memory-write gating is mostly an instruction to the agent.
   - Guarded recipes are "a guardrail against habit, not a security boundary" (`docs/tool.md`).
   - Containment amounts to a clone directory plus a systemd scope.
6. **Hermes covers the other 90% of what a person wants an agent for.** For most people, one tool that answers on
   their phone, triages email, runs cron jobs, browses *and* runs a coding board is worth more than one that only
   supervises coding CLIs.

For users whose coding needs come down to "a few background tasks on one model family, landed as PRs", the steelman
wins outright.

---

## 6. Why the Strong Claim Still Fails: Gaps That Survived Verification

Each gap below is stated at the strength the evidence supports, and each says how it could erode.

### 6.1 Who does the work: a harness as worker versus a harness as model

SASE runs a vendor's **whole harness** as the worker: Claude Code's tools, context compaction and permission model, or
Codex's. Hermes runs **its own loop**. It brings in vendor CLIs in three ways:

- as a runtime swap (Codex only, with a reduced toolset)
- as a model provider (Claude, Antigravity and Grok, with the vendor's own tools stripped or bypassed)
- as a terminal command the Hermes LLM runs through a skill

A user who wants Claude Code, Codex and Grok Build working one board under one set of rules has no paved path in
Hermes. Hermes's docs describe that lane as open design work: issue #19931 is open, and Codex PR #19924 was closed
without merging †.

- **When it matters:** if you believe each vendor's harness is part of the product. This is a preference about how the
  work gets done, not a measured quality gap.
  - gem asserted a "frontier harness penalty" for Hermes's loop. No researcher benchmarked one, so treat it as a
    hypothesis.
- **How it could erode:** Hermes ships `spawn_fn` lanes for Claude Code and Codex. The dispatcher is already pluggable.

### 6.2 Who owns the commit

In SASE the agent declares and the host commits. Submission rejects a stale context. Once a declaration is accepted,
any further change to the repositories counts as a protocol violation, and the executor fails closed. A deferral is
judged against the run's evidence. A run that leaves dirty work behind fails or is marked `deferred`. Every commit
carries bead, agent and plan trailers (`docs/commit_workflows.md`) †.

Hermes gives git to the worker LLM. Its PR contract is a read-only acceptance check, and "no remote writes are
performed by this gate" †.

- **Precision matters here, because gem overstated it.** Host-owned completion is a **workflow and provenance
  contract, not a security boundary.**
  - Agents run with bypass flags and could physically run `git`.
  - What SASE guarantees is that such a commit is *detected and not accepted as completed work*, not that it is
    impossible.
- **How it could erode:** a host-side commit finalizer for Kanban. No Hermes plugin currently takes git away from the
  agent.

### 6.3 Pausing for a human without holding a worker

SASE's gates end the agent's turn. A pending plan approval, question, launch approval or sudo request then exists as a
record, with no model process and no runner slot. The answer arrives from the TUI, the CLI, Telegram or Android and
starts a new turn carrying a write-once receipt.

**Correction to gem (and partly mus):** Hermes *does* have a durable pause, at the Kanban level. A worker calls
`kanban_block(needs_input)`. The dispatcher reaps the worker. The card waits in `blocked` indefinitely until a human
comments and unblocks it, and the re-run sees the earlier handoffs †. gem's "300-second approval deadlock fails the
task" is true only of per-command approvals and `clarify`, not of Kanban workflows.

What remains different:

- SASE's gates are **typed**: plan approval with decisions, multiple-choice questions, launch approval, sudo manifests
  and triage.
- They apply to **any agent turn**, not only Kanban cards.
- They leave receipts.

Hermes tried to make per-command approvals durable and reverted the change the same day (2026-10-01) †. It wants this
model, but retrofitting it is evidently hard.

### 6.4 A portable record stored in git

SASE stores beads, plans, epics, research and project memory **in git**, in sidecars or in-tree, so a clone carries
them. Memory is rendered into *every* vendor's instruction file and read with logged reasons. Typed artifact links
connect research to plans, plans to phases, phases to commits.

Hermes keeps the Kanban board in local SQLite under `~/.hermes`, on a single host. Its memory describes the user, not
the codebase, and it loads one project context file per session.

- **When it matters:** long-lived codebases where people ask "which agent, under which plan, using which evidence,
  produced this change?", and where a teammate or another machine should see the work graph by cloning.
- **How it could erode:** an external memory or graph service, but that is an additional system to evaluate.

### 6.5 The shape of the work: an epic with an automatic land step

SASE's epic flow starts with human plan approval. Each phase's size picks the model, and `large` and `xlarge` phases
must plan before they implement. A land agent is **always scheduled**, and it waits mechanically on every phase agent
and every phase bead. `sase bead close` refuses while phases are incomplete or stale epic-symbol entries remain.

**Correction to gem:** the land agent's verification and integration are **LLM work guided by a prompt** (the
`bd/land_epic` macro in `default_config.yml`). That work is: read the child beads and commits, integrate changes that
landed since the epic started, and triage `PROPOSED FOLLOW-UP:` notes. It is not a host step that "rebases, runs the
complete integration suite, and lands only after all checks pass." Hermes documents a comparable reconciliation-card
pattern, but the user composes it by hand.

- **The real difference:** the automatic tail and the mechanical waits, not verification that is any harder to fool.

### 6.6 Verification evidence

SASE's ToolRuns record:

- the command's identity
- before and after fingerprints
- failure evidence

Failures are triaged into NEW, KNOWN, FLAKY or UNKNOWN; KNOWN requires an independent witness. A receipt can satisfy
an explicitly configured completion policy.

Hermes runs checks deterministically (goal gates, the PR contract) but keeps no project-level failure ledger.

- **Do not oversell this.** Receipts never skip running a test. They depend on configuration. A thin ledger produces
  many UNKNOWN verdicts. An ordinary SASE final declaration runs no tests unless the agent ran them through ToolRuns or
  the turn used the prepared-completion path (cdx).

### The gaps that decide the question

Gaps 6.1–6.3 decide the strong claim. Suppose Hermes ships three things:

- **(a)** a paved external-CLI Kanban lane for at least Claude Code and Codex
- **(b)** typed, durable approvals in core
- **(c)** a host-side commit finalizer

Then "Hermes can do everything SASE can" becomes *nearly* true. SASE's remaining edge would be the record stored in git
and the evidence ledger (6.4–6.6).

---

## 7. Claims in the Swarm That Did Not Survive Verification

Most of these came from one report (gem), whose architectural analysis was otherwise sound. They are listed so that
nobody repeats them in an argument for SASE.

| Claim | Source | Finding |
| ----- | ------ | ------- |
| Hermes is "almost exclusively metered"; it has no usage-window tracking or subscription use | gem; mus in part | **Wrong.** Hermes has credential pools that rotate on usage limits and `/usage` with account and model windows. It reaches Claude through a subscription plugin and Codex through ChatGPT auth, and community plugins cover `agy` and `grok` †. One real catch, verified in `providers.md:142-148`: the *native* Anthropic OAuth path bills only Max **extra-usage** credits, never the base allowance. |
| SASE "proactively" tracks windows and reroutes before limits | gem | **Overstated.** Auto-disable classifies limit *errors* after they happen (`docs/llms.md` §Usage-Limit Auto-Disable) †. Both systems react to limits once they are hit (cld). SASE does collect usage windows for display. |
| The land agent rebases, runs the full integration suite and lands only after all checks pass | gem | **Overstated.** Those steps are a prompt to an LLM; the waits and close refusals are mechanical (§6.5) †. |
| Host finalizers "execute verification hooks (`just check`, tests)" | gem | **Only on the prepared-completion path**, with its sealed command. An ordinary final runs no tests (§6.6) †. |
| Host-owned completion makes rogue git "physically impossible"; SASE is an "air-gapped governance layer" with agents "sandboxed" in clones | gem | **Wrong.** Agents run with permission bypass. The guarantee is detection plus a fail-closed check, not prevention (§6.2) †. gem's own matrix contradicts the sandbox claim. |
| Hermes worktrees "share `.git` references, index locks" | gem | **Mostly wrong.** Each git worktree has its own index and HEAD. They share the object store and refs. Isolation is not a meaningful differentiator here (cdx, cld). |
| A swarm costs "$100–$400 per day" on metered APIs | gem | **Unsupported**, and it cites stale model names. Dropped. |
| Hermes Kanban approvals hit a "300-second deadlock" and the task fails | gem | **Applies to per-command approvals only.** Kanban `blocked` cards wait indefinitely (§6.3) †. |
| Driving Claude Code or Codex from Hermes "requires custom shell skills" | gem | **Incomplete.** Codex has an opt-in native runtime, and Claude, Antigravity and Grok have model-provider plugins. None of these is a worker lane. |
| Sudo requests use SHA-256 hashing of every executable | gem | **True**, but sudo is **beta and off by default**, behind the `agent_sudo_requests` flag (`docs/sudo.md:29`) †. |

---

## 8. Who Is "Just About Any User"?

This is where the reports disagreed most.

- cld, cdx and grk call the practical claim *supported*.
- mus calls it "refuted as stated, true for a large segment".
- gem calls it "categorically refuted for serious software engineering".

**Resolution.** gem's "Archetype B" is "anyone managing production codebases with strict git history". That is far too
broad. A professional developer working one repository with one harness and existing CI gets review, required-check
gating, worktrees and a task board from Hermes Kanban, or simply uses the vendor CLI. Being serious or professional is
not the dividing line. **Several conditions holding at once** is.

| User profile | Best fit | What SASE adds for them |
| ------------ | -------- | ----------------------- |
| Wants a personal assistant (developer or not): chat reach, voice, browsing, cron, memory about them | **Hermes** | Nothing. SASE is a different category of product. |
| Developer using one coding agent at a time | **The vendor CLI directly**, or Hermes for an all-in-one tool | Overhead. SASE's README says as much. |
| Developer who wants background coding with chat control: a few parallel tasks, one model family, PRs as output | **Hermes Kanban** | Little. Hermes's review lane and CI gate are things SASE lacks. |
| Needs a security boundary, faces untrusted input, or uses Windows | **Hermes** | SASE is ruled out: permission bypass, no sandbox, POSIX only. |
| **Runs a sustained fleet across vendors**: several frontier CLIs at once, often on flat-rate subscriptions; long-lived trusted repositories; supervises asynchronously; lands large multi-phase work and wants it attributable | **SASE** | §6.1–6.6. Hermes has no paved path to most of them. |

The first four rows contain most people who want "an AI agent", so the claim's practical advice is sound. The fifth
row is not "Bryan and nobody else". It is a profile defined by features: someone who has moved from *I use an agent*
to *I manage agents*, for whom vendor lock-in, commits nobody can attribute and approvals that block a thread are daily
problems.

"Except for me" confuses **authorship with fit** (mus). SASE fits whoever runs the fifth workflow.

---

## 9. SASE's Realistic Role for Many Users

**Role: the vendor-neutral engineering control plane above frontier coding CLIs.** SASE is not an agent. It is the team
layer that makes several agents behave like a supervised engineering organization. This is the "Agent Command
Environment" of Hassan et al., *Agentic Software Engineering* (arXiv:2509.06216), the paper SASE takes its name from
(grk).

**Why the role is real, and not just Bryan's:**

1. **It answers four recurring operator questions that Hermes does not answer as one package** (cdx):
   - What is the approved plan, and what remains blocked?
   - Which agent, on which harness, changed which repository, using what evidence?
   - What actually verified the change, including known failures and uncertainty?
   - Who may land the result, and how is a failed or ambiguous landing recovered?
2. **It gains value as vendor CLIs multiply rather than consolidate.** A layer that rides the best harness of the
   moment without rewriting any agent loop benefits from vendor competition. Hermes's architecture makes it sit
   *beside* those harnesses, or replace them, rather than *above* them.
3. **The orchestration costs no tokens.** Dispatch, waits, gates, commits and landing are deterministic Python and
   Rust. The models spend tokens only on the work itself (cld).
4. **Its demand comes from a policy, not a person.** Any team that adopts "agents may write code; the host and humans
   own git and review" needs *some* command environment. The options are:
   - homegrown tmux plus scripts
   - a single harness's own board (Hermes Kanban, a vendor's cloud board)
   - a coordinator that works with any harness

   SASE's wedge is the third option, combined with records stored in git and host-owned completion (grk).

**How large "many" is cannot be measured here,** because adoption was excluded. The role exists independent of how
many people fill it. The feature evidence supports a *repeatable class* of operator, not a mass market.

**What SASE should not try to be:** a Telegram companion, a self-learning personal assistant, a Windows desktop agent,
or a replacement for Claude Code's inner loop. Those belong to Hermes or the vendor CLIs. Competing there dilutes the
control plane (grk, mus, cld).

**What currently keeps the role out of reach.** These are product changes that follow from the feature comparison;
none of them is current capability.

- **Cut a release.** Everything since 0.17.1 exists only on master, so most of the differentiators above are hard for a
  new user to get (cld).
- **Offer an opt-in sandboxed run mode,** such as a container or bubblewrap per workspace. Today every agent runs with
  its permission bypass on (cld, gem).
- **Present a small core path**: workspaces → launch → final declaration → gates → TUI. Show it on an ordinary repo,
  with one approved dependency graph, one failed-check recovery and one verified landing. Make personal macros
  optional (cdx, cld).
- **Close the verification gaps Hermes exposed:**
  - a per-bead review lane
  - a required-checks gate for `#pr` Patches
  - in-run rollback (mus, cld, gem)
- **Borrow only coordinator features from Hermes:**
  - full-text search over transcripts
  - webhook ingress
  - an MCP server as a *control-plane API* over beads, runs and gates
  - staged memory drafts proposed by agents

  Do not borrow self-editing skills or autonomous memory. They conflict with SASE's reproducibility story of authored
  memory, skills kept in version control and audited reads (grk, mus).

**Complement, not rival.** Four reports converged on this independently (cld, mus, gem, cdx).

- Hermes has a clean headless mode: `hermes chat --oneshot -q … --format stream-json`, verified in `cli-commands.md` †.
  That is the shape a SASE provider needs.
- Making **Hermes the eighth SASE provider** would turn the main competitor in the overlap into a supplier. It would
  bring Hermes's local and any-model loop under SASE's workspaces, gates and finalizers.
- From Hermes's side, SASE fills the documented gap: external CLI workers plus governance.
- A user could keep Hermes as their always-on personal front door and use SASE for the engineering fleet.
- This requires a maintained integration. It does not exist today, and shell access alone does not make it exist
  (cdx).

---

## 10. What Would Change the Verdict

- **Toward "Hermes does everything":** Hermes ships (a) paved external-CLI Kanban lanes for Claude Code and Codex,
  (b) typed durable approvals in core, and (c) a host-side commit finalizer.
  - A Kanban board that spans hosts and a record stored in git would close most of the rest.
  - Watch issue #19931, and any second attempt at durable approvals after the reverted `e57fa350cb`.
- **Against SASE's role:** SASE's distinctive contracts stay hard to adopt (no release, no sandbox, a huge
  vocabulary). Or, in a side-by-side trial, they deliver no practical benefit over Hermes plus existing CI.
  - A useful trial would run the same four workflows through both products:
    - a small issue-to-PR task
    - a dependency-ordered effort with a failed worker and a review rework
    - a change across repositories whose verified inputs go stale
    - a research swarm whose report a later implementation must consume
  - Judge them on which records survive, how recovery behaves, the verification policy, and how much custom
    integration each needed (cdx).
  - Nobody has run this trial.

---

## 11. Recommendation

1. **Make the practical argument and drop the strong one.** "Most people, including most developers, should use
   Hermes or a single vendor CLI and not bother with SASE" holds up on features. "Hermes can do everything SASE can"
   does not. Even with generous grading, 9 of the 19 SASE capabilities in §3 have no Hermes core or official
   equivalent, and the most important three follow from opposite architectural choices.
2. **Recommend Hermes first** for general assistance, research, automation, ordinary coding, and many durable
   multi-agent coding workflows. Do not add SASE just to get parallel agents, worktrees, a task board, scheduling,
   memory, review or chat control. Hermes already has all of these, and on review and CI gating it is ahead.
3. **Recommend SASE only when several of these needs occur together and keep recurring:**
   - several *native* coding-agent harnesses as workers
   - host-owned, attributable landing across repositories
   - typed asynchronous human gates that free the worker
   - a work graph and project memory stored in git, shared across vendors
   - project-level verification evidence

   That is a real role beyond Bryan: a specialist control plane for operators of fleets of coding agents. It is not a
   reason to recommend SASE to agent users in general.
4. **Position SASE as the layer above coding agents, not as a Hermes competitor.** Make that role reachable: cut a
   release, add an opt-in sandbox, offer a small core path, and add a review lane and a CI gate. Build the Hermes
   provider bridge so the two products compose. If SASE's distinctive contracts cannot justify a separate install
   compared with Hermes plus existing CI, contributing those contracts to Hermes would be the better strategy (cdx).

---

## Where the Five Reports Agreed and Disagreed

- **Unanimous:**
  - Claim A is refuted.
  - The two are different categories of product.
  - Hermes dominates personal-agent features, containment, interop and platforms.
  - SASE's core differentiators are vendor CLIs as workers, host-owned commits and durable gates.
  - The Hermes-as-provider bridge (cld, mus, gem) and the complementary-positioning idea (all five).
- **Split on Claim B.** cld, cdx and grk said supported; mus said true only for a large segment; gem said refuted for
  serious engineering. §8 resolves the split in favour of "supported, with an exception defined by features".
- **Factual disagreements resolved by the lead's checks:**
  - subscription and usage routing (cld was right, gem wrong)
  - whether Hermes has any durable pause (yes, at Kanban level; cld noted it, gem missed it)
  - what the land agent actually does (it follows a prompt; gem overstated it)
- **Unique contributions kept:**
  - **cdx:** source-level confirmation that Hermes's completion and PR-acceptance checks are real transactional rules;
    the four operator questions; the side-by-side trial design.
  - **cld:** the 20-row graded audit; the durable-approval revert; the context-file priority; subscription billing
    details.
  - **grk:** the category framing (Hermes swaps models under one harness, SASE swaps harnesses under one coordinator);
    the git-portable work state; the Agent Command Environment lineage.
  - **mus:** "authorship versus fit".
  - **gem:** the architecture diagrams and the strongest version of the governance argument, kept here at its verified
    strength.

---

## Sources

**Hermes Agent** (`NousResearch/hermes-agent`): a local checkout opened with `sase repo open`. The researchers used
`1e0c7730d7`; the lead re-verified at `908e4a4b44`. Paths below are relative to `website/docs/` unless they name code.

- Docs:
  - `user-guide/features/kanban.md`, including lines 48–67 (PR contracts), 466–476 (block, unblock and review tools),
    1194–1227 (reconciliation cards) and 1449 (single-host)
  - `user-guide/features/kanban-worker-lanes.md:119-125`
  - `user-guide/features/codex-app-server-runtime.md:72-114`
  - `user-guide/features/context-files.md:15-26`
  - `user-guide/features/credential-pools.md`, `user-guide/features/goals.md` and
    `user-guide/features/subscription-proxy.md`
  - `integrations/providers.md:142-148`
  - `reference/cli-commands.md:125-164`
  - `user-guide/import-from-other-agents.md`
- Code and catalog:
  - `AGENTS.md`
  - `tools/approval_gateway_wait.py`, `hermes_cli/config_defaults.py:1680` (`timeout: 300`),
    `agent/account_usage.py` and `agent/prompt_builder.py`
  - `plugin-catalog/{claude-subscription-directsdk,antigravity-agy,antigravity-subscription-directsdk,grok-acp,crew,hermes-workflows,plan-mode,git-hook,hermes-council}.yaml`
- Commits `e57fa350cb` and `afc47d6e4f` (2026-10-01).
- Researcher citations to `hermes_cli/kanban_db.py`, `kanban_pr_acceptance*.py`, `kanban_swarm.py` and
  `hermes_cli/goals.py` (cdx).
- Online docs at [hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/).

**SASE** at `96dd8ed270`:

- `README.md` (alpha; POSIX-only; "does not replace coding agents")
- `pyproject.toml` (0.17.1) and tag `v0.17.1` (2026-08-29)
- `docs/llms.md`, including the bypass flags, §Usage-Limit Auto-Disable and the land-agent model selection
- `docs/commit_workflows.md:700-730, 785-800`
- `docs/beads.md:2765-2800`
- `docs/sudo.md:13-35`
- `docs/tool.md`, `docs/sdd.md`, `docs/memory.md`, `docs/remote_dispatch.md` and `docs/goals.md`
- `src/sase/default_config.yml` (the `bd/land_epic` macro)
- Online docs at [sase.sh](https://sase.sh/)

**Other sources:**

- Anthropic billing pages, cited by cld: [Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
  (updated 2026-10-07) and [Monthly API credits for Max and Team plans](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans).
- Hassan et al., *Agentic Software Engineering: Foundational Pillars and a Research Roadmap*, arXiv:2509.06216 (grk).
- Researcher reports in this directory: `can_hermes_replace_sase__{cdx,cld,grk,mus,gem}.md`.
- Earlier comparisons, used by the researchers only as pointers: `research:202604/sase_vs_hermes_agent.md` and
  `research:202609/sase_vs_hermes_agent/`.
