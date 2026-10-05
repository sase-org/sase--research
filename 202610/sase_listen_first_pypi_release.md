# 📦 Publishing sase-listen to PyPI for the First Time

> **Question:** what needs to happen before `uv tool install sase-listen` works from PyPI?
>
> **Bottom line:** the package is ready, and so is most of the release pipeline. The
> code builds, passes `twine check --strict`, and passes a clean-venv install smoke
> test. The Publish workflow already uses trusted publishing. Nothing has reached PyPI
> because the release pipeline has never gotten past its first job. Three fixes clear it:
> **(1)** add the `SASE_RELEASE_TOKEN` secret that every sibling repo has, **(2)** register
> sase-listen as a pending trusted publisher on PyPI, and **(3)** create the `v0.1.0`
> GitHub release that was never made. After that, merging release-please's next PR
> publishes **0.1.1** (the current `master`) to PyPI automatically.

_Checked live 2026-10-05 against `sase-org/sase-listen@355e649` (master), GitHub repo and
Actions settings, and pypi.org. PyPI account pages need a login, so pending-publisher
state could not be checked from here._

---

## The steps

Do them in this order. Step 2 has to come before step 5, or the publish job fails.

1. **Add the release token to the repo.** Run
   `gh secret set SASE_RELEASE_TOKEN -R sase-org/sase-listen` and paste the same PAT
   that sase, sase-github, sase-telegram, and sase-research-artifacts already use. If it
   is a fine-grained PAT, first add `sase-org/sase-listen` to its repository list
   (Contents, Pull requests, and Issues all need read/write).
2. **Tell PyPI to trust the workflow.** Go to <https://pypi.org/manage/account/publishing/>,
   choose **Add a new pending publisher → GitHub**, and enter: project `sase-listen`,
   owner `sase-org`, repository `sase-listen`, workflow `publish.yml`, environment
   `pypi`.
3. **Create the missing 0.1.0 release.** This gives release-please its starting point:
   ```bash
   gh release create v0.1.0 -R sase-org/sase-listen \
     --target ef84b3ba7a86e54a629c031f61bceb4fb089f368 \
     --title v0.1.0 --notes "First tagged release. See CHANGELOG.md."
   ```
   (`ef84b3b` is the merge commit of release PR #1.)
4. **Have release-please open the release PR.** Re-run the most recent failed Publish
   run (`gh run rerun 37342958185 -R sase-org/sase-listen --failed`), or push any commit
   to `master`. Expect a PR titled **`chore(master): release 0.1.1`**. Its CHANGELOG
   should list only work done after 0.1.0 (web/URL fetching, PDF sources, feed host,
   brief/full editions, the live checklist, and so on).
5. **Merge that PR** once CI is green. On that push, the Publish workflow tags
   `v0.1.1`, builds the wheel and sdist, smoke-tests them with a tone-engine render,
   and uploads to PyPI. Watch it with `gh run watch -R sase-org/sase-listen`.
6. **Check the result.** <https://pypi.org/project/sase-listen/> should show 0.1.1.
   Then, on athena and apollo, switch from git installs to
   `uv tool install --force sase-listen` and confirm that `sase-listen --version`
   prints 0.1.1.
7. **Clean up the docs.** Remove the "no PyPI release yet" notes and the `git+https`
   install workarounds (see [Follow-ups](#follow-ups)).

Optional, matching the sibling repos: restrict the `pypi` environment to the `master`
branch (**Settings → Environments → pypi → Deployment branches**). sase-telegram does
this.

---

## Where you stand

|     | Piece                       | State                                                                                                                                                                                                                       |
| --- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ✅  | Package metadata            | `pyproject.toml` has name, version 0.1.0, MIT license with `license-files`, readme, classifiers, project URLs, the `sase-listen` console script, and `requires-python >=3.12`. Every dependency is on PyPI; none are git or URL deps. |
| ✅  | Build                       | `uv build` produces `sase_listen-0.1.0-py3-none-any.whl` (620 kB) and an sdist (1.1 MB). `twine check --strict` passes for both.                                                                                             |
| ✅  | Wheel works                 | A fresh 3.12 venv runs `--version`, `doctor --json` (exit 0), and a tone render of the bundled `demo.md` (`ok: true`, 3 chapters, 30 s). These are the same checks the workflow's `install-smoke` job runs.                  |
| ✅  | CI and docs                 | The latest `CI` and `Docs` runs on master are green.                                                                                                                                                                        |
| ✅  | Name                        | `sase-listen` returns 404 on both PyPI and TestPyPI, so the name is free.                                                                                                                                                   |
| ✅  | Publish workflow            | `release-please → build → install-smoke → publish`, where publish uses `pypa/gh-action-pypi-publish` with `id-token: write` and `environment: pypi`. This matches the sibling repos.                                         |
| ✅  | `pypi` GitHub environment   | It exists, with no protection rules.                                                                                                                                                                                        |
| ❌  | `SASE_RELEASE_TOKEN`        | **Missing.** sase-listen has 0 repo secrets and 0 visible org secrets. All four sibling repos have the secret.                                                                                                               |
| ❌  | Tag or GitHub release       | **None.** There is no `v0.1.0` tag or release, even though PR #1 ("release 0.1.0") was merged on 2026-10-01.                                                                                                                |
| ❓  | PyPI trusted publisher      | Probably not configured. The upload step has never run, so it has never been tested.                                                                                                                                        |

---

## Why nothing has been published

Three problems stack on top of each other:

1. **release-please cannot open PRs.** `publish.yml` uses
   `secrets.SASE_RELEASE_TOKEN || secrets.GITHUB_TOKEN`. The secret is missing, so it
   falls back to `GITHUB_TOKEN`. At both the repo and the `sase-org` org level, Actions
   permissions are `default_workflow_permissions: read` with
   `can_approve_pull_request_reviews: false`. As a result, every Publish run since
   2026-10-01 has failed with _"GitHub Actions is not permitted to create or approve
   pull requests"_ (15 of 15 recent runs). The release job pushes the release branch,
   then fails when it tries to open the PR.
2. **The workaround PR left no tag.** PR #1 was opened by hand from the release-please
   branch. Its body says so: _"the release-please action cannot open PRs in this
   repo"_. release-please turns a merged PR into a tag and GitHub release only if the
   PR has the `autorelease: pending` label, which release-please adds itself. A
   hand-opened PR has no such label. So `v0.1.0` was never created,
   `release_created` stayed `false`, and the `build` and `publish` jobs never ran.
3. **release-please has no starting point.** With no `v0.1.0` release, release-please
   logs _"No latest release found … but a previous version (0.1.0) was specified in the
   manifest"_ and counts every commit since the bootstrap SHA. Its current branch
   (`fdaa8b4`) proposes 0.1.1, but the CHANGELOG repeats every 0.1.0 entry and links a
   compare view to the missing `v0.1.0` tag. Step 3 fixes this.

The sibling packages confirm that the trusted-publishing setup itself works. For example,
the PyPI provenance for `sase_telegram-0.4.24` names the publisher as
`{kind: GitHub, repository: sase-org/sase-telegram, workflow: publish.yml, environment: pypi}`.
That is exactly the pattern sase-listen's workflow expects.

---

## Decisions behind the steps

- **The first PyPI version is 0.1.1, not 0.1.0.** The `v0.1.0` commit is from
  2026-10-01 and lacks URL/PDF sources, the feed host, and brief/full editions. The docs
  on master already describe all of these. 0.1.1 keeps the CHANGELOG accurate, with 0.1.0
  as history and everything since in 0.1.1, and ships what the docs describe. If you want
  a bigger first number, add `"release-as": "0.2.0"` under `packages["."]` in
  `release-please-config.json` before step 4, and remove it after the release. Otherwise
  `bump-patch-for-minor-pre-major` turns `feat:` commits into patch bumps.
- **Do not label PR #1 `autorelease: pending`.** That would get release-please to tag
  `v0.1.0`, but on a later push. The `build` job checks out the push SHA, not the tag,
  so it would upload today's `master` as "0.1.0" while the tag points at the 2026-10-01
  code. Creating the release by hand in step 3 avoids this, because no upload is
  attached to it.
- **Use a PAT rather than enabling "Allow GitHub Actions to create and approve pull
  requests".** Enabling that setting would mean changing it at both the org and repo
  level. PRs opened with `GITHUB_TOKEN` also do not trigger other workflows, so CI and
  the `PR Title` check would never run on release PRs. The PAT matches the four sibling
  repos.
- **Do not upload manually with `uv publish` or twine and an API token.** It works once,
  but it skips the install smoke test and the attestations, and the next release would
  still be broken.
- **Skip the TestPyPI dry run.** The local build, strict metadata check, and clean-venv
  smoke test already cover what TestPyPI would test, and none of the siblings used it.
  The one untested piece is the OIDC handshake. If step 5 fails there, the fix is on
  the PyPI side; see Recovery below.

## Recovery if the publish job fails

- **`invalid-publisher` / OIDC error:** fix the pending publisher (step 2). Every field
  must match exactly: `sase-org`, `sase-listen`, `publish.yml`, `pypi`. Then run
  `gh workflow run publish.yml -R sase-org/sase-listen --ref master -f publish_existing=true`.
  This builds from `master` HEAD, so run it before any new commit lands after the
  release merge.
- **Partial upload** (the wheel went up, the sdist was rejected): a re-run fails on the
  file that already exists. The main sase repo avoids this with `skip-existing: true` on
  `pypa/gh-action-pypi-publish`. Consider copying that.

## Follow-ups

None of these block the release:

- **Docs that say there is no PyPI release:** `docs/field-notes.md` (lines 10 and 123),
  plus the `git+https://…` fallbacks in `docs/troubleshooting.md` and
  `docs/multi-machine.md`. Once 0.1.1 is live, replace them with `uv tool install
  --force sase-listen`.
- **README relative links:** `[…](CONTRIBUTING.md)` and `[…](LICENSE)` will be broken on
  the PyPI project page. Use absolute `https://github.com/sase-org/sase-listen/blob/master/…`
  URLs instead. The PyPI badges in the README start working once the release is live.
- **Sdist contents:** the sdist ships `AGENTS.md`, `CLAUDE.md`, `.github/`, `sase/`,
  `uv.lock`, and `docs/assets/sample.mp3`. This is harmless at 1.1 MB, but a
  `[tool.hatch.build.targets.sdist]` include list would trim it.
- **License metadata:** the wheel bundles the Inter font with its `OFL.txt`, which meets
  the font license. Optionally, declare `license = "MIT AND OFL-1.1"` and add `OFL.txt`
  to `license-files` so the metadata says the same.
