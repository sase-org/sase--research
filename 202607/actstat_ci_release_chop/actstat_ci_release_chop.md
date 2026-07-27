---
create_time: 2026-07-27
updated_time: 2026-07-27
status: research
---

# An `actstat`-Driven CI Watch / Release-Merge Lumberjack Chop (Consolidated)

Consolidation of two independent research reports (`actstat_ci_release_chop__a.md` by the codex researcher,
`actstat_ci_release_chop__b.md` by the claude researcher) plus lead-researcher verification of every load-bearing claim
against this workspace, the installed `actstat` binary, and live GitHub state on 2026-07-27.

## The question

Design an AXE lumberjack chop that uses `actstat` to check the most recent GitHub Actions CI run for all SASE repos,
then either (a) launches an agent to fix current CI failures or (b) merges all ready release-please / release-plz
release PRs, letting the repositories' existing workflows publish the packages.

## Recommended solution (summary)

**One script chop (`bugyi_chop_ci_watch`) in the `bugyi-chops` package, configured as a dedicated lumberjack lane in
the chezmoi-managed `sase_athena.yml`. One `actstat -f jsonl` sweep per tick over a chop-owned actstat config, then a
per-repo either/or: actionably-red default branch → one deduplicated `#pr(...)` fix-agent proposal; green default
branch with a fully green release PR → deterministic `gh pr merge --squash --match-head-commit <sha>`. Everything
unknown or unsettled fails closed.** Ship with `merge_enabled: false`, soak the fix half, then enable merging with
`max_merges_per_tick: 1` in dependency order (`sase-core` → plugins → `sase`). Before flipping merges on, land a small
SASE change threading `source`/`dry_run` into `ChopScriptContext` so `sase axe chop run --dry-run` is genuinely
side-effect-free for mutation-capable chops.

Details in §6; the reasoning that gets there follows.

## 1. Facts both researchers agree on (and the lead verified)

These were independently established by both reports and spot-checked by the lead researcher; treat them as settled.

**`actstat`** (v0.1.0, `~/.cargo/bin/actstat`; `act stat` is the unrelated nektos/act) is a great fit for the
*observation* half: a full org sweep takes ~4 s, `--format jsonl` is pipe-clean with `active_commit` / `commit` /
`repo_error` record types, per-repo failures are isolated as `repo_error` rows instead of aborting the sweep, and a red
settled commit carries problem workflows → jobs → steps with direct GitHub URLs — ideal bounded evidence for a fix
prompt. Auth resolves `ACTSTAT_GITHUB_TOKEN` → `GH_TOKEN`/`GITHUB_TOKEN` → `gh auth token`, so no token belongs in chop
config. Verified: the binary honors both `--config PATH` and an `ACTSTAT_CONFIG` environment variable (confirmed in the
binary's strings; the `--help` output only mentions the flag).

**Its three gaps shape the whole design:**

1. **`actstat` never looks at pull requests.** Settled history is default-branch only; release PRs live on
   `release-please--*` / `release-plz-*` branches. The merge half must use `gh`.
2. **`cancelled` counts as red, and that is frequently a lie.** `sase-org/sase` uses `concurrency:
   cancel-in-progress`, so superseded pushes permanently leave `cancelled` runs behind. A live capture (commit
   `fa6b004`) showed one `cancelled` run containing two genuinely failed jobs and three merely superseded ones. The
   chop needs its own red predicate (§6.1), not `actstat`'s.
3. **The reported settled commit may be superseded.** `actstat` reports the newest *settled* commit; a newer HEAD may
   already be in flight (live capture: red `fa6b004` reported while `352c693` ran). Additionally, `active_commit` is
   only the single newest `in_progress` run, queued/waiting runs are invisible, and a repo *absent* from the JSONL is
   not proven healthy. So `actstat` discovers and diagnoses; a narrow `gh` revalidation closes races before any action.

**AXE chop framework** (verified against `docs/axe.md` and `src/sase/axe/`): every chop is an external executable
invoked with `--context <context.json>`; agents are launched only via schema-versioned launch proposals in the result
file (legacy `agent:`/`xprompt:` chops are rejected); direct side effects like `gh pr merge` are allowed and are the
*only* route for the merge half. A proposal's own `dedupe_key` takes precedence over the chop's `once_per`
(docs/axe.md:540); an explicit `agent_name` treats a launch-time name collision as idempotency, not failure
(docs/axe.md:558); inline `#xprompt` references are fine in proposal prompts but standalone `#!workflow` references are
forbidden (docs/axe.md:513). Failed fix agents release their dedupe key, so a later tick retries naturally.

**`for_each: {source: projects}` is the wrong fan-out.** Enabled SASE projects are currently only `actstat`,
`bob-cli`, and `sase`; `sase-core`, `sase-github`, `sase-telegram`, `sase-nvim` are linked repos, not projects. And per
the actstat README, `--repo` filters output but does not avoid the org API calls, so N per-repo instances would each
pay a full sweep. One chop instance, one sweep, internal per-repo iteration.

**This is personal automation, not a SASE builtin.** The `bugyi-chops` package (already home to three
proposal-emitting chops with a shared `_common.py` `run_chop`/`result_with_summary` harness and strict tests) is the
natural home; chezmoi (`sase_athena.yml`, the actstat config, the existing `#actstat` xprompt) owns cadence and policy.

**Release tooling per repo** (verified live):

| Repo            | Tool                            | Release-PR head branch prefix | Merge triggers                                          |
| --------------- | ------------------------------- | ----------------------------- | ------------------------------------------------------- |
| `sase`          | release-please (`publish.yml`)  | `release-please--branches--…` | push → release-please tags/releases → build → PyPI      |
| `sase-github`   | release-please                  | `release-please--branches--…` | same shape                                              |
| `sase-telegram` | release-please                  | `release-please--branches--…` | same shape                                              |
| `sase-core`     | release-plz (`release-plz.yml`) | `release-plz-…`               | push → release-plz tags/releases → wheel matrix → PyPI  |

Detection rule matching all four live PRs: **`headRefName` starts with `release-please--` or `release-plz-`**. Do not
key off author (all are authored by `bbugyi200` via `SASE_RELEASE_TOKEN`, not a bot) or label alone (release-plz sets
none). All four repos are **squash-merge-only** with auto-merge disabled, so `gh pr merge --squash` and never
`--auto`/`--admin`; squash preserves the PR title as commit subject, which release-please's post-merge detection
expects. `sase-core`'s publish pipeline is self-healing (publish jobs gate on "tag missing from PyPI" plus a 6-hourly
cron), so the chop does not need to babysit publication after a merge.

## 2. The safety finding that drives everything

**No SASE repo has branch protection.** `gh api repos/sase-org/<repo>/branches/master/protection` returns 404 "Branch
not protected" for all four release repos (found by researcher B, re-verified by the lead on 2026-07-27). GitHub will
happily merge a release PR with failing checks: live proof was `sase` PR #243 (`chore(master): release 0.12.0`) showing
`lint` and `published-core-minimum-smoke` **failing**, three jobs pending — and still `mergeable: MERGEABLE`
(`mergeStateStatus: UNSTABLE`). A naive `gh pr merge` publishes 0.12.0 to PyPI off a red tree.

**The chop is the only gate that will ever exist between a tick and a PyPI/crates.io publish.** That is why the merge
decision must be deterministic code with redundant guards, and why "launch an agent to do the merging" was rejected by
both researchers: a hallucinated "looks green to me" ships a broken release with no backstop. (Rollout step §6.6.5:
adding even a minimal ruleset requiring `CI` would demote the chop from only-gate to second-gate, and is worth doing
regardless.)

## 3. Where the researchers disagreed, and how it resolves

### 3.1 Global state machine vs per-repo either/or → **per-repo wins**

Researcher A proposed a global gate: any current CI failure anywhere puts the whole org in repair mode and blocks *all*
merges; releases happen only when the entire monitored set is settled green. Researcher B proposed evaluating each repo
independently: red → fix agent; green with green release PR → merge.

The live evidence decides this. `sase`'s CI includes a `published-core-minimum-smoke` job that validates against the
*published* `sase-core-rs` minimum (`pyproject.toml` pins `sase-core-rs>=0.11.2,<0.12.0`). When `sase` master needs
bindings from an unreleased core version, `sase` CI is red **until core publishes**. Under the global rule that redness
blocks `sase-core`'s own (green) release PR — a deadlock only a human can break. Under the per-repo rule, core merges,
publishes, and `sase` goes green on a later tick: the system self-heals. Per-repo is also what the request asked for
("either launches an agent … or merges"), evaluated per repository.

Keep two of A's global instincts, scoped correctly: (a) process-level failures (actstat invocation/auth failure,
malformed JSONL, config errors) fail the whole tick closed as `check_error`; a `repo_error` row fails closed for that
repo only. (b) A's per-PR guards (expected-head pinning, generator-settled check) fold into the per-repo merge
predicate (§6.2).

### 3.2 Dry-run safety: SASE contract change vs `merge_enabled` var → **do both**

Researcher A found — and the lead verified against `src/sase/axe/chop_script_context.py:28` — that `ChopScriptContext`
carries no `dry_run` or `source` field. The runner applies `--dry-run` only to *proposal launching* after the script
exits; a script's direct side effects cannot tell a dry run from a scheduled apply. So today, "dry-running" this chop
could still execute `gh pr merge`. Researcher B sidestepped this with a `merge_enabled: false` config var.

These compose rather than compete. `merge_enabled` is the rollout switch and belt; the SASE change (thread `source` ∈
{scheduled, manual, oneshot} and `dry_run` into the context dataclass and `SASE_CHOP_SOURCE`/`SASE_CHOP_DRY_RUN` env
mirrors) is the braces, and improves the generic contract for any future mutation-capable chop. Sequence: ship the
chop with `merge_enabled: false` now; land the SASE change before ever flipping it to true, so `sase axe chop run
ci_watch --dry-run` is trustworthy from the first real merge onward. In dry-run the chop should still do the full
read-only preflight and render the exact merge plan in counters/evidence — just execute no merges.

### 3.3 actstat config: reuse the personal one vs dedicated → **dedicated config**

A would reuse `~/.config/actstat/config.yml` and filter to `sase-org/` in the script; B would give the chop its own
config. B is right: the personal config also expands `bobs-org` and `bbugyi200/*`, which adds API calls, foreign
`repo_error` rows (a report of only error rows exits 1), and surprise scope growth. The `ACTSTAT_CONFIG` env var is
confirmed to exist, so point the chop at a chezmoi-sourced `~/.config/sase/actstat-ci-watch.yml` (org `sase-org`,
excluding `sase-android` and the empty `sase-tui`), **and** keep A's in-script filter as a `vars.repos` allowlist —
two independent scoping mechanisms so neither a config edit nor a new org repo silently widens what the chop can merge.

### 3.4 Cancelled runs → B's precise predicate, plus A's supersession rule

A said "treat cancelled as red only after proving nothing supersedes it"; B turned that into a testable predicate.
Adopt B's, and A's supersession guard alongside it (§6.1).

### 3.5 Cadence: 300 s vs 600 s → minor; **start at 300 s**

With `max_merges_per_tick: 1`, a four-repo release train needs several ticks plus CI re-runs in between; 5 minutes
converges the happy path in a reasonable hour while staying far below any rate-limit concern (one sweep ≈ 4 s). 600 s
is a fine conservative alternative during initial soak.

## 4. Repository scope

"All SASE repos" concretely means the non-archived `sase-org` code repos with a `CI` workflow: `sase`, `sase-core`,
`sase-github`, `sase-telegram`, `sase-nvim` (plus `sase-google`/`sase-gchat` if desired — open question §7).
`sase-android` is already excluded in config, `sase-tui` is empty, and the `--sdd`/`--plans`/`--research`/`--agents`
sidecars have no CI: all "not applicable", never silently green. A repo absent from the sweep with no explanation is an
observation gap, not health.

## 5. Rejected alternatives (both researchers concur)

- **Shell script piping `actstat` into `jq` + `gh pr merge`** — conflates exit codes with complete observation, misses
  `repo_error`, untestable, and doesn't solve the dry-run gap.
- **Two chops (`ci_watch` + `release_merge`)** — duplicates the red/green predicate in two places; drift means merging
  a release on a red master, precisely the failure this exists to prevent.
- **`for_each` per-repo instances** — wrong source set (§1) and N× the API cost for state the script holds cheaply.
- **One "CI warden" agent that does everything** — puts an LLM in the publish path with no branch protection behind it,
  and burns an agent per tick to learn "all green". Agents belong on the *fix* side, where judgment is the point.
- **Generic non-agent action proposals in AXE** (typed `github.merge_pr` actions the runner validates/previews) — the
  right long-term abstraction, but one personal chop doesn't justify a new cross-language result schema. Revisit if
  more mutation-capable chops appear.
- **cron/systemd outside AXE** — loses run history, live log tailing, dry-run, dedupe, and the
  `action_succeeded` lifecycle tying the chop to its agents.

## 6. The recommended design in detail

### 6.1 Per-repo decision table (each tick)

| Default-branch state                          | Release PR                     | Action                              |
| --------------------------------------------- | ------------------------------ | ----------------------------------- |
| process-level actstat/auth/parse failure      | —                              | whole tick → `check_error`          |
| `repo_error` row                              | —                              | count `errors`, no action this repo |
| active/queued run in flight, or newer HEAD    | —                              | skip: `run_in_flight`               |
| actionably red (below)                        | —                              | **propose one fix agent** (deduped) |
| `cancelled` with no failing job               | —                              | skip: `superseded`, not red         |
| green                                         | none                           | no-op                               |
| green                                         | exists, not fully eligible     | skip: `release_pr_not_ready`        |
| green                                         | exists, eligible (§6.2)        | **`gh pr merge --squash`**          |

Fix and merge are mutually exclusive by construction: merge requires green, fix requires red.

**Actionably red:** some retained run has `conclusion ∈ {failure, timed_out, startup_failure, action_required}`, or is
`cancelled` with at least one job/step whose conclusion is `failure`. `stale` and job-less `cancelled` are superseded,
not red. Before proposing, revalidate with `gh` that the red run's `head_sha` is still the current default-branch HEAD
and no newer run is queued/running — `actstat`'s snapshot alone cannot prove currency (gap 3).

### 6.2 Merge eligibility — all of the following, or no merge

1. `headRefName` starts with `release-please--` or `release-plz-`; exactly one candidate per repo (ambiguity = error,
   not a guess); `isDraft == false`; base is the repo's current default branch.
2. `mergeable == MERGEABLE` and `mergeStateStatus == CLEAN`. On `UNKNOWN`, skip this tick (GitHub computes it
   asynchronously).
3. Nonempty `statusCheckRollup` where every entry is `COMPLETED` with conclusion ∈ {SUCCESS, SKIPPED, NEUTRAL}. Any
   pending/queued entry disqualifies.
4. The repo's default branch is green per this tick's sweep (§6.1 predicate).
5. Generator settled: no queued/running `Publish` (release-please) or `Release-plz` run on the default branch —
   release-plz documents a squash-merge race when merging while its release job is still finishing, and its PR job can
   force-push updates.
6. Re-read the PR immediately before merging and pin the head: `gh pr merge --squash --match-head-commit <sha>` (the
   merge API returns a conflict if the head moved).
7. `merged_this_tick < vars.max_merges_per_tick` (start at 1) — a predicate bug cannot cascade across every repo in
   one tick.

Guards 2–3 are redundant with each other by design: since nothing else protects these branches, redundancy is the
point. Iterate repos in `merge_order: [sase-core, sase-github, sase-telegram, sase-nvim, sase]` so the cross-repo
dependency (§3.1) converges in the fewest ticks; already-merged PRs vanish from the next sweep, making partial batches
naturally idempotent. Record every decision (PR number/URL, base/head SHA, reason) in a bounded JSON evidence ledger.

### 6.3 Fix-agent proposals

One proposal per actionably-red repo, in the single result document:

- `workspace: gh:sase-org/<repo>`; `dedupe_key: ci_fix:<repo>:<sha>` (same red commit never relaunches across ticks);
  stable `agent_name: ci_fix.<slug>` (name collision at launch = idempotency, so at most one in-flight fixer per repo);
  optionally pre-check `sase agent list -j` to keep skip-noise out of the logs.
- Prompt: `#pr(ci_fix_<repo>_<sha7>, status=ready)` rollover plus the existing `#actstat(repo=…)` xprompt — the agent
  re-runs `actstat` itself and diagnoses *current* state (the gap-3 mitigation), with the pinned run URL and failed
  job/step evidence from the sweep, and an instruction to leave the worktree unchanged if the failure was superseded.
  `#pr(...)` in proposal prompts is proven in production by `bugyi_chops/recent_audits.py`; a PR rollover rather than
  `#commit` keeps unattended fixers off `master`.
- AXE lifecycle does the rest: accepted-but-failed agents release the dedupe key for a later retry; the chop run ends
  `action_succeeded`/`action_failed` with its agents.

### 6.4 Implementation shape

`src/bugyi_chops/ci_watch.py`, entry point `bugyi_chop_ci_watch`, reusing `_common.run_chop`/`result_with_summary` so
exceptions fail closed into `check_error`. Keep pure decisions separate from adapters for testability:

- `ActstatClient` — runs `actstat -f jsonl -c <config>`, validates every record into typed observations (never trust
  exit codes alone; `repo_error` rows don't necessarily fail the process);
- `GitHubReader` — default branch/HEAD, workflow-run state, PR details, check rollups (narrow `gh` calls);
- `classify_repo(...)` — pure: `ERROR | PENDING | RED | GREEN`;
- `plan_release_merge(...)` — pure: eligibility §6.2 → immutable expected-head plan;
- `build_fix_proposal(...)` / `merge_release_pr(...)` — the only mutation-adjacent edges;
- `main` — SDK invocation, `merge_enabled`/dry-run checks, counters (`repos`, `green`, `pending`, `red`,
  `fix_proposed`, `release_candidates`, `merged`, `errors`), atomic result write.

argv lists only (no `shell=True`), validate all repo/branch/workflow strings, no tokens in vars/evidence/logs, bounded
diagnostics. **Environment gotcha (verified in `src/sase/axe/chop_env.py`):** chop `env` values resolve whole — a
literal string or a single `{env|file|pass}` reference — with no interpolation, so `PATH: "…:{env: PATH}"` would pass
literally and break every subprocess. Pass absolute binary paths (`~/.cargo/bin/actstat`, `gh`) through `vars` and fail
closed with an explicit reason if one is missing.

### 6.5 Config sketch (`sase_athena.yml` via chezmoi)

```yaml
axe:
  lumberjacks:
    ci_watch:
      description: |-
        Watch GitHub Actions health across SASE repos and drive fixes or releases

        Runs every five minutes; the single chop owns its own actstat config so unrelated orgs are never swept, and it
        is the only gate on release merges because no SASE repo has branch protection.
      interval: 300
      chop_timeout: "120s"
      chops:
        ci_watch:
          script: bugyi_chop_ci_watch
          timeout: "120s"
          env:
            ACTSTAT_CONFIG: /home/bryan/.config/sase/actstat-ci-watch.yml
          vars:
            actstat_bin: /home/bryan/.cargo/bin/actstat
            gh_bin: gh
            ci_workflow: CI
            repos: [sase-org/sase, sase-org/sase-core, sase-org/sase-github,
                    sase-org/sase-telegram, sase-org/sase-nvim]
            release_repositories:
              sase-org/sase: release-please
              sase-org/sase-core: release-plz
              sase-org/sase-github: release-please
              sase-org/sase-telegram: release-please
            merge_order: [sase-core, sase-github, sase-telegram, sase-nvim, sase]
            max_merges_per_tick: 1
            fix_enabled: true
            merge_enabled: false   # flip after the SASE dry-run change lands and the fix half has soaked
```

### 6.6 Rollout

1. **Register target repos as SASE projects deliberately.** A proposal with `workspace: gh:sase-org/sase-core`
   implicitly creates the project and clones a workspace on first launch; do it once by hand for the four non-`sase`
   repos so the first automated fix isn't also first-time setup. ⚠️ Newly enabled projects immediately join
   `for_each: source: projects` expansions in existing chops (e.g. `refresh_docs`) — accept that knowingly.
2. **Soak the fix half** with `merge_enabled: false`: `sase axe chop run ci_watch --dry-run -V`, then scheduled ticks
   for a few days. Verify the red predicate never fires on superseded `cancelled` runs.
3. **Land the SASE `ChopScriptContext` change** (`source` + `dry_run` + env mirrors, with tests proving they reach the
   subprocess and that proposal preview behavior is unchanged).
4. **Enable merging** with `max_merges_per_tick: 1`, one release repository first (`sase-core`); watch the merge
   trigger the release workflow and the next tick wait while it runs; then enable the rest.
5. **Notify on every action**: `sase notify create` (`-s ci_watch`, `-t release`) per merge and per fix launch, so
   releases are never silent; keep payloads bounded.
6. **Add branch protection anyway** — a minimal ruleset requiring `CI` turns the chop into a second gate instead of
   the only one.

### 6.7 Test plan (fake `actstat`/`gh` adapters in `bugyi-chops`)

All green / no PRs → no-op; current red → one pinned proposal, zero merge calls; several red repos → independent
proposals; old red + newer queued run → pending; settled SHA ≠ current HEAD → pending; superseded-only `cancelled` →
no proposal; `repo_error` / malformed JSONL / auth failure → fail closed; release-PR identity rules incl. near-match
false positives; draft/ambiguous/dirty/pending/red/empty-rollup/changed-head PR → no merge; eligible PRs merged in
`merge_order` respecting the per-tick cap; `--match-head-commit` mismatch → visible partial result, no same-tick
retry; `merge_enabled=false` and dry-run → full plan rendered, zero mutations; no token-like fields in evidence.

## 7. Open questions for Bryan

1. **Scope**: include `sase-google`/`sase-gchat` (CI but no release automation today)?
2. **Merge appetite**: fully unattended, or a `sase gate` confirmation for the first N merges given §2? One
   notification per release is cheap insurance while trust builds.
3. **Fix-agent model/effort**: default `@default`/`xhigh`, or something cheaper for first-pass CI triage?
4. **Red release PR**: should the chop ever act on a red *release PR* directly (as `sase` #243 was), or is red-master
   fixing sufficient? (Usually sufficient — the release PR rebuilds from master.)

## Sources

- `actstat_ci_release_chop__a.md` (codex researcher) and `actstat_ci_release_chop__b.md` (claude researcher), this
  directory — full detail, live captures, and per-file line references.
- Lead verification, 2026-07-27: `src/sase/axe/chop_script_context.py:28-42` (no `dry_run`/`source`),
  `src/sase/axe/chop_env.py` (whole-value env resolution), `docs/axe.md:513,540,558,608` (proposal/dedupe/dry-run
  contract), `strings ~/.cargo/bin/actstat` (`ACTSTAT_CONFIG`, token fallback chain), `gh api
  repos/sase-org/{sase,sase-core,sase-github,sase-telegram}/branches/master/protection` → 404 on all four.
- [actstat](https://github.com/bbugyi200/actstat) · [GitHub workflow-runs
  API](https://docs.github.com/en/rest/actions/workflow-runs) · [PR merge API
  (`--match-head-commit`)](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request) · [release-please
  action](https://github.com/googleapis/release-please-action) · [release-plz
  docs](https://release-plz.ieni.dev/docs).
