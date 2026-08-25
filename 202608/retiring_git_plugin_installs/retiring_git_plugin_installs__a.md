---
create_time: 2026-08-25
updated_time: 2026-08-25
status: research
---

# Retiring "From Git" SASE Plugin Installs

**Research question:** What would it take to remove support for `--git` ("from git")
SASE plugin installations, and can the `bugyi-chops` install on `athena` be migrated to
a dev/editable install instead?

**Scope:** `sase` at `2d908ca11` (version 0.16.0), the live `uv-receipt.toml` on
`athena`, and the `bbugyi200/bugyi-chops` repository at `22b3db5`. External checks
(PyPI, GitHub Actions) were made on 2026-08-25. This is architecture research, not an
implementation plan; no runtime behavior and no installed package was changed.

## Bottom line

Three conclusions, in order of how much they change the question.

1. **The premise is half right.** There is no third "dev install" *mode* for plugins.
   `sase plugin install` offers exactly two sources — index and git — and there is no
   flag that produces an editable plugin. Editable plugins exist only as a property of
   the **whole environment**, established by `sase update --to dev`, which converts
   every package at once. So "use option 2 instead" is not something a user can do for a
   single plugin today.

2. **`--git` is not why `bugyi-chops` is on git.** `bugyi-chops` is unpublished because
   its one PyPI release attempt failed on 2026-07-27 with `invalid-publisher` — a
   trusted-publisher configuration that was never created. The package is otherwise
   fully publishable. The git install is a workaround for a five-minute PyPI settings
   gap, not a design requirement.

3. **You cannot remove git support, only demote it.** The `uv-receipt.toml` is written
   by `uv`, not by SASE, and any `uv tool install sase --with git+…` run from outside
   SASE puts a git row in it. Every SASE mutation path (`install`, `uninstall`,
   `update`, both mode-switch legs) reconstructs the *entire* `--with` set from that
   receipt. If SASE stops understanding git rows it will silently drop or corrupt them.
   Git **tolerance** in `Requirement` and the receipt round-trip is permanent
   infrastructure; only the *promoted* `-g|--git` shortcut is removable.

**Recommendation (detail in §7):** fix the `bugyi-chops` PyPI publisher, add the missing
per-plugin editable install (`sase plugin install -e|--editable <path>`), then retire
`-g|--git` behind a `sunset` feature flag while keeping receipt-level git tolerance
forever. Migrate `athena` with `sase update --to dev`, which already resolves
`bugyi-chops` correctly — but read §5.4 first, because it makes `--to pypi` a one-way
door until `bugyi-chops` is published.

## 1. What the three "modes" actually are

### 1.1 Mode 1 — index (PyPI)

`sase plugin install github` resolves the name through the GitHub catalog and installs
the published distribution. `resolve_install_spec` →
`_spec_from_entry(entry, git=False)` builds `Requirement.from_spec(entry.repo)`, an
ordinary PEP 508 requirement (`src/sase/plugins/_operations_common.py:130`).

### 1.2 Mode 2 — git

`sase plugin install github -g` resolves the same catalog entry to
`Requirement.from_spec(f"git+{entry.url}")` and tags the resolution
`source="git"` (`src/sase/plugins/_operations_common.py:123`). The flag is defined at
`src/sase/main/parser_plugin.py:182`. In ACE, the same thing appears as a second variant
in the install confirm modal, labeled `from git`
(`src/sase/ace/tui/modals/plugins_browser_install.py:354`).

Crucially, `--git` is only a **catalog shortcut**. `_looks_like_raw_spec` already passes
any `git+…` URL through verbatim (`src/sase/plugins/_operations_common.py:136`), so
`sase plugin install git+https://github.com/bbugyi200/bugyi-chops` works with or without
the flag. Deleting `-g` removes a convenience, not a capability.

### 1.3 Mode 3 — editable is *not* a plugin install mode

There is no `-e`, `--editable`, or `--dev` on `sase plugin install`. Editable plugins
arise from exactly two places:

- **`sase update --to dev`** (`src/sase/mode_switch/plan.py:129`), which rewrites the
  *entire* package set — host, core, and every plugin — as editable checkouts under
  `update.dev_root` (default `~/projects/github/<owner>/<repo>`); or
- **a hand-run `uv tool install … --with-editable <path>`** outside SASE.

A local path passed to `sase plugin install` does **not** produce an editable install.
`Requirement.from_spec("/some/path")` sets `url=<path>`, and `with_args()` emits
`--with <path>` rather than `--with-editable <path>`
(`src/sase/uv_tool/receipt.py:78-82`). uv builds and installs a frozen wheel from that
directory. This is the single most misleading gap in the current surface: the command
that *looks* like a dev install silently isn't one.

**So the real inventory is two per-plugin sources plus one whole-environment mode.**
Removing `--git` without adding a per-plugin editable source would leave exactly one way
to install a plugin — from an index — and would strand every unpublished plugin.

## 2. Evidence from this machine

The live receipt at `~/.local/share/uv/tools/sase/uv-receipt.toml`:

| Package | Receipt source | PyPI | `direct_url.json` |
| --- | --- | --- | --- |
| `sase` | `editable = ~/projects/github/sase-org/sase` | 200 | `dir_info.editable` |
| `bugyi-chops` | `git = https://github.com/bbugyi200/bugyi-chops` | **404** | `vcs_info` @ `22b3db5` |
| `sase-research-artifacts` | `git = https://github.com/sase-org/sase-research-artifacts` | 200 | `vcs_info` @ `a045047` |
| `sase-github` | `editable = ~/projects/github/sase-org/sase-github` | 200 | `dir_info.editable` |
| `sase-telegram` | `editable = ~/projects/github/sase-org/sase-telegram` | 200 | `dir_info.editable` |

Two observations worth carrying forward:

- **`bugyi-chops` is not the only git install.** `sase-research-artifacts` is also on
  git, and it *is* published. Any migration that runs through
  `sase update --to dev` converts both.
- **Both git checkouts already exist locally** at
  `~/projects/github/bbugyi200/bugyi-chops` and
  `~/projects/github/sase-org/sase-research-artifacts`, at exactly the paths
  `repo_for_package()` resolves to. A dev switch would reuse rather than clone them.

`~/.sase/uv/editable-overrides.txt` already lists all five packages as `-e` lines,
including the two git ones, and is 15 minutes *newer* than the receipt. That file is
rewritten during **planning** (`write_editable_overrides` is called from
`plan_install`, `plan_mode_switch`, and `managed_update_argv`), so its content reflects
a dev-switch plan that was computed but not executed. It is harmless — every mutation
path rewrites the file from the current receipt before passing it to `uv --overrides` —
but it means the file is not a reliable record of installed state.

### 2.1 Why `bugyi-chops` is on git

`bugyi-chops` has a complete release pipeline: `hatchling` build backend, a
`publish.yml` triggered on `v*` tags, a tag-vs-version guard, and a sole dependency
(`toobig`) that *is* on PyPI. It was tagged `v0.3.1` on 2026-07-27. That run failed after
19 seconds:

```
Trusted publishing exchange failure:
* `invalid-publisher`: valid token, but no corresponding publisher
  (Publisher with matching claims was not found)
* workflow_ref: bbugyi200/bugyi-chops/.github/workflows/publish.yml@refs/tags/v0.3.1
* environment: pypi
```

No release was ever published, and the repository has since moved to `0.7.0` untagged.
The git install is a consequence of one missing PyPI *pending publisher* entry, not of
a deliberate preference for VCS installs.

## 3. What "from git" is load-bearing for today

Four things depend on git installs, only one of which is really about the `-g` flag.

**3.1 Unpublished and pre-release plugins.** This is the genuine use case. A plugin that
exists on GitHub but not on an index — a fork, a private plugin, a plugin between
releases, a plugin whose publish is broken (as here) — has no index to install from. The
catalog is built from the GitHub `sase--plugin` topic, so the catalog can list plugins
that are not installable from PyPI. Today `-g` is the answer.

**3.2 The ephemeral-checkout error messages.** `ephemeral_install_source_error` refuses
to install a plugin from a path inside the managed workspace store and points the user
at `sase plugin install --git <name>` as the durable alternative
(`src/sase/uv_tool/preflight.py:64`). `missing_local_requirements_error` gives the same
advice for a vanished local source (`src/sase/uv_tool/preflight.py:113`). Both messages
would have to be rewritten; both are exactly the case where a *durable editable path*
would be a better recommendation than git.

**3.3 The `--to pypi` return leg for unpublished plugins.** `_index_requirement_for`
looks for a non-editable receipt row for the package and returns it verbatim
(`src/sase/mode_switch/plan.py:496`). For `bugyi-chops` today that row is the git row, so
`--to pypi` keeps it on git and succeeds. See §5.4 for what happens after a dev switch.

**3.4 Receipt round-trip.** `Requirement.git` / `git_ref`, `requirement_argument()`'s
`git+{git}{@ref}` rendering, and `_requirement_from_table`'s `rev`/`tag`/`branch`
parsing are what let `install`, `uninstall`, `update`, and both mode-switch legs rebuild
a `--with` set without dropping a git-sourced plugin. This is not removable; see §4.2.

## 4. Blast radius of removal

### 4.1 Scope A — remove the promoted `-g|--git` path

This is the tractable scope. Roughly 25 source references and 8 test files.

| Area | File | What changes |
| --- | --- | --- |
| CLI | `src/sase/main/parser_plugin.py:181` | Delete the `-g/--git` argument; edit the `install` description and epilog |
| Resolution | `src/sase/plugins/_operations_common.py:18,57,123` | Drop the `git` parameter and the `_spec_from_entry` git branch; narrow `SpecSource` to `catalog \| passthrough` |
| Planning | `src/sase/plugins/_operations_install.py:114` | Drop `git=` from `plan_install` |
| CLI handler | `src/sase/plugins/cli_install.py:87` | Drop `args.git`; `source` disappears from the JSON payload's git value |
| ACE | `src/sase/ace/tui/modals/plugins_browser_install.py:62,87,354-365,428` | Delete `InstallPreview.git_plan`, the second modal variant, and the `--git` argv append |
| Preflight copy | `src/sase/uv_tool/preflight.py:64,113` | Rewrite both actionable messages |
| Docs | `docs/plugins.md:404-460`, `INSTALL.md` | Remove the `-g` examples and the name-resolution paragraph |
| Completions | `tests/completion/snapshots/cli_spec.json` | Regenerate |
| Tests | `tests/test_plugin_operations_resolve.py`, `tests/test_plugin_cli_install.py`, `tests/test_plugin_operations_install.py`, `tests/ace/tui/test_plugin_action_confirm_modal.py`, `tests/ace/tui/test_plugins_browser_pane_install.py`, `tests/ace/tui/visual/test_ace_png_snapshots_config_center_plugin_actions.py` | Delete git-variant cases; re-approve PNG goldens |

Nothing cascades into dead code. The multi-variant machinery in
`PluginActionConfirmModal` stays live because `mixed`-mode `sase update -t` still offers
two variants (`plugins_browser_mode_switch.py:50`).

### 4.2 Scope B — remove git *understanding* (do not do this)

Deleting `Requirement.git`/`git_ref`, the `git+` branch of `requirement_argument()`, the
`LatestSource = "git"` member, and the `git+` case in `_looks_like_raw_spec` would break
any environment whose receipt already contains a git row — including `athena` right now.
SASE does not own the receipt. A user running
`uv tool install sase --with git+https://…` creates a git row that SASE must faithfully
re-emit on the next `sase plugin install`, or that plugin is silently uninstalled.
**Git tolerance in the receipt layer is permanent.** Only the promoted UI is removable.

## 5. Defects found while researching

These are pre-existing, independent of any removal decision, and each is worth a task
bead.

### 5.1 Git installs are misclassified as index installs

`_source_for_entry` short-circuits on the runtime inventory record before consulting
PEP 610 metadata (`src/sase/plugins/latest.py:536`):

```python
if record is not None:
    if record.install_type == "editable":
        return "editable"
    if record.install_type == "wheel":
        return "index"
return installed_source_fn(key)
```

`uv` builds a wheel from a git checkout, so a git-installed plugin that contributes
`sase_*` entry points has `install_type == "wheel"` and never reaches the `vcs_info`
check. Verified live: `sase-research-artifacts` is `git` in the receipt and has
`vcs_info` in `direct_url.json`, yet the inventory reports `install_type=wheel` and
`sase plugin list` renders it as `v0.2.0` compared against PyPI. `bugyi-chops` escapes
only because it contributes no `sase_*` entry point, so it has no inventory record and
falls through to `installed_source` → `"git"`.

The consequence is a wrong-direction update prompt: when PyPI moves ahead of the pinned
git commit, SASE shows `↑ update available` and recommends
`sase plugin update research-artifacts`, which re-resolves *from git* and never clears
the arrow. When git HEAD moves ahead of PyPI, SASE reports "up to date" for a stale
install. The fix is to consult `installed_source_fn` before the `wheel` short-circuit,
or to make the inventory carry a `git` install type.

### 5.2 Git installs get no update comparison at all

When classification does work, `enrich_with_latest` returns
`LatestInfo(source="git", error="non-index install")`
(`src/sase/plugins/latest.py:248`), rendered as `not compared · git install`
(`src/sase/plugins/render_catalog.py:431`). SASE never fetches the upstream ref for a
git-installed plugin, even though `sase.version._git.classify_git_upstream` — the exact
machinery used for editable checkouts — could answer the question against a
`git ls-remote`. Git installs are the only source with no freshness signal whatsoever.
This is the strongest functional argument that git installs are a second-class mode.

### 5.3 No per-plugin editable install

Covered in §1.3. `sase plugin install <path>` produces a frozen wheel copy that looks
like a dev install, drifts silently from the checkout, and is not reported as `editable`
anywhere.

### 5.4 `--to pypi` becomes a one-way door for unpublished plugins

After a dev switch, `_plan_to_dev` records `Requirement(name=…, editable=<path>)` and
discards the original git source (`src/sase/mode_switch/plan.py:237`). The receipt then
has no non-editable row for that package, so on the way back
`_index_requirement_for` falls through to its constructor branch, where
`url=requirement.url if requirement.editable is None else None` yields `None` and
`git` is `None` (`src/sase/mode_switch/plan.py:505-512`). The result is a bare
`bugyi-chops` requirement, which uv cannot resolve — PyPI returns 404.

Because `--to pypi` builds **one** `uv tool install --force --reinstall` command for the
whole package set, that single unresolvable requirement fails the switch for the entire
environment. **Migrating `bugyi-chops` to editable therefore disables
`sase update --to pypi` on this machine until `bugyi-chops` is published.** The
mode-switch backup (`~/.sase/update/mode_switch_backup.json` plus `restore_command`)
still lets you rebuild the previous set by hand, so this is recoverable, not
catastrophic — but it is a real, undocumented trap and the reason §7 puts the PyPI fix
first.

## 6. Options considered

| # | Option | Verdict |
| --- | --- | --- |
| 1 | Delete `-g|--git` outright, now | **No.** Strands unpublished plugins; breaks two preflight messages; violates the project's sunset-flag policy for a deprecation whose old branch must stay reachable. |
| 2 | Keep `-g` forever, do nothing | **No.** Git installs have no freshness signal (§5.2), are misclassified (§5.1), and duplicate a job editable installs do better. |
| 3 | Delete `-g` but keep `git+` passthrough | Cosmetic only. The catalog shortcut disappears; users type the URL. Does not fix §5.1/§5.2 and does not give unpublished plugins a supported home. |
| 4 | Replace `-g` with a per-plugin editable install, retire `-g` behind a sunset flag, keep receipt tolerance | **Yes.** Closes the real gap (§1.3), gives unpublished plugins a first-class path, and leaves the receipt layer honest. |
| 5 | Make git installs first-class (compare against `git ls-remote`, fix classification) | Only if you decide unpublished plugins should stay on git long-term. Strictly more work than option 4 and preserves the mode you want to remove. |

## 7. Recommendation

### 7.1 Immediately, for `athena` — do these in order

**Step 1: fix the `bugyi-chops` PyPI publisher.** On PyPI, add a *pending publisher* for
project `bugyi-chops`, owner `bbugyi200`, repository `bugyi-chops`, workflow
`publish.yml`, environment `pypi`. Then tag `v0.7.0` and let `publish.yml` run. This is
worth doing regardless of what happens to `--git`, and it is what makes step 3 safely
reversible (§5.4).

**Step 2: verify the plan.**

```bash
sase update --to dev --dry-run
```

`repo_for_package` was checked live and resolves all five packages correctly, including
`bugyi-chops` → `bbugyi200/bugyi-chops` at `~/projects/github/bbugyi200/bugyi-chops`.
Both git checkouts already exist at those paths, so the plan should read `reuse`, not
`clone`. Confirm that before proceeding.

**Step 3: switch.**

```bash
sase update --to dev
```

This converts **all four plugins plus the host and core** to editable, not just
`bugyi-chops` — `sase update -t` has no per-package granularity. On this machine that
means `sase-research-artifacts` also moves to its existing checkout, which is almost
certainly what you want on a dev host, but it is a side effect to accept deliberately.
The switch also runs `just rust-install-uv-tool` to rebuild `sase-core-rs`, so budget
several minutes.

If you want `bugyi-chops` *alone* on editable without touching the other three, there is
no supported command; the manual equivalent is a full
`uv tool install --force --reinstall --editable <sase> --with-editable …` reconstructed
from the receipt, which is exactly what §7.2's new flag should automate. Prefer waiting
for the flag over hand-running uv.

### 7.2 In `sase` — the change that makes removal defensible

**Slice 1 — add the missing mode.** Add `-e|--editable <path>` to
`sase plugin install`, resolving to `Requirement(name=…, editable=<abspath>)`, reusing
`ephemeral_install_source_error` to reject workspace-local paths, and adding an
`editable` member to `SpecSource`. This is a small change — `Requirement.with_args()`
already emits `--with-editable`, and `write_editable_overrides` already picks up
editable rows. Per the CLI rules, keep the option optional with a short alias and keep
the subcommand's options sorted. Also make a bare local path (§1.3) either error with a
pointer to `-e`, or install editable — the current silent frozen-copy behavior is a
trap either way.

**Slice 2 — fix the classification defect (§5.1)** so git installs stop being compared
against PyPI. This is a genuine correctness bug and should land independently of any
deprecation.

**Slice 3 — retire `-g` behind a `sunset` flag.** Per the flags memory, a deprecation
whose old branch must stay reachable is exactly a `sunset` flag (default **on**). Create
it with `sase flag new` — never by hand:

```bash
sase flag new plugin_git_install_source -k sunset \
  --when-enabled  "`sase plugin install -g` resolves a catalog entry to git+<repo url>." \
  --when-disabled "`-g` is rejected with a pointer to `-e|--editable` or an explicit git+ URL." \
  --remove-when   "No SASE-managed environment resolves a plugin through the -g shortcut, and every catalog plugin is either published to an index or installable editable."
```

With the flag off, `-g` errors with a message naming both replacements. Both branches
need tests, per policy. When the removal bead comes due, delete the Off branch and the
flag together.

**Slice 4 — never remove receipt tolerance.** `Requirement.git`, `git_ref`,
`requirement_argument()`'s `git+` rendering, `_requirement_from_table`'s
`rev`/`tag`/`branch` parsing, `_looks_like_raw_spec`'s `git+` case, and the
`LatestSource = "git"` member stay. Consider adding a decision record — the codebase
already carries `decisions:rust-core-required` and friends — stating that SASE tolerates
but does not promote VCS-sourced plugins, so a future agent does not "finish the job"
and break receipts SASE did not write.

**Slice 5 — rewrite the preflight copy (§3.2)** to recommend
`sase plugin install -e <durable path>` first and an explicit `git+` URL second, instead
of `--git`.

### 7.3 What would reopen this

- **A plugin that must never be published and must never have a local checkout** — a
  private plugin installed on a machine with no source tree — would justify keeping a
  promoted git path. Nothing on `athena` fits that description today.
- **`sase update -t` gaining per-package granularity** would make the "editable replaces
  git" story complete and could accelerate the flag's removal.
- **A catalog that starts listing many unpublished community plugins** would argue for
  option 5 (make git installs first-class) instead of option 4.

## Appendix A — commands used to verify

```bash
cat ~/.local/share/uv/tools/sase/uv-receipt.toml
cat ~/.local/share/uv/tools/sase/lib/python3*/site-packages/*.dist-info/direct_url.json
curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/bugyi-chops/json   # 404
gh run list --repo bbugyi200/bugyi-chops --workflow publish.yml
gh run view 30294883603 --repo bbugyi200/bugyi-chops --log-failed

/home/bryan/.local/share/uv/tools/sase/bin/python -c "
from sase.mode_switch.repos import repo_for_package, load_catalog_best_effort
cat = load_catalog_best_effort()
print(repo_for_package('bugyi-chops', catalog=cat))"
# RepoSpec(full_name='bbugyi200/bugyi-chops',
#          url='git@github.com:bbugyi200/bugyi-chops.git',
#          checkout_name='bugyi-chops')

/home/bryan/.local/share/uv/tools/sase/bin/python -c "
from sase.version.inventory import collect_runtime_version_inventory
for r in collect_runtime_version_inventory(include_plugins=True).packages:
    print(r.name, r.install_type)"
# sase-research-artifacts wheel   <- git install reported as wheel (see 5.1)
```

## Appendix B — unrelated observation

`~/projects/github/` contains a directory literally named
`git@github.com:bbugyi200/`, holding empty (`.git`-only) clones of `bugyi-chops`,
`sase`, and a defunct `sase-chop-telegram`, dated 2026-02-18 through 2026-07-18. The
`sase` one predates install-mode switching (introduced 2026-07-04 in `5131ec849`), so
these are not artifacts of `_checkout_path`, which has always used
`dev_root / owner / repo`. They appear to be leftovers from a `git clone <url> <url>`
mishap and are safe to delete. Noted only so a future reader does not mistake them for
dev checkouts.
