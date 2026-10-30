# Fork-wait granularity: why `16h.f0` started early, and a reviewed proposal for `target=session|turn`

Research swarm report (`__mus`). Question under study: why did the `16h.f0`
agent start before the `16h` agent finished, given `fork:16h` in its prompt —
and is a new `target=<target>` input on the `fork` macro (`session` vs `turn`,
enum-typed, default `session`) the right fix?

## TL;DR

- **Most likely cause:** `#fork:16h` does imply a wait, but the wait that gets
  armed is pinned at launch time to one of four identity kinds
  (`clan`/`session`/`agent`/`proc`, in that priority order). Only the
  `session` kind waits for the whole multi-turn session. If `16h` resolved to
  the **`agent` kind — a single turn artifact** — then `16h.f0` was released
  the moment *that one turn* wrote its terminal marker, even while `16h`'s
  logical work continued in a follow-up turn under a different artifact/name.
  This matches the observed symptom exactly, including the reporter's own
  suspicion that `16h.f0` "targeted the currently running turn."
- **The proposal is a good idea with adjustments.** The gap is real: today
  there is no way to express wait granularity, and the granularity you get is
  an emergent property of whatever identity existed at launch. But (1) model
  inputs are *not* the enum precedent — they are a builtin named type; the
  correct precedent is the `enum`+`choices` input in `pr.yml`; (2) the default
  must be `session` specifically because it preserves current behavior, not
  just as a preference; (3) `target` has to live in the `#fork` *reference
  syntax itself*, not just in `fork.yml`'s input declaration, because the wait
  is derived from raw prompt text before the macro ever renders; and
  (4) `target` should govern history injection and the wait together, or the
  two will disagree about what was "forked."
- **Recommended solution:** add an optional `target` qualifier
  (`session`|`turn`, default `session`) threaded through three layers —
  reference syntax (`#fork(16h, target=turn)`), `fork.yml` enum input, and
  `fork_wait_dependency` pinning — plus history-injection coherence, with
  wait-spec (`%wait`/TUI wait editor) parity as an explicit phase 2. Details
  in §6.

## 1. How `#fork` implies a wait today

The pipeline has four stages. All paths cited from the current checkout.

### 1.1 The `fork` macro itself does not wait — it injects history

`src/sase/macros/fork.yml` declares exactly one input, the repeatable `name`
(agent name, proc name/ID, or monitor turn; omitted means "default resolver"),
and runs two hidden steps: `resolve` (resolves names to transcript sources via
`agent_chat_from_name.main`) and `load_history` (assembles history via
`fork_history.main`), then injects the result as a prompt part. There is no
wait logic in the macro. The wait is *implied* and computed elsewhere.

### 1.2 The wait is derived by scanning the raw prompt for `#fork` references

`resolve_wait_state` in `src/sase/axe/run_agent_directives_flow.py` (lines
39–137) calls `fork_agent_names(fork_reference_prompt)` (from
`src/sase/agent/names/_resume.py`), and for every explicit fork target it does
**two** registrations (lines 73–85 and 120–127):

1. appends the name to `wait_names` (the plain-name wait channel), and
2. records a pinned identity in `wait_fork_sources` via
   `fork_wait_dependency(normalized_wait_name(name))` — unless the name was
   already an explicit `%wait` target, in which case only the name channel
   applies.

Both channels must resolve before the waiter is released (see §1.4). Tribe
references (`@...`) are included in the name channel but excluded from the
fork-source channel.

### 1.3 The fork-source identity is pinned at launch, with kind priority

`fork_wait_dependency` (`src/sase/agent/fork_waits.py`, lines 13–64) resolves
the name once, at child-launch time, in this order:

1. **clan** (`find_agent_clan`) → `{kind: clan, name, generation}`;
2. **agent session** (`find_agent_session`) → `{kind: session, name, ...}` plus
   the root's `artifact_dir`/`timestamp` (and `project_name`);
3. **named agent** (`find_named_agent`) → `{kind: agent, name, ...}` plus that
   turn's `artifact_dir` (or `{kind: proc, ...}` for monitor members);
4. **standalone proc** → `{kind: proc, name, proc_id}`;
5. otherwise `{kind: name, name}` — a bare-name fallback.

The critical point: **steps 2 and 3 pin different things.** A `session` pin
captures the session *root* and is later evaluated as a whole generation
(descendants chained from the root at check time). An `agent` pin captures
*one artifact directory* — one turn. And step 2 only fires when the name is a
plan-chain/agent-session name; an ordinary single agent, or a name that only
matches one concrete turn artifact, falls through to step 3. Which branch fires
depends on what existed at the moment `16h.f0` launched — it is not written
anywhere in the prompt.

### 1.4 Release requires both channels to resolve

`dependency_resolution_status`
(`src/sase/core/wait_dependency_resolution/_resolution.py`, lines 33–80)
evaluates `wait_identity_deps`, then `wait_fork_sources` (via
`fork_source_status`), then plain `wait_names` (via `is_resolved`), accumulating
`blocked_on`. A single unresolved channel blocks the release. The runner
evaluates this up front (`resolve_initial_wait_release`) and re-evaluates the
recorded `waiting.json` marker on later polls
(`src/sase/axe/run_agent_wait_deps.py`), with a shared epic-follow release path
and a two-round freshness confirmation (§3.3).

### 1.5 Per-kind release semantics differ — this is the heart of the matter

`fork_source_status`
(`src/sase/core/wait_dependency_resolution/_index_fork_queries.py`, lines
72–117):

| Pinned kind | Releases when |
|---|---|
| `agent` | that one artifact is terminal: `is_done or is_failed` (lines 83–89) |
| `session`/`family` | the root's whole generation is done: `(session.is_resolved and session.is_done) or session.is_failed`, where `is_done` = *any* member done and `is_resolved` = handoffs-present *and all* effective members resolved (lines 91–105; aggregate built in `_index_queries.py` `agent_session_candidate_for_root`, lines 287–338) |
| `clan` | all members of the pinned generation terminal (lines 106–111) |
| `proc` | proc status terminal (lines 112–113) |
| `name` fallback | name resolves (`is_resolved`) *or* a terminal blocker exists for the name — i.e. **a failed parent also releases the waiter** (lines 166–182) |

Note the last row: terminal *failure* releases fork waits by design (see also
`test_settled_failed_session_releases_fork_wait` in
`tests/test_wait_dependency_slot_queued_session_members.py`). "Parent failed"
is a second, independent early-start vector — worth ruling out when diagnosing
any specific incident.

## 2. Why `16h.f0` most likely started before `16h` finished

Assembling §1, the mechanism that fits best is **single-turn pinning**:

1. At `16h.f0` launch, `fork_wait_dependency("16h")` did not find a clan or an
   agent session for `16h` (e.g. `16h` is not a plan-chain session name —
   `find_agent_session` in `src/sase/agent/names/_lookup_groups.py` only
   considers plan-chain/agent-session metadata, lines 317–331), so it pinned
   `{kind: agent}` to the one `16h` artifact that existed then — the
   currently running turn.
2. The `agent`-kind release fires on that artifact's terminal marker alone.
   When that turn finished (success *or* failure), the fork-source channel
   resolved.
3. The plain-name channel (`is_resolved("16h")` in `_index_queries.py`, lines
   370–419) takes the newest candidate across the clan/session/workflow/named
   buckets *for the literal name `16h`*. If `16h`'s continued work ran as a
   follow-up turn under a different agent name (gate/monitor follow-up, shell
   handoff, retry, or next session member such as a `--code`-style member
   name), neither channel covers it — both point at the finished turn.
4. Both channels resolved → `16h.f0` started while the logical `16h` effort
   was still going.

Secondary vectors to rule out, in rough likelihood order:

- **Parent-turn failure.** Failure releases both the `agent`-kind channel and
  the name fallback. Check `16h`'s `done.json` outcome.
- **Manual release.** A TUI run-now (`unwait`) writes `ready.json` and
  releases unconditionally (`read_ready_result`, `run_agent_wait_deps.py`
  lines 379–407). Check for `released_by`/`unwait` in the marker.
- **Session-handoff race (unlikely by design).** For a true `session` pin, the
  aggregate is rebuilt live from the index (descendants chained from the
  pinned root, `_agent_session_chain`, `_index_entities.py` lines 342–363),
  and `confirm_dependency_resolution` (`_confirmation.py`) re-reads membership
  for up to two rounds specifically because "a shell successor is created
  before its predecessor writes the terminal marker." A successor appearing
  after confirmation is therefore unlikely — the design already closes the
  obvious race. This is evidence *for* the granularity explanation over the
  race explanation.
- **Parked-member exclusion (session pins only).** Session aggregates exclude
  dependency-parked members (`_aggregate_candidates`, `_index_entities.py`
  lines 434–460) while keeping slot-queued ones. A session whose next member
  is parked behind its own barrier can read as resolved+done. Narrow, but
  real: "session finished" and "session has no more *runnable* members" are
  not identical.

### How to confirm what happened to `16h`/`16h.f0`

The child's recorded wait state is authoritative. Inspect `16h.f0`'s
`agent_meta.json` / `waiting.json`:

- `wait_for_fork_sources[0].kind` — `agent` confirms single-turn pinning;
  `session` points at one of the secondary vectors instead.
- `wait_for_fork_sources[0].artifact_dir` / `timestamp` — which exact turn was
  pinned.
- `16h`'s turn artifacts' `done.json` outcomes and timestamps vs `16h.f0`'s
  launch timestamp — establishes whether release coincided with one turn's
  completion while later `16h`-lineage artifacts exist.

## 3. Critique of the proposed `target=<target>` input

### 3.1 What the proposal gets right

- The gap is real and worth fixing. Granularity today is emergent (whatever
  identity existed at launch), invisible (not recorded in the prompt), and
  asymmetric with history: a `session`-kind fork injects the whole session's
  transcripts (`_sources.py` `_resolve_fork_source` returns all session
  members) while an `agent`-kind fork injects one turn — so author intent
  about "resume this work" vs "resume this turn" is already load-bearing and
  already inexpressible.
- The tale-gate coder case is the right motivating consumer: gate-launched
  coders (`_coder_branch` in `src/sase/plan_gate_turn/create.py`, "Implement
  the approved plan") inherit session continuation semantics, and wanting to
  say "wait for the session" vs "wait for this turn" there is legitimate.
- `session` as the default is correct — but for a stronger reason than taste
  (see adjustment 2).

### 3.2 Required adjustments

1. **The "same type as model names" parenthetical is wrong — use a real
   `enum`, not the model named-type.** Per the macros memory note, input
   types are scalars plus `enum`+`choices` plus builtin
   `agent`/`model`/`effort` (plugin types aside). Model-typed inputs go
   through `classify_model_value` via `named_type == "model"`
   (`src/sase/macro/models.py`, `validate_and_convert`); they are open-ended
   model names, not a closed choice set. The correct precedent is the closed
   `enum` with `choices:` in `src/sase/macros/pr.yml` (`status`: wip/draft/
   ready), validated through `check_input_value`. `target` should be
   `type: enum` with `choices: [{value: session, ...}, {value: turn, ...}]`.
2. **Default `session` is a compatibility requirement, not a preference.**
   `fork_wait_dependency` already prefers `session` whenever a session
   exists, so default-`session` preserves today's resolution everywhere and
   makes `turn` a pure opt-in. State this as the compat argument. Also define
   the fallback explicitly: for names with no session notion (plain agents,
   procs, `@tribe` refs, bare-name fallbacks), `session` ≡ `turn` ≡ current
   behavior — the qualifier is accepted and ignored. For clans, define
   whether `turn` means "newest member artifact" (recommended) or is likewise
   a no-op; do not leave it undefined.
3. **The qualifier must live in the `#fork` reference syntax, not only in
   `fork.yml`.** This is the structural catch: the implicit wait is derived
   from the *raw prompt text* (`fork_agent_names` over the prompt string) at
   runner time, while `fork.yml`'s inputs only take effect when the macro
   renders inside the child's prompt assembly. A `target:` input declared in
   YAML but not carried in the reference text can never reach
   `resolve_wait_state`. Concretely, the scanner
   (`_RESUME_REF_RE`/`_resume_reference_arguments` in `_resume.py`, lines
   22–33 and 301–317) currently parses `#fork:16h` and `#fork(...)` paren
   args but discards named args (`positional, _ = parse_args(...)`). The
   macro arg grammar already supports `#name(k=v)` (per the macros memory
   note), so `#fork(16h, target=turn)` is the natural spelling — but the
   scanner, `fork_agent_names` (which returns bare names today), every
   consumer of it (`sole_resume_agent_name`, resume-name allocation,
   `resolve_wait_state`), and history resolution must all learn the
   qualifier. This is a small but cross-cutting change; sizing it as "one new
   input" understates it.
4. **Bind history injection and the wait to the same qualifier.** Today both
   already branch on the resolved kind (whole-session transcripts vs one
   turn; whole-generation wait vs one-artifact wait). If `target=turn`
   narrowed only the wait while history still injected the whole session (or
   vice versa), the child would see context for work it didn't wait for, or
   wait for work it can't see. `target` should mean "this fork resumes the
   turn" vs "this fork resumes the session" in both layers:
   `resolve_agent_chat_sources`/`fork_history.main` and
   `fork_wait_dependency`.
5. **Keep failure-release semantics unchanged and say so.** Both granularities
   release when the pinned scope settles failed (settled-failed session;
   failed turn; terminal-blocker fallback). `turn` must not become "wait for
   success" — that would strand waiters on failures and contradict the
   established settled-failure rule. Document it; do not redesign it here.
6. **Scope the tale-gate/TUI half explicitly.** The TUI/CLI wait spec
   (`src/sase/wait_spec.py`: agent names plus `bead=`/`hood=`, edited in
   `approve_options_modal.py`) has the same expressiveness gap for explicit
   waits, and `%wait` (per the macros note, dependencies and time floors
   only) likewise has no granularity qualifier. Either extend the same
   qualifier vocabulary to wait specs (`turn=<name>` alongside `<name>`,
   phase 2) or explicitly defer it — but don't imply the fork-macro input
   covers the coder-options case, because gate-launched coder waits travel
   through the wait-spec path, not the fork-macro path.

### 3.3 Alternatives considered

- **Fix the identity model instead of adding a flag** (make gate/monitor
  follow-ups and retries first-class session members so every fork of `16h`
  is session-kind). More principled — it would also fix history injection
  and the TUI's session views at once — but it is a much larger change to
  plan-chain/session identity with wide blast radius. The qualifier is the
  right incremental step; the identity work can follow if the same confusion
  recurs.
- **Wait-spec-only qualifier, no fork-macro change** (e.g. `%wait(turn=16h)`).
  Cleaner layering (granularity is a property of waits), and it covers the
  tale-gate coder case directly. But it leaves fork-implied waits — the
  actual `16h.f0` mechanism — still inexpressible. Since fork-implied waits
  are the reported pain, the fork reference needs the qualifier regardless;
  wait-spec parity then becomes phase 2 reusing the same vocabulary.
- **Do nothing; document "fork waits for the turn."** Rejected: it would
  enshrine whichever accidental kind won the launch-time race as the
  contract, and it contradicts the session-kind behavior that already exists
  and that session authors rely on.

## 4. Recommended solution

**Add `target: session | turn` (enum, default `session`) to the fork
reference, the `fork` macro declaration, wait pinning, and history
injection — one qualifier, four touchpoints, then wait-spec parity.**

### Phase 1 — fork granularity (the `16h.f0` fix)

1. **Syntax.** `#fork(16h, target=turn)`; `#fork:16h` and `#fork(16h)` keep
   meaning `target=session`. Reject other values at parse time with the
   enum's validation error (same UX as `pr.yml`'s `status`).
2. **Scanner** (`src/sase/agent/names/_resume.py`): stop discarding named args
   in `_resume_reference_arguments`; return `(name, target)` pairs (new
   function alongside `fork_agent_names`, e.g. `fork_targets`, keeping
   `fork_agent_names` behavior-stable for existing callers); validate
   `target` against `{session, turn}`; ensure resume-name allocation, sole-
   parent naming, and fenced/disabled-region handling ignore the qualifier.
3. **Macro declaration** (`src/sase/macros/fork.yml`): add the `target` enum
   input (`choices: session/turn`, default `"session"`, with descriptions
   stating the wait+history meaning) so macro validation, completion, and
   docs agree with the scanner. Keep `name` as-is.
4. **Wait pinning** (`src/sase/agent/fork_waits.py` + call site
   `resolve_wait_state` in `run_agent_directives_flow.py`): `target=session`
   → today's `fork_wait_dependency` exactly; `target=turn` → pin the single
   newest existing artifact for the name (member turn if it is a session/clan
   member, else the named agent/proc artifact) as an `agent`-shaped
   `{kind, name, artifact_dir, ...}` dep, evaluated by the existing
   single-artifact terminal rule. No new release rule needed — reuse
   `_candidate_terminal_for_fork`.
5. **History coherence** (`_agent_chat_from_name_sources.py`,
   `fork_history.main`): `target=turn` injects only that turn's transcript;
   `target=session` keeps today's whole-session (or whole-clan) injection.
6. **Compat guarantee:** default `session` reproduces today's resolution
   everywhere (session preferred where one exists; single artifact where
   none exists). `turn` only narrows waits that would otherwise be
   session-wide — it can never newly strand a waiter that resolves today.
   State this precisely in the change's docs: for non-session names,
   `turn` ≡ `session` ≡ today.

### Phase 2 — explicit-wait parity (the tale-gate coder case)

7. Extend `parse_wait_spec`/`format_wait_spec` (`src/sase/wait_spec.py`) with
   the same qualifier (proposed spelling `turn=<name>`, keeping bare `<name>`
   at current name semantics), surface it in the approve-options wait editor
   (`approve_options_modal.py`), and plumb it through `%wait` directive
   extraction to `wait_names`-vs-pinned-dep the same way phase 1 does.
   Reuse the phase-1 vocabulary and validation messages verbatim.

### Phase 3 — verification

8. Unit tests: scanner qualifier parsing (colon/paren forms, invalid value,
   fenced-block exclusion); `fork_wait_dependency` forcing (session name +
   `target=turn` pins the member artifact; non-session name + either target
   unchanged); index-level release test mirroring
   `tests/test_wait_dependency_slot_queued_session_members.py` —
   `target=turn` releases when the pinned turn completes while a session
   sibling is still running, `target=session` stays blocked.
9. Chop/runner-level test: fork-implied waiter with `target=turn` vs
   `target=session` against a two-turn session fixture, asserting release
   timing through `resolve_initial_wait_release` + `waiting_marker_
   dependencies_resolved`, including the settled-failure release for both.
10. Wait-spec round-trip test (`turn=16h` survives parse→format→parse) and TUI
    editor test if the modal has harness coverage.
11. Docs: update the fork macro description, the wait-spec reference, and the
    tale-gate coder-options help to define session vs turn, the default, the
    no-session fallback, and the unchanged failure-release rule.

## 5. Open questions and risks

- **Colon-form spelling.** `#fork:16h` cannot carry a qualifier without new
  punctuation (`#fork:16h!turn`? `#fork:16h/target=turn`?). Restricting the
  qualifier to the paren form (`#fork(16h, target=turn)`) avoids grammar work
  but creates two spellings with different power — acceptable (mirrors
  `#name:arg` shorthand vs `#name(k=v)` full form), but say so explicitly.
- **Multi-parent forks.** `#fork(a, b, target=turn)` — does the qualifier
  apply per-reference or per-invocation? Recommend per-invocation (one
  `target` for all parents in the call); per-parent targeting can be done
  with repeated `#fork` references. Document the choice.
- **`turn` on a clan.** Recommended above: newest member artifact. Alternative
  (no-op, clan waits are already generation-scoped) is defensible but leaves
  a silent qualifier — worse. Pick newest-member and test it.
- **Survivorship of the pinned turn.** A `turn` pin names an artifact that
  could be wiped by healer forced-reuse; note that `_forward_identity_deps`
  (`run_agent_wait_deps.py`) already remaps wiped identity deps to
  replacements — confirm the `turn`-shaped dep flows through that path (it
  carries `artifact_dir`, so it should) and test it.
- **The deeper identity question from §3.3 stands.** If follow-up turns
  routinely escape their parent's session identity, granularity flags treat
  the symptom per-launch. Worth one follow-up bead: audit whether `16h`'s
  continuation *should* have been session membership, independent of this
  change.

## 6. Diagnostic appendix: what to check for the `16h` incident specifically

1. `16h.f0`'s `agent_meta.json`: `wait_for_fork_sources` — `kind`,
   `artifact_dir`, `timestamp`. `kind: agent` confirms §2's primary
   mechanism; `kind: session` redirects to the secondary vectors.
2. `16h`-lineage artifacts sorted by timestamp against `16h.f0`'s launch:
   one `done.json` at ~release time plus later same-lineage artifacts
   confirms "released on one turn while the lineage continued."
3. `done.json` outcomes along that lineage: any non-success outcome implicates
   the failure-release rule instead of (or as well as) granularity.
4. `ready.json` on `16h.f0` (`released_by`/`unwait`): rules manual release
   in or out.
