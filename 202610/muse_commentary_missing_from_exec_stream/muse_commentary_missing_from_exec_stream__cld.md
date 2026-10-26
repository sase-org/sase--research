# Muse Reply Card Stays Empty Because `muse exec --json` Drops Commentary

> **Research query:** The Muse LLM provider still streams no output to the Reply card in
> the main deck while an agent runs; the text only arrives after the agent completes.
> The example is the `bob-cli-cn.1` agent on athena. Figure out exactly what causes
> this, and why it seems to affect only Muse, then recommend a solution.

_Researcher: cld · 2026-10-26 · sase `master` @ `60832648be` · Muse Code
`1.4.13-R6996.1` on athena and apollo_

## Bottom line

**The TUI is not the problem anymore, and neither is SASE's Muse parser. Muse does write
mid-run text. Since about Oct 4–5, the model sends a short "commentary" progress message
before most tool calls, much like Codex and Claude narrate. `muse exec --json`, the only
stream SASE reads, leaves those messages off stdout. Muse writes them only to its private
session log. So `live_reply.md` stays at 0 bytes until the final answer, and the Reply card
correctly shows "Waiting for agent response..." for most of the run.**

Evidence from the agent in the screenshot (`bob-cli-cn.1`, artifacts
`…/gh_bobs-org__bob-cli/artifacts/ace-run/202610/26/20261026131420`):

| Time (UTC) | What happened |
| --- | --- |
| 17:23:56 | Main step starts; `live_reply.md` is created empty |
| 17:24:00 | Muse commits its first commentary: *"Fixing your phase bead — reading scope and landing the work."* |
| 17:24:00 – 17:43:40 | 19 more commentary messages, e.g. *"All green — now adding the hand-derived tests."*, *"Contract verified — measuring performance before/after."* |
| **17:45:21** | **Screenshot taken: 20 progress messages exist, and `live_reply.md` is still 0 bytes** |
| 17:50:57 | 25 commentary messages so far, and `live_reply.md` is still 0 bytes (131+ tool calls) |

The 25 messages are in
`~/.local/share/muse/sessions/2026/10/26/66b7ac36-…/session.jsonl` as `runtime.session`
→ `assistant_message_committed` events with `"phase": "commentary"`. None of them appears
anywhere on that run's `muse exec --json` stdout.

**Why only Muse:**

- Claude, Codex, and Grok put their between-tool narration on their machine-readable stream:
  - Claude: text blocks.
  - Codex: `agent_message` items.
- SASE writes that narration to `live_reply.md` as timestamped chunks.
- Muse's narration never reaches SASE.

Across athena's Oct 5–26 runs that made at least 5 tool calls:

| Provider | Runs | Median `live_reply.md` chunks per run | Runs with ≥3 chunks |
| --- | --- | --- | --- |
| claude | 579 | 9 | 563 (97%) |
| codex | 943 | 6 | 924 (98%) |
| grok | 498 | 9 | 497 (~100%) |
| **muse** | **1,015** | **1** | **18 (2%)** |

**Recommendation:** have the Muse adapter tail its own session log while the run is in
progress. Each `phase == "commentary"` message becomes a timestamped chunk in
`live_reply.md`, the same way Codex `agent_message` items are handled. Display-only, fail-soft,
and no TUI change. Also ask upstream to put commentary on `exec --json`, so the tail can
be deleted later. Details are in [Recommended solution](#recommended-solution).

## What changed since the earlier studies

Two earlier consolidated studies looked at this symptom:
`202610/muse_live_reply_streaming` (Oct 3) and
`202610/muse_reply_card_follow_skips_workflow_agents` (Oct 9). Both found real TUI
defects, and both were fixed:

- `2307212bcd`: the selected-agent live-reply follow.
- `8150a76d46`, Oct 10: the follow gate now uses `is_agent_entry`, so workflow rows are followed too.

Both studies also accepted one premise: **"Muse sends no text during tool phases."** That
premise was true on Oct 3 and false a day later. A scan of every Muse session log on
athena shows a sharp change:

| Session-log dates | Sessions with tool calls | Sessions with ≥1 commentary message | Commentary messages |
| --- | --- | --- | --- |
| Aug 7 – Oct 3 | 1,918 | **0** | 0 |
| Oct 4 | 1 | 1 | 66 |
| Oct 5 – Oct 26 | 1,377 | **1,377 (100%)** | 18,903 |

The Oct 3 study was right for Muse `1.4.2`. The Oct 9 study used `1.4.4`, which already
narrated. But it judged Muse's behaviour from **stdout probes and SASE's own
`live_reply.md` artifacts**, and neither of those can show commentary. The session log
was the only place the narration was visible, and it was only checked for reasoning
summaries and usage.

This also explains why the Oct 10 gate fix changed nothing visible for the user. The
follow now watches the right file, but the file has nothing in it until the final answer.

## How the text gets lost

```
Muse model ──▶ assistant message, phase="commentary"   ("Schema in place — wiring the window computation.")
           ──▶ assistant tool calls
           ──▶ … repeat …
           ──▶ assistant message, phase=None            (final answer)

muse runtime
  ├─ session.jsonl (private, flushed live)   : commentary ✔  tool calls ✔  final ✔
  └─ exec --json stdout (SASE reads this)    : commentary ✘  tool/task lifecycle ✔  final as run.output.delta ✔

SASE _subprocess_muse.py
  run.output.delta ─▶ append_stream_delta ─▶ live_reply.md     (final answer only)

ACE TUI live-reply follow (works) ─▶ Reply card shows "Waiting for agent response..." until the final answer
```

### Proof that stdout has no commentary

I ran `muse exec --json` 1.4.13 with SASE's flags at `--reasoning-effort low` on a
four-step shell task. I captured stdout with wall-clock timestamps and compared it with
the session log:

- **Session log:** four commentary messages, one before each tool call. Examples:
  "I'll work through this step by step, starting with the line count.", "Line count is 3.
  Now reading the file contents.", and so on. The final answer came after them.
- **stdout (143 envelopes):**
  - `run.output.delta` appeared only at 17.5–17.8 s, carrying the final answer.
  - The other envelopes were `task.lifecycle.*`, `tool.result`, `run.model.configured`, and similar.
  - Not one commentary string appears anywhere in stdout, in any payload type.
- **Binary vocabulary:** the 1.4.13 binary's public exec vocabulary matches this.
  - It contains `run.output.delta`, `run.terminal.*`, `tool.result`,
    `todo.snapshot.updated`, and `task.lifecycle.*`.
  - It has no commentary or message event.
  - `muse exec --help` has no flag that would add one.

The model is asked to write these messages: Muse's base instructions refer to
"commentary, progress updates, todo items, and other tool-call text". `exec --json`
simply does not export them.

### Proof that the rest of the pipeline is fine

- **The parser.** `_process_muse_json_line` (`src/sase/llm_provider/_subprocess_muse.py`)
  writes every `run.output.delta` to `live_reply.md` as it arrives. It ignores unknown
  payload types, and that is correct here, because no payload carries the commentary.
- **The TUI row.** I loaded the live rows with the real `load_all_agents()` on athena. The
  `bob-cli-cn.1` row loads as:
  - `AgentType.WORKFLOW`, `appears_as_agent=True`, `status=RUNNING`;
  - `is_live_reply_agent() == True`;
  - `_selected_live_reply_agent()` returns the row itself;
  - its artifacts directory is `…/20261026131420`.

  So the follow is armed and watching `live_reply.md`, a file that stays empty.
- **The deck.** The SPREAD Main deck renders from the hidden `#agent-prompt-panel`
  document sink, and that is the panel the follow updates. The mounted tests
  (`tests/ace/tui/test_live_reply_follow_mounted_workflow.py` and siblings) cover workflow
  root rows, workflow step rows, and session turns end to end.
- **The tests' blind spot.** Those mounted tests use `gated_muse_script()`, which emits
  `run.output.delta` **mid-run**. Real Muse never does that: it sends deltas only for the
  final answer. The tests pass because the fixture is more talkative than the real CLI.
- **Other providers.** In the same TUI, the same week, they show median 6–9 chunks per run.

## How much the user is missing

| Measure (athena, Oct 20–26) | Value |
| --- | --- |
| Muse runs joined to their session logs | 217 |
| Commentary messages Muse wrote | 2,705, a median of 7 and a mean of 12.5 per run; 100% of runs had at least one |
| Commentary messages that reached `live_reply.md` | **0** |
| First commentary after run start | median 3.1 s, p90 5.6 s |
| Share of a completed run with an empty Reply card (first tool → `done.json`) | median **84%**, p90 93% (64 runs over 60 s) |
| Minutes of empty Reply card | median **17.9**, p90 46.6, max 84.4 |
| First reply text → `done.json` | median 178 s. The final answer does show before DONE, but only after Muse's work is over, which reads as "after it completes." |

**Latency of the fix, measured.** A prototype tailer polled the session log every 0.2 s
during a live run. It read the commentary line **54 ms after Muse's `recorded_at`**,
0.6 s *before* the matching tool call was committed. The session log is flushed promptly
enough to drive a live display.

## Options

| Option | Verdict | Why |
| --- | --- | --- |
| **A. Tail the Muse session log in the adapter; write `phase == "commentary"` messages to `live_reply.md`** | **Do** | Fixes the symptom now and matches what Codex and Claude already show in Reply. The adapter already chooses the `--session-id` and already reads this log for usage (`_muse_session_usage.py`). Display-only, and if it fails the card shows exactly what it shows today. |
| **B. Ask Muse upstream to emit commentary on `exec --json`** (a `phase` on `run.output.delta`, or a durable message event) | **Do, in parallel** | This is the right long-term home, because session-log parsing is coupled to a private format. When it ships, switch to stdout and delete the tail. |
| C. Migrate to `muse serve` (MSP), whose message items carry `commentary`/`finalAnswer` phases | Defer | Large rewrite of a Developer-Preview protocol. Earlier studies deferred it for the same reasons. |
| D. TUI-only changes (repaint more often, a new progress strip) | Reject as the fix | The TUI already follows the file correctly. The file is empty. |
| E. Prompt Muse to narrate in its final answer, or to echo progress via shell | Reject | It costs tokens on every run and duplicates what the model already writes. Earlier probes showed narration prompts are unreliable. |
| F. Show only `todo.snapshot.updated` (already on stdout) | Optional extra | A useful progress signal, but it is not narration, and it updates only a few times per run (3 in `bob-cli-cn.1`). |

## Recommended solution

### 1. Muse commentary tail (adapter, Python, this repo)

All of this is provider-adapter glue in `src/sase/llm_provider/`, where every
`_subprocess_*.py` adapter already lives. The `live_reply.md` artifact contract does not
change, so **no `sase_core` change and no TUI change are needed.**

1. **New module `_muse_commentary_tail.py`.** A small daemon-thread tailer, shaped like
   the existing `start_completion_watchdog` helper:
   - **Locate.** Poll `find_muse_session_log(session_id)` every ~0.25 s until the log
     exists. Muse creates the directory at startup; the glob already handles runs that
     cross midnight.
   - **Read.** Read new bytes from a byte offset and keep any partial trailing line for
     the next pass.
   - **Prefilter.** Check bytes before parsing JSON:
     `b'"assistant_message_committed"' in line and b'"phase":"commentary"' in line`.
     Session logs reach several MB of tool output, so do not parse every line.
   - **Accept a line only when all of these hold:**
     - `payload_type == "runtime.session"`;
     - `payload.kind == "run"`;
     - `event.kind == "assistant_message_committed"`;
     - `event.phase == "commentary"`;
     - `stream.id == session_id`. Reminder child sessions use their own session IDs,
       and every commentary line in the `bob-cli-cn.1` log carried the main session
       and run.
     - `text` is a non-empty string.
   - **Dedupe** by `message_id`.
   - **Never write `phase is None`** (the final answer). Stdout deltas already stream it.
   - **Stop.** `stop()` does one final drain, then `join(timeout=…)`.
   - **Failures** produce one bounded diagnostic (for example
     `muse_commentary_tail_unavailable`) through the existing
     `append_tool_call_collector_diagnostic` path, and never raise. This covers a
     missing log, an unreadable line, or an unexpected schema.
2. **Wire it in `stream_and_parse_muse_json_output`.**
   - Add `write_lock: threading.Lock` and `commentary_ids: set[str]` to
     `_MuseStreamState`.
   - Take the lock in `_stream_output_delta`, `_close_delta_chunk`, and a new
     `_append_commentary(text, state)`. `_append_commentary` should:
     - close any open delta chunk;
     - call `append_stream_delta(text, …, new_chunk=True)`, giving one timestamped
       chunk per message;
     - close the chunk again, so the console line ends.
   - Start the tail before `stream_json_lines(...)` when `session_id` is set and the
     live-reply file is open. Stop it in the `finally`, before the reply files are
     closed.
   - **Do not** add commentary to `terminal_texts` or `streamed_texts`. That keeps these
     unchanged:
     - `InvokeResult.content` (terminal-authoritative);
     - delta salvage;
     - the wait-claim guard;
     - the reply that host finalizers see.

   This is the same split Codex has: its narration goes to the live reply, and its
   content comes from the final message.
3. **Ordering.** Commentary always comes before the tool calls that follow it, and the
   final answer comes after the last tool. The lock is enough, and chunks land in
   generation order. One edge case: a message caught only by the final drain would land
   after the final answer, a few milliseconds late. That is harmless.
4. **Tests:**
   - **Unit, `tests/llm_provider/`.** Run the tailer against a sanitized excerpt of a real
     1.4.13 session log containing:
     - commentary lines;
     - a `phase: null` final message;
     - `retained_frame` and `retained_marker` records;
     - a partial last line;
     - a duplicate `message_id`.

     Assert that only the commentary texts come out, in order, with no duplicates. Add a
     second case where the log never appears: one diagnostic, no exception.
   - **Integration.** A fake `muse` script writes commentary lines into a session log
     under a temporary `XDG_DATA_HOME`. It then blocks on a handshake while emitting only
     `task.lifecycle.*` on stdout, the way real Muse does. Assert that `live_reply.md`
     already holds the commentary chunk before the handshake releases. After release,
     the final deltas follow, and the returned `content` equals the terminal text only.
   - **Fix the fixture.** Change `gated_muse_script()` in
     `tests/ace/tui/_live_reply_follow_mounted_helpers.py` to match real Muse: no
     mid-run `run.output.delta`, commentary in the session log only. Then the mounted
     TUI tests exercise the production shape, and a regression in either layer fails a
     test.
5. **Rollout and flags.**
   - The change is fail-soft: if the tail breaks, the card looks exactly as it does today.
   - It brings Muse in line with every other provider's Reply behaviour. Once deployed,
     DONE Muse replies will also list the commentary chunks above the final answer, as
     Codex and Claude replies already do.
   - Under `sase_flags.md`, this does not need a flag unless you want a staged rollout.
     If you do, create it with `sase flag new`.
6. **Manual check:**
   - Restart the TUI. The editable-install TUI on athena has been running since Oct 24.
   - Launch a Muse agent and select it.
   - A one-line progress chunk should appear within about 1 s of each commentary
     message, which is a few seconds after start. Right now the card is blank for about
     18 minutes at the median.

### 2. Upstream request (parallel, cheap)

File a Muse Code feature request for an exec event that carries assistant message phase.
Either `run.output.delta` with `"phase": "commentary" | "final_answer"`, or a durable
`run.output.message.committed`, would work. Point out that `exec --json` currently exports
less than the interactive surfaces do. Once a release ships it:

- parse it in `_process_muse_json_line`, deduping by `message_id` against the tail
  during the transition;
- delete `_muse_commentary_tail.py`.

### Fit with existing decisions

- **[[decisions/adapters-normalize-harnesses]].** This record rejected parsing Muse's
  private session log for *wait semantics*, because correctness would then depend on a
  format that changes with every release. This tail is different:
  - it is display-only and fail-soft;
  - SASE already depends on the same log for token usage.

  The cost to record: one more consumer of a private format, retired once Option B ships.
- **[[decisions/rust-core-required]] and the Rust core boundary.** No conflict. Provider
  stream parsing lives in Python in this repo, and every frontend sees the same
  `live_reply.md` artifact.

## Method and limits

**Live inspection on athena** (read-only):

- the `bob-cli-cn.1` artifacts directory, its process, and its Muse session log (copied
  to `/tmp` for analysis);
- the real `load_all_agents()` row classification, using the installed sase interpreter.

**Probes on apollo** (`muse exec --json` 1.4.13, `muse-spark-1.3-contributor`, low effort,
throwaway workspace):

- a full stdout capture with timestamps, compared against the session log;
- a prototype session-log tailer that measured read latency.

Both probes used the same flags SASE passes.

**Corpus scans on athena:**

- every Muse session log, giving commentary counts by day;
- every October `ace-run` artifacts directory, giving reply chunks per provider;
- a join of 217 Oct 20–26 Muse runs to their session logs through
  `run_metadata.json`'s `muse_session_id`, giving commentary versus chunks and the
  empty-card timing.

**Code read:**

- `src/sase/llm_provider/`: `_subprocess_muse.py`, `muse_provider.py`,
  `_muse_launch.py`, `_muse_session_usage.py`, `_subprocess_artifacts.py`, and
  `_subprocess_codex.py` (for comparison);
- `src/sase/ace/tui/widgets/prompt_panel/_live_reply_follow.py`,
  `_agent_detail_deck_source.py`;
- the mounted live-reply tests and their helpers;
- the two prior consolidated reports.

**Limits:**

- **Prototype only.** I implemented nothing in the repo. The tailer lives only as a
  prototype in `/tmp`.
- **Commentary density varies.** One probe produced a message before every tool call;
  another produced only one at the start. Real SASE runs average 12.5 per run.
- **Unknown upgrade.** I did not identify the exact Muse release that started
  narration. It falls between `1.4.2-R4684.1` (Oct 3) and `1.4.4-R5419.1` (Oct 9), and
  the session logs date it to Oct 4–5.
- **athena only.** The scans cover athena, not apollo.
- **No mounted TUI with real commentary.** I did not drive a mounted TUI against real
  commentary. The TUI conclusion rests on:
  - the real-loader row check;
  - the existing mounted tests;
  - other providers streaming normally in the same TUI.
