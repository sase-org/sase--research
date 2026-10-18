# Track 0 (ship sase 0.18.0): what got done and what is left for you

> **Request:** Do all the work that can be done from Track 0 of
> [the PyPI release reliability design](pypi_release_reliability_design_and_work_split/pypi_release_reliability_design_and_work_split.md),
> then write a short report on whatever remains for you to do.

## Bottom line

- **The release is on track and needs nothing from you yet.** sase-core-rs 0.42.0 is on
  PyPI, and release PR #299 is green. The release watcher (`sase-1mk.8`) is driving the
  rest: `ci_watch` merges #299, then the watcher publishes.
- **I made the one Track 0 code change: the `publish.yml` exact-build fix.** 0.18.0's
  wheel and sdist will be built from the release commit, not from whatever `master`
  happened to be when the Publish run started. It is committed with this run. Every
  lint gate and the 192 workflow and release-watch tests pass. The full `just check`
  could not go green, for two reasons that have nothing to do with the fix (see
  "Verification note").
- **The PyPI size request was already filed.** It is
  [pypi/support#12339](https://github.com/pypi/support/issues/12339), opened 2026-09-19
  and still waiting for PyPI staff. There is nothing to file.
- **Your part is about 10 minutes, after 0.18.0 is on PyPI:** run the two checks below,
  and do one macOS install by hand. The stale epics are superseded for you.

## Where things stand (19:29Z, 2026-10-18)

- **PyPI `sase`:** 0.17.1, still uninstallable.
- **PyPI `sase-core-rs`:** 0.42.0. Publish run
  [`39146142368`](https://github.com/sase-org/sase-core/actions/runs/39146142368)
  succeeded.
- **Release PR #299:** open and `CLEAN` (all checks green), waiting for `ci_watch` to
  merge it.
- **A clean resolve of the family today gives:** `sase 0.1.0`, `sase-github 0.1.0` and
  `sase-telegram 0.4.9`. This is the outage Track 0 fixes.

## What I did

1. **Exact-build fix in `.github/workflows/publish.yml`** (Track 0, step 2):
   - The `release` job now exports release-please's `sha` output, the commit it tagged.
   - The `build` job checks out that commit. A guard step fails the build if
     release-please reports a release but no SHA. A `Record the built commit` step logs
     the SHA it built.
   - The `install-smoke-core-floor` job reads the core floor from that same commit, so
     the floor it tests matches the wheel.
   - `publish_existing` dispatches behave as before: the SHA is empty, so they build
     the dispatched ref.
   - A new contract test is in `tests/test_github_actions_publish.py`. All 5 tests pass.
     I first confirmed in the release-please-action v5 source that `sha` is a
     root-component output.
2. **Tested the post-release verification recipe on 0.17.1.** The recipe downloads the
   PyPI files, checks their SHA-256 digests, and compares them with `git archive` of the
   tag. For 0.17.1 every file matched. The same commands are below, ready for 0.18.0.
3. **Checked the size request.** It is already filed (see above).

**What I deliberately did not do:**

- I did not merge #299, dispatch Publish or the core cut, or touch any beads.
  - The watcher and `ci_watch` own those steps, so doing them by hand would race them
    (the design's "one decider" rule).
  - Superseding the stale epics is the `sase-1mk` lander's job, after the release is
    confirmed.

**Timing note on the fix:**

- If it reaches `master` before #299 merges, 0.18.0 is built from its tag commit.
  `master` will then need one green Master Gate run on the new commit before `ci_watch`
  merges #299, which is a short delay.
- If it lands after the merge, the watcher already dispatches Publish right after the
  merge, so `GITHUB_SHA` is the release merge commit anyway.
- Either way, the check in step 1 below confirms the result.

**Verification note:** `just check` failed twice, and neither failure comes from the
fix.

- **`SASE validation` fails in every workspace right now.** A research-sidecar commit
  from earlier today (`dcbfd0dc`) hand-edited the generated research `README.md` to add
  a "Topic Tags" section. `sase init repo --check` wants to remove it. I filed this as
  bug `sase-1mm` and left the README alone, since reverting it would undo that agent's
  work.
- **The scoped test stage escalated to the full suite**, because the sase-core checkout
  moved to 0.42.0. That is 56,501 tests on one worker, about 10 hours on this loaded
  host, so I stopped it. Instead I ran every test that reads `publish.yml` or the
  release watcher: 192 passed. CI tests the commit again after it lands: Master Gate
  on push, and the full matrix on its schedule.

## What is left for you

### Optional, any time: triage `sase-1mm`

- Until it is fixed, every agent's `just check` fails at `SASE validation`. It will show
  up as a TaskTriage gate. Launch it, or fix the README by hand.

### While the watcher runs: nothing, unless it gives up

- The watcher has a 12 h deadline, so it gives up at about 04:30Z on 2026-10-19 at the
  latest.
- If `sase-1mk.8` closes as **canceled**, its note gives the verdict and the last
  state. Read that note before doing anything by hand.

### After `sase` 0.18.0 is on PyPI (about 10 minutes)

**1. Check that what shipped is the tag.** Run this from any sase checkout:

```bash
v=0.18.0; repo=~/projects/github/sase-org/sase
git -C "$repo" fetch -q --tags origin
d=$(mktemp -d); cd "$d"; mkdir dl tag whl
curl -s "https://pypi.org/pypi/sase/$v/json" \
  | python3 -I -c 'import json,sys; [print(u["url"], u["digests"]["sha256"]) for u in json.load(sys.stdin)["urls"]]' \
  > urls.txt
while read -r url sha; do (cd dl && curl -sLO "$url"); echo "$sha  dl/${url##*/}"; done < urls.txt | sha256sum -c
git -C "$repo" archive "v$v" | tar -x -C tag
tar -xzf "dl/sase-$v.tar.gz" -C dl && (cd whl && unzip -q "../dl/sase-$v-py3-none-any.whl")
command diff -rq "dl/sase-$v/src" tag/src && command diff -rq whl/sase tag/src/sase && echo "PASS: PyPI files match v$v"
grep __version__ whl/sase/__init__.py
```

- **Pass:** both files print `OK`, you see `PASS`, and `__version__` is `"0.18.0"`.
- **Bonus check:** in that release's Publish run, the `build` job's
  `Record the built commit` step should print the same SHA as
  `git rev-parse v0.18.0^{commit}`. If the step is missing, the fix was not yet on
  `master` when the release published. The diff above is then the proof that matters.
- **Attestation note:** PyPI's attestation names the Publish run's trigger commit,
  which can differ from the tag even when the bytes are right. The design says to accept
  this once and record it; E2.1 removes it by running the publisher at the tag.

**2. Re-resolve the family on Linux:**

```bash
d=$(mktemp -d); cd "$d"; printf 'sase\nsase-github\nsase-telegram\n' > req.in
uv pip compile req.in --python-version 3.12 --no-cache -q \
  --index-url https://pypi.org/simple/ | grep -E '^sase'
```

- **Expect:** `sase==0.18.0`, `sase-core-rs==0.42.x`, `sase-github==0.2.24` and
  `sase-telegram==0.4.29`.
- **Fail:** anything showing `0.1.0` means a resolver fallback and is a failure.
- **Optional:** also run `gh workflow run install-smoke.yml -R sase-org/sase` to get the
  daily install smoke green now instead of at 07:26Z.

**3. Install once on macOS, by hand.**

- Track 0's exit asks for "family canary green on both OSes", but there is no macOS
  canary yet; E1.2 adds one.
- Until then, run this on the Mac. It installs into a throwaway directory, so your
  normal install is untouched:

  ```bash
  t=$(mktemp -d)
  UV_TOOL_DIR=$t/tools UV_TOOL_BIN_DIR=$t/bin uv tool install sase --with sase-github --with sase-telegram
  "$t/bin/sase" version && "$t/bin/sase" core health
  ```

- **Pass:** `sase version` prints 0.18.0 and `core health` succeeds.

### Done for you once the release is confirmed

- **Superseding `sase-1jz`, `sase-1lh`, `sase-16p` and `sase-10d`:** the `sase-1mk`
  lander does this, because the epic's `stale_epics = supersede` decision tells it to.
  Step in only if the lander skips it.

### After Track 0

- **Next per the design:** turn E1 (installable family), E2 (release train and steward)
  and E3 (trustworthy signal) into epic plans. They can start in parallel.
- **The size request:** nothing to do; it is waiting on PyPI staff.
