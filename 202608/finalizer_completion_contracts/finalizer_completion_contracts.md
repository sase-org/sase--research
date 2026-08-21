# Finalizer Completion Contracts

**Research snapshot:** 2026-08-21

## Executive conclusion

SASE finalizers are most valuable as **host-owned completion contracts**: trusted
configuration decides which conditions define completion, an agent declares only the
judgment the host cannot derive, and bounded providers independently execute and verify
the postconditions. They should not become a generic collection of stop hooks.

The best product direction combines the two strongest ideas from the source reports:

1. bind finalizer profiles to the role or xprompt that knows what kind of work is being
   done; and
2. populate those profiles with small, composable contracts for verification, SASE
   hygiene, durable artifacts, workflow reconciliation, and policy.

That composition matters. A global `just check` default would burden research and
review turns, while manually typing `%final:check` repeats the prompt-law problem that
finalizers are meant to solve. A code role should select `check`; a research role
should select `research-doc`; a land role should select `check`, `epic-symbols`, and
closeout checks. Explicit `%final` operations should remain the launch-level override,
subject to required policy.

## Evidence and current constraints

The completed `sase-rn` epic established sealed plan resolution, launch selection,
turn-bound atomic declarations, isolated providers, a bounded fixed-point controller,
and durable evidence. The ongoing `sase-rr` epic is removing the beta/legacy split and
proving the single path end to end. The current tree still documents the beta branch,
and the default configuration contains only `builtin@commit`.

The substrate has four unusual advantages over ordinary hooks:

- configuration, rather than model-authored prompt text, owns commands, credentials,
  environment access, retries, timeouts, and required policy;
- the declaration is bound to the run, turn nonce, plan digest, and current repository
  obligations;
- providers execute in isolation and return evidence, while the host owns the success
  decision; and
- dependency ordering plus repository recomputation lets a later mutation reactivate
  commit, with cycle and no-progress protection.

The right analogy is a local synthesis of required checks, policy enforcement, and a
reconciliation controller. GitHub required checks remain the authoritative remote merge
gate; OPA illustrates separating policy decisions from enforcement; Kubernetes
finalizers illustrate withholding completion until a controller proves a condition.
SASE adds agent identity, workspace baselines, declarations, and local recovery at the
completion seam.

Current limitations shape the rollout:

- `builtin@command` is usable now for trusted, bounded argv-based checks and
  deterministic tools. It accepts no model payload and runs in the primary repository.
- External providers have richer `describe`, `validate`, `execute`, and `verify`
  operations, but operations are currently capped at 30 seconds.
- At the inspected revision, non-commit declaration payloads are accepted without
  provider validation and are not forwarded with host obligations into provider
  execution. This gap is already recorded on `sase-rr`; typed delivery, handoff, and
  cross-repository providers should wait for it.
- Only commit is reactivated by later dirt; non-commit instances run once. Mutators
  therefore need deliberate ordering before checks and commit.
- Finalizers run on normal completion and intentional plan/monitor/pipe/question
  handoffs bypass them. They cannot be the sole crash cleanup, lease release, or
  asynchronous job mechanism.
- Atomic declaration is not atomic side effect. A later provider may fail after an
  earlier provider committed or changed a remote object. Side-effecting providers need
  idempotency keys, independent verification, explicit partial-completion evidence, and
  irreversible operations ordered last.

## A selection rule

A concern belongs in a finalizer when it must hold before the run may honestly succeed,
needs final workspace/run state, can be independently verified, is bounded and
retry-safe, and benefits from ordering with other completion conditions.

Use another seam when those properties do not hold:

- CI for authoritative builds, noisy benchmarks, and cryptographic provenance;
- monitors for long-running checks, deploys, and polling;
- notifications and telemetry for best-effort observation;
- gates during the turn for human authorization;
- runner-level `finally`, leases, and TTL reapers for crash-safe cleanup; and
- mentor/reviewer agents for open-ended judgment.

## Recommended portfolio

### Configure now

Start with command-backed instances whose result is host-observable and whose failure is
actionable:

| Profile | Selected contracts | Notes |
| --- | --- | --- |
| Code change | `check` → `commit` | Wrap `just check` with a 15–20 minute timeout; keep `just check-full` on a monitor. |
| Epic phase | `check` → `phase-hygiene` → `commit` | Verify a phase worker did not create task beads and recorded proposed follow-ups correctly. |
| Epic land | `check` → `epic-symbols` → `land-closeout` → `commit` | Verify symbol hygiene, child/follow-up disposition, bead closure, and plan `status: done`. |
| Research | `research-doc` → `commit` | Verify month placement, document shape, ranked recommendations, and artifact links; do not run primary-tree tests by default. |
| Plan | `plan-doc` → `commit` | Validate frontmatter, phase slugs, and absence of ephemeral `sase_<N>` paths. |
| Review/mentor | `review-packet` or none | Do not default-commit a read-only review. |

Add a small `sase-hygiene` command where audit data is already available: verify that
foreign repositories were opened through `sase repo`, long-term memory was consumed
through audited reads, generated skills were changed at their source, and flag-registry
checks ran when relevant. Begin in advisory profiles before making every rule required;
false positives in a host-owned completion gate are operational outages.

### Build after the protocol bridge

The best custom provider is a typed **delivery manifest**. The agent declares
user-visible impact, tests, feature flag, migration and rollback needs, documentation,
known limitations, and artifact references. The provider validates the schema, compares
claims with the actual diff and evidence, and emits a durable review packet. Agent
claims are accountability input, never proof.

The same pattern extends naturally to:

- swarm/family handoff contracts that require named, typed output variables and valid
  artifact references from the producer;
- feature-flag contracts that require a flag key or explicit permanent-config rationale
  when the diff changes user-facing TUI, CLI, defaults, or public schemas;
- cross-repository compatibility checks using host-issued opaque repository inventory,
  not plugin path discovery; and
- idempotent bead, Patch, PR, and artifact reconciliation after commit proof.

### Explicit heavy profiles

Compatibility suites, visual snapshots, deterministic performance budgets, migration
probes, SBOM/evidence bundles, and preview deployment are useful only for land,
release, or otherwise high-risk launches. Prefer checks with stable local signals.
Workspace evidence improves traceability but is not automatically high-assurance SLSA
provenance; signing and trusted-build claims remain CI responsibilities.

## Design recommendations

1. Make role/xprompt profile binding a first-class trusted configuration mechanism.
   Apply role defaults before user `%final` operations so explicit removal still wins
   unless an instance is required.
2. Prefer many narrow instances over one opaque omnibus script. Narrow instances give
   clearer evidence, ordering, retry behavior, and adoption control.
3. Add a change/dirt trigger or a host-side diff classifier. Profiles should avoid
   paying for irrelevant checks, but the model should not be trusted to classify its
   own risk without verification.
4. Finish the external-provider payload and obligation bridge, then ship a reference
   provider exercising schema publication, declaration validation, payload delivery,
   execution, verification, and evidence end to end.
5. Document side-effect rules: idempotency keys based on run/tree identity, independent
   verify operations, partial-completion reporting, and irreversible work last.
6. Measure finalizer latency, retry rate, failure codes, and bypass frequency through
   ordinary telemetry. Use that evidence before promoting an advisory instance to
   `required`.
7. Consider future lifecycle phases (`success`, `failure`, `always`) and asynchronous
   job/status providers only as separate designs. Do not stretch the current success
   seam to cover cleanup or long deploys.

## Ranked recommended use cases

Ranked by immediate value, SASE-specific leverage, feasibility, and failure safety:

1. **Role/xprompt-bound fast verification before commit.** The highest-value complete
   system: code roles select `just check`, research and review roles do not, and users
   no longer have to remember `%final:check` on every launch.
2. **Land-epic and phase-worker mechanical closeout.** Verify epic symbols, plan state,
   descendant/follow-up disposition, and the prohibition on phase-created task beads.
   These are consequential SASE definitions of done currently enforced mainly by prose.
3. **Run-scoped SASE hygiene.** Enforce audited repo/memory access, generated-skill
   provenance, no ephemeral paths in plans, and relevant feature-flag checks.
4. **Research and plan document contracts.** Validate durable deliverable location,
   schema, required sections, ranked conclusions, and artifact relationships.
5. **Structured delivery/review manifest.** The strongest use of typed declarations:
   impact, tests, flags, migration, rollback, docs, limitations, and refs validated
   against host facts. Implement after the payload bridge.
6. **Required local security and repository policy.** Secret scanning, protected paths,
   forbidden binaries, dependency policy, and “schema change requires migration.” Keep
   checks local and deterministic where availability is critical.
7. **Swarm/family handoff contract.** Fail the producing agent for missing or invalid
   typed outputs instead of making the consumer discover an empty handoff.
8. **Deterministic formatting and generated-artifact reconciliation.** Use only
   idempotent trusted tools, ordered before verification and commit; default to
   cleanliness checks when generation could alter semantics.
9. **Feature-flag and user-reaching-change contract.** Require a real flag or an
   explicit, verifiable permanent-configuration rationale for relevant diffs.
10. **Cross-repository compatibility contracts.** Verify core binding floors, plugin
    schemas, generated clients, wire versions, completion snapshots, and sidecar links
    using host-authorized repository context.
11. **Post-commit bead/Patch/PR/artifact reconciliation.** Attach verified evidence and
    normalize workflow state idempotently after commit proof.
12. **Named compatibility, visual, performance, and migration profiles.** Select for
    land/release work rather than imposing them on every completion.
13. **Release evidence bundles.** Record tree, tools, tests, plan/context digests,
    hashes, and SBOMs; reserve cryptographic provenance claims for trusted CI.
14. **Evidence that required human authorization already exists.** Narrowly verify a
    prior gate result for memory edits, flag removal, or publishing; never wait for a
    person inside a provider.
15. **Preview deploy and smoke verification.** Useful only after an asynchronous job
    shape and robust retry/partial-effect semantics exist; use monitors or CI today.
16. **Crash cleanup, lease release, and notifications.** Do not implement on the current
    finalizer seam. Use runner cleanup, TTLs, and existing notification channels until
    an explicit failure/always lifecycle is designed.

## Sources and provenance

This synthesis preserves the source assignment from the named transcripts, not
filesystem order: `research.0u.cdx` produced the `__a` report and
`research.0u.cld` produced `__b`. It also draws on the `sase-rn` and `sase-rr` beads,
their plans, and the current finalizer configuration, declaration, executor, and
controller implementation.

External conceptual references: [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges/managing-protected-branches/about-protected-branches),
[Open Policy Agent in CI/CD](https://www.openpolicyagent.org/docs/cicd),
[Kubernetes finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/),
and [SLSA build provenance](https://slsa.dev/spec/v1.2/build-provenance).
