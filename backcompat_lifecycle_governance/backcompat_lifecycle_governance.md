---
create_time: 2026-07-11
updated_time: 2026-07-11
status: research
---

# Governing the Lifecycle of Backward-Compatibility Logic

Consolidated from two independent research reports:
[backcompat_lifecycle_governance__a.md](backcompat_lifecycle_governance__a.md) (agent
`research.@.cdx`, external prior art and lifecycle policy) and
[backcompat_lifecycle_governance__b.md](backcompat_lifecycle_governance__b.md) (agent
`research.@.cld`, in-repo enforcement substrate).

## Problem Statement

SASE accumulates backward-compatibility ("backcompat") logic that never gets removed. The request
is explicitly two-sided and must not be collapsed into "stop writing backcompat":

- Agents should **keep adding** backcompat, because once SASE is popular, silently breaking real
  users is far worse than carrying a shim for a release or two.
- A **policy** must govern how and when a shim is deprecated, and — most importantly — a mechanism
  must **guarantee every shim is eventually removed** rather than accreting forever.

The real target is lifecycle management: a shim should be born with an expiry condition, an owner,
and a tracked work item, and the system should refuse to let it quietly become permanent. Today the
removal condition lives in nobody's head and nothing fails when a shim overstays.

**Scale.** Keyword scans are high-recall, not exact, but establish the problem is distributed:
`rg -li 'deprecat|backcompat|backward.compat|legacy' src` hits **235 files**; a broader scan adding
`compatibility` variants hits 306 of 1,774 Python files under `src/sase`, plus 219 test files and
31 docs. The shims span config aliases, persisted-format readers, CLI spellings, import façades,
agent-metadata/hook payload shapes, cross-repo contracts, and test patch points. Marker styles are
maximally inconsistent (`# Backward compat`, `# Back-compat shim`, docstring prose, schema
descriptions…) — none machine-parseable, none carrying a removal trigger, owner, or introduction
version. Any solution must first impose one structured form.

**Release velocity matters.** Tags `v0.2.0`–`v0.10.0` landed between June 13 and July 5, 2026. A
policy stated only as "keep for two releases" could expire in days. Removal thresholds need the
later of a calendar duration **and** a release boundary, not either alone.

## First Define What Is Protected

"Always add backward compatibility" without a boundary makes agents preserve private helper names
and accidental imports — more debt than user safety. Following
[PEP 387](https://peps.python.org/pep-0387/) and [SemVer](https://semver.org/), declare the
protected contract explicitly:

1. documented CLI commands, flags, directives, configuration, and environment variables;
2. persisted user data and repository-managed state written by a released SASE version;
3. documented Python APIs and plugin hooks;
4. cross-repository wire formats, metadata, env vars, and provider contracts;
5. documented workflows and behavior scripts can reasonably depend on.

Private names, test-only patch points, and undocumented module layout are not protected merely
because an in-repo test imports them. Internal multi-change transition shims are still tracked, but
under a much shorter horizon. The actionable rule for agents: **every change to an observable
released contract either preserves old behavior through the compatibility process or carries an
explicitly approved breaking-change exception.**

## What SASE Already Provides (build on these, do not reinvent)

1. **Custom linters gated by `just check`.** `just lint` already composes `ruff + mypy + pyscripts
   + pyvision + pylimit + keep-sorted + SASE validation` (`Justfile:124`), and `just check` is
   mandatory before landing. One more project linter is an established pattern.
2. **A self-cleaning, bead-keyed allowlist precedent.** `pyvision --epic-symbol
   <bead_id>(<symbol>)` (`Justfile:152-153,375-376`), run with `BD_COMMAND=tools/sase_bead`,
   already queries the bead store to decide whether a temporary code allowance is still legitimate
   and forces the entry to be dropped when the bead closes. This is exactly the forcing-function
   loop needed, applied today to epic scaffolding instead of backcompat.
3. **Beads as a dependency-aware tracker with agent execution.** `sase bead` supports
   `create/dep/ready/blocked/close/work`; dependencies plus `ready` express "removal becomes
   actionable when its trigger fires," and `sase bead work` can launch an agent to perform the
   deletion. Caveat: beads are currently **plan-shaped** (`-T plan/phase`, `--tier plan/epic`,
   attached to plan files/ChangeSpecs), so a literal one-bead-per-shim needs a lightweight
   removal/chore bead type — the main net-new plumbing cost.
4. **Bidirectional structured-block enforcement precedent.** `keep-sorted` shows CI enforcing
   invariants on declarative blocks; the same spirit validates marker↔bead consistency.
5. **Partial deprecation surfaces.** `src/sase/config/core.py` centralizes some
   deprecated/retired config keys and `sase doctor` exposes some to users — useful hooks, but with
   no lifecycle metadata (no introduced-in, promise window, proving test, owner, or deadline).
   Cleanup so far has happened via intentional campaigns, not per-shim end states.

## Prior Art, Distilled

- **PEP 387 (Python):** deprecation is a multi-release process — warn on old use, name the removal
  release in the warning, wait the stated window, then remove. "Deprecated" must not be ambiguous:
  a temporary shim is a hard deprecation with a removal target; a behavior kept indefinitely is a
  supported contract, not compatibility debt.
- **Django:** release-versioned warning classes plus a generated central timeline of upcoming
  removals. Lesson: a human-readable "what lapses when" view generated from structured records is
  valuable; a documentation list alone proves nothing about the code.
- **Kubernetes:** different contract classes get different guarantees (GA CLI: ≥12 months or two
  releases, whichever is longer); "time **and** releases"; and crucially, *accepting an old input*
  is distinct from *retaining the ability to decode persisted data* — the decoder must outlive the
  endpoint. Deprecated-path use is instrumented with the target removal version attached.
- **Chromium flags:** every flag has an owner and an `expiry_milestone`; tooling finds expired
  flags and notifies owners; indefinite expiry needs special approval. Closest model for the
  enforcement problem — but a metadata entry disappearing is not proof the implementation did, so
  SASE should additionally require source/test markers and a removal work item.

## Options Compared

| Option | Removal guarantee | Friction | State lives in | Governs introduction | Agent-executable |
| --- | --- | --- | --- | --- | --- |
| A. Policy + review only | none (status quo) | lowest | heads | weakly | no |
| B. In-code expiry markers + linter | strong (CI hard-fail) | low | code | requires marker | no |
| C. Central registry file | strong | medium (two edits; drift) | central file | requires row | no |
| D. Bead-backed tracking | strong *with* linter | high (bead-type gap) | tracker | requires bead | **yes** |
| E. Version-gated windows (Go/semver N-2) | strong, predictable | low | policy | **yes** | no |
| F. Scheduled agentic sweep | medium alone | low | agent | no | **yes** |
| Telemetry / `doctor` diagnostics | supporting only | low | runtime | no | no |
| Versioned readers/converters | required for persisted data | design work | code | no | no |

The rows are complementary, not competing: B is the **teeth**, E is the **clock**, D is the **work
item**, F is the **driver**, A is the **rule**. Telemetry helps users migrate but absence of
observations never proves absence of users (offline/privacy-conscious users are invisible), and
versioned decoding is the required technique for persisted data regardless of tracking mechanism.
Today only a weak version of A exists — which is what produced the backlog.

### Resolved divergence: central ledger vs. in-code markers

Report A proposed a hand-maintained `compatibility.yml` ledger as the lifecycle authority with
markers as join keys; report B argued a registry duplicates state and drifts, preferring markers as
the single source of truth with beads as the work handle. **Resolution: markers win as the source
of truth.** The in-repo precedents (`--epic-symbol`, `keep-sorted`) are marker/allowlist-shaped;
one edit point per shim keeps friction low for agents; and A's own design conceded source locations
must come from markers anyway. The ledger's genuine value — a portfolio view ("what do we owe and
when does it lapse?"), Django-style timelines, and owner notifications — is preserved by
**generating** that report from the markers instead of hand-maintaining it. A hand-maintained
registry remains the documented fallback only if the lightweight bead type proves too heavy.

## Recommended Solution

**A layered lifecycle system: one structured in-code marker per shim, keyed to a removal bead,
enforced by a bead-aware `_lint-backcompat` stage in `just check`, with removal windows anchored to
both calendar and releases, and a scheduled sweep agent that works removals before CI ever fails —
generalizing the proven `pyvision --epic-symbol` loop.**

**Layer 0 — Policy (the rule).** Add a "Backward-Compatibility Lifecycle" section to agent
instructions (with user approval — memory files are permission-gated). Two governing rules:

- *Introduction rule:* only add a shim when a real consumer inside the declared **compatibility
  baseline** (the oldest version/state we owe compatibility to) is protected, and the change
  touches a protected contract (see above). Prefer the narrowest adapter that normalizes old input
  at the boundary into one canonical path; for persisted data, versioned decode-then-convert — old
  branches must not spread through domain logic.
- *Birth-certificate rule:* **no shim merges without a removal trigger and a tracking id.** A shim
  with no declared death is a lint error, full stop.

**Layer 1 — One structured marker (source of truth, in the code):**

```python
# BACKCOMPAT[bd-1234]: since=v0.11.0 remove_by=2026-10-15/v0.14.0 reason="old sibling_repos spelling"
```

plus a `@backcompat(bead="bd-1234", ...)` decorator form for whole callables, and equivalent
comment forms for Rust/YAML. `remove_by` carries **both** a date and a release; the shim is
removal-due only when both have passed. A shim spanning multiple files repeats the same id, and its
old-behavior tests carry the same marker — the id is the join key between code, tests, and bead.
This one form replaces all ~235 ad-hoc styles.

**Layer 2 — `_lint-backcompat` in `just lint`/`just check` (the teeth).** Built like the other
project linters, run with `BD_COMMAND=tools/sase_bead`. Hard-fails when:

1. a marker is malformed or missing `remove_by`/bead id;
2. a marker's bead is absent, or terminal while the marker still exists (bidirectional,
   self-cleaning — same spirit as `--epic-symbol`);
3. a marked shim has no non-test implementation site or no old-behavior test carrying the id;
4. both `remove_by` thresholds (date **and** release) have passed — after a short grace/notify
   window, so the first lapse warns and only a grossly overdue shim blocks;
5. (initially advisory, then fatal on new diffs only) backcompat-ish language — `legacy`,
   `deprecated`, alias/fallback/old-schema branches — appears without a structured marker or an
   explicit `compat-permanent`/`not-compat` annotation with rationale.

A daily scheduled run catches expiry even when the repo is quiet. Extensions must update the
thresholds with evidence in review — never an automatic bump. "Never expires" is prohibited for
temporary entries: a genuinely permanent bridge is reclassified as a supported contract (owner
approval + maintenance rationale) and leaves the temporary system.

**Layer 3 — Beads as the work item.** The removal bead is created in the same change that adds the
shim, with acceptance criteria naming every marker site. Dependencies express triggers ("blocked
until vX ships"); the bead flips `ready` ~14 days before expiry; `sase bead work` lets an agent
execute the deletion. Build cost: a lightweight removal/chore bead type, since current beads are
plan-shaped. Granularity: one bead per independently removable behavior (which may span files),
never one per keyword match.

**Layer 4 — Version anchor (the clock).** Default windows by contract class, taking the **later**
of the two thresholds:

| Contract class | Minimum window | Additional gate |
| --- | --- | --- |
| Internal transition / experimental surface | 30 days + 1 feature release | no external/persisted use |
| CLI, config, directives, env vars, documented Python API | 90 days + 2 feature releases | warning/diagnostic shipped |
| Cross-repo plugin or wire contract | 90 days + 2 feature releases | all first-party peers migrated |
| Persisted user data/layout | 180 days + 2 feature releases | migration shipped; supported upgrade paths can still decode |

At `1.0`, publish stronger guarantees (≥180 days/two releases for public surface, ≥12 months for
persisted data, API removals on SemVer majors) rather than inheriting them accidentally. Once a
release train exists, `remove_by` becomes mechanical (e.g. current + previous two). Keep the
Kubernetes distinction: a legacy CLI spelling may go earlier than the decoder needed to rescue old
on-disk state.

**Layer 5 — Scheduled sweep agent (the driver) + generated timeline.** A cron/xprompt audit agent
periodically lists ready removal beads and soon-to-expire markers, launches removal agents/PRs, and
nudges owners *before* the linter fails — converting the CI time-bomb into proactively worked
hygiene. The same tooling generates the Django-style "upcoming removals" report and `sase doctor`
surfaces user-facing deprecations with replacement and removal target.

**Lifecycle in practice.** Introduce (shim + warning where practical + marker + old-path and
canonical-path tests + removal bead + migration docs, all in one change) → observe/migrate
(warnings name the replacement; telemetry may justify an extension but its absence never
accelerates removal) → removal-due (bead ready, owner notified, then CI gate) → remove completely
(delete the branch, warning, old-behavior tests, markers, migration-only docs, dead helpers; close
the bead; a negative test may remain only to verify an actionable error) → exceptions (security,
data corruption, legal, or behavior no released user could observe may break immediately, but still
leave an explicit exception record so changelog/CI can tell deliberate from accidental).

## Immediate Backlog Remediation

The premise is that **no current consumer needs the existing logic**, so this moment is a one-time
baseline reset — do not age 235+ files through new windows. Declare the compatibility baseline at
the current version, then:

1. generate a candidate inventory from keywords, aliases, fallback readers, converters, and git
   history;
2. classify each as public contract / persisted data / first-party cross-repo bridge /
   internal-test shim / false positive;
3. check the linked first-party repos (`sase-core`, `sase-github`, `sase-telegram`, `sase-nvim`)
   for live consumers of cross-repo bridges;
4. delete unneeded shims now, in subsystem-sized changes, keeping explicit migration tools only
   where real user state may exist;
5. add markers + beads only for compatibility that survives the audit, so the backlog cannot
   re-form.

A handful of subsystem audit beads can drive this sweep; the one-bead-per-shim rule applies to new
debt after the policy takes effect.

## Risks and Mitigations

- **Time-bomb blocks an unrelated PR:** Layer 5 works removals early; the linter warns through a
  grace window before hard-failing; a reviewed short extension stays possible.
- **Agents don't comply:** encode Layer 0 in always-loaded instructions uniformly for all runtimes,
  and ship a `#backcompat` xprompt/skill that emits the marker and opens the bead in one step.
- **False-positive detection:** hard-enforce only explicit markers; roll the language heuristic out
  as advisory, then diff-only fatal.
- **Marker/bead drift:** the bidirectional lint validates both directions, exactly as
  `--epic-symbol` does.
- **Shim rots before removal:** every entry requires an old-behavior test carrying its id.
- **Warning noise:** warn only on actual old-path use; aggregate cleanup surfaces via `sase doctor`.
- **Permanent adapters hiding as temporary:** indefinite expiry is forbidden; reclassification to
  supported contract requires owner rationale.
- **Bead-model fit:** if the lightweight bead type proves heavy, fall back to a validated central
  registry file as the tracking handle and keep Layers 1–2 and 4–5 unchanged.
- **Over-deletion:** the compatibility baseline is the guard — only delete below it.

## Sources

- [backcompat_lifecycle_governance__a.md](backcompat_lifecycle_governance__a.md) — prior art
  (PEP 387, Django, Kubernetes, Chromium), protected-contract scoping, dual thresholds, horizons,
  lifecycle stages, backlog procedure.
- [backcompat_lifecycle_governance__b.md](backcompat_lifecycle_governance__b.md) — in-repo
  substrate (`Justfile` linters, `pyvision --epic-symbol`, `keep-sorted`, bead model and its
  plan-shaped caveat), layered teeth/clock/work-item/driver/rule framing, sweep agent, verification
  evidence.
- External: [PEP 387](https://peps.python.org/pep-0387/),
  [SemVer 2.0.0](https://semver.org/),
  [Django release process](https://docs.djangoproject.com/en/6.1/internals/release-process/),
  [Kubernetes deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/),
  [Chromium flag expiry](https://chromium.googlesource.com/chromium/src/+/main/docs/flag_expiry.md).
