# Provider-neutral remote dispatch and fleet UX for SASE

**Researcher:** A (`research.1i` swarm)  
**Date:** 2026-09-06  
**Scope:** architecture and UX research, not an implementation plan  
**Code reviewed:** `sase` at `58f16fe68`; `sase-core` at `0504155`

## Executive summary

Remote dispatch is a good fit for SASE, but the proposed feature contains two ideas that
should be separated:

1. a standard SASE control plane for observing and operating agents on another machine;
2. pluggable ways to discover, enroll, authenticate to, and reach those machines.

The first must remain SASE-owned and versioned. The second is the correct plugin seam.
Letting plugins invent agent-list and mutation semantics would create incompatible
identity, authorization, caching, and error behavior in the TUI. Instead, every remote
machine should expose a fixed **SASE Remote Agent Protocol** implemented by the Rust
daemon/gateway. A new `sase_dispatch` plugin group should supply machine-access
providers. The built-in `tailnet` provider can discover candidates during `sase init`
and provision a Tailnet-reachable endpoint; a built-in `static` provider can enroll an
explicit HTTPS endpoint. Tailscale is then an excellent default without becoming a hard
runtime or installation dependency.

The proposed Local/Remote subtabs also need reframing. If “Local” contains subscribed
remote agents, it is not local. The useful distinction is between the user's **working
set** and the **fleet catalog**:

- **Focus**: every local agent plus remote agents this machine follows. This is the
  default, management-oriented view and preserves today's Agents experience.
- **Fleet**: discoverable agents from all configured remote machines, with followed
  agents visibly marked. This is a browse-and-follow surface, not a mirror of each
  remote TUI's private filters and dismissal state.

“Subscribe” is precise implementation language; “Follow” is the better interface verb.
A followed row should have a filled star and accent rail, not color alone. Every remote
row should display a compact machine pill such as `@apollo`, freshness, and capability
state. The Fleet view should make the whole catalog reachable but should initially load
only active/attention/recent rows and page older history. Eagerly materializing the full
history of every host is neither necessary nor compatible with the performance goal.

`%dispatch:<machine>` should be parsed into the typed launch plan before SASE reserves
any local name, timestamp, workspace, or artifact path. The remote authority performs
target-specific validation and allocation. Dispatch should create a durable local
follow intent and idempotency key before sending the launch request, then bind the
returned authoritative run ID to that follow. This closes the most dangerous reliability
gap: a launch that succeeds remotely while its response is lost.

The work should be staged. First remove local-path/PID assumptions from the provider and
action boundaries. Next harden and extend the existing Rust gateway: scoped credentials,
safe enrollment, resident reads, stable global locators, revisioned summaries/snapshots,
real invalidation events, capability negotiation, and a durable mutation journal. Only
then add access-provider plugins, `%dispatch`, and the Focus/Fleet UI.

## Research basis

I reviewed the three requested research snapshots in creation order:

1. `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`
2. `research:202609/sase_collaboration_architecture.md`
3. `research:202609/tailnet_fleet_federation/tailnet_fleet_federation.md`

Their direction is sound: per-host authority, cached snapshots, typed remote actions,
Tailnet-friendly transport, and an explicit distinction between same-user fleet control
and cross-user collaboration. The most recent federation report is a particularly good
protocol foundation. This report narrows the plugin boundary, redesigns the requested
TUI model, and follows the current launch and provider code far enough to expose several
implementation-order constraints.

I did not consult the other report in this swarm, directly or indirectly.

External references used here are primary documentation:

- Tailscale's CLI documents `tailscale status --json`, which provides structured peer
  and user information suitable for explicit-time discovery:
  [Tailscale CLI reference](https://tailscale.com/docs/reference/tailscale-cli?tab=macos).
- Tailscale Serve can publish a local service privately within a tailnet:
  [Serve command](https://tailscale.com/docs/reference/tailscale-cli/serve) and
  [Serve examples](https://tailscale.com/docs/reference/examples/serve).
- Tailnet identity and ACL/grant policy are useful transport signals, but they are not a
  substitute for SASE authorization:
  [Tailscale identity](https://tailscale.com/docs/concepts/tailscale-identity),
  [grants syntax](https://tailscale.com/docs/reference/syntax/grants), and
  [application capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities).
- Pluggy's hook validation and `firstresult` behavior inform the proposed hook shapes:
  [Pluggy documentation](https://pluggy.readthedocs.io/en/stable/).

## 1. What problem is this feature actually solving?

The desired experience is not generic remote execution. It is a personal SASE fleet:

- launch an agent on a machine with appropriate capacity, data, credentials, or
  environment;
- see that work alongside work on the current machine;
- browse work running elsewhere without importing it;
- perform the same safe lifecycle actions wherever possible;
- remain useful when one or more machines are offline;
- avoid making the local TUI pay continuously for remote functionality the user is not
  using.

That definition matters. “Remote execution” suggests SSH plus a command string. “Fleet”
requires durable identity, observation, retries, policy, subscriptions, reconciliation,
and humane degraded behavior. Dispatching is the small visible tip; following and
operating the launched agent reliably is the harder part.

The feature should explicitly remain a **same-owner control plane** in its first form.
The collaboration research correctly argues that another person's agents should cross
the boundary as artifacts, patches, beads, or other reviewable work—not as foreign
processes one can casually kill or fork. A provider may use an organizational transport,
but SASE should deny cross-owner operation unless a later, separately designed
delegation model authorizes it.

## 2. Critique of the initial proposal

### 2.1 What is right

Several instincts in the request are exactly right:

- Tailscale should be a strong default but not a required dependency.
- Discovery can happen during `sase init`; runtime polling of a whole tailnet is needless.
- The local machine should automatically follow work it dispatches.
- Remote browsing should not crowd the primary working view.
- A hidden Fleet surface must not make local navigation or startup slower.
- The user should be able to operate followed remote agents with familiar commands.
- There should be a visible count of currently running agents in each mode.

### 2.2 What should change

#### “Local” is the wrong label

A tab called Local that includes remote agents violates a user's simplest spatial model.
It will create questions such as “why is `@apollo` under Local?” and make documentation
resort to explaining an exception. The distinction is not location; it is attention.
Call the modes **Focus** and **Fleet**.

I considered **Home / Fleet** and **Following / Fleet**. Home is attractive but still
suggests physical locality. Following excludes local agents that are implicitly always
included. Focus describes exactly why a row appears: this machine's active working set.

#### Do not mirror “what each remote TUI shows”

A remote TUI's folds, dismissals, query, selection, and recent-history cutoff are viewer
preferences. Mirroring them makes one viewer's private UI state part of the fleet API and
can cause an agent to disappear on another machine for surprising reasons. Fleet should
display an authoritative, discoverable agent catalog exposed by each host, filtered and
folded locally.

This also avoids reviving the retired agents-sync import model. A remote row is a cached
projection with an origin locator, never a local imported agent or local history record.

#### “All” should mean reachable, not eagerly resident

The Fleet view should let a user reach all discoverable remote agents, but it should not
fetch every historical row at startup or on every refresh. Its first page should contain:

- active and waiting agents;
- failures or gates that need attention;
- a bounded recent tail;
- cursors and server-side filtering for older history.

This interpretation gives the requested complete fleet view without turning the TUI
into a distributed history database.

#### A provider must not own agent semantics

“One or more plugin hooks for remote discovery and dispatch” is directionally good but
too broad. If each plugin implements listing, launching, killing, retrying, eventing, and
content access, every provider becomes a new backend. Security invariants and UI
capabilities will drift.

Plugins should own **machine access**. SASE core should own the **remote agent protocol**.
That gives a Tailnet provider, static-HTTPS provider, future SSH-tunnel provider, and
future Cloudflare provider the same safe semantics.

#### A single global dispatch provider is too restrictive

One machine may be reached over a tailnet, another through an explicit HTTPS URL, and a
temporary host through an SSH tunnel. Configuration needs a default provider for
discovery/enrollment convenience, but each enrolled machine must retain its own provider.
At runtime `%dispatch:apollo` resolves an explicit machine record; it should not ask a
global provider to rediscover `apollo`.

## 3. Current architecture: useful seams and dangerous assumptions

### 3.1 The Rust gateway is the right protocol nucleus

`sase-core/crates/sase_gateway` already exposes health, pairing/session, SSE events,
agent list, launch, kill, retry, and several related mobile operations. This is a much
better starting point than shelling out over SSH from the TUI.

It is not ready to expose as a fleet control plane unchanged:

- `CommandAgentHostBridge` forks `sase mobile agent-bridge ...` for requests, so hot
  reads still pay Python startup and scanning costs.
- the event stream currently replays in-memory records and emits heartbeats, but does
  not yet provide a complete authoritative mutation/invalidation stream;
- request IDs are preserved as correlation fields, but there is no durable
  idempotency/deduplication journal;
- pairing start returns a code to the unauthenticated caller and pairing finish mints a
  bearer token, which is unsuitable for an endpoint exposed to a whole tailnet;
- kill/retry are name-addressed, and names alone are not durable identities across
  hosts, projects, and reuse;
- the daemon's mobile gateway and current wire schema were designed for mobile access,
  not yet for a multi-host cache and reconciliation loop.

The correct move is to evolve this gateway into a shared remote protocol in Rust, not
build a parallel Python federation server.

### 3.2 ACE already has a provider-shaped read seam

ACE has `AceSnapshot`, `AgentsProviderSnapshot`, stable row handles, page/delta fields,
counts, and lazy-detail concepts. This is promising. Yet the current direct provider is
effectively the only path, and the model beneath it remains deeply local.

For example, an agent row handle is currently derived as
`agent:<project-directory-name>:<raw-suffix>`, while `local_identity` joins the existing
local tuple. Neither can distinguish identical project/run names on two hosts. The
`AgentState` model carries local paths (`project_file`, `response_path`, `diff_path`,
workspace paths), a PID, and direct file-backed enrichment fields. Those are not valid
remote capabilities.

The first refactor should introduce an origin-aware locator and content/action adapters,
then make the direct provider use them too. Remote support should not be implemented by
stuffing URLs into local path fields or remote PIDs into local process actions.

### 3.3 Launch routing currently occurs too late

`%dispatch` is absent from the known directive set and `PromptDirectives`. In the ACE
launch path, `_submit_resolved_launch` reserves a local timestamp and workflow identity
before `submit_agent_launch` starts a durable local `sase run`. Deeper launch planning
also creates target-specific names, directories, and workspaces.

Therefore “parse `%dispatch` and replace the final command with SSH” is incorrect. By
then the client has already made local-authority decisions. Dispatch must be represented
in the Rust typed launch plan and route each launch unit before target allocation.

### 3.4 The existing plugin architecture is a good mechanical model

SASE already discovers providers through Python entry-point groups such as `sase_llm`,
`sase_vcs`, `sase_workspace`, and `sase_artifact_refs`. The workspace hook specs also
document argument names as a cross-repository compatibility boundary. A new entry-point
group fits the project.

Two Pluggy details matter:

- discovery and metadata hooks should aggregate results;
- endpoint ownership and target resolution should be `firstresult` only after SASE has
  selected the configured provider explicitly.

Relying on registration order for “the first plugin that recognizes this machine” would
be nondeterministic and confusing. Machine alias uniqueness and provider ownership must
be validated when configuration is created.

## 4. The proposed conceptual model

### 4.1 Three layers

```text
ACE / CLI
  Focus, Fleet, %dispatch, typed actions
                  │
                  ▼
SASE Remote Agent Protocol (Rust-owned)
  identity, snapshots, summaries, cursors, events, content, mutations,
  capabilities, auth scopes, revisions, idempotency
                  │
                  ▼
Machine-access provider plugin
  discover, propose enrollment, provision/resolve endpoint, transport hints
     ├── tailnet (built in, enabled by default when available)
     ├── static  (built in, explicit HTTPS endpoint)
     └── future ssh-tunnel / Cloudflare / other transports
```

This division is the central recommendation. A plugin can tell SASE how to find and
reach a host. It cannot reinterpret what “kill this exact live run” means.

### 4.2 Durable identities

Every enrolled host needs a stable installation identity that is independent of its
display name, MagicDNS name, IP address, and provider. Enrollment pins that identity.
A human-friendly alias such as `apollo` is local configuration.

An agent locator should contain at least:

```text
provider_id
host_installation_id
project_id
run_id
```

It may also carry attempt or logical-agent identity where needed. `run_id` must be minted
by the authoritative host and remain unique across name reuse. The display label can
remain the familiar SASE agent name.

This is compatible with machine-qualified display names while correcting the collision
problem in current ACE row handles. Remote APIs should never make a local filesystem
path or PID part of a portable identity.

### 4.3 Authority and state ownership

The remote host owns:

- whether a run exists and is live;
- agent status, lineage, content, and capabilities;
- target project availability and launch admission;
- mutation ordering and idempotency;
- the mapping from opaque content handles to local files;
- authorization policy.

The viewing machine owns:

- machine aliases and enabled providers;
- follow/unfollow state;
- its own filters, folds, selection, and dismissal preferences;
- cached projections and freshness metadata;
- pending dispatch intents.

That separation lets the viewer work offline without pretending it can mutate an
offline authority.

## 5. Plugin design

### 5.1 Entry-point group

Add one group, tentatively `sase_dispatch`. “Dispatch” matches the user-facing directive,
although the internal protocol should call these machine-access providers.

Do not create separate discovery and execution plugin families yet. They have the same
machine ownership and configuration lifecycle, while the SASE protocol already isolates
execution semantics.

### 5.2 Hook surface

The hook API should use versioned typed request/result objects and keyword invocation.
A compact first version is:

```python
@hookspec
def dispatch_provider_spec() -> DispatchProviderSpec:
    """Static ID, version, capabilities, config schema, and availability probe."""

@hookspec
def dispatch_discover(request: DispatchDiscoveryRequest) -> list[DiscoveredMachine]:
    """Slow, explicit discovery used by init/refresh—not a render-path hook."""

@hookspec(firstresult=True)
def dispatch_plan_enrollment(request: EnrollmentPlanRequest) -> EnrollmentPlan | None:
    """Read-only preview for the explicitly selected provider."""

@hookspec(firstresult=True)
def dispatch_apply_enrollment(request: EnrollmentApplyRequest) -> EnrollmentResult | None:
    """Provision/verify access after explicit user authorization."""

@hookspec(firstresult=True)
def dispatch_resolve_endpoint(request: EndpointResolveRequest) -> EndpointDescriptor | None:
    """Fast resolution of an enrolled machine to the standard SASE protocol."""
```

If a transport requires a tunnel, `EndpointDescriptor` may say it needs preparation;
preparation runs in a durable/off-thread operation and yields a short-lived local URL.
The hot resolver itself should be pure and fast.

Metadata and discovery aggregate across enabled providers. Plan/apply/resolve are invoked
only on the provider named by the machine record, so `firstresult` does not become an
implicit priority scheme.

### 5.3 Loading must be lazy

SASE can inspect entry-point metadata without importing provider modules. It should:

1. load no dispatch provider on a machine with no dispatch configuration;
2. load only the provider needed by `sase init` discovery or a configured machine;
3. never call discovery during ordinary startup, completion, rendering, or refresh;
4. cache static provider metadata and validated machine records;
5. isolate provider failures so one plugin cannot remove local agents or other hosts.

The `tailnet` provider being “enabled by default” should mean it participates when its
binary/session is available during explicit discovery. On a computer without Tailscale,
it returns a typed unavailable result and SASE remains fully local.

### 5.4 Built-in providers

#### `tailnet`

At explicit init time:

- run `tailscale status --json` with a deadline;
- filter plausible candidates, optionally preferring a `tag:sase` convention;
- probe a fixed `/.well-known/sase-dispatch` or protocol health endpoint concurrently
  with bounded fan-out and short deadlines;
- show identity, OS, advertised SASE version, host fingerprint, and capabilities;
- let the user choose machines;
- pin the returned SASE installation identity during enrollment;
- optionally configure/verify Tailscale Serve for a loopback-bound daemon.

Tailnet membership is discovery and transport evidence, not permission to control SASE.
SASE credentials and host policy are still required.

#### `static`

This provider accepts an explicit HTTPS URL, verifies the SASE protocol and pinned host
identity, and enrolls it. It makes the feature useful without Tailscale and provides the
simplest integration test target.

An SSH-tunnel provider can follow later. It should create connectivity to the same
loopback-bound protocol rather than accept arbitrary remote command templates.

## 6. Configuration and onboarding

### 6.1 Suggested shape

```yaml
dispatch:
  enabled: true
  default_provider: tailnet
  providers:
    tailnet:
      enabled: true
    static:
      enabled: true
  machines:
    apollo:
      provider: tailnet
      endpoint: https://apollo.example-ts.net
      host_installation_id: host_01J...
      host_fingerprint: sha256:...
      credential_ref: keyring://sase/dispatch/apollo
      enabled: true
```

The endpoint is provider output, not the identity. Credentials should live in an OS
credential store or permission-restricted secret store; YAML should contain only a
reference. Project IDs and host capabilities should be learned dynamically and cached,
not configured as absolute remote paths.

`default_provider` selects the provider preselected for discovery/enrollment. It does
not override the provider pinned on an enrolled machine. Machine aliases must be unique
across providers because `%dispatch:<machine>` must be unambiguous.

### 6.2 `sase init` flow

Discovery and enrollment are different trust transitions:

1. **Discover:** “These tailnet peers appear to run compatible SASE endpoints.”
2. **Select:** user chooses candidates and aliases.
3. **Inspect:** show host identity, ownership, protocol compatibility, projects,
   capabilities, and requested access scopes.
4. **Enroll:** confirm identity and provision a credential.
5. **Verify:** make an authenticated read-only call and write configuration atomically.

`sase init --check` may report discovered/configured drift but must not enroll, mint
credentials, modify Serve, or trust a new fingerprint. An unattended `--yes` should not
silently authorize every visible tailnet machine. Safe automation can consume an
explicit allowlist or pre-pinned identities.

Because discovery is intentionally not continuous, expose a focused refresh command,
for example `sase dispatch discover` or the dispatch portion of `sase init`. Runtime
uses only enrolled records. A tailnet peer appearing later does not suddenly join the
fleet.

### 6.3 Project matching

A machine cannot safely receive a local path. Dispatch requests should identify a SASE
project by immutable repository/provider metadata, with a human-readable project alias
as a hint. The target returns one of:

- eligible and resolved;
- project not installed;
- repository identity mismatch;
- project disabled;
- provider/model/plugin capability missing;
- policy or capacity rejection.

Ambiguous project matching must require configuration or a user decision, never choose
the first path with the same basename.

## 7. The SASE Remote Agent Protocol

### 7.1 Read model

The minimum read surface is:

- `hello`: protocol versions, host identity, build, owner identity, capabilities;
- `summary`: revision, observed time, live counts, attention counts, capacity/slots;
- `agents`: bounded/cursor-paged projections with server-side status/project/query
  filters;
- `agent detail`: lazy metadata for a selected run;
- `content`: opaque content handle plus digest/range support;
- `events`: revisioned invalidations and mutation results;
- `projects`: dispatch eligibility and target capability summaries.

The tiny `summary` call is important because tab counts must not require fetching every
agent row. A summary response should be cheap enough to serve from resident Rust state.

Snapshots are authoritative. Events should say “host/project revision changed” and
allow selective revalidation; clients should not reconstruct truth solely from an SSE
event log. Periodic jittered reconciliation (for example every 30–60 seconds while
active) repairs missed events.

### 7.2 Mutation model

Every mutation needs:

- authenticated principal and scope;
- exact origin-aware target locator;
- operation type and typed arguments;
- client-generated idempotency key;
- expected observed revision or liveness precondition where relevant;
- deadline;
- durable server-side receipt/result.

The host re-resolves the locator and rechecks liveness immediately before acting. A
cached “RUNNING” label never authorizes killing a newly reused name. Destructive actions
are never queued while a host is offline.

Launch, retry, fork, and other creation operations require a durable journal. If the
network drops after the host accepts a launch, repeating the same idempotency key must
return the original run locator rather than start a second agent.

### 7.3 Capability negotiation

Both host and individual row should expose capabilities. Examples:

- view summary/detail/output/diff;
- follow (always viewer-local, so no host mutation needed);
- kill/retry/fork/create;
- answer gate/question;
- open remote shell/attach;
- content range reads;
- server-side search;
- live events.

ACE should compute available commands from capabilities and freshness, not from whether
a row happens to have a PID/path-shaped field. A disabled command should explain why:
“Unavailable on this host,” “stale snapshot,” “requires operate scope,” or “host
offline.”

### 7.4 Security model

The effective permission should be the intersection of:

1. transport identity/policy (Tailnet identity, ACL/grant, tunnel identity, TLS);
2. scoped SASE credential (`view`, `operate`, `admin` or a more granular equivalent);
3. target-host policy for project, operation, provider, and owner.

This is defense in depth. Being on a tailnet should not imply permission to kill an
agent. Conversely, a leaked SASE bearer token should not be sufficient from an arbitrary
network location when the provider can bind it to a transport principal.

The current mobile pairing behavior must be hardened before Tailnet exposure. Enrollment
should require local confirmation on the target, a pre-authorized transport identity,
or an explicit one-time out-of-band flow. The unauthenticated network caller must not
receive the secret needed to finish its own pairing.

Audit records should include principal, transport identity, source machine, target
locator, operation, idempotency key, result, and timestamp—but never prompt/output bodies
or bearer tokens by default.

## 8. `%dispatch:<machine>` design

### 8.1 Syntax and behavior

The requested syntax is good:

```text
%dispatch:apollo Investigate the failing integration test.
```

No directive means local dispatch. An optional `%dispatch:local` could be useful in
reusable xprompts, but it is not required for the first release. Do not add
`%dispatch:auto` initially: client-side scheduling from stale fleet summaries creates
surprising placement and complex policy. If added later, it should be an explicit
placement-policy layer whose chosen target still performs authoritative admission.

Machine completion must come only from the cached configuration registry. Typing in the
prompt bar must never probe the network. Completion can show alias, provider, last-known
state, eligible project, and slot summary, with stale data visibly marked.

Unknown aliases should fail locally with a direct repair action:
“Machine `gpu-box` is not enrolled; run `sase dispatch discover`.” Provider unavailable,
host offline, incompatible protocol, missing project, and policy rejection must remain
distinct errors.

### 8.2 Correct routing point

Add a target field to `PromptDirectives`, but do not let it remain prompt-parser trivia.
Normalize it into each typed launch unit before target-specific planning. Then partition
the plan by target:

```text
parse/expand prompt
    → typed logical launch units with DispatchTarget
    → validate cross-unit constraints
    → local units: current admission/allocation/execution
    → remote units: authenticated remote admission/allocation/execution
```

The remote host owns timestamps, run IDs, names, workspaces, and artifact paths. The
wire request carries logical intent, project identity, model/provider requirements,
approved inputs, and finalizer policy—not client-created filesystem locations.

The directive should be consumed before forwarding the prompt so the remote runner does
not recursively dispatch it. The resolved target and source machine become immutable
provenance on the remote run.

### 8.3 Multi-agent and workflow constraints

Repeat can naturally inherit the same target. Independent alternative units may target
different machines after the typed plan can represent a target per unit.

Cross-machine families, clans, `%wait` dependencies, gates, and finalizers are much more
subtle. For the first release:

- allow a whole repeat/family to run on one target;
- allow independent launch units to use different targets;
- reject a single family/clan split across authorities;
- reject cross-machine `%wait`/unit dependencies;
- execute run finalization on the authoritative target;
- let the source observe results through the normal followed-agent protocol.

These restrictions are honest and removable. Pretending a local runner supervises a
distributed dependency graph would undermine the single-host durability assumptions.

### 8.4 Auto-follow must be crash-safe

Before the network call, write a viewer-local pending follow record containing:

- machine identity;
- client launch/idempotency key;
- creation time and source `dispatch`;
- enough logical context to render “launch pending” without a fake agent identity.

When the host accepts or a retry recovers the receipt, bind the pending record to the
authoritative agent locator. If the source crashes after acceptance, reconciliation by
idempotency key performs the binding later. If the target definitely rejects the launch,
mark the intent failed and offer retry; do not leave a phantom subscribed row.

## 9. Focus/Fleet UX

### 9.1 Information architecture

Use the existing one-line tab-strip visual language inside Agents:

```text
┌ Agents ────────────────────────────────────────────────────────────────────┐
│            ● Focus  7     │     Fleet  12 ◌                              │
├────────────────────────────────────────────────────────────────────────────┤
│ … current Agents list/detail layout …                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Focus count:** running local agents plus running followed remote agents.
- **Fleet count:** all running remote agents visible under configured hosts.
- Counts intentionally overlap; the mode labels and help text should say so.
- A filled live dot means current summaries; a hollow/dim dot means at least one count
  includes stale cached data. If no trustworthy cached count exists, show `—`, not zero.

This satisfies the requested running counts without lying during partitions. Count only
concrete live SASE agent runs; exclude synthetic family/clan rows, procs, and gates. If
the current Agents view aggregates families, the count should still derive from the
host's concrete-run summary rather than the number of rendered rows.

The strip should reuse SASE's existing `PanelTabStrip` and configured subtab cycling
conventions. Do not invent an unconfigurable key. Local-only users should see no
disruptive empty Fleet experience: either hide/soft-disable Fleet until the first machine
is enrolled, or show a single elegant onboarding panel with no background work.

### 9.2 Focus view

Focus is the current Agents experience plus followed remote rows. Preserve selection,
folds, and cached content when switching modes. Sort primarily by the existing semantic
status rules, then activity; do not segregate remote rows into a second list because the
purpose is unified management.

Every remote row needs a compact, consistent origin mark:

```text
●  fix-auth-race     @apollo   RUNNING   04:12   codex
```

The `@apollo` pill should remain visible at every width tier where an action could be
mistaken for local. A remote detail header repeats the full host and freshness state.

Followed lineage should behave predictably:

- dispatch-created work is followed automatically;
- retry/fork from a followed row follows the successor;
- following a family root follows current and future descendants by default;
- the user can choose a leaf-only follow when needed;
- unfollow removes the row from Focus but does not kill or dismiss it on its host.

### 9.3 Fleet view

Fleet groups visually by host but remains one scrollable list—not sub-sub-tabs. Host
headers are sticky/collapsible and show connectivity, freshness, live count, and capacity:

```text
▼ apollo   online · now · 5 running · 1 slot free
  ★ fix-auth-race       sase       RUNNING  04:12  Fix auth race…
  ☆ docs-refresh        website    WAITING  00:41  Refresh docs…

▼ mac      stale · 2m · 3 running last seen
  ★ perf-investigation  sase       RUNNING* 18:09  Profile ACE…

▶ gpu-box  unauthorized · reconnect
```

The initial row must answer only “Should I follow this?” It needs:

- `★` followed / `☆` not followed;
- agent or family display name;
- project;
- status and age;
- short prompt/intent summary;
- model only when it materially aids the decision;
- machine via its group header, plus origin in search results;
- stale/terminal/attention indicators.

A filled star plus an accent left rail makes followed state distinct without depending
on color. Use the same accent on the `@machine` pill in Focus. The icon provides a
color-independent signal and maps naturally to the `f` action (“follow/unfollow”) if
that key is available in the configured keymap.

Selecting a Fleet row may lazily fetch a compact remote preview. Full output, diff, or
artifacts are fetched only after an explicit view action. Searches should push query and
filters to hosts with server support, merge pages incrementally, and clearly label
partial results from offline/incompatible hosts.

### 9.4 Remote actions

Use one command vocabulary for local and remote rows, routed by an `AgentLocator`:

- view, retry, kill, fork, create child, answer gate/question, and inspect artifacts use
  the same keys when the remote host advertises equivalent semantics;
- every remote mutation displays the target machine in its confirmation/toast;
- fork/retry initiated from a remote row defaults to the same host and visibly shows
  that target before submission;
- actions on stale rows are disabled until refresh/revalidation;
- a per-host failure never freezes or clears other rows;
- local-only operations such as terminal attach or opening a remote path in the local
  editor are disabled with an explanation.

An explicit “Open remote shell” escape hatch may be offered if a provider advertises a
safe interactive transport. It is separate from ordinary agent actions and should show
the actual target. SASE must never attempt to make a remote filesystem path look locally
openable.

### 9.5 Language and status

Use “Follow” in the interface and documentation aimed at users. Use “subscription” for
the persisted mechanism and APIs. Reserve “remote” for actual topology, not the mode
name.

Connectivity should be first-class, not collapsed into agent status:

- connecting;
- online;
- reconnecting;
- stale (with age);
- offline;
- unauthorized;
- incompatible;
- provider unavailable.

A stale cached RUNNING row should render `RUNNING · last seen 2m` and cannot support a
destructive action until revalidated. This makes degraded operation calm rather than
alarmist while preserving truth.

## 10. Performance design

The TUI performance requirements should be protocol acceptance criteria, not follow-up
polish.

### 10.1 Startup and hidden-mode behavior

- With no enrolled machines, no provider import, daemon connection, cache scan, or
  additional timer should run.
- First paint uses local data plus permission-restricted cached remote summaries/rows.
- Network and provider work happens off the Textual event loop.
- Fleet row/detail hydration starts only after Fleet is opened.
- Focus starts remote synchronization only when there are followed locators (or a
  pending dispatch intent).
- A lightweight summary stream may start after first paint when machines are configured
  so counts become live, but tab rendering never waits for it.

### 10.2 Cache and event strategy

Maintain per-host caches keyed by pinned host identity and protocol/schema version:

- summary and observed time;
- bounded agent pages;
- content blobs keyed by digest;
- capability/compatibility state;
- cursors and last applied revision;
- pending mutation receipts.

Render cached state immediately, then stale-while-revalidate. SSE/websocket events carry
small revision invalidations; they do not push entire lists. Coalesce bursts by host and
project. Fetch only the visible/affected page and preserve row object identity and
selection where possible.

The server should maintain resident Rust summaries and scan/index state. Forking Python
for each count or list defeats the design even if the client is asynchronous. The prior
research measured a large qualitative difference between current command-bridge reads
and resident Rust reads; remote latency makes eliminating that fixed overhead even more
valuable.

### 10.3 Backpressure and deadlines

- Bound concurrent host connections and page fetches.
- Apply per-host exponential backoff with jitter.
- Prioritize visible Focus rows, then visible Fleet rows, then background counts.
- Cancel obsolete detail/page requests when selection or query changes.
- Never let one slow host delay merged results from others.
- Give every network and plugin call a deadline.
- Avoid periodic full-fleet scans; reconcile revisions and visible pages.

ACE's established p95 `j`/`k` navigation target of under 16 ms must hold with remote
machines configured, disconnected, and producing event bursts. That implies no I/O,
serialization, plugin loading, or full-list merging on key handling/render paths.

## 11. Failure and recovery matrix

| Failure | Required behavior |
|---|---|
| Tailscale is not installed | Tailnet provider reports unavailable; static/local operation remains intact. |
| Enrolled host is offline | Show cached rows/counts with age; disable mutations; do not queue destructive work. |
| Host identity changes at same URL/name | Quarantine connection and require explicit re-enrollment; never silently trust. |
| Protocol is newer/older | Negotiate supported version/capabilities; show incompatible if no safe overlap. |
| Provider plugin crashes | Isolate that provider's hosts; preserve local and other-provider data. |
| Launch response is lost | Retry same idempotency key and recover original receipt/run; do not duplicate. |
| Source crashes during dispatch | Pending follow intent reconciles against durable target receipt. |
| Remote name is reused | Run locator and revision prevent actions from hitting the replacement. |
| SSE disconnects/misses events | Snapshot revision reconciliation repairs state. |
| Credential expires/revokes | Mark unauthorized; preserve cache; prompt re-enrollment, never fall back to weaker auth. |
| Project absent/mismatched | Target rejects before allocation with structured remediation. |
| User unfollows | Remove from Focus only; remote run continues. |
| User kills from stale row | Force refresh/revalidation; never send against cached name alone. |

## 12. Questions the design should answer

### Is there a better way than two subtabs?

A single list with a remote filter looks simpler but fails at scale: browsing the fleet
would either flood the working list or require a hidden query state. Top-level per-host
tabs make machine location too dominant and create the forbidden sub-sub-tab pattern.
Two modes are correct; **Focus/Fleet** is the better semantic pair.

### Should followed remote agents be copied into local history?

No. Copying revives sync/import conflicts, duplicates identity, and makes source
dismissal ambiguous. Store a small local subscription plus an immutable cached
projection. If the user wants a durable cross-boundary result, export/register an
artifact explicitly.

### Should the Fleet view show only followed agents?

No; then it cannot serve discovery. Focus is the followed working set. Fleet must show
all discoverable remote agents, with followed state unmistakable.

### Should remote viewers share dismissal and fold state?

No. These are viewer-local presentation preferences. A target-host archival or deletion
operation is a different, capability-gated mutation and should be named accordingly.

### Should plugins be able to implement custom remote backends?

Not in the first architecture. They should implement access to the standard protocol.
If a future provider genuinely cannot expose that protocol, it should be adapted by a
local bridge that still speaks it. This keeps one identity/action/cache contract.

### Should Tailscale Services be the abstraction?

No. SASE machines are not interchangeable replicas: each owns distinct processes,
projects, credentials, and workspaces. A stable service address is useful for a service
pool but obscures which authority accepted a launch. Pin a host installation identity
and address that host directly.

### Should runtime auto-discovery be optional?

It should be absent initially, not merely optional. Explicit init-time discovery reduces
latency, surprise, and trust churn. A later background discovery feature can propose
unenrolled candidates without making them active.

### Should exact counts update while Fleet is hidden?

Only through the cheap summary channel, after first paint. Exact-but-old values must be
marked stale; unknown must render as `—`. Fetching complete lists to maintain decorative
counts would be a poor trade.

### Should SASE automatically choose the “best” machine?

Not initially. `%dispatch:<machine>` is legible and reproducible. Automatic placement
needs policy for project locality, credentials, cost, models, capacity, privacy, and
failure; it deserves its own design after explicit dispatch is reliable.

## 13. Suggested delivery sequence

### Phase 0: contract and measurements

- Specify identities, summary/snapshot/event envelopes, mutation receipts, capability
  vocabulary, auth scopes, and freshness semantics in `sase-core`.
- Record local-only startup/navigation baselines and remote-failure test scenarios.
- Decide the host-installation identity lifecycle and credential store.

### Phase 1: make the existing local path provider-safe

- Introduce `AgentLocator`, `AgentOrigin`, opaque content handles, and capability-based
  action routing.
- Make the direct/local provider implement the same interfaces.
- Change ACE row identity to include authoritative origin/project/run identity.
- Remove PID/path assumptions from shared TUI commands.

This phase should produce no user-visible remote feature, but it is the dependency that
prevents remote special cases from infecting the TUI.

### Phase 2: harden the Rust host protocol

- Move agent summaries/listing to resident Rust/indexed state.
- Add stable host/run/project identities, paging, revisions, real invalidations, and
  opaque content reads.
- Add scoped auth, safe enrollment, pinned identity, and audit.
- Add durable idempotency/mutation receipts and liveness preconditions.
- Bind conservatively (loopback by default) and test Tailnet Serve/static TLS exposure.

### Phase 3: providers and init

- Add the `sase_dispatch` entry-point group and typed hooks.
- Ship lazy built-in `tailnet` and `static` providers.
- Add config schema/merge/doctor support and explicit discovery/enrollment UX.
- Add compatibility, identity-change, credential, and offline diagnostics.

### Phase 4: following and Focus/Fleet reads

- Add the durable viewer-local subscription store in Rust.
- Implement cached federated summaries/pages/events.
- Add Focus/Fleet, honest counts, star/rail distinction, machine pills, stale states,
  paging, and server-side search.
- Initially keep remote operations read-only except follow/unfollow.

### Phase 5: dispatch and safe mutations

- Add `%dispatch` to parser, completion, prompt metadata, typed plan, and admission.
- Route before local allocation; implement target-side allocation.
- Add pending follow intents and idempotent launch recovery.
- Enable capability-gated kill/retry/fork/create/gate operations incrementally.

### Phase 6: advanced topology only after evidence

- Consider cross-machine workflow dependencies, automatic placement, SSH interactive
  escape hatches, and cross-owner delegation separately.
- Do not make these blockers for explicit same-owner dispatch.

## 14. Acceptance criteria

### Correctness and reliability

- A lost launch response cannot create a duplicate run.
- A stale or name-reused row cannot kill the wrong process.
- Dispatch success eventually appears in Focus after either client or connection crash.
- Unfollow never changes target process state.
- Host identity replacement is detected and quarantined.
- Offline and unauthorized states never masquerade as an empty fleet.
- Local, Tailnet, and static-provider agents share one locator/action contract.

### Performance

- With no enrolled machines, startup and Agents behavior are indistinguishable from the
  current local-only path within measurement noise.
- First paint never waits on provider loading or network I/O.
- `j`/`k` p95 remains below the established 16 ms target during disconnects and event
  bursts.
- Opening Fleet fetches bounded summaries/first pages, not full histories.
- Hidden Fleet performs no detail/history hydration.
- One slow host does not delay local rows or other hosts.

### UX

- A user can tell local from remote and followed from unfollowed without relying on
  color.
- Every remote action names its target machine.
- Counts communicate stale/unknown state honestly.
- Focus is useful without understanding fleet architecture.
- Fleet has one merged browse surface, no per-machine tabs.
- Disabled actions say whether the cause is capability, freshness, permission, or
  connectivity.
- Machine completion never causes network activity.

## 15. Risks and explicit non-goals

The largest risk is attempting UI aggregation before identity and mutation contracts are
safe. That path will look successful in a happy-path demo but produce duplicate launches,
wrong-target actions, and permanent local/remote conditionals.

Other risks are:

- treating Tailnet identity as sufficient authorization;
- importing all dispatch plugins at startup;
- letting exact title counts trigger full remote scans;
- leaking prompts/output into logs or broad caches;
- assuming repo basename equals project identity;
- mixing viewer dismissal with target archival/deletion;
- promising parity for local-only actions that fundamentally require a local terminal or
  filesystem;
- expanding the first version into a distributed scheduler.

Non-goals for the first release should be cross-owner process control, cross-host clans
or wait graphs, automatic placement, arbitrary remote shell execution, and replicated
agent history.

## Recommended solution

Build remote dispatch as a **SASE-owned Rust protocol reached through pluggable
machine-access providers**. Add a lazy `sase_dispatch` plugin group with explicit
discover/plan-enroll/apply-enroll/resolve hooks. Ship `tailnet` as the default available
provider and `static` as the non-Tailscale baseline. Store an explicit provider on each
enrolled machine, pin a stable host installation identity, keep secrets out of YAML, and
perform discovery only during explicit init/refresh workflows.

Before exposing the feature, refactor ACE around global agent locators, opaque content
handles, and capability-based actions; then harden the existing Rust gateway with
resident indexed reads, scoped authorization, safe enrollment, revisioned summaries and
snapshots, real invalidation events, and durable idempotent mutation receipts.

Replace the proposed Local/Remote labels with **Focus/Fleet**. Focus contains all local
agents and followed remote agents. Fleet is one merged, paged remote catalog grouped by
host, with followed rows marked by both `★` and an accent rail. Show honest running
counts from cheap cached summaries, including stale/unknown indicators. Keep all network
and plugin work off the render path; load detailed content only on demand.

Implement `%dispatch:<machine>` as a typed launch target resolved before any local
allocation. Let the authoritative host validate the project and allocate the run. Write
a durable pending follow intent and idempotency key before dispatch, bind it to the
returned remote run, and recover it after lost responses or crashes. Preserve familiar
management keys only where remote capabilities truly match; clearly explain stale,
offline, unauthorized, and local-only limitations. Defer automatic placement and
cross-machine workflows until explicit same-owner dispatch is demonstrably reliable.
