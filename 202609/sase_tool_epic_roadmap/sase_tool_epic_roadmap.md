# The `sase tool` epic roadmap

**Consolidated report** · 2026-09-17 · host apollo · sase master `14403c1594` · core pin
`e210d18a80` (published `v0.34.47`)
**Sources:** researcher A (`sase_tool_epic_roadmap__a.md`, seven-epic decomposition and
contract analysis), researcher B (`sase_tool_epic_roadmap__b.md`, six-epic split plus a
fresh 14-day apollo measurement and bead-graph analysis), the prior consolidated
use-case report (`research:202609/sase_tool_control_plane/sase_tool_control_plane.md`),
and the lead researcher's own verification against today's tree and bead store.

**Question.** Is the `sase tool` work large enough to split into multiple epics, each
with a result a normal user can verify? How should it be split, and how does in-flight
epic work (especially `sase-11y`) conflict with or complement it?

---

## 1. Answer up front

**Yes. This is eight epics, not one — and the first move is to retire `sase-zm`, not to
plan anything.** Both researchers reached the multi-epic conclusion independently (A:
seven epics; B: six), for the same underlying reason: the work contains several
*different products* with different evidence prerequisites, different failure modes, and
different calendar gates — prediction cannot be calibrated until a corpus has
accumulated for weeks, and admission cannot be priced until prediction is calibrated.
Their differences are structural, not directional, and §3 resolves them into one set:

| # | Epic | Size | User-verifiable result |
| --- | --- | --- | --- |
| **E1** | Named tools and the ToolRun ledger (foreground) | large (~8–9 phases) | `sase tool run check` prints one line per stage; `sase tool runs` / `show` reprint the durable timeline; `sase tool list` shows last result + typical duration |
| **E2** | Durable hand-off execution | medium (~5–6) | start a run, leave the shell or agent turn, `show --follow` it live, `stop` it; exactly one ToolRun linked to exactly one monitor/proc |
| **E3** | Failure triage: NEW vs KNOWN vs FLAKY | medium (~6) | a failed run labels each failure NEW or KNOWN; `sase tool failures` groups today's red-master signatures across agents |
| **E4** | Verification receipts and staged reuse | medium (~6–7) | the second `sase tool run check` on an unchanged tree returns instantly citing a receipt; `just install` no-ops; a lint failure stops before the heavy stage |
| **E5** | Tool runs on the TUI surfaces | medium (~6) | a live run shows on the owning agent's row; its detail card shows stages + log tail; the old Tools panel is now **LLM Calls** and links to the run |
| **E6** | Forecasts and automatic inline-vs-hand-off | large (~8–9) | `run -E` explains predicted duration and the decision; `check-full` hands off with a one-line reason; `stats` reports ≥80% interval coverage |
| **E7** | Local tool capacity admission | large (~8) | a second heavy run queues with an expected start instead of oversubscribing; refusals print an executable retry |
| **E8** | Fleet capacity surfaces and coordinated rollout | medium (~6) | machine badges/meters show fresh/stale capacity fleet-wide; drill-down answers "why is apollo busy?"; staged athena/apollo/mac cutover with proven rollback |

Sequencing: **E1 → E2 → {E3, E4, E5 in parallel} → E6 → E7 → E8**, where E6's *start*
is set by corpus age (~3 weeks of recorded load samples), not by roadmap position —
E3–E5 fill that window. On the project's measured epic cadence this is weeks of wall
clock, not a quarter, and every epic pays for itself even if its successors never ship.

## 2. Where all three investigations agree (each independently verified)

These points now have three concurring sources — the control-plane report plus both
researchers — and I re-verified the load-bearing facts on today's tree (§7):

1. **The wrapper's value is the record, not the queue.** Record first, admit last.
2. **`sase-zm` must be superseded before any new plan is written.** 14 phases, zero
   closed (re-verified today), no landed implementation, no capacity fixtures on
   master, and its scope is exactly what the new epics take over. Leaving it open
   keeps drawing land-agent attention and makes seam ownership ambiguous.
3. **Zero new supervisors.** A ToolRun is a *semantic record* delegating execution to
   one of three existing executors: inline child, monitor (in-agent), durable proc
   (standalone). `sase tool` is already the *fourth* "run a command" entry point
   (`proc run`, `monitor start`, `gate`); a fifth supervisor would be a design failure.
4. **A new per-machine Rust-owned store with its own retention** (~180-day summaries,
   shorter logs), registered as a disk owner in the phase that creates it. The proc
   store is disqualified — `procs.history_limit: 100` (verified) would destroy the
   corpus in days — and the telemetry store keeps only aggregates.
5. **Record everything from day one, consume it later.** Fingerprints (tree +
   dirty-diff + inputs + toolchain), per-stage timings, and PSI/loadavg samples. There
   is no load sampling anywhere in `src/`, `tools/`, or `tests/` today (verified), and
   none of it can be backfilled. This is the strongest reason E1 ships recording before
   anything consumes it.
6. **Adoption is instructions + the wrapper.** Provider hooks are gone from the
   transport (B verified), and opt-in features measurably don't get adopted (`verify`
   profile 1/69 on apollo, prepared host completion 0/69). Guidance changes and an
   adoption metric land inside the epics, via `/sase_memory_write` and the skill
   templates.
7. **Free the word "tool" first.** `src/sase/ace/tui/tools/` (verified) means provider
   LLM calls today. Rename that panel **LLM Calls** before the vocabulary collision
   infects every plan and glossary strand; link a wrapping Bash call to its ToolRun
   instead of double-rendering.
8. **Green-master-independent acceptance.** `just check-full` has been red on master
   since 2026-08-10 (`sase-j0`, +38 corroborations, re-verified). No epic exit may
   require a green `check-full` — and the red master is a free real-data fixture for
   E3's KNOWN class.

## 3. Where the researchers disagreed, and the resolutions

### 3.1 Seven epics (A) vs six (B) → eight, by applying B's own evidence consistently

B mined 600 epic-tier beads and showed what actually breaks large epics here: 86% of
epics close without remediation children, and the 14% that spawn deep chains are the
big infrastructure units — driven by (a) trees moving under long epics, (b) released
core-contract ratchets, and (c) **live multi-machine acceptance**. B distilled this as
"one epic, one released contract, one acceptance surface" — then left T1 at 10–11
phases including the hand-off leg, and left T6 with an inherently multi-machine exit
while predicting it would "expect one child epic." A's structure applies B's lesson
better in exactly those two places:

- **Hand-off execution is its own epic (E2), out of E1.** T1 at 10–11 phases would be
  the largest epic shape this project has attempted since `sase-zl` (12 phases, whose
  landing audit produced 20 follow-up outcomes) and `sase-zm` itself (14, never
  landed). E1 and E2 each have a clean independent user story.
- **Local admission (E7) and fleet/rollout (E8) split up front**, rather than planning
  one epic and expecting its remediation child. Multi-machine cutover is the #1
  measured driver of deep remediation chains; isolating it is the deliberate version
  of what would otherwise happen by accident.

Conversely, B's structure beats A's in one place, adopted here:

- **Surfaces are a standalone epic (E5), not folded into A's Epic 2 and Epic 7.**
  Pixel-level TUI acceptance must not share a unit with a supervision or admission
  cutover (B's own lesson), and E5 has independent timing constraints — it should land
  after `sase-124` (Agents-tab freshness) and after `sase-11y.7/.8` so the tool-run
  card and the Services-tab oneshot section are designed together, not merged together.

### 3.2 Is E2 gated on `sase-11y`? → No, if the standalone leg uses plain durable procs

A gated its durable-execution epic on `sase-11y.4/.8` (service host, transient oneshot
service procs). B showed the primitives hand-off actually needs are the two **closed**
`sase-11y` phases — `detach_scope` (cgroup escape, without which a `sase service`
restart kills a handed-off run) and the shared child-supervision library — plus the
monitor machinery (`sase-kp`/`sase-zl`, closed) and the existing `sase proc run`
runner. Resolution, adopting B:

- The standalone detached leg delegates to the **existing durable proc runner** with
  `detach_scope`, not to `sase-11y.8`'s oneshot *service* procs. Tool runs are
  user-initiated work: `sase-11y` deliberately hides `service`-marked rows from the
  Procs tab, and tool procs must stay visible. Do not reuse the `service` marker.
- **The link lives on the tool side only** (`monitor_id`/`proc_id` on the ToolRun; no
  new field on the proc wire). `sase-11y.2` is already bumping the proc wire schema
  for its `service` block; a second concurrent additive field on the same wire is a
  gratuitous merge and floor-ratchet conflict.
- Reopen condition: if `sase-11y.8` lands an oneshot model (recorded exit codes,
  durable rerun) that subsumes what tool procs need, converge on it then — in E5 or
  later, never mid-E2.

This un-gates E2 from in-flight work entirely; the residual coordination with
`sase-11y` is "don't edit the same proc-wire/config/TUI seams concurrently," which the
link-direction rule and E5's timing already handle.

### 3.3 Forecast third (A) vs triage/receipts first (B) → B's order; the conflict mostly dissolves

B's argument is empirical: today's dominant measured waste is **re-discovery and
repetition, not mis-scheduling** — 37.2 h of repeated verification commands and 16.24 h
of `check-full` runs re-discovering one month-old known-red master on apollo alone —
and both are attacked by triage and receipts, neither of which needs a predictor.
Meanwhile prediction is gated on *calendar time*: load-conditioned quantiles need load
samples that do not exist until E1 records them. A effectively concedes this by
allowing its receipt/failure epics to run during the corpus-accumulation window. The
consolidated position: E3/E4/E5 proceed while E6's corpus matures; E6 starts no earlier
than ~3 weeks after E1 lands and stays advisory until chronologically backtested
interval coverage reaches ~80%.

### 3.4 Minor resolutions

- **Interim capacity relief:** while E7 waits for calibration, a heavy tool run arming
  a `sase-11l` `%hold` is a cheap stopgap that needs no ledger (B's D6). A's stricter
  "no admission before evidence" is preserved — the hold is not admission.
- **Cheap-stages-first lives in E4**, not E6: the stage order in `just check` is
  already cheap-first; the missing behavior is running cheap stages inline *before
  paying a hand-off* and minting per-stage receipts the heavy stage reuses. B's
  measured 4–7-second failed hand-offs are the evidence.
- **Core snapshot discrepancy:** A reviewed sase-core master (`b4f7de3a`), B the
  published pin (`e210d18a80`, matching `sase-core-revision.txt` today). The pin is
  what governs deployed behavior; contract work in E1 must ratchet the published floor
  inside the epic that needs it (a measured driver of remediation chains).

## 4. The epic set

Full phase sketches live in the two sibling reports (`__a.md` §"Recommended epic set",
`__b.md` §9); this section records the consolidated boundaries. Every epic owns exactly
one beta flag (removed before landing, per `sase_flags`; note 13 flags are already
open), states green-master-independent acceptance, and assigns each CLI verb and each
durable store to exactly one owner.

- **E1 — Named tools and the ToolRun ledger.** Versioned Rust
  ToolDefinition/ToolRun/store contracts + PyO3 bindings, with the published core floor
  ratcheted inside the epic; `tools:` catalog in `sase/sase.yml` (repo-owned, argv
  arrays, no implicit shell; ad-hoc `run -- ARGV…` recorded but receipt-less);
  foreground execution preserving child stdout/stderr and exit status; fingerprints,
  `run_silent` stage events (today it records no timing and nothing on success),
  PSI/loadavg sampling (recorded, unused); `list`/`run`/`runs`/`show` with versioned
  JSON; compact agent output; retention + `sase disk` ownership; the
  `tool_calls.jsonl` backfill importer (`source: imported`), inline-tool guidance
  updates, and the adoption/bypass metric. The **LLM Calls rename** lands as its first
  phase or as an immediately preceding small task. Out: hand-off, prediction,
  receipts, triage, admission, TUI surfaces.
- **E2 — Durable hand-off execution.** Explicit `-H`: monitor leg inside agents
  (result/continuation through the `sase-zl` graph), plain-proc leg standalone (via
  `detach_scope`); `stop` and `show --follow` as facades over the owning executor;
  crash/settlement reconciliation on both sides; one settlement notification through
  the existing `sase-117` path; the `check-full` "monitor only" prose rule replaced by
  tool guidance. Out: auto-routing, TUI chips.
- **E3 — Failure triage.** Rust signature normalization (strip workspace paths and
  unstable line numbers), verification-vs-infra split, classification against
  master/merge-base and the flake baseline; `failures` and `rerun` attempt chains;
  structured NEW/KNOWN `--next` payloads replacing the hand-written baseline essays
  (median 1,778 chars on apollo — this is also the adoption vehicle for `sase-zl`'s
  built-but-unused machinery); suggested (never auto-created) `ci`/`flake` beads.
- **E4 — Receipts and staged reuse.** Tree- vs workspace-scoped receipts with declared
  inputs and TTL; minting on success only; reuse in `run` with `-R` force;
  unchanged-since-failure refusal; `install` skip; cheap-stages-inline-before-hand-off
  with per-stage receipts; `receipt TOOL` for scripts and landers. Host-completion
  policy, not the agent, decides whether a receipt satisfies a landing gate. Exit 0 is
  not proof of applicability: opt-in per tool, TTL'd, never reuse failures.
- **E5 — Surfaces.** Snapshot-with-change-token contract (per `tui_perf`: no
  per-render filesystem access, no new polling loop); fixed-width agent-row chip;
  agent-detail card (stage timeline, log tail, actions); LLM Calls ↔ run linkage;
  Admin Center Tools pane (Runs first; Stats/Failures views arrive with E6/E3);
  keymaps in `src/sase/default_config.yml`; visual snapshot coverage. Land after
  `sase-124` and `sase-11y.7/.8`.
- **E6 — Forecasts and routing.** Load-bucket empirical quantiles with transparent
  fallback and sample counts (no ML); selection-store covariates; survival-conditional
  remaining time; censored-observation handling; overdue/stalled (never a regenerated
  ETA); `timeout: auto`; `stats` with calibration; `run -E`; then automatic
  inline-vs-hand-off against the provider's inline budget, explained in one stderr
  line; notifications through the existing dedup store. Advisory until calibrated.
- **E7 — Local admission.** Extend the Rust `runner_capacity` authority (schema v5)
  with temporary ToolRun demand — no second ledger, no Python queue; absorb the
  `WorkerTokenLease` worker-token pool from `tests/` into the same accounting; one
  fair queue with aging, finite default wait, expected start; typed refusals printing
  the executable retry; `-B` bypass recorded as forced; pytest workers drawn from the
  shared grant; preserve `sase-10h`'s zero-weight gate semantics and `sase-11l` hold
  boundaries; fail-closed admission with designed break-glass (recording itself stays
  fail-open). Start after E6 calibration and after `sase-zp`/`sase-11l`/`sase-10h`
  settle.
- **E8 — Fleet surfaces and rollout.** Versioned per-machine capacity snapshots over
  the existing fleet wire; fresh/stale/unknown honesty; machine meters and drill-down;
  per-machine capacity through init/doctor; staged athena/apollo/mac activation with
  drain, proven rollback, and no double admission; optional cross-machine prediction
  *hints* in `run -E` (no remote dispatch, no cross-machine result caches). After
  `sase-x7`'s shared-format cutover settles.

Cross-epic invariants (A's list, confirmed by B's findings): one semantic run = one
ToolRun id with explicit attempt chains; one process owner; one log owner (never a
second copied log); one continuation graph (`sase-zl`); one capacity authority
(`runner_capacity`); one fleet transport; versioned JSON from the first release; no
policy feedback before calibration; no unbounded storage; no fake precision.

## 5. Interaction with in-flight work

| Work | Status (verified today) | Relationship | Rule |
| --- | --- | --- | --- |
| `sase-11y` service host | 2/10 phases closed | Biggest interaction; mostly complement — the closed phases (`detach_scope`, supervision lib) are exactly what E1/E2 need | §3.2: plain visible procs, link on tool side only, no `service` marker; E5 after `.7`/`.8` |
| `sase-zm` capacity epic | 14 phases, 0 closed, no landed code | Superseded — its scope is distributed across E1/E2/E6/E7/E8 | Retire first (§6); keep-list preserved in the control-plane report §8 |
| `sase-z4`/`sase-zt` (closed), `sase-zp`, `sase-10h`, `sase-11l` | zp/10h/11l in progress | E7's substrate and constraints | E7 extends Rust capacity policy; starts after these settle; `%hold` is the interim |
| `sase-zl` monitor continuations | closed | Pure complement; built and unused (verify profile 1/69, host completion 0/69 on apollo) | E2 links it as execution owner; E3 makes its structured results the default payload |
| `sase-zw` disk retention | in progress | New ~180-day store + logs is a new disk class | Retention owner lands in the same phase as the store |
| `sase-124`, `sase-zn`, `tui_perf` | 124 in progress | E5 constraint | Cached snapshots + change tokens; land E5 after `sase-124` |
| `sase-x7` canonical-only | in progress | New wire types born canonical | Defer cross-machine publication (E8) until its cutover settles |
| `sase-11e` renames, `sase-113` | 11e in progress | Vocabulary | New-vocabulary strings everywhere; stay out of `src/sase/axe/**`; new glossary strands via `/sase_memory_write` |
| `sase-j0`/`sase-th`/`sase-10w` red master | j0 in progress, +38 | Confound and fixture | D7 acceptance rule; E3's KNOWN class demos on real data day one |
| `sase-s6` typed launch units | beta flag on | Complement | The standalone `-H` path rides typed proc launch units |

## 6. First moves (in order)

1. **Retire `sase-zm` explicitly.** `sase bead close sase-zm --force -R superseded`
   with a reason pointing at this report and the control-plane keep-list. As the owner,
   deliberately — closing a plan bead with unclosed phases is normally the land agent's
   job. (`sase-zm.5`'s dependency on `sase-zl` dies with it.)
2. **Write one decision record** (via `/sase_memory_write`): *"Expensive commands are
   recorded before they are admitted"* — claim, alternatives (admission-first
   `sase-zm`; recognition-by-profile; reusing the proc store), costs (new store, new
   disk class, instruction-led adoption), and the reopen condition (a measured
   concurrent-duplicate or queue-starvation rate). This makes the invariants citable
   from eight plans and stops re-litigation.
3. **Land the LLM Calls rename** as a small standalone task (via `/sase_new_task`) or
   E1's first phase — independently user-verifiable and it unblocks unambiguous
   writing everywhere.
4. **Write the E1 plan only** (via `/sase_plan`), with the §4 invariants stated as
   cross-cutting rules and E2–E8 named as successors so reviewers see what E1
   deliberately omits. Do not write eight plans up front: E3–E8's content should be
   revised by what E1 measures. E1's first planning session must also settle A's
   contract questions: store shape (SQLite entity store; telemetry stays aggregate),
   config-field provenance (repo-owned identity vs machine-tunable operational
   fields), log ownership, recording-failure semantics (warn and run), argv redaction
   (protected execution argv separate from display argv, no env dumps), and whether a
   `tool:<run-id>` artifact reference is reservable.

Decisions that should wait for evidence: admission weights, automatic timeouts,
single-flight joining (zero repeated request fingerprints in 14 days on apollo),
fleet placement, any ML predictor, cross-machine receipt reuse.

## 7. Open questions for Bryan

1. **Catalog placement** — both researchers and the control-plane report recommend the
   repo (`sase/sase.yml`), which means a tool's stages and price are reviewed like
   code. Confirm.
2. **Is `sase tool` the name?** It collides conceptually with provider "tool calls";
   `sase tool` + the LLM Calls rename is the joint recommendation (`run`/`task`/`job`/
   `gate` are taken; `cmd`/`verify` are each worse).
3. **Epic count comfort.** Eight units is the evidence-backed recommendation, but E3
   and E4 could merge into one "intelligence" epic (~12 phases) if you prefer fewer,
   at the cost of exactly the size profile §3.1 warns about. I recommend keeping them
   separate.
4. **`-w` letter** — `proc run` uses `-w` for `--wait`; E7 wants it for demand. A
   deliberate cross-command inconsistency to choose now (it must never be argparse-
   required regardless).
5. **E5 timing** — third (elapsed-only chips, my recommendation: an invisible feature
   is an unadopted one) or after E6 so chips ship with ETAs?

## 8. Lead verification appendix

Claims I independently re-verified on apollo today (2026-09-17, tree `14403c1594`):

- `sase --full-help`: no `tool` command; `proc` and `monitor` exist. `procs.history_limit: 100` in `src/sase/default_config.yml`.
- `sase bead show sase-zm`: 14 phases, all IN_PROGRESS, zero closed. No `sase-zm` implementation commits on master; no `tests/fixtures/*capacit*`.
- `sase bead show sase-11y`: exactly `.1` (cgroup escape) and `.3` (supervision library) CLOSED; `.2/.4/.5/.6/.7/.8/.9/.10` in progress. `sase-11l`, `sase-124`, `sase-zp`, `sase-10h`, `sase-x7`, `sase-zw`, `sase-11e` all IN_PROGRESS; `sase-j0` open with +38 corroborations.
- B's monitor measurements reproduce exactly: 69 monitors, `elapsed_seconds` on only 30 terminal rows, 29 terminal `just check-full` monitors with **0 completed**.
- No `getloadavg`/`/proc/pressure`/`loadavg` hits anywhere in `src/`, `tools/`, `tests/`. `tests/_suite_gate_lease.py` `WorkerTokenLease` exists. `src/sase/ace/tui/tools/` exists (the name collision). `_observation_fingerprint` exists in `src/sase/monitor/host_completion_state.py`. Core pin `e210d18a80` matches B's citation; A reviewed sase-core master, which is ahead of the pin — the pin governs deployed behavior.
