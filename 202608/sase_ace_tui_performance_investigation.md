# `sase ace` TUI performance investigation

**Date:** 2026-08-27  
**Runtime inspected:** `sase` 0.16.0+1638.g5cc5da03a, `sase-core-rs` 0.32.8  
**Scope:** current and rotated ACE performance logs, an August 14 instrumented trace, live-process state, and the Python/Rust paths implicated by those measurements.

## Executive summary

The TUI is slow because several individually expensive subsystems now amplify one another:

1. ACE repeatedly reconstructs a scanner-shaped snapshot of hundreds of agents. Among loads slow enough to be logged, disk/index work has a median of 2.62 seconds and a p95 of 9.75 seconds; Python preparation and UI application are normally only about 0.17 seconds combined.
2. The artifact-index "read" path opens SQLite read/write, runs schema DDL, and rewrites the schema-version row on every connection. Concurrent refresh, notification, launch, and delta jobs therefore contend on the same 186 MB database. Tier-1 revalidation is particularly pathological: on August 27 its slow-load p95 was 53.9 seconds and its maximum was 373 seconds.
3. Textual eagerly mounts a large hidden widget tree. A stall captured while the Agents tab was active contained 874 asyncio tasks, including 847 widget message pumps and hundreds of Markdown table/paragraph/list widgets. The current process was using about 2.5 GB RSS and 140% CPU at one observation point.
4. Several keystroke, countdown, notification, and worker-completion handlers still perform synchronous repository discovery, Git calls, configuration loads, Rust snapshot reads, log scans, and relation-index builds on the Textual event loop. Captured examples blocked it for roughly 1.5–2.4 seconds.
5. Textual worker cancellation does not stop the underlying thread. The worst stall showed overlapping cancelled/replacement workers independently scanning the archived agent-name registry while other workers built relation and detail indexes. Moving work to threads preserved input safety, but did not bound resource consumption.

This explains the user-visible pattern: first paint remains fast, but the app becomes CPU- and I/O-saturated while supposedly background work runs; any synchronous UI-path lookup then turns that pressure into a multi-second freeze.

## Evidence and method

### Sources

- `~/.sase/logs/tui_agent_loads.jsonl` and `.1`: 10,420 slow-load records from 2026-08-19 through 2026-08-27.
- `~/.sase/logs/tui_stalls.jsonl` and `.1`: watchdog stack captures, including 43 events from three current-day processes during 14:50–14:57 UTC.
- `~/.sase/logs/tui_startup.jsonl`: 362 startup records from 2026-08-12 through 2026-08-27.
- `~/.sase/logs/tui_trace.jsonl` and `tui_jk.jsonl`: an instrumented August 14 ACE session.
- Live `/proc` and `ps` observations of ACE process 542237.
- Python source at main-repository revision `5cc5da03a` and the linked `sase-core` source opened through `sase repo`.

The agent-load files log only operations above the slow threshold (normally two seconds). Their percentiles therefore describe **slow loads**, not every load. Live CPU and memory figures are a point-in-time snapshot and do not by themselves prove a leak. The conclusions below rely on the agreement between timing records, captured stacks, traces, and code paths rather than on either caveat-prone measurement alone.

## Findings

### 1. Shared-store/index loading dominates normal refresh cost

Across the 10,420 slow-load records:

| Stage | p50 | p95 | Maximum |
| --- | ---: | ---: | ---: |
| Disk/index load | 2.622 s | 9.751 s | 373.139 s |
| Python preparation | 0.115 s | 0.246 s | 4.086 s |
| UI apply | 0.051 s | 0.103 s | 1.239 s |

For an ordinary slow refresh, disk/index work is therefore about 94% of the measured pipeline. Optimizing row rendering first would attack the smallest component.

The August 27 breakdown is more revealing:

| Source/kind | Slow records | Disk p50 | Disk p95 | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Auto-refresh, full | 1,665 | 2.921 s | 7.576 s | 146.650 s |
| Tier-1 revalidate, full | 92 | 3.733 s | 53.932 s | 373.139 s |
| Notification, artifact delta | 21 | 3.159 s | 10.104 s | 15.437 s |
| Startup, full | 19 | 7.728 s | 20.335 s | 21.043 s |
| Launch, full | 11 | 5.258 s | 7.950 s | 18.530 s |

Even a one-agent artifact delta can take about three seconds, which rules out visible row count as the primary cause. The delta path still opens and updates the shared index before merging the result.

Long-running sessions continuously pay this cost. Representative processes recorded slow auto-refreshes at median intervals of 16–21 seconds, despite a 60-second full-sanity interval. One session accumulated 3,457 slow full auto-refreshes in 36 hours. Current code defaults the timer to ten seconds (`src/sase/ace/tui/app.py:280-285`), with a five-second minimum load interval and a 60-second sanity gate (`src/sase/ace/tui/actions/event_refresh/_constants.py:13-19`). Dirty notifications and watcher activity are causing broad reloads far more often than the sanity pass alone would.

An August 14 trace independently confirms the shape of the work. All 21 sampled auto-refreshes were broad tier-1 loads of 276 agent records, with disk p50/p95 of 2.02/2.26 seconds. Each ended in `display_full_rebuild`; list highlighting itself took only about 0.4–0.5 milliseconds.

The provider design already anticipates a better path, but it is not active. `AgentsViewport` bounds visible and prefetched rows, and the snapshot contract carries daemon/delta metadata (`src/sase/ace/tui/data_providers/_types.py:13-62`). The factory always returns `DirectAgentsDataProvider` (`_factory.py:5-11`), which explicitly discards `search_query` and `viewport`, marks every snapshot as a full reload, and reconstructs all models (`_direct.py:11-46`).

### 2. Cached index reads still behave like writes

The current artifact index is approximately 186 MB. In `sase-core`, every `query_agent_artifact_index` goes through `open_index` (`crates/sase_core/src/agent_scan/index.rs:870-976,1961-2202`). Opening the index:

- creates the parent directory and opens a read/write connection;
- installs a five-second busy timeout;
- executes WAL, foreign-key, table, and index DDL;
- checks migration state; and
- performs `INSERT OR REPLACE` on the schema-version metadata row on every open.

Consequently, a logically read-only refresh can acquire write locks and create WAL traffic. ACE concurrently initiates auto-refresh, notification polling, launch checks, delta upserts, startup loading, and revalidation, so the five-second busy window is a credible explanation for the frequent multi-second clusters. Revalidation then stats or refreshes many stale rows, explaining its much longer tail.

The selected rows are also expensive in shape. The query can return roughly 1,000 active plus 200 recent records. It deserializes stored scanner-style JSON and reconstructs rich Python dictionaries/models even if the TUI displays only a dozen rows. At the PyO3 boundary the Rust snapshot becomes `serde_json::Value` and is recursively converted to Python objects, creating avoidable copies and allocations.

### 3. Background work is unbounded and frequently duplicated

The most severe current-day watchdog capture recorded a 5.28-second pump stall followed by a 7.42-second recovery. It contained 874 asyncio tasks, 19 asyncio worker threads, and multiple active jobs:

- two launch-provider workers were both resolving wait templates, rebuilding or validating the agent-name registry, and walking archived `done.json` files;
- another worker was building the Artifacts Agents relation index;
- another was building selected-agent detail state and resolving real paths;
- filesystem watching, notification polling, axe refresh, patch refresh, and auto-refresh were also active.

Textual's `exclusive=True` cancels the previous worker's coroutine result, but cannot terminate synchronous work already running in a thread. Rapid replacement therefore produces overlapping scans. Off-pump work keeps blocking calls away from the event loop, but it does not make those calls cheap or prevent them from competing for the GIL, SQLite, the filesystem, and CPU.

### 4. Hidden widgets impose a large steady-state tax

The same Agents-tab stall contained 847 Textual widget message pumps. The most common widget classes included:

| Widget class | Count |
| --- | ---: |
| `MarkdownTableCellContents` | 199 |
| `MarkdownParagraph` | 165 |
| `Vertical` / `Horizontal` | 151 |
| `Static` | 62 |
| `MarkdownBullet` | 55 |
| `MarkdownH3` | 21 |

Top-level layout composition mounts Agents, Axe, and Artifacts together, and `ArtifactsView` composes every descriptor pane into a `ContentSwitcher`. Thus invisible panes still own message pumps, layout state, Markdown children, timers, and subscriptions. The observed process snapshot—about 2.5 GB RSS, 27 threads, and 140% CPU—matches this architecture, although a soak measurement is still needed to distinguish fixed overhead from growth.

The August 14 keystroke trace also separates model work from Textual pressure. Across 1,111 samples, model mutation was normally below 0.15 ms, while paint p95 was 45 ms, Agents-tab paint p95 was 51 ms, and next-selection action p95 was 173 ms. A large widget/compositor surface plus saturated background workers is a better explanation than expensive selection arithmetic.

### 5. UI handlers still cross blocking boundaries

Watchdog stacks caught concrete event-loop violations:

- Link-action availability called `selected_link_subject` and `accent_and_icon_for_ref`, which rediscovered artifact providers, resolved project/sidecar stores, and invoked Git. Three examples blocked for about 1.52–1.59 seconds. A recently added `provider_source_token` cache expires after only 0.75 seconds (`src/sase/ace/tui/_artifact_tab_discovery.py:219-263`), so this expensive discovery still occurs during ordinary key handling.
- Synchronous `_refresh_notification_count` read a Rust notification snapshot and blocked for about 1.7–1.8 seconds, even though an asynchronous variant exists (`src/sase/ace/tui/actions/agents/_notification_polling.py:197-249`).
- The one-second countdown refreshed agent detail/configuration and recomputed active row/clan runtime state. Captures blocked for about 1.7–2.4 seconds.
- Axe worker completion synchronously loaded chop status and scanned the chop log tail, blocking for about 1.76 seconds.
- Startup applied a patch snapshot and built relation links on the event loop, blocking for about 1.56 seconds.
- Footer layout and modal lazy import caused separate 1.5–2.2-second hitches.

These are not the largest total cost, but they are the direct cause of frozen input. Under background CPU/I/O pressure, any normally modest synchronous operation becomes visibly catastrophic.

### 6. The regression is recent and affects readiness, not first paint

Startup telemetry shows the intended first-paint optimization is still working:

| Metric | All 362 starts p50 / p95 | August 27 p50 / p95 |
| --- | ---: | ---: |
| First paint | 0.259 / 0.399 s | 0.379 / 0.490 s |
| Agents ready | 4.558 / 8.815 s | 11.149 / 25.011 s |
| Visible data ready | 3.680 / 7.881 s | 9.852 / 23.882 s |

First paint remains below 0.6 seconds, while August 27 agent readiness is roughly 2.5–3 times slower than August 18. Index row counts increased from roughly 600–700 to a median of 782 and a p95 of 1,171 on August 27. Recent link-graph, Artifacts Agents, runtime, notification, and gate-shell work also appears directly in the captured stacks. This is correlation rather than a commit-level bisect, but it explains why a pre-existing broad-load design crossed from tolerable to consistently slow.

## Root-cause model

| Rank | Mechanism | User-visible effect | Confidence |
| ---: | --- | --- | --- |
| 1 | Repeated scanner-shaped full reloads through a contended, write-capable index path | Multi-second readiness and refresh; high idle CPU/I/O | High |
| 2 | Eager hidden widget/Markdown tree | High memory, slow layout/paint, hundreds of active pumps | High |
| 3 | Overlapping uncancellable thread workers | Sustained CPU/GIL/disk contention and long-tail stalls | High |
| 4 | Synchronous discovery/store/config/log work in event handlers | Immediate 1.5–2.4-second input freezes | High |
| 5 | General Textual rendering or row mutation | Residual frame latency | Low as primary cause |

## What would and would not materially help

Moving the remaining blocking handlers to workers, lengthening refresh intervals, adding caches, and lowering timer cadence are worthwhile containment. They should eliminate specific freezes and reduce contention, but they leave the fundamental problem intact: every event still requests an oversized mutable snapshot from a shared store, and every pane remains mounted.

Micro-optimizing Rich markup, row highlighting, or the final Python apply phase would have little impact. The trace puts these operations in microseconds to tens of milliseconds while shared loading consumes seconds.

The durable fix is to make ACE consume a compact, versioned read model rather than repeatedly acting as an artifact scanner.

## Recommended solution

Implement and enable a **long-lived Rust ACE read-model service**, using the daemon/viewport contract already present in Python, and pair it with lazy Textual pane mounting. This should be delivered in three steps:

1. **Stop the immediate event-loop violations and worker amplification.** Make keystroke/action availability purely snapshot-based; replace every synchronous notification/config/repository/log lookup with a cached value plus one guarded refresh; coalesce work by key so at most one registry scan, relation build, or agent load can run; ignore stale worker generations; and update elapsed-time labels only for visible running rows at a lower cadence. Treat full refresh as manual recovery or an infrequent integrity check, not a response to ordinary filesystem activity.
2. **Move steady-state loading to a persistent Rust owner.** Initialize/migrate SQLite once, keep persistent connections, serialize and batch writes, and make reads genuinely read-only. Let filesystem events update a compact normalized row store and publish monotonic sequence-numbered deltas. The provider should apply search/filter/order in Rust and return only the requested viewport plus a small prefetch window; fetch detail, logs, relations, and Markdown only for the selected item. Python should receive typed compact rows, not recursive scanner JSON. Keep the current direct provider only as an explicit degraded fallback.
3. **Mount only what the user can see.** Lazily create the active top-level tab and active artifact pane; unmount or cache a compact model for inactive Markdown/detail panes. Recreate view widgets from that model when activated. This removes hundreds of idle message pumps and makes compositor work proportional to the viewport.

Validate the change with a 30-minute scripted soak and hard budgets: no broad auto-refresh in steady state, cached viewport/delta delivery below 50 ms p95, keystroke-to-paint below 16 ms p95, no event-loop stall above 250 ms, visible-data readiness below two seconds, and low single-digit idle CPU. Keep the existing watchdog, startup, agent-load, and `SASE_TUI_PERF=1` instrumentation as regression gates.

This solution addresses all three dominant multipliers together—shared-index churn, unbounded background work, and hidden widget cost. Tactical cache and timer fixes should land first for relief, but the daemon-backed bounded read model plus lazy mounting is the change most likely to produce a significant and durable improvement.
