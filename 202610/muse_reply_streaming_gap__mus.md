# Why Muse agents show nothing in the deck Reply card until they finish

**Report:** `muse_reply_streaming_gap__mus.md` · researcher `mus` · 2026-10-26
**Question:** the Muse LLM provider never streams output to the main-deck Reply
card while running; the reply arrives only after the agent completes (example:
`bob-cli-cn.1` on athena, TUI `v0.18.1+12.g60832648b`, model
`muse-spark-1.3-contributor`, card stuck on "Waiting for agent response..." at
21m36s of RUNNING). Other providers stream fine.

## Bottom line

The blank card is **Muse CLI behavior, faithfully reproduced by SASE** — not a
TUI refresh bug and not stdout buffering. `muse exec --json` emits
assistant-facing text **only as `run.output.delta` fragments of the final
answer, near the end of the run**. During tool phases it emits zero reply
bytes: narration between tool calls is never sent as deltas. SASE writes
`live_reply.md` exclusively from those deltas (the terminal event's text is
never written to the file), so the file — and therefore the Reply card — stays
empty until the final answer starts composing. Recommended fix is SASE-side
interim progress in the Reply path (details at the end).

## Evidence (live probes, this workspace, Muse 1.4.13 R6996.1)

Two headless runs were timed line-by-line against the real CLI:

1. **No-tool prompt** ("150-word lighthouse story", `muse-spark-1.2`): 12
   `run.output.delta` events, first at **6.07s**, `run.terminal.completed` at
   **11.02s**. Deltas stream ~5s before the end. Stdout is *not* block-buffered
   to exit, and the `run.output.delta` envelope still exists in this release —
   ruling out "CLI buffers everything" and "schema rename" as the cause.
2. **Tool-using prompt** (list files, write `story.txt`, reply with a summary;
   65.6s total, 458 JSONL events, saved to `/tmp/muse_probe/tool_raw.jsonl`):
   - **First `run.output.delta` at 49.24s; terminal at 65.33s.** For the first
     ~75% of the run — the entire tool phase — the stream carried **zero**
     assistant-text events.
   - The 47 deltas are word-level fragments of the final 2-paragraph summary
     only (`"I started"`, `" by listing ..."`, ...). Concatenated deltas are
     byte-identical to the terminal text (876 chars == 876 chars).
   - The 49 silent seconds were *not* quiet on the wire: dozens of
     `task.lifecycle.started/completed`, `tool.result` (which *do* carry tool
     output text), `task.lifecycle.status` ("opening meta model stream attempt
     1/10", ...), and `task.lifecycle.output` events. None of them carries
     assistant narration, and SASE's Muse parser deliberately ignores all of
     them for reply purposes.

So a 21-minute PLAN run (read beads, search, clan workflows — almost all tool
calls, as in the screenshot) legitimately produces no reply bytes until its
closing summary streams. The card then fills "after the agent completes" (or
seconds before, perceptually the same).

## Why the SASE side is innocent (but owns the fix)

- `src/sase/llm_provider/_subprocess_muse.py`: `_stream_output_delta` appends
  each delta **synchronously** to `live_reply.md` with flush, plus a
  `live_reply_timestamps.jsonl` entry per run stream. `_capture_run_terminal`
  appends only to the in-memory result — terminal text never touches the live
  file. File-growth timing therefore equals delta-arrival timing exactly.
  Covered by `tests/llm_provider/test_muse_provider_stream.py` and
  `tests/ace/tui/widgets/test_agent_reply_muse_chunks.py`.
- Deck pickup path is provider-agnostic and proven by the working providers:
  `render_agent_reply_content`
  (`src/sase/ace/tui/widgets/prompt_panel/_agent_display_content.py`)
  prefers timestamped chunks → `live_reply.md` → response file; the follow
  controller (`_live_reply_follow.py`) combines a file watcher with a 1s stat
  poll. Empty file + absent timestamps file ⇒ "Waiting for agent response..."
  — exactly the screenshot.
- This checkout is `v0.18.1-12-g60832648be`, i.e. the same build as athena's
  TUI, so the finding is not version skew. (Minor caveat: probes used
  `muse-spark-1.2`; the failing agent used `muse-spark-1.3-contributor`. The
  streaming envelope is CLI-version behavior, not model behavior, and the echo
  provider on this same CLI still emits `run.output.delta` — but a
  confirmatory run on `1.3-contributor` is a cheap extra data point.)

## Why only Muse

Claude/Codex/OpenCode/Qwen parsers stream **every assistant message**
(`append_stream_text` per block in `_subprocess_claude.py`, etc.), including
"let me check X" narration seconds into the run — their `live_reply.md` grows
from the start. Muse's `--json` vocabulary has no per-message assistant event
at all; the only reply-text carrier is the end-of-run delta burst. Any
tool-heavy Muse run looks dead in the Reply card by construction.

## Ruled out

- **Stdout/pipe buffering**: deltas arrive 5s (short run) / 16s (tool run)
  before exit while the process is still running.
- **Payload rename / schema drift** (installed R6996.1 vs R708.1 fixtures):
  `run.output.delta` with top-level `text` + `command_id`/`run_stream` is
  still what the CLI emits, and the parser tolerates unknown types anyway.
- **Rich `FileProxy` no-flush** (`append_stream_delta` skips flush under
  `FileProxy`): affects terminal echo only; the deck reads the file, which is
  flushed per delta.
- **`_ReplyChangedDuringRead` snapshot livelock**: retries converge once a
  burst ends; cannot explain 21 silent minutes with zero file bytes.

## Recommended solution

1. **SASE-side interim progress (the fix):** while a run has produced tool
   activity but no reply bytes, show *something* truthful in the Reply card —
   e.g. a "working: last tool …" line synthesized from the already-parsed
   `MuseToolCallTracker` / `task.lifecycle.*` events as its own timestamped
   chunk, or render the existing tool-call artifacts in the card's waiting
   state. This closes the perceived-dead gap without misrepresenting tool
   output as the model's reply. The `task.lifecycle.status` messages
   ("opening meta model stream…") are also candidate filler but are noisier
   and less informative than tool names.
2. **Upstream ask (parallel, low priority):** request that `muse exec --json`
   emit narration/status text as `run.output.delta` (or a documented
   equivalent) during tool phases, matching the other CLIs' per-message
   streaming. Check first whether a verbosity/progress flag already enables
   this — none was found in `muse exec --help`.
3. **Verify on athena:** during the next long Muse run, `stat`/`tail` the
   agent's `live_reply.md` mid-run. Expected per this analysis: file absent or
   0 bytes until the final minutes. If instead the file *has* content the TUI
   doesn't show, reopen as a TUI/polling bug (TailCache or watcher scope) —
   but all local evidence says the file will be empty.

## Reproduction

```bash
# timed arrival log of every payload type (needs Muse auth; ~1 min, tiny cost)
timeout 540 python3 /tmp/muse_probe/tool_run.py
grep -c run.output.delta /tmp/muse_probe/tool_raw.jsonl   # 47, all after 49s
grep -E "run.terminal|done rc" /tmp/muse_probe/tool_timed.txt
```
