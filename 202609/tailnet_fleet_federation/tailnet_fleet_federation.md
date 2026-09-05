# Tailnet Fleet Federation: One ACE TUI For Every Machine

## Research question

How should SASE let one `sase ace` TUI — on the MacBook — view, launch, kill, and
otherwise manage sase agents running on every machine in the user's Tailscale tailnet,
with the same fidelity as local agents, now that the `agents_sync` import leg has been
deleted (epic `sase-ws`, decision `agents-sync-publish-only`) and the git-backed second
plane is gone?

## Provenance

Consolidated from two independent researcher reports plus lead-researcher verification:

- `tailnet_fleet_federation__a.md` — `research.1g.cdx` (codex/gpt-5.6-sol), originally
  `tailnet_agent_fleet_v2.md`.
- `tailnet_fleet_federation__b.md` — `research.1g.cld` (claude/opus), originally
  `cross_machine_agent_control_plane.md`.

Both examined `sase` @ `302e6d643` and `sase-core` @ `fe9a643c` and measured live on
athena. Both build on `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md` (the
consolidated predecessor, now superseded) and
`research:202609/sase_collaboration_architecture.md` (which motivated deleting the
import leg). During consolidation the lead re-verified every load-bearing code claim
against the checkouts with fresh audits of `crates/sase_gateway`, `crates/sase_core`,
and the ACE loader/provider packages, and re-ran the index probes on athena on
2026-09-05. §3 records what survived, what needed correction, and the handful of claims
each report got wrong.

## Executive summary

Both researchers, starting from the same predecessor, independently converged on the
same architecture — the third convergence on this transport in three reports. The lead
verification confirms it. The consolidated recommendation:

**Extend the existing Rust `sase_gateway` into one supervised per-user binary with two
roles — `serve` (expose this machine's agents as the sole authority for them) and
`federate` (aggregate configured peers for local consumers) — speaking versioned
HTTP/JSON snapshots plus an SSE invalidation feed over per-device Tailscale Serve
endpoints. The fleet wire is the `AgentArtifactScanWire` contract Rust and Python
already share, wrapped in a small fleet envelope; ACE consumes it through the provider
seam that already exists. No ZeroMQ, no NATS, no gRPC, no broker, no new row model, no
new identity space — and the `agents_sync` import leg stays deleted.**

The load-bearing points, in the order they were hardest won:

1. **The hard part is a local refactor, not networking** (report B's central finding,
   verified). ACE's agent loader conflates *resolution* (work needing the owning
   machine's kernel and disk: PID liveness, stale-marker repair, index mutation) with
   *presentation* (pure data → the 209-field row). Split them, and remote parity
   becomes structural: the remote machine resolves, the viewer presents, both running
   code that already exists. Do this split first, before any network code.
2. **Liveness must be a resolved verdict shipped by the owner, never a viewer
   inference.** Lead re-measurement: 1,871 index rows carry an active status while 27
   agents are actually alive (98.6% phantom). A viewer that trusts index rows renders
   ~1,800 agents that do not exist; worse, `_running_loaders.py:252-257` would check a
   remote PID against the local process table and then unlink markers and mutate the
   local index for a path that is not local.
3. **Reads must be resident in Rust.** The gateway forks a Python bridge per request:
   6.3–6.7 s on athena versus ~14 ms for the same data from SQLite (lead re-verified:
   status aggregation over the 195 MB index in 12–15 ms). Tailnet latency (10–33 ms,
   direct WireGuard) is noise by comparison; the fork is the entire problem.
4. **Mutations need a durable idempotency journal before they ship.** The launch
   route's `request_id` is a pure correlation passthrough — verified: no dedup, no
   journal, zero hits for any idempotency machinery in the gateway crate. A retried
   launch after a lost response burns a second runner slot and real money.
5. **The current pairing flow cannot be exposed to the tailnet** (report A's finding,
   verified). `pair_start` is unauthenticated and returns the pairing code in its
   response; `pair_finish` mints a bearer token from that code alone
   (`routes.rs:562-651`). Loopback binding mitigates this today — but Tailscale Serve
   publication makes loopback tailnet-reachable, which is exactly the fleet deployment.
   Fixing pairing is a Phase 0 blocker, not polish.
6. **The deleted import leg took the offline story with it.** A viewer-side per-machine
   snapshot cache is now load-bearing, not an optimization — and it must be a
   disposable presentation cache under `~/.sase/machines/<machine>/`, never touching
   the artifact index, name registry, or dismissed bundles, or it recreates what
   `sase-ws` just removed.

Ship read-only fleet visibility first. Enable mutations only behind the journal,
host-side name resolution, revision fencing, and the fault gates in §8.

## 3. Lead verification: what survived, what was corrected

Every claim below was re-checked against `sase` @ `302e6d643` and `sase-core` @
`fe9a643c` during consolidation, plus fresh probes on athena.

**Verified (both reports or unique to one):**

- SSE is not a live change feed. `events()` (`routes.rs:764-788`) replays a buffered
  ring then emits only heartbeats; a connected client never sees subsequent events
  without reconnecting. `publish_agents_changed` is called from exactly four
  production sites, all the gateway's own mutation handlers (`routes.rs:854, 889, 925,
  967`) — an agent launched by a local TUI, chop, or finalizer emits nothing.
- `request_id` is carried on launch/retry wires (`wire.rs:488, 503, 562`) and never
  used for deduplication anywhere in the crate.
- Pairing is self-authorizable once remotely reachable (§2 point 5), with no rate
  limit or pairing-count cap; additionally every authenticated request rewrites all of
  `devices.json` to update `last_seen_at` and fsyncs an audit line
  (`storage.rs:66-88, 206-221`) — a per-poll durability tax report A alone caught.
- `sase_core` has no tokio, no reqwest, no async runtime, and is deliberately
  PyO3-free; `sase_gateway` has axum, tokio, reqwest, and already depends on
  `sase_core`. The predecessor's plan to put the HTTP client in `sase_core` behind the
  Python binding does not survive the crate graph (report B's correction, confirmed).
- The fleet wire exists: `AgentArtifactRecordWire` is shared Rust/Python, with a live
  `record_shape: full | list` discriminator, and the index `meta` table already holds
  versioned state — but **no monotonic revision counter exists yet** (B proposes one;
  nothing to reuse).
- The provider seam is real and idle: `provider_contract.py` defines capabilities,
  handles, pages, snapshots, and delta batches with `resync_hint`;
  `agents_daemon_reads_enabled()` is a hard `return False`; the factory returns only
  `DirectAgentsDataProvider`.
- `kill_named_agent` (`src/sase/agent/running.py:45`) re-resolves by name and returns
  typed `not_found` / `already_completed` outcomes — the host-side mutation pattern to
  build on. Query pushdown (`compile_agent_query_pushdown`) already emits a filter
  dict the Rust index consumes end-to-end.
- The gateway serves 27 routes including the whole attention plane (notifications,
  gate approval, question answering, beads, xprompts catalog) — remote "answer this
  agent's question" inherits existing, authenticated, audited endpoints.
- Deployment gaps are real: the gateway binary is not shipped in any wheel (resolved
  from `PATH` or a sibling dev build, `mobile_gateway.py:285-297`); `DaemonConfig`
  models a Unix socket that nothing has ever bound (no `UnixListener` in the crate);
  tower-http is pulled with only the `trace` feature, so HTTP compression is absent
  (16× on live payloads, 7.8× on history — measured by B).
- The sase-3e daemon revert (`5a65fa4fc`, 2026-05) removed an entire local
  daemon/projection/scheduler stack and its ACE surfaces. Invariant I1 below is that
  lesson encoded as structure: the daemon must only ever add remote rows, never
  mediate local ones.
- 13 Python runtime deps, no HTTP client. `max_running_agents` is a host-wide slot cap
  (`default_config.yml:38`); no `machines:` config section exists yet.

**Corrected during consolidation:**

- B's "zero filesystem access" claim for `_done_snapshot_loaders.py` holds for done
  rows, but one transitive FS touch is reachable on the wire path for active rows:
  `enrich_agent_from_meta_wire` → `_meta_enrichment_common.py:453`
  `response_path.exists()`, gated on `STARTING`/`RUNNING`. Presentation is *nearly*
  total, not total — the Phase 1 fence must include the wire-path enrichment
  functions, precisely for the rows a fleet view cares most about.
- B's fencing arithmetic: `is_process_running`/`is_process_alive` has ~41 sites in
  `src/sase/ace/` (8 in the loader path) as claimed, but
  `update_agent_artifact_index_for_marker_mutation` has ~39 call sites repo-wide (6
  inside ACE), not 10. The ACE-scope conclusion — enumerable, mechanically findable —
  stands; the repo-wide fence is somewhat larger.
- B cites `_submit_tracked_proc()` for remote-mutation proc tracking; that symbol
  exists only in a test harness and a stale `tui_perf.md` line. The production analogs
  are `_submit_launch_proc` / `_submit_cleanup_proc` over `agent_durable`. (Memory-fix
  task filed separately.)
- B's identity claim that machine-qualified names "already exist and are already
  idempotent" is thinner than it reads: `machine_hood` exists in `sase_core` and
  validates/qualifies/strips `<machine>.<agent>` names, but it currently has no
  internal Rust callers — only PyO3 exports. The concept is established; the plumbing
  is real work, not a citation.
- A's probe numbers (5.6 s bridge, 39–79 ms MacBook ping) and B's (6.3–6.7 s, 33 ms)
  differ only as load-dependent samples of the same facts; B's are the more complete
  set and are used here.

## 4. Disagreements between the reports, resolved

1. **Where the federating client lives.** A federates directly inside ACE
   (per-host Python providers owning connections); the predecessor wanted a Rust
   client in `sase_core` behind the binding; B puts it in a `federate` role of
   `sase_gateway`, consumed by ACE over a local Unix socket. **B is right.** The crate
   graph rules out `sase_core` (no tokio/reqwest; adding them puts an async runtime
   inside every Python wheel across the GIL). Direct-in-ACE federation puts N live
   SSE/backoff/retry state machines in Python with no HTTP client dependency and
   spends the `rust_core_backend_boundary` budget in the TUI. The federate daemon
   keeps backend logic in Rust, keeps warm state across ACE restarts, costs exactly
   one new local process whose failure blast radius is "remote rows go stale" — and
   yields the one payoff nothing else offers: `sase mobile` pointed at a federate
   endpoint sees the whole tailnet through one pairing. A's non-negotiables (one bad
   host never blocks the TUI or other hosts) are preserved as per-peer connection,
   cache, deadline, and circuit-breaker state inside the federate role.
2. **Identity.** A wants a new `host_installation_id` UUID plus preallocated
   `agent_instance_id` as the global row key; B reuses machine-qualified global names
   plus a gateway identity pinned at enrollment. **B and the predecessor are right: no
   new identity space.** Machine name (`id.machine_name` + `machine_hood`
   qualification) stays the one agent identity; enrollment pins the gateway identity
   and fails closed if the endpoint later presents a different one — that is endpoint
   authentication, not naming. **But adopt A's instance-reservation idea inside the
   launch journal**: reserve the run identity durably before spawning so crash
   recovery can detect an already-created run instead of launching twice. That is a
   journal implementation detail, not a second row key.
3. **The wire.** A specifies a purpose-built `/api/fleet/v1` row projection; B reuses
   `AgentArtifactScanWire` plus an envelope. **B is right, and A's real concern is
   honored.** A's argument was against freezing the 16-field *mobile* DTO as the fleet
   contract — nobody proposes that. The scan wire is the marker-record projection both
   languages already share, and the snapshot loaders already build full ACE rows from
   it; a parallel fleet DTO beside a 209-field row model is the drift machine to
   avoid. A's envelope requirements fold in: `machine`, pinned identity, `now` (for
   skew-free durations), `revision`, `capabilities`, resolved `liveness` with
   timestamp, and opaque `content_handle`s in place of absolute paths.
4. **Event cursor.** A designs boot-epoch + sequence event IDs to survive daemon
   restarts of an in-memory ring; B makes the cursor a durable monotonic `revision` in
   the index `meta` table, stamped on each row. **B's design subsumes A's problem**:
   the store is the log, `SELECT … WHERE revision > :cursor` is the delta query, the
   observed revision is the mutation fence, and a daemon restart does not invalidate
   cursors. `ResyncRequired` fires only when a cursor predates the oldest retained
   tombstone — a variant `wire.rs` and the ACE seam already model. Keep A's framing as
   doctrine: events are hints; the periodic reconcile (30–60 s, jittered) is
   authoritative.
5. **CLI naming.** A brands `sase fleet …`; B specifies `sase machine …`. **B**, per
   the glossary ("node" collides with *Sase Node*/*Agent Node* in the exact surface
   this feature touches; the predecessor already ruled this) and per `cli_rules.md`
   (alphabetical subcommands, bare default `list`): `sase machine
   add|check|list|remove|serve|status|stop`.
6. **macOS supervision.** A requires a launchd user agent on every managed machine; B
   observes the viewer needs none: Linux serve machines reuse the existing
   `sase axe ensure` systemd-user-timer pattern, and the MacBook runs the federate
   role as an ACE-lifetime tracked child (`machines.daemon: auto`), visible in the
   Procs tab. **B initially; A's launchd agent becomes the later opt-in**
   (`machines.daemon: always`) for when the phone should reach the MacBook directly.
7. **Mutations through the fork bridge.** A gates every mutation on the journal from
   day one; B tolerates the subprocess bridge for mutations through the read phases.
   **Keep the predecessor's resolution**: the bridge may carry the mutation phase's
   first cut (a 4 s kill is survivable; a 4 s list is not), but the phase does not
   ship until the journal and every fault gate in §8 pass.

## 5. The consolidated design

### 5.1 Topology

```text
  MacBook — the viewer
  ┌────────────────────────────────────────────────────────────────┐
  │ sase ace                                                       │
  │   FederatedAgentsDataProvider                                  │
  │     ├── DirectAgentsDataProvider   ← local rows, always, alone │
  │     └── unix socket ──┐                                        │
  └───────────────────────┼────────────────────────────────────────┘
                          │ ~/.sase/run/<machine>/sase-daemon.sock
  ┌───────────────────────▼────────────────────────────────────────┐
  │ sase_gateway  role=federate                                    │
  │   per-peer: connection · snapshot cache · revision cursor ·    │
  │             deadlines/backoff · circuit breaker · op journal   │
  └───────┬─────────────────────────────────┬──────────────────────┘
          │  WireGuard / MagicDNS           │
          │  loopback bind + tailscale serve (never Funnel)        │
  ┌───────▼──────────────┐        ┌─────────▼────────────┐
  │ athena    role=serve │        │ apollo    role=serve │
  │  resident Rust reads │        │  resident Rust reads │
  │  resolution pass     │        │  resolution pass     │
  │  revision feed       │        │  revision feed       │
  └──────────────────────┘        └──────────────────────┘
       ▲ ~10 ms                        ▲ ~33 ms (MacBook)
       └── `sase mobile` sees the whole fleet through one pairing ┘
```

Direct star federation: each machine is the sole authority for its own live agents and
operation journal; there is no fleet-wide primary, no discovery (peers are enrolled
explicitly), and no Tailscale Services in front of hosts — Services routes among
interchangeable hosts, but a live agent belongs to exactly one machine (report A's
catch, kept).

### 5.2 Invariants

Each is a test; together they are why this is robust by construction rather than by
discipline.

- **I1 — Local truth is never daemon-mediated.** Local rows always come from
  `DirectAgentsDataProvider`; the daemon dying costs remote rows and nothing else.
  (The sase-3e revert lesson, structural.)
- **I2 — A machine is the sole authority for its own agents.** The viewer's cache
  lives in `~/.sase/machines/<machine>/` — never the artifact index, name registry,
  or dismissed bundles.
- **I3 — Liveness is a resolved verdict, never an inference.** Only the owning machine
  runs `is_process_running`; the wire carries `liveness: alive|dead|unknown` with its
  resolution timestamp. A remote PID is never an actionable value.
- **I4 — Freshness is on every row and staleness degrades status.** Past a bounded
  horizon (default 90 s ≈ 3 missed reconciles, configurable), a cached `RUNNING`
  renders `UNKNOWN`. Stale "running" invites a kill; stale "unknown" invites a
  refresh. Cached rows are never actionable (report A), and enrollment mismatches
  fail closed.
- **I5 — Mutations are name-addressed, target-resolved, journaled, fenced, and never
  queued.** An unreachable machine yields an immediate typed failure; a kill that
  executes two hours later is worse than one that visibly failed.
- **I6 — Remote paths are inert.** `artifact_dir` and friends arrive as opaque
  handles; a typed `RemoteArtifactRef` with no `__fspath__` makes misuse a type error
  at authoring time — no remote string ever reaches `open()`, `unlink()`, `$EDITOR`,
  `tmux`, or the local index mutator.
- **I7 — One wire, one row model.** Remote records enter through the same
  `AgentArtifactScanWire` the local scanner emits and are presented by the same
  loader. A field renders remotely iff it renders locally.
- **I8 — Off is byte-for-byte today.** Flag off, the factory returns
  `DirectAgentsDataProvider` and nothing else runs.

### 5.3 Read path

Resident, tiered, compressed. The serve role calls `query_agent_artifact_index`
in-process plus the resolution pass (PID liveness, stale-marker repair — the exact
work `terminalize_stale_active_agent_artifact_index_rows` and the local loader do),
then answers: 6.3 s → ~14 ms. Live tier (active + recent, ~18 KB gzipped) streams and
reconciles every 60 s; history tier (~424 KB gzipped per 200 rows) is fetched by
cursor page on demand, never on a tick — `record_shape: "list"` and
`AcePage.next_cursor` already express this. Search pushes down as the existing
`CandidateFilterWire`. Add tower-http `compression-gzip` — a one-line change with the
largest bandwidth effect in the design.

### 5.4 Change feed

Add the monotonic `revision` to the index `meta` table, stamp rows, keep a bounded
tombstone table for deletions. Drive SSE from index writes (inotify on Linux via the
existing `fs_watcher` pattern; polling elsewhere) so the feed finally reports changes
the gateway did not cause. Events are coalesced invalidation hints carrying only the
new revision; the bounded snapshot is the recovery mechanism after any gap, overflow,
or restart. The 60 s jittered reconcile is the correctness backstop; the revision
cursor makes idle ticks exact (no revision change → no reload), which is better than
the local stat-token heuristic.

### 5.5 Mutations

Typed operations only — kill, retry, wait/resume, answer-question, approve-gate, and
(last) launch — through the existing lifecycle facades; no exec endpoint, no arbitrary
cwd/env, ever. Each mutation carries
`(machine, global_name, operation, idempotency_key, payload_fingerprint,
observed_revision, deadline)`. The owning machine journals `accepted` durably before
executing, advances through a small state machine, and replays the journaled receipt
for a duplicate key; the same key with a different fingerprint is `409 Conflict`; long
operations return an operation resource the client polls or watches. The target
re-resolves by name (`kill_named_agent`'s typed outcomes are the pattern), refuses on
revision drift for destructive operations, and admits its own launches against its own
live `max_running_agents` slots — the viewer proposes, the target decides; a
client-side scheduler working from a 60 s-old snapshot would oversubscribe. For
launch, reserve the run identity in the journal before spawn so crash recovery finds
the existing run instead of creating a second (A's contribution).

### 5.6 Offline machines

The federate role persists one opaque snapshot blob + revision + `observed_at` per
peer. On startup ACE paints cached remote rows immediately (staleness-badged) and
reconciles behind them. What keeps this from becoming a second import leg: one blob
per machine, no local artifact/name/dismissal objects, rows expire and degrade per I4,
overwrite-or-discard with no merge semantics, and staleness is *rendered* rather than
silently reconciled. Machine link states are explicit: `online · reconnecting · stale
· unauthorized · incompatible · offline` — incompatible peers stay legible with an
upgrade hint, not generic failures.

### 5.7 Security and enrollment

Defense in depth; effective permission is the intersection of Tailscale grants
(deny-by-default, least-privilege per device), optional application capabilities,
scoped revocable SASE bearer tokens (hashed at rest; controller copy in the OS
keychain), and current host policy. Loopback-only bind is load-bearing, not stylistic:
`Tailscale-User-Login` headers are trustworthy only because the backend is reachable
solely through Serve. Never Funnel; Tailnet Lock is optional hardening, not a
prerequisite.

Phase 0 blockers, all verified against today's code: replace remote `pair_start`
(unauthenticated, returns the code, no rate limit) with local-only pairing initiation
via the daemon's Unix socket or an on-host interactive command using a short-lived
single-use secret; pin the gateway identity at enrollment and verify on every connect
(a MagicDNS rename or IP reassignment must never silently substitute a kill target);
introduce scoped tokens (`view`/`operate`/`admin`) instead of one broad capability
set; coalesce `last_seen_at` persistence instead of rewriting `devices.json` per poll;
rate-limit pairing, auth, and mutations independently. Audit every mutation with
principal, device, machine, operation id, fingerprint, decision, result, timestamps.

This stays single-user, per `sase_collaboration_architecture` §5.3: cross a user
boundary as an artifact, never as a process. A second user is a different feature.

### 5.8 TUI integration and scope honesty

The `tui_perf` rules are the acceptance criteria: all daemon I/O in pump-free tasks
cancelled at teardown; cache-first first paint that never awaits the network; deltas
land as selective row patches, never list rebuilds; remote mutations run as tracked
procs (via the `_submit_launch_proc`/`_submit_cleanup_proc` lineage) so they dedup,
appear in the Procs tab, and count at quit; selection re-captured after every await —
remote latency widens that window; p95 `j`/`k` stays under 16 ms with one host hung.
The machine becomes a column, a group, and a query facet — never another kind of agent
row. Per-row: host badge + precise stale age. Per-fleet: a host strip with
online/stale/offline/unauthorized/incompatible counts and slot capacity. The launch
picker shows per-machine project availability, live slots, and freshness; "Auto" is
client-side ranking among currently eligible hosts only — the target remains the
admission authority.

What "the same ways" decomposes into: list/tree/search (remote records, local
presentation, pushed-down queries); lifecycle and attention mutations (remote,
journaled — the attention routes already exist); content reads (by handle,
digest-cached, lazily); viewer-local state (folds, marks, dismissal, query profiles —
local, keyed by global name; dismissal is a per-viewer choice, not a remote fact);
genuinely local operations (`tmux attach`, `$EDITOR`) are refused with an explanation
or offered as an explicit `ssh -t` escape hatch — pretending a remote process is local
is the one dishonesty this design refuses.

## 6. Alternatives (settled three times; unchanged)

ZeroMQ, NATS, gRPC, WebSockets, SSH fan-out, a shared DB/central scheduler, and
git/`agents_sync` replication were each evaluated by the predecessor and re-evaluated
by both reports; every rejection held and two got stronger: the gateway now has 27
routes to inherit (including the whole attention plane), and only the gateway's own
contract lets `sase mobile` see the fleet through one pairing. Tailscale Services is
additionally rejected because interchangeable-host routing cannot preserve process
ownership. See `__a` §Alternatives and `__b` §4 for the scorecards.

## 7. Phasing

Each phase is independently useful and revertible, behind a `beta` flag per
`sase_flags.md`. Phases 1–3 pay for themselves at N=1 with no network involved.

| Phase | Deliverable |
| --- | --- |
| **0** | Ship the gateway binary in the `sase-core-rs` wheel; `sase machine` CLI + `machines:` config; bind the Unix socket; add gzip; **fix pairing + token scoping + identity pinning**; fault harness (a fake peer that delays, disconnects, duplicates, reorders, overflows, restarts). |
| **1** | **Resolution/presentation split** in the ACE loader: fence the enumerable call sites (41 liveness sites in ACE, index-mutation sites, 28 `artifacts_dir` modules, plus the wire-path enrichment touch) behind `RemoteArtifactRef` and an explicit resolution pass. Pure local win; do it before any network exists. |
| **2** | Resident Rust reads in the serve role (6.3 s → 14 ms); drop the fork from reads. |
| **3** | Index `revision` + tombstones; real `AgentsChanged{revision}` feed driven by index writes; `ResyncRequired` on gaps. |
| **4** | Federate role: per-peer connections, snapshot cache, cursors, circuit breakers; `FederatedAgentsDataProvider` behind the existing seam; machine column/group/filter, staleness badges, link states. **Read-only. The core ask.** |
| **5** | Mutations: kill, retry, wait/resume — journal, host-side resolution, revision fencing, target-side admission. Gated on §8. |
| **6** | Attention plane: answer questions, approve gates on remote agents (routes exist; mostly UI). |
| **7** | Content by handle: chat, response, diff, artifacts; digest-validated cache. |
| **8** | Remote launch with the machine picker and journal-reserved run identity. Most dangerous mutation; last. |
| **9** | Phone sees the fleet: point `sase mobile` at a federate endpoint. Free once Phase 4 lands; validates the contract. |

## 8. Acceptance gates

Phase 4 (read-only) requires: local agents paint and stay navigable with one remote
host hung; healthy hosts hydrate independently; cached rows show honest stale ages and
degrade `RUNNING`→`UNKNOWN` past the horizon; daemon restart, replay loss, and cursor
gaps converge automatically; sleep/wake and direct↔DERP transitions recover without
restarting ACE; endpoint reuse with a different pinned identity fails closed; version
mismatches negotiate or stay legible; viewing remote state creates zero local
artifacts, index rows, or registry entries; no snapshot discloses an actionable
absolute path; cache-first startup and p95 navigation latency are preserved.

Phase 5 (mutations) additionally requires, as automated fault-injection tests: a lost
launch response retried with the same key yields exactly one agent; a disconnect
mid-kill recovers the journaled terminal result; a stale kill against a reused name or
recycled PID returns a conflict, never a wrong kill; a stale-`UNKNOWN` row refuses
mutation; revoked tokens and denied grants stop access predictably; no remote path
reaches `open()`/`unlink()`/the local index (asserted by type and by test); turning
the daemon off leaves local CLI and ACE fully functional.

## 9. What would reopen this decision

More than ~10 machines or several non-TUI consumers of the same feed (NATS leaf nodes
become the better answer; the JSON records port); cross-machine agent-to-agent
coordination (a genuinely different topology); a second user or hardware you do not
own (a multi-tenant scheduler with a real permission model — explicitly out of scope);
sub-second cross-machine event latency as a requirement; or Tailscale ceasing to be
the substrate (encryption, identity, and NAT traversal land back on SASE's budget).

## 10. Open questions for the user

1. **MacBook daemon: ACE-lifetime child or supervised launchd agent?** §4.6 recommends
   the child and defers launchd until the phone should reach the MacBook — confirm the
   phone is not an immediate goal.
2. **Remote `tmux attach`: refuse with explanation, or shell out to
   `ssh -t <machine> tmux attach`?** The design assumes refuse-plus-explicit-escape.
3. **Is dismissal per-viewer or fleet-wide?** Per-viewer is assumed; dismiss-everywhere
   is a remote mutation and belongs in Phase 5 if wanted.
4. **May remote launch target a machine where the project is not checked out?**
   Dodgeable until Phase 8 while the three machines share projects.
5. **Is 90 s the right staleness horizon?** A config field, not a flag; the default
   trades phantom-`RUNNING` risk against badge churn.

## 11. Sources

**Researcher reports:** `tailnet_fleet_federation__a.md` (cdx),
`tailnet_fleet_federation__b.md` (cld) — see each for full measurement tables,
alternative scorecards, and code citations.

**Prior research:** `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`
(superseded by this report), `research:202609/sase_collaboration_architecture.md`.

**Lead verification (2026-09-05, athena):** fresh audits of
`crates/sase_gateway/src/{routes.rs,storage.rs,daemon.rs,server.rs,wire.rs}`,
`crates/sase_core/src/agent_scan/*`, `crates/{sase_core,sase_gateway,sase_core_py}/Cargo.toml`,
`src/sase/ace/tui/{provider_contract.py,data_providers/*,models/_loaders/*}`,
`src/sase/agent/running.py`, `src/sase/ace/agent_query/pushdown.py`,
`src/sase/axe/_ensure_timer.py`, `src/sase/integrations/mobile_gateway.py`,
`src/sase/default_config.yml`, `pyproject.toml`, revert `5a65fa4fc`; read-only SQLite
probes of `~/.sase/agent_artifact_index.sqlite` (194.7 MB; 1,871 active-status rows;
40,108 dismissed rows; 12–15 ms aggregation) and `sase agent list --json` (27 live).

**Project context:** epic `sase-ws` (all six phases closed), decisions
`agents-sync-publish-only`, `rust-core-required`, `two-speed-verification`; memories
`rust_core_backend_boundary`, `tui_perf.md`, `sase_flags.md`, `cli_rules.md`.

**External:** [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) ·
[Tailscale Services](https://tailscale.com/docs/features/tailscale-services) ·
[connection types](https://tailscale.com/docs/reference/connection-types) ·
[grants](https://tailscale.com/docs/reference/syntax/grants) ·
[MagicDNS](https://tailscale.com/docs/features/magicdns) ·
[Tailnet Lock](https://tailscale.com/docs/features/tailnet-lock) ·
[WHATWG SSE](https://html.spec.whatwg.org/dev/server-sent-events.html) ·
[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) ·
[IETF Idempotency-Key draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)
(expired April 2026; a design reference, not a standard).

## 12. Recommended solution

Build **tailnet fleet federation** as a feature of the existing Rust `sase_gateway`:
one supervised per-user binary, `serve` role on every managed machine (loopback bind,
published per-device via Tailscale Serve, resident `sase_core` reads, resolution pass,
revision feed) and `federate` role beside the viewer (per-peer caches, cursors,
circuit breakers, operation journal, Unix-socket API for ACE — and, later, one pairing
that shows the phone the whole tailnet). The fleet wire is the shared
`AgentArtifactScanWire` in a small envelope of machine identity, freshness, resolved
liveness, and opaque content handles; ACE consumes it through the provider seam that
has been waiting for exactly this, with local rows always served directly.

Do the work in this order: split resolution from presentation in the ACE loader (the
real feature, and a local win on its own); make serve reads resident; add the one
monotonic revision that is simultaneously cursor, delta query, and mutation fence;
ship read-only fleet visibility; and only then enable mutations behind the durable
idempotency journal, host-side name resolution, revision fencing, target-side launch
admission, and the fault gates above — with pairing, token scoping, and identity
pinning fixed before the first tailnet exposure.

This is **reliable** because every failure has one bounded consequence: the daemon
dying costs remote rows, a peer going offline costs freshness, a lost response costs a
retry that cannot duplicate. It is **robust** because the invariants are enforced by
types and ownership rather than discipline: a remote path has no `__fspath__`, a
remote PID has no liveness, a remote machine's state has no local writer, and off is
byte-for-byte today. And it is **beautiful** because remote and local rows are built
by the same function from the same contract — parity is not a checklist to maintain
but the shape of the thing — while the TUI stays local-first, progressively hydrated,
and honest about exactly how stale everything it shows you is.
