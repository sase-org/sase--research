---
create_time: 2026-10-07
updated_time: 2026-10-07
status: draft
tags:
  [
    research_swarm,
    percent-auto,
    notification-gates,
    hitl,
    permissions,
    directives,
    sase-core,
  ]
---

# Make `%auto` a host-owned HITL policy, not a more powerful prompt toy

**Question.** `%auto` is the practical way to tune agent permissions today, because
SASE agents do not yet have real provider-level permissions. It is not very
configurable or intuitive. What is the best way to make it more powerful? Is that
a good idea, or is a different approach better?

**Researcher.** grk (`research.41.grk`). Independent report. I did not read peer
reports from this swarm.

**Scope.** Current `%auto` contract and storage; gate-adapter auto policies; TUI `A`
key; provider `bypass_permissions`; Claude Code / Codex permission models as
comparisons. Recommendation for a design that SASE can implement without turning
the prompt into a privilege-escalation language.

## Bottom line

Making `%auto` "much more powerful" is the right *problem* and the wrong *shape*.

`%auto` is already SASE's real permission knob. Provider CLIs launch with
approval-bypass flags (`tmux_agent.bypass_permissions: true`, Grok
`--permission-mode bypassPermissions`, Claude `--dangerously-skip-permissions`,
Codex/OpenCode the same posture). Native plan/ask surfaces are stripped
(`--no-plan`, `--no-ask-user`) so `/sase_plan` and `/sase_questions` own HITL.
The only remaining human gate is SASE's notification-gate layer, and `%auto` is
how a launch says "resolve those gates without me."

That architecture is good. The directive as it exists is not:

- One opaque string, validated later by whichever gate kind happens to open.
- Three overlapping metadata fields (`approve`, `auto_approve_plan_action`,
  `auto_approve_argument`) plus five environment variables.
- Bare `%auto` means "approve the authored plan *and* pick the first answer on
  every question." `%auto:tale` / `%auto:epic` are documented as plan-only, but
  `is_auto_approve_active()` treats *any* stored argument as full auto, so the
  docs and the question path disagree.
- Nine of eleven gate kinds refuse automatic resolution entirely. There is no
  config profile, no per-kind verb, no parenthesized form, and no way to say
  "auto the plan, ask the questions."
- The TUI `A` key only toggles bare `%auto`. Launch-time `%auto:epic` is a
  one-bit on/off as far as the key is concerned.

**Do not** grow `%auto` into a free-form permission DSL, a per-tool allow/deny
language, or a way to auto-approve sudo / launch / custom gates from prompt
text. **Do** keep `%auto` as the launch-time selector for a *host-owned HITL
policy*, the same way `%final` only selects configured finalizer instances.

Recommended solution: named `auto.profiles` in config, a structured
`AutoPolicy` on the agent, additive `%auto(profile=…, plan=…, question=…)`
syntax that can only *tighten* a profile, privileged kinds remaining
adapter-forbidden, provider sandbox left on a later profile field.

## 1. What `%auto` is today

### 1.1 Launch-time directive

`%auto` / `%a` is a single-occurrence prompt directive. The parser keeps an
optional raw argument and does **not** apply a global enum. Bare `%auto`,
`%auto+`, and `%a` canonicalize to compatibility mode `"plan"`. Unknown
spellings such as `%auto:foo` are valid *syntax* and are handed to the gate
adapter, which may reject them.

Evidence:

- `src/sase/macro/_directive_values.py` `resolve_auto_mode` /
  `resolve_auto_argument`
- `src/sase/macro/_directive_types.py`: `auto_mode`, `auto_enabled`,
  `auto_argument`; `AUTO_COMPATIBILITY_ARGUMENT_SUGGESTIONS = ("plan", "tale",
  "epic")`
- sase-core `DirectiveMetadata` for `auto`: `syntax_forms: COLON_BARE_PLUS`,
  `keywords: &[]`, description "arguments are interpreted by the gate kind"
- `docs/macros.md` "Auto Directive"

The Rust completion contract only offers colon/bare/plus. Parenthesized
keywords are not part of the advertised syntax. That is the same shape `%hide`
has, not the shape `%queue` / `%hold` / `%final` have.

### 1.2 What the argument is supposed to mean

| Spelling | Documented effect |
| --- | --- |
| `%auto` / `%a` / `%auto:plan` | Default automatic choice per adapter. Tale plan → normal approval (approve+commit primary branch). Epic plan → epic approval. Question → first listed option. |
| `%auto:tale` | Plan-specific. Auto-approve and commit as an SDD tale, then launch the coder. Documented *not* to auto-answer questions. |
| `%auto:epic` | Plan-specific. Epic path. Documented *not* to auto-answer questions. |
| `%auto:foo` | Valid syntax. Plan adapter raises `invalid_auto_argument` if the authored tier does not allow it. Question adapter allows only `None` / `""` / `"first"`. |
| Launch / sudo / custom / … | Automatic resolution is rejected (`auto_not_supported`). |

Plan adapters also refuse *tier-changing* combinations: `%auto:epic` on a tale
plan, `%auto:tale` on an epic. That floor is correct and must stay.

### 1.3 How it is stored (the real mess)

Extraction writes a triad into `agent_meta.json`:

```text
%auto / %auto:plan  →  approve=true
                       (auto_approve_argument omitted; auto_argument is None)

%auto:tale          →  plan=true
                       auto_approve_plan_action="tale"
                       auto_approve_argument="tale"

%auto:epic          →  plan=true
                       auto_approve_plan_action="epic"
                       auto_approve_argument="epic"
```

`AgentInfo.approve` is `auto_mode == "plan"` only. Tests encode that as
"`%auto:epic` is plan-specific and does not enable full auto-approve" by
asserting `approve is False` and `"approve" not in meta`. They never assert
that questions stay manual.

Runtime readers then reconstruct intent from several sources, in different
orders:

- `get_auto_plan_approval_action()`: raw argument → env
  `SASE_AGENT_AUTO_APPROVE_PLAN_ACTION` / `SASE_AGENT_AUTO_PLAN_ACTION` → meta
  `auto_approve_plan_action` → boolean `SASE_AGENT_AUTO_APPROVE` / meta
  `approve`
- `get_auto_plan_approval_argument()`: env `SASE_AGENT_AUTO_APPROVE_ARGUMENT`
  / `SASE_AGENT_AUTO_PLAN_ARGUMENT` → meta `auto_approve_argument`
- `is_auto_approve_active()` (questions): **true if any raw argument is
  present**, or the boolean env, or meta `approve`

That last function is the contradiction. `%auto:epic` stores
`auto_approve_argument="epic"`, so `is_auto_approve_active()` is true, so a
later `/sase_questions` gate is created with `auto=True` and settles on the
first option. `docs/macros.md` says the opposite.

The TUI `A` key makes this worse: it toggles *bare* `%auto` only. Enabling
writes `approve=true` and `%auto`. Disabling strips `approve`,
`auto_approve_plan_action`, and `auto_approve_argument` together. A
launch-time `%auto:epic` becomes a one-bit switch.

Monitor follow-ups rebuild the prefix from the same triad
(`auto_launch_prefix` in `src/sase/monitor/continuation_delivery.py`), so the
ambiguity is inherited by every `%auto` chain, including `sase bead work`
phase and land segments, which inject bare `%auto` on every agent.

### 1.4 Gate-adapter auto policies

`GateAdapter.auto_policy` is a closed enum in
`src/sase/notification_gates/adapters.py`:

| Policy | Kinds | Behavior |
| --- | --- | --- |
| `approval` | `plan`, `epic_plan` | Interpret `plan`/`tale` vs `epic`/`epic_plan`; select the primary branch's `default_selected` options |
| `first` | `question` | Only `None`/`""`/`"first"`; first / default-selected primary branch |
| `forbidden` | `sudo`, `launch`, `hitl`, `task_triage`, `bead_snooze`, `flag_triage`, `bead_stale_cleanup`, `plugins_required`, `custom` | Always `auto_not_supported` |

The common gate request field is tiny:

```json
"auto": { "enabled": true, "argument": "tale" }
```

Creation-time auto resolution runs the selected option commands inside the
creating agent's existing runner claim (`creator_live=True`) and never
publishes a notification. That is why `%auto` is cheap, and why it is
dangerous: a misspelled policy fails at gate creation, not at launch, and a
successful auto resolution is silent.

Custom gates are extra-forbidden at the skill layer: `/sase_gate` tells the
agent never to set `"auto": true` on a gate that exists to get a human
decision. Launch approval (`/sase_run` → `sase launch request`) is the same
floor for a different reason: an agent must not approve its own child
launches.

### 1.5 There is no config for this

`src/sase/default_config.yml` has no `auto:` policy block. The closest knobs
are unrelated:

- `tmux_agent.bypass_permissions` (provider CLI approval bypass, default
  `true`)
- Prompt-completion `auto:` (soft suggestions)
- Artifact capture "automatic" vs explicit

`%auto` is entirely launch-text plus the metadata triad. That is why it feels
like "the permissions system": it is the only HITL policy a user can actually
set per agent, and they set it by sprinkling a token in the prompt.

## 2. The two permission layers, and why only one is real

SASE currently has two layers that people call "permissions":

**Layer A — provider tool / sandbox permissions.** Disabled in practice.
Grok is launched with `--permission-mode bypassPermissions` and no sandbox
profile; docs say this matches Codex, OpenCode, and Muse. Claude interactive
and headless paths pass the provider's `bypass_args`. Native plan and ask
are disabled so SASE owns those handoffs (`docs/llms.md`,
`docs/agent_providers.md`). This is consistent with
`decisions/adapters-normalize-harnesses`: the adapter makes the CLI conform
to the single-turn contract instead of modeling the harness's private wait
and approval semantics.

**Layer B — SASE HITL gates.** This is the live permission system:

- Plan / epic plan approval
- User questions
- Launch approval
- Sudo
- Custom command-backed gates
- Plugin-required, flag/task triage, bead snooze/cleanup

`%auto` only talks to Layer B, and only to the two kinds that allow it (plan
and question). Layer A is a global boolean. The user's observation is
accurate: *the permissions that are used in practice are `%auto`*, because
hard provider permissions are not on.

That is not an accident to reverse in the same change. Re-enabling Claude
`acceptEdits` / Codex `workspace-write` *instead of* SASE gates would split
HITL across two UIs, fight `--no-plan` / `--no-ask-user`, and reopen
adapter-harness normalization. If SASE ever grows real provider sandboxing,
it should be a *second field on the same host-owned profile*, not a second
directive and not a return of in-harness prompts.

## 3. Why the current design is unintuitive

These are the actual usability failures, ranked by how often they bite:

1. **One token, two secret modes.** Bare `%auto` is "full HITL auto" (plans
   *and* questions). `%auto:tale` / `%auto:epic` are documented as plan-only.
   Users who want "just don't stop for the plan" reasonably write
   `%auto:tale` and get a different question policy than they think — or the
   inverse, depending on which of docs vs `is_auto_approve_active()` they
   hit.
2. **You cannot name the thing you want.** There is no spelling for "auto the
   plan, ask the questions," "ask the plan, auto-answer questions," or
   "auto this epic's child tales but not a nested epic." `sase bead work`
   therefore injects bare `%auto` on every phase and land agent, which is how
   nested landing loops auto-approve child plans (see prior research
   `202609/sase_11e_nested_landing_loop.md`).
3. **The argument is not a mode, it is a conflict check.** `%auto:epic` does
   not *select* the epic option on a tale; it *errors* if the authored tier
   is tale. Bare `%auto` already follows the authored tier. The colon values
   are mostly "please fail if the agent authors the other tier," plus the
   accidental question-policy split.
4. **Parser, adapter, TUI, and memory tell four stories.** Core memory still
   says "Auto-approve next plan." `docs/macros.md` says "automatic gate
   resolution; optional argument is gate-owned." Completion suggests
   `plan|tale|epic` "without closing the parser." The TUI footer is
   `auto-approve` / `unapprove`.
5. **No host-owned default.** Every autonomous loop has to remember to put
   `%auto` in the prompt. Forget it and the agent parks on a plan gate.
   Put it in a generated segment and you cannot later say "this land agent
   should still ask." Policy lives in string concatenation.
6. **Power and safety are coupled the wrong way.** The kinds you most want
   to auto (routine plans, first-option questions in a land loop) share a
   boolean with the kinds you must never auto (sudo, launch, custom). The
   adapter floor is the only thing keeping `%auto` from becoming
   "auto-approve privilege," and it is invisible in the prompt.

## 4. Critique of the implied plan

The request is: *`%auto` is not very configurable or intuitive; make this
directive much more powerful.*

### 4.1 What is a good idea

- Treat HITL policy as a first-class, inspectable object rather than an
  opaque colon token.
- Let a user say, in one place, which gate kinds auto-resolve and how.
- Keep a short launch-time spelling. People already type `%auto` constantly
  (`sase bead work`, typical `+sase %auto #pr:…` prompts, TUI `A`).
- Keep adapter-owned validation. Plan-vs-epic conflict checks, question
  "first" vocabulary, and `forbidden` kinds are the safety model.
- Make the TUI, CLI, Telegram, and mobile share that object. Today they
  reconstruct it from the metadata triad.

### 4.2 What is a bad idea

**A more powerful opaque argument.** `%auto:plan+questions-first,sudo=no` or
a mini-language in the colon slot will fail the same way `%wait` failed
before `%queue` / `%hold` were split: one token, too many jobs, unreadable
errors, no completion. sase-core currently types the auto argument as
`DirectiveValueRole::GateOwned` with *no keywords*. Stuffing a DSL into that
slot fights the directive grammar.

**A prompt-owned permission DSL.** Allow/deny lists, tool names, path globs,
and "yolo" in the prompt are a privilege-escalation channel. Any successor,
macro, or `#fork` can widen them. Claude Code learned this the hard way:
project `.claude/settings.json` is no longer allowed to turn on
`bypassPermissions` or `auto` (v2.1.257+); those modes are user/managed
settings or an explicit CLI flag. SASE should not put the equivalent in
agent-authored prompt text.

**Auto-resolving privileged kinds from `%auto`.** `/sase_gate` and
`/sase_run` exist so a human sees the command or the child prompt. Letting
`%auto(sudo=approve)` or `%auto(custom=primary)` come from the same agent
that authored the gate is self-approval. The adapter `forbidden` policy is
the product. Keep it.

**Re-enabling provider HITL as the "real" permission system.** That
duplicates `/sase_plan` and `/sase_questions`, breaks single-turn adapters,
and still would not cover sudo, launch, or custom gates, which the harness
has never heard of.

**Splitting `%auto` back into `%plan` / `%approve` / `%tale`.** Already
removed (changelog: those spellings are no longer recognized). Unification
was correct; the missing piece is structure, not more names.

**Making `%auto` repeatable like `%final` without a merge rule.** Duplicate
`%auto` is an error today. Repeatable union is surprising ("does the second
line add questions or replace the profile?"). If composition is needed, copy
`%queue`: one canonical field per launch, disjoint fields may compose,
conflicts error.

### 4.3 Would I take a different approach?

Yes. I would **not** start by making the directive more powerful. I would
start by making the *policy* real, then let the directive select it.

The closest in-tree analog is `%final`, not `%model`. `%final` cannot invent
finalizer instances; it can only add/remove configured ones, and required
instances cannot be removed. `%queue` is the analog for structured
parenthesized fields. `%hold` is the analog for "this used to be overloaded
onto `%wait`; we gave it its own typed object."

The closest external analog is Codex, not Claude Code's tool allowlist:

- Codex splits **sandbox** (what the process can do) from **approval_policy**
  (when it must ask), then names the pair as a **profile**
  (`[profiles.full_auto]`).
- Claude Code layers **permissionMode** (baseline) under **allow/ask/deny
  rules**, and refuses to let a project file turn on the most dangerous
  modes.

SASE already has the Codex-shaped split in spirit: Layer A is sandbox
(currently "danger-full-access"), Layer B is approval (gates). `%auto` is
trying to be the approval-policy profile with none of the profile machinery.

So: keep the directive, stop pretending the argument *is* the policy.

## 5. Justified requirement adjustments

These change the user's request. Each is explicit.

1. **`%auto` remains a selector, not a permission language.** The
   requirement "much more powerful" is accepted for *expressiveness of HITL
   policy* and rejected for *arbitrary privilege in prompt text*.
2. **Privileged gate kinds stay auto-forbidden**, even if a profile or
   prompt asks. `sudo`, `launch`, `custom`, `plugins_required`,
   `flag_triage`, `task_triage`, `bead_snooze`, `bead_stale_cleanup`, `hitl`.
   A future exception would be a new adapter policy plus a config opt-in,
   never a prompt spelling. Agents still must not set `"auto": true` on
   custom gates they author.
3. **Do not fold provider permission-mode / sandbox into v1.** Optional
   later field on the same profile (`provider_permission_mode`,
   `provider_sandbox`). v1 is SASE gates only. Re-enabling in-harness
   prompts is out of scope and conflicts with adapter normalization.
4. **Prompt overrides may only tighten.** A launch can select a configured
   profile and may change a kind from `first`/`authored` to `ask`. It may
   not raise a kind above the profile ceiling, and it may not enable a
   kind the adapter forbids. Same rule as `%final` required instances.
5. **Keep today's spellings working.** Bare `%auto`, `%a`, `%auto:plan`,
   `%auto:tale`, `%auto:epic` remain. After the question-path bug is fixed,
   `%auto:tale` / `%auto:epic` mean "plan auto at that tier, questions
   *ask*" — matching the docs, not `is_auto_approve_active()`. Call that
   out in the changelog; it is a behavior fix, not a silent compat break
   for people who relied on the bug.
6. **Replace the metadata triad with one `AutoPolicy` object.** Stop
   writing `approve` + `auto_approve_plan_action` + `auto_approve_argument`.
   Keep a compatibility reader for one release. Environment variables
   collapse to one structured value or go away.
7. **TUI `A` becomes a profile picker (or a cycle through configured
   profiles), not a bare-`%auto` toggle.** The current toggle erases
   tale/epic intent. A boolean is the wrong UI for a structured policy.
8. **No new `%permissions` / `%yolo` / `%ask` directive.** One HITL
   selector. Adding names re-creates the `%plan`/`%tale`/`%approve` mess.
9. **Generated launches (`sase bead work`, macros) select a named profile
   rather than concatenating `%auto`.** Land vs phase can then differ
   (`profile=land` vs `profile=phase`) without a special case in
   `work_prompt.py`.
10. **Policy resolution belongs in sase-core** (launch wire + directive
    metadata + validation). TUI, CLI, Telegram, and mobile must not each
    re-derive "does this auto-answer questions?"

## 6. Alternatives considered

### A. Status quo plus docs

Rewrite memory to match `docs/macros.md`, fix `is_auto_approve_active()`,
leave the opaque argument. Cheap. Does not give "auto plan, ask questions"
except via the tale/epic accident, and does not give a host default.

**Reject as the whole answer.** Do the docs/bugfix as phase 0 of the real
design.

### B. Kitchen-sink `%auto(...)` DSL in the prompt

```text
%auto(plan=tale, question=first, sudo=ask, custom=primary, tools=bypass)
```

Expressive in a demo, unsafe in a successor prompt, unreadable in
completion, and still has nowhere to put a *default* for `sase bead work`.

**Reject.** Parentheses are right; unconstrained keys are not.

### C. Split directives (`%auto-plan`, `%auto-questions`)

Clear, and matches how `%queue` was split out of `%wait`. Wrong here:
plan and question policy are one HITL posture for one launch, and we
already unified `%plan`/`%tale`/`%epic`/`%approve` into `%auto` on
purpose.

**Reject.**

### D. Per-tool allow/deny copied from Claude Code

Useful *if* SASE were mediating provider tools. It is not. SASE mediates
gates. Tool allowlists would be fiction until Layer A is real, and even
then they belong in config/managed settings, not `%auto`.

**Defer** until a provider-sandbox profile field exists, then as config
rules, not prompt text.

### E. Host-owned profiles + tightening selector (recommended)

Config declares named postures. `%auto` names one and may tighten. Adapters
keep their floors. One `AutoPolicy` on the agent.

This is `%final` + Codex profiles, applied to gates.

## 7. Recommended solution

### 7.1 Host-owned profiles

Add a config block, user- and project-scoped, project cannot raise the
user/host ceiling (Claude's lesson about project `bypassPermissions`):

```yaml
auto:
  default: ask          # used when the prompt has no %auto
  profiles:
    ask:
      plan: ask
      question: ask
    plan:               # today's bare %auto, minus the docs bug
      plan: authored    # follow the plan's own tier
      question: first
    tale:               # today's %auto:tale, after the bugfix
      plan: tale
      question: ask
    epic:
      plan: epic
      question: ask
    land:               # for sase bead work land agents, opt-in
      plan: authored
      question: ask
```

Verbs, closed set:

| Verb | Plan | Question |
| --- | --- | --- |
| `ask` | Create a pending gate | Create a pending gate |
| `authored` | Auto the primary branch for the authored tier (`plan` → approve+commit, `epic_plan` → epic) | n/a |
| `tale` / `epic` / `approve` | Auto that action; conflict with authored tier is `invalid_auto_argument` as today | n/a |
| `first` | n/a | First / default-selected option (today's question auto) |

Privileged kinds do not appear. An unknown kind key is a config error, not
"try to auto it."

`auto.default: ask` preserves today's no-`%auto` behavior. A user who wants
every agent to be hands-off sets `auto.default: plan` in *user* config, not
in a project file that an agent can edit.

### 7.2 Directive syntax (additive)

Keep colon/bare/plus. Add parenthesized form in sase-core
(`syntax_forms` gains parentheses; keywords `profile`, `plan`, `question`).

```text
%auto                         # profile `plan` (compat: today's bare)
%auto:plan                    # same
%auto:tale                    # profile `tale`
%auto:epic                    # profile `epic`
%auto:land                    # named profile
%auto(profile=land)
%auto(profile=plan, question=ask)   # tighten: auto plan, ask questions
%auto(plan=authored, question=ask)  # equivalent, uses default profile as base
```

Rules:

- One `%auto` per launch (still not repeatable).
- `profile=` selects a configured name. Unknown profile is a launch error.
- `plan=` / `question=` override that profile only toward `ask` or an
  equally strict verb. Escalation is a `DirectiveError` at extract time,
  not at gate creation.
- Colon values `plan`/`tale`/`epic` remain compatibility aliases for
  profiles of the same name, not a second vocabulary.
- Completion lists configured profile names plus the three compatibility
  values, then keyword names. Gate-owned free typing goes away for the
  common path; unknown colon values still reach the adapter so
  `%auto:foo` keeps failing at the plan gate rather than at parse, unless
  we decide to fail closed at extract — I would fail at extract once
  profiles exist, with a message naming configured names.

### 7.3 One `AutoPolicy` on the agent

Replace the triad with a single frozen object on the launch wire and in
`agent_meta.json`:

```json
{
  "auto_policy": {
    "profile": "plan",
    "plan": "authored",
    "question": "first",
    "source": "directive"
  }
}
```

`source` is `default` | `directive` | `tui` | `cli`. Readers:

- Plan propose uses `plan`.
- Question gate creation uses `question`.
- TUI glyph `⚡` means `plan != ask` or `question != ask`, with the profile
  name in the footer (`auto:plan`, `auto:tale`, `ask`).
- Monitor follow-ups serialize the object back to the canonical directive
  (`%auto` vs `%auto:tale` vs `%auto(profile=land, question=ask)`).

Gate request `auto.enabled` / `auto.argument` stay as the *transport* into
the existing adapter. The host compiles `AutoPolicy` → `(enabled, argument)`
per kind:

- plan + `authored` on a tale → `{enabled: true, argument: null}`
- plan + `tale` → `{enabled: true, argument: "tale"}`
- plan + `ask` → `{enabled: false}`
- question + `first` → `{enabled: true, argument: null}`
- question + `ask` → `{enabled: false}`
- sudo / launch / custom → always `{enabled: false}`; a compile that would
  set true is a host bug, not an adapter surprise

### 7.4 TUI, CLI, generated prompts

- `A` opens a small profile menu (configured names + `ask`), or cycles if
  there are only two. It must not collapse `%auto:epic` into bare `%auto`.
- `sase bead work` phase segments use `auto.profiles.phase` if defined,
  else today's `plan` profile. Land uses `auto.profiles.land` if defined,
  else `plan` with `question=ask` recommended so a land agent cannot
  silently approve a nested epic. That is a product choice: default land to
  `question=ask, plan=authored` and document it.
- `sase agent show` prints the resolved policy. Today you have to mentally
  XOR three fields.

### 7.5 Phasing

**Phase 0 — truth.** Align `sase/memory/macros.md` with `docs/macros.md`.
Fix `is_auto_approve_active()` so it is `question == first`, not "any
argument present." Add tests that `%auto:epic` does *not* auto-answer
questions. This is justified even if the rest waits.

**Phase 1 — object without new syntax.** Introduce `AutoPolicy`, write it
from existing spellings, read it everywhere, keep colon/bare/plus. No
user-visible syntax change except the question bugfix.

**Phase 2 — config profiles + parenthesized form.** sase-core directive
keywords, config schema, tightening rule, completion. `sase bead work`
gains an optional profile name.

**Phase 3 — TUI picker and `sase agent auto` CLI** (show/set/clear the
policy on a live agent), sharing the same core function as `A`.

**Phase 4 (later, separate decision).** `provider_permission_mode` on the
profile. Still host-owned. Still cannot be raised by prompt text. Only
worth doing when SASE is ready to stop launching with
`bypassPermissions` for some profiles. Not part of making `%auto`
configurable.

No feature flag is required if phase 1 is a pure representation change and
phase 2 is additive syntax. Use a flag only if parenthesized `%auto(...)`
needs to be beta while colon forms stay; I would not bother — the grammar
is the same as `%queue`.

### 7.6 Where the code goes

Litmus: TUI, CLI, Telegram, and mobile all need the same answer to "will
this question auto-resolve?" That is sase-core.

- `sase-core`: `AutoPolicy` type; launch-wire field; directive metadata
  (keywords, profile completion hook); compile-to-gate-auto; tightening
  check.
- sase Python: config schema; extract → policy; plan propose / question
  create / TUI `A` / monitor prefix consume the object; delete the triad
  writers; keep a one-release reader.
- Docs + core memory: one table (profile / verb / kind). Stop saying
  "auto-approve next plan" as the whole story.
- Adapters: unchanged `auto_policy` floors. The host stops sending
  `enabled: true` to forbidden kinds; the adapter remains the last line of
  defense.

## 8. Worked examples

Hands-off fixer, today's default `%auto`:

```text
%auto
%id:auto-fixer
Fix the lint errors.
```

Same, but stop and ask if the agent uses `/sase_questions`:

```text
%auto(question=ask)
%id:auto-fixer
Fix the lint errors.
```

Epic author who wants the epic path and still wants to answer questions
(today's *documented* `%auto:epic`):

```text
%auto:epic
%id:billing-epic
Plan the billing dashboard epic.
```

Land agent in an epic that may not auto-approve a nested child epic:

```text
%auto(profile=land)
#bd/land_epic:proj-epic
```

with

```yaml
auto:
  profiles:
    land:
      plan: ask
      question: ask
```

User-wide "I am watching the TUI, never auto anything" without editing every
prompt:

```yaml
auto:
  default: ask
```

None of these auto-approve sudo or a `sase launch request`. If someone
writes `%auto(sudo=first)`, extract fails.

## 9. Risks and non-goals

- **Behavior fix in phase 0.** Anyone depending on `%auto:epic` also
  auto-answering questions will see questions start pending. That matches
  the docs; changelog it.
- **Project config that sets `auto.default: plan`.** An agent that can
  edit project config could widen the default. Mitigate the same way
  Claude did: project may *tighten* relative to user/host, not raise.
  Document that `auto.default: plan` belongs in user config.
- **Macros that inject `%auto`.** After phase 2 they should inject
  `profile=` names. Until then, bare `%auto` still means the `plan`
  profile.
- **Not in scope:** mediating Bash/Edit/Read; OS sandboxing; making
  `tmux_agent.bypass_permissions` per-agent in v1; auto-resolving
  LaunchApproval for "trusted" child prompts; letting custom gates declare
  themselves auto-capable.

## 10. Recommendation

Implement **host-owned HITL profiles with `%auto` as a tightening
selector.**

Do it in four small steps: fix the question-path lie, replace the metadata
triad with `AutoPolicy`, add config profiles and parenthesized keywords,
then give the TUI a profile picker. Leave provider bypass as a later field
on that same profile. Do not make the directive more "powerful" than the
host's configured ceiling.

That is the version of "make `%auto` much more powerful" that is actually
a good idea.

## Sources

In-tree (inspected this turn):

- `docs/macros.md` (directive table, Auto Directive, `%auto:epic` plan-only claim)
- `docs/ace.md` (Agents-tab `A` toggle, `⚡` glyph)
- `docs/llms.md`, `docs/agent_providers.md`, `docs/configuration.md` (provider bypass)
- `docs/beads.md` (epic phase/land segments carry bare `%auto`)
- `sase/memory/macros.md` (stale "auto-approve next plan" summary)
- `sase/memory/decisions/gates-never-block.md`
- `sase/memory/decisions/adapters-normalize-harnesses.md`
- `src/sase/macro/_directive_values.py`, `_directive_types.py`, `_directive_extract.py`
- `src/sase/axe/run_agent_directive_metadata.py`, `run_agent_directives_extract.py`
- `src/sase/main/plan_approve_handler.py` (`is_auto_approve_active`, argument readers)
- `src/sase/axe/run_agent_exec_questions.py`
- `src/sase/notification_gates/adapters.py`, `service.py`, `model_request.py`
- `src/sase/_plan_gate_metadata.py`, `src/sase/plan_gate.py`
- `src/sase/bead/work_prompt.py`
- `src/sase/ace/tui/actions/agents/_approve.py`
- `src/sase/monitor/continuation_delivery.py`
- `src/sase/default_config.yml` (`tmux_agent.bypass_permissions`)
- sase-core `crates/sase_core/src/editor/directive/metadata.rs` (auto: colon/bare/plus, no keywords)
- Skills: `/sase_gate`, `/sase_run`, `/sase_sudo`

External (permission-model comparison, 2026):

- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Claude Code permissions](https://code.claude.com/docs/en/permissions)
- [Codex sandboxing](https://developers.openai.com/codex/concepts/sandboxing)
- [Codex sandbox.md (approval vs sandbox, profiles)](https://raw.githubusercontent.com/openai/codex/main/docs/sandbox.md)

Prior SASE research cited for symptoms, not for this design:

- `research:202609/sase_11e_nested_landing_loop.md` (land `%auto` auto-approving nested child plans)
