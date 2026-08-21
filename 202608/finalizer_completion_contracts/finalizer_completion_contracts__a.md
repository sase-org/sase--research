# New Uses for SASE's Generalized Finalizers

**Research snapshot:** 2026-08-21, primary SASE revision
`dc7da84f9458186a100620b4f7f0dc1c22370bba`. This report uses the completed `sase-rn`
epic, the in-progress `sase-rr` epic, their two plans, the earlier finalizer research,
and a source audit of the current registry, declaration, controller, command executor,
and plugin SDK.

## Executive answer

The most productive mental model is not "run arbitrary things when the agent stops." It
is **a host-owned completion-contract graph**: before a normal SASE turn may be declared
done, trusted policy chooses a bounded set of conditions, the agent supplies typed
intent only where judgment is unavoidable, deterministic providers act, and the host
independently verifies that the conditions now hold.

That framing points to a much larger opportunity than commit automation. Finalizers can
become the local, agent-aware equivalent of required checks, policy enforcement,
reconciliation controllers, and evidence producers. Their special advantage over CI is
that they run while SASE still owns the workspace, its repository baselines, the agent
artifacts, the turn identity, and the right to withhold a successful completion. Their
special advantage over ordinary hooks is that selection, dependency order, input,
attempts, evidence, and terminal outcome are all sealed and observable.

The best initial portfolio is:

- a fast, risk-aware verification finalizer;
- a required security and repository-policy finalizer;
- deterministic normalization or generated-file reconciliation where it is safe;
- the existing commit finalizer;
- opt-in heavier profiles for compatibility, release evidence, and preview deployment.

The most interesting second-wave use is a structured **delivery manifest**: have the
agent declare user-visible impact, tests, migration/rollback needs, documentation,
feature-flag state, and known limitations; then have a provider validate those claims
against the actual diff and publish a durable review packet. This makes the atomic
declaration channel useful for more than commit messages.

## What the new substrate actually enables

`sase-rn` and `sase-rr` provide five unusually valuable properties:

| Property                | New leverage                                                                                                                                                                           |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Trusted plan resolution | Configuration, not prompt text, owns executable policy, credentials, timeouts, retries, defaults, and required instances. `%final` only chooses among configured instances.            |
| Turn-bound declaration  | Agent judgment can be captured as one nonce- and digest-bound document with complete selected-instance coverage, rather than inferred from prose or scattered variables.               |
| Isolated providers      | External providers have bounded `describe`, `validate`, `execute`, and `verify` operations in a sanitized subprocess. The provider reports evidence but does not own agent completion. |
| Ordered fixed point     | Dependency order is deterministic; repository state is recomputed after mutation; later dirt can reactivate commit; no-progress and cycle caps fail closed.                            |
| Durable evidence        | Plans, contexts, submissions, per-attempt output, aggregate results, timings, diagnostics, and commit proof make finalization auditable and debuggable.                                |

This resembles several successful patterns elsewhere, but combines them at the agent
completion seam:

- GitHub protected branches use required checks and even successful deployments as merge
  conditions. SASE finalizers can provide the earlier local gate and richer
  agent/workspace context, while remote branch protection remains the authoritative
  merge gate.
  [GitHub's branch-protection documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- Open Policy Agent separates policy decisions from enforcement and explicitly supports
  validating configuration, outputs, and organizational rules in CI/CD. That same
  separation maps cleanly onto a SASE policy provider plus host enforcement.
  [OPA's CI/CD guidance](https://www.openpolicyagent.org/docs/cicd)
- Kubernetes finalizers prevent lifecycle completion until controllers satisfy named
  conditions. The useful analogy is the reconciliation contract, not cleanup alone.
  [Kubernetes finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/)

## Important boundaries in the current implementation

The following constraints materially affect which ideas are ready now:

1. **The current seam is normal-success finalization.** It does not run after a provider
   failure, and intentional plan/monitor/pipe/question handoffs bypass it mechanically.
   A finalizer therefore cannot yet be the sole owner of resource cleanup or lease
   release.
2. **`builtin@command` is deliberately narrow.** It runs a trusted argv in the primary
   repository, accepts no model submission, and treats a bounded exit code as the
   result. This is ideal for tests, linters, scanners, drift checks, and deterministic
   generators.
3. **External providers are richer but currently fail closed.** They are best for
   completion-critical behavior. At the inspected revision each worker operation also
   has a host-fixed 30-second cap, whereas `builtin@command` has a trusted configurable
   timeout. Best-effort telemetry and notifications should use their existing
   nonblocking channels instead of making agent success depend on an exporter.
4. **Atomic declaration does not mean atomic effects.** A later provider can fail after
   an earlier provider committed or changed an external system. Side-effecting providers
   must be idempotent, keyed by run/tree identity, independently verifiable, and ordered
   with irreversible work last.
5. **Non-commit ordering must be intentional.** At the inspected revision a selected
   non-commit instance runs once, while commit can be reactivated by later dirt. A
   mutating normalizer should therefore precede all checks, and checks should precede
   commit; adding a finalizer with `%final` should not be assumed to place it before an
   already selected commit.
6. **The generic declaration bridge has one unfinished edge.** At this revision,
   `declaration._validate_provider_payloads()` validates only `builtin@commit`, while
   `executor._provider_request()` does not pass the accepted non-commit payload or host
   obligations to worker operations. External instances nevertheless currently publish
   `submission_required: true` with an empty payload template. This blocks genuinely
   typed declaration-driven providers until provider validation and payload delivery are
   wired through. The issue was recorded on active epic `sase-rr`, whose protocol and
   acceptance scope causally owns it.

These boundaries suggest a clean rollout rule: begin with host-observable, no-input
checks and deterministic reconciliation; add judgment-bearing finalizers after the
provider payload bridge is complete.

## A test for whether something should be a finalizer

A use case is a strong finalizer candidate when most of these are true:

- The condition must hold before a normal SASE run may honestly be called complete.
- It needs the final workspace, repository baseline delta, agent artifacts, or commit
  proof.
- A deterministic host or provider can verify the postcondition independently.
- Execution is bounded and retry-safe, or a timeout can fail without losing evidence.
- Trusted configuration grants any needed command, credential, or external authority.
- Dependency ordering with other completion conditions matters.

It is probably not a finalizer when it is merely informative, can take an unbounded
time, must run after crashes or termination, or exists only to ask another LLM for a
general opinion. Use notifications/telemetry for observation, monitors or CI for long
asynchronous work, a failure/cleanup lifecycle for guaranteed teardown, and an ordinary
workflow or reviewer agent for open-ended reasoning.

## Use-case analysis

### 1. Adaptive verification profiles

Create a provider that inspects the actual change and selects a bounded verification
lane: focused tests for narrow edits, broader contract suites for public interfaces,
visual tests for rendering changes, and full checks for build/configuration or shared
core changes. The provider should emit the commands, exit results, selected rationale,
and artifact references as evidence.

This can start today as one smart trusted command, or as several fixed `builtin@command`
instances selected through project defaults and `%final`. The provider form is better
long term because it can make the selection from host-observed diff facts rather than
trusting the model's risk estimate.

Why it belongs here: it gives the agent immediate feedback before success, has the final
diff rather than a mid-turn snapshot, and can be ordered before commit. CI should still
rerun authoritative checks on the committed tree; the local finalizer shortens the
feedback loop and records exactly what was run.

### 2. Security and repository-policy enforcement

Use a required, read-only finalizer for secret scanning, forbidden generated or binary
files, dependency/license allowlists, infrastructure policy, protected-path rules,
commit-signing prerequisites, and project-specific constraints such as "a schema change
requires a migration."

The first version can be a command bundle. A reusable plugin can later normalize the
diff and repository facts into structured input for OPA/Conftest-style policy, return
stable diagnostic codes, and provide evidence for every allow/deny decision. OPA's model
is especially appropriate because policy evaluation stays separate from SASE's
enforcement decision.
[OPA describes itself as a policy decision point whose decisions are enforced by a separate policy enforcement point.](https://www.openpolicyagent.org/docs/deploy)

Make this instance `required` in repositories where bypass would be unsafe. Keep the
policy deterministic and local where possible; a transient SaaS scanner should not brick
every completion unless the organization deliberately accepts that availability
tradeoff.

### 3. Deterministic normalization and generated-artifact reconciliation

Run idempotent mutators such as formatting, generated-client refresh, schema/docs
generation, lockfile normalization, or snapshot-index regeneration before verification
and commit. This is one of the few use cases that exploits the fixed-point controller
rather than merely using finalizers as status checks: a provider can create attributable
dirt, later checks see the normalized tree, and commit reconciles the final state.

Guardrails matter:

- The transformation must be deterministic and idempotent.
- It should not perform broad heuristic rewrites or silently change semantics.
- Mutators must run before checks, not after them.
- Generated outputs should be verified against their inputs, not trusted merely because
  the generator exited zero.
- Network-dependent generation should be pinned or moved to a release workflow.

For many projects, "check that generation is clean" is a safer default and "regenerate"
an explicit profile. Projects with very stable formatters can reasonably make the
mutator a default.

### 4. Structured completion and delivery manifests

Use the declaration channel to require structured answers to questions that are
currently buried in final prose:

```json
{
  "change_kind": "user_reaching",
  "tests": ["focused", "integration"],
  "user_visible": true,
  "migration_required": false,
  "rollback": "disable feature flag foo",
  "docs_updated": true,
  "known_limitations": [],
  "artifact_refs": ["file:explicit:..."]
}
```

A provider should validate the schema, independently compare the claims with the diff,
test evidence, feature-flag registry, migrations, and produced artifacts, then write a
durable review packet or update an already-authorized PR description. The declaration is
**intent and accountability**, not proof; host facts remain authoritative.

This is the highest-potential use of custom payloads because it converts "remember to
mention X" into a typed completion obligation without granting the model executable
authority. It requires the non-commit payload-validation/delivery bridge identified
above.

### 5. Cross-repository contract reconciliation

SASE routinely spans a primary repository, linked repositories, sidecars, and opened
external repositories. A finalizer can verify cross-repository invariants that ordinary
single-repo hooks miss:

- core binding version floors agree with the released core package;
- plugin manifests, schemas, docs, and completion snapshots agree with the host;
- protocol producers and consumers support compatible wire versions;
- a release version bump is reflected in every package and compatibility matrix;
- durable sidecar state points at committed, published source state.

This is unusually SASE-specific and high leverage. The ideal provider context would
extend the host's opaque repository inventory and baseline deltas to explicitly
authorized external providers; it should not make plugins rediscover arbitrary paths.
The provider can then report per-repository evidence and either fail read-only or apply
a narrowly deterministic reconciliation before commit.

### 6. Targeted compatibility and regression budgets

Treat performance, bundle size, API/schema compatibility, database-query cost, coverage,
generated binary size, and migration reversibility as change-specific completion
contracts. Examples include:

- public API changes must pass an ABI/API compatibility checker;
- TUI changes must stay within an interaction-latency or render-work budget;
- web changes must not exceed a bundle-size delta;
- database changes must include and pass forward/backward migration probes;
- serialization changes must decode a fixture corpus from supported releases.

These checks are too expensive or irrelevant for every run, which makes named `%final`
profiles valuable. A smart verifier can also trigger them from diff classification. Keep
benchmarks statistically honest: a noisy microbenchmark that intermittently blocks
completion belongs in a controlled CI environment, while deterministic size and
compatibility checks fit locally.

### 7. Bead, PR, and release-state closeout

After verification and commit proof exist, a provider can reconcile authorized workflow
state: attach artifact references to the active bead, confirm required child work is
closed, update a PR body/check result, apply risk labels, or advance a release candidate
only when the evidence set is complete.

The provider must not infer new authority from installation or prompt text. It should
use stable idempotency keys, verify the resulting remote state, and run after all local
mutators. A failure may occur after the commit has already been published, so the
aggregate result must clearly expose partial completion and make retry safe.

This is preferable to an unstructured "send a message at the end" hook because the
external state becomes a verified completion obligation. Pure notification, however,
should stay on the existing notification path.

### 8. Release evidence, SBOMs, and attestations

For release-oriented runs, a finalizer can assemble a signed evidence bundle containing
the committed tree, resolved dependencies, tool versions, verification results, SASE
plan/context digests, produced artifact hashes, and an SBOM. SLSA defines provenance as
verifiable information about where, when, and how artifacts were produced, so SASE's
sealed plan and evidence ledger are natural inputs.
[SLSA build provenance specification](https://slsa.dev/spec/v1.2/build-provenance)

Do not overclaim: evidence produced in an ordinary developer workspace is useful
traceability, not automatically high-assurance SLSA provenance. Cryptographic
attestation should bind artifacts built in a trusted build environment. GitHub likewise
recommends attestations for released binaries, packages, or content manifests rather
than frequent test builds, and notes that provenance must be verified to provide its
security benefit.
[GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)

Therefore this should be an explicit release profile, not a universal default.

### 9. Preview or staging deployment with smoke verification

An opt-in finalizer can deploy the committed change to a disposable preview or staging
environment, run smoke checks, and publish the environment URL and result evidence. This
directly models the same "deployment must succeed" condition that GitHub can make a
branch-protection requirement.

The constraints are substantial: credentials, network availability, long latency,
partial external effects, teardown, and cost. The current 30-second external-provider
operation cap also rules out most direct deployments unless the provider contract gains
an asynchronous job/status shape. Use this only when deployment is bounded and
idempotent. If it takes long enough to need polling, hand it to a monitor or CI and let
the external status become the final condition rather than blocking a local worker
subprocess.

### 10. Resource and lease cleanup — valuable, but not yet safe as the sole mechanism

The name "finalizer" naturally suggests cleaning containers, temporary branches, preview
environments, locks, worktrees, or cloud resources. Kubernetes demonstrates why
completion-blocking cleanup controllers are useful, but it also demonstrates the failure
mode: a broken finalizer can leave an object stuck terminating.

SASE's present normal-success seam is insufficient for guaranteed cleanup because it is
bypassed on provider failures and intentional handoffs. Cleanup should remain backed by
leases, ownership records, TTL reapers, or runner-level `finally` behavior. A future
`always`/`failure` lifecycle with persisted retry ownership could make cleanup providers
first-class; even then, cleanup should be idempotent and recoverable outside the dying
agent process.

## Recommended portfolio and sequencing

Start with three layers:

1. **Required, read-only defaults:** adaptive fast verification, repository/security
   policy, then commit. These are easy to reason about and fail before external
   publication beyond the commit already owned by SASE.
2. **Deterministic reconciliation:** formatting or generated outputs, placed before the
   checks, only in projects where the transformation is stable and accepted.
3. **Explicit profiles:** full compatibility, release evidence, PR closeout, and preview
   deployment selected with `%final` for the launches that justify their latency and
   authority.

Before building declaration-heavy providers, finish the non-commit payload bridge and
add a reference plugin whose schema, accepted submission, executor input, evidence, and
verification can be inspected end to end. Before building side-effecting providers, make
partial completion and idempotent retry a documented provider design requirement.

The finalizer result artifacts already provide useful run-level observability. Exporting
their timings and outcomes should be ordinary instrumentation rather than another
completion-blocking finalizer: OpenTelemetry explicitly treats traces, metrics, and logs
as correlated but distinct signals, which fits SASE's existing telemetry layer.
[OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)

## Ranked recommended use cases

1. **Adaptive verification gate** — Highest immediate value and lowest integration risk;
   begin with a trusted command and evolve toward diff-aware lane selection with
   explicit evidence.
2. **Security and repository-policy gate** — Make secrets, protected paths, dependency
   policy, IaC rules, and change requirements fail closed under trusted required policy.
3. **Deterministic normalization and generated-artifact reconciliation** — Exploits the
   ordered fixed point directly; use only for idempotent transformations and always run
   verification afterward.
4. **Structured completion/delivery manifest** — The best use of typed agent
   declarations; validate user impact, tests, migrations, rollback, docs, flags, and
   artifacts against host facts after the non-commit payload bridge is complete.
5. **Cross-repository contract reconciliation** — Especially valuable for SASE's core,
   plugins, schemas, generated clients, and sidecars; extend the opaque host repository
   context rather than letting providers rediscover paths.
6. **Targeted compatibility and regression budgets** — Use named profiles for API/ABI,
   migrations, performance, bundle size, visual output, and backward-compatibility
   checks that are too expensive for every turn.
7. **Bead, PR, and release-state closeout** — Reconcile authorized workflow state from
   verified commit and artifact evidence; require idempotency and surface partial
   completion clearly.
8. **Release evidence, SBOM, and attestation bundle** — Strong for release runs, but
   keep cryptographic claims in a trusted build environment and verify the resulting
   attestation downstream.
9. **Preview/staging deployment and smoke gate** — Useful opt-in assurance when bounded;
   defer long-running or flaky environments to monitors/CI.
10. **Resource and lease cleanup** — Pursue only after SASE has an always/failure
    lifecycle with durable retry ownership; retain TTL and runner-level safety nets even
    then.
