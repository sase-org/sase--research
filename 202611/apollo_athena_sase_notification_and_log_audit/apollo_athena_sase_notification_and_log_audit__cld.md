# SASE notifications and error/warning logs on apollo and athena: what to fix

_Researcher: `cld` · 2026-11-19 · Machines: apollo (this host) and athena (over Tailscale
SSH) · Window: full notification history, with emphasis on Nov 1–19_

## Bottom line

- **The biggest live problem isn't an error. It's a notification feedback loop.** The
  `hooks/stale_running_cleanup` routine re-settles every legitimately retained ("held")
  monitor workspace on every pass. Each pass re-probes git and appends a "+1" to the
  "Workspace held: stranded work" notification.
  - Totals: **107,153 +1s on apollo and 124,210 on athena.** One apollo row alone has
    90,786.
  - Each +1 rewrites the whole notification store under an exclusive lock. On athena that
    is **20 full rewrites per minute of a 7.4 MB file, right now.** Store generation
    counters read 135,428 (apollo) and 340,879 (athena).
  - It keeps going after you dismiss the notification. All 10 rows still ticking on
    athena are dismissed.
- **The disk-pressure notifier can't tell you what is filling the disk.** Workspace rows
  in `sase disk list` read `0 B` with coverage `complete` because the shared 5-second
  scan budget ran out before they were measured.
  - Apollo ran out of space on Nov 16 21:06 (1.8 MiB free). That crash-looped the
    `agent_waits` routine and produced hourly "100 error(s)" digests.
  - Every one of the 64 November disk-pressure notifications blamed ~175–193 GiB of
    "unattributed" space.
  - The real owners included 54 GiB of SASE workspaces (34 GiB from 24 bob-cli
    workspaces) and 24 GiB under `~/.sase`.
  - This is a regression of closed bead `sase-1bf.4`, whose stated scope was "cover every
    registered root and every workspace checkout before the stray walk".
- **Four smaller defects, each confirmed in code:**
  1. The Telegram client resends as plain text after network errors, not only after
     Markdown parse errors.
  2. `bead_task_triage` retries a gate request ID that can never succeed (1,517 times in
     7 days).
  3. The sase instruction bundle now exceeds Codex's 32 KiB cap, so every Codex launch
     since Nov 17 falls back to legacy delivery (207 launches).
  4. The SDD health check reports a timeout as repository corruption.
- **The big digest storms from Nov 1–17 are mostly fixed already.** These were the
  `agent_publication` errors repeated every ~18 s: 94% of apollo's and 96% of athena's
  November digest entries.
  - The last storm (`nut`: "no usable agents publication target") stopped at Nov 17 07:36.
    That was one minute after commit `b0de76422d`.
  - What's left: the digest format still hides how bad a storm is. It caps at 100
    entries, doesn't group, and doesn't show truncation.

## 1. What I examined

| Source                                                    | apollo                                                 | athena                                    |
| --------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------- |
| `sase notify list -j --all`                                 | 1,777 rows (Aug 31 → Nov 19)                           | 2,626 rows (Jul 6 → Nov 19)               |
| Error digests (`~/.sase/axe/error_digests/`)              | 436 files; 8,546 entries since Nov 1                   | 726 files; 6,050 entries since Nov 1      |
| Lumberjack routine logs (`~/.sase/axe/logs/lumberjack-*`) | 11 logs, ~33–50 MB each, Nov 12–19 window              | same set, remote aggregation              |
| TUI logs (`tui.log`, `tui_faults.log`, `tui_stalls.jsonl`)  | read                                                   | read (`tui.log*`)                         |
| `launch_failures.jsonl`, `dev_update.jsonl`                 | read                                                   | `dev_update.jsonl` read                     |
| `sase disk list -j`                                         | run                                                    | run                                       |
| Cron logs (`~/.local/state/cron/`)                        | no job logs                                            | `bob-nightly`, `pass-git-sync`: clean |
| Source code verification                                  | sase (`master` @ `065eda33`), sase-core, sase-telegram | —                                         |

I parsed everything read-only, with scripts that normalize numbers, hashes, paths, and
agent names into error signatures. I didn't dismiss or mutate any notification.

## 2. Notification volume at a glance (November)

| Sender                                    | apollo rows | athena rows | Note                                                               |
| ----------------------------------------- | ----------: | ----------: | ------------------------------------------------------------------ |
| `user-agent`                                |         268 |         297 | Completions plus "Workspace held" (where the +1s pile up)         |
| `bead`                                      |         250 |         258 | Task-triage prompts; healthy                                       |
| `axe`                                       |         191 |         146 | Hourly error digests (189 / 140) plus ACE-prune nudges           |
| `wait_checks`                               |          24 |         130 | "Wait dependency can never self-resolve", "Stranded bead"          |
| `remote-attention`                          |           0 |         162 | apollo beads mirrored to athena; working as intended               |
| `file-hooks`, `workspace-rescue`, `plan`, … |       small |       small | Informational                                                      |
| `disk_pressure`                             |          12 |           0 | apollo only; all say "unattributed"                                |
| `instructions`                              |           3 |           3 | "Instruction delivery fell back to legacy for codex: oversize"     |

Unread, undismissed notifications: **420 on apollo, 422 on athena.** Most of the
counter weight is +1s, not rows:

| +1 source (rows created since Nov 5)                       |  apollo |  athena |
| ---------------------------------------------------------- | ------: | ------: |
| `user-agent` "Workspace held: stranded work"                 | 107,153 | 124,210 |
| `wait_checks` "Wait dependency can never self-resolve"       |     299 |   4,135 |
| `wait_checks` "Stranded bead: …" (largest single row)        |     435 |   1,003 |
| `instructions` "fell back to legacy for codex: oversize"     |     116 |      85 |

## 3. Open findings, with evidence and root cause

### F1. Held-workspace re-settlement loop: +1 storm and store write amplification (both machines, live)

**Symptom.**

- 6 "Workspace held" rows on apollo carry 107,153 +1s. 27 rows on athena carry 124,210.
- The retained +1 notes all read "Workspace still held (evidence_unavailable)" or
  "(session_owned_dirt)". They arrive every ~9 s (median gap on apollo's largest row)
  to ~30 s.
- On athena, 10 rows were still ticking during this audit, and all 10 are already
  dismissed.
- Over 60 s, athena's `notifications.jsonl.generation` advanced by 20 while the file was
  7,419,214 bytes. That's about 150 MB/min, or about 210 GB/day, rewritten for no new
  information.

**Root cause (verified in code).**

1. `hooks/stale_running_cleanup` calls the leaked-monitor repair for each claim it
   classifies as leaked:
   - The repair calls `release_monitor_claim(...)` (`src/sase/ace/scheduler/stale_running_leak.py:134`).
   - When the claim legitimately stays held, it logs "Leaked monitor claim for workspace
     #N retained with other dirt" (`:159`) and returns.
   - Nothing marks the claim as already settled with unchanged evidence, so the next pass
     repeats the whole settlement.
   - Athena's hooks log, which only covers Nov 17–19 because of truncation, has
     5,500–5,660 "retained" lines for each of 6 workspaces (#16, #18, #20, #25, #31, #33).
2. Each settlement runs `settle_stranded_workspace`:
   - It probes `git status` in every related repo.
   - It re-snapshots worktree diffs. For apollo's bob-cli #24 that was 5 files, 5.6 MB per
     pass.
   - It re-persists the retention record.
   - With `notify_on_retain=True` it calls `notify_retained_workspace`
     (`src/sase/turns/_workspace_retention/settle.py:362-365`).
3. `notify_retained_workspace` upserts with a fixed `dedup_key`, so every call becomes a
   +1 (`src/sase/turns/workspace_retention_surface.py:136`).
4. In sase-core, `upsert_notification` takes the exclusive lock, reads all rows, and calls
   `merge_and_rewrite_notifications_unlocked` for every +1
   (`crates/sase_core/src/notifications/store.rs:672-742`). A dismissed row is +1'd and
   rewritten just like a live one.

**A second, separate defect in the same path.** Apollo's 90,786-+1 row (bob-cli
workspace #24, monitor `h2tekq4gtm97`) sat in `evidence_unavailable` for 14 days (Nov 1 →
Nov 15). Its retention record's only probe error was:

> `sibling:bob-mac-capture: fatal: cannot change to '…/bob-cli_19/sase/repos/linked/bob-mac-capture': No such file or directory`

That is a path inside a _different_ workspace (#19). A stale repo path from another
workspace held #24 hostage until it was finally settled `proven_clean`. Bead `sase-1rg.3`
("Scope monitor retention evidence to the monitor's own workspace") is closed. Check that
its fix also covers repo lists inherited from the starter's evidence.

**Fix (all three parts are objectively better than today).**

1. **Settle once per evidence state.** Before calling `release_monitor_claim` in the
   leaked-claim path, skip claims that meet all of these:
   - The retention record is `disposition=retain` and unresolved.
   - The record's `probe_errors` and dirty-path fingerprint match a cheap recomputation.
   - Or simply: the record was written less than N minutes ago.
   Also cache the `git status` result.
2. **+1 only on change.** In `notify_retained_workspace`, skip the upsert when the reason
   (`policy_reason`/`terminal_reason`) equals the last +1 note. Optionally allow a
   low-rate heartbeat, at most hourly.
3. **Store guard.** In sase-core `upsert_notification`, don't rewrite the file for a +1
   whose `(sender, note)` equals the row's newest +1 and arrives within a short coalescing
   window. Never +1 a dismissed row unless the caller opts in. This protects the store
   from the next caller with the same bug.

### F2. `sase disk list` and disk-pressure report skipped rows as `0 B, complete` (both machines; a regression of `sase-1bf.4`)

**Symptom.**

- Apollo: every November `disk_pressure` notification says "Unattributed 174–193 GiB on
  the SASE_HOME filesystem falls outside every inventoried owner". The final ones on
  Nov 16 read "1.8 MiB free (0.0%)… Recovery target: 9.6 GiB".
- The agent_waits routine then crash-looped on `OSError: [Errno 28] No space left on
  device` (notification `f953f4d3`, Nov 16 21:05). Apollo had also nearly filled on
  Sep 13–14 ("N MiB free").
- Today `sase disk list -j` on apollo reports:
  - `stray_scan_visited: 0`
  - `owned_total_bytes == total_bytes` with 159.4 GiB in the `unattributed` row
  - 38 workspace rows (`workspace_cleanup_and_compact` / `workspace_git_object_source`) at
    `size_bytes: 0`, `coverage: complete`
  - diagnostics: "…/workspaces/bobs-org/bob-cli: skipped; shared scan budget exhausted"
- Athena: 43 of 43 workspace rows read 0 B `complete`, 57 "budget exhausted"
  diagnostics, and 567 GiB "unattributed".
- What `du` actually finds on apollo:
  - `~/.local/state/sase/workspaces` holds 54 GiB: bob-cli 34 GiB across 24 workspaces,
    sase 19 GiB across 9.
  - `~/.sase` holds 24 GiB.
  - The provider CLI homes (`~/.codex`, `~/.grok`) hold 5.4 GiB each.

**Root cause (verified).** `DiskFootprintMeter.size()` returns `0` once the shared
budget (default 5 s / 50k nodes) is exhausted (`src/sase/core/disk_footprint_utils.py:132-135`).
Callers can't tell "skipped" from "empty", so the row keeps `coverage: complete`. The
budget is spent first on the large `artifacts/ace-run` trees: "fallback walk truncated;
visited=0". After that, every workspace and repo root is skipped.

**Fix.**

- Return `None`/unknown on a skip, and mark those rows `coverage: partial` with no size.
- Give workspace roots their own budget, or measure them first. A single `du -skx` of each
  project's workspace root is cheap and is what the notification actually needs.
- When attribution is partial, say so in the notification ("workspaces not measured")
  instead of reporting everything as unattributed.

### F3. Telegram client resends as plain text after network failures (athena; sase-telegram)

**Symptom.** Athena's telegram log, Nov 13–18, shows:

- 143 "Failed to send with parse_mode=MarkdownV2, falling back to plain text"
- 637 `telegram.error.TimedOut`, 319 `httpx.ReadTimeout`, 25 `NetworkError: Bad Gateway`
- 455 "Failed to send notification … to Telegram"

Every fallback I inspected followed a `NetworkError`/`TimedOut`, not a Markdown parse
error.

**Root cause (verified).** In `sase-telegram: src/sase_telegram/telegram_client.py`:

- `_send_single_message` catches bare `Exception` (`:129`) and always retries without
  `parse_mode`.
- `@_with_retry` wraps the multi-chunk `send_message`, so a retry re-sends every chunk,
  including chunks that were already delivered.
- One failing chunk can therefore make up to 8 HTTP sends (4 attempts × Markdown plus
  plain).
- A `TimedOut`/`ReadTimeout` doesn't prove the server dropped the message. When it
  didn't, you get a duplicate, and the duplicate is in plain text.

**Fix.**

- Fall back only on `BadRequest` whose message says the entities can't be parsed.
  `BadRequest` subclasses `NetworkError` in python-telegram-bot, so check it explicitly
  first.
- Let `TimedOut`/`NetworkError` propagate to the retry wrapper.
- Move the retry to per-chunk sends.

Related, lower priority: on Nov 14–15, `pass`/gpg decryption failed ("gpg: decryption
failed: No such file or directory"). That produced 408 identical
`TelegramCredentialError` tracebacks. One degraded-state warning or notification with
backoff would carry the same information.

### F4. `bead_task_triage` retries a request ID that can never succeed (athena)

**Symptom.** "[bead_task_triage] Failed to create gate for sase:sase-1hr: request id
already belongs to a different gate specification" appeared 1,517 times between Nov 10
20:17 and Nov 17 11:04. The bead never got its triage gate.

**Root cause (verified).**

- `_request_id(project, bead, generation, kind)` is deterministic.
- On any creation failure the job logs, `continue`s, and doesn't advance `generation`
  (`src/sase/scripts/sase_chop_bead_task_triage.py:509-523`).
- `service_creation.py:334-339` raises `request_id_conflict` whenever the journaled spec
  fingerprint for that ID differs from the new spec, for example after the bead's text
  changed since an earlier partial create.
- So the "retry deterministically" comment is wrong for this error class: the retry is
  guaranteed to fail.

**Fix.** On `GateError("request_id_conflict")`, bump the generation, or adopt and cancel
the journaled request and mint the next ID, then create again. Add a test that changes
the issue body between a failed and a retried create.

### F5. The Codex instruction bundle exceeds its 32 KiB cap; every Codex launch since Nov 17 falls back to legacy (both)

**Symptom.** Daily notifications "Instruction delivery fell back to legacy for codex:
oversize" first appeared Nov 17 00:07. With +1s, they count 119 Codex launches on apollo
and 88 on athena through Nov 19. The two newest bundle snapshots in
`~/.sase/instruction_snapshots/` are 34–35 KB, against 25–26 KB in early November.

**Root cause (verified).** Codex declares `max_bytes: 32 * 1024` for its explicit root
channel (`src/sase/llm_provider/codex.py:213`). `_instruction_boundary.py:404-408`
reports `oversize` and falls back when the rendered root text is larger. The always-inlined
content has grown, mostly the memory-web descriptor sections (31 decision records and the
glossary term list) plus core memory. The bundle crossed the cap around Nov 16–17.

**Fix.**

- Short term: bring the root bundle back under 32 KiB, for example by shortening the
  decisions-web inline listing.
- Durable: add a `just check` or doctor gate that renders each provider's root bundle and
  fails when it's over that provider's `max_bytes`, so growth is caught at authoring time
  instead of in production.
- If Codex's channel genuinely allows more, raise the cap with a test that proves the
  larger payload is delivered.

### F6. The SDD health check reports a timeout as corruption (both)

**Symptom.** Digest entries such as:

> "SDD repository …/gh_bbugyi200\_\_body/repos/plans is not safe to write: not a valid Git
> worktree; detached HEAD; could not list unmerged index entries: deadline expired before
> git operation. Finish or abort the existing Git operation in that repository… machine-
> managed recovery failed"

This appeared for `body`, `love`, `job`, `dev` and `bob-cli` sidecars, about 30 times in
November across both hosts.

I checked the flagged apollo clones (`body/plans`, `love/beads`, `job/research`). All
three are healthy: on `main`, clean, no unmerged entries. The only real failure was
"deadline expired". It happens most on apollo, whose 15-minute load average was 39 on 16
cores during this audit.

**Fix.** When a health probe fails because its deadline expired, classify the result as
`health_unknown: timeout`. Defer it to the next pass, and keep it out of the error digest
until it persists, say for several passes. Don't print the corruption text or "machine-
managed recovery failed".

Athena did have one _real_ corruption: empty object files in
`bob-cli/sase/repos/plans`, 108 log lines on Nov 14–15. It has since recovered
(`git fsck --connectivity-only` clean, 0 empty objects).

### F7. Error digests hide storm size (both; carried over from the Nov 8 report, still open)

**Symptom.** `append_error` keeps only the last 100 errors
(`src/sase/axe/_state_scheduler.py:198`). So:

- 17 apollo and 6 athena November digests said exactly "100 error(s) in the last hour".
  The true counts were higher; publication was failing every ~18 s, about 200 per hour.
- Each such digest lists the same signature 100 times.
- Three signatures made up 94% (apollo) and four made up 96% (athena) of all November
  digest entries.

**Fix.** In `notify_axe_error_digest` (`src/sase/notifications/senders.py:117`):

- Group entries by `(routine, job, normalized error)`, with count, first and last seen,
  and one sample.
- Keep a full-hour counter separate from the 100-sample ring, so the header can say
  "≥ 312 errors (100 sampled)".

### F8. `agent_state_refresh` re-logs the same verdict for terminal agents on every pass (both)

**Symptom.** Over 8 days, 7,724 lines on apollo (1,287 distinct agents) and 8,580 on
athena (2,582 agents) of "[agent_state_refresh] <agent>: conflicting_terminal_evidence;
preserved failed" or "missing_evidence; preserved failed". Single agents repeat up to 246
times.

**Fix.** Persist the verdict with an evidence fingerprint and skip re-examining unchanged
terminal agents. At minimum, log only on a change. This also cuts work in the `checks`
routine, which times out on apollo.

### F9. Priority ACE-prune nudges for trivial amounts (athena)

**Symptom.** Priority `axe` notifications such as "873.7 KiB of old ACE runs can be
pruned" (Nov 18) and "9.7 MiB… can be pruned", with 41 +1s. Athena has 283 GiB free.

**Root cause.** `_should_notify` fires whenever `counts.selected > 0`, with no size floor
(`src/sase/core/agent_artifact_run_prune_publish.py:179`).

**Fix.** Require a minimum reclaimable size, or a share of the filesystem, before a
priority notification. Below the floor, prune silently on the normal schedule or emit a
non-priority row.

### F10. Install-window skew shows up as job and launch errors (both, intermittent)

These look like routine spawns racing a dev update (`uv tool` reinstall or source
switch):

- athena Nov 8: `can't open file …/bin/sase_job_mentor_checks` (and three sibling hook
  jobs)
- athena Nov 16–17: `Job script not found: sase_job_tg_outbound` and
  `sase_job_agent_auto_restart`
- apollo Nov 12: 80 lines of "sase_core_rs … does not expose binding
  'project_local_commands'; the installed wheel is stale"
- apollo Nov 18: launch failure `ImportError: cannot import name 'BeforeSpawnCallback'`

`dev_update.jsonl` also shows the step "Install prebuilt Rust dev artifacts" returning
exit 1 in 18 of 37 records on apollo and 8 of 15 on athena. Each time the reason is
`{"hit": false, "reason": "commit-mismatch"}`, which is a cache miss and not a failure.
After the miss the update compiles from source; that update took 711 s on apollo. The
records also carry a `RuntimeWarning: 'sase.dev_update.prebuild' found in sys.modules`.

**Fix.**

- While a dev update holds the code-swap lock, have the orchestrator treat "job script
  not found" and "binding missing" as _deferred_ (retry next tick) instead of errors.
- Make `prebuild consume` exit 0 with `hit:false` on a miss, or have the caller treat that
  result as a miss.
- Run the prebuild module so it isn't imported by its own package first; that removes the
  runpy warning.

## 4. Already fixed: no action needed

| Issue                                                                                                                 | Evidence that it's over                                                                                                                    |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `agent_publication` "gh_bbugyi200\_\_nut: no usable agents publication target", repeated every ~18 s (1,893 digest entries) | Last entry Nov 17 07:36; commit `b0de76422d` (Nov 17 07:35) "silence unmanaged-project noise in retention and publication"                 |
| "ACE run pruning is paused: 2 protection sources are unreadable" (apollo, 19 +1s) and `artifact_run_prune protection_unavailable`  | Same commit skips not-applicable beads/plans retention sources; no entries after Nov 17                                                     |
| Nov 1–6 bob-cli publication storms ("withheld by publication protection", `git pull --rebase` failed)                   | No entries after Nov 6 (apollo) / Nov 4 (athena)                                                                                           |
| TUI crash in `gate_input_panel._fit_body_scroll` (apollo, Nov 17 20:33)                                                 | `dd56fe2075` "survive gate-fit teardown" (Nov 17 20:17; the running TUI predated it)                                                       |
| TUI `AgentWorkspaceRetention is not JSON serializable` (17 occurrences, Nov 4)                                         | `c6282f75b2` "omit workspace retention from agent bundles"                                                                                 |
| Athena `bob-cli/sase/repos/plans` empty git objects (Nov 14–15)                                                         | Repo is healthy now                                                                                                                        |

## 5. Context, not recommendations

- **Apollo is resource-starved under swarm load.** Its 15-minute load average was 39 on
  16 cores. Routine timeouts are far more common there than on athena: since Nov 2,
  `sidecar_auto_sync` (34), `agent_publication` (32), `stale_running_cleanup` (31),
  `wait_checks` (25), `usage_refresh` (20), and the other hook jobs (10–14 each).
  Fixes F1 and F8 remove recurring work from exactly those routines.
- **Apollo's disk is 193 GB**, and 24 bob-cli workspaces take 34 GiB of it. Whether to
  cap the workspace count is a preference, not an objective fix. But F2 is what would
  have told you this before Nov 16.
- **`tui_faults.log`** holds 305 session-start headers and no fault stacks. The
  faulthandler is armed and has caught nothing; that's benign.
- **`managed_tmp_reap`** logs "environ unreadable: Permission denied" for same-UID
  processes such as `systemd --user`. That's deliberate fail-closed behaviour; at most,
  log it once per PID.
- **`remote-attention`** (162 rows on athena) mirrors apollo task beads as intended.

## 6. Ranked fixes

Ranked by impact (user-visible noise, wasted I/O and CPU, outage risk) × confidence. All
are fixes for verified defects or plain improvements, not changes of policy.

1. **Stop re-settling already-retained monitor claims, and +1 only on change (F1).**
   Settle at most once per evidence fingerprint in
   `stale_running_leak.py` → `release_monitor_claim`. Skip the upsert in
   `notify_retained_workspace` when the reason is unchanged. Add a sase-core store guard
   that coalesces identical +1s and doesn't rewrite for +1s to dismissed rows. _Removes
   about 230k redundant +1s, ~20 full-store rewrites/min on athena right now, and
   repeated git probes and diff snapshots in a routine that times out on apollo._
2. **Make disk attribution honest (F2).** Return unknown, not `0`, when the scan budget
   is exhausted, and mark the row `partial`. Measure workspace roots first or with their
   own budget. Name unmeasured owners in the disk-pressure notification. Reopen or
   follow up `sase-1bf.4`. _Apollo hit ENOSPC on Nov 16 while 64 notifications pointed
   at "unattributed"._
3. **Fix the Telegram fallback and retry semantics (F3).** Fall back to plain text only
   for entity-parse `BadRequest`, and retry per chunk. _Stops duplicate and
   wrong-format sends, and cuts up to 8× HTTP amplification per failing chunk._
4. **Advance the generation on `request_id_conflict` in `bead_task_triage` (F4).** _The
   triage gate currently can never be created for an affected bead; 1,517 failed
   retries in a week._
5. **Get the Codex root bundle under 32 KiB, and gate bundle size in CI or doctor (F5).**
   _Restores the documented explicit-delivery path for every Codex launch, about 60–75
   per day._
6. **Classify SDD health-probe deadline expiry as "unknown/deferred", not corruption
   (F6).** _Removes false "not a valid Git worktree… recovery failed" alarms on healthy
   repos._
7. **Group error digests by signature and show the true count beyond the 100-sample cap
   (F7).** _A storm becomes one line with a count and is never hidden by truncation._
8. **Memoize `agent_state_refresh` verdicts for terminal agents (F8).** _About 1,000
   redundant warning lines per day per host, and less work in a routine that times out._
9. **Treat install-window skew as deferred, and a prebuild cache miss as a miss (F10).**
   _Removes intermittent false job and launch errors during updates, and a false
   "failed" step in half of all dev updates._
10. **Add a size floor to priority ACE-prune nudges (F9), and collapse repeated Telegram
    credential tracebacks into one degraded-state signal (F3 addendum).** _Inbox and log
    hygiene._

## 7. Limitations

- Lumberjack logs are truncated to their most recent output, so per-routine counts cover
  only the windows noted (hooks: Nov 17–19; others: Nov 12–19). Notification and digest
  counts cover full history.
- I didn't trace which TUI readers reload on every generation bump. The write
  amplification in F1 is measured; any read-side cost is inferred, not measured.
- I read the athena sources over SSH and aggregated them remotely with the same scripts
  used on apollo. I verified code only against the apollo checkouts, which run the same
  `master`.
