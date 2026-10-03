# Muse Reply Streaming: Why It Looks Broken, and How to Fix It

_Researcher: cld · 2026-10-03 · sase `master` @ `598928da70`, Muse Code `1.4.2-R4684.1`_

## Bottom Line

**The Muse provider's streaming is not broken.** `muse exec --json` emits `run.output.delta`
fragments in real time, and SASE writes them to `live_reply.md` token by token as they
arrive, coalesced into one chunk per Muse command
(`src/sase/llm_provider/_subprocess_muse.py:252`). Live probes and on-disk session logs
confirm it. The September 20 chunking fix (`a0244d7599`) is correct. It is not the
regression.

What looks like "no streaming" comes from three things stacking up. None of them is in the
provider's delta handling:

1. **Muse never narrates between tool calls.** In 1,584 Muse sessions there were 109,416
   tool-call turns, and **none** carried any text. A live probe that told the model to
   write a sentence alongside each tool call got none. The model writes text only at the
   end of a Muse turn.
2. **Since the September 23 `muse_synchronous_shell` change (`28b3c1bab2`), each `muse exec`
   is one long turn, so there is one message, at the very end.** Before that change, Muse
   ended its own turns mid-run while background commands ran ("Rebuild running;
   continuing once it completes.") and resumed later. Those status lines landed in
   `live_reply.md` during the run. That is very likely the "it used to stream" memory.
   Sessions with two or more messages fell from **10.2% to 0.7%**. The chunking fix landed
   three days earlier, which makes it easy to blame.
3. **The TUI never repaints when `live_reply.md` grows.** The inotify watcher sees the
   writes but classifies them as ignorable
   (`src/sase/ace/tui/actions/event_refresh/_watcher.py:98-134`). A test pins that
   behaviour. Claude looks live mostly because a 5-second "slow-tool" repaint tick runs
   while a tool call is pending, and Claude's narration is written *before* its tool calls.
   Muse's only message arrives *after* its last tool finishes, when no tick is running.
   It then sits on disk unseen until something else triggers a repaint. Muse keeps running
   reminder child sessions after its reply: **median 27 s, p90 60 s, max 116 s** before it
   terminates.

**Recommendation:**

- **Phase 1 (fixes the actual gap, works for every provider):** make the TUI follow the
  live reply. Route watcher events for the *selected* running agent's `live_reply.md` to a
  throttled repaint of the prompt panel, and do not dirty the Agents loader. The repaint
  reuses the path the slow-tool tick already uses. Muse's final reply then streams in the
  panel token by token, instead of appearing 30–60 s late.
- **Phase 2 (optional; the only way to get Muse content *during* a run):** tail Muse's
  on-disk session log for plaintext `reasoning_summary_committed` events and show them as
  live progress. They never appear on stdout. They arrive about every 39 s (median), with
  about 8 per run.
- **Do not** revert the chunking fix, and do not add a "narrate before each tool call"
  prompt directive. Both were checked and neither helps.

---

## 1. How the Pipeline Works Today

```
muse exec --json ──stdout JSONL──▶ stream_and_parse_muse_json_output()
   run.output.delta (ephemeral)        └─ _stream_output_delta() ─▶ append_stream_delta()
   run.terminal.completed                                    ├─ live_reply.md   (append, flush)
                                                             └─ live_reply_timestamps.jsonl
                                                                (one line per *new chunk*)
TUI (ACE)
   fs_watcher (IN_MODIFY …) ──▶ _on_artifact_change ──▶ _dirty_surfaces_for_paths
                                     └─ live_reply.md → "ignored artifact path" → return
   panel repaint triggers: selection change, agents/delta loads, header enrichment,
                           5 s slow-tool tick (only while a tool call is pending),
                           300 s sanity reconcile
```

The provider side:

- `_stream_output_delta` keys each delta by run stream. The key is `command_id`, then
  `run_stream.id`, then a sentinel (`_subprocess_muse.py:252-292`).
- The first delta of a stream opens a timestamped chunk. Later deltas append bare text
  (`_subprocess_artifacts.py:133-159`).
- A matching `run.terminal.*` closes the chunk (`_subprocess_muse.py:304`).
- The returned reply always comes from the terminal event. Deltas are display-only, plus
  salvage when no terminal event arrives.

The TUI side:

- `read_reply_chunks` and `_TailCache` (`src/sase/agent/artifact_files_cache.py`) handle a
  growing file correctly on *any* repaint, because the last chunk runs to EOF.
- The gap is the **trigger**, not the read path.

## 2. Evidence

### 2.1 The provider streams in real time

- **Session log timing, real run** `6f0b8e01…` (Oct 2):
  - `model_response_created` at 23:14:04.594.
  - The first `live_reply.md` chunk timestamp is 23:14:04.632, about 40 ms later.
  - `assistant_message_committed` at 23:14:06.473.

  So the deltas were written as the model produced them.
- **Live probe #1** (timed stdout capture): eight `run.output.delta` events, about 33 ms
  apart (17.59 → 17.84 s), each a fragment such as `'I ran echo one'` or
  `' first and received'`.
- **The final message streams briefly.** Across 208 sessions from Oct 1–2,
  `model_response_created` → `assistant_message_committed` took **p50 2.4 s, p90 5.9 s,
  max 15 s**.
- `sase agents show` already tells you to run `tail -f <dir>/live_reply.md`
  (`src/sase/agents/cli_show.py:100-102`). That shows the token stream today, which is a
  quick way to confirm the provider side works.

### 2.2 Muse never writes text next to tool calls

- **Corpus:** 1,584 sessions from Sept 20 to Oct 2; 109,416 `assistant_tool_calls_committed`
  events. Every one has only the keys `kind`, `message_id`, `response_id`, `tool_calls`.
  **Zero carry text.**
- **Probe #1** prompt: "write one short sentence … and in the SAME response call the shell
  tool". The model made both tool calls with no text: `finish_reason: "tool_calls"`, 177
  output tokens of which 107 were reasoning. It wrote text only in the final turn.
- **Consequence:** even with perfect TUI streaming, a Muse run has nothing to stream until
  its final ~2 seconds. The only exceptions are cases where Muse itself ends a turn early
  (§2.3).

### 2.3 The synchronous-shell change removed mid-run messages

Messages per session, for sessions with at least one tool call:

| Era (session date)                             | Sessions | 0 msgs | 1 msg | **≥2 msgs**     | Shell tool              |
| ---------------------------------------------- | -------- | ------ | ----- | --------------- | ----------------------- |
| ≤ 2026-09-23 (managed `bash`, background jobs) | 433      | 35     | 354   | **44 (10.2%)**  | 388 `bash`, 43 `shell`  |
| ≥ 2026-09-24 (`muse_synchronous_shell` on)     | 1,343    | 355    | 978   | **10 (0.7%)**   | 1,343 `shell`           |

Before the change, multi-message sessions looked like this. Artifact dirs
`ace-run/202609/20/20260920171616` and `…171617` contain live-reply chunks timestamped
across 1–1.5 hours:

```
22:17:51  Rebuild running; continuing once it completes.
22:28:04  Check gate running; will finalize on its result.
22:54:08  Still running with no output yet (output is piped …). Continuing to wait for the gate.
23:11:26  Bead sase-14n.10 complete. …
```

- Each message was a Muse turn ending with a new `command_id`, so each got its own chunk.
  This is the post-fix coalescing working as designed.
- These lines were on disk mid-run, so any incidental repaint showed them. That "progress
  ticker" is what disappeared when commands became synchronous on Sept 23.
- The chunking fix (Sept 20) did not change when anything reached disk or how the TUI was
  triggered. Before it, the same text showed up as roughly 25 dividers per reply; after
  it, as one.

### 2.4 The TUI ignores `live_reply.md` growth

What happens to a write:

- **The event arrives.** Live agent dirs are inotify-watched
  (`actions/agents/_live_watch_coverage.py`). The event mask includes `IN_MODIFY`
  (`util/fs_watcher.py:60-67`), and bursts coalesce over 50 ms.
- **It is discarded.** `artifact_path_affects_agents`
  (`actions/event_refresh/_artifact_paths.py:63`) accepts only the loader marker set
  (`_constants.py:24-35`: `agent_meta.json`, `done.json`, `running.json`, `waiting.json`,
  `pending_question.json`, `workflow_state.json`, `plan_path.json`, `retry_state.json`),
  plus `prompt_step_*.json`, `.ace_refresh_pulse`, and shallow directory paths.
  `live_reply.md` falls through to "ignored". `_dirty_surfaces_for_paths` returns `set()`,
  and `_on_artifact_change` exits at `_watcher.py:53`. The test
  `test_artifact_change_ignores_non_loader_artifact_content`
  (`tests/ace/tui/test_event_handlers_artifact_dirty_flags.py:384`) pins this.
- **The polling paths miss it too:**
  - The auto-refresh tick (10 s default, `main/parser_ace.py:66-69`) only refreshes the
    selected agent's *file* (diff) panel (`_auto_refresh_surfaces.py:34-60`).
  - The 1 s in-flight marker poll stats only marker files.
  - Surface tokens stat only project-level roots.
- **What does repaint the reply on a running agent** is the slow-tool tick:
  - It runs every 5 s (`widgets/prompt_panel/__init__.py:35, 214-277`).
  - It calls `refresh_slow_tool_metadata_from_cache` → `_update_display_impl`
    (`_agent_display.py:289-295`), which re-reads the live reply
    (`_agent_display_render.py:589-607`).
  - It runs only while `slow_tool_sources_have_pending(agent)` is true.

  Claude writes its narration and then calls a tool, so the narration is on disk while
  the tool is pending, and the tick paints it within 5 s. Muse's single message comes
  after its last tool result, so no tick is active.
- **The watcher logic has not changed in the relevant window.** The marker set at
  `794fbd3db9` (2026-08-27) is identical. So this is a long-standing limitation that Muse's
  behaviour exposes, not a new regression.

### 2.5 What you actually see: a finished reply hidden for 30–60 s

- Muse keeps working after its final message: `goal-reminder` and `verify-reminder` tasks,
  plus memory-reminder child sessions.
- **Reply committed → `terminal`**, across 208 sessions from Oct 1–2: **p10 12 s, p50 27 s,
  p90 60 s, max 116 s**.
  - Probe #1: reply done at 17.8 s, terminal at 83.5 s.
  - Probe #2: reply done at 8.1 s, terminal at 15.9 s.
- During that window the reply is fully in `live_reply.md` but the panel still shows no
  reply. It appears only when the process exits and the next marker write (finalization,
  `done.json`) triggers a repaint.
- From the user's seat it looks exactly like "the reply doesn't stream; it pops in at the
  end".

### 2.6 Confounder: about 31% of Muse runs never produce a reply at all

- 319 of 1,016 Muse runs from Sept 24 to Oct 2 have an empty `live_reply.md`.
- 317 of those end with an interrupted tool call. In the one I traced (`8b91b705…`), that
  call was `sase monitor start …`: a mechanical monitor/plan handoff that cancels Muse
  (`terminal: cancelled after tool result reconciliation`) before it writes any reply.
- That is expected behaviour, not a streaming bug. Keep it in mind when spot-checking:
  roughly a third of Muse agents legitimately end with no reply.

## 3. What `muse exec --json` Does and Doesn't Expose

Findings from three live probes against `muse-spark-1.3` in a scratch dir, plus the bundled
fixtures (`tests/llm_provider/fixtures/muse_exec_*`):

| Signal                              | stdout (`--json`)                        | session log (`$XDG_DATA_HOME/muse/sessions/Y/M/D/<sid>/session.jsonl`)                     |
| ----------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------- |
| Reply text deltas                   | ✅ `run.output.delta` (ephemeral)        | ❌ (only the committed message)                                                             |
| Final reply                         | ✅ `run.terminal.*` `payload.text`       | ✅ `assistant_message_committed.text`                                                       |
| Reasoning summaries (plaintext)     | ❌ never, even at `--reasoning-effort high` | ✅ `reasoning_summary_delta` / `reasoning_summary_committed`                             |
| Tool-call **arguments**             | ❌ (results only)                        | ✅ `assistant_tool_calls_committed.tool_calls[].args`                                       |
| Token usage                         | ❌                                       | ✅ `model_completed.usage` (already used by `_muse_session_usage.py`)                       |
| End of reply generation             | ✅ `task.lifecycle.completed` for the `model.meta.response` task right after the deltas | ✅ |

- `muse exec --help` has no flag for a more verbose event stream.
- **The session log is flushed live.** Probe #3 tailed it during a run and saw
  `reasoning_summary_*`, `assistant_tool_calls_committed`, and `assistant_message_committed`
  within about 0.2–0.5 s of their `recorded_at` (the 0.5 s poll interval included). Tailing
  it is therefore practical.
- **Reasoning-summary density**, from 258 sessions from Oct 1–2 with at least 5 model calls:
  - median **8** summaries per session (p90 28);
  - about 0.14 summaries per model call;
  - a median gap of **39 s** between summaries (p90 204 s);
  - 15 sessions had none.

  Typical text: _"Executing sequential shell commands with sleep and echo while noting tool
  parameters."_

## 4. Timeline

| When (UTC)        | Commit       | Effect on what reaches `live_reply.md`                                                                         |
| ----------------- | ------------ | -------------------------------------------------------------------------------------------------------------- |
| 2026-08-07        | `44fa7eee24` | Muse provider added. Each delta goes through `append_stream_text` and gets its own chunk and divider.           |
| 2026-08-27        | `794fbd3db9` | Watcher marker set already excludes reply files; unchanged since.                                              |
| 2026-09-20 17:25  | `a0244d7599` | Deltas coalesce to one chunk per run stream. Same bytes, same timing, fewer dividers.                           |
| 2026-09-23 22:09  | `28b3c1bab2` | `muse_synchronous_shell` (default on). No background waits, so no mid-run turn endings and no mid-run messages. |

## 5. Options

### A. TUI live-reply follow (provider-agnostic). **Recommended Phase 1**

Make a growing `live_reply.md` in the selected running agent's dir trigger a throttled
repaint of the prompt panel, without marking the Agents loader dirty.

- **Fixes:** Muse's final reply streams live, instead of appearing 27–60 s late. Claude,
  Codex, and the others get the same benefit for final messages and for narration written
  while no tool is pending.
- **Boundary:** presentation-only TUI state, so it stays in this repo (no `sase_core`
  change under the Rust boundary rule).
- **Cost:** about one repaint per throttle window while text is streaming, for one agent.
  The slow-tool tick already does a full `_update_display_impl` every 5 s for most running
  agents, so the extra cost is small.

### B. Muse reasoning-summary progress from the session log. **Optional Phase 2**

Tail `session.jsonl` during the run and emit `reasoning_summary_committed` text as live
progress.

- **Fixes:** the only source of *mid-run* Muse content, about one line every ~39 s. It is
  the closest analogue to Claude's narration.
- **Cost:**
  - It couples SASE to Muse's internal log. SASE already depends on that log for usage.
  - It needs a TUI surface. Thinking artifacts exist (`codex_thinking.jsonl`, written by
    the Codex, Claude, and Grok parsers), but `sase.ace.tui.thinking.read_codex_thinking`
    currently has **no consumers**.

### C. Prompt directive: "narrate before each tool call". Rejected

The model ignored the instruction when told directly (probe #1), and the corpus shows 0 of
109k tool turns with text. It would add prompt tokens for no output.

### D. Revert or loosen the chunking fix. Rejected

That brings back the roughly 25 dividers per reply. It cannot help, because the TUI ignores
both reply files equally.

### E. Provider writes `.ace_refresh_pulse` into the agent dir on chunk open/close. Stopgap only

The watcher already treats an in-agent-dir pulse as a row-exact trigger
(`_artifact_paths.py`, `artifact_dir_from_known_marker_path`). But it does so by arming an
**Agents delta load**, which is the expensive loader, held to a 5 s floor and the 10 s tick.
It conflates reply streaming with row reloads, and its latency is about 5–10 s. Use it only
if Phase 1 has to wait.

### F. Close the chunk at end of generation instead of at `run.terminal.*`. Minor polish

`task.lifecycle.completed` for the `model.meta.response` task follows the deltas
immediately. Closing on it would end the console line and mark "reply complete" 27 s
earlier.

- It is not needed for Phase 1: the panel reads the open chunk to EOF either way.
- Deltas carry only `command_id`, so it needs a small amount of extra state: "a model
  response task is open and has streamed deltas".

| Option                     | Visible effect for Muse               | Muse-specific? | Effort      | Main risk                                     |
| -------------------------- | ------------------------------------- | -------------- | ----------- | --------------------------------------------- |
| **A. TUI live-reply follow** | Final reply streams live (≈2–6 s)   | No             | Small–medium | Repaint cost and scroll behaviour; mitigated by throttle and guards |
| **B. Reasoning progress**  | Progress line about every 39 s mid-run | Yes           | Medium (+ TUI surface) | Internal log format; needs a renderer |
| C. Narrate directive       | None (model ignores it)               | Yes            | Trivial     | Wasted tokens                                 |
| D. Revert chunk fix        | Dividers return; no streaming gain    | Yes            | Trivial     | Reintroduces the bug                          |
| E. Refresh pulse           | Reply shows within about 5–10 s       | Yes            | Small       | Extra Agents loads; it's a hack               |
| F. Early chunk close       | Console newline/marker earlier        | Yes            | Small       | Small                                         |

## 6. Recommended Solution

### Phase 1: TUI live-reply follow (do this)

1. **Trigger, event-driven and zero cost when idle.** In
   `EventWatcherRefreshMixin._on_artifact_change` (`_watcher.py`), before the
   empty-targets early return at line 53, look for paths named `live_reply.md` or
   `live_reply_timestamps.jsonl` whose parent equals the selected agent's artifacts dir.
   Fire only when all of the following hold:
   - the Agents tab is current;
   - no attempt is pinned (`current_attempt_number is None`);
   - the selected agent is in a live status (`agent_has_live_file_panel` and
     `_LIVE_FILE_REFRESH_STATUSES` are the existing predicates to mirror).

   Resolve the artifacts dir from the in-memory `agent.get_artifacts_dir()`, the same way
   `_live_watch_coverage.py` does, so the render path does no stat/glob (tui_perf rule 8).
   On a hit, call a new `prompt_panel.request_live_reply_refresh(agent)`.
2. **Keep the loader untouched.** `artifact_path_affects_agents` should keep returning
   `False` for reply files, and the existing ignore test should keep passing. Add a sibling
   test asserting that a selected-agent reply write requests a panel refresh while
   `_dirty_agents` stays `False`.
3. **Repaint through the existing path (tui_perf rule 5).** Reuse the slow-tool tick's
   body: `refresh_slow_tool_metadata_from_cache(agent)` → `_update_display_impl(agent)`.
   Consider renaming it to something neutral such as `refresh_live_content_from_cache`.
   Apply the same guards as `_on_slow_tool_render_tick`: hint mode, attempt pinned,
   `NavigationGate`, and `context.is_current(...)`. Also defer while the prompt input is
   active (`_on_artifact_change` already has that machinery).
4. **Throttle.** Muse deltas arrive about every 33 ms. Use a leading-plus-trailing limiter
   of about 0.5–1.0 s with a scheduled/pending coalescing guard (tui_perf rule 2: a thin
   timer callback; heavy work stays wherever `_update_display_impl` already puts it).
   Always land a trailing repaint so the last tokens show.
5. **Fallback when inotify is unavailable.** Widen `_configure_slow_tool_render_tick` so
   the existing 5 s tick also runs while the selected agent is in a live status, not only
   while a tool call is pending. The panel's digest compare (`prompt_panel/__init__.py`
   `update()`) keeps no-change ticks from touching widgets.
6. **Scroll etiquette.** Follow the FINAL deck's rule (`widgets/decks/final/live.py`):
   follow the tail when the reader is at the bottom, and never yank a reader who has
   scrolled up. Check how `_update_display_impl` currently preserves scroll before
   choosing.
7. **Verify against tui_perf.**
   - Run `SASE_TUI_TRACE=1` while a Muse agent streams; repaints should stay at or under
     the throttle rate.
   - Run `SASE_TUI_PERF=1` and confirm j/k p95 stays under 16 ms with a streaming agent
     selected.
   - Take a `sase screenshot` mid-stream as visual evidence.
8. **Flag.** This changes user-visible refresh behaviour. Read `sase_flags.md` and decide
   whether to ship it behind a short-lived sunset flag (default on) for rollback.

Expected result: on Muse, the AGENT REPLY section fills in token by token during the 2–6 s
the reply is generated, instead of 27–60 s later. Every other provider's final message
benefits the same way.

### Phase 2 (optional): Muse live progress from reasoning summaries

1. **Tail thread.** In `MuseProvider._run_subprocess` (`muse_provider.py:468`), next to
   `start_completion_watchdog`, start a daemon `start_muse_session_progress_tail(session_id)`:
   - Locate the log with `_find_muse_session_log` (`_muse_session_usage.py`); retry until
     it appears.
   - Poll about every 0.5 s by byte offset, buffering any partial trailing line.
   - Stop when the process exits, after a final drain.
   - On a missing log, newer schema versions, or a `--no-session-log` passthrough, do
     nothing beyond a bounded diagnostic (mirror `_note_unknown_schema_version`).
2. **Extraction.** Take `runtime.session` events with `event.kind ==
   "reasoning_summary_committed"` and ignore `_delta`. Write `{"text", "timestamp"}`
   through the existing thinking-artifact helpers (`open_codex_thinking_file()` format).
   Optionally attach `following_action` from the next `assistant_tool_calls_committed`
   name and args, the same shape `_write_codex_thinking` already emits.
3. **Do not write summaries into `live_reply.md`.** That file is the *reply*: chunks,
   attempt archives, content search, and salvage all depend on it. Mixing in reasoning
   would reintroduce a "chunked poorly" symptom.
4. **TUI surface.** Without one, Phase 2 produces an artifact nobody sees. Either render
   the thinking artifact as a dim "progress" strip under AGENT REPLY for running agents
   (repainted by the Phase 1 trigger extended to the thinking file), or revive
   `sase.ace.tui.thinking`. Doing this generically also lights up the existing
   Codex/Claude/Grok thinking artifacts.

### Explicitly not recommended

- Option C, the narration directive (the model ignores it).
- Option D, reverting the chunking fix (it reintroduces the bug).
- Option E, refresh pulses, except as a stopgap.

### Side findings worth filing (proposed follow-ups; not filed by this researcher)

- **Tool-call arguments are available.** The Muse session log carries tool-call arguments
  that the stdout stream lacks. `_tool_call_muse.py` currently derives targets
  "honestly" from result previews. The same tail could fill in real arguments.
- **Thinking artifacts go unread.** `sase.ace.tui.thinking` appears to have no consumers,
  so the thinking artifacts written by Codex, Claude, and Grok are not shown anywhere in
  the TUI.
- **Muse's post-reply phase is long.** Reminder child sessions take a median 27 s and up
  to about 2 min after the final message. If that matters for throughput, look at whether
  Muse exposes a way to disable reminders in headless runs (`muse exec --help` shows none
  today).

## Appendix: Method

- **Code read:**
  - `src/sase/llm_provider/{muse_provider,_subprocess_muse,_subprocess_artifacts,_muse_session_usage,_tool_call_muse}.py`
  - the ACE watcher, auto-refresh, artifact-cache, and prompt-panel modules cited above
  - `git show a0244d7599`, plus the history of `_watcher.py` and `_artifact_paths.py`
- **Artifacts:**
  - all `~/.sase/projects/*/artifacts/ace-run/**/run_metadata.json` with
    `runtime: muse` dated before 2026-10-03;
  - their `live_reply*.{md,jsonl}` and `tool_calls.jsonl`;
  - Muse session logs under `~/.local/share/muse/sessions/2026/{09,10}/…`, before
    2026-10-03 for the corpus statistics.
- **Live probes:** three small `muse exec --json` runs using SASE's argv shape
  (`--enable-shell-tool`, `--disable-approval`, `--disable-sandbox`, and so on), the
  standard `muse-spark-1.3` model, a scratch workspace under `/tmp`, and harmless prompts.
  Their stdout was timestamped per line, and probe #3 tailed the session log while the run
  was in progress.
- **Limitation:** I did not drive a live TUI session. The TUI conclusions come from code,
  tests, and artifact timing. Phase 1 should be confirmed with a mid-stream
  `sase screenshot`.
