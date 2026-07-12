# Improving Lumberjacks: What Chop Configuration Allows Today, and What It Should

**Date:** 2026-07-12
**Scope:** The `axe` lumberjack/chop subsystem (`src/sase/axe/`), the builtin chops
(`src/sase/scripts/sase_chop_*.py`), and the custom chops defined in the chezmoi repo
(`home/dot_config/sase/*.yml`, `home/bin/executable_sase_chop_*`).
**Question:** What can lumberjack/chop configuration express now, and which capabilities that are
currently hand-rolled in scripts and xprompts should be promoted to first-class, built-in support?

---

## 1. Executive summary

The chop configuration surface is deliberately thin. A chop can declare only **what** to run
(`agent:` prompt or a `sase_chop_<name>` script), **how often** (`run_every`), a **timeout**, and a
static **env** map. Everything else — *when should this actually fire?*, *what should it run across?*,
and *how should the launched agent be named/grouped/routed?* — has escaped out of config and into
imperative code: bespoke Python guard scripts, copy-pasted config rows, and gating logic buried inside
xprompt workflows.

The clearest evidence is in your own chezmoi chops:

- **`sase_chop_gh_actions_fix`** is a **551-line Python program** whose declarative residue (a repo
  list, a set of "actionable" CI conclusions, a dedupe-by-run policy, a "don't relaunch while a repair
  PR is open" guard, a timeout) is all config-shaped. Only its live-log harvesting is inherently code.
- **`sase_chop_sase_fix_just`** is a **158-line program that is almost entirely one guard** wrapped
  around what is otherwise a one-line agent chop.
- The **five `*_refresh_docs` chops** are identical except for three values (`project`, `gh_ref`,
  `threshold`) — a matrix faked by copy-paste.
- The same agent scaffold `%n:<name>-@ #gh:<repo> %g:chop #!sase/<xprompt>` is hand-assembled in
  **three separate layers**: YAML config, the wrapper scripts, and the xprompt fan-out steps.

**Recommendation.** Pull three escaped concerns back into declarative config, and fix two config
footguns:

1. **Declarative guards/triggers** (highest value) — `no_open_changespec: <prefix>`,
   `commits_since_marker`, and `once_per: <key>` — to retire three duplicated gating mechanisms.
2. **Matrix / per-project fan-out** (`for_each:`) — to collapse the 5 refresh_docs rows and unify with
   `SASE_GHA_FIX_REPOS`.
3. **Auto-injected agent scaffold** — auto-set the `chop` group, derive the agent name from the chop
   name, and add a `repo:` field feeding `#gh`, so an agent chop is just a `#!xprompt` reference.
4. **Env parity + shared/secret env** — agent chops currently *silently drop* `env:`; lumberjack-level
   env and secret references would de-duplicate the Telegram creds and the GHA repo list.
5. **Schema validation** — unknown keys are silently ignored today, so a typo like `run-every` fails
   quietly.

The rest of this document supports these with a full inventory and gap analysis.

---

## 2. How lumberjacks and chops work today (primer)

**Three-tier process model** (no systemd timers, no cron — a userspace Python loop that must stay
alive; the ACE TUI auto-starts it):

1. **Orchestrator** (`orchestrator.py`) — a single supervisor guarded by an `flock` lifetime lock
   (`lock.py`). It spawns one child process per lumberjack (`sase axe lumberjack run <name>`) and
   restarts any child that exits unexpectedly.
2. **Lumberjack** (`lumberjack.py`) — one process per lumberjack, driven by the `schedule` library:
   `scheduler.every(interval).seconds.do(_run_tick)`. Each tick writes a `context.json` plus two
   ChangeSpec snapshots, then runs its chops.
3. **Chop** — one unit of work per tick.

**Two kinds of chop**, discriminated by a single field — `chop.agent is not None`
(`chop_runner.py:166`):

- **Script chop** (`agent` unset): resolved by name to an executable. Lookup order
  (`chop_script_runner.py:18-53`): each `chop_script_dirs` entry (exact name) → the interpreter's bin
  dir (`sase_chop_<name>`) → `$PATH` (`sase_chop_<name>`). Invoked as `<script> --context <ctx.json>`;
  stdout+stderr streamed to a per-run log; exit code → `success`/`failure`; SIGKILL of the process
  group on timeout.
- **Agent chop** (`agent:` set): the string is passed **verbatim** to `launch_agent_from_cwd(...)` —
  the *same* launcher as `sase run`. So the `agent:` field is a full SASE prompt and supports the
  entire xprompt/directive pipeline (`#!`, `#gh`, `%n`, `%g`, `%auto`, swarm `---`, …). The chop layer
  never validates it; a bad prompt surfaces as `agent_failed` at launch.

**What a script chop receives** (`chop_script_context.py`): a JSON context with `max_hook_runners`,
`max_agent_runners`, `zombie_timeout_seconds`, the global ChangeSpec `query`, `lumberjack_name`,
`state_dir`, and `all_changespecs_file` / `filtered_changespecs_file`. The `query` shapes the
changespec list handed to the chop; it does **not** decide whether the chop runs.

---

## 3. The current configuration surface (what it allows *now*)

The config models are plain `@dataclass`es in `src/sase/axe/config.py` — hand-parsed, **not** pydantic,
with **no schema validation** (unknown keys are silently ignored).

### 3.1 `ChopConfig` (`config.py:32-41`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | str | required | Identifier; a bare-string YAML entry becomes `name` with empty description. |
| `description` | str | `""` | Human-readable only. |
| `agent` (alias `xprompt`) | str \| None | None | **The one switch** between agent-chop and script-chop. Full prompt string. |
| `run_every` | int \| None | None | Min spacing, from a duration string `s`/`m`/`h`. None → runs every tick. |
| `timeout` | int \| None | None | **Script chops only.** Duration string. |
| `env` | dict[str,str] | `{}` | **Script chops only** — silently dropped for agent chops (see §6). |

### 3.2 `LumberjackConfig` (`config.py:44-56`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | str | map key | |
| `interval` | int | `1` (seconds) | Tick cadence. A **bare integer of seconds** — *not* a duration string, unlike the chop fields. |
| `chop_timeout` | int \| None | None | Default per-chop **script** timeout (duration string). |
| `chops` | list[ChopConfig] | `[]` | |

### 3.3 `AxeConfig` (top level, `config.py:59-70`)

`max_hook_runners` (3), `max_agent_runners` (3), `zombie_timeout_seconds` (7200),
`lumberjack_log_max_bytes` (50 MiB), `verbose_lumberjack_diagnostics` (false), `query` (`""`),
`chop_script_dirs` (`[]`), `lumberjacks` (`{}`).

### 3.4 Scheduling, concurrency, and gating semantics

- **Cadence:** effective spacing = `max(interval, run_every)`. Last-run timestamps persist in
  `chop_timestamps.json` and are updated **only on success** (with a deliberate exception: a failed
  *agent* launch updates the timestamp when `run_every` is set, so a misconfigured agent chop doesn't
  relaunch every tick and flood the error digest). Manual runs (`sase axe chop run`, TUI `r`) **bypass**
  the `run_every` throttle.
- **Concurrency within a tick** (`lumberjack.py:216-228`): script chops are submitted to an
  **unbounded** `ThreadPoolExecutor` (they run concurrently); **agent chops run sequentially** in listed
  order, deliberately, to avoid same-tick workspace-allocation races. There is **no per-chop or
  per-lumberjack concurrency cap** in config — only the global `max_hook_runners`/`max_agent_runners`,
  and those are self-enforced by the chop *scripts* via a `SharedRunnerPool` flock, not by the framework.
- **The only gating primitives** are: `run_every` (time throttle), a global `maintenance.json` marker
  that pauses **all** chops, and an implicit singleton dedupe (agent chops dedupe on
  `(lumberjack, chop, prompt_hash)` against the live registry; script chops dedupe against any still-
  running run-history entry with a live PID).
- **No** `enabled`/toggle, `when`/`if` condition, `depends_on`, retry/backoff/jitter, cron/absolute-time
  scheduling, per-chop fan-out, structured output capture, or per-chop failure notification.
- **Timeout** applies to script chops only; **agent chops are fire-and-forget with no timeout or
  liveness enforcement**.
- **Failure surface:** every run writes a `ChopRunEntry` (status, error, traceback, exit code, pids,
  source) and appends to `recent_errors.json` (capped at the last 100). The only alerting path is the
  hourly `error_digest` chop — there is no per-chop `on_failure: notify`.

---

## 4. Inventory: builtin chops

All 13 builtin chops are **script chops**. Cadence = the owning lumberjack's `interval` (none set
`run_every`). Default wiring: `src/sase/default_config.yml:256-298`.

| Chop | Lumberjack (interval) | Category | Purpose |
|---|---|---|---|
| `hook_checks` | hooks (5s) | poll + dispatch | Complete finished hooks, start stale ones, zombie-detect |
| `mentor_checks` | hooks (5s) | dispatch | Start mentor workflows once hook prereqs met |
| `workflow_checks` | hooks (5s) | poll + dispatch | Complete/start CRS & fix-hook workflows |
| `pending_checks_poll` | hooks (5s) | poll | Poll background check results; reap orphan files |
| `comment_zombie_checks` | hooks (5s) | cleanup | Mark stale comment threads ZOMBIE |
| `suffix_transforms` | hooks (5s) | cleanup | Strip stale suffixes; update mail-readiness |
| `orphan_cleanup` | hooks (5s) | cleanup | Release claims orphaned by reverted PRs (dead PIDs) |
| `stale_running_cleanup` | hooks (5s) + checks (300s) | cleanup | Release claims held by dead processes |
| `wait_checks` | waits (10s) | poll + dispatch | Resolve wait deps; write `ready.json` |
| `cl_submitted_checks` | checks (300s) | dispatch | Start background `is_cl_submitted` checks |
| `comment_checks` | comments (60s) | dispatch | Start background `critique_comments` checks |
| `error_digest` | housekeeping (3600s) | notification | Hourly digest of recent errors |
| `pushgateway_cleanup` | **unwired** | cleanup + telemetry | Delete stale pushgateway groups |

**Structural observations (internal DX, not user config, but directly relevant to "better built-in
support"):**

- **9 of 13 are near byte-for-byte clones** — `argparse(--context)` → `read_chop_context` →
  build a `HookJobRunner(...)` → call one `run_*()` method. The seven-argument `HookJobRunner(...)`
  construction is copy-pasted nine times; the throwaway `def log(message, style=None): print(message)`
  closure is duplicated in **12 of 13** scripts (the `style` arg is always ignored in a subprocess).
- **Adding a builtin chop means editing five sites**: a new module, its `main()`, an `__init__.py`
  wrapper, two `pyproject.toml` entry-point lines, and a `default_config.yml` row.
- **Six independent "already handled?" stores coexist**: chop run-history, `run_every` timestamps,
  the PR-submitted `sync_cache`, `has_pending_check` files, `waiting.json`/`ready.json` markers, and
  `last_error_digest_ts`. "Detect a dead PID and release its lease" is reimplemented ~4 times against
  four different files.
- **Two latent bugs worth noting:** `pushgateway_cleanup` is a config-orphan (a real script + entry
  point that no lumberjack references — runnable only via `sase axe chop run`); and the
  `cl_submitted_checks` config name maps through a legacy alias to `sase_chop_pr_submitted_checks`,
  i.e. two console scripts for one implementation.

---

## 5. Inventory & review: your chezmoi chops

This is the section you specifically asked for — the custom chops, not just the builtins.

### 5.1 Script chops (Python programs in `home/bin/`)

| Chop | Lumberjack | Cadence | Size | What it does |
|---|---|---|---|---|
| `sase_fix_just` | run_every | 60m | 158 lines | Guard: skip if any open `sase_fix_just_*` ChangeSpec (WIP/Draft/Ready/Mailed) exists; else launch one agent running the `fix_just` xprompt. |
| `gh_actions_fix` | github_actions | 15m (+`timeout: 120s`) | 551 lines | For each repo in `SASE_GHA_FIX_REPOS`, poll the latest GH Actions run; if it failed (and not already handled, and no open `sase_gha_fix_*` ChangeSpec), fetch failed-step logs and launch a fixer agent seeded with them. |

### 5.2 Agent chops (config `agent:` strings in `sase_athena.yml`)

| Chop | Lumberjack | Cadence | Prompt |
|---|---|---|---|
| `sase_pylimit_split` | run_every | 60m | `%n:sase_pylimit_split-@ #gh:sase %g:chop #!sase/pylimit_split %auto` |
| `sase_recent_bug_audit` | code_quality | 60m | `%n:… #gh:sase %g:chop #!sase/audit_recent_bugs` |
| `sase_recent_improvement_audit` | code_quality | 60m | `%n:… #gh:sase %g:chop #!sase/audit_recent_improvements` |
| `sase_refresh_docs` | refresh_docs | 3h | `%n:… #gh:sase-org/sase %g:chop #!sase/refresh_docs` |
| `sase_core_refresh_docs` | refresh_docs | 24h | `…#!sase/refresh_docs(project=sase-core, gh_ref=sase-org/sase-core, threshold=25)` |
| `sase_github_refresh_docs` | refresh_docs | 24h | `…(project=sase-github, gh_ref=sase-org/sase-github, threshold=25)` |
| `sase_nvim_refresh_docs` | refresh_docs | 24h | `…(project=sase-nvim, gh_ref=sase-org/sase-nvim, threshold=25)` |
| `sase_telegram_refresh_docs` | refresh_docs | 24h | `…(project=sase-telegram, gh_ref=sase-org/sase-telegram, threshold=25)` |

Plus two **builtin** chops configured purely through `env:` in `sase.yml`: `tg_inbound` / `tg_outbound`
(lumberjack `telegram`, interval 5s), which carry the identical `SASE_TELEGRAM_BOT_USERNAME` and
`SASE_TELEGRAM_BOT_CHAT_ID` (`8990449281`) on both rows.

### 5.3 Decoding the agent-chop directive scaffold

`%n:sase_pylimit_split-@ #gh:sase %g:chop #!sase/pylimit_split %auto`:

| Token | Meaning |
|---|---|
| `%n:sase_pylimit_split-@` | Agent **name template**; `-@` yields a stable unique name. Restates the chop's own `name:`. |
| `#gh:sase` | GitHub **VCS workflow block** — run in a clone of the `sase`-aliased repo. Restates a fixed target. |
| `%g:chop` | Sets the agent **group** to `chop`. Appears on **every** chop — pure boilerplate. |
| `#!sase/pylimit_split` | **Invoke the xprompt workflow** (the only meaningfully-varying token). |
| `%auto` | Autonomous / auto-approve. Present only on `pylimit_split`; omitted elsewhere — an inconsistency. |
| `(project=…, gh_ref=…, threshold=…)` | xprompt **input parameters** (`refresh_docs.yml:4-16`). |

**The scaffold `%n:<name>-@ #gh:<repo> %g:chop #!sase/<xprompt>` is hand-assembled at three layers:**
(1) the YAML above; (2) inside the wrapper scripts —
`FIX_JUST_PROMPT = "%n:sase_fix_just-@ #gh:sase %g:chop #!sase/fix_just"` and
`gh_actions_fix`'s `f"#gh:{repo} %g:chop #pr({change_name}) %n:{run_agent_name}"`; and (3) again inside
each xprompt when *it* fans out child agents (`refresh_docs.yml`, `audit_recent_bugs.yml` build the same
`%name:… #gh:{gh_ref} %g:chop …` triple).

### 5.4 What the two scripts do that config can't express

- **`sase_fix_just`** is *entirely* a guard: read the ChangeSpec snapshot from the chop context, block
  if any open `sase_fix_just_*` ChangeSpec exists (failing **safe** — skip — on a missing snapshot),
  else `sase run -d <one fixed prompt>`. **If config had a declarative open-ChangeSpec guard, this whole
  script collapses to a one-line agent chop** like `sase_pylimit_split`.
- **`gh_actions_fix`** layers several config-shaped concerns over a small imperative core:
  - *Fan-out* over `SASE_GHA_FIX_REPOS` (a space-separated string re-parsed in Python).
  - *Trigger predicate*: status `completed` **and** conclusion ∈ `{action_required, failure,
    startup_failure, timed_out}` (hard-coded sets).
  - *Dedupe by external event*: its own `gh_actions_fix_seen.json` keyed `"{run_id}:attempt:{attempt}"`.
  - *Open-ChangeSpec guard* (prefix `sase_gha_fix_`) — **duplicated verbatim** from `sase_fix_just`.
  - *Bespoke naming*: `repo_slug` → `pr_name`/`agent_name` slugify recipes.
  - The **genuinely imperative residue** is only: `gh run list` polling, `gh run view --log-failed`
    harvesting + 60 KiB truncation, and seeding that live output into the launch prompt.

### 5.5 Cross-cutting duplication in the custom chops

- **Three bespoke gating mechanisms**, all config-shaped, all in code because `run_every` is the only
  declarative gate: (a) the **open-ChangeSpec-prefix guard** (duplicated across both scripts);
  (b) the **commit-count-since-marker threshold** (triplicated across `refresh_docs.yml`,
  `audit_recent_bugs.yml`, `audit_recent_improvements.yml` — each does the same marker read →
  `git rev-list --count` → force-on-first-run → `should_launch` → `update_marker` dance);
  (c) the **per-run seen-dedupe** in `gh_actions_fix`.
- **Fan-out expressed two inconsistent ways**: copy-paste (5 refresh_docs rows) vs. an env-string list
  (`SASE_GHA_FIX_REPOS`).
- **Credentials/targets as plaintext `env:`**, duplicated (Telegram chat ID on two rows; the GHA repo
  list smuggled through an env var).

---

## 6. Gap analysis — recurring patterns that escaped config

| # | Pattern (hand-rolled today) | Where it recurs | Should be… |
|---|---|---|---|
| G1 | "Don't relaunch while an open repair ChangeSpec (prefix X) exists" | `sase_fix_just`, `gh_actions_fix` (verbatim dup) | A declarative chop **guard** |
| G2 | "Only run when ≥N new commits since a marker" | 3 xprompts (triplicated) | A declarative chop **trigger** |
| G3 | "Fire once per unique external event (run_id:attempt)" | `gh_actions_fix` seen-file | A declarative **once_per** dedupe key |
| G4 | Run one template across N projects/repos | 5 refresh_docs rows; `SASE_GHA_FIX_REPOS` | A **matrix / for_each** field |
| G5 | `%n:<name>-@ #gh:<repo> %g:chop` scaffold | YAML + scripts + xprompts (3 layers) | **Auto-injected** by the chop runner |
| G6 | `env:` silently dropped on agent chops; creds duplicated | agent chops; tg_inbound/outbound | **Env parity + shared/secret env** |
| G7 | Typos in field names fail silently | whole config surface | **Schema validation** |
| G8 | 9-way clone scaffold; 5 edit-sites to add a builtin | builtin scripts | A **chop registry/decorator** |
| G9 | No agent-chop timeout/liveness, no retries/jitter, no `enabled` | framework | Reliability/ergonomics fields |

The unifying diagnosis: **config today is a thin launcher.** It answers *what* and *how often*, but
every *when-to-actually-fire* decision (G1–G3), every *what-to-run-it-across* decision (G4), and every
*how-to-name-and-route-the-agent* decision (G5) has leaked into imperative code — scripts you maintain
by hand and gating logic buried inside xprompts.

---

## 7. Recommendations

Ranked by value-to-effort. Config snippets below are **illustrative proposals, not existing syntax.**

### Tier 1 — retire the most duplication

**R1. Declarative guards & triggers (addresses G1, G2, G3).**
Add an optional `guard:` / `trigger:` block that the chop runner evaluates *before* dispatch, using the
context it already builds (it already loads the ChangeSpec snapshot and knows `state_dir`):

```yaml
# sase_fix_just: 158-line script → one agent chop
- name: sase_fix_just
  agent: "#!sase/fix_just"
  run_every: 60m
  guard:
    no_open_changespec: sase_fix_just_*     # skip while a repair PR is open

# refresh_docs: the marker/threshold dance moves out of the xprompt
- name: sase_refresh_docs
  agent: "#!sase/refresh_docs"
  run_every: 3h
  trigger:
    commits_since_marker: { project: sase, threshold: 100 }

# gh_actions_fix: the seen-file becomes a declared dedupe key
  once_per: "{gh.run_id}:{gh.attempt}"       # fire once per unique external event
```

This deletes `sase_fix_just` entirely, un-triplicates the commit-count logic, and removes the bespoke
seen-file. Guard results should be recorded on the run entry (`status: skipped, reason: guard`) so the
TUI can show *why* a chop didn't fire — a strict improvement over today's silent no-ops.

**R2. Matrix / per-project fan-out (addresses G4).**
A `for_each:` that expands one templated chop into N, unifying the two inconsistent fan-out styles:

```yaml
- name: refresh_docs
  agent: "#!sase/refresh_docs(project={{project}}, gh_ref={{gh_ref}}, threshold={{threshold}})"
  run_every: 24h
  for_each:
    - { project: sase-core,     gh_ref: sase-org/sase-core,     threshold: 25 }
    - { project: sase-github,   gh_ref: sase-org/sase-github,   threshold: 25 }
    - { project: sase-nvim,     gh_ref: sase-org/sase-nvim,     threshold: 25 }
    - { project: sase-telegram, gh_ref: sase-org/sase-telegram, threshold: 25 }
```

Same construct lets `gh_actions_fix` take `for_each: [repo1, repo2]` instead of `SASE_GHA_FIX_REPOS`.
Fanned-out chop names should derive deterministically (e.g. `refresh_docs[sase-core]`) so dedupe and
run-history stay per-instance.

**R3. Auto-injected agent scaffold (addresses G5).**
The runner already tags chop agents (`SASE_CHOP_*`, prompt-hash). Have it also (a) default the group to
`chop`, (b) derive the agent name from the chop `name` unless `%n` is given, and (c) accept a `repo:`
field that feeds `#gh`. An agent chop becomes just its meaningful token:

```yaml
- name: sase_pylimit_split
  repo: sase
  autonomous: true
  agent: "#!sase/pylimit_split"     # group=chop and name auto-injected
```

### Tier 2 — fix the footguns

**R4. Env parity + shared/secret env (addresses G6).**
First, make agent chops honor `env:` (today it is silently dropped — a latent bug: someone will set it
and be baffled). Second, add lumberjack-level `env:` so the Telegram creds aren't repeated on both rows,
and a secret reference (`env: { SASE_TELEGRAM_BOT_CHAT_ID: !secret telegram/chat_id }`) so IDs/tokens
aren't plaintext in `sase.yml`. `chop_doctor.py` already knows how to resolve a Telegram token from
env → file → `pass`; a `!secret` resolver could reuse that discovery.

**R5. Schema validation (addresses G7).**
Validate the `axe:` block on load and warn (or error) on unknown keys and malformed durations. Today
`run-every: 60m` (hyphen) or `run_every: 60min` parse to `None` and the chop silently runs every tick.
Also enrich the duration regex (`^(\d+)(s|m|h)$`) to accept days and compound forms (`1h30m`).

### Tier 3 — internal DX & reliability

**R6. Builtin chop registry (addresses G8).** Replace the 5-edit-site + 9-way-clone pattern with a
`@chop("hook_checks", scope="filtered")` decorator/registry so a builtin script chop is declared once.
Fold the duplicated `log` closure and `argparse(--context)`/context-hydration preamble into the
decorator.

**R7. Reliability fields (addresses G9).** Consider: `enabled: false` (soft-disable without deleting a
row), optional `jitter` to de-sync ticks, bounded `retries`/`backoff` for transient failures, and a
liveness/timeout policy for agent chops (today they are fire-and-forget). Optional per-chop
`on_failure: notify` would generalize the single hourly `error_digest` path.

**R8. Consolidate the "already handled?" stores.** Longer-term, the six dedupe mechanisms (§4) and the
~4 dead-PID-reclamation implementations want a single "PID lease + high-water-mark" abstraction the
runner owns, which R1's `once_per` and R3's auto-dedupe would build on.

### What should stay imperative

The one thing **not** to force into config is `gh_actions_fix`'s live-state harvesting — polling `gh`
and seeding failed-step logs into a prompt. That is genuinely a "gather external state → inject into the
launch prompt" step. A reasonable pattern is a thin **producer** script chop that emits structured
events, consumed by a declarative agent-chop template — but that is a later refinement, not Tier 1.

---

## 8. Implementation considerations

- **Rust core boundary.** Per this repo's boundary rule, chop **gating/trigger evaluation, fan-out
  expansion, and dedupe/lease bookkeeping** are backend/domain behavior that a future CLI, web
  dashboard, or editor integration would need to match the TUI on. New logic for R1–R2 and R8 should
  most likely live in `../sase-core` (`sase_core_rs`) with thin Python adapters here, rather than being
  reimplemented in Python. Presentation (how the TUI renders a skipped/guarded chop) stays in this repo.
- **Backward compatibility.** All proposed fields are additive and optional; existing configs keep
  working. Migration is opt-in: rewrite `sase_fix_just` first (biggest simplification, lowest risk),
  then the refresh_docs matrix, then the scaffold defaults.
- **Observability first.** Whatever guard/trigger/skip mechanism lands (R1) must record a reason on the
  run entry. The current subsystem's biggest UX weakness is silent no-ops; declarative gating is only a
  win if "why didn't this fire?" is answerable from run history.
- **Keep the escape hatch.** Script chops and raw `agent:` prompts should remain fully supported for the
  genuinely-imperative cases (§7, "what should stay imperative").

---

## Appendix — file map

**Config & engine:** `src/sase/axe/config.py` (models/parsing), `lumberjack.py` (scheduler/tick),
`orchestrator.py`, `lock.py`, `maintenance.py`, `runner_pool.py` (global concurrency).
**Dispatch:** `chop_runner.py`, `chop_runner_types.py`, `chop_runner_agent.py`, `chop_runner_script.py`,
`chop_runner_context.py`, `chop_script_runner.py`, `chop_script_context.py`, `chop_agents.py`.
**State:** `_state_chops.py`, `_state_lumberjack.py`, `_state_scheduler.py`.
**Inventory/UX:** `chop_inventory.py`, `chop_doctor.py`, `chop_render.py`.
**Builtin chops:** `src/sase/scripts/sase_chop_*.py`; business logic in `src/sase/axe/hook_jobs.py`,
`check_cycles.py`, and `src/sase/ace/scheduler/`.
**Defaults & entry points:** `src/sase/default_config.yml:248-298`, `pyproject.toml:102-115`.
**Chezmoi custom chops:** `home/bin/executable_sase_chop_sase_fix_just`,
`home/bin/executable_sase_chop_gh_actions_fix`; config in `home/dot_config/sase/sase_athena.yml`
(axe.lumberjacks) and `home/dot_config/sase/sase.yml` (telegram).
**Referenced xprompts (sase repo):** `xprompts/{pylimit_split,fix_just,audit_recent_bugs,
audit_recent_improvements,refresh_docs}.yml`.
