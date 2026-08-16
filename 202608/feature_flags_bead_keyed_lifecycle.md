---
create_time: 2026-08-15
updated_time: 2026-08-15
status: research
---

# Feature Flags for SASE: Reuse the Bead-Keyed Lifecycle, Not a New Control Plane

**Research question:** What feature-flag design best supports epic work, unstable/beta
features, and the staged removal of deprecated behavior in SASE?

**Scope:** SASE at `4fae4e794` (version 0.16.0) and linked `sase-core`, both read
directly on 2026-08-15. Every repository claim below was verified against the working
tree at that commit. No runtime behavior was changed.

## Relationship to prior research

Two reports already exist in this repository and were read in full before this one:

- [`202608/feature_flag_architecture.md`](feature_flag_architecture.md) (2026-08-15) —
  a full feature-flag architecture proposing a typed registry, a `feature_flags:` config
  map, and a resolver in `sase-core`.
- [`backcompat_lifecycle_governance/`](../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md)
  (2026-07-11) — a lifecycle-governance design for backward-compatibility shims, keyed
  to removal beads and enforced by a `_lint-backcompat` stage.

This report is an independent re-derivation, not a summary. It agrees with the prior
flag report's *shape* (small, local, boolean, typed, lifecycle-aware) and disagrees with
four of its specific decisions, each on the strength of code read this session. It also
argues that the backcompat report — which has **not** been implemented — already owns
half the problem, and that a flag system must join it rather than fork a second,
competing lifecycle mechanism.

External prior art (Fowler/Hodgson toggle taxonomy, Unleash lifetimes, GitLab `wip`/
`beta` types and cleanup policy, OpenFeature, LaunchDarkly code references) is carried
over from those two reports and was **not** independently re-verified here. Their
conclusions on external practice are sound and are not restated at length.

## Bottom line

Build a **small Python-only feature-flag registry whose expiry is keyed to a bead ID,
whose keys are code-generated into the config JSON Schema, and whose enforcement is a
new `just lint` stage modeled directly on `symvision --epic-symbol`.**

Four specific divergences from the prior architecture report, each verified below:

1. **No `sase-core` work in v1.** Flag resolution is a flat boolean precedence chain
   with no domain complexity, and Rust never resolves a flag under either proposal.
   Putting it in core buys nothing and costs a cross-repo release round trip plus a
   second duplicated-logic-with-parity-tests surface.
2. **Expire flags on beads, not calendar dates.** SASE already ships a proven
   bead-keyed, self-cleaning allowlist (`--epic-symbol`). Release velocity makes date
   windows nearly meaningless here, a point the backcompat report established and the
   flag report did not absorb.
3. **Generate closed schema properties per flag, plus open `additionalProperties`.** An
   open `feature_flags:` map — as proposed — renders in Config Center as a single opaque
   `"map"` leaf with no per-flag provenance. A generated hybrid gets per-flag rows,
   descriptions, defaults, deprecation markers, and provenance from existing Rust code
   with zero Rust changes.
4. **Re-rank the three use cases.** Beta/unstable is the real gap. Deprecation is
   already half-solved by an existing config-deprecation ladder and belongs with the
   backcompat plan. Epic WIP is the *weakest* case, because epics land as one Patch and
   their actual pain is already solved by `--epic-symbol`.

## 1. Re-scoping the three use cases

The three stated uses are not equally well served by a runtime flag in *this* codebase.

| Use case | Existing SASE substrate | Real gap | Flag value |
| --- | --- | --- | --- |
| Unstable / beta features | none — ad-hoc env vars only (§2.3) | opt-in, discoverability, staged default flip | **high** |
| Deprecation / backcompat | `DEPRECATED`/`UNSUPPORTED`/`RETIRED` key ladder + schema `deprecated` (§2.1) | a forcing function, not a switch | **medium** — extend, don't duplicate |
| Epic / multi-change WIP | Patch-scoped epics + `--epic-symbol` (§2.2, §2.4) | mostly lint-shaped, already solved | **low** — do not build first |

This ranking is the main practical difference from the prior report, which treats the
three as coequal and proposes migrating an ACE daemon stub as flag #1.

## 2. Repository evidence

### 2.1 SASE already has a config deprecation ladder

`src/sase/config/layers.py` defines three distinct terminal states for config keys:

```python
UNSUPPORTED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"amd_h1_title", "glossary", "workflows"}
)                                                            # layers.py:23-25

DEPRECATED_TOP_LEVEL_KEYS: dict[str, str] = {                # layers.py:31-43
    "linked_repos": "repos.linked",
    "machine_name": "id.machine_name",
    "tasks": "procs",
    ...                                                      # 8 entries total
}

RETIRED_SDD_SELECTOR_KEYS: frozenset[str] = frozenset(
    {"storage", "version_controlled"}
)                                                            # layers.py:44
```

`ConfigLayer` carries `unsupported_keys`, `deprecated_keys`, and `retired_keys` per
layer (`layers.py:73-79`), and the in-code comments state these are surfaced
non-fatally through `sase config layers` and `sase doctor` "so users get a nudge to
migrate without breaking launched agents with repeated warnings." Separately, the JSON
Schema marks 12 fields `"deprecated": true` — including `linked_repos`,
`sibling_repos`, `tasks`, `machine_name`, `ace.artifacts.commits`, and
`ace.keymaps.gate.activate_control` — and `sase-core` already plumbs both `deprecated`
and `deprecated_replacement` through the Config Center field-model wire
(`config/schema.rs:80-88`).

**Implication.** Use case #3 is not missing a mechanism. Deprecation already has a
declaration form, a three-stage ladder (deprecated → unsupported/retired → gone), and
user-facing diagnostics. What it lacks is exactly what the backcompat report diagnosed:
nothing forces removal. Introducing a parallel `sunset` flag kind with its own registry,
its own diagnostics, and its own expiry rules would give SASE **two** deprecation
systems that disagree. The prior flag report does not mention this ladder at all.

### 2.2 The forcing function already exists, and it is keyed to a bead

`just lint` runs nine stages (`Justfile:259-276`): ruff, mypy, pyscripts, test-waits,
changelog, patch-stitch-terminology, symvision, toobig, keep-sorted. There is **no**
`_lint-backcompat` stage — the 2026-07-11 backcompat design was never implemented.

The symvision stage is the important one:

```make
_lint-symvision *args: _setup
    SASE_SYMVISION_BEAD_STATUS_ONLY=1 BD_COMMAND=tools/sase_bead {{ venv_bin }}/symvision src/sase \
    ...                                                       # Justfile:303-304
```

It passes a bead command into the linter. Per `sase/memory/symvision.md`, the
`--epic-symbol <bead_id>(<symbol>)` allowlist entries "are self-cleaning: Symvision
tells you to drop one when the bead is missing/closed, the symbol is now properly used,
or the symbol no longer exists as a public def."

That is a working, in-production instance of precisely the loop a flag registry needs:

- a temporary allowance is declared in-tree, keyed to a bead;
- the linter queries live bead state on every `just check`;
- closing the bead makes the allowance a hard error, forcing its removal;
- a stale or invalid entry is itself an error.

**This is the single most important finding of this report.** SASE does not need to
invent flag expiry. It needs to apply an existing, proven, bead-keyed pattern to a
second kind of temporary allowance.

Bead-keyed expiry is also strictly better than the `review_on: date` the prior report
recommends, for a reason the backcompat report already established from tag history:
"Tags `v0.2.0`–`v0.10.0` landed between June 13 and July 5, 2026. A policy stated only
as 'keep for two releases' could expire in days." Dates and release counts are poorly
calibrated against SASE's velocity; a bead's *status* is exact. A flag whose epic bead
is closed is unambiguously overdue, whatever the calendar says.

### 2.3 Ad-hoc boolean gates already exist, with inconsistent parsing

`src/sase` references 243 distinct `SASE_*` environment variables. At least ten are
boolean feature gates, and they use three mutually incompatible conventions:

| Gate | Convention | Site |
| --- | --- | --- |
| `SASE_DISABLE_PLUGINS` | any non-empty value | `artifact_providers/_discovery.py:205`, `plugins/inventory.py:145`, `main/plugin_discovery.py:22`, `config/file_hooks.py:373` |
| `SASE_DISABLE_PRETTIER` | any non-empty value | `file_references.py:529,569` |
| `SASE_DISABLE_COMMIT_STOP_HOOK` | any non-empty value | `llm_provider/commit_finalizer.py:155`, `axe/run_agent_runner_bootstrap.py:95` |
| `SASE_GIT_PRE_ALLOCATED` | `== "1"` | `scripts/git_setup.py:35` |
| `SASE_TOOL_LOG_FULL` | `== "1"` | `llm_provider/_tool_call_common.py:66,138` |
| `SASE_CODER_INHERIT_PLANNER_CHAT` | `== "1"` | `axe/run_agent_exec_plan_accept.py:442` |
| `SASE_ACE_DEBUG_LEAKS` | `== "1"`, **at module import time** | `ace/tui/bindings.py:256` |

`SASE_DISABLE_PLUGINS` alone is read at four independent sites with no shared helper.
There are two unrelated private truthy parsers
(`main/plan_inventory_collectors.py:302`, `chops/sdk.py:60`).

Two conclusions. First, the "do nothing / keep using env vars" option is not
hypothetical — it is the status quo, and it has already produced the inconsistency a
registry prevents. Second, `ace/tui/bindings.py:256` evaluates its gate at module scope,
which is exactly the anti-pattern the design must forbid; that alone justifies a
snapshot-at-boundary rule with something to point at.

Also verified: `src/sase/ace/tui/data_providers/_settings.py` contains
`agents_daemon_reads_enabled()` returning an unconditional `False`, as the prior report
states. It is a genuine flag-shaped seam — but it is a *dead* seam for a reverted
feature, which makes it a weak choice for the first real consumer.

### 2.4 Epics land as one Patch, so epic WIP flags are the weakest case

`src/sase/bead/work.py` builds a wave-partitioned plan: phase beads are layered
Kahn-style over the epic's dependency DAG (`work.py:100-105`), and the rendered
multi-prompt targets a shared Patch —

> "When *patch_context* is provided, the first phase segment targets the project ref and
> includes `#pr` to create/own the Patch; later phase segments and the land segment
> target the Patch ref directly." (`work.py:386-389`)

— with a final land agent that waits on every launched phase (`work.py:375`,
`land_waits_on`). `CLAUDE.md` correspondingly requires `just check-full` "before landing
an epic's combined tree."

So an epic does **not** dribble half-finished user-visible behavior onto `master`; it
accumulates on a Patch and lands once. The intermediate states that must stay green are
green on the Patch branch, and the characteristic epic problem — phase *k* adds a public
symbol that only phase *k+1* consumes — is a **lint** problem that `--epic-symbol`
already solves.

This does not make epic flags worthless. A long epic that must be split across releases,
or one whose wave-0 phase lands a user-reachable surface early, still benefits. But it
means epic WIP is a *consequence* of having flags, not the reason to build them, and it
should not drive v1.

### 2.5 An open `feature_flags:` map is opaque to Config Center

The prior report recommends (§5.2) an open map of booleans, and defers per-flag catalog
rendering to a later "Config Center polish" slice. The core code says that deferral is
unnecessary — and that the open map actively forfeits capability.

`sase-core/crates/sase_core/src/config/schema.rs` classifies schema nodes:

```rust
/// Order matters: a node with named `properties` is always a closed object
/// container; otherwise an object-typed node is an open `"map"` ...
fn classify(types: &[String], has_props: bool) -> String {
    if has_props { return "object".to_string(); }
    if types.iter().any(|t| t == "object") { return "map".to_string(); }
    ...
}                                                    # schema.rs:104-117
```

and its module docstring is explicit: "open objects (`additionalProperties` is a schema)
become `"map"` leaves whose user-defined keys are not enumerated" (`schema.rs:5-7`).
`xprompt_aliases` in `sase.schema.json` is exactly this shape today.

So an open `feature_flags` map yields **one** field row. No per-flag description,
default, deprecation marker, or provenance.

The fix costs no Rust work. `classify()` returns `"object"` whenever named `properties`
exist, *regardless of* `additionalProperties`, and `flatten()` then recurses into those
properties (`schema.rs:91-96`). Meanwhile `additional_properties_allowed` is false only
for the literal `additionalProperties: false` (`schema.rs:60-63`). Therefore:

```jsonc
"feature_flags": {
  "type": "object",
  "description": "Opt-in switches for beta and in-progress SASE behavior.",
  "properties": {                      // GENERATED from the registry
    "ace_perf_view_v2": {
      "type": "boolean",
      "default": false,
      "description": "Beta: incremental Perf view refresh. Owner: sase-a1."
    }
  },
  "additionalProperties": { "type": "boolean" }   // tolerate removed/unknown keys
}
```

gets both halves at once: every registered flag becomes a real dotted-path field with
description, default, and full provenance from the existing `config_inventory`
contract, while an unknown key — a flag removed since the user wrote their config, or a
downgraded install — still validates as a boolean instead of hard-failing the closed
top-level schema (`sase.schema.json` is `additionalProperties: false` at the root, 44
properties). The runtime resolver reports unknown keys as a diagnostic, exactly as
`_collect_deprecated_keys` does today.

Generation also settles a question the prior report answers by fiat ("the default is
explicit in the registry and is not duplicated in `default_config.yml`"): with a
generated schema the default is *derived*, so it cannot drift, and Config Center still
shows it. A `keep-sorted`-style check that the generated block matches the registry is a
one-line addition to a lint stage that already exists.

### 2.6 The Rust boundary argues against a core resolver in v1

`CLAUDE.md`'s litmus test — "if a web app, CLI, editor integration, or another frontend
would need the behavior to match the TUI, treat it as core backend logic" — superficially
points flag resolution at `sase-core`. Three verified facts point the other way for v1.

**It is a released, pinned dependency.** `pyproject.toml:46` requires
`sase-core-rs>=0.27.9,<0.28.0`, and history shows the floor ratcheted repeatedly
(0.24.0 → 0.26.4 → 0.26.5 → 0.26.6 → 0.26.10 → 0.27.2 → 0.27.4 → 0.27.5 → 0.27.7 →
0.27.9). Adding or changing a flag definition in Rust means a core change, a core
release, and a floor ratchet in this repo. A mechanism whose entire purpose is to make
in-progress work cheap to gate should not cost a two-repo release round trip. The prior
report concedes this partially by leaving definitions in Python — but then the Rust side
holds only the precedence chain.

**That precedence chain has no domain complexity.** It is "last layer that mentions the
key wins, for a boolean." Compare what core config actually owns: schema flattening,
deep merge, provenance attribution, edit planning, and validation (`config/mod.rs:1-16`).

**Duplication there is already load-bearing.** `config/mod.rs:14-16` states the merge
"mirrors `sase.config.core._deep_merge` exactly so the two can never silently diverge
(see the parity tests)." Adding a Rust resolver adds a second such surface — and under
*both* proposals Rust never actually resolves a flag, because the resolved boolean is
what crosses the binding.

Keep the seam, not the code: define the resolver behind a narrow Python interface so a
future `sase_core::feature_flags` — or a standalone Rust process that genuinely owns a
toggle point — can take it over without touching call sites. Promote it when a second
runtime needs to resolve independently, which is a fact, not a forecast.

## 3. Where this diverges from `feature_flag_architecture.md`

| Question | Prior report | This report | Basis |
| --- | --- | --- | --- |
| Resolver location | `sase_core::feature_flags` in slice 1 | Python only; seam preserved | §2.6 — pinned release cadence, zero domain logic, existing parity-test burden |
| Expiry trigger | `review_on: date` + CI staleness gate | bead ID + live bead status, via a lint stage | §2.2 — `--epic-symbol` precedent; release velocity defeats dates |
| Config schema shape | open `feature_flags` boolean map | generated closed `properties` **plus** open `additionalProperties` | §2.5 — open maps are single opaque `"map"` leaves |
| Deprecation handling | new `sunset` flag kind, own lifecycle | extend the existing `DEPRECATED`/`UNSUPPORTED`/`RETIRED` ladder; flags only for the *behavior* switch | §2.1 — ladder already exists with diagnostics |
| First consumer | `agents_daemon_reads_enabled()` | a live beta feature; then normalize the ad-hoc env gates | §2.3, §2.4 — the daemon stub is dead code for a reverted feature |
| Use-case priority | three coequal cases | beta ≫ deprecation > epic WIP | §2.4 — epics land as one Patch |
| Config Center support | deferred to slice 4 | free in slice 1 | §2.5 |

Where the reports agree, and that agreement is worth stating: boolean-only; no
targeting, percentages, or dependencies; no hosted service; no OpenFeature SDK; typed
keys rather than raw strings; one `SASE_FEATURE_FLAGS` JSON env override; an immutable
snapshot resolved at a process boundary; routing at a feature's edge with the decision
injected downstream; explicit `global` vs `project` scope. That last point is real —
`sase ace` calls `set_include_local_config(False)` (`core.py:101`,
`main/ace_handler.py:162`), so a project-local override is genuinely invisible to ACE.

## 4. Recommended design

### 4.1 The registry

One Python module, dataclass records, keyed by a typed enum:

```python
@dataclass(frozen=True)
class FeatureFlagDefinition:
    key: FeatureFlag
    kind: Literal["beta", "wip", "sunset", "ops"]
    description: str
    default: bool
    scope: Literal["global", "project"]
    bead: str | None        # required for beta/wip/sunset; None only for ops
    rationale: str          # required when bead is None
```

`bead` replaces the prior report's `owner` + `introduced_on` + `review_on` triple. It is
one field, it is exact, it is already how SASE tracks work, and its terminal state is
machine-checkable. Introduction date is recoverable from git; a review date is a guess.

Naming rules carry over unchanged and are worth keeping: stable positive `snake_case`,
no `disable_*` double negatives, no lifecycle words (`beta`, `v2`) baked into keys, since
a graduating flag would otherwise need a rename.

### 4.2 Config, resolution, and the snapshot

Add the generated `feature_flags` object of §2.5 to `sase.schema.json`. Resolution
order, lowest to highest, matching the existing layer chain
(`layers.py:148,170,185,198,218,238` — `default` → `plugin:*` → `user` → `overlay:*` →
`local`):

1. registry default
2. `user` (`~/.config/sase/sase.yml`)
3. `overlay:*` machine overlays, in existing order
4. `local` project config — **only** for `scope: project` flags
5. explicit in-process/test override
6. `SASE_FEATURE_FLAGS` — one JSON object of booleans, strict-parsed

Plugin layers deliberately do **not** get to flip first-party flag defaults; installing
a plugin must not silently change SASE behavior. Strictness is asymmetric on purpose:
malformed or unknown **env** input fails loudly, because an operator typed it this
process; unknown **file** keys warn and are ignored, because a config file outlives the
flag it names.

Resolve one immutable snapshot at the command/app boundary. Never at import time — see
`ace/tui/bindings.py:256` for why. Log the non-default set once at startup and forward
it to child processes through the same `SASE_FEATURE_FLAGS` encoding, so a launched
agent cannot silently resolve a different project's config.

### 4.3 The forcing function: `_lint-flags`

A tenth `just lint` stage, built exactly like `_lint-symvision`, run with
`BD_COMMAND=tools/sase_bead`. Hard-fail when:

1. a `beta`/`wip`/`sunset` definition has no `bead`, or an `ops` definition has no
   `rationale`;
2. a definition's bead is missing from the store, or is **closed while the flag still
   exists** — the `--epic-symbol` rule, and the core of the whole design;
3. the generated schema block does not match the registry;
4. a flag key has no non-test reference (a flag nothing reads is already dead);
5. a `wip`/`beta` flag has no test covering *both* states while both branches exist;
6. a config override in a repo-managed layer names an unregistered key.

Rule 2 is what makes cleanup non-optional: an epic's land agent cannot close the epic
bead while its WIP flag survives, so flag removal becomes part of landing rather than
future hygiene. Note the interaction with `sase bead close`, which refuses to close a
bead with unclosed descendants — flag removal naturally belongs to the phase or land
change that finishes the feature.

Deliberately **not** enforced: any wall-clock rule. Released installs must keep working
after every date, and behavior must never depend on today.

### 4.4 Inspection

`sase config` today offers `init`, `layers`, `mentor-match`, `show`. Add read-only
surfaces first:

- `sase config flags` — key, kind, default, effective value, source layer, scope, bead,
  bead status. A sibling of `sase config layers`, not a new top-level noun.
- `sase doctor` checks: unknown override keys, wrong-scope overrides, closed-bead flags.
  This slots beside the existing deprecated/unsupported/retired key diagnostics rather
  than duplicating them.

Writes go through normal Config Center YAML edit transactions, which already handle
provenance, previews, chezmoi, and conflicts. A `sase config flags set` convenience
wrapper can come later, if ever.

## 5. Lifecycle by use case

**Beta (build this first).** Ship disabled with a `beta` kind and a bead. Both states
tested. Dogfood via a machine overlay — not project-local config, if ACE is involved
(§2.6/`ace_handler.py:162`). Flip the default in a focused change. Remove the flag and
the old branch in the change that closes the bead. If users are meant to choose forever,
it was never a flag: promote it to an ordinary config field.

**Deprecation.** The flag switches *behavior*; the existing ladder handles the *config
surface*. A new behavior lands behind a disabled `sunset` flag; the default flips; the
old key moves into `DEPRECATED_TOP_LEVEL_KEYS` with its replacement and gets
`"deprecated": true` in the schema; finally the flag, the override, and the old
implementation are removed together and the key graduates to `UNSUPPORTED`. Two
mechanisms, one sequence, no duplication. Wire and persisted-format compatibility remain
an independent expand-and-contract problem — a flag cannot make a mixed-version state
change safe.

**Epic / WIP.** Reach for `--epic-symbol` first; it covers the common case of a symbol
awaiting a later phase. Add a `wip` flag only when a phase lands *user-reachable*
behavior that must not be reachable yet — most often when an epic spans a release
boundary. One flag per coherent routing decision, not one per phase. The epic bead is
the flag's bead, which makes rule 2 above automatic.

**Ops.** Only for a genuine supported degradation path, with a written rationale for why
it is permanent. Both states stay in the test matrix forever.

## 6. Implementation slices

1. **Registry + resolver + schema generation + snapshot** (Python only). Include the
   generated `feature_flags` block and the strict `SASE_FEATURE_FLAGS` parser. Config
   Center provenance works from day one via existing Rust (§2.5).
2. **`_lint-flags` stage.** Bead-status enforcement, generation check, both-states test
   check. Ship this *with* slice 1 — the whole argument is that governance is not a
   later slice.
3. **First real consumer:** one live beta feature. Then normalize `SASE_DISABLE_PLUGINS`
   and the `== "1"` gates from §2.3 onto the registry, one at a time, keeping the old
   env names working through the deprecation ladder.
4. **`sase config flags` + `sase doctor` checks.**
5. **Only on demand:** promote the resolver to `sase_core::feature_flags`, add
   plugin-namespaced definitions, or add an OpenFeature adapter. None of these should
   gate v1.

Slices 1–2 are one change. That is the point: a flag system that ships without its
forcing function is how 235 files of unmarked backcompat happened.

## 7. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Flags accumulate anyway | bead-keyed rule 2 makes a closed bead a hard lint failure; there is no "just renew the date" escape |
| Bead store unavailable in CI/sandbox | `_lint-symvision` already solves this with `BD_COMMAND=tools/sase_bead` and `SASE_SYMVISION_BEAD_STATUS_ONLY=1`; reuse the same handshake |
| Two deprecation systems disagree | flags own behavior, the key ladder owns config surface; §5 defines the single sequence |
| Removed flag breaks an older install | generated `properties` + open `additionalProperties: {type: boolean}` keeps unknown keys valid; runtime warns |
| Generated schema drifts from registry | lint rule 3, alongside the existing `keep-sorted` and changelog generation checks |
| ACE resolves differently from the CLI | explicit `global`/`project` scope; project-scope overrides are invisible to ACE by design (`ace_handler.py:162`) |
| Behavioral combinations explode | boolean-only, no dependencies, edge routing, per-flag tests; no Cartesian matrix |
| Import-time evaluation returns | snapshot-at-boundary rule; `ace/tui/bindings.py:256` is the cautionary example and an early migration target |
| It regrows into the reverted daemon rollout registry | feature-specific capability, parity, and fallback gates stay out of the generic flag record |

## Sources

Repository evidence, all read at `4fae4e794` on 2026-08-15:

- `src/sase/config/layers.py` (deprecation ladder :23-44, `ConfigLayer` :69-90, layer
  construction :148-254)
- `src/sase/config/core.py:101` and `src/sase/main/ace_handler.py:158-162`
  (`set_include_local_config`)
- `src/sase/config/sase.schema.json` (closed root, 44 properties, 12 `deprecated: true`
  fields, `xprompt_aliases` open-map precedent)
- `src/sase/bead/work.py` (wave partitioning :100-105, Patch targeting :386-389, land
  agent :375)
- `src/sase/ace/tui/data_providers/_settings.py` (`agents_daemon_reads_enabled`)
- Ad-hoc gates: `artifact_providers/_discovery.py:205`, `plugins/inventory.py:145`,
  `main/plugin_discovery.py:22`, `config/file_hooks.py:373`, `file_references.py:529`,
  `llm_provider/commit_finalizer.py:155`, `scripts/git_setup.py:35`,
  `llm_provider/_tool_call_common.py:66`, `ace/tui/bindings.py:256`
- `Justfile:258-276` (lint stages), `:303-304` (symvision + `BD_COMMAND`), `:584,604`
  (`check`, `check-full`)
- `pyproject.toml:46` and `git log -p -- pyproject.toml` (core floor ratchet history)
- `sase-core`: `crates/sase_core/src/config/mod.rs:1-17`,
  `crates/sase_core/src/config/schema.rs:1-7,55-96,104-117`
- `sase/memory/symvision.md` (`--epic-symbol` semantics), `sase/memory/sase_beads.md`
  (epic/phase/land structure, close semantics)

Prior research (read in full; external citations carried over, not re-verified):

- [`202608/feature_flag_architecture.md`](feature_flag_architecture.md)
- [`backcompat_lifecycle_governance/backcompat_lifecycle_governance.md`](../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md)

## Recommended solution

**Ship a Python-only, boolean-only feature-flag registry whose every temporary entry is
keyed to a bead, whose keys are generated into the config JSON Schema, and whose removal
is enforced by a `_lint-flags` stage modeled on `symvision --epic-symbol` — in a single
change that includes the linter.**

Concretely:

- Registry in Python with `key`, `kind` (`beta`/`wip`/`sunset`/`ops`), `description`,
  `default`, `scope`, and `bead` (or a written `rationale` for permanent `ops`). No
  dates.
- Generate `feature_flags.<key>` schema properties from the registry and keep
  `additionalProperties: {type: boolean}` for tolerance. This yields per-flag Config
  Center rows and provenance with **no `sase-core` change**.
- Resolve registry default → `user` → `overlay:*` → `local` (project-scope flags only) →
  test override → strict `SASE_FEATURE_FLAGS` JSON. One immutable snapshot per
  process, never at import time, forwarded to child agents.
- Enforce with `_lint-flags`: a closed bead with a surviving flag is a hard error. This
  is the whole design; everything else is plumbing.
- Build for **beta features first**. Let deprecation extend the existing
  `DEPRECATED`/`UNSUPPORTED`/`RETIRED` ladder rather than fork it. Reach for
  `--epic-symbol` before a WIP flag.
- Preserve a narrow resolver seam so `sase_core::feature_flags` can claim the logic if
  and when a second runtime must resolve independently — but do not pay that cross-repo
  cost up front.

The difference from a conventional flag system is deliberate: SASE's scarce resource is
not evaluation machinery, it is *deletion*. Keying expiry to beads borrows a forcing
function this repository has already proven, and makes flag removal a precondition for
closing the work that created it.
