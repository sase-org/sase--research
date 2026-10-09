# Muse Reply card stays blank until the agent completes

**Researcher:** grk (independent swarm member)
**Date:** 2026-10-09
**Installed Muse:** 1.4.4-R5419.1
**Closed epic:** [sase-1fu](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1fu/README.md) (closed 2026-10-04)
**Plan:** `plan:202610/muse_reply_streaming.md`

This note is an independent diagnosis of the remaining user-visible failure:
a Muse SASE agent's Agents-tab Reply card shows no text until that agent
completes. It does not reopen sase-1fu's transport or follow work unless a
specific residual is named. Peer swarm reports from this turn were not read.

## Finding

sase-1fu made streamed Muse bytes *paintable*. The remaining blank card is
mostly *empty `live_reply.md` for almost the entire Muse turn*.

On current Muse, `muse exec --json` **does** emit token-level
`run.output.delta` events on a PIPE. A live 1.4.4-R5419.1 no-tool probe
produced **63 deltas over 1.84 s**, then `run.terminal.completed` with the
same 1131 characters. PIPE stdout is not holding those records until exit.

What SASE writes into the Reply card is only those deltas. Muse coding
agents spend nearly all of their wall time in tools. Across **344** recent
`runtime=muse` artifact dirs:

- **235** finished with a non-empty `live_reply.md`. The first timestamp is
  typically **~1.7 s after the last tool** (p50). Only **2 / 235** got a
  first chunk within 30 s of the first tool. **143 / 226** long tool runs
  (>60 s) opened the live reply at or after the last tool.
- **109** finished with a **0-byte** `live_reply.md`. **105 / 109** are
  `continuation_status=interrupted` (plan/monitor/handoff). Those turns
  never emit a user-visible assistant message, so the session phase stays
  on `No response content yet.`

The Reply follow then does what sase-1fu told it to do: leave the
first-paint placeholder in place until a timestamp chunk or stripped reply
text exists (`e1fa79db96`). For a 10-minute Muse coding turn that means
~10 minutes of `Waiting for agent response...`, then one or two seconds of
real streaming that races `done.json` and the DONE rebuild. That matches
"I never see any text until the agent completes."

The primary fix is product-shaped: show in-flight Muse *work* in the Reply
region (tools / stream status) during the quiet phase, and keep the
existing delta follow for the short final generation. Chasing PTY wrapping,
JSONL drain, or inotify is the wrong next move; those were the 1fu gaps
and they are no longer the user-visible failure.

## How the path works today

```
muse exec --json  (Popen stdout=PIPE, text=True)
        │
        ▼
stream_json_lines  (os.read, 64 KiB / 256-record budgets)
        │
        ▼
_process_muse_json_line
   run.output.delta  ──► append_stream_delta ──► live_reply.md (+ timestamps.jsonl), flush every fragment
   run.terminal.*    ──► state.terminal_texts only (NOT written to live_reply)
   task.lifecycle.*  ──► tool_calls.jsonl (not the Reply body)
        │
        ▼
ACE ArtifactWatcher (IN_MODIFY|IN_CLOSE_WRITE, 50 ms coalesce)
        │  live_reply.md is ignored by artifact_path_affects_agents
        │  so the roster loader stays out
        ▼
LiveReplyFollowMixin
   300 ms throttle, 1 s stat poll backstop
   empty snapshot → keep first-paint placeholder
   non-empty → replace only the live_reply_region, publish via AgentPromptPanel.update
        │
        ▼
hidden #agent-prompt-panel  →  Main document sink  →  visible Reply card
```

Authoritative sources:

- Parser contract: `src/sase/llm_provider/_subprocess_muse.py`
  (`run.output.delta` is live-display + salvage; `run.terminal.*` is
  `InvokeResult.content`).
- Artifact writes: `src/sase/llm_provider/_subprocess_artifacts.py`
  (`append_stream_delta` always flushes the file; Rich `FileProxy` is
  not flushed per fragment).
- Follow: `src/sase/ace/tui/widgets/prompt_panel/_live_reply_follow.py`
- Watcher route: `src/sase/ace/tui/actions/event_refresh/_watcher.py`
  `_route_live_reply_artifact_paths`
- First paint: `src/sase/ace/tui/widgets/prompt_panel/_agent_display_render.py`
  (`Waiting for agent response...`) and
  `_agent_display_agent_session_render.py` (`No response content yet.`)
- Docs: `docs/llms.md` (Muse event stream + live reply) and `docs/ace.md`
  AGENT REPLY.

Muse's interactive TUI/SDK path is a different protocol. The
`gh:meta-models/muse-code-sdk` cookbook `stream_a_turn.py` teaches
`item/delta` as live text and `item/completed` as authoritative. SASE does
not speak MSP; it speaks `muse exec --json`. That adapter **does** forward
assistant tokens as `run.output.delta` (live probe below). It does **not**
forward `runtime.session` / `text_delta` on that stdout, and session logs
omit ephemeral `run.output.delta` records, so you cannot reconstruct
mid-stream text from `~/.local/share/muse` after the fact.

## What sase-1fu already landed

| Phase | Commit | What it fixed |
| --- | --- | --- |
| live-reply-follow | `2307212bcd` | Selected Reply follows `live_reply.md` without a roster reload |
| jsonl-reader | `392983091d` | Drain every complete JSONL record in a burst; incremental UTF-8 |
| console-framing | `ca1ffac8e3` | Do not let Rich `FileProxy.flush` split streamed words |
| streaming-validation | `7b39db7b67` | Mounted gated-Muse test + docs |
| empty placeholder | `e1fa79db96` | Empty follow snapshots no longer clobber first-paint copy |

Landing review (`sase-1fu` note #2) declined a real Meta capture because
1.4.2-R4684.1 was quota-blocked (429) until 2026-10-05. The mounted test
proves transport-to-paint with a **fake** Muse child that emits deltas on
demand. It **monkeypatches** `on_live_reply_artifact_change` rather than
proving inotify (`tests/ace/tui/test_live_reply_follow_mounted.py`). The
plan itself already warned: ACE can only display bytes Muse has emitted,
and Muse is usually quiet through tool work.

The empty-placeholder tale is working as designed. Combined with a
tool-quiet `live_reply.md`, it *is* the blank card.

## Evidence

### 1. Live Meta probe (this turn) — token deltas are real on PIPE

Command (workspace `/tmp/muse-jsonl-probe-ws`):

```text
muse exec --json --trust-workspace --disable-approval
  --disable-shell --disable-web-tools --disable-write
  --disable-reminders --no-session-log
  --max-model-steps 1 --reasoning-effort low
  "Do not use any tools. Write four short paragraphs explaining how DNS ..."
```

Reader: non-blocking `os.read` on `stdout=PIPE`, wall-clock per JSONL line.

| Metric | Value |
| --- | --- |
| Muse | 1.4.4-R5419.1 |
| Exit | 0 in 5.571 s |
| First event | 0.329 s (`runtime.command.accepted`) |
| First `run.output.delta` | **3.666 s** (`When you enter`) |
| Last delta | 5.504 s |
| Delta count | **63** |
| Delta span | **1.838 s** |
| Fragment sizes | 2–54 characters (token/word pieces) |
| `run.terminal.completed` | 5.539 s, 1131 chars = sum of deltas |
| Other `*delta*` payload types on stdout | none |

An `--provider echo` control emitted one 32-char delta and the matching
terminal at t=0.257 s, process exit 0.282 s. The JSONL reader is seeing
lines as Muse writes them.

Conclusion: **PIPE buffering is not why the Reply card is blank.** Muse
1.4.4 streams the *final assistant message* as many `run.output.delta`
records. It is quiet until that message starts (here ~3.3 s of
`task.lifecycle.status` "opening meta model stream", then tokens).

### 2. Checked-in `muse exec` fixtures look one-shot because the answers are one word

`tests/llm_provider/fixtures/`:

| Fixture | Deltas | Delta text | Terminal seq |
| --- | --- | --- | --- |
| `muse_exec_read_tool_R708.1.jsonl` | 1 at seq 45 | `bravo` | 60 |
| `muse_exec_shell_tool_R3401.1.jsonl` | 1 at seq 65 | `DONE` | 83 |
| `muse_exec_write_bash_tools_R708.1.jsonl` | 1 at seq 71 | `DONE` | 86 |

Those captures are consistent with a short final answer after tools, not
with "Muse never streams." `test_agent_reply_muse_chunks.py` *synthesizes*
token-level deltas and only asserts one timestamp divider, which is the
`a0244d7599` coalescing contract.

The R708.1 Meta wire facet on the second model stream reports
`wire_events_seen: 10` / `last_wire_event_type: response.completed` while
`--json` still exposed a single five-character `run.output.delta`. Short
answers collapse; long answers (live probe) do not.

### 3. Real SASE Muse artifacts: reply bytes arrive after tools, or never

Sample: every 202610 `run_metadata.json` with `runtime=muse` under
`~/.sase/projects/*/artifacts/ace-run/` (**344** dirs).

| Bucket | N | What it means for the Reply card |
| --- | --- | --- |
| Non-empty `live_reply.md` | 235 | Follow *could* paint, but the first byte is late |
| Exactly one timestamp chunk | 160 / 235 | One run stream, one divider |
| Two or three chunks | 75 / 235 | Almost always a later run/attempt; several files have two timestamps at `byte_offset` 0 (truncated retry) |
| Empty `live_reply.md` | 109 | Placeholder for the whole turn |
| Empty + `interrupted` | 105 / 109 | Handoff; no assistant message |
| `response.md` present | 0 | DONE view for Muse is `live_reply` chunks, not a separate response file |

Timing on the 235 non-empty dirs (ISO timestamps on `tool_calls.jsonl`
vs `live_reply_timestamps.jsonl`):

- `first_live_reply_ts - last_tool`: min −12842 s (outlier / clock skew or
  reused files), **p50 +1.73 s**, max +38.9 s
- First chunk within −5..+30 s of last tool: **150 / 235**
- First chunk within 30 s of first tool: **2 / 235**
- Tool span > 60 s and first chunk near/after last tool: **143 / 226**

Worked example, `bob-cli-60.land--code` artifacts
`.../ace-run/202610/09/20261009172429` (from the earlier pass on this
turn): tools 21:24:48 → 21:35:20 (~10.5 min, 184 tool events), first
`live_reply` timestamp 21:35:26.2 (~6 s after the last tool), one chunk,
2405 bytes vs `usage.json` `output_tokens: 50631`. Almost all tokens are
tools/reasoning, not Reply prose.

A two-timestamp example from this afternoon,
`gh_sase-org__sase/.../20261009173441`, has both JSONL rows at
`byte_offset` 0. The visible body is the *second* stream (an acrostic plus
"Research complete..."), timestamped 1.7 s after the last of 110 tools.
The first stream's bytes were overwritten; the timestamps file still has
both rows.

### 4. Parser gap that still matters at the edges

`_capture_run_terminal` records `payload.text` into `state.terminal_texts`
and never calls `append_stream_delta`. `_resolve_muse_content` returns
that text as `InvokeResult.content` after the process exits.

Consequences:

- If Muse ever emits a terminal without deltas, `live_reply.md` stays
  empty for the whole RUNNING window. DONE rendering in
  `_agent_display_render.py` prefers timestamped chunks, then
  `get_response_content()` (`response.md`). Muse dirs in this corpus have
  **no** `response.md`, so a textless-delta run would also look empty
  after completion unless `chat_path` is used (that fallback is on the
  session helper `render_agent_reply_content`, not on the solo DONE
  branch).
- In the live probe and in 229/235 completed non-empty dirs, deltas *do*
  exist, so this gap is not the common path. It is still the right
  salvage for interrupted-without-deltas and for a future schema drift.

### 5. Follow / paint residuals (secondary)

These can hide a *short* final burst; they do not explain ten minutes of
blank.

- **Empty-snapshot skip** (`_live_reply_follow.py` `collect_apply`):
  correct, and the reason the placeholder survives the whole tool phase.
- **`replaced != 1`**: `update()` is skipped; `accepted` stays false so
  the mixin retries. A missing `live_reply_region` (hint mode, attempt
  pin, generation change, session identity mismatch via
  `current_agent_session_turn_row`) loops until context matches.
- **`update_display` cancels follow** then reconfigures. The DONE rebuild
  (status flip on `done.json`, which *is* roster-relevant) tears down the
  live region and paints AGENT CHAT from chunks. A 100 ms one-word delta
  + terminal + exit can complete before the 300 ms follow applies, so the
  first visible text is the completed view.
- **Mounted test injects watcher events.** Real inotify on an
  open-append-flush of `live_reply.md` is still unproven in CI. The 1 s
  poll would still converge a growing file; an empty file has nothing to
  converge.
- **Slow-tool tick** (`_on_slow_tool_render_tick`) refreshes cached tool
  metadata; it does not call `update_display`, so it does not cancel
  follow. Muse agents *do* qualify for `supports_slow_tool_sources`
  (`agent.is_agent_entry`). Tool activity can appear on the tool-call
  surface while Reply stays on the waiting sentence. That split is easy
  to miss if you are staring at the Reply card.

## Ranked remaining causes

1. **Muse emits no `run.output.delta` until the final assistant message,
   which is after tools.** SASE copies only those deltas into
   `live_reply.md`. This is the common, evidence-backed cause.
2. **Handoff / interrupted turns never get a final message**, so
   `live_reply.md` stays 0 bytes and a session phase keeps
   `No response content yet.`
3. **The final generation is short (often 0.1–2 s) and races the DONE
   rebuild**, so even a working follow is easy to miss. One-word fixture
   answers are a single delta.
4. **Terminal text is not mirrored into `live_reply.md`**, so a
   delta-less terminal cannot paint while RUNNING and may not paint on
   the solo DONE path either (no `response.md` for Muse).
5. **Follow/identity/hint/pin edge cases** can drop a region replace.
   Unlikely as the *steady* blank-until-done report; worth a log line
   when `replaced != 1`.

## How to confirm on the next live Muse agent

Do not guess. Split emission from paint with one running agent selected
on the Agents tab:

```bash
# artifacts dir from the selected row (or `sase agent show`)
tail -f "$SASE_ARTIFACTS_DIR/live_reply.md"
```

| What you see | What to fix |
| --- | --- |
| File empty until the last seconds, then a burst; TUI placeholder until DONE | Cause 1. Show tools in Reply; optional salvage of terminal text |
| File grows for seconds and TUI stays on Waiting… | Follow/paint (inotify, `replaced != 1`, session identity, hint/pin) |
| File empty even after DONE, TUI then shows a reply | DONE path is reading `chat_path` / some other file; parser never got deltas |
| File empty after DONE and TUI empty | Interrupted handoff, or terminal-only with no `response.md` |

A second probe, if you want token timing on a *tool-using* run:

```bash
muse exec --json --trust-workspace --disable-approval \
  --workspace /tmp/muse-jsonl-probe-ws \
  --max-model-steps 3 \
  'Read README.md and then write a 200-word summary. Timestamp nothing.'
```

Wrap with the same per-line `os.read` clock. Expect: many
`task.lifecycle.*` / `tool.result` with **zero** `run.output.delta`, then
a burst of deltas, then `run.terminal.completed`.

## Recommended fix sequence

Work in this order. Each step is independently shippable.

### 1. Tool-aware Reply placeholder (the actual UX bug)

Keep `live_reply.md` as assistant text. Change the *empty* Reply region
so it is not a static waiting sentence while Muse is clearly working.

Concrete shape:

- In `_snapshot_renderables` / first paint, when chunks and stripped
  `live_text` are empty **and** `tool_calls.jsonl` has entries, render a
  dim live status from the already-cached slow-tool sources: last tool
  name, running vs completed, elapsed, maybe a one-line `task.lifecycle.status`
  (`opening meta model stream attempt 1/10`).
- Do not write that status into `live_reply.md` (it would become a
  timestamped assistant chunk).
- When the first real delta arrives, existing follow replace still wins.
- Extend `tests/ace/tui/widgets/test_live_reply_follow.py` so an empty
  reply plus pending Muse tools publishes something other than the
  waiting sentence.

This is presentation, so it stays in the sase TUI. It matches
`tui_perf.md`: collection stays off-thread, apply stays a region
replace, reply writes still must not dirty the Agents roster.

### 2. Mirror terminal text into `live_reply.md` before the parser returns

In `_capture_run_terminal`, if `payload.text` is non-empty and this run
stream has no open live chunk (or the concatenated deltas are empty),
call `append_stream_delta(..., new_chunk=True)` — or write once after
`_close_delta_chunk` in `stream_and_parse_muse_json_output`'s `finally`
using `_resolve_muse_content` when `live_reply.md` is still empty.

That covers delta-less terminals and gives the follow ~one flush *before*
`done.json` exists. Do not append terminal text on top of deltas when
they already equal the terminal (duplicate chunk). The salvage comment
in `_resolve_muse_content` already describes this relationship.

### 3. Make the DONE race lose less often

- Flush and close live reply in `finally` **before** usage/metadata
  writes (already the order today). Host `done.json` is later; keep it
  that way.
- Optional: if `replaced != 1` after a non-empty snapshot, log once and
  force a cheap `update_display` rather than a silent retry. Cheap
  because it is the failure path.
- Recapture a 1.4.4 long-answer JSONL fixture with dozens of deltas so
  tests stop looking like Muse only ever emits `DONE`.

### 4. Session interrupted turns

A plan/monitor handoff with 0-byte `live_reply.md` should not look like a
hung model. The session renderer already has `No response content yet.`
Replace that, for interrupted Muse members, with a one-liner from
`continuation_status` / the successor's name (`handed off to …`). Out of
scope for token streaming; in scope for "the Reply card is empty."

### 5. Leave these alone unless a diagnostic table row says otherwise

- PTY / `stdbuf` / `PYTHONUNBUFFERED` around `muse exec`. Live PIPE
  already delivers token deltas.
- Re-draining `stream_json_lines`. Burst dispatch is proven by echo
  (13 records in 8 ms) and by the 63-delta Meta run.
- Parsing Muse session logs for `text_delta`. Ephemeral `run.output.delta`
  is omitted there by design; `--json` stdout is the live source.
- Showing `reasoning_delta` / `settings.tui.show_reasoning`. The binary
  has those strings; `--json` stdout in the live probe did not. A
  separate epic if product wants reasoning in Reply.
- Switching SASE to MSP `item/delta` just to get streaming. `--json`
  already streams the final message.

## Suggested verification after a fix

1. `tail -f live_reply.md` plus a selected Agents-tab Reply during a
   real Muse coding agent: placeholder becomes tool status while tools
   run; Reply prose appears during the last 1–2 s, *before* the row
   flips to DONE.
2. Focused tests: `test_live_reply_follow.py`,
   `test_live_reply_follow_mounted.py`, `test_agent_reply_muse_chunks.py`,
   plus a new 1.4.4 multi-delta fixture parse.
3. A no-tool `muse exec --json` like the probe in this note: many
   `run.output.delta`, growing `live_reply.md` mid-process, TUI follow
   paints before terminal.
4. An interrupted `--plan` Muse turn: Reply phase is not a naked
   waiting sentence.

`just check` is the agent verification recipe. Do not run
`just check-full` unless a CI repair needs it.

## Open questions (narrow)

- Does Muse ever emit intermediate assistant narration *between* tools
  on `--json`? This corpus says almost never. One live tool-using capture
  would settle it.
- Why do some retry/continuation runs write a second timestamp at
  `byte_offset` 0 (truncated `live_reply.md` with a leftover JSONL row)?
  That can render a blank divider plus the new body. Separate from
  blank-until-done, but ugly.
- Solo DONE rendering does not consult `get_chat_response_content`. If
  anyone still sees a post-DONE reply with a 0-byte `live_reply.md`,
  that path is the place to look.

## Sources

- `src/sase/llm_provider/_subprocess_muse.py`
- `src/sase/llm_provider/_subprocess_artifacts.py`
- `src/sase/llm_provider/_subprocess_stream.py`
- `src/sase/llm_provider/muse_provider.py` (`Popen(..., stdout=PIPE, text=True)`)
- `src/sase/ace/tui/widgets/prompt_panel/_live_reply_follow.py`
- `src/sase/ace/tui/widgets/prompt_panel/__init__.py` (`update`, document sink)
- `src/sase/ace/tui/widgets/prompt_panel/_agent_display_render.py`
- `src/sase/ace/tui/actions/event_refresh/_watcher.py`
- `src/sase/ace/tui/actions/event_refresh/_artifact_paths.py`
- `src/sase/ace/tui/util/fs_watcher.py` (`DEFAULT_COALESCE_S = 0.05`)
- `docs/llms.md` Muse event stream + Live Reply File
- `docs/ace.md` AGENT REPLY
- `plan:202610/muse_reply_streaming.md`
- `plan:202610/live_reply_empty_placeholder.md`
- `sase bead read sase-1fu`
- `tests/llm_provider/fixtures/muse_exec_*_{R708.1,R3401.1}.jsonl`
- `tests/ace/tui/test_live_reply_follow_mounted.py`
- Live `muse exec --json` echo + Meta probes, 2026-10-09, Muse 1.4.4-R5419.1
- 344 `runtime=muse` artifact dirs under `~/.sase/projects/*/artifacts/ace-run/202610/`
- `sase/repos/external/gh/meta-models/muse-code-sdk` (`stream_a_turn.py`,
  `schema/msp/transcripts/text-run-single-turn/`)
