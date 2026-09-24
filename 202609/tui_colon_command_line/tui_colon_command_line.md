# A `:` Command Line for the SASE TUI: Build It on Ordinary Tagged Procs, With Four Changes to the Plan

Date: 2026-09-24. This report consolidates three independent reports on this request: "bind the
Command Palette to `;` only and give `:` to a new command-mode panel that runs `sase` commands from
the TUI, with better completion than a shell, output inline by default, and procs you can leave
running and find in Admin Center → Procs." I re-checked every claim the reports disagreed on against
sase `b6b9f4f59` and sase-core `master`. I also ran new measurements where a report's evidence was
weak or missing: spec value-kind coverage, proc latency, `FORCE_COLOR` behavior, proc retention, and
`--yes` coverage. I changed no code, and all proc probes used a throwaway `SASE_HOME`.

| Dependency | Preserved report | Immutable snapshot | Main contribution |
| --- | --- | --- | --- |
| `research.2h.cld` | [cld](tui_colon_command_line__cld.md) | `file:explicit:118812b4aa5498ef5b5cec9a` | The deepest ground truth. Found that `_submit_durable_proc` settles a plain command as `missing-result` and that service oneshots are hidden from Procs. Measured latency and color. Wrote the run-policy table, the full UX (Warp-style blocks, ghost text, signature line) and the flip-touchpoint inventory |
| `research.2h.mus` | [mus](tui_colon_command_line__mus.md) | `file:explicit:fff58600897f6a487693cbeb` | Build a `sase`-argv runner, not a shell. Treat destructive commands as a design problem. Never inject flags silently. Add a read-only MVP phase and a PNG regression gate from day one |
| `research.2h.gem` | [gem](tui_colon_command_line__gem.md) | `file:explicit:de1e7a29a02448e5961f9b65` | A shell-vs-TUI completion capability table. A dual-pane "candidates + docs" card. A panel state machine. Ex-style built-ins and a re-attach flow |

No predecessor chat transcripts were read.

---

## Bottom line

**Yes, build it. This is a good idea, and `:` is the right key.** The CLI has 365 leaf commands and
the TUI's keymap reaches only a small part of them. The TUI also knows things a shell never can: your
current selection, live entities, and room for rich descriptions. All four analyses agree on the
shape:

- `;` opens the Command Palette (TUI actions).
- `:` opens a separate panel for composing `sase` commands, with an implicit `sase` prefix.
- Commands run as durable procs, and hiding the panel never interrupts them.

Four changes to the plan are needed. Without them the feature will feel unreliable or ugly:

1. **Not every command can be a proc.** Procs run with `stdin=/dev/null` and no TTY. Commands that
   need `$EDITOR`, fzf, a pager or tmux must suspend the TUI and run in the real terminal, like vim's
   `:!`. `sase tui` and foreground servers must be refused (§5.7).
2. **Use a new submission path.** Command-line procs are **ordinary procs tagged `command-line`**.
   They must not go through `_submit_durable_proc`, which needs an operation and settles a plain
   command as `error / missing-result`. They must not be service oneshots either (the `!!` path),
   because the Procs tab hides those by default.
3. **Output needs a fidelity contract.** Every command-line proc gets `FORCE_COLOR`, `COLUMNS` and
   `PYTHONUNBUFFERED`. The `bead` renderers must first learn to honor `FORCE_COLOR`, because today
   they print no color at all under a pipe.
4. **Completion is only as good as the grammar's annotations, and they are thin.** *(New.)* Only 101
   of 688 value-taking options (15%) and 94 of 224 positionals (42%) declare a value kind. There are
   no kinds yet for gates, tool runs or task types. Filling these gaps is a prerequisite, and it
   improves shell completion as well.

Two more findings from this consolidation shape the architecture:

- *(New.)* **Proc retention is one shared bucket of 100 finished procs.** Heavy command-line use would
  push agent-launch and Patch-operation procs out of history. Command-line procs need their own
  retention bucket. Named service procs already get one.
- **Put the line resolver in `sase_core`, not in Python.** This departs from `cld`. sase-core already
  hosts editor completion, fuzzy ranking and frozen catalog handles, and the core-memory boundary
  rule is explicit.

The full recommendation is in [§11](#11-recommended-solution).

---

## 1. How the reports' disagreements were resolved

| Question | cld | mus | gem | Resolution (evidence) |
| --- | --- | --- | --- | --- |
| Panel geometry | Bottom-anchored `ModalScreen` drawer | Bottom-docked bar that grows into a panel | Centered, top-weighted modal; docking causes reflow | **Bottom-anchored `ModalScreen`.** gem's reflow objection applies to docking into the main layout, not to a modal aligned to the bottom. The bottom edge matches vim, Helix and k9s, and it sets the command line apart from the centered palette at a glance. |
| Submission path | Ordinary proc via `submit_proc_request`: no `operation`, `origin="ace"`, tag `command-line` | "The same supervisor path bgcmd uses" | `submit_proc_request(origin="command-mode")` | **cld.** The bgcmd path creates service oneshots, which the Procs default query `-service` hides (`default_config.yml:306`). A new origin would also lose the observer's cross-session relevance rule `proc.origin == "ace"` (`_proc_observer_store.py:127-146`), so procs from a restarted TUI would drop out of view. Use `origin="ace"` plus a tag. |
| Cost to build the spec | 0.32 s import + 0.45 s build | — | 1.68 s | **About 0.4 s warm** (0.07 s import + 0.34 s build, re-measured). gem's figure was probably a cold import. Either way, cache the spec and never build it on the UI thread. |
| Extra cost of running as a proc | About 1 s to first byte | — | "50–80 ms" | **cld.** Re-measured: direct `sase version` takes 0.34–0.37 s; `sase proc run -w -- sase version` takes 0.97–1.34 s. The UI must be optimistic and show the block at once. |
| Quick queries run in-process, not as procs | No, everything is a proc | — | Yes (Adjustment 4) | **No.** Running the CLI in-process pulls argparse registrars, `sys.exit`, stdout capture and global state into the TUI. It would also run the TUI's *imported* code, not the on-disk code (`tui_perf` rule 15). gem's real worry was store bloat; the dedicated retention bucket (§6.4) solves that. Only the spec-rendered `help` built-in skips the proc. |
| Non-interactive flags | Advisory lint that suggests `-y` | Never inject flags | Inject `--yes` / `--non-interactive` automatically | **Never inject silently.** Confirmations already fail closed under `/dev/null`: the helpers check `stdin.isatty()` or catch `EOFError`, e.g. `bead/cli_admin.py:405`, `prompt/cli_maintenance.py:43`, `agents/cli_restart.py:180`. Only 16 leaves have `-y/--yes`, so a block can offer an explicit, visible "rerun with `-y`" (§5.7). |
| Confirming destructive commands | None; Enter always runs | Denylist plus a second confirmation | — | **No gate. Show a `⚠ writes` chip in the signature line.** A shell runs `bead close` at once too. The CLI owns its own safety prompts, and a second denylist would drift. Accidental runs are handled by the zsh menu-select rule: Enter on a candidate you navigated to accepts it and does not run. |
| History store | New locked `command_line_history.json` | Extend `command_history.json` | — | **cld.** `history/command.py` has no lock, and its entries are shaped for shell strings with `project`/`cl_name`. `history/prompt_store.py` shows the locked, atomic pattern to copy. |
| Value candidates in-process or subprocess | In-process worker, TUI entities first | Subprocess, to respect the import quarantine | In-process worker | **In-process, TUI entities first.** The quarantine only runs one way: catalog modules must not import `textual`/`rich`/`sase.ace` (`candidates/catalog.py` docstring). The TUI importing them is fine. See §6.3 for two caveats. |
| Where the resolver lives | Python `sase.completion.line`, ported to Rust later | Not addressed | Python | **`sase_core`** (§6.2). |
| Name | "Command Line" | "command-mode" | "Command Mode" | **"Command Line."** In this TUI, "mode" already means a transient prefix mode (`bang_mode`, `bead_issue_mode`, leader, custom modes), and vim calls `:` the command line. |
| Ex built-ins | `cd`, `clear`, `help`, `history` | — | `:q`, `:w`, `:procs`, `:last`, `:palette` | **cld's set.** `:w` has no meaning here, and `:q` duplicates `q` while adding a new way to quit by accident. `:last` and `:palette` are covered by reopen-restores-transcript and the hop key. |
| Escape | Two-stage (INSERT → NORMAL → hide) | Esc closes | Esc / `q` closes | **Esc on an empty line hides the panel. Otherwise the first Esc goes to NORMAL (for block navigation) and the second hides.** The draft is always kept, so hiding costs nothing. This matches the house `SingleLineVimTextArea` convention. |

---

## 2. Verified ground truth

Each fact below was confirmed at `b6b9f4f59`, except where it is marked as coming from a report.

**Keys and palette**

- `open_command_palette: "colon,semicolon"` is at `src/sase/default_config.yml:804`. No user
  override exists in `~/.config/sase/sase.yml`, so flipping the default takes effect with no config
  edits.
- Textual's built-in palette is off (`app.py:161`).
- `:` is already used, scoped, as "Jump to path" in the Admin Center Config pane
  (`config_pane_widget.py:52`). That binding stays.
- `docs/ace.md:6014` shows a custom mode with `prefix: ";"`, which already collides with the
  palette. Fix it during the flip.
- The palette only dispatches TUI actions. Nothing in the TUI talks to the `sase` CLI grammar, so this
  is a new execution path, not a palette extension (mus).
- `action_open_command_palette` builds a `CommandContext` holding the tab, the selected `patch`,
  `agent` and `axe_item`, and the mark counts. It has **no bead field**. "Active bead" ranking (gem)
  has to come through the selected agent or Patch.

**Procs**

- `ProcSubmitRequest` (`procs/request.py`) already has `tags`, `label`, `cwd`, `origin`, `session_id`,
  `project`, an `env` overlay and timeouts. `sase proc run` already exposes
  `-t/--tag`, `-l/--label`, `-c/--cwd`, `-s/--session` and `-p/--project`, so the CLI has everything
  the command line needs.
- The supervisor starts children with `Popen(..., stdin=DEVNULL, ..., start_new_session=True)`
  (`procs/supervisor.py:281-288`). No pty is involved.
- If a proc declares an `operation` and succeeds without a result path, it settles as
  `error / missing-result` (`procs/settlement.py:268-291`). `_submit_durable_proc` requires
  `operation:`.
- `ObservedProc` has `origin` but no `tags`. The Procs query dialect has `cmd`, `name`, `status`,
  `kind`, `monitor`, `service`, `exit`, `svc` and `project`, but no `tag` or `origin` field
  (`_proc_query.py:57-113`).
- The observer tails a single detail proc (`set_detail_proc`, `proc_observer.py:191`).
- The Procs pane renders ANSI through `Text.from_ansi` (`procs_pane_render.py:358`).
- *(New.)* **Retention:** `procs.history_limit: 100` (`default_config.yml:96`). In sase-core,
  `apply_retention` (`procs/store.rs:537`) gives every non-service proc one shared bucket of finished
  rows. Named service procs get their own per-name buckets (`SERVICE_PROC_HISTORY_LIMIT`). That is a
  ready precedent for a `command-line` bucket.

**The existing `!!` flow**

- `!!` opens three modals: ProjectSelect → WorkspaceInput → `CommandHistoryModal`.
- It then runs `sh -c CMD` as a transient service oneshot with up to 9 slots, and it can check out a
  Patch first (`axe/bgcmd_operations.py`).
- History goes to the unlocked `~/.sase/command_history.json`.

**CLI grammar and completion**

- The grammar is argparse: 63 top-level commands, 439 nodes, 365 leaves and 1,591 options.
  Plugins add no subcommands.
- `build_spec()` yields `CommandSpec`, `OptionSpec` and `PositionalSpec`. These already carry
  `kind`, `choices`, `repeatable`, `mutex_groups`, `default_child` and `is_remainder` (which settles
  mus's open question). They lack `required`, option metavars and defaults.
- `sase completion spec` swaps descriptions for digests.
- *(New.)* **Kind coverage** (`build_spec()` walk):

  | Slot | Total | With `kind` | `choices` only | Neither |
  | --- | --- | --- | --- | --- |
  | Value-taking options | 688 | 101 (15%) | 122 (18%) | 465 (68%) |
  | Positionals | 224 | 94 (42%) | 10 (4%) | 120 (54%) |

  - Most of the "neither" slots are free text such as `reason`, `limit`, `timeout` and
    `description`, and that is fine.
  - But many real entity slots have no kind:
    - `gate_ref` (4)
    - `run_id` (ToolRun, 2)
    - `selector` (memory, 4)
    - `alias` (11)
    - `task_type` (3)
    - `provider` (4, although a `PROVIDER` kind already exists)
    - `path` (9)
    - `id`/`name` on several paths.
  - Kinds for these go in `NAME_TABLE` / `PATH_OVERRIDES` (`completion/kinds.py`). There are no
    `GATE`, `TOOL_RUN`, `TASK_TYPE` or `SESSION` kinds at all.
- The parser keeps argparse's default `allow_abbrev`, so `--stat` is a valid spelling of `--status`.
  The resolver must not flag unique prefixes.
- `candidates_for(kind, prefix, *, project, limit)` filters by **prefix and applies the limit before
  any ranking** (`protocol.py:48`). Fuzzy ranking therefore needs a large limit, with ranking done in
  Rust.
- *(New.)* Provider latency re-measured in-process:

  | Kind | Latency |
  | --- | --- |
  | agent | 207 ms |
  | monitor | 78 ms |
  | xprompt | 12 ms |
  | patch | 9 ms |
  | proc | 7 ms |
  | flag | 8 ms |
  | bead (materialized store) | 5 ms |
  | project | 2 ms |

  Bead candidates returned **0 rows** until the beads sidecar was materialized (by a `sase bead list`
  run). Providers can quietly return nothing.
- The TUI already has `SingleLineVimTextArea`, `OptionList` dropdowns, Rust `fuzzy_match` with
  match-run highlighting, and Textual 8.0.1's `TextArea.suggestion` ghost text (`_text_area.py:411`).
- `app.suspend()` already appears 41 times in the TUI, e.g. `xprompt_browser_actions.py:125`.

**Output fidelity**

- Counting ANSI sequences with `FORCE_COLOR=1 COLUMNS=100` on a pipe:

  | Command | ANSI sequences |
  | --- | --- |
  | `bead list` | **0** |
  | `bead show` | **0** |
  | `agent list` | 528 |
  | `plan list` | 564 |
  | `memory list` | 502 |
  | `proc list` | 1,428 |
  | `flag list` | 210 |
  | `gate list` | 148 |
  | `monitor list` | 46 |
  | `tool list` | 20 |

- `bead/cli_dep_render.py:34 resolve_color` checks only `NO_COLOR`, then `isatty()`.
  `isatty()` appears in 32 `src/sase` files, which mix stdin and stdout checks, and none of them reads
  `FORCE_COLOR`.
- cld found that working directory changes results: `sase bead list` from `/tmp` prints
  `No issues found.`. Confirmed.

**Confirmations**

- 16 leaves take `-y/--yes`: `agent drain`, `agent restart`, `agent-cli install`, `bead doctor`,
  `bead history`, `bead work`, `doctor`, `init skills`, `machine remove`, `prompt delete`,
  `prompt prune`, `service init`, `service uninstall`, `skill init`, `telemetry cleanup-test-data`
  and `update`.
- 157 leaves take `-j/--json`.
- `agent restart` documents exit 2 as "refused with nothing changed". That is exactly the signal a
  "rerun with `-y`" action needs.

---

## 3. Is this a good idea? (critique)

### Why it's worth doing

- **Reach.** Many operations exist only in the CLI: `bead` admin, `memory`, `flag`, `tool`, `repo`,
  `artifact`, `gate` and `monitor`. Today you have to leave the TUI, and lose your context, to reach
  them.
- **The TUI can beat a shell at completion**, because it has:
  - live in-memory entities, ranked by the current selection
  - fuzzy matching with highlighted match runs
  - multi-column, colored descriptions
  - live signature help that highlights the active argument
  - advisory validation of mutex groups, choices and unknown options
  - history ghost text.

  zsh can do almost none of this (see gem's capability table).
- **Durability.** Every run is recorded, can be killed, shows in Procs and survives a TUI restart. A
  terminal tab gives you none of that.
- **It can replace `!!`'s three-modal flow for `sase` commands**, which is the worst "run a thing"
  experience in the TUI today.

### What would go wrong if built exactly as stated

1. **"Every command is a proc"** hangs or garbles every command that needs a TTY (R2).
2. **"Better completion"** is true only where the grammar is annotated. Today 68% of value-taking
   options have neither a kind nor choices (R7).
3. **Inline output** would be gray, the wrong width and block-buffered. Streaming would not actually
   stream (R6).
4. **Unbounded command-line procs** would push operational proc history out of the shared 100-row
   bucket (R8).
5. **Muscle memory.** `:` has opened the palette since the palette first shipped. Users who press `:`
   and get a different surface will stumble without hop keys and a one-time tip (R5).

### Real costs, none fatal

- **Two surfaces.** Users may confuse palette actions with CLI commands. Mitigate with distinct chrome,
  hop keys, and a palette fallback row: "Run `sase <query>` in Command Line".
- **A shortcut can weaken the TUI.** An easy CLI route can reduce the pressure to build proper TUI
  affordances. Optional mitigation: a "tip: `x` on the Agents tab does this" hint when a typed command
  has a keymapped equivalent.
- **Latency.** About 1 s to first byte. Fine with an optimistic UI; a warm supervisor can come later.
- **Flip churn.** The key flip touches about 20 files and four PNG golden suites (Appendix A).

**Safety is neutral to good.** Commands run with the user's own privileges, just as in a terminal.
Confirmation prompts fail closed because stdin is `/dev/null`.

**Would I take a different approach?** No. I would take the same approach with the adjustments below.
Section 8 lists the alternatives and why each was rejected.

---

## 4. Requirement adjustments (called out explicitly)

- **R1: Call it "Command Line", not "command mode".** Use the action `open_command_line`: `:` opens
  the Command Line and `;` opens the Command Palette. "Mode" already means prefix modes in this TUI.
  *(This one is your call; "Console" is the runner-up.)*
- **R2: Not everything becomes a proc.** Each CLI path gets a run policy:
  - `proc`: the default.
  - `foreground`: suspend the TUI and run in the real terminal. This is recorded in history but is not
    a proc.
  - `deny`: refused with a suggested alternative.
- **R3: An implicit `sase` prefix, plus four built-ins.** You type `bead list`; a leading `sase ` is
  accepted and stripped. The built-ins `cd`, `clear`, `help` and `history` run without a proc. A guard
  test asserts they never collide with a top-level command; none do today. The `help` built-in renders
  from the spec instantly, while `<cmd> -h` still runs argparse's real help as a proc.
- **R4: A visible working context.** A header chip reads `⌂ +sase · ~/…/sase`.
  - By default it **follows the TUI's current project** (the top-bar `+<project>` chip) and resolves
    to that project's primary checkout. It falls back to the TUI's launch cwd.
  - `cd <path|+project>` pins it, and the pin holds until `cd -`.
  - This follows the glossary: the current project supplies only defaults.
- **R5: Hop keys and a one-time tip.**
  - `;` typed into an **empty** Command Line switches to the palette.
  - `:` typed into an **empty** palette filter switches to the Command Line.
  - The first time `:` opens after the flip, show: "Command Palette moved to `;` (type `;` here to
    jump)".
- **R6: An output fidelity contract is a prerequisite.** Children get `PYTHONUNBUFFERED=1`,
  `FORCE_COLOR=1` and `COLUMNS=<transcript width>`. Before that, add one shared
  `resolve_color(auto)` (`NO_COLOR` → `FORCE_COLOR`/`CLICOLOR_FORCE` → `isatty`) used by the `bead`
  renderers and every other stdout-color branch.
- **R7 (new): Completion coverage is a prerequisite, enforced by a ratchet.**
  - Add `GATE`, `TOOL_RUN` and `TASK_TYPE` kinds, plus `SESSION` if needed, with providers.
  - Annotate the unkinded entity slots listed in §2.
  - Add a coverage test: every non-hidden value slot must be kinded, have choices, or be explicitly
    marked free-form (`text`/`int`/`duration`). Free-form slots then render as `‹duration›` hints
    instead of blank popups.
- **R8 (new): Command-line procs get their own retention bucket.** In sase-core's `apply_retention`,
  finished `command-line`-tagged procs are pruned against their own limit
  (`procs.command_line_history_limit`, e.g. 50) instead of the shared 100. The transcript must
  tolerate a proc that has been pruned.
- **R9: Command-line procs are ordinary tagged procs.** They use `origin="ace"`, the tag
  `command-line`, a label such as `: bead list --status open`, and no service block. That keeps them
  visible under the Procs default query and counted in the proc gear.
- **R10: Roll out behind a beta flag, and flip the keys last.** Use `ace_command_line`, created with
  `sase flag new` as epic scaffolding. While it is off, `:` still opens the palette. The final phase
  flips the keys and deletes the Off branch.
- **R11 (optional, later): `:!<shell>`.** Run a shell command in the same panel and working context as
  a `command-line` proc. Keep `!!` for its Patch-checkout and slot semantics until the two
  deliberately converge.

---

## 5. Design: UX

### 5.1 Anatomy

The panel is a bottom-anchored `ModalScreen` (`align: center bottom`):

- width about 96%, max 160 columns
- height grows with its content up to about 65%
- `ctrl+t` toggles between tall and full height.

The dimmed TUI stays visible above it. The transcript sits above the input and the completion popup
floats over the transcript, as in Helix.

**Empty state** (Agents tab, agent `research.2h.cld` selected):

```
╭─ ❯ Command Line ────────────────────────────── ⌂ +sase · ~/projects/github/sase-org/sase ─╮
│  RECENT                                                                                   │
│    bead show sase-17p                                                     2h ago  ✓       │
│    agent wait research.2h --timeout 10m                                   1d ago  ✗ 124   │
│  FOR research.2h.cld · selected agent                                                     │
│    agent show research.2h.cld                                                             │
│    chat show research.2h.cld                                                              │
│                                                                                           │
│ ❯ sase ▌                                                                                  │
│   63 commands · type to search · ⇥ complete · ; Command Palette                           │
╰─ ⏎ run · ⇥ complete · ↑↓ history · ^R search · esc hide ──────────────────── 0 running ───╯
```

The "FOR <selection>" rows are **derived, not curated**. They are every leaf command whose first
positional's `kind` matches the selected entity's kind, ranked by your own usage. New commands appear
automatically, and R7 makes more of them eligible.

**Typing, with the popup, signature line and `writes` chip:**

```
╭─ ❯ Command Line ────────────────────────────── ⌂ +sase · ~/projects/github/sase-org/sase ─╮
│ ✓ bead list --status open                           exit 0 · 0.9s · 14:02 · proc 470vtq   │
│ │ ◐ M sase-17p.4 · Stop, follow, and wait on a ToolRun by id ← sase-17p                   │
│ │ ⋯ 406 more lines · o expand                                                             │
│        ┌───────────────────────────────────────────────────────────────┐                  │
│        │ ◆ sase-17p     epic  in_progress  Tool-run hand-off      sel  │                  │
│        │   sase-17p.4   task  in_progress  Stop, follow, and wait…     │                  │
│        │   sase-17m     epic  open         Rename agent family…        │                  │
│        │ bead · 3 of 410 · fuzzy                            ⇥ accept   │                  │
│        └───────────────────────────────────────────────────────────────┘                  │
│ ❯ sase bead close sase-17▌                                                                │
│   bead close ‹ID…› [-n NOTE] [-r REASON] [-R canceled|done|superseded]          ⚠ writes  │
╰─ ⏎ run · ⇥ accept · ↑↓ move · esc normal ─────────────────────────────────── 0 running ───╯
```

On wide terminals (≥ 140 columns), when the highlighted item is a subcommand or an option, the popup
can grow a right-hand **doc peek**. This is gem's dual-pane card: the summary, arguments, choices and
defaults of the highlighted item. On narrow terminals it collapses into the signature line.

**Transcript blocks in NORMAL-mode block navigation:**

```
│ ✗ bead close sase-zz                                exit 2 · 0.7s · 14:05                 │
│ │ error: no such bead: sase-zz                                                            │
│ ⊘ agent restart foo                                 declined · exit 2 · y rerun with -y   │
│ │ Restart would stop foo and wipe 3 related agents.                                       │
│▌⠹ agent wait research.2h --timeout 10m             running 0:42 · proc 3aacsa      [sel]  │
│▌│ waiting for 3 agents (research.2h.mus, research.2h.gem, research.2h.cld) …              │
│ ↗ prompt edit                                       ran in terminal · exit 0              │
╰─ K kill · r rerun · e edit · o expand · y copy · p open in Procs · i input ── 1 running ──╯
```

### 5.2 Visual language (reusing the house palette)

| Element | Style |
| --- | --- |
| Frame | `border: round $primary`, not the palette's `double`, so the two are distinguishable at a glance. Title `❯ Command Line` with `❯` in bold `#FFD700` |
| Command-path tokens | bold `#00D7AF` (the palette's key color) |
| Options | `#87D7FF` |
| Values | default text. Popup rows carry the entity glyph and a kind badge |
| Quoted strings | a warm, opaque accent. Follow `test_prompt_bar_palette_safety.py`: opaque colors, and avoid xterm-256 slots 16–21 |
| Advisory problems | red undercurl on the token, with the message in the signature line |
| `⚠ writes` chip | dim amber, right-aligned in the signature line. It comes from the run-policy table's `writes` bit |
| Ghost suggestion | `text-area--suggestion`, dim italic |
| Block gutter | gold `⠋…` spinner (running) · green `✓` · red `✗` with the exit code · dim `⊘` (killed or declined) · `↗` (ran in the foreground terminal) |
| Selected block | a left `▌` bar in `#00D7AF`, as in the Agents list |

"Beautiful" needs a regression gate. Add PNG goldens from the first panel phase for the empty,
typing, doc-peek, running, error, declined and indexing states.

### 5.3 Completion behavior ("better than a shell", concretely)

1. **Slot-aware.** The cursor is resolved to one of: subcommand, option name, option value,
   positional or remainder. The resolver handles `--opt=value`, stacked short flags, `--`, remainder
   positionals such as `proc run -- CMD`, bare groups with a `default_child`, and argparse's
   abbreviated long options.
2. **Sources, in priority order:**
   - TUI in-memory entities (agents, procs, projects, Patches): instant and fresh
   - the spec (subcommands, options, choices)
   - `candidates_for(kind)` in a debounced worker (about 80 ms), cached per kind and project
   - paths
   - values from history.
3. **Selection first.** The selected entity, and the entities linked to it (a selected agent's or
   Patch's bead), rank first and are marked `◆ … sel`. Marked rows can fill a variadic slot in one
   keystroke, e.g. `agent kill ‹marked›`.
4. **Fuzzy, not prefix.** Ranking uses Rust `fuzzy_match` with highlighted match runs. Exact-prefix
   hits outrank fuzzy ones.
5. **Grammar-aware suppression.** Non-repeatable options already used, and the other members of a
   used mutex group, are hidden.
6. **Live signature help.** The active slot is highlighted. The highlighted option shows its summary,
   choices, repeatable/mutex notes and default; that needs `required`, metavar and default in the spec.
7. **Fish-style ghost text** from history, preferring the current working context. `→` accepts it.
8. **Advisory validation, never gatekeeping.** The resolver flags:
   - an unknown subcommand or option
   - an invalid choice
   - a missing required argument
   - "this command asks for confirmation".

   **Enter always runs.** argparse is the authority and reports its own errors in the block.

### 5.4 Keys inside the panel (all configurable under `ace.keymaps`)

| Context | Key | Action |
| --- | --- | --- |
| INSERT | `⇥` / `shift+⇥` | accept or cycle the completion |
| INSERT | `↑` `↓` / `ctrl+p` `ctrl+n` | move in the popup; with no popup, walk history filtered by prefix |
| INSERT | `→` at end of line | accept the ghost text |
| INSERT | `ctrl+r` | fuzzy history search, shown in the same popup |
| INSERT | `⏎` | run. If you navigated to a candidate, accept it instead (zsh menu-select rule) |
| INSERT | `esc` | on an empty line, hide; otherwise go to NORMAL |
| INSERT | `;` on an empty line | hop to the Command Palette |
| NORMAL | `esc` | hide the panel; running commands continue |
| NORMAL | `k` / `↑` | move into the transcript |
| Block nav | `j` `k` `g` `G` | select a block, or jump to the top or bottom |
| Block nav | `o` / `⏎` | expand or collapse; huge output opens in `PagerScreen` |
| Block nav | `K` | kill, with confirmation (the same verb as the Procs pane) |
| Block nav | `r` / `e` | rerun / load the command into the input for editing |
| Block nav | `y` / `Y` | copy the output / copy the command |
| Block nav | `p` | open Admin Center → Procs with this proc selected |
| Block nav | `x` | remove the block from the transcript (the proc record stays) |
| Block nav | `i` `a` `:` | back to the input in INSERT |

### 5.5 Leaving and returning

- **Hiding never interrupts anything.** Each block is a view of a durable proc, and an unsent line is
  kept as a draft.
- **A toast while hidden.** A command that finishes while the panel is hidden raises a toast, such as
  `✓ bead list · exit 0 · 0.9s — : to view`. Failures toast at error severity.
- **Reopening is instant.** `:` restores the panel from app-held state. Blocks that finished while it
  was hidden get an "unseen" dot. This covers gem's `:last` / re-attach.
- **Restore after a restart.** On first open after a TUI restart, the transcript restores the newest
  `command-line` procs from the store (last 24 h, up to 20) below a `── earlier ──` divider.
- **Jump back from Procs.** In Admin Center → Procs, `⏎` on a `command-line` row opens it in the
  Command Line, mirroring how `⏎` on a monitor row opens its agent.
- **Quitting the TUI** never kills command-line procs, because they are durable.

### 5.6 Output rendering

- Collapse `\r` overwrites, drop non-SGR CSI sequences, then apply `Text.from_ansi`. Cache the
  rendered `Text` per `(proc_id, log offset)`.
- Collapsed blocks show the last 12 lines. Expanded blocks render at most 2,000 lines, and link to
  the pager beyond that.
- Rich Live and progress widgets do not animate off a terminal. They print their final state and no
  cursor garbage, which is what we want.

### 5.7 Run policies and confirmation-aware blocks

The run-policy table lives next to `PATH_OVERRIDES` in `sase.completion`, so new commands are
classified where the grammar lives. A drift test checks that every path in the table exists in the
spec. Each row carries a `policy`, plus a `writes` bit that drives the chip.

| Policy | Commands (initial sweep, from cld) |
| --- | --- |
| `foreground` (suspend, run in the terminal, return) | `run` with no prompt or with `.` · `prompt edit` / `prompt run` · `artifact open` · `pager` · `tmux-agent` · `gate act` edit actions · `sudo approve` without `--approve`/`--deny` |
| `deny`, with an alternative | `tui` ("you're in it") · `service run` / `scheduler run` / `mobile gateway start` / `lsp` (→ `service start`) |
| `proc`, with a streaming hint | `proc show --follow` · `monitor show --follow` · `agent wait` |
| `proc` (default) | everything else, including `screenshot` |

**Confirmation-aware blocks** *(new; this merges mus's safety concern with cld's advisory model)*:

- Suppose the leaf has `-y/--yes` and was run without it.
- A non-zero exit (for `agent restart`, the documented "refused" exit 2) renders the block as
  `⊘ declined` with the command's own preview output.
- The block then offers `y`: "rerun with `-y`". The rerun appears as its own block, with `-y` visible
  in the command.
- Nothing is injected silently, and the user sees the CLI's own preview before confirming.

---

## 6. Design: architecture

```
            ┌──────────────────────────────── TUI process ────────────────────────────────┐
 keystroke ─▶ CommandLineScreen (ModalScreen, view only)                                  │
            │   input · popup · signature · transcript widgets                            │
            │        │ sync, < 2 ms                                                       │
            │   CommandLineSession (app-held: transcript, draft, cwd pin, history cursor) │
            │        │ resolve(line, cursor) ──▶ sase_core_rs.CommandLineGrammar (frozen) │
            │        │ in-memory sources (agents/procs/projects/Patches)                  │
            │        │ async: candidates_for(kind) worker · debounced · last request wins │
            │        ▼                                                                    │
            │   submit_command_line_proc() ──worker──▶ submit_proc_request()              │
            │        ▲                      (no operation · origin=ace · tag=command-line)│
            │   ProcObserver exit-watch ◀── store rows (status, exit_code)                │
            │   ProcLogCursor (offset tail; visible running blocks only)                  │
            └─────────────────────────────────────────────────────────────────────────────┘
 spec cache: `sase completion spec -d -j -o ~/.sase/completion/cache/<identity>.json`
             built in a subprocess · keyed by runtime_identity() + source_fingerprint()
```

### 6.1 The spec pipeline (Python: argparse is the source of truth)

- **Extend the model.** Add `OptionSpec.required`, `OptionSpec.metavar`, a display-safe `default`, a
  free-form marker (R7), and per-path `run_policy` / `writes`.
- **Add `sase completion spec -d/--descriptions`**, which keeps summaries instead of digests. This
  follows `cli_rules`: a short alias and alphabetized options.
- **Build the spec in a subprocess**, never in the TUI. A subprocess describes the on-disk code that
  procs will actually run (`tui_perf` rule 15) and keeps about 0.4 s of GIL-heavy work off the event
  loop.
- **Key the cache** by `runtime_identity()` + `source_fingerprint()`, as the shell-grammar cache
  already does.
- **Load it at idle** after the startup stopwatch, or on the first `:`. The panel never waits for
  it: until the spec lands, history works and the popup shows "indexing commands…".

### 6.2 The line resolver belongs in `sase_core`

cld proposed a Python `sase.completion.line` engine with a Rust port "on the second consumer". I
recommend building it in Rust from the start, for four reasons:

- **The core-memory boundary rule is explicit.** A frontend that has to match the TUI's behavior
  (for example sase-nvim's `:Sase …` or the mobile gateway) is core behavior. `docs/rust_backend.md`
  already keeps small parsers in Rust "for shared-core hygiene rather than user-perceived latency."
- **The pieces already exist in sase-core.**
  - `crates/sase_core_py/src/editor_completion/` hosts editor completion.
  - `sase_core::editor::fuzzy::fuzzy_match` is the ranking the popup uses anyway.
  - The frozen compiled-catalog pattern (`GlossaryCatalogHandle`, `AtReferenceInventory`) is exactly
    the shape needed: parse a 460 KB spec once, then resolve per keystroke.
- **The spec is already a wire format.** The resolver needs no argparse. Python keeps producing the
  spec and the dynamic values; Rust owns tokenizing, slot resolution, static candidates, merge and
  rank, diagnostics and the signature.
- **"Port later" rarely happens.** When it does, it doubles the golden-test work.

The API is `CommandLineGrammar(spec_json)`, with `.resolve(line, cursor)` returning a `LineContext`
and `.rank(ctx, sources, selected)`. It is tested against a spec fixture checked into sase-core, with
a p95 budget under 1 ms per `resolve`. Moving sase's `sase-core-revision.txt` pin is part of that
phase. If you would rather iterate in Python first, cld's plan is a workable fallback. But it bends a
core-memory rule, so decide it explicitly.

### 6.3 Dynamic value sources

- Prefer the TUI's in-memory entities. Use `candidates_for` only for kinds the TUI does not hold.
- Call it with a large limit, because the limit is applied before any ranking, and rank in Rust.
- Treat an empty result as possibly "store not materialized" rather than "no values". Show a subtle
  `⚠ <kind> unavailable` footer; never stall typing.
- The 207 ms agent provider must never sit on the keystroke path.

### 6.4 Proc plumbing

- **`submit_command_line_proc(tokens, cwd, width)`** builds a `ProcSubmitRequest` with:
  - `argv = sase_command_argv(*tokens)`, the TUI's own interpreter (`durable_ops.py:36`)
  - `command = ["sase", *tokens]`
  - `label = ": " + shlex.join(tokens)`
  - `tags = ("command-line",)`, `origin = "ace"`, and the TUI's `session_id`
  - the env overlay from R6
  - **no `operation` and no `service` block**.

  There is no concurrency key: running the same command twice on purpose is legitimate. A 300 ms
  double-Enter guard catches accidents.
- **Submit in a worker.** Submission blocks for 0.26–0.50 s (cld's measurement). Register an observer
  placeholder first, so the block and the gear appear at once. If submission fails, the block turns
  red and the line goes back into the input.
- **Register the producer site** in `_proc_producer_sites_actions.py`; the inventory test enforces
  this.
- **Observer changes.**
  - Add `register_exit_watch(proc_id)`, which settles from `status` and `exit_code` and never decodes
    a typed result.
  - Replace the single `set_detail_proc` with ref-counted tail subscriptions, so Procs and the Command
    Line do not fight over the one slot.
- **`ProcLogCursor`** (`sase.procs.logs`) replaces 400-line re-reads for running blocks.
  - It holds `(inode, offset)`, reads only new bytes, and drains `.log.1` on rotation.
  - It polls every 150–250 ms, only for *visible running* blocks, through pump-free tasks.
- **Retention bucket (R8).** This is one small Rust change beside the existing service bucket in
  `apply_retention`, plus the config key and binding plumbing.
- **Procs pane changes.**
  - Add `ObservedProc.tags` and a `tag:` query field, so `tag:command-line` and `-tag:command-line`
    both work.
  - Add a `proc_focus_target` to `_open_config_center` (like `log_error_target`) for "open in Procs".
- **Kill** goes through the same durable `sase proc kill` path the Procs pane uses.

### 6.5 History

- Use a new store, `~/.sase/command_line_history.json`, with an `fcntl` lock and atomic writes, as in
  `history/prompt_store.py`.
- Each entry records the line, the working context, the last exit code, a use count and `last_used`.
- Ghost text and ↑/↓ come from prefix-filtered history, preferring entries from the same working
  context.

### 6.6 Performance rules this must honor (`tui_perf`)

- **The keystroke path is synchronous and in memory:** the resolver handle, in-memory sources and Rust
  ranking. It never spawns a process, never calls `resolve_ref` and never takes a lock (rule 11).
- **Async results are stale-checked.** After the `await`, re-capture the line and cursor and drop the
  result if they changed (rule 4).
- **Tail and render work runs in pump-free tasks.** A running block repaints only its own `Static`
  (rules 2 and 6).
- **Budgets:** first paint under 50 ms · keystroke to popup p95 under 16 ms · async kinds under
  150 ms · zero stalls in `tui_stalls.jsonl` during a stress run.

---

## 7. Reliability and edge cases

| Situation | Behavior |
| --- | --- |
| TUI crash or restart mid-command | The proc continues under its supervisor. The transcript restores from store rows and logs |
| Proc pruned by retention | The block keeps its cached tail and shows `record pruned`. Restore skips it |
| Log rotation during a long command | `ProcLogCursor` drains `.log.1`. The block shows `⋯ earlier output rotated` if bytes were lost |
| A command asks for confirmation | It fails closed. A confirmation-aware block offers `y` to rerun with `-y` (§5.7) |
| A command reads stdin | It gets EOF. The signature line notes "reads stdin; pass input via flags or files" |
| Spec stale after an upgrade | The identity changes and the spec is rebuilt in a subprocess. The stale spec is used meanwhile; argparse stays authoritative |
| A provider fails, is slow or is unmaterialized | The source is empty and the popup footer shows `⚠ <kind> unavailable`. Typing never stalls |
| Very chatty output | The existing 2 MiB log cap, render caps and collapsed tails apply. The pager is the escape hatch |
| `:` inside another modal or input | Not available, as with the palette today. The Config pane keeps `:` for jump-to-path |
| Remote or fleet machines | Out of scope. Commands run on the TUI host; with fleet mode on, the chip shows the host name |

---

## 8. Alternatives considered

| Approach | Verdict | Why |
| --- | --- | --- |
| **`:` Command Line drawer + tagged durable procs** (the plan, adjusted) | ✅ Recommend | Matches vim, Helix and k9s. Keeps "pick an action" separate from "compose a command". Durable and observable |
| One omnibar with prefixes (VS Code: `>` actions, `:` CLI) | ❌ as the primary surface | Picking one row and composing token by token are different interactions. Ranking 365 CLI leaves together with the TUI actions degrades both. The hop keys give most of the benefit |
| Keep `:`+`;` on the palette and add a `>` switch inside it | ❌ instead · ✅ as well | Cheapest, but it hides the feature and gives up the vim affordance. Ship it as the hop key |
| Put CLI commands into the palette | ❌ | Ranking pollution, and argument entry does not fit a pick-one list. A single fallback row, "Run `sase <query>` in Command Line", is enough |
| Embedded pty terminal widget running zsh | ❌ | It brings back the shell completion we are trying to beat. Terminal emulation in Textual is fragile. Not durable, not in Procs |
| Run command-line procs on a pty, so `isatty()` is true and color and width come free | ❌ | Rich Live and progress output would write cursor animation into the durable log, which shows up as garbage in Procs and `proc show`. A pty on stdin turns fail-closed prompts into hangs. Pagers may auto-launch. The change touches every proc. The env contract (R6) is smaller and safer |
| Suspend to the terminal for everything | ⚠️ only as the `foreground` policy | Perfect fidelity, but it blocks the TUI and is neither durable nor inline |
| Run quick queries in-process (gem) | ❌ | Imports the CLI into the TUI, runs stale code, and bypasses the proc model. Retention bloat is solved by R8 instead |
| A generic shell runner as the primary surface | ❌ for now | Completion over arbitrary shell is intractable, and it would duplicate `!!`. `:!` is a later, optional phase (R11) |
| Generated forms (argparse → form fields) | 💡 later | Good for rare commands with many flags; a later "open as form" key could add it |
| Docked bottom widget instead of a `ModalScreen` | ❌ | Needs `check_app_action` gating for every row action while typing, plus focus juggling. Modals are the house pattern |

---

## 9. Rollout (epic-shaped)

| Phase | Content | Size |
| --- | --- | --- |
| **P0: prerequisites** | R6: shared `resolve_color(auto)` adopted by the `bead` renderers and every other stdout-color branch. R7: new kinds (`GATE`, `TOOL_RUN`, `TASK_TYPE`), slot annotations, and the coverage ratchet test. Spec extensions (§6.1), `completion spec -d`, and the run-policy/`writes` table with its drift test | M |
| **P1: resolver (sase-core)** | `CommandLineGrammar` frozen handle: tokenizer, slot resolver, static candidates, merge/rank, diagnostics, signature. Golden and perf tests, then the revision-pin bump in sase | M |
| **P2: proc plumbing** | `submit_command_line_proc`, exit-watch, ref-counted tails, `ProcLogCursor`, producer-site registration, the R8 retention bucket (sase-core), the Procs `tag:` field, `proc_focus_target` | M |
| **P3: read-only MVP panel (flag `ace_command_line`)** | Drawer, highlighted input, ghost text, popup, signature line, transcript blocks, history store, hide/reopen/toasts/restore. `open_command_line` is unbound and reachable from the palette. PNG goldens for every state, with both flag states tested. Dogfood list/show commands first, as mus suggested | L |
| **P4: policies and built-ins** | Foreground runs via `app.suspend()`, deny messages, confirmation-aware blocks, the `writes` chip, `cd`/`clear`/`help`/`history`, the working-context chip, "FOR <selection>" rows, marks filling variadic slots, doc peek | M |
| **P5: flip and land** | `:` → `open_command_line`, `;` → palette only, hop keys, the one-time tip, the palette fallback row, and every docs/help/onboarding/test/golden touchpoint (Appendix A). Delete the flag's Off branch | M |
| P6: optional | `:!shell` and convergence with `!!`; "tip: key `x` does this"; clickable entity refs in output; generated forms; a warm supervisor for latency | — |

---

## 10. Open questions for you

1. **Name.** "Command Line" (recommended), "Command Mode", or "Console"?
2. **Rust boundary.** Build the resolver in `sase_core` from the start (recommended), or accept cld's
   Python-first engine with a later port? The latter bends a core-memory rule.
3. **Working context.** Follow the current project's primary checkout with `cd` pinning
   (recommended), or always use the TUI's launch cwd?
4. **Retention.** Is a separate `command-line` bucket of about 50 finished procs right? Should
   `-tag:command-line` be added to the Procs default query, or should these procs show by default, as
   the request implies?
5. **Transcript after a restart.** Restore the last 24 h from this machine (recommended), or this
   session only?
6. **`:!shell` and `!!`.** Bring them in as P6, or leave `!!` alone?

---

## 11. Recommended solution

Build a **`:` Command Line**: a bottom-anchored `ModalScreen` drawer where you type `sase` commands
(the `sase` prefix is implicit). Commands run as **ordinary durable procs** with `origin="ace"`, the
tag `command-line`, no operation and no service block. Output streams inline as Warp-style blocks with
status gutters. Hiding the panel is free: procs keep running, show in Admin Center → Procs, toast when
they finish, and come back after a TUI restart. Move the Command Palette to `;`, with one-key hops
between the two surfaces and a one-time tip.

**Win on completion** with what only the TUI has:

- selection-aware, in-memory entity candidates
- Rust fuzzy ranking with rich descriptions and a doc peek
- a live signature line with a `⚠ writes` chip
- advisory validation that never blocks Enter
- fish-style ghost text from history.

A frozen **`sase_core` `CommandLineGrammar`** resolver powers all of it. It reads an extended
`sase completion spec -d`, which is built in a subprocess and cached by runtime identity. Before this
can work, close the value-kind coverage gap, with a ratchet so it stays closed.

**Make it reliable** with:

- an exit-code watch path instead of `_submit_durable_proc`
- an offset-based `ProcLogCursor` with ref-counted tails
- a run-policy table (`proc` / `foreground` via `app.suspend()` / `deny`) and confirmation-aware
  blocks in place of silent flag injection
- a visible working-context chip with `cd`
- a `FORCE_COLOR` / `COLUMNS` / `PYTHONUNBUFFERED` output contract, which first requires fixing the
  `isatty`-only color resolution
- a dedicated retention bucket for command-line procs.

Ship it in phases behind the beta flag `ace_command_line`. Start with a read-only MVP, and add PNG
goldens for every state from the first panel phase. Flip `:`/`;` and delete the flag only in the
final phase.

---

## Appendix A: touchpoints for the `:`/`;` flip

Taken from cld's sweep and re-anchored where lines have drifted.

- **Config and keymaps:**
  - `src/sase/default_config.yml:804`
  - `keymaps/app_keymaps.py`, a new field (the YAML is the only source of defaults)
  - `keymaps/metadata.py` `_BINDING_META`
  - `commands/_app_metadata_display.py`: the new row, and remove the palette's `":"` alias
  - `_APP_COMMAND_META`, whose catalog guard raises on drift
  - `action_open_command_line`
  - `actions/artifacts.py` `NON_PRS_ARTIFACT_ACTIONS`
  - the `commands/_availability_artifacts.py` allowlist
- **Help, onboarding and palette text:**
  - `help_modal/{agents,patches,axe,patches_artifact}_bindings.py`
  - `widgets/tab_quickstart.py`, `widgets/agent_onboarding.py`
  - the palette hint's `key::` example
  - the `action_open_command_palette` docstring, which still says "bound to `:`"
- **Docs:**
  - `docs/ace.md`: the global key table, the Command Palette section, and the custom-mode example
    `prefix: ";"` at line 6014.
- **Tests:**
  - `test_keymaps_{defaults_panels,validation,app_bindings}.py`
  - `test_command_catalog{,_guards}.py`, `test_command_palette_{modal,wiring,e2e}.py`
  - `test_keymaps_display_help_key_display.py`
  - PNG goldens for `agents_onboarding`, `changespecs_onboarding`, `help_panel` and `agents_fleet`,
    regenerated with `just fix-tui-screenshots`.

## Appendix B: external precedents

- **Vim / Neovim.** `:` as the command line, the wildmenu, `:!` suspending to the shell, and
  two-stage Escape.
- **Helix.** A bottom command line with the completion menu above it and docs for the typed command.
- **k9s.** `:` to command a TUI, with ghost text.
- **fish.** `→`-accepted history autosuggestions.
- **Warp.** Command-plus-output blocks with status.
- **VS Code.** Prefix hops between quick-open surfaces.
- **Fig / Amazon Q.** Spec-driven completion with dynamic generators; `sase.completion`'s spec plus
  providers is the same idea, and it already exists.
