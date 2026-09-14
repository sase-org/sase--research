# Renaming AXE/ACE/lumberjacks/chops: consolidated critique

_Lead researcher consolidation of [`scheduler_tui_naming__a.md`](scheduler_tui_naming__a.md)
and [`scheduler_tui_naming__b.md`](scheduler_tui_naming__b.md), plus independent
verification against `sase` master @ `c402a04317`. 2026-09-14._

## 1. Verdict

**Make the rename — the motivation is sound — but change one of the four names, adjust
the phrasing of two others, and stage the rollout instead of doing a global
find/replace.** Both researchers independently reached the same overall shape, and my
verification confirms their load-bearing evidence.

| Proposal | Verdict | One-line reason |
| --- | --- | --- |
| `sase ace` → `sase tui`; ACE → "sase's TUI" | **Endorse** (say "the SASE TUI") | "Agentic Change Explorer" is stale — ChangeSpecs became Patches and the TUI opens on Agents; `sase tui` explains itself. |
| AXE → "sase's scheduler" | **Endorse** (say "the SASE scheduler") | Docs already say "AXE schedules" / "the scheduler"; a newcomer can guess what it does. |
| AXE tab → "Schedule" | **Prefer "Scheduler"** | The tab is a live operations console (daemon control, lanes, jobs, bgcmds), not a timetable view. |
| lumberjacks → routines | **Reject — use "lane"** | "Routine" means a single automation, so "a routine contains jobs" reads backwards; "lane" is already the codebase's own vocabulary. |
| chops → jobs | **Endorse** (plus "job run" for one execution) | `docs/axe.md` already explains chops as jobs; it is the standard industry term. |

The strongest argument for the whole change is the **ACE/AXE pair itself**: two core
nouns differing by one letter, both opaque acronyms, sitting side by side in real usage
(`sase ace --restart-axe`, the `stop_axe_and_quit` keymap, `alias ace=`/`alias axe=` in
the dotfiles). Once AXE is renamed, the axe → lumberjack → chop metaphor loses its
anchor, so renaming the family together is right.

The biggest risk is treating this as one mechanical rename. Several of these names are
**durable contracts** — config roots composed exactly by the Rust core, a
schema-versioned status wire, `sase_chop_*` console-script names quoted inside user
configs, `SASE_CHOP_*`/`SASE_AXE_*` env vars, on-disk state under `~/.sase/axe/`, and
`chop:<lumberjack>/<chop>` artifact identity — while others are just prose. The plan
must classify each reference before touching it (§5).

## 2. What the names describe today (verified)

- **ACE** — "Agentic Change Explorer" (`docs/ace.md:5`), the main TUI with tabs
  **Agents / Artifacts / AXE**. The `src/sase/ace/` package is *not* TUI-only: it also
  holds changespec/query/patch/hooks/mentors/workflows domain code and a
  `sase.ace.scheduler` sub-package of Patch-lifecycle utilities whose own docstring says
  it is "used by the sase axe scheduler".
- **AXE** — the "Background Automation Daemon" (`docs/axe.md`): an orchestrator
  supervising N lumberjack processes. `src/sase/axe/` is likewise more than the
  scheduler — B counts 56 of its 155 modules as `run_agent_*` agent-runner code.
- **Lumberjack** — one long-lived, independently supervised loop with its own interval,
  timeout, state dir, log, restart backoff, and metrics, running its chops
  concurrently. It is both a cadence group and a failure boundary — not itself the work.
- **Chop** — one configured script-only work definition with `fs`/`always`/`run_every`
  triggers, guards, timeouts, dedupe, and `for_each` fan-out, which may return launch
  proposals executed by the runner. There is a public authoring SDK (`sase.chops`),
  29 built-in `sase_chop_*` console scripts, and two more in sase-telegram — chop is an
  extension protocol, not just a class name.

Key verified facts the recommendations rest on:

- `src/sase/default_config.yml` already calls lumberjacks lanes: "Fast lane that
  advances hook, mentor, and workflow lifecycle state" (line 916), "belong in the other
  lanes" (920), "their dedicated lanes" (1052). Bryan's chezmoi configs do the same
  ("audit lane", "lane state").
- `docs/axe.md` already explains chops in job vocabulary: "periodically runs lifecycle
  jobs" (line 6), a lumberjack "runs a subset of jobs on its own schedule" (41), a chop
  is "a single script-only job unit" (45).
- The tab label is presentation-only: `_TAB_DISPLAY_NAMES` in
  `src/sase/ace/tui/widgets/tab_bar.py:19-23` maps internal ID `"axe"` → `"AXE"`, so a
  label-only change needs no ID, CSS, or persistence migration.
- The command palette already aliases `jobs` to "Open procs panel"
  (`src/sase/ace/tui/commands/catalog.py:233`) — a small collision to clean up.
- No `sase tui` command exists today; the name is free.
- Claude Code's own `schedule` skill (in Bryan's active toolchain) manages "scheduled
  cloud agents (**routines**)" — the routines collision is live, not hypothetical.

## 3. Critique of each rename

### 3.1 `sase ace` → `sase tui` — make it, scoped

The command has outgrown its expansion, `sase tui` is self-describing, and the word is
already in use internally (`SASE_TUI_TRACE`, `src/sase/ace/tui/`, `feat(tui):` commit
scopes). Three scope limits:

1. **Prose form**: use "the SASE TUI" on first mention, then "the TUI" — not the
   possessive "sase's TUI", which turns awkward in compounds ("sase's TUI's Scheduler
   tab"). In broad docs, first reference "SASE terminal UI (TUI)".
2. **Do not rename the `sase.ace` Python package wholesale.** You would get
   `sase/tui/tui/` and mislabel the non-TUI domain modules. Keep the package name for
   now, or split by responsibility first (presentation → a TUI namespace; Patch/query/
   hook logic → neutral homes, with shared behavior migrating to `sase-core` per the
   backend-boundary rule). "TUI" names a form factor, which is fine precisely because
   Telegram and any future web UI are separate frontends.
3. **Keep `sase ace` as a hidden/deprecated alias** under a sunset feature flag (the
   `sase_flags` memory makes the flag mandatory). It is embedded in docs, shell aliases,
   fish completions, demo tapes, and the published `sase.sh/ace/` URL (keep redirects).

### 3.2 AXE → the SASE scheduler — make the public change, not a blind internal rename

Accurate and already half-true in the docs (README: "ACE supervises, AXE schedules";
`docs/mentors.md` calls AXE "the scheduler"). Caveats, all fixable:

- **Phrasing**: "the SASE scheduler", then "the scheduler" — never the literal
  possessive. CLI noun: **`sase scheduler …`**, not `sase schedule …` (matches
  `sase proc`/`sase agent`/`sase bead`; keeps `schedule` free as a future verb).
- **Internal collision**: `sase.ace.scheduler` (Patch-lifecycle helpers) would sit
  under a system newly named "scheduler". Rename it (e.g. `sase.patch_lifecycle`).
- **Admission-scheduling confusion**: runner slots and weighted launch capacity are
  also "scheduling" colloquially, and `docs/troubleshooting/runner-slots.md` says
  "mixed old/new scheduler fleet" about runner capacity while noting the slot gate
  "does not depend on the axe daemon". Add a glossary line — *the scheduler runs jobs;
  it does not admit agent launches* — and reword that doc.
- **Semantics**: "scheduler" is slightly narrower than the implementation (fs triggers,
  guards, manual runs, fan-out — most default hooks-lane jobs are fs-triggered, not
  timed). Not disqualifying — modern schedulers mix time/event/manual triggers — but
  introduce it as "the background automation scheduler", not as cron.
- **Grepability regresses**: AXE is a unique token; "scheduler" is not. Mitigate by
  using one exact token everywhere (CLI noun, `scheduler:` config root, log names).
- If `sase axe`, `--no-axe`, `SASE_AXE_*`, and an AXE tab stay visible, prose-only
  replacement leaves two names for one system — the public surfaces need `scheduler`
  spellings with Axe forms as compatibility aliases (§6).

Alternatives considered and rejected: "automation" (vaguer), "daemon" (names the
process, not the purpose), "cron" (wrong — most default jobs are fs-triggered).

### 3.3 The tab: prefer **Scheduler** over "Schedule" (or "Automation")

This was the one real disagreement between the reports; both agree "Schedule" is the
weakest of the three because it names a timetable while the tab is an operations
console: its sidebar holds the daemon parent row, lumberjack rows, *and* background-
command (`!!` bgcmd) rows that `docs/ace.md` explicitly styles "so they cannot be
mistaken for scheduled AXE work"; its controls start/stop the daemon and rerun work.

- **A prefers "Automation"** — it honestly covers the non-scheduler bgcmd rows.
- **B prefers "Scheduler"** — it names the component being monitored and matches the
  CLI noun.

**Resolution: "Scheduler."** The deciding criterion is A's own "one noun per level"
test: introducing *Automation* as a fourth public word (tab) alongside *scheduler*
(subsystem/CLI/config) re-creates the two-names-for-one-thing problem the rename is
meant to fix. B's mitigation resolves A's objection: move bgcmds to the Procs panel
(they are procs in spirit) or label their sidebar section "Commands". Fall back to
"Automation" only if the tab permanently keeps non-scheduler surfaces. Do not name the
tab "Jobs" (palette alias collision, §2).

First step is label-only and low-risk: change `_TAB_DISPLAY_NAMES` while keeping
internal tab ID `axe`, saved `--tab axe` startup values, CSS IDs, and keymap groups; a
later release can accept `--tab scheduler` and canonicalize it.

### 3.4 lumberjacks → routines — reject; use **lane**

Both researchers independently rejected "routine", for the same reason:

- **The meaning is backwards.** In everyday and industry usage a routine is a single
  automation (Alexa/Google Home routines, subroutines — and Claude Code's `schedule`
  skill, in Bryan's own toolchain, calls one scheduled cloud agent a "routine").
  Readers will assume routine ≈ job; "a routine contains jobs" will confuse them, and
  "create a routine that…" becomes ambiguous to Bryan's agents.
- It hides what a lumberjack actually is: a supervised process and failure/cadence
  boundary that groups many jobs.
- Grep noise: "routine" substring-matches "coroutine" across the codebase.

**"Lane" is the best replacement** — and it is already the project's de facto
vocabulary (§2): the defaults and Bryan's own configs describe lumberjacks as lanes. It
says what the concept is for (grouping jobs by latency class so groups run side by
side), reads well everywhere ("hooks lane", "lane status",
`sase scheduler lane list|run`), and stays short. Known collisions are in different
domains (TUI metadata panel PLAN/BEAD "lanes"; CI-lane vocabulary): qualify as
"scheduler lane" in the glossary. If maximal literalness ever matters more, "schedule
group" (`groups:`) is the fallback. Runners-up rejected: **loop** (clashes with Claude
Code `/loop`), **worker** (SASE already uses it for agents/phase workers), **cadence**
(abstract).

### 3.5 chops → jobs — make it, with "job run" for one execution

The strongest proposed rename. `docs/axe.md` already teaches chops in job vocabulary
(§2), and the surrounding ecosystem agrees on the pattern (Kubernetes CronJob → Jobs;
GitHub Actions workflows contain jobs; Airflow schedules DAGs of tasks): "a lane owns
jobs; each job produces job runs" is instantly learnable. Fix the definition precisely
rather than inventing another noun:

- **job** — a configured scheduler work definition;
- **job run** — one execution of it;
- **job script** — its executable;
- **proposed launch** — an agent launch a job result requests.

Do **not** use "task" (task beads exist; big schedulers use task for a finer unit) or
"check" (many chops are cleanups/flushes/mirrors). Existing "job" uses are manageable,
none blocking: the palette `jobs` alias → Procs panel (repoint or drop),
`sase.axe.hook_jobs.HookJobRunner` (becomes "hook job" inside a "job" — rename),
chat-install jobs, the `job=` structured-log field, GitHub Actions jobs watched by the
`ci_watch` lane, and the shell `jobs` builtin.

## 4. Scale

Token scans at `c402a04317` (upper bounds — lines matched, not required replacements;
`ace` is inflated by `sase.ace.*` import paths and `tests/ace/**`):

| Token | sase repo lines / files | Named paths | sase-core lines | Other notable |
| --- | ---: | ---: | ---: | --- |
| ace/ACE | ~19,300 / ~3,850 | ~4,020 | 284 | sase-github 30, sase-nvim 20, chezmoi 133 |
| axe/AXE | ~5,700 / ~970 | 435 | 230 | chezmoi 261, sase-telegram 15 |
| lumberjack(s) | ~1,100–1,400 / ~220 | 20 | 255 | chezmoi 55 |
| chop(s) | ~2,500–3,100 / ~440 | 173 | 224 | sase-telegram 48, chezmoi 77 |

(The two reports' counts differ by methodology — A case-insensitive scan, B `git grep
-w` per case — but agree on magnitude.) Also: ~918 distinct Python identifiers contain
"axe", ~871 "chop", ~294 "lumberjack"; 667 visual-snapshot PNGs under
`tests/ace/tui/visual/` regenerate once labels change; `ace-run/` appears in ~990 lines
across ~365 files and exists in every project's artifacts.

## 5. Concise replacement inventory

Categories a coherent rename must classify (representative roots; generate an exact
machine inventory at the chosen baseline):

1. **TUI copy** — `_TAB_DISPLAY_NAMES`/`_TAB_COLORS` in `tab_bar.py`; onboarding, help
   modal, command-palette categories and `jump_all` colors (`"axe": ("AXE", "#FFD700")`),
   refresh-panel labels, `agents/_folding_axe.py` copy; visual goldens.
2. **CLI grammar** — `sase ace` (+ `--no-axe`, `--restart-axe`) in
   `src/sase/main/parser_ace.py`, `parser_registry.py`, `parser_root_help.py`,
   `entry.py`, `ace_handler.py`, `ace_tmux.py`; `sase axe
   {start,stop,status,restart,ensure,maintenance,bgcmd,chop,lumberjack}` +
   `axe_handler.py`, `src/sase/axe/cli.py`; `--lumberjack`, `--chop-verbose`; help text
   and generated shell completions.
3. **Config** — top-level `ace:` (~89 keys incl. `ace.keymaps`,
   `ace.axe_description_expanded`, tribe `ace.tribes.chop`) and `axe:`
   (`lumberjacks:`, `chops:`, `chop_timeout`, `chop_script_dirs`, `lumberjack_log_*`,
   `lumberjack_restart_backoff_max_seconds`, `verbose_lumberjack_diagnostics`); keymap
   action names (`add_axe_item`, `toggle_axe_description`, `stop_axe_and_quit`,
   `toggle_axe`, nested `axe:` scope — remember `default_config.yml` per the gotchas
   memory); chezmoi user configs and aliases.
4. **Script/plugin/env API (contract)** — 29 `sase_chop_*` console scripts +
   `SASE_CHOP_SCRIPT_PREFIX`; the public `sase.chops` SDK (`ChopResultBuilder`,
   `ChopReport`, …); sase-telegram's `sase_chop_tg_inbound`/`outbound`; env families
   `SASE_CHOP_*` (~16 vars), `SASE_AXE_*` (~7), `SASE_ACE_*` (~3), `SASE_CHOPPER`.
5. **Python/Rust namespaces** — `src/sase/axe/` (155 modules), `src/sase/ace/`,
   `src/sase/ace/scheduler/`, `src/sase/chops/`, `sase.core.axe_chop_facade`;
   sase-core modules `axe_chop/`, `axe_status/`, `axe_overrun/`, `config::axe` and
   functions (`compose_axe_config`, `validate_axe_config`, `classify_axe_status`,
   `parse_chop_result`, `healthy_lumberjack`, …). Responsibility-split, never global
   rename.
6. **Wire and persistence (contract)** — schema-versioned status JSON (`lumberjacks`,
   `configured_chops`, `Chop*` types); config-selector kinds; `~/.sase/axe/**`
   (lumberjacks/, logs/, orchestrator.pid/lock, lifecycle.jsonl, desired_state.json);
   `~/.sase/ace_*` state files; saved tab IDs; op name `axe.bgcmd`.
7. **Agent/artifact identity (contract)** — `artifacts/ace-run/**` and workflow value
   `ace-run`; `chop:<lumberjack>/<chop>` refs; `.chop.<name>.` agent-name segments;
   `chop` tribe/source/producer labels; `chop_name`/`chop_lumberjack`/`parent_chop`.
8. **Observability** — Prometheus `sase_axe_cycles_total`,
   `sase_axe_lumberjacks_active`, `sase_axe_lumberjack_restarts_total`; telemetry
   component labels; log-pack sections; the `job=` log-field overlap.
9. **Docs/site/media** — README, `docs/ace.md`, `docs/axe.md`, cli/configuration/
   plugins/mentors/development guides, `troubleshooting/runner-slots.md` (reword the
   "scheduler fleet" ambiguity), INSTALL, demos; `sase.sh/ace/`+`/axe/` URLs with
   redirects; blog posts and `sase_ace_*` media.
10. **SASE memory and skills** — glossary strands (add Scheduler/Lane/Job/Job Run;
    retire Chop/Lumberjack; fix the Proc strand's "ACE's Procs tab"), memory notes,
    xprompt skill sources (e.g. `sase_notify`'s "axe notifications/errors") and their
    generated chezmoi copies — regenerate via the generated-skills flow, and use
    `/sase_memory_write` for the memory edits.
11. **Tests/CI/tooling** — `tests/ace/**`, `tests/test_axe_*`, fixtures,
    import-patching strings, snapshots, just recipes, CI names, spellcheck dicts.
12. **Downstream** — sase-core, sase-telegram, sase-github, sase-nvim, chezmoi
    (aliases `ace`/`axe`/`acei`/`aceii`, fish completions, xprompt snippets,
    per-machine YAML).
13. **Do not touch** — released changelogs, historical commit subjects, archived
    plans/research, old blog posts, compatibility fixtures. History keeps the name that
    was true at the time.

## 6. Rollout

Precedents to follow: task → proc kept `sase task` as a legacy alias plus facade
modules; ChangeSpec → Patch kept serde aliases. The `sase_flags` memory mandates a
`sunset` feature flag for every deprecated/back-compat branch.

1. **Vocabulary (cheap, most of the value).** New docs/UI/glossary language (SASE TUI,
   SASE scheduler, lane, job, job run); tab label "Scheduler" over internal ID `axe`;
   canonical `sase tui` + `sase scheduler` with hidden `ace`/`axe` aliases under sunset
   flags; regenerate xprompt skills to chezmoi; define the old↔new mapping once in the
   glossary. No persisted identity changes.
2. **Config keys, Rust first.** Add `tui:`/`scheduler:`/`lanes:`/`jobs:` (+
   `job_timeout`, `job_script_dirs`, `lane_log_*`) in sase-core composition/validation;
   accept legacy keys with a warning, fail actionably on ambiguous old+new conflicts;
   provide a migration preview; then migrate the chezmoi configs. Status wire: keep v1
   keys stable or issue a v2 schema — deserialization aliases alone don't protect old
   consumers of newly emitted JSON.
3. **Script/plugin API, dual-publish.** `sase_job_*` alongside `sase_chop_*` (user
   configs quote script names literally); export both `SASE_JOB_*` and `SASE_CHOP_*`;
   `sase.jobs` re-exporting `sase.chops`; coordinate sase-telegram; add `job:` artifact
   refs as alias for `chop:` before touching anything durable.
4. **Internal cleanup only where it improves boundaries.** Split `sase.ace` by
   responsibility before moving the TUI subtree; rename `sase.ace.scheduler` →
   `sase.patch_lifecycle`; rename Axe/lane/job internals after external compatibility
   exists. Leave `~/.sase/axe/` and `ace-run/` as internal names (or one-shot/dual-read
   migrations later — `ace-run` is a public workflow name in the Rust scan layer, so it
   needs dual-read, index compatibility, and retention coverage if ever renamed). Keep
   metric aliases long enough for dashboards. Remove public aliases only via normal
   sunset-flag deprecation after plugins and dotfiles have migrated.

## 7. Recommended names

| Today | Your proposal | **Recommended** |
| --- | --- | --- |
| `sase ace` | `sase tui` | **`sase tui`** (keep `sase ace` as hidden alias under a sunset flag) |
| ACE (prose) | "sase's TUI" | **"the SASE TUI"**, then "the TUI" |
| AXE (prose) | "sase's scheduler" | **"the SASE scheduler"**, then "the scheduler" |
| `sase axe …` | — | **`sase scheduler …`** (not `sase schedule`) |
| AXE tab | "Schedule" | **"Scheduler"** (alt: "Automation" if bgcmds stay; move them to Procs or a "Commands" section) |
| lumberjack | routine | **lane** ("scheduler lane" on first use; config `scheduler.lanes`; fallback: "schedule group") |
| chop | job | **job**; one execution = **job run**; executable = **job script** |
| `sase_chop_*` / `SASE_CHOP_*` / `sase.chops` | — | **`sase_job_*` / `SASE_JOB_*` / `sase.jobs`** (dual-publish through the sunset) |
| `ace:` / `axe:` config roots | — | **`tui:` / `scheduler:`** (legacy keys accepted in sase-core) |
| `sase.ace.scheduler` package | — | **`sase.patch_lifecycle`** (frees "scheduler") |
| `chop` agent tribe | — | **`job`** |
| orchestrator | — | keep **orchestrator** (the scheduler's supervisor) |
| `ace-run/`, `~/.sase/axe/` | — | leave as internal names; migrate only with dual-read if ever |

Canonical sentence for the glossary: *the **SASE scheduler** runs **jobs** in
independently supervised **lanes**; each execution is a **job run**; operators watch it
in the **Scheduler** tab of the **SASE TUI**, launched with `sase tui`.*
