# Making `%auto` a Real Autonomy Policy — Research, Critique, and Recommendation (cld)

_Researcher: cld · 2026-10-07 · Scope: the `%auto`/`%a` prompt directive in `sase`, its
runtime consumers, how it is used in practice, external prior art for agent permission
models, and a recommended redesign._

---

## TL;DR

- **Today `%auto` is a single on/off switch with three effects.** It auto-resolves three
  gate kinds: tale plans, epic plans, and questions (by picking the first option). Every
  other gate kind is hard-coded to refuse auto-resolution: launch, sudo, custom, HITL,
  and the triage kinds. The optional argument (`plan`/`tale`/`epic`) chooses a _plan
  branch_. It is not a permission. Provider CLIs all run with bypass flags, so `%auto`
  really is the only permission dial SASE has.
- **Usage shows the gap clearly.** Since July, **69.5% of prompts** (7,993 of 11,501)
  carry `%auto`, rising from 61% to 80% per month. Almost all of it is bare `%auto`
  (12,142 occurrences); `%auto:tale` appears 702 times and `%auto:epic` **zero times**.
  On this host, **234 epic plans were auto-approved by bare `%auto`**, and each one fans
  out a whole clan of agents. A user cannot say "auto-approve tales but stop me for epics"
  or "never stop, deny anything that needs me."
- **There are real bugs and inconsistencies to fix whatever is decided** (§3):
  - Toggling auto **off** in the TUI does not stick for a running `%auto` agent.
  - `%auto:epic` auto-answers questions, although the docs say it does not.
  - `%auto` survives monitor follow-ups but is silently dropped after launch, custom, and
    sudo gate follow-ups.
  - `%auto:tale` is lost on the coder successor, while bare `%auto` is kept.
- **Critique: the goal is right, but the obvious implementation is wrong.** Do not turn
  `%auto` into a policy mini-language typed into prompts. Prompts are authored by agents
  too (launch requests, epic worker rendering, follow-ups). Once `%auto` can grant launch,
  sudo, or custom-gate authority, a prompt-literal grant becomes a **privilege-escalation
  path**. Copy the internal precedent of `%final` instead: _config defines named
  instances; prompt text can only select them._
- **Recommendation: autonomy profiles.**
  - Config gets an `auto:` section of named **profiles**. Each profile maps a gate kind to
    a decision: `ask`, `deny`, or a kind-specific allow value. It can also set limits and
    an `on_ask` fallback.
  - Bare `%auto` selects the configured default, which reproduces today's behavior
    exactly. `%auto:<profile>` selects another profile. `%auto(<profile>, epic=ask)`
    applies **narrow inline overrides**: prompts may loosen only plan, epic, and question
    decisions, and may only tighten anything else.
  - Agent-initiated launches that are auto-approved are **clamped** to the requester's
    policy.
  - The resolved policy is persisted once in `agent_meta`, read live at every gate,
    **rendered into the agent's context**, and recorded in every auto-resolution.
  - Parsing, merging, clamping, and evaluation live in `sase-core`.
  - Hard tool-level permissions are a later, separate layer that compiles from the same
    profile. Its `ask` decision becomes "deny and escalate through a custom gate," which
    is the only `ask` a single-turn agent can honor.

---

## 1. What `%auto` actually is today

### 1.1 Mechanics, end to end

1. **Parse.** `src/sase/macro/_directive_values.py:506-527`. `%auto`/`%a` (alias at
   `_directive_types.py:105`) yields `auto_mode` (bare/`true` becomes `"plan"`, otherwise
   the raw string), `auto_enabled`, and an opaque `auto_argument`. The argument is
   validated later by whichever gate adapter consumes it (commit `a0dc62d2fa`,
   "adapter-owned auto resolution").
2. **Persist.** `src/sase/axe/run_agent_directive_metadata.py:290-300` writes these
   `agent_meta.json` keys:
   - `approve: true` (only for bare/`plan`)
   - `auto_approve_argument`
   - `auto_approve_plan_action` (`tale`/`epic`)
   - `plan: true` (tale/epic; used only for `--plan` session naming)
3. **Process env.** `src/sase/axe/run_agent_runner_launch.py:308-309` sets
   `SASE_AGENT_AUTO_APPROVE=1` in the runner process, which the provider subprocess and
   any `sase plan propose` it runs inherit. This happens only when `approve` is true.
4. **Read.** `src/sase/main/plan_approve_handler.py`:
   - `get_auto_plan_approval_action()` (:68-95) layers four env-var spellings over the
     meta keys.
   - `is_auto_approve_active()` (:382-395) is true if _any_ argument is present, or the
     env var, or `approve`.
5. **Decide.** Each `GateAdapter` in `src/sase/notification_gates/adapters.py:449-599`
   carries an `auto_policy`, one of `approval`, `first`, or `forbidden`.
   `resolve_auto_selection` (:46-76) validates the argument and selects the primary
   branch's default options. Auto gates skip notification and resolve inline with
   `source="auto_resolution"` (`notification_gates/service.py`). The creator keeps running
   in-process at the cost of one agent (decision `gates-never-block`).

### 1.2 Gate coverage

| Gate kind                                 | `auto_policy`     | What `%auto` does                                                                                                        |
| ----------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `plan` (tale tier)                        | approval          | Approves. Bare `%auto` approves _without_ an SDD commit (`a3e494d938`); `:tale` approves and commits.                    |
| `epic_plan`                               | approval          | Bare or `:epic` commits the SDD epic, initializes beads, and **launches the epic**.                                      |
| `question`                                | first             | Picks the **first option of every question**. Gets only a bool, so the argument is ignored.                              |
| `launch` (`/sase_run`)                    | forbidden         | Never. `"auto": False` is hard-coded (`agent/launch_request_gate.py:254`); request `approval` must be `"required"` (`launch_request_planning.py:37-43`). |
| `sudo`, `custom`, `hitl`, triage kinds    | forbidden         | Never. Setting `auto` raises `auto_not_supported`.                                                                       |

Two consequences matter for the redesign.

**The agent picks the blast radius.** Under bare `%auto`, whether a run ends in one coder
or a whole epic clan depends on which tier _the agent_ authored. The user has no way to
say "tales yes, epics no." `%auto:tale` on an epic plan is a hard `invalid_auto_argument`
error, not a fallback to human review (`_plan_gate_metadata.py:62-74`).

**There is already an unused extension point.** The launch-request schema has an
`approval` field whose only legal value is `"required"`. Someone anticipated a policy
here.

### 1.3 Where "permissions" actually live in SASE

| Layer                   | Mechanism                                                                                                                                         | Enforced by                              | `%auto` role                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------- |
| Provider tools (hard)   | All providers run with bypass flags: `--dangerously-skip-permissions` (claude, opencode, agy), `--dangerously-bypass-approvals-and-sandbox` (codex), `--yolo` (qwen), `bypassPermissions` (grok), `--disable-approval` (muse) | Nothing; the ephemeral workspace clone is the de facto sandbox | none |
| Host gates (checkpoints) | Plan, epic, question, launch, sudo, and custom gate turns                                                                                         | Host; gate turns end the agent's turn    | **the only dial**                |
| Instructions (soft)     | Skills and memory rules: `/sase_run` for launches, custom gates for dangerous commands, the memory-write authorization list, no direct commits    | Agent compliance                         | none; **the agent is never told it is in `%auto`** |
| Completion              | `%final`, `#commit`/`#pr`/`#propose`, host finalizers                                                                                             | Host (decision `host-owned-completion`)  | none                             |

The completion layer is already well designed: config-defined instances, prompt-selected,
and host-enforced. It is the template the gate layer should follow.

### 1.4 Propagation today: ad hoc per path

| Path                                                                | Inherits `%auto`?                                                                                                                                                                                                                         |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| In-process successor (plan coder, question follow-up, pipe)         | Only the `approve` key is copied (`axe/run_agent_helpers_artifacts.py:161-187`), and the env var lingers in-process. **Bare `%auto` survives; `:tale`/`:epic`/`<arg>` do not.**                                                         |
| Monitor follow-up                                                   | Yes, re-emitted as a prompt prefix by `auto_launch_prefix` (`monitor/continuation_delivery.py:216-229`). This was added only on 2026-09-15 (`61febdcc68`).                                                                              |
| Gate-turn follow-up (launch, custom, sudo, non-auto plan/question)  | **No.** The prefix is only `#fork`/`%model`/`%effort` (`turns/prompt.py:12-30`, used at `gate_turn/followup.py:290`, `followup_prompt.py:147`).                                                                                         |
| New agents (`sase run`, launch requests)                            | No. `SASE_AGENT_*` env is scrubbed (`agent/env_hygiene.py`).                                                                                                                                                                              |
| Epic phase and land workers                                         | Always a hard-coded bare `%auto` (`bead/work_prompt.py:187, 224`), whatever the parent had. History: land auto removed (`5074543f85`), changed to `%auto:tale` (`64728c413a`), then back to bare (`496c7945ea`). Three policy flips in code. |
| `%repeat` / `%alt`                                                  | Yes, per segment (textual).                                                                                                                                                                                                                |

The inheritance contract is whatever each code path happened to implement. Hard-coded
policy also keeps churning in code (the epic workers) when it should be config.

---

## 2. Evidence from real use (athena, Jul 1 – Oct 7 2026)

These were measured from `~/.sase/prompt_history/*.json` (non-cancelled entries) and the
`~/.sase/interaction_requests/<kind>/` bundles.

| Metric                                     | Value                                                                                                                                             |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prompts containing `%auto`/`%a`            | **7,993 / 11,501 (69.5%)**. Jul 61%, Aug 68%, Sep 80%.                                                                                            |
| Directive occurrences                      | bare **12,142** · `:tale` **702** · `:epic` **0** · any keyword-arg form **0**                                                                     |
| Gate bundles by kind                       | plan 1,767 · epic_plan 712 · question 76 · launch 49 · custom 31 · sudo 17                                                                        |
| Auto-resolved (`source=auto_resolution`)   | plan 563 · **epic_plan 234 (all `argument: null`, i.e. bare `%auto`)** · question 46 (vs. 20 human-answered) · launch/custom/sudo 0 (forbidden)    |

Older bundles record a legacy `plan_response` source label, so human versus auto counts
for plans are lower bounds.

What the numbers say:

1. **`%auto` is effectively a binary flag that is on by default.** The argument
   vocabulary went almost unused. "More arguments on the same string" is not what users
   reach for.
2. **The default carries the most risk.** Bare `%auto` silently promoted 234 epics to
   launch. Some of these are probably epic phase workers (hard-coded bare `%auto`) whose
   phase plan came out epic-tier, because `496c7945ea` preserves the authored tier. That
   is nested fan-out with no human checkpoint.
3. **Auto-answered questions are common** (46 versus 20 human-answered). Nothing tells
   the asking agent to put its recommended option first, and nothing tells it that no
   human will read the question (§3.4).

---

## 3. Defects and inconsistencies (fix regardless of the redesign)

Each of these is small and independently shippable.

1. **The TUI toggle-off does not stick for a live bare-`%auto` agent.** `A` toggles
   through `ace/tui/actions/agents/_approve.py`, which removes the `approve` meta key and
   the `%auto` prompt directive. But the runner already exported
   `SASE_AGENT_AUTO_APPROVE=1` (`run_agent_runner_launch.py:309`), and nothing clears it.
   Both readers OR the env var with the meta key (`plan_approve_handler.py:92, 392`). So
   the next plan or question gate in that process still auto-resolves. Toggling **on**
   works because meta is read fresh. (`80f279a58a` shows mid-run toggling is an intended
   feature.)
2. **The `%auto:epic` question behavior contradicts the docs.** `docs/macros.md` (Plan
   Approval section) says `%auto:epic` "does not automatically answer unrelated
   questions." But `is_auto_approve_active()` returns true whenever
   `auto_approve_argument` exists, and `run_agent_exec_questions.py:191` passes exactly
   that bool. So `%auto:epic` (and `:tale`, and `:foo`) **does** auto-answer questions.
   With 0 recorded uses this is low-stakes, but code and docs must agree.
3. **Inheritance is inconsistent** (§1.4).
   - `%auto` survives a monitor handoff but not a launch, custom, or sudo gate handoff.
     An unattended `%auto` agent that asks permission to launch a helper comes back
     _without_ `%auto`, and its next plan parks for a human.
   - `%auto:tale` is lost on the coder successor, while bare `%auto` is kept.
4. **The question auto-answer is semantically blind.** It picks option #1 of each
   question, and the `/sase_questions` skill gives no ordering guidance. At minimum, the
   skill should say "list your recommended option first; in unattended runs it is chosen
   automatically."
5. **Policy is hard-coded in epic rendering.** `bead/work_prompt.py` appends a literal
   `%auto` for phase and land workers, so every policy change is a code change (three
   flips so far).

---

## 4. Prior art: how other agent harnesses model this

| System                     | Model                                                                                                                                                                                                                                                                                                                     | Lesson for SASE                                                                                                                                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Claude Code**            | Rules are `allow`/`ask`/`deny` with tool specifiers (`Bash(npm test:*)`, `Edit(src/**)`). **Deny beats ask, and ask beats allow.** A permission _mode_ supplies the default when no rule matches (`default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`). Settings layer managed > CLI > local > project > user. Headless runs can route prompts to an MCP tool (`--permission-prompt-tool`). **Auto mode** uses a model-based classifier to approve in-scope actions and block escalations. | Separate _mode_ (the default stance) from _rules_ (exceptions). Use most-restrictive-wins merging and layered config. A classifier or reviewer is a credible third resolver beside "human" and "rule."   |
| **Codex CLI**              | Two orthogonal axes: `approval_policy` (`untrusted`/`on-request`/`never`, or granular) × `sandbox_mode` (`read-only`/`workspace-write`/`danger-full-access`). **Named `[profiles.<name>]`** in `config.toml` are selected with `-p`. Starlark `prefix_rule` exec policies decide `allow`/`prompt`/`forbidden`, most restrictive wins, testable with `codex execpolicy check`. | Named profiles selected by a short flag are the right UX. "Never ask" (`approval_policy=never`) is a first-class stance for unattended runs. Ship a dry-run "check/explain" command.                   |
| **Gemini CLI**             | TOML policy engine with rules (`toolName`, `commandPrefix`, `argsPattern`) deciding `allow`/`deny`/`ask_user`, using **tiered priorities** (default < extension < workspace < user < admin).                                                                                                                              | Explicit tiering avoids "which file wins?" confusion. Admin, or in SASE's case config, outranks anything a workspace or prompt can say.                                                                    |
| **OpenCode**               | A `permission` map with `allow`/`ask`/`deny` and glob patterns per tool, **per-agent overrides** merged over global config, and an `ask` UI offering **once / always (this session) / reject**.                                                                                                                         | Per-agent-role policy (SASE: epic phase/land roles) and **"approve and remember for this session"** standing approvals both remove friction without upfront configuration.                              |
| **Progent** (arXiv 2504.11703) | A JSON-Schema DSL of per-tool allow/forbid with argument conditions, fallback actions, and dynamic policy updates, enforced deterministically outside the model.                                                                                                                                                       | Least privilege works best as a deterministic, out-of-model check with typed fallbacks. "Deny" should come back to the agent as information it can act on, not a crash.                                 |

The common pattern across all of them:

- The decision space is **{allow, ask, deny}**.
- **Most-restrictive-wins** merging.
- **Named, layered configuration** with a terse selector.
- A **default stance plus exceptions**.
- An **explain/check** tool.

None of them makes the end user type the policy body into each request.

**What SASE cannot copy directly.** In those tools, `ask` blocks mid-turn on a human. In
SASE an agent is single-turn (decisions `single-turn-agents` and `gates-never-block`), so
`ask` must mean "end the turn into a gate turn." For tool-level rules, which fire
mid-turn inside the provider, `ask` can only be implemented as **deny with guidance**:
the agent is told to request the action through a custom gate. Conveniently, gate turns
already execute reviewed argv commands host-side. "Provider denies, agent escalates
through a custom gate, human approves, gate shell runs the exact command" is therefore a
complete `ask` that fits SASE's model.

---

## 5. Critique of the plan

### 5.1 What is right

- **The need is real and measured.** `%auto` is on in 70–80% of launches, yet it cannot
  express the distinctions that matter: tale versus epic, questions versus plans,
  unattended versus attended, or whether helpers may be launched.
- **`%auto` is the right home.** It is already the de facto autonomy dial, it has strong
  muscle memory, and it already appears in TUI chips and toggles. A second competing
  directive would be worse.
- **Making it configurable stops policy churning in code.** The three epic-worker flips
  show this.

### 5.2 What is risky or wrong-headed

1. **The prompt is not a trust boundary.** `%auto` text is written by humans _and_ by
   machinery and agents: launch requests from `/sase_run`, epic rendering, monitor
   follow-ups, and handoffs. Today that is harmless only because `%auto` cannot unlock
   anything dangerous, and launch approvals are always human-reviewed. If a prompt
   literal can grant `launch=allow` or `custom=allow`, an agent can mint a child with more
   authority than it has. **Grants of escalating authority must come from config, and
   agent-authored launches must be attenuated** (capability-style narrowing).
2. **Mixing branch choice with permission confuses users.** `tale` and `epic` say _which
   option to pick_. "Is a human required here?" is a different question. Growing more
   opaque arguments on one string (`%auto:foo`, adapter-interpreted) makes the directive
   _less_ intuitive, which is the opposite of the goal. Keep the per-kind decision
   explicit (`epic=ask`, `plan=tale`).
3. **Gate-level policy is a checkpoint system, not enforcement.** Custom gates, the
   memory-write rules, and `/sase_run` rely on the agent choosing to gate. Calling the
   result "permissions" will over-promise unless the docs say plainly that hard
   enforcement is a later layer.
4. **Auto-allowing custom gates defeats their purpose.** An agent creates a custom gate
   precisely when it wants a human (the `/sase_gate` skill says never enable `auto` to
   bypass the reviewer). The right way to pre-authorize an action is to **tell the agent
   up front** that the action is pre-approved, so it never creates the gate. That is an
   instruction-layer feature driven by the same profile, not an auto-allow of custom
   gates.
5. **There is a complexity tax.** Profiles, overrides, inheritance, and clamping are
   powerful but opaque. Without an `explain` surface and visible effective policy in the
   TUI and launch preview, users will not know what a run is allowed to do. That is
   strictly worse than today's on/off switch.

### 5.3 Would I take a different approach?

Partly. I would not build "a more powerful `%auto` directive." I would build **a policy
object (an autonomy profile) that `%auto` selects**:

- It is defined in config, like `finalizers:` and model aliases.
- Its resolution happens once, at launch.
- It is persisted on the agent and read live at each gate.
- It is shown to the agent and to the user.
- It is inherited by one uniform rule.

The directive stays as short as it is today. I would also add two things the plan does
not mention:

- **Standing approvals**: "approve and allow this for the session for N hours," on the
  gate itself, reusing the scope and TTL model of `%hold` (default 2h, cap 12h).
- **Agent awareness**: rendering the effective policy into the agent's context.

Both reduce friction more than any argument syntax would.

---

## 6. Adjusted requirements (explicitly called out)

| #   | Requirement                                                                                                                                                                                                                                                                             | Status vs. the request                                        |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| R1  | `%auto` expresses a **per-gate-kind decision** (`ask` / `deny` / kind-specific allow), not one opaque argument.                                                                                                                                                                         | Core of the request, sharpened                                |
| R2  | Policies live in config as **named profiles**, layered builtin < user < project. Bare `%auto` selects a configured default that **reproduces today's behavior exactly**.                                                                                                               | **CHANGED**: power moves from prompt syntax to config         |
| R3  | **Inline overrides are narrow.** Prompt literals may loosen only `plan`/`epic_plan`/`question`, and may only _tighten_ `launch`/`sudo`/`custom`/`hitl`. Loosening those requires a config profile.                                                                                       | **ADDED** (trust boundary)                                    |
| R4  | **Attenuation.** An agent-initiated launch that is _auto-approved_ gets `min(requested, requester's effective)` per kind. A launch a human approves keeps the requested policy, which the launch preview must display.                                                                    | **ADDED**                                                     |
| R5  | **One inheritance rule** for every successor in an agent session: in-process, monitor, gate, and handoff. Epic worker policy comes from config roles, not literals.                                                                                                                     | **ADDED** (fixes §3.3 and §3.5)                               |
| R6  | **Agent awareness.** The effective policy is rendered into the agent's context as a short block.                                                                                                                                                                                         | **ADDED**                                                     |
| R7  | **Live and auditable.** The policy is persisted once (`agent_meta.auto`) and read fresh at each gate (no env snapshot). TUI edits write the same record. Every auto-resolution records `{profile, rule, decision}`.                                                                      | **ADDED** (fixes §3.1)                                        |
| R8  | **An unattended stance.** A profile can declare `on_ask: deny`, so a run never parks on a human: any `ask` becomes an immediate typed denial the agent can act on.                                                                                                                        | **ADDED**                                                     |
| R9  | **Rust core owns** parse, merge, clamp, and evaluate (TUI, CLI, Telegram, and mobile must agree), per `rust_core_backend_boundary`.                                                                                                                                                      | **ADDED** (project rule)                                      |
| R10 | Hard, tool-level provider permissions are **out of scope for v1**. The profile schema reserves a `tools:` section so the later layer compiles from the same object.                                                                                                                      | **DEFERRED** (explicitly not promised)                        |
| —   | Rename `%auto`, or add a second permissions directive.                                                                                                                                                                                                                                  | **DROPPED**: muscle memory (70% of prompts); one dial is better |
| —   | Auto-allowing custom gates.                                                                                                                                                                                                                                                             | **DROPPED**: use pre-authorization in the awareness block instead |

---

## 7. Design options compared

| Option                                                                        | Expressiveness                     | Safety                                  | Intuitiveness                    | Cost        | Verdict                                              |
| ----------------------------------------------------------------------------- | ---------------------------------- | --------------------------------------- | -------------------------------- | ----------- | ---------------------------------------------------- |
| A. More opaque arguments (`%auto:unattended`, adapter-interpreted)            | Low; one string per adapter        | OK                                      | Poor: the same word means different things per gate | Low | Reject                                       |
| B. Full keyword policy in the prompt (`%auto(plan=tale, launch=allow(max=3), …)`) | High                            | **Poor**: prompt-literal escalation     | Poor: verbose on every launch    | Medium      | Reject as the primary form; keep a narrow subset (R3) |
| **C. Config profiles + selector + narrow overrides** (`%auto`, `%auto:overnight`, `%auto(epic=ask)`) | High (config) | Good: config-only grants plus clamp | Good: terse daily use, explicit when needed | Medium | **Recommend** |
| D. Separate `%perm` directive for tool rules                                  | High                               | Same as B                               | Two dials to learn               | High        | Reject; reserve `tools:` inside the profile instead   |
| E. Reviewer or classifier resolution (`plan=review(@large)`)                  | High for plans                     | Good (model-in-the-loop)                | Good                             | Medium–High | **Later phase**, as a decision value inside C        |

---

## 8. Recommended solution: autonomy profiles selected by `%auto`

### 8.1 Concept

An **autonomy profile** is a named, config-defined policy. For each gate kind it says
whether the host should resolve the gate (and how), deny it, or ask a human. It also
says what to do when a human would be needed but should not be (`on_ask`). `%auto`
selects a profile. Absence of `%auto` keeps meaning "a human decides everything," as
today.

### 8.2 Config sketch (follows the `finalizers:` instance pattern)

```yaml
auto:
  default: standard            # what bare %auto / %a selects
  roles:                        # replaces literal %auto in bead/work_prompt.py
    epic_phase: standard
    epic_land: standard
  profiles:
    standard:                   # == today's bare %auto, bit-for-bit
      description: Approve authored plans; answer questions with the first option.
      gates:
        plan: approve           # tale tier: approve, no SDD commit
        epic_plan: epic         # commit SDD epic + launch it
        question: first
        launch: ask
        sudo: ask
        custom: ask
      on_ask: park              # park | deny
    # compat profiles keep the old spellings working
    plan:  { extends: standard }
    tale:  { extends: standard, gates: { plan: tale,  epic_plan: ask } }   # today: error on epic
    epic:  { extends: standard, gates: { plan: ask,   epic_plan: epic } }  # today: error on tale
    careful:
      extends: standard
      gates: { plan: tale, epic_plan: ask, question: ask }
    overnight:                  # "I'm walking away"
      extends: standard
      gates:
        plan: tale
        epic_plan: ask          # parks... but on_ask turns it into a typed denial
        question: decide
        launch: { allow: { max_slots: 2, max_model: "@medium", child_profile: careful } }
        sudo: deny
        custom: deny
      on_ask: deny
      preauthorized:            # rendered into the agent's context, see 8.6
        - "Rebasing and force-pushing your own PR branch."
```

**Decision vocabulary per kind.** Each adapter declares which values it supports, which
replaces today's `auto_policy` string with a capability set:

| Kind        | Values                                                                                                                                                                                                    |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `plan`      | `ask` · `approve` · `tale` · `deny` · _(later)_ `review(<model>)`                                                                                                                                         |
| `epic_plan` | `ask` · `epic` · `commit` (record SDD but do not launch, if the epic adapter exposes it) · `deny` · _(later)_ `review(<model>)`                                                                            |
| `question`  | `ask` · `first` · `recommended` (agent-flagged option, falling back to first) · `decide` (resolve with "no human available; choose, and record your assumption") · `deny`                                 |
| `launch`    | `ask` · `deny` · `allow` with limits (`max_slots`, `max_per_session`, `max_model`, `tribe`/`hood` scope, `child_profile` ceiling)                                                                          |
| `sudo`      | `ask` · `deny`. No allow in v1; a later exact-argv allowlist is possible.                                                                                                                                 |
| `custom`    | `ask` · `deny`. Pre-authorization goes through the awareness block, not auto-allow.                                                                                                                       |
| `hitl`      | `ask` · `deny`                                                                                                                                                                                            |

**`deny` semantics.** The gate is created and settled synchronously with a typed
`denied_by_policy` response, and the requester continues in-process. This is the same
cost model as today's auto-resolution ("costs exactly one agent").

### 8.3 Directive grammar

Use the same argument grammar as `%queue` and `%hold`: positional plus keyword, with
canonicalized aliases.

```
%auto                         # default profile (today's behavior)
%a:careful                    # select a profile
%auto(epic=ask)               # default profile + override
%auto(overnight, q=decide)    # profile + override; q→question, epic→epic_plan
%auto:tale                    # compat profile (still works)
```

Validation is in the parser, not deferred to adapters. Unknown profiles, unknown kinds,
unsupported values, and R3 violations ("`launch=allow` must come from a profile") fail
**at launch**. Today, `%auto:foo` survives until `sase plan propose` rejects it
mid-run.

### 8.4 Resolution, layering, attenuation, inheritance

1. **Resolve once at launch.** The order is builtin < user < project profile, then
   inline overrides. Store the **resolved** policy plus `profile`, `overrides`, `source`
   (`prompt|tui|inherited|epic_role|launch_clamp`), and a config digest in
   `agent_meta.json` under one `auto` key. Later config edits do not silently change a
   running agent. `%dispatch` ships the resolved record, so remote config drift cannot
   change semantics.
2. **Read live at every gate** from that record. Drop the `SASE_AGENT_AUTO_APPROVE`
   snapshot as a source of truth; this fixes §3.1. The TUI `A` key keeps toggling the
   default profile on and off. A profile picker returns (for example in the command
   palette or on a second key), because with real profiles a choice is meaningful again.
   The September removal of the menu was right for three plan branches.
3. **Uniform inheritance.** Every member of the same agent session inherits the
   session's effective policy unchanged, whether it is an in-process successor, a
   monitor, gate, or handoff follow-up. An explicit `%auto` in an agent-authored
   follow-up prompt is clamped.
4. **Attenuation for new agents.** For agent-initiated launches that a policy
   auto-approves, the child's policy per kind is `min(requested, requester)` under the
   ordering `allow > ask > deny`. The parent's `child_profile` ceiling also applies. A
   **human-approved** launch keeps the requested policy, so the launch preview must show
   the child's effective profile prominently.
5. **Epic roles.** `bead/work_prompt.py` emits `%auto:<auto.roles.epic_phase>` instead of
   a literal. Policy flips become config edits.

### 8.5 Merging rule

Use **most-restrictive-wins for clamps**, as Claude Code, Codex, and Gemini CLI do, and
**most-specific-wins for authoring**: a profile overrides what it extends, and inline
overrides beat the selected profile within R3 limits. Write this down once and expose
it through `explain`.

### 8.6 Agent awareness (the cheapest high-value piece)

Render about 5 lines into the agent's context whenever `%auto` is active. Examples:

```
SASE autonomy profile: overnight — no human will see gates during this run.
- Plans: tale plans are approved and committed automatically; epic plans are denied — split work into tales.
- Questions: not delivered to a human; decide, and list your assumptions in your final reply.
- Launch requests: auto-approved up to 2 slots at ≤ @medium; children run under `careful`.
- Sudo and custom gates: denied — skip the step and report it.
- Pre-authorized: rebasing and force-pushing your own PR branch.
```

This turns policy into behavior. Agents stop asking questions that will be auto-answered,
stop creating gates that will be denied, and know what is pre-approved. It is also where
`preauthorized` lives, which is the safe substitute for auto-allowing custom gates.
Update `/sase_questions` to say "list your recommended option first."

### 8.7 Audit and visibility

- An auto-resolved or denied response records
  `policy: {profile, rule: "gates.epic_plan", decision, source}`.
- The notification inbox, Telegram, and mobile show "auto-approved by `overnight`
  (`gates.plan=tale`)."
- The TUI row chip shows the profile name; today it shows only `⚡`/`⚡T`/`⚡E`.
- Proposed CLI, to be named per `cli_rules`. These are alphabetized subcommands with
  short aliases, and bare `sase auto` delegates to `list`:
  - `sase auto list` — profiles with sources.
  - `sase auto show <profile>` — resolved profile with layer provenance.
  - `sase auto explain <agent|prompt>` — the effective policy and, per gate kind, what
    will happen. This is the analogue of `codex execpolicy check`.

### 8.8 Rust core boundary

The litmus test applies: the TUI, CLI, Telegram, mobile, and the gate service must all
agree on what a profile means. So `sase-core` should own:

- the profile schema,
- directive-argument parsing for `%auto`,
- layering,
- clamping,
- `evaluate(gate_kind, policy) -> Decision`.

The Python adapters call the binding. `GateAdapter.auto_policy` becomes a declared
capability set. The `sase-core-revision.txt` pin moves accordingly. Directive parsing
already partially lives in core (`macro/queue_directive.py`), and so does gate decision
acceptance (`notification_gates/decision.py`), so there is precedent on both sides.

### 8.9 Migration and compatibility

- **Zero behavior change in the first landing.** `standard` reproduces bare `%auto`, and
  the compat profiles reproduce `:plan`/`:tale`/`:epic`. There are two deliberate
  exceptions, each called out:
  - The tier mismatch (`:tale` on an epic) becomes `ask` (park for a human) instead of a
    hard error.
  - The compat `epic` profile's question decision must be chosen. Code says `first`,
    docs say `ask`. I recommend keeping code behavior (`first`) and fixing the doc,
    because there are 0 historical uses and it causes the least surprise.
- Legacy meta keys (`approve`, `auto_approve_argument`, `auto_approve_plan_action`), the
  `SASE_AGENT_AUTO_*` env readers, and `auto_launch_prefix` stay as **derived
  compatibility** behind a **`sunset` flag**, created with `sase flag new` per
  `sase_flags`, until old runners drain. Profiles themselves are a **config field, not a
  flag**: users choose them forever.
- Launch requests: `approval` gains `"policy"` (meaning "resolve per the requester's
  profile") beside `"required"`.

### 8.10 Phased rollout

| Phase                              | Content                                                                                                                                                                                                                                                                             | Size      |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **P0 — fixes** (independent tales) | §3.1 toggle-off env bug; §3.2 epic/question doc–code agreement; §3.3 uniform inheritance (gate follow-ups carry the session's policy, the coder keeps `:tale`); §3.4 question-skill ordering guidance.                                                                                | Small ×4  |
| **P1 — profiles, no behavior change** | Core schema, parse, merge, and evaluate; `auto:` config with `standard` and compat profiles; `%auto:<profile>` and R3-limited overrides for plan/epic/question; `agent_meta.auto`; awareness block; audit fields; `sase auto list/show/explain`; TUI chip shows the profile name.      | Epic (4–6 phases) |
| **P2 — deny, launch, unattended**  | `deny` for all agent-facing kinds; `on_ask: deny`; launch `allow` with limits and attenuation; launch preview shows the child's effective policy; `auto.roles` for epic workers.                                                                                                     | Epic (3–4 phases) |
| **P3 — friction reducers**         | Standing approvals ("approve and allow `<kind>` for this session/tribe for N h," with `%hold`-style scope/TTL/cap); `review(<model>)` decisions where a reviewer agent's gate turn answers plan gates.                                                                               | Medium    |
| **P4 — hard permissions (separate decision)** | Compile the profile's `tools:` section into provider-native configs where they are rich enough: Claude permission rules or auto mode, Codex sandbox + `prefix_rule`, Gemini policy TOML, OpenCode `permission`. `ask` → deny-with-guidance → custom-gate escalation (§4). Other providers stay bypass and are documented as such. | Large; only if P1–P3 data show tool-level risk matters |

For P4, verify per provider whether deny rules are honored at all under the bypass flags
SASE currently passes. If they are not, the adapter must switch from bypass to an
explicit "allow everything except these" mode. That is consistent with the
`adapters-normalize-harnesses` decision.

### 8.11 Open questions for Bryan

1. **Should bare `%auto` keep auto-launching epics?** It did 234 times. My lean: keep
   `standard` identical in P1, then look at P1 audit data. If most auto-epics come from
   nested phase workers, set `auto.roles.epic_phase` to `epic_plan: ask` (or `deny`, to
   force tales) rather than changing the human default.
2. **Should absence of `%auto` ever mean anything else** (for example a per-project
   implicit profile, given 80% adoption in September)? My lean is **no**. Absence is the
   human-in-the-loop safety default, and a `#macro` that expands to `%auto:<profile>`
   already gives a one-token shortcut, since macros can emit directives (`#tribe`, `#t`).
3. **What should questions do by default: `first`, `recommended`, or `decide`?** My lean:
   `recommended` in `standard` (backward compatible, because it falls back to first) and
   `decide` in unattended profiles.
4. **Which launch limits actually matter?** Slots, model size, tribe/hood scope, child
   ceiling, or a per-hour budget?

### 8.12 What would change my mind

- If the friction users feel is mostly **tool-level** (bash, network, file writes
  outside the workspace) rather than gates, skip to P4 sooner, keeping the same profile
  object.
- If, after a month of P1, nobody uses more than `standard` plus one other profile,
  collapse the config back to two or three builtins and keep the gains from P0, the
  awareness block, and audit.

---

## Sources

Internal (sase repo, read at `ca5eff431f`):

- `src/sase/macro/_directive_values.py`, `_directive_types.py`, `_directive_edit_wait.py`
- `src/sase/axe/run_agent_directive_metadata.py`, `run_agent_runner_launch.py`,
  `run_agent_exec_questions.py`, `run_agent_helpers_artifacts.py`
- `src/sase/main/plan_approve_handler.py`, `src/sase/plan_gate_turn/create.py`,
  `src/sase/_plan_gate_metadata.py`
- `src/sase/notification_gates/adapters.py`
- `src/sase/agent/launch_request_planning.py`, `launch_request_gate.py`
- `src/sase/monitor/continuation_delivery.py`, `src/sase/turns/prompt.py`,
  `src/sase/gate_turn/followup.py`
- `src/sase/bead/work_prompt.py`
- `src/sase/default_config.yml` (`finalizers:`)
- `docs/macros.md` (Auto Directive, Plan Approval)
- Skill sources `sase_gate.md`, `sase_questions.md`, `sase_run.md`, `sase_memory_write.md`
- Commits `36559c4b70`, `a0dc62d2fa`, `a3e494d938`, `64728c413a`, `496c7945ea`,
  `5074543f85`, `61febdcc68`, `80f279a58a`, `651a32ee00`
- Memory: `macros.md`; decisions `gates-never-block`, `single-turn-agents`,
  `host-owned-completion`, `guarded-recipes`; `sase_flags.md`, `cli_rules.md`
- Local data: `~/.sase/prompt_history/2607–2610.json`,
  `~/.sase/interaction_requests/*`

External:

- [Auto mode for Claude Code (Claude blog)](https://claude.com/blog/claude-code-auto-mode)
- [Claude Code auto mode (Anthropic Engineering)](https://anthropic.com/engineering/claude-code-auto-mode)
- [Claude Code headless mode / `--permission-prompt-tool`](https://docs.claude.com/en/docs/claude-code/headless)
- [Claude Code permission modes & rules (community summary)](https://stevekinney.com/courses/ai-development/claude-code-permissions)
- [Codex rules (execpolicy `prefix_rule`)](https://developers.openai.com/codex/rules)
- [Codex sandboxing concepts](https://developers.openai.com/codex/concepts/sandboxing.md)
- [Codex configuration reference (profiles, approval_policy, sandbox_mode)](https://developers.openai.com/codex/config-reference)
- [Codex CLI two-axis approval/sandbox model (D. Vaughan)](https://codex.danielvaughan.com/2026/04/08/codex-cli-security-model-approval-sandbox-two-axis/)
- [Gemini CLI policy engine](https://geminicli.com/docs/reference/policy-engine/)
- [OpenCode permissions](https://opencode.ai/docs/permissions/)
- [Progent: Programmable Privilege Control for LLM Agents (arXiv 2504.11703)](https://arxiv.org/html/2504.11703v2)
