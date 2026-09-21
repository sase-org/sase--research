# Why SASE Agents "Die" After Long Commands: Consolidated Audit and Recommendation

Date: 2026-09-21. Lead-researcher consolidation of three independent reports, plus new
verification against SASE `c6807d24c`, the installed provider CLIs, and run telemetry on
athena from Sep 14–21.

| Dependency | Preserved report | Immutable snapshot | Main contribution |
| --- | --- | --- | --- |
| `research.25.cld` | [cld](agent_long_command_early_exits__cld.md) | `file:explicit:a45b3e221d06f59121470617` | Full telemetry audit across 1,193 agent runs, 270 monitors, and the ToolRun ledger; the inline-then-switch finding; the chain analysis |
| `research.25.mus` | [mus](agent_long_command_early_exits__mus.md) | `file:explicit:3dce6e23de3de8c46ba04f87` | Provider guard matrix; "enforce the contract once, centrally" framing; pre-fix transcript cases |
| `research.25.gem` | [gem](agent_long_command_early_exits__gem.md) | `file:explicit:34c43ed55641cde2cf7f474d` | Deep agy (Antigravity) mechanism analysis; two agy failures traced step by step; a working keep-alive pattern demonstrated live |

No predecessor chat transcripts were read.

## Bottom line

**Your hypothesis is partly right. Three different things look the same from the TUI**
("ran a long command, some monitor started, the agent died"). Only one of them is agents
misunderstanding headless mode.

1. **Silent false success. This is the headless misunderstanding.**
   - **What happens:** the agent backgrounds a command with its harness's own
     mechanism, ends its reply with "waiting…" or "monitoring…", and SASE records the
     run as `completed`. The work is lost.
   - **Claude:** common before Sep 15 (10 of 67 Claude runs on Sep 14). Fixed by
     `bdda3bdf1`; zero cases since then.
   - **agy (Antigravity):** happening today, in **2 of the 7 agy runs on Sep 20–21**.
     One of them was `research.24.gem`. Its lost report stalled the `research.24`
     swarm, which this dispatch re-runs. That is probably what prompted this request.
   - **Other providers:** I found no case on Grok, Muse, or Codex since Sep 15.
2. **Designed monitor handoffs. This is most of what you see.**
   - `sase monitor start` kills the agent on purpose. It ended **190 of 1,193 agent
     runs (16%)** from Sep 14 to 21, including **49% of Grok runs**.
   - The mechanism works as specified.
   - The problem is how agents reach it. They start verification inline and discover
     it is slow. Then they cancel the in-flight run and restart it from zero under a
     monitor. When it fails, they repeat the cycle: 23 agent families ran ≥3 monitors;
     the worst took 15 hops over 8 hours.
3. **Slow verification sits underneath both.**
   - `just check` has a p90 of 34–45 min. `check-full` has a median of 45 min.
   - Every provider's tool-call window is far shorter. Past it, the command is pushed
     to the background or the call returns while the command is still running:
     agy at 10 s, Grok at about 15 s, Muse at 300 s.

**Root causes.**

- **The model makes the wait-or-hand-off decision.** Nothing mechanical does.
  - The agent has to make a duration prediction it cannot make.
  - Its instructions contradict each other.
  - The only handoff primitive, `sase monitor start`, destroys work already in flight.
- **Each provider enforces the single-turn contract separately, and SASE's "success"
  test is too weak to catch a turn that stopped halfway.**

**Recommendation (§6).**

1. **Now:** add a host-side backstop that fails runs ending mid-task. Repair agy's wait
   path. Replace "hand it to a monitor whenever it is taking a long time" with a rule
   each provider decides up front.
2. **Next:** make handoff mechanical and lossless. Verification runs should be
   joinable and survive the agent. A monitor should adopt an in-flight run. A
   `--handoff-after` threshold should replace the model's guess.
3. **Then:** add a governor on verify→fix→re-verify loops, and make verification
   faster.

Adding more "you are headless" text to prompts will not fix this. The agents already
know they are headless. agy's own harness tells the model to end its turn, and no
prompt wins against that.

## 1. Where the reports agree, disagree, and what I verified

| Claim | Source | Verdict after my checks |
| --- | --- | --- |
| Claude's native-background exits stopped after `bdda3bdf1` (Sep 15) | cld, mus | **Confirmed.** mus's ~15 transcript cases all date from Sep 7–13. My scan of Sep 15–21 wait-ending replies found no Claude case that was not a monitor handoff or a read-only answer |
| Grok/Muse/Codex silently lose work, and this is the dominant cause (mus: "explains the grok-heavy telemetry") | mus | **Not supported.** I scanned every Sep 15–21 run whose final reply ended in wait language and had no declaration or plan (19 runs). Every Grok and Codex case ended with a trailing `sase monitor start`. The Muse cases correspond to monitors in `sase monitor list` (Muse records empty tool inputs). The one Codex failure was usage-limit exhaustion. mus's 573 Grok "background-poll" calls are **in-turn polling, which works**. The missing guards are a real *latent* risk, not the current source of losses |
| agy: `run_command` cannot block longer than 10 s; the tool text orders "update the user … and end the turn. DO NOTHING ELSE"; print mode kills background tasks after a 5 s idle grace and exits 0 | gem | **Confirmed in the agy 1.2.7 binary.** Strings found: `WaitMsBeforeAsync must be in the range [%d, %d]` (schema: 500–10000 ms); `IMPORTANT: Do NOT poll or loop on status … Simply proceed with other work or stop calling tools`; `root agent idle; waiting up to %s for %d background task(s)`; `terminating %d background task(s) … on exit`. The run_command schema exposes no blocking option. (`IsDaemon`/`RunPersistent` are hidden from the model) |
| agy's text classifier misses the two replies | gem, cld | **Confirmed by running the code.** `_classify_agy_no_progress(text, None)` returns `(False, 'text_progress')` for both the `sase-14t.3` and `research.24.gem` replies |
| Fixing the `sase-15o` allowlist would "immediately restore" detection | gem | **True, but only by accident.** Replaying both runs' trajectory databases through the current analyzer does yield `trajectory_pending_run_command`. It does so only because the decoder misreads agy 1.2.7's layout. Tool calls and their names now live in step type 132 (which the decoder treats as a *result*). The later `manage_task` status calls are not recognized as tool uses at all. A decoder that correctly recognized them would see a *completed* `manage_task` as the last tool and accept the turn. Widening the allowlist without validating the decoder is fragile (see §6.1) |
| "Workspace wiped, uncommitted work deleted" | gem | **Overstated for the cited case.** `sase-14t.3` had a clean tree. The damage was a phase bead left `IN_PROGRESS` (still true 22 h later) and, for `research.24.gem`, a report that was never written |
| Most visible "dying" is the designed monitor handoff, used destructively | cld | **Confirmed.** Per-day monitor counts (below) match cld. I re-traced the `sase-14n.14--plan` cancel-and-restart timeline in its `tool_calls.jsonl`: a 300 s yield, an in-turn wait, the monitor skill read at 23:04:38, then `bash_input` interrupting a ~61-min-old `sase tool run check` at 23:04:54 |
| `sase tool run` / `sase monitor` can adopt an already-running command | — | **No such capability exists.** A monitor start with an identical fingerprint returns the existing *monitor*, but no ToolRun join exists. The tool executor starts its child in a new session but forwards termination to the child's process group. So killing the agent kills the check |

**New findings from this consolidation.**

- **The host accepted a mid-task abandonment as success.**
  - For `sase-14t.3`, `finalizer_result.json` reports `commit: success` with no
    attempts and no evidence, and no `final_submission.json` exists.
  - Why: `builtin@commit` requires a declaration only when a repository is dirty
    (`declaration_store.py`: `submission_required=bool(repository_obligations)`).
  - So a phase worker that stops halfway, on a clean tree, "completes".
  - I then checked every Sep 15–21 run that had an assigned bead, no declaration, no
    plan, and no trailing handoff (11 runs):
    - 9 were Muse monitor handoffs.
    - 1 was a deliberate "keep in progress" (`sase-11o.2`, Claude).
    - 1 was the agy false success.
  - A "declaration required when a bead is assigned" rule would therefore catch the
    real failure. Its only cost elsewhere is one `keep` declaration.
- **Grok's auto-backgrounding is configurable.**
  - Grok 1.0.40's shipped config reference lists `toolset.bash.timeout_secs`,
    `toolset.bash.max_timeout_secs` and `toolset.bash.auto_background_on_timeout`.
  - SASE sets none of them. Grok could potentially block the way Claude does.
  - I could not confirm a per-run override path. `GROK_CONFIG` accepts allowlisted
    keys only, and `grok inspect` does not print toolset values.
- **Claude still exposes background tools in print mode.**
  - This session (`claude -p`, SASE single-turn) was offered deferred `Monitor`,
    `CronCreate`/`CronDelete`/`CronList`, `RemoteTrigger`, `PushNotification` and
    `SendMessage`.
  - It was also offered a loaded `Workflow` tool, whose description says it "runs in
    the background … a task-notification arrives when the workflow completes".
  - None of these can deliver in single-turn mode. Only `ScheduleWakeup` is disallowed.

## 2. Failure mode A — silent false success (the headless misunderstanding)

### 2.1 Claude before Sep 15 (fixed)

- **Before.** On Sep 14, 10 of 67 Claude runs used `run_in_background`,
  `ScheduleWakeup`, `Monitor`, `TaskOutput` or `TaskStop`. They ended with lines like
  _"The Bash background task itself will notify me automatically"_ (`sase-10w.3`).
  - mus found the classic rationalization in `ace_run-sase_xz_3-260907_105255`.
  - The agent scheduled a wakeup, then decided it did not need one because _"the
    backgrounded `just check` will automatically notify me."_
- **The fix.** `bdda3bdf1` added four things:
  - the `_SINGLE_TURN_DIRECTIVE`;
  - `--disallowedTools ScheduleWakeup`;
  - `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` plus a 4 h `BASH_MAX_TIMEOUT_MS`;
  - a stream-level wait-state classifier that nudges twice and then raises.
- **After.** 0 native background uses in the 269 Claude runs since the fix.

### 2.2 agy today (active)

| Run | Command backgrounded at 10 s | Final reply | SASE recorded | Real outcome |
| --- | --- | --- | --- | --- |
| `sase-14t.3` (`20260920205622`, gemini-3.8-flash-high) | `sase doctor` | _"I have launched `sase doctor` … and am waiting for it to complete."_ | `completed`; commit finalizer `success` | Phase bead still `IN_PROGRESS` |
| `research.24.gem` (`20260921162655`) | `time ./scripts/check.sh clippy` | _"I am monitoring the execution … I will proceed … once the build step finishes."_ | `SUCCESS` (workflow log) | No report; the swarm's lead stopped for a missing input |

The failure takes six steps, and each layer was individually reasonable:

1. agy forces any command longer than 10 s into the background.
2. Its tool result tells the model to report and end the turn, and not to poll.
3. The model obeys and stops calling tools.
4. agy print mode sees an idle root agent, waits 5 s, kills the task, and exits 0.
5. SASE's structural check is off because of the version allowlist (`sase-15o`). The
   text fallback misses "monitoring" / "once … finishes" and replies that have no
   "I will"-style lines.
6. The host finalizer does not require a declaration on a clean tree.

gem demonstrated the in-harness escape. After a command is backgrounded, the agent
**keeps calling tools** (`manage_task status`, reading output). agy then delivers the
completion message inside the same turn. `research.25.gem` finished this way.

### 2.3 Grok, Muse, Codex (latent)

None has a SASE directive or wait guard, as mus's matrix shows. Their harnesses keep
the turn alive while a command runs, and in practice their models polled or handed off:

- **Grok:** returns `"status":"running"` at about 16 s; there is a clear spike of Bash
  results there. It then polls with `get_command_or_subagent_output`.
- **Muse:** yields at 300 s and then polls with `bash_input`.
- **Codex:** polls unified-exec sessions in-turn.

This costs quota rather than work:

- cld counted 5,549 Codex "still waiting / no output yet" narration lines across 226
  runs.
- Two Codex runs died on usage limits mid-poll.

## 3. Failure mode B — designed monitor handoffs used destructively

Monitors started per day, by starter provider (my recount from `sase monitor list --all`):

| Day | Total | Dominant rows |
| --- | ---: | --- |
| Sep 17 | 39 | codex check 12, codex check-full 11, epic launch 7 |
| Sep 18 | 84 | grok check 25, grok check-full 15, codex check-full 15, epic launch 14 |
| Sep 19 | 43 | grok check 24, grok check-full 9 |
| Sep 20 | 21 | epic launch 10, muse check 8 |
| Sep 21 | 14 | epic launch 7, muse 7 |

**The guidance forces a mid-flight decision.** `lint_and_test.md` says _"`just check`
may be run inline, but hand it to a monitor the same way whenever it is taking a long
time."_ The `sase_monitor` skill triggers on _"when a command may take long enough…"_.
Since a monitor can only start a *new* command, switching late means restarting.

**cld measured the cost:**

- 51 of 80 Grok handoffs and 22 of 78 Codex handoffs came after long or backgrounded
  inline verification. That is about 590 min of prior inline wall time each.
- Muse cancelled in-flight verification 20 times in 11 runs. 8 of those runs then read
  the monitor skill and handed off.
- `0oo--code` even cancelled an in-flight `just install`.

**Chains** (cld):

- 23 families ran ≥3 monitors, 119 monitors in total.
- `sase-126.4` (Codex) ran 15 monitors over 8 h, 14 of which failed. Every hop re-ran
  the full suite.
- 18 monitors hit agent-chosen timeouts that were too short. For example, check-full was
  killed at 60 min, and its retry needed 145 min.

**One fix already helped.** `28d1e8708` made check-full explicit-only. Check-full
monitors fell from 30 (Sep 18) to 0 (Sep 21).

**Claude's instructions contradict the skill.**

- The Claude directive says _"Run commands synchronously in the foreground … Never end
  your turn to wait."_
- The monitor skill says to hand off, which ends the turn.
- One Claude agent (`0nz`) concluded that monitors "could never reach me". That is
  false, but harmless for Claude, since Claude can block for 4 h.

## 4. Failure mode C — verification outlives every harness window

| Measure | n | Median | p90 | Max |
| --- | ---: | ---: | ---: | ---: |
| `sase tool run check` (ToolRun ledger, Sep 20–21) | 125 | 4.5 min | 34 min | 135 min |
| `just check` inside a monitor | 56 | 15 min | 45 min | 67 min |
| `just check-full` inside a monitor | 39 | 45 min | 145 min | 276 min |

Drivers seen directly in transcripts:

- **Host load average of 33–50.**
- **Per-workspace `_setup` rebuilds of `sase_core_rs`.** In one case, 17.5 min of wall
  time covered 12 s of pytest.
- **`| tail -n N` piping.** It hides all progress, so the run looks stalled and invites
  cancellation.

## 5. Provider matrix (merged)

| Provider | SASE directive | Native bg tools disabled | Wait guard | Foreground window | Knob to block longer | Observed behavior |
| --- | --- | --- | --- | --- | --- | --- |
| claude | yes (contradicts skill) | partly: `ScheduleWakeup` only; `Monitor`, Cron, `RemoteTrigger`, `PushNotification`, `Workflow` still offered | yes | 4 h (`BASH_MAX_TIMEOUT_MS`) | already set | Blocks; 0 failures since Sep 15 |
| agy | yes (tells it to "run synchronously", which is impossible) | n/a | **broken** (allowlist + regex) | **10 s, hard** | none in 1.2.7 | 2 of 7 runs false success |
| grok | no | no | no | ~15 s auto-background | `toolset.bash.*` config (per-run override unverified) | Polls, then hands off (49% of runs) |
| muse | no | no | no | 300 s yield | unknown (`--enable-shell-tool` legacy shell untested) | Polls; cancel-and-restart |
| codex | no | no | no | polled unified exec | `unified_exec` flag (untested) | Polls expensively |
| qwen / opencode | no | no | no | — | — | inactive in window |

## 6. Recommended solution

**Guiding principle.** This applies `decisions:single-turn-agents`: "continuation is
always mechanical".

- **Mechanism, not the model, decides when a wait becomes a handoff.**
- **A handoff never discards in-flight work.**
- **A turn that stops mid-task fails loudly, whatever the provider.**

Options I rejected:

- **Prompting alone.** Agents already know they are headless, and agy's harness
  overrides the prompt.
- **"Always wait inline".** Cheap for Claude, but it means hours of token-burning polls
  for Grok and Codex, and it is impossible for agy.
- **"Always monitor" as the permanent design.** It adds a hop even to the median
  4.5-min check. It is acceptable as a stopgap for non-Claude providers (§6.1c).

### 6.1 Phase 0 — stop the bleeding (small, independent changes)

**a. Host backstop against mid-task abandonment (provider-neutral).**

- **Rule:** require a final declaration whenever the run has an assigned bead, even on
  a clean tree. The declaration may say `keep`.
- **Better still:** whenever the run has any registered completion obligation, such as
  a research member's report registration.
- **Classify the ending:** a run that ends with neither a declaration nor a mechanical
  handoff (monitor, plan, pipe, questions, gate) is `incomplete`, not `completed`.
- **Why here:** this catches `sase-14t.3`-class failures for *any* current or future
  harness, independent of text heuristics.
- **Cost:** in the audit window it would have fired on exactly one false success, and
  asked one legitimately blocked worker for a `keep` declaration.
- **Where it lives:** finalizer requirement derivation is shared backend behavior. Put
  it where that wire lives (sase-core, if the requirement logic is mirrored there), per
  the Rust-core boundary.

**b. Repair agy.**

- **Rewrite `_AGY_PRINT_MODE_DIRECTIVE`.** Replace the impossible "run commands
  synchronously" with the verified keep-alive rule:
  - The turn ends the moment you stop calling tools, and background tasks are then
    killed.
  - If a command is backgrounded, ignore the tool's "end the turn" advice. Keep
    checking `manage_task` / reading output until it finishes.
  - For verification, use `sase monitor start` instead.
- **Fix the text classifier.** Treat a short reply that has a wait/monitoring signal
  and no completion signal as no-progress, regardless of "I will" counts. Add
  `monitor(ing)` and `once … (finishes|completes)`.
- **Resolve `sase-15o` properly.**
  - Prefer agy's `--output-format stream-json`; otherwise validate the decoder against
    1.2.x.
  - Define no-progress as **"a backgrounded `run_command` was still pending at turn
    end"**, independent of any trailing `manage_task` calls.
  - Emit a one-time diagnostic whenever structural detection is disabled.
- **Make the continuation nudge state the fact:** the command was killed; re-run it
  and keep polling, or hand it to a monitor.

**c. Replace the mid-flight guidance with an up-front, per-provider rule.**

These are memory/skill edits and must go through `/sase_memory_write`.

- **Claude:** run `sase tool run check` inline with an explicit long timeout. Do not
  monitor `just check`.
- **All other providers:** start verification **directly** under
  `sase monitor start --profile verify`, with the final declaration prepared
  (`sase final prepare`, then `-f/--completion REF`). A pass then completes through
  the host with no extra model turn. Only failures hop.
- **Everyone:** never cancel an in-flight verification to re-run it under a monitor.
  Do not pipe verification through `| tail`.
- **Make the Claude directive agree with the skill:** "waiting in the foreground is
  fine; `sase monitor start` is the only way to wait beyond this turn and ends it by
  design".
- **Disallow Claude's remaining native tools in print mode:** `Monitor`, `Cron*`,
  `RemoteTrigger`, `PushNotification`, `Workflow`.

### 6.2 Phase 1 — lossless, mechanical handoff (the durable fix)

This is cld's core proposal, which I endorse after confirming that nothing like it
exists today.

- **Detached, joinable ToolRuns (sase-core).**
  - `sase tool run <tool>` starts its child under the supervisor, outside the agent's
    process tree. The ToolRun is the durable handle.
  - A second request with the same key joins the non-terminal run instead of spawning
    a new one. The key is project, workspace, definition digest, args digest, and input
    fingerprint; the ledger already stores the digests.
- **Monitor adoption.** `sase monitor start … -- sase tool run check` adopts an
  in-flight run rather than restarting it.
- **`--handoff-after DURATION` on `sase tool run`**, defaulted in the verify profile.
  - If the run settles first, the agent just gets the result.
  - Otherwise the command itself creates a monitor that adopts the run, then ends the
    turn mechanically.
  - This works on every harness, including agy while it keeps polling.
  - Defaults per provider: Claude late (≈60 min); Grok and Codex early (≈10–15 min,
    before polling gets expensive); Muse ≈20–30 min; agy early. Tune from ToolRun
    history.
  - Monitor timeouts default to `max(requested, 1.5 × p95)`.
- **Afterwards, the guidance collapses to one line for every provider:**
  `sase tool run check --handoff-after auto --next '…'`.
  - Record it as a decision ("long-running work is adopted, never restarted") so later
    edits don't reintroduce inline-then-switch.
- **Provider-neutral wait-state detection.**
  - Add "background work outstanding at turn end" detectors to the Grok, Muse and Codex
    stream parsers:
    - Grok: `"status":"running"` with no settle.
    - Muse: a `background_running` session that never reaches a terminal state.
    - Codex: a unified-exec session still open at `turn.completed`.
  - Feed them into the shared nudge-then-fail policy Claude uses.
  - This is insurance, since these providers are not losing work today. It is cheap
    once 6.1a exists.
- **Harness knobs, as experiments.** Try Grok's `toolset.bash.timeout_secs` /
  `max_timeout_secs` / `auto_background_on_timeout=false` through a SASE-owned config
  layer, Muse's legacy shell, and Codex `unified_exec`. If Grok can block like Claude,
  its handoff rate and polling cost should both drop.

### 6.3 Phase 2 — fewer, cheaper hops

- **Governor.**
  - After a failed verify monitor, the follow-up re-runs the failing gates/tests first
    (IDs from `sase tool show`), and the full check only after they pass.
  - After 3 consecutive failed verification monitors in one family, raise
    `/sase_questions` or a gate instead of hop 4.
- **Faster verification.**
  - Build a shared prebuilt `sase_core_rs` wheel per sase-core commit through the
    existing `SASE_CORE_WHEEL` hook, so 30+ workspaces stop rebuilding it.
  - Add load-aware admission for test lanes (see `command_capacity_and_load_meter`).
- **Per-hop cost.** Complementary to the Sep 10 `monitor_continuation_design`
  consolidation, which attacks per-hop replay cost. This report attacks hop count and
  duplicated execution.

### 6.4 Why this order

- **Phase 0** closes the only path that silently loses work today (agy plus the weak
  success test) and removes the most wasteful habit, cancel-and-restart. It needs
  small, independent changes.
- **Phase 1** removes the prediction entirely, so later guidance cannot regress it.
- **Phase 2** reduces how often any of this matters.

## 7. How to tell it worked

| Metric (weekly, from the same artifacts) | Baseline Sep 14–21 | Target |
| --- | --- | --- |
| Runs recorded `completed` with an assigned bead left open and no declaration/handoff | 1 (`sase-14t.3`) | 0: classified `incomplete` |
| agy runs ending in a wait reply | 2 of 7 | 0 |
| In-flight verification cancelled then re-run | ≥20 (Muse), plus Grok kills | 0 |
| Monitor handoffs per agent run | 16%; Grok 49% | Mostly epic launches and genuinely long waits |
| Families with ≥3 monitors | 23 (119 monitors) | ≤3, gated at hop 3 |
| Monitor timeouts | 18 | ~0 |
| Codex poll-narration lines per run | ~25 | Bounded by `--handoff-after` |
| Native Claude background/scheduling tool uses | 0 since Sep 15 | 0, tools disallowed |

## 8. Limits and open questions

- Only athena artifacts were examined; remote machines were not.
- The ToolRun ledger starts Sep 20.
- `research.24.gem`'s artifact directory is gone. Its evidence is the workflow log and
  the agy conversation DB, both of which I checked.
- Grok's per-run bash-timeout override, Muse's legacy shell, and Codex `unified_exec`
  blocking are untested.
- The "join" key for ToolRuns needs care around dirty trees: two runs on different
  uncommitted states must not join. The existing fingerprint fields appear sufficient,
  but that is unverified.
- cld's duplicated-time figures overstate pure waste. Some inline runs finished and
  informed a fix before a broader monitored run. Muse's cancel-and-restart cases are
  unambiguous waste.

## Appendix — evidence pointers

Artifact dirs are under `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/`.

- **agy false success:**
  - `20/20260920205622` (`sase-14t.3`): see `done.json`, `finalizer_result.json`, and
    the agy DB `af9c4e3e-….db`.
  - `research.24.gem`: workflow log `~/.sase/workflows/202609/gh_sase-org__sase_ace-run-260921_162655.txt`
    and agy DB `a92c2c6a-….db`.
- **Claude pre-fix native background use:**
  - `14/20260914090758` (`sase-10w.1`)
  - `14/20260914070315` (`sase-zw.8.1`)
  - `14/20260914090801` (`sase-10w.3`)
- **Muse cancel-and-restart:**
  - `20/20260920171620` (`sase-14n.14--plan`)
  - `20/20260920212106`
  - `20/20260920163306`
  - `21/20260921135726`
- **Grok auto-background then handoff:**
  - `18/20260918093921` (`0mu--code`)
  - `19/20260919043506` (`0nh--5`)
- **Monitor chains:** `sase monitor list --all -l <family>` for `sase-126.4`, `0mu`,
  `0nh`, `0mi`.
- **Code:**
  - `src/sase/llm_provider/agy.py` (`_AGY_PRINT_MODE_DIRECTIVE`,
    `_looks_like_no_progress`)
  - `src/sase/llm_provider/_subprocess_agy.py` (`_SUPPORTED_AGY_TRAJECTORY_VERSIONS`,
    `_analyze_agy_trajectory_steps_progress`)
  - `src/sase/llm_provider/claude.py` (`_SINGLE_TURN_DIRECTIVE`, wait classifier)
  - `src/sase/finalizers/declaration_store.py` (commit requirement trigger)
  - `src/sase/tool/executor.py` (child process-group signalling)
  - `src/sase/monitor/request.py` (fingerprint replay)
- **Related beads and research:**
  - `sase-15o` (agy allowlist, READY)
  - `research:202609/monitor_continuation_design/monitor_continuation_design.md`
