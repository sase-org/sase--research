# Why SASE Agents Die After Long Commands: The Host Has No Model Of Provider Waits

Date: 2026-09-22. Lead-researcher consolidation of three independent reports (`research.29.*`),
plus new verification against sase `d3002aba1`, Muse Code `1.3.0-R3401.1` (installed Sep 17
22:41), agy `1.2.8`, Claude Code `2.1.280`, and run telemetry on athena for Sep 14–22.

| Dependency | Preserved report | Immutable snapshot | Main contribution |
| --- | --- | --- | --- |
| `research.29.cld` | [cld](provider_wait_contract_early_exits__cld.md) | `file:explicit:879bf00a26a9ded64d4a7a1a` | Found that `muse exec` wakes the model after its turn ends, and that SASE's teardown watchdog kills agents waiting for that wake; the Muse mid-turn delivery race; the "wait contract" framing |
| `research.29.mus` | [mus](provider_wait_contract_early_exits__mus.md) | `file:explicit:d54caf11de8c1286297f4947` | Provider guard matrix; "mechanism, not the model, decides when a wait becomes a handoff"; the success-on-clean-tree gap |
| `research.29.gem` | [gem](provider_wait_contract_early_exits__gem.md) | `file:explicit:87b1d16e3e6c6642ed5ed3a4` | The agy failure chain and the flaw in its text classifier; `sase monitor start` kill mechanics; `\| tail` hiding output |

I also re-checked yesterday's consolidated report
(`research:202609/agent_long_command_early_exits/agent_long_command_early_exits.md`). It did
finish; its conclusions were correct for Sep 14–19 but are out of date for the current fleet
(§4). No predecessor chat transcripts were read.

## Bottom line

**Your hypothesis describes the symptom correctly, but for the agents failing today the cause is
the reverse of what you suspected.** The agents dying now are not confused about headless mode.
They are Muse agents doing what their harness tells them to do, which is to end the turn and
wait. **SASE is the component that misunderstands headless mode.**

- **The fleet changed.** Since Sep 20, SASE agents on athena have been almost entirely Claude
  and Muse. agy ran 8 times, Codex once, and Grok not at all.
- **Muse can wait.** Muse Code 1.3.0's `muse exec` keeps the process alive after the model
  ends its turn. When a background command finishes, Muse wakes the model, and it sends a
  reminder every 30 minutes while the command runs. Muse's own tool text says a
  backgrounded command's output *"wakes you even after you end the turn."* I replayed one such session end to end:
  `sase-14n.11` waited 1h30m through three reminders, was woken, and closed its bead.
- **SASE assumes no agent can wait.** Its rule is universal: "agents are single-turn; native
  background features silently no-op." That rule is built into its prompts, skills, and host
  mechanisms. For Muse it is false, and three SASE behaviors built on it destroy Muse waits:

| # | What you see | Mechanism (verified) | Sep 20–22 |
| --- | --- | --- | --- |
| **A** | Agent says "waiting on `just check`", then dies about 2 min later; run shows SUCCESS | `/sase_final` makes the agent **declare before an "I will wait" reply**. The Sep 20 teardown watchdog (`68d9e0f65`) **kills the provider 120 s after any declaration** and never checks whether background work is still pending | **8 of 9** watchdog firings killed a waiting agent. All 9 were Muse. The latest was `sase-16e.5` today at ~13:04 EDT |
| **B** | A long command runs, the agent starts "some monitor" and dies, then a new agent re-runs the command from zero | A Muse overdue reminder ("running 30m… you may inspect it or terminate it") wakes the model. The model reads `/sase_monitor`, which says to hand off "whenever it is taking a long time". It cancels the in-flight check and runs `sase monitor start`, which kills the agent by design | **26 in-flight commands cancelled across 21 Muse runs**. 15 of those runs had read `/sase_monitor` first. 19 of the cancelled commands were verification or build commands |
| **C** | Agent says "still running, I'll report when it lands" and exits cleanly; run shows completed | **Muse delivery race.** The command finishes *during* the turn, so Muse drains its completion notice into that same turn. The model ignores it and ends the turn claiming to wait. Nothing is pending any more, so Muse exits and no wake ever comes. SASE has no Muse wait guard | 4 runs, all with the same `deferred_token_held` signature |
| **D** | agy: "waiting for `sase doctor`…", recorded SUCCESS, bead stranded | agy moves anything longer than 10 s to the background, tells the model to end the turn, and kills background tasks when print mode exits. SASE's agy guard is disabled by a version allowlist (`sase-15o`), and its text fallback misses these replies | 2 (`sase-14t.3`, `research.24.gem`) out of about 8 agy runs |
| **E** | Claude | Native background tools were fixed on Sep 15 (`bdda3bdf1`); Claude blocks in the foreground for up to 4 h | **0**. My own scan found no native background or scheduling tool use from Sep 15 to 22; the last uses were all on Sep 14 |

**Root cause.** SASE treats "the model stopped talking" as if it meant "the provider process is
over". It has no per-run, mechanical record of **pending work**, so every layer guesses
differently:

- the skills tell agents to declare before waiting and to switch to a monitor mid-flight;
- the watchdog treats a declaration as the end of the turn;
- the success test treats "the process exited" as "the task is done".

Each rule is reasonable for Claude. Together they are lethal for Muse. The watchdog was itself
built to fix a Muse "hang" that looks like the same harness wait, misread as a leaked pipe (§3,
R1).

**Recommendation (§5).**

1. **Today:** fix the conflicting instructions.
2. **This week:** make the watchdog aware of pending work, and give Muse a guard against
   stranded waits.
3. **Next:** give each provider an explicit *wait contract*, backed by a host-owned
   pending-work ledger, and a provider-neutral "incomplete" classification.
4. **Then:** make handoff lossless through the `sase tool` roadmap's E2 work, now that this
   audit supplies the evidence that roadmap was waiting for.

More "you are headless" prompt text is the wrong fix. Every agent that failed in categories A
and B was following an explicit instruction.

## 1. Method

| Source | What I checked myself |
| --- | --- |
| `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/{15..22}` | Scripted scan of 1,561 run dirs: provider, tool names, trailing replies, declarations, `provider_teardown_stall.json`, and Muse `bash_input` cancellations |
| `~/.local/share/muse/sessions/2026/09/{20,21,22}` | Replayed run starts, run terminals, inbox queue/drain events, and delivery anomalies for 9 sessions (`c9dcd3ee`, `429e3f38`, `66634b4d`, `f482f2f0`, `c7e17370`, `eefe0f8b`, `bb014b66`, `97dbdd11`, `c2e8b6d0`), plus a pass over the whole corpus for `background_running` events |
| Binaries | Muse 1.3.0 tool text; agy 1.2.8 version; Claude 2.1.280 environment switches |
| sase source | `_subprocess_plain.py` watchdog, `claude.py` directive and guard, `muse.py` (no directive, no guard), `agy.py` classifier, `declaration_store.py`, `declaration_recovery.py`, skill sources `sase_final.md` and `sase_monitor.md` |
| Memory and plans | `decisions:single-turn-agents`, `lint_and_test.md`, `plan:202609/provider_teardown_stall_watchdog.md`, `plan:202609/tool_e15_enforced_adoption.md`, `research:202609/sase_tool_epic_roadmap/…` |
| `sase monitor list --all -j`, `sase bead read` | Monitor volume and outcomes since Sep 20; current status of every bead that a failed run touched |

## 2. Failure modes in detail

### 2.1 A — The watchdog reaps agents that are legitimately waiting

The loop in `src/sase/llm_provider/_subprocess_plain.py` (`start_completion_watchdog`) checks
only two things: whether the provider process is still alive, and whether a new
`final_submission.json` has appeared. Once 120 s have passed since a declaration, it calls
`_tear_down_stalled_provider`. That sends SIGTERM, then SIGKILL, and the runner then reports
**a clean exit** with the reply intact.

Meanwhile, `/sase_final` (`src/sase/xprompts/skills/sase_final.md:11`), echoed by core memory
in `sase/memory/sase.md:77`, says the declaration *"is mandatory for final answers,
incomplete-status responses, **"I will wait" responses**, and replies that intend to resume in a
later turn."* A Muse agent that obeys both its harness and this skill therefore:

1. declares a commit with the bead kept open;
2. ends the turn to wait for its wake;
3. is killed 120 s later, along with the verification it was waiting for.

All nine firings in September (every `provider_teardown_stall.json` in `202609/`):

| Run | Agent | Reply when killed | Bead now |
| --- | --- | --- | --- |
| `20/20260920171045` | `sase-142.5.2` | "`just check` is still running. Holding the bead open until verification lands" | **IN_PROGRESS** |
| `20/20260920171046` | `sase-142.5.3` | "the recorded `check` gate and one bead note are running. On their delivery I will…" | **IN_PROGRESS** |
| `20/20260920171610` | `sase-14n.4` | "still running and will wake me, after which I'll close the bead" | closed by you: *"finished its work. It just didn't complete verification"* |
| `20/20260920171615` | `sase-14n.9` | "waiting on the in-flight recorded `sase tool run check`" | closed by you, same reason |
| `21/20260921062759` | `sase-157.7` | "now waiting on the full `just check` gate" | closed |
| `21/20260921153305` | `sase-15p.2` | "Waiting on the `just install` build to run tests" | closed by you, same reason |
| `22/20260922104606` | `0pb--1` | "Still in flight: the full `check` lane and the visual check-only rerun" | n/a |
| `22/20260922121459` | `sase-16e.5` | "the full `just check` gate is still running… Waiting on verification before closing" | **IN_PROGRESS** (new since the cld report; Muse logs `background cancelled` at 17:04Z) |
| `21/20260921062756` | `sase-157.3` | work finished and bead closed | closed normally. Muse was in its own *"end-of-turn reminder wait"*, so this reap was harmless |

The damage, per the bead data:

- Three beads are still `in_progress`.
- You closed at least five by hand with the same reason: `sase-14n.4`, `sase-14n.9`,
  `sase-15p.2`, `sase-11y.11.4`, and `sase-165.7`. (`sase-11y.11.4` and `sase-165.7` were lost
  to mode C, not to the watchdog.)
- Work landed unverified, because the commit finalizer committed the declared tree and the
  gate that would have checked it was killed.

### 2.2 B — "Long command, then a monitor, then dead": cancel-and-restart on Muse

This is the pattern you described, and none of the three reports quantified it for the current
fleet. Muse's 30-minute overdue notice wakes the model and explicitly allows it to *"inspect it
or terminate it with bash_input now."* `lint_and_test.md` says *"`just check` may be run
inline, but hand it to a monitor the same way whenever it is taking a long time."* The
`/sase_monitor` description says provider-native background execution *"does not work in
SASE"*, which is false for Muse. The woken model combines these. Two verified timelines:

- `sase-14n.14--plan` (session `eefe0f8b`):
  - 22:33Z: first reminder; the model replies "still running with no output yet (its output is
    piped through `tail`)".
  - 23:03Z: second reminder.
  - 23:04:38Z: reads `/sase_monitor`.
  - 23:04:54Z: `bash_input` cancels the roughly 61-minute-old `sase tool run check`.
  - 23:05:46Z: the turn is *"cancelled after tool result reconciliation"*, meaning
    `sase monitor start` killed the runner. The follow-up monitor then re-ran the check from
    zero.
- `sase-11y.10.1.3.1.2--plan` (session `bb014b66`): the same sequence on its second reminder.
  It cancelled `just test-scoped` and also ran `pkill -f pytest`.

Across Sep 20–22 there were 26 in-flight cancellations in 21 Muse runs, 15 of which read `/sase_monitor` just before cancelling:

| Cancelled command | Count |
| --- | ---: |
| `sase tool run check` | 10 |
| `just install` | 4 |
| `just test-scoped` | 3 |
| `just test-visual` | 2 |
| others (lint, fmt, `sase final context`, probes) | 7 |

This is less severe than A, because a follow-up agent does continue. But it throws away up to
an hour of wall time per hop on a host already running at load averages of 18–85. It is also
the direct cause of the "it ran for ages, some monitor started, it died" impression. By
contrast, monitors are now uncommon: 23 non-epic monitors from Sep 20 to 22, against 84 on Sep
18 alone when Grok and Codex were running.

### 2.3 C — The Muse mid-turn delivery race

I verified all four sessions. In each one, the background command finished while the model was
still mid-turn:

1. Muse queued the completion and logged `inbox_delivery_anomaly: deferred_token_held`.
2. It then drained the completion into the running turn.
3. The model ended the turn claiming to wait.
4. The session ended with `exit_reason: clean`.

In `66634b4d` (`0p5--code`), the drained notice reads `Background terminal completed …
command: sase tool run check 2>&1 | tail -n 25 … exit_code: 0`. Twenty seconds later the model
wrote *"the full verification gate is still running; I'll report the result when it lands."*

The `| tail -n 25` output was a list of pytest durations with no pass/fail line, which plausibly
helped the model misread it. The same race also happens harmlessly, when the drain lands just
before a real final turn (`c2e8b6d0`).

For Muse this state can be detected mechanically. `muse exec` exits cleanly only when nothing
is pending, so *clean exit + a final reply claiming to wait* means the wait is stranded, every
time.

### 2.4 D — agy (low volume, still unguarded)

This mode is confirmed as described by gem and yesterday's report:

- `_SUPPORTED_AGY_TRAJECTORY_VERSIONS = frozenset({"1.0.10"})`, while agy 1.2.8 is installed
  (`sase-15o`, still `ready`).
- `_looks_like_no_progress` returns true only when the text is `dominated_by_intentions and
  (has_wait_signal or low_substance)`, so a long, explanatory wait reply passes as progress.
- `sase-14t.3` is still `IN_PROGRESS`.

gem's own run survived only by ignoring agy's "end the turn" advice and polling
`manage_task`. cld points out that agy 1.2.8's prompt example passes `Blocking:true`; whether
the model-facing schema exposes that is untested.

### 2.5 E — Claude (clean, with latent gaps)

Claude tool calls, Sep 14–22:

- `ScheduleWakeup` 7, `TaskOutput` 5, `TaskStop` 3, `Monitor` 1, all on **Sep 14**;
- **zero** from Sep 15 to 22.

The latent gaps are tracked in bead `sase-163`. Print mode still offers `Monitor`,
`CronCreate`/`CronDelete`/`CronList`, `RemoteTrigger`, `PushNotification`, and `Workflow`; this
lead session sees all of them. `sase-163`'s critique note also says `claude -p` stays alive up
to `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` (10 min) for background subagents and workflows. The
switch exists in the 2.1.280 binary, and `CLAUDE_CODE_DISABLE_WORKFLOWS` and
`CLAUDE_CODE_DISABLE_CRON` are present too.

So Claude also has a small, bounded wait window, and the same watchdog would cut it off.

## 3. Root causes

**R1. SASE's single-turn rule conflates *provider process* with *model turn*, and SASE then
built host mechanisms on the false half of it.**

`decisions:single-turn-agents` rests on this premise: *"every [native background primitive]
silently no-ops here: the runner captures the turn and exits, so there is no process left to
resume into."* That is true of the SASE runner, but not of `muse exec`, which keeps the process
alive and resumes the model inside the same run. That in-process wait holds the same workspace
claim and runner slot as a 45-minute foreground `just check` on Claude, which SASE already
accepts.

The watchdog's own motivating incident (`plan:202609/provider_teardown_stall_watchdog.md`,
`research.a.cdx` on Sep 20) was a **Muse** run. In it, `muse exec` stayed alive holding pipes
from a shell command that its Bash tool "returned in 7 ms" and did not reap. That fits a
Muse-managed background session that would never finish (a listener script with no exit),
diagnosed as a leaked pipe. I could not find that session's log to confirm it.

Either way, a check that only asks "is the process alive" cannot tell three states apart:

- the harness is waiting for a command that will finish;
- the harness is waiting for a command that never will;
- a genuinely leaked process is holding the pipe.

**R2. SASE's own instructions contradict each other, and agents follow them.** There are three
conflicts:

- "Declare before an 'I will wait' reply" (`/sase_final`) conflicts with "kill 120 s after a
  declaration" (the watchdog).
- "Hand it to a monitor whenever it is taking a long time" (`lint_and_test.md`) conflicts with a
  handoff primitive that can only start a *new* command.
- "Native background tools don't work in SASE" (`/sase_monitor`) conflicts with Muse's harness,
  which says they do.

Muse agents get no SASE directive at all (`muse.py` builds no preamble), so no one tells them
which instruction wins.

**R3. The host has no mechanical notion of pending work or of an unfinished task.**

- A run is `completed` when the provider exits and the finalizers pass.
- A declaration is required only when a repository is dirty
  (`declaration_store.py:217`, `submission_required=bool(repository_obligations)`).
- The one recovery turn (`declaration_recovery.py:131`) says *"Do not perform unrelated
  work… submit one valid declaration… return briefly"*. It collects a declaration even when
  the run's completed verification result is sitting in the transcript.

Nothing ever records "this run ended while waiting for X".

**Contributing factors (real, but not the trigger):**

- Verification wall time: `just check` p90 is 34–45 min under load.
- The Muse foreground window is 10 s by default and 300 s at most. SASE never sets
  `yield_time_ms`, so even bookkeeping commands (`sase bead note/close/show`, `sase final
  context`, `sase monitor start` itself) get pushed into the background under load.
- `| tail -n N` hides all progress until the command exits. That invites "no output yet →
  cancel", and in mode C it hid the pass/fail line.

## 4. Where the reports disagree, and the resolution

| Claim | Source | Verdict |
| --- | --- | --- |
| Muse "yields at 300 s, then polls with `bash_input`", has no guard, and loses work only in theory | mus, gem, yesterday's report | **Out of date for Muse 1.3.0 (installed Sep 17).** Muse's tool text forbids polling with `bash_input` and promises a post-turn wake, and session logs show the wakes happening. Muse is now the *main* source of losses (A, B, C), not a latent one |
| Silent false success from a headless misunderstanding is the dominant active failure | mus, gem | **Only for agy**, about 2 runs in 3 days. Muse's losses come from SASE's watchdog, SASE's instructions, and one harness race, not from a misunderstanding |
| Muse is the only provider losing work; the fix is a per-provider wait contract | cld | **Confirmed.** I found a 9th firing after cld wrote (`sase-16e.5`). cld treated designed monitor handoffs as minor (about 21 monitors); it did not count the 26 Muse in-flight cancellations that come before them (mode B) |
| `sase-165.6.f0--code` has been "completely hung" for 80+ min behind `\| tail` | gem | **Wrong outcome.** It was in Muse's wait-for-wake state. It was woken, finished, and its declared work became HEAD `d3002aba1`. `\| tail` hides progress but did not lose work here |
| gem's 499-run table (60 completed / 360 "failed") | gem | **Not usable.** Its "failed" means "no `done.json`", which includes dismissed and in-flight runs |
| Monitor cascades (`sase-m4.land` 9 hops, `sase-126.4` 15 hops) are the main visible dying | gem, yesterday | **Historical** (Codex/Grok era, Sep 14–19). Since Sep 20, cancel-and-restart happens mostly through Muse wakes (§2.2) |
| Fix by requiring a declaration whenever a bead is assigned | mus, gem, yesterday | **Necessary but not sufficient.** It catches D. Every A victim *did* declare; the test must also look at "bead still open + reply claims a wait + no handoff" |
| Build detached, joinable ToolRuns plus `--handoff-after` first | mus, gem, yesterday | **Right destination, wrong first step.** Nothing in A or C needs it. It is the durable fix for B, and it belongs in the `sase tool` roadmap's E2 (§5 Step 3) |
| `sase final submit` should refuse while background work is pending | cld | **Prefer a warning plus a watchdog exemption.** A checkpoint declaration before a wait is useful (it protects the work if the wait is cut short), and later declarations already reset the watchdog |
| `sase bead` commands were backgrounded 91 times | cld | **Plausible.** SASE's tool-call stream shows only 3 (it keeps truncated previews), but a pass over the raw Muse session logs puts bead commands at about a quarter of all `background_running` mentions |

## 5. Recommended solution

**Principle: the host, not the model, must know whether a run still has work in flight. Every
policy reads that one fact instead of guessing: the watchdog, the success test, the handoff
guidance, and the TUI state. Each provider's wait semantics are declared once, and the true
guidance is derived from them.**

This refines `decisions:single-turn-agents` rather than abandoning it. The invariant that
matters is: *one SASE run = one provider process and one workspace claim, and nothing survives
its exit.* How many model turns happen inside that process is a per-provider property. A wait
is legitimate only when the host can see it and put a bound on it.

### Step 0 — today (memory and skill edits, through `/sase_memory_write`)

1. **`/sase_final` + core memory `sase.md`.** Replace the "I will wait" clause with: *the
   declaration means "my work is done", not "my turn is ending". If your harness keeps the
   session alive and wakes you when a background command finishes (Muse), you may submit a
   checkpoint declaration, but you must declare again in the turn that finishes the work. If
   your harness cannot wake you, you cannot wait: finish inline or hand off with
   `/sase_monitor`.*
2. **`lint_and_test.md` + `/sase_monitor`.**
   - Delete "hand it to a monitor whenever it is taking a long time".
   - Add: *choose inline or monitor **before** starting; never cancel an in-flight
     verification or build to restart it under a monitor; an overdue reminder is not a
     reason to terminate verification.*
   - Stop piping verification through `| tail`. Correct the `/sase_monitor` description so it
     no longer claims native background execution never works.
3. **Optional bridge.** Set `SASE_PROVIDER_TEARDOWN_GRACE_SECONDS` to 2–3 h in the runner
   environment until Step 1 lands.
   - It keeps a bound on true hangs while letting the median wait (about 9 min, per cld)
     finish.
   - Setting it to `0` disables the guard entirely. That trades 8 kills in 3 days for the
     original hang, which occurred once.

### Step 1 — this week (small, independent code fixes)

1. **Make the watchdog aware of pending work** (filed as bug **`sase-16i`**; `_subprocess_plain.py`).
   - Have the Muse stream parser (`_tool_call_muse.py`, which already sees
     `execution_state: background_running` and the `Background terminal
     completed/failed/cancelled` notices) keep a set of outstanding background tasks, as
     `ClaudeTurnWaitState.outstanding_background_tasks` already does for Claude.
   - Write the set to a per-run `provider_pending_work.json`.
   - Reap only when **a declaration is current, nothing is pending, and the stream has been
     idle** for the grace period.
   - While work is pending, apply a separate long ceiling. When that ceiling fires, record
     the run as `incomplete`, not as a clean exit.
   - Show a distinct TUI state (e.g. `WAITING ON BG`) so a waiting agent looks different
     from a hung one.
2. **Guard Muse against stranded waits** (`muse.py`), reusing Claude's pattern
   (`claude.py`: `_WAIT_SIGNAL_RE` plus a bounded nudge, then a loud failure).
   - Trigger: `muse exec` exits cleanly **and** the final text matches the wait pattern.
   - Continue through Muse's existing reconstructed-context path, with a nudge that states
     the facts: *"the command you were waiting on finished at HH:MM with exit N; nothing is
     running; finish the task."*
3. **Declaration recovery.** When the last reply claimed a wait and the waited-on result is
   already available, the recovery prompt should allow finishing the task, not only
   declaring.
4. **Add a Muse preamble** (Muse has no system-prompt flag, so use a prompt prefix, as agy
   already does).
   - It should state Muse's true contract: waiting is fine; do not cancel verification to
     move it to a monitor; pass `yield_time_ms: 300000` for verification and for slow SASE
     CLI calls.
   - Unlike "you are headless", this text agrees with the harness.
5. **Land `sase-163`** for Claude: disallow `Monitor`, the `Cron*` tools, `RemoteTrigger`, and
   `Workflow` (or set `CLAUDE_CODE_DISABLE_WORKFLOWS`/`CLAUDE_CODE_DISABLE_CRON`), and refuse
   cross-session inbound messages.

### Step 2 — make the contract explicit (the durable structure)

- **Record a wait contract per provider adapter:**

  | Provider | Foreground window | Post-turn wake | Host policy derived from it |
  | --- | --- | --- | --- |
  | claude | 4 h | none (a bounded 10 min only for subagents and workflows, disabled by `sase-163`) | Block inline; wait reply → nudge, then fail |
  | muse | 10 s default, 300 s max | **yes, in-process, with reminders every 30 min** | Don't reap while work is pending; checkpoint and final declarations; stranded wait → nudge |
  | agy | ≤10 s | none; tasks are killed at exit | Must not wait; keep polling or hand off up front; fix `sase-15o` and the classifier |
  | codex / grok / others | in-turn polling | none | Poll or hand off; detect a session still open at turn end |

  Generate the directive text, the disallowed tools, the watchdog policy, the wait classifier,
  and the provider-specific lines of `/sase_final`, `/sase_monitor`, and `lint_and_test` from
  this record. Skills are already deployed per provider (for example
  `~/.config/muse/skills/sase_monitor/SKILL.md`). Today these statements live in five places
  and disagree.
- **Classify incomplete runs the same way for every provider**, in `sase-core` alongside the
  finalizer requirement logic, per the Rust boundary rule.
  - A run is **incomplete** when it ends with no mechanical handoff (monitor, plan, pipe,
    questions, gate) and either of these holds:
    - an assigned bead is still open **and** the final reply claims a wait;
    - an assigned bead or report obligation exists **and** there is no declaration.
  - Show it in `done.json` and the TUI, and send it through the continuation path.
  - Existing task `sase-12s` already tracks the "assigned bead still open → recorded as
    success" half of this rule; widen it rather than filing a parallel task.
  - In this window, the rule catches A, C, and D, and nothing else I found.
- **Write a new decision record** that supersedes `decisions:single-turn-agents`, with the
  invariant stated above and a link back to the old record. This is a memory change and goes
  through `/sase_memory_write`.

### Step 3 — lossless handoff and fewer waits

- **Build handoff into the `sase tool` roadmap's E2** (`-H`, durable handoff execution). Do
  not build a separate mechanism.
  - Starting a verify run under `-H` from the outset removes the mid-flight decision
    entirely.
  - The roadmap defers "single-flight joining" for lack of evidence (*"zero repeated request
    fingerprints in 14 days on apollo"*). That is the wrong measure: a cancel-and-restart
    never shows up as a repeated fingerprint, because the first run is killed before the
    second starts.
  - This audit's 26 in-flight cancellations in 3 days are the evidence to reopen
    adoption/joining of an in-flight ToolRun.
  - `sase-16b` (E1.5) is a prerequisite: today a SIGKILL of the caller orphans the child of
    `sase tool run`.
- **Reduce how often any of this matters:**
  - faster verification (E1.5/E2 and a shared prebuilt `sase_core_rs`);
  - lower SASE CLI latency under load, so bookkeeping stays under Muse's 10 s yield;
  - a governor on verify→fix→re-verify loops (escalate to a gate after 3 failed
    verification hops).

### Rejected

- **More "you are headless" prompt text.** It is false for Muse, and the A/B victims were
  obeying explicit instructions.
- **Forcing Muse to poll.** Muse's harness forbids it, and fighting a harness with prompts is
  what already failed on agy.
- **Killing faster after the declaration.** It throws away work the harness was about to
  finish, and it forbids a wait mechanism that worked in about 31 sessions in 3 days, per cld.
- **Making the host refuse checkpoint declarations.** A checkpoint protects the work if the
  wait is cut short, and the watchdog already re-arms on each new declaration.

## 6. How to tell it worked

| Metric (same artifact sources) | Sep 20–22 baseline | Target |
| --- | ---: | ---: |
| `provider_teardown_stall.json` written while background work was pending | 8 | 0 |
| Muse `bash_input` cancellations of in-flight verify or build commands | 19 (26 total) | ≈0 |
| Runs recorded `completed`/SUCCESS whose final reply claims a wait | ≥12 (A + C) | 0 (classified `incomplete`, then continued) |
| Beads left `in_progress` or hand-closed after a killed or stranded wait | 4 open (3 Muse, plus the agy bead `sase-14t.3`) + 5 hand-closed | 0 |
| Muse waits completed by a post-turn wake | about 31 sessions (cld) | ≥ baseline: this is the path to preserve |
| agy runs with structural no-progress detection active | 0 | all |

## 7. Limits and open questions

- The scope is athena and the sase project, Sep 14–22. Remote machines and other projects were
  not examined.
- I did not confirm that the watchdog's motivating incident was a Muse-managed background
  session, because its session log was not found.
- These are cheap experiments that could remove backgrounding outright, and none has been run:
  - Can Muse's default yield or its 300 s ceiling be configured? `muse exec --help` shows no
    knob. `--enable-shell-tool` is untested.
  - Does agy 1.2.8 expose `Blocking` to the model?
  - Do Grok's `toolset.bash.*` settings allow a per-run override?
- Holding a runner slot during an in-process wait has a capacity cost that has not been
  measured. cld bounds it at about 602 min of post-turn waiting in 3 days. If slots get tight,
  a host threshold (in-process wait below N minutes, `-H` monitor above it) is the knob.
- **Follow-ups.**
  - Filed: `sase-16i` (the watchdog bug, Step 1.1; linked to `sase-12s` and `sase-163`).
  - Proposed, not filed: the Muse stranded-wait guard (Step 1.2); the skill and memory
    conflict (Step 0.1–0.2, which goes through `/sase_memory_write`).
  - Existing and related: `sase-15o`, `sase-163`, `sase-12s`, `sase-12r` (a monitor start
    lost when the turn ends mid-start; Muse also backgrounds `sase monitor start` itself).

## Appendix — evidence index

- **Watchdog firings:** `ace-run/202609/{20/20260920171045, 20/20260920171046,
  20/20260920171610, 20/20260920171615, 21/20260921062756, 21/20260921062759,
  21/20260921153305, 22/20260922104606, 22/20260922121459}/provider_teardown_stall.json`
- **Muse wake working:** session `c9dcd3ee` (`sase-14n.11`; turn ends 22:14Z → reminders at 22:39Z,
  23:09Z, 23:39Z → completion at 23:41Z → bead closed 23:44Z)
- **Cancel-and-restart:** runs `20/20260920171620` (session `eefe0f8b`) and
  `20/20260920212106` (`bb014b66`), plus 19 other Muse runs with `bash_input`
  `terminal_status: cancelled` in `tool_calls.jsonl`
- **Delivery race:** sessions `429e3f38`, `66634b4d`, `f482f2f0`, `c7e17370` (runs
  `21/20260921072102`, `22/20260922081937`, `22/20260922095049`, `22/20260922112047`)
- **Harness texts:**
  - Muse 1.3.0: *"Do not poll for completion: the final output is delivered to you
    automatically as runtime context and wakes you even after you end the turn. Exception:
    when a runtime overdue notice names a still-running session, you may inspect it or
    terminate it with bash_input now."*
  - Muse 1.3.0: *"By default the runtime waits at most 10 seconds in the foreground… pass a
    larger yield_time_ms (up to 300000)."*
- **Code:**
  - `src/sase/llm_provider/_subprocess_plain.py` (`start_completion_watchdog`)
  - `src/sase/llm_provider/claude.py:49-110,423-424,527-528`
  - `src/sase/llm_provider/muse.py:370-400` (no directive)
  - `src/sase/llm_provider/agy.py:213-238`
  - `src/sase/llm_provider/_subprocess_agy.py:24`
  - `src/sase/finalizers/declaration_store.py:212-217`
  - `src/sase/finalizers/declaration_recovery.py:128-137`
  - `src/sase/xprompts/skills/sase_final.md:11`
  - `src/sase/xprompts/skills/sase_monitor.md:3-7,23-24`
- **Commits:** `68d9e0f65` (watchdog, Sep 20), `bdda3bdf1` (Claude guard, Sep 15),
  `28d1e8708` (check-full explicit-only)
- **Beads:**
  - still `in_progress`: `sase-142.5.2`, `sase-142.5.3`, `sase-14t.3`, `sase-16e.5`
  - `ready`: `sase-15o`, `sase-163`, `sase-16i` (new), `sase-12s`, `sase-12r`
  - E1.5 wrapper defects: `sase-16b`, `sase-16c`, `sase-16d`
