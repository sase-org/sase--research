# Muse Reply Streaming: Where It Breaks and How to Restore It

_Consolidated report · 2026-10-03 · sase `master` @ `598928da70` · Muse Code
`1.4.2-R4684.1` · Rich `14.3.3`_

Sources: five independent researcher reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`,
in this directory), plus lead-researcher verification. I re-ran the disputed claims
against the code, ran pty and subprocess probes, and checked artifacts on disk.

## Bottom Line

**The Muse provider already streams, and the September 20 chunking fix is not the
regression.** Every `run.output.delta` is still written and flushed to `live_reply.md` as
it arrives. Deltas are coalesced into one timestamped chunk per run stream. Commit
`a0244d7599` changed how the deltas are framed, not when they reach disk. Two
researchers (cld, mus) confirmed this with live `muse exec` runs. All five agree after
reading the diff.

Reply streaming still looks dead because of three defects outside the Muse delta handler,
made worse by how Muse behaves:

1. **The TUI never repaints when `live_reply.md` grows. This is the primary cause.** The
   inotify watcher sees the writes but deliberately classifies both reply files as
   ignorable. No polling path repaints AGENT REPLY for a running agent, except a 5 s
   tick that runs only while a tool call is pending. Muse writes its reply *after* its
   last tool call, so the reply stays on disk unseen until some unrelated event
   repaints the panel. That can be 27–60 s or more later. (Found by cdx, cld, and grk;
   I verified it.)
2. **The shared JSONL reader strands lines that are already buffered.** The reader calls
   `readline()` once per `select()` wakeup. Any extra lines from the same pipe read sit
   in Python's text buffer until the provider writes again. Muse emits deltas in
   bursts, which is exactly the case that triggers this. (Found by cdx; I reproduced
   it. The fix pattern already exists in the same file.)
3. **On an interactive terminal, every delta becomes its own console line.** Under the
   `provider_timer` Rich `Live` display, each `print(text, end="", flush=True)` is
   emitted as a separate line. The "chunked poorly" symptom therefore never went away
   on the CLI console. (New finding: verified in a pty. It contradicts gem and settles
   mus's open question.)

Context that shapes expectations:

- Muse writes **no text alongside tool calls**: 0 of 109,416 tool-call turns had text.
  Its reply appears only in the final ~2–6 s of generation.
- The **September 23 `muse_synchronous_shell` change** (`28b3c1bab2`) removed the
  mid-run status messages that used to land in `live_reply.md` during a run. That is
  the likely source of the "it used to stream" memory.

**Recommendation:** Keep `a0244d7599`. Then:

- **Phase 1:** a selected-agent live-reply follow in the TUI. It is event-driven,
  throttled, and has a polling backstop.
- **Phase 2:** drain buffered lines in `stream_json_lines`.
- **Phase 3:** stop the per-delta console flush under Rich `Live`.
- **Optional:** show Muse reasoning summaries as mid-run progress.

Details are in the [Recommended Solution](#7-recommended-solution) section.

---

## 1. Timeline: What the User Remembers vs. What Changed

| Date (2026) | Commit | Effect on visible streaming |
| --- | --- | --- |
| 05-28 | `f41cfe0948` "filter artifact refresh routing" | Writes to `live_reply.md` stop dirtying the Agents surface. The commit's own test lists `live_reply.md` as now ignored. This was a deliberate perf fix, and it predates Muse. |
| 08-07 | `44fa7eee24` | Muse provider added. Each delta goes through `append_stream_text`, so every token fragment gets its own timestamp, `\n\n` separator, and console newline. |
| 09-20 | `a0244d7599` | Adds `append_stream_delta(new_chunk=…)`. One chunk per run stream, keyed by `command_id`, then `run_stream.id`, then a sentinel. Same bytes, same timing, about 25 fewer dividers per reply. |
| 09-23 | `28b3c1bab2` | `muse_synchronous_shell` (default on). No background waits, so Muse no longer ends turns mid-run, and mid-run status messages disappear. |
| 10-01 | `977b3dd501`, `e9221a88ea` | Transient-failure retry; module split. No change to streaming. |

**Why it "used to stream."** Two effects stacked, and neither was token streaming in the
TUI:

- **Mid-run messages (cld).** Before September 23, a Muse run produced short turn-ending
  messages while background commands ran. I verified one run on disk:
  `ace-run/202609/20/20260920171616` has four `live_reply_timestamps.jsonl` entries
  spread over 54 minutes ("Rebuild running; continuing once it completes.", …). Each
  was on disk mid-run, so any incidental repaint showed progress.
  - Sessions with two or more messages fell from **10.2% to 0.7%** after the change
    (cld's corpus of 1,776 sessions).
- **The divider explosion (grk).** Before the fix, a late repaint showed many
  timestamped fragments, which *looked* like a streamed transcript. After the fix, the
  same late repaint shows one intact block. That reads as "streaming died."

The chunking fix landed three days before the synchronous-shell change, which makes it
the natural suspect. It is innocent.

## 2. How the Pipeline Works Today

```
muse exec --json ──stdout JSONL──▶ stream_json_lines()            [_subprocess_stream.py]
                                    └ select() + ONE readline() per wakeup   ◀── defect 2
                                 ▶ _process_muse_json_line → _stream_output_delta
                                    └ append_stream_delta()        [_subprocess_artifacts.py]
                                        ├ live_reply.md        (append + flush per delta)
                                        ├ live_reply_timestamps.jsonl (one entry per new chunk)
                                        └ print(text, end="", flush=True) ◀── defect 3 (TTY+Live)
TUI (ACE)
  ArtifactWatcher (IN_MODIFY, 50 ms coalesce) → _on_artifact_change
     └ artifact_path_affects_agents(live_reply.md) == False → targets = ∅ → return ◀── defect 1
  AGENT REPLY repaints only on: selection change, agent loads / marker deltas,
     header enrichment, slow-tool tick (5 s, only while a tool call is pending),
     300 s sanity reconcile
```

| Layer | Status | Evidence |
| --- | --- | --- |
| Muse CLI emission | Streams; the CLI controls the pace | `--json` is the only stream surface; there is no verbosity or stream flag (cdx, cld, mus, grk). |
| Shared reader | **Defect 2:** buffered lines wait for the next write | cdx's experiment, my repro (§3.2). |
| Muse parser | Correct | Terminal text is authoritative. Deltas are used only for salvage. There is no double reply. Existing tests pass (cdx: 26 tests; mus: 18). |
| Reply cache | Correct for growth | `read_reply_chunks` keys on both files' `(mtime_ns, size)`, and the last chunk runs to EOF. A growing single chunk shows up on the next repaint (verified by cdx). |
| TUI trigger | **Defect 1:** no repaint on reply growth | §3.1. |
| CLI console | **Defect 3:** one line per delta under `Live` | §3.3. |

## 3. Findings in Detail

### 3.1 Defect 1: the TUI ignores reply growth (primary)

- **The watcher drops reply writes.** `_dirty_surfaces_for_paths`
  (`src/sase/ace/tui/actions/event_refresh/_watcher.py`) routes any `artifacts` path
  through `artifact_path_affects_agents`.
  - That check accepts only loader markers: `agent_meta.json`, `done.json`,
    `running.json`, `waiting.json`, `pending_question.json`, `workflow_state.json`,
    `plan_path.json`, `retry_state.json`, `prompt_step_*.json`, `.ace_refresh_pulse`,
    and shallow directory paths.
  - `live_reply.md` and `live_reply_timestamps.jsonl` fall through to
    `ignored_artifact_path`, which yields an empty target set, so `_on_artifact_change`
    returns early.
  - `test_artifact_change_ignores_non_loader_artifact_content`
    (`tests/ace/tui/test_event_handlers_artifact_dirty_flags.py:384`) pins this.
- **The polling paths miss it too:**
  - The quiet auto-refresh tick (10 s) calls `_refresh_selected_agent_file_panel()`. It
    refreshes only the Files deck.
  - The 1 s countdown patches runtime suffixes and polls status markers only
    (`_INFLIGHT_POLL_MARKERS`).
  - Surface tokens stat only root directories, so an append to a nested file does not
    change them (cdx verified the token stayed identical).
- **The slow-tool tick only paints by accident.** It runs every 5 s
  (`widgets/prompt_panel/__init__.py:214-277`) and calls
  `refresh_slow_tool_metadata_from_cache` → `_update_display_impl`, which does re-read
  the reply. But it runs only while `slow_tool_sources_have_pending(agent)` is true.
  - Claude narrates *before* its tool calls, so its text gets painted during the
    pending tool.
  - Muse's reply comes *after* its last tool, when no tick is armed.
- **The hidden window is long.** Muse keeps running reminder child sessions after its
  reply. Across 208 sessions, the time from reply committed to `run.terminal.*` was
  **p50 27 s, p90 60 s, max 116 s** (cld). The finished reply sits unseen on disk
  during that window and appears only when a later marker write (finalization,
  `done.json`) or a selection change triggers a repaint.
  - Navigating away and back with j/k "shows streaming" as a side effect (grk).
- **This is long-standing, not new.** The filter dates from 2026-05-28, before Muse
  existed. Muse has never had a reliable trigger for repainting mid-reply in the TUI.
  Muse's behaviour (§4) simply makes the hole obvious.
- **gem's claim is wrong.** gem says the TUI re-renders the reply on a 1–2 s tick. No
  such tick exists for AGENT REPLY.

### 3.2 Defect 2: the shared reader strands buffered JSONL lines

`stream_json_lines` (`src/sase/llm_provider/_subprocess_stream.py`) works like this:

- It calls `select()` on the pipe, then `process.stdout.readline()` **once** per ready
  stream.
- One OS read can pull in several JSONL records. `readline()` returns the first and
  keeps the rest in the `TextIOWrapper` buffer.
- The pipe is now empty, so `select()` will not wake again until the provider writes
  more.
- The loop's own `stdout_buffer` only reassembles partial lines. It cannot see lines
  still held in the wrapper.

The same file already knows about this. `drain_reaped_streams` carries the comment
"`select` cannot see lines the text wrapper already buffered, so read until the wrapper
reports nothing more", and loops on `readline()`. Only the main loop lacks that loop.

**My repro.** A child wrote three JSONL lines in one flush, slept 1.5 s, then wrote a
fourth:

| Reader | Line 1 | Lines 2–3 | Line 4 |
| --- | --- | --- | --- |
| Current `stream_json_lines` | 0.01 s | **1.51 s** (stalled until the next write) | 1.51 s |
| Same loop with a drain-until-empty `readline()` loop | 0.01 s | 0.01 s | 1.51 s |

**Impact on Muse:**

- Muse's bursts are the multi-record-per-read case. mus measured 26 deltas arriving
  within 40 ms on a short reply.
- The tail of a burst waits until the next stdout event. That event may be
  `task.lifecycle.completed` right away, or nothing until the post-reply phase.
- cdx showed the live reply still empty at 250 ms while a raw-byte reader had already
  shown `alpha beta`.

**Scope and history:**

- This is a real but secondary latency defect. It cannot by itself explain "the reply
  only appears at the end", which defect 1 explains.
- The reader is shared by Muse, Claude, Codex, Qwen, and OpenCode, so the fix benefits
  all of them.
- Git blame dates the pattern to May 2026, before Muse.

grk and mus judged the transport fine. Neither tested the multi-record-per-read case.

### 3.3 Defect 3: every console delta becomes its own line under Rich `Live`

Interactive runs wrap the call in `provider_timer("Waiting for Muse Code")`
(`src/sase/output.py`), which is a Rich `Live` with the default `redirect_stdout=True`.
On a terminal, `Live` swaps `sys.stdout` for a `FileProxy`. In Rich 14.3.3 the two
methods behave like this:

- `FileProxy.write` buffers text until it sees `\n`.
- **`FileProxy.flush()` calls `console.print(buffer)`, which appends a newline.**

So each `print(text, end="", flush=True)` from `append_stream_delta` becomes its own
line above the spinner. A pty probe with the real `provider_timer` and
`append_stream_delta` printed:

```
It doesn
't replace
coding agents
 at all.
```

Each line appeared about 0.6 s apart, as the deltas did.

- **The console streams live, but fragmented.** This is the original "chunked poorly"
  symptom, still present on the CLI console. The September fix's `end=""` is defeated
  by the proxy's flush.
- **Both prior readings were off.** gem's claim that `Live` holds everything until the
  final newline and then dumps it in one burst is incorrect. mus suspected an
  interaction but could not verify it headlessly.
- **Dropping the per-delta `flush=True` while stdout is a `FileProxy` works.** I
  verified that this yields intact line-by-line output under the timer
  ("It doesn't replace coding agents." then "Second line here.").
- **Scope:** this affects only interactive `sase run` on a TTY. ACE-launched agents
  write stdout to a log file (`src/sase/agent/launch_admission_coordinator.py:67`).
  `Live` does not redirect a non-terminal stream, so agent logs get the raw
  concatenated text.

## 4. Muse Behaviour That Limits What Any Fix Can Show

All three bounds below are measured; none is a SASE defect.

- **Pacing is set by the CLI.**
  - Deltas arrive about 33 ms apart during generation (cld).
  - A 950-character reply arrived as **26 deltas in about 40 ms**. A 4,561-character
    reply arrived as **430 deltas over 16.7 s** (mus, same binary).
  - From response start to committed message: **p50 2.4 s, p90 5.9 s, max 15 s**
    (cld, 208 sessions).
  - Short replies always look like one burst.
- **There is no narration between tool calls.**
  - In 1,584 sessions, none of the 109,416 `assistant_tool_calls_committed` events
    carried text (cld).
  - A probe that explicitly asked for a sentence alongside each tool call got none.
  - gem's benchmark observation agrees: zero deltas during tool execution, which is
    more than 90% of turn latency.
- **About 31% of Muse runs legitimately end with no reply.** cld counted 319 of 1,016.
  I independently counted 74 of 235 runs on Oct 1–2 with an empty `live_reply.md`.
  These are mostly mechanical monitor or plan handoffs that cancel Muse before it
  writes a reply. Keep this in mind when spot-checking a fix.
- **Session log contents.** The `--session-id` log at
  `~/.local/share/muse/sessions/…/session.jsonl` is flushed live, about 0.2–0.5 s
  behind events (cld).
  - It carries **no per-token reply text**; cld and mus agree.
  - It does carry plaintext `reasoning_summary_committed` events (median 8 per session,
    median gap 39 s, per cld), tool-call **arguments**, and usage.
  - mus saw only one `reasoning_summary_delta` in their run. Density clearly varies by
    task.

**Net expectation after the fixes:**

- A typical Muse coding run still shows "Waiting for agent response..." for most of
  the run.
- The reply then streams in over a few seconds, at generation time instead of 27–60 s
  or more later.
- Long replies stream visibly.
- Mid-run content requires the optional reasoning-summary phase.

## 5. Disagreements Resolved

| Claim | Who | Verdict |
| --- | --- | --- |
| The September 20 fix broke streaming | gem (framing) | **Rejected.** The diff changes framing only; every delta is still written and flushed on arrival (all five read the diff; verified live by cld and mus). |
| The provider is fine and the TUI is the gap | cdx, cld, grk | **Confirmed** as the primary cause. mus missed the TUI gap; gem misdescribed it. |
| The TUI re-renders the reply every 1–2 s | gem | **Incorrect.** No reply-repainting tick exists except the conditional slow-tool tick. |
| Restore paragraph-boundary chunking (Gemini/agy style) for "TUI progression" | gem | **Rejected as a streaming fix.** `_subprocess_plain.py` does stamp at paragraph starts, but `live_reply_timestamps.jsonl` is ignored by the watcher just like `live_reply.md`, so it triggers nothing. It also reintroduces several dividers per reply. At most it is a separate presentation choice. |
| Rich `Live` buffers deltas until a newline, then dumps them at the end | gem | **Incorrect.** Each flushed delta prints as its own line (pty probe, §3.3). |
| The transport is fine; PTY or `stdbuf` would be the only lever | grk, mus | **Superseded.** The CLI does flush events in real time (mus), but SASE's own reader strands buffered lines (cdx, my repro). A PTY or line-buffer wrapper would not help: the stall is downstream of the pipe. |
| Watcher-driven vs. countdown-polled reply refresh | cld (watcher) vs. grk (1 s countdown) | **Use both.** The watcher is primary (low latency, zero idle cost). A cheap off-pump stat of the selected agent's two files on the existing countdown is the backstop for missed or unavailable inotify. |
| Migrate to `muse serve` (MSP) | cdx (defer), grk (reject) | **Not now.** MSP has proper `item/delta` semantics, but the SDK is a Developer Preview. Migrating would not fix defect 1, and it sits uneasily with `decisions:adapters-normalize-harnesses`. Reopen only if a timed capture shows `exec --json` cannot deliver early output. |
| The session log has useful live content | cld (yes: reasoning summaries) vs. mus (no per-token text) | **Both right.** It has no reply tokens, but it does have sparse reasoning summaries. That makes it a progress source, not a reply source. |

## 6. Options Considered

| Option | Verdict | Why |
| --- | --- | --- |
| **A. TUI selected-agent live-reply follow** | **Do (Phase 1)** | Fixes the primary gap for every provider. Presentation-only, so it stays in this repo. |
| **B. Drain buffered lines in `stream_json_lines`** | **Do (Phase 2)** | A small, shared transport fix that follows a pattern already in the file. |
| **C. Console: no per-delta flush under `Live` (or dismiss the timer on the first delta)** | **Do (Phase 3)** | Removes the console's one-line-per-token output. Small, and confined to `append_stream_delta`. |
| D. Muse reasoning-summary progress from the session log | Optional (Phase 4) | The only source of mid-run Muse content. Needs a TUI surface and must stay out of `live_reply.md`. |
| E. End the chunk on `task.lifecycle.completed` for the `model.meta.response` task | Optional polish | Ends the console line and marks "reply complete" about 27 s earlier. Not needed for Phase 1. |
| F. Revert or loosen `a0244d7599` | Reject | Brings back about 25 mid-word dividers with no liveness gain. |
| G. Add reply files to `_AGENTS_RELEVANT_ARTIFACT_MARKERS` or `_INFLIGHT_POLL_MARKERS` | Reject | Runs the expensive Agents loader at token rate. Violates tui_perf rules 5, 6, and 14, and undoes `f41cfe0948`. |
| H. Provider writes `.ace_refresh_pulse` | Reject (at most a stopgap) | Arms a row reload held to a 5–10 s floor. It ties reply text to roster mechanics. |
| I. Paragraph-boundary chunking | Reject as a fix | Triggers no repaint (see §5). |
| J. PTY or `stdbuf` wrapper | Reject | The stall is in SASE's reader, not in the CLI's pipe buffering. |
| K. Migrate to MSP (`muse serve`) | Defer | Large scope, and it does not fix the TUI. |
| L. "Narrate before each tool call" prompt directive | Reject | The model ignores it (cld's probe), and it costs tokens on every run. |

## 7. Recommended Solution

Keep `append_stream_delta()`, with one timestamped chunk per contiguous run stream,
terminal-authoritative content, and salvage-only deltas. Do not touch
`_stream_output_delta`. Then ship the phases below in this order. Phases 1–3 are
independent and can land as separate changes.

### Phase 1: TUI live-reply follow (fixes what users see)

1. **Event trigger.**
   - Where: `EventWatcherRefreshMixin._on_artifact_change`, *before* the
     `if not targets: return`.
   - Match: changed paths named `live_reply.md` or `live_reply_timestamps.jsonl` whose
     parent is the **selected** agent's artifacts directory. Resolve that directory
     from the in-memory `agent.get_artifacts_dir()`, as `_live_watch_coverage.py`
     does, so there is no stat or glob on the event loop (tui_perf rule 8).
   - Fire only when all of these hold:
     - the Agents tab is current;
     - no attempt is pinned;
     - the agent is in a live status (mirror `_LIVE_FILE_REFRESH_STATUSES` and
       `agent_has_live_file_panel`);
     - hint mode is not rendered.
   - On a match, call a new `prompt_panel.request_live_reply_refresh(agent)`.
2. **Keep the loader out of it.** `artifact_path_affects_agents` must keep returning
   `False` for reply files, and the existing ignore test stays green. Add a sibling test
   asserting that a selected-agent reply write requests a reply refresh while
   `_dirty_agents` stays `False` and no roster delta is scheduled.
3. **Throttled, pump-free refresh body.**
   - Throttle: leading-plus-trailing, about 250–500 ms, with a
     scheduled/running/pending coalescing guard. Always land the trailing refresh so the
     last tokens show.
   - Timer callback: keep it thin (rule 2).
   - Off-pump work (`spawn_pump_free_task`): stat and read the reply chunks, using
     `read_reply_chunks` / `_TailCache`, which already handle a growing last chunk.
   - Back on the UI thread: re-check the selected identity and render generation
     (rule 4), then update **only the reply content**. Do not restart header-enrichment,
     bead, linked-delta, or file-discovery workers.
   - Shortcut and caveat: `refresh_slow_tool_metadata_from_cache` →
     `_update_display_impl` is the existing repaint path and is an acceptable first
     cut. But it re-renders the whole panel and reads reply files synchronously, so do
     not drive it at token rate without the throttle and the off-pump prefetch.
4. **Polling backstop.** On the existing 1 s Agents countdown, when the user is not
   navigating or typing:
   - stat the selected live agent's two reply files off-pump;
   - compare a per-identity `(mtime_ns, size)` signature;
   - on change, issue the same refresh request.

   This covers inotify being unavailable or missing events. It costs two stats per
   second for one agent. Unlike surface tokens, it detects nested appends.
5. **Presentation.**
   - Follow the tail only when the reader is already at the bottom (mirror
     `widgets/decks/final/live.py`).
   - Preserve folds, attempt pinning, and hints.
   - One divider stays one divider (`test_agent_reply_muse_chunks` stays green).
6. **Flag.** This changes user-visible refresh behaviour. Read `sase_flags.md` and
   consider a short-lived sunset flag (default on) for rollback.
7. **Verify.**
   - Unit test: append bytes to a single-timestamp `live_reply.md` for a RUNNING
     selected agent, and assert the reply grows before any `done.json` write and
     without the agent loader running.
   - Perf: `SASE_TUI_TRACE=1` shows refreshes at or under the throttle rate, with no
     extra `refresh.auto_tick` surface reloads. `SASE_TUI_PERF=1` shows j/k p95 under
     16 ms with a streaming agent selected.
   - Visual evidence: a mid-stream `sase screenshot`.

### Phase 2: Shared reader drain

In `stream_json_lines`, replace the single `readline()` per ready stream with the
drain-until-empty loop already used by `drain_reaped_streams`:

- Loop `readline()` until it returns `""`.
- Dispatch each chunk through `dispatch_stdout_chunk`, which already reassembles partial
  lines.
- Treat an empty first read from a `select()`-ready stream as EOF.
- Cap lines per wakeup so a chatty stdout cannot starve stderr, cancellation, or
  teardown checks.

I verified this variant removes the stall. Keep the watchdog and teardown semantics
unchanged.

Add tests for two cases:

- A child writes metadata plus several deltas in one flush, then blocks on a handshake.
  Assert all deltas are dispatched and appear in `live_reply.md` before release.
- A delta stream with UTF-8 split across writes. Then re-run
  `test_completion_watchdog_streams.py` and the shared-reader provider tests, because
  Claude, Codex, Qwen, and OpenCode use this loop too.

cdx's fuller design is a coherent `os.read()` byte reader with an incremental UTF-8
decoder. It is the more robust long-term shape. Adopt it only if the drain loop shows
problems at UTF-8 boundaries or EOF.

### Phase 3: Console output under `provider_timer`

In `append_stream_delta`'s console branch, do not `flush=True` per delta when
`sys.stdout` is a Rich `FileProxy` (that is, while `Live` is redirecting). The proxy then
emits whole lines as `\n` arrives, and `_close_delta_chunk`'s final `print()` flushes
the rest.

- Result: intact line-by-line streaming under the spinner (verified).
- On a plain terminal or a log file, keep the token-level `end=""` + flush.
- Token-level console streaming is possible: gem proposed stopping or dismissing the
  timer on the first delta. It is more code in `output.py` and only matters for
  interactive `sase run`.

### Phase 4 (optional): Mid-run progress from Muse reasoning summaries

Do this only if seeing *something* during Muse's long tool phase matters.

1. **Tail the log.**
   - Start a daemon tail of the Muse session log beside `start_completion_watchdog` in
     `MuseProvider._run_subprocess`.
   - Locate the log with `_find_muse_session_log`, poll by byte offset about every
     0.5 s, and do a final drain at exit.
   - On a missing log or unknown schema, emit only a bounded diagnostic.
2. **Write progress.** Write `reasoning_summary_committed` text through the existing
   thinking-artifact format (`open_codex_thinking_file`). **Never into
   `live_reply.md`**: chunks, attempt archives, search, and salvage all depend on that
   file being the reply.
3. **Surface it.** Without a TUI surface the artifact is invisible.
   `sase.ace.tui.thinking.read_codex_thinking` currently has no consumers. A generic
   dim progress strip under AGENT REPLY, repainted by the Phase 1 trigger, would also
   light up the Codex, Claude, and Grok thinking artifacts.

### Decision gate after Phases 1–2

Capture one real Muse run with a long answer, timestamping four things:

- raw stdout events;
- parser dispatch;
- `live_reply.md` growth;
- visible panel repaint.

Store a sanitized, release-keyed fixture. The existing `muse_exec_*` fixtures carry one
delta each and prove nothing about latency.

- **Success:** several deltas painted well before `run.terminal.*`.
- **Failure:** if the deltas are late even on the wire, evaluate MSP `item/delta`
  timing against the same criteria before considering a migration.

### Boundaries and what not to do

- **No `sase_core` change is needed.**
  - Phase 1 is presentation: Textual scheduling and rendering.
  - Phases 2 and 3 are Python process and console glue.
  - If a reusable provider-event or reply projection is ever introduced, that part
    belongs in `sase_core` with bindings and a revision-pin bump.
- **Do not:**
  - revert `a0244d7599`;
  - add reply files to the Agents loader or in-flight marker sets;
  - duplicate deltas into `InvokeResult.content`;
  - add a "narrate" prompt directive;
  - start with a PTY, `stdbuf`, or an MSP rewrite.

## Method and Limits

- **Code read:**
  - `muse_provider.py`, `_subprocess_muse.py`, `_subprocess_artifacts.py`,
    `_subprocess_stream.py`, `_subprocess_plain.py`;
  - `output.py`;
  - the ACE watcher, auto-refresh, prompt-panel, and artifact-cache modules;
  - Rich 14.3.3 `FileProxy`.
- **History:** `git log -S` over `ignored_artifact_path` and
  `_AGENTS_RELEVANT_ARTIFACT_MARKERS`; `git show` of `f41cfe0948`, `a0244d7599`, and
  `28b3c1bab2`.
- **Lead-researcher probes:**
  - a pty run of the real `provider_timer` + `append_stream_delta`, with and without
    per-delta flush;
  - a subprocess repro of the reader stall, plus the drain-loop variant;
  - an artifact check of the 2026-09-20 multi-message run;
  - an empty-reply count over Oct 1–2 Muse runs.
- **Researcher probes:** live `muse exec --json` timing runs (cld: 3; mus: 4), corpus
  statistics over 1,584+ Muse sessions (cld), and controlled parser and cache
  experiments (cdx).
- **Not done:**
  - No researcher drove a live, mounted TUI against a streaming Muse agent. The TUI
    conclusions rest on code, tests, controlled cache experiments, and artifact timing.
    Confirm Phase 1 with a mid-stream screenshot.
  - No upstream Muse change in delta vocabulary or cadence was established; 1.4.2 is the
    baseline.
