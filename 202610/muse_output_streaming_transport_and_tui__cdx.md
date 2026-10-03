# Restoring Muse output streaming without regressing reply chunking

Researcher: **cdx**. Research date: **2026-10-03**.

## Finding

**Keep the current Muse JSONL integration and its September chunk-coalescing fix. Repair the shared subprocess reader and add a narrowly scoped live-reply refresh path in the TUI.** Streaming support still exists; I found two independently reproducible gaps that can prevent users from seeing it.

1. The shared JSONL reader can strand already-received events in Python's text buffer until the provider emits more output or exits.
2. Appending to a live reply does not mark the Agents surface dirty, and its stat-only surface token does not change. The quiet auto-refresh path refreshes file viewers rather than the reply document.

These are confirmed properties of the checked-out implementation. They are credible explanations for the symptom, but I did not capture a current production Muse run or demonstrate that they explain every observed incident. The September fix itself does **not** disable streaming.

## Scope and evidence

I conducted this investigation independently and did not read another swarm researcher's report, transcript, or findings. I inspected this checkout's implementation, relevant git history and fixtures, the linked Rust core, the installed Muse CLI's help/version, and Meta's official documentation and SDK. I ran controlled subprocess experiments and existing focused tests. I made no implementation changes and launched no paid model run.

The SASE checkout was at `598928da70fd37ef9b9ed1265fc50ed4018fbc0d`. Installed Muse reported **1.4.2 (1.4.2-R4684.1)**. The official SDK checkout inspected was at `bb44be3d36de46d2411bd9eaa4aee99006092546`.

Key source anchors:

| Evidence | Source |
| --- | --- |
| Muse launch argv and subprocess invocation | [`muse_provider.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/llm_provider/muse_provider.py) |
| Delta grouping and terminal-authoritative result | [`_subprocess_muse.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/llm_provider/_subprocess_muse.py#L252) |
| Immediate artifact/console flush | [`_subprocess_artifacts.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/llm_provider/_subprocess_artifacts.py#L133) |
| Shared reader and post-exit drain | [`_subprocess_stream.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/llm_provider/_subprocess_stream.py#L91) |
| Reply cache and UTF-8 byte offsets | [`artifact_files_cache.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/agent/artifact_files_cache.py#L225) |
| Reply renderer prefers timestamped chunks | [`_agent_display_content.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/widgets/prompt_panel/_agent_display_content.py#L209) |
| Watcher classification and routing | [`_artifact_paths.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/actions/event_refresh/_artifact_paths.py#L63), [`_watcher.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/actions/event_refresh/_watcher.py) |
| Metadata-only Agents token | [`_surface_tokens.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/actions/event_refresh/_surface_tokens.py) |
| Quiet tick updates file viewers | [`_auto_refresh_surfaces.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/actions/event_refresh/_auto_refresh_surfaces.py#L440), [`_agent_detail_state.py`](https://github.com/sase-org/sase/blob/598928da70fd37ef9b9ed1265fc50ed4018fbc0d/src/sase/ace/tui/widgets/_agent_detail_state.py#L161) |

## What the earlier fix actually changed

The provider was introduced by [`44fa7eee24`](https://github.com/sase-org/sase/commit/44fa7eee2445bc1b33742cd3ffef7f7a983110d0) on August 7. It already consumed `muse exec --json`, extracted `run.output.delta`, and preferred `run.terminal.*` text for the returned reply.

The user-recalled fix is [`a0244d7599`](https://github.com/sase-org/sase/commit/a0244d75993b74a09f054019be583c38f7f51ef7) on September 20. Before that fix, Muse sent token/text fragments to `append_stream_text()`, a helper designed for complete assistant messages. Every fragment received a timestamp and blank-line separator. That produced repeated AGENT CHAT dividers and broke words and inline code.

The fix introduced `append_stream_delta(..., new_chunk=...)`. The parser opens one chunk for a contiguous run stream, identified by `command_id`, then `run_stream.id`, then an unkeyed sentinel. Later fragments append directly to the same chunk. A matching terminal event closes it; switching streams also starts a fresh chunk. No-terminal recovery concatenates fragments within streams.

Crucially, **every delta still writes and flushes `live_reply.md` immediately**, and console output still prints with `end=""` and `flush=True`. `suppress_output=True` suppresses the console, not the live artifact. Final reply extraction continues to prefer terminal text and avoids appending that full text a second time to the deltas.

The existing grouping supports sequential streams, not a general interleaved message graph. Returning to an earlier stream after another stream opens will open another visible chunk. There is no reason to expand that policy for this repair without a capture showing such interleaving.

## Confirmed gap 1: buffered JSONL events wait for another OS readiness event

`stream_json_lines()` uses `select()` on a pipe descriptor, then calls the buffered `TextIOWrapper.readline()` **once** for each ready stream.

One read from the OS may contain several JSONL records. `readline()` returns the first record and retains subsequent records in the wrapper's internal buffer. The OS pipe is now empty, so the next `select()` reports no readiness. The loop does not consume those buffered records. Its own `stdout_buffer` only assembles partial JSON lines; it cannot see lines still inside the text wrapper.

If the first record is metadata or task lifecycle output, the later reply delta can remain unseen throughout a quiet interval. The post-exit drain eventually consumes it, producing exactly the appearance of a non-streaming provider. This reader is shared by Muse, Claude, Codex's JSONL parser, Qwen, and OpenCode.

### Controlled comparison

I used the real current Muse parser with a Python child that:

1. Writes `run.model.configured`, delta `alpha `, and delta `beta` together and flushes once.
2. Remains running for 1.2 seconds.
3. Writes terminal text `alpha beta` and exits.

At 250 ms:

| Reader | Child still running | Live reply |
| --- | --- | --- |
| Current shared reader | Yes | Empty |
| Experimental raw-byte reader | Yes | `alpha beta` |

Both ultimately returned `alpha beta`, wrote exactly `alpha beta` to the live file, and created **one** timestamp entry. The raw-byte prototype was substituted in memory only. It demonstrates the transport remedy, not a production-ready replacement; teardown/watchdog semantics were not implemented in that prototype.

A separate single-line-first probe exposed `alpha ` within approximately 20 ms, before terminal completion. Thus the current parser can stream when pipe write boundaries happen to cooperate.

Git blame places the single-read readiness pattern in May 2026, before Muse was added. This is not evidence that the September coalescing commit introduced it. It is evidence of an existing transport defect that must be fixed before claiming reliable streaming.

## Confirmed gap 2: live-reply writes lack a reliable TUI repaint trigger

The reply cache is **not** keyed only by timestamp count. `read_reply_chunks()` keys its cache jointly by `(mtime_ns, size)` of the timestamps and reply files and slices the last chunk through the current reply-file end. Appending to a single chunk can therefore refresh correctly.

I verified this against the actual parser/cache: two separated writes changed the cached chunk from `alpha ` to `alpha beta` while the timestamp file retained exactly one entry and the child remained running. The coalescing fix does not inherently freeze the cache.

The missing piece is scheduling a render:

- `_AGENTS_RELEVANT_ARTIFACT_MARKERS` contains lifecycle/metadata markers, not `live_reply.md` or `live_reply_timestamps.jsonl`.
- `artifact_path_affects_agents()` returns false for both live-reply files under a normal sharded run directory.
- `_dirty_surfaces_for_paths()` deliberately ignores artifact paths that do not affect rows.
- The Agents surface token stats project/artifact roots, the index, and refresh pulses. An append to an existing nested reply file does not change those directory metadata values.
- A quiet auto-refresh tick calls `_refresh_selected_agent_file_panel()`. `refresh_current_file()` only refreshes panels showing the Files deck; it does not repaint the reply document.

A controlled temporary project tree confirmed: after appending `beta` to `live_reply.md`, the Agents token remained identical and determinate, and both reply filenames were classified as not affecting Agents.

Other activity can accidentally repaint the reply: metadata/status changes, navigation, a sanity refresh, or the slow-tool timer. The slow-tool timer is only enabled while eligible tool sources have pending work, so it does not guarantee updates during an answer with no pending tools. This explains why a streaming problem can appear intermittent.

This is a confirmed absence of a content-change trigger in these paths, not a full mounted-TUI incident reproduction. A focused UI test should establish its precise user-visible effect before landing the change.

## Current Muse interfaces and implementation alternatives

The installed `muse exec --help` describes `--json` as JSONL event output and exposes no separate stream-enabling flag. Meta documents that same headless interface and a debug transport trace setting. Neither promises a particular number of deltas or their latency for every model/version. [Meta headless automation documentation](https://dev.meta.ai/docs/muse-code/extending), [Meta configuration documentation](https://dev.meta.ai/docs/muse-code/configuration).

There is also Muse Session Protocol (MSP) through `muse serve`. The official SDK models streaming as `item/started` followed by `item/delta`, with `item/completed` supplying the authoritative final object and `turn/completed` settling the turn. Deltas are keyed by item and field; the default field is `text`. Different fields can carry tool output or reasoning summaries, so blindly concatenating all deltas would be incorrect. The SDK's stream recipe explicitly requires at least two pieces to prove incremental delivery. Its README labels the SDK a Developer Preview. [Official protocol declarations](https://github.com/meta-models/muse-code-sdk/blob/bb44be3d36de46d2411bd9eaa4aee99006092546/schema/msp/msp.d.ts#L724), [official executable streaming recipe](https://github.com/meta-models/muse-code-sdk/blob/bb44be3d36de46d2411bd9eaa4aee99006092546/python/clients/sdk-cookbook-py/src/cookbook_recipes/recipes/stream_a_turn.py), [SDK README](https://github.com/meta-models/muse-code-sdk/blob/bb44be3d36de46d2411bd9eaa4aee99006092546/README.md).

| Approach | Assessment |
| --- | --- |
| Repair JSONL transport and focused reply refresh | Best first implementation: preserves the existing launch, usage, tools, retry, and single-turn contract. Directly addresses demonstrated gaps. |
| Only repair TUI refresh | Improves visibility when deltas already reach the live file; cannot fix buffered deltas. |
| Only repair the shared reader | Repairs artifact/console timing; can still leave a selected TUI reply stale. |
| Restore one timestamp/message per delta | Reintroduces the original word/code fragmentation and divider bug. Reject. |
| Add a speculative `--stream` flag or force a PTY | No such headless flag was found; PTY behavior adds terminal parsing complexity and does not repair repaint scheduling. Reject absent upstream evidence. |
| Migrate the whole provider to MSP | Credible future option for richer item semantics, cancellation, and session controls; significantly larger integration and validation scope. It would still need a TUI refresh path. Reserve it for measured headless limitations or broader requirements. |

## Proposed implementation details

### Transport

Replace the ordinary shared-reader readiness path with one coherent byte transport. For each ready descriptor, consume available bytes through `os.read()` or an equivalent unbuffered interface, frame JSONL records, and dispatch **all** complete records obtained. Do not mix raw reads with reads from a text wrapper that may already hold buffered data.

Maintain per-stream byte or incremental-decoder state. UTF-8 split across reads should be retained until complete, not replaced simply because a read ended. If framing in bytes, split at ASCII newline and decode complete records; flush an unterminated final record at actual EOF. Continue collecting/printing stderr according to `suppress_output`.

Remove descriptors from the readiness set at EOF, distinguish temporary `EAGAIN` from EOF, and preserve bounded draining of watchdog-reaped providers whose descendants hold inherited pipes open. Preserve existing exit-code and accepted-final-declaration handling. Cap each drain batch so a continuously busy stdout cannot starve stderr, cancellation, or teardown checks. Reuse one transport implementation for normal and teardown draining where feasible.

A tempting smaller change is to drain buffered `readline()` calls until they return no data. It addresses the demonstrated buffered-line stall, but retains the awkward nonblocking text-wrapper/UTF-8 boundary behavior. A coherent byte reader provides a clearer contract for partial JSON, Unicode, EOF, and pipe ownership.

### TUI

Introduce a **reply-content dirty signal separate from roster dirtiness**. Classify writes to the two live-reply files as changes to the appropriate selected/visible reply document, rather than adding them to the list of lifecycle markers and running the agent loader for every token.

Coalesce watcher bursts through the existing detail debouncer (150 ms) and established pump-free worker path. Read/stat/parse off the UI thread, marshal the result back, and recheck selected identity and render generation before publishing. Keep navigation immediate and avoid cancelling/restarting all header, bead, diff, and file-discovery workers for a reply append. Scope updates to visible reply content; preserve attempt pinning, fold state, scrolling, and hints.

For unavailable/missed filesystem notifications, add a bounded metadata probe for the selected live reply files on the existing cadence. Root-directory-only surface tokens cannot detect nested appends. Do not scan all historical agent artifacts or restore unconditional full Agents reloads.

Retain the existing single timestamp per contiguous run stream. Neither new timestamp entries nor filesystem refresh pulses are needed per token. Keep provider-event interpretation separate from presentation: any new reusable event/reply projection domain belongs in `sase_core` with bindings and a revision-pin update, per project instructions. Pipe handling can remain thin Python process-I/O glue; Textual debounce, selection, and rendering remain presentation code.

### Result authority and defensive cases

Preserve terminal-authoritative returned content, per-stream delta recovery when terminal data is missing, exit-code semantics, schema diagnostics, and the distinction between task-level cancellations/rejections and run failure. No stream change should create a second full answer by appending terminal text after all deltas.

Also test terminal-only replies and terminal/delta disagreement. Today `_capture_run_terminal()` stores authoritative text but does not reconcile the live file, and the reply renderer prefers existing chunks. If a current capture shows incomplete/different provisional text, reconcile the active reply block or select authoritative completed content; do not append a duplicate full answer. A model run that emits its only delta at completion cannot acquire token streaming solely from a SASE UI fix.

## Validation required before landing

The existing focused suite passed unchanged:

```sh
uv run --no-sync pytest -q \
  tests/llm_provider/test_muse_provider_stream.py \
  tests/ace/tui/widgets/test_agent_reply_muse_chunks.py \
  tests/llm_provider/test_subprocess_utf8_decode.py
```

**26 passed in 2.94 seconds.** Existing tests validate final text, chunk count, salvage, and formatting. The widget regression renders a DONE agent after parsing finishes; it does not prove that a RUNNING agent changes before terminal completion. The three checked-in Muse exec captures are short answers (`bravo`/`DONE`) with only one output delta each; they provide no production latency evidence.

Add tests for behavior, especially:

1. **Batched-record progress before exit:** a child writes metadata plus several deltas in one flush and waits for the parent to release it. Assert both deltas are visible before release. Use a handshake and generous deadline rather than relying on an arbitrary sleep.
2. **Within-chunk progress:** a second delta grows the same chunk while the timestamp count stays one; no blank lines or divider growth appear mid-word or mid-code.
3. **Selected TUI progress with an unchanged roster:** live-reply-only writes update the mounted reply without navigation or a `done.json` write and without invoking the broad agent loader. Verify unrelated agents and quiet ticks do no extra work.
4. **UTF-8/framing:** split a multibyte character, JSON line, and newline across OS writes; preserve exact output; handle many records in one write and a final line without newline.
5. **Lifecycle:** stderr bursts, normal failure, cancellation, pipe EOF, inherited open pipes, and completion-watchdog teardown retain existing behavior. Run `test_completion_watchdog_streams.py` and shared-reader provider tests because the transport has multiple callers.
6. **Navigation/presentation:** selection changes during a pending update cannot publish stale text; attempts/folds/hints and scroll position remain stable.

Then capture one current Muse run with a sufficiently long answer and timestamp raw stdout events, parser delivery, live-file growth, and visible repaint. Distinguish a transport delay from upstream emission and TUI delay. The current release should produce multiple deltas materially before terminal completion for a successful token-streaming demonstration. Store a sanitized release-keyed fixture. Run the project's prescribed verification for implementation changes; this research did not modify primary-repository code.

## Limits and decision gates

I did not demonstrate an upstream Muse regression, a missing stream flag, or a change to the event vocabulary in 1.4.2. The installed version/help establishes the available launch surface, not current model-stream behavior. I did not inspect peers' reports or existing live agents' transcripts. Controlled probes used local test children, not a production Muse session.

The shared-reader defect predates the September fix; TUI token gating also predates that fix. Therefore the report supports a repair strategy and disproves the claim that the fix intentionally removed streaming, but cannot assign a precise historical regression date. A current raw capture is the decision gate for whether JSONL provides sufficiently early output. If it does not, evaluate MSP's item-delta delivery with the same timing criteria before committing to a migration.

## Recommended solution

**Restore reliable end-to-end streaming on the existing `muse exec --json` path: fix the shared byte reader, add coalesced reply-only TUI updates, and retain `append_stream_delta()` plus one timestamped chunk per contiguous run stream.** Require tests that observe progress while the child and selected agent are still running. Confirm with a current release capture before declaring the feature restored. Consider MSP only if that capture shows headless JSONL cannot deliver incremental output early enough, or if richer session/item controls become an explicit requirement.
