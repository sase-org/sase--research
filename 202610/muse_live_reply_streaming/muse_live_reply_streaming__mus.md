# Muse provider output streaming: history, live measurements, and recommendation

Researcher: mus (`__mus`). Independent swarm report. I did not consult peer
reports; all findings below are from the repo, the shipped Muse CLI, and live
runs I performed myself on 2026-10-03.

## TL;DR and recommended solution

**Do not rewrite the Muse stream parser. It already streams.** I verified
end-to-end against the real `muse exec` (1.4.2-R4684.1) that every
`run.output.delta` is forwarded to the console and to `live_reply.md`
immediately on arrival, coalesced into one timestamped chunk per run stream.
The chunk-coalescing fix (commit `a0244d7599`) did not break forwarding — the
forwarding code path is exercised live in my measurements below, and all 18
existing stream/chunk tests pass.

What *is* true, and what I believe explains the "streaming never worked since"
perception:

1. **Delta pacing is controlled by the Muse CLI, not by SASE, and it is
   inconsistent.** The same 1.4.2 binary delivered a 950-char reply as a
   single ~40 ms burst of 26 deltas, and a 4561-char reply as 430 deltas
   spread over 16.7 s. Short replies will always *look* unstreamed no matter
   what SASE does.
2. **Console fragments compete with the Rich `Live` timer.** Muse is the only
   provider that prints sub-message fragments (`print(text, end="")`);
   every other provider prints whole messages with newlines. Under
   `provider_timer`'s 2 Hz `Live` redraw this is the one Muse-specific
   display-layer risk I could not fully verify headlessly.

**Recommended solution (minimal, in order):**

1. **Keep the coalesced-chunk design.** Do not revert `a0244d7599`; its tests
   (`test_muse_provider_stream.py`, `test_agent_reply_muse_chunks.py`) lock
   correct behavior (one divider per run stream, terminal text authoritative,
   deltas salvage-only).
2. **Fix the one plausible live-display defect: route Muse console fragments
   through the Rich console** (or suspend the `Live` timer while a delta
   burst is printing) instead of raw `print(text, end="")`, and verify on a
   real TTY with a long reply. Small change, confined to
   `append_stream_delta`'s console branch / the Muse provider's timer use.
3. **Document that streaming pace is CLI-controlled**, so a bursty short
   reply is not misfiled as a SASE bug again.
4. **Only if a programmatic (API-level) stream is wanted**, add an optional
   provider-neutral `on_delta` callback to `LLMProvider`, implemented first
   for Muse (the only provider whose CLI emits fragment deltas). Do not add
   a Muse-only streaming API; every other provider shares the blocking
   `invoke` + `live_reply.md` side-channel contract.

## 1. History: what "used to" work and what the chunk fix changed

- `muse exec --json` emits one JSON envelope per stdout line. The reply
  arrives twice in different forms: incremental `run.output.delta` fragments
  (`durability: ephemeral`, `payload.text` concatenates to the reply, splits
  mid-word) and one authoritative `run.terminal.*` event (`payload.text` is
  the reply). Parser rules live in
  `src/sase/llm_provider/_subprocess_muse.py`.
- Before 2026-09-20, each delta went through `append_stream_text()`, which
  treats every call as a whole assistant message: one timestamp entry and one
  blank-line separator **per token fragment**. The metadata panel showed ~25
  `AGENT CHAT` dividers with breaks mid-word and mid-inline-code.
- Fix `a0244d7599` ("coalesce output deltas into one live-reply chunk per run
  stream") added `append_stream_delta()` with an explicit `new_chunk` flag,
  keyed on `command_id`, then `run_stream.id`, then an `<unkeyed>` sentinel.
  First delta of a stream opens one timestamped `live_reply.md` chunk; later
  deltas append bare text; the matching `run.terminal.*` closes it with a
  newline. Console printing changed from `print(text)` per delta to
  `print(text, end="")` per delta plus one newline at chunk close
  (`test_muse_stream_prints_one_console_block_per_run_stream` locks
  `"It doesn't split\nnext\n"`).
- Crucially, **both versions forward every delta on arrival** (file append +
  `flush()` + console `print` with `flush=True`). The fix changed *framing*,
  not *liveness*. Nothing in the diff delays, buffers, or drops a delta.

## 2. How streaming works today (all layers SASE controls)

| Layer | Mechanism | Verdict |
|---|---|---|
| CLI stdout | `run.output.delta` JSONL lines, flushed by CLI in real time (proven: events arrive mid-run, well before process exit) | streams, CLI-paced |
| `stream_json_lines` (`_subprocess_stream.py`) | `select` + nonblocking `readline`, per-line dispatch | shared by all providers, no Muse special-casing |
| `_stream_output_delta` (`_subprocess_muse.py`) | per-delta `append_stream_delta` → `live_reply.md` append+flush, console print | forwards live |
| `live_reply.md` + `live_reply_timestamps.jsonl` | TUI `TailCache`/`read_reply_chunks`, cache keyed on file mtime+size; render path (`_agent_display_content.py`, `_agent_display_render.py`) is provider-neutral | file-driven live display, nothing Muse-specific |
| `run.terminal.*` | authoritative reply; `InvokeResult.content`; deltas never appended to content (no doubling) | correct |
| Usage | recovered post-exit from the `--session-id` session log (`_muse_session_usage.py`) | not streamable, by design |

Console streaming for every other provider goes through `append_stream_text`
→ `print(text)` (whole messages, newline-terminated). Muse is the only
fragment streamer, hence the only `end=""` printer.

## 3. Live measurements (2026-10-03, Muse 1.4.2-R4684.1, `muse-spark-1.3`)

All runs used piped stdout with per-line arrival timestamps, so burst vs.
spread is observed fact, not inference.

**Run A — short reply, raw CLI** (`muse exec --json`, 150-word story prompt):
26 deltas (~30–50 chars each), **all arriving within ~40 ms at t=19.5 s**,
after ~7.6 s of silence; `run.terminal.completed` (946 chars = exact
concatenation of the deltas) at t=23.8 s. Process exit followed. stderr
carried only `muse: workspace root/trust` diagnostics — no reply text.

**Run B — long reply, raw CLI** (800-word story): **430 deltas spread over
16.69 s** (t=25.5 s → t=42.2 s), terminal (4561 chars = exact delta sum) at
t=49.1 s. Same binary as Run A. Conclusion: **the CLI streams incrementally
for long generations and flushes short replies as one burst.** SASE cannot
influence this pacing; there is no `muse exec` flag controlling delta
granularity (checked full `--help`: no streaming/verbosity option).

**Run C — SASE parser vs. real CLI** (`stream_and_parse_muse_json_output`
+ 400-word story, `SASE_ARTIFACTS_DIR` set, `live_reply.md` polled every
0.5 s): `live_reply.md` grew 10% → 100% across t=3.0 s → t=10.0 s of a
13.5 s run, one timestamp entry, final bytes identical to returned content.
**The parser forwards live; the coalescing fix streams fine.**

**Run D — full `MuseProvider.invoke`** (300-word story, `suppress_output=False`,
console bytes timestamped): console and `live_reply.md` reached 100% at
t≈39.5 s of a 54 s wall (remainder is post-terminal task wrap-up before
process exit — same pattern as Run A's 4.3 s gap). Forwarding is immediate;
this run's generation was simply bursty (cf. Run A).

**Session-log check:** the `--session-id` log
(`~/.local/share/muse/sessions/.../<id>/session.jsonl`) grows live during
the run (137 KB at t=1 s → 161 KB during generation) but carries only
per-model-call events (`model_response_created`, `model_completed` with
usage, `assistant_message_committed`, one `reasoning_summary_delta`) — **no
per-token text**. It is not a viable fallback live-text source.

**Tests:** `tests/llm_provider/test_muse_provider_stream.py` +
`tests/ace/tui/widgets/test_agent_reply_muse_chunks.py` — 18 passed.

## 4. Options considered

1. **Revert to per-delta chunks (`append_stream_text`).** Rejected: resurrects
   the ~25-divider rendering bug the fix cured, for zero liveness gain (both
   forward immediately).
2. **Buffer deltas and render whole replies (drop live forwarding).**
   Rejected: strictly worse; destroys the only live signal for long runs.
3. **Tail the session log for live text.** Rejected: no per-token text exists
   there (measured).
4. **Unbuffer/PTY-wrap the CLI hoping for finer deltas.** Rejected: Run B
   proves the pipe already delivers events in real time; batching happens
   inside the CLI/server, upstream of anything a PTY changes.
5. **Request/pin an older CLI that streamed short replies.** Rejected without
   evidence: R708.1 fixtures contain exactly 1 delta per (tiny) reply,
   consistent with today's batch-short-replies behavior — no proof an older
   CLI was finer-grained, and pinning old CLIs fights auto-update.
6. **(Recommended) Console-layer fix + docs.** The one place where current
   code is plausibly worse than pre-fix on a real terminal: partial-line
   `print(..., end="")` interleaved with the 2 Hz Rich `Live` timer redraw.
   Routing fragments through the Rich `Console` (which coordinates with
   `Live`) is a small, safe, Muse-confined change. Everything else already
   works.
7. **(Optional, if API streaming is the actual ask) Provider-neutral
   `on_delta` callback**, Muse first. Note this is new API surface on
   `LLMProvider`/`llm_invoke` shared by 8 providers — justified only if a
   consumer (TUI live feed, log tailer) needs deltas without polling files.

## 5. Suggested verification for the implementer

- Long-reply TTY test pre/post console change: `muse-spark-1.3`,
  `--reasoning-effort minimal`, 800-word story; observe fragment rendering
  under the "Waiting for Muse Code" timer (flicker/garbling check).
- Short-reply control: same prompt at 50 words; expect a single burst —
  assert this is accepted as CLI pacing, not a regression.
- Re-run `tests/llm_provider/test_muse_provider_stream.py` and
  `tests/ace/tui/widgets/test_agent_reply_muse_chunks.py` (18 tests, ~4 s).
- Probe scripts used here were throwaway (`/tmp/muse_stream_probe.py`,
  `/tmp/muse_sase_e2e.py`, `/tmp/muse_invoke_e2e.py`); the durable evidence
  is the four runs' numbers quoted in §3, reproducible with any timing
  wrapper around `muse exec --json`.
