---
create_time: 2026-08-10
updated_time: 2026-08-10
status: research
---

# Emulating an Unprivileged GitHub Contributor Against `sase-org/sase`

**Research question:** what is the best way to stand up a GitHub identity that *cannot*
push to `sase-org/sase`, so that SASE's fork-and-contribute path — and the collaboration
features built on top of it — can be exercised end to end instead of remaining
theoretical?

**Scope:** the `sase` repo at master `0ccd7f844`, the `sase-github` plugin at
`4603b35` (`v0.2.3`), and the live state of `sase-org/sase` and the `bbugyi200` account
as read on 2026-08-10T22:09Z. Every claim marked **measured** below was produced by a
read-only command run against the real GitHub API or against a throwaway local git
directory; nothing was created, forked, or pushed.

## Bottom line

Use a **dedicated GitHub machine account that forks `sase-org/sase`**, and select its
identity **per-process through environment variables** rather than through `gh auth
switch` or a global SSH config. Everything SASE's GitHub provider does goes through
`gh` and `git` subprocesses that inherit `os.environ` verbatim, so `GH_CONFIG_DIR`,
`GIT_SSH_COMMAND`, and `GIT_AUTHOR_*` are sufficient and safe under parallel agents.

Three findings drive that conclusion, and two of them rule out the cheaper options
outright:

1. **A single account cannot emulate this, at any level of token scoping.** GitHub
   hard-blocks a PR author from approving their own PR — no branch protection setting,
   ruleset, or token scope overrides it. Any collaboration feature that touches review
   approval is untestable without a second identity. A scoped fine-grained PAT can
   simulate "push denied" but nothing else.
2. **The ToS explicitly permits exactly the account you need.** "You may maintain no
   more than one free machine account in addition to your free Personal Account." A
   machine account driven by SASE agents performing automated tasks is the intended
   use, not a workaround.
3. **SASE will create the PR against the wrong repository today.** *Measured:* with a
   fork as the only remote, `gh pr create` targets the **fork's own** default branch,
   not the parent. SASE's workspace clones are structurally origin-only, so a naive
   fork project produces fork→fork PRs silently. This is a real bug the harness will
   expose on day one, and it must be fixed (or worked around) before anything else can
   be tested.

There is also a fourth finding that reframes what the harness is *for*: SASE's GitHub
provider declares that it does not support reviewer comments at all
(`ws_supports_reviewer_comments` returns `False` for hosted GitHub URLs). The inbound
half of the collaboration loop is not merely untested — it is unimplemented. The
machine account is the prerequisite for building it, not just for validating it.

## 1. What "collaboration features" actually means in sase today

Before choosing an emulation strategy it is worth being precise about what the strategy
has to exercise, because the answer is narrower than the Patch model suggests.

The Patch model already has the vocabulary: `COMMENTS`, `MENTORS`, a `Mailed` status,
and a CRS ("comment resolution") workflow that spawns an agent to address review
feedback. But the two sides are wired very differently:

| Surface | Today | Needs an external identity? |
| --- | --- | --- |
| `MENTORS` | LLM reviewers run locally, emit a comments JSON (`workflows/mentor.py`) | No |
| `COMMENTS` → CRS | Consumes a comments file; reviewer key defaults to `critique` | Not to *run*, but yes to be *real* |
| PR submitted-check | `gh pr view --json state`, polled by the scheduler | Only to test the non-merge paths |
| Inbound PR review comments | **Not implemented for GitHub** | Yes |
| PR approval / changes-requested | Not modeled | Yes — and impossible with one account |

The decisive line is `sase-github/src/sase_github/workspace_plugin.py:224`:

```python
@hookimpl
def ws_supports_reviewer_comments(self, pr_url: str) -> bool | None:
    """GitHub does not support reviewer comments via critique_comments."""
    if _HOSTED_URL_RE.match(pr_url):
        return False
    return None
```

The `COMMENTS` → CRS machinery is generic and provider-neutral; the GitHub provider
simply declines to feed it. So the highest-value thing the harness unlocks is not
"verify feature X works" but "give feature X a real counterparty so it can be built."
That should shape the setup: the goal is a *durable second identity you can drive
repeatedly*, not a one-shot demo.

## 2. How SASE's GitHub integration authenticates — the levers that exist

This determines which emulation mechanisms are even possible, so it is worth stating
concretely. SASE has **no GitHub credential model of its own**. Every operation shells
out to `gh` or `git`, and the environment is built by copying the ambient one:

```python
# sase/src/sase/workspace_provider/utils.py:22
def non_interactive_git_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment that prevents git/SSH credential prompts."""
    env = dict(os.environ if base is None else base)
    env["GIT_TERMINAL_PROMPT"] = "0"
    ...
```

```python
# sase-github/src/sase_github/workspace_plugin.py:1856
def _non_interactive_gh_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = non_interactive_git_env(base)
    env["GH_PROMPT_DISABLED"] = "1"
    return env
```

`dict(os.environ)` is the whole story: **anything exported into the agent's environment
reaches every `gh` and `git` invocation SASE makes.** That is the lever, and it is a
good one — it is per-process, so it does not race with other SASE agents working on the
real repo in parallel.

All three identity levers were verified live:

```
$ GH_CONFIG_DIR=$(mktemp -d) gh auth status
You are not logged into any GitHub hosts. To log in, run: gh auth login   # isolated ✓

$ GH_TOKEN=ghp_invalid… gh api user
{ "message": "Bad credentials", … }                    # env token wins over hosts.yml ✓

$ ssh -o BatchMode=yes -T git@github.com
Hi bbugyi200! You've successfully authenticated…       # account resolved by SSH key ✓
```

The clone URL is built literally as `git@{host}:{user}/{project}.git`
(`workspace_plugin.py:1099`, SSH first with an HTTPS fallback), so an `~/.ssh/config`
`Host` alias will *not* be consulted. Key selection must go through `GIT_SSH_COMMAND`
with `-o IdentitiesOnly=yes`.

Relevant current state, all measured:

- `sase-org/sase` — `PUBLIC`, `defaultBranch: master`, `forkCount: 0`, `viewerPermission: ADMIN`.
- `sase-org` — organization on the **free** plan, 1 filled seat.
- `master` — **not protected**; `repos/sase-org/sase/rulesets` returns `[]`.
- `gh` 2.97.0; active account `bbugyi200`, classic PAT, git protocol `ssh`.
- `bbugyi200` already maintains ~20 forks, so forking workflows are familiar territory.

## 3. Hard constraints discovered

### 3.1 A PR author can never approve their own PR

This is a platform-level rule, not a configurable one. It is the single fact that
collapses the option space: any harness built on one account can test "push rejected"
and "PR opened", but can never reach `APPROVED`, `CHANGES_REQUESTED`, required-review
gating, or CODEOWNERS satisfaction. Since those are precisely the collaboration
features in question, **two distinct GitHub identities are mandatory.**

### 3.2 The ToS permits one machine account, and this is what it is for

> "One person or legal entity may maintain no more than one free Account (if you choose
> to control a machine account as well, that's fine, but it can only be used for
> running a machine)."
>
> "A machine account is an Account set up by an individual human who accepts the Terms
> on behalf of the Account… A machine account is used exclusively for performing
> automated tasks… **You may maintain no more than one free machine account in addition
> to your free Personal Account.**"

Two consequences worth internalizing. First, this is a sanctioned path, so there is no
need to be clever. Second, the allowance is *one* — so the account should be created
deliberately, named generically enough to serve future automation, and not burned on a
throwaway experiment.

Practical note: 2FA is mandatory for accounts that contribute code, so provisioning
requires a TOTP secret stored somewhere durable.

### 3.3 Push restriction is available on this repo, for free

GitHub's docs confirm "Restrict who can push to matching branches" is available on
"public repositories owned by a GitHub Free organization" — which is exactly
`sase-org/sase`. Since `master` is currently unprotected with no rulesets, the
maintainer half of the emulation is one configuration change away, and it costs
nothing. This matters more than it first appears: without it, the *maintainer* side of
the workflow is also unrealistic, because `bbugyi200` can bypass the PR flow entirely
and SASE will never observe a rejected push.

### 3.4 Fork PRs from a new contributor block CI until approved

Public repositories default to requiring approval for workflow runs on PRs from
first-time contributors — where "first-time" means no merged commit or PR. `ci.yml` and
`pr-title.yml` both trigger on `pull_request: branches: [master]`, so the machine
account's first PRs will sit in `action_required` until a maintainer clicks approve.

This is not an obstacle to route around; it is one of the most valuable behaviors in
the whole test matrix, because SASE's scheduler polls PR state and has no concept of
"CI is waiting on a human." Note that it self-resolves once the account has one merged
PR, so **capture the behavior early or lose the chance** on this repo.

## 4. The blocking integration gap: origin-only clones target the wrong base

This is the finding that changes the shape of the recommendation, and it was measured
directly rather than inferred.

**Setup A — fork as the only remote** (what SASE produces today):

```
$ git init -q . && git remote add origin git@github.com:bbugyi200/rich.git
$ gh pr create --dry-run --head master --title test --body test
head branch "master" is the same as base branch "master", cannot create a pull request
```

`gh` resolved the base repo to **`bbugyi200/rich`** — the fork itself. Confirmed
independently: `gh repo view --json nameWithOwner` returns `bbugyi200/rich`, and
`gh pr list` returns nothing (the fork has no PRs) rather than upstream's PR list.

**Setup B — with an `upstream` remote added:**

```
$ git remote add upstream git@github.com:Textualize/rich.git
$ gh pr create --dry-run --head master --title test --body test
Would have created a Pull Request with:
base:	main
head:	master
maintainerCanModify:	true
```

Base is now `Textualize/rich`'s default branch. `gh repo view` agrees
(`{"nameWithOwner":"Textualize/rich"}`) and `gh pr list` returns upstream PRs #4184,
#4182.

Now the structural part. SASE never creates that second remote:

- `_clone_gh_repo` (`workspace_plugin.py:1099`) runs a bare `git clone <url> <target>` —
  origin only.
- `ensure_git_clone_at` (`workspace_provider/utils.py:210`) materializes numbered
  workspaces by cloning the **primary workspace directory** and then running
  `git remote set-url origin <real_url>`. Additional remotes on the primary are *not*
  propagated, so even manually adding `upstream` to `sase_0` would not reach `sase_7`.

And both PR-creation paths rely on `gh`'s default base resolution:

```python
# sase-github/src/sase_github/plugin.py:387
def vcs_mail(self, revision: str, cwd: str):
    out = self._run(["git", "push", "-u", "origin", revision], cwd)
    ...
    pr_create = self._run(["gh", "pr", "create", "--fill"], cwd)
```

```python
# sase-github/src/sase_github/plugin.py:404 — vcs_create_pull_request
pr_out = self._run(["gh", "pr", "create", "--title", title, "--body", body], cwd)
```

**Conclusion:** without a fix, a fork-based SASE project opens PRs from the fork's
branch against the fork's own `master`. It will not error; it will quietly do the wrong
thing. This must be addressed first, and it is a genuine `sase-github` defect
independent of this research — worth its own task bead.

Two viable fixes, in preference order:

1. **Provider fix (correct).** Teach `_clone_gh_repo` / `ensure_git_clone_at` to add an
   `upstream` remote pointing at the parent when `gh repo view --json parent` reports
   one. `gh` prefers remotes named `upstream`, so this is all that is required. It fixes
   every workspace, present and future, and benefits any user contributing to a fork.
2. **Per-workspace workaround (immediate).** `gh repo set-default sase-org/sase` in each
   workspace, which writes `remote.origin.gh-resolved` into that clone's `.git/config`
   and persists across `sase repo open` cleanups. Adequate for a first manual run;
   fragile because each new numbered workspace needs it again.

## 5. Options considered

### A. Scoped fine-grained PAT on `bbugyi200` — rejected

Fork `sase-org/sase` → `bbugyi200/sase`, then drive SASE with a fine-grained PAT that
grants write only to the fork. Zero new accounts, zero ToS questions, ten minutes of
setup.

It genuinely does emulate "push to upstream is denied" — but the denial comes from the
*token*, not from GitHub's permission model, and that is where it stops. The account is
still `ADMIN` on upstream, so: no approval flow (§3.1), no first-time-contributor CI
gate (§3.4, which keys on the actor), no outsider-shaped API responses, and
`gh pr merge` would still succeed if a differently-scoped token were ever picked up.
Worth knowing as a five-minute smoke test of the fork *plumbing*; not a basis for
testing collaboration.

### B. Dedicated machine account + fork — **recommended**

Clears §3.1 and §3.4, is explicitly permitted by §3.2, and needs no new SASE
abstractions because the identity levers in §2 already work per-process. It is also the
only option that produces *durable* state: a second account you can keep driving as the
inbound-comment support in §1 gets built.

Costs: one account to provision and secure (2FA, SSH key, PAT), and the machine
account's namespace accumulates the fork plus auto-created sidecars (§6.1).

### C. GitHub App with an installation token — rejected as primary

Superficially attractive: granular per-repo permissions, no extra account, no ToS
question. In practice it fails on the tooling. Installation tokens authenticate as an
*installation*, not a user, so `gh` commands that resolve the current viewer degrade or
break; tokens expire after one hour, which is hostile to long agent runs; a GitHub App
cannot fork a repository on its own behalf; and PRs would be attributed to
`app-slug[bot]`, which changes the review semantics being tested. Keep it in mind if
SASE ever needs unattended CI-side automation — not for this.

### D. A second human personal account — rejected

Functionally identical to option B but violates the one-free-account rule in §3.2. The
machine-account carve-out exists precisely so this is unnecessary; there is no reason to
take the risk.

### E. Self-hosted forge (Gitea/Forgejo) or GitHub Enterprise Server — rejected

SASE's GitHub support *is* the `gh` CLI, top to bottom, and `gh` speaks the GitHub API.
Gitea and Forgejo expose their own API and would require an entire new provider plugin —
far more work than the thing being tested. GHES would work (`GH_HOST` and
`github_hosts:` are both plumbed through) but requires a license and a server. The one
place a local forge would win is offline/deterministic CI, which option F covers more
cheaply.

### F. A recorded `gh` shim — recommended as a **complement**, not a substitute

For regression tests, a fixture-backed fake `gh` earlier on `PATH` is cheaper, faster,
and hermetic; SASE's codebase is already friendly to it (`_gh_api_json` takes an
injectable `run_fn`). This does not emulate an unprivileged user — it emulates the
*responses* one would see. Use the live machine account to discover what those responses
actually look like, then freeze them as fixtures so CI covers the paths without network
or credentials. The two tracks are complementary and should both exist.

## 6. Consequences to plan for

### 6.1 The fork project will try to auto-create four sidecar repos

`sase/sase.yml` sets `is_sase_managed: true` and declares `plans`, `beads`, `agents`,
and `research` sidecars (`plans` and `beads` with `auto_clone: true`). A fork inherits
that file. `gh_setup.py` calls `materialize_sdd_store(workspace_dir, workspace_num)`
with no `sdd_creation_authorized` argument, and the docstring is explicit that "omitting
it authorizes creation for a managed repo."

So the first `#gh:<bot>/sase` launch will attempt to create `<bot>/sase--plans`,
`<bot>/sase--beads`, and friends on the machine account.

Let it. Sidecar provisioning as a non-owner is itself an untested path, the repos are
free, and suppressing it means carrying an `is_sase_managed: false` diff in the fork that
would contaminate every PR branch. Know that it happens so it does not look like a bug.

### 6.2 Project and workspace isolation is already clean

`#gh:<bot>/sase` resolves to project key `gh_<bot>__sase` with its own ProjectSpec,
registry, and workspace tree under `<owner>/<repo>/sase_<N>` — no collision with the
real `gh_sase-org__sase` project. The fork can live side by side with the real one
indefinitely.

### 6.3 `gh pr merge` will fail, and should

`workspace_plugin.py:1822` builds `["gh", "pr", "merge", "--merge", "--delete-branch"]`.
As the machine account this returns a 403. Whether SASE surfaces that as a clear,
actionable error or as an opaque failure is one of the more useful things this harness
will reveal.

## 7. Recommended solution

**Stand up a dedicated GitHub machine account that forks `sase-org/sase`, select its
identity per-process through environment variables, and fix the missing `upstream`
remote in `sase-github` before the first run.**

### Step 0 — Fix the base-repo gap first

File a task bead for `sase-github` to add an `upstream` remote for forked clones in
`_clone_gh_repo`, and to propagate it through `ensure_git_clone_at` so numbered
workspaces inherit it. Until that lands, run `gh repo set-default sase-org/sase` in each
fork workspace. **Do not skip this** — every PR created before it is fixed goes to the
wrong repository, silently (§4).

### Step 1 — Provision the machine account

Create it with a distinct email, enable TOTP 2FA, and store the recovery codes durably.
Name it for the long term (it is your only free machine account) — something like
`sase-bot` rather than a one-off experiment name. Do **not** add it to `sase-org`; being
an outsider is the entire point. Fork `sase-org/sase` from that account — no invitation
is needed since the repo is public.

### Step 2 — Create isolated credentials

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_sase_bot -C "sase-bot@github"
# add ~/.ssh/id_sase_bot.pub as an *authentication* key on the machine account

export GH_CONFIG_DIR="$HOME/.config/gh-sase-bot"
gh auth login --with-token < /path/to/bot-pat   # scopes: repo, read:org, workflow
```

Use a separate `GH_CONFIG_DIR` rather than `gh auth switch`: switching mutates global
state and would corrupt concurrent agents working on the real repo. Isolation was
verified in §2.

### Step 3 — Bind the identity to the fork project

The clean SASE-native mechanism already exists: workflow xprompts support an
`environment:` mapping that is injected at workflow start
(`xprompt/workflow_models.py:144`, `xprompt/workflow_executor.py:107`). Define a
`#ghbot` workflow that sets the identity and delegates to `#gh`:

```yaml
environment:
  GH_CONFIG_DIR: "{{ env.HOME }}/.config/gh-sase-bot"
  GIT_SSH_COMMAND: "ssh -i {{ env.HOME }}/.ssh/id_sase_bot -o IdentitiesOnly=yes"
  GIT_AUTHOR_NAME: "sase-bot"
  GIT_AUTHOR_EMAIL: "<id>+sase-bot@users.noreply.github.com"
  GIT_COMMITTER_NAME: "sase-bot"
  GIT_COMMITTER_EMAIL: "<id>+sase-bot@users.noreply.github.com"
```

Because `#gh` is `wraps_all: true`, wrapping it may need care; verify that the injected
environment actually reaches the spawned agent process before trusting it. A shell
wrapper exporting the same six variables around the launcher is the fallback and is
guaranteed to work given §2 — start there if the xprompt route fights back.

### Step 4 — Make the maintainer side real

Protect `master` on `sase-org/sase` with "Restrict who can push" plus "Require a pull
request before merging" (§3.3 — free on this repo). Without it, the maintainer half of
the workflow stays unrealistic and SASE never observes a rejected push.

### Step 5 — Work the test matrix, capturing the perishable cases first

| # | Scenario | Watch for | Perishable? |
| --- | --- | --- | --- |
| 1 | `sase commit` → push to fork | Push succeeds against fork origin | No |
| 2 | `#pr:` from fork | PR lands on **`sase-org/sase`**, not the fork | No |
| 3 | Push directly to upstream `master` | Rejection is legible, not a crash | No |
| 4 | First PR's CI | `action_required`; how the scheduler reports a human-blocked run | **Yes** — expires after first merge |
| 5 | Maintainer requests changes | Nothing ingests it yet (§1) — the gap to build | No |
| 6 | Maintainer approves | Reachable only with two accounts (§3.1) | No |
| 7 | `gh pr merge` as the bot | 403 surfaced clearly | No |
| 8 | Sidecar materialization on the fork | Four repos auto-created (§6.1) | Partly |

Run scenario 4 before merging anything from the machine account.

### Step 6 — Freeze what you learn into fixtures

Capture the `gh` JSON observed in each scenario — especially the outsider-shaped
responses in 3, 4, 6, and 7 — and land them as fixtures behind a fake `gh` (option F).
That converts a manual harness into permanent regression coverage and is what makes the
work durable after the exploratory phase ends.

## 8. Open questions

- Does `environment:` injection in a `wraps_all: true` workflow actually reach the
  spawned agent, or only the workflow executor? Untested here; determines whether Step 3
  uses the xprompt or the shell wrapper.
- Should `upstream`-aware cloning be conditional on detecting a fork, or should SASE
  model "this project contributes upstream to X" explicitly in the ProjectSpec? The
  latter is more work but would let `sase` reason about the two repos as a pair — which
  the inbound-comment feature will need anyway.
- Where should inbound GitHub review comments be normalized — a new `sase-github`
  `ws_generate_reviewer_comments_script` implementation, or in the Rust core given the
  backend-boundary rule? Comment ingestion looks like shared domain behavior any
  frontend would need, which argues for core.

## Sources

- [GitHub Terms of Service — Account Requirements](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)
- [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- [Approving workflow runs from public forks](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)
- [cli/cli discussion #5095 — using `gh` with a GitHub App](https://github.com/cli/cli/discussions/5095)
- [GitHub CLI manual — `gh auth login`](https://cli.github.com/manual/gh_auth_login)
