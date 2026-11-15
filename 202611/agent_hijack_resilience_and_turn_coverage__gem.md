# Agent Hijack Failure Diagnosis, Turn-Coverage Audit, and Resilience Architecture

**Context:** Failure report against `~/tmp/screenshots/20261115_164112.png` (captured on `apollo`, `sase tui v0.19.0+45.g9793a95a5`, session `tailnet-t.10`)  
**Goal:** Diagnose why Agent Hijacks are failing in practice, evaluate the requirement to make hijacks work across as many `sase` turn types and states as possible, propose justified requirement adjustments, and recommend an end-to-end implementation plan.

---

## 1. Executive Summary

Agent Hijack is currently broken at **multiple independent layers simultaneously**, meaning fixing any single bug still leaves real sessions unhijackable or corrupts recovery afterward:

1. **TUI rejects almost all real agents outright:** `agent_can_offer_hijack()` (`src/sase/ace/tui/actions/agents/_hijack_action.py`) hard-requires `agent.agent_type is AgentType.RUNNING`, whereas `setup_artifacts_directory` / `create_followup_artifacts()` write `workflow_state.json` (`appears_as_agent: True`), and `dedup_running_vs_workflow()` keeps `AgentType.WORKFLOW` while dropping `AgentType.RUNNING`.
2. **Runner bootstrap and follow-up handoffs silently wipe `"hijack"` capability:** `_write_bootstrap_agent_meta()` writes `runner_capabilities: ["hijack"]`, only for `extract_directives_and_write_meta()` (`src/sase/axe/run_agent_runner_bootstrap.py`) to overwrite `agent_meta.json` using `preserved_agent_metadata()`, whose allow-list omits `"runner_capabilities"`. Follow-up artifact creation (`create_followup_artifacts()`) omits `"runner_capabilities"` too. So Rust `eligibility.rs` rejects even CLI hijacks with `missing_capability` (`"launched before hijack support; use x"`).
3. **Collapsed session selection and dual-turn finalization (`tailnet-t.10` in the screenshot):** Selecting collapsed `tailnet-t.10` evaluates hijack eligibility against the completed `--plan` root container instead of delegating to active turn(s) (`10 --5 ▶` finalizing + `11 --mon-3 ▶` running simultaneously). Worse, even after hijacking a member turn, `_mirror_root_from_child()` omits `hijack_record` and member identity fields, breaking `⏎` recovery when collapsed.
4. **Downstream recovery/evidence schema drift:** `_stop_target.py` reads stale/wrong keys (`agent_llm_provider`, `agent_effort`, `booted_at` float, `gate_turn`), causing missing `provider` / `effort` / duration and making `require_concrete_target()` fail recovery (`RecoveryRefusal("invalid_model_target", ...)`). `_stop_evidence.py` also misses opened linked/sibling repos recorded in `opened_linked_workspaces.json` / `opened_siblings.json` and `LinkedRepoResolution` dicts.

Expanding hijacks across more turn types and states is **strongly worthwhile**, **provided we adjust the requirement away from uniform workspace-holding hijack everywhere**: hijack should target the **active workspace-claiming lane**, preempt hung `finalizing` states carefully, support `Monitor` turns and stuck `settling` gates with turn-appropriate recovery actions, and keep workspace-less pre-run (`WAITING`/`QUEUED` at `ws #0`), idle human gates, and `$HOME`/unisolated `home_mode` turns out of fake exclusive workspace custody.

---

## 2. Root-Cause Diagnosis of `~/tmp/screenshots/20261115_164112.png` (`apollo`)

In the screenshot (`apollo`, `sase tui v0.19.0+45.g9793a95a5`):
- The selected row in the Agents tab is the **collapsed session container** `tailnet-t.10`.
- The `JUMP` panel (`SESSION TURNS 00-11`) shows two live member turns at once: `10 --5 ▶` (blue) and `11 --mon-3 ▶` (yellow).
- The footer on the right pane displays `final running · record -`.
- Live session artifacts show `--plan` already completed (`done.json: outcome="completed"`), turn `--5` (`20261115163657`, `pid: 2266250`) is in `finalizer_status` phase `declaring`/`executing` (`final running`) and has staged `--mon-3` (`20261115164035`), which is simultaneously running.

Four interacting bugs block hijack in this exact scenario (and on ordinary runs):

| Layer | File / Symbol | Observed Behavior | Impact in Screenshot & General Runs |
| :--- | :--- | :--- | :--- |
| **1. TUI type filter** | `src/sase/ace/tui/actions/agents/_hijack_action.py:23` | `if agent.agent_type is not AgentType.RUNNING: return False` | Rejects nearly every `ace-run` / follow-up agent because `workflow_state.json` (`appears_as_agent: True`) makes `dedup_running_vs_workflow()` surface `AgentType.WORKFLOW` instead of `AgentType.RUNNING`. User immediately sees `"Selected agent is not eligible for hijacking"`. |
| **2. Collapsed container & Enter-key mirroring** | `_start_hijack_agent()` (`_hijack_action.py`); `_mirror_root_from_child()` (`src/sase/ace/tui/models/_agent_status_apply.py:49-98`) | Evaluates eligibility on the collapsed parent row itself (`--plan`, `completed`) rather than delegating to live member turn(s) like `x` (`_kill_action_flow.py` / `confirmation_sase_agent_entries(..., include_running_agent_session_members=True)`). Also never copies `hijack_record`, `pid`, `artifacts_dir`, `agent_name`, `is_monitor`, or `is_gate` to parent. | Clicking/pressing `,k` -> `h` on `tailnet-t.10` tests the completed root container (`completed`), never `--5`. Even if a member is hijacked externally, pressing `⏎` on collapsed `HIJACKED` `tailnet-t.10` hits `getattr(agent, "hijack_record", None) -> None` -> `"Recovery details are unavailable; refresh the Agents tab"`. |
| **3. Capability clobber & follow-up omission** | `src/sase/axe/run_agent_runner_bootstrap.py:150-160, 421, 467`; `run_agent_directive_metadata_preserved.py`; `run_agent_helpers_artifacts.py`; `eligibility.rs:55-56` | `_write_bootstrap_agent_meta()` adds `HIJACK_RUNNER_CAPABILITY` (`"hijack"`), then `extract_directives_and_write_meta()` overwrites `agent_meta.json` cleanly via `write_agent_meta_atomic()` merging `preserved_agent_metadata()`, which omits `"runner_capabilities"`. `create_followup_artifacts()` also omits `"runner_capabilities"`. | Even bypassing TUI via `sase agent hijack`, Rust `eligibility.rs` rejects with `("missing_capability", "launched before hijack support; use x")`. |
| **4. Finalizing & dual active turn (`--5` + `--mon-3`)** | `sase/repos/linked/sase-core/crates/sase_core/src/agent_hijack/eligibility.rs:28-36` | Refuses `finalizer_status.phase` in `"declaring" \| "executing" \| "finalizing"` (`"finalizing; try again in a moment"`) and refuses `is_monitor_turn` (`"monitor turns cannot be hijacked"`). | With `--5` in `final running` and `--mon-3` live in the same session, neither turn is eligible. And if `--5` finishes finalizers after transferring claims to `--mon-3`, there is no lane-level preemption covering `--mon-3`. |

### Additional Latent Bugs Discovered Beyond the Screenshot

5. **Metadata Key Mismatch Breaks Hijack Recovery (`_stop_target.py` vs Metadata Writers):**
   - `src/sase/axe/run_agent_directive_metadata_build.py:84-89` writes `"model"`, `"llm_provider"`, `"reasoning_effort"`. Lifecycle bootstrap (`boot_code_identity` in `runner_lifecycle_phase.py`) writes ISO string `"booted_at"`, and `create_followup_artifacts()` writes ISO string `"run_started_at"`. Turn creation (`src/sase/turns/member.py`) writes `meta[TURN_KIND_KEY]` (`"turn_kind": "gate"` or `"monitor"`).
   - Meanwhile `src/sase/agent/hijack/_stop_target.py:78, 85-89` reads:
     - `is_gate_turn=_meta_bool(meta, "gate_turn", "is_gate_turn")` (misses `turn_kind == "gate"`)
     - `provider=_meta_str(meta, "agent_llm_provider", "provider")` (misses `"llm_provider"` -> `None`)
     - `model=_meta_str(meta, "agent_model", "model")` (hits `"model"`, bare e.g. `"gpt-6-luna"`)
     - `effort=_meta_str(meta, "agent_effort", "effort")` (misses `"reasoning_effort"` -> `None`)
     - `run_started_at=_meta_float(meta, "booted_at", "started_at")` (fails float conversion on ISO string `"booted_at"` -> `run_duration_seconds=None`)
   - Downstream, `concrete_model_target()` (`_preview_values.py`) and `predecessor_concrete_target()` (`recover_common.py`) receive bare `"gpt-6-luna"` with `provider=None`, causing `require_concrete_target()` (`recover_target.py`) to refuse Escalate/Continue/Instruct with `RecoveryRefusal("invalid_model_target", ...)`.
6. **Evidence Capture Misses Linked / Dynamically Opened Repos (`_stop_evidence.py`):**
   - `src/sase/agent/hijack/_stop_evidence.py:77` searches `("opened_repos", "linked_repos", "sidecar_repos", "repo_roots")` expecting `list[str]`.
   - In reality, `run_agent_runner_setup_linked_repos.py` writes `LinkedRepoResolution.to_jsonable()` (`list[dict]`) into `agent_meta["linked_repos"]`, and dynamically opened repos are stored in `opened_linked_workspaces.json` and `opened_siblings.json` (which `recover_settle.py` reads via `sase._linked_repo_markers.opened_repo_records()`). Hijack diffs miss dirty linked/sidecar checkouts while recovery checks workspace transfer fail-closed (`_observe_repo_transfer`).
7. **Why Existing Tests Passed Despite Total Production Failure:**
   - `tests/ace/tui/test_agent_hijack_action.py` constructs synthetic `Agent(agent_type=AgentType.RUNNING, ...)` directly, skipping `load_all_agents()` / `dedup_running_vs_workflow()`.
   - `tests/test_agent_hijack_stop.py` and `tests/fakey/test_agent_hijack_e2e.py` hardcode `"runner_capabilities": ["hijack"]` and legacy keys (`agent_model`, `agent_llm_provider`, `agent_effort`) directly into `agent_meta.json`, bypassing `run_agent_runner_bootstrap.py` and `extract_directives_and_write_meta()`.

---

## 3. Comprehensive Audit of SASE Turn Types, Lifecycle States & UI Topologies

Before deciding what *should* be hijackable, below is the full matrix of SASE turns, statuses (`src/sase/agent/status_buckets.py`, `src/sase/axe/runner_lifecycle_phase.py`), and TUI row topologies:

### A. By Turn Kind & Lifecycle State

| Turn Kind | Status / Phase | Current Behavior | Has Held Workspace (`ws #N`)? | Live Process / Subprocesses? | Should Hijack Work? & Ideal Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agent** (`turn_kind` unset / `"agent"`) | `RUNNING` (`provider_running`) | TUI fails (`AgentType.WORKFLOW`); CLI fails (`missing_capability`) | Yes (`ws #N > 0`) | Yes (runner + LLM provider) | **Yes — Standard Hijack.** Stop PID group, keep workspace #N locked, capture diffs + log, offer Continue / Escalate / Instruct / Restart / Edit Prompt / Dismiss. |
| **Agent** | `STARTING` (`booting`, `preparing`) | TUI accepts if `RUNNING` + PID set + `ws > 0`; CLI accepts | Maybe (deferred claim may still be `ws #0` or `pid is None`) | Launching runner / workspace checkout | **Yes (two subcases).** If `ws > 0` & PID exists: standard hijack. If still in `booting`/`preparing` pre-PID or `ws == 0`: stop/cancel startup cleanly (either wait briefly for PID/ws, or cancel-to-edit-prompt without locking fake ws). |
| **Agent** | `RETRYING`, `RESTARTING`, `ANSWERED`, `PLAN COMMITTED`, `EPIC APPROVED` | `eligibility.rs` **only** accepts `"RUNNING" \| "STARTING" \| "RETRYING"`; TUI matches that subset | Yes (`ws #N`) | Yes (restarting, consuming retry/answer/plan-accept transition) | **Yes — Expand to all `ACTIVE_AGENT_STATUSES`.** `RESTARTING`, `ANSWERED`, `PLAN COMMITTED`, and `EPIC APPROVED` are active execution transitions with a live workspace/runner and should not return arbitrary not-eligible failures. |
| **Agent** (`--plan` / `--tale`) | `WORKING PLAN`, `WORKING TALE` | **Refused** by both `_hijack_action.py` and `eligibility.rs`! | Yes (`ws #N`) | Yes (planner/storyteller provider turn) | **Yes.** Planner/storyteller turns burn just as much time/quota or go down wrong tracks; hijacking with Escalate / Instruct / Edit Prompt (preserving `--plan` / `--tale` directive context where appropriate) is critical. |
| **Agent** | `WAITING`, `QUEUED` (`PRE_RUN_WAIT_STATUSES`, `waiting.json`) | Refused (`status` mismatch; often `workspace_num == 0` due to deferred claim) | Usually **No** (`ws #0` deferred), unless pre-claimed on `ws #N` | Waiting runner barrier (`run_agent_wait.py`) | **Conditional / Adjusted.** If holding `ws #N`: allow workspace-holding hijack. If `ws #0` (no workspace claimed yet): do **not** put in workspace-holding `HIJACKED` state; offer **Hold/Unblock/Edit & Relaunch/Cancel** instead (see §4). |
| **Agent** | `provider_done`, `finalizing`, `handoff` (`declaring` / `executing` / `finalizing`) | Hard refused (`"finalizing; try again in a moment"`) | Yes (`ws #N`), unless transferring claim | Finalizers, git stitch, hooks, staged monitor/successor | **Yes — Bounded Drain + Force Preemption.** Wait ~1.5s in case natural completion finishes cleanly; if hung, terminate finalizer process group, cancel staged unlaunched handoffs (or capture active co-turn), warn in recovery panel that finalizers were interrupted mid-flight. |
| **Agent** | `home_mode` (`is_home_mode=True`) | Refused (`"home-mode turns cannot be hijacked"`) | **No** (runs in `$HOME` / primary checkout) | Yes | **Keep excluded from workspace custody** (or offer lightweight stop-and-edit without locking `$HOME` or snapshotting `$HOME`). See §4. |
| **Monitor** (`--mon-N`, `turn_kind="monitor"`) | Running (`monitor/supervise.py` active) | Hard refused (`is_monitor`, `monitor_turn`) | Yes (typically `ws #N` shared/inherited from producer) | Yes (shell command + monitor supervisor) | **Yes — Adapted Monitor Hijack.** Stop monitor process group cleanly, retain `ws #N` custody, inspect diffs + monitor log tail, recover via **Spawn Follow-up Agent**, **Restart Command**, or **Dismiss** (hide LLM Escalate/`#fork:` Continue). |
| **Monitor** (`--mon-N`) | Stalled / Failed / Stopped with held workspace | N/A (not active status) | Potentially dirty `ws #N` | No | **Nice-to-have / Reuse Recovery UI** or integrate monitor follow-up actions cleanly (out of active-turn critical path). |
| **Gate** (`--gate-N`, `turn_kind="gate"`) | Pending human (`EPIC`, `TALE`, `PLAN`, `QUESTION`) | Hard refused (`is_gate`, `gate_turn`) | Workspace/branch held pending review | **No** (awaiting human input) | **No (Redirect to Review).** Refusal should be helpful: `"Awaiting your decision — press Enter to approve, reject, or send feedback"`. Human feedback/rejection already cleanly handles pivoting. |
| **Gate** (`--gate-N`) | `settling` (post-decision script / `run_agent_exec_plan_accept.py` hung) | Refused (`gate_turn` + non-`RUNNING` status) | Yes (`ws #N`) | Yes (settling/commit/handoff process) | **Yes!** If a gate's post-decision transition hangs during SDD commit, coder promotion, or handoff launch, allow hijacking into `HIJACKED` so work and approved plan state aren't lost. |
| **Any** | Terminal (`completed`, `failed`, `STOPPED`) | Refused | Usually released | No | **No.** Already finished (except possibly orphaned workspace cleanup, which `sase` already handles separately). |

### B. By TUI Row Topology / Ownership

| Row Shape | Current Behavior | Required Behavior |
| :--- | :--- | :--- |
| **Standalone `AgentType.WORKFLOW` (`appears_as_agent: True`)** | Broken by `_hijack_action.py:23` | Treated cleanly as an ordinary single hijackable agent turn. |
| **Collapsed sequential session container (e.g. `tailnet-t.10`)** | Broken: evaluates parent (`--plan`), hides `--5` & `--mon-3`; `⏎` fails when collapsed after hijack | Automatically resolve to the **active lane member(s)** (shared with CLI by session name); mirror `hijack_record` & recovery fields onto collapsed container so `⏎` opens the recovery panel directly. |
| **Co-active session members on same lane (`--5` finalizing + `--mon-3` active)** | Neither eligible; no coordinated stop | Resolve/preempt the **active lane** atomically: stop finalizing parent (if alive) + active `--mon-3` supervisor, reconcile `monitor_handoff_claim_transferred`, hold `ws #N` once under one record. |
| **Parallel Clan container (`is_clan_container`)** | Refused (`agent_can_offer_hijack` returns `False`) | Mirror `x` kill semantics: either prompt which member(s) to hijack or hijack all live members cleanly (per-member custody since clan members hold distinct workspaces). |
| **Multi-step workflow (`appears_as_agent: False`, `is_workflow_child`)** | Refused unless leaf matches `RUNNING` | Do not hijack an isolated bash/python sub-step leaving sibling orchestration alive; either hijack an active `agent` step safely or cancel at the workflow coordinator boundary. |
| **Named Service Proc (`is_named_proc`)** | Refused | Keep excluded — service procs are background daemons, not workspace agent turns. |
| **Remote / Fleet Agent (`fleet_origin_alias`, `is_local=False`, `imported_source_owner`)** | Refused locally | Keep excluded from **local** hijack orchestration; if supported later, dispatch explicitly via remote RPC (`sase agent hijack` on origin machine) rather than letting local TUI touch local PIDs/paths. |

---

## 4. Critique of the Proposed Goal & Justified Requirement Adjustments

The core instinct in the request — *"make hijacks work on as many types of sase turns in as many states as possible, and make them much more resilient / dependable"* — hits real pain points, because today's hijack feature fails on virtually every real session (`AgentType.WORKFLOW`, missing `runner_capabilities`, collapsed containers, `WORKING PLAN`, `finalizing`, dual `--5`+`--mon-3` transitions).

However, **treating "work across every turn type and state" as forcing every turn into the identical `⏏ HIJACKED` workspace-holding state machine is a mistake.** SASE's current hijack design (`custody.py` + `recover.py` + `eligibility.rs`) embeds four strong assumptions:
1. There is a live local OS process/process-group to interrupt.
2. There is an exclusive numbered workspace (`ws #N > 0`) to lock and snapshot.
3. There is an LLM model/provider/prompt lineage to **Escalate** or **Continue (`#fork:`)**.
4. Recovery yields a successor LLM turn inheriting that prompt and model lineage.

When a turn violates one or more of those assumptions, jamming it into `⏏ HIJACKED` creates workspace claim bugs, meaningless UI buttons, or corrupted recovery state. Furthermore, the architecture currently suffers from **split-brain eligibility** (TUI Python checks vs Rust `eligibility.rs`) and **unvalidated metadata keys** (`_stop_target.py` vs `agent_meta.py`), which undermines dependability more than missing edge states do.

### Explicitly Called-Out Requirement Adjustments

1. **Adjustment 1 — Separate Workspace-Holding Hijack from Pre-Workspace Wait Control (`WAITING` / `QUEUED` at `ws #0`):**
   - *Adjustment:* Turns waiting on dependencies/timers with deferred workspace claims (`workspace_num == 0`) should **not** enter workspace-holding `HIJACKED` state. Provide a lightweight **Pause / Edit Prompt / Cancel** flow (or reuse cancel/relaunch) when `ws == 0`, reserving full `HIJACKED` custody for queued turns that already pin a workspace (`ws #N > 0`).
   - *Why justified:* There is no workspace diff to preserve and allocating/locking a fresh workspace just to stop a queued turn wastes limited workspace slots and misleads recovery UI.

2. **Adjustment 2 — Exclude Pending Human Gates (`PLAN`/`TALE`/`EPIC`/`QUESTION`), Include Stuck `settling` Gates:**
   - *Adjustment:* Do **not** make idle human-waiting gates hijackable (`"Already awaiting your decision — press Enter to approve, edit, or send feedback"`). **Do** make gates stuck in `settling` (hung commit/coder/handoff promotion) hijackable.
   - *Why justified:* An awaiting gate is already paused cleanly with zero running provider process and first-class feedback/reject actions on `⏎`. Hijacking it duplicates review UX while risking lost `sdd` / plan approval state. Conversely, a hung `settling` gate leaves a live process and pinned workspace stuck where `x` would lose work.

3. **Adjustment 3 — Adapt Monitor Hijacks Instead of Faking LLM Continuation:**
   - *Adjustment:* Support hijacking running monitor turns (`--mon-N`), **but** render a monitor-specific recovery action set: **Hand off workspace + log tail to an Agent**, **Restart monitor command**, **Inspect Diff**, **Dismiss** — hiding LLM-only **Escalate** and **`#fork:` Continue** (unless restoring a co-hijacked parent agent turn in the same lane).
   - *Why justified:* Monitors execute deterministic shell commands, not LLM prompts (`_stop_target.py` / `escalation.rs` cannot escalate a bash command with no `#fork:` checkpoint). Pretending otherwise produces `invalid_model_target` or broken continuation prompts.

4. **Adjustment 4 — Replace Session/Turn Ambiguity with Lane-Atomic Hijacking:**
   - *Adjustment:* Define hijack ownership on an **active lane holding workspace #N** rather than assuming 1-to-1 correspondence between selected UI row and single active turn. When `--5` is finalizing and `--mon-3` is concurrently active on the same session/workspace, hijacking the collapsed session (or either overlapping member) atomically preempts the live lane processes, reconciles `monitor_handoff_claim_transferred`, and keeps one workspace custody record. For parallel multi-workspace clans (`is_clan_container`), prompt/disambiguate per member workspace.
   - *Why justified:* Directly prevents split-brain custody in the exact `tailnet-t.10` pattern shown in the screenshot, where `--5` and `--mon-3` both appear active under one collapsed row.

5. **Adjustment 5 — Replace Hard `finalizing` Refusal with Bounded Drain + Preemption Warning:**
   - *Adjustment:* Instead of refusing `"finalizing; try again in a moment"` forever when a finalizer/hook hangs, attempt a brief bounded drain (~1-2s); if finalizers haven't finished, preempt the finalizer subprocess group cleanly, cancel any staged unlaunched handoff, inspect repo index/lock state, and record `interrupted_phase = "finalizing"` in the hijack record so the recovery UI surfaces an explicit warning banner.
   - *Why justified:* Preserves fast graceful completion when finalizers actually finish in 500ms, while eliminating the failure mode where stuck hooks force the user back to `x`.

6. **Adjustment 6 — Keep `home_mode` and `named_proc` Excluded from Workspace Custody; Unify Eligibility in Rust:**
   - *Adjustment:* Keep `is_named_proc` excluded, and keep `is_home_mode` excluded from **workspace-holding** hijack (at most a future stateless "Stop & Edit/Relaunch Prompt" with no workspace pin or `$HOME` git diff). Delete TUI's divergent `agent_can_offer_hijack()` rules and make Rust `agent_hijack_eligibility()` (fed by one shared session/turn resolver and canonical schema) the single source of truth for `,k`, Kill modal `[h]`, and `sase agent hijack`.
   - *Why justified:* Locking `$HOME` or primary checkouts as exclusive workspaces breaks unrelated work; double-gating eligibility between Python and Rust guarantees recurring drift bugs like `AgentType.WORKFLOW`.

---

## 5. Recommended Solution & Implementation Roadmap

To fix both the immediate outage and long-term fragility, implement this in three clean phases:

### Phase P0: Fix the Broken Critical Path (Immediate Unblock)

1. **Make `"hijack"` Capability Unlosable Across All Agent Writers:**
   - Stop treating `"runner_capabilities"` as an ad-hoc bootstrap patch that `extract_directives_and_write_meta()` overwrites.
   - Add `"runner_capabilities"` (populated via a single helper `default_runner_capabilities() -> ["hijack"]`, unioned with any existing capabilities) directly inside `build_agent_meta()` (`run_agent_directive_metadata_build.py`), `preserved_agent_metadata()` (`run_agent_directive_metadata_preserved.py`), and `create_followup_artifacts()` (`run_agent_helpers_artifacts.py`).
2. **Unify Metadata Schema Between Writers (`axe`/`turns`) and Readers (`hijack`):**
   - Fix `src/sase/agent/hijack/_stop_target.py`:
     - `provider`: check `("llm_provider", "agent_llm_provider", "provider")`
     - `model`: check `("model", "agent_model")`
     - `effort`: check `("reasoning_effort", "agent_effort", "effort")`
     - `run_started_at`: parse both numeric epochs and ISO-8601 timestamps from `("booted_at", "run_started_at", "started_at")`
     - `is_gate_turn`: check `meta.get("turn_kind") == "gate"` alongside legacy `"gate_turn"` / `"is_gate_turn"`
     - `is_monitor_turn`: check `getattr(row, "is_monitor", False)` **and** `meta.get("turn_kind") == "monitor"` so headless CLI targets without a TUI row are classified accurately.
   - Fix `src/sase/agent/hijack/_stop_evidence.py`:
     - Reuse `sase._linked_repo_markers.opened_repo_records()` (the same source `recover_settle.py` already uses) and extract paths from `LinkedRepoResolution` dict entries in `agent_meta["linked_repos"]`, in addition to flat string lists.
3. **Fix TUI Eligibility, Collapsed Session Resolution & Enter-Key Mirroring:**
   - Remove the `AgentType.RUNNING`-only gate in `agent_can_offer_hijack()` (`_hijack_action.py`); evaluate hijack via a shared `resolve_hijack_candidate(agent)` -> Rust `agent_hijack_eligibility()` so TUI and CLI agree 100% and surface real Rust refusal explanations.
   - Delegate collapsed sequential session containers in `_start_hijack_agent()` and CLI `resolve_target` (following the pattern in `_kill_action_flow.py`) to locate active member turn(s).
   - Update `_mirror_root_from_child()` (`src/sase/ace/tui/models/_agent_status_apply.py`) to project `hijack_record` (and member `artifacts_dir` / identity context required by Enter-key resolution) onto collapsed container rows so pressing `⏎` on a `HIJACKED` collapsed session opens the recovery panel reliably.

### Phase P1: Expand Turn & State Coverage Safely

1. **Expand `ACTIVE_AGENT_STATUSES` in Rust (`eligibility.rs`) & Python:**
   - Permit `WORKING PLAN`, `WORKING TALE`, `PLAN COMMITTED`, `EPIC APPROVED`, `RESTARTING`, and `ANSWERED` alongside `RUNNING`, `STARTING`, and `RETRYING` (preserving plan/tale prompt context cleanly on continuation/restart).
2. **Preemptible `finalizing` / `handoff` + Lane Atomicity:**
   - Replace hard refusal on `"declaring" | "executing" | "finalizing"` in `eligibility.rs` with an interruptible state (bounded ~1.5s drain to let fast finalizers finish naturally, then process-group termination + staged-handoff cancellation + explicit `interrupted_during_finalizing` warning flag in recovery UI).
   - When resolving a session lane (or detecting `monitor_handoff_claim_transferred` / co-active turns sharing `workspace_num` like `--5` + `--mon-3`), collect and preempt **all** live processes on that workspace lane under one atomic custody transition before taking snapshot evidence.
3. **Monitor & Stuck-Gate Hijack Support:**
   - Allow `is_monitor_turn=True` in `eligibility.rs` (carrying `turn_kind="monitor"` into `HijackRecord`), wiring `_hijack_recovery_actions.py` / `recovery_preview` to present monitor-appropriate recovery choices (`Launch Agent With Diff + Log Tail`, `Restart Monitor`, `Dismiss`) while hiding LLM Escalate/`#fork:`.
   - Allow hijacking `gate` turns specifically when in `settling` / failed-handoff states; keep idle pending gates excluded with a clear `"Press Enter to review or give feedback"` notice.
4. **Pre-Run `WAITING`/`QUEUED` (`ws #0`) Control & Clan Disambiguation:**
   - Wire `ws #0` waiting rows to a non-custody **Edit Prompt / Cancel** prompt bar without locking a workspace.
   - On `is_clan_container`, show a compact member selector or hijack-all prompt matching `x` kill ergonomics.

### Phase P2: Dependability & Regression Prevention

1. **Single Typed Metadata & Wire Contract:** Define one shared metadata reader helper in `src/sase/axe/agent_meta.py` consumed by both `axe` writers and `agent/hijack` readers so field renames cannot silently produce `provider=None` or missing capabilities.
2. **Signal / Shutdown Race Verification:** Audit `_stop_orchestrator.py`, `run_agent_runner_signals.py`, `_run_agent_runner_shutdown_finalize.py`, `gate_turn/claims.py`, and `monitor/claims.py` to guarantee hijack intent + `stop_request` markers are durable **before** `SIGTERM` so shutdown handlers never release the workspace claim under hijack custody.
3. **End-to-End Integration Tests Without Synthetic Mocks:**
   - Add tests that write real `agent_meta.json` and `workflow_state.json` through `run_agent_runner_bootstrap.py` -> `extract_directives_and_write_meta()` -> `create_followup_artifacts()` (not hand-written JSON dicts).
   - Load TUI agent rows through `load_all_agents()` + `dedup_running_vs_workflow()` (including collapsed session rows with active `--N` + `--mon-M` overlap).
   - Assert end-to-end stop -> snapshot evidence (including linked/opened repos) -> recovery target validation (`provider/model` resolution) -> `Escalate` / `Continue` settlement across `RUNNING`, `WORKING PLAN`, `finalizing`, and active `Monitor` turns.
