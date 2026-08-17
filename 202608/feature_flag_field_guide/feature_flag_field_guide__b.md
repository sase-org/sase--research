---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# SASE Feature Flags In Practice: What They Are Good For, And What To Fix First

**Research question:** Now that SASE's feature-flag system has shipped, what is it actually
useful for, and how should it be improved?

**Scope:** the as-built system at `790cb61ee` (SASE 0.16.0), inspected on 2026-08-17. This is
an evaluation of shipped behavior, not a design proposal. Every defect below was reproduced
against the working tree. No runtime code was changed.

**Relationship to prior research.** Three earlier reports designed this system:
[`feature_flag_architecture.md`](feature_flag_architecture.md) (2026-08-15) and the
consolidated
[`feature_flag_lifecycle_governance/`](feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)
(2026-08-16) with its two source reports. Those answered "what should we build." This one
answers "what did we get, and what does it buy us." Their conclusions are not restated except
where the shipped system diverges from them.

## Bottom line

The system is **worth keeping and is being under-used, but for a different reason than its
own framing suggests.**

A SASE feature flag is not primarily a switch. It is a **scheduled deletion with a switch
attached**. Almost every part of the shipped machinery — the mandatory flag bead, the
date+release thresholds, the five-minute chop that raises a `FlagTriage` gate, the gate action
that *launches a removal agent*, the lint that errors when a bead closes while its definition
survives — exists to force a future deletion to actually happen. The boolean is the cheap
part. The deletion contract is the product.

That reframing changes the answer to "how much use is this?":

- **Use a flag when you want to guarantee a future decision point** about code you are
  knowingly leaving in an unfinished or duplicated state. That is the only thing this system
  does that nothing else in SASE does.
- **Do not use a flag when you just want the behavior to be configurable.** The Config Center
  and `sase.yml` already do that, for free, forever.

This matters more in SASE than in a typical repository because *agents write the code*. Agents
add branches readily and delete them almost never; there is no standing reviewer who remembers
that a fallback path was supposed to be temporary. The registry-plus-bead loop is a deletion
scheduler for a codebase whose authors have no memory across runs. That is the strongest
argument for the system, and it is not the argument the memory note currently makes.

The system is also **one day old** — both flag beads were created 2026-08-16 19:31 EDT — with
two flags, two call sites, zero removals, and no `wip`, `ops`, or `project`-scoped flag ever
created. So there is no empirical track record. What follows is a design-and-defect evaluation,
and it is labeled as such.

The single most important fix is not a feature: **the env transport currently marks every flag
in every child process as an override**, which makes `sase doctor` warn permanently inside
agent runs about flags that are sitting at their registry defaults. That defect trains
everyone — Bryan and agents alike — to ignore the one check that is supposed to catch a
genuinely hidden override.

## 1. What actually shipped

### 1.1 The parts

| Piece | Location | Size |
| --- | --- | --- |
| Registry, models, resolver, snapshot, env transport, schema gen | `src/sase/feature_flags/` | ~1,300 lines |
| `FlagTriage` gate (spec, response, actions, preview, input) | `src/sase/bead/_flag_gate_*.py`, `flag_gate*.py` | ~880 lines |
| Registry/bead integrity lint | `tools/check_feature_flags` | 930 lines |
| Doctor checks | `src/sase/doctor/checks_flags.py` | 294 lines |
| CLI (`list`/`new`/`show`) | `src/sase/feature_flags/cli*.py`, `main/parser_flag.py` | ~740 lines |
| Registered flags | `src/sase/feature_flags/registry.py` | **2** |
| Non-test call sites | `file_references.py:517`, `run_agent_exec_plan_accept.py:470` | **2** |

Roughly 4,800 lines of machinery behind two booleans. That ratio looks damning and mostly is
not: the lint, gate, doctor, and CLI are **fixed** costs amortized across every future flag.
The marginal cost of flag number three is a registry entry, a schema regen, a call site, and
two tests. It is worth stating the fixed cost plainly, though, because it sets the bar: this
investment only pays back if flags are actually created and — more importantly — actually
removed.

### 1.2 The loop, end to end

```
sase flag new <key>
  └─ creates the `flag` removal bead (remove_by = today+90d / current-minor+2)
  └─ prints the registry entry to paste

     [ registry entry + generated schema block + gated call site + both-states tests ]

  ├─ just lint  → tools/check_feature_flags  (9 rules, static + bead status)
  ├─ sase doctor → flags.registry / flags.overrides / flags.due
  └─ sase flag list / show → value, provenance, bead, countdown, call sites

     ... 90 days pass, and the release threshold passes ...

  chop `bead_task_triage` (every 5 min, default_config.yml:738)
  └─ raises exactly one FlagTriage gate for the due flag bead
       ├─ Remove  → notes the winning branch, then LAUNCHES a removal agent
       │            (`_flag_gate_actions.py:30-71`) briefed to delete the losing
       │            branch and the registry entry in the change that closes the bead
       ├─ Extend  → rewrites both thresholds, requires a reason
       ├─ Keep    → launches a promotion agent (→ `ops`, or an ordinary config field)
       └─ Close   → cancels the bead with a reason
```

The important detail is the arrow marked **LAUNCHES**. The removal is not a reminder, a TODO,
or a lint warning that a human must act on. It is an agent launch that the gate submits on
Bryan's behalf. `sase bead work` accepts `FLAG`-type beads through the task path
(`cli_work_task.py:120`), so the loop closes without any bespoke plumbing.

### 1.3 Resolution model

Precedence, lowest to highest (`resolver.py:118-216`):

1. registry default
2. `user` config layer (`~/.config/sase/sase.yml`)
3. `overlay:*` machine overlays
4. `local` project config — **rejected for `scope: global` flags** with a diagnostic
5. explicit in-process `override_flags(...)` (tests)
6. deprecated legacy env aliases (`SASE_DISABLE_PRETTIER` today)
7. `SASE_FEATURE_FLAGS` JSON object

`plugin:*` layers are skipped entirely (`resolver.py:154-155`) — installing a plugin cannot
flip a first-party default, by design. `install_process_feature_flags()` pins one immutable
snapshot and exports it into `os.environ` for children; it is called at exactly three
boundaries: `ace_handler.py:166`, `axe_handler.py:14`, `run_agent_runner.py:261`.

Each flag is also a first-class Config Center field, because the schema block is generated with
closed `properties` per key. Verified:

```
feature_flags.coder_inherits_planner_chat  boolean  default False
feature_flags.prettier_enabled             boolean  default True   deprecated
```

So flipping a flag from ACE's Config Center already works today. That is better than the CLI
surface suggests, and it is not documented anywhere a user would look.

## 2. What the mechanism is genuinely good at

**It converts "we'll clean this up later" into a dated work item with a named executor.** No
other SASE mechanism does this. A TODO comment has no due date. A task bead has no link to the
code that must die. `symvision`'s epic whitelist expires against an epic, not against a
behavior. The flag bead is the only construct that says *this specific branch of this specific
routing decision must be deleted, and here is the date on which someone will be asked about
it.*

**It makes a half-finished landing legible instead of invisible.** Without a flag, a partially
landed path is discoverable only by reading the code. With one, it appears in `sase flag list`,
in `sase doctor`, in the bead views, and in the lint. The cost of the incompleteness becomes
visible to its owner.

**It gives a single-user product a way to A/B its own defaults.** Bryan is the entire user
population and also the test population. `coder_inherits_planner_chat` is exactly the shape of
question that cannot be answered by reasoning — you find out whether a coder inheriting the
planner's chat produces better work by living with both for a while. A flag is the cheapest
container for that experiment.

**It has one honest safety property:** because the value never changes based on the clock
(`flag_due.py:1-14`), a released SASE cannot time-bomb itself. Expiry drives diagnostics only.

## 3. What it is not good at, and should not be used for

- **Permanent user choice.** If Bryan is meant to pick forever, it is a config field. The
  memory note already says this; it is the single most likely misuse.
- **Dev/debug scaffolding.** `SASE_TUI_TRACE`, `SASE_TUI_PERF`, `SASE_ACE_DEBUG_LEAKS` are not
  user-reaching behavior. Making them flags adds bead ceremony to things that should stay
  cheap env switches.
- **Per-run or per-agent behavior selection.** The snapshot is per process and is pinned by
  the parent. There is no launch-time override (`sase run` has no `--flag`; `sase flag` has
  only `list`/`new`/`show`). Two agents launched from the same ACE cannot disagree about a
  flag. See improvement 6.
- **Rollout safety.** There is no deploy, no cohort, no blast radius. SASE is installed from
  source by one person. The rollback framing in the general feature-flag literature does not
  transfer.
- **Wire, schema, or file-format migration.** A flag chooses behavior *after* compatibility is
  established. This was settled in the prior research and remains true.
- **Anything Rust core must decide independently.** Core cannot read flags; only the resolved
  boolean crosses the binding. See improvement 9.

## 4. Verified defects and gaps

Each item below was reproduced at `790cb61ee`.

### 4.1 The env transport marks inherited defaults as overrides

`apply_feature_flags_env` encodes **every** resolved flag (`env.py:76-89`), and `_apply_values`
sets `overridden=True` unconditionally for anything an env or config layer mentions
(`resolver.py:108-115`). So in any child process — which is every agent, every hook, every
`sase` subcommand run from an agent shell — every flag reports `source=env, overridden=yes`
even when it equals the registry default.

Reproduction:

```
$ sase flag show prettier_enabled            # inside an agent shell
  effective:  on
  source:     ENV:SASE_FEATURE_FLAGS
  overridden: yes

$ env -u SASE_FEATURE_FLAGS sase flag show prettier_enabled
  effective:  on
  source:     default
  overridden: no
```

Three consequences:

1. `sase doctor -C flags` is **WARN inside every agent process and OK outside it**, with
   identical values. `override_integrity_findings` iterates `snapshot.non_default()` and emits
   `env_inherited` for each (`integrity.py:198-215`). Verified: `WARN: 1` with the env set,
   `OK: 1` with it cleared.
2. The startup log line `feature flags resolved; non-default: …` (`snapshot.py:100-109`) lists
   every registered flag in every agent run.
3. `sase flag list`'s ENV marker — documented as existing "so a long-running detached process
   cannot hide an override" (`parser_flag.py:48`) — cannot distinguish a real override from an
   inherited default. It marks everything, so it signals nothing.

This is the highest-value fix in the report: it is small, and until it is fixed the check that
is supposed to make hidden overrides falsifiable is permanently yellow.

### 4.2 `scope: project` does not work for ACE-launched agents

ACE deliberately resolves flags with project-local config **off**, and the comment says why:
"local config should only apply to agent runs (which are separate processes)"
(`ace_handler.py:159-166`). It then exports that local-config-free snapshot into `os.environ`.
Agents inherit it, and env sits at the *top* of precedence in the child, above the agent's own
project config.

Verified directly against the resolver:

```python
resolve_feature_flags(
    definitions={"proj_flag": …scope="project", default=False…},
    layers=[LayerInput(name="local", values={"proj_flag": True})],
    env_value='{"proj_flag":false}',
)
# → FeatureFlagDecision(enabled=False, source='env', overridden=True)
```

So a project-scoped flag set in a project's `sase/sase.yml` is silently overridden in exactly
the process the ACE comment says it was meant for. `scope` is a first-class registry field with
its own resolver rule and its own doctor diagnostic, and it has zero working users. This is
latent rather than active — both current flags are `global` — but it is a documented capability
that does not do what it says.

### 4.3 The release threshold is decorative at SASE's cadence

A flag is due only when **both** thresholds pass (`flag_due.py:26-43`). Defaults are
`today + 90 days` and `current minor + 2` (`defaults.py:11-31`).

Observed minor-release cadence: v0.5.0 (2026-06-24) through v0.16.0 (2026-08-07) is 11 minors
in 44 days — about one per four days, so `+2 minors ≈ 8 days` against a 90-day date. Both
current flag beads carry `remove_by: 2026-11-14 / 0.18.0`, and 0.18.0 will ship months before
2026-11-14. The date binds; the release threshold contributes nothing but the impression of a
second gate.

(Caveat: no minor has been tagged in the ten days since v0.16.0, so the cadence may be
slowing. The conclusion holds under any cadence faster than one minor per 45 days.)

The conjunction is the *safe* choice — it cannot fire early — so this is a calibration bug,
not a correctness bug. But a threshold that is always already satisfied should either be
calibrated to the real cadence or dropped.

### 4.4 The removal half has no tooling

`sase flag new` scaffolds creation. Nothing scaffolds removal — which is the half the whole
design exists to force, and the half that will be executed repeatedly by agents who have never
done it before. A removal agent must rediscover, every time: delete the enum member, delete the
registry entry, run `just sync-feature-flags-schema`, find and collapse the call sites, delete
the losing branch, delete the both-states tests, and close the bead in the same change.

### 4.5 The `new` scaffold omits the schema-sync step

`_scaffold_text` (`cli_new.py:170-188`) prints the registry entry and a four-item both-states
checklist. It never mentions `just sync-feature-flags-schema`, even though lint rule 2 will
fail without it (`check_feature_flags:249`). Every flag author hits an avoidable lint failure
and then has to go find the tool.

### 4.6 Both-states testing is a printed checklist, not a rule

The memory note requires tests for both states. `sase flag new` prints a checklist. The linter
does not check it: rule 3 requires only that each key have **at least one non-test reference**
(`check_feature_flags:305-330`). Today both flags happen to be covered — `prettier_enabled` in
`tests/feature_flags/test_consumers.py:86` and `coder_inherits_planner_chat` in
`tests/test_axe_run_agent_exec_plan_followup_coder_prompt.py:82` — but nothing keeps it that
way, and the losing branch of an untested flag is exactly what makes removal risky later.

### 4.7 Plugins cannot own flags

The registry is a closed `StrEnum` in the SASE source tree, `sase flag new` refuses to run
outside a SASE-managed checkout (`cli_new.py:33-38`), and `plugin:*` config layers are skipped
by the resolver. SASE has five plugin repos (`sase-github`, `sase-telegram`, `sase-nvim`,
`sase-research-artifacts`, plus the research sidecar). A plugin shipping a beta behavior has no
flag path at all — it gets ad-hoc env vars, which is the status quo the registry was built to
replace.

### 4.8 The ad-hoc env-gate population is untouched

The prior research counted five incompatible truthiness conventions across ~15 boolean env
gates. At `790cb61ee` that population is essentially unchanged: `SASE_DISABLE_PLUGINS`,
`SASE_DISABLE_PLUGIN_{FILE_HOOKS,LLM,XPROMPTS,ARTIFACT_REFS}`,
`SASE_DISABLE_COMMIT_STOP_HOOK`, `SASE_DISABLE_CODE_SWAP_LOCK`, `SASE_DISABLE_IMPORT_PRELOAD`,
`SASE_AGENT_AUTO_{APPROVE,DISMISS}`, `SASE_TUI_*`, and a `~/.sase/telegram_is_enabled` **file**
probe (`axe/chop_doctor.py:441`). Exactly one gate migrated: `SASE_DISABLE_PRETTIER`, retained
as a legacy alias (`env.py:26-32`), which proves the migration path works.

## 5. Ranked use cases

Ranked by expected value in SASE specifically, given one user, agent-authored changes, and
continuous landing to master.

### 1. Sunset a behavior you intend to delete (`sunset`)

**Verdict: the flagship case. Use it every time.**

You are replacing behavior and the old branch must stay reachable for a bounded window. The
flag's value is almost entirely the scheduled deletion: without it, the old branch survives
indefinitely because nothing tracks it. `prettier_enabled` is the model — default `true`, old
env alias retained, bead `sase-nx` holding the deletion date.

Tell-tale: you find yourself writing "we can remove this once X." That sentence is a flag bead.

### 2. Beta behavior only living with it can judge (`beta`)

**Verdict: use it when the question is genuinely empirical, not when you are hedging.**

Default off, opt in from the Config Center, live with it, then either flip the default or
remove it. `coder_inherits_planner_chat` is the right shape: no amount of reasoning settles
whether a coder inheriting the planner's chat produces better work.

The discipline that makes this work is a **decision criterion written into the bead** — what
you will look at in 90 days to decide. Without it the `FlagTriage` gate arrives and the honest
answer is "I never compared," which produces an Extend, and Extend is how flag debt is born.
This case is currently rate-limited by the missing per-agent override (improvement 6): you
cannot run the same task both ways without restarting ACE.

### 3. Ops kill switch for an external or expensive dependency (`ops`)

**Verdict: use it, and use it to consolidate the env-gate sprawl.**

Network calls, paid LLM providers, Telegram, plugin loading, heavy TUI subsystems — things you
want to switch off decisively when something is misbehaving, forever. `ops` requires a
rationale and creates no bead, so ceremony is low. The payoff is one parsing convention, real
provenance in `sase flag show`, doctor visibility, and a schema-documented switch instead of a
truthiness set copied inline for the sixth time.

Zero `ops` flags exist today. This is the largest untapped use case by volume.

### 4. Multi-change epic seam (`wip`)

**Verdict: use sparingly, and only for epics whose phases reach master separately.**

The classic "long-running branch" motivation is weaker here than the design docs assume,
because an epic's phase workers converge into a combined tree that the land agent lands as a
unit — so intermediate states often never reach Bryan's daily driver. A `wip` flag earns its
cost when a phase lands a user-reaching surface ahead of the phases that complete it, or when
an epic will span multiple landings.

One flag per **coherent routing decision**, never one per phase.

### 5. Risky replacement with a retained fallback

**Verdict: use only when the fallback is real and tested.**

A new engine/provider/renderer alongside the old one, with a bounded window to switch back.
This degenerates into permanent dual maintenance without the bead. With the bead it is
case 1 wearing different clothes — which is a good sign about the design.

### 6. Deprecating a *config field* or CLI surface

**Verdict: probably not a flag.**

Retiring a config key or command is a migration with its own deprecation machinery (the schema
already carries `deprecated` and `deprecated_replacement`, and `sase config layers` reports
retired keys). A flag adds a second, competing expiry mechanism. Use the flag only when the old
and new behaviors must both *execute*, not merely both *parse*.

### Do not use a flag for

Permanent user preferences (config field) · debug/trace scaffolding (env var) · per-agent or
per-run behavior (not supported; see improvement 6) · wire/schema/state migrations
(expand-and-contract) · anything Rust core must decide on its own (improvement 9) · gating a
change you could simply not land yet.

## 6. Ranked recommended improvements

Ranked by (value × confidence) ÷ cost. Sizes are rough agent-effort estimates.

### 1. Stop the env transport from reporting inherited defaults as overrides — **small**

**Why first:** it makes `sase doctor` permanently WARN inside every agent process (§4.1), which
is how a diagnostic becomes noise. It is also the cheapest fix in the list.

Two layers to the fix:

- **Minimal:** in `_apply_values` (`resolver.py:108-115`), set
  `overridden = (value != definition.default)` instead of `True`. `non_default()` then means
  what its name says, and the `env_inherited` warning fires only for values that genuinely
  differ from the registry.
- **Precise (preferred):** have the doctor compare the pinned env values against what *this*
  process would resolve without the env, and warn only on a real difference. That also catches
  the case the minimal fix misses — a stale env pinning a default value while the local config
  has since moved to non-default.

Either way `sase flag list` should keep showing `ENV` provenance; the bug is the override
*claim*, not the source label.

### 2. Give the removal half the tooling the creation half has — **medium**

Add `sase flag rm <key>`: remove the enum member and registry entry, run the schema sync, print
every remaining call site (`references.py` already finds them), print the both-states tests that
now need collapsing, and print the exact `sase bead close` invocation. Wire it into the brief
that `remove_flag_triage` hands the launched agent (`_flag_gate_actions.py:57-61`).

**Why:** removal is the half the entire design exists to force, it will be executed repeatedly
by agents starting from zero context, and it is currently the *least* supported operation in
the system. Every ungrooved removal is a chance to leave a half-deleted flag behind — which
lint rules 7 and 8 will catch, but only after the fact.

### 3. Fix or retire `scope: project` — **small to medium**

Either make it work — scrub `SASE_FEATURE_FLAGS` at agent launch and re-resolve in the agent's
own project (the `_remove_inherited_*` scrubber pattern in `agent/launch_spawn.py` is right
there and handles exactly this class of problem), or merge the inherited snapshot as a *lower*
precedence layer than local config for project-scoped keys — or delete the scope field until
there is a real consumer.

**Why:** a documented capability that silently does the opposite of its documentation is worse
than an absent one, and the ACE comments at `ace_handler.py:161-165` state the intent that the
code defeats. Retiring it is a legitimate outcome: zero flags use it.

### 4. Enforce both-states coverage in the linter — **small**

Add rule 10 to `tools/check_feature_flags`: every non-`ops` key must appear in the test tree
under both `True` and `False` — trivially detectable via `override_flags(key=…)` literals and
`feature_flags` layer dicts in tests.

**Why:** the requirement is already written in memory and printed by the scaffold, so this
closes a gap between stated policy and enforcement at near-zero cost. It also protects the
losing branch, which is precisely the code a removal agent must confidently delete 90 days
later.

### 5. Recalibrate or drop `remove_by_release` — **small**

Either derive the default release threshold from observed tag cadence so it lands near the date
threshold, or make `remove_by_date` the sole default and treat the release as an optional
extra constraint an author can add deliberately.

**Why:** §4.3 — at ~1 minor per 4 days, `+2 minors` is ~8 days against a 90-day date, so the
conjunction is a single-threshold system wearing a two-threshold costume. Fixing the default
costs a few lines in `defaults.py`; the semantics in `flag_due.py` need not change.

### 6. Add a per-launch flag override — **medium**

A `sase run`/launch-path option (and the matching xprompt directive) that injects
`SASE_FEATURE_FLAGS` for one agent, on top of the parent's pinned snapshot. `extra_env` already
threads through the launcher; nothing user-facing exposes it.

**Why:** it turns the `beta` use case from "flip it and hope I remember what the other way felt
like" into an actual comparison — launch the same task twice, once each way. That is a
SASE-specific capability no general-purpose flag system offers, and it is what makes the
`FlagTriage` "Remove: which branch wins?" question answerable with evidence instead of vibes.
It is ranked below the correctness fixes because it is additive, not repair.

### 7. Migrate the user-reaching env gates to `ops` flags — **medium, incremental**

Start with `SASE_DISABLE_PLUGINS` (five sites), `SASE_DISABLE_COMMIT_STOP_HOOK`, and the
Telegram file-probe in `axe/chop_doctor.py:441`. Retain each old name through
`_LEGACY_ENV_MAPPINGS` exactly as `SASE_DISABLE_PRETTIER` did. Leave `SASE_TUI_*` and
`SASE_ACE_DEBUG_LEAKS` alone — they are dev scaffolding, not user-reaching behavior.

**Why:** one truthiness convention instead of five, real provenance, doctor coverage, and
schema documentation. It also gives the registry a population large enough to be worth
consulting — a two-entry `sase flag list` is not a habit anyone forms.

### 8. Close the small documentation and scaffold papercuts — **xsmall**

- Add `just sync-feature-flags-schema` to the `sase flag new` scaffold output (§4.5).
- Have `sase flag list`/`show` state *how* to change a value — the Config Center path and the
  config key — since each flag is already a first-class Config Center field and nothing says so.
- Note in `sase/memory/sase_flags.md` that a flag's primary product is its scheduled deletion,
  and that a `beta` flag's bead should carry the decision criterion that will settle it.

**Why:** cheapest items in the report; each removes a rediscovery cost that every future flag
author pays.

### 9. Decide the plugin and Rust-core seams deliberately — **large, defer until a consumer exists**

Two capability gaps with no current consumer:

- **Plugins** (§4.7) cannot own flags. If a plugin needs one, the honest options are a
  namespaced plugin registry contributing definitions, or a documented statement that plugins
  use plain config fields and no flags.
- **Rust core** cannot resolve flags; only resolved booleans cross the binding. Given the
  repo's own rule that shared backend behavior belongs in `sase-core`, any *core* behavior you
  want to gate must be gated from the Python call-through point. That is fine today. If a
  standalone Rust process or non-Python frontend ever needs to resolve independently, that is
  the trigger to promote the resolver — as the prior research concluded.

**Why last:** both are real, neither blocks anything now, and building either speculatively is
how a small mechanism turns into the reverted daemon rollout registry that the original research
warned about.

## Sources

Repository evidence, all at `790cb61ee` (SASE 0.16.0):

- `src/sase/feature_flags/` — `registry.py`, `models.py`, `resolver.py`, `snapshot.py`,
  `env.py`, `defaults.py`, `integrity.py`, `references.py`, `schema.py`, `cli_new.py`
- `src/sase/bead/flag_due.py`, `flag_gate.py`, `_flag_gate_spec.py`, `_flag_gate_actions.py`
- `src/sase/scripts/_bead_task_triage_state.py`, `_bead_task_triage_gates.py`
- `src/sase/main/ace_handler.py:159-166`, `axe_handler.py:14`, `axe/run_agent_runner.py:261`
- `src/sase/doctor/checks_flags.py`, `tools/check_feature_flags`, `tools/sync_feature_flags_schema`
- `src/sase/default_config.yml:738-750` (chop schedule), `Justfile:292,296,754`
- `src/sase/file_references.py:513-537`, `src/sase/axe/run_agent_exec_plan_accept.py:466-471`
- `tests/feature_flags/`, `tests/test_axe_run_agent_exec_plan_followup_coder_prompt.py`
- beads `sase-nw`, `sase-nx`; git tags v0.5.0–v0.16.0 for release cadence

Prior research (not restated):

- [`feature_flag_architecture.md`](feature_flag_architecture.md)
- [`feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md`](feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)

## Recommended solution

Keep the system, and change how it is framed and used.

**Framing:** a SASE feature flag is a scheduled deletion with a switch attached. Reach for one
when you want to guarantee a future decision point about code you are knowingly leaving in a
temporary state — not when you want something to be configurable.

**Usage priority:** `sunset` deprecations first, `beta` behaviors whose answer is empirical
second, `ops` kill switches third (and use them to absorb the ad-hoc env-gate sprawl), `wip`
epic seams sparingly.

**Repair priority:** fix the env-override reporting bug so `sase doctor` means something inside
agent runs; build `sase flag rm` so the removal half is as grooved as the creation half; fix or
retire `scope: project`; enforce both-states coverage in the linter; recalibrate the release
threshold. Then add the per-launch override that makes `beta` flags decidable with evidence.

Defer the plugin registry and the Rust resolver until a concrete consumer exists.
