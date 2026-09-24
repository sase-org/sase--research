# In-TUI `sase` Command-Mode (`:`) + Palette on `;` Only — Research Report

Researcher: mus · 2026-09-24 · independent swarm report (`__mus`)

Request: rebind the command palette to `;` only, and give `:` to a new
"command-mode" panel that runs `sase` CLI commands from inside the TUI with
better-than-shell completion, inline output by default, execution as a durable
proc (visible on the Admin Center Procs tab), and leave-able while running.
Design goals: intuitive, reliable, beautiful.

## 1. What exists today (verified in-tree)

- **One binding, two keys.** `ace.keymaps.app.open_command_palette` is
  `"colon,semicolon"` ([default_config.yml](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/default_config.yml:799)).
  Both `:` and `;` open the same modal from any tab; this is documented in
  `docs/ace.md` ("Command Palette" section) and the binding help
  (`:` / `;` row). `action_open_command_palette` docstring still says
  "bound to `:`" ([actions/base.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/actions/base.py:656)).
- **Palette architecture (3 phases, all landed).** Catalog
  ([commands/catalog.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/commands/catalog.py)) builds
  `CommandSpec` entries from the `KeymapRegistry` (every `AppKeymaps` field +
  saved-query slots + mode subkeys + custom modes; a guard raises if
  `_APP_COMMAND_META` drifts from `AppKeymaps`) → availability predicates
  filter by tab/selection → `CommandPaletteModal` (filterable `OptionList`,
  `key:` search prefix, category badges)
  ([modals/command_palette_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/modals/command_palette_modal.py)) →
  `execute_command` dispatches back through existing app actions/mode handlers
  ([commands/execute.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/commands/execute.py)).
  Key point: **the palette only runs TUI-internal actions; it knows nothing
  about the `sase` CLI.** Command-mode is therefore a genuinely new execution
  path, not a palette extension.
- **Closest existing analog: bgcmd (`!!` / `,!`).** Project-select modal →
  workspace-input modal → `CommandHistoryModal` (history + free-typed
  *arbitrary shell*) → launched as a oneshot service proc via a durable CLI
  operation ([actions/axe_bgcmd.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/actions/axe_bgcmd.py)).
  Three-modal friction, shell-string (not argv-aware) input, no flag/value
  completion. Command-mode should obsolete this flow for `sase` commands
  without removing generic-shell bgcmd.
- **Proc infrastructure already does what the request wants.**
  `sase proc run -- CMD` records a proc, starts it under a supervisor, and
  returns; procs survive TUI restarts; session/project attribution controls
  where they appear ([proc run help](observed via CLI)). `sase proc show REF
  --follow` streams output; the Admin Center Procs tab already polls
  supervisor state on a daemon observer thread and renders live log tails
  ([tui/proc_observer.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/proc_observer.py),
  [modals/procs_pane_store.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/ace/tui/modals/procs_pane_store.py)).
  So "inline output + leave + find it in Procs" = **submit via the existing
  proc path, render via the existing observer/log-tail path.** No new
  process management should be built.
- **Completion infrastructure is the unfair advantage.** Two machine-readable
  surfaces already exist:
  1. `sase completion spec` — full argparse tree as JSON (subcommands,
     options, choices). Cache once per TUI session.
  2. `sase completion candidates KIND [PREFIX]` — live value completion
     (`project`, `bead`, `agent`, `proc`, `monitor`, `model`, `provider`,
     …) with a pre-argparse fast path and a hard constraint: the candidate
     modules must stay off `sase.ace` / `main.parser` / `rich` / `textual`
     imports so they stay cheap
     ([completion/candidates/catalog.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/completion/candidates/catalog.py)).
     Wire format is `value<TAB>description` lines
     ([candidates/protocol.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/completion/candidates/protocol.py)).
  - **History storage exists** (`sase_home()/command_history.json`,
    `CommandEntry{command, project, cl_name, timestamp, last_used}`,
    [history/command.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_39/src/sase/history/command.py))
    and `CommandHistoryModal` already pairs history list + details preview.
    Reuse the store (namespace `sase`-argv entries separately from shell
    strings) and the two-panel layout idiom.
- **Keymap mechanics.** `AppKeymaps` has no defaults — every field must come
  from `default_config.yml` (single source of truth; startup fails otherwise).
  Per repo convention, keymap changes also touch `default_config.yml`. A new
  `open_command_mode` action additionally needs a row in `_APP_COMMAND_META`
  (else the catalog guard raises), help-modal bindings, quickstart/onboarding
  hints, and docs.

## 2. Critique of the plan

**Verdict: good idea, worth building — with adjustments.** The core insight is
right: the TUI can complete `sase` invocations better than any shell because
it owns the completion spec, live value catalogs, and current project/session
context. And `:` is the right key (vim ex-command muscle memory). Three
concerns change the shape of the solution:

1. **Don't build a shell; build a `sase`-argv runner.** The request says
   "run `sase` commands", so enforce it: parse with `shlex` (no `shell=True`,
   no pipes/redirects), require the argv to resolve inside the `sase` tree.
   Rationale: (a) quoting/injection bugs vanish; (b) completion is tractable
   (finite grammar vs. arbitrary shell); (c) generic shell already exists via
   `!!` bgcmd — duplicating it splits history and confuses users about which
   runner to use. Adjustment: command-mode accepts `sase bead list …` (with
   the `sase` prefix optional and implied), and offers "run in shell bgcmd
   instead" as an escape hatch when input doesn't parse as `sase` argv.
2. **The dangerous-command problem is real and must be designed, not
   documented.** One typo away from `sase stitch`, `bead close`, `agent kill`.
   Shell users get a moment of reflection at Enter; a fast TUI panel gives
   less. Adjustment: submit path echoes the fully-resolved argv, and
   write/destructive verbs (stitch, revert, kill, close, … — a denylist in
   one place) require a second explicit confirm (type-to-confirm or `y`).
   Read-only commands run immediately. Consider making this configurable.
3. **Interactivity will bite.** Many `sase` commands open `$EDITOR`, prompt
   `y/n`, or wait on gates (`sudo`, `questions`, launch approval). A proc has
   no TTY. Adjustment: command-mode is explicitly non-interactive. Reject (with
   guidance, not silence) commands known to need a terminal; prefer `-j/--json`
   or `--yes` equivalents where the user typed them, but never silently inject
   flags — that changes semantics. Long waits should suggest `sase monitor`
   semantics, which already compose with procs.

Smaller critiques:

- **`;` vs `:` ergonomics.** On US layouts `:` is Shift+`;` — the palette
  (discovery, high-frequency for newcomers) keeps the unshifted key while the
  power-user feature takes the shifted one. That is the right assignment, and
  it matches vim. Note it in docs for non-US layouts; both remain rebindable
  via `ace.keymaps.app.*`.
- **Two fuzzy finders, one brain.** Users will confuse "palette commands"
  (TUI actions like `app.refresh`) with "command-mode commands" (`sase bead
  …`). Mitigate with unmistakable chrome: different title/icon (`✦` is taken
  by the palette — use something like `❯ sase`), a persistent `sase` prefix
  affordance in the input, and distinct accent color. Also consider the VS
  Code escape hatch: typing `>` in the palette jumps to command-mode and
  vice versa — cheap, familiar, kills the "which one was it" problem.
- **Scope creep risk: output rendering.** `sase` output may be rich tables,
  pagers, ANSI, or huge. Don't build a renderer: cap the inline tail (reuse
  the Procs tab's 200-line default), render plain/markdown-ish via existing
  widgets, and link "open full output in Procs" for the rest. Pager-invoking
  commands should get `--no-pager`-style env or be refused with a hint.

## 3. Recommended solution

**Split the keys as proposed (`;` palette, `:` command-mode), implemented as
two entry points sharing one modal shell and design language.**

### UX

- `:` opens a bottom-docked command bar (vim-style) that expands into a panel:
  input line with implicit `sase` prefix shown as a fixed prompt chip, a
  completion popup (subcommands → flags → values, with `description` text from
  the candidates wire format), and an output region below.
- `Tab` completes (common-prefix, then cycle); `↑/↓` walks history filtered by
  prefix; `Enter` runs read-only commands immediately, destructive verbs show
  an inline confirm row; `Esc` closes the panel but the proc keeps running —
  toast with proc id + "Procs tab" jump action (the `proc_indicator` widget
  already links there). Reopening `:` while a command runs shows its live tail
  (latest command-mode proc per session), not a blank prompt.
- Output region: live tail via the existing proc-observer log stream, exit-code
  chip on settlement (green/red), elapsed timer, "Open in Procs" link. Leave =
  detach, never kill (kill explicitly from Procs tab).
- History: extend `command_history.json` with argv entries tagged by kind
  (`sase` vs `shell`), project-scoped ranking as today.

### Engineering (reuse order)

1. **Submit:** build argv → `sase proc run` equivalent in-process (same
   supervisor path bgcmd uses), attributing current project + session so the
   row appears in the Procs tab. No new runner.
2. **Complete:** cache `completion spec` JSON once per TUI process; complete
   values out-of-process via `sase completion candidates KIND PREFIX`
   (subprocess, debounced) or in-process against `catalog_*` fetchers —
   respecting their import quarantine (never import them into the
   `textual`-loaded app process if that violates the fast-path constraint;
   subprocess keeps it safe). Needs one new table: option → value-kind
   mapping (check whether `spec` already carries `kind`; if not, add it at
   the argparse-source level so shell and TUI completion improve together).
3. **Render:** reuse `ObservedProc` snapshots + log-tail decoding from
   `proc_observer`; reuse `FilterInput`/`OptionList` idioms and `styles.tcss`
   accents from `CommandPaletteModal` for beauty-with-consistency.
4. **Keymap/config:** `open_command_palette: "semicolon"` +
   new `open_command_mode: "colon"` in `default_config.yml`; new `AppKeymaps`
   field; `_APP_COMMAND_META` row; help-modal/quickstart/onboarding/docs
   updates. Both keys stay user-rebindable.
5. **Safety:** argv-only parsing; destructive-verb confirm; non-interactive
   contract with explicit refusals; output cap with Procs-tab handoff.

### Phasing

1. Read-only MVP: run + complete + inline tail + detach (`bead list`,
   `agent list`, `proc list`, …). Proves the completion and observer-reuse
   story with zero destructive risk.
2. Destructive confirm + history + `>`/`:` cross-jump.
3. Polish: elapsed/exit chrome, perf (debounced candidates, cached spec),
   visual snapshot tests mirroring the palette's PNG suite.

### Alternatives considered

- **Keep both keys on the palette, add a `>` mode-switch inside it** (VS Code
  style). Cheapest, zero keymap churn — but buries the feature and concedes
  the vim `:` affordance. Do this *as well* (cross-jump), not *instead*.
- **Full shell panel.** Rejected: duplicates `!!` bgcmd, completion intractable.
- **Suspend-and-run-in-terminal.** Loses proc durability and leave-ability;
  the whole point is proc-backed execution.

## 4. Risks / open questions

- Option→value-kind mapping may not exist in `completion spec` yet — small
  upstream completion change required; confirm before estimating.
- In-process vs subprocess candidates: measure `sase completion candidates`
  latency under TUI load; subprocess is safe but needs debounce + cancel.
- TTY/editor commands need a curated refuse-list; enumerate top interactive
  commands (`stitch` flows, `run` prompts, anything honoring `$EDITOR`).
- proc attribution defaults (current session vs none) decide Procs-tab noise;
  default to current session so users can find their output.
- Visual tests: extend the existing palette PNG snapshot pattern to the new
  panel from day one — "beautiful" needs a regression gate.
