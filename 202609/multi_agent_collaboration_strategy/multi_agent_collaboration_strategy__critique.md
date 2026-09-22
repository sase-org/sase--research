# Critique: Multi-Agent Collaboration for SASE Agents

- **Type:** critique of the lead's consolidated report, and a companion to it
- **Date:** 2026-09-22
- **Subject:** [multi_agent_collaboration_strategy.md](multi_agent_collaboration_strategy.md)
  (`research.26.final`). Two snapshots are registered under the same label:
  `file:explicit:004f14dd…` is the earlier one and `file:explicit:2c4def79…` the later.
  They differ only in the `sase-163` sentence in §9. The later snapshot matches the
  canonical file, which is the one reviewed here.
- **Also read** (through `sase artifact read`): the three drafts
  ([cld](multi_agent_collaboration_strategy__cld.md),
  [mus](multi_agent_collaboration_strategy__mus.md),
  [gem](multi_agent_collaboration_strategy__gem.md)), plus
  [`family_channel_delivery`](../family_channel_delivery/family_channel_delivery.md) and
  [`multi_cli_orchestration_vs_sase`](../multi_cli_orchestration_vs_sase/multi_cli_orchestration_vs_sase.md).
- **Evidence tags:**
  - **[code]** read at sase `8246e8286`.
  - **[corpus]** my own rescan of athena's `ace-run` archive for 2026-08-15 → 09-22:
    7,316 run directories, 5,043 prompts and 4,823 tool logs.
  - **[V]** primary source fetched today.
  - **[inferred]** reasoning I did not test.

---

## Verdict

**The main conclusion holds, with corrections.** Build collaboration as information the
host carries between single-turn agents, stage it, and don't build peer chat, polling,
A2A, supervisors or leases. The code citations, the headline corpus numbers and the Claude
Code side-channel finding all check out.

**The most important correction is to Stage 1b.** The review evidence, and SASE's own
epic data, do not support a `different_from_author` vendor constraint:
- The one study cited shows that the reviewer's **strength and review mode** matter. Being
  a different vendor does not help by itself.
- SASE's routing pools already send about three quarters of epic landings to a lander
  from a different vendor.
- On athena, the lander's vendor predicts its behaviour far better than whether it
  matches the authors' vendor.

**Three other corrections materially affect implementation:**
- Stage 1a is prioritised on how often `%wait` is used, not on any demonstrated need.
- Stage 2's acknowledgment design misses every turn that ends through a handoff.
- Stage 3 misses the simplest mid-turn path for Claude: stdin that the runner owns.

---

## Revised bottom line

What an implementer should act on. Anything not listed here stands as the lead wrote it.

1. **Direction: unchanged.** The host carries information between turns. Agents don't
   converse, poll, or wake each other. The durable family inbox comes after cheaper
   loops. The "Never" list in the lead's final section stands.
2. **Stage 0: build it (task `sase-163`), with a corrected rationale.**
   - Launch SASE Claude agents with `--settings '{"crossSessionInbound":"refuse"}'`.
   - Disallow `ListAgents`. Keep `SendMessage`: denying it also removes in-session
     subagent messaging.
   - Remove the async tools. `CLAUDE_CODE_DISABLE_WORKFLOWS=1` and
     `CLAUDE_CODE_DISABLE_CRON=1` exist for Workflow and cron. `--disallowedTools`
     also works for those two, and it is the only targeted switch I found for `Monitor`
     and `RemoteTrigger`.
   - The reason is **not** that results "can never arrive". `claude -p` stays open for
     background work for up to 10 minutes. The results are lost because SASE's final
     declaration comes last and SASE's own watchdog kills the provider 120 s after the
     declaration is accepted (see finding m1).
   - Optionally, log any stream event with `origin.kind: "peer"` as an audit tripwire.
3. **Stage 1: new order, and two items redesigned.**
   - **(a) Opt-in `%wait` failure policy.** Resume the waiter with a failure bundle
     instead of parking it. This is the collaboration pain with the most evidence on
     SASE itself: 79 "can never self-resolve" notifications in 8 days.
   - **(b) Continuation-ownership repair.** Every turn-ending branch must record the next
     action, and recurring supervision should be scheduled by the host. mus and
     `family_channel_delivery` both call for this; the lead dropped it.
   - **(c) Review routing: measure first, then route by capability, not by vendor.**
     - Analyse the 282 existing epics, which already contain natural (phase vendor,
       lander vendor) pairs.
     - If routing is still wanted, make it a *soft* preference: the reviewer is at least
       the author's tier, the strongest available model is preferred, and a different
       vendor only breaks ties.
     - Have reviewers report findings that tests or the author verify, instead of
       rewriting code that already passes.
     - Never hard-require a different vendor.
   - **(d) Delegation reply join: try a recipe first.** Document and test a two-turn join
     built from existing `/sase_run` pieces (finding M5). Build
     `resume_requester_on_completion` only if people use the recipe, mainly to fix
     failure handling.
   - **(e) Reply bodies and every clan member's chat in `%wait` context: low priority.**
     Waiters overwhelmingly use `%wait` as an ordering barrier, not to receive content.
   - **(f) Plan-time overlap warnings: optional**, as the lead says.
4. **Stage 2: the family inbox, as the lead specifies, with two fixes.**
   - Every turn-ending path records the acknowledgment: `/sase_final` **and** the
     plan, monitor, pipe, questions, gate and launch-request handoffs.
     - Otherwise the host treats a batch included in a handoff-ended turn as
       included-but-unacknowledged.
   - The inbox reports honestly when a message is posted after a family's last shell has
     already ended. The turn-end successor rule does not cover that case.
5. **Stage 3: mid-turn delivery, with a different first choice for Claude.**
   - For Claude, prefer the runner writing extra user messages to a
     `--input-format stream-json` stdin that it keeps open. Claude picks them up between
     tool calls in the same turn, with no socket and no hook.
     - Today SASE writes the prompt to stdin and closes it (`claude.py:539-542`).
   - A `PostToolUse` hook is the fallback.
   - Codex `turn/steer` stays gated as the lead describes.
   - Before deciding whether to build this at all, re-ask the March question with the
     corrected history in finding M4.

**Confidence:**
- **Moderate to high** in the overall architecture.
- **Low** in any specific quantitative benefit of cross-vendor review for SASE's
  workload. Nothing measured on repository-scale work settles it yet.

---

## Findings

### Critical

**C1. Stage 1b rests on the wrong abstraction: vendor difference instead of reviewer
strength and review mode.** It appears in *§4* (the Xiang row), *§6.3 1b*, *§7
decision 2* and *Recommended solution 2(b)*.

*The study itself* [V] ([arXiv 2607.21656](https://arxiv.org/abs/2607.21656)):
- **Setup:**
  - 116 LiveCodeBench problems.
  - `claude-opus-4-7` (Claude Code 2.1.50) against `gpt-5.5` (Codex CLI).
  - One run per task.
  - The reviewer **cannot execute code**, and its rewritten program *is* the submission.
- **Results:**
  - Codex draft, Claude review: .716 → .897.
  - Codex draft, **Codex** review: .716 → .845 (+12.9 pts). Same-vendor review helps too.
  - Claude draft, Claude review: flat, with 3 fixes and 3 regressions.
  - Claude draft, Codex review: .914 → .828, with 13 regressions against 3 fixes.
- **The authors' explanation:** gains depend on "whether the repairer is stronger than
  the drafter". A weaker reviewer "tends to fall back on rewriting".
- **Limits:** the difference between the two cross-vendor pairings is not significant
  (corrected p = .144). The authors say the result "does not generalize to
  repository-scale bug fixing … or multi-file review".
- **Supporting evidence** [V]: Jin & Chen ([arXiv 2603.00539](https://arxiv.org/abs/2603.00539))
  report that LLM reviewers reject correct code more often once they are asked to explain
  and repair it.

*SASE's routing already mixes vendors* [code, corpus]:
- `@medium` (the phase default) and `@large`/`@xlarge` (landers) are round-robin
  `claude | codex | grok` pools (`model_alias_defaults.yml`).
- Across 282 epics:
  - 51 landers came from a vendor that wrote no phase;
  - 161 epics had mixed vendors;
  - only 70 epics had every phase from the lander's own vendor.
- So about 75% of landings already include cross-vendor review. For the 57% of epics
  whose phases were written by several vendors, "different from the author" has no clear
  meaning.

*SASE's own data points at the reviewer's vendor* [corpus]. I used "the lander ran
`sase plan propose`" as a proxy for "it found remaining work". That rate hardly moves
with pairing, but it moves a lot with the lander's vendor:

| Lander | Pairing | Epics | Proposed remaining work |
|---|---|---|---|
| Claude | cross / mixed / same | 37 / 96 / 5 | 24% / 23% / 20% |
| Codex | cross / mixed / same | 14 / 59 / 60 | 57% / 61% / 68% |

- This is a proxy with small cells. It cannot say whether Codex landers catch more real
  problems or over-flag (the pattern both papers warn about).
- Either way, **who reviews** matters far more than **whether the vendor differs**.

*Two more points:*
- The land agent (`bd/land_epic`) verifies, integrates and writes code. It is not a pure
  reviewer, so the Xiang rewrite-regression mechanism applies directly when a lander
  "fixes" phase work.
- A hard filter also works against `decisions:size-alias-effort-ladder`, which keeps
  every alias multi-provider so that one vendor's outage is not a total outage.

**Fix:** see Revised bottom line 3(c). The lead's own proposal to "record the provider
pair" is already possible: `agent_meta.json` stores `llm_provider` for every run, so the
analysis can be done retrospectively now.

**Effect:** the Stage 1b headline changes from "cross-vendor review" to "measure, then
route by capability". The overall conclusion is unchanged.

### Major

**M1. Stage 1a is ranked by how often `%wait` is used, not by evidence that waiters need
more context.** It appears in *§1 item 2*, *§3.2 "What this changes"* and *§6.3 1a*
("serves the 44%").

[corpus] The 44% figure reproduces (2,195 of 5,043 prompts). Its make-up:
- **Epic-generated:** 1,243 (57%) are epic phase and land prompts, which mostly read bead
  notes, landed code and artifacts.
- **Research swarms:** 136.
- **The other 816:** mostly `#gh`/`#split_file` serialization chains. Only **9** of them
  also `#fork`.

How often waiters use the waited-for agent's output:
- Only 43 waiter runs (2%) pull a transcript with `sase chat show`.
- `wait.chats`/`wait.artifacts`/`wait.replies` template references appear in 28
  prompts, all of them research prompts.

`%wait` is mainly an **ordering barrier**. The corpus supports the failure-policy half of
1a (79 parked notifications), not the reply-body half.

**Fix:** split 1a and promote the failure policy (Revised bottom line 3(a), 3(e)). The
lead's 1a kill criterion ("fewer `sase chat show` pulls") starts from a baseline of 2% of
waiters, which is a sign that little demand exists.

**M2. Stage 2's acknowledgment design misses every turn that ends through a handoff.**
It appears in *§5 (Acknowledgment row)* and *§6.4* ("carry acks in the `/sase_final`
declaration, which every agent already submits").

- Core memory exempts successful plan, monitor, pipe and questions handoffs from
  `/sase_final`, and gate or launch-request handoffs also end the turn.
- [corpus] Up to 55% of runs (2,632 of 4,823) invoked such a command. This is a
  string-match upper bound; monitors are 1,352 and `sase plan propose` 1,164.
- `family_channel_delivery` already said: "An intentional pipe/monitor/gate handoff
  should record receipt before termination."

**Fix:** acknowledgment is a field on *every* turn-ending path. A crash, or a handoff
without it, leaves the batch included but unacknowledged.

**Effect:** implementation correctness only. It does not change the staging.

**M3. The lead dropped continuation-ownership repair.** It is absent from *§6* and the
*Recommended solution*.

- mus makes it a parallel Phase 1 item.
- `family_channel_delivery` says supervision chains died at LaunchApproval handoffs
  because nothing owned the next action, and that "reliable messages cannot keep an
  unscheduled sequence alive". It recommends fixing this even if channels are rejected.

**Fix:** Revised bottom line 3(b).

**Effect:** it adds a cheap, evidence-backed Stage 1 item. Without it, Stage 2's
steering trial repeats the `016` failure.

**M4. Stage 3 misses the runner-owned stdin path, and the March history is misread.** It
appears in *§3.1 "A mid-run steering feature…"*, *§3.3 consequence 2*, *§6.5* and *§7
decision 1*.

*Stdin* [V]:
- Claude Code's SDK docs say a regular message sent while a turn is running is "pick[ed]
  up … between tool calls", and "the turn answers the picked-up message from then on".
- The CLI's `--input-format stream-json` queues messages.
- SASE's runner is Claude's parent and already owns stdin. It writes the prompt and then
  closes the pipe [code].
- Keeping stdin open gives mid-turn delivery inside one provider turn. It needs no
  socket trust or `crossSessionInbound` setting, and it is unaffected by `refuse`.
- "The host cannot use the socket" is true, but it doesn't matter.
- [inferred] It still needs a spike test: how stdin interacts with SASE's `result`
  handling and the wait-continuation `--resume` loop.

*History* [code]:
- `739196a9c` (the March `m` key) killed the provider process mid-tool and restarted
  with the **same** session ID ("Claude provider: interrupt-resume loop reuses session
  ID").
- The fresh-session behaviour the lead describes (`active_session_uuid = None`) arrived
  in `bdda3bdf1` on **2026-09-15**, six months after the key was removed. It cannot be
  the reason for the removal.
- The removal plan (`plans/202603/remove_agents_m_keymap.md`) frames the change as
  ending the `m` key's "double duty" between marking and messaging. It gives no quality
  reason.

**Fix:** reword decision 1. The March design's known defect was killing in-flight tool
calls. Stdin delivery between tool calls avoids that defect.

**Effect:** makes Stage 3 cheaper and removes a misleading argument against it. The
evidence gate stays.

**M5. The delegation reply join (1c) may already be composable today.** It appears in
*§3.1 "Delegation has no reply join"* and *§6.3 1c*.

- The `/sase_run` skill documents:
  - multi-prompt requests (`---`, one slot per segment);
  - `%wait` inside requested prompts;
  - family attach (`%i(<suffix>, family=parent)`);
  - `terminal_handoff`.
- One request could therefore contain the helper plus a successor in the requester's
  family that waits on the helper. That is two requester-side turns, not the lead's
  three-turn chain with a monitor.
- [inferred, untested] Known gaps: a failed helper parks the successor, and a rejected
  request never resumes the requester.

**Fix:** ship this as a documented recipe first, and measure use. Build the runner mode
if people use the recipe, to fix those gaps.

**Effect:** a cheaper Stage 1c that respects the "mechanism follows corpus" spirit.

### Minor

**m1. The Stage 0 rationale is partly wrong, and `sase-163` inherits it.** It appears in
*§3.3 "A related hazard"*.

What the docs say [V] ([headless](https://code.claude.com/docs/en/headless),
[env-vars](https://code.claude.com/docs/en/env-vars),
[settings reference](https://code.claude.com/docs/en/settings-reference)):
- "If Claude starts a background subagent or workflow, `claude -p` … stays open until
  that work completes." The wait is capped at 10 minutes
  (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`).
- A `Monitor` watch keeps feeding output mid-conversation for up to 10 minutes in `-p`.
- `refuse` also refuses the session's *own* hook and Bash socket posts.
- A stricter project or local `crossSessionInbound` value overrides `--settings`.
- An unrecognised value falls back to `hold`.
- Peer messages appear on the stream-json output as `origin.kind: "peer"`.

In practice the results are lost because SASE submits its final declaration last and a
watchdog (`68d9e0f65`) terminates the provider 120 s after the declaration is accepted
[code].

**Fix:** correct the rationale and add the env switches (Revised bottom line 2). The
recommendation itself is unchanged.

**m2. Several rows of the evidence table are stale or loose.** It appears in *§4*. [V]
- **Google:** v3 of arXiv 2512.08296 relabels 17.2×/4.4× as *trace-level*
  (computational) amplification. Task-level amplification is only ≈1.1–1.3×.
  - More relevant to SASE: on SWE-bench Verified, every multi-agent variant did worse
    than a single agent (independent −14.9%, centralized −3.1%).
- **Anthropic Frontier Red Team:** the post doesn't use the phrase "premature consensus".
  - Its 266 vs 21 vulnerability comparison is confounded by different search scopes and
    about 4× the tokens. `family_channel_delivery` already flagged this.
- **Cursor:** agents became risk-averse because there was "no hierarchy", not because of
  optimistic concurrency.
  - Cursor also found a dedicated integrator role "created more bottlenecks than it
    solved". That tempers rule 2's reliance on integrators, though SASE's per-epic
    lander runs after the work, not during it.

None of these reverses a conclusion.

**m3. Mentors are dormant by the user's choice.** This affects *§3.2* and *§7 decision
3*.
- `21da671e2` (2026-08-09) removed `mentor_profiles` from `sase/sase.yml` as "obsolete /
  old", the same day the last mentor completed [code].
- So decision 3 should be "*why* were mentors retired?" If they were noisy or
  low-value, that is SASE-local evidence to weigh before investing in automated review
  loops.

**m4. The "latent demand for sibling awareness" reading is unsupported.** It appears in
*§3.2*.
- The sampled phase-worker `ListAgents` call was made with no input, in the middle of
  reading tests, with no coordination intent visible [corpus].
- Treat the 75 calls as tool curiosity, not demand.

**m5. "All three reports agree" is overstated.** It appears in *§1 item 1*.
- gem proposes in-turn `sase channel read/post` and clan channels, so that concurrently
  running siblings see each other's notes. That is pull-based live exchange.
- The lead records the disagreement in §5, but the bottom line hides it.

**m6. Two scoping gaps.**
- `decisions:corpus-before-mechanism` is scoped to memory retrieval and recall
  machinery. Using it for collaboration features is an analogy, not the decision.
- The Stage 2 turn-end successor rule does not close the "pending message but the family
  is dead" gap. The lead's §6.4 table says it does, but a message that arrives after the
  family's last shell ended still just sits there.

**m7. Missed prior art.** The source is [Carlini, "Building a C compiler with a team of
parallel Claudes"](https://www.anthropic.com/engineering/building-c-compiler), Feb 2026
[V].
- **Setup:** 16 agents, each with its own clone. They claimed tasks by writing lock files
  to a shared git repo. There was no orchestrator and no inter-agent messaging.
- **Result:** merges were "frequent" but manageable. The failure case was every agent
  hitting the same bug, which was fixed by using an oracle to split the work.
- This supports P5's "disjoint assignment plus a strong test oracle, no peer talk".
- It also shows that *task-level* claims work. SASE's bead claims already provide them,
  which is consistent with rejecting *file* leases.

---

## Verified claims

These are the load-bearing claims I re-checked and found sound.

**Code** [code, at `8246e8286`]:
- **Claude launch flags** (`claude.py:412-427`):
  - `claude -p … --dangerously-skip-permissions --disallowedTools ScheduleWakeup`;
  - `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (`:527`);
  - no `crossSessionInbound`.
  - This session also has `CLAUDE_CODE_MESSAGING_SOCKET` set, on Claude Code 2.1.278.
- **Clan waits** (`run_agent_refs.py`): for a clan, `wait.chats` resolves only the newest
  successful member, while the producer directories (`wait.artifacts`) span every
  successful member.
- **`/sase_run`** (`sase_run.md`): `resume_requester` fires when the gate settles, not
  when the child finishes.
- **Mentors:** `MentorConfig` has no model field.
- **Epic land model:**
  - `epic_lander_model: "@large"` and `big_epic_lander_model: "@xlarge"`;
  - `docs/beads.md` says `-m` on a plan bead sets the land model;
  - `select_epic_land_model` is in `sase-core` (`model_route.rs:92`).
- **Deferred expansion:** `LAUNCH_DEFERRED_XPROMPT_NAMES = {"fork"}` (`processor.py:80`).
- **Wait parking:** `%wait` releases only on `completed` and otherwise parks, with a
  `wait_checks` notification (`docs/xprompt.md:2329-2342`).
- **Interrupt history:** commits `739196a9c` and `1a46198f1`; the provider-side
  interrupt consumer is still live.
- **Task bead:** `sase-163` exists and matches §6.2.

**Corpus** [corpus]:
- `%wait` in 44% of prompts.
- 1 `SendMessage` call.
- 75 `ListAgents` calls.
- 79 "can never self-resolve" notifications.
- Run and prompt totals within a few runs of the lead's.

**Primary sources** [V]:
- **Claude Code cross-session messaging:**
  - `-p` binds an inbox; bare mode doesn't;
  - messages are read "between tool calls";
  - a bypass session delivers only from a bypassing sender, otherwise holds, and the
    hold expires after 5 minutes in `-p`;
  - `accept`/`hold`/`refuse`, with `--settings` outranking user settings;
  - denying `SendMessage` also removes subagent messaging;
  - own-child delivery applies only when no value is set.
- **Hooks:** `PostToolUse` supports `hookSpecificOutput.additionalContext`; hooks run in
  `-p`; hook entries merge across settings sources.
- **Agent teams:** no teammates in `-p`; teammates share one working tree.
- **Xiang et al.:** the numbers are exact (with the context in C1).
- **Anthropic, 2026-01-23:** "telephone game"; "3-10x more tokens"; verification
  subagents sidestep it.
- **Cognition, 2026-04-22:** "writes stay single-threaded …"; reviewer and coder share no
  context.
- **Cursor:** 20 agents fell to the throughput of 2–3 under locks.
- **Codex:** `turn/steer` needs `expectedTurnId`; openai/codex#40805 is still open.
- **MCP SEP-1686:** the "claiming to be 'waiting'" quote is exact.

---

## Synthesis check

- **Dropped:**
  - mus's continuation-ownership repair (M3).
  - mus's list of cheap continuation bugs (Codex's stale "no session persistence"
    rebuild; drain discarding in-flight progress). Only the Claude interrupt made it
    into the lead's report.
  - cld's merge-conflict evidence (Xu et al.: cross-agent PR pairs conflict 41.7% vs
    19.8%) and its C-compiler source (m7). Both bear on P5.
- **Misrepresented:** the consensus claim (m5).
- **Settled without evidence:**
  - The acknowledgment compromise was chosen over cld's CLI or final-declaration option
    without checking which turns submit a declaration (M2).
  - The cross-vendor direction was left to "record pairs" even though the pairs already
    exist (C1).
- **Handled well:**
  - The lead correctly rejected gem's auto-ack, newest-first truncation, leases and
    capsules.
  - gem's unsupported claims did not make it into the recommendation: the "80% fewer
    merge conflicts" figure and the attribution of forum findings to Anthropic.
- **Stated as settled but still open:** the 8 KiB budget is openly left as a
  hypothesis.

---

## Open questions

| Question | What would settle it |
|---|---|
| Does cross-vendor (or stronger-model) landing reduce post-land defects on SASE's workload? | A retrospective join of the 282 epics' `agent_meta.json` vendor pairs with outcome signals: follow-up bug beads citing the epic, reopened phases, CI failures within N days. Then check a sample of Codex- and Claude-lander remediation plans for real versus spurious findings |
| Why were mentors retired on 2026-08-09, and why was the `m` key removed in March? | The user. Both answers change whether review loops and mid-turn steering deserve investment |
| Does a stdin-owned `--input-format stream-json` session deliver runner messages mid-turn under SASE's runner? | A spike: keep stdin open, inject one message after the first tool result, and confirm it appears between tool calls and in the `result`'s picked-up UUID list, with the wait-continuation loop intact |
| Does the multi-prompt `/sase_run` reply-join recipe (M5) work? | `sase xprompt expand` on the composed request, then one live helper round-trip |
| How many turns end without `/sase_final`? | An exact count from finalizer artifacts per run (declaration present vs handoff), to size the acknowledgment paths in M2 |
| Is there a real steering workflow to trial Stage 2 against? | The user (the lead's decision 4 stands) |
