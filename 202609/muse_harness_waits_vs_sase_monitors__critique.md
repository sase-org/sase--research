# Critique: Muse Harness Waits vs `sase monitor` (202609)

Reviewer: Muse Code powered by Meta Muse Spark (model review, not telemetry rerun).
Date: 2026-09-23.
Source under review: `research:202609/muse_harness_waits_vs_sase_monitors.md`
("the report"), researcher `0q8`, written against sase `02cd6b69e` and Muse Code
`1.3.0-R3401.1`.
Prior report: `research:202609/provider_wait_contract_early_exits/provider_wait_contract_early_exits.md`.
Code checked against this workspace checkout (post-`02cd6b69e`; spot-checks only,
all consistent unless noted).

## Verdict

The report's bottom line stands: ban Muse's post-turn harness wait, make Muse run
synchronously, and route work that can exceed the synchronous ceiling to `sase
monitor` up front. Its decisive new evidence — the managed-`bash` 300 s clamp vs.
the legacy-`shell` 600.1 s hard kill with output discarded — correctly reframes the
prior report's "embrace the wait" recommendation as unworkable, and the 600 s
up-front routing line (155 commands, 0.9%, in 29% of Muse sessions) is the right
granularity instead of "monitor everything Muse backgrounds."

Adopt the plan with the adjustments below. The most important corrections are:
(1) do not build predictive refusal in `sase tool run` on duration distributions —
use declared duration classes per recipe; (2) do not run the Phase 0 canary on the
live fleet without the directive; (3) ban the capability with a `run.toolset`
allowlist, not just the `--enable-shell-tool` flag; and (4) measure verification
pass rates before claiming prepared completion "costs less than waiting," since
that claim is conditional on green.

## What the report gets right (spot-verified)

- **No Muse directive, no guard.** `src/sase/llm_provider/muse.py` sets only
  `MUSE_NO_AUTO_UPDATE` (lines ~74, ~287, ~502) and has no prompt prefix; the
  extra-args hatch (`SASE_MUSE_LARGE_ARGS` / `SASE_MUSE_SMALL_ARGS`) the report
  cites for the canary exists. `claude.py` has the directive, `_WAIT_SIGNAL_RE`,
  `_WAIT_CONTINUATION_NUDGE`, `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` and 4 h
  `BASH_MAX_TIMEOUT_MS` (~lines 44–110, 428, 499, 531–532). The asymmetry claim
  holds.
- **Watchdog is declaration-blind.** `start_completion_watchdog` /
  `_tear_down_stalled_provider` in `_subprocess_plain.py` with the 120 s grace
  (`DEFAULT_TEARDOWN_GRACE_SECONDS = 120.0`) matches the mode-A mechanism.
- **No detach/join in `sase tool run`.** `src/sase/main/parser_tool.py` (219 lines)
  has no detach/handoff/join path — mid-flight adoption really does mean
  kill-and-rerun today.
- **`shell` has no display path.** `_tool_call_muse.py` maps only `"bash": "Bash"`
  (~line 67) with `command`/`description` extraction gated on `bash` (~line 301);
  a `shell` tool call will render raw unless the parser fix lands. Correct catch.
- **Prepared completion exists and is unused.** `docs/monitors.md` documents the
  `-f` / prepared-completion and `--next` semantics the report relies on
  (e.g. `sase monitor start -p verify -f '<intent-ref>' -- just check`).
- **Skill/memory quotes are accurate.** `sase_final.md` lists "I will wait"
  responses as valid endings; `sase.md:77` echoes it; `lint_and_test.md` says
  "hand it to a monitor … whenever it is taking a long time." The report's
  rewrites target the right lines.
- **Single-turn reopen condition.** `decisions:single-turn-agents` reopens only on
  "a true suspend/resume primitive that preserves workspace claims and provider
  budget." The report is right that Muse's keep-alive wake does not meet it, and
  right not to supersede the decision.
- **Method honesty.** §6 discloses the single-run basis for parts of the 600 s
  claim, the unmeasured pass rates, and the indicative-only next-turn token
  comparison. That disclosure is what makes this critique possible instead of
  necessary.

## Critique and gaps

### 1. The 600 s fixity claim is under-evidenced for the weight it carries

Everything downstream (routing line, directive text, refusal threshold) assumes
600 s is fixed and universal. The evidence is one 35-minute loop killed at
600.1 s plus absence-from-binary-strings, while the report itself notes unknown
`run.*` keys are silently ignored (so probes prove nothing) and leaves
`TBH_EVAL_APPEND_DEVELOPER_PROMPT` and `exec --agents <JSON>` unverified. Absence
from `strings` output of a stripped Rust binary is weak evidence for "no
setting." Before encoding 600 s in a directive, a refusal gate, and success
metrics, verify: a second long run at a different payload shape, one run via
each unverified delivery path, and one run after the next Muse CLI update (the
report shows silent behavior changes arrive with updates — Sep 17 — so this
number needs a smoke test regardless; the report's §7.5 smoke test is the right
idea but should assert the ceiling value, not just tool presence).

### 2. "The model resists blocking" rests on one refusal

The `nohup … &` improvisation finding comes from a single legacy-shell run
(expL/first). One refusal may be prompt wording, not a stable model disposition.
The directive is still warranted (explicit ceilings beat improvisation), but do
not treat reluctance-to-block as an established behavior — and the pilot (§6)
should measure compliance rate across real tasks, not just timeout handling.

### 3. Predictive refusal in `sase tool run` is the riskiest Phase 2 item

Refusing a tool when "P(duration > ceiling) [is] above a threshold" on the
control plane's duration corpus has four unaddressed failure modes:

- **Bimodal recipes.** `sase tool run check` exceeds 600 s 18.9% of the time
  (report Table §2.2). Any fixed threshold either waves through most kills or
  forces ~80% of checks through monitors needlessly. The report never names the
  threshold or the false-positive budget.
- **Cold and shifted distributions.** New recipes, new machines (athena-only
  telemetry), and behavior-changing CLI updates all invalidate predictions.
- **Gaming and opacity.** A refusal that prints "run this monitor command
  instead" becomes a second scheduler agents must satisfy; its errors will look
  like mode B (cancel-and-restart by instruction) to future telemetry.
- **Boundary cost.** The report notes "put the prediction logic in sase-core"
  but not the `sase-core-revision.txt` pin move, the binding/API change, or
  tests in the linked `sase-core` checkout that the Rust boundary rule requires.

Declared duration classes (see §Better solution) dominate prediction here:
deterministic, reviewable in the tool catalog, no cold-start problem.

### 4. Phase 0 canary as specified should not run on the live fleet

"Without the directive, expect about one `sase tool run check` in five to be
killed at 10 minutes" — with all output discarded. Running that canary on athena
runners to "watch for `tool timed out`" spends real verification work and real
beads to confirm a number already measured in scratch. Run the canary in scratch
workspaces (as the report's own experiments did with scratch workspaces and
scratch `XDG_DATA_HOME`), or pair flag with directive from the start. A short
live canary is only justified to measure directive compliance, not the kill.

### 5. `--enable-shell-tool` alone is a fragile ban

The report acknowledges "legacy tool could be deprecated" yet makes the flag the
whole mechanism (Phase 1.1). A cleaner mechanical ban is the `run.toolset`
allowlist preset the report already verified (deny `bash`, `cron_*`,
`workflow`, `subagent_*`), delivered per-invocation if possible rather than via
user-owned `~/.config/muse/settings.json`. Keep the flag as the implementation,
but add the allowlist as the enforcement: if a future release drops `shell`, the
smoke test fails closed (report §7.5) and behavior reverts to managed `bash` +
in-turn discipline rather than silent resurrection of the wake. Also file the
config/flag change per `sase_flags.md` (flag bead + rollback path), which the
report mentions only in passing.

### 6. Hop-cost comparison concedes too little

Median 176 s monitor hop vs. 6.1 s wake understates the report's own case: the
wake is non-durable and invisible (dies with the provider, no host record),
while the monitor is durable and visible. The latency gap is real for mid-task
commands (~3 min + re-orientation, up to 29% of Muse sessions), but framing it
as wake-vs-hop invites "make wakes visible" (the prior report's ledger) rather
than the correct "wakes are keep-alives, ban them." The token comparison of
next turns is, as disclosed, uncontrolled for work done — it should be dropped
from future versions rather than hedged, since successors necessarily include
new work.

Slot analysis also stops early. Both mechanisms hold slot and workspace; only
the ~180 MB LLM process is freed. ADJ-5's "reserve the family's slot for the
successor" plus "stop gating on starter bookkeeping" needs a bounded lease and
an orphan story: who releases the reservation if the supervisor dies, and what
prevents family-slot exhaustion when Muse starts "several times more monitors"?
Two ~30-min re-queues in the window justify decoupling dispatch from the
starter's 77 s median post-kill bookkeeping, but the reservation itself needs a
timeout and a `sase monitor list`-visible holder.

### 7. "Costs less than waiting" needs the missing pass rate

Prepared completion costs zero additional turns on green and one recovery
successor on red. With 0/1,344 historical uses, the report has no Muse final-gate
pass rate, and it admits hop counts depend on unmeasured pass rates. If final
gates pass 90%+, the claim holds easily; at 50% the expected cost is half a hop
per gate — still likely cheaper than an 18.9% kill-with-total-output-loss rate,
but that arithmetic should be shown, not asserted. Measure `check` pass rates
from the same Sep 20–23 corpus before using this claim to prioritize ADJ-5 work.

### 8. Option 4 is dismissed faster than its evidence allows

346 in-turn `bash_input` waits in four days show Muse tolerates in-turn polling
fine; the anti-poll text belongs to managed `bash`, while legacy `shell`'s tool
text ("run a shell command subject to runtime policy") says nothing against
blocking. A Stop-hook + ceiling-chunked `sase tool wait` design (see below)
does not "fight the harness" under `shell` — it uses the harness's only mode.
Continuation cap 8 is cited as a risk but never divided into actual wait
durations (8 × ~9 min chunks ≈ 72 min covers nearly all Table §2.2 cases). Keep
option 4 as fallback, but recognize its modern form overlaps the E2 end state
rather than contradicting it.

### 9. Transition semantics are unspecified

During any flag/directive rollout, some runners use `bash` (background at
300 s) and some use `shell` (kill at 600 s). The routing rule "600 s, decided
up front" is wrong for the former fleet half. State the mode-conditional rule
explicitly (`bash` runners: expect backgrounding past ~10 s, never end the turn
to wait; `shell` runners: 600 s ceiling), or cut over atomically per host.
Relatedly, `timeout 540` wrapping advice should say where it applies: useful
for uncertain-length `shell` commands to preserve evidence, but it interacts
with `sase tool run`'s own output retention (`sase tool show RUN -l`) and must
not be applied inside recorded recipes without updating their declared argv.

### 10. Small correctness notes

- Dropping `| tail` piping (lint_and_test rewrite) and adding `tail -n 80 <log>`
  after `timeout 540` are consistent, but say so explicitly or agents will read
  a contradiction.
- The stranded-wait guard "port" assumes Muse has a reconstructed-context
  re-invoke path equivalent to Claude's; verify before estimating it as small.
- The §7 metrics table sets "Muse `bash_input` cancel/terminate calls → 0 (tool
  removed)" — under `shell`, `bash_input` may be gone, but `nohup/&` workarounds
  produce equivalent stranded work; track "runs ending with wait claims" (also
  in the table) as the primary metric, not tool-name counts.
- Memory/skill edits go through `/sase_memory_write` authorization; the report
  notes this but Phase 1 should sequence the decision record (ADJ-4 companion)
  before the skill text that cites it.

## A better solution

Keep the report's option 3 as the near term and option 5 (E2 detach/wait/join)
as the end state, with these substitutions:

1. **Ban by allowlist, flag as implementation.** Deliver a `run.toolset`
   allowlist per invocation where possible (deny background-capable tools),
   keep `--enable-shell-tool` as the current mechanism, and gate both behind a
   flag bead with rollback. The smoke test asserts ceiling value and tool
   absence, failing closed to managed-`bash` discipline if `shell` disappears.
2. **Route by declared duration class, not predicted P(overrun).** Add a
   duration class to the tool catalog per recipe (`short` / `long` /
   `unbounded`, with the evidence corpus as calibration, not gate). `sase tool
   run` refuses `long`/`unbounded` recipes when the caller's ceiling
   (`SASE_PROVIDER_SYNC_CEILING_SECONDS`) is below the class floor and prints
   the prepared-completion or `--next` invocation. Deterministic, reviewable,
   no cold-start problem; prediction can later tune classes offline.
3. **Recover in-turn waits with ceiling-chunked host waits.** As the first E2
   slice, ship `sase tool wait <id>` that blocks for less than the provider
   ceiling and returns status plus tail, so 10–60 min commands need no hop when
   the agent can poll across calls under `shell`. Escalate to
   `sase monitor start --join <id>` only when a Stop hook observes pending work
   at turn end or the agent declares a long/unbounded wait up front. This keeps
   the up-front decision (no cancel-and-restart) while removing the up-front
   guess for the common uncertain-length case — the one thing the Muse harness
   did better.
4. **Bound every reservation.** Slot/family reservation for successors carries a
   lease with a visible holder and automatic release; dispatch decoupling ships
   with it, not before it.
5. **Land classification before enforcement.** Ship `sase-12s`
   (provider-neutral incomplete classification: assigned bead still open plus
   wait claim or missing declaration ⇒ incomplete, never success) before or
   with the ban, so any transition kills stop masquerading as SUCCESS. Keep the
   watchdog as-is after the ban (the report is right that "alive 120 s after
   declaration means hang" becomes true again) and drop the ledger.
6. **Measure the two missing numbers first.** Final-gate pass rate (for the
   prepared-completion cost claim) and directive compliance / `shell` model
   quality on real tasks (the pilot). Both come from existing corpora plus a
   scratch-only pilot — no live canary required.

Why this is better: it replaces the two fragile elements (a flag that upstream
can remove, a prediction gate that misfires on the commonest recipe) with two
durable ones (an allowlist that fails closed, declared classes that are
reviewable), and it removes the up-front-guess cost that is the strongest
argument against the report's routing rule — without reviving the harness wait.

## Recommended changes (concise list)

1. Verify 600 s fixity with two more runs (different payload, one unverified
   delivery path) and assert the ceiling value in the CLI-update smoke test.
2. Do not run the Phase 0 canary on the live fleet without the directive; use
   scratch workspaces or pair flag with directive.
3. Enforce the ban with a `run.toolset` allowlist in addition to
   `--enable-shell-tool`, behind a flag bead with rollback; fail closed if
   `shell` disappears.
4. Replace predictive `sase tool run` refusal with declared per-recipe duration
   classes; keep the duration corpus as calibration only, and handle the
   sase-core boundary (binding, tests, revision pin) if any logic moves there.
5. Measure final-gate pass rates from the Sep 20–23 corpus before claiming
   prepared completion is cheapest; show the green/red expected-cost arithmetic.
6. Bound successor slot reservations with a lease, visible holder, and orphan
   release; ship dispatch decoupling together with the lease.
7. Ship ceiling-chunked `sase tool wait` as the first E2 slice so uncertain-length
   commands need no up-front guess; keep full detach/join as the end state.
8. State the transition's mode-conditional routing rule (300 s backgrounding vs.
   600 s kill) or cut over atomically per host.
9. Clarify `timeout 540` + `tail -n 80` vs. the `| tail` pipe ban, and scope
   `timeout` wrapping to unrecorded commands unless recipe argv is updated.
10. Verify the Muse reconstructed-context re-invoke path before estimating the
   stranded-wait guard port; track "runs ending with wait claims" as the primary
   success metric rather than tool-name counts.
11. Sequence the ADJ-4 companion decision record before the skill/memory edits
   that cite it, via `/sase_memory_write`; land `sase-12s` incomplete
   classification with or before the ban.
