# Just Install: PyPI Prod And Editable Dev

**Date:** 2026-10-08 · **Researcher:** grk · **Scope:** sase Justfile install recipes, uv-tool daily driver, linked sase-core, agent/CI blast radius

> **Question.** How should `just` grow a reliable, intuitive, beautiful way to install sase from PyPI (prod) and from a matching editable checkout (this tree plus the right sase-core), given that `just install` already means “editable sase into this clone’s `.venv`”?

## Bottom line

The *capability* is worth building. The *rename-and-steal* of `just install` as sketched is a high-blast-radius footgun.

Today SASE already has two complete install worlds that share a name in the contributor’s mouth and almost nothing else in the machine:

| World | Command today | Target | Who uses it |
| --- | --- | --- | --- |
| Daily driver | `uv tool install sase`, `sase update --to pypi\|dev` | `$(uv tool dir)/sase` | Humans running `sase` |
| Contributor venv | `just install`, `just _setup` | `<checkout>/.venv` | Agents, CI, `just check` |

The missing piece is a **bootstrap** that puts *this Justfile’s checkout* (and its matching sase-core) onto the daily-driver uv-tool environment, without requiring a working `sase` already. `sase update --to dev` does a different job: it clones canonical trees under `update.dev_root` (`~/projects/github/sase-org/{sase,sase-core}`).

**Recommended shape.** Keep three nouns, never let `just install` silently change meaning:

```text
just install          # dispatcher: status + the three nouns
just install pypi     # PyPI wheels → uv-tool daily driver
just install dev      # THIS checkout + matching sase-core → uv-tool
just install venv     # current just install (also: just install-venv)
```

Ship the two uv-tool recipes first, with `just install` still meaning venv until the dispatcher lands in the same change that rewrites memory, doctor strings, and CI. Agents keep using the venv path. Global-mutating recipes refuse `SASE_AGENT`.

---

## Critique of the proposed plan

The request is: rename `just install*` → `just install-venv*`, then add `just install` (PyPI) and `just install-dev` (editable + matching core).

That diagnosis is half right. The current names hide that they only feed `.venv`. A human who wants “install sase” and types `just install` in this repo is currently setting up tests, not their `sase` binary. Freeing a short name for the daily driver is a real UX win.

The proposed assignment of the short name is the problem.

### 1. `just install` is load-bearing infrastructure

It is not a leftover alias. It is the documented contributor bootstrap and the string agents, doctor, CI, and tests repeat:

- `CONTRIBUTING.md`, `README.md`, `docs/development.md`, `docs/rust_backend.md`
- Reference memory `lint_and_test.md` and `symvision.md` (“you MAY need to run `just install` before `just check`”)
- Doctor next-steps (`src/sase/doctor/checks_runtime_environment.py`)
- Import-error hints (`src/sase/core/rust.py`: “reinstall with `just install`”)
- Inline-memory tests that snapshot the `lint_and_test.md` recipe list
- CI: `.github/actions/setup-sase/action.yml` defaults `install-recipe: install` and allowlists `install|install-visual`. Workflows pass `install-visual` for visual jobs.
- Guarded-recipes decision: `install` is **never** guarded, because it is the venv heal path.

If `just install` starts meaning “overwrite the host uv-tool with PyPI wheels”:

- An agent following stale memory installs *published* sase over the human’s daily driver.
- CI `setup-sase` with the default recipe stops creating `.venv` from the PR and instead `uv tool install`s PyPI sase on the runner.
- Doctor’s “run `just install` in this workspace” starts mutating a shared host environment from an ephemeral `sase_<N>` clone.

That is not a rename. It is a semantic inversion of the highest-frequency just recipe in the project.

### 2. `sase update --to` already owns the in-product switch

`sase update --to pypi|dev` already:

- Reconstructs the full plugin set from `uv-receipt.toml` (uv’s `--with` *replaces*, it does not append)
- Clones or fast-forwards checkouts under `update.dev_root`
- Rebuilds `sase-core-rs` via `just rust-install-uv-tool`
- Takes the code-swap lock, restarts the scheduler, refreshes shell completion
- Previews, confirms, logs, and renders a live timeline

A Justfile that reimplements that in bash will drift. A Justfile that shells out to `sase update --to` cannot *bootstrap*: those commands refuse unless the running interpreter is already a uv-tool sase with a receipt.

The just recipes earn their keep as **bootstrap + this-checkout** entry points. They should call shared Python (a stdlib `tools/` script, or mode-switch with a bootstrap path) rather than copy the receipt logic.

### 3. `--to dev` is the wrong backend for “install this tree”

`sase update --to dev` materializes `~/projects/github/sase-org/sase` and, when `cargo` is on `PATH`, `~/projects/github/sase-org/sase-core` at the default-branch tip. It does not:

- Install the Justfile directory you are standing in
- Honor `sase/repos/linked/sase-core` or `SASE_CORE_DIR`
- Check out `sase-core-revision.txt`

The user asked for “the appropriate sase-core checkout for that *dev version*.” For a just recipe run from a workspace or a dirty feature branch, that means **this tree’s resolved core**, containing this tree’s pin, built into the uv-tool venv. A second clone at `origin/master` is the wrong core the moment the branch has moved the pin or the linked checkout has local work.

`--to pypi` *is* a reasonable backend for `just install pypi` once a uv-tool install exists. The PyPI just recipe is the bootstrap half plus a thin wrapper.

### 4. `just install-venv-terminal-smoke` is not beauty

Hyphen piles (`install-venv-visual`, `install-venv-terminal-smoke`) are how we got unintuitive names in the first place. A dispatcher with a venv extra (`just install venv`, `just install-venv-visual`) is easier to scan in `just --list` than a forest of prefixes.

### 5. Global mutation from a workspace is a new class of command

`just check` is checkout-local. `just install` today is checkout-local. `uv tool install` is host-global. Putting the global mutation on the short name `just install`, runnable from every ephemeral workspace, without confirmation and without an agent refusal, will eventually clobber a running host sase under other agents. The guarded-recipes record says venv `install` stays unguarded; that claim does not extend to a host-tool rewrite.

---

## Requirement adjustments

These change the request. Each is justified by the facts above.

**R1. Do not silently invert `just install`.**
The short name becomes a dispatcher (status + nouns) in the same change that rewrites docs/memory/CI. Until that change, `just install` continues to mean the venv recipe. A compatibility error that prints the map is acceptable; a silent PyPI install is not.

**R2. `just install dev` installs *this* Justfile directory.**
It does not clone `update.dev_root`. That remains `sase update --to dev`. Document the two jobs side by side so they do not collapse.

**R3. Matching sase-core is this checkout’s resolved core plus its pin.**
Use the existing Justfile `sase_core_dir` chain (`SASE_CORE_DIR` → workspace-scoped linked env → `sase/repos/linked/sase-core` → sibling `../sase-core`). Ensure `sase-core-revision.txt` is contained in that checkout. Build with `rust-install-uv-tool` (release / wheel cache). Leave a dirty core worktree in place when it still satisfies the pyproject floor; fail closed when it is behind the pin and cannot fast-forward.

**R4. uv-tool recipes refuse `SASE_AGENT`.**
Exit 2 with the dispatcher map unless `SASE_TOOL_BYPASS` is set. Venv recipes stay unguarded, matching `decisions:guarded-recipes`. Host-tool rewrites are a different command class.

**R5. Preserve injected plugins.**
PyPI and dev uv-tool installs reconstruct `--with` from the existing receipt when one exists. They also keep `plugins.required` satisfied (linked checkout editable if present, else the declared PyPI spec), the same contract `tools/setup_required_plugins` already enforces for `.venv`.

**R6. Post-condition is health, not uv’s exit code.**
A successful recipe prints `sase version` and passes `sase core health`. Dev additionally verifies the loaded `sase_core_rs` was built from the resolved core identity (the `.sase-core-rs-source.json` stamp `rust-install` already writes).

**R7. Confirmation on mode switches.**
Switching pypi ↔ editable, or retargeting editable from one checkout to another, is `[confirm]` in a TTY and `--yes` in scripts. Same-mode no-ops skip the prompt.

**R8. Rename the venv recipes, but keep a short venv noun.**
`just install-venv` / `just install-venv-visual` / `just install-venv-terminal-smoke` are the mechanical names CI and agents need. `just install venv` is the human noun. Private `_setup` stays private and venv-scoped; `just check` continues to heal `.venv` through `_setup`, not through the uv-tool recipes.

**R9. Do not teach end users to clone-then-just.**
`INSTALL.md` / `docs/getting_started.md` stay on `uv tool install sase`. The just recipes are for people who already have this repo (contributors, Bryan’s daily-driver switch, workspace dogfooding).

**R10. One implementation core, two fronts.**
Justfile recipes are thin. Shared logic lives in a bootstrap-safe `tools/install_sase_tool` (stdlib + `uv` + `just rust-install-uv-tool`; no import of `sase` so a broken daily driver can still be repaired). When a healthy uv-tool `sase` is already running, the PyPI path may delegate to `sase update --to pypi -y` for restart, completion refresh, and the live timeline.

---

## Current surface (facts)

### Contributor venv (`Justfile`)

`install`, `install-visual`, and `install-terminal-smoke` all:

1. Ensure `.venv`
2. Prefer `SASE_CORE_WHEEL` (CI), else `rust-install` from `sase_core_dir` when `Cargo.toml` + `cargo` exist
3. `uv pip install --no-sources $(just _core-overrides-arg) -e ".[dev…]"`
4. `install` also runs `_setup-required-plugins`

`_setup` is the incremental twin used by `lint` / `test` / `check`. It validates via `tools/validate_test_environment`, rebuilds core when the source-identity stamp drifts, and only re-resolves Python deps when the group is stale. That is why agents often skip an explicit `just install`: the next `just check` heals.

`rust-install-uv-tool` already installs the local extension into `$(uv tool dir)/sase`. It is fail-open (exit 0) when uv or the tool venv is missing. A new `install dev` recipe must treat that as a hard error after it has just created the tool venv.

Core resolution is already careful: workspace-scoped linked paths only when they sit under this Justfile directory, so a shell inherited from another numbered workspace cannot build the wrong core. `_refresh-sase-core-checkout` fast-forwards a *clean, strictly-behind* core. Stale-behind-floor is a hard error unless `SASE_ALLOW_STALE_CORE=1`.

### Daily driver (product)

Canonical human path: `uv tool install sase`. Updates and plugins require that method; pip/pipx fail fast.

`sase update --to pypi` reinstalls index requirements for sase + plugins (sase-core-rs comes along as a dependency). `--to dev` clones owner-nested GitHub trees and rebuilds core with `just rust-install-uv-tool` from the *cloned* sase path.

Dev updates skip a host fast-forward when the target `sase-core-revision.txt` is missing from the core checkout. Mode-switch *to* dev does not pin-checkout that SHA; it uses default-branch HEAD. That is a reliability gap the new just recipe should close for the this-checkout path.

### Pin vs window vs checkout

Three different “which core?” answers already coexist:

- **CI pin:** `sase-core-revision.txt` (currently a 40-character SHA). Linked `sase-core` declares `revision_pin: sase-core-revision.txt`.
- **Published window:** `pyproject.toml` `sase-core-rs` specifier, ratcheted only on the release branch. Editable installs lift it with a uv overrides file so a local build is never downgraded to a wheel inside the window.
- **Source identity:** `HEAD` plus a digest of core sources, recorded in the venv as `.sase-core-rs-source.json`.

“Appropriate for this dev version” is the pin as a *floor* and the resolved checkout as the *source*. Building the published wheel, or cloning a disconnected master, is the wrong answer for `install dev`.

---

## Design

### Vocabulary

Three nouns, one dispatcher:

| Noun | Target | Source | Core |
| --- | --- | --- | --- |
| `pypi` | uv-tool | PyPI `sase` | published `sase-core-rs` wheel |
| `dev` | uv-tool | `-e` this Justfile directory | resolved `sase_core_dir`, pin-contained, `rust-install-uv-tool` |
| `venv` | `<checkout>/.venv` | `-e ".[dev]"` | same resolution as today, including `SASE_CORE_WHEEL` |

Extras stay hyphenated because CI and optional groups need stable recipe names:

- `just install-venv` — body of today’s `install`
- `just install-venv-visual`
- `just install-venv-terminal-smoke`

`just --list` groups (just 1.50, already pinned in `setup-sase`):

```text
[tool]
  install            Show install status and the pypi / dev / venv nouns
  install-pypi       Alias of `just install pypi`
  install-dev        Alias of `just install dev`

[venv]
  install-venv       Editable sase + core into this checkout's .venv
  install-venv-visual
  install-venv-terminal-smoke
```

Hyphen aliases exist so scripts and muscle memory do not have to remember argument syntax. The dispatcher is what a human sees.

### Preview (the beautiful part)

Before mutating, print a box. After, print the same box with health.

```text
┌─ just install dev ─────────────────────────────────────────────┐
│ daily driver   uv-tool  ~/.local/share/uv/tools/sase           │
│ from           editable  /home/bryan/projects/github/sase-org/sase
│                (this Justfile)                                 │
│ sase-core      source    sase/repos/linked/sase-core           │
│                pin       e8606a564e4d  contained in HEAD       │
│ plugins        keep      sase-github, sase-research-artifacts  │
│                required  both present (linked editable)        │
│ rust           release   rust-install-uv-tool                  │
│ currently      pypi      sase 0.x.y  /  sase-core-rs 0.y.z     │
└────────────────────────────────────────────────────────────────┘
Switch daily driver from pypi → editable this checkout? [y/N]
```

`just install` with no args prints the box for the *current* daily driver and `.venv`, plus the three nouns, and exits 0. That is the status command; a separate `install-status` is unnecessary.

Colors: reuse the `sase update` palette (step checkmarks, dim paths, yellow for mode change). Progress to stderr, summary to stdout, same split as `sase update`.

### `just install pypi`

1. Refuse if `SASE_AGENT` is set (R4).
2. Require `uv` on `PATH`.
3. If a uv-tool receipt exists and `sase` is already that install: `sase update --to pypi` (honors `-y` / confirm). This gets plugin reconstruction, restore backup, scheduler restart, completion refresh, live timeline.
4. Else bootstrap: `uv tool install --force --reinstall sase` plus reconstructed `--with` from a receipt if one is on disk, else `plugins.required` from `sase/sase.yml`.
5. `sase version` and `sase core health`. Fail the recipe if health fails.
6. Restart scheduler if it is running and sase is now importable.

No local rust build. No `SASE_CORE_DIR`. The published wheel is the point.

### `just install dev`

1. Refuse if `SASE_AGENT` is set.
2. Require `uv`, `git`, and (for core) `cargo`. Missing cargo: fail closed with “install rustup, or use `just install pypi`”. Do not silently keep a published core wheel — that is how “matching core” gets lost. (Adjustment vs `--to dev`, which keeps the wheel and warns.)
3. Resolve `sase_core_dir`. If absent, clone `sase-org/sase-core` to the Justfile fallback (`sase/repos/linked/sase-core` in a workspace, else `../sase-core`) and check out the pin SHA.
4. Pin algorithm (R3):

   - Read `sase-core-revision.txt` from *this* sase tree.
   - `git fetch` when the SHA is missing.
   - Clean and behind the pin → fast-forward / checkout so the pin is an ancestor.
   - Dirty and behind the pin → fail with the existing stale-core message (`sase repo open sase-core`, `SASE_ALLOW_STALE_CORE=1` for bisects).
   - Ahead of the pin → proceed, print the same “ahead of the published window / pin; normal for local core work” note `_setup` already prints.
5. Write the editable overrides file (unconstrained `sase-core-rs`) so uv cannot replace the local build with a windowed wheel.
6. `uv tool install --force --reinstall --editable <justfile_directory>` plus reconstructed plugins (receipt editables kept as editables when those paths still exist; required plugins from linked checkouts with `--no-deps` the way `setup_required_plugins` does).
7. `just rust-install-uv-tool` against the resolved core, **failing** if the tool venv is missing.
8. Take the code-swap lock around the uv + rust steps (same `~/.sase/locks/code-swap.lock` as `sase update`).
9. Health: `sase version` shows `install_type: editable` and `source_root` equal to this Justfile directory; `sase core health` passes; source stamp matches.

Optional extra, not v1: `just install dev-fast` → `rust-dev-install-uv-tool` (dev-update profile, isolated cargo targets). Daily-driver reliability wants the release profile and the wheel cache.

### `just install venv` / `just install-venv`

Today’s `install` body, renamed. `_setup` keeps calling it conceptually (implementation can stay a private copy). Error strings that currently say “rerun `just install`” become “rerun `just install-venv`”.

CI `setup-sase` allowlist becomes `install-venv|install-venv-visual`; default `install-recipe: install-venv`. Visual workflows pass `install-venv-visual`.

### Agent and human docs

| Audience | Command |
| --- | --- |
| Agent about to `just check` | `just install-venv` if the workspace venv drifted; usually `_setup` already healed |
| Contributor first clone | `uv venv .venv && just install-venv` (CONTRIBUTING) |
| Dogfood this branch as daily `sase` | `just install dev` |
| Return daily `sase` to PyPI | `just install pypi` or `sase update --to pypi` |
| New machine, no clone | `uv tool install sase` (INSTALL.md unchanged) |
| Canonical GitHub clones as daily driver | `sase update --to dev` |

---

## Why this is more reliable than a pair of shell one-liners

A naive `just install-dev`:

```bash
uv tool install --force --reinstall -e .
just rust-install-uv-tool
```

fails in the ways this repo has already paid to fix:

- uv re-resolves `sase-core-rs` inside the pyproject window and **replaces** the local extension (`_core-overrides-arg`, `write_editable_overrides`)
- `--with` from a previous plugin set is dropped
- `plugins.required` import-check is skipped, so a dangling `.pth` looks installed
- rust-install-uv-tool exits 0 when there is no tool venv
- core checkout can be behind the pin; `_refresh-sase-core-checkout` is best-effort (`|| true`) and the floor check is the real gate
- no code-swap lock, so a running `sase bead work` can import a torn tree
- no health coda, so a green uv and a red `sase core health` look like success
- running from `sase_20` while `SASE_CORE_DIR` points at another workspace’s core is exactly the bug the Justfile’s workspace-scoped path filter exists to prevent

Reliability here means reusing those gates, not wrapping `uv` and hoping.

---

## Rollout

Do this in **one** PR for the rename, or **two** with capability first. Capability-first is the safer sequence.

**PR A — capability, zero rename**

- Add `just install-pypi` and `just install-dev` (and `just install pypi|dev` if the dispatcher can land without stealing the empty `install` recipe).
- Add `tools/install_sase_tool`.
- Tests for preview JSON, plugin reconstruction, pin algorithm, agent refusal, health failure.
- Docs: a short “Daily driver vs contributor venv” section in `docs/development.md` and a pointer from `INSTALL.md`.
- Leave `just install` as the venv recipe.

**PR B — rename, atomic string update**

- `install` → dispatcher; venv body → `install-venv`.
- CI action + workflows + `tests/test_github_actions_setup_sase.py`.
- Doctor, rust import hints, finalizer messages.
- Memory: `lint_and_test.md`, `symvision.md`; `sase memory init`. Guarded-recipes body still says venv install is unguarded; add one sentence that uv-tool recipes refuse `SASE_AGENT`.
- `tests/main/test_inline_memory.py` snapshots.
- `justfile` error strings that tell humans to rerun `just install`.

If PR B cannot land in the same week as A, **do not** make `just install` mean pypi in the gap.

A one-release compatibility stub that errors:

```text
error: `just install` is now a dispatcher.

  just install          status + nouns
  just install venv     this checkout's .venv  (what `just install` used to do)
  just install dev      this checkout → daily-driver uv-tool
  just install pypi     PyPI → daily-driver uv-tool
```

is acceptable as the *entire* body of `install` for a few days only if every agent memory file already says `install-venv`. Otherwise agents hit the error in the critical path of `just check` setup. Prefer keeping a hidden `install` alias to `install-venv` until memory has baked, *or* land dispatcher + memory in one commit.

---

## Blast radius (must-touch list)

Not exhaustive, but these are the ones that fail CI or mis-teach agents if missed:

- `Justfile` public recipes and every “rerun `just install`” string in `_setup` / `rust-install` / `rust-dev-install`
- `.github/actions/setup-sase/action.yml` (default + allowlist)
- `.github/workflows/ci.yml`, `telemetry.yml` (`install-recipe: install-visual`)
- `tests/test_github_actions_setup_sase.py` (asserts `just install SASE_CORE_WHEEL=…`)
- `tests/test_justfile_lint.py` (recipe dry-runs; docstring “`just install` must never leave a stale sase-macro-lsp”)
- `tests/doctor/test_checks_runtime.py`, `tests/test_core_rust.py`
- `tests/main/test_inline_memory.py` (embeds the lint_and_test recipe block)
- `src/sase/doctor/checks_runtime_environment.py`, `checks_providers.py`
- `src/sase/core/rust.py`, query corpus facades, `finalizers/_prepare_completion.py`
- `sase/memory/lint_and_test.md`, `symvision.md` (plan memory decisions; `/sase_memory_write`)
- `CONTRIBUTING.md`, `README.md`, `docs/development.md`, `docs/rust_backend.md`, `docs/tool.md`, `docs/monitors.md`
- Monitor quoting tests that use `just install && just check` as a *string* fixture — those may stay as historical examples, but new docs should use `install-venv`

`decisions:guarded-recipes` cites `just install && just check` as a wrapper the guard *refuses*. Update the example to `just install-venv && just check` when the rename lands; the decision itself stays.

---

## Alternatives considered

**A. User’s plan (steal `just install` for PyPI, `just install-dev` for editable).**
Short names, matches the request. Semantic inversion, CI default landmine, agent host-clobber. Rejected as the landing shape; the nouns can still be `pypi` and `dev`.

**B. Only document `uv tool install` / `sase update --to`.**
Zero just work. Leaves the this-checkout daily-driver gap and the bootstrap-when-sase-is-broken gap. The request is specifically those gaps.

**C. `just tool-install` / `just tool-install-dev`, leave `just install` forever as venv.**
Safest rename avoidance. Worse names. Acceptable as PR A’s public names if the dispatcher is deferred; the dispatcher is still the better end state.

**D. Add `sase update --to checkout` and make just a one-liner.**
Good long-term product surface (TUI `m` could offer “this checkout”). Still needs a just bootstrap when `sase` is missing or not a uv-tool install. Do not block v1 on the CLI flag; keep the tool script callable from both.

**E. Have `just install dev` also refresh `.venv`.**
One command that “does everything.” Mixes the two worlds again. `just check` already heals `.venv` via `_setup`. Daily-driver and test venv can legitimately differ (release uv-tool vs editable `.venv`). Keep them separate.

---

## Recommended solution

1. **Treat this as two features:** (i) a this-checkout daily-driver bootstrap, (ii) a rename of the venv recipes so the short name can become a dispatcher. Ship (i) first if they cannot land together.

2. **Public interface:**

   ```text
   just install            # status + nouns (TTY box); exit 0
   just install pypi       # PyPI → uv-tool; alias just install-pypi
   just install dev        # this tree + matching core → uv-tool; alias just install-dev
   just install venv       # .venv; alias just install-venv
   just install-venv-visual
   just install-venv-terminal-smoke
   ```

3. **Implementation:** `tools/install_sase_tool` (stdlib, bootstrap-safe) owned by the Justfile recipes. Reuse receipt reconstruction, editable overrides, code-swap lock, pin containment, `rust-install-uv-tool`, and the health coda. Delegate PyPI to `sase update --to pypi` when a healthy uv-tool sase is already the running install.

4. **Core matching:** resolved `sase_core_dir` for this Justfile; `sase-core-revision.txt` must be contained; dirty-behind fails closed; ahead is allowed and noted; cargo missing fails closed on the dev path.

5. **Safety:** uv-tool recipes refuse `SASE_AGENT`; confirm on mode change; CI allowlist and default move to `install-venv*` in the same commit as the rename; memory (`lint_and_test.md`, `symvision.md`) in that same commit via `/sase_memory_write`.

6. **Beauty:** one preview box, grouped `just --list`, stderr progress / stdout summary, `sase version` + `sase core health` as the last frame. End users still get `uv tool install sase` with no clone.

That is the design I would implement. The original plan’s intent — make the just nouns match the two installs a SASE developer actually wants — is right. The original plan’s assignment of the bare name `just install` to PyPI, and its use of “dev” as if it were `sase update --to dev`, are the parts to change before anyone writes the Justfile.
