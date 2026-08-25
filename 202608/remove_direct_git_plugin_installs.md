# Removing direct-Git SASE plugin installations

**Research date:** 2026-08-25

## Executive summary

SASE's three plugin source forms are not three spellings of the same behavior:

| Source form | uv receipt | Runtime behavior | Update owner | Durable checkout required |
| --- | --- | --- | --- | --- |
| Published/index | `{ name = "pkg" }` | A built artifact is copied into the tool environment | uv/PyPI | No |
| Direct Git | `{ name = "pkg", git = "https://..." }` | uv resolves a Git revision, builds it, and copies the result into the tool environment | uv plus the remote repository | No |
| Dev/editable | `{ name = "pkg", editable = "/path" }` | The tool environment imports from the working tree; local edits are live | SASE's editable-checkout updater plus the developer | Yes |

An editable checkout can provide the same *code* as a direct-Git install, but it does
not provide the same operational contract. Direct Git is a deployment-style source for
an unpublished or revision-pinned package without leaving a mutable working tree on the
machine. Editable mode is a development contract: it depends on a durable checkout,
exposes local edits immediately, can be blocked by a dirty/diverged/detached checkout,
and introduces SASE's code-swap concerns.

The direct-Git option is therefore not intrinsically required, but it **is required by
the current product**. Today it is the only supported way to install an unpublished
catalog plugin without manually reconstructing the uv tool environment. In particular,
`bugyi-chops` is still absent from PyPI, and SASE does not yet offer a per-plugin
editable install or source-switch operation.

Removing direct-Git support is feasible, but the deletion itself is the small part. The
real work is to make “published or editable” a complete two-mode model: support
per-plugin editable installation/switching, make receipt-owned plugins participate in
the editable updater, handle unpublished packages deliberately, and migrate legacy Git
receipts before rejecting them.

## What “from Git” actually means

The current UI wording can suggest that “from Git” is another development mode. It is
not. SASE resolves `--git` to `git+<catalog repository URL>` in
`src/sase/plugins/_operations_common.py`, and uv installs a built snapshot of the
resolved revision. PEP 610 metadata records the VCS URL and resolved commit. The live
`bugyi-chops` distribution demonstrates this:

```json
{
  "url": "https://github.com/bbugyi200/bugyi-chops",
  "vcs_info": {
    "vcs": "git",
    "commit_id": "22b3db5f72330f70494b3fd0b72da2fe34378b07"
  }
}
```

By contrast, an editable install records a local file URL and
`{"dir_info":{"editable":true}}`; imports resolve into that checkout. These are
standard Python packaging distinctions, not SASE inventions. uv documents Git sources,
revision selection, and editable local dependencies separately in its
[dependency-source guide](https://docs.astral.sh/uv/concepts/projects/dependencies/),
and the packaging specification gives the corresponding
[VCS and editable `direct_url.json` shapes](https://packaging.python.org/en/latest/specifications/direct-url-data-structure/).

One nuance: the *installed* direct-Git artifact is a snapshot, but an unpinned Git URL
is not a reproducible specification. `bugyi-chops` has no branch, tag, or commit in its
receipt, so the next targeted update may resolve a newer default-branch commit. A Git
URL pinned to a commit is reproducible; the current `--git` convenience flag is not.

## Why SASE added the third source

The original plugin-install plan explicitly records the reason: catalog plugins were
expected to live on PyPI when possible, with Git as the fallback for a catalog plugin
that was not published. That became `sase plugin install <name> --git` and the Admin
Center's “from index / from git” toggle.

That fallback solved two concrete problems:

1. It let a user install an unpublished community plugin directly from the catalog
   without first choosing and maintaining a checkout location.
2. It gave SASE a durable replacement for local paths inside numbered SASE workspaces.
   Those workspaces are ephemeral. SASE now rejects such local sources and explicitly
   recommends either a direct-Git install or a checkout outside the workspace store in
   `src/sase/uv_tool/preflight.py`.

Direct Git also has legitimate secondary uses: installing a private repository when no
index exists, testing a branch or commit without exposing a live checkout, and deploying
an unpublished package onto a machine that is not a development workstation.

The cost is a less coherent product model. Direct-Git installs are classified as
managed work even though they are not index releases. SASE does not compare them with
PyPI or their remote Git branch, so the catalog shows `git / not compared` and no update
indicator. Updates work only because SASE faithfully reconstructs the Git requirement
and asks uv to `--upgrade-package`; incoming commit visibility and editable checkout
health do not apply.

## Current `bugyi-chops` state

The live SASE uv receipt currently contains:

```toml
requirements = [
    { name = "sase", editable = "/home/bryan/projects/github/sase-org/sase" },
    { name = "bugyi-chops", git = "https://github.com/bbugyi200/bugyi-chops" },
    { name = "sase-research-artifacts", git = "https://github.com/sase-org/sase-research-artifacts" },
    { name = "sase-github", editable = "/home/bryan/projects/github/sase-org/sase-github" },
    { name = "sase-telegram", editable = "/home/bryan/projects/github/sase-org/sase-telegram" },
]
```

The installed `bugyi-chops` artifact is version `0.7.0` at commit `22b3db5f…`.
`sase plugin show bugyi-chops --offline --json` correctly reports it as an installed
community plugin with `install_type: "git"`, but with no comparable latest version.

The source repository is ready to build and has a tag-driven PyPI publish workflow, but
the public PyPI JSON endpoint for
[`bugyi-chops`](https://pypi.org/pypi/bugyi-chops/json) returns HTTP 404 as of this
research. Its README currently says both “install the published package” and “for
development ... use `-g`”; both statements are inaccurate today: there is no published
package, and `-g` is a non-editable VCS install rather than a development checkout.

This means removing `--git` immediately would leave a fresh user no supported command
that can install `bugyi-chops`:

- the default `sase plugin install bugyi-chops` resolves only the distribution name and
  fails when uv cannot find it on PyPI;
- a raw local directory is installed as a non-editable path unless SASE reconstructs it
  with `--with-editable`;
- `sase update --to dev` converts packages already present in the receipt, so it cannot
  bootstrap an uninstalled plugin.

## What the current migration path can and cannot do

The existing whole-environment mode switch can plan a conversion. On this machine,

```bash
sase update --to dev --dry-run --json
```

proposes to reuse `/home/bryan/projects/github/bbugyi200/bugyi-chops` and reinstall it
with:

```text
--with-editable /home/bryan/projects/github/bbugyi200/bugyi-chops
```

That is encouraging, but it is too broad for a one-plugin migration: it also converts
`sase-research-artifacts`, fetches or fast-forwards every SASE checkout, reinstalls the
whole uv environment, and rebuilds the Rust core. There is no supported equivalent for
“replace just the `bugyi-chops` receipt requirement with this editable path.”

More importantly, **the planned migration is not safe yet**. `bugyi-chops` is a valid
receipt-owned plugin, but it intentionally has neither a `sase-*` distribution name,
nor a `sase_*` plugin entry point, nor a `sase_chop_*` console script. SASE previously
fixed receipt-aware installed status for the catalog, but runtime version inventory
still uses only those naming/entry-point heuristics. The evidence is visible now:

- `sase plugin show` includes `bugyi-chops` because the catalog merge reads the receipt;
- `sase version -j` omits it;
- the mode-switch preview has no current version for it;
- `src/sase/plugins/latest.py::_editable_latest_info()` explicitly reports
  `editable install is missing from version inventory` when this happens;
- `src/sase/main/update_routing.py::dev_route_from_inventory()` updates only editable
  receipt entries that have matching version-inventory records.

After a conversion today, SASE would import the editable checkout, but later
`sase update` runs would silently omit that checkout from their Git fetch/fast-forward
plan. Direct-Git targeted updates do not have this blind spot because they operate from
the receipt and let uv refresh the requirement.

Therefore the current whole-install command should be treated as a useful preview, not
as the recommended `bugyi-chops` migration procedure.

## Required product and implementation work

### 1. Make receipt-owned editables first-class runtime records

Unify the two notions of installed plugin. The receipt-aware logic already used by
`src/sase/plugins/installed.py` should feed runtime version inventory or editable update
routing as well. Every explicitly injected receipt plugin needs a
`VersionPackageRecord`, even when it has no conventional SASE signal.

Coverage should use `bugyi-chops`' exact shape: a non-`sase-*` distribution with only
`bugyi_chop_*` console scripts. Once represented as editable, it must:

- appear in `sase version` with its source root and Git metadata;
- receive editable latest-state detection in `sase plugin list/show`;
- participate in `sase update` fetch, cleanliness, ancestry, code-swap, and reconcile
  planning;
- produce an actionable error instead of being silently omitted if its source cannot be
  inspected.

This is a prerequisite for migration, independent of whether direct-Git support is
ultimately removed.

### 2. Add per-plugin editable install and source switching

The two-mode model needs a first-class operation, not a raw local-path escape hatch.
A coherent CLI would extend the existing `--to` vocabulary:

```bash
sase plugin install bugyi-chops --to dev
sase plugin update bugyi-chops --to dev   # convert an existing install
sase plugin update bugyi-chops --to pypi  # convert back when published
```

Exact command naming can be settled during design, but the behavior must be explicit:

1. Resolve the repository through the catalog.
2. Materialize or reuse an owner-nested checkout under `update.dev_root`.
3. Apply the same clean/upstream/durable-path checks used by whole-install mode
   switching.
4. Reconstruct the full uv receipt while replacing only the selected plugin's source.
5. Install it with `--with-editable`, preserve every other package source, and restart
   SASE processes through the existing path.
6. On `--to pypi`, verify that an index release exists before replacing the editable
   requirement. An unpublished plugin should fail in the preview with a precise reason,
   not fail halfway through uv resolution.

The Admin Center should expose those same two variants. Its highlighted-plugin `m`
action is the natural surface for a *per-plugin* switch; the current global
`sase update --to ...` operation can remain for users who intentionally want to convert
the entire environment.

Automatic fallback from a missing PyPI package to editable mode is not recommended. It
would silently add a durable checkout and the mutable-code contract. The user should
choose dev mode explicitly.

### 3. Decide the policy for unpublished catalog plugins

With direct Git gone, every installable catalog entry must satisfy one of these rules:

- it has a published distribution and defaults to PyPI; or
- its user explicitly selects dev/editable mode and accepts a durable checkout.

For production-like machines, publishing is the better answer. It avoids live source
trees, Git cleanliness failures, and code-swap hazards while providing ordinary version
and update comparisons. The `bugyi-chops` publishing workflow and README should be
reconciled with reality, and `0.7.0` should be published if the package is intended to
have a managed installation mode.

Private plugins can still use an authenticated private index. If SASE intends to
support private-Git-only deployment without editable checkouts, then direct Git remains
a legitimate source and should not be removed; that requirement is a policy decision,
not an implementation accident.

### 4. Migrate existing direct-Git receipts before deleting compatibility

Removing only the `-g|--git` flag would be cosmetic because raw `git+...` requirements
are also passed through today. A real removal must cover both creation paths while
still recognizing legacy receipts long enough to migrate them.

A safe staged sequence is:

1. Add the receipt-inventory fix and per-plugin `--to dev|pypi` switch.
2. Mark `--git`, raw Git URL installation, and the Admin Center's “from git” variant as
   deprecated. New uses get a precise `--to dev` or publication/index alternative.
3. Detect existing `{ git = ... }` receipt entries and show an actionable migration
   status. Continue parsing and reconstructing them during the deprecation window so
   unrelated installs, updates, and uninstalls do not break.
4. Convert this machine's `bugyi-chops` entry with the new per-plugin command and verify
   its receipt, PEP 610 metadata, version inventory, catalog latest state, executable
   paths, and one no-op/one-behind editable update scenario.
5. Convert `sase-research-artifacts` to either its published distribution or editable
   mode; it is the other direct-Git receipt on this machine.
6. Once supported installations have no Git receipts, reject new Git specs and remove
   the UI toggle. Keep legacy receipt parsing for at least one release so uninstall and
   recovery remain possible.
7. Only then simplify the `Requirement.git` model, Git-specific latest rendering, docs,
   and compatibility tests.

### 5. Update safety guidance and documentation

Several current errors recommend `sase plugin install --git <name>` as the durable
alternative to an ephemeral or missing local source. Those messages must instead point
to a durable dev-root checkout or a published/index install. Documentation also needs
to stop calling direct Git “development” and state the live-code implications of
editable mode.

## Change surface and risk

The direct removal touches a modest, well-isolated set of surfaces:

- CLI parsing and source resolution (`parser_plugin.py`, `_operations_common.py`);
- install planning and JSON source labels;
- the Admin Center's dual install preview and durable-proc request;
- direct-Git classification/latest rendering;
- local-path preflight recovery messages;
- plugin docs, configuration docs, completion snapshots, and focused CLI/TUI tests.

The prerequisite work is larger than that deletion:

- runtime inventory and dev-update routing need receipt-aware records;
- mode-switch repository planning must be refactored into a reusable per-plugin source
  switch;
- legacy receipt migration and PyPI-availability preflight need new typed outcomes;
- real-uv integration tests must prove that replacing one source preserves all other
  injected requirements and executable exposure.

The main regression risks are losing a plugin while reconstructing uv's replacing
`--with` set, stranding an old Git receipt so all future updates fail, silently failing
to update a receipt-owned editable, and converting a deployment install into live
mutable code without an explicit user choice.

## Recommended solution

Adopt the two-mode goal—**published/index for managed use, durable editable checkout for
development—but do not remove or migrate direct-Git installs yet**.

First, make receipt-owned plugins such as `bugyi-chops` participate fully in runtime
version inventory and editable updates. Second, add an explicit per-plugin
`--to dev|pypi` source-switch operation that reuses SASE's durable `update.dev_root`
checkout machinery. Third, fix and use the `bugyi-chops` PyPI release path so ordinary
server installations can be managed artifacts; reserve editable mode for machines where
live development is actually wanted. Then migrate `bugyi-chops` with the new targeted
command, migrate the remaining `sase-research-artifacts` Git receipt, deprecate new Git
installs for one release, and finally remove the creation/UI paths while retaining
legacy receipt parsing for recovery.

If SASE wants to keep supporting unpublished private plugins on non-development
machines, stop after the migration work and retain direct Git under a clearer name such
as “VCS snapshot”; that use case cannot be replaced by editable mode without changing
its operational and security contract.
