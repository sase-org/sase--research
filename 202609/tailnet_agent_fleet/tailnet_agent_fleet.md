---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Managing SASE Agents Across A Tailscale Fleet From One ACE TUI

## Research question

How should SASE let one `sase ace` TUI — on the MacBook — view, launch, kill, and
otherwise manage sase agents running on every machine in the user's Tailscale tailnet,
with the same fidelity as local agents? Which external framework, if any (ZeroMQ was the
user's starting suggestion), should carry that traffic?

## Provenance

Consolidated from two independent researcher reports (`tailnet_agent_fleet__a.md`,
`tailnet_agent_fleet__b.md`) plus lead-researcher verification. Both reports examined
`sase` @ `4c1c7b24e` and `sase-core` @ `51df9061` and independently reached the same
core recommendation. Every repo claim relied on below was re-verified against the
checkouts during consolidation; the live-tailnet latency measurements come from report B
(measured 2026-09-03) and were not re-run. The two reports' disagreements — fleet
naming, host identity, and where the client code lives — are resolved explicitly in §5.

## Executive summary

**Recommendation: no new messaging framework — not ZeroMQ, not NATS, not gRPC.** Extend
the existing Rust `sase_gateway` crate into a supervised per-machine host daemon that
serves a versioned HTTPS/JSON API plus an SSE change feed, exposed tailnet-only via
loopback bind + `tailscale serve`. Make agent reads resident in Rust (no Python fork per
request), give the SSE stream a real change feed with a resumable cursor, and consume it
all through the daemon-ready provider seam that already exists in the ACE Agents tab.
Ship read-only fleet visibility first; enable remote mutations only after idempotency,
server-side identity resolution, and fault-injection tests are in place.

Three findings drive this:

1. **SASE has already built most of it.** `sase-core/crates/sase_gateway` is an
   11,229-line axum daemon with agent list/launch/kill/retry routes, SSE, device
   pairing, bearer tokens, an audit log, and a committed API contract. The ACE Agents
   tab has a provider seam (`used_daemon`, `fallback_reason`, `resync_required`,
   `AgentsViewport`) designed for exactly a remote, paginated, event-driven source —
   currently hard-disabled. Machine-qualified agent identity (`<machine>.<name>`) and a
   durable cross-machine git plane (agents_sync) already work.
2. **The bottleneck is the process model, not the network.** `tailscale ping apollo` is
   32 ms direct P2P, but the gateway forks a fresh Python interpreter per request
   (`host_bridge.rs` runs `sase mobile agent-bridge <op>`), costing ~3.8 s per list call
   on apollo — roughly 120× the round trip. SSH fan-out fails for the same reason
   (5.5–6.8 s per call; multiplexing saves only the transport share). Any framework
   choice is downstream of making reads resident.
3. **Tailscale subtracts the hard transport problems.** WireGuard encryption, per-node
   identity, ACLs, MagicDNS naming, and NAT traversal come free. That removes ZeroMQ's
   and NATS's main structural advantages over plain HTTP, leaving only "what shape are
   the messages" — and the answer is the shape they already are.

The data scale confirms HTTP+SSE is sufficient: a full running-agent snapshot is
13–27 KB per machine, so per-machine full-snapshot reconciliation every minute is
affordable and deltas are a latency optimization, not a bandwidth necessity.

## 1. What exists today (verified)

Five mechanisms already exist in the tree. Any plan that ignores them builds a sixth.

### 1.1 The mobile gateway: an HTTP control plane, already written

`crates/sase_gateway` (11,229 lines) exposes `GET /api/v1/agents`,
`POST /api/v1/agents/launch`, `POST /api/v1/agents/:name/kill`, `.../retry`, and SSE at
`GET /api/v1/events`, behind device pairing (`/api/v1/session/pair/start|finish`),
bearer tokens, and a JSONL audit log. It has a committed API contract snapshot
(`contract.rs`, `--contract-out`) and a wire schema version. Its bind-policy error
already anticipates this feature: pass `--allow-non-loopback` "only for explicit LAN or
tailnet exposure" (`server.rs`). `docs/mobile_mvp_runbook.md` documents the right
posture: loopback bind + `tailscale serve`, restricted ACLs, no Funnel.

Three gaps make it unusable as-is, all fixable:

1. **Fork-per-request bridge.** `CommandAgentHostBridge::invoke` (`host_bridge.rs:186`)
   spawns `sase mobile agent-bridge <operation>` and pipes JSON over stdio. Measured:
   ~1.0 s locally on the M1, ~3.8 s on apollo — dominated by Python interpreter/import
   startup, not scanning (the index has only 43 live rows).
2. **The SSE stream is not a change feed.** After replaying buffered events, the stream
   loop emits only heartbeats. `publish_agents_changed` is called *only* from the
   gateway's own mutation handlers (`routes.rs:854, 889, 925, 967` — launch,
   launch_image, kill, retry). An agent launched by a local TUI, a chop, or a finalizer
   emits nothing; a MacBook watching apollo this way would miss nearly every real
   change. The `ResyncRequired` event variant already exists in `wire.rs`.
3. **Not shipped or operable.** The binary resolves from `PATH` or a sibling dev build
   only; `sase mobile gateway start` is foreground-only with no status/stop.

`daemon.rs` is a further head start: `DaemonConfig` already models a `host_identity`, a
run root at `~/.sase/run/<host>/`, and a `sase-daemon.sock` path — but nothing ever
binds the socket (no `UnixListener` exists in the crate). It is a placeholder waiting
for exactly this feature.

### 1.2 The ACE provider seam: the insertion point

`src/sase/ace/tui/data_providers/_types.py` defines `AgentsProviderSnapshot` with
`used_daemon`, `fallback_reason`, `fallback_message`, and `snapshot_id`;
`AgentEventApplyResult` with `resync_required`/`resync_reason`; and `AgentsViewport`
with a bounded read window. The factory returns only `DirectAgentsDataProvider`
(`_factory.py`) and `agents_daemon_reads_enabled()` is a hard `False` (`_settings.py`).
This seam survived the sase-3e daemon revert precisely so a remote/daemon provider
could be added later. Using it costs no new abstraction.

The gap is width: ACE's `_agent_state.py` row model has 197 annotated fields and
`src/sase/ace/tui/actions/agents/` holds ~160 action modules, while the mobile wire
summary is a 15-field projection. Full "manage the same way" parity is a surface
problem, not a wire problem — and it decomposes cleanly (§6.6).

### 1.3 Machine identity: already solved for agents

`sase_core::machine_hood` (`machine_hood.rs`) validates machine names (`^[a-z_]+$`,
line 25) and qualifies agent names as `<machine>.<name>` idempotently (line 49).
`~/.sase/machine_name` is set on both live machines (`kellys_mbp`, `apollo`), and
agents_sync v2 records already carry `owner`/`local_name`/`global_name`. Duplicate
agent names across machines are structurally impossible.

### 1.4 The durable git plane

`sase/agents_sync/` publishes owner-qualified hoods, runs, prompts, commits, and
content-addressed file references (path + digest + size) into a git sidecar on a
10-minute cadence (`default_config.yml:271`). It is slow but partition-proof: `athena`
has been offline for three days and its agent history is still readable today. That
property must not regress.

### 1.5 The reverted daemon is a warning, not a precedent

Commit `5a65fa4fc` (`feat: revert sase-3e daemon rollout`) removed a large
Unix-RPC/SQLite-projection daemon that tried to own scheduling, watching, and provider
hosting all at once. The fleet feature needs a narrow supervised gateway and a small
durable command journal — not a revived all-purpose daemon, and not a migration that
makes *local* ACE depend on a daemon before remote access works.

## 2. Measurements (report B, live tailnet, 2026-09-03)

| Operation | Result |
| --- | --- |
| `tailscale ping apollo` | **32 ms**, direct P2P (public ip:port, no DERP) |
| `sase agent list --json` local (M1) | 0.68 s, 12.9 KB (9 agents) |
| `sase agent list --json` on apollo | 5.5–5.9 s, 27.4 KB (19 agents) |
| `sase mobile agent-bridge list-agents` on apollo | **~3.8–4.0 s** |
| `ssh apollo sase agent list --json` cold / warm (ControlMaster) | 6.77 s / 5.51 s |
| Local artifact index | 1.9 MB SQLite, 43 live rows |

Conclusions: interpreter startup dominates (~4.8 s of the warm SSH call is the remote
Python side); SSH multiplexing cannot save the design; a resident Rust reader is worth
~100×; and at 13–27 KB per machine, periodic full-snapshot reconciliation is free.

Also load-bearing: ICMP jitter on MacBook Wi-Fi was ±100 ms around the 32 ms baseline —
so the client needs explicit deadlines, not assumptions about stable RTT. And ACE's
filesystem watcher uses Linux inotify via ctypes and "silently declines to start" on
macOS (`src/sase/ace/tui/util/fs_watcher.py:9-11`) — the MacBook TUI is *already* in
the polling regime today, so remote sources add no new failure mode on the primary
host, while Linux hosts can drive a genuine inotify-based change feed.

## 3. Transport evaluation

### 3.1 Scorecard

| | Reuses gateway | New native dep | Change feed | Auth/identity | Broker-free | Upstream health |
| --- | --- | --- | --- | --- | --- | --- |
| **HTTP+SSE (extend gateway)** | ✅ full | none | needs work (§6.2) | ✅ exists + Tailscale | ✅ | ✅ axum/tokio |
| ZeroMQ | ❌ parallel stack | pyzmq/libzmq | build it | build CURVE (3rd auth model) | ✅ | ⚠️ 4.3.5, Oct 2023 |
| NATS (+ leaf nodes) | ❌ parallel stack | client libs | ✅ native | ✅ native | ❌ broker | ✅ |
| gRPC | ❌ rewrite wire | grpcio/tonic | ✅ streams | build it | ✅ | ✅ |
| SSH fan-out | n/a | none | ❌ poll only | ✅ keys | ✅ | ✅ |
| git sidecar alone | n/a | none | ❌ 10 min | ✅ | ✅ | ✅ |

### 3.2 Why not ZeroMQ

Both researchers independently rejected it, for converging reasons:

- **It solves the wrong problem.** The measured bottleneck is a ~3.8 s Python fork, not
  framing or latency; ZeroMQ would move slow responses very efficiently. Its advantages
  target high-frequency in-datacenter messaging, not 3–5 personal machines exchanging
  ~20 KB/min.
- **You must build the application layer yourself.** The official ZeroMQ Guide's
  reliability chapters show that robust request/reply needs explicit timeouts, retries,
  heartbeats, and deduplication, and plain pub/sub loses messages for late or slow
  subscribers. SASE would reimplement framing, versioned schemas, auth, replay,
  idempotency, structured errors, health, and observability — everything the HTTP
  gateway already has (contract snapshot, schema version, audit log included).
- **A third auth model.** ZeroMQ security is CURVE keypairs; Tailscale already provides
  WireGuard encryption, node identity, ACLs, and MagicDNS, and the gateway already has
  pairing + bearer tokens.
- **A new C dependency in a deliberately minimal stack.** The Python project has 13
  runtime dependencies and no HTTP client at all (stdlib `urllib`); the Rust workspace
  already has axum/tokio/reqwest. `pyzmq` bundles libzmq as a native extension.
- **Upstream momentum is a real risk for a control plane you trust with `kill`.**
  libzmq's last stable release is 4.3.5 (October 2023); a July 2026 zeromq-dev thread
  asked whether the project is still maintained, with replies framing it as mature /
  maintenance-mode (verified during consolidation). Survivable for a script; awkward
  for new load-bearing infrastructure.

### 3.3 Why not NATS or gRPC (now)

**NATS** is the most capable alternative — single static binary, native request-reply
and pub/sub, leaf nodes built for intermittently-connected edges — but it reintroduces
a single point of failure the tailnet doesn't have (a broker must live somewhere; on a
sleeping/roaming MacBook or on one host whose outage blinds the rest), and avoiding
that means running a NATS server on every machine to replace an HTTP client the Rust
side already has. Right answer at a different scale (§8).

**gRPC** adds tonic + protobuf codegen + a large Python native wheel beside a working
JSON contract, while the hard problems (idempotency, snapshots after reconnect, stale
state) remain application-level either way. Near-zero benefit at 20 KB/min.

**SSH fan-out** is the zero-infrastructure baseline and fails on measurement (5.5–6.8 s
per call, no change feed, no down-vs-slow distinction). Keep it only as the escape
hatch for genuinely local operations, e.g. `ssh -t apollo tmux attach`.

## 4. Tailscale as the security layer

The tailnet supplies encryption, identity, ACLs, stable MagicDNS names
(`apollo.<tailnet>.ts.net`), and NAT traversal. The design inherits the mobile
runbook's posture:

- Gateway binds **loopback only**; `tailscale serve --bg <port>` publishes it
  tailnet-only with managed TLS, surviving restarts. Never Funnel; never
  `--allow-non-loopback`.
- **Layered authorization**, not tailnet-membership-only: (1) a least-privilege
  Tailscale grant restricting which devices/users reach the port; (2) optionally
  Tailscale app capabilities for read/operate/admin scopes; (3) the gateway's own
  scoped, hashed, revocable per-controller bearer token as defense in depth.
- Identity headers (`Tailscale-User-Login`) are trustworthy only because the backend is
  reachable solely through Serve on loopback — anything that can hit the port directly
  could forge them. This is why the loopback rule is load-bearing.
- Tailscale may fall back from direct P2P to DERP relays; relay paths are slower but
  healthy. Deadlines and staleness UX must tolerate this without declaring failure.

## 5. Disagreements between the reports, resolved

1. **Fleet naming.** Report B proposed a `sase node` daemon and "nodes" for machines;
   report A warned the term collides. **A is right**: the project glossary already
   defines *Sase Node* as "one row of the Agents tab's agent tree" (verified via
   `sase memory read glossary:node`). Use **host** / **machine** for the fleet concept
   (e.g. `sase host {start,status,stop,list}` or `sase fleet …`), never "node".
2. **Host identity.** Report B said "do not invent a node ID — the node is the machine
   name"; report A wanted a pinned gateway-generated `host_id`. **Merge them**: the
   machine name (`~/.sase/machine_name` + `machine_hood` qualification) stays the one
   identity for agents and display — no new ID space. But enrollment should pin a
   stable gateway identity (returned by `/hello` and checked on connect) so a MagicDNS
   rename or IP reassignment can never silently substitute a different host as the
   target of a `kill`. That is endpoint authentication, not a second naming scheme.
3. **Where the client lives.** Report A says the host client belongs in `sase-core`
   behind the `sase_core_rs` binding; report B implied Python (noting the project has
   no HTTP client). **A is right, and it is project policy**: the
   `rust_core_backend_boundary` core memory requires shared backend behavior — retry
   classification, cursors, idempotency keys, schema validation, host health — to live
   in the Rust core, and the `sase-core-rs` binding already ships as a dependency.
   Python ACE owns only provider composition, TUI-lifetime cancellation, and
   presentation. This also keeps the Python dependency count at 13.
4. **API surface.** Report A wants a distinct versioned fleet contract rather than
   growing the mobile DTO; report B's own measurement (15 wire fields vs 197 row
   fields) supports that. **Adopt A's split**: share the gateway's server, auth, audit,
   and event infrastructure, but give the fleet API its own versioned routes and richer
   wire types so the mobile app's deliberately shallow contract stays stable.
5. **Mutations through the fork bridge.** Report B allows keeping the subprocess bridge
   for mutations initially (rare, user-initiated; a 4 s kill is survivable, a 4 s list
   is not); report A gates all mutations on a durable idempotency journal. **Both**:
   the bridge may stay for the mutation phase's first cut, but the phase itself does
   not ship until A's safety requirements (§6.4) and fault tests (§7.1) pass.

## 6. Recommended architecture

### 6.1 Shape: federated star, no broker, two planes

```text
  MacBook (kellys_mbp) ── sase ace TUI
      │
      │  Federated agents provider (composes per-host providers behind the seam)
      │    ├── DirectAgentsDataProvider          (local, unchanged)
      │    └── Rust host client × N  (sase-core, via sase_core_rs)
      │          · GET  snapshot (paginated, snapshot_id + cursor)
      │          · GET  SSE change feed (Last-Event-ID resume)
      │          · POST typed, name-addressed mutations (idempotency keys)
      │
      ├─── WireGuard (Tailscale), MagicDNS names, loopback + tailscale serve
      │
      ├── apollo  ── sase host daemon ── resident Rust reader → agent_scan/SQLite
      └── athena  ── (offline) ── rows served stale from cache + git sidecar plane
```

Each host is the sole authority for its own agent processes and stores. ACE keeps an
independent connection, snapshot, cursor, and circuit state per host; one slow or dead
machine never blocks first paint, local rows, or healthy hosts. Hosts are configured
explicitly (name → MagicDNS URL, token file, pinned identity) — no automatic discovery
initially, so a newly visible tailnet device is never implicitly trusted.

**Two planes, always.** The live daemon plane carries current state and mutations and
requires reachability. The git agents_sync plane carries durable history and survives
partitions. An agent must never vanish from the TUI because its machine went offline:
offline hosts degrade to stale-badged rows ("as of HH:MM") with mutations refused —
never queued blind — and never present a cached process as alive.

### 6.2 The read path: resident reads and a real change feed

The two highest-value changes in the whole plan:

1. **Serve agent reads resident** from `sase_core::agent_scan` and the SQLite index
   inside the daemon — no Python fork. The gateway crate already links `sase_core` and
   `rusqlite` is already a workspace dependency. This turns ~3.8 s into single-digit
   milliseconds and makes everything downstream viable.
2. **Make the SSE feed real.** Add a monotonic generation/sequence counter to the index
   (the `meta` table already holds versioned state, so the pattern exists), bump it on
   marker writes — inotify-driven on Linux, polling elsewhere — and emit
   `AgentsChanged { cursor }` for *all* changes, not just gateway-originated ones.
   Clients resume with `Last-Event-ID`; a cursor gap emits the already-defined
   `ResyncRequired`, which the TUI seam already models.

Use **snapshot-plus-invalidation, not event sourcing**: events are hints that trigger
coalesced refreshes; a bounded authoritative snapshot (with its cursor) is the recovery
mechanism after missed events, replay overflow, epoch change, or version mismatch. Keep
a 60-second full reconcile per host as the safety net, mirroring the local watcher's
design — at 13–27 KB per host it is free, and a missed event self-heals within a
minute. Combine filesystem hints with periodic reconciliation scans on the host side
too, since watcher events can be lost.

### 6.3 Wire model: handles, not paths; project keys, not directories

Absolute paths do not port (`/Users/bbugyi/…` vs `/home/bryan/…`); project keys
(`gh_sase-org__sase`) and machine-qualified global names (`apollo.research.5.cld`) do.
The wire summary carries displayable state, timestamps, project key, global name,
status, revision, and capability flags — never `artifacts_dir`, and never a PID as an
actionable identity. Chat, response, diff, and artifact content are fetched by opaque
handle and cached locally; agents_sync v2's `V2FileReference` (path + digest + size) is
the precedent, letting caches validate by digest without re-transfer. Remote PIDs and
paths must never reach a code path that signals or opens a local resource.

Timestamps: each response carries the host's own "now" alongside event times, so
durations are computed against the host's clock and a 30 s skew cannot show negative
runtimes.

### 6.4 Mutations: typed, name-addressed, idempotent, admitted by the target

- **Typed operations only** — launch, kill, retry, wait/resume, answer-question,
  gate-approval — routed through the existing lifecycle facades. No exec, no arbitrary
  cwd/path/env endpoint (the current gateway already refuses these; preserve that).
- **Name-addressed, server-resolved.** `kill_named_agent` (`agent/running.py:45`)
  already re-resolves by name on the owning host and returns typed `not_found` /
  `already_completed` outcomes, so a 30-second-stale row cannot kill the wrong process.
  Build on this; verify process identity immediately before signaling so PID reuse
  yields a conflict, not a wrong kill.
- **Idempotency keys + a durable command journal.** Every mutation carries a client
  key, request fingerprint, target revision, and deadline. The host journals before
  executing; retrying the same key returns the original operation's result. A duplicate
  kill is harmless; a duplicate launch burns a runner slot and real money — this is
  what makes lost-response retries safe. Long operations return an `operation_id` the
  client can poll after reconnecting.
- **Optional fencing** via the observed row revision, with explicit reconfirmation for
  destructive actions against changed state.
- **The target machine admits its own launches.** `max_running_agents` is host-wide
  (`default_config.yml:38`) and the runner-slot state is already in the JSON. The
  client proposes; the target's existing slot gate accepts or queues. Surfacing each
  host's slot state in the picker is enough for intelligent routing — a client-side
  scheduler working from a 30 s-old snapshot would oversubscribe.
- **Never queue mutations for an offline host.** A kill executing hours later is worse
  than a visible failure.

### 6.5 TUI integration: the tui_perf rules are the acceptance criteria

Network I/O runs in pump-free tasks, never in timers or message handlers. Render cached
rows on the first frame with staleness badges, reconcile in the background, and land
deltas through selective row updates rather than list rebuilds. Per-host fetches are
independent with explicit deadlines (short for lists — the next tick retries anyway;
longer for mutations), capped jittered backoff, and a per-host circuit breaker. Host
becomes a column/group/filter with explicit `online` / `reconnecting` / `stale` /
`unauthorized` / `incompatible` / `offline` states. When the daemon path fails, the
provider falls back to the direct local provider and surfaces `fallback_reason` — the
seam already models exactly this.

### 6.6 Scope honesty: what "the same ways" decomposes into

| Class | Examples | Where it executes |
| --- | --- | --- |
| List/state | status, model, duration, family | Remote read, cached locally |
| Lifecycle mutations | kill, retry, launch, wait/resume | Remote, name-addressed |
| Content reads | chat, response, diff, artifacts | Remote by handle, digest-cached |
| Viewer-local state | folds, marks, dismissal, tribe, query profiles | Local, keyed by global name |
| Genuinely local | tmux attach, `$EDITOR` on workspace files | Refuse cleanly or `ssh -t` |

Viewer state stays on the MacBook keyed by global name — the `athena_agent_sync_repair`
research already established this separation for imports ("'imported' is a provenance
fact; 'visible' is a local UI choice"). Remote tmux attach is honestly a different
operation; say so in the UI rather than pretend.

## 7. Phasing

Each phase is independently useful and revertible, behind a feature flag (per
`sase/memory/sase_flags.md`).

| Phase | Deliverable |
| --- | --- |
| **0** | Fleet wire contract + fault harness in `sase-core` (identity, snapshots, cursors, revisions, error model; a fake host server that can delay, disconnect, duplicate, overflow replay, restart epochs). Ship the gateway binary; add `sase host {start,status,stop,list}` under launchd/systemd supervision; `hosts:` config block. |
| **1** | Resident Rust read path for agent snapshots; drop the Python fork from reads. |
| **2** | Index generation counter + real `AgentsChanged { cursor }` feed; `ResyncRequired` on gaps. |
| **3** | Federated provider behind the existing ACE seam; cache-first rendering; per-host staleness badges; machine column/filter. **Read-only — this is the user's core ask and the milestone to optimize for.** |
| **4** | Mutations (kill, retry, wait/resume, then launch) with idempotency journal, server-side resolution, revision fencing, and target-side admission — gated on §7.1. |
| **5** | Content by handle: chat, response, diff, artifacts with digest-validated caching. |
| **6** | Launch routing: host picker showing live runner-slot capacity. |

Phase 3 ships before any mutation exists, so its blast radius is a wrong row rather
than a wrong kill, and it is where the staleness model gets validated by real use.

### 7.1 Fault-injection gates for the mutation phase

The mutation phase does not ship until automated tests demonstrate: a lost launch
response retried yields exactly one agent; a disconnect during kill recovers the same
terminal result via the journal; a stale kill against a reused name/PID cannot hit a
newer run; gateway restart forces a correct epoch-based resync; duplicated, reordered,
and overflowed events all converge to the snapshot; one hung host leaves the rest
responsive; sleep/wake and direct↔DERP transitions recover without a TUI restart; two
controllers issuing conflicting actions resolve deterministically via revisions; older
and newer client/server versions negotiate capabilities cleanly; revoked tokens and
denied grants stop access; and turning the daemon off leaves local CLI/ACE fully
functional. The sidecar plane must never present an imported remote process as live.

## 8. What would reopen this decision

- **More than ~10 machines, or non-TUI consumers** (web, phone, second laptop) wanting
  the same feed: N-way mesh polling stops being simple; NATS with leaf nodes becomes
  the better answer, and the JSON wire records port over largely unchanged.
- **Cross-machine agent-to-agent coordination** (one machine's agent blocking on
  another's) — a genuinely different topology that would justify a broker.
- **Sub-second cross-machine event latency as a requirement** rather than a nicety.
- **Tailscale stops being the substrate** — the encryption/identity/discovery work it
  absorbs comes back, and the transport calculus changes.
- **High-volume streaming or non-Python clients** making gRPC's generated contracts
  substantially more valuable.

## 9. Open questions for the user

1. Should the MacBook be able to launch on a host where the project is not checked out?
   (apollo and the MacBook share both projects today, so this is dodgeable until the
   launch-routing phase.)
2. Remote tmux attach: refuse with an explanation, or shell out to
   `ssh -t <host> tmux attach`? The latter is useful but is honestly a different
   operation.
3. Should dismissal be global or per-viewer? §6.6 argues per-viewer (consistent with
   the agents_sync import model), but a single-user tailnet might prefer
   dismiss-everywhere.

## 10. Sources

Repo evidence (verified during consolidation against `sase` @ `4c1c7b24e` /
`sase-core` @ `51df9061`): `crates/sase_gateway/` (`routes.rs`, `host_bridge.rs:186`,
`daemon.rs`, `server.rs`, `wire.rs`, `contract.rs`), `crates/sase_core/src/machine_hood.rs`,
`src/sase/ace/tui/data_providers/` (`_types.py`, `_factory.py`, `_settings.py`),
`src/sase/ace/tui/util/fs_watcher.py`, `src/sase/agent/running.py:45`,
`src/sase/default_config.yml:38,271`, `pyproject.toml`, revert commit `5a65fa4fc`,
`docs/mobile_gateway.md`, `docs/agents_sidecar.md`, glossary strand `glossary:node`,
core memory `rust_core_backend_boundary`.

External:

- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) ·
  [MagicDNS](https://tailscale.com/docs/features/magicdns) ·
  [connection types](https://tailscale.com/docs/reference/connection-types) ·
  [app capabilities](https://tailscale.com/docs/features/access-control/grants/grants-app-capabilities) ·
  [Tailscale identity](https://tailscale.com/docs/concepts/tailscale-identity)
- [WHATWG Server-Sent Events](https://html.spec.whatwg.org/dev/server-sent-events.html) ·
  [Axum SSE](https://docs.rs/axum/latest/axum/response/sse/)
- [RFC 9110 HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html) ·
  [IETF Idempotency-Key draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)
- [ZeroMQ Guide: reliable request/reply](https://zguide.zeromq.org/docs/chapter4/) ·
  [reliable pub/sub](https://zguide.zeromq.org/docs/chapter5/) ·
  [libzmq releases](https://github.com/zeromq/libzmq/releases) ·
  [zeromq-dev status thread, July 2026](http://www.mail-archive.com/zeromq-dev@lists.zeromq.org/msg31708.html)
  (and [reply](http://www.mail-archive.com/zeromq-dev@lists.zeromq.org/msg31709.html))
- [Core NATS](https://docs.nats.io/nats-concepts/core-nats) ·
  [JetStream](https://docs.nats.io/nats-concepts/jetstream) ·
  [NATS leaf nodes](https://docs.nats.io/running-a-nats-service/configuration/leafnodes)
- [gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/) ·
  [deadlines](https://grpc.io/docs/guides/deadlines/) ·
  [retry](https://grpc.io/docs/guides/retry/)

## 11. Recommended solution

**Extend the existing Rust `sase_gateway` into a supervised per-machine host daemon
speaking versioned HTTPS/JSON + SSE, published tailnet-only via loopback +
`tailscale serve`, and consumed through the ACE provider seam that already exists. Add
no ZeroMQ, no NATS, no gRPC, and no revived all-purpose daemon.**

Concretely: make agent reads resident in Rust (the single highest-value change —
~3.8 s → milliseconds); add a real cursor-based change feed with `ResyncRequired` on
gaps and a 60 s snapshot reconcile as the safety net; keep machine names as the one
identity while pinning a gateway identity at enrollment; put the host client in
`sase-core` behind `sase_core_rs` per the project's own backend boundary; keep each
host authoritative for its own processes and launch admission; keep the git agents_sync
sidecar as the durable second plane so offline machines degrade to stale rows instead
of absent ones; and call the fleet concept "host", never "node".

Ship read-only fleet visibility first (Phase 3). Enable remote kill/retry/launch only
after the idempotency journal, server-side name resolution, revision fencing, and the
fault-injection suite in §7.1 are green. This path adds no new failure domain, degrades
along an axis that already works today (athena offline is already handled), reuses the
tested pieces already in the tree, and is the most reliable route to local-fidelity
management of every machine's agents from one TUI.
