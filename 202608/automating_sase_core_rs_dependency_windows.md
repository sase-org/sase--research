# Automating `sase-core-rs` dependency windows

**Date:** 2026-08-09  
**Scope:** `sase` and `sase-core` release/development workflows  
**Question:** How can SASE stop assigning agents routine work to raise the
published `sase-core-rs` dependency floor and upper bound?

## Executive finding

The recurring work exists because a **release-time package invariant** is being
enforced during **feature integration**.

Development and most CI lanes already build `sase_core_rs` from the current
`sase-core` source checkout and deliberately override the published dependency
window. The window in `pyproject.toml` matters primarily when building or
installing a published `sase` distribution. Nevertheless, every normal pull
request also runs a lane against the *oldest published core allowed by that
window*. As soon as Python starts using a new binding or corrected behavior,
that lane forces the feature agent to perform the release-metadata ratchet:

1. edit the range in `pyproject.toml`;
2. regenerate `uv.lock`;
3. edit a hard-coded expected version in a test; and
4. wait for a core release if the required version is not on PyPI yet.

That timing is the fundamental problem. The best place to choose and verify the
published core window is the pending `sase` Release Please PR, immediately before
a `sase` release, not every feature PR.

The recommended design is therefore a **release-boundary core-window ratchet**:

- add one idempotent synchronization tool;
- have the existing Release Please branch updater run it before regenerating
  `uv.lock`;
- run published-wheel compatibility checks on that release PR;
- leave ordinary feature PRs testing the current `sase-core` source revision;
- optionally wake the updater from a `sase-core` publish event, with a scheduled
  or manual recovery path.

This coalesces many core releases and feature-level edits into at most one
dependency-window update per `sase` release.

## Evidence from the current repositories

The observations below use `sase` commit
`9bce277c942cc10009b984f1cc309920a36c29a6` and `sase-core` commit
`b8b6570e37ae5d302593eae89086348ca0d4eb0d`.

### Current contract

`sase/pyproject.toml` currently declares:

```toml
"sase-core-rs>=0.21.3,<0.22.0"
```

The lower bound means every released `sase` installation must receive at least
the core behavior SASE expects. The upper bound treats the next pre-1.0 minor as
a possible breaking boundary. PEP 440 makes the two comma-separated clauses a
logical AND, so both bounds constrain resolution
([PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)).

The local-development path is intentionally different:

- `Justfile` builds from the sibling/linked `sase-core` checkout or a wheel
  supplied by CI, using an override so dependency resolution does not replace it
  with a version inside the published range.
- `.github/workflows/ci.yml` checks out `sase-org/sase-core` and builds one wheel
  from its default branch for the source-based lint and test jobs.
- `tools/validate_sase_core_rs_version` warns when the source checkout is ahead
  of the declared window and separately checks that a declared minimum exists on
  PyPI.
- The `published-core-minimum-smoke` job creates a clean environment containing
  the exact lower bound, statically checks every discoverable
  `require_rust_binding(...)` call, and runs several behavioral smokes.

This split is sound: source-based CI answers “does current SASE work with current
core?”, while the published-minimum lane answers “would the released package
metadata install a core that can run current SASE?” The mistake is requiring the
second answer to remain true at every intermediate feature commit.

### Measured churn

On the current `sase` history from 2026-07-24 through 2026-08-09:

- **50 commits** changed the `sase-core-rs` requirement in `pyproject.toml`;
- **47** of those also changed `uv.lock`;
- **48** also changed the hard-coded minimum in
  `tests/test_sase_core_rs_telemetry_smoke_tool.py`;
- **18 commits (36%)** touched no files beyond those three and were essentially
  standalone dependency-window chores; and
- the other **32** repeated the metadata work inside a larger feature or fix.

Over the same period, current `sase-core` history contains **68 distinct release
versions**, while `sase` contains **8 releases**. A bot PR for every core release
would therefore reproduce the high-frequency churn in a different place. A
release-boundary ratchet would have reduced 50 SASE window edits to at most 8 in
this sample—an **84% reduction**—and removed all 18 standalone chores from agent
work.

The release histories also show that “oldest required core” and “latest core”
have not always been identical. Four of the eight sampled `sase` releases had a
floor below the newest core release commit available at the time. Automating the
latest version unconditionally therefore changes policy: it favors lockstep and
simplicity over retaining the broadest possible backward-compatible window.
That choice should be explicit.

## Why the existing release flow is the right insertion point

The `sase` publish workflow already has nearly the mechanism needed:

1. Release Please creates or refreshes
   `release-please--branches--master` after a push to `master`.
2. The `sync-lockfile` job detects that branch, checks it out, runs `uv lock`,
   commits any change, and pushes back to the same branch.
3. Merging the Release Please PR creates the release; the build and install
   smoke then resolve `sase-core-rs` from PyPI.

The proposed ratchet is a small extension of step 2, not a second release
system. Release Please PRs are durable accumulators: many feature commits can be
represented by one eventual release candidate. That is exactly the desired
coalescing boundary.

`uv` also provides the required deterministic primitive. Its documentation says
that an existing lockfile retains locked versions unless an upgrade is
explicitly requested, and supports upgrading one package to an exact version
with `uv lock --upgrade-package package==version`
([uv locking and upgrading](https://docs.astral.sh/uv/concepts/projects/sync/#upgrading-locked-package-versions)).
This avoids refreshing unrelated packages.

## Options considered

| Option | Benefit | Main problem | Verdict |
|---|---|---|---|
| Add a `just bump-core` helper for agents | Makes the three edits reliable and cheap | Agents still need a task, must choose timing/version, and create merge conflicts | Useful implementation primitive, not the automation boundary |
| Dependabot | Native GitHub service; current GitHub docs list `uv` as a supported ecosystem | Generic dependency updating does not express SASE's policy for ratcheting both a semantic lower bound and the next-breaking upper bound; scheduled PRs also lag a just-published core | Not a good fit for this special dependency |
| Renovate with PEP 621/`uv.lock` support | Renovate explicitly supports PEP 621 and `uv.lock`, with configurable range strategies | Still tends toward one update PR per core release, adds another bot, and does not know whether SASE requires or is compatible with a release | Capable, but solves the mechanics at the wrong cadence |
| Dispatch one SASE PR from every `sase-core` publish | Immediate and can carry the exact version | Would have produced roughly 68 downstream update events in the sample period; needs cross-repository credentials and careful race handling | Too noisy unless it only wakes a coalescing release-branch updater |
| Remove the upper bound or declare an unversioned dependency | Eliminates some edits | Allows a future breaking core to be selected for an older SASE release; does not guarantee a sufficiently new lower bound | Unsafe |
| Exact-pin core or bundle the extension into SASE | Makes the pair fully lockstep | Reduces resolver flexibility or turns SASE into a platform-wheel build, substantially changing release architecture | Disproportionate |
| Compute the oldest passing core by testing every release | Preserves the widest valid window | Potentially expensive; correctness is only as complete as the compatibility test suite; version compatibility can be non-monotonic across pre-1.0 minor lines | Possible later refinement |
| Ratchet on the pending SASE release PR | Coalesces updates, reuses existing automation, and puts the check where package metadata matters | Requires an explicit policy for selecting the release candidate | Best fit |

Dependabot's current package-ecosystem reference lists `uv`, and Renovate's PEP
621 manager documents `uv.lock` maintenance
([Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#package-ecosystem),
[Renovate PEP 621 manager](https://docs.renovatebot.com/modules/manager/pep621/)).
Renovate can deliberately bump an in-range dependency range, but that only
addresses text transformation, not the SASE/core compatibility decision
([Renovate `rangeStrategy`](https://docs.renovatebot.com/configuration-options/#rangestrategy)).

## Proposed design

### 1. Create one tested synchronization command

Add a repository-owned tool, for example:

```text
tools/sync_sase_core_rs_window \
  --version 0.21.3 \
  [--check] [--allow-downgrade]
```

It should:

1. parse versions with `packaging.version.Version`, not handwritten tuple logic;
2. reject pre-releases, yanked releases, malformed versions, and downgrades by
   default;
3. verify that the exact version is fully visible on PyPI before changing the
   floor;
4. compute the compatibility ceiling from an explicit project policy—for the
   current pre-1.0 policy, `0.MINOR.PATCH` becomes `<0.(MINOR+1).0`;
5. structurally replace only the `sase-core-rs` requirement in
   `pyproject.toml`;
6. run
   `uv lock --upgrade-package sase-core-rs==VERSION` so unrelated locked
   packages remain stable;
7. assert that `uv.lock` contains the requested version and matching root
   requirement; and
8. be idempotent and support a non-mutating `--check` mode.

The PyPI JSON API exposes the latest project metadata and release files, which
is sufficient for discovery and publication checks
([PyPI JSON API](https://docs.pypi.org/api/json/)). The tool should still accept
an explicit `--version`; workflows become more reproducible when selection and
mutation are separate operations.

The test with a literal `"0.21.3"` should be replaced. It currently turns every
valid ratchet into a third hand-edited fixture without testing an independent
fact. Better invariants are:

- the declared floor is canonical and parseable;
- its ceiling matches the compatibility policy;
- the locked direct dependency equals the declared floor on a release branch;
- the exact floor is published; and
- the installed floor passes binding and behavior checks.

### 2. Extend the existing release-branch updater

Rename `sync-lockfile` to something like `sync-release-metadata` and have it:

1. locate the pending Release Please branch as it does today;
2. select the candidate `sase-core-rs` version;
3. run the synchronization tool;
4. regenerate the root-package version in `uv.lock` in the same operation;
5. commit `pyproject.toml` and `uv.lock` together; and
6. push to the existing Release Please branch.

Do not create a separate dependency PR. The release PR is already the review
surface for the artifact that will ship.

The default candidate policy should be:

> Select the newest fully published stable core release, update the SASE window
> to that release's minor train, and require the release compatibility lane to
> pass before the Release Please PR can merge.

This adopts explicit lockstep-at-release semantics. It is simple, deterministic,
and matches the fact that normal CI already validates SASE against core's default
branch. If preserving the oldest compatible core becomes a user-facing support
goal, add an `--oldest-passing` selector later; do not make the first version of
the automation search dozens of historical wheels.

### 3. Move the published-floor gate to the release candidate

Ordinary feature PRs should continue to:

- build the current `sase-core` source wheel;
- run lint and tests against it; and
- fail if current Python and current core are incompatible.

They should not be required to keep the *previous published SASE artifact's*
minimum-core metadata current. Remove the ordinary-PR requirement from
`published-core-minimum-smoke`.

Run an expanded version of that job on
`release-please--branches--master` after the synchronizer pushes. It should
install the exact declared core wheel from PyPI and run:

1. `tools/check_sase_core_rs_bindings`;
2. the existing semantic smoke tools;
3. the contract-marked tests against the published wheel; and
4. ideally the full non-visual suite once, because this is the release
   candidate rather than every candidate core version.

The existing post-tag fresh-install smoke remains a final defense, but the
release PR must go red before merge if the selected core is absent or
incompatible. That avoids creating a SASE release tag whose package cannot be
published successfully.

### 4. Make triggering prompt and self-healing

A SASE `master` push will normally be enough: it refreshes the Release Please PR
after feature work lands, at which point the required core release should
already be on PyPI.

For the race where core publishes after the last SASE push, add both:

- a manual workflow dispatch; and
- either a low-frequency scheduled reconciliation or a `repository_dispatch`
  sent after the core PyPI publish succeeds.

The cross-repository event should only *wake* the SASE-side reconciler. The
reconciler must query current PyPI state and update the one pending release
branch, so duplicate, delayed, or out-of-order events cannot regress the floor.
GitHub documents `repository_dispatch` for externally triggered workflows
([workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#repository_dispatch)).

The source repository's `GITHUB_TOKEN` cannot access another repository. If a
cross-repository wake-up is added, prefer a narrowly installed GitHub App token;
GitHub explicitly recommends an App when a workflow needs resources outside its
own repository
([GitHub App authentication in Actions](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)).
The existing `SASE_RELEASE_TOKEN` may work technically, but expanding a broad PAT
should not be the default security design.

Use one concurrency group for release-branch synchronization, always re-read the
latest default-branch and PyPI state when a run starts, and refuse downgrades.
GitHub concurrency permits one running and one latest pending run, which is
useful for coalescing bursts
([Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)).

## Failure modes and safeguards

| Failure | Safeguard |
|---|---|
| Core tag exists but PyPI upload is not yet visible | Ratchet only after exact-version JSON and required distribution files are visible; retry with a bounded backoff |
| Core publish partially uploads | Verify the required wheel/sdist set, not only `info.version` |
| Older dispatch finishes after a newer one | Ignore event version for final selection, re-read PyPI, serialize runs, and reject downgrades |
| Latest core is breaking for current SASE | Source-core CI should already fail; the published-wheel release lane is the authoritative block |
| No pending SASE release PR exists | Exit successfully without creating a dependency-only PR; the next SASE master push will create/update the release candidate |
| `uv lock` changes unrelated dependencies | Use the package-specific exact upgrade and fail if the diff exceeds the expected lock entries |
| Version policy changes at core 1.0 | Keep ceiling calculation in one tested policy function rather than embedding string arithmetic in YAML |
| Automation silently weakens coverage | Make the release compatibility job a required check and retain the post-build fresh-install smoke |

## Suggested implementation sequence

1. Add the synchronization tool and focused unit tests, including patch/minor
   transitions, idempotence, PyPI absence, yanked/pre-release rejection, and
   downgrade refusal.
2. Replace the hard-coded minimum-version test with structural invariants.
3. Extend the existing release-branch `sync-lockfile` job to update the core
   window and lockfile atomically.
4. Change CI so published-minimum compatibility is required on the Release
   Please PR, while ordinary PRs rely on source-core CI.
5. Run one SASE release in report-only mode, showing the proposed version and
   diff without pushing it.
6. Enable branch updates and make the compatibility lane required.
7. Add manual dispatch immediately; add cross-repository dispatch plus scheduled
   recovery only if the normal SASE-push trigger leaves observable gaps.
8. Stop creating feature/phase tasks whose sole purpose is dependency-window
   ratcheting once the release gate has proven itself.

## Acceptance criteria

- A feature PR can use a newly landed core binding without editing
  `pyproject.toml`, `uv.lock`, or a version literal.
- Normal CI still tests that PR against current core source.
- A pending SASE release PR automatically receives one canonical core-window
  update, regardless of how many core versions were published during the SASE
  development interval.
- The release PR cannot merge unless its exact PyPI core floor exposes every
  required binding and passes behavioral compatibility tests.
- Re-running the synchronizer produces no diff; stale events cannot downgrade
  the floor.
- The published SASE wheel's fresh-install smoke resolves the same core version
  tested on the release PR.
- An unavailable or incompatible core blocks the SASE release with a precise
  diagnostic, rather than spawning a task for an unrelated feature agent.

## Recommended solution

Implement a **release-boundary `sase-core-rs` window ratchet on the existing
SASE Release Please branch**. Build one idempotent tool that selects an explicit,
fully published stable core version, rewrites `pyproject.toml`, upgrades only
`sase-core-rs` in `uv.lock`, and verifies the result. Invoke it from the existing
release-branch lockfile-sync job, and make an exact-published-wheel compatibility
lane required on that release PR. Remove the published-minimum requirement from
ordinary feature PRs, which should continue testing against current core source.

For the initial policy, select the newest fully published core and treat the
release compatibility check as the decision gate. This deliberately adopts
lockstep-at-release behavior; it cuts the sampled metadata churn by about 84%,
eliminates standalone bump beads, and adds no new dependency bot or PR stream.
If maintaining the oldest possible compatible core later becomes a real support
requirement, extend the same tool with an `--oldest-passing` search—without
moving version maintenance back into feature-agent work.
