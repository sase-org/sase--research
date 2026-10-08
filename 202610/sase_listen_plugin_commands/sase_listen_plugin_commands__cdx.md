# Making sase-listen a first-class SASE plugin

Researcher: **cdx**. Independent investigation; no peer swarm reports or findings were consulted.
Date: 2026-10-08. Scope: implementation research and critique, not an implementation.

## Assessment

**This is a good idea if “first-class plugin” means an optional package that contributes a command, shares SASE’s completion, and uses the existing installation manager.** It should retain its independent CLI and audio implementation. Moving narration into SASE, making SASE a mandatory dependency of sase-listen, or inventing another updater would add coupling without helping this request.

The smallest durable solution is a versioned Python entry-point contract for top-level commands, with two capabilities: execute an unchanged argument vector and supply an argparse parser for completion. SASE should own discovery, command-name conflicts, completion cache freshness, and installation lifecycle. sase-listen should own its arguments, defaults, output, errors, configuration, and rendering.

A useful finding changes the apparent scope: **the Updates-tab catalog integration already works.** The new work is principally command dispatch and completion correctness, plus compatibility for existing callers of the standalone executable.

## Evidence and limits

I inspected the local repositories through `sase repo open`, at these revisions:

| Repository | Inspected revision |
| --- | --- |
| sase | `f92bde8abef2bf0191273e86c30325e12d243fad` |
| sase-listen | `3ae7310388449c2513e90b14428ccd6fce0482f1` |
| sase-core | `1ff436055b128f21349e0f8d1136020e0a4cb079` |
| sase-research-artifacts | `bea92afb713db71c666a4f62ea53c4652460e2c4` |

Live checks were read-only or dry runs. `gh repo view sase-org/sase-listen --json nameWithOwner,repositoryTopics` confirmed the `sase--plugin` **repository topic**. `sase plugin show listen -r -j` successfully returned `found: true`, `name: listen`, `kind: builtin`, and latest index version `0.1.1`; this running SASE environment did not have it installed. `sase plugin install listen -n` produced an install plan using `--with sase-listen` while retaining the existing editable SASE/plugin requirements. No installation was performed. Those diagnostics reflect the running host environment, separately from the source revisions above.

I also reproduced two argparse hazards with small standard-library probes: nested subparser actions both using `dest="command"` produce `{"command": "render"}` for `listen render`, losing the outer command; `parse_known_args` consumes an abbreviated known option (`--pro` for `--progress`) instead of reliably preserving a foreign argument vector. These probes were not end-to-end tests of a proposed implementation. Python’s documentation explicitly warns about prefix matching in partial parsing. [Python argparse documentation](https://docs.python.org/3/library/argparse.html#partial-parsing)

## What exists today

### CLI routing is closed, but already designed for lazy loading

SASE has a static `_COMMAND_REGISTRARS` inventory of built-in command trees. `parser_only_hint()` selects a narrow tree for ordinary invocations; `entry.main()` handles a few fast paths and then uses an explicit chain of built-in handlers. There is no command-plugin registration point. Adding one parser alone would therefore not establish dispatch. Root help also has a curated compact inventory distinct from the full inventory. [Registrar registry](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/parser_registry.py), [entry point](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/entry.py), [root help](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/parser_root_help.py)

Preserve that lazy architecture. A built-in operation such as `sase bead show` should not import the audio stack because a narration plugin happens to be installed.

### sase-listen already provides the right execution seam

Its console script points to `sase_listen.cli:main`. The actual implementation exposes `build_parser()` and `main(argv: Sequence[str] | None = None) -> int`. It registers command modules, stores their handlers in `args.func`, prints help and returns usage code 2 when invoked bare, and catches `BrokenPipeError`. `prog="sase-listen"` is currently fixed. [Packaging](https://github.com/sase-org/sase-listen/blob/3ae7310388449c2513e90b14428ccd6fce0482f1/pyproject.toml), [CLI implementation](https://github.com/sase-org/sase-listen/blob/3ae7310388449c2513e90b14428ccd6fce0482f1/src/sase_listen/cli/app.py)

The inspected parser includes `audition`, `cache`, `config`, `doctor`, `feed`, `guide`, `lint`, `ls`, `publish`, `render`, `script`, and `unpublish`. Some commands remain stubs in this revision. Integration should preserve whatever the installed version implements, rather than silently turn this project into an effort to finish those commands.

### Completion is substantially richer than a static command-name list

`completion.build.build_spec()` walks argparse into `CompletionSpec`, including nested commands, options, choices, mutual exclusion, and positional arguments. Bash, fish, and zsh emitters consume that model. The TUI Command Line also consumes spec JSON through an identity-keyed cache and Rust `CommandLineGrammar`. Reusing this model makes plugin commands available across these surfaces. [Spec builder](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/build.py), [TUI spec cache](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/command_line_spec.py), [Rust grammar](https://github.com/sase-org/sase-core/blob/1ff436055b128f21349e0f8d1136020e0a4cb079/crates/sase_core/src/command_line/grammar.rs)

Managed shell installation writes a small loader that obtains cached grammar from the active executable. Manual `sase completion zsh|bash|fish` exports are snapshots. **Neither a plugin install nor a regenerated file automatically replaces functions already loaded into an existing shell.** [Completion documentation](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/docs/completion.md), [loader implementations](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/loader.py)

The current cache identity enumerates only `sase` and `sase-core-rs`. Its source fingerprint scans SASE’s `__init__.py`, `completion/`, and `main/`, with `SASE_HOME` as an environment input. It does not identify command-contributing plugins, their entry points, plugin disable controls, or their editable sources. Consequently, merely adding a plugin parser would permit a pre-existing cached grammar to remain valid after a plugin-only change. This is a prospective integration gap, not evidence that today’s built-in grammar is broken. [Cache identity and fingerprint](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/runtime_cache_identity.py)

### Updates already uses the correct catalog

GitHub discovery searches `topic:sase--plugin`; repositories under `sase-org` are classified as built-in, and `sase-listen` derives short name `listen`. Updates rows project the shared catalog rather than maintaining their own plugin list. The topic is sufficient for discovery; an issue label alone would not be. The live check confirmed the user’s change is the required topic. [GitHub search boundary](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/plugins/_github_source_gh.py), [Updates row model](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/ace/tui/modals/plugins_browser_rows.py)

Installed status combines entry-point inventory, SASE distribution/console-script signals, and explicitly injected uv receipt packages. sase-listen’s distribution name already qualifies when present in the **running SASE environment**. A separate `uv tool install sase-listen` environment does not make it an installed SASE plugin. The default Outdated scope also legitimately hides an uninstalled plugin; check Available or All and refresh the catalog. [Installed merge](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/plugins/installed.py), [distribution detection](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/version/_plugins.py)

## Alternatives

| Approach | Advantages | Costs and concerns | Verdict |
| --- | --- | --- | --- |
| Hard-code `sase listen` in SASE | Small first patch | Couples core to one optional tool; does not establish a reusable plugin capability | Only a temporary bridge |
| Discover arbitrary `sase-*` executables from PATH | Separate environments; simple process delegation | Names do not prove plugin intent; ambiguous executable versions; no grammar/completion contract | Avoid as the primary design |
| Let plugins mutate the complete argparse tree and dispatch parsed namespaces | Fits existing registrar style | Exposes built-ins to mutation, namespace collisions, global validation, and default-command rewriting | Possible, but unnecessarily broad |
| Versioned entry point with argv execution and parser factory | Preserves the existing CLI; explicit discovery; one argument definition feeds completion | Requires a small registry and grammar-composition adapter | **Recommended** |
| Rewrite CLI around Click/Typer or add a separate JSON CLI schema | May offer richer future extension machinery | Framework migration or another argument definition to synchronize | Not justified for this request |
| Separate `sase-listen-plugin` adapter distribution | Leaves standalone package completely unchanged | Extra release, version, and catalog identities for a very small adapter | Reserve for a real packaging incompatibility |

Python packaging entry points provide installed component discovery and deliberately leave cross-distribution name conflict handling to the consumer. SASE can use this existing packaging mechanism without introducing a second plugin manager. [PyPA entry-point specification](https://packaging.python.org/en/latest/specifications/entry-points/)

## Explicit adjustments to the requirements

1. **Retain standalone use.** Publish one `sase-listen` distribution with its current console script and an optional SASE command contribution. Keep SASE and sase-core out of its mandatory dependencies and imports. The existing AGENTS.md and integration docs prohibit SASE entry points; implementation must explicitly revise that prohibition while retaining the standalone boundary. The user’s new direction supersedes that old design rule. [Existing instructions](https://github.com/sase-org/sase-listen/blob/3ae7310388449c2513e90b14428ccd6fce0482f1/AGENTS.md)
2. **Define behavioral parity precisely.** Identical suffix arguments must retain argument acceptance, defaults, config/env paths, JSON/data output, exit codes, stream behavior, progress, and interrupts. Help/usage should identify `sase listen`; version output should still identify the installed sase-listen version. Literal example/error text containing `sase-listen` can be updated gradually. Do not force a bare `sase listen` to become `ls` or introduce SASE-specific output/artifact behavior.
3. **Define automatic completion freshness.** Managed plugin installs, updates, removals, and batches should refresh existing managed completion installations automatically; a fresh shell must receive the current grammar without a manual generation command. For v1, document that already-open shells reload their completion or restart. This is an explicit narrowing of a possible “next Tab in every existing shell” interpretation. If that stronger guarantee is required, add a shell-native generation-marker check and reload mechanism, with performance tests; avoid launching Python on every Tab. Unmanaged snapshot exports remain explicitly unmanaged.
4. **Include the TUI Command Line.** Because it uses the same spec, installation should make `sase listen` available there as well. Its cache must invalidate with the shell grammar’s plugin identity. This does not require a new audio panel or streaming player.
5. **Preserve existing automation.** Installing the plugin alone must not lead existing SASE audio workflows to use an unrelated standalone version or an unnecessary uvx download. Update those workflows to prefer a compatible `sase listen` when available, then preserve their existing standalone/uvx fallback. Keep remote feed hosts’ standalone executable requirement documented initially.
6. **Treat Updates visibility as validation, not a new catalog implementation.** Confirm the existing topic-driven row, installed version, entry-point details, and install/update/uninstall actions. Do not hard-code a listen row or require installation through GitHub rather than the existing index/git resolution.
7. **Limit v1 to owned top-level subtrees.** Plugins may contribute `sase <name>` and descendants, but cannot patch built-in commands or override names/aliases. Arbitrary live completion-provider plugins, configurable command renaming, and arbitrary external CLI frameworks can wait for a second demonstrated use case.

These changes preserve the user’s desired experience while making compatibility and completion semantics testable.

## Proposed command contract

Use a new entry-point group, for example `sase_cli`, consistent with SASE’s existing `sase_*` groups:

```toml
[project.entry-points."sase_cli"]
listen = "sase_listen.sase_plugin:provider"
```

PyPA recommends project-prefixed dotted group names for new groups, so `sase.cli` is also defensible; choose one spelling once. `sase_cli` minimizes divergence from this project’s conventions. The name identifies the owned root command. The loaded object can be a small factory returning a provider with this conceptual interface:

```python
api_version: int                 # initially 1
summary: str
build_parser(*, prog: str) -> argparse.ArgumentParser
invoke(argv: Sequence[str], *, prog: str) -> int
```

This is a proposal, not an existing SASE API. Define the protocol in the host; plugins can satisfy it structurally using standard-library types, without importing SASE. Add small optional metadata for completion hints and TUI execution properties if necessary; do not ask plugins to emit shell code or maintain a second CLI grammar.

For sase-listen, add `prog` as an optional keyword to `build_parser` and `main`, defaulting to `sase-listen`. A lightweight provider module delegates to those functions and imports the CLI only when the parser or invocation is requested. Execution becomes `main(argv, prog="sase listen")`. Both front doors retain the same command-module registration and error handling.

### Dispatch and parser composition

Discover metadata with `importlib.metadata.entry_points`, associate each contribution with its distribution, and sort deterministically. Metadata enumeration should not load every provider. Resolve leading SASE global options once, determine the root command, and route a selected plugin’s suffix arguments directly to `invoke`. Preserve the order and spelling of every suffix token, including `--` and positional strings. Honor SASE’s explicit leading `-p/--print-command`; never consume a same-spelled option after the plugin root as a SASE global.

For a built-in root, retain the existing narrow parser/fast path. For root inventory/help, expose lightweight plugin entries from the same command catalog. Curated compact help can add a short plugin section or direct users to full help; full help must list contributed commands and their distribution ownership.

For completion, build the builtin spec as today, walk each plugin’s own parser with the existing builder under path `("listen",)`, and merge those command nodes into the root spec. Promote the existing private walker to a supported internal composition seam. The result is one combined `CompletionSpec` feeding the existing emitters and Rust grammar. This differs slightly from mounting a live plugin parser into the execution parser, but the grammar still comes from the exact parser the plugin executes.

This arrangement avoids an actual trap: both SASE and sase-listen currently use `dest="command"`. It also avoids copying parsers with `parents=` and then repairing help-action conflicts or stale nested `prog` values. SASE’s parser subclass performs built-in validation, and its postprocessor defaults any exact `list` child; neither rule should rewrite an independent plugin’s execution semantics. The completion walker itself currently infers `default_child="list"` by child-name presence, so plugin composition must use the plugin’s actual default behavior rather than that inference. [Parser validation](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/parser_root_args.py), [default-list transformation](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/parser_root_defaults.py)

### Conflicts, disable controls, and diagnostics

Reserve every built-in root and alias, including aliases hidden from normal help. Reject invalid command names. If two distributions claim the same root, disable that ambiguous command with a message naming both owners rather than choosing whichever entry point happens to come first. One broken plugin should not make unrelated built-ins, completion candidates, or plugin uninstall unavailable.

Respect `SASE_DISABLE_PLUGINS` and a group-specific control such as `SASE_DISABLE_PLUGIN_CLI`. Unsupported API versions and import/parser failures should produce an actionable error for the selected command and a visible doctor diagnostic. Completion generation should preserve usable built-in grammar and report omitted broken plugin subtrees on stderr. Cache the omission as part of the resulting grammar’s health evidence, rather than retrying a failed import on every keystroke.

Add the new group to `plugins.inventory.ENTRY_POINT_GROUPS`; otherwise commands can function while version/doctor/group displays omit their capability. Deep diagnostics can load and validate providers; ordinary inventory should remain metadata-only. [Inventory](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/plugins/inventory.py)

### Completion annotations and TUI semantics

Ordinary argparse choices already cover editions and progress modes. File options should complete paths, while voice/narrator/config text needs accurate hints. Mixed source values remain free to accept files, URLs, and artifact refs; file suggestions must not narrow accepted input. Prefer a public descriptor map of relative command paths and argument destinations to host completion kinds/hints, rather than importing SASE or setting undocumented action attributes from sase-listen. Defer live voice/narrator enumeration unless required.

The spec also has `run_policy`, `writes`, and `stdin` fields. Its current verb heuristics will not identify `render` and `publish` as writes; `feed receive` is a binary stdin transport. Add provider metadata for these existing fields so the TUI does not give misleading execution advice. Completion callbacks must never render, fetch an article, access paid APIs, or initialize user config. [Spec model](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/model.py), [execution metadata](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/run_policy.py)

Plugin imports are execution of installed code, as with existing SASE providers. Do not treat a GitHub topic as a trust boundary or attempt to build a new sandbox for this integration. Keep discovery offline and metadata-only, and preserve existing installation previews and ownership diagnostics.

## Making completion refresh automatic and reliable

Two pieces are necessary; implementing only one is insufficient.

**First, fix identity-based invalidation.** Add a deterministic list of command entry points and owning distribution names, versions, locations, and installation metadata to the runtime identity/fingerprint. Include effective plugin disable controls. Reinstallation with the same package version and entry-point-set changes should invalidate too. For editables, incorporate plugin grammar-source changes, including command definition files reached from the provider; hashing only the provider file is insufficient. A conservative scoped fingerprint of the contributing package’s source is acceptable for v1, with warm-cache measurements. Do not import a plugin just to compute its ordinary identity; use installed-distribution/direct-url metadata and require explicit editable grammar roots if they cannot be resolved safely.

Use this identity in both runtime shell caches and the TUI spec cache. Source fingerprinting already checks filesystem changes; extending it should not entail a full parser build at each cache hit.

**Second, refresh after successful environment mutations.** Apply one shared post-change hook to CLI/TUI install, batch install, update, uninstall, required-plugin installation, and core updates that change injected packages. Reuse `completion refresh` and preserve loader ownership/stamps. Current plugin operation functions execute uv without a completion-refresh step; core `sase update` already provides a useful fresh-child-process implementation. [Plugin operations](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/plugins/_operations_install.py), [core update refresh helper](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/main/update_handler_completion.py)

Run refresh through the newly installed SASE executable, not by importing modules into the old updater/TUI process. Reinstallation may replace files beneath an already-imported process. Preserve successful package installation if refresh fails, but report the completion failure in human output and structured results with a retry command. Do not quietly claim the whole completion requirement succeeded. Retain the existing TUI restart behavior; the new process should observe the new command spec.

Correct identity also provides recovery when installation happens through pip/uv outside SASE: a fresh loader invocation must notice the changed command providers even if the explicit post-install hook never ran. No plugin-specific installation hook is necessary.

## Packaging and automation: the easily missed issue

`uv tool install sase --with sase-listen` installs the additional distribution in SASE’s isolated environment, but `--with` does **not** publish that package’s executable to the user’s PATH. uv provides `--with-executables-from` for that separate behavior. [uv tools documentation](https://docs.astral.sh/uv/concepts/tools/#installing-executables-from-additional-packages)

This matters here because the audio macro chooses `sase-listen`, checks `--generated-cover`, and falls back to `uvx sase-listen`. The feed transport constructs a remote command invoking `sase-listen feed receive`. Plugin-only installation could otherwise cause SASE automation to use a different version than `sase listen`, or download another copy. [Audio workflow](https://github.com/sase-org/sase-research-artifacts/blob/bea92afb713db71c666a4f62ea53c4652460e2c4/src/sase_research_artifacts/xprompts/research_audio.md), [SSH transport](https://github.com/sase-org/sase-listen/blob/3ae7310388449c2513e90b14428ccd6fce0482f1/src/sase_listen/feedhost.py#L162)

My default is to keep the generic SASE plugin installer’s existing `--with` behavior and make SASE-owned workflows prefer a capability-checked `sase listen`, retaining their standalone/uvx fallback. This makes the environment managed in Updates the environment actually used for narration. Preserve the standalone package/script for non-SASE users and existing remote hosts. Broader remote-command migration can be a separate change after deciding whether those hosts should require SASE.

If the product requirement instead includes a globally available `sase-listen` after every plugin install, say so explicitly and implement selective executable exposure. That has larger consequences: receipt reconstruction must preserve exposure through reinstall/uninstall, and an existing separately installed standalone tool can own the same executable. Do not enable `--force` to overwrite it automatically. Merely retaining `[project.scripts]` is insufficient to promise PATH exposure.

The audio dependencies are substantial, including numpy, image/PDF/HTML extraction, HTTP clients, and Google’s SDK. They remain optional for SASE users, but share its resolver when installed as a plugin. Test dependency compatibility; do not add sase-listen to SASE’s mandatory runtime requirements. A separate adapter package is only justified if actual resolver or release constraints demonstrate the need.

## Rust ownership and rollout

Python must discover Python distribution metadata, construct argparse trees, and invoke Python callables. Those are runtime integration responsibilities. Shared descriptor validation, ownership/conflict rules, and any new completion/domain semantics that the CLI and TUI must agree on belong in `sase_core`, called through a thin adapter. Keep the existing Rust `CommandLineGrammar` consuming the combined spec rather than introducing a second Python completion engine. New binding/wire changes require matching Rust tests and advancing SASE’s `sase-core-revision.txt`; do not use this feature as a reason to migrate the entire legacy plugin manager at once.

A practical implementation sequence is:

1. Establish the small provider contract, command metadata/validation, conflict policy, and metadata-only inventory. Add fake installed-provider integration fixtures before depending on a real listen release.
2. Implement early argv routing and combine built-in/plugin parser specs. Preserve fast paths and add explicit plugin default-command and argument-hint handling.
3. Implement shared cache identity and post-mutation refresh, covering CLI and TUI and editable sources.
4. Add the lightweight provider to sase-listen and parameterize its parser’s `prog`. Update its standalone-boundary instructions and documentation.
5. Verify the existing Updates entry/actions and migrate the SASE audio workflow’s capability-based CLI selection.
6. Release host support before publishing the listen entry point; document the first compatible SASE version and standalone behavior on older hosts.

No CLI framework migration, extra updater, new audio UI, or generic network completion API is required.

## Acceptance checks

| Area | Useful evidence |
| --- | --- |
| Behavioral parity | Compare standalone and plugin invocations for bare help/exit 2, root/nested help, version, unknown flags, config JSON, lint errors, local deterministic script creation, and tone-engine rendering. Normalize only intentional invocation-name text. Preserve streams and interrupt/broken-pipe behavior. No paid TTS required. |
| Generic extension | Install a tiny test distribution with `sase_cli`, verify dispatch and nested grammar. Cover conflicts with built-in aliases, duplicate distributions, disabled plugins, unsupported API, broken import/parser, and uninstall recovery. |
| Shell completion | Exercise actual bash/zsh/fish for root `listen`, children, `--edition`, `--progress`, paths, and mutually exclusive options. Use the generated spec for TUI parity rather than separate hard-coded command tests. |
| Freshness | Warm caches before install; then install, update, remove, disable, and edit a plugin while SASE itself stays unchanged. A fresh shell and rebuilt TUI grammar must change correctly. Include same-version reinstall and a nested command-source edit. |
| Mutation coverage | Exercise CLI/TUI installs, batches, removals, required-plugin installation, refresh failure reporting, and external environment changes. Verify refresh runs in the new interpreter and leaves managed loader ownership intact. |
| Updates | A topic-derived `listen` row appears under Available/All, becomes Installed after injection, shows the new entry-point group, and supports normal update/uninstall. Include stale/offline cache behavior. |
| Automation | With only the SASE plugin installed and no standalone PATH executable, audio workflows select the same compatible plugin version. Standalone/uvx fallback and existing remote feed transport remain usable. |
| Performance and packaging | Unrelated built-ins and warm completion caches do not import sase-listen. Measure cold grammar generation, warm identity checks, and a representative plugin set. Build/install a real wheel and exercise managed plus editable environments. |

Make core-only completion snapshots hermetic. The current drift/coverage tests build the live spec; optional plugins installed on a developer’s machine must not change the expected built-in snapshot. Use an explicit core-only builder/discovery fixture for those tests, and separate fixtures for plugin grammar. [Snapshot gate](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/src/sase/completion/snapshot.py), [value coverage](https://github.com/sase-org/sase/blob/f92bde8abef2bf0191273e86c30325e12d243fad/tests/completion/test_kind_coverage.py)

## Recommended solution

**Implement a small versioned `sase_cli` provider contract with raw-argv invocation and an argparse parser factory, and register `listen` from the existing sase-listen distribution.** Reuse its current `main` and argument definitions, preserve standalone operation, and combine its parser-derived subtree with SASE’s existing completion spec. Make plugin metadata and editable grammar sources part of cache identity, and refresh managed completion automatically after every successful plugin environment change through a fresh process.

Use the Updates catalog already supplied by the `sase--plugin` topic; verify it instead of adding a special listen row. Make SASE-owned audio workflows prefer the managed `sase listen` capability while keeping standalone fallbacks and existing remote host compatibility. State the fresh-shell completion guarantee explicitly, with optional shell-native hot reload only if immediate refresh in existing shells is required. This delivers the requested experience with clear ownership, a reusable extension point, and little coupling between SASE and audio rendering.
