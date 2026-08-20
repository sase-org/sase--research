---
create_time: 2026-08-20
updated_time: 2026-08-20
status: research
---

# Generalizing SASE Finalization Without Weakening Commit Safety

**Research question.** How should SASE replace its hard-coded commit finalizer with
user-defined finalizers from configuration and plugins, add a per-agent `%final`
directive and `/sase_final` skill, require explicit commit or refusal intent for every
modified repository, and preserve the existing merge-conflict workflow?

**Scope.** Current behavior was verified against `sase@b6864fdb600f` and
`sase-core@751d60f600d0` on 2026-08-20. The earlier finalizer research and its two
source reports were reviewed first, then every load-bearing recommendation was checked
against the current code. External sources were checked on 2026-08-20. This is
architecture research, not an implementation plan; no SASE runtime behavior was
changed.

---

## Bottom line

SASE should generalize finalization, but it should **not** generalize the commit
algorithm. The safest design is a host-owned finalization controller with three
separate contracts:

1. **Discovery and selection:** configuration defines named finalizer instances;
   plugins contribute declarative finalizer providers through a new
   `sase_finalizers` entry-point group; a constrained built-in command provider covers
   config-only local finalizers; `%final` changes the selected instances for one agent.
2. **Agent declaration:** a generated `/sase_final` skill calls a new `sase final`
   command to submit one versioned, turn-bound JSON manifest. The built-in commit
   payload must cover every repository with agent-attributable dirty work using exactly
   one `commit` or `refuse` decision. Refusal requires a reason and, by default, remains
   a failed finalization while dirt is present.
3. **Deterministic reconciliation:** after a successful provider turn, SASE validates
   the manifest, runs selected finalizer executors out of process, and independently
   verifies their postconditions. The commit executor delegates to the existing
   `sase stitch create` / `--resume` workflow and its durable result ledger. It never
   reimplements staging, VCS publication, Patch/Stitch bookkeeping, or conflict
   recovery.

If the turn returns without a current valid manifest, SASE should force exactly one
declaration-recovery turn. A second omission fails the run. A valid manifest does not
mean the run is final: execution, conflict repair, and postcondition checks remain
bounded host-controlled phases.

The new controller should ship behind a beta flag, tentatively
`pluggable_finalizers`, default off. With the flag off, the current commit finalizer
must remain byte-for-byte equivalent at its call boundary. With it on, `commit` becomes
the first built-in provider and the default selected instance, so the resolved default
is equivalent to `%final:commit` without literally modifying every prompt.

---

## 1. Earlier research reviewed

The prior consolidated report,
[`202607/pluggable_finalizers_final_directive`](../202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md),
recommended:

- a keyed finalizer config map;
- plugin-provided executors;
- a `%final` directive with add, remove, and clear operations;
- bounded agent and script phases;
- explicit `turn` versus `agent` scope;
- migration of commit finalization into the generic registry;
- use of agent artifacts and axe-chop-style JSON boundaries.

Those conclusions were directionally good. The old report was also appropriately
cautious about plugin activation and prompt-injected executable paths. Four things have
changed or become clearer since July:

1. **Commit attribution is now much stronger.** SASE records a run-owned,
   per-repository `commit_results.json` ledger containing the commit SHA and tree. The
   current finalizer accepts a tree match after a rebase, so it can distinguish an
   attributable commit from work that merely disappeared.
2. **The conflict protocol is mature.** `sase stitch create` has a durable
   `commit_state.json` checkpoint and a canonical `--resume` path. Exit code 2 means an
   agent must resolve the paused Git operation and resume the same workflow.
3. **Plugin provider conventions now exist.** File hooks and task types use
   plugin-qualified `distribution@provider` references and explicit config activation.
   Finalizers should follow that pattern instead of injecting plugin config defaults.
4. **The abandoned vars-driven commit plan is too narrow.** The old
   `202607/commit_vars_finalizer.md` plan proposed JSON output variables and
   exclusion-based staging for the primary repository. General JSON output variables
   and exclusion staging landed, but `sase commit --vars` did not. More importantly,
   the new requirement covers every modified repository and requires explicit refusal
   reasons, so one unstructured variable cannot be the source of truth.

The current design can therefore be both more generic at the finalizer boundary and
more conservative at the VCS boundary than the July proposal.

---

## 2. Current behavior and invariants

### 2.1 The finalizer is still hard-coded at the provider call site

`src/sase/llm_provider/_invoke.py` calls `run_commit_finalizer()` immediately after
every successful `provider.invoke()`. The finalizer then:

- skips outside a SASE agent, when disabled by configuration, or when the legacy
  disable environment variable is set;
- inventories the primary workspace, opened linked and external repositories, and SDD
  sidecars;
- accounts for dirty paths captured before the run;
- performs a few narrow machine-owned auto-commits;
- prompts the same provider for at most `commit.finalizer.max_passes` repair turns;
- fails if attributable dirt remains or if dirty work vanished without commit evidence.

This is already a reconciliation loop, not merely a stop hook. The generalized system
should preserve that character.

### 2.2 Repository ownership is almost, but not completely, available

At runner startup, `commit_finalizer_baseline.json` records dirty-path fingerprints so
pre-existing user work is not charged to the agent. Agent-family attachment inherits
the parent's run artifacts. Opened repositories are recorded in
`opened_linked_workspaces.json`, and current-state inventory spans the repositories the
agent could have modified.

There is one important gap: a linked or external repository first opened *after* the
run baseline was captured has no entry-time dirty fingerprint. Its existing dirt can be
mistaken for agent work. Before making per-repository declarations mandatory, SASE
must capture a baseline atomically when a repository enters the run's inventory. This
can extend the opened-workspace record or use a separate versioned
`repo_baselines.json`; the important property is that the host writes it before the
agent can edit that repository.

The host, not the model, must derive the set of repository obligations from those
baselines. The agent should receive opaque repository IDs and display paths, but it
must not be allowed to invent filesystem paths in a finalization manifest.

### 2.3 Commit evidence survives rebases

The existing commit workflow writes both a latest `commit_result.json` and an
accumulating `commit_results.json`. Each successful result identifies the run,
repository, method, Patch and Stitch where applicable, commit SHA, and commit tree.
The finalizer checks provenance trailers and the ledger, accepting the same tree when a
rebase changes the SHA.

That ledger should remain the authority for “this run committed this repository.” A
new finalizer manifest should describe pending intent; it should not duplicate or
replace commit evidence.

### 2.4 Merge conflicts already have one safe owner

The canonical user-facing operation is `sase stitch create` (with `sase commit` as a
legacy alias). It records a checkpoint before dispatching into the VCS provider. A
conflict leaves the repository in its paused state, returns exit code 2, and retains
enough state for `sase stitch create --resume` to finish publication and replay Patch,
Stitch, and result-ledger bookkeeping.

The `/sase_git_commit` skill already tells an agent to resolve conflict markers, stage
the resolution, continue the Git operation, and invoke the wrapper with `--resume`.
This matches Git's own documented rebase protocol: resolve, `git add`, then
`git rebase --continue`; aborting and skipping are materially different choices and
must not be guessed by an automated hook.
([Git documentation](https://git-scm.com/docs/git-rebase))

Any generic finalizer that shells out to `git commit`, starts a new stitch after exit
2, stashes the tree, or auto-aborts would bypass these guarantees. That is the clearest
architectural boundary in this research.

### 2.5 Intentional handoffs already avoid normal post-turn finalization

`/sase_plan`, `/sase_monitor`, `/sase_questions`, and `/sase_pipe` hand control to
another mechanism and terminate the runner. Their provider invocation does not return
normally through the success path. A generalized controller placed after a successful
return is therefore naturally exempt for these intentional early terminations. SASE
should preserve that structural exemption rather than teach `/sase_final` a growing
list of magic skip reasons.

---

## 3. Requirements derived from the request

The design should satisfy these invariants:

| Invariant | Consequence |
| --- | --- |
| Finalization is completion-critical | Selected finalizer load, validation, or execution errors fail closed. |
| Plugins are opt-in | Installing a plugin makes a provider available; only config or `%final` selects it. |
| Prompt text is untrusted input | A directive selects configured instance names, never executable paths or arbitrary shell fragments. |
| Agent intent is not proof | SASE re-inventories repositories and validates durable executor results after every action. |
| Every attributable dirty repo is explained | Exactly one commit or refusal decision is required per repository. |
| Refusal is observable, not a loophole | A refusal requires a reason; the built-in commit finalizer fails while attributable dirt remains unless an explicit host policy says otherwise. |
| Pre-existing work is protected | Host-derived exclusions prevent an agent's final commit from absorbing paths it does not own. |
| Conflicts stay agent-owned | A paused commit workflow always produces a repair turn and must be resumed from its checkpoint. |
| Finalization is bounded | Missing declarations, agent repair, executor retry, and fixed-point rounds each have explicit budgets. |
| Results are auditable | Selection, prompt declaration, executor input/output, refusal, and final postconditions are durable agent artifacts. |

Kubernetes finalizers provide a useful conceptual precedent: a finalizer name is a
durable key indicating that a controller still owes work; it is not executable code,
and the key is removed only after the controller satisfies the condition. Kubernetes
also recommends qualified names for custom finalizers and warns against force-removing
stuck finalizers. SASE should adopt the same separation between **selected key** and
**controller behavior**, without copying Kubernetes's object lifecycle wholesale.
([Kubernetes documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/))

---

## 4. Options considered

| Option | Strength | Fatal weakness | Verdict |
| --- | --- | --- | --- |
| Keep the hard-coded commit finalizer and add more special cases | Lowest migration risk | Cannot support plugins, `%final`, or typed non-commit intent | Reject |
| Let `/sase_final` directly execute arbitrary configured commands | Simple mental model | The model controls sequencing and can omit checks; no host postcondition authority | Reject |
| Store finalizer requests in generic agent output variables | Reuses existing JSON storage | No turn nonce, selection digest, repository coverage, or provider schema; stale values can satisfy a later turn | Reject as protocol, reuse storage utilities only |
| Run plugin callbacks in the SASE process | Easy access to internals | Imports third-party behavior into a critical trust boundary; poor timeout and crash isolation | Reject for executors |
| Generic scripts plus one follow-up prompt, as in the July report | Extensible and bounded | Too weak on repo ownership, result proof, conflicts, mutation ordering, and fail-closed activation | Evolve, do not implement literally |
| Host-owned manifest and reconciliation controller | Typed intent, independent verification, plugin isolation, current commit workflow reuse | More state-machine work | **Choose** |

---

## 5. Recommended architecture

The architecture should have five components:

```text
config + plugin providers + %final
                |
                v
      resolved finalization plan
       (persisted in agent_meta)
                |
                v
provider turn -> /sase_final -> sase final submit
                |                 |
                |         turn-bound manifest
                v                 v
       host finalization controller
         |       |          |
      validate  execute   reconcile
                  |
          out-of-process providers
                  |
       existing SASE domain commands
       (commit uses stitch create/resume)
```

The critical distinction is between a **provider** and an **instance**:

- A provider is code supplied by SASE or a plugin. It declares a schema, stage,
  capabilities, executor command, and result contract.
- An instance is a named, configured use of a provider. `%final:commit` selects the
  instance named `commit`; configuration determines that its provider is
  `builtin@commit`.

This permits two differently configured instances of the same plugin provider without
putting config syntax or executable identity in the agent prompt.

### 5.1 Keep shared domain state in `sase-core`

The versioned wire types and pure decisions are cross-frontend behavior and belong in
`sase-core`:

- provider and instance wire schemas;
- resolved-selection operations;
- manifest envelope validation;
- repository-obligation coverage;
- stage/dependency validation;
- state and result transitions;
- fixed-point and budget decisions.

Python should own config layering, Python packaging discovery, process execution,
filesystem inventory, prompt integration, and calls into VCS/workspace adapters. The
existing axe-chop wire is a useful local model: versioned strict JSON, unknown-field
rejection, and pure decisions separated from host effects.

### 5.2 Use a staged reconciliation pipeline

Finalizers cannot be treated as an arbitrary ordered list. A task-bead finalizer may
create repository changes that the commit finalizer must then seal. Conversely, a
read-only verification finalizer may need to inspect the committed result.

Providers should declare one of three host-enforced stages:

1. `mutate` — may change repositories or external state;
2. `seal` — converts remaining repository work into durable commits/publications;
3. `verify` — must be read-only and checks final postconditions.

All selected `mutate` instances run before `seal`, and `verify` runs last. Within a
stage, config may define `after` dependencies and the host topologically sorts them.
Cycles and references to unavailable instances are launch-time errors.

After one pass, the controller re-evaluates triggers and repository state. If a
mutating finalizer created new obligations, it runs another bounded round. Success
requires a fixed point: every selected provider reports satisfied, no blocking
checkpoint exists, and all host-owned postconditions hold. This prevents a task-bead
finalizer from dirtying a sidecar after commit has already declared success.

---

## 6. Plugin and configuration contract

### 6.1 Discovery

Add a `sase_finalizers` Python entry-point group. A provider entry point should load a
small declarative spec, not execute finalizer behavior in process. Python package entry
points are explicitly intended to let an installed distribution advertise components,
while console-script entry points provide command wrappers; this maps cleanly onto
declarative discovery plus isolated execution.
([PyPA entry-point specification](https://packaging.python.org/en/latest/specifications/entry-points/))

A provider spec should include at least:

```yaml
schema_version: 1
id: task-beads
description: File or update follow-up task beads declared by the agent.
stage: mutate
submission_schema: { ... }
result_schema: { ... }
executor: sase_finalizer_task_beads
timeout_seconds: 60
mutates_repositories: true
```

The host invokes `executor` as an argv vector with paths to immutable input and a
required result location. It must not use a shell. Apply a sanitized environment,
wall-clock timeout, stdout/stderr caps, and a strict result schema. Record distribution,
version, provider ID, executable resolution, and input digest in the run artifacts.

The manifest and result schemas should use JSON Schema Draft 2020-12 (or SASE's Rust
equivalent with an exported schema), with a required version and unknown fields denied.
([JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12))

### 6.2 Activation

Follow the current file-hook/task-type convention: a plugin may advertise providers,
but installation alone must not activate them. Configuration creates instances using a
plugin-qualified provider reference:

```yaml
finalizers:
  enabled: true
  defaults: [commit]
  required: [commit]
  instances:
    commit:
      use: builtin@commit
      max_attempts: 2
      refusal: fail
    task-beads:
      use: acme-sase@task-beads
      after: []
    local-check:
      use: builtin@command
      stage: verify
      command: [just, check]
      timeout_seconds: 600
      submission: none
```

`plugins.required` should still govern whether a plugin distribution is trusted and
expected. A selected instance whose provider is missing, malformed, or incompatible
must fail before the main provider turn where possible. An invalid *unselected*
provider belongs in `sase final doctor`, not in the critical path.

`builtin@command` is the config-only escape hatch. Its executable and argv are fixed by
trusted merged configuration; `%final` can select only the instance name. It uses no
shell, cannot interpolate manifest strings into executable position, receives context
and result paths through a fixed protocol, and is subject to the same timeout, output,
schema, and postcondition controls as a plugin provider. `submission: none` handles
automatic checks; an inline or config-relative JSON Schema can opt a command into typed
agent input. Reusable or domain-aware finalizers should still be plugins, because a
plugin can version its schema, instructions, and executor together.

The July report suggested treating script spawn failures as soft. That is inappropriate
for a selected completion-critical finalizer: a missing executor means SASE cannot prove
the completion policy ran. Selected provider failures must be hard failures after the
bounded retry policy is exhausted.

### 6.3 `%final` semantics

Retain the safe compositional semantics from the older research:

- selection begins with `finalizers.defaults`;
- `%final:<name>` adds a configured instance;
- `%final:!<name>` removes one;
- `%final:none` clears the selection;
- repeated directives are applied left to right.

Therefore `%final:task-beads` does not accidentally turn off commit safety. An explicit
replacement is `%final:none %final:task-beads`, which is visible and auditable. In the
default configuration, selecting `commit` implicitly has the same result as writing
`%final:commit` in every prompt.

Version 1 should allow **selection only**. Do not expose arbitrary directive kwargs for
timeouts, failure behavior, executors, or credentials. Those are host policy and belong
in configuration. Unknown instance names and attempts to remove a required instance
are launch-time validation errors. Persist both the raw operations and the resolved
ordered plan in `agent_meta.json`.

Under the beta flag's off branch, the parser should recognize `%final` only to return a
targeted “requires `pluggable_finalizers`” diagnostic; it must not silently strip and
ignore the directive.

---

## 7. `/sase_final` and the `sase final` CLI

### 7.1 Skill responsibilities

`/sase_final` should be a generated xprompt skill whose source lives with SASE's other
skill templates. It should:

1. run `sase final context --format json`;
2. inspect the host-issued selected finalizers and repository obligations;
3. construct payloads conforming to each provider's submission schema;
4. submit the complete envelope with `sase final submit`;
5. report validation errors and correct them within the same turn where possible.

The skill should not run plugin executors itself and should not decide whether the run
is complete. Its job is to make the agent's intent explicit.

### 7.2 CLI surface

Following SASE's CLI conventions, `sase final` should be a command group whose bare
form defaults to `list`:

```text
sase final [list]
sase final show <instance>
sase final context [-f|--format json]
sase final submit <manifest-file|->
sase final doctor
```

An internal/test-only reconcile entry point may exist, but users and agents should not
need a `sase final run` escape hatch. Every public long option needs a short alias, help
must include examples and side effects, and required inputs should be positional rather
than required options.

### 7.3 The envelope must be turn-bound

Generic output variables are insufficient because a value from an earlier turn could
appear valid. At turn start, the host should mint a nonce and write a context digest.
Submission atomically writes a single envelope such as:

```json
{
  "schema_version": 1,
  "run_id": "20260820T...",
  "turn_id": "01J...",
  "plan_digest": "sha256:...",
  "context_digest": "sha256:...",
  "finalizers": {
    "commit": {
      "schema_version": 1,
      "repositories": [
        {
          "repo_id": "linked:7fd1...",
          "decision": "commit",
          "message": "feat(finalizers): add manifest protocol"
        },
        {
          "repo_id": "external:291a...",
          "decision": "refuse",
          "reason": "The only dirty path predates this run."
        }
      ]
    }
  }
}
```

The exact IDs should be host-issued opaque identifiers, not path-derived user input.
The context can display the canonical path and project name for comprehension while the
executor resolves the ID from the pinned inventory.

Reject stale run/turn IDs, a changed plan or context digest, missing selected payloads,
extra unselected payloads, unknown repositories, duplicate decisions, and schema
violations. Keep attempted invalid submissions as numbered diagnostic artifacts, but
only one atomic `final_submission.json` may be current.

---

## 8. Built-in commit provider

### 8.1 Coverage rules

For every repository with host-classified agent-attributable dirty paths, the commit
payload must contain exactly one repository decision:

- `commit` — request one finalization commit/stitch for the remaining attributable
  work; or
- `refuse` — decline to commit and provide a non-blank reason.

No entry is required for a clean repository or for a repository containing only
unchanged pre-run dirt. The host must recompute coverage at submission and again before
execution, because a tool may have changed state since `context` was read.

A refusal is valuable evidence, but it is not success. The built-in instance should
default to `refusal: fail`: record the structured refusal and reason, then fail the run
if attributable dirt remains. A project owner may later choose a distinct policy such
as `warn`, but prompt text must never weaken it. A paused merge/rebase checkpoint is
always blocking and cannot be converted into a refusal.

### 8.2 One final commit per dirty repository in version 1

The phrase “commits/stitches for each repo” does not require the finalizer to become a
commit-series planner. SASE's current safe primitive stages everything except explicit
exclusions, and splitting remaining dirt into several commits would require a new
include-set ownership protocol with partial-tree failure semantics.

Version 1 should therefore permit one pending finalization commit per dirty repository.
If an agent needs several semantic commits, it can create them during its main turn via
`/sase_git_commit`; those successes already appear in `commit_results.json`. The final
submission only accounts for remaining dirt. A future multi-commit extension should be
designed separately around disjoint, host-validated path partitions.

### 8.3 Protect pre-existing paths

The executor should derive exclusions, not trust the model to identify them. For a
`commit` decision:

1. compare the current tree with the repository's entry baseline;
2. classify attributable versus protected pre-existing paths;
3. generate repeated `-x|--exclude` arguments for protected paths;
4. invoke the existing stitch workflow for the pinned repository;
5. re-inventory and validate the ledger, provenance, and remaining paths.

If the agent asks not to include one of its attributable paths, treat that as a
path-level refusal with a reason and leave the repository decision unsatisfied under
the default policy. Never make an unexplained exclusion a route to a green run.

The commit method (`create_commit`, GitHub PR, and so on) should be resolved from the
launch and repository policy, not freely supplied in the manifest. The manifest may
provide schema-bounded inputs such as the commit message and existing workflow flags,
but it may not select arbitrary commands or credentials.

### 8.4 Delegate to `sase stitch create`

The built-in executor should call the same public workflow as `/sase_git_commit` and
then trust only the workflow's durable result:

- invoke `sase stitch create` in the pinned repository with host-derived exclusions;
- require a matching run-owned result in `commit_results.json` by SHA or tree;
- require Patch/Stitch bookkeeping when the selected VCS method creates it;
- recheck the repository after execution;
- let the existing discarded-work guard reject dirt that vanished without evidence.

This keeps all VCS-provider semantics, publication, trailers, remote integration, and
Patch/Stitch updates in one implementation.

---

## 9. Merge-conflict protocol

Repositories must be finalized serially. Only one `commit_state.json` checkpoint can
be active for a run, and a paused Git operation must be resolved before later
repositories are touched.

The controller's conflict path should be:

1. the commit executor invokes `sase stitch create`;
2. exit code 2 produces `needs_agent`, identifies the repository and checkpoint, and
   stops the current finalizer round;
3. SASE forces a repair turn using the same provider/model/effort and explicitly tells
   the agent to use `/sase_git_commit`'s conflict-resume procedure;
4. the agent resolves markers, stages the resolution, continues the paused Git
   operation, and runs `sase stitch create --resume` through the skill wrapper;
5. `--resume` completes publication and writes/upserts the normal result ledger;
6. the controller verifies that ledger and re-inventories before proceeding to the next
   repository.

It must **not** retry the original create command while a checkpoint exists. It must
not auto-stash, reset, abort, skip, or create a replacement commit. Existing benign
machine-owned merge handling inside a VCS provider can remain, but every unresolved
content conflict stays with an agent.

If the repair budget is exhausted, fail with the checkpoint and repository still
intact so a successor can inspect and resume it. Preserving evidence is more important
than returning the workspace to a cosmetically clean state.

---

## 10. Turn lifecycle and bounded recovery

The controller should use explicit agent-shell context rather than the current
incidental `SASE_AGENT_TIMESTAMP` test. A caller of `invoke_agent` opts into
finalization by passing a resolved plan, artifact directory, run ID, and turn ID.
Standalone provider calls without that context are not silently enrolled.

For each successful provider return:

1. **Declaration check.** Validate a current submission for this turn.
2. **One omission recovery.** If absent or invalid, force one narrowly scoped provider
   turn instructing the agent to invoke `/sase_final`. Mint a new declaration turn ID
   linked to the original turn; a second omission or invalid submission fails.
3. **Execution.** Run selected providers by stage and dependency order.
4. **Agent repair.** A provider may return `needs_agent` with a schema-bounded repair
   prompt. Run at most the instance's configured attempt budget.
5. **Reconciliation.** Re-inventory host state and evaluate postconditions.
6. **Fixed point.** Repeat only when a declared mutating action created new obligations,
   up to a small global round cap.
7. **Result.** Write one aggregate `finalization_result.json` and only then allow the
   agent's normal done/completion path.

Keep three separate budgets instead of one ambiguous `max_passes`:

- exactly one missing-declaration recovery;
- `max_attempts` per selected finalizer for executor/agent repair;
- `max_rounds` for whole-plan convergence.

No-progress fingerprints should apply within and across rounds. The aggregate response
may include repair-turn content for continuity, as the current finalizer does, but the
artifact record must distinguish the original answer from finalization-only turns.

Intentional handoff termination remains exempt because it never reaches this successful
return path. Provider errors, user kills, and crashes should record an incomplete
finalization outcome, not start a surprise recovery turn while the primary execution is
already failing.

---

## 11. Result model and observability

Each provider result should use a small closed vocabulary:

- `satisfied` — executor completed and host postconditions pass;
- `needs_agent` — a recoverable condition such as a merge conflict requires a bounded
  repair turn;
- `refused` — the agent explicitly declined an obligation and supplied a reason;
- `error` — executor or validation failed;
- `not_triggered` — the host proved no current obligation exists.

Only the host may produce `not_triggered` or final aggregate success. A plugin's claim
of `satisfied` is evidence to inspect, not authority to skip postcondition validation.

Suggested durable artifacts:

```text
agent_meta.json                    resolved plan and directive operations
repo_baselines.json               entry baseline for every inventoried repo
final_context_<turn>.json         immutable context offered to the agent
final_submission_attempt_*.json   audit trail for rejected/accepted submissions
final_submission.json             current valid envelope
finalizer_<instance>_input_*.json exact executor inputs
finalizer_<instance>_result_*.json strict executor outputs
finalization_result.json          aggregate terminal result
commit_state.json                 existing resumable commit checkpoint
commit_results.json               existing authoritative commit ledger
```

`sase final show` and `sase agent show` should explain the resolved provider, source
distribution/config layer, selection reason, current obligation, attempts, and terminal
status. Refusal reasons should be prominent in failure notifications. Secrets must be
redacted before writing artifacts or building repair prompts.

---

## 12. Feature flag and migration

This change reaches the most safety-critical completion path and belongs behind a beta
flag. During implementation, create it only with:

```text
sase flag new pluggable_finalizers
```

That command will create the typed registry entry and its mandatory removal bead. The
flag should default off.

### Phase A — protocol without behavior change

- Add core wire types, repository entry baselines, provider discovery, config schema,
  CLI inspection commands, and artifacts.
- Add the built-in commit provider as an adapter around current code.
- Keep `_invoke.py` on the old path when the flag is off.
- In shadow tests, compare old dirty-state and new obligation inventories.

### Phase B — declaration handshake

- Add `%final`, `/sase_final`, `sase final context`, and `submit` under the flag.
- Make `commit` the only built-in/default instance.
- Require one current manifest and exercise the omission-recovery turn.
- Preserve all current auto-commit exceptions and discarded-work checks inside the
  adapter until their ownership is deliberately redesigned.

### Phase C — out-of-process reference plugin

- Add a harmless reference provider, preferably a read-only verifier, to prove plugin
  discovery, schema validation, timeouts, result artifacts, and selection.
- Then test a mutating task-bead provider so the mutate/seal/fixed-point behavior is
  exercised before third parties depend on it.

### Phase D — default-on and cleanup

- Soak the flagged path on real agents.
- Default the beta on only after conflict, multi-repo, pre-existing-dirt, family attach,
  crash, and refusal telemetry shows parity or improvement.
- Remove the hard-coded branch and retire the flag only through its flag bead.

The old behavior must remain reachable while the flag exists. Tests must cover both
states; a disabled branch may not parse `%final` as if it worked.

---

## 13. Required test matrix

The implementation is not safe based only on unit tests of JSON validation. At minimum:

| Area | Cases |
| --- | --- |
| Selection | defaults, add/remove/clear, unknown instance, required instance removal, dependency cycle, missing plugin |
| Turn binding | valid submission, stale run, stale turn, stale context digest, duplicate submission, recovery omission twice |
| Repository ownership | clean repo, pre-existing dirt, new repo opened mid-run, linked repo, external repo, SDD sidecar, family attach |
| Coverage | all commit, mixed commit/refuse, blank refusal reason, unknown repo ID, state changed after context |
| Commit evidence | direct SHA, rebased tree, missing trailer, ledger mismatch, dirty work deleted without commit |
| Exclusions | protected pre-run path excluded, attributable path cannot disappear through unexplained exclusion |
| Conflicts | exit 2, paused checkpoint, successful `--resume`, failed repair, later repos untouched, no accidental second create |
| Ordering | mutator dirties repo before seal, verifier after seal, second fixed-point round, no-progress/global cap |
| Plugin isolation | timeout, crash, malformed JSON, oversized output, shell metacharacters treated as data, selected vs unselected bad provider |
| Feature flag | exact old path off, generic built-in parity on, targeted `%final` error off |
| Handoffs | plan, monitor, question, and pipe terminate without declaration enforcement |

Two end-to-end assertions are release blockers:

1. no agent can reach normal completion with unexplained attributable dirty work; and
2. a real merge conflict is always left in a resumable checkpoint and resolved by an
   agent before finalization proceeds.

---

## 14. Risks and decisions to keep explicit

### 14.1 “Custom finalizer” is not “arbitrary stop script”

The provider boundary should be intentionally narrower than a generic lifecycle hook.
Plugins get a versioned context, a schema-bounded declaration, and a result channel.
They do not get to alter the selected plan, claim another repository by path, inject a
new prompt without host approval, or declare aggregate success.

### 14.2 `%final:none` is powerful

Clearing finalizers can intentionally bypass commit policy. Some installations will
want `commit` to be required. Support `required: [commit]` in host configuration, and
reject directives that remove required instances. This is authorization, not a prompt
preference.

### 14.3 Refusal policy needs one safe default

Recording a refusal reason improves diagnosis, but treating every recorded refusal as
success would weaken the existing guarantee. Use `fail` for the built-in commit
instance. If `warn` is later supported, it must be an administrator/project config
choice and the completion result must visibly say the workspace was left dirty.

### 14.4 External side effects may not be reversible

Fixed-point re-execution is safe only for idempotent providers. Require every provider
to consume an operation ID and make result writes idempotent. A retry must return the
prior durable result or safely continue it, not create a second issue, bead, or remote
message.

### 14.5 Scope should be fixed for version 1

The prior report proposed both `turn` and `agent` scope. The current request explicitly
asks agents to invoke the skill at the end of every turn, and SASE currently finalizes
after successful provider calls. Implement `turn` scope only first. Adding `agent`
scope later is reasonable, but mixing both into the first state machine would obscure
when declarations become stale and which child shell owns repository changes.

---

## 15. Sources and inspected artifacts

### SASE sources

- Prior report:
  [`pluggable_finalizers_final_directive.md`](../202607/pluggable_finalizers_final_directive/pluggable_finalizers_final_directive.md)
- Historical plan from the plans repository:
  `202607/commit_vars_finalizer.md` at Git commit `123306be`
- Current finalizer:
  `src/sase/llm_provider/commit_finalizer.py` and its `commit_finalizer_*` modules
- Invocation boundary: `src/sase/llm_provider/_invoke.py`
- Commit execution and results: `src/sase/workflows/commit/` and
  `src/sase/xprompts/skills/sase_git_commit.md`
- Directive parsing: `src/sase/xprompt/_directive_*`
- Plugin precedent: `src/sase/config/file_hooks.py`, task-type providers, and
  `src/sase/plugins/inventory.py`
- Handoff precedents: `src/sase/xprompts/skills/sase_plan.md` and
  `src/sase/xprompts/skills/sase_monitor.md`
- Rust wire precedent: `sase-core/crates/sase_core/src/axe_chop/`

### External primary sources

- [Kubernetes finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/)
- [Python Packaging Authority entry-point specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- [Git rebase conflict and continuation behavior](https://git-scm.com/docs/git-rebase)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)

---

## 16. Recommended solution

Implement **a flag-gated, host-owned finalization controller** with a versioned,
turn-bound declaration manifest. Add plugin-discovered declarative providers and
config-defined named instances; make `%final` operate only on those instance names;
make `commit` the default and optionally required built-in instance. Require
`/sase_final` to submit typed intent, force one recovery turn when it is omitted, and
fail on the second omission.

For commit finalization, require exactly one `commit` or reasoned `refuse` decision for
every host-detected repository containing agent-attributable dirt. Treat refusal as a
structured failure by default, protect pre-existing paths with host-derived exclusions,
and limit version 1 to one remaining finalization commit per dirty repository. Use the
existing `commit_results.json` ledger as proof and invoke only the existing
`sase stitch create` / `--resume` workflow.

Run mutating finalizers before the commit sealing stage, read-only verification after
it, and reconcile to a bounded fixed point. When a commit conflicts, stop later
repositories, force an agent repair turn, and resume the existing checkpoint—never
retry, stash, abort, reset, or reimplement Git recovery in the generic engine.

This is the smallest design that genuinely generalizes SASE finalization while keeping
the property that makes the current finalizer valuable: an agent cannot quietly finish
after discarding, ignoring, or ambiguously owning repository changes.
