**Reliable SASE installation: a user tool, a checkout environment, and the right Rust core**

Independent research by **cdx**, 2026-10-08. This report uses the shared request, the SASE and sase-core source trees, official upstream documentation, and an isolated uv experiment. No other report, chat transcript, or researcher finding from this swarm was consulted. This is a design recommendation; application code and memory were not changed.

**Assessment.** The proposed naming change is a good idea. It fixes a real ambiguity: today `just install` prepares a repository-local test environment, while SASE's own update and plugin workflows expect a user installation managed by `uv tool`. Reserving `install` for the application people run and naming checkout preparation `install-venv` makes those purposes easier to see.

The rename alone is insufficient. Reliability depends on selecting the correct Rust source, keeping that source available for an editable installation, preserving the user's plugins, and making installation agree with subsequent updates. I recommend proceeding with the rename, but treating these contracts as the feature's acceptance criteria.

“Prod” should mean **the published SASE distribution and its compatible published core**, not a claim of operational readiness. Provider authentication, project configuration, and services are separate setup concerns.

**What the repository actually does.** I inspected SASE at commit `e6adb110af9f6be222782977c8840e2d91cf7cdf` and the opened sase-core checkout at `e411a392bb2ddec27534aea4da1ad69bf2bd86ea`. These observations are tied to those revisions, rather than inferred from recipe names.

| Evidence | Current behavior | Design implication |
|---|---|---|
| `Justfile:181`, `:205`, `:258` | `install`, `install-visual`, and `install-terminal-smoke` use `uv pip install` into `.venv`, with editable SASE and test extras. | These are the three existing public `install*` recipes to rename. |
| `Justfile:18–53` | Core discovery handles explicit `SASE_CORE_DIR`, workspace-scoped linked paths, primary paths, and a sibling fallback. Editable installation can lift the published core version window. | Preserve workspace isolation; consolidate discovery rather than inventing another precedence order. |
| `Justfile:975–1234` | Native recipes install the extension and LSP, use wheel/build caches, remove stale extension files, and have separate target directories for dev builds. Several missing-core/tool cases return success or describe Rust as optional. | Reuse build machinery, but new user-facing dev installation must not equate a skipped build with success. |
| `pyproject.toml` | SASE is `0.17.1`, needs Python `>=3.12`, and declares `sase-core-rs>=0.35.0,<0.36.0`. | Published installation should resolve this metadata normally. Source installation needs an explicit local-source policy. |
| Opened core's `Cargo.toml` | The checkout has version `0.37.0`, outside that published range. | Requiring the published upper bound for dev would reject the actual development checkout. |
| `sase-core-revision.txt` | The checkout pins `e8606a564e4ddccbc4eb2369f4f32dd02ce8c3af`. The opened core contains that commit in its ancestry. | The source pin is a better automatic pairing rule than “latest core.” |
| `INSTALL.md:19–24`; `uv_tool/detect.py` | Managed updates and plugin mutations require the uv tool environment and receipt. Running from `.venv` fails that detection. | Choose uv tool, rather than pipx or a hand-managed global venv, for the new user recipes. |
| `mode_switch/plan.py` | Mode switching already reconstructs the package set, prepares restore information, clones/fetches sources, and reinstalls the tool. Its dev path permits a published core when Cargo is missing. | Share infrastructure, but tighten the requested source-pair contract instead of wrapping this workflow unchanged. |
| `dev_update/core_pin.py`; `dev_update/_plan_core_checkout.py` | Update planning already checks pin ancestry. Its fallback core discovery is narrower than the Justfile's discovery. | Installation and update need the same source-selection contract. |
| `uv_tool/commands.py`; `uv_tool/overrides.py` | Commands reconstruct the complete injected package set. Editable-host overrides loosen the core constraint but do not themselves bind it to a particular core checkout. | Preserve receipt requirements and explicitly name the selected core source. |
| `sase/sase.yml:244`; `.github/actions/setup-sase/action.yml` | A named `install` tool currently executes `[just, install]`; the composite CI action defaults to `install` and allowlists `install|install-visual`. | Reusing the name before migrating callers would make automation install the wrong environment. |

Source links: [SASE Justfile](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/Justfile), [package metadata](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/pyproject.toml), [installation guide](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/INSTALL.md), [Rust integration guide](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/docs/rust_backend.md), [mode-switch planner](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/src/sase/mode_switch/plan.py), [dev source-pin checks](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/src/sase/dev_update/core_pin.py), [CI setup action](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/.github/actions/setup-sase/action.yml), and [core Python packaging](https://github.com/sase-org/sase-core/blob/e411a392bb2ddec27534aea4da1ad69bf2bd86ea/crates/sase_core_py/pyproject.toml).

**The public command contract.** Keep the surface small and organize recipes around the outcome users want.

| Command | Outcome | Destination | Core source |
|---|---|---|---|
| `just install` | Install or refresh published SASE for normal use. | SASE's uv tool environment; commands available through uv's executable directory. | PyPI dependency of the chosen SASE release. |
| `just install-dev` | Run this stable SASE checkout as an editable user tool. | The same uv tool environment. | An explicitly selected compatible local checkout, or an automatically prepared checkout at this SASE tree's pin. |
| `just install-venv` | Prepare this checkout for development and tests. | `.venv`, or its existing configured override. | Preserve the existing local/CI wheel machinery. |
| `just install-venv-visual` | Prepare the checkout with visual-test dependencies. | Repository venv. | Same as `install-venv`. |
| `just install-venv-terminal-smoke` | Prepare the checkout with real-terminal test dependencies. | Repository venv. | Same as `install-venv`. |

Suggested usage, with optional arguments handled by one helper rather than separate recipes for every variation:

```sh
just install
just install --version 0.17.1
just install --dry-run

just install-dev
just install-dev --core /path/to/sase-core
just install-dev --dry-run

just install-venv
just install-venv-visual
just install-venv-terminal-smoke
```

Both user recipes target one active `sase` tool. Running `install` after `install-dev` switches the host and core back to published packages; running `install-dev` switches them to the selected source pair. Simultaneous `sase` and `sase-dev` executables would require a separate command/environment identity that existing receipt detection and services do not currently understand. I would not add that scope here.

`install-dev` means editable application code, not installing pytest, mypy, and visual-test dependencies into the user's everyday tool. Keep those extras in `install-venv*`. A checkout contributor can intentionally use both commands: one for the runnable tool, one for tests.

Default `install-dev` to the checkout containing the Justfile. Do not silently pull SASE, switch its branch, or install a different canonical checkout. Default published installation to the latest stable release; an explicit version must remain an exact request. Repeating either command should ensure the requested result and repair stale artifacts without requiring an uninstall first.

Retain `uv tool install sase` as the documented installation path for people without a checkout. A repository recipe is a convenience, not a replacement for installation instructions that work before cloning the repository.

**Which core is appropriate?** There are two distinct compatibility contracts:

- For published SASE, the dependency specification in its released metadata selects compatible core distributions. A source checkout's revision pin is irrelevant to this path.
- For editable SASE, the selected Python tree and selected core tree must work together. The source pin identifies a known pairing; the core's distribution version alone does not identify its bindings or dirty source changes.

The repository already explains that CI builds from the source pin, while published compatibility is managed at release time. An ancestry check can prove a local checkout includes a needed commit; it cannot prove that later changes remain compatible. A symbol-presence check similarly cannot prove every wire contract or behavior. These are useful checks with different limits, not interchangeable proofs. [Rust backend source and release contracts](https://github.com/sase-org/sase/blob/e6adb110af9f6be222782977c8840e2d91cf7cdf/docs/rust_backend.md).

I recommend the following source-selection policy:

1. **An explicit `--core` or `SASE_CORE_DIR` wins.** Validate that it is the expected Cargo workspace and binding project. Never reset it, switch its branch, or silently fast-forward it during installation. Permit dirty paired development. Require the pinned commit to exist in its ancestry, and verify the resulting bindings and contracts. A core with newer, unpublished APIs is allowed; an incompatible one fails clearly.
2. **An already associated checkout can be reused.** Honor a valid workspace association or stable sibling using the shared discovery rules. Apply the same checks and keep its source unchanged. If an explicit association is invalid, report it rather than silently using another checkout. If an incidental sibling is incompatible, use the pinned managed checkout and show why that sibling was not selected.
3. **Otherwise obtain the exact pin.** Read the pin from the selected SASE working tree, including an uncommitted pin edit. Fetch the full commit and prepare a persistent installer-owned checkout at it. Do not interpret the pin as a suggestion to pull core's default branch.
4. **Missing or malformed pin is actionable failure.** For an older SASE tree without the pairing contract, require a deliberate explicit core selection and compatibility validation; do not invent a latest-core fallback.

A suitable automatic layout is `~/.sase/dev/core/<full-core-sha>/`, adjusted for SASE's configured state location. It must be persistent and outside uv's disposable cache. Reuse a clean checkout with the same full SHA. If that directory has been edited, fail with guidance to use it explicitly or choose a different managed location; do not destroy the edits to recreate an allegedly immutable checkout.

A full clone is simpler to own independently than a Git worktree dependent on another developer clone. Fetching by SHA from a shallow clone can fail when the server cannot provide that object; include a bounded deeper/ref fetch fallback and then fail visibly if the commit remains unavailable. Use HTTPS for automatic public source acquisition so a first-time user does not need GitHub SSH credentials. Existing repository opening policy still applies when an agent accesses those sources.

An installation that has explicitly requested local core source should fail when Git, Cargo, a compiler prerequisite, the binding project, or the required revision is unavailable. It must not quietly substitute the published core. Existing CI's `SASE_CORE_WHEEL` path belongs to `install-venv*`; it is not an implicit exception to the user-facing editable pair.

There is one deliberate escape hatch to discuss with the implementation lead: current `SASE_ALLOW_STALE_CORE=1` supports bisects. Keep that expert behavior explicit and visible if it remains supported, rather than weakening normal dev success criteria. An intentionally incompatible pair should not receive the normal healthy-install success message.

**Editable Rust needs a build contract.** Python edits to SASE should be reflected without reinstalling. Rust edits still need a rebuild; a live editable path does not continuously compile native code. Maturin supports PEP 660 editable installation and `maturin develop`. Import hooks can add automatic recompilation, but that is an additional mechanism and should not be introduced as part of this feature. [Maturin local development](https://www.maturin.rs/local_development).

Prefer having the core source appear as an explicit editable requirement in the uv receipt, pointing to **`<core>/crates/sase_core_py`**, not to the Cargo workspace root. That directory owns the Python distribution. This gives later update/plugin workflows a durable source requirement rather than an unexplained wheel manually inserted into the tool environment.

A source-specific override should point to the selected editable core path. Merely writing `sase-core-rs` as an unconstrained override loosens the published window but still allows a published candidate if no local source requirement binds the resolver. Preserve overrides for editable plugins that are already in the environment, and remove the dev core override when switching to published SASE.

The conceptual uv operation is:

```sh
# Schematic: paths and the complete preserved plugin set come from the plan.
uv tool install --python 3.12 --editable /stable/sase \
  --with-editable /stable/core/crates/sase_core_py \
  --overrides /persistent/installation-overrides.txt \
  --reinstall-package sase-core-rs
```

The override file explicitly names the selected editable core. This is a command shape to implement and test, not a claim that these illustrative paths exist. `--with-editable`, `--overrides`, and targeted reinstallation are supported options in the official [uv CLI reference](https://docs.astral.sh/uv/reference/cli/). Reconstruct existing injected requirements in the actual argv.

Use the established `dev-update` profile and isolated extension/LSP target directories. Maturin documents `editable-profile`; configure or pass the build settings through the supported backend interface and test them with the minimum supported Maturin version. Do not assume an environment variable consumed by an existing Just recipe also changes a PEP 660 build. Old core snapshots that lack the profile need an explicit compatible profile fallback, such as release. [Maturin configuration](https://www.maturin.rs/config.html).

Preserve stale-extension cleanup, source identity stamps, and the LSP installation. The core also provides gateway, federation-worker, and sudo-runner entry points. Verify their expected availability inside the tool environment where relevant; exposing all dependency executables globally is a separate decision. Build the LSP from the same core tree as the extension, since the current developer workflow depends on that parity. Avoid compiling the extension once through uv and then again through `rust-dev-install-uv-tool` just to install the LSP: split preparation and artifact installation as necessary.

A local wheel plus a source stamp can also represent a source-built core, but it would require changing the current update routing, which treats a wheel core beside editable SASE as an environment to repair. Given that existing assumption, genuine editable core requirements are the cleaner target.

**A small experiment establishes the uv behavior.** I ran an isolated probe using installed uv `0.12.23`. It used temporary `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` values, unique fake distribution names, and small Hatchling packages. It did not modify the real SASE tool environment, shell profile, or application checkout.

The fake host required core `>=0.35,<0.36`; the fake editable core was `0.99.0`. A third fake package represented an injected plugin.

| Probe | Result |
|---|---|
| Editable host plus editable core, without an override | Exit 1: dependency resolution rejected the source version outside the host's range. |
| Same requirements, with an override containing `-e <core-path>` and an injected plugin | Exit 0. The receipt recorded editable host and core paths and the editable core override. |
| Repeat the installation while omitting the injected plugin | Exit 0, but uv uninstalled the plugin and removed it from the receipt. |

This validates the resolver and receipt design, and independently corroborates the warning in SASE's existing `build_install` implementation. It does **not** validate the real Maturin build, native binaries, profile configuration, or compatibility of a production/dev SASE pair. Those remain implementation acceptance tests.

**Published installation and plugin preservation.** Use uv tool as the environment owner. Upstream explicitly recommends against directly mutating its managed environments. Existing SASE's native build recipes are a pragmatic exception, but the new path should aim to express Python package sources through uv and reserve manual installation for artifacts such as the separately built LSP. [uv tool environment management](https://docs.astral.sh/uv/concepts/tools/#tool-environments).

For a fresh published install, install the release requirement with a supported Python interpreter. Python 3.12 is the current baseline; allow `--python`, and preserve a compatible existing tool interpreter instead of gratuitously replacing it. Resolve the release's core dependency normally. Do not apply the repository's `uv.lock`, `.venv`, source override, `SASE_CORE_DIR`, or `SASE_CORE_WHEEL` to production.

For an existing install, read and reconstruct its entire injected requirement set before replacement. Preserve version specifications, URLs, editable paths, and supported receipt options. If a receipt field cannot be represented faithfully, fail before changing the install rather than guessing. Treat the host and core as this command's targets; preserve plugin source choices by default. A managed host with an editable plugin is a legitimate mixed package set and should be described accurately.

This is a scope adjustment: the current `sase update --to dev` can convert known plugins as well as the host. New `just install-dev` should not silently turn every installed plugin into a development checkout. Share the planner and execution infrastructure with an explicit target policy. Users who want whole-install mode conversion can continue to use the existing update workflow, once its core contract is aligned.

Avoid unconditional `--force`: it can overwrite executables owned by another installer. Changing a SASE-owned install is expected, but encountering a pipx/system/foreign executable should produce a conflict and an explicit replacement option. Published installation should not require Rust on supported wheel platforms. If a compatible core wheel is unavailable, prefer an actionable failure; a source-build fallback is a deliberate advanced policy, not an invisible change to the installation promise. [uv executable ownership](https://docs.astral.sh/uv/concepts/tools/#overwriting-executables), [uv build options](https://docs.astral.sh/uv/reference/cli/).

Use PyPI as the normal package source and distinguish any configured mirror in the plan. Ensure inherited editable override settings do not accidentally turn the published operation into a source install. Do not automatically install this repository's `plugins.required` into a fresh everyday tool: that declaration belongs to this project, and the existing checkout setup remains responsible for satisfying it. Plugins can be added explicitly afterward through SASE's plugin workflow.

**Implementation structure and bootstrap.** Two long, duplicated shell recipes would be easy to ship and hard to maintain. Keep Justfile recipes as short entry points forwarding arguments to one standalone bootstrap adapter. It must run before SASE or `.venv` exists, and without importing SASE's TUI or a missing Rust binding. A standard-library Python adapter launched through `uv run --no-project --python 3.12` is a reasonable shell/process boundary; uv can supply the interpreter without installing SASE's development dependencies. [uv script execution](https://docs.astral.sh/uv/guides/scripts/).

Separate inspection and planning from mutation. Inputs are the requested mode/version, current source root, optional core selection, discovered receipt, and interpreter. The plan names the selected sources, full package set, preparation steps, target environment, and verification steps. The executor invokes argv arrays, not generated shell strings. `--dry-run` can display fetch/build actions without performing them, and labels unresolved versions honestly rather than guessing.

Reuse and extend `uv_tool/receipt.py`, command reconstruction, source stamps, and the existing code-swap coordination. This does not mean importing those Python modules during a fresh bootstrap and hoping all their dependencies exist. Before a backend is available, keep the adapter's work mechanical: read installation metadata, obtain the selected source, and invoke the package manager/build tooling. Existing-install planning can use the installed backend.

The project boundary matters: new shared source-selection, receipt transformation, and update policy belongs in `sase_core`, with bindings or a thin adapter consumed by both Just and the CLI/TUI. Do not add a new, parallel Python implementation of domain policy merely because the existing update modules are Python. Bootstrap's minimal metadata/process operations and presentation can remain Python glue. Avoid making a published bootstrap depend on locally compiling that Rust planner; the ordinary fresh PyPI path remains a direct uv install with post-install validation. The migration should extract the shared policy needed for these operations, not rewrite the entire update subsystem as a prerequisite.

The implementation must also address **source lifetime**. A user tool cannot safely point at a numbered SASE workspace that the host later reclaims. `install-dev` should reject such a source by default with guidance to use `install-venv` there or run the user installation from a stable checkout. Production installation can be launched from that workspace because its result has no editable reference to it. Apply the same lifetime check to the selected core path. Resolve and display canonical absolute paths so inherited environment variables cannot silently pair different workspaces.

Use uv's actual tool-directory query, rather than assuming a Linux XDG path. First-version recipe support should match the existing POSIX Justfile; wheel support on Windows does not make shell-based recipes Windows-compatible. State that boundary rather than introducing a new portability promise.

**Updates must preserve the pairing.** Automatically prepared core checkouts are pinned and may be detached. The current update code often reasons about a branch and upstream. Installation cannot be declared finished if the first `sase update` skips the detached core or replaces it with unrelated latest source.

Persist a small provenance record identifying the core source policy (`pinned` or `local`), selected root, required pin, built HEAD, and dirty-source fingerprint. Prefer extending the existing source stamp over creating a second package registry; the uv receipt remains authoritative for installed requirements. After uv reconstructs an environment, restore the validated source stamp only for the artifacts actually installed.

For a managed pinned core, an update that advances SASE must read the pin from the new SASE revision, prepare the corresponding persistent core checkout, update the editable requirement, rebuild, and validate the pair before declaring success. For an explicit local core, preserve the developer's source choice and check compatibility against the new host pin; installation itself should not pull that core. Existing update commands may offer their deliberate fast-forward behavior, but that policy must be explicit and keep the pairing checks.

This source-policy distinction is justified extra scope. Without it, an installation can be correct today and broken by the project's supported update command tomorrow.

**What reliable success means.** Define zero exit status around the resulting installation, not around individual subprocesses returning zero.

- The tool environment and uv receipt exist, and host/core source types match the requested mode.
- Every retained injected requirement is still represented and importable as appropriate.
- For dev, the installed core source is the selected binding checkout, its pre-build source identity matches the installed artifacts, and the required pin is present. If source inputs change during compilation, rebuild or fail with a clear retry message.
- The selected environment's interpreter can import SASE and core, run SASE's core health check, and verify the bindings/wire contracts required by the selected Python tree. Use the target interpreter and executable directly, rather than an ambiguous `sase` on PATH.
- The dev LSP and expected native entry points work from that environment. Health verification should run from a neutral directory, avoiding accidental source imports through the current directory or inherited `PYTHONPATH`.
- The receipt/source metadata remains usable by `sase update` and plugin install/update operations.

Keep these checks installation-scoped. `sase doctor` also checks provider authentication and project/service readiness, so it should be an optional suggested next command; an unauthenticated coding provider should not make a correctly installed package fail.

Serialize user-tool mutations using the same coordination as update/plugin operations. Preparation should happen before replacing a working installation where practical: validate the source, prepare the LSP, and let uv resolve/build package artifacts before applying package changes. Save the old receipt and reconstructable restore intent before mutation. On a failed post-install health check, exit nonzero and show the old and current states plus recovery instructions. A command that merely prints a restore command has not rolled back.

Do not promise transactionality for the whole environment unless it is implemented and tested. Moving a staging venv to a different final path is not a safe shortcut because console-script shebangs and editable references can encode paths. uv should continue to own the tool environment. Guaranteed rollback could be added later with a tested uv-aware design; truthful failure and useful restoration are required immediately.

**Making the interface beautiful.** Beauty here comes from a clear result, deliberate defaults, and compact evidence. Group the five recipes under installation and give each a one-line description that names its destination. Just supports recipe groups and parameter forwarding; keep maintenance Rust recipes available without expanding the beginner-facing naming scheme unnecessarily. [Just attributes](https://just.systems/man/en/attributes.html), [recipe parameters](https://just.systems/man/en/recipe-parameters.html).

A proposed dev success presentation:

```text
SASE · development

✓ Source      /stable/sase · <host-revision>
✓ Core        <core-pin> · paired source built
✓ Install     uv tool · 2 existing plugins preserved
✓ Verify      core contracts and native tools healthy

Ready: <uv-executable-dir>/sase
Python edits are live. After Rust edits, rerun just install-dev.
```

Use actual detected revisions and versions in implementation. Show source paths once. Stream verbose build output to a log, with a quiet/plain mode for redirected output and `--verbose` for diagnosis. Report a cache hit as completed preparation, not as a skipped requirement. A failure should identify the failed step and the concrete correction, such as an unavailable pin or conflicting executable.

Print the PATH/shadowing situation accurately. An activated `.venv` may still resolve `.venv/bin/sase` before the freshly installed user tool. Successful installation does not mean the caller's shell is using it. Show the managed executable path and, when necessary, a short instruction to deactivate the checkout environment or adjust PATH. Do not silently edit shell startup files, install completions, configure providers, or restart services as incidental installation effects. Shell integration and runtime restarts should use the established explicit workflows.

**Migration is part of the feature.** Reusing `install` is a behavior change, so a global text replacement is dangerous. Migrate callers according to their intended destination before landing the new meaning.

| Consumer | Required change |
|---|---|
| `Justfile` | Rename the three local environment recipes; update internal examples and repair hints. Preserve CI wheel input and custom venv support. |
| `.github/actions/setup-sase/action.yml` | Change default to `install-venv`; update the allowlist to `install-venv|install-venv-visual`. |
| CI and telemetry workflows | Change `install-recipe: install-visual` to `install-venv-visual`; inspect other setup callers. |
| `sase/sase.yml` named tool | Ensure the existing development installer still executes `[just, install-venv]`. Rename its tool key to `install-venv` deliberately, accounting for callers and recorded tool identities; do not reinterpret old tool duration history as user-install history. |
| `CONTRIBUTING.md`, `docs/development.md`, `docs/rust_backend.md`, performance/repro instructions | Use `install-venv*` for tests and `.venv`; add the user-tool contract where relevant. |
| `sase/memory/lint_and_test.md` | Update local bootstrap names and known-long command examples, keeping the distinction between test setup and user installation. |
| `src/sase/macros/skills/sase_monitor.md` and other discovered skill examples | Replace repository verification examples with `install-venv`; change generated skill sources, not deployed files. |
| Runtime validators and test helpers | Change remedies and assertions that mean “prepare `.venv`.” Preserve generic shell-parser strings when they are only arbitrary parser fixtures, unless changing them improves the example. |
| Receipt/update/plugin handlers | Make source-specific overrides and pairing metadata survive subsequent operations; remove them on published-core conversion. |

Reference memories were read through the audited memory command. Their canonical edits must follow the memory-write workflow and regenerate instructions with `sase memory init`; do not hand-edit generated `AGENTS.md`. Any implementation plan that includes memory edits needs the required per-note memory decision. The `generated_skills` memory also requires deploying changed skill templates from a clean, landed source revision, not from this research checkout.

The old `install` spelling cannot remain a permanent alias for `install-venv` while also doing the new job. I recommend one coordinated migration with a release note. Old suffix names can temporarily be deprecated aliases if there are outside callers; the unsuffixed old name needs a clearly communicated cutover. Follow the project's feature-flag policy if compatibility behavior must remain reachable during staged rollout. Do not add a long-lived flag that makes `just install` mean different things on different machines.

Do not edit immutable historical research reports, transcripts, or accepted decision records simply because they contain old commands. Update living instructions and executable consumers. A migration audit should explicitly distinguish those categories.

**Alternatives and their costs.**

| Approach | Benefit | Main cost | Judgment |
|---|---|---|---|
| Leave names alone and document `uv tool install` | Minimal change; no caller migration. | Maintains the confusing `install` meaning and leaves source pairing to users. | Insufficient for the stated goal. |
| Add `install-user` and `install-user-dev`, retaining current `install` | Avoids the unsuffixed behavior change. | The common application action remains the longer name; original ambiguity stays. | Best fallback if external automation cannot be migrated, otherwise weaker. |
| Implement two small shell wrappers around uv and Rust recipes | Quick initial delivery. | Duplicates source discovery, receipt handling, failure policy, and update rules. | Useful only as a tightly bounded prototype. |
| Make `install-dev` call `sase update --to dev` unchanged | Reuses a mature workflow. | Requires a working prior install; may choose another checkout, convert plugins, and keep a published core when Cargo is absent. | Wrong default contract. Share infrastructure instead. |
| Use pipx or a custom user venv | Standard isolated application installation. | Conflicts with SASE's uv receipt assumptions and supported management commands. | Reject for the primary path. |
| Add root-local `tool.uv.sources` and use `uv sync` for everything | Declarative checkout dependency sources. | Mainly solves project environments; source paths and a lockfile policy do not themselves install a managed user tool or select the right external revision. | Possible future checkout cleanup, not this feature's core solution. |
| Clone latest core for every dev install | Simple source acquisition. | “Latest” can be incompatible with older SASE and makes results time-dependent. | Reject. |
| Automatically use the exact pin, with explicit local override | Reproducible default and room for paired development. | Requires persistent source ownership and updates that follow pin changes. | Recommended. |

**Adjustments to the request, stated explicitly.**

1. Define `install` and `install-dev` as **user-tool** installers; reserve `install-venv*` for repository testing and build extras.
2. Define automatic dev pairing as **the exact core pin of the selected SASE tree**, not latest core. Allow validated explicit local core work, including unpublished versions and dirty changes.
3. Require persistent editable sources. A user tool must not be installed from reclaimable agent workspaces by default.
4. Preserve existing plugin requirements and their source choices. Do not silently convert all plugins or inject this project's required plugins during user installation.
5. Include `sase update` and plugin-operation compatibility in acceptance criteria. Installation alone is not sufficient if normal management immediately destroys the source pairing.
6. Keep direct uv installation documented for users without the repository, and keep the initial Just recipe support at the existing POSIX boundary.
7. Avoid expanding this into a custom environment manager or automatic shell/provider/service setup. uv owns the environment; SASE owns pairing policy, build orchestration, and verification.

These adjustments increase implementation work compared with a rename plus two shell commands. They are justified by existing behavior and the reliability requirement. Cosmetic output should follow those contracts rather than conceal incomplete installation behind a polished success message.

**Acceptance evidence for implementation.** Use focused contract tests with fake subprocesses for planning failures, plus a small real uv/Maturin matrix in isolated tool directories. Relevant scenarios include:

- Fresh published install without Rust; exact-version install; dev-to-published conversion with all editable core overrides removed.
- Fresh dev install with no sibling core; verify installed core at the selected host pin and both editable source paths in metadata.
- Explicit compatible dirty core outside the published upper bound; incompatible or missing-pin core; missing Cargo; a failed clone/build; an unavailable wheel; source edits during compilation.
- A second dev installation that does no unnecessary native work, then a dirty Rust edit at the same HEAD that causes a rebuild.
- Preserved managed and editable plugins across installs, core rebuilds, plugin mutations, and mode conversion.
- A normal update of a pinned managed core to a new host pin; an explicit local core that cannot satisfy that new pin; a source-specific override that survives receipt reconstruction.
- PATH shadowing by an activated `.venv`, paths containing spaces, a foreign executable conflict, two concurrent installers, interrupted installation, and a failed health check with truthful recovery output.
- Existing CI wheel/visual/terminal-smoke preparation after the rename, with the named SASE tool and repair hints still preparing `.venv`.

The published package already has install-smoke and exact-core-floor release jobs. Extend those where suitable; do not replace them with a fake-package probe or recipe-text assertions. Run the project's required `just check` through its tool workflow for implementation changes; the research report alone changes only the separate research repository.

**Recommended solution.** Rename the three local recipes to `install-venv`, `install-venv-visual`, and `install-venv-terminal-smoke` in a coordinated migration that updates CI, the SASE tool catalog, live documentation, memory, and skill sources. Add thin `install` and `install-dev` recipes over one bootstrap adapter. Published installation uses uv and released dependency metadata. Dev installation uses the current stable Python checkout plus an explicitly validated local core or a persistent checkout at that tree's exact core pin, records both editable sources, and builds the extension and LSP with the established dev build machinery. Preserve the user's plugin set, make installation and update share the pairing policy, and report success only after the selected environment passes source and runtime checks. This delivers the requested intuitive names while making the important promise concrete: the installed SASE command and its Rust core belong together.
