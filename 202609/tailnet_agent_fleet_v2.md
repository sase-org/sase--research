# Tailnet Agent Fleet v2: One ACE TUI, Many Machines

**Date:** 2026-09-05

**Status:** Architecture recommendation

**Scope:** A single user managing SASE agents on their own Tailscale devices from one `sase ace` TUI

## Executive summary

SASE should make each machine an authoritative process-control endpoint and make ACE a federated, cache-first client of those endpoints. The transport should remain deliberately ordinary: versioned HTTP/JSON for snapshots and commands, plus Server-Sent Events (SSE) as an invalidation hint, carried over per-device Tailscale Serve HTTPS endpoints. It should not use `agent_sync`, a shared database, NATS, ZeroMQ, gRPC, or a central scheduler for the first implementation.

This conclusion agrees with the strongest part of the earlier `tailnet_agent_fleet.md` proposal—reuse the Rust gateway and Tailscale—but tightens it in five important ways:

1. Remote state is never imported into the local agent store. The removed `agent_sync` import leg stays removed.
2. A durable SASE host-installation ID and agent-instance ID, not a machine name, PID, path, or row name, anchor identity and mutations.
3. The current mobile pairing and token model is not safe enough to expose unchanged as fleet enrollment.
4. SSE is only a prompt to refresh an authoritative snapshot. Correctness never depends on receiving every event.
5. Mutations use a durable operation journal and optimistic concurrency. A network retry must not create a second agent or kill a reused target.

The result is a direct star topology: the MacBook ACE connects independently to each enrolled host. Local agents render immediately; cached remote rows render as explicitly stale; healthy hosts hydrate in parallel; and a slow, sleeping, or incompatible machine cannot block the rest of the TUI.

## Question and constraints

The desired experience is parity with local agent management—launch, inspect, wait, retry, kill, and related actions—across known personal machines. The design must tolerate ordinary tailnet conditions: direct WireGuard links, DERP or peer-relay fallback, sleep/wake cycles, address and machine-name changes, partial upgrades, and lost responses after a mutation may already have committed.

The scope is intentionally narrower than multi-user collaboration:

- one human principal and that person's trusted machines;
- one authoritative host for every live process;
- no globally ordered cross-host event log;
- no cross-host process migration;
- no assumption that every repository exists on every host;
- no resurrection of foreign runs as local SASE agents.

That boundary follows `sase_collaboration_architecture.md`: the fleet is a process-plane feature crossing a machine boundary for one user, while forge collaboration and published agent artifacts remain separate concerns.

## Research basis

This report reviewed the audited research artifacts
`research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md` and
`research:202609/sase_collaboration_architecture.md`, the completed phases of the
`sase-ws` epic, and the current SASE and Rust-core implementations at these revisions:

- `sase`: `302e6d643af4`
- `sase-core`: `fe9a643cd295`
- research sidecar baseline: `a487088cf011`

The code audit covered the ACE provider seam, agent row model and actions, mobile gateway routes and wire types, pairing and bearer-token storage, event replay, mobile launch/lifecycle bridges, launch-admission journal, and the Rust agent artifact index.

Point-in-time probes on `athena` also help put the transport problem in proportion:

| Probe | Observed result |
|---|---:|
| Tailscale ping to `apollo` | direct, 7–14 ms |
| Tailscale ping to the MacBook | direct, 39–79 ms |
| `sase agent list --json` | about 24.5 KB and 10.8 s |
| `sase mobile agent-bridge list-agents` | about 16.1 KB and 5.6 s |

These are diagnostic samples, not a benchmark. They nevertheless show that today's scan/process startup cost is orders of magnitude larger than the observed tailnet latency. Changing wire protocols cannot fix that. Keeping a resident Rust service and querying the existing Rust index can.

The network recommendations use current primary documentation. Tailscale Serve can expose a loopback service only inside a tailnet and can add signed identity and application-capability headers; the backend should remain on loopback ([Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)). Tailnet links may move between direct, peer-relayed, and DERP-relayed paths while retaining WireGuard end-to-end encryption, so the application still needs deadlines and stale-state behavior ([connection types](https://tailscale.com/docs/reference/connection-types)). Grants are deny-by-default and can constrain both connectivity and application capabilities ([grants syntax](https://tailscale.com/docs/reference/syntax/grants), [application capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities)).

## What changed from the first fleet proposal

### `agent_sync` is no longer a live-state fallback

The `sase-ws` work removed the import engine, incoming cache, ACE import surfaces, and related configuration. That was the right decision. A remote fleet cache must not be smuggled back in under another name:

- remote rows do not enter the local artifact index;
- remote names do not enter the local name registry;
- remote processes never become local process objects;
- going offline does not cause an imported copy to look authoritative;
- published terminal history, if available, is resolved lazily through the archive/artifact plane.

The controller may maintain an ordinary UI cache keyed by host and run identity. That cache is disposable presentation state, not an agent store and not a synchronization leg.

### Machine names are labels, not identity

The live tailnet already demonstrates why: Tailscale's device name and SASE's configured machine label need not match, and a Tailscale device rename changes its MagicDNS name ([MagicDNS](https://tailscale.com/docs/features/magicdns), [machine names](https://tailscale.com/docs/concepts/machine-names)). A physical machine can also contain more than one SASE home.

The protocol therefore needs three separate concepts:

- `host_installation_id`: an immutable random UUID persisted per SASE home;
- display/provenance labels: SASE owner, machine, operating system, and friendly name;
- endpoint: the mutable per-device MagicDNS name or Serve URL used to connect.

Enrollment pins the host ID and a host key/fingerprint to the endpoint. An endpoint that later presents a different host fails closed and requires explicit re-enrollment.

### The existing gateway is a foundation, not a finished fleet API

The Rust `sase_gateway` already provides Axum routing, loopback defaults, bearer hashing, contract snapshots, auditing hooks, and mobile agent operations. Reusing that implementation is substantially better than creating a second daemon.

However, the present mobile bridge has constraints that should not become permanent fleet contracts:

- each list or lifecycle request forks a Python `sase mobile agent-bridge` process;
- the list DTO is a narrow mobile projection and lacks a host revision or snapshot cursor;
- ordinary launch carries a `request_id` but does not deduplicate dispatch with it;
- kill has no operation ID or expected-target revision;
- launch results expose an absolute artifact directory;
- all paired tokens receive the same broad capability set;
- authenticated polling rewrites `devices.json` to update `last_seen_at` on every request.

Most importantly, the unauthenticated pairing-start route returns the pairing secret in the same remote response. A caller who can reach that route can initiate and finish its own pairing. Fleet enrollment cannot expose that behavior.

### The current event stream is not a live change feed

The gateway keeps an in-memory replay ring and sends heartbeats, but an already-connected SSE response is not subscribed to subsequent appended events. Changes made outside gateway mutation handlers are also invisible. Sequence numbers restart with the process and do not include a boot epoch.

This is repairable, but it reinforces the right abstraction: SSE should reduce refresh latency, never be the source of truth.

## Architecture decision

### Topology: direct federation

Every managed SASE installation runs one supervised per-user daemon. ACE holds an explicit enrollment record for each host and opens independent sessions to them:

```text
                         Tailscale Serve HTTPS
                    +------------------------------+
                    |                              |
              +-----v------+                 +-----v------+
              | host A     |                 | host B     |
              | sase daemon|                 | sase daemon|
              | authority A|                 | authority B|
              +------------+                 +------------+
                    ^                              ^
                    | HTTP snapshots/commands     | HTTP snapshots/commands
                    | + SSE invalidations         | + SSE invalidations
                    +--------------+---------------+
                                   |
                              +----v-----+
                              | ACE TUI  |
                              | cache +  |
                              | federation|
                              +----------+
```

There is no fleet-wide primary. Each host is the only authority for its own live agents and operation journal. The ACE controller composes local and remote providers into one view.

Tailscale Services should not sit in front of the hosts. Services deliberately offer a stable name that can route to any available tagged service host, which is excellent for interchangeable replicas but incorrect when a request must reach the one machine that owns a process. They also require service hosts to use tag-based identity ([Tailscale Services](https://tailscale.com/docs/features/tailscale-services)). Per-device Serve endpoints preserve authority.

### Host service: extend `sase_gateway`

Add a versioned `/api/fleet/v1` surface to the existing Rust gateway. Reuse its server, authentication, audit, and compatibility infrastructure, but do not freeze the mobile DTO as the desktop fleet model.

The daemon should be:

- a `launchd` user agent on macOS and a `systemd --user` service on Linux;
- bound to a Unix socket and/or `127.0.0.1`, never a LAN address;
- published to the tailnet through Tailscale Serve, never Funnel;
- restartable without losing host identity or completed operation receipts;
- independently diagnosable through `sase fleet host status` and `sase fleet doctor`.

The resident Rust process should query `sase_core` directly. The existing artifact index already supports windowed projections; the fleet API should add a purpose-built row projection and a transactionally updated source revision. Python remains appropriate for presentation glue or operations not yet migrated, but a Python process per poll must not be the steady state.

### Read model: snapshot plus invalidation

The authoritative read is a paginated snapshot:

```json
{
  "schema": 1,
  "host_id": "01b1...",
  "boot_id": "1a2c...",
  "revision": 841,
  "observed_at": "2026-09-05T14:12:03Z",
  "capabilities": ["agents.read", "agents.kill"],
  "rows": [],
  "next_page": null
}
```

`revision` changes transactionally with any visible indexed state. HTTP conditional requests use an ETag derived from the host ID and revision. A summary endpoint serves virtualized rows; separate detail and content endpoints fetch expensive data lazily.

SSE carries small invalidations and operation progress:

```json
{
  "event_id": "1a2c...:319",
  "kind": "agents.changed",
  "revision": 842
}
```

Event IDs combine an unpredictable boot epoch with a monotonic sequence. A missing replay window, boot change, or revision gap produces `resync_required`; the client then conditionally fetches a snapshot. `Last-Event-ID` is useful for reconnection but does not eliminate the need to resynchronize ([WHATWG SSE](https://html.spec.whatwg.org/dev/server-sent-events.html)).

Events must come from a real broadcast subscription and include changes observed outside the HTTP handlers. A cross-platform filesystem/process observer can make updates fast, while periodic indexed reconciliation remains the correctness backstop. The controller should also reconcile every 30–60 seconds with jitter. This yields convergence even when the watcher, SSE connection, or laptop sleep loses a transition.

### Identity and wire boundaries

Generate an `agent_instance_id` before launch admission and persist it with the run. The globally unique row key is:

```text
(host_installation_id, agent_instance_id)
```

User-facing agent names, PIDs, filesystem paths, tmux sessions, and project labels remain display attributes. They are never mutation targets.

The wire projection should contain stable state, display fields, timestamps, progress, available actions, and opaque content handles. It must not serialize the full Python `Agent` object or make a remote absolute path actionable. Content responses should carry a digest, size, media type, and bounded bytes or stream. Project availability should be expressed by an immutable project/repository identity plus host-local display data; MVP launch only targets projects already configured on that host and does not clone repositories automatically.

This boundary lets the local and remote providers render the same row contract without pretending their implementation details are identical.

### Mutation model: durable operations, not request/response optimism

Network ambiguity matters more than network latency. If ACE sends launch, the host commits it, and the response is lost, retrying a conventional POST can launch twice. HTTP does not make POST idempotent automatically, and preconditions such as `If-Match` exist specifically to prevent lost-update races ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). The IETF `Idempotency-Key` document is a useful design reference, but its current draft expired in April 2026 and is not a standard to depend upon ([draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)).

Use a SASE-owned durable operation contract:

```json
{
  "operation_id": "0199...",
  "kind": "agent.launch",
  "payload": {},
  "payload_fingerprint": "sha256:...",
  "expected_revision": 841,
  "deadline": "2026-09-05T14:13:03Z"
}
```

The host transactionally records `accepted`, then advances through `running` to `succeeded`, `failed`, or `expired`. A duplicate operation ID with the same fingerprint returns the original receipt; the same ID with a different fingerprint returns `409 Conflict`. The initial response is `202 Accepted` with an operation resource. Polling and SSE both expose progress.

For launch, extend the existing typed launch-admission journal rather than inventing an unrelated deduplication store. The journal must reserve the agent instance ID before spawning and recover after a crash by detecting the already-created run. Merely forwarding today's `request_id` is insufficient.

For kill, retry, wait, and other lifecycle actions, require the stable target identity and an expected target revision/state. A stale command must not affect a new process that reused a PID, name, or shell. The owning host performs final capability, state, capacity, and project validation immediately before execution.

ACE does not enqueue blind mutations for an offline host. Actions remain disabled until a fresh target validation succeeds. This makes the user's intent visible instead of converting a click into a surprising command hours later.

### Security and enrollment

The secure baseline is defense in depth:

1. Tailscale grants permit only intended controller principals/devices to reach the Serve endpoint.
2. Optional application capabilities describe a coarse role such as `view`, `operate`, or `admin`; the gateway validates them.
3. SASE issues a scoped, revocable bearer credential whose hash is stored on the host.
4. Enrollment pins the immutable host ID and host key/fingerprint.
5. The effective permission is the intersection of tailnet policy, token scopes, endpoint capability, and current host policy.

Pairing initiation must be local-only through the daemon's Unix socket or an interactive command on the target host. The secret must never be returned to an unauthenticated remote caller. A controller completes enrollment using a short-lived, single-use secret and displays both endpoint and host fingerprint for confirmation. Store the controller credential in the OS keychain or an equivalent protected secret store; expose list/revoke/rotate operations.

Audit every mutation with principal, controller device, host ID, agent ID, operation ID, payload fingerprint, authorization decision, result, and timestamps. Coalesce `last_seen_at` persistence instead of rewriting the token database on every poll. Rate-limit authentication, pairing, and mutations independently.

Tailnet Lock can be recommended as optional hardening against control-plane key substitution, but should not be an application prerequisite ([Tailnet Lock](https://tailscale.com/docs/features/tailnet-lock)).

### Controller and TUI model

Implement a `FederatedAgentsDataProvider` over the existing ACE provider contract:

- the local direct provider produces the first snapshot immediately;
- one `RemoteHostProvider` owns each enrolled host's connection, cache, deadlines, backoff, and version negotiation;
- host refreshes run concurrently in pump-free background work;
- each result patches only affected rows and counts;
- one failed host never delays local input or another host;
- incompatible hosts stay visible with an upgrade action, not as generic offline failures.

The cache stores the last bounded row projection, revision, capabilities, and observation time. On disconnect, terminal facts remain visible, active-looking states become neutralized, and the UI says exactly when the host was last observed. Cached rows are never actionable.

A visually coherent Agents tab can provide:

- an “All hosts” strip with online, stale, offline, unauthorized, and incompatible counts plus capacity;
- grouping and filtering by host without making host another kind of agent row;
- the existing row action menu, populated from current capability bits;
- a host badge and precise stale-age badge on every remote row;
- a launch target picker showing project availability, capacity, latency/staleness, and an optional “Auto” suggestion;
- progressive detail loading rather than blocking first paint.

“Auto” is only client-side ranking among currently eligible hosts. The selected host remains the admission authority. It should initially consider explicit user preference, project availability, free configured slots, freshness, and measured latency—not build a distributed scheduler.

Some local actions cannot honestly be made transparent. Opening a remote tmux pane or editor should be an explicit SSH deep link or a remote-view action. It must not pretend a remote process is local. Likewise, v1 should not give agent prompts cross-host wait semantics; the TUI may invoke `wait` or `retry` on the host that owns the target.

The existing TUI performance rules remain binding: cache-first first paint, no data-scaled work on the message pump, selective row updates, and p95 navigation latency under 16 ms.

## Alternatives considered

| Alternative | Benefit | Why it is not the default |
|---|---|---|
| Git/`agent_sync` replication | Durable, already familiar | Imports stale process representations, cannot provide safe mutation semantics, and contradicts the completed removal decision |
| NATS with leaf nodes | Strong pub/sub and request/reply; can grow into a real control plane | Adds broker lifecycle, routing, persistence, and security operations before the personal fleet needs them ([NATS concepts](https://docs.nats.io/nats-concepts/core-nats), [leaf nodes](https://docs.nats.io/running-a-nats-service/configuration/leafnodes)) |
| gRPC | Typed streaming, deadlines, and retry support | Browser/TUI interoperability and operational complexity are worse here, while idempotency and reconciliation remain application problems ([gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/), [deadlines](https://grpc.io/docs/guides/deadlines/), [retry](https://grpc.io/docs/guides/retry/)) |
| WebSockets | Bidirectional low-latency channel | Commands already fit HTTP; bidirectionality couples correctness to a long-lived socket and complicates reconnection |
| ZeroMQ | Fast and flexible sockets | Requires building discovery, durable identity, authorization, retry, replay, and observability into the application |
| Shared database or central scheduler | Convenient global queries | Creates a fleet-wide authority and availability dependency that the one-user, few-host problem does not require |
| Tailscale Services | Stable service address and failover | It routes among interchangeable hosts, but live agents belong to one exact host |

Reconsider a broker only if the real workload grows beyond roughly tens of hosts or gains many simultaneous controllers, cross-host agent-to-agent coordination, or a need for sub-second globally ordered events. Those are different requirements, not reasons to pre-install distributed-systems machinery now.

## Delivery plan

### Phase 0: contract, identity, and fault harness

- Define versioned fleet wire fixtures and capability negotiation.
- Add durable host-installation and agent-instance identities.
- Specify the operation journal, fingerprints, state machine, and retention.
- Build tests for dropped responses, duplicated commands, restarts, stale targets, and event gaps.
- Fix pairing before any tailnet exposure.

### Phase 1: daemon operability and enrollment

- Add supervised user services for macOS and Linux.
- Add local-only pairing initiation, scoped credentials, fingerprint pinning, revoke/rotate, status, and doctor commands.
- Configure loopback-only Tailscale Serve and document least-privilege grants.

### Phase 2: resident read-only host API

- Move summary queries onto the Rust index and add transactional revisions.
- Ship paginated snapshots, ETags, bounded detail/content endpoints, and capabilities.
- Measure snapshot time and payloads with realistic fleets.

### Phase 3: federated read-only ACE

- Add per-host providers and a cache-backed federator.
- Add host status, stale semantics, version errors, and selective row patches.
- Add real SSE invalidation plus periodic reconciliation.

### Phase 4: lifecycle operations

- Land the durable operation resource and journal.
- Enable wait, kill, and retry with target preconditions and audit records.
- Add exhaustive lost-response and stale-identity tests.

### Phase 5: remote launch and routing

- Integrate ordinary launches with launch admission and crash recovery.
- Add project availability and capacity advertisement.
- Add the explicit host picker, then an explainable “Auto” suggestion.

### Phase 6: parity and polish

- Add lazy logs/content and explicit remote terminal/editor affordances.
- Tune batching, cache retention, reconnect jitter, and accessibility.
- Remove any temporary beta flag before the completed feature lands.

## Acceptance criteria

The feature is ready when all of these hold:

- local agents paint and remain navigable while one remote host is hung;
- healthy hosts appear independently, and cached rows have honest stale ages;
- losing a successful launch response and retrying creates exactly one agent;
- a stale kill cannot affect a replacement process or reused name/PID;
- daemon restart, replay-window loss, and boot-epoch change converge automatically;
- direct-to-DERP transitions and laptop sleep/wake recover without restarting ACE;
- endpoint reuse with a different pinned host identity fails closed;
- mixed compatible versions negotiate features and incompatible versions remain legible;
- Tailscale grant or SASE token revocation takes effect predictably;
- viewing remote state creates no local agent artifacts or registry entries;
- snapshot/detail responses are bounded and disclose no actionable absolute paths;
- ACE preserves cache-first startup and p95 `j`/`k` latency below 16 ms.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| False confidence in stale process state | Observation timestamps, neutralized active state, actions disabled until fresh validation |
| Duplicate launches after ambiguous failures | Durable operation ID, payload fingerprint, launch-admission receipt, preallocated run identity |
| Wrong-host or wrong-process mutation | Pinned host ID/key plus stable agent ID and expected revision |
| Tailnet policy accidentally too broad | Loopback backend, Serve-only exposure, deny-by-default grants, scoped SASE credential |
| One bad host freezes ACE | Per-host deadlines/backoff, concurrent pump-free tasks, selective updates |
| Watcher or SSE loses an event | Events are hints; periodic revision-based reconciliation is authoritative |
| API becomes coupled to Python/TUI internals | Narrow Rust-owned fleet projection and opaque content handles |
| Fleet cache recreates `agent_sync` | Disposable UI cache, no local artifact/index/name materialization, architecture tests |
| Daemon adoption creates operational burden | Reuse `sase_gateway`; supervised user services; status, doctor, logs, and explicit enrollment |

## Recommended solution

Build **SASE Fleet** as a versioned feature of the existing Rust `sase_gateway`, running as a supervised, loopback-only per-user daemon on every managed SASE installation and exposed through that device's Tailscale Serve HTTPS endpoint. Give each installation an immutable host ID and each run a preallocated immutable agent ID. Let ACE directly federate its local provider with one independently cached remote provider per enrolled host.

Use HTTP/JSON for bounded snapshots, details, and durable operation resources; use SSE only to invalidate snapshots and report operation progress. Make host snapshots authoritative and periodic reconciliation mandatory. Keep cached offline rows visible but explicitly stale and non-actionable. Resolve published history lazily through the separate artifact/archive plane, and never import remote process state into local SASE storage.

Before enabling mutations, replace remote pairing-start with local-only enrollment, add pinned host fingerprints and scoped revocable credentials, and enforce the intersection of Tailscale grants, application capabilities, token scopes, and host policy. Then extend the existing launch-admission machinery into a durable, fingerprinted operation journal so retries are exactly-once from the user's perspective and stale lifecycle commands fail safely.

This direct, per-host architecture is the most reliable fit for a personal tailnet, the most robust under partial failure, and the most beautiful in the TUI: local-first, progressively hydrated, visibly honest about staleness, and free of a new broker or resurrected synchronization subsystem. Start read-only, prove convergence and responsiveness, add lifecycle operations, and make remote launch the final mutation milestone.
