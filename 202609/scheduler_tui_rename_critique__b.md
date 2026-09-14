# Critique: AXE → Scheduler, Lumberjacks → Routines, Chops → Jobs, ACE → TUI

_Researcher B · 2026-09-14 · evidence from `sase` master @ `c402a04317`, linked `sase-core`,
`sase-github`, `sase-telegram`, `sase-nvim`, `chezmoi`, and live `~/.sase` state._

## 1. Verdict

**Yes, make the rename, but change one of the four names and limit how far down the
stack it goes.**

| Proposal                              | Verdict                  | Why, in one line                                                                                                     |
| ------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `sase ace` → `sase tui`, ACE → TUI    | **Endorse**              | "Agentic Change Explorer" is out of date. ChangeSpecs are now Patches and the TUI puts agents first.                 |
| AXE → "sase's scheduler"              | **Endorse, with caveats** | Accurate, and the docs already say "AXE schedules" and "the scheduler". Watch for two existing uses of "scheduler". |
| AXE tab → "Schedule"                  | **Acceptable**           | Slight preference for **Scheduler**. The tab controls the daemon and also lists non-scheduled bgcmds.                |
| Chops → **jobs**                      | **Endorse**              | Standard industry term, and `docs/axe.md` already calls chops "lifecycle jobs".                                      |
| Lumberjacks → **routines**            | **Recommend against**    | "Routine" means a single automation, so "a routine that contains jobs" reads backwards. Use **lane**.                |

The strongest argument for the whole change is **ACE vs AXE**. Two core nouns differ by one
letter, both are opaque acronyms, and they sit side by side: `sase ace --restart-axe`,
`alias ace='sase ace'` / `alias axe='sase axe'`, and the `stop_axe_and_quit` key in the ACE
keymap. The pun family (axe → lumberjack → chop) is charming. But once AXE is renamed the
metaphor has nothing to anchor it, so renaming all four together is the right call.

The biggest risk is a **mechanical, repo-wide find/replace**. Several names are durable
contracts: on-disk dirs, env vars, console-script names that appear inside user config, a
plugin SDK, and Rust config composition. Two internal packages would also become new
misnomers if renamed wholesale (see §4).

## 2. What these things actually are (so the names can be judged)

- **AXE**: "Background Automation Daemon" (`docs/axe.md`). An **orchestrator** process
  supervises N **lumberjack** processes. The TUI starts it automatically
  (`sase ace --no-axe` / `--restart-axe`). Operators can also run
  `sase axe start|stop|status|restart|ensure|maintenance|bgcmd|chop|lumberjack`. Note that
  the `src/sase/axe/` package is more than the scheduler: **56 of its 155 modules are
  `run_agent_*` agent-runner code**.
- **Lumberjack**: a long-lived, independently supervised process with its own `interval`,
  `chop_timeout`, description, state dir (`~/.sase/axe/lumberjacks/<name>/`), log
  (`~/.sase/axe/logs/lumberjack-<name>.log`), crash-restart backoff, and cycle/error
  metrics. It runs its chops concurrently. The default config's own descriptions already
  call them **lanes**: "Fast lane that advances hook…", "belong in the other lanes",
  "their dedicated lanes". So does the user config in chezmoi (`sase_athena.yml`: "audit
  lane", "lane state").
- **Chop**: one short, script-only unit of work. Its triggers are `fs` (with `max_quiet`),
  `always`, or `run_every`, plus guards, timeouts, dedupe, and `for_each` targets. A chop
  can return launch proposals that the runner performs. There is a public authoring SDK
  (`sase.chops`: `ChopResultBuilder`, `ChopReport`, …), 29 built-in `sase_chop_*` console
  scripts, and 2 plugin scripts in sase-telegram.
- **ACE**: "Agentic Change Explorer" (`docs/ace.md`). Its top tabs are **Agents**,
  **Artifacts**, and **AXE**. The `src/sase/ace/` package is **not TUI-only**: it also
  holds `changespec/`, `query/`, `patch/`, `hooks/`, `mentors/`, `scheduler/`,
  `workflows/`, `revert_agent*`, and dismissed-agent stores.

## 3. Critique of each proposed name

### 3.1 AXE → "sase's scheduler"

**For:**

- The README already says "ACE supervises, **AXE schedules**" and "scheduled and background
  agent work".
- `docs/mentors.md` already calls AXE "the scheduler".
- `src/sase/ace/scheduler/__init__.py` describes itself as utilities "used by the sase axe
  scheduler".
- A newcomer can guess what it does.

**Against / risks:**

1. **An internal name already collides.** `src/sase/ace/scheduler/` (hook, mentor, and
   orphan-cleanup helpers called from chops) would sit next to a top-level "scheduler". It
   should be renamed, for example to `sase.patch_lifecycle`.
2. **It can be confused with agent-launch admission.** Runner slots, weighted capacity, and
   wait slots are also "scheduling" in the everyday sense.
   `docs/troubleshooting/runner-slots.md` says "mixed old/new **scheduler** fleet" about
   runner capacity, and explicitly says the slot gate "does not depend on the axe daemon".
   Users will ask whether "the scheduler" decides when their queued agent starts. Fix this
   with a glossary strand that says outright: the scheduler runs jobs; it does not admit
   agent launches. Also reword that runner-slots doc.
3. **The name is harder to grep.** "AXE" is a unique token; "scheduler" is not (pytest-xdist
   "worksteal scheduler" in `docs/development.md`, the Rust/async ecosystem). Use one exact
   token everywhere: CLI `sase scheduler`, config `scheduler:`, and log names.
4. **Don't write "sase's scheduler" literally.** Possessives read badly in help text and
   tables ("sase's TUI's AXE tab…"). Use "the SASE scheduler" on first mention and "the
   scheduler" after. Treat "the SASE TUI" / "the TUI" the same way.
5. **CLI noun:** use `sase scheduler …`, not `sase schedule …`. It matches the other nouns
   (`sase proc`, `sase agent`, `sase bead`). `schedule` reads as a verb and is worth
   keeping free for a future "launch this agent at 3pm" command.

**Alternatives considered:**

- "automation": broader, and covers fs-triggered jobs, but vague.
- "daemon": names the process, not its purpose.
- "cron": wrong, because most default hooks-lane jobs are fs-triggered.

"Scheduler" is the best balance.

### 3.2 AXE tab → "Schedule"

It works, with three caveats:

- **The tab is also the daemon's control surface.** It has start/stop, status, and a
  refresh countdown.
- **It lists background-command rows (`!!` bgcmds).** `docs/ace.md` itself says these rows
  are styled "so they cannot be mistaken for scheduled AXE work".
- **Much of the default hooks lane isn't time-scheduled.** Its jobs are fs-triggered.

"Schedule" sounds like a timetable view. **"Scheduler"** names the component being
monitored and matches the CLI. Either is fine. If you pick "Schedule", consider moving
bgcmds to the Procs panel, since they are procs in spirit.

Avoid naming the tab "Jobs": the command palette already maps the alias `jobs` to the
Procs panel (`src/sase/ace/tui/commands/catalog.py:233`).

### 3.3 Lumberjacks → "routines" (recommend against)

- **The meaning is backwards.** In both everyday and industry usage a *routine* is a single
  procedure or automation: Alexa and Google Home routines, subroutines, and **Claude Code
  "routines" = one scheduled cloud agent**. A lumberjack is the opposite: a supervised
  *process* with a PID, log, restart backoff, and state, running *many* jobs on a shared
  interval. Readers will assume routine ≈ job, and "a routine contains jobs" will confuse
  them.
- **It clashes in your own toolchain.** You drive sase through Claude Code, whose built-in
  `schedule` skill manages "routines". "Create a routine that…" would be ambiguous to your
  agents.
- **Grep noise:** the substring "routine" also matches "coroutine" in the codebase.

**Better choice: lane.**

- It is already the vocabulary used in the defaults and your chezmoi configs.
- It says what the concept is for: grouping work by latency class so groups run side by
  side ("hooks lane every 5s", "checks lane every 5 min").
- It is short and works in the CLI: `sase scheduler lane list`.

The collision is that `lane` already means something else in the TUI metadata panel
(`SASE CONTEXT` → `PLAN`/`BEAD` "lanes") and in test/CI vocabulary. That is a different
domain, so qualify it as "scheduler lane" in the glossary.

**Runners-up:**

- **loop**: fits the fixed-interval tick, but clashes with Claude Code `/loop`.
- **worker**: the Celery/Sidekiq meaning is close, but sase already has "epic phase workers"
  and "task workers".
- **cadence**: accurate but abstract.

### 3.4 Chops → "jobs" (endorse)

- It is the term people already know from cron jobs, CI jobs, and Sidekiq jobs.
- `docs/axe.md` already says lumberjacks run "lifecycle **jobs**" "on its own schedule".
- "job" is not a first-class sase noun today, which fits "scheduler runs jobs in lanes".
- Do **not** use "task" (task beads) or "check" (many chops are cleanups, flushes, and
  mirrors).

Existing uses of "job" to clean up or tolerate:

- the palette alias `jobs` → Procs panel;
- `sase.axe.hook_jobs.HookJobRunner` (imported by `sase.chops.builtin`), which would become
  "hook job" inside a "job";
- chat install/update "jobs" (`src/sase/integrations/chat_install.py`, a `jobs/` state dir);
- `llm_provider/usage/refresh_runner.py` jobs;
- the structured-log field `job=` in `register_flush_on_exit`;
- GitHub Actions jobs watched by the `ci_watch` / `github_actions` lanes ("a job that
  watches CI jobs");
- the shell `jobs` builtin.

All are manageable; none is a blocker.

### 3.5 `sase ace` → `sase tui`, ACE → "sase's TUI" (endorse, scoped)

**For:**

- The acronym is out of date: ChangeSpecs → Patches (`50f8961ac7`), and the TUI now opens
  on Agents.
- `sase tui` explains itself.
- There is no existing `sase tui` command.
- `SASE_TUI_TRACE`, `src/sase/ace/tui/`, and many commits (`feat(tui): …`) already use the
  word.

**Against / scope limits:**

1. **"TUI" names a form factor, not a product.** That is fine as long as the name only
   refers to the terminal app. Telegram, the mobile helper, and a future web UI stay
   separate frontends.
2. **Don't rename the `sase.ace` package to `sase.tui` wholesale.** You'd get
   `sase/tui/tui/`, and it would misname non-TUI domain modules (changespec, query, patch,
   hooks, mentors, revert_agent). Keep the internal package name, or move `sase/ace/tui` →
   `sase/tui` and relocate the domain modules as a separate refactor. Shared behavior
   belongs in `sase-core` anyway.
3. **The brand gets weaker.** The README hero line and the `sase.sh/ace/` and
   `sase.sh/axe/` URLs are published. Keep redirects.

## 4. Compatibility and cost: how to do it without breakage

Past renames set the pattern:

- **task → proc** (`a0e9ae4ed3`) kept `sase task` as a legacy alias plus facade modules at
  the old import paths.
- **ChangeSpec → Patch** kept serde aliases (`#[serde(rename = "distinct_changespecs", alias = "distinct_patches")]`).

The `sase_flags` memory also makes a **`sunset` feature flag mandatory** for any
deprecated/back-compat branch, created with `sase flag new`.

Suggested phases:

1. **Vocabulary (cheap, high value).**
   - Tab label, help modal, command-palette categories, onboarding text.
   - `docs/`, README, glossary (new `Scheduler`/`Lane`/`Job` strands; retire `Chop`/
     `Lumberjack`; update the `Proc` strand's "ACE's Procs tab").
   - Memory notes and xprompt skills. Regenerate the skills, since they deploy to chezmoi
     for claude/codex/muse.
   - New CLI `sase tui` / `sase scheduler` with hidden `ace`/`axe` aliases (sunset flag).
     Keep subcommands sorted per `cli_rules`.
2. **Config keys (Rust first).** Config composition and validation live in `sase-core`
   (`compose_axe_config`, `validate_axe_config`, `classify_axe_status`,
   `healthy_lumberjack`, `parse_chop_result`). Add `tui:`, `scheduler:`, `lanes:`, `jobs:`,
   `job_timeout`, `job_script_dirs`, and `lane_log_*` there, accept legacy keys with a
   warning, then migrate the chezmoi configs.
3. **Script and plugin API (dual-publish).**
   - Configs name scripts literally (`script: sase_chop_hook_checks`), so keep the
     `sase_chop_*` entry points as aliases next to `sase_job_*`.
   - Export both `SASE_JOB_*` and `SASE_CHOP_*` env vars.
   - Re-export `sase.chops` from `sase.jobs`.
   - Coordinate with sase-telegram (`sase_chop_tg_inbound`/`outbound`).
4. **On-disk state: leave or migrate once.**
   - `projects/*/artifacts/ace-run/` is referenced in ~990 lines across ~365 files and in
     fs-trigger globs, and it exists in every project. Treat it as an internal name; don't
     rename it.
   - `~/.sase/axe/` (lumberjacks/, logs/, orchestrator.pid/lock, lifecycle.jsonl) and
     `~/.sase/ace_*` state files: migrate once at startup, or leave them.
5. **Internal identifiers (optional, high churn).** There are roughly 918 distinct Python
   identifiers containing "axe", 871 containing "chop", and 294 containing "lumberjack",
   plus about 175 chop and 225 axe file paths. The 667 PNG visual snapshots under
   `tests/ace/tui/visual/snapshots/png` will need regeneration once the tab labels change.
   Don't rewrite `CHANGELOG.md` or historical blog posts.

## 5. Concise inventory of references to replace

Counts are `git grep -w` lines/files on master and are upper bounds: "ace" is inflated by
`sase.ace.*` import paths.

**Raw totals (sase repo, 10,305 tracked files)**

| Term       | Case  | Lines  | Files |
| ---------- | ----- | ------ | ----- |
| axe        | lower | 4,798  | 893   |
| AXE        | upper | 658    | 214   |
| Axe        | title | 279    | 111   |
| lumberjack | any   | ~1,110 | ~225  |
| chop       | any   | ~2,475 | ~440  |
| ace        | lower | 16,828 | 3,570 |
| ACE        | upper | 2,490  | 755   |

Other literal strings:

| String                | Lines | Files |
| --------------------- | ----- | ----- |
| `sase ace`            | 167   | 89    |
| `sase axe`            | 273   | 66    |
| `sase axe chop`       | 74    | 23    |
| `sase axe lumberjack` | 35    | 12    |

**CLI**

- `sase ace` and its flags `--no-axe`, `--restart-axe`: `src/sase/main/parser_ace.py`,
  `parser_registry.py`, `parser_root_help.py`, `entry.py`, `ace_handler.py`,
  `ace_tmux.py`.
- `sase axe {bgcmd, chop {doctor,list,run}, ensure, lumberjack {list,run,…}, maintenance, restart, start, status, stop}`:
  the same `parser_ace.py`, plus `axe_handler.py` and `src/sase/axe/cli.py`.
- chezmoi: `home/dot_config/aliases.sh` (`ace`, `axe`, `acei`, `aceii`) and
  `home/dot_config/fish/completions/sase.fish`.

**Config (`src/sase/default_config.yml` + user configs)**

- Top-level `ace:` (~89 distinct `ace.*` keys, including `ace.keymaps`,
  `ace.axe_description_expanded`, and tribe `ace.tribes.chop` with the "gold ACE fallback"
  comment).
- Top-level `axe:`: `lumberjacks:`, `chops:`, `chop_timeout`, `chop_script_dirs`,
  `lumberjack_log_max_bytes`, `lumberjack_log_temp_max_age_seconds`,
  `lumberjack_restart_backoff_max_seconds`, `verbose_lumberjack_diagnostics`.
- Keymap names: `add_axe_item`, `toggle_axe_description`, `stop_axe_and_quit`,
  `toggle_axe`, and a nested `axe:` keymap scope.
- chezmoi: `home/dot_config/sase/sase.yml` (xprompt snippets `ace`, `axe`, `gsn`, `gsna`,
  `gta`, `gtu`; telegram lane config), `sase_athena.yml`, `sase_apollo.yml`,
  `sase_kellys_mbp.yml`, `actstat-ci-watch.yml`.

**Script / plugin / env API**

- 29 `sase_chop_*` console scripts (`pyproject.toml`, 231 references) and the
  `SASE_CHOP_SCRIPT_PREFIX` discovery prefix.
- sase-telegram: `sase_chop_tg_inbound`, `sase_chop_tg_outbound`; its package description
  "Telegram integration chop".
- Public SDK `src/sase/chops/` (`ChopArguments`, `ChopResultBuilder`, `ChopReport`, …).
- Env vars:
  - `SASE_CHOP_*`: `RESULT_FILE`, `NAME`, `RUN_ID`, `LUMBERJACK`, `TARGET_*`, `SOURCE`,
    `DRY_RUN`, `VERBOSE`, `ID`, `ADMISSION_*`, `PROPOSAL_INDEX`, `PROMPT_HASH`,
    `SCAN_FULL_WALK`; plus `SASE_CHOPPER`.
  - `SASE_AXE_*`: `START_SOURCE`, `LIFECYCLE_LOCK_FD`, `WEDGED_LOCK_GRACE_SECONDS`,
    `ALLOW_LIFECYCLE_IN_TESTS`, `MODE`, `CANONICALIZED`, `OTHER`.
  - `SASE_ACE_*`: `RELEASE_VERSION_TITLE`, `DEBUG_LEAKS`, `PAGE_GROUP_ISOLATION`.
- Durable op name `axe.bgcmd` (`src/sase/ops/names.py`); agent tribe `chop`.

**On-disk state**

- `~/.sase/axe/`: `lumberjacks/<name>/`, `logs/axe.log`, `logs/lumberjack-<name>.log`,
  `orchestrator.{pid,lock}`, `lifecycle.jsonl`, `desired_state.json`, `ensure.json`.
- `~/.sase/ace_admin_center_last_tab.txt`, `ace_agents_fold_state.json`,
  `ace_agents_last_query.json`.
- `~/.sase/projects/*/artifacts/ace-run/`.

**Code packages and tests**

- `src/sase/axe/` (155 modules; 41 `chop*`, 56 `run_agent_*`), `src/sase/ace/` (TUI plus
  domain modules), `src/sase/ace/scheduler/`, `src/sase/chops/`.
- `tests/ace/…`, `tests/test_axe_*`, 667 visual-snapshot PNGs.
- Agent instruction shims in `src/sase/ace/` (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `QWEN.md`, `OPENCODE.md`).

**TUI strings**

- `widgets/tab_bar.py`, `widgets/agent_onboarding.py` (`"AXE"`, "Monitor the Axe daemon
  and automation.").
- `modals/command_palette_modal.py` and `modals/jump_all_modal.py` (`"axe": ("AXE", "#FFD700")`).
- `modals/help_modal/binding_common.py`, `actions/refresh_panel.py` (`_TAB_LABELS`),
  `commands/types.py` and `commands/_app_metadata_actions.py` ("Axe" category), and
  `actions/agents/_folding_axe.py` ("lumberjack and chop folds").

**Rust `sase-core`**

- 230 axe / 122 lumberjack / 150 chop / 284 ace lines.
- Modules `axe_chop/`, `axe_status/`, `axe_overrun/`.
- Functions `compose_axe_config`, `validate_axe_config`, `classify_axe_status`,
  `classify_chop_overrun`, `parse_chop_result`, `evaluate_chop_decision`,
  `expand_chop_targets`, `healthy_lumberjack`, `lumberjack_path`, and `chop_error_to_pyerr`.
- Wire/config fields `lumberjacks` and `chops`.

**Linked plugins**

| Plugin        | References                                    |
| ------------- | --------------------------------------------- |
| sase-telegram | axe 15, lumberjack 6, chop 44, ace 27 lines   |
| sase-github   | ace 30 lines                                  |
| sase-nvim     | ace 20 lines                                  |

**Docs and agent context**

- Docs files: `docs/ace.md`, `docs/axe.md`, `docs/cli.md`, `docs/configuration.md`,
  `docs/plugins.md`, `docs/mentors.md`, `docs/troubleshooting/runner-slots.md`, README,
  `INSTALL.md`, `demos/README.md`.
- Blog posts, including `axe-background-daemon.md`.
- Image prompts/critiques (`sase_tui_tabs_infographic.*`) and media named `sase_ace_*`.
- Docs totals: ~600 axe, ~1,200 ace, 182 lumberjack, and 405 chop lines.
- `sase/memory/` notes (ace 23, axe 6, chop 4, lumberjack 3 lines) and glossary strands
  `Chop`, `Lumberjack`, `Proc`.
- xprompt skill sources (axe 6, ace 6 lines, e.g. `sase_notify` "axe notifications/errors")
  and their generated copies in chezmoi.

## 6. Recommended names

| Today                           | Your proposal        | **Recommended**                                                                                    |
| ------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------- |
| `sase ace`                      | `sase tui`           | **`sase tui`** (keep `sase ace` as a hidden alias under a sunset flag)                              |
| ACE (prose)                     | "sase's TUI"         | **"the SASE TUI"**, then **"the TUI"**                                                              |
| AXE (prose)                     | "sase's scheduler"   | **"the SASE scheduler"**, then **"the scheduler"**                                                  |
| `sase axe …`                    | —                    | **`sase scheduler …`** (`start`/`stop`/`status`/`restart`/`ensure`/`maintenance`); not `sase schedule` |
| AXE tab                         | "Schedule"           | **"Scheduler"** (acceptable alternative: "Schedule")                                                |
| lumberjack                      | routine              | **lane** (runner-up: loop): `sase scheduler lane list\|run`, config `scheduler.lanes`, "hooks lane" |
| chop                            | job                  | **job**: `sase scheduler job doctor\|list\|run`, config `jobs:` / `job_timeout` / `job_script_dirs` |
| `sase_chop_*` / `SASE_CHOP_*`   | —                    | **`sase_job_*` / `SASE_JOB_*`** (dual-publish old names during the sunset)                          |
| `sase.chops` SDK                | —                    | **`sase.jobs`** (with a `sase.chops` re-export)                                                     |
| `ace:` / `axe:` config roots    | —                    | **`tui:`** / **`scheduler:`** (legacy keys accepted in `sase-core`)                                 |
| orchestrator                    | —                    | keep **orchestrator** (the scheduler's supervisor process)                                          |
| `sase.ace.scheduler` package    | —                    | rename to **`sase.patch_lifecycle`** to free "scheduler"                                            |
| `chop` agent tribe              | —                    | **`job`** (or **`scheduled`**)                                                                      |
| bgcmd rows on AXE tab           | —                    | move to the **Procs** panel, or label the section **Commands**                                     |
| `ace-run` artifact dir, `~/.sase/axe/` | —             | **leave as internal names** (or a one-shot migration); never user-facing                            |
