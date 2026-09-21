# Why SASE Agents "Die" After Long Commands — Audit of Sep 14–21, 2026 Runs

Researcher: `research.25.cld` (Claude). Date: 2026-09-21. Scope: every local SASE agent
run from 2026-09-14 through 2026-09-21 on athena, plus the monitor corpus and the ToolRun
ledger.

## Bottom line

The hypothesis is **partly right, but it is no longer the main cause.**

1. **"Agents don't know they are headless"** was real, but only for Claude before Sep 15.
   On Sep 14, 10 of 67 Claude runs (15%) used Claude Code's native background tools
   (`run_in_background`, `ScheduleWakeup`, `Monitor`, `TaskOutput`, `TaskStop`). They
   then ended their turn saying things like _"The Bash background task itself will notify
   me automatically"_. Commit `bdda3bdf1` (Sep 15, _fix(claude): guard background wait
   replies_) fixed this. Since then, **0 of 269 Claude runs** used a native
   background or scheduling tool. The same pattern still exists in small residual forms
   for other providers (see §3).
2. **Most of the "running a long command, then some monitor, then dying" you see is
   SASE's own `sase monitor start` handoff.** It kills the agent by design. In the
   window it ended **190 agent runs** (16% of all non-monitor, non-gate runs), and
   **49% of all Grok runs**. The mechanism works as specified. What goes wrong is
   **how and when** agents reach it:
   - **(a) Commands outlive every provider's tool-call window.** `just check` has a p90
     of 34–45 min and a max of 67–135 min. `check-full` has a median of 45 min and a max
     of 4.6 h. The windows are: Grok auto-backgrounds after about 15 s, Muse yields at
     300 s, and Codex polls.
   - **(b) The guidance tells agents to run verification inline and "hand it to a
     monitor … whenever it is taking a long time."** That is a duration prediction the
     agent cannot make. So agents start inline, notice it is slow, then kill the
     in-flight run and re-run it from zero under a monitor. `sase monitor start` can
     only launch a new command. It cannot adopt one that is already running.
   - **(c) Failed verification becomes a loop.** The pattern is fail → follow-up →
     small fix → full re-verify under a new monitor. 23 families ran ≥3 monitors (119
     monitors total). The worst ran 13–15 hops over 8–15 hours.
3. **Headless safeguards are uneven.** Only Claude and Antigravity (`agy`) get a
   single-turn directive and a wait-state guard. Codex, Grok, Muse, Qwen and OpenCode
   get nothing from SASE except skill text. The Claude directive also contradicts the
   monitor skill. The agy guard let a phase agent finish as `completed` while its reply
   was "waiting for `sase doctor`".

**Recommendation (details in §9).** Don't mainly fix this with more "you are headless"
prompting. Make long-running work **mechanically lossless**:

- **Joinable, detached ToolRuns.** A verification run survives its agent. A second
  identical request joins the in-flight run instead of restarting it.
- **A monitor can adopt an in-flight run.** Plus a single `--handoff-after` switch, so
  the tool decides mechanically whether to wait or hand off. The agent never guesses.
- **Provider-neutral single-turn contract and wait-state guard**, with consistent
  wording and native background tools disabled where possible.
- **A governor on verify→fix→re-verify monitor chains.**

Cutting verification duration itself (a shared `sase_core_rs` wheel cache, admission
control) is the long-run lever that makes all of this rarer.

---

## 1. Method and data

| Source | What it gave | Size |
| --- | --- | --- |
| `~/.sase/projects/*/artifacts/ace-run/202609/{14..21}/*` | `agent_meta.json`, `done.json`, `tool_calls.jsonl`, `live_reply.md`, `error_report.md`, finalizer and plan markers | 1,714 artifact dirs. 1,193 are agent runs (excluding 270 monitor rows and 251 gate rows) |
| `sase monitor list --all --format json` | Command, state, elapsed time, timeout, follow-up outcome for every monitor | 1,311 total, 270 in window |
| `~/.sase/tools/runs.sqlite` (ToolRun ledger) | `sase tool run check` durations and stage timings | 139 runs (ledger starts Sep 20) |
| Provider source in `src/sase/llm_provider/` | What each provider is told and guarded against | claude, agy, codex, grok, muse |
| Git history | When guards and policy changed | `bdda3bdf1` (Sep 15), `28d1e8708` (Sep 19) |

**How run endings were classified.** Each run's ending came from its own artifacts.

- `final_submission.json` means the agent declared final.
- `plan_path.json` or a trailing `sase plan propose` means a plan handoff.
- A trailing `sase monitor start` means a monitor handoff.
- A trailing `sase sudo request` or `sase gate` means a gate handoff.
- `.sase_user_kill_pending` means a user kill.
- Everything else is "no final".

Every "no final" run was then read by hand. Tool-call pairs were joined on `tool_use_id`
because Claude `ToolResult` rows do not carry tool names.

**Caveats.**

- Muse runs killed mid-`sase monitor start` record an empty command, so ~6 Muse monitor
  handoffs are counted as "no final" in the table below.
- The ToolRun ledger only covers Sep 20–21.
- Only athena-local artifacts were examined; no remote machines.
- `tool_calls.jsonl` timestamps are UTC. Artifact dir names are local (EDT).

## 2. How runs actually ended

| Provider | Final declared | Plan handoff | **Monitor handoff** | Gate/sudo handoff | User kill | Never started | No final | Runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| claude | 121 | 78 | **21** | 6 | 71 | 19 | 20 | 336 |
| codex | 246 | 103 | **79** | 2 | 59 | 7 | 14 | 510 |
| grok | 48 | 9 | **82** | 1 | 19 | 4 | 4 | 167 |
| muse | 97 | 0 | **8 (+~6)** | 0 | 0 | 33 | 14 | 152 |
| agy | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 5 |
| **all** | 513 | 190 | **190** | 9 | 168 | 67 | 56 | 1,193 |

On "No final":

- Almost all are benign: read-only Q&A agents that correctly had nothing to declare,
  runs still in progress, or sudo tests that ended at their gate.
- Only a handful are genuine "ended while waiting" exits. They are listed in §3.3 and
  §3.4.
- So the visible "dying" is overwhelmingly the **monitor-handoff column**, not silent
  crashes.

Monitors in the window: 270.

| Monitor command | Count |
| --- | ---: |
| `just check` / `sase tool run check` | 96 |
| `just check-full` | 78 |
| Epic launch (`sase bead work`) | 68 |
| Other | 28 |

Monitor outcomes: 126 failed, 125 completed, 18 timed out, 1 stopped. Of the 200
follow-up agents launched, **125 followed a failed command and 18 a timeout.**

## 3. Finding 1 — the "headless" hypothesis: true for pre-fix Claude, residual elsewhere

### 3.1 Claude before Sep 15: yes, exactly the suspected failure

On Sep 14, 10 of 67 Claude runs used native background or scheduling tools:
`ScheduleWakeup` ×7, `TaskOutput` ×5, `TaskStop` ×3, `Monitor` ×1, and 18
`run_in_background: true` Bash calls across 4 runs. Examples:

- `sase-10w.1` (sonnet, `202609/14/20260914090758`)
  - Tried `Monitor`, then `ScheduleWakeup`.
  - Ended with _"…test run for `tests/monitor/` is still in progress. I'll pause tool
    calls here and pick back up once it completes."_
  - A later recovery turn committed with the bead left `in_progress` _"since
    verification was still running in the background when the prior turn ended."_
- `sase-zw.8.1` (sonnet, `…/20260914070315`)
  - Ran `just check` and `just rust-dev-install` with `run_in_background: true`, then
    ended the turn.
- `sase-10w.3` (sonnet, `…/20260914090801`)
  - _"The Bash background task itself will notify me automatically when
    `just test-visual` finishes, so I'll wait for that rather than force a wakeup."_

Commit `bdda3bdf1` (2026-09-15 14:59 EDT) added four guards in
`src/sase/llm_provider/claude.py`:

- The `_SINGLE_TURN_DIRECTIVE` system-prompt append.
- `--disallowedTools ScheduleWakeup`.
- `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` and `BASH_MAX_TIMEOUT_MS=14400000`.
- A stream parser that detects outstanding background tasks and "I'll wait" replies,
  then nudges up to 2 times before failing loudly.

**Result:** zero native background or scheduling tool uses in 269 Claude runs from Sep
15–21, and no wait-guard failure reports. The main hypothesis is already fixed for
Claude.

### 3.2 Residual Claude gaps

- **Native tools are still offered.** Only `ScheduleWakeup` is disallowed. This audit
  session itself (a `claude -p` SASE agent) was offered deferred `Monitor`,
  `CronCreate`/`CronDelete`/`CronList`, `RemoteTrigger`, `PushNotification` and
  `SendMessage`.
  - The loaded `Monitor` schema says _"you keep working and notifications arrive in the
    chat"_. That is impossible in single-turn print mode.
  - They are unused today, but they remain a trap for future models and prompts.
- **The directive contradicts the monitor skill.** The directive says _"Run commands
  synchronously in the foreground … anything still running when you give your final
  response is lost … Never end your turn to wait."_ The skill says to use
  `sase monitor start`, which deliberately ends the turn.
  - Claude reads the directive as "monitors don't work". `0nz` (Sep 20): _"I ran the
    long jobs inline instead of through `/sase_monitor`, because this session is
    single-turn and a monitor's follow-up could never reach me."_ That belief is false.
  - It is harmless for Claude, which can block for up to 4 h. It still shows the two
    instruction sources disagree.

### 3.3 Other providers get no SASE-side headless contract

| Provider | Single-turn directive | Wait/no-progress guard | Native background mechanism observed |
| --- | --- | --- | --- |
| claude | yes | yes (background task IDs + wait phrases) | disabled via env; `Monitor`/Cron still exposed |
| agy | yes (`_AGY_PRINT_MODE_DIRECTIVE`) | yes (no-progress classifier) | n/a |
| codex | **no** | **no** | unified-exec sessions, polled in-turn |
| grok | **no** | **no** | auto-background after ~15 s, `get_command_or_subagent_output` polling |
| muse | **no** | **no** | Bash yields at 300 s → `background_running`, `bash_input` polling |
| qwen / opencode | **no** | **no** | (not active in window) |

**Genuine silent early exit (guard false negative).** `sase-14t.3` (agy /
`gemini-3.8-flash-high`, `202609/20/20260920205622`, Sep 20 22:35–22:40 EDT):

- The entire final reply is three lines of _"I have launched `sase doctor` … and am
  waiting for it to complete."_
- `done.json` says `outcome: completed`, and the commit finalizer reported `success`.
- Bead `sase-14t.3` is still `IN_PROGRESS` 21 h later.
- This is the pure form of the failure you described, and the existing agy guard did
  not catch it.

### 3.4 Codex "deaths" were quota, not confusion

- The two Codex runs that died mid-wait (`sase-113.1` and `0me--code`) had spent 30–40
  minutes polling a running `just check` or Rust rebuild, narrating _"Still waiting. No
  new output yet. Still in the silent full test lane…"_
- They then died on _"You've hit your usage limit"_.
- Codex polls correctly in-turn (_"I'm keeping the session open so no background command
  is left dangling"_), but expensively: **5,549 "still waiting / no output yet"
  narration lines across 226 Codex runs**, peaking at 229 in one run
  (`sase-11l.5.1.2.1.3`).
- Codex was later auto-disabled for 105–114 h, and Grok for 140 h. I did not prove that
  polling caused those limit hits. It is a plausible contributor worth measuring.

## 4. Finding 2 — commands outlive every provider's tool-call window

### 4.1 How long the commands are

| Measure | n | Median | p90 | Max |
| --- | ---: | ---: | ---: | ---: |
| `sase tool run check` (ToolRun ledger, Sep 20–21) | 125 | 4.5 min | 34 min | 135 min |
| `test (scoped)` stage within those | 51 | ~0 (cached/skipped) | 42.7 min | 128 min |
| `just check` inside a monitor (Sep 14–21) | 56 | 15.0 min | 45 min | 67 min |
| `just check-full` inside a monitor | 39 | 45.1 min | 145 min | 276 min |

Contributing causes seen directly in transcripts:

- **Host contention.** Load averages of 46–50 during the Muse runs on Sep 20. `uptime`
  still showed ~33 during this audit.
- **Per-workspace `_setup` Rust rebuilds.** The Justfile's `_setup` rebuilds
  `sase_core_rs` from the linked `sase-core` checkout whenever it is stale. Examples:
  - `sase-11t.2--plan`: `just test` on two files took **17.5 min**; pytest reported
    _"45 passed in 11.97s"_.
  - `sase-11y.3--2`: **11.6 min** wall time for _"44 passed in 5.75s"_.
  - Codex narrated it directly: _"The first test run is rebuilding the Rust extension
    because the linked core checkout had moved ahead of the installed wheel."_
- **`| tail -n N` hides progress.** Agents pipe verification through `tail`, so nothing
  prints until it finishes. Muse: _"its output is piped through `tail`, so nothing shows
  until it finishes"_. A silent command looks stalled, which invites cancellation.

### 4.2 What each harness does when a command outlives its window

| Provider | Evidence | Resulting behavior |
| --- | --- | --- |
| grok | 754 of 3,558 Bash calls (21%) came back `"status":"running"`, clustered at 16–17 s. The model says _"auto-backgrounded after 15s"_. 836 `get_command_or_subagent_output` polls, 11 `kill_command_or_subagent` | Polls a few times, then usually switches to `sase monitor start` (82 handoffs = 49% of Grok runs) |
| muse | 63 Bash calls ended at exactly ~300 s. Commands move to `execution_state: background_running`, then `bash_input` polls | 48 runs hit the yield. 30 waited it out in-turn. **11 cancelled an in-flight command; 8 of those then read `/sase_monitor` and handed off** |
| codex | Unified exec (`codex features`: `unified_exec stable true`). 5,549 poll-narration lines | Stays in-turn and burns tokens. 22 of 78 handoffs came after long inline verification |
| claude (post-fix) | Blocks in the foreground up to 4 h in one tool call | Cheapest wait: zero polling. 21 monitor handoffs |

## 5. Finding 3 — "start inline, then switch to a monitor" throws work away

The standing guidance creates a decision the agent can only make mid-flight:

- `lint_and_test.md`: _"`just check` may be run inline, but hand it to a monitor the same
  way whenever it is taking a long time."_
- `sase_monitor` skill: _"Use this skill when a command may take long enough that waiting
  inline would block the agent turn."_ Its canonical example is monitoring
  `sase tool run check`.

A monitor can only start a **new** command, so switching means restarting.

Measured, per handoff, looking at the starter's own tool trail before `sase monitor
start`. Counts differ slightly from §2 because `--help` probes are excluded here:

| Provider | Handoffs | Preceded by long/backgrounded inline verification | Wall time from first such inline start to handoff (sum) |
| --- | ---: | ---: | ---: |
| grok | 80 | 51 | 592 min (median 4.8, max 78) |
| codex | 78 | 22 | 597 min (median 26, max 75) |
| muse | 7 recorded (+~6 unrecorded) | 5 | 86 min (median 17) |
| claude | 21 | 0 | — |

Not all of that time is duplicated. Some inline runs finished and informed a fix, and
the monitor then ran something broader. The clean, unambiguous duplication is Muse's.

**Case study, `sase-14n.14--plan` (muse, `202609/20/20260920171620`, UTC):**

1. 22:03:19 — ran `sase tool run check 2>&1 | tail -n 30`.
2. 22:08:22 — Muse's 300 s yield moved it to the background.
3. 22:10 → 23:04 — waited in-turn, narrating _"Verification is still running; the bead
   stays open until it lands"_. Load average was 46–50.
4. 23:04:38 — read the `sase_monitor` skill.
5. 23:04:54 — **cancelled the ~61-minute-old in-flight check** (`terminated by
   bash_input`).
6. 23:05:46 — ran `sase monitor start`; the agent was killed.
7. `--mon` re-ran `just check` from zero and failed after 11.3 min. Then came follow-up
   `--1`, another monitor `--mon-0` (8.9 min, passed), and follow-up `--2`.

The same shape — yield, poll, read the skill, cancel, monitor — appears in:

- `sase-11y.10.1.3.1.2--plan`
- `sase-14j.4--plan`
- `toobig-5q.plan_approval_actions.0--plan`
- `sase-11y.10.1.4--2`
- `0oo--code`, which cancelled an in-flight **`just install`** and `just _lint-symvision`
  to hand them to a monitor.

This is almost certainly the "runs a command that takes a long time, then runs some
kind of internal monitor, then dies" you are seeing on Sep 20–21, when Muse was the most
active provider.

## 6. Finding 4 — verify→fix→re-verify chains make it feel "constant"

After a monitor fails, the follow-up agent fixes something small and re-runs the entire
verification under a new monitor. Each hop costs a kill, a fresh agent with forked
family context, and a full-suite run.

| Family | Provider | Monitors | Outcome | Span |
| --- | --- | ---: | --- | --- |
| `sase-126.4` | codex | 15 | 14 failed, 1 passed | Sep 17 20:15 → Sep 18 04:18 |
| `0mu` | grok | 13 | 11 failed, 1 timeout, 1 passed | Sep 18 10:32 → Sep 19 01:18 |
| `0nh` | grok | 8 | 6 failed, 1 timeout, 1 passed | Sep 18 22:02 → Sep 19 08:55 |
| `0mi` | codex | 8 | 3 failed, 1 timeout, 4 passed | Sep 17 16:37 → Sep 18 01:51 |

The same pattern repeats in 19 more families. In total: 23 families with ≥3 monitors,
119 monitors.

- **`sase-126.4`**
  - Every hop re-ran
    `just install && just fix && just check && just test-visual && just phase7-perf-check && just check-full`.
  - One hop (`--mon-4`) failed on a single test after a 34-minute full-suite run
    (_"1 failed, 42695 passed"_).
- **`0mu`**
  - Grok wrote its own load-gated wrapper (`while load > N; sleep`) around check-full.
    It ran up to 92 min per hop.
- **Agent-chosen timeouts were too short**, wasting whole runs. 18 monitors timed out.
  For example, `0nh--mon-0` killed check-full at its 60-min timeout; the retry then
  needed 145 min.

One policy change already helped a lot. `28d1e8708` (Sep 19, _make just check-full
explicit-only for agents_) took check-full monitors from **30 on Sep 18 → 9 → 1 → 0 on
Sep 21**. The remaining chains are mostly `just check` plus Muse's cancel-and-restart.

The Sep 10 research (`research:202609/monitor_continuation_design/monitor_continuation_design.md`)
already attacks the **per-hop** cost: recursive transcript replay in follow-ups. This
report is about **hop count** and **duplicated command execution**. The two are
complementary.

## 7. Root causes, ranked

1. **The switch to a monitor is destructive.** There is no way to hand an already-running
   verification to a monitor, so every late switch restarts from zero (§5).
2. **The policy asks for a prediction the agent can't make** ("whenever it is taking a
   long time"). This forces a mid-flight decision, which is exactly when (1) bites.
3. **Verification is slow and high-variance**: host contention, per-workspace Rust
   rebuilds, full-lane escalation (§4.1). Commands routinely outlive every provider's
   15 s / 300 s / poll windows.
4. **Nothing stops verify-fix-verify monitor loops.** No hop cap, no "re-run the failures
   first", and timeouts guessed by the agent (§6).
5. **Uneven, contradictory headless contract across providers.** Only Claude and agy
   are guarded. The Claude directive disagrees with the monitor skill. Native Claude
   `Monitor`/Cron tools remain offered. The agy guard produced a false `completed`
   (§3).
6. **Pre-Sep-15 only:** Claude using native background tools. Already fixed.

## 8. Options considered

| Option | Addresses | Verdict |
| --- | --- | --- |
| A. More "you are headless" prompting everywhere | 5, partly 6 | **Not sufficient.** Agents already know. The skill text says it, Muse and Grok read it, and then they cancel and re-run. It doesn't touch causes 1–4 |
| B. Forbid monitors for `just check`; always wait inline | 1, 2 | Great for Claude (one blocking call). For Grok and Codex it means long in-turn polling, which burns quota (§3.4) and holds runner slots. Not provider-neutral |
| C. Always run `just check` through a monitor, never inline | 1, 2 | Removes duplication but maximizes hops. Every change pays a kill + forked follow-up even when check takes 3 min (ToolRun median 4.5 min) |
| **D. Joinable detached ToolRuns + monitor adoption + mechanical `--handoff-after`** | **1, 2**, partly 4 | **Recommended core.** No duplication, no prediction, provider-neutral, reuses the ToolRun ledger and monitor machinery |
| **E. Provider-neutral single-turn contract + per-provider wait-state guards** | **5** | **Recommended.** Closes the residual headless failures |
| **F. Chain governor (targeted re-verify, hop cap, history-based timeouts)** | **4** | **Recommended** |
| **G. Make verification faster (shared core-wheel cache, admission control)** | **3** | **Recommended as follow-on.** Highest long-run leverage, larger project |

## 9. Recommended solution

Guiding principle, consistent with `decisions:single-turn-agents` ("continuation is
always mechanical"): **the tool, not the model, decides when a wait becomes a handoff,
and a handoff never discards work already in progress.**

### 9.1 Make verification runs durable and joinable (core fix)

- **Detach the child from the agent's lifetime.** `sase tool run <tool>` should start
  its child under the proc supervisor, in its own session and process group, with the
  ToolRun as the durable handle. Killing the agent at handoff must not kill the run.
- **Join instead of restart.** In `tool_run_begin`, if a non-terminal run already exists
  for the same key, attach to it and wait on its settlement instead of spawning. The key
  is (project, workspace, tool definition digest, extra-args digest, input fingerprint).
  The ledger already stores `definition_digest`, `extra_args_digest` and
  `fingerprint_before_json`.
  - Consequence: `sase monitor start … -- sase tool run check` issued while an inline
    `sase tool run check` is in flight **adopts** it. No restart, no cancel.
  - Same for two sibling agents or a follow-up re-requesting the same tree.
- **Where it lives.** This is shared backend behavior: any frontend that runs tools must
  agree on join semantics. It belongs in `sase-core` (`sase.core.tool_run` is already
  the adapter), with Python as thin glue, per the Rust-core boundary rule.

### 9.2 Replace the prediction with a mechanical threshold

- **One flag.** Add `--handoff-after DURATION` (plus `--next`/`--model`, reusing the
  monitor flags) to `sase tool run`, and make it the default in the `verify` profile.
- **Behavior.** The run executes normally. If it settles before the threshold, the agent
  just gets the result — the common 3–5 min case, with no hop. If not, the command
  itself creates a monitor that **adopts the in-flight ToolRun** (no new process), then
  ends the turn mechanically, as `sase monitor start` does today.
- **Threshold.** Pick it per provider and from history:
  - Claude can block for hours at zero token cost, so hand off late (e.g. 60 min).
  - Grok and Codex wait by polling, so hand off earlier (e.g. 10–15 min), well before
    polling becomes expensive.
  - Muse waits cheaply in 300 s `bash_input` polls, so hand off around 20–30 min.
  - Make it configurable, and derive it from ToolRun history (`sase tool list` already
    shows TYPICAL).
- **Monitor timeout.** Default it to `max(agent value, 1.5 × p95 of recorded runs)`, so
  agents stop picking 45 min for a 145 min command.

### 9.3 Rewrite the guidance around the mechanism

These are memory/skill edits, so implementers must go through `/sase_memory_write`.

- **`lint_and_test.md`.** Replace "may be run inline, but hand it to a monitor … whenever
  it is taking a long time" with the single rule: _"Run
  `sase tool run check --handoff-after auto --next '<what to do after>'`. Never cancel an
  in-flight verification to re-run it."_ Also say not to pipe through `| tail`: the
  ToolRun already prints compact output, and piping hides liveness.
- **`sase_monitor` skill.** State that monitoring a `sase tool run` that is already
  running adopts it. Replace the canonical example with the `--handoff-after` form.
- **Claude `_SINGLE_TURN_DIRECTIVE`.** Make it agree with the skill: _"Waiting in the
  foreground is fine. For durable waits, `sase monitor start` / `--handoff-after` ends
  your turn and a successor resumes; that is the only way to wait beyond this turn."_
- **Record the policy** as a decision (e.g. "Long-running work is adopted, never
  restarted"), so future guidance edits don't reintroduce the inline-then-switch
  pattern.

### 9.4 A provider-neutral single-turn contract (closes the residual headless failures)

- **One directive for every provider.** Move the directive text into the provider-neutral
  layer. Apply it to codex, grok, muse, qwen and opencode, not just claude and agy.
- **Wait-state detection in every stream parser**, feeding one shared "nudge, then fail
  loudly" policy. Detectors per provider:
  - Claude: `backgroundTaskId` (exists).
  - Grok: tool results with `"status":"running"` and no later settle.
  - Muse: `background_running` sessions never terminal.
  - Codex: unified-exec sessions still open at `turn.completed`.
  - agy: extend the no-progress classifier. `sase-14t.3` must fail, not report
    `completed`.
- **Never report a run as `completed`** if its final reply is a wait statement and a
  background task is outstanding. Raise instead, as the Claude guard already does.
- **Disallow Claude's remaining native tools in print mode:** `Monitor`,
  `CronCreate`/`CronDelete`/`CronList`, `RemoteTrigger`, `PushNotification` (keeping
  `ScheduleWakeup`). Look for equivalent CLI switches for the others. Codex's
  `unified_exec` feature flag may allow blocking execution; that needs an experiment
  before relying on it.

### 9.5 Govern verify→fix→re-verify chains

- **Targeted re-verify.** After a failed verification monitor, the follow-up prompt
  should carry the failing gate or test IDs (from `sase tool show`). The rule: re-run
  the failures first, then the full `just check` only once they pass.
- **Hop cap.** After 3 consecutive failed verification monitors in one family, the next
  follow-up must raise `/sase_questions` or a gate instead of starting hop 4.
- **Settled.** Keep check-full explicit-only; `28d1e8708` already removed most multi-hour
  hops.

### 9.6 Reduce how often commands are long (follow-on)

- **Shared prebuilt `sase_core_rs` wheel per sase-core commit.** Use the existing
  `SASE_CORE_WHEEL` hook in `_setup`, so 30+ workspaces stop compiling the same Rust
  extension.
- **Admission and weighting for test lanes** under load. See the existing
  `command_capacity_and_load_meter` research.

### 9.7 How to tell it worked

Track these weekly from the same artifacts this audit used:

| Metric | Baseline (Sep 14–21) | Target |
| --- | --- | --- |
| In-flight verification cancelled then re-run (Muse `terminated by bash_input`, Grok `kill_command_or_subagent` on verify commands) | 20 cancellations in 11 Muse runs, plus Grok kills | 0 |
| Monitor handoffs per agent run | 16% overall; Grok 49% | Mostly epic launches and explicit long waits |
| Families with ≥3 monitors | 23 (119 monitors) | ≤3, each gated after hop 3 |
| Monitor timeouts | 18 | ~0 (history-based defaults) |
| Codex poll-narration lines per run | 24.6 avg over 226 runs | Bounded by the `--handoff-after` threshold |
| Runs ending in a wait reply but recorded `completed` | ≥1 (`sase-14t.3`) | 0 (guard raises) |
| Native Claude background/scheduling tool uses | 0 since Sep 15 | 0 (tools disallowed) |

## Appendix A — evidence pointers

Artifact dirs are under `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/`.

- **Pre-fix Claude native background use:**
  - `14/20260914090758` (`sase-10w.1`)
  - `14/20260914070315` (`sase-zw.8.1`)
  - `14/20260914090801` (`sase-10w.3`)
  - `14/20260914041806` (`toobig-5d.test_artifact_cli_link_health.0`)
  - `14/20260914080911` (`sase-zn.9.land--2`)
- **Claude misreading the directive:** `20/20260920090315` (`0nz`).
- **agy false `completed`:** `20/20260920205622` (`sase-14t.3`).
- **Codex quota death while polling:**
  - `14/20260914153557` (`sase-113.1`)
  - `17/20260917105414` (`0me--code`)
- **Muse cancel-and-restart:**
  - `20/20260920171620` (`sase-14n.14--plan`)
  - `20/20260920212106`
  - `20/20260920163306`
  - `20/20260920112350`
  - `20/20260920221847`
  - `21/20260921135726`
- **Grok auto-background then handoff:**
  - `18/20260918093921` (`0mu--code`)
  - `19/20260919043506` (`0nh--5`)
- **Monitor chains:** `sase monitor list --all -l <family>` for `sase-126.4`, `0mu`,
  `0nh`, `0mi`.

## Appendix B — reproduction sketch

The audit scripts walked each run's `tool_calls.jsonl`. They joined `ToolUse` and
`ToolResult` rows on `tool_use_id`, then flagged:

- tool names such as `Monitor`, `ScheduleWakeup`, `TaskOutput`, `TaskStop`, `bash_input`,
  `get_command_or_subagent_output` and `kill_command_or_subagent`;
- `run_in_background` in Bash inputs;
- responses with `"status":"running"` (Grok) or `background_running` (Muse);
- Muse Bash results lasting 295–305 s;
- the last `sase monitor start` / `sase plan propose` / `sase sudo request`.

Other inputs:

- Monitor statistics come from `sase monitor list --all --format json`.
- ToolRun statistics come from the `runs` and `stages` tables in
  `~/.sase/tools/runs.sqlite`.
- Provider mix by day was Codex/Claude on Sep 14–17, Grok/Codex on Sep 18–19, and
  Muse/Claude on Sep 20–21. Codex and Grok were usage-limit-disabled in between.
