---
create_time: 2026-10-03
updated_time: 2026-10-03
status: draft
tags:
  [
    muse,
    llm-provider,
    streaming,
    live_reply,
    tui,
    research_swarm,
  ]
---

# Muse LLM provider reply streaming

**Question.** How should SASE restore live Muse agent-reply streaming after the
chunking-bug fix, without bringing the mid-word `AGENT CHAT` dividers back?

**Researcher.** grk (`research.3g.grk`). Independent report. I did not read
peer swarm reports (`__cdx.md`, `__cld.md`, `__mus.md`, `__gem.md`).

**CLI under test.** Muse Code 1.4.2 (`1.4.2-R4684.1`). `muse exec --json`
already emits JSONL on stdout; there is no extra stream flag.

## Bottom line

The Muse parser **already streams**. Commit `a0244d7599`
(`fix(muse): coalesce output deltas into one live-reply chunk per run stream`,
2026-09-20) did not stop writing `run.output.delta` fragments to
`live_reply.md`. It stopped treating each fragment as a whole assistant
message.

What broke user-visible streaming is the **TUI refresh graph**, not the
provider:

1. Deltas still `write` + `flush` into `live_reply.md` as they arrive.
2. After the fix, `live_reply_timestamps.jsonl` gets **one** entry per run
   stream, on the first delta only.
3. The Agents-tab watcher and inflight poll **ignore** both `live_reply.md`
   and `live_reply_timestamps.jsonl`.
4. Idle auto-refresh updates the selected agent's **Files** pane, not
   AGENT REPLY. Countdown ticks patch runtime suffixes and status markers.
5. AGENT REPLY rebuilds when the selected agent's detail is re-rendered
   (selection, agent load, sanity refresh). Intra-chunk growth is invisible
   until then.

So the "streaming used to work" memory is almost certainly the **pre-fix
chunk explosion**: ~25 timestamped dividers, breaks mid-word and
mid-inline-code. After coalescing, the same run lands as **one** divider
when the agent finishes. That reads as "streaming died."

**Recommended solution.** Keep coalescing. Do not revert `a0244d7599`. Add a
**selected in-flight AGENT REPLY tail**, modeled on `_axe_live_tick` and
`_refresh_selected_agent_file_panel`, driven from the 1 s countdown (optional
throttled watcher shortcut). Rebuild the reply card only. Do not put
`live_reply.md` on the roster-reload marker lists.

## What "streaming" means in this stack

Three layers, easily confused:

| Layer | What it does today | User-visible? |
| --- | --- | --- |
| Muse CLI | `muse exec --json` JSONL envelopes on stdout | Only if something consumes them live |
| Provider parser | `stream_and_parse_muse_json_output` in `_subprocess_muse.py` | Console `print` when `suppress_output=False`; always `live_reply.md` when `SASE_ARTIFACTS_DIR` is set |
| TUI Agents tab | `get_timestamped_reply_chunks` / `get_live_reply_content` into AGENT REPLY | Only when the detail panel is rebuilt |

Docs already describe the intended contract
(`docs/llms.md` "The Event Stream" and "Live Reply File"):

- `run.terminal.*` `payload.text` is the **authoritative** reply.
- `run.output.delta` is `ephemeral`, live-display only, may split mid-word.
- Deltas of one run stream coalesce into **one** timestamped `live_reply.md`
  chunk.
- Deltas are **never** appended to the returned content (no double reply).
- Salvage concatenates deltas only when no terminal event arrives.
- `live_reply.md` "is used by sase's TUI Agents tab to display the agent's
  reply **as it streams in**."

The last sentence is the gap: the file is written as it streams; the TUI
does not notice.

## History: the chunking bug and the fix

### Parser introduction

- `44fa7eee24` — add Muse Code provider and JSONL stream parser.
- `050c9477ce` — tool calls, usage, model identity.
- `a0244d7599` (2026-09-20) — coalesce deltas into one live-reply chunk per
  run stream.

### What `append_stream_text` did to Muse

`append_stream_text` (`_subprocess_artifacts.py`) treats **every call** as a
whole assistant message:

- write a timestamp at the current byte offset
- insert `"\n\n"` if the file already has content
- write the text and flush
- `print(text, flush=True)` (newline)

Claude and Codex call that helper on **complete** assistant text blocks /
`item.completed` `agent_message` items. One timestamp per message is
correct.

Muse `run.output.delta` is token-level. The commit message for
`a0244d7599` records the failure: the metadata panel showed **~25 AGENT
CHAT dividers** with breaks mid-word and mid-inline-code.

### What `append_stream_delta` does instead

```python
# new_chunk True only when the run-stream key changes
if new_chunk:
    write_reply_timestamp(...)
    if live_reply_file.tell() > 0:
        live_reply_file.write("\n\n")
live_reply_file.write(text)
live_reply_file.flush()
if not suppress_output:
    print(text, end="", flush=True)
```

Stream key: `command_id`, else `run_stream.id`, else `"<unkeyed>"`. A
matching `run.terminal.*` closes the open chunk. A later stream opens a
new one (wait-continuation cycles, multiple runs).

Tests lock this in:

- `tests/llm_provider/test_muse_provider_stream.py` —
  `test_muse_stream_coalesces_deltas_into_one_live_reply_chunk`
  (one timestamp at byte 0; `live_reply.md` is the concatenation).
- `tests/ace/tui/widgets/test_agent_reply_muse_chunks.py` —
  `test_muse_reply_renders_one_divider_for_all_streamed_deltas`.

**Do not revert this.** Reverting would restore "streaming" only as visual
noise.

## Provider path (already live)

`MuseProvider._run_subprocess` (`muse_provider.py`):

- `Popen(..., stdout=PIPE, stderr=PIPE, text=True)`
- `muse exec --json --prompt-file --session-id ...`
- `stream_and_parse_muse_json_output`

`stream_json_lines` (`_subprocess_stream.py`) sets both pipes non-blocking
and `select`s with a 0.1 s timeout. Complete JSONL lines are dispatched as
they arrive. Partial lines stay in a buffer.

On each `run.output.delta` with non-empty `text`, `_stream_output_delta`:

1. Accumulates fragments in `state.streamed_texts` (salvage only).
2. Calls `append_stream_delta` with `new_chunk=(open_stream_key != stream_key)`.

Returned content prefers `run.terminal.*` texts. Deltas are not copied into
it. Missing-terminal salvage concatenates per stream, then joins streams
(`_resolve_muse_content`). That path is already tested.

`open_live_reply_file` opens `live_reply.md` in append mode. Python file
buffering is irrelevant because every delta **flushes**.

Captured fixtures (`muse_exec_read_tool_R708.1.jsonl` line 45) often have
**one** `run.output.delta` carrying the full short reply (`"bravo"`),
`record_type: status`, `durability: ephemeral`. Live Muse streams are
finer; the coalescing commit and the mid-word test (`"It doesn" / "'t
replace..."`) are the source of truth for fragment size.

`muse schema generate-json-schema` exports **MSP** (`muse serve` stdio),
not the `muse exec --json` envelopes SASE parses. Switching the adapter to
`muse serve` is a different project and is not required for reply
streaming.

Muse has no headless resume. Wait-claim continuations start a **new**
`muse exec` with reconstructed context. Each cycle is a new run stream and
correctly opens a new live-reply chunk.

## TUI path (where streaming dies)

### How AGENT REPLY is built

For a running agent (`_agent_display_render.py`):

1. `chunks = agent.get_timestamped_reply_chunks()`
2. If chunks exist: one timestamp divider per chunk, markdown of
   `chunk_text.strip()`
3. Else `get_live_reply_content()` as a single un-timestamped body
4. Else "Waiting for agent response..."

`read_reply_chunks` (`artifact_files_cache.py`) keys the cache on **both**
files' `(mtime_ns, size)`. The last chunk extends to EOF. Growing
`live_reply.md` with a **stable** timestamps file already invalidates the
cache and returns a longer last chunk. `_TailCache` does the same for the
un-timestamped path.

The data model is ready. The panel is not asked to re-read.

### Why the watcher drops the writes

`ArtifactWatcher` watches live agent artifact directories with
`IN_MODIFY | IN_CREATE | ...`. Directory watches **do** see
`live_reply.md` mutations. `_on_artifact_change` then maps paths through
`artifact_path_affects_agents`.

`_AGENTS_RELEVANT_ARTIFACT_MARKERS` is only:

`agent_meta.json`, `done.json`, `running.json`, `waiting.json`,
`pending_question.json`, `workflow_state.json`, `plan_path.json`,
`retry_state.json`

plus `prompt_step_*.json`, `.ace_refresh_pulse`, and some directory-create
cases.

`live_reply.md`, `live_reply_timestamps.jsonl`, and `tool_calls.jsonl` are
**not** markers. A `live_reply.md` IN_MODIFY is classified as an ignored
artifact path and does **not** set `_dirty_agents`.

This is intentional roster hygiene: token-level writes must not reload the
Agents list. `tests/ace/tui/test_artifact_paths.py` already asserts that
unrelated files under an agent artifact dir do not affect agents.

### Idle auto-refresh does not paint AGENT REPLY

Default `refresh_interval` is 10 s. `AGENTS_LOAD_MIN_INTERVAL_SECONDS` is
5 s. Sanity floor is 300 s.

When agents are **not** due, `_run_auto_refresh_body` calls
`_refresh_selected_agent_file_panel()`, which only
`agent_detail.refresh_current_file(agent)` (Files deck). Comment in
`_event_countdown.py`: cosmetic countdown/runtime repaint and inflight
marker poll are explicitly **not** a prompt-panel rebuild.

### Countdown (1 s) also skips the reply

On the Agents tab, each quiet second:

- `_update_agents_info_panel`
- `_patch_agent_runtime_rows` (runtime suffixes on list rows only)
- `_poll_starting_agent_transitions` → `_poll_inflight_agent_transitions`
- tool-run drift probe (2 s)

`_INFLIGHT_POLL_MARKERS` is `agent_meta.json`, `done.json`,
`waiting.json`, `retry_state.json`, `pending_question.json`. A signature
change schedules `_schedule_agent_artifact_delta_refresh` (roster row
reconcile), not a live-reply tail.

`_first_observation_needs_refresh` only knows those status markers.
Adding `live_reply.md` to the tuple without rewriting that helper would
still miss the first-create case, and **with** a rewrite would roster-reload
every in-flight Muse agent about once a second while tokens arrive.

### When AGENT REPLY actually updates

`prompt_panel.update_display(agent)` (via `_update_main_source`) on:

- selection / focus detail refresh
- agent load / artifact-delta that re-renders the selected row
- hint-mode / attempt pinning paths

`update_display` is heavier than a reply tail: it prepares sections, may
reset per-agent markdown cache (identity change only), and starts header
enrichment, linked-delta, and bead workers. It is the wrong hammer to
swing on every token, and even a 1 s full `update_display` should be
avoided.

Re-selecting the agent **does** show the current `live_reply.md` because
the cache keys include size. Users who j/k away and back "see streaming"
as a side effect.

## Why the bug-fix looked like it killed streaming

Two effects stacked:

1. **Before the fix**, each delta was a new timestamped chunk. When the
   TUI finally rebuilt (done marker, selection, 300 s sanity, or an
   unrelated marker write), the panel showed many dividers. That looked
   like a streamed transcript, even if the rebuild was late.
2. **After the fix**, the same rebuild shows one intact chunk. If the
   rebuild is only at completion, the user sees nothing until the end.

Console streaming (`print(..., end="", flush=True)`) still works when
`suppress_output=False`. ACE agents typically display through the TUI
artifact, not an attached console. `docs/llms.md` "Output Suppression":
background invocations capture lines and skip console print. The TUI
**is** the stream surface.

## Comparison with other providers

| Provider | What is written to `live_reply.md` | Timestamp policy | TUI live-update? |
| --- | --- | --- | --- |
| Muse | Token/fragment `run.output.delta` | One per run stream (`append_stream_delta`) | No, same watcher hole |
| Claude | Complete assistant `text` blocks | One per block (`append_stream_text`) | Same hole; blocks are rarer so it hurts less |
| Codex | Complete `agent_message` items | One per message | Same hole |
| Grok | Messages-json assistant text (Claude-like) | One per block | Same hole |

Muse is the provider that **needs** intra-chunk TUI tails, because its
deltas are sub-message. Claude/Codex "stream" at message granularity; a
10 s delay between messages is less obvious than a frozen Muse paragraph.

A selected-agent live-reply tail would help every provider. Muse is the
one that makes the hole obvious.

AXE already has the pattern: `_axe_live_tick` on the 1 s countdown pulls
fresh output for the selected running chop **without** waiting for the
fleet refresh interval. Files already have
`_refresh_selected_agent_file_panel`. AGENT REPLY has no sibling.

## Alternatives

### A. Revert coalescing / per-delta `append_stream_text`

Restores ~25 mid-word dividers. Still does not make the TUI notice
`live_reply.md` unless timestamps.jsonl were added as a roster marker
(expensive). **Reject.**

### B. Put `live_reply.md` on `_AGENTS_RELEVANT_ARTIFACT_MARKERS`

Watcher would set `_dirty_agents` on every token. Auto-refresh is floored
at 5 s and runs the agents loader. Violates TUI perf rules 5–6 and 14
(`tui_perf.md`: route roster through the existing fast path; prefer
selective updates; idle ticks skip unchanged surfaces). **Reject as
primary.**

### C. Put `live_reply.md` on `_INFLIGHT_POLL_MARKERS`

1 s stats for up to 256 in-flight dirs, then **artifact-delta roster
refresh** whenever size changes. Works for the selected row only by
accident, and thrashes unselected Muse runs. First-observation helper
would need a rewrite. **Reject as primary.** Acceptable only as a
last-resort backstop with a selected-dir filter, which then collapses
into D.

### D. Selected in-flight AGENT REPLY tail (recommended)

On the Agents-tab countdown, when not navigating and not typing:

1. If the selected agent is in-flight (`_LIVE_FILE_REFRESH_STATUSES` /
   `agent_row_is_in_flight`).
2. Off the pump (`spawn_pump_free_task` / `asyncio.to_thread`), `stat`
   `live_reply.md` and `live_reply_timestamps.jsonl`.
3. If `(mtime_ns, size)` changed versus the last signature for that
   identity, on the UI thread rebuild **only the reply card** (chunks /
   live reply), then push the Main-deck document.
4. Do not start header enrichment, bead, or linked-delta workers.
5. Do not set `_dirty_agents`.
6. Respect `DetailPanelDebouncer` (150 ms) or a 250–500 ms throttle so
   Muse's 50 ms inotify coalesce cannot flood markdown.

Reuse `read_reply_chunks` / `_TailCache`. Last chunk already grows to
EOF. One divider stays one divider.

Optional phase 2: if the watcher event path is the selected agent's
`live_reply.md` / timestamps file, schedule the same reply-only refresh,
still without roster dirty. Faster than 1 s; throttle it.

This matches `tui_perf.md`: no event-loop disk work, pump-free stats,
activity gates, selective update, ticks revalidate a cached signature.

### E. Parser writes `.ace_refresh_pulse` on a throttle

Would trip `artifact_path_affects_agents` and reload the row. Couples the
provider to TUI roster mechanics. Pulse is for "something about this
agent changed for the loader." Reply text is not loader state. **Reject.**

### F. Switch SASE to `muse serve` (MSP)

MSP schema has ephemeral `item/delta`. SASE's Muse adapter is `muse exec
--json`. A transport rewrite does not fix TUI tails, and conflicts with
`decisions:adapters-normalize-harnesses` (keep the harness on the
single-turn `exec` path, 10 min sync ceiling, no invisible keep-alive).
**Reject as a streaming fix.**

### G. Force Muse stdout line-buffering (`stdbuf -oL`, PTY)

Secondary. Pre-fix ~25 chunks prove many JSONL lines exist; they do not
prove inter-arrival timing through a pipe. Rust CLIs often block-buffer
when stdout is not a TTY. If a live `muse exec --json` shows
`live_reply.md` jumping in 4–8 KiB bursts while the TUI tail is in
place, then consider a line-buffer wrapper. Do **not** start here; the
TUI hole is sufficient to explain "no streaming."

### H. Render the last chunk as plain text until the stream closes

Avoids markdown flicker on incomplete fences. Optional polish after D.
Default markdown of the growing last chunk is acceptable.

## Recommended solution

**Keep the provider coalescing. Teach the TUI to tail the selected
in-flight agent's `live_reply.md`.**

Implementation sketch (for whoever implements; this report does not
change product code):

1. **Do not** change `_stream_output_delta`, salvage, or
   no-duplication-into-content.
2. Add `_refresh_selected_agent_live_reply()` next to
   `_refresh_selected_agent_file_panel` / `_axe_live_tick`.
3. Call it from `_on_countdown_tick` on the Agents tab, inside the
   existing nav-gate and prompt-input quiet check.
4. Stat off-thread; compare a per-identity signature; reply-card rebuild
   only.
5. Tests:
   - Growing `live_reply.md` with **one** timestamp row updates AGENT
     REPLY / Main reply card for the selected RUNNING agent.
   - Mid-word deltas still render **one** divider
     (`test_agent_reply_muse_chunks` stays green).
   - `live_reply.md` IN_MODIFY does **not** set `_dirty_agents` or
     schedule a roster delta.
   - Existing Muse stream tests stay green (terminal wins, salvage,
     one chunk per stream, new chunk per `command_id`).
6. Optional later: throttled watcher shortcut for the selected dir;
   verify Muse pipe buffering with a live capture; if bursts are large,
   wrap stdout line-buffering.
7. Docs: change "as it streams in" from an aspiration to "TUI tails
   `live_reply.md` for the selected in-flight agent about once a
   second."

### What not to do

- Revert `a0244d7599`.
- Add `live_reply.md` to `_AGENTS_RELEVANT_ARTIFACT_MARKERS`.
- Drive this through inflight **roster** polls.
- Duplicate deltas into `InvokeResult.content`.
- Rewrite the adapter onto `muse serve`.

## Verification notes for the implementer

- `read_reply_chunks` already treats last-chunk-to-EOF + joint signature
  as the live-growth API. A TUI test can append bytes to `live_reply.md`
  and assert the selected panel's reply markdown grew without a new
  timestamp line.
- `just check` after the TUI change. PNG goldens only if the reply card
  layout itself changes (`lint_and_test.md`).
- Muse agent turns can exceed 10 minutes; do not use a live Muse invoke
  as the unit test. Fixtures plus a fake growing file are enough.
- Confirm with a **manual** Muse run: select the agent, watch AGENT REPLY
  grow before `done.json`, still one divider, no Agents-list flicker.

## Confidence and gaps

**High** that the parser already streams to disk and that coalescing was
the right chunking fix.

**High** that the TUI watcher and countdown ignore `live_reply.md`, and
that idle refresh only tails Files.

**Medium-high** that restoring UX is a selected-agent reply tail, because
AXE and Files already use that shape and `tui_perf.md` forbids roster
reloads on hot files.

**Medium** on Muse pipe buffering as an additional delay. Not required to
explain the regression; worth a live capture after the TUI tail exists.

**Not measured in this pass:** wall-clock delay from first Muse delta to
`live_reply.md` mtime in a real `muse exec --json` under `Popen(stdout=PIPE)`.
Captured R708.1 fixtures are too coarse (one full-text delta) to time
fragments.

I did not implement streaming. I did not read peer swarm reports.
