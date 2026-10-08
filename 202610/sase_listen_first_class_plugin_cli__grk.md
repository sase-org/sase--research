# Making sase-listen a first-class SASE plugin

**Researcher:** grk
**Date:** 2026-10-08
**Scope:** How SASE plugins, CLI dispatch, shell completion, and the Admin Center Updates tab actually work today, whether `sase-listen` should become a first-class plugin that defines `sase listen`, and the cheapest architecture that preserves both tools' existing contracts.

## Verdict

The destination is right. sase-listen belongs in the plugin catalog, on the Updates tab, and behind `sase listen`, with the standalone `sase-listen` binary kept forever.

The proposed *shape* of the work is too large in one place and too small in another:

- **Too large:** "start displaying this plugin on the Updates tab" is already done. The GitHub **topic** `sase--plugin` is on `sase-org/sase-listen`, the catalog already lists it as built-in short name `listen`, `sase plugin show listen` works, and `sase plugin install listen -n` already plans a real `uv tool install … --with sase-listen`. The Updates tab reuses that catalog. No TUI special case is required.
- **Too small:** "allow plugins to define sub-commands somehow" plus "completion is updated automatically when a plugin like this is installed" is the real platform change. Grafting sase-listen's argparse tree into `sase.main.parser.create_parser()` would break the committed completion snapshot, load the TTS stack into every `sase --help` / grammar rebuild, and still would *not* refresh completions on `sase plugin install`.

**Recommended architecture:** a host-owned **plugin CLI mount** (Docker-style metadata + Git-style exec), not an in-process argparse plugin and not a hardcoded `listen` registrar in sase. Keep sase-listen a standalone package with no `sase` import. Teach the host to exec `sase-listen` as `sase listen`, merge a cheap command spec into the *runtime* completion grammar, and include plugin CLI identity in the grammar cache key. Refresh stamped completions on plugin install/update/uninstall, not only on `sase update`.

Do **not** add sase-listen to `plugins.required` on the sase project. Do **not** put this in sase-core.

---

## 1. Plan critique

The request has four parts. They are not one feature.

| Request | Assessment |
| --- | --- |
| Make sase-listen a first-class plugin | Good idea. It is already a linked repo, on PyPI at 0.1.1, and in the catalog. "First-class" here means *optional, official, installable into sase's uv-tool env*, not "required for every sase install." |
| Let plugins define subcommands | Good idea, and it should be a generic host mechanism. Hardcoding `listen` in `_COMMAND_REGISTRARS` would ship faster and rot immediately. |
| `sase listen` works exactly like `sase-listen`, with SASE completion | Right user-facing contract, with one adjustment: parity is **the listen family's own CLI**, not sase's CLI rules (short aliases, default-`list`, `SaseArgumentParser`). |
| Show it on the Updates tab | Already true once the catalog cache has the topic. The remaining work is install/update/uninstall, which already exist. |

### 1.1 This is a good idea

sase-listen is the first sase-org tool that is a real **user-facing command family** rather than a provider, a job script, or an editor drop-in. GitHub, Telegram, nvim, and research-artifacts extend sase *inside* existing verbs (`sase stitch`, axe jobs, macros, `@research`). Listen *is* a verb. Users already type `sase-listen render …`. Putting that under `sase listen` matches how the rest of the product is invoked, and putting the package on the Updates tab matches how GitHub and Telegram are managed.

The current split is worse than it looks:

- `#research/audio` in sase-research-artifacts shells out to `sase-listen` / `uvx sase-listen` and documents `uv tool install sase-listen` as a **second** tool environment.
- This machine already has that second environment: `uv tool list` shows `sase-listen v0.1.1` next to `sase v0.17.1`.
- The plugin catalog therefore reports listen as **not installed**, because installed status is "is this distribution in *sase's* environment?", not "is there a `sase-listen` somewhere on PATH."

Installing listen *as a plugin* colocates the binary with sase (`uv tool install sase --with sase-listen`). That is a product win even before `sase listen` exists: the research-audio macros find the CLI without a second tool, and Updates/`sase plugin update` can move it.

### 1.2 I would not take the most literal implementation path

The literal reading is:

1. Invent a plugin subcommand API.
2. Teach sase-listen to use it.
3. Register `sase listen` in the host argparse tree.
4. Let completion walk that tree.
5. Add listen to the Updates tab.

Steps 3–5 as written fight the code that already exists.

**Do not register plugin commands in `create_parser()`.** The host parser is a closed, lazy registry (`src/sase/main/parser_registry.py` `_COMMAND_REGISTRARS`). Completion's committed snapshot (`tests/completion/snapshots/cli_spec.json`) is a drift gate against `build_spec()` → `create_parser()`. CI installs required plugins (`sase-github`, `sase-research-artifacts`); a developer who has sase-listen injected would regenerate a snapshot that includes `listen` and break CI, or CI would include `listen` and a machine without it would fail the gate. Plugin commands must be merged into the *runtime* grammar only.

**Do not import `sase_listen.cli.app` into the host process to build help or completion.** `build_parser()` imports every command module at module level. `cli/render.py` imports `sase_listen.pipeline`, engines, events, and Rich progress. The package depends on numpy, google-genai, trafilatura, pdfminer.six, curl_cffi, lxml, mutagen, Pillow, imageio-ffmpeg. That stack must not load on `sase --help`, `sase completion ensure`, or a grammar-cache miss. sase-listen's own `AGENTS.md` currently forbids `sase` / `sase_core_rs` imports for the same independence reason.

**Do not special-case the Updates tab.** It already renders every catalog entry. sase-nvim is the cautionary counterexample: it is documented as a plugin package in `docs/plugins.md` but its GitHub repo has **empty topics**, so `sase plugin show nvim` is "No plugin named 'nvim'". Listen already has the topic, so it already appears.

**Do not implement this in sase-core.** The rust-core-required decision keeps "Python's plugin dispatch, filesystem/process side effects, and TUI presentation" in the host. CLI mounts are exactly that. Core would only be justified later if a second frontend needed the same mount table.

### 1.3 Requirement adjustments (explicit)

These change the request. They are justified by the current code.

1. **Updates-tab display is a documentation/cache issue, not an implementation issue.** The topic is already on the repo. After `sase plugin list -r` / Updates `r`, listen is a built-in ○ row. Treat "show it on Updates" as *done*, and spend the engineering budget on CLI mount + completion identity.
2. **The registry key is a GitHub *topic*, not a *label*.** The catalog search is `topic:sase--plugin` (`src/sase/plugins/_github_source_gh.py`). Issue labels on sase-listen do not include `sase--plugin`; repository topics do. The user-facing sentence should say "topic."
3. **"Exactly like `sase-listen`" means listen's contract, not sase CLI rules.** sase CLI rules require short aliases for every public long option, alphabetically sorted subcommands, and a default `list` child. sase-listen has `ls` (stub), not `list`; many long options have no short alias; help uses rich-argparse. Forcing sase conventions onto listen is a rewrite, not a mount. Host-owned chrome (`sase -p`, `-f`/`-F`, compact root help) stays sase's; everything after `listen` stays sase-listen's.
4. **Keep the `sase-listen` console script forever.** `#research/audio`, Telegram delivery docs, and existing muscle memory all call `sase-listen`. Plugin install should *add* `sase listen`, not remove the hyphenated binary.
5. **Do not make sase-listen a required plugin of the sase project.** TTS, numpy, and ffmpeg-class deps do not belong in every sase developer's tool env. Optional, official, catalogued.
6. **Do not add a `sase` dependency to sase-listen.** Standalone `uv tool install sase-listen` must keep working for people who only want the TTS CLI. Ref resolution can continue to shell out to `sase artifact read`.
7. **Completion auto-refresh is a host bug/gap, independent of listen.** Today only `sase update` refreshes stamped completion. `sase plugin install` / `update` / `uninstall` restart the scheduler and do not touch grammar. The runtime cache identity (`src/sase/completion/runtime_cache_identity.py`) only records the `sase` and `sase-core-rs` distributions. Even a perfect argparse graft would serve a stale grammar after plugin install until something else changed sase's version or source mtime.
8. **sase-listen `AGENTS.md` is now wrong and must be edited as part of the work.** It currently says "declare no `sase_*` entry points, and do not add the `sase--plugin` topic." The topic is already on the repo. The no-sase-import rule can stay; the topic ban cannot.

---

## 2. How plugins work today

### 2.1 Three different "plugin" meanings

SASE already has three layers that the request collapses:

1. **Catalog identity** — GitHub repos with topic `sase--plugin`. This is what `sase plugin list` / `show` / the Updates tab browse. Ownership `sase-org` ⇒ built-in; anyone else ⇒ community warning. Short name is `sase-` stripped from the repo (`sase-listen` → `listen`).
2. **Installed identity** — distributions in the running (uv-tool) environment. Merge order in `src/sase/plugins/installed.py`: `sase_*` entry points, then console-script / `sase-*` distribution heuristics, then uv-receipt `--with` packages. A Neovim-only repo with the topic can appear as ○ available and correctly show as not installed.
3. **Runtime contribution** — entry points (`sase_vcs`, `sase_workspace`, `sase_llm`, `sase_macros`, `sase_config`, `sase_artifact_refs`, `sase_file_hooks`, `sase_task_types`, `sase_finalizers`, `sase_dispatch`, `sase_plugin_manifest`) plus console scripts (`sase_job_*`, `sase-listen`). **There is no `sase_cli` group.**

Listen today has (1), can gain (2) with one install command, and has a console script for (3) that the host does not mount as a subcommand.

### 2.2 What each official plugin actually is

| Package | Catalog today | Runtime contribution | Has a `sase <name>` command? |
| --- | --- | --- | --- |
| sase-github | topic present; installed in this env | VCS, workspace, config, macros, github task type | No |
| sase-telegram | topic present; installed | `sase_config` + `sase_job_tg_*` / `sase_chop_tg_*` scripts | No |
| sase-research-artifacts | topic present; installed; **required** on the sase project | `@research`, file-hook, macros, config | No |
| sase-nvim | **no topics** → absent from catalog | Lua files; no Python package | No |
| sase-listen | topic present; **not** in sase's env; separate uv tool v0.1.1 | console script `sase-listen` only | No (`sase listen` is currently `invalid choice`) |

`docs/plugins.md` "Available Plugin Packages" is already stale: it lists github/telegram/nvim and omits both research-artifacts and listen.

### 2.3 Install path already works for listen

Verified on this machine, offline catalog cache ~2 minutes old:

- `sase plugin show listen` → built-in `sase-org/sase-listen`, topics include `sase--plugin`, latest **v0.1.1**, installed ✗, hint `sase plugin install listen`.
- `sase plugin install listen -n` → would run `uv tool install --editable <sase> --with-editable <telegram> --with-editable <github> --with-editable <research-artifacts> --with sase-listen …`.

After a real install, heuristic discovery would mark it installed: `is_sase_plugin_distribution_name("sase-listen")` is true, and console script `sase-listen` matches `is_sase_plugin_console_script`. No new entry point is required for the Updates row to flip to ●.

Cost of that install: listen's dependency set (numpy, google-genai, lxml, …) enters **sase's** uv-tool environment. That is the price of "managed the same way as other plugins." It is acceptable *because the plugin is optional*. It is not acceptable as `plugins.required`.

### 2.4 Dual-install hazard

This host already has `uv tool install sase-listen` as its own tool, with a `~/.local/bin/sase-listen` shim. Plugin install injects a second copy into sase's env and may emit a second shim. uv tool shims for the same command name on PATH will surprise people.

**Adjustment:** after plugin install, document `uv tool uninstall sase-listen` for users who no longer need a separate tool. Host dispatch should prefer the console script **in sase's own environment** over a PATH binary from another uv tool, so `sase listen` and the injected plugin stay on the same version.

XDG config and library (`$XDG_DATA_HOME/sase-listen/`) are shared either way. Episodes and config survive a move from standalone tool to plugin.

---

## 3. How the host CLI and completion actually work

### 3.1 Dispatch is a closed `if args.command ==` chain

`src/sase/main/entry.py` consumes global `-p`/`-f`/`-F`, then a few fast paths (`bead`, `goal`, `completion candidates|ensure`, `run`), then `create_parser(only=parser_only_hint(argv))`, then a long alphabetized handler chain. Plugin commands cannot join that chain without a generic branch.

`parser_only_hint` returns a registrar key from `_COMMAND_REGISTRARS`. Unknown names fall through to the full parser, which then errors:

```text
sase: error: argument command: invalid choice: 'listen' (choose from 'agent', …)
```

There is no "did you mean a catalog plugin?" hint. `sase listen` today is indistinguishable from a typo.

### 3.2 Completion is a live argparse walk plus a version-keyed cache

- `sase.completion.build.build_spec()` walks `create_parser()`.
- Installed completion is a small loader + a SASE-owned runtime grammar cache (`docs/completion.md`).
- Cache identity (`runtime_identity()`) is: cache format revision, **sase** version/location, **sase-core-rs** version/location, python executable/version, package file identity.
- Source fingerprint walks `sase/__init__.py`, `sase/completion/**/*.py`, and `sase/main/**/*.py` only.
- `sase update` (live, including no-op) refreshes stamped installs. Mode switches and plugin mutations do not.
- The checked-in snapshot is a test gate, not the runtime grammar.

Implications for plugin commands:

1. Adding a command only in an installed plugin does **not** invalidate the grammar cache.
2. `sase plugin install` does **not** rewrite loaders or grammars.
3. A new shell still asks sase for the cached grammar; a cache hit skips `create_parser()`.
4. Therefore "completion updates automatically when a plugin is installed" requires **both** identity expansion **and** a refresh call from plugin mutations. Either alone is insufficient.

Dynamic value kinds (`sase completion candidates`) are a closed host list (bead, project, plugin, …). Listen does not need a new kind for v1: its useful completions are subcommands, static argparse choices (`--progress`, `--edition`), and filesystem paths (shell-native). Episode ids / narrators can wait.

### 3.3 Help surfaces

Compact `sase -h` is a curated allowlist (`_COMPACT_ROOT_COMMANDS`). Plugin commands should stay out of it.

Full `sase -H` is `parser.print_help()`. If plugin commands are not in argparse, they will not appear unless full help grows a "plugin commands" footer. That footer is worth doing; stuffing stubs into argparse to get them into `-H` is how the snapshot gate gets poisoned.

---

## 4. What sase-listen is, as a CLI

sase-listen is a complete argparse program:

- Console script: `sase-listen = sase_listen.cli:main`
- Parser: `sase_listen.cli.app.build_parser()`, `prog="sase-listen"`
- Commands: `render`, `script`, `lint`, `guide`, `audition` (stub), `ls` (stub), `doctor`, `cache` (stub), `config`, `feed`, `publish`
- Exit codes: 0, 1, 2, 3, 4, 5, 6, 130
- Agent-friendly `--json` on the important verbs
- Live Rich progress on network-bound commands
- Artifact refs via subprocess `sase artifact read`, not a Python import

It is deliberately not a sase plugin today. `docs/sase-integration.md` and `AGENTS.md` place SASE-facing work in sase-research-artifacts (`#research/audio`, research swarm audio stage) and sase-telegram (`sendAudio`). That split is still correct for *domain* integration. The missing piece is *invocation and lifecycle*: one tool env, one Updates row, one `sase listen` name.

sase-listen also still has stub commands. Mounting it under `sase listen` will surface those stubs to a wider audience. That is fine if help copy stays honest; it is not a reason to delay the mount, and it is a reason not to pretend listen is a polished sase-native command family in compact root help.

---

## 5. Options for plugin-defined subcommands

### Option A — In-process argparse registrar (`sase_cli` entry point loads a `register(subparsers)` callable)

Closest to how VCS/LLM plugins work. Host `create_parser()` loads `sase_cli` entry points and grafts trees.

**Reject for listen, and as the default for any heavy CLI.** Snapshot drift, import cost, sase-listen would need a `sase` dependency or a private argparse contract with the host, and cache identity still would not see the plugin unless separately fixed. Fine later for a *tiny* plugin command that is already in-process (a config helper, not TTS).

### Option B — Hardcoded host wrapper

Add `listen` to `_COMMAND_REGISTRARS` and `entry.py`, exec `sase-listen`.

**Reject as the platform.** Ships listen this week, teaches the next audio/editor/mobile CLI nothing, and requires a sase release for every new plugin verb. Acceptable only as a throwaway prototype.

### Option C — Git-style PATH exec only (`sase foo` → `sase-foo` on PATH)

`git stash` is builtin; `git foo` execs `git-foo`. Cargo's `cargo foo` → `cargo-foo` is the same idea. Almost no plugin API.

**Too loose for SASE.** `sase-core` is already excluded from plugin heuristics, but a random `sase-foo` on PATH would become a root command with no catalog, no Updates row, and no collision policy against `_COMMAND_REGISTRARS`. Completion for nested flags would be empty unless each binary shipped its own completions.

Use PATH exec as a **fallback** for people who still have the standalone uv tool, not as the only discovery rule.

### Option D — Docker-style CLI plugin (recommended)

Docker CLI plugins are binaries named `docker-<name>`. Docker invokes `docker-cli-plugin-metadata` and expects JSON (`SchemaVersion`, `Vendor`, `Version`, `ShortDescription`, `URL`). Help and completion see a stub; execution is a subprocess. The plugin remains a standalone binary.

Map that onto SASE:

| Docker | SASE |
| --- | --- |
| `docker-<name>` on a plugin path | console script `sase-<name>` in sase's env (and optionally PATH) |
| `docker-cli-plugin-metadata` | cheap JSON spec: name, summary, version, and a `CommandSpec` subtree (or an argv that prints one) |
| stub command in `docker --help` | stub in `sase -H` plugin-commands footer; not in compact help; not in committed snapshot |
| exec plugin with remaining argv | exec `sase-listen` with remaining argv, `prog` rewritten to `sase listen` |
| plugin stays independent | sase-listen still has no `sase` import |

Discovery should be **explicit first, heuristic second**:

1. **Explicit:** new entry point group `sase_cli`. Value is a **lightweight** module or object: command name, summary, argv to exec, optional spec callable / spec argv. Loading it must not import numpy. Add this group to `ENTRY_POINT_GROUPS` in `src/sase/plugins/inventory.py` (today that tuple still lists `sase_xprompts` and omits canonical `sase_macros` — do not copy that drift).
2. **Heuristic fallback:** an installed catalogued distribution whose console script is exactly `sase-<cmd>` (single token, not `sase_job_*` / `sase_chop_*`) mounts as `sase <cmd>` if `<cmd>` is not in `_COMMAND_REGISTRARS`. This is how listen works **before** it grows an entry point, and how a third-party CLI plugin can opt in with naming alone.

Collision policy: builtin names always win; `sase doctor -C plugins.cli` warns; the plugin command is skipped. Never let a plugin shadow `run`, `bead`, `plugin`, …

### Option E — Nested `sase plugin listen …`

Keeps the root parser closed. Wrong UX. Users will not type `sase plugin listen render`. Telegram does not live under `sase plugin telegram`. Reject.

---

## 6. Completion design for plugin commands

### 6.1 Split snapshot from runtime

- **Committed snapshot / `just sync-completion-spec`:** builtin argparse tree only. Tests keep a hermetic gate.
- **Runtime grammar:** builtin spec plus one `CommandSpec` child per mounted plugin command.
- **`sase completion spec`:** default builtin (CI-friendly). Add `--include-plugins` for debugging.

Walk plugin argparse with the existing `sase.completion.build._build_command` **in the plugin process or in an import-safe module**, then attach the resulting `CommandSpec` under `listen`. Do not walk it inside `create_parser()`.

### 6.2 How listen should expose a spec without loading TTS

sase-listen should split **parser registration** from **handler imports**. Today `add_parser` lives in the same module that imports `pipeline`. Make `add_parser` cheap (argparse only, `set_defaults(func=…)` via a string or lazy wrapper). Then either:

- `sase-listen --sase-cli-spec` (hidden, like Docker's metadata subcommand) prints JSON `CommandSpec`, or
- a tiny `sase_listen.cli.spec` module is safe to import from the host.

Prefer the hidden subcommand / JSON dump so the host never imports `sase_listen` at all. Cache the dump keyed by distribution name+version.

Honor `prog`. When SASE execs listen, set `SASE_LISTEN_PROG='sase listen'` (or argv0) so `--help` reads `sase listen render` rather than `sase-listen render`. That is the one visible difference "exactly like" should allow: the *name* in usage, not the flags.

### 6.3 Cache identity and refresh (the actual "automatic" part)

Required host changes, independent of which plugin is first:

1. Extend `runtime_identity()` with a sorted tuple of mounted CLI plugins: `(normalized_name, version, spec_digest)`.
2. Call the same `maybe_refresh_installed_completions` path from `sase plugin install` / `update` / `uninstall` after a real uv change (and after a no-op is unnecessary). Failures must not fail the plugin mutation, matching `sase update`.
3. Grammar generation must read the live mount table, not only `create_parser()`.

Without (1), (2) rewrites loaders that then load a cache still keyed as "same sase version." Without (2), (1) only helps the next `sase update` or `sase completion refresh`.

Chezmoi-owned completion sources stay loaders; they already ask the active sase for grammar. Once identity includes plugins, a new shell after install is enough *if* the cache was rebuilt. Plugin mutation should rebuild it so the user does not have to open a new shell *and* wait for a later update.

---

## 7. Updates tab and lifecycle

No new TUI widget. The Updates tab (`src/sase/ace/tui/modals/plugins_browser_pane.py`) is a master/detail inventory of core + plugin catalog + agent CLIs. Plugins rows are the CLI catalog. Listen is already a built-in Plugins row once the topic is in cache.

What "first-class" still needs on this surface:

- After install, ● and version (heuristic discovery already supports this).
- Update/uninstall via existing `U` / uninstall actions (receipt `--with` reconstruction already generic).
- Docs table in `docs/plugins.md` should list sase-listen (and sase-research-artifacts).
- Do not wait for an entry point before showing contributed groups; empty groups are already how telegram-as-scripts is described in the docs, and listen-as-console-script is the same shape until `sase_cli` exists.

Admin Center first-open is cache-only (`docs/configuration.md`). If someone's catalog cache predates the topic, Updates `r` or `sase plugin list -r` is the fix, not code.

---

## 8. sase-listen-side work (minimal)

Keep the no-sase-import rule. Change the rest of `AGENTS.md` to match reality.

Concrete listen changes:

1. Leave `sase--plugin` topic in place (already done).
2. Keep `[project.scripts] sase-listen = …`.
3. Make parser construction import-light so a spec dump is cheap.
4. Add a hidden metadata/spec dump (Docker analogue) *or* a `sase_cli` entry point that points at a metadata module containing only strings + argv. The entry point is nicer for `sase plugin show` group lists; the hidden subcommand is nicer for "host never imports us." Doing **both** is cheap: entry point names the command and the spec argv; host execs that argv.
5. Accept an env/argv0 override for `prog`.
6. Do not depend on `sase`. Do not declare VCS/LLM/macro entry points you do not implement.
7. Tests: spec dump stays stable; `main(argv)` with `prog` override; import of the spec module does not import `pipeline` / `engines`.

Host tests: a fake wheel in `tests/` with a `sase-fake` console script and a tiny spec JSON, proving mount, collision-with-builtin, snapshot unchanged, cache identity change, and install-triggered refresh.

---

## 9. Sequencing

Ship as two sase patches and one listen patch, in this order. Listen can land its spec dump in parallel with host patch 1.

**Patch 1 — host, no listen required (unblocks the catalog story people think is missing):**

- Document listen in `docs/plugins.md`.
- Unknown root command: if the name matches a catalogued short name that is not installed, print `sase plugin install <name>` instead of the 80-choice argparse dump. Cheap, uses catalog cache, helps listen *today*.

**Patch 2 — host plugin CLI mount + completion identity:**

- Mount table, pre-argparse dispatch, full-help footer, runtime grammar merge, cache identity, plugin-mutation completion refresh, doctor check, tests with a fake plugin.

**Patch 3 — sase-listen spec dump + prog override + AGENTS.md.**

**Patch 4 (optional, later):** `#research/audio` prefers `sase listen` when `sase listen render --help` works, else `sase-listen`, else `uvx sase-listen`. Not a blocker; plugin install already puts `sase-listen` on the sase tool PATH.

Do not combine 2 and 3 into "make listen a plugin" as a single epic if it can be avoided. Patch 2 is the platform. Patch 3 is the first consumer. Patch 1 is the one-day UX fix that matches the Updates-tab part of the request.

---

## 10. Risks

- **Tool-env weight.** Optional plugin install pulls numpy/TTS into sase's uv-tool env and onto `sase update` resolution time. Accept for optional; refuse for required.
- **Dual shims.** Standalone `uv tool install sase-listen` plus `--with sase-listen` can fight over `~/.local/bin/sase-listen`. Prefer same-env exec; document uninstall of the extra tool.
- **Stub commands.** `audition` / `ls` / `cache` / `doctor --online` still exit 1. Mounting them under `sase listen` does not make them real.
- **Parser-only-hint / fast path.** Dispatch must run before argparse, next to bead/goal fast paths, so `sase listen render` does not build the full host tree.
- **Global options.** `sase -p listen render …` should keep working because globals are consumed before the command token. Plugin-side `-h` is listen's. Do not steal listen's flags at the host layer.
- **Name reservation.** `listen` is free today. Freeze a host-side reserved set (builtin commands) and a plugin-side convention (`sase-<token>`).
- **sase-nvim confusion.** Docs call it a plugin but it has no topic, so it is invisible on Updates. Do not "fix" nvim in this work; do not copy its pattern.

---

## 11. Recommended solution

Implement a **generic plugin CLI mount** in the sase host, and use sase-listen as the first consumer without making sase-listen import sase.

**Host contract**

1. Discover CLI mounts from `sase_cli` entry points, then from installed `sase-<cmd>` console scripts of catalogued/receipt-owned distributions, skipping job/chop prefixes and builtin collisions.
2. In `entry.py`, before argparse: if `argv[1]` is a mount, exec that plugin (prefer the binary in sase's environment) with remaining argv and a prog override. Exit with the plugin's exit code.
3. If `argv[1]` is *not* a mount but *is* a catalogued short name that is not installed, fail with `sase plugin install <name>` (and `sase plugin show <name>`), not argparse's full choice list.
4. Keep plugin commands out of `create_parser()`, compact help, and `cli_spec.json`. Append them to `sase -H` as a "plugin commands" section when mounts exist.
5. Merge each plugin `CommandSpec` into the runtime completion grammar. Key the grammar cache on the mount table. Refresh stamped completions after plugin install/update/uninstall.

**Listen contract**

1. Remain a standalone PyPI tool with `sase-listen` on the console-scripts group and no `sase` dependency.
2. Keep the `sase--plugin` topic (already present) so Updates continues to list it as built-in `listen`.
3. Expose a cheap spec dump and honor `prog` so `sase listen --help` is listen's help with sase's name.
4. Update `AGENTS.md`: topic is required for catalog membership; `sase_cli` metadata is allowed; importing `sase` is still forbidden.

**Lifecycle**

- Users install with Updates `i` or `sase plugin install listen` (already planned by dry-run).
- Users who currently have a separate `uv tool install sase-listen` can keep it; `sase listen` should still work via PATH fallback, same-env preferred when both exist.
- Do not add listen to `plugins.required`.
- Do not implement this in sase-core.

This is the smallest design that matches how SASE already treats plugins (topic catalog, uv-receipt install, entry-point inventory), how it already treats completion (runtime grammar cache + committed snapshot), and how sase-listen already treats itself (standalone argparse CLI). The Updates tab part of the request is satisfied by work that has already landed. The new work is the mount, the spec, and the cache identity.

---

## Sources

### SASE host (this checkout)

- `docs/plugins.md` — entry-point groups, catalog topic, Updates parity, install/update/uninstall, discovery
- `docs/completion.md` — loader + runtime grammar cache; refresh after `sase update` only
- `docs/configuration.md` — Updates tab reuses the plugin catalog; first open is cache-only
- `src/sase/plugins/_github_source_gh.py` — `SASE_PLUGIN_TOPIC = "sase--plugin"`
- `src/sase/plugins/catalog.py` — short name, `find_plugin` matches `listen` / `sase-listen` / `sase-org/sase-listen`
- `src/sase/plugins/installed.py` / `src/sase/version/_plugins.py` — entry points, `sase-*` names, `sase-*` console scripts, uv receipt
- `src/sase/plugins/inventory.py` — `ENTRY_POINT_GROUPS` (no CLI group; still lists `sase_xprompts`)
- `src/sase/plugins/cli_install.py` / `cli_restart.py` — install restarts scheduler, does not refresh completion
- `src/sase/main/parser_registry.py`, `parser.py`, `entry.py`, `parser_root_help.py` — closed registrar, compact vs full help
- `src/sase/completion/build.py`, `snapshot.py`, `runtime_cache_identity.py` — argparse walk, committed snapshot, identity without plugins
- `src/sase/ace/tui/modals/plugins_browser_pane.py` — Updates tab
- `sase/sase.yml` — listen is linked, not required; required plugins are github + research-artifacts
- `tests/completion/test_snapshot.py` — snapshot drift gate

### sase-listen (linked repo)

- `AGENTS.md` — no sase import, no `sase_*` entry points, no topic (now stale vs GitHub)
- `pyproject.toml` — `sase-listen` script, no sase dep, heavy TTS/stack deps, version 0.1.1
- `src/sase_listen/cli/app.py` — argparse registry, eager command-module imports
- `src/sase_listen/cli/render.py` — pipeline/engine imports at module level
- `docs/sase-integration.md`, `docs/cli.md`, `README.md`

### Sibling plugins

- sase-github / sase-telegram / sase-research-artifacts `pyproject.toml` — entry points vs console scripts
- sase-research-artifacts macros (`research_audio.md`) — invoke `sase-listen`, not `sase listen`
- sase-nvim — Lua-only; GitHub topics empty, so absent from catalog
- sase-core `AGENTS.md` + decision `rust-core-required` — plugin dispatch stays Python

### Live checks (2026-10-08)

- `gh api repos/sase-org/sase-listen` — topics include `sase--plugin`; issue labels do not
- `gh api repos/sase-org/sase-nvim` — `topics: []`
- `sase plugin show listen` — catalogued, not installed in sase's env, latest v0.1.1
- `sase plugin install listen -n` — plans `--with sase-listen`
- `sase listen` — argparse invalid choice
- PyPI `sase-listen` 0.1.1
- `uv tool list` — separate `sase-listen v0.1.1` tool besides `sase`

### External analogue

- Docker CLI plugins: binary prefix `docker-`, hidden `docker-cli-plugin-metadata` JSON, stub in help, subprocess exec (`github.com/docker/cli/cli-plugins/metadata`, SchemaVersion `0.1.0`)
- Git / Cargo: `git-foo` / `cargo-foo` on PATH as the loose fallback, not the only rule
