# A `:` Command Line for the SASE TUI

**Research question.** Should the TUI split its command-palette keys so that `;` opens
the Command Palette and `:` opens a new panel for typing and running `sase` CLI
commands, with completion better than a shell's? The commands would run as durable
procs: output streams inline, but the user can leave the panel and follow the proc in
Admin Center → Procs. Is the plan sound? What would I change? What should we build?

**Scope and method.** I read the code at sase `438881786` (2026-09-24): keymaps, the
command palette, the `!!` background-command flow, the proc store, supervisor and
observer, the Admin Center Procs pane, the completion package and the TUI's input and
completion widgets. I also read the earlier `cli_tab_completion` research and the
command-palette plans.

I measured spec-build cost, candidate-provider latency, proc submit-to-first-byte
latency, and ANSI color behavior under a pipe. Proc probes ran against a throwaway
`SASE_HOME`, so the user's proc store was not touched. I changed no code.

---

## Bottom line

**Yes, build it. It is a strong idea.** The TUI knows things a shell never can: what
you have selected, and which agents, beads, procs and projects are loaded right now. It
can also show inline docs and live output. Four parts of the plan need to change,
though, or it will feel unreliable.

1. **Not every command can be a proc.** Procs have no TTY and read stdin from
   `/dev/null`. Commands that open `$EDITOR`, fzf, a pager or tmux need a foreground
   escape hatch (`app.suspend()`, like vim's `:!`). A few commands must be refused:
   `sase tui` itself, and foreground servers such as `service run`.
2. **`_submit_durable_proc` is the wrong path.** It is operation-centric: a plain
   `sase …` command that exits 0 without writing a typed result settles as
   `error / missing-result`. Command-line procs need a small exit-code watch path, and
   they must **not** be service oneshots. The Procs tab hides those by default
   (`-service`), which would defeat the "watch it in Procs" requirement.
3. **Output fidelity needs a contract.** Procs run on a pipe. To show color, correct
   width and live streaming, the child needs `FORCE_COLOR`, `COLUMNS` and
   `PYTHONUNBUFFERED`. Today `sase bead list` / `bead show` ignore `FORCE_COLOR`
   (measured: 0 ANSI sequences), while `agent list`, `memory list` and `plan list`
   honor it.
4. **Working directory matters.** From `/tmp`, `sase bead list` prints
   `No issues found.`; from the sase checkout it lists 410 beads. The panel needs a
   visible working-context chip and a `cd` built-in.

**Recommended shape:** a bottom-anchored drawer (ModalScreen) that looks like vim's
command line grown into a small console:

- a transcript of "command blocks" (inspired by Warp)
- a syntax-highlighted input with fish-style ghost text
- a fuzzy completion popup with descriptions
- a live signature/help line

It is backed by:

- a frontend-neutral completion engine over the existing `sase.completion` spec
- the TUI's in-memory entity data
- durable, tagged procs

Ship it behind a beta flag and flip `:` / `;` in the final phase. The full recommendation
is in [§10](#10-recommended-solution).

---

## 1. What exists today (the ground truth this design builds on)

### 1.1 Keymaps and the palette

- `src/sase/default_config.yml:799` binds `open_command_palette: "colon,semicolon"`.
  Comma-separated keys are alternate bindings for one action. `;` was added later by
  `plans/202604/semicolon_command_palette.md`, simply because it was asked for.
- The palette is `CommandPaletteModal`
  (`src/sase/ace/tui/modals/command_palette_modal.py`), a centered `ModalScreen`:
  - Frame: 75% × 70%, `border: double $primary`.
  - Title: `✦ Command Palette  [Agents]  ·  N of M commands`.
  - Footer: a `━━●━━` position gauge.
  - Ranking: tiered substring scoring plus a `key:<key>` filter.
  - Textual's built-in palette is disabled (`app.py:161 ENABLE_COMMAND_PALETTE = False`).
- `action_open_command_palette` (`actions/base.py:656`) already builds a
  `CommandContext` snapshot (`commands/types.py:202`) of the current tab and the
  selected agent, Patch and axe item. That snapshot is a ready-made seed for
  selection-aware completion.
- No plan has ever proposed an ex-style `:` line. `plans/202608/prompt_star_search.md:314`
  lists "a `:` command line" as a non-goal of that epic, and nothing claims the key
  otherwise. Inside the Admin Center Config pane, `:` is a scoped jump-to-path binding.
  The pager's `:`/`;` (go-to-line) is a separate app and is unaffected.

### 1.2 The existing "run a command" feature: `!!`

`!!` (bang mode) walks three modals: ProjectSelect → WorkspaceInput →
CommandHistoryModal. It then submits the durable wrapper `sase axe bgcmd-launch`, which
runs `sh -c CMD` as a **transient service oneshot** with at most 9 slots
(`actions/axe_bgcmd.py`, `axe/bgcmd_operations.py`).

- Output shows in the Services tab's oneshot list, not in Procs. Service rows are hidden
  by the Procs default query `ace.procs.default_query: "-service"`.
- History lives in `~/.sase/command_history.json` (`history/command.py`), with no file
  lock.

That flow is clunky: three modals before you can type, and output in a different tab.
It is exactly what a good command line should make obsolete.

### 1.3 Procs

The store is Rust-backed (`sase_core_rs`) behind `src/sase/procs/store.py`. The
supervisor, log capture and settlement are Python.

- **Launch path:** `submit_proc_request(ProcSubmitRequest)` (`procs/submission.py:72`)
  is the one launch path. `ProcSubmitRequest` (`procs/request.py:16`) carries:
  - `argv`, `label`, `cwd`, `origin`, `session_id`, `tags`
  - an `env` overlay
  - `concurrency_keys`, timeouts
  - an optional `operation` and `service` block.
- **Capture:** `Popen(..., stdin=DEVNULL, stdout=pipe, stderr=STDOUT, start_new_session=True)`
  (`procs/supervisor.py:270`). There is no pty anywhere in `src/sase`. Output is written
  byte-for-byte to `~/.sase/procs/logs/<id>.log`, with one rotated `.log.1`
  segment and a 2 MiB cap.
- **Settlement:** exit 0 → `success`, anything else → `error`. The `exit_code` is
  recorded. *But* if a proc declares an `operation`, a success without a typed result
  becomes `error / missing-result` (`procs/settlement.py:268-300`).
- **TUI submission:** `_submit_durable_proc` (`_proc_action_submission.py`) always
  supplies an operation and decodes the typed result on completion
  (`_proc_observer_store.py:100 decode_completion`). **So a raw `sase <cmd>` cannot go
  through it unchanged.**
- **Observer:** it polls every 0.5 s and tails **one** detail proc
  (`set_detail_proc`), re-reading a 400-line tail each poll (`read_proc_log_tail`
  seeks from the end). There is no incremental, offset-based reader.
- **Procs pane:** it renders ANSI with `Text.from_ansi`, auto-follows unless the user
  scrolled, and supports `K` kill, `e` editor, `y` copy and `/` filter. `ObservedProc`
  carries no `tags`, and the query dialect has no tag or origin field. There is also
  no way to open the Admin Center with a particular proc pre-selected.
- **Producer inventory:** every TUI proc producer must be registered in
  `ace/tui/_proc_producer_sites_*.py`, which `tests/ace/tui/test_proc_producer_inventory.py`
  enforces.

### 1.4 CLI grammar and completion

- **The CLI is argparse, loaded lazily.** It has 63 top-level commands and 439 parser
  nodes (365 leaves), with nesting up to 4 levels deep and 1,591 options. **Plugins do
  not add subcommands**, so the grammar is static per install. The earlier
  `cli_tab_completion` research verified this, and this is what makes a cached spec
  correct.
- **A machine-readable spec already exists.** `sase.completion.build.build_spec()`
  walks the live parser into `CommandSpec`, `OptionSpec` and `PositionalSpec` objects
  carrying:
  - summaries, choices, `kind`, `repeatable`
  - `mutex_groups`, `default_child`, remainder positionals.

  The spec **lacks** `required`, option metavars and defaults. `sase completion spec`
  emits only the structural view, with descriptions replaced by digests.
- **Typed value providers exist.** `candidates_for(kind, prefix, project=, limit=)`
  (`completion/candidates/providers.py`) covers 25 value kinds: project, bead, agent,
  proc, xprompt, flag, plan, patch, artifact ref, and more. They filter by prefix
  only. Several read through `sase_core_rs`.
- **The TUI does not use `sase.completion` at all today.** Its completion stack is
  separate:
  - `FilterBar` plus `FilterBarCompletionMixin`: a `SingleLineVimTextArea` with an
    `OptionList` dropdown.
  - Prompt-bar completion panels and debounced soft completion.
  - Rust `fuzzy_match` with match-run highlighting
    (`widgets/_completion_match_highlight.py`).
- **Textual 8.0.1's `TextArea` has a native `suggestion` reactive.** It renders ghost
  text that the right arrow accepts (`textual/widgets/_text_area.py:411`), so
  fish-style autosuggestions come almost free.
- **House Escape convention for vim inputs:** Escape in INSERT enters NORMAL; Escape in
  NORMAL bubbles up to the modal's cancel (`single_line_vim_text_area.py` docstring).

### 1.5 Measurements

| Probe | Result |
| --- | --- |
| `import sase.completion.build` + full `build_spec()` in-process | 0.32 s + 0.45 s |
| Full spec JSON size / `json.dumps` / `json.loads` | 462 KB / 7 ms / 3 ms |
| `candidates_for("agent")` / `("proc")` / `("project")` / `("flag")` | 228 ms / 7 ms / 1 ms / 7 ms |
| `candidates_for("bead")` in-process from the repo checkout | 0 rows (the CLI fast path `sase completion candidates bead` returns rows, so the in-process call lacks the fast path's store setup) |
| `sase version` direct | 0.35 s |
| `sase proc run -w -- sase version` | 1.29 s |
| In-process `submit_proc` → returns / first log byte / terminal | 0.26–0.50 s / 0.79–0.95 s / 1.04–1.12 s |
| `FORCE_COLOR=1 COLUMNS=100` child under the supervisor | colored, 100-column rich output captured in the log ✓ |
| ANSI sequences with `FORCE_COLOR=1` on a pipe: `agent list` / `memory list` / `plan list` | 43 / 64 / 75 ✓ |
| … `bead list` / `bead show` | **0 / 0** ✗ (`bead/cli_dep_render.py:34 resolve_color` checks only `NO_COLOR` then `isatty()`; `-c always` → 101) |
| `sase bead list` from `/tmp` vs from the sase checkout | `No issues found.` vs 410 beads |

Three consequences follow:

- The keystroke path must use in-memory data. The agent provider alone costs 228 ms.
- The spec should be built once, cached, and never built on the UI thread.
- A command-line proc takes about 1 s to show its first byte. That is fine for a
  durable job, but the UI must be optimistic and show the block the instant you press
  Enter.

---

## 2. Is this a good idea? (critique)

### Why it's worth doing

- **The CLI is far bigger than the TUI's keymap.** It has 365 leaf commands, and many
  operations exist only there: `bead` admin, `memory`, `flag`, `tool`, `repo`,
  `artifact`, `gate`, `monitor`. Today you have to leave the TUI and lose your context
  to reach them.
- **The TUI can genuinely beat a shell at completion.** A shell completes from a
  generated grammar plus a 30 s value cache. The TUI has:
  - live in-memory entities
  - knowledge of your current selection
  - room for multi-column, colored descriptions
  - space for signature help and inline validation
  - fuzzy ranking.

  zsh cannot do most of that.
- **Durable procs make it trustworthy.** Every run is recorded, killable, visible in
  Procs and survives a TUI restart. A terminal tab has none of that.
- **It can replace `!!`'s three-modal flow**, the worst "run a thing" UX in the TUI
  today.

### Risks and costs (none fatal)

1. **Muscle-memory churn.** `:` has meant "palette" since sase-1d. Mitigation: hop keys
   between the two surfaces (§4, R5) and a one-time tip.
2. **Two ways to do everything.** A TUI key and a CLI command for the same thing can
   reduce the pressure to build proper TUI affordances. Mitigation, optional: when a
   typed command has a keymapped equivalent, show "tip: `x` on the Agents tab does
   this". This is the reverse of what the palette teaches.
3. **Interactive commands.** Editor, fzf, pager, tmux and confirmation prompts. Without
   a policy these hang, fail with EOF, or print garbage (§5.7).
4. **Latency.** About 1 s to the first byte, compared with 0.35 s for a direct
   subprocess. That is acceptable if the UI is optimistic, and worth a later perf item
   (a warm supervisor).
5. **Output fidelity.** Color, width, `\r` progress bars and `isatty()`-based branching
   (§5.6).
6. **The working directory changes results** (§1.5).
7. **The Rust-core boundary.** A command-line completion engine is arguably "shared
   behavior" (§6.6).
8. **Test and doc churn.** The keymap flip touches about 20 files plus four PNG golden
   suites (Appendix A).

Safety is neutral-to-good. Commands run with the user's own privileges, as they would in
a terminal. And because stdin is `/dev/null`, destructive commands that normally ask for
confirmation **fail closed** unless the user passes `-y`.

---

## 3. Alternatives considered

| Approach | Verdict | Why |
| --- | --- | --- |
| **A. `:` command-line drawer + durable procs** (the user's plan, adjusted) | ✅ **Recommend** | Matches vim/Helix/k9s muscle memory. Separates "pick an action" (palette) from "compose a command" (command line). Durable and observable. |
| B. One omnibar with prefixes (VS Code style: `>` actions, `:` CLI, `!` shell) | ❌ for now | The interaction models differ: picking one row vs. composing token by token. Ranking 365 CLI leaves together with ~300 TUI actions would make both worse. The hop keys in R5 get about 90% of the benefit for about 1% of the cost. |
| C. Embed a pty terminal widget running zsh | ❌ | Re-imports the shell completion we are trying to beat. Heavy and fragile terminal emulation in Textual. Not durable, not in Procs. |
| D. Suspend to the real terminal for everything (`app.suspend()`, vim `:!`) | ⚠️ only as a fallback | Perfect fidelity, but it blocks the TUI, isn't durable and has no inline output. Right for TTY-needing commands only (§5.7). |
| E. Put CLI commands into the palette | ❌ | Same ranking-pollution problem as B, and argument entry doesn't fit a pick-one list. A single "Run in Command Line: `sase <query>`" fallback row is a fine optional bridge. |
| F. Generated forms (argparse → form fields) | 💡 later | Great for rare, many-flag commands. Could be a `ctrl+space` "open as form" on the current command in a later phase. It is not the primary surface. |
| Docked bottom widget (like the prompt bar) instead of a ModalScreen | ❌ | Needs `check_app_action` gating for every row action while typing, and focus juggling. Modals are the house pattern (about 79 of them; the palette and the Admin Center are modals). "Leaving" is just a dismiss, and the state lives on the app. |

---

## 4. Requirement adjustments (called out explicitly)

- **R1 — Name it "Command Line", not "command mode".** In this TUI, "mode" already
  means a transient prefix mode (leader `,`, bang `!`, fold `z`, copy `%`) with a
  footer badge. "Shell" is a glossary term (agent, proc and gate shells). Vim's own name
  for `:` is the command line. Use action id `open_command_line`, with Command Palette
  on `;` and Command Line on `:`. *(Your call; "Console" is the runner-up.)*
- **R2 — Not everything becomes a proc.** Each CLI path gets a **run policy**:
  - `proc` (the default): durable, streamed inline.
  - `foreground`: needs a TTY. Suspend the TUI and run it in the real terminal, then
    return. Record it in history, but it is not a proc.
  - `deny`: `sase tui` and foreground servers. Explain why, and suggest the alternative
    (e.g. `service start`).
- **R3 — An implicit `sase` prefix, plus built-ins.** You type `bead list`, not
  `sase bead list`; a leading `sase ` is accepted and stripped. Four in-panel built-ins
  run without a proc:
  - `cd <path|+project>`
  - `clear`
  - `help [cmd…]`
  - `history`

  A guard test asserts built-in names never collide with top-level commands. None do
  today.
- **R4 — An explicit, visible working context.** A header chip such as
  `⌂ sase · ~/projects/github/sase-org/sase` shows where commands run. The default is
  the TUI's launch cwd if it lies inside a project checkout, otherwise the current
  project's checkout, otherwise the launch cwd. `cd` changes it, and `cd +<project>`
  completes project names. This is a *default*, which is exactly what the glossary
  allows "current project" to supply.
- **R5 — Hop keys between the two surfaces.** Typing `;` into an **empty** Command Line
  switches to the palette. Typing `:` into an **empty** palette filter switches to the
  Command Line. The first time `:` opens the Command Line after the flip, show a
  one-time tip: "Command Palette moved to `;` (type `;` here to jump)".
- **R6 — Command-line procs are ordinary tagged procs, never service oneshots.** Use
  `origin="ace"`, tag `command-line`, and label `: bead list --status open`. This keeps
  them visible under the Procs default query and in the proc gear count.
- **R7 — A color and width contract is a prerequisite.** `--color auto` resolvers must
  honor `FORCE_COLOR`/`CLICOLOR_FORCE`. Ten `src/sase` files branch on
  `stdout.isatty()`, and none reads `FORCE_COLOR`.
- **R8 — Roll out behind a beta flag, and flip the keys last.** While the flag is off,
  `:` still opens the palette. The final phase flips the default keys and removes the
  flag. This is the `sase_flags` "epic scaffolding" pattern.
- **R9 (optional, later) — `:!<shell>`.** Run a shell command in the same panel and
  working context, as a `command-line` proc. That is vim parity, and it lets `!!`'s
  three-modal flow be retired later.

---

## 5. Design: UX

### 5.1 Anatomy

The panel is a bottom-anchored ModalScreen, `align: center bottom`:

- width about 96% (max 160)
- height grows with content up to about 65%
- `ctrl+t` toggles between tall and full height.

The dimmed TUI stays visible above it, so you keep your context. It is visually distinct
from the centered palette on purpose: *you are at the command line.*

**Empty state** (Agents tab, agent `research.2h.cld` selected):

```
╭─ ❯ Command Line ──────────────────────────── ⌂ sase · ~/projects/github/sase-org/sase ─╮
│  RECENT                                                                                  │
│    bead show sase-17p                                                    2h ago  ✓       │
│    agent wait research.2h --timeout 10m                                  1d ago  ✗ 124   │
│  FOR research.2h.cld · selected agent                                                    │
│    agent show research.2h.cld                                                            │
│    agent wait research.2h.cld                                                            │
│    chat show research.2h.cld                                                             │
│                                                                                          │
│ ❯ sase ▌                                                                                 │
│   63 commands · type to search · ⇥ complete · ; Command Palette                          │
╰─ ⏎ run · ⇥ complete · ↑↓ history · ^R search · esc hide ─────────────────── 0 running ──╯
```

The "FOR <selection>" rows are **derived, not curated**. They are every leaf command
whose first positional's `kind` matches the selected entity's kind (agent, bead, proc,
project or Patch), ranked by how often you used them. New commands appear automatically.

**Typing, with the completion popup and signature line:**

```
╭─ ❯ Command Line ──────────────────────────── ⌂ sase · ~/projects/github/sase-org/sase ─╮
│ ✓ bead list --status open                          exit 0 · 0.9s · 14:02 · proc 470vtq  │
│ │ ◐ M sase-17p.4 · Stop, follow, and wait on a ToolRun by id ← sase-17p     ⧖ 1h        │
│ │ ◐ L sase-17p.5 · Settle hand-off runs truthfully after crashes …          ⧖ 1h        │
│ │ ⋯ 406 more lines · o expand                                                           │
│         ┌──────────────────────────────────────────────────────────────┐                │
│         │ ◆ sase-17p     epic  in_progress  Tool-run hand-off     sel  │                │
│         │   sase-17p.4   task  in_progress  Stop, follow, and wait…    │                │
│         │   sase-17m     epic  open         Rename agent family…       │                │
│         │ bead · 3 of 410 · fuzzy                           ⇥ accept   │                │
│         └──────────────────────────────────────────────────────────────┘                │
│ ❯ sase bead show sase-17▌                                                                │
│   bead show ‹ID…› [-f compact|json|full] [-P PROJECT] [-N] [-w WIDTH] · Show one or more │
╰─ ⏎ run · ⇥ accept · ↑↓ move · esc normal ─────────────────────────────────── 0 running ──╯
```

**Running and finished blocks, with a block selected (NORMAL-mode block navigation):**

```
│ ✗ bead close sase-zz                                exit 2 · 0.7s · 14:05              │
│ │ error: no such bead: sase-zz                                                         │
│▌⠹ agent wait research.2h --timeout 10m             running 0:42 · proc 3aacsa   [sel]  │
│▌│ waiting for 3 agents (research.2h.mus, research.2h.gem, research.2h.cld) …           │
│ ↗ prompt edit                                       ran in terminal · exit 0            │
╰─ K kill · r rerun · e edit · o expand · y copy · p open in Procs · i input ─ 1 running ─╯
```

### 5.2 Visual language (reusing the house palette)

| Element | Style |
| --- | --- |
| Frame | `border: round $primary`, rather than the palette's `double`, so the two are distinguishable at a glance. Title `❯ Command Line` with `❯` in bold `#FFD700`. |
| Command path tokens (`bead show`) | bold `#00D7AF` (the palette's key color) |
| Options (`--status`, `-P`) | `#87D7FF` |
| Values / positionals | default text. Values of a known kind get their entity glyph in the popup, not inline. |
| Quoted strings | a warm accent, opaque. Follow `test_prompt_bar_palette_safety.py`: opaque colors, and avoid xterm-256 slots 16–21. |
| Advisory problems | red undercurl on the token, plus a message in the signature line |
| Ghost suggestion | `text-area--suggestion`, dim italic |
| Block status gutter | `⠋…` spinner in gold (running) · `✓` green · `✗` red with the exit code · `⊘` dim (killed) · `↗` (ran in the foreground terminal) |
| Selected block | a left `▌` bar in `#00D7AF`, as in the Agents list |
| Popup rows | value · kind badge · status/metadata column · description, with fuzzy match runs highlighted via `append_highlighted` |

### 5.3 Completion behavior ("better than a shell", concretely)

1. **Slot-aware.** The engine resolves the cursor into one of these slots: subcommand,
   option name, option value, positional value, or remainder. It knows about
   `--opt=value`, stacked short flags, `--`, and remainder positionals such as
   `proc run -- CMD`.
2. **Sources, in priority order.**
   - **TUI in-memory entities** (agents, beads, procs, projects, Patches): instant,
     fresh, richly described.
   - **The spec**: subcommands, options, choices.
   - **`candidates_for(kind)`** in a debounced worker (~80 ms), cached per kind, for
     kinds the TUI doesn't hold in memory (flags, xprompts, skills, memory, models…).
   - **Paths.**
   - **History-derived values.**
3. **Selection first.** The selected entity is ranked first for a matching kind and
   marked `◆ … sel`.
4. **Fuzzy, not prefix.** Ranking uses Rust `fuzzy_match` with match-run highlighting.
   Exact-prefix hits outrank fuzzy ones.
5. **Grammar-aware suppression.** Already-used non-repeatable options and the other
   members of a used mutex group are hidden. Repeatable options stay.
6. **Live signature help.** The usage line highlights the active slot. On the
   highlighted option it shows that option's summary, choices, `repeatable`/mutex notes
   and default. This needs `required`, metavar and default added to the spec (§6.1).
7. **Ghost text from history, fish style.** It is cwd-aware, uses Textual's
   `TextArea.suggestion`, and `→` accepts it.
8. **Advisory validation, never gatekeeping.** The engine flags an unknown subcommand or
   option, an invalid choice, a missing required positional, and a "this command asks
   for confirmation; add `-y`" warning. **Enter always runs.** argparse is the authority
   and reports its error in the block.

### 5.4 Keys inside the panel (all configurable under `ace.keymaps`)

| Context | Key | Action |
| --- | --- | --- |
| INSERT | `⇥` / `shift+⇥` | accept or cycle completion |
| INSERT | `↑` `↓` / `ctrl+p` `ctrl+n` | move in the popup; with no popup, prefix-filtered history |
| INSERT | `→` at end of line | accept the ghost suggestion |
| INSERT | `ctrl+r` | fuzzy history search, shown in the same popup |
| INSERT | `⏎` | run. If the user *navigated* to a candidate, accept it first (zsh menu-select rule). |
| INSERT | `ctrl+c` | clear the line; on an empty line, hide the panel |
| INSERT | `esc` | on an empty line, hide the panel; otherwise go to NORMAL (house two-stage convention) |
| INSERT | `;` on an empty line | hop to the Command Palette (R5) |
| NORMAL (input) | `esc` | hide the panel. Running commands continue. |
| NORMAL (input) | `k` / `↑` | move into the transcript (block navigation) |
| Block nav | `j` `k`, `g` `G` | select a block, top or bottom |
| Block nav | `o` / `⏎` | expand or collapse; for huge output, open in the pager (`PagerScreen`) |
| Block nav | `K` | kill a running block, with confirmation (same verb as the Procs pane) |
| Block nav | `r` / `e` | rerun / load the command into the input for editing |
| Block nav | `y` / `Y` | copy output / copy command |
| Block nav | `p` | open Admin Center → Procs with this proc selected; returns to the Command Line on close |
| Block nav | `x` | remove the block from the transcript (the proc record stays) |
| Block nav | `i` / `a` / `:` | back to the input in INSERT mode |

### 5.5 Leaving and returning

- **Hiding never interrupts anything.** Each block is a view of a durable proc.
- **You can hide mid-edit.** An unsent line is kept as a draft and restored when you
  reopen.
- **Finish notice while hidden.** If a command finishes while the panel is hidden, a
  toast appears: `✓ bead list · exit 0 · 0.9s — : to view`. Failures toast at error
  severity. Commands that finish while the panel is visible don't toast.
- **Reopening is instant.** `:` reopens the panel from app-held state with the
  transcript intact. Blocks that finished while it was hidden get an "unseen" dot.
- **The transcript survives a TUI restart.** On first open after a restart, it
  restores the newest command-line procs from the store: tag `command-line`, last 24 h,
  up to 20. They sit below a `── earlier ──` divider.
- **You can jump back from Procs.** In Admin Center → Procs, `⏎` on a command-line row
  opens it in the Command Line, mirroring how `⏎` on a monitor row opens its agent.
- **Quitting is unchanged.** Running command-line procs appear in the existing "procs
  still running" quit dialog.

### 5.6 Output fidelity

**Environment overlay** for every command-line proc:

- `PYTHONUNBUFFERED=1`. Without it, `print()`-based output block-buffers on the pipe
  and "streaming" stops streaming.
- `FORCE_COLOR=1`
- `COLUMNS=<transcript inner width>`. Rich honors it, and the probe captured a
  100-column colored table correctly.

**Rendering.** `\r` overwrite collapse, then drop non-SGR CSI cursor sequences, then
`Text.from_ansi`. Rendered `Text` is cached per `(proc_id, log offset)`.

- Collapsed blocks show only the last 12 lines.
- Expanded blocks render at most 2,000 lines, and link to the pager beyond that.

**Rich Live and progress widgets** don't animate on a non-terminal. That is desirable:
they print their final state and no cursor garbage.

**Prerequisite R7:** `bead` color resolution (`bead/cli_dep_render.py:34`) and the other
`isatty()` color branches must honor `FORCE_COLOR`. Otherwise the two most-used command
families render gray.

### 5.7 Run policies (R2)

These are declared in a table next to `PATH_OVERRIDES` in `sase.completion`, so new
commands are classified where the grammar lives, with a drift test that every path in
the table exists in the spec. Initial classification, from the sweep:

| Policy | Commands |
| --- | --- |
| `foreground` (suspend the TUI, run in the terminal, return) | `run` with no prompt or with `.` (editor/fzf) · `prompt edit` / `prompt run` (fzf) · `artifact open` · `pager` · `tmux-agent` · `gate act` edit actions · `sudo approve` without `--approve`/`--deny` |
| `deny`, with a suggested alternative | `tui` ("you're in it") · `service run` / `scheduler run` / `mobile gateway start` / `lsp` (foreground servers → `service start`) |
| `proc`, with a streaming hint | `proc show --follow` · `monitor show --follow` · `agent wait` (fine as procs; they settle on their own) |
| `proc` (default) | everything else, including `-h`/`--help` on any path, and `screenshot` (it drives its own private tmux window, and agents already run it without a TTY) |

---

## 6. Design: architecture

```
            ┌────────────── TUI process ───────────────────────────────────────────┐
 keystroke ─▶ CommandLineScreen (ModalScreen, view only)                            │
            │   ├─ input (SingleLineVimTextArea + suggestion) ─┐                    │
            │   ├─ popup / signature / transcript widgets       │ sync, <2 ms       │
            │   └─ CommandLineSession (app-held state) ◀────────┘                   │
            │        │ resolve(spec, line, cursor)  ◀── sase.completion.line (pure) │
            │        │ in-memory sources (agents/beads/procs/projects/patches)      │
            │        │ async: candidates_for(kind) worker, debounced, last-wins     │
            │        ▼                                                              │
            │   submit_command_line_proc() ──worker──▶ submit_proc_request()        │
            │        ▲                                   (no operation, tagged)     │
            │   ProcObserver: exit-code watch ◀── store rows (status, exit_code)    │
            │   ProcLogCursor (offset tail, only visible running blocks)            │
            └───────────────────────────────────────────────────────────────────────┘
 spec cache: `sase completion spec --descriptions -j -o ~/.sase/completion/cache/…json`
             (subprocess, keyed by runtime_identity()+source_fingerprint())
```

### 6.1 The spec pipeline

- **Extend the spec model.** Add `OptionSpec.required`, `OptionSpec.metavar`, a
  display-safe `default`, and `CommandSpec.run_policy`.
- **Add a flag to the CLI.** `sase completion spec -d/--descriptions` keeps summaries
  instead of digests. The name follows `cli_rules`: a short alias, alphabetized
  options.
- **Build the cache in a subprocess, not in the TUI process.** The full build costs
  about 0.77 s of pure-Python, GIL-heavy work. In-process it would contend with the
  event loop and pull all 63 registrars into the long-lived TUI. It would also describe
  the TUI's *imported* code rather than the on-disk code that command-line procs
  actually run (tui_perf rule 15).
- **Key the cache by `runtime_identity()` + `source_fingerprint()`,** the key the
  shell-grammar cache already uses (`completion/runtime_cache*.py`).
- **Load it at idle** after the startup stopwatch (tui_perf rule 9), or on the first
  `:`. The JSON load takes about 3 ms plus `from_json`, in a thread.
- **The panel never waits for the spec.** It opens instantly; until the spec lands,
  history suggestions work and the popup shows "indexing commands…".

### 6.2 The completion engine (`sase.completion.line`, frontend-neutral)

A pure module with no Textual or Rich imports, data in and data out:

```python
resolve(spec: CompletionSpec, line: str, cursor: int) -> LineContext
#   tokens (with spans and quote state), deepest CommandSpec, slot kind
#   (SUBCOMMAND | OPTION_NAME | OPTION_VALUE | POSITIONAL | REMAINDER),
#   slot target (OptionSpec | PositionalSpec), prefix + replace span,
#   used dests (non-repeatable and mutex suppression), advisory diagnostics,
#   signature (usage segments + active index), run policy
static_candidates(ctx) -> list[Candidate]   # subcommands, options, choices
merge_rank(ctx, sources: list[list[Candidate]], selected: Candidate | None) -> list[Ranked]
```

It is tested with golden cases against the checked-in
`tests/completion/snapshots/cli_spec.json`, with a perf test budget of under 2 ms per
`resolve` on the full spec. The TUI supplies the dynamic sources; the engine never does
I/O.

### 6.3 Proc plumbing

- **`submit_command_line_proc(tokens, cwd, width)`** builds a `ProcSubmitRequest`:
  - `argv = sase_command_argv(*tokens)` (same interpreter as the TUI)
  - `command = ["sase", *tokens]` (display)
  - `label = ": " + shlex.join(tokens)`, `tags = ("command-line",)`, `origin = "ace"`
  - `session_id = TUI session`, `cwd`, and the env overlay from §5.6
  - **no `operation`** (so exit-code settlement applies) and **no `service` block**
  - no concurrency key, since running the same command twice on purpose is legitimate.
    A 300 ms double-Enter guard prevents accidental duplicates.
- **Submission:**
  - Submit in a worker thread. `submit_proc` blocks for 0.26–0.50 s.
  - Before that, register an observer placeholder so the block and the gear appear
    immediately.
  - If submission fails, the block turns red with the error and the line is restored
    to the input.
- **Register the new producer site** in `_proc_producer_sites_actions.py`.
- **Observer extension.** Add `register_exit_watch(proc_id)`, which completes from the
  row's `status` and `exit_code` without decoding a typed result. Allow multiple
  detail/tail subscriptions (ref-counted) instead of the single `set_detail_proc`, so
  the Procs pane and the Command Line don't fight.
- **`ProcLogCursor`** (in `sase.procs.logs`) replaces 400-line re-reads for running
  blocks:
  - It holds `(inode, offset)` and reads only the new bytes.
  - It detects rotation (inode change or shrink), drains `.log.1`, then restarts.
  - It is polled at 150–250 ms, only for *visible running* blocks and only while the
    panel is shown, via pump-free tasks (tui_perf rule 2).
- **Kill** goes through the same durable `sase proc kill` path `!!` uses.
- **Procs pane additions:**
  - `ObservedProc.tags` and a `tag:` query field, so `tag:command-line` works.
  - A `proc_focus_target` argument to `_open_config_center` (like `log_error_target`)
    for "open in Procs".

### 6.4 History

Use a new store, `~/.sase/command_line_history.json`, with `fcntl` locking and atomic
writes, following `history/prompt_store.py`. Do not extend the unlocked
`command_history.json`. Each entry holds:

- line and cwd
- last exit code
- count and `last_used`.

Up/Down history is filtered by the typed prefix. `ctrl+r` fuzzy search reuses the
popup. Ghost suggestions come from the most recent history match for the prefix, with
matches from the same cwd preferred.

### 6.5 Performance rules this must honor (from `tui_perf`)

- **Keystrokes stay synchronous and in memory.** The keystroke path is the spec walk,
  in-memory sources and Rust fuzzy ranking. It never spawns a process, never calls
  `resolve_ref`, never takes a lock (rule 11).
- **Async results are discarded if stale.** Provider results come back through a
  worker, re-capture the current line and cursor after the `await`, and are dropped if
  the line changed (rule 4, last request wins).
- **Timer callbacks stay thin.** Tail and render work runs in pump-free tasks, and a
  running block repaints only its own `Static` (rules 2 and 6).
- **Budgets:**

  | What | Target |
  | --- | --- |
  | Panel first paint | < 50 ms |
  | Keystroke → popup | p95 < 16 ms (`SASE_TUI_PERF`-style probe) |
  | Async kinds | < 150 ms |
  | Pump stalls | zero, checked with `tui_stalls.jsonl` during a stress run |

### 6.6 The Rust-core boundary (a decision point)

The core-memory litmus test ("would another frontend need it to match?") leans toward
putting a line-completion engine in `sase_core`. But:

- the grammar is Python argparse
- the value providers already live in Python `sase.completion`, and that is how the
  shipped shell completion works
- no second consumer exists yet. The decision record `corpus-before-mechanism` argues
  against building shared machinery ahead of demand.

**My recommendation:** build `sase.completion.line` in Python, with JSON-shaped
request and result types. Port it to Rust the moment a second frontend adopts it:
`sase-nvim`'s `:Sase …`, mobile or web. Please confirm this explicitly, because it
bends a core-memory rule.

---

## 7. Reliability and edge-case matrix

| Situation | Behavior |
| --- | --- |
| TUI crash or restart mid-command | The proc continues under its supervisor. The transcript restores from store rows plus logs. |
| Log rotation during a long command | `ProcLogCursor` drains `.log.1` and resumes. The block shows `⋯ earlier output rotated` if bytes were lost. |
| A command asks for confirmation | stdin is `/dev/null`, so it fails closed (declines or errors). The advisory lint suggests `-y` before running. |
| A command reads stdin (`notify create`, `comments`) | EOF. It is policy-classified; its signature line notes "reads stdin — pass input via flags/files". |
| Spec cache stale after an upgrade | The runtime identity changes, so the cache is rebuilt in a subprocess. Stale-but-present specs are used until then. Harmless, because argparse stays authoritative. |
| A provider raises an exception or is slow | Empty source plus a subtle `⚠ <kind> unavailable` in the popup footer. Typing never stalls. |
| Very chatty output | 2 MiB log cap (existing), a render cap per block, collapsed tails. The pager is the escape hatch for more. |
| Same command twice quickly | The double-Enter guard drops it. A deliberate rerun (`r`) is allowed. |
| `:` pressed inside another modal | Not available, same as the palette today. The Config pane keeps `:` for jump-to-path. |
| Remote or fleet machines | Out of scope. Commands run on the TUI host, and the header chip shows the host when fleet mode is on. |

---

## 8. Rollout (epic-shaped)

| Phase | Content | Size |
| --- | --- | --- |
| **P0 — prerequisites** | **R7 color contract:** a shared `resolve_color(auto)` that honors `NO_COLOR` → `FORCE_COLOR`/`CLICOLOR_FORCE` → `isatty`, used by the bead renderers and other `isatty` branches. **Spec extensions** (§6.1), the run-policy table plus its drift test, and `completion spec -d`. | M |
| **P1 — engine** | `sase.completion.line`: tokenizer, resolver, static candidates, merge/rank, advisory diagnostics, signature. Golden and perf tests. | M |
| **P2 — proc plumbing** | `submit_command_line_proc`, observer exit-watch plus multiple tail subscriptions, `ProcLogCursor`, producer-site registration, Procs `tag:` field, `proc_focus_target`. | M |
| **P3 — panel (beta flag `ace_command_line`)** | Drawer screen, input with highlighting and ghost text, popup, signature line, transcript blocks and actions, history store, hide/reopen/toasts/restore, the `open_command_line` action (unbound; also reachable from the palette while beta). Pilot tests and PNG goldens for empty, typing, running and error states. Both flag states tested. | L |
| **P4 — policies and built-ins** | Foreground runs via `app.suspend()`, deny messages, `cd`/`clear`/`help`/`history`, the working-context chip, derived "FOR <selection>" suggestions. | M |
| **P5 — flip and land** | `:` → `open_command_line`, `;` → palette only, hop keys (R5), the one-time tip, all docs/help/onboarding/tests/goldens (Appendix A); remove the flag. | M |
| P6 — optional | `:!shell` (R9) and retiring `!!`; a palette "Run in Command Line" fallback row; "tip: key `x` does this"; clickable entity refs in output; generated forms. | — |

---

## 9. Open questions for you

1. **Name.** "Command Line" (recommended), "Command Mode", or "Console"?
2. **Default working directory.** The smart default in R4, or always the TUI's launch
   cwd?
3. **Transcript scope after a restart.** Restore the last 24 h of command-line procs
   from this machine (recommended), or this session only?
4. **`:!shell` and `!!` retirement.** In scope as P6, or leave `!!` alone?
5. **Rust boundary.** Is Python-first `sase.completion.line`, with a port on the
   second consumer, acceptable (§6.6)?

---

## 10. Recommended solution

Build a **`:` Command Line**: a bottom-anchored drawer that runs `sase` commands (with
an implicit `sase` prefix) as **ordinary durable procs tagged `command-line`**. Stream
their output inline as Warp-style blocks, and make hiding the panel free: procs keep
running, stay visible in Admin Center → Procs (`tag:command-line`), toast when they
finish, and restore after a TUI restart. Move the Command Palette to `;`, with one-key
hops between the two surfaces.

Win on completion with what only the TUI has:

- in-memory, selection-aware entity candidates
- fuzzy ranking with rich descriptions
- live signature help from an extended `sase.completion` spec, built in a subprocess
  and cached by runtime identity
- advisory validation
- fish-style history ghost text.

A frontend-neutral `sase.completion.line` engine powers all of it.

Make it reliable with:

- an exit-code watch path instead of `_submit_durable_proc`
- an offset-based `ProcLogCursor`
- a run-policy table (`proc` / `foreground` via `app.suspend()` / `deny`)
- a visible working-context chip with `cd`
- a `FORCE_COLOR`/`COLUMNS`/`PYTHONUNBUFFERED` output contract, which first requires
  fixing `isatty`-only color resolution.

Ship it in phases behind the beta flag `ace_command_line`. Flip `:`/`;` and remove the
flag only in the final phase.

---

## Appendix A: touchpoints for the `:` → Command Line / `;` → palette flip

Line numbers come from the codebase sweep and may drift.

- **Config and keymaps:**
  - `src/sase/default_config.yml:799`
  - `keymaps/app_keymaps.py` (a new field; the YAML is the only source of defaults)
  - `keymaps/metadata.py` `_BINDING_META`
  - `commands/_app_metadata_display.py`: the new row, and remove the palette's `":"`
    alias
  - the new `action_open_command_line`
  - `actions/artifacts.py` `NON_PRS_ARTIFACT_ACTIONS`
  - `commands/_availability_artifacts.py` allowlist
  - optionally the fallback `tui/bindings.py`
- **Help, onboarding and palette text:**
  - `help_modal/{agents,patches,axe,patches_artifact}_bindings.py`
  - `widgets/tab_quickstart.py`, `widgets/agent_onboarding.py` (which also feeds the
    Guide view)
  - the palette hint's `key::` example in `command_palette_modal.py:45-47`
- **Docs:**
  - `docs/ace.md` (line 16, the global key table, the Command Palette section at about
    line 3457)
  - the custom-mode example `prefix: ";"` at `docs/ace.md:6014`, which already collides
    with the palette today.
- **Tests:**
  - `test_keymaps_{defaults_panels,validation,app_bindings}.py`
  - `test_command_catalog{,_guards}.py`, `test_command_palette_{modal,wiring,e2e}.py`
  - `test_keymaps_display_help_key_display.py`, `test_agent_group_revival_e2e.py`
  - PNG goldens: `tests/ace/tui/visual/test_ace_png_snapshots_{agents_onboarding,changespecs_onboarding,help_panel,agents_fleet}.py`,
    via `just fix-tui-screenshots`.
- There is no user override in `~/.config/sase/sase.yml` today, so the default flip
  takes effect without config edits.

## Appendix B: external precedents that informed the design

- **Vim / Neovim.** `:` as the command line, the wildmenu, `:!` suspending to the
  shell, and two-stage Escape.
- **Helix.** A bottom command line with a completion menu above it and docs for the
  typed command.
- **k9s.** `:` to command a TUI, with ghost-text completion.
- **fish.** History autosuggestions accepted with `→`.
- **Warp.** Command-plus-output "blocks" with status.
- **VS Code.** Prefix hopping between quick-open surfaces.
- **Fig / Amazon Q.** Spec-driven completions with descriptions and dynamic
  generators; `sase.completion`'s spec plus providers is the same idea, already
  built.
