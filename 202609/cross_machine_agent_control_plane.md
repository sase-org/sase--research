# One TUI, Every Machine: A Cross-Machine Agent Control Plane For SASE

**Research question:** How should SASE let one `sase ace` TUI view, launch, kill, and
otherwise manage the agents running on every machine in the user's tailnet, with the
same fidelity as local agents — now that the `agents_sync` import leg has been deleted
and the git-backed second plane is gone?

**Scope and evidence:** `sase` @ `302e6d643`, `sase-core` @ `fe9a643`, measured live on
**athena** (Linux, 64 cores, load average 30.1) on 2026-09-05. Every number in §3 was
measured directly against this machine's checkouts, its 195 MB artifact index, and its
live tailnet. Prior art read and cited:
`research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md` (the direct predecessor)
and `research:202609/sase_collaboration_architecture.md` (which motivated deleting the
import leg). This report supersedes the predecessor's §6.1 offline story, §5.3 client
placement, and §6.2 reconciliation budget, and confirms the rest.

---

## Executive summary

**Recommendation: extend `sase_gateway` into one supervised binary with two roles —
`serve` (expose this machine's agents) and `federate` (aggregate configured peers) —
and make the fleet wire the `AgentArtifactScanWire` contract that Rust and Python
already share.** No ZeroMQ, no NATS, no gRPC, no new row model, no revived
all-purpose daemon.

The predecessor report reached the right transport conclusion. What it got wrong, and
what this report changes, is *what the hard part is*. The hard part is not networking.
It is that ACE's agent loader silently conflates two different jobs:

- **Resolution** — work that requires the owning machine's kernel and disk: is this PID
  alive, does this marker file still exist, does `commit_results.json` exist, delete the
  stale `running.json` and repair the index.
- **Presentation** — work that requires only data: build the 209-field row, compute
  clan/tribe/family structure, order the tree, format durations.

Today both run in the same process because both inputs are local. The fleet feature is
the refactor that draws that line, with a network hop inserted at the resulting seam.
Once drawn, remote parity is *structural* rather than a 162-module porting checklist:
the remote machine resolves, the viewer presents, and both run code that already exists.

Four findings drive the design:

1. **The wire already exists and is already versioned on both sides.**
   `sase_core::agent_scan::wire::AgentArtifactRecordWire` (Rust) and
   `sase.core.agent_scan_wire` (Python) are the same contract, and
   `src/sase/ace/tui/models/_loaders/_done_snapshot_loaders.py` already builds ACE rows
   from it with **zero filesystem access**. That file is a proof of concept for the
   whole feature, written for another reason. Inventing a "fleet DTO" beside it would be
   the mistake (§4).
2. **The artifact index is a catalog, not a liveness oracle — and the gap is enormous.**
   On athena, **1,860 index rows carry an active status while 17 agents are actually
   alive** (99.1% phantom). Any design that ships index rows and lets the viewer decide
   liveness shows 1,843 agents that do not exist. Liveness must be resolved by the
   owning machine, on every read, and shipped as a resolved verdict (§3.3).
3. **Reads must be resident, and the payoff is bigger than previously measured.** The
   gateway still forks `sase mobile agent-bridge` per request: **6.3–6.7 s** on athena
   today. The same data from a resident SQLite read is **14 ms**. That is ~450×, and it
   is the difference between a control plane and a slideshow (§3.1).
4. **The deleted import leg took the offline story with it.** The predecessor leaned on
   `agents_sync` as a "partition-proof second plane" so an offline machine's agents
   degraded to stale rows instead of vanishing. Epic sase-ws deleted that leg, and the
   `agents-sync-publish-only` decision forbids rebuilding it. **A viewer-side
   per-machine snapshot cache is therefore now load-bearing, not an optimization** —
   and it must live outside the local artifact index and outside the name registry, or
   it recreates exactly the mistake that epic removed (§7.6).

Ship read-only fleet visibility first. Enable remote mutations only behind an
idempotency journal, host-side name resolution, revision fencing, and the fault suite in
§9.

---

## 1. What changed since `tailnet_agent_fleet`

Five things moved. Three make the design easier, two make it harder.

### 1.1 The import leg is gone (harder)

Epic **sase-ws** — "Remove The Agents-Sync Import Leg" — closed all six phases. The
subsystem went from 20,645 lines / 83 modules to **13,424 lines / 64 modules**; every
`v2_import_*`, `incoming_cache*`, and `v1_*` module is deleted, and `sase agent sync`
now only publishes. Decision `agents-sync-publish-only` records that one explicit purge
command is the sole supported operation on leftover imported state.

Consequence for this feature: the predecessor's §6.1 promise — "an agent must never
vanish from the TUI because its machine went offline: offline hosts degrade to
stale-badged rows … the git agents_sync plane carries durable history" — no longer has a
mechanism behind it. Either offline machines vanish, or the viewer keeps its own cache.
§7.6 chooses the cache and specifies the constraints that keep it from becoming a second
import leg.

### 1.2 The gateway grew into a full control plane (easier)

`crates/sase_gateway` now serves **27 routes**, not the 6 the predecessor described.
Beyond agents (list, resume-options, launch, launch-image, kill, retry) it now covers
the entire *attention plane*:

```text
/api/v1/notifications            /api/v1/actions/gate/:prefix
/api/v1/notifications/:id        /api/v1/actions/question/:prefix/answer
/api/v1/notifications/:id/mark-read   /api/v1/actions/question/:prefix/custom
/api/v1/notifications/:id/dismiss     /api/v1/attachments/:token
/api/v1/beads  /api/v1/beads/:id  /api/v1/xprompts/catalog
/api/v1/update/start  /api/v1/update/:job_id  /api/v1/session/push-subscriptions
```

This matters more than it looks. "Manage agents the same ways" includes *answering an
agent's question* and *approving its gate* — and those endpoints already exist, already
authenticate, and already audit. The fleet feature inherits them.

### 1.3 The Rust scan path is complete and the gateway already links it (easier)

`sase_core::agent_scan` is **14,047 lines** across `scanner.rs`, `index.rs`,
`layout.rs`, `selector.rs`, and `wire.rs`, exporting the full index surface
(`query_agent_artifact_index`, `load_agent_artifact_records`,
`rebuild_agent_artifact_index`, `terminalize_stale_active_agent_artifact_index_rows`,
…). `sase_gateway/Cargo.toml` already declares `sase_core = { workspace = true }`.

The predecessor called resident reads "the single highest-value change." It is now not a
port — it is wiring one crate's existing public API into another crate that already
depends on it.

### 1.4 The ACE provider seam became a real contract (easier)

`src/sase/ace/tui/provider_contract.py` (210 lines) now defines
`AceProviderCapabilities(pages, deltas, lazy_details, counts)`, `AceRowHandle` with a
`daemon_handle` field, `AcePage[T]` with `cursor`/`next_cursor`/`bounded`/`truncated`,
`AceSnapshot[T]` with `snapshot_id`/`generation_id`, and `AceDeltaBatch[T]` with
`row_patches`, `count_patches`, `invalidation_reason`, and `resync_hint`.
`data_providers/_types.py` adds `AgentsViewport`, `AgentEventApplyResult`, and
`AgentsProviderSnapshot(used_daemon, fallback_reason, snapshot_id)`.

This is a complete vocabulary for a paginated, delta-fed, fallback-capable remote
source. It has one production implementation (`DirectAgentsDataProvider`) and one
consumer of the flag that would enable another (`agents_daemon_reads_enabled()`, a hard
`return False`). The seam is waiting.

### 1.5 The measurements from the biggest machine are worse (harder)

The predecessor measured the MacBook: 1.9 MB index, 43 live rows, and concluded
"per-machine full-snapshot reconciliation every minute is affordable." On athena — the
machine the user most wants to watch — the index is **195 MB with 9,446 artifact rows
and 40,084 dismissed-agent rows**. A 200-row history page of full records is **3.3 MB**
(424 KB gzipped). Full-history reconciliation is not free here. §7.3 replaces the flat
budget with tiering.

---

## 2. The central finding: resolution versus presentation

### 2.1 The loader does two jobs in one pass

`load_tiered_agents()` (`src/sase/ace/tui/models/agent_loader.py:489`) produces the
209-field `AgentState` rows the Agents tab renders. Underneath it, the `_loaders/`
package already contains **two parallel implementations** of the same job:

| Path | Input | Filesystem touches |
| --- | --- | --- |
| `_done_snapshot_loaders.py` | `AgentArtifactScanWire` | **0** |
| `_workflow_snapshot_loaders.py` | `AgentArtifactScanWire` | 0 (plus liveness) |
| `_done_filesystem_loaders.py` | directory walk | many |
| `_meta_enrichment_filesystem.py` | `agent_meta.json` | many |

Across `_loaders/*.py` there are 54 filesystem calls (`.exists()`, `open()`,
`iterdir()`, `glob()`, `read_text()`, `load_json_cached`). They are concentrated in the
legacy filesystem path and in three specific places on the snapshot path:

- `_done_common.py:33` — `Path(artifact_dir) / "commit_results.json").is_file()`
- `_running_loaders.py:253-256` — reads `running.json`, then **unlinks it** and calls
  `update_agent_artifact_index_for_marker_mutation(artifact_dir)` when the PID is dead
- `_running_loaders.py:307-320` — walks `~/.sase/projects/home/artifacts/ace-run/`

That second one is the whole problem in miniature. Given a *remote* record, the viewer
would call `is_process_running(pid)` against **its own** process table — a coin flip
that either invents a live agent or declares a live one dead — and then attempt to
mutate its own artifact index on behalf of a path that does not exist locally.

### 2.2 The blast radius is enumerable, which is why this is tractable

ACE calls `is_process_running` / `is_process_alive` at **41 sites**, of which 8 are in
the loader path (`agent_loader.py`, `_running_loaders.py`, `_workflow_loaders.py`,
`_workflow_snapshot_loaders.py`, `_meta_enrichment_common.py`,
`_agent_loader_normalization.py`, `_dismiss_persistence.py`). It calls
`update_agent_artifact_index_for_marker_mutation` at 10 sites. 28 of the 162 modules
under `actions/agents/` reference `artifacts_dir`.

That is the actual scope of "make remote rows safe": ~50 call sites to fence, not 162
modules to port. Every one of them is mechanically findable, and each has exactly one
correct answer — *resolve on the owning machine, or refuse*.

### 2.3 Why this makes the design beautiful rather than merely correct

Draw the line once and three things follow for free:

1. **The fleet wire is the scan wire.** Both machines already agree on
   `AgentArtifactRecordWire` — it is a complete projection of every marker file
   (`agent_meta`, `done`, `running`, `waiting`, `pending_question`, `workflow_state`,
   `plan_path`, `prompt_steps`, `raw_prompt_snippet`, `used_xprompts`) with a
   `record_shape` discriminator (`"full" | "list"`) already built for windowed reads.
2. **Row parity is structural.** Remote records flow through the *same* Python
   presentation code as local ones. Clan grouping, tribe panels, family trees, ordering,
   duration formatting, fold state — all of it matches by construction, because it is
   literally the same function. No 209-field DTO to keep in sync, and no drift class.
3. **The local path gets better too.** Splitting resolution out of presentation makes
   the loader testable without a filesystem and lets the snapshot path replace the
   legacy filesystem path — work that is independently worth doing and that
   `_done_snapshot_loaders.py` already started.

The one thing the wire needs added is provenance and freshness: a small envelope
carrying `machine`, `observed_at`, `revision`, resolved `liveness`, and an opaque
`content_handle` in place of absolute paths (§7.2).

---

## 3. Measurements (athena, 2026-09-05, load avg 30.1 / 64 cores)

### 3.1 The fork bridge is the bottleneck, worse than previously measured

| Operation | Result |
| --- | --- |
| `sase agent list --json` (17 live agents) | **10.9 – 11.4 s**, 24.5 KB |
| `sase mobile agent-bridge list-agents` | **6.3 – 6.7 s**, 16.1 KB |
| `sase --help` (interpreter + import floor) | 0.85 s |
| SQLite: live rows, 195 MB index | **13.7 ms** |
| SQLite: 200 most recent rows | 15.5 ms |
| SQLite: 200 full `record_json` blobs | 85.9 ms, 3.1 MB |

Two corrections to the predecessor's model. First, interpreter startup is **not** the
dominant cost here: 0.85 s of 6.3 s. The other 5.5 s is real work — scanning,
normalizing, and pid-checking under load. Second, that makes the resident-read argument
*stronger*, not weaker: a Rust reader skips both the interpreter and the redundant
Python normalization, landing at ~14 ms. **~450×.**

### 3.2 Network is not the problem; payload size is, above the live tier

| Path | Latency |
| --- | --- |
| `tailscale ping apollo` | **10 ms**, direct P2P |
| `tailscale ping kellys-macbook-pro` | **33 ms**, direct P2P |

| Payload | Raw | Gzip | Ratio |
| --- | --- | --- | --- |
| 50 live records (`full` shape) | 287 KB | **18 KB** | 16× |
| 200 history records (`full` shape) | 3.30 MB | **424 KB** | 7.8× |

Conclusions: (a) HTTP compression is mandatory, and the gateway does not have it —
`tower-http` is pulled in with only the `trace` feature. (b) A live-tier snapshot at
18 KB over a 10–33 ms link is genuinely cheap and can be reconciled every minute. (c) A
history page at 424 KB is fine on demand and unacceptable per tick. Tier the reads.

### 3.3 The index is a catalog, not a liveness oracle

```text
agent_artifacts rows                                    9,446
  … with an active status (running|waiting|starting)    1,860
actually alive (agent-bridge list-agents)                  17
dismissed_agents rows                                  40,084
index file size                                          195 MB
```

**99.1% of "active" index rows are dead.** SASE already knows this — that is what
`terminalize_stale_active_agent_artifact_index_rows()` and
`stale_running_cleanup` exist for — but it means the index alone can never be the remote
read. The serve role must run the resolution pass (pid liveness, stale-marker repair)
before answering, exactly as the local loader does today, and ship the verdict.

### 3.4 The seam is wide but the wire is narrow — and that is fine

`AgentState` carries 209 annotated fields across 532 lines; `actions/agents/` holds 162
modules. The mobile agent summary is 16 fields. The predecessor treated that gap as a
scope problem to decompose. Under §2 it is not a gap at all: the wire carries *marker
records*, not *rows*, and the 209 fields are computed locally from them by the code that
already computes them.

---

## 4. Transport: the prior conclusion holds, and one new argument strengthens it

The predecessor evaluated ZeroMQ, NATS, gRPC, SSH fan-out, and the git sidecar, and
chose HTTP+SSE over the existing gateway. Every reason still applies and two got
stronger: the gateway now has 27 routes instead of 6 (more to reuse, more to reinvent),
and `sase_core::agent_scan` is complete in Rust (the resident read is now free to
build).

The new argument is **client reuse**. Today `sase mobile` shows the agents of the single
machine its phone is paired with. If the federate role (§6) speaks the same
`/api/v1/*` contract, the phone pairs once with the MacBook and sees **the whole
tailnet** — with no mobile-app change beyond a machine column. Any transport that is not
the gateway's own forfeits that. This is a large payoff that no alternative offers, and
it did not appear in the predecessor's scorecard.

| | Reuses 27 routes | Frees the phone | New native dep | Auth model |
| --- | --- | --- | --- | --- |
| **HTTP+SSE via gateway** | ✅ all | ✅ | none | reuses pairing + Tailscale |
| ZeroMQ | ❌ | ❌ | libzmq (C) | third model (CURVE) |
| NATS | ❌ | partial | client libs + broker | fourth model |
| gRPC | ❌ rewrite | ❌ | tonic + grpcio | build it |
| SSH fan-out | n/a | ❌ | none | keys; no change feed |

Nothing here reopens the decision. §11 lists what would.

---

## 5. Correcting the predecessor: `sase_core` cannot host the client

The predecessor's §5.3 resolved a disagreement between its two source reports in favor
of "the host client belongs in `sase-core` behind the `sase_core_rs` binding, and it is
project policy." The policy half is right. The placement half does not survive contact
with the crate graph:

```text
sase_core     serde, serde_yaml, thiserror, regex, chrono, fs2, rusqlite,
              hex, sha2, libc, unicode-width      ← no tokio, no reqwest, no async
sase_core_py  sase_core + pyo3(abi3-py312)        ← cdylib wheel
sase_gateway  axum, tokio, reqwest, tower-http, jsonwebtoken, sase_core
```

`sase_core` is deliberately synchronous, PyO3-free, and dependency-light — its own
module header says the crate "stays free of PyO3 types so later UniFFI/WASM/server work
can reuse the same logic." Putting an async HTTP client with connection pooling, SSE
streams, backoff timers, and a circuit breaker into it means adding tokio and reqwest to
the crate that compiles into every Python wheel, and hosting a tokio runtime inside a
PyO3 extension across the GIL. That is a real cost the predecessor did not price.

The `rust_core_backend_boundary` memory is still satisfied — better, in fact — by
putting the client in `sase_gateway`, which already has tokio and reqwest, and having
Python talk to it. §6 does exactly that.

---

## 6. Where the code lives: one binary, two roles

### 6.1 The shape

```text
  MacBook (kellys_mbp) — the viewer
  ┌──────────────────────────────────────────────────────────────────┐
  │ sase ace (Textual)                                               │
  │   FederatedAgentsDataProvider                                    │
  │     ├── DirectAgentsDataProvider   ← LOCAL ROWS, ALWAYS, ALONE   │
  │     └── unix socket ──┐                                          │
  └───────────────────────┼──────────────────────────────────────────┘
                          │ ~/.sase/run/<machine>/sase-daemon.sock
  ┌───────────────────────▼──────────────────────────────────────────┐
  │ sase_gateway  role=federate                                      │
  │   per-peer: connection · snapshot cache · revision cursor ·      │
  │             circuit breaker · idempotency journal · health       │
  └───────┬───────────────────────────────────┬──────────────────────┘
          │  WireGuard / MagicDNS             │
          │  loopback bind + tailscale serve  │
  ┌───────▼──────────────┐          ┌─────────▼────────────┐
  │ athena               │          │ apollo               │
  │ sase_gateway         │          │ sase_gateway         │
  │   role=serve         │          │   role=serve         │
  │   resident reads     │          │   resident reads     │
  │   resolution pass    │          │   resolution pass    │
  │   revision feed      │          │   revision feed      │
  └──────────────────────┘          └──────────────────────┘
       ▲ 10 ms                            ▲ 33 ms
       └── also reachable by `sase mobile` ┘ (whole fleet through one pairing)
```

One binary. `serve` exposes this machine; `federate` aggregates peers. Both default on,
so a machine that watches is also watchable.

### 6.2 Why a federate process rather than Python HTTP

| Concern | Federate daemon | Python client in ACE |
| --- | --- | --- |
| `rust_core_backend_boundary` | ✅ retry/cursor/idempotency in Rust | ❌ ~800 lines of backend logic in the TUI |
| Python dependency count (13, no HTTP client) | unchanged | stdlib `http.client` SSE hand-roll |
| tui_perf rule 2 (pump-free, cancellable) | one UDS read | N live SSE tasks inside the pump |
| Warm state across ACE restarts | ✅ | ❌ N handshakes + N snapshots per start |
| Phone sees the fleet | ✅ free | ❌ |
| New failure mode | a local process | none |

The last row is the honest cost, and §7.1 bounds it to exactly one consequence: remote
rows go stale. That is the same consequence the network already has.

### 6.3 Deployment, without inventing OS integration

- **Served machines** (athena, apollo — Linux) run `sase machine serve` supervised.
  `sase axe ensure install` already installs a **user systemd timer** for exactly this
  pattern (`src/sase/axe/_ensure_timer.py`); reuse it rather than writing a new
  supervisor.
- **The viewer** (MacBook — macOS, where SASE has no launchd integration today) does not
  need supervision. `machines.daemon: auto` makes ACE spawn the federate role as a
  tracked proc for its own lifetime, through the existing `_submit_tracked_proc()`
  machinery, and stop it at quit. It appears in the Procs tab like everything else.
- Set `machines.daemon: always` later if the phone should reach the MacBook. That is a
  launchd job and a separate, optional phase — not a prerequisite.

This asymmetry is deliberate: the platform that needs supervision already has it, and
the platform that lacks it does not need it.

### 6.4 Local transport is a unix socket, not a port

`DaemonConfig` already models `~/.sase/run/<host>/sase-daemon.sock` and nothing has ever
bound it (`crates/sase_gateway/src/daemon.rs` — there is no `UnixListener` in the
crate). Bind it. A 0600 socket makes filesystem permissions the authentication, needs no
token, cannot be reached from the tailnet by accident, and is trivially reachable from
Python: `http.client.HTTPConnection` with a pre-connected `sock` is about 30 stdlib
lines. Peer-to-peer traffic keeps the existing posture — loopback TCP published by
`tailscale serve`.

---

## 7. The design

### 7.1 Eight invariants

These are the contract. Each one is a test, and together they are why the design is
robust rather than merely functional.

**I1 — Local truth is never daemon-mediated.** Local rows always come from
`DirectAgentsDataProvider`. `FederatedAgentsDataProvider` composes local-direct plus
remote-cached. The daemon dying costs remote rows and nothing else. *This is the
specific lesson of the reverted sase-3e daemon (`5a65fa4fc`), encoded as structure.*

**I2 — A machine is the sole authority for its own agents.** No other machine may write
its state. The viewer's cache lives in `~/.sase/machines/<machine>/`, never in
`agent_artifact_index.sqlite`, never in `agent_name_registry.json`, never in
`dismissed_bundles/`. *This is what keeps the cache from becoming a second import leg.*

**I3 — Liveness is a resolved verdict, never an inference.** Only the owning machine
runs `is_process_running`. The wire carries `liveness: alive | dead | unknown` with the
timestamp it was resolved. The viewer never sees a remote PID as an actionable value.
*Without this, athena renders 1,843 phantom agents (§3.3).*

**I4 — Freshness is on every row, and staleness degrades status.** Each remote row
carries `machine`, `observed_at`, and `revision`. Past a bounded horizon (default 90 s,
= 3 missed reconciles), a cached `RUNNING` row renders `UNKNOWN`, not `RUNNING`. Stale
"running" invites a kill; stale "unknown" invites a refresh.

**I5 — Mutations are name-addressed, target-resolved, idempotent, and never queued.**
The client sends `(machine, global_name, operation, idempotency_key, observed_revision,
deadline)`. The target re-resolves by name — `kill_named_agent()`
(`src/sase/agent/running.py:45`) already returns typed `not_found` /
`already_completed` outcomes — journals before executing, and returns the journaled
result on replay. An unreachable machine yields an immediate typed failure. A kill that
executes two hours later is worse than a kill that visibly failed.

**I6 — Remote paths are inert.** `artifact_dir`, `project_dir`, and `project_file`
arrive as opaque `content_handle`s for remote records. No remote string ever reaches
`open()`, `unlink()`, `$EDITOR`, `tmux`, or `update_agent_artifact_index_for_marker_
mutation()`. Enforce with a typed `RemoteArtifactRef` that has no `__fspath__`, so the
failure is a type error at authoring time rather than a wrong file at runtime.

**I7 — One wire, one row model.** Remote records enter through the same
`AgentArtifactScanWire` the local scanner emits and are presented by the same loader.
A field that renders locally renders remotely, or neither does.

**I8 — Off is byte-for-byte today.** With the flag off,
`make_agents_data_provider()` returns `DirectAgentsDataProvider` and nothing else runs.

### 7.2 The wire

Extend, do not replace:

```jsonc
{
  "schema_version": 2,
  "machine": {
    "name": "athena",                 // id.machine_name — the one identity
    "identity": "gw_2f7c…",           // pinned at enrollment; endpoint auth
    "now": "2026-09-05T18:35:08-04:00",  // for skew-free durations
    "revision": 918447,               // monotonic; cursor + fence in one
    "runner_slots": {"max": 10, "occupied": 7}
  },
  "scan": { /* AgentArtifactScanWire, unchanged */ },
  "resolution": {
    "athena/gh_sase-org__sase/20260905182109": {
      "liveness": "alive",
      "resolved_at": "2026-09-05T18:35:08-04:00",
      "content_handle": "h_9f31c0…"   // replaces artifact_dir for remote rows
    }
  }
}
```

Machine-qualified global names (`bbugyi200.athena.research.1g.image`) already exist and
are already idempotent (`sase_core::machine_hood`, `agent_identity_facade`). No new
identity space. Displayed names stay local-spelled; the machine becomes a column, a
group, and a query facet.

### 7.3 The read path: resident, tiered, compressed

1. **Serve reads from `sase_core::agent_scan` in-process.** `query_agent_artifact_index`
   plus the resolution pass. 6.3 s → ~14 ms (§3.1). Delete the fork for reads; the
   `sase mobile agent-bridge` subprocess may remain for mutations through Phase 4.
2. **Tier by cost, not by uniformity.** *Live tier* (active + recent, ~18 KB gzipped):
   streamed, reconciled every 60 s. *History tier* (424 KB per 200 rows): fetched by
   cursor page on scroll or search, never on a tick. `AgentsViewport.requested_limit`
   and `AcePage.next_cursor` already express this.
3. **Push search down.** `compile_agent_query_pushdown()`
   (`src/sase/ace/agent_query/pushdown.py`) already emits a JSON
   `CandidateFilterWire = dict[str, object]` that `query_agent_artifact_index` consumes.
   Remote search is that dict, sent. Free, exact, and already tested.
4. **Turn on compression.** Add `tower-http`'s `compression-gzip` feature and the layer.
   16× on live payloads, 7.8× on history (§3.2). This is a one-line dependency change
   with the largest bandwidth effect in the design.
5. **Use the light record shape for windows.** `record_shape: "list"` already exists in
   the wire contract for exactly this.

### 7.4 The change feed: one counter does three jobs

Add a monotonic `revision` to the index `meta` table (which already holds versioned
state: `schema_version`, `dismissed_projection`), bump it on every write, and stamp each
row with the revision at which it changed. Then:

- **Cursor**: the client's `Last-Event-ID` is a revision.
- **Delta**: `SELECT … WHERE revision > :cursor` *is* the delta query. No event log to
  keep consistent with the store — the store is the log.
- **Fence**: a mutation carries the row revision it observed; the target refuses on
  drift for destructive operations.

Deletions need a bounded `deleted_revisions` tombstone table. A cursor older than the
oldest retained tombstone gets `ResyncRequired` — the event variant already exists in
`wire.rs` and the seam already models it (`AgentEventApplyResult.resync_required`,
`AceDeltaBatch.resync_hint`).

Then make the SSE stream real. Today `events()` (`routes.rs:764-788`) replays buffered
events and thereafter emits **only heartbeats**; `publish_agents_changed` is called from
four places, all of them the gateway's own mutation handlers (`routes.rs:854, 889, 925,
967`). An agent launched by a local TUI, a chop, or a finalizer emits nothing — a viewer
watching athena this way would miss essentially every real change. Drive the feed from
index writes: inotify on Linux (`fs_watcher.py` already does this via ctypes), polling
elsewhere. Keep the 60 s full reconcile as the safety net; a missed event self-heals
within a minute.

**Snapshot-plus-invalidation, not event sourcing.** Events are hints that trigger a
coalesced refresh; the bounded snapshot with its revision is the recovery mechanism.

### 7.5 Mutations

Typed operations only — kill, retry, wait/resume, answer-question, approve-gate, and
(last) launch — routed through the existing lifecycle facades. No exec endpoint, no
arbitrary cwd/env; the gateway already refuses these and must keep refusing.

The gateway's launch route today (`routes.rs:835`) has an audit line and no idempotency
key. A duplicate kill is harmless; **a duplicate launch burns a runner slot and real
money.** The journal is what makes retry-after-lost-response safe, and it is the
gate on the whole mutation phase.

**The target machine admits its own launches.** `max_running_agents` is host-wide
(`default_config.yml:38`) and the slot state is already in the wire (§7.2). The viewer
proposes; the target's existing gate accepts, queues, or refuses. A client-side
scheduler working from a 60 s-old snapshot would oversubscribe. Surfacing each
machine's live slot count in the launch picker is enough for intelligent routing.

### 7.6 Offline machines, now that the git plane is gone

The viewer keeps a per-machine snapshot cache at `~/.sase/machines/<machine>/`:
last snapshot, its revision, and `observed_at`. On startup, ACE paints cached remote
rows immediately (tui_perf rule 5, rule 9) and reconciles behind them.

The constraints that keep this from becoming the import leg the user just deleted, and
that make it consistent with `agents-sync-publish-only`:

| Import leg (deleted) | Snapshot cache (proposed) |
| --- | --- |
| Wrote local **agent artifacts** | Writes one opaque blob per machine |
| Claimed names in `agent_name_registry.json` | Never allocates a name |
| Created dismissed bundles + revival groups | No local objects at all |
| Rows persisted forever as `STOPPED` | Rows expire; status degrades to `UNKNOWN` (I4) |
| Continuously reconciling engine, silent failure | Last-write cache; staleness is *rendered* |
| Needed transactions, quarantine, v1→v2 adoption | Overwrite-or-discard; no merge semantics |

A cache is the right mechanism for "show me what I last saw." Git replication was an
extraordinarily expensive way to obtain one — that is precisely what the collaboration
research concluded, and it explicitly recommended this amendment.

Machine link states are explicit and visible: `online` · `reconnecting` · `stale` ·
`unauthorized` · `incompatible` · `offline`.

### 7.7 TUI integration: tui_perf rules are the acceptance criteria

- All daemon I/O in `spawn_pump_free_task()`, cancelled by `cancel_pump_free_tasks()` at
  teardown (rule 2). Never in a timer or message handler.
- Cached rows on the first frame with staleness badges; reconcile in the background
  (rule 5). First paint never waits on a network round trip (rule 9).
- Deltas land through `patch_row()` / `try_remove_rows()`, never a list rebuild
  (rule 6).
- Ticks revalidate the live tier; history recomputes on a much longer cadence (rule 10).
- Idle ticks with no machine revision change reload no surfaces (rule 14) — the revision
  cursor makes this exact, which is *better* than the local stat-token heuristic.
- Remote mutations are tracked procs via `_submit_tracked_proc()` (rule 3), so they
  appear in the Procs tab, dedup, and count at quit.
- Re-capture selection after every await (rule 4) — remote latency widens this window.

### 7.8 Security posture

Inherit `docs/mobile_mvp_runbook.md` unchanged: loopback bind, `tailscale serve --bg`
for tailnet-only publication with managed TLS, **never Funnel**, never
`--allow-non-loopback`. Layer authorization rather than trusting tailnet membership: a
least-privilege Tailscale grant restricting which devices reach the port, plus the
gateway's own scoped, hashed, revocable per-viewer bearer token. `Tailscale-User-Login`
headers are trustworthy *only* because the backend is reachable solely through Serve on
loopback — which is why the loopback rule is load-bearing, not stylistic.

Pin the peer's gateway identity at enrollment and verify it on every connect (§7.2), so
a MagicDNS rename or IP reassignment can never silently substitute a different machine
as the target of a `kill`. Peers are configured explicitly; a newly visible tailnet
device is never implicitly trusted. No discovery.

This stays **single-user**, per `sase_collaboration_architecture` §5.3. Crossing a user
boundary turns a UX problem into an authorization problem and is a different feature.

### 7.9 Scope honesty: what "the same ways" actually decomposes into

| Class | Examples | Where it runs |
| --- | --- | --- |
| List / state / tree | status, model, duration, clan, family, tribe | Remote records → local presentation |
| Search / filter | agent queries, facets | Pushed down to the remote index (§7.3) |
| Lifecycle mutations | kill, retry, wait/resume, launch | Remote, name-addressed, journaled |
| Attention | answer question, approve gate, notifications | **Remote routes already exist** (§1.2) |
| Content reads | chat, response, diff, artifacts | Remote by handle, digest-cached |
| Viewer-local state | folds, marks, dismissal, tribe, query profiles | Local, keyed by global name |
| Genuinely local | `tmux attach`, `$EDITOR` on workspace files | Refuse with an explanation, or `ssh -t` |

Viewer-local state stays on the viewer keyed by global name. "Dismissed" is a local view
choice, not a fact about the remote machine — the same separation
`athena_agent_sync_repair` established. Remote tmux attach is honestly a different
operation; the UI should say so rather than pretend.

### 7.10 Naming and CLI

Use **machine**, matching `id.machine_name` and `machine_hood`. Never "node": the
glossary defines *Sase Node* as one row of the Agents tab's agent tree, and *Agent Node*
sits inside that — a collision in the exact surface this feature touches.

Per `cli_rules.md` (alphabetical, every long option gets a short alias, no required
options, `list` is the bare default):

```text
sase machine            → delegates to `sase machine list`
sase machine add <name> <url>    Enroll a peer, pin its identity, store its token
sase machine check [name]        Probe reachability, auth, and schema compatibility
sase machine list                Peers with link state, revision lag, and slot counts
sase machine remove <name>       Forget a peer and drop its cache
sase machine serve               Run the serve role in the foreground
sase machine status              Local daemon roles, sockets, peers, cache ages
sase machine stop                Stop the local daemon
```

`sase mobile gateway start` becomes a deprecated alias behind a `sunset` flag, per
`sase_flags.md`. Note that the gateway binary is not shipped today — it resolves from
`PATH` or a sibling dev build (`src/sase/integrations/mobile_gateway.py:287-295`), and
`sase doctor` already reports its absence. Shipping it in the `sase-core-rs` wheel is a
Phase 0 prerequisite, not a detail.

---

## 8. Phasing

Each phase is independently useful, independently revertible, and behind a `beta` flag
per `sase/memory/sase_flags.md`.

| Phase | Deliverable | Why here |
| --- | --- | --- |
| **0** | Ship the gateway binary in the wheel. `sase machine` CLI + `machines:` config. Bind the UDS. Add gzip. Fault harness in `sase_gateway`: a fake peer that delays, disconnects, duplicates, reorders, overflows, and restarts with a new epoch. | Nothing below is testable without a peer you can break on purpose |
| **1** | **Resolution/presentation split.** Make the snapshot loaders total: fence the ~50 call sites from §2.2 behind a `RemoteArtifactRef` type, move liveness and marker repair to an explicit resolution pass. | Pure local win — faster, testable without a filesystem, retires the legacy loader path. Do it before any network exists |
| **2** | Resident Rust reads in the serve role (6.3 s → 14 ms). Drop the fork from reads. | The change everything else depends on |
| **3** | Index `revision` counter + tombstones; real `AgentsChanged { revision }` feed; `ResyncRequired` on gaps. | Cursor, delta, and fence from one mechanism |
| **4** | Federate role: per-peer connections, snapshot cache, cursors, circuit breakers. `FederatedAgentsDataProvider` behind the existing seam. Machine column/group/filter, staleness badges, link states. **Read-only.** | **The user's core ask.** Blast radius is a wrong row, not a wrong kill |
| **5** | Mutations: kill, retry, wait/resume — idempotency journal, host-side resolution, revision fencing, target-side admission. Gated on §9. | The safety work is the feature here |
| **6** | Attention plane: answer questions and approve gates on remote agents. | Routes already exist (§1.2); mostly UI |
| **7** | Content by handle: chat, response, diff, artifacts, digest-validated cache. | Deepens the panel, needs the handle model from Phase 4 |
| **8** | Remote launch with a machine picker showing live slot counts. | Most dangerous mutation; last |
| **9** | Phone sees the fleet: point `sase mobile` at a federate endpoint. | Free once Phase 4 lands; validates the contract |

Phases 1–3 pay for themselves at N=1 with no network involved. Phase 4 is the milestone
to optimize for.

---

## 9. Fault-injection gates for the mutation phase

Phase 5 does not ship until automated tests demonstrate all of:

1. A lost launch response, retried with the same idempotency key, yields **exactly one**
   agent.
2. A disconnect mid-kill recovers the same terminal result from the journal.
3. A stale kill against a reused name or recycled PID returns a conflict, never a wrong
   kill.
4. Daemon restart forces a correct epoch-based resync; duplicated, reordered, and
   overflowed events all converge to the snapshot.
5. One hung peer leaves local rows and every healthy peer fully responsive, with first
   paint unaffected.
6. Sleep/wake and direct↔DERP transitions recover without a TUI restart.
7. A cached `RUNNING` row past the staleness horizon renders `UNKNOWN` and refuses
   mutation (I4).
8. No remote path reaches `open()`, `unlink()`, or the local artifact index — asserted
   by type, and by a test that hands the loader a record whose paths point at a real
   local file that must remain untouched (I6).
9. Older and newer client/server schema versions negotiate capabilities cleanly;
   revoked tokens and denied grants stop access.
10. Turning the daemon off leaves local CLI and ACE **fully** functional (I1, I8).

---

## 10. Costs and risks accepted

- **A new supervised process on served machines.** Mitigated by reusing the existing
  `sase axe ensure` systemd-timer pattern, and by I1 keeping the failure blast radius to
  remote rows.
- **A second consumer of `AgentArtifactScanWire`.** The contract now has a network
  compatibility requirement, so it needs a committed snapshot test like the gateway's
  `contract.rs`. This is a genuine new constraint on a previously in-process type.
- **Phase 1 touches ~50 call sites in load-bearing loader code.** It is the riskiest
  phase and it ships with no user-visible feature. That is deliberate: doing it under
  the pressure of a half-working network feature is how this goes wrong.
- **macOS has no inotify** — `fs_watcher.py:9-11` silently declines to start there. The
  MacBook is already in the polling regime today, so remote sources add no new failure
  mode on the viewer; Linux peers drive genuine event feeds.
- **The 195 MB index will keep growing.** Tiering (§7.3) bounds what crosses the wire,
  but athena's index deserves its own retention work regardless.

---

## 11. What would reopen this decision

- **More than ~10 machines, or several non-TUI consumers** wanting the same feed: N-way
  federation stops being simple and NATS leaf nodes become the better answer. The JSON
  records port largely unchanged.
- **Cross-machine agent-to-agent coordination** — one machine's agent blocking on
  another's — a genuinely different topology that would justify a broker.
- **A second user**, or agents on hardware you do not own (cf.
  `temporary_high_capacity_test_machine`). That is a multi-tenant scheduler with a real
  permission model, and `sase_collaboration_architecture` §5.3 says explicitly not to
  reach it by widening this.
- **Sub-second cross-machine event latency as a requirement** rather than a nicety.
- **Tailscale stops being the substrate** — encryption, identity, and NAT traversal come
  back onto SASE's budget and the transport calculus changes.

---

## 12. Open questions for the user

1. **Should the MacBook run a supervised daemon, or an ACE-lifetime child?** §6.3
   recommends the child (no launchd work) and defers the daemon to whenever the phone
   should reach the MacBook. Confirm the phone is not an immediate goal.
2. **Remote `tmux attach`: refuse with an explanation, or shell out to
   `ssh -t <machine> tmux attach`?** The latter is useful and is honestly a different
   operation. §7.9 assumes refuse-with-explanation plus an opt-in escape hatch.
3. **Is dismissal per-viewer or fleet-wide?** §7.9 argues per-viewer, consistent with
   how imported rows were treated. A single-user tailnet might genuinely prefer
   dismiss-everywhere — but that is a *mutation* on the remote machine and belongs in
   Phase 5 if so.
4. **Should remote launch be allowed on a machine where the project is not checked
   out?** Dodgeable until Phase 8, since athena, apollo, and the MacBook share projects
   today.
5. **Staleness horizon: is 90 s right?** It trades phantom-`RUNNING` risk against badge
   churn on a flaky link. It should be a config field, not a flag (users choose it
   forever), but the default matters.

---

## 13. Sources

**Repo evidence**, verified on `sase` @ `302e6d643` and `sase-core` @ `fe9a643`:
`crates/sase_gateway/src/{routes.rs,host_bridge.rs,daemon.rs,server.rs,wire.rs,contract.rs}`,
`crates/sase_gateway/Cargo.toml`, `crates/sase_core/src/agent_scan/{mod.rs,index.rs}`,
`crates/sase_core/Cargo.toml`, `crates/sase_core_py/Cargo.toml`,
`src/sase/ace/tui/provider_contract.py`,
`src/sase/ace/tui/data_providers/{_types.py,_direct.py,_factory.py,_settings.py,_handles.py}`,
`src/sase/ace/tui/models/agent_loader.py`, `src/sase/ace/tui/models/_agent_state.py`,
`src/sase/ace/tui/models/_loaders/{_done_snapshot_loaders.py,_done_filesystem_loaders.py,_running_loaders.py,_done_common.py}`,
`src/sase/ace/agent_query/pushdown.py`, `src/sase/core/agent_scan_wire_records.py`,
`src/sase/core/agent_identity_facade.py`, `src/sase/agent/running.py:45`,
`src/sase/integrations/mobile_gateway.py:287-295`, `src/sase/axe/_ensure_timer.py`,
`src/sase/ace/tui/util/fs_watcher.py`, `src/sase/default_config.yml:38,129-142`,
`pyproject.toml`, `docs/mobile_mvp_runbook.md`, revert commit `5a65fa4fc`, bead
`sase-ws`, decisions `agents-sync-publish-only` and `rust-core-required`, core memory
`rust_core_backend_boundary`, reference memory `tui_perf.md`, `sase_flags.md`,
`cli_rules.md`, glossary strands `node` and `hood`.

**Live measurements** (athena, 2026-09-05): `sase agent list --json`,
`sase mobile agent-bridge list-agents`, `tailscale ping apollo|kellys-macbook-pro`,
read-only SQLite probes against `~/.sase/agent_artifact_index.sqlite`.

**Prior research**: `research:202609/tailnet_agent_fleet/tailnet_agent_fleet.md`,
`research:202609/sase_collaboration_architecture.md`.

**External**:
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) ·
[MagicDNS](https://tailscale.com/docs/features/magicdns) ·
[connection types](https://tailscale.com/docs/reference/connection-types) ·
[Tailscale identity](https://tailscale.com/docs/concepts/tailscale-identity) ·
[WHATWG Server-Sent Events](https://html.spec.whatwg.org/dev/server-sent-events.html) ·
[Axum SSE](https://docs.rs/axum/latest/axum/response/sse/) ·
[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) ·
[IETF Idempotency-Key draft](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-idempotency-key-header-07)

---

## 14. Recommended solution

**Extend `sase_gateway` into one supervised binary with a `serve` role and a `federate`
role; make the fleet wire the `AgentArtifactScanWire` contract Rust and Python already
share; and consume it through the ACE provider seam that already exists. Add no new
messaging framework, no new row model, and no new identity space.**

The work, in the order it should happen:

1. **Split resolution from presentation in the ACE loader** (Phase 1). This is the real
   feature. Liveness checks, marker repair, and index mutation move into an explicit
   pass that only the owning machine runs; presentation becomes a total function of
   `AgentArtifactScanWire`. Do it before any network code exists — it is a local win on
   its own, and doing it later means debugging it through a socket.
2. **Make reads resident** in the serve role: 6.3 s → 14 ms, measured, on the machine
   that matters most.
3. **Add one monotonic `revision`** to the artifact index and let it be the cursor, the
   delta query, and the mutation fence simultaneously. Drive SSE from index writes so
   the feed reports changes the gateway did not cause — today it reports essentially
   nothing.
4. **Ship read-only fleet visibility** through `FederatedAgentsDataProvider`, with local
   rows always served directly, remote rows always stamped with machine and freshness,
   and cached rows degrading to `UNKNOWN` rather than lying about `RUNNING`.
5. **Only then enable mutations**, behind an idempotency journal, host-side name
   resolution, revision fencing, target-side launch admission, and the ten fault gates
   in §9.

This is reliable because every failure has one bounded consequence — the daemon dying
costs remote rows, a peer going offline costs freshness, a lost response costs a retry
that cannot duplicate. It is robust because the invariants are enforced by types and
ownership rather than by discipline: a remote path has no `__fspath__`, a remote PID has
no liveness field, a remote machine's state has no local writer. And it is beautiful
because the remote row and the local row are built by the same function from the same
contract — parity is not a checklist anyone has to maintain, it is the shape of the
thing.
