---
create_time: 2026-08-15
updated_time: 2026-08-15
status: research
---

# Feature Flags for SASE: A Small, Typed, Lifecycle-Aware Control Plane

**Research question:** What feature-flag design best supports multi-change epic work,
unstable or beta features, and the staged removal of deprecated behavior in SASE?

**Scope:** SASE at `f86373aeddab` (version 0.16.0), `sase-core` at `7acf60737880`,
and the reverted `sase-3e` daemon rollout preserved in SASE history. External sources
were checked on 2026-08-15. This is architecture research, not an implementation plan;
no runtime behavior was changed.

## Bottom line

SASE should build a **small in-repository feature-flag system**, not adopt a hosted flag
service and not begin with the OpenFeature SDK.

The system should have three deliberately separate pieces:

1. a code-owned, typed registry describing every flag and its cleanup obligation;
2. boolean overrides carried by SASE's existing user, machine-overlay, and project-local
   config layers, plus one strict process-level environment override;
3. an immutable resolved snapshot that is created at a command or app boundary and
   injected at a small number of routing points.

Deterministic resolution and validation belong in `sase-core`; Python should continue to
own config/plugin discovery and file I/O, just as it does for Config Center today. The
first version should support boolean flags only, no targeting, percentages, dependencies,
or live remote updates. Mandatory metadata and CI checks should make flags expire as a
matter of engineering policy, without ever changing behavior automatically based on the
clock.

This is enough for all three requested uses, while leaving a clean provider seam if SASE
eventually needs OpenFeature or a remote control plane.

## 1. What SASE actually needs

The three stated uses are related, but they have different default directions and
lifecycle expectations.

| Use | Initial state | Typical transition | Terminal action |
| --- | --- | --- | --- |
| Multi-change epic / work in progress | off | enable for the SASE project or a development machine | remove the flag and the old/unreachable branch |
| Unstable or beta feature | off | opt in, then possibly default on | graduate to ordinary behavior or replace with a permanent setting |
| Deprecation / backward compatibility | old behavior retained | opt into new behavior, flip the default, retain a bounded escape hatch | remove the flag and old behavior |
| Operational rollback, when genuinely needed | new behavior on | turn off during an incident | remove after confidence, or intentionally classify as a permanent kill switch |

These are static routing decisions for a locally installed CLI/TUI. SASE currently has
no need for per-request cohorts, user segmentation, percentage rollout, A/B experiments,
or a network control plane. Those requirements would materially change the answer, but
building for them now would turn a small local mechanism into a distributed system.

Feature flags also should not become a synonym for settings. A preference that users are
expected to control indefinitely belongs in the normal config schema. A permission or
security decision belongs in authorization. A wire, file-format, or database migration
still needs versioning and expand-and-contract compatibility; a flag cannot make mixed
versions safe.

## 2. Repository evidence

### 2.1 There is already one hard-coded flag-shaped seam

`src/sase/ace/tui/data_providers/_settings.py` describes itself as containing
"feature-flag checks," but its only function currently returns `False` unconditionally:

```python
def agents_daemon_reads_enabled() -> bool:
    return False
```

This is a good first migration target. It is already a centralized decision point, but
it has no discoverability, configuration provenance, lifecycle, or common evaluator.

### 2.2 SASE already has the right local control plane

`sase.config.core` already loads and caches a deterministic config stack:

1. bundled defaults;
2. plugin defaults;
3. `~/.config/sase/sase.yml`;
4. selected `sase_*.yml` machine/ordinary overlays;
5. the current project's `sase/sase.yml`.

Nested maps deep-merge, later scalar values win, and Config Center already exposes
source provenance and conflict-safe edits. Reusing this machinery gives feature flags
machine and project scope without inventing another persistent store.

One caveat must be explicit: `sase ace` disables project-local config because ACE is a
cross-project application. A flag used by ACE therefore cannot quietly depend on a
project-local override. The registry should declare whether a flag is `global` or
`project`; a behavior that genuinely needs different global and project decisions should
use two flags rather than one context-sensitive flag.

### 2.3 The schema and Config Center can host overrides, but not governance alone

`src/sase/config/sase.schema.json` is a closed top-level schema, and the Config Center's
deterministic field model, merge, provenance, validation, and edit planning are already
owned by `sase-core`. Adding an open `feature_flags` map of booleans is mechanically
compatible with that system.

A config map alone is insufficient, however. It cannot say who owns a flag, why it
exists, when it should be reviewed, which state is the safe default, or whether an
override names a flag that has already been removed. Those facts must live in a code-owned
registry, not in user configuration.

### 2.4 SASE's Rust boundary favors a split implementation

The sibling core's `sase_core::config` module already establishes the intended boundary:
Python discovers layers, reads files, and parses YAML; Rust owns deterministic merge,
provenance, validation, and logical decisions exposed over JSON-shaped wires.

Feature-flag resolution is domain behavior that a CLI, TUI, web frontend, editor, or
plugin host could all need to agree on. The generic resolver and diagnostics therefore
belong in `sase-core`. Application-owned flag definitions can still live alongside the
toggle points so that adding a Python-only epic flag does not require publishing a new
Rust crate merely to add a name. The resolved decision—not duplicate evaluation
logic—should cross the binding when Rust behavior is gated.

### 2.5 The reverted daemon rollout is a valuable warning, not proof against flags

Before commit `5a65fa4fc` reverted the daemon work, SASE had a sophisticated rollout
system:

- a registry of read, write, scheduler, provider-host, mobile, and recovery surfaces;
- global, milestone, and per-surface switches;
- config keys plus several overlapping environment overrides;
- capability, contract, parity, performance, recovery, and documentation gates;
- user-facing rollout diagnostics and direct fallbacks.

That design had strong ideas: explicit ownership, default policy, recovery posture,
provenance, and tests that prevented premature default changes. It also demonstrates how
quickly rollout controls become a product of their own. The registry intertwined feature
selection with daemon capabilities, milestones, fallback logic, operational commands,
and dozens of knobs.

The daemon was reverted as a whole; repository history does **not** establish that flags
caused the revert. The useful lesson is narrower: the generic flag layer should remain
small, flat, and independent of feature-specific readiness machinery. A feature can have
its own parity or performance gates without making those concepts part of every flag
evaluation.

## 3. External findings

### 3.1 Flag type and lifetime matter

Pete Hodgson's foundational [Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
article separates release, experiment, operational, and permission toggles, primarily by
how dynamic they are and how long they should live. It also recommends separating
decision logic from toggle points and preferring static configuration when static routing
is sufficient. That maps closely to SASE: evaluate once near the application boundary,
then select or inject an implementation.

[Unleash's current model](https://docs.getunleash.io/concepts/feature-flags) adds two
ideas worth adopting without adopting the product: flag types carry expected lifetimes,
and overdue flags become stale. Its current defaults distinguish release (40 days),
operational (7 days), sunset (90 days), and permanent kill-switch/permission flags. The
exact numbers need not be copied, but a required review date and a distinct sunset type
directly address SASE's three goals.

[GitLab's development guidance](https://docs.gitlab.com/development/feature_flags/)
provides a particularly relevant `wip` type for features delivered across multiple
changes and a `beta` type for incomplete or not-yet-scaled behavior. It also requires new
development flags to start disabled and requires both states to remain functional while
the flag exists.

### 3.2 Cleanup must be designed in, not remembered later

[GitLab's cleanup policy](https://docs.gitlab.com/development/feature_flags/controls/#cleaning-up)
states the core cost clearly: every surviving flag adds behavioral combinations and
reduces confidence that tests cover the active system. GitLab reports development flags
that survive more than two milestones and expects an old flag to be removed, converted
to a real setting, or abandoned.

Unleash similarly tracks active, potentially stale, stale, cleanup, and archived states.
[LaunchDarkly's code-reference model](https://launchdarkly.com/docs/home/flags/code-references)
adds a useful implementation detail: removal becomes safer when a tool can prove that a
flag key no longer has code references.

For SASE, a registry with a required review date plus simple repository reference checks
captures most of this value without a service. The date must trigger diagnostics and CI
review only; it must never flip behavior at runtime.

### 3.3 OpenFeature is a useful interface target, but not yet a useful dependency

The [OpenFeature evaluation specification](https://openfeature.dev/specification/sections/flag-evaluation/)
standardizes typed evaluation with caller-supplied defaults and detailed results. Its
[provider model](https://openfeature.dev/specification/sections/providers/) deliberately
allows providers backed by vendors, REST APIs, environment data, or local files, and
official SDKs exist for both
[Python and Rust](https://openfeature.dev/docs/reference/sdks/).

Those semantics are worth mirroring: a stable key, a default, a provider/resolver seam,
and a decision object that explains value, source, and reason. The SDK itself does not
solve SASE's main problem—lifecycle governance—and would require two runtime SDKs plus
provider initialization for a local boolean lookup. SASE can add an OpenFeature adapter
later if it needs remote targeting, without making the initial implementation depend on
one.

### 3.4 Flags are not a compatibility boundary

GitLab explicitly warns in its
[cleanup guidance](https://docs.gitlab.com/development/feature_flags/controls/#zero-downtime-upgrade-compatibility)
that a feature flag does not make mixed-version state changes safe. Although SASE is not
a multi-node Rails deployment, it does have separately released Python and Rust packages,
plugins, long-running processes, subprocesses, and persisted state. The same rule
applies: schema and wire compatibility must be solved independently; the flag chooses
behavior only after compatibility has been established.

## 4. Options considered

| Option | Strengths | Weaknesses | Fit |
| --- | --- | --- | --- |
| Ad hoc environment variables and helper functions | almost no initial work | no inventory, provenance, lifecycle, typo detection, or consistent precedence; repeats the old daemon knob proliferation | poor |
| `feature_flags:` config map only | simple and reuses existing merge behavior | strings at call sites, no owner/expiry/type, stale keys linger, defaults become duplicated config | fair for a prototype only |
| Typed in-repo registry plus local resolver | local, fast, testable, discoverable, lifecycle-aware, compatible with Config Center and Rust boundary | requires a small cross-repo core contract and governance checks | **best current fit** |
| OpenFeature SDK with an in-memory/file provider | standard API and future vendor portability | still needs a SASE registry; two SDK integrations, singleton/provider lifecycle, and more failure modes for no current targeting need | defer |
| Unleash, LaunchDarkly, or another remote service | rich targeting, live rollout, analytics, UI, stale-flag workflows | network/control-plane dependency, credentials, operations, cost, and targeting complexity SASE does not need | poor now |
| Compile-time/build features | removes disabled code from artifacts | cannot dogfood per machine/project or provide a post-release compatibility escape hatch; multiplies artifacts | unsuitable as the primary mechanism |

## 5. Proposed contract

### 5.1 Definitions are code-owned

Every first-party flag should be declared through one typed registry. A conceptual
record is:

```python
@dataclass(frozen=True)
class FeatureFlagDefinition:
    key: FeatureFlag
    kind: Literal["wip", "beta", "sunset", "ops"]
    description: str
    default: bool
    scope: Literal["global", "project"]
    owner: str                 # epic/bead or durable responsible component
    introduced_on: date
    review_on: date
```

Properties should have the following rules:

- Keys are stable, positive, descriptive `snake_case`; do not encode lifecycle words
  such as `beta` or `v2` in the key, and avoid double-negative `disable_*` names.
- `wip`, `beta`, and `sunset` always require an owner and finite `review_on` date.
- `ops` may have no expiry only when the registry entry explicitly documents why it is
  a permanent kill switch. Otherwise it also gets a review date.
- The default is explicit in the registry and is not duplicated in
  `default_config.yml`.
- Dates are review deadlines, never runtime inputs. Reproducible behavior cannot depend
  on today's date.
- Raw string lookup is private. Application call sites accept the typed `FeatureFlag`
  key, so misspellings are caught by Python typing or Rust compilation.

Keeping application definitions next to their owning application avoids a release-cycle
tax just to introduce a WIP flag. The generic Rust resolver accepts serialized
definitions and overrides. If a flag gates a Rust operation, the Python boundary passes
the resolved boolean or decision into that operation. If a future standalone Rust
process owns the toggle point, that process owns its typed definition and uses the same
core resolver.

### 5.2 User config contains overrides only

Add one top-level schema field:

```yaml
feature_flags:
  daemon_backed_agent_reads: true
```

The JSON Schema should allow an open map whose values are booleans. The runtime resolver
then validates keys against the code registry. This is preferable to enumerating each
flag in the config schema because flags are intentionally short-lived and the schema
should not need bespoke structural edits for every one.

Unknown file-based overrides should be ignored with an actionable diagnostic rather than
making every command unusable after a flag is removed or after a version downgrade.
Config Center and `sase doctor` should elevate that diagnostic prominently. Invalid
types must be errors.

Bundled/plugin defaults should not silently override first-party flags through ordinary
config merging. A flag's owner declares its default. A future plugin extension can let a
plugin register namespaced definitions and defaults, but third-party config should not
be able to flip unrelated SASE defaults merely by being installed.

### 5.3 Resolution is flat and explicit

Recommended precedence, lowest to highest:

1. definition default;
2. global user config;
3. selected machine/ordinary overlays in existing SASE order;
4. project-local config, for `scope: project` flags only;
5. explicit in-process/test overrides;
6. one process environment override, `SASE_FEATURE_FLAGS`, encoded as a JSON object of
   booleans.

The environment form should be a single mapping, for example:

```bash
SASE_FEATURE_FLAGS='{"daemon_backed_agent_reads":true}' sase ace
```

One mapping avoids a new environment variable per feature and preserves exact keys.
Invalid JSON, non-boolean values, or unknown environment keys should fail immediately
with a clear message because an operator explicitly requested that process behavior.

Do not add parent flags, milestone flags, global "all experimental features" switches,
or implicit dependencies in v1. If two independently reversible decisions exist, use two
flags. If they cannot safely differ, use one flag at their common routing boundary.

### 5.4 Evaluation produces details, not just a boolean

The core result should resemble OpenFeature's useful subset:

```python
@dataclass(frozen=True)
class FeatureFlagDecision:
    key: FeatureFlag
    enabled: bool
    default: bool
    source: Literal["default", "user", "overlay", "project", "runtime", "env"]
    source_detail: str | None
    overridden: bool
```

Normal routing may call `flags.enabled(FeatureFlag.X)`, but diagnostics and repro capture
can retain the full decision. The resolver should also return unknown-key, invalid-value,
wrong-scope, and overdue-review diagnostics.

Resolve an immutable `FeatureFlags` snapshot once at a command/app boundary. Do not read
config at every toggle point and do not evaluate flags at module import time. A command
therefore cannot change behavior halfway through if config files are edited. ACE should
load one snapshot at startup; live reload can be added later only as an explicit,
atomic whole-snapshot action.

When a parent process launches children that must make the same decisions, it should
forward the resolved snapshot through the same compact JSON environment representation.
That avoids a child resolving a different project or config state after launch.

### 5.5 Toggle at routing boundaries and inject the result

Prefer one decision near a feature's edge:

```python
provider = (
    DaemonAgentsProvider(...)
    if flags.enabled(FeatureFlag.DAEMON_BACKED_AGENT_READS)
    else DirectAgentsProvider(...)
)
```

Downstream code receives `provider`; it should not repeatedly ask the global flag system.
This limits the number of code paths that need cleanup, makes tests straightforward, and
prevents feature decisions from leaking into domain logic.

The registry and resolver are infrastructure, not a substitute for a feature-specific
fallback contract. A daemon route may still need capability checks and direct fallback;
those belong to that feature's router, not the generic flag record.

## 6. Lifecycle by use case

### 6.1 Epic / WIP

1. Add the `wip` definition disabled by default in the same change that adds the first
   gated code path.
2. Enable it in the SASE project's checked-in local config for dogfooding, or in a
   development-machine overlay when the affected process ignores project config.
3. Keep the default path fully functional throughout the epic.
4. Before closing the epic, either graduate the flag to `beta` with a new review date or
   remove the flag and losing branch.

Do not create one flag per epic phase by default. One flag should represent one coherent
user-visible routing decision; several independently shippable surfaces may warrant
several flags.

### 6.2 Beta

1. Start disabled and documented as opt-in.
2. Test both states and record non-default decisions in diagnostics/repro metadata.
3. When supported, flip the registry default in a focused change whose tests exercise
   the new default and the temporary opt-out.
4. After a bounded rollback window, remove the flag and old branch. If users are meant to
   choose forever, migrate it to an ordinary setting instead.

### 6.3 Deprecation and compatibility removal

Prefer a flag named for the desired new behavior:

1. Release A: new behavior exists behind a disabled `sunset` flag; old behavior remains
   the default.
2. Release B: flip the default on; users retain a documented, temporary opt-out.
3. Release C (or the declared compatibility boundary): remove the flag, override, and old
   implementation together.

The default flip should be isolated from unrelated feature work. Persisted schemas and
cross-version protocols must use expand-and-contract independently of this sequence.

### 6.4 Operational flags

Use `ops` only when an operator genuinely needs a rapid, supported degradation path.
Most flags that begin as beta should still be removed after stabilization. A permanent
kill switch is an exception that must say why it is permanent and have both states in
the normal test matrix.

## 7. Tooling and governance

### 7.1 User-facing inspection

Add read-only commands before adding convenience mutation commands:

- `sase feature list` — key, type, default, effective value, source, scope, owner, review
  date, and stale status;
- `sase feature explain <key>` — the winning decision plus layer-by-layer provenance;
- `sase doctor` checks for unknown overrides, invalid values, wrong-scope overrides, and
  overdue definitions.

Persistent changes should initially go through normal SASE YAML/Config Center
transactions so source provenance, chezmoi behavior, previews, and conflict protection
remain consistent. A `sase feature set/unset` command can be added later as a thin client
of those existing edit contracts.

At startup, log non-default effective flags once. Include the resolved non-default set in
ACE repro captures and agent launch metadata where relevant. Avoid logging on every
evaluation; the snapshot makes that noise unnecessary.

### 7.2 CI invariants

Fast tests should enforce:

- unique keys and valid naming;
- finite review dates for temporary kinds;
- no overdue temporary flag on the default branch without an explicit renewed date;
- every file-based override references a live definition;
- resolver precedence, scope, invalid-input, and provenance behavior;
- each flag's on and off branches have focused tests while both branches exist;
- the built-in default configuration is covered explicitly;
- removed registry keys have no code references or config overrides.

Do not test the Cartesian product of all flags. Test each flag independently, plus only
the small set of interactions that the product intentionally supports. Disallowing flag
dependencies in v1 keeps that set small.

An expiry check should fail CI or produce a deliberate review gate, but released SASE
versions must continue running after the date. No wall-clock behavior changes and no
time-bombed user installations.

## 8. Suggested implementation slices

This sequence keeps the first useful version small:

1. **Core contract:** add pure Rust definition validation, override resolution,
   diagnostics, decision wires, and focused tests under `sase_core::feature_flags`; expose
   a JSON-shaped PyO3 binding.
2. **Python facade and first flag:** add typed first-party definitions, serialize existing
   config layers to the core resolver, add the `feature_flags` schema field and strict env
   parser, and migrate `agents_daemon_reads_enabled()` as the first consumer.
3. **Inspection and governance:** add list/explain output, doctor diagnostics, expiry and
   code-reference CI checks, and repro/launch metadata.
4. **Config Center polish:** render registered flags as a catalog rather than as arbitrary
   map keys, while continuing to write ordinary sparse YAML overrides.
5. **Only if demanded:** add plugin-owned namespaced definitions, an OpenFeature adapter,
   or a remote provider. Do not block the local design on these extensions.

## 9. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Flag debt accumulates | required owner/review date, CI staleness gate, list/doctor visibility, removal reference check |
| Behavioral combinations explode | boolean-only, no dependencies, edge routing, per-flag tests plus explicit interaction tests |
| A typo silently changes behavior | typed call-site keys; strict environment parsing; config diagnostics for unknown keys |
| Removed flags break older/downgraded installs | unknown file overrides warn and are ignored; never make ordinary startup fatal |
| ACE and CLI resolve the same key differently | registry scope is explicit; split mixed-scope decisions; snapshot provenance is inspectable |
| Config changes alter an in-flight operation | immutable per-command/app snapshot |
| Plugin installation flips first-party behavior | owner-declared defaults; plugin defaults cannot override unrelated registry entries |
| Flags hide unsafe migrations | keep schema/wire expand-and-contract rules independent; gate routing only after compatibility checks |
| The abstraction grows into the old daemon rollout registry | keep feature-specific capabilities, perf gates, recovery commands, and fallbacks outside the generic flag contract |

## Sources

Repository evidence:

- `src/sase/ace/tui/data_providers/_settings.py`
- `src/sase/config/core.py`, `loading.py`, `layers.py`, `inventory.py`, and
  `sase.schema.json`
- `src/sase/main/ace_handler.py`
- `pyproject.toml` (`sase-core-rs>=0.27.5,<0.28.0`)
- `sase-core/crates/sase_core/src/config/` and
  `sase-core/crates/sase_core_py/src/lib.rs`
- SASE commits `f15037215` (daemon per-surface rollout hardening) and `5a65fa4fc`
  (daemon rollout revert), including the pre-revert `rollout_registry.py`,
  `read_config.py`, and `rollout_gates.py`

External sources:

- [Feature Toggles, Martin Fowler / Pete Hodgson](https://martinfowler.com/articles/feature-toggles.html)
- [Unleash feature flags, types, lifetimes, and lifecycle](https://docs.getunleash.io/concepts/feature-flags)
- [GitLab feature flag development guidance](https://docs.gitlab.com/development/feature_flags/)
- [GitLab feature flag controls and cleanup](https://docs.gitlab.com/development/feature_flags/controls/)
- [OpenFeature flag evaluation specification](https://openfeature.dev/specification/sections/flag-evaluation/)
- [OpenFeature provider specification](https://openfeature.dev/specification/sections/providers/)
- [OpenFeature SDKs](https://openfeature.dev/docs/reference/sdks/)
- [LaunchDarkly code references and extinction events](https://launchdarkly.com/docs/home/flags/code-references)

## Recommended solution

Implement a **boolean-only, typed, local feature-flag system with mandatory lifecycle
metadata**.

- Put generic definition validation, flat override resolution, provenance, and decision
  diagnostics in `sase-core`; expose them through the existing JSON/PyO3 boundary.
- Keep first-party flag definitions code-owned and typed in the application that owns
  their toggle points. Require `kind`, positive key, description, default, global/project
  scope, owner, introduction date, and review date.
- Add a sparse top-level `feature_flags:` boolean map to SASE config. Resolve definition
  default → user config → machine overlays → eligible project config → explicit test
  override → one strict `SASE_FEATURE_FLAGS` JSON environment override.
- Resolve one immutable snapshot at process/app startup, record non-default decisions,
  and inject choices at routing boundaries. Do not poll config at each call site.
- Support `wip`, `beta`, `sunset`, and narrowly justified `ops` kinds. Enforce expiry in
  CI/doctor, never by automatically changing runtime behavior.
- Ship `sase feature list`, `sase feature explain`, stale/unknown-override doctor checks,
  and on/off tests before adding remote targeting or convenient write commands.
- Start by migrating `agents_daemon_reads_enabled()` to prove the contract. Defer
  OpenFeature, plugin registries, percentage rollout, dependencies, and remote services
  until a concrete requirement needs them.

This gives epic branches a safe merge seam, beta features an inspectable opt-in path,
and deprecations a bounded escape hatch—while making flag removal part of the definition
of done rather than future cleanup work.
