---
create_time: 2026-09-04
updated_time: 2026-09-04
status: research
---

# A Collaboration Architecture For SASE

**Research question:** How should SASE support multiple users, on multiple machines
(including several users on one machine), developing the same codebase concurrently
through a PR workflow? What is `agents_sync` actually buying, and should it be kept,
changed, or removed?

**Scope and evidence:** `sase` @ `a81bc8d59`, `sase-github` @ `5aa3225`, and the live
state of this machine (`kellys_mbp`) on 2026-09-04. Every number in §3 and §5 was
measured directly against the local checkouts, the `sase--agents` sidecar clone at
`~/.sase/projects/gh_sase-org__sase/repos/agents`, and read-only CLI probes
(`sase agent sync --check --json`, `sase bead show`, `sase repo list`). Prior art read
and cited: `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`,
`research:202609/athena_agent_sync_repair/athena_agent_sync_repair.md`,
`research:202609/stitch_timeout_hardening/stitch_timeout_hardening.md`,
`research:202608/fork_contributor_harness/fork_contributor_harness.md`,
`research:202607/shared_sdd_clone_consolidated.md`.

---

## Executive summary

**Collaboration in SASE is shared authorship of durable artifacts with routed
attention. It is not shared visibility into each other's running agents.** Those are
different problems with different consistency requirements, different trust boundaries,
and different failure modes — and the single most expensive mistake in the current
design is that `agents_sync` conflates them.

Three claims drive everything below:

1. **SASE is already ~80% of a good multi-user system, and the missing 20% is not
   synchronization — it is the review loop and an identity join key.** Beads, plans,
   research, memory, and the primary repo already live in shared git repos with
   multi-writer conflict resolution, event-sourced storage, cross-host advisory claims,
   and publication verification. What is missing is small and specific: SASE cannot
   ingest a single inbound review comment
   (`sase-github/src/sase_github/workspace_plugin.py:224` still returns `False` for
   `ws_supports_reviewer_comments`), has no `username` field on a bead, and keeps its
   Patch records — the local record of every PR — in machine-local
   `~/.sase/projects/<key>/<key>.sase`.

2. **`agents_sync`'s import leg should be removed, not fixed.** It is 6 weeks old,
   ~9,400 lines across 32 modules, and on this machine it has imported **zero** v2
   hoods while accumulating **1,375 pending hoods / 8,015 pending runs** for `sase`
   plus 81/272 for `bob-cli`. Its publication leg has produced 3,758 commits (3,012 in
   the last 30 days, ~100/day), 79,386 tracked files, and a 108 MiB pack — to deliver,
   when it works, *dismissed rows in another machine's Agents tab*. The value it does
   deliver (the prompt archive, `@agent:` pages, commit and bead provenance) is
   artifact-shaped and survives the amputation intact.

3. **The single-writer agents sidecar is already a production failure source at N=1,
   and collaboration multiplies it.** `stitch_timeout_hardening` found a finalizer
   SIGKILLed while blocked on `.git/index.lock` in the `agents` sidecar — "which,
   unlike `beads`, `plans`, and `linked`, exists **once per project** and is shared by
   every concurrent agent on the host." Adding users to a design that publishes
   synchronously to one shared remote on the commit-critical path makes commit latency
   a function of team size.

**Recommended solution (detail in §7, §11):** adopt one rule — *cross a user boundary
as an artifact, never as a process* — and then (a) narrow `agents_sync` to a
publish-only, off-critical-path artifact publisher, deleting the import leg in favor of
lazy resolution and explicit `sase agent import`; (b) add a project roster and a
`username` join key so beads, patches, and claims can name a person; (c) implement the
inbound half of the review loop for GitHub, feeding the existing provider-neutral
`COMMENTS` → CRS machinery that is already built and idle; (d) route cross-user
attention onto GitHub review requests and bead assignment rather than building a new
gate transport; and (e) keep the tailnet host daemon strictly single-user — it is the
right answer to *your machines* and the wrong answer to *your team*.

---

## 1. What "collaboration" should mean when the unit of work is an agent

### 1.1 Six distinct things people mean by the word

Bundling these is why "collaboration support" tends to produce expensive machinery that
nobody uses. They are ordered by how much shared mechanism they actually require.

| # | Meaning | Real requirement | Status today |
| --- | --- | --- | --- |
| 1 | **Shared codebase, parallel work** | Non-colliding change units; isolated workspaces | ✅ Works. Workspaces are per-SASE-home; git handles the rest |
| 2 | **Shared backlog** — we agree on what to do and who has it | A multi-writer issue store with claims and assignment | ⚠️ Beads are ~90% there; assignee is an *agent name*, not a person |
| 3 | **Shared understanding** — plans, research, decisions, memory | Durable, addressable, reviewable documents | ✅ Works. Sidecars + in-repo `sase/memory/` |
| 4 | **Review** — I read your change and you act on my feedback | Inbound review ingestion, review state, an agent that applies feedback | ❌ **Outbound only.** The inbound half is unimplemented |
| 5 | **Routed attention** — "someone must decide X, and that someone is you" | Person-addressed, claimable decisions | ❌ Gates are machine-local and single-user |
| 6 | **Shared process** — I watch/drive your running agents | A cross-trust-boundary live control plane | ❌ And it should stay that way (§6.2) |

Items 1–5 are collaboration. Item 6 is a different feature that *looks* like
collaboration, and the existing partial implementation of it (`agents_sync`'s import
leg) is what is expensive and not useful.

### 1.2 The three planes

Every piece of SASE state falls into exactly one of three planes, and the plane
determines its correct transport.

**Plane 1 — The artifact plane.** Durable, content-addressed or name-addressed,
immutable-or-append-mostly, reviewable, valid when the machine that produced it is
offline or destroyed. Beads, plans, research reports, memory notes, decision records,
prompt archives, stitches, PRs, code. Correct transport: **git, with a merge/conflict
policy per store.** Partition-tolerant by construction. This is the only plane that
should cross a user boundary.

**Plane 2 — The process plane.** Live agent runs, runner slots, workspace claims, PIDs,
tmux sessions, in-flight chats, kill/retry. Authoritative *only* on its owning host,
meaningless when that host is down, and dangerous to act on from stale state. Correct
transport: **a per-host daemon with snapshots, cursors, idempotent name-addressed
mutations, and explicit staleness** — exactly what `tailnet_agent_fleet` specifies. This
plane may cross a *machine* boundary within one user. It must not cross a *user*
boundary.

**Plane 3 — The attention plane.** "A human must decide something." Gates,
notifications, questions, plan approvals, review requests, triage. Latency-sensitive,
short-lived, addressed to a *person* rather than to a machine or a repository. Today
this plane exists only inside one SASE home (`~/.sase/interaction_requests/`,
`~/.sase/notifications/notifications.jsonl`), with Telegram and the mobile gateway as
same-user remote projections.

### 1.3 The load-bearing rule

> **Cross a user boundary as an artifact, never as a process.**

Corollaries:

- If a teammate needs to know something, it must be expressible as a durable record
  they can read months later without your laptop being on. That constraint is a
  feature: it forces the thing to be reviewable.
- A teammate never needs your PID, your workspace number, your runner slots, or your
  chat transcript. They need your *change*, your *reasoning*, and your *claim on the
  work*.
- Process-plane fidelity across machines is a legitimate, separate feature — for **one
  user's own machines**. Do not pay for it twice, and do not extend it across a trust
  boundary where mutation authority becomes a security question rather than a UX one.

`agents_sync` violates this rule in one specific place: it ships process history over
the artifact plane (fine, that is what a prompt archive is) and then **rehydrates it
back into the process plane** on the receiving side — as local agent artifacts,
dismissed bundles, saved-family revival groups, and permanent name-registry claims.
Every hard problem the subsystem has (name collisions, transactional import,
quarantine, v1→v2 adoption, registry squatting) lives in that rehydration step and
nowhere else.

---

## 2. What SASE already has (verified)

The surprising finding of this research is how much of the multi-user substrate is
already built, and how little of the remaining gap is about synchronization.

### 2.1 The shared plane is real and already multi-writer

All four project sidecars are ordinary GitHub repos under the same org as the primary
repo, so org membership is already the access-control model:

```text
sase-org/sase            primary
sase-org/sase--plans     plans + the canonical bead store
sase-org/sase--beads     generated bead pages
sase-org/sase--research  research reports (this document)
sase-org/sase--agents    agent hoods, prompt archive, chats
```

Beads in particular are further along than they look for multi-user work:

- **Event-sourced storage** with a generated `issues.jsonl` compatibility projection
  sorted by issue ID "for clean diffs" — an append-mostly shape that merges well.
- **Concurrent-mint conflict resolution** that *relocates* one of two colliding beads
  rather than failing, deterministically from store contents rather than from whoever
  syncs first (`src/sase/bead/conflict_resolver.py`, `relocation.py`).
- **Cross-host advisory claims**: the runner writes `claimed`, commits, and publishes
  synchronously best-effort "so other hosts can see the claim," with a
  `bead_claim_checks` reconciler as the backstop and an explicit rule that a claim is
  never released unless the owning agent is provably dead.
- **Publication verification**: every bead mutation that commits re-checks that the
  commit was actually pushed, and *fails the command* with an operator diagnostic if
  not — because "a bead mutation that is committed but never pushed... is destroyed"
  when the numbered workspace is evicted.

That last one is the single best piece of multi-writer engineering in the tree. It is
the correct posture for authoritative shared state and should be the template.

### 2.2 The mirror pattern is already the right collaboration primitive

The `external_mirror` AXE lane (15-minute interval) already runs both halves of a
"the shared system is the truth, the local record is a projection" design:

- `external_issue_mirror` diffs each project's tracker against local beads on
  `external_ref` and creates `small`/`open` task beads for uncovered issues, with
  bounded per-pass writes (≤25 creations, ≤50 notes) and per-tracker exponential
  backoff.
- `external_pr_mirror` lists remote PRs in every state, discards SASE's own tracked
  workflow markers, applies author/base/head/title/state filters, and **adopts the
  remaining PRs as local Patches** — including other people's.

This is already the shape of the answer for item 4 in §1.1. A teammate's PR can already
become a first-class local Patch. What is missing is everything that would let you *do*
something with it.

### 2.3 Identity is half-built

`id.username` + `id.machine_name` is a well-specified, explicitly-owned, globally-unique
identity that "should normally be the user's GitHub username," and the agents wire
already uses `<username>.<machine_name>.<name>` global names with idempotent
qualification. Duplicate agent names across machines are structurally impossible.

The gap is that **nothing else in SASE uses `username`.** A bead carries three
unrelated identity spellings and no user join key:

```text
$ sase bead show sase-w3.6
Owner: bryanbugyi34@gmail.com          # git author email
Assignee: sase-w3.6                    # a bead id used as an agent name
CREATED BY
  bbugyi200.apollo.b                   # a global agent name
  → .../agents/bbugyi200.kellys_mbp.bbugyi200.apollo.b/README.md
```

Note the link: an already-global name (`bbugyi200.apollo.b`) was globalized a second
time, producing `bbugyi200.kellys_mbp.bbugyi200.apollo.b`. **That page does not exist**
— verified: zero paths in the sidecar match `bbugyi200.*.bbugyi200.*`, and neither
`agents/bbugyi200.apollo.b` nor the double-qualified path is present. Every bead created
by an apollo agent carries a dead provenance link today. This is the same
identity-versus-display conflation `athena_agent_sync_repair` identified as the
architectural fault beneath that incident, and it is now leaking into shared artifacts.

### 2.4 Same-machine multi-user is a capacity problem, not a correctness problem

Two OS users on one machine get two independent `$SASE_HOME`s, two workspace roots, and
two distinct `<username>.<machine>` namespaces — so nothing collides. What *does*
collide is the machine itself: `max_running_agents` and the `runner_slots` pool are
per-SASE-home, so two users on one box can each admit their configured maximum and
jointly oversubscribe the hardware. `two-speed-verification` already establishes that
host capacity — not test speed — is SASE's binding constraint, so this is the failure
mode that matters. It needs a machine-level (not home-level) admission guard, not a new
sync mechanism.

---

## 3. Critique of `agents_sync`

### 3.1 Measured cost

| Dimension | Measurement |
| --- | --- |
| Source | 20,645 lines, 83 modules (2.3% of `src/sase`) |
| Tests | 14,705 lines |
| Age | First commit 2026-07-22; 111 commits, **all within 90 days** |
| Fix ratio | 36 of 111 commits are `fix` (32%) for a 6-week-old subsystem |
| Sidecar commits | 3,758 total; **3,012 in the last 30 days** (~100/day) |
| Commit mix (30d) | 1,363 `sync from`, 1,643 `archive prompt` |
| Tracked files | 79,386 |
| Pack size | 108.22 MiB |
| Agent pages | 10,488 (10,229 from `athena`, 259 from `kellys_mbp`) |
| Chat transcripts | 7,353 |
| Prompt archives | 4,948 |
| Import-leg code | ~5,598 src + ~3,770 test lines across 32 modules |

The publisher asymmetry is diagnostic: `athena` has published 2,011 hoods and 10,229
agent pages; `kellys_mbp` has published 5 hoods and 259 pages. The subsystem is
dominated by a batch machine mass-publishing per-run pages that nothing reads.

### 3.2 Measured value

```text
$ sase agent sync --check --json
sase     behind=0 ahead=0 pending=1375   runs pending: 8015
bob-cli  behind=1 ahead=0 pending=81     runs pending:  272
```

**1,375 hoods / 8,015 runs have been sitting unimported for the `sase` project alone.**
`athena_agent_sync_repair` established (and this probe confirms the shape of) the reason:
this machine imported only the lossy legacy v1 payload, whose 651 `origin: import_v1`
registry entries then made every v2 hood import fail with
`ImportedNameCollisionError`. Zero v2 imports have ever been applied here.

The important part is not that it broke. It is that **it broke, stayed broken across
1,375 accumulated packages, and nobody noticed from use** — the badge was noticed from a
screenshot. That is about as strong a signal as one gets that the import leg's output is
not load-bearing.

And when it does work, the output is: foreign runs materialized as **terminal, dismissed
agent artifacts** (source `active`/`waiting`/`stopped` all collapse to `STOPPED`), plus a
saved-family group revivable from the Agents tab. Useful once in a while. Not worth a
continuously-reconciling replication engine.

Two further quality signals from the same report: ~35% of published v2 run pages
(3,247 of 9,183) carry no `prompt.md` at all, and the dismissed-bundle writer
serializes only a narrow projection, so `agent_family`, `artifacts_dir`, `model`,
`llm_provider`, and `reasoning_effort` land as `null`. The replicated record is both
incomplete at the source and degraded at the sink.

### 3.3 The category error

The publication leg builds artifacts. The import leg builds **processes** — local agent
artifacts, dismissed bundles, revival groups, and *permanent name-registry claims* in
the same namespace live local agents allocate from. That last one is why a foreign
machine's history can wedge your local name allocation, and why `athena.7n--code`
parses as hood `athena`, family `athena.7n`: provenance was encoded as a dotted prefix
in the topology namespace.

Compare with how every other artifact reference works. `@plan:`, `@research:`,
`@bead:`, `@stitch:` all resolve by *reading the sidecar checkout you already have*.
None of them materialize a local shadow copy in a live-object namespace. `@agent:`
alone was given a replication engine — and it is the only one with collision, quarantine,
transaction-recovery, and adoption machinery.

### 3.4 The cost is not hypothetical — it is already breaking commits at N=1

From `stitch_timeout_hardening` (2026-09-04): nine of twenty-five finalizer runs on
apollo (36%) hit the wall-clock cap on Sep 3–4. **Seven died after the commit had
already landed**, during post-commit tail work; one was "visibly stuck on
`.git/index.lock` in the `agents` sidecar — which, unlike `beads`, `plans`, and
`linked`, exists **once per project** and is shared by every concurrent agent on the
host."

This is a direct consequence of the documented design: the commit path "records an
outbox request for the exact hood and immediately drains it under the bounded agents
lock, so the commit does not return until the hood is published and pushed." A durable
outbox exists precisely so that publication *can* be deferred — and then the commit path
drains it synchronously anyway, putting a shared-lock, network-push, whole-hood
re-render on the critical path of every commit.

With N users pushing to one `sase--agents` remote, this gets worse in two compounding
ways: the local `index.lock` contention becomes remote non-fast-forward contention, and
the documented recovery is "a non-fast-forward rejection triggers **one**
pull/recompute/commit/push retry." One retry is not a concurrency-control strategy for
five writers.

### 3.5 What is genuinely worth keeping

Not everything here is waste. The following are artifact-plane and valuable:

- **The prompt archive** (`prompts/<YYYYMM>/<name>.md`, 4,948 entries). Durable,
  addressable, human-readable provenance for "what was this agent actually asked?",
  with `PLAN`/`AGENTS`/`ARTIFACTS` header links and durable `@`-reference staging. This
  is the best thing the subsystem produces and it is exactly the record a *teammate*
  wants six months later.
- **`@agent:` pages** as citable artifacts for plans, beads, and patches — but see
  §2.3; they must resolve, and today cross-machine ones do not.
- **Content-addressed `files/objects/sha256/`** for prompt attachments. Correct design:
  identical bytes publish once, clean tracked files link to hosted blobs instead of
  being duplicated.
- **Commit ↔ agent ↔ bead provenance.** The `SASE_AGENT` footer, the family page as the
  durable home of a family's commits, and bead `created_by` links are the audit trail
  that makes agent-authored code reviewable at all. In a team, this stops being a nicety
  and becomes the mechanism by which a reviewer knows *what instruction produced this
  diff*.

### 3.6 Verdict

**Change it, aggressively — keep publication, delete import.** Specifically:

| Component | Verdict | Why |
| --- | --- | --- |
| Prompt archive | **Keep** | Highest-value artifact in the subsystem |
| `files/objects/` CAS | **Keep** | Correct, cheap, dedupes by construction |
| Commit/bead provenance links | **Keep + fix** | Currently emits dead double-qualified links (§2.3) |
| `@agent:` page publication | **Keep, narrow** | Publish pages for runs with a durable reference (commit, plan approval, bead association, explicit citation) — not every run in every hood |
| Chat publication | **Opt-in** | 7,353 transcripts; largest byte contributor; highest privacy surface in a shared repo |
| Synchronous drain on commit path | **Remove** | Already causing finalizer kills at N=1; the outbox already provides the durability |
| Full-hood reconcile every 10 min | **Remove** | Replace with outbox drain on an AXE lane |
| **v2 import leg** | **Remove** | ~9,400 lines to produce dismissed rows; 0 successful imports; 1,375 pending |
| Legacy v1 leg | **Remove** | Already sunsetting under the `v1-import-retired` decision |
| Name-registry claims from imports | **Remove** | The root cause of the wedge; provenance must not occupy the live-name namespace |
| Cross-machine family revival | **Keep as an explicit pull** | Real capability; does not require eager import (§6.5) |

---

## 4. The gaps that actually block collaboration

### 4.1 The review loop is half-built — this is the #1 gap

`fork_contributor_harness` found it and it is still true at `5aa3225`:

```python
# sase-github/src/sase_github/workspace_plugin.py:224
def ws_supports_reviewer_comments(self, pr_url: str) -> bool | None:
    """GitHub does not support reviewer comments via critique_comments."""
```

Verified today: the plugin contains **no** `gh pr review` call, no review-comment fetch,
and no review-state handling of any kind.

The asymmetry is stark. SASE can produce review feedback (mentors — LLM reviewers that
match profiles against commits, emit structured `error`/`warning`/`suggestion` JSON, and
feed an apply-agent through the `COMMENTS` → CRS workflow) but cannot **consume** it. The
`COMMENTS`/CRS machinery is provider-neutral and fully built; the GitHub provider simply
declines to feed it.

That means today: a teammate reviews your PR on github.com, and SASE knows nothing. No
comment lands in the Patch, no CRS agent is offered, no status transition reflects
`CHANGES_REQUESTED`. The `Mailed → Submitted` lifecycle has no review state in it at
all. **The most valuable single feature in this entire report is wiring inbound GitHub
review comments into the CRS machinery that is already sitting idle**, because it turns
a human reviewer's comment into an agent task automatically — which is the actual
promise of agentic collaboration.

Two related, already-diagnosed blockers: SASE creates no `upstream` remote for forked
clones, so a fork-based project silently opens fork→fork PRs (`GH_REPO` is a measured
one-env-var mitigation; the durable fix is `_clone_gh_repo` adding the remote), and a
second GitHub identity is *mandatory* to test any of this because GitHub hard-blocks
self-approval.

### 4.2 The Patch is machine-local and mixes two planes

Patches live in `~/.sase/projects/<key>/<key>.sase` — never shared. Verified locally:
1 active Patch, 264 archived, entirely on this machine.

Two separate problems:

1. **Plane mixing.** The same file's project-metadata header carries a `RUNNING:` block
   of live host process state:

   ```text
   RUNNING:
     #10 | 25286 | ace(run)-260901_063906 | gh_sase-org__sase | 20260901063906 | PINNED
     #12 | 62990 | ace(run)-260904_113036 | gh_sase-org__sase | 20260904113036
   ```

   PIDs and workspace numbers (plane 2) in a document about change units (plane 1). Any
   attempt to share the ProjectSpec inherits this, and it is exactly the kind of
   host-local state the agents-sidecar allowlist correctly excludes.

2. **No shared view.** With Patches machine-local, two collaborators cannot see each
   other's in-flight change units, dependency chains (`PARENT:`), or hook status.

The fix is *not* to sync ProjectSpec files. It is to recognize that **the PR is already
the shared record** and make the Patch a two-tier object: shared fields projected from
the PR, private fields kept local. `external_pr_mirror` already implements the
projection direction.

### 4.3 Attention does not cross a user boundary

Gates and notifications are `~/.sase/interaction_requests/` and
`~/.sase/notifications/notifications.jsonl` — one SASE home, one person. Telegram and
the mobile gateway are same-user remote projections of that inbox, not multi-user
routing.

In a team, the recurring question is "this decision is blocked on a human — which human,
and how do they find out?" There is no answer today, and `gates-never-block` means the
agent that raised the gate has already ended its turn, so the decision has to reach a
person out-of-band.

### 4.4 Write-path economics do not survive N writers

Summarized from §3.4 and §2.1:

| Store | Push policy | Concurrency safety | Verdict at N users |
| --- | --- | --- | --- |
| Beads (canonical event store) | Synchronous + **publication verification that fails the command** | Duplicate-ID relocation resolver; append-mostly JSONL | **Correct.** Keep synchronous; harden retry |
| Agents sidecar | Synchronous drain on commit path, **one** non-fast-forward retry, one shared per-project clone | Bounded lock; whole-hood re-render | **Wrong.** Already failing at N=1 |
| Plans / research | Ordinary commits | Human-authored, low rate | Fine |

The distinction is principled and should be stated as policy: **synchronous
push-and-verify is justified for authoritative state, and unjustified for projections.**
A bead close that is lost is data loss. An agent page that publishes ninety seconds late
is a cache miss.

### 4.5 Everything else is fine

Worth saying explicitly, because it constrains scope: workspaces, agent naming, memory,
plans, research, artifact references, xprompts, and the primary-repo git workflow all
work unmodified with N users. No change needed. The temptation to build a "collaboration
system" should be resisted in favor of five targeted changes.

---

## 5. Alternatives considered and rejected

### 5.1 A central SASE server / hosted service

Every collaborator connects to one service holding beads, patches, agent state, and
attention routing. Rejected: it introduces the one failure domain SASE currently does
not have, requires operating infrastructure, breaks the offline-first property that
makes the git plane work (`athena` has been offline for days and its history stays
readable), and duplicates services the team already runs (GitHub). The
`corpus-before-mechanism` decision applies directly: do not build retrieval or routing
machinery ahead of a corpus that demonstrably needs it. At 2–5 collaborators there is no
such corpus.

### 5.2 CRDTs / operational sync for shared state

Rejected as solving a problem SASE does not have. Bead events are append-mostly with a
deterministic reducer and an existing relocation resolver for the one real conflict
class (concurrent ID minting). Plans and research are human-authored prose reviewed
through PRs — where merge conflicts are *desirable* signal. A CRDT layer would add a
consistency model to state that is already convergent and remove the review step from
documents whose whole purpose is being reviewed.

### 5.3 Extend the tailnet host daemon across users

Tempting, because `tailnet_agent_fleet` already specifies a supervised per-machine
gateway with typed mutations, idempotency journals, and revision fencing — and Tailscale
supports multi-user tailnets with per-user ACLs. **Rejected**, for four reasons:

1. **It answers a question nobody asked.** No teammate needs to kill your agent. The
   mutation surface (launch, kill, retry, answer-question, gate-approval) is
   self-management, not collaboration.
2. **It converts a UX problem into a security problem.** Within one user, a mis-scoped
   token is an inconvenience. Across users it is an authorization boundary requiring a
   real permission model, per-user audit, and a threat model for "teammate kills my
   in-flight epic."
3. **It requires reachability where collaboration must not.** Colleagues are on
   different networks, asleep, on leave, or gone. Anything routed through their host
   daemon disappears with them. Artifacts do not.
4. **It repeats the `agents_sync` mistake at a higher cost.** Process state crossing a
   user boundary is the exact category error §3.3 identifies — this time with a live
   mutation channel instead of a git repo.

The fleet daemon is a good design *for its stated scope*. Keep the scope.

### 5.4 Keep `agents_sync` and scale it (the status quo)

Fix the v1 wedge, add the missing manifests, keep replicating everything. Rejected on
arithmetic: ~100 sidecar commits/day/user against one shared remote, with one
non-fast-forward retry, a per-project single clone, and a synchronous drain on the
commit-critical path that is *already* killing finalizers at N=1. Five users is 500
commits/day into one repo whose working tree is already 79,386 files. The subsystem
would need per-user sharding, an async publisher, and a real backoff strategy — which is
most of the recommended work anyway, spent to preserve an import leg with zero
demonstrated consumption.

### 5.5 Share ProjectSpec files through a sidecar

Rejected. It would publish PIDs and workspace numbers (§4.2), create a high-rate
multi-writer store for a document with no merge semantics, and duplicate a record —
the PR — that is already shared, already has review threads, and is already the thing
CI and humans look at. Mirror from the PR instead.

---

## 6. Recommended architecture

### 6.1 Shape

```text
                      THE ARTIFACT PLANE  (git · shared · offline-durable)
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  sase-org/sase          code + sase/memory/  ← PRs, review, CODEOWNERS   │
   │  sase-org/sase--plans   plans + canonical bead store (claims, assignee)  │
   │  sase-org/sase--research   research reports                             │
   │  sase-org/sase--agents  prompt archive + referenced agent pages + CAS    │
   └──────────────────────────────────────────────────────────────────────────┘
        ▲ authoritative, synchronous+verified      ▲ projection, async, off critical path
        │ (beads)                                  │ (agents)
   ─────┼──────────────────────────────────────────┼──────────────────────────────
        │        alice                             │        bob
   ┌────┴───────────────────────┐            ┌─────┴──────────────────────┐
   │ PROCESS PLANE (per user)   │            │ PROCESS PLANE (per user)   │
   │  mbp ─ host daemon ─┐      │            │  laptop ─ host daemon      │
   │  apollo ─ host daemon┼ ACE │  ✗ never ✗ │  desktop ─ host daemon     │
   │  athena ─ host daemon┘     │ ◀────────▶ │                            │
   │  (tailnet, single-user)    │  no link   │  (tailnet, single-user)    │
   └────────────────────────────┘            └────────────────────────────┘
        │                                          │
        └───────── ATTENTION PLANE ────────────────┘
          within a user: gates, notifications, Telegram, mobile gateway
          across users:  GitHub review requests + bead assignment (no new transport)
```

### 6.2 Plane-by-plane policy

**Artifact plane.** The only cross-user channel. Two write classes with different
policies:

- *Authoritative* (beads): synchronous commit, push, and verify; fail loudly on
  unpublished state. Already implemented; harden the retry loop (§6.6).
- *Projection* (agent pages, prompt archives, bead pages): asynchronous, batched,
  off any command's critical path, idempotent, safe to be minutes stale.

**Process plane.** Strictly single-user. Build `tailnet_agent_fleet` as specified,
with one amendment (§6.5): its offline-host story should rest on a **client-side
per-host snapshot cache**, not on the git import leg. A cache is the right mechanism
for "show me what I last saw"; git replication is an extraordinarily expensive way to
obtain one, and it is the mechanism this report recommends deleting.

**Attention plane.** Within a user, unchanged. Across users, **map onto substrates the
team already shares** — GitHub review requests, `@mentions`, issue assignment, and bead
`assignee` — rather than building a cross-user gate transport. This preserves
`gates-never-block`, adds no failure domain, and gives every collaborator notifications
on the channels they already watch (email, GitHub mobile). ACE's contribution is two
*views*, not a transport: "reviews requested of me" and "beads assigned to me."

### 6.3 Identity: one join key, three surfaces

`id.username` becomes the person join key everywhere a person can appear.

1. **A project roster in the shared plane** — `sase/collaborators.yml` in the
   primary repo, so the roster is itself reviewed through a PR:

   ```yaml
   roster:
     - username: bbugyi200        # SASE username, the join key
       github: bbugyi200
       display: Bryan Bugyi
       role: maintainer
     - username: someone_else
       github: someone-else
       role: contributor
   ```

   Reviewed, versioned, offline-readable, and it makes "who is on this project" a fact
   rather than an inference from git history.

2. **Beads gain a `username`-shaped assignee.** Today `assignee` holds an agent name
   and `owner` holds a git email. Introduce a qualified spelling — `alice` for a person,
   `alice/<agent-global-name>` for that person's agent — so `sase bead list --mine`,
   "who has this," and the claim reconciler all work across users. **Safety rule: the
   `bead_claim_checks` reconciler must never release a claim whose username is not the
   local user's.** It currently releases only when it can resolve the owning agent's
   artifact locally, which for a foreign claim it cannot — so today's behavior is
   accidentally correct. Make it explicit before it is refactored.

3. **Fix double-globalization.** `machine_hood` qualification is documented as
   idempotent for the *local* owner; the bead-page renderer is applying it to names that
   are already global for a *different* owner, producing dead links (§2.3). Every
   provenance link in a shared artifact must be built from the canonical global name,
   never re-qualified.

### 6.4 Close the review loop (highest leverage)

1. **Implement `ws_supports_reviewer_comments` for GitHub.** Fetch PR review comments
   and threads (`gh api repos/{owner}/{repo}/pulls/{n}/comments`, plus reviews for
   state), normalize into the existing structured comment JSON the mentors already
   emit, and write them into the Patch `COMMENTS:` section keyed by reviewer. The CRS
   apply-agent then works unchanged: **a human's review comment becomes an agent task.**
   Store resolution state so a resolved thread stops re-proposing work.
2. **Model review state in the Patch lifecycle.** `APPROVED` /
   `CHANGES_REQUESTED` / `REVIEW_REQUIRED` alongside `STATUS:`, so `Mailed → Submitted`
   respects it and ACE can show "blocked on review" versus "blocked on CI."
3. **Generalize `external_pr_mirror` into the team case.** It already adopts other
   people's PRs. Add author-scoped mirroring driven by the roster, so a teammate's PR
   becomes a Patch you can run mentors against and open a review agent on. This is the
   one place where SASE's agent machinery has an obvious, large, unique payoff in a team:
   *your mentors review your teammate's PR before you read it.*
4. **Fix the fork path**: add an `upstream` remote in `_clone_gh_repo` when
   `gh repo view --json parent` reports one, and propagate it through
   `ensure_git_clone_at` so numbered workspaces inherit it. `GH_REPO` is the measured
   interim mitigation.
5. **Provision the machine account** from `fork_contributor_harness` (classic PAT or
   OAuth, never fine-grained). Two identities are mandatory: GitHub hard-blocks
   self-approval, so none of the above can be tested end-to-end without it.

### 6.5 `agents_sync`: publish-only, lazily resolved

- **Delete the import leg** (`v2_import_*`, `incoming_cache*`, `v1_*` — ~9,400 lines,
  32 modules) behind a sunset flag per `sase/memory/sase_flags.md`. Nothing is lost that
  is not recoverable from the sidecar checkout on demand.
- **Resolve `@agent:` refs lazily**, like `@plan:` and `@research:` — read the page out
  of the sidecar clone at `~/.sase/projects/<key>/repos/agents`. Same UX, no local
  materialization, no name-registry claims, no import transactions, no quarantine.
- **Replace eager import with an explicit pull** for the one real capability: keep
  cross-machine family revival as `sase agent import <agent-ref>`, reading revival
  inputs from the sidecar at the moment the user asks for them. A user-initiated,
  one-shot, foreground operation with a clear failure mode — instead of a continuously
  reconciling engine whose failures accumulate silently to 1,375.
- **Narrow publication** to runs with a durable reference: a commit, an approved plan, a
  bead association, or an explicit `@agent:` citation. `athena`'s 10,229 pages become a
  small fraction of that. Everything else stays local, where it already is.
- **Make chats opt-in** (`agents_sync.publish_chats: false` by default). 7,353
  transcripts is both the byte bulk and, in a *team* repo, the largest privacy surface —
  and the docs are explicit that publishing exposes data to everyone who can read the
  remote.
- **Move publication off the commit-critical path.** The durable outbox already exists;
  let an AXE lane drain it. This is independently the recommendation of
  `stitch_timeout_hardening` ("remove bootstrap and publication work from the
  commit-critical path"). Keep the *bead* store synchronous and verified.

Projected effect (a projection, not a measurement): sidecar commits from ~100/day to
roughly the prompt-archive rate; tracked files from 79,386 toward the low thousands;
~9,400 lines of the most conflict-prone code in the tree deleted; and the commit path
loses a shared-lock network push.

### 6.6 Write-path hardening for N writers

- **Beads**: keep synchronous push + publication verification. Add bounded exponential
  backoff with jitter in place of the single retry, and add a `.gitattributes` union
  merge driver for the append-only `events/**` streams and the ID-sorted `issues.jsonl`
  projection so ordinary concurrent appends never reach the conflict resolver at all.
  Reserve the relocation resolver for genuine ID collisions.
- **Agents sidecar**: asynchronous drain, batched, with backoff. Because it is a
  projection, a rejected push is a retry, never a user-visible failure.
- **Machine-level admission**: a host-scoped runner-slot guard so two SASE homes on one
  machine cannot jointly oversubscribe it (§2.4).
- **Bead ID minting**: the relocation resolver is a good backstop, but per-writer
  minting ranges (or a username-derived discriminator on the counter) would make most
  collisions structurally impossible. Worth doing only if measurement shows relocations
  actually occurring — otherwise it is mechanism ahead of corpus.

---

## 7. The explicit answer: keep / change / remove

**Change it — by removing half of it.**

- **Remove:** the v2 import leg, the legacy v1 leg, import-created name-registry claims,
  full-hood 10-minute reconciliation, and the synchronous drain on the commit path.
- **Keep:** the prompt archive, the content-addressed file store, commit/bead/agent
  provenance links, and `@agent:` pages.
- **Change:** publish only referenced runs; chats opt-in; publication asynchronous and
  batched; `@agent:` resolves lazily from the sidecar clone; cross-machine revival
  becomes an explicit `sase agent import`.

The one-line rationale: **`agents_sync` is a good artifact publisher wrapped around a
bad process replicator.** Keep the publisher. Delete the replicator. What remains is
smaller, faster, cheaper, survives a second user, and loses no capability that anyone has
been observed to use.

---

## 8. Phasing

Each phase is independently useful, independently revertible, and behind a feature flag
per `sase/memory/sase_flags.md`.

| Phase | Deliverable | Why here |
| --- | --- | --- |
| **0** | Move agents publication off the commit-critical path (AXE-lane outbox drain). Fix double-globalized provenance links. | Pure win at N=1; already causing finalizer kills; unblocks everything else |
| **1** | Lazy `@agent:` resolution from the sidecar clone + `sase agent import <ref>` for explicit revival | Preserves the capability the import leg exists for, without the engine |
| **2** | Sunset and delete the v2/v1 import legs and their registry claims | Safe once Phase 1 covers the use case; removes ~9,400 lines |
| **3** | Narrow publication to referenced runs; chats opt-in | Cuts sidecar growth an order of magnitude before a second user arrives |
| **4** | `sase/collaborators.yml`; `username` join key on beads; foreign-claim safety rule in `bead_claim_checks` | Identity must land before anything can be addressed to a person |
| **5** | **Inbound GitHub review comments → Patch `COMMENTS` → CRS**; review state in the Patch lifecycle | The highest-leverage collaboration feature; needs the machine account to test |
| **6** | Roster-driven `external_pr_mirror`; run mentors on a teammate's PR | Where SASE's agent machinery pays off uniquely in a team |
| **7** | Split `RUNNING:` out of ProjectSpec; two-tier Patch (PR-projected shared fields, local private fields) | Cleans the plane mixing; makes the Patch honest about what is shared |
| **8** | ACE views: "reviews requested of me", "beads assigned to me"; machine-level admission guard | Attention surfacing without a new transport |
| **9** | Bead write-path hardening: union merge driver, backoff | Do when measurement shows contention, not before |

Phases 0–3 are subtractive and pay for themselves immediately, at N=1, before any second
user exists. Phases 4–6 are the actual collaboration feature. Phases 7–9 are polish and
scale.

---

## 9. What would reopen this decision

- **More than ~8–10 active collaborators**, or a sustained shared-store write rate where
  git push contention becomes the binding constraint rather than review throughput. At
  that point the beads store wants a real backend, not a better merge driver.
- **A genuine need to run agents on someone else's hardware** — a shared build farm, a
  team-owned high-capacity machine (cf. `temporary_high_capacity_test_machine`). That is
  a multi-tenant scheduler, a different feature, and it would justify a cross-user
  control plane with a real permission model.
- **Cross-user agent-to-agent coordination** — one person's agent blocking on another
  person's agent. A genuinely different topology; the same threshold
  `tailnet_agent_fleet` names for reconsidering a broker.
- **A non-GitHub VCS host becoming primary**, which would break the "route attention
  through GitHub" recommendation in §6.2 and force a native attention transport.
- **Evidence that the import leg was actually load-bearing.** If cross-machine dismissed
  history turns out to be used regularly (§10, Q1), Phase 2 should be re-scoped to keep
  a much thinner import that materializes *only* referenced runs on demand.

---

## 10. Open questions for the user

1. **Has cross-machine agent revival ever actually been used?** Phase 1 preserves the
   capability, but the answer determines whether `sase agent import` needs to be
   pleasant or merely present.
2. **Should the `sase--agents` sidecar be private?** The docs are explicit that
   publishing exposes prompts, chats, and output variables to everyone who can read the
   remote. That is a very different risk at N=1 (your own repo) than at N=5 (a team repo
   whose prompts may quote customer data). Recommendation: private by default for any
   project with a roster of more than one.
3. **Do collaborators share a `sase.yml`, or does each bring their own?** Mentor
   profiles, file hooks, and commit hooks are arguably project policy (shared, reviewed)
   rather than personal preference. The deep-merge system already supports both; the
   question is which layer owns what once more than one person is affected by the answer.
4. **Is "my mentors review your PR" desirable, or intrusive?** Phase 6 is the highest
   unique value in this report, but automated LLM review of a teammate's PR is a social
   decision before it is a technical one. It may want to be opt-in per reviewer, or to
   post to your own Patch rather than to the PR.
5. **Should the tailnet fleet ever show a *teammate's* hosts in read-only mode?** This
   report says no (§5.3). If the answer is "yes, eventually," the wire model should
   reserve a place for it now, because retrofitting an authorization boundary is much
   harder than designing one in.

---

## 11. Recommended solution

**Adopt one rule — *cross a user boundary as an artifact, never as a process* — and
implement it by shrinking `agents_sync` to a publisher, adding an identity join key, and
closing the review loop.**

Concretely, in priority order:

1. **Move agents-sidecar publication off the commit-critical path** and fix the
   double-globalized provenance links. Both are bugs today, at one user, on one machine.
2. **Make `@agent:` resolve lazily from the sidecar clone**, like every other artifact
   reference, and provide `sase agent import <ref>` for explicit cross-machine revival.
3. **Delete the v2 and v1 import legs** (~9,400 lines, 32 modules) and the name-registry
   claims they create. Narrow publication to runs with a durable reference; make chat
   publication opt-in.
4. **Add `sase/collaborators.yml` and a `username` join key** on beads, patches, and claims,
   with an explicit rule that the claim reconciler never releases a foreign claim.
5. **Implement inbound GitHub review comments** into the Patch `COMMENTS` section and
   the existing CRS apply-agent, model review state in the Patch lifecycle, fix the fork
   `upstream` remote, and provision the machine account so the loop can be tested.
6. **Route cross-user attention onto GitHub review requests and bead assignment**, and
   surface both in ACE. Build no new gate transport.
7. **Keep the tailnet host daemon strictly single-user**, and give it a client-side
   per-host snapshot cache for offline rendering instead of depending on the git import
   leg this report removes.

This is a net *reduction* in system size that leaves SASE meaningfully more capable in a
team: it deletes the subsystem that has produced 32% fix commits, 1,375 stalled imports,
and at least one class of finalizer failure, and it spends a fraction of that budget on
the one loop that actually makes agentic collaboration work — a teammate's review comment
becoming an agent's task.

---

## 12. Sources

**Repo evidence** (verified 2026-09-04 against `sase` @ `a81bc8d59`, `sase-github` @
`5aa3225`): `src/sase/agents_sync/` (83 modules; import leg `v2_import_*`,
`incoming_cache*`, `v1_*`), `src/sase/bead/` (`conflict_resolver.py`, `relocation.py`,
`claims.py`, `_db_schema.py`, `sync.py`), `src/sase/default_config.yml:270-273`
(`agents_sync` cadence), `sase-github/src/sase_github/workspace_plugin.py:224`,
`~/.sase/projects/gh_sase-org__sase/gh_sase-org__sase.sase` (`RUNNING:` block),
`~/.sase/projects/gh_sase-org__sase/repos/agents` (3,758 commits / 79,386 files /
108.22 MiB / 10,488 agent pages / 7,353 chats / 4,948 prompts),
`sase agent sync --check --json` (1,375 + 81 pending hoods), `sase bead show sase-w3.6`
(dead provenance link).

**Docs:** `docs/agents_sidecar.md`, `docs/beads.md`, `docs/change_spec.md`,
`docs/project_spec.md`, `docs/configuration.md` (Owner Identity, `external_mirror`),
`docs/axe.md` (`external_mirror` lane), `docs/mentors.md`, `docs/vcs.md`,
`docs/notifications.md`.

**Prior research:** `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`,
`research:202609/athena_agent_sync_repair/athena_agent_sync_repair.md`,
`research:202609/stitch_timeout_hardening/stitch_timeout_hardening.md`,
`research:202608/fork_contributor_harness/fork_contributor_harness.md`,
`research:202607/shared_sdd_clone_consolidated.md`.

**Decision records:** `decisions:gates-never-block`, `decisions:single-turn-agents`,
`decisions:host-owned-completion`, `decisions:v1-import-retired`,
`decisions:two-speed-verification`, `decisions:corpus-before-mechanism`,
`decisions:rust-core-required`.

**Core memory:** `rust_core_backend_boundary` (any wire model, retry classification, or
identity resolution added here belongs in `sase-core`, not in Python).

---

## Appendix A — Parallel independent analysis (`research.7.cdx`)

Two agents researched this question concurrently and each produced a complete report.
The body above is `research.7.cld`'s. This appendix is `research.7.cdx`'s report —
originally titled *SASE collaboration architecture* — reproduced verbatim with its
headings demoted one level. The two agree on the load-bearing conclusions (make the
forge-backed Patch/PR plane the collaboration boundary, retire the `agents_sync` import
leg while keeping durable published provenance, and keep the tailnet host daemon
single-user); they differ in evidence, emphasis, and phasing detail. Neither has been
edited to agree with the other, and this document has not yet been consolidated into a
single narrative.

**Date:** 2026-09-04  
**Status:** Research recommendation; not an approved implementation direction  
**Question:** How should SASE support multiple users, including multiple users on one
machine, developing the same project concurrently through a pull-request workflow? What
should happen to the current cross-machine agent-sync system, and how should the proposed
single-TUI tailnet fleet fit into the result?

### Executive conclusion

SASE should make the **Patch and its pull request**, not the agent, the unit of
collaboration.

The right architecture has three deliberately separate planes:

1. **Personal execution plane:** each SASE host is authoritative for the processes and
   workspaces it runs. One user's ACE TUI may observe and control that user's hosts over
   the tailnet using the HTTP+SSE host-daemon design from
   [the fleet research](tailnet_agent_fleet/tailnet_agent_fleet.md). This plane is for
   live, private, high-fidelity state.
2. **Project collaboration plane:** the Git forge is authoritative for work intent,
   branches, pull requests, review, CI, mergeability, and integration. SASE projects a
   provider-neutral Patch model onto those forge objects. This is the boundary shared by
   different users and does not require them to share a tailnet or a SASE data directory.
3. **Run archive plane:** a terminal agent may publish a minimal, immutable provenance
   manifest and optional content-addressed artifacts linked from its Patch/PR. Archives
   are fetched on demand; they are not imported into every user's local agent store.

The current `agents_sync` implementation should therefore be **retired as an automatic
replication and collaboration mechanism**. The existing agents sidecar should remain
readable for compatibility and can become the first backend for the new lazy archive,
but the behaviors that clone every enabled project's archive, periodically inspect it,
publish complete active hoods, rebuild shared indexes, and materialize foreign runs as
local dismissed agents should be removed.

This is a change, not a total deletion: retain durable, commit-linked provenance; remove
eager synchronization and the fiction that another user's historical agent is a local
agent. The tailnet fleet does not replace the shared PR plane, and the PR plane does not
replace the user's live fleet.

### Method and evidence

This report examined:

- `sase` at `a81bc8d5982c01c951294da4a1d3d0c22d844176`, especially
  `src/sase/agents_sync/`, `docs/agents_sidecar.md`, the Patch/Stitch workflow, ACE's
  sync surfaces, owner identity, prompt publication, and artifact resolution.
- `sase-github` at `5aa32258103c8faa39efef3ba546e8f3e79b0527`, especially its
  VCS/workspace provider hooks and normalized issue and PR records.
- The live `sase--agents` checkout at
  `9a97e9422e6eee999a510098ab73087756a31124`.
- [Managing SASE Agents Across A Tailscale Fleet From One ACE
  TUI](tailnet_agent_fleet/tailnet_agent_fleet.md), treated as an unapproved but useful
  direction.
- [Athena Agent Sync Repair](athena_agent_sync_repair/athena_agent_sync_repair.md),
  including the v1/v2 migration and identity failures it documented. Several of its
  immediate repair recommendations have since landed; its failure history remains
  evidence about the transport's state-space cost.
- Primary GitHub, Git, Tailscale, and local-first sources linked throughout this report.

The sidecar measurements below are a point-in-time sample from one large project and
must not be mistaken for a cross-project benchmark. They are nevertheless valuable
because the sample contains only one user across two machines: it is a lower-complexity
case than the multi-user design must support.

### What collaboration should mean in SASE

Collaboration is not “I can see every agent everybody has ever run.” It is the ability
for people and their tools to develop one codebase concurrently while maintaining
awareness, isolation, review, integration safety, attribution, and useful handoff.

The durable object hierarchy should be:

```text
Project (forge repository)
└── Work item (issue or another provider-backed task)
    ├── Patch A  <──>  branch + pull request
    │   ├── agent run/family 1
    │   ├── agent run/family 2
    │   └── stitches  <──>  commits
    └── Patch B  <──>  another branch + pull request
        └── intentionally competing or alternative work
```

This model gives collaboration seven concrete meanings:

1. **Awareness.** A contributor can see that a work item or code area already has an
   active Patch/PR, who owns it, what base and branch it uses, when it last changed, and
   whether it is draft, blocked, awaiting review, failing checks, or ready to merge.
2. **Isolation.** Each Patch has its own branch and SASE workspace. Different agents and
   users do not share a mutable checkout. Git explicitly supports multiple worktrees and
   branches for concurrent work, although SASE's numbered-clone workspace model can
   remain its local implementation ([Git worktree
   documentation](https://git-scm.com/docs/git-worktree.html)).
3. **Coordination without false locking.** Work-item claims and overlap warnings are
   advisory. SASE warns before duplicating an issue or heavily overlapping another open
   PR, but permits intentional alternative implementations. A disconnected laptop must
   not hold an unbreakable distributed lease on a project.
4. **Review and steering.** Humans and agents exchange requests through the PR timeline,
   where comments, line suggestions, approvals, and change requests are already visible
   to the team. GitHub's review model provides all four and can require approvals before
   merge ([GitHub pull request reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews)).
5. **Safe convergence.** CI, branch rules, CODEOWNERS, and the merge queue decide when
   work may land. A merge queue retests proposed changes against the latest base and the
   work ahead of them instead of requiring every author to manually serialize updates
   ([GitHub merge queues](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)).
6. **Attribution and audit.** A Patch records its human principal, contributing run IDs,
   commits, reviews, and terminal result. This is provenance for a proposed code change,
   not a wholesale copy of the worker's private environment.
7. **Handoff.** Another authorized user can check out the branch, inspect the PR and its
   minimal run manifest, continue the Patch, or launch a new run. Handoff does not
   require importing the original worker's agent into the new user's local namespace.

Two tempting goals are explicitly out of scope for the collaboration foundation:

- live multi-user editing of one checkout; Git and PRs provide batch convergence, so a
  CRDT for source files would add a second merge model;
- implicit cross-user control of agent processes. A teammate may request a change or a
  handoff through the PR, but must not gain `kill`, `launch`, or raw-transcript access
  merely by having repository read access.

This preserves the most useful local-first properties: work remains fast and available
offline, source and local agent state remain under the user's control, and collaboration
occurs when durable changes are exchanged. The local-first literature explicitly
describes Git-style pull requests as a legitimate batched collaboration model, distinct
from real-time shared-document replication ([Kleppmann et al., “Local-first
software”](https://www.inkandswitch.com/essay/local-first/)).

### The current agent-sync solution

#### What it does well

The present v2 system is carefully engineered. It provides:

- owner-sharded authority at `users/<username>/machines/<machine>/manifest.json`;
- strict, bounded schemas, SHA-256 file references, portable metadata allowlists, and
  relationship validation through the Rust identity boundary;
- atomic publication and per-hood transactional import;
- durable outboxes, receipts, recovery journals, quarantine, retirement, and a bounded
  non-fast-forward retry;
- prompt, chat, commit, family, relationship, and output-variable preservation;
- offline durability independent of a running SASE service;
- project-scoped access inherited from the agents repository;
- deterministic Markdown pages and `@agent:` references.

Those are real capabilities. In particular, the offline-machine property emphasized by
the tailnet fleet report is worth preserving: a host disappearing should not destroy the
only record of work that affected the project.

#### Its actual shape

`sase agent sync` is a full-duplex Git transaction per selected project:

```text
resolve every selected/enabled project
  → acquire the agents-repository lock
  → pull --rebase
  → validate and import foreign owner hoods into local agent history
  → inventory locally owned hoods
  → regenerate owner snapshots and shared Markdown indexes
  → restore deferred prompt archives
  → commit generated paths
  → push, with one pull/recompute/push retry on non-fast-forward
  → drain Referenced By writes into other sidecars
```

The commit path also publishes prompt archives and the committing agent's complete hood
synchronously when possible, falling back to durable outboxes. Periodic ACE detection
fetches agents repositories for all enabled projects; a full unscoped sync also targets
all enabled projects. Remote v2 runs are not merely displayed: they are transformed into
terminal local artifacts, dismissed bundles, permanent-name claims, and saved-family
records so they can be revived locally.

The subsystem's implementation size is a warning about conceptual width, not a criticism
of code quality:

| Measure | Current sample |
| --- | ---: |
| `src/sase/agents_sync/` | 83 files, 20,645 lines |
| `tests/agents_sync/` | 60 files, 14,168 lines |
| Commits touching `src/sase/agents_sync/` since its 2026-07-22 introduction | 111 |
| Additional cross-cutting callers/tests | Not included above |

#### Observed scale

On 2026-09-04, the live agents sidecar for `sase`—one user, two machines, initialized
2026-07-23—had:

| Measure | Observed value |
| --- | ---: |
| Checkout disk allocation | 662 MiB |
| `.git` disk allocation | 135 MiB |
| Packed Git objects | 108.22 MiB across 293,043 objects |
| Current-tree blob bytes | 282.6 MiB |
| Tracked paths | 79,386 |
| Per-agent directories | 10,826 |
| Hood snapshots | 2,016 |
| Git commits | 3,758 |
| `chore(agents): sync ...` commits | 2,019 |
| `chore(agents): archive ...` commits | 1,722 |

The `agents/` working tree alone occupies about 455 MiB even though all `chat.md` files
sum to about 49 MiB and all `prompt.md` files to about 8 MiB. Much of the cost is the
filesystem and Git-index overhead of tens of thousands of small generated files.

The September Athena repair research found a more important scaling symptom: a full
validation pass over roughly 2,000 hoods took minutes and launched tens of thousands of
per-file `git show` subprocesses. It also documented a destination wedged by 338 lossy v1
imports that blocked 1,948 v2 hoods through name-registry collisions. The v1 import has
since been retired behind a sunset path and batching work has landed, but the episode
shows how replication, migration, display naming, provenance, revival, and permanent
name allocation amplify one another.

#### Why it is not a collaboration architecture

The current solution answers “how do I reproduce remote agent history locally?” It does
not answer the questions collaborators actually need:

- Which issue or Patch is this work for?
- Is there already an open PR?
- What files or subsystem are likely to overlap?
- Who owns the decision, who should review it, and who can merge it?
- Are checks passing against the current base?
- Is the change in the merge queue?
- How should a teammate request another iteration?

The sync does contain commit associations, but the agent hood remains the primary
replication object and the PR remains secondary. For team development, that priority is
backward.

#### Principal problems

1. **It conflates six products.** Provenance archive, prompt archive, artifact hosting,
   live-status discovery, cross-machine revival, and collaboration are one Git protocol.
   Each has different consistency, retention, privacy, and latency requirements.
2. **It scales with accumulated history rather than active collaboration.** Every
   enabled project carries a growing sidecar and local Git index. A collaboration view
   should normally scale with open work items and PRs, while old run bodies are fetched
   only when requested.
3. **It turns observation into local mutation.** Importing a foreign run creates local
   artifacts, dismissed state, family projections, registry claims, receipts, and
   recovery journals. A remote terminal record should be observable without pretending
   it ran locally. Revival should create a new local run from a selected archive, not
   import the old run wholesale.
4. **Git is being used as a mutable database.** One generated main branch is repeatedly
   pulled, regenerated, committed, and pushed. Owner-sharded manifests reduce semantic
   conflicts, but shared root/user/family indexes still make every writer touch derived
   state. Non-fast-forward retry and repository-wide locking are symptoms of the
   mismatch.
5. **Publication is on the code-change critical path.** Prompt and hood publication may
   delay a commit/PR operation or create recovery obligations. Collaboration metadata
   must not make the primary code commit less reliable.
6. **Privacy defaults are too broad.** A hood publication includes active, waiting,
   failed, dismissed, and terminal runs, potentially before a transcript is finished.
   Prompts, chats, model settings, variables, and copied artifact bytes become visible
   to everyone who can read the sidecar. Repository access is not automatically consent
   to every agent transcript.
7. **Identity is display-oriented.** V2 keys owners by configured `username` and
   `machine_name`, and global names embed both. This is better than v1 but insufficient
   as an authorization identity: labels can be renamed, mistyped, restored onto another
   installation, or collide for multiple OS users. The fleet report correctly adds a
   pinned gateway identity, but collaboration also needs an authenticated human
   principal.
8. **Retention is effectively monotonic.** Temporarily missing runs are intentionally
   retained and there is no ordinary history compaction. This is sensible for audit but
   makes eager replicas increasingly expensive.
9. **Its best features do not require sync.** Content hashes, immutable run manifests,
   prompt provenance, and `@agent:` resolution can all work with an on-demand archive.
   Replicating and localizing the entire corpus is an implementation choice, not a
   prerequisite for durability.

Partial clone and sparse checkout can reduce reader cost: `--filter=blob:none` omits
file contents until needed, and sparse checkout limits populated paths
([Git clone](https://git-scm.com/docs/git-clone.html), [Git sparse
checkout](https://git-scm.com/docs/git-sparse-checkout.html)). They do not fix the
writer's global regeneration, the commit frequency, eager import semantics, privacy, or
the lack of a PR-centered model. They are a useful transition optimization, not the
architecture.

### Requirements and invariants

The collaboration design should satisfy these invariants.

#### Authority

- A host is the sole authority for its live processes, local workspaces, local logs, and
  runner-slot admission.
- The forge is the authority for repository identity, issue/PR identity, branch head,
  reviews, checks, and merge state.
- An archive provider is the authority for an immutable published run bundle.
- Caches may be stale and must display their observation time; they never become a new
  authority merely because a TUI loaded them.

#### Identity

Display names and durable identities must be separate:

| Entity | Durable identity | Display label |
| --- | --- | --- |
| Project | `(provider, immutable repository ID)` | `owner/repo` |
| Human principal | `(issuer/provider, immutable subject/account ID)` | login/name |
| SASE installation/host | gateway public-key fingerprint or generated UUID bound to a key | machine name |
| Patch | SASE UUID plus provider PR ID when mailed | branch/Patch name |
| Run | random UUID/ULID generated at launch | semantic agent name |
| Commit | repository ID plus full object ID | short SHA/subject |

For the same user on two machines, the principal is equal and host IDs differ. For two
OS users on one machine, both principal and per-user host installation differ; their
SASE homes, Unix sockets, token files, and workspace stores remain protected by normal
filesystem permissions. A machine label is metadata, never an ownership proof.

Human identity should normally bind to the forge account already authorized for the
project. Tailscale's model is a useful precedent: it distinguishes identity-provider
user identity from a cryptographic node identity and considers both when authorizing a
connection ([Tailscale identity](https://tailscale.com/docs/concepts/tailscale-identity)).

#### Safety and consistency

- Local work must continue offline. Shared state is eventually published when the forge
  is reachable.
- Every network mutation uses an idempotency key and an expected revision/head SHA.
- A stale client may request an action but cannot silently act on a different run or PR
  revision.
- No network failure may roll back a successfully created code commit.
- Team claims are advisory; merges are serialized by branch policy and the merge queue,
  not by a SASE global lock.
- A raw prompt, transcript, response, environment value, or artifact is private unless
  policy or an explicit action publishes it.
- Cross-user process operations are denied by default even when both users can read the
  repository.

### Options considered

| Architecture | Same-user fleet | Multi-user PR coordination | Offline/local work | Privacy | Scaling | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Keep current full agents sync | Historical copies only | Weak | Good | Broad publication | Poor with history/projects | Reject as collaboration foundation |
| Tailnet host mesh only | Excellent | Requires shared tailnet and dangerous cross-user trust | Good | Good within one user | Good for a few hosts | Keep for personal fleet only |
| Forge/PR only | Coarse view of work | Excellent | Good until publication | Strong | Scales with open work | Insufficient for live personal control |
| Central SASE service owns everything | Excellent | Excellent | Degraded without service | Depends on operator | Operationally scalable | Too large a trust/failure-domain change now |
| **Layered host + forge + lazy archive** | **Excellent** | **Excellent** | **Good** | **Explicit per plane** | **Active work + on-demand history** | **Recommended** |

The central-service option may eventually improve webhook fan-out and organization-wide
analytics, but it should be a cache/relay over forge truth, not a prerequisite for local
SASE or a new owner of source and agent data.

### Recommended architecture in detail

```text
                                  SHARED PROJECT PLANE
                         ┌────────────────────────────────┐
                         │ Git forge                      │
                         │ issues · branches · PRs        │
                         │ reviews · checks · merge queue │
                         └───────────────▲────────────────┘
                                         │ provider adapter
                                         │ normalized events/snapshots
        PERSONAL EXECUTION PLANE         │
┌────────────────────────────────────┐   │   ┌──────────────────────────────┐
│ ACE on user's controller           │───┼──▶│ Collaboration/Workstreams UI │
│ local host provider                │   │   │ Patch/PR-centered cache      │
│ remote host providers × N          │   │   └──────────────────────────────┘
└──────────────┬─────────────────────┘   │
               │ HTTPS/JSON + SSE        │
               │ over user's tailnet     │
       ┌───────▼────────┐  ┌────────────▼───────┐
       │ host daemon A  │  │ host daemon B      │
       │ local agents   │  │ local agents       │
       │ local workspaces│ │ local workspaces   │
       └───────┬────────┘  └────────────┬───────┘
               │ terminal, policy-approved run manifests
               └──────────────┬─────────┘
                              ▼
                    OPTIONAL ARCHIVE PLANE
             immutable manifests · content-addressed blobs
             fetched by run/Patch reference, never auto-imported
```

#### 1. Personal execution and fleet plane

Adopt the tailnet research's central recommendation:

- extend the existing Rust `sase_gateway` into a supervised per-user host daemon;
- keep resident agent reads in Rust;
- expose versioned HTTPS/JSON snapshots and an SSE invalidation stream;
- bind loopback and publish with `tailscale serve`, never Funnel;
- compose one independent provider per host behind ACE's existing data-provider seam;
- ship read-only fleet visibility before remote mutations;
- require idempotency, revision fencing, server-side name/run resolution, a durable
  command journal, and fault-injection tests before enabling kill/retry/launch.

One adjustment is necessary for multiple users on the same machine: run one daemon per
OS user with a per-user Unix socket, state root, credentials, and installation key.
Local SASE never crosses that Unix-user boundary. Tailnet exposure is separately opt-in
per user and must use a distinct Serve route/port plus application-layer credentials;
the Tailscale identity of one physical node is not proof of which OS user's SASE home a
request may access. A first release may support remote fleet access for only the OS user
who explicitly exposes a route while still fully supporting local multi-user work and
forge collaboration for everyone else.

This plane may expose full logs and controls to the owner. It should not be used as the
project's multi-user bus. Requiring every contributor to join one tailnet would couple
project membership to network membership, fail for outside contributors, and grant a
larger remote-execution surface than PR collaboration requires. Tailscale grants remain
valuable for explicit team-operated hosts, but new grants are deny-by-default and should
be least privilege ([Tailscale grants](https://tailscale.com/docs/reference/syntax/grants)).

#### 2. Forge-backed collaboration plane

The shared read model is **workstreams**, not remote agent rows. A workstream combines:

- immutable repository identity;
- work item/issue and advisory assignees;
- Patch ID, branch, base SHA, head SHA, and PR ID;
- human owner and optional contributing run IDs;
- draft/open/closed/merged state;
- review decision and requested reviewers/CODEOWNERS;
- checks and mergeability;
- merge-queue position when available;
- timestamps and a provider revision/cursor;
- dependencies and explicit handoff state.

ACE should render this in a Patches/Workstreams surface across enabled projects. For the
current user's Patches, it overlays live run state from the personal fleet. Teammate
work remains useful even when no SASE agent data is shared: the draft PR, commits,
reviews, and checks are enough to coordinate.

`sase-github` already supplies provider classification, issue CRUD, normalized issue and
PR records, PR creation, and Patch submission. It does not yet supply comments, review
events, checks, merge queues, or event cursors; its workspace provider currently reports
that reviewer comments are unsupported. Extend the provider boundary rather than
putting GitHub concepts into ACE:

```text
CollaborationProvider
  repository_identity()
  list_workstreams(since/cursor)
  get_workstream(provider_id)
  claim_or_warn(work_item, expected_revision)
  publish_patch_intent(patch, expected_revision)
  list_reviews_and_checks(patch)
  request_iteration(patch, message)
  submit_or_enqueue(patch, expected_head)
```

Provider-neutral identity, state transitions, idempotency, overlap policy, and cache
semantics belong in `sase-core`. GitHub API/`gh` adaptation remains in `sase-github`.

For the first release, use authenticated, conditional API queries through the user's
existing forge credentials. A future GitHub App can provide near-real-time webhooks and
richer checks without changing the core model. GitHub recommends webhooks over broad
polling for scale and latency ([About
webhooks](https://docs.github.com/en/webhooks/about-webhooks)), and GitHub Apps begin
with no permissions and should request the minimum needed
([choosing GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app)).
The webhook receiver may be a small relay, but GitHub remains the source of truth and
clients periodically reconcile in case deliveries are missed.

Do not require Checks API support for the MVP. Check runs are useful for a coarse
`sase/agent` status attached to a commit and can provide requested-action buttons, but
write access is GitHub-App-only and check data has finite retention
([GitHub Checks API](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks)).
PR state and terminal run manifests must remain understandable without a check run.

#### 3. Collaboration workflow

##### Launch

1. Resolve the project by immutable provider repository ID.
2. If launched from an issue, query open claims and PRs linked to that issue. Warn on an
   existing active workstream and offer: join/continue it, create an explicitly parallel
   Patch, or cancel.
3. Record an advisory issue claim using provider-native assignee/label/comment
   capabilities where available. GitHub permits multiple assignees, so this is awareness,
   not a lock ([issue assignee API](https://docs.github.com/en/rest/issues/assignees)).
4. Create a locally unique Patch ID, workspace, and branch. Use a branch namespace that
   includes the forge principal and a short Patch ID; semantic agent names are not safe
   remote branch keys.
5. Launch the run with stable principal, host, Patch, and run identities captured.

##### Publish intent

- Before the first push, the Patch is local and may continue offline.
- At the first durable stitch/push, open or update a **draft PR** promptly. The draft PR
  is the canonical visible declaration that work exists. Do not manufacture empty
  commits merely to advertise a future idea; an issue claim covers the pre-commit phase.
- Store machine-readable SASE linkage in a provider-owned, idempotently updated marker or
  external record, while keeping the human PR body readable. Never overwrite unrelated
  human edits.

This mirrors current coding-agent practice: GitHub's own and third-party coding agents
are assigned issues, work asynchronously, create PRs, request human review, and accept
follow-up through PR comments ([GitHub third-party coding
agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-coding-agents),
[Copilot agent workflow](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/overview)).

##### Iterate and hand off

- Reviews and PR comments become durable collaboration events. SASE may offer a local
  action to launch a successor run from a selected change request.
- A handoff changes the Patch's human owner explicitly; it does not transfer process
  ownership. The recipient checks out the PR branch into their own workspace and launches
  a new run ID.
- If two users intentionally share one PR branch, pushes use expected-head checks and
  normal Git reconciliation. Prefer one active writer at a time and explicit handoff;
  multiple agents may still contribute sequentially to the same Patch.
- Potential overlap is computed from shared issue links and PR diffs. It is a warning,
  never an attempt to lock paths globally.

##### Land

- Ready state means the Patch has a current remote head, required reviews, required
  checks, and no unresolved blocking relationships.
- Submission delegates to the forge's protected merge or merge queue. SASE does not
  reproduce merge-queue scheduling locally.
- Terminal run manifests may publish asynchronously after the code commit/PR update. A
  failed archive upload leaves an explicit retry obligation but never invalidates the
  source commit or hides the PR.

#### 4. Lazy run archive

Introduce a `RunArchiveProvider` boundary with local, Git-sidecar, and future object-store
implementations. The archive is useful for reproducibility and handoff, but collaboration
must work when it is disabled.

A default shared manifest should contain only:

```text
schema version
run ID, Patch ID, repository ID, PR ID
authenticated principal ID and host installation ID
started/finished timestamps and terminal outcome
base/head SHAs and contributed commit IDs
tool/provider/model identifiers if project policy allows them
prompt digest and configuration digest, not prompt text
capabilities: viewable / reproducible / restartable
content references: kind, digest, size, media type, locator
supersedes/superseded-by links when corrected
signature or authenticated publisher metadata
```

Prompt bodies, chats, responses, images, external files, variables, and environment
details are separate encrypted or access-controlled blobs and default to **not
published**. Project policy may require a sanitized prompt or transcript for regulated
work; an explicit one-off publish action may attach more. Secret scanning is a backstop,
not a publication policy.

For a no-new-service transition, redesign the agents sidecar as a compact v3 archive
backend:

- one append-only owner/installation stream or branch, avoiding a shared generated main
  branch as the write authority;
- one terminal manifest per Patch-associated run, or a compact append-only catalog plus
  content-addressed compressed blobs;
- no active/waiting hood snapshots;
- no per-commit prompt-archive commit;
- no regenerated global README/user/family trees on the writer path;
- no foreign-run import, permanent-name claim, or dismissed-bundle creation;
- shallow partial fetch of catalogs and requested blobs only;
- local or asynchronous static rendering when a human-readable page is requested.

This backend preserves user-owned Git durability and gives the existing corpus a natural
successor. The provider boundary permits S3/R2, an OCI registry, or a forge-native
artifact service later without coupling SASE's domain model to one store.

`@agent:` should resolve a stable run/Patch identity through this provider and cache the
selected manifest/content locally. “Revive” downloads one selected restartable capsule
and launches a **new** local run with `derived_from_run_id`; it never rewrites the old
identity into the viewer's agent namespace.

#### 5. Failure and offline semantics

| Condition | Required behavior |
| --- | --- |
| A personal host is offline | Show cached rows as stale with observation time; refuse live mutation; retain forge workstream |
| Forge is offline | Local run and commits continue; Patch shows unpublished/ahead state; retry idempotently later |
| Archive is offline | PR collaboration continues; archive link shows unavailable/pending |
| Webhook is lost or reordered | Reconcile from provider snapshot/cursor; never infer deletion from silence |
| Two users claim one issue | Warn and show both; allow explicit parallel Patch; do not deadlock |
| Two users push one PR branch | Reject stale expected head and require reconcile/handoff |
| Base advances | Recompute mergeability or rely on forge merge queue; do not mutate unrelated workspaces |
| User or machine display name changes | Stable principal/host/run IDs preserve identity; labels update independently |
| User loses repository access | Forge and archive reads stop; cached sensitive bodies obey local retention policy |
| Host token is revoked | Fleet connection becomes unauthorized; forge work remains visible according to repo ACLs |

#### 6. Security model

There are three different permissions and they must not collapse into “can read the
repo”:

1. **Project permissions:** read/write/review/merge are inherited from the forge and its
   branch rules. CODEOWNERS can require review from responsible teams
   ([GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)).
2. **Fleet permissions:** view/operate/admin apply to the owner's host daemon, authorized
   through Tailscale identity/grants plus scoped gateway credentials. Default scope is
   the user's own devices.
3. **Archive permissions:** metadata and each content class have explicit publication
   policy and retention. A repository-readable summary does not imply transcript or
   external-file access.

Every shared action records the authenticated principal, provider installation, target
Patch/run, expected revision, result, and idempotency key. The system should expose
coarse teammate activity only when deliberately published; raw reasoning and transcripts
are neither required nor desirable for basic collaboration.

### What to keep, change, and remove

#### Keep

- Patch ↔ PR as the durable code-change mapping, and Stitch ↔ commit attribution.
- SASE's isolated workspace-per-agent model.
- Content digests, bounded/versioned archive schemas, capability declarations, and
  portable metadata validation.
- Durable local outboxes for eventually publishing non-critical metadata.
- Read compatibility for existing v1/v2 agents sidecars and existing `@agent:` links.
- The fleet report's host daemon, HTTP+SSE, per-host authority, cache/staleness model,
  and read-only-first rollout.

#### Change

- Make stable principal/host/run IDs canonical; render username, machine, and agent names
  as labels.
- Make the forge-backed workstream the team-visible collaboration object.
- Change agents-sidecar publication from repeated hood snapshots to terminal,
  Patch-associated, policy-minimal manifests and optional blobs.
- Change archive access from clone/import/reconcile to resolve/fetch/cache on demand.
- Change revival from “import a foreign agent” to “launch a new run derived from a
  selected restart capsule.”
- Move publication off the code-commit critical path.
- Make broad transcript/prompt sharing opt-in or project-policy-driven.

#### Remove

- Default cloning/materialization of every enabled project's full agents archive.
- Periodic all-project agent-repository inspection as the source of collaboration
  awareness.
- Publication of active, waiting, failed, and dismissed hoods merely because a related
  commit occurred.
- Regeneration of shared global indexes on each writer's push.
- Automatic import of other owners' runs into local artifacts, dismissed bundles,
  family groups, visibility state, and permanent name registry.
- Any plan to use a personal tailnet as the required multi-user project bus.

### Migration strategy

The migration should preserve existing archives while proving the replacement in small
steps.

#### Phase 1 — Establish the collaboration read model

- Add stable repository, Patch, principal, host, and run IDs without changing current
  display names.
- Extend the provider-neutral core and `sase-github` read surface for linked issues,
  PR review/check/merge state, and provider revisions.
- Add the Patches/Workstreams view and overlap warnings. Read only at first.
- Measure query count, time to first useful row, active-PR cardinality, and stale-cache
  behavior.

#### Phase 2 — Publish Patch intent and handoff

- Add idempotent advisory issue claims and early draft-PR linkage.
- Add PR-comment-driven iteration and explicit Patch handoff.
- Use expected head SHA on remote mutations.
- Let the forge's review rules and merge queue own landing safety.

#### Phase 3 — Ship the personal fleet separately

- Follow the fleet report through read-only federated visibility before mutations.
- Use stable per-user host-installation identity rather than machine label alone.
- Overlay only the current user's live agents onto shared workstreams.
- Keep all cross-user controls disabled unless a separately audited operator policy is
  configured.

#### Phase 4 — Introduce archive v3 and stop eager imports

- Add the `RunArchiveProvider` and compact terminal manifest.
- Publish only Patch-associated terminal runs by default; allow explicit archives for
  research/non-code work.
- Resolve and cache archives on demand without local agent materialization.
- Put the old sync behavior behind a sunset compatibility path while both readers work;
  the disabled branch is removed only after the project's flag criteria are met.
- Make current agents clones partial/sparse during the transition to reduce immediate
  disk and blob-transfer cost.

#### Phase 5 — Freeze and retire legacy transport

- Stop writing v2 hood snapshots and per-commit prompt pages.
- Retain existing v1/v2 repositories as read-only history for a documented period.
- Migrate references lazily or in a separately measured offline job, never as a TUI
  startup requirement.
- Delete import transactions, receipts, incoming hood caches, name-localization bridges,
  shared-index regeneration, and full-sync UI only after telemetry shows no required
  consumers remain.

#### Acceptance criteria

The replacement is successful when:

1. A fresh user can collaborate on an existing SASE project without cloning its agents
   sidecar.
2. ACE's collaboration startup work is proportional to open workstreams, not historical
   agent count or number of sidecar files.
3. Two users on two machines can launch separate Patches from the same base, see each
   other's draft PRs, receive overlap warnings, review, and land through protected merge
   without sharing SASE homes or tailnets.
4. Two OS users on one machine have isolated daemons, credentials, workspaces, and run
   identities while sharing the same forge-backed project view.
5. A code commit and PR update succeed even when fleet and archive services are offline.
6. No prompt/chat/artifact body leaves its host under default policy.
7. A selected historical run can be inspected or revived with one on-demand fetch, and
   the revived run has a new identity linked to its source.
8. An offline host appears stale, not alive and not absent; an offline collaborator's
   PR remains fully visible through the forge.
9. A busy repository can use required reviews/checks and a merge queue without SASE
   implementing a second integration scheduler.
10. The old agents-sync path can be removed without breaking Patch/PR collaboration or
    personal fleet visibility.

### Risks and open decisions

- **Archive backend:** a compact Git v3 backend is the lowest-risk transition, but an
  object store will eventually handle large encrypted blobs and retention better. The
  provider boundary must precede either commitment.
- **Forge coverage:** GitHub is the practical first implementation, but core types must
  avoid GitHub-only state. A plain-Git provider can offer branches and manual Patch
  exchange with reduced review/issue capabilities.
- **Work-intent noise:** issue comments and labels can become noisy. Prefer one
  idempotently updated marker and a draft PR after the first push, not progress spam.
- **Teammate live status:** the default should be no live agent sharing. If teams later
  want coarse `working/waiting/finished` presence, publish expiring summaries through a
  forge/app relay; do not expose the personal host API.
- **PR branch co-ownership:** explicit sequential handoff is much easier to reason about
  than concurrent pushes. SASE should support the latter safely with expected-head
  checks, but teach the former.
- **Service pressure:** webhooks and organization-wide dashboards may justify a hosted
  relay later. It must remain a reconstructible cache over forge/archive truth so local
  development never depends on it.

### Recommended solution

Build SASE collaboration around a provider-neutral **Workstream = Work item + Patch +
PR** model, with the Git forge as the shared source of truth for intent, review, checks,
and merge. Use the proposed Rust HTTP+SSE tailnet host daemon only for a user's own live
fleet, with per-user installation identity and no implicit cross-user control. Replace
the current full `agents_sync` replication with an optional, asynchronous, lazy run
archive that publishes minimal immutable provenance for terminal Patch-associated runs
and fetches detailed content only on demand.

Concretely, keep existing sidecars readable and reuse their schema-validation and
content-addressing lessons, but stop automatically cloning them, stop publishing whole
hoods and prompts on every commit, stop rebuilding shared indexes, and stop importing
foreign runs into local agent state. Start with a compact Git-backed archive v3 so the
migration needs no new service, behind an archive-provider boundary that can later use
object storage. Extend `sase-github` for the missing collaboration events, add a
Patch/PR-centered Workstreams view, publish draft PR intent early, and delegate final
convergence to reviews, required checks, and the forge's merge queue.

This preserves SASE's local-first execution and durable provenance while making cost,
privacy, and coordination scale with the work people are actually sharing—not with every
agent every user has ever run.
