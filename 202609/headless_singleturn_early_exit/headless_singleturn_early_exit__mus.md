# Headless single-turn early exits: audit, root causes, recommended fix (__mus)

Researcher: mus (independent swarm report; conclusions my own).
Date: 2026-09-22. Scope: sase checkout at `sase_37` plus live run telemetry
(chats, agent list, monitor history) from Sept 2026.

I reviewed the prior `agent_long_command_early_exits` swarm (all three member
reports plus the lead consolidation) for inspiration, and re-verified every
claim I rely on below against the current tree and live telemetry. I did not
consult the peer reports of this swarm.

## Bottom line

The user's hypothesis is **confirmed with one important refinement**: agents
do run long commands, background them with provider-native async/monitor
primitives, end their turn waiting for a notification that can never arrive —
and the turn is then recorded as finished while the work is still in flight.
But "agents don't understand headless mode" is not the whole story. Three
different things look identical from the outside ("ran a long command, some
monitor started, the agent died"), and only one of them is the headless
misunderstanding:

1. **Silent false success (the headless misunderstanding).** The agent
   backgrounds work with its harness's own mechanism, ends with "waiting…",
   and SASE records `completed`. Fixed for Claude on Sep 15; still active for
   agy; latent (no guard) for Grok/Muse/Codex.
2. **Designed monitor handoffs used destructively.** `sase monitor start`
   kills the agent on purpose and works as specified — but agents reach it by
   cancelling in-flight verification and restarting it from zero, sometimes in
   long chains. This is most of what "dying" visibly is.
3. **Slow verification underneath both.** `just check` p90 is 34–45 min;
   every provider's foreground window is shorter, so the wait-or-hand-off
   decision is forced constantly.

## What I checked (my own verification)

1. **Monitor history** (`sase monitor list --all -j`, just now): 1319
   monitors; states failed 710 / completed 537 / timeout 57 / stopped 12 /
   lost 3; follow-up outcomes launched 968 / none 324 / launched-degraded 19
   / not-launchable 8. Matches the prior swarm's counts within days of drift
   (1311 then). The handoff machinery itself is healthy — most "failed"
   monitors are commands that exited nonzero, and their follow-ups still
   launched. The problem is agents that never reach `sase monitor` at all, or
   reach it by destroying in-flight work.
2. **Provider glue** (`src/sase/llm_provider/`): full guard matrix re-read in
   the current tree (below). Every cell verified by reading the code, not by
   trusting the prior reports.
3. **Recent transcripts** (newest 300 chats in `~/.sase/chats/202609/`,
   grepped for wait-ending language: "will notify me", "simply wait",
   "monitoring the execution", "once the build … finishes"): 3 hits, and all
   three are *research reports quoting the old pre-fix cases*, not new
   failures. In other words, fresh silent wait-endings are currently rare in
   the sampled window — consistent with Claude fixed, agy the remaining
   active source.
4. **Guidance text**: `sase_monitor.md` skill and `lint_and_test.md` reference
   memory read in full.
5. **Finalizer requirement logic**:
   `src/sase/finalizers/declaration_store.py` read directly.

## Provider guard matrix (verified in current tree)

| Guard | claude | agy | grok | muse | codex |
|---|---|---|---|---|---|
| Single-turn directive in system prompt | yes (`_SINGLE_TURN_DIRECTIVE`, [claude.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/claude.py:49)) | yes (`_AGY_PRINT_MODE_DIRECTIVE`, [agy.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/agy.py:68)) | **no** | **no** | **no** |
| Native background/wakeup tool disabled | yes (`ScheduleWakeup` disallowed; note: `Monitor`, Cron, `RemoteTrigger`, `PushNotification`, `Workflow` still offered in print mode) | n/a (print mode) | **no** | **no** | **no** |
| Wait-state response classifier | yes (`_classify_claude_wait_state`, [claude.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/claude.py:96)) | yes, two-layer: structural trajectory analysis + `_looks_like_no_progress` text fallback ([agy.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/agy.py:195)) | **no** | **no** | **no** |
| Bounded recovery, then loud failure | yes (2 continuations → error) | yes (2 continuations → error) | **no** (first reply = success) | **no** (first reply = success) | **no** |
| Long-command escape hatch | 4h `BASH_MAX_TIMEOUT_MS` + "rerun with larger timeout" | 24h `--print-timeout` | none set (harness auto-backgrounds at ~15s) | 300s yield, then poll | polled unified exec |

Verified details:

- Grok's `_invoke_loop` ([grok.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/grok.py:315)) loops only on a
  pending interrupt message; otherwise it accumulates the response and
  returns it unconditionally. No wait-state check exists.
- Muse's loop ([muse.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_37/src/sase/llm_provider/muse.py:424)) is the same shape —
  returns the first response as success. Its own comment notes headless
  resume is unavailable, so context is reconstructed instead.
- Agy's directive tells the model to "run commands synchronously", which is
  impossible: agy forces commands longer than 10s into the background and its
  tool text orders the model to report and end the turn. The verified
  keep-alive escape is to *ignore* that tool advice and keep calling
  `manage_task`/reading output so the turn stays alive.
- Agy's text classifier misses wait-shaped replies without "I will"-style
  intention lines (e.g. "monitoring the execution … once the build finishes"),
  and its structural detector is version-gated, so both layers can miss at
  once on current agy versions.

## True root causes, ranked

1. **The wait-or-hand-off decision is made by the model, not by mechanism.**
   Nothing mechanical decides when a wait becomes a handoff. The agent must
   predict a duration it cannot predict, its instructions contradict each
   other (Claude's directive says "never end your turn to wait" while the
   monitor skill says handing off — which ends the turn — is the right move
   "whenever it is taking a long time"), and the only handoff primitive
   destroys work already in flight (no adopt/join of a running command
   exists). This single cause produces both failure modes 1 and 2.
2. **Per-provider enforcement of a platform-wide contract.** Single-turn-ness
   is a property of SASE's runner, but it is implemented separately in each
   provider's glue. Claude and agy have directive + classifier + bounded
   recovery; Grok, Muse, Codex have none of it, so a wait-ending reply on
   those providers is accepted as success. Latent today (they poll or hand
   off in practice), but one harness-behavior change away from active loss.
3. **Silent success on a clean tree.** `declaration_store.py` derives
   `submission_required=bool(repository_obligations)` — a run with an
   assigned bead that stops halfway on a clean tree "completes" with no
   declaration and no evidence. The host accepts a mid-task abandonment as
   success regardless of provider.
4. **Native tools work just well enough to teach the wrong pattern.** Polling
   a background task succeeds while the turn is alive, so the agent learns
   "background + wait works" — the failure only materializes when the reply
   ends first. The `decisions:single-turn-agents` record already states this:
   every hosted runtime ships background primitives and every one silently
   no-ops here. A rule disconfirmed by the agent's own experience needs
   mechanical enforcement, not more documentation.

## Recommended solution

Guiding principle (from `decisions:single-turn-agents`): continuation is
always mechanical — mechanism, not the model, decides when a wait becomes a
handoff; a handoff never discards in-flight work; a turn that stops mid-task
fails loudly on every provider.

### Phase 0 — stop the bleeding (small, independent changes)

a. **Host backstop against mid-task abandonment (provider-neutral).**
   Require a final declaration whenever the run has an assigned bead, even on
   a clean tree (`keep` is an acceptable declaration); better still, whenever
   the run carries any completion obligation. Classify a run ending with
   neither declaration nor mechanical handoff (monitor, plan, pipe,
   questions, gate) as `incomplete`, not `completed`. This catches the
   `sase-14t.3` class for any current or future harness without text
   heuristics. Shared-backend behavior — put it where the finalizer wire
   lives (sase-core if mirrored there).
b. **Repair agy (the only active silent-loss source).** Rewrite the directive
   around the verified keep-alive rule (turn ends the moment you stop calling
   tools; background tasks are then killed; ignore the tool's "end the turn"
   advice and keep polling, or hand off to `sase monitor start`); widen the
   text classifier to wait/monitoring-shaped replies without "I will" lines;
   resolve the trajectory-version gating so structural detection ("a
   backgrounded `run_command` still pending at turn end") works on current
   agy; make the continuation nudge state the fact that the command was
   killed.
c. **Replace mid-flight guidance with an up-front per-provider rule**
   (memory/skill edits): Claude runs verification inline with an explicit
   long timeout and never monitors `just check`; all other providers start
   verification directly under `sase monitor start --profile verify` with the
   declaration prepared; everyone is told never to cancel in-flight
   verification to re-run it under a monitor, and never to pipe verification
   through `| tail`. Also disallow Claude's remaining print-mode native
   wait tools (`Monitor`, Cron, `RemoteTrigger`, `PushNotification`,
   `Workflow`).

### Phase 1 — lossless, mechanical handoff (the durable fix)

- **Detached, joinable ToolRuns.** `sase tool run` starts its child under the
  supervisor, outside the agent's process tree; a second request with the
  same key (project, workspace, definition/args digests, input fingerprint)
  joins the run instead of spawning a new one.
- **Monitor adoption** of an in-flight run instead of restart.
- **`--handoff-after DURATION`** (defaulted in the verify profile): if the
  run settles first the agent gets the result; otherwise the command itself
  creates an adopting monitor and ends the turn mechanically. Per-provider
  defaults (Claude late, Grok/Codex/agy early, Muse mid). Afterwards the
  guidance collapses to one line for every provider and the model's duration
  prediction disappears entirely.
- **Provider-neutral wait-state detection** for Grok/Muse/Codex (background
  work outstanding at turn end → shared nudge-then-fail policy) as insurance.

### Phase 2 — fewer, cheaper hops

Governor on verify→fix→re-verify loops (re-run failing gates first; after 3
consecutive failed verification monitors, raise a question/gate instead of
another hop) and faster verification (shared prebuilt `sase_core_rs` wheel;
load-aware admission). This reduces how often any of the above matters.

**What I would not do:** add more "you are headless" prompt text alone (agy's
harness overrides prompts, and agents already know); build another
continuation mechanism, daemon agent, or per-provider polling loop (the
decision record rejects these and the monitor data says the existing handoff
is reliable enough to standardize on); mandate "always inline" (impossible
for agy, quota-burning for Grok/Codex) or "always monitor" permanently (adds
a hop to the median 4.5-min check — acceptable only as a stopgap for
non-Claude providers).

## Limits / what I did not verify

- I did not trace a fresh silent-loss run end-to-end; my transcript sample
  (newest 300) surfaced no new wait-ending failures, so the current-epoch
  evidence for mode 1 is structural (missing guards on three providers, agy's
  broken layers) plus the two agy cases established by the prior swarm, whose
  evidence pointers I did not re-open.
- Grok's `toolset.bash.*` timeout knobs, Muse's legacy shell, and Codex
  `unified_exec` blocking remain untested — recorded as experiments, not
  claims.
- Only local telemetry examined; remote machines out of scope.
- I did not read this swarm's peer reports (`__cld.md`/`__gem.md`); any
  overlap with their findings is coincidental.
