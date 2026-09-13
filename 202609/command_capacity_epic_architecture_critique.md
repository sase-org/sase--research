# Architecture critique of the sase-zm epic (command capacity reservations and fleet load meters)

Research date: 2026-09-13, performed on kellys_mbp from sase workspace #10. Requested
scope: a high-level architecture/design critique of the `sase-zm` epic — explicitly
*not* a re-derivation of the `just` command weight tables.

Sources reviewed (all through audited reads): the full plan
`plan:202609/command_capacity.md`; `sase bead show` for `sase-zm`, its phase dependency
edges, `sase-z4`, and `sase-zl`; decision records `two-speed-verification`,
`single-turn-agents`, `host-owned-completion`, and (by reference)
`gates-never-block` and `rust-core-required`; and the prior adversarial review
`research:202609/command_capacity_epic_critique.md` (2026-09-12, athena).

**Relationship to the prior critique.** That report is a code-level, measured review;
this one is an independent architecture pass. Where my conclusions converged with its
findings I say so and cite its finding IDs rather than restating its evidence. The
distinct contributions here are: the fail-closed-availability trade on the developer
inner loop (§C3), the contract-by-prose problem (§C6), the `max_running_agents`
semantic-shift landmine (§C7), and a sharper statement of the epic-splitting argument
(§C1). The convergent findings (§C2, §C4, §C5) should be read as independent
corroboration — two reviews reached them from different directions.

---

## Verdict

The problem is real and the core accounting model is right: today an agent-count limit
and a pytest token pool are two independent budgets on the same machine, so nothing
stops N admitted agents from each launching a full check and oversubscribing the host.
Unifying agents, tool commands, and pytest workers under one machine-local ledger, with
Rust owning admission policy and hosts owning process supervision, is the correct
consolidation and matches every standing decision record (`rust-core-required`,
`single-turn-agents`, `gates-never-block`, `host-owned-completion`,
`two-speed-verification`).

The risk is not the model — it is the delivery shape. The epic bundles a
distributed-systems migration (a new authoritative ledger with a drain-based cutover),
a CLI product surface, a repo-tooling enforcement sweep, a config/onboarding change
across three machines via chezmoi, and a TUI feature with pixel-level acceptance into
one 14-phase unit built on **two prerequisite epics that are still in flight**
(`sase-z4`, `sase-zl`, both `IN_PROGRESS` as of this review). Most of what follows is
some form of "decouple these so each part can be proven, landed, and rolled back on its
own terms."

---

## What the design gets right

- **One ledger instead of two budgets.** Eliminating the independent agent-slot and
  pytest-pool accounting is the whole point, and the plan holds that line everywhere —
  including refusing a second scheduler on managed hosts and confining the legacy pool
  to genuinely isolated CI.
- **Layering.** Rust core owns validation, aggregation, ownership, fairness, and
  profile decisions; host adapters own process identity, locking, and durable writes;
  repo tooling collects evidence; Textual renders. This is exactly the
  `rust-core-backend-boundary` litmus test applied correctly.
- **Refusal as executable choices.** Exit 75 plus printed `queue`/`force`/`resume`
  commands — never a blocking prompt, never an in-place wait — is the right adaptation
  to `single-turn-agents` and `gates-never-block`. The `-r/--resume` design (validate
  owner/cwd/argv/fingerprint, reserve resumption atomically) is careful.
- **Capacity as declared policy, not measured utilization.** Saying plainly that a
  unit is reserved demand, that values come from the user, and that this is not a
  resource jail is honest scoping — though see §C2 for the cost of that honesty.
- **Independent per-machine denominators** with an explicit prohibition on a combined
  "44" meter. Correct, and easy to have gotten wrong.
- **Supervision rigor.** Boot identity, process-birth identity, no age-only expiry for
  a living holder, and treating flock as insufficient proof of child death are the
  right instincts (but see the prior critique's R5 for why flock should still be kept
  as the anti-leak floor — I agree with that finding).

---

## Concerns

### C1. One epic is carrying what should be three, on foundations that are still moving

The phase graph is honest about its coupling: the critical path runs
baseline → contracts → leases → fair-queue → monitors → cli → profiles →
pytest-admission → recipe-admission → guidance → acceptance, roughly eleven deep, and
`contracts` and `monitors` are correctly gated on `sase-z4` and `sase-zl` — both of
which are still `IN_PROGRESS` (the prior critique's S1 documents nested remediation
epics under both). Meanwhile the plan itself concedes drift risk: "Parent acceptance is
still in progress at authoring; old failure notes are not fresh reproductions," and an
entire paragraph of rebase/revalidate instructions exists because the foundations are
expected to shift underneath.

Three deliverables inside this epic have genuinely different risk profiles and
rollback semantics, and none of them needs the others to be *in the same epic*:

1. **The mechanism** (reservation model, leases, fair queue, tool command, profiles) —
   library-plus-CLI work, testable with fixtures, machine-local, no operational risk
   until activated.
2. **The enforcement and cutover** (recipe/pytest admission, version barrier, drain,
   per-machine activation) — an operational migration whose failure mode is "nobody
   can run tests." This is the risky part and deserves its own epic with its own
   rollout evidence.
3. **The observability** (capacity snapshot object, fleet capsules, meters) — a
   read-only feature consuming a versioned published contract. It could land *first*,
   against the existing weighted-load data, and would make every later pricing and
   activation decision evidence-based instead of speculative. The prior critique's S1
   reaches the same conclusion; I'd state it more strongly: shipping the meter before
   the ledger is not just de-risking, it is the natural order.

The epic's own text almost admits this split: the meters phase consumes "a versioned
capacity object per machine through the existing Rust fleet worker summary path" — a
contract that could be frozen and built against fixtures today. Bundling pixel-level
PNG acceptance (14 scene matrix, three widths, two themes) into the same unit as a
distributed cutover means the epic's completion is hostage to its least risky and its
most risky parts simultaneously. S2 of the prior critique makes the related point that
`acceptance` as scoped cannot close while apollo or the Mac is offline.

**Change:** split into mechanism / enforcement-and-cutover / observability epics, land
observability first, and let the enforcement epic carry the activation evidence.

### C2. One scalar unit is asked to mean four different things, and the dimension that actually kills athena is unmodeled

A capacity unit prices: an agent's presence (base 1, LLM-bound, near-zero CPU), a
pytest worker (a core plus substantial memory), compiler fan-out (cargo/uv jobs), and
arbitrary user-declared demand (`-w 2.5`). The plan says explicitly that a unit has no
fixed physical meaning and that tuning happens later from evidence — but admission
decisions are made *now*, from the scalar alone, while "additional CPU and
available-memory checks may reduce concurrency" *after* admission. That sentence is
the tell: memory is a real admission dimension the ledger does not model, demoted to a
post-admission adjustment. The prior critique measured the consequence on athena (R1:
the system being replaced is currently self-throttling to a budget of 2 because the
machine is in swap; R2–R3 price the memory commitment nobody has priced) — I
independently flag the same architectural gap without the measurements: **a scalar
admission ledger on a memory-constrained host will confidently admit work the host
cannot run.**

Ruling out a "general multidimensional scheduler" is a defensible v1 boundary. What
the plan is missing is the *failure story* for when the scalar mispredicts: who
notices, what the meter shows, and what mechanically backs off. A
`min(persistent_capacity, health_derived_ceiling)` effective denominator with
`health` as a capacity source (prior critique R1's recommendation) is the smallest
honest answer, and the plan already has the persistent/effective/override/source
machinery to express it.

**Change:** either model a health-derived effective ceiling, or state in the plan that
scalar mispricing is accepted and name the observable signal and the operator playbook
for it. Silence is the only wrong option.

### C3. Fail-closed accounting is priced above availability of the developer inner loop, with no break-glass

This one is not in the prior critique. Trace the availability posture through the
plan: force "cannot bypass … an unavailable ledger"; "a bare environment bypass is
never sufficient to disable the ledger"; after activation, malformed or missing
capacity "refuses new capacity admissions, **including forced ones**"; and every
supported entry point — `just`, `tools/run_pytest`, bare `pytest` via conftest — must
obtain a ledger grant on a managed host. Compose those: **if the ledger is wedged,
corrupt, or half-migrated, no human and no agent can run any test or expensive recipe
on that machine, and the designed escape hatch (force) is defined to not work.**

The epic moves `just check` — the single most-executed command in the development
loop, per `two-speed-verification` the thing every agent runs by default — behind a
distributed-protocol boundary with version negotiation, durable state, and a
reconciler. A bug in admission no longer breaks scheduling fairness; it breaks the
ability to verify code at all. Accounting integrity is worth a great deal here, but it
is not worth that.

The plan closes the accidental bypasses (correctly — an env var must not silently
disable accounting) but never provides a *deliberate* one. Those are different things.
A break-glass path can be loud, audited, rate-limited, and ugly: an explicit
`sase tool run --unaccounted` requiring an interactive confirmation or a host
operator flag, recorded with force-style provenance, showing on the meter as
uncounted load. What matters architecturally is that its existence is designed, so
that the first wedged-ledger incident produces an audited override instead of an
engineer discovering which file to delete — because that discovered workaround, not
the designed one, is what actually erodes the ledger's authority.

**Change:** specify a designed, audited break-glass for ledger unavailability, and add
"ledger daemon wedged/corrupt" to the acceptance matrix with a required recovery time.

### C4. There is no shadow stage between dormant library code and a drain-based cutover

The rollout jumps from "earlier landed phases must be dormant library code" directly
to a machine-local barrier: pause launches, drain legacy holders, prove nothing can
acquire the old budget, activate. The plan asserts a long list of delicate invariants
(compensated summation, ULP comparison bounds, PID-reuse defense, lease
reconciliation, no leaks across reboot) whose real-world validation *only begins at
activation* — on the busiest machine, behind a quiesce that the prior critique's S3
argues may never converge given continuous epic-worker launches.

A shadow mode is the standard answer and it is conspicuously absent: run the ledger
observe-only alongside the legacy pool for a period, record what it *would* have
admitted and refused, compare its load accounting against the legacy pool's and
against host reality, and alert on divergence. That converts the scariest step of the
epic from a leap into a verification, produces exactly the calibration evidence the
profiles phase says it wants ("collect warm/cold … samples", "tune from fresh
evidence"), and pairs naturally with the prior critique's dual-write proposal (S3),
which I endorse as the cutover mechanism itself.

**Change:** insert a shadow/observe-only stage as a named phase deliverable with
divergence criteria that gate activation.

### C5. The fair-queue's total-protection rule designs in a machine-wide launch freeze

After 120 seconds, the oldest aged request is protected "from all newer competing
admissions, including new agents, until its frozen target fits," and running work is
never preempted. On a machine where agents run for hours holding base claims, a
protected 15-unit request means every unit freed is hoarded and no agent launches —
an unbounded, by-design freeze whose acceptance test only verifies that it *happens*
(prior critique R4 develops this fully; R3's reserved verification floor largely
dissolves the need for it). I reached the same conclusion independently, with one
addition at the policy level: **both the 120-second threshold and the
total-protection semantics are hard-coded policy constants baked into acceptance
tests.** Queue policy of this kind is never right on the first guess; encoding the
first guess in the test suite makes every future tuning iteration a contract change.

**Change:** adopt a reserved heavy-work floor as the primary anti-starvation
mechanism, demote aging protection to a bounded backstop, and make both the threshold
and the protection mode versioned policy configuration with status/telemetry, not
constants.

### C6. The inter-phase contract is 600 lines of binding prose

"Each phase description above is its scope; the shared contracts in this body are
binding." That makes a ~48 KB document the interface definition among 14 workers plus
a land agent, across four repositories, over a multi-week horizon during which both
prerequisite epics will change what "the accepted revision" means. Two failure modes
follow: workers resolving the same ambiguous sentence differently (the plan's own
symbol-level slip — `ProviderInfoPanel`, prior critique R14 — shows prose drifts from
the tree even at authoring time), and the plan aging into exactly the kind of stale
design doc the project's own decisions web warns about.

The stable, load-bearing agreements in this epic are enumerable and small: the
reservation record schema, the capacity snapshot schema, the exit-code and typed-record
contract, the CLI grammar, and the state table for capacity held per executing state.
Those belong in versioned fixture/schema artifacts that `baseline` creates and every
phase tests against — the plan already gestures at this ("immutable
accounting/selection fixtures") but stops short of making the contracts themselves
machine-checkable.

**Change:** have `baseline` extract the five contracts above into schema/fixture files
that phases import in tests, so cross-phase agreement is enforced by CI rather than by
14 readings of the same prose.

### C7. Reusing `max_running_agents` while changing what it means is a permanent landmine

The key stays, the UI says "Machine capacity," and the *semantics* silently shift from
"how many agents may run" to "abstract weight units shared by agents, tools, compilers
and test workers" — where a full check costs 15 of them. The plan's justification is
avoiding "an unrelated key rename," but the rename is not unrelated: the meaning is
the thing changing. Everyone who reads a config file, a diff, or an old runbook now
does a mental translation forever; every future config-related bug report starts with
disambiguating which meaning the reporter assumed. The plan already forces an explicit
per-machine re-initialization (source-aware validation rejects inherited defaults) —
that is precisely the moment a one-time key migration (`machine_capacity`, with the
old key read-and-warned) would cost nearly nothing extra.

**Change:** rename the key during the forced re-initialization, with a
read-old/write-new compatibility window, instead of aliasing forever.

### C8. Smaller notes

- **CLI semantics wrinkles.** The minimum-one rule applies to built-in zero-extra
  profiles but not to explicit fractional weights, so `-w 0.25` in a monitor is
  *cheaper* than a "free" built-in serial profile (0.25 vs 1). That inversion invites
  gaming and confusion; a uniform floor for any live holder would be simpler. This
  compounds the prior critique's R10 (three meanings of "weight" across the surface)
  and R7 (`-q` always hands off even when the command fits, burning a provider turn
  for no accounting benefit — I independently flag the same and endorse its
  "inline-if-fits, handoff-if-not" default).
- **Workspaces are a second, unmodeled resource.** Parked monitors hold zero capacity
  but retain multi-GB workspace tenure; the meter can read idle while the machine
  cannot start work. Prior critique R6 covers this well; architecturally it is the
  same class of gap as §C2 — a real constraint outside the scalar.
- **The v1 fixed-peak-envelope rule** (reserve the whole peak for the child lifetime,
  no hold-and-wait upgrades) trades utilization for deadlock-freedom. That is the
  right v1 trade and the plan says so; no change requested — just don't let later
  tuning reintroduce in-place upgrades casually.
- **The plan over-specifies presentation** (amber at exactly 75%, eight-cell bars,
  capsule text) inside a document that is otherwise a contract. The meters phase
  should own visual specifics against the data contract; binding them in the epic body
  inflates the acceptance matrix and guarantees the plan's prose diverges from the
  shipped UI. Prior critique R12 shows the specimen already fails its own width
  budget.

---

## If you change only three things

1. **Split the epic** (§C1): mechanism, enforcement-and-cutover, and observability as
   separate epics, observability first. Everything else gets easier — including
   waiting out `sase-z4`/`sase-zl` without holding 14 phases hostage.
2. **Add the shadow stage** (§C4) and pair it with a dual-write cutover instead of a
   full drain. The activation step is the epic's concentrated risk; this is the
   cheapest way to spend it down.
3. **Design the break-glass** (§C3). A capacity ledger that can take `just check`
   hostage on a wedged daemon will lose its authority the first time that happens;
   an audited override is how it keeps it.

The underlying idea — one honest, machine-local, Rust-owned admission ledger with the
load made visible — is sound and worth building. The critique is entirely about
sequencing, blast radius, and the handful of places where the plan chooses accounting
purity over operability.
