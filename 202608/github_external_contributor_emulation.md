# Emulating an unprivileged external GitHub contributor for SASE

Date: 2026-08-10

## Goal

Create a repeatable identity that can run SASE, own a fork of `sase-org/sase`, push
branches to that fork, and open pull requests against the upstream repository, but
cannot push to upstream `master` or silently act with Bryan's maintainer privileges.
Ideally, the same setup should also exercise SASE's cross-owner agent and sidecar
collaboration paths.

## Executive answer

The best fit is a manually created GitHub **machine account** used exclusively by SASE
automation. It should own a public fork, have no membership or collaborator role on the
upstream code repository, and use isolated `gh`, SSH, Git, and SASE state. GitHub's
current terms explicitly permit one free machine account in addition to a free personal
account, provided it is created by a human and used exclusively for automated tasks.
GitHub also documents machine users as accounts to which a dedicated SSH key can be
attached. [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service),
[machine-user documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#machine-users)

For collaboration testing, grant that account write access only to the SASE sidecar
repositories that are meant to be shared, starting with `sase-org/sase--agents`. It
remains a true external contributor to the code repository while gaining the minimum
coordination-plane permission needed to publish a second SASE owner's agent hoods.

There is one product limitation to address or work around: SASE currently preserves
only `origin` in numbered workspaces and invokes `gh pr create` without identifying the
upstream base repository or fork head. Fork-aware pull-request targeting is therefore
not yet a reliable first-class SASE path.

## What a useful emulation must preserve

| Property | Why it matters |
| --- | --- |
| A distinct GitHub principal | GitHub must enforce the denial; a convention or local token wrapper is not enough. |
| Fork-owned writable `origin` | SASE currently pushes branches with `git push -u origin`. |
| Upstream-targeted `gh` operations | PR lookup, creation, closing, and submission use context-sensitive `gh pr` commands. |
| A distinct SASE owner identity | Cross-owner agent-sidecar import depends on `<username>.<machine_name>` ownership, not just Git commit authorship. |
| Isolated credentials and state | A missed environment switch must not fall back to Bryan's admin token or SSH key. |

## Current repository and account state

Read-only checks on 2026-08-10 found:

- `sase-org/sase` is public, forkable, and uses `master` as its default branch.
- The active `gh` account is `bbugyi200`, with `ADMIN` repository permission.
- The repository currently has no repository ruleset and no branch protection on
  `master`.
- Fork PR workflow approval is set to `first_time_contributors`.
- There is no existing `bbugyi200/sase` fork.

This means the present login cannot serve as an unprivileged test identity, and a typo
or missed profile switch can still write directly to upstream. A branch ruleset should
be added as defense in depth even after a separate contributor identity exists. GitHub
supports requiring pull requests and applying branch protection to administrators as
well. [Protected-branch behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[ruleset rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

## GitHub behavior relevant to the design

### A machine account is the supported second free identity for automation

GitHub permits one free personal account plus one free machine account. The machine
account must be created manually and used exclusively for automation. That is a good
match for an account whose pushes, issues, and PRs are produced by SASE agents; ordinary
human review and merge actions should continue to use Bryan's personal account.

A second free personal account used interactively would conflict with the current
one-free-account rule. A second paid personal account or another real human collaborator
would also create a true principal, but neither is as cheap or repeatable for automated
testing.

### A public fork has the desired permission boundary

Public forks do not inherit the upstream repository's permissions. A machine account
that is not a member of `sase-org` and is not a collaborator on `sase-org/sase` can
write its own fork but cannot write the upstream repository. Maintainers may optionally
be allowed to edit a branch in a user-owned fork. [Fork permission and visibility](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-permissions-and-visibility-of-forks)

GitHub CLI's normal fork topology is:

```text
origin    -> contributor/sase
upstream  -> sase-org/sase
```

`gh repo fork` makes the fork `origin` and renames the old origin to `upstream`; `gh
repo clone` recognizes a fork, adds its parent as `upstream`, and makes the parent the
default repository for GitHub API operations. [gh repo fork](https://cli.github.com/manual/gh_repo_fork),
[gh repo clone](https://cli.github.com/manual/gh_repo_clone)

`gh repo set-default` explicitly controls the repository used to view and create pull
requests, issues, releases, and Actions operations. [gh repo set-default](https://cli.github.com/manual/gh_repo_set-default)

### Fork PRs exercise a meaningfully different CI trust boundary

For a fork-originated PR, Actions secrets are not passed to the workflow and the
`GITHUB_TOKEN` is read-only. A first-time contributor may also require a maintainer to
approve the workflow run. These are collaboration behaviors that same-repository
feature branches do not reproduce. [Events triggered by fork PRs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories),
[approving workflow runs from forks](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)

The current `first_time_contributors` policy is suitable for an initial smoke test.
Changing it to `all external contributors` would keep this approval path repeatable
after the machine account's first PR is merged.

## SASE-specific findings

### The push side already matches a fork workflow

`sase-github` pushes a Patch branch with:

```text
git push -u origin <revision>
```

That is exactly right when `origin` is the contributor's fork. It is wrong when the
primary checkout still points at `sase-org/sase`, so the fork must be the ProjectSpec's
primary repository. See
[`GitHubPlugin.vcs_mail`](https://github.com/sase-org/sase-github/blob/master/src/sase_github/plugin.py#L386-L398).

### PR targeting is not fork-aware yet

After pushing, the provider runs context-sensitive commands with no explicit repository
coordinates:

```text
gh pr view --json number -q .number
gh pr create --fill
```

The direct PR creation path likewise omits `--repo`, `--base`, and `--head`. See
[`GitHubPlugin`](https://github.com/sase-org/sase-github/blob/master/src/sase_github/plugin.py#L357-L420).
GitHub CLI supports the reliable cross-fork form
`--repo sase-org/sase --base master --head <contributor>:<branch>`, but SASE does not
currently pass those values. [gh pr create](https://cli.github.com/manual/gh_pr_create)

As an interim single-project workaround, launch SASE with:

```text
GH_REPO=sase-org/sase
```

GitHub CLI documents `GH_REPO` as the repository selector for commands that would
otherwise infer a local repository. [gh environment](https://cli.github.com/manual/gh_help_environment)
This should make SASE's context-free PR and issue commands target upstream while Git
continues to push to the fork's `origin`. The resulting PR URL must be checked during
the first smoke test. If inference of the head fork is still ambiguous, create the PR
explicitly after SASE pushes:

```bash
gh pr create \
  --repo sase-org/sase \
  --base master \
  --head <machine-user>:<patch-branch> \
  --fill
```

### Numbered workspaces lose the fork's upstream metadata

The GitHub workspace provider uses raw `git clone`, not `gh repo clone`, when resolving
`#gh:<owner>/<repo>`. See
[`_clone_gh_repo`](https://github.com/sase-org/sase-github/blob/master/src/sase_github/workspace_plugin.py#L1099-L1132).

SASE then creates a numbered workspace by cloning the primary checkout, reads only the
primary's `origin`, resets the numbered clone's `origin` to that URL, and fetches it.
It does not copy additional remotes or `remote.<name>.gh-resolved` configuration. See
[`ensure_git_clone_at`](https://github.com/sase-org/sase/blob/master/src/sase/workspace_provider/utils.py#L210-L334).

A local reproduction added an `upstream` remote and
`remote.upstream.gh-resolved=base` to a temporary primary clone, materialized a numbered
workspace through `ensure_git_clone_at`, and observed that the numbered workspace
contained only `origin` and no `gh-resolved` entry. This is why configuring the primary
checkout once with `gh repo set-default upstream` is insufficient.

The durable fix should make `sase-github` detect a fork's parent, carry fork/base
coordinates in workspace metadata, and use explicit `--repo`, `--base`, and `--head`
arguments for every PR lifecycle command. Preserving an `upstream` remote in every
numbered workspace is useful for humans, but explicit provider coordinates are less
brittle than relying on GitHub CLI's local remote inference.

### A fork naturally derives separate sidecars

SASE derives `--plans`, `--beads`, `--agents`, and `--research` repositories from the
primary repository owner. If the primary is `<machine-user>/sase`, the default sidecars
belong to the machine user. This is isolated and safe, but it does not test the
cross-owner convergence described by SASE's shared agents-sidecar design.

To test that design while keeping the code boundary intact, pin only the collaboration
sidecars to the upstream organization in the external SASE profile:

```yaml
repos:
  sidecar:
    builtin:
      agents:
        repo: sase-org/sase--agents
      plans:
        repo: sase-org/sase--plans
      beads:
        repo: sase-org/sase--beads
    custom:
      research:
        repo: sase-org/sase--research
```

Then grant the machine account `write` only to the sidecars actually being exercised.
Start with `sase--agents`; add plans, beads, and research later if those workflows need
shared mutation. GitHub explicitly supports adding a machine user as an outside
collaborator with a selected role. The account still has no write permission to
`sase-org/sase`. [Machine-user access options](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#machine-users)

A zero-access test should also be retained: with no sidecar grants, SASE ought to fail
cleanly when it cannot publish shared collaboration metadata. That negative path is
different from the shared-sidecar collaboration test.

## Options considered

| Option | Fidelity | Assessment |
| --- | --- | --- |
| Machine account + personal fork | High | Best repeatable external principal; expressly supported for automation. |
| Bryan's account + branch ruleset | Low to medium | Good protection against direct `master` pushes, but no external identity, fork, or Actions trust boundary. |
| Bryan's account + restricted token/deploy key | Low | Git and `gh` use different credentials, the underlying actor is still an admin, and a missed switch restores privilege. Fine-grained PATs also currently cannot contribute to public repositories where the user is not a member. [PAT limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens-limitations) |
| GitHub App | Medium for authorization, low for contributor realism | Strong least privilege, but it acts as an app, uses short-lived installation credentials, and does not reproduce a normal external user's fork/PR experience. It also does not match SASE's current `gh` + SSH assumptions. [GitHub App permissions](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app) |
| GitHub Enterprise Server sandbox | High | Expensive and operationally heavy; useful only if GitHub.com cannot host destructive integration tests. |
| Another real human contributor | Highest social fidelity | Excellent final validation, but not deterministic or self-service enough for routine development. |

## Suggested isolated profile

Use a conspicuous account name such as `sase-contrib-bot`, document its owner and
automation-only purpose in the profile, enable 2FA, and do not add it to `sase-org`.
Create a dedicated SSH key and authenticate a dedicated GitHub CLI configuration:

```bash
ssh-keygen -t ed25519 \
  -f /home/bryan/.ssh/id_ed25519_sase_contrib \
  -C sase-contrib-bot

GH_CONFIG_DIR=/home/bryan/.config/gh-sase-contrib \
  gh auth login --hostname github.com --git-protocol ssh --web --skip-ssh-key

GH_CONFIG_DIR=/home/bryan/.config/gh-sase-contrib \
  gh ssh-key add /home/bryan/.ssh/id_ed25519_sase_contrib.pub \
  --title "athena SASE external contributor"
```

GitHub CLI supports both multiple accounts and a separate `GH_CONFIG_DIR`; GitHub also
documents `GIT_SSH_COMMAND` with `IdentitiesOnly=yes` for choosing a key per account.
[GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login),
[multiple-account SSH setup](https://docs.github.com/en/account-and-profile/how-tos/account-management/managing-multiple-accounts#contributing-to-multiple-accounts-using-ssh-and-git_ssh_command)

Create the fork using only that profile:

```bash
GH_CONFIG_DIR=/home/bryan/.config/gh-sase-contrib \
  gh repo fork sase-org/sase --clone=false
```

Run the external SASE instance through a saved wrapper script that sets all relevant
boundaries:

```bash
#!/usr/bin/env bash
exec env \
  SASE_HOME=/home/bryan/.sase-contrib \
  SASE_WORKSPACE_ROOT=/home/bryan/.local/state/sase-contrib/workspaces \
  GH_CONFIG_DIR=/home/bryan/.config/gh-sase-contrib \
  GH_REPO=sase-org/sase \
  GIT_CONFIG_GLOBAL=/home/bryan/.config/git/sase-contrib.gitconfig \
  GIT_SSH_COMMAND='ssh -F /dev/null -i /home/bryan/.ssh/id_ed25519_sase_contrib -o IdentitiesOnly=yes' \
  sase "$@"
```

The dedicated Git config should contain only the machine account's author name and a
verified or GitHub-provided no-reply email. The separate `SASE_HOME` provides independent
projects, artifacts, and the machine selector; the separate workspace root prevents
claim/checkout collisions. SASE's configuration directory remains
`~/.config/sase`, so use `SASE_HOME=/home/bryan/.sase-contrib sase config init` to
create and select a second machine overlay there with an owner such as:

```yaml
id:
  username: sase-contrib-bot
  machine_name: athena_contrib
```

The isolated state root's `machine_name` selector ensures that only this overlay
contributes identity and machine-specific settings to the external process. If sharing
the configuration directory at all is too risky, use a dedicated local OS account or
container instead; changing `SASE_HOME` does not relocate `~/.config/sase`.

Resolve and work on `#gh:sase-contrib-bot/sase`, not `#gh:sase-org/sase`, so every SASE
push goes to the fork. Keep the fork's `master` synchronized from its parent before a
test run with `gh repo sync`; do not develop on the fork's default branch.

`gh auth switch` alone is not a sufficient boundary. It changes GitHub CLI's active
account but does not force Git's SSH connection to use the corresponding key. The
dedicated config directory plus `GIT_SSH_COMMAND` makes both identities explicit.

## Acceptance test matrix

Run these checks before trusting the profile:

1. `gh api user --jq .login` under the wrapper reports the machine account.
2. `ssh -T git@github.com` with the wrapper's SSH command reports the machine account.
3. The primary and every numbered workspace have
   `origin = git@github.com:<machine-user>/sase.git`.
4. A dry-run push to `sase-org/sase` is rejected by GitHub, while a feature-branch push
   to the fork succeeds.
5. The created PR URL is under `https://github.com/sase-org/sase/pull/...`, and its head
   label is `<machine-user>:<branch>`.
6. The PR's initial Actions run follows the configured external-contributor approval
   policy and receives no upstream secrets.
7. The machine account cannot merge or submit the upstream PR; the maintainer profile
   can review and merge it.
8. With only `sase--agents` access granted, an external SASE commit publishes a distinct
   `<machine-user>.athena_contrib...` hood and Bryan's normal profile imports it after
   `sase agent sync`.
9. Removing the sidecar grant produces a clear, recoverable publication failure without
   affecting the already-pushed code branch or PR.

## Recommended solution

Create one automation-only GitHub machine account, give it a dedicated SSH key and
isolated `gh`/Git/SASE profile, and fork `sase-org/sase` into that account. Never make
the account a member or collaborator of the upstream code repository. Add a `master`
branch ruleset requiring pull requests with no routine bypass, both to protect normal
work and to make accidental use of Bryan's admin credentials visible.

Use the machine fork as SASE's `origin`. Until SASE becomes fork-aware, set
`GH_REPO=sase-org/sase`, verify the first PR's upstream URL and head label, and fall back
to explicit `gh pr create --repo ... --head ...` after SASE pushes if necessary. Track a
SASE change that carries fork-parent metadata into numbered workspaces and supplies
explicit repository/base/head arguments to all PR lifecycle commands.

For the collaboration experiment, grant the machine account write access first to only
`sase-org/sase--agents` and pin that sidecar in its external SASE profile. This preserves
the key invariant—GitHub itself rejects every upstream code push—while enabling real
two-owner agent-hood publication and import. Expand access to `--plans`, `--beads`, or
`--research` one at a time when a test specifically needs shared writes. This is more
faithful, safer, and more diagnostic than trying to make Bryan's privileged account
behave as though it were unprivileged.
