# Waiting on remote agents (`%wait` × `%dispatch`): research and recommendation

**Researcher:** mus · **Date:** 2026-11-07 · **Swarm:** 5-researcher swarm (independent report)

**Request under study:** let a prompt launched on one machine (e.g. apollo) wait for a
sase agent running on an enrolled remote machine (e.g. athena), something like
`%wait:athena.foobar` in a prompt that launches locally, where athena was configured
via `sase machine init`.

## Summary of findings

1. The building blocks for remote *visibility* already exist (fleet catalog, federation
   worker, remote rows in the Agents tab), but remote *waiting* does not: every wait
   evaluation path today reads only local artifact state.
2. The `%wait:athena.foobar` spelling as literally proposed should not be adopted: the
   dot is already overloaded (clan members, dotted agent names, dotted machine
   aliases), and the colon form cannot carry the extra fields a remote wait needs.
3. A remote wait is implementable at moderate cost by treating the remote side as a
   second snapshot source behind the existing `WaitDependencyIndex` / poll-loop seams,
   reusing the federation read path the TUI already uses. No gateway protocol change
   is strictly required for a V1.
4. The bigger risk is semantic, not plumbing: remote state is eventually consistent
   (cached fleet feeds with "stale" markers), remotely-named agents can be retried,
   renamed, or reaped out of the recent-terminal window, and the owner machine is the
   authority on outcomes. A remote wait must therefore pin identity (including the
   target installation) at bind time and define fail-open vs. fail-closed behavior
   for unreachable machines up front.
5. My recommendation: ship a narrow V1 — `%wait(agent, machine=<alias>)` for the
   session/turn cases only, evaluated by the existing poll loop against the federation
   catalog with explicit stale-feed and unreachable-host semantics — and keep the V1
   `%dispatch`+`%wait` combination ban in place. Details in §7.

## 1. How remote machines work today

Enrollment and transport (per `docs/reference/integrations/remote-dispatch.md` and the
dispatch memory note):

- Each machine that serves agents runs a loopback `sase_gateway` supervised by the
  service host, exposed inside the tailnet via Tailscale Serve (HTTPS, private tailnet
  only — no Funnel).
- The controller enrolls with `sase machine init -B <bootstrap.json>` (canonical path;
  `add`/`repair` are the lower-level variants). The bundle is a single-use secret with
  a short TTL; steady-state auth uses a credential stored in the controller's
  protected SASE state. This confirms the request's assumption: yes, `sase machine
  init` is the configuration step.
- Steady-state reads go controller → local `sase_federation_worker` subprocess →
  HTTPS to the target gateway. The Python `FleetGatewayClient`
  (`src/sase/dispatch/fleet_client.py`) only implements `enroll` and `hello`; all
  fleet data reads (`summary`, `catalog`, `catalog_hosts`, `followed_batch`,
  `detail`, `content_range`) go through the federation facade
  (`src/sase/dispatch/federation/_facade.py`) backed by the worker. Fleet protocol
  versions in play: wire schema v2, supported protocol versions {2, 3}
  (`src/sase/dispatch/models.py`).

What the controller can already see about remote agents:

- The Agents tab merges remote rows into the same session/clan nodes the owner
  reports, with host-alias chips, `machine:<alias>` filtering, and by-machine
  grouping. Remote rows carry authored capacity/weight badges but never join the
  controller's `load:` gauge.
- Crucially, remote state arrives as a **bounded, cached feed**: the owner's recent
  window (7 days, ≤200 completed rows), with explicit `feed invalid` / `stale ·
  cached Xm ago` / `last seen … ago` markers, and per-host failure diagnostics that
  stay visible rather than hiding hosts. There is no long-poll, subscription, or
  gateway-side "notify me when agent X settles" operation anywhere in the fleet API
  surface I surveyed.

## 2. How local waits work today (the machinery a remote wait must plug into)

Three cooperating layers, all local-artifact based:

1. **Directive parsing.** `%wait` accepts positional agent names plus `bead=`,
   `hood=`, `time=`, `target=session|turn`, `for_epic=`, `proc=`, `unit=` keywords
   (`docs/reference/macros/directive-launch.md`, `src/sase/macro/_directive_values.py`).
   Notably, `%dispatch` and `%wait`/`%queue`/`%clan`/`%hold` in the *same* prompt are
   rejected at scan time: `"%dispatch cannot be combined with %wait, %queue, %clan,
   or %hold in V1 remote launch"` (`src/sase/macro/_directive_scan.py`). Rationale in
   the docs: the controller strips only the dispatch selector and the *target*
   executes the remaining directives, so a controller-side wait would be meaningless
   (or worse, silently evaluated against the wrong machine's artifacts) on the
   target. This ban concerns a *dispatched launch that itself waits* — the inverse of
   the request (a *local launch waiting on remote work*) — but it shows the codebase
   already treats "which machine's state does this wait read?" as a correctness
   question, which is exactly the right instinct.
2. **Bind-time pinning.** At launch, `bind_wait_target`
   (`src/sase/agent/wait_target_binding.py`) classifies each reference (agent, clan,
   session, workflow, `@tribe`) and pins it to a v2 identity record (artifact dir,
   timestamp, turn name). Later evaluation never re-resolves the name: retries,
   renames, and successor turns are handled deliberately (e.g. retry-chain
   following, the `--mon`/`--gate` newest-member rule).
3. **Release evaluation.** Two paths share the semantics: the AXE `wait_checks`
   lumberjack chop plus a runner-side fallback (`src/sase/axe/run_agent_wait_deps.py`,
   built so "a chop outage cannot strand a waiting agent forever"), resolving a
   `WaitDependencyIndex` built from local artifact dirs (`wait_for_artifacts`,
   `wait_for_beads`, `wait_for_hoods`, `wait_for_epics_of`, time floors). A separate
   interactive path, `sase agent wait` (`src/sase/agents/cli_wait.py`), polls
   `scan_agent_artifacts` snapshots through the generic engine
   (`watch_wait_targets` in `src/sase/agent/wait_watch/_watch.py`, adaptive
   1s/2s/5s cadence) and classifies records by `done.json` outcome. Named waits
   release only on `"completed"`; anything else parks the waiter and (for the AXE
   path) posts one deduplicated `wait_checks` notification naming waiter and
   blocker.

So a remote wait is not a parser-only feature. It needs a value for every one of
these layers: name it, pin it, and re-evaluate it — against state that lives on
another machine.

## 3. Critique of the plan as stated

**The goal is sound.** Cross-machine fan-in ("build on athena, integrate on apollo")
is the obvious missing primitive once remote launch and remote visibility exist, and
users will otherwise reimplement it with sleep-loops over `sase machine agent` /
fleet polling, which is worse in every way (no bind pinning, no AXE stranded-waiter
diagnostics, no TUI affordance). Doing it as a first-class wait also composes with
everything waits already compose with: `%queue` admission ordering, `time=` floors,
the Wait modal, `sase agent wait` scripting.

**But the proposed spelling `%wait:athena.foobar` has three concrete problems:**

1. **The dot is ambiguous three ways.** Dots already separate clan members
   (`<clan>.<member>` hood scoping), appear inside agent names and name templates,
   and are legal *inside machine aliases themselves* (`validate_machine_alias`
   allows letters, digits, `.`, `_`, `-`). `athena.foobar` could be agent `foobar`
   on machine `athena`, member `foobar` of clan `athena`, or a local agent on a
   machine aliased `athena.foobar`. A bare-name syntax cannot be disambiguated
   without an alias-registry lookup at parse time, and parse time is the wrong
   layer to consult enrollment state.
2. **The colon form cannot grow.** A remote wait needs at minimum machine + agent,
   and plausibly `target=turn` (pin remote turn vs. whole remote session), timeout
   behavior, and unreachable-host policy. Parenthesized keywords already exist for
   exactly this (`%wait(planner, target=session)`), while `%wait:<name>` is the
   single-value shorthand. The remote form belongs in the parenthesized grammar.
3. **It conflates two directions.** `%wait:athena.foobar` on a prompt *also*
   carrying `%dispatch:athena` would parse as "launch remotely and wait remotely,"
   which is precisely the currently-banned combination. Whatever syntax is chosen
   must keep "wait *on* machine M" and "launch *on* machine M" visibly distinct so
   the V1 ban stays enforceable and its eventual lifting stays expressible.

**A further scope warning:** the request says "wait for a sase agent named `foobar`
… to complete," but local `%wait` is far richer than agent completion (sessions,
clans, `@tribe` next-entity semantics, beads, hoods, epic-follow, turn-pinning).
Each of those needs a remote analogue decision — and several have no sane remote
meaning in V1 (remote `hood=` would snapshot membership across a stale feed;
remote `bead=` would read the *controller's* bead store while naming remote work;
`for_epic=true` would chase epics launched on another machine). The requirements
should explicitly defer those, or the feature will accrete half-defined semantics.

## 4. Design options considered

### Option A — Controller-side poll of the fleet feed (recommended for V1)

The waiter (parked local agent, or `sase agent wait` process) polls the *existing*
federation read path (`catalog_hosts`/`detail` via the local worker) for the pinned
remote identity, on the existing adaptive cadence, and applies the existing
outcome-classification table to the remote row's outcome. No gateway protocol
change; no target-side code. This mirrors how the TUI already renders remote rows,
so the semantics users see while waiting match the semantics they see in the list.

- Pros: smallest blast radius; Python-only; reuses auth, caching, diagnostics, and
  the staleness markers; works for both `%wait` (parked agent) and `sase agent
  wait` (scripting) through the shared poll engine.
- Cons: poll latency stacked on feed-cache latency (see §5); the controller pays one
  poller per remote wait.

### Option B — Gateway-side wait RPC (long-poll / "wait-for-settle")

Add a fleet endpoint where the controller registers interest in an agent identity
and the target gateway replies when it settles (or on timeout). 

- Pros: prompt wakeups, fewer round trips, natural place to enforce authz per wait.
- Cons: requires a fleet protocol bump, gateway state (wait registrations across
  gateway restarts — recall enrollments must already "survive a gateway process
  restart," so this is a known-hard area), worker support, and a fallback anyway
  for old gateways (fleet v2 targets are in the wild; the codebase already
  special-cases version skew). This is the right *eventual* design for scale, but
  it multiplies the V1's version-matrix and restart-recovery testing. Defer.

### Option C — Target-side waiter proxy

Compile the wait into a tiny agent (or proc unit) launched *on athena* via the
existing dispatch path, which does a local wait there and then signals apollo
(notification inbox, `machine attention`, or simply completing so the controller's
poll of one row succeeds).

- Pros: reuses 100% of local wait semantics including epic-follow and turn
  pinning; no controller poll loop.
- Cons: consumes a runner slot on the target for the waiter's whole lifetime;
  inverts failure domains (a stuck proxy looks like stuck work); needs a
  signaling path back that does not currently exist in reliable form; and it
  clashes with the V1 `%dispatch`+`%wait` ban — you would be lifting that ban
  through the back door while claiming to keep it. Reject for V1; possibly revisit
  as the implementation *behind* Option A's syntax much later.

### Option D — Event/inbox-driven wake (no polling at all)

The controller subscribes to the target's completion events (agents-sync
publication, notification inbox reconciliation — the same channel that already
reconciles "pending remote questions and gates … rather than inferred from
row-follow state").

- Pros: no polling; consistent with the attention-reconciliation precedent.
- Cons: that channel is built for human-attention items with per-revision
  dedup semantics, not for agent-lifecycle completeness; completion publication
  is about *publishing pages*, with repair/replay machinery (`publication_repair`,
  backfill timeouts noted in recent research) that makes "did agent X succeed?"
  a harder query than it looks. The feed-based read path is the one the TUI
  already trusts for liveness; the inbox path is not. Reject for V1.

## 5. Hard problems any option must solve (requirements adjustments)

These are the adjustments to the requirements I would insist on; each is a place
where "just make `%wait` accept a remote name" silently under-specifies behavior:

1. **Syntax: keyword, not dot.** Adopt `%wait(foobar, machine=athena)` (agent
   positional, machine as keyword — mirroring the `sase machine agent stop ALIAS
   AGENT` two-argument precedent, machine second). Reserve `machine=` for the
   parenthesized form; reject `machine=` on bare/colon `%wait` with a migration-style
   diagnostic. Explicitly reject dotted `machine.agent` shorthands in the error
   text so users learn the keyword form. `local` stays reserved (omit `machine=`
   for local).
2. **Bind-time pinning must include the target installation.** Local waits pin
   artifact dir + turn; remote waits must additionally pin the machine's
   *installation ID* (already carried in `MachineRecord.pinned_installation_id`),
   so a later `machine repair` rotation or alias rename cannot silently rebind a
   parked waiter to a different machine's same-named agent. Unknown machine alias
   or quarantined machine at bind time is a launch error, not a parked wait —
   fail fast, consistent with `_target_machine` in `launch_preview.py`.
3. **Poll the feed; honor its staleness contract.** The federation catalog is
   cached. A remote wait must define: (a) maximum acceptable feed age while
   waiting (suggest: warn past the TUI's stale threshold, refuse to *release* on
   data older than N minutes — never release a waiter on a stale "completed");
   (b) outcome mapping for `feed invalid` and host-down (park, do not fail: a
   network blip must not kill a multi-hour pipeline — but see 4); (c) the recent
   terminal window edge — a remote agent that settles and ages out of the owner's
   served window must still release the waiter, so bind must capture enough
   identity (and the poller must treat "known-settled earlier" as latched, or
   query `detail`/receipt rather than the bounded list).
4. **Unreachable-host policy with a timeout.** Parking forever on a dead machine
   replays the exact failure mode the runner fallback was built to prevent
   ("cannot strand a waiting agent forever"). Require either an explicit
   `time=`-style ceiling on every remote wait or a configured default
   (suggest: remote waits default to the hold TTL convention thinking — bounded,
   e.g. 2h default, 12h cap — rather than inventing a new constant family), with
   the `wait_checks` notification naming the unreachable host, last-seen time,
   and the recovery command. `sase agent wait` already has `-t/--timeout` with
   exit code 4; the directive form needs the equivalent.
5. **Outcome equality with local waits.** Release only on the owner's recorded
   `completed` outcome (the same `done.json`-derived value the feed serves);
   failed/killed/crashed remote agents park the waiter exactly like local ones,
   with the `wait_checks` "can never self-resolve" diagnostic extended to name
   `machine:agent`. Turn-vs-session pinning (`target=turn`) should work remotely
   in V1 since it is just pinning a member name — but `for_epic=true`,
   `bead=`, `hood=`, `@tribe`, `proc=`, `unit=` with `machine=` are V1 errors.
   Bead scoping deserves emphasis: `%wait` beads resolve in the *waiter's*
   project store, so allowing `bead=` alongside `machine=` would silently mix
   machines. Ban the combination explicitly.
6. **Keep the `%dispatch`+`%wait` ban; say what lifts it.** A prompt with both
   `%dispatch:M` and `%wait(X, machine=N)` (N ≠ M, or even N = M) must remain an
   error in V1: the target executes remaining directives against *its* artifacts,
   and a machine-qualified wait evaluated on the wrong controller would be a
   correctness hole, not a feature. The ban lifts only when waits carry an
   explicit evaluation-site rule (e.g. "machine-qualified waits always evaluate
   on the controller") with a test proving the target ignores rather than
   reinterprets them. Relatedly, `%wait(X, machine=N)` inside a *typed launch
   plan* (`%if`/`%proc` plans, LaunchApproval) needs the same coordinator
   treatment `target=` already gets (stays in the unit's prompt; binds at
   dispatch) — or an explicit V1 rejection.
7. **CLI parity from day one.** `sase agent wait` needs `--machine/-M ALIAS`
   (mirroring `--project` scoping, and the `sase machine agent` ALIAS-first
   convention), resolving names against the remote feed with the same pinning
   and timeout semantics. Without it, the feature is untestable in scripts and
   the monitor use-case (`sase monitor start … -- sase agent wait -a`) cannot
   span machines. Also extend the Wait modal and `wait_spec_label` so a remote
   wait renders as `waiting for athena:foobar`-style text rather than a bare
   name that looks local.
8. **Capacity and hold interactions.** A waiter parked on a remote agent holds a
   local runner slot (or not?) — decide and document. The conservative V1 choice:
   identical to local waits (no special-casing in `%queue`/admission or `%hold`
   matching; a hold on the waiter works, a hold *by* remote name does not).
   Also: remote load must not leak into the controller `load:` gauge, consistent
   with the existing "remote load never joins" rule — pollers are not runners,
   so count them nowhere.

## 6. Is this a good idea? Would I take a different approach?

Yes, with the scoping above: cross-machine wait is the natural third leg after
remote launch and remote visibility, and Option A delivers it without protocol
work. The main thing I would do differently from the request is **not** frame it
as "allow `%wait:athena.foobar`" (a syntax extension) but as "teach wait
evaluation about a second snapshot source" (an evaluation-semantics extension
with syntax following). That framing forces the staleness, pinning, timeout, and
ban-interaction decisions that the syntax framing hides — and it yields the test
plan directly: bind-pinning tests, stale-feed refusal tests, host-down parking
tests, window-age-out latching tests, and ban-interaction tests, most of which
can run against a fake federation facade without any gateway.

One deliberate non-goal worth stating: bidirectional rendezvous (apollo waits on
athena *while* athena waits on apollo) will deadlock exactly as it does locally
today; the existing cycle diagnostics (`wait_checks`, blocked-follow `↪`
annotations) should cover machine-qualified names, but nobody should promise
distributed deadlock *detection*. Document "don't do that" alongside the V1.

## 7. Recommended solution (V1)

1. **Syntax:** `%wait(<agent>, machine=<alias>[, target=session|turn][,
   for_epic=false])` only. Everything else combined with `machine=` is a
   directive error with a named diagnostic (`wait-machine-<case>` family,
   following the existing `wait-target-*` / `wait-for-epic-*` convention).
2. **Binding:** at launch, resolve the alias via the dispatch config; error on
   unknown/quarantined; pin `{installation_id, agent/session/turn identity,
   project}` into the waiter's marker next to `wait_for_artifacts` (new
   `wait_for_remote_agents` list — do not overload the local identity records,
   so old readers ignore rather than misinterpret them).
3. **Evaluation:** controller-side poll through `catalog_hosts`/`detail` on the
   existing adaptive cadence; release only on owner-recorded `completed` from a
   fresh (non-stale) feed; latch settlement so window age-out cannot re-park;
   park (don't fail) on host-down/feed-invalid with `wait_checks` diagnostics
   carrying last-seen timestamps; require a bounded default TTL.
4. **Surfaces:** `sase agent wait --machine`, Wait-modal/TUI label support,
   `sase doctor -D -C dispatch`-adjacent diagnostics for "remote wait
   unsatisfiable" (unknown alias at parse, unreachable host at runtime), and
   docs in `remote-dispatch.md` + `directive-launch.md` plus the `dispatch.md`
   memory note.
5. **Explicitly deferred:** gateway wait RPC (Option B — revisit when poll
   volume or latency actually hurts), target-side proxy (Option C), inbox-driven
   wake (Option D), remote `bead=`/`hood=`/`@tribe`/epic-follow, lifting the
   `%dispatch`+`%wait` ban, and bidirectional-rendezvous detection.
6. **Rollout order:** parser + diagnostics → `sase agent wait --machine` (the
   independently testable poll loop) → parked-agent (`%wait`) admission support
   in `wait_checks`/runner fallback → TUI labels → docs/memory. Each step is
   shippable and the first two already deliver scripted cross-machine pipelines.

## Appendix: sources consulted

- `docs/reference/integrations/remote-dispatch.md` — enrollment, launch
  constraints ("V1 remote launch does not combine with `%wait`, `%queue`,
  `%clan`, or `%hold`"), fleet operations journaling, feed-staleness UX.
- `docs/reference/cli/machine.md` — `machine init/add/repair/status` surface.
- `docs/reference/agents/machine-initialization.md` — init review/acknowledgment
  behavior.
- `docs/reference/macros/directives.md`, `docs/reference/macros/directive-launch.md`
  — `%wait`/`%dispatch`/`%hold`/`%queue` grammar and combination rules.
- `sase/memory/dispatch.md`, `sase/memory/macros.md` (via audited `sase memory
  read`) — launch selector, source preflight, same-key recovery, viewer parity.
- Code: `src/sase/macro/_directive_scan.py` (combination ban),
  `src/sase/macro/_directive_values.py` (wait/dispatch arg validation),
  `src/sase/agent/wait_target_binding.py` (bind-time pinning),
  `src/sase/agent/wait_watch/{_resolve,_watch,_types,_classify}.py` (poll engine),
  `src/sase/agents/cli_wait.py` (`sase agent wait`),
  `src/sase/axe/run_agent_wait_deps.py` (parked-wait release),
  `src/sase/dispatch/{fleet_client,machine_service,launch_preview,models}.py` and
  `src/sase/dispatch/federation/_facade.py` (transport, config, read ops),
  `src/sase/dispatch/models.py::validate_machine_alias` (dots legal in aliases),
  `src/sase/wait_spec.py` (wait-spec grammar).
