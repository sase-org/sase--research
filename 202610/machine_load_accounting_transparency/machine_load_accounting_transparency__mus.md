# Machine load (`load: 3/8`): how it is calculated, why 6 running ≠ 6.0 load, and what UX to change

Researcher: mus (`__mus`). Independent swarm report. Scope: the Agents-row
`load: <occupied>/<limit>` gauge seen in `~/tmp/screenshots/20261026_172751.png`
as `load: 3/8` next to a `6 running` count, and what it would take to make that
state self-explanatory. All code refs are to the sase checkout unless noted.

## TL;DR

- `load: 3/8` is **not** "3 of 8 agent slots taken". It is **3.0 weighted
  capacity units occupied of an 8.0-unit budget** on the **local machine only
  (athena)**. Fractional and zero weights are normal, so a `6 running` lane
  count and a `3.0` load are consistent — very likely **not a calculation bug**.
- Live evidence from this machine right now reproduces the exact confusion:
  five RUNNING swarm researchers (myself included) each carry explicit weight
  **0.25**, a TESTING monitor carries **1.0**, and a WAITING CUTOVER monitor
  carries **0.0** (see §4). Five running lanes = 1.25 load units.
- The `/8` (not the configured default `/10`) comes from a live machine-wide
  override, `~/.sase/max_running_agents_override.json` (`{"limit": 8,
  "source": "ace"}`), verified on athena during this research.
- The real defect is **transparency, not arithmetic**: default-weight rows show
  no weight badge at all, the only composition breakdown is a hover-only
  tooltip capped at 12 holders, nothing marks the override, nothing says the
  gauge is local-machine scope, and the integer rendering (`3`, not `3.0`)
  invites exactly the count comparison the user made.
- Recommended UX (§6): render one decimal, add a keyboard-openable load
  breakdown (holders + exempt rows with reasons), mark override-sourced limits,
  label local scope, and legend the badge silence (no badge = default 1.0).

## 1. What the gauge is and where it renders

- The gauge is `AgentLoadIndicator`
  (`src/sase/ace/tui/widgets/agent_load_indicator.py`), mounted once per Agents
  status row (`AgentInfoRow` in
  `src/sase/ace/tui/widgets/launch_context_bar.py`), fed by
  `agent_load_indicator.update_load(limit, occupied, holders)` from
  `_update_agents_info_panel_impl`
  (`src/sase/ace/tui/actions/agents/_display_detail_info.py:238-252`).
- The value triple comes from `self._agent_runner_capacity`, a
  `RunnerCapacitySnapshot` dataclass
  (`src/sase/ace/tui/models/_agent_runner_slot_types.py:40-47`) with
  `effective_limit: float`, `occupied_capacity: float | None`,
  `slots_in_use: int` (integer lane count), `queued_count`, `queue`, and
  `holders`.
- The gauge renders **only `occupied_capacity / effective_limit`** (floats
  rounded to 2 decimals, integers when whole). `slots_in_use` is computed but
  **never displayed** — the first transparency gap.

## 2. How the numbers are computed (the contract)

- `refresh_runner_slot_context`
  (`src/sase/ace/tui/models/agent_runner_slots.py:65-116`) builds one capacity
  record per agent row (`capacity_record_from_agent` in
  `src/sase/ace/tui/models/_agent_runner_slot_capacity.py:35-112`) and sends
  them to the Rust engine `sase_core_rs.runner_capacity_snapshot`
  (`src/sase/core/runner_slots/_admission_snapshot.py:23-41`). There is **no
  Python fallback** (raises if the binding is missing) — the Rust projection
  is authoritative.
- Occupancy is **per agent session, not per row**: records group by
  `(project_name, agent_session)` (`runner_slot_agent_session_key`,
  `src/sase/core/runner_slots/_admission_predicates.py:152-159`). Serial
  session members (non-parallel children, monitors, follow-ups) **ride one
  session claim**; only parallel members wait for their own slot
  (`is_runner_slot_user_agent_record`, same file `:38-56`).
- A record occupies only if **all** hold (`is_runner_slot_occupying_record`,
  same file `:84-136`): `ace-run` workflow, no done marker, `appears_as_agent`,
  no `pending_question` yield, no pending gate turn, **started**
  (`run_started_at`, or for real monitor members just a recorded pid), and
  **live** (verified pid liveness — stale PIDs are re-probed and excluded,
  `_capacity_record_is_live` in `_agent_runner_slot_capacity.py:196-225`).
- Each claim contributes its **queue weight**, default `1.0`
  (`DEFAULT_QUEUE_WEIGHT`, `src/sase/core/runner_slots/_admission_types.py:13`;
  authored via `%queue(weight=…)` / `%q(w=…)`). Explicit `0.0` is valid and
  occupies nothing (`_queue_weight.py`, `docs/reference/runner-slots.md:12-17`).
- The snapshot is computed from the **local roster before fleet rows are
  projected in** (`_loading_compute.py:332-357`: "Slot annotation above stays
  local-only. The fleet rows are projected in before folding"). So the gauge
  is **local-machine (athena) capacity**; apollo's 23 agents draw on apollo's
  own budget and never move athena's number.
- The effective limit prefers a **temporary machine-wide override** first,
  merged config second (`get_max_running_agents`,
  `src/sase/config/core.py:466-477`; `docs/reference/runner-slots.md:19-24`).
  Configured default is 10 (`max_running_agents: 10`,
  `src/sase/default_config.yml:67`, `DEFAULT_MAX_RUNNING_AGENTS = 10`).

## 3. Reading the screenshot with that contract

`load: 3/8` = 3.0 weighted units occupied of an 8.0-unit athena budget (67.5%…
62.5% free). The `6 running` is a **status-lane count** for the active machine
tab, a different unit. The user's "expect 5" assumes (a) every running lane
weighs 1.0 and (b) the one waiting-monitor weighs 0. Live data refutes both
(§4). There is no evidence of a miscount: fractional weights alone
(5 × 0.25 = 1.25 for five lanes) bridge most of the 6 → 3 gap, with the
remainder attributable to any of: zero-weight monitors/gates, pending-question
or pending-gate rows holding no claim, session-shared claims, unstarted or
dead-PID rows, or clan-container/named-proc rows (`has_agent_meta=false`).

## 4. Live evidence (athena, 2026-10-26, `sase agent list -j`)

Project-scoped listing at research time (11 capacity-relevant rows):

| status | weight | explicit | kind | name |
|---|---|---|---|---|
| RUNNING ×4 | 1.0 | no | plain agents | `14p`, `bob-cli-ct.5`, `sase-1oh.5.1.2`, `sase-1oh.4.1.2` |
| RUNNING ×5 | 0.25 | yes | swarm researchers | `research.5e.{gem,mus,grk,cld,cdx}` |
| TESTING ×1 | 1.0 | yes | monitor (`role=monitor`) | `sase-1oe.3--mon-1` |
| WAITING CUTOVER ×1 | 0.0 | yes | monitor | `sase-1n6.10--mon` |

Observations that directly answer the user's questions:

1. **Fractional weights are routine.** This very swarm runs at 0.25 each —
    five RUNNING lanes contribute 1.25 units. Any operator doing lane-count
    math will be wrong whenever weights are fractional.
2. **"Running a waiting monitor" does not mean "counts 0".** Only monitors
    launched with `-w 0` (or the host-owned epic-launch monitor) record
    explicit zero weight (`src/sase/main/monitor/start.py:73-87`,
    `docs/reference/runner-slots.md:141-144`). A default monitor inherits the
    starter's weight and **does occupy** — the TESTING monitor above holds 1.0.
    The user's "subtract 1" step is therefore unreliable in both directions.
3. **Zero-weight occupants exist alongside full-weight ones** (the CUTOVER
    monitor at 0.0), and zero-weight rows are visually identical to full-weight
    rows unless they carry an explicit badge (see §5).
4. **`/8` is override-sourced.** `~/.sase/max_running_agents_override.json`
    on athena currently reads `{"limit": 8, "source": "ace"}`. Nothing in the
    TUI row says so.

## 5. Transparency gaps (the actual defects — all UX, none arithmetic)

1. **Badge silence for the common case.** `format_queue_weight_badge_value`
    (`_agent_runner_slot_types.py:69-83`) returns `None` for the default 1.0
    weight, and `_append_agent_queue_weight_badge`
    (`widgets/_queue_weight_badge.py:38-60`) additionally suppresses badges for
    clan containers, named procs, gates, plain monitors, and serial children.
    Net effect: the rows a user most needs to audit (the "which nodes have no
    weight" question) show **nothing**, and absence-of-badge ambiguously means
    "default 1.0", "zero-weight monitor", "gate", or "not individually
    counted". This is the single biggest source of the reported confusion.
2. **The only composition view is a hover tooltip.** `_holder_tooltip_block`
    (`agent_load_indicator.py:111-126`) lists at most 12 `Held by: label
    (kind): weight` lines. It is mouse-only (no keyboard path), truncated,
    shows holders but never the **exempt** rows (zero-weight, gated, yielded,
    unstarted, dead-PID, session-shared) with their reasons — i.e. exactly the
    rows whose exclusion the user is trying to verify.
3. **Two units, one row, no legend.** The left count (`6 running`) counts
    lanes/statuses; the right gauge (`3/8`) counts weight units. The row never
    states this. Integer rendering (`3` rather than `3.0`) actively suggests a
    count. (`_format_load_value` integerizes whole floats,
    `agent_load_indicator.py:26-43`.)
4. **Override invisibility.** Limit 8 vs default 10 is unexplained in the UI;
    the models-panel runner-limit card knows about overrides
    (`modals/models_panel_runner_limit.py:161`) but the status row does not.
5. **Scope invisibility.** One gauge, silently local-machine scope, in a UI
    with per-machine tabs (athena/apollo) and fleet-projected rosters. The
    capacity-before-fleet ordering (§2) is documented only in a code comment.
6. **Group-label vs status confusion.** The screenshot's Running group contains
    a `WAITING CUTOVER` row; status buckets map through the Rust
    `status_bucket_for_status` binding (`agent/status_buckets.py:221-241`), so
    "Running" the group ≠ "RUNNING" the status ≠ "occupying" the slot — three
    distinct predicates sharing one word.
7. **Silent holder drops (minor, worth a fix).** `_capacity_holders`
    (`agent_runner_slots.py:345-377`) silently skips claims whose artifact dirs
    resolve to no row or an unlabelled row. A dropped claim means the tooltip
    under-reports without any signal. Should log/count.
8. **Degraded states are cryptic.** `—/—` (limit unknown) and `—/N` (occupied
    unavailable) plus one-line tooltips (`agent_load_indicator.py:84-108`); no
    row-level hint about *why* (loader not finished vs snapshot failure).

## 6. Recommended UX (ordered by value/effort)

1. **Render one decimal when fractional (`load: 3.0/8`).** One-line change in
    `_format_load_value` call-site for the gauge (keep integer when the value
    is whole AND all claims are integral? simpler: always show `.0`). Breaks
    the false count-comparison at a glance. Keep bar color semantics.
2. **Keyboard-openable Load breakdown (`?` or click on gauge).** A small panel
    with three sections, all already available in `RunnerCapacitySnapshot` +
    per-row fields: (a) **Holding** — every holder with weight (uncapped, or
    capped with exact count); (b) **Running but not holding** — each
    non-occupying RUNNING-lane row with its machine-checkable reason
    (`w0 monitor`, `gate pending`, `question yielded`, `not started`,
    `stale/dead pid`, `shares session claim with X`, `container/proc row`,
    `non-ace-run`); (c) **Budget** — `effective 8 (override, source: ace)` vs
    `configured 10`. This single view resolves the user's entire report.
3. **Mark override-sourced limits inline.** E.g. `load: 3.0/8*` with tooltip
    `* temporary override (ace); configured 10`, reusing the
    `models_panel_runner_limit` snapshot logic. Fails safe: no marker when no
    override.
4. **Legend the badge silence.** Options, cheapest first: (a) document in
    `docs/reference/runner-slots.md` + status-row help that "no `wN` badge =
    default 1.0"; (b) render default weight as a dim `w1` behind a
    config/toggle (default off to avoid row-width churn); (c) in the breakdown
    panel (§6.2) show every weight explicitly. At minimum do (a) with the
    breakdown panel.
5. **Label scope in the tooltip.** First tooltip line:
    `Runner load on <local-machine> (local agents only; <apollo> tabs use
    <apollo>'s budget)`. The local name and fleet tab names are already in the
    tab strip model (`widgets/agent_tab_strip.py`,
    `_agent_tab_strip_model.py:137`).
6. **Show lanes alongside units in the breakdown, not the gauge.**
    `slots_in_use` (integer lanes) is already computed — surface it in the
    breakdown header (`3.0 units across 6 lanes / 8.0 budget`) so both counting
    instincts are served without cluttering the row.
7. **Disambiguate "Running".** In grouped views, footnote or tooltip the group
    header when a group contains non-canonical statuses (e.g. the CUTOVER row),
    or suffix the count (`6 running` → tooltip listing statuses). Do not rename
    buckets — too invasive.
8. **Count (don't silently drop) unresolvable holders** (§5.7): emit
    `… +N unmapped` in the tooltip/panel and a debug log with artifact dirs.
9. **Degraded-state reasons.** Distinguish `—/— (capacity not loaded yet)` from
    `(snapshot failed — see logs)`; the widget already distinguishes
    `limit <= 0` from `occupied is None` internally.

## 7. Suggested acceptance checks for the fix

- With the live swarm state (§4), the breakdown panel must show five 0.25
  holders by name, the 1.0 TESTING monitor, and the 0.0 CUTOVER monitor under
  "running but not holding", summing holders to the gauge numerator.
- Setting/clearing `~/.sase/max_running_agents_override.json` flips the `*`
  marker and tooltip source line within one refresh tick.
- `just check` (repo's agent verification recipe) green; runner-slot unit tests
  covering `_format_load_value` decimal rendering and `_capacity_holders`
  unmapped counting.

## 8. Files of record (for implementers)

- Gauge render/tooltip: `src/sase/ace/tui/widgets/agent_load_indicator.py`
  (esp. `:26-126`); row wiring:
  `src/sase/ace/tui/actions/agents/_display_detail_info.py:238-252`;
  layout: `src/sase/ace/tui/widgets/launch_context_bar.py:303-328`.
- Snapshot/types: `src/sase/ace/tui/models/agent_runner_slots.py`,
  `src/sase/ace/tui/models/_agent_runner_slot_types.py`,
  `src/sase/ace/tui/models/_agent_runner_slot_capacity.py`.
- Engine contract: `src/sase/core/runner_slots/` (`_admission_predicates.py`
  occupancy/admission split, `_admission_snapshot.py` Rust call,
  `_queue_weight.py` zero-weight rules); defaults/override:
  `src/sase/config/core.py:466-477`, `src/sase/default_config.yml:60-67`.
- User docs: `docs/reference/runner-slots.md` (weighted-capacity semantics,
  monitor/gate/procs rules — the best existing statement of the contract;
  the UX gap is that the TUI surfaces almost none of it).
- Screenshot: `/home/bryan/tmp/screenshots/20261026_172751.png`
  (`load: 3/8`, `6 running`, `⌂ athena 174 · ⌨ apollo 23`).
