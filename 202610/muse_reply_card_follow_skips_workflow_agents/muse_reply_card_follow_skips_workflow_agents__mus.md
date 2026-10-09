# Muse Reply-Card Streaming: Why the Reply Card Stays Empty Until Completion

**Researcher:** mus (independent swarm report; no peer reports consulted)
**Date:** 2026-10-09
**Question:** In the SASE TUI, a Muse agent's "Reply" card shows no text until
the agent completes. How do we fix live reply streaming for Muse?

## Top finding

The Muse CLI is not the bottleneck, and SASE's Muse stream parser is not
broken. Live `run.output.delta` text **does** arrive incrementally and SASE
**does** write it to `live_reply.md` as it arrives (verified end-to-end
against the real CLI). The Reply card starves because of *what the CLI
chooses to emit*: **model turns that drive tool calls produce zero text
deltas, and all tool activity is emitted as `task.lifecycle.*` /
`tool.result` events that SASE's Muse parser deliberately ignores for live
display.** A typical agent run spends most of its life in tool phases, so
`live_reply.md` sits empty (or nearly so) until the final answer streams in
the last seconds. The fix is to project tool/progress activity into the live
reply, not to repair the delta pipeline.

## Method

- Read the full chain independently from source: CLI argv construction
  (`src/sase/llm_provider/muse_provider.py`, `_muse_launch.py`), the Muse
  JSONL parser (`src/sase/llm_provider/_subprocess_muse.py`), the shared
  stream loop (`_subprocess_stream.py`), artifact writers
  (`_subprocess_artifacts.py`), the TUI Reply render path
  (`ace/tui/widgets/prompt_panel/_agent_display_content.py`,
  `_live_reply_follow.py`), the artifact cache
  (`agent/artifact_files_cache.py`), and the existing tests.
- Ran three **live** probes against the installed CLI
  (`muse 1.4.4-R5419.1`, far newer than the `R708.1` release the checked-in
  fixtures were captured from), timestamping every stdout event:
  1. pure-text poem (no tools), 2. tool-only run (`write_file`, reply DONE),
  3. mixed run (3-sentence plan, then `write_file`, then DONE).
- Ran SASE's own parser (`stream_and_parse_muse_json_output`) against a live
  `muse exec` subprocess while sampling `live_reply.md` size every 0.5 s.
- Ran the existing suites: `test_muse_provider_stream.py` +
  `test_agent_reply_muse_chunks.py` (20 passed).

## Finding 1 — The CLI streams text incrementally (CLI exonerated)

Probe 1 (pure text, 6.5 s run): **46 `run.output.delta` events starting at
t=2.6 s**, ~4 s before completion. Small word-fragment payloads
(`'Al'`, `'one upon'`, `' the granite'`), i.e. genuine token streaming.

Probe 3 (mixed, 13.6 s run): the 3-sentence plan streamed as 9 deltas at
t=3.0–3.2 s, long before the run ended.

So "the CLI buffers everything until the end" is **false** on the current
CLI. (Caveat: it was plausibly true before — every checked-in `R708.1`
fixture contains exactly **one** `run.output.delta` holding the entire reply,
emitted immediately before the terminal event. See Finding 4.)

## Finding 2 — Tool phases emit no displayable text (root cause)

Probe 2 (tool run, 9.3 s total):

| t (s) | event | text shown in Reply? |
|---|---|---|
| 3.2 | model stream opens/completes (drives `write_file`) | no — no delta emitted |
| 3.3 | `task.lifecycle.output` + `tool.result` (`wrote 2 bytes…`) | no — parser ignores both for live display |
| 4.7 | `run.output.delta` (`DONE`) | **yes, first byte** |
| 4.8 | model stream completed | — |
| 9.3 | `run.terminal.completed` | run ends |

Probe 3 confirms the pattern at larger scale: the tool turn at t=8.2–8.4 s
(`model.meta.response` → `tool:write_file`) produced **zero deltas**; the
only deltas in the whole 13.6 s run were the plan text (t≈3 s) and the final
`DONE` (t=9.6 s).

The parser's own docstring states the policy: deltas go to `live_reply.md`,
terminal text is authoritative, and `task.*` failures are diagnostics. The
consequence is structural: **`live_reply.md` only ever contains model-spoken
text, and tool-driving turns usually contain none.** Other providers do not
have this hole to the same degree — e.g. Codex writes every assistant
message via `append_stream_text` (`_subprocess_codex.py`), so each model
turn lands in the live reply even when its purpose is a tool call. Muse's
equivalent per-turn content (status messages like `opening meta model stream
attempt 1/10`, `task.lifecycle.output` chunks, `tool.result` summaries)
never reaches the file.

## Finding 3 — SASE's parser and file pipeline stream correctly (plumbing exonerated)

Feeding a live `muse exec` subprocess through
`stream_and_parse_muse_json_output` with `SASE_ARTIFACTS_DIR` set:

```
live_reply.md size: -1@0.0s, 0@0.5s, … 118@2.5s, 306@3.0s, 459@3.5s (complete, process ran to ~6s)
artifacts: live_reply.md, live_reply_timestamps.jsonl, run_metadata.json, usage.json
```

First byte at 2.5 s, full text at 3.5 s — the file grows live with a flush
per delta (`append_stream_delta`), and timestamps get one entry per run
stream. One probe initially showed an empty artifacts dir; that was a probe
bug (the var was set on the child's env, not the parser's process env), not
a product bug. The 20 existing stream/reply tests pass unmodified.

## Finding 4 — The TUI display path has no Muse-specific branch (display exonerated, with one caveat)

`grep -i muse src/sase/ace/` hits only a provider style color and a query
profile list. Reply rendering (`render_agent_reply_content`), the
live-follow watcher/poll/throttle (`_live_reply_follow.py`: file watcher +
1 s signature-poll backstop + 0.3 s throttle), and the artifact cache are all
provider-agnostic. No Muse-specific gate was found that could blank the card.

Caveat: anyone still running a Muse CLI of the `R708.1` era gets literally
one end-of-run delta (per the fixtures), which reproduces the reported
symptom exactly with zero SASE-side fault. The parser's fixture convention
is explicitly release-keyed ("when Muse renames a payload type, the right
fix is a re-capture"), and the vocabulary has already drifted once: current
`R5419.1` emits `task.lifecycle.tool_output_ref`, which no parser constant
names (harmless today — unknown types are ignored by design — but it proves
the stream keeps evolving under us).

## Finding 5 — The terminal event lags output by seconds (aggravating factor, CLI-side)

In both tool probes the last content arrived 4–4.5 s before
`run.terminal.completed` (4.7 s → 9.3 s; 9.6 s → 13.6 s). The tail is session
finalization (`reminder.child_run` tasks in the event log), not model work.
This stretches the "nothing is happening" window: even the final answer sits
complete while the agent still shows RUNNING. Nothing in SASE can shorten
this; it only matters for expectations (and it means the Reply card *could*
show the final text seconds before DONE whenever deltas arrived — consistent
with the card working at all).

## Recommended fixes (ranked)

1. **Project tool/progress activity into `live_reply.md` (the actual fix).**
   In `_process_muse_json_line` (`src/sase/llm_provider/_subprocess_muse.py`),
   handle a small allowlist of already-observed live events in addition to
   `run.output.delta`: `task.lifecycle.side_effect_intent` with
   `operation: tool:<name>` → one compact line (e.g. `⚙ write_file…`);
   `task.lifecycle.output` / `tool.result` → a truncated one-line summary;
   `task.lifecycle.status` `event.message` → progress line. Write them as
   clearly-marked progress (separate timestamped chunk per task stream, or a
   distinct prefix) so they never pollute the authoritative terminal reply,
   mirroring how Codex surfaces per-turn activity. Add parser tests in
   `tests/llm_provider/test_muse_provider_stream.py` asserting the live file
   grows during a tool-only fixture while `content` still equals exactly the
   terminal text, plus a TUI render test that progress chunks render in the
   Reply card. This is the only recommendation that changes what the user
   sees during the 95%-of-runtime tool phases.
2. **Set a CLI version floor and detect the old behavior.** Add a
   `muse --version` check (doctor or provider advisory) warning when the CLI
   predates incremental `run.output.delta` streaming, and re-capture the
   `R708.1` fixtures against the current release per the file's own
   convention. Cheap insurance against "fixed for me, broken for them"
   reports.
3. **Do not rewrite the delta pipeline.** Findings 1 and 3 show the
   transport, the non-blocking `stream_json_lines` loop, the flush-per-delta
   writes, and the TUI follow (watcher + 1 s poll + 0.3 s throttle) all work.
   A refactor here would spend the budget without moving the symptom.
4. **Optional, low value:** during the CLI-side finalization lag (Finding 5),
   the TUI could label a complete-but-unterminated live reply as
   "finalizing…". Cosmetic; do only if users still report confusion after
   fix 1.

## How to verify the fix

- Replay probes 2 and 3 through the patched parser: `live_reply.md` must be
  non-empty within ~1 s of the first tool event while `content` remains
  exactly the terminal text (no duplication — the existing
  `test_muse_stream_returns_the_terminal_text_without_delta_duplication`
  regression guards this).
- `just check` (or at minimum the two suites above) plus a new tool-activity
  fixture test.
- Manual: run a tool-heavy Muse agent in `sase agent` with the fix and watch
  the Reply card — progress lines should appear during tool phases instead
  of `Waiting for agent response…` until DONE.

## Reproduction appendix

- CLI: `muse 1.4.4 (1.4.4-R5419.1)`; auth via `~/.config/muse/auth.json`.
- SASE argv used in probes (matches `MuseProvider.invoke` minus prompt
  templating): `muse exec --json --workspace <dir> --model muse-spark-1.3
  --reasoning-effort minimal --disable-sandbox --disable-approval
  --trust-workspace --user-input-auto-resolve --no-foreign-personal-context
  --session-id <uuid> --prompt-file <file>` with `MUSE_NO_AUTO_UPDATE=1`.
- Probe technique: `select`-loop over `Popen.stdout`, recording
  `(arrival_time, payload_type, text_preview)` per JSONL line; SASE-side
  check via `stream_and_parse_muse_json_output` + 0.5 s sampler thread on
  `live_reply.md` size.
- Key source files: `src/sase/llm_provider/_subprocess_muse.py` (parser,
  delta/chunk policy), `src/sase/llm_provider/muse_provider.py` (argv),
  `src/sase/llm_provider/_subprocess_artifacts.py` (`append_stream_delta`),
  `src/sase/ace/tui/widgets/prompt_panel/_live_reply_follow.py` (follow),
  `src/sase/agent/artifact_files_cache.py` (`read_reply_chunks`,
  `_TailCache`), `tests/llm_provider/fixtures/muse_exec_*` (single-delta
  era evidence). Recent related commits: `a0244d7599` (coalesce deltas into
  one live-reply chunk), `7b39db7b67` (validate live Muse reply streaming).
