# SASE collaboration architecture

**Date:** 2026-09-04  
**Status:** Research recommendation; not an approved implementation direction  
**Question:** How should SASE support multiple users, including multiple users on one
machine, developing the same project concurrently through a pull-request workflow? What
should happen to the current cross-machine agent-sync system, and how should the proposed
single-TUI tailnet fleet fit into the result?

## Executive conclusion

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

## Method and evidence

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

## What collaboration should mean in SASE

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

## The current agent-sync solution

### What it does well

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

### Its actual shape

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

### Observed scale

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

### Why it is not a collaboration architecture

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

### Principal problems

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

## Requirements and invariants

The collaboration design should satisfy these invariants.

### Authority

- A host is the sole authority for its live processes, local workspaces, local logs, and
  runner-slot admission.
- The forge is the authority for repository identity, issue/PR identity, branch head,
  reviews, checks, and merge state.
- An archive provider is the authority for an immutable published run bundle.
- Caches may be stale and must display their observation time; they never become a new
  authority merely because a TUI loaded them.

### Identity

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

### Safety and consistency

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

## Options considered

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

## Recommended architecture in detail

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

### 1. Personal execution and fleet plane

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

### 2. Forge-backed collaboration plane

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

### 3. Collaboration workflow

#### Launch

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

#### Publish intent

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

#### Iterate and hand off

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

#### Land

- Ready state means the Patch has a current remote head, required reviews, required
  checks, and no unresolved blocking relationships.
- Submission delegates to the forge's protected merge or merge queue. SASE does not
  reproduce merge-queue scheduling locally.
- Terminal run manifests may publish asynchronously after the code commit/PR update. A
  failed archive upload leaves an explicit retry obligation but never invalidates the
  source commit or hides the PR.

### 4. Lazy run archive

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

### 5. Failure and offline semantics

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

### 6. Security model

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

## What to keep, change, and remove

### Keep

- Patch ↔ PR as the durable code-change mapping, and Stitch ↔ commit attribution.
- SASE's isolated workspace-per-agent model.
- Content digests, bounded/versioned archive schemas, capability declarations, and
  portable metadata validation.
- Durable local outboxes for eventually publishing non-critical metadata.
- Read compatibility for existing v1/v2 agents sidecars and existing `@agent:` links.
- The fleet report's host daemon, HTTP+SSE, per-host authority, cache/staleness model,
  and read-only-first rollout.

### Change

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

### Remove

- Default cloning/materialization of every enabled project's full agents archive.
- Periodic all-project agent-repository inspection as the source of collaboration
  awareness.
- Publication of active, waiting, failed, and dismissed hoods merely because a related
  commit occurred.
- Regeneration of shared global indexes on each writer's push.
- Automatic import of other owners' runs into local artifacts, dismissed bundles,
  family groups, visibility state, and permanent name registry.
- Any plan to use a personal tailnet as the required multi-user project bus.

## Migration strategy

The migration should preserve existing archives while proving the replacement in small
steps.

### Phase 1 — Establish the collaboration read model

- Add stable repository, Patch, principal, host, and run IDs without changing current
  display names.
- Extend the provider-neutral core and `sase-github` read surface for linked issues,
  PR review/check/merge state, and provider revisions.
- Add the Patches/Workstreams view and overlap warnings. Read only at first.
- Measure query count, time to first useful row, active-PR cardinality, and stale-cache
  behavior.

### Phase 2 — Publish Patch intent and handoff

- Add idempotent advisory issue claims and early draft-PR linkage.
- Add PR-comment-driven iteration and explicit Patch handoff.
- Use expected head SHA on remote mutations.
- Let the forge's review rules and merge queue own landing safety.

### Phase 3 — Ship the personal fleet separately

- Follow the fleet report through read-only federated visibility before mutations.
- Use stable per-user host-installation identity rather than machine label alone.
- Overlay only the current user's live agents onto shared workstreams.
- Keep all cross-user controls disabled unless a separately audited operator policy is
  configured.

### Phase 4 — Introduce archive v3 and stop eager imports

- Add the `RunArchiveProvider` and compact terminal manifest.
- Publish only Patch-associated terminal runs by default; allow explicit archives for
  research/non-code work.
- Resolve and cache archives on demand without local agent materialization.
- Put the old sync behavior behind a sunset compatibility path while both readers work;
  the disabled branch is removed only after the project's flag criteria are met.
- Make current agents clones partial/sparse during the transition to reduce immediate
  disk and blob-transfer cost.

### Phase 5 — Freeze and retire legacy transport

- Stop writing v2 hood snapshots and per-commit prompt pages.
- Retain existing v1/v2 repositories as read-only history for a documented period.
- Migrate references lazily or in a separately measured offline job, never as a TUI
  startup requirement.
- Delete import transactions, receipts, incoming hood caches, name-localization bridges,
  shared-index regeneration, and full-sync UI only after telemetry shows no required
  consumers remain.

### Acceptance criteria

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

## Risks and open decisions

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

## Recommended solution

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
