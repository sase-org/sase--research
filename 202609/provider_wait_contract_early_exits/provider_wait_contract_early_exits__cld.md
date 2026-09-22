# Agents That "Die" After Long Commands: The Wait Contract Is The Bug

Researcher `research.29.cld`, 2026-09-22. Independent audit of SASE agent runs on athena
Sep 20–22, against sase `8d1779a3e`, muse `1.3.0-R3401.1`, agy `1.2.8`, Claude Code
print mode.

## Bottom line

**Your hypothesis is right about the symptom and wrong about the cause for the provider
that is actually producing it today.**

Since Sep 20 the fleet is Claude + Muse (Grok and Codex have not run since Sep 19). All
of the "ran something long, then died" cases I can find in the last three days are Muse,
and Muse agents are *not* confused about headless mode. `muse exec` genuinely keeps the
process alive after the model ends its turn, wakes the model when a background command
finishes, and repeats that until the work is done. I verified 44 Muse sessions in which
work outlived a turn end, and 31 sessions in which the model was woken and continued in
the same SASE run. One waited 1h30m across three overdue reminders and closed its bead.

What kills them is SASE:

1. **The host reaps a provider that is legitimately waiting.** The Sep 20 teardown
   watchdog (`68d9e0f65`) kills the provider 120 s after a final declaration is
   accepted, with no check of whether it is idle or mid-work. Meanwhile `/sase_final`
   *instructs* agents to declare before an "I will wait" response. Result: the agent
   obeys both instructions and is killed 120 s later, its verification killed with it,
   its bead left open — and the run is reported **SUCCESS**. 7 runs in 3 days.
2. **A Muse delivery race strands the model.** When a background command finishes
   *mid-turn*, Muse marks the notice `deferred_token_held`, drains it into the running
   turn as a developer message, and the model does not notice — it ends the turn saying
   "still running, I'll report when it lands". Nothing is pending any more, so Muse
   exits and no wake ever comes. 4 runs in 2 days, 4 of 4 with that exact signature.
3. Everything else is small: agy's known broken no-progress detector (bead `sase-15o`,
   still `ready`), and designed `sase monitor start` handoffs (only 21 monitors in three
   days, down from 80+/day when Grok and Codex ran).

Claude is clean: **zero** native background/scheduling tool uses in 217 Claude runs since
the Sep 15 fix. Adding more "you are headless" prompt text would not have prevented a
single failure in this window — and for Muse it would be false.

**The root cause is that SASE has no model of each provider's wait semantics.** It
asserts one universal rule ("agents are single-turn; native background primitives
silently no-op"), encodes that rule in prompts *and* in host mechanisms (the teardown
watchdog, declaration timing, the success test), and that rule is factually wrong for
`muse exec`. The recommendation in §7 is to make the wait contract explicit, per
provider, and derive both the guidance and the host policy from it — plus a
provider-neutral completeness test so that "I am waiting" can never be recorded as
success.

## 1. Method and scope

| Source | What I did |
| --- | --- |
| `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/{20,21,22}` | Parsed all 499 artifact dirs; 420 are agent runs (the rest are monitor/gate shells). Extracted provider, model, final reply, declaration, recovery, plan/monitor handoff, tool calls |
| `~/.sase/dismissed_bundles/202609` | Recovered outcome/status for dismissed runs, whose `done.json` is deleted on dismissal |
| `~/.local/share/muse/sessions/2026/09/**/session.jsonl` | Full event replay of all 217 Muse sessions: tool calls with arguments, tool results, inbox deliveries, per-turn terminals, session end |
| `sase monitor list --all -j` | 1,319 monitors; per-day counts by starter provider |
| `muse-bin-1.3.0-R3401.1`, `agy 1.2.8` | Tool-description and schema strings, read directly out of the binaries |
| sase source at `8d1779a3e` | Watchdog, provider adapters, finalizer recovery, `/sase_final` and `/sase_monitor` skill sources |
| `sase bead read` | Current status and close reasons of every bead touched by a failed run |

I did not read the reports of the other researchers in this swarm. I did read
yesterday's consolidated report `research:202609/agent_long_command_early_exits/…` for
context, and I re-derived every claim of it that I use; §8 lists where I contradict it.

## 2. What the fleet actually looks like now

Agent runs per provider (Sep 20–22, monitor/gate shells excluded):

| Provider | Runs | Long-command behavior (verified) |
| --- | ---: | --- |
| claude | 217 | Blocks in the foreground up to 4 h (`BASH_MAX_TIMEOUT_MS`); background tools disabled; wait-reply classifier nudges then fails |
| muse | 194 | **Auto-backgrounds at 10 s** (default) or at the model's `yield_time_ms`, max 300 s; then wakes the model after the turn ends |
| agy | 8 | Backgrounds at ≤10 s; harness tells the model to end the turn; print mode kills background tasks on exit |
| codex | 1 | (inactive) |

Grok: 0 runs since Sep 19. Codex: 1 since Sep 20. Any analysis weighted toward Grok or
Codex telemetry is describing a fleet that no longer exists.

Muse's Bash tool description, verbatim from the 1.3.0 binary:

> By default the runtime waits at most 10 seconds in the foreground; for a slow build or
> test, pass a larger `yield_time_ms` (up to 300000) to wait for it to finish in this one
> call. Commands still running after the wait remain managed by the runtime and return an
> internal `session_id` handle […]; final output arrives later as runtime context. […] If
> there is no substantive next work after a command backgrounds, end the turn without
> extra status text. Use `bash_input` only to send input to or terminate that live
> session, **not to poll a backgrounded command for completion** — the final output is
> delivered automatically.

And the per-result guidance the model receives when a command backgrounds:

> The command is still running in the background […] Do not poll for completion: the
> final output is delivered to you automatically as runtime context **and wakes you even
> after you end the turn**. […] Managed sessions end when your agent session ends.

In `muse exec` that promise is true. Across Sep 20–22:

- 154 of 217 sessions backgrounded at least one command (481 commands total).
- 44 sessions had work outlive a turn end.
- 31 sessions were woken at least once after a turn end and continued in the same SASE
  run; Muse also sends "running 30m, no output yet, Nth reminder" notices that produce a
  short wake turn.
- 51 post-turn waits longer than 30 s, ~602 minutes total, median 8.9 min.

Worked example — `sase-14n.11` (session `c9dcd3ee`), the mechanism working as designed:

```
18:14:35 model: "Verification re-running in the background; waiting on its result…"
18:14:56 turn terminal: completed
18:39:28 inbox: background task (session 48) — running 30m, no output yet, 1st reminder
18:39:29 turn 2 starts → "still progressing" → ends
19:09/19:39  2nd and 3rd reminders, two more short turns
19:41:14 inbox: Background terminal completed
19:44:45 model: "Bead sase-14n.11 is done and closed."   (bead closed 23:43:43Z)
```

That agent never submitted a declaration before it waited, so the watchdog never armed.
That single difference is what separates it from every failure in §3.

What Muse auto-backgrounded, by command class (Sep 20–22):

| Command | Times backgrounded |
| --- | ---: |
| `just check` / `sase tool run check` | 219 |
| `sase bead …` (note/close/search) | 91 |
| `just install` | 42 |
| `just test-scoped` | 22 |
| `sase final context` | 6 |

The 91 bead commands and 6 `sase final context` calls matter: they are *supposed* to be
fast, and they crossed Muse's 10 s default yield because the host is loaded (load
averages of 18–47 appear throughout these sessions). Slow SASE CLI calls push ordinary
bookkeeping onto the wait path.

## 3. Failure mode A — the host reaps a provider that is legitimately waiting

### Mechanism

1. Muse backgrounds the verification command and tells the model to end the turn.
2. The model does what `/sase_final` says. The skill's own words:
   *"It is mandatory for final answers, incomplete-status responses, **"I will wait"
   responses**, and replies that intend to resume in a later turn"*, and
   *"Treat a successful submit as the final action of the normal turn."*
   Core memory says the same and adds *"Intending to resume later is not an exemption."*
   So the agent submits a `commit` declaration with `bead_action: keep`, then ends the
   turn to wait for the wake.
3. `final_submission.json` is written. The teardown watchdog
   (`src/sase/llm_provider/_subprocess_plain.py:140`) starts a 120 s timer. Its loop
   checks nothing except "is the process still alive":

   ```python
   while process.poll() is None:
       ...
       elif declared_at is not None and now - declared_at >= grace:
           _tear_down_stalled_provider(...)   # SIGTERM → SIGKILL + reap descendants
   ```
4. 120 s later Muse is killed. Muse records `Background terminal cancelled … reason:
   cancelled by runtime client`. The verification dies with it.
5. SASE reports the run as **SUCCESS**, with one stderr line:
   `[sase] muse (pid …) was still running 120s after its final declaration was accepted;
   terminated it. The completed reply is unaffected.` The reply was *not* complete.

The watchdog's own design note says it exists for "a provider CLI [that] could finish
its turn […] and then never exit because a process leaked from its tool sandbox held a
pipe open". A Muse agent waiting for its harness wake is indistinguishable from that,
under a test that only looks at liveness.

### Evidence

Every SASE run with a `provider_teardown_stall.json` in the window (all 8 are Muse):

| Run | Agent | Reply when it was killed | Bead afterwards |
| --- | --- | --- | --- |
| `20/20260920171045` | `sase-142.5.2` | "`just check` is still running. Holding the bead open until verification lands" | **still `in_progress`** |
| `20/20260920171046` | `sase-142.5.3` | "the recorded `check` gate and one bead note are running. On their delivery I will…" | **still `in_progress`** |
| `20/20260920171610` | `sase-14n.4` | "final verification … is still running **and will wake me**, after which I'll close the bead" | closed by hand: *"The agent finished its work. It just didn't complete verification."* |
| `20/20260920171615` | `sase-14n.9` | "waiting on the in-flight recorded `sase tool run check` to close sase-14n.9" | closed by hand: *"This agent seemed to complete its work but left the beat open because verification was incomplete."* |
| `21/20260921062759` | `sase-157.7` | "now waiting on the full `just check` gate to finish before closing" | killed *during* its wake turn, mid-`sase bead close` |
| `21/20260921153305` | `sase-15p.2` | "Waiting on the `just install` build to run tests and finish verification" | closed by hand: *"…didn't close the bead because it was unable to finish verification."* |
| `22/20260922104606` | `0pb--1` | "Still in flight: the full `check` lane and the visual check-only rerun" | killed 6 s into its wake turn |
| `21/20260921062756` | `sase-157.3` | (genuinely finished; legitimate reap) | closed normally |

7 of 8 firings hit an agent that was waiting exactly as its harness told it to. Two of
them were killed *while actively working* in a woken turn — the watchdog does not even
look for that.

### Cost

- Three beads (`sase-142.5.2`, `sase-142.5.3`, plus agy's `sase-14t.3`) are **still**
  `in_progress` days later.
- You closed at least five by hand, and your close reasons are the same sentence every
  time: *"The agent completed its work but didn't close the bead because it didn't
  finish verification"* (`sase-14n.4`, `sase-14n.9`, `sase-15p.2`, `sase-11y.11.4`,
  `sase-165.7`).
- Work landed **unverified**. In each case the host's commit finalizer committed the
  tree (that is the point of the intermediate declaration) and then the gate that would
  have checked it was killed.

## 4. Failure mode B — Muse's mid-turn delivery race

When the background command finishes while the model is still mid-turn, Muse queues the
completion, records `inbox_delivery_anomaly: deferred_token_held`, then "drains" it into
the *current* run as a `role: developer` history message. The model does not act on it,
ends the turn claiming to be waiting, and Muse — with nothing pending — exits cleanly.
No wake is possible, because the delivery was already consumed.

| Run | Agent | Completion | Model's final line |
| --- | --- | --- | --- |
| `21/20260921072102` | `sase-11y.11.4` | 08:50:51 drained 08:52:33 | 08:54:21 "…`just test-scoped` … is still running; I'll verify its result and close the bead when it lands" |
| `22/20260922081937` | `0p5--code` | 08:36:32 drained 08:36:33 | 08:36:53 "the full verification gate is still running; I'll report the result when it lands" |
| `22/20260922095049` | `0p8--code` | 09:55:01 drained 09:55:42 | 09:57:22 "The duplicate search … is still running; when its result arrives I will file the bead" |
| `22/20260922112047` | `sase-165.7--1` | 11:30:02 drained 11:32:06 | 11:32:39 "Waiting on the measurement run to finish; will record results, verify, and close the bead then" |

Contrast: when the completion lands *after* the turn terminal (`d0c71e11`, `8b2492b2`),
the deferral is held and delivered as a wake turn, and the agent recovers. So this is a
timing race, not a lost message. The model genuinely received the text (I confirmed the
1,358–1,836-byte developer message in the model input trace) and ignored it.

SASE then made it worse in two of these: the declaration-recovery turn fired (missing
declaration), and its prompt says *"Do not perform unrelated work, make no new
repository edits… submit one valid declaration… then return briefly."* The agent
dutifully declared with the bead kept open and reported success. The host had the
finished verification result available and used its one recovery turn to cement the
abandonment instead of finishing the task.

**Important:** for Muse this state is mechanically detectable with certainty. `muse
exec` only exits while a wait is outstanding if it was killed; a clean exit means
nothing is pending. So *"clean exit + final text claims to be waiting"* ⇒ the wait is
stranded, always. No heuristics about model phrasing are needed beyond the text match,
and SASE already streams the facts it needs (`tool_calls.jsonl` in these runs contains
119 `execution_state: background_running` results and the `Background terminal
completed` / `cancelled` notices, parsed from muse's stdout via
`PAYLOAD_TOOL_RESULT` in `_tool_call_muse.py:50`).

## 5. Failure mode C — agy, and failure mode D — designed handoffs

**agy** (8 runs, all research): no failure in this window; the two known losses were
`sase-14t.3` (Sep 20, bead still `in_progress`) and `research.24.gem` (Sep 21). I
re-verified the latent defect rather than the anecdotes:

- `_SUPPORTED_AGY_TRAJECTORY_VERSIONS = frozenset({"1.0.10"})`
  (`_subprocess_agy.py:24`) while the installed agy is **1.2.8** — structural
  no-progress detection is silently off. Bead `sase-15o` is still `ready`.
- agy's own prompt still contains: *"After launching a background task such as
  'run_command', YOU MUST TAKE ONE OF THE FOLLOWING TWO ACTIONS: […] B) simply pause and
  end the turn to wait for the background task to complete."* SASE's directive tells it
  the opposite (*"Run commands synchronously and wait for their output"*).
- **New, and contradicting yesterday's report:** agy 1.2.8's own worked example in the
  system prompt passes `{"CommandLine":"npm test","Cwd":"…","Blocking":true,
  "WaitMsBeforeAsync":0,…}`, and `CortexStepRunCommand` carries `Blocking`,
  `WaitMsBeforeAsync`, `RunPersistent`, `IsDaemon`, `NotificationTimeoutSeconds`. I could
  not prove from strings alone whether the model-facing schema exposes `Blocking` in
  1.2.8, but "agy cannot block" should be re-tested on 1.2.8 before any design is built
  on it. That is a 5-minute experiment.

**Designed monitor handoffs** are no longer the dominant visual: 21 monitors started by
agents in three days (Sep 20: 10, Sep 21: 7, Sep 22: 4), versus 47 on Sep 18 from Grok
alone. Of the Muse-started ones, 12 of 21 failed or timed out. Two oddities worth noting:
Muse *backgrounded the `sase monitor start` call itself* (`dfa9d051`, `dae5caec`) because
it outran the 10 s yield, and the resulting replies ("I'll follow up once it completes")
look identical to a stranded wait even though the handoff worked.

## 6. Root causes

**R1. SASE has no per-provider wait contract, and its single universal rule is false for
one of its two active providers.** `decisions:single-turn-agents` states as its premise:
*"Every hosted agent runtime ships background-execution and scheduling primitives, and
every one of them silently no-ops here: the runner captures the turn and exits, so there
is no process left to resume into."* For `muse exec` there **is** a process left: it
stays alive, wakes the model, and finishes the job, inside one SASE run, holding the same
workspace claim and runner slot the whole time — which is exactly what a 45-minute
foreground `just check` on Claude already does, and which SASE already accepts. The
decision's own reopen condition ("a hosting platform ships a true suspend/resume
primitive that preserves workspace claims and provider budget") is arguably met in a
weaker form. Because the premise is treated as universal, the host built mechanisms that
assume it.

**R2. The completion protocol conflates "declaration accepted" with "turn over".** The
watchdog arms on the declaration; the skill tells agents to declare before waiting. Those
two rules are individually reasonable and jointly lethal. Note that the failing agents
were *following instructions* — this is not rationalization or misunderstanding.

**R3. "Success" means the process exited, not that the task reached a terminal state.**
A reply that says "I am waiting" with an assigned bead still open, no mechanical handoff,
and a killed verification is recorded as `SUCCESS`/`completed`. The only backstop,
declaration recovery, asks for a declaration and explicitly forbids finishing the work.

Contributing factors (real, but not the trigger): verification wall-clock (`just check`
routinely 15–45 min under load) far exceeds every harness's foreground window; piping
verification through `| tail` hides progress and invites "still running with no output
yet" replies; and host load pushes even `sase bead note` past Muse's 10 s default yield.

## 7. Recommended solution

**Principle: the host must know each provider's wait contract, and must never silently
end a wait it did not start. Whatever the contract says, the decision is made at the
moment the wait begins, mechanically and visibly — not 120 seconds later by a reaper.**

### P0 — stop the bleeding (small, independent, today)

**a. Make the teardown watchdog background-aware.** In `_subprocess_plain.py`, the kill
condition becomes *declaration accepted **and** the provider reports no pending
background work **and** no stream activity for the grace period*. Pending work is already
on the stdout stream SASE parses: pair `execution_state: background_running` (with its
`work_id`) against the later `Background terminal completed/failed/cancelled` notice. When
work is pending, do not kill; apply a separate, much larger ceiling
(`SASE_PROVIDER_WAIT_CEILING`, default in the hours, aligned with the existing agent
timeout), record the wait in an artifact, and surface it in the TUI as a distinct state
(e.g. `WAITING ON BG`) so a waiting agent is visibly different from a hung one. Keep the
existing 120 s behavior for the idle-with-leaked-pipe case it was written for.
*Stopgap available immediately:* `SASE_PROVIDER_TEARDOWN_GRACE_SECONDS=0` disables the
watchdog entirely; it trades this failure for the original hang risk, so it is a bridge,
not a fix.

**b. Remove the instruction that creates the conflict.** `/sase_final` and the core
memory currently require a declaration for *"I will wait" responses* and *replies that
intend to resume in a later turn*. On a wake-capable provider those are not turn
endings at all. The rule should be: **do not declare while background work you are
waiting on is still pending — declare in the turn where the work is actually done**; if
you cannot be woken, you cannot wait, so hand off with `sase monitor start`. Both files
are memory/skill sources (`src/sase/xprompts/skills/sase_final.md`, `sase/memory/*`) and
must go through `/sase_memory_write`. Better still, enforce it mechanically: have
`sase final submit` refuse (with a clear message naming the pending command) when the
current run's provider is wake-capable and has pending background work. That is a host
check, not a prompt.

**c. Turn a stranded wait into a continuation, not a declaration.** Give Muse the
equivalent of Claude's wait guard (`claude.py:49–110`), using the stronger Muse-specific
signal: *clean exit + final text matches the wait regex ⇒ stranded, by construction*.
Continue with a bounded nudge (Muse has no headless resume, so reuse the existing
reconstructed-context path in `muse.py`) whose text states the facts: *"the command you
were waiting on finished at HH:MM with exit N; its output is <…>; nothing is running now;
finish the task."* And when declaration recovery fires after a wait-reply, the recovery
prompt should carry the delivered background result and permit finishing the task rather
than only declaring.

### P1 — make the contract explicit (the durable fix)

Give every provider adapter a declared **wait contract** — one small record, not prose:

| Provider | Foreground window | Post-turn wake | Native bg tools | Host policy derived from it |
| --- | --- | --- | --- | --- |
| claude | 4 h | none | disabled | Block inline; wait-reply ⇒ nudge, then fail |
| muse | 10 s default / 300 s max | **yes, in-process** | n/a | Don't reap while pending; declare last; stranded-wait ⇒ nudge |
| agy | ≤10 s | none (tasks killed at exit) | n/a | Must not wait; structural no-progress detection must be on (fix `sase-15o`) |
| codex / grok / others | in-turn polling | none | none | Poll or hand off; detect "session still open at turn end" |

Everything else is derived from that record instead of being restated in four places:
the provider directive text, the disallowed-tool list, the watchdog policy, the
wait-state classifier, and the one line of verification guidance the agent sees. Today
those live in `claude.py`, `agy.py`, `lint_and_test.md`, the `/sase_monitor` skill, and
the watchdog, and they already disagree with each other (the `/sase_monitor` skill's
description asserts that *"provider-native background-execution […] do not work in SASE"*,
which is false for Muse and is the reason nobody noticed the watchdog interaction).

Per `sase/memory/rust_core_backend_boundary.md`, the *classification* — is this run
complete? — is shared backend behavior and belongs in `sase-core` with the finalizer
requirement logic; the per-CLI capability table and stream parsing are frontend adapter
concerns and stay in Python here.

This also needs a decision record: `decisions:single-turn-agents` should be amended or
superseded to say what is actually true — *a SASE run is one runner process and one
workspace claim; how many provider turns happen inside it is a per-provider property, and
a wait is only legitimate when the host knows about it and bounds it*. That is a memory
change, so it goes through `/sase_memory_write`.

### P2 — a provider-neutral completeness test

Independent of any provider: a run that ends with **(a)** no final declaration or a
declaration that keeps an assigned bead open, **(b)** no mechanical handoff (monitor,
plan, pipe, questions, gate), and **(c)** a final reply that claims to be waiting, is
`incomplete`, not `completed`. Surface it in the TUI and in `done.json`, and let the
existing recovery path continue the work rather than just collect a declaration. In this
window that rule fires on exactly the 11 runs analyzed above and on nothing else — it is
cheap, and it is the only part of this that protects you against the *next* provider's
quirks.

### P3 — reduce how often any of this matters

- **Bound the wait at its start, not after the fact.** For a wake-capable provider the
  in-process wait is cheaper than a monitor hop for the median 9-minute wait, but it
  holds a runner slot; above a threshold (~20–30 min) the monitor handoff is the right
  answer because it frees the slot. Make that threshold a host default, not a model
  judgment call — the `--handoff-after` idea from the `sase_tool` research is the right
  shape, and for Muse it can be implemented without any new execution machinery because
  the command is already surviving in the harness's managed session.
- **Stop piping verification through `| tail`.** It is the direct cause of the "still
  running with no output yet" replies, and of at least one cancel-and-restart.
- **Fix the latency that pushes `sase bead note` past a 10 s yield** (91 backgroundings
  in three days). A bookkeeping command that backgrounds turns every bead update into a
  wait.

### Explicitly rejected

- **More "you are headless" prompt text.** Every agent that failed here was following
  its instructions; for Muse the claim is false, and a false rule teaches agents to
  discount the true ones.
- **Killing every provider immediately after the declaration** (the current behavior,
  just faster). It would make the failure louder but would still throw away work that
  the harness was about to finish, and it would forbid a wait mechanism that demonstrably
  works 31 times in three days.
- **Building detached joinable ToolRuns first.** That is a good idea for other reasons,
  but nothing in the current failures requires it: the work is not being lost because it
  cannot be re-joined, it is being lost because the host kills it.

## 8. Where I disagree with yesterday's consolidated report

| Its claim | My finding |
| --- | --- |
| "I found no case on Grok, Muse, or Codex since Sep 15"; "The Muse cases correspond to monitors in `sase monitor list`" | **Wrong.** Muse is the *only* provider losing work now: 7 watchdog kills + 4 stranded waits in Sep 20–22, none of which correspond to a monitor. The report's scan relied on Muse's empty tool inputs in `tool_calls.jsonl` and on the trailing-`sase monitor start` test, and Muse's waits leave no monitor row |
| "Most visible dying is the designed monitor handoff" (16% of runs, 49% of Grok) | True for Sep 14–19, obsolete now: 21 agent-started monitors in three days |
| "agy 1.2.7's run_command schema exposes no blocking option" | Unresolved on 1.2.8: the shipped prompt example passes `Blocking:true`, and the proto has `Blocking`/`RunPersistent`/`IsDaemon`. Needs an empirical test before it is treated as fact |
| "The host accepted a mid-task abandonment as success… require a declaration whenever a bead is assigned" | Right diagnosis, insufficient remedy. All 7 watchdog victims *did* submit a declaration; requiring one would not have caught them. The test has to be about the bead still being open and the reply claiming a wait (§P2) |
| Recommends detached joinable ToolRuns + `--handoff-after` as the durable fix | Good, but it is not the fix for what is failing today, and it is a large build. The wait contract (§P1) is smaller and strictly necessary first |
| Claude clean since `bdda3bdf1` | **Confirmed independently**: 0 native background/scheduling tool uses in 217 Claude runs, Sep 20–22 |

## 9. How to tell it worked

| Metric (from the same artifacts) | Baseline Sep 20–22 | Target |
| --- | ---: | --- |
| `provider_teardown_stall.json` written for a provider with pending background work | 7 | 0 |
| Runs recorded SUCCESS whose final reply claims a wait | 11 | 0 (classified `incomplete`, then continued) |
| Beads left `in_progress` by a killed or stranded agent | 3 open + 5 hand-closed | 0 |
| Declaration-recovery turns that end with the bead still open | 2 | 0 |
| Muse post-turn waits that complete by wake | 31 | ≥31 (this is the path to preserve, not remove) |
| agy runs with structural no-progress detection enabled | 0 (allowlist stuck at 1.0.10) | all |

## 10. Limits and open questions

- Only athena, only Sep 20–22 for the per-run audit (the Muse session corpus covers all
  of September). Remote machines not examined.
- I mapped Muse sessions to SASE runs by recorded `muse_session_id` where available and
  by workspace + start time otherwise; a handful of `--plan`/`--code` siblings in the
  same workspace could be mislabeled. The failure *counts* come from
  `provider_teardown_stall.json` and from session logs directly, so they do not depend on
  that mapping.
- I did not test `muse exec --enable-shell-tool` (the legacy shell) to see whether it
  blocks instead of yielding, and I did not test whether a larger `yield_time_ms` ceiling
  can be configured. Both are cheap experiments that could reduce backgrounding
  altogether.
- Whether agy 1.2.8 exposes `Blocking` to the model is unresolved (§5).
- I did not measure how often the in-process wait costs a slot that a queued agent
  wanted; ~602 minutes of post-turn waiting in three days is the upper bound on the
  capacity at stake.
- Proposed follow-ups I did **not** file as beads (swarm duplicate risk; the lead should
  file them): (1) watchdog reaps waiting Muse providers — bug; (2) `/sase_final` "I will
  wait" instruction conflicts with the watchdog — memory; (3) stranded-wait detector for
  Muse — feature; (4) `sase-15o` already covers the agy allowlist.

## Appendix — evidence index

- **Watchdog kills:** artifact dirs `20/20260920171045`, `20/20260920171046`,
  `20/20260920171610`, `20/20260920171615`, `21/20260921062756`, `21/20260921062759`,
  `21/20260921153305`, `22/20260922104606` (each has `provider_teardown_stall.json`);
  matching Muse sessions `da329fb7`, `0f73425e`, `5248c2ba`, `61cdf105`, `c2e8b6d0`,
  `8b2492b2`, `e0d6def8`, `6366eee0`.
- **Stranded waits (delivery race):** `21/20260921072102`, `22/20260922081937`,
  `22/20260922095049`, `22/20260922112047`; sessions `429e3f38`, `66634b4d`, `f482f2f0`,
  `c7e17370`.
- **Wake working:** sessions `c9dcd3ee` (`sase-14n.11`, 1h30m), `64584d8f`, `69741503`,
  `bb014b66`, `eefe0f8b`, `d0c71e11`, `8b2492b2` (woken, then killed).
- **Live at the time of writing:** `sase-165.6.f0--code` (`22/20260922111254`), RUNNING
  in the wait-for-wake state.
- **Code:** `src/sase/llm_provider/_subprocess_plain.py:140` (watchdog loop);
  `src/sase/llm_provider/muse.py` (no directive, no wait guard);
  `src/sase/llm_provider/_subprocess_muse.py` (joins every run terminal — multi-turn safe);
  `src/sase/llm_provider/_tool_call_muse.py:46-60` (stdout payloads already carrying the
  background state); `src/sase/llm_provider/claude.py:49-110,470-500` (directive, nudge,
  classifier — the pattern to generalize);
  `src/sase/llm_provider/_subprocess_agy.py:24` (version allowlist);
  `src/sase/finalizers/declaration_recovery.py` (recovery turn);
  `src/sase/xprompts/skills/sase_final.md:11` ("I will wait" instruction).
- **Related:** beads `sase-15o` (ready), `sase-142.5.2`, `sase-142.5.3`, `sase-14t.3`
  (all still `in_progress`); commit `68d9e0f65` (watchdog), `bdda3bdf1` (Claude guard),
  `28d1e8708` (check-full explicit-only); research
  `research:202609/agent_long_command_early_exits/agent_long_command_early_exits.md`,
  `research:202609/monitor_continuation_design/monitor_continuation_design.md`.
