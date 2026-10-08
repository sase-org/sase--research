# Reliable `just install` (PyPI) and `just install-dev` (editable + matched sase-core): research & recommendation

Researcher: **mus** (independent swarm report; conclusions my own).

## Request in one paragraph

Today `just install` (plus `install-visual` / `install-terminal-smoke`) performs an
editable dev install into the repo-local `.venv`. The proposal: rename those to
`just install-venv*`, freeing the intuitive names `just install` (reliable PyPI/prod
install) and `just install-dev` (editable dev install including the matching sase-core
checkout) for new recipes. This report researches the current machinery, critiques the
plan, adjusts requirements where justified, and ends with a recommended solution.

## 1. What exists today

### 1.1 The three `install*` recipes (all target the repo `.venv`)

From `Justfile` (verified by reading the file, not from memory):

- `just install` — builds `sase_core_rs` from the configured sase-core checkout (or
  installs `$SASE_CORE_WHEEL`) when available, then
  `uv pip install --python .venv/bin/python --no-sources $(just _core-overrides-arg) -e ".[dev]"`,
  then installs `plugins.required` via `tools/setup_required_plugins`.
- `just install-visual` / `just install-terminal-smoke` — identical shape with
  `-e ".[dev,visual]"` / `-e ".[dev,terminal-smoke]"`.
- These are **force paths**: unconditional reinstall. The idempotent fast path used by
  every test/lint recipe is the private `_setup`, which validates via
  `tools/validate_test_environment` (fingerprinted on `pyproject.toml`, `uv.lock`,
  validators, core version, installed metadata) and only reinstalls/rebuilds on drift.

So the rename surface is exactly three public recipes plus their doc comments. Private
`_setup`, `_setup-visual`, `_setup-terminal-smoke`, `_setup-demos` need no renames.

### 1.2 The prod install path (already exists, just not under `just`)

- `INSTALL.md`: canonical prod install is `uv tool install sase` (managed tool env;
  required for `sase update` / plugin workflows), with `pip install sase` as an
  escape hatch. Post-install verification is `sase version`, `sase doctor`,
  `sase core health`.
- `smoke/pypi/` is a full PyPI smoke harness (Docker Compose) that installs both the
  `uv tool` flavor and the `uv pip` flavor with `SASE_SPEC`-style pins and asserts
  version inventory, job inventory, doctor health, and macro catalog. This is the
  reliability blueprint a new `just install` should copy, not reinvent.
- `sase update` / `sase update -t dev|pypi` (backed by `src/sase/mode_switch/`) already
  implements managed tool-env switching between PyPI wheels and editable checkouts,
  including editable-overrides wiring. A new `just install-dev` that targets the tool
  env would duplicate this unless it delegates to it.

### 1.3 The sase-core version-matching machinery

- `pyproject.toml` pins a `sase-core-rs>=X,<Y` window for wheel installs; editable
  installs pass a uv `--overrides` file lifting the window so the locally built
  extension is never downgraded.
- `sase-core-revision.txt` pins the exact sase-core revision CI builds from. The
  "appropriate sase-core checkout for that dev version" therefore has a well-defined
  answer: **the `sase-core-revision.txt` content at the requested sase revision**
  (falling back to the published `sase-core-rs` floor when no checkout/toolchain
  exists, or `$SASE_CORE_WHEEL` when supplied).
- Staleness guards already exist (`validate_sase_core_rs_version`, the
  `SASE_ALLOW_STALE_CORE=1` escape hatch, auto-fast-forward of clean checkouts); new
  recipes should reuse them verbatim.

## 2. Critique of the plan

**Verdict: the plan is a good idea and worth doing.** The bare word `install` doing an
editable dev install into a repo-local venv is genuinely surprising — every newcomer
reads it as "install sase (prod)". The rename makes the common thing easy and the dev
thing explicit. That said, I would adjust the requirements in four places (marked
**ADJUSTMENT** below), and there is one hard constraint the plan must respect.

### Hard constraint: the rename is a flag day for `install`, not a deprecation

`just` recipes occupy a single namespace. The new prod `just install` and the old dev
`just install` cannot coexist, so **no backward-compatible alias is possible for the
bare name** — old muscle memory (`just install` meaning "set up my dev venv") will
silently do something different after the change. This is the plan's main risk, and it
is borne mostly by agents/memory rather than humans: `sase/memory/lint_and_test.md`,
`sase/memory/symvision.md`, the `guarded-recipes` decision note, and a dozen docs
pages all say `just install` meaning the dev setup.

Mitigation (not elimination): do the rename atomically in one commit together with
every doc/memory/string update (§4), announce it in the release notes, and make the new
`just install` print an unmistakable banner (e.g. `[install] Installing sase <ver> from
PyPI into the uv tool environment`) so a misfiring invocation is instantly
recognizable. Do **not** try a transition period where `just install` warns — a recipe
must do one thing, and a warning-plus-prod-install still surprises.

### **ADJUSTMENT 1**: the variant renames CAN be soft-deprecated (unlike bare `install`)

`just` supports `alias` and wrapper recipes, and nothing else wants the names
`install-visual` / `install-terminal-smoke`. So: rename the bodies to
`install-venv-visual` / `install-venv-terminal-smoke`, and keep thin wrappers under the
old names that print a deprecation notice and forward, with removal scheduled (e.g.
two releases). This gives a graceful path everywhere one is possible, reserving the
flag day for the one name where it is unavoidable.

### **ADJUSTMENT 2**: `just install` (prod) must NOT target the repo `.venv`

The most important semantic decision in this design, and the one the request leaves
open: *install into what?* Installing a PyPI `sase` wheel into the repo's `.venv`
would divorce the venv from the working tree — `just check`/`just test` in that
checkout would then test the released code, not the checkout, which is a beautiful
footgun. The prod recipe should target the **uv tool environment** (`uv tool install
sase`), i.e. exactly what `INSTALL.md` tells users to do, with optional `--with`
plugins. Rationale: (a) it makes `just install` reproduce byte-for-byte what a user
gets, which is the point of "reliably install from PyPI"; (b) it keeps `.venv`
exclusively the contributor inner loop; (c) the smoke harness already validates this
exact shape. If someone truly wants a PyPI wheel in an isolated venv for testing,
that is `smoke/pypi`, not a new recipe — or a `just install-pypi-venv` escape hatch
added later on evidence of demand, not now.

### **ADJUSTMENT 3**: `just install-dev` should delegate, not reimplement

There are two plausible targets for `install-dev` and they want different
implementations:

1. **Tool-env dev** (`sase update --to dev` machinery in `src/sase/mode_switch/`):
   editable sase + editable plugins + rebuilt extension in `~/.local/share/uv/tools/sase`.
   The planning, overrides, and verification logic already exists and is tested — a
   just recipe here should be a thin, discoverable front door (`sase update -t dev`
   plus verification), not new shell.
2. **Checkout dev** (what `install-venv` already does): editable install of *this*
   checkout into `.venv` with the *linked/sibling* sase-core build. For the common
   case this needs no new recipe at all — it is the renamed `install-venv`.

The request's parenthetical ("needs to include the appropriate sase-core checkout for
that dev version") points at a third case: **installing a dev version of an arbitrary
sase ref** (e.g. "give me editable sase @ v0.16.x with its matching core"). That is
genuinely new functionality: resolve ref → read `sase-core-revision.txt` at that ref
→ materialize both checkouts under a dev root → editable-install + `rust-install` →
verify. It belongs behind `just install-dev [REF]` with the default (`REF` = current
checkout) degrading to case 2. Do not scope-creep case 1 into it; cross-link instead.

### **ADJUSTMENT 4**: keep new recipes OUT of the tool-run guard, and say so

The `guarded-recipes` decision explicitly leaves `install` unguarded (only
`check`/`check-full` are guarded). New `install`/`install-dev` recipes mutate the
user's tool environment — far outside any single checkout — so they must stay
unguarded too, and the decision note should gain one line recording that. An agent
running `just install` inside a verify monitor and upgrading the user's global sase
mid-run would be a spectacular failure mode; unguarded + documented + bannered is the
right combination. Relatedly: CI must never call the new `just install` (it mutates
the runner's tool env); CI's prod coverage stays `smoke/pypi` + `pypi-smoke`.

## 3. Proposed naming taxonomy (the "beautiful" part)

```text
just install [VERSION] [WITH="..."]   # prod: uv tool install sase[==VERSION] [--with ...]; then verify
just install-dev [REF="..."]          # dev: editable sase@REF + matched sase-core checkout; then verify
just install-venv                     # contributor inner loop: editable .[dev] into .venv (today's `install`)
just install-venv-visual              # today's `install-visual`
just install-venv-terminal-smoke      # today's `install-terminal-smoke`
```

Why this shape:

- The bare, obvious verb does the obvious thing (prod install — what `INSTALL.md`
  teaches). Suffixes specialize: `-dev` changes *what* is installed, `-venv` changes
  *where*.
- `install-venv*` reads as "set up my venv", which is exactly what those recipes do,
  and it groups them adjacently in `just --list` for discoverability.
- Parameters, not recipe explosion: `just install 0.17.0` / `just install-dev v0.16.0`
  beat `install-version-*` combinatorics. Keep the zero-arg forms as the blessed
  defaults (latest PyPI; current checkout).
- Every recipe gets the existing `_header` box treatment and `[install]`/`[install-dev]`/
  `[setup]` log prefixes, a preview of the exact `uv` command before mutation
  (mirroring the Admin Center Updates tab's "confirmation is the dry run" principle),
  and ends with the verification trio (`sase version`, `sase doctor`, `sase core health`).

## 4. Rename mechanics checklist (all in the one flag-day commit)

1. **Justfile**: rename the three recipe bodies; add deprecation wrappers for
   `install-visual` and `install-terminal-smoke` (NOT for bare `install` — impossible,
   §2); update the two error strings that say `Then rerun 'just install'`
   (in `_setup` and `rust-install`/`rust-dev-install`) to name `just install-venv`;
   write careful one-line doc comments (they are the `just --list` UX).
2. **Memory** (via the memory-write skill, per AGENTS.md): `lint_and_test.md`
   (command table line 12, the "run `just install` before `just check`" guidance,
   known-long-commands list), `symvision.md` ("run `just install` first"),
   `decisions/guarded-recipes.md` (record install recipes unguarded, incl. new ones).
3. **Docs**: `docs/development.md` (setup + verification tables), `CONTRIBUTING.md`,
   `README.md`, `docs/rust_backend.md` (source-workflow section), `docs/tool.md`,
   `docs/monitors.md`, `docs/perf_runbook.md`, `docs/mobile_mvp_runbook.md`;
   cross-link the new commands from `INSTALL.md`.
4. **Sweep**: `grep -rn "just install"` over `*.md`/`Justfile`/`tools/` to catch
   stragglers (prior research notes under `sase/repos/research/` are historical and
   should NOT be rewritten — only live docs).
5. **No changes needed**: `_setup` and friends (private names unchanged, so every
   `check`/`test`/`lint` dependency edge keeps working), `sase tool run` catalog,
   CI workflows (which use `_setup`-based lanes and `smoke/pypi`, never bare
   `just install` — verify this with a workflow grep in the implementing turn).

## 5. Reliability design notes for the two new recipes

- **`just install`**: shell out through the same steps as `smoke/pypi/entrypoint.sh`
  (`uv tool install --force --refresh sase[==VERSION] --python 3.12 [--with ...]`),
  honoring `SASE_SPEC`-style env pins; then run the smoke script's assertion subset
  that is cheap locally (version-inventory check, `sase doctor` no-ERROR,
  `sase core health`). Idempotent by construction (`--force`). Failure modes to
  handle explicitly: no-network (actionable message, nonzero exit), missing `uv`
  (point at INSTALL.md prerequisites), prebuilt-wheel gap on exotic platforms
  (the `cargo`-needed path INSTALL.md already documents).
- **`just install-dev`**: default (no REF) = `just install-venv` + Rust build +
  verification — i.e. a bannered alias, so the two can never drift. With REF:
  fresh worktree/clone of sase@REF under a dev root (never mutate a dirty checkout —
  refuse unless clean or `--force`), read `sase-core-revision.txt` at that REF,
  materialize sase-core at that pin (or `$SASE_CORE_WHEEL` when set), editable
  install + `rust-install` equivalent, then the same verification trio. Reuse
  `validate_sase_core_rs_version` and the staleness errors verbatim.
- **Testing the change itself**: the rename commit should run the `_setup`-based
  lanes (`just check`) to prove no dependency edge broke, plus a dry-run/preview
  invocation of each new recipe. Full `smoke/pypi` revalidation belongs to release
  CI, not the rename commit.

## 6. Alternatives considered

- **Don't rename; add `install-pypi` / `install-editable`.** Zero breakage, but it
  leaves the confusing bare `install` = dev-setup meaning in place forever and
  surrenders the intuitive names. Rejected: the confusion is the problem.
- **Put prod wheels into `.venv` (`install-venv-prod`).** Rejected per ADJUSTMENT 2 —
  a `.venv` that no longer reflects its checkout corrupts the contributor loop.
- **One mega `just setup` with flags.** Rejected: `just` recipes with `--to pypi|dev`
  flags duplicate the `sase update -t` interface inside a second grammar; two
  discoverable recipe names beat one parameterized one here, and `--list` readability
  matters for beauty.
- **Delete old variant names immediately (no wrappers).** Possible, but wrappers are
  ~3 lines each and the old names appear in docs/history; graceful-forward costs
  nothing. Adopt wrappers for variants only.

## 7. Recommended solution

**Approve the plan with the four adjustments above.** Concretely, implement in one
flag-day commit:

1. Rename `install` → `install-venv`, `install-visual` → `install-venv-visual`,
   `install-terminal-smoke` → `install-venv-terminal-smoke` (bodies unchanged), with
   deprecation wrappers for the two variants.
2. Add `just install [VERSION] [WITH]` targeting the **uv tool env** (prod PyPI +
   plugins + verification trio), implemented by factoring the `smoke/pypi` install
   steps into a shared script both call.
3. Add `just install-dev [REF]` where no-arg = bannered `install-venv` path and
   REF = materialize sase@REF + its `sase-core-revision.txt`-pinned core, editable
   install, verification trio; refuse dirty checkouts without `--force`.
4. Update all memory files, live docs, and Justfile-internal strings atomically (§4);
   leave historical research notes untouched; announce the flag day in release notes.
5. Record in `decisions/guarded-recipes.md` that the new install recipes stay
   unguarded, and keep CI on `smoke/pypi` (never the new `just install`).

The result: `just install` finally means what every newcomer thinks it means,
`just install-dev` makes matched-core dev installs reproducible instead of tribal
knowledge, and `just install-venv*` honestly names the contributor inner loop —
intuitive, reliable, and (with the `_header` banners, command previews, and
verification-trio finales) beautiful.
