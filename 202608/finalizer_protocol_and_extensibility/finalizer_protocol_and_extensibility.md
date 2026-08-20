---
create_time: 2026-08-20
updated_time: 2026-08-20
status: research
---

# Finalizer Protocol and Extensibility

## Decision summary

Generalize SASE finalization as a **host-owned, feature-flagged reconciliation
protocol**, while keeping VCS mutation behind the existing `sase stitch create` and
`--resume` machinery. Plugins and trusted configuration may define named finalizer
instances, but installation alone must never activate them, `%final` must only select
configured instances, and prompt text must never supply an executor, environment, or
repository path.

The built-in `commit` finalizer should remain the default. Omitting `%final` therefore
has the resolved effect of `%final:commit`; do not inject that literal directive into
every prompt. A generated `/sase_final` skill should collect a versioned, turn-bound
declaration through a new `sase final` CLI. For each repository containing
agent-attributable dirty work, that declaration must say either `commit` or `refuse`;
refusal requires a reason and normally leaves the run failed while attributable dirt
remains.

If a selected finalizer needs agent input and a normally completing turn omits it, give
the agent exactly one recovery turn, then fail closed. Intentional handoffs such as
`/sase_plan`, `/sase_monitor`, `/sase_pipe`, and `/sase_questions` remain mechanically
exempt because their commands terminate the runner before the normal success path.

## Evidence and what changed since the earlier research

This report consolidates the two 2026-08-20 reports preserved beside it and adds an
independent audit of `sase@f3a52bc0a`. Both source reports audited `b6864fdb6`; the only
relevant intervening commit added the snippet CLI, so their current-code findings still
hold. The older July report at
`202607/pluggable_finalizers_final_directive/` was reviewed as prior art, not truth.

The July architecture—named finalizers, ordered `%final` operations, plugin opt-in, and
a bounded host driver—was directionally right. Several old premises are now obsolete:

- The proposed vars-driven commit finalizer did not land. `sase var` is also the wrong
  store: it is not turn-bound, has the wrong visibility and schema, and cannot safely
  express complete multi-repository coverage.
- Commit attribution is stronger now. `commit_results.json` records run-owned,
  per-repository commit SHA and tree evidence, allowing a rebase-changed SHA to be
  recognized by tree identity.
- Conflict recovery is mature. `commit_state.json` and `sase stitch create --resume`
  persist and finish the same operation after an agent resolves a conflict.
- SASE now has feature flags and plugin-qualified provider conventions. They supply a
  safer rollout and activation model than plugin-injected default config.

The hard-coded seam remains in `src/sase/llm_provider/_invoke.py`: after a successful
`provider.invoke()`, SASE calls `run_commit_finalizer()`. The current controller already
inventories the primary and opened repositories, protects pre-run dirt, performs a few
narrow machine-owned auto-commits, gives the agent bounded repair turns, detects
discarded dirty work, and verifies publication. This is a reconciliation loop, not a
simple stop hook; the generic design should retain that seam and those invariants.

One prerequisite deserves explicit implementation work: a linked or external repo
opened after the run baseline was captured may already be dirty. SASE must atomically
capture that repo's baseline when it enters the run inventory, before the agent can
edit it. The host must derive obligations from baseline deltas and issue opaque repo
IDs; the model must not invent paths or decide which repositories count.

## Recommended architecture

Separate finalization into four contracts:

1. **Plan:** resolve enabled definitions, defaults, `%final` operations, dependencies,
   and ordering before the provider call. Persist the raw selectors, resolved plan,
   provider provenance, and spec digests in agent metadata/artifacts.
2. **Context and declaration:** when a host-evaluated trigger says a selected finalizer
   needs model input, mint a turn nonce and context digest. `/sase_final` reads the
   context and atomically submits one typed manifest.
3. **Execute:** SASE runs deterministic executors out of process with a sanitized
   environment, argv rather than a shell, time and output limits, immutable context,
   and a required structured result.
4. **Verify:** SASE recomputes triggers and postconditions independently. An executor's
   claim of success is never sufficient. Iterate to a bounded fixed point or fail.

This division lets plugins extend finalization without granting them ownership of the
completion lifecycle. The host controls selection, budgets, ordering, retries, status
aggregation, evidence, and failure. Provider code supplies typed instructions and an
executor; it does not call the model, mark itself skipped, or bypass verification.

Trigger evaluation, dependency closure, stable ordering, result validation, and
aggregate status are shared domain behavior. They should move to `sase-core` when the
CLI/ACE or another frontend needs to answer “what will run?” consistently. Do not
prematurely stabilize a Rust wire while the initial single-entry Python protocol is
still changing.

## Configuration and plugin contract

Use a keyed registry of explicitly activated instances:

```yaml
finalizers:
  defaults: [commit]
  required: [commit]
  instances:
    commit:
      use: builtin@commit
      max_attempts: 2
      refusal: fail
    local-check:
      use: builtin@command
      command: [just, check]
      timeout_seconds: 600
      submission: none
    task-beads:
      use: acme-sase@task-beads
      after: [commit]
```

Plugins should advertise declarative providers through a `sase_finalizers` entry-point
group, using plugin-qualified references such as `distribution@provider`. Installing a
plugin only makes a provider available; a user/project config instance or `%final`
selection of an already configured instance activates it. Missing or invalid selected
providers fail before the main model turn where possible. `plugins.required` remains
the trust/availability assertion.

A constrained `builtin@command` provider is worthwhile so configuration alone can
define local checks. Its command is fixed in trusted merged config, invoked without a
shell, and subject to the same schema, timeout, output, and verification rules. Prompt
input may satisfy a declared JSON schema, but may not interpolate into executable
position. Reusable or domain-aware behavior should be a versioned plugin.

In-repository config is executable-policy input and therefore a supply-chain boundary.
That risk already exists for hooks and chops; surface provenance in `sase final list`
and `doctor`, and never let a plugin layer silently set a new active default.

## `%final` semantics

Treat directives as ordered operations on configuration-derived defaults:

| Form | Meaning |
| --- | --- |
| omitted | configured defaults; initially `commit` |
| `%final:commit` | add or explicitly retain `commit` |
| `%final:lint` | add `lint` without removing `commit` |
| `%final:!commit` | remove `commit` if policy allows |
| `%final:none` | clear all defaults |
| `%final:none %final:lint` | select exactly `lint` |

Apply repeated and comma-separated operations left to right. Reject bare `%final`,
unknown instances, dependency cycles, and removal of a required instance at launch.
Persist both raw operations and the resolved ordered plan. While the beta flag is off,
recognize `%final` only to emit a targeted flag-required error; never silently strip
it.

For version 1, `%final` should be **selection only**. One source report and the July
consolidation allowed a closed set of per-launch kwargs such as `max_passes`. The safer
choice for a completion-critical system is to keep retry budgets, failure policy,
timeouts, credentials, and all executable details in trusted configuration. If a real
need for per-run tuning emerges, add a separately reviewed allowlist later; it is not
needed to deliver the requested override.

## `/sase_final` and `sase final`

The generated skill's source belongs under `src/sase/xprompts/skills/`; deployed skill
copies must not be edited directly. Inject the end-of-turn rule in the launch prompt
while the beta is enabled, because global generated instructions cannot vary with a
per-project flag.

The instruction should say to invoke `/sase_final` as the last action of a normally
completing turn. The skill should:

1. read `sase final context --format json`;
2. inspect selected finalizers and host-issued obligations;
3. construct schema-valid payloads;
4. submit the complete envelope atomically;
5. fix validation errors within the same turn when possible.

The CLI should prefer document-level atomicity over a collection of stateful mutation
commands:

```text
sase final [list]
sase final show <instance>
sase final context [-f|--format json]
sase final submit <manifest-file|->
sase final doctor
```

Convenience builders such as `commit` and `refuse` are acceptable only if they produce
and validate the same atomic document. The agent-facing command must never execute
plugins or Git; it records intent. Follow normal CLI conventions: bare groups default
to `list`, required values are positional, and every public long option has a short
alias.

The envelope needs a schema version, run ID, turn ID/nonce, selected-plan digest,
context digest, and exactly one payload for each selected finalizer that requires
submission. Reject stale IDs/digests, unknown repos, duplicated decisions, missing or
extra payloads, unknown fields, and schema violations. Preserve invalid attempts as
diagnostic artifacts, but expose only one current `final_submission.json`.

“Every completing turn must use the skill” is useful agent policy, but enforcement
should be demand-driven. A clean commit-only turn needs neither a declaration nor a
recovery LLM pass. A selected always-run audit finalizer may require one. The driver
forces recovery only when its validated plan and current triggers find missing input.

## Commit finalizer contract

For every host-classified repository with agent-attributable dirty paths, require
exactly one decision:

- `commit`: request one final stitch for the remaining attributable work, including a
  conventional commit message; or
- `refuse`: decline with a nonblank reason.

Refusal is evidence, not permission. Record and surface the reason, but with the default
`refusal: fail` policy, dirty attributable work still fails completion. An explicit
trusted configuration may define a different policy for a non-required instance; a
prompt may not.

Version 1 should request at most one final stitch per dirty repository. Multiple
commits require reliable file-to-commit partitioning and add conflict ordering without
improving the core protocol. Keep pre-existing paths excluded exactly as today, and
recompute coverage at submission, before execution, and after execution so edits made
after `/sase_final` make the manifest stale.

The executor must call `sase stitch create`, not raw Git and not a new commit engine.
`commit_results.json` remains the evidence that this run committed a repository;
`final_submission.json` records intent only. Preserve the current narrow auto-commits,
bead publication checks, Patch/Stitch bookkeeping, discarded-work guard, and the
compatibility `commit_finalizer_result.json` artifact while consumers migrate.

## Merge-conflict state machine

Process mutating repository decisions sequentially in deterministic order. Parallel
commits would make partial completion and recovery ambiguous.

1. Pin the repo ID, baseline/context digest, message digest, and decision in the sealed
   submission.
2. Run `sase stitch create` for the first repository.
3. On success, verify `commit_results.json`, cleanliness relative to protected pre-run
   dirt, publication, and Patch/Stitch state; then continue.
4. On exit code 2, stop immediately. Preserve `commit_state.json` and the paused VCS
   operation. Do not start another repository and do not consume a normal declaration
   retry.
5. Give the agent a dedicated repair turn containing the existing conflict recipe:
   inspect conflicts, resolve markers, stage, continue the Git operation, then invoke
   the wrapper's resume path.
6. Resume the same operation with `sase stitch create --resume`; never start a new
   stitch, stash, auto-abort, skip, or guess a resolution.
7. Revalidate evidence and continue only after success. A second unresolved conflict
   or stale/contradictory state fails with artifacts intact for diagnosis.

The declaration-recovery budget and conflict-repair budget are different. Missing
`/sase_final` gets one recovery turn; an actual exit-2 conflict gets one explicit repair
turn. Counting conflict repair as noncompliance would regress today's workflow.

## Feature flag and rollout

Create a beta flag such as `pluggable_finalizers` only with `sase flag new`. It defaults
off, requires both-state tests, and owns a removal bead. The disabled branch must remain
the current `run_commit_finalizer()` path; permanent choices such as defaults and
instance configuration remain config, not flags.

Recommended phases:

1. Add schemas, artifacts, baseline-on-repo-open, plan resolution, and compatibility
   writers without changing behavior.
2. Behind the flag, add the declaration handshake and host-executed built-in `commit`;
   prove parity for every current safety invariant and conflict path.
3. Add keyed configuration and `%final` selection; migrate
   `commit.finalizer.{enabled,max_passes}` with diagnostics.
4. Add plugin discovery, `builtin@command`, `list/show/doctor`, provenance, and a
   non-mutating reference finalizer.
5. Soak under opt-in. Then remove the flag's old branch and close its bead; do not leave
   two commit engines indefinitely.

Critical tests include: flag-off equivalence; clean turns without declarations;
one-and-only-one missing-declaration recovery; stale submissions after later edits;
complete commit/refusal coverage; refusal reason preservation and fail policy;
late-opened dirty repo baselines; pre-existing path protection; tree-based evidence
after rebase; first-repo conflict preventing second-repo dispatch; successful
`--resume`; discarded-work detection; intentional SIGTERM handoff exemption; family
baseline inheritance; plugin installation without activation; `%final:lint` preserving
commit; `%final:none` clearing it; and launch-time rejection of unknown, cyclic, or
policy-forbidden selections.

## Recommended solution

Implement a beta-gated generic finalizer controller at the existing post-invocation
seam. Give it a declarative keyed registry, explicit plugin/config activation, additive
selection-only `%final` operations, host-evaluated triggers, a generated `/sase_final`
skill, and a turn-bound atomic `sase final submit` manifest. Make `commit` the default
built-in instance and require a reasoned `commit`/`refuse` decision for every
agent-attributable dirty repository.

Keep all authority with SASE: derive repository obligations from host baselines, seal
and validate intent, execute selected providers out of process, verify postconditions,
and fail closed after bounded recovery. For commits, delegate exclusively to the
existing sequential `sase stitch create` / `--resume` state machine and retain its
ledger, publication, discarded-work, and merge-conflict guarantees. This yields real
user extensibility without turning the most safety-critical part of SASE into an
arbitrary prompt-controlled hook system.

