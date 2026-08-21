---
create_time: 2026-08-21
updated_time: 2026-08-21
status: research
---

# Finalizer Integrity and Capabilities

## Research question

After `sase-rn` introduced host-owned pluggable finalizers and `sase-rr` retired the
beta and legacy controller, which bugs remain, and which improvements would make SASE
finalizers materially more powerful?

## Scope and method

This report consolidates two independent audits:

- `finalizer_integrity_and_capabilities__a.md` (Codex researcher; originally
  `finalizer_protocol_integrity_audit.md`), which emphasized adversarial protocol and
  integrity probes; and
- `finalizer_integrity_and_capabilities__b.md` (Claude researcher; originally
  `finalizer_bugs_and_capability_upgrades.md`), which emphasized plugin usability,
  documentation, tests, and deployable finalizer ideas.

I independently checked both reports against primary HEAD `f1c3555636`. No commit
touching `src/sase/finalizers/`, the focused finalizer tests, or the cited finalizer
documentation has landed since their shared audited snapshot `28009002d`. I also read
the `sase-rn` and `sase-rr` epic beads and inspected the controller, executor,
declaration, SDK, commit ordering, and focused tests. The strongest adversarial audit
ran 59 focused tests successfully and then reproduced uncovered failures with targeted
probes. Thus the findings below are coverage gaps and contract violations, not a claim
that the existing suite is generally unhealthy.

## Executive conclusion

The architecture is promising and the built-in commit path is already strong:
selection is configuration-derived, declarations are turn-bound, repository choices
use opaque host-issued IDs, subprocesses avoid a shell, execution is cycle-bounded,
and reconciliation can reactivate commit after later dirt. Recent `sase-rr` work also
fixed external payload validation/delivery and fakey turn identity; those should not be
re-filed.

The largest remaining problem is more fundamental than plugin ergonomics: the
controller trusts `finalizer_plan.json`, even though it is stored in the agent-writable
artifact directory. It accepts the plan's self-reported digest without recomputing or
checking it against runner-owned state, silently skips malformed entries, and reloads
live configuration without comparing it to the sealed entry. The Codex researcher
replaced the plan with an empty plan and an invalid digest; the controller recorded a
successful zero-finalizer run. Current source still has that path. Until this is fixed,
the protocol's central “host-owned sealed plan” guarantee is not true.

After integrity, the main opportunity is to finish the provider contract. Plugins are
currently told config defaults instead of the resolved selection, receive null run and
agent IDs, always require a declaration containing an empty object, cannot influence
context through `describe`, do not receive a consistently enforced attempt budget, and
cannot compose safely with later mutators. A context-time, sealed provider description
would unlock optional and typed inputs, truthful capabilities, mutation-aware
reactivation, and useful third-party finalizers.

## Confirmed bugs

### 1. The persisted plan is not sealed

`controller._selected_entries()` loads the writable plan artifact, extracts only a few
fields, silently ignores malformed entries, and returns any string as `plan_digest`.
It does not recompute the digest or compare the plan to a runner-owned expectation.
Execution then selects live config by `instance_id` without checking the sealed
provider, config digest, policy, provenance, or dependency order.

Consequences:

- removing required entries can bypass every finalizer and still produce success;
- adding or editing entries can change what the controller attempts; and
- config drift during a long turn can execute a command or provider different from the
  one represented to the model.

Store the authoritative digest or full executor snapshot in runner-owned state (or
authenticate the artifact with a runner-held key). Recompute and validate the complete
plan before context publication and dispatch. Corruption or drift must write a durable
integrity failure, never empty success.

### 2. Attempt policy has no consistent meaning

`builtin@command` loops over `max_attempts`; a plugin performs one operation pipeline;
commit may re-enter across controller cycles without using the instance limit. The
schema, CLI, Rust policy wire, and docs present one instance property, but the three
executor classes implement different budgets.

Define a central whole-instance attempt ledger, consume attempts before mutating
execution, distinguish retryable from terminal failures, and keep declaration recovery,
conflict repair, and controller-cycle limits as separately named budgets.

### 3. `skipped` can fail the run while durable aggregation says success

The external execute wire accepts `skipped`, but the controller treats every status
other than `success` as fatal. Rust aggregation can convert an all-skipped set to
aggregate success, and aggregate writing can overwrite the explicit failure status.
The process outcome and `finalizer_result.json` can therefore disagree.

For now, reserve `skipped` for a host-evaluated untriggered instance. If provider skip
is later allowed, require a reason and host verification. An aggregate must never
overwrite a controller failure with success.

### 4. Worker requests are not bound to the real turn and selection

`run_finalizers()` builds execution context with only artifact directory and plan
digest. Plugin `run_id` and `agent_id` are null, while `selected` is recomputed from
config defaults rather than read from the resolved plan. `%final` additions/removals
are therefore misreported to providers, breaking conditional behavior and reliable
idempotency.

Send authenticated run, agent, turn/context, plan, and resolved-selection identity in
every operation request. This should share the same integrity fix as item 1 rather than
copying more untrusted artifact fields.

### 5. Plugin distribution identity is normalized inconsistently

Discovery preserves raw distribution spelling, Rust requires lowercase slug segments,
and worker lookup compares package names exactly. Python packaging treats case and
hyphen/underscore/dot variants as equivalent. A valid installed distribution such as
`Example_Finalizers` can be discovered under a reference Rust rejects, or pass one
surface and fail execution.

Apply one PEP 503-style normalizer at discovery, configuration, required-plugin
matching, duplicate detection, and worker lookup; retain the raw name only for display
and provenance.

### 6. Output caps do not cap memory

Plugin subprocesses call `communicate()` and check stdout/stderr size afterward. The
nominal 1 MiB caps limit accepted evidence but not buffered memory, so a faulty trusted
plugin can exhaust the host before SASE rejects its output. Stream both pipes, retain a
bounded tail, and terminate the process group immediately at the cap. Audit command and
stitch subprocesses under the same resource policy.

### 7. Reactivation destroys historical evidence

The controller appends renumbered attempts but replaces earlier evidence and
diagnostics with the latest result. Operation-based artifact filenames are also reused,
so retries overwrite prior stdout/stderr. Allocate controller-owned monotonic attempt
IDs and immutable per-attempt artifacts, with evidence and diagnostics associated with
the attempt that produced them.

### 8. Model input controls repository execution order

The host publishes ordered repository obligations, but commit execution iterates the
submitted decision mapping. JSON insertion order can therefore reverse the host order.
Iterate host obligations and look up each decision by opaque ID; the model should
provide decisions, not scheduling.

### 9. Provider dispatch masks real `TypeError`s

The SDK guesses whether a callable is a request handler or a no-argument factory by
calling it with the request and catching any `TypeError`. A `TypeError` thrown inside
real provider logic is mistaken for a factory mismatch, can invoke the provider twice,
and hides the original fault. Require an explicit provider shape or inspect a declared
entry-point adapter; never use provider exceptions as signature detection.

### 10. Operator and agent surfaces can describe the wrong contract

`sase final list/show` resolve defaults rather than the current sealed selection;
external instances always get `submission_required: true` and `{}` because `describe`
is not consulted at context time; pretty context omits the manifest template; and the
generated skill explains only commit/refuse payloads. Some docs still describe the
deleted legacy follow-up controller and cite its removed module. These mismatches turn
minor plugin failures into difficult-to-diagnose completion failures.

## Capability direction

### Seal a provider description before the turn

Run external `describe` in an isolated worker during planning or context construction,
then seal:

- provider distribution/version and entry-point provenance;
- capabilities such as requires-submission, mutates-repository, and verify;
- payload JSON-schema and schema digest;
- trigger/reactivation policy, timeout, and resource class; and
- the configuration digest used for execution.

This lets passive checks avoid pointless `{}` submissions, gives agents typed manifest
templates, and lets the host decide when a provider must rerun. Because describing a
provider executes plugin code, retain the trust model (“installed trusted plugin,” not
a security sandbox), use a scratch home/cwd and sanitized environment, and enforce the
same streaming limits as execution.

### Replace run-once bookkeeping with fixed-point triggers

`ran_non_commit` means a formatter, generator, check, or audit never reruns after
another finalizer changes relevant state. Replace it with host-evaluated triggers such
as `once`, `always`, `dirty_repository`, `provider_requested`, or input/evidence digest
changes. Mutation declarations and host-observed before/after state should drive
reactivation, bounded by the central attempt ledger and no-progress detector.

### Ship useful command-backed instances before elaborate plugins

Once integrity is repaired, `builtin@command` can deliver value with a smaller surface:

- `check` wrapping `just check`, selected by code/PR/epic workflows before commit;
- `research-doc` and `plan-doc` checks for required structure and prohibited paths;
- narrow land/phase closeout checks for epic state, follow-up disposition, and plan
  completion; and
- post-commit artifact/bead/Patch reconciliation after the identity and ordering bugs
  are fixed.

Do not make expensive checks global defaults. Add role/xprompt profiles in trusted
configuration, retain `%final:!name` for optional removal, and keep required instances
non-removable.

### Add closed repository-aware execution policies

`builtin@command` currently supports only the primary cwd and no model payload; plugins
have a fixed 30-second timeout while commands can be effectively unbounded. Add bounded
per-instance timeouts under hard host maxima and closed cwd/input choices such as
`primary`, `plans`, `research`, or `opened:<obligation-id>`. Never accept raw paths,
shell strings, or executable interpolation from the model.

## Verification priorities

Add regression tests that mutate, truncate, reorder, add, and remove persisted plan
entries; alter provider/config/policy digests; remove a required instance; and verify
that execution never begins. Then cover plugin retry budgets, `skipped`, real selection
and identity, normalized distribution names, bounded streaming, immutable retry
evidence, host repository order, provider-internal `TypeError`, payload rejection, and
context-time optional/typed descriptions. Existing live e2e tests should remain, but
these invariants need direct tests rather than mocked worker calls.

## Ranked recommended bug fixes and improvements

| Rank | Kind | Recommendation | Why now |
| ---: | --- | --- | --- |
| **1** | Critical bug | Anchor the resolved plan outside agent-writable artifacts; validate its digest, entries, provider/config/policy snapshot, dependencies, and required selection before context publication and every dispatch. | An empty tampered plan currently bypasses all finalizers and records success, defeating the protocol's core guarantee. |
| **2** | High bug | Define and centrally enforce whole-instance attempt budgets for commit, command, and plugin providers; name declaration, conflict, and cycle budgets separately. | `max_attempts` is a public contract with incompatible behavior across executors. |
| **3** | High bug | Make controller failure authoritative and give `skipped` one host-owned semantic. | Current durable status can claim success after the controller failed. |
| **4** | High bug | Bind every worker request to authenticated run/agent/context/plan identity and the actual resolved selection. | Plugins currently receive null identity and config defaults, breaking idempotency and conditional behavior. |
| **5** | High bug | Normalize plugin distribution identities consistently across discovery, config, required-plugin matching, Rust validation, and worker lookup. | Valid installed plugins can be impossible to configure or execute. |
| **6** | High bug | Enforce streaming output limits, bounded diagnostics, process-group termination, and consistent timeout maxima. | Post-`communicate()` checks do not prevent memory exhaustion. |
| **7** | Medium-high bug | Preserve immutable per-attempt artifacts, evidence, and diagnostics with controller-issued monotonic IDs. | Reactivation currently destroys the history needed to explain failure and recovery. |
| **8** | Medium bug | Execute repository decisions in host context order and harden context/submission freshness races. | Model declarations should express choices, never protocol ordering. |
| **9** | Medium bug | Replace the SDK's `TypeError` callable/factory heuristic with an explicit provider adapter contract. | Real plugin failures are masked and a callable can run twice. |
| **10** | Highest-leverage improvement | Run isolated `describe` at plan/context time and seal provider provenance, capabilities, mutation flag, payload schema, and schema digests. | Unlocks optional/passive and typed providers while making the execution contract truthful. |
| **11** | Improvement | Replace `ran_non_commit` with host-evaluated triggers and fixed-point reactivation bounded by the attempt ledger. | Checks, formatters, generators, commit, and reconciliation can then compose correctly. |
| **12** | Improvement | Repair CLI/skill/docs drift and add a turn-bound explain/doctor view before broad plugin rollout. | Operators and agents currently see defaults or commit-only guidance instead of the actual turn contract. |
| **13** | Improvement | Add role/xprompt profiles and ship narrowly selected command-backed `check`, research/plan validation, and closeout instances. | Provides immediate product value without waiting for a mature third-party ecosystem. |
| **14** | Improvement | Add closed repository-aware cwd/input policies and bounded configurable plugin/command timeouts. | Enables safe sidecar and multi-repository checks without exposing raw execution control. |

The recommended sequencing is ranks 1–9 as a correctness and integrity epic, ranks
10–12 as the provider-contract epic, and ranks 13–14 as a small capability rollout.
Cryptographic provenance, deployments, async jobs, and failure/always lifecycle hooks
should remain later designs; monitors, gates, and CI already cover much of that space.
