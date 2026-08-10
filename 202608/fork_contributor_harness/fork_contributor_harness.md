---
create_time: 2026-08-10
updated_time: 2026-08-10
status: research
---

# Emulating an Unprivileged External GitHub Contributor Against `sase-org/sase`

**Research question:** what is the best way to stand up a GitHub identity that *cannot*
push to `sase-org/sase`, so SASE's fork-and-contribute path — and the collaboration
features built on it — can be exercised end to end instead of remaining theoretical?

**Scope:** the `sase` repo at master `aae179e86`, the `sase-github` plugin, and the live
state of `sase-org/sase` and the `bbugyi200` account as read on 2026-08-10. Claims marked
**measured** were produced by read-only commands against the real GitHub API or against
throwaway local git directories. Nothing was created, forked, pushed, or reconfigured.

## Bottom line

Stand up a **dedicated GitHub machine account that forks `sase-org/sase`**, and select
its identity **per-process through environment variables**. Everything SASE's GitHub
provider does shells out to `gh`/`git` with `dict(os.environ)`, so `GH_CONFIG_DIR`,
`GIT_SSH_COMMAND`, `GIT_AUTHOR_*`, and `GH_REPO` are sufficient, and safe under parallel
agents because they are per-process rather than global mutable state.

Five findings drive the recommendation. Two rule out the cheaper options, one unblocks
the work sooner than either source report concluded, and two are corrections.

1. **A single account cannot emulate this at any level of token scoping.** GitHub
   hard-blocks a PR author from approving their own PR — no ruleset, branch protection
   setting, or token scope overrides it. A scoped PAT can simulate "push denied" and
   nothing else.
2. **The ToS explicitly permits exactly the account you need**: one free machine account
   in addition to your free Personal Account. This is the sanctioned path, not a
   workaround.
3. **SASE targets the wrong repo today — but a one-line env var fixes the entire PR
   lifecycle.** *Measured:* with a fork as the only remote, `gh` resolves the base repo
   to the **fork itself**, so a naive fork project opens silent fork→fork PRs.
   *Also measured (new):* `GH_REPO=sase-org/sase` corrects **every** affected command —
   creation, cross-fork lookup, and merge — with no code change and no per-workspace
   setup. You can start testing today; the provider fix is a follow-up, not a blocker.
4. **Correction: do NOT require pull requests on `master`.** Both source reports
   recommend it. *Measured:* the last four commits on `sase-org/sase` master have **no
   associated PR** — SASE's own `sase commit` pushes the current branch straight to
   `origin master`. Requiring PRs would break every one of Bryan's own agents. The bot
   is already fully denied by GitHub's permission model; the ruleset buys nothing it
   needs.
5. **Correction: the bot must use a classic PAT or OAuth, never a fine-grained PAT.**
   GitHub documents that fine-grained PATs cannot be used "to contribute to public repos
   where the user is not a member" — precisely the bot's situation. A fine-grained token
   would fail to open the upstream PR.

A sixth finding reframes what the harness is *for*: SASE's GitHub provider declares that
it does not support reviewer comments at all. The inbound half of the collaboration loop
is not merely untested — it is **unimplemented**. The machine account is a prerequisite
for building it, not just for validating it. That argues for provisioning it properly
rather than as a throwaway.

## 1. What "collaboration features" actually means today

The Patch model already has the vocabulary — `COMMENTS`, `MENTORS`, a `Mailed` status,
and a CRS ("comment resolution") workflow that spawns an agent to address review
feedback. But the two sides are wired very differently:

| Surface | Today | Needs an external identity? |
| --- | --- | --- |
| `MENTORS` | LLM reviewers run locally, emit a comments JSON (`workflows/mentor.py`) | No |
| `COMMENTS` → CRS | Consumes a comments file; reviewer key defaults to `critique` | Not to *run*, but yes to be *real* |
| PR submitted-check | `gh pr view --json state`, polled by the scheduler | Only for the non-merge paths |
| Inbound PR review comments | **Not implemented for GitHub** | Yes |
| PR approval / changes-requested | Not modeled | Yes — and impossible with one account |

The decisive line is `sase-github/src/sase_github/workspace_plugin.py:224` (**verified**):

```python
@hookimpl
def ws_supports_reviewer_comments(self, pr_url: str) -> bool | None:
    """GitHub does not support reviewer comments via critique_comments."""
    if _HOSTED_URL_RE.match(pr_url):
        return False
    return None
```

The `COMMENTS` → CRS machinery is generic and provider-neutral; the GitHub provider
simply declines to feed it. So the highest-value thing this harness unlocks is not
"verify feature X works" but "give feature X a real counterparty so it can be built."
The goal is a *durable second identity you can drive repeatedly*, not a one-shot demo.

## 2. The identity levers that exist

SASE has **no GitHub credential model of its own**. Every operation shells out to `gh` or
`git`, and the environment is built by copying the ambient one:

```python
# sase/src/sase/workspace_provider/utils.py:22
def non_interactive_git_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env["GIT_TERMINAL_PROMPT"] = "0"
```

`dict(os.environ)` is the whole story: **anything exported into the agent's environment
reaches every `gh` and `git` invocation SASE makes.** That is the lever, and it is a good
one — per-process, so it does not race with agents working on the real repo in parallel.

All three levers verified live:

```
$ GH_CONFIG_DIR=$(mktemp -d) gh auth status
You are not logged into any GitHub hosts.                # isolated ✓
$ GH_TOKEN=ghp_invalid… gh api user
{ "message": "Bad credentials", … }                      # env token beats hosts.yml ✓
$ ssh -o BatchMode=yes -T git@github.com
Hi bbugyi200! You've successfully authenticated…         # account resolved by SSH key ✓
```

The clone URL is built literally as `git@{host}:{user}/{project}.git`
(`workspace_plugin.py:1099`, SSH first with HTTPS fallback), so an `~/.ssh/config` `Host`
alias will **not** be consulted. Key selection must go through `GIT_SSH_COMMAND` with
`-o IdentitiesOnly=yes`.

`gh auth switch` is **not** a sufficient boundary: it changes `gh`'s active account but
does not force git's SSH connection to use the corresponding key, and it mutates global
state that concurrent agents share.

## 3. Verified current state (2026-08-10, read-only)

- `sase-org/sase` — `PUBLIC`, `defaultBranch: master`, `forkCount: 0`,
  `viewerPermission: ADMIN`. No `bbugyi200/sase` fork exists yet.
- `sase-org` — organization on the **free** plan, 1 filled seat.
- `master` — **not protected**; `repos/sase-org/sase/rulesets` returns `[]`.
- Fork PR workflow approval policy — `{"approval_policy": "first_time_contributors"}`.
- Actions — `default_workflow_permissions: read`,
  `can_approve_pull_request_reviews: false`.
- `gh` 2.97.0; active account `bbugyi200`, classic PAT, git protocol `ssh`.
- `bbugyi200` already maintains ~24 forks, so fork workflows are familiar territory.

## 4. Hard constraints

### 4.1 A PR author can never approve their own PR

Platform-level, not configurable. This single fact collapses the option space: any
harness built on one account can test "push rejected" and "PR opened", but can never
reach `APPROVED`, `CHANGES_REQUESTED`, required-review gating, or CODEOWNERS
satisfaction. **Two distinct GitHub identities are mandatory.**

### 4.2 The ToS permits one machine account, and this is what it is for

> "A machine account is an Account set up by an individual human who accepts the Terms on
> behalf of the Account… used exclusively for performing automated tasks… **You may
> maintain no more than one free machine account in addition to your free Personal
> Account.**"

Two consequences. This is sanctioned, so there is no need to be clever. And the allowance
is *one* — name it generically enough to serve future automation rather than burning it
on a throwaway experiment. 2FA is mandatory for accounts that contribute code, so
provisioning requires a TOTP secret stored durably.

### 4.3 The bot needs a classic PAT or OAuth token — not a fine-grained PAT

GitHub's documented fine-grained PAT limitations include "using fine-grained personal
access token to contribute to public repos where the user is not a member." That is
exactly the machine account's position relative to `sase-org/sase`, and contributing
includes opening the pull request. Authenticate the bot with `gh auth login --web`
(OAuth) or a **classic** PAT scoped `repo, read:org, workflow`. This also disposes of the
"scoped fine-grained PAT on `bbugyi200`" option in §6 on its own terms.

### 4.4 The fork-PR CI approval gate is real — and can be made permanent

Public repos default to requiring approval for workflow runs from first-time
contributors. `ci.yml` and `pr-title.yml` both trigger on
`pull_request: branches: [master]`, so the bot's first PRs sit in `action_required` until
a maintainer clicks approve. This is one of the most valuable behaviors in the matrix,
because SASE's scheduler polls PR state and has no concept of "CI is waiting on a human."

The default policy self-resolves once the account has one merged PR. Rather than racing
to capture it before it expires, **flip the setting to `all_external_contributors`** —
the API confirms `approval_policy` is a writable field on
`repos/sase-org/sase/actions/permissions/fork-pr-contributor-approval`. That makes the
gate permanent and the scenario repeatable.

## 5. The integration gap — and the env var that closes it

### 5.1 The defect

**Measured, setup A — fork as the only remote** (what SASE produces today):

```
$ git init -q . && git remote add origin git@github.com:bbugyi200/rich.git
$ gh pr create --dry-run --head master --title test --body test
head branch "master" is the same as base branch "master", cannot create a pull request
```

`gh` resolved the base repo to **`bbugyi200/rich`** — the fork itself. Confirmed
independently: `gh repo view --json nameWithOwner` returns the fork, and `gh pr list`
returns nothing rather than upstream's PR list.

**Setup B — with an `upstream` remote added:** base correctly resolves to
`Textualize/rich`'s default branch.

SASE never creates that second remote:

- `_clone_gh_repo` (`workspace_plugin.py:1099`) runs a bare `git clone <url> <target>` —
  origin only.
- `ensure_git_clone_at` (`workspace_provider/utils.py:210`) materializes numbered
  workspaces by cloning the **primary workspace directory** and then running
  `git remote set-url origin <real_url>`. Additional remotes and
  `remote.<name>.gh-resolved` config are *not* propagated — so even manually fixing
  `sase_0` would not reach `sase_7`. Independently reproduced by both researchers.

And both PR-creation paths rely on `gh`'s default base resolution
(`plugin.py:387` `vcs_mail` → `gh pr create --fill`; `plugin.py:404`
`vcs_create_pull_request` → `gh pr create --title … --body …`), as do
`vcs_get_pr_number`, `vcs_get_change_url`, `vcs_abandon_change`, and `gh pr merge`.

**Without a fix, a fork-based SASE project opens PRs from the fork's branch against the
fork's own `master`. It will not error; it will quietly do the wrong thing.**

### 5.2 `GH_REPO` closes it — measured across the whole lifecycle

The two source reports diverged here: one proposed `GH_REPO`, hedged that head inference
might still be ambiguous, and offered a manual `gh pr create --repo … --head …` fallback;
the other did not consider `GH_REPO` and recommended per-workspace
`gh repo set-default`. Direct measurement settles it in favor of `GH_REPO`, and more
strongly than either report claimed:

| Command | origin=fork, no `GH_REPO` | origin=fork, `GH_REPO=<upstream>` |
| --- | --- | --- |
| `gh pr create` base | the **fork** (`origin/master…`) | **upstream** (`main…`) ✓ |
| `gh pr create` head | n/a | **`bbugyi200:fix-detect-color`** ✓ |
| `gh pr view --json number` | `no pull requests found for branch` ✗ | **`4184  …/Textualize/rich/pull/4184`** ✓ |

The cross-fork lookup test used a real fork-originated PR (`KRRT7:migrate-to-uv` →
`Textualize/rich#4184`) with the fork as the only remote. `GH_REPO` found it; the bare
invocation did not. That covers `vcs_mail`'s `pr_check`, `vcs_get_pr_number`,
`vcs_get_change_url`, and the scheduler's submitted-check — i.e. the entire PR lifecycle,
via **one env var in the launcher wrapper**, applied automatically to every numbered
workspace present and future.

This is materially better than `gh repo set-default`, which writes
`remote.origin.gh-resolved` into one clone's `.git/config` and must be redone for every
new numbered workspace.

**Blast radius is bounded.** The provisioning calls all pass explicit repo coordinates,
so `GH_REPO` cannot confuse them: `gh repo view <full_name>` (`workspace_plugin.py:784`),
`gh repo create <full_name>` (`:868`), `gh label create --repo <full_name>` (`:958`), and
`gh repo list <namespace>` (`:1212`). An explicit argument wins over the env var.

**Two rough edges to watch, not blockers:**

- `gh pr create --fill` computes the title/body from `<upstream-default>…<branch>`, which
  must resolve locally. Since both `sase` and its fork use `master`, this resolves to the
  fork clone's local `master` — it works, but keep the fork synced (`gh repo sync`) so
  the computed range is meaningful.
- `vcs_abandon_change` runs `gh pr close <cl> --delete-branch`. With `GH_REPO` pointing
  upstream, the branch deletion targets a repo the bot cannot write. Expect a partial
  failure; it is a test case, not a defect in the workaround.

### 5.3 The durable provider fix

`GH_REPO` unblocks testing today, but `sase-github` should still be fixed. In preference
order:

1. **Add an `upstream` remote for forked clones** in `_clone_gh_repo` when
   `gh repo view --json parent` reports a parent, and propagate it through
   `ensure_git_clone_at`. `gh` prefers remotes named `upstream`, so this alone corrects
   base resolution for every workspace and benefits any user contributing to a fork.
2. **Pass explicit coordinates** — `--repo`, `--base`, `--head <owner>:<branch>` — on
   every PR lifecycle command. Less brittle than relying on `gh`'s remote inference, and
   it makes the fork relationship legible in the code rather than implicit in git config.

Modeling "this project contributes upstream to X" in the ProjectSpec is the more
ambitious version, and the inbound-comment feature will need that pairing anyway.

## 6. Options considered

| Option | Verdict | Why |
| --- | --- | --- |
| **Machine account + fork** | **Recommended** | Clears §4.1 and §4.4, permitted by §4.2, needs no new SASE abstractions. The only option producing *durable* state you can keep driving as inbound-comment support gets built. Cost: one account to provision and secure. |
| Scoped fine-grained PAT on `bbugyi200` | Rejected | Denial comes from the *token*, not GitHub's permission model. No approval flow, no first-time-contributor gate (it keys on the actor), no outsider-shaped API responses. And §4.3 means it cannot even open the upstream PR. |
| `bbugyi200` + branch ruleset alone | Rejected | No external identity, no fork, no Actions trust boundary — and see §7, it breaks the existing workflow. |
| GitHub App + installation token | Rejected as primary | Installation tokens authenticate as an *installation*, not a user, so `gh` commands resolving the current viewer degrade; tokens expire hourly, hostile to long agent runs; an App cannot fork on its own behalf; PRs attribute to `app-slug[bot]`, changing the review semantics under test. Revisit for unattended CI-side automation. |
| Second human personal account | Rejected | Functionally identical to the machine account but violates the one-free-account rule. The carve-out exists precisely so this is unnecessary. |
| Self-hosted forge (Gitea/Forgejo) | Rejected | SASE's GitHub support *is* the `gh` CLI, top to bottom. A new forge needs an entire new provider plugin — more work than the thing being tested. GHES would work (`GH_HOST` is plumbed) but needs a license and a server. |
| Recorded `gh` shim / fixtures | **Recommended complement** | A fixture-backed fake `gh` earlier on `PATH` is cheaper, faster, and hermetic; `_gh_api_json` already takes an injectable `run_fn`. It emulates the *responses*, not the identity — so use the live bot to discover what outsider-shaped responses look like, then freeze them. Both tracks should exist. |

## 7. Correction: do not require pull requests on `master`

Both source reports recommend protecting `sase-org/sase`'s `master` with "Require a pull
request before merging" — one as "defense in depth", the other to make the maintainer
side realistic. **This would break SASE's own commit workflow.**

*Measured:* `repos/sase-org/sase/commits/<sha>/pulls` returns empty for `aae179e86`,
`0ccd7f844`, `6f4a032cd`, and `83e3d3c27` — the four most recent master commits arrived
by direct push. The mechanism is `_push_with_retry`
(`vcs_provider/plugins/_git_commit_dispatch.py:191`), which pushes
`origin <current-branch>`; agents work on `master` directly. Master's history is mixed —
there are `Merge pull request #…` commits from release-please and some agent branches —
but the dominant recent pattern is direct-to-master, and requiring PRs would break it.

The important point: **the ruleset is not load-bearing for this harness.** A
non-collaborator on a public repo cannot push to *any* branch — GitHub's permission model
already denies the bot completely, with no configuration at all. A ruleset would only
constrain `bbugyi200`, and constraining `bbugyi200` is what breaks things.

If you still want defense-in-depth against your own credentials, use a ruleset that
**restricts who can push** (actor-based) with `bbugyi200` / the Repository admin role on
the bypass list — and accept that a bypass list makes it advisory for the only account
capable of violating it. The honest recommendation is to skip it, and revisit only if you
later migrate SASE's own workflow onto branches.

## 8. Consequences to plan for

### 8.1 The fork will auto-create four sidecar repos — let it

`sase/sase.yml` sets `is_sase_managed: true` and declares `plans`, `beads`, `agents`, and
`research` sidecars. A fork inherits that file, and `gh_setup.py` calls
`materialize_sdd_store` with no `sdd_creation_authorized` argument — the docstring is
explicit that "omitting it authorizes creation for a managed repo." So the first
`#gh:<bot>/sase` launch attempts to create `<bot>/sase--plans`, `<bot>/sase--beads`, and
friends.

Let it happen. Sidecar provisioning as a non-owner is itself an untested path, the repos
are free, and suppressing it means carrying an `is_sase_managed: false` diff in the fork
that would contaminate every PR branch.

**On the sidecar disagreement.** One source report proposes the opposite — pin the
sidecars to `sase-org/*` and grant the bot write access to `sase--agents` — to exercise
cross-owner agent-hood convergence. Both are right about different experiments, and the
order matters:

- **Baseline (do this first):** bot owns its own sidecars. This is the true-outsider
  topology, needs no grants, and is what a real external contributor would experience.
- **Cross-owner experiment (later, deliberately):** grant the bot `write` on
  `sase-org/sase--agents` *only*, and pin that one sidecar. This intentionally breaks the
  outsider model in exchange for testing two-owner hood publication and import. Expand to
  `--plans`/`--beads`/`--research` one at a time, only when a test needs shared writes.

Where that report is unambiguously right: pin the override in the **bot's SASE config
overlay**, never in the fork's `sase.yml`, so no diff contaminates PR branches. Also keep
a zero-grant negative test — SASE should fail *cleanly* when it cannot publish shared
collaboration metadata.

### 8.2 Project and workspace isolation is already clean — extra isolation is optional

`#gh:<bot>/sase` resolves to project key `gh_<bot>__sase` with its own ProjectSpec,
registry, and workspace tree under `<owner>/<repo>/sase_<N>` — no collision with
`gh_sase-org__sase`. The fork can live beside the real project indefinitely.

So a separate `SASE_HOME` is **not required**. Both env vars do exist if you later want a
harder wall (`SASE_HOME` → `core/paths.py:108`, defaulting to `~/.sase`;
`SASE_WORKSPACE_ROOT` → `workspace_provider/store.py:25`). One caveat is verified and
worth knowing: **`SASE_HOME` does not relocate the config directory** —
`config/core.py:60` hardcodes `CONFIG_DIR = Path("~/.config/sase")`. Full isolation
therefore needs a machine overlay under `~/.config/sase`, or a separate OS account or
container.

Recommendation: start **without** `SASE_HOME` isolation. Keeping beads, notifications,
and agent state in one place is what you want while developing, and `GH_CONFIG_DIR` plus
`GIT_SSH_COMMAND` already prevent credential bleed.

### 8.3 `gh pr merge` will fail, and should

`workspace_plugin.py:1822` builds `["gh", "pr", "merge", "--merge", "--delete-branch"]`.
As the machine account this returns 403. Whether SASE surfaces that as a clear,
actionable error or an opaque failure is one of the more useful things this harness
reveals.

### 8.4 Keep the fork's `master` synced

A fork's default branch goes stale, and SASE rebases against `origin/master` — which is
now the *fork's* master. Run `gh repo sync` before each test run, and never develop on
the fork's default branch.

## 9. Recommended solution

**Stand up a dedicated GitHub machine account that forks `sase-org/sase`, select its
identity per-process through environment variables, and set `GH_REPO=sase-org/sase` so
every PR command targets upstream from day one.**

### Step 1 — Provision the machine account

Create it with a distinct email, enable TOTP 2FA, store recovery codes durably. Name it
for the long term — it is your only free machine account — something like `sase-bot`
rather than a one-off experiment name. Do **not** add it to `sase-org`; being an outsider
is the entire point. Fork `sase-org/sase` from that account; no invitation is needed
since the repo is public.

### Step 2 — Create isolated credentials

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_sase_bot -C "sase-bot@github"
# add ~/.ssh/id_sase_bot.pub as an *authentication* key on the machine account

export GH_CONFIG_DIR="$HOME/.config/gh-sase-bot"
gh auth login --hostname github.com --git-protocol ssh --web --skip-ssh-key
# or: gh auth login --with-token < bot-classic-pat   (scopes: repo, read:org, workflow)
```

Use a **classic** PAT or the OAuth `--web` flow — not a fine-grained PAT (§4.3). Use a
separate `GH_CONFIG_DIR` rather than `gh auth switch`, which mutates global state shared
with concurrent agents.

### Step 3 — Bind the identity with a launcher wrapper

```bash
#!/usr/bin/env bash
exec env \
  GH_CONFIG_DIR="$HOME/.config/gh-sase-bot" \
  GH_REPO=sase-org/sase \
  GIT_SSH_COMMAND="ssh -F /dev/null -i $HOME/.ssh/id_sase_bot -o IdentitiesOnly=yes" \
  GIT_AUTHOR_NAME="sase-bot" \
  GIT_AUTHOR_EMAIL="<id>+sase-bot@users.noreply.github.com" \
  GIT_COMMITTER_NAME="sase-bot" \
  GIT_COMMITTER_EMAIL="<id>+sase-bot@users.noreply.github.com" \
  sase "$@"
```

`GH_REPO` is what makes the fork workflow correct without a code change (§5.2). Start
with the wrapper: it is guaranteed to work given §2. The SASE-native alternative is a
workflow xprompt `environment:` mapping (`xprompt/workflow_models.py:144`,
`xprompt/workflow_executor.py:107`) defining a `#ghbot` that delegates to `#gh` — but
`#gh` is `wraps_all: true`, so verify the injected environment actually reaches the
spawned agent process before trusting it.

Then resolve and work on `#gh:sase-bot/sase`, never `#gh:sase-org/sase`, so every push
goes to the fork.

### Step 4 — Make the CI gate permanent instead of racing it

Set `repos/sase-org/sase/actions/permissions/fork-pr-contributor-approval` to
`all_external_contributors` (§4.4). This converts the most interesting scheduler scenario
from a one-shot, perishable observation into a repeatable one.

Do **not** add a "require a pull request" ruleset on `master` (§7).

### Step 5 — Work the test matrix

| # | Scenario | Watch for |
| --- | --- | --- |
| 1 | `gh api user` + `ssh -T git@github.com` under the wrapper | Both report the bot, not `bbugyi200` |
| 2 | `sase commit` → push to fork | Succeeds against fork origin; every workspace's origin is the fork |
| 3 | Direct push to upstream `master` under the wrapper | Rejected by GitHub; rejection is legible, not a crash |
| 4 | `#pr:` from the fork | PR URL is under `sase-org/sase`, head label is `sase-bot:<branch>` |
| 5 | First PR's CI | `action_required`; how the scheduler reports a human-blocked run |
| 6 | `vcs_get_pr_number` / submitted-check on that PR | Finds the cross-fork PR (should, per §5.2) |
| 7 | Maintainer requests changes | Nothing ingests it yet (§1) — this is the gap to build |
| 8 | Maintainer approves | Reachable only with two accounts (§4.1) |
| 9 | `gh pr merge` as the bot | 403 surfaced clearly |
| 10 | `sase` abandons the Patch | `gh pr close --delete-branch` against upstream (§5.2 rough edge) |
| 11 | Sidecar materialization on the fork | Four repos auto-created (§8.1) |
| 12 | Zero-grant sidecar publication | Fails cleanly, without affecting the pushed branch or PR |

### Step 6 — Freeze what you learn into fixtures

Capture the `gh` JSON observed in scenarios 3, 5, 8, and 9 especially, and land them
behind a fake `gh` on `PATH`. That converts a manual harness into permanent regression
coverage and is what makes the work durable after the exploratory phase ends.

### Step 7 — Land the provider fix

File the `upstream`-remote defect against `sase-github` (§5.3). `GH_REPO` makes it
non-blocking, but the defect is real for any user contributing from a fork, independent
of this research.

## 10. Open questions

- Does `environment:` injection in a `wraps_all: true` workflow reach the spawned agent,
  or only the workflow executor? Determines whether Step 3 can move from the shell
  wrapper to a `#ghbot` xprompt.
- Should upstream-aware cloning be conditional on detecting a fork, or should SASE model
  "this project contributes upstream to X" explicitly in the ProjectSpec? The latter is
  more work but lets `sase` reason about the two repos as a pair — which the
  inbound-comment feature needs anyway.
- Where should inbound GitHub review comments be normalized — a new `sase-github`
  `ws_generate_reviewer_comments_script`, or the Rust core? Comment ingestion looks like
  shared domain behavior any frontend would need, which argues for core under the
  backend-boundary rule.
- Does `GH_REPO` interact badly with `gh repo sync` or issue operations on the fork? Both
  now resolve to upstream; `gh issue create` landing on upstream is arguably correct for
  an external contributor, but confirm before relying on it.

## Sources

- [GitHub Terms of Service — Account Requirements](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- [Managing your personal access tokens — fine-grained PAT limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [About permissions and visibility of forks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-permissions-and-visibility-of-forks)
- [Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)
- [Approving workflow runs from public forks](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)
- [Events that trigger workflows — workflows in forked repositories](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories)
- [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Machine users](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#machine-users)
- [GitHub CLI — `gh` environment variables](https://cli.github.com/manual/gh_help_environment)
- [GitHub CLI — `gh pr create`](https://cli.github.com/manual/gh_pr_create)
- [cli/cli discussion #5095 — using `gh` with a GitHub App](https://github.com/cli/cli/discussions/5095)

---

*Consolidated from two independent research passes (`fork_contributor_harness__a.md`,
`fork_contributor_harness__b.md`) plus lead-researcher verification. New in this
consolidation: the measured `GH_REPO` lifecycle results (§5.2), the master-protection
correction (§7), the fine-grained PAT constraint (§4.3), the writable CI approval policy
(§4.4), the `GH_REPO` blast-radius bound (§5.2), and the sidecar/isolation conflict
resolutions (§8.1, §8.2).*
