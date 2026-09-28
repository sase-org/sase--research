# Goals vs. notification filtering: is the Goals program worth it?

_Research critique · 2026-09-28 · researcher mus · project: sase_

**Question.** If the only value-add of "goals" is better notifications — users are
only notified when work they asked for is complete — couldn't we just customize
xprompt swarms and/or agent clans to only send a completion notification for
certain agents?

**Short answer.** The premise is false, and the cheap fix is real but narrow. You
*could* silence contributor pings in about one small task, and you probably should
as a stopgap. But that buys one quieter inbox, not what Goals G1–G6 actually buy:
a durable, citable, cross-machine outcome record with human settlement, evidence
checked by the host, and one verification inbox. Notification filtering is the last
and smallest epic (G6, 4 phases). The expensive parts (G1–G5) solve identity,
verification, and audit problems that per-clan notification flags cannot solve and
would have to re-derive anyway. Press forward, but narrowly: keep landed G1, do
G2+G3 next, measure, and keep G6 gated.

## Sources (all independently read; no peer swarm reports consulted)

- `research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md` — the six-epic
  program (G1–G6 + JumpToAgent pre-task), phase counts, verification worlds.
- `sase-1bu` epic bead (read via `sase bead read sase-1bu`) — G1 scope, children
  sase-1bu.1–1bu.7 closed, child epic sase-1bu.8 landing-fixes in progress.
- `research:202609/sase_goals_why_not_beads.md` — why goals are not a bead subtype.
- `research:202609/sase_goals_persistence.md` — named→pushed→fetched sync model,
  five pre-freeze gaps.
- `research:202609/xprompt_swarm_goals.md` — one shared draft per clan, lead-only
  claim; G4 behavior; three G2–G4 gaps.
- `research:202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`
  — outcome-vs-process framing, host-bound binding, `builtin@goal` evidence policy.
- `research:202609/sase_goals_memory_end_state/sase_goals_memory_end_state.md`
  (§0–§2) — memory cost (+320 tokens) and per-epic memory rule.
- `plan:202609/goal_ledger.md` + `docs/goals.md` — G1 contract as built.
- Code at HEAD: `src/sase/axe/run_agent_runner_finalize.py:405–480` (notification
  send site), `src/sase/core/agent_clan_*.py`, `src/sase/xprompts/` (no swarm dir;
  swarm = clan + xprompt fan-out).
- Memory decisions `decisions:goal-ledger`, `decisions:goals-host-binds`;
  glossary `goal`.

## 1. What "goals" actually is (the premise correction)

The notification framing understates the program by roughly five epics. Per the
roadmap:

| Epic | What it builds | Verification world |
| --- | --- | --- |
| pre | `JumpToAgent` reveals collapsed rows (small bug) | one TUI test |
| G1 (landed) | Conflict-free event ledger + `live/` markers, manual `sase goal` CLI, `goal:` artifact + `@goal:` citations | Rust tests, two-clone fixtures, 100k-settled benchmark |
| G2 | Deterministic binding: explicit `%goal` → session → plan → clan → parent → bead; resolved in the runner | frozen launch-path matrix (~14 paths) + `sase goal audit` |
| G3 | Claims + verification: fail-open `builtin@goal` after commit, host-gathered evidence, one `GoalVerify` gate per claim | finalizer protocol + gate end-to-end |
| G4 | Every turn has a goal: machine-local drafts, compare-and-swap naming, adoption, swarm-shared draft, answer acknowledgement | matrix + model-judgment metrics |
| G5 | Goals tab + Agents-tab integration | goldens + perf budgets (only epic with golden churn) |
| G6 | Attention cutover: silence success pings, retire ✅ unread, idle hygiene | notification truth table + before/after volume |

G6 — the "better notifications" piece — is 4 phases, the smallest epic. G1 alone
was 7 phases and is already landed (`acfca26db`, `tests/goals` 91 passed per land
notes). The remaining cost is G2–G6, not the whole program. Judging the program by
G6 alone is like judging beads by `sase bead list` formatting.

The decisions make the distinction sharp:

- A goal is a **person-owned durable outcome record** (`goal:<id>`, shown `⌖<id>`);
  Running vs. Idle is derived, never stored (`glossary:goal`).
- **The host binds every LLM turn to exactly one goal before spawn; agents only
  name/adopt/claim; only humans settle** (`decisions:goals-host-binds`).
- State is **immutable events + live markers, O(unsettled) reads, honest
  freshness** (`decisions:goal-ledger`).

Notifications carry none of those invariants.

## 2. The steelman: notification filtering is cheap and partly sufficient

Today's pain really is notification overload, and the cheap fix really is cheap:

- There is **one send site**: `run_agent_runner_finalize.py:469` builds
  `CompletionNotificationPayload(..., silent=agent_hidden, tags=["done"] ...)` and
  `send_completion_payload(payload)`. Silencing a class of agents is a predicate
  at that site.
- A swarm already has the grouping primitive: a **clan** (see
  `src/sase/core/agent_clan_context.py`, `agent_clan_record.py`). The host knows
  which members the lead `%wait`s on. A rule like "contributors are silent; only
  the waited-on owner pings" reproduces the swarm note's headline behavior — one
  ping per 5-agent swarm instead of five — with no ledger, no Rust, no tab, no
  soak.
- The `xprompt_swarm_goals.md` walkthrough itself shows the target UX fits in one
  sentence: researchers write `__<short>.md` and finish `keep_open`; the lead
  claims and you get one signal. A filter gets you 80% of that sentence's
  *audible* shape.
- Cost asymmetry is brutal: one small task vs. ~35 phases across G1–G6, 2.5–4
  weeks including a ≥7-day soak, plus a second lifecycle to maintain, ~+320
  always-loaded memory tokens, and known G1 follow-ups (warm-list p50 ~37 ms vs.
  5 ms contract as `sase-1c3`; phantom-goal / criterion-id / corrupt-event fixes
  in `sase-1bu.8`).

If the team is resource-constrained this week, "silence swarm contributors" is a
legitimate stopgap. The roadmap even lists the adjacent pre-task (JumpToAgent
revealing collapsed rows) as independently valuable.

## 3. Why the cheap fix does not substitute for goals

### 3.1 Identity: a clan is not a citable outcome

- A clan exists at launch on one machine. It has no stable ID, no revision, no
  title/outcome text, no merge/reopen/drop, and nothing to cite. Goals give
  `goal:<id>` + `@goal:<id>` expansion (G1, already built and documented in
  `docs/goals.md`).
- Re-asking "something already in flight" has no answer under filtering: two
  identical swarms ping twice. Under goals the second agent **adopts** with a
  reason (G4), and `sase goal audit` reports zero orphans.
- Plans already carry a `goal:` frontmatter *string*; goals turn that string into
  a record with provenance (submitted unit prompt + root prompt digest).

### 3.2 Verification: a quiet inbox is not a verification inbox

- `JumpToAgent(done)` opens an agent row. A `GoalVerify` gate (G3) carries a claim
  sentence (≤280 chars), 1–3 check-it steps, gaps, `@commit` evidence resolved
  *after* commit by the host, and receipt snapshots — with strength badges and
  provenance checks.
- Filtering keeps today's authority model: agents finish and the row says done.
  Goals invert it: **agents may only claim; humans verify/reject/drop**
  (`why_not_beads` §2.3). Reading or dismissing a notification is explicitly not
  verification; `verify`/`reject`/`drop`/`reopen`/`merge` are human-only verbs
  refused inside agent runs.
- Evidence policy matters (§5 of the outcomes synthesis): answers need transcript
  snapshots, research needs file refs, code needs the host-finalized stitch plus
  receipts. A notification payload has `notes`/`commit_message` strings; it
  cannot enforce "no self-written 'tests passed' as a receipt."

### 3.3 Deduplication and idempotency across retries, pipes, and machines

- One published claim yields **at most one** notification, deduplicated by
  `goal:<id>:claim:<n>` across retries and machines (G3). A per-agent filter
  re-fires per retry, per pipe successor, per gate relaunch, per monitor member —
  unless it re-implements claim identity, at which point it is rebuilding G3
  without the ledger.
- Cross-machine: the clan that launched on athena does not exist on apollo.
  Goals publish `named`/`claimed`/`settled` through the hidden-clone write lane
  with bounded push + outbox + `↑ unpublished` chip and TTL/`--fresh` fetch with
  `synced Ns ago` honesty (persistence note §§1–2). Filtering has no fetch story;
  B simply never sees A's silence decision.

### 3.4 Coverage beyond swarms

Swarms are the minority shape. The roadmap cites ~310 outcomes/week, ~25/day
ad-hoc (mostly questions), and 841/2,048 weekly runs epic-bound. Filtering
"research contributors" helps one fan-out pattern and leaves:

- epic → planner → phases → land (the noisiest shape; G3 deliberately claims here
  first);
- direct questions with no bead/plan/commit (need answer acknowledgement, G4);
- monitors, pipes, retries, dispatch, gate relaunches (need inheritance rules,
  G2–G3);
- standing routines (need standing goals or explicit exemption, G4/G6 decision).

Each would need its own bespoke silence rule. Goals provide one binding ladder
(explicit → session → plan → clan → parent → bead → routine → draft) plus
`audit --since` to prove coverage.

### 3.5 The filter needs the same hard logic goals needs

Role derivation ("an agent another pending agent waits on is a contributor") is
shared. The swarm note's gap §6.1 shows the lead does *not* always claim when
`critique=true`/`image=true` add `%wait` members — an infographic agent could
become the claimer. A notification filter keyed on "lead pings" breaks the same
way a naive G3 would; the fix (name the claimer / bar helpers from claiming) is
G3/G4 work regardless. Filtering saves the store, not the semantics.

Similarly, G2's launch-path matrix (~14 paths: direct, plan, bead, swarm,
`%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe, question,
monitor) must be enumerated either way. Goals freeze that matrix as an acceptance
suite; filters would leave it as tribal knowledge in one `if` statement.

### 3.6 Scale and audience

- Bead reads cost O(history); 6,479 beads, 93% closed. Goals list costs
  O(unsettled) via `live/` markers; settled goals are never opened
  (`why_not_beads` §2.4, G1 benchmark). A notification filter does not fix the
  underlying read scaling for any future "show me open outcomes" surface.
- Beads show scheduled work; Agents shows processes; Plans shows designs; Goals
  would show intent. Stuffing intent into notification routing (or into beads —
  rejected for the same reason) forces every consumer to re-filter. Twenty-five
  answered questions a day do not belong in `sase bead ready` triage, and
  silencing them does not make them findable.

### 3.7 What filtering actually risks

- **Throwaway work.** The roadmap §6 already adjudicates "claims without goals
  (a per-agent flag)": reject as throwaway; G3-on-epics gives the same early
  signal durably.
- **Silent loss.** Today's failure mode is noise. The filter's failure mode is
  silence: a contributor that actually failed, a lead that died unnamed, a
  rejected claim relaunched onto nothing. Goals fail open (`keep_open` + audit
  diagnostic; binding failures leave the turn unbound) and gate G6 on measured
  shadow coverage (≥90%), claim precision (≥80%), zero orphan turns, zero
  finalizer-caused failures. No filter proposal in the prompt includes a start
  gate.
- **Flag debt.** Per-clan/per-swarm silence flags multiply both-state tests. The
  flags memory (cited in roadmap §3) allows at most one beta flag per epic,
  removed before landing. A permanent "who pings" config matrix is exactly the
  kind of umbrella flag the roadmap rejects unless explicitly requested.

## 4. Honest costs and risks of pressing forward

Critique must cut both ways. Goals is expensive and still rough:

- **Size.** ~35 phases across five contracts; large epics here spawn remediation
  children 50–58% of the time and take 3–10× longer (§1.1 of roadmap). The
  sibling-epic split mitigates but does not eliminate this.
- **G1 is landed but not clean.** `sase-1bu.8` is open: edit/drop on unknown IDs
  mints phantom goals, uppercase IDs fork, criterion IDs use `len()` not event
  index, one corrupt event aborts list/show/doctor, `goals-hot.json` corruption
  handling, reopen-keeps-`merged_into`, and the warm-list miss (`sase-1c3`:
  38.7 ms vs. 5 ms at 1,000 unsettled). None is fatal, but G2 should not start on
  a ledger whose repair path is still being fixed — sequence G1-fixes → G2.
- **Two model-judgment risks.** Claim honesty (G3) and name-vs-adopt (G4) cannot
  be proven by unit tests; they need a ≥7-day soak with per-model precision,
  adopt:name ratio, and merge rate. If precision lands <60% on some model, G6
  must not open and a per-model claim policy is needed.
- **Sync is honest, not instant.** Remote freshness is minutes (5-min backstop,
  TTL fetch), not 30 s; the publisher leg for batched progress is new; ledger
  visibility inherits the beads repo's public readability (needs the G1 `local`
  visibility decision). If push contention rises, the answer is splitting the
  `goals` role into its own repo (a config change, per decisions).
- **Second-system permanently.** A new lifecycle, reducer, CLI noun, tab, and the
  eternal "bead or goal?" triage question (answer: schedule→bead, verify→goal).
  Plus ~+320 always-loaded tokens and ~12 existing memory notes/strands to fix
  as each epic lands (memory end-state note).

None of these is an argument for filtering instead; they are arguments for
*sequencing and gating* goals, not for abandoning it.

## 5. Decision framework

| Signal | Meaning | Action |
| --- | --- | --- |
| Most goals map 1:1 to epics; answer/ad-hoc goals rare | Goal ≈ epic+review; bead extension might have been cheaper (`why_not_beads` §5) | Revisit only if measured post-G3; do not pre-reject on hypothesis |
| Bead store gains unsettled-only hot path for its own reasons | §2.4 objection weakens | Still blocked by authority/lifecycle (§§2.1–2.3); keep separate |
| Claim precision <60% on some model | Model judgment not ready | Per-model `keep_open` policy; hold G4 exposure and G6 |
| Shadow coverage <90% at soak end | Success pings still carry unique signal | Fix Idle/role derivation; run goals noisily (G1–G5 work without G6) |
| Push contention / hot-list p95 grows with settled history | Ledger contract stressed | Split repo (config); fix projection short-circuit (`sase-1c3`) |
| G2 matrix fails structurally on some path | Runner binding insufficient | Bind that path on the unit wire inside G2 (no new epic) |

## 6. Recommendation

**Press forward with goals, but as the roadmap's gated sequence — not as a
notification project — and ship a narrow notification stopgap in parallel.**

1. **Do the cheap stopgap now (one small task, not an epic).** File the
   `JumpToAgent`-reveals-collapsed-rows bug and, alongside it, silence
   non-owner clan members' success pings (owner = the member no pending member
   waits on; carve out `critique`/`image` helpers per gap §6.1). This is
   explicitly *not* goals; mark it as such so it is not mistaken for G6.
2. **Close out G1 properly.** Land `sase-1bu.8` (phantom-goal, criterion-ID,
   corrupt-event, projection-header fixes) before G2 binds agents to the ledger.
3. **Write only the G1-successor plan next: G2 deterministic binding.** No
   drafts, no model judgment. Acceptance is the frozen launch-path matrix +
   `sase goal audit`. This already makes `sase goal list` the inventory of every
   approved epic in flight — value before any notification changes.
4. **Then G3 claims on epics + explicit `%goal` only.** Keep success pings on.
   Verify through one `GoalVerify` per land with `@commit` + receipt evidence;
   measure claim precision per model and shadow coverage while loud.
5. **Defer the universal invariant (G4 drafts) until G3 numbers clear.** Claims on
   known-identity goals first (41% of volume, the noisiest shape), drafts second.
   If planning exceeds 7 phases, push standing goals to G6 per the roadmap's
   overflow rule.
6. **Run G5 (tab) parallel with G4 once G3's claim payload is frozen; gate G6 on
   the soak table** (≥7 days, ≥100 settled claims, ≥90% shadow, ≥80% precision,
   0 orphans, 0 finalizer-caused failures). If the gate never opens, goals still
   work — just noisier. That is the correct failure mode, and filtering cannot
   offer it.
7. **Do not build per-swarm/per-clan notification customization as the
   alternative.** It duplicates role derivation, launch-path enumeration, and
   claim identity without producing a citable, verifiable, cross-machine record,
   and it becomes throwaway the moment G3 lands.

In one line: **filtering makes noise quieter; goals make outcomes checkable.
Take the quiet as a stopgap, but build the checkable.**
