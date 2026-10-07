# `%auto` Redesign: A Real Autonomy Policy That `%auto` Selects

> **Research query:** The `%auto` directive is the main way to tune permissions for a
> SASE agent in practice (real agents have no hard permissions yet), but it is not very
> configurable or intuitive to use. What is the best way to make it much more powerful?
> Is that a good idea at all, would a different approach be better, which requirement
> adjustments are justified (called out clearly), and what is the recommended solution?

![Infographic: "%auto needs a policy". It shows the July–October evidence (69.5% of prompts use %auto; 73% of auto-approved epics came from land or phase workers; 557 of 557 auto-approved tales were also archived, among recorded selections), today's silent-authority defects, the proposed flow from a named config profile through the %auto selector and Rust policy engine to explicit gate decisions, and the four-step rollout](auto_directive_autonomy_policy_infographic.png)

## Bottom line

- **The problem is real.** `%auto` appears in **[69.5% of prompts](#usage)** (7,993 of
  11,501 since July), rising from 61% in July to 80% in September. In practice it is the
  only autonomy control SASE has, because every provider CLI runs with its
  [approval-bypass flag](#where-permissions-actually-live). Yet it can express almost
  nothing.
  - You cannot say "auto the plan, ask me the questions."
  - You cannot say "tales yes, epics no."
  - You cannot say "this land agent must not approve a child epic."
- **The most dangerous behavior today is not missing syntax. It is what `%auto` already
  does silently.**
  - Bare `%auto` auto-approved **234 epic plans**. **73% of them (170) came from epic
    land or phase workers**, whose `%auto` is hard-coded in `bead/work_prompt.py`. That
    is the nested-epic loop that earlier research documented for `sase-11e`.
  - Parenthesized `%auto(...)` **[fails open](#defects-to-fix-regardless-of-the-redesign)**.
    `%auto(plan=ask, questions=ask)` and `%a(epic=ask)` both parse as bare `%auto`, so
    they grant full automation. I reproduced this with a parser probe.
  - **The authority `%auto` grants is derived from gate UI defaults.** When the July 18
    gate refactor made Enter submit "approve + commit", bare `%auto` began archiving
    every tale plan to the plans sidecar: 557 of 557 auto-approved tales. `docs/macros.md`
    and the core `macros.md` memory row still describe the old behavior.
- **[Critique.](#critique-of-the-plan)** "Make the directive much more powerful" is the
  right goal in the wrong shape. Do not grow `%auto` into a permission language typed
  into prompts.
  - Prompts are also written by machinery and by agents: launch requests, epic worker
    rendering, monitor and gate follow-ups.
  - Once a prompt literal can grant launch or custom-gate authority, an agent can mint
    a child with more authority than it has.
  - Gate auto-resolution is also not enforcement. An agent can still reach most side
    effects through its shell.
- **[Recommendation: autonomy profiles.](#recommended-solution)**
  - **[Profiles.](#config-sketch)** Add a small, typed, Rust-owned autonomy policy.
    Named profiles are defined in config, following the precedent of `%final` and
    `finalizers:`. `%auto` selects a profile, and narrow inline overrides adjust it.
  - **[Lifecycle.](#resolution-inheritance-and-attenuation)** Resolve the policy once
    at launch and persist it as one structured record. Read it live at every gate,
    inherit it by one rule, show it to the user, and render it into the agent's context.
  - **[Order of work.](#phased-rollout)** Ship the fail-open and nested-epic fixes
    first. Bounded launch delegation comes later. Hard execution permissions are a
    separate, later layer. That layer attaches to the same profile object; it is not
    another prompt directive.

## Scope and method

_Consolidated research, 2026-10-07. This report merges
[five independent reports](#sources) (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`) with
my own verification. That verification covered source at sase `142636c528`, a parser
probe, the gate bundles under `~/.sase/interaction_requests/`, prompt history from July
to October, and the official Claude Code and Codex docs. All syntax and config below
marked **proposed** describes a design, not existing behavior._

## What the auto directive does today

This section describes how `%auto` works today; everything in it was verified.

### Mechanics

- **Parse.** `%auto` and `%a` produce three overlapping fields: `auto_enabled`,
  `auto_mode`, and an opaque `auto_argument` (`src/sase/macro/_directive_values.py`).
  Bare, `+`, and `true` map to mode `plan`. There is no global enum, so `%auto:foo` is
  valid syntax. A duplicate `%auto` is an error. The Rust editor metadata advertises
  colon, bare, and plus forms only, with no keywords.
- **Persist.** Launch writes up to three `agent_meta.json` keys: `approve`,
  `auto_approve_plan_action`, and `auto_approve_argument`. The runner also exports
  `SASE_AGENT_AUTO_APPROVE=1` when `approve` is set (`axe/run_agent_runner_launch.py:308`).
- **Read.** `main/plan_approve_handler.py` reconstructs intent by layering four
  environment-variable spellings over the meta keys.
  `is_auto_approve_active()` is true if *any* argument is present.
- **Decide.** Each `GateAdapter` carries an `auto_policy` of `approval`, `first`, or
  `forbidden`. `resolve_auto_selection` returns the gate's **primary branch, filtered by
  `default_selected`** (`notification_gates/adapters.py:46-76, 387`). An auto gate
  publishes no notification. It resolves inline through the normal executor with
  `source="auto_resolution"`, and the creator keeps running. Per `gates-never-block`,
  this costs exactly one agent.

| Gate kind | Adapter policy | What `%auto` does | Observed (Jul–Oct) |
| --- | --- | --- | --- |
| `plan` (tale) | `approval` | Selects primary branch **`approve` + `commit`**: launches the coder **and archives the plan** to the plans sidecar | 564 auto-resolved; **557 of 557 with a recorded selection chose `approve`+`commit`** |
| `epic_plan` | `approval` | Commits the SDD epic, initializes beads, **launches the epic clan** | **234 auto-resolved, all from bare `%auto`** |
| `question` | `first` | Picks the first option of every question. The transport is a bool, so the argument is dropped | 46 auto-answered vs. 20 answered by a human |
| `launch`, `sudo`, `custom`, `hitl`, triage, snooze, cleanup, plugins | `forbidden` | Never; raises `auto_not_supported`. Launch requests hard-code `approval: "required"` (`agent/launch_request_planning.py:37`) | 0 auto-resolved |

### Usage

I re-measured the usage figures from `~/.sase/prompt_history/26{07..10}.json` and the
gate bundles. They match the cld report exactly.

| Metric | Value |
| --- | --- |
| Prompts containing `%auto`/`%a` | **7,993 / 11,501 (69.5%)**: Jul 60.7%, Aug 67.8%, Sep 79.6% |
| Directive spellings | bare **12,142** · `:tale` **702** · `:epic` **0** · parenthesized **0** |
| Who authored the 234 auto-approved epics | epic **land** workers **137** · epic **phase** workers **33** · top-level/other agents **64** |

Two conclusions follow:

1. `%auto` works as a binary flag that is on by default. Users have not reached for its
   argument vocabulary.
2. Most epic fan-out with no human checkpoint comes from **generated** prompts, not from
   anything a human typed. More directive syntax would not have prevented any of it.

### Where permissions actually live

| Layer | Mechanism | Enforced by | Relation to `%auto` |
| --- | --- | --- | --- |
| Provider tools | Every adapter passes a bypass flag: Claude/agy/opencode `--dangerously-skip-permissions`, Codex `--dangerously-bypass-approvals-and-sandbox`, qwen/muse `--yolo`, grok `bypassPermissions`. Controlled by `tmux_agent.bypass_permissions: true` | Nothing. The ephemeral workspace clone is the only de facto sandbox | None |
| Host gates | Plan, epic, question, launch, sudo, custom, triage | Host. A gate turn ends the agent's turn | **The only dial** |
| Instructions | Skills and memory rules: `/sase_run` for launches, `/sase_gate` for dangerous commands, the no-direct-commit rule | Agent compliance | None. **The agent is never told it is running under `%auto`** |
| Completion | `%final`, `#commit`/`#pr`, host finalizers | Host (`host-owned-completion`) | None. This layer is already the right pattern: config defines instances, the prompt selects them, the host enforces |

All five reports agree that `%auto` decides **who clicks approve**. It does not decide
**what the agent can do**. Everything is the same Unix user on one host, and an agent can
edit `agent_meta.json` or config. So any policy in this design guards against footguns
and accidental self-escalation. It is not an adversarial security boundary (cdx).

## Defects to fix regardless of the redesign

Each item below is small and can ship on its own. The **Status** column records how I
verified the defect.

| # | Defect | Status | Found by |
| --- | --- | --- | --- |
| D1 | **Parenthesized `%auto` fails open.** The generic collector parses named arguments, but `%auto` keeps only the first positional. `%auto(plan=ask, questions=ask)`, `%a(epic=ask)`, and `%auto(sudo=approve)` all become `auto_enabled=True, mode=plan, argument=None`, which is full bare-`%auto` automation | **Observed** (parser probe, installed interpreter, workspace `src`) | cdx; confirmed |
| D2 | **`%auto:off` enables auto.** It produces `enabled=True, argument="off"`. Plan gates then fail mid-run with `invalid_auto_argument`, while questions are still auto-answered, because the question transport is a bool | Parse observed; downstream source-traced | Extends cdx |
| D3 | **Bare `%auto` archives tale plans.** Docs, the core memory row ("`tale`/`epic` commit SDD"), and commit `a3e494d938` (June: "keep auto plan approvals non-committing") all say bare does not commit. Since `005f431eb8` (2026-07-18), the tale primary branch has been `[approve, commit]` with every option `default_selected`, so bare `%auto` = Enter = approve + archive. For tales, `%auto:plan` ≡ `%auto:tale`, except that `:tale` errors on epic plans | **Observed** (557/557 bundles) | cdx (cld's report is wrong on this point) |
| D4 | **`%auto:epic`, `:tale`, and `:anything` auto-answer questions.** `is_auto_approve_active()` treats any stored argument as active. `docs/macros.md:3204` says `%auto:epic` does not answer questions | Source-traced | cld, grk, mus, gem |
| D5 | **TUI toggle-off does not stick for a live bare-`%auto` agent.** `A` removes the meta keys, but the runner already exported `SASE_AGENT_AUTO_APPROVE=1`, and both readers OR that env var with meta | Source-traced (not reproduced live) | cld |
| D6 | **Inheritance is ad hoc.** In-process successors copy only `approve` (`axe/run_agent_helpers_artifacts.py:161-187`), so `:tale` is lost on the coder. Monitor follow-ups re-emit a `%auto` prefix (`auto_launch_prefix`). Gate-turn follow-ups emit only `#fork`/`%model` (`turns/prompt.py`), so `%auto` is dropped after a launch, custom, or sudo gate | Source-traced | cld |
| D7 | **Epic worker policy is hard-coded.** `bead/work_prompt.py:187, 224` appends a literal `%auto` to every phase and land worker. This produced 170 nested epic auto-approvals and the `sase-11e`/`sase-xe` nesting loops (`research:202609/sase_11e_nested_landing_loop.md`). The pattern is still live: in-progress epic `sase-19i.7.3.3.3.3.3` is six levels deep. The policy has flipped three times in code | Observed + source | cld, grk; quantified here |
| D8 | **Question auto-answer is blind.** The agent is never told no human will read its question. `/sase_questions` gives no guidance to put the recommended option first | Source-traced | cld, gem |

**Filed as task beads:** D1/D2 → `sase-1hg` (bug); D3/D4 stale core-memory row and
docs → `sase-1hh` (memory). The remaining defects are P0 items in the
[phased rollout](#phased-rollout) and depend on the decisions in
[open decisions for you](#open-decisions-for-you).

D3 deserves emphasis because it is the strongest argument for the redesign's core
principle. **Automatic authority must come from a typed policy that names explicit option
IDs, never from presentation defaults** such as `primary_branch`, `default_selected`, or
option order (cdx). A UI keymap change silently changed what `%auto` publishes, and
nothing noticed.

## Critique of the plan

This section answers the question: is this a good idea?

### What is right

- **The need is measured, not hypothetical.** The most-used directive cannot express
  tale vs. epic, plans vs. questions, attended vs. unattended, or role-specific policy.
- **`%auto` is the right home.** It carries strong muscle memory (70% of prompts), TUI
  chips, and the `A` toggle. SASE deliberately collapsed `%plan`, `%tale`, `%epic`, and
  `%approve` into `%auto`, so do not re-split it into a second competing dial.
- **Configurability stops policy churning in code.** The three epic-worker flips show
  the cost of keeping that policy in code.

### What is risky in the plan as stated

1. **"Permissions" over-promises.** Gate policy is a checkpoint system. With provider
   bypass flags on, a "denied" capability is a workflow constraint the agent can route
   around through its shell. Name it **autonomy policy**, show enforcement coverage in
   the UI, and never display a reassuring "restricted" badge while the shell is
   unrestricted (cdx, gem, mus).
2. **A prompt-literal grant is a privilege-escalation path.** If `%auto(launch=allow)`
   or `%auto(custom=approve)` were legal in prompt text, any agent-authored launch,
   epic rendering, or follow-up could grant authority the user never gave. Claude Code
   learned the same lesson: project settings cannot turn on `auto` or
   `bypassPermissions`.
3. **More opaque arguments make it less intuitive.** `tale`/`epic` already conflate
   *which branch to pick* with *whether a human is needed*. The colon value currently
   acts as a tier-conflict check rather than a mode (grk). Adding more values without a
   central schema multiplies the D1–D4 confusion.
4. **Auto-allowing custom gates or sudo defeats their purpose.** An agent creates those
   gates precisely to get a human. The right way to pre-authorize an action is to tell
   the agent up front that it is pre-approved, so it never creates the gate (cld).
5. **Power without visibility is worse than today's on/off switch.** Profiles,
   overrides, inheritance, and clamping are opaque unless the effective policy is shown
   at launch, in the TUI, and in an explain command.

### What I would do differently

I would **not build "a more powerful `%auto` directive."** I would build **a policy
object that `%auto` selects**:

- defined in config,
- resolved and frozen at launch,
- persisted once,
- read live at every gate,
- inherited by one rule,
- shown to both the user and the agent.

The directive stays about as short as it is today. Most of the value comes from four
things the original framing does not mention:

1. role defaults for generated launches,
2. agent awareness,
3. fail-closed validation,
4. an explain surface.

## Adjusted requirements

Each requirement below is explicitly called out with how it changes the request.

| # | Requirement | Change vs. the request |
| --- | --- | --- |
| R1 | v1 is **gate autonomy policy**, not hard permissions. Docs and UI state the enforcement coverage | **CHANGED.** "Permissions" narrowed |
| R2 | **Per-gate-kind decisions** (`ask` / `deny` / a kind-specific allow value) that map to **explicit option IDs**, never UI defaults | Sharpened (fixes D3's root cause) |
| R3 | Policies live in config as **named profiles**. Bare `%auto` selects a default profile that reproduces today's *observed* behavior | **CHANGED.** Power moves from prompt syntax to config |
| R4 | **Inline overrides are narrow.** Prompts may set plan/epic/question freely, may only tighten other kinds, and can never exceed a role or parent ceiling | **ADDED.** Trust boundary |
| R5 | **Fail closed at launch.** Unknown profiles, keys, values, extra positionals, and mixed forms are launch errors, not mid-run gate errors | **ADDED.** Fixes D1 and D2 |
| R6 | **Role defaults for generated launches.** Epic phase and land workers select config roles. Their default denies nested-epic auto-approval (`epic: ask`) | **ADDED.** Behavior change for D7; see [open decision 1](#open-decisions-for-you) |
| R7 | **One persisted record, read live; one inheritance rule** across in-process, monitor, gate, and handoff successors. No environment-variable snapshot as a source of truth | **ADDED.** Fixes D5 and D6 |
| R8 | **Agent awareness.** The effective policy is rendered into the agent's context | **ADDED.** Fixes D8 |
| R9 | **Visibility and audit.** A launch preview, a TUI chip naming the profile, an explain command, and `{profile, rule, decision, source}` recorded on every auto-resolution | **ADDED** |
| R10 | **Rust core owns** the schema, parse, merge, clamp, and evaluate. TUI, CLI, Telegram, mobile, and LSP must agree | **ADDED.** Project rule `rust_core_backend_boundary` |
| R11 | `sudo`, `custom`, `hitl`, and the triage kinds stay non-auto-allowable. Launch allow comes in a later phase, config-only, bounded | **DEFERRED / CONSTRAINED** |
| — | Hard tool/sandbox permissions | **DEFERRED** to a separate decision. The profile reserves a section for them |
| — | A new `%caps`/`%perm`/`%policy` directive, numbered autonomy levels, `%auto(all)` | **DROPPED.** Two dials, false ordering, and implicit grants for future gate kinds |

## Options compared

| Option | Expressiveness | Safety | Intuitiveness | Verdict |
| --- | --- | --- | --- | --- |
| A. Status quo plus doc fixes | None added | Leaves D1 and D7 | — | Reject as the whole answer; its fixes become P0 |
| B. More colon values (`%auto:unattended`, adapter-interpreted) | Low | OK | Poor: one word means different things per adapter | Reject |
| C. Full keyword DSL in the prompt (gem/mus shape) | High | **Poor**: prompt-literal escalation; no home for role defaults | Verbose on every launch | Reject as the primary form; keep a narrow subset |
| **D. Config profiles + `%auto` selector + narrow overrides** | High | Good: config-only grants, ceilings, fail-closed | Terse daily use, explicit when needed | **[Recommend](#recommended-solution)** |
| E. Separate `%caps` directive now | High on paper | Theater until enforced | Two dials to learn | Reject now; a later profile section instead |
| F. Reviewer/classifier resolver (`review(@model)`) | High for plans | Good *behind* deterministic rules | Good | **Later phase.** Codex `approvals_reviewer = auto_review` and Claude Code auto mode both run a model reviewer *after* deterministic rules, never as the source of authority |

## Where the reports disagreed and how I resolved it

| Question | Positions | Resolution |
| --- | --- | --- |
| **Where does the power live?** | gem, mus: rich keyword arguments in the prompt. cld, grk, cdx: config profiles selected by `%auto` | **Config profiles plus a selector.** The prompt is not a trust boundary: 73% of auto-approved epics came from generated prompts. Keyword arguments stay, but narrowly (see the next row). |
| **May prompt overrides loosen?** | grk: tighten only. cld: may loosen plan/epic/question, only tighten everything else. cdx: a trusted user's explicit field may override a default, but never a host ceiling or parent restriction | **cld's rule plus cdx's ceiling.** Bare `%auto` already grants the maximum for plan, epic, and question, so allowing those values inline escalates nothing. grk's tighten-only rule would make `%auto(plan=approve)` impossible on top of a cautious default. Escalating kinds (launch, and anything added later) are config-only. A role or parent ceiling always wins. |
| **Bare `%auto` question default** | gem: change to `ask`. grk, cld: keep auto. mus: product decision | **Keep auto-answer in the default profile**, but switch from blind `first` to `recommended` (agent-flagged, falling back to first), and add the awareness block ([agent awareness](#agent-awareness)). For unattended runs, parking on a question is the worse failure. The real trap is that the agent does not know nobody is listening. `%auto(q=ask)` and an `attended` profile give the other posture in one token. |
| **`%auto:epic`/`:tale` and questions (D4)** | grk: fix the code to match the docs (ask). cld: keep the code and fix the docs | **Keep the observed behavior and fix the docs.** `:tale` has 702 real uses that currently auto-answer questions. `:epic` has 0 uses. Matching the docs would silently change 702 workflows to fix a sentence. |
| **Launch auto-approval** | gem: `launch=approve` / `tribe:<name>` in the prompt. cld, cdx: later, config-only, with limits and attenuation. grk, mus: keep forbidden | **Later, config-only, bounded.** Only 49 launch gates in three months shows low demand. The safety work is substantial: a cumulative budget, atomic reservation, a child-policy ceiling, and fan-out accounting. Never grant it from prompt text. |
| **Hard permissions** | gem: new `%caps`. mus: separate `%perm`/config. cld, grk: a later section on the same profile. cdx: a separate project sharing the vocabulary | **Same profile object, separate section, later.** Users think in postures ("overnight", "read-only research"), not in two independent knobs. Do not ship a second directive with no enforcement behind it. Revisit the directive's name only when a hard layer actually ships. |
| **Budgets / TTL** | mus: `count=`/`ttl=` on auto-resolutions. cld: standing approvals. cdx: `scope=turn/session` | **v1 scope is the agent session**, which is already SASE's natural unit. The one budget the data demands is an **epic nesting limit**. Generic count/TTL and standing approvals come later. |
| **Feature flag** | cld: `sunset` for legacy readers. grk: none. mus: `beta` | **`sunset` flag** for the legacy meta triad and env readers while old runners drain. `sase_flags.md` makes this mandatory for backward-compatible branches. Profiles themselves are config fields, not flags. |
| **Claude Code / Codex prior-art details** | grk: Claude blocks project-level `bypassPermissions`/`auto` "v2.1.257+". cld: Codex `[profiles.<name>]`, `approval_policy=untrusted` | I checked the current docs. Claude does ignore `auto`/`bypassPermissions` set in `.claude/settings.json`, but the docs give **no version**. Codex profiles are **`$CODEX_HOME/<name>.config.toml` files selected with `--profile`**, and `untrusted` is now unsupported. Neither correction changes a conclusion. |

## Recommended solution

Autonomy profiles selected by `%auto`. Implement **Rust-owned autonomy profiles that
`%auto` selects**:

- **First, ship [P0](#phased-rollout).** Fail-closed parsing, a live-read policy record,
  uniform inheritance, doc and memory truth, and a stop to nested-epic auto-approval by
  epic workers. These remove today's silent risks without any new syntax.
- **Then introduce the policy object (P1) and profiles (P2):**
  - per-gate-kind `ask`/`deny`/allow decisions that select explicit option IDs;
  - named config profiles with project tighten-only layering and role defaults;
  - `%auto` / `%auto:<profile>` / `%auto(<profile>, plan|epic|q=…)` with narrow overrides;
  - an effective policy frozen at launch, inherited by one rule, rendered into the
    agent's context, and visible through explain and audit surfaces.
- **Hold back** automatic launch approval until it can be bounded and attenuated (P3).
- **Treat real execution permissions as a separate, later layer** on the same profile.
  Never claim enforcement where the provider still runs with a bypass flag.

### Concept

An **autonomy profile** is a named, config-defined, versioned policy. For each gate kind
it states one of three outcomes:

- the host resolves the gate, and how (by explicit option IDs),
- the host denies it with a typed refusal,
- a human decides.

The profile also states what happens when a human would be needed but none is listening
(`on_ask`). `%auto` selects a profile. **The absence of `%auto` still means "a human
decides everything"**, which matters because machine-generated launches rely on it.

### Config sketch

**Proposed.** This follows the `finalizers:` instance pattern. I use a top-level
`autonomy:` key to avoid colliding with other `auto` settings.

```yaml
autonomy:
  version: 1
  default: standard              # what bare %auto / %a selects
  roles:                         # replaces the literal %auto in bead/work_prompt.py
    epic_phase: epic_worker
    epic_land: epic_worker
  profiles:
    standard:                    # == today's observed bare %auto
      description: Approve and archive tales, launch epics, answer questions.
      gates:
        plan: approve_archive    # option ids [approve, commit]
        epic: approve            # commit SDD epic + launch clan
        question: recommended    # agent-flagged option, else first
        launch: ask
      on_ask: park               # park | deny
    epic_worker:                 # nested epics need a human (or a depth budget)
      extends: standard
      gates: { epic: ask }
    attended:
      extends: standard
      gates: { question: ask }
    overnight:                   # "I'm walking away"
      extends: standard
      gates: { epic: ask, question: decide }
      on_ask: deny
    # compatibility spellings, reserved names
    plan: { extends: standard }
    tale: { extends: standard, gates: { epic: ask } }    # today: hard error on epic
    epic: { extends: standard, gates: { plan: ask } }    # today: hard error on tale
```

Rules for profiles:

- Layering is builtin < user < project. A **project layer may only tighten** relative to
  user config, the same way Claude Code ignores project-level `auto` and
  `bypassPermissions`.
- Use single-level `extends` only. Do not add numeric priorities in v1.
- The names `plan`, `tale`, and `epic` are reserved for the compatibility translation.

### Decision vocabulary

Each adapter **declares** the values it supports. This replaces today's `auto_policy`
string with a capability set. Validation is central; adapters keep only selection
semantics.

| Kind | Values (v1 in bold) |
| --- | --- |
| `plan` (tale) | **`ask`**, **`approve`** (coder only), **`approve_archive`** (coder + archive), **`archive`** (archive, no coder), `deny` |
| `epic` (epic_plan) | **`ask`**, **`approve`**, `deny`; later `approve(max_depth=N)` |
| `question` | **`ask`**, **`recommended`**, **`first`** (legacy), `decide` ("no human available; choose and record your assumptions"), `deny` |
| `launch` | **`ask`**; later `deny`, and a config-only `allow(max_children, max_depth, max_model, scope, child_profile)` |
| `sudo`, `custom`, `hitl`, triage kinds | **`ask`**; later `deny`. **No allow.** Pre-authorization goes through the [awareness block](#agent-awareness) |

- **Unknown kinds.** A gate kind a profile does not mention evaluates to `ask`. Adding a
  plugin or a new gate kind can never silently widen an existing profile.
- **Combined selections.** If a combined selection includes an effect the profile does
  not grant, the whole gate stays manual. The host never executes part of it (cdx).

**Question schema change.** Add an explicit `recommended: true` flag on at most one
option, rather than parsing labels as gem proposed. `recommended` uses that flag and falls
back to the first option. Free-text-only and malformed questions stay manual. A question
answer must **never** mint launch, sudo, or publishing authority (cdx).

### Directive grammar

**Proposed.** The grammar uses the same positional-plus-keyword form as `%queue`/`%hold`,
with canonicalized aliases (`q` → `question`, `e` → `epic`).

```text
%auto                          # autonomy.default (today's behavior)
%a:attended                    # select a profile
%auto(q=ask)                   # default profile + override
%auto(overnight, epic=deny)    # profile + override
%auto:tale                     # compatibility profile; still works
```

- A launch unit has exactly one `%auto`, as today. There is no order-sensitive
  accumulation.
- **Explicitly rejected at launch:** unknown profile; unknown key; extra positional;
  duplicate key; mixed `%auto:x(...)`; `launch=allow` or any non-`ask`/`deny` value for
  privileged kinds ("must come from a config profile"); and any value above the role or
  parent ceiling.
- Completion and LSP list configured profile names first, then keys. Python, the Rust
  typed launch extractor, editor metadata, and the macro LSP must accept and reject
  exactly the same forms.

### Resolution inheritance and attenuation

1. **Resolve once at launch.** Combine the profile layers with the inline overrides,
   then apply role and parent ceilings. Persist a single `agent_meta.autonomy` record
   containing:
   - the resolved policy,
   - `profile`,
   - `overrides`,
   - `source` (`prompt|tui|cli|inherited|role|launch_clamp`),
   - schema version and config digest.

   A later config edit never silently widens a running agent. `%dispatch` ships the
   resolved record, so remote config drift cannot change semantics.
2. **Read live at every gate** from that record. Stop using `SASE_AGENT_AUTO_APPROVE`
   and its siblings as a source of truth (fixes D5). TUI and CLI edits write the same
   record.
3. **One inheritance rule.** Every member of an agent session inherits the session's
   effective policy unchanged: in-process successors, monitor, gate, and handoff
   follow-ups (fixes D6). Do this structurally. Do not re-emit `%auto` strings, as
   `auto_launch_prefix` does today. An explicit `%auto` in an agent-authored follow-up
   can only narrow the policy.
4. **Attenuation for new agents.** For an agent-initiated launch that a policy
   auto-approves (a later phase), the child's policy per kind is
   `min(requested, requester)`, and the parent's `child_profile` ceiling applies.
   A human-approved launch keeps the requested policy, so the launch preview must show
   it prominently. Unrelated sessions never inherit by adjacency or clan name.
5. **Roles.** `bead/work_prompt.py` emits the configured role's profile instead of a
   literal `%auto` (fixes D7). Future policy flips become config edits.

### Agent awareness

This is the cheapest high-value piece. Render about five lines into the agent's context
whenever a profile is active. Example (proposed):

```text
SASE autonomy profile: overnight — no human will see gates during this run.
- Tale plans: approved and archived automatically. Epic plans: denied — split into tales.
- Questions: not delivered to a human; decide, and list your assumptions in your final reply.
- Launch, sudo, custom gates: denied — skip the step and report it.
- Pre-authorized: rebasing and force-pushing your own PR branch.
```

This turns policy into behavior. Agents stop asking questions that will be auto-answered,
stop creating gates that will be denied, and know what is pre-approved. A `preauthorized`
list in the profile is the safe substitute for auto-allowing custom gates. Update
`/sase_questions` to say "mark your recommended option; in unattended runs it is chosen
automatically." The block is instruction-layer only (soft), and it must be labeled that
way.

### Audit and visibility

- **Records.** Every auto-resolved or denied gate records
  `policy: {profile, rule, decision, source, digest}`. The `source="auto_resolution"`
  field already exists.
- **Surfaces.**
  - The inbox, Telegram, and mobile show "auto-approved by `overnight`
    (`gates.plan=approve_archive`)".
  - The TUI chip shows the profile name instead of `⚡`/`⚡T`/`⚡E`.
  - The `A` key keeps toggling the default profile. A profile picker returns, because
    with real profiles the choice is meaningful again.
- **CLI (proposed).** Names and placement follow `cli_rules.md`, which you must read
  before implementing. Each subcommand is read-only and shares its core evaluation with
  the runtime, so an explain result can never disagree with real evaluation.
  - `sase autonomy list`
  - `sase autonomy show <profile>` (shows layer provenance)
  - `sase autonomy explain <agent|prompt>` (per gate kind: what will happen and why)
- **Coverage line.** Every view states which checks the host enforces and which are
  cooperative.

### Rust core boundary

The TUI, CLI, Telegram, mobile, the LSP, and the gate service must all agree on what a
profile means. Under `rust_core_backend_boundary`, `sase-core` therefore owns:

- the profile schema and wire types: an `EffectiveAutonomyPolicy`, an
  `AutonomyRequest {gate_kind, request_hash, proposed_option_ids, derived_effects}`, and
  an `AutonomyDecision {auto|ask|deny, option_ids, reason_code, digest}`;
- `%auto` argument parsing and directive metadata;
- layering, ceilings, and clamping;
- `evaluate()`.

Python keeps adapter I/O, gate bundles, the executor, and glue. Precedent for this split
already exists: gate decision acceptance, `%hold` validation, and `%queue` parsing all
live in core. Move the `sase-core-revision.txt` pin when the binding lands.

### Migration and compatibility

- **Zero intended behavior change in the first landing**, with three deliberate
  exceptions. Each must be called out in the changelog:
  - D1/D2: malformed or parenthesized forms now fail at launch instead of granting
    automation.
  - A tier mismatch (`:tale` on an epic, `:epic` on a tale) becomes `ask` instead of a
    mid-run `invalid_auto_argument` error.
  - The epic-worker role default ([R6](#adjusted-requirements)), if you accept it.
- **Compatibility translation.** `%auto`, `%a`, `%auto+`, and `%auto:plan` map to
  `standard`. `:tale` and `:epic` map to their reserved profiles. Translate
  `question=first` → `recommended` only after the awareness block and
  `/sase_questions` guidance ship.
- **Legacy readers.** The meta triad, the `SASE_AGENT_AUTO_*` env readers, and
  `auto_launch_prefix` stay as derived compatibility behind a **`sunset` flag**, created
  with `sase flag new` and tested in both states, until old runners drain.
- **Docs and memory.** Fix `docs/macros.md` (Auto Directive, `%auto:epic` paragraph) and
  the core `macros.md` directive row in the same change that fixes D3/D4. The memory edit
  must go through `/sase_memory_write`.
- **Launch requests.** `approval` gains `"policy"` beside `"required"` (a later phase).

### Phased rollout

| Phase | Content | Size |
| --- | --- | --- |
| **P0: truth and safety** (independent tales) | D1/D2 fail-closed parsing; D5 read meta live, stop trusting the env snapshot; D4/D3 doc–code agreement plus the stale memory row; D6 gate follow-ups carry the session's auto state and the coder keeps `:tale`; D8 `/sase_questions` ordering guidance; **D7 interim stopgap: epic land/phase workers stop auto-approving nested epics** (simplest form: emit `%auto:tale` for those roles, which turns an epic plan into an `ask` once the tier-mismatch fix lands) | Small ×5–6 |
| **P1: policy object, no new syntax** | Core schema, parse, merge, and evaluate; `agent_meta.autonomy`; compatibility translation; explicit option-ID selection; awareness block; audit fields; the three CLI commands; TUI chip | Epic (4–5 phases) |
| **P2: profiles and overrides** | `autonomy:` config with layering and the project tighten-only rule; `%auto:<profile>` and `%auto(<profile>, k=v)`; `roles:` for epic workers; `deny` and `on_ask: deny`; `question: decide/recommended` plus the schema flag; TUI picker; epic `max_depth` | Epic (3–4 phases) |
| **P3: bounded delegation** | Config-only `launch: allow(...)` with a cumulative, atomically reserved budget; retry identity and refund on failed dispatch; attenuation; launch preview showing the child's policy | Epic |
| **P4: friction reducers** | Standing approvals ("approve and allow for this session for N h", reusing `%hold`'s TTL/cap model); a `review(@model)` decision value, placed only after deterministic rules | Medium |
| **P5: hard permissions** (separate decision) | A profile `sandbox:`/`tools:` section compiled into provider-native configs where they exist (Claude permission rules or auto mode, Codex `sandbox_mode` + `prefix_rule`, OpenCode `permission`), or a bwrap/broker layer. Tool-level `ask` becomes deny-with-guidance plus custom-gate escalation, the only `ask` a single-turn agent can honor. Providers without enforcement are shown as advisory. First verify, per provider, whether deny rules are honored at all under the bypass flags SASE passes | Large; only if P1–P3 data shows tool-level risk matters |

### Open decisions for you

1. **Nested epics.** Should epic land and phase workers default to `epic: ask`, or to
   `approve(max_depth=1)`? I recommend `ask` in P0 and a depth budget in P2. 170 nested
   auto-approvals and the `sase-11e`/`sase-xe` loops are the evidence. Note that October
   so far shows only 4 land-worker auto-epics, so check whether something already
   dampened this before treating it as urgent.
2. **Should bare `%auto` keep auto-launching top-level epics?** It did so about 64 times
   from non-worker agents. I recommend keeping `standard` identical, then revisiting
   with P1 audit data.
3. **Should plans still be archived automatically?** Bare `%auto` archives every tale
   today, matching Enter. I recommend keeping `approve_archive` in `standard` and simply
   documenting it. The vocabulary lets you pick `approve` (no archive) per profile.
4. **What should absence of `%auto` mean?** I recommend that absence stays manual. Use
   a macro (for example `#auto` expanding to `%auto:<profile>`) or a TUI prompt default
   for convenience, rather than a config-level implicit profile. Machine-generated
   launches such as `/sase_run` children rely on absence meaning manual.

### What would change this recommendation

- If the friction you feel is mostly **tool-level** (shell, network, writes outside the
  workspace) rather than gate-level, pull P5 forward, keeping the same profile object.
- If after a month of P2 nobody uses more than `standard` plus one other profile,
  collapse the config to two or three built-ins. Keep the P0 fixes, roles, awareness,
  and audit, which carry most of the value.

## Sources

**Researcher reports (this swarm):**

- `auto_directive_autonomy_policy__cdx.md`: typed policy, explicit option IDs, fail-open
  parser probe, plan-commit mismatch, delegation budgets.
- `__cld.md`: usage data, inheritance and toggle defects, profiles, roles, awareness,
  attenuation.
- `__grk.md`: HITL framing, `%final` analogy, tighten-only selector, land profile.
- `__mus.md`: two-layer split, central validation, budgets, observability.
- `__gem.md`: autonomy-vs-authority framing, blind-question critique, `%caps`
  enforcement layers.

**Lead verification (sase `142636c528`):**

- **Source:**
  - `src/sase/notification_gates/adapters.py` (`resolve_auto_selection`,
    `_default_branch_selection`)
  - `src/sase/plan_gate.py` (`primary_branch`, `_plan_gate_option`)
  - `src/sase/plan_gate_turn/create.py`
  - `src/sase/main/plan_approve_handler.py`
  - `src/sase/axe/run_agent_runner_launch.py:308`
  - `src/sase/axe/run_agent_helpers_artifacts.py:161-187`
  - `src/sase/axe/run_agent_exec_questions.py:191`
  - `src/sase/user_question_actions.py`
  - `src/sase/monitor/continuation_delivery.py:216`
  - `src/sase/turns/prompt.py`
  - `src/sase/gate_turn/followup.py`
  - `src/sase/bead/work_prompt.py:187,224`
  - `src/sase/ace/tui/actions/agents/_approve.py`
  - `src/sase/agent/launch_request_planning.py:37`
  - `src/sase/llm_provider/*.py` (bypass flags)
  - `src/sase/default_config.yml` (`finalizers:`, `tmux_agent.bypass_permissions`)
  - `src/sase/macros/skills/sase_questions.md`
  - `docs/macros.md` §Auto Directive and §Plan Approval
- **Commits:** `a3e494d938` (June, non-committing auto approvals), `005f431eb8`
  (2026-07-18, primary branch = approve+commit).
- **Parser probe:** `extract_prompt_directives` with the installed sase interpreter and
  workspace `src`.
- **Data:** gate bundles under `~/.sase/interaction_requests/{plan,epic_plan,question,launch,custom,sudo}`
  (source, selection, auto argument, and creator agent); `~/.sase/prompt_history/2607–2610.json`
  (non-cancelled prompts).
- **Memory:** `macros.md`, `sase_flags.md`, `decisions:gates-never-block`,
  `decisions:single-turn-agents`.
- **Prior research:** `research:202609/sase_11e_nested_landing_loop.md`.

**External (fetched 2026-10-07):**

- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes): the
  modes `default/acceptEdits/plan/auto/dontAsk/bypassPermissions`; auto mode's classifier
  runs after the rules; project `.claude/settings.json` cannot start `auto` or
  `bypassPermissions`.
- [Claude Code permissions](https://code.claude.com/docs/en/permissions): "deny, then
  ask, then allow"; a deny at any level cannot be overridden.
- [Codex config reference](https://learn.chatgpt.com/docs/config-file/config-reference):
  `approval_policy` is `on-request | never | granular` (`untrusted` unsupported);
  `sandbox_mode` is `read-only | workspace-write | danger-full-access`; profiles are
  `<name>.config.toml` files selected with `--profile`;
  `approvals_reviewer = user | auto_review`.
- As cited by the researchers: [Codex rules](https://developers.openai.com/codex/rules),
  [Gemini CLI policy engine](https://geminicli.com/docs/reference/policy-engine/),
  [OpenCode permissions](https://opencode.ai/docs/permissions/),
  [Cedar authorization](https://docs.cedarpolicy.com/auth/authorization.html),
  [MCP tools spec](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
  [Progent (arXiv 2504.11703)](https://arxiv.org/html/2504.11703v2).
