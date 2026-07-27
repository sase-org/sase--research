# An `actstat`-driven CI watch / release-merge chop

Research for a single AXE lumberjack chop that sweeps GitHub Actions health across the SASE repositories with
`actstat`, then either launches a fix agent for a red repository or merges that repository's pending release-please /
release-plz PR.

Everything below was verified live on 2026-07-27 against the real repos, the real `actstat` binary, and the real AXE
chop framework in this workspace. Line references point at `sase-org/sase` unless noted.

---

## 1. The question

> "A lumberjack chop that uses `actstat` to check the most recent GitHub CI workflow run for all SASE repos. It either
> launches an agent to fix the CI failures or merges all release-please and release-plz release PRs, which should
> automatically trigger a release of the appropriate packages."

Three sub-questions fall out of that:

1. **Can `actstat` actually answer the question the chop needs to ask?** (Partly — see §2.)
2. **Which AXE mechanism should carry each half?** The fix half is a *launch proposal*; the merge half is a *direct side
   effect*. AXE treats those very differently. (§3)
3. **What is the safe eligibility rule for an unattended merge that publishes packages to PyPI/crates.io?** This is the
   part with real blast radius, and the live evidence says the current setup gives you no safety net at all. (§4)

---

## 2. What `actstat` gives you, and what it does not

`actstat` is Bryan's own Rust CLI (`github.com/bbugyi200/actstat`, v0.1.0, installed at `~/.cargo/bin/actstat`,
registered with SASE as the external project `gh_bbugyi200__actstat`). Its config lives at
`~/.config/actstat/config.yml` and currently expands `org: sase-org` (minus `sase-android`), `org: bobs-org`, plus
`bbugyi200/dotfiles` and `bbugyi200/actstat`.

### 2.1 Measured behavior

| Property           | Measured value                                                                       |
| ------------------ | ------------------------------------------------------------------------------------ |
| Full org sweep     | **3.8 s** wall clock, 9 JSONL records across 4 orgs/repos sources                    |
| Machine output     | `--format json` (one document) or `--format jsonl` (one record per line), pipe-clean |
| Record types       | `active_commit`, `commit`, `repo_error`                                              |
| Exit codes         | `0` normal, `1` operational error / all-error report, `2` with `--fail-on-failure`   |
| Failure isolation  | One inaccessible repo becomes a `repo_error` row, never aborts the sweep             |
| Auth               | `ACTSTAT_GITHUB_TOKEN` → `GH_TOKEN`/`GITHUB_TOKEN` → `gh auth token` → anonymous     |

3.8 s comfortably fits inside a chop `timeout`, and the JSONL shape is directly consumable — no scraping.

### 2.2 What it reports

- **`active_commit`** — per repo, the single most recently *started* `in_progress` run, across all branches.
- **`commit`** — per repo, the most recent **settled** commits on the **default branch**, grouped by SHA, with
  problem runs → problem jobs → problem steps and their GitHub URLs. `-n/--limit` controls how many (default 1).
- **`repo_error`** — per repo or per failed org expansion.

### 2.3 The three gaps that shape the design

**Gap 1 — `actstat` never looks at pull requests.** Settled history comes only from the default branch. Release PRs
live on `release-please--branches--*` / `release-plz-*` branches, so `actstat` cannot tell you whether a release PR
exists, or whether its checks are green. The merge half of this chop needs `gh`, not `actstat`.

**Gap 2 — `cancelled` counts as red, and that is frequently a lie.** Per the README, a settled commit is green only if
every retained run concluded `success`, `skipped`, or `neutral`; `failure`, `cancelled`, `timed_out`,
`action_required`, `startup_failure`, and `stale` all make it red. `sase-org/sase` uses
`concurrency: cancel-in-progress`, so a push that supersedes an in-flight run leaves a `cancelled` run behind
permanently. A live capture of `sase-org/sase` at commit `fa6b004` shows exactly this ambiguity:

```json
{ "workflow": "CI", "conclusion": "cancelled", "jobs": [
    { "name": "published-core-minimum-smoke", "conclusion": "failure", "steps": [{"name": "Check every required binding exists in the published minimum", "conclusion": "failure"}] },
    { "name": "lint",        "conclusion": "failure",  "steps": [{"name": "Lint", "number": 17}] },
    { "name": "visual-test", "conclusion": "cancelled" },
    { "name": "test (3.14)", "conclusion": "cancelled" } ] }
```

The run says `cancelled`; two jobs genuinely **failed** and three were merely superseded. A chop that treats
`conclusion != success` as "launch a fix agent" will fire on every superseded run in a busy repo. **The chop needs its
own red predicate**, not `actstat`'s. Proposed rule:

> A repo is *actionably red* iff some retained run has `conclusion ∈ {failure, timed_out, startup_failure,
> action_required}`, **or** has `conclusion == cancelled` **and** contains at least one job or step whose conclusion is
> `failure`. A run that is `cancelled` with no failing job is "superseded", not red.

**Gap 3 — the newest commit may not be the reported one.** `actstat` reports the newest *settled* commit and skips
newer unsettled ones. In the live capture, `sase-org/sase` reported settled `fa6b004` as red while newer `352c693` was
still `in_progress`. Acting on `fa6b004` risks chasing a failure that the newer commit already fixed. Two cheap
mitigations, both worth taking:

- Skip the fix path for any repo that has a non-empty `active` record (something newer is already in flight).
- Make the fix prompt re-run `actstat` itself so the agent diagnoses *current* state rather than the snapshot. The
  user's existing `#actstat` xprompt already does exactly this.

---

## 3. What the AXE chop framework can and cannot carry

Read `docs/axe.md` §§ "Script Chops", "Structured Results and Launch Proposals", and "Triggers, Guards, Dedupe, and
Targets" (`docs/axe.md:423-563`) for the authoritative contract. The load-bearing facts:

- **Every chop is an external executable**, invoked as `<script> --context <context.json>`. Legacy `agent:` /
  `xprompt:` chop fields are *rejected*: "scheduled agent work must originate from a script's structured launch
  proposals" (`docs/axe.md:340-341`). So this must be a script chop.
- **Agents are launched by writing proposals**, not by calling `sase run`. The script writes a schema-versioned JSON
  document to `$SASE_CHOP_RESULT_FILE`; the runner validates the whole document, injects the workspace ref, a
  deterministic `%id(...)` with `tribe=chop`, and any `%wait`, then launches. `src/sase/chops/sdk.py` provides
  `load_chop_invocation`, `ChopLogger`, `ChopResultBuilder`, `launch_proposal`.
- **A chop script may also perform direct side effects.** Nothing stops it shelling out to `gh pr merge`. That is the
  only available route for the merge half — proposals launch agents, they do not merge PRs.
- **Per-proposal dedupe**: a proposal's own `dedupe_key` takes precedence over the chop's `once_per` template. Perfect
  fit for "one fix agent per (repo, red SHA)".
- **Name-collision idempotency**: "A proposal that supplies an explicit `agent_name` treats a name collision at launch
  as idempotency, not failure" — the run records a skip and relinks waits. A stable `ci_fix.<repo>` name therefore
  gives you at most one in-flight fix agent per repo, for free.
- **Guards**: `inhibit_if` supports `changespec`, `agent_hood`, `agent_clan`. These are per *chop instance*, so they are
  too coarse for a single-instance chop that fans out over repos internally (see §5.1). `sase agent list -j` gives the
  script live agent names + project for a precise per-repo guard instead.
- **Lifecycle**: a run with accepted proposals goes `launched` → `action_succeeded`/`action_failed` once linked agents
  reach terminal state. Pure side-effect runs end `ok` / `no_op` / `check_error`.
- **Precedent exists.** `bugyi_chops` (`github.com/bbugyi200/bugyi-chops`, v0.2.0, installed into the sase tool venv as
  `bugyi_chop_recent_bug_audit`, `bugyi_chop_recent_improvement_audit`, `bugyi_chop_toobig_split`) is already the home
  for personal proposal-emitting chops, with `src/bugyi_chops/_common.py` supplying `run_chop`, `result_with_summary`,
  `proposal_workspace`, `safe_fragment`. **The new chop belongs there**, not in the `sase` repo.

### 3.1 `for_each` does not enumerate SASE repos

`for_each: source: projects` expands to enabled **SASE projects**, whose rows are built at
`src/sase/axe/_config_targets.py:136-156` (`name`, `project`, `vcs`, `workspace`, `workspace_dir`, `enabled`,
`launchable`). Today `sase project list` returns exactly **three** enabled projects: `actstat`, `bob-cli`, `sase`.
`sase-core`, `sase-github`, `sase-telegram`, and `sase-nvim` are *linked repos* of the `sase` project, not projects, so
they would not appear. `for_each` over projects is therefore the wrong fan-out for "all SASE repos".

---

## 4. The live release/CI inventory — and the safety finding

### 4.1 Repositories and release tooling

`sase-org` has 17 repos; the code repos with CI are `sase`, `sase-core`, `sase-github`, `sase-telegram`, `sase-nvim`,
`sase-google`, `sase-gchat` (`sase-android` is excluded in the `actstat` config; `sase-tui` is empty; the `--sdd`,
`--plans`, `--research`, `--agents` sidecars have no CI).

| Repo            | Release tool                       | Release-PR head branch                                       | Label                  |
| --------------- | ---------------------------------- | ------------------------------------------------------------ | ---------------------- |
| `sase`          | release-please (`publish.yml`)     | `release-please--branches--master`                            | `autorelease: pending` |
| `sase-github`   | release-please                     | `release-please--branches--master--components--sase-github`   | `autorelease: pending` |
| `sase-telegram` | release-please                     | `release-please--branches--master--components--sase-telegram` | `autorelease: pending` |
| `sase-core`     | release-plz (`release-plz.yml`)    | `release-plz-2026-07-27T13-26-47Z`                            | *(none)*               |

Detection rule that matches all four live PRs: **`headRefName` starts with `release-please--` or `release-plz-`.**
Do *not* key off author — every one of these PRs is authored by `bbugyi200` (they use a PAT, `SASE_RELEASE_TOKEN`), not
a bot. Do not key off the label alone either — release-plz sets none.

Discovery cost: one `gh search prs --owner=sase-org --state=open 'release'` returned exactly those four PRs in
**0.85 s**, but the text query is fragile. A per-repo `gh pr list -R <repo> --json number,headRefName,isDraft` over the
handful of repos `actstat` reported is deterministic and still cheap.

### 4.2 The safety finding: nothing is protecting these branches

```
$ gh api repos/sase-org/{sase,sase-core,sase-github,sase-telegram}/branches/master/protection
→ 404 "Branch not protected"   (all four)
```

**No branch protection exists on any SASE repo.** GitHub will merge a release PR whose checks are failing, with no
complaint. `sase-org/sase` PR #243 (`chore(master): release 0.12.0`) is live proof — `lint` and
`published-core-minimum-smoke` are **failing**, three test jobs are **pending**, and GitHub still reports
`mergeable: MERGEABLE`, `mergeStateStatus: UNSTABLE`. A naive `gh pr merge` would publish `sase` 0.12.0 to PyPI off a
red tree.

**The chop is the only gate that will ever exist.** That single fact should drive the whole eligibility design.

All four repos are **squash-merge-only** (`mergeCommitAllowed: false`, `rebaseMergeAllowed: false`,
`squashMergeAllowed: true`), so `gh pr merge --squash` is the only valid method. Squash preserves the PR title as the
commit subject (`chore(master): release 0.12.0`), which is what release-please's post-merge detection expects.

By contrast, `sase-core` PR #35 (`chore: release v0.11.3`) is the clean case:

```json
{"n":35,"branch":"release-plz-2026-07-27T13-26-47Z","mergeable":"MERGEABLE","state":"CLEAN",
 "checks":[{"name":"cargo fmt + clippy + test","status":"COMPLETED","conclusion":"SUCCESS"},
           {"name":"Conventional PR title","status":"COMPLETED","conclusion":"SUCCESS"},
           {"name":"Cargo version guard","status":"COMPLETED","conclusion":"SKIPPED"},
           {"name":"maturin build + import smoke","status":"COMPLETED","conclusion":"SUCCESS"}]}
```

`mergeStateStatus: CLEAN` + an all-green rollup is the signature to require.

### 4.3 Release ordering matters

`pyproject.toml:46` pins `sase-core-rs>=0.11.2,<0.12.0`, and `sase` CI has a `published-core-minimum-smoke` job that
checks every required binding exists in the *published* minimum. So `sase-core` must release before a `sase` release
that depends on new bindings. Good news: gating on green is self-correcting — `sase`'s release PR simply stays red
until `sase-core`'s release publishes, then becomes eligible on a later tick. Still worth merging in a deliberate
order (core → plugins → sase) so the happy path converges in the fewest ticks.

### 4.4 What merging actually triggers

- **release-please** (`.github/workflows/publish.yml`): merge → `push` to master → `release-please-action@v5` (with two
  retries) creates the tag + GitHub release → the `build` job publishes when `release_created == true`.
- **release-plz** (`sase-core/.github/workflows/release-plz.yml`): merge → `push` to master → `release-plz release`
  tags + creates the GitHub release → a wheel matrix builds and publishes to PyPI. Publishing is deliberately
  self-healing: build/publish jobs gate on "the tagged version is missing from PyPI", and a `23 */6 * * *` cron heals
  missed publishes. So a merge that half-fails recovers on its own — the chop does not need to babysit publication.

---

## 5. Alternatives considered

### A. One chop, one `actstat` sweep, internal per-repo fan-out — **recommended**

A single chop instance (no `for_each`) runs `actstat -f jsonl` once, classifies each repo, and then per repo either
emits a fix proposal or merges an eligible release PR.

- **+** One sweep serves both decisions. The merge gate *needs* the red/green verdict; sharing it in-process makes it
  impossible for the two halves to disagree.
- **+** Matches the ask ("a lumberjack chop") and the natural per-repo either/or.
- **+** One chop run in AXE history = one coherent story per tick.
- **−** Loses AXE-managed per-target cadence/checkpoints; the script owns per-repo dedupe (via proposal `dedupe_key`
  and a stable `agent_name`) and per-repo guards (via `sase agent list -j`).
- **−** Mixes a proposal path and a side-effect path in one run. Acceptable: the result status is `ok` with proposals,
  and the merge outcomes go in `counters` + the summary line.

### B. Two chops in one lumberjack: `ci_watch` + `release_merge`

- **+** Clean separation of "proposes agents" from "mutates GitHub"; independent history, cadence, and blast radius.
- **−** **The red/green predicate gets duplicated in two places.** If they ever drift, you merge a release PR on a red
  master. That is precisely the failure this whole thing exists to prevent.
- **−** Two `actstat` sweeps per cycle (cheap, ~4 s each — not the real objection) or a shared cache file (extra state).
- Verdict: rejected on the correctness risk, not the cost. If you later want the split, share one snapshot file written
  by the sweep chop and consumed by the merge chop, so there is still exactly one predicate.

### C. `for_each` per-repo chop instances

- **+** Free per-repo `run_every`, run history, checkpoints, and dedupe state; per-instance `inhibit_if`.
- **−** `source: projects` only sees the 3 enabled SASE projects (§3.1) — wrong set entirely.
- **−** Literal `for_each` rows would work, but then each instance runs its own `actstat`. `--repo` is only a *filter*:
  per the README it "does not avoid organization API calls", so N instances = N full org expansions.
- Verdict: rejected. It multiplies API cost to buy per-repo state the script can hold more cheaply.

### D. One chop that just launches a "CI warden" agent to do everything

- **+** Trivial script; the agent reads `actstat`, decides, and merges.
- **−** Puts a non-deterministic LLM directly in the loop that publishes packages to PyPI and crates.io, with **no
  branch protection behind it** (§4.2). A hallucinated "looks green to me" ships a broken release.
- **−** Burns an agent every tick just to discover "everything is green".
- Verdict: rejected for the merge half. The merge decision must be deterministic code. Keep agents for the *fix* half,
  where their judgment is the point.

### E. A cron/systemd job outside AXE

The `actstat` README even ships a cron recipe. But you would lose chop run history, live log tailing in the AXE tab,
`sase axe chop run --dry-run`, guards, dedupe, the proposal launch path, and the `action_succeeded` lifecycle that ties
the chop to its agents' completion. AXE is strictly better here.

---

## 6. Recommended solution

> **One script chop, `ci_watch`, in the `bugyi-chops` package. One `actstat` sweep per tick against a chop-owned
> `actstat` config. Per repo: if actionably red → propose one fix agent (deduped on repo + SHA, stable agent name); if
> green and a release PR exists and is *fully* green → `gh pr merge --squash`. Otherwise no-op with an explicit
> reason.**

### 6.1 Decision table (evaluated per repo, per tick)

| Default-branch state                        | Release PR                      | Action                                           |
| ------------------------------------------- | ------------------------------- | ------------------------------------------------ |
| `repo_error` row                            | —                               | Count `errors`, log, no action                   |
| `active` run in flight                      | —                               | Skip: `reason=run_in_flight`                     |
| Actionably red (§2.3)                       | —                               | **Propose fix agent** (deduped)                  |
| Superseded-only `cancelled`                 | —                               | Skip: `reason=superseded`                        |
| Green                                       | none                            | No-op                                            |
| Green                                       | exists, draft or not all-green  | Skip: `reason=release_pr_not_ready`              |
| Green                                       | exists, `CLEAN` + all-green     | **`gh pr merge --squash`**                       |

Fix and merge are mutually exclusive *by construction* — merge requires green, fix requires red.

### 6.2 Eligibility predicate for an unattended merge

All of the following, or no merge:

1. `headRefName` starts with `release-please--` or `release-plz-`.
2. `isDraft == false`.
3. `mergeable == "MERGEABLE"` and `mergeStateStatus == "CLEAN"`. If `mergeable == "UNKNOWN"`, **skip this tick** —
   GitHub computes it asynchronously; it will be known next tick.
4. Every `statusCheckRollup` entry has `status == "COMPLETED"` and `conclusion ∈ {SUCCESS, SKIPPED, NEUTRAL}`. Any
   `PENDING`/`QUEUED`/`IN_PROGRESS` entry disqualifies — do not merge mid-run.
5. The repo's default branch is green per the same `actstat` sweep (§2.3 predicate).
6. `--squash` only (all repos are squash-only).
7. Optional but recommended: a `vars.max_merges_per_tick` cap (start at `1`) so a bad predicate cannot cascade across
   every repo in one tick.

Conditions 3–4 are belt and braces: with green checks the PR reads `CLEAN` anyway (as `sase-core` #35 does), but since
**nothing else is protecting these branches**, redundancy is the right call.

### 6.3 Repository scope

`~/.config/actstat/config.yml` is a *user* config spanning `bobs-org` and `bbugyi200/*`. The chop should not inherit
surprise repos, and expanding unrelated orgs adds API calls and error rows (recall: a report of only error rows exits
`1`). Give the chop **its own config**:

```yaml
# ~/.config/sase/actstat-ci-watch.yml  (source it from the chezmoi repo)
projects:
  - org: sase-org
    exclude:
      - sase-org/sase-android
      - sase-org/sase-tui
```

Point at it with `env: { ACTSTAT_CONFIG: ... }`, and *also* filter the parsed output against a `vars.repos` allowlist as
defense in depth. Two independent scoping mechanisms, so neither a config edit nor a new org repo can silently widen
what the chop merges.

### 6.4 Config sketch

Add to `~/.config/sase/sase_athena.yml` under `axe.lumberjacks` (canonical source:
`home/dot_config/sase/sase_athena.yml` in the chezmoi repo):

```yaml
axe:
  lumberjacks:
    ci_watch:
      description: |-
        Watch GitHub Actions health across SASE repos and drive fixes or releases every five minutes

        Runs every 300 seconds because CI runs take minutes, not seconds, and both actions it can take — launching a
        fix agent and merging a release PR — are expensive to repeat. Put remote CI observation here; ChangeSpec
        lifecycle work and local maintenance belong in their own lanes.

        The single chop owns its own actstat config so unrelated orgs are never swept, and it is the only gate on
        release merges because no SASE repo has branch protection.
      interval: 300
      chop_timeout: "120s"
      chops:
        ci_watch:
          script: bugyi_chop_ci_watch
          description: |-
            Fix red SASE repos or merge their green release PRs from one actstat sweep

            Runs actstat once per tick over the sase-org repositories, classifies each default branch, then proposes at
            most one fix agent per red repository and squash-merges release-please or release-plz PRs whose own checks
            are fully green.

            - A run cancelled with no failing job is treated as superseded, not red, so concurrency cancels do not
              launch agents.
            - Merges require mergeStateStatus CLEAN plus an all-green rollup; vars.max_merges_per_tick bounds the
              blast radius.
          run_every: "5m"
          timeout: "120s"
          env:
            ACTSTAT_CONFIG: /home/bryan/.config/sase/actstat-ci-watch.yml
          vars:
            actstat_bin: /home/bryan/.cargo/bin/actstat # see §6.7
            gh_bin: gh
            repos:
              - sase-org/sase
              - sase-org/sase-core
              - sase-org/sase-github
              - sase-org/sase-telegram
              - sase-org/sase-nvim
            merge_order: [sase-core, sase-github, sase-telegram, sase-nvim, sase]
            max_merges_per_tick: 1
            fix_enabled: true
            merge_enabled: false # flip on after a dry-run soak — see §6.8
```

### 6.5 Script skeleton

New module `src/bugyi_chops/ci_watch.py`, entry point
`bugyi_chop_ci_watch = "bugyi_chops.ci_watch:main"` in `pyproject.toml`, reusing `_common.run_chop` /
`result_with_summary` so failures fail closed into a `check_error` result.

```python
RED_CONCLUSIONS = {"failure", "timed_out", "startup_failure", "action_required"}
RELEASE_BRANCH_PREFIXES = ("release-please--", "release-plz-")
GREEN_CHECKS = {"SUCCESS", "SKIPPED", "NEUTRAL"}


def actionably_red(commit: dict) -> bool:
    """True only for a genuine failure, not a concurrency-superseded cancel."""
    for run in commit.get("runs", []):
        conclusion = (run.get("conclusion") or "").lower()
        if conclusion in RED_CONCLUSIONS:
            return True
        if conclusion == "cancelled" and any(
            (job.get("conclusion") or "").lower() == "failure"
            or any((s.get("conclusion") or "").lower() == "failure" for s in job.get("steps", []))
            for job in run.get("jobs", [])
        ):
            return True
    return False


def build(invocation):
    sweep = run_actstat(invocation)            # actstat -f jsonl, parse, index by repo
    live = live_agent_names()                   # sase agent list -j
    result = result_with_summary(invocation, "ci_watch", counters)

    for repo in ordered_repos(invocation, sweep):
        report = sweep[repo]
        if report.error:            counters["errors"] += 1;   continue
        if report.active:           counters["in_flight"] += 1; continue
        if actionably_red(report.commit):
            if f"ci_fix.{slug(repo)}" in live:
                counters["fix_inflight"] += 1;  continue
            result.propose(
                fix_prompt(repo, report),
                workspace=f"gh:{repo}",
                proposal_id=f"fix_{slug(repo)}",
                agent_name=f"ci_fix.{slug(repo)}",         # collision == idempotency
                dedupe_key=f"ci_fix:{repo}:{report.commit['sha']}",
            )
            counters["fix_proposed"] += 1
        else:
            counters["merged"] += maybe_merge_release_pr(invocation, repo)
    return result
```

The fix prompt reuses the xprompt Bryan already wrote (`xprompts.actstat` in `~/.config/sase/sase.yml`), which tells
the agent to run `actstat` itself — which is exactly the Gap-3 mitigation:

```python
def fix_prompt(repo: str, report) -> str:
    name = f"ci_fix_{slug(repo)}_{report.commit['sha'][:7]}"
    return f"#pr({name}) #actstat:{repo.split('/')[-1]}\n\nFailing run: {report.worst_run_url}"
```

`#pr(...)` in a proposal prompt is already proven in production by `bugyi_chops/recent_audits.py:_prompt`. Inline
xprompt references remain valid in proposal prompts; only standalone `#!workflow` references are forbidden
(`docs/axe.md:512-513`).

### 6.6 Idempotency and guards, layer by layer

| Layer                                 | Prevents                                                        |
| ------------------------------------- | ---------------------------------------------------------------- |
| `dedupe_key = ci_fix:<repo>:<sha>`    | Re-launching for the same red commit across ticks               |
| `agent_name = ci_fix.<slug>`          | A second concurrent fix agent for the same repo (collision skip) |
| `sase agent list -j` pre-check        | Proposing at all while a fix agent is live — keeps logs quiet   |
| Skip when `active` is non-empty       | Chasing a commit a newer run may already have fixed             |
| `max_merges_per_tick`                 | A predicate bug cascading across every repo at once             |
| AXE `already_running` chop status     | Overlapping chop runs                                           |

Note the AXE dedupe subtlety: once-per keys for accepted proposals that never started are released immediately, and a
started proposal releases its key if the agent *fails* — so a failed fix agent is retried on a later tick rather than
being permanently suppressed. That is the behavior you want here.

### 6.7 Environment: PATH and auth

Chop env is composed over `os.environ` of the axe daemon (`src/sase/axe/chop_env.py:34`), which inherits whatever
`sase axe start` was launched with. `actstat` lives at `~/.cargo/bin/actstat` and `gh` must also resolve — do not
assume either is on the daemon's `PATH`.

**Do not try to extend `PATH` through chop `env`.** Each env value is resolved whole: a string is used verbatim, and a
`{env: NAME}` / `{file: ...}` / `{pass: ...}` mapping is replaced entirely by the resolved value
(`src/sase/axe/chop_env.py:85-140`). There is no interpolation, so `PATH: "/home/bryan/.cargo/bin:{env: PATH}"` would
be passed literally and would break every subprocess the chop spawns. Instead pass absolute binary paths through
`vars` (as sketched above) and have the script fail closed with `check_error` and an explicit reason when a binary is
missing. `actstat` picks up `gh auth token` automatically, so no token needs to appear in config.

### 6.8 Rollout

1. **Register the target repos as SASE projects, deliberately.** Only `sase` is currently an enabled project.
   A proposal with `workspace: "gh:sase-org/sase-core"` will *implicitly create* project `gh_sase-org__sase-core` and
   clone a workspace on first launch. Do that once by hand for `sase-core`, `sase-github`, `sase-telegram`, `sase-nvim`
   so the first automated run is not also doing first-time project setup.
   ⚠️ **Side effect to accept knowingly:** newly enabled projects immediately join `for_each: source: projects`
   expansions in your *existing* chops — `refresh_docs` will start fanning out to them. Decide that on purpose.
2. **Ship the script with `merge_enabled: false`.** Run `sase axe chop run ci_watch --dry-run -V` and let the fix half
   soak for a few days. Verify the red predicate does not fire on superseded `cancelled` runs.
3. **Enable merging with `max_merges_per_tick: 1`.** Watch the first few real merges land and publish.
4. **Add a notification.** `sase notify create` (stdin JSON, `-s ci_watch`, `-t release`) for every merge and every fix
   launch, so releases are never silent. Keep the payload bounded — the AXE log contract forbids unbounded command
   output.
5. **Reconsider branch protection.** Even a minimal ruleset requiring `CI` to pass would turn the chop from *the only*
   safety gate into a second one. Worth doing regardless of this chop.

---

## 7. Open questions for Bryan

1. **Repo scope** — should `sase-google`, `sase-gchat`, and `bbugyi200/dotfiles` be in scope, or is this strictly
   `sase-org` code repos? (They appear in the shared `actstat` config today but have no release automation.)
2. **Auto-merge appetite** — is fully unattended release merging the goal, or would a `sase gate` confirmation for the
   first N merges feel better given §4.2? The gate skill exists and would cost one notification per release.
3. **Fix-agent model/effort** — the proposal can set `model`/`effort`. Default (`@default` at `xhigh`) or something
   cheaper for a first-pass CI triage?
4. **Should the chop also handle a red *release PR*** (as `sase` #243 is today), or only a red default branch? Right
   now the red-master fix agent will usually fix both, since the release PR is based on master.

---

## Sources

- `actstat` README and `--help`, external checkout via `sase repo open actstat`
- `docs/axe.md:246-665` (configuration, script chops, proposals, triggers/guards/dedupe, run history)
- `src/sase/axe/_config_types.py:51-123`, `src/sase/axe/_config_targets.py:126-172`, `src/sase/axe/chop_env.py:24-38`
- `src/sase/chops/sdk.py`, `src/sase/scripts/sase_chop_refresh_docs.py`
- `bugyi-chops` v0.2.0 — `src/bugyi_chops/_common.py`, `src/bugyi_chops/recent_audits.py`
- `sase/memory/xprompts.md` (launch grammar, `#pr`, workspace refs)
- Live `gh` queries against `sase-org` on 2026-07-27: repo list, open PRs, `statusCheckRollup`, merge settings,
  branch protection
- `~/.config/sase/sase.yml` (`xprompts.actstat`), `~/.config/sase/sase_athena.yml` (existing chop lanes)
