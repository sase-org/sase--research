# Headless single-turn early exits: audit, root causes, recommended fix (__mus)

Researcher: mus (independent swarm report; conclusions my own).
Date: 2026-09-21. Scope: sase repo checkout + `~/.sase` run telemetry (chats,
tool-call records, monitor history) from Sept 2026.

## Bottom line

The user's hypothesis is **confirmed with one refinement**: agents do run long
commands, background them with **provider-native** async/monitor primitives, end
their response waiting for a notification that can never arrive — and the turn is
then captured as finished while the work is still in flight. But "agents don't
understand headless mode" is not the whole story. The project already documents
this exact failure class (`decisions:single-turn-agents`: "every hosted agent
runtime ships background-execution and scheduling primitives, and every one of
them silently no-ops here"), and two providers are already guarded against it.
The true root cause is that **the single-turn contract is enforced unevenly per
provider instead of once, centrally**: Claude and Agy/Gemini have directives,
tool disabling, and wait-state detection with bounded recovery; **Grok, Muse,
Codex (and Opencode/Qwen) have none of that** — a wait-ending reply is accepted
as success and the backgrounded work is silently lost. Telemetry matches:
background-poll tool usage since 2026-09-18 is grok 573, muse 77, claude 4.

## What I checked

1. **Monitor history** (`sase monitor list --all --format json`): 1311 monitors;
   states completed 534 / failed 705 / timeout 57 / stopped 12 / lost 3. Only 17
   follow-up errors and 19 degraded follow-ups. The `sase monitor` handoff
   machinery itself is healthy — most "failed" monitors are just commands that
   exited nonzero (their follow-ups still launched). The problem is agents that
   never reach `sase monitor` at all.
2. **Tool-call telemetry**: 526 recent `tool_calls.jsonl` files, 28,382 ToolUse
   events since 09-18. Native background-poll tools (`get_command_or_subagent_output`,
   plus `bash_input`, `kill_command_or_subagent`, `Agent`) total 654 uses, split
   grok 573 / muse 77 / claude 4. Correct-path usage exists too: ~20+
   `sase monitor start --profile verify` invocations and repeated reads of the
   `sase_monitor` skill. So both patterns coexist; the wrong one dominates on
   unguarded providers.
3. **Chat transcripts** (`~/.sase/chats/202609/`, 7157 files): a full-month scan
   for responses ending in wait language ("I'll wait for the notification",
   "will notify me", "stop checking in manually and simply wait") surfaced
   ~15 cases, all pre-fix era (09-07–09-13), e.g.:
   - `ace_run-sase_xz_3-260907_105255`: "I've scheduled a wakeup to check on the
     `just check` run. Ending this turn now — I'll resume automatically…",
     followed by "My mistake — I don't need `ScheduleWakeup` here since the
     backgrounded `just check` will automatically notify me." Textbook
     rationalization of the guard away, exactly as the decision record predicts.
   - `ace_run-0ao__code-260908_162843`: three consecutive "wait for the `just
     check` background task" messages.
   - `ace_run-sase_zf_2-260910_180254`: "Waiting for the background `just check`
     watcher to notify me — no further action needed… I'm going to stop checking
     in manually now and simply wait."
   - Same shape in `0ii`, `0j0`, `sase_z4_6_5_4_1`, `sase_zl_13_11_*`,
     `toobig_4v_federation_0`, `sase_y5_5`, `sase_10w_1`.
4. **Provider glue** (`src/sase/llm_provider/`): full guard matrix (below).
5. **Reference memory** (via audited `sase memory read`): `single-turn-agents`,
   `gates-never-block`, `xprompts.md`, `lint_and_test.md`.

## Provider guard matrix (the core finding)

| Guard | claude | agy (gemini) | grok | muse | codex | opencode/qwen |
|---|---|---|---|---|---|---|
| Single-turn directive in system prompt | yes (`_SINGLE_TURN_DIRECTIVE`, `--append-system-prompt`) | yes (`_AGY_PRINT_MODE_DIRECTIVE`) | **no** | **no** | **no** | **no** |
| Native background/wakeup tool disabled | yes (`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, `--disallowedTools ScheduleWakeup`) | n/a (print mode) | **no** | **no** | **no** | **no** |
| Wait-state response classifier | yes (`_classify_claude_wait_state`, bdda3bdf1, `test_claude_wait_guard.py`) | yes (no-progress regexes, `test_agy_no_progress.py`) | **no** | **no** | **no** | **no** |
| Bounded recovery, then loud failure | yes (2 continuations → `LLMInvocationError`, run fails visibly) | yes (2 continuations → nudge) | **no** (first reply = success) | **no** (first reply = success) | **no** | **no** |
| Long-command escape hatch | 4h `BASH_MAX_TIMEOUT_MS` + "rerun with larger timeout" | 24h `--print-timeout` | none | none | none | none |

Muse (`muse.py`) and Grok (`grok.py`) `_invoke_loop`s return the first response
unconditionally. A reply of "I'll wait for the notification" is recorded as a
successful turn. There is no equivalent of Claude's refusal ("refusing to report
it as success… `claude -p` cannot deliver").

## True root causes, ranked

1. **Per-provider enforcement of a platform-wide contract.** Single-turn-ness is
   a property of SASE's runner, but it is implemented (twice) in provider glue.
   Any provider without the trio — directive + tool disabling + response
   classifier — silently converts early exits into false successes. This is the
   dominant cause and explains the grok-heavy telemetry.
2. **Native tools work just well enough to teach the wrong pattern.** Polling a
   background task returns output while the turn is alive, so the agent learns
   "background + wait works" — the failure only materializes when the response
   ends first. A rule that is disconfirmed by the agent's own experience needs
   mechanical enforcement, not just documentation (the decision record says
   this outright).
3. **The correct path is opt-in knowledge.** `sase monitor` usage requires the
   agent to load a skill (`sase_monitor.md`) or reference note
   (`lint_and_test.md`) at the right moment. Nothing inlined in every turn tells
   the agent "if this command may outlive your turn, stop and hand it off."
   The inlined core memory carries only the one-line decision descriptor.
4. **Silent failure.** On unguarded providers nothing fails loudly: no error, no
   amber flag (contrast `sase monitor list`'s `⚑` for dropped follow-ups). Lost
   work looks like completed work until a human notices the bead didn't move.

## Recommended solution

**Generalize the Claude/Agy pattern to every provider, once, in shared code —
fail loudly instead of succeeding silently.** Concretely:

1. **Shared single-turn preamble** (highest leverage): move one canonical
   directive ("one provider turn; no follow-up events; background tasks and
   scheduled wake-ups can never reach you; run synchronously; never end your
   turn waiting; for long verification use `sase monitor start`") into the
   shared prompt path so new providers inherit it instead of each provider
   re-deriving it. Keep provider-specific tool-disabling flags alongside.
2. **Port the response classifier**: apply a Claude-style wait-language +
   outstanding-background-task check to grok/muse/codex/opencode/qwen
   responses, with the same bounded-continuation budget (2) and the same
   terminal `LLMInvocationError` on exhaustion. A run that would otherwise die
   quietly must fail visibly so it gets retried instead of mistaken for done.
3. **Disable what can be disabled**: set each CLI's no-background / no-wakeup /
   no-approval flags where they exist (as done for Claude and Grok's
   `--no-ask-user`); where a CLI has no such flag, the classifier in (2) is the
   backstop.
4. **Make the right path unavoidable at the decision point**: add one inlined
   (core, not reference) line to the effect of "commands that may outlive this
   turn go through `sase monitor start` with `--next`; provider-native
   background/wakeup tools never deliver." Reference memory is read on demand;
   this choice happens before any demand exists.
5. **Do not** build a fourth continuation mechanism, a long-lived daemon agent,
   or per-provider polling loops — the decisions record already rejects these,
   and the monitor-history data (only 17 dropped follow-ups in 1311) says the
   existing handoff is reliable enough to standardize on.

Suggested staging: (1)+(4) are prompt-only and cheap — do first; (2) per
provider starting with grok (highest misuse count), reusing
`test_claude_wait_guard.py` as the template; (3) opportunistically per CLI
capability.

## Limits / what I did not verify

- I did not trace any single recent run end-to-end from "wait reply" to "bead
  left open"; the ~15 transcript cases are pre-guard-era (09-07–09-13) and most
  eventually completed within the same turn by polling. The current-epoch proof
  is structural (missing guards + grok-skewed background-tool telemetry), not a
  fresh corpse.
- I did not consult the peer researchers' reports (`__cld.md`/`__gem.md`) per
  the swarm rule; overlap with their findings is coincidental.
- A long background `grep` for guard-firing errors was still running when this
  report was written; it is corroborating detail, not load-bearing.
