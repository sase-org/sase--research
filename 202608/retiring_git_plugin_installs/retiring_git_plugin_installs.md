---
create_time: 2026-08-25
updated_time: 2026-08-25
status: research
---

# Retiring "From Git" SASE Plugin Installs

**Research question.** Why does SASE need a "from git" plugin install source when a
dev/editable install exists? What would it take to remove it, and can the `bugyi-chops`
install on `athena` be migrated to editable instead?

**Scope.** `sase` at `51f6369b3` (0.16.0); the live uv tool environment on `athena`;
`bbugyi200/bugyi-chops` at `22b3db5`; the original design plan
`plans/202606/sase_update_and_plugin_install.md`. External checks (PyPI, GitHub Actions)
made 2026-08-25. Architecture research only — nothing installed or changed.

This consolidates two prior reports, kept alongside as `…__a.md` and `…__b.md`. Every
claim below was re-verified against code or live state; where the two disagreed, §9
records the resolution.

---

## Bottom line

1. **The premise conflates two axes.** There is no per-plugin "dev mode." *Per plugin*
   there are exactly two sources: **index** and **git**. *Editable* is a property of the
   **whole environment** (`managed | dev | mixed`), set by `sase update --to dev|pypi`,
   which converts every package at once. So "just use option 2 instead" is not something
   a user can do for one plugin today — that command does not exist.

2. **`-g|--git` is a half-built feature, and that is the real answer to "why".** The
   original plan specified index-by-default with a git fallback *"for catalog plugins not
   published to an index"*, and `-g` merely to **force** it. The automatic fallback was
   never implemented — `_spec_from_entry` only checks the explicit boolean. So today an
   unpublished catalog plugin's default install simply fails at uv resolution, and `-g`
   is the manual workaround for a gap the design intended to close automatically.

3. **`-g` is not why `bugyi-chops` is on git.** It has exactly one publish attempt ever:
   tag `v0.3.1`, 2026-07-27, failed after 19s with `invalid-publisher` — a PyPI trusted
   publisher that was never created. Nobody retried; the repo is now at `0.7.0`, untagged.
   The git install is a workaround for a five-minute PyPI settings gap.

4. **You can remove the promoted `-g` UI; you cannot remove git *understanding*.** SASE
   does not write `uv-receipt.toml` — uv does. Anyone running
   `uv tool install sase --with git+…` by hand creates a git row that every SASE mutation
   path must faithfully re-emit, or that plugin is silently uninstalled on the next
   `sase plugin install`. Receipt-level git tolerance is permanent infrastructure, not a
   migration window.

5. **Migrating `bugyi-chops` to editable *today* is a net regression.** Two traps, both
   confirmed empirically (§5): `sase update` would silently stop updating it, and
   `sase update --to pypi` would fail for the entire environment. Neither is obvious
   from the UI.

**Recommendation (§8):** fix the `bugyi-chops` PyPI publisher first — it dissolves the
proximate problem, restores reversibility, and costs almost nothing. Treat `-g` removal
as an optional follow-on that must be *preceded* by three prerequisites, not led by them.

---

## 1. What the "three modes" actually are

Two independent axes, not one list of three:

**Axis 1 — per-plugin install source** (`sase plugin install`):

| Source | Receipt row | uv argv | Runtime | Freshness signal |
| --- | --- | --- | --- | --- |
| Index (default) | `{ name = "pkg" }` | `--with pkg` | built artifact copied in | PyPI compare |
| Git (`-g`, or `git+…` passthrough) | `{ name = "pkg", git = "…" }` | `--with git+…` | uv resolves a revision, builds it, copies the result in | **none** (§4.2) |

**Axis 2 — whole-environment install mode** (`sase update --to dev|pypi`):
`managed`, `dev`, `mixed`. Editable rows (`{ name, editable = "/path" }` →
`--with-editable /path`) exist only here. `sase update -t` has no per-package
granularity, and the ACE `m` action offers the same whole-environment targets.

Git and editable are not two spellings of one thing. Git is a **deployment** contract: a
built snapshot of a revision, no mutable source tree on the machine. Editable is a
**development** contract: imports resolve into a durable working tree, local edits are
live, and the checkout's cleanliness/ancestry become operational concerns
(`_checkout_warning` blocks or warns on detached, dirty, diverged, no-upstream, or
ahead-of-upstream checkouts).

### 1.1 The local-path trap

`sase plugin install /some/path` looks like a dev install and is not one.
`Requirement.from_spec("/some/path")` sets `url=<path>`, and `with_args()` emits
`--with <path>`, not `--with-editable` (`src/sase/uv_tool/receipt.py:76-82`). uv builds a
frozen wheel from that directory, which then drifts silently from the checkout and is
never reported as `editable`. This is the single most misleading behavior on the current
surface and should be fixed regardless of what happens to `-g`.

### 1.2 `-g` is a catalog shortcut, not a capability

`_looks_like_raw_spec` passes any `git+…` URL through verbatim
(`src/sase/plugins/_operations_common.py:136`), so
`sase plugin install git+https://github.com/bbugyi200/bugyi-chops` works with or without
the flag. **Deleting `-g` alone removes a convenience, not a capability.** Whether to
also reject raw `git+` specs at the SASE surface is a separate, larger decision (§6.2).

---

## 2. Why the third source exists

From `plans/202606/sase_update_and_plugin_install.md` (the epic that introduced
`sase plugin install`, landed 2026-06-25 in `e9d17424e`):

> `sase` and `sase-github` both resolve on PyPI (HTTP 200), so the default install source
> is the **distribution name** (PyPI), with a **git fallback** for catalog plugins not
> published to an index.

and, in the resolution algorithm:

> resolve through the catalog (`find_plugin`): found → spec is the **distribution name**;
> with `--git` **or when the entry is not on an index** → `git+<url>`.

That second clause — the automatic fallback — was never built. The catalog is assembled
from the GitHub `sase--plugin` topic, so it can and does list plugins with no index
release; for those, the default install path fails inside uv rather than falling back.

Beyond that intent, three things depend on git installs today:

- **Unpublished / pre-release / private plugins.** The genuine use case: a fork, a plugin
  between releases, a private repo with no index, or a plugin whose publish is broken.
- **The ephemeral-checkout escape hatch.** `ephemeral_install_source_error` refuses to
  install from a path inside the managed workspace store and points at
  `sase plugin install --git <name>` as the durable alternative
  (`src/sase/uv_tool/preflight.py:64`); `missing_local_requirements_error` gives the same
  advice for a vanished local source (`:113`). Both messages are exactly the case where a
  *durable editable path* would be the better recommendation.
- **The `--to pypi` return leg.** `_index_requirement_for` looks for a non-editable
  receipt row and returns it verbatim (`src/sase/mode_switch/plan.py:496`). For
  `bugyi-chops` today that row is the git row, so `--to pypi` currently succeeds. See §5.2
  for what changes after a dev switch.

---

## 3. Live state on `athena`

`~/.local/share/uv/tools/sase/uv-receipt.toml` plus PEP 610 metadata:

| Package | Receipt source | PyPI | `direct_url.json` | Inventory `install_type` |
| --- | --- | --- | --- | --- |
| `sase` 0.16.0 | `editable ~/projects/github/sase-org/sase` | 200 | `dir_info.editable` | `editable` |
| `sase-core-rs` 0.32.2 | (override) | — | `dir_info.editable` | `editable` |
| `bugyi-chops` 0.7.0 | `git …/bugyi-chops` | **404** | `vcs_info` @ `22b3db5` | **absent** |
| `sase-research-artifacts` 0.2.0 | `git …/sase-research-artifacts` | 200 (0.2.0) | `vcs_info` @ `a045047` | **`wheel`** |
| `sase-github` 0.2.6 | `editable …/sase-github` | 200 | `dir_info.editable` | `editable` |
| `sase-telegram` 0.4.9 | `editable …/sase-telegram` | 200 | `dir_info.editable` | `editable` |

Carry forward:

- **`bugyi-chops` is not the only git install.** `sase-research-artifacts` is also on
  git — and it *is* published, at exactly the installed version. Any `--to dev` run
  converts both.
- **Both git checkouts already exist locally** at `~/projects/github/bbugyi200/bugyi-chops`
  and `~/projects/github/sase-org/sase-research-artifacts`, which is where
  `repo_for_package` + `_checkout_path` resolve.
  `sase update --to dev --dry-run --json` plans **`reuse`** for all six packages,
  `git fetch` + `merge --ff-only` for each, and **zero warnings** — meaning every checkout
  is clean, attached, has an upstream, and is not ahead (`_checkout_warning`,
  `plan.py:461`). The resulting single uv command is:

  ```text
  uv tool install --color never --force --reinstall \
    --editable  …/sase-org/sase \
    --with-editable …/bbugyi200/bugyi-chops \
    --with-editable …/sase-org/sase-research-artifacts \
    --with-editable …/sase-org/sase-github \
    --with-editable …/sase-org/sase-telegram \
    --overrides ~/.sase/uv/editable-overrides.txt
  ```

- **`~/.sase/uv/editable-overrides.txt` is not a record of installed state.** It currently
  lists all five packages as `-e` lines and is 15 minutes newer than the receipt, because
  `write_editable_overrides` runs during *planning* (`plan_install`, `plan_mode_switch`,
  `managed_update_argv`). It reflects a plan that was computed and not executed. Harmless
  — every mutation path rewrites it from the current receipt — but do not read it as truth.

### 3.1 Why `bugyi-chops` is on git

`bugyi-chops` has a complete release pipeline: `hatchling`, a `publish.yml` triggered on
`v*` tags with a tag-vs-version guard and PyPI trusted publishing (`environment: pypi`,
`id-token: write`, `pypa/gh-action-pypi-publish`). Its sole runtime dependency (`toobig`)
is on PyPI. One run, ever:

```text
completed  failure  release bugyi-chops 0.3.1  Publish to PyPI  v0.3.1  19s  2026-07-27
  invalid-publisher: valid token, but no corresponding publisher
  workflow_ref: bbugyi200/bugyi-chops/.github/workflows/publish.yml@refs/tags/v0.3.1
  environment: pypi
```

Its README still says both "Install the published package… `sase plugin install
bugyi-chops`" and "`sase plugin install bugyi-chops -g`". Both are wrong today: there is
no published package, and `-g` is a VCS snapshot, not a development checkout.

---

## 4. Git installs are already second-class

This is the strongest argument for the user's instinct — stronger than "it duplicates
editable." SASE already treats git installs as a mode it does not really support.

### 4.1 Classification is wrong, and inconsistently so

`_source_for_entry` short-circuits on the runtime inventory record before consulting
PEP 610 metadata (`src/sase/plugins/latest.py:528`):

```python
if record is not None:
    if record.install_type == "editable":
        return "editable"
    if record.install_type == "wheel":
        return "index"
return installed_source_fn(key)   # ← the only branch that reads direct_url.json
```

uv builds a wheel from a git checkout, so any git-installed plugin that *has* an inventory
record is classified `index`. Verified live — two git installs, two different answers:

```text
research-artifacts   install_type: "wheel"   ← wrong; it is a git install
bugyi-chops          install_type: "git"     ← right, but only by accident
```

`bugyi-chops` escapes only because it contributes no `sase_*` entry point, so it has **no**
inventory record and falls through to `installed_source` → `vcs_info` → `"git"`. The same
heuristic that decides whether a plugin appears in the inventory silently decides whether
its source is classified correctly.

Consequence (latent today, because PyPI `sase-research-artifacts` is also 0.2.0): the
moment PyPI moves ahead of the pinned commit, SASE shows `↑ update available` and
recommends `sase plugin update research-artifacts`, which re-resolves **from git** and can
never clear the arrow. When git HEAD moves ahead of PyPI, SASE reports "up to date" for a
stale install. This is a plain correctness bug and should be fixed independently of any
deprecation.

### 4.2 Git installs get no freshness signal at all

When classification *does* work, `enrich_with_latest` returns
`LatestInfo(source="git", error="non-index install")` (`latest.py:248`), rendered as
`not compared · git install` (`render_catalog.py:431`) and `git` in the version column
(`:145`, `:400`, and `plugins_browser_rendering.py:329`). SASE never probes the upstream
ref. Note that the obvious building block does *not* fit as-is:
`sase.version._git.classify_git_upstream` takes a **local `source_root`**
(`_git.py:113`), and a git-installed plugin has no local checkout — a real fix would need
a new `git ls-remote` probe. Git is the only source with zero freshness signal.

### 4.3 SASE's own automated install paths never use git

Two paths that install plugins without a human typing the command hardcode the index:

- **Batch install** (marked-set install in ACE) calls
  `resolve_install_spec(catalog, query, git=False)` (`_operations_install.py:182`).
- **The `PluginsRequired` notification gate** — the chop that offers to install a
  project's missing `plugins.required` set — calls `plan_install(name)` with no `git`
  argument (`_required_gate_spec.py`, `_execute_install`).

So an unpublished plugin can never be satisfied by SASE's own repair path. If unpublished
plugins were meant to be a supported deployment shape, this is where it would show.

### 4.4 An unpinned git URL is not reproducible

`{ git = "https://github.com/bbugyi200/bugyi-chops" }` carries no `rev`/`tag`/`branch`.
The installed artifact is a snapshot, but the *specification* is not: the next
`--upgrade-package` re-resolves whatever the default branch points at. A commit-pinned git
URL would be reproducible; the `-g` convenience flag never produces one.

---

## 5. What migrating `bugyi-chops` to editable costs today

Both traps verified empirically against the live environment.

### 5.1 `sase update` would silently stop updating it

`dev_route_from_inventory` builds its work list by intersecting editable **receipt** rows
with editable **inventory** records, and drops anything missing from either side without a
warning (`src/sase/main/update_routing.py:65-88`) — the `UvToolError` fires only when the
intersection is *entirely* empty. Simulating a post-switch receipt against the live
inventory:

```text
DevRoute records routed for dev update:
   sase, sase-github, sase-telegram, sase-core-rs      ← bugyi-chops absent
```

`bugyi-chops` is absent from `collect_runtime_version_inventory` because plugin discovery
recognizes only a `sase_*` entry-point group, a `sase-*` distribution name, or a
`sase_chop_*` console script — and `bugyi-chops` deliberately has none of those (its
scripts are `bugyi_chop_ci_watch` and `bugyi_chop_toobig_split`). Making it editable does
not change any of those facts.

This gap has documented history: `plans/202607/fix_receipt_owned_plugin_detection.md`
(landed 2026-07-23, `ef2cc16`) fixed exactly this for the **catalog** side — that is why
`sase plugin list` shows `bugyi-chops` at all — and explicitly noted that "`sase version`
omits `bugyi-chops`" without fixing it. `tests/test_plugin_catalog_installed.py:119`
(`test_bugyi_chops_requires_receipt_membership`) is the canonical fixture for this shape.

After the switch the degradation is half-visible: `sase plugin list` would render
`editable install is missing from version inventory` (`latest.py:409`), while
`sase update` just quietly never fetches the checkout. Git installs do **not** have this
blind spot, because they operate from the receipt and let uv refresh the requirement.

### 5.2 `sase update --to pypi` becomes a one-way door

`_plan_to_dev` records `Requirement(name=…, editable=<path>)` and discards the original
git source (`plan.py:237`). On the way back, `_index_requirement_for` finds no
non-editable receipt row and falls into its constructor branch, where
`url=requirement.url if requirement.editable is None else None` yields `None` and `git` is
`None` (`plan.py:505-512`). Verified directly:

```text
_index_requirement_for(post_dev_receipt, bugyi-chops)
  → Requirement(name='bugyi-chops', git=None, url=None)
  → ['--with', 'bugyi-chops']       # PyPI → 404
```

Because `--to pypi` builds **one** `uv tool install --force --reinstall` for the whole
package set, that single unresolvable requirement fails the switch for *every* package.
So converting `bugyi-chops` to editable disables `sase update --to pypi` on this machine
until `bugyi-chops` is published. `~/.sase/update/mode_switch_backup.json` plus its
`restore_command` make this recoverable by hand, not catastrophic — but it is real,
undocumented, and the main reason §8 puts the PyPI fix first.

### 5.3 There is no per-plugin granularity

`sase update --to dev` converts **all six** packages, fetches and fast-forwards every
checkout, reinstalls the whole uv environment, and rebuilds the Rust core. There is no
supported "replace just this plugin's receipt row with an editable path." Reconstructing
that by hand with raw `uv tool install --force --reinstall …` is possible but is exactly
the operation a new command should own.

---

## 6. Blast radius of removal

### 6.1 Scope A — remove the promoted `-g|--git` path

Tractable: roughly 25 source references and ~8 test files.

| Area | File | Change |
| --- | --- | --- |
| CLI | `main/parser_plugin.py:152,164,181-186` | Delete `-g/--git`; edit the `install` description and epilog example |
| Resolution | `plugins/_operations_common.py:18,57,123-131` | Drop the `git` parameter and the `_spec_from_entry` git branch; narrow `SpecSource` to `catalog \| passthrough` |
| Planning | `plugins/_operations_install.py:114` (`:182` already `git=False`) | Drop `git=` from `plan_install` |
| CLI handler | `plugins/cli_install.py` | Drop `args.git`; `source` loses its `git` value in the JSON payload |
| ACE | `ace/tui/modals/plugins_browser_install.py:53,62,87-95,316,340,354-365,427-428` | Delete `InstallPreview.git_plan`, the second modal variant, and the `--git` argv append |
| Rendering | `plugins/render_catalog.py:145,400,431`; `ace/tui/modals/plugins_browser_rendering.py:329` | Keep or retire the `source == "git"` branches — see 6.2 |
| Preflight copy | `uv_tool/preflight.py:64,113` | Rewrite both actionable messages |
| Docs | `docs/plugins.md:404-460`; `INSTALL.md` | Remove `-g` examples and the name-resolution sentence |
| Completions | `tests/completion/snapshots/cli_spec.json` | Regenerate |
| Tests | `test_plugin_operations_resolve.py`, `test_plugin_cli_install.py`, `test_plugin_operations_install.py`, `ace/tui/test_plugin_action_confirm_modal.py`, `ace/tui/test_plugins_browser_pane_install.py`, `ace/tui/_plugins_browser_pane_helpers.py`, `uv_tool/test_preflight.py`, `ace/tui/visual/test_ace_png_snapshots_config_center_plugin_actions.py` | Delete git-variant cases; re-approve PNG goldens |

Nothing cascades into dead code. `PluginActionConfirmModal`'s multi-variant machinery stays
live because `mixed`-mode `sase update -t` still offers two variants
(`plugins_browser_mode_switch.py:46-50`).

### 6.2 Scope B — do **not** remove git understanding

`Requirement.git` / `git_ref`, `requirement_argument()`'s `git+{git}{@ref}` rendering,
`_requirement_from_table`'s `rev`/`tag`/`branch` parsing, `_looks_like_raw_spec`'s `git+`
case, and the `LatestSource = "git"` member are what let `install`, `uninstall`, `update`,
and both mode-switch legs rebuild a `--with` set without dropping a git-sourced plugin.
Deleting them breaks any receipt that already contains a git row — including `athena`'s,
right now.

Keeping the `source == "git"` *rendering* branches costs nothing and is what makes a
legacy git row legible rather than mysterious. Retiring them is the last thing to consider,
not the first.

---

## 7. Options considered

| # | Option | Verdict |
| --- | --- | --- |
| 1 | Delete `-g` outright, now | **No.** Strands unpublished plugins, breaks two preflight messages, and ships a deprecation with no reachable replacement. |
| 2 | Keep `-g` forever, change nothing | **No.** Git installs are misclassified (§4.1), have no freshness signal (§4.2), aren't reproducible (§4.4), and SASE's own automated paths already refuse to use them (§4.3). |
| 3 | Delete `-g`, keep `git+` passthrough | Cosmetic on its own. Fine as the *final* step of a sequence; useless as the first. |
| 4 | Fix the prerequisites, add a per-plugin source switch, then retire `-g` behind a `sunset` flag, keeping receipt tolerance forever | **Yes.** §8. |
| 5 | Make git installs first-class (remote `ls-remote` compare, fixed classification, commit pinning) | Only if you decide unpublished/private plugins should stay on git long-term. Strictly more work than 4 and preserves the mode you want gone. |

---

## 8. Recommendation

The proximate cause of the whole question is one missing PyPI setting. Fix that first; the
removal is optional and must *follow* its prerequisites.

### 8.1 On `athena`, in order

**Step 1 — publish `bugyi-chops`.** On PyPI, add a pending publisher for project
`bugyi-chops`: owner `bbugyi200`, repository `bugyi-chops`, workflow `publish.yml`,
environment `pypi`. Then tag `v0.7.0` and let `publish.yml` run. This is worth doing
regardless of what happens to `-g`, and it is what makes anything later reversible (§5.2).
Fix the README while you are there — it currently documents both an install that does not
work and `-g` as "development."

**Step 2 — move both git rows to the index.** Note that `sase plugin install <name>` on an
already-injected plugin is an idempotent no-op, and `sase plugin update` re-resolves the
*existing* receipt row (`with_upgraded` preserves the git source). Neither switches source.
The supported sequence is uninstall then install:

```bash
sase plugin uninstall sase-research-artifacts -n   # preview first
sase plugin uninstall sase-research-artifacts && sase plugin install research-artifacts
# after step 1 succeeds:
sase plugin uninstall bugyi-chops && sase plugin install bugyi-chops
```

`sase-research-artifacts` is already on PyPI at exactly the installed version (0.2.0), so
that half can be done today — and it also fixes its misclassification (§4.1).

**Step 3 — decide about editable deliberately, not as a bug fix.** `athena` is your dev
box, so wanting these checkouts editable is legitimate. But do **not** reach for
`sase update --to dev` as the way to "fix" `bugyi-chops`:

- it converts all six packages, not one;
- `sase update` will then silently never fetch the `bugyi-chops` checkout (§5.1);
- `--to pypi` will fail for the whole environment until `bugyi-chops` is published (§5.2).

If you do it anyway, do it *after* step 1, and know that `sase plugin list` will show
`editable install is missing from version inventory` for `bugyi-chops` until §8.2's
prerequisite lands.

### 8.2 In `sase`, sequenced — each step is independently valuable

1. **Fix `_source_for_entry`** so PEP 610 metadata is consulted before the `wheel`
   short-circuit (or give the inventory a `git` install type). Pure correctness bug; land
   it alone, ahead of everything else.
2. **Make receipt-owned packages first-class in `collect_runtime_version_inventory`.**
   Every explicitly injected receipt requirement deserves a `VersionPackageRecord` even
   without a `sase_*` signal — this is the half of
   `fix_receipt_owned_plugin_detection` that was scoped out in July. Use `bugyi-chops`'
   exact shape as the test fixture. Once represented, it must appear in `sase version`,
   get editable latest-state detection, participate in `sase update` fetch / cleanliness /
   ancestry / code-swap planning, and produce an *actionable error* rather than silent
   omission when its source cannot be inspected. **This is the hard prerequisite for any
   editable migration.**
3. **Add a per-plugin source switch**, extending the existing `--to` vocabulary rather
   than inventing a path flag:
   ```bash
   sase plugin install bugyi-chops --to dev     # install editable from a dev-root checkout
   sase plugin update  bugyi-chops --to dev     # convert an existing install
   sase plugin update  bugyi-chops --to pypi    # convert back once published
   ```
   Resolve the repo through the catalog, materialize or reuse the owner-nested checkout
   under `update.dev_root`, apply the same `_checkout_warning` health checks as the
   whole-environment switch, reconstruct the full receipt replacing only that plugin's
   source, and restart through the existing path. `--to pypi` must **preflight index
   availability** and fail in the preview with a precise reason instead of dying halfway
   through uv resolution — which also repairs the `_index_requirement_for` one-way door
   (§5.2) for the whole-environment leg. Do **not** auto-fall-back from a missing PyPI
   release to editable: that silently creates a durable checkout and a mutable-code
   contract the user did not choose.
4. **Fix the local-path trap (§1.1):** a bare local path must either error with a pointer
   to the new command, or install editable. The current silent frozen-wheel copy is a trap
   either way.
5. **Rewrite the two preflight messages** (`preflight.py:64,113`) to recommend a durable
   dev-root checkout first and an explicit `git+` URL second, instead of `--git`.
6. **Only then, retire `-g`.** Per the flags policy, a deprecation whose old branch must
   stay reachable is a `sunset` flag (default on), created only with `sase flag new`
   (`-k sunset` is a valid kind; it also files the removal bead):
   ```bash
   sase flag new plugin_git_install_source -k sunset \
     --when-enabled  '`sase plugin install -g` resolves a catalog entry to git+<repo url>.' \
     --when-disabled '`-g` is rejected with a pointer to `--to dev` or an explicit git+ URL.' \
     --remove-when   'No SASE-managed environment resolves a plugin through -g, and every catalog plugin is either published to an index or installable via --to dev.'
   ```
   Retire the ACE "from git" variant on the same flag. Both branches need tests.
7. **Never remove receipt tolerance (§6.2).** Consider a decision record — the project
   already carries `decisions:rust-core-required` and friends — stating that *SASE
   tolerates but does not promote VCS-sourced plugins*, so a future agent does not "finish
   the job" and break receipts SASE did not write.

Steps 1 and 2 are worth doing even if you never remove `-g`. Steps 3–6 are the price of
removing it honestly.

### 8.3 What would reopen this

- **A plugin that must never be published and must never have a local checkout** — a
  private plugin on a machine with no source tree, or an authenticated-private-index
  arrangement you do not want to run. That is a policy decision, not an implementation
  accident, and it would justify keeping a promoted git path (renamed to something honest
  like "VCS snapshot") and doing option 5 instead.
- **A catalog that starts listing many unpublished community plugins** would argue for
  option 5 over option 4 — or for finally implementing the automatic index→git fallback
  the original plan specified (§2).
- **`sase update -t` gaining per-package granularity** would complete the
  "editable replaces git" story and could accelerate the flag's removal.

---

## 9. Where the two source reports disagreed

| Question | `__a` | `__b` | Resolution |
| --- | --- | --- | --- |
| Is `bugyi-chops` correctly classified as a git install? | No — git installs are misclassified as `index` | Yes — `plugin show` reports `install_type: "git"` | **Both, for different plugins.** `bugyi-chops` is correct *by accident* (no inventory record); `sase-research-artifacts` is wrong. Verified live (§4.1). |
| How long must receipt-level git tolerance survive? | Permanently | "at least one release," then simplify | **Permanently.** SASE does not own the receipt; a hand-run `uv tool install --with git+…` can create a git row at any time, so this is a standing property, not a migration window (§6.2). |
| Which prerequisite is the real blocker? | The PyPI publish | The runtime-inventory fix | **Both, in that order.** Publishing dissolves the problem on `athena` today and restores reversibility; the inventory fix is the product-level prerequisite for *any* editable migration of a receipt-owned plugin. |
| Shape of the missing per-plugin operation | `sase plugin install -e|--editable <path>` | `sase plugin install/update <name> --to dev\|pypi` | **`--to dev\|pypi`.** It reuses `repo_for_package` + `dev_root` + checkout-health machinery, matches the existing `--to` vocabulary, and avoids inviting arbitrary paths — the exact thing `ephemeral_install_source_error` exists to reject. `__a`'s separate point stands: a bare local path must stop silently producing a frozen wheel (§1.1). |
| Is removing only `-g` cosmetic? | "removes a convenience, not a capability" | "cosmetic, because raw `git+…` also passes through" | **Same claim.** Fine as the last step of a sequence, useless as the first (§7 option 3). |

Findings unique to this pass: the original plan's unimplemented automatic index→git
fallback (§2); the batch-install and `PluginsRequired`-gate paths already hardcoding
`git=False` (§4.3); the empirical `DevRoute` omission (§5.1) and `--to pypi` reconstruction
(§5.2); `classify_git_upstream` taking a local path, so §4.2's fix needs a new remote probe.

---

## Appendix A — verification commands

```bash
cat ~/.local/share/uv/tools/sase/uv-receipt.toml
cat ~/.local/share/uv/tools/sase/lib/python3*/site-packages/*.dist-info/direct_url.json
curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/bugyi-chops/json            # 404
curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/sase-research-artifacts/json # 200 (0.2.0)
gh run list --repo bbugyi200/bugyi-chops --workflow publish.yml
sase update --to dev --dry-run --json     # all six: reuse, zero warnings
sase plugin list  --offline --json        # research-artifacts: wheel; bugyi-chops: git
sase plugin show bugyi-chops --offline --json

SASE_PY=/home/bryan/.local/share/uv/tools/sase/bin/python

# §4.1 — git install reported as a wheel
$SASE_PY -c "
from sase.version.inventory import collect_runtime_version_inventory
for r in collect_runtime_version_inventory(include_plugins=True).packages:
    print(r.name, r.install_type)"

# §5.1 — post-switch dev route silently omits bugyi-chops
$SASE_PY -c "
from sase.uv_tool.receipt import Requirement, ToolReceipt
from sase.main.update_routing import dev_route_from_inventory
from sase.version.inventory import collect_runtime_version_inventory
reqs = (Requirement(name='sase', editable='/x'),
        Requirement(name='bugyi-chops', editable='/y'))
r = ToolReceipt(primary=reqs[0], plugins=reqs[1:], requirements=reqs)
print([x.name for x in dev_route_from_inventory(r, collect_runtime_version_inventory(include_plugins=True)).records])"

# §5.2 — --to pypi reconstructs a bare, unresolvable index requirement
$SASE_PY -c "
from sase.uv_tool.receipt import Requirement, ToolReceipt
from sase.mode_switch.plan import _index_requirement_for
reqs = (Requirement(name='sase', editable='/x'),
        Requirement(name='bugyi-chops', editable='/y'))
r = ToolReceipt(primary=reqs[0], plugins=reqs[1:], requirements=reqs)
print(_index_requirement_for(r, r.plugins[0]).with_args())"   # ['--with', 'bugyi-chops']
```

## Appendix B — unrelated observation

`~/projects/github/` contains a directory literally named `git@github.com:bbugyi200/`,
holding empty (`.git`-only) clones of `bugyi-chops`, `sase`, and a defunct
`sase-chop-telegram`, dated 2026-02-18 through 2026-07-18. The `sase` one predates
install-mode switching (introduced 2026-07-04 in `5131ec849`), so these are not artifacts
of `_checkout_path`, which has always used `dev_root / owner / repo`. They look like
leftovers from a `git clone <url> <url>` mishap and are safe to delete. Noted only so a
future reader does not mistake them for dev checkouts.
