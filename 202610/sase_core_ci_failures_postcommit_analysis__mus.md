# sase-core CI Failures: Nature, Causes, and Why a Post-Commit Hook Is the Wrong Fix

Researcher: mus (independent swarm report, `__mus` suffix).
Scope: the linked `sase-core` checkout (Rust core, `sase_core` + `sase_core_py` +
`gateway` + `macro-lsp`), its CI (`.github/workflows/ci.yml`), its gate script
(`scripts/check.sh`), and recent history leading to HEAD `cd62c83d`
(2026-10-28). Question asked: can a post-commit hook prevent recurring CI
failures?

Short answer: **do not use a post-commit hook.** A post-commit hook runs after
the commit already exists, cannot block a push, runs only on machines that
installed it, and cannot reproduce the CI matrix. The recurring failures fall
into ~10 classes, and almost all of them are "passed locally, failed on CI"
gaps that a local hook either cannot see or can only see if it runs the full
gate — at which point it should be a **pre-push hook plus protected-branch
required checks**, not post-commit.

## 1. What CI actually checks

`sase-core/.github/workflows/ci.yml`, job `rust-checks` (matrix
`ubuntu-latest` + `macos-latest`), runs exactly the `scripts/check.sh` gate:

1. `fmt-check` — `cargo fmt --all -- --check`.
2. `features` — unified dependency-feature drift gate (cargo-hakari
   `sase_workspace_hack`, tool-free `cargo tree`/`cargo metadata` comparison).
   Fix is `cargo hakari generate && cargo hakari manage-deps`.
3. `clippy --workspace --all-targets -- -D warnings`.
4. `cargo test --workspace` under a hermetic test environment.
5. `script-test` — `python -m unittest` for `.github/scripts` helpers
   (release, retention, pin checks).
6. `wheel-smoke` (separate job) — maturin abi3 wheel build, import smoke,
   `twine check`.

Two companion workflows matter: `release-plz.yml` (daily cut, publish gate,
PyPI headroom/quota, `EXPECTED_DIST_SUFFIXES` completeness) and
`runner-starvation-retry.yml` (one automatic rerun when every red job never
got a runner). There is also `pr-title.yml` (Conventional Commits).

The repo's own `AGENTS.md` states the two load-bearing facts for this report:
`master` is **unprotected**, and a red commit also fails every release-plz run;
and a targeted `cargo test -p` run is **not** a substitute for `just check`
because `-p` skips the `sase_core_py` binding tests (the gap that let stale
schema fixtures reach master in `a509dcc`).

No git hooks are installed in either checkout today: both `.git/hooks/`
directories contain only the stock `*.sample` files, and there is no
`.pre-commit-config.yaml`, lefthook, or husky config in either repo.

## 2. Taxonomy of recurring failures (with evidence)

### Class A — rustfmt drift (cheapest, most frequent)

Commits like `e08f0c2b` ("fix(ci): format plugin input type registry changes",
7 files reformatted) and half of `da22713e` ("restore a green sase-core
check") are pure formatting. Cause: author ran tests but not `cargo fmt` /
`fmt-check`. Local `cargo test` passes; CI `fmt-check` fails. This is the only
class a commit-time hook catches trivially — and it is also the class `just
fmt` fixes in seconds.

### Class B — clippy `-D warnings` on new code

`da22713e` also fixes a `clippy::nonminimal_bool` rejection in
`crates/sase_core/src/project_onboarding/classify.rs`; `ed8328f9`
("fix(clippy): isolate env mutations behind a thread-local test guard")
migrates the whole tree off `std::env::set_var`/`remove_var` after Clippy
started rejecting them under `-D warnings`. Any new lint (toolchain bump) or
new pattern re-opens this class. Local `cargo check`/`cargo test` without
`-- -D warnings` passes; CI clippy fails. A hook running only `cargo test`
misses it.

### Class C — unified-features / workspace-hack drift

`1d129cd2` introduced the `sase_workspace_hack` + `features` drift gate;
`04fbb48d` then had to fix the gate itself (cargo color polluting `cargo
tree` parse; workspace-hack needed its own release-plz tag). Any commit adding
a dependency without `cargo hakari generate && cargo hakari manage-deps`
breaks CI while local `-p` runs stay green (single-crate resolution unifies
fewer features). This failure is **invisible without the workspace-wide gate**,
which is why `check.sh`'s `default_scope` logic and the `features` step exist.

### Class D — hermetic-environment failures (passes at desk, fails on ubuntu)

The clearest "same test, different result" class. `a031ee4` committed a test
in a shallow clone with no git identity: it passed on dev hosts and macOS and
failed only on `ubuntu-latest`. The fix (documented inline in `check.sh`'s
`run_hermetic_tests`) was to clear `GIT_CONFIG_GLOBAL`/`NOSYSTEM`, set
`user.useConfigOnly`, and unset ambient `GIT_*`/`SASE_*`/`EMAIL`, plus make
each committing test set `user.name`/`user.email` in the repo it commits in.
Follow-ups `56bd9747` (shallow-clone fixture identity) and `ac370734` (scrub
git routing env, bounded batch stdin) are the same class. A developer hook
that does not replicate the hermetic wrapper will keep passing locally on
exactly the commits CI rejects.

### Class E — macOS-only path/platform behavior

The largest single cluster by commit count:

- `d99ba118`: macOS leg was non-blocking (`continue-on-error`); made blocking
  and fixed a canonicalization expectation in `git_object_sharing.rs`.
- `1fee6419` + `d4377825`: `/var` vs `/private/var` symlink — `temp.path()`
  vs `canonicalize()` mismatch in `launch_scratch_liveness`; product fix plus
  test fix to canonicalize both sides.
- `05cc860a`: goal-ledger test asserted non-canonical IDs; fixed via dir
  listings so it passes on macOS (case behavior).
- `80dc704a`: non-UTF-8 snapshot fixture path written with `fs::write`
  fails on macOS (`EILSEQ`); fixed via `git hash-object` +
  `update-index --cacheinfo`.
- `ce85b670`: `cached_golden_bytes_match_replay` failed macOS-only because
  uncontended `flock` timing (1–6 ms) was serialized into golden bytes; fixed
  by normalizing `lock_wait_ms` to zero.
- `72bf9203` / `dd56b94a`: variadic `openat` modes / `mode_t` fixes for the
  macOS build.

No Linux-only hook — post-commit or otherwise — reproduces any of these. Only
the macOS CI leg (or a macOS dev box running the full gate) catches them.

### Class F — binding/parity and fixture skew (the `a509dcc` lesson)

`a509dcc` ("resolve file artifact refs in core") is cited in `AGENTS.md` as
the incident: the author verified with `cargo test -p sase_core`, which
silently skipped the `sase_core_py` binding tests, so stale schema-version
assertions reached master. `305b7b80` + `da22713e` repeat the shape on a
smaller scale (facade fixture missing `proposed_with`). The guard since added
is procedural + scripted: `scripts/check.sh` resolves a qualifying
`PYO3_PYTHON` (≥3.12 for the `abi3-py312` feature) so the workspace build
never has an excuse to fall back, and the `require_tool_run` guard in the
`justfile` refuses raw agent `just check` outside `sase tool run check`.
A hook that forwards extra args to `cargo test -p` reintroduces the hole.

### Class G — toolchain / interpreter / output-format brittleness

- `PYO3_PYTHON` resolution: `sase_core_py` hard-errors on interpreters <3.12;
  CI pins `setup-python 3.12` and `check.sh` re-resolves locally.
- `d48aaf3e`: "Read pinned toolchain" step used GNU-only `\s`; BSD
  sed/grep on the macOS runner passed the whole line as the toolchain name.
- `04fbb48d`: `CARGO_TERM_COLOR=always` (set in CI env) wrapped the `(*)`
  dedupe marker in ANSI escapes and broke the `features` gate parse.

These are CI-harness bugs, not product bugs. A local hook on a GNU/Linux box
with a different Python and no color env cannot catch them.

### Class H — workflow action-pin drift

`cbc08c53` / `e0ddc100`: `setup-uv` stopped publishing floating `vN` tags
after v7, so `@v10` failed at "Set up job" before any step ran; the fix pins
exact releases and adds `test_workflow_action_pins.py` (run under
`script-test`). No Rust gate covers this; only `script-test` does. A hook that
runs only cargo steps misses it entirely.

### Class I — release/PyPI plumbing (not `ci.yml`, still "CI is red")

`9876b3ae`, `a908ceb3`, `e0ddc100`, `db2ce637` (`jq`-safe release-plz PR
filter), plus the long `release-plz.yml` header comment: partial uploads when
the PyPI quota trips mid-upload, yanked-file handling, `EXPECTED_DIST_SUFFIXES`
drift when the wheel matrix changes, once-a-day cut discipline (4.32 releases
a day filled the 10 GB quota). These fail the release workflow on green
`rust-checks`. Commit-time hooks cannot observe PyPI quota, yank state, or
the tagged-version completeness gate.

### Class J — runner starvation and load flakes (infrastructure, not code)

`b0c6e781` adds `runner-starvation-retry.yml`: a run whose only red jobs never
got a runner (queued then cancelled, e.g. macos universal2, 4.5 h red) is
retried once; the publish gate's next-push/six-hourly heal is the backstop.
`b12e5815` merges integration tests into one binary per crate to damp load
flakes; the `hermetic_test_env` canary exists to distinguish "fails outside
the hermetic env" from product failure. Retrying these locally is pure waste.

## 3. Why a post-commit hook cannot fix this

1. **Wrong phase.** `post-commit` fires after the commit object exists. It
   cannot block the commit or the push; at best it can print "CI will
   probably fail" or immediately create a fixup commit, which doubles commit
   noise on an already high-velocity repo (1,058 commits since 2026-08-01).
   Prevention needs `pre-commit` (cheap) or `pre-push` (full gate), not
   `post-commit`.
2. **Local-only, opt-in, bypassable.** Hooks live in `.git/hooks/`, are not
   committed, are not installed on fresh clones, do not run in CI, do not run
   on other contributors' machines unless each installs them, and are skipped
   by `--no-verify`. Every agent path (SASE agents never commit; humans and
   automation do) needs a separate install story.
3. **Cannot reproduce the matrix.** Classes D–G and J require the ubuntu +
   macOS matrix, the hermetic wrapper, pinned Python 3.12, and the
   workspace-wide features gate. A 30-second local `cargo test -p` gives false
   confidence (Class F) while a faithful local replica costs the full
   `just check` (~5 minutes per `AGENTS.md`; cold check ~85 s per `1d129cd2`).
   Nobody will wait 5 minutes inside a post-commit hook on every commit.
4. **Misses whole workflows.** Classes H–I live in YAML + PyPI state, not in
   the working tree at commit time. Only `script-test` and the release
   workflow itself see them.
5. **The binding constraint is server-side.** `master` is unprotected: a bad
   commit lands immediately and then poisons every release-plz run. No
   client-side hook, however diligent, substitutes for a required-checks gate
   on the branch.

## 4. Recommended solution

**Do not add a post-commit hook. Instead, (a) protect `master` with required
status checks, and (b) ship an opt-in pre-push hook that runs the same
`scripts/check.sh` gate CI runs.**

Concrete steps, in order of leverage:

1. **Branch protection on `master` (highest leverage, fixes the blast
   radius).** Require `rust-checks (ubuntu-latest)`, `rust-checks
   (macos-latest)`, `release workflow scripts`, and `wheel-smoke` to pass
   before merge; require PRs (no direct pushes) or at minimum required
   checks on push. This single change converts every Class A–H failure from
   "red master poisons release-plz" into "red PR blocks merge." Keep the
   `runner-starvation-retry` + publish-gate backstop for Class J.
2. **Pre-push (not pre-commit, not post-commit) local hook, committed to the
   repo.** Add `scripts/install-hooks.sh` that installs a `pre-push` hook
   running `./scripts/check.sh all` (the CI entrypoint, ~5 min) or, for
   interactive speed, `fmt-check + features + clippy` on pre-commit and the
   full `all` on pre-push. Document it in `README.md`/`AGENTS.md` next to
   `just check`. Rationale for the split: formatting/clippy/features are fast
   enough to run per-commit; the full `cargo test --workspace` + `script-test`
   + wheel build belongs at push time. Never forward `-p` selections from the
   hook (Class F); always run the workspace scope CI runs.
3. **Keep the already-landed structural fixes; do not regress them.**
   Workspace-hack drift gate, hermetic wrapper + canary, `PYO3_PYTHON`
   resolver, BSD-portable toolchain parse, colorless tree parse, macOS leg
   blocking, action-pin unit test, `EXPECTED_DIST_SUFFIXES` completeness
   check, daily-cut discipline. Each maps to one failure class above; the hook
   is only the delivery vehicle, and CI remains the source of truth.
4. **Optional accelerator, not a substitute:** `just fast` (`cargo check
   --workspace --all-targets`) as the inner loop between pushes, per
   `AGENTS.md`. It catches compile errors in ~85 s without replacing the gate.
5. **What to explicitly not build:** a post-commit auto-fix/amend loop (rewrites
   history under the user, races with pushes, and still skips the matrix), a
   per-commit full-gate hook (will be `--no-verify`'d within a week), or a
   second gate script diverging from `scripts/check.sh` (the repo already
   enforces "single source of truth" for exactly this reason).

Verification note: this report is history- and code-based (CI YAML, gate
script, `git log` evidence above). I did not re-run the 5-minute `just check`
gate or the release workflow; the cited fix commits and inline script comments
are the corroboration for each class. Re-running the full gate is the natural
next step before implementing the hook, not a precondition for choosing
pre-push + branch protection over post-commit — the phase argument (Section 3)
settles that choice on its own.

## 5. Files and commits consulted

- `sase-core/.github/workflows/ci.yml` — gate definition (fmt, features,
  clippy, test, script-test, wheel-smoke; ubuntu + macos matrix).
- `sase-core/.github/workflows/release-plz.yml` — header comment (publish
  gate, quota, suffix list, daily cut).
- `sase-core/.github/workflows/runner-starvation-retry.yml` + `b0c6e781`.
- `sase-core/scripts/check.sh` — `resolve_pyo3_python`, `default_scope`,
  `run_hermetic_tests`, `cmd_features`.
- `sase-core/AGENTS.md` — unprotected master, `-p` vs workspace warning,
  hermetic env, `just fast`/`just check` costs.
- Commits: `a509dcc`, `a031ee4`, `1d129cd2`, `04fbb48d`, `d48aaf3e`,
  `d99ba118`, `1fee6419`, `d4377825`, `05cc860a`, `80dc704a`, `ce85b670`,
  `72bf9203`, `56bd9747`, `ac370734`, `e08f0c2b`, `da22713e`, `ed8328f9`,
  `cbc08c53`, `e0ddc100`, `db2ce637`, `b12e5815`, `305b7b80`.
