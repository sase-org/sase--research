---
create_time: 2026-07-27
updated_time: 2026-07-27
status: research
---

# GitHub CI Repair and Release-PR Lumberjack Chop

## Question

What is the safest and simplest way to build an AXE lumberjack chop that:

1. uses `actstat` to inspect GitHub Actions across the SASE organization;
2. launches repair agents when the current default-branch CI run is genuinely failing; and
3. otherwise merges every ready release-please and release-plz release PR, triggering the repositories' existing
   release workflows?

The important word is **current**. A periodic automation must not react to a red run that has already been superseded,
merge a release PR while its generator is still updating it, or interpret a partial GitHub API failure as “everything
is green.”

## Executive conclusion

Build one host-specific Python chop in the existing `bugyi-chops` package and configure it as one ten-minute lumberjack
in `sase_athena.yml`. Invoke `actstat --format jsonl` once per tick as the primary inventory and diagnostic source, then
use narrowly scoped `gh` reads to revalidate the current default-branch HEAD, exact `CI` workflow state, unsettled
release workflows, and release-PR head/check state immediately before acting.

Use one global, fail-closed state machine:

1. incomplete observation → `check_error`, no action;
2. queued/in-progress/superseded state → `no_op`, wait for the next tick;
3. one or more current CI failures → emit one deduplicated `#pr(...)` repair-agent proposal per failing repository and
   merge nothing;
4. all monitored repositories green and settled → preflight the complete release-PR batch, then squash-merge each PR
   with its expected head SHA.

Before enabling direct merges, make one small SASE runner change: pass `source` and `dry_run` into
`ChopScriptContext` (and preferably `SASE_CHOP_SOURCE` / `SASE_CHOP_DRY_RUN`). Today `sase axe chop run --dry-run`
prevents returned launch proposals from running, but the flag is not visible to the subprocess. Without that change, a
“dry run” of this chop could still execute `gh pr merge`.

## What exists today

### `actstat`

The installed command is `actstat` (one word), version `0.1.0`; `act stat` invokes the unrelated `nektos/act` command.
The current `actstat` implementation is unusually well suited to the observation half of this job:

- It expands organization entries from `~/.config/actstat/config.yml`, fans out concurrently, and isolates individual
  repository failures.
- JSONL is pipe-clean and emits `active_commit`, `commit`, and `repo_error` records.
- A red settled commit includes problem workflow runs, failed jobs, failed steps, and direct GitHub URLs. That is
  excellent bounded evidence for a repair-agent prompt.
- It groups completed default-branch runs by commit, deduplicates reruns, and reports a commit only after the retained
  runs have settled.
- `--fail-on-failure` distinguishes red settled status from operational failure, but JSONL parsing is still necessary:
  partial `repo_error` records do not necessarily make the overall process fail.

The current personal config already expands `sase-org` (excluding `sase-android`) as well as unrelated organizations
and repositories. The chop should therefore filter records to `sase-org/` rather than create a second repository
inventory.

There are four limitations relevant to unattended mutation:

1. `active_commit` is only the single newest `in_progress` run across all branches. It does not represent queued,
   waiting, pending, requested, or every simultaneously active workflow.
2. The settled record is a commit-level aggregate. There is no `--workflow CI` view that proves which exact workflow is
   the latest one for the current default-branch HEAD.
3. Successful repositories with neither a qualifying settled commit nor a current running workflow are omitted. An
   absent JSONL row is therefore not proof that a configured repository is healthy.
4. The report does not expose the repository's current default-branch HEAD independently of the reported commit SHA.

These are reporting choices, not defects. They mean that `actstat` should discover candidates and provide diagnostics,
while a small authoritative pre-action check closes races. GitHub's workflow-runs API supports filtering by branch,
head SHA, workflow, status, and all relevant queued/completed states, so the needed revalidation is straightforward:
[GitHub workflow-runs API](https://docs.github.com/en/rest/actions/workflow-runs).

### AXE chop behavior

AXE already provides the right framework:

- A chop is a short script, run as `<script> --context <context.json>`.
- A schema-versioned result can contain validated launch proposals.
- The runner, not the script, injects workspace/name/tribe scaffolding, launches agents, tracks them to completion, and
  enforces `wait_on`.
- Proposal `dedupe_key` values are reserved after successful work and released after failed work, which maps cleanly to
  “one repair agent per failed run.”
- Scheduled instances have bounded run history, timeouts, counters, evidence paths, and operator-visible logs.

One chop invocation should inspect the organization once and return zero or more proposals. `for_each: {source:
projects}` is the wrong fan-out primitive here: the enabled SASE project inventory currently contains `actstat`,
`bob-cli`, and `sase`, not every GitHub repository in `sase-org`. Per-project expansion would also rerun the same
organization-wide `actstat` query several times.

The direct-merge path exposes one missing safety signal. `dry_run` is handled after the script exits, when the runner
decides whether to launch proposed agents; it is absent from `ChopScriptContext`. Direct side effects performed by a
script cannot currently distinguish a scheduled apply from a manual dry run. Pass both the run `source`
(`scheduled`/`manual`/`oneshot`) and `dry_run` into the subprocess context before adding this chop.

### Existing personal extension points

This automation is personal and organization-specific, so it should not become a built-in SASE chop.

- `bugyi-chops` already packages the personal proposal-emitting chops, depends on the public `sase.chops` SDK, exposes
  console-script entry points, and has strict unit tests. It is the natural home for
  `bugyi_chop_github_ci_release`.
- `chezmoi` already owns `~/.config/actstat/config.yml`, the reusable `actstat` xprompt, and the athena-only lumberjacks
  in `sase_athena.yml`. It is the natural home for cadence and policy configuration.
- The existing `actstat(repo=...)` xprompt is worth reusing inside repair prompts, but the chop should add the pinned
  run SHA/URL and a `#pr(...)` rollover itself.

This split keeps generic mechanics in the Python package and mutable host policy in configuration.

## Release behavior verified in the SASE repositories

The relevant package repositories currently use these strategies:

| Repository | Strategy | Release PR identity | What a merge triggers |
| --- | --- | --- | --- |
| `sase-org/sase` | release-please | `release-please--branches--...` plus `autorelease: pending` | `Publish` on a push to `master`; release-please creates the GitHub release, then build/smoke/PyPI jobs run |
| `sase-org/sase-github` | release-please | `release-please--branches--...` plus `autorelease: pending` | the same push-driven release-please/build/PyPI shape |
| `sase-org/sase-telegram` | release-please | `release-please--branches--...` plus `autorelease: pending` | the same push-driven release-please/build/PyPI shape |
| `sase-org/sase-core` | release-plz | branch starts with `release-plz-` | `Release-plz` on a push to `master`; it creates tags/releases and runs the guarded wheel/PyPI pipeline |

This agrees with the upstream tools' intended lifecycle: release-please maintains a release PR until the maintainer
merges it, and release-plz releases after its prepared PR is merged:
[release-please action](https://github.com/googleapis/release-please-action),
[release-plz introduction](https://release-plz.ieni.dev/docs).

During this research, open release PRs existed in all four repositories. Three were clean and green; the SASE release
PR still had running and failed checks. At the same time, `actstat` showed a newer SASE `CI` run in progress above an
older red settled run. This is the concrete race the state machine must handle: it should wait, not launch a fixer for
the older run and not merge the release batch.

The four package repositories currently permit squash merges only, have auto-merge disabled, and do not have protected
default branches. Consequently:

- do not use `--auto` or `--admin`;
- explicitly require a nonempty, fully terminal, green PR check rollup;
- require the PR to be non-draft, cleanly mergeable, and based on the repository's current default branch; and
- pin the head with `gh pr merge --squash --match-head-commit <sha>`.

GitHub's merge API makes this expected-head guard a first-class parameter and returns a conflict if the head changed:
[GitHub pull-request merge API](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request).

Release-plz deserves an additional settle guard. Its documentation warns about squash-merge races when a release is
merged before `release-plz release` has finished, and its release-PR job can force-push updates. Before merging a
release-plz PR, require the current default-branch `Release-plz` workflow to be terminal and require that there are no
queued or running `Release-plz` runs:
[release-plz configuration](https://release-plz.ieni.dev/docs/config).
Apply the analogous “generator settled” rule to the release-please repositories' `Publish` workflow.

## Proposed state machine

```text
scheduled tick
    |
    v
actstat --format jsonl
    |
    +-- command/config/auth failure or any sase-org repo_error
    |       -> check_error; no proposals; no merges
    |
    v
authoritative GitHub revalidation
    |
    +-- queued/in-progress workflow, HEAD mismatch, missing data
    |       -> no_op; wait for the next tick
    |
    +-- current default-branch CI failure(s)
    |       -> repair proposals, one per failed repo; merge nothing
    |
    v
all monitored CI and release-generator workflows settled green
    |
    v
discover + preflight every release PR
    |
    +-- any candidate draft, dirty, pending/red, ambiguous, or changed
    |       -> no_op/check_error; merge none
    |
    v
squash-merge each PR with expected head SHA
    |
    +-- race/failure partway through
            -> record exact partial result; next tick converges on the remainder
```

### Repository classification

“All SASE repositories” should mean all non-archived, non-fork `sase-org` repositories selected by the existing
`actstat` config that expose a workflow named exactly `CI`. Repositories without `CI`—for example SDD/agent sidecars or
an empty repository—are explicitly “not applicable,” not silently green.

For every applicable repository:

1. Resolve its current default branch and HEAD SHA.
2. Fetch the newest `CI` run for that branch and verify its `head_sha`.
3. If a newer HEAD has no run yet, or the newest run is queued/running, classify it as pending.
4. Only a terminal run on the current HEAD is actionable.
5. Treat `success`, `neutral`, and `skipped` as green. Treat `failure`, `cancelled`, `timed_out`, `action_required`,
   `startup_failure`, and `stale` as red only after proving that no newer run/HEAD supersedes them.

For the release gate, also require every workflow run associated with the current default-branch HEAD to be terminal
and non-red. That retains the useful “settled commit” semantics of `actstat` and prevents release-generator races.

### Failure mode

If at least one current CI run is red, emit proposals for every red repository in one result document. Each proposal
should contain:

- `workspace: gh:<owner>/<repo>`;
- a stable ID derived from repository and GitHub run ID;
- `dedupe_key: github-ci:<owner>/<repo>:<run-id>`;
- an agent name such as `ci_fix.<repo-slug>.<run-id>`;
- `%auto #pr(ci_fix_<repo>_<run-id>, status=ready)` followed by the existing `#actstat(repo=...)` xprompt;
- the authoritative head SHA, CI run URL, failed job/step names, and direct job URLs from `actstat`; and
- an instruction to verify that the failure is still current before editing, leaving the worktree unchanged if it was
  superseded.

Use a PR rollover, not `#commit`: an unattended fixer should not push straight to `master`. AXE's proposal dedupe means
the same run will not repeatedly launch agents. If the agent itself fails, the key is released and a later tick can
retry.

Do not launch for a previous red record while a newer run is queued or active. Cancelled runs deserve the same rule:
many cancellations are caused by superseding work rather than a repairable defect.

### Release mode

Enter release mode only when the complete monitored set is settled green. Keep release-enabled repositories and their
strategies in explicit configuration:

```yaml
release_repositories:
  sase-org/sase: release-please
  sase-org/sase-core: release-plz
  sase-org/sase-github: release-please
  sase-org/sase-telegram: release-please
```

For each open PR:

- release-please: require the configured branch prefix, `autorelease: pending`, expected base branch, and no draft;
- release-plz: require the configured `release-plz-` prefix, expected base branch, and no draft;
- require exactly one candidate per repository; ambiguity is an error, not a reason to guess;
- require a nonempty check rollup where every check is terminal and acceptable;
- require clean mergeability;
- save the exact PR number, URL, base SHA, and head SHA in the decision ledger.

Preflight the whole batch before the first mutation. Then re-read each PR immediately before merging and use its saved
head SHA with squash merge. Cross-repository all-or-nothing transactions do not exist, so a race can still produce a
partial batch. Make partial progress explicit and idempotent: already-merged PRs disappear from the next tick, while
unmerged PRs are reconsidered only after the newly triggered workflows settle.

## Configuration sketch

The athena overlay can own a dedicated low-frequency lane:

```yaml
axe:
  lumberjacks:
    github_ci_release:
      description: |-
        Repair settled SASE CI failures or merge a fully green release batch

        Runs every ten minutes because GitHub status and release automation do not need interactive latency. The chop
        observes the SASE organization once per tick, waits out unsettled runs, and gives CI repair priority over
        releases.
      interval: 600
      chop_timeout: 2m
      chops:
        github_ci_release:
          script: bugyi_chop_github_ci_release
          timeout: 90s
          description: |-
            Reconcile current SASE CI failures and ready release PRs

            Uses actstat JSONL for organization-wide diagnostics, revalidates mutable decisions with GitHub, emits one
            deduplicated repair proposal per current failed run, and otherwise squash-merges the fully preflighted
            release batch. Unknown or unsettled state fails closed.
          vars:
            organization: sase-org
            ci_workflow: CI
            release_repositories:
              sase-org/sase: release-please
              sase-org/sase-core: release-plz
              sase-org/sase-github: release-please
              sase-org/sase-telegram: release-please
```

There is no `for_each`: the script performs one bounded organization observation and emits per-repository proposals
only when needed.

## Implementation shape

Add `src/bugyi_chops/github_ci_release.py` and expose
`bugyi_chop_github_ci_release = "bugyi_chops.github_ci_release:main"`.

Keep the module split into testable pure decisions and narrow adapters:

- `ActstatClient`: runs `actstat --format jsonl`, bounds stderr, validates every record, and returns typed observations;
- `GitHubReader`: resolves repositories/default branches/HEADs, workflow state, PR details, and check rollups;
- `classify_tick(...)`: a pure function returning `ERROR`, `PENDING`, `REPAIR`, or `RELEASE`;
- `build_repair_result(...)`: creates `ChopResultBuilder` proposals and stable dedupe keys;
- `plan_release_batch(...)`: identifies exact release PRs and returns immutable expected-head plans;
- `merge_release_batch(...)`: performs only the final guarded squash merges and records partial outcomes;
- `main`: loads the public chop SDK invocation, checks `dry_run`, emits a compact summary, and atomically writes the
  structured result.

Do not parse human output, shell-interpolate repository names, or use `shell=True`. Validate all repo/workflow/branch
fields and pass argv lists to subprocesses. Let `gh` obtain its token from normal authentication; never copy credentials
into chop vars, evidence, or logs.

Write a small JSON evidence ledger beside the result containing only bounded decisions:

```json
{
  "mode": "repair",
  "repositories": {
    "sase-org/sase": {
      "state": "red",
      "head_sha": "...",
      "run_id": 123,
      "run_url": "https://github.com/..."
    }
  },
  "release_prs": [],
  "merged": []
}
```

Suggested summary counters are `repos`, `green`, `pending`, `red`, `proposals`, `release_candidates`, `merged`, and
`errors`. Ordinary logs should contain identifiers and URLs, not full prompts, API payloads, or command output.

## Dry-run prerequisite

Extend the SASE chop subprocess contract before enabling merge mode:

```python
@dataclass
class ChopScriptContext:
    ...
    source: str = "scheduled"
    dry_run: bool = False
```

Thread the values already accepted by `run_configured_chop_once` into the per-run context and export deterministic
environment mirrors. The SDK can expose them through `ChopInvocation` without requiring scripts to read ambient
variables.

The new chop's behavior in dry-run should be:

- perform read-only `actstat` and GitHub preflight;
- return/preview repair proposals normally;
- render the exact release merge plan in counters/evidence;
- execute no merges.

This also improves the generic third-party chop contract. Any future chop that performs a direct API mutation needs the
same signal.

## Alternatives considered

### A shell script that pipes `actstat` into `jq` and immediately calls `gh pr merge`

This is short but too easy to get wrong. It tends to conflate exit codes with complete observation, misses
`repo_error`, has awkward typed validation and testing, and encourages mutation before a complete batch preflight. It
also does not solve AXE's missing dry-run signal.

### Launch an agent to merge release PRs

Returning a single “release manager” proposal would inherit AXE's existing dry-run and lifecycle behavior with no SASE
change. It is a reasonable temporary prototype, but merging a known set of checked PRs is a deterministic operation.
Adding model latency, prompt interpretation, and a broad GitHub mutation task makes it less predictable and more
expensive than a guarded command.

### Add generic non-agent action proposals to AXE

The cleanest long-term abstraction would let a result propose typed actions such as `github.merge_pr`, which the runner
could validate, preview, deduplicate, and execute. That requires a new cross-language result schema, Rust validation,
Python executors, lifecycle semantics, and likely a provider/plugin API. One personal chop does not yet justify that
surface. If several mutation-capable chops appear, revisit it.

### Implement the chop as a SASE builtin

The mechanics are broadly reusable, but the policy is specifically Bryan's org, workflow names, release repositories,
and willingness to merge. Keeping it in `bugyi-chops` avoids turning personal release authority into a default SASE
capability.

## Test plan

The `bugyi-chops` suite should use fake `actstat`/`gh` adapters and cover:

- all green, no release PRs → `no_op`;
- current red CI → one pinned proposal, no merge calls;
- several red repositories → one independently deduplicated proposal per repo;
- old red plus newer queued/in-progress run → pending, no proposal;
- settled SHA differs from current default HEAD → pending;
- `repo_error`, malformed JSONL, auth failure, rate limit, or missing workflow → fail closed;
- sidecar/no-`CI` repository → explicitly not applicable;
- release-please and release-plz identity rules, including near-match false positives;
- draft, ambiguous, dirty, red-check, pending-check, empty-check, or changed-head release PR → no merge;
- all release PRs valid → complete preflight before ordered squash merges;
- expected-head mismatch during merge → visible partial failure, no unsafe retry in the same tick;
- `dry_run=True` → exact merge plan but zero mutation calls;
- bounded diagnostics and evidence with no token-like fields.

The SASE contract change needs tests proving that scheduled/manual/oneshot source and dry-run reach both context JSON
and environment, plus a regression test showing that proposal preview behavior is unchanged.

Before deployment:

1. run the chop in dry-run against live GitHub;
2. inspect its AXE preview, evidence, and candidate PR set;
3. temporarily configure an empty release-repository map and exercise a real no-op scheduled tick;
4. enable one release repository first;
5. verify that the merge triggers the expected release workflow and that the next tick waits while it runs;
6. enable the remaining repositories.

## Sources and observed commands

Primary references:

- [`actstat` repository and output contract](https://github.com/bbugyi200/actstat)
- [SASE AXE documentation](https://github.com/sase-org/sase/blob/master/docs/axe.md)
- [GitHub workflow-runs API](https://docs.github.com/en/rest/actions/workflow-runs)
- [GitHub PR merge API](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
- [release-please action](https://github.com/googleapis/release-please-action)
- [release-plz release lifecycle](https://release-plz.dev/docs/usage/release)
- [release-plz release-PR identity/configuration](https://release-plz.ieni.dev/docs/config)

Read-only live checks used `actstat -f jsonl`, `gh repo list`, `gh pr list`, `gh api repos/...`, and `gh pr merge --help`.
Repository source was inspected through SASE-managed checkouts for `sase`, `sase-core`, `sase-github`,
`sase-telegram`, `sase-nvim`, `actstat`, `bugyi-chops`, and `chezmoi`.

## Recommended solution

Implement `bugyi_chop_github_ci_release` in `bugyi-chops` as a single organization-wide Python reconciler, configure it
in athena's chezmoi-managed `sase_athena.yml` on a ten-minute cadence, and keep release strategy in an explicit
four-repository map. Use `actstat` JSONL for discovery and rich failure evidence, but require a fresh `gh` revalidation
of default-branch HEAD, all queued/running states, exact `CI` status, release-generator settlement, and every candidate
PR's checks/mergeability. Give failures global priority and emit one durable `#pr(...)` repair proposal per failed run;
only when the entire monitored set is settled green should the chop preflight and expected-head squash-merge the release
batch. First add `source` and `dry_run` to the SASE chop context so previewing this mutation-capable chop is genuinely
side-effect free.
