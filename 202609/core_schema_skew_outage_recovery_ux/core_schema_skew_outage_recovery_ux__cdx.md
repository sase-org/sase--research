# Recovering SASE from shared-runtime schema skew

**Research date:** 2026-09-25 (America/New_York)  
**Researcher:** `research.2k.cdx`  
**Scope:** The machine-wide SASE failures observed roughly 30–60 minutes before
this research request, the operator's recovery actions, and TUI designs that would
make the same class of incident safer and faster to recover from.

## Executive finding

The incident was a **shared-runtime compatibility failure**, not an LLM-provider
outage and not a system OOM. A breaking `sase-core` change advanced the Rust agent
scan wire schema from 9 to 10 while older SASE workspace checkouts still expected
9. Because editable development installs load the native binding from the shared
linked `sase-core` checkout, a core fast-forward changed the behavior beneath
already-existing workspaces. Any agent bootstrap that scanned artifacts from one of
those stale workspaces failed deterministically before its provider could start.

The strongest incident sample is the pair of follow-up agents that ended at
15:34 EDT. Both retained error reports show the same exception after about 12
seconds:

```text
ValueError: agent scan wire schema mismatch: got 10, expected 9
```

One was continuing `sase-17d.12.2`; the other was continuing `sase-19i.1`.
Both failed while resolving a fork dependency during bootstrap, before useful agent
work. This is consistent with the operator's observation that every attempted SASE
agent failed, although the durable sample only proves **two captured attempts out of
two** at that moment.

The operator correctly cleared the failed rows, aligned SASE to the new core
contract, and restarted the service/TUI generation. Recovery succeeded, but it was
labor-intensive and the evidence trail is incomplete: the TUI records generic
operations such as `kill sase` and `launch sase`, and its ordinary retry path does
not use the existing recovery-bundled `sase agent restart` engine. The TUI also kept
showing a top-level failed count when a parent workflow was running and the failed
state belonged to a nested continuation/monitor, making it hard to tell whether the
system was still unhealthy.

## What happened

### Causal chain

1. At 14:55:11 EDT, `sase-core` commit `2a0fc2abdaea` landed the breaking
   `canonicalize agent-session contracts` change. Among other wire changes, it
   raised `AGENT_SCAN_WIRE_SCHEMA_VERSION` from 9 to 10.
2. Existing numbered SASE workspaces retained Python code that expected schema 9,
   while their development environment could import the newly built/shared Rust
   binding returning schema 10.
3. The agent scanner is used in central operations such as named-agent lookup,
   launch dependency resolution, agent listing, TUI refresh, cleanup, and test
   setup. The mismatch therefore was not isolated to one feature.
4. The conversion boundary deliberately rejects incompatible schemas in
   `src/sase/core/agent_scan_wire_conversion.py`. That fail-closed behavior is
   correct for data integrity, but callers did not translate it into a recoverable
   machine incident. It escaped as a worker or bootstrap exception.
5. SASE commit `d86bcc3ac219` at 16:09:17 EDT updated Python's mirrored wire
   versions, moved `sase-core-revision.txt` from `c31b8cf...` to `24579137...`, and
   changed the other agent-session contracts needed by the core cutover.
6. Old workspaces remained old. Their `just check` setup could still report
   `scan_agent_artifacts probe returned stale schema: got 10, expected 9` even after
   the primary checkout was fixed. Agents could triage that as an unrelated
   environment failure, but the verification badge still looked like a task
   failure.

The TUI log exposes the non-atomic nature of the transition especially clearly:

- 15:08:10: TUI worker crash, `got 10, expected 9`.
- 16:20:56: another TUI worker crash in the opposite direction, `got 9, expected
  10`.

The reverse mismatch is important. It indicates that different long-lived
processes/workspaces could temporarily combine opposite generations of Python and
the native binding; this was not merely a corrupt artifact index. The same log also
contains `got 9, expected 8` incidents on 2026-09-13, so schema-skew crashes are a
recurring incident class rather than a one-off anomaly.

### Timeline

All times below are EDT on 2026-09-25.

| Time | Evidence | Interpretation |
| --- | --- | --- |
| 14:55:11 | `sase-core` commit `2a0fc2ab` | Rust wire schema advances 9 → 10. |
| 15:07:55–15:08:13 | Clean systemd service stop/start | An operator-triggered service generation change; service did not crash itself. |
| 15:08:10 | `~/.sase/logs/tui.log` | TUI worker dies on `got 10, expected 9`. |
| 15:33:41 | Two monitored `just check` commands finish | Their automatic follow-up agents are then created. |
| 15:34:20 / 15:34:28 | `runs.jsonl`; two error reports | Both follow-up agents fail at bootstrap on the identical schema mismatch. |
| 15:34:41 | Proc `rkxa8fvzpmg5` | TUI successfully performs `kill 1 + dismiss 3 agents`. |
| 15:34:52 | Proc `jw7wymbq5mba` | TUI successfully kills the other captured failed run. |
| 15:35:07 | Proc `gwjntqd458jx` | A dismiss attempt fails: `dismissed-agent artifact index sync failed`. Recovery itself is affected. |
| 15:36–15:49 | TUI proc store | Several more targeted kills and relaunches occur while the operator clears/restarts work. |
| 15:44–15:52 | Agent artifact records | Replacement epic/phase runs are materialized and later begin running. |
| 16:09:17 | SASE commit `d86bcc3ac` | Python mirrors and the core pin are made compatible with the contract flip. |
| 16:09:52–16:09:55 | systemd journal | Service cleanly restarts into the updated generation. |
| 16:12–16:15 | Continuation completions | Agents identify old-workspace `just check` failures as shared schema skew, run focused tests, and complete their scoped work. |
| 16:20:56 | TUI log | Reverse mismatch (`got 9, expected 10`) shows another stale generation remained. |
| 16:30:12–16:30:20 | systemd journal | Second clean service restart. Current service reports active/running, `Result=success`, `NRestarts=0`. |

### Blast radius

The phrase “all agents failed” should be interpreted precisely. The failure was
universal for an affected runtime combination, but it did not mean every LLM
provider process on the machine was down.

- The two preserved 15:34 launch attempts both failed before provider execution.
- The TUI artifact loader could crash on the same scan boundary.
- Agent cleanup/index synchronization could fail, as the 15:35 dismiss attempt
  demonstrates.
- Verification monitors in old workspaces continued to fail `_setup` after the
  primary checkout was repaired.
- Claude, Codex, Grok, and Muse work resumed later, and there is no journal evidence
  of a provider-wide outage.
- `sase.service` had large memory peaks (7.3 GB before the 16:09 restart and 5.5 GB
  before the 16:30 restart), but the journal contains clean operator stop/start
  transitions, no automatic restart, and no OOM-kill evidence. Memory pressure is
  worth monitoring but is not the causal explanation here.

## Audit of the operator's recovery

### What was done well

1. **Failed rows were cleared promptly.** Within seconds of the two bootstrap
   failures, the TUI bulk cleanup killed one live row and dismissed three completed
   rows, followed by a second targeted kill.
2. **The compatibility problem was fixed at its source.** Commit `d86bcc3ac` did not
   paper over one exception; it updated the Python mirrors, canonical agent-session
   keys, fleet protocol, tests, and the `sase-core` revision pin required by the
   breaking core change.
3. **Long-lived processes were reloaded.** The service was restarted after the
   compatibility fix and again after another stale generation surfaced.
4. **Scoped work was preserved where possible.** Later continuations for
   `sase-19i.2` and `sase-19o.3` distinguished shared setup failure from their phase
   code, ran focused tests (3 and 9 tests respectively), recorded follow-up context,
   and completed. The incident did not force blanket deletion of all workspaces.
5. **The post-incident state was investigated rather than trusted blindly.** The
   16:13 screenshot and a later diagnostic request explicitly question the single
   `failed` badge shown over a running epic, correctly identifying that status
   aggregation can mislead recovery decisions.

### What could not be proven from the audit trail

The proc store proves cleanup and launch operations, but not a complete bijection
between each old agent and its replacement:

- cleanup labels are often just `kill sase` or `dismiss sase`;
- launch records say `Started 1 agent(s)` without recording “restart of X”;
- the TUI retry action allocates a new retry name and opens the prompt editor without
  killing the old row;
- the TUI kill-and-edit path and its later launch are separate operations;
- no recovery bundles were created under `~/.sase/restarts` during the incident
  window, so the operator did not use the recovery-bundled `sase agent restart`
  execution path.

Accordingly, the evidence supports “the operator cleaned up affected rows and
relaunched replacement work,” but it cannot certify that every replacement maps to
exactly one old row. That attribution gap is itself a product defect for incident
response.

### Residual risk after recovery

The primary checkout and service becoming healthy did not make every existing
workspace healthy. A stale workspace still had Python schema 9 and failed `just
check` against schema-10 core. Restarting an agent into a fresh workspace can bypass
that skew; resuming it in place may preserve it. Recovery therefore needs an
explicit per-agent decision among:

- resume in place after proving the workspace runtime is compatible;
- restart from the current workspace state in a fresh runtime generation;
- preserve dirty changes and ask for operator review;
- classify a failed monitor as shared infrastructure blockage, not failed task
  logic.

## Current UX and reusable machinery

SASE already contains most of the safe primitives needed for a better experience:

- `sase.agent.restart.plan_agent_restart()` is read-only and builds a preview with
  live-agent, dirty-workspace, home-target, and related-artifact warnings.
- `execute_agent_restart()` saves a bundle under `~/.sase/restarts` **before** it
  stops the old agent, releases the name, and relaunches. Partial failures return a
  recovery hand-back instead of throwing away context.
- Provider drain reuses the restart planner and executor sequentially. Its comment
  explicitly rejects a parallel restart storm because admission and runner slots
  already throttle relaunches.
- The TUI has stale editable-code detection
  (`src/sase/ace/tui/stale_running_code.py`) and a tracked-proc-aware TUI/service
  restart helper (`src/sase/ace/tui/update_restart.py`).
- TUI performance rules already require disk/subprocess work to run outside the
  Textual event loop and prefer durable procs for long operations.

But these pieces are not joined for runtime incidents. The current `R` retry path
edits a copied prompt under a newly allocated name; it is not a same-name restart.
The kill-and-edit path is interactive and split across cleanup and later launch.
Neither is an incident coordinator, neither runs a compatibility canary first, and
neither produces a single durable audit record for a multi-agent recovery.

## TUI solution options

| Option | Benefit | Main risk | Assessment |
| --- | --- | --- | --- |
| Per-row **Restart** action | Small UI/code change; removes some prompt-copy toil. | Operator must diagnose the common cause and repeat the action; retries can fail into the same broken runtime. | Useful primitive, insufficient solution. |
| **Restart marked agents** | Reduces keystrokes and can reuse restart previews. | A manually marked set may omit affected rows or include healthy ones; still lacks a health gate. | Good secondary action. |
| Automatic retry on matching failure | Fast when failures are transient. | This mismatch is deterministic; auto-retry creates a storm, consumes slots, and hides the causal signal. | Reject for contract/version errors. |
| Transactional self-update only | Prevents some future mixed generations. | Does not help lock corruption, provider incidents, or agents already stranded in stale workspaces. | Necessary prevention, not complete recovery UX. |
| **Incident-aware Recovery Center** | Diagnoses once, groups impact, validates repair, and safely restarts only affected rows. | More engineering and a persistent state machine across TUI/service restart. | Best fit. |

## Design requirements inferred from this incident

### 1. Detect a typed runtime incident before ordinary rendering

Add a cheap compatibility handshake that reports the loaded host/core revision and
the wire versions needed by agent scan, launch, cleanup, and fleet. The durable
classification should be something like `runtime_contract_mismatch`, not a free-text
`ValueError`. Shared contract inventory and incident fingerprinting belong in
`sase-core`; the TUI should only present the result.

Run the handshake:

- at TUI/service startup;
- before admitting a new agent;
- after an editable checkout or native binding changes on disk;
- before a bulk recovery resumes.

If it fails, keep the TUI interactive in a degraded recovery mode. Do not let a
background agent refresh worker crash the whole app.

### 2. Correlate instead of multiplying red rows

Normalize failures by fingerprint—for example host revision, core revision,
operation, expected schema, and actual schema. When multiple agents or monitors hit
the same fingerprint in a short window, create one incident and attach affected rows
to it.

The header should separate:

```text
Task failures: 0    Infrastructure blocked: 6    Active incidents: 1
```

A monitor failing because its workspace cannot load core is `BLOCKED (runtime)`,
not evidence that the feature implementation failed. The 16:13 screenshot's single
global `failed` count over a running epic demonstrates why the distinction matters.

### 3. Provide a recovery preview, not a blind bulk retry

An incident panel should show:

- incident fingerprint and first/last occurrence;
- “providers healthy / runtime incompatible” when evidence supports it;
- affected agents and monitors, grouped by workspace generation;
- fresh, stale, dirty, live, pending-question, and non-restartable rows;
- the exact action proposed for each row;
- warnings already computed by `plan_agent_restart()`;
- service/TUI generation and revision inventory;
- a canary result.

A compact initial presentation could be:

```text
┌ Runtime incident: SASE/core contracts disagree ───────────────────┐
│ Host d86bcc3 · core 2a0fc2a · scan expected 9, got 10             │
│ 6 blocked · providers healthy · artifacts retained                │
│                                                                   │
│ Repair plan                                                       │
│  ✓ align runtime and restart service/TUI                          │
│  ✓ run scan + clean-workspace bootstrap canary                    │
│  ↻ restart 4 affected agents (2 need confirmation, 1 dirty)       │
│  – leave 2 failed monitors attached as incident evidence          │
│                                                                   │
│ [Repair & restart affected] [Inspect evidence] [Export report]    │
└───────────────────────────────────────────────────────────────────┘
```

### 4. Make recovery a durable, resumable transaction

“Repair and restart affected” crosses the very TUI/service restart that loads the
fixed code. It therefore cannot be a session-local callback. Persist a recovery
intent/state machine before changing anything, then have the new service/TUI
generation resume it.

Suggested stages:

1. `planned`: capture incident fingerprint, affected identities, workspace facts,
   and read-only restart previews.
2. `quiesced`: stop admitting launches that require the incompatible contract;
   unaffected providers/tasks may continue.
3. `runtime_repaired`: apply or validate the compatible SASE/core generation.
4. `reloaded`: restart TUI/service using the existing tracked-proc-aware mechanism.
5. `canary_green`: scan artifacts and bootstrap one disposable/fresh-workspace
   probe. Refuse fan-out if either fails.
6. `bundled`: persist each agent's recovery bundle before destructive cleanup.
7. `restarting`: execute sequentially through the existing restart engine and
   normal admission controls.
8. `complete` or `partial`: retain per-agent outcome, replacement identity,
   recovery path, and operator-action history.

Sequential execution is deliberate. It limits blast radius, avoids a runner-slot
storm, and allows the first restarted agent to act as an additional canary.

### 5. Preserve operator authority where data can be lost

The primary action may repair compatible runtime code automatically if that policy
already exists, but it must preview and confirm:

- killing a live agent;
- a workspace with uncommitted changes;
- name reuse that deletes related artifacts;
- pending questions or gate state;
- any restart that cannot create a recovery bundle.

Default to excluding uncertain rows, not force-restarting them. A secondary “mark
additional agents” action can broaden the set explicitly.

### 6. Improve the audit record

For every cleanup/relaunch, record stable identities and causal links:

```text
incident_id → old agent/artifacts → recovery bundle → new agent/artifacts
```

The TUI history should say `restart sase-19i.1 → sase-19i.1 (workspace 40 → 52)`,
not `kill sase` followed later by `launch sase`. Record the acting TUI session,
reason/fingerprint, confirmation, skipped rows, canary evidence, and each partial
failure. This would make the next audit answerable without reconstructing intent
from timestamps.

## Implementation path

### Phase 0: stop the crash loop

- Catch typed core compatibility errors at agent/TUI scan entry points.
- Render a stable incident banner and cached last-good agent list.
- Block incompatible launches with a precise message and evidence-copy action.
- Split infrastructure-blocked counts from task failures.

### Phase 1: safe affected-set restart

- Add a Recovery Center panel backed by a durable proc/state record.
- Reuse `plan_agent_restart()` previews and recovery bundles.
- Correlate matching failed runs/monitors into one affected set.
- Require a green compatibility scan and clean-workspace bootstrap canary.
- Execute restarts sequentially; display per-row progress and recovery paths.

### Phase 2: transactional runtime generations

- Make SASE + native core activation atomic from the perspective of long-lived
  processes.
- Persist loaded/current revisions and wire inventories in service health.
- When editable roots move, quiesce incompatible operations until restart instead
  of continuing with a mixed generation.
- Resume interrupted recovery from its durable manifest after TUI/service restart.

### Acceptance tests

At minimum, test:

1. both mismatch directions (`got 10/expected 9` and `got 9/expected 10`);
2. TUI remains usable and emits exactly one correlated incident;
3. no provider call or retry storm occurs while the canary is red;
4. healthy/unrelated agents are excluded;
5. dirty and live agents require confirmation;
6. recovery interrupted after every stage resumes idempotently;
7. a failed relaunch exposes its saved recovery bundle;
8. monitor infrastructure failures do not inflate the task-failure count;
9. audit history preserves old-to-new identity linkage.

## Evidence and confidence

Primary local evidence consulted:

- `~/.sase/logs/tui.log` (schema mismatch crashes and timestamps);
- `~/.sase/logs/runs.jsonl` and the two 15:34 agent error reports;
- `sase proc list -a -j` plus proc logs for TUI cleanup/launch operations;
- `journalctl --user -u sase.service` and current systemd properties;
- SASE commit `d86bcc3ac219` and `sase-core` commit `2a0fc2abdaea`;
- `~/tmp/screenshots/20260925_161333.png`;
- current restart, provider-drain, stale-code, and TUI restart source modules.

Confidence is **high** on root cause, failure mechanics, service health, and the
first cleanup actions; **medium** on a complete old-agent → restarted-agent mapping
because current TUI audit records do not retain that relationship. No other
researcher's report or transcript was consulted.

## Recommended solution

Build an **incident-aware Recovery Center** whose primary action is **Repair runtime
and restart affected agents**. The feature should combine a typed SASE/core
compatibility handshake, failure fingerprinting, a degraded-but-live TUI, a
clean-workspace canary, and a durable recovery transaction that reuses
`plan_agent_restart()` plus its pre-destructive recovery bundles. After the runtime
and service/TUI generation are compatible, restart only the proven affected set,
sequentially, under normal admission limits and with explicit confirmation for live,
dirty, pending-question, or related-artifact cases.

This is preferable to a bulk-retry button because it solves the operator's actual
problem in the correct order: **prove and repair the shared environment first,
separate infrastructure blockage from task failure, then recover work without losing
state**. Implement Phase 0 immediately so this class of mismatch becomes one
actionable banner rather than a TUI crash; then add the durable affected-set restart
as Phase 1. Atomic runtime generations are the longer-term prevention layer, not a
substitute for recovery UX.
