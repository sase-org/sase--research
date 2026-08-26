---
create_time: 2026-08-26
updated_time: 2026-08-26
status: research
---

# Gate shells: durable decisions as first-class agent-family members

**Research question.** How should SASE represent an agent-created notification gate as
a named **gate shell** in that agent's family, terminate the creating agent immediately,
stream reviewed-command output through the family, and later continue the same family
with the right context—without preserving the current plan/question wait loops or
building a second version of the monitor system?

**Snapshot.** Researched 2026-08-26 against `sase` at `23b7abf1b` and linked
`sase-core` at `5ab0250a7`. The `bob-cli-15` case study uses its bead sidecar and the
draft `live_reply.md` produced by `bbugyi200.athena.bob-cli-15.1`; it is explicitly
treated as draft agent output, not as an authoritative project record.

**Related work.** This design builds directly on
[`sase_shell_named_procs`](sase_shell_named_procs/sase_shell_named_procs.md), whose most
important conclusions have now landed in part: named proc shells have a durable proc
record, lane-attached shells retain an artifact record, proc logs are bounded, and the
proc settlement path is checkpointed. It also follows the TUI constraints in
`sase/memory/tui_perf.md`: no filesystem work in render/event handlers, cache immutable
data, and refresh live data selectively in the background.

---

## Bottom line

The right abstraction is **not “a gate that happens to appear in a family,” and not “a
monitor whose command is `sase gate wait`.”** It is a shared family-shell lifecycle with
two policies:

- a **monitor shell** immediately runs one predetermined command;
- a **gate shell** waits without an LLM, accepts durable reviewer-action intents, runs
  the selected trusted commands, records their output, settles the decision, and may
  launch a family successor.

An agent-created gate should therefore become a named, family-attached proc shell. The
gate shell—not the agent runner—owns the gate from publication through terminal
settlement. Starting it promotes a standalone creator into a family when necessary,
transfers the workspace claim after a detached controller acknowledges startup, writes
a generic family-shell handoff marker, and terminates the creator. The creator settles
as `DONE`; the gate shell owns `TALE` / `EPIC`, `PLAN APPROVED` / `TALE APPROVED` /
`EPIC APPROVED`, `QUESTION` / `ANSWERED`, and generic gate states. The family node keeps
doing the simple and correct thing: display its newest concrete shell's status.

This gives SASE one durable sequential history:

```text
agent shell --0  →  gate shell --gate  →  agent shell --1
     DONE            TALE / APPROVED          RUNNING
```

The implementation should reuse the proc supervisor, bounded artifact log, family
promotion, claim transfer, checkpointed settlement, follow-up launch, and `#fork`
projection already used by monitors. It should *not* merge the notification-gate trust
model into procs: verified bundles, owned commands, typed inputs/results, write-once
responses, repeatable operations, and AND-branch retry journals remain the gate domain.

---

## 1. The current architecture has two incompatible meanings of “handoff”

The plan and question flows stop the provider subprocess but keep the outer agent runner
alive. Monitors perform a real ownership transfer and end the runner.

### 1.1 Plan and question gates are synchronous waiters

`sase plan propose` tells the agent that the runner will create the approval gate, “wait
mechanically,” and continue (`src/sase/xprompts/skills/sase_plan.md:54-66`). The runner
does exactly that: `handle_plan_marker()` calls `handle_plan_approval()` synchronously
(`src/sase/axe/run_agent_exec_plan.py:78-132`), and the plan utility calls the common
poller. The question flow is even more explicit: it writes `pending_question.json`,
calls `wait_for_gate()` every 200 ms, then reacquires a runner slot before continuing
(`src/sase/axe/run_agent_helpers_questions.py:99-146`).

The provider turn has ended, but a live agent-runner process still owns continuity and
waits for a human. This is the architectural bug. A gate may be unanswered for hours or
days; an agent runner and its special resumption loop are the wrong durable object.

The generic custom-gate skill exposes the same mistake directly. It tells the agent to
create a schema-v3 gate and then use `sase gate wait`; the CLI advertises that command as
“Wait mechanically for a durable gate to reach a terminal state”
(`src/sase/main/parser_gate.py:304-352`). `wait_for_gate()` is a process-local polling
loop around response and cancellation files (`src/sase/notification_gates/poller.py:64-134`).

### 1.2 Monitors already implement the correct lifetime

Monitor start resolves or promotes the creator's family, allocates a `--mon` member,
creates family artifacts, submits a detached proc, waits for supervisor acknowledgement,
and transfers the workspace claim (`src/sase/monitor/start.py:173-293`). Only after the
monitor exists durably does the CLI write a handoff marker and kill the agent runner
group (`src/sase/monitor/handoff.py:24-62`). Completion uses the proc settlement path to
dispose the claim, finalize artifacts, and launch an optional successor.

That separation is exactly what gates need:

- the agent does not survive the handoff;
- the long-lived object consumes no LLM/provider turn and no agent runner slot;
- the family has a durable member while work is pending;
- the workspace can remain owned by the family;
- a successor can be launched only after the predecessor and shell are durably settled.

### 1.3 The generic proc substrate is now ready for another family-shell policy

`ProcSubmitRequest` already carries a stable shell name, artifact-owned log, artifact
directory, workspace-claim policy, and arbitrary follow-up policy
(`src/sase/procs/request.py`). `settle_proc_shell()` is a resumable sequence of
checkpoints for output, claim, artifacts, follow-up, and result publication
(`src/sase/procs/settlement.py`). However, its follow-up hook recognizes only
`kind == "monitor"`; monitor-specific metadata remains spread across roughly twenty
flat `monitor_*` fields in both the Python and Rust artifact scanner. Adding another
parallel block of `gate_*` plumbing would preserve the accidental duplication.

The seam to extract is therefore **family-shell orchestration**, not all monitor and
gate behavior.

---

## 2. `bob-cli-15` demonstrates why the terminal result must travel with the family

`bob-cli-15.1` was emergency disk-pressure work on an 11 TB array. The implementing
agent found that a destructive backup-rotation cleanup required explicit approval. Its
draft live reply records this sequence:

1. It proposed deleting only two stale yearly rotations, guarded so the command would
   refuse to run while backup, `rsync`, or another recursive delete was active.
2. It then reported “I’m waiting on it now,” followed by repeated pending updates
   (`live_reply.md:29-35`).
3. The approved command reclaimed about 90.1 GB, but that result was insufficient for
   the 500 GB exit target (`live_reply.md:37`).
4. The agent measured the remaining rotations, proposed a second narrower command,
   waited again (`live_reply.md:41-49`), and used the second result—about 225.7 GB—to
   establish that the target had finally been met (`live_reply.md:51`).

This is the important shape, independent of the specific cleanup:

```text
pre-gate investigation
  → reviewed selection
  → command output/result changes the diagnosis
  → follow-up agent must continue from both
```

A plain “approved” event is not enough. The successor needs the prior family transcript,
the exact selected options, terminal state, redacted structured results, and—depending
on policy—either a bounded output tail or a durable log pointer. Keeping the original
agent alive happens to retain that context, but at the cost of an indefinitely blocked
runner. Launching an unrelated new agent avoids the waiter but loses causal continuity.
A gate shell gives the result a durable place in between.

The same shape appears in existing built-ins:

| Gate | What the next agent needs |
| --- | --- |
| Plan/tale approval | plan transcript, selected action, feedback or approval, plan path, chosen implementation tier |
| Epic approval | proposal transcript, approved plan, bead/launch result, any gate-side failure |
| Questions | original conversation, typed answers, reconstructed Q&A history |
| Destructive custom gate | reviewed command identity, selection, exit/result, bounded output or log pointer |
| Launch approval | requested launch parameters, approval/result, capacity or launch failure |

These are variations of one continuation envelope, not reasons for separate waiting
systems.

---

## 3. Define a gate shell precisely

The new glossary strand should define the concept narrowly enough to keep the
architecture honest:

> **Gate Shell** — A named, family-attached proc shell that owns an agent-created SASE
> gate from publication through reviewer-action execution, terminal settlement, and an
> optional successor launch. Attaching the first gate shell promotes a standalone
> creator into an agent family. A gate shell contains no LLM and never keeps its creator
> agent alive while awaiting a human.

Suggested dependencies for the memory strand are `Agent Family`, `Agent Shell`, `Proc
Shell`, and `Sase Shell`. “Gate Shell” should also be added to the glossary descriptor's
term list. The memory edit should be performed with the normal approved-memory workflow
and followed by `sase memory init`; this research file intentionally does not edit
canonical memory.

Four identity fields should remain distinct:

| Field | Meaning | Example |
| --- | --- | --- |
| family | sequential ownership/history lane | `disk-cleanup` |
| shell name | human-addressable family member | `disk-cleanup--gate` |
| proc id | supervisor/store identity | `g8f2…` |
| gate id/kind | decision-bundle identity | `custom-…` / `custom` |

The first gate in a family should use `<family>--gate`; later ones should use
`<family>--gate-0`, `<family>--gate-1`, and so on, allocated under the same family-name
lock used by promotion and monitor naming. The artifact member should keep
`shell_kind: "proc"`, `agent_family_role: "gate"`, and proc `origin: "gate"`.
Do **not** introduce another proc `kind`: gate-ness is an origin/family-role policy, not
a new execution primitive.

Agent-created gates are always attached. Gates created by chops, daemons, or other
host-owned automation have no creator agent to kill and should remain neutral system
gates unless an origin family is explicitly supplied. Inventing fake agent families for
system producers would corrupt the meaning of a family.

---

## 4. The lifecycle should be explicit and crash-recoverable

A gate shell needs more states than a monitor because it can accept repeatable actions
without resolving the gate and can execute multiple selected commands before producing
one response.

```text
CREATING
   │ controller ACK + claim transfer + notification publication
   ▼
PENDING ── repeatable action ──► EXECUTING_ACTION ──► PENDING
   │
   ├── answer intent ──────────► EXECUTING_SELECTION ──► SETTLING
   ├── cancellation ──────────────────────────────────► SETTLING
   └── deadline ──────────────────────────────────────► SETTLING
                                                        │
                                                        ▼
                                      terminal artifacts + optional successor
```

The artifact projection can use a compact public state vocabulary—`pending`,
`executing`, `answered`, `cancelled`, `timed_out`, `failed`, `lost`—while the controller
keeps finer internal checkpoints. Unknown states must conservatively render as active,
as monitor state does today.

### 4.1 Creation and handoff ordering

The critical invariant is: **never kill the creator until another durable owner has
acknowledged the gate, and never publish an actionable notification without a durable
owner.** The start transaction should be:

1. Validate the gate request and build its verified bundle in an unpublished staging
   state.
2. Under the family lock, resolve the creator, promote it if necessary, allocate the
   gate suffix, and create the gate-shell artifact member.
3. Reserve and start a detached gate-controller proc whose log lives in that artifact
   directory.
4. Wait for controller acknowledgement; transfer the workspace claim from the creator
   to the gate shell.
5. Atomically publish the bundle/notification and release the controller's launch
   barrier.
6. Write one generic family-shell handoff marker in the creator artifacts and terminate
   the agent runner group.
7. The runner recognizes the marker, saves the creator transcript, and terminalizes the
   creator as `DONE`—not `killed` and not `TALE DONE`.

Every boundary needs compensation. Before notification publication, failures tear down
the reserved proc/member and restore the creator's claim. If publication succeeds but
the handoff marker cannot be written, cancel the gate and stop the controller rather
than allowing the creator and gate shell to own one lane concurrently. An automatically
resolved gate still materializes a short-lived gate shell and obeys the launch barrier;
otherwise auto-approval can race a successor against the still-running creator.

This is a generalization of the monitor handoff marker, not a second marker loop. Rename
the underlying concept to a family-shell handoff with a typed payload (`kind`, `proc_id`,
`member_name`, `member_artifacts_dir`) and keep a compatibility reader for the existing
monitor marker.

### 4.2 The controller—not ACE—should execute reviewed commands

Today `execute_gate_selection()` runs trusted option commands synchronously in whichever
client answered the gate. It exposes live callbacks (`on_command_start`,
`on_output_line`, `on_process_state`) and holds `.response.lock` through the sequence
(`src/sase/notification_gates/executor.py:62-112`). Its journal correctly prevents an
incomplete AND branch from being silently replayed and supports explicit resume or
restart, but live stdout/stderr is not a durable gate-shell log.

Merely passing a log callback from ACE would make the panel look right while leaving
the lifecycle wrong: closing ACE could kill an approved destructive command, mobile and
Telegram would need equivalent callback wiring, and no process would own timeout or
follow-up settlement.

Instead, answering clients should submit a durable **gate action intent**. The gate
controller serializes intents and invokes the existing trusted executor:

- final-selection intents contain the request hash, selected option ids, typed inputs,
  feedback, source, and retry mode;
- repeatable-operation intents contain the operation id, typed input, and a unique
  client action id;
- intents and results are write-once and idempotent by action id;
- the current response lock and attempt journal remain the exactly-once authority for
  terminal execution;
- only one controller may claim an intent; a restarted controller resumes from the
  durable journal and never guesses whether to rerun a partially completed branch.

ACE, mobile, Telegram, and headless clients then share one behavior: submit an intent
and observe its status/log. A CLI may wait for *that short command action* to finish for
interactive ergonomics; no agent waits for the human decision itself.

### 4.3 Output must be a durable artifact, not a UI callback

Use the existing artifact-owned `BoundedLogPipe` and proc `log_path`. Append compact
lifecycle records and command output in execution order, including action/option labels,
attempt boundaries, exit state, and diagnostics. Keep the typed result in the response
and journal; the log is display evidence, not the result authority.

Three security rules matter:

1. Never write declared secret inputs to the log, response, metadata, or successor
   prompt. Keep the existing input/result redaction at the executor boundary.
2. Treat all command output as untrusted data. The TUI should style it as output, and a
   `#fork` continuation must fence and label it exactly as proc output is today.
3. Bound retained bytes and follow-up injection separately. A full local log may be
   retained under artifact policy while the prompt gets `none`, a bounded tail, or only
   a file pointer.

The execution journal should remain structured and append-only; it should reference log
offsets or action spans rather than duplicating unbounded stdout/stderr inside JSON.

### 4.4 Reconciliation must cover a human-scale wait

A gate controller can outlive a login session or a reboot. Reconciliation should derive
truth from the bundle, intent records, proc row, and journal:

- a terminal gate with a nonterminal proc is settled without rerunning commands;
- a dead controller with no active command is restarted and resumes pending;
- an interrupted selection is surfaced as the current `partial_attempt`, requiring the
  existing explicit `resume` or `restart` choice;
- a gate deadline is enforced by the controller/host, not by an agent poller;
- notification state is reconciled from the gate terminal record;
- claim and follow-up checkpoints remain idempotent;
- a controller that cannot be recovered becomes `lost`/`FAILED` visibly and preserves
  its log and unlaunched follow-up prompt.

This preserves the strongest property in the current executor: destructive commands are
never silently repeated after an ambiguous crash.

---

## 5. Continuation should be declarative, outcome-aware, and shared with monitors

`continuation_mode` is currently only a required string in the generic schema; kind
adapters interpret values such as `agent_plan`, `agent_question`, and
`wait_for_launch`. It names bespoke code paths rather than describing continuation
policy. Schema v3 also rejects unknown fields, so adding a real policy warrants gate
request schema v4 while continuing to read v3 bundles.

The canonical internal object should be a generic `FamilyFollowupSpec`, also used by
monitors. A gate adds outcome routing because “feedback,” “approved,” “rejected,” and
“answered” need different prompts. A representative v4 shape is:

```json
{
  "continuation": {
    "context": "family",
    "workspace": "inherit",
    "model": "inherit",
    "include": {
      "status": true,
      "response": "redacted",
      "command_output": { "mode": "tail", "lines": 200 }
    },
    "routes": [
      {
        "when": { "outcome": "approved" },
        "prompt": { "template": "plan_approved" }
      },
      {
        "when": { "outcome": "feedback" },
        "prompt": { "template": "plan_feedback" }
      }
    ]
  }
}
```

Key design choices:

- The gate adapter derives a bounded semantic `outcome` (`approved`, `feedback`,
  `answered`, `rejected`, `cancelled`, `timed_out`, `failed`) from the typed response.
  Routes match that outcome rather than reimplementing plan semantics in the supervisor.
- `prompt` supports either validated inline text or a registered built-in template.
  Plan and question behavior stays typed and testable; custom gates can supply the
  optional next prompt requested by the feature.
- No matching route means no successor. Cancellation, timeout, and failure can each be
  configured explicitly instead of inheriting surprising behavior.
- `include.status`, `include.response`, and `include.command_output` independently
  control what reaches the successor. `response: "redacted"` is the maximum safe mode;
  raw secret-bearing inputs are never eligible.
- Output modes reuse monitor semantics: `none`, `tail`, or `file`, with a bounded line
  count. CLI conveniences such as `--next`, `--model`, and `--next-output` compile into
  this object rather than becoming separate execution paths.
- `workspace` is explicit: `inherit` transfers the family claim (the default for plan,
  question, and destructive workflows), `fresh` launches in a new workspace, and
  `release` ends without retaining one. The existing claim-transfer degradation and
  persisted-unlaunched-prompt behavior should be shared with monitors.

The resulting successor prompt should have two layers. Routing directives come first;
the user-authored next action remains the only instruction; a generated, disabled
context block reports gate identity, terminal status, selection, redacted results,
timing, output policy, and log pointer. This mirrors the monitor prompt's strong
untrusted-output labeling.

### 5.1 Full-family `#fork` is mostly implemented already

The current monitor follow-up emits `#fork:<starter_name>`
(`src/sase/monitor/followup_prompt.py:137-156`). That only asks for the starter. In
contrast, the general `#fork:<family>` resolver already walks the family oldest-first,
includes agent transcripts, classifies terminal monitor members as proc records, and
formats their bounded logs as untrusted command output
(`src/sase/scripts/_agent_chat_from_name_sources.py`,
`src/sase/scripts/_agent_chat_from_name_family.py`, and
`src/sase/history/chat_fork/family.py`).

The gate work should:

1. generalize the family-member classifier from “agent or monitor” to “agent or typed
   family proc shell”;
2. add gate-specific execution metadata to the proc fork projection;
3. wait until the gate shell is terminal and its artifact index is visible;
4. launch the successor with `#fork:<family-base>`, not the creator's member name.

That produces exactly the requested transcript: every earlier family shell, the creator
agent shell, and the gate shell. Monitor follow-ups should migrate to the same family
fork when attached, eliminating another behavioral difference.

---

## 6. Status becomes simpler when it belongs to the shell that owns the state

Current family status policy reconstructs pending and approved plan states from planner
timestamps, feedback timestamps, child roles, plan actions, and special sticky labels.
For example, `done_handoff_status()` manufactures `TALE DONE` or `PLAN DONE`, and the
planner policy keeps approved states sticky across later children
(`src/sase/ace/tui/models/_agent_status_family_policy.py:101-174`). This is why a planner
can appear to have implemented a plan or why an agent that merely asked a question can
carry a workflow status long after its turn ended.

Make status an explicit projection of the concrete shell:

| Shell | Lifecycle | Visible status |
| --- | --- | --- |
| creator agent | handoff finalized | `DONE` |
| tale gate | pending review | `TALE` |
| epic gate | pending review | `EPIC` |
| approved plan gate | terminal | `PLAN APPROVED`, `TALE APPROVED`, or `EPIC APPROVED` |
| question gate | pending / terminal | `QUESTION` / `ANSWERED` |
| generic gate | pending / executing / terminal | `GATE` / `EXECUTING` / adapter-configured terminal status |
| successor agent | running | its ordinary agent status |

Each built-in adapter should supply a validated display-status profile for its semantic
outcomes. Custom gates may choose from a bounded status vocabulary; they should not
inject arbitrary control characters or unbounded labels into the agent list.

The family container's status algorithm then reduces to: select the newest concrete,
visible sequential family shell and project its status. During review that is the gate
shell; after a successor launches it is the successor. Keep the old inference policy as
a read-only compatibility path for legacy artifacts, but stop writing new `PLAN DONE`
and `TALE DONE` agent statuses. This meets the no-family-node-regression requirement
while deleting a substantial amount of chronology inference.

---

## 7. Metadata should become generic before another field family is added

The Rust artifact scanner is the stable backend boundary and currently has
`AGENT_SCAN_WIRE_SCHEMA_VERSION = 6`. Its `AgentMetaWire` and `DoneMarkerWire` enumerate
monitor lifecycle fields individually (`crates/sase_core/src/agent_scan/wire.rs`), and
the Python/TUI layers reconstruct a `MonitorRecord` from them. Duplicating that layout
as `gate_id`, `gate_state`, `gate_output_path`, `gate_followup_*`, and so on would make a
later monitor/gate unification harder, not easier.

Add one additive schema-v7 nested record to agent metadata and terminal markers:

```json
{
  "family_shell": {
    "schema_version": 1,
    "kind": "gate",
    "proc_id": "g8f2...",
    "state": "pending",
    "display_status": "TALE",
    "label": "Approve disk-space plan",
    "log_path": ".../gate.log",
    "starter_agent": "disk-cleanup--0",
    "request": { "kind": "plan", "id": "plan-..." },
    "followup": {
      "agent": null,
      "outcome": null,
      "error": null,
      "prompt_path": null
    }
  }
}
```

The terminal marker carries the final state, outcome, timestamps, truncation, and
follow-up disposition. Immutable request/bundle details remain in the verified gate
bundle; metadata contains only the bounded projection needed by scanners and UIs.
During migration, readers synthesize `family_shell.kind == "monitor"` from legacy
`monitor_*` fields, and monitor writers switch to the generic object before those flat
fields are retired. The proc row continues to be the supervisor/store identity; the
artifact member continues to be the family/history/retention identity.

Because this projection must match across CLI, TUI, web, and editor integrations, the
wire type, state bucketing, terminal predicate, and deterministic “newest family shell”
selection belong in `sase-core`. Python should own gate adapters, command execution, and
presentation glue—not reimplement those shared rules.

---

## 8. TUI design: a decision diamond with monitor-grade detail

Use `◆` as the gate-shell glyph. It reads as a decision node, is visually distinct from
the monitor's `⚙`, occupies one predictable terminal cell, and is present in the pinned
Fira Code environment. Use color for state rather than changing glyph width:

- pending: warm amber (`#D7AF5F`);
- executing: blue/cyan (`#5FAFFF`);
- answered/cancelled: settled gray (`#9E9E9E`), while the status text carries the
  semantic result;
- failed/lost: the existing failure red.

The current agent-list prefix renderer and family roster explicitly branch on monitors,
and the prompt panel has monitor-only builders for fields, output, and a family phase.
Do not copy these into equally large gate-only modules. Introduce a small typed
`FamilyShellPresentation` projection (`kind`, glyph/color, label, state, timing, command
summary, log, follow-up), then let monitor and gate adapters add their domain-specific
fields.

When the gate shell itself is selected, the metadata pane should show:

```text
◆ GATE
  Decision:     Delete stale backup rotations
  Kind / id:    custom / custom-…
  State:        EXECUTING
  Requested by: disk-cleanup--0
  Selection:    delete-and-verify
  Attempt:      1
  Follow-up:    family, tail 200 lines

  COMMANDS
  ✓ preflight guard
  ● delete stale rotations
  ○ verify free space

  OUTPUT
  …live bounded output…
```

When the family node is selected, the same material appears chronologically inside
`AGENT REPLY` as a new `GATE` phase, parallel to the existing monitor phase:

```text
AGENT REPLY
  ── agent disk-cleanup--0 ──
  …conversation…

  ── ◆ gate disk-cleanup--gate ──
  GATE
  …decision, state, selection, follow-up…
  Output:
  …the same live command log…
```

The data source must be the artifact/proc log and structured gate projection, not modal
widget state. The scanner/background refresh path should tail only the selected shell's
log, cache by identity plus mtime/size, coalesce bursts, and update the prompt panel
selectively. Rendering must perform no file reads. Add PNG snapshots for pending,
executing, approved, failed, long-output, and narrow-width layouts so the `◆` alignment
and `GATE` subsection stay beautiful under real terminal constraints.

---

## 9. What to unify—and what to keep separate

The shared code should be obvious at the service boundary:

| Shared family-shell kernel | Monitor policy | Gate policy |
| --- | --- | --- |
| family resolution/promotion | one command starts immediately | decision starts pending |
| suffix allocation and member artifacts | total/idle timeout semantics | gate deadline/cancellation semantics |
| proc reservation, supervisor ACK | monitor state/outcome mapping | action-intent mailbox |
| artifact-owned bounded log | command/run metadata | verified bundle and typed options |
| workspace claim transfer/release | immediate stdout/stderr stream | repeatable operation and selection execution |
| generic handoff marker and creator finalization | completion trigger | semantic outcome trigger |
| checkpointed settlement/reconciliation | monitor prompt fields | selected options/redacted result fields |
| successor launch/fallback | monitor-specific status | gate-kind display status |
| family `#fork` projection | `⚙` presentation | `◆` presentation |

Keep the public concepts separate. A monitor observes command completion; a gate mediates
a trusted human decision. Combining their CLIs or forcing gate options into a monitor
command string would erase useful semantics and weaken the gate security boundary. The
goal is one lifecycle kernel with two policies, not one feature wearing two names.

Three tempting alternatives should be rejected:

1. **Keep the outer runner as the supervisor.** This preserves the exact resource leak
   and special continuation loops the change is meant to remove.
2. **Add only a synthetic TUI family row.** This improves appearance but leaves clients
   executing commands, loses durable live output, and provides no owner for timeout,
   claim, or follow-up.
3. **Start a monitor whose command is `sase gate wait`.** The monitor would own a polling
   process but not the reviewed option commands or gate transaction. Status, output,
   response, and retries would still be split across two systems.

---

## 10. Migration path and proof obligations

The safest order is substrate-first, then one simple gate, then the complex plan chain.

### Stage 1: generic family-shell kernel

- Extract monitor family resolution/promotion, suffix allocation, artifact creation,
  claim transfer, handoff, settlement, and successor launch behind typed services.
- Add the `family_shell` Rust/Python wire and compatibility projection for monitors.
- Change attached monitor follow-ups to `#fork:<family>` and prove the transcript order.

### Stage 2: gate controller and durable action intents

- Add gate-shell start/reconcile/stop services over the proc substrate.
- Move option and operation execution behind the controller while retaining current
  bundle verification, response lock, journal, redaction, and retry contracts.
- Persist bounded logs and expose a neutral show/follow projection.
- Make agent-context gate creation perform the acknowledged handoff and terminate.

### Stage 3: family/status/TUI projection

- Generalize concrete-family-shell enumeration and newest-shell status selection.
- Add the `◆` gate row, selected-shell detail, family `GATE` phase, and background log
  refresh.
- Keep legacy plan/question inference only for old artifacts.

### Stage 4: migrate every agent-facing producer

- Migrate `sase questions` first: one answered outcome and one successor prompt.
- Migrate custom `/sase_gate`, removing its instruction to run `sase gate wait`.
- Migrate plan/tale/epic feedback and approval onto outcome routes and registered prompt
  templates; delete the runner's synchronous plan-approval loop.
- Migrate HITL and launch approval gates.
- Update the generated skill source templates under `src/sase/xprompts/skills/`, then use
  the generated-skill deployment workflow; do not patch deployed copies in chezmoi.
- Retain `sase gate wait` only for non-agent scripts/tests. When `SASE_AGENT` is present,
  reject it with an actionable message directing the caller to create a gate shell with
  a continuation instead.

### Stage 5: retire compatibility writes

- Stop writing monitor-only flat metadata after all readers understand `family_shell`.
- Stop writing `PLAN DONE` / `TALE DONE` on agent shells.
- Remove question runner-slot release/reacquire and pending-wait code, plan wait loops,
  and old per-kind continuation plumbing after existing in-flight bundles have settled.

The end-to-end suite should prove at least these invariants:

- a standalone named agent becomes `<family>--0` plus `<family>--gate` atomically;
- the controller acknowledges and owns the claim before the creator dies;
- no agent runner or runner slot remains while a human gate is pending;
- the creator is `DONE`, the gate owns pending/approved status, and the family mirrors
  the newest shell;
- two reviewers racing one answer execute the selected commands once;
- a crash at every intent/executor/response/settlement checkpoint is recoverable without
  an implicit destructive-command replay;
- repeatable actions return to pending and stream to the same log;
- timeout works without a waiter;
- continuation modes independently include status, redacted response, tail/file/no
  output, model routing, and workspace policy;
- `#fork:<family>` includes earlier shells, creator, and terminal gate exactly once and
  in order, with command output fenced as untrusted;
- follow-up launch failure releases or safely transfers the claim and persists the
  unlaunched prompt;
- plan feedback, tale approval, epic approval, questions, custom destructive gates,
  auto-resolution, and non-agent system gates retain their intended behavior;
- live TUI refresh does not perform synchronous render-path I/O and visual snapshots
  cover glyph width, long output, and terminal states.

---

## Recommended solution

Implement gate shells as a **new policy on the existing named proc/family-shell
substrate**, with a detached gate controller as the sole owner of reviewer commands,
timeout, durable output, settlement, and optional continuation. First extract a generic
family-shell kernel from monitors; then add a schema-v4 declarative, outcome-aware
`continuation` object and a schema-v7 generic `family_shell` scan projection; finally
migrate questions, custom gates, plan/tale/epic approval, HITL, and launch gates off the
outer runner's wait loops.

Use `<family>--gate[-N]`, `agent_family_role: "gate"`, proc `origin: "gate"`, and the
single-cell amber decision glyph `◆`. Finalize the creator as ordinary `DONE`; put
pending and approved workflow statuses on the gate shell; keep the family node as the
status of its newest shell. Persist every selected command's bounded live output in the
gate shell artifact, render it both on the selected shell and in an `AGENT REPLY → GATE`
phase, and launch successors with `#fork:<family>` plus explicit redacted-result/output
policy.

This is the smallest design that satisfies all of the requested behavior while improving
reliability: humans may take arbitrarily long, no agent waits, destructive execution
remains exactly-once and recoverable, continuations receive precisely configured gate
evidence, status becomes a property of the shell that owns it, and gates and monitors
share their real common machinery without pretending they are the same product concept.
