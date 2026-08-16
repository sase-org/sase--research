---
create_time: 2026-08-15
updated_time: 2026-08-15
status: research
---

# Feature Flags in SASE: Implementation Decision Research

## Question

What feature-flag design best supports:

- landing a multi-phase epic without exposing incomplete behavior;
- making unstable or beta functionality opt-in and reversible; and
- retiring deprecated behavior through a bounded compatibility window?

This report evaluates the current SASE architecture at commit `4fae4e7941dc`
(SASE 0.16.0), repository history, and current primary-source guidance. It is a
decision document, not an implementation plan, and it does not change runtime behavior.

There is an earlier, broader report in this directory,
`feature_flag_architecture.md`. The present report independently rechecks its central
claims against the newer checkout and narrows them into an implementation decision.

## Executive conclusion

SASE should implement a **small, typed, local feature-flag facility**. It should not
start with OpenFeature, a hosted flag service, ad hoc environment variables, or Cargo
features.

The design should consist of:

1. a code-owned registry of boolean flags and lifecycle metadata;
2. sparse overrides in SASE's existing layered YAML configuration;
3. one strict JSON environment override for ephemeral runs and subprocess propagation;
4. a pure, deterministic resolver that returns an immutable snapshot with provenance;
5. routing-boundary toggle points rather than flag checks scattered through domain code;
6. CI and `sase doctor` checks that force temporary flags to be reviewed and removed.

Python should collect config layers and environment input. Deterministic definition
validation and resolution belong in `sase-core`, exposed through the normal PyO3 facade,
because other frontends will need identical semantics. The first release should be
boolean-only and local. Targeting, percentages, dependencies, remote updates, and plugin
registries should wait for a demonstrated use case.

## 1. Requirements and non-requirements

### 1.1 Required behavior

The facility needs to support three related but distinct transitions:

| Use case | Initial default | Middle state | End state |
| --- | --- | --- | --- |
| Epic / work in progress | off | developers or the SASE project opt in | remove the flag or graduate it to beta |
| Unstable / beta | off | opt in, then possibly default on with a rollback window | remove the flag or convert it to a permanent setting |
| Deprecation / compatibility removal | old behavior remains | new behavior is opt-in, then default-on with temporary opt-out | remove the flag and old code |

All three require deterministic process-wide decisions, a discoverable owner, tests for
both paths while both exist, and an explicit cleanup obligation.

### 1.2 What SASE does not currently need

SASE is a locally installed CLI/TUI, not a multi-tenant web service. There is no current
requirement for:

- percentage rollout;
- per-request or per-user targeting;
- A/B experiments;
- a network control plane;
- live flag changes during an operation;
- a permanent entitlement or authorization system.

Those needs would justify a larger system later. Building them now would add state,
failure modes, credentials, deployment work, and cross-language SDKs without helping the
three stated uses.

Feature flags also must not replace ordinary settings, permissions, format versions, or
wire compatibility. If a user should retain a choice indefinitely, it is a setting. If
a persisted or cross-process contract changes, it still needs an expand-and-contract
migration independent of the flag.

## 2. Evidence from the SASE codebase

### 2.1 SASE already has a flag-shaped toggle point

`src/sase/ace/tui/data_providers/_settings.py` calls itself a home for environment and
feature-flag checks. Its only function currently returns `False` unconditionally:

```python
def agents_daemon_reads_enabled() -> bool:
    return False
```

That is a useful first integration seam: it centralizes one routing decision, but today
has no registry, lifecycle, override, provenance, or inspection mechanism.

### 2.2 Existing configuration is the right persistent control plane

`src/sase/config/core.py`, `loading.py`, and `layers.py` already provide a cached,
deterministic merge chain:

1. bundled defaults;
2. plugin defaults;
3. `~/.config/sase/sase.yml`;
4. ordinary and selected machine overlays;
5. project-local `sase/sase.yml`.

Later scalar values win. This already gives SASE the useful scopes: user, machine, and
project. The config cache also means flag lookup does not need a new file watcher or
storage subsystem.

There is one important scope rule. `sase ace` calls
`set_include_local_config(False)` because ACE is a cross-project application and must not
inherit one repository's agent-run settings. Therefore a TUI flag cannot depend on a
project-local override. A developer can use a machine overlay or the process environment
for ACE; a flag definition should declare whether project overrides are valid so this
difference is explicit and diagnosable.

### 2.3 Schema support is useful, but runtime validation must be explicit

`src/sase/config/sase.schema.json` is closed at the top level and drives Config Center's
inventory and editors. A new open map of boolean overrides is a natural schema addition.

However, SASE does not validate every loaded layer against the JSON Schema at runtime.
Domain config loaders such as `src/sase/config/file_hooks.py` therefore reject or
diagnose unknown fields themselves. Feature flags need the same discipline: the runtime
resolver must validate values and registry membership rather than relying on Config
Center or editor validation.

The default state should not be duplicated in `default_config.yml`. It belongs to the
code-owned definition so every flag has exactly one authoritative default. YAML should
contain only sparse overrides.

### 2.4 The Rust boundary argues for a split, not a Python-only helper

The project instructions place shared backend and domain decisions in `sase-core` and
keep Python responsible for host I/O and presentation. The current facade pattern uses
`sase.core.rust.require_rust_binding` and JSON-shaped PyO3 wires.

Flag resolution is a pure decision that a CLI, TUI, editor, web frontend, or standalone
Rust process could all need to reproduce. Therefore:

- Python should discover config layers, parse the process environment, and decide the
  applicable project context;
- `sase-core` should validate definitions and overrides, apply precedence and scope,
  and return decisions plus diagnostics;
- Python should expose a typed immutable facade and inject decisions into routing
  points;
- when Rust behavior itself is gated, the resolved decision should be passed across the
  boundary instead of re-reading Python configuration inside Rust.

Definitions may remain application-owned so introducing a Python-only WIP flag does not
require making `sase-core` the release registry for every SASE feature. The core resolver
can accept serialized definitions and overrides.

### 2.5 Prior daemon rollout work shows what to retain and what to avoid

The daemon rollout that was later reverted (`5a65fa4fc`) had a detailed registry of
surfaces, owners, defaults, capabilities, environment variables, parity gates,
performance gates, schema versions, recovery commands, and milestone state. The history
does not show that feature flags caused the revert, but it does show how easily rollout
machinery can become a second product.

Useful ideas to retain are owner, default policy, provenance, recovery awareness, and
tests that constrain default changes. The generic flag facility should not absorb
feature-specific capabilities, performance evidence, milestones, fallback protocols, or
operational commands. Those belong to the feature's own router or readiness logic.

## 3. Findings from established systems

### 3.1 WIP is a first-class and time-bounded use case

[GitLab's development documentation](https://docs.gitlab.com/development/feature_flags/)
defines a `wip` flag specifically for complex features delivered through several merge
requests. Its purpose is to let incomplete code reach the default branch while remaining
hidden. GitLab requires WIP flags to be off by default, owned, explicitly defined, and
transitioned or removed after a bounded period.

This maps directly to SASE epic work. The lesson is not GitLab's exact four-month limit;
it is that an epic flag needs a declared type and cleanup date rather than being an
untracked boolean.

### 3.2 Lifecycle should change the default, then remove the gate

[Kubernetes feature-gate policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
uses a simple lifecycle:

- alpha: disabled by default and opt-in;
- beta: enabled by default but still reversible;
- GA: the gate becomes non-operational;
- after the compatibility window: the gate is removed.

Kubernetes explicitly says feature gates cover a development lifecycle and are not
long-term APIs. This is the right mental model for SASE. A stable feature should not keep
a permanent flag merely because the infrastructure exists.

### 3.3 Cleanup is a core feature, not project hygiene

[GitLab's cleanup guidance](https://docs.gitlab.com/development/feature_flags/controls/)
notes that each surviving flag expands the behavioral state space and reduces confidence
in test coverage. Its prescribed terminal actions are to remove the flag with the new
behavior enabled, convert it into a real setting, or revert an abandoned feature.

[Unleash's current lifecycle model](https://docs.getunleash.io/concepts/feature-flags)
similarly attaches expected lifetimes to flag types and moves flags through cleanup and
archive states. SASE does not need Unleash to adopt the useful part: required lifecycle
metadata, stale diagnostics, and an enforced terminal action.

Dates should never change runtime behavior. They should make CI or `sase doctor` demand
a review. Automatically flipping a released installation based on the wall clock would
be surprising and irreproducible.

### 3.4 OpenFeature supplies useful semantics but too much machinery for v1

The [OpenFeature evaluation specification](https://openfeature.dev/specification/sections/flag-evaluation/)
standardizes typed evaluation and detailed results. Its
[provider specification](https://openfeature.dev/specification/sections/providers/)
separates the call-site API from the backing system, which may be a vendor, remote API,
environment, or local file. Official SDKs exist for both
[Python and Rust](https://openfeature.dev/docs/reference/sdks/).

SASE should copy the useful shape—a typed key, caller-visible default, provider/resolver
seam, value, source, and reason—but not take the SDK dependency yet. OpenFeature does not
provide SASE's registry governance or cleanup policy. Using it now would introduce two
SDKs and provider lifecycle management for a local boolean lookup. A future adapter is
straightforward if remote targeting becomes real.

### 3.5 Compile-time features solve a different problem

[Cargo features](https://doc.rust-lang.org/cargo/reference/features.html) control
conditional compilation and optional dependencies. They are useful when code or
dependencies must be absent from an artifact. They are a poor primary fit here because
they cannot be changed per process, machine, or project after installation and cannot
provide a runtime compatibility escape hatch. They also create more build combinations.

Cargo features remain appropriate for optional dependencies or platform-specific code,
not for SASE's epic, beta, and sunset lifecycle.

## 4. Options evaluated

| Option | Advantages | Main problems | Decision |
| --- | --- | --- | --- |
| Ad hoc `SASE_ENABLE_*` variables | minimal setup | no inventory, owner, expiry, provenance, typo control, or common precedence | reject |
| Plain `feature_flags:` YAML map | reuses config and is easy to prototype | no authoritative definitions or lifecycle; raw strings spread through code | insufficient alone |
| Typed local registry + resolver | deterministic, fast, inspectable, testable, fits current scopes and Rust boundary | small amount of cross-repo infrastructure | choose |
| OpenFeature + local provider | standard API and future provider portability | does not solve governance; duplicate Python/Rust integration and lifecycle overhead | defer |
| Unleash/LaunchDarkly/remote service | targeting, UI, analytics, live rollout | network control plane, credentials, operations, cost, and capabilities SASE does not need | reject for current needs |
| Cargo/build features | removes code and dependencies from the artifact | no runtime opt-in/rollback and more artifact combinations | use only for build concerns |

## 5. Proposed contract

### 5.1 Code-owned definitions

Every first-party flag should have one typed definition. Conceptually:

```python
class FeatureFlag(Enum):
    DAEMON_BACKED_AGENT_READS = "daemon_backed_agent_reads"


@dataclass(frozen=True)
class FeatureFlagDefinition:
    key: FeatureFlag
    kind: Literal["wip", "beta", "sunset", "ops"]
    description: str
    default: bool
    scope: Literal["global", "project"]
    owner: str
    introduced_on: date
    review_on: date | None
    permanent_reason: str | None = None
```

The validation rules should be:

- keys are unique, positive, descriptive `snake_case` names;
- keys describe the behavior, not its stage—avoid suffixes such as `_beta` and `_v2`;
- avoid negative `disable_*` names and double-negative call sites;
- `wip`, `beta`, and `sunset` require an owner and finite `review_on` date;
- `ops` also requires a review date unless `permanent_reason` explains a genuine
  supported kill switch;
- defaults are explicit in the definition and absent from bundled config;
- application call sites use `FeatureFlag`, not arbitrary strings.

The registry should be an inventory, not a dependency graph. V1 should not support
parent flags, implied flags, an "enable all experimental" switch, or milestone gates.

### 5.2 Sparse configuration overrides

Add one top-level schema field:

```yaml
feature_flags:
  daemon_backed_agent_reads: true
```

The schema should accept a mapping of string keys to booleans. The runtime resolver then
validates those keys against the registry and validates scope.

Unknown file-based keys should produce an actionable diagnostic and be ignored. This is
important for downgrades and for stale configuration after a flag is removed. Invalid
file values should likewise be diagnosed and ignored in favor of the next valid lower
layer; `sase doctor -C config.feature_flags` should fail until they are fixed. An invalid
process override, by contrast, should fail immediately because it was an explicit request
to alter that invocation.

Plugin config must not be able to change defaults for first-party flags merely by being
installed. Plugin-owned flags can be added later through a namespaced definition
registry if a concrete need arises.

### 5.3 Flat precedence

Resolve each flag from lowest to highest precedence:

1. definition default;
2. user base config;
3. selected ordinary/machine overlays in existing SASE order;
4. project-local config, only when the definition permits project scope;
5. one process environment map;
6. an explicit in-process override used for tests or a deliberately injected command
   context.

Use one environment variable rather than one variable per flag:

```bash
SASE_FEATURE_FLAGS='{"daemon_backed_agent_reads":true}' sase ace
```

JSON is preferable to a comma grammar because values and exact keys remain unambiguous.
Unknown keys, non-boolean values, duplicate keys, or invalid JSON should fail fast with a
clear message.

The environment form is especially useful for epic work: it enables a feature in one
process without changing portable config, is inherited naturally by subprocesses, and
works for ACE even though ACE excludes project-local YAML.

### 5.4 Immutable decisions with provenance

Resolution should produce details, not just booleans:

```python
@dataclass(frozen=True)
class FeatureFlagDecision:
    key: FeatureFlag
    enabled: bool
    default: bool
    source: Literal["default", "user", "overlay", "project", "env", "runtime"]
    source_detail: str | None
    overridden: bool
```

Resolve all definitions once at a command or application boundary into an immutable
snapshot. Do not read config at every toggle point and do not evaluate flags at module
import time. ACE should keep one snapshot for its lifetime unless an explicit future
feature atomically reloads the whole snapshot.

If a parent launches children that must behave consistently, forward the resolved map in
`SASE_FEATURE_FLAGS`. Do not let a child silently resolve a different project or changed
config file halfway through one logical operation.

Log non-default decisions once at startup and attach them to relevant repro/agent-launch
metadata. Repeated per-evaluation logging would be noisy and unnecessary.

### 5.5 Toggle at routing boundaries

Prefer one decision that selects an implementation:

```python
provider = (
    DaemonAgentsProvider(...)
    if flags.enabled(FeatureFlag.DAEMON_BACKED_AGENT_READS)
    else DirectAgentsProvider(...)
)
```

Downstream code should receive `provider`; it should not repeatedly consult global flag
state. This makes deletion mechanical, limits behavioral combinations, and keeps
feature-specific fallback and compatibility logic outside the generic resolver.

Flags should not gate half of a state mutation unless both paths are independently safe
with the same persisted and wire formats. A feature flag is a router, not a migration
protocol.

## 6. Lifecycle for each intended use

### 6.1 Epic / WIP

1. Add an off-by-default `wip` definition in the first change that adds gated code.
2. Enable it in checked-in project config for project-scoped agent behavior, a machine
   overlay for persistent local dogfooding, or `SASE_FEATURE_FLAGS` for ACE/one-off runs.
3. Keep the default path operational while the epic is incomplete.
4. Before closing the epic, remove the flag and losing branch or deliberately transition
   the definition to `beta` with a new review date.

Use one flag per coherent user-visible routing decision, not automatically one per epic
phase. Independently reversible surfaces may need separate flags.

### 6.2 Unstable / beta

1. Start off by default and document how to opt in.
2. Exercise both paths in focused tests.
3. When ready, flip the registry default in a focused change while retaining a bounded
   opt-out window.
4. Remove the flag and old path after that window. If users should choose forever,
   migrate the choice to ordinary configuration instead.

### 6.3 Deprecation / backward compatibility

Name the flag for the desired new behavior:

1. Release A: add the new behavior behind a default-off `sunset` flag.
2. Release B: make it default-on while retaining a documented temporary opt-out.
3. Release C or the declared compatibility boundary: remove the flag, override, and old
   implementation together.

The default flip should be isolated from unrelated feature work. Persisted data and
mixed-version processes still require ordinary compatibility engineering.

### 6.4 Operational escape hatches

Use `ops` only when operators genuinely need a supported degradation mode. A beta flag
does not become permanent merely because it can serve as a kill switch. Permanent ops
flags need a documented reason, runbook, and normal tests for both states.

## 7. Inspection, testing, and cleanup enforcement

### 7.1 User-facing inspection

The first CLI surface should be read-only:

- `sase feature list` — key, kind, default, effective value, source, scope, owner, and
  review status;
- `sase feature explain <key>` — layer-by-layer provenance and diagnostics;
- `sase doctor -C config.feature_flags` — unknown keys, invalid values, wrong-scope
  overrides, and overdue temporary definitions.

Persistent writes should initially use the existing YAML/Config Center transaction
machinery, which already understands scopes, chezmoi, previews, and conflict protection.
`sase feature set` can be added later as a thin client if repeated use justifies it.

### 7.2 Tests and CI invariants

Automated checks should enforce:

- unique, valid keys and complete required metadata;
- no overdue temporary definition without an intentional review-date update;
- every checked-in override refers to a live definition and valid scope;
- exact precedence and provenance behavior;
- strict process-override parsing;
- focused on/off tests for every live toggle point;
- no remaining references or config overrides when a definition is removed.

Do not test the Cartesian product of all flags. Test each flag against the default
baseline, plus only interactions the product intentionally supports. Banning implicit
flag dependencies in v1 keeps that matrix tractable.

Expiry checks may fail CI or `sase doctor`, but dates must never flip a released
installation's behavior automatically.

## 8. Implementation shape and deferral boundary

A minimal useful implementation has three layers:

1. **Core:** pure definition validation, flat resolution, scope rules, decision details,
   and diagnostics in `sase-core`, exposed through a stable PyO3 wire.
2. **Host facade:** typed first-party definitions, conversion of existing config-layer
   provenance, strict `SASE_FEATURE_FLAGS` parsing, immutable snapshots, and the schema
   addition in SASE.
3. **Governance:** list/explain, doctor checks, CI expiry/reference checks, repro metadata,
   and the first migrated toggle point.

The first proof should migrate `agents_daemon_reads_enabled()`. It is already isolated,
off by default, and has a clear old path. Success means the mechanism can explain why
the flag is on or off, test both routes, propagate a decision, and remove the flag
cleanly—not that it supports every future rollout technique.

Revisit OpenFeature or a remote provider only when SASE has a concrete requirement for
one of the following:

- targeting different users or hosts without editing local configuration;
- percentage rollout or experiments;
- centrally changing several deployed installations in real time;
- a durable audit log and approval workflow for flag mutations;
- multiple products consuming one external flag control plane.

Until then, keep a provider-shaped internal boundary but avoid the dependency and
operational surface.

## Sources

Repository evidence:

- `src/sase/ace/tui/data_providers/_settings.py`
- `src/sase/config/core.py`
- `src/sase/config/loading.py`
- `src/sase/config/layers.py`
- `src/sase/config/file_hooks.py`
- `src/sase/config/sase.schema.json`
- `src/sase/main/ace_handler.py`
- `src/sase/core/rust.py`
- daemon rollout registry before revert commit `5a65fa4fc`
- `sase/repos/research/202608/feature_flag_architecture.md`

External primary sources:

- [GitLab feature flags in development](https://docs.gitlab.com/development/feature_flags/)
- [GitLab feature-flag controls and cleanup](https://docs.gitlab.com/development/feature_flags/controls/)
- [Kubernetes feature-gate lifecycle and deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Unleash feature-flag types and lifecycle](https://docs.getunleash.io/concepts/feature-flags)
- [OpenFeature flag evaluation specification](https://openfeature.dev/specification/sections/flag-evaluation/)
- [OpenFeature provider specification](https://openfeature.dev/specification/sections/providers/)
- [OpenFeature SDK inventory](https://openfeature.dev/docs/reference/sdks/)
- [Cargo features](https://doc.rust-lang.org/cargo/reference/features.html)

## Recommended solution

Implement a **boolean-only, typed, lifecycle-aware local feature-flag system**:

- Add a code-owned registry whose temporary entries require a stable positive key,
  `wip`/`beta`/`sunset`/`ops` kind, description, explicit default, global/project scope,
  owner, introduction date, and review date.
- Put pure validation, precedence, provenance, and diagnostic resolution in `sase-core`;
  let Python continue to own config discovery, environment parsing, and host wiring.
- Add a sparse top-level `feature_flags:` boolean override map. Resolve definition
  default → user config → selected overlays → eligible project config → strict
  `SASE_FEATURE_FLAGS` JSON → explicit in-process/test override.
- Resolve an immutable snapshot once per command/app, record non-default decisions, pass
  the snapshot to child processes when consistency matters, and inject choices at a few
  routing boundaries.
- Ship `sase feature list`, `sase feature explain`, doctor diagnostics, owner/review-date
  CI checks, stale-reference checks, and focused tests for both states.
- Use the lifecycle off → opt-in → default-on with opt-out → removed. Convert a flag to
  ordinary config only when the choice is intentionally permanent.
- Prove the design with `agents_daemon_reads_enabled()`. Defer OpenFeature, remote
  services, targeting, percentages, dependencies, live reload, plugin definitions, and
  convenience mutation commands until a concrete requirement needs them.

This is the smallest design that addresses all three goals while making flag cleanup an
enforced part of completion rather than optional future maintenance.
