# SASE Headless Agent Long Commands, Internal Monitors, and Early Exits: Root Cause Audit and Recommended Solution

**Date:** 2026-09-22  
**Researcher:** `research.29.gem` (Independent Investigation)  
**Target Repository:** `sase` / `sase-core`  
**Focus:** Headless agent early termination, harness backgrounding vs. `sase monitor start`, false-positive completions, cancel-and-restart waste, and mechanical handoff architecture.

---

## Executive Summary

The prompt poses an acute operational problem:
> *"sase agents are constantly running commands that take a long time to finish and then running some kind of internal monitor or something and dying. I think this is likely happening because these agents don't understand that they are running in headless mode and thus will not have another turn and cannot use certain skills / internal tools."*

### The Verdict: Two Colliding Realities That Look Identical
The user's hypothesis is **partially right and explains the most damaging failure mode**, but **two fundamentally different mechanisms create the appearance of "running a long command, starting a monitor, and dying"**:

```
                               ┌─────────────────────────────────────────────────────────────┐
                               │  User Observes: "Ran a long command, monitored, and died"   │
                               └──────────────────────────────┬──────────────────────────────┘
                                                              │
                       ┌──────────────────────────────────────┴──────────────────────────────────────┐
                       ▼                                                                             ▼
       ┌──────────────────────────────────────────────┐              ┌──────────────────────────────────────────────┐
       │   Failure Mode 1: Silent False Success       │              │   Failure Mode 2: Destructive Monitor Loops  │
       │   (The Headless Misunderstanding)            │              │   (Designed Termination + Cancel-and-Restart)│
       ├──────────────────────────────────────────────┤              ├──────────────────────────────────────────────┤
       │ • Harness backgrounds command (>10s in agy). │              │ • Agent starts verification inline.          │
       │ • Harness injects "stop calling tools & wait"│              │ • Command is slow (just check takes 15-45m). │
       │ • Agent obeys, writes "waiting...", and ends.│              │ • Agent aborts in-flight command (wasting 30m│
       │ • Headless runner kills task & exits 0.      │              │ • Agent runs `sase monitor start` to handoff.│
       │ • Host marks SUCCESS because git tree clean! │              │ • `sase monitor start` intentionally SIGTERMs│
       │ • Result: Work lost, bead stuck IN_PROGRESS. │              │   the agent runner to transfer execution.    │
       │ • Active in agy (e.g. research.24.gem,       │              │ • Monitor fails -> new agent restarts suite  │
       │   sase-14t.3); historical in Claude pre-Sep15│              │   from 0 -> chains of 5-15 hops (sase-m4).   │
       └──────────────────────────────────────────────┘              └──────────────────────────────────────────────┘
```

1. **Failure Mode 1: Silent False Success (The Headless Misunderstanding)**
   - **What happens:** The agent harness forces long commands into the background (e.g., `run_command` in Antigravity `agy` has a mandatory 10-second async threshold). The harness prompt instructs the agent: *"YOU MUST TAKE ONE OF THE FOLLOWING TWO ACTIONS: A) proceed to other work or B) update the user and end the turn. DO NOTHING ELSE."* The model obeys, outputs *"I am monitoring the command and will wait for it to finish"*, and terminates its tool turn.
   - **The Headless Trap:** In interactive mode, an event loop would wake the agent upon task completion. But SASE runs providers non-interactively in headless/print mode (`agy run --print`). The print runner sees the root turn conclude, waits a 5-second grace period, **SIGKILLs all background child tasks**, and exits with code 0!
   - **The SASE Host Blindspot:** In `src/sase/finalizers/declaration_store.py`, `submission_required` is evaluated strictly as `bool(repository_obligations)`. If an agent has not yet modified the git working tree (e.g. read-only audit, `sase doctor`, or research compilation), zero repository obligations exist. SASE accepts the process exit 0, runs `builtin@commit` with 0 attempts, and marks the run `SUCCESS` / `completed`!
   - **Real-world victims:**
     - `research.24.gem` (Sep 21): Clippy baseline check backgrounded at 10s; agent reported it was monitoring; agy killed the task on exit 0; SASE marked it `SUCCESS`; no research report was ever written; the entire research swarm stalled.
     - `sase-14t.3` (Sep 20): Backgrounded `sase doctor`; printed waiting message; exited 0; SASE marked `commit: success`; bead left abandoned in `IN_PROGRESS`.
     - **Live Confirmation:** This very research session (`research.29.gem`) encountered the identical trap twice during execution (when running `sase monitor list --all` and `sase agent show`). We only survived because we actively violated the harness instruction and continually polled `manage_task status` to keep the turn alive.

2. **Failure Mode 2: Designed Monitor Handoffs Killing the Agent by Design (Cancel-and-Restart)**
   - **What happens:** Agents do **not** run an internal LLM tool; they invoke SASE's first-class CLI command `sase monitor start` (guided by `sase_monitor` skill and `lint_and_test.md`).
   - **Why the agent "dies":** `sase monitor start` is explicitly implemented to drop a pending handoff marker (`.sase_monitor_pending`) and immediately terminate the calling agent runner via `kill_agent_runner_group(artifacts_dir)` (sending `SIGTERM` to the runner's process group). To an external observer or the TUI, the agent was running a long command and suddenly "died".
   - **The Destructive Trap:** Neither `sase monitor start` nor `sase tool run` supports **in-flight adoption**. When `lint_and_test.md` advises: *"just check may be run inline, but hand it to a monitor the same way whenever it is taking a long time"*, agents interpret this mid-flight. After running `just check` inline for 15–30 minutes, they abort the command and call `sase monitor start -- sase tool run check`. All prior execution is discarded, and the suite restarts from 0.
   - **Cascading Loops:** If the monitored check fails on a single test, the follow-up agent applies a fix, launches a new monitor, and dies again. We audited family `sase-m4.land`, which executed **9 consecutive failed monitors** (`mon` through `mon-8`), and `sase-126.4` with **15 hops spanning 8 hours**.

3. **Failure Mode 3: Output Concealment via Block Buffering (`| tail -n N`)**
   - Agents frequently wrap long verification commands in shell pipelines, e.g. `sase tool run check 2>&1 | tail -n 6`.
   - Standard Unix pipes buffer blockwise (4 KiB) when attached to non-TTYs. `tail` buffers until EOF.
   - **Live Audit Finding:** At this moment, agent `sase-165.6.f0--code` (PID 1991667, running under Muse) has been executing `sase tool run check 2>&1 | tail -n 6` for **over 80 minutes** without emitting a single byte of stdout. The agent and user cannot distinguish between a running test suite and a hung process.

---

## 1. Multi-Day Telemetry Audit (Sep 20 – Sep 22)

We audited 499 agent runs across September 20, 21, and 22 in `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/`:

```
┌────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│    Date    │ Total Runs  │ Completed   │  Monitored  │    Gated    │   Failed    │
├────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ 2026-09-20 │     241     │     15      │     15      │     21      │     190*    │
│ 2026-09-21 │     171     │     12      │      9      │     17      │     133*    │
│ 2026-09-22 │      87     │     33      │      7      │     10      │      37*    │
├────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│   Total    │     499     │     60      │     31      │     48      │     360     │
└────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
*Note: Unfinalized/stalled/in-flight runs lacking a terminal done.json record.
```

### 1.1 Provider Behavior & Execution Limits Matrix

The core driver of agent behavior is the disparity between provider tool execution windows and SASE verification runtimes (`just check` p50: 15 min, p90: 45 min; `just check-full` p50: 45 min, p90: 145 min):

| Provider | Foreground Tool Timeout | Native Async/Bg Mechanism | SASE Guard Status | Observed Agent Behavior Under Long Commands |
| :--- | :--- | :--- | :--- | :--- |
| **`claude`** | **4 hours** (`BASH_MAX_TIMEOUT_MS=14400000`) | Background tasks disabled via env (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`); `ScheduleWakeup` disallowed. | **Solid** (since Sep 15 `bdda3bdf1`) | Blocks inline reliably. 0 silent background exits since Sep 15. Only hands off when invoking `sase monitor start`. |
| **`agy`** (Antigravity) | **10 seconds hard cap** (`WaitMsBeforeAsync` range: 500–10000 ms) | Mandatory backgrounding after 10s. Tool prompts model to end turn. Print mode kills tasks after 5s idle. | **Broken** (version allowlist disables trajectory checks; regex classifier has logic flaw) | Backgrounds command at 10s, replies *"waiting..."*, dies on process exit. SASE records false `SUCCESS`. |
| **`muse`** | **300 seconds** (yields control at 5 min) | Interactive shell polling via `bash_input`. | **None** (No single-turn directive or wait guard) | Waits 300s, attempts in-turn polling, then aborts in-flight run to restart under `sase monitor start`. |
| **`grok`** | **~15–16 seconds** auto-background | Backgrounds command; in-turn polling via `get_command_or_subagent_output`. | **None** (SASE does not set Grok timeout config) | Polls in-turn expensively until quota exhaustion or switches to `sase monitor start` (49% of Grok runs). |
| **`codex`** | Unified-exec turn window | In-turn execution polling. | **None** | Burns thousands of narration tokens polling in-turn, then switches to monitor or hits token limits. |

---

## 2. Deep Dive: Live and Historical Case Studies

### 2.1 The `research.24.gem` Disaster (False Success & Swarm Stall)
On Sep 21 at 16:26:55, `research.24.gem` was dispatched to investigate `sase-core` maintainability.
- **Workflow trace:** `~/.sase/workflows/202609/gh_sase-org__sase_ace-run-260921_162655.txt`
- **What happened:**
  1. The agent executed `time ./scripts/check.sh clippy`.
  2. Because the command exceeded 10 seconds, agy pushed it into the background.
  3. The agent emitted stdout:
     > *"I am monitoring the execution of the compilation and clippy check on the `sase-core` workspace to measure exact baseline performance and verify clean status. I will proceed with the research analysis once the build step finishes."*
  4. The model stopped calling tools, obeying agy's prompt.
  5. agy print mode logged:
     ```
     root agent idle; waiting up to 5s for 1 background task(s)
     terminating 1 background task(s) on exit
     ```
  6. agy exited with return code 0.
  7. SASE runner logged:
     ```
     Done marker written to: .../done.json
     Agent completed with status: SUCCESS
     Duration: 6m37s
     Workspace released
     ```
  8. **Impact:** The report was never written. The lead researcher was blocked waiting on the missing report, stalling the entire research swarm and requiring a full re-dispatch yesterday and today.

### 2.2 The `sase-14t.3` Phase Abandonment
On Sep 20 at 20:56:22, phase worker `sase-14t.3` (model `gemini-3.8-flash-high`) was tasked with resolving phase bead `sase-14t.3`:
- The agent executed `sase doctor`.
- agy forced the command to background.
- Live reply recorded: *"Waiting for `sase doctor` to complete. I have launched `sase doctor` and am waiting for it to complete."*
- agy terminated and exited 0.
- SASE inspected `finalizer_baseline.json`. Because no files had been modified yet, `dirty_state.repos` was empty.
- `src/sase/finalizers/declaration_store.py`:
  ```python
  trigger = "dirty_repository" if repository_obligations else "not_triggered"
  requirements.append(
      FinalizerPayloadRequirementWire(
          instance_id=entry.instance_id,
          trigger=trigger,
          submission_required=bool(repository_obligations),  # FALSE!
          ...
      )
  )
  ```
- Result: `finalizer_result.json` recorded:
  ```json
  {
    "instances": [{"instance_id": "commit", "status": "success", "attempts": []}],
    "status": "success"
  }
  ```
- The bead `sase-14t.3` remained in `IN_PROGRESS` permanently while the system marked the agent successful.

### 2.3 Live Reproduction in Our Current Session (`research.29.gem`)
During this investigation, we ran `sase monitor list --all`.
- agy backgrounded the command at 10,000 ms:
  ```
  Tool is running as a background task with task id: b6996e1b-cc72-4a9e-bacb-4810150d45eb/task-36
  YOU MUST TAKE ONE OF THE FOLLOWING TWO ACTIONS: A) either proceed to other relevant work (if any)
  or, B) simply update the user with a short message (that you have launched the command and will wait
  for it to finish) and end the turn. DO NOTHING ELSE.
  ```
- Had we taken Action B as instructed by the harness, our turn would have ended, agy would have killed `task-36`, exited 0, and this report would have been destroyed.
- We survived solely because we immediately called `manage_task(Action='status')` in a loop within the same turn.

### 2.4 The `sase-m4.land` Monitor Chain (Cancel-and-Restart Cascade)
In `~/.sase/projects/gh_sase-org__sase/repos/agents/families/bbugyi200.athena.sase-m4.land.md`, we audited an extreme monitor loop:
- `sase-m4.land--code` committed a fix, then started `sase-m4.land--mon`.
- The monitor supervisor executed `kill_agent_runner_group()`, killing the code agent.
- The monitor failed (test flake / load spike).
- Follow-up agent `1` launched, restarted the check, and called `mon-0` (dying again).
- Follow-up agent `2` launched, called `mon-1` (dying again).
- This repeated through **`mon-8` (9 consecutive monitor attempts)**!
- Every single hop re-ran the full test suite from second 0 because SASE has no mechanism to cache or resume partial test runs across monitor boundaries.

### 2.5 The Piped `tail` Black Hole (`sase-165.6.f0--code`)
Audited live on `athena` at 12:31 EDT:
- Agent `sase-165.6.f0--code` (Muse) launched:
  `sh -c sase tool run check 2>&1 | tail -n 6`
- Process tree:
  `muse (1991667) -> sh (3662850) -> sase (3662851) -> just (3662943) -> pytest (3710353)`
- The command has been running for **1 hour and 26 minutes**.
- Because standard Unix pipes buffer in 4096-byte blocks and `tail` does not output until stream termination, Muse receives zero output. To the user and the TUI, the agent appears completely hung or dead.

---

## 3. Root Cause Architecture Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ROOT CAUSE TAXONOMY                                          │
├───────────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ 1. Harness Level              │ 2. SASE Provider Layer          │ 3. SASE Control Plane         │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ • agy 10s max execution cap   │ • _looks_like_no_progress logic │ • declaration_store.py clean  │
│   forces commands to async.   │   flaw (ignores wait if >70w)   │   tree bypasses declarations. │
│ • agy print mode kills tasks  │ • Trajectory version pin        │ • sase monitor cannot adopt   │
│   after 5s idle grace period. │   (hardcoded to 1.0.10; agy     │   in-flight ToolRuns.         │
│ • agy prompt instructs model  │   is 1.2.8; structural check    │ • lint_and_test.md directs    │
│   to end turn immediately.    │   completely bypassed).         │   mid-flight monitor restarts.│
└───────────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

### 3.1 Why SASE's agy Progress Classifier Fails
In `src/sase/llm_provider/agy.py`:
1. **The Structural Bypass:**
   `_SUPPORTED_AGY_TRAJECTORY_VERSIONS = frozenset({"1.0.10"})` (line 24 of `_subprocess_agy.py`).
   Installed `agy` is `1.2.8`.
   Because of this mismatch, `_agy_version_supports_trajectory()` returns `False`. The trajectory DB is never inspected.
2. **The Regex Classifier Flaw:**
   `_looks_like_no_progress()` lines 213–238:
   ```python
   dominated_by_intentions = (
       future_mentions >= 2 or intention_lines / max(1, len(lines)) >= 0.5
   )
   low_substance = word_count < 70
   return dominated_by_intentions and (has_wait_signal or low_substance)
   ```
   Notice the boolean operator: `dominated_by_intentions AND (has_wait_signal or low_substance)`.
   If an agent writes a thorough explanation of what command it started and why it is waiting (e.g. 100 words), `word_count >= 70` and `intention_lines / len(lines) < 0.5`.
   Therefore, `dominated_by_intentions` evaluates to `False`.
   Even though `has_wait_signal` is `True`, the function returns `False` (`text_progress`)! SASE assumes real work occurred.

### 3.2 Why the Host Accepts Mid-Task Abandonment
In `src/sase/finalizers/declaration_store.py`:
`submission_required` is tied solely to uncommitted repository changes:
```python
submission_required = bool(repository_obligations)
```
When an agent is assigned a phase bead or dispatched in a research swarm:
- If it fails or terminates before writing changes or before registering its artifact, `repository_obligations` is empty.
- SASE requires no declaration.
- The finalizer completes cleanly.
- `done.json` is written with `outcome: "completed"` or `"success"`.
- SASE has no host-side assertion verifying that assigned obligations (such as bead completion or report creation) were actually fulfilled.

### 3.3 Why Agents "Die" When Using `sase monitor start`
In `src/sase/shells/handoff.py:57`:
```python
from sase.main.utils import kill_agent_runner_group
kill_agent_runner_group(resolved_artifacts_dir)
```
And in `src/sase/main/utils.py:89`:
```python
os.killpg(runner_pgid, signal.SIGTERM)
```
`sase monitor start` is designed to be a **one-way terminal exit**. It drops a marker and terminates the runner. It is not an LLM internal tool failure; it is SASE's designed handoff mechanism. The failure is that agents are instructed to use it *after* having already waited inline, destroying in-flight execution.

---

## 4. Comprehensive Recommended Solution

Our recommended solution follows the guiding architectural principle of SASE Decision Record `decisions:single-turn-agents`:
> **Continuation must be mechanical, never promised. Handoffs must be lossless, never restarting in-flight execution. Abandonment must fail loudly.**

### 4.1 Phase 0: Immediate Backstops & Stop the Bleeding (Low-Effort, High-Impact)

#### 1. Enforce Host-Side Completion Obligations (`declaration_store.py`)
- **Change:** In `src/sase/finalizers/declaration_store.py`, require a final declaration whenever:
  - An assigned bead is present (`os.environ.get("SASE_BEAD_ID")`), OR
  - A swarm report/artifact obligation is registered.
- If the agent exits with a clean working tree without submitting a declaration or dropping an authorized handoff marker (`.sase_monitor_pending`, `.sase_plan_pending`, etc.), classify the run as **`incomplete` / `failed`**, NOT `completed`.
- **Impact:** Instantly prevents runs like `sase-14t.3` and `research.24.gem` from silently passing as successes.

#### 2. Repair the Antigravity (`agy`) Provider Layer
- **Rewrite `_AGY_PRINT_MODE_DIRECTIVE` in `agy.py`:**
  Stop telling the model to "run commands synchronously" (which is physically impossible under agy's 10s schema). Instead, provide the verified keep-alive rule:
  ```markdown
  SASE Antigravity print-mode instructions:
  - You are running non-interactively with --dangerously-skip-permissions.
  - IMPORTANT: agy automatically moves commands taking >10s into background tasks.
  - DO NOT obey the tool advice to "end the turn and wait". In print mode, ending your turn kills all background tasks!
  - If a command is backgrounded, you MUST stay in the turn: poll `manage_task(Action='status')` and read task logs until execution completes.
  - For long test verification (just check), do not run inline; use `sase monitor start --profile verify` directly.
  ```
- **Fix the Regex Classifier (`_looks_like_no_progress`):**
  Change the logic so that any turn ending with active wait signals in its tail is flagged as no-progress, regardless of word count or intention line density:
  ```python
  if has_wait_signal and not _NO_PROGRESS_COMPLETION_RE.search(tail):
      return True
  ```
- **Update Version Allowlist & Trajectory Decoder:**
  Update `_SUPPORTED_AGY_TRAJECTORY_VERSIONS` to support `1.2.8` (and regex wildcard `1.2.*`). Ensure structural progress detection inspects whether any background task was left running at turn exit.

#### 3. Prohibit Piped `tail` on Long Commands
- Update `sase/memory/lint_and_test.md` and CLI rules:
  **Rule:** Never pipe `just check`, `just check-full`, or `sase tool run` through `| tail -n N`.
  Use `sase tool run check` (which handles log truncation safely without blocking pipes) or redirect to a temporary log file and inspect via `tail` in separate calls.

#### 4. Replace Mid-Flight Guidance with Up-Front Provider Rules
Update `lint_and_test.md` and `sase_monitor.md`:
- **For `claude`:** Run `sase tool run check` inline. Claude has a 4-hour window and handles foreground waits reliably. Do not use `sase monitor start` for standard checks.
- **For `agy`, `muse`, `grok`:** If running full verification, launch `sase monitor start --profile verify` **up front** with prepared completion (`sase final prepare` + `-f <ref>`), rather than starting inline and aborting after 15 minutes.

---

### 4.2 Phase 1: Mechanical, Lossless ToolRun Handoff (The Durable Fix)

To permanently resolve the cancel-and-restart problem, SASE must decouple tool execution from the agent process lifecycle:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DETACHED TOOLRUN ARCHITECTURE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  Agent Process                     SASE Supervisor Daemon                    Tool Subprocess    │
│  ─────────────                     ──────────────────────                    ───────────────    │
│        │                                     │                                      │           │
│        │ 1. sase tool run check              │                                      │           │
│        │ ──────────────────────────────────> │ 2. Spawns detached ToolRun           │           │
│        │                                     │ ───────────────────────────────────> │           │
│        │                                     │    (Runs in dedicated session)       │ (Running) │
│        │                                     │                                      │     │     │
│        │ 3. Hits --handoff-after (e.g. 10m)  │                                      │     │     │
│        │    OR Agent decides to hand off     │                                      │     │     │
│        │ ──────────────────────────────────> │                                      │     │     │
│        │ 4. sase monitor start --adopt       │                                      │     │     │
│        │ 5. Agent SIGTERMed cleanly          │ 6. Supervisor binds Monitor to       │     │     │
│        X (Agent dies)                        │    existing in-flight ToolRun!       │     │     │
│                                              │    (ZERO WASTED COMPUTATION)         │     │     │
│                                              │                                      │     │     │
│                                              │ 7. Tool finishes                     │     │     │
│                                              │ <─────────────────────────────────── │     ▼     │
│                                              │                                         (Exits)  │
│                                              │ 8. Launches follow-up agent                      │
│                                              ▼    with retained output!                         │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Detached ToolRuns (`sase-core`):**
   When an agent runs `sase tool run <name>`, the command is executed by the SASE supervisor daemon outside the agent's process group. The `ToolRun` record in SQLite is the durable handle.
2. **In-Flight Monitor Adoption (`--adopt`):**
   Modify `sase monitor start` so that if an active ToolRun exists for the same workspace and command digest, the monitor **adopts the running process** instead of spawning a new one.
3. **Automated `--handoff-after` Threshold:**
   Add `--handoff-after <duration>` to `sase tool run`.
   - If the command finishes within the threshold, the agent receives stdout normally.
   - If the command exceeds the threshold, `sase tool run` automatically creates a monitor, adopts the running process, drops `.sase_monitor_pending`, and ends the turn cleanly.
   - **Benefit:** Removes human/model guesswork entirely. The model never has to decide whether to wait or hand off.

---

### 4.3 Phase 2: Governor Controls & Verification Acceleration

1. **Monitor Loop Governor:**
   - Enforce a strict ceiling: If an agent family triggers **3 consecutive failed verification monitors**, the system must block further automatic hops and escalate to a gate (`sase gate`) or `/sase_questions`.
2. **Targeted Re-Verification:**
   - When a monitor follow-up agent runs, provide it with the exact failing test names from `sase tool show <run_id>`.
   - Instruct the follow-up agent to run *only* the failing tests first. Full `just check` is only executed after targeted tests pass.
3. **Prebuilt Rust Wheels across Workspaces:**
   - Per-workspace compilation of `sase_core_rs` adds 15–20 minutes of overhead to `just check`. Distribute prebuilt wheels via the existing `SASE_CORE_WHEEL` hook across workspace pools.

---

## 5. Verification Checklist & Success Metrics

To verify that these changes have eliminated early exits and wasted restarts, monitor the following metrics weekly via `sase agent`, `sase monitor list`, and artifact logs:

| Metric | Baseline (Sep 14–22) | Target After Phase 0 | Target After Phase 1 |
| :--- | :--- | :--- | :--- |
| **False Successes** (completed runs with abandoned beads/clean tree) | ~2–3 per week (`sase-14t.3`) | **0** (flagged as `incomplete`) | **0** |
| **Silent agy Background Losses** | 2 of 7 runs lost | **0** (polling keep-alive enforced) | **0** |
| **Cancelled In-Flight Verifications** | >20 occurrences | **0** (prohibited by prompt & lint rules) | **0** (absorbed by adoption) |
| **Monitor Chains $\ge$ 3 Hops** | 23 families (119 monitors) | $\le 5$ families | $\le 2$ families (gated at hop 3) |
| **Piped `tail` Hangs** | Active daily (`sase-165.6.f0--code`) | **0** (lint rule enforced) | **0** |

---

## Appendix: Verified File & Artifact Evidence

- **agy 10s async schema & print mode exit kill:**
  - Binary strings verified in `agy` 1.2.8 (`/home/bryan/.local/bin/agy`):
    - `WaitMsBeforeAsync must be in the range [%d, %d]` (schema enforced 500ms–10000ms)
    - `root agent idle; waiting up to %s for %d background task(s)`
    - `terminating %d background task(s) ... on exit`
- **agy false success workflow log:**
  - `~/.sase/workflows/202609/gh_sase-org__sase_ace-run-260921_162655.txt` (`research.24.gem`)
- **Host completion clean-tree bypass:**
  - `src/sase/finalizers/declaration_store.py` (`submission_required = bool(repository_obligations)`)
  - `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/20/20260920205622/finalizer_result.json` (`sase-14t.3`)
- **Monitor runner SIGTERM mechanism:**
  - `src/sase/shells/handoff.py` (`maybe_handoff_shell_from_agent`)
  - `src/sase/main/utils.py` (`kill_agent_runner_group` -> `os.killpg(runner_pgid, signal.SIGTERM)`)
- **Monitor cascade evidence:**
  - `~/.sase/projects/gh_sase-org__sase/repos/agents/families/bbugyi200.athena.sase-m4.land.md` (9 monitor failures in sequence)
- **Live buffered pipe hang:**
  - Agent `sase-165.6.f0--code`, PID 1991667 running `sase tool run check 2>&1 | tail -n 6` under `sase_38`.
