---
create_time: 2026-08-16
updated_time: 2026-08-16
status: research
---

# Feature Flags for SASE: Bead-Keyed Registry with a Real Expiry Trigger

**Research question:** What feature-flag design best supports (a) multi-change epic work,
(b) unstable/beta features, and (c) staged removal of deprecated behavior?

**Consolidated from** two independent reports plus a third verification pass:

- [`feature_flag_lifecycle_governance__a.md`](feature_flag_lifecycle_governance__a.md) —
  agent `research.0m.cdx`. External lifecycle prior art, six-option comparison, resolver
  contract, `sase-core` split.
- [`feature_flag_lifecycle_governance__b.md`](feature_flag_lifecycle_governance__b.md) —
  agent `research.0m.cld`. In-repo substrate, bead-keyed expiry, schema-generation finding,
  use-case re-ranking.
- This report — independent re-verification at `30c9ba23b`, resolving the four
  disagreements and correcting two errors that survive in both.

A **third**, earlier report — [`../feature_flag_architecture.md`](../feature_flag_architecture.md)
(2026-08-15) — already existed in this directory and is the common ancestor both agents read.
It is left in place unchanged. Its conclusions are folded in here; it is not restated.

Every repository claim below was re-checked against the working tree at `30c9ba23b`
(SASE 0.16.0, `sase-core-rs>=0.27.11`) on 2026-08-16. Both source reports were written
against `4fae4e794`; line numbers below reflect the newer tree. No runtime code changed.

## Bottom line

Build a **Python-only, boolean-only feature-flag registry** whose every temporary entry is
keyed to a **dedicated removal bead** *and* carries a **`remove_by` date+release threshold**,
whose keys are **generated into the config JSON Schema**, and whose enforcement ships in the
**same change** as the registry, as a `tools/check_feature_flags` lint stage.

The scarce resource in this repository is not flag evaluation — it is *deletion*. Everything
below is chosen to make removal a forced event rather than optional hygiene.

## 1. What both reports settled (do not relitigate)

These are agreed across all three prior reports and independently hold up. They are the
uncontested base of the design:

- **Boolean-only, local, in-process.** No hosted service, no OpenFeature SDK, no targeting,
  percentages, cohorts, experiments, flag dependencies, or network control plane. SASE is a
  locally installed CLI/TUI. Mirror OpenFeature's *shape* (stable key, caller default,
  resolver seam, decision object with value/source/reason); take the dependency only if
  remote targeting ever becomes real.
- **Cargo/build features are the wrong tool.** They cannot be flipped per process, machine,
  or project after install and cannot serve as a post-release escape hatch. Keep them for
  optional dependencies and platform code.
- **Code-owned typed registry, not raw strings.** Call sites take a typed key so typos fail
  at type-check time. Config carries *sparse overrides only*; the default lives in the
  registry.
- **Existing config layers are the persistent control plane.** `default` → `plugin:*` →
  `user` → `overlay:*` → `local`, later scalars win (`config/layers.py`). No new store, no
  file watcher.
- **One strict `SASE_FEATURE_FLAGS` JSON env override**, not one variable per flag. Strictness
  is asymmetric on purpose: bad *env* input fails loudly (an operator typed it this process);
  unknown *file* keys warn and are ignored (a config file outlives the flag it names).
- **Immutable snapshot resolved once at a command/app boundary**, never at import time, then
  injected at routing boundaries so downstream code never consults global flag state.
- **Explicit `global` vs `project` scope.** `sase ace` calls `set_include_local_config(False)`
  (`config/core.py:101`, `main/ace_handler.py:162` — verified), so a project-local override is
  genuinely invisible to ACE. A flag must declare whether project scope is even legal.
- **Plugin layers must not flip first-party defaults.** Installing a plugin must not silently
  change SASE behavior.
- **Dates must never change runtime behavior.** Expiry drives CI/doctor diagnostics only. No
  time-bombed installs.
- **A flag is a router, not a migration protocol.** Persisted and wire formats still need
  independent expand-and-contract.
- **Naming:** stable positive `snake_case`; no `disable_*` double negatives; no lifecycle
  words (`beta`, `v2`) in the key, since a graduating flag would need a rename.

## 2. The four disagreements, resolved

### 2.1 Resolver location: Python-only — but not for the reason report B gives

**B is right; its headline argument is wrong.** B claims a `sase-core` resolver is too
expensive because it costs "a cross-repo release round trip." The actual cadence refutes
that. `pyproject.toml` floor history shows the core pin ratcheted from `0.20.0` (Aug 8) to
`0.27.11` (Aug 16) — roughly twenty ratchets in eight days, **five on 2026-08-15 alone** —
and the repo ships dedicated tooling for it (`tools/ratchet_core_window`,
`tools/probe_core_floor`, `just validate`'s `validate_sase_core_rs_version`). A core
round trip is routine daily traffic here, not a tax.

The real reasons to keep v1 in Python are two, and they are decisive:

1. **There is no Rust consumer.** Under *both* proposals the resolved boolean is what crosses
   the PyO3 binding; Rust never resolves a flag. A core resolver would be unexercised
   duplicate logic.
2. **Duplication in core config is already load-bearing.** `sase_core/src/config/mod.rs:14-16`
   states the merge "mirrors `sase.config.core._deep_merge` exactly so the two can never
   silently diverge (see the parity tests)." Adding a second such surface for a chain whose
   entire semantics are "last layer that mentions the key wins, for a boolean" buys nothing.

There is also a principled point neither report made. `CLAUDE.md`'s litmus test — "if a web
app, CLI, editor integration, or another frontend would need the behavior to match the TUI,
treat it as core backend logic" — does not actually catch flag resolution. A flag decision is
a *deployment-time switch whose whole purpose is that different processes may resolve
differently*; the thing that must match across frontends is the **gated behavior**, which
lives wherever it already lives. Report A's application of the litmus test is a
misclassification.

**Decision:** Python-only in v1, behind a narrow `FeatureFlagResolver` interface. Promote to
`sase_core::feature_flags` on one concrete trigger: a non-Python frontend (web, editor, a
standalone Rust process) must resolve a flag *independently* rather than receive a resolved
snapshot. That is a fact to wait for, not a forecast.

### 2.2 Expiry trigger: beads **and** a threshold — the dichotomy is false

This is the most consequential disagreement, and **neither report is right alone**.

Report B's core proposal — key every flag to a bead, hard-fail when the bead closes while the
flag survives, modeled on `symvision --epic-symbol` — has a **self-defeating flaw**. The only
event that trips the lint is *someone closing the bead*, and nobody has any incentive to close
a bead whose entire content is "remove this flag" while the flag still exists. A flag whose
bead stays `open` forever **never trips anything**. `--epic-symbol` escapes this only because
the epic bead has a *forced* close: the land agent must close it to finish the epic
(`sase/memory/sase_beads.md`: "Never close the parent epic bead; its land agent does that").
A standalone flag has no such deadline.

Report B also cites the 2026-07-11 `backcompat_lifecycle_governance` research as authority for
"beads, not dates" — but that report actually recommends **both**:

> `# BACKCOMPAT[bd-1234]: since=v0.11.0 remove_by=2026-10-15/v0.14.0 …`
> "`remove_by` carries **both** a date and a release; the shim is removal-due only when both
> have passed."
> "Removal thresholds need the later of a calendar duration **and** a release boundary, not
> either alone."

B read the velocity argument (which says *dates alone* are badly calibrated — SASE went
v0.2.0→v0.10.0 in three weeks, and v0.10.x→v0.16.0 in the six weeks since) as an argument
against dates entirely. It is not. It is an argument against *dates alone*.

**Resolution — the two do different jobs:**

| Mechanism | Job |
| --- | --- |
| Bead ID | Identity, ownership, triage, and the *work item* that executes deletion |
| `remove_by` = date **and** release | The **due signal** — what makes an untouched flag start failing |
| Closed bead + surviving flag | The **integrity check** — you cannot mark the work done and keep the flag |

Both directions are needed. Bead-only never fires; date-only has no owner and no work item.

### 2.3 Key the flag to a **removal** bead, not the implementation or epic bead

Report B's rule 2 says "an epic's land agent cannot close the epic bead while its WIP flag
survives, so flag removal becomes part of landing." That is **internally inconsistent with B's
own §5**, which says a WIP flag is justified "most often when an epic spans a release
boundary." A release-spanning epic *must* land with its flag still off — but its land agent
*must* close the epic bead to land. Under B's rule, that combination is unlandable.

The same bug hits the beta case, which B ranks highest: the bead "add feature X" naturally
closes when X ships behind the flag, months before the flag is removed — so the flag becomes a
hard lint error the moment it starts being useful.

**Fix:** the flag's bead is a **dedicated removal task bead** — `"remove feature flag <key> and
the losing branch"` — created in the same change that introduces the flag, never the
implementation or epic bead. Then every case works:

- Flag added → removal bead created (`open`) → lint passes.
- Epic/implementation bead closes normally → flag unaffected.
- `remove_by` approaches → bead flips `ready` → raises a `TaskTriage` gate → owner schedules it.
- `remove_by` passes → lint warns, then hard-fails.
- Flag removed in the change that closes the removal bead → lint passes.
- Removal bead closed with the flag still present → hard fail.

This composes with existing machinery rather than forking it: removal beads go through
`/sase_new_task` (semantic-duplicate check, intentional `--size`), surface in `sase bead ready`,
and get triaged like any other work. It also matches what the backcompat report independently
concluded: "The removal bead is created in the same change that adds the shim."

### 2.4 Schema shape: generated closed `properties` **plus** open `additionalProperties`

**Report B is fully correct here, verified in current core.** This is the strongest single
technical finding in either report.

`sase_core/src/config/schema.rs`:

```rust
/// Order matters: a node with named `properties` is always a closed object
/// container; otherwise an object-typed node is an open `"map"` ...
fn classify(types: &[String], has_props: bool) -> String {
    if has_props { return "object".to_string(); }          // :103-106
    if types.iter().any(|t| t == "object") { return "map".to_string(); }
    ...
}
```

`flatten()` recurses into `properties` whenever `kind == "object"` (`:91-96`), and
`additional_properties_allowed` is false **only** for the literal `additionalProperties: false`
(`:60-63`). The module docstring is explicit: "open objects (`additionalProperties` is a
schema) become `"map"` leaves whose user-defined keys are not enumerated" (`:5-7`).

So report A's open `feature_flags:` map renders in Config Center as **one opaque row**. The
hybrid gets per-flag rows, descriptions, defaults, `deprecated`/`deprecated_replacement`
markers (`schema.rs:80-88`), and full provenance from the existing `config_inventory` contract
— **with zero Rust changes** — while unknown keys still validate:

```jsonc
"feature_flags": {
  "type": "object",
  "description": "Opt-in switches for beta and in-progress SASE behavior.",
  "properties": {                                   // GENERATED from the registry
    "incremental_perf_refresh": {
      "type": "boolean", "default": false,
      "description": "Beta: incremental Perf view refresh. Removal: sase-xx."
    }
  },
  "additionalProperties": { "type": "boolean" }     // tolerate removed/downgraded keys
}
```

**But add report A's corrective, which B omits and which matters:** nothing schema-validates
ordinary loaded config layers at process startup. `config_validate` runs on *candidate merged
config* during Config Center edit planning (`config/mod.rs:1-16`); ordinary loads do not
`jsonschema`-validate, which is why domain loaders like `config/file_hooks.py` diagnose their
own unknown fields. The generated schema buys **Config Center rows + edit-time validation**,
not startup validation. The runtime resolver must still validate keys, types, and scope itself.
The two are complementary, not alternatives — a point neither report states cleanly.

Generation also settles by construction what both reports assert by fiat ("the default lives in
the registry, not `default_config.yml`). That convention is now evidenced: **14 of the schema's
44 top-level keys have no `default_config.yml` entry** (`artifact_refs`, `github_orgs`, `id`,
`mentor_profiles`, `metahooks`, `timezone`, …). Adding `feature_flags` to the schema with
registry-owned defaults follows existing precedent and does not conflict with the `CLAUDE.md`
default-config gotcha, which is about keymaps and ordinary settings.

### 2.5 Use-case ranking: B's order is right; its epic argument needs a qualifier

Report A treats the three uses as coequal. Report B ranks them beta ≫ deprecation > epic WIP.
**B's ranking is right, and I confirm both of its supporting findings — with one correction.**

*Deprecation is genuinely half-solved.* `config/layers.py` carries a real three-stage ladder:
`UNSUPPORTED_TOP_LEVEL_KEYS` (3 keys), `DEPRECATED_TOP_LEVEL_KEYS` (8 keys → replacement),
`RETIRED_SDD_SELECTOR_KEYS`, with `ConfigLayer.unsupported_keys/deprecated_keys/retired_keys`
surfaced non-fatally through `sase config layers` and `sase doctor`, plus 12 `"deprecated": true`
schema fields and `deprecated_replacement` plumbed through core. Report A never mentions this
and proposes a parallel `sunset` lifecycle — which would give SASE two deprecation systems that
disagree. **Extend the ladder; do not fork it.**

*Epic WIP is the weakest case — but B overstates why.* B asserts "epics land as one Patch."
That is **conditional, not universal**: `bead/cli_work_handler.py:236-247` resolves a
`PatchLaunchContext` only `if issue.changespec_name`; otherwise it falls back to
`resolve_vcs_launch_context()` and phase segments target the project ref directly. So:

- **Patch-scoped epic** → accumulates on a Patch and lands once → B's argument holds, a WIP
  flag is usually unnecessary, and the real epic pain (phase *k* adds a public symbol only
  phase *k+1* consumes) is lint-shaped and already handled by `symvision --epic-symbol`.
- **Non-Patch epic, or an epic spanning a release** → phases reach the default branch
  incrementally → a WIP flag has genuine value.

The practical rule: **reach for `--epic-symbol` first; add a `wip` flag only when a phase lands
*user-reachable* behavior that must not be reachable yet.**

## 3. Findings neither report had

### 3.1 Child-process propagation is free — and that is also a hazard

Both reports recommend forwarding the snapshot to child processes; neither verified it was
possible. It is, at zero cost: SASE builds child environments with `os.environ.copy()` at
**15 spawn sites** — `procs/spawn.py:106`, `procs/supervisor.py:350`,
`procs/legacy_supervisor.py:170`, `monitor/spawn.py:100`, `monitor/supervise.py:187`,
`agent_clis/runner.py:84`, `main/axe_handler.py:219`, `llm_provider/{codex,agy,muse}.py`,
`file_hooks/runner.py:170`, `xprompt/workflow_executor_steps_script.py:103`, and others.
There is no allowlist to extend. `SASE_FEATURE_FLAGS` inherits automatically.

The hazard is the same fact: a flag exported once leaks into **every** descendant, including
detached procs and monitors that outlive the shell that set it. Two consequences for the design:

- The parent should re-encode the **resolved snapshot**, not pass raw input through, so a child
  cannot re-resolve against a different project's config mid-operation.
- `sase config flags` must show `env` provenance prominently; an inherited flag in a
  long-running proc is otherwise invisible and effectively unfalsifiable.

### 3.2 The ad-hoc env-gate problem is worse than reported

Report B found ~10 gates in three parsing conventions. At `30c9ba23b` there are **at least
five incompatible conventions**:

| Convention | Examples |
| --- | --- |
| any non-empty value | `SASE_DISABLE_PLUGINS` (5 sites), `SASE_DISABLE_PRETTIER`, `SASE_DISABLE_COMMIT_STOP_HOOK`, `SASE_DISABLE_PLUGIN_FILE_HOOKS`, `SASE_AGENT_AUTO_APPROVE`, `SASE_AGENT_AUTO_DISMISS` |
| `== "1"` | `SASE_GIT_PRE_ALLOCATED`, `SASE_TOOL_LOG_FULL`, `SASE_CODER_INHERIT_PLANNER_CHAT`, `SASE_ACE_DEBUG_LEAKS` |
| `{"1","true","yes","on"}` | two independent `_TRUTHY` definitions (`agent/launch_timing.py:17`, `ace/tui/util/_stall_watchdog_config.py:30`) plus ~4 inline copies of the same set literal |
| `{"1","true","yes"}` (no `on`) | `main/plan_inventory_collectors.py:302` |
| `{"1","true","yes","on","soft"}` | `ace/tui/widgets/prompt_completion.py:353` |

`ace/tui/bindings.py:257` still evaluates its gate at **module import time** — the exact
anti-pattern the snapshot rule must forbid, and a ready-made cautionary example to cite in the
design doc. The "do nothing, keep using env vars" option is not hypothetical; it is the status
quo, and it has already produced the inconsistency a registry prevents.

### 3.3 `symvision` is a third-party package — copy the pattern, not the code

Report B repeatedly proposes building "on" `symvision --epic-symbol`. `symvision` is a
**published external dependency** (`pyproject.toml:60`: `symvision>=0.1.0,<0.2.0`), and
`sase/memory/symvision.md` is explicit: "Do not patch the installed package or recreate a
vendored linter." SASE cannot extend it. What is reusable is (a) the *loop* — an in-tree
temporary allowance keyed to a bead, checked against live bead status, self-cleaning — and
(b) the concrete CI handshake, already proven in `Justfile:303-304`:

```make
SASE_SYMVISION_BEAD_STATUS_ONLY=1 BD_COMMAND=tools/sase_bead {{ venv_bin }}/symvision src/sase …
```

`tools/sase_bead` is a local shim with retries, designed for exactly this. Also worth knowing:
there are currently **zero** `--epic-symbol` entries in the Justfile. The pattern is documented
and proven-by-design, not currently load-bearing — a mild caveat on B's "working, in-production"
framing.

The new check is an ordinary `tools/` script, matching `tools/check_test_wait_helpers`,
`tools/validate_changelog`, and `tools/audit_patch_stitch_terminology`: one script, one
`_lint-flags` recipe, one line each in `lint`, `check`, and `check-full`.

### 3.4 CLI surface: `sase config flags`, not `sase feature`

The reports disagree (A: a new `sase feature` group; B: `sase config flags`). Evidence favors B:

- `sase config` currently has exactly `{init, layers, mentor-match, show}` — and `layers`
  already reports per-layer deprecated/unsupported/retired keys, which is the same view.
- `sase doctor` check IDs are dotted and domain-namespaced: `config.repos`,
  `config.external_mirror`, `config.model_xprompts`, `llm.registry`, `axe.chops`. So
  `sase doctor -C config.feature_flags` is idiomatic **and** keeps command and check ID
  coherent — which a top-level `sase feature` noun would not.
- `sase/memory/cli_rules.md`: a group with an exact `list` child defaults to it bare, options
  must never be required, every public long option needs a short alias, subcommands stay
  alphabetically sorted.

### 3.5 No prior beads exist

`sase bead search` finds no beads for "feature flag" or "backcompat". Both this work and the
2026-07-11 backcompat governance design are unstarted greenfield — and `just lint`'s nine
stages (ruff, mypy, pyscripts, test-waits, changelog, patch-stitch-terminology, symvision,
toobig, keep-sorted) confirm `_lint-backcompat` was never built. **These two designs should
share one linter**, not ship two bead-aware expiry checkers a quarter apart.

## 4. Recommended design

### 4.1 Registry

```python
@dataclass(frozen=True)
class FeatureFlagDefinition:
    key: FeatureFlag                              # typed enum, not a string
    kind: Literal["beta", "wip", "sunset", "ops"]
    description: str
    default: bool
    scope: Literal["global", "project"]
    removal_bead: str | None      # required for beta/wip/sunset; None only for ops
    remove_by: RemoveBy | None    # date AND release; required with removal_bead
    rationale: str                # required when removal_bead is None
```

`removal_bead` + `remove_by` replaces report A's `owner`/`introduced_on`/`review_on` triple and
report B's bare `bead`. The introduction date is recoverable from git; the owner is recoverable
from the bead. The registry is an **inventory, not a dependency graph** — no parent flags, no
implied flags, no "enable all experimental" switch.

### 4.2 Resolution

Lowest → highest, mirroring the existing layer chain:

1. registry default
2. `user` (`~/.config/sase/sase.yml`)
3. `overlay:*` machine overlays, in existing order
4. `local` project config — **only** for `scope: project` flags
5. explicit in-process/test override
6. `SASE_FEATURE_FLAGS` — one strict-parsed JSON object of booleans

`plugin:*` deliberately cannot flip first-party defaults. Resolution yields a
`FeatureFlagDecision` (`enabled`, `default`, `source`, `source_detail`, `overridden`) —
diagnostics and repro capture keep the full decision; routing calls `flags.enabled(...)`.
One immutable snapshot per command/app, logged once at startup for the non-default set, and
re-encoded into `SASE_FEATURE_FLAGS` for children (§3.1).

### 4.3 `tools/check_feature_flags` — ship in the same change

Hard-fail when:

1. a `beta`/`wip`/`sunset` definition lacks `removal_bead` or `remove_by`; an `ops` definition
   lacks `rationale`.
2. the removal bead is **missing** from the store, or is **closed while the flag survives**
   (integrity, both directions).
3. `remove_by` has passed on **both** date and release, after a short warn-first grace window.
   Extensions require an evidenced threshold bump in review, never an automatic bump.
4. the generated `feature_flags` schema block does not match the registry.
5. a flag key has no non-test reference (a flag nothing reads is already dead).
6. a `wip`/`beta` flag has no test covering **both** states while both branches exist.
7. a repo-managed config layer overrides an unregistered key.

Rules 1/4/5/7 are pure static checks and can also run under `just validate`, which needs no
bead store. Rules 2/3 need bead status: reuse `BD_COMMAND=tools/sase_bead` +
`SASE_SYMVISION_BEAD_STATUS_ONLY=1`. Deliberately **not** enforced: any rule that changes
runtime behavior by wall clock.

### 4.4 Inspection

- `sase config flags` — key, kind, default, effective value, source layer, scope, removal bead
  + status, `remove_by`, days/releases remaining. Sibling of `sase config layers`.
- `sase doctor -C config.feature_flags` — unknown keys, invalid values, wrong-scope overrides,
  missing/closed removal beads, overdue flags.
- Writes go through existing Config Center YAML edit transactions (provenance, previews,
  chezmoi, conflicts). A `set` wrapper can come later, if ever.

## 5. Lifecycle by use case

**Beta — build this first.** Ship disabled, `kind="beta"`, with a removal bead and a
`remove_by`. Both states tested. Dogfood via a machine overlay, not project-local config, if
ACE is involved. Flip the default in a focused change; remove the flag and the old branch in
the change that closes the removal bead. If users are meant to choose forever, it was never a
flag — promote it to an ordinary config field.

**Deprecation — extend the ladder, don't fork it.** The flag switches *behavior*; the existing
key ladder handles the *config surface*. New behavior lands behind a disabled `sunset` flag →
default flips → old key moves into `DEPRECATED_TOP_LEVEL_KEYS` with its replacement and gets
`"deprecated": true` in the schema → finally flag, override, and old implementation are removed
together and the key graduates to `UNSUPPORTED`. Two mechanisms, one sequence. Wire and
persisted-format compatibility remain an independent expand-and-contract problem.

**Epic / WIP — last resort.** Reach for `--epic-symbol` first. Add a `wip` flag only when a
phase lands *user-reachable* behavior that must not be reachable yet — most often a non-Patch
epic or one spanning a release boundary (§2.5). One flag per coherent routing decision, never
one per phase. The removal bead is a task bead, **not** the epic bead (§2.3).

**Ops — rare.** Only for a genuine supported degradation path, with a written rationale for why
it is permanent. Both states stay in the test matrix forever. A beta flag does not become
permanent merely because it *could* serve as a kill switch.

## 6. Implementation slices

1. **Registry + resolver + generated schema + snapshot + `tools/check_feature_flags`** — one
   change, Python only. Config Center provenance works from day one via existing Rust (§2.4).
   Shipping the linter separately is how 235 files of unmarked backcompat happened.
2. **First consumer.** Report A proposes `agents_daemon_reads_enabled()` — still an
   unconditional `return False` in `ace/tui/data_providers/_settings.py`, i.e. a dead seam for
   reverted work, which proves nothing about a live toggle. Report B says "a live beta
   feature" without naming one. **Better: migrate an existing ad-hoc gate.** Convert
   `SASE_DISABLE_PLUGINS` (5 sites, one convention, a `disable_*` double negative) to a
   registered positive `plugins_enabled` flag, keeping the old env name working through the
   deprecation ladder. That gives a real consumer with real users, exercises both states, pays
   down §3.2 debt immediately, and is itself a worked example of use case #3.
3. **`sase config flags` + `sase doctor -C config.feature_flags`.**
4. **Normalize the remaining env gates** one at a time, starting with the import-time
   `SASE_ACE_DEBUG_LEAKS` (`bindings.py:257`).
5. **Only on demand:** promote the resolver to `sase_core::feature_flags` (trigger in §2.1),
   plugin-namespaced definitions, or an OpenFeature adapter. None gates v1.

**Sequencing note.** Slice 1's linter and the unimplemented `_lint-backcompat`
(`../backcompat_lifecycle_governance/`) are the same machine: an in-tree structured marker, a
removal bead, a date+release threshold, a bead-status handshake. Build one bead-aware expiry
checker with two marker sources, not two linters.

## 7. Risks

| Risk | Mitigation |
| --- | --- |
| Flags accumulate anyway | `remove_by` (date **and** release) is the due signal; the removal bead flips `ready` and raises a `TaskTriage` gate; a closed bead with a surviving flag hard-fails |
| Bead never closes, so bead-only enforcement never fires (§2.2) | precisely why `remove_by` is not optional |
| Release-spanning WIP flag becomes unlandable (§2.3) | key to a dedicated removal task bead, never the epic or implementation bead |
| Two deprecation systems disagree | flags own *behavior*; the `DEPRECATED`/`UNSUPPORTED`/`RETIRED` ladder owns the *config surface*; §5 defines the single sequence |
| Removed flag breaks a downgraded install | generated `properties` + `additionalProperties: {type: boolean}`; unknown file keys warn and are ignored |
| Generated schema drifts from the registry | lint rule 4, beside existing `keep-sorted` and changelog generation checks |
| Startup never schema-validates config (§2.4) | the runtime resolver validates keys, types, and scope itself; Config Center validation is edit-time only |
| Env flag leaks into detached procs/monitors (§3.1) | forward the *resolved* snapshot; surface `env` provenance in `sase config flags` |
| ACE resolves differently from the CLI | explicit `global`/`project` scope; project overrides are invisible to ACE by design |
| Import-time evaluation returns | snapshot-at-boundary rule; `bindings.py:257` is the cautionary example and an early migration target |
| Combinations explode | boolean-only, no dependencies, routing at the edge, per-flag tests — no Cartesian matrix |
| It regrows into the reverted daemon rollout registry (`5a65fa4fc`) | feature-specific capability, parity, perf, and fallback gates stay out of the generic flag record |

## Sources

**Verified this session at `30c9ba23b`:** `config/layers.py` (ladder :22-45, `ConfigLayer`
:69-82) · `config/core.py:101` + `main/ace_handler.py:158-162` · `config/sase.schema.json`
(root `additionalProperties: false`, 44 props, 12 `deprecated: true`, `xprompt_aliases` open-map
precedent) · `default_config.yml` (30 keys; 14 schema keys have no bundled default) ·
`bead/cli_work_handler.py:231-247` + `bead/work.py:356-397` (Patch mode is conditional) ·
`ace/tui/data_providers/_settings.py` · `ace/tui/bindings.py:257` · env-gate sites and
`_TRUTHY` variants in §3.2 · 15 `os.environ.copy()` spawn sites · `Justfile:259-343`
(9 lint stages, no `_lint-backcompat`), `:303-304`, `:584-620`, `:730-736` · `pyproject.toml:46,60`
+ core-floor ratchet history · `main/validate_handler.py` · `doctor/checks_*.py` (`-C` IDs) ·
`sase config -h` · `sase bead search` · **sase-core:** `config/mod.rs:1-17`,
`config/schema.rs:1-7,55-96,99-117` · **memory:** `symvision.md`, `sase_beads.md`, `cli_rules.md`

**Prior research:** [`__a`](feature_flag_lifecycle_governance__a.md) ·
[`__b`](feature_flag_lifecycle_governance__b.md) ·
[`../feature_flag_architecture.md`](../feature_flag_architecture.md) ·
[`../../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md`](../../backcompat_lifecycle_governance/backcompat_lifecycle_governance.md)

**External** (carried from `__a`/`__b`; not re-verified here): Fowler/Hodgson
[Feature Toggles](https://martinfowler.com/articles/feature-toggles.html) ·
[GitLab feature flags](https://docs.gitlab.com/development/feature_flags/) and
[cleanup controls](https://docs.gitlab.com/development/feature_flags/controls/) (`wip`/`beta`
types; every surviving flag expands the behavioral state space) ·
[Kubernetes feature-gate lifecycle](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
(alpha → beta → GA → gate removed; gates are not long-term APIs) ·
[Unleash lifecycle](https://docs.getunleash.io/concepts/feature-flags) (types carry expected
lifetimes; flags go stale) · [OpenFeature evaluation](https://openfeature.dev/specification/sections/flag-evaluation/)
and [provider](https://openfeature.dev/specification/sections/providers/) specs ·
[LaunchDarkly code references](https://launchdarkly.com/docs/home/flags/code-references) ·
[Cargo features](https://doc.rust-lang.org/cargo/reference/features.html)

## Recommended solution

**Ship a Python-only, boolean-only feature-flag registry in which every temporary flag carries
both a dedicated removal bead and a `remove_by` date+release threshold, whose keys are generated
into the config JSON Schema, enforced by `tools/check_feature_flags` in the same change.**

1. **Registry** (Python): `key` (typed enum), `kind` ∈ {`beta`,`wip`,`sunset`,`ops`},
   `description`, `default`, `scope` ∈ {`global`,`project`}, `removal_bead` + `remove_by`
   (or a written `rationale` for permanent `ops`). Inventory only — no flag dependencies.
2. **Expiry = bead + threshold.** The bead is a *dedicated removal task bead* created with the
   flag — never the epic or implementation bead, which would make release-spanning flags
   unlandable. The bead gives identity, ownership, and a triageable work item; `remove_by`
   (later of date and release) gives the due signal a bead alone can never provide. A closed
   removal bead with a surviving flag is a hard error, both directions.
3. **Generate `feature_flags.<key>` schema properties** from the registry, keeping
   `additionalProperties: {type: boolean}` for tolerance — per-flag Config Center rows,
   defaults, and provenance with **no `sase-core` change** (verified in `schema.rs`). The
   runtime resolver still validates keys, types, and scope itself, because nothing
   schema-validates config at startup.
4. **Resolve** registry default → `user` → `overlay:*` → `local` (project-scope only) → test
   override → strict `SASE_FEATURE_FLAGS` JSON. One immutable snapshot per process, never at
   import time, re-encoded (resolved, not raw) for child procs — which inherit it for free via
   the existing `os.environ.copy()` spawn paths.
5. **Enforce in one change** with `tools/check_feature_flags` as a tenth `just lint` stage,
   reusing the proven `BD_COMMAND=tools/sase_bead` + `SASE_SYMVISION_BEAD_STATUS_ONLY=1`
   handshake. Build it to also serve the unimplemented `_lint-backcompat` design — one
   bead-aware expiry checker, two marker sources.
6. **Keep the resolver in Python** behind a narrow seam. Not because a core round trip is
   expensive (the floor ratcheted ~20 times in the last 8 days), but because no Rust path
   resolves a flag and core config already carries a duplicated-`_deep_merge`-with-parity-tests
   burden. Promote to `sase_core::feature_flags` only when a non-Python frontend must resolve
   independently.
7. **Order the work beta → deprecation → epic.** Prove it by converting `SASE_DISABLE_PLUGINS`
   into a registered positive `plugins_enabled` flag with the old env name deprecated through
   the existing ladder — a live consumer, both states exercised, and existing debt repaid.
   Let deprecation extend the `DEPRECATED`/`UNSUPPORTED`/`RETIRED` ladder rather than fork it,
   and reach for `symvision --epic-symbol` before any `wip` flag.

The difference from a conventional flag system is deliberate. SASE does not need evaluation
machinery; it needs a mechanism that cannot be ignored. Bead identity supplies the owner and
the work item, the `remove_by` threshold supplies the deadline, and shipping the linter in the
same change supplies the teeth. Any one of the three alone is how flag debt happens.
