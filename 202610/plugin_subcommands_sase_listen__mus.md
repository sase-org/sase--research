# First-class sase plugins with sub-commands: making `sase listen` real

Research report (mus). Goal: decide how to let sase plugins define
sub-commands, expose sase-listen as `sase listen` with working shell
completion, and surface sase-listen on the Updates tab of the SASE Admin
Center — plus a critique of the plan and a recommended solution.

All claims below were verified against the sase checkout in this workspace
and the linked sase-listen checkout unless marked as inference.

## Current state (what exists today)

### 1. The plugin system has no sub-command concept

Sase defines eleven entry-point groups (`docs/plugins.md`; inventory in
`src/sase/plugins/inventory.py`): `sase_artifact_refs`, `sase_config`,
`sase_dispatch`, `sase_file_hooks`, `sase_finalizers`, `sase_llm`,
`sase_plugin_manifest`, `sase_task_types`, `sase_vcs`, `sase_workspace`,
`sase_xprompts` (retired macro alias). None of them contributes a CLI
sub-command. The closest precedents are negative ones: `sase-telegram`
integrates via job scripts ("CLI scripts (not pluggy entry points)") and
`sase-nvim` via standalone editor files. So "plugins define sub-commands"
is genuinely new machinery, not an extension of an existing hook.

Top-level commands are statically registered in
`src/sase/main/parser_registry.py` (`_COMMAND_REGISTRARS`: module +
registrar-function pairs, lazily imported), built by `create_parser()` in
`src/sase/main/parser.py`, and dispatched by a long `if args.command == …`
chain in `src/sase/main/entry.py`. There is no fallback for unknown
commands: `sase listen` today fails at argparse with an invalid choice.
Any plugin-command design must touch all three sites (registry, parser
build, dispatch).

Two parser details matter for the design:

- `create_parser(only=…)` builds a single command tree for speed, and
  `parser_only_hint()` maps argv to that tree. It returns `None` for any
  command not in `_COMMAND_REGISTRARS`, which correctly falls back to the
  full parser — so plugin commands work without fast-path support, just
  without the fast path. A plugin-aware hint is an optimization, not a
  prerequisite.
- The `list`-defaults-to-bare-group convention (`cli_rules.md`,
  `_default_list_subcommands`) is wired centrally; a plugin group with a
  `list`-like child would inherit the behavior automatically if it goes
  through the same helpers.

### 2. Completion is generated from the live parser — good news with one hole

Shell completion is derived from the argparse tree, not from a hand-written
list: `src/sase/completion/build.py` imports `create_parser` and walks the
full parser (`create_parser(only=None)`), and the TUI Command Line grammar
is built from `sase completion spec -d -j` output cached under
`src/sase/completion/command_line_spec.py`. Consequence: **any plugin
command registered through the normal parser automatically appears in
shell completion and in the TUI command line**, provided the spec cache is
rebuilt after the plugin is installed.

The hole is cache invalidation. The spec cache key is
`runtime_identity_key() + source_fingerprint()`
(`src/sase/completion/runtime_cache_identity.py`). I read both functions:
`source_fingerprint()` hashes only `sase/__init__.py`, `sase/completion/`,
and `sase/main/`; `runtime_identity()` records only the `sase` and
`sase-core-rs` distributions. Installing, upgrading, or removing a plugin
changes neither, so **after `sase plugin install listen`, completion will
keep serving the stale pre-plugin grammar until something else invalidates
the cache**. The requirement "completion is updated automatically when a
plugin like this is installed" therefore needs explicit work (see
recommendation §5), it does not fall out of the parser design for free.

Related precedent: `sase update` already refreshes stamped shell
completions in a child process
(`src/sase/main/update_handler_completion.py`, `completion/install_refresh.py`
`refresh_stamped_completions`). Plugin install/uninstall/update perform no
equivalent refresh — I grepped `src/sase/plugins/*.py` and
`src/sase/main/plugin_handler.py` for completion hooks and found none.
They do restart the scheduler on environment change, so there is already a
post-mutation hook to hang the refresh off.

A second, smaller completion consideration: the checked-in completion-spec
snapshot gate compares a structural view of the spec. If a developer runs
that gate with plugins installed, plugin commands would churn the
snapshot. The existing `SASE_DISABLE_PLUGINS` escape hatch (honored by
`plugin_discovery.py`) gives a hermetic core-only mode; the snapshot gate
should pin that on rather than trying to model plugin contributions.

### 3. sase-listen's CLI is shaped for embedding — with one structural caveat

sase-listen (`sase/repos/linked/sase-listen`, v0.1.1, on PyPI — confirmed
live version `0.1.1`) exposes 12 sub-commands via argparse
(`render script lint guide audition ls doctor cache config feed publish
unpublish`), with one module per command under `src/sase_listen/cli/` and
an `add_parser(sub)` convention per module, assembled by `build_parser()`
in `cli/app.py` and published as the `sase-listen` console script. That
per-module `add_parser` shape maps almost one-to-one onto "register a
sub-tree under `sase listen`".

The caveat is import weight. `cli/app.py` imports all twelve command
modules at top level, and the package pulls heavy dependencies
(`google-genai`, `numpy`, `Pillow`, `imageio-ffmpeg`, `mutagen`,
`trafilatura`, …). Whatever mechanism sase uses **must not import
sase-listen code during every `sase` startup or every full-parser build**;
parser registration must live in a light module and handler bodies must
defer heavy imports to call time. This should be a stated rule of the new
plugin-command contract, not left to each plugin author to discover via a
startup-latency regression. (The completion-spec builder already builds in
a subprocess, so it can tolerate the heavier import — but interactive `sase`
dispatch cannot.)

### 4. The Updates tab is already catalog-driven — this requirement is nearly free

The Updates tab (`src/sase/ace/tui/modals/plugins_browser_pane.py`,
row model in `plugins_browser_rows.py`) renders one merged inventory from
the `sase plugin` catalog, whose registry is the GitHub `sase--plugin`
topic search (`SASE_PLUGIN_TOPIC` in
`src/sase/plugins/_github_source_gh.py`), enriched with installed-version
and PyPI-latest data. Nothing in the tab filters by org or by a hardcoded
plugin list; sections are "built-in" (official `sase-org`) vs "community".

I verified live behavior: `sase plugin show listen` currently reports "No
plugin named 'listen' in the catalog" (suggesting `github`/`telegram`).
That is the expected transient: the `sase--plugin` topic was only just
added to the sase-listen repo, and GitHub topic search needs indexing time
plus sase's catalog cache needs a refresh (`sase plugin list -r`). No code
change in sase should be needed for the Updates-tab requirement — it is a
wait-and-refresh item, with one verification step (confirm `sase plugin
show listen` resolves and the Updates tab lists it after refresh). If the
tab still omits it after indexing, that would indicate a catalog-shaping
bug worth filing, but the architecture says it will appear.

## Critique of the plan

**The direction is sound.** Plugins that can only contribute providers and
macros while shipping their own hyphenated binaries (`sase-listen`,
`sase_job_tg_*`) bifurcates the UX: discovery (`sase plugin list`),
installation (`sase plugin install`), and invocation live in three
different worlds. A plugin-command mechanism unifies all three and makes
the Updates tab the single management surface. The `sase--plugin` topic as
registry keeps working unchanged.

Three objections, in descending importance:

1. **"Work exactly like `sase-listen`" should not mean two implementations.**
   The most likely failure mode of this project is reimplementing
   sase-listen's twelve sub-commands as sase-side parser/handler code and
   then maintaining parity by hand. The correct reading — which I recommend
   adopting explicitly — is single-source: the command tree and handler
   logic live in exactly one place (the sase-listen package) and `sase
   listen` is a hosting of that implementation. Whether hosting is
   in-process (import `add_parser` + dispatch to handler funcs) or
   out-of-process (`sase listen` execs the `sase-listen` binary with argv
   passthrough) is an engineering choice (§5 recommends in-process with a
   light-registration rule, for completion fidelity), but "two copies that
   behave identically" must be rejected as an acceptance criterion and
   replaced with "one implementation reachable under both spellings".

2. **A generic mechanism is justified, but `listen` squats a generic word.**
   `sase listen` claims a top-level noun for one plugin. That is fine as
   long as the mechanism ships a collision policy from day one: core names
   are reserved, first-registered or explicit-allowlist wins, and conflicts
   fail loudly at parser build with an actionable message (not silently
   shadow). Without that, each new plugin command is a future naming
   dispute. I would also reserve the right to move genuinely-core concepts
   back (a `sase listen` that later collides with a core verb needs a
   documented migration, e.g. plugin accepts `sase audio` alias).

3. **Plugin code at parser-build time widens the trust and perf envelope.**
   Every `sase` invocation — including `sase --help`, spec builds, and
   doctests — would import third-party plugin registrars. Mitigations
   exist (lazy per-command import, the `SASE_DISABLE_PLUGINS` /
   per-group-disable convention already established in
   `plugin_discovery.py`, light-registration rule), but they must be part
   of the design, not follow-ups. Note the trust model is not new:
   `sase plugin install` already puts plugin code in sase's own uv-tool
   environment ("entry points are discovered the next time sase runs").
   Parser-time loading extends *when* that code runs, not *whether* it is
   trusted.

Smaller points: the twelve-command surface of sase-listen is large for a
first consumer of a brand-new mechanism — consider landing the mechanism
with a minimal surface first (e.g. `sase listen render/ls/doctor`) if
sase-listen can stage its `add_parser` exports, though its modular layout
makes full adoption cheap too. And `sase listen ls` vs `sase listen list`:
the central bare-group-defaults-to-`list` convention means a plugin child
literally named `list` changes bare-invocation behavior; sase-listen's use
of `ls` neatly avoids this, which is worth calling out as a convention for
future plugin authors (prefer `ls`, or accept the delegation notice).

## Adjustments to the requirements

1. Replace "work exactly like `sase-listen`" with "single implementation,
   two spellings": `sase listen …` and `sase-listen …` share one parser
   definition and one handler path owned by the sase-listen package. Add a
   conformance test that runs both spellings over `--help` and a harmless
   sub-command (e.g. `doctor` dry paths) and diffs behavior, rather than
   asserting parity by code review.
2. Make the completion requirement concrete and testable: "after `sase
   plugin install/uninstall/update`, the next `sase completion spec`
   output and the next shell-grammar `ensure` reflect the new command set
   with no manual step." That is the observable contract; "updated
   automatically" underspecifies whether install, shell reload, or first
   use triggers it.
3. Downgrade the Updates-tab item from feature to verification: no sase
   code change expected; acceptance is `sase plugin show listen` resolving
   plus a screenshot-equivalent row check after topic indexing and
   `sase plugin list -r`. Keep the bead open until that is observed, since
   catalog latency is the only risk.
4. Add two requirements the plan omits: (a) a top-level-name collision and
   reservation policy with a loud failure mode; (b) a startup-cost budget
   for plugin registrars (light registration module, heavy imports deferred
   to handler time), enforced by a test that builds the full parser with a
   fixture plugin and asserts the heavy marker was not imported.

## Recommended solution

**A. New entry-point group `sase_commands` (name bikesheddable;
`sase_cli_commands` is the only alternative I would consider).**
Each entry point names a light module exposing three members:

- `COMMAND_NAME: str` (e.g. `"listen"`),
- `register_parser(subparsers) -> None` — argparse-only, no heavy imports,
  following sase's `cli_rules.md` (sorted children, `-h` excellence,
  short option aliases),
- `handle_command(args) -> int | None` — imports heavy dependencies lazily
  inside the function or inside the sub-command `func` targets.

Sase side, three small changes mirroring the existing static registry:

1. `parser_registry.py`: after the static `_COMMAND_REGISTRARS` loop,
   enumerate `sase_commands` entry points (dedupe by value, core names
   win, collisions raise a descriptive error). Reuse
   `discover_plugin_resources()` semantics from `plugin_discovery.py`
   (sorted, skip-and-debug-log on import failure) plus the
   `SASE_DISABLE_PLUGINS` / new `SASE_DISABLE_PLUGIN_COMMANDS` guards.
2. `entry.py`: dispatch `args.command` to the plugin handler via a
   dynamic lookup after the static chain (no per-plugin `if` additions
   ever again).
3. `inventory.py` `ENTRY_POINT_GROUPS`: add the group so `sase doctor`
   and `sase version` inventory cover plugin commands; add the group to
   `docs/plugins.md`'s table with sase-listen as the example plugin.

`parser_only_hint()` needs no change for correctness (unknown → full
parser), but teaching it the plugin command names buys back the
single-tree fast path; do it if the entry-point enumeration proves cheap
enough to run pre-parse, else explicitly defer.

**B. Completion correctness in the same change, not later.**
Two halves: (1) extend `runtime_identity()`/`source_fingerprint()` in
`completion/runtime_cache_identity.py` to include the name+version+location
of distributions contributing `sase_commands` entry points, so a
plugin install/upgrade/removal naturally misses the spec cache and the TUI
Command Line grammar (same key) follows; (2) invoke the existing stamped
completion refresh (`refresh_stamped_completions`) from the shared
post-mutation path in `sase/plugins/operations.py` (covers both CLI and
Updates-tab installs, since the TUI reuses those operations), best-effort
and never aborting the install — mirroring the `sase update` refresh
pattern. Pin the completion-spec snapshot gate to `SASE_DISABLE_PLUGINS`
for hermeticity.

**C. sase-listen adopts the group; sase owns no listen code.**
sase-listen publishes a light `sase_listen.sase_plugin:COMMAND_NAME =
"listen"`, `register_parser` (reusing its existing per-module `add_parser`
functions, but importing command modules lazily inside the function to
satisfy the light-registration rule), and `handle_command` (delegating to
its existing `func(args)` dispatch). Its `pyproject.toml` adds the
`[project.entry-points."sase_commands"]` registration. `sase listen` then
behaves identically to `sase-listen` by construction, completion covers
the full twelve-command tree through the normal spec walk, and the
`sase-listen` console script stays as the standalone spelling. Staging
option if review surface matters: export a subset of sub-commands first;
the mechanism does not care.

**D. Updates tab: verify, don't build.** After topic indexing: `sase
plugin list -r`, `sase plugin show listen`, install from the Updates tab
in a scratch env, confirm row, install, update-offer, and uninstall
flows. File a bug only if any step deviates — the architecture already
routes this correctly.

Sequencing: A (mechanism + collision policy + light-registration test) →
C (sase-listen adoption + dual-spelling conformance test) → B
(cache-key + refresh hook + snapshot pinning) → D (verification after
index propagation). B can parallelize with C once A's contract is frozen.
