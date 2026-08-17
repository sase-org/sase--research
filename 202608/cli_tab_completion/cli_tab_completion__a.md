---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# Shell completion for the `sase` command

**Research question.** What is the best way to give the `sase` CLI excellent
command-line completion, with Zsh as the quality bar and coverage of the other
common POSIX shells?

**Scope.** SASE at `ded7f1a5f` (version 0.16.0) and `sase-core` at `875309a`.
External sources were checked on 2026-08-17: shtab (`gh:iterative/shtab`, MPL-2.0),
argcomplete (`gh:kislyuk/argcomplete`), Click's completion docs, Cobra / GitHub CLI
conventions, clap_complete, uv, carapace, and jdx `usage`. This is architecture
research, not an implementation plan; no runtime behavior was changed.

## Bottom line

Ship **native, generated completion scripts** produced from the live argparse tree,
exposed as `sase completion <shell>`, and pair them with a **hidden, early-dispatch
candidate command** for live values (projects, beads, repos, and later agents).

Do **not** adopt argcomplete as the Zsh experience. Do **not** rewrite the CLI onto
Click, Typer, or clap just to get completions. Do **not** hand-maintain a `_sase`
file for a 300-node command tree. Do **not** call the ordinary `sase <group> list`
commands on every Tab.

The library that already does the hard static part well is **shtab**. It walks an
`argparse.ArgumentParser` and emits real compsys Zsh (`_arguments` + `_describe`
with help text), plus Bash, Fish, and tcsh. SASE should use it for the command and
flag tree, then own the dynamic layer that shtab cannot do excellently: described,
cached, prefix-filtered IDs that reuse catalogs SASE already has.

That combination is the only option that is simultaneously (a) excellent in Zsh,
(b) good in Bash and Fish without a second design, (c) cheap to keep in sync with
a parser that already changes often, and (d) fast enough that Tab will not feel
like launching `sase`.

## 1. What "excellent" has to mean here

For Zsh, "excellent" is not "some words appear when I press Tab." It is the compsys
experience people get from `git`, `gh`, and well-written `_arguments` scripts:

| Property | Why it matters for `sase` |
| --- | --- |
| Native compsys, not `bashcompinit` | Descriptions, grouping, `_files`, menu-complete, and approximate matching all depend on this |
| Descriptions next to values | 52 top-level commands and 1,139 options are unusable as a bare word list |
| Commands at the first token, flags only after `-` | Dumping every option on `sase <TAB>` is noise |
| Nested subcommands | `sase bead dep add <TAB>` is the normal shape of this CLI |
| `choices=` and file/dir types | 94 actions already declare choices; many positionals are paths |
| Hidden / `SUPPRESS` commands stay hidden | `sase editor helper-bridge` and retired aliases must not leak |
| Legacy aliases still complete | `patch`/`changespec`, `proc`/`task`, `stitch`/`vcs`, `artifact`/`artifact-file` |
| Dynamic IDs with descriptions | Bead id + title, **project display name** (never a ProjectSpec key), repo, plugin, flag |
| Fast | Static completion must not start Python; dynamic work must be cached and narrow |
| Installable without slowing every new shell | `eval "$(sase completion zsh)"` in `~/.zshrc` is the wrong default |
| Portable to Bash and Fish | Same spec, different emitters; Zsh is the bar, not the only shell |

Bash should be *good*: commands, flags, choices, files, and the same dynamic helper.
Fish should be *good* the same way. Elvish, Nushell, and PowerShell can wait. SASE
targets POSIX hosts (`INSTALL.md`); those shells are not part of the first contract.

"Excellent" also has a SASE-specific rule from long-term memory: user-facing text
must render configured `PROJECT_NAME:` values (`sase`, not `gh_sase-org__sase`).
Completion rows are user-facing text.

## 2. What SASE actually is today

### 2.1 A large, hand-built argparse tree — not Click, not clap

The public entry point is `sase = "sase.main.entry:main"` in `pyproject.toml`.
`src/sase/main/entry.py` builds an `argparse` tree from
`src/sase/main/parser.py` and 45 `parser_*.py` modules.

Measured against this checkout:

| Fact | Number |
| --- | --- |
| Top-level command names in `_COMMAND_REGISTRARS` | 52 |
| Distinct command nodes after walking subparsers | 331 |
| Option actions | 1,139 |
| Positional actions | 140 |
| Actions that already declare `choices=` | 94 |
| `add_parser(` call sites in `src/sase/main` | 304 |

Help is already a product: compact `sase -h` vs exhaustive `sase -H`, colored
output, alphabetized subcommands, short aliases on every public long option, and
bare groups that default to `list`. Any completion design that cannot see that
tree will rot in a week.

Plugins do **not** currently register extra argparse commands. Workspace, artifact,
and editor providers use pluggy; they do not extend the CLI grammar. Generated
completions from the live parser therefore stay complete as the tree changes,
without a plugin-completion protocol.

### 2.2 The parser is already lazy, because it is expensive

`create_parser(only=...)` exists so `sase bead …` does not import the ACE, plan,
and plugin trees. `parser_only_hint()` reads `argv[1]` and loads one registrar.

Measured with this workspace's `.venv` (CPython 3.14), importing
`sase.main.parser` and building trees:

| Step | Time |
| --- | --- |
| `from sase.main.parser import create_parser` | 78 ms |
| `create_parser()` full tree | 318 ms |
| `create_parser(only="bead")` | 3.5 ms |
| `create_parser(only="project")` | 1.1 ms |

The installed `sase` on `PATH` (`/home/bryan/.local/bin/sase`) is in the same
band for a full process:

| Command | Wall time |
| --- | --- |
| `sase version` | 325 ms |
| `sase -h` | 386 ms |
| `sase project list -j` | 170 ms |
| `sase agent list -j` | **6.9 s** |

Two consequences follow, and they disqualify several popular designs:

1. **Tab must not start the full `sase` process to complete commands and flags.**
   300 ms is sluggish; 6.9 s is a product defect.
2. **Tab must not shell out to the ordinary list commands for live values.**
   `sase agent list` is a scan, not a completer. Even `sase project list` is
   already near the edge of what a keypress can afford, and `sase bead list`
   does not even accept `-j` (it is `-f/--format json`).

`sase bead` already has an early-dispatch fast path in `entry.py` /
`bead_fast_path.py` for the same reason. Completion needs the same kind of door
in `main()`, not a second trip through argparse and the handler graph.

### 2.3 SASE already has rich completion — for documents, not argv

This work must not reinvent, or confuse itself with, the existing completion
stack:

| Surface | What it completes | Where it lives |
| --- | --- | --- |
| ACE prompt | `@` refs, `#` xprompts, `%` directives, files, agents, beads | Python TUI + `sase-core` `editor::completion` |
| xprompt LSP (`sase lsp`) | The same document grammar | `sase_xprompt_lsp` |
| `sase editor helper-bridge` | Hidden JSON catalogs for Neovim | Python bridge over Rust catalogs |
| `sase file list` | Filesystem candidates as JSON | **Imports ACE widgets** — not a shell fast path |

`sase-core` already exports `CompletionCandidate`, `CompletionList`, agent /
artifact / VCS / xprompt / file builders, and fuzzy ranking. Those catalogs are
the right **value source** for overlapping kinds (agents, artifacts, files,
xprompts, VCS repos). They are the wrong **engine** for `sase bead show <TAB>`:
that is argv-position completion against argparse, not a cursor in a document.

`sase file list` is also the wrong thing to call from Zsh. It exists for editor
integrations and pulls ACE completion widgets into process.

### 2.4 Install path is `uv tool`, not Homebrew

The documented install is `uv tool install sase`. Homebrew-style automatic
drops into `/usr/share/zsh/site-functions` will not happen for most users.
`sase init` already deploys skills and memory through chezmoi. That is the
natural place to *offer* a `_sase` file on SASE-managed machines. The portable
contract is still "print a script to stdout."

`sase doctor` already has an `integrations` group. A later check that `_sase`
is on `fpath` (or the Bash/Fish equivalent) belongs there. It should not block
`sase doctor` with `ERROR` when completions are simply not installed.

### 2.5 Tests already walk the parser

`tests/main/parser_help_helpers.py::walk_subparser_actions` and
`tests/main/test_parser_narrowing.py` already treat the argparse tree as a
stable inventory. A completion spec extracted from the same walk is in-family
with existing tests, not a new metaphysics.

## 3. The industry options, scored against SASE

### 3.1 argcomplete — reject as the Zsh design

argcomplete is the default answer people give for "argparse + Tab." It works by
re-running the program on every Tab with `_ARGCOMPLETE=1`, intercepting
execution at `argcomplete.autocomplete(parser)`, and printing candidates.

What it gets right:

- Completers attach to argparse actions (`action.completer = ...`).
- Zsh can show help strings via `_describe`.
- Bash, Fish, tcsh, and PowerShell wrappers exist.
- Dynamic completers see `prefix`, `action`, `parser`, and `parsed_args`.

Why it fails the SASE bar:

- **It starts `sase` on every Tab.** Their own README says this will feel
  sluggish if startup is not tiny. Ours is 300 ms before any completer runs,
  and a careless completer that calls `agent list` is 7 seconds.
- **Side effects before `autocomplete()` run on every Tab.** `entry.py` already
  has bead fast-path work and `sase run` special cases before argparse. Those
  would have to be proven inert under `_ARGCOMPLETE=1`.
- **The Zsh script is a Bash-shaped wrapper** (`COMP_LINE` / `COMP_POINT`, then
  `_describe`). It is better than raw `bashcompinit`, but it is not an
  `_arguments` state machine. You do not get first-class `_files`, grouped
  contexts, or the rest of compsys for free.
- **Full parser construction is required** before `autocomplete()` can answer
  `sase <TAB>`. That throws away the `only=` narrowing SASE already invested in.

argcomplete is a reasonable escape hatch for a tiny argparse script. It is the
wrong architecture for this CLI.

### 3.2 shtab — the right static engine

shtab's explicit reason for existing is "argcomplete and pyzshcomplete are slow
and have side-effects." It walks a parser object **once** and prints a shell
script. Tab then runs only shell.

What it already emits for Zsh (verified in `shtab/__init__.py::complete_zsh`):

- `#compdef ${prog}`
- `_arguments -C -s` option specs with help in `[brackets]`
- `_describe '… commands' _commands` with `name:help` rows
- Recursive functions per subcommand
- Skips `help=SUPPRESS`
- `choices=` become `(a b c)`
- `.complete = shtab.FILE` / `DIRECTORY` / `glob(...)` become `_files`
- `.complete = shtab.cmd("…")` becomes a shell command substitution
- Per-shell custom snippets plus a `preamble` for helper functions

It also generates Bash, Fish, and tcsh from the same walk. DVC is the cited
large-argparse user.

Limits that SASE must wrap, not ignore:

- `shtab.cmd("git branch")` returns bare words. No descriptions, no prefix
  sent into the command, no cache, no structured kinds.
- Custom `.complete` dictionaries are **shell-specific snippets**. That is
  fine for `_files`; it is a poor place to embed SASE domain logic 331 times.
- Eager `eval "$(shtab …)"` on every shell start is documented as possibly
  slow for complex CLIs. For SASE, generating the script is a ~400 ms
  `create_parser()` plus emit. Do that at install or `sase update`, not in
  `~/.zshrc`.
- License is **MPL-2.0**. Using it as a PyPI dependency is normal and
  acceptable. Vendoring the sources into the MIT tree would require keeping
  MPL notices on those files; prefer a dependency.

shtab is the correct *generator*. It is not, by itself, the complete product.

### 3.3 Rewrite the CLI onto Click, Typer, or clap — reject

Click (and Typer, which is Click) have polished `eval "$(_FOO_COMPLETE=zsh_source foo)"`
support and `shell_complete` callbacks. clap has `clap_complete` and the newer
`COMPLETE=zsh your_program` env integration. Cobra is how `gh` and `kubectl`
do `gh completion -s zsh`.

The migration cost is the whole CLI:

- 45 parser modules, custom `_SaseArgumentParser` validation, compact vs full
  help, default-`list` rewriting, `sase run` pre-argparse special cases, and
  the bead Rust fast path all assume argparse.
- Click's completion model still **invokes the program** to produce the
  script or the candidate list. That reintroduces the startup tax unless the
  binary is a Rust CLI.
- Moving the host CLI into `sase-core` / clap would invert the current
  boundary: Python owns host-coupled argparse and help; Rust owns domain
  execution (beads, config merge, editor catalogs). Completions are not a
  reason to relocate that boundary.

If the host CLI is ever rewritten in Rust for other reasons, `clap_complete`
becomes the obvious generator. That is a different research question.

### 3.4 Hand-written `_sase` — reject as the source of truth

A crafted Zsh file can be prettier than any generator. It cannot stay true to
1,139 options and 331 nodes that agents edit every week. The moment the
hand-written file is the source of truth, help and Tab diverge.

A **small** hand-written preamble (cache helpers, `_sase_complete_kind`,
quoting for `+1`) on top of a generated tree is the right split. A 4,000-line
`_sase` checked in as art is not.

### 3.5 Cobra-style `__complete` on every Tab — reject as the only mechanism

`gh` and `kubectl` generate a thin shell function that calls
`prog __complete <words…>` and parses `value\tdescription` lines. That is an
excellent *dynamic* protocol — **when the binary starts in tens of milliseconds.**

`sase` does not. Using `__complete` for the static tree would make every Tab
pay 300 ms plus parser construction. Using it **only** for annotated dynamic
slots, after a generated `_arguments` script has already decided *which* kind
is needed, is the Cobra idea adapted to a slow host.

### 3.6 carapace, `usage`, Fig / Amazon Q — optional later, not the design

- **carapace** is an excellent multi-shell completer binary. Requiring
  users to install it in order to Tab-complete `sase` fails the
  `uv tool install sase` onboarding story. A community spec later is fine.
- **jdx `usage`** (what mise uses) wants a KDL spec as source of truth.
  SASE's source of truth is argparse. A second spec will drift.
- **Fig / Amazon Q** are not the POSIX Zsh bar and do not replace compsys.

### 3.7 Comparison

| Approach | Zsh quality | Other shells | Stays in sync | Tab latency | Fit to SASE |
| --- | --- | --- | --- | --- | --- |
| argcomplete | Medium (`_describe` over a Bash hook) | Bash, Fish, limited others | Yes (live parser) | Poor (full process every Tab) | No |
| **shtab static + SASE candidates** | **High (`_arguments`)** | **Bash, Fish, tcsh** | **Yes (live parser)** | **High (shell-only static)** | **Yes** |
| Click / Typer rewrite | High | Bash, Fish, PowerShell | Yes | Medium (still starts the app) | No — rewrite |
| clap / Cobra rewrite | High | Broad | Yes | High if Rust-fast | No — rewrite |
| Hand-written `_sase` | Highest on day one | Must rewrite per shell | No | Highest | No — will rot |
| `__complete` for everything | High descriptions | Broad | Yes | Poor at 300 ms+ | No as sole engine |
| carapace / usage / Fig | High if someone writes the spec | Broad | Extra source of truth | High | Optional extra |

## 4. Recommended solution

### 4.1 Shape

Three pieces, deliberately separate:

```
argparse tree  ──walk──►  completion spec  ──emit──►  _sase / sase.bash / sase.fish
                                   │
                                   │ annotated slots (bead, project, file, …)
                                   ▼
                    sase completion candidates --kind K --prefix P
                                   │
                                   ▼
                    existing catalogs (Rust editor/bead/project APIs)
```

1. **Spec extraction** in Python, next to the parser tests. Walk
   `_SubParsersAction` the way `walk_subparser_actions` already does. Record
   command names, aliases, help, options (short/long, repeatable, remainder),
   `choices`, `SUPPRESS`, and an optional **completer kind** per action.
2. **Script generation** via shtab for Bash / Zsh / Fish (tcsh is free if the
   emit path stays generic). Public command: `sase completion <shell>` prints
   the script. No `eval` in the getting-started path.
3. **Dynamic candidates** via an early `entry.py` dispatch that does **not**
   call `create_parser()`. One hidden-or-quiet subcommand, something like
   `sase completion candidates`, prints `value\tdescription` lines (Zsh
   `_describe` / Cobra shape). Each kind is a small importer: project display
   names, bead id+title through the existing Rust bead read binding, repo
   names, plugin names from cache, flag keys, files through the Rust file
   completer — **not** through ACE widgets and **not** through `sase agent list`.

shtab's `.complete` hook is how the generated Zsh calls back into (3): one
shared helper, not 140 custom snippets.

```zsh
# sketched preamble the generator always includes
_sase_complete_kind() {
  local kind="$1"
  local prefix="${words[CURRENT]}"
  local -a lines
  lines=(${(f)"$(sase completion candidates --kind "$kind" --prefix "$prefix" 2>/dev/null)"})
  _describe "$kind" lines
}
```

Zsh `_store_cache` / `_cache_invalid` should wrap expensive kinds. A 30–60 s
TTL for projects and plugins is plenty. Agents, if offered at all in the first
cut, need a cache or a cheaper index; they must not trigger a 6.9 s scan.

### 4.2 Public CLI

Follow existing CLI rules (`cli_rules.md`):

- `sase completion` defaults to `sase completion list` and names the supported
  shells, matching the bare-`list` convention.
- `sase completion zsh|bash|fish` prints the script (shell is a positional,
  not a required option).
- Short aliases on any flags (`-s/--shell` only if a flag form is also
  offered; prefer the positional).
- `sase completion install` is worth adding once the generator works: write
  `_sase` into a user completions dir and tell the user the one `fpath` line
  if it is missing. Do **not** silently edit `~/.zshrc`.
- `sase completion candidates` can be public-but-quiet or `help=SUPPRESS`.
  Agents and tests need it; humans almost never do.

Do not put `eval "$(sase completion zsh)"` in `docs/getting_started.md`.
Print-and-save is the `gh` / `rustup` / `uv generate-shell-completion` lesson,
and it avoids adding ~400 ms to every new Zsh.

Suggested user-facing snippets:

```zsh
# Zsh — once, then after sase update if doctor says the script is stale
mkdir -p ~/.zfunc
sase completion zsh > ~/.zfunc/_sase
# in ~/.zshrc, before compinit:
fpath=(~/.zfunc $fpath)

# Bash
sase completion bash > ~/.local/share/bash-completion/completions/sase

# Fish
sase completion fish > ~/.config/fish/completions/sase.fish
```

On SASE-managed machines, `sase init` / chezmoi can deploy the same `_sase`
file it already deploys for skills. That is a **config/install preference**,
not a feature flag: users who want completions forever should set a setting,
not flip a beta.

A feature flag is only justified if an early land auto-installs into chezmoi
before the generator is trustworthy. Prefer shipping `sase completion` as
opt-in and unflagged, then adding install integration when the snapshots are
boring.

### 4.3 Completer kinds (annotate, do not infer everything)

Static generation already covers commands, flags, and `choices=`. The remaining
quality is a small registry so authors do not invent per-flag shell snippets.

Infer what is safe:

| Signal | Kind |
| --- | --- |
| `choices=` | those strings, with help if it is a mapping we control |
| `type=Path` / dest or metavar in `{path,file,dir}` | `file` or `directory` via `shtab.FILE` / `DIRECTORY` |
| `help=SUPPRESS` | omit |
| subparser name | command |

Declare what cannot be inferred, with a helper next to the existing
`add_argument` calls:

| Kind | First commands that need it | Source |
| --- | --- | --- |
| `project` | `project show/enable/disable`, most `-p/--project` | project records, **display name + alias**, never the spec key |
| `bead` | `bead show/close/open/update/note/dep/ref/work` | Rust bead read; `id` + title |
| `repo` | `repo path/open` | `sase repo` inventory |
| `plugin` | `plugin show/install/uninstall` | cached catalog, offline-safe |
| `flag` | `flag` group | flag registry keys |
| `agent` | `agent show/kill`, some xprompt inputs | **later**; reuse Rust agent catalog, never `sase agent list` |
| `plan` | `plan show/validate` | existing plan reference resolution |
| `artifact` | `artifact show/path/open` | existing artifact index |
| `skill` / `memory` / `xprompt` | their `show`/`read`/`run` | existing catalogs |
| `workspace` | `workspace` selectors | workspace inventory |

The first ship can stop after `project`, `bead`, `repo`, `plugin`, and files.
That is already a different product from "Tab lists subcommands." Agent
completion is the prestige kind and the latency trap; do not block the static
tree on it.

Annotation should be a tiny helper so dest names stay consistent:

```python
add_bead_id_argument(parser, "id", help="Full or shorthand issue ID")
```

That helper both `add_argument`s and sets `.complete` for shtab. Do not sprinkle
raw `shtab` types across 45 parser files if a SASE helper can own the mapping.

### 4.4 Where code should live (Rust boundary)

Litmus test from project memory: if a web app, another CLI, or the editor
needs the **same values**, the catalog is core. If only the shell needs the
**adapter**, it stays in this repo.

| Piece | Home |
| --- | --- |
| Argparse walk, shtab emit, `sase completion` | Python, `src/sase/main/` + a small `sase/cli_completion/` module |
| Zsh/Bash/Fish preambles | Python-owned templates next to the emitter |
| Bead / project / artifact / agent / file / xprompt **values** | Existing Rust bindings and catalogs; thin Python adapters |
| Document-cursor completion (ACE, LSP, nvim) | Unchanged; do not route argv completion through it |
| New `sase-core` crate just to print `_arguments` | No |

Do not implement a second bead or project lister in the completer.

### 4.5 Performance contract

Write these down as tests or doctor hints so a later agent cannot "just call
`sase agent list`":

| Event | Budget |
| --- | --- |
| Completing `sase <TAB>` / `sase bead <TAB>` / flags | Shell only; no Python |
| `sase completion zsh` (generate script) | One full `create_parser()` is acceptable (~0.4 s) |
| `sase completion candidates --kind project` | Early dispatch; well under 150 ms once imported; cache in Zsh |
| `sase completion candidates --kind bead` | Rust bead read only |
| `sase completion candidates --kind agent` | Must use a cheap catalog + cache, or do not ship the kind |

Generation belongs in `sase completion` and in `sase update` / `sase init`
refresh, not in `compinit`.

### 4.6 Testing

This is unusually testable for shell work:

- Snapshot the extracted spec (JSON) so a new command without a kind annotation
  is a visible diff, not a silent "now it completes as a file."
- Snapshot generated Zsh/Bash/Fish **or** assert stable fragments (`#compdef sase`,
  `_describe 'sase commands'`, `bead show` has a `bead` kind, `helper-bridge`
  is absent, `+1` is quoted).
- Unit-test each candidate kind: project rows are display names; bead rows are
  `id\ttitle`; prefix filtering; empty prefix returns a bounded list.
- Keep using `walk_subparser_actions` so help tests and completion tests share
  one tree walker.
- Do **not** block on interactive Zsh expect tests for the first land. Add a
  narrow one later if the preamble gets non-trivial.

### 4.7 Docs and doctor

- `docs/getting_started.md` and `docs/cli.md` gain a short "Tab completion"
  section with the print-to-`fpath` commands.
- `sase doctor` gains an advisory integrations check: script missing, script
  stale versus current generator version, or `fpath` does not include the
  install dir.
- `sase update` should refresh a previously installed script if
  `sase completion install` recorded a stamp under `~/.sase/`.

### 4.8 Suggested implementation order

This is sizing guidance for whoever plans the work, not a plan file.

1. **Static tree (the 80%).** Depend on shtab, add `sase completion list|zsh|bash|fish`,
   generate from `create_parser()`, hide `SUPPRESS`, cover aliases, snapshot tests,
   document print-to-`fpath`. Zsh first in review, Bash and Fish in the same change
   because shtab already emits them.
2. **Kinds that are cheap.** `FILE`/`DIRECTORY` annotations and `project` / `bead`
   / `repo` / `plugin` candidates on an early-dispatch command. Zsh `_describe`
   with descriptions. Cache wrapper.
3. **Install UX.** `sase completion install`, optional chezmoi deploy, doctor
   advisory, refresh on `sase update`.
4. **Prestige kinds.** Agents, artifacts, plans, `sase run` xprompt/`#`/`%`
   prefixes — reusing Rust editor catalogs, still not ACE widgets.

Step 1 alone is already a large upgrade over today (today is nothing). Step 2
is what makes it feel like `gh` rather than `ls` of subcommands.

## 5. SASE-specific pitfalls the implementation must not miss

- **`sase run` is not a normal positional.** `entry.py` special-cases it before
  argparse so prompts with spaces survive. Completing `PROMPT` as `_files` is
  acceptable at first. Completing `#xprompt` / `%directive` / `@ref` is a later
  reuse of the Rust document catalogs, not a reason to run the TUI completer.
- **`sase bead +1` is a real subcommand.** Zsh will treat `+` specially if the
  generator does not quote. Verify this in the Zsh snapshot.
- **Default-`list` groups.** Completing after `sase bead <TAB>` must offer
  `list`, `show`, `create`, … — not jump straight into `list`'s flags. shtab's
  `_describe` of subcommands is the correct behavior; do not "helpfully"
  flatten to the default child.
- **`--` remainders** (`sase proc run -- COMMAND`) must use `_arguments`
  remainder form so the completer stops claiming tokens.
- **Narrow parser vs generation.** `sase completion zsh` must call
  `create_parser()` with `only=None`. Candidate dispatch must not call it at all.
- **Workspace venvs.** Completing the `sase` on `PATH` is correct; do not bind
  the script to a workspace-local `.venv/bin/sase` that disappears.
- **No ProjectSpec keys in the menu.** Reuse `project_display_names` / resolved
  `display_name`. Keys remain identity.
- **Do not import ACE on Tab.** `sase.main.file_handler` importing
  `sase.ace.tui.widgets.file_completion` is exactly the coupling to avoid.

## 6. What was not chosen, in one paragraph each

**argcomplete.** Best dynamic API in Python, worst latency and a merely adequate
Zsh adapter. SASE's process start makes the first Tab a shrug.

**Click/Typer.** Completions would be fine on the far side of a rewrite that
nobody should schedule for this reason.

**clap / moving the host CLI to Rust.** Right generator *if* the CLI moves.
The bead Rust fast path and editor catalogs show how SASE ports *domain*
work, not the argparse host.

**Hand-written `_sase`.** Highest craft, guaranteed drift against 1,139 options.

**carapace as the required completer.** Excellent if the user already lives in
carapace; invisible if they just ran `uv tool install sase`.

**`usage` KDL or a checked-in spec as source of truth.** Argparse is already
the grammar. A second grammar is how Tab and `--help` stop matching.

## 7. Recommendation

Implement **shtab-generated native scripts for Zsh, Bash, and Fish**, printed by
`sase completion`, installed by writing `_sase` onto `fpath` (and the Bash/Fish
equivalents), and extended with a **pre-argparse `sase completion candidates`
command** for live IDs.

Treat Zsh compsys quality as the acceptance test for the generator and the
preamble. Treat Bash and Fish as the same spec, different emit. Treat dynamic
kinds as a short annotation registry over catalogs SASE already owns. Treat
process startup as a hard constraint: the static tree never starts Python, and
the dynamic path never starts ACE or `sase agent list`.

That is the smallest design that can honestly be called excellent in Zsh and
still be maintainable for this CLI.

## Sources

- This workspace: `src/sase/main/{entry,parser,parser_*.py,bead_fast_path,file_handler}.py`,
  `tests/main/parser_help_helpers.py`, `docs/cli.md`, `INSTALL.md`,
  `sase-core` `crates/sase_core/src/editor/{mod,completion,wire}.rs`
- Timed on 2026-08-17: workspace `.venv` parser construction; installed
  `/home/bryan/.local/bin/sase` for `version`, `-h`, `project list`, `agent list`
- `gh:iterative/shtab` (opened via `sase repo open`): `README.rst`,
  `docs/use.md`, `examples/customcomplete.py`, `shtab/__init__.py` Zsh emitter
- `gh:kislyuk/argcomplete` (opened via `sase repo open`): `README.rst`,
  `argcomplete/shell_integration.py`
- Click shell completion: <https://click.palletsprojects.com/en/stable/shell-completion/>
- Cobra / `gh` / `kubectl` `completion` and `__complete` convention
- uv: `uv generate-shell-completion`
- carapace: <https://carapace.sh/>
- jdx usage / mise completion docs
