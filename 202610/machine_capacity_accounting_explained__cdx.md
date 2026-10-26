**Machine capacity accounting: explain every contribution, and repair the monitor undercount**

Independent research by `cdx`, 2026-10-26. Investigation completed against the supplied screenshot and local source and execution metadata. No other report, findings, or transcript from this research swarm was consulted. No production code or runtime metadata was changed.

**The screenshot probably shows a real TUI undercount.** The strongest explanation is three unit-weight provider executions, two unit-weight testing monitors, and one explicitly zero-weight waiting monitor: **six active agents, five capacity units**. I reproduced a defect that drops a live testing monitor from the TUI capacity calculation while the runtime capacity calculation counts it. There are also independently reproducible defects involving claim ownership and invalid-weight diagnostics. The appropriate response is to fix the data projection and make capacity explainable, while preserving the distinction between an active agent count and weighted capacity.

The most useful UX change is a persistent, machine-labeled capacity indicator that opens a keyboard-accessible breakdown. That breakdown must explain both contributions and non-contributions, including intentional zero, shared claims, waiting work, and unknown accounting. A tooltip listing only recognized holders cannot explain a missing holder.

**What the screenshot and subsequent metadata establish.** The screenshot is `/home/bryan/tmp/screenshots/20261026_172751.png`, showing athena selected, `6 running`, and `load: 3/8`. Its TUI version is `v0.18.1+14.gdd12f981a`. The running groups show two active members under `bob-cli-ct` and one each under `sase-1oh.5.1`, `sase-1oh.4.1`, `sase-1oe`, and `sase-1n6`.

The following is a reconstruction, not a saved atomic scheduler snapshot from 17:27:51 EDT:

| Active execution corresponding to the screenshot | Evidence and expected contribution |
| --- | --- |
| `bob-cli-ct.5` | Later listing reports RUNNING, weight 1; started 17:20:03 EDT. Expected 1. |
| `sase-1oh.5.1.2` | Later listing reports RUNNING, weight 1; started 17:13:55 EDT. Expected 1. |
| `sase-1oh.4.1.2` | Later listing reports RUNNING, weight 1; started 15:45:06 EDT. Expected 1. |
| `bob-cli-ct.3--mon` | TESTING monitor, weight 1, started 17:25:32 EDT and stopped 17:29:57 EDT. Its recorded interval brackets the screenshot. Expected 1. |
| `sase-1oe.3--mon-1` | TESTING monitor, weight 1, started 17:21:02 EDT; its supervisor was still live during inspection. Expected 1. |
| `sase-1n6.10--mon` | WAITING CUTOVER monitor, explicitly authored weight 0; supervisor still live during inspection. Expected 0. |
| **Reconstructed total** | **6 active executions; 1 + 1 + 1 + 1 + 1 + 0 = 5 capacity units.** |

Both testing monitors have their supervisor PID in `agent_meta.json` and a null PID in `workflow_state.json`. The TUI loader's choice of the latter explains why the three provider agents contribute while the two testing monitors disappear from the total. The zero-weight waiting monitor also disappears as a holder, concealing the fact that its zero was intentional.

Confidence is high in the monitor defect and high in this explanation of the arithmetic. Exact historical attribution remains conditional because the screenshot does not include the capacity input records, claim identities, or observation timestamp. I did not reconstruct a complete historical scan or all process liveness at that instant. This is evidence of an incorrect display projection; it is **not evidence that the runtime scheduler admitted work using the same incorrect number**.

**The current accounting contract.** The load numerator is a scheduling reservation measure, not operating-system load average, CPU utilization, RAM usage, a provider quota, or a count of visible rows. The Rust `runner_capacity` domain computes it from execution records. [S1–S3]

For valid input, its essential calculation is:

```text
eligible occupancy records
  -> group by canonical capacity-claim owner
  -> take the maximum live record weight within each claim
  -> sum those claim weights
```

The maximum within a claim avoids charging twice for overlapping records of the same serial execution lineage. Independent parallel claims are charged separately. A default weight is 1. An absent weight therefore does not mean zero. An explicit numeric zero is valid; an implicit zero or invalid weight is a different condition. Fractional and larger weights are supported.

A record normally qualifies when it represents an `ace-run` agent, has agent metadata, appears as an agent, has no done marker, is live, is not yielding for a pending question or pending gate, and has started. A real monitor uses the presence of its PID as its start qualification. A monitor normally inherits its capacity weight; being a monitor or displaying a waiting-like status does not automatically exempt it. Host epic-launch supervision can explicitly override the monitor's weight to zero. [S1, S4]

The denominator comes from the effective configured runner limit, including a temporary override. A candidate can have an authored admission budget, and eligibility also depends on holds, queue order, input validity, and the candidate's own weight. Thus “3 free” is arithmetic headroom, not a promise that a particular queued agent can start. Authored per-launch budgets can exceed the displayed default limit, so the denominator should not be described as an inviolable machine ceiling. [S3, S8]

The running count has separate semantics. It counts deduplicated agent nodes using their status buckets, including session/container projections. It is affected by the selected presentation scope. The capacity calculation is deliberately performed over local capacity rows before fleet projection and before ordinary display folding/hiding. The same status label can therefore coexist with distinct contribution states. Aggregating these two numbers into one counter would remove useful information. [S5]

**Finding 1: a live monitor's PID is lost before TUI accounting — confirmed, high priority.**

The runtime adapter's `_record_pid()` chooses `agent_meta.pid` first and falls back to the running marker. In contrast, `load_workflow_states_from_snapshot()` sets `pid = wf_state.pid`, and `load_workflow_agents_from_snapshot()` passes that PID to `Agent`. The metadata enrichment reads monitor state, weight, and run-start time but does not restore `agent_meta.pid`. `_capacity_record_is_live()` then sees no PID and returns false; Rust excludes the monitor. [S2, S6]

Read-only probes against the two still-live screenshot monitors produced:

```text
name                       meta PID   workflow PID   weight
sase-1oe.3--mon-1           283336     null           1
sase-1n6.10--mon            4026430    null           0

Runtime capacity from those exact records:               1.0
TUI capacity after normal loading and normalization:      0.0
TUI capacity after supplying monitor meta PID in memory:  1.0
Holders after supplying PID: testing monitor 1; cutover monitor 0
```

The final probe used `_load_agents_from_artifact_snapshot_sources()`, `normalize_loaded_agents(..., keep_orphaned_followups=True)`, and `refresh_runner_slot_context()`. It was not merely a hand-constructed `Agent` fixture. The in-memory intervention changed no files. The earlier, simpler workflow-loader probe gave the same mismatch.

The immediate repair is to preserve the correct execution PID when constructing real monitor rows and verify its liveness. Do not simply mark all monitor rows live: dead or reused PIDs and pending/terminal turns must remain excluded. The stronger repair is to calculate capacity directly from the original normalized execution snapshot, then attach its results to presentation rows by stable identity. That removes the need to reconstruct execution facts from an already transformed UI model. Apply equivalent behavior to the filesystem loader, index-backed loader, and exact-delta refresh. The domain rule and any shared PID/lifecycle normalization belong in Rust core; Python should pass and render those facts.

**Finding 2: the TUI drops canonical claim ownership — confirmed by a synthetic parity probe.**

`capacity_record_from_scan()` forwards `runner_claim_owner_key`. The TUI `Agent` model has no field with that name, and `capacity_record_from_agent()` does not forward it. Rust explicitly prefers that persisted key over session/parent inference. [S1, S2, S6]

I constructed two live unit-weight records in the same displayed session with different explicit claim owners, representing independent branches whose ancestry need not be loaded. The runtime projection returned two claims and capacity 2. The corresponding TUI projection inferred one session claim and returned capacity 1. This establishes a real lossy adapter boundary. It does not establish that the screenshot involved this second defect.

The repair is to carry canonical claim ownership through all adapters, preferably by retaining the original Rust capacity result rather than reconstructing claim identity from a displayed session. Parent and session relationships are useful presentation data, but not substitutes for a persisted admission identity. Regression coverage must include parallel branches, serial successors of parallel branches, absent terminal ancestors, and bounded history. Merely testing two independent standalone agents does not exercise this case.

**Finding 3: invalid accounting can be displayed as healthy free capacity — confirmed.**

Rust intentionally skips an invalid live claim from the numeric sum, emits `invalid-live-claim-weight`, and fails new admission closed. The numeric result is therefore only the valid subtotal. However, `_apply_runner_capacity_snapshot()` drops the top-level diagnostics, and the TUI `RunnerCapacitySnapshot` has no diagnostic or validity field. [S1, S7]

A single live invalid-weight fixture produced this combination:

```text
Rust diagnostic: invalid-live-claim-weight
TUI numerator:   0.0
TUI tooltip:     Runner load: 0 of 8 capacity units in use (8 free).
                 New agents queue when load reaches capacity.
```

Existing parity coverage checks that queued agents receive the `capacity-snapshot-invalid` blocker. It does not require the headline to disclose the same fault. With no waiter to inspect, the user may see no explanation at all. [S9]

Retain diagnostics and an explicit accounting-validity state. Render, for example, `athena capacity ?/8 · accounting error`, with detail `known subtotal 3; 1 unresolved claim; admission blocked`. An unknown contribution must never be rendered as an intentional zero, and a subtotal with invalid claims must not generate a green “free” message. Diagnostic severity must be typed: an informational compatibility translation is not equivalent to an invalid snapshot.

**Other UX limitations confirmed in the source.** The current load tooltip already lists “Held by” entries, up to twelve, so adding that list is not a new solution. It only covers recognized, resolvable claims, and shows neither rejected records nor the full reconciliation. `_capacity_holders()` can omit a claim when no display row or usable label resolves. The holder value stores only label, weight, and kind, losing claim identity and the member-to-claim relationship. [S7]

Default unit weights are hidden. Monitor row badges expose only explicit zero; positive monitor weights are suppressed. Clan containers and serial child rows suppress weight badges, too. These choices reduce clutter but make precisely this screenshot difficult to audit: the missing positive monitors are hidden inside container summaries, and the zero monitor may be hidden there as well. An authored weight is also different from the amount currently contributing, so showing every authored `wN` alone would still be misleading. [S10]

The load widget has a hover tooltip but no dedicated activation handler for a full explanation. Its compact form can lose the “load” label. Its tooltip's categorical claims about when agents queue ignore candidate weight and other admission blockers. Its two-decimal formatting can hide very small positive values or small overages. These are presentation problems; the Rust summation itself uses compensated summation and a small floating-point comparison tolerance. I found no evidence that changing the arithmetic algorithm would resolve this incident. [S1, S7]

**Recommended interaction, illustrated with the reconstructed screenshot state.** Keep the ordinary tree readable, but make the capacity chip visibly actionable and accessible through the command/help interface. A new keybinding, if chosen, must be reflected in default configuration and help. Use plain wording and a named machine:

```text
Agents: 6 active                         athena capacity 5/8 ▸

Machine capacity · athena                         observed 2s ago
5 units in use / 8 default limit · 3 units headroom
3 provider executions + 3 monitor executions active
5 contributing claims · 1 explicit zero claim

Execution                  In use   Weight source       Explanation
bob-cli-ct.5                  1      default             Provider running
sase-1oh.5.1.2                1      default             Provider running
sase-1oh.4.1.2                1      default             Provider running
bob-cli-ct.3--mon             1      inherited           Testing monitor
sase-1oe.3--mon-1             1      explicit            Testing monitor
sase-1n6.10--mon              0      explicit            Waiting monitor
Total                        5

All local work, including rows hidden by this view.
Select an execution to locate it; expand for claim and source details.
```

This is a proposed view of reconstructed data, not a captured screen or a claim that these agents still have those states. Labels such as “testing” explain known monitor purpose; free text like TESTING must not determine accounting policy. If shared claims exist, group their members under one charged claim and show `shared with …` on secondary rows rather than adding their weights again.

The inspector should answer four questions in one place: what counts, what does not count and why, where the limit came from, and what prevents queued work from starting. Its default list should include positive contributions, explicit zero claims, and anomalous active records. Queued and intentionally excluded work can be expandable; completed history should not flood the default list. All lists must be complete or explicitly say they are truncated.

Use distinct contribution states:

| State shown to the user | Meaning |
| --- | --- |
| `1 in use · default` | One current claim using the default weight. |
| `0.25 in use · authored` | A fractional weight currently charged. |
| `0 · explicit zero` | Valid and intentionally uncharged; show its source/reason. |
| `shared with <owner>` | Execution belongs to an already charged claim; not another additive amount. |
| `0 now · requests 1` | Queued execution has a future requested weight, no current reservation. |
| `excluded · awaiting answer` | Known lifecycle exclusion with a specific explanation. |
| `? · PID unavailable` | Required execution evidence is absent; do not pretend this is a valid zero. |
| `? · invalid weight` | Accounting fault, including admission consequences. |

In each selected node's Context card, show its current contribution, configured/effective weight and origin, claim owner when shared, and one sentence explaining the result. Container rows may show a small aggregate `capacity 2` badge, computed over distinct descendant claim IDs. Expand an aggregate to its actual executions. Offer an optional aligned contribution column for auditing many rows; do not permanently crowd every tree row with detailed metadata.

The chip should continue to represent the named machine's full accounting scope even while viewing a project, tribe, search result, or remote tab. Clearly state `all local work` and identify hidden contributors. If a remote machine's capacity is available, give it its own labeled snapshot and age; otherwise show unavailable, not an inferred value from remote visible rows. A machine/tab switch must not make an unlabeled local numerator appear remote.

The denominator detail should expose configured limit, active override and expiry, and the fact that a queued candidate may have its own budget. A queue row should say something like `requests 2; usable headroom 1; blocked by capacity`, or name the actual hold/input/error. Do not turn headroom into a launch-time prediction. Preserve precision in the inspector while using compact rounded values in the chip, marking approximation where it could change interpretation.

For refresh behavior, publish the count summary, contributions, totals, and diagnostics with a snapshot generation and observation time. Keep stable selection as values refresh. If a new observation is incomplete or unavailable, disclose that and retain a visibly stale last-good view rather than manufacturing zero. Provide a copy/export action for the exact accounting explanation so a future screenshot investigation need not infer state from unrelated later observations.

These recommendations follow two established design principles: communicate system state so users can understand and act on it, and expose relevant choices and explanations rather than requiring remembered rules. The application-specific inspector and contribution vocabulary are my design inference from those principles, not a prescription from an external source. [Nielsen Norman Group: visibility of system status](https://www.nngroup.com/articles/visibility-system-status/), [recognition and recall](https://www.nngroup.com/articles/recognition-and-recall/).

Separating reserved capacity from measured utilization also has a useful operational precedent: Kubernetes schedules against resource requests, which need not match momentary CPU/memory usage. This supports labeling SASE's policy metric accurately; it does not imply SASE should adopt Kubernetes resource enforcement or scheduling behavior. [Kubernetes resource management documentation](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

**Implementation and verification evidence needed before landing.** Prefer a shared Rust-owned explanation projection over a second Python accounting algorithm. The projection should return snapshot validity/freshness, limit provenance, distinct claims, and a per-execution disposition with a typed reason. Preserve source execution identity, canonical claim key, effective weight and origin, current contribution, and relevant blockers. The host supplies verified liveness; frontends map identities to labels and navigation. Diagnostic detail can be expanded without exposing raw storage paths in the primary user flow.

Make the sum invariant explicit: the distinct positive/zero claim amounts displayed in a valid snapshot must reconcile exactly with its numerator before display rounding. Every relevant active execution must resolve to a claim, a documented exclusion, or an unknown/error disposition. Missing a label must produce a fallback identity, not silently remove a numeric contributor. Group totals must deduplicate claims, and presentation filters must not change machine occupancy.

The minimum meaningful regression matrix is:

| Case | Required result |
| --- | --- |
| Real monitor artifacts: live meta PID, null workflow PID, weight 1 | Runtime, CLI, full/index/delta TUI loaders and chip all show 1. |
| Same monitor with explicit weight 0 | Shows an explained zero holder, not missing or unknown. |
| Three provider agents, two testing monitors, one zero monitor | Six active agents and five units, with six inspectable dispositions. |
| Dead supervisor, reused PID, pending gate, terminal monitor | Appropriate exclusion or uncertainty; no ghost claim. |
| Two distinct owners in one displayed session, missing ancestors | Two independent charges remain distinct. |
| Overlapping serial records for one owner | One charge at the policy-defined maximum; sharing explained. |
| Invalid live weight, with and without waiters | Accounting error visible; no claim of reliable free capacity. |
| Default weight absent, explicit zero, fractional/heavy weights | Defaults, exemptions, and precise charged values remain distinguishable. |
| Search/fold/project/tribe/remote tab changes | Local machine total unchanged; scope and hidden contributors clear. |
| Override expiry, smaller per-launch budget, hold, overload | Chip and admission explanation agree without promising a start. |
| Partial/stale refresh or provider change during refresh | Observation quality visible; no mixture presented as one fresh snapshot. |

The current `tests/test_capacity_snapshot_parity.py` is a good home for boundary coverage, but its basic entity fixture supplies PID directly and omits canonical ownership. Add source-artifact loading to the monitor case and ownership to the shared fixture. Existing invalid-weight tests demonstrate admission blockers but need a headline/inspector assertion. This research ran targeted Python probes; it did not run the full test suite because it made no implementation changes. Any implementation crossing the shared boundary must update the Rust wire/binding tests and SASE's core revision pin.

**Source and reproduction record.** Local source inspected: SASE commit `f4591e9106830fb5e558d71f506b4a2d9fe9791b`; screenshot commit `dd12f981ae3256d135114dc46aaa2eb4ecb73ddf`; linked sase-core commit `d14a32c8242aea936f39711a8452ef0ba08b121d`; installed Python binding `sase-core-rs 0.42.7`; SASE CI core pin `416db28904d080f5fc1ed884dfc256a4d0427fa6`. No changes between the screenshot commit and inspected SASE HEAD appeared for the critical loader/capacity adapter files. The linked core's `runner_capacity` directory also had no diff against that CI pin. These facts support applicability without claiming that every installed component was identical to the current checkout.

Repository-relative source anchors, intended to remain useful after this report moves:

- **S1:** `sase-core:crates/sase_core/src/runner_capacity/records.rs:31,102`; `claims.rs:28,105`; `snapshot.rs:17,60`; `capacity_math.rs`. Occupancy, weight validity, grouping, diagnostics and summation.
- **S2:** `sase:src/sase/core/runner_slots/_admission_capacity_records.py:137,179,228`; `_admission_snapshot.py`. Original execution PID and canonical owner mapping into Rust.
- **S3:** `sase-core:crates/sase_core/src/runner_capacity/waiters.rs:144`; `candidate.rs`; `queue_directive.rs:181`. Candidate limits, blockers, shared claims and authored budgets.
- **S4:** `sase:src/sase/monitor/member.py:60`; `src/sase/bead/epic_launch.py:232`; `src/sase/turns/member.py`. Weight inheritance and explicit zero supervision.
- **S5:** `sase:src/sase/ace/tui/models/_agent_clan.py:400`; `actions/agents/_display_detail_info.py:101`; `actions/agents/_loading_compute.py:342,485`. Status counts, local scope and capacity roster.
- **S6:** `sase:src/sase/ace/tui/models/_loaders/_workflow_snapshot_loaders.py:118,266,286`; `_meta_enrichment_wire.py:234`; `models/_agent_runner_slot_capacity.py:35,196`; `models/_agent_state*.py`. TUI projection and missing PID/owner identity.
- **S7:** `sase:src/sase/ace/tui/models/agent_runner_slots.py:210,333,345,380`; `models/_agent_runner_slot_types.py`; `widgets/agent_load_indicator.py:84,111,129`. Dropped diagnostics, holders and current tooltip behavior.
- **S8:** `sase:src/sase/config/core.py:466`; `ace/tui/modals/models_panel_runner_limit_cards.py`. Effective limit and existing configuration UI.
- **S9:** `sase:tests/test_capacity_snapshot_parity.py:50,221,315,456`. Existing parity fixture and assertions.
- **S10:** `sase:src/sase/ace/tui/widgets/_queue_weight_badge.py:38`; `models/_agent_runner_slot_types.py:69`. Badge suppression/default formatting.

Execution metadata inspected was limited to relevant screenshot agents, with no swarm peer findings consulted. The two concrete monitor probes used these machine-local artifact directories:

```text
~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/26/20261026172102
~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/25/20261025175222
```

The testing monitor whose interval brackets the screenshot was:

```text
~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/26/20261026172532
```

Metadata is later observation, not an archived 17:27:51 snapshot. The code-path probes used `.venv/bin/python` in the inspected SASE checkout. A minimal deterministic reproduction for the two additional defects follows; it reads no live agents and mutates no files:

```python
from datetime import UTC, datetime
from sase.ace.tui.models.agent import Agent, AgentType
from sase.ace.tui.models._agent_runner_slot_capacity import capacity_record_from_agent
from sase.ace.tui.models.agent_runner_slots import refresh_runner_slot_context
from sase.ace.tui.widgets.agent_load_indicator import _agent_load_tooltip
from sase.core.runner_slots import runner_capacity_snapshot_from_capacity_records

now = datetime(2026, 10, 26, tzinfo=UTC)
rows = [
    Agent(
        agent_type=AgentType.WORKFLOW, cl_name=name, agent_name=name,
        start_time=now, project_file='/tmp/proj/proj.sase',
        artifacts_dir=f'/tmp/proj/artifacts/ace-run/{timestamp}',
        raw_suffix=timestamp, status='RUNNING', pid=123,
        runner_is_live=True, run_start_time=now,
        agent_session='same-session', parent_timestamp='20261025120000',
        queue_weight=1.0, workflow='ace-run', appears_as_agent=True,
    )
    for name, timestamp in [
        ('branch-A', '20261026120000'), ('branch-B', '20261026120100')
    ]
]
records = [capacity_record_from_agent(row, {}) for row in rows]
for index, record in enumerate(records):
    record['runner_claim_owner_key'] = f'parallel-origin-{index}'
raw = runner_capacity_snapshot_from_capacity_records(records, effective_limit=8)
ui = refresh_runner_slot_context(rows, effective_limit=8)
print(raw['occupied_capacity'], ui.occupied_capacity)  # observed: 2.0 1.0

rows[0].queue_weight_invalid = True
raw = runner_capacity_snapshot_from_capacity_records(
    [capacity_record_from_agent(rows[0], {})], effective_limit=8
)
ui = refresh_runner_slot_context([rows[0]], effective_limit=8)
print(raw['diagnostics'])  # observed: invalid-live-claim-weight
print(_agent_load_tooltip(ui.effective_limit, ui.occupied_capacity, ui.holders))
# observed: 0 of 8 capacity units in use (8 free), with no accounting warning
```

**Recommended decision.** First repair the monitor PID projection, preserve canonical claim ownership, and carry accounting validity/diagnostics through to the display. Keep the existing weighted-claim policy: the evidence does not justify replacing it with “running count minus waiting monitors.” Then ship `athena capacity 5/8` as an actionable chip, a keyboard-accessible capacity inspector, and per-node contribution explanations that distinguish default, inherited, explicit zero, shared, queued, excluded and unknown states. Finally, make runtime admission, CLI and every TUI refresh path consume the same Rust-owned explanation snapshot and export that snapshot for incident review. This addresses the likely 3-versus-5 defect and makes future discrepancies diagnosable without guessing from a screenshot.
