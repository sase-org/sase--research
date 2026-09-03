---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Cross-Machine SASE Agent Control Over Tailscale

## Research question

How should SASE let one `sase ace` TUI discover, view, launch, resume, retry, and kill
agents on a small set of known machines—especially Tailscale-connected personal
devices—with local-like behavior, bounded lag, and reliable failure handling?

## Scope and method

This report evaluates the current SASE architecture and five transport/topology
options: HTTPS with JSON and server-sent events (SSE), gRPC, ZeroMQ, NATS/JetStream,
and SSH. It treats the existing Git-backed agents sidecar separately because that
system solves durable history and import, not live process control.

The repository review covers SASE at `4c1c7b24ef39` and `sase-core` at
`51df9061fd85`. The external research uses official project specifications and
documentation. The most important design criterion is not message throughput; a
personal fleet produces very little control traffic. The hard problems are command
identity, replay, stale state, authorization, version skew, partial failure, and making
sure a remote PID or path can never be mistaken for a local one.

## Executive summary

SASE should use a direct star topology: ACE connects independently to a narrow SASE
host gateway on every configured machine. The gateway should extend the existing Rust
`sase_gateway` implementation and expose a versioned HTTPS/JSON API plus an SSE event
stream. Each machine remains the sole authority for its own agent processes and source
stores. There is no central broker and no peer-to-peer coordination between hosts.

Tailscale supplies the private routed network, DNS, encrypted transport, and the first
authorization boundary. Run each gateway on loopback and publish it with persistent
Tailscale Serve. Add per-controller SASE credentials and scoped actions as defense in
depth; do not rely solely on network membership or forwarded identity headers.

The existing components already point toward this design:

- `sase-core/crates/sase_gateway` is an Axum gateway with fixed operations, bearer-token
  authentication, audit logging, health checks, JSON endpoints, SSE heartbeats, event
  IDs, bounded replay, and an explicit `resync_required` response.
- ACE has an `AgentsDataProvider` boundary with snapshot IDs, cursors, stable row
  handles, capability flags, pagination, lazy details, and event application. Its
  daemon mode is currently disabled, but the seam survived the earlier daemon revert.
- Existing lifecycle entry points already centralize launch, kill, retry, and resume
  behavior. A gateway should call these rather than duplicate process management.
- The Git agents sidecar already provides machine-qualified identity and durable remote
  history. It should remain the asynchronous historical plane, not carry live commands
  or claim that imported processes are still running.

Before mutations are enabled, the gateway needs a durable idempotency journal, opaque
run identities, optimistic state checks, explicit operation results, and a passive
state observer. The current mobile event stream announces gateway-originated mutations
but does not observe all CLI, ACE, axe, or filesystem changes, so it is not yet a
complete remote control plane.

ZeroMQ is not recommended. Its low latency is attractive, but SASE would have to build
the application protocol, authentication, discovery, request deduplication, replay,
schema evolution, health model, and observability itself. gRPC is the strongest
alternative but would duplicate a working HTTP gateway and add a second client/server
toolchain without removing any of the difficult application-level reliability work.
NATS/JetStream is justified only if SASE later needs durable disconnected work queues,
large fan-out, or many simultaneous controllers.

## 1. What exists today

### 1.1 Local state and operations

SASE currently treats local source stores under `~/.sase` and local process state as
authoritative. Python owns filesystem, plugin, provider, process, and TUI side effects;
shared backend/domain behavior belongs in the required Rust core. Launch paths used by
CLI, ACE, axe, editor, and mobile entry points converge on the same persistent stores
and lifecycle functions.

This boundary should remain intact. A remote feature should invoke the owning machine's
normal lifecycle functions. It should not introduce another implementation of agent
state transitions or synchronize writable process state between machines.

### 1.2 The agents sidecar is historical, not live

`docs/agents_sidecar.md` defines a per-project Git sidecar that publishes
machine-owned hood snapshots and machine-qualified names. It deliberately excludes
PIDs, absolute paths, and other local execution state. Imported agents that were active
on their source machine become stopped historical records locally.

That is the correct semantic boundary. Git gives SASE durable, conflict-resistant
history and an offline revival path, but polling, commits, and merges are unsuitable
for live presence or command acknowledgement. The sidecar should complement the live
gateway rather than be replaced by it:

| Plane | Authority | Data | Consistency |
|---|---|---|---|
| Live host gateway | The machine running the process | Current status, details, logs, commands | Online snapshot plus bounded event lag |
| Git agents sidecar | Each publishing machine's historical namespace | Durable prompts, chats, commits, terminal history | Eventual, mergeable, offline |

When a host is online, its gateway wins for live status. When it is offline, ACE may
show the last sanitized snapshot and sidecar history, but must label both as stale and
must not imply that a process is alive.

### 1.3 The mobile gateway is a useful foundation

`sase_gateway` already exposes an Axum HTTP server, fixed JSON operations, a pairing and
token flow, hashed credential storage, JSONL audit records, and an SSE stream. The
stream uses monotonic event IDs, a bounded in-memory replay buffer, heartbeats, and
`Last-Event-ID`; buffer loss or server restart can force a full resynchronization. This
matches the web platform's SSE model, where clients automatically reconnect and send
the last observed event ID ([WHATWG Server-Sent Events](https://html.spec.whatwg.org/dev/server-sent-events.html)).

The existing gateway is intentionally narrow and denies arbitrary shell commands,
paths, working directories, and environment variables. Preserve that design. The new
host API can share its server, authentication, audit, and event infrastructure without
forcing the fleet API to reuse the mobile client's deliberately shallow agent DTOs.

### 1.4 ACE already has the beginning of the client boundary

ACE's `AgentsDataProvider` contract contains most of the right read-side abstractions:
bounded snapshots and pages, opaque cursors, stable row handles, event application,
lazy details, and advertised capabilities. The current direct provider is local, and
the daemon-backed configuration is disabled.

The remaining problem is that the `Agent` presentation model and several actions still
assume local artifact paths and PIDs. Remote rows cannot safely be dropped into that
model unchanged. The provider seam should be completed with wire-safe summaries,
details, logs, and operation routing. In particular:

- A row handle must contain a machine identity and immutable run identity, not merely a
  name or timestamp.
- Remote PIDs and filesystem paths must never enter a code path that signals or opens a
  local resource.
- Actions must be routed to the provider that owns the row.
- Capability negotiation must determine which buttons and keybindings are enabled.

### 1.5 The earlier full daemon is a warning

The repository history contains a large daemon/indexed-projection rollout that added
Unix RPC, SQLite/WAL projections, schedulers, watchers, provider hosting, and remote
sync, then was reverted in `5a65fa4fc` (`feat: revert sase-3e daemon rollout`). The
retained data-provider seam is useful, but reviving the whole daemon would repeat an
unnecessarily large migration.

The fleet feature needs a supervised host gateway and a small durable command journal.
It does not need to replace source stores with a database, own all scheduling, or make
local ACE depend on a daemon before remote access works.

## 2. Requirements and failure model

A robust design should make the following invariants explicit:

1. **Single ownership.** The host running an agent is the only writer of its live state
   and the only machine allowed to signal its process.
2. **At-most-once effect for requested mutations.** A lost HTTP response followed by a
   retry must not launch two agents or kill a newer process that reused an identifier.
3. **Authoritative snapshots.** Events reduce latency, but a complete snapshot is the
   recovery mechanism after missed events, server restart, buffer overflow, or version
   mismatch.
4. **Visible uncertainty.** Offline, reconnecting, degraded, and stale are first-class
   UI states. Cached data is never silently presented as current.
5. **Per-host isolation.** One slow or unreachable machine cannot block initial paint,
   local navigation, or healthy machines.
6. **No generic remote execution.** Clients select typed SASE operations. They cannot
   submit arbitrary shell, path, environment, or working-directory input.
7. **Version tolerance.** Machines may be upgraded independently. A handshake and
   capability set gate behavior, and additive JSON fields do not break older clients.
8. **Recoverability without the gateway.** Stopping or uninstalling the gateway leaves
   the existing source stores valid and local CLI/TUI behavior functional.

The failure cases that drive the design are:

- direct Tailscale path becomes a DERP or peer-relay path, increasing latency;
- host sleeps, changes network, reboots, or restarts only the gateway;
- ACE disconnects after a command is accepted but before it sees the response;
- events are delayed, duplicated, missed, or fall outside the replay window;
- a filesystem notification is missed;
- two ACE instances operate on the same agent concurrently;
- a display name or OS PID is reused;
- controller and host run different SASE releases;
- a credential is stolen or a Tailscale ACL/grant is too broad;
- a malformed or oversized response attempts to exhaust the TUI.

## 3. Transport and topology evaluation

### 3.1 Decision matrix

Scores are relative to a small personal fleet and the current codebase: 5 is best.

| Option | Reliability primitives | Existing-code fit | Operational simplicity | Evolvability | Overall |
|---|---:|---:|---:|---:|---:|
| HTTPS/JSON + SSE, direct per host | 4 | 5 | 5 | 4 | **18** |
| gRPC, direct per host | 5 | 2 | 3 | 5 | **15** |
| ZeroMQ, direct or brokered | 2 | 1 | 2 | 3 | **8** |
| NATS + JetStream | 5 | 1 | 1 | 5 | **12** |
| SSH command invocation | 2 | 2 | 3 | 1 | **8** |

The reliability score reflects supplied transport primitives, not correctness of the
overall operation. No transport eliminates the need for stable resource identity,
durable idempotency, state preconditions, audit, and resynchronization.

### 3.2 HTTPS/JSON plus SSE

This is the best fit because SASE already has the server and event mechanics. HTTP gives
clear request boundaries, ordinary observability, structured status codes, independent
deadlines, and easy testing. SSE is sufficient because the long-lived traffic is
primarily host-to-controller state invalidation; commands remain normal request/response
operations. Axum directly supports keepalive-enabled SSE streams
([Axum SSE documentation](https://docs.rs/axum/latest/axum/response/sse/)).

HTTP does not make mutations automatically retry-safe. HTTP semantics allow automatic
retry of idempotent requests, while a POST is not inherently idempotent
([RFC 9110, section 9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)).
The gateway therefore needs application-level idempotency. The emerging
`Idempotency-Key` specification describes the relevant model—unique keys, payload
fingerprints, and cached outcomes—but remains an IETF Internet-Draft rather than a
final standard ([IETF Idempotency-Key draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)).
SASE can adopt those semantics under its own versioned API whether or not the header is
eventually standardized.

### 3.3 gRPC

gRPC is the strongest runner-up. It supplies generated clients from Protobuf schemas,
unary and streaming RPCs, ordered messages within a stream, deadlines, retry policies,
health checking, and good schema-evolution rules
([gRPC core concepts](https://grpc.io/docs/what-is-grpc/core-concepts/),
[deadlines](https://grpc.io/docs/guides/deadlines/),
[retry](https://grpc.io/docs/guides/retry/),
[health checking](https://grpc.io/docs/guides/health-checking/), and
[ProtoJSON evolution guidance](https://protobuf.dev/programming-guides/proto3/)).

It is not the best next step here. SASE would add Tonic, Protobuf generation, and a
Python gRPC client beside an existing Axum JSON/SSE service. gRPC retries still require
the application to know which operations are safe, streams still need snapshot/replay
semantics after reconnection, and ownership/stale-state rules remain unchanged. gRPC
would be a reasonable reconsideration if telemetry volume becomes high, bidirectional
streaming becomes central, or non-Python clients make generated contracts substantially
more valuable.

### 3.4 ZeroMQ

ZeroMQ is fast, asynchronous, and brokerless, with useful request/reply and pub/sub
patterns ([ZeroMQ overview](https://zeromq.org/get-started/)). Those strengths do not
target SASE's bottleneck. The official ZeroMQ Guide's reliability chapters show that
robust request/reply requires explicit polling, timeouts, retries, heartbeats,
re-registration, sequence handling, and deduplication; classic pub/sub can lose messages
when subscribers disconnect, start late, or cannot keep up
([reliable request/reply patterns](https://zguide.zeromq.org/docs/chapter4/) and
[reliable pub/sub patterns](https://zguide.zeromq.org/docs/chapter5/)).

Using ZeroMQ would mean designing and maintaining nearly everything the existing HTTP
gateway already provides: framing, versioned schemas, authentication, authorization,
replay, request correlation, idempotency, structured errors, health endpoints, and
debug tooling. Its latency advantage is immaterial for dozens or hundreds of small
state updates. It should not be selected.

### 3.5 NATS and JetStream

Core NATS provides lightweight pub/sub and request/reply but is best-effort, at-most-once
delivery: disconnected subscribers miss messages. JetStream adds persistence, replay,
replication, and stronger storage guarantees
([Core NATS](https://docs.nats.io/nats-concepts/core-nats) and
[JetStream](https://docs.nats.io/nats-concepts/jetstream)).

That is useful for a much larger system with durable offline work queues, many
publishers/subscribers, or multi-controller fan-out. For a handful of known Tailscale
machines it introduces a broker, server configuration, credential rotation, storage,
upgrades, and either a single infrastructure dependency or a clustered service. It
also does not remove the need for per-host process ownership and mutation deduplication.
Do not add it now; define a clean gateway client boundary so a brokered topology remains
possible later.

### 3.6 SSH

SSH already solves machine authentication and can launch a remote CLI command, making
it useful as an operator's diagnostic or emergency fallback. It is a poor primary API:
each call has process-start overhead, output parsing becomes a compatibility contract,
continuous state needs another channel, cancellation is subtle, and idempotency or
replay would still be custom. SASE should expose an explicit health/debug command that
operators can invoke over SSH, but ACE should not use SSH as its control transport.

## 4. Recommended architecture

### 4.1 Direct, federated host gateways

Use a star topology with no required coordinator:

```text
                         +--> host gateway on Mac mini --> local SASE stores/processes
ACE on MacBook ----------+--> host gateway on server   --> local SASE stores/processes
                         +--> host gateway on laptop   --> local SASE stores/processes

Each host --------------------> Git agents sidecar (durable history, asynchronous)
```

ACE maintains an independent connection state, snapshot, cursor, retry schedule, and
health summary for each host. A machine failure affects only that machine. Multiple ACE
controllers may connect; the host serializes and validates operations against its own
authoritative state.

Avoid calling machines “SASE nodes” in the API and UI because “Sase Node” already means
a row in the Agents tab. Use `host`, `machine`, and `host_id` for the fleet concept.

### 4.2 Host configuration and discovery

Start with explicit configuration, not multicast or automatic LAN discovery. The user
already knows which machines are trusted, and explicit membership avoids accidental
control of a newly visible device.

```yaml
hosts:
  local:
    kind: local
    enabled: true
  athena:
    kind: remote
    url: https://athena.example-tailnet.ts.net
    token_file: ~/.config/sase/credentials/athena-controller.token
    expected_host_id: 818565ad-8e4f-4b6e-88e4-f29e7ac8ea8d
```

Prefer the full MagicDNS name over a Tailscale IP. MagicDNS registers machine names and
provides tailnet-qualified names, although a machine rename changes its DNS name
([Tailscale MagicDNS](https://tailscale.com/docs/features/magicdns)). Pin a
gateway-generated stable `host_id` after first trusted enrollment so DNS reassignment or
misconfiguration cannot silently substitute a different host. Store tokens outside the
main YAML with restrictive permissions and support environment/keychain providers
later.

Discovery can be layered on after the protocol is stable: a read-only Tailscale device
inventory may suggest hosts, but enrollment should always require an explicit trust
action and host-identity confirmation.

### 4.3 Tailscale exposure and authorization

Bind the gateway only to `127.0.0.1` and publish it through persistent Tailscale Serve:

```sh
tailscale serve --bg 7629
```

Serve provides tailnet-only HTTPS, automatically managed certificates, and reverse
proxying to the loopback service; background Serve configuration survives process and
machine restarts ([Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
and [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)). Never enable
Funnel for the control API. If SASE app capabilities are enabled, also pass
`--accept-app-caps=<controlled-domain>/cap/sase-agents`; Tailscale requires custom
capability names to use a domain the application owner controls.

Use layered authorization:

1. A tailnet grant permits only intended controller users/devices to TCP 443 on hosts.
2. A Tailscale application capability distinguishes read, operate, and admin scopes
   where practical. Serve can forward application capabilities to the backend
   ([Tailscale application capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities)).
3. The SASE gateway requires a per-controller bearer credential, stored hashed, with
   explicit scopes, expiration/rotation, and revocation.
4. The gateway checks the expected Serve identity/capability context and its own token
   scopes, then audits both identities.

Tailscale warns that identity headers must be protected from spoofing by ensuring the
backend is reachable only through Serve; tagged source devices also do not receive the
same user identity headers. This is why loopback binding and gateway credentials remain
important even inside a tailnet ([Serve identity-header guidance](https://tailscale.com/docs/features/tailscale-serve)).

Tailscale attempts direct UDP paths for low latency and falls back to peer relays or
DERP relays while preserving end-to-end WireGuard encryption. Relay paths can be
slower, so the client must tolerate latency without treating it as failure
([Tailscale connection types](https://tailscale.com/docs/reference/connection-types)).

### 4.4 Versioned host protocol

Create a distinct fleet contract, for example `/api/host/v1`, while sharing the mobile
gateway's server infrastructure. Do not silently expand the mobile DTO until it becomes
an accidental all-purpose API.

Minimum read endpoints:

- `GET /hello`: stable `host_id`, display name, boot/gateway epoch, SASE build, minimum
  and maximum protocol versions, clock metadata, and capability set.
- `GET /agents`: bounded/paginated summaries plus `snapshot_id`, `event_cursor`, facets,
  and next-page cursor.
- `GET /agents/{run_id}`: lazy, wire-safe detail.
- `GET /agents/{run_id}/logs?cursor=...`: bounded log chunks or stream with byte/event
  offsets and truncation markers.
- `GET /agents/{run_id}/artifacts/{artifact_id}`: allowlisted resources addressed by
  opaque IDs, never client-supplied filesystem paths.
- `GET /events`: SSE stream with epoch and monotonic sequence ID, heartbeat, bounded
  replay, and explicit `resync_required`.
- `GET /operations/{operation_id}`: status and durable result for an accepted mutation.

Minimum mutation endpoints should be typed: launch, kill, retry, resume/revive, answer
question, approve/reject gate, and any other ACE action that has an established local
lifecycle facade. There must be no `exec`, generic command, arbitrary cwd, arbitrary
path, or arbitrary environment endpoint.

Use Rust-owned Serde wire types and contract snapshots in `sase-core`. JSON readers
should tolerate unknown additive fields. The hello/capability exchange gates optional
fields and operations; breaking changes get a new route version. This supports rolling
upgrades across machines.

Put the reusable host client in `sase-core` as well: use Rust's existing Axum/Reqwest
ecosystem for the server and client, and expose snapshots, operation results, and event
invalidations through a thin `sase_core_rs` adapter. Retry classification, epochs,
cursors, idempotency keys, schema validation, and host health are shared backend
behavior that a future CLI, web app, or editor integration will also need. Python ACE
should own only provider composition, cancellation tied to TUI lifetime, and
presentation state. This avoids adding a separate Python networking stack as the
protocol implementation of record.

### 4.5 Identity and remote-safe models

Give every agent execution an immutable `run_id` that survives display-name changes and
cannot be confused with an OS PID. A globally unique row handle should incorporate the
host and owning namespace, for example:

```text
agent:<host_id>:<username>:<project_id>:<run_id>
```

The wire summary should contain displayable and filterable state, timestamps, project,
provider/model, host label, lifecycle status, revision, capabilities, and safe progress
metadata. It should not expose absolute paths or treat a PID as an actionable identity.

Refactor ACE into three related contracts:

- `AgentsDataProvider`: snapshots, pages, queries, facets, and event application;
- `AgentDetailsProvider`: detail, log, chat, and artifact retrieval by opaque resource;
- `AgentOperationsProvider`: typed actions routed to the row's owning host.

An aggregate provider composes the existing local direct provider with one remote
provider per host. It preserves current local startup behavior while remote support
matures. Once the gateway is proven, local ACE may optionally use the same host
contract, but the fleet project should not require a full local-daemon migration.

### 4.6 Snapshot and event correctness

Use snapshot-plus-invalidation, not event sourcing, for the first implementation:

1. ACE fetches a complete bounded snapshot that includes the event cursor corresponding
   to that snapshot.
2. ACE connects to SSE from that cursor.
3. An event identifies affected resources and prompts a coalesced incremental or full
   refresh. Duplicate events are harmless.
4. A new gateway epoch, missing cursor, replay overflow, incompatible schema, or
   `resync_required` discards remote derived state and fetches a new snapshot.

Typed deltas may be added later, but invalidation hints minimize the amount of
state-machine logic shared between client and server. Snapshot state remains truth.

The host observer must cover changes initiated outside the gateway. Combine filesystem
notifications for responsiveness with periodic fingerprint/reconciliation scans for
correctness. Watcher events can be lost or coalesced; a scan must eventually discover a
missed update. The gateway should emit only after it can serve the corresponding new
snapshot/revision.

Do not persist the whole agent projection merely to support replay. A bounded in-memory
event ring plus authoritative source-store snapshots is sufficient. Persist only the
small amount of state whose durability is required for safe commands and audit.

### 4.7 Reliable mutations

Every mutating request carries:

- a globally unique idempotency key generated by ACE;
- a canonical request fingerprint;
- target `host_id` and immutable `run_id` where applicable;
- the last observed resource revision or an explicit force/reconfirm flag;
- a request ID for tracing and a declared client deadline.

Before executing, the host writes an entry to a durable, bounded command journal with
the key, fingerprint, caller, target, and status. Reusing a key with the same fingerprint
returns the original operation/result. Reusing it with a different fingerprint is a
conflict. A long operation returns `202 Accepted` and an `operation_id`; the caller can
poll or consume its event. Terminal outcomes are retained long enough to cover realistic
reconnect and retry windows, then compacted.

The state revision prevents a command based on stale UI state from silently affecting a
new execution. A kill request must resolve `run_id` to the current locally recorded
process identity and verify that identity immediately before signaling. Name reuse and
PID reuse then yield a conflict/not-found response instead of killing the wrong process.

Launch acknowledgement should occur only after the existing durable launch admission
or reservation has been recorded. If ACE loses the response, it retries with the same
key and receives the existing operation. Do not queue launch or kill indefinitely while
a host is offline: a command unexpectedly executing hours later is worse than a visible
failure. Offline requests fail locally; an ambiguous in-flight request is resolved by
querying the operation with the same key after reconnection.

### 4.8 Latency, backpressure, and UX

Connect to hosts concurrently and isolate all network I/O from Textual's event loop.
Use explicit per-call deadlines, capped exponential backoff with full jitter, bounded
response sizes, and a circuit state per host. gRPC's documentation makes the same
general reliability point: without explicit deadlines a client may wait indefinitely
([gRPC deadlines](https://grpc.io/docs/guides/deadlines/)). It applies equally to HTTP.

Suggested starting behavior:

- Render local agents immediately; merge each remote snapshot as it arrives.
- Use a 2–3 second connect timeout and about 5 seconds for normal metadata requests;
  actions receive explicit, operation-specific deadlines.
- Send SSE heartbeats around every 20–30 seconds and cap reconnect backoff around
  30 seconds, with jitter.
- Coalesce bursts into at most one refresh per host over a short window.
- Fetch summaries first, details on selection, and logs in bounded chunks.
- Retain the last sanitized snapshot only for UX continuity; label every cached row
  `STALE` with its age and disable mutations until a fresh revision is obtained.
- Show host as a column, group, and filter, with host-level states such as `online`,
  `reconnecting`, `unauthorized`, `incompatible`, and `offline`.

Initial service objectives should be measured, not promised as protocol guarantees:
local initial paint should not regress; a healthy direct Tailscale host should normally
appear within one second; event-driven state should normally appear within five
seconds; and an offline host should add no perceptible main-loop stall. Relay-connected
hosts may be slower without being unhealthy.

### 4.9 Supervision, observability, and security hardening

Run the gateway as a user service under launchd/systemd with restart-on-failure, resource
limits, and a stable local state directory. Tailscale Serve remains the TLS/network
front end. Expose a cheap health endpoint and include build/protocol data in `/hello`.

Audit mutating operations with timestamp, controller identity, Tailscale identity or
capability context, source address, request and operation IDs, action, target, state
revision, and outcome. Do not log bearer tokens, prompts, full chat bodies, or arbitrary
environment values. Add token rotation/revocation, request and response size limits,
rate limits, bounded concurrency, strict content types, safe error bodies, and redaction
tests.

Because all WireGuard peers in a tailnet are not automatically all authorized peers,
ship an example least-privilege grant policy. Treat the gateway token as necessary
defense in depth, not a replacement for the tailnet policy.

## 5. Implementation sequence

### Phase 0: contract and fault harness

- Define host identity, wire summaries/details, revisions, capabilities, error model,
  snapshot/cursor semantics, and operation/idempotency semantics in `sase-core`.
- Add schema/contract snapshots and a fake host server that can delay, disconnect,
  duplicate events, overflow replay, restart epochs, and return older capabilities.
- Add a Rust host-client proof and exercise it through a thin Python binding before
  reshaping ACE models.

### Phase 1: read-only fleet view

- Add explicit host configuration and enrollment.
- Extend the Rust gateway with `/api/host/v1/hello`, paginated summaries, and SSE.
- Add the host observer with filesystem hints plus periodic reconciliation.
- Compose local and remote providers in ACE; add machine column/filter and stale/error
  states.
- Keep all remote mutations disabled.

This phase proves the hardest read-path properties without putting processes at risk.

### Phase 2: details, logs, and artifacts

- Introduce opaque resource endpoints and the `AgentDetailsProvider`.
- Remove remote paths/PIDs from presentation action paths.
- Test large logs, truncation, cancellation, slow readers, and malformed payloads.

### Phase 3: safe mutations

- Add the durable command journal and operation resource.
- Start with kill and launch, guarded by immutable run identity, revisions, scopes,
  idempotency, and audit.
- Add retry/resume and interactive actions only through existing lifecycle facades.
- Require fresh state or explicit reconfirmation for destructive actions.

### Phase 4: parity and optional convergence

- Close remaining ACE action-capability gaps.
- Consider routing local ACE through the same contract only after latency and failure
  behavior are proven; retain a direct recovery path.
- Re-evaluate gRPC or a durable bus only against measured needs such as sustained
  high-volume streams, offline queued workflows, or a fleet large enough to make
  controller-to-every-host connections impractical.

## 6. Required fault-injection and acceptance tests

The feature is not robust until automated tests demonstrate all of the following:

- ACE loses the launch response, retries, and exactly one agent exists.
- ACE disconnects during kill, then obtains the same terminal operation result.
- A stale kill targeting a reused name/PID cannot affect a newer run.
- Gateway restart changes the epoch and forces a correct full resync.
- Event duplicates, reordering, replay overflow, and a missed watcher notification all
  converge to the authoritative snapshot.
- One host hangs or remains offline while local and other remote hosts stay responsive.
- Host sleep/wake and transitions between direct and relayed Tailscale paths recover
  without manual TUI restart.
- Two controllers issue compatible and conflicting actions; revisions and journal
  records yield deterministic results.
- Older and newer client/server combinations negotiate capabilities and reject only
  unsupported actions.
- Revoked SASE tokens and denied tailnet grants stop access; spoofed identity headers
  sent directly to the loopback service are not remotely reachable or trusted.
- Oversized JSON, log streams, malformed events, reconnect storms, and slow consumers
  remain bounded.
- Turning the gateway off leaves local CLI/ACE and source stores correct.
- Sidecar history never overrides fresher gateway state and never represents an
  imported remote process as live.

## 7. Sources

Primary external references:

- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve),
  [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve),
  [MagicDNS](https://tailscale.com/docs/features/magicdns),
  [connection types](https://tailscale.com/docs/reference/connection-types), and
  [application capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities)
- [WHATWG Server-Sent Events](https://html.spec.whatwg.org/dev/server-sent-events.html)
  and [Axum SSE](https://docs.rs/axum/latest/axum/response/sse/)
- [RFC 9110 HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html) and the
  [IETF Idempotency-Key Internet-Draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)
- [gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/),
  [deadlines](https://grpc.io/docs/guides/deadlines/),
  [retry](https://grpc.io/docs/guides/retry/), and
  [health checking](https://grpc.io/docs/guides/health-checking/)
- [ZeroMQ overview](https://zeromq.org/get-started/),
  [reliable request/reply](https://zguide.zeromq.org/docs/chapter4/), and
  [reliable pub/sub](https://zguide.zeromq.org/docs/chapter5/)
- [Core NATS](https://docs.nats.io/nats-concepts/core-nats) and
  [JetStream](https://docs.nats.io/nats-concepts/jetstream)

Repository evidence:

- `docs/architecture.md`
- `docs/agents_sidecar.md`
- `docs/mobile_gateway.md`
- `docs/integrations.md`
- `src/sase/ace/tui/data_providers/`
- `src/sase/integrations/_mobile_agent_summary.py`
- `sase-core/crates/sase_gateway/`
- Revert commit `5a65fa4fc`

## 8. Recommended solution

Implement a **narrow federated host gateway over Tailscale Serve, using versioned
HTTPS/JSON commands and SSE snapshot invalidations**. Extend the existing Rust
`sase_gateway`; do not introduce ZeroMQ, NATS, or a revived full projection daemon.
Configure trusted hosts explicitly by MagicDNS URL and pinned `host_id`. Bind each
gateway to loopback, apply least-privilege Tailscale grants/application capabilities,
and require scoped per-controller SASE tokens.

Keep each host authoritative for its own agents. In ACE, compose the current local
provider with independent remote providers, route every action by an opaque
host-qualified run ID, and present stale/offline state explicitly. Keep the Git agents
sidecar as the durable historical plane only.

Ship read-only fleet visibility first. Enable launch, kill, retry, and other mutations
only after the host has a durable idempotency journal, resource revisions, safe
process-identity checks, operation-status recovery, complete passive-change observation,
and the fault-injection coverage listed above. This path reuses the strongest pieces
already in SASE, minimizes new operational machinery, fails independently per machine,
and provides the clearest route to reliable local-like control across a Tailscale fleet.
