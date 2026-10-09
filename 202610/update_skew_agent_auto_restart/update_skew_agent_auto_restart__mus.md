# Auto-Relaunching sase Agents That Fail From Mid-Run Updates

**Researcher:** mus · **Date:** 2026-10-09 · **Swarm:** research.47
**Question:** agents failed with `ImportError: cannot import name
'auto_launch_prefix' from 'sase.monitor.continuation_delivery'` after a sase
update landed while they were running. Should we detect such errors and
automatically dismiss + relaunch the failed agent (once), mirroring the manual
Agents-tab `,x` → submit-unmodified flow, with a thorough notification? Lead
the design: intuitive, reliable, beautiful.

---

## 1. TL;DR (read this and skip to §8 for the build order)

1. **Yes, build it — but not as an ImportError-regex watcher.** The robust
   design has two halves: (a) make version skew a *first-class, explicit*
   failure (`VersionSkewError`, recorded structurally at the catch site), and
   (b) auto-relaunch exactly once on that error class plus a tiny allowlist
   of structurally-recorded infrastructure failures. Fuzzy-matching
   `ImportError` message text is the weakest part of the proposal as stated;
   §5 explains why and what replaces it.
2. **The real fix is defense in depth.** Auto-relaunch is the safety net, not
   the fix. The fix is atomic installs (new-tree + symlink swap, never
   half-written trees) plus spawn-time version stamping so a skewed process
   *knows* it is skewed. With those two, the detector becomes one crisp
   predicate instead of a pattern catalog.
3. **Reuse, don't reimplement, the `,x` path.** The headless equivalent of
   "`,x` then submit unmodified" already exists: `prepare_kill_and_edit_prompt`
   (`src/sase/agent/relaunch_prompt.py`) for the rewrite plus
   `plan_agent_restart` / `execute_agent_restart` (`src/sase/agent/restart.py`
   seam). Drive those. Do not drive TUI internals.
4. **Reliability hinges on three mechanisms the request doesn't mention:**
   an update-quiescence gate (never relaunch into a half-written install), a
   persisted once-only marker with a fleet-wide circuit breaker, and a
   launch-failure vs task-failure distinction (only the former auto-relaunches).
5. **Notifications:** one digest-capable sender in
   `src/sase/notifications/senders.py` (new `notify_agent_auto_relaunched`,
   precedent: `notify_axe_error_digest`), coalescing same-signature bursts,
   attaching the original error excerpt as a file, and stating plainly that no
   second auto-retry will happen.

---

## 2. What actually happened (root-cause analysis)

### 2.1 The symbol does not exist

I searched the entire `src/` tree for `auto_launch_prefix`: **zero hits**.
The name appears nowhere in the current checkout — not in
`src/sase/monitor/continuation_delivery.py` (which today is about ordinary
continuation reservation, spawn claiming, and receiver adoption), not in its
tests, nowhere. So the failing agents were running **old bytecode** (a
supervisor or delivery path from before the update) that imported a name from
a **new** `continuation_delivery` module where that name no longer exists —
or, symmetrically, new code importing from a partially-replaced tree. Either
direction is the same disease: **a long-lived sase process imported across a
version boundary mid-run.**

### 2.2 Why sase is structurally exposed to this

Several sase processes are long-lived and import sase modules continuously:

- **Monitor supervisors** (`src/sase/monitor/supervise.py`): detached
  per-agent processes (`python -m sase.monitor.supervise`) owning a monitored
  command from spawn through the terminal marker, streaming output and
  reacting to signals. They live as long as the agent does.
- **Continuation delivery** (`claim_ordinary_continuation_dispatch`,
  `claim_dispatch_slot`, spawn-slot claiming): the exact frame in the
  traceback. Delivery happens repeatedly over an agent's life, so every
  delivery after an update re-imports (or re-resolves attributes) across the
  boundary.
- **TUI observers / Agents-tab pollers** and hook/agent/mentor processes
  (`src/sase/ace/hooks/...`) with the same long-lived shape.

Meanwhile `sase update` replaces the installed tree underneath them (global
install; agents are even *forbidden* from running `just install`, per the
`global-install-is-human-only` decision — the human updates while the fleet
runs). A non-atomic rewrite means there is a window where the tree is a mix
of old and new files, plus stale `__pycache__` entries. Any import in that
window can produce `ImportError`, `ModuleNotFoundError`, or `AttributeError`
— the exact trio that `src/sase/monitor/store.py` **already catches
defensively in three places** (`except (OSError, RuntimeError, ValueError,
ImportError, AttributeError)`), which is precedent that the codebase treats
these as expected environmental failures, not programming bugs.

### 2.3 The failure is cheap — and that matters for the design

A skew failure strikes at **spawn/delivery time**: the agent's model turn
never started, (almost) no tokens burned, no user-visible work produced. That
makes it the *safest possible* thing to auto-retry — far safer than retrying
an agent that ran for 20 minutes and then failed. This observation becomes
the launch-failure vs task-failure rule in §6.

---

## 3. Critique of the plan as stated

### 3.1 What's right

- **Supporting update-while-running is the correct goal.** Users will update
  whenever prompted; telling them to drain the fleet first will fail in
  practice. The system should be robust to it.
- **Restart-exactly-once is the correct budget.** It bounds cost, bounds
  surprise, and converts "flapping forever" into "one graceful recovery."
- **Mirroring `,x`-submit-unmodified is the correct UX invariant.** Users
  already understand what that operation means; an automatic version of it is
  legible ("sase did what I would have done").
- **A thorough notification is non-negotiable.** Silent auto-relaunch would
  be creepy (new token spend, new process) and undebuggable. The request is
  right to demand excellence here.

### 3.2 What's risky or wrong — and my adjustments

| # | Issue with the proposal as stated | Adjustment (called out per instructions) |
|---|-----------------------------------|------------------------------------------|
| 1 | **Fuzzy ImportError pattern-matching is fragile.** `ImportError` text also fires on genuinely broken installs, missing optional deps, and user-environment damage — none of which a relaunch heals. A relaunch-into-broken loop burns exactly the one retry on a no-hope case, and worse, *normalizes* ignoring ImportErrors that are real bugs. | **Classify structurally at the catch site** (§5): record `failure_class: "version_skew"` (explicit version check) at delivery/spawn time. Match the class, not the string. Keep at most 2–3 string patterns as a legacy backstop, clearly marked. |
| 2 | **No quiescence gate.** Relaunching the instant the failure is seen can relaunch *into the same half-written tree* (update still copying files), failing again and spending the single retry for nothing. | **ADJUSTMENT: add an update-quiescence gate** — relaunch only when the installed version has been stable for N seconds (or an install lock/marker is absent). This is a new requirement, and it's the highest-leverage reliability item. |
| 3 | **"Without modifying it" is literally false for `,x`.** The kill-and-edit path *rewrites* the prompt (forced name reuse, `%id`/clan/agent-session reference repair via `prepare_kill_and_edit_prompt`, with `KillAndEditPromptError` refusals for unrecoverable cases). Submitting "the prompt that loads" unmodified means submitting the *rewritten* prompt. | **ADJUSTMENT: restate the invariant** as "the exact prompt the `,x` flow would seed, submitted with no additional user edits." Reuse `prepare_kill_and_edit_prompt` verbatim — do not hand-roll a "resubmit stored prompt" path that skips the rewrite, or relaunches will collide on names and clan membership. |
| 4 | **Per-agent "exactly once" is necessary but not sufficient.** A bad update can fail 50 agents at once; 50 simultaneous relaunches = a thundering herd against a possibly-still-settling install, plus 50 notifications. | **ADJUSTMENT: add a fleet circuit breaker** (cap auto-relaunches per window, e.g. N per 10 min; overflow stays FAILED and is named in the digest notification) and stagger relaunches with jitter. |
| 5 | **No launch-vs-task distinction.** "Detected error pattern matches → restart" applied to an agent that *ran and failed at its task* (test failures, wrong answer, provider error mid-turn) would silently re-spend a full agent turn on something the user may already be handling. | **ADJUSTMENT: auto-relaunch applies only to infrastructure/launch failures** — agent never productively started (delivery/spawn/adoption errors, skew errors). Task failures are never eligible, no matter the pattern. |
| 6 | **Bypassing admission/confirmation could surprise.** `sase agent restart` has confirmation logic (`restart_needs_confirmation`) and launch admission (holds, capacity). An auto path must not bulldoze those. | **ADJUSTMENT: the auto path plans through the same `plan_agent_restart` gate** (refusals → no relaunch, noted in notification) and launches through normal admission, never forced. |
| 7 | **Silent scope: which agents?** Epics, plan-chain members, clan members, and agent-session roots have identity subtleties (`_verify_*` functions exist precisely because naive relaunch breaks them). | **ADJUSTMENT: reuse the `,x` eligibility predicate** (`_agent_is_restartable` / `prepare_kill_edit_agent_prompt` returning `None` = ineligible → no relaunch). Whatever `,x` refuses, auto refuses. |

### 3.3 Would I take a different approach?

Not a *different* approach — a **layered** one. Ranked by leverage:

1. **Make skew explicit (kills the pattern problem).** Stamp `sase_version`
   (+ install-tree mtime/identity) into the agent row / monitor claim record
   at spawn; check it at every delivery/adoption. Mismatch → raise a
   dedicated `VersionSkewError` carrying `expected_version` / `actual_version`.
   The detector then matches *one type*, not N strings. This is a small,
   high-value change and I recommend it as Phase 0.
2. **Make installs atomic (shrinks the window).** Install the new tree to a
   fresh directory and symlink-swap (or equivalent); never mutate the live
   tree file-by-file. This converts "mixed-tree ImportErrors" (unmatchable in
   principle — any import can fail) into "old-process/new-tree skew" (exactly
   the explicit error from layer 1). If atomic install already holds, say so
   in the design doc and skip; if not, it's worth more than any detector.
3. **Auto-relaunch as the safety net** (this proposal), keyed on the explicit
   error from layer 1.
4. **Supervisor re-exec (future).** Long-lived supervisors could detect skew
   and re-exec themselves into the new version instead of dying. This is the
   elegant end-state but strictly harder (in-flight stream state, claim
   ownership); do not block auto-relaunch on it.

Layers 1+2 also fix the *detection* story for every future skew-shaped bug,
not just this one ImportError.

---

## 4. Where the manual flow lives (what "similar to `,x`" must reuse)

Traced in the current tree:

- **Eligibility + prompt resolution (TUI):** `prepare_kill_edit_agent_prompt`
  in `src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py` — checks
  `_agent_is_restartable`, loads stored prompt via
  `get_restartable_prompt_content`, and calls `prepare_kill_and_edit_prompt`.
  **This is the spec for "which agents are eligible."**
- **The rewrite (headless-safe):** `src/sase/agent/relaunch_prompt.py`
  (`prepare_kill_and_edit_prompt`, `ensure_forced_name_reuse`,
  `KillAndEditPromptError`). Deliberately lives outside the TUI package so
  non-TUI callers can use it — the auto path qualifies. Handles unnamed
  prompts (returned unchanged → fresh name), agent-session members/roots,
  clan membership, and *refuses* unrecoverable rewrites by raising.
- **Plan/execute (headless `,x` equivalent):** the `sase.agent.restart` seam
  (`src/sase/agent/restart.py` → `_restart_planning`, `_restart_execute`,
  `_restart_recovery` with the `~/.sase/restarts` bundle). Planning is
  read-only; every refusal surfaces *before* anything is killed. The CLI
  (`src/sase/agents/cli_restart.py`, `sase agent restart`) is the proof that
  the TUI is not needed for dismiss+relaunch.
- **Failure-prompt preservation:** `stash_failed_launch_prompt`
  (`src/sase/agent/failed_launch_prompt_stash.py`) already saves failed-launch
  prompts into the prompt stash (never raises, never masks the original
  error). The auto path should keep calling it — belt and suspenders for
  prompt recovery.
- **Submit equivalence:** manual `,x` mounts the prompt bar pre-filled
  (immediately, via the `_relaunch_barrier` ordering barrier) and `<ctrl+g>`
  submits through the normal launch pipeline (admission, holds, capacity).
  Headless equivalence = rewritten prompt → normal launch pipeline with the
  same admission. **Do not build a privileged "auto-launch" lane that skips
  admission** — that would let a fleet-wide skew event stampede capacity and
  bypass holds the user set deliberately.

Design rule: **the auto path is `plan_agent_restart` + quiescence gate +
once-marker + `execute_agent_restart`, invoked from a non-TUI sweeper.** Any
design that duplicates the TUI action code will drift from `,x` semantics
within a release or two.

---

## 5. Which error patterns to match (the "think hard" section)

### 5.1 Principle: match classes recorded at the catch site, not log strings

By the time an agent row reads FAILED with a traceback in a log, the
information about *where* the error was raised is degraded. The reliable
design records a machine-readable `failure_class` (+ `failure_signature`:
exception type, module, symbol) at the `except` site in the delivery/spawn
paths, persisted on the agent/monitor record. The sweeper matches classes.
String patterns are a backstop for failures recorded before this change
ships, and for paths we haven't instrumented yet.

### 5.2 Recommended allowlist (eligible for auto-relaunch)

These share three properties: **infrastructure-phase** (agent never
productively started), **externally caused** (update/skew, not the prompt),
and **self-healing on retry** (the world has moved on by retry time):

1. **`version_skew` (new explicit class — Phase 0).** Spawn-stamped version
   ≠ delivery-time version. Includes the reported `auto_launch_prefix`
   ImportError *once it is re-expressed* as skew (old code importing new
   module). This is the primary trigger; everything below is secondary.
2. **`sase_import_breakage` (narrow).** `ImportError` / `ModuleNotFoundError`
   where the module path starts with `sase.` (or `sase_core_rs`) raised in a
   spawn/delivery/adoption frame — backstop for skew that predates the
   explicit check. Deliberately **excludes** ImportErrors for third-party
   modules (broken venv, user env damage — relaunch won't heal).
3. **`binding_transient`.** `sase_core_rs` / Rust-binding import failures at
   spawn (native extension mid-rebuild during update). Same shape as (2) but
   worth naming separately because its quiescence signal differs (extension
   file settled, not just tree mtime).
4. **`state_wire_mismatch_at_spawn`.** Wire/schema-version decode failures
   (`ValueError: ... schema mismatch`-shaped, `proc wire schema mismatch`)
   raised while *reading our own freshly-written state* across an update —
   heals once the install settles. **Only at spawn/adopt time**; the same
   error mid-task is not eligible (see blocklist).
5. **(Possible, flagged for decision) `supervisor_lost_during_update`.**
   Supervisor process vanished while an install was in flight (mtime evidence)
   with no terminal marker. This one needs care — "lost" can also mean OOM or
   host reboot — so gate it on positive evidence of a concurrent update
   (install log/marker within the window), not merely temporal coincidence.

### 5.3 Blocklist (never auto-relaunch, even on a FAILED row)

- **Prompt/directive errors** (`DirectiveError`, macro parse/expand errors,
  unknown model aliases): relaunch reproduces them deterministically. (Note:
  `_verify_kill_and_edit_prompt` already tolerates stale aliases at
  seed-time — but *launch* still validates, so it fails again.)
- **Provider/auth/quota/rate-limit errors**: retry policy belongs to the
  provider layer with backoff, not to dismiss+relaunch (which would also
  churn the agent identity).
- **User-driven terminals**: user kill/stop/dismiss, plan rejection, declined
  confirmations, `STOPPED` chain slots. Relaunching something the user killed
  is the most trust-destroying behavior in this design space.
- **Task failures**: agent ran, produced output, and failed (test failures,
  wrong results, mentor rejection, budget caps). Zero auto-relaunch.
- **Anything already auto-relaunched once** (marker present), anything with
  significant token spend (belt: even if the class matches, a high-spend row
  suggests the agent *did* run — treat as task failure), and anything the
  `,x` eligibility predicate refuses (`prepare_*` returns `None` or raises
  `KillAndEditPromptError`).

### 5.4 Why "exactly once" should mean "once per agent row, plus fleet cap"

Once-per-row is the right atomicity (a relaunched agent is a *new* row with
its own budget — if the new row hits skew again from a *second* update, that
is arguably a new event; but to keep the guarantee legible to users, document
it as "at most one automatic relaunch per agent you launched; a second update
that breaks the replacement is reported, not auto-retried"… or deliberately
choose per-(row) with the same once-only rule applying to the replacement —
either is defensible; pick one and state it). The fleet circuit breaker (§3.2,
item 4) is the backstop against correlated mass failure regardless.

---

## 6. Reliability design (the unglamorous parts that decide success)

1. **Quiescence gate (new requirement).** Before relaunch: installed version
   string stable across two reads separated by N seconds (suggest N=30,
   jittered), no install lock/marker present, and (for binding failures) the
   native extension mtime settled. If not quiescent, *defer* (re-check on a
   bounded schedule, e.g. up to 15 min) rather than spending the retry. A
   deferred relaunch must say so in the notification ("waiting for update to
   settle").
2. **Persisted once-only marker, checked atomically.** Store
   `auto_relaunch_attempts` keyed by agent/row identity in durable state
   (extend the `~/.sase/restarts` bundle or the agent record — not process
   memory, since the TUI restarts too). Check-and-set must be atomic against
   two observers (TUI + CLI sweeper) to avoid double relaunch. Lost-marker =
   potential double relaunch, so the marker write must precede the launch,
   and a crash between marker-write and launch must resolve to "attempt
   spent, notify" (fail closed toward *not* relaunching twice).
3. **Eligibility re-verified at relaunch time.** `plan_agent_restart` refusal,
   `prepare_kill_and_edit_prompt` refusal/`None`, or admission/hold refusal →
   no relaunch; notification explains which gate said no. The world may have
   changed between detection and quiescence.
4. **Sweeper placement.** Prefer a hook in the non-TUI layer that already
   observes terminal agent states (monitor/store or agent-list polling core),
   callable from both the TUI observer and a headless path, so headless
   fleets get the behavior too. The TUI Agents tab additionally annotates the
   row ("auto-relaunched 1× — update skew, 12:04"). Rust-core-boundary note:
   per `rust_core_backend_boundary`, if the marker + failure-class schema is
   behavior every frontend must agree on, it belongs in the `sase_core` crate
   with Python calling through the binding; the TUI annotation and
   notification copy stay in this repo. Decide the placement explicitly in the
   design doc — do not let the marker become a second, divergent Python-side
   schema.
5. **Observability.** Every auto-relaunch writes a structured record (agent,
   signature, pre/post version, quiescence waits, outcome) to the diagnostic
   log dir pattern (`diagnostics.py` precedent) and links it from the
   notification file. If the relaunched agent fails *again* (any cause), the
   notification follow-up states the final FAILED disposition and does not
   retry.
6. **Kill safety.** The auto path performs the same kill-and-dismiss the
   manual path does. Only FAILED-terminal rows are eligible — never running,
   paused-for-input, or plan-awaiting-review rows. A TOCTOU re-check
   (row still FAILED immediately before kill) is required.

---

## 7. Notification design (intuitive + beautiful)

Precedent: `notify_axe_error_digest` (`src/sase/notifications/senders.py`) —
sender label, human-readable notes, machine-actionable `action`/`action_data`,
and a digest *file* attached for detail. New sender
`notify_agent_auto_relaunched` should follow that shape:

- **Sender:** `"agents"` (stable, filterable).
- **Notes (human, ordered):** (1) what happened in plain language —
  "Agent `research.47.mus` failed during sase's self-update (old code met new
  code: `ImportError: …auto_launch_prefix…`)"; (2) what sase did — "Dismissed
  and relaunched it unchanged (automatic retry 1 of 1), same prompt, same
  name"; (3) the state of the world — "Update settled on version X before
  relaunching" or "Relaunch deferred: update still settling"; (4) what comes
  next — "If the replacement fails, it will stay failed and notify; sase will
  not retry again on its own."
- **Coalescing:** same-signature failures within a window produce ONE
  notification listing all agents ("7 agents failed on update skew; 5
  relaunched, 2 deferred/ineligible — details attached"), following the digest
  precedent. Fifty push notifications for one update is the failure mode to
  avoid; also respect the fleet circuit-breaker overflow explicitly ("3 more
  were left failed by the auto-relaunch rate cap — say the word and I'll
  relaunch them" — with the action to do it).
- **Action:** deep-link to the agent / Agents tab (existing actions like
  `JumpToChangeSpec`/`HITL`/`OpenLaunchControl` are the pattern; add
  `JumpToAgent` or reuse the closest existing one — do not invent a parallel
  action vocabulary).
- **Attached file:** error excerpt + relaunch record (versions, signature,
  marker id), mirroring the digest-file pattern, so the inbox note stays
  short and the forensics are one tap away.
- **Tone:** factual, calm, no exclamation marks, no anthropomorphism. State
  whose tokens are being spent (the user's) — "relaunched (this spends a
  fresh agent turn)" is the honest line that keeps trust.
- **Settings:** a visible opt-out (`agents.auto_relaunch`, default on for
  skew-class only) and per-notification affordance ("don't auto-relaunch
  again" → flips the setting). Auto-spending user money with no off switch
  is not beautiful.

---

## 8. Recommended solution (phased)

**Phase 0 — make skew explicit (small, unlocks everything).**
Stamp install version + tree identity at spawn/claim time; check at each
delivery/adoption; raise/persist `VersionSkewError` with both versions.
Record `failure_class` + `failure_signature` structurally on FAILED rows at
the catch sites (delivery, spawn, adoption). No behavior change yet — just
evidence. (Assess `rust_core_backend_boundary` placement for the schema
here.)

**Phase 1 — headless auto-relaunch for the skew class only.**
Sweeper (non-TUI core, surfaced in TUI too): match `failure_class ==
"version_skew"` on FAILED-terminal rows → check persisted once-marker →
quiescence gate (defer ≤15 min) → re-verify `plan_agent_restart` +
`,x`-eligibility → `execute_agent_restart` through normal admission →
`notify_agent_auto_relaunched` (coalesced). Fleet circuit breaker from day
one. Setting `agents.auto_relaunch` (default on) with an explicit off path.

**Phase 2 — widen cautiously.**
Add allowlist classes from §5.2 one at a time, each with a documented
heals-on-retry argument and a soak period watching the relaunch-success rate.
Any class whose auto-relaunch success rate is low gets demoted back to
notify-only. Never add task-failure or user-terminal classes.

**Phase 3 (parallel, owned separately) — shrink the cause.**
Atomic installs + supervisor re-exec investigation. Every improvement here
reduces the detector's workload; the detector remains as the net.

**Explicit non-goals:** auto-relaunch of task failures; retry budgets >1
without a user decision; privileged launch lanes bypassing admission; string-
pattern matching as the primary detector; silent (notification-free)
relaunch.

---

## 9. Open questions for the lead

1. Is atomic install already guaranteed by `sase update`? (Determines how
   much Phase 3 matters.)
2. Per-row once-only vs once-per-causal-chain: if a *second, separate*
   update breaks the replacement, should that replacement get its own single
   retry? I lean yes-per-row-lifetime with the fleet cap as backstop, but it
   needs a stated rule.
3. Should `agents.auto_relaunch` default on? I lean yes for the skew class
   (cheap, clearly-correct, no useful user action exists) but several peers
   may reasonably demand opt-in for anything that spends tokens.
4. Rust-core vs Python placement of the marker + failure-class schema (§6.4).

---

## 10. Sources consulted (all independent; no peer reports touched)

- `src/sase/monitor/continuation_delivery.py`, `supervise.py`,
  `outcome_policy.py`, `store.py` (ImportError-tolerant catch sites)
- `src/sase/agent/relaunch_prompt.py`, `restart.py`, `_restart_types.py`,
  `failed_launch_prompt_stash.py`; `src/sase/agents/cli_restart.py`
- `src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py`,
  `_relaunch_barrier.py`, `_keybinding_modes.py` (`,x` flow), keybinding
  display in `_keybinding_bindings_agents.py`
- `src/sase/agent/status_buckets.py` (FAILED-terminal semantics)
- `src/sase/notifications/senders.py` (`notify_axe_error_digest` precedent)
- `AGENTS.md` project rules (rust-core boundary, global-install-human-only
  decision context)

*Peer-report avoidance: I listed the `202610/` research directory to pick a
non-colliding filename (saw peer filenames only) and did not open, read, or
infer from any `__cdx/__cld/__grk/__gem` report or transcript.*
