# Cross-Machine Audit of SASE Notifications and Error/Warning Logs (`apollo` vs. `athena`)

**Audit Date:** 2026-11-19 (`10:05 UTC`)
**Machines Audited:**
- **`apollo`** (local host, UTC clock, `sase 0.19.0+196.g065eda332`, `sase-core-rs 0.44.2+43.g6f8f016e8`, Python `3.12.3`)
- **`athena`** (remote host over SSH, EST `-05:00` clock, `sase 0.19.0+196.g065eda332`, `sase-core-rs 0.44.2+43.g6f8f016e8`, Python `3.14.7`; additionally runs `sase-spotify 0.1.1+untagged.g2221a35d9` and `telegram_receiver`)

**Sources Inspected:** Both hosts' `~/.sase/notifications/` (`notifications.jsonl`, `notifications-archive.jsonl`), `~/.sase/interaction_requests/`, `~/.sase/axe/` (`recent_errors.json`, `error_digests/`, `logs/`, `lumberjacks/*/logs/`), `~/.sase/logs/` (`tui.log`, `tui_stalls.jsonl*`, `tui_agent_loads.jsonl*`, `tui_git_ops.jsonl*`, `tui_faults.log`, `workspace_claims.jsonl*`, `launch_failures.jsonl`, `install_logs`, `update_logs`), `~/.sase/service/procs/*/output.log` (including `gateway/output.log`, `scheduler/output.log`, `telegram_receiver/output.log`), `~/.sase/bead_push_logs/`, `~/.sase/procs/logs/`, `journalctl --user -u sase.service`, `sase doctor`, `sase disk` (`apollo`), and source code in `sase` and `sase-core`.

---

## Executive Summary

Both `apollo` and `athena` run identical `sase` and `sase-core-rs` versions and exhibit severe, self-reinforcing operational friction across four core subsystems—plus distinct machine-specific failure modes:

1. **Disk-Pressure Accounting Blindness Caused an Actual `apollo` Outage (Nov 16–17):** Every one of `apollo`'s `119` `disk_pressure` notifications reported `171.9–192.7 GiB` "Unattributed" because `InventoryScanBudget(max_nodes=50_000, max_seconds=5.0)` in `src/sase/core/disk_footprint_utils.py` is shared globally across sequential `du -skx` subprocesses. When free space collapsed to `1.8 MiB` (`0.0%`) on `2026-11-17T02:04–02:06 UTC`, `managed_tmp_reaper` reported `Reap blocked/incomplete owners: managed_tmp_reaper` and `sase.service` suffered widespread `OSError: [Errno 28] No space left on device` routine crash loops.
2. **Severe TUI Memory Growth, Swap-Amplified GC Pauses, and Synchronous Main-Thread Stalls:** Live `sase tui` on `athena` was measured at `2.52 GB` RSS (`7.88 GB` VSZ), peaked at **`6,195,879,936` bytes (`6.20 GB`)** in `tui_stalls.jsonl`, and hit GC pauses of **`73.02s`** (with `128,608` `major_faults_delta`) in `tui_stalls.jsonl` and **`324.22s` (5.4 min)** in `tui_stalls.jsonl.1`. `apollo` peaked at **`3,875,663,872` bytes (`3.88 GB`)** with a **`37.94s`** GC pause and **`116.77s`** hitch recovery on key `'E'`. Both UIs also hit live Textual `NoMatches` exceptions and dozens of 30s `kill-and-edit` cleanup barrier timeouts.
3. **Unbackedoff `agent_publication` Retry Storms Dominate `axe` Digests:** `agent_publication` accounts for `62/100` entries in `apollo`'s `recent_errors.json` (`16` separate `100 error(s) in the last hour` bursts in 7 days) and `44/100` on `athena` (`5,956` `agent_publication` entries across Nov 2026 digests). Persistent misconfigurations and protection-withheld items (`gh_sase-org__sase-spotify` missing remote, `gh_bbugyi200__nut` missing target, `gh_bobs-org__bob-cli` protection-withheld) still increment `summary.errors` every scheduler tick without per-`(project, signature)` backoff, leaving **`1,546`** (`apollo`) and **`5,202`** (`athena`) `state.agent_publication_outbox` issues in `sase doctor`.
4. **Notification Amplification, UUID-Based Dedup Failures, and Orphaned Gates:** Both hosts carry exactly `420` unread, undismissed, non-silent active notifications alongside **`314`** (`apollo`) and **`522`** (`athena`) broken file references, multi-hundred-KB embedded prompts/notes, **`2,501`** (`apollo`) and **`5,029`** (`athena`) pending `interaction_requests/` directories (mostly orphaned `task_triage`), per-waiter `wait_checks` cascade storms (`94` in 7d on `athena`, `31` on `apollo`), and a `remote-attention` dedup key bug making `remote-attention` `#1` non-local sender in 7d on `athena` (`308` notifications).
5. **Gateway WAL Bug & Slow Fleet Snapshots, Systemd/Upgrade Races, SDD Worktree Drift, and Ledger/Temp Clutter:** `sase_gateway` logs SQLite WAL checkpoint integer-conversion failures (`u64::try_from(-1)`) and multi-minute fleet snapshot stalls (`158.3s` on Nov 18, `1,796.3s` on Nov 14, producing `504 Gateway Timeout`s); live `uv tool` upgrades trigger `SIGBUS` (`exit code -7`) and `ImportError`s in running chops; `workspace_claims.jsonl` logs thousands of `"already pinned (no-op)"` error rows per night; and tens of thousands of `.log.lock` / `.agent_name_registry.json.*.tmp` clutter `~/.sase/`.

---

## Cross-Machine Baseline Metrics

| Dimension | `apollo` | `athena` |
|---|---:|---:|
| Filesystem capacity / free (`/` or `SASE_HOME`) | `193G` total, `167G` used (`87%`), `26G` avail | `875G` total, `582G` used (`68%`), `284G` avail |
| `~/.sase` footprint (major dirs) | `~24G` (`projects` `13G`, `cache` `5.9G`) | Larger host SSD; systemd peak `12.3–16.3 GB` RSS |
| `notifications.jsonl` rows / size | `1,777` rows / `5,109,549 B` (`5.11 MB`) | `2,624` rows / `7,347,581 B` (`7.35 MB`) |
| `notifications-archive.jsonl` rows / size | `6,386` rows / `41,210,538 B` (`41.21 MB`) | `23,551` rows / `108,871,123 B` (`108.87 MB`) |
| Active unread + undismissed + non-silent | `420` | `420` |
| Broken `files` paths in active `notifications.jsonl` | `314` | `522` |
| Pending `interaction_requests/` dirs (total dirs) | `2,501` (`3,397` total) | `5,029` (`8,947` total) |
| `axe/error_digests/` count / size | `436` files / `23,563,779 B` (`23.56 MB`) | `726` files / `14,530,315 B` (`14.53 MB`) |
| `axe/error_digests/` in Nov 2026 | `220` digests | `171` digests |
| `tui_stalls.jsonl` peak RSS (`tui_memory_heartbeat`) | `3,875,663,872 B` (`3.88 GB`) | `6,195,879,936 B` (`6.20 GB`) |
| `tui_stalls.jsonl` max `tui_gc_pause` (`tui_stalls.jsonl.1`) | `37.94s` (`8.26s` in `.1`) | `73.02s` (`324.22s` in `.1`) |
| `procs/logs/.*.log.lock` count (vs other files) | `6,716` locks (`40` other) | `13,570` locks (`585` other) |
| Orphaned `.agent_name_registry.json.*.tmp` | `3` files (`22,869,916 B` / `22.9 MB`) | `9` files (`85,646,457 B` / `85.6 MB`) |

> **Important methodological note:** `tui.log` does not rotate cleanly by age, so some high all-time counters represent **already-fixed historical incidents** (documented explicitly in [Part 3](#part-3-historical--resolved-log-artifacts)). All high-priority findings below are verified against the last 7 days (`2026-11-12`..`2026-11-19`) and current code.

---

## Part 1: SASE Notifications Audit

### 1.1 Sender & Action Volume Breakdown

**Top Notification Senders (All-Time / 30d / 7d / 48h):**

| Sender | `apollo` Total (7d / 48h) | `athena` Total (7d / 48h) | Notes / Primary Action |
|---|---:|---:|---|
| `user-agent` | `3,970` (`545` / `133`) | `13,408` (`510` / `172`) | `JumpToAgent` (`545` 7d `apollo`; `481` 7d `athena`) |
| `bead` | `2,487` (`298` / `100`) | `5,099` (`306` / `109`) | Mostly `TaskTriage` (`288` 7d `apollo`; `294` 7d `athena`) |
| `remote-attention` | `0` (`0` / `0`) | `1,615` (**`308`** / `109`) | `athena` `#2` sender overall in 7d, `#1` non-`user-agent` |
| `axe` | `478` (`64` / `23`) | `792` (`65` / `22`) | Hourly error digests (`ViewErrorReport`) |
| `wait_checks` | `102` (`31` / `6`) | `501` (`94` / `14`) | Terminal blocked dependency cascades (`83` 7d `athena`, `18` `apollo`) |
| `plan` | `160` (`36` / `12`) | `1,648` (`45` / `22`) | `PlanApproval` |
| `workspace-rescue` | `161` (`27` / `7`) | `184` (`33` / `12`) | `Workspace held: stranded work` (`33` 7d `athena`, `5` `apollo` stranded) |
| `epic-launch` | `115` (`25` / `6`) | `692` (`47` / `18`) | Epic launch confirmations / completions |
| `epic` | `90` (`22` / `5`) | `632` (`24` / `8`) | `EpicApproval` |
| `file-hooks` | `284` (`47` / `10`) | `302` (`15` / `6`) | File-hook notifications (`586` combined across both hosts) |
| `disk_pressure` | `119` (**`18`** / `0`) | `0` (`0` / `0`) | `apollo`-only unattributed disk exhaustion alerts |
| `sudo` | `21` (`12` / `12`) | `71` (`9` / `4`) | `SudoRequest` gates |
| `question` | `24` (`12` / `2`) | `76` (`7` / `2`) | `UserQuestion` gates |
| `instructions` | `14` (`8` / `2`) | `14` (`7` / `2`) | Daily Codex `oversize` delivery fallbacks |

### 1.2 `remote-attention` Broken Deduplication (`athena`)

On `athena`, `remote-attention` accounts for `308` notifications in the last 7 days (`109` in 48h, `28` in 24h, `1,615` all-time). Instead of collapsing updates to a single notification per remote gate/attention item, repeated re-emissions flood the inbox:

- **Root cause (`src/sase/dispatch/attention_inbox.py:555-561`):**
  ```python
  def _dedup_key(
      *,
      origin_installation_id: str,
      request_id: str,
      revision: str,
  ) -> str:
      return f"remote-attention:{origin_installation_id}:{request_id}:{revision}"
  ```
- **Observed failure mechanics:**
  1. `request_id` carries the remote *notification UUID* rather than a stable gate or bead identifier, so whenever the remote host recreates a notification or emits a related attention record, a brand-new `remote-attention` row is created locally.
  2. Including `:{revision}` inside `dedup_key` ensures every edit or `+1` hash change generates a **new unread row** rather than updating the existing row in place.
  3. Worse, `athena`'s store contains multiple duplicate `remote-attention` pairs with **identical `revision` hashes**: e.g., `bob-cli-ki` generated **23** `remote-attention` notifications within 7 days (including multiple pairs sharing identical revisions `6739461665619980938`, `9269403913340446553`, and `7649370080100180250`), and `sase-1tm` immediately created a fresh unread row (`9b3900bd`) right after `3fb61705` was dismissed with the exact same `revision=17322918467837617308`.

### 1.3 `wait_checks` Per-Waiter Terminal-Block Amplification

When an upstream phase bead or prerequisite fails fatally, every blocked downstream phase bead receives its own `Wait dependency can never self-resolve` notification—and continues receiving `+1` updates up to the `500`-entry `plus_ones` cap:

- **Observed counts:** `83` terminal-blocked notifications in 7 days on `athena` (`10` in 48h) and `18` in 7 days on `apollo` (`2` in 48h). In an epic like `bob-cli-na` or `bob-cli-nb`, separate unread alerts fire for `.2`, `.3`, ..., `.8`, `.land` even when all are blocked by the **same single failed blocker**.
- **Root cause (`src/sase/scripts/_chop_wait_checks_terminal.py:183-190`):** `upsert_terminal_blocked_wait_notification` computes `dedup_key=f"wait_checks:terminal-blocked:{waiter_dir}"` (keyed by *waiter* rather than *blocker/epic*), and appends `plus_one_note=f"Still blocked on {blocker.dependency}: {blocker.artifact_dir} ({blocker.outcome})"` on every subsequent `wait_checks` pass.

### 1.4 Single-Row Bloat, Broken `files` References, and Archive Growth

Active and archived notification JSONL files carry heavy inline text blobs and dead file pointers:

- **File Sizes & Broken References:**
  - `apollo`: active `notifications.jsonl` is `5.11 MB` (`1,777` lines) with `314` broken `files` paths; `notifications-archive.jsonl` is `41.21 MB` (`6,386` lines, spanning `2026-09-01`..`2026-11-16`, `5,887` of which were archived unread).
  - `athena`: active `notifications.jsonl` is `7.35 MB` (`2,624` lines) with `522` broken `files` paths; `notifications-archive.jsonl` is **`108.87 MB`** (`23,551` lines, spanning `2026-07-06`..`2026-11-16`, `12,663` unread).
- **Inline Bloat Hotspots in Active `notifications.jsonl`:**
  - `action_data` alone consumes **`3.05 MB`** on `apollo` and **`3.38 MB`** on `athena` (over half the active store). Sample offenders on `apollo`: notification `21e5a6e2...` (Nov 17) embeds a **`171,826`-byte** raw continuation prompt in `action_data['prompt']`, and `43f4df42...` embeds **`217,876` bytes** of raw error output inside `notes`.
  - `plus_ones` consumes **`2.13 MB`** across active `notifications.jsonl` on `athena` (`wait_checks` rows alone account for **`1.63 MB`**); individual rows pinned at the `500` `plus_ones` cap grow to **`66–69 KB`** per notification line, slowing every synchronous JSONL rewrite and TUI parse.

### 1.5 Massive Orphaned `interaction_requests/` Backlog

Pending interaction-gate directories accumulate far faster than they are resolved or pruned:

| Kind | `apollo` Pending / Total | `athena` Pending / Total | Notes |
|---|---:|---:|---|
| `task_triage` | **`2,393` / `2,393`** | **`4,801` / `5,018`** | `1,922` (`apollo`) & `4,324` (`athena`) absent/archived; `66` & `72` dismissed |
| `bead_stale_cleanup` | `68` / `68` | `82` / `84` | Nearly 100% unresolved pending dirs |
| `bead_snooze` | `21` / `27` | `45` / `46` | Accumulating uncleaned dirs |
| `custom` | `5` / `12` | `27` / `85` | — |
| `plan` | `10` / `570` | `32` / `2,403` | `+1` malformed on `athena` |
| `epic_plan` | `1` / `267` | `11` / `1,057` | — |
| `question` | `3` / `29` | `13` / `120` | — |
| `sudo` | `0` / `21` | `13` / `70` | — |
| `launch` | `0` / `1` | `5` / `55` | — |
| `.locks` | `0` / `9` (`9` malformed) | `0` / `9` (`9` malformed) | Empty lock/sentinel files counted under dir scan |
| **Total** | **`2,501` / `3,397`** | **`5,029` / `8,947`** | Majority of pending dirs correspond to dead/archived notifications |

Whenever a user dismisses or archives a `TaskTriage` notification in the TUI—or resolves the bead directly via `sase bead`—the underlying `interaction_requests/task_triage/*` request directory is left pending indefinitely.

### 1.6 Daily Codex `oversize` Instruction Fallback

- **Observed counts:** `8` `instructions` fallback notifications in 7 days on `apollo` and `7` in 7 days on `athena` (once per UTC day due to `notify_instruction_fallback` deduplicating per host/provider/reason/UTC-day in `src/sase/llm_provider/instruction_delivery.py`).
- **Root cause:** `src/sase/llm_provider/codex.py:213` fixes `max_bytes: 32 * 1024` (`32,768` bytes) for `CHANNEL_CODEX_ROOT = "codex.developer_instructions"`, and `src/sase/llm_provider/_instruction_boundary.py:406-408` triggers `active.report_fallback("root", "oversize")` whenever UTF-8 byte length exceeds `max_bytes`. Compiling project bundles via `compile_bundle` showed:
  - `bob-cli`: **`36,186` bytes** (`+3,418` bytes over limit -> triggers fallback on *every* `bob-cli` Codex invocation)
  - `sase`: `22,105` bytes (under limit)
  - `tailnet`: `7,876` bytes (under limit)

### 1.7 `disk_pressure` Notifications & The `apollo` Nov 16–17 Disk-Full Outage

- **Observed notifications:** `apollo` emitted `119` `disk_pressure` notifications all-time (`39` in 30d, `18` in 7d, `0` in 48h after manual disk recovery reduced used space to `87%`). Every notification stated: `Unattributed <171.9–192.7> GiB on the SASE_HOME filesystem falls outside every inventoried owner`.
- **Root cause (`src/sase/core/disk_footprint_utils.py:14-18, 131-137`):**
  ```python
  class InventoryScanBudget:
      """One budget shared by a whole disk-inventory collection pass."""
      max_nodes: int = 50_000
      max_seconds: float = 5.0
  ```
  `size()` checks `if budget.exhausted:` and immediately aborts with `budget.record_diagnostic(f"{path}: skipped; shared scan budget exhausted")` and returns `0`. Running `sase disk` live on `apollo` reproduced the failure: only **`1,826,816` bytes (`1.8 MiB`)** was attributed while **`179,093,680,128` bytes (`166.8 GiB`)** fell into `unattributed` because large repository checkouts, `sase-core/target/uv-tool-*`, `.cache/sase/tmp/cargo-targets/*`, and `managed_tmp` directories all exhausted the single shared 5s / 50k-node budget.
- **Operational cascade (`2026-11-16T19:34-05:00`..`2026-11-17T02:06Z`):** Because inventory failed, three consecutive `disk_pressure` notifications reported `Reap blocked/incomplete owners: managed_tmp_reaper` as free space fell `7.4 GiB -> 443.7 MiB -> 1.8 MiB (0.0%)`. At `Nov 17 02:04:56–02:06:03 UTC`, `journalctl --user -u sase.service`, `scheduler/output.log`, `axe.log`, `lumberjack-telegram.log`, and `lumberjack-sidecar_sync.log` all recorded `OSError: [Errno 28] No space left on device` during `sase service host reconcile error`, `pump_service_output` (`append_bounded_log`), routine crash loops (`telegram`, `checks`, `hooks`, `agent_waits`, `sidecar_sync`, `waits`, `usage`, `comments`), and `Failed to notify about crash loop ... No space left on device`.

---

## Part 2: Error & Warning Logs Audit

### 2.1 `axe` `recent_errors.json` & `error_digests/` Storms

**`recent_errors.json` Breakdown (last 100 recorded job errors per machine):**

| Job Name | `apollo` (`2026-11-17 07:20`..`11-19 01:24 -05:00`) | `athena` (`2026-11-14 17:35`..`11-18 20:57 -05:00`) | Primary Failure Modes |
|---|---:|---:|---|
| `agent_publication` | **`62`** | **`44`** | Retried every tick with no per-project backoff |
| `workspace_sdd_clone_recovery` | `7` | **`25`** | Invalid worktrees, detached HEAD, `0.1s` conflict timeouts |
| `artifact_retention` | `2` | **`19`** | `failed` / `timed out after 300s` |
| `artifact_link_backfill` | `6` | `1` | `300s` timeouts (`15x` in `athena` Nov digests) |
| `sidecar_auto_sync` | `5` | `1` | `120s` timeouts / `SIGBUS` during upgrade |
| `stale_running_cleanup` | `4` | `1` | `90s` timeouts |
| `tg_outbound` | — | `4` | Missing `sase_job_tg_outbound` binary |
| `agent_auto_restart` | — | `2` | Missing/renamed job script & `exit code -7` (`SIGBUS`) |
| `artifact_run_prune` | `1` | `2` | `300s` timeouts (`3x` in `athena` Nov digests) |
| `pending_checks_poll` | `2` | — | Including `exit code -7` (`SIGBUS` during upgrade) |
| Other `90s–120s` chop timeouts (`wait_checks`, `gate_turn_reclaim`, `footprint_fold`, `usage_refresh`, etc.) | `11` (`1` each across 11 chops) | `1` (`wait_checks` `ModuleNotFoundError`) | Simultaneous load spikes (`18` errors in single `apollo` digest `20261118_170232`) |

**Digest Error Amplifiers (Last 14 Days / Nov 2026):**
- **`apollo`:** `16` separate `100 error(s) in the last hour` burst notifications in 7 days (`3` in 48h). Top 14d digest lines:
  - `gh_bbugyi200__nut: no usable agents publication target`: **`1,795`** occurrences (failing ~every 17s; e.g., `digest_20261117_053307.txt` capped at `100/100`).
  - `gh_sase-org__sase: git pull --rebase failed: Rebasing (1/1)` (**`1,466`**) & `gh_bobs-org__bob-cli: git pull --rebase failed: Rebasing (1/1)` (**`1,436`**) from a stuck rebase state (subsequently cleared).
  - Latest Nov 18–19 digests (`digest_20261118_191904.txt`, `digest_20261119_013903.txt`): `gh_bobs-org__bob-cli: agent-hood publication did not complete within 120s; publication cleanup also failed: publication cleanup did not complete within 1s` and `parked 1 publication request: bbugyi200.apollo.bob-cli-eb.6@a3735b914939: prompt archive withheld by publication protection`.
  - `lumberjack-publication.log` tail shows `3,004` runs ending `errors=1` vs only `1,727` ending `errors=0`.
- **`athena`:** `54` digest notifications in 7 days (`39` `1 error(s)`, `8` `2 error(s)`, `7` `3 error(s)`). Across `171` Nov 2026 digests, there are **`5,956`** `agent_publication` error entries:
  - `gh_bobs-org__bob-cli: run withheld by publication protection`: `3,795` + `1,215` = **`5,010`** occurrences.
  - `gh_sase-org__sase-spotify: could not clone configured agents sidecar ... ERROR: Repository not found.`: **`835`** occurrences.
  - `gh_bobs-org__bob-cli: git pull --rebase failed: Permission denied (publickey)`: `57` occurrences.
  - Latest digest (`digest_20261118_211912.txt`): `could not restore deferred prompt archive for bbugyi200.athena.<agent>@<hex>: prompt archive is unresolved and a missing local source does not prove there was no prompt obligation` (repeated 3x for `1e6@50c90e3f2f54`).

- **Why Storms Persist (`src/sase/agents_sync/publication_job.py:135-140, 186-191, 223-225` & `sase doctor`):**
  Every `missing_active` target and every per-project `result.error` increments `summary.errors += 1` (`check_error` despite `Exit Code: 0`) unconditionally on every cycle with zero per-`(project, error_signature)` exponential backoff or error-state deduplication. Over time, `sase doctor` accumulated:
  - `state.agent_publication_outbox`: **`1,546` issues on `apollo`** (`802` quarantined, `311` retired, `3` parked, `430` stale requested revisions) and **`5,202` issues on `athena`** (`3,856` quarantined, `13` retired, `1,333` stale requested revisions).
  - `state.agent_publication_protection`: **`29` issues on `apollo`** (`8` enforced blocked, `11` stale awaiting revalidation, `5` unverified, `5` superseded) and **`74` issues on `athena`** (`6` enforced blocked, `52` stale awaiting revalidation, `16` superseded).

### 2.2 TUI Memory Leaks, Swap Thrashing, Multi-Minute GC Pauses, & Live UI Crashes

Both hosts experience debilitating TUI latency caused by unthrottled heap growth, synchronous main-thread I/O / Python work, and stop-the-world Gen-2 GC sweeps hitting swapped pages:

| Metric (`tui_stalls.jsonl*` + `tui.log` + `ps`) | `apollo` | `athena` |
|---|---:|---:|
| Live `sase tui` memory (`ps`) | — (intermittent sessions) | `2.52 GB` RSS / `7.88 GB` VSZ (`pid=3820644`) |
| Peak `tui_memory_heartbeat` RSS (`tui_stalls.jsonl`) | **`3,875,663,872 B`** (`3.88 GB`, `7,676,093` blocks) | **`6,195,879,936 B`** (`6.20 GB`, `16,589,943` blocks) |
| Early-session RSS bloat (`20–30 min` uptime) | — | `4.56–5.54 GB` RSS with `489 MB` swapped (`vmswap_bytes=489693184`) |
| `tui_gc_pause` count / p50 / p95 / p99 (`tui_stalls.jsonl`) | `4,153` (`365ms` / `1,500ms` / `2,123ms`; `64 >= 2s`, `1 >= 10s`) | `38,730` (`69ms` / `1,253ms` / `2,475ms`; `873 >= 2s`, `17 >= 10s`) |
| Max `tui_gc_pause` (`tui_stalls.jsonl` / `.1`) | **`37.94s`** (`0` collected) / `8.26s` (`5,903,459` collected) | **`73.02s`** (`5,787,488` objects, `128,608` major faults) / **`324.22s`** (`5.4 min`, `backstop`) |
| Worst interactive stall recoveries (`tui_hitch_recovered`) | **`116.77s`** (`'E'`), **`73.20s`** (`'enter'`) | **`74.12s`** (`52.07s` GC with `110,812` major faults while `input_age_s=8.49s`) |
| `tui.log` loop / pump stalls in last 7d | `45` loop stalls, `53` pump stalls | `527` event-loop stalls, `273` pump stalls |
| `tui_agent_load_slow` events (`tui_agent_loads.jsonl*`) | `6,798` (~51h) | `6,266` (~48h) |
| `kill-and-edit` 30s cleanup barrier timeouts (7d) | `9` (`5` `bob-cli`, `3` `tailnet`, `1` deferred kill `bob-cli`) | `22` (`13` `bob-cli`, `9` `sase`) |
| Malformed JSONL rows (`tui_stalls.jsonl`) | **`3`** malformed lines | `0` |

**Captured Main-Thread Stack Hotspots in `tui_stalls.jsonl` (`sample_stacks`):**
- `aggregate_clan_runtime` (`src/sase/core/agent_runtime_facade.py:22`): `334` sampled main-thread hits on `athena`
- `list_project_records` (`project_lifecycle_facade.py:65`) + `_project_record_has_spec` (`project_alias_records.py:82`): `185 + 68` hits on `athena`, `144` combined on `apollo`
- `_canonical_path` (`_hijack_roster_snapshot.py:236`): `109` hits on `athena`, `141` on `apollo`
- `_fingerprint_value` / `agent_share_fingerprint` (`_agent_graph.py:288, 306`): `71` hits on `athena`, `198` on `apollo`
- `compile_query_profile` (`query_profile/compiler.py:120`): `53` hits on `apollo`
- `_stat_token` (`current_project.py:328`): `42` hits on `athena`
- `_gc_callback` + `_gc_policy_policy.tick`: `169` hits on `apollo` (plus heavy hits on `athena`)

**Unhandled Live UI `NoMatches` Crashes (`tui.log`, Nov 16–17):**
- `athena`: `2` `Notification poll failed (source=watcher)` errors (`2026-11-16 10:54:28`, `2026-11-17 14:12:45`) from `src/sase/ace/tui/actions/agents/_notification_polling.py:438`: `self.query_one("#notification-indicator", NotificationIndicator)` raises `NoMatches` when the active screen is `Screen(id='_default')`.
- `apollo`: `1` `Unhandled exception in sase's TUI` (`2026-11-17 20:33:51`) from `src/sase/ace/tui/modals/gate_input_panel.py:167`: `self.query_one("#gate-input-footer", Static)` raises `NoMatches` on `GateInputPanel()`.

### 2.3 `sase.service` Memory Peak, Clean-Stop `SIGKILL`s, & Live Upgrade Races

- **Systemd Peak Memory & Forced `SIGKILL` Shutdowns (`journalctl --user -u sase.service`):**
  - On `athena`, `sase.service` hit peak memory of **`12.3–16.3 GB`** with **`1.1–1.2 GB`** swap (`sase_job_wait_checks` alone observed at **`951.7 MB` RSS** on `pid=52745`).
  - Across dozens of `sase.service` restarts (Nov 17–19), systemd repeatedly timed out and sent **`SIGKILL`** to child jobs (`sase_job_sideca`, `sase_job_agent_`, `sase_job_stale_`, `sase_job_bead_c`, `sase-config-tok`, `git`, `ssh` on `athena`; `sase_job_sideca`, `sase_job_artifa`, `sase_job_agent_`, `git`, `ssh` on `apollo`).
  - On `apollo`, two restarts logged `Found left-over process ... in control group while starting unit` (`Nov 17 20:24:13` and `23:45:23`).
- **In-Place `uv tool` / Code Upgrade Races Against Running Daemons & Launches:**
  - `athena` (`2026-11-18T12:36:20-05:00`, 27 seconds before a `12:36:47` `sase.service` restart): `sidecar_auto_sync`, `agent_auto_restart`, and `artifact_retention` crashed simultaneously with **`exit code -7` (`SIGBUS`)** when shared binaries/mmap'd extensions were overwritten under running processes. Earlier on `2026-11-16T10:52:47`, `wait_checks` failed with `ModuleNotFoundError: No module named 'sase_core_rs'` coinciding with `install-20261116T155240Z`.
  - `apollo`: `pending_checks_poll` hit **`exit code -7` (`SIGBUS`)** (`2026-11-17T20:59:54-05:00`), and `launch_failures.jsonl` recorded `ImportError: cannot import name 'BeforeSpawnCallback' from 'sase.agent.launch_executor_types'` (`261118_072052`) during a partial code/install transition.
  - Renamed/removed entrypoints still referenced by live scheduler state caused `sase_job_tg_outbound` `No such file or directory` (`athena`, `2026-11-16`) and `sase_job_agent_auto_restart` (`358` historical digests on `athena`), while `sase doctor` warns of **`14 provider skill files out of sync`** (`config.init`) on both hosts.

### 2.4 `sase_gateway` WAL `try_from(-1)` Bug & Multi-Minute Fleet Snapshots (`apollo`)

In `apollo`'s `~/.sase/service/procs/gateway/output.log` (`2.0 MB` bounded log):
- **SQLite WAL Checkpoint Bug:** Repeated warnings:
  ```text
  WARN sase_gateway::fleet_reads: fleet index WAL checkpoint failed error="out of range integral type conversion attempted"
  ```
  - **Root cause (`sase-core/crates/sase_core/src/agent_scan/index/checkpoint.rs:70-86`):** `PRAGMA wal_checkpoint(TRUNCATE)` returns `(-1, -1, -1)` in SQLite when busy/unavailable, and lines `83–86` unconditionally pass those `i64` values to `u64::try_from(log_frames)` and `u64::try_from(frames_checkpointed)`, failing every blocked checkpoint attempt.
- **Slow `scope="presentation"` Snapshot Builds & `504` Timeouts:** Snapshot builds logged durations of `5s–28s`, **`158.3s`** (`Nov 18 17:35Z`), and up to **`1,796,293 ms` (~30 min, `Nov 14 17:13Z`)**, starving callers (`timed_out_waiters=1..3`) and triggering **`504 Gateway Timeout`** HTTP responses (`latency=4000–4005 ms` on `Nov 15` and `Nov 18`).

### 2.5 SDD Sidecar Integrity Failures, Nested Mismatched Clones, & Git Contention

- **`workspace_sdd_clone_recovery` (`recent_errors.json` & digests):**
  - `athena` (`25/100` recent errors): `17` occurrences of `/home/bryan/projects/github/bobs-org/bob-cli/sase/repos/plans is not safe to write: not a valid Git worktree`, plus `bob-cli/repos/plans`, `love/repos/beads`, `dev/repos/plans`, `love/repos/research` hitting detached HEAD or `sdd.health.head` / `sdd.health.conflicts timed out after 0.1s`.
  - `apollo` (`7/100` recent errors), plus a persistent mismatched nested sidecar clone at `/home/bryan/projects/github/sase-org/sase/sase/repos/research/sase/repos/plans` whose `origin` is `git@github.com:sase-org/sase--research.git` (producing `Refusing to replace mismatched SDD sidecar clone` in `lumberjack-comments.log` and live during `sase repo open research`).
- **Bead Push Dirtiness & Git Lock Contention:**
  - `athena` `bead_push_logs` (`2026-11-19T01:01`/`01:03Z`): `sase_11/sase/repos/plans needs integration but has tracked worktree changes`.
  - `tui_git_ops.jsonl`: `508` `nonzero` ops out of `7,087` on `athena`; `414` `nonzero` ops out of `3,527` (`tui_git_ops.jsonl`) + `1` `timeout` (`562ms` vs `0.46s` budget in `.1`) on `apollo`. Active `git_lock_retry` warnings and stale `.git/index.lock` cleanups still appear in mid-November (`apollo` `2026-11-14` `sase-research-artifacts`, `2026-11-18` `sase`; `athena` `2026-11-18 11:32` `sase-core`).

### 2.6 `workspace_claims.jsonl` No-Op Spam, Stranded Work, & Reuse Failures

- **Ledger Churn (`src/sase/running_field/_hold.py:70-84`):** When `hold_workspace_claim` detects `not bool(plan.get("changed"))`, it calls `record_running_field_mutation(..., error="already pinned (no-op)")`. Because `ace-monitor` polls repeatedly, this writes thousands of bogus error rows:
  - `athena`: **`4,790` rows in ~3.5 hours** (`2,107` in `.jsonl` + `2,683` in `.jsonl.1`, on `ws25`, `gh_sase-org__sase`).
  - `apollo`: **`2,275` rows in ~7 hours** (`.jsonl.1`, on `ws13`, `gh_bbugyi200__tailnet`).
- **Stranded Work, Occupancy Conflicts, & Quarantined Slots:**
  - `Workspace held: stranded work` notifications fired **`33` times in 7 days on `athena`** (`17` in 48h) and `5` times in 7 days on `apollo`.
  - `sase doctor` `workspace.occupancy_conflicts`: **`4`** on `athena` (`cash` `ws#10`, `bob-cli` `ws#32`, `sase` `ws#43` & `ws#45`), **`1`** on `apollo` (`bob-cli` `ws#32`), plus `1` quarantined workspace slot on `apollo` (`workspace-slot-refusal`, `tailnet_10` nested `nut`).
- **Agent Name Reuse Cleanup Failures (`launch_failures.jsonl`):** `athena` logged **`4`** failures in the last 7 days (`sase-1t3.5`, `sase-1t3.1`, `sase-1tb.land`, `sase-1t3.10.1.3`) plus earlier November failures (`bob-cli-kq.land`, `bob-cli-k3.10`) reading `Agent name reuse failed: forced reuse cleanup left agent session '<name>' reservations after rebuild`, and `apollo` logged `2` historical failures in October (`bob-cli-a7.1`, `bob-cli-a8.1`).

### 2.7 Heavy Axe Chop Timeouts & Usage Probes

- Multi-minute chop timeouts recur simultaneously during periodic maintenance sweeps:
  - `artifact_link_backfill` (`300s`: `15x` in Nov `athena` digests, `6` in `apollo` `recent_errors.json`), `artifact_run_prune` (`300s`), `artifact_retention` (`300s`), `sidecar_auto_sync` (`120s`), `footprint_fold` (`120s`), `gate_turn_reclaim` (`120s`), `agent_state_refresh` (`120s`), `stale_running_cleanup` (`90s`), `usage_refresh` (`90s`). On `apollo`, `digest_20261118_170232.txt` alone captured `18` concurrent chop errors.
- `lumberjack-usage.log` logs `muse=error` continuously on both `apollo` and `athena`.

### 2.8 Telegram Transient Traceback Spam & Temp Clutter (`athena`)

- Over the tail `4 MB` of `athena`'s `lumberjack-telegram.log` (and echoed in `telegram_receiver/output.log`), transient Telegram/Cloudflare API hiccups generated **`130` `TimedOut`** and **`19` `NetworkError: Bad Gateway`** full multi-frame Python tracebacks.
- `sase doctor` flags `1` missing custom Telegram command (`tg_cmd_tasks` under `integrations.telegram_commands`).
- `~/.sase/axe/lumberjacks/telegram/` holds orphaned `toPdfViaTempFile*.html` (`~8.2 MB`) and `0B` PDF temporary conversion files.

### 2.9 Hygiene Clutter, Startup Log Noise, & CLI BrokenPipe

- **Leaked Proc Lock Files (`~/.sase/procs/logs/`):** **`13,570`** `.*.log.lock` files vs `585` non-lock files on `athena`; **`6,716`** `.*.log.lock` files vs `40` non-lock files on `apollo`.
- **Orphaned Atomic-Write Temps (`~/.sase/`):** **`9`** leftover `.agent_name_registry.json.*.tmp` files totaling **`85,646,457 B` (`85.6 MB`)** on `athena`, and **`3`** files totaling **`22,869,916 B` (`22.9 MB`)** on `apollo`.
- **`sase doctor` Configuration & Workspace Drift:**
  - `project.junk_directories`: **`32`** on `athena`, **`18`** on `apollo`.
  - `completion.install`: stale/missing runtime grammar cache (`3` shells on `athena`, `2` on `apollo`).
  - `axe.external_pr_mirror`: `stale_cursor` on **`10`** repos (`athena`) and **`9`** repos (`apollo`).
  - `config.model_macros`: `m_cheap: '@cheaper'` warning on both hosts; `config.retired_xprompt_names`: `sase-github` and `sase-research-artifacts` still defining `sase_xprompts`.
- **Zero-Fault Banner Noise (`src/sase/main/ace_handler.py:39-48`):** `_enable_tui_faulthandler` appends a timestamp/PID/version line to `tui_faults.log` on every normal launch despite `0` faults ever occurring (`305` lines / `14,555 B` on `apollo`; `351` lines / `16,727 B` on `athena`).
- **Uncaught Pipe Error (`src/sase/notifications/cli_list.py:48`):** `_print_json` calls `json.dump(payload, sys.stdout, indent=2)` without catching `BrokenPipeError`, printing a raw traceback when piped (`sase notify list -j | head`).

---

## Part 3: Historical / Resolved Log Artifacts

Because `tui.log` (`~1.60 MB` on both hosts) does not perform date-based rotation, several prominent all-time log patterns are **already resolved** and should **not** be conflated with active regressions:

- **`AgentWorkspaceRetention is not JSON serializable`** (`34` `ERROR` + traceback rows on `athena`, ending **Nov 4**; older `Oct 12+` rows on `apollo`).
- **`sase-tui-screenshot-export` timeouts** (ceased after **Nov 1** on `athena`).
- **`Ignoring conflicting PROJECT_NAME 'sase'`** (`7,461` warning lines in `apollo` `tui.log`, all from **Sep 9–12**).
- **`Packaged skills/xprompts directory not found via importlib.resources`** (`384` lines in `apollo` `tui.log`, **Oct 3**).
- **`sase-core` `.git/index.lock` burst (`3,066` retries on `athena`)** (concentrated on **Oct 11**; recent retries are much smaller isolated events).

---

## Part 4: Ranked List of Recommended Fixes & Improvements

Recommendations are ranked strictly by operational risk, outage/freeze severity, and alert-noise reduction across `apollo` and `athena`:

1. **Rank 1 (Critical) — Decouple Disk Reapers from Shared `InventoryScanBudget` (`src/sase/core/disk_footprint_utils.py`)**
   - **Why:** Prevents silent `166–192 GiB` "Unattributed" blind spots, `managed_tmp_reaper` blocks, and full `Errno 28: No space left on device` service outages like `apollo`'s Nov 16–17 crash.
   - **Fix:** Give each owner/reaper an independent per-owner scan budget (or fast targeted mtime cleanup pass on `.cache/sase/tmp/cargo-targets/*`, `sase-core/target/uv-tool-*`, `.local/state`, and `managed_tmp`) so `du` exhaustion never blocks temp reaping. Keep the global inventory budget solely as a best-effort reporting cap.

2. **Rank 2 (Critical) — Eliminate TUI Heap Growth, Main-Thread Sync Hotspots, and Missing-Widget Crashes**
   - **Why:** Eliminates `3.88–6.20 GB` RSS bloat, swap-amplified `73s–324s` GC pauses, `74s–116s` key-input hitches, `30s` `kill-and-edit` cleanup timeouts, and live `NoMatches` tracebacks.
   - **Fix:**
     1. Offload `aggregate_clan_runtime`, `list_project_records`/`_project_record_has_spec`, `_canonical_path`, `agent_share_fingerprint`, and `compile_query_profile` from Textual's main loop into worker threads backed by mtime/TTL caches.
     2. Bound in-memory caches/history objects retained per TUI session (preventing `16.5M`-block / `5.8M`-object Gen-2 collections) and investigate leaked references driving `4.5+ GB` RSS within 20–30 min on `athena`.
     3. Guard optional UI queries in `src/sase/ace/tui/actions/agents/_notification_polling.py:438` (`#notification-indicator`) and `src/sase/ace/tui/modals/gate_input_panel.py:167` (`#gate-input-footer`) against `NoMatches`/screen switches.
     4. Serialize `tui_stalls.jsonl` writes cleanly to prevent torn/malformed JSON lines (`3` observed on `apollo`).

3. **Rank 3 (High) — Add Per-Project/Signature Backoff & Protection Classification to `agent_publication` (`src/sase/agents_sync/publication_job.py`)**
   - **Why:** Eliminates `#1` `axe` error digest storm (`62/100` `recent_errors` on `apollo`, `44/100` on `athena`, `5,956` Nov entries on `athena`, `16` `100-error/hr` alerts in 7d on `apollo`) and stops `1,546` / `5,202` outbox drift rows.
   - **Fix:** Maintain per-`(project, error_signature)` exponential backoff and state-transition alerting (notify on transition/escalation, not every 17s); separate intentionally withheld/parked items from `summary.errors`; treat permanent config errors (missing `sase-spotify` remote or `nut` target) as sticky degraded state until config changes; prune stale/retired outbox revisions.

4. **Rank 4 (High) — Fix SQLite WAL `u64::try_from(-1)` in `sase-core` & Add Stale-While-Revalidate Fleet Snapshot Serving (`sase_gateway`)**
   - **Why:** Stops `WARN sase_gateway::fleet_reads` conversion failures and prevents `158s–1,796s` snapshot rebuilds from triggering `504 Gateway Timeout`s on `apollo`.
   - **Fix:** Update `sase-core/crates/sase_core/src/agent_scan/index/checkpoint.rs:70-86` to handle SQLite's `-1` checkpoint return safely (`Option<u64>` / clamp `< 0` rather than failing `u64::try_from`); use non-blocking `PASSIVE` checkpoints on read paths; serve cached presentation snapshots asynchronously while rebuilding in the background.

5. **Rank 5 (High) — Fix `remote-attention` Dedup Key, Aggregate `wait_checks` by Blocker, Externalize Oversized Notification Blobs, & Reconcile Orphaned Gates**
   - **Why:** Cuts duplicate alert fatigue (`308` `remote-attention` + `94` `wait_checks` in 7d on `athena`), shrinks `5–7 MB` active / `41–109 MB` archive JSONL rewrites and broken `files` refs (`314` / `522`), and clears `2,501` / `5,029` orphaned `interaction_requests/`.
   - **Fix:**
     1. Key `_dedup_key` in `src/sase/dispatch/attention_inbox.py:555-561` by `(origin_installation_id, stable_gate_or_bead_id)` (not per-event `request_id`/`revision`), preserving dismissed state across matching revisions.
     2. Key `upsert_terminal_blocked_wait_notification` (`src/sase/scripts/_chop_wait_checks_terminal.py:183-190`) by root blocker + waiter epic rather than per downstream waiter bead, and halt repeated `plus_ones` once terminal failure is recorded.
     3. Store large prompts/errors (`> 8 KB`) as indexed sidecar/log files instead of embedding `171–217 KB` inside `notifications.jsonl` `action_data`/`notes`, and prune dangling `files` paths + `notifications-archive.jsonl` entries past retention.
     4. Add periodic reconciliation resolving/pruning `interaction_requests/` entries whose notification was dismissed/archived or whose bead closed.

6. **Rank 6 (High) — Atomic Daemon Upgrade Coordination & Clean Systemd Process-Group Teardown**
   - **Why:** Prevents mid-upgrade `SIGBUS` (`exit code -7`), `No module named 'sase_core_rs'`, `ImportError`, `14` out-of-sync skill files, `951 MB` `wait_checks` RSS spikes / `16.3 GB` `sase.service` peaks, and `SIGKILL`/leftover-cgroup restarts.
   - **Fix:** Stop/quiesce `sase.service` workers (or switch active symlink atomically after wheel build) before `uv tool` overwrites live binaries/extensions, run skill & scheduled-job migrations (`tg_outbound`, `agent_auto_restart`) at install time, and use process-group termination + shorter git/ssh subprocess timeouts so systemd stops cleanly before `SIGKILL`.

7. **Rank 7 (Medium-High) — Silence `already pinned (no-op)` Ledger Writes & Harden SDD Sidecar / Name-Reuse Cleanup**
   - **Why:** Stops `4,790` (`athena` in ~3.5h) and `2,275` (`apollo` in ~7h) false `"error"` writes churning `workspace_claims.jsonl`, prevents `25/100` SDD recovery errors, and eliminates recent name-reuse launch aborts.
   - **Fix:** Skip writing `record_running_field_mutation(..., error="already pinned (no-op)")` in `src/sase/running_field/_hold.py:70-84` when `not plan.get("changed")`; raise `sdd.health.conflicts` timeout above `0.1s` and avoid nesting incompatible `sase/repos/plans` clones inside sidecar repos like `sase--research`; ensure agent-session reservation cleanup confirms zero remaining reservations before triggering a `launch` failure.

8. **Rank 8 (Medium) — Shrink `bob-cli` Codex Developer Instructions & Make Heavy Axe Chops Incremental**
   - **Why:** Eliminates daily Codex `oversize` delivery fallbacks (`36,186 B > 32,768 B` in `codex.py:213`) and stops `90s–300s` batch chop timeouts (`artifact_link_backfill`, `artifact_run_prune`, `artifact_retention`, etc.) + constant `muse=error` usage failures.
   - **Fix:** Trim/move non-essential instructions from `bob-cli` core memory into on-demand reference notes until the compiled bundle sits comfortably under `32 KiB` (or split spillover cleanly in `instruction_delivery`); convert backfill/prune/retention chops to cursor-based bounded batches per tick; fix or explicitly gate/disable broken `muse` usage polling.

9. **Rank 9 (Medium-Low) — Downgrade Transient Telegram Network Tracebacks & Clean PDF/HTML Temp Files (`athena`)**
   - **Why:** Stops `130` `TimedOut` + `19` `Bad Gateway` stack traces flooding `lumberjack-telegram.log` and reclaims orphaned `8.2 MB` `toPdfViaTempFile*` artifacts.
   - **Fix:** Log transient `TimedOut`/`NetworkError` as compact single-line warnings with backoff; clean up dead `tg_cmd_tasks` registration; wrap HTML->PDF temp paths in `try/finally` deletion.

10. **Rank 10 (Low) — Automate Lock/Temp/Junk Hygiene & Fix `tui_faults.log` / `BrokenPipeError`**
    - **Why:** Reclaims **`20,286`** leaked `.log.lock` files (`13,570` + `6,716`), **`108.5 MB`** across `12` orphaned `.agent_name_registry.json.*.tmp` files (`85.6 MB` + `22.9 MB`), **`50`** junk project dirs (`32` + `18`), `stale_cursor`s, and small CLI irritations.
    - **Fix:** Unlink per-proc `.log.lock` files cleanly on exit and add an age-based reaper for `.log.lock` and `.agent_name_registry.json.*.tmp`; fix `src/sase/main/ace_handler.py:39-48` to write `tui_faults.log` headers only on actual faults (or remove empty session headers on clean exit); catch `BrokenPipeError` in `src/sase/notifications/cli_list.py:48`; refresh `completion.install`, stale PR mirror cursors, `m_cheap`, and retired `sase_xprompts` configs.
