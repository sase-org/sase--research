---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# How to Use SASE Feature Flags (and How to Improve Them)

**Research question:** Now that SASE has shipped a feature-flag system, how should
we actually use it, how useful is it today, and what should we improve next?

**Scope:** SASE workspace tree on 2026-08-17, after epic `sase-nb` landed. Live
inventory from `sase flag list` / `sase flag show`. Bead store: flag beads
`sase-nw` and `sase-nx`, follow-ups `sase-o2` and `sase-o3`. Prior architecture
research is treated as settled and is not redesigned here:

- [`feature_flag_architecture.md`](feature_flag_architecture.md) (2026-08-15)
- [`feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md`](feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)
  (2026-08-16)

External sources were re-checked on 2026-08-17. No runtime behavior was changed.

## Bottom line

SASE feature flags are useful, but **not as a product-management control plane**.
They are a **temporary boolean router whose real product is deletion**: a typed
registry, a dedicated flag bead, a date-and-release deadline, and a `FlagTriage`
gate that forces Remove / Extend / Keep / Close.

That is the right tool for three SASE jobs:

1. ship a user-visible beta without making it the default
2. keep an old branch reachable while a behavior migrates
3. land user-reachable incomplete work on the default branch when
   `symvision --epic-symbol` is not enough

It is the wrong tool for settings, debug knobs, process identity, percentage
rollouts, A/B tests, entitlements, or anything the user is meant to choose
forever.

Today the inventory is two flags, both created yesterday as the epic's first
consumers. That is not evidence the system is unused. It is evidence the system
is one day old and that creating a flag is still a multi-step paste-and-test
ritual. The bigger risk is the opposite of neglect: the short-term agent
instruction says **MUST** flag any not-ready user-reaching behavior, while the
lifecycle design and GitLab's own handbook say **flag only when needed**. If
that contradiction is left standing, agents will either over-flag (and pay a
both-states tax on every change) or ignore the instruction (and keep shipping
ad-hoc `SASE_*` env gates).

Use flags sparingly, at one routing boundary, with both states tested, and with
the removal bead treated as part of the feature. Improve the system first by
teaching that decision, then by making create/toggle/inspect cheaper, then by
fixing the two known correctness gaps (`sase-o2`, `sase-o3`) before the first
`scope: "project"` flag or the first due `FlagTriage` gate.

## 1. What actually shipped

The implementation matches the 2026-08-16 lifecycle research more closely than
most SASE epics match their research. The important pieces are live:

| Piece | Where | Status |
| --- | --- | --- |
| Typed registry, boolean-only, four kinds | `src/sase/feature_flags/registry.py` | shipped, two members |
| Layered resolver + immutable snapshot | `resolver.py`, `snapshot.py` | shipped |
| Strict `SASE_FEATURE_FLAGS` JSON transport | `env.py`; installed at ACE, AXE, and agent-runner boundaries | shipped |
| Legacy env alias | `SASE_DISABLE_PRETTIER` → `prettier_enabled` | shipped |
| `sase flag list` / `show` / `new` | `src/sase/feature_flags/cli*.py` | shipped; `new` scaffolds, does not apply |
| Generated `feature_flags` schema properties | `src/sase/config/sase.schema.json` | shipped |
| `tools/check_feature_flags` | static + bead-status rules | shipped; both-states tests are **not** a lint rule |
| `sase doctor -C flags.*` | registry, overrides, due | shipped |
| Flag bead type + `FlagTriage` | `sase-nw`, `sase-nx`; AXE `bead_task_triage` | shipped |
| Shared ⚑ visual language | CLI, TUI Beads pane, bead pages, gate preview | shipped |
| Agent short memory | `sase/memory/feature_flags.md` | shipped; more aggressive than the design |

What did **not** ship, relative to the research and to common flag products:

- no `sase flag set` / `unset`
- `sase flag new` prints a paste block; it does not edit the registry or sync
  the schema
- no ACE status chrome for non-default flags
- no plugin-owned flags
- no OpenFeature adapter, targeting, percentages, or remote control plane
- `scope: "project"` exists in the model but is unsafe to use (`sase-o2`)
- `FlagTriage` preview omits call sites (`sase-o3`)
- `plugins_enabled` was the recommended first consumer and was **not** created
- `agents_daemon_reads_enabled()` is still an unconditional `return False`

That last point is useful. The old daemon seam was deliberately *not* the first
flag, because a dead `return False` proves nothing about a live toggle. The
first two consumers are real branches.

## 2. How much use they currently have

### 2.1 The live inventory

`sase flag list` on 2026-08-17:

| Key | Kind | Default | Effective | Scope | Bead | Remove by |
| --- | --- | --- | --- | --- | --- | --- |
| `coder_inherits_planner_chat` | `beta` | off | off | global | `sase-nw` (open) | 2026-11-14 / 0.18.0 |
| `prettier_enabled` | `sunset` | on | on | global | `sase-nx` (open) | 2026-11-14 / 0.18.0 |

No `wip` flags. No `ops` flags. No `scope: "project"` flags. No user, overlay,
or project-local `feature_flags:` overrides exist in repo-managed YAML.

Both beads were created by phase `sase-nb.9` on 2026-08-16, ~13 hours before
this report. The 90-day / +2-minor default window is what `sase flag new`
computes (`defaults.py`: 90 days, current minor + 2). Neither flag is anywhere
near due. `FlagTriage` has never fired in production.

### 2.2 What the two flags actually do

**`coder_inherits_planner_chat` is a real beta.** The new default is that a
follow-up coder starts from the approved plan file alone. Enabling the flag
restores the old `#fork:<planner>--plan` inheritance. One call site
(`axe/run_agent_exec_plan_accept.py:469-471`). Both states are tested
(`tests/test_axe_run_agent_exec_plan_followup_coder_prompt.py`). This is the
textbook SASE beta: a user-visible behavior change that some people may still
want, disabled by default, with a removal deadline.

**`prettier_enabled` is a sunset of a disable switch, not of a new feature.**
Markdown prettier stays on by default. The flag exists so
`SASE_DISABLE_PRETTIER` can be retired through the registry instead of living
as a private env convention. One call site (`file_references.py:517`). Both
states reach the call site (`tests/feature_flags/test_consumers.py`,
`tests/test_format_with_prettier.py`). This is the textbook SASE sunset: keep
the losing branch explicit enough that a later worker can delete it in the same
change that closes `sase-nx`.

These two flags therefore already exercise the two highest-value kinds. They do
not yet exercise `wip`, `ops`, project scope, FlagTriage, or a default flip.

### 2.3 Why the inventory is small

Three reasons, in order:

1. **Age.** The epic closed yesterday. There has been almost no subsequent
   user-reaching work that needed a new router.
2. **Creation friction.** `sase flag new` creates the bead and prints a
   registry snippet. The agent still has to paste two members into
   `registry.py`, run `tools/sync_feature_flags_schema`, write both-states
   tests, and put the `current_flags().enabled(FeatureFlag.X)` call at a
   routing boundary. That is correct hygiene. It is also enough friction that
   an agent under time pressure will keep using `os.environ.get("SASE_…")`.
3. **The rest of the env-gate iceberg is still env.**
   `SASE_DISABLE_PLUGINS` and the `SASE_DISABLE_PLUGIN_*` family, 
   `SASE_DISABLE_COMMIT_STOP_HOOK`, `SASE_ACE_DEBUG_LEAKS`,
   `SASE_TOOL_LOG_FULL`, `SASE_AGENT_AUTO_APPROVE`, and the stall-watchdog
   disables were identified in the lifecycle research and have not been
   migrated. Some of them *should* stay env (see §5.2). The plugin kill
   switches were the recommended first consumer and are still ad hoc.

### 2.4 A provenance illusion that makes them look more used than they are

Every SASE-launched process in this session reports both flags as
`overridden: yes` with source `ENV:SASE_FEATURE_FLAGS`, even though both
effective values equal the registry defaults.

That is because `install_process_feature_flags()` encodes **every** resolved
boolean into `SASE_FEATURE_FLAGS` (`env.py:76-89`), and children inherit that
JSON via `os.environ.copy()`. The child then treats env as a winning layer
and marks `overridden=True` even when the value is the default.

Consequences:

- `sase flag list` cannot tell you whether anyone actually chose a value.
- `sase doctor -C flags.overrides` is designed to warn on inherited env
  (`integrity.py:198-215`). In an agent or ACE child it will warn on the
  entire inventory, forever.
- Combined with `sase-o2`, the transport both **washes provenance** and
  **pins the wrong project** the first time a `scope: "project"` flag exists.

This is the single most important "how they feel in practice" finding. The
flags work. The inspection surface currently lies about why.

## 3. What SASE flags are, and what they are not

Pete Hodgson's [Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
article still has the right categories. Mapped onto SASE:

| Hodgson category | Typical industry job | SASE equivalent | Fit |
| --- | --- | --- | --- |
| Release toggle | Trunk-based delivery of incomplete work | `wip` | Use only when the incomplete path is *user-reachable* |
| Experiment toggle | A/B, cohorts, percentage rollout | none | Do not build. One user, no cohort, no metrics plane |
| Ops toggle | Kill switch / degrade under load | `ops` | Rare. Needs a written rationale and no flag bead |
| Permissioning toggle | Entitlements, premium, champagne brunch | none | That is a config field or an auth rule |

LaunchDarkly's 2023 use-case catalog
([Feature Flags 101](https://launchdarkly.com/blog/what-are-feature-flags/))
adds canaries, personalization, mobile store review, entitlements, and AI
eval routing. Unleash's
[11 principles](https://docs.getunleash.io/guides/feature-flag-best-practices)
assume a networked control plane that must stay available when the flag
service is not. Almost none of that is SASE's problem. SASE is a locally
installed CLI/TUI with one primary operator, many agent children, and a
strong existing config stack.

The useful Unleash / GitLab ideas that *do* apply, and that SASE already
took:

- kinds carry expected lifetimes (`beta` / `wip` / `sunset` / `ops`)
- flags are inventory with a carrying cost; deletion is the product
- dates must not flip runtime behavior
- both states stay functional while the flag exists
- do not use flags as long-lived settings
  ([GitLab: "Do not use feature flags for long lived settings"](https://docs.gitlab.com/development/feature_flags/))
- prefer static, source-controlled configuration (Hodgson: "Prefer static
  configuration")
- evaluate at a routing boundary and inject the result, do not re-ask the
  global flag system in domain code

GitLab's handbook question is the one SASE agents should ask:

> Why do I need to add a feature flag? If I don't add one, what options do I
> have to control the impact on application reliability and user experience?

([When to use feature flags](https://handbook.gitlab.com/handbook/product-development/how-we-work/product-development-flow/feature-flag-lifecycle/#when-to-use-feature-flags))

SASE's current short memory skips that question and jumps to MUST. That is
the usage bug.

## 4. How to decide whether to add a flag

Use this in order. Stop at the first yes.

```
1. Will users choose this value forever?
     → ordinary config field. Not a flag.

2. Is this process identity, a one-shot bypass, or debug instrumentation?
     (SASE_AGENT, SASE_ARTIFACTS_DIR, SASE_ACE_DEBUG_LEAKS,
      SASE_DISABLE_COMMIT_STOP_HOOK, SASE_TOOL_LOG_FULL, …)
     → environment variable. Not a flag.

3. Is the only problem a public symbol that a later epic phase will consume,
   with no user-reachable behavior yet?
     → `symvision --epic-symbol`. Not a flag.

4. Is a user-reachable path landing before it should be the default?
     → `wip` if it is unfinished; `beta` if it is finished enough to dogfood.

5. Must an old behavior stay reachable while users migrate?
     → `sunset`, named for the *new* behavior, default on once the new
       behavior is the intended default.

6. Do operators need a supported, permanent degradation path?
     → `ops`, with a rationale, no bead. This should be rare enough that
       adding the second `ops` flag requires a written argument.

7. Otherwise do not add a flag.
```

Two extra tests that catch most bad flags:

- **Can you name the losing branch you will delete?** If removal would be
  "just delete the if," the flag is in the right place. If removal would
  require hunting stringly `if flag:` checks through domain logic, the
  toggle is too deep.
- **Would a later worker be able to close the flag bead in one change?**
  If not, the flag is wrapping more than one routing decision. Split it or
  do not add it.

### 4.1 Kind cheat sheet

| Kind | Default `sase flag new` picks | Default boolean | Bead? | Typical life |
| --- | --- | --- | --- | --- |
| `beta` | yes (this is the CLI default) | off | yes | dogfood → flip default → remove old branch |
| `wip` | no | off | yes | land incomplete user-reachable work; graduate to `beta` or remove |
| `sunset` | no | on | yes | keep old branch as escape hatch; delete after both thresholds |
| `ops` | no | off, usually | no; rationale required | permanent or until the operational need dies |

Do not put lifecycle words in the key. `coder_inherits_planner_chat` is a
good name; `coder_inherits_planner_chat_beta` would have to be renamed the
day it graduates.

### 4.2 Scope cheat sheet

- `global` — the flag must resolve the same way in ACE, the CLI, AXE, and
  agent children. This is the only safe choice today.
- `project` — do **not** create one until `sase-o2` is decided. ACE
  disables project-local config, and `SASE_FEATURE_FLAGS` currently pins
  children to the launcher's snapshot. A project flag would silently
  resolve against the wrong project inside every agent ACE launched.

If a behavior genuinely needs different answers globally and per project,
that is two flags after `sase-o2`, not one context-sensitive flag.

## 5. How to use each kind well

### 5.1 Beta — the default and the best first instinct

This is the use that pays for the whole system.

**When:** a user-visible feature is done enough to dogfood and not done
enough to be unconditional. `coder_inherits_planner_chat` is the template.

**How:**

1. `sase flag new <key> -k beta -d "<what the enabled branch does>"`
2. Paste the registry entry, sync the schema, add the typed call at **one**
   routing boundary.
3. Write both-states tests *at that boundary*, not just resolver tests.
   Resolver tests prove the control plane. Call-site tests prove the
   feature.
4. Leave the default off. Enable it in a machine overlay
   (`sase_*.yml`) if ACE is involved; project-local config cannot reach
   ACE.
5. Document the opt-in next to the feature (`docs/xprompt.md` already does
   this for the coder flag).
6. When the enabled branch should become the product: flip the registry
   default in a focused change, keep the off branch as a temporary
   opt-out, then remove flag + losing branch in the change that closes the
   flag bead.

**When not:** the user will want this switch forever (that is config). The
feature is only half-built and must not be reachable at all (that is `wip`,
or `--epic-symbol` if it is not user-reachable).

### 5.2 Sunset — retire a behavior, not a preference

**When:** the new behavior is the intended default, but the old branch must
stay a documented escape hatch for one release window. `prettier_enabled`
is the template for "retire a `SASE_DISABLE_*` alias." A larger sunset is
the three-step deprecation in the lifecycle research: new behavior behind
a disabled flag → flip default on → remove flag, override, and old
implementation together, while the existing
`DEPRECATED` / `UNSUPPORTED` / `RETIRED` config-key ladder owns the *config
surface*.

**How:** name the flag for the desired new behavior, default it on, keep
the old env name working through `_LEGACY_ENV_MAPPINGS` if one exists, and
let `FlagTriage` delete the off branch when both thresholds pass.

**When not:** users should keep the choice. Then it was never a sunset; add
a real setting. Do not invent a parallel deprecation system.

### 5.3 WIP — last resort for user-reachable incomplete work

**When:** a phase of a non-Patch or release-spanning epic lands behavior a
user or agent can actually reach, and that behavior must stay dark. GitLab
uses `wip` the same way: merge the work, hide the feature, change the type
to `beta` when it is ready to dogfood.

**When not:** a Patch-scoped epic that lands once — the unfinished code
never ships. A missing consumer for a new public symbol —
`--epic-symbol`. One flag per epic phase — that multiplies inventory for
no extra routing decision.

A `wip` flag should represent **one coherent routing decision**. Several
independently shippable surfaces may warrant several flags. A single epic
almost never should.

The default 90-day / +2-minor window is too long for most `wip` flags.
Pass `-r YYYY-MM-DD/0.x.0` and aim at the next minor, not two minors out.

### 5.4 Ops — almost never

**When:** there is a supported, permanent degradation path an operator
will actually use during an incident. GitLab's `ops` type is for
Sidekiq-style kill switches and is re-evaluated every 12 months. SASE
should be stricter: if you cannot write a rationale that still makes sense
a year from now, it is a `beta` with a deadline.

Plugin loading (`SASE_DISABLE_PLUGINS` and friends) is the strongest
current `ops` candidate, and even that may belong as several small ops
flags or as ordinary config, not as one `plugins_enabled` mega-switch.
A one-shot hook bypass (`SASE_DISABLE_COMMIT_STOP_HOOK`) and a leak
profiler (`SASE_ACE_DEBUG_LEAKS`) should stay env. They are not product
routes.

## 6. A practical playbook

### 6.1 Create

```bash
sase flag new my_new_behavior -k beta -d "Opt-in: …" -s global
# then paste into registry.py, sync schema, add the call site, add tests
```

Do not hand-edit a registry member. Do not reuse the implementation epic
as the removal bead. `sase flag new` already refuses a duplicate key and
refuses to run outside a SASE-managed checkout.

### 6.2 Toggle

Until a `set` command exists, the supported write paths are:

```yaml
# ~/.config/sase/sase.yml or a machine overlay
feature_flags:
  coder_inherits_planner_chat: true
```

```bash
SASE_FEATURE_FLAGS='{"coder_inherits_planner_chat":true}' sase ace
```

Prefer the YAML overlay for anything you will still want tomorrow. Use the
env form for a single process. Do not put a `global` flag in project-local
`sase/sase.yml`; the resolver rejects it with `scope_violation`.

In tests, use `override_flags(...)`. Do not mutate `os.environ` and hope
the snapshot rebuilds.

### 6.3 Inspect

```bash
sase flag                  # inventory, values, provenance, due state
sase flag show <key>       # layers, bead, call sites
sase doctor -C flags.due
sase doctor -C flags.overrides
sase doctor -C flags.registry
sase bead list --type flag
```

Until the provenance bug in §2.4 is fixed, treat `ENV:SASE_FEATURE_FLAGS`
on a SASE-launched process as "inherited snapshot," not as "someone set
this." Look at the LAYERS block on `sase flag show` to see whether user /
overlay / local actually named the key.

### 6.4 Test

While the flag exists:

- enabled path
- disabled path
- the call site, not only the resolver
- no import-time `current_flags()` (the linter already forbids this)

Do **not** build a Cartesian product across flags. Hodgson and GitLab both
say the same thing: flags rarely interact, and most releases change at
most one flag. Test each flag independently plus the few interactions the
product actually supports.

`tools/check_feature_flags` currently enforces "at least one non-test
reference" (rule 3) and "no import-time resolution" (rule 4). It does
**not** enforce both-states tests. That checklist is printed by
`sase flag new` and then left to review.

### 6.5 Remove

Wait for `FlagTriage`. Do not close a flag bead by hand to "clean up."
The gate's options are the contract:

| Option | Meaning |
| --- | --- |
| **Remove** | choose the winning branch, delete the loser, delete the registry entry, close the bead, in one change |
| **Extend** | still temporary; write a new date **and** release |
| **Keep** | the behavior is permanent; promote to `ops` or a config field, then close the bead |
| **Close** | the flag is already gone, or the bead is intentionally orphaned |

A closed bead with a surviving definition is a hard lint error. A live
bead with no definition is also a hard lint error. Both directions are
load-bearing. Due-ness never changes the boolean; a shipped SASE that
passes its `remove_by` date keeps running.

## 7. Gaps worth closing

These are usage and product gaps, not a redesign.

**Decision guidance is the wrong shape.** Short memory says MUST flag
not-ready user-reaching behavior. Long memory and the design say flag
only a temporary route, and prefer `--epic-symbol` for epic WIP. Agents
read the short memory first.

**Create is a scaffold, not a command.** GitLab's `bin/feature-flag`
writes the YAML definition. SASE's `sase flag new` stops at a paste
block. Schema sync is a second tool. This is the main reason the
remaining env gates have not been migrated.

**There is no first-class toggle.** Writes go through raw YAML or a JSON
env blob. Config Center will show per-flag rows because the schema is
generated, but there is no catalog copy, no "this is a flag, not a
setting" treatment, and no `sase flag set`.

**Inspection lies in child processes.** See §2.4. Related: `sase-o2`
makes the same transport incorrect for project scope.

**`FlagTriage` will fire blind.** `sase-o3`: the human who picks Remove
does not see call sites. `sase flag show` already has them. The gate
preview cannot scan the working tree at render time (byte-compared
contract), so the sites have to be captured into the gate payload.

**Both-states tests are social, not mechanical.** The linter will accept a
flag whose only tests are resolver tests.

**The default lifetime is one size.** 90 days and two minor bumps is
reasonable for a sunset and long for a `wip`. GitLab gives `wip` four
months, `beta` six, `gitlab_com_derisk` two. SASE can be tighter because
releases move faster.

**ACE has no flag chrome.** Beads render ⚑. The running app does not
say "you have one non-default flag." Hodgson's "expose current feature
toggle configuration" is only half-done: CLI yes, TUI no.

**Ad-hoc env gates still outnumber registered flags.** That teaches
agents the old pattern. The next registered flag should probably be a
migration of a remaining *product* gate, not a new experiment, and only
after the decision guide says that gate is actually a flag.

**`sase flag list` is slow in a cold agent.** This session's listing took
~36 seconds, dominated by process startup plus bead-store load. Fine at
two flags, painful as a habit.

## 8. Ranked use cases

Ranked for **SASE as it exists**: a single-operator local CLI/TUI, many
agent children, trunk-based epics, and an existing config stack. Rank is
expected value over the next two releases, not theoretical completeness.

| Rank | Use case | Kind | Why it ranks here | Example |
| ---: | --- | --- | --- | --- |
| 1 | Opt-in beta for a user-visible behavior that is done enough to dogfood | `beta` | Highest leverage. Lets incomplete-but-reachable work ship without becoming the product. Already proven. | `coder_inherits_planner_chat` |
| 2 | Bounded escape hatch while retiring old behavior or an env alias | `sunset` | Second-highest leverage. Makes deprecation a bead with a deadline instead of a comment. Already proven. | `prettier_enabled` / `SASE_DISABLE_PRETTIER` |
| 3 | Dark-launch of user-reachable work on a release-spanning or non-Patch epic | `wip` | Real, but last-resort. `--epic-symbol` covers the common "phase *k* adds a symbol phase *k+1* uses" case. | A half-built ACE pane that must not open yet |
| 4 | Default flip with a temporary opt-out | `beta` → default on → remove | The graduation step for #1. Isolating the flip from unrelated work is the whole point of the flag. | Turning coder-chat inheritance on for everyone, then deleting the off branch |
| 5 | Inventorying a remaining product-shaped env gate | `sunset` or `ops` | Pays down the iceberg that still teaches the old pattern. Only for gates that are actually product routes. | A future `plugins_enabled` *if* plugin loading should stay a supported switch |
| 6 | Permanent operator kill switch | `ops` | Valid, rare. Needs a rationale that will still be true next year. Most "we might want to turn this off" instincts are betas. | Disable a known-expensive subsystem during an incident |
| 7 | Repro and launch metadata ("this run had flag X on") | any | Multiplies the value of every other use. Not a reason to add a flag, a reason to record the ones you have. | ACE repro capture, agent launch metadata |
| 8 | Agent-visible experiment the operator wants to try on one machine | `beta` | Same mechanism as #1, smaller blast radius. Enable via overlay, not project config. | Trying a new prompt-assembly path on `athena` only |
| 9 | Project-local behavior differences | `project` **after `sase-o2`** | The scope field exists for this. Using it today is a silent bug. | A project that must not run prettier |
| 10 | Percentage rollout, A/B, entitlements, remote targeting | — | Do not use SASE flags for this. One user, no cohort, no control plane. | — |

Uses **not** ranked because they are anti-uses:

- long-lived user preferences
- process identity and artifact paths
- one-shot hook bypasses
- debug / leak / stall-watchdog instrumentation
- lint-only incomplete symbols
- wrapping an entire epic in one flag
- wrapping each epic phase in its own flag

## 9. Ranked recommended improvements

Ranked by how much they improve *use of the system that already exists*,
not by how impressive they would look in a flag-product comparison.

| Rank | Improvement | Why it is next | Size-ish |
| ---: | --- | --- | --- |
| 1 | Rewrite the short-term agent instruction into a decision guide | The MUST/last-resort contradiction will either explode inventory or train agents to ignore flags. This is a memory edit, not a feature. Include the §4 tree, the anti-uses, and "reach for `--epic-symbol` before `wip`." | small, needs explicit user permission to edit memory |
| 2 | Make `sase flag new` apply the registry entry and schema sync | GitLab writes the definition; SASE prints a paste block. Applying the edit (and running `tools/sync_feature_flags_schema`) is the highest-leverage command change. Keep the both-states checklist. | medium |
| 3 | Stop encoding default-valued flags into `SASE_FEATURE_FLAGS`, or stop calling that an override | Fixes the provenance lie and the doctor-noise in every agent child. Complementary to `sase-o2`, and useful even if every flag stays `global`. | small |
| 4 | Decide `sase-o2` before the first `scope: "project"` flag | Already filed, already `ready`, size large. Option (a) in the bead — encode only global decisions, let children resolve project flags — is the one that preserves the scope field's meaning. | large (existing bead) |
| 5 | Put call sites on the `FlagTriage` preview (`sase-o3`) | The first due flag is 2026-11-14 / 0.18.0. The human answering Remove should see the branches. Capture sites into the gate payload; do not scan at render time. | medium (existing bead) |
| 6 | Add `sase flag set` / `unset` as a thin Config Center client | Inspection shipped first, correctly. The missing write path is why people will keep using env vars. Must not be required options; key positional, value positional or `--on`/`--off`. | medium |
| 7 | Enforce both-states tests in `tools/check_feature_flags` | The printed checklist is social. A lint rule that each non-ops key is referenced from a test that exercises both values (or that uses `override_flags`) matches the research and GitLab. | medium |
| 8 | Per-kind default lifetimes | `wip`: next minor / ~30 days. `beta`: +2 minor / 90 days (current). `sunset`: +2 minor / 90 days, or the next compatibility boundary. Today every temporary flag gets the sunset window. | small |
| 9 | ACE chrome for non-default flags | One status-bar or doctor-style chip: "⚑ 1 override." Hodgson's "expose current toggle configuration" is half-done. Do not build a flag admin tab. | small |
| 10 | Record non-default flags in agent launch / ACE repro metadata | Makes a beta supportable. "It broke" without "which flags were on" is how flag systems lose trust. | small |
| 11 | Classify and migrate remaining env gates, one at a time | Only the product-shaped ones. Plugin kill switches may become `ops`. Commit-stop, debug leaks, auto-approve, tool-log, stall-watchdog stay env. Do not migrate the daemon `return False`. | series of smalls |
| 12 | Config Center copy that flags are temporary routers | The generated rows already appear. They need kind, bead, and "this is not a setting" help so a flag is not silently promoted by being edited like a preference. | small |
| 13 | Kind-specific `remove_by` on `FlagTriage` Extend | When someone extends, suggest the next window for that kind instead of another blanket 90 days. | small |
| 14 | Share the expiry checker with `_lint-backcompat` | Already designed. One bead-aware linter, two marker sources. Do not build a second one. | medium, when backcompat work starts |
| 15 | Faster `sase flag list` | Lazy bead load, or a `--no-beads` path. Only matters once listing is a habit. | small |
| 16 | Plugin-namespaced flags | Only if a plugin has a temporary route that first-party config must not own. Not needed for the two current flags. | defer |
| 17 | OpenFeature / remote targeting / percentages | Still no consumer. Keep the decision-object shape; do not take the SDK. | defer |

Do not do: a hosted flag service, an "enable all experimental features"
parent flag, flag dependencies, compile-time Cargo features as the primary
mechanism, or time-bombed runtime behavior.

## Recommended way to use them, starting tomorrow

Treat the two existing flags as the style guide.

- Want to dogfood a user-visible change? Add a `beta`, default off, one
  call site, both-states tests, enable it in a machine overlay. That is
  `coder_inherits_planner_chat`.
- Want to delete a `SASE_DISABLE_*` product gate? Add a `sunset`, default
  on, keep the env name as a legacy alias, let `FlagTriage` finish the
  job. That is `prettier_enabled`.
- Want to land unfinished user-reachable UI on master? Consider
  `--epic-symbol` first; add a `wip` only if a user or agent can reach
  the new path. Give it a short `remove_by`.
- Want a setting the user will still be choosing next year? Add a config
  field. Do not add a flag and then "just leave it."
- Want a debug knob? Use an env var. Do not put it in the registry.

Do not add a third flag until the short-term instruction matches that
paragraph. The system is already good at preventing forgotten flags. It
is not yet good at preventing unnecessary ones, and unnecessary flags are
the way this feature stops being useful.

## Sources

**This session, verified against the live tree and bead store:**
`src/sase/feature_flags/` (registry, resolver, snapshot, env, cli, schema,
references, integrity, defaults) ·
`src/sase/file_references.py:513-538` ·
`src/sase/axe/run_agent_exec_plan_accept.py:465-471` ·
`src/sase/ace/tui/data_providers/_settings.py` ·
`src/sase/doctor/checks_flags.py` ·
`src/sase/main/{ace,axe}_handler.py` and `axe/run_agent_runner.py`
(install sites) ·
`tools/check_feature_flags` ·
`src/sase/config/sase.schema.json` `feature_flags` block ·
`docs/{configuration,beads,axe,xprompt}.md` ·
`sase flag list` / `show` on 2026-08-17 ·
`sase bead show` for `sase-nw`, `sase-nx`, `sase-o2`, `sase-o3` ·
`sase/memory/feature_flags.md` and `sase memory read sase_flags.md`

**Prior SASE research (not restated):**
[`feature_flag_architecture.md`](feature_flag_architecture.md) ·
[`feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md`](feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)
·
[`../../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md`](../../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md)

**External:**
Pete Hodgson / Martin Fowler,
[Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
(2017; categories, static config, edge routing, carrying cost) ·
GitLab,
[feature flags in development](https://docs.gitlab.com/development/feature_flags/)
and
[when to use them](https://handbook.gitlab.com/handbook/product-development/how-we-work/product-development-flow/feature-flag-lifecycle/#when-to-use-feature-flags)
(`wip` / `beta` / `ops`; flags are not settings; flag only when needed) ·
Unleash,
[11 best practices](https://docs.getunleash.io/guides/feature-flag-best-practices)
(short-lived, unique names, flags ≠ configuration, DX) ·
LaunchDarkly,
[Feature Flags 101](https://launchdarkly.com/blog/what-are-feature-flags/)
(industry use-case catalog; most items do not apply to SASE) ·
Kubernetes
[deprecation / feature-gate policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
(gates are not long-term APIs; carried from prior research)
