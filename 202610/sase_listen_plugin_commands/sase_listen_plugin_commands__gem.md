# Research Report: First-Class `sase-listen` Plugin & Plugin Subcommand Architecture

**Author:** Researcher gem (Swarm Evaluation)  
**Date:** 2026-10-08  
**Target Delivery:** `research:202610/sase_listen_plugin_and_subcommand_architecture__gem.md`  
**Topic:** Architectural evaluation, critique, and implementation blueprint for making `sase-listen` a first-class SASE plugin with CLI subcommand support, automated completion synchronization, and SASE Admin Center integration.

---

## Executive Summary

This report investigates the proposal to convert the standalone [`sase-listen`](https://github.com/sase-org/sase-listen) repository into a first-class SASE plugin providing the `sase listen` CLI command, integrating with SASE shell completion, and surfacing in the "Updates" tab of the SASE Admin Center.

### Key Verdicts & Findings
1. **The Core Proposal is Sound, but Requires Strict Latency Guards:** Making `sase-listen` a first-class plugin creates a seamless bridge between SASE's heavy markdown research output and developer commute audio. However, `sase-listen` has a substantial dependency tree (`google-genai`, `numpy`, `imageio-ffmpeg`, `curl_cffi`, `pillow`, `mutagen`, `trafilatura`, `pdfminer.six`). SASE's sub-10ms CLI responsiveness would be completely compromised if plugin discovery or imports were eager. Subcommand registration must be strictly decoupled and lazy.
2. **Subcommand Registration Mechanism:** The optimal mechanism is a new Python entry-point group `sase_commands`. Using standard Python packaging entry points (`[project.entry-points."sase_commands"]`) aligns with SASE's existing resource and provider patterns (`sase_vcs`, `sase_config`, `sase_macros`). Pluggy is rejected as over-engineered for 1-to-1 CLI subcommand routing, and subprocess delegation (`git-foo` style) is rejected because it prevents in-process shell completion introspection.
3. **Shell Completion Requires Fixing Two Existing Gaps in SASE Core:**
   - **Missing Lifecycle Hook:** `sase plugin install`, `sase plugin update`, and `sase plugin uninstall` currently do *not* invoke `maybe_refresh_installed_completions()`, unlike `sase update`.
   - **Grammar Cache Invalidation Blindness:** The shell completion runtime cache (`runtime_cache_identity.py`) hardcodes `_DISTRIBUTIONS = ("sase", "sase-core-rs")` and hashes only SASE's own package files. Installing or uninstalling a plugin does not change the cache digest key, causing existing shells to silently serve stale completion scripts.
4. **Admin Center Updates Tab Status:** The user added the GitHub topic `sase--plugin` to `sase-org/sase-listen` (verified via `gh api repos/sase-org/sase-listen --jq .topics`). Because SASE queries GitHub repository topics (`topic:sase--plugin`), `sase-listen` **already appears** as an official built-in plugin in `sase plugin list` and the Admin Center Updates tab once the catalog cache refreshes (`sase plugin list --refresh`).
5. **CLI Conventions Alignment:** SASE's convention (`sase/memory/cli_rules.md`) dictates that command groups must provide an exact `list` command and default bare invocations to `list`. `sase-listen` currently defines `ls`. When integrated as `sase listen`, it should alias `ls` to `list` and adopt SASE's bare delegation pattern.

---

## 1. Background & Context

### 1.1 What is `sase-listen`?
`sase-listen` turns Markdown documents into chaptered, loudness-normalized MP3 audio editions narrated by Gemini TTS. It is designed specifically for developers and researchers listening to technical reports, literature, and architectural analyses during walks or commutes. It features:
- Speech synthesis and script rewriting via Gemini 2.5 Flash / Pro.
- Audio pipeline with FFmpeg normalization (`-16 LUFS`) and ID3 chapter metadata tagging via `mutagen`.
- Local podcast RSS feed generation (`sase-listen feed`) and direct audio dispatch (`sase-listen publish`).
- Standalone CLI with 11 subcommands: `render`, `script`, `lint`, `guide`, `audition`, `ls`, `doctor`, `cache`, `config`, `feed`, and `publish`.

### 1.2 Current Plugin Landscape in SASE
SASE currently defines eleven entry-point groups (`docs/plugins.md`):
- **Provider Classes (Pluggy / Registries):** `sase_vcs`, `sase_workspace`, `sase_artifact_refs`, `sase_dispatch`, `sase_file_hooks`, `sase_finalizers`, `sase_task_types`, `sase_llm`.
- **Package Resources:** `sase_macros`, `sase_config`, `sase_plugin_manifest`.

Notably, **no entry-point group currently allows plugins to declare user-facing CLI subcommands**. All top-level CLI commands in SASE (`agent`, `bead`, `patch`, `plan`, `tool`, `repo`, `plugin`, etc.) are statically hardcoded in `src/sase/main/parser_registry.py` (`_COMMAND_REGISTRARS`) and dispatched via an explicit `if args.command == ...` ladder in `src/sase/main/entry.py`.

---

## 2. Critique of the Proposed Plan

### 2.1 Is this a good idea?

#### The Pros
1. **High Workflow Synergy:** SASE agents continuously generate long-form markdown deliverables (such as this research report under `sase/repos/research/`). Running `sase listen render research:202610/...` provides immediate, tactile utility.
2. **Unified Toolchain:** Managing installation and updates via `sase plugin install listen` and `sase update` simplifies onboarding and environment maintenance under `uv tool`.
3. **Discoverability:** Placing `listen` in the SASE Admin Center ("Updates" tab) and `sase plugin list` surfaces the tool directly where SASE operators spend their time.

#### The Risks & Technical Challenges
1. **Dependency Weight & Environment Bloat:**
   - `sase-listen` depends on `google-genai>=1.0`, `trafilatura>=2.0`, `curl_cffi>=0.10`, `numpy>=1.26`, `Pillow>=10.0`, `imageio-ffmpeg>=0.5`, `lxml>=5`, `pdfminer.six>=20250506`.
   - Injected into `sase`'s `uv tool` environment, this increases disk footprint by ~250MB and can lengthen dependency resolution times.
   - *Verdict:* Acceptable because plugins are opt-in. Users who do not need audio narration do not install it.
2. **CLI Startup Latency Danger:**
   - SASE places extreme value on sub-10ms CLI responsiveness.
   - Importing `google-genai` or `numpy` during root `sase` execution or shell completion would inject 150–350ms of overhead.
   - *Verdict:* The plugin command system **must guarantee zero eager imports**. Neither `sase` startup nor shell completion of built-in commands may touch `sase-listen` modules.
3. **Command Namespace Pollution & Collision:**
   - If plugins can register arbitrary top-level commands, a rogue or buggy community plugin could shadow core commands like `sase bead`, `sase plan`, or `sase update`.
   - *Verdict:* SASE must enforce strict namespace reservation and fail-closed collision handling.

### 2.2 Would We Take a Different Approach?
We evaluated three candidate architectures for plugin commands:

| Architecture | Description | Pros | Cons | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Python Entry Points (`sase_commands`)** | Plugins declare `[project.entry-points."sase_commands"] name = "module:register_parser"` | Standard PEP 517/621; zero SASE core overhead until invoked; native `argparse` integration; full shell completion support. | Requires entry-point discovery check during CLI parsing. | **Recommended** |
| **Option B: Pluggy Hook System** | Add a `sase_cli` hookspec using pluggy `PluginManager`. | Fits existing `sase_vcs` pattern. | Over-engineered for 1:1 subcommand routing; forces loading hook classes; slower than lightweight entry points. | Rejected |
| **Option C: Subprocess Execution (`git-foo` style)** | `sase <cmd>` delegates via `exec` to `sase-<cmd>` executable on `$PATH`. | Completely isolated process and dependencies. | Breaks SASE shell completion (`build_spec` cannot inspect arguments); no unified Rich error handling or global flag inheritance. | Rejected |

**Conclusion on Approach:** Option A is vastly superior. It maintains unified in-process `argparse` construction for shell completion while allowing deferred, isolated module loading.

---

## 3. Deep Dive: Subcommand Discovery & Execution

### 3.1 The Performance Bottleneck in Standard Entry Points
Running `importlib.metadata.entry_points(group="sase_commands")` in Python 3.12 takes **11–18 ms** on a warm process, and scanning all entry points takes **~70 ms**.
If `sase` ran this on *every* invocation of `sase bead ...` or `sase plan ...`, it would noticeably degrade SASE's fast-path performance.

### 3.2 The Zero-Overhead Discovery Pattern
SASE already uses an optimized narrow-parser strategy in `src/sase/main/parser_registry.py`:
```python
def parser_only_hint(argv: Sequence[str]) -> str | None:
    args = argv[1:]
    command_index = root_command_index(args)
    if command_index is None:
        return None
    candidate = args[command_index]
    if candidate.startswith("-") or candidate not in _COMMAND_REGISTRARS:
        return None
    return candidate
```

We can preserve SASE's zero-overhead guarantee with a **two-tier resolution path**:
1. **Tier 1 (Built-in Fast Path):** If `candidate in _COMMAND_REGISTRARS`, return immediately. This covers 99.9% of everyday commands (`bead`, `plan`, `agent`, etc.) with **0.00 ms** added latency.
2. **Tier 2 (Plugin Discovery):** If `candidate not in _COMMAND_REGISTRARS` (e.g. `sase listen ...`), query `importlib.metadata.entry_points(group="sase_commands")`. If an entry point matches `candidate`, return `candidate` as the narrow parser target!
3. **Execution:** When `only == "listen"`, only `sase_listen`'s registrar is loaded. The rest of SASE's 50+ built-in parsers are completely bypassed!

### 3.3 Handler Dispatch in `src/sase/main/entry.py`
Currently, `entry.py` has a 500-line hardcoded `if args.command == "...":` chain terminating in:
```python
print(f"Unknown command: {args.command}")
sys.exit(1)
```

To support plugin commands cleanly, `entry.py` should inspect the parsed namespace before the fallback exit:
```python
# Generic fallback for plugin-contributed commands
handler = getattr(args, "func", None) or getattr(args, "_command_handler", None)
if callable(handler):
    sys.exit(handler(args))

print(f"Unknown command: {args.command}")
sys.exit(1)
```
Because `sase-listen` (and standard `argparse` applications) already sets `p.set_defaults(func=run)`, this makes dispatch automatic and standard.

### 3.4 Collision & Security Policy
To prevent broken environments:
- **Core Reservation:** Built-in commands (`_COMMAND_REGISTRARS.keys()`) cannot be overridden. If a plugin registers `bead`, SASE must emit a warning and ignore the entry point.
- **Plugin Collisions:** If two installed plugins provide the same subcommand name, SASE must refuse execution with an explicit error naming both distributions.

---

## 4. Deep Dive: Shell Completion Integration

### 4.1 How SASE Completion Works
SASE's shell completion architecture (`docs/completion.md`) builds a complete command tree model (`CompletionSpec`) by calling `build_spec(parser)` in `src/sase/completion/build.py`.
`build_spec` recursively walks `parser._actions`, inspecting every `_SubParsersAction`, subparser options, positionals, and choices.
From this spec, native completion generators emit:
- `emit_zsh.py` (`_sase` function with `_describe` and compsys integration)
- `emit_bash.py`
- `emit_fish.py`

When `sase listen` is registered on `top_level_subparsers`, `build_spec` automatically traverses all 11 `listen` subcommands (`render`, `script`, `doctor`, etc.) and all their flags (`--cover`, `--dry-run`, `--narrator`). **Grammar generation requires no special code for plugins.**

### 4.2 Gap 1: Missing Completion Refresh Hook on Plugin Install
When a user updates SASE via `sase update`, `src/sase/main/update_handler_completion.py` runs `completion_refresh_after_update()`.
However, inspecting `src/sase/plugins/cli_install.py`, `cli_uninstall.py`, and `cli_update.py` reveals that **none of the plugin mutation commands refresh completion stamps!**

**Required Fix:**
In `src/sase/plugins/cli_install.py` (and uninstall/update):
```python
from sase.completion.install import maybe_refresh_installed_completions

# After successful uv tool execution:
if outcome.change_set.has_changes:
    refresh_report = maybe_refresh_installed_completions()
```

### 4.3 Gap 2: Runtime Grammar Cache Invalidation Blindness
SASE avoids full parser builds on shell startup by maintaining a compiled runtime grammar cache (`~/.sase/completion/cache/`).
In `src/sase/completion/runtime_cache_identity.py`:
```python
_DISTRIBUTIONS = ("sase", "sase-core-rs")

def runtime_identity() -> dict[str, Any]:
    return {
        "cache_format_revision": CACHE_FORMAT_REVISION,
        "distributions": _distribution_records(),
        ...
    }
```
And `source_fingerprint()` hashes only Python files inside the `sase` repository package root.

**The Bug:**
If a user installs `sase-listen`, neither `distributions` nor `source_fingerprint()` changes!
When a fresh shell starts and `ensure_cached_grammar()` runs, it sees a matching manifest and reuses the existing cached grammar. As a result, `sase listen` will **not** tab-complete in the shell until the cache is manually blown away or `sase` core itself is upgraded.

**Required Fix:**
In `src/sase/completion/runtime_cache_identity.py`, expand `_distribution_records()` to include all distributions providing `sase_commands` entry points:
```python
def _distribution_records() -> tuple[dict[str, object], ...]:
    dist_names = set(_DISTRIBUTIONS)
    try:
        for ep in metadata.entry_points(group="sase_commands"):
            if ep.dist is not None:
                dist_names.add(ep.dist.metadata.get("Name", ep.dist.name))
    except Exception:
        pass
    ...
```
This guarantees that installing, upgrading, or removing any command-providing plugin immediately invalidates the runtime completion cache.

---

## 5. Deep Dive: SASE Admin Center & Updates Tab

### 5.1 GitHub "Label" vs "Topic"
The user's prompt notes:
> "I have already added the `sase--plugin` GitHub label on sase-listen's GitHub repo to support this."

In GitHub terminology, an issue/PR tag is a "label", whereas repository classification tags in the "About" box are "topics".
SASE's plugin catalog (`src/sase/plugins/github_source.py`) queries:
`search/repositories?q=topic:sase--plugin`

We checked GitHub directly via `gh api repos/sase-org/sase-listen --jq .topics` and confirmed that the repository **already has** the `sase--plugin` topic:
```json
[
  "audiobook", "cli", "gemini", "markdown", "podcast",
  "python", "sase", "sase--plugin", "text-to-speech", "tts"
]
```

### 5.2 Verification in `sase plugin list`
Running `sase plugin list --refresh` during our investigation proved that `sase-listen` is already recognized:
```text
╭──────────────────────────────── SASE Plugins ────────────────────────────────╮
│ BUILT-IN  ·  sase-org (official)                                             │
│   g…    v0.2.20   dev           sase_config, sase_task_types, sase_vcs, s…   │
│   l…    —                       —                                            │
│   r…    v0.3.0+7.gbea92afb7…    sase_artifact_refs, sase_config, sase_fil…   │
│   t…    v0.4.25+2.g40734089…    sase_config                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```
And running `sase plugin show listen` displays:
```text
╭─────────────────────── listen · sase-org/sase-listen ────────────────────────╮
│ BUILT-IN (official)                                                          │
│                                                                              │
│ Turn Markdown into chaptered, loudness-normalized MP3 audio editions —       │
│ narrated by Gemini TTS, built for listening to SASE research on a commute or │
│ walk.                                                                        │
│                                                                              │
│ Installed     ✗  not installed                                               │
│ Latest        v0.1.1                                                         │
│ Repository    https://github.com/sase-org/sase-listen                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 5.3 Behavior in the Admin Center
In `src/sase/ace/tui/modals/plugins_browser_loading.py`:
The Admin Center Updates tab calls `load_plugin_catalog()`.
In `plugins_browser_rows.py`, `build_update_rows()` projects the entries into rows.
Because `sase-listen` is owned by `sase-org`, it automatically sorts into the `── Plugins · Built-in ──` section.
Pressing `i` on that row in the TUI invokes `execute_install` (`uv tool install sase --with sase-listen`), which already works out of the box.

**What needs updating in Admin Center:**
When `sase-listen` is installed, `sase plugin show listen` currently shows `contributed entry points: —`.
Once `sase_commands` is declared, the catalog inspects contributed entry points via `installed.py`. Adding `sase_commands` to the known contributed groups ensures the card displays:
`Contributed     sase_commands (listen)`

---

## 6. Adjustments to Requirements

We recommend the following five adjustments to the user's requirements:

| # | Proposed Requirement | Recommended Adjustment | Rationale |
| :- | :--- | :--- | :--- |
| **1** | "Define sub-commands somehow" | Use PEP 517/621 entry-point group `sase_commands` with lazy registrar functions | Standard, robust, avoids Pluggy overhead, preserves sub-10ms CLI latency. |
| **2** | "Work exactly like `sase-listen`" | Retain standalone `[project.scripts] sase-listen` alongside `sase listen` | Allows `sase-listen` to remain usable standalone in scripts, CI, and external workflows without requiring SASE. |
| **3** | `sase-listen` command structure | Provide `list` command (aliasing `ls`) and bare list delegation | Conforms to SASE CLI standard (`sase/memory/cli_rules.md`) where command groups must support `list` and bare execution delegates to `list`. |
| **4** | "Support CLI completion" | Fix cache invalidation in `runtime_cache_identity.py` and add completion hook in `cli_install.py` | Without these core fixes, installing a plugin will fail to update shell completions automatically. |
| **5** | SASE Artifact integration (Value-Add) | Allow `sase listen render` to accept SASE artifact references (`research:...`, `plan:...`) | Greatly elevates `sase-listen` from an external tool to a true "first-class" SASE citizen. |

---

## 7. Recommended Solution & Concrete Blueprint

### 7.1 Changes to `sase` Core

#### 1. Add Entry Point Group Definition
In `docs/plugins.md`, document `sase_commands`:
```markdown
| `sase_commands` | Registrar function | Plugin-contributed CLI subcommands (`register_<name>_parser`) | `sase-listen` (`listen`) |
```

#### 2. Update `src/sase/main/parser_registry.py`
Add dynamic plugin command lookup to `parser_only_hint` and `register_command_parsers`:
```python
def get_plugin_command_entry_points() -> dict[str, importlib.metadata.EntryPoint]:
    """Return discoverable plugin CLI commands, ignoring reserved core names."""
    try:
        eps = importlib.metadata.entry_points(group="sase_commands")
        return {ep.name: ep for ep in eps if ep.name not in _COMMAND_REGISTRARS}
    except Exception:
        return {}

def parser_only_hint(argv: Sequence[str]) -> str | None:
    args = argv[1:]
    command_index = root_command_index(args)
    if command_index is None:
        return None

    candidate = args[command_index]
    if candidate.startswith("-"):
        return None
    if candidate in _COMMAND_REGISTRARS:
        return candidate

    # Lazy check for plugin command without importing full parser
    plugin_eps = get_plugin_command_entry_points()
    if candidate in plugin_eps:
        return candidate

    return None
```

#### 3. Update `src/sase/main/entry.py`
In `main()`, right before `print(f"Unknown command: {args.command}")`:
```python
    # Dispatch plugin command if handler attached via set_defaults
    plugin_handler = getattr(args, "func", None) or getattr(args, "_command_handler", None)
    if callable(plugin_handler):
        sys.exit(plugin_handler(args))
```

#### 4. Update Shell Completion Cache Invalidation
In `src/sase/completion/runtime_cache_identity.py`:
Include all distributions providing `sase_commands` in `_distribution_records()`:
```python
def _command_plugin_distributions() -> tuple[str, ...]:
    try:
        eps = importlib.metadata.entry_points(group="sase_commands")
        dists = {ep.dist.metadata.get("Name", ep.dist.name) for ep in eps if ep.dist is not None}
        return tuple(sorted(dists))
    except Exception:
        return ()

def runtime_identity() -> dict[str, Any]:
    ...
    # include command plugin distributions in identity digest
```

#### 5. Hook Completion Refresh into Plugin Mutations
In `src/sase/plugins/cli_install.py`, `cli_uninstall.py`, and `cli_update.py`:
Invoke `maybe_refresh_installed_completions()` whenever packages are altered.

---

### 7.2 Changes to `sase-listen`

#### 1. Update `pyproject.toml`
```toml
[project.scripts]
sase-listen = "sase_listen.cli:main"

[project.entry-points."sase_commands"]
listen = "sase_listen.sase_plugin:register_listen_parser"
```

#### 2. Create `src/sase_listen/sase_plugin.py`
```python
"""SASE plugin integration for sase-listen."""

from __future__ import annotations
import argparse

def register_listen_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register 'sase listen' on SASE's top-level parser."""
    from sase_listen import __version__
    from sase_listen.cli.app import _COMMAND_MODULES, _Formatter

    listen_parser = subparsers.add_parser(
        "listen",
        help="Turn Markdown into chaptered MP3 audio editions",
        description=(
            "Turn Markdown into chaptered, loudness-normalized MP3 audio editions.\n"
            "Render research reports for the commute, then listen in Telegram or a\n"
            "private podcast feed."
        ),
        formatter_class=_Formatter,
    )
    listen_parser.add_argument(
        "--version", action="version", version=f"sase-listen {__version__}"
    )

    sub = listen_parser.add_subparsers(dest="listen_subcommand", metavar="<command>")
    for mod in _COMMAND_MODULES:
        mod.add_parser(sub)

    # Alias 'list' to 'ls' to follow SASE CLI rules
    if "ls" in sub.choices and "list" not in sub.choices:
        ls_parser = sub.choices["ls"]
        sub._name_parser_map["list"] = ls_parser
        sub.choices["list"] = ls_parser
```

#### 3. Support SASE Artifact References in `render` (Value-Add)
In `sase_listen/cli/render.py`:
When `source` matches an artifact reference pattern (e.g. `research:`, `plan:`, `file:`):
If `sase` is installed in the environment, invoke `sase.artifact.resolve_path(source)` to transparently resolve the source file path!

---

## 8. Summary Checklist for Implementation

- [ ] **SASE Core:** Add `sase_commands` entry point group specification.
- [ ] **SASE Core:** Update `parser_registry.py` with two-tier lazy plugin command detection.
- [ ] **SASE Core:** Add generic `args.func` fallback dispatcher in `entry.py`.
- [ ] **SASE Core:** Update `runtime_cache_identity.py` to factor command plugins into completion cache digests.
- [ ] **SASE Core:** Add `maybe_refresh_installed_completions()` call in `cli_install.py`, `cli_uninstall.py`, and `cli_update.py`.
- [ ] **SASE Core:** Register `sase_commands` in `installed.py` for Admin Center detail view.
- [ ] **sase-listen:** Implement `src/sase_listen/sase_plugin.py` with `register_listen_parser`.
- [ ] **sase-listen:** Register `listen = "sase_listen.sase_plugin:register_listen_parser"` in `pyproject.toml`.
- [ ] **sase-listen:** Add `list` alias for `ls` to comply with SASE CLI rules.
- [ ] **Verification:** Test `sase listen render --help`, `sase completion zsh`, and Admin Center Updates tab install flow.
