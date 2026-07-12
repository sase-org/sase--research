---
create_time: 2026-07-11
updated_time: 2026-07-11
status: research
---

# Governing and Reliably Removing Backward-Compatibility Logic

## Research Question

SASE should protect users from breaking changes as adoption grows, but a compatibility shim is
also a maintenance liability: it adds branches, tests, documentation, debugging states, and often
another data or protocol format. What policy and tooling can require agents to introduce backward
compatibility for real contracts while also ensuring that temporary compatibility code is removed?

The central conclusion is that deprecation policy and cleanup tracking cannot be separate systems.
Every temporary compatibility path needs a machine-readable expiration record, a local code marker,
a tested migration path, and a pre-created removal task. CI—not memory, comments, or a periodic
human audit—must make an overdue shim impossible to ignore.

## Current SASE Baseline

This repository already contains several distinct forms of compatibility:

- CLI and prompt syntax aliases;
- configuration-key renames and ignored retired keys;
- readers and migrations for persisted file formats and directory layouts;
- import/module façades and re-exported symbols;
- old agent metadata, hook payload, and provider protocol shapes;
- cross-repository environment-variable and plugin compatibility;
- test patch points and helpers preserved for older tests.

A deliberately broad keyword scan for `legacy`, `deprecated`, `compatibility`, and variants found
matches in 306 of 1,774 Python files under `src/sase`, as well as 219 test files and 31 documentation
files. This is a high-recall signal, not an exact inventory: some matches describe stable protocol
compatibility or ordinary English, while some compatibility branches do not use these words.
Nevertheless, it establishes that the cleanup problem is distributed rather than confined to one
subsystem.

There are useful partial mechanisms already:

- `src/sase/config/core.py` centralizes some deprecated, unsupported, and retired config keys, and
  `sase doctor` / Config Center expose some of them to users.
- The changelog and history show successful cleanup campaigns, including removal of legacy memory
  layouts, plugin commands, directives, project aliases, provider paths, and migration UI.
- `just lint` already composes repository-specific validators, so an additional compatibility
  validator fits the existing development and CI model.
- Beads provide an in-repository unit of scheduled work that agents already understand.

The gap is lifecycle metadata. For example, `DEPRECATED_TOP_LEVEL_KEYS` says what replaces a key,
but not when the alias was introduced, how long it is promised, which test proves it, who owns it,
or when its removal becomes mandatory. Cleanup currently happens through intentional campaigns,
not because each new shim carries its own enforceable end state.

The release history also matters. Tags `v0.2.0` through `v0.10.0` were created between June 13 and
July 5, 2026. A policy stated only as “two releases” could therefore expire in days. SASE needs the
later of a calendar duration and a release boundary, not either one alone.

## First Define What Is Protected

A policy that says “always add backward compatibility” without defining its boundary will cause
agents to preserve private helper names, test implementation details, and accidental imports. That
creates more debt than user safety. Python's compatibility policy draws a useful boundary: public
APIs are protected, while explicitly private names, internal inheritance, and tests are not
([PEP 387](https://peps.python.org/pep-0387/)). Semantic Versioning similarly requires a project to
declare its public API before version numbers can communicate compatibility
([Semantic Versioning 2.0.0](https://semver.org/)).

For SASE, the protected contract should explicitly include:

1. documented CLI commands, flags, directives, configuration, and environment variables;
2. persisted user data and repository-managed state that a released SASE version writes;
3. documented Python APIs and plugin hooks;
4. cross-repository wire formats, metadata, environment variables, and provider contracts;
5. documented workflows and behavior that scripts can reasonably depend on.

Private Python names, test-only patch points, undocumented module layout, and implementation details
should not become public merely because an in-repository test imports them. If a multi-change
internal refactor temporarily needs a shim, that shim should still be tracked, but under a much
shorter internal-transition horizon.

This gives agents an actionable rule: **every change to an observable released contract must either
preserve old behavior through the compatibility process or carry an explicitly approved breaking-
change exception.** It does not require an alias for every private rename.

## Prior Art and Lessons

### Python: warnings need a declared removal release and feedback path

PEP 387 treats incompatible change as a multi-release process: discuss it, warn on old use, name the
expected removal release in the warning, link to a feedback issue, wait through the stated window,
then remove the old behavior and warning. It also distinguishes a “soft deprecation,” which has no
scheduled removal, from a real deprecation
([PEP 387](https://peps.python.org/pep-0387/)).

The lesson for SASE is that “deprecated” must not be an ambiguous status. A temporary shim should be
a hard deprecation with a removal target. A behavior intended to remain indefinitely is a supported
legacy contract or permanent adapter—not temporary compatibility debt—and should be reviewed as
such.

### Django: a visible removal timeline prevents forgotten shims

Django encodes its deprecation window in release-specific warning classes and maintains a central
timeline of what will be removed in each future release. Features normally remain through at least
two feature releases before removal
([release process](https://docs.djangoproject.com/en/6.1/internals/release-process/),
[deprecation timeline](https://docs.djangoproject.com/en/dev/internals/deprecation/)).

The lesson is that generating a human-readable “upcoming removals” view from structured records is
valuable. The weakness, if copied alone, is that a documentation list does not prove the code or its
tests were removed.

### Kubernetes: different contract classes need different guarantees

Kubernetes applies different lifetimes to stable, beta, and alpha surfaces, and different rules to
APIs, CLI elements, metrics, and behaviors. User-facing GA CLI elements work for at least 12 months
or two releases after announced deprecation, whichever is longer. Persisted API data receives
stronger treatment: the server must remain able to decode/convert stored representations even after
an endpoint stops being served. Deprecated API use emits warnings and is observable in audit data
and a metric labeled with the removal release
([Kubernetes deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)).

The lessons are:

- use stability/contract classes rather than one arbitrary duration;
- use “time **and** releases,” especially when cadence varies;
- distinguish accepting an old input from retaining the ability to decode persisted data;
- instrument deprecated-path use where practical, with the target removal version attached.

### Chromium: ownership plus machine-readable expiry drives cleanup

Chromium's flag metadata requires owners and an `expiry_milestone`. Tooling determines which flags
are expired; indefinite expiry requires a rationale and special approval. Owners are notified, and
the documented purpose is to make obsolete flags eventually get cleaned up
([flag metadata](https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/chrome/browser/flag-metadata.json),
[ownership](https://chromium.googlesource.com/chromium/src/+/main/docs/flag_ownership.md),
[expiry process](https://chromium.googlesource.com/chromium/src/+/main/docs/flag_expiry.md)).

This is the closest model for the enforcement problem. A structured expiry ledger can be validated,
queried, used to notify an owner, and connected to automation. SASE should go one step further by
requiring source/test markers and a removal bead, because a metadata entry disappearing is not by
itself proof that the implementation disappeared.

## Implementation Options

| Approach | Strengths | Failure mode | Removal assurance |
| --- | --- | --- | --- |
| Prose policy + code review checklist | Very cheap; clarifies intent | Agents and reviewers miss entries; no inventory | Low |
| Removal issue/bead only | Assignable, discussable, visible in normal planning | Can be closed, stale, renamed, or detached from code | Low–medium |
| Inline `TODO(remove...)` with date/version | Code is locally understandable; simple scanner | Duplicated metadata; hard to query across files; comments drift | Medium |
| Central compatibility ledger only | Queryable ownership, deadlines, reports | Ledger can drift from actual code and tests | Medium |
| Ledger + local markers + CI + removal bead | Atomic metadata, code linkage, scheduling, enforced expiry | Requires a small custom validator and disciplined exceptions | High |
| Usage telemetry / `doctor` diagnostics | Evidence for migration and extensions; helps users | Absence of observations does not prove absence of users | Supporting only |
| Feature flags | Useful for rollout and rollback | Flags themselves become debt; poor fit for file-format aliases/import façades | Supporting only |
| Versioned readers/converters | Safest persisted-data and wire evolution | More design work; does not schedule their deletion by itself | Required for those classes |

No single tracking surface is enough. An issue tracker is good at work ownership but bad at proving
source state. Inline comments are good at explaining a branch but bad at portfolio reporting. A
central ledger is good at policy enforcement but needs code markers to prevent drift. The combined
model uses each for what it is good at.

## Proposed Compatibility Record

Add one tracked, machine-readable ledger, for example `compatibility.yml` at the repository root.
Each temporary compatibility behavior gets a stable ID, normally its dedicated removal bead ID:

```yaml
version: 1
compatibility:
  - id: sase-abc
    contract: config
    owner: config
    introduced_in: 0.11.0
    deprecated_in: 0.11.0
    remove_after: 2026-10-15
    remove_in_or_after: 0.14.0
    replacement: "Use linked_repos instead of sibling_repos"
    warning: doctor
    migration: rewrite_on_edit
    removal_bead: sase-abc
    status: active
```

Required fields should be `id`, `contract`, `owner`, `introduced_in`, `remove_after`,
`remove_in_or_after`, `replacement` (or an explanation that none exists), `warning`, `migration`,
`removal_bead`, and `status`. The actual source locations should not be hand-maintained in YAML;
language-neutral comments should establish them:

```python
# compat[sase-abc]: accept the released sibling_repos spelling
```

```rust
// compat[sase-abc]: decode schema v2 records during the migration window
```

The old-behavior tests should carry the same marker. The marker is both local explanation and the
join key between code, tests, ledger, and bead. A shim spanning multiple files simply repeats the
same ID.

The ledger is the lifecycle authority because it changes atomically with code and CI. The bead is
the work-scheduling authority: it exists from the day the shim is added, rather than being created
after somebody notices expiry.

## CI Enforcement

Add a focused `tools/compat_lint` check to `just lint` / `just check`. It should fail when:

1. a `compat[...]` source or test marker has no ledger entry;
2. a ledger entry has no non-test implementation marker or no old-behavior test marker;
3. required metadata is missing or its dates/versions are malformed;
4. the removal bead is absent or terminal while the compatibility code remains;
5. the current date is later than `remove_after` **and** the current version is at or beyond
   `remove_in_or_after`;
6. a PR deletes the ledger entry but leaves markers behind;
7. a compatibility-like addition uses explicit legacy/deprecation markers without an ID.

The final heuristic should initially be advisory because terms such as “protocol compatibility” can
describe permanent behavior. The exact markers and ledger relationships can be hard errors from day
one. Once the existing corpus is classified, the heuristic can become a diff-only presubmit rule:
new `legacy`, `deprecated`, compatibility fallback, alias, or old-schema branches must either carry
a compatibility ID or an explicit `compat-permanent` / `not-compat` annotation with rationale.

Expiry should block ordinary CI after a short notification period. Quietly opening an issue is not
enforcement; a red build makes removal or an explicit extension part of the critical path. A daily
scheduled CI job should also run the validator so expiry is detected even when the repository is
temporarily quiet.

An extension must update the date/version, explain the evidence, and leave history in code review.
It should never be an automatic date bump. A “never expires” value should be prohibited for
temporary entries. If a bridge is genuinely permanent, reclassify it as a supported contract and
remove it from the temporary ledger; that decision should require owner approval and a maintenance
rationale.

## Lifecycle Policy

### 1. Introduce

In the same change that alters a protected contract, the agent must:

1. implement the canonical behavior and the narrowest possible old-to-new adapter;
2. emit an actionable warning or diagnostic when old behavior is observed, where practical;
3. add a ledger entry and source/test markers;
4. test both the canonical path and the compatibility path;
5. create the removal bead with acceptance criteria naming every marker;
6. document replacement/migration steps and the earliest removal target.

“We might need compatibility later” is not enough reason to duplicate an entire implementation.
Prefer an adapter that normalizes old input at the boundary and then invokes one canonical code
path. For persisted data, prefer versioned decoding followed by conversion to the current in-memory
form; do not let old-format branches spread throughout the domain logic.

### 2. Observe and migrate

Warnings should include the replacement and removal target. CLI/config deprecations should appear in
`sase doctor` where that produces an actionable cleanup. Local counters or diagnostics can measure
old-path use without sending data externally. Optional telemetry may inform an extension, but lack
of telemetry must not accelerate removal: offline and privacy-conscious users are invisible.

### 3. Become removal-due

An entry is removal-due only when both its calendar and release thresholds have passed. The removal
bead should become ready before this point (for example, 14 days earlier), and automation should
notify its owner. After the deadline, CI fails until the shim is removed or a reviewed extension is
merged.

### 4. Remove completely

The removal change deletes:

- the old input/behavior branch and warning;
- its old-behavior tests and all markers;
- migration-only docs or changes them into historical release notes;
- the ledger entry;
- any no-longer-needed helper or dependency.

It then closes the removal bead. A negative test may remain if it verifies an actionable error for
the now-unsupported form, but it is no longer a compatibility test.

### 5. Exceptions

Security, data corruption, legal requirements, or a behavior that no released user could have
observed may justify immediate removal. The breaking change should still receive a short ledger
record or explicit exception record so CI and the changelog can distinguish a deliberate exception
from an accidental omission.

## Suggested Horizons

Because SASE is currently `0.x` and releases very frequently, use conservative but finite defaults:

| Contract class | Minimum window before removal | Additional gate |
| --- | --- | --- |
| Internal transition across a multi-change rollout | 30 days and 1 feature release | No external/persisted use |
| Alpha/explicitly experimental public surface | 30 days and 1 feature release | Replacement or clear unsupported error |
| Normal CLI, config, directive, env var, documented Python API | 90 days and 2 feature releases | Warning/diagnostic shipped |
| Cross-repo plugin or wire contract | 90 days and 2 feature releases | All first-party peers migrated |
| Persisted user data/layout | 180 days and 2 feature releases | Migration shipped; supported upgrade paths can decode/convert it |

These are minimums, not promises to remove blindly. Use the later threshold. At `1.0`, the public
surface should move to at least 180 days and two feature releases, with incompatible public API
removal aligned to a SemVer major release. Persisted-data support should move to at least 12 months
and a documented supported-upgrade window. The project should publish these guarantees before
`1.0` rather than inheriting them accidentally.

The persisted-data gate is intentionally evidence-based. Kubernetes' distinction is instructive:
stopping new requests in an old form is different from being unable to read state previously written
in that form. SASE may remove a legacy CLI spelling earlier than the decoder needed to rescue old
on-disk state.

## Treating the Existing Backlog

The user's premise is that no current external projects require the existing compatibility logic.
That makes the present moment a one-time baseline reset, not a reason to put hundreds of old paths
through a new six-month window.

Recommended baseline procedure:

1. generate a candidate inventory from compatibility keywords, aliases, fallback readers, schema
   converters, and git history;
2. classify each candidate as public contract, persisted data, first-party cross-repo bridge,
   internal/test-only shim, or false positive;
3. check the linked first-party repositories for live consumers of cross-repo bridges;
4. remove unneeded internal/test shims immediately;
5. remove public/persisted shims in subsystem-sized changes, preserving explicit migration tools
   only where real user state may exist;
6. seed the new ledger only with compatibility that survives this audit.

Do not create one removal bead for every keyword match. Create one bead per independently removable
compatibility behavior, which may span several files. A small number of subsystem audit beads can
drive the baseline cleanup; the one-bead-per-shim rule applies to new debt after the policy takes
effect.

## Risks and Mitigations

- **Registry bureaucracy:** keep the schema small, provide a command/template that creates the entry
  and removal bead together, and infer source locations from markers.
- **Agents evade the process accidentally:** put the rule in agent instructions, make PR guidance
  match it, and use a diff heuristic as a backstop.
- **False-positive compatibility detection:** hard-enforce explicit markers; roll out word/AST
  heuristics as warnings before making only new-diff violations fatal.
- **Expired shim blocks unrelated work:** notify before expiry and make the bead ready early. The
  build blockage is the enforcement mechanism, but a reviewed short extension remains possible.
- **Bead/ledger drift:** CI validates the reference and status; the ledger remains authoritative for
  code lifecycle.
- **Compatibility path rots before removal:** require an old-behavior test for every entry.
- **Warnings become noisy:** warn only on actual old-path use, deduplicate within a run where useful,
  and expose aggregate cleanup through `sase doctor`.
- **Permanent adapters hide in the temporary system:** forbid indefinite expiry; require an explicit
  supported-contract classification and owner rationale.

## Recommended Solution

Adopt an **expiring compatibility ledger** backed by **local source/test markers, a removal bead
created in the same change, and a CI deadline gate**. Scope the compatibility mandate to released,
observable contracts and persisted data—not private implementation details. Give every temporary
shim two thresholds (calendar date and release), remove it only after both pass, and make CI fail if
it remains past that point. Use 90 days plus two feature releases as the current default for public
interfaces, 180 days plus two feature releases for persisted data, and shorter windows for explicitly
experimental or internal transitions. Generate a human-readable deprecation timeline and owner
notifications from the ledger; use warnings, `sase doctor`, and optional usage evidence to help
users migrate, not as substitutes for the deadline.

Begin with a one-time audit that aggressively removes today's unneeded shims under the stated
no-consumer premise, then seed the ledger only with compatibility that must remain. This combination
provides the missing closed loop: agents cannot add compatibility without scheduling its deletion,
tests keep it working during the promise window, and the build eventually forces either removal or
an explicit, reviewable extension.
