# Agent Hijack Resilience: Why Hijacks Refuse Live Turns, and How to Fix It

_Research report · researcher `mus` · 2026-11-15 · in response to the 16:41 apollo
screenshot (`~/tmp/screenshots/20261115_164112.png`) showing
"Selected agent is not eligible for hijacking" on the RUNNING turn `tailnet-t.10`._

## Bottom line

**The feature is a good idea and the request is justified — but "hijack" is
currently broken at a layer below the one the screenshot shows.** I found one
verified P0 bug that makes the CLI/orchestrator hijack path refuse essentially
*every* production agent, plus a second UX-level defect that explains the exact
toast in the screenshot. Fix those two before widening coverage; then widen
selectively, not universally. Blanket coverage ("hijack every turn type in every
state") would be actively harmful for gate turns, monitor turns, and remote rows,
and unnecessary for several other exclusions. My recommendation is a 4-phase plan
in [Recommended solution](#recommended-solution).

Verified headline findings:

1. **(P0, verified live on apollo) The runner capability stamp never survives to
   disk, so the stop orchestrator refuses all real agents with
   `missing_capability`.** `sase agent hijack <live-RUNNING-turn>` cannot succeed
   today no matter what the TUI says. The refusal message ("launched before
   hijack support; use x") misdiagnoses a turn launched minutes ago.
2. **(Verified in code) The TUI toast in the screenshot names no reason.**
   `_start_hijack_agent` shows a generic "not eligible" toast that hides which
   of ~9 predicate clauses fired, while the authoritative decision (with a
   machine-readable `code`) exists one layer down and is never consulted.
3. **(Verified in code) Two independent eligibility policies can disagree.**
   The TUI's `agent_can_offer_hijack` and the Rust `agent_hijack_eligibility`
   (via `_check_eligibility`) check overlapping but different conditions, so the
   TUI can offer what the orchestrator refuses and refuse what it would allow.

## Sources and method

Live state on apollo (I am on apollo, where the screenshot was taken):
` sase agent list -j`, `agent_meta.json` for the live `tailnet-t.10` artifacts
dir, read-only `resolve_target` probes via the project venv, and `ps` proof that
pid 2295354 is a live local process. Code read in full: the Rust eligibility
(`crates/sase_core/src/agent_hijack/eligibility.rs` in `sase-core` at
`2159438daaad`), `src/sase/agent/hijack/_stop_target.py`,
`_stop_orchestrator.py`, `_stop_models.py`, `core.py`, `ledger.py`,
`recover_subject.py`, `src/sase/ace/tui/actions/agents/_hijack_action.py`,
`_kill_action_flow.py`, `_display_detail_footer.py`, `agent_durable.py`,
`src/sase/ace/tui/models/agent_hijack_presentation.py`, `agent_status.py`,
`agent_types.py`, `_loaders/_running_loaders.py`, `run_agent_runner_bootstrap.py`,
`run_agent_directives_extract.py`, `run_agent_directive_metadata_build.py`,
`run_agent_directive_metadata_preserved.py`, `run_agent_markers.py`,
`agent_meta.py`, plus the two prior research notes
(`sase/repos/research/202611/agent_hijack_user_guide/agent_hijack_user_guide.md`
and `.../agent_hijack_held_workspace_recovery/agent_hijack_held_workspace_recovery.md`,
unsuffixed base documents only) and the glossary strands `gate turn` and
`sase turn` (`sase memory read`). The installed venv wheel in this workspace is
stale (`sase_core_rs` lacks `agent_hijack_eligibility`), so the Rust decision was
evaluated by hand-walking the authoritative Rust source against live resolved
facts rather than by calling the binding — same function, no writes, no signals.

I did not open any peer swarm report (`__cdx`/`__cld`/`__grk`/`__gem`); the
suffixed files under `agent_hijack_held_workspace_recovery/` were left alone.

## What the screenshot actually shows

- Bottom `@epic` panel: row 6 selected (white border), `tailnet (RUNNING)` with
  `tailnet-t.10`, elapsed `2m49s / 1h42m`. A separate `tailnet-t.land` row sits
  in `WAITING`.
- Right `SESSION` detail: `tailnet-t.10 · 12 turns · PLAN`, models `gpt-6-luna`,
  raw prompt containing `%w(tailnet-t.3,tailnet-t.9, for_epic=false)` (a wait
  dependency) and `%model:@medium`, one `QUESTIONS` round `gate ANSWERED human
  via TUI`, and `sh starting`.
- Top-right toast: "Selected agent is not eligible for hijacking" — this exact
  string is emitted only by
  `src/sase/ace/tui/actions/agents/_hijack_action.py:62-67`, i.e. the cheap TUI
  predicate `agent_can_offer_hijack` returned `False`. (The remote-fleet branch
  just above it copies a command instead of toasting, so the selected row was
  *not* classified remote-fleet.)

Live follow-up (same machine, ~10 min later): `sase agent list -j` still shows
the session alive as `tailnet-t.10--6`, `RUNNING`, `workspace_num 10`, pid
2295354 (`ps` confirms a live local `python3`), `agent_session_role "root"`,
`gate_id null`, `monitor_id null`, `fleet_origin_alias null`. The pre-screenshot
attempt is gone (superseded by retry `--6`), so the screenshot's exact row state
cannot be re-observed — the ranked hypotheses in the next section account for
that. Note the glossary rules out one tempting reading: the `QUESTIONS … gate
ANSWERED` panel is a *question round inside an agent turn*, not a *gate turn*
(session-attached `<session>--gate` member owning a durable decision), so
`is_gate` was almost certainly `False` for this row.

## Finding 1 (P0, verified): every production agent fails orchestrator eligibility

Even when the TUI predicate passes, `sase agent hijack` (and the TUI's own
`persist-hijack` durable proc, which funnels into the same
`stop_agent_for_hijack` in
`src/sase/agent/hijack/_stop_orchestrator.py:58`) refuses with `missing_capability`
/ "launched before hijack support; use x". Live proof for the screenshot's own
session:

- `resolve_target('tailnet-t.10--6')` (read-only) returns `status RUNNING`,
  `lifecycle_phase "planned"`, `pid == claim_pid == 2295354`, `workspace_num 10`,
  `is_monitor_turn/is_gate_turn/is_home False`, `done_outcome None`,
  **`capabilities []`**.
- Hand-walking `agent_hijack_eligibility`
  (`crates/sase_core/src/agent_hijack/eligibility.rs`) over these facts: phase
  `"planned"` is not in `{declaring, executing, finalizing}`; not monitor, gate,
  named-proc, home, remote, clan-container, or bulk; local LLM agent; then
  `has_hijack_capability == false` fires → refusal `(missing_capability,
  "launched before hijack support; use x")`. No later check is reached.

Root cause is a write-then-wipe ordering bug in the runner, not an old binary:

1. `_write_bootstrap_agent_meta`
   (`src/sase/axe/run_agent_runner_bootstrap.py:75-160`) appends `"hijack"` to
   `runner_capabilities` (added 2026-11-03 in `01a28287c8`) and writes
   `agent_meta.json`.
2. Later in the same `bootstrap_agent_run`,
   `extract_directives_and_write_meta`
   (`src/sase/axe/run_agent_directives_extract.py:47`) builds a **fresh** dict in
   `build_agent_meta` (`run_agent_directive_metadata_build.py:27`) and publishes
   it via `write_agent_meta_atomic` (`axe/agent_meta.py:125`), documented as "a
   complete sibling-file replacement" — no merge.
3. The only carry-over is the allow-list in `preserved_agent_metadata`
   (`run_agent_directive_metadata_preserved.py:31`), which keeps ~20 named keys
   (`bead_id`, `model*`, `prompt_origin`, `code_identity`, lifecycle
   breadcrumbs, wait records…) but **not** `runner_capabilities`.

Net effect: the stamp survives only between the two writes (milliseconds). I
scanned every live `agent_meta.json` on this machine across both projects
(~30 files, all today's launches): **all** have `runner_capabilities: null`.
The unit tests mask this — `tests/test_agent_hijack_stop.py:40-46` and
`tests/fakey/test_agent_hijack_e2e.py:206` hand-inject
`"runner_capabilities": ["hijack"]` instead of launching through the real
runner. The fix is a one-line-class change (add the key to the preserved
allow-list, or re-stamp after directive extraction), plus a test that launches
through the real bootstrap and asserts the on-disk meta keeps the capability.

## Finding 2: the TUI toast cannot diagnose itself

`agent_can_offer_hijack`
(`src/sase/ace/tui/actions/agents/_hijack_action.py:12-36`) refuses when *any*
of these hold: `agent is None`; `agent_type is not RUNNING`; `status` not in
`{RUNNING, STARTING, RETRYING}`; `workspace_num` missing/`<= 0` or `pid`
missing; `is_monitor`, `is_gate`, `is_named_proc`, `is_clan_container`,
`fleet_origin_alias`, or `imported_source_owner` set. The toast names none of
them, and the kill dialog (`_kill_action_flow.py:158-171`) likewise only hides
the `h` option. Meanwhile `_check_eligibility`
(`_stop_orchestrator.py:298-318`) asks the Rust core a *different* question
(phase, capability, home, remote, bulk, status text, pid) — it never sees
`imported_source_owner`, `fleet_origin_alias`, `agent_type`, or clan-container,
and the TUI never sees `lifecycle_phase` or `runner_capabilities`. Concretely:

- A row the TUI refuses for `imported_source_owner` or `WORKFLOW` agent_type
  (workflow-claim rows get `AgentType.WORKFLOW` in
  `_loaders/_running_loaders.py:336-349`) would sail through the orchestrator's
  facts (`is_named_proc False`, status RUNNING, …).
- A row the TUI accepts (plain RUNNING + ws + pid — i.e. today's tailnet-t.10)
  is refused one layer down by `missing_capability`, surfacing only later as a
  durable-proc completion message after an optimistic `HIJACKING…` overlay.

Ranked hypotheses for the screenshot toast, given the live facts rule out
monitor/gate/remote/pid-less as *current* properties:

1. **Container/wave row selected.** The highlighted `@epic` row renders
   aggregate counts and may be the clan wave/container projection
   (`is_clan_container`), which the predicate excludes. The SESSION detail can
   lag or pin a different row than the list cursor.
2. **Transient STARTING state.** Claim-built rows start as `STARTING` before
   the runner fills in pid/workspace (`_running_loaders.py:load_agents_from_
   resolved_running_claims`); a `,k` in that window toasts. The screenshot's
   `sh starting` and `2m49s` age are consistent with early life.
3. **WORKFLOW-typed claim.** If the tailnet wave claims carry
   `workflow("…")`, the row is `AgentType.WORKFLOW` and permanently ineligible
   in the TUI although it is a real LLM turn with a real pid.
4. **Orchestrator refusal misread as TUI refusal** — unlikely (different
   strings), listed only to exclude it: the screenshot string is byte-identical
   to the TUI toast.

Any of 1–3 resolves to the same UX defect: the user cannot tell a "select the
leaf row" problem from a "this turn type is unsupported" problem from a
"transient, retry in a second" problem.

## Coverage matrix: what can be hijacked today

Authoritative policy = Rust `agent_hijack_eligibility` + `resolve_target` +
TUI predicate. "No" means refused with nothing changed (exit 2 / toast).

| Turn / state | Hijackable today? | Where it refuses |
|---|---|---|
| Plain agent turn, RUNNING, numbered ws, live pid | No (bug) | `missing_capability` (Finding 1) |
| Same, once Finding 1 is fixed | Yes | — |
| STARTING / RETRYING with ws + pid | Yes (if caps fixed) | TUI allows trio; Rust allows trio |
| STARTING before claim/pid exists | No (transient) | TUI predicate; retries seconds later pass |
| WAITING on `%wait`/slots/time (`tailnet-t.land`, `research.4u.linker`) | No | `ineligible_status` (+ `workspace_num 0` → `unnumbered_workspace`) |
| QUEUED on runner slots | No | same as WAITING |
| Gate turn (`<session>--gate`) | No | `gate_turn` (Rust) + `is_gate` (TUI) |
| Monitor turn (`--mon`) | No | `monitor_turn` + `is_monitor` |
| Named proc (`sh`, oneshots, `AgentType.NAMED_PROC`) | No | `named_proc` + TUI |
| Home-mode (`ws #0`, e.g. WAITING home rows) | No | `home_mode`; TUI needs `ws > 0` |
| Clan container / wave aggregate row | No | `clan_container` + TUI |
| Workflow-claim row (`AgentType.WORKFLOW`) | No | TUI `agent_type` check only |
| Remote-fleet row viewed from another host | No (by design) | TUI copies `sase agent hijack NAME` for the owning host |
| Imported (agents-sync) row | No | TUI `imported_source_owner` only |
| Bulk-marked row | No | `bulk_mark` |
| Lifecycle `declaring`/`executing`/`finalizing` | No (transient) | `finalizing` ("try again in a moment") |
| `done.json` already written (any outcome incl. `monitored`) | No | `already_completed` (kept, correct) |
| HIJACKED row (re-hijack) | No | status trio excludes it (correct; recovery panel owns it) |
| Held-expired row | Recover-only (`r`/`e`/`d`) | recovery policy (correct) |
| `stop_failed` survivor row | No clean retry | stays RUNNING + red badge; re-`,k` re-runs full stop |

Cells marked "(bug)" or "(transient)" are the resilience gaps; the rest are
policy choices, several of which should stand (see critique).

## Stop-protocol resilience gaps (beyond the capability wipe)

The stop order itself (`src/sase/agent/hijack/stop.py:1-22`, executed by
`_stop_orchestrator.py:58-283`) is careful — intent + ledger record before any
signal, claim pin under lock, `finished_first` race handling, verified death,
best-effort evidence — but several edges are sharp:

1. **No retry path for `stop_failed`.** If `terminate_tree` leaves survivors
   (`_stop_claim.py:terminate_tree`), the record goes `stop_failed`, intent is
   removed, the pin restored, and the row stays RUNNING with a badge. The only
   recourse is another full `,k`, which re-runs the whole protocol including a
   fresh ledger record. Survivors that resist SIGKILL (uninterruptible sleep,
   a `sudo`-elevated child — cf. `sase/sudo/runner.py` detached-execution
   capability probing) will fail identically each time with no escalation
   (e.g. "still failing after N attempts → offer kill-with-release").
2. **The `finalizing` refusal is a blind spot, not a wait.** `declaring` /
   `executing` / `finalizing` refuse with "try again in a moment", but nothing
   retries or notifies when the phase clears — the user must poll `,k`. The TUI
   does not even know the phase, so it shows `HIJACKING…` optimistically and
   then reports failure.
3. **Claim-mismatch aborts are silent about cause.** `pin_claim` failure
   returns `claim_mismatch` with "workspace claim changed while preparing".
   Against clan waves and retries (this session is already at `--6`), claim
   churn is normal, and the user gets no "who holds it now" detail.
4. **Evidence is best-effort and invisible on failure.** `collect_evidence` /
   `capture_snapshots` exceptions only warn (`_stop_orchestrator.py:236-256`);
   a held record can silently lack the diff snapshot the recovery panel
   promises. There is no `snapshot_ok` flag for the panel to branch on.
5. **`resolve_target` identity is name-based.** `_find_live_row` matches on
   `row.name == name and artifacts_dir`; with retries (`tailnet-t.10` vs
   `tailnet-t.10--6`) and wave members, a stale name can resolve to the DONE
   predecessor (as my own probe did for bare `tailnet-t.10` → `done_outcome
   monitored`) and refuse `already_completed` while the live retry runs under a
   suffixed name the user never typed.

## Recovery-side resilience gaps

Recovery (held → `resolving` → settled) is the most state-heavy part and the
least observable. From `recover.py`, `_recover_reconcile_observation.py`,
`_recovery_admission_observe.py`, `recovery_successor*.py`, and the user guide:

1. **Admission limbo.** Keep-work actions go through a durable admission queue
   (`submitted → reserved → waiting → checking → eligible → dispatching →
   launched`). `resume_recovery_admission` exists for resolver interruption,
   but a successor that never dispatches leaves the row in `RECOVERING…` with
   the workspace still pinned — the exact "stuck, holding a workspace" shape
   hijack was built to avoid creating. There is no watchdog that reconciles a
   `resolving` record back to `held` after a timeout with the evidence to show
   for it.
2. **Expiry narrows options silently.** After 14 days the record goes `expired`
   and only Restart/Edit/Dismiss remain; the snapshot that justifies that
   narrowing is taken by the sweeper, and a sweeper failure mode (cf. prior
   `stale_running_sweep` work) would strand the row.
3. **Remote rows have no recovery path at all.** The TUI copies
   `sase agent hijack NAME` for the owning host, but nothing tracks whether the
   operator ran it, and the local mirror row never reflects the remote ledger
   state. For the tailnet epic — whose whole point is multi-host acceptance —
   the host where you notice the stall is routinely not the host running it.
4. **WAITING/QUEUED turns can neither be hijacked nor cleanly abandoned.**
   `tailnet-t.land` (WAITING on ten siblings) and the three WAITING research
   linkers hold no process to stop, but the user's intent — "stop waiting and
   keep/release cleanly" — has no hijack-shaped answer; `x` kill is the only
   lever, and it releases. A wait-cancel with snapshot would subsume this
   without touching the stop protocol.

## Critique: is "hijack everything" a good idea?

**Building hijack was the right call, and fixing it (not reverting it) is
right.** Every other stop path couples "stop the process" to "give up the
work", which is exactly wrong for a stalled 90-minute run. The ledger + pin +
verified-death + snapshot-before-release design is sound, and the
never-downgrade escalation is the correct default. **But "as many turn types in
as many states as possible" as a blanket requirement is wrong**, and I would
amend it to "every *agent turn* in every *live* state, with reason-carrying
refusals everywhere else". Specifically:

- **Keep refusing gate turns and monitor turns — deliberately.** A gate turn
  *is* the human's move; hijacking it means killing the prompt that is waiting
  for the human, which destroys the decision context. A monitor turn is a
  detached supervisor for a long command; SIGKILLing it behind the supervisor
  creates the orphan the supervisor exists to prevent. What these need is not
  hijack but first-class stuck handling of their own (gate timeout +
  re-prompt; monitor command kill with log preservation). Conflating them into
  hijack would trade one stuck shape for another.
- **Keep refusing remote rows locally — but close the loop.** Cross-host
  signalling from apollo to mac is a distributed-systems commitment (identity,
  auth, exactly-once) that does not belong in a stop protocol. The copy-command
  affordance is the right shape; what is missing is *tracking*: record the
  referral in the ledger and reflect the remote outcome back on the mirror row.
- **Do widen: workflow-typed LLM rows, STARTING/RETRYING transients, and
  WAITING/QUEUED waiters.** A `WORKFLOW`-typed row that is really an LLM turn
  with a pid is an artifact of claim typing, not a safety boundary — classify
  by `is_llm_agent`, not by TUI enum. Transients should debounce-and-retry
  inside the submission, not toast. Waiters need a wait-cancel-with-snapshot
  path (they hold no process; there is nothing to "stop", only a queue entry
  to release and state to keep).
- **Do not widen: home-mode `#0`, named procs, bulk marks, HIJACKED rows.**
  Home rows have no numbered workspace to hold (there is nothing to keep);
  named procs/oneshots are process management, not agent sessions, and already
  have `x`/retry; bulk marks are a selection artifact. Each has a cheaper
  correct tool.
- **Fix the message before the matrix.** Every refusal already computes a
  `(code, message)` pair in Rust or a specific clause in the TUI; the work is
  plumbing, not policy: surface `code` + next action ("select the leaf row",
  "retrying automatically", "run on mac: …", "use x — nothing to hold").

### Requirement adjustments I am calling out

1. Replace "as many types/states as possible" with the matrix above: widen to
   workflow-typed LLM turns, transient STARTING, and wait-cancel for
   WAITING/QUEUED; explicitly keep gate/monitor/remote-local/home/proc/bulk
   out, each with its named alternative.
2. Add: every refusal, TUI or CLI, must carry its `code` and a next action.
   The generic toast is a bug, not a limitation.
3. Add: single source of truth for eligibility. The TUI predicate must be
   generated from (or delegate to) the same facts the orchestrator decides on;
   two hand-synced policies have already diverged twice (capability, phase).
4. Add: a regression test that launches through the real runner bootstrap and
   asserts `runner_capabilities` survives to disk. The current tests inject the
   capability and therefore certify a path production never takes.
5. Add: `stop_failed` gets a bounded retry + downgrade offer, and `resolving`
   gets a reconcile watchdog, before any coverage widening. Widening the mouth
   of a funnel that jams is how you get more jams.

## Recommended solution

**Phase 0 — unbreak the happy path (P0, small, no design risk).**
(a) Add `runner_capabilities` to `preserved_agent_metadata` (or re-stamp in
`extract_directives_and_write_meta` after `build_agent_meta`); backfill is
unnecessary since only live rows matter. (b) Add the real-bootstrap regression
test. (c) Fix the refusal text: `missing_capability` should distinguish
"capability absent on a current runner" (bug/edge — say so) from a genuinely
old runner. Expected outcome: `sase agent hijack tailnet-t.10--6` reaches the
stop protocol instead of refusing.

**Phase 1 — one policy, speaking plainly (small-medium).** Collapse the TUI
predicate into a call to the same facts/orchestrator precheck (read-only
`resolve_target` + `agent_hijack_eligibility`, which is already side-effect
free), keep it cheap by caching per refresh, and render `code` + next action
in the toast, the kill dialog (`h` disabled *with reason* instead of hidden),
and a footer hint. Container rows get "select a leaf member (Enter to
expand)"; transient rows get auto-retry of the submission for ~10 s instead of
a toast; remote rows keep the copy-command but also record a ledger referral.

**Phase 2 — widen where it is safe (medium).** (a) Classify workflow-claim LLM
rows as hijackable (predicate on `is_llm_agent`, not `AgentType`). (b) Add
wait-cancel-with-snapshot for WAITING/QUEUED rows (no stop protocol involved;
reuse ledger + snapshot + release). (c) Bounded retry + downgrade offer for
`stop_failed`; reconcile watchdog for `resolving`. (d) Cross-host referral
tracking for remote rows.

**Phase 3 — explicitly not built.** Gate/monitor hijack, home-mode holds,
bulk hijack, proc hijack. Each gets a one-line documented alternative (gate
timeout/re-prompt, monitor command kill, `x`, per-row `,k`) instead of protocol
support.

## Verification appendix (what I actually ran)

- `sase agent list -j` on apollo: `tailnet-t.10--6` RUNNING ws 10 pid 2295354,
  role `root`, no gate/monitor/fleet markers; `tailnet-t.land` WAITING ws 0;
  three `research.4u.*` WAITING linkers (peers' rows; not inspected further).
- `agent_meta.json` (`.../ace-run/202611/15/20261115164340/`): `gate_turn null`,
  `runner_capabilities null`, `finalizer_status.phase "planned"`,
  `model_alias "medium"`. ~30 live metas across two projects: all
  `runner_capabilities null`.
- Read-only `resolve_target('tailnet-t.10--6')` → RUNNING / planned /
  pid=claim_pid=2295354 / ws 10 / caps `[]` / `done_outcome None`;
  bare `tailnet-t.10` resolves to a DONE predecessor (`monitored`) — the
  name-suffix hazard noted under stop-protocol gap 5.
- `ps -p 2295354` → live `python3`: the turn is genuinely running while
  unrunnable-by-hijack.
- Rust `eligibility.rs` hand-evaluated over those facts → `missing_capability`.
  (Direct binding call impossible: this workspace's venv wheel predates the
  hijack bindings — itself worth a `just install-venv`, but orthogonal.)
- `git log -S runner_capabilities` → stamp introduced in `01a28287c8`
  (2026-11-03); the wiping write (`write_agent_meta_atomic`, "complete
  sibling-file replacement") predates it — the stamp was dead on arrival.

*End of report.*
