---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# Shell Completion for `sase`: Generate the Grammar, Serve the Values

**Research question:** What is the best way to give the `sase` command excellent
command-line completion — first-class in ZSH, good in every other common shell?

**Scope:** SASE at `ded7f1a5f` (version 0.16.0), Python 3.14.3, zsh 5.9, measured on
`athena` on 2026-08-17. External tools were checked the same day: `shtab` v1.11.0
(opened as `gh:iterative/shtab`), `argcomplete` 3.7.2, `carapace-bin` 1.7.2. All timings
in this note are real measurements from this workspace, not estimates; the repro
commands are in the appendix. No runtime behavior was changed.

## Bottom line

Build a **hybrid completion system**: generate the *static grammar* into a native shell
script at build time, and serve the *dynamic values* from a new, deliberately fast
`sase complete` subcommand.

Concretely:

1. Add a **build-time generator** (`sase completion --shell zsh|bash|fish`) that walks
   the existing argparse tree and emits a native `_arguments`-based `_sase` script.
   Use `shtab` as the emitter — it already produces good zsh — wrapped in a sase-owned
   annotation layer.
2. Add a **runtime value server** (`sase complete <kind> [prefix]`) wired into
   `entry.py` *before* `create_parser()`, alongside the existing bead fast path, with a
   hard budget of 40 ms and its own cache. Existing user-facing list commands are
   nowhere near fast enough to be reused.
3. **Deploy and drift-gate it** exactly like generated skills and memory: an
   `init`-style command with `--check`/`--diff`, chezmoi deploy, and a `just lint` stage
   that fails when the checked-in script no longer matches the parser.

Do **not** use `argcomplete`. It re-runs `sase` on every TAB, and `sase` needs ~400 ms
to build its full parser. That is a 35–80× regression against the generated script and
it cannot be fixed without dismantling the lazy-parser design that makes `sase` fast
today.

The full recommendation, with phasing, is in [§8](#8-recommended-solution).

## 1. What "excellent" means in zsh

Zsh's completion system is the most capable of the common shells, and the gap between
"works" and "excellent" is almost entirely in features the other shells do not have:

| Capability | Zsh mechanism | Why it matters for `sase` |
| --- | --- | --- |
| Per-option help text in the listing | `_arguments '--flag[help]'` | 808 options; without descriptions the list is unusable |
| Descriptions on *values*, not just options | `_describe`, `compadd -d` | `sase bead show <TAB>` should show bead titles, not bare IDs |
| Grouped, tagged listings | `_describe -t <tag>`, `zstyle group-name` | separate "beads" from "files" from "options" |
| Won't re-offer an option already given | exclusion lists `'(-v --verbose)'{-v,--verbose}'[…]'` | 15 mutually exclusive groups exist in the parser today |
| `--opt=value` and option stacking | `_arguments -s -S` | `sase bead create --size=<TAB>` |
| Repeatable options | `'*--ref[…]'` | `--ref` / `--tag` are `append` actions |
| Typed positionals | `:desc:action` state machine | 140 positionals across 331 parsers |
| Caching of expensive candidate sets | `_cache_invalid` / `_retrieve_cache` / `_store_cache` | bead and agent inventories are megabytes |
| Zero perceptible latency | everything above runs in-shell | the decisive constraint — see §2 |

Bash reaches roughly the "options and subcommands, no descriptions" tier; fish gets
descriptions but not the state machine; PowerShell is its own world. Designing for zsh
first and degrading is the right order, and it is also the order every generator
supports.

## 2. The constraint that decides everything: `sase` is slow to start

`sase` uses a lazy argparse registry. `src/sase/main/parser.py` maps each top-level
command to a `(module, function)` pair, and `entry.py` calls
`create_parser(only=parser_only_hint(sys.argv))` so that `sase version` never imports the
bead or ACE command trees. This is good for normal use and fatal for naive completion.

Measured cost of a cold process in this workspace:

| Operation | Min | Notes |
| --- | --- | --- |
| bare `python -c pass` | 15.2 ms | interpreter floor |
| `import sase.main.entry` | 18.3 ms | lazy imports are working |
| `create_parser(only="version")` | 87.3 ms | narrow parser |
| `create_parser(only="bead")` | 276.6 ms | narrow parser, heavy tree |
| `create_parser()` — **full tree** | **370.9 ms** | median 401.5 ms |
| `sase --help` | 400.0 ms | end-to-end |
| `sase --full-help` | 447.5 ms | end-to-end |
| bare `sase` (no args) | 394.3 ms | pays for the full parser to print an error |

Any completion strategy that runs `sase` on every TAB press pays the **full** 370–400 ms,
not the narrow-parser cost: at completion time argcomplete drives the program from
`COMP_LINE`, so `parser_only_hint(sys.argv)` sees a bare `sase` and returns `None`.

Now the comparison. I generated a real `_sase` script from the actual sase parser with
shtab and measured it in a genuine zsh pty session:

| Operation | Time |
| --- | --- |
| `source` the generated 308 KB `_sase` | 12.2 ms |
| same, after `zcompile` → `_sase.zwc` | **3.7 ms** |
| real TAB: `sase bead cr<TAB>` | **5.2 ms** |
| real TAB: `sase <TAB>` (55 commands) | **6.9 ms** |
| real TAB: `sase bead create --<TAB>` (option list) | **11.8 ms** |
| `compinit -C` with the script on `fpath` | 10.8–16.7 ms (unchanged vs. without) |
| `compinit` full rescan with the script | 22.4 ms |

**A generated script is 35–80× faster than re-running `sase`, and it costs nothing at
shell startup.** That single ratio settles the architecture. Everything else in this note
is detail.

## 3. The shape of the CLI being completed

Walking the full parser tree gives the scale of the problem:

| Metric | Count |
| --- | --- |
| Parsers (root + all subparsers) | 331 |
| Leaf commands | 270 |
| Command groups | 61 |
| Max subcommand depth | 4 |
| Options (excluding `--help`) | 808 |
| Positionals | 140 |
| Actions with static `choices=` | 89 |
| Mutually exclusive groups | 15 |

Three properties of this tree matter for the design:

**The command tree is static.** Plugins (`src/sase/main/plugin_discovery.py`) contribute
xprompts, config defaults, and VCS providers via entry points — they do **not** register
subparsers. `_COMMAND_REGISTRARS` is a literal dict. Every `choices=` in
`src/sase/main/parser_*.py` is a module-level constant (`ARTIFACT_FILE_KINDS`,
`PROC_STATUS_CHOICES`, `MONITOR_STATE_CHOICES`, …), not a value computed from config or
installed plugins. So a build-time snapshot of the grammar is correct by construction,
and only *values* need to be live.

**Help strings are too long to use verbatim as completion descriptions.** Of 937 help
strings: median 54 characters, p90 113, max 262. 34% exceed 60 characters and 13% exceed
100. Zsh renders descriptions in a column beside the candidate; a 262-character help
string destroys the listing. `sase agent-cli`'s command help is an entire paragraph.
Generation therefore needs a **shortening pass**, not a straight copy — this is real work
that no generator does for you.

**Positional names cluster into a small set of completable kinds.** The most common
positional metavars across the tree are `name` (17), `id` (17), `project` (13), `query`
(5), `ID` (5), `reference` (4), `refs` (4), `workspace_num` (3), `status` (3), plus
`bead_id`, `PLAN_FILE`, `REPO`, `REF`, `SELECTOR`, `workflow_name`, `chop_name`. On the
option side, the most repeated dests are `--json` (84), `--project` (33), `--format`
(23), `--status` (12), `--kind` (11), `--agent` (9), `--tag` (8). That means roughly
**10–15 value kinds** cover the great majority of the surface. This is a tractable
amount of dynamic-completion work, and it is where the perceived quality lives.

## 4. Options evaluated

### 4.1 argcomplete 3.7.2 — reject

The default choice for argparse, and the wrong one here. Its own documentation is
explicit that it re-executes the program: *"any side effects that happen before
argcomplete is called … will happen every time the user presses `<TAB>`"*, and *"if the
program takes a long time to get to the point where `argcomplete.autocomplete()` is
called, the tab completion process will feel sluggish."*

For `sase` that is ~400 ms per TAB, every TAB. Mitigating it would mean making
`create_parser()` fast — but the whole reason it is slow is that it imports 331 parsers
across ~50 modules, which is exactly the work the lazy registry exists to avoid.

Credit where due: argcomplete has genuinely good zsh support (native, no `bashcompinit`,
argparse help strings become completion descriptions) and a clean custom-completer API
(`completer(prefix, action, parser, parsed_args)` returning `{value: description}`).
Those are the right *interfaces*; the execution model is the problem. Its interfaces are
worth copying, and §5 does.

Also note the `PYTHON_ARGCOMPLETE_OK` global-activation model would put `sase` behind a
global bash/zsh hook — an extra failure mode for a tool the user runs constantly.

### 4.2 shtab v1.11.0 — recommended emitter

Pure Python, zero runtime dependencies, MPL-2.0, supports bash/zsh/fish/tcsh. It walks an
`ArgumentParser` and emits a static script. I ran it against the real sase parser:

```
parser build: 315 ms   zsh generation: 40 ms
zsh:  308,278 bytes / 6,081 lines
bash: 114,857 bytes
fish: 255,379 bytes
```

The zsh output is native and structurally sound — `#compdef`, `_arguments -C -s`,
`_describe` for subcommand lists, grouped option forms, choices, repeatables:

```zsh
_shtab_sase_bead_create_options=(
  "(- : *)"{-h,--help}"[show this help message and exit]"
  {-a,--assignee}"[Assignee]:assignee:"
  "*"{-R,--ref}"[Artifact reference to attach (repeatable)]:ref:"
  {-z,--size}"[Phase/task size…]:size:(xsmall small medium large xlarge)"
  {-r,--tier}"[Plan-bead tier (plan or epic)]:tier:(plan epic)"
)
```

**What shtab gives us for free:** the whole 331-parser tree, four shells, option
grouping, static choices, repeatable options, `FILE`/`DIRECTORY`/`glob()` path
completion, nested subcommand dispatch, and a per-action `complete` attribute plus a
`preamble` hook — which together are enough to graft arbitrary zsh completion functions
onto any argument.

**What shtab does not give us**, each of which is a real gap against §1:

- No exclusion lists — after `sase bead create -t x`, zsh still offers `-t`.
- No `_arguments -S`, so `--` semantics are not honored.
- Mutually exclusive groups are ignored (15 exist).
- `shtab.cmd("…")` emits `($(command))` — a bare word list. No descriptions, no
  caching, and the command runs on **every** TAB. Unusable for `sase agent list`.
- No description shortening; it takes the first *line* of `help`, and sase help strings
  are one long line (§3).
- No tag/group naming for value completions.

Every one of these is addressable in a thin sase-owned layer, which is why shtab is the
recommendation rather than a bespoke emitter. See §8.

One licensing note: sase is MIT, shtab is MPL-2.0. Using it as a build-time dependency
is unambiguous. The emitted bash/fish scripts embed shtab-authored helper functions;
shipping generated output is standard practice for shtab users, but if that matters, the
zsh path in the recommendation is sase-owned anyway.

### 4.3 A hand-written `_sase` — reject as the primary strategy

This is the only way to reach the true ceiling (git's and docker's completions are
hand-written). It is also unmaintainable here: 331 parsers, 808 options, and a CLI that
changes every week. It would be stale within days and there is no mechanical way to
detect that.

Hand-writing is right for **fragments**: the value-completion functions (`_sase_beads`,
`_sase_projects`) belong in a hand-written preamble, because that is where the craft
is. Generation for the grammar, hand-writing for the values.

### 4.4 carapace / carapace-spec — good bonus, wrong foundation

`carapace-bin` 1.7.2 is a single binary that provides completions for 1000+ tools across
bash, zsh, fish, elvish, nushell, powershell, xonsh, oil, ion, and tcsh — far broader
shell coverage than anything else. `carapace-spec` lets a tool ship a YAML spec instead
of shell code.

Rejected as the foundation because it requires users to install and hook a third-party
binary before `sase` completes at all, which is a bad default for a tool whose install
story is `pip install`/`uv tool install`. But: once sase has a structured completion
model (§8.1), **emitting a carapace spec is nearly free**, and it buys nushell,
elvish, and powershell in one step. Worth doing later, not first.

### 4.5 Rewriting the CLI on Click / Typer — reject

Click and Typer have completion built in, but they use the argcomplete execution model
(run the program on every TAB), so they do not solve the actual problem — and they would
require rewriting 331 parsers. Strictly worse on both axes.

### 4.6 A Rust completion binary via `sase-core` — reject for now, revisit later

Tempting given `CLAUDE.md`'s Rust-core boundary and a compiled binary's ~2 ms startup.
But `sase_core_rs` is a Python extension module, not a standalone binary, so there is no
fast Rust entry point today; shipping one means a new build artifact, a new install path,
and a new place for the CLI grammar to drift.

The measured fast path (§5) hits 22 ms in pure Python, which is already imperceptible.
If a value kind ever needs to be faster than that, the right move is to move *that one
lookup* behind `sase_core_rs`, not to build a Rust completion binary.

### 4.7 Fig-style specs / inshellisense — reject

IDE-style inline autocomplete is a different product with a different install story and a
separate spec format to keep in sync. Not a fit for a `pip`-installed developer CLI.

### 4.8 Comparison

| | argcomplete | **shtab (rec.)** | hand-written | carapace | Click/Typer |
| --- | --- | --- | --- | --- | --- |
| Per-TAB latency | ~400 ms | **5–12 ms** | ~5 ms | ~10 ms | ~400 ms |
| Stays in sync automatically | ✓ | ✓ (with drift gate) | ✗ | ✗ | ✓ |
| Zsh descriptions | ✓ | ✓ | ✓ | ✓ | partial |
| Exclusion lists / mutex groups | ✗ | ✗ (add in layer) | ✓ | ✓ | ✗ |
| Dynamic values with descriptions | ✓ | via custom hook | ✓ | ✓ | partial |
| Shells covered | bash, zsh | bash, zsh, fish, tcsh | one | 10+ | bash, zsh, fish |
| Extra user install | no | no | no | **yes** | no |
| Cost to sase | small | small | prohibitive | medium | prohibitive |

## 5. The dynamic-value problem is the real work

Static grammar is solved by generation. Whether `sase` completion feels *excellent*
depends entirely on `sase bead show <TAB>` offering bead IDs with titles, and doing it
instantly.

**Existing list commands cannot be reused.** Measured end-to-end:

| Command | Min | Verdict |
| --- | --- | --- |
| `sase agent list --json` | **6431.7 ms** | unusable |
| `sase bead list --limit 5` | 831.2 ms | unusable |
| `sase workspace list --json` | 298.5 ms | unusable |
| `sase version` | 292.3 ms | — |
| `sase project list --json` | 173.9 ms | borderline |
| `sase file list -t src/` | 157.0 ms | borderline (this *is* the existing completion helper) |

Anything above ~100 ms is felt on TAB. A completion path built on these commands would
be worse than no completion, because it would hang the prompt.

**A dedicated fast path is cheap.** `entry.py` already has the precedent: it dispatches
`sase bead …` to `try_handle_bead_fast_path` *before* importing `parser.py` at all. The
same trick applies. I simulated a `sase complete beads` handler — interpreter start, a
regex scan of the 7.3 MB `issues.jsonl`, and emitting all 3698 IDs:

```
simulated `sase complete beads` fast path: 22.2 ms  (3698 ids)
```

The underlying data is cheap when you do not go through the domain layer:

| Source | Cost |
| --- | --- |
| `issues.jsonl` (7.3 MB, 3698 rows), full `json.loads` per line | 45.9 ms |
| same file, regex scan for IDs only | **2.9 ms** |
| `agent_name_registry.json` (13 MB), `json.load` | 97.0 ms |
| `listdir ~/.sase/projects` (30 entries) | 0.1 ms |

So the design is: **a `sase complete` subcommand that reads flat state directly, imports
almost nothing, and is held to a measured budget.** Give it a contract test that fails
if any kind exceeds ~40 ms, the same way `tools/check_test_cost_budgets` guards test
cost.

**Then cache on top of it.** Two layers, both cheap:

1. *In-process*: a completion cache file under `~/.sase/cache/completion/<kind>.txt`,
   invalidated by the mtime of the source (`issues.jsonl`, `~/.sase/projects/`). Cuts the
   13 MB agent-registry case to a file read.
2. *In-shell*: zsh's standard `_cache_invalid` / `_retrieve_cache` / `_store_cache`
   layer, gated on `zstyle ':completion:*' use-cache on`. This is the idiomatic answer
   for exactly this problem and it respects the user's own zstyle preferences, so a user
   who wants always-live data can turn it off.

**Value kinds to implement first** (from the metavar frequency in §3):

`bead-id`, `project`, `agent`, `patch`, `plan-file`, `workspace-num`, `repo`,
`memory-file`, `model`, `xprompt`/`skill`, `artifact-ref`, `proc`, `monitor`, `flag-key`,
`tag`.

Several already have Python providers built for the TUI and LSP that can be reused
rather than rewritten: `src/sase/xprompt/model_completion.py` (635 lines),
`vcs_project_completion.py`, `vcs_repo_completion.py`, `vcs_ref_completion.py`,
`placeholder_completion.py`, and `src/sase/ace/query/completion.py`. Caution: these
import the config and LLM registry layers, so they are the *fallback* path, not the fast
path — measure each before wiring it in.

**Output format.** Emit `value\tdescription` lines, which maps directly onto zsh's
`_describe` (descriptions, grouping, tags) and degrades to plain words in bash. This is
the same shape argcomplete's `{value: description}` completers produce and what Cobra's
`__complete` emits — a well-trodden contract.

## 6. Deployment, drift, and CI

sase already has the machinery for "generated file that must not drift," and completion
should reuse it rather than invent a parallel one:

- **Generation + drift check.** `sase skill init` and `sase memory init` both support
  `--check` (report drift without writing) and `--diff`. `just lint` already runs
  `_lint-flags`, `_lint-changelog`, and `_lint-patch-stitch-terminology` as
  generated-artifact gates. Add `_lint-completion`: regenerate from the parser, diff
  against the checked-in `_sase`, fail on mismatch. Without this gate the script silently
  rots, which is the single biggest risk of the static approach.
- **Deploy.** `src/sase/main/_init_chezmoi_deploy.py` provides locked, provenance-tracked
  chezmoi deploys with `--no-commit`/`--no-push`/`--dry-run`. The completion script is a
  dotfile-shaped artifact; it belongs on that path, landing in the user's `fpath`.
- **`zcompile`.** Compile `_sase` to `_sase.zwc` on install — measured 12.2 ms → 3.7 ms.
- **CLI conventions.** Per `sase/memory/cli_rules.md`: sorted subcommands, a short alias
  for every long option, no required options, colored output. A new `completion` group
  with an exact `list` child would inherit the bare-invocation default automatically via
  `_default_list_subcommands()`.

## 7. Risks and open questions

- **Drift is the main risk.** Static generation is only correct if regeneration is
  enforced. The lint gate in §6 is not optional.
- **Help-string shortening needs a policy.** 34% of help strings are too long for a
  completion column. Options: (a) truncate at the first sentence, (b) add an optional
  `short_help` attribute honored by both the generator and, eventually, `--help`, or (c)
  a deep-copied parser rewritten before generation. (c) is the cheapest to ship; (b) is
  the better end state and dovetails with the `cli_rules.md` mandate that `--help` be
  excellent.
- **Alias duplication.** `artifact`/`artifact-file`, `patch`/`changespec`, `proc`/`task`,
  `stitch`/`vcs` share registrars. Legacy aliases should probably be hidden from
  completion listings even though they remain valid.
- **`sase run` bypasses argparse.** `entry.py` intercepts `sase run` before parsing to
  handle free-form queries. Completion after `sase run` should fall back to `_normal` or
  to xprompt/`#directive` completion rather than pretending the argparse spec applies.
- **`sase file list` overlap.** The existing filesystem completion helper (157 ms) is
  consumed by editor integrations. It is the wrong path for shell completion — use
  `_files` natively — but the two should not diverge in behavior.
- **Script size.** 308 KB is large but measurably harmless (§2). If it becomes an issue,
  splitting per top-level command into separately autoloaded functions is the standard
  remedy.
- **Not yet measured:** bash and fish end-to-end latency, and behavior under
  `zsh-autosuggestions` / `fzf-tab`, which Bryan may be running. `fzf-tab` in particular
  interacts with `_describe` grouping and is worth verifying early.

## 8. Recommended solution

Build a **hybrid**: generated static grammar plus a fast dynamic value server, deployed
and drift-gated like every other generated artifact in this repo. Ship it in three
phases, each independently useful.

### 8.1 Phase 1 — static grammar, all shells (small)

1. Add `shtab` as a **dev/build dependency** (not a runtime one).
2. Add a sase-owned generator module that:
   - deep-copies the parser from `create_parser()`,
   - rewrites each `help` to a short completion description (first sentence, capped at
     ~60 chars),
   - hides legacy aliases,
   - hands the result to `shtab.complete_zsh` / `complete_bash` / `complete_fish`.
3. Add `sase completion [zsh|bash|fish]` to print the script, and
   `sase completion install` to write it into `fpath`, `zcompile` it, and report what it
   did. Follow `cli_rules.md`; give the group a `list` child.
4. Check the generated `_sase` into the repo and add `_lint-completion` to `just lint`.

After Phase 1: every command, subcommand, option, and static choice completes in ~5–12 ms
with help descriptions. This is already better than most CLIs and is the bulk of the
value.

### 8.2 Phase 2 — dynamic values, zsh-first (medium)

5. Add a `sase complete <kind> [prefix]` fast path in `entry.py`, dispatched **before**
   `create_parser()`, next to the bead fast path. Import nothing heavy. Emit
   `value\tdescription` lines. Hold it to a 40 ms budget with a contract test.
6. Back it with a mtime-invalidated cache under `~/.sase/cache/completion/`, and read
   flat state directly (`issues.jsonl`, `~/.sase/projects/`) rather than going through
   the domain layer. Reuse the existing TUI/LSP completion providers only where they
   measure fast enough.
7. Add a sase-owned **annotation layer**: mark actions with a completion kind
   (`action.sase_complete = "bead-id"`), and have the generator translate that into
   shtab's per-action `complete={"zsh": "_sase_beads", …}`. Ship the `_sase_beads`-style
   functions in shtab's `preamble` hook — hand-written zsh using `_describe` with proper
   tags plus `_cache_invalid`/`_store_cache`.
8. Start with the ~15 kinds in §5, prioritized by metavar frequency: `bead-id`,
   `project`, `agent`, `patch`, `plan-file`, `workspace-num`, `repo`.

After Phase 2: `sase bead show <TAB>` lists bead IDs with titles, grouped and cached, in
under 40 ms. This is the step that makes it feel excellent.

### 8.3 Phase 3 — polish and reach (optional)

9. Post-process the zsh output to add exclusion lists, `_arguments -S`, and mutually
   exclusive group handling — the remaining §1 gaps shtab does not cover. If the
   post-processing gets awkward, this is the natural point to replace shtab's zsh emitter
   with a sase-owned one; by then the annotation layer and value server are already ours,
   so the swap is contained.
10. Emit a `carapace-spec` YAML from the same model to pick up nushell, elvish, and
    powershell essentially for free.
11. Special-case `sase run` to complete xprompts and `#directives` instead of argparse
    options.

### 8.4 Why this and not the alternatives

The decision reduces to one measured fact: **`sase` needs ~400 ms to build its full
parser, and a generated zsh script answers in 5–12 ms.** Every rejected option either
pays the 400 ms on every keystroke (argcomplete, Click, Typer), cannot be kept in sync
(hand-written), requires users to install a third-party binary (carapace), or adds a
build artifact for a problem already solved in 22 ms of Python (a Rust binary).

The hybrid also matches where the industry has landed. .NET 10's native completions are
explicitly hybrid: shell-native code for the static grammar, falling back to a `complete`
command for dynamic content like NuGet package IDs. Cobra ships a generated script that
calls back into a hidden `__complete` subcommand — viable there only because a Go binary
starts in single-digit milliseconds, which is precisely the property `sase` lacks and
must therefore recover by keeping the grammar in the shell. And the shape matches how
this repo already handles generated artifacts: generate, check in, drift-gate, deploy
through chezmoi.

## Appendix: reproducing the measurements

```bash
# Parser shape and cost
.venv/bin/python -c "
from sase.main.parser import create_parser; import time
t=time.perf_counter(); p=create_parser(); print((time.perf_counter()-t)*1000, 'ms')"

# Generate a real zsh script from the real parser
sase repo open gh:iterative/shtab -r "…"
PYTHONPATH=<shtab-checkout> .venv/bin/python -c "
import shtab; from sase.main.parser import create_parser
open('/tmp/zc/_sase','w').write(shtab.complete_zsh(create_parser()))"

# Load cost, with and without zcompile
zsh -f -c 'zmodload zsh/datetime; autoload -Uz compinit; compinit -u -d /tmp/zd
  s=$EPOCHREALTIME; source /tmp/zc/_sase; e=$EPOCHREALTIME
  printf "%.1f ms\n" $(( (e-s)*1000 ))'
zsh -f -c 'zcompile -R /tmp/zc/_sase'   # then repeat the above

# End-to-end TAB latency in a real pty (delta vs. the same keystrokes without TAB)
# see zsh/zpty + zsh/datetime harness; measured 5.2 / 6.9 / 11.8 ms
```

Command latencies were measured with `subprocess.run` over 3–5 cold runs, reporting the
minimum. Machine: `athena`, Linux 6.12.101, zsh 5.9, Python 3.14.3.
