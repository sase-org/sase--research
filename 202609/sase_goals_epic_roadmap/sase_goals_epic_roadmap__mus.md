# Splitting SASE Goals into multiple distinct, verifiable epics

_Researcher mus · 2026-09-27 · project: sase_

**Question.** The goals design (`research:202609/sase_goals_design/sase_goals_design.md`,
read via `sase artifact read`) is currently framed as one `xlarge` epic behind a
`goals` flag with phases P0–P4. Is that the right shape, or should it be split into
multiple distinct, verifiable epics? If split, where exactly are the seams?

**Short answer.** Split it. I recommend **five epics plus one hardening/landing epic**,
sequenced as a DAG, not one big-bang epic. Each epic below is independently shippable
behind the existing flag scaffolding (or its own thin flag), has its own acceptance
tests, and leaves the product no worse than before if later epics stall. A single epic
is not appropriate: the work spans four different verification surfaces (Rust unit/CLI
latency, launch/binding integration, finalizer protocol, gates/notifications, TUI
goldens) and at least three review skill sets, so one epic would be hard to verify,
hard to review, and hard to roll back.

I verified the key seam points against the tree myself (citations below). I did not
read any peer `__cdx/__cld/__grk/__gem` split reports.

## 1. Method and grounding

Sources: the goals design synthesis (the `sase_goals_design.md` lead synthesis only),
plus spot-checks of the current tree at the workspace checkout:

- Finalizer config shape: `finalizers: defaults: [commit], required: []` with a
  `commit` instance (`src/sase/default_config.yml`, finalizers block). So a
  `builtin@goal` "required, after commit" addition is a config + controller change,
  separable from storage work.
- Launch seam: `src/sase/agent/launch_spawn.py:86` pops `SASE_PLAN` on every spawn.
  The design's claim that `SASE_PLAN` is commit plumbing rather than a plan-presence
  signal is consistent with what I saw (also set again only for plan-approval
  successors / session attach). Binding-at-launch is therefore its own work item with
  its own integration matrix, independent of the ledger.
- Lineage gap: `parent_agent_name` is read in `src/sase/agent/launch_request_planning.py`,
  `src/sase/agents_sync/inventory_sources.py:277`, and the list-entry builder, but no
  production write path stamps it into child `agent_meta.json` on the paths I checked.
  Persisting parent lineage is a small, prerequisite-shaped change — exactly the kind
  of thing that should land and verify alone rather than hide inside a mega-epic.
- Notification seam: `JumpToAgent` exists
  (`src/sase/ace/tui/modals/notification_modal_constants.py:34`,
  `.../actions/agents/_notification_dispatch.py:75`); `GoalVerify` / `JumpToGoal` do
  not. So verification transport is additive new code with its own gate/CLI/TUI test
  surface, separable from the claim-validation logic.
- Reusable patterns: `src/sase/finalizers/` already has the commit finalizer family
  (`commit.py`, `controller.py`, `declaration*.py`, `ledger.py`), and
  `src/sase/feature_flags/` has a CLI. A goals flag and a goal finalizer therefore
  follow established shapes rather than inventing new ones.
- TUI seam: the Goals tab / lanes / card / chips / grouping work touches tab order,
  goldens, keymap (`src/sase/default_config.yml` per the gotchas note), and jump
  reveal paths — a purely presentational surface verifiable with screenshots and
  golden tests, independent of backend semantics once the CLI contract is frozen.

## 2. Why one epic is the wrong shape

1. **Four verification surfaces, one verdict.** Ledger work is verified by Rust unit
   tests + CLI latency numbers; binding by launch-matrix integration tests; claims by
   finalizer protocol tests; transport by gate/notification tests; the tab by TUI
   goldens. One epic forces a single "done" judgment across all five, which in
   practice means the easy surfaces get checked and the slow ones (TUI soak,
   cross-machine sync) get waved through.
2. **The flag lives too long.** A single epic keeps the `goals` flag open across
   storage → binding → finalizer → gates → TUI → cutover. Long-lived flags rot:
   later phases build on unreviewed earlier phases, and reverting anything means
   reverting everything.
3. **Reviewer mismatch.** Storage/sync wants a Rust reviewer; binding/finalizer wants
   a launch-protocol reviewer; the tab wants a TUI reviewer. One epic either waits
   for all three on every change or gets rubber-stamped by whoever is available.
4. **Cutover risk concentrates.** The riskiest user-visible step (silencing success
   pings, §4.6 of the design) should be its own go/no-go decision with its own
   metrics, not the tail of an epic that is already "almost done."
5. **Stall amplification.** If the TUI tab stalls, a single epic holds the ledger,
   binding, and claim work hostage. Split epics let CLI/gate value land first.

Counter-argument (when a single epic would be right): if the team were one person
doing a throwaway prototype with no flag and no cross-machine promises, one epic
minimizes coordination overhead. That is not this project: the design explicitly
promises conflict-free sync, O(n_unsettled) reads with latency targets, and a
notification cutover — all of which need independent acceptance gates.

## 3. Proposed epic decomposition

Six epics (E1–E5 + E6 landing). Each lists scope, explicit non-goals, acceptance
criteria, verification method, and rough size. Dependencies form a DAG (§4), not a
strict chain: E1 unlocks E2/E3; E2+E3 unlock E4; E4 unlocks E5; E6 closes.

### E1 — Goal ledger + `sase goal` CLI foundation (Rust-owned)

**Scope.**

- `sase-core` goal domain: ids (5-char Crockford base32), events, reducer,
  transitions, `STORE.json` schema fence.
- Ledger layout: immutable `items/<id>/events/<ulid>.json` + `live/` markers, no
  in-place edits, marker-races-resolve-by-reduction rule.
- Hidden-host-clone write path for the beads-co-hosted `goals/` role; machine-local
  fallback layout for projects without the sidecar.
- `sase goal list/show/doctor/new/drop/merge` read path + `goals-hot.json`
  projection + Rust fast path; `goal:` artifact kind + resolver (read-only).
- CLI rules compliance (alphabetical options, short aliases).

**Non-goals.** No binding, no finalizer, no gates, no TUI tab, no notification
cutover, no idle-nudge automation. `new` is human-only seed for testing; agents may
not call it.

**Acceptance criteria.**

1. `sase goal list` p50 < 30 ms warm; p95 < 50 ms at 1,000 unsettled goals
   (measured, on stated hardware, committed as a regression test or recorded
   benchmark — not asserted prose).
2. Adding 100k settled goals changes hot-list p95 by ≤ 10% (the design's contract).
3. File-open tracing proves a warm list never opens settled goals' directories.
4. Concurrent appends from two clones rebase without content conflicts; a marker
   race resolves by reduction (scripted two-clone test).
5. `sase artifact read goal:<id>` renders a card; unknown/cross-project refs fail
   closed with a stable error.

**Verification.** Rust unit tests (reducer, transitions, idempotency keys, basis
checks) + CLI integration tests + the latency/tracing tests above. No TUI, no agent
runs needed.

**Size.** L (new domain crate surface + storage + CLI + perf harness).

### E2 — Host binding + draft name/adopt loop

**Scope.**

- Pure-Rust binding-resolution function over launch facts + Python fact suppliers.
- Resolution ladder: explicit `%goal` / session inheritance / plan `goal_id` / clan
  single-goal / parent inheritance / bead link / routine standing goal / draft.
- `goal_binding` on the launch wire (not env-smuggled); `goal_id` persisted in
  `agent_meta.json`; `SASE_GOAL_ID` convenience exposure only.
- Draft intake block injection at the provider-neutral point; `sase goal
  name/adopt/list/show` agent subset; compare-and-swap naming; adopt-with-reason;
  adopt-retracts-review-claim rule.
- P0 lineage prerequisites folded in here (persist `parent_agent_name` +
  `parent_goal_id` into child metadata; plan-propose stamps `goal_id` onto the
  archived plan) — they are small and this epic is their only consumer.
- `%goal` directive registration + tab completion; `@goal:` cite-only expansion.
- `/sase_goal` skill text (list/show/name/adopt); no mandatory `/sase_new_goal`.

**Non-goals.** No claim/verify semantics (goals can sit active/Idle; nothing moves
them to review), no gates, no TUI, no receipt logic.

**Acceptance criteria.**

1. Every new LLM turn has exactly one `goal_id` before provider start; mechanical
   members (monitor, gate, `%proc`) create none and inherit.
2. Launch-matrix test passes: direct, plan, bead-linked, 5-member clan/swarm (yields
   exactly one goal), `%alt`/`%repeat`, session/pipe/questions/monitor/gate
   follow-ups, child via `/sase_run`, retry, dispatch, plan→code successor — each
   preserves the intended binding and role.
3. Clan race test: five siblings name concurrently; exactly one title wins, others
   exit 0 with "already named."
4. Adopted-draft test: an adopted draft never appears in the shared ledger (fetch
   from a second clone proves absence).
5. Stored unit-prompt digest matches `submitted_xprompt.md`; swarm root digest
   separately reachable.

**Verification.** Integration tests over the launch matrix + a scripted 5-member
swarm test (the design's own acceptance #3, moved here where it belongs). CLI-only;
no finalizer, no notifications.

**Size.** L (touches launch orchestration across many call sites, but each case is a
small mapping with a shared test harness).

### E3 — `builtin@goal` claim finalizer + evidence validation

**Scope.**

- Finalizer registration: `required: [goal]`, `after: [commit]`, alongside the
  existing commit instance; `sase_final` one-paragraph skill update.
- Host-built obligation (goal id/revision/status/text/criteria, `draft`, `can_claim`
  + reasons, evidence candidates: `@commit`, created `file:` artifacts, plan ref,
  covering receipt, `@reply` snapshot).
- Agent payload: `claim` (≤280 chars) + typed refs + 1–3 check-it steps + `gaps`, or
  `keep_open` + progress; draft-naming inside the payload as fallback.
- Host-derived eligibility: active-or-naming-draft, role from launch structure
  (phase worker/contributor cannot claim; land agent/owner can; live-wait
  dependencies cannot; routines never), no-live-contributor, `@commit`-requires-commit-success,
  basis-freshness (`stale_final_context` reuse).
- Evidence validation: resolve-at-submit, provenance tie-back (stitch/file/plan
  authored by contributors), symbolic `@commit`/`@reply` resolution after commit,
  receipt-snapshot embedding (machine-local receipts cross machines as snapshots),
  criterion→evidence-or-gaps mapping, strength badge ordering
  (tested › committed › documented › answered).
- `claimed` event append + commit to hidden clone; idempotency on
  `goal:<id>:claim:<n>`; push-with-bound + outbox + `↑ unpublished` chip on failure.
- Prepared-monitor completion carrying a predeclared goal decision (green claims
  with monitor receipt; red becomes `keep_open`).
- Policy hook only: `goals.require_receipt_for_code` default-off (badge `untested`
  otherwise) — no per-project policy UI.

**Non-goals.** No gate creation, no notification routing, no Verify/Reject/Drop UX
(E4 owns the gate; this epic stops at the durable `claimed` event + a pluggable
"claim published" hook the gate epic consumes). No TUI.

**Acceptance criteria.**

1. Epic phases can never claim; the land agent can; claims are refused while another
   contributor is live (unit tests on `decide_goal_action` + integration test).
2. `@commit` refused when commit deferred/failed; missing, cross-project, or stale
   evidence blocks the claim and creates no downstream side effects.
3. Double-submit / retry produces exactly one `claimed` event (idempotency test).
4. Receipt snapshot test: claim created on machine A renders evidence on machine B
   from the embedded snapshot without resolving A's local receipt.
5. `keep_open` storms (N turns, no claim) produce zero user-facing noise and valid
   progress timeline entries.

**Verification.** `sase-core` unit tests for eligibility/validation + finalizer
protocol tests (reuse the existing `tests/finalizers*` harness patterns) + CLI
inspection of the `claimed` event. No gates, no TUI.

**Size.** M–L (new finalizer instance, but the controller/declaration/ledger
patterns already exist).

### E4 — Verification transport: `GoalVerify` gate + notification routing

**Scope.**

- `GoalVerify` interaction gate (Verify with note / Reject with required feedback +
  optional relaunch pre-filled with `%goal:<id>` / Drop); JumpToGoal notification
  row action; Remote Attention dedup on goal+claim id.
- "Read/dismissed is never a decision" inherited from gate semantics; same decision
  available in tab (stub handler is fine — E5 builds the UI), `sase goal
  verify/reject/drop/reopen` (human-only; refused inside agent runs), mobile,
  Telegram.
- Answer-only claims policy: `goals.answer_claims: ack` default (open-the-answer
  settles as `done · acknowledged`, undo window `u`, `verify` opt-in to explicit `v`).
- Follow-up semantics: prompt to a Review-goal agent retracts the claim with
  feedback recorded; prompt to a Done-goal agent opens a `follows`-linked goal.
- Plan-only duplicate suppression (PlanApproval is the decision; no second alert).
- **Dual-run cutover step 1 only**: claims notify alongside today's `done` pings
  (no silencing yet — that is E6's go/no-go).

**Non-goals.** No Goals tab, no lanes/card rendering, no success-ping retirement, no
idle notices, no metrics dashboard.

**Acceptance criteria.**

1. One claim → exactly one gate + one notification across retries and machines
   (dedup test).
2. Reading/dismissing settles nothing (gate-semantics test).
3. Reject requires feedback; accept-with-launch relaunches onto the goal with the
   feedback pre-filled (end-to-end gate test).
4. Answer-claim ack test: opening the answer settles `acknowledged`; `u` undoes
   within the window; explicit-`v` mode honored when configured.
5. Follow-up tests: Review-goal follow-up retracts; Done-goal follow-up chains with
   `follows`.
6. Routing matrix: TUI, CLI, mobile, Telegram all expose the same three branches.

**Verification.** Gate/notification integration tests + CLI tests + manual
TUI/mobile/Telegram checklist (small, transport-only — no visual design review).

**Size.** M (mostly wiring existing gate infrastructure to a new gate type).

### E5 — Goals tab + Agents-tab integration (presentational)

**Scope.**

- Top-level Goals tab in second position (`Agents | Goals ⌖N | Artifacts |
  Services`); Review → Running → Idle lanes (+ collapsed Standing / Done-today,
  lazy history); stable row order; Review-count badge, hidden at 0; Goals inbox tab
  feeding the top-bar `inbox: ⌖N` chip.
- Review card renderer (You asked → Outcome → Claim → Check it → Evidence → Gaps →
  Agents → Timeline) + same renderer for the Agents-tab Goal card; FINAL-deck Goal
  enricher (not a new widget); goal chips on agent rows; `by goal` grouping mode;
  numbered jump chips reusing the relation rail; reveal-path jump (fixing
  `handle_jump_to_agent`'s linear-scan/collapsed-row gap as the prerequisite fix);
  sync-watermark footer ("synced Ns ago") + TTL-gated fetch + `--fresh`.
- Keymap additions in `src/sase/default_config.yml` (`v/r/x/l/e/m/a/p/n//` etc.);
  empty state copy; status-as-text-plus-glyph (never color alone); `⌖` (U+2316)
  glyph + one new accent color checked against the pane palette.
- `goal:` relations projection (`pursues/pursued-by`, `evidences/evidenced-by`,
  `defines/defined-by`, `follows/followed-by`, reuse `supersedes` for merges);
  agent chips via `reveal_agent_navigation_target` with archived-Agent-pane
  fallback.

**Non-goals.** No semantic changes to binding/claims/gates; no cutover; no sync
protocol changes (consumes E1's projection + E4's gate handlers).

**Acceptance criteria.**

1. Frozen-contract test: tab renders entirely from E1 CLI output + E4 gate state
   (mock both; zero backend logic in the TUI).
2. Golden/screenshot tests for lanes, card, chips, empty state, Idle aging badges,
   `↑ unpublished` chip.
3. Jump tests: goal→agent reveals grouped/collapsed live rows; archived fallback
   works; `1–9/$/Ctrl+O` trail behaves.
4. Keymap tests: every new key registered, documented, and conflict-free.
5. Perf: projection paint off the event loop; highlight→paint within the existing
   16 ms budget at n=100 (measured).

**Verification.** TUI golden + screenshot suite + keymap tests + the perf probes.
No Rust, no launch matrix, no gate semantics re-verified.

**Size.** L (large file count, but mechanical given the frozen contract; the
existing FINAL-deck and Artifacts-pane components are reused).

### E6 — Attention cutover + hygiene + metrics + flag removal (landing)

**Scope.**

- Cutover step 2: silence successful `JumpToAgent(done)` (migrate unread success
  rows), keep failures/questions/approvals/sudo/triage unchanged; Idle quiet
  notices; answer-ack default live.
- Hygiene: Idle aging badges + "stale: drop?" nudge after `goals.idle_nudge_days`
  (never auto-verify); auto-name for Runs that died unnamed; `sase goal doctor`
  repair path; local-only labeling.
- Metrics instrumentation: claims/day; verify/reject/ack/lapse per model; median
  time-to-verify; adopt-vs-name ratio; merges/100 goals; Idle age distribution;
  notification volume before/after; hot-list latency flatness.
- Soak + flag removal + docs/changelog.

**Non-goals.** No new semantics, no new surfaces.

**Acceptance criteria (the epic-level go/no-go).**

1. Soak period (propose 1–2 weeks of daily use) meets pre-declared thresholds,
   e.g.: median time-to-verify under the agreed bound; reject rate within the
   expected band (high reject = over-claiming, investigate before landing);
   notification volume down vs. baseline (the design's athena recount gives the
   baseline method: outcomes/day from `agent_meta.json` bound-to-epic ratios);
   hot-list latency still flat.
2. Rollback drill: flag-off restores today's notification behavior with no orphaned
   gates (tested, not assumed).
3. Flag removed; docs + changelog landed; decision log records the answer-claims
   default, tab position/startup-tab choice, visibility posture, and stale-review
   lapse policy (the design's §6 open questions — each gets an explicit answer
   before removal).

**Verification.** Soak metrics + rollback test + docs review. This is the only epic
whose verdict is "the whole thing was worth it."

**Size.** S–M (mostly measurement, docs, and deletion).

## 4. Sequencing and dependencies

```text
E1 (ledger+CLI) ─┬─► E2 (binding) ──► E3 (finalizer) ──► E4 (transport) ──► E5 (tab) ──► E6 (cutover)
                 └──► (E2 needs E1's ledger + goal_id stamp; E3 needs E2's roles/basis)
E4 needs E3's claim hook; E5 needs E1's read contract + E4's gate handlers.
E6 needs all five.
```

- **E1 first, alone.** It has no dependencies and unblocks everything. Land it and
  the team gets a usable `sase goal list` on day one.
- **E2 and E3 can overlap** once E1's `goal_id` + event schema are frozen, but E3's
  eligibility tests need E2's role derivation — sequence E2's role work before E3's
  claim-gating work, or stub roles behind a test seam.
- **E4 starts when E3's `claimed` event shape is frozen** (the gate consumes the
  event, not the finalizer internals).
- **E5 starts when E1's read contract + E4's gate-handler signatures are frozen**;
  mock both and build the UI in parallel with E4's transport work if desired.
- **E6 is last by definition.** Do not bundle it with E5 to "save an epic" — the
  cutover decision must be takable independently of whether the tab looks finished.

Staffing note: E1 wants Rust + CLI; E2/E3 want launch/finalizer protocol; E4 wants
gates/notifications across surfaces (TUI+mobile+Telegram); E5 wants TUI. Four
different reviewers can work in parallel once E1 lands.

## 5. Cross-cutting decisions to lock early (before or during E1)

These are cheap to decide early and expensive to revisit mid-stream:

1. **Co-host vs. split repo.** Accept the design's co-host-first (`goals/` role in
   the beads repo, splittable later on measured contention). Revisit only with
   contention numbers in hand (`corpus-before-mechanism`).
2. **Markers + events over mutable snapshots.** Accept (conflict-free rebase is the
   load-bearing property). E1 proves it with the two-clone test.
3. **Glyph `⌖` (U+2316).** Accept — I confirmed the design's collision note is
   plausible (`◈` is taken in `src/sase`; `⌖` is unused there). E5 re-verifies with
   a grep before painting.
4. **Terminal states `done {verified, acknowledged}` / `dropped
   {canceled, merged, superseded}`.** Accept; fewer states for users, flavors for
   audit. Locked in E1's schema fence so later epics don't re-litigate.
5. **Agents claim, humans settle; status verbs human-only.** Accept (mirrors the
   bead-status rule that agents never hand-edit lifecycle state). Enforced in E3,
   surfaced in E4.
6. **Flag strategy.** One `goals` epic-scaffolding flag for E1–E5 plus per-epic thin
   gates only where independent rollback matters (E4's dual-run switch, E6's
   cutover switch). Removed in E6.

## 6. Risks this split mitigates (and creates)

- **Mitigated: mega-epic verification theater.** Each epic's acceptance list above
  is checkable by one reviewer with one harness. The most common failure of the
  single-epic shape — "the ledger and binding got reviewed, the TUI got eyeballed,
  the sync and cutover got trusted" — becomes structurally impossible.
- **Mitigated: stalled-tab hostage.** If E5 stalls, E1–E4 still deliver CLI +
  gate value (claims verifiable from CLI/mobile/Telegram).
- **Mitigated: silent contract drift.** E1→E5 handoffs are frozen contracts
  (event schema, `claimed` shape, read/gate-handler signatures) with consumer tests,
  not shared-branch assumptions.
- **Created: contract-freeze discipline.** The split only works if E1's schema and
  E3's `claimed` shape actually freeze before consumers build. Mitigation: E2–E5
  each open with a "contract test against the frozen shape" task, and any schema
  change re-opens E1 explicitly rather than sneaking in downstream.
- **Created: epic-count overhead.** Six epics mean six beads, six reviews, six
  landings. That is the point — but keep each epic's scope sheet to one page so
  the overhead stays in the process, not in the design.

## 7. Recommended solution

1. **Do not run goals as a single epic.** Approve the six-epic split above (E1
   ledger+CLI; E2 binding+adopt; E3 claim finalizer; E4 gate transport; E5 Goals
   tab; E6 cutover+landing).
2. **Land E1 first** with the latency/conflict acceptance tests as the definition
   of done; freeze the event schema and the read contract on landing.
3. **Sequence E2 → E3 → E4 → E5** per the DAG, allowing E2/E3 overlap and E4/E5
   overlap behind frozen-contract tests.
4. **Hold E6 as the single go/no-go**: dual-run first (E4), silence successes only
   after soak metrics clear pre-declared thresholds, then remove the flag.
5. **Answer the design's §6 open questions explicitly in E6** (answer-ack default,
   tab position/startup tab, visibility posture, routines-as-standing-goals,
   launching-project ownership, stale-review lapse) and record each answer in the
   landing notes — not as drive-by decisions inside earlier epics.
6. **If resourcing forces fewer epics, merge adjacent pairs only**: E2+E3 (both
   launch-protocol) or E4+E5 (both attention surfaces) — never merge E1 into
   anything (its perf/conflict contract must stand alone) and never merge E6 into
   E5 (the cutover decision must stay independent). Even merged, keep each half's
   acceptance list verbatim.

**Smallest shippable value.** E1 + E2 + a read-only `show` is already useful (every
turn attributable to an outcome, inspectable from the CLI) before any claim, gate,
or tab exists. That early, cheap win is the clearest sign the split is right: a
single epic would deliver nothing until everything lands.
