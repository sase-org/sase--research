---
narration: 1
title: Bead History Cost and Lossless Archival
source: research:202610/bead_history_cost_and_lossless_archival/bead_history_cost_and_lossless_archival__final.md
source_blob: 55637b586748f28c9c70ff7bfa231268c3d2f9d0
date: 2026-10-06
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## Does bead count matter?

Yes. Every bead read and write replays the entire event store. Looking up one bead costs roughly the same as summarizing everything. The deciding variable is total events and bytes, rather than the number of open beads.

Today's store has 7,034 beads, spread across 2,108 stream files and about 48,400 events. Through the Python binding, one lookup takes 0.58 seconds. Doubling the real store raises that to 1.28 seconds. At 4 times today's size, it takes 2.70 seconds.

Commands multiply that cost. A write does 3–5 replays, then rewrites and commits a 20.8 megabyte derived projection. Its local cost that grows with history is about 3–4.5 seconds today. At 4 times the history, that becomes about 16–21 seconds.

The terminal user interface has another problem: repeated replays and an inefficient grouping loop. Its Beads pane refresh costs 2.8 seconds today, with an estimated 48 seconds at 4 times the history.

These measurements establish the scaling problem. Absolute timings vary with host load. Future growth dates and proposed improvements remain estimates.

## Why archiving comes later

Closed beads account for 91.6% of the store. Moving closed history out of the replay path sounds sensible. But measured physical archive gains range from 1.6 to 6.8 times, depending on the cutoff. Those gains shrink as new history accumulates.

Archiving also crosses relationships that the application still needs. Live beads depend on closed beads. Closed phases remain inside live epic streams. And closed does not mean immutable: 2,899 events reached 968 beads at least 7 days after closure. A read-only archive would break existing behavior.

Compression is useful for backups, but it does not address this latency problem. Opening and reading all stream files takes just 15 milliseconds, about 3% of replay time. The expensive work is parsing, validation, and rebuilding state.

About 40% of replay time is removable waste. A completed migration gets checked again. Parsed data gets copied and validated repeatedly. Eliminating that work should reduce replay from about 480 to about 290 milliseconds. That still leaves history-dependent work.

Some delays sit outside the store altogether. Audited reads take 5–8 seconds. Rescanning an artifact-link outbox accounts for 2.9 seconds of that. Git storage growth is dominated by the derived projection, rather than canonical events.

## The recommended solution

Change the goal from fewer beads to hot-path latency that is independent of closed history. Keep every canonical event unchanged and recoverable. Preserve old identifiers, dependencies, search, duplicate checks, and history. Derived files may be regenerated. Git history must remain intact.

First, remove measured waste. Fix the outbox collision check and the Beads pane grouping and refresh behavior. Remove redundant replay work. Use one replay per command, and pack the host's hidden clone.

Second, add a disposable, validated read cache in the Rust core. It stores current state and relationship indexes. Unchanged history needs no replay. Newly appended events can update the cache only when their ordering and integrity satisfy strict conditions. Otherwise, rebuild from the complete event store.

This makes the cache an acceleration layer, never the authority. Prove that cached results match full replay, including incoming merges and backdated events. Expected warm reads are tens of milliseconds, but no cache prototype has confirmed those targets yet.

Third, stop committing the full derived projection on every mutation. Migrate change detection first, so existing views keep refreshing correctly.

Finally, physically seal old streams only when explicit size or speed thresholds justify it. Preserve their bytes and checksums. Keep accepting later writes through overlays, and prove replay equivalence before sealing.

The recommendation is cache first, projection cleanup next, and physical archiving only when needed. Preserve information while removing repeated work from everyday operations.
