# What was athena doing at 07:57 on 2026-10-24?

**Short answer: athena ran out of RAM and spent the morning swapping. This isn't an
emergency, but some of it is worth fixing.** Too many memory-hungry jobs started at
once: two full sase pytest-xdist suites (24 workers at about 1 GB each), Rust builds for
bob-cli, a batch of xelatex renders, and about 28 SASE agent runners. Together they asked
for more than the 62.7 GB of RAM. The kernel pushed about 33–39 GB into swap, and that
swap is a partition on the same NVMe as `/`. So the box ended up waiting on disk, not
CPU. The load average of 58 counts processes stuck in uninterruptible disk wait (D
state) as well as processes using CPU. Over the same hour, CPU usage averaged no more
than about 60%.

Nothing is damaged. The kernel has killed nothing (`oom_kill = 0` since boot),
temperatures are normal, and the box recovered by itself. At 08:19 the load was 15,
swap use was down to 20 GB, and IO pressure was down to ~2%.

Three things are still worth your attention:

1. **SSD write volume.** The root NVMe has had 13.9 TB written in 8.9 days, which is
   about 1.5 TB/day. That's high for a Samsung 970 PRO 1TB (warranty rating 1,200 TBW).
   Check its SMART wear counter.
2. **Waste from parked agent runners.** About 20 idle runners use ~2.2 cores and ~300 MB
   of RAM each. Because of a stuck bead read-model cache, each one also writes about
   67 MB/min to SQLite and then throws the result away. I filed this as **sase-1nw**.
3. **How these spikes happen.** Several full test suites, Rust builds, and LaTeX batches
   can run on one 64 GB host at the same time, and swap shares a disk with everything
   else.

## What the screenshot shows

| htop field          | Value                         | What it means                                                        |
| ------------------- | ----------------------------- | -------------------------------------------------------------------- |
| Load average        | 58.14 / 37.66 / 25.95         | Rising fast over the last 15 minutes; counts D-state waits, not just CPU |
| CPU bars            | 80–98% on all 64 threads      | A brief all-core burst (rustc at 533%, the pytest workers, xelatex)   |
| Mem                 | 45.5 G / 62.7 G               | Doesn't look full, because ~19 GB is page cache the kernel keeps refilling |
| **Swp**             | **32.8 G / 64.0 G**           | The real problem: half of swap in use                                 |
| `kswapd0`           | 45.6% CPU                     | The kernel's page-reclaim thread working hard                        |
| `kcompactd0`        | 34.2% CPU                     | Memory compaction (hunting for contiguous pages under pressure)       |
| `tailscaled`        | 215% CPU                      | A short spike (see below), not a trend                                |
| Several `python3.14` / `xetex` rows | state `D`     | Blocked on disk IO                                                    |

## What was actually using the memory

Snapshot at about 07:59 EDT, grouped from `/proc/*/status` (resident RSS plus swapped-out
VmSwap):

| Category                           | Procs | RSS (GB) | In swap (GB) |
| ---------------------------------- | ----: | -------: | -----------: |
| pytest-xdist workers (sase_18 `-n 14`, sase_12 `-n 10`) | 24 | 23.7 | 4.4 |
| SASE agent runners (`run_agent_runner.py`) | 28 | 8.4 | 8.8 |
| rustc / clippy (bob-cli builds)    | 3     | 5.8      | 0            |
| `sase_job_*` routines              | 8     | 2.9      | 0.1          |
| ACE TUI                            | 1     | 2.7      | 0            |
| sccache                            | 3     | 0.4      | 1.1          |
| Everything else                    | —     | ~4.1     | ~2.7         |
| **All processes**                  |       | **48.0** | **17.1**     |

That accounts for 17 GB of the 31 GB swap in use at that moment. Most of the rest is
**`/tmp`, which is a 32 GB tmpfs holding 12 GB of files**. They're all leftover agent
scratch (`sase_v018_verify` 1.6 G, `sase12_ci` 943 M, `exleg` 892 M, `cargo-install*`
870 M, several `release-core-floor*` and `*-wheel-venv` dirs). Since tmpfs lives in
RAM, untouched files there get pushed to swap. Only 2.8 MB of tmpfs was still resident,
so essentially all 12 GB was sitting in swap. Another ~3.4 GB was SwapCached.

Committed virtual memory was 90 GB against 62.7 GB of RAM, so the box was relying on
swap well before the spike.

## Why the load hit 58 and the box felt slow

- Swap is a 64 GB partition (`nvme1n1p3`) on **the same disk as `/`** (`nvme1n1p2`).
  Swap-in, swap-out, builds, tests, git, and the ext4 journal were all competing for
  that one drive.
- `iostat` on nvme1n1 at 07:59: ~6.8k reads/s (45 MB/s), ~4.9k writes/s (246 MB/s),
  51 flushes/s, **average write wait of 48 ms with a queue of about 250**. For a 970 PRO
  that is saturated.
- Pressure stall info (PSI), 60–300 s averages: **IO "full" at 13%**, meaning all
  non-idle tasks were stalled on IO 13% of the time. Memory "full" was 1–3%.
- `vmstat` showed 2–23 processes blocked at a time, iowait at 11–17%, and CPU about 50%
  idle. In other words, CPU wasn't the bottleneck.
- The D-state processes were waiting in `jbd2_log_wait_commit` (ext4 journal commits) and
  `folio_wait_bit_common` (page reads, including swap-ins).
- The second NVMe (`nvme0n1`, another 970 PRO 1TB mounted at `/mnt/hades`) was
  **completely idle**.

## Timeline (node_exporter / Prometheus on athena)

Hourly mean/max for today (EDT):

| Hour | Load (mean/max) | Swap used GB | Swap-in MB/s | IO full % | CPU busy % (5 min avg) |
| ---- | --------------- | ------------ | ------------ | --------- | ---------------------- |
| 00–02 | 3–4 / 7         | 17           | 0            | 1–4       | 5–6                    |
| 05   | 9 / 19          | 18 / 24      | 1 / 5        | 1 / 4     | 13 / 24                |
| 06   | 17 / 48         | 22 / 31      | 5 / 15       | 4 / 9     | 24 / 38                |
| 07   | 20 / 58         | 23 / 37      | 4 / 38       | 4 / 20    | 27 / 58                |
| 08 (to 08:02) | 46 / 77 | 32 / 39    | 36 / 45      | 16 / 19   | 56 / 62                |

After that it cleared as the sase_18 test run finished: load 25.8 at 08:07 and 15.0 at
08:19, with swap at 25 GB and then 20 GB. For comparison, Oct 22 was a quiet day: mean
load 2.6, max 7.8, swap flat at 13.4 GB. Oct 23 had a smaller version of the same spike
(load max 39, swap max 35 GB).

## Things that are fine

- **No OOM kills.** `/proc/vmstat oom_kill = 0` across 8.9 days of uptime.
- **Temperatures.** Threadripper 3970X under load: Tctl 82.8 °C, CCDs 62–80 °C (Tjmax
  is 95 °C). NVMe composite temperatures 42–48 °C against an 80.8 °C limit. The
  `temp1 … ALARM` lines from `sensors` are unconfigured limit registers, not real alarms.
- **tailscaled.** The 215% in the screenshot was a burst. A minute later it was at
  0–10%, and its lifetime average is ~4% of one core (3 h 40 m of CPU over 3.7 days).
  Tailnet traffic was tiny. The burst most likely came from your own traffic over the
  tailnet (the htop session and the screenshot upload) while the CPUs were contended.
- **Disk space.** `/` is 61% used (339 GB free). `/mnt/hercules` is 60% used.
- **Not checked:** the kernel log. `journalctl -k` returned nothing to the `bryan`
  user, so I couldn't rule out NVMe or hung-task messages. To check it yourself:
  `sudo journalctl -k --since -12h | grep -iE 'nvme|blocked for more|I/O error'`.

## Worth acting on, ranked

### 1. Check the root SSD's wear, because it's taking ~1.5 TB/day of writes

`/proc/diskstats` for nvme1n1 since boot (8.9 days): **13.9 TB written, 18.7 TB read**.
Daily writes from Prometheus:

| Day   | 10-15 | 10-16 | 10-17 | 10-18 | 10-19 | 10-20 | 10-21 | 10-22 | 10-23 | 10-24* |
| ----- | ----: | ----: | ----: | ----: | ----: | ----: | ----: | ----: | ----: | -----: |
| Written GB | 815 | 2,150 | 1,499 | 1,231 | 1,889 | 2,327 | 1,057 | 167 | 1,864 | 2,263 |
| of which swap-out GB | 23 | 234 | 96 | 79 | 156 | 253 | 11 | 0 | 142 | 244 |

\*The 10-24 column is the 24 hours ending at about 08:15.

Swap accounts for only 10–15% of it. Most writes come from ordinary agent work: Rust
target dirs and sccache, venvs, test runs, and git. At this rate the drive would write
its full 1,200 TBW warranty rating in roughly two years, and it already had unknown
prior wear. Run:

```bash
sudo smartctl -a /dev/nvme1n1 | grep -iE 'percentage used|data units written|media|error'
```

If "Percentage Used" is already high, move build- and test-heavy workspaces, or at least
swap, to the idle `nvme0n1`.

### 2. Stop running two full test suites and Rust builds at the same time

The spike came from concurrency. In the same ten minutes there were two full sase
`pytest -n 14` / `-n 10` runs (about 1 GB per worker, so ~24 GB), bob-cli `cargo test`
plus clippy (clippy-driver alone reached 6.2 GB), and a dozen or more xelatex renders
from one bob-cli agent. Some ways to cut that down:

- Cap or serialize full-suite runs host-wide. One full suite at a time, or fewer xdist
  workers when memory is low.
- Watch for host memory headroom, not just CPU slots, before admitting heavy jobs.

### 3. Move swap off the root disk, or add zram

Swap competing with `/` on one NVMe is what turned memory pressure into load-average
pressure. The simplest fixes:

- A swapfile on `/mnt/hades` (the idle 970 PRO) with a higher priority than the
  current partition.
- zram with a few GB of compressed swap in front of the disk partition.

Either way, swapping stops blocking every git, journal, and build write on `/`.

### 4. Parked agent runners cost ~2.2 cores, and each one churns SQLite (filed as sase-1nw)

At 08:14 there were 20 `run_agent_runner.py` processes with no child agent. They are
epic phase workers waiting on earlier phases (`wait_for_dependencies`) or waiting for a
runner slot. Over a 30 s sample they used **2.23 cores combined**, and each holds about
300 MB RSS. The older ones (started Oct 19–20) have each used 4–5 hours of CPU while
sitting there. Active runners also grow to 1–2 GB, which ends up in swap while their
agent CLI runs.

I traced one of them (PID 1950974) for 65 s. It made **32,592 `pwrite64` calls totaling
67.4 MB, all into the bead read-model WAL**:
`~/projects/github/sase-org/sase/sase/repos/beads/.git/sase/bead-read-model/bead-read-model-e3b0c44298fc1c14.sqlite-wal`.
The WAL is then unlinked without ever being merged into the database. Over its lifetime
that runner has written 21.7 GB, and 20.75 GB of it was cancelled before reaching disk.
The cache file itself hasn't changed since **Oct 16 10:20**. Its metadata still says
`crate_version 0.40.0`, while sase-core-rs 0.42.3 is installed. sase-core's rule is that
a version mismatch makes "the next read rebuild", but the rebuild apparently rolls back
every time, so every bead reader pays for a full replay plus a discarded write. Across
all runners this was about 19.7 MB/s of writes (15.7 MB/s cancelled, ~3.9 MB/s actually
reaching disk), plus a WAL create and unlink per runner per minute on the ext4 journal
that the D-state processes were waiting on.

This doesn't cause the spikes by itself, but it is pure overhead that is always running.
Filed as **sase-1nw** (bug, large). The bead includes reproduction steps and a
hypothesized mechanism (`drop_cache_file` invalidates in place, then
`rebuild_from_replay` loses the generation CAS and rolls back). That mechanism comes
from reading the code and isn't verified yet.

The quick fix is unverified, but probably harmless: delete that one cache file while
nothing is reading it. It's a derived cache, so the next reader should rebuild it.
Whether the rebuild then sticks would also test the mechanism.

### 5. `/tmp` is a RAM-backed tmpfs holding 12 GB of agent leftovers

sase-zn.1 moved `SASE_TMPDIR` off tmpfs, but agents still create ad-hoc scratch
directly in `/tmp`: release proofs, CI venvs, `cargo install` temp dirs, and git
tarballs. Nothing cleans it up until a reboot, so it slowly fills swap. Look at what's
there (`du -xsh /tmp/* | sort -rh | head`) and remove the old `sase*`/`release-*`/
`cargo-install*` dirs. Longer term, either point `TMPDIR` for agents at disk-backed
scratch or have the managed-tmp reaper cover `/tmp`.

### 6. The ACE TUI uses ~1.6–1.9 cores all the time

The TUI process in the screenshot (`sase tui --restart-service`, started 06:03) had used
3 h 07 m of CPU in under 2 hours and held 2.7 GB RSS (20 GB virtual). Its replacement,
started 07:58, used 1.87 cores in my sample and grew to 3.1–3.6 GB RSS. This overlaps
with the GC-freeze work (sase-1nf.13 is closed, sase-1nf.14 is in progress, and sase-1nc
is open). A 3 GB Python heap that has partly been swapped out will stall badly on a full
GC, so the swap pressure described above likely makes those freezes worse.

### 7. Minor: one waiter that may be stranded

Runner PID 3441838 (phase sase-1nf.14) is waiting on agent and bead **sase-1nf.13**. That
bead closed at 07:11 EDT, and the runner was still waiting nearly an hour later. The
sase-1nf.13 agent's last run ended SUCCESS with a `shell-handoff:monitored` exit, so its
session may still be legitimately open. ACE's new stranded-work flags (c793bff54b) are
the right place to confirm.

## How this was measured

All commands were run over `ssh athena` between 07:59 and 08:19 EDT, read-only:
`uptime`, `free`, `vmstat 1 5`, `/proc/pressure/*`, `/proc/meminfo`, `/proc/vmstat`,
`/proc/swaps`, `iostat -dxm 5 2`, `/proc/diskstats`, `df`, `sensors`, `tailscale
status/netcheck`, per-process `/proc/<pid>/{status,io,stat,cmdline}` aggregation,
`py-spy dump` on two runners, a 65 s `strace` of one parked runner (fd-to-path write
accounting), a read-only `immutable=1` SQLite read of the read-model `meta` table, and
range queries against athena's local Prometheus (`node_exporter`).
