# Why `16h.f0` started before `16h` finished, and should `#fork` get `target=session|turn`?

**Short answer.** `#fork:16h` did mean "wait for the `16h` session", and the docs say so.
It released early because of **when** the wait was bound. When `16h.f0` launched
(15:22:39), `16h` was still a bare agent. It had no gate or coder yet, so it was not yet
an agent session. `fork_wait_dependency()` therefore recorded the dependency as
`kind: "agent"`, pinned to the artifact of 16h's first (plan) turn. About two minutes
later, 16h's plan turn opened a tale gate and `16h` was promoted to a session
(`16h--plan`, `16h--gate`, then `16h--code`). The stored dependency never learned about
the promotion. The fork-wait checker for `kind: "agent"` only looks at that one
artifact's done marker, and it skips the name-based, session-aware check for any name
that has a fork source. So `16h.f0` released at the exact instant `16h--plan` finished
(15:25:08.57), while 16h's gate and coder were still ahead of it.

So this is a **bug** (the bound kind goes stale after promotion), not proof that `#fork`
targets turns. Your proposed `target=` option is still worth adding, but only on top of
the fix. A `target=session` default on its own would not have prevented this incident:
the code already thought it was doing the session thing.

**Recommendation (details in §8):**

1. **Fix the bug first, with no new syntax.** Make bare-name fork dependencies notice
   promotion: a bare agent counts as a session of one, re-checked at evaluation time.
   Include a compatibility rule for waits that are already persisted.
2. **Then add the option, with three adjustments:**
   - Call it `scope=` rather than `target=`.
   - Store it on the wait dependency itself, so `%wait` and the gate coder options can
     use the same field.
   - Plumb it through both places that read `#fork`: the launch-time scan and the
     history resolver. This needs a small macro-loader change, because `fork.yml`'s
     repeatable `name` input must currently be the last input.

---

## 1. What happened (evidence)

All artifacts are under
`~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/30/`. Times are EDT.

| Time        | Event                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 15:16:00    | `16h` launched (artifact `20261030151600`), runs from 15:17:42. At this point it is a **bare agent** named `16h`.                                                                                                                                                                                                                                              |
| 15:22:39    | `16h.f0` launched: `#gh:gh_bobs-org__bob-cli #fork:16h … #plan %m:@xlarge`. Launch-time extraction records `wait_for: ["16h"]` and `wait_for_fork_sources: [{"kind": "agent", "name": "16h", "artifact_dir": ".../20261030151600", "timestamp": "20261030151600"}]`. Note `kind: "agent"`, not `"session"`.                                                    |
| 15:25:01    | 16h's plan turn proposes a tale. Gate turn `16h--gate` (`20261030152501`) is created and `16h` is **promoted to a session**: the root is renamed `16h--plan` and gets `agent_session: "16h"`, `agent_session_role: "root"`.                                                                                                                                         |
| 15:25:08.57 | `16h--plan` writes `done.json` (`outcome: completed`, `finished_at: 1793388308.573959`).                                                                                                                                                                                                                                                                      |
| 15:25:39    | **`16h.f0` wait released.** `wait_dependencies_satisfied_at = 1793388308.573959`, exactly 16h--plan's `finished_at`. `wait_release_source: ready_json`.                                                                                                                                                                                                       |
| 15:27:18    | `16h.f0` starts running (after an 85.8 s runner-slot wait).                                                                                                                                                                                                                                                                                                 |
| 15:27:50    | `16h.f0`'s fork history is rendered. It already sees a session: _"Source 1 of 1 — agent session `16h` · Members shown: 1 of 2 · Not shown: `16h--gate` (running)"_.                                                                                                                                                                                             |
| 15:30:48    | You answer 16h's tale gate (approve + commit). `16h--code` (`20261030153048`) is launched and runs from 15:32:29.                                                                                                                                                                                                                                             |
| 15:51:36.77 | `16h--code` finishes. The `16h` session is now actually done.                                                                                                                                                                                                                                                                                         |
| 15:51:54    | `16h.f0--code` (from 16h.f0's tale gate, with coder option `wait_agents: ["16h"]`, giving `%wait(16h)`) is released. Its `wait_dependencies_satisfied_at = 1793389896.767679`, exactly 16h--code's `finished_at`. It had `wait_for: ["16h"]` and `wait_for_epics_of: ["16h"]`, and **no** fork source.                                                       |

The last two rows matter. The coder-options `%wait(16h)` waited for the whole session, as
you expected. Only the implicit wait from `#fork` released early. The fork's own history
renderer also knew `16h` was a session with a running gate, so `16h.f0` was in effect told
"you are forking an unfinished session".

## 2. Mechanism (code path)

1. **The implied wait is derived once, at launch, from a lexical scan.**
   `resolve_wait_state()` (`src/sase/axe/run_agent_directives_flow.py:40`) collects
   `#fork` names via `fork_agent_names()` (lines 73–85). For each implicit target it
   calls `fork_wait_dependency(name)` (lines 120–126). The result is persisted as
   `wait_for_fork_sources` in `agent_meta.json` and `waiting.json`.
2. **`fork_wait_dependency()` freezes the kind as well as the identity.**
   (`src/sase/agent/fork_waits.py:13`). The order is clan, then `find_agent_session()`,
   then `find_named_agent()`. `find_agent_session()` deliberately ignores "plain exact
   agents named `base_name`" (`src/sase/agent/names/_lookup_groups.py:320`). It only sees
   artifacts that carry `agent_session` or plan-chain metadata, and a bare agent gets that
   metadata only when `promote_agent_to_agent_session()` runs
   (`src/sase/agent/_agent_session_promotion.py:82`, writing `role="root"` at line 170).
   That happens when the first gate, monitor, or handoff member is attached. At 15:22:39
   none existed, so the lookup fell through to
   `{"kind": "agent", "artifact_dir": <16h's first artifact>}`.
3. **Evaluation trusts the frozen kind.** In
   `src/sase/core/wait_dependency_resolution/_index_fork_queries.py:82`, the `"agent"`
   branch returns `candidate.is_done or candidate.is_failed` for the pinned artifact.
   Only the `"session"` branch (line 91) calls `agent_session_candidate_for_root()`,
   which aggregates the whole session, including declared-but-not-yet-launched handoffs.
4. **The session-aware name check is skipped.**
   `dependency_resolution_status()` (`_resolution.py:71`) runs
   `if name in identity_names or name in fork_source_names: continue`. So the plain
   `"16h"` in `wait_for` is never evaluated through `is_resolved("16h")`, which would have
   chosen the session aggregate, as it did for `16h.f0--code`.

The launch-time binding is deliberate. `docs/reference/macros/built-ins.md` explains that
a proc/monitor name "is bound to one exact durable proc ID when the fork directive is
extracted, so a later proc reusing that name never redirects an already-queued fork."
Identity pinning is good, and it is also what gives forks "release on failure too"
semantics. The defect is narrower: the **kind** is pinned along with the identity, and a
bare agent's kind is not stable, because promotion is a normal lifecycle event that comes
after launch.

This is a different mechanism from the earlier `11q.w0` early release
(`research:202610/11q_w0_early_wait_release.md`). That one was a gate-settlement window
where a transient `gate_followup_outcome: "failed"` looked like "no successor". Here the
release came 5½ minutes **before** the gate was even answered.

## 3. Verification (replaying the 15:26 state)

I copied `16h--plan` (done) and `16h--gate` (metadata only, gate open, no follow-up
fields, no `done.json`) into a temporary projects root. `16h--code` was not yet present.
I then ran the real resolver (`build_wait_dependency_index` +
`dependency_resolution_status`) from the installed sase:

```
recorded kind=agent dep            -> resolved          # the bug, reproduced
pinned candidate: 16h--plan session=16h parent_ts=None done=True
promotion-aware session aggregate: AgentSessionCandidate(timestamp='20261030152501',
                                     is_resolved=False, is_done=True, ...)
same dep as kind=session           -> waiting  (blocked_on the 16h root)
explicit %wait:16h (name only)     -> waiting  (blocked_on '16h')
```

The pinned candidate itself already says "I am now the root of session `16h`"
(`agent_session_name="16h"`, no `parent_timestamp`). The data needed to fix this is in
the index at evaluation time. Only the dispatch on `kind` ignores it.

## 4. Bug or missing feature?

Bug. The documented contract is that bare-name references go through the session:

> `%wait:<session>` and `#fork` references to the bare session name resolve through the
> session container … An exact `--<suffix>` name targets one member.
> — `docs/reference/agents/agent-sessions.md:97-101`

`16h.f0` broke that contract only because `16h` was not a session **yet**. Three
behaviors show the inconsistency:

| Surface                                      | What it did for `16h`                            |
| -------------------------------------------- | ------------------------------------------------ |
| Explicit `%wait(16h)` (coder options)        | Waited for the whole session ✅                  |
| `#fork:16h` history renderer (late-bound)    | Treated `16h` as a session, flagged gate running |
| `#fork:16h` implied wait (launch-bound kind) | Waited for one turn ❌                           |

Your reading, "it seems to have targeted the currently running turn", is accurate about
the effect. But it was the turn that happened to be running at launch, and it was
targeted by accident. If 16h had already been promoted when you launched 16h.f0 (for
example, if you had launched it after 15:25:01), you would have gotten session semantics.

## 5. Critique of the proposal

**What's right about it**

- The underlying need is real. There are two useful "how much of X do I wait for"
  answers, and SASE currently picks between them implicitly, based on whether X has been
  promoted yet. That is the worst option. Making the choice explicit, with a safe
  default, is good design.
- `session` as the default is correct. It matches the docs, what you expected, and what
  `%wait` does.
- Using a closed, typed value (not free text) is correct. It gets validation,
  prompt-bar completion, LSP hover, and `sase macro types` for free, because one Rust
  catalog drives every surface.

**Problems and gaps**

1. **The default would not have fixed this incident.** The code already intended session
   semantics. Without the promotion fix, `#fork(16h, target=session)` launched at 15:22
   would release at 15:25:08 exactly as before. The bug fix is the prerequisite.
2. **`fork.yml` cannot take another input as written.** `name` is `repeatable: true`,
   and `validate_repeatable_input_order()` (`src/sase/macro/input_binding.py:24`) requires
   a repeatable input to be the **last** user-facing input. Appending `target` is a load
   error. Putting it first breaks `#fork:16h`, because position 0 would bind to `target`.
   You need to relax the rule so that inputs after a repeatable one are **keyword-only**.
   That is safe for the binder: `input_for_position()` never maps a position past the
   repeatable tail. But the signature and completion surfaces (`cli_show_model.py`,
   `_catalog_format.py`, and Rust `editor/macro_arg_choices.rs`) must render and complete
   it correctly. This is a real cost the plan didn't account for.
3. **The input is read in two different phases.** The wait comes from a **lexical scan
   at launch** (`_resume_reference_arguments()`, `src/sase/agent/names/_resume.py:307,315`,
   which currently throws away named args with `positional, _ = parse_args(...)`). The
   macro's typed input binding only happens at **expansion**, which is *after* the wait.
   If you only add a macro input:
   - the wait never sees it, and
   - a typo like `target=tunr` is rejected only after the agent has waited, possibly for
     hours.

   The launch scan must parse the keyword and validate it against the same enum
   definition, and launch preparation must fail fast.
4. **The name `target` is overloaded.** The codebase and docs already use "target" for
   the *name* being forked or waited on: `fork_wait_target`,
   `implicit_fork_wait_targets`, "bare-session `%wait` and `#fork` targets", and the TUI's
   `PromptTargetKind`. `#fork(16h, target=turn)` reads as "the target is turn". `scope=`
   (`%wait(16h, scope=turn)`) says what it means: how much of the target to wait for.
   This is a naming preference, low stakes, but cheap to get right now.
5. **Small correction on the enum type.** Model inputs use `type: model`, a builtin
   *domain* type validated by the Rust `classify_model_value`, not a plain enum. The
   precedents that fit are:
   - an inline `type: enum` with `choices` (`#pr`'s `status`), or
   - a **builtin closed enum** like `effort`, which shares its values with the `%effort`
     directive (`sase-core: crates/sase_core/src/macro_input_types/catalog.rs:109`).

   If the same values are also used by `%wait(scope=…)` (recommended), the `effort`
   pattern fits. Add a builtin `wait_scope` (or similar) named enum so `#fork`'s input
   and `%wait`'s keyword share one list.
6. **"Turn" needs a precise definition.** The proposal leaves these cases open:
   - **Bare agent:** turn = the agent's run (what happened to 16h.f0).
   - **Session whose live member is an agent turn:** turn = that member.
   - **Session parked at a gate:** the live member is the gate turn, so `scope=turn`
     waits for your decision. That is probably surprising if you wanted "fork the plan
     now", but `#fork:16h--plan` already says that exactly.
   - **Handoffs:** a `/sase_handoff` successor is a new turn, so `scope=turn` releases
     at the handoff and does not follow it.
   - **Idle or finished session:** turn = the newest member, so it releases immediately.

   Recommended rule: pin to the source member that is live at launch. If no member is
   live, pin to the newest member. Pin by artifact identity, like today.
7. **History must use the same cutoff as the wait.** The history resolver
   (`src/sase/scripts/_agent_chat_from_name_sources.py:152`) re-resolves the name late
   and renders every completed member. With `scope=turn` and a runner-slot delay, members
   that finished after the pinned turn could quietly be included, so a "turn" fork would
   carry more context than it waited for. The resolver should be given the scope and cut
   the session chain at the pinned turn (the pinned artifact and its predecessors).
8. **The motivating surface is `%wait`, not `#fork`.** The gate coder options build
   `wait_agents`, which becomes `%wait(name)` (`src/sase/_plan_approval_protocol.py:302`,
   `PromptWaitDirective`). A `#fork` input alone does nothing there. If you want the
   coder-options choice, the scope has to be part of the wait relation itself.
   `%wait` already takes keywords (`for_epic=`, `bead=`, `hood=`) and has directive
   diagnostics, so `scope=` fits there.
9. **Non-agent targets.**
   - Clans have generations, not turns. Tribes are next-entity. `scope=turn` on either
     should be a launch-time diagnostic.
   - A proc or monitor fork is already a single run, so `turn` and `session` are the same
     and both should be accepted.
   - A group-level keyword applies to every parent in `#fork(a, b, scope=turn)`. Mixing
     scopes needs separate `#fork(...)` references. That is fine, since mixed scopes are
     rare.
10. **Part of the need is already covered.** `#fork:16h--plan` and `%wait:16h--code`
    already target one member. `scope=turn` only adds something real when:
    - the member does not have a suffixed name yet (the bare-agent case), or
    - you don't know which member is current.

    That is a narrow but real use. One example is planning in parallel off a planner's
    context without waiting on approval and implementation. By accident, that is exactly
    what 16h.f0 did, and it worked out because 16h.f0's coder serialized behind 16h.

## 6. Options considered

| Option                                                                     | Fixes 16h.f0?           | Serves coder options? | Cost / risk                                                                          | Verdict                              |
| -------------------------------------------------------------------------- | ----------------------- | --------------------- | ------------------------------------------------------------------------------------ | ------------------------------------ |
| A. `target=` input on `fork.yml` only (as proposed)                        | No (needs B)            | No                    | Repeatable-last rule, two-phase parsing, history cutoff                              | Partial                              |
| B. Promotion-aware fork dependency (bug fix only)                          | **Yes**                 | n/a                   | Small: evaluation tweak plus recording tweak and tests                              | **Do first**                         |
| C. `%wait(x, scope=…)` only; `#fork` inherits an explicit wait's scope     | With B                  | Yes                   | Forking a turn takes two tokens; explicit waits use success-only semantics, so a failed source would park the fork forever | Rejected as the only surface         |
| D. Name-level selector (`#fork:16h^`, `16h--@current`)                     | With B                  | Yes                   | More name grammar next to templates (`@`), tribes (`@x`), and suffixes; poor discoverability; no typed completion | Rejected                             |
| E. Late-bind fork waits by name (drop identity pinning for agents)         | Yes                     | n/a                   | Loses "release on failure", self-exclusion, and the anti-name-reuse guarantee        | Rejected                             |
| **F. B + one `scope` field on the wait dependency, exposed as `#fork(…, scope=)` and later `%wait(…, scope=)`** | **Yes** | **Yes (phase 3)**     | B + A's plumbing, done once in the wait layer                                         | **Recommended**                      |

I also considered and deferred a third value, `scope=none` ("snapshot fork, don't wait").
Running members are not injectable, at least one shown member is required, and already
failed parents skip the wait today. So `none` would mostly produce errors or duplicate
`#fork:<x>--<suffix>` / `#fork_by_chat`.

## 7. Adjusted requirements (explicit changes to your spec)

| #   | Your spec                                 | Adjusted                                                                                                                                                                 | Why                                                                                       |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| R1  | (implicit) the option fixes this behavior | **Add a prerequisite bug fix:** bare-name `#fork` follows promotion with no new syntax                                                                                    | The default `session` already *was* the intent; the binding was wrong (§2, §3)            |
| R2  | `target=<target>`                         | **`scope=<scope>`** (suggested; keep `target` if you prefer)                                                                                                              | "target" already names the forked or waited entity across code and docs (§5.4)            |
| R3  | enum "like model inputs"                  | Inline `type: enum` with `choices: [session, turn]`, default `session`. **Promote to a builtin named enum** in the Rust catalog once `%wait` adopts it                   | `model` is a domain type; `effort` is the shared-values precedent (§5.5)                  |
| R4  | input on the `fork` macro                 | Also store `scope` on each `wait_for_fork_sources` entry, and validate at **launch**, not just at expansion                                                               | The wait is computed before expansion (§5.3)                                              |
| R5  | —                                         | **Relax the repeatable-last rule** so inputs after a repeatable positional are keyword-only                                                                               | Otherwise `fork.yml` cannot add the input (§5.2)                                          |
| R6  | "currently running turn"                  | Define `turn` = the member live at launch, else the newest member, pinned by artifact identity. History is cut at that member                                            | Covers gates, handoffs, and idle sessions; wait and history must agree (§5.6–5.7)         |
| R7  | —                                         | `scope=turn` is a launch error for clans and tribes, and a no-op for procs and monitors                                                                                    | No turn concept there (§5.9)                                                              |
| R8  | coder options can choose                  | Same `scope` on `%wait` / `PromptWaitDirective`, with a toggle in the coder-options wait field (phase 3, optional)                                                        | That surface emits `%wait`, not `#fork` (§5.8)                                            |

## 8. Recommended solution

### Phase 1: Bug fix (small, ship alone)

**Evaluation side** (`_index_fork_queries.py`, `fork_source_status`): handle `"agent"`
and `"session"` through one helper. Then old persisted markers, including any fork parked
right now, heal without a migration.

```python
def _root_scoped_status(self, candidate, dependency, *, exclude_artifact_dir):
    scope = dependency.get("scope") or _legacy_scope(dependency, candidate)
    if scope == "session" and candidate.parent_timestamp is None:
        session = self.agent_session_candidate_for_root(
            candidate, exclude_artifact_dir=exclude_artifact_dir
        )
        if session is not None:      # promoted (now or later): aggregate the session
            return _fork_status((session.is_resolved and session.is_done)
                                or session.is_failed)
    return _fork_status(_candidate_terminal_for_fork(candidate))  # bare agent / exact turn

def _legacy_scope(dependency, candidate):
    # A legacy "agent" record from a *bare* reference (`#fork:16h`) whose artifact has
    # since become the session root means "session". An exact member reference
    # (`#fork:16h--plan`) keeps meaning that one turn.
    name = dependency.get("name")
    if dependency.get("kind") in ("session", "family"):
        return "session"
    if candidate.agent_session_name and same_owner_key(name, candidate.agent_session_name):
        return "session"
    return "turn"
```

The guard on the second branch matters. `#fork:16h--plan` *also* records
`kind: "agent"`, pinned to the root artifact. Upgrading every root-pinned `"agent"`
record to session semantics would break the documented exact-member contract. Comparing
the recorded **name** with the candidate's session base tells a bare reference from an
exact one.

**Recording side** (`fork_waits.py`): when a bare name resolves to a bare root agent (no
`parent_timestamp`, no member suffix), record
`{"kind": "session", "scope": "session", "name": …, "artifact_dir": …}`, treating the
bare agent as a session of one, and record `"scope": "turn"` for exact member names. This
makes new markers self-describing. The evaluation-side rule exists only for old markers.

**Invariant to assert in tests:** a successor member (gate, monitor, or handoff) is
registered **before** its predecessor writes `done.json`. In this incident the gate was
created at 15:25:01 and the plan finished at 15:25:08. The session aggregate depends on
this ordering, so a regression test should pin it. Separately, confirm the `11q.w0`
gate-settlement window is closed, because session scope inherits it.

**Tests:**

- `tests/test_agent_names_extract_naming.py`: a bare agent forked, then promoted, records
  a session-scoped dependency.
- The wait-dependency suites (`tests/test_wait_dependency_slot_queued_session_members.py`,
  `tests/test_axe_chop_wait_checks_artifact_identities.py`): the exact 16h replay from §3
  stays waiting until the coder finishes. A legacy `kind: "agent"` + bare name +
  promoted root stays waiting. A legacy `kind: "agent"` + `--plan` name still releases
  on that turn.

**Docs:** `agent-sessions.md` §"bare session name": add "including an agent that becomes
a session after the fork or wait was launched". Add a CHANGELOG entry.

### Phase 2: `#fork(…, scope=session|turn)`

1. **Macro loader:** allow keyword-only inputs after a repeatable positional
   (`validate_repeatable_input_order`). Update compact signatures, `sase macro show`, and
   Rust editor arg completion to render `#fork(name..., scope=)`.
2. **`fork.yml`:** add
   `scope: {type: enum, choices: [{value: session, description: …}, {value: turn, description: …}], default: session}`.
   Pass `scope` into `agent_chat_from_name.main(names, scope=…)`.
3. **Launch scan** (`_resume.py`): return named args from `_resume_reference_arguments`.
   Validate `scope` against the fork macro's declared `InputArg` (the same Rust
   `check_input_value` path) and fail launch preparation on invalid values or on `turn`
   with a clan or tribe target. Pass `scope` into `fork_wait_dependency(name, scope)`.
4. **Turn pinning** in `fork_wait_dependency`: for `scope=turn`, resolve the live member
   at launch (else the newest member) and record
   `{"kind": "agent", "scope": "turn", "artifact_dir": <that member>}`.
5. **History cutoff:** with `scope=turn`, the resolver reads the pinned dependency from
   the launching agent's `agent_meta.json` (`wait_for_fork_sources`) instead of
   re-resolving by name. It renders the chain up to and including the pinned member, and
   lists later members as "not shown (after pinned turn)".
6. **Surfaces:** prompt-bar completion and diagnostics come from the catalog. The WAITING
   row's blocker label should name the scope, for example
   `waiting on 16h (turn 16h--plan)`, so a turn-scoped fork is never mistaken for this
   bug again.

### Phase 3 (optional, when you want it in coder options): `%wait(…, scope=…)`

Promote the values to a builtin named enum (`wait_scope`) in
`sase-core/crates/sase_core/src/macro_input_types/catalog.rs`, following `effort`.
Add `scope=` to the `%wait` directive parser and diagnostics, `PromptWaitDirective`,
`_add_optional_wait_fields`, `sase agent wait --scope`, and a toggle next to the
coder-options wait field. Explicit `%wait(x, scope=turn)` keeps `%wait`'s success-only
semantics. `#fork` keeps its terminal-on-failure semantics. Both share the same
dependency field and evaluator.

### Where the code lives (Rust boundary)

Wait and fork dependency resolution is still Python
(`src/sase/core/wait_dependency_resolution/`, with no Rust binding except epic-follow).
Phases 1–2 should change it where it lives. Porting it is a separate, larger decision.
The enum *values* are already Rust-owned through the input-type catalog. Phase 3 puts
the shared vocabulary there, which is the right side of the boundary because every
frontend has to agree on it.

## 9. Bottom line

- **Why it happened:** a launch-time binding bug. `#fork:16h` froze `16h` as "one agent
  run" because it hadn't been promoted to a session yet, and the fork-wait evaluator
  never re-checked.
- **Is the plan good?** The direction is good: an explicit, typed, defaulted choice
  between session and turn. As specified it is incomplete:
  - it doesn't fix the bug;
  - it can't be added to `fork.yml` without a loader change;
  - it must be parsed at launch, not just bound at expansion;
  - it needs a precise definition of "turn" and a matching history cutoff;
  - it doesn't reach the coder-options `%wait` you cited as motivation.
- **Recommended:**
  1. Ship the promotion-aware fix now.
  2. Then add `scope=session|turn` (default `session`) to `#fork`, stored on the wait
     dependency and validated at launch.
  3. Extend the same field to `%wait` and the coder options when you want that knob
     there.
