# Which athena/apollo audit findings are worth fixing?

> **Research query:** Review
> [athena_apollo_operational_log_audit.md](athena_apollo_operational_log_audit.md) and
> decide which of its issues are worth addressing. Check recent commits and launched
> epic and tale plans first, so nothing already fixed or in flight is duplicated. End
> with a ranked list.
>
> **Checked:** 20 October 2026, about 15:45–16:20 UTC (11:45–12:20 EDT), against:
>
> - sase master `9188cc5733` and sase-core master `b664b15b`, which is sase's pinned
>   core;
> - the plans and beads sidecars and the live agent list on apollo;
> - apollo's own logs and disk;
> - one read-only SSH read of athena's TUI telemetry and disk.
>
> The audit was committed at 10:45 EDT the same day. Nothing was restarted, retried,
> reaped, or deleted.

## Short answer

Five of the audit's six findings still reproduce, and all five are worth fixing. The
remaining finding, apollo's disk exhaustion, is mostly fixed already, by an epic the
audit never mentions. The audit's explanation of what is left points at the wrong
place.

- **Mostly fixed already: apollo's disk exhaustion.** Epic `sase-1n8`, closed this
  morning, investigated the same 08:36 UTC ENOSPC. It found what filled the disk: a
  19-turn bob-cli verify loop that built a fresh ~2.5 GB cargo target every turn. It
  landed six fixes. The audit's "identify the burst producer" step is therefore done.
- **Still open, and missed by the audit: apollo's tmp reaper can't reclaim most of what
  it should.** Two defects cause this:
  - the known but unworked `sase-1bw`: any SSH session makes the liveness check
    "incomplete" for every older scratch directory;
  - a new defect: read-only `vault` directories left behind by bob-cli tests make
    removal fail about 197 times per run.

  Apollo has **18 GB free** while **25 GB of cargo targets** and **7.6 GB of agent
  TMPDIRs** wait to be reclaimed. `sase-1bw` also undercuts two of `sase-1n8`'s new
  fixes. This is the most urgent item.
- **Confirmed, small, and unclaimed:** `sase-1nb` (cleanup serialization) and `sase-1na`
  (`sase doctor -j`). `sase-1nb`'s blast radius is wider than the audit says: one
  waiting agent can block kill and dismiss for the whole roster.
- **Confirmed and large:** `sase-1nc`. Athena's TUI still has 10–13 second garbage
  collections after a restart.
- **Real, but parked on stale owners:** the publication backlog and the missing
  artifact-link endpoints. The audit attached its evidence as notes on `sase-11o`,
  `sase-11h`, and `sase-12y`. All three epics have been "in progress" for about a month,
  and nobody is working on them. A note on a stalled epic does not mean the problem is
  being addressed.

## What recent work already covers

### Epic `sase-1n8` (done)

Epic `sase-1n8`, "Stop unsatisfiable host-completion loops and the disk churn they
caused", was planned in `plan:202610/host_completion_loop_and_disk_churn.md`. Its
landing tale `plan:202610/sase_1n8_landing_fixes.md` closed it at about 10:20 EDT,
roughly 25 minutes before the audit was committed. Its incident is the audit's
finding 1: the same `rustc` ENOSPC at 08:36 UTC, the same supervisor settlement crash,
and the same 04:50 EDT housekeeping run.

| Phase | Commit | What it fixed | Audit item it covers |
| --- | --- | --- | --- |
| `sase-1n8.1`, `.2` | core `b664b15b`, sase `321d881250` | `sase final prepare` refuses a `just check` contract that cannot report stages, and refuses re-sealing an unchanged tree that was already refused | Removes the loop that minted cargo targets |
| `sase-1n8.3` | `e77280c873` | Follow-up prompts show why host completion refused | Same loop: the agent was never told why |
| `sase-1n8.4` | `25d14fae6c`, `379040e699` | Reclaims the starter's cargo target when its monitor settles | Burst producer |
| `sase-1n8.5` | core `2f433851` | The 1-hour emergency pressure age now applies to unheld entries; the 04:50 run had selected nothing at 3.6 MB free | Pressure recovery |
| `sase-1n8.6` | `2648c7cddf` | The proc supervisor survives ENOSPC and settles truthfully | `proc reconciliation failed: failed to serialize proc: No space left on device` |

All of these are in the installed `0.18.0+46.g2648c7cdd`. The core pin `b664b15b`
contains `2f433851`.

### Everything else

- **Nothing landed after the audit.** Since 10:45 EDT, the only sase commits are test
  splits (`b7f145ef96`, `9188cc5733`). sase-core has nothing after 07:43 EDT.
- **Nothing is in flight.** The only sase-project agent running on apollo is this
  research agent; the rest are bob-cli and home-project agents. Athena's agent list was
  not inspected. No in-progress epic or plan covers `sase-1na`, `sase-1nb`, `sase-1nc`,
  `sase-1bw`, or the read-only removal failure.
- **The audit's own beads are untouched.** It filed `sase-1na`, `sase-1nb`, and
  `sase-1nc` at about 10:27 EDT. All three are `READY` and unclaimed.

## Finding-by-finding verdict

| # | Audit finding | State now (verified today) | Already addressed? | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Apollo disk exhaustion; pressure recovery reported `no_op` | Burst producer and supervisor crash fixed by `sase-1n8`. The `no_op` mislabel and the notify-before-reap ordering are unchanged. Reclamation is still blocked; see the next section | **Partly** (`sase-1n8`) | Fix what remains; it is the top item |
| 2 | Agent publication stuck in quarantine | Apollo: 456 quarantined (453 at audit time) and 284 retired. Athena: 3,356 quarantined per the audit | **No.** `sase-11o.2` last progressed 16 September and has been blocked since | Worth fixing; needs a new owner |
| 3 | Cleanup cannot encode `EpicFollowView` | Reproduces on master in both `serialize_agent` and `agent_state_to_bundle_dict` | **No.** `sase-1nb` is filed but unclaimed | Fix now; wider impact than reported |
| 4 | Long TUI GC pauses | Athena's restarted TUI (instance `8f5fc7b8`): idle gen-2 collections of 10.65 s (12:32:32 UTC), 13.32 s (12:36:44), and 5.02 s (13:24:47) | **No.** `sase-1nc` filed; the `sase-1f3` soak never ran | Worth fixing; large |
| 5 | Artifact-link projection fails on missing bead endpoints | Apollo's latest tick still fails with `Issue not found: bob-cli-5z`. `sase-164` does not exist in the sase bead store | **No.** `sase-1c5` open since 28 September; `sase-12y` is stale | Worth fixing; lower priority |
| 6 | `sase doctor -j` exits during the model-macro scan | Reproduces with apollo's installed sase: exit 1, no JSON | **No.** `sase-1na` is filed but unclaimed | Fix now; smallest change |

## The disk problem the audit missed

The audit read the 04:50 EDT counters `failed=221 incomplete_observations=180` and only
cautioned against misreading them. Those counters are the remaining defect. They have
stayed about that high on every run since.

Apollo's latest `managed_tmp_reap` run (12:04:45 EDT) reported:

```text
scanned=700 selected=198 removed=1 failed=197
ordinary_selected=198 ordinary_removed=1 ordinary_reclaimable_bytes=2237092017
dead_launch_scanned=285 dead_launch_selected=0
dead_launch_preserved_incomplete=267 dead_launch_preserved_live=3
Structured job result: ok
```

A read-only `sase disk reap -j` preview a few minutes later broke down the 287 skips:

- 267 dead-launch entries were preserved because "liveness was incomplete";
- 17 pressure candidates were preserved for the same reason;
- 3 entries were held by a live process.

Disk state at the same point:

- `df` showed 18 GB free of 193 GB (91% used).
- `~/.cache/sase/tmp/cargo-targets` held 25 GB in 42 directories. Most came from bob-cli
  launches on 19 and 20 October.
- `~/.cache/sase/tmp/agent-tmp` held 7.6 GB in 261 entries.
- The housekeeping log's `pressure_available_bytes` fell from about 31.0 GB at 09:40 EDT
  to about 19–20 GB by 12:04 EDT.

Bob-cli agents are still running on apollo, so the conditions behind this morning's
ENOSPC are coming back.

### Defect A: `sase-1bw`, where SSH sessions block the dead-launch backstop

The procfs liveness observer marks a candidate as "incomplete" in one case: a same-uid
process whose `/proc/<pid>/environ` or `cwd` it can't read, and that started after the
candidate was created (`launch_scratch_liveness.rs` `observe_unreadable`). Non-dumpable
processes such as `sshd` session children, `ssh-agent`, `gpg-agent`, and `sd-pam` meet
that description. So one new SSH login hides every older scratch directory from the
backstop until that login ends.

Apollo currently has six such processes owned by `bryan`:

| Process | Started (UTC) |
| --- | --- |
| `sd-pam` | 9 Oct |
| `ssh-agent` | 9 Oct |
| `npm root` | 16 Oct |
| `gpg-agent` | 17 Oct |
| `python3` | 20 Oct 11:58 |
| `sshd` (pid 3465998) | 20 Oct 13:27 |

This also defeats parts of `sase-1n8`:

- **`sase-1n8.4`:** monitor-settlement reclaim uses the same observer. Today its log
  shows that the starter target `gh_sase-org__sase-ws10-261020_091901` (created 13:19
  UTC) was skipped with `3465998: environ unreadable`. Two later targets, created after
  13:27 UTC, were removed. That is exactly the predicted split.
- **`sase-1n8.5`:** the emergency pressure age only helps entries the observer reports
  as complete. All 17 pressure candidates are incomplete.

`sase-1bw` was filed on 27 September by `sase-1bf.land`. Its description already
proposes a design: a non-dumpable process whose parent chain reaches a different-uid
ancestor before any same-uid ancestor cannot have inherited the launch environment. It
is size large, `READY`, and unclaimed.

### Defect B (new): read-only test vaults make removal fail

Of the 261 agent-tmp entries, 222 contain at least one directory the owner can't write.
All 295 such directories follow the same pattern:
`bob-cli-complete-vault-<pid>-<ns>-<n>/vault`, with mode `0555` and `0444` files. No
other kind of non-writable directory appears. For example:

```text
agent-tmp/gh_bobs-org__bob-cli-ws11-261013_085111/
  bob-cli-complete-vault-3217142-1791896771823491810-3280/vault   dr-xr-xr-x  2026-10-13
```

The age reaper removes directories with `fs::remove_dir_all` (`managed_tmp.rs`
`remove_snapshot`). That cannot unlink entries inside a `0555` directory, so each run
selects about 198 old entries, removes 1, and counts the rest as failures. No bead
tracks this.

**Confidence: likely, not proven.** The per-entry `removal_errors` are not logged, so
the actual failure message was not seen. The counts and modes fit, and the only entry
removed in the latest run was a `gh-diffs` entry.

The fix has two sides:

- **sase-core:** before removing a tree the reaper owns, add owner write permission to
  its directories. The reaper should not follow symlinks and should stay inside the
  managed root. Go module caches produce the same `0555` pattern, so this is useful
  beyond bob-cli.
- **bob-cli:** tests should restore permissions on teardown. Bob-cli's source was not
  opened. The directory names are the evidence.

### Defect C: job statuses hide reaper failures

Two jobs report success while failing:

- `managed_tmp_reap` reports `Structured job result: ok` with `failed=197`.
- `disk_pressure` reports `no_op` after a failed owner step. This is the audit's
  finding, and it is unchanged: `sase_chop_disk_pressure.py:126` emits
  `reason="pressure"`, and `chops/sdk.py:306` maps any reason to `no_op`.

`disk_pressure` also still sends its notification (`:89`) before calling `run_disk_reap`
(`:99`). On a truly full disk, a failed notification write could prevent the reclaim the
job exists to run. `artifact_run_prune` failed exactly that way at 04:50 EDT.

These are small fixes that belong with defects A and B. Without them, the reaper problem
stays invisible to anything that reads structured job results. The audit attached this
work to `sase-11h` as a note. That epic's last phase has been stuck since 16 September
on unrelated selection-health failures, so a new task or tale is a better home.

## Notes on the other findings

**`sase-1nb` (cleanup serialization) blocks more than the audit says.** Kill and dismiss
payloads serialize the agent being cleaned up, and they also serialize the entire
`agents_with_children` snapshot. Four call sites do this: `_kill_procs.py:96` and
`:187`, and `_dismissing.py:282` and `:439`. So while any loaded agent has a non-empty
`wait_epic_follows`, kill and dismiss likely fail for every agent in that TUI, not only
the waiting one. Apollo currently has `95.w1` waiting with `wait_for_epics_of: ['95']`.
The fix the audit proposes is right: a lossless encoder and decoder at the shared bundle
boundary. Its size estimate (medium) is right too.

**`sase-1na` (doctor).** CI runs only scoped doctor checks
(`sase doctor -C llm.default -j`), so CI is unaffected. Full `sase doctor -j` is broken
on any host with the research-artifacts plugin installed. The fix is to pass
`raise_on_error=True` at `checks_config_macros.py:591` and classify unbound template
arguments explicitly. That is the smallest well-understood change in the set.

**`sase-1nc` (GC freezes).** The problem survived a TUI restart. Athena's newer instance
`8f5fc7b8` had idle gen-2 collections of 10–13 s within about an hour of the 32 s
incident on instance `d2b7cd41`. Apollo is milder: its active stall log has one
collection of 2 s or more (2.29 s). The audit's advice to measure allocation and
retention before tuning thresholds is right. `sase-1ez` already did the cheap policy
work. `sase-1f3`, the post-`sase-1ez` acceptance soak, never ran. Plan `sase-1nc` as an
epic that runs `sase-1f3`'s measurement as its first phase, rather than leaving two
parallel beads.

**Publication backlog.** This is real, has existed since at least 14 September
(`sase-10x`), and keeps growing. Its impact:

- commit-page agent links are dead;
- model attribution covers only 31% of October sase commits (`sase-10x` evidence), which
  blocks the per-model statistics view;
- most finalizers report "success with warnings".

It is not destroying data. Local hoods remain, and artifact-run deletion is preview-only.
The audit's recovery recipe is sound: time one transaction first, fix the measured
cause, then retry in bounded batches. Do not use a blanket `--retry-quarantined`.

The audit routed this work to `sase-11o.2`. That phase's own notes say it has been
blocked since 16 September on a separate design problem: the full reconcile builds one
unbounded all-hoods payload. Close or supersede `sase-11o` and plan a new
investigation-first epic.

**Artifact-link endpoints (`sase-1c5`).** The failures continue every tick on both
hosts. Most of the cost is wasted housekeeping work and links that never converge; users
see little of it. `sase-1c5` plus the audit's evidence is already precise enough to
implement. `sase-12y.4`, the core wheel floor, is unrelated and also stale. Pick up
`sase-1c5` directly.

## Not worth addressing now

- **The audit's "signals not promoted" table.** Agree with all of it. The gateway 504s
  already have an owner (`sase-1j1`, in progress). The three `-7` (SIGBUS) job exits
  deserve a core dump the next time they happen, not a fix now. Update exit codes,
  Telegram edit misses, name-reuse failures, apollo workspace #14, and scheduler log
  size need no action.
- **Attributing the "unattributed 192.7 GiB" bucket.** `sase-1n8` already found the
  producer. Better owner attribution in `disk_footprint` would be nice, but it would not
  have prevented the incident.
- **Blanket publication retries or longer timeouts.** Agree with the audit: both hide
  the fault rather than fix it.

## Ranked list: what to fix

1. **Make apollo's tmp reaper actually reclaim space** (`sase-1bw` plus new defects B
   and C).
   - **Why first:** it is the only item that can take a host down again soon. Apollo
     has 18 GB free while 25 GB of cargo targets and 7.6 GB of agent TMPDIRs are
     blocked by defects A and B. It also undercuts `sase-1n8.4` and `.5`.
   - **Shape:** a small tale now for defect B (owner-write before removal) and defect C
     (truthful `managed_tmp_reap` and `disk_pressure` status, reap before notify). An
     epic plan for `sase-1bw`'s design, including the `sudo`/setuid edge cases its bead
     lists.
   - **Stopgap until then:** the backstop stays blocked for directories older than the
     newest live non-dumpable process, currently the 13:27 UTC `sshd` session. Ending
     long-lived SSH sessions lets the next hourly pass reclaim more, but `ssh-agent`
     and `gpg-agent` remain.
2. **`sase-1nb`: lossless `EpicFollowView` encoding.** Medium, confirmed, unclaimed.
   Kill and dismiss for the whole roster can fail while any agent waits on an epic.
3. **`sase-1na`: keep `sase doctor -j` running past unbound macro templates.** Medium,
   but the smallest change in the set. It restores the main diagnostics command.
4. **`sase-1nc`: TUI GC freezes.** The biggest day-to-day annoyance and a large job.
   Plan it as an epic that starts with `sase-1f3`'s measurement, then attributes
   allocation before touching GC policy.
5. **Publication backlog.** Supersede the stalled `sase-11o` with a new
   investigation-first epic. The payoff is working agent links and per-model
   attribution.
6. **`sase-1c5`: isolate invalid artifact-link endpoints.** Medium. It stops repeated
   failing work every tick and lets projection converge.

## Evidence and reproduction

All checks were read-only.

```bash
# Findings 3 and 6 reproduce on master / installed sase
sase doctor -C config.model_macros -j        # exit 1, no JSON
.venv/bin/python -I -c '...'                 # the audit's EpicFollowView snippet; both serializers raise TypeError

# Reaper state on apollo
sase disk reap -j                            # dry run: 267 + 17 "liveness was incomplete"
grep -E 'managed_tmp_reap|disk_pressure' ~/.sase/axe/lumberjacks/housekeeping/logs/output.log
grep -h launch_scratch_cleanup ~/.sase/procs/runtime/*/supervisor.log   # monitor-settlement skip on pid 3465998
find ~/.cache/sase/tmp/agent-tmp -type d ! -writable                     # 0555 bob-cli test vaults

# Current status
sase doctor -C state.agent_publication_outbox -j   # apollo: 456 quarantined, 284 retired
sase bead read sase-1bw sase-11o.2 sase-11h.4 sase-12y.4 -r "<why>"
```

Plans read: `202610/host_completion_loop_and_disk_churn.md` and
`202610/sase_1n8_landing_fixes.md`. Beads read: `sase-1na`, `sase-1nb`, `sase-1nc`,
`sase-1c5`, `sase-11o`, `sase-11o.2`, `sase-11h`, `sase-11h.3`, `sase-11h.4`, `sase-12y`,
`sase-12y.4`, `sase-1f3`, `sase-1ez`, `sase-10x`, `sase-104`, `sase-1bw`, and `sase-1n9`.
