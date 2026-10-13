# Is apollo's TUI `bus error` related to the startup slowness?

> **Research query:** The TUI keeps crashing with `[1] 3192631 bus error (core dumped)
> sase -p tui` on apollo. Could that be related to the issue in
> [apollo_tui_startup_slowness.md](apollo_tui_startup_slowness/apollo_tui_startup_slowness.md)?

## Short answer

**Not directly.** The slowness comes from CPU and GIL contention, and contention cannot
raise a bus error. The crash most likely has a separate cause: a SQLite locking bug in
the TUI process. Both problems sit on the same overloaded host and touch the same SQLite
files, so apollo's load makes the crash more *likely*. Fixing the slowness will not fix
the crash, though.

Confidence: **likely, not proven.** No core dump was saved for this crash (see
[how to confirm](#how-to-confirm-it-next-time)). Even so, the mechanism produces exactly
this signal, and I caught its precursor state live on apollo.

## What a bus error means

On Linux x86, `SIGBUS` almost always means a process touched a **memory-mapped file page
that is past the file's current end**, because someone truncated the file while it was
mapped. It is not an out-of-memory kill (that shows `killed`/SIGKILL), and it is not a
symptom of slowness.

So the question becomes: which file did the TUI have mapped, and who truncated it?

## What I found on apollo (2026-10-13, UTC)

- **The crashed TUI.** PID 3192631 started at about 13:01 and restarted in-process at
  13:54. Its last log line was written at **14:22:45**, which dates the crash to about
  14:23.
- **What a TUI has mapped from disk.** The only shared file mappings that could cause
  this are the `sase_core_rs` extension (`.so`) and SQLite `-shm` files. Those are the
  dismissed-bundle index, `agent_artifact_index.sqlite`, and the bead read model.
- **Ruled out: a rebuilt `.so`.** `sase_core_rs.abi3.so` was last written at 11:54:42,
  before this TUI started, and no process maps a deleted copy of it.
- **Ruled out: a full disk.** `/` is 79% used (42 GB free), and `/dev/shm` is empty.
- **The live clue.** The *replacement* TUI (PID 4103979) was mapping
  `~/.sase/agent_artifact_index.sqlite-shm (deleted)`, while no `-shm` file existed on
  disk. SQLite only deletes or resets a `-shm` file when no other connection holds a lock
  on it. Another process therefore believed the TUI was not connected, which means the
  TUI's locks had been silently lost.

## Why the locks get lost

The TUI process contains **two separate copies of SQLite**:

| Copy | Used by | Version |
| --- | --- | --- |
| System `libsqlite3.so` | Python's `sqlite3` module | 3.45.1 |
| Bundled inside `sase_core_rs` | Rust core (`rusqlite` with `features = ["bundled"]`) | its own |

Both copies open `agent_artifact_index.sqlite` in the same process. Rust handles the
index queries. Python opens the file directly in
`read_agent_artifact_index_schema_status` (imported by
`ace/tui/actions/_startup_loads_index.py`) and in the chat-catalog provenance reader.

POSIX file locks belong to a *process + file* pair. When either copy closes its file
handle, the kernel drops **every** lock the process holds on that file, including the
other copy's locks. A single SQLite copy tracks this internally, but two copies cannot see
each other's handles. SQLite's own docs list this as a known corruption cause ("How To
Corrupt An SQLite Database", §2.2.1, multiple copies of SQLite in one process).

After the TUI's locks are dropped, the next sase process to touch the database (an agent,
axe, a `sase tool wait` poller, or a CLI command) sees nobody else connected:

- **If it opens the database:** it decides it is the first user and **truncates the
  `-shm` file** to reset it. The TUI's mapped pages now lie past the end of the file, and
  its next access raises **`SIGBUS`**. That is this crash.
- **If it closes the last connection it can see:** it **deletes `-shm` and `-wal`**. That
  leaves the stale mapping I caught in the live TUI, and risks silently losing index
  writes.

## How this relates to the slowness report

| | Startup slowness | Bus error |
| --- | --- | --- |
| Mechanism | GIL convoy plus CPU hogs | Lost SQLite locks, then a truncated `-shm` |
| Can contention alone cause it? | Yes | No |
| Made worse by apollo's load? | Yes | Yes, indirectly |

The connection is that the race fires on SQLite opens and closes, and apollo does a lot of
both on these files. Agents, pollers, axe, and researcher TUIs all hit them, and the
slowness report's churn adds more: watcher reloads, refresh ticks, and opening a database
on every read. Slow startups produce more of those cycles. Some slowness fixes (ranked
items 1, 2, and 7) would therefore *reduce* the crash rate, but none of them removes the
bug.

## What to do

1. **Fix the root cause (code; sase plus sase-core).** Each SQLite database file should be
   opened by only one SQLite copy per process. Route the Python-side reads of
   `agent_artifact_index.sqlite` (the schema-version check and the chat-catalog reader)
   through `sase_core_rs`. This also follows the Rust-core boundary rule. Then audit the
   other Rust-owned databases for direct Python `sqlite3` access or plain `open()`/`close()`
   calls (copies, hashes, backups). A plain close drops the locks in the same way. The
   alternative, linking `rusqlite` against the system SQLite, is a packaging change that
   would hurt wheel portability.
2. **Reduce exposure meanwhile.** Do the slowness report's items 1, 2, and 7 (fewer hidden
   reloads, and stop opening the dismissed index with `create=True` on every read), and
   lower apollo's process churn (item 4).

## How to confirm it next time

- **Let apport save the next core.** Apport keeps only one crash report per executable.
  `/var/crash/_usr_bin_python3.12.1000.crash` is still there from Oct 9 (a `sase tui`
  SIGSEGV, possibly the same family but not analyzed), so today's dump was dropped. Move
  it aside with `sudo mv /var/crash/_usr_bin_python3.12.1000.crash ~/`.
- **Check the faulting address.** After the next crash, install `gdb` (it is not on
  apollo), run `apport-unpack` on the new report, and check whether the faulting address
  falls inside a `*.sqlite-shm` mapping. If it does, the diagnosis is confirmed.
- **Optional small code change:** have the TUI call `faulthandler.enable()` with a log file
  under `~/.sase/logs/`, so every fatal signal records Python stacks for all threads. The
  TUI draws on stderr, so plain `PYTHONFAULTHANDLER=1` output would be lost.
