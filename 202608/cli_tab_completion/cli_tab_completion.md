---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# Tab completion for the `sase` CLI

**Research question.** What is the best way to give the `sase` command excellent
command-line completion — first-class in Zsh, good in the other common shells?

**Scope.** SASE at `ded7f1a5f` (v0.16.0), CPython 3.14, zsh 5.9, on `athena`,
2026-08-17. Consolidates two independent reports ([`__a`](cli_tab_completion__a.md),
Codex/grok-4.6; [`__b`](cli_tab_completion__b.md), Claude/opus) plus a third
verification pass. Every number below was re-measured or reproduced; where the two
reports disagreed, §3 and §8 say which reading survived and why. No runtime behavior
was changed.

## Bottom line

**Generate a native Zsh/Bash/Fish grammar from the live argparse tree with `shtab`,
expose it as `sase completion <shell>`, and serve live values from a
pre-argparse `sase completion candidates` fast path that reads through
`sase_core_rs`.**

Three constraints force this and nothing else fits all three:

1. `sase` needs **250–400 ms** to build its full parser and **300–640 ms** for a cold
   process. A generated script answers TAB in **0.4–12 ms**. Anything that re-runs
   `sase` per keystroke is dead on arrival.
2. The tree is **331 parsers / 809 options / 140 positionals** and agents edit it
   weekly. Anything hand-maintained rots.
3. The host shell invokes the completion system **on every keystroke**, not just on
   TAB (§5.2). Dynamic values must be cached in-shell or they become a per-keystroke
   subprocess storm.

Reject: **argcomplete** (re-runs the program per TAB), **Click/Typer** (same execution
model, plus a full rewrite), **a hand-written `_sase`** (guaranteed drift), **carapace
as the foundation** (third-party binary before `sase` completes at all), **a Rust
completion binary** (no standalone entry point today; the measured fast path is already
~22 ms).

Two things neither original report caught change the *install* design and are the
highest-value findings here:

- **The documented install is a silent no-op on this machine.** `~/.zshrc` adds
  `~/.zfunc` to `fpath` *after* `compinit` has already run, so a `_sase` dropped there
  is never registered (§5.1). Verified empirically.
- **`zcompile` is mandatory, not an optimization.** The first `sase<TAB>` in each new
  shell costs **79–84 ms** parsing the 308 KB script, versus **0.4 ms** from
  `_sase.zwc` — a ~200× difference on the cost users actually feel (§5.3).

Full recommendation with phasing in [§8](#8-recommended-solution).

## 1. What "excellent" has to mean

For Zsh the bar is the compsys experience of `git`, `gh`, and well-written
`_arguments` scripts — not "some words appear."

| Property | Zsh mechanism | Why `sase` needs it |
| --- | --- | --- |
| Native compsys, not `bashcompinit` | `#compdef` + `_arguments` | descriptions, grouping, `_files`, menu-select all depend on it |
| Per-option help in the listing | `'--flag[help]'` | 809 options are unusable as a bare word list |
| Descriptions on *values* | `_describe`, `compadd -d` | `sase bead show <TAB>` should show titles, not bare IDs |
| Grouped, tagged listings | `_describe -t`, `zstyle group-name` | separate beads from files from options |
| Won't re-offer a given option | exclusion lists `'(-v --verbose)'{-v,--verbose}` | 15 mutex groups exist today |
| `--opt=value`, option stacking, `--` | `_arguments -s -S` | `sase bead create --size=<TAB>`; `sase proc run -- CMD` |
| Repeatable options | `'*--ref[…]'` | `--ref` / `--tag` are `append` actions |
| Nested subcommands, typed positionals | `:desc:action` state machine | depth 4; 140 positionals |
| Caching of expensive candidates | `_cache_invalid` / `_store_cache` | mandatory here — see §5.2 |
| Hidden commands stay hidden | skip `help=SUPPRESS` | `sase editor helper-bridge` must not leak |
| Zero perceptible latency | everything above runs in-shell | the decisive constraint (§2) |

Bash should be *good* (commands, flags, choices, files); Fish *good* the same way with
descriptions. Elvish/Nushell/PowerShell can wait — SASE targets POSIX hosts
(`INSTALL.md`).

One SASE-specific rule from long-term memory applies: completion rows are user-facing
text, so they must render configured `PROJECT_NAME:` values (`sase`), never ProjectSpec
keys (`gh_sase-org__sase`).

## 2. The decisive constraint: `sase` is slow to start

`src/sase/main/parser.py` maps each top-level command to a `(module, function)` pair and
`entry.py` calls `create_parser(only=parser_only_hint(sys.argv))`, so `sase version`
never imports the bead or ACE trees. Good for normal use, fatal for naive completion:
at completion time the program is driven from `COMP_LINE`, so `parser_only_hint()` sees
a bare `sase`, returns `None`, and the **full** tree is built.

| Operation | `__a` | `__b` | verify | Reading |
| --- | --- | --- | --- | --- |
| `import sase.main.parser` | 78 ms | 18 ms¹ | 48 ms | ~20–80 ms |
| `create_parser(only="bead")` | 3.5 ms² | 277 ms | — | narrow parsers are cheap-to-moderate |
| **`create_parser()` full tree** | **318 ms** | **371 ms** | **256 ms** | **250–400 ms** |
| `sase version` end-to-end | 325 ms | 292 ms | 636 ms³ | 290–640 ms |
| `sase -h` end-to-end | 386 ms | 400 ms | 489 ms | 390–490 ms |

¹ `import sase.main.entry` (lazier module). ² measured against an already-imported
module. ³ cold page cache.

Against a generated script, measured in real zsh:

| Operation | Time |
| --- | --- |
| `autoload +X _sase` (308 KB, **uncompiled**) | **79–84 ms** |
| `autoload +X _sase` (**zcompiled `.zwc`**) | **0.4 ms** |
| `compinit` full rescan, cost *added* by `_sase` | +15–30 ms |
| real TAB `sase bead cr<TAB>` (`__b`, pty) | 5.2 ms |
| real TAB `sase <TAB>` (55 commands) | 6.9 ms |
| real TAB `sase bead create --<TAB>` | 11.8 ms |

**A generated script is 30–1000× faster than re-running `sase`, and costs ~0 at shell
startup.** That ratio settles the architecture; everything else is detail.

The corollary matters just as much: **the ordinary list commands cannot be completion
sources.**

| Command | Time | Verdict |
| --- | --- | --- |
| `sase agent list --json` | **6.4–6.9 s** | unusable |
| `sase bead list --limit 5` | 831 ms | unusable |
| `sase workspace list --json` | 299 ms | unusable |
| `sase project list --json` | 170–174 ms | borderline |
| `sase file list -t src/` | 157 ms | borderline, and imports ACE widgets |

Anything above ~100 ms is felt. A completion path built on these would be worse than no
completion.

## 3. Shape of the tree being completed

Independently re-measured; this reconciles the two reports' conflicting counts.

| Metric | Count | Note |
| --- | --- | --- |
| Parsers (root + subparsers) | **331** | both reports agree |
| Leaf commands / groups / max depth | 270 / 61 / **4** | |
| Options **excluding** auto `--help` | **809** | `__b`'s 808 |
| Options **including** auto `--help` | **1,139** | `__a`'s 1,139 — same tree, different convention |
| Positionals | **140** | both agree |
| Actions with static `choices=` | **94** | `__a` correct; `__b`'s 89 undercounts |
| Mutually exclusive groups | **15** | only `__b` found these |
| Actions with `help=SUPPRESS` | **17** | new |
| Top-level command names | 52 | |

Three properties drive the design:

**The grammar is static.** Plugins (`plugin_discovery.py`) contribute xprompts, config
defaults, and VCS providers via entry points — they do **not** register subparsers.
`_COMMAND_REGISTRARS` is a literal dict, and every `choices=` is a module-level constant
(`ARTIFACT_FILE_KINDS`, `PROC_STATUS_CHOICES`, …), never computed from config. Both
reports independently verified this. So a snapshot of the grammar is correct by
construction, and **only values need to be live**.

**Help strings are too long to use verbatim.** Median 44–54 chars, p90 92–113, **max
262**, and a quarter to a third exceed 60 chars. This is not theoretical: the emitted
Zsh contains a **271-character bracket description**. Zsh renders descriptions in a
column beside the candidate, so generation needs a **shortening pass**, which no
generator does for you. `sase agent-cli`'s command help is a full paragraph.

**Values cluster into ~15 kinds.** Most common positional metavars: `name` (17), `id`
(17), `project` (13), `query` (5), `reference`/`refs` (4 each), plus `bead_id`,
`PLAN_FILE`, `REPO`, `SELECTOR`, `workspace_num`. Most repeated option dests: `--json`
(84), `--project` (33), `--format` (23), `--status` (12), `--kind` (11), `--agent` (9).
So **10–15 kinds cover the great majority of the surface** — a tractable amount of work,
and where the perceived quality lives.

## 4. Options evaluated

### 4.1 argcomplete — reject

The default answer for argparse, and the wrong one here. Its own docs are explicit:
*"any side effects that happen before argcomplete is called … will happen every time the
user presses `<TAB>`"* and *"if the program takes a long time to get to the point where
`argcomplete.autocomplete()` is called, the tab completion process will feel sluggish."*

For `sase` that is 300–640 ms per TAB. Mitigating it means making `create_parser()`
fast — but its slowness *is* the lazy registry doing its job. It would also require
proving `entry.py`'s bead fast path and `sase run` special cases inert under
`_ARGCOMPLETE=1`, and its Zsh integration is a Bash-shaped `COMP_LINE`/`COMP_POINT`
wrapper around `_describe`, not an `_arguments` state machine.

Credit where due: argcomplete's *interfaces* are the best in Python —
`completer(prefix, action, parser, parsed_args) -> {value: description}` attached to
argparse actions. §8 copies those interfaces. (Bryan already runs
`register-python-argcomplete` for `macros` and `pipx`; the rejection is about `sase`'s
startup cost, not argcomplete's design.)

### 4.2 shtab 1.11.0 — the right emitter

Pure Python, zero runtime deps, MPL-2.0, emits bash/zsh/fish/tcsh from one parser walk.
Run against the real `sase` parser and reproduced byte-for-byte across two independent
runs:

```
parser build 256–315 ms | zsh emit 40 ms
zsh 308,278 B / 6,081 lines · bash 114,857 B · fish 255,379 B
```

Output is native and structurally sound:

```zsh
_shtab_sase_bead_create_options=(
  "(- : *)"{-h,--help}"[show this help message and exit]"
  "*"{-R,--ref}"[Artifact reference to attach (repeatable)]:ref:"
  {-z,--size}"[Phase/task size…]:size:(xsmall small medium large xlarge)"
)
```

**Verified working** (probes against the generated script, plus a real zsh pty):

| Concern raised | Verdict |
| --- | --- |
| `sase bead +1` — does `+` break `_describe`? | **Works.** shtab single-quotes it; `sase bead +<TAB>` → `sase bead +1` in a real pty |
| `help=SUPPRESS` leaking | **Clean.** `helper-bridge` absent from the emitted script |
| Static `choices=`, repeatables, nesting | all emitted correctly |
| `#compdef`, `_arguments -C -s`, `_describe` | all present |
| Registration in a real shell | `_comps[sase]=_sase` after `compinit` |

**Verified gaps** shtab does not cover, each a §1 requirement:

| Gap | Evidence |
| --- | --- |
| No exclusion lists | after `-t x`, zsh still offers `-t` |
| No `_arguments -S` | confirmed absent from output — `--` semantics not honored |
| Mutex groups ignored | 15 exist |
| **Legacy aliases duplicated** | `_shtab_sase_changespec` emitted — `patch`/`changespec`, `proc`/`task`, `stitch`/`vcs`, `artifact`/`artifact-file` each appear twice at top level |
| No description shortening | 271-char description in the output |
| `shtab.cmd("…")` emits `($(command))` | bare words, no descriptions, no cache, runs on every TAB — unusable for live values |
| No tag/group naming for values | |

All are addressable in a thin sase-owned layer, which is exactly why shtab is the
*emitter* and not the *product*.

*Licensing:* sase is MIT, shtab MPL-2.0. A PyPI dependency is unambiguous and normal.
Do not vendor the sources (that would carry MPL notices into the MIT tree).

### 4.3 Rewrite onto Click / Typer — reject

Click and Typer have polished completion, but it uses the same execution model (run the
program to produce candidates), so it does not solve the actual problem — and it would
mean rewriting 45 parser modules, `_SaseArgumentParser` validation, compact-vs-full
help, default-`list` rewriting, `sase run` pre-argparse handling, and the bead fast
path. Strictly worse on both axes.

### 4.4 Hand-written `_sase` — reject as source of truth

The only route to the true ceiling (git's and docker's completions are hand-written),
and unmaintainable here: 331 parsers, 809 options, edited weekly, with no mechanical
staleness detector. Hand-writing is right for **fragments** — the value-completion
functions (`_sase_beads`, `_sase_projects`) belong in a hand-written preamble, because
that is where the craft is. *Generate the grammar, hand-write the values.*

### 4.5 Cobra-style `__complete` for everything — reject as sole engine

`gh`/`kubectl` ship a thin function that calls `prog __complete <words…>` and parses
`value\tdescription`. Excellent *dynamic* protocol — viable because a Go binary starts
in single-digit ms. `sase` does not. Using it **only** for annotated dynamic slots,
after a generated `_arguments` script has decided *which* kind is needed, is the Cobra
idea correctly adapted to a slow host. That is what §8 does.

### 4.6 carapace / `usage` / Fig — later, not the foundation

`carapace-bin` covers 10+ shells and `carapace-spec` accepts a YAML spec, but it
requires users to install and hook a third-party binary before `sase` completes at all —
a bad default when the install story is `uv tool install sase`. Once a structured
completion model exists (§8.1), **emitting a carapace spec is nearly free** and buys
nushell/elvish/powershell in one step. jdx `usage` wants KDL as source of truth; argparse
already is the source of truth and a second grammar is how TAB and `--help` stop
matching. Fig/inshellisense are a different product with a separate spec to sync.

### 4.7 A Rust completion binary — reject for now

Tempting given the Rust-core boundary and ~2 ms binary startup, but `sase_core_rs` is a
Python extension module, not a standalone binary; shipping one means a new build
artifact, install path, and place for the grammar to drift. The measured fast path
(§6) is already ~22 ms. If one value kind ever needs to be faster, move *that lookup*
behind `sase_core_rs` — which §6 recommends anyway.

### 4.8 Comparison

| | argcomplete | **shtab + candidates (rec.)** | hand-written | carapace | Click/Typer |
| --- | --- | --- | --- | --- | --- |
| Per-TAB latency | 300–640 ms | **0.4–12 ms** | ~5 ms | ~10 ms | 300–640 ms |
| Stays in sync | ✓ | ✓ (regen + snapshot test) | ✗ | ✗ | ✓ |
| Zsh quality | medium (`_describe` wrapper) | **high (`_arguments`)** | highest | high | high |
| Exclusion lists / mutex | ✗ | ✗ (add in layer) | ✓ | ✓ | ✗ |
| Values with descriptions | ✓ | via candidates hook | ✓ | ✓ | partial |
| Shells | bash, zsh | bash, zsh, fish, tcsh | one | 10+ | bash, zsh, fish |
| Extra user install | no | no | no | **yes** | no |
| Cost to sase | small | small | prohibitive | medium | prohibitive |

## 5. Host-environment findings (new; these change the install design)

Neither original report inspected the target machine. Doing so overturns one
recommendation and resolves both of `__b`'s open questions.

### 5.1 The documented install is a silent no-op on this machine

`~/.zshrc` runs oh-my-zsh (which calls `compinit`) at line 39 and
`autoload -U +X compinit && compinit -u` at line 256 — but adds `fpath+=~/.zfunc` at
**line 320**, after both. `compinit` scans `$fpath` once and builds `_comps`; entries
added later are never registered. Verified:

```
compinit BEFORE fpath+=  (current order)   -> _comps[faketool] = <UNSET>
fpath+= BEFORE compinit  (correct order)   -> _comps[faketool] = _faketool
```

`~/.zfunc` exists but is **empty**, so nothing depends on the current ordering — but
`sase completion zsh > ~/.zfunc/_sase` (what both reports recommend) would produce a
`_sase` that never loads, with no error message.

**Implications for `sase completion install`:** it must not just write a file. It must
(a) detect whether its target directory is on `fpath` *and scanned by `compinit`*, and
(b) when it is not, either fix the ordering or print the exact `fpath=(… $fpath)` line
to add **before** `compinit`. `sase doctor` must assert `_comps[sase]` resolves — file
presence is not evidence of a working install. `/usr/local/share/zsh/site-functions` is
on this machine's `fpath` and is scanned, but needs root.

Related: the dotfiles already `eval "$(atuin gen-completions -s zsh)"` and
`source <(jj util completion zsh)` at startup. Those are Rust binaries (~5 ms). An
`eval "$(sase completion zsh)"` would add **300–640 ms to every new shell**. Print to a
file; never eval. (`~/.bash-completions/*` is already sourced by the same zshrc, so bash
has a ready-made drop directory here.)

### 5.2 Completion runs on every keystroke, not just on TAB

`zsh-autosuggestions` v0.7.0 is installed with
`ZSH_AUTOSUGGEST_STRATEGY=(history completion)`, and async is on by default at zsh 5.9.
The `completion` strategy drives the **completion engine on each keystroke** to produce
its inline suggestion.

This is the single most important host interaction and it cuts two ways:

- It **strengthens** the static-grammar-in-shell design well beyond the TAB-only
  analysis: at 0.4 ms per invocation the generated script is free even per keystroke.
- It makes any dynamic completer that shells out **dangerous**: typing
  `sase bead show a4f2` would spawn ~14 subprocesses at ~22–40 ms each. Zsh-side
  caching (`_cache_invalid` / `_retrieve_cache` / `_store_cache`, gated on
  `zstyle ':completion:*' use-cache on`) is therefore **mandatory, not a polish item**.
  The `history` strategy runs first and absorbs many keystrokes, but that is luck, not
  design.

`__b` flagged this as unmeasured. It is real and it is load-bearing.

**`fzf-tab` is not installed** — `__b`'s other open question, resolved with no action
needed. `zstyle ':completion:*' menu select` is set, so menu selection works today.

### 5.3 `zcompile` is mandatory

Controlled measurement of the cost users actually pay (first `sase<TAB>` in a shell):

| | uncompiled | `.zwc` |
| --- | --- | --- |
| `autoload +X _sase` (308 KB) | 79–84 ms | **0.4 ms** |
| `compinit` cost added by `_sase` | +15–30 ms | +15–30 ms |

~200×. `__b` measured `source` (12.2 → 3.7 ms), which understates the autoload path.
**`sase completion install` must `zcompile`**, and `sase doctor` should check the `.zwc`
exists and is newer than the script. The `compinit` delta is small, real (not "none
measurable"), and normally amortized by the compdump.

## 6. The dynamic-value layer is the real work

Static grammar is solved by generation. Whether completion feels *excellent* depends on
`sase bead show <TAB>` offering bead IDs with titles, instantly.

`entry.py` already has the precedent — 5 lines dispatching `sase bead …` to
`try_handle_bead_fast_path` *before* `parser.py` is imported at all:

```python
if len(sys.argv) >= 2 and sys.argv[1] == "bead":
    from .bead_fast_path import try_handle_bead_fast_path
    ...
```

A completion candidates door goes in the same place, keyed on
`sys.argv[1:3] == ["completion", "candidates"]`.

**Where the values come from — the one place the two reports genuinely conflict.**
`__b` recommends reading flat state directly (regex-scanning `issues.jsonl`, measured
2.9 ms for IDs, 22.2 ms end-to-end). `__a` recommends going through the existing Rust
bindings and catalogs. **Measurement settles it for `__a`:**

```
python -c pass          20.0 ms   (interpreter floor)
import sase_core_rs      1.6 ms   (installed interpreter)
```

`__b`'s 22.2 ms is essentially the interpreter floor; the regex scan was never the cost.
Going through `sase_core_rs` adds **~1.6 ms** and buys correctness, so there is no
reason to reimplement the bead store format in a second place where it will silently
break. This also satisfies the `rust_core_backend_boundary` rule: values any frontend
would need are core; the shell adapter is local.

**Budget contract** — write these down as tests so a later agent cannot "just call
`sase agent list`":

| Event | Budget |
| --- | --- |
| `sase <TAB>`, `sase bead <TAB>`, any flag | shell only; **no Python** |
| `sase completion zsh` (generate) | one full `create_parser()`, ~0.4 s, acceptable |
| `sase completion candidates --kind K` | **≤40 ms**, contract-tested |
| kind `agent` | cheap catalog + cache, or do not ship the kind |

**Two cache layers, both cheap.** (1) On disk under `~/.sase/cache/completion/<kind>`,
invalidated by source mtime. (2) In-shell via `_store_cache`/`_cache_invalid` — required
by §5.2, and it respects the user's own `zstyle` so anyone wanting live data can opt out.

**Output format:** `value\tdescription` lines — maps directly onto `_describe` (with
tags and grouping), degrades to plain words in bash, and matches both argcomplete's
`{value: description}` and Cobra's `__complete`. Well-trodden contract.

**Kinds, in priority order** (by metavar frequency): `project`, `bead`, `repo`,
`plugin`, `workspace`, `flag`, then `patch`, `plan`, `artifact`, `agent`, `model`,
`xprompt`/`skill`, `memory`, `proc`, `monitor`, `tag`.

Existing Python providers (`xprompt/model_completion.py`, `vcs_*_completion.py`,
`ace/query/completion.py`) can be reused *only where they measure fast enough* — they
import the config and LLM registry layers, so they are a fallback, not the fast path.
**Do not import ACE widgets on TAB**: `sase file list` (157 ms) pulls
`sase.ace.tui.widgets.file_completion` into process and is the exact coupling to avoid.
Use `_files` natively for paths.

## 7. Resolving the deployment disagreement

This is the substantive conflict between the two reports.

- **`__a`:** generate on demand from the live parser (`sase completion zsh > …`);
  nothing checked in; handle staleness with a `sase doctor` advisory and regeneration on
  `sase update`.
- **`__b`:** generate at build time, **check the 308 KB `_sase` into the repo**, and add
  a `_lint-completion` gate that regenerates and diffs — because "a static script that
  silently rots is the one real risk."

`__b` is right that drift is the main risk and right that this repo has the machinery
(`sase skill init --check`, `sase memory init --check`, and eight `_lint-*` gates in
`Justfile`; a checked-in zsh script would *not* trip `_lint-toobig`, which only measures
Python in `src/` and `tests/`). But its remedy solves a problem its own design creates:
if the script is generated on demand, there is no checked-in artifact to rot. Checking in
308 KB that changes on nearly every parser edit adds review noise to a repo agents touch
weekly, and the gate would then be regenerating the file to prove it equals itself.

Meanwhile the drift that actually reaches users — **the installed `_sase` going stale
after `sase update`** — is untouched by a repo-side gate. `sase` is a `uv tool` console
script and `sase update` delegates to `uv tool upgrade sase`, which is the natural
regeneration hook.

**Synthesis — take the discipline from `__b` and the freshness from `__a`:**

1. Generate on demand; **do not** check in the 308 KB script.
2. **Check in a compact JSON spec snapshot** (`__a` §4.6) instead — commands, aliases,
   options, `choices`, `SUPPRESS`, and completer kind per action. Human-scale, reviewable
   diffs; a new command that silently completes as a file becomes a visible diff. This is
   `__b`'s drift gate at 1/50th the churn, and it is in-family with
   `tests/main/parser_help_helpers.py::walk_subparser_actions`, which already treats the
   tree as a stable inventory.
3. Assert stable fragments of the emitted Zsh (`#compdef sase`,
   `_describe 'sase commands'`, `bead show` carries the `bead` kind, `helper-bridge`
   absent, `+1` quoted) rather than snapshotting 6,081 lines.
4. Handle user-side drift with a version stamp written by `sase completion install`,
   regeneration during `sase update`, and a **non-blocking** `sase doctor` advisory in
   `src/sase/doctor/checks_integrations.py`.

**Consequence:** on-demand generation makes `shtab` a **runtime** dependency (`__a`'s
position), not dev-only (`__b`'s). That is acceptable — pure Python, zero transitive
deps, ~14th entry in a curated list — and it is what buys the freshness guarantee.

**Naming:** put everything under one group rather than `__b`'s separate top-level
`sase complete` verb — `sase completion {list,zsh,bash,fish,install,candidates}`. Per
`cli_rules.md` a group with a `list` child inherits the bare-invocation default, and the
fast-path check (`sys.argv[1:3] == ["completion", "candidates"]`) is just as cheap as a
one-token check.

## 8. Recommended solution

### 8.1 Phase 1 — static grammar, all shells (small)

1. Add `shtab` as a runtime dependency.
2. Add a sase-owned generator that, before emitting:
   - deep-copies the parser from `create_parser()` (never mutate the live one),
   - rewrites each `help` to a short description — first sentence, capped ~60 chars,
   - hides legacy aliases (`changespec`, `task`, `vcs`, `artifact-file`) from listings
     while keeping them completable,
   - then hands the result to `shtab.complete_{zsh,bash,fish}`.
3. Add `sase completion [list|zsh|bash|fish]` printing to stdout, and
   `sase completion install` that writes the script, **`zcompile`s it**, verifies the
   target directory is scanned by `compinit`, records a version stamp, and reports what
   it did. It must never silently edit `~/.zshrc`.
4. Snapshot the JSON spec; assert stable Zsh fragments (§7).
5. Document print-to-file in `docs/getting_started.md` / `docs/cli.md`:

```zsh
# Zsh — note the fpath line must come BEFORE compinit (see §5.1)
mkdir -p ~/.zfunc && sase completion zsh > ~/.zfunc/_sase && zsh -c 'zcompile ~/.zfunc/_sase'
# ~/.zshrc, before compinit:  fpath=(~/.zfunc $fpath)

sase completion bash > ~/.local/share/bash-completion/completions/sase
sase completion fish > ~/.config/fish/completions/sase.fish
```

After Phase 1: every command, subcommand, option, and static choice completes in
0.4–12 ms with descriptions. This is most of the value and already better than most CLIs.

### 8.2 Phase 2 — dynamic values, zsh-first (medium)

6. Add the `sase completion candidates --kind K --prefix P` fast path in `entry.py`
   **before** `create_parser()`, next to the bead fast path. Import nothing heavy; emit
   `value\tdescription`; hold to 40 ms with a contract test.
7. Source values through `sase_core_rs` and existing catalogs (§6). Add the disk cache
   under `~/.sase/cache/completion/`.
8. Add a **sase-owned annotation layer**: a small helper next to `add_argument` that both
   registers the argument and tags it (`add_bead_id_argument(parser, "id", …)`), which
   the generator translates into shtab's per-action `complete={"zsh": "_sase_beads"}`.
   Do not sprinkle raw shtab types across 45 parser files.
9. Ship the `_sase_beads`-style functions in shtab's `preamble` hook — hand-written zsh
   using `_describe` with proper tags **plus `_cache_invalid`/`_store_cache`, which §5.2
   makes non-optional**:

```zsh
_sase_complete_kind() {
  local kind="$1" prefix="${words[CURRENT]}"
  local -a lines
  if ! _retrieve_cache "sase-$kind"; then
    lines=(${(f)"$(sase completion candidates --kind $kind --prefix $prefix 2>/dev/null)"})
    _store_cache "sase-$kind" lines
  fi
  _describe -t "$kind" "$kind" lines
}
```

10. Start with `project`, `bead`, `repo`, `plugin`, files. Ship `agent` **only** behind a
    cheap catalog — never `sase agent list` (6.4–6.9 s).

After Phase 2: `sase bead show <TAB>` lists IDs with titles, grouped and cached, in under
40 ms. This is the step that makes it feel excellent.

### 8.3 Phase 3 — polish and reach (optional)

11. Post-process the Zsh output for exclusion lists, `_arguments -S`, and the 15 mutex
    groups — the remaining §1 gaps. If post-processing gets awkward, this is the natural
    point to replace shtab's Zsh emitter with a sase-owned one; by then the annotation
    layer and value server are already ours, so the swap is contained.
12. Emit a `carapace-spec` from the same model for nushell/elvish/powershell.
13. Special-case `sase run` to complete `#xprompts` / `%directives` / `@refs` by reusing
    the Rust document catalogs — still not ACE widgets.
14. Offer chezmoi deploy via `src/sase/main/_init_chezmoi_deploy.py` on SASE-managed
    machines. This is a **config/install preference, not a feature flag**: a flag is only
    justified if an early land auto-installs before the generator is trustworthy.

### 8.4 Why this and not the alternatives

One measured fact decides it: **`sase` needs 250–400 ms to build its full parser and
300–640 ms for a cold process; a generated zsh script answers in 0.4–12 ms.** Every
rejected option either pays that cost per keystroke (argcomplete, Click, Typer), cannot
be kept in sync (hand-written), requires a third-party binary (carapace), or adds a build
artifact for a problem already solved in ~22 ms of Python (a Rust binary).

The shape also matches where the industry landed. .NET 10's native completions are
explicitly hybrid — shell-native static grammar, falling back to a `complete` command for
dynamic content. Cobra ships a generated script calling a hidden `__complete`, viable
because a Go binary starts in single-digit ms — precisely the property `sase` lacks and
must recover by keeping the grammar in the shell.

## 9. Pitfalls the implementation must not miss

- **`fpath` ordering (§5.1).** Writing the file is not installing it. Verify
  `_comps[sase]` resolves.
- **`zcompile` (§5.3).** Skipping it costs 80 ms on the first TAB of every shell.
- **Shell-side cache (§5.2).** `zsh-autosuggestions`' `completion` strategy invokes the
  engine per keystroke.
- **Legacy aliases duplicate.** Confirmed in the emitted script; needs a hide list.
- **Help shortening.** A 271-char description reaches the output today. Options: truncate
  at the first sentence (cheapest), or add a `short_help` attribute honored by both the
  generator and `--help` (better end state, dovetails with `cli_rules.md`'s mandate that
  help be excellent).
- **Default-`list` groups.** `sase bead <TAB>` must offer `list`, `show`, `create`, … —
  not flatten to `list`'s flags.
- **`--` remainders** (`sase proc run -- CMD`) need `_arguments` remainder form; shtab
  omits `-S` today.
- **`sase run` bypasses argparse.** Complete it as `_files` first; xprompt/`#`/`%`
  completion is Phase 3.
- **Narrow vs full parser.** `sase completion zsh` must call `create_parser(only=None)`;
  the candidates path must not call it at all.
- **No ProjectSpec keys in the menu.** Use `project_display_names` / resolved
  `display_name`.
- **Workspace venvs.** Complete the `sase` on `PATH`; never bind the script to a
  `sase_<N>/.venv/bin/sase` that disappears.
- **Don't import ACE on TAB.** `sase file list` is for editor integrations, not shells.
- **Script size.** 308 KB is measurably harmless once zcompiled. If it ever matters, split
  per top-level command into separately autoloaded functions.

## 10. Open questions

- **Bash and Fish end-to-end latency were never measured** in any of the three passes.
  Zsh is the bar and was measured thoroughly; the other two are assumed-good by
  construction (same static-script mechanism) but unverified.
- **Which help-shortening policy** to adopt — truncation now vs a `short_help` attribute
  that also improves `--help`. Worth deciding before Phase 1 lands, since it touches the
  same generator code either way.
- **Whether `sase completion install` should offer to fix `~/.zshrc` ordering** (§5.1) or
  only diagnose it. Editing a user's rc file is intrusive; leaving a silently-broken
  install is worse. A `sase doctor` check plus a copy-pasteable line is the conservative
  middle.

## Sources

- **This workspace:** `src/sase/main/{entry,parser,parser_*,bead_fast_path,file_handler,
  update_handler,_init_chezmoi_deploy}.py`, `src/sase/doctor/checks_integrations.py`,
  `tests/main/parser_help_helpers.py`, `Justfile`, `INSTALL.md`, `pyproject.toml`
- **Host:** `chezmoi` linked repo `home/dot_zshrc`;
  `~/.oh-my-zsh/custom/plugins/zsh-autosuggestions` v0.7.0; zsh 5.9; installed
  `~/.local/bin/sase` (uv tool shim)
- **Upstream, opened via `sase repo open`:** `gh:iterative/shtab` 1.11.0 (README,
  `docs/use.md`, `shtab/__init__.py` Zsh emitter), `gh:kislyuk/argcomplete` 3.7.2
- Click shell completion · Cobra `__complete` (`gh`, `kubectl`) · `clap_complete` ·
  `uv generate-shell-completion` · carapace-bin 1.7.2 · jdx `usage` ·
  zsh Completion System manual · .NET CLI tab completion

## Appendix: reproducing the new measurements

```bash
# Parser shape and cost (reconciles the option-count conflict)
.venv/bin/python -c "
import argparse, time
from sase.main.parser import create_parser
t=time.perf_counter(); p=create_parser(); print((time.perf_counter()-t)*1000,'ms')"

# Generate the real script
uv run --with shtab --python .venv/bin/python --no-project python -c "
import shtab, sys; sys.path.insert(0,'src')
from sase.main.parser import create_parser
open('/tmp/zt/zf/_sase','w').write(shtab.complete_zsh(create_parser()))"

# §5.1 fpath-vs-compinit ordering
zsh -f -c 'autoload -U +X compinit && compinit -u -d /tmp/zd1
           fpath+=/tmp/zt/zf; print ${_comps[faketool]:-<UNSET>}'   # -> <UNSET>
zsh -f -c 'fpath+=/tmp/zt/zf
           autoload -U +X compinit && compinit -u -d /tmp/zd2
           print ${_comps[faketool]:-<UNSET>}'                       # -> _faketool

# §5.3 zcompile impact (run with and without _sase.zwc present)
zsh -f -c 'zmodload zsh/datetime; fpath=(/tmp/zt/zf $fpath)
  autoload -Uz compinit; compinit -u -d /tmp/zdX
  s=$EPOCHREALTIME; autoload +X _sase; e=$EPOCHREALTIME
  printf "%.1f ms\n" $(( (e-s)*1000 ))'
zsh -fc 'zcompile -R /tmp/zt/zf/_sase'    # then repeat

# §6 Rust binding import cost, on the installed interpreter
~/.local/share/uv/tools/sase/bin/python3 -c "
import time; t=time.perf_counter(); import sase_core_rs
print((time.perf_counter()-t)*1000,'ms')"

# Real-pty TAB probe (verifies `sase bead +<TAB>` -> `sase bead +1`)
# zsh/zpty harness: compinit with _sase on fpath, write 'sase bead +\t', read back
```

Timings: minimum of 2–5 runs unless noted. Machine `athena`, Linux 6.12.101, zsh 5.9,
CPython 3.14.
