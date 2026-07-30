---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# Customizable Finalizers and the `%final` Directive

## Question

SASE has exactly one finalizer today — a hard-coded, provider-neutral commit finalizer that runs after a successful LLM
turn and refuses to let an agent finish with a dirty workspace. We want to generalize it so that:

1. Users can define their own finalizers.
2. Users can disable the default finalizer (and any default we add later).
3. Multiple finalizers can run in one agent run.
4. Each finalizer is configurable — a prompt, a script, retry attempts, trigger conditions, dependencies on other
   finalizers — and SASE plugins can ship their own.
5. Agents communicate with finalizers by setting sase variables (the model the in-flight `sase-be` epic establishes).

What is the right shape, and what should `%final` actually mean?

**Short answer: make `%final` a _selection and override_ directive over a keyed `finalizers:` config registry — never a
definition site. Model each finalizer as a three-part contract (host-evaluated trigger → bounded prompt passes → a
deterministic script), which is exactly the shape the current commit finalizer already has once you name its parts.
Reuse the axe-chop config/execution machinery wholesale rather than inventing a parallel one, and carry per-launch
selections in `agent_meta.json`, not in the environment.** Details, alternatives, and the reasons each rejected
alternative is rejected are below.

---

## 1. What "the finalizer" is today

Verified against the tree at commit `e3a898b6a` (2026-07-30). Line numbers are as of that commit.

### 1.1 It is one function, not a system

`run_commit_finalizer` (`src/sase/llm_provider/commit_finalizer.py:128-318`) is called from exactly one place:
`src/sase/llm_provider/_invoke.py:308-317`, immediately after a successful `provider.invoke(...)`. There is no
registry, no dispatch, no name — "the finalizer" is a single hard-coded code path with commit semantics baked in at
every level:

| Layer          | File                                              | What is hard-coded                                                   |
| -------------- | ------------------------------------------------- | -------------------------------------------------------------------- |
| Trigger        | `commit_finalizer_state.py:34-89`                 | "is any enforced repo dirty?" — main, linked, external, SDD sidecars |
| Prompt         | `commit_instructions.py:106-153`                  | Bead-close + commit-skill instruction text                            |
| Prompt (repos) | `commit_finalizer_prompting.py:15-122`            | Per-repo `cd` instructions, follow-up prompt framing                  |
| Effect         | the LLM itself, shelling out to `/sase_git_commit` | No script; the model performs the side effect mid-conversation       |
| Loop           | `commit_finalizer.py:230-318`                     | `for pass_number in range(1, config.max_passes + 1)`                  |
| Failure        | `commit_finalizer.py:306-318`                     | `raise CommitFinalizerError` → the whole run is recorded failed      |

### 1.2 Its configuration surface is two booleans-ish

```yaml
# src/sase/default_config.yml:791-794
commit:
  finalizer:
    enabled: true
    max_passes: 2
```

Schema at `src/sase/config/sase.schema.json:1685-1703`; loader at `commit_finalizer_config.py:41-59`. Plus one escape
hatch: `SASE_DISABLE_COMMIT_STOP_HOOK` (`commit_finalizer.py:148`), which is process-global, not per-launch.

### 1.3 It has real ordering guarantees worth preserving

Because it runs inline in `_invoke.py`, it completes **before** `done.json`
(`src/sase/axe/run_agent_exec_finalize.py:619`), before status/claim release
(`run_agent_runner_lifecycle.py:157-269`), and before the completion notification (`run_agent_runner_finalize.py`
`send_completion_notification`). Family members each run their own runner process and therefore their own finalizer, so
per-member ordering holds automatically. Any generalization must not lose this.

### 1.4 Non-obvious: it is per-*turn*, not per-*agent*

`invoke_agent` is the shared LLM entry point for far more than the agent runner — mentors
(`src/sase/workflows/mentor.py:332`), CRS (`src/sase/workflows/crs.py:221`), fix hooks
(`src/sase/axe/fix_hook_runner.py:198`), workflow prompt steps
(`src/sase/xprompt/workflow_executor_steps_prompt.py:340`), and standalone steps
(`src/sase/main/query_handler/_standalone_steps.py:182`) all route through it. The finalizer therefore fires after
*every* provider turn in a SASE agent session, gated only on `SASE_AGENT_TIMESTAMP`. A multi-step plan-chain agent runs
it more than once.

This matters for the design: "finalizer" is currently a *turn* hook that is being used as if it were an *agent* hook.
A general system must name that distinction rather than inherit the ambiguity (§5.8).

### 1.5 The `sase-be` epic already moves it halfway there

`sase-be` — "Vars-driven commit finalization with exclusion-based staging"
(plan: `sase/repos/plans/202607/commit_vars_finalizer.md`) — is in progress and reshapes the commit finalizer into
precisely the two-stage form a general system needs:

- The agent no longer commits. It **records intent as sase variables** via `sase commit --vars`
  (`commit_message`, `commit_exclude_files`, `commit_repo_root`, …).
- The finalizer **executes** that intent deterministically as a `sase commit` subprocess
  (phase `finalizer-vars-commit`, design decision 4).
- Variables gain list values, and `clear_agent_output_variables(artifacts_dir, keys)` is added so the driver can
  consume intent (phase `list-vars-python`, step 2).

This is the single most important input to this research: **the "prompt asks the agent to record vars; a script then
performs the effect" contract is already being built.** Generalizing finalizers is largely the work of naming that
contract and letting other things plug into it. It also means the generalization should land *after* or *alongside*
`sase-be`, not in conflict with it (§7).

---

## 2. What the six requirements actually imply

| Requirement                    | Implication                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Generalize the current one     | The commit finalizer must become an ordinary registry entry with no privileged code path, or the abstraction will rot instantly. |
| Disable defaults               | Config must **deep-merge by key**, not replace by list — see §3.6 for why a `finalizers:` *list* is a trap.                     |
| Support multiple               | Needs deterministic ordering, a shared artifact/result format, and a policy for what one failure does to the others.             |
| Prompt + script + retries + …  | Needs a spec dataclass, a script contract (argv, context, result document), and host-evaluated trigger providers.                |
| Plugin support                 | Should ride existing plugin seams (`sase_config` entry points + console scripts), not a new one.                                 |
| Agents set sase variables      | The agent→finalizer wire is `agent_meta.json.output_variables`; the driver must own a reserved-namespace and clearing policy.   |

---

## 3. Prior art inside SASE (reuse, don't invent)

SASE has already solved most of this four times. The strongest recommendation in this document is *don't build a fifth
mechanism*.

### 3.1 Axe chops — the closest analogue by a wide margin

`ChopConfig` (`src/sase/axe/_config_types.py:52-83`) is very nearly the `FinalizerSpec` we want:

```python
name: str; description: str; script: str | None = None
enabled: bool = True
run_every: int | None = None; timeout: int | None = None
env: dict[str, ChopEnvValue]
inhibit_if: list[dict[str, Any]]                     # guards
trigger: dict[str, Any] = {"provider": "always"}     # trigger providers
once_per: dict[str, Any] | None
```

Everything the requirements ask for except "prompt" and "depends_on" already exists here, with a JSON Schema
(`sase.schema.json` `definitions.axeChop`) covering `enabled`, `run_every`, `timeout`, `env`, `inhibit_if` (providers:
`changespec`, `agent_hood`, `agent_clan`) and `trigger` (providers: `always`, `git.commits_since`, with
`checkpoint_policy`).

Execution is equally reusable:

- **Script discovery**: `discover_chop_script` (`src/sase/axe/chop_script_runner.py:32-65`) resolves an exact executable
  name across search dirs → the running interpreter's `bin/` → `PATH`. This is how a plugin's console script gets found
  with zero new machinery.
- **Invocation**: `run_chop_script` (`:68-97`) passes `--context <json-file>`, with agent-identity env scrubbed
  (`scrub_agent_identity_env`).
- **Result contract**: `sase.chops.sdk` gives scripts `load_chop_invocation()`, a `ChopResultBuilder` with
  `status: ok|no_op|check_error`, counters, evidence, and an atomic validated write to `SASE_CHOP_RESULT_FILE`.
- **Decision engine in Rust**: `crates/sase_core/src/axe_chop/decision.rs::evaluate_chop_decision` evaluates guards then
  the trigger and returns a `ChopDecisionWire` — the exact shape a finalizer trigger evaluator needs.

### 3.2 `%clan(..., summary_script=...)` — a directive that already names an executable

`src/sase/axe/clan_summary_script.py:44-215` is the template for "a directive supplies a script that the host runs":
argv resolution reusing `discover_chop_script`, `start_new_session`, a hard timeout (20s), a 32 KiB output cap, process
-group kill on timeout, and — importantly — **every failure downgraded to a warning** plus an artifact log
(`clan_summary_stderr.log`) recording argv/outcome/env/stderr per attempt.

The lesson: a decorative script fails soft; an enforcing script must fail loud. A general finalizer needs both, which is
why `on_failure` must be an explicit per-finalizer field (§5.6).

### 3.3 File hooks — named, matched, fail-soft config entries

`src/sase/config/file_hooks.py` shows the config→dataclass→matcher pattern with per-entry validation that *skips the bad
entry and warns* rather than failing the load (`_load_file_hooks`, `:202-229`), memoized on `current_config_token()`.
`src/sase/file_hooks/engine.py` shows the fail-soft producer boundary: "a hook engine, filesystem, or spawn failure must
never alter the result of a commit or artifact creation."

### 3.4 Notification gates — a typed adapter registry

`src/sase/notification_gates/adapters.py:213-311` registers kinds (`plan`, `epic_plan`, `question`, `launch`, `hitl`,
`custom`) as frozen `GateAdapter` records with per-kind policies (`auto_policy`, `neutral_only`) and lookup helpers.
Notably it includes a deliberate `custom` kind marked `neutral_only` — the precedent for "user-defined entries exist but
are denied privileged actions". That precedent applies directly to user-defined finalizers.

### 3.5 `%repeat`'s `STOP` — the reserved-variable pattern

`src/sase/axe/run_agent_repeat_stop.py:24-33` reserves one case-sensitive output variable (`STOP`), with a conservative
falsy set, read by the runner from the predecessor's `agent_meta.json`. `sase var set` itself stays generic; only the
consumer interprets the name. `sase-be` extends the same idea with a reserved `commit_*` prefix. A general finalizer
system needs to turn that into a *rule* rather than a growing list of special cases (§5.5).

### 3.6 Config layering — the reason a `finalizers:` list would be a bug

`src/sase/config/layers.py:119-254` builds layers in order: `default` → `plugin:<module>` (one per `sase_config` entry
point, `:154-183`) → `user` (`~/.config/sase/sase.yml`) → `overlay:*` → `local`. **The `user` layer declares
`list_strategy="replace"` (`layers.py:195`).**

Consequence: if `finalizers` is a YAML *list*, a user adding one custom finalizer to `~/.config/sase/sase.yml` silently
deletes the builtin commit finalizer *and every plugin-contributed finalizer*. Maps deep-merge
(`crates/sase_core/src/config/merge.rs::deep_merge_objects`), lists do not. `axe.lumberjacks.*.chops` already supports
both forms for exactly this reason and the schema calls the list form "legacy".

**This single fact should decide the config shape.** A keyed map also gives requirement 2 for free:
`finalizers: {commit: {enabled: false}}`.

### 3.7 `finally: true` workflow steps — an adjacent concept to keep distinct

`docs/workflow_spec.md:790-819`: xprompt workflow steps marked `finally: true` run even after failure. That is
*intra-workflow cleanup*, not *post-completion enforcement*. Naming the new directive `%final` risks confusion; §5.3
addresses naming.

---

## 4. Design space

### 4.1 Where finalizers are *defined*

| Option                                      | Pros                                                                                  | Cons                                                                                                                                                                | Verdict         |
| ------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| **A. Config registry only** (`finalizers:`) | Reuses layering, schema, provenance, plugin layer; one trust boundary; disable-by-key | Not authorable inline                                                                                                                                                 | **Recommended** |
| B. Inline in the prompt (`%final(script=…)`) | Maximum flexibility                                                                    | **Security-fatal**: prompts are produced by other agents, xprompt bodies, and swarm segments. A directive that injects a shell command into a privileged post-completion phase is arbitrary code execution with the agent's credentials. | Reject          |
| C. xprompt-defined (`finalizer:` frontmatter, like `skill:`) | Familiar authoring; discovery already layered                          | xprompts are *prompt* artifacts; embedding an executable + trigger + retry policy overloads them, and xprompt discovery has 8 precedence tiers no one wants in an enforcement path | Reject for v1   |
| D. Python entry-point group (`sase_finalizers`) | Type-safe; rich                                                                    | Runs plugin code **in-process inside the agent's provider turn**; loses subprocess isolation and fail-soft; adds import cost to every `invoke_agent`                  | Reject          |

A and D are not exclusive in principle, but D's cost is real and its benefit is already covered: a plugin can ship both
a config layer (declaration) and a console script (implementation) today.

### 4.2 What `%final` *means*

| Option                                      | Assessment                                                                                                                                       |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Definition site                             | Rejected with B above.                                                                                                                             |
| **Selection + bounded override**            | `%final:<name>` opts a launch into a registered finalizer; `%final(<name>, max_passes=3)` tunes it; `%final:-<name>` / `%final:none` opts out. |
| Pure on/off switch                          | Too weak — "retry attempts, trigger conditions" are per-launch concerns in practice ("this one run may commit twice").                             |

Selection + bounded override is the right power level: the *set* of things a finalizer may do is fixed by config
(trusted), and the prompt only picks from that set and adjusts scalars (untrusted-safe).

### 4.3 How per-launch selections reach the finalizer

The finalizer runs inside the agent runner process, which has `SASE_ARTIFACTS_DIR`.

- **Environment variables** (as `%clan` does with `SASE_CLAN_*`): leaks into nested agent launches, requires additions to
  `scrub_agent_identity_env`, and does not survive a runner re-exec.
- **`agent_meta.json`** (as `%auto`, `%hide`, `%wait`, `%id`, clan membership all do, via
  `build_agent_meta` in `run_agent_directive_metadata.py:147-235`, with re-exec durability through
  `preserved_agent_metadata` `:56-104`): durable, already read by ACE/TUI/sidecar, and already the file whose
  `output_variables` field the finalizer must read anyway.

`agent_meta.json` wins on every axis. The finalizer already receives `artifacts_dir`.

### 4.4 Composition model

- **Ordered list with `depends_on`** → topological sort, ties broken by config key order. Captures the one real
  dependency shape ("close the bead before committing; commit last") without inventing a scheduler.
- **Full DAG workflow engine** → over-engineered; SASE already has one (xprompt workflows) and it is the wrong layer.
- **Implicit priority integer** → brittle as soon as plugins contribute entries.

### 4.5 Where the Rust core boundary falls

Per the `rust_core_backend_boundary` memory, the litmus test is "would another frontend need this to match the TUI?"

- **Trigger/guard evaluation and the decision record**: yes → belongs in `sase_core`, mirroring
  `axe_chop::decision::evaluate_chop_decision`. A `sase final list` CLI, the ACE dashboard, and a future web view must
  all agree on "would this finalizer fire right now?".
- **Config composition of the keyed registry**: yes → `config::merge` / the keyed-composition path already used by axe.
- **Execution driver** (subprocess spawn, prompt passes, artifact writes, provider re-invocation): no → stays Python;
  it is inherently coupled to `LLMProvider`.

Recommendation: land the Rust decision engine **with the trigger phase**, not with the initial refactor. Phase 1 (§6)
introduces a registry with exactly one entry and one implicit trigger, crosses no frontend boundary, and would only
churn a Rust wire that has not stabilized.

---

## 5. Recommended design

### 5.1 The finalizer contract

A finalizer is a named, three-part contract:

```
  ┌── trigger ──────────┐   ┌── prompt pass (×N) ────────┐   ┌── script ──────────────┐
  │ host-evaluated;     │   │ provider turn; the agent   │   │ subprocess; performs   │
  │ cheap; no LLM.      │─▶ │ records intent as          │─▶ │ the deterministic      │
  │ "is there work?"    │   │ sase variables.            │   │ effect. Returns a      │
  └─────────────────────┘   └────────────────────────────┘   │ structured result.     │
             ▲                                                └───────────┬────────────┘
             └──────────────── re-evaluate ───────────────────────────────┘
```

Loop: evaluate trigger → if satisfied, done. Otherwise run one prompt pass, then the script, then re-evaluate. Repeat
up to `max_passes`. On exhaustion, apply `on_failure`.

The current commit finalizer *is* this, with the parts unnamed: its trigger is "any enforced repo dirty", its prompt is
`build_commit_instruction_message`, its `max_passes` already exists, and `sase-be` is adding the missing script stage.
Either half may be omitted: a finalizer with no `prompt` is a pure post-run script; one with no `script` is today's
"nag the model until the trigger clears".

### 5.2 Configuration shape

Keyed map (§3.6), shipped in `src/sase/default_config.yml` with one builtin:

```yaml
finalizers:
  commit:
    description: |-
      Require every agent change to be committed before completion

      Detects uncommitted work in the primary workspace and every opened linked,
      external, and SDD sidecar repository, asks the agent to record commit intent
      as sase variables, then executes that intent deterministically.
    enabled: true
    scope: turn                    # turn | agent            (§5.8)
    trigger:                       # host-evaluated          (§5.4)
      provider: repo_dirty
    prompt_xprompt: _finalizer_commit   # or inline `prompt:` (Jinja2)
    script: sase_final_commit           # console-script name; resolved like a chop
    max_passes: 2
    timeout: 5m
    on_failure: fail               # fail | warn | skip      (§5.6)
    depends_on: []
    vars_prefix: commit            # reserved variable namespace (§5.5)
    env: {}
```

Notes:

- `description` follows the chop convention (summary line ≤100 chars, blank line, body) so `sase final list` and doctor
  output render like `sase chop` output.
- `prompt` / `prompt_xprompt` are mutually exclusive; `prompt_xprompt` is strongly preferred because it makes the text
  reviewable, translatable, and testable through the existing xprompt machinery, and keeps YAML free of prose.
- `script` resolution reuses `discover_chop_script`, so a plugin's `[project.scripts]` entry is found automatically.
- Every field is optional except `description` and at least one of `prompt`/`script`.

Retire `commit.finalizer.{enabled,max_passes}` by mapping it onto `finalizers.commit.{enabled,max_passes}` with a
deprecation diagnostic (the config layer machinery already has `_collect_deprecated_keys`).

### 5.3 The `%final` directive

Grammar, following the existing directive conventions in `src/sase/xprompt/_directive_types.py`:

| Form                              | Meaning                                                                 |
| --------------------------------- | ----------------------------------------------------------------------- |
| `%final:<name>`                   | Enable a registered finalizer for this launch (repeatable, accumulates) |
| `%final:<a>,<b>`                  | Comma list, like `%wait`                                                |
| `%final(<name>, max_passes=3)`    | Enable with bounded per-launch overrides                                |
| `%final(<name>, enabled=false)`   | Disable one finalizer for this launch                                   |
| `%final:-<name>`                  | Shorthand for the above                                                 |
| `%final:none`                     | Disable **all** finalizers for this launch (per-launch `SASE_DISABLE_COMMIT_STOP_HOOK`) |
| `%f`                              | Alias (the `f` alias slot is currently free)                            |

Implementation touch points, all mechanical:

- Add `"final"` to `_KNOWN_DIRECTIVES` and `"f": "final"` to `_DIRECTIVE_ALIASES` (`_directive_types.py:31-98`).
- Add `"final"` to `_MULTI_VALUE_DIRECTIVES` (`:45`) so repeats accumulate instead of raising "Duplicate directive".
- Collect paren kwargs in `_directive_collect.py` with a `supported_keys` allowlist, mirroring the `%wait` branch
  (`:104-123`) — this is what keeps override power bounded.
- Resolve in `_directive_values.py`, populate `PromptDirectives.finalizers`, and persist through `build_agent_meta`
  (§4.3).
- Add rows to `_DIRECTIVE_ARGUMENT_HINTS`, `_DIRECTIVE_DESCRIPTIONS`, and a `final_keyword` branch in
  `src/sase/ace/tui/widgets/directive_completion.py`, with argument values sourced from the registry so completion lists
  real finalizer names.

**Allowed override keys**: `enabled`, `max_passes`, `on_failure`, `timeout`. **Never** `script`, `command`, `env`, or
`prompt` — those stay config-only. This is the trust boundary.

**On the name.** `%final` reads well and matches "finalizer", but it collides conceptually with workflow `finally: true`
steps (§3.7). `%fin` is worse. `%after` describes the timing but not the enforcement. Recommendation: keep `%final`,
and disambiguate in docs by consistently calling the workflow feature "`finally` steps" and this one "finalizers".

### 5.4 Trigger providers

Start with a deliberately small closed set, extended the way chop trigger providers are:

| Provider       | Fires when                                                                        | Notes                                                |
| -------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `always`       | Every eligible turn/run                                                           | Default                                              |
| `repo_dirty`   | Any enforced repo has uncommitted changes                                          | Today's commit trigger; reuses `collect_dirty_state` |
| `vars_present` | The agent set variables matching `keys:` / the finalizer's `vars_prefix`          | The natural "agent requested this" trigger           |
| `vars_absent`  | Required variables are *missing* — i.e. the agent failed to report something      | The natural enforcement trigger                      |
| `script`       | Delegate to the finalizer's own script run in a cheap `--probe` mode              | The escape hatch                                     |

Plus `inhibit_if` guards reusing the chop guard providers (`changespec`, `agent_hood`, `agent_clan`) verbatim — same
YAML, same Rust evaluator, same docs.

`vars_absent` deserves emphasis: it is what makes requirement 5 ("expect all agents to set sase variables") enforceable
rather than aspirational. A `report` finalizer with `trigger: {provider: vars_absent, keys: [summary]}` and a prompt of
"you did not set a `summary` variable; set one now" turns a convention into a contract, using machinery that costs
nothing when the agent complied.

### 5.5 The sase-variable contract

Generalize the `STOP` / `commit_*` special cases into one rule:

- A finalizer named `<n>` owns the `<n>_*` variable prefix by default (`vars_prefix` overrides it). Registration of two
  finalizers with overlapping prefixes is a config diagnostic.
- The finalizer's script receives those variables in its JSON context; it does not re-read `agent_meta.json`.
- On a satisfied result, the driver calls `clear_agent_output_variables` (added by `sase-be` phase `list-vars-python`)
  for the consumed keys.
- `_completion_output_variables` (`run_agent_runner_finalize.py:191-205`) filters *any* variable whose prefix belongs to
  a registered finalizer, replacing today's hand-maintained `STOP` filter and `sase-be`'s planned `commit_*` filter with
  one rule.

### 5.6 Failure semantics

`on_failure` is per finalizer:

| Value            | Effect                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| `fail` (default for `commit`) | Raise `FinalizerError` → run recorded failed, no completion notification. Preserves today's behavior. |
| `warn`           | Record in `finalizer_result.json` and append a warning to the completion notification; run completes.  |
| `skip`           | Record only.                                                                                            |

Independently, and following the file-hooks precedent: **a finalizer that cannot be loaded, resolved, or spawned is
always a warning, never a failure.** A typo in a plugin's `finalizers:` block must not brick every agent run. Only a
*triggered, executed, unsatisfied* finalizer with `on_failure: fail` fails the run.

A dependency that ended unsatisfied under `on_failure: fail` causes dependents to be skipped with reason
`dependency_failed` — recorded, not silent.

### 5.7 Script contract

Mirror `sase.chops.sdk` rather than inventing a second SDK — ideally by extracting the shared parts into a
`sase.finalizers.sdk` that re-exports the chop primitives:

```
argv:  <script> --context <path-to-context.json>
env:   SASE_FINAL_RESULT_FILE, SASE_ARTIFACTS_DIR, SASE_PROJECT_DIR, SASE_AGENT_TIMESTAMP,
       SASE_FINALIZER_NAME, SASE_FINALIZER_PASS, plus the spec's `env:` merged over
context: { schema_version, finalizer, pass, max_passes, project_dir, artifacts_dir,
           agent: {name, bead_id, workspace_num, ...}, variables: {...}, trigger: {...} }
result:  { schema_version, status: "satisfied"|"unsatisfied"|"error",
           reason, counters, evidence, warnings, consumed_variables }
```

Execution hygiene copied from `clan_summary_script.py`: `start_new_session`, hard timeout, process-group kill,
bounded stdout capture, stderr appended to the agent log **and** to a per-finalizer artifact log.

### 5.8 Scope: `turn` vs `agent`

Because today's finalizer is a per-turn hook (§1.4), make the ambiguity explicit:

- `scope: turn` — runs after each successful `invoke_agent` turn. Today's behavior; the v1 default; what `commit` keeps.
- `scope: agent` — runs once, in `finalize_loop` (`run_agent_exec_finalize.py:524`), before the done marker. Reserved
  for a follow-up phase; it is the right home for "summarize the run", "publish artifacts", "notify".

Also worth documenting plainly: mentors, CRS, and fix hooks route through `invoke_agent` but carry no prompt directives,
so they get config defaults only. That is correct, but it should be a stated rule rather than an accident.

### 5.9 Plugin support — no new machinery

1. **Declaration**: a plugin ships `default_config.yml` containing a `finalizers:` block. It is picked up as its own
   config layer between `default` and `user` (`layers.py:154-183`) via the existing `sase_config` entry-point group.
   Users override or disable it by key. `SASE_DISABLE_PLUGIN_CONFIG` already disables the whole tier.
2. **Implementation**: the plugin declares a console script in `[project.scripts]`; `discover_chop_script` finds it in
   the interpreter's `bin/` even when `PATH` symlinks are stale.

Both mechanisms are load-bearing today for `sase-github`, `sase-telegram`, and `sase-nvim`. Nothing new is required —
which is the strongest argument for this shape.

### 5.10 Artifacts and observability

- `finalizer_result.json` — one document, per-finalizer entries: `{name, status, reason, passes, triggered, duration_ms,
  consumed_variables, warnings, error}`.
- Keep writing `commit_finalizer_result.json` as a compatibility alias for one release; it is read by docs, ACE, and
  `sase-be` phase `finalizer-vars-commit` step 4.
- Per-pass prompts/responses: `finalizer_<name>_pass_<N>_{prompt,response}.md`, generalizing
  `commit_finalizer_pass_prompt_filename` (`src/sase/core/commit_finalizer_prompt_artifacts.py`).
- Script stderr: `finalizer_<name>_stderr.log`, in the `clan_summary_stderr.log` format (timestamp / attempt / outcome /
  argv / env names / stderr).

### 5.11 CLI surface

Following `cli_rules` (alphabetized, short alias on every public long option, bare group delegates to `list`):

```
sase final list                 # registry with source layer, enabled state, trigger
sase final show <name>          # full resolved spec + provenance
sase final run <name> [-a DIR]  # execute against an artifacts dir, for authoring/testing
sase final doctor               # unresolvable scripts, dependency cycles, prefix collisions
```

`sase final doctor` should also be wired into `sase doctor`, alongside `checks_plugins.py` and `chop_doctor.py`.

---

## 6. Phasing

Sized as beads/phases, each independently landable and each leaving the tree working.

| Phase | Title                                  | Content                                                                                                                                                | Depends on            |
| ----- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------- |
| 1     | Finalizer registry and driver          | `finalizers:` keyed config + schema + `FinalizerSpec` + driver that runs an ordered list. Ship exactly one entry (`commit`) reproducing today's behavior byte-for-byte. Deprecate `commit.finalizer.*`. **No user-visible feature change.** | `sase-be` phase 5     |
| 2     | Script stage and SDK                   | Script discovery/execution/result contract; `sase_final_commit` becomes the commit finalizer's script; artifacts generalized.                            | 1                     |
| 3     | Triggers and guards                    | Trigger providers + `inhibit_if`; **Rust decision engine in `sase_core`** mirroring `axe_chop::decision`; `sase final list/show/doctor`.                | 2                     |
| 4     | `%final` directive                     | Directive parsing, `PromptDirectives.finalizers`, `agent_meta.json` persistence, TUI completion, docs.                                                  | 3                     |
| 5     | Dependencies, `on_failure`, `scope: agent` | Topological ordering, failure policies, the once-per-agent hook in `finalize_loop`.                                                                | 4                     |
| 6     | Plugin documentation and a reference plugin | Document both seams; ship one non-commit builtin (e.g. a `vars_absent`-triggered `report` finalizer) to prove the abstraction.                     | 5                     |

Phase 1 is the whole bet: if the commit finalizer cannot be expressed as an ordinary registry entry without a special
case, the model is wrong and should be revised before phases 2-6 build on it.

---

## 7. Risks and open questions

- **Collision with `sase-be`.** `sase-be` phases 3-5 are in progress and rewrite the same files
  (`commit_finalizer.py`, `commit_instructions.py`, `commit_finalizer_prompting.py`). Phase 1 here **must** land after
  `finalizer-vars-commit`, or the two efforts will conflict continuously. The upside is large: `sase-be` delivers the
  script stage for the commit finalizer, so phase 2 becomes mostly extraction rather than invention.
- **Latency.** Each triggered finalizer adds at minimum a trigger evaluation and at most `max_passes` provider turns to
  every agent turn. With N finalizers this multiplies. Mitigations: triggers must be cheap and host-evaluated (never an
  LLM call); `repo_dirty` should be computed once per turn and shared; a global cap on total finalizer passes per turn
  is worth considering in phase 5.
- **Trust boundary drift.** The value of the config-only definition rule is entirely in its enforcement. The `%final`
  kwarg allowlist must be a closed set validated at parse time, and it must be covered by a test that fails when someone
  adds `script` to it. Note that `local` config (`sase/sase.yml` in-repo) is checked in, so a malicious PR could add a
  finalizer — the same exposure `file_hooks` and `chops` already carry, and worth stating rather than discovering.
- **Prompt-pass semantics for non-agent callers.** Mentors/CRS/fix hooks getting config-default finalizers is probably
  right, but it should be verified against real mentor runs before phase 1 lands, since a `fail` policy there converts
  mentor turns into failures.
- **Naming.** `%final` vs workflow `finally:` steps (§5.3). Decide before phase 4; renaming a shipped directive requires
  a `_DEPRECATED_DIRECTIVE_MESSAGES` entry, as `%name`/`%tribe` did.
- **Where the registry lives long-term.** Phase 3 puts trigger evaluation in `sase_core`. Whether the *registry loading*
  should also move (as axe config composition did) is deferred — it should follow the same trigger as axe did, namely a
  second frontend needing it.

---

## 8. Recommended solution (summary)

**Build a keyed `finalizers:` config registry whose entries are three-part contracts — a host-evaluated trigger, bounded
prompt passes that ask the agent to record sase variables, and a script that performs the deterministic effect — and
make `%final` a selection-and-bounded-override directive over that registry, never a definition site.**

Concretely:

1. **Config, not prompt, is the definition site.** `finalizers:` is a **map** keyed by name (never a list — the `user`
   config layer replaces lists, `layers.py:195`), shipped with a single builtin `commit` entry. `finalizers: {commit:
   {enabled: false}}` disables the default; the same works for any future default or plugin entry.
2. **`%final:<name>` selects; `%final(<name>, max_passes=3)` tunes; `%final:-<name>` and `%final:none` opt out.** The
   kwarg allowlist is closed (`enabled`, `max_passes`, `on_failure`, `timeout`) so a prompt can never introduce an
   executable. Alias `%f`; multi-value like `%wait`.
3. **Selections travel in `agent_meta.json`, not the environment** — durable across re-exec, already read by every
   consumer, no nested-launch leakage.
4. **The execution model is trigger → prompt passes → script → re-evaluate**, bounded by `max_passes`, which is exactly
   what `sase-be` is building for commits. Generalizing is naming, not inventing.
5. **Reuse axe-chop machinery end to end**: `ChopConfig`'s field vocabulary, `discover_chop_script`, the
   `--context`/result-file protocol, the `sase.chops.sdk` result builder, `inhibit_if` guard providers, and
   `axe_chop::decision::evaluate_chop_decision` as the model for a Rust trigger evaluator.
6. **Plugins need no new seam**: declare via a `sase_config` entry-point `default_config.yml` layer, implement via a
   console script. Reject an in-process `sase_finalizers` Python entry-point group.
7. **One reserved-namespace rule** (`<name>_*`, cleared on success, filtered from completion notifications) replaces the
   growing set of `STOP` / `commit_*` special cases.
8. **Failure policy is explicit per finalizer** (`fail`/`warn`/`skip`), while *loading and spawning* failures are always
   soft — a broken plugin entry must never brick an agent run.
9. **Sequence it after `sase-be`**, and prove the abstraction in phase 1 by expressing today's commit finalizer as an
   ordinary registry entry with zero special cases. If that is not possible, the model needs revision before anything
   is built on it.

The distinguishing property of this design is that almost none of it is new code. It is the axe-chop config and
execution model, the file-hooks fail-soft posture, the notification-gate registry discipline, and the `sase-be` variable
contract, assembled at a new call site. That is why it is worth doing this way rather than growing a second
`commit.finalizer`-shaped block for every future enforcement need.
