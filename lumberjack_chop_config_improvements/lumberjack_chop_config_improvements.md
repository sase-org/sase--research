# Improving Lumberjacks: Chop Configuration Audit and Recommendations

**Date:** 2026-07-12
**Scope:** SASE commit `599f6feb2` (runtime `sase 0.10.2+untagged.gf115c3c5b`); chezmoi commit
`f6f90f86a`. Covers the `axe` subsystem (`src/sase/axe/`), the 13 builtin chop scripts
(`src/sase/scripts/sase_chop_*.py`), and Bryan's chezmoi-defined chops
(`home/dot_config/sase/*.yml`, `home/bin/executable_sase_chop_*`).
**Question:** What can lumberjack/chop configuration express today, and which capabilities that are
currently hand-rolled in scripts and xprompts deserve first-class built-in support?
**Sources:** Consolidated from two independent audits —
[`lumberjack_chop_config_improvements__a.md`](lumberjack_chop_config_improvements__a.md) (codex) and
[`lumberjack_chop_config_improvements__b.md`](lumberjack_chop_config_improvements__b.md) (claude) —
which corroborate each other on every load-bearing claim; key claims (config fields, agent-chop `env`
drop, duration parsing) were re-verified against the source before consolidation.

---

## 1. Executive summary

The execution substrate is strong — process supervision, live logs, bounded run history, dedupe,
manual runs, doctor/inventory, metrics — but the configuration language is deliberately thin. A chop
declares only **what** to run (`agent:` prompt or a `sase_chop_<name>` script), **how often**
(`run_every`), a script **timeout**, and a static **env** map. Everything else — *when should this
actually fire?*, *what should it run across?*, *how should the launched agent be named/grouped?*, and
*did the work actually succeed?* — has escaped into imperative code.

The effective Athena runtime has **10 lumberjacks and 25 chop entries** (17 script-backed, 8
agent-backed), 12 of them from chezmoi rather than bundled defaults. All configured scripts resolve;
doctor warns only about two installed-but-unconfigured scripts. Bryan's custom chops are the clearest
evidence of the gap:

- **`gh_actions_fix`** is a 551-line Python program whose declarative residue (repo list, actionable
  CI conclusions, dedupe-by-run-attempt, open-ChangeSpec guard, timeout) is all config-shaped; only
  its live-log harvesting is inherently code.
- **`sase_fix_just`** is 158 lines that are almost entirely *one guard* around a one-line agent chop.
- The **five `*_refresh_docs` chops** are identical except for `(project, gh_ref, threshold)` — a
  matrix faked by copy-paste.
- The agent scaffold `%n:<name>-@ #gh:<repo> %g:chop #!sase/<xprompt>` is hand-assembled at **three
  layers**: YAML config, the wrapper scripts, and the xprompt fan-out steps.
- Three bespoke gating mechanisms (open-ChangeSpec guard, commit-count markers, seen-event dedupe)
  live in code because `run_every` is the only declarative gate.

**The highest-leverage improvement is not more built-in chops.** It is a first-class
**trigger/probe → decision → action** layer, backed by runner-owned checkpoints, keyed concurrency,
lifecycle-aware outcomes, and fail-closed validation. Ranked:

1. **Declarative guards/triggers** with typed results and checkpoint policies (retires
   `sase_fix_just`, un-triplicates the commit-count markers, replaces the seen-file).
2. **End-to-end action lifecycle** — `agent_launched` should be a phase, not the terminal truth —
   plus structured (machine-readable) chop results.
3. **Keyed concurrency and inhibition** with real caps for direct agent chops.
4. **Fail-closed validation and env parity** (agent chops silently drop `env:` today).
5. **Matrix/`for_each` fan-out and typed workflow actions** with auto-injected agent scaffold.

One explicit non-goal: do **not** restore the retired arbitrary shell `gate:` field. Git history
shows it was added to prevent pointless `pylimit_split` spawns (chezmoi `919ba759`) and deliberately
removed (chezmoi `edf0f1c4`, sase `0d1f4909e`) once discovery moved into the workflow. The missing
abstraction is a safe *typed* trigger protocol, not another opaque shell string in YAML.

---

## 2. How the subsystem works today

**Three-tier process model** (no systemd timers, no cron — a userspace Python loop that must stay
alive; the ACE TUI auto-starts it unless `--no-axe`):

1. **Orchestrator** (`orchestrator.py`) — single supervisor under an `flock` lifetime lock
   (`lock.py`); spawns one child per lumberjack (`sase axe lumberjack run <name>`) and restarts any
   child that exits unexpectedly.
2. **Lumberjack** (`lumberjack.py`) — one process per lumberjack, driven by the `schedule` library
   (`scheduler.every(interval).seconds`). Each tick atomically writes a `context.json` plus two
   ChangeSpec snapshots (all / query-filtered), then runs its chops. The first tick runs immediately.
3. **Chop** — one unit of work per tick.

**Two chop kinds**, discriminated by a single field — `chop.agent is not None`
(`chop_runner.py:166`):

- **Script chop** (`agent` unset): resolved by name — each `chop_script_dirs` entry (exact name) →
  the interpreter's bin dir (`sase_chop_<name>`) → `$PATH` (`sase_chop_<name>`). Invoked as
  `<script> --context <ctx.json>` from the lumberjack state dir (the daemon's launch CWD may be a
  deleted ephemeral workspace); stdout+stderr streamed to a per-run log; exit code →
  `success`/`failure`; SIGKILL of the whole process group on timeout; PID recorded early.
- **Agent chop** (`agent:`/legacy alias `xprompt:` set): the string is passed **verbatim** to
  `launch_agent_from_cwd(...)` — the same launcher as `sase run`. The field is therefore a full SASE
  prompt supporting the entire xprompt/directive pipeline (`#!`, `#gh`, `%n`, `%g`, `%auto`, swarm
  `---`, …). The chop layer never validates it; a bad prompt surfaces as `agent_failed` at launch.
  The runner injects `SASE_CHOP_LUMBERJACK` / `SASE_CHOP_NAME` / `SASE_CHOP_RUN_ID` /
  `SASE_CHOP_PROMPT_HASH` and records a durable registry entry for dedupe.

The script context JSON (`chop_script_context.py`) carries runner limits, the global ChangeSpec
`query`, `lumberjack_name`, a writable `state_dir`, and the two snapshot paths. The `query` shapes
the ChangeSpec list handed to chops; it does **not** gate whether a chop runs.

---

## 3. The configuration surface (what it allows now)

Config models are plain `@dataclass`es, hand-parsed in `src/sase/axe/config.py`. A JSON schema
exists (`src/sase/config/sase.schema.json:365-494`) for editor/Admin Center use, but the **runtime
parser does not validate**: unknown keys are silently ignored and invalid durations degrade to
`None`.

### 3.1 `ChopConfig` (`config.py:32-41`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | str | required | Script-lookup name and state/history identity. Bare-string YAML entries remain accepted (legacy). No separate stable ID; duplicate names are not rejected. |
| `description` | str | `""` | Operator-facing. Docs call it required; parser allows absence. |
| `agent` (alias `xprompt`) | str \| None | None | **The one switch** between agent and script chop; `agent` wins if both are set. Full prompt string, unvalidated. |
| `run_every` | int \| None | None | Minimum spacing, duration string (`s`/`m`/`h` only). Invalid → `None` → **runs every tick**. |
| `timeout` | int \| None | None | **Script chops only**; parsed but never applied to agent chops. |
| `env` | dict[str,str] | `{}` | **Script chops only** — silently dropped for agent chops (§4). |

### 3.2 `LumberjackConfig` (`config.py:44-56`) and `AxeConfig` (`config.py:59-70`)

| Field | Notes |
|---|---|
| `interval` | Tick cadence in **bare integer seconds** (default 1; not a duration string, unlike chop fields; no positive-minimum check). Schedules the whole tick, not each chop. |
| `chop_timeout` | Default per-chop **script** timeout (duration string). Ignored by agent chops. |
| `chops` | The chop list. |
| `max_hook_runners` / `max_agent_runners` (3/3) | Global runner caps — enforced by the chop *scripts* via `SharedRunnerPool` flock, **not** by the framework; direct `agent:` chops never acquire a slot. |
| `zombie_timeout_seconds` (7200), `lumberjack_log_max_bytes` (50 MiB), `verbose_lumberjack_diagnostics`, `query`, `chop_script_dirs` | Passed into context / log bounding / script discovery. One global `query`; no per-lumberjack or per-chop filter. |

Duration parsing: `^(\d+)(s|m|h)$` — no days, no compound (`1h30m`), no fractions, no bare integers.

### 3.3 Merge and composition model

Effective config is a deep merge: bundled defaults → plugin defaults (list concat) → user
`~/.config/sase/sase.yml` (list replace) → sorted `sase_*.yml` overlays (list concat) → project-local
`./sase.yml`. Maps merge recursively, so overlays add lumberjacks easily — but **lists are not merged
by chop identity**: an overlay can append a chop but cannot patch one field of, disable, or delete an
existing entry. Re-declaring a name creates a duplicate entry rather than overriding it.

### 3.4 Scheduling, concurrency, and gating semantics that matter in practice

- **Cadence:** effective spacing = `max(interval, run_every)`. Timestamps persist across restarts
  (`chop_timestamps.json`) and update **only on success** — with one deliberate exception: a failed
  *agent launch* updates the timestamp when `run_every` is set, throttling a misconfigured agent chop
  to normal cadence instead of every tick. A failed script retries next tick. A daemon outage
  produces at most one catch-up launch; missed intervals are not replayed. Manual runs
  (`sase axe chop run`, TUI `r`) bypass `run_every` but keep timeout/context/dedupe/history.
- **Concurrency within a tick:** script chops run in an **unbounded** `ThreadPoolExecutor`; agent
  chops run **sequentially** in listed order (deliberate, to avoid same-tick workspace-allocation
  races). No per-chop or per-lumberjack cap exists, and separate lumberjacks are separate processes —
  so the eight configured agent chops across `run_every`/`code_quality`/`refresh_docs` can launch
  concurrently, outside any named runner cap.
- **The only gating primitives:** `run_every`; a global `maintenance.json` marker that pauses all
  chops (stale markers auto-cleared); and implicit singleton dedupe — agent chops on
  `(lumberjack, chop, prompt_hash)` against the live registry, script chops against a still-running
  run-history entry with a live PID (stale PID-less rows finalized after a grace window).
- **Agent chops are fire-and-forget:** no timeout, no liveness enforcement, and the run-history row
  ends as `agent_launched` immediately — the chop dashboard answers "did AXE launch it?" rather than
  "did the maintenance job succeed?" The eventual workflow no-op/success/failure never flows back.
- **Failure surface:** every run writes a `ChopRunEntry` (status, error, traceback, exit code, PIDs,
  source, output size; 10 terminal runs retained per chop) and errors append to
  `recent_errors.json` (last 100). The only alerting path is the hourly `error_digest` chop; there is
  no per-chop `on_failure: notify`.
- **Notably absent (confirmed by grep):** `enabled`, `when`/`if`/`gate`, `depends_on`,
  retry/backoff/jitter, cron/absolute-time schedules, fan-out/matrix, structured output capture,
  per-chop concurrency, per-chop notifications.

---

## 4. Inventory

### 4.1 Effective Athena runtime (10 lumberjacks, 25 entries)

| Lumberjack | Tick | Chops | Provenance |
|---|---:|---|---|
| `hooks` | 5s | 8 script chops | bundled defaults |
| `waits` | 10s | `wait_checks` | bundled defaults |
| `checks` | 300s | `cl_submitted_checks`, `stale_running_cleanup` (backstop) | bundled defaults |
| `comments` | 60s | `comment_checks` | bundled defaults |
| `housekeeping` | 3600s | `error_digest` | bundled defaults |
| `telegram` | 5s | `tg_inbound`, `tg_outbound` | chezmoi base + `sase-telegram` executables |
| `run_every` | 60s | `sase_pylimit_split` (60m), `sase_fix_just` (60m) | chezmoi Athena overlay |
| `code_quality` | 60s | two recent-commit audit agents (60m) | chezmoi Athena overlay |
| `refresh_docs` | 60s | five repository docs agents (3h/24h) | chezmoi Athena overlay |
| `github_actions` | 300s | `gh_actions_fix` (15m, 120s timeout) | chezmoi Athena overlay + custom executable |

### 4.2 Builtin chops — internal DX findings

All 13 builtins are script chops; none sets `run_every`. Structurally:

- **9 of 13 are near byte-for-byte clones**: `argparse(--context)` → `read_chop_context` → construct
  the same seven-argument `HookJobRunner(...)` → call one `run_*()` method. The throwaway
  `def log(message, style=None): print(message)` closure is duplicated in 12 of 13 scripts.
- **Adding a builtin chop means editing five sites**: new module, `main()`, `__init__.py` wrapper,
  two `pyproject.toml` entry-point lines, and a `default_config.yml` row.
- **Six independent "already handled?" stores coexist**: chop run-history, `run_every` timestamps,
  the PR-submitted `sync_cache`, `has_pending_check` files, `waiting.json`/`ready.json` markers, and
  `last_error_digest_ts`. "Detect a dead PID and release its lease" is reimplemented ~4× against four
  different state files.
- **Wiring debt:** `pushgateway_cleanup` is a config-orphan (real script + entry point, referenced by
  no lumberjack; runnable only manually), and config name `cl_submitted_checks` maps through a legacy
  alias to `sase_chop_pr_submitted_checks` (two console scripts, one implementation).
- Every script hand-assembles the same `key=value … reason=<…>` summary-line convention with bespoke
  f-strings — a de-facto log-parsing contract that is not shared code.

### 4.3 Chezmoi custom chops (the specific ask)

**Script chops** (Python programs deployed from `home/bin/`, with bash regression tests):

| Chop | Cadence | Size | What it does |
|---|---|---|---|
| `sase_fix_just` | 60m | 158 lines | Guard: skip while any open `sase_fix_just_*` ChangeSpec (WIP/Draft/Ready/Mailed) exists — failing *safe* (skip) on a missing snapshot — else `sase run -d` one fixed `fix_just` workflow prompt. |
| `gh_actions_fix` | 15m | 551 lines | Per repo in `SASE_GHA_FIX_REPOS`: poll the latest GH Actions run (`gh run list`); classify conclusions against hard-coded actionable/ignored sets; dedupe via `gh_actions_fix_seen.json` keyed `{run_id}:attempt:{attempt}`; block on open `sase_gha_fix_*` ChangeSpecs (checked before any `gh` call); harvest failed-step logs (`--log-failed`, 60 KiB cap, `--verbose` fallback); build a seeded prompt and launch a fixer agent; emit structured per-repo outcome counters. |

**Agent chops** (`sase_athena.yml`): `sase_pylimit_split` (60m, the only one with `%auto`),
`sase_recent_bug_audit` / `sase_recent_improvement_audit` (60m), and five `*_refresh_docs` chops
(3h for sase at threshold 100; 24h at threshold 25 for sase-core/-github/-nvim/-telegram) — the five
differ only in `(project, gh_ref, threshold)` workflow inputs. Additionally, the builtin
`tg_inbound`/`tg_outbound` are configured purely through `env:`, with identical plaintext Telegram
credentials (`SASE_TELEGRAM_BOT_USERNAME`, chat ID) duplicated on both rows.

**The directive scaffold**, e.g. `%n:sase_pylimit_split-@ #gh:sase %g:chop #!sase/pylimit_split %auto`:
`%n:<name>-@` (name template restating the chop's own `name:`), `#gh:<repo>` (VCS workspace block),
`%g:chop` (groups the agent under the `chop` root in the TUI — pure boilerplate on every entry),
`#!sase/<xprompt>` (the only meaningfully-varying token), optional `(inputs…)`. This scaffold is
hand-assembled at three layers: the YAML, the wrapper scripts
(`FIX_JUST_PROMPT = "%n:sase_fix_just-@ #gh:sase %g:chop #!sase/fix_just"`;
`gh_actions_fix`'s `f"#gh:{repo} %g:chop #pr({change_name}) %n:{run_agent_name}"`), and again inside
each xprompt's own fan-out steps. Every layer also reinvents the same slugify → agent/PR-name recipe.

**Cross-cutting observations:**

- **"Do I have work?" is implemented three different ways** — file scanning (`pylimit_split`, which
  today runs *inside* a launched agent workspace just to discover a no-op), git-history-vs-marker
  comparison (triplicated near-identically across `refresh_docs.yml`, `audit_recent_bugs.yml`,
  `audit_recent_improvements.yml`: marker read → `rev-list --count` → force-on-first-run →
  `should_launch` → symmetric marker update), and provider polling + seen-set (`gh_actions_fix`).
- **At least three dedupe lifetimes** exist beyond the runner's live-process dedupe, and a single
  `already_running` bit cannot represent them: *event* dedupe (same run attempt), *work-product*
  dedupe (open matching ChangeSpec), and *watermark* dedupe (commits already covered).
- **The `gh_actions_fix` guard is global:** one open `sase_gha_fix_*` ChangeSpec blocks checking
  *every* configured repository — a keyed (per-repo) guard would be strictly better.
- **Checkpoint timing is correctness-critical and unwritten convention:** markers advance only after
  a successful *launch*, but "launch succeeded" ≠ "work completed." Jobs differ in whether they should
  checkpoint on observation, accepted launch, or completed action.
- **Outputs already try to be structured** (`repos_checked`, `dedupe_skips`, `launch_failures`,
  `should_launch`, `reason`, …) but AXE stores text only, so the TUI cannot distinguish a healthy
  no-op from an action or a degraded provider check.
- **Fan-out is expressed two inconsistent ways** — copy-paste (5 rows) vs. an env-string list
  (`SASE_GHA_FIX_REPOS`, space-separated, re-parsed in Python).

---

## 5. Gap analysis

| # | Pattern hand-rolled today | Where it recurs | Should be |
|---|---|---|---|
| G1 | "Don't relaunch while an open ChangeSpec (prefix X) exists" | both custom scripts, verbatim dup | declarative **inhibition guard** (keyed) |
| G2 | "Run only when ≥N commits since a marker" | 3 xprompts, triplicated | declarative **trigger** + runner-owned watermark |
| G3 | "Fire once per external event" | `gh_actions_fix` seen-file | declarative **once_per** dedupe key |
| G4 | One template × N projects/repos | 5 refresh_docs rows; `SASE_GHA_FIX_REPOS` | **matrix / for_each** with stable derived IDs |
| G5 | `%n:<name>-@ #gh:<repo> %g:chop` scaffold | 3 layers (YAML, scripts, xprompts) | **auto-injected** by the chop runner |
| G6 | `env:` silently dropped on agent chops; plaintext creds duplicated | agent chops; tg rows | **env parity** + shared/secret env references |
| G7 | Typos and bad durations fail silently (open) | whole runtime parser | **fail-closed validation** + doctor checks |
| G8 | `agent_launched` is terminal; outcomes are text | all agent chops | **lifecycle-aware statuses** + structured results |
| G9 | Live-process-only dedupe; no caps on direct agent chops | framework | **keyed concurrency** + real resource caps |
| G10 | Overlays can't patch/disable one packaged chop | config merge model | **keyed chop maps** + `enabled` |
| G11 | 9-way builtin clone; 5 edit-sites per new builtin; 6 dedupe stores | builtin scripts | **chop registry/decorator**; shared lease/watermark helpers |
| G12 | No retries/backoff/jitter/cron/agent-timeout | framework | reliability & scheduling fields |

Unifying diagnosis: **config today is a thin launcher.** It answers *what* and *how often*; every
*when-to-actually-fire* (G1–G3), *what-to-run-across* (G4), *how-to-name-and-route* (G5), and
*did-it-work* (G8) decision has leaked into imperative code.

---

## 6. Recommendations

Config snippets are illustrative proposals, not existing syntax. Ranked by value-to-effort.

### P0-1: Declarative triggers and guards (G1, G2, G3)

Add an optional trigger/guard block evaluated by the runner *before* dispatch, using context it
already builds (it already loads the ChangeSpec snapshot and owns `state_dir`):

```yaml
- name: sase_fix_just              # 158-line script → one agent chop
  agent: "#!sase/fix_just"
  run_every: 60m
  inhibit_if:
    changespec: { name_prefix: "sase_fix_just_", status: [WIP, Draft, Ready, Mailed] }

- name: sase_refresh_docs          # marker/threshold dance moves out of the xprompt
  agent: "#!sase/refresh_docs"
  run_every: 3h
  trigger:
    provider: git.commits_since
    project: sase
    threshold: 100
    checkpoint: on_action_accepted   # or on_observation / on_action_success

- name: gh_actions_fix             # the seen-file becomes a declared dedupe key
  once_per: "{gh.run_id}:{gh.attempt}"
```

The core contract should include: a typed trigger result (`action` / `no_op` / `check_error`), a
stable event/dedupe key with optional evidence-file references, runner-owned checkpoint storage
scoped by chop and target, and explicit checkpoint timing. Core ships generic triggers (`always`,
`script_probe`, `changespec_query`, plausibly `git.commits_since`); **provider triggers stay
plugin-owned** (`github.actions.failed` in `sase-github`, Telegram events in `sase-telegram`). The
`script_probe` escape hatch uses argv + timeout + a JSON result-file protocol — *not* a
shell-interpreted YAML string (see the retired `gate:` history in §1). Guard/trigger skips must be
recorded on the run entry (`status: skipped, reason: …`) so "why didn't this fire?" is answerable —
the subsystem's biggest current UX weakness is silent no-ops.

### P0-2: End-to-end action lifecycle and structured outcomes (G8)

Make launchable chops have phases rather than terminal `agent_launched`:

```text
probing → no_op | check_error
        → action_queued → action_running → action_succeeded | action_failed
```

Link launched agents/workflows back to the chop run through the existing agent-completion artifacts
(the runner already stamps `SASE_CHOP_*` env into launched agents) rather than inventing a second
completion channel. For scripts, add `SASE_CHOP_RESULT_FILE`: new scripts atomically write a
versioned result document (counters, reason, evidence paths); existing exit-code semantics keep
working. `gh_actions_fix` and the xprompt workflows already emit exactly these fields as text.

### P0-3: Keyed concurrency, inhibition, and real resource caps (G9)

```yaml
concurrency:
  key: "refresh_docs:{project}"
  max_running: 1
  scope: global                # chop | lumberjack | target | global
  hold_until: action_terminal  # process_live | agent_terminal | changespec_terminal
```

This generalizes live-run dedupe into the three lifetimes Bryan's chops actually need (event,
work-product, watermark), scopes the `gh_actions_fix` guard per-repo instead of globally, and — since
the eight direct agent chops currently bypass `max_agent_runners` entirely — applies a real
global/per-lumberjack cap to configured script and direct-agent actions.

### P0-4: Fail-closed validation and env parity (G6, G7)

- Invalid `run_every`/`timeout`/`chop_timeout` must not silently become `None` (the dangerous case:
  an intended `run_every: 1d` or `60min` silently becomes *every tick*). `interval` must be a
  positive integer. Unknown keys, duplicate chop identities, and `agent`+`xprompt` conflicts should
  error with a config path and provenance.
- Make agent chops honor `env:` — or reject it — instead of silently dropping it; warn on
  script-only fields (`timeout`) on agent chops.
- Extend doctor to resolve `#!` workflow references, typecheck xprompt inputs, and verify VCS refs.
- Enrich duration parsing (days, compound `1h30m`).

### P1-5: Matrix fan-out, typed workflow actions, auto-injected scaffold (G4, G5)

Keep `agent: <raw prompt>` as the universal escape hatch; add a structured form that normalizes to
the same launcher path (preserving runtime uniformity):

```yaml
- name: refresh_docs
  repo: "{target.gh_ref}"           # feeds #gh; group=chop and %n auto-derived from name
  action:
    workflow: sase/refresh_docs
    inputs: { project: "{target.project}", gh_ref: "{target.gh_ref}", threshold: "{target.threshold}" }
  targets:
    - { project: sase,          gh_ref: sase-org/sase,          threshold: 100, every: 3h }
    - { project: sase-core,     gh_ref: sase-org/sase-core,     threshold: 25,  every: 24h }
    - { project: sase-github,   gh_ref: sase-org/sase-github,   threshold: 25,  every: 24h }
    - { project: sase-nvim,     gh_ref: sase-org/sase-nvim,     threshold: 25,  every: 24h }
    - { project: sase-telegram, gh_ref: sase-org/sase-telegram, threshold: 25,  every: 24h }
```

Expansion must produce stable target-specific chop IDs and state (e.g. `refresh_docs[sase-core]`) so
dedupe, timestamps, and run history stay per-instance. The same construct replaces
`SASE_GHA_FIX_REPOS`. Benefits: validation, provenance, one source of truth, no quoting, and the
launched-agent name/group boilerplate disappears (the runner already knows it is launching a chop).

### P1-6: Keyed composition, activation, and secret references (G10, G6)

Accept a map form (`chops: {tg_inbound: {enabled: true, …}}`) normalized from the legacy list, so
overlays can patch one field, soft-disable (`enabled: false`), or override without duplicating whole
entries; report per-field provenance. Add lumberjack-level `env:` (de-dupes the Telegram creds) and
secret *references* (env-var name / provider source — the Telegram doctor's env → file → `pass`
discovery is the precedent) rather than plaintext values. Core should not become a secret vault.

### P1-7: Explicit cadence anchors, retry, and backoff (G12)

Replace the implicit failure asymmetry (§3.4) with visible policy: cadence anchored on attempt /
successful probe / accepted action / completed action; `retry: {on: [check_error, launch_error],
delays: [1m, 5m, 15m]}`; persisted `next_eligible_at` so restarts don't erase backoff; deterministic
jitter. The typed trigger result makes retry classification tractable (a healthy `no_op` is not a
failure). Avoid sleep-based retries that hold a whole tick.

### P2-8: Scheduling and runtime management

`cron` + IANA timezone (a global timezone already exists to default from), one-shot `at`/`in`,
catch-up policy (`skip`/`once`/bounded replay), quiet windows; validated hot reload
(`sase axe reload`) and per-chop pause/resume — but only after keyed identity and validation exist.
None of Bryan's current chops is blocked by these; they follow the trigger/lifecycle work.

### P2-9: Per-chop observability and retention

Bounded-cardinality per-chop metrics (probe outcomes, launches, terminal outcomes, durations,
retries, skipped-by-concurrency, last-success timestamp — keyed by lumberjack/chop, not event ID),
configurable run-history retention (hard-coded at 10 today), and a `sase axe chop runs` CLI/JSON
query surface.

### P2-10: Internal DX — builtin registry and shared state helpers (G11)

A `@chop("hook_checks", scope="filtered")` decorator/registry collapses the 9-way clone and the
5-edit-site process (fold in the `--context` preamble, the `log` closure, and a shared
`emit_chop_summary(...)` for the `key=value … reason=` convention). Longer term, a single
"PID-lease + high-water-mark" abstraction owned by the runner replaces the six dedupe stores and the
~4 dead-PID reclamation implementations — and is what P0-1's `once_per` and checkpoints build on.
Retire the `cl_submitted_checks` alias; wire or drop `pushgateway_cleanup`.

---

## 7. What should stay outside chop config

- **Multi-step workflow logic.** Xprompt workflows already provide typed inputs, conditionals,
  steps, fan-out, waits, and cleanup. AXE should reference and supervise them, not duplicate the
  workflow language in YAML — `pylimit_split`'s per-file fan-out and `refresh_docs`' update+polish
  sequencing stay in workflows.
- **Provider business logic.** GitHub conclusion classification and log retrieval belong in
  `sase-github`; Telegram transport in `sase-telegram`. Core owns the generic trigger/action/
  checkpoint contract and extension interfaces.
- **Arbitrary shell gates.** Already tried and deliberately removed; opaque, unvalidatable, and
  workspace-fragile. Typed triggers or the `script_probe` result-file protocol cover the need.
- **A catalog of opinionated built-in jobs.** Bryan's chops are *policy* (audit at 200 commits,
  refresh these five repos, these ChangeSpec naming conventions). SASE should make policy concise
  and safe to express, not hard-code it.
- **Genuinely imperative residue.** `gh_actions_fix`'s live-state harvesting — poll `gh`, fetch and
  truncate failed logs, seed them into the launch prompt — is real code. A later refinement is a
  thin *producer* script emitting structured events consumed by a declarative agent-chop template.

---

## 8. Implementation notes

- **Rust core boundary.** Trigger/guard evaluation, fan-out expansion, checkpoint/dedupe
  bookkeeping, and the result wire types (`ChopProbeResult`, `ChopActionResult`) are backend/domain
  behavior any frontend would need to match — they belong in `../sase-core` (`sase_core_rs`) with
  thin Python adapters here. TUI rendering of skipped/guarded runs stays in this repo.
- **Backward compatibility.** All proposed fields are additive and optional; raw scripts and raw
  `agent:` prompts remain fully supported escape hatches.
- **Migration order.** Phase 0: fail-closed parsing, duplicate/applicability validation, doctor
  workflow-ref checks, and *documenting* today's surprises (agent-chop `env`/`timeout`, uncapped
  direct agent chops) with regression tests. Phase 1: result/checkpoint protocol — migrate
  `gh_actions_fix` first; its bash tests (event classification, dedupe, log fallback, guards,
  prompt assembly, summaries) are the richest acceptance suite. Phase 2: trigger/action +
  lifecycle linkage + keyed concurrency — collapse `sase_fix_just` to an inhibition rule. Phase 3:
  typed actions, target matrices, keyed maps/`enabled` — collapse the five docs rows. Phase 4:
  retry/backoff, cron/one-shots, retention, hot reload, per-chop metrics.
- **Acceptance criteria** (a redesign is materially better only if it expresses all of these):
  Telegram polling with credential-source diagnostics; hourly pylimit checks without allocating an
  agent workspace on no-op; `fix_just` inhibition lasting beyond the launcher process; threshold
  audits with marker recovery and configurable checkpoint phase; one docs policy across five typed
  targets with two cadences; per-repo GHA detection with bounded evidence, restart-safe dedupe, and
  per-repo (not global) inhibition; no-op vs. degraded vs. launched vs. final status visible in
  history; the eight agent chops under an explicit resource policy; manual runs, live output,
  timeout kill, and bounded history preserved.

---

## 9. Latent bugs and quick fixes (independent of any redesign)

1. `env:` on agent chops is silently dropped (`chop_runner_agent.py:99-109` builds only the
   `SASE_CHOP_*` metadata env) — honor or reject it.
2. `timeout:` is parsed for agent chops but never applied; agent chops have no liveness policy.
3. Invalid duration strings (`60min`, `1d`) and typo'd keys (`run-every`) silently degrade —
   an intended hourly chop becomes an every-tick chop.
4. `pushgateway_cleanup` is a config-orphan builtin; `cl_submitted_checks` survives only via a
   legacy alias entry point.
5. The one-shot context path does not copy `verbose_lumberjack_diagnostics`.
6. `%auto` appears only on `sase_pylimit_split`, not the other agent chops (nor the fix_just
   script's prompt) — likely an unintended inconsistency in the chezmoi config.
7. `description` is documented as required but parsed as optional.

---

## 10. Bottom line

Lumberjacks do not need to become a second workflow engine. Their strengths — supervision, periodic
polling, context delivery, history, dedupe, operator visibility — are real and recent. What Bryan's
custom chops demonstrate is the missing middle between "tick" and "run this prompt": typed triggers
with runner-owned state, lifecycle-aware outcomes, keyed concurrency, validated and composable
actions. Build that middle in core (behind the Rust boundary), let xprompts own multi-step work and
plugins own provider details, and the current collection of capable but bespoke wrappers collapses
into concise, inspectable configuration — without losing the raw-script and raw-prompt escape
hatches that made those wrappers possible.

---

## Appendix — source map

Paths relative to the SASE primary repo unless prefixed `chezmoi:`.

**Engine & config:** `src/sase/axe/config.py` (models, `_parse_duration`);
`src/sase/config/sase.schema.json:365-494`; `src/sase/config/core.py` (merge order);
`src/sase/default_config.yml:248-298`; `src/sase/axe/lumberjack.py` (tick, eligibility, concurrency);
`orchestrator.py`, `lock.py`, `maintenance.py`, `runner_pool.py`.
**Dispatch & state:** `chop_runner.py`, `chop_runner_types.py`, `chop_runner_agent.py`,
`chop_runner_script.py`, `chop_script_runner.py`, `chop_script_context.py`, `chop_runner_context.py`,
`chop_agents.py`, `_state_chops.py`, `_state_lumberjack.py`, `_state_scheduler.py`.
**Inventory/UX & docs:** `chop_inventory.py`, `chop_doctor.py`, `chop_render.py`, `docs/axe.md`,
`docs/configuration.md`.
**Builtin chops:** `src/sase/scripts/sase_chop_*.py`, `src/sase/scripts/__init__.py`,
`pyproject.toml:102-115`; business logic in `src/sase/axe/hook_jobs.py`, `check_cycles.py`,
`src/sase/ace/scheduler/`.
**Chezmoi:** `home/dot_config/sase/sase.yml:96-110` (telegram),
`home/dot_config/sase/sase_athena.yml:66-129` (custom chops),
`home/bin/executable_sase_chop_sase_fix_just`, `home/bin/executable_sase_chop_gh_actions_fix`,
`tests/bash/{sase_fix_just,gh_actions_fix}_chop_test.sh`.
**Referenced xprompts (sase repo):**
`xprompts/{pylimit_split,fix_just,audit_recent_bugs,audit_recent_improvements,refresh_docs}.yml`.
**History:** chezmoi `919ba759` (shell `gate:` added) → chezmoi `edf0f1c4` / sase `0d1f4909e`
(removed); chezmoi `1eda9cd9` (`sase_fix_just` ChangeSpec guard).
**Prior research:** `202603/lumberjack_vs_openclaw.md` (partly obsolete),
`202603/refresh_docs_workflow.md`, `202604/email_reading_chop.md`,
`202605/preferred_plugins_chops_install_strategy.md`, `202605/sase_chops_rust_repo_research.md`,
`202605/dream_chop_agent_chat_distillation.md`.
