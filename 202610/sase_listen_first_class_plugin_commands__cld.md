---
title: Making sase-listen a first-class sase plugin (`sase listen`) — plugin-contributed CLI commands
date: 2026-10-08
researcher: cld
---

# Making sase-listen a first-class sase plugin: plugin-contributed commands, completion, and the Updates tab

## TL;DR

- **The plan is a good idea, with conditions.** Today sase-listen has no shell completion and is
  installed by hand with `uv tool install` on three machines. Making it a plugin gives it one
  install/upgrade channel: `sase update` and the Admin Center Updates tab, which also fixes the
  manual rollout pain behind `sase-1gc`. It also gets completion and discoverability for free.
- **It reverses a recorded decision.** Decision #1 of `plan:202610/sase_listen.md` says
  "standalone tool, not a sase plugin". The repo's `AGENTS.md` says the same, as do
  `docs/background.md`, `docs/getting-started.md` and `docs/sase-integration.md`.
  - **Still valid:** the reasoning behind the no-`sase`-import rule.
  - **No longer valid:** the "no entry points / no topic" part, which can be dropped safely.
  - **Must be solved first:** the PATH argument. Some real call sites assume `sase-listen` is on
    `PATH`, including the cross-machine feed publish.
- **One requirement is already met.** The `sase--plugin` marker is a repository *topic*, not a
  label, and it is set. The catalog cache I inspected (refreshed today) already lists
  `listen · sase-org/sase-listen` as a **built-in** plugin in `sase plugin list`/`show`, and
  therefore in the Updates tab. What remains is making install, installed-detection,
  capabilities and post-install side effects correct.
- **Recommended design:**
  - A new, generic, metadata-first entry-point group, `sase_commands`. The entry-point name is the
    top-level command word (`listen`); the value is a tiny adapter module in the plugin with
    `build_parser(prog)` and `main(argv, prog)`. The plugin needs zero `sase` imports.
  - sase *executes* plugin commands through an early fast path in `entry.py`, before sase's own
    argparse tree is built. That path calls the plugin's own `main()`, which guarantees
    byte-for-byte behaviour parity and avoids a ~1 s full-parser build.
  - sase *grafts* the plugin's parser into its tree only for help, completion and the TUI command
    line.
  - Completion stays fresh automatically: a `sase_commands` fingerprint goes into the completion
    runtime cache key, plus an eager refresh after plugin install/update/uninstall.
- **Adjustments I recommend, all called out in §3:**
  - Keep `sase-listen` working standalone.
  - Make sase-listen's printed hints use the invoked program name.
  - Fix the feed host's hard-coded remote `sase-listen` call.
  - Migrate the `#research/audio` xprompts to prefer `sase listen`.
  - Treat this as a generic plugin mechanism with collision rules, not a listen-specific hack.

---

## 1. What exists today (verified in code)

### 1.1 Plugin catalog and the Admin Center "Updates" tab

- The Updates tab is `PluginsBrowserPane`, registered as tab `"updates"` in
  `src/sase/ace/tui/modals/config_center_catalog.py`. It loads through
  `plugins_browser_loading.py` (`load_plugin_catalog` + `enrich_with_latest`).
  - Rows come from `plugins_browser_rows.py`; `build_plugin_row` is at `:287`.
  - The row disables install/update/uninstall when sase is not a uv-tool install.
- **The list comes from a GitHub repository *topic* search, not a label:**
  `src/sase/plugins/_github_source_gh.py:19-20` (`SASE_PLUGIN_TOPIC = "sase--plugin"`,
  `GH_SEARCH_QUERY = f"topic:{SASE_PLUGIN_TOPIC}"`).
  - Repos owned by `sase-org` are "built-in" (`src/sase/plugins/catalog.py:43`).
  - The short name is the repo name minus the `sase-` prefix, so `sase-listen` becomes `listen`.
  - The catalog is cached in `~/.sase/plugins/catalog_cache.json`; the cache is called stale
    after 7 days (`plugins/cache.py:31`).
- **Verified live state:**
  - `gh api repos/sase-org/sase-listen` shows topics
    `[…, "sase", "sase--plugin", …]`, and the repo has **no** plugin label.
  - The cached catalog (`fetched_at` today) contains `sase-listen`.
  - `sase plugin show listen` already renders "BUILT-IN (official) … Not installed — run
    `sase plugin install listen`".
  - So the "display in the Updates tab" requirement is **already satisfied by the topic**.
- **How plugins are installed:** `uv tool install sase --with <full set>` is rebuilt from the uv
  receipt (`src/sase/uv_tool/commands.py:28` `build_install`, `:84` `build_uninstall`,
  `:108` `build_upgrade_packages`). The distribution name is assumed to equal the repo name
  (`sase-listen`, which is on PyPI at 0.1.1).
- **Plugin console scripts are not put on `PATH`.**
  - The receipt at `~/.local/share/uv/tools/sase/uv-receipt.toml` lists only `from = "sase"`
    entrypoints, even though `sase-telegram`, `sase-github` and `sase-research-artifacts` are
    installed `--with`.
  - Today `sase-listen` is a **separate** uv tool (`~/.local/share/uv/tools/sase-listen`, v0.1.1).
    `~/.local/bin/sase-listen` symlinks to that tool.
  - The sase-listen plan itself recorded this fact as the reason for staying standalone
    (`plan:202610/sase_listen.md`, "`sase plugin install` … does **not** put the plugin's
    console scripts on `PATH`").
  - The `sase-11y.9` notes record the same pain for service procs ("resolve plugin console
    scripts at the…").
- **"Installed?" detection:** `plugins/installed.py:124` `build_installed_index` and `:215`
  `lookup_installed`. Any distribution whose normalized name starts with `sase-` already counts
  (`version/_plugins.py:194-214`), so sase-listen would be detected as installed with no changes.
- **Post-operation side effects:**
  - **CLI** `sase plugin install|update|uninstall` only calls `restart_after_plugin_change`
    (`plugins/cli_restart.py:19`), which restarts the scheduler.
  - **TUI** `_handle_code_update_completion`
    (`ace/tui/modals/plugins_browser_sase_update_procs.py:277`) invalidates the inventory and
    restarts the TUI.
  - **Neither one refreshes shell completion.** Only `sase update` does, via
    `completion_refresh_after_update` (`main/update_handler_completion.py:24`).
- **Inventory drift (unrelated, found along the way):**
  - `plugins/inventory.py:17-29` `ENTRY_POINT_GROUPS` still lists the retired `sase_xprompts` and
    omits the current `sase_macros` (`legacy_xprompt_syntax.py:39`) and `sase_pager_history`.
  - The capability column in `sase plugin list` comes from this tuple, which is why `listen`
    shows `—` today. It is also where a new `sase_commands` group would need to be added.

### 1.2 How the `sase` CLI is built and dispatched

- **`entry.py`:**
  - Root global options are stripped first (`consume_global_options`, which rewrites
    `sys.argv`).
  - Then come string-compare fast paths for `bead`, `goal`, `completion candidates` and
    `completion ensure`.
  - Then `create_parser(only=parser_only_hint(sys.argv))` (`entry.py:61`).
  - Then a long `if args.command == "…"` chain ending in `Unknown command` (`entry.py:637`).
- **Lazy registry:** `main/parser_registry.py:18` `_COMMAND_REGISTRARS` holds name →
  (module, function).
  - `parser_only_hint` (`:100`) narrows the build to one command tree.
  - **An unknown root word falls back to building the full parser.**
- **Measured cost on apollo** (editable sase tool env):
  - `sase plugin --help` (narrowed parser): **0.13 s**.
  - Any unknown root word (full parser build): **~1.0 s**.
  - So without a dedicated fast path, `sase listen …` would pay roughly 1 s of sase overhead on
    top of sase-listen's own ~0.55 s startup.
- **No plugin CLI hook exists.** There is no `sase_cli`/`sase_commands` group, no `parser_*.py`
  reads entry points, and no `set_defaults(func=…)` dispatch is used.

### 1.3 How completion works

- **Pure argparse introspection:** `completion/build.py:39` `build_spec()` walks
  `create_parser(only=None)._actions`. Emitters write static zsh, bash and fish grammars.
  - The TUI `:` command line feeds the same spec JSON to the data-driven Rust resolver in
    `sase-core` (`crates/sase_core/src/command_line/`). That resolver has no hard-coded command
    table.
  - Consequence: **anything registered into sase's argparse tree gets shell and TUI completion
    automatically.**
- **Installs are lazy loaders by default:**
  - The loader runs `sase completion ensure <shell>` (`completion/loader.py:119`) the first time
    `_sase` is autoloaded in a shell, i.e. on the first `sase <TAB>`.
  - `ensure` returns a cached grammar from
    `~/.sase/completion/grammar/<runtime_key>/<shell>/…`.
- **The cache key cannot see plugins:**
  - `completion/runtime_cache_identity.py:16,19-31` covers only the `sase` and `sase-core-rs`
    distributions, the sase package path, the Python executable and version, and
    `sase.__version__`.
  - `source_fingerprint()` covers only sase's own `__init__.py`, `completion/` and `main/`.
  - **Installing a plugin therefore does not invalidate the grammar.** That is the core of the
    "update completion automatically" requirement.
- **Value kinds:**
  - The kind of a value slot comes from a private attribute `_sase_completion_kind`
    (`completion/kinds.py:45,242`), else `PATH_OVERRIDES`, else `NAME_TABLE` (by dest or
    metavar).
  - `choices=` are completed natively.
  - `tests/completion/test_kind_coverage.py` requires every sase slot to have a kind, choices or
    a hint. Plugin subtrees will need an exemption or a default.
- **Tests that pin the command set:**
  - `tests/main/test_parser_narrowing.py` asserts the full parser's root commands equal
    `set(_COMMAND_REGISTRARS)`.
  - `tests/completion/snapshots/cli_spec.json` is a checked-in spec snapshot.
  - Plugin commands must be excludable from both.

### 1.4 sase-listen today

- **Argparse app:**
  - `sase_listen/cli/app.py` has `build_parser()`, which hard-codes `prog="sase-listen"`, uses
    `rich_argparse.RichHelpFormatter`, and creates subparsers with `dest="command"`.
  - It also has `main(argv=None) -> int`.
  - There are 12 subcommands: render, script, lint, guide, audition, ls, doctor, cache, config,
    feed, publish, unpublish.
- **Startup:** `sase-listen --help` takes **~0.55 s**. Importing `sase_listen.cli.app` alone
  takes **~440 ms**, because every command module is imported eagerly. Building the parser takes
  6 ms.
- **Explicit standalone stance:** `AGENTS.md` "No-sase-import rule":
  > Never import `sase` or `sase_core_rs` here, declare no `sase_*` entry points, and do not add
  > the `sase--plugin` topic.
  - The topic has already been added, so `AGENTS.md` is now out of date.
- **Hard-coded program name:**
  - 57 user-facing strings say `sase-listen <subcommand>` in hints, epilogs and errors. Examples:
    `feed.py:105` "run `sase-listen feed init`", `feedhost.py:49`
    `PENDING_HINT = "sase-listen publish --pending"`, and `script_cmd.py:74`.
- **The cross-machine feed publish assumes `sase-listen` is on the remote `PATH`:**
  `feedhost.py:163-165` builds `ssh <dest> sase-listen feed receive …`.
- **Integrations that call it by name:** sase-research-artifacts
  `xprompts/research_audio.md:34-65` ("Prefer an installed `sase-listen` … otherwise
  `uvx sase-listen`") and `xprompts/research_swarm.md:461`.
- **Dependency footprint:**
  - sase-listen pulls numpy, imageio-ffmpeg (a 77 MB bundled ffmpeg), curl_cffi (38 MB),
    google-genai, lxml, pdfminer.six and trafilatura.
  - None of these except Pillow, mutagen and httpx are in sase's tool env today.
  - The standalone sase-listen env is **310 MB**; sase's env is **132 MB**.
  - Installing the plugin adds roughly **+180 MB** to the sase env.
- **Co-resolution works:** I ran `uv pip compile` of local sase + `sase-listen==0.1.1` +
  sase-telegram + sase-github + sase-research-artifacts for Python 3.12. It resolved cleanly
  (261 pins; `rich==15.0.0`, `numpy==2.5.3`, `google-genai==2.29.0`, `sase-core-rs==0.35.1`).

---

## 2. Critique: is this a good idea?

### 2.1 What the proposal gets right

1. **One install/upgrade channel.**
   - sase-listen currently ships to athena, apollo and the Mac by hand: `sase-1g7.4` was the
     rollout, and `sase-1gc` is still open to "finish sase-listen rollout on the Mac".
   - As a built-in plugin it rides `sase update`, which runs `uv tool upgrade sase` and so
     upgrades `--with` packages too. Each machine gets the new version whenever sase updates.
   - This is the strongest practical argument for the change.
2. **Completion and discoverability are net-new value.** `sase-listen` has *no* shell completion
   today. With the grafted-parser design, `sase listen <TAB>` completes all 12 subcommands, their
   options and their `choices` (editions, progress modes, feed actions). It also shows up in the
   TUI `:` command line and in `sase -H`.
3. **A generic plugin-command hook is overdue.**
   - Plugins today can contribute LLMs, VCS, workspaces, macros, config, task types, file hooks,
     finalizers, dispatch providers and job scripts, but not a user-facing command.
   - The job-script and console-script workaround leaves executables off `PATH`, which is the
     known `sase-11y.9` pain.
   - This is a well-trodden pattern elsewhere: `llm`/datasette `register_commands`, poetry
     `application.plugin`, gh extensions discovered by the `gh-extension` topic, and
     git/cargo/kubectl `<tool>-<cmd>` executables.

### 2.2 What it reverses, and whether those reasons still hold

The plan that created sase-listen chose "standalone" for four reasons:

| Original reason | Still valid? | What to do |
| --- | --- | --- |
| "`sase plugin install` does not put console scripts on `PATH`; a CLI agents and humans invoke should be its own `uv tool install`" | **Partly.** `sase listen` fixes PATH for anyone with sase. Three real call sites still assume `sase-listen` on PATH: the feed-host SSH command, the 57 hints, and the xprompts. | Fix those call sites (R4–R6 below); keep the standalone install working for non-sase users. |
| "CI needs no sase or Rust checkouts" | **Yes, and it can be kept.** An entry point is pure packaging metadata, and the adapter needs no `sase` import. | Keep "never import sase"; relax only "no entry points / no topic". |
| "Rendering audio is not shared domain behavior" (Rust-boundary litmus) | **Yes.** Nothing about audio moves into sase or sase-core. | No sase-core changes (see §5.9). |
| "Integration lives in sibling plugins" | **Yes.** `#research/audio` stays in sase-research-artifacts; Telegram delivery stays in sase-telegram. | Only the xprompts' CLI-selection line changes. |

**Verdict:** the reversal is justified, but it should be recorded as a new decision rather than
silently contradicting `AGENTS.md` and the docs.
- In sase-listen: update `AGENTS.md`, `docs/background.md`, `docs/getting-started.md` and
  `docs/sase-integration.md`.
- In sase: consider a `decisions` strand such as "Plugins may contribute top-level commands
  through metadata-declared entry points", authored through `/sase_memory_write`.

### 2.3 Costs and risks to accept or mitigate

1. **Environment weight and coupling.**
   - About +180 MB in the sase tool env, including a bundled ffmpeg binary.
   - From then on every sase dependency pin must co-resolve with sase-listen's. It does today,
     but sase pins `pygments==2.19.2` and `resvg_py==0.3.3`, and a future pin could make
     `sase update` fail only for people who have `listen` installed.
   - Mitigation: a scheduled CI job that co-resolves sase with every built-in (`sase-org`)
     plugin. It is cheap and protects all plugins, not just this one.
   - The cost is opt-in: only users who install `listen` pay it.
2. **Two install channels during migration.**
   - A machine with both the standalone tool and the plugin has two copies that can drift.
   - The xprompts' `command -v sase-listen` would keep choosing the standalone copy.
   - The Updates tab says "not installed" while a standalone `sase-listen` is on PATH, which is
     confusing.
   - Mitigations are in R6–R7.
3. **Behaviour parity is subtle if done "the obvious way".**
   - If sase grafted sase-listen's parser into its own tree and parsed the args itself,
     sase-listen's subparser `dest="command"` would overwrite sase's root `dest="command"`.
   - I prototyped this: after `root.parse_args(["listen","render",…])`, `ns.command == "render"`,
     not `"listen"`. sase's `if args.command == …` dispatch would then fail.
   - Help formatting (rich-argparse) and error text would also differ.
   - **This is why execution must go through the plugin's own `main()`.** See §5.2.
4. **Startup.**
   - Through a fast path, `sase listen` costs about `import sase` + root-option handling + one
     entry-point scan: roughly 50–60 ms on top of sase-listen's own startup.
   - Measured: `importlib.metadata` import ≈ 60 ms (sase-listen pays this anyway for
     `__version__`) and the `entry_points(group=…)` scan ≈ 10 ms. That is acceptable.
   - Through the full parser it would be about +1 s, which is not acceptable for "works exactly
     like `sase-listen`".
5. **sase's CLI rules.**
   - `cli_rules.md` requires a short alias for every public long option. Of sase-listen's 47
     options, 36 have no short alias (for example `render --cover`, `--dry-run`, `--force`,
     `--json`).
   - Decide explicitly whether plugin-owned subtrees are exempt (my recommendation: exempt them,
     and recommend the rules to plugins) or must comply.

---

## 3. Requirement adjustments (explicitly called out)

> **R1 — "label" → "topic" (no work needed).** `sase--plugin` is a GitHub *repository topic*,
> and it is already set on sase-org/sase-listen. The catalog already lists `listen` as a
> built-in plugin. I would restate the Updates-tab requirement as: "installing `listen` from the
> Updates tab yields a working `sase listen`, correct installed/capability display, and fresh
> completion without manual steps."

> **R2 — Define "exactly like `sase-listen`" precisely.**
> - **Identical:** argv grammar, exit codes, stdout/stderr content and formatting, config and env
>   (`SASE_LISTEN_*`, XDG paths, library), and `--json` payloads.
> - **Allowed difference:** the displayed program name (`usage: sase listen …`, and hints that
>   say `sase listen …`).
> - Achieve this by **delegating to the plugin's own `main()`**, never by re-parsing in sase.

> **R3 — Make it a generic mechanism, not a listen special case.**
> - A new `sase_commands` entry-point group, with name validation.
> - Built-in names always win. Collisions are reported by `sase doctor`.
> - A `SASE_DISABLE_PLUGIN_COMMANDS` switch, consistent with the existing
>   `SASE_DISABLE_PLUGIN_*` family.

> **R4 — Keep sase-listen standalone-capable.** Keep the `sase-listen` console script and the
> "never import sase" rule. Relax only "no `sase_*` entry points / no topic", and allow exactly
> one `sase_commands` entry point.

> **R5 — Prog-aware messages in sase-listen.** The 57 hard-coded `sase-listen …` hints must
> follow the invoked program name. Otherwise a plugin-only user is told to run a binary that is
> not on their `PATH`.

> **R6 — Remove `PATH` assumptions that break a plugin-only install.**
> - The feed host's remote command (`feedhost.py:165`) should run `sase-listen` if present, else
>   `sase listen`, or be configurable.
> - `#research/audio` and `research_swarm` should prefer `sase listen`, then `sase-listen`, then
>   `uvx sase-listen`.

> **R7 — Single channel per machine during migration.** Document the one-time migration on
> athena, apollo and the Mac: `sase plugin install listen`, then `uv tool uninstall sase-listen`.
> Optionally, have `sase plugin show/list` flag "also installed as a standalone uv tool".

> **R8 — "Completion updates automatically" means key-based, not hook-based.**
> - Put the plugin-command fingerprint in the completion runtime cache key. Then *any* way of
>   changing plugins (Updates tab, `sase plugin …`, `sase update`, hand-run `uv tool install
>   --with`, uninstall) invalidates the grammar on the next shell's first `<TAB>`.
> - Add an eager refresh after plugin operations as an optimization and for stamp hygiene.
> - Accept one caveat: an *already open* zsh keeps its loaded grammar until a new shell
>   (`exec zsh`).

> **R9 (nice-to-have) — Helpful "not installed" path.** If the user runs `sase listen` without
> the plugin, use the cached catalog (offline) to print "`listen` is provided by the
> `sase-listen` plugin — run `sase plugin install listen`" instead of argparse's generic
> "invalid choice".

---

## 4. Design options considered

### Option A — In-process, metadata-declared entry-point commands (**recommended**)

- `[project.entry-points."sase_commands"] listen = "sase_listen.sase_command"`.
- sase learns command *names* from entry-point metadata alone, with no plugin import. It loads
  the adapter only when the command runs (calling `main`) or when building help/completion
  (calling `build_parser`).
- **Pros:**
  - Exact parity: the plugin's own `main`.
  - Free, accurate completion through the existing argparse walker.
  - Fits the existing `--with` install model and the Updates tab unchanged.
  - Zero sase imports in the plugin.
  - Mirrors `sase_dispatch`'s "inventoried from entry point metadata only" precedent.
- **Cons:** the plugin shares sase's venv (weight and resolver coupling, §2.3.1).

### Option B — git/gh-style external executables (`sase-<cmd>` on PATH or in sase's venv `bin/`)

- `sase listen …` execs `sase-listen …`.
- **Pros:** process isolation; a plugin could be any language.
- **Cons:**
  - Completion needs a new subprocess spec protocol (e.g. `sase-listen --sase-completion-spec`),
    versioned forever.
  - Discovery by PATH scan is ambiguous: any `sase-foo` binary becomes a command.
  - An extra interpreter start.
  - It still doesn't solve install management, because the Updates tab installs into sase's
    venv anyway.
  - gh itself never solved completion for extensions; this is the weak spot of the pattern.

### Option C — pluggy hook `register_commands(subparsers)` (llm/datasette style)

- **Pros:** familiar; sase already uses pluggy for VCS, workspaces and LLMs.
- **Cons:**
  - Every plugin must be **imported** to learn command names. That kills the fast path:
    sase-listen alone is a 440 ms import.
  - The plugin would need a pluggy dependency and hook markers.
  - The plugin's parser would be parsed by sase's parser, which brings back the `dest` collision
    and the parity problems.

### Option D — keep sase-listen standalone; teach the Updates tab to manage *separate* uv tools, and make `sase listen` exec it

- **Pros:** full isolation (no +180 MB in sase's env, no resolver coupling).
- **Cons:**
  - A new operation family: `uv tool install/upgrade/uninstall <pkg>` plus a new
    installed-detection source.
  - The receipt-centric code in `plugins/_operations_*` and `uv_tool/commands.py` assumes
    `--with`.
  - Completion again needs a cross-venv spec protocol, since sase cannot import from another
    venv.
  - `sase update` would need to learn to upgrade companion tools.
- This is the right fallback **if** dependency coupling ever becomes painful. Today co-resolution
  is clean, so it is not worth the extra machinery.

### Comparison

| | A: entry-point, in-process | B: external exec | C: pluggy hook | D: separate tool + exec |
| --- | --- | --- | --- | --- |
| Behaviour parity | exact (own `main`) | exact | weaker (sase parses) | exact |
| Completion | free via argparse walker | needs spec protocol | free | needs spec protocol |
| `sase listen` overhead | ~50–60 ms | ~+interpreter | ≥ import all plugins | ~+interpreter |
| Isolation | shared venv | shared or separate | shared venv | separate venv |
| Updates-tab fit | as-is | as-is | as-is | new install kind |
| Plugin must import sase | no | no | pluggy only | no |
| Implementation size | small–medium | medium | small | large |

---

## 5. Recommended solution (details)

### 5.1 The contract: `sase_commands` entry-point group

In the plugin's `pyproject.toml`:

```toml
[project.entry-points."sase_commands"]
listen = "sase_listen.sase_command"
```

**Contract**, a duck-typed module with no sase import:

| Attribute | Required | Meaning |
| --- | --- | --- |
| `build_parser(prog: str) -> argparse.ArgumentParser` | yes | Full parser for help and completion only. Must be cheap and side-effect free. |
| `main(argv: Sequence[str], prog: str) -> int` | yes | Runs the command and returns an exit code. |
| `SUMMARY: str` | no | One-line help for the root listing. If omitted, sase uses the distribution's `Summary` metadata (no import needed). |
| `SASE_COMMAND_API: int = 1` | no | Contract version, so sase can reject or adapt future shapes. |

**Rules enforced by sase:**
- The entry-point name must match `^[a-z][a-z0-9-]{0,31}$`.
- A name that equals a built-in command or alias (any key of `_COMMAND_REGISTRARS`) is
  **ignored** and reported by `sase doctor`.
- Duplicates across distributions resolve deterministically (first by normalized distribution
  name) and produce a doctor warning.
- `SASE_DISABLE_PLUGINS` or `SASE_DISABLE_PLUGIN_COMMANDS` turns the group off, reusing
  `is_plugin_disabled("commands")` in `main/plugin_discovery.py:35`.

**Convention (documented, not enforced):** a plugin whose catalog short name is `X` should name
its command `X`. That gives the R9 "not installed" hint for free.

### 5.2 Execution: fast path in `entry.py`

Insert this after the `completion ensure` fast path and before `create_parser` (`entry.py:61`).
Global options have already been stripped from `sys.argv` by `consume_global_options`, so
`sase -F flag listen …` also works.

```python
# entry.py (sketch)
if len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
    from .parser_registry import is_builtin_command  # name in _COMMAND_REGISTRARS

    if not is_builtin_command(sys.argv[1]):
        from .plugin_commands import try_run_plugin_command

        exit_code = try_run_plugin_command(sys.argv[1], sys.argv[2:])
        if exit_code is not None:
            sys.exit(exit_code)
```

```python
# src/sase/main/plugin_commands.py (sketch)
GROUP = "sase_commands"

def discover_plugin_commands() -> dict[str, PluginCommand]:
    """Metadata-only: name -> (entry point, dist name, version). No plugin import."""

def try_run_plugin_command(name: str, argv: list[str]) -> int | None:
    command = discover_plugin_commands().get(name)
    if command is None:
        return _maybe_print_install_hint(name)  # R9: catalog cache, offline; else None
    try:
        adapter = command.entry_point.load()
    except Exception as exc:  # broken install
        print(f"sase: '{name}' is provided by {command.dist} {command.version} "
              f"but failed to load: {exc}\n  try: sase plugin update {name}", file=sys.stderr)
        return 1
    return int(adapter.main(argv, prog=f"sase {name}"))
```

- Built-in commands pay **nothing**: one dict lookup before the existing path.
- Typos and plugin commands pay one `importlib.metadata` scan (~10 ms plus a ~60 ms import if
  not already loaded).
- As a safety net, the full parser also tags grafted plugin parsers with
  `set_defaults(_sase_plugin_command=name)`. If `entry.py` ever sees that attribute after
  `parse_args`, it re-dispatches through `try_run_plugin_command` with the original argv. That
  defends against the `dest="command"` overwrite (§2.3.3).
- Do **not** add plugin commands to `parser_only_hint` narrowing. The fast path makes it
  unnecessary.

### 5.3 Help, completion, and TUI command line: graft the parser

In `register_command_parsers` (`parser_registry.py:113`), when `only is None` and plugins are
included:

```python
plugin_parser = adapter.build_parser(prog=f"sase {name}")
sub = subparsers.add_parser(
    name,
    help=summary,
    description=plugin_parser.description,
    parents=[plugin_parser],          # public argparse API; copies options + subparsers
    add_help=False,                    # parent already carries -h/--help
    formatter_class=plugin_parser.formatter_class,
)
sub.set_defaults(_sase_plugin_command=name)
```

- I verified this against sase-listen in its venv.
  - Grafting takes 0.26 ms.
  - The walker sees `listen` plus all 12 children (render … unpublish).
  - Parsing `listen render x.md -e brief --dry-run` reaches sase-listen's `run` handler.
  - The same experiment also showed the `ns.command` overwrite, which is why parsing stays the
    plugin's job.
- **Failure handling:** if `load()` or `build_parser()` raises, skip the command, log at debug
  level, and let `sase doctor` report it. Completion generation must never fail because of a
  plugin.
- `create_parser(only=None, include_plugins=True)` is the default. Snapshot tooling
  (`tools/sync_completion_spec`), `test_parser_narrowing` and `test_kind_coverage` call it with
  `include_plugins=False`.
- **Value kinds for plugin slots:**
  - `choices` already work.
  - For path-like positionals, honour a **public, string-valued, duck-typed** attribute, e.g.
    `action.sase_completion = "path"` (or `"dir"`). sase coerces it to `ValueKind`, so plugins
    never import `sase.completion.kinds`.
  - Slots without a kind default to a `text` hint, and the coverage test exempts plugin
    subtrees.
  - For sase-listen: `render source`, `script source`, `lint script` → `"path"`.
- **Run policy:** the default `proc` for leaves (`completion/run_policy.py`) is fine for
  `sase listen render` in the TUI `:` line. sase-listen already degrades its live checklist with
  `--progress plain`.
- **Root help:** `sase -H` lists plugin commands automatically.
  - Optionally add a "Plugin commands:" line to the compact `sase -h`.
  - Build that line from metadata (name + dist `Summary`), so plain `sase -h` never imports
    plugins.

### 5.4 Keep completion fresh automatically (R8)

1. **Cache key.**
   - Extend `runtime_identity()` (`completion/runtime_cache_identity.py:19`) with a
     `plugin_commands` record: a sorted tuple of
     `{name, value, dist, version, location}` for the `sase_commands` group.
   - Also include the `SASE_DISABLE_PLUGIN(S|_COMMANDS)` state, and bump
     `CACHE_FORMAT_REVISION`.
   - Because `runtime_identity_key` also partitions the TUI command-line spec cache
     (`command_line_spec-<runtime_key>-…json`), the TUI `:` line follows for free.
   - Cost: about 10 ms in `completion ensure`, which already imports `importlib.metadata` for
     `_distribution_records`. It runs once per shell, on the first `sase <TAB>`.
2. **Eager refresh.**
   - Call `completion_refresh_after_update` (`main/update_handler_completion.py:24`) next to
     `restart_after_plugin_change` in `plugins/cli_install.py`, `cli_update.py` and
     `cli_uninstall.py`.
   - Also call it from the TUI `_handle_code_update_completion` and the in-process batch-install
     path.
   - This rebuilds stamped installs (including any non-loader install), keeps
     `sase completion list` from reporting drift, and makes the next shell's first `<TAB>`
     instant.
3. **Known limitation:** an editable plugin whose parser changes without a version bump is not
   detected.
   - A precise fingerprint would need the plugin module's path. Resolving it via `find_spec`
     imports `sase_listen.cli/__init__`, which costs 440 ms. Not worth it in v1.
   - Document "run `sase completion refresh` after editing a plugin's CLI in an editable
     checkout".

### 5.5 Updates tab and plugin inventory

- **Listing:** done (R1). There is no code change for display.
- **Capabilities:**
  - Add `sase_commands` to `plugins/inventory.py` `ENTRY_POINT_GROUPS` as a provider-style
    (metadata-only, not loaded) group. `listen` then shows `sase_commands` instead of `—`.
  - While there, fix the drift: add `sase_macros` and `sase_pager_history`, and drop or retire
    `sase_xprompts`.
  - In `sase plugin show listen` and the Updates-tab detail, render "Commands: `sase listen`".
- **Install/update/uninstall:** unchanged. `sase plugin install listen` resolves the
  distribution `sase-listen` from PyPI and rebuilds the `--with` set. Post-operation, add the
  completion refresh (§5.4.2).
- **Optional (R7):** when a catalog entry's repo also exists as a standalone uv tool (the
  `uv tool list` / `~/.local/share/uv/tools/<repo>` receipt), show "also installed as a
  standalone uv tool (vX) — `uv tool uninstall <repo>` after installing the plugin". This is
  generic and cheap, and it removes the main migration confusion.
- **`sase doctor`:** add a "plugin commands" check covering:
  - invalid names;
  - collisions with built-ins or other plugins;
  - `load()` / `build_parser()` failures;
  - `SASE_COMMAND_API` mismatches.

### 5.6 sase-listen changes (no `sase` import anywhere)

1. **`pyproject.toml`:** add the `sase_commands` entry point (`listen =
   "sase_listen.sase_command"`).
2. **New `src/sase_listen/sase_command.py`** (a thin adapter that imports the app lazily):

   ```python
   """`sase listen` adapter (sase_commands entry point). Never imports sase."""
   from __future__ import annotations

   import argparse
   from collections.abc import Sequence

   SASE_COMMAND_API = 1
   SUMMARY = "Turn Markdown into chaptered, loudness-normalized MP3 audio editions."


   def build_parser(prog: str) -> argparse.ArgumentParser:
       from sase_listen.cli.app import build_parser as _build

       return _build(prog=prog)


   def main(argv: Sequence[str], prog: str) -> int:
       from sase_listen.cli.app import main as _main

       return _main(argv, prog=prog)
   ```

3. **`cli/app.py`:** change to `build_parser(prog: str = "sase-listen")` and
   `main(argv=None, *, prog="sase-listen")`.
   - `main` records the display program in a tiny leaf module, e.g. `sase_listen/invocation.py`
     with `display_prog()`.
   - Replace the 57 `sase-listen <cmd>` literals in hints, epilogs and errors with
     `f"{display_prog()} <cmd>"` (R5).
   - The `--version` string becomes `f"{prog} {__version__}"`.
4. **`feedhost.py:163-165`** (R6): build the remote command as a POSIX snippet that prefers
   `sase-listen` and falls back to `sase listen`. For example
   `sh -c 'if command -v sase-listen >/dev/null; then exec sase-listen "$@"; else exec sase listen "$@"; fi' sase-listen feed receive …`.
   Optionally add a `feed.remote_command` config override. Keep the existing "too old to
   receive" detection working for both forms.
5. **Docs:** update `AGENTS.md` and `docs/background.md`, `getting-started.md` and
   `sase-integration.md`.
   - Two install paths:
     - `sase plugin install listen` (Updates tab), which gives `sase listen`;
     - standalone `uv tool install sase-listen`, which gives `sase-listen` for non-sase users.
   - The rule becomes "never import sase; the only sase coupling is the `sase_commands` entry
     point and the topic".
   - Reference the superseding decision.
6. **Contract tests (no sase needed):**
   - `importlib.metadata.entry_points(group="sase_commands")` contains `listen` in the dev env.
   - The adapter exposes the contract.
   - `main(["--help"], prog="sase listen")` prints `usage: sase listen`.
   - `main(["render", …, "--dry-run"], prog="sase listen")` returns the same code and output as
     the default prog, apart from the program name.
7. **Optional performance work, a win in both modes:** import the command modules lazily inside
   each `func`. This cuts the ~440 ms import for `--help`, completion builds and the `sase listen`
   path.

### 5.7 Integrations and machines

- **sase-research-artifacts** `xprompts/research_audio.md` and `research_swarm.md`:
  - CLI selection order becomes: `sase listen` (if `sase listen render --help` advertises
    `--generated-cover`), else `sase-listen`, else `uvx sase-listen`.
  - Keep "the plugin never depends on sase-listen".
- **sase-telegram:** no change. It only routes `.mp3` to `sendAudio`.
- **Machines (athena, apollo, Mac):**
  1. `sase plugin install listen`.
  2. Verify with `sase listen doctor`.
  3. `uv tool uninstall sase-listen`.
  4. Re-check `sase listen publish` to the feed host once R6 has shipped. Until then, keep the
     standalone tool on the feed host.
  - `sase-1gc` (Mac rollout) is a natural place to do the Mac step.

### 5.8 sase-side tests and docs

- **Unit tests:**
  - discovery (name validation, built-in collision, duplicates, disable env);
  - fast-path dispatch (exit-code passthrough, load-failure message, global-options-before-command);
  - graft and walker (spec contains the plugin subtree when included, excludes it when not);
  - the runtime-identity key changes when a fake `sase_commands` entry point appears or
    disappears;
  - post-operation completion refresh is invoked.
- Use a fake in-repo distribution or a monkeypatched `entry_points` so the tests never depend on
  sase-listen.
- **Docs:**
  - `docs/plugins.md`: the group table (eleven → twelve groups), a new "Example: Command Plugin",
    `SASE_DISABLE_PLUGIN_COMMANDS` in "Disabling Plugins", and sase-listen in "Available Plugin
    Packages".
  - `docs/cli.md`: plugin commands.
  - The completion docs: "plugin installs invalidate the grammar; open shells need `exec $SHELL`".
- **Memory:** consider a `decisions` record, and a line in `cli_rules.md` on whether plugin
  subtrees must follow the short-alias rule (my recommendation: recommend, don't require). Both
  go through `/sase_memory_write`.

### 5.9 Rust core boundary

Nothing moves to `sase-core`.
- Plugin command discovery and dispatch are Python CLI glue.
- The TUI and other frontends consume the command grammar through the existing
  `sase completion spec` JSON. The Rust `command_line` resolver is data-driven, with no command
  table, so it gets `listen` for free once the spec includes it.
- Audio rendering stays in sase-listen, per the original litmus-test reasoning.

### 5.10 Suggested phasing

1. **sase: core mechanism.**
   - `plugin_commands.py` (discovery + fast path + R9 hint).
   - Graft into the full parser with an `include_plugins` switch.
   - Test isolation.
   - Doctor check.
   - Inventory group fix.
   - Docs.
2. **sase: completion freshness.** The runtime-identity fingerprint, plus eager refresh after
   CLI and TUI plugin operations.
3. **sase-listen:** entry point + adapter, prog-aware hints, feed-host remote fallback, docs and
   AGENTS update, contract tests, release (0.2.0).
4. **sase-research-artifacts:** xprompt CLI-selection order.
5. **Rollout:** install the plugin on each machine and retire the standalone tools (feed host
   last).
6. *(Optional)* Lazy command imports in sase-listen; a "Plugin commands" line in compact
   `sase -h`; the standalone-tool hint in the Updates tab; scheduled co-resolution CI for
   built-in plugins.

---

## 6. Open questions for Bryan

1. **CLI rules for plugin commands:** may plugin subtrees keep their own option style (36 of 47
   sase-listen options have no short alias), or should `sase listen` comply with `cli_rules.md`?
   I recommend exempting plugin subtrees.
2. **Feed host:** is apollo (the feed host) going plugin-only too? If yes, R6 must ship before
   apollo's standalone tool is removed.
3. **Weight:** is roughly +180 MB in sase's tool env acceptable on the Mac? It is opt-in per
   machine. If not, Option D is the escape hatch.
4. **Should the Updates tab ever expose plugin executables on `PATH`?** That would mean using
   uv's `--with-executables-from`, which uv 0.11.8 supports. I recommend **no** for now. It
   conflicts with an existing standalone `~/.local/bin/sase-listen` link (uv refuses to
   overwrite another tool's executable without `--force`), and `sase listen` already covers the
   use case.

---

## 7. Discovered issues (not filed as beads, to avoid duplicates across this five-researcher swarm; the lead may file them)

- `src/sase/plugins/inventory.py:17-29` `ENTRY_POINT_GROUPS` lists the retired `sase_xprompts`
  and omits `sase_macros` and `sase_pager_history`.
  - Effects: wrong capability columns in `sase plugin list`.
  - A plugin that only exposes `sase_macros` and is not named `sase-*` would not be counted as
    installed.
- sase plugin install/update/uninstall (CLI and TUI) never refresh shell completion, and the
  completion runtime key ignores plugins. This is a latent staleness bug today for any
  plugin-provided completion values.
- sase-listen's `src/sase_listen/cli.py` is shadowed by the `cli/` package (dead file).

---

## 8. Recommended solution

Adopt **Option A**: metadata-declared, in-process plugin commands through a new generic
`sase_commands` entry-point group. Ship sase-listen as its first user, under the adjusted
requirements R1–R9.

- **Plugin contract.**
  - The plugin declares `listen = "sase_listen.sase_command"` under
    `[project.entry-points."sase_commands"]`.
  - It exposes `build_parser(prog)` and `main(argv, prog)` (plus optional `SUMMARY` and
    `SASE_COMMAND_API`).
  - It still never imports sase, so its CI and standalone `uv tool install sase-listen` keep
    working.
- **Execution.**
  - `entry.py` gets a fast path for non-built-in root words: a metadata-only discovery that loads
    the adapter and returns `main(argv, prog="sase listen")`.
  - This gives exact behaviour parity and ~50–60 ms overhead instead of the ~1 s full-parser
    path.
  - It avoids the proven `dest="command"` collision.
  - Built-in names always win; collisions and load failures go to `sase doctor`.
  - With no provider installed, sase prints an offline "install with
    `sase plugin install listen`" hint.
- **Help, completion and TUI.**
  - The full parser grafts each plugin parser with `add_parser(name, parents=[plugin_parser],
    add_help=False)`, so the existing argparse walker, the zsh/bash/fish emitters and the Rust
    TUI command line pick it up unchanged.
  - Plugins are excluded from snapshot and registry tests.
  - Value kinds come from `choices` and a public string attribute, `sase_completion`.
- **Automatic completion freshness.**
  - A `sase_commands` fingerprint (name, value, dist, version, location, disable env) goes into
    `runtime_identity()`, so any plugin change invalidates the grammar and the TUI spec on the
    next first `<TAB>`.
  - An eager `completion_refresh_after_update` runs after every CLI and TUI plugin operation.
- **Updates tab.**
  - Already listed, since the topic is set.
  - Add `sase_commands` (and the drifted `sase_macros` and `sase_pager_history`) to the
    inventory groups, show "Commands: `sase listen`", refresh completion after operations, and
    optionally flag a duplicate standalone uv-tool install.
- **sase-listen follow-through.**
  - Prog-aware hints, and a feed-host remote command that falls back to `sase listen`.
  - Updated AGENTS and docs recording that the standalone decision is superseded, plus contract
    tests.
- **Integrations and rollout.**
  - The research xprompts prefer `sase listen`.
  - Then migrate each machine to the plugin install, retiring the standalone tool on the feed
    host last.

This delivers what was asked (`sase listen` == `sase-listen`, with completion that
self-updates, managed from the Updates tab). It also leaves sase with a reusable, cheap and safe
way for any plugin to contribute a command, and it gives up nothing the original standalone
decision was protecting except a separate venv. If that venv separation ever matters, Option D is
the escape hatch.

---

### Appendix: measurements (apollo, 2026-10-08, editable sase uv-tool env, Python 3.12)

| Measurement | Value |
| --- | --- |
| `sase-listen --help` / `--version` wall time | 0.52–0.67 s |
| `import sase_listen.cli.app` / `build_parser()` | 442 ms / 6 ms |
| `sase plugin --help` (narrowed parser) | 0.13–0.14 s |
| unknown root word (full parser build + error) | ~1.0 s |
| `import sase` | ~40 ms over a 20 ms interpreter baseline |
| `import importlib.metadata` (cold) / `entry_points(group=…)` scan | ~60 ms / ~10 ms (56 dists) |
| argparse graft of sase-listen parser via `parents=` | 0.26 ms; 12 subcommands visible to walker |
| env sizes: sase tool env / standalone sase-listen env | 132 MB / 310 MB |
| largest sase-listen deps absent from sase env | imageio-ffmpeg 77 MB, curl_cffi 38 MB, numpy 33 MB, lxml 12 MB, pdfminer 8.5 MB, google 7.8 MB |
| `uv pip compile` sase + sase-listen 0.1.1 + 3 sibling plugins | resolves (261 pins) |
