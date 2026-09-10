# SASE Monitors: Token Efficiency Research (Researcher B)

**Date:** 2026-09-10
**Repo:** `sase-org/sase` @ `f5a3f5c99`
**Question:** How should sase monitors be improved, especially for token efficiency?

---

## 1. Executive Summary

Monitors are not expensive because they run commands. They are expensive because
**every monitor handoff permanently bakes its evidence into the family transcript,
and every later handoff replays that transcript verbatim while also re-deriving it.**
The result is geometric duplication.

Measured over the 4 days since the last monitor-fork fix landed
(`a45669b26`, 2026-09-06 14:33) on this machine:

| Metric | Value |
| --- | --- |
| Chats written since 2026-09-06 15:00 | 2,033 |
| Of those, monitor follow-ups | 340 (**17%** of chats) |
| Prompt bytes, monitor follow-ups | **40.1 MB** |
| Prompt bytes, all other 1,693 chats | 2.7 MB |
| Monitor follow-ups' share of all prompt bytes | **94%** |
| Median monitor follow-up prompt | 36 KB (~9K tokens) |
| Median *non-monitor* prompt | 1.07 KB (~270 tokens) |
| Mean monitor follow-up prompt | 115 KB (~29K tokens) |
| p90 monitor follow-up prompt | 335 KB (~84K tokens) |
| Follow-ups whose prompt alone exceeds a 200K-token window | **3%** (9 runs) |
| Follow-ups burning >=25% of a 200K window before acting | **14%** |

Of those 40.1 MB:

- **56%** is raw fenced command output.
- **34%** is *byte-identical duplicate* output blobs inside a single prompt.
- **90%** of the bytes live in prompts that carry 2-32 *stale, superseded* monitor
  breakdowns from earlier generations of the same chain.
- The agents' own responses across all 342 of those runs total 1.74 MB — a
  **23:1 prompt-to-output ratio**.

A worked example, `tmp_260907_011856` (1.28 MB prompt): it contains **32 monitor
breakdowns for only 6 distinct monitors**, at multiplicities 16x, 8x, 4x, 2x, 1x, 1x —
a clean geometric series. The oldest monitor in that chain is replayed **sixteen times**
in one prompt.

**Recommended fix (Section 6): stop persisting injected fork history inside the stored
`## Prompt`, and make command evidence a first-class transient region that replays as a
one-line pointer.** Simulated against the real corpus this takes the same 342 prompts
from **40.27 MB to 5.33 MB (-87%)**, median 35 KB -> 14 KB, worst case
1.28 MB -> 25 KB (-98%). That is roughly **8.7M tokens saved per 4 days** on one
machine, with no loss of information the follow-up cannot recover on demand.

A second, independent finding: the 200-line tail is a *bad selector*. Across 134
`FAILED just check*` monitors, the embedded tail contained the actual failing-test
detail only **25%** of the time; **46%** contained nothing but `error: recipe ... failed`.
The current design pays ~9.4 KB per follow-up for a signal that is usually absent.

---

## 2. Method

Everything below is measured, not estimated from reading code alone.

- **Corpus:** `~/.sase/chats/202609` — 2,371 durable chat transcripts. Each transcript
  stores the *fully expanded* prompt the provider actually received under `## Prompt`,
  so byte counts there are a faithful proxy for input tokens.
- **Cutoff:** measurements are restricted to files modified after 2026-09-06 15:00,
  i.e. after `a45669b26 fix(agent): preserve monitor fork context` landed, so the
  numbers describe *current* behaviour, not an already-fixed regression. (Before that
  commit, single follow-up prompts reached **1.89 MB of injected history** — 472K
  tokens — because a monitor member's chat was forked as a plain agent conversation
  and its 2 MiB retained log came along whole.)
- **Token estimates** use bytes/4. Command logs are path- and punctuation-heavy, so
  this is mildly conservative; the ratios are unaffected.
- Reconstruction commands are in Appendix A.

---

## 3. Where The Tokens Go

### 3.1 The composition of a monitor follow-up prompt

A follow-up prompt is assembled by `compose_followup_prompt`
(`src/sase/monitor/followup_prompt.py:96`):

```
#fork:<family>            <- live routing directive, expands to the whole family
%model:/%effort:          <- routing
<disabled region>
  # Monitored command finished
  **Command:** / **Directory:**  (fenced)
  | Outcome | Started | Finished | Elapsed | Output |
  **Why this was monitored:** <reason>
  ## Last 200 lines of output   <- fenced, untrusted, <=12,000 chars
  ## Your next action           <- the --next text
</disabled region>
```

Only the last section is instruction. Everything above it is context and evidence.

Measured shares of the 40.27 MB (n=342):

| Region | Bytes | Share |
| --- | --- | --- |
| Fenced command output (all blobs >2 KB) | 22.57 MB | 56% |
| ...of which exact duplicates within the same prompt | 13.88 MB | 34% |
| Everything else (prose, tables, forked conversation) | 17.70 MB | 44% |
| Agent responses produced from all of it | 1.74 MB | (4% of file bytes) |

### 3.2 The geometric blow-up

Counting `# Monitored command finished` occurrences per follow-up prompt:

| Stale breakdowns in prompt | Prompts | Bytes | Mean prompt |
| --- | --- | --- | --- |
| 1 (its own only) | 170 | 4.07 MB | 23 KB |
| 2 | 71 | 4.18 MB | 57 KB |
| 4 | 49 | 6.45 MB | 128 KB |
| 8 | 26 | 7.53 MB | 282 KB |
| 16 | 19 | 10.38 MB | 533 KB |
| 23 | 3 | 3.43 MB | 1,115 KB |
| 32 | 4 | 4.24 MB | 1,034 KB |

The powers of two are the tell. **50% of prompts carry only their own breakdown and
account for 10% of the bytes; the other 50% carry stale generations and account for
90%.** Each hop down a monitor chain roughly doubles the replayed evidence.

### 3.3 Root causes, in code

**(a) The stored `## Prompt` contains the injected fork history.**
`run_agent_exec_finalize.py:177` and `run_agent_exec_monitor.py:63` call
`save_chat_history(prompt=state.current_prompt, ...)` — `current_prompt` is the
*expanded* prompt, including the entire `# Previous Conversation` block that `#fork`
just injected. `write_chat_history` has a dedicated `previous_history` parameter
(`chat_storage.py:211`) that writes a separate `## Previous Conversation` section —
**the agent path never uses it.**

**(b) Replay re-emits that baked-in history *and* re-derives it.**
`parse_chat_turns` (`chat_resume.py:167`) reads only `## Prompt`/`## Response` pairs, so
the baked-in history is returned as part of the prompt text. `load_chat_for_resume`
then *also* follows any `#fork` refs it finds and expands the same ancestors again
(`chat_resume.py:210-256`). One hop, two copies.

**(c) `visited` is copied, not shared, at the top level.**
`share_visited = _visited is not None` (`chat_resume.py:218`), and
`nested_visited = visited if share_visited else set(visited)`
(`chat_resume.py:247`). The single-agent entry point in `build_fork_injected_history`
calls `load_resume_history(path)` with no `visited`, so sibling branches each get a
private set and the same ancestor can be expanded more than once in one fork build.

**(d) There is no bound of any kind on `load_chat_for_resume`.**
Every other output path in the system is bounded — `OUTPUT_TAIL_MAX_CHARS = 12_000`
(`shells/prompt.py:8`), `_LOG_TAIL_LINES = 400` / `_LOG_TAIL_MAX_CHARS = 12000`
(`scripts/_fork_proc_sources.py:18-19`), `SHELL_MAX_OUTPUT_BYTES = 2 MiB`
(`shells/output.py:6`). Forked conversation history is the one unbounded channel, and
it is the channel every monitor handoff uses.

**(e) `--next-output` cannot actually opt out of the cost.**
`--next-output none` suppresses the `## Last N lines` section only. The `#fork` path
renders the monitor member's `log_tail` unconditionally
(`_fork_proc_sources.py:125`, `chat_fork/proc.py:132`), so the log arrives anyway.
Today the flag saves ~9 KB out of a 36 KB median prompt and nothing at all from the
stale generations.

### 3.4 Secondary sinks

- **Monitor shell chats.** A `__mon` member's chat "Response" is its 2 MiB retained
  output. Since 2026-09-06 15:00 these total **29.3 MB** of on-disk chat text. They are
  bounded in the fork path today, but they are the blast radius for any direct
  `#fork:<monitor-id>` and for every future reader.
- **The `/sase_monitor` skill body.** 1,271 words (~1.7K tokens), the second-largest
  bundled skill after `sase_gate`. At ~340 monitor starts per 4 days that is ~580K
  tokens. It also still teaches deprecated `--command '...'` as the *Canonical
  Invocation* while `docs/monitors.md` says the `-- <cmd>` form is canonical and
  `-c/--command` is a hidden compatibility alias — so agents are being taught the
  deprecated form at full token price.
- **No provider session reuse.** `claude.py:332-343` mints a fresh
  `--session-id <uuid4>` per turn and discards it. Every follow-up is a cold session:
  the system prompt, tool definitions, CLAUDE.md core memory, and the entire
  reconstructed history are re-sent at full price, and the follow-up gets only the
  starter's *final reply text* — never its tool results — so it frequently re-reads the
  same files the starter already read.

---

## 4. The Signal-Quality Problem

Token efficiency and usefulness point the same direction here, which is unusual and
worth exploiting.

Across 134 monitors that ran `just check*` and ended `FAILED`, with a mean embedded
tail of 9,385 bytes:

| The embedded tail contains... | Count | Share |
| --- | --- | --- |
| Some failure marker (`✗` or `error: recipe`) | 131 | 97% |
| Actual failing-test detail (`FAILED ` / `short test summary`) | 34 | **25%** |
| Only `error: recipe ... failed`, no failing-test detail | 62 | **46%** |

"Last 200 lines" is a positional heuristic applied to output whose structure it ignores.
`just check-full` (`Justfile:657`) is a sequence of named gates run through
`tools/run_silent`, which **discards a gate's output on success**. So the log is already
structured: `✓ <gate>` lines, then one failing gate's full output, then
`error: recipe ... failed`. Whatever failed early — a mypy error, a symvision finding —
is pushed out of the tail window by whatever printed last, typically the flake-baseline
dump. In the worked example above the last 200 lines were ~28 KB of flake-baseline
listing plus two `error: recipe` lines; the actionable content was two lines.

Nearly half the time the follow-up must now spend a tool call on
`sase monitor show <id> --all-lines` (or re-run the command) to learn anything. **We are
paying 9.4 KB per follow-up for a pointer.**

---

## 5. Options Considered

### A. Transient evidence + unbaked history *(recommended core)*

Two coupled changes:

1. **Persist the prompt split.** At `save_chat_history` time, split
   `state.current_prompt` at the injected-history boundary and pass the history through
   the existing `previous_history=` parameter instead of concatenating it into
   `prompt=`. The chat file renders identically for humans, ACE, and audit; but
   `parse_chat_turns` — and therefore every future fork — replays only the New Query.
   This alone kills the doubling.
2. **Mark command evidence as a transient region.** Wrap the monitor breakdown's
   evidence sections in a durable delimiter (e.g.
   `<!-- sase:evidence kind=monitor id=<monitor_id> -->` ... `<!-- /sase:evidence -->`)
   and teach `sanitize_resume_prompt` (`chat_resume.py:32`, which already strips
   directives and xprompt refs from replayed prompts) to collapse the region to one
   line on replay:
   `[monitor tk8xq2 — FAILED exit 1 after 41m of 45m; sase monitor show tk8xq2 --all-lines]`

   Generalizes for free to gate shells and proc shells, which are the same class of
   evidence.

Simulated on the real corpus (Appendix A.4): **40.27 MB -> 5.33 MB (-87%)**,
median 35 KB -> 14 KB, p90 prompt collapses, worst case -98%.

- **Cost:** the fully expanded prompt is no longer recoverable as one blob from the
  chat file; it is recoverable as (previous_history + prompt). A migration/compat read
  path is needed for existing transcripts.
- **Risk:** low. Both hooks already exist; no new subsystem.

### B. Structured digests instead of a positional tail

Replace `--next-output tail` with `--next-digest`:

- Ship named digests: `just` (extract the `✓`/`✗` gate ladder + the failing gate's
  block + `error: recipe` lines), `pytest` (the `=== short test summary info ===`
  section + `--durations` outliers), `raw-tail` (today's behaviour), `none`.
- `--next-digest 'cmd'` as an escape hatch: the log is piped through the command and
  its bounded stdout becomes the evidence.
- Make the default **outcome-conditional**: `none` on success (93 of 342 monitors
  completed cleanly — their tail is pure waste), digest on failure/timeout.

Expected: ~9.4 KB -> ~1.5 KB per failing follow-up, *and* the failing-test detail
present 100% of the time instead of 25%.

- **Cost:** a small, maintained library of log grammars. Digest bugs could hide real
  failures — mitigate by always emitting the `sase monitor show --all-lines` pointer
  and by including the digest's own "N lines matched" count.

### C. Outcome-branched follow-ups

`--next-on-success` / `--next-on-failure` (with `--next` as the shared default), each
with its own `--model`. The success branch of a `TESTING`/`TESTED` gate is usually
"reply to the user" or "land the epic" — cheap, deterministic work that does not need
the failure branch's model or evidence. Today one `--next` string must serve both, so
it is written for the expensive case.

Small token win on its own; large when composed with B, because it makes
`--model @small --next-digest none` safe on the success path.

### D. Provider session resume

Persist the `--session-id` UUID that `claude.py:332` already mints, and launch the
follow-up with `claude -p --resume <id> --fork-session` instead of re-sending a
reconstructed transcript.

- **Upside:** the fork block disappears entirely; the follow-up inherits the starter's
  *tool results*, not just its final reply, so it stops re-reading the same files; on a
  warm prompt cache the input is ~10% of the cold price.
- **Downside, and it is real:** a resumed session re-sends *more* material than the
  fork does (all tool calls, not just replies), so on a **cold** cache it can be a net
  loss. `just check-full` monitors routinely run 20-45 minutes, which is inside the
  1-hour extended cache TTL but well outside the 5-minute default. It is also
  provider-specific (Codex has no equivalent session persistence — see
  `codex.py:468`), breaks `--model` re-routing across the handoff, and cannot survive a
  workspace or machine change.
- **Verdict:** a genuine quality and latency win, an *uncertain* token win. Worth a
  flag-gated experiment on Claude-only, same-machine handoffs **after** A lands — but
  it is not the answer to the measured problem, and A makes it much cheaper to evaluate
  because the baseline stops being dominated by duplication.

### E. Bound the monitor member's chat projection

Write the digest + pointer as the `__mon` chat "Response" rather than 2 MiB of raw log
(which stays on disk in `live_reply.md`, reachable via
`sase monitor show --all-lines`). Saves ~29 MB of chat text per 4 days and shrinks the
blast radius of a direct monitor fork.

- **Cost:** `sase chat` on a monitor member no longer shows the full log inline.
  Acceptable — the docs already frame a monitor as an execution record with a pointer.

### F. Trim the `/sase_monitor` skill

Cut ~1,271 words to ~550: drop the three long worked examples down to one, move the
`--next-output`/follow-up-context prose to `docs/monitors.md` (where it already lives
nearly verbatim), and **fix the Canonical Invocation to use `-- <cmd>`** instead of the
deprecated `--command`. ~1K tokens saved per monitor start, plus agents stop being
taught a deprecated flag.

### G. Rejected: summarize the transcript with an LLM

Compressing the forked history via a cheap model call was considered and rejected. It
adds a provider round-trip and a new failure mode to every handoff, and it solves the
*symptom*. 90% of the bytes are literal duplicates of text already in the prompt;
deleting duplicates is free, exact, and auditable. Revisit only if post-fix prompts are
still too large.

### H. Rejected: blocking waits / long-lived agents

Out of bounds by `decisions:single-turn-agents` and `decisions:gates-never-block`.
The handoff mechanism is not the problem; what it carries is.

---

## 6. Recommendation

Ship in three phases. Phase 1 is where essentially all the token savings are.

### Phase 1 — Stop replaying evidence *(the fix)*

1. Split the persisted prompt: pass injected fork history through
   `write_chat_history(previous_history=...)` rather than baking it into `prompt=`.
   Update `parse_chat_turns` consumers and add a compat path for existing transcripts.
2. Introduce a transient-evidence region delimiter, emit it from
   `compose_followup_prompt` around the command/table/tail sections, and collapse it to
   a one-line pointer in `sanitize_resume_prompt`. Apply the same wrapper to gate-shell
   and proc-shell follow-up prompts.
3. Fix `share_visited` at the top-level fork entry point so one fork build cannot
   expand the same ancestor twice.
4. Add a hard bound to `load_chat_for_resume` as a backstop — a per-source and total
   character budget with a visible truncation notice. Every other output channel in the
   system has one; this one should not be the exception.
5. Add a regression test that asserts a 4-deep monitor chain's final prompt contains
   exactly one `# Monitored command finished` and one copy of each ancestor turn.

**Expected: -87% on monitor follow-up prompt bytes (40.27 MB -> 5.33 MB measured on the
real corpus); ~8.7M tokens per 4 days on this machine. No information is lost that
`sase monitor show <id> --all-lines` cannot return on demand.**

### Phase 2 — Make the remaining evidence worth its tokens

6. `--next-digest {auto,just,pytest,raw-tail,none,<cmd>}`, defaulting to `auto`:
   outcome-conditional (`none` on success, best-matching digest on failure/timeout),
   always with the `--all-lines` pointer appended. Keep `--next-output` as a
   deprecated alias.
7. `--next-on-success` / `--next-on-failure`, each accepting its own `--model`.
8. Write the digest, not the 2 MiB raw log, as the `__mon` member's chat response.

**Expected: the ~1.5 MB/4-day residual tail cost drops ~85%, and failing-test detail
reaches the follow-up 100% of the time instead of 25%.**

### Phase 3 — Trim the instruction surface, then evaluate resume

9. Rewrite `src/sase/xprompts/skills/sase_monitor.md` to ~550 words with `--` as the
   canonical form; regenerate deployed skills per `sase/memory/generated_skills.md`.
10. Behind a feature flag (per `sase/memory/sase_flags.md`), persist the provider
    session id and try `--resume --fork-session` for Claude-only, same-machine,
    same-model handoffs. **Measure before adopting** — instrument actual input tokens
    with and without, since a cold cache can make resume a net loss.

### What I would not do

- Do not lower `DEFAULT_TAIL_LINES` or `OUTPUT_TAIL_MAX_CHARS` as the primary fix. The
  live tail is ~1.5 MB of the 40.27 MB. Halving it saves 2% and makes the 25%
  signal-hit-rate worse.
- Do not make monitors rarer to save tokens. `decisions:two-speed-verification` fixes
  the `just check-full`-through-a-monitor rule on *host capacity* grounds; the monitor
  count is not the lever.

---

## 7. Risks And Open Questions

- **Transcript compatibility.** Changing what lands in `## Prompt` changes what every
  existing reader (`sase chat`, ACE prompt panel, `#fork`, chat catalog/search) sees.
  Phase 1 needs a read path that handles both shapes. The `## Previous Conversation`
  heading is already recognised by `extract_previous_conversation_turns`
  (`chat_resume.py:145`), which helps.
- **Does the follow-up genuinely need ancestor turns at all?** Half of monitor
  follow-ups already carry only their own breakdown and still work. It may be that the
  right long-term shape is "fork the immediate predecessor's *conclusions*, point at
  everything else." Out of scope here, but the Phase 1 instrumentation would answer it.
- **Digest correctness.** A digest that silently misses a novel failure shape is worse
  than a dumb tail. Always emit match counts and the full-log pointer; keep `raw-tail`
  available.
- **Session-resume evaluation needs real token telemetry.** The chat corpus measures
  prompt bytes, not billed input tokens including cache reads. Before Phase 3.10,
  instrument `total_usage` (already threaded through `claude.py`) per follow-up.
- **Cross-machine generality.** All numbers here come from one machine's
  `~/.sase/chats`. The mechanism is machine-independent, but the *magnitude* depends on
  how deep monitor chains typically get in a given workload.

---

## Appendix A — Reconstruction Commands

Run from `~/.sase/chats/202609`.

**A.1 — Monitor follow-ups' share of prompt bytes:** for each `*.md`, split at the
first `^## Response$`; classify by presence of `# Monitored command finished`; sum the
prefix lengths for each class.

**A.2 — Geometric blow-up:** count `^# Monitored command finished$` occurrences in the
prompt prefix; bucket prompts by that count; sum bytes per bucket.

**A.3 — Duplication proof:** in one prompt, collect
`sase monitor show (\S+) --all-lines` pointers and count multiplicities. For
`tmp_260907_011856`: 32 pointers, 6 distinct, multiplicities {16, 8, 4, 2, 1, 1}.

**A.4 — Savings simulation:** for each prompt, keep everything before the *first*
breakdown with fenced blobs >2 KB elided, add 300 bytes per superseded generation, and
keep the final breakdown with its tail replaced by a 1.5 KB digest. Result:
40.27 MB -> 5.33 MB.

**A.5 — Tail signal quality:** for `FAILED` monitors whose command starts with
`just check`, extract the `## Last N lines of output` section and test it for
`^FAILED ` / `short test summary` versus `error: recipe`.

## Appendix B — Key Code Locations

| Concern | Location |
| --- | --- |
| Follow-up prompt composition | `src/sase/monitor/followup_prompt.py:96` |
| Live tail bound (12,000 chars) | `src/sase/shells/prompt.py:8` |
| Default tail lines (200) | `src/sase/monitor/request.py:24` |
| Fork tail bound (400 lines / 12,000 chars) | `src/sase/scripts/_fork_proc_sources.py:18` |
| Retained output bound (2 MiB) | `src/sase/shells/output.py:6` |
| Unbounded history replay | `src/sase/history/chat_resume.py:210` |
| `visited` copy-vs-share | `src/sase/history/chat_resume.py:218,247` |
| Replayed-prompt sanitizer (fix hook #2) | `src/sase/history/chat_resume.py:32` |
| Turn parser (reads only `## Prompt`/`## Response`) | `src/sase/history/chat_resume.py:167` |
| Unused `previous_history=` param (fix hook #1) | `src/sase/history/chat_storage.py:211,240` |
| Expanded prompt persisted (agent path) | `src/sase/axe/run_agent_exec_finalize.py:177` |
| Expanded prompt persisted (monitor path) | `src/sase/axe/run_agent_exec_monitor.py:63` |
| Monitor log rendered into family forks | `src/sase/history/chat_fork/proc.py:132` |
| Fresh, discarded provider session id | `src/sase/llm_provider/claude.py:332-343` |
| Monitor skill source | `src/sase/xprompts/skills/sase_monitor.md` |
| `just check-full` gate ladder | `Justfile:657` |
