# Making `%auto` Powerful: Permissions-Oriented Redesign Research

**Swarm suffix:** `__mus` (independent researcher report; no peer reports consulted)
**Date:** 2026-10-07
**Question:** The `%auto` directive is currently the main practical way to tune
"permissions" for a sase agent, but it is not configurable or intuitive. How
should we make it much more powerful? Is that a good idea, and if so, how?

## TL;DR recommendation

Yes, improve `%auto`, but **do not turn `%auto` into a full permissions system
in one step**. That conflation is the biggest risk in the plan as stated.

Recommended two-layer solution:

1. **Short term — structured `%auto` gate policy (this epic):** keep `%auto`'s
   job exactly as it is today (automatic *gate resolution*), but replace the
   single opaque `:arg` with typed per-kind keyword policy plus global caps,
   e.g. `%auto(plan=tale, question=ask, sudo=off, budget=5)`. Back-compat shims
   keep `%auto`, `%auto:plan`, `%auto:tale`, `%auto:epic` working. Default-deny
   for privileged kinds. Central validation with one vocabulary, not one
   vocabulary per adapter.
2. **Longer term — separate execution permissions (different epic):** real
   tool/filesystem/network/command sandboxing, provider `bypass_permissions`
   alignment, and any yolo-mode config belong in a *different* surface
   (`%perm`, config, or CLI flags) — not inside `%auto`. `%auto` answers "who
   clicks approve"; execution permissions answer "what the agent may do after
   approval". Merging them produces a footgun: auto-approving a plan whose
   coder can run anything.

The rest of this report justifies that split, documents how `%auto` actually
works today (from source), critiques the "more powerful `%auto`" plan, lists
requirement adjustments, and sketches the concrete grammar, validation,
TUI/completion, propagation, audit, and migration design.

## 1. What `%auto` is today (source-grounded)

### 1.1 Parser: one bit + one opaque string

- `%auto` / alias `%a` is a known directive
  (`src/sase/macro/_directive_types.py`: `_KNOWN_DIRECTIVES`, `_DIRECTIVE_ALIASES`).
- The parser retains an **arbitrary raw argument** and does no global enum
  check. `resolve_auto_mode` maps bare/empty/`true` to `"plan"`;
  `resolve_auto_argument` returns `(enabled, argument)` where bare is
  `(True, None)` (`src/sase/macro/_directive_values.py`).
  So `%auto:foo` parses fine and reaches the gate adapter, which may then
  reject it. Completion-only suggestions (`plan`, `tale`, `epic`) are in
  `AUTO_COMPATIBILITY_ARGUMENT_SUGGESTIONS` — explicitly *not* an allowlist.
- `PromptDirectives` carries three fields: `auto_mode` (compat rendering),
  `auto_enabled` (presence), `auto_argument` (opaque raw string)
  (`src/sase/macro/_directive_types.py`).
- `set_prompt_auto_mode` canonicalizes only `plan → %auto`, else `%auto:{mode}`
  (`src/sase/macro/_directive_edit_wait.py`). `AutoMode = Literal["plan",
  "tale", "epic"]`.
- Duplicate `%auto` (including `%auto` + `%a`) raises `Duplicate directive
  '%auto'`; removed spellings (`%plan`, `%approve`, `%tale`, `%epic`) stay
  literal (see `tests/test_directives_flags.py`).

Documented contract (`docs/macros.md`, "Auto Directive" + directive table):
`%auto` = "Request automatic gate resolution; an optional argument is
gate-owned". Bare = each adapter's default automatic choice.

### 1.2 Gate adapters: three policies, twelve kinds

`src/sase/notification_gates/adapters.py` registers 12 `GateAdapter`s, each
with an `auto_policy`:

| policy | kinds | behavior of `resolve_auto_selection` |
|---|---|---|
| `approval` | `plan`, `epic_plan` | allowlist per kind: tale-tier `{None,"",plan,tale}`, epic-tier `{None,"",epic,epic_plan}`; tier-changing combos rejected (`%auto:epic` on a tale, etc.) |
| `first` | `question` | only `{None,"",first}` accepted; selects primary-branch default (first listed option per question) |
| `forbidden` | `sudo`, `launch`, `hitl`, `task_triage`, `bead_snooze`, `flag_triage`, `bead_stale_cleanup`, `plugins_required`, `custom` | any `%auto` raises `auto_not_supported` |

`GateSpec.auto` is `{enabled: bool, argument: str|null}` with strict shape
validation (`src/sase/notification_gates/model_request.py::_GateAuto`).
Creation (`src/sase/notification_gates/service.py::create_gate`): if
`spec.auto.enabled`, **no notification is published** and `_resolve_auto_gate`
runs `execute_gate_selection(..., source="auto_resolution")` synchronously,
settling the gate-turn inline with `creator_live=True` (no follow-up launch,
no claim disposal). Otherwise a notification is appended and the result is
`auto_state="disabled"`.

### 1.3 Plan vs question plumbing (two different transports)

- **Plan gates:** `build_plan_approval_gate_spec(..., auto_enabled,
  auto_argument)` validates tier via `validate_plan_auto_argument`
  (`src/sase/plan_gate.py`, `src/sase/_plan_gate_metadata.py`). Allowed sets
  are tiny and tier-locked. `%auto:tale` on an epic (and vice versa) is a
  `GateError invalid_auto_argument`.
- **Question gates:** `user_question_gate_spec(..., auto: bool)` takes only a
  bool (`src/sase/user_question_actions.py`); the runner passes
  `auto=is_auto_approve_active()` (`src/sase/axe/run_agent_exec_questions.py`).
  So **question auto has no argument transport at all** — `%auto:foo` vs bare
  `%auto` are indistinguishable to a question gate today, despite the docs
  saying the question adapter "also accepts `first`". (This bool-vs-string
  mismatch is a real wart the redesign must fix.)
- **Propagation is four-sourced:** env (`SASE_AGENT_AUTO_APPROVE`,
  `SASE_AGENT_AUTO_APPROVE_PLAN_ACTION/ARGUMENT` and `AUTO_PLAN_*` aliases),
  `agent_meta.json` (`approve`, `auto_approve_plan_action/argument`), the
  launch wire (`auto_enabled/auto_mode`), and `is_auto_approve_active()`
  (`src/sase/main/plan_approve_handler.py`). Semantics: *any* raw argument
  present → active; `approve` bool → `"approve"` sentinel.
- **TUI:** `action_toggle_auto_approve` only toggles bare `%auto` on/off via a
  `set_auto_mode` prompt rewrite + meta patch (`approve: True`,
  `auto_approve_plan_action` cleared); it cannot express tale/epic/first and
  rewrites the prompt rather than storing policy (`src/sase/ace/tui/actions/agents/_approve.py`).
  Display chips show `auto_approve_plan_action or "plan"`.

### 1.4 What `%auto` is *not*

- Not a tool permission: no filesystem/network sandbox, no command allowlist.
  `%if::` predicates and `%proc` run "with the SASE process's filesystem and
  network permissions" with only home-scrubbing, explicitly "not a sandbox"
  (`docs/macros.md`). Provider `bypass_permissions` (tmux agent config) is a
  separate, provider-level concern (`src/sase/config/tmux_agent.py`,
  `src/sase/tmux_agent/launch_spec.py`).
- Not scoped: no per-question, per-plan, count/time budget, or expiry.
  Launch-time consumption only; `%repeat` serial chaining, `%wait`, queue
  admission, and holds (`%hold`, Rust-validated via
  `src/sase/macro/hold_directive.py`) are orthogonal.
- Attempted live probing of `extract_prompt_directives` in this checkout
  failed with `RuntimeError: sase_core_rs content-layout wire is stale:
  expected schema >= 7, got 5`, so behavioral claims above rest on source
  reads, not a runtime probe. Re-verify after the `sase-core-revision.txt`
  pin moves (see `docs/rust_backend.md` and AGENTS §1.3).

## 2. Critique: is "much more powerful `%auto`" a good idea?

**Good core, risky framing.** The instinct is right — `%auto` today is the
only knob and it is blunt — but the request as worded invites three mistakes:

1. **Conflating gate auto-resolution with execution permissions.** Today
   `%auto` decides *whether a human clicks*. Permissions decide *what the
   agent can do unsupervised*. Users asking for "tune permissions via %auto"
   usually want both ("auto-approve plans but still ask before `rm -rf` /
   push / sudo / external publish"). A single `%auto:...` string that both
   answers gates and grants capabilities will be misread as a sandbox. It is
   not one. The design must name two layers and refuse to let `%auto` grant
   capabilities it cannot enforce. This is the #1 adjustment (see §3.1).
2. **Per-adapter vocabularies don't compose.** Each adapter owning validation
   sounded extensible but produced the current confusion: `plan` vs
   `epic_plan` vs `first` vs `forbidden`, compat aliases (`tale` ≈ approve a
   tale?), and the question-gate bool transport that drops the argument. "More
   values" without a central schema multiplies this. Power must come with
   *one* documented grammar validated in one place, with adapters declaring
   support — not inventing syntax.
3. **All-or-nothing + invisible = mistrust.** Bare `%auto` today means "auto
   plans AND auto-answer every question with the first option". There is no
   way to say "auto plans, ask me questions" (arguably the most useful
   policy), no budget ("at most N auto-resolutions"), no TTL, no audit trail
   distinguishing auto vs human decisions in the TUI, and error surfacing is
   late (parse succeeds, gate creation fails). More power without
   visibility/audit/deny-by-default will reduce adoption, not increase it.

Secondary critiques:

- **Intuitiveness problem is real but underspecified.** `%auto:tale` vs
  `%auto:epic` vs `%auto:plan` requires knowing SDD tier lore; `%a` collides
  mnemonically with approve/all/agent; plus/colon/paren spellings (`%auto`,
  `%auto+`, `%auto:plan`, hypothetically `%auto(...)`) are not uniformly
  documented per directive. Any redesign needs a TUI completion + `--explain`
  story, not just grammar.
- **Do not break the three compat spellings.** `%auto`, `%auto:plan`,
  `%auto:tale`, `%auto:epic` are in docs, memory (`sase/memory/macros.md`),
  tests, and user muscle memory (typical prompt: `+sase %auto #pr:…`).
  Keep them as frozen shims with defined translations.
- **Rust boundary.** Directive lexing/collection already straddles Python and
  `sase_core_rs` (content-layout wire, `%hold` validation). A richer `%auto`
  grammar that needs TUI completion, LSP completion, and Python validation
  should define the schema once (Rust-owned if shared behavior, per AGENTS
  §1.3 litmus: a web app/CLI/editor would need identical validation) and
  project it to completions — not three hand-synced enums.

## 3. Requirement adjustments (explicit deltas to the ask)

- **[CHANGE] Split the epic in two.** Epic 1: structured `%auto` gate policy
  (this report). Epic 2 (separate): execution/tool permissions. Do not accept
  "powerful `%auto`" as done when only gate policy ships, and do not let Epic
  1 grant execution capabilities.
- **[CHANGE] Default-deny, not default-allow, for new surface.** Any kind that
  is `forbidden` today stays forbidden under bare `%auto` and under compat
  shims. New auto-ability per kind is opt-in per kind (`sudo=off` default,
  `launch=off` default, etc.), never implied by "more powerful".
- **[CHANGE] One grammar, central validation.** Replace "adapter owns
  validation" with: central `%auto` policy parser + per-kind capability
  declaration (`supports: {plan: [...], question: [...], sudo: []}`). Adapters
  keep *selection semantics* (which option is "first"/"approve") but not
  syntax.
- **[ADD] Negative and scoped requirements.** The spec must cover: explicit
  `off` per kind; `ask` (force-manual even when a global auto is on);
  budgets (`count=`, `ttl=`); `on_error=` (fail-open vs fail-closed);
  conflict errors at *parse/launch* time, not gate-creation time; audit bit
  (`source=auto_resolution` already exists — surface it in TUI + journal).
- **[ADD] Observability requirement.** Every auto-resolution must be
  distinguishable in TUI/notifications/journal from a human decision, and
  `%auto --explain` / `sase plan --dry-run` must preview what *would* be
  auto-resolved.
- **[DROP] Do not promise "intuitive" via syntax alone.** Require completion,
  TUI toggle parity (every policy value settable without hand-typing), docs
  with tier-blind examples, and a migration table. Syntax without tooling is
  not intuitive.
- **[OUT OF SCOPE]** Provider permission modes (`bypass_permissions`,
  yolo/approval CLI flags), filesystem/network sandboxing, sudo policy
  itself, LaunchApproval semantics change. `%auto` may *address* those gates
  (still default-off) but does not *redefine* them.

## 4. Design space considered

| option | sketch | pros | cons |
|---|---|---|---|
| A. Structured `%auto(...)` kwargs | `%auto(plan=tale, question=ask, sudo=off, count=5, ttl=2h)`; bare `%auto` = frozen preset | back-compat; one directive; completion-friendly; matches `%id(...)`/`%wait(...)` kwarg idiom | long prompts; still one directive doing a lot |
| B. New `%policy`/`%perm` directive + `%auto` shim | `%auto` stays bool-ish; `%policy(gates=…, exec=…)` owns power | clean separation of gate vs exec | two directives to learn; migration burden; still needs same grammar |
| C. Config/CLI only (`sase.cfg`, `--auto …`) | no prompt syntax change | good for durable prefs | invisible per-launch; doesn't travel with the prompt/patch; breaks `+sase %auto …` idiom |
| D. Natural-language "auto everything safe" | agent judges safety | zero syntax | un-auditable; safety judgment by the party being supervised |

Recommendation: **A now, with B's separation enforced by scope** (A's grammar
covers *gates only*; exec policy is a named future surface, not extra `%auto`
keys). C as a complement (persist presets), never the primary. D rejected.

## 5. Recommended solution (concrete)

### 5.1 Grammar (gates only)

Canonical form: `%auto` + optional paren kwargs (colon shim retained):

```
%auto                                          # preset: plan default + question ask? (decision below)
%auto:plan | %auto:tale | %auto:epic           # frozen compat shims
%auto(plan=<v>, question=<v>, sudo=<v>, launch=<v>, hitl=<v>,
      triage=<v>, count=<N>, ttl=<dur>, on_error=<v>)
```

Per-kind values (central enum; kinds without support reject non-`off`/`ask`):

- `plan`: `off | ask | approve | tale | epic` (tier-conflict still validated
  against authored tier at spec build, but error surfaces at parse/launch).
- `question`: `off | ask | first | first+N`? Start with `off | ask | first`.
  (`first` = today's behavior; `ask` = force manual — the missing useful
  value.)
- `sudo | launch | hitl | triage(*) | custom | plugins_required | *_cleanup`:
  `off | ask` only in Epic 1 (no auto-approve of privileged kinds yet; the
  grammar reserves the slot so `sudo=approve` fails closed with
  `auto_not_supported`, not silently).
- Globals: `count=<positive int>` (max auto-resolutions for this launch, then
  fall back to manual), `ttl=<duration>` (e.g. `30m`, `2h`, cap 12h mirroring
  hold-TTL conventions), `on_error=fail-closed | fail-open-manual` (default
  fail-closed: ambiguous policy blocks launch with a clear error).

Preset decision needed (product call, default recommended): bare `%auto` keeps
today's behavior (`plan=approve-default-tier, question=first`) for back-compat,
**but** the TUI toggle and docs steer new users to explicit
`%auto(plan=approve, question=ask)`. Alternative (breaking): bare `%auto` =
`question=ask`. Do not change bare semantics silently; if changed, gate behind
a `sunset` flag per `sase/memory/sase_flags.md`, not a stealth edit.

Plus/colon/paren normalization: accept `%a(...)` alias; reject mixed
`%auto:plan(...)` with a targeted error. Bare `%a` = bare `%auto`.

### 5.2 Validation architecture

- Single `%auto` policy parser owned near `src/sase/macro/_directive_values.py`
  (or Rust core if completion parity demands it — decide via AGENTS §1.3
  litmus; either way, TUI/LSP completions generated from the same table as
  `AUTO_*` suggestions are today).
- `GateSpec.auto` gains a structured `policy` field alongside legacy
  `{enabled, argument}` during migration; `resolve_auto_selection`
  (`adapters.py`) becomes a thin dispatch to per-kind selection functions
  taking the *parsed* policy, never raw strings. Question gate transport
  becomes string-or-structured (fix the `auto: bool` loss in
  `user_question_gate_spec`).
- Errors at earliest point: unknown key/value → `DirectiveError` at parse;
  kind-unsupported value → `GateError invalid_auto_argument` at spec build
  with the same message in `sase plan --dry-run`; tier conflict likewise.
  No "parses, then fails at 2am during gate creation".
- Budgets enforced in `notification_gates/service.py::_resolve_auto_gate`
  (counter + TTL scoped to the launching agent/session; journal it).

### 5.3 Propagation, TUI, completion, audit

- Collapse four propagation sources to one resolved policy object before
  launch (env, `agent_meta.json`, wire, directive — precedence documented;
  today any-raw-argument-wins is too subtle). Keep env/meta keys working as
  compat (map to policy fields), log the resolved policy at launch.
- TUI: replace the bare on/off toggle with a policy editor (per-kind
  dropdowns + count/TTL + preview line); completion rows per
  `docs/macros.md` directive table extended with the new kwargs; header chip
  shows compact policy (`auto:plan✓ q:ask`) not just `plan`; auto-resolved
  gates render an `auto` badge (wire `source="auto_resolution"` already
  exists — surface it).
- Audit: journal every auto-resolution with policy snapshot, selected options,
  remaining budget; `sase tool show` / notification history distinguishes
  auto vs human. Required for trust.
- `sase plan propose --dry-run` / prompt `--explain` prints: resolved policy,
  which upcoming gates would auto-resolve, which would stay manual, and why
  (e.g. "sudo: forbidden → manual").

### 5.4 Migration

1. Ship parser accepting new kwargs + old shims; old shims translate to
   policy (`%auto:tale → plan=tale, question=<bare default>` — document the
   question default explicitly, that ambiguity is today's bug).
2. Fix question transport (bool → policy) behind a `beta` flag; both-states
   tests per `sase_flags.md`.
3. TUI toggle + completions + audit badge.
4. Docs + memory update (`docs/macros.md` Auto Directive section,
   `sase/memory/macros.md` row, directive table kwargs).
5. Follow-up epic: execution permissions surface; `%auto` docs link to it
   with "what `%auto` does not grant" box.
6. Tests: parse table (every key/value, aliases, duplicates, mixed-form
   errors), per-kind adapter matrix (allowed/rejected), budget/TTL expiry,
   fail-closed errors, compat-shim equivalence, TUI/completion parity, audit
   badge presence.

## 6. Risks and open questions

- Bare-`%auto` question default (`first` vs `ask`) is the one breaking-change
  landmine; needs an explicit product decision + sunset flag if changed.
- Budget/TTL scope (per-agent vs per-session vs per-patch) needs the gate-turn
  owners' input; wrong scope makes budgets either useless or surprising.
- Richer `%auto` increases prompt length; consider named presets in config
  (`auto_presets: {cautious: "plan=approve,question=ask", ...}` +
  `%auto:cautious`?) — but presets are a second feature; don't block Epic 1
  on them.
- Security review: any move of a kind from `forbidden` to auto-capable (even
  `hitl`/`triage`) needs a threat model per kind, not a blanket "more auto".

## 7. Sources consulted (independent)

Code: `src/sase/macro/_directive_types.py`, `_directive_values.py`,
`_directive_extract.py`, `_directive_edit_wait.py`, `directive_edit.py`;
`src/sase/notification_gates/adapters.py`, `service.py`, `model_request.py`
(`_GateAuto`, `GateSpec`), `models.py`; `src/sase/plan_gate.py`,
`src/sase/_plan_gate_metadata.py`; `src/sase/user_question_actions.py`;
`src/sase/question_gate_turn/create.py`; `src/sase/gate_turn/transaction.py`;
`src/sase/axe/run_agent_exec_questions.py`, `run_agent_directives_extract.py`;
`src/sase/main/plan_approve_handler.py`, `plan_propose_handler.py`;
`src/sase/ace/tui/actions/agents/_approve.py`; `src/sase/config/tmux_agent.py`.
Docs/memory: `docs/macros.md` (Auto Directive §, directive tables, `%if`/`%proc`
sandbox notes), `docs/axe.md`, `sase/memory/macros.md`, `sase/memory/sase_flags.md`.
Tests: `tests/test_directives_flags.py`. No swarm peer reports or transcripts
consulted.

*Report: independent `__mus` contribution; synthesis left to the lead researcher.*
