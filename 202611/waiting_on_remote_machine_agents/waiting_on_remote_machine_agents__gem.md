# Research Report: Cross-Machine Agent Wait Directives in SASE

**Author:** Researcher `gem` (5-Researcher Swarm)  
**Date:** November 2026  
**Target Output File:** `sase/repos/research/202611/remote_machine_agent_wait_directives__gem.md`  
**Artifact Label:** `research:202611/remote_machine_agent_wait_directives__gem.md`

---

## Executive Summary

This report evaluates the proposal to extend SASE's `%wait` directive across remote enrolled machines—specifically enabling an agent on controller machine `apollo` to wait for an agent `foobar` on target machine `athena` via directives like `%wait:athena.foobar`.

### Key Findings
1. **Feasibility:** Cross-machine waiting is technically viable within SASE's current architecture by leveraging the existing `sase_gateway` HTTP API and the local `sase_federation_worker` IPC facade.
2. **Syntax Conflict:** The dot-separated shorthand syntax (`%wait:athena.foobar`) is ambiguous in SASE because dots are legal and widely used in agent names (e.g., `research.3l.gem`), clan-member addressing (`<clan>.<member>`), and machine hostnames/aliases (e.g., `mac.local`). We recommend adopting an explicit keyword syntax `%wait(foobar, machine=athena)` alongside a slash or colon shorthand (`%wait:athena/foobar` or `%wait:athena:foobar`).
3. **Architectural Fit:** Resolution should be owned by the background scheduler chop (`wait_checks`) on the controller machine via `FederationFacade`, rather than having parked runner processes perform distributed network polling. The local runner continues its existing contract: park, wait for local `ready.json`, and re-exec.
4. **Architectural Critique:** While cross-machine `%wait` provides convenient ad-hoc workflow chaining, synchronous cross-machine process holding is fraught with distributed systems failure modes (unreachable machines, silent hangs, network partitions, purged history, and unshared artifact states). For durable or multi-step distributed workflows, cross-machine coordination is better solved by synchronizing durable beads (`%wait(bead=...)`), with remote `%wait` reserved for lightweight ephemeral turn sequencing.

---

## 1. Current SASE Architecture & Capabilities

To evaluate this proposal accurately, we first examined the existing codebase across `sase`, `sase-core`, and related subsystem documentation.

### 1.1 Remote Machine Enrollment & Fleet Infrastructure
Remote machine management is governed by `sase machine init`, `sase machine add`, and `sase machine bootstrap`:
- **Gateway (`sase_gateway`):** A Rust daemon running on enrolled target machines (`sase-core/crates/sase_gateway`). It binds to `127.0.0.1:7629` and is exposed within a private tailnet (via Tailscale Serve with HTTPS).
- **Authentication & Enrollment:**
  - Target generates a single-use secret token with `sase machine bootstrap --json`.
  - Controller initializes enrollment via `sase machine init -B <bootstrap.json>`, calling `/api/fleet/v1/enroll`.
  - Machine records are stored locally in configuration under `dispatch.machines.<alias>` (including `endpoint`, `pinned_installation_id`, `credential_ref`, and `tls`), while secrets reside in protected state.
- **Federation Worker (`sase_federation_worker` & `FederationFacade`):**
  - A local supervised background worker (`sase-core/crates/sase_gateway/src/federation_worker`) manages pooled HTTPS connections to remote gateways.
  - Python code talks to the worker over a blocking Unix domain socket (`_ipc.py`) using `FederationFacade` (`src/sase/dispatch/federation/_facade.py`).
  - Available read operations include: `summary()`, `catalog()`, `catalog_hosts()`, `detail()`, and `batch()`.
- **Current Remote Execution Constraints:**
  - `%dispatch:<alias>` launches an agent on an enrolled machine.
  - As documented in `docs/reference/integrations/remote-dispatch.md`:
    > *"V1 remote launch does not combine with `%wait`, `%queue`, `%clan`, or `%hold`."*
    > *"The controller strips only the dispatch selector, so other launch directives are processed on the target."*

### 1.2 Local Wait Execution Mechanics
The local waiting mechanism in SASE follows a clean decoupled pattern:
1. **Directive Extraction (`src/sase/macro/`):**
   - The user prompt is parsed by `_directive_extract.py`. Directives like `%wait:agent_a` or `%wait(agent_b, target=turn)` are extracted and normalized into structured launch metadata.
2. **Runner Barrier (`src/sase/axe/run_agent_wait.py`):**
   - The spawned runner process initializes and enters `wait_for_dependencies()`.
   - If dependencies are not already satisfied, it writes `waiting.json` into its artifact directory, marks lifecycle phase as `"waiting"`, calls `release_idle_memory()`, and enters a sleep loop checking for `ready.json`.
3. **Background Resolution Chop (`wait_checks`):**
   - The background AXE scheduler runs the `wait_checks` lumberjack chop periodically (`src/sase/scripts/_chop_wait_checks_run.py`).
   - `wait_checks` scans all active `waiting.json` markers across the filesystem, builds a `WaitDependencyIndex` from disk metadata (`agent_meta.json`, `done.json`), and determines whether the dependencies are in `WAIT_SUCCESS_OUTCOMES` (`{"completed", "noop", "epic_approved", "plan_committed"}`).
   - If satisfied, `wait_checks` writes `ready.json` (`publish_ready_marker`).
   - If a dependency fails or terminates abnormally (`FAILURE_OUTCOMES = {"failed", "killed", "stopped", "epic_launch_failed"}`), `wait_checks` flags a terminal blocker and posts a notification.
4. **Resumption:**
   - The waiting runner detects `ready.json`, records `wait_completed_at`, refreshes its runner code (`refresh_runner_code_after_wait`), requests a queue slot (`wait_for_runner_slot`), and launches the model turn.

---

## 2. Critique of the Proposal: Is This a Good Idea?

The user asks: *"Is this a good idea? Would you take a different approach? Make any adjustments to the requirements that you think are justified..."*

### 2.1 The Value & Intuition
The desire for cross-machine `%wait` is understandable:
- **Heterogeneous Hardware:** Bryan's setup features machines with distinct hardware profiles (e.g. desktop/server `athena` vs laptop `apollo`). Running a heavy build, long benchmark, or GPU training task on `athena` and wanting an analysis or follow-up turn to run automatically on `apollo` once `athena` completes is a natural workflow.
- **Ergonomic Familiarity:** Users and agents already understand `%wait:<name>`. Reusing `%wait` across machines avoids introducing new mental models or complex pipeline definitions.

### 2.2 Critical Vulnerabilities & Distributed Systems Fallacies
Despite the ergonomic appeal, introducing cross-machine waiting into an architecture built around local ephemeral workspaces introduces serious risks:

#### 1. The Fallacy of the Local Filesystem
Local `%wait` is reliable because local filesystem reads cannot partition. Atomic writes to `ready.json` and local directory checks (`stat()`) never fail due to network dropped packets, DNS failures, or expired TLS certs.
In contrast, a remote machine may:
- Go to sleep or lose Wi-Fi/Tailscale connection.
- Have its `sase_gateway` process killed or restarted.
- Crash or reboot mid-run.
If the controller runner on `apollo` is parked waiting for `athena.foobar`, network loss causes `apollo` to hang indefinitely unless proactive timeouts, health heartbeats, and failure classifications are explicitly built.

#### 2. Resource Exhaustion from Parked Processes
In SASE, waiting agents are active OS processes. Although `release_idle_memory()` minimizes RAM consumption, the process still holds:
- An OS PID and open file descriptors.
- A lock or reservation on an ephemeral numbered workspace (e.g. `sase_16`).
- A slot in the local runner accounting table.
Holding an ephemeral workspace on `apollo` for hours waiting for a remote machine that might be offline degrades local throughput.

#### 3. The "Target Existence" and Timing Window Race
In local SASE, `wait_checks` looks at recent artifact directories on disk. If agent `foobar` hasn't started yet, `wait_checks` assumes it might start soon.
On a remote machine:
- What if `foobar` is a typo?
- What if `foobar` ran yesterday, finished, and was already pruned from the gateway's bounded active window (7 days / 200 items)?
- What if `foobar` was dispatched to `athena` under a different project name?
Without a mechanism to verify that `athena` actually knows about `foobar` or plans to run it, `apollo` will sit in `"waiting"` forever.

#### 4. Asymmetric State & Artifact Silos
When an agent finishes locally on `apollo`, its git commits, branches, and artifact files are on `apollo`. A downstream agent waiting on `apollo` can read those outputs immediately.
When agent `foobar` completes on `athena`:
- Its git commits are in `athena`'s local repo checkout unless pushed to an upstream remote (e.g. GitHub).
- Its generated artifact files, test logs, and `sase var` output variables reside in `athena`'s `~/.sase/projects/...` directory.
- If an agent on `apollo` wakes up because `athena.foobar` completed, but `athena` never pushed its branch, `apollo` will attempt to build or review non-existent code!

#### 5. Distributed Deadlock & Cycles
If agent A on `apollo` has `%wait:athena.B`, and agent B on `athena` has `%wait:apollo.A` (or a 3-machine cycle), neither machine has global dependency visibility. Local cycle detection cannot see across the network boundary, creating an undetected distributed deadlock.

---

## 3. Justified Adjustments to the Requirements

Based on the critique above, several adjustments to the user's initial specification are strongly justified:

### 3.1 Requirement Adjustment 1: Disambiguate Directive Syntax (Do NOT use bare dot notation)
The user suggested:
```
%wait:athena.foobar
```
**Why this is problematic:**
- SASE allows dots in agent names: e.g. `research.3l.cdx`, `foo.bar`, `agent.v2`.
- SASE uses dots in clan member notation: `<clan>.<member>`.
- Machine aliases can contain dots, hyphens, and underscores (`_ALIAS_RE = ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`), so a machine could be named `mac.local` or `server.lan`.
If someone writes `%wait:athena.foobar.baz`, the parser cannot reliably determine if this refers to machine `athena`, agent `foobar.baz`, or machine `athena.foobar`, agent `baz`, or a clan `athena` on the local machine.

**Recommended Adjusted Syntax:**
1. **Primary Structured Syntax (Preferred):**
   ```
   %wait(foobar, machine=athena)
   ```
   or
   ```
   %wait(agent=foobar, machine=athena)
   ```
   This fits SASE's existing macro argument grammar perfectly (matching `%wait(planner, target=turn)` and `%id(..., session=...)`) and leaves zero ambiguity.
2. **Shorthand Syntax Options:**
   - **Slash notation:** `%wait:athena/foobar` (matches git `remote/branch`, GitHub `owner/repo`, and macro `ns/name`).
   - **Colon notation:** `%wait:athena:foobar` (matches SASE memory strand `web:keyword`, e.g. `glossary:stitch`).
   - *If dot notation must be supported for backward compatibility:* The parser must look up the prefix against `dispatch.machines`. If the prefix exactly matches an enrolled machine alias, treat it as remote; otherwise treat it as a local agent or clan. However, slash or keyword notation should remain canonical.

### 3.2 Requirement Adjustment 2: Explicit Target Granularity (Turn vs Session)
In SASE, multi-turn interactions (plan chains, retries, forks) belong to an `agent_session`. Local `%wait` supports `target=session` (default) vs `target=turn`.
Remote wait must support this distinction:
```
%wait(foobar, machine=athena, target=turn)
```
Waiting for a single turn should unblock when turn 0 completes; waiting for a session waits until the entire remote session settles.

### 3.3 Requirement Adjustment 3: Mandatory Remote Wait Timeout & Liveness Protection
Local waits can afford to wait indefinitely because local processes are supervised by the local AXE scheduler. Remote waits must guard against stranded processes.
- Add an optional `timeout=` parameter:
  ```
  %wait(foobar, machine=athena, timeout=30m)
  ```
- If `timeout` is omitted, enforce a sensible system ceiling (e.g. 4 hours) or require an explicit `timeout=none` to wait indefinitely.
- If target `athena` is unreachable (network timeout / gateway error) for longer than a configurable grace period (e.g. 10 minutes), the waiter should transition to a `remote_unreachable` diagnostic state and trigger a user notification via `sase notify`, rather than failing silently.

### 3.4 Requirement Adjustment 4: Require Published / Shared Upstream Precondition
If `foobar` on `athena` was launched to perform code edits, waiting for `foobar` on `apollo` is only useful if `foobar`'s changes are pushed to git.
The documentation and system prompt instructions should clarify:
> *Remote `%wait` guarantees temporal ordering, but does NOT automatically synchronize git branches or artifact files across machines. If the downstream agent requires code changes, the upstream remote agent must be configured with a rollover macro (`#commit`, `#pr`, etc.) to publish its commits before completion.*

---

## 4. Architectural Alternatives

We evaluated four implementation approaches:

| Approach | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **Approach 1: Scheduler Chop (`wait_checks`) via Federation Worker** | `wait_checks` scans remote wait markers, queries `FederationFacade`, and writes local `ready.json`. | Zero runner changes; batching across waiters; leverages existing federation worker & auth; consistent with local wait design. | Polling latency bounded by chop interval (~2–5s); requires federation worker. | **Recommended** |
| **Approach 2: Event-Driven Push via SSE (`/api/fleet/v1/events`)** | Federation worker maintains SSE stream to remote gateway; lifecycle events trigger local wait release. | Sub-second latency; zero query load on remote gateway when idle. | High complexity; network reconnections can drop events; still requires poll fallback. | **Good Phase 2 optimization** |
| **Approach 3: Direct Runner Polling** | Each waiting runner process queries `athena`'s gateway directly. | Simple to prototype in one file. | Serious thundering herd; network socket sprawl; bypasses scheduler control plane; breaks SASE architectural boundaries. | **Rejected** |
| **Approach 4: Decoupled Coordination via Beads** | Coordinate across machines via SASE task beads (`%wait(bead=...)`) and git/sidecar sync. | Durable, decoupled, survives machine reboots; doesn't care which machine ran what. | Heavier weight; requires filing a bead for quick ad-hoc commands. | **Complementary (Best for production pipelines)** |

---

## 5. Recommended Solution Specification

We recommend **Approach 1** with the syntax adjustments from Section 3. Below is the technical specification for implementing this feature cleanly across SASE.

```
+-----------------------------------------------------------------------------------+
| CONTROLLER MACHINE (apollo)                                                       |
|                                                                                   |
|  [ User Prompt ] ---> %wait(foobar, machine=athena)                               |
|          |                                                                        |
|          v                                                                        |
|  [ Directive Parser ] ---> writes waiting.json                                    |
|          |                 { "waiting_for_remote": [                              |
|          |                     {"machine": "athena", "agent": "foobar"}           |
|          |                 ]}                                                     |
|          v                                                                        |
|  [ Runner Process ] ---> parks & polls for ready.json                             |
|                                                                                   |
|  [ AXE Scheduler: wait_checks chop ]                                              |
|          |                                                                        |
|          +---> reads waiting.json                                                 |
|          +---> calls FederationFacade.catalog_hosts() / batch_lookup()            |
|          |            |                                                           |
|          |            v                                                           |
|          |     [ sase_federation_worker (Rust) ]                                  |
|          |            |                                                           |
|          |            | HTTPS (Tailscale)                                         |
+----------|------------|-----------------------------------------------------------+
           |            |
           |            v
+----------|------------------------------------------------------------------------+
| TARGET MACHINE (athena)                                                           |
|          |                                                                        |
|          |   [ sase_gateway :7629 ]                                               |
|          |            |                                                           |
|          |            +---> /api/fleet/v1/batch or /catalog                       |
|          |            +---> queries local agent metadata                          |
|          |            +---> returns { "status": "completed", "outcome": "done" }  |
|          |                                                                        |
+----------|------------------------------------------------------------------------+
           |
           v (when athena.foobar is completed)
 [ wait_checks writes ready.json ]
           |
           v
 [ Runner Process wakes up & launches ]
```

### 5.1 Component Details

#### 1. Macro & Directive Parser (`src/sase/macro/`)
- In `src/sase/macro/_directive_types.py`:
  - Extend wait structures to support remote targets:
    ```python
    @dataclass(frozen=True)
    class RemoteWaitTarget:
        machine: str
        agent: str
        target: str = "session"  # "turn" or "session"
        project: str | None = None
        timeout: float | None = None
    ```
- In `src/sase/macro/_directive_collect_main.py`:
  - Add `"machine"` to `supported_keys` in `%wait(...)`:
    ```python
    supported_keys = {
        "agent", "bead", "for_epic", "hood", "proc",
        "target", "time", "unit", "machine", "timeout",
    }
    ```
- In `src/sase/macro/_directive_values.py`:
  - In `resolve_wait_agent_args()`, inspect positional arguments:
    - If argument contains `/` (e.g. `athena/foobar`), split into `(machine, agent)`.
    - If argument contains `:` (e.g. `athena:foobar`), split into `(machine, agent)`.
    - Validate `machine` against `load_dispatch_config().machines`.

#### 2. Waiting Marker Representation (`waiting.json`)
- In `src/sase/axe/run_agent_wait.py`:
  - When writing `waiting.json`, include structured remote dependencies:
    ```json
    {
      "waiting_for": [],
      "waiting_for_remote": [
        {
          "machine": "athena",
          "agent": "foobar",
          "target": "session",
          "timeout_seconds": 3600
        }
      ]
    }
    ```
  - The local runner's wait loop (`while not os.path.exists(ready_path): sleep(2)`) requires **zero changes**. It still simply waits for `ready.json`.

#### 3. Gateway Enhancements (`sase-core/crates/sase_gateway`)
- The existing `/api/fleet/v1/catalog` and `/api/fleet/v1/batch` routes in `sase_gateway` already return agent status records (`FleetCatalogRowWire`), including `logical_locator`, `lifecycle` (`Terminal`, `Failed`, etc.), and `outcome` (`completed`, `failed`).
- To make remote wait lookups fast and minimal, ensure `/api/fleet/v1/batch` supports exact logical locator lookups by `agent_name` or `agent_id` with `include_terminal: true`.

#### 4. Scheduler Resolution in `wait_checks` (`src/sase/scripts/_chop_wait_checks_run_waiters.py`)
- When `process_one_waiter()` parses `LiveWaiter`:
  - If `waiting_for_remote` entries exist:
    - Group remote targets by machine alias.
    - Query `FederationFacade.catalog_sync()` or `batch_lookup()` for those specific machine aliases.
    - Evaluate whether the target row on that machine has reached terminal status:
      - If remote row status is `completed` / `done`: Mark that remote dependency resolved.
      - If remote row status is `failed`, `killed`, or `stopped`: Flag as a remote terminal blocker, log diagnostic, and alert the user.
      - If remote machine is offline or returns an error: Count consecutive failures. If grace period expires, trigger a stranded wait notification (`upsert_stranded_remote_wait_notification`).
- Once all local AND remote dependencies are resolved:
  - Write `ready.json` with payload:
    ```json
    {
      "resolved_deps": ["athena:foobar"],
      "released_by": "wait_checks"
    }
    ```

---

## 6. Implementation Roadmap & Milestones

1. **Milestone 1: Directive Parsing & Syntax Normalization**
   - Implement `machine=` keyword arg and shorthand parsing (`athena/foobar` / `athena:foobar`) in `src/sase/macro/`.
   - Add unit tests verifying parsing, validation against configured machine aliases, and error messages for unknown machines.
2. **Milestone 2: `waiting.json` Marker Schema & Runner Serialization**
   - Update `run_agent_wait.py` to record `waiting_for_remote` in `waiting.json`.
   - Ensure `sase agent status` and TUI prompt panel reflect remote wait dependencies cleanly (e.g. `Waiting for athena:foobar`).
3. **Milestone 3: `wait_checks` Remote Resolution**
   - Implement remote dependency evaluation in `_chop_wait_checks_run_waiters.py` using `FederationFacade`.
   - Add batching and local caching to avoid duplicate gateway calls on each tick.
4. **Milestone 4: Error Handling & Resilience**
   - Add terminal blocker notifications for failed remote agents.
   - Add timeout enforcement and unreachable-host handling.
   - Document the feature in `docs/reference/integrations/remote-dispatch.md` and `docs/reference/agents/macros.md`.

---

## 7. Conclusion

Extending `%wait` to remote machines is a natural and high-value enhancement for SASE, provided it is implemented via the centralized scheduler control plane (`wait_checks` + `FederationFacade`) rather than ad-hoc runner polling. Crucially, avoiding dot-delimited shorthand in favor of `%wait(foobar, machine=athena)` or `%wait:athena/foobar` prevents syntax collisions with existing agent names and clans. Combining this with mandatory timeouts and clear terminal failure reporting ensures the distributed wait remains robust, predictable, and resilient.
