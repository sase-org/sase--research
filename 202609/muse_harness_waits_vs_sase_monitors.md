# Muse Harness Waits vs `sase monitor`: Ban The Wait, Make Muse Synchronous, Route Long Work To Monitors Up Front

Researcher `0q8` (Claude), 2026-09-23. Written against sase `02cd6b69e` and Muse Code
`1.3.0-R3401.1`, using athena telemetry for Sep 20–23 and live `muse exec` experiments.
This is a follow-up to
`research:202609/provider_wait_contract_early_exits/provider_wait_contract_early_exits.md`
("the prior report"). That report recommended that SASE **embrace** Muse's native
post-turn wait. You asked me to critique the opposite plan: forbid the harness wait and
have Muse agents use `sase monitor`.

## Bottom line

**Your plan is right. The prior report's recommendation should not be adopted. Three
adjustments turn your plan from a prompt rule into a mechanism.**

1. **Ban the harness wait.** Muse's post-turn wake keeps a vendor process alive; it does
   not suspend and resume. SASE can't see it: the events that describe it never reach the
   `--json` stream SASE reads. SASE can't bound it or make it durable. It arrived silently
   with a CLI update on Sep 17. And it has produced 17 teardown-watchdog kills in four days,
   all Muse, 16 of them with the waited-on command still running.
2. **Muse cannot run a command synchronously for more than 10 minutes, in any mode.** This
   is the new finding here, and it decides the question.
   - The managed `bash` tool moves a command to the background after at most 300 s.
   - The legacy `shell` tool (`--enable-shell-tool`), which the prior report listed as an
     untested experiment, is truly synchronous: no background, no wake. But it **kills the
     command at exactly 600.1 s and returns only "tool timed out"**, with all output
     discarded.
   - No setting raises either limit.

   So for Muse, any command longer than 10 minutes *must* wait across tool calls. The only
   choices are the harness wake (which we're banning), in-turn polling (which contradicts
   Muse's own tool text), or a SASE monitor. That makes your preference the natural fit, not
   just a defensible one.
3. **The routing line is 10 minutes, decided before the command starts.**
   - A literal "use a monitor whenever Muse backgrounds something" would send 602 commands
     in four days through monitors, 46% of them under a minute (mostly
     `sase bead note/close`). And once a command is backgrounded it is already running; the
     only way to move it is the cancel-and-restart that caused the prior report's mode B.
   - The right cut is the 600 s line. On Sep 20–23 that was **155 Muse commands (0.9%), in
     29% of Muse sessions**. Most were verification or build recipes: `sase tool run check`,
     `just test-scoped`, and `just install`.

**The cheapest monitor already exists and has never been used.** *Prepared monitor
completion* is `sase final prepare` (with `bead_action: close`) plus
`sase monitor start -p verify -f <ref> -- <gate>`. It commits and closes the bead when the
gate passes, **with no successor agent**, and launches a recovery agent only when the gate
fails. Of 1,344 monitors on record, **0** used it.

For Muse's commonest long wait, the final verification gate, a monitor therefore costs
*less* than waiting. The expensive case is a mid-task long command, where a monitor hop
takes a median 176 s (p90 709 s) to get the successor working, versus 6 s for a Muse wake,
and the successor gets a transcript without tool calls. Hops need to get cheaper, because
Muse will make more of them.

**Recommended solution (§7):**

1. Run Muse with `--enable-shell-tool`.
2. Give Muse a SASE directive that states its real 10-minute ceiling, together with the
   routing rules: final gate → prepared completion; known-long commands → a monitor up
   front; everything else inline.
3. Add Claude's stranded-wait guard to Muse, and fix the skill and memory text.
4. Then make the routing mechanical: have `sase tool run` refuse, before starting, any tool
   predicted to exceed the calling provider's synchronous ceiling, and print the monitor
   command to use instead.
5. Make monitor hops cheaper.
6. Long term, have SASE itself provide "start inline, escalate without restarting"
   (detach, wait, and join on ToolRuns, the `sase tool` roadmap's E2), for every provider.

## 1. Method

| Source | What I checked |
| --- | --- |
| Prior report and its inputs | Read with `sase artifact read`: diagnosis, modes A–E, recommendations, open experiments |
| sase `02cd6b69e` | `llm_provider/muse.py`, `_subprocess_muse.py`, `_tool_call_muse.py`, `claude.py`, `agy.py`, `_subprocess_plain.py` (watchdog), the `monitor/` and `axe/` handoff path, `docs/monitors.md`, the `sase_monitor.md` and `sase_final.md` skill sources, `sase/memory/lint_and_test.md`, `sase/memory/sase.md`, `decisions:single-turn-agents` |
| Beads | `sase-16i`, `sase-163`, `sase-12s`, `sase-12r`, `sase-15o` are all still `ready`. Nothing the prior report proposed has landed, and the watchdog is unchanged |
| Muse binary | `muse` launcher → `muse-bin-1.3.0-R3401.1`, a 314 MB stripped Rust ELF. Checked `--help`, the binary's strings (settings schema, tool schemas), settings, preset, and hook behavior, the offline echo provider, and nine real `muse exec` runs, the longest about 11 minutes. All runs used scratch workspaces and a scratch `XDG_DATA_HOME`; the real `~/.config/muse` was read, never written |
| Telemetry | `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/{20..23}`, 361 Muse `session.jsonl` files (Sep 20–23), `sase monitor list --all -j` (1,344 monitors, 68 in the window). Sep 23 data runs to about 14:50 EDT |

The telemetry agrees with the prior report where they overlap: through Sep 22 13:00 EDT, 28
sessions woke successfully after the turn ended and waited 597 min in total; the prior
report had about 31 and 602.

## 2. Facts that decide the design

### 2.1 Muse's two shell modes, measured

| | Managed `bash` (default) | Legacy `shell` (`--enable-shell-tool`) |
| --- | --- | --- |
| Foreground limit | `yield_time_ms` defaults to 10 s and is **clamped at 300 000 ms**. A PreToolUse hook that injected `3600000` still saw a 330 s command go to the background at 300.1 s | **Hard 600.1 s timeout.** A loop printing a line every 60 s was killed at 600.1 s. The tool result was just `tool timed out` (`correlation_facts.outcome: timeout`); **all output was discarded** and the process tree was killed |
| What happens past the limit | The command keeps running in the background. `muse exec` stays alive after the model's turn, wakes the model on completion, and sends overdue reminders every `TBH_OVERDUE_NOTICE_AGE_SECS` (1800) | Nothing: no background state, no wake, no reminder |
| Configurable? | Wake: no setting found. Reminder interval: an env var | The valid `run.*` settings listed in the binary are `system_prompt`, `developer_prompt`, `toolset`, `workflow_trigger_mode`, `workflow_api_version`, `subagent_delegation_mode`, `code_mode`, `context_usage_message_enabled`, `context_slimming`, `reminder_roster`, and `parallel_tool_calls`. None is a timeout; `tool_timeout_sec` exists only for MCP servers. Unknown `run.*` keys are silently ignored, so a validation probe proves nothing either way |
| Tool text the model sees | Long guidance: backgrounding is normal, and the result "wakes you even after you end the turn" | Only "Run a shell command in the workspace subject to runtime policy." Parameter: `command` |

More facts from the binary and the live runs:

- **SASE can't see what is pending.** Stdout omits the inbox events that name pending
  background work (`inbox_item_queued/drained`, sources `background_task_terminal` and
  `background_task_overdue`); they appear only in `session.jsonl`. Stdout timestamps are
  synthetic. A host-side pending-work ledger, the prior report's §5 Step 1.1, would have to
  tail Muse's private session-log format.
- **The Muse model resists blocking.** My first legacy-shell run asked plainly for a
  35-minute foreground loop, and the model *refused*: *"I'm not running that 35-minute
  blocking loop — it would tie up this turn… I can run it detached with output to a log
  file and check progress."* With explicit authorization it complied, hit the 600 s kill,
  and reported the timeout honestly.
  - So the directive must state the ceiling and the routing rules, or the model will
    improvise with `nohup … &`.
- **Other tools that can create out-of-turn work** (`workflow`, `cron_*`, `subagent_*`,
  `work_stop`, `snooze_reminder`) remain under `--enable-shell-tool`. On Sep 20–23 they were
  essentially unused: `snooze_reminder` appeared in 2 sessions, the rest in none. They
  can be removed with a `run.toolset` allowlist in a preset, or denied by a PreToolUse
  hook; both were verified. Both need entries in `~/.config/muse/settings.json`, which the
  user owns. Hooks run with a scrubbed environment.

### 2.2 How long Muse commands really run (Sep 20–23; true durations from session logs)

| Command prefix | Muse runs | Share over 600 s | Claude share over 600 s |
| --- | ---: | ---: | ---: |
| `sase tool run check` | 302 | 18.9% (57) | 13.6% (6 of 44) |
| `just test-scoped` | 32 | **75.0%** (24) | 82.1% |
| `just install` | 58 | 37.9% (22) | 56.0% |
| `just test-wheel` / `rust-install` | 9 | 55% (5) | – |
| `just check` | 88 | 11.4% (10) | 4.5% |
| `just test-visual` | 44 | 13.6% (6) | 15.0% |
| `just fix-tui-screenshots` | 113 | 8.0% (9) | 0% |
| `python -m pytest` | 1,160 | 0.1% (1) | 1.0% |
| `sase bead note` / `close` | 241 | 0% (median 31–38 s under load) | – |
| **All Muse bash commands** | **16,452** | **0.9% (155), in 105 of 361 sessions (29%)** | 27% of runs had at least one (upper bound) |

- Claude blocks through all of these today: 61 of 193 Claude runs spent a median 14.7 min
  (p90 42.9 min) on verification, with no losses.
- Muse can't do the same for about 29% of its sessions.
- Of the 155 over-600 s commands, 129 were verification or build recipes.

### 2.3 What waiting cost on Sep 20–23

| | Muse post-turn wake | `sase monitor` hop (35 non-epic; 34 started by Muse) |
| --- | --- | --- |
| Command end → model acting | median **6.1 s** (p90 13.7 s) | median **176 s** (p90 709 s, max 1,950 s). 6 of 35 re-queued for a runner slot; 2 waited ~30 min |
| Where the delay comes from | — | The starter's model stops 2–10 s after the monitored command launches, but its runner's post-kill bookkeeping takes a median 77 s (up to 415 s). Dispatch waits for the starter to settle (`shells/followup.py` polls up to 60 s; the successor carries `wait_for: [starter]`) |
| Context carried over | The whole session | `#fork` transcript, prompt/response turns only, no tool calls (`history/chat_resume.py:167-197`). The starter's own final reply is replaced by a synthetic "Monitor handoff" block (`axe/run_agent_exec_monitor.py:150-177`) |
| Next turn (whole turn; only indicative) | median 160 s, ~923k input tokens | median 693 s, ~825k input tokens, from a cold ~28.5k-token prompt |
| Durability | Dies with the provider | The supervisor is detached, so the command outlives the agent |
| Host visibility | None | Monitor record, TUI, `sase monitor list` |
| Slot and workspace | Held | Also held: the claim moves to the supervisor, and a live monitor member counts toward the family's slot at weight 1.0. Only the ~180 MB LLM process is freed |
| Incidents | 17 watchdog kills, 46+ in-flight cancel/terminate calls, 4+ stranded waits (mode C) | All 35 successors launched; failed starts were CLI usage errors |
| Prepared completion (`-f`) | n/a | **0 of 1,344 monitors ever**. 31 of the 68 in the window used `-p verify` without it |

**Capacity is not a reason to prefer either:** both hold the slot and the workspace. The
monitor's advantages are durability and visibility. Its costs are latency and lost
context. And when prepared completion passes the gate, none of those costs apply.

## 3. Critique

### 3.1 Is banning Muse's harness wait a good idea? Yes

1. **It can't be seen or bounded.** The prior report's own fix, a pending-work ledger,
   means parsing a private log. The stripped binary and silent behavior changes make that
   fragile: `background_running` appears in 261 of 361 Muse sessions on Sep 20–23 and in
   none of 11 August sessions, and no changelog is on disk.
2. **It is a keep-alive, not a suspend.**
   - It dies with the provider, whether the cause is the watchdog, OOM, a host restart, or
     a CLI update.
   - `decisions:single-turn-agents` reopens only when *"a hosting platform ships a true
     suspend/resume primitive that preserves workspace claims and provider budget across
     the pause."* Muse's wake is not that primitive.
   - Superseding the decision on this basis, as the prior report proposed, would reopen it
     on weaker grounds than its own trigger.
3. **Its harness bugs are ones SASE can't fix.**
   - The delivery race (mode C) strands waits behind a clean exit.
   - The 30-minute overdue notice explicitly offers to *"terminate it with bash_input
     now"*, which is how mode B cancel-and-restart starts.
4. **Per-provider wait contracts are an ongoing tax.** The prior report's §5 Step 2 matrix
   would need re-checking on every CLI release, for every provider. Making each harness
   conform at the adapter boundary shrinks the host contract to one sentence.
5. **It matches what SASE already does for Claude.**
   - The Claude adapter sets `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` and a 4 h
     `BASH_MAX_TIMEOUT_MS`, disallows `ScheduleWakeup`, appends a single-turn directive,
     and has a nudge-then-fail wait guard (`claude.py:44-110`, `:426-427`, `:531`).
   - Result: 1 `run_in_background` in 16,251 Bash calls, and 0 watchdog kills.
   - `muse.py` does none of this: it sets only `MUSE_NO_AUTO_UPDATE` (`:502`) and prepends
     no directive (`:418`).
6. **One rule means consistent instructions.** Modes A and B came from instructions that
   are true for one provider and false for another (prior report R2).

### 3.2 Does "use sase monitors instead" hold up? Yes, but only as a routing rule, not a mechanism

- **It can't be enforced with managed `bash`.** Muse's harness picks the background, not
  the model, and backgrounds everything longer than 10 s by default. Telling the model
  otherwise repeats the "fight the harness with prose" approach that failed on agy. The
  capability itself has to go: switch to the legacy `shell` tool.
- **It needs a decision point before the command starts.** Once a command is running, a
  monitor can't adopt it: `sase tool run` has no detach, handoff, or join today
  (`src/sase/main/parser_tool.py:56-105`). Switching mid-flight means kill-and-rerun.
- **It should apply at the 10-minute line, not the 10-second one.** Below 600 s, the
  legacy shell blocks exactly like Claude's `Bash`, with no hop cost.
- **It carries a real cost for mid-task commands**, such as `just install` before tests or
  `just test-scoped` while iterating. There, a hop is about 3 minutes plus lost context,
  and Muse will hit that in up to ~29% of sessions. That cost is why hops must get cheaper
  (ADJ-5), and why the long-term fix is lossless escalation (ADJ-6).

### 3.3 In general, should agents prefer their own harness's command monitoring? No

| Mechanism | Host sees it | Bounded | Survives provider death | Context kept | Cost to continue | Provider-neutral | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Synchronous command in the turn (Claude `Bash` ≤4 h, Muse `shell` ≤10 min) | Yes | Yes | No | Yes | 0 | Yes | **Default** up to the provider's ceiling |
| `sase monitor` with prepared completion (`-f`) | Yes | Yes | **Yes** | n/a (no successor on success) | **0 on green**; one recovery successor on red | Yes | **Default for final gates that may exceed the ceiling** |
| `sase monitor` with `--next`, chosen up front | Yes | Yes | Yes | Partial | ~3 min + re-orientation | Yes | Known-long mid-task work, external or unbounded waits |
| SASE-owned detach/wait/join on ToolRuns (future E2) | Yes | Yes | Yes | Yes while waiting in the turn; partial after handoff | Only when it escalates | Yes | **End state** |
| Harness background + in-turn polling | Partial | Partial | No | Yes | Polling model calls | No | Fallback only |
| Harness post-turn wake (Muse `bash`) | **No** | **No** | No | Yes | 0 | No | **Ban** |

**Rule:**

- Prefer synchronous execution in the turn, up to the provider's ceiling.
- Use SASE monitors for anything that can exceed that ceiling, or that waits on something
  external, and decide before the command starts.
- Never use harness waits that outlive the turn.

A harness primitive becomes acceptable only when it meets the single-turn decision's
reopen condition. None does today.

## 4. Requirement adjustments (explicit changes to your ask)

- **ADJ-1: ban the post-turn wait by removing the capability, not by "use monitors for
  background commands".**
  - Muse runs commands synchronously (`--enable-shell-tool`). Nothing outlives the turn
    except through a SASE handoff.
  - *Why:* Muse backgrounds by harness policy. 46% of what it backgrounds takes under a
    minute. And a background command can't be moved to a monitor without a restart.
- **ADJ-2: route by the provider's synchronous ceiling, decided up front.** For Muse
  (600 s):
  - **Final verification gate:** use prepared completion (`sase final prepare` with
    `bead_action: close`, then `sase monitor start -p verify -f <ref> -- sase tool run
    check`), not inline. It lands on green with no model turn. Inline it would be killed
    19% of the time with its output lost.
  - **Known-long mid-task commands** (`just test-scoped`, `just install`,
    `just test-wheel`, `rust-install`, full visual suites, `check-full`, CI, deploy,
    release, or rate-limit waits): `/sase_monitor` with `--next` from the start. Combine
    dependent steps into one monitored command.
  - **Everything else:** inline. Wrap commands of uncertain length as
    `timeout 540 <cmd> > <log> 2>&1; echo "exit=$?"; tail -n 80 <log>`, so a kill still
    leaves evidence behind.
  - **Never** cancel an in-flight command to move it to a monitor. This part applies to
    every provider; see the rewrite of `lint_and_test.md:54-56` in §7.
- **ADJ-3: enforce through the tool surface, and make routing mechanical where possible.**
  - The adapter removes the capability. The directive explains the rule. A wait guard
    catches violations.
  - Later, `sase tool run` itself enforces the routing. SASE already refuses raw agent runs
    of guarded recipes outside `sase tool run` (`decisions:guarded-recipes`), so this is a
    known pattern. Extending `sase tool run` to refuse a tool whose
    predicted duration exceeds the caller's ceiling takes routing out of model judgment.
  - *Why:* every agent in modes A and B was obeying an instruction.
- **ADJ-4: keep `decisions:single-turn-agents`, and add an adapter-normalization rule.**
  - Don't write the superseding record the prior report proposed.
  - Add a companion decision: *each provider adapter makes its harness conform to the
    single-turn contract. Where the CLI allows, it disables native background and wake
    primitives mechanically. It publishes the provider's synchronous ceiling. Otherwise it
    detects violations (guard, then fail).*
- **ADJ-5: cheaper monitor hops are part of the requirement.** Muse will start several
  times more monitors, so hop cost now matters:
  - hand the successor the starter's last reply and a tool-call digest;
  - reserve the family's slot for the successor;
  - stop gating dispatch on the starter runner's 77 s median post-kill bookkeeping.
- **ADJ-6: rescope the prior report's follow-ups.**
  - Drop the Muse pending-work ledger. Once Muse can't background, "still alive 120 s
    after the final declaration" means a hang again, so the watchdog is right for Muse.
  - Rescope `sase-16i` to "make Muse synchronous", or close it as superseded when that
    lands.
  - Keep `sase-12s` (provider-neutral incomplete-run classification), `sase-163` (Claude's
    leftover async tools; same principle), `sase-15o` (agy), and the stranded-wait guard.
  - Reprioritize the E2 detach/handoff/join work: Muse's 10-minute ceiling makes it the
    one change that removes Muse's hop cost.

## 5. Implementation options compared

| # | Option | Enforces the ban? | Effort | Main risk |
| --- | --- | --- | --- | --- |
| 1 | **The prior report's plan:** allow the wake; watchdog aware of pending work; ledger built from Muse's private events; per-provider contracts | No (embraces it) | Medium–high, recurring | Private log format; not durable; supersedes the decision; per-CLI re-verification |
| 2 | **Your plan, literally:** keep managed `bash`, tell Muse to use monitors | **No** (prompt only) | Low | Every command past 300 s is cancelled and restarted (mode B at scale), or the model ignores the rule |
| 3 | **Make Muse synchronous and route up front:** `--enable-shell-tool`, directive with the 600 s ceiling, prepared completion for gates, monitors for known-long work, wait guard | **Yes** | Low | 10-min kill with lost output when routing guesses wrong; the model's reluctance to block; "legacy" tool could be deprecated; more monitor hops |
| 4 | **Managed `bash` + in-turn polling enforced by hooks:** a preset forces `yield_time_ms=300000`; a Stop hook refuses to end the turn while work is pending and instructs `bash_input` polling; deny `cron_*`, `workflow`, `subagent_*` | Mostly | Medium | Writes into the user-owned `~/.config/muse/settings.json` (or a per-workspace `.muse/hooks.json`); hooks get a scrubbed env and must parse the private log to know what is pending; Muse's text says "do not poll", so this fights the harness; continuation cap 8; not durable. *Advantage:* no hop for 10–60 min commands, and in-turn polling already happens (346 `bash_input` waits on Sep 20–23) |
| 5 | **SASE-owned escalation without restart:** `sase tool run --detach` + `sase tool wait <id>` (each call under the provider ceiling) + `sase monitor start --join <id>`, i.e. roadmap E2 `-H` | Yes, for every provider | High | Roadmap work in the ToolRun control plane (sase-core boundary); adoption and orphan correctness |

**Recommended:** option 3 now, option 4 as the documented fallback if hop cost proves
unacceptable, and option 5 as the end state.

## 6. Limits and open questions

- **Whether 600 s is fixed.** I found no setting that raises it; that conclusion rests on
  the binary's settings schema and one 35-minute run. `TBH_EVAL_APPEND_DEVELOPER_PROMPT`
  and `--agents <JSON>` in `exec` are unverified. Either might be a cleaner way to deliver
  the directive, or to scope a tool allowlist per invocation without touching user
  settings.
- **Model quality with the legacy `shell` tool on real SASE tasks has not been measured.**
  The pilot should cover it.
- **Hop-count estimate.** The "up to ~29% of Muse sessions" figure counts sessions with at
  least one over-600 s command. The real number of successor hops depends on how many of
  those are final gates (no hop on green) and on verification pass rates, which I did not
  measure.
- **Comparing next turns** (wake vs successor) is only indicative: a successor's tokens
  include new work.
- **Scope:** athena and the sase project, Sep 20–23 (Sep 23 is a partial day).

## 7. Recommended solution

**Principle:** one wait contract for every provider. *Commands run synchronously within
the turn, up to the provider's published ceiling. Waiting across a turn happens only
through a host-owned handoff, chosen before the command starts. The final gate prefers
prepared completion, so passing work lands without another model turn.* Each provider
adapter makes its harness conform mechanically; the host never learns a harness's
private wait semantics.

**Phase 0 — canary (hours, no code).**

1. Set `SASE_MUSE_LARGE_ARGS="--enable-shell-tool"` and
   `SASE_MUSE_SMALL_ARGS="--enable-shell-tool"` in the environment SASE launches runners
   from on athena. Leave `SASE_LLM_*_ARGS` unset; they take precedence
   (`muse.py:401-412`).
2. Watch a handful of Muse runs for `tool timed out` results and for runs that end with a
   wait claim.
3. Without the directive, expect about one `sase tool run check` in five to be killed at
   10 minutes. That is why Phase 1 follows quickly, and why the canary should be short.

**Phase 1 — make it the Muse contract (sase repo; one small epic).**

1. **`muse.py`:** pass `--enable-shell-tool` by default, behind a config key or feature
   flag per `sase_flags.md`, so it can be rolled back to managed `bash`. Export the
   provider's synchronous ceiling (`SASE_PROVIDER_SYNC_CEILING_SECONDS=600`) to the agent
   environment for later routing.
2. **Muse directive,** a prompt prefix like `_AGY_PRINT_MODE_DIRECTIVE`. Proposed text:
   > SASE single-turn instructions for Muse Code: This session is exactly one turn;
   > nothing can wake you after you end it. Your `shell` tool runs each command
   > synchronously, but kills it at 10 minutes and discards all of its output. Blocking for
   > up to about 9 minutes is expected and correct. Decide before starting a command where
   > it runs:
   > (1) The final verification gate always goes through prepared completion:
   > `sase final prepare` with `bead_action: close`, then
   > `sase monitor start -p verify -f <ref> -- sase tool run check`. Passing work lands
   > without another turn.
   > (2) Commands that often exceed 10 minutes (`just test-scoped`, `just install`,
   > `just test-wheel`, `rust-install`, full visual suites, `check-full`, CI, deploy,
   > release, or rate-limit waits) go to `/sase_monitor` with `--next` up front; combine
   > dependent steps into one monitored command.
   > (3) Run everything else inline. Wrap anything of uncertain length as
   > `timeout 540 <cmd> > <log> 2>&1; echo "exit=$?"; tail -n 80 <log>`.
   > Never detach or background a command (`&`, `nohup`, `setsid`), never cancel or rerun
   > an in-flight command to move it to a monitor, and never end your turn to wait.
3. **Muse stranded-wait guard.** Port Claude's `_WAIT_SIGNAL_RE` and
   `_WAIT_CONTINUATION_NUDGE`:
   - trigger on a clean exit whose final text claims a wait;
   - re-invoke through Muse's reconstructed-context path, up to 2 times, then raise
     `LLMInvocationError`;
   - this also catches `nohup … &` workarounds.
4. **Parser and docs.**
   - `_tool_call_muse.py:67` and `:301` need a `shell` display name and `command`
     extraction, or Muse tool calls will show raw in the TUI.
   - Record a `timeout` outcome as a distinct tool-call status.
   - Update the Muse sections of `docs/llms.md`.
5. **CLI-update smoke test** in `sase agent-cli update muse`:
   - check that `shell` is active and `bash` is absent;
   - check that a 15 s command blocks;
   - fail loudly if a future release drops the legacy tool, and fall back to option 4.

**Phase 1 — skill and memory edits (all through `/sase_memory_write`).**

- **`sase_monitor.md`:**
  - Keep "provider-native background execution does not work in SASE"; after
    normalization it's true for every provider.
  - Add the up-front routing rule, the never-cancel-in-flight rule, and each provider's
    ceiling.
  - Promote prepared completion from a footnote in `sase_final.md` to the recommended way
    to verify long gates.
- **`lint_and_test.md:54-56`:** replace "hand it to a monitor … whenever it is taking a
  long time" with the up-front rule. Stop piping verification through `| tail`.
- **`sase_final.md:11` and core memory `sase.md:77`:**
  - Remove "I will wait" responses from the list of valid endings. A turn ends with a
    final answer, an incomplete status, or a handoff.
  - Add: *the declaration is your last action.*
- **New decision record:** "Provider adapters normalize harnesses to the single-turn
  contract" (ADJ-4), linked from `decisions:single-turn-agents`. Do not supersede that
  record.

**Phase 2 — make routing mechanical and hops cheaper.**

- **Provider-aware `sase tool run`.** When `SASE_PROVIDER_SYNC_CEILING_SECONDS` is set
  and the tool's recorded duration distribution (the control plane's prediction corpus)
  puts P(duration > ceiling) above a threshold, refuse before starting. Print the exact
  `sase monitor start -p verify …` (or prepared-completion) command to run instead. This
  follows the guarded-recipes pattern. Put the prediction logic in sase-core, per the Rust
  boundary rule.
- **Cheaper hops (ADJ-5):**
  - the successor prompt gets the starter's last reply and a tool-call digest;
  - the family's slot is reserved across the hop (two ~30-min re-queues in this window);
  - dispatch is no longer gated on the starter runner's post-kill bookkeeping (median
    77 s, up to 415 s).
- **Beads (ADJ-6):**
  - Rescope or close `sase-16i`, and drop the pending-work ledger.
  - Land `sase-12s` as the provider-neutral net: an assigned bead still open, plus a wait
    claim or no declaration, is recorded as *incomplete*, not success.
  - Add a SASE `run.toolset` preset only if Muse's remaining async tools show up in
    telemetry.

**Phase 3 — the end state: SASE owns "inline, then escalate".**

The one thing Muse's harness did better than SASE is not forcing an up-front guess. Build
that into the `sase tool` roadmap's E2, provider-neutral and durable:

- `sase tool run --detach` returns a ToolRun id;
- `sase tool wait <id>` blocks for less than the provider's ceiling and returns status
  and an output tail, so an agent can wait in the turn across several calls;
- `sase monitor start --join <id>` hands a *running* ToolRun to a monitor without
  restarting it.

With that in place, Muse's 10-minute ceiling stops mattering, cancel-and-restart becomes
impossible, and this report's 155 over-600 s commands plus the prior report's 26
cancellations are the evidence for reopening the roadmap's deferred single-flight joining.

**How to tell it worked** (same artifact sources as the Sep 20–23 baseline):

| Metric | Baseline | Target |
| --- | ---: | ---: |
| Muse teardown-watchdog kills | 17 | 0 |
| Muse post-turn waits (wakes) | 104 | 0 |
| Muse `bash_input` cancel/terminate calls | 46+ | 0 (tool removed) |
| Muse runs whose final reply claims a wait | ≥12 (modes A + C) | 0 |
| Muse `shell` 600 s kills (routing misses) | n/a | < 1 per day, trending to 0 once Phase 2 lands |
| Final gates landed through prepared completion | 0 ever | most Muse final gates |
| Command end → successor's first tool call | median 176 s, p90 709 s | median < 90 s, no 30-min slot re-queues |
| Beads left `in_progress` or hand-closed after a lost wait | 4 open + 5 hand-closed (prior report) | 0 |

## Appendix — evidence index

- **Muse experiments.** These are in temporary directories and will be deleted.
  - `/tmp/musetest/expC`: a hook set `yield_time_ms: 3600000`, and the command still
    backgrounded at 300.1 s.
  - `/tmp/musetest/expF`: `--enable-shell-tool`, 330 s synchronous.
  - `/tmp/musetest/expL/first`: the model refused a 35-minute block.
  - `/tmp/musetest/expL`: explicit authorization, then the `shell` tool timed out at
    600.1 s with only `tool timed out`. Session
    `01a0cfb4-4969-7452-b6e0-ff0285ec0b13`.
  - `/tmp/musetest/expT`: echo-provider settings probes.
- **Telemetry** (scripts in `/tmp/wait_research/`, also temporary):
  - 361 Muse `session.jsonl` files (Sep 20–23);
  - `ace-run/202609/{20..23}` run dirs;
  - 17 `provider_teardown_stall.json` files;
  - `sase monitor list --all -j` (1,344 monitors, 0 with `completion_ref`).
- **Code** (sase `02cd6b69e`):
  - `src/sase/llm_provider/muse.py`: `:377-412` (argv, extra-args hatch), `:418` (no
    directive), `:502` (env), `:519` (watchdog).
  - `src/sase/llm_provider/claude.py`: `:44-110` (directive, nudge, wait regex,
    classifier), `:426-427`, `:531`.
  - `src/sase/llm_provider/agy.py:68-72`.
  - `src/sase/llm_provider/_tool_call_muse.py:67`, `:301`.
  - `src/sase/llm_provider/_subprocess_plain.py:34`, `:104`.
  - `src/sase/main/parser_tool.py:56-105`.
  - `docs/monitors.md` ("prepared completion" and the `-p verify` profile).
  - `src/sase/finalizers/declaration_manifest.py:474` (`bead_action` keep/close).
- **Skills and memory:**
  - `src/sase/xprompts/skills/sase_monitor.md:1-24`
  - `src/sase/xprompts/skills/sase_final.md:11`, `:51-62`
  - `sase/memory/lint_and_test.md:54-56`
  - `sase/memory/sase.md:77`
  - `decisions:single-turn-agents`
- **Beads** (all `ready`): `sase-16i`, `sase-163`, `sase-12s`, `sase-12r`, `sase-15o`.
