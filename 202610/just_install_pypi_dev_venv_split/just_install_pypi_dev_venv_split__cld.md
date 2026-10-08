# `just install` for prod and dev: renaming the venv recipes and adding global installers

_Researcher: cld · 2026-10-08 · sase @ `e6adb110af`, sase-core pin `e8606a5`_

## TL;DR

**The direction is right, but the plan as written is unsafe.** By the GNU convention and
by `cargo install`, `install` means "put the program where I run it from." Today
`just install` means "build this checkout's `.venv`." That naming is backwards, and the
gap it leaves is already patched outside the repo: the user's `install_sase_github` and
`install_sase_google` dotfile scripts (aliases `acei` and `aceii`) are the real dev
installer today.

The risk is that `just install` is one of the most-cited commands in the SASE world:

- about 50 files in this repo;
- triage remedies in sase-core's Rust code;
- the `sase.yml` tool catalog and the CI setup action;
- three plugin repos, which use the same name with venv meaning;
- a generated skill deployed to 7 provider directories;
- error messages printed by sase versions already installed.

If you flip the meaning silently, any agent or human following an old hint will replace
the user's editable global `sase` with PyPI wheels. That can downgrade `sase-core-rs`
below what the bead store needs, and it breaks every agent and the scheduler.

**What I recommend:** keep your names, and add four guardrails that turn a wrong
`just install` from a silent clobber into a loud refusal that fixes itself.

1. **Agents can't run the global installers.** `just install` and `just install-dev`
   refuse when `SASE_AGENT` is set, and the refusal points to `just install-venv`.
2. **Every global install shows its plan and asks before acting.** The same rule SASE
   already uses: "the confirmation _is_ the dry run."
3. **`install-dev` refuses to install from a SASE-managed `sase_<N>` workspace.** Agents
   reset those directories, so an editable global install would break without warning.
4. **The matching sase-core is defined precisely.** A sase-core checkout matches when its
   HEAD contains the commit pinned in `sase-core-revision.txt`. This is the same rule
   `sase update` already enforces. `--core pin` builds from exactly the pinned commit.

Build the installer as a small standalone Python tool (`tools/sase_install`) run through
`uv`. The `just` recipes stay thin wrappers. It builds the Rust extension before it
changes anything, holds the code-swap lock during the swap, keeps the plugin set from
uv's receipt, verifies the result, and restarts the scheduler. Then land it in phases:
rename first, guarded installers second, the cross-repo updates after that.

---

## 1. What exists today

### 1.1 Install paths you already have (more than you might think)

| Path                                                          | Installs into                     | Source                                                    | Notes                                                                                                                                                                                                                                         |
| ------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `just install` / `install-visual` / `install-terminal-smoke`  | repo `./.venv`                    | this checkout (editable) + local `sase_core_rs` build     | The same ~15 lines copied three times. They have drifted: only `install` runs `_setup-required-plugins`, and `install` tests `-d sase_core_dir` while `_setup` tests for `Cargo.toml`.                                                       |
| `_setup` (implicit dependency of `check`, `test`, `lint`, …)   | repo `./.venv`                    | same                                                      | Validates and heals the venv automatically, so contributors seldom need the explicit recipe.                                                                                                                                                 |
| `rust-install[-uv-tool]`, `rust-dev-install[-uv-tool]`, `rust-lsp-install[-uv-tool]` | a venv / `$(uv tool dir)/sase` | linked or sibling sase-core                    | **Called by name from sase's Python code**: `mode_switch/plan.py` runs `just rust-install-uv-tool` and `dev_update/_plan_reconcile.py` runs `just rust-dev-install-uv-tool`. These names are a cross-version API, so this rename must not touch them. |
| `sase update` / `sase update --to dev\|pypi`                  | uv-tool env                       | receipt; dev clones under `update.dev_root`               | Shows a live timeline, a backup and restore command, the code-swap lock, and a scheduler restart. It **needs a working uv-tool sase to run**, and `--to dev` uses `~/projects/github/<owner>/<repo>`, not "this checkout".                  |
| `uv tool install sase` (INSTALL.md)                           | uv-tool env                       | PyPI                                                      | `--with` _replaces_ the injected plugin set, so a bare `uv tool install --force sase` silently drops your plugins.                                                                                                                           |
| chezmoi `install_sase_github` / `install_sase_google` (`acei`, `aceii`) | uv-tool env              | hard-coded `~/projects/github/sase-org/*`                 | The de facto dev installer. Its strong points are a fatal sync gate, an axe maintenance window, and a post-install health probe. Problems below.                                                                                             |

**Your actual install right now** (`~/.local/share/uv/tools/sase/uv-receipt.toml`) is a
dev-mode receipt. It contains editable `sase`, `sase-github`, `sase-telegram`,
`sase-research-artifacts`, and `bugyi-chops` (from `bbugyi200`, not `sase-org`), plus an
override that lifts the `sase-core-rs` version window. `install_sase_github` would not
produce that receipt: it doesn't know about `sase-research-artifacts` or `bugyi-chops`.
So the receipt came from `sase update`/mode-switch, which shows the hard-coded script has
already drifted from reality.

Other problems in the chezmoi scripts:

- **It builds the Rust core twice.** `--with-editable sase-core-rs @ crates/sase_core_py`
  makes uv run a full maturin build with no cache, and then the script runs
  `rust-install-uv-tool` anyway.
- **It installs the LSP into the wrong place.** It runs
  `cargo install … sase-macro-lsp` into `~/.cargo/bin`. `sase lsp` looks for the binary
  in the venv's `bin/` before `PATH` (`docs/editor.md`). After you switch to PyPI, that
  stale `~/.cargo/bin` copy becomes the server `sase lsp` uses.
- **The plugin set is hard-coded twice**, once per variant: github+telegram and
  google+gchat.

### 1.2 "The appropriate sase-core checkout": three conflicting meanings in the code

1. **CI** builds `sase_core_rs` from **exactly** the 40-character SHA in
   `sase-core-revision.txt` (`docs/rust_backend.md`, "The CI source revision pin").
2. **`sase update` (dev path)** requires that the core checkout target **contains** the
   pin: `dev_update/core_pin.py` checks `git merge-base --is-ancestor <pin> <ref>`.
   Otherwise it skips the host root.
3. **The venv recipes** (`rust-install`, `_setup`) never read the pin. They check only the
   **published `sase-core-rs` floor in `pyproject.toml`**
   (`tools/validate_sase_core_rs_version`), fast-forward the checkout if it is clean and
   behind, and rely on the bindings check after the build.

Right now the linked core HEAD `e411a39` is 1 commit past the pin `e8606a5`. The ratchet
moves the pin to core HEAD every 6 h, so "HEAD contains pin" and "HEAD == pin" are usually
almost the same thing. They differ exactly when you are developing sase-core, and that is
when it matters.

### 1.3 Where the name `install` is used

Counts come from `git grep` on this tree and read-only opens of the linked repos.

- **sase repo, about 50 files.** The ones that matter most:
  - `sase/sase.yml` tool catalog entry `install: argv: [just, install]`;
  - `.github/actions/setup-sase/action.yml`, where `install-recipe` defaults to `install`
    and a `case` statement allows only `install|install-visual`;
  - `ci.yml` and `telemetry.yml`, which pass `install-recipe: install-visual` 4 times;
  - user-facing runtime remedies in `src/sase/core/rust.py`, the `doctor` checks
    (`checks_runtime_environment.py`, `checks_providers.py`),
    `finalizers/_prepare_completion.py`, and the query facades;
  - tool messages (`tools/validate_sase_core_rs`, `setup_required_plugins`, …);
  - tests that assert on those strings;
  - docs: README, CONTRIBUTING, `development.md`, `rust_backend.md`, `tool.md`,
    `monitors.md`, mobile runbooks, perf READMEs.
- **Memory:** `lint_and_test.md` (3 places: the command block, the long-commands list, and
  the IMPORTANT note about ephemeral workspaces), `symvision.md` (Verify section), and
  `decisions/guarded-recipes.md`, which says "`test` and `install` are never guarded".
  Decision records are immutable, so that one is left alone (see §6).
- **Generated skill** `src/sase/macros/skills/sase_monitor.md`
  (`-- 'just install && just check'`). It is deployed through chezmoi to the Claude,
  Codex, Muse, OpenCode, Antigravity, Grok, and Qwen skill directories.
- **sase-core (Rust):** `tool_run/triage/extractors/environment.rs` (5 remedies →
  `"just install"`), `triage/verdict.rs` (``"run `just install` or `sase update` and
  retry"``), and `bead/jsonl.rs` (``"unknown bead event operation … run `just install` to
  update sase-core"``).
- **Plugin repos** (sase-github, sase-telegram, sase-research-artifacts): each has its own
  `just install` meaning _local venv_, and their CI, `_setup`, AGENTS.md, and README use
  it.
- **chezmoi:** the 7 deployed copies of the monitor skill. The installer scripts call
  only `rust-install-uv-tool`.

Two examples show why "just repoint `install`" is dangerous:

- `bead/jsonl.rs` tells you to run `just install` "to update sase-core" when an older
  core meets a newer bead event. Under the new meaning, following that advice would
  replace a local core build with an **older published** core, which is the opposite of
  the fix.
- `sase doctor` prints "Run `just install` in this workspace" when the active `sase` import
  root differs from the cwd checkout. That is the **normal** state when the global `sase`
  runs from `~/projects/github/sase-org/sase` and the cwd is `sase_19`. Under the new
  meaning it would trigger a global PyPI reinstall. A naive `install-dev` would be worse:
  it would point the global `sase` at an ephemeral workspace.

---

## 2. Critique: is this a good idea?

### 2.1 What the plan gets right

- **The naming convention.** The GNU Coding Standards define `install` as "copy the
  executables … to their final locations" and say it should run a simple test that the
  install worked
  ([GNU standard targets](https://www.gnu.org/software/automake/manual/html_node/Standard-Targets.html)).
  `cargo install`, `pipx install`, and `uv tool install` mean the same thing. Building a
  development venv is GitHub's
  "[bootstrap/setup](https://github.blog/engineering/scripts-to-rule-them-all/)" step,
  which is a different verb. A newcomer who types `just install` expects a working
  `sase` on `PATH`.
- **There is a real gap.** Nothing in the repo reliably answers "make my `sase` command
  run this checkout plus a matching core." It must work even when the current `sase` is
  broken, which is exactly when you reinstall. The chezmoi scripts exist because of this
  gap, and they are drifting.
- **Moving the venv recipe to a longer name costs little.** `_setup` already heals
  `.venv` on every `just check` or `just test`, so very few people need to type the venv
  install by hand.

### 2.2 What's wrong with it as specified

| #   | Problem                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Severity |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| P1  | **The meaning of a heavily used command flips.** Old hints keep circulating after the rename: chat transcripts, Rust triage strings pinned by `sase-core-revision.txt`, installed sase binaries that can't be patched, and agent habits. An agent following one runs a global PyPI reinstall. That replaces the editable install, can downgrade `sase-core-rs` below the bead store's format, and breaks every running agent and the scheduler, because they all import from the uv-tool venv. | High     |
| P2  | **`install-dev` from "this checkout"** in a `sase_<N>` workspace makes the global `sase` import from a directory that other agents reset, reuse, and check out to other commits.                                                                                                                                                                                                                                                                                                                                                                                                             | High     |
| P3  | **"The appropriate sase-core checkout" is undefined**: there are three meanings (§1.2), and the venv path today doesn't check the pin at all.                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Medium   |
| P4  | **A second engine duplicates `sase update --to dev\|pypi`.** If `just install-dev` and `sase update --to dev` produce different receipts, `sase update` and `sase plugin install` will mishandle whatever the other one built.                                                                                                                                                                                                                                                                                                                                                             | Medium   |
| P5  | **The repo family splits.** Plugin repos keep `just install` meaning venv, and sase-core triage prints one remedy string for every repo. A sase-only rename makes that remedy wrong somewhere.                                                                                                                                                                                                                                                                                                                                                                                              | Medium   |
| P6  | **A plain `uv tool install --force sase` drops your plugins** (uv's `--with` replaces the set), and **an unpublished editable plugin** such as `bugyi-chops`, if it is not on PyPI, fails resolution when switching to PyPI. A naive `just install` hits both.                                                                                                                                                                                                                                                                                                                           | Medium   |

### 2.3 Would I take a different approach?

I considered keeping `install` for the venv and adding `install-tool` / `install-tool-dev`
(option D below). That has zero migration risk, but it keeps the backwards name forever,
and a `-tool` suffix makes no sense to anyone who doesn't know uv's internals. With the
guardrails in §3, P1 becomes a loud, self-correcting refusal rather than a clobber. So I
**keep your naming** and adjust the requirements around it.

On `install-venv` itself: "venv" exposes an implementation detail, but it is accurate,
easy to grep, and matches the existing `rust-install VENV` and `venv_dir` vocabulary. The
alternatives are worse here:

- `setup` collides with the private `_setup`, which has a different contract (validate
  and heal versus force install).
- `sync` reads like `uv sync`, which these recipes don't run.
- `bootstrap` is vague.

Keep `install-venv`.

---

## 3. Requirement adjustments (called out explicitly)

| ID  | Adjustment                                                                                                                                                                                                                                                                                                                                                                                                                                              | Why                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| R1  | **Only humans run the global installers.** `just install` and `just install-dev` exit 2 when `SASE_AGENT` is set. The refusal names `just install-venv` (for repairing a workspace) and `/sase_gate` (for proposing a global reinstall the user asked for). An explicit `SASE_GLOBAL_INSTALL_BYPASS='<reason>'` escape hatch mirrors `SASE_TOOL_BYPASS`.                                                                                                                      | Fixes P1 for agents, the main source of stale hints. Fits "completion is host-owned".      |
| R2  | **Preview, then confirm.** Every global install renders its plan, including a loud row for any mode flip (dev → PyPI) or downgrade, and asks `[y/N]`. `-y` skips the prompt and `-n` previews only. Without a TTY and without `-y`, it fails closed.                                                                                                                                                                                                       | Fixes P1 for humans and CI: an old `just install` in CI fails instead of reinstalling.      |
| R3  | **`install-dev` requires a durable source.** It refuses when the checkout is under the managed workspace root (`workspace_provider/store.py::_default_state_root`, i.e. `~/.local/state/sase/workspaces`). The refusal prints a ready-to-run `just -f <durable>/Justfile install-dev`.                                                                                                                                                                         | Fixes P2.                                                                                   |
| R4  | **A sase-core checkout matches when its HEAD contains this sase checkout's `sase-core-revision.txt` pin** (the `sase update` rule). `--core pin` builds from an isolated worktree at exactly the pin, for CI parity or bisects. The installer **never silently falls back** to a published core. `--core pypi` is explicit and allowed only if the bindings check passes.                                                                                       | Fixes P3; keeps one rule across `sase update`, `just install-dev`, and CI.                 |
| R5  | **Build first, swap second, then verify.** The slow and fallible work (cargo or wheel-cache build, LSP build) finishes before the uv-tool env changes. After the swap: `sase core health`, the bindings check, and a probe showing `sase update` still recognizes the install. Failures print the exact restore command.                                                                                                                                       | Reliability: the old install stays intact until a known-good build exists.                  |
| R6  | **The receipt decides the plugin set**, as it does for `sase update` and `sase plugin`. Dev mode makes each plugin editable when a sibling checkout exists; otherwise the plugin stays on PyPI. PyPI mode keeps unpublished plugins editable and says so. `--with NAME` adds plugins.                                                                                                                                                                          | Fixes P6; matches what users already expect.                                                |
| R7  | **One venv implementation.** A private `_install-venv EXTRAS` replaces the three copied recipes and fixes the `required-plugins` and `Cargo.toml` drift.                                                                                                                                                                                                                                                                                                       | Beauty and reliability.                                                                    |
| R8  | **Runtime remedies depend on context.** One helper chooses `sase update` / `just install-dev` / `just install-venv` based on how the running sase is installed. sase already has the facts it needs (`uv_tool.detect`, `VersionPackageRecord.install_type`).                                                                                                                                                                                                  | Fixes the doctor and core-hint false advice in §1.3.                                       |
| R9  | **Family-wide `install-venv`.** Plugin repos rename too and keep `install` as a hidden alias for a while. The sase-core triage remedies switch to `just install-venv`, and the bead-event message switches to `sase update`.                                                                                                                                                                                                                                    | Fixes P5.                                                                                   |
| —   | **No time-boxed "tombstone" period is needed** once R1 and R2 ship. Phase 1 below still uses a short tombstone, only because it lands before the global installers exist.                                                                                                                                                                                                                                                                                 | Simpler.                                                                                    |
| —   | **Non-goals:** `just uninstall` (`uv tool uninstall sase` is one line, and INSTALL.md covers it); a JSON mode (`sase update -j` already exists).                                                                                                                                                                                                                                                                                                             | Scope.                                                                                      |

---

## 4. Design options

| Option                                                                                                  | Intuitive                                                         | Reliable                                                                                                                                                                       | Beautiful                                                                    | Cost  |
| ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ----- |
| **A. Pure Justfile shell** (port the chezmoi script into recipes)                                       | ✓                                                                 | ✗ Hard to test. Shell with `\` line continuations has already drifted three ways in this file.                                                                                 | ✗ 300 lines of `printf`                                                       | M     |
| **B. Thin recipes → standalone `tools/sase_install`** (stdlib + optional `rich`, run with `uv run --no-project --python 3.12`) | ✓                                              | ✓ Unit-testable. No dependency on the `sase` it replaces. Hermetic integration tests through `UV_TOOL_DIR` / `UV_TOOL_BIN_DIR`.                                                | ✓ Can match `sase update`'s timeline                                          | M/L   |
| **C. Thin recipes → `sase update --to …`**                                                              | ✓                                                                 | ✗ Needs a working installed sase (it fails exactly when you need a reinstall). A no-op when already in the target mode. Uses `dev_root`, not this checkout. Behavior depends on the installed version. | ✓ (already pretty)                                                            | S     |
| **D. No rename: `install-tool`, `install-tool-dev`**                                                    | ✗ Backwards default; "tool" is uv jargon                          | ✓ Zero migration risk                                                                                                                                                          | ~                                                                            | S/M   |
| **E. One recipe, `just install [pypi\|dev]`**                                                           | ~ `just install dev` reads well                                   | ✓                                                                                                                                                                              | ~ Hides `dev` from `just --list` and from tab completion of recipe names      | M     |

**Choose B.** Notes:

- The tool can't simply `import sase.uv_tool` from `src/`. I tried it:
  `sase.uv_tool/__init__` pulls in `rich`, and `receipt` pulls in `sase.config`, which
  needs `yaml` and much more. So the installer gets its own small receipt reader (stdlib
  `tomllib`) plus a **parity test**. The test asserts that the installer's `uv` argv
  matches `sase.uv_tool.commands.build_reinstall_set()` for fixture receipts, so the two
  engines can't drift (P4).
- It reuses existing stdlib tools as subprocesses: `tools/sase_core_wheel_cache`,
  `tools/_sase_core_source_identity.py`, and `tools/check_sase_core_rs_bindings`.
- The Rust-core boundary rule doesn't apply. This is host bootstrap tooling that must run
  _without_ sase-core installed, not shared domain behavior.

---

## 5. Recommended design in detail

### 5.1 The recipe surface

`just --list` already prints `install  # distribution instead.`, because `just` shows only
the last comment line. `[doc]` fixes that. `[group]` collects the install recipes into
their own section:

```text
    [install]
    install *args                     # Install the latest sase release from PyPI as your `sase` command
    install-dev *args                 # Install this checkout + a pin-matched sase-core build as your `sase` command
    install-venv                      # Install this checkout into ./.venv for tests, lint, and benchmarks
    install-venv-terminal-smoke       # install-venv + real-terminal smoke-test deps
    install-venv-visual               # install-venv + visual-snapshot test deps
```

(I prototyped this with just 1.58; the output matches.)

```just
# ── Install ─────────────────────────────────────────────────────────────
# `install` / `install-dev` own your global `sase` (the uv-tool env);
# `install-venv*` own this checkout's ./.venv. See docs/development.md#installing.
sase_install := "uv run --no-project --quiet --python 3.12 " + justfile_directory() / "tools/sase_install"

[group('install')]
[doc('Install the latest sase release from PyPI as your `sase` command')]
[positional-arguments]
install *args:
    @{{ sase_install }} pypi "$@"

[group('install')]
[doc('Install this checkout + a pin-matched sase-core build as your `sase` command')]
[positional-arguments]
install-dev *args:
    @{{ sase_install }} dev --sase-core-dir "{{ sase_core_dir }}" "$@"

[group('install')]
[doc('Install this checkout into ./.venv for tests, lint, and benchmarks')]
install-venv: (_install-venv "dev")

[group('install')]
[doc('install-venv + visual-snapshot test deps')]
install-venv-visual: (_install-venv "dev,visual")

[group('install')]
[doc('install-venv + real-terminal smoke-test deps')]
install-venv-terminal-smoke: (_install-venv "dev,terminal-smoke")
```

Constraints that shape this:

- **CI pins `just` 1.50.0** in `.github/actions/setup-sase/action.yml`. Any newer syntax
  anywhere in the Justfile makes _every_ CI recipe fail to parse. That rules out
  `[arg(flag)]` (just 1.53), which boolean flags like `-y` would need. `[arg(long)]`
  (1.46) would parse, but it only covers options that take values. `[group]` (1.27),
  `[doc]`, and `[positional-arguments]` are all safe. Flags therefore go through `*args`
  to the tool's argparse, the same pattern as `demos *args` with `-y` today.
- **`sase_core_dir` is passed in from the Justfile**, so its env-var and
  linked-or-sibling resolution stays the single source of truth.
- **`rust-install-uv-tool` and `rust-dev-install-uv-tool` keep their names**, because
  installed sase versions call them.

### 5.2 Semantics and flags

|                   | `just install`                                                                                                                       | `just install-dev`                                                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Result            | `~/.local/bin/sase` runs the **latest published** sase (or `--version X` for a rollback)                                              | `~/.local/bin/sase` runs **this checkout as it is on disk** (editable), with `sase-core-rs` + `sase-macro-lsp` built from a matching core                                                                                                                                       |
| Plugins           | Receipt set from PyPI; unpublished editable plugins stay editable (shown in the plan)                                                   | Receipt set; each one with a sibling checkout (`../<repo>`) becomes editable, the rest stay on PyPI                                                                                                                                                                                 |
| Fresh machine     | Works with only `uv` + `just` (fetches Python 3.12 if needed)                                                                          | Same, plus `git` + `cargo`. Offers to clone a missing `../sase-core` (shown in the plan)                                                                                                                                                                                            |
| Idempotent        | Already current → `✓ already installed`, nothing changes (`--force` to redo)                                                          | Same receipt + same core source identity (`.sase-core-rs-source.json` in the tool venv) → no-op (`--force` to redo)                                                                                                                                                              |
| Guards            | R1, R2                                                                                                                               | R1, R2, R3, R4. A dirty checkout is a **warning**, not an error: dev installs of working trees are legitimate                                                                                                                                                                      |
| Flags             | `-n/--dry-run`, `-y/--yes`, `-v/--verbose`, `--with PLUGIN`, `--version X`, `--force`                                                    | `-n`, `-y`, `-v`, `--with`, `--force`, `--core {checkout,pin,pypi}` (default `checkout`), `--sync`                                                                                                                                                                                  |

`--sync` reproduces the `acei` fatal sync gate. It fetches and fast-forwards (`--ff-only`)
the sase, core, and plugin checkouts, and aborts before touching anything if any of them
is dirty or diverged. That lets the chezmoi scripts become one-line wrappers or retire.
Without `--sync`, `install-dev` never pulls: pulling and reinstalling is
`sase update`'s job.

### 5.3 The pipeline (one engine, two modes)

```text
preflight ─► plan ─► confirm ─► build ─► lock ─► swap ─► reconcile ─► verify ─► restart ─► summary
   │           │                  │        │       │        │           │          │
   │           │                  │        │       │        │           │          └ only if it was running
   │           │                  │        │       │        │           └ core health · bindings · `sase update -n -j` recognizes the install
   │           │                  │        │       │        └ uv pip install cached core wheel + copy LSP (dev)
   │           │                  │        │       └ uv tool install --force --reinstall … --overrides (same argv as build_reinstall_set)
   │           │                  │        └ exclusive code-swap lock; blocking readers → abort; advisory runners → warn
   │           │                  └ dev: sase_core_wheel_cache store + LSP build (no env mutation yet)
   │           └ receipt read, mode detection, pin check, plugin sources, downgrade/flip warnings
   └ agent guard · workspace guard · uv/git/cargo present · Python ≥3.12 available
```

The mutation window is only **swap + reconcile**: a cached uv install plus a local wheel
install, a few seconds. A cargo failure happens before the uv-tool env changes.
`mode_switch_backup.json`-style restore metadata is written before the swap, and the
failure panel prints the exact `uv tool install …` that restores the previous receipt.

**Why not hand the core wheel to `uv tool install --with <wheel>`?** It would make the
swap atomic, but it records a cache path in `uv-receipt.toml`. When the cache is pruned,
every later `sase update` or `sase plugin install` would fail while rebuilding from the
receipt. Mode-switch already avoids this by overriding the version window and then
replacing the wheel. The installer should do the same, for receipt parity (P4).

### 5.4 Core resolution (R4)

```text
pin  := <this checkout>/sase-core-revision.txt               (working tree; 40-hex)
core := --sase-core-dir (Justfile resolution)                 (--core checkout, default)
        | isolated `git worktree add --detach` at pin         (--core pin; cached per SHA)
1. core missing            → plan row "clone sase-org/sase-core → ../sase-core" (confirmed with the rest)
2. pin object missing      → git fetch; still missing → ✗ "pin not on the core remote"
3. pin ⊄ HEAD, clean+behind → plan row "fast-forward sase-core <a> → <b>" (existing _refresh behavior)
4. pin ⊄ HEAD otherwise    → ✗ with two exact remedies (switch/pull, or --core pin)
5. pin ⊆ HEAD              → ✓ "sase-core e411a39 (pin e8606a5 + 1)"; dirty core → ⚠ but allowed
```

### 5.5 What it looks like

The visual language follows `sase update`: a rounded panel, `✓ ⠼ ○` step rows, and
append-only plain lines when stderr isn't a TTY. These are mockups: the versions, pids,
and timings in them are made up.

Plan and confirm for `just install-dev`:

```text
╭─ just install-dev · your `sase` → dev (editable) ──────────────────────────────╮
│ sase           ~/projects/github/sase-org/sase        master @ 0ac86ad · clean │
│ sase-core-rs   ~/projects/github/sase-org/sase-core   master @ e411a39         │
│                contains pin e8606a5 (sase-core-revision.txt) · +1 commit        │
│ plugins        sase-github ✎  sase-telegram ✎  sase-research-artifacts ✎       │
│                bugyi-chops ✎                         ✎ editable sibling checkout │
│ target         ~/.local/share/uv/tools/sase          currently: dev @ 0ac86ad   │
╰─────────────────────────────────────────────────────────────────────────────────╯
Install? [y/N]
```

Run:

```text
╭─ just install-dev ──────────────────────────────────────────────────╮
│ ✓ Preflight              uv 0.12.23 · cargo · pin ok          0.3s │
│ ✓ Build sase-core-rs     cache hit · e411a39                  0.1s │
│ ✓ Build sase-macro-lsp   cache hit                            0.1s │
│ ✓ Code-swap lock         1 agent runner warned                0.0s │
│ ✓ Install package set    uv tool · 5 editable · 0 managed     8.2s │
│ ✓ Install core + LSP     sase-core-rs 0.35.4 (local)          0.9s │
│ ✓ Verify                 core health ok · bindings ok         1.4s │
│ ✓ Restart scheduler      pid 41210 → 41388                    2.0s │
╰──────────────────────────────────────────────────────── 13.0s ─╯
✓ sase now runs dev @ 0ac86ad from ~/projects/github/sase-org/sase
  sase-core-rs built from sase-core e411a39 (pin e8606a5 + 1)
  Pull & reinstall: sase update   ·   Back to the release: just install
```

The mode flip that P1 is about, made visible:

```text
╭─ just install · your `sase` → PyPI ────────────────────────────────────────────╮
│ sase           dev 0.17.1.dev42+g0ac86ad  →  0.17.1   PyPI                      │
│ sase-core-rs   0.35.4 local build         →  0.35.3   PyPI   ⚠ downgrade        │
│ sase-github    dev (editable)             →  0.4.2    PyPI                      │
│ bugyi-chops    dev (editable)             →  stays editable · not on PyPI       │
│ ⚠ Replaces your editable install from ~/projects/github/sase-org/sase.          │
╰─────────────────────────────────────────────────────────────────────────────────╯
Install? [y/N]
```

Agent refusal (exit 2):

```text
✗ just install-dev won't run inside a SASE agent.
  It replaces the global `sase` that every agent and the scheduler run.
  • Repairing this workspace's test environment?   just install-venv
  • The user asked for a global reinstall?          propose it with /sase_gate
```

Workspace refusal (exit 2):

```text
✗ just install-dev: this checkout is a SASE-managed workspace
  (~/.local/state/sase/workspaces/sase-org/sase/sase_19). Agents reset and reuse
  it, so your global `sase` would change underneath you. Install from your
  durable checkout instead:
    just -f ~/projects/github/sase-org/sase/Justfile install-dev
```

Exit codes match `sase update`: `0` success or no-op, `1` failure, `2` refusal or usage,
`130` interrupted.

### 5.6 Relationship to `sase update`

- **Use `just install*` to bootstrap or repair.** It works when `sase` is missing or
  broken and installs from a known source.
- **Use `sase update` for day-to-day updates.** It pulls, reinstalls, and restarts from
  inside sase.
- **The handoff is checked mechanically.** After `just install-dev`, `sase update -n -j`
  must report `mode: dev`, and the installer's verify step runs that check. A parity test
  keeps the receipt shapes identical.
- **Later convergence (optional):** `sase update --to dev` already shells into the dev
  checkout to run `just rust-install-uv-tool`. It could run `just install-dev -y` there
  instead, leaving one engine that materializes a dev install.

---

## 6. Migration plan

**Phase 1: rename (sase, one PR, mostly mechanical).**

- `install*` → `install-venv*` through `_install-venv`. Add `[group('install')]` /
  `[doc]`. `just install` becomes a **temporary tombstone** that prints the split and
  exits 2 until Phase 2 replaces it.
- Update the `setup-sase` action (default and `case`), `ci.yml` / `telemetry.yml`
  (`install-venv-visual`), and the `sase.yml` catalog (`install` → `install-venv`). The
  `install` ToolRun duration history starts over under the new name, which is
  acceptable. Also fix the stale comment in `check.receipt`.
- Update `tests/test_justfile_sase_core_dir.py` (parametrized names),
  `tests/test_github_actions_setup_sase.py`, `tests/test_justfile_lint.py`, and the visual
  `renderer_env.py` message.
- Update the docs listed in §1.3. In INSTALL.md, add an "Installing from a checkout"
  section pointing at `just install-dev`.
- Implement R8 (context-aware remedies) for `core/rust.py`, the doctor checks,
  `_prepare_completion.py`, the query facades, and the `tools/*` messages.
- Memory, through `/sase_memory_write`:
  - `lint_and_test.md`: all 3 sites;
  - `symvision.md`: the Verify section;
  - generated skill source `src/sase/macros/skills/sase_monitor.md`, then regenerate and
    redeploy to chezmoi.
  - `decisions/guarded-recipes.md` is immutable. Its "`install` is never guarded" claim
    stays true of the venv recipe it meant. Add a **new** decision record instead (e.g.
    `global-install-is-human-only`) that records R1 and R2, the alternatives, and the
    condition that would reopen it.

**Phase 2: global installers (sase).** Build `tools/sase_install` with:

- unit tests for planning, pin rules, and guards;
- the receipt parity test;
- a slow hermetic integration test under temporary `UV_TOOL_DIR` / `UV_TOOL_BIN_DIR`
  (uv honors both, and so does `rust-install-uv-tool`, through `uv tool dir`).

This phase replaces the tombstone. Check whether `tools/pyscripts-260801` accepts a
PEP 723 header if the tool uses `rich`. Otherwise use a small stdlib ANSI renderer.

**Phase 3: cross-repo.**

- **sase-core:** triage remedies → `just install-venv`; the `bead/jsonl.rs` message →
  "`sase update` (or `just install-dev` from your sase checkout)". Bump the pin.
- **Plugin repos:** `install-venv` becomes the canonical name; keep `install` as a
  `[private]` alias for one release cycle; update CI and AGENTS.md.
- **chezmoi:** `acei` → `just -f ~/projects/github/sase-org/sase/Justfile install-dev --sync -y && sase tui --restart-axe`,
  or retire it. `aceii` becomes the same command, with `sase-google` / `sase-gchat`
  carried by the receipt. Remove the `~/.cargo/bin/sase-macro-lsp` copy so PyPI installs
  don't pick up a stale server.

**Later (optional).**

- Every SASE repo gets `just install-dev` = "make my global `sase` use _this_ checkout".
  For plugins, that means injecting the checkout as editable through the receipt.
- `sase update --to dev` delegates to it.

---

## 7. Risks and open questions

1. **Default `--core`:** containing the pin (my choice: it keeps your in-progress core
   work) or exactly the pin (CI parity)? If you prefer reproducibility, flip the default.
   The flag already exists either way.
2. **What `just install` installs on a fresh machine:** only `sase`, or also this
   project's `plugins.required` (`sase-github`, `sase-research-artifacts`)? I'd install
   only `sase` and print a hint, because `plugins.required` describes developing _this
   project_, not every user.
3. **How strict the workspace guard is:** refuse outright (recommended), or allow it with
   `--i-know`? Refusing is simpler and avoids an attractive footgun.
4. **`rich` dependency:** PEP 723 + `uv run --script` gives the nicest output for free.
   But tools here are stdlib-only by convention, and the first run needs network access
   to fetch `rich` (an install needs network anyway).
5. **Interrupted swap:** the code-swap lock covers `sase bead work` and warns about agent
   runners. A process that starts mid-swap can still import a torn tree, which is the
   residual race `sase update` already accepts. Restarting the scheduler afterwards
   handles long-lived services.

---

## 8. Recommended solution

**Adopt the naming:** `just install` (PyPI), `just install-dev` (this checkout plus a
matching sase-core), and `just install-venv` / `install-venv-visual` /
`install-venv-terminal-smoke`.

**Build it as thin `[group('install')]` / `[doc]` recipes over a standalone, tested
`tools/sase_install`, with these properties:**

1. **Agents can't run it** (exit 2 under `SASE_AGENT`, with an explicit bypass), and
   **every run previews and confirms** (`-n` / `-y`). Old `just install` habits then
   produce a helpful refusal instead of replacing your dev install.
2. **`install-dev` refuses to run from SASE-managed workspaces** and installs exactly the
   durable checkout it runs from.
3. **A sase-core checkout matches when its HEAD contains `sase-core-revision.txt`**, the
   same rule `sase update` uses. `--core pin` gives CI parity, and the installer never
   silently falls back to a published core.
4. **Build first, swap second, verify after:** the wheel and LSP come from the existing
   cache, the swap holds the code-swap lock, then core health, bindings, and a
   `sase update` recognition check run, and the scheduler restarts.
5. **The receipt decides the plugin set**, and a parity test ties it to
   `sase.uv_tool.commands`, so `just install*` and `sase update` stay interchangeable.
6. **Ship in phases:** the mechanical rename with a short-lived tombstone first, then the
   guarded installers, then the sase-core remedy strings, the plugin-repo renames, and
   retiring the chezmoi `install_sase_*` scripts.

Leave the `rust-*-uv-tool` recipe names alone, because installed sase versions call them.
Leave the immutable `guarded-recipes` decision unchanged, and record the new
human-only-global-install rule as its own decision.

---

### Sources

- Local evidence (read-only):
  - this repo: `Justfile`, `sase/sase.yml`, `.github/actions/setup-sase/action.yml`,
    `src/sase/mode_switch/`, `src/sase/dev_update/core_pin.py`, `src/sase/uv_tool/`,
    `INSTALL.md`, `docs/plugins.md`, `docs/rust_backend.md`, `docs/editor.md`;
  - linked repos opened with `sase repo open`: sase-core, sase-github, sase-telegram,
    sase-research-artifacts, chezmoi (`home/bin/executable_install_sase_github`,
    `home/dot_config/aliases.sh`);
  - `~/.local/share/uv/tools/sase/uv-receipt.toml`;
  - `just --changelog` (1.58.0).
- [GNU Automake: Standard Makefile Targets](https://www.gnu.org/software/automake/manual/html_node/Standard-Targets.html)
- [GitHub Engineering: Scripts to Rule Them All](https://github.blog/engineering/scripts-to-rule-them-all/)
- [uv docs: Tools concepts](https://docs-next.astral.sh/uv/concepts/tools) and
  [`uv tool install` CLI reference](https://www.mintlify.com/astral-sh/uv/cli/tool-install)
  (flags confirmed locally with `uv tool install --help`, uv 0.12.23)
