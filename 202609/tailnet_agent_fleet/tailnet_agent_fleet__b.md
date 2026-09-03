---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# One TUI, Every Machine: Cross-Machine Agent Dispatch And Control

**Research question:** how should SASE let one `sase ace` TUI — running on the MacBook —
view, launch, kill, and otherwise manage sase agents running on every other machine in
the user's Tailscale tailnet, with the same fidelity as local agents? Which external
framework, if any (ZeroMQ was the user's prior), should carry that traffic?

**Scope:** `sase` at master `4c1c7b24e`, `sase-core` at `51df9061`. Read paths: the
`sase_gateway` crate in full, `sase/agents_sync/` (the existing cross-machine channel),
the ACE Agents-tab data-provider seam, the agent loader / refresh cadence, the Rust
`agent_scan` index, `machine_hood.rs`, and the mobile gateway docs and config surface.
Every latency and payload number below was **measured on the live tailnet on
2026-09-03** against `kellys_mbp` (Apple M1) and `apollo` (16-core Linux droplet); no
runtime state was mutated. External framework claims are cited to sources at the end.

---

## Executive summary

The honest headline is that **SASE has already built roughly 70% of this, twice, and
neither copy is wired to the TUI.**

- `sase-core/crates/sase_gateway` is an 11.2k-line axum HTTP daemon that already exposes
  `GET /api/v1/agents`, `POST /api/v1/agents/launch`, `POST /api/v1/agents/:name/kill`,
  `POST /api/v1/agents/:name/retry`, and an SSE stream at `GET /api/v1/events`
  (`routes.rs:501-542`), behind device pairing and bearer tokens (`routes.rs:1605`). Its
  bind-policy error message already says the quiet part out loud: *"pass
  `--allow-non-loopback/-L` only for explicit LAN or **tailnet** exposure"*
  (`server.rs:37-41`).
- The ACE Agents tab already has a **provider seam built for exactly this**:
  `AgentsProviderSnapshot` carries `used_daemon`, `fallback_reason`, and `snapshot_id`;
  `AgentEventApplyResult` carries `resync_required`; `AgentsViewport` bounds a remote
  read window (`data_providers/_types.py:14-46`). The factory returns only
  `DirectAgentsDataProvider` (`_factory.py:9`) and `agents_daemon_reads_enabled()`
  returns a hard `False` (`_settings.py:6`).
- Cross-machine **identity** is already solved. `~/.sase/machine_name` is set on both
  machines (`kellys_mbp`, `apollo`), `qualify_machine_agent_name`
  (`machine_hood.rs:49`) produces globally unique `<machine>.<name>`, and agents_sync v2
  already publishes owner-qualified global names.
- Cross-machine **durable history** already works, over git, on a 10-minute cadence
  (`default_config.yml:271`).

What is missing is not a transport. It is (a) a **resident** read path, (b) a **real
change feed**, and (c) the TUI provider that consumes them.

**The decisive measurement is that the network is not the bottleneck — the process model
is.** Over the tailnet, `tailscale ping apollo` is **32 ms**, direct peer-to-peer, no
DERP relay. But the gateway's agent bridge forks a fresh Python interpreter per request
(`host_bridge.rs:186-202` runs `sase mobile agent-bridge <op>`), and one
`list-agents` call costs **1.04 s on the M1 and ~3.8 s on apollo**. The fork is
**~120x the round trip**. Any design that keeps the fork-per-request bridge will feel
broken no matter which framework moves the bytes.

**Recommendation (§7): do not adopt ZeroMQ.** Promote `sase_gateway` into a per-machine
`sase node` daemon, serve agent reads *resident* from the Rust `agent_scan` SQLite index
instead of forking Python, add a real change feed keyed on an index generation counter,
expose it on the tailnet, and light up the already-designed TUI provider seam with a
`FederatedAgentsDataProvider`. Tailscale supplies the encryption, identity, ACLs, and
naming that ZeroMQ's CURVE would otherwise have to reinvent, and the gateway supplies
the pairing, audit log, and committed API contract that ZeroMQ has no opinion about.

Critically, the design must be **two-plane**: a best-effort live control plane and the
existing durable git plane. `athena` is offline right now — last seen three days ago —
and its agent history is still readable. That property must not regress.

---

## 1. What "manage agents the same way" actually costs

The user's requirement is exact: *"view and manage (e.g. from the Agents tab) sase agents
running on different machines in all of the same ways I can view and manage sase agents
that are running on the local machine."* It is worth being precise about how large that
surface is, because the surface — not the wire protocol — is where this project's risk
lives.

`src/sase/ace/tui/actions/agents/` holds **~160 modules**. The verbs include: kill (with
a cleanup panel, clan cleanup, kill-all, kill transactions, kill persistence), dismiss,
revive (nine modules), revert, fork, wait/resume, tribe assignment, marking, folding,
notification and gate execution, HITL modals, plan gates, and detail panels for diffs,
artifacts, and tmux workspaces.

The row model is correspondingly wide: `_agent_state.py` declares **197 annotated
fields** across 512 lines. The mobile gateway's `MobileAgentSummaryWire`
(`wire.rs:420-435`) is a **15-field** projection. That gap is the design problem. It is
also the reason the answer is *not* "just replicate the row."

The tractable decomposition — and the one this report recommends — is:

| Class | Examples | Where it must execute |
| --- | --- | --- |
| **List/state** | status, model, duration, family, prompt snippet | Remote reads, cached locally |
| **Lifecycle mutations** | kill, retry, launch, wait/resume | **Remote**, name-addressed, server-resolved |
| **Content reads** | chat, response, diff, artifacts | **Remote**, fetched by handle, cached |
| **Local-only view state** | fold state, marks, dismissal, tribe, query profile | **Local**, keyed by global name |
| **Genuinely local** | tmux attach, `$EDITOR` on a workspace file | Refuse cleanly, or shell out to `ssh -t` |

That last row matters for honesty: **attaching to a remote agent's tmux pane is not the
same operation**, and the TUI should say so rather than pretend. Everything else is
reachable.

---

## 2. Prior art already in the tree

Five mechanisms already exist. Any plan that ignores them will build a sixth.

### 2.1 The mobile gateway — an HTTP control plane, already written

`crates/sase_gateway` is a complete axum service:

```text
crates/sase_gateway/src/  routes.rs 5489  wire.rs 1579  contract.rs 981
                          host_bridge.rs 844  push.rs 674  storage.rs 522
                          server.rs 422  daemon.rs 345  main.rs 299  (11,229 total)
```

It has device pairing (`/api/v1/session/pair/start|finish`), bearer-token auth with an
audit log (`routes.rs:1605`, `storage.rs`), a **committed API contract snapshot**
(`contract.rs`, `--contract-out`), schema versioning (`GATEWAY_WIRE_SCHEMA_VERSION`,
`wire.rs:20`), FCM push, and the agent verbs the user wants. `docs/mobile_gateway.md`
documents the architecture; `docs/mobile_mvp_runbook.md` documents the deployment
posture — **loopback bind plus `tailscale serve`, ACLs limited, no Funnel, no public
tunnels**.

Three gaps make it unusable *as-is* for this purpose, all of them fixable:

1. **The bridge forks Python per request.** `CommandAgentHostBridge::invoke`
   (`host_bridge.rs:186-202`) spawns `sase mobile agent-bridge <operation>` and pipes
   JSON over stdin/stdout. Measured cost in §3.
2. **The SSE stream is not a change feed.** After replaying initial events, the loop
   emits only heartbeats (`routes.rs:764-787`). `EventPayloadWire::AgentsChanged` exists
   (`wire.rs:251`) but is published *only* as an echo of the gateway's own mutations
   (`routes.rs:854, 889, 925, 967`). An agent launched by a local TUI, a chop, or a
   finalizer produces **no event at all**. A MacBook watching apollo this way would miss
   essentially every real change.
3. **The binary is not shipped.** `_resolve_gateway_command`
   (`integrations/mobile_gateway.py:286-299`) looks on `PATH`, then falls back to a
   sibling `../sase-core/target/{debug,release}/sase_gateway` dev build. `sase_gateway`
   is not present anywhere on this machine. `sase mobile gateway start` is also
   foreground-only, with no `status` or `stop` subcommand.

### 2.2 The daemon scaffold

`daemon.rs` already models a host daemon: `DaemonConfig` with a `host_identity`, a run
root at `~/.sase/run/<host>/`, and a `sase-daemon.sock` path (`daemon.rs:23, 203`). But
`run_daemon` only serves the HTTP gateway or blocks on Ctrl-C — **nothing ever binds the
socket**. It is a placeholder waiting for exactly this feature.

### 2.3 The TUI provider seam

Already quoted in the summary. `AgentsProviderSnapshot.used_daemon`,
`fallback_reason`, `fallback_message`, `snapshot_id`; `AgentEventApplyResult` with
`resync_required`/`resync_reason`; `AgentsViewport` with `start_row`, `visible_rows`,
`prefetch_rows` and a `requested_limit` (`_types.py:14-46`). Someone designed this seam
for a remote, paginated, event-driven, fallback-capable source and then shipped only the
direct provider. **This is the insertion point.** Using it costs no new abstraction.

### 2.4 Machine-qualified identity

`machine_hood.rs` is small, tested, and exactly right: `validate_machine_name` (line 25)
enforces `^[a-z_]+$`; `qualify_machine_agent_name` (line 49) is idempotent and
hood-boundary-aware; stripping is its inverse. Live state confirms it is in use —
`~/.sase/machine_name` is `kellys_mbp` here and `apollo` there.

The agents_sync v2 records (`agents_sync/v2_models.py`) already carry
`owner`/`local_name`/`global_name`/`source_run_id`. **Do not invent a node ID.** The
node is the machine name.

### 2.5 The durable git plane

`sase/agents_sync/` publishes owner-qualified hoods, runs, families, containers,
relationships, commits, and content-addressed file references (path + digest +
size_bytes) into a git sidecar, integrated on a **10-minute** check interval
(`default_config.yml:271`). The 2026-09-02 `athena_agent_sync_repair` research
established the v2 protocol's invariants — most relevantly, *"imported terminal runs are
hidden by default"* and *"identity is global; names are projections."*

This plane is slow, but it is **partition-proof**, and it is the reason `athena` — three
days offline — is not invisible today. §7 keeps it.

---

## 3. Measurements

All on 2026-09-03, MacBook (`kellys_mbp`, Apple M1) to `apollo` (16 vCPU Linux, DO
droplet, nyc1).

### 3.1 The tailnet is fast

```text
$ tailscale ping --c 5 apollo
pong from apollo (100.76.155.98) via 159.223.165.54:41641 in 32ms
```

**32 ms, direct peer-to-peer** (a public `ip:port`, not a DERP relay). ICMP to the
tailnet IP averaged 192 ms with a 100 ms standard deviation — that spread is MacBook
Wi-Fi jitter, not tailnet cost, and it is the reason §6.4 insists on deadlines rather
than assuming a stable RTT.

Tailnet: `tail297af1.ts.net`, MagicDNS enabled, four nodes, all owned by one user:

```text
100.108.201.99  kellys-macbook-pro  macOS    (self, TUI host)
100.76.155.98   apollo              linux    online
100.87.31.114   athena              linux    offline, last seen 3d ago
100.69.110.59   pixel-10-pro-xl     android  offline, last seen 24d ago
```

### 3.2 The process model is slow

| Operation | Host | Wall time | Payload |
| --- | --- | --- | --- |
| `sase agent list --json` | kellys_mbp | **0.68 s** | 12.9 KB (9 agents) |
| `sase agent list --json` | apollo | **5.47–5.87 s** | 27.4 KB (19 agents) |
| `sase mobile agent-bridge list-agents` | kellys_mbp | **1.04 s** | 7.3 KB |
| `sase mobile agent-bridge list-agents` | apollo (via ssh) | **3.95 s** | 16.9 KB |
| `ssh apollo true` (cold TCP) | — | **0.71 s** | — |
| `ssh apollo sase agent list --json` (cold) | — | **6.77 s** | 27.4 KB |
| `ssh apollo …` (warm, `ControlMaster`) | — | **5.51 s** | 27.4 KB |
| `tailscale ping apollo` | — | **0.032 s** | — |

Three conclusions fall directly out of this table:

1. **Python interpreter startup dominates everything.** apollo is a 16-core machine with
   only five projects; `sase agent list` still burns 4.7–5.0 s of *user CPU*. The
   scanning work is negligible — the local index is 1.9 MB with 43 live rows. This is
   import cost (SASE plus three installed plugins).
2. **SSH multiplexing does not save you.** `ControlMaster` removed only ~1.2 s of a
   6.8 s call, because the remaining 4.8 s is the remote interpreter, not the transport.
3. **A resident reader is worth ~100x.** 32 ms of network versus ~3.8 s of fork. Every
   framework question in §5 is downstream of fixing this.

### 3.3 The data is small

- Local artifact index: 1.9 MB SQLite, **43 rows** in `agent_artifacts` (34 completed, 5
  waiting, 4 running), 565 projected identities.
- A full running-agent JSON snapshot is **13–27 KB** per machine.

At this scale, full-snapshot reconciliation per machine is affordable — a few tens of KB
every minute is nothing on a 32 ms link. Deltas are a latency optimization, not a
bandwidth necessity. That materially lowers the risk of the whole feature.

### 3.4 Paths do not port; project keys do

```text
kellys_mbp:  sase (gh_sase-org__sase)  → /Users/bbugyi/projects/github/sase-org/sase/
apollo:      sase (gh_sase-org__sase)  → /home/bryan/projects/github/sase-org/sase/
```

The project *key* `gh_sase-org__sase` is identical. Every absolute path differs.
`sase agent list --json` emits `"artifacts_dir": "/Users/bbugyi/.sase/projects/…"` —
meaningless on another machine. See §6.2.

---

## 4. The requirement the TUI imposes

`sase/memory/tui_perf.md` is not advisory here; it is the acceptance criteria. The rules
that bind this feature:

- **Rule 1 / 2 — never block the loop, and off-the-loop is not off-the-pump.** A network
  call must run in `spawn_pump_free_task()`, never in a timer or message handler. At a
  32 ms RTT with 100 ms jitter, a synchronous remote read is a visible stall.
- **Rule 5 — cached data instantly, then a background reload.** Remote rows must render
  from a local cache on the first frame, with the network reconcile arriving later. This
  is not a nicety; it is what makes an offline machine tolerable.
- **Rule 6 — selective updates over full rebuilds.** Remote deltas should land through
  `patch_row()` / `try_remove_rows()`, not a list rebuild.
- **Rule 10 — ticks revalidate, recomputes get a longer cadence.** A per-machine poll
  must not trigger a full recompute every tick.

The existing local cadence is the template: `FULL_SANITY_REFRESH_SECONDS = 60.0` and
`AGENTS_LOAD_MIN_INTERVAL_SECONDS = 5.0` (`event_refresh/_constants.py:13, 19`), with an
event-driven watcher on top.

One platform fact shapes the design pleasantly: `util/fs_watcher.py` uses **Linux inotify
directly through `ctypes`** and *"on platforms without inotify the watcher silently
declines to start."* So the MacBook TUI is **already in the polling regime today** —
which is precisely the regime a remote source lives in. Adding remote machines does not
introduce a new failure mode on the user's primary host; it reuses the one already
proven there. And on apollo (Linux), the daemon *can* use inotify to produce a genuine
change feed.

---

## 5. Transport evaluation

### 5.1 ZeroMQ — the user's prior

ZeroMQ is a genuinely good library and the instinct is reasonable: brokerless, low
latency, and its `ROUTER`/`DEALER` and `PUB`/`SUB` patterns map cleanly onto
"one TUI, many machines." But for *this* codebase and *this* tailnet, it loses on five
counts:

1. **It solves the problem that is already solved, and not the one that isn't.** The
   bottleneck measured in §3.2 is a 3.8 s Python fork, not framing. ZeroMQ would move
   3.8 s responses very efficiently.
2. **New C dependency in a deliberately minimal Python project.** `pyproject.toml` lists
   **13 runtime dependencies**. There is no HTTP client at all — `mobile_gateway.py`
   uses stdlib `urllib.request`. `pyzmq` bundles libzmq as a C extension. Meanwhile the
   Rust side *already* has axum 0.7, tokio, and reqwest-with-rustls in the workspace.
   Adding ZeroMQ means a new native dependency in the stack that has none, to duplicate
   a capability the other stack already has.
3. **Upstream momentum is a real risk for a "reliable and robust" requirement.**
   libzmq's last stable release is **4.3.5, October 2023**, and there is an unresolved
   July 2026 mailing-list thread asking whether the project is maintained or
   feature-complete-in-maintenance-mode. That is survivable for a hobby script and
   awkward for a control plane you intend to trust with `kill`.
4. **No service discovery, and auth you must build.** ZeroMQ has no discovery — you
   configure endpoints yourself. Its security story is CURVE, which means minting and
   distributing keypairs. Tailscale already gives WireGuard encryption, per-node
   identity, ACLs, and MagicDNS names for free (§5.5), and the gateway already has device
   pairing and bearer tokens. CURVE would be a *third* auth model.
5. **No HTTP-level observability or contract.** The gateway has a committed API contract
   snapshot, a schema version, and an audit log. A raw ZMTP socket has none, and the
   project would have to reinvent all three.

**ZeroMQ is the right answer to a different question** — high-frequency, many-endpoint,
in-datacenter message passing. This is 3-5 personal machines exchanging ~20 KB a minute.

### 5.2 NATS

Technically the most *capable* option: a single ~20 MB dependency-free binary,
sub-millisecond latency, native request-reply *and* pub-sub, leaf nodes designed
explicitly for intermittently-connected edge deployments, and clean reconnect semantics.
If this were ten machines plus a phone plus a web client, NATS would be the
recommendation.

It loses here on one structural point: **it reintroduces a single point of failure that
the tailnet does not have.** A broker has to live somewhere. On the MacBook, it sleeps
and roams. On apollo, then the MacBook cannot see athena when apollo is down, even though
Tailscale would have routed MacBook↔athena directly. Leaf nodes mitigate this at the cost
of running a NATS server on *every* machine — at which point you have added a whole
messaging system to avoid writing an HTTP client for a mesh you already own.

It is the right answer if the topology grows; see §9.

### 5.3 gRPC

Strong typing, HTTP/2 streaming, mature Rust (`tonic`) and Python (`grpcio`) stacks. But
`grpcio` is another large native wheel, protobuf adds a codegen step to a project that
currently versions its wire format with a hand-written `contract.rs` snapshot, and the
gateway's existing JSON contract would have to be abandoned or dual-maintained. The
benefit over HTTP+SSE at 20 KB/min is close to zero.

### 5.4 SSH fan-out (the zero-new-infrastructure baseline)

Deserves a fair hearing because it needs *nothing* new: `ssh apollo sase agent list
--json`, parse, merge. It is genuinely the fastest thing to prototype.

Measured, it fails the requirement: **6.77 s cold, 5.51 s warm.** It also has no change
feed (only polling), no capacity awareness, requires SSH keys on every host, and gives
the TUI no way to distinguish "machine is down" from "command is slow" without a
timeout heuristic. Worth keeping as an **escape hatch for genuinely local operations**
(§1: `ssh -t apollo tmux attach`), not as the control plane.

### 5.5 Tailscale as the security layer (not a transport choice — a subtraction)

This is the point that collapses most of the complexity. The tailnet already provides:

- **WireGuard encryption** on every link, with measured direct P2P (§3.1).
- **Stable naming** via MagicDNS (`apollo.tail297af1.ts.net`) — no IP configuration, no
  discovery service, no "machines configured somewhere" file to maintain.
- **Identity and authorization** via ACLs, plus `tailscale whois` over the LocalAPI for
  per-connection user/node identity, and `Tailscale-User-Login` identity headers when
  fronted by `tailscale serve`.
- **NAT traversal**, which is what makes apollo (a cloud droplet) and the MacBook (behind
  home NAT, roaming) reachable to each other at all.

The documented caveat matters and the design must respect it: identity headers are only
trustworthy if the backend binds loopback and Serve is the sole proxy, because anything
that can reach the port directly can forge the header. `docs/mobile_mvp_runbook.md`
already lands on the right posture — **loopback + `tailscale serve`, ACLs limited, no
Funnel** — and this feature should inherit it rather than open `--allow-non-loopback`.

**Net effect: with Tailscale underneath, the transport does not need to solve encryption,
authentication, naming, or discovery.** That removes ZeroMQ's and NATS's main structural
advantages over plain HTTP, and it means the remaining question is only "what shape are
the messages," where the answer is "the shape they already are."

### 5.6 Scorecard

| | Reuses gateway | New native dep | Change feed | Discovery | Auth | Broker-free | Upstream health |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **HTTP+SSE (gateway)** | ✅ full | none | needs work | Tailscale | ✅ exists | ✅ | ✅ axum/tokio |
| ZeroMQ | ❌ parallel stack | pyzmq/libzmq | build it | build it | build CURVE | ✅ | ⚠️ 4.3.5, Oct 2023 |
| NATS | ❌ parallel stack | client libs | ✅ native | ✅ subjects | ✅ native | ❌ broker | ✅ |
| gRPC | ❌ rewrite wire | grpcio | ✅ streams | Tailscale | build it | ✅ | ✅ |
| SSH fan-out | n/a | none | ❌ poll only | ssh config | ✅ keys | ✅ | ✅ |
| git sidecar (today) | n/a | none | ❌ 10 min | ✅ | ✅ | ✅ | ✅ |

---

## 6. Problems any transport must still solve

These are the parts that actually determine whether the feature is robust. None of them
are transport features; all of them are protocol and product decisions.

### 6.1 Two planes, and never one

The single most important structural decision:

- **Live control plane** (daemon RPC, best-effort). Current state and mutations. Requires
  reachability.
- **Durable plane** (agents_sync git sidecar, eventually consistent). Terminal runs,
  prompts, commits, artifact digests. Survives partitions.

**An agent must never disappear from the TUI because its machine went offline.** athena
is offline right now; its runs are still reachable through the sidecar today, and that
must not regress. The Agents tab should show a stale-but-present row with an explicit
staleness badge and an "as of HH:MM" timestamp, and refuse mutations rather than queue
them blind (§6.5).

### 6.2 Paths are not portable; handles are

Measured in §3.4. The wire model must carry:

- the **project key** (`gh_sase-org__sase`) — portable;
- the **global agent name** (`apollo.research.5.cld`) via
  `qualify_machine_agent_name` — already portable;
- **opaque content handles** for chat, response, diff, and artifacts — never
  `artifacts_dir`.

Content is then fetched by handle over the daemon and cached locally. The agents_sync v2
`V2FileReference` (`path` + `digest` + `size_bytes`) is the right precedent: content is
addressed by digest, so a local cache can be validated without re-transfer.

### 6.3 Capacity is per-machine and machine-owned

`max_running_agents: 10` is a **host-wide** cap (`default_config.yml:38`), and the live
JSON already carries `runner_slots_in_use`, `runner_slot_queue_position`,
`runner_slot_queue_size`, and `runner_slot_holders`. apollo currently holds 20 claims on
the sase project against the MacBook's 10.

Therefore: **the target machine admits its own launches.** The client proposes; the
target's existing runner-slot gate accepts or queues. A client-side scheduler that
decides "apollo has room" from a snapshot that is 30 s old will oversubscribe. Surfacing
each node's slot state in the node list is enough for the user to route intelligently,
and it keeps the authority where the invariant lives.

### 6.4 Deadlines, not timeouts-by-accident

At 32 ms RTT with 100 ms jitter and machines that vanish for days, every remote call
needs an explicit deadline and every node needs a circuit breaker. Concretely: a short
deadline for list reads (they are re-tried on the next tick anyway), a longer one for
mutations, exponential backoff on a failing node, and — importantly — **a slow node must
never delay rendering of the fast ones.** Per-node fetches are independent; the snapshot
merges whatever arrived.

### 6.5 Mutations must be safe against stale rows

This one is already half-solved and worth preserving deliberately.
`kill_named_agent(name)` (`agent/running.py:45`) **re-resolves the agent by name on the
server**, and returns typed outcomes including `not_found` and `already_completed`. So a
client acting on a 30-second-old row cannot kill the wrong process — the worst case is a
clean "already completed" response.

Build on that rather than around it:

- **Name-addressed, server-resolved** mutations only. Never send a PID.
- **Idempotency keys** on every mutation, so a retry after a dropped response cannot
  double-launch. (A duplicate `kill` is harmless; a duplicate `launch` burns a runner
  slot and real money.)
- **Optional fencing**: include the row generation the user was looking at, and let the
  server refuse if the agent has since changed status in a way that would surprise them.

### 6.6 The change feed has to be real

As established in §2.1, `AgentsChanged` today is an echo of the gateway's own writes. A
correct feed needs a **monotonic cursor** the client can resume from:

- Add a generation/sequence counter to the artifact index (the `meta` table already holds
  `schema_version` and a `dismissed_projection` signature, so the pattern exists).
- Bump it on marker writes; on Linux, drive it from the existing inotify watcher, and
  fall back to polling elsewhere.
- Emit `AgentsChanged { cursor, … }` on SSE; clients reconnect with `Last-Event-ID`.
- If the client's cursor is too old, emit the **already-defined**
  `EventPayloadWire::ResyncRequired` (`wire.rs:242`), which the TUI seam already models
  as `AgentEventApplyResult.resync_required`.

Keep the 60-second full-snapshot reconcile as the safety net, exactly as the local
watcher does today. At 13-27 KB per machine (§3.3) that is affordable, and it means a
missed event self-heals within a minute instead of persisting until restart.

### 6.7 Clock skew

`duration_seconds` and `started_at` come from the remote host's clock. Send both the
remote timestamp *and* the remote "now" in each response, and compute durations against
the node's own clock. Otherwise a machine 30 s out of sync shows negative or inflated
runtimes.

### 6.8 Local-only state, keyed globally

Fold state, marks, dismissal, tribe assignment, and query profiles are **viewer state**,
not agent state. They belong on the MacBook, keyed by global name. The
`athena_agent_sync_repair` research already reached this conclusion for imports —
*"'Imported' is a provenance fact; 'visible' is a local UI choice. They must not be
represented by the same bit."* The same separation applies to live remote rows, and
reusing that framing keeps one model instead of two.

---

## 7. Recommendation

**Promote `sase_gateway` into a per-machine `sase node` daemon on the tailnet, make its
agent reads resident, give it a real change feed, and consume it through the ACE provider
seam that already exists. Add no new messaging framework.**

### 7.1 Shape

```text
  MacBook (kellys_mbp) ── sase ace TUI
      │
      │  FederatedAgentsDataProvider
      │    ├── DirectAgentsDataProvider        (local, unchanged)
      │    └── RemoteNodeClient × N            (one per configured node)
      │          · GET  /api/v1/agents?cursor= …    snapshot
      │          · GET  /api/v1/events              SSE change feed
      │          · POST /api/v1/agents/:name/kill   name-addressed mutations
      │
      ├─── WireGuard (Tailscale), 32 ms direct P2P, MagicDNS names
      │
      ├── apollo   ── sase node daemon ── resident Rust reader → agent_scan/SQLite
      └── athena   ── (offline) ─────────── rows served from the git sidecar plane
```

### 7.2 The decisions, and why

1. **Transport: HTTP/1.1 + JSON + SSE, the existing gateway.** Not ZeroMQ. The gateway
   already has the routes, pairing, tokens, audit log, schema version, and a committed
   contract; Tailscale already has the encryption, identity, ACLs, and naming. ZeroMQ
   would add a maintenance-mode C dependency to duplicate both.
2. **Kill the fork-per-request bridge for reads.** Serve `/api/v1/agents` *resident*
   from `sase_core::agent_scan` and the SQLite index inside the daemon. The gateway crate
   already links `sase_core`, and `rusqlite` is already a workspace dependency — this is
   the single highest-value change in the whole plan (§3.2: ~3.8 s → single-digit ms).
   Mutations may keep the subprocess bridge initially; they are rare and user-initiated,
   so a 4 s kill is survivable while a 4 s list is not.
3. **Identity: reuse `machine_name`.** Nodes are `kellys_mbp` / `apollo` / `athena`;
   agents are `<machine>.<name>` via `qualify_machine_agent_name`. No new ID space.
4. **Security posture: inherit the mobile runbook.** Loopback bind plus `tailscale serve`
   inside the tailnet, ACLs restricted to the user's own devices, bearer tokens retained
   as defence-in-depth, no Funnel, no `--allow-non-loopback`.
5. **Two planes, always.** Live daemon for current state and control; git sidecar for
   durable history. Offline machines degrade to stale-badged rows, never to absent rows.
6. **Cache-first rendering.** Persist the last snapshot per node. Render it on the first
   frame with an "as of" marker; reconcile in a pump-free task. Never let a remote fetch
   touch the Textual pump.
7. **Launch admission stays on the target.** The client proposes; the target's runner-slot
   gate decides.

### 7.3 Why this is the robust choice

- It **adds no new failure domain**. No broker to keep alive, no second auth system, no
  second wire format, no new native dependency in either language.
- It **degrades along an axis that already works.** When a node is unreachable, the
  system falls back to exactly what SASE does today for athena.
- It reuses the code paths that are **already load-bearing and already tested**: the
  contract snapshot, the pairing/audit storage, the artifact index, the machine-hood
  helpers, the agents_sync v2 records, and the TUI's provider seam.
- Every mutation is **name-addressed and server-resolved**, so stale client state cannot
  cause a wrong-target action.

### 7.4 Phasing

Each phase is independently useful and independently revertible, behind a feature flag
(`sase/memory/sase_flags.md` governs the flag-and-bead procedure).

| Phase | Deliverable | Unlocks |
| --- | --- | --- |
| **0** | Ship the `sase_gateway` binary; add `sase node {start,status,stop,list}`; a `nodes:` config block (name → MagicDNS host, token) | The daemon is installable and operable |
| **1** | Resident Rust read path for `/api/v1/agents`; drop the Python fork from reads | ~3.8 s → ms; makes everything after it viable |
| **2** | Index generation counter + inotify-driven `AgentsChanged { cursor }`; `ResyncRequired` on cursor gaps | A real change feed |
| **3** | `FederatedAgentsDataProvider` behind the existing seam; cache-first render; per-node staleness badges; read-only | **The user's core ask: see every machine's agents in one tab** |
| **4** | Mutations: kill / retry / wait-resume with idempotency keys and target-side admission | Manage, not just view |
| **5** | Content by handle: chat, response, diff, artifacts, digest-validated local cache | Full-fidelity detail panels |
| **6** | Launch routing: node picker showing live runner-slot capacity | Dispatch |

Phase 3 is the milestone worth optimizing for. It is read-only, so its blast radius is a
wrong row rather than a wrong `kill`, and it is where the user finds out whether the
staleness model feels right before any mutation depends on it.

---

## 8. Failure modes and how this design answers them

| Failure | Behavior |
| --- | --- |
| Node offline (athena today) | Rows persist from cache + git sidecar, badged stale with "as of"; mutations refused with a clear reason |
| Node slow | Per-node deadline; other nodes render unaffected; breaker backs the slow node off |
| MacBook sleeps / roams | SSE reconnects with `Last-Event-ID`; cursor gap → `ResyncRequired` → full snapshot |
| Missed event | 60 s full reconcile self-heals, mirroring the local watcher's safety net |
| Stale row, user hits kill | Server re-resolves by name; returns `already_completed` / `not_found` |
| Dropped response after mutation | Idempotency key makes the retry a no-op |
| Duplicate agent names across machines | Impossible: `<machine>.` qualification is enforced at the identity layer |
| Clock skew | Durations computed against each node's reported "now" |
| Daemon dies | TUI falls back to the direct local provider; `used_daemon=False`, `fallback_reason` surfaced — the seam already models this |
| Token compromise | Tailscale ACLs are the outer boundary; revoke the device in the existing pairing store |

---

## 9. What would reopen this decision

State the conditions honestly, so the choice can be revisited on evidence rather than
taste:

- **More than ~10 nodes, or non-TUI clients wanting the same feed** (web, phone, a second
  laptop). N² mesh polling stops being the simple option; **NATS with leaf nodes** becomes
  the better answer, and the JSON wire records port to it largely unchanged.
- **Sub-second cross-machine event latency becomes a requirement.** SSE over a 32 ms link
  is fine for a TUI; if SASE ever wants tight cross-machine agent coordination
  (one machine's agent blocking on another's), a real message bus earns its keep.
- **Agents need to talk to each other across machines,** not just be observed by one TUI.
  That is a genuinely different topology and would justify a broker.
- **Tailscale stops being the substrate.** If machines must be reachable outside a
  tailnet, the encryption/identity/discovery work that Tailscale absorbs comes back, and
  the calculus in §5.5 changes.
- **libzmq's status resolves upward** *and* a measured need for its patterns appears.
  Absent both, §5.1 stands.

---

## 10. Open questions for the user

1. **Should the MacBook's TUI be able to launch on a machine where the project is not
   checked out?** apollo and kellys_mbp happen to share both projects today, so the
   question is dodgeable now, but the node picker needs an answer before Phase 6.
2. **How should remote `tmux` attach behave** — refuse with an explanation, or shell out
   to `ssh -t <node> tmux attach`? The second is genuinely useful and genuinely a
   different operation from the local one.
3. **Should dismissal be global or per-viewer?** §6.8 argues per-viewer, consistent with
   the `athena_agent_sync_repair` conclusion, but a single-user tailnet might reasonably
   prefer dismissing an agent everywhere at once.

---

## Sources

Repo evidence is cited inline as `file:line` against `sase` @ `4c1c7b24e` and
`sase-core` @ `51df9061`. External sources:

- [ZeroMQ — Wikipedia](https://en.wikipedia.org/wiki/ZeroMQ)
- [zeromq/libzmq releases](https://github.com/zeromq/libzmq/releases)
- [zeromq-dev: "Clarification on libzmq Project Status" (July 2026)](http://www.mail-archive.com/zeromq-dev@lists.zeromq.org/msg31708.html)
- [PyZMQ documentation](https://pyzmq.readthedocs.io/en/v15.0.0/index.html)
- [What is NATS? — NATS Documentation](https://docs.nats.io/concepts/what-is-nats)
- [NATS Leaf Nodes](https://docs.nats.io/running-a-nats-service/configuration/leafnodes)
- [Why NATS Is Built for DDIL Environments — Synadia](https://www.synadia.com/blog/nats-ddil-leaf-nodes)
- [NATS Sizing & resources](https://docs.nats.io/learn/deployment/sizing-and-resources)
- [gRPC vs ZeroMQ — StackShare](https://stackshare.io/stackups/grpc-vs-zeromq)
- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve)
- [Tailscale identity](https://tailscale.com/docs/concepts/tailscale-identity)
- [tsnet package — pkg.go.dev](https://pkg.go.dev/tailscale.com/tsnet)
- [tsidp — Tailscale Docs](https://tailscale.com/docs/features/tsidp)
