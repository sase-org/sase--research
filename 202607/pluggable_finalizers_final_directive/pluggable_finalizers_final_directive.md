---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
kind: consolidated
sources:
  - pluggable_finalizers_final_directive__a.md  # research.v.cdx
  - pluggable_finalizers_final_directive__b.md  # research.v.cld
---

# Pluggable finalizers and the `%final` directive

Consolidated from two independent research passes plus a third verification pass. Every code anchor below was
re-verified against the working tree at `84d47aa78` (2026-07-30); claims that only one report made and that did not
survive verification are called out explicitly.

## Question

SASE has exactly one finalizer: a hard-coded, provider-neutral commit finalizer that runs after a successful LLM turn
and refuses to let an agent finish with a dirty workspace. Generalize it so that users can define their own finalizers,
disable defaults (current and future), run several per launch, configure each one (prompt, script, retries, triggers,
dependencies), let plugins ship their own, and let agents hand data to finalizers through sase variables. What is the
right shape, and what should `%final` mean?

**Short answer.** Make `finalizers:` a **keyed config map** — the definition site — whose entries are a three-part
contract: *host-evaluated trigger → bounded prompt passes that ask the agent to record sase variables → a script that
performs the deterministic effect → re-evaluate*. Make `%final` a **selection-and-bounded-override** directive over that
registry, never a definition site. Reuse the axe-chop config vocabulary, script discovery, `--context` protocol, result
SDK, and Rust decision engine rather than building a fifth mechanism. Force plugin-contributed finalizers to be
**opt-in** so `pip install` can never activate post-run code. Sequence the whole thing after the in-flight `sase-be`
epic, which is already building the commit finalizer's script stage.

---

## 1. Verified ground truth

### 1.1 The finalizer is one function, not a system

`run_commit_finalizer` (`src/sase/llm_provider/commit_finalizer.py:128`) is called from exactly one place —
`src/sase/llm_provider/_invoke.py:308`, immediately after `provider.invoke(...)` at `:301`, inside the same `try:`.
There is no registry, no dispatch, no name. Commit semantics are baked in at every layer:

| Layer          | File                                     | What is hard-coded                                                   |
| -------------- | ---------------------------------------- | -------------------------------------------------------------------- |
| Gate           | `commit_finalizer.py:148-186`            | `SASE_DISABLE_COMMIT_STOP_HOOK` → `config.enabled` → `SASE_AGENT_TIMESTAMP` |
| Trigger        | `commit_finalizer_state.py`              | "is any enforced repo dirty?" — main, linked, external, SDD sidecars |
| Prompt         | `commit_instructions.py`, `commit_finalizer_prompting.py` | Bead-close + commit-skill text, per-repo `cd` framing |
| Effect         | the LLM itself, shelling to `/sase_git_commit` | No script; the model performs the side effect mid-conversation  |
| Loop           | `commit_finalizer.py:230+`               | `for pass_number in range(1, config.max_passes + 1)`                 |
| Failure        | `commit_finalizer.py`                    | `raise CommitFinalizerError` → the whole run is recorded failed       |

Configuration is two keys (`commit.finalizer.{enabled,max_passes}`, `default_config.yml:791-794`, schema
`sase.schema.json:1685-1703`, loader `commit_finalizer_config.py:41-59`) plus one process-global env escape hatch.

### 1.2 Its ordering guarantees are the thing worth preserving

Because it runs inline in `_invoke.py`, it completes **before** `done.json`
(`run_agent_exec_finalize.py:619`), before status/claim release (`run_agent_runner_lifecycle.py`), and before the
completion notification (`run_agent_runner_finalize.py`). Family members each run their own runner process and therefore
their own finalizer, so per-member ordering holds automatically. Finalization is owned by the process that owns the
agent invocation, not by provider-specific stop hooks — that is the correct seam and any generalization must keep it.

### 1.3 Non-obvious and load-bearing: it is per-*turn*, not per-*agent*

Only report **B** found this, and it verifies. `run_commit_finalizer` is called unconditionally after every
`provider.invoke()` in `invoke_agent`, and `invoke_agent` is the shared LLM entry point for far more than the agent
runner:

- mentors — `src/sase/workflows/mentor.py:332`
- CRS — `src/sase/workflows/crs.py:221`
- fix hooks — `src/sase/axe/fix_hook_runner.py:198`
- workflow prompt steps — `src/sase/xprompt/workflow_executor_steps_prompt.py:340`
- ACE workflow handlers — `src/sase/ace/handlers/workflow_handlers.py:313` *(missed by both reports)*
- standalone steps — `src/sase/main/query_handler/_standalone_steps.py:182`

The finalizer fires after *every* provider turn in a SASE agent session, gated only on `SASE_AGENT_TIMESTAMP`. A
multi-step plan-chain agent runs it more than once. "Finalizer" is currently a *turn* hook being used as if it were an
*agent* hook. A general system must name that distinction rather than inherit the ambiguity (§5.7).

Corollary worth stating as a rule rather than leaving as an accident: mentors, CRS, fix hooks, and workflow steps carry
no prompt directives, so they get config defaults only and `%final` never applies to them.

### 1.4 Provider failure never reaches the finalizer

`run_commit_finalizer` sits inside the `try:` that `provider.invoke()` raises from; the `except` branches at
`_invoke.py:348/375/396` all re-raise without finalization. So `events: [success]` is the only honest lifecycle event at
this seam in v1. A `failure`/`always` event would need a different call site, not a config flag.

### 1.5 `sase-be` is already building the general contract

`sase-be` — "Vars-driven commit finalization with exclusion-based staging"
(plan `plans:202607/commit_vars_finalizer.md`) — is **IN_PROGRESS**: phase 1 CLOSED, phases 2–5 in flight.

- The agent no longer commits. It **records intent as sase variables** via `sase commit --vars` — reserved keys
  `commit_message` (multiline), `commit_exclude_files` (list), `commit_repo_root`, plus passthroughs `commit_name`,
  `commit_parent`, `commit_bug_id`, `commit_status`, `commit_method` (plan §`commit-vars-option`).
- The finalizer **executes** that intent deterministically as a `sase commit` subprocess, then clears the consumed
  variables (plan §`finalizer-vars-commit`).
- Phase 1 landed list-valued variables in the Rust scan wire: `OutputVariableValue::{Text,List}` at
  `sase-core/crates/sase_core/src/agent_scan/wire.rs:179`.
- `clear_agent_output_variables(artifacts_dir, keys)` does **not exist yet** — it is added by phase `list-vars-python`
  step 2 (plan line 195). Today `agent_output_variables.py` exposes only `read_`/`set_`/`parse_`.

This is the single most important input: **the "prompt asks the agent to record vars; a script then performs the effect"
contract is already being built.** Generalizing finalizers is largely naming that contract and letting other things plug
into it — and it means this work must land *after* `finalizer-vars-commit`, not beside it (§7).

### 1.6 The migration surface is wider than "one function"

`commit_finalizer` names leak into 12 modules and the docs tree:

- 7 `commit_finalizer*` modules under `llm_provider/` plus `core/commit_finalizer_prompt_artifacts.py`
- artifact selection: `core/artifact_file_defaults.py:525`, `agent/artifact_files_cache.py:137`,
  `main/feedback_prompt.py:93` — all call `is_commit_finalizer_followup_prompt` to *exclude* finalizer follow-up
  prompts from prompt pickers
- reporting: `axe/runner_reporting.py:10-11,61` reads `commit_finalizer_result.json` by literal filename
- tests patch `sase.llm_provider._invoke.run_commit_finalizer` in at least 5 files
- docs: `commit_workflows.md`, `configuration.md`, `llms.md`, `workspace.md`, plus a published blog post and infographic

Generalization needs a compatibility plan, not just a loop around the current function.

---

## 2. Prior art inside SASE — reuse, don't invent

The strongest single recommendation in both reports, and it holds: **don't build a fifth mechanism.**

### 2.1 Axe chops — the closest analogue by a wide margin

`ChopConfig` (`src/sase/axe/_config_types.py:52-83`) is very nearly the `FinalizerSpec` we want: `name`, `description`,
`script`, `enabled`, `run_every`, `timeout`, `env`, `inhibit_if` guards, `trigger` providers, `once_per`. Everything the
requirements ask for except `prompt` and `depends_on` already exists, with JSON Schema coverage
(`sase.schema.json` `definitions.axeChop`) for guard providers (`changespec`, `agent_hood`, `agent_clan`) and trigger
providers (`always`, `git.commits_since`).

Execution is equally reusable, all verified:

- **Script discovery** — `discover_chop_script` (`axe/chop_script_runner.py:32`) resolves an exact executable name
  across search dirs → the running interpreter's `bin/` → `PATH`. This is how a plugin console script gets found with
  zero new machinery, even when `PATH` symlinks are stale mid-reinstall.
- **Invocation** — `run_chop_script` (`:68`) passes `--context <json-file>` with agent identity scrubbed via
  `scrub_agent_identity_env`.
- **Result contract** — `sase/chops/sdk.py` gives scripts `load_chop_invocation()`, `ChopResultBuilder` (`:259`,
  statuses `ok|no_op|check_error`), counters, evidence, `resolve_chop_result_file` (`:395`), and an atomic validated
  write.
- **Rust decision engine** — `sase-core/crates/sase_core/src/axe_chop/` has `decision.rs:8 evaluate_chop_decision`,
  `validation.rs:26 parse_chop_result` / `:82 validate_chop_result`, plus `wire.rs`, `config.rs`, `targets.rs`,
  `bookkeeping.rs`. This is a complete, working template for a finalizer trigger evaluator and result validator.

### 2.2 `%clan(..., summary_script=...)` — a directive that already names an executable

`src/sase/axe/clan_summary_script.py` is the template for "a directive supplies an executable the host runs": argv
resolution reusing `discover_chop_script`, `start_new_session`, hard timeout, 32 KiB output cap, process-group kill,
per-attempt artifact log — and **every failure downgraded to a warning**.

This matters for the security argument in §4.3: the line is not "a prompt may never name an executable" (SASE already
allows exactly that), it is that a *decorative* script may fail soft while an *enforcing, credentialed, completion-
blocking* one may not accept its executable from untrusted prompt text.

### 2.3 File hooks — fail-soft producer boundary

`src/sase/config/file_hooks.py` shows the config→dataclass→matcher pattern where a bad entry is *skipped with a warning*
rather than failing the load (`_load_file_hooks:202-229`), memoized on `current_config_token()`.
`src/sase/file_hooks/engine.py` states the posture directly: a hook engine, filesystem, or spawn failure must never
alter the result of a commit or artifact creation.

### 2.4 Notification gates — user-defined entries denied privileged actions

`src/sase/notification_gates/adapters.py:213-311` registers kinds as frozen `GateAdapter` records with per-kind
policies, including a deliberate `custom` kind marked `neutral_only`. That is the in-repo precedent for "user-defined
entries exist but are denied privileged actions", and it applies directly here.

### 2.5 `%repeat`'s `STOP` — the reserved-variable pattern

`src/sase/axe/run_agent_repeat_stop.py:24` reserves one case-sensitive output variable with a conservative falsy set;
`sase var set` stays generic and only the consumer interprets the name. `_completion_output_variables`
(`run_agent_runner_finalize.py:191-205`) filters exactly one key today. `sase-be` is about to add a second special case
(`commit_*`). A general system should turn that into a *rule* (§5.4) rather than a growing list.

### 2.6 Config layering — the reason a `finalizers:` **list** would be a bug

`src/sase/config/layers.py` builds layers `default` → `plugin:<module>` (one per `sase_config` entry point, `:155-183`,
`list_strategy="concatenate"`) → `user` (`~/.config/sase/sase.yml`, **`list_strategy="replace"` at `:195`**) →
`overlay:*` → `local`.

Consequence: if `finalizers` is a YAML *list*, a user adding one custom finalizer to `~/.config/sase/sase.yml` silently
deletes the builtin commit finalizer *and every plugin-contributed finalizer*. Maps deep-merge
(`sase-core/crates/sase_core/src/config/merge.rs:16 deep_merge_objects`); lists do not. `axe.lumberjacks.*.chops`
already accepts both forms for exactly this reason — the schema types it `["array", "object"]` and describes the array
form as *"Legacy list or composable map of chop scripts to run on each tick."*

**This single fact should decide the config shape**, and a keyed map delivers requirement 2 for free:
`finalizers: {commit: {enabled: false}}`. Both reports reached this conclusion; only B produced the decisive evidence.

### 2.7 Directive parsing already supports the syntax

`src/sase/xprompt/_directive_types.py`:

- `_KNOWN_DIRECTIVES` = `{auto, clan, effort, hide, model, id, repeat, wait}` — **`final` is free.**
- `_DIRECTIVE_ALIASES` = `a,c,e,h,i,m,n,r,t,w` — **`f` is free.**
- `_MULTI_VALUE_DIRECTIVES` = `{wait}` — the repeated-value model already exists.
- `_DIRECTIVE_PATTERN` colon-arg body char class is `[!a-zA-Z0-9_#/.,()@=-]`, with the constraint that an arg must not
  *end* in `.` or `!`. So `!`, `-`, `/`, and `,` all parse: `%final:!commit`, `%final:-commit`, `%final:plugin/audit`,
  and `%final:a,b` are all lexically valid today.
- Bounded paren kwargs have direct precedent: `_directive_collect.py:105` uses
  `supported_keys = {"bead","priority","runners","time"}` for `%wait`, and `:188` uses
  `{"summary","summary_script","tribe"}` for `%clan`, rejecting unknown keys.

### 2.8 Per-launch state already has a home

`build_agent_meta` (`axe/run_agent_directive_metadata.py:147`) persists `%auto`, `%hide`, `%wait`, `%id`, and clan
membership into `agent_meta.json`, with re-exec durability through `preserved_agent_metadata` (`:56`). That is also the
file whose `output_variables` field the finalizer must read anyway. Environment variables (the `%clan` `SASE_CLAN_*`
approach) leak into nested launches, need `scrub_agent_identity_env` additions, and do not survive a runner re-exec.

### 2.9 Adjacent concept to keep distinct

`docs/workflow_spec.md:790-819` — xprompt workflow steps marked `finally: true` run even after failure. That is
*intra-workflow cleanup*, not *post-completion enforcement*. Naming risk addressed in §5.2.

---

## 3. What the requirements imply

| Requirement                   | Implication                                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Generalize the current one    | The commit finalizer must become an ordinary registry entry with **zero special cases**, or the abstraction rots. |
| Disable defaults              | Config must deep-merge **by key**, not replace by list (§2.6), and needs a future-proof "all defaults off" switch. |
| Support multiple              | Deterministic ordering, a shared result document, and an explicit policy for what one failure does to the others.  |
| Prompt + script + retries + … | A spec dataclass, a script contract (argv, context, result document), and host-evaluated trigger providers.        |
| Plugin support                | Ride existing plugin seams — **and make plugin entries opt-in** (§4.2).                                            |
| Agents set sase variables     | The wire is `agent_meta.json.output_variables`; the driver owns a reserved-namespace and clearing policy.          |

---

## 4. Where the two source reports disagreed, and how it resolves

### 4.1 Definition site: config map vs. a new `sase_finalizers` resource tier

**A** proposed first-wins discovery across `<project>/sase/finalizers/`, `~/sase/finalizers/`, a new `sase_finalizers`
entry-point resource group, and bundled core definitions. **B** proposed config-only (`finalizers:` map) with plugins
declaring through the existing `sase_config` entry point.

Two corrections first. B rejected A's option as "runs plugin code in-process"; that is a mischaracterization —
`RESOURCE_ENTRY_POINT_GROUPS` (`plugins/inventory.py:25`) is `{sase_config, sase_plugin_manifest, sase_xprompts}`, and a
`sase_finalizers` group would load a package *module* for resource resolution exactly like `sase_xprompts`, not
callbacks. Conversely, A's asset-provenance objection to config-only is real: plugin layers are built from
`resource_files(module).joinpath("default_config.yml")` (`layers.py:157`) and stored with `path=None`, so a relative
`prompt: prompt.md` inside a plugin's config block has no anchor after the merge.

**Resolution: config map wins, and A's provenance objection is solved without a new tier.**

The decisive argument is surface area. A's design still needs a config-side selection and override surface — A itself
proposes `finalizers.{enabled,enable_defaults,select,overrides}` — so it requires **both** a discovery tier and a config
tier, with its own precedence rules, shadowing semantics, disable switches, and doctor checks. B's design needs one
surface that already exists, already deep-merges, already reports provenance through `ConfigLayer` names, already
validates against the schema, and already has deprecation machinery (`_collect_deprecated_keys`).

The asset problem has two cheap fixes, either sufficient:

1. `prompt_xprompt: <name>` indirection — the prompt body lives in the existing xprompt system, which is reviewable,
   testable, Jinja-capable, and already layered. Keeps prose out of YAML entirely. **Preferred.**
2. Anchor relative asset paths **at layer-load time**, in `layers.py` where `resource_files(module)` is still in hand,
   before the merge erases the anchor.

Keep A's `sase_finalizers` resource group documented as a **v2 escape hatch** if plugin authors ever need to ship
definition *bundles*. The config `finalizers:` map remains the selection and override surface either way, so adding the
tier later is additive, not a redesign.

### 4.2 Plugin defaults — a real safety hole in B's model that A caught

Under B's design, a plugin's `default_config.yml` shipping `finalizers: {my_thing: {enabled: true, script: …}}` becomes
a config layer at install time and **activates automatically on `pip install`** — arbitrary post-completion code with
the agent's credentials, with no user action beyond installing a plugin.

A's rule fixes it: *only bundled core definitions may be defaults; plugin, project, and user definitions require
explicit selection.* This is also exactly the `notification_gates` `neutral_only` precedent (§2.4).

**Resolution — adopt A's rule inside B's mechanism:** the registry loader forces `enabled: false` for any finalizer
whose *originating layer* is `plugin:*`, regardless of what the plugin's YAML says, unless the `user`, `overlay:*`, or
`local` layer re-enables it by key or `%final:<name>` selects it for the launch. `ConfigLayer.name` already carries the
originating layer, so this is enforceable at load time. Pair it with `finalizers.enable_defaults: false` as the
future-proof master switch A asked for, and `sase final list` showing each entry's source layer and effective state.

This is the highest-value merge of the two reports: neither is safe alone.

### 4.3 What `%final` may override

**A**: selection only, no kwargs — all tuning stays in config. **B**: selection plus a *closed* kwarg allowlist
(`enabled`, `max_passes`, `on_failure`, `timeout`), never `script`/`command`/`env`/`prompt`.

**Resolution: B, with a sharper framing.** Bounded kwargs are the house style (`%wait(priority=…)`,
`%clan(…, tribe=…)`), the allowlist mechanism already exists (`_directive_collect.py:105,188`), and "this one run may
commit twice" is a real per-launch need that A's model cannot express without editing config.

The security framing both reports reached for should be stated precisely, because B's absolutism is contradicted by the
tree: `%clan(…, summary_script=…)` *already* accepts an executable name from prompt text. The actual boundary is:

> A prompt may name an executable for a **decorative, fail-soft** phase. A prompt may **not** name an executable for an
> **enforcing, credentialed, completion-blocking** phase.

That justifies the closed allowlist without pretending to a rule SASE does not follow, and it must be defended by a test
that fails if anyone adds `script`, `command`, `env`, or `prompt` to the allowlist.

Note the residual exposure both reports flagged: in-repo `local` config (`sase/sase.yml`) is checked in, so a malicious
PR can define a finalizer. That is the same exposure `file_hooks` and `chops` already carry — worth documenting rather
than discovering.

### 4.4 Negation syntax: `!name` vs `-name`

Both parse (§2.7). **Resolution: `!`.** Finalizer names will contain hyphens (`license-audit`, `bead-close`), which
makes `%final:-license-audit` visually ambiguous and worse inside a comma list (`%final:a,-license-audit`). `!` cannot
begin a name, reads as negation, and matches A's proposal. Keep `%final:none` for "clear everything".

### 4.5 When the Rust boundary gets crossed

**A**: put schema, selector application, dependency closure, ordering, and result validation in `sase-core` as step 2 of
the migration. **B**: land the Rust decision engine with the *trigger* phase (phase 3), not the initial refactor.

**Resolution: B's sequencing.** The `rust_core_backend_boundary` rule says trigger evaluation and the decision record
belong in core — a `sase final list` CLI, ACE, and any future web view must agree on "would this fire right now?" — and
A is right about *where* it ends up. But a registry with one entry and one implicit trigger crosses no frontend
boundary, and defining a Rust wire before the Python shape has stabilized churns it. This is also how `axe_chop`
actually evolved. Land Rust with the trigger phase; carry A's list of what belongs there
(trigger predicates, dependency closure and cycle detection, stable topological order, script-result validation,
aggregate status reduction) as the scope of that phase.

### 4.6 Launch-time plan snapshot

A proposed a `finalizer_plan.json` snapshot written before the first provider call, capturing selection, provenance,
resolved prompt *content*, argv, normalized policy, and a plan digest — so a config or plugin upgrade during a long
`%wait` cannot change what eventually runs. B did not address this.

**Resolution: adopt a reduced form.** The exposure is narrower than A implies — the finalizer runs inside the runner
process, so the only true divergence window is between directive parse time (launch, pre-wait) and finalizer run time
(post-wait), and B's `agent_meta.json` persistence already pins the *selection* across that window. What can still drift
is the *definition body*. Rather than snapshotting prompt content (which is heavy, and unfixable for plugin console
scripts anyway — A concedes those can only be recorded by distribution + version), record a **spec digest plus
originating layer** in `finalizer_result.json` at execution time. Drift then becomes observable and debuggable rather
than silent. Full content snapshotting is a later phase if the observability turns out to be insufficient.

### 4.7 Script result vocabulary

A proposed `succeeded | skipped | retry | failed`; B proposed `satisfied | unsatisfied | error`; chops use
`ok | no_op | check_error`.

**Resolution:** `satisfied | unsatisfied | error` for the *script*, because the driver's loop is "re-evaluate the
trigger" and those words describe the trigger's state. `unsatisfied` consumes a pass and its `reason` is fed into the
next prompt (which is A's `retry` under a better name). `error` respects `on_failure`. `skipped` and `blocked` are
**driver-owned** statuses recorded in the aggregate document — a script should not be able to declare itself skipped.

---

## 5. Recommended design

### 5.1 The finalizer contract

```
  ┌── trigger ──────────┐   ┌── prompt pass (×N) ────────┐   ┌── script ──────────────┐
  │ host-evaluated;     │   │ provider turn; the agent   │   │ subprocess; performs   │
  │ cheap; no LLM.      │─▶ │ records intent as          │─▶ │ the deterministic      │
  │ "is there work?"    │   │ sase variables.            │   │ effect. Returns a      │
  └─────────────────────┘   └────────────────────────────┘   │ structured result.     │
             ▲                                                └───────────┬────────────┘
             └──────────────── re-evaluate ───────────────────────────────┘
```

Evaluate the trigger; if unsatisfied, run one prompt pass, then the script, then re-evaluate. Repeat up to `max_passes`,
then apply `on_failure`. Either half may be omitted: no `prompt` is a pure post-run script; no `script` is today's "nag
the model until the trigger clears". Today's commit finalizer *is* this with the parts unnamed, and `sase-be` is adding
its missing script stage.

### 5.2 Configuration shape

Keyed map in `src/sase/default_config.yml`, one builtin:

```yaml
finalizers:
  enable_defaults: true          # future-proof master switch for every core default
  commit:
    description: |-
      Require every agent change to be committed before completion

      Detects uncommitted work in the primary workspace and every opened linked,
      external, and SDD sidecar repository, asks the agent to record commit intent
      as sase variables, then executes that intent deterministically.
    enabled: true
    default: true                # only settable by the bundled core layer (§4.2)
    scope: turn                  # turn | agent                      (§5.7)
    trigger: {provider: repo_dirty}
    inhibit_if: []               # chop guard providers, verbatim
    prompt_xprompt: _finalizer_commit
    script: sase_final_commit    # console-script name, resolved like a chop
    max_passes: 2
    timeout: 5m
    on_failure: fail             # fail | warn | skip                 (§5.5)
    depends_on: []
    vars_prefix: commit          # reserved variable namespace        (§5.4)
    env: {}
```

- `description` follows the chop convention (≤100-char summary, blank line, body) so `sase final list` renders like
  `sase chop`.
- `prompt` / `prompt_xprompt` are mutually exclusive; `prompt_xprompt` is strongly preferred (§4.1).
- Every field optional except `description` and at least one of `prompt*`/`script`.
- Retire `commit.finalizer.{enabled,max_passes}` by mapping onto `finalizers.commit.{enabled,max_passes}` with a
  deprecation diagnostic via the existing `_collect_deprecated_keys`.
- Keep `SASE_DISABLE_COMMIT_STOP_HOOK` disabling only `commit`; add `SASE_DISABLE_FINALIZERS` as the master kill.

### 5.3 The `%final` directive

| Form                            | Meaning                                                                          |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `%final:<name>`                 | Add a registered finalizer to this launch's selection (repeatable, accumulates)  |
| `%final:<a>,<b>`                | Comma list, like `%wait`                                                         |
| `%final:!<name>`                | Remove it for this launch, and remember it was *explicitly* removed              |
| `%final(<name>, max_passes=3)`  | Add with bounded per-launch overrides                                            |
| `%final:none`                   | Clear the selection and suppress current *and future* defaults for this launch   |
| `%f`                            | Alias                                                                            |

Selectors are **ordered operations over the config-derived selection**, applied left to right — so `%final:lint` adds
lint without accidentally disabling commit enforcement, and `%final:none %final:lint` gives exact selection when that is
what you want. Bare `%final` is a parse error, not a silent no-op.

Allowed kwargs: **`enabled`, `max_passes`, `on_failure`, `timeout`** — closed set, test-enforced (§4.3).

Fails at launch, before any provider call: unknown names, unknown removals, cycles, self-dependencies, unresolvable
scripts, missing prompt assets, and a `depends_on` prerequisite that was explicitly removed with `%final:!<name>`
(silently overriding the user's removal would be worse than failing).

Mechanical touch points: `"final"` into `_KNOWN_DIRECTIVES` and `_MULTI_VALUE_DIRECTIVES`, `"f": "final"` into
`_DIRECTIVE_ALIASES`, a `supported_keys` branch in `_directive_collect.py` mirroring `%wait`, resolution in
`_directive_values.py`, `PromptDirectives.finalizers`, persistence through `build_agent_meta` +
`preserved_agent_metadata`, rows in `_DIRECTIVE_ARGUMENT_HINTS`/`_DIRECTIVE_DESCRIPTIONS`, and a `final_keyword` branch
in `ace/tui/widgets/directive_completion.py` sourcing real names from the registry.

Selections travel in `agent_meta.json`, never the environment (§2.8).

**Naming.** `%final` collides conceptually with workflow `finally: true` steps (§2.9). Keep `%final` and disambiguate in
docs by consistently calling the workflow feature "`finally` steps" and this one "finalizers" — but decide before the
directive ships, since renaming afterward requires a `_DEPRECATED_DIRECTIVE_MESSAGES` entry as `%name`/`%tribe` did.

### 5.4 Trigger providers and the sase-variable contract

Start with a deliberately small closed set, extended the way chop trigger providers are:

| Provider       | Fires when                                                                    |
| -------------- | ------------------------------------------------------------------------------ |
| `always`       | Every eligible turn/run (default)                                              |
| `repo_dirty`   | Any enforced repo has uncommitted changes — today's trigger; reuses `collect_dirty_state` |
| `vars_present` | The agent set variables matching `keys:` / the finalizer's `vars_prefix`       |
| `vars_absent`  | Required variables are *missing* — the agent failed to report something        |
| `script`       | Delegate to the finalizer's own script in a cheap `--probe` mode (escape hatch) |

Plus `inhibit_if` guards reusing the chop guard providers (`changespec`, `agent_hood`, `agent_clan`) verbatim — same
YAML, same Rust evaluator, same docs.

`vars_absent` is what makes requirement 5 *enforceable* rather than aspirational, and it is the best idea in either
report. A `report` finalizer with `trigger: {provider: vars_absent, keys: [summary]}` and a prompt of "you did not set a
`summary` variable; set one now" turns a convention into a contract, at zero cost when the agent complied.

Generalize the `STOP` / `commit_*` special cases into one rule:

- A finalizer named `<n>` owns the `<n>_*` variable prefix by default (`vars_prefix` overrides). Overlapping prefixes
  are a config diagnostic.
- The script receives those variables in its JSON context; it does not re-read `agent_meta.json`.
- The context is **reloaded immediately before every prompt pass and before every script invocation** — a launch-time
  snapshot would miss exactly the values the finalizer prompt just asked the agent to write.
- On a satisfied result, the driver calls `clear_agent_output_variables` (arriving in `sase-be` phase
  `list-vars-python`) for the consumed keys.
- `_completion_output_variables` (`run_agent_runner_finalize.py:191-205`) filters any variable whose prefix belongs to a
  registered finalizer — one rule replacing today's `STOP` filter and `sase-be`'s planned `commit_*` filter.

### 5.5 Failure semantics and ordering

`on_failure` is per finalizer: `fail` (raise → run recorded failed, no completion notification — today's commit
behavior), `warn` (recorded in the result document and appended to the completion notification; run completes), `skip`
(recorded only).

Independently, following the file-hooks precedent (§2.3): **a finalizer that cannot be loaded, resolved, or spawned is
always a warning, never a failure.** A typo in a plugin's `finalizers:` block must not brick every agent run. Only a
*triggered, executed, unsatisfied* finalizer with `on_failure: fail` fails the run.

Ordering is `depends_on` → topological sort, ties broken by config key order (deterministic, no priority integers to
fight over as plugins arrive). A dependency that ended unsatisfied under `on_failure: fail` marks dependents `blocked`
with reason `dependency_failed` — recorded, not silent. A trigger-skipped dependency counts as *satisfied* (it was not
applicable); a warned dependency counts as satisfied but propagates its warning.

### 5.6 Script contract

Mirror `sase.chops.sdk` rather than inventing a second SDK — ideally by extracting shared primitives into a
`sase.finalizers.sdk` that re-exports them:

```
argv:  <script> --context <path-to-context.json>
env:   SASE_FINAL_RESULT_FILE, SASE_ARTIFACTS_DIR, SASE_PROJECT_DIR, SASE_AGENT_TIMESTAMP,
       SASE_FINALIZER_NAME, SASE_FINALIZER_PASS, plus the spec's `env:` merged over
context: { schema_version, finalizer, pass, max_passes, project_dir, artifacts_dir,
           agent: {name, bead_id, workspace_num, …}, variables: {…}, trigger: {…},
           dependencies: {…}, previous_result: … }
result:  { schema_version, status: "satisfied"|"unsatisfied"|"error",
           reason, counters, evidence, warnings, consumed_variables }
```

`command` is argv, never `shell=True`. Execution hygiene copied from `clan_summary_script.py`: `start_new_session`, hard
timeout, process-group kill, bounded stdout capture, stderr to both the agent log and a per-finalizer artifact log.
Scripts run in the primary project workspace by default; arbitrary unresolved working directories are rejected.

Artifacts: one `finalizer_result.json` with per-finalizer entries (`{name, status, reason, passes, triggered,
duration_ms, spec_digest, source_layer, consumed_variables, warnings, error}`); per-pass
`finalizer_<name>_pass_<N>_{prompt,response}.md` generalizing `commit_finalizer_prompt_artifacts.py`; per-finalizer
`finalizer_<name>_stderr.log` in the `clan_summary_stderr.log` format. Keep writing `commit_finalizer_result.json` as a
compatibility alias for one release — `runner_reporting.py:11` and `sase-be` phase `finalizer-vars-commit` step 4 read
it by literal name. Record variable *names*, never values, in anything user-visible.

### 5.7 Scope: `turn` vs `agent`

Because today's finalizer is a per-turn hook (§1.3), make the ambiguity explicit:

- `scope: turn` — runs after each successful `invoke_agent` turn. Today's behavior; the v1 default; what `commit` keeps.
- `scope: agent` — runs once in `finalize_loop` (`run_agent_exec_finalize.py:524`), before the done marker. Reserved for
  a later phase; it is the right home for "summarize the run", "publish artifacts", "notify".

### 5.8 Plugin support and CLI

Declaration: a plugin ships `default_config.yml` with a `finalizers:` block, picked up as its own config layer via the
existing `sase_config` entry point (`layers.py:155-183`). Implementation: a console script in `[project.scripts]`, found
by `discover_chop_script`. Both seams are load-bearing today for `sase-github`, `sase-telegram`, and `sase-nvim` —
nothing new is required, which is the strongest argument for this shape. Plugin entries are **opt-in** (§4.2).

CLI, following `cli_rules` (alphabetized, short alias on every public long option, bare group delegates to `list`):

```
sase final list                 # registry: name, source layer, enabled, default, trigger
sase final show <name>          # full resolved spec + provenance + spec digest
sase final run <name> [-a DIR]  # execute against an artifacts dir, for authoring/testing
sase final doctor               # unresolvable scripts, dependency cycles, prefix collisions,
                                # plugin entries enabled without user opt-in
```

Wire `sase final doctor` into `sase doctor` alongside `checks_plugins.py` and `chop_doctor.py`. `final` does not collide
with any existing top-level subcommand.

---

## 6. Phasing

| Phase | Title                                     | Content                                                                                                                                                                       | Depends on         |
| ----- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| 1     | Finalizer registry and driver             | `finalizers:` keyed config + schema + `FinalizerSpec` + driver running an ordered list. Ship exactly one entry (`commit`) reproducing today's behavior. Deprecate `commit.finalizer.*`. **No user-visible feature change.** | `sase-be` phase 5  |
| 2     | Script stage and SDK                      | Script discovery/execution/result contract; `sase_final_commit` becomes the commit finalizer's script; artifacts generalized with the compat alias.                             | 1                  |
| 3     | Triggers, guards, and the Rust engine     | Trigger providers + `inhibit_if`; **`sase_core` decision engine** mirroring `axe_chop::decision`; result validation in Rust; `sase final list/show/doctor`.                    | 2                  |
| 4     | `%final` directive                        | Parsing, `PromptDirectives.finalizers`, `agent_meta.json` persistence, TUI completion, docs, the allowlist-closure test.                                                        | 3                  |
| 5     | Dependencies, `on_failure`, `scope: agent` | Topological ordering, failure policies, plugin opt-in enforcement, the once-per-agent hook in `finalize_loop`.                                                                 | 4                  |
| 6     | Plugin docs and a reference finalizer     | Document both seams; ship one non-commit builtin (a `vars_absent`-triggered `report` finalizer) to prove the abstraction.                                                       | 5                  |

**Phase 1 is the whole bet**: if the commit finalizer cannot be expressed as an ordinary registry entry with zero special
cases, the model is wrong and should be revised before anything is built on it.

Tests worth pinning beyond the happy path: no directive uses defaults; `enable_defaults: false` survives a
*newly added* default fixture; `%final:none` suppresses all defaults; additive and negative selectors preserve order; a
removed required dependency fails at launch; cycles and unknown IDs fail before any provider call; a plugin layer
setting `enabled: true` stays off until user opt-in; the kwarg allowlist rejects `script`/`env`/`prompt`; prompt-written
scalar *and list* variables reach the script; consumed variables clear only after success; retry diagnostics enter the
next prompt; warn vs. fail behavior; loading/spawn failures degrade to warnings; runner refresh, deferred launch,
spawn-on-retry, `%repeat`, families, clans, and `%{a|b}` fan-out each preserve the resolved selection; finalizers finish
before `done.json` and the notification; and the migrated commit finalizer retains every `sase-be` ordering and
exclusion guarantee.

---

## 7. Risks and open questions

- **Collision with `sase-be`.** Phases 2–5 of `sase-be` are in progress and rewrite the same files
  (`commit_finalizer.py`, `commit_instructions.py`, `commit_finalizer_prompting.py`). Phase 1 here **must** land after
  `finalizer-vars-commit` or the two efforts conflict continuously. The upside is large: `sase-be` delivers the commit
  finalizer's script stage, so phase 2 becomes extraction rather than invention.
- **Latency and cost multiplication.** Each triggered finalizer adds a trigger evaluation and up to `max_passes`
  provider turns to *every* turn (§1.3). With N finalizers this multiplies. Mitigations: triggers must be cheap and
  host-evaluated, never an LLM call; `repo_dirty` computed once per turn and shared; consider a global cap on total
  finalizer passes per turn in phase 5.
- **Non-agent callers.** Mentors, CRS, fix hooks, and workflow steps route through `invoke_agent` and would inherit
  config-default finalizers. That is probably right, but verify against real mentor runs before phase 1 lands — an
  `on_failure: fail` finalizer there converts mentor turns into failures.
- **Trust boundary drift.** The value of the config-only definition rule and the plugin opt-in rule is entirely in their
  enforcement; both need tests that fail when someone loosens them. In-repo `local` config remains checked in, so a
  malicious PR can define a finalizer — the same exposure `file_hooks` and `chops` already carry.
- **Definition drift across long `%wait`s** — mitigated to observable (spec digest + source layer in the result), not
  prevented (§4.6). Revisit if it bites.
- **Naming** — `%final` vs. workflow `finally:` steps. Decide before phase 4.
- **Where the registry lives long-term.** Phase 3 puts trigger evaluation in `sase_core`. Whether *registry loading*
  should also move is deferred — follow the same trigger axe did, namely a second frontend needing it.

---

## 8. Recommended solution

**Build a keyed `finalizers:` config registry whose entries are three-part contracts — a host-evaluated trigger, bounded
prompt passes that ask the agent to record sase variables, and a script that performs the deterministic effect — and
make `%final` a selection-and-bounded-override directive over that registry, never a definition site.**

1. **Config, not prompt, is the definition site.** `finalizers:` is a **map** keyed by name, never a list — the `user`
   config layer replaces lists (`layers.py:195`), so a list would let one user entry silently delete the builtin and
   every plugin contribution. Ship one builtin `commit` entry. `finalizers: {commit: {enabled: false}}` disables it;
   `finalizers: {enable_defaults: false}` disables every current and future core default.
2. **Plugin-contributed finalizers are opt-in.** The loader forces `enabled: false` for entries originating in a
   `plugin:*` layer until the user re-enables by key or selects with `%final`. Installing a plugin must never activate
   credentialed post-completion code.
3. **`%final:<name>` adds, `%final:!<name>` removes, `%final:none` clears, `%final(<name>, max_passes=3)` tunes.**
   Selectors are ordered operations over the config-derived selection, so `%final:lint` cannot accidentally disable
   commit enforcement. The kwarg allowlist is closed (`enabled`, `max_passes`, `on_failure`, `timeout`) and
   test-enforced: a prompt may name an executable for a decorative fail-soft phase, never for an enforcing,
   credentialed, completion-blocking one. Alias `%f`; multi-value like `%wait`.
4. **Selections travel in `agent_meta.json`**, not the environment — durable across re-exec, already read by every
   consumer, no nested-launch leakage.
5. **The execution model is trigger → prompt passes → script → re-evaluate**, bounded by `max_passes`, with variables
   reloaded immediately before every pass and every script call. This is exactly what `sase-be` is building for commits;
   generalizing is naming, not inventing.
6. **Reuse axe-chop machinery end to end**: `ChopConfig`'s field vocabulary, `discover_chop_script`, the
   `--context`/result-file protocol, the `sase.chops.sdk` result builder, `inhibit_if` guard providers, and
   `axe_chop::{decision,validation}` as the model for the Rust trigger evaluator and result validator — landed with the
   trigger phase, not before the Python shape stabilizes.
7. **Plugins need no new entry-point group**: declare via a `sase_config` `default_config.yml` layer, implement via a
   console script. Keep a `sase_finalizers` resource group as a documented v2 escape hatch for definition bundles; the
   config map stays the selection surface either way.
8. **One reserved-namespace rule** (`<name>_*`, cleared on success, filtered from completion notifications) replaces the
   growing set of `STOP` / `commit_*` special cases. A `vars_absent` trigger is what makes "expect all agents to set
   sase variables" enforceable rather than aspirational.
9. **Failure policy is explicit per finalizer** (`fail`/`warn`/`skip`) while *loading and spawning* failures are always
   soft — a broken plugin entry must never brick an agent run. Dependency failures mark dependents `blocked`, recorded.
10. **Name `scope: turn | agent` explicitly.** Today's finalizer runs after every `invoke_agent` turn, not once per
    agent; inheriting that ambiguity silently would be a bug factory.
11. **Sequence after `sase-be`**, and prove the abstraction in phase 1 by expressing today's commit finalizer as an
    ordinary registry entry with zero special cases.

The distinguishing property of this design is that almost none of it is new code: it is the axe-chop config and
execution model, the file-hooks fail-soft posture, the notification-gate registry discipline, and the `sase-be` variable
contract, assembled at a new call site — with one genuinely new rule (plugin entries are opt-in) that neither the config
model nor the discovery model was safe without.
