# Making Agents-tab unread indicators correct and responsive

**Researcher:** cdx  
**Date:** 2026-09-30  
**Scope:** The Agents-tab unread-completion indicators, especially leader actions `,u`
(mark all read) and `,j` (jump to next unread), in the current SASE TUI.

## Executive summary

The current implementation already puts the durable notification-store mutation for
`,u` on a Textual thread worker. A new Proc would therefore move the part that is
already off the UI thread while leaving the measured stalls in place. The expensive
work is mainly synchronous projection and rendering before the worker starts, plus a
synchronous full notification-store refresh on the UI thread after it finishes.

The live incident provides unusually strong evidence:

- At approximately 06:02 local time, the TUI reported “Marked 27 completed agents
  read,” but the screenshot taken about 27 seconds later still showed 27 unread.
- During that action, the watchdog captured the worker completion callback calling a
  synchronous notification snapshot read on the Textual message pump. That operation
  reread a live JSONL store of about 3,874 lines and 18 MB.
- During a second `,u`, the watchdog captured the key handler itself spending about
  2.9 seconds in per-row patching and recursive panel-count calculation before it
  could return.
- The optimistic clear is not protected from an older notification poll that was
  already in flight. Such a poll can reconcile its stale snapshot after the clear and
  re-add the same unread identities. This is the leading explanation for a successful
  toast followed by the count returning to 27.

My recommendation is **not** to add a Proc for these actions. Keep one batched Rust
store mutation in an in-process worker, but make the UI path a small optimistic state
transition followed by one batched render. Fence stale reconciliation with mutation
generations, never reread the store synchronously from a completion callback, and
maintain an incremental navigation index so `,j` does not rebuild an O(N) projection
and cache signature for every keystroke.

## Evidence and method

I independently inspected the following first-party evidence:

- the supplied screenshot, `~/tmp/screenshots/20260930_060248.png`;
- the exact current TUI source paths for leader mode, unread state, notification
  polling/reconciliation, row patching, and unread jump candidates;
- the TUI watchdog records in `~/.sase/logs/tui_stalls.jsonl*`;
- the TUI toast log in `~/.sase/logs/tui_toasts.jsonl`;
- the normal-navigation measurements in `~/.sase/perf/tui_jk.jsonl`;
- the live notification-store size and the Rust-backed notification-store wire
  contract; and
- the project's TUI performance rules and Rust-core boundary documentation.

The screenshot identifies the running build as
`v0.17.1+1848.g28efa6f84`. The current checkout differs from that revision only by a
documentation commit, so the unread implementation under inspection matches the one
shown in the incident.

The toast log contains two especially relevant entries:

| Local time (approximately) | Event |
| --- | --- |
| 06:02:21 | `Marked 27 completed agents read` |
| 06:07:05 | `Marked 27 completed agents read` |

No corresponding persistence-error toast appears. The screenshot at 06:02:48 still
shows `27 unread` in the global status line and unread badges elsewhere. This is more
consistent with a stale reconciliation or stale presentation than with a rejected
store write.

The incident watchdog stacks make the latency diagnosis concrete rather than
speculative:

1. The first `,u` was followed by a pump hitch in
   `_complete_unread_notification_dismissal`, which invoked
   `_refresh_notification_count`, then `read_notification_snapshot`, then the Rust
   binding. The hitch recovered after roughly 2.5 seconds.
2. The second `,u` hit a roughly 2.9-second stall directly in the key event path:
   `_toggle_all_unread_done_agents_read` → `_mark_current_unread_done_agents_read` →
   `_patch_unread_completed_agent_changes` → `_try_patch_agent_row` →
   `_agent_panel_title` → `agent_panel_counts` → recursive lane-count traversal.

The normal `j`/`k` performance log is not a direct benchmark of leader `,j`, so it
should only be treated as corroborating evidence. After excluding neither scheduler
pauses nor other extreme outliers, its agent-navigation paint p95 is around 175 ms,
far above the project's 16 ms target. A dedicated leader-key benchmark is needed.

## What the code does today

### `,u`: optimistic state, synchronous projection, background write, synchronous reread

The leader-mode action calls the unread toggle and returns after displaying a result
toast (`src/sase/ace/tui/actions/agent_workflow/_leader_mode.py`). The toggle path in
`src/sase/ace/tui/actions/agents/_unread_state.py`:

1. scans the loaded roster for terminal unread agent nodes;
2. computes notification keys for those agents, including construction of a full
   agent-node projection index;
3. removes the agent identities from the local unread sets optimistically;
4. synchronously repaints every affected unread row; and
5. launches one thread worker to dismiss matching completion notifications through
   the Rust store.

The store mutation is correctly batched. The problem is what surrounds it.

`_patch_unread_completed_agent_changes` rebuilds roster/projection structures, works
out affected clans, and calls `_try_patch_agent_row` once for each changed agent.
`_try_patch_agent_row` performs a linear lookup in the agent list and refreshes panel
title and info state. A bulk clear can therefore recalculate recursive panel totals
many times. After the per-agent loop, the caller refreshes panel titles and summary
state again. The watchdog stack is exactly this path.

When the thread worker succeeds, its UI-thread callback removes matching
notifications from the local cache and then calls the synchronous
`_refresh_notification_count`. The notification mutation invalidates the process-local
snapshot cache, so this callback can force a fresh parse and projection of the whole
notification store on the Textual pump. At the time of the incident, that store was
about 18 MB. The code already has an asynchronous, guarded, coalesced refresh path;
the unread completion callback bypasses it.

The local cache removal also recomputes agent notification keys and scans cached
notifications against them. Its present nested matching structure is effectively
O(notification rows × agent keys), yet it runs on the UI callback.

### `,j`: a cache whose key is itself expensive

Leader `,j` asks for unread timed-jump candidates and then jumps to the next result.
The candidate helper in
`src/sase/ace/tui/actions/agents/_unread_jump_candidates.py` has a cache, but every
lookup constructs a large cache key. Among other values, that key contains a sorted
fold snapshot and a tuple of identity, status, start, stop, and parent fields for
every complete agent. With roughly 1,400 loaded agents, a nominal cache hit still
performs O(N) allocation and comparison.

On a miss it additionally rebuilds panel trees, examines expanded and collapsed
clans, looks through off-tab results, and sorts candidates. The leader footer can ask
the same machinery merely to decide whether `j` should be advertised. The jump path
then derives visible panel indices again. A cross-tab or collapsed target can also
trigger refiltering, fold expansion, tab creation, and a structural display refresh.

Some structural work is unavoidable when a target is hidden. Reconstructing the
entire candidate universe and its validity signature on each keypress is not.

### Why unread can come back after a successful action

Notification polling correctly performs its store read and preparation off the event
loop, but it later reconciles the prepared snapshot into the unread set on the UI
thread. The reconciliation has no operation generation, snapshot generation, or
pending-ack exclusion.

A plausible sequence is therefore:

1. poll P reads a snapshot containing 27 unread completions;
2. the user presses `,u` and the TUI clears those 27 locally;
3. worker W successfully dismisses them in the store;
4. poll P, still holding the older snapshot, applies its reconciliation and adds the
   27 identities back.

`_pending_bulk_read_agent_ids` exists, but it supports the bulk-toggle/undo behavior;
reconciliation does not use it as a stale-data fence. A stale poll can also invalidate
the undo state. This race needs a deterministic test, but it explains the observed
“success, then still 27” better than a failed write does.

There is also a cost problem in reconciliation itself: it reconstructs a loaded
roster projection and normalizes identities on the UI thread. A later watchdog record
captured this path too. Even after the race is fixed, this computation should not be
allowed to become a long pump callback.

## Critique of the Proc proposal

The intuition behind the proposal is right: expensive work should not delay input or
paint. A Proc is the wrong boundary for this particular work.

In SASE, a Proc is a durable, supervised process with registry state, logs, lifecycle,
and Procs-tab visibility. That is valuable for genuinely long-lived or operationally
important work such as an agent launch, cleanup, or Patch action. Marking an idempotent
set of notification rows read should normally finish quickly, and it does not need to
survive the TUI process.

A per-gesture Proc would add process startup, serialization, registry, logging, and
result-delivery complexity. It would also introduce more stale-state questions: the
Proc would receive a snapshot of target keys, while only the TUI can safely mutate
Textual widgets. Most importantly, it would not remove either measured hot spot:
synchronous bulk row projection happens before persistence, and synchronous snapshot
refresh happens when the result returns.

The current thread worker is already an appropriate execution mechanism for the Rust
store write. The right design distinction is not “foreground versus Proc”; it is:

- Textual model/widget mutation: short, batched, UI-thread work;
- pure data-scaled preparation: cached, incremental, or off-loop;
- durable notification mutation: one in-process background worker calling Rust;
- nonurgent reload/reconciliation: coalesced pump-free task with a thin UI commit;
- genuinely durable long operations: Proc.

Notification-log compaction is a separate concern. If it ever becomes costly enough
to require durable scheduling, it belongs to service housekeeping, not in the `,u`
gesture. The TUI should never compact the store while handling an input event.

## Requirement adjustments

I would make four changes to the informal requirements before implementation.

### 1. Define success as two separately measured moments

“Responsive” should not mean that persistence must finish within one frame. Define:

- **first-paint latency:** from key event to visible optimistic state, p95 under 16 ms
  for a warm TUI at the supported scale;
- **settlement latency:** persistence and authoritative reconciliation complete
  asynchronously, without any UI callback longer than 16 ms and preferably within
  one second under normal local load.

Errors may roll back the affected operation with a clear toast. Input and navigation
must remain responsive while settlement is pending.

### 2. Define the scope of “all”

The current Agents view can have several tabs and collapsed clans. `,u` should mean:

> Mark every currently loaded unread terminal agent-node completion read across all
> Agents tabs, including collapsed nodes, while leaving unrelated notification kinds
> unchanged.

This matches the global unread badge and the current cross-tab `,j` model. If product
intent is current-tab-only instead, the key label and global count need to say so. The
behavior should not depend accidentally on which rows happen to be mounted.

### 3. Correctness is a prerequisite, not an eventual side effect

After a successful acknowledgment, no snapshot older than that acknowledgment may
make an identity unread again. A genuinely new completion for a later turn may do so.
This requires an explicit ordering token or overlay, not timing assumptions.

### 4. Keep the first patch narrow, but recognize the shared read-model problem

Unread actions expose broader data-scaled work on the TUI pump: fleet projection,
tab descriptors, runtime-row patches, detail rendering, and notification projection
also appear in watchdog stacks. The first change should fix unread correctness and its
measured stalls. A follow-up should apply the same incremental-index and thin-commit
rules to the shared Agents read model; otherwise background activity can still make
the feature feel flaky even when the key handler is fast.

## Options considered

| Option | Responsiveness | Correctness complexity | Operational cost | Assessment |
| --- | --- | --- | --- | --- |
| Launch a Proc per `,u`/`,j` acknowledgment | Does not remove measured pre/post stalls | Higher; IPC results can also be stale | High | Reject |
| Only replace the synchronous completion refresh with an async one | Removes one measured stall | Leaves stale-poll race and bulk-paint stall | Low | Necessary but insufficient |
| Only debounce or delay row painting | May make keys return faster | Risks laggy/incorrect feedback; still O(N) later | Low | Reject as a primary fix |
| In-process optimistic transaction + batched render + fenced background persistence | Directly addresses measured paths | Moderate and explicit | Low | Recommended |
| Move all unread projection into Rust immediately | Can be fast and reusable | Large API/design change before measuring the smaller fix | Medium/high | Consider only after profiling |

The Rust boundary matters: notification mutation semantics and any cross-frontend
store generation belong in `sase_core`; Textual row indexes, batching, and widget
painting belong in the Python TUI. The current update wire returns counts and change
counts but not the exact changed notification IDs or a store generation. Extending the
core result with those fields could eliminate ambiguity and reduce rereads, but a
Python-side operation epoch/pending overlay is sufficient to fix the immediate stale
poll race while that API is evaluated.

## Proposed design

### A. Represent acknowledgment as an optimistic operation

Create a small operation record containing:

- monotonically increasing UI operation ID;
- target canonical agent identities and precomputed notification keys;
- prior unread/manual state needed for rollback;
- the notification snapshot generation observed when the operation began; and
- state: pending, settled, or failed.

On `,u` or automatic acknowledgment from `,j`, update the unread set immediately and
place the targets in a pending-ack overlay. Reconciliation must subtract targets in
that overlay from any older snapshot. A poll may commit only if its captured UI
generation is still current, or it must merge through the overlay.

On success, retain the suppression until a post-mutation snapshot is known to be at
least as new as the mutation. The strongest implementation is for the Rust mutation
outcome to include a store generation/revision and exact changed IDs. A near-term
implementation can serialize mutation and poll commits through one coordinator and
use UI epochs, as long as tests prove that an in-flight old poll cannot win.

On failure, roll back only targets still owned by that operation. Do not overwrite a
newer user action or a genuinely new completion.

### B. Make the key handler O(changed visible rows), with one aggregate refresh

For `,u`, the synchronous handler should do only:

1. get target identities from a maintained unread index;
2. update local sets and register the pending operation;
3. patch mounted target rows in one render transaction;
4. refresh each affected panel title once, and refresh global/tab/tribe/info summaries
   once; and
5. schedule persistence.

Hidden and off-tab targets require model/count changes, not per-row widget work. The
current per-agent `_try_patch_agent_row` should gain a bulk form, or at minimum accept
flags that defer panel-title and info refresh until the caller finishes. The hot path
also needs direct identity-to-agent and identity-to-mounted-row indexes rather than
`list.index` and repeated projection construction.

The toast should be emitted after the optimistic transaction has been queued for
paint, not after seconds of recursive aggregate recomputation. Its language can make
the scope explicit: “Marked 27 loaded agent completions read.” A later failure toast
can report rollback.

### C. Keep persistence in a worker, but make completion thin

Continue using one thread worker for the single Rust
`dismiss_agent_completions_matching_agents` update. Coalesce overlapping operations
when safe, while retaining operation IDs for rollback and ordering.

The completion callback must not call synchronous `_refresh_notification_count`.
Instead it should:

- apply the returned change/count outcome to the local read model when sufficient;
- remove cached rows using a precomputed hash set or exact returned IDs, avoiding an
  O(rows × keys) scan;
- schedule the existing guarded asynchronous notification refresh if a full snapshot
  is still required; and
- perform one thin UI summary update.

The existing update helper currently reduces the Rust outcome to an integer. Exposing
the full typed outcome through the local adapter would allow the UI to use counts it
already computed rather than immediately rereading the store. If tab classifications
or exact IDs are needed, extend the core wire deliberately instead of making the TUI
parse 18 MB on the pump.

### D. Replace `,j` reconstruction with an incremental unread-navigation index

Maintain a versioned `UnreadNavigationIndex` alongside roster and fold/tab state. It
should contain ordered unread terminal identities plus enough location information to
answer:

- which unread target follows the current selection;
- whether it is mounted, collapsed, or on another tab; and
- the minimal reveal plan for that target.

Update this index when roster identities/statuses, unread membership, fold state, tab
membership, or sort order change. These are already explicit invalidation points. A
keypress then performs O(1), or at worst logarithmic, target selection without
constructing an O(N) cache signature. The footer's “is `j` available?” check should
read an incremental count/boolean, not build candidates.

For a mounted target, highlight it immediately and acknowledge through the same
optimistic-operation path. For a hidden target, execute at most one structural
reprojection from its cached reveal plan, select it, and defer expensive detail
rendering. Re-capture selection/tab state after any await before applying UI results.

### E. Prevent background work from competing with the gesture

Use the existing interaction/activity gates to defer nonurgent fleet refresh,
countdown repaint, and notification presentation while an input gesture is committing
its first paint. This is not a substitute for fixing slow callbacks, but it prevents a
correctly optimized handler from being obscured by unrelated projection bursts.

Pure, data-scaled preparation can run off the event loop, but it must also be kept off
the Textual message pump. Only the final small state/widget commit belongs on that
pump. Textual widgets themselves must never be accessed by a worker.

## Verification plan

Add dedicated spans or `SASE_TUI_PERF` events for:

- `leader.unread_bulk_ack`: target lookup, local mutation, row patch, aggregate patch,
  worker queue, store mutation, and settlement commit;
- `leader.unread_jump`: index lookup, reveal/reproject, selection paint, and
  acknowledgment settlement; and
- notification poll: read/prepare duration off-loop and commit duration on-loop.

Record workload dimensions with each event: loaded agents, mounted rows, affected
rows/panels, unread targets, notification rows/bytes, and whether the destination was
collapsed or off-tab. Without these dimensions, a fast empty test can hide the
production path.

At minimum, tests should cover:

1. **Stale-poll race:** pause a poll after it reads old unread data, complete `,u`, then
   release the poll; the targets must remain read.
2. **New completion after ack:** a later completion for the same clan/turn lineage is
   allowed to become unread if its identity/version is genuinely new.
3. **Failure rollback:** fail the Rust update and restore only the operation's still-
   current targets.
4. **Repeated actions:** two `,u` or `,j` acknowledgments settling out of order cannot
   undo each other.
5. **Scope:** loaded targets across expanded, collapsed, and off-tab locations clear;
   unrelated notifications do not.
6. **Render batching:** N targets in one panel cause N row-state changes but one panel
   aggregate refresh and one global summary refresh.
7. **No synchronous store read:** assert that unread worker completion cannot invoke
   the synchronous snapshot API on the UI thread.
8. **Scale:** benchmark approximately 1,500 loaded agents and 4,000 live notifications,
   matching the observed order of magnitude.
9. **Navigation:** warm repeated `,j` presses do not build a full roster signature or
   candidate list, and cross-tab/collapsed jumps perform at most one structural
   refresh.

Acceptance targets should be p95 under 16 ms from key event to optimistic paint, no
single Textual pump callback over 16 ms attributable to the action, and zero stale
resurrection in deterministic race tests. Store settlement may take longer without
blocking input; its latency should be separately reported rather than hidden inside
the interaction metric.

## Recommended solution

Implement this in two deliberately sized stages, without a per-action Proc.

**Stage 1 — correctness and the two proven stalls:** add a pending-ack operation epoch
that fences stale poll reconciliation; batch `,u` row changes and refresh each affected
panel/global summary once; expose the Rust mutation outcome instead of reducing it
immediately to an integer; replace the completion callback's synchronous snapshot read
with a thin local update plus the existing coalesced asynchronous refresh; and make
cache removal hash-based with precomputed keys. Add the race and scale tests above.

**Stage 2 — consistently fast navigation:** replace the expensive candidate cache key
with version counters and an incremental `UnreadNavigationIndex`; let footer
availability read that index; give each target a cached location/reveal plan; and apply
the shared optimistic acknowledgment pipeline after selection. Then profile remaining
Agents-tab background projections and move or incrementally cache only the paths still
breaking the pump budget.

This design preserves instant feedback, makes successful acknowledgments monotonic in
the face of stale polls, keeps shared notification semantics in Rust where appropriate,
and limits Textual work to a single small render transaction. It addresses both the
observed “didn't work” failure and the observed slowness at their actual causes; a Proc
would address neither.
