---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# SASE Feature Flags: A Field Guide to Using Them and What to Fix First

**Research question:** SASE shipped a feature-flag system a day ago. How much use is it
really, how should it be used, and what should be improved?

**Consolidated from** two independent reports plus this verification pass:

- [`feature_flag_field_guide__a.md`](feature_flag_field_guide__a.md) — agent
  `research.0p.cdx`. External prior art (Hodgson / GitLab / Unleash / LaunchDarkly), the
  add-a-flag decision tree, per-kind playbooks, bead-store awareness.
- [`feature_flag_field_guide__b.md`](feature_flag_field_guide__b.md) — agent
  `research.0p.cld`. The scheduled-deletion reframing, end-to-end loop trace, release-cadence
  measurement, Config Center discovery, removal-tooling gap.
- This report — independent re-verification at `5abf9eb64` on 2026-08-17, resolving six
  disagreements and correcting four claims that are wrong in one report or the other.

Two earlier reports designed this system and are **not** restated:
[`../feature_flag_architecture.md`](../feature_flag_architecture.md) (2026-08-15) and
[`../feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md`](../feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)
(2026-08-16). No runtime code was changed by this research.

## Bottom line

A SASE feature flag is **a scheduled deletion with a switch attached**. That framing — report
B's, and the one this report adopts — is the whole answer to "how much use are they?"

Nearly every part of the shipped machinery exists to force a future deletion to happen: the
mandatory flag bead, the date+release thresholds, the 5-minute `bead_task_triage` chop, the
`FlagTriage` gate whose Remove option *launches a removal agent*, and the lint that errors when
a bead closes while its registry entry survives. The boolean is the cheap part.

This matters more in SASE than in a normal repository because **agents write the code**. Agents
add branches readily and delete them approximately never, and there is no standing reviewer who
remembers that a fallback was meant to be temporary. The registry-plus-bead loop is a deletion
scheduler for a codebase whose authors have no memory across runs.

So the rule is:

> **Use a flag when you want to guarantee a future decision point about code you are knowingly
> leaving in a temporary or duplicated state. Do not use one when you merely want the behavior
> to be configurable** — the Config Center and `sase.yml` already do that, for free, forever.

**How much use is it today?** Two flags, two non-test call sites, zero removals, and zero
`wip`, `ops`, or `project`-scoped flags ever created. Both flag beads were created 2026-08-16
19:31 EDT — about 13 hours before the source reports. There is no track record, so everything
below is a design-and-defect evaluation, explicitly labeled as such. The small inventory is
evidence of **age plus creation friction**, not of a system nobody wants.

**The one thing to fix first** is not a feature. The env transport marks every flag in every
child process as an *override* even when it equals the registry default, so `sase doctor -C
flags` is permanently WARN inside every agent run and OK outside it, with identical values.
That trains everyone to ignore the one check meant to catch a genuinely hidden override — and
its printed remediation cannot be followed by the agent that sees it.

## 1. What shipped, and the honest ratio

Roughly **4,800 lines of machinery behind two booleans**: registry/resolver/snapshot/env
(~1,300), the `FlagTriage` gate (~880), `tools/check_feature_flags` (930), doctor checks (294),
CLI (~740). That ratio looks damning and mostly is not — the lint, gate, doctor, and CLI are
*fixed* costs amortized over every future flag. The marginal cost of flag three is a registry
entry, a schema regen, a call site, and two tests. But it does set the bar: this pays back only
if flags are actually created and, more importantly, actually **removed**.

The live inventory:

| Key | Kind | Default | Scope | Bead | Remove by | Call site |
| --- | --- | --- | --- | --- | --- | --- |
| `coder_inherits_planner_chat` | `beta` | off | global | `sase-nw` (open) | 2026-11-14 / 0.18.0 | `run_agent_exec_plan_accept.py:470` |
| `prettier_enabled` | `sunset` | on | global | `sase-nx` (open) | 2026-11-14 / 0.18.0 | `file_references.py:517` |

These two already exercise the two highest-value kinds, and both have real both-states tests.
They do not exercise `wip`, `ops`, project scope, a default flip, or `FlagTriage` — which has
never fired.

The loop, end to end:

```
sase flag new <key>
  ├─ creates the `flag` removal bead (remove_by = today+90d / current-minor+2)
  └─ prints a registry entry to paste  ← does not apply it, does not sync the schema

     [ registry entry + generated schema block + gated call site + both-states tests ]

  ├─ just check → just _lint-flags → tools/check_feature_flags
  ├─ sase doctor → flags.registry / flags.overrides / flags.due
  └─ sase flag list / show → value, provenance, bead, countdown, call sites

     ... both thresholds pass ...

  chop `bead_task_triage` (every 5 min) → exactly one FlagTriage gate
    ├─ Remove → notes the winner, then LAUNCHES a removal agent
    ├─ Extend → rewrites both thresholds, requires a reason
    ├─ Keep   → launches a promotion agent (→ `ops` or a config field)
    └─ Close  → cancels the bead with a reason
```

The load-bearing word is **LAUNCHES**. Removal is not a reminder a human must act on; it is an
agent launch the gate submits on your behalf. Nothing else in SASE does this: a TODO has no due
date, a task bead has no link to the code that must die, and `symvision`'s epic whitelist
expires against an epic rather than a behavior.

**A genuine strength neither source report checked:** every flag is already a first-class Config
Center field, because the schema block is generated with closed `properties` per key —
description, default, and even `deprecated: true` on the `sunset` flag. You can flip a flag from
ACE today. Nothing documents this anywhere a user would look. Relatedly, unknown keys are
handled well: a typo'd key in `SASE_FEATURE_FLAGS` or config produces
`warning: unknown feature flag 'x' ignored` in `sase flag list` and a doctor WARN, despite the
schema's permissive `additionalProperties`.

## 2. Where the two reports disagreed, and what is actually true

This is the section that justified a third pass. Each item was re-verified at `5abf9eb64`.

**1. `sase flag list` is not slow.** Report A ranked "faster `sase flag list`" as an improvement
on the basis of a ~36-second observation. Measured here: **0.48s warm**. A's number was cold
agent-process startup — venv, imports, bead-store load on first touch — not a property of the
command. *Dropped from the improvement list.*

**2. There is no MUST-vs-"flag only when needed" contradiction.** A ranks "rewrite the agent
instruction" as improvement #1, arguing the short memory's MUST contradicts the design's "flag
only when needed." Reading both notes: the short memory says *"You MUST put a feature flag on
user-reaching behavior before it is ready"*; the canonical `sase_flags.md` says *"a temporary
boolean route for behavior that reaches users before it is ready to become unconditional."*
Those agree, in scope and in wording. **"Flag only when needed" is GitLab's rule, not SASE's** —
A imported an external best practice and then scored the divergence as an internal
contradiction.

The real gap is narrower and still worth fixing: neither note lists the **non-flag off-ramps**
(`symvision --epic-symbol` for a not-yet-user-reachable symbol, an env var for debug
scaffolding, a config field for a forever choice, or simply not landing it yet), and neither
tells a `beta` author to write the decision criterion into the bead. That is a missing-branches
edit, not a contradiction to resolve — real, cheap, and mid-list rather than #1.

**3. Report B did not check the bead store.** B's improvement #3 (`scope: project`) is **already
filed as `sase-o2`** (READY, size large), which names three concrete options — (a) encode only
global decisions and let the child re-resolve, (b) carry launcher project identity alongside the
snapshot, (c) declare the pin intentional and reject `scope:"project"` at registration. B's
proposed fix maps onto (a)/(c). B also never mentions **`sase-o3`** (the `FlagTriage` preview
omits call sites), which is the filed fix that most directly serves B's own argument about
removal being under-supported. Do not re-file either.

**4. B overstates the `ops` opportunity.** B ranks `ops` as use case #3 and "the largest untapped
use case by volume." The repo has 296 distinct `SASE_*` env vars, ~27 of them disable/auto/debug
shaped. Filtering honestly: `SASE_TUI_*` (7) and `SASE_ACE_DEBUG_LEAKS` are dev scaffolding;
`SASE_AGENT_AUTO_*` (6) are harness knobs; `SASE_DISABLE_CODE_SWAP_LOCK` and
`SASE_DISABLE_IMPORT_PRELOAD` are internal performance switches. Real `ops` candidates number
**one to three**, headed by `SASE_DISABLE_PLUGINS` (7 non-test call sites, a genuine product
route). A's "almost never" is closer to right, but A is too dismissive: zero is also wrong, and
one good `ops` flag consolidates five truthiness conventions into one.

**5. B is wrong that `SASE_DISABLE_COMMIT_STOP_HOOK` should become an `ops` flag.** It is a
per-process bootstrap bypass, checked at `run_agent_runner_bootstrap.py:95` *before*
`sase.llm_provider` is imported. Making it a flag would require import-time flag resolution,
which lint rule 4 explicitly forbids — and it would additionally require the per-launch override
that does not exist. A is right: it stays env.

**6. B's schema-sync papercut is lower severity than stated.** B says the author "has to go find
the tool." The lint failure names it verbatim: *"Run tools/sync_feature_flags_schema --write to
update it."* And `just check` already runs `_lint-flags`, so drift is caught before landing. It
costs one wasted lint cycle, not a hunt. Still worth adding to the scaffold; not worth ranking
highly.

**Where they agreed, and both were right:** the env-override provenance bug, the absent
`set`/`unset`/`rm` commands, `new` printing a paste block, both-states testing being a printed
checklist rather than a lint rule, and `wip` being the weakest kind.

## 3. Verified defects

**3.1 The env transport reports inherited defaults as overrides.** `apply_feature_flags_env`
encodes *every* resolved flag, and `_apply_values` sets `overridden=True` unconditionally for
anything an env layer mentions. Reproduced:

```
$ sase flag show prettier_enabled          # inside an agent shell
  effective: on   source: ENV:SASE_FEATURE_FLAGS   overridden: yes
  LAYERS: default on (registry) · user — · overlay — · local — · env on

$ env -u SASE_FEATURE_FLAGS sase flag show prettier_enabled
  effective: on   source: default                  overridden: no
```

`sase doctor -C flags` is `OK: 2, WARN: 1` inside an agent and `OK: 3, WARN: 0` outside, with
identical values and no layer having named the key.

**A detail neither source report drew out:** the warning's own remediation text reads *"Inspect
`sase flag list` and clear inherited SASE_FEATURE_FLAGS."* An agent **cannot** clear it — SASE
set it, at one of the three `install_process_feature_flags()` boundaries. The check fires
permanently in the one context where its instruction is impossible to follow. That is how a
diagnostic becomes furniture.

**3.2 `scope: project` is defeated by the pinned snapshot.** ACE deliberately resolves flags
with project-local config off, then exports that snapshot; env sits at the *top* of precedence
in the child, above the agent's own project config. So a project-scoped flag set in a project's
`sase/sase.yml` is silently overridden in exactly the process ACE's own comment says it was
meant for. Latent today (both flags are `global`, and the resolver rejects local overrides of
global flags outright with `scope_violation`). Filed as **`sase-o2`**.

**3.3 The release threshold is decorative at SASE's cadence.** A flag is due only when *both*
thresholds pass. Defaults are today+90d and current-minor+2. Measured: v0.8.0 (2026-07-02) →
v0.16.0 (2026-08-07) is **8 minors in 36 days**, ~1 per 4.5 days. Even using the slowest recent
gap — no minor tagged in the 10 days since v0.16.0 — `+2 minors` lands ~20 days out against a
90-day date. The date binds; the release threshold contributes only the impression of a second
gate. This is a calibration bug, not a correctness bug: the conjunction is the safe direction
and cannot fire early.

**3.4 The removal half has almost no tooling — and the brief is two sentences.** Nothing
scaffolds removal, which is the half the entire design exists to force and the half that will be
executed repeatedly by agents starting from zero context. Worse, the text those agents start
from is the entire briefing (`_flag_gate_actions.py`):

> This is a feature-flag removal bead for the `<key>` flag. The `<winner>` branch wins: delete
> the losing branch and the registry entry in the same change that closes this bead.

It never mentions the enum member, `just sync-feature-flags-schema`, collapsing the call sites,
or deleting the now-dead both-states tests. **This string is the cheapest high-value fix in the
whole report** — it is where every removal actually begins, and enriching it captures most of the
value of a full `sase flag rm` at a fraction of the cost.

**3.5 Both-states coverage is social, not mechanical.** Lint rule 3 requires only that each key
have at least one *non-test* reference. Both current flags happen to be covered, but nothing
keeps it that way — and the losing branch of an untested flag is precisely the code a removal
agent must confidently delete 90 days later.

**3.6 `sase flag new` is a scaffold, not a command.** It creates the bead and prints a paste
block; the author still edits `registry.py` by hand, runs the schema sync, and wires the call
site. GitLab's `bin/feature-flag` writes the definition. This is the single biggest reason the
remaining env gates have not migrated.

**3.7 A papercut neither report caught:** `sase flag --help` advertises
`sase flag show plugins_enabled` as a built-in example — for a flag **that does not exist**.
`plugins_enabled` was the recommended first consumer in the design research and was never
created. Half bug, half signpost: the CLI is telling you which flag to create next.

**3.8 Plugins cannot own flags.** The registry is a closed `StrEnum` in the SASE tree, `flag new`
refuses to run outside a SASE-managed checkout, and `plugin:*` config layers are skipped by the
resolver by design. Five plugin repos have no flag path. No consumer yet; defer deliberately.

## 4. How to decide whether to add a flag

Stop at the first yes.

```
1. Will users choose this value forever?           → config field. Not a flag.
2. Is it process identity, a one-shot bypass,
   or debug instrumentation?                       → env var. Not a flag.
3. Is it only a public symbol a later epic phase
   will consume, not user-reachable yet?           → symvision --epic-symbol. Not a flag.
4. Could you simply not land it yet?               → don't land it. Not a flag.
5. Is a user-reachable path landing before it
   should be the default?                          → `wip` if unfinished, `beta` if dogfoodable.
6. Must an old behavior stay reachable while
   users migrate?                                  → `sunset`, named for the NEW behavior.
7. Do operators need a supported, permanent
   degradation path?                               → `ops`, with a rationale, no bead. Rare.
8. Otherwise                                       → no flag.
```

Two tests that catch most bad flags:

- **Can you name the losing branch you will delete?** If removal is "just delete the if," the
  flag is at the right boundary. If it means hunting `if flag:` through domain logic, the toggle
  is too deep.
- **Could a later worker close the flag bead in one change?** If not, the flag wraps more than
  one routing decision. Split it or skip it.

| Kind | Default bool | Bead? | Typical life |
| --- | --- | --- | --- |
| `beta` (CLI default) | off | yes | dogfood → flip default → delete old branch |
| `wip` | off | yes | land dark, graduate to `beta` or remove. Use a short `remove_by`. |
| `sunset` | on | yes | keep old branch as escape hatch, delete after both thresholds |
| `ops` | usually off | **no** — rationale required | permanent, or until the operational need dies |

Do not put lifecycle words in the key: `coder_inherits_planner_chat` is right;
`..._beta` would need renaming the day it graduates. Do not create a `scope: "project"` flag
until `sase-o2` is decided. Until `sase flag set` exists, write flags via `feature_flags:` in
`~/.config/sase/sase.yml` or a machine overlay (project-local config cannot reach ACE), use
`SASE_FEATURE_FLAGS='{"key":true}'` for one process, and `override_flags(...)` in tests.

## 5. Ranked use cases

Ranked by expected value in SASE specifically — one operator, agent-authored changes, trunk
landing, and a strong existing config stack.

| Rank | Use case | Kind | Why here |
| ---: | --- | --- | --- |
| 1 | **Retire a behavior or env alias you intend to delete** | `sunset` | The flagship. The scheduled deletion *is* the value, and the gate decision is nearly automatic — the new behavior already won, so Remove just deletes the old branch. Lowest variance of any case. Proven by `prettier_enabled`. Tell-tale: you catch yourself writing "we can remove this once X." That sentence is a flag bead. |
| 2 | **Dogfood a user-visible change whose answer is empirical** | `beta` | Highest ceiling, higher variance. Use it when living with the change is the only way to settle it — not when you are hedging. **Write the decision criterion into the bead**, or `FlagTriage` arrives, the honest answer is "I never compared," and you press Extend. Extend is how flag debt is born. Currently rate-limited by the missing per-launch override (improvement 10). Proven by `coder_inherits_planner_chat`. |
| 3 | **Flip a default with a temporary opt-out** | `beta` → default on → remove | The graduation step for #2, and the reason the flag existed: it isolates the flip from unrelated work, then deletes the opt-out on a deadline. Never exercised yet. |
| 4 | **Kill switch for an expensive or failure-prone dependency** | `ops` | Real and currently at zero, but worth **one or two flags, not a program**. Start with `plugins_enabled` — the CLI help already advertises it. Buys one truthiness convention instead of five, real provenance, doctor coverage, and a schema-documented switch. |
| 5 | **Risky replacement with a retained fallback** | `sunset` | Case 1 wearing different clothes, which is a good sign about the design. Only when the fallback is real and tested; otherwise it is permanent dual maintenance. |
| 6 | **Epic seam across multiple landings** | `wip` | Weakest real case. The classic long-running-branch motivation is thin here because an epic's phases converge into a combined tree landed as a unit, so intermediate states rarely reach you. Earns its cost only when a phase lands a user-reaching surface ahead of the phases that finish it, or the epic spans releases. Reach for `--epic-symbol` first. One flag per *coherent routing decision*, never one per phase. |
| 7 | **Repro and launch metadata** | any | Not a reason to add a flag — a reason to record the ones you have. "It broke" without "which flags were on" is how a flag system loses trust. |
| 8 | **Project-local behavior differences** | `project` | The scope field exists for this and does not work. Blocked on `sase-o2`. |

**Anti-uses** — do not reach for a flag for: permanent user preferences (config field) · debug,
trace, and leak instrumentation (env var) · process identity and one-shot bypasses (env var) ·
deprecating a config key or CLI surface that only needs to keep *parsing* (the schema's
`deprecated` ladder owns that; use a flag only when both behaviors must *execute*) ·
wire/schema/state migration (expand-and-contract) · anything Rust core must decide alone ·
percentage rollout, A/B, cohorts, entitlements, remote targeting (one user, no cohort, no
control plane) · one flag wrapping a whole epic, or one per epic phase.

## 6. Ranked recommended improvements

Ranked by (value × confidence) ÷ cost. **Filed** marks work that already exists as a bead — do
not re-file it. Nothing else below is filed; neither researcher created beads.

| Rank | Improvement | Size | Why here |
| ---: | --- | --- | --- |
| 1 | **Stop reporting inherited defaults as overrides** | small | Unanimous across all three passes and independently reproduced. Minimal fix: in `_apply_values`, set `overridden = (value != definition.default)`. Better: have doctor compare the pinned env against what *this* process would resolve without it, which also catches a stale env pinning a default while local config has moved. Keep the `ENV` source label — the bug is the override *claim*. Fix the remediation text too: it currently tells agents to do something only ACE can do. |
| 2 | **Enrich the `FlagTriage` removal brief** | xsmall | The two-sentence brief is the entire context a removal agent starts from. Add the enum member, `just sync-feature-flags-schema`, "collapse every call site," and "delete the both-states tests for the losing branch." Highest value per byte in this report. |
| 3 | **Land `sase-o3` — call sites in the gate preview** | medium · **filed** | The human answering "should the enabled branch win?" cannot currently see how many branches exist or where. `find_flag_call_sites` already exists and `sase flag show` already renders it; capture the list into the gate payload at creation time (the preview is byte-compared, so it cannot scan a mutable tree at render time). Directly serves #2. |
| 4 | **Make `sase flag new` apply the registry entry and sync the schema** | medium | GitLab writes the definition; SASE prints a paste block. This is the friction that keeps agents reaching for `os.environ.get("SASE_…")`. Keep the both-states checklist in the output. |
| 5 | **Enforce both-states coverage in the linter** | small | Add a rule: every non-`ops` key must appear in the test tree under both `True` and `False` — detectable from `override_flags(key=…)` literals and `feature_flags` layer dicts. Closes the gap between stated policy and enforcement, and protects the exact code a removal agent must delete later. |
| 6 | **Add the non-flag off-ramps to the memory notes** | small · *needs explicit user permission* | Not the contradiction fix report A proposed (see §2.2). Add to `sase/memory/feature_flags.md` and `sase_flags.md`: `--epic-symbol` before `wip`, env vars for debug scaffolding, config fields for forever choices, "or don't land it yet" — plus "a flag's primary product is its scheduled deletion" and "a `beta` bead must carry the criterion that will settle it." |
| 7 | **Create `plugins_enabled` as the first `ops` flag** | small | `SASE_DISABLE_PLUGINS` has 7 non-test call sites and is a genuine product route. Retain the old name via `_LEGACY_ENV_MAPPINGS` exactly as `SASE_DISABLE_PRETTIER` did — that migration is already proven. Bonus: it makes `sase flag --help`'s own example real (§3.7). Leave the per-plugin `SASE_DISABLE_PLUGIN_*` family alone; "which plugins load" is a config question, not a kill switch. |
| 8 | **Recalibrate `remove_by_release`** | small | Derive the default release threshold from observed tag cadence, or make the date the sole default and let authors add a release constraint deliberately. A few lines in `defaults.py`; `flag_due.py` semantics need not change. |
| 9 | **Decide `sase-o2` before the first project-scoped flag** | large · **filed** | Option (a) — encode only `global` decisions and let children resolve project-scoped flags themselves — is the one that preserves the scope field's meaning. Retiring `scope` is a legitimate outcome; zero flags use it. A documented capability that silently does the opposite of its documentation is worse than an absent one. |
| 10 | **Per-launch flag override** | medium | A launch-path option and matching xprompt directive injecting `SASE_FEATURE_FLAGS` for one agent (`extra_env` already threads through the launcher). Turns `beta` from "flip it and hope I remember how the other way felt" into running the same task both ways. This is what makes the gate's "which branch wins?" answerable with evidence instead of vibes — a SASE-specific capability no general-purpose flag system offers. Additive, not repair, hence below the fixes. |
| 11 | **`sase flag set` / `unset`, and document the Config Center path** | small–medium | Inspection shipped first, correctly; the missing write path is why people reach for env vars. Also: `flag list`/`show` should say *how* to change a value, since every flag is already an editable Config Center field and nothing says so. |
| 12 | **Per-kind default lifetimes** | small | Today every temporary flag gets the `sunset` window. `wip` should be much shorter — next minor, ~30 days. Feed the same per-kind window into the gate's Extend suggestion. |
| 13 | **Migrate remaining product-shaped env gates, one at a time** | series of smalls | Only genuine product routes. Explicitly leave as env: `SASE_TUI_*`, `SASE_ACE_DEBUG_LEAKS` (dev scaffolding), `SASE_AGENT_AUTO_*` (harness), and `SASE_DISABLE_COMMIT_STOP_HOOK` (bootstrap-ordering; see §2.5). |
| 14 | **ACE chrome for non-default flags** | small | One status chip: "⚑ 1 override." **Strictly after #1** — built today it would permanently display the provenance lie. Do not build a flag admin tab. |
| 15 | **Add the schema-sync step to the `new` scaffold** | xsmall | Real but minor: the lint already names the fix and `just check` already catches drift. One wasted cycle per author. |
| 16 | **Plugin-owned flags · Rust-core resolver · OpenFeature** | large | Defer, deliberately. All three are real gaps with no consumer. Building any speculatively is how a small mechanism becomes the reverted rollout registry the original research warned about. The trigger for promoting the resolver is a standalone Rust process or non-Python frontend needing to resolve independently. |

**Do not build:** a hosted flag service, an "enable all experimental features" parent flag, flag
dependencies, compile-time Cargo features as the primary mechanism, or any runtime behavior that
changes when a date passes. The last one is already a deliberate safety property — a released
SASE that passes its `remove_by` date keeps running, because expiry drives diagnostics only.

## 7. What to do differently starting tomorrow

- Retiring something? `sunset`, default on, keep the old env name as a legacy alias, let
  `FlagTriage` finish it. That is `prettier_enabled`.
- Dogfooding something? `beta`, default off, one call site, both-states tests, enabled from the
  Config Center or a machine overlay — **and write into the bead what will settle it.**
- Landing unfinished work? Try `--epic-symbol` first. `wip` only if a user or agent can actually
  reach the new path, and give it a short `remove_by`.
- Want a knob forever? Config field. Want a debug switch? Env var. Neither is a flag.

The system is already good at preventing *forgotten* flags. It is not yet good at preventing
*unnecessary* ones, and it is weakest at the moment it matters most — the removal. Improvements
1–3 are all in that gap, and together cost less than a day.

## Sources

**Verified this pass at `5abf9eb64`** (SASE 0.16.0), 2026-08-17: `src/sase/feature_flags/`
(registry, resolver, snapshot, env, defaults, integrity, references, schema, cli, cli_new) ·
`src/sase/bead/_flag_gate_actions.py`, `flag_due.py` · `tools/check_feature_flags:240-260` ·
`src/sase/config/sase.schema.json` `feature_flags` block · `Justfile:288-296,609,630` ·
`src/sase/axe/run_agent_runner_bootstrap.py:95` · `src/sase/llm_provider/commit_finalizer.py:155` ·
`sase flag list` / `show` / `--help`, `sase doctor -C flags` with and without
`SASE_FEATURE_FLAGS` · `sase bead show sase-o2 sase-o3` · `sase bead list --type flag` ·
`sase memory read sase_flags.md` and `sase/memory/feature_flags.md` · git tags v0.8.0–v0.16.0 ·
timing of `sase flag list` · `SASE_*` env-var census across `src/sase`.

**Source reports:** [`feature_flag_field_guide__a.md`](feature_flag_field_guide__a.md) ·
[`feature_flag_field_guide__b.md`](feature_flag_field_guide__b.md)

**Prior SASE research (not restated):**
[`../feature_flag_architecture.md`](../feature_flag_architecture.md) ·
[`../feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md`](../feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md)

**External** (via report A, spot-checked): Pete Hodgson,
[Feature Toggles](https://martinfowler.com/articles/feature-toggles.html) — categories, prefer
static configuration, evaluate at a routing boundary, carrying cost · GitLab,
[feature flags in development](https://docs.gitlab.com/development/feature_flags/) and
[when to use them](https://handbook.gitlab.com/handbook/product-development/how-we-work/product-development-flow/feature-flag-lifecycle/#when-to-use-feature-flags)
— the `wip`/`beta`/`ops` kinds SASE adopted; flags are not settings · Unleash,
[11 best practices](https://docs.getunleash.io/guides/feature-flag-best-practices) — short-lived,
flags ≠ configuration · LaunchDarkly,
[Feature Flags 101](https://launchdarkly.com/blog/what-are-feature-flags/) — industry use-case
catalog, most of which does not transfer to a single-operator local tool.
