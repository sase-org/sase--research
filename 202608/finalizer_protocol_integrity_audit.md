---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
---

# Pluggable Finalizer Protocol Integrity Audit

## Research question

After `sase-rn` introduced host-owned pluggable finalizers and `sase-rr` retired the
beta/legacy controller split, what correctness bugs remain in the current implementation,
and which extensions would make finalizers substantially more useful without weakening
their trust boundary?

This is a post-retirement implementation audit, not a restatement of the original design.
It extends the existing
`research:202608/finalizer_bugs_and_capability_upgrades.md` with direct adversarial probes
of the sealed-plan boundary, aggregation, retry policy, plugin identity, evidence
retention, and subprocess limits.

## Snapshot and method

The audited primary revision is `sase@28009002d` (`fix(finalizers): prove live e2e
acceptance and validate external payloads`). The shared Rust implementation is
`sase-core@937a5d2c5cdb86a3ebed13dc4d584ac7be603bbe`; the configured linked checkout and
an independently opened checkout were identical at that revision.

Evidence came from:

- the `sase-rn` and `sase-rr` epic beads, all of their phase notes, and the associated
  plans;
- the Python plan, config, provider discovery, declaration, executor, controller,
  commit, repair, reconciliation, SDK, worker, artifact, and CLI modules;
- the Rust finalizer wire, selection, submission, digest, and outcome modules;
- finalizer documentation and all focused finalizer tests; and
- small read-only probes against the installed current tree.

After rebuilding the workspace binding from the current linked core, the focused suite
passed:

```text
59 passed in 31.53s
```

The passing suite is meaningful: clean/dirty completion, `%final:none`, external and
command providers, refusal, stale declaration recovery, later dirt, conflict resume, and
handoff bypass all have coverage. The findings below are mostly invariant gaps that the
current scenarios do not assert.

## Executive assessment

The finalizer architecture is sound in shape: selection is configuration-derived,
declarations are turn-bound, providers execute out of process, commit uses opaque
host-issued repository obligations, and the controller is cycle-bounded and fail-closed.
The recent `sase-rr.4` work also fixed two important external-provider defects: submitted
payloads are now provider-validated, and accepted payloads plus host obligations reach
the provider request.

However, one critical trust-boundary bug remains: the controller treats the
model-writable `finalizer_plan.json` artifact as the authority for which instances run.
The artifact contains both the plan and its claimed digest, and the controller neither
validates the digest nor compares the sealed entry policy/configuration to the current
trusted configuration. A direct probe replaced the artifact with an empty plan and the
invalid digest `not-a-valid-digest`; the controller accepted it and wrote a successful
zero-instance result. That contradicts the protocol's central “host-owned sealed plan”
claim.

The next cluster is extension correctness. `max_attempts` is enforced for
`builtin@command` but ignored for plugins and not used as an instance budget by commit.
External providers may return `skipped`; the controller rejects that as non-success,
while Rust aggregation converts an all-skipped result to aggregate success. Plugin
distribution names are emitted in raw packaging form even though the Rust wire requires
lowercase slugs and the worker later uses exact string comparison. Provider output caps
are checked only after `communicate()` has already buffered the entire stream.

The most valuable capability improvement is therefore a provider-spec handshake at
plan/context time, after the integrity boundary is repaired. The Rust wire already has
capabilities and schema digests, but Python currently hardcodes capabilities and forces
every external instance to require an empty `{}` submission. Sealing a real provider
description would enable passive audits, typed declarations, explicit mutation and
verification contracts, and safe reactivation after another finalizer changes state.

## Current contract and trust boundary

The intended lifecycle has four useful boundaries:

1. **Plan:** trusted merged configuration and `%final` selection resolve an ordered,
   policy-bearing plan before the main model turn.
2. **Declare:** when current host facts require input, the agent submits one atomic
   envelope bound to run, agent, turn nonce, plan digest, and context digest.
3. **Execute:** built-ins or an isolated plugin worker perform bounded work using trusted
   configuration and accepted input.
4. **Verify/reconcile:** the host recomputes obligations, preserves evidence, and runs to
   a bounded fixed point before deciding overall success.

The agent may supply judgment such as a Conventional Commit message. It must not be able
to remove a required finalizer, replace its provider, change an attempt budget, or alter
the executable configuration. A digest is useful only if its expected value is held
outside the object being checked.

## Confirmed bugs

### F-01 — Critical: the “sealed” plan is controlled by a writable artifact

`resolve_and_persist_finalizer_plan()` writes `finalizer_plan.json` under the run artifact
directory. At completion, `controller._selected_entries()` loads that file, silently
skips malformed entries, sorts the survivors, and accepts any string in `plan_digest`.
`declaration.load_finalizer_plan()` reconstructs Python wire records but does not
independently establish that the plan is the one resolved by the host before the turn.

Execution then reloads live merged configuration by `instance_id`. It never compares the
plan entry's `provider_ref`, `config_digest`, provenance, or policy against that live
instance. This creates two related failure modes:

- an agent or tool can remove plan entries—including required ones—and finish with no
  finalizers; and
- configuration can drift during a long turn, so the executor runs a different command,
  provider, or policy than the one whose digest was shown to the model.

The direct empty-plan probe completed with:

```text
invalid empty plan digest accepted by controller: status=success cycles=0 instances=[]
```

**Fix:** keep the authoritative expected plan digest in runner-owned state that is not
agent-writable (or authenticate the artifact with a runner-held key). At context publish
and again before each dispatch, validate the full plan structure and recompute its
digest. Compare every selected entry's provider reference, configuration digest,
provenance/version digest, dependency order, and policy with the sealed executor
snapshot. Corruption or drift must produce a durable `plan_integrity_failed` result,
never an empty success.

**Regression tests:** mutate, truncate, reorder, add, and remove entries after plan
resolution; alter `provider_ref`, `max_attempts`, and command configuration; supply an
invalid digest; verify every case fails before provider execution. Include a required
instance removal case.

### F-02 — High: attempt policy is not a protocol-wide budget

`builtin@command` loops up to `max_attempts`. `execute_plugin_finalizer()` always performs
one `describe → validate → execute → verify` sequence. The commit executor does not
consume the configured instance limit and can be invoked again by controller cycles.
This disagrees with configuration, the Rust policy wire, CLI output, and documentation,
which present `max_attempts` as an instance property. A probe configured a plugin with
`max_attempts=3`; it executed once and returned failure.

There are also multiple incomparable budgets: controller cycles, declaration recovery,
conflict repair, command attempts, and implicit commit reactivation. Without a precise
definition, operators cannot know whether `max_attempts: 2` means two provider
subprocesses, two whole operation pipelines, two repository stitches, or two controller
cycles.

**Fix:** define one host-owned whole-instance attempt ledger. Consume an attempt before a
mutating `execute`, classify failures as retryable/non-retryable, and enforce the same
limit centrally for built-ins and plugins. Keep declaration-recovery and human/agent
conflict-repair budgets separately named. A provider must not decide its own retry count.

### F-03 — High: `skipped` has contradictory meanings

External execute validation permits `success`, `failed`, or `skipped`. The controller
raises for every status other than `success`, so `skipped` fails the run. If the result
reaches Rust aggregation, however, an all-skipped set aggregates to `success`:

```text
skipped aggregate: instance=skipped aggregate=success
```

`_write_aggregate_result()` replaces its explicit failure status with the aggregate
status, so a failed controller path can leave `finalizer_result.json` claiming success.
That makes the exit path and durable evidence disagree.

**Fix:** choose one semantic. The safer current contract is that only the host may mark
an untriggered instance skipped; reject provider-authored `skipped`. If provider skip is
needed later, require a reason and an independently verified trigger result. Aggregation
must never overwrite a controller failure with success.

### F-04 — High: installed plugin names can be impossible to configure or execute

Provider discovery constructs `provider_ref` from the distribution metadata name
verbatim. Python package names are case-insensitive and treat hyphens, underscores, and
dots as equivalent after normalization. The Rust provider-ref validator instead requires
lowercase slug segments, while `worker_entry._find_entry_point()` compares the configured
package and installed metadata name with exact string equality.

A synthetic installed distribution named `Example_Finalizers` was discovered as
`Example_Finalizers@audit`; the Rust validator rejected that exact discovered reference:

```text
discovered provider ref: Example_Finalizers@audit
Rust validation: ValueError provider_ref segments must be lowercase slugs
```

Even a user who guesses the normalized config spelling can pass discovery diagnosis and
then fail the worker's exact lookup.

**Fix:** use the existing distribution-name normalizer at discovery, configuration,
required-plugin matching, duplicate detection, and worker lookup. Store the raw
distribution name only for display/provenance. Add mixed-case and `-`/`_` equivalence
tests around a real entry point.

### F-05 — High: output limits do not bound memory use

The external worker path uses `subprocess.Popen(...).communicate(...)` and checks byte
limits only after stdout/stderr are fully resident in memory. The advertised 1 MiB caps
therefore limit accepted evidence, not resource consumption. A buggy or hostile trusted
plugin can exhaust the host before SASE reports `provider_output_limit`. Command and
conflict-repair subprocesses deserve the same audit; the stitch repair path has neither
an explicit timeout nor a streaming cap at this layer.

**Fix:** incrementally drain both pipes, stop retaining bytes at the cap, terminate the
process group as soon as either limit is exceeded, and preserve a bounded diagnostic
tail. Make limits and timeouts host-configurable within hard global maxima.

### F-06 — Medium-high: reactivation loses evidence and overwrites artifacts

`controller._remember_result()` appends and renumbers attempts from a prior invocation,
but replaces the previous result's evidence and diagnostics with those from the newest
invocation. A direct probe produced:

```text
merged attempts: [1, 2]
merged evidence: ['second']
merged diagnostic codes: []
```

Provider artifact names are operation-based (`validate.stdout`, `execute.stdout`), so a
later validation or retry overwrites earlier material. Commit attempt filenames restart
inside a new controller invocation. Conflict repair may also succeed after an agent
repair without adding a success attempt to the returned ledger.

**Fix:** allocate monotonic attempt IDs in the controller, append immutable per-attempt
artifacts, and merge evidence/diagnostics with explicit attempt association. Strengthen
Rust result validation to require unique increasing attempt numbers and status/attempt
coherence.

### F-07 — Medium: the model controls multi-repository commit order

The host publishes an ordered dirty-repository context, but
`commit._dirty_repos_in_context_order()` iterates the submitted decision mapping. JSON
object insertion order is therefore the execution order. A probe with host order
`[main, research]` and a reversed manifest yielded execution order
`[research, main]`.

This is not path injection—the repo IDs remain validated—but it contradicts deterministic
host-owned ordering and can change cross-repository outcomes.

**Fix:** iterate host context obligations and look up each decision by opaque ID. Treat
the manifest as a map of decisions, never as an ordering mechanism.

### F-08 — Medium: the SDK masks real provider `TypeError`s and may invoke twice

`sdk.dispatch_provider_request()` accepts either a callable provider or a no-argument
factory. It distinguishes them by calling `provider(request)` and catching every
`TypeError`; a real `TypeError` inside provider logic is interpreted as “this must be a
factory,” and the callable is invoked again with no arguments. The probe recorded calls
with the request and then `None`, and surfaced an unrelated “does not implement
operation” error instead of the original exception.

**Fix:** make factory-vs-callable shape explicit in the entry-point contract, or inspect
the signature before invocation. Never use a runtime exception from provider code as
shape detection.

### F-09 — Medium: provider requests are not bound to the real selection

`_provider_request()` derives `selected` from current configuration defaults, not the
resolved plan. The controller also constructs its execution context without the current
run and agent identifiers, leaving both `None` in worker requests. A `%final` override
can therefore execute `audit` while telling it that only default `commit` was selected.

This was directly observed:

```text
provider request selected=[]
```

for a selected non-default provider.

**Fix:** construct worker requests only from the authenticated sealed plan and accepted
context: selected IDs in resolved order, run ID, agent ID, turn nonce, plan/context
digests, provider-spec digest, accepted payload, and host-issued obligations.

### F-10 — Medium: context publication and submission have a stale-success race

Submission holds the submission lock while validating and replacing the accepted
manifest, but context publication uses a separate context lock. A concurrent republish
can make an otherwise valid submission stale immediately after `submit` reports success.
Later execution fails closed, so this is not a bypass; it is a misleading success and an
avoidable recovery turn.

The commit executor also returns early success when the repository is already clean at
execution time. That path should prove why accepted dirty obligations disappeared rather
than assuming disappearance is success.

**Fix:** define a single lock order for context/submission, re-read the current context
under that lock immediately before atomic replacement, and verify accepted obligation
coverage even on clean transitions. Add interleaving tests rather than timing sleeps.

## Capability improvements

### 1. Seal a real provider description at plan/context time

The Rust `FinalizerProviderSpecWire` already names provider version, capabilities,
configuration schema digest, submission schema digest, result schema digest, and
provenance. Python discovery instead hardcodes a capability tuple, while execution calls
`describe` only after the agent has already been forced to submit `{}`.

Run `describe` in an isolated, read-only planning worker before the main turn (and in a
deep doctor command). Validate and seal the returned spec with the selected plan. Use it
to decide:

- whether an instance requires agent submission;
- the typed payload template/schema shown by `/sase_final`;
- whether it may mutate repository state;
- whether a separate verify operation is required;
- which host facts/obligation kinds it may receive; and
- its timeout/output needs within global policy.

This turns external finalizers from a fixed four-method callback into honest completion
contracts. A passive audit would no longer force a dummy declaration, and a typed
delivery manifest could tell the agent exactly what fields are required.

### 2. Replace `ran_non_commit` with explicit trigger/reactivation semantics

Today only commit can reactivate after later dirt. Every other instance is permanently
suppressed after its first run. Add a small host-evaluated trigger vocabulary such as
`once`, `always`, `dirty_repository`, `changed_paths`, and `provider_requested`, plus a
declared mutation capability. After a mutator succeeds, invalidate and re-evaluate only
dependent checks. Keep the controller's cycle/no-progress caps.

This is necessary for useful compositions such as formatter → check → commit or commit →
artifact reconciliation. Without it, ordering is syntactic but not a fixed-point
contract.

### 3. Add role/xprompt profiles and ship a small trusted portfolio

`%final` is a good override, not an ergonomic default-selection mechanism. Trusted
configuration should support named profiles applied by a role/xprompt before user
selector operations. A practical initial portfolio is:

| Profile | Instances | Purpose |
| --- | --- | --- |
| code/PR/epic | `check → commit` | Run `just check` before final commit. |
| research | `research-doc → commit` | Validate month placement, report structure, sources, and ranked ending. |
| plan | `plan-doc → commit` | Validate frontmatter, phase shape, and portable paths. |
| land | `check → epic-closeout → commit` | Verify symbols, descendants, follow-ups, and plan status. |

Start `check`, `research-doc`, and `plan-doc` as constrained command finalizers where no
agent payload is needed. Do not make `just check` a global default; it is irrelevant and
expensive for read-only or research turns.

### 4. Make `builtin@command` repository-aware without accepting paths

The command finalizer is currently limited to the primary working directory and a fixed
argv. Extend it with closed host-resolved cwd/input policies—such as `primary`, each
opened obligation, `research`, or changed repositories—and provide changed paths and
artifact references through a read-only JSON file or stdin. Never interpolate
model-authored strings into argv, cwd, or environment.

This would cover many high-value checks without requiring plugin packaging, while
preserving the trust boundary.

### 5. Add deep doctor, explain, and replay tools

`sase final doctor` currently proves metadata/config availability, not that a worker can
load or satisfy its contract. Add an opt-in `--deep` mode that launches the isolated
worker for `describe`, validates all advertised schemas/digests, and reports normalized
package identity and effective limits. Add a turn-bound `explain` view showing resolved
order, triggers, attempt budgets, and why submission is or is not required.

For postmortems, provide a non-mutating replay validator over stored plan/context/result
artifacts. It should recompute digests and invariants without re-executing side effects.

## Suggested implementation sequence

Do not start with more provider types. The sequence that contains risk and produces
usable increments is:

1. repair plan authenticity/config drift and add adversarial artifact tests;
2. centralize attempt/status/aggregation semantics and hard resource limits;
3. normalize plugin identity and bind truthful run/plan context to workers;
4. make evidence append-only and host ordering deterministic;
5. seal provider descriptions and add deep doctor;
6. add trigger/reactivation semantics; then
7. ship command-backed profiles before introducing side-effecting external providers.

## Sources

- `bead:sase-rn`, its seven closed phases, and
  `plan:202608/pluggable_finalizers.md`
- `bead:sase-rr`, its four closed phases, and
  `plan:202608/retire_pluggable_finalizers.md`
- `research:202608/finalizer_protocol_and_extensibility/finalizer_protocol_and_extensibility.md`
- `research:202608/finalizer_completion_contracts/finalizer_completion_contracts.md`
- `research:202608/finalizer_bugs_and_capability_upgrades.md`
- Python: `src/sase/finalizers/{plan,config,providers,declaration,executor,controller,commit,commit_repair,reconciliation,artifacts,sdk,worker_entry,cli}.py`
- Rust: `crates/sase_core/src/finalizer/{wire,selection,submission,outcome,digest}.rs`
- Focused finalizer tests in `tests/test_core_finalizer_facade.py`,
  `tests/test_finalizer_declaration_channel.py`, and `tests/test_finalizers_*.py`

## Ranked recommended bug fixes / improvements

Ranked by correctness/security impact first, then ecosystem leverage, then implementation
risk. The first nine are fixes; the remainder are capability work.

| Rank | Kind | Recommendation | Rationale |
| ---: | --- | --- | --- |
| **1** | Critical bug | Anchor the expected plan outside model-writable artifacts; validate/recompute it and reject provider/config/policy drift before context publication and every dispatch. | The current empty-plan probe bypasses every finalizer and still records success, defeating the host-owned protocol. |
| **2** | High bug | Define and centrally enforce whole-instance attempt budgets for commit, command, and plugin providers, with separately named declaration/conflict budgets. | `max_attempts` is currently a public contract that two of three executor classes do not honor consistently. |
| **3** | High bug | Remove provider-authored `skipped` for now and make durable aggregate status unable to overwrite a controller failure. | Current code can fail the run while persisting aggregate success. |
| **4** | High bug | Normalize distribution identities consistently across discovery, config, required-plugin matching, Rust validation, and worker lookup. | Valid installed packages can be undiscoverable or unexecutable solely because of packaging-equivalent spelling. |
| **5** | High bug | Enforce streaming stdout/stderr caps and process-group termination for provider, command, and stitch subprocesses. | Current post-`communicate()` checks do not prevent memory exhaustion. |
| **6** | Medium-high bug | Bind every worker request to authenticated plan/context identity and the real resolved selection. | Plugins currently receive default selection and missing run/agent identity, undermining idempotency and conditional behavior. |
| **7** | Medium-high bug | Preserve immutable, per-attempt evidence/diagnostics with controller-issued monotonic attempt IDs. | Current reactivation erases failure history and can overwrite the artifacts needed to debug it. |
| **8** | Medium bug | Execute repository decisions in host context order, not manifest insertion order; harden context/submission and clean-transition races. | The model should provide decisions, never protocol ordering, and success should correspond to the context actually accepted. |
| **9** | Medium bug | Replace the SDK's `TypeError` callable/factory heuristic with an explicit provider shape. | Real plugin bugs are masked and a callable may be invoked twice. |
| **10** | Highest-leverage improvement | Run isolated `describe` at planning/context time and seal provider version, capabilities, provenance, and schema digests. | Enables optional/passive providers, typed declarations, real mutation/verify contracts, and safer supply-chain diagnostics. |
| **11** | Improvement | Replace `ran_non_commit` with host-evaluated trigger/reactivation semantics tied to declared mutation. | Makes formatter/check/commit and post-commit reconciliation correct fixed-point compositions. |
| **12** | Improvement | Add role/xprompt finalizer profiles and ship command-backed `check`, `research-doc`, `plan-doc`, and closeout instances. | Delivers immediate value without asking users to remember `%final` or requiring immature plugin payloads. |
| **13** | Improvement | Add closed repository-aware cwd/input policies to `builtin@command`. | Makes sidecar and multi-repository checks useful without exposing raw paths or executable interpolation. |
| **14** | Improvement | Add `doctor --deep`, a turn-bound explain view, and non-mutating artifact replay validation. | Makes plugin installation failures and protocol-integrity failures diagnosable before completion is at risk. |
