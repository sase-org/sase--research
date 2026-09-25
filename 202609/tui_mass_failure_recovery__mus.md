# TUI mass-failure audit and recovery UX — researcher mus

Date: 2026-09-25 (EDT). Scope: the failure ~30–60 min before ~16:45 EDT that took
down all sase agents from the operator's point of view and the manual restart
that followed. All times below are EDT (`~/.sase/logs/tui.log` timestamps).
Evidence is from host logs and the live tree; where I infer rather than observe,
I say so.

## 1. What failed

Two TUI crashes with the same signature, ~75 min apart:

| Time | TUI pid | Error |
|------|---------|-------|
| 15:08:10 | 124854 | `ValueError('agent scan wire schema mismatch: got 10, expected 9')` |
| 16:20:56 | 1670985 | `ValueError('agent scan wire schema mismatch: got 9, expected 10')` |

Both are logged as `ERROR sase.ace.tui.app: Unhandled exception in sase's TUI`
(`textual.worker.WorkerFailed`), each followed within seconds by 5–6 s
event-loop / message-pump stall warnings and then
`TUI exiting with live worker threads`. Only 2 occurrences of
`schema mismatch` exist in the current `tui.log`
(`grep -c` = 2), so this is not a chronic crash — it is two discrete skew
events, and the 16:20 one is the incident under audit (the "30–60 min ago"
failure; the 15:08 one is a prior instance of the same class).

Strictly, **the agents did not all fail — the TUI did**. The agent-scan worker
threw, the exception escaped to the Textual app boundary, and the whole TUI
exited. From the operator's chair that is indistinguishable from "all agents
failed": no Agents tab, no statuses, no kill/restart path. The `sase agent
list` taken during this research shows agents still `RUNNING`/`WAITING`
afterwards, consistent with the runners surviving while the control surface
died.

## 2. Root-cause analysis

The throwing check is the strict equality gate in
[src/sase/core/agent_scan_wire_conversion.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/core/agent_scan_wire_conversion.py:485)
(`agent_scan_wire_from_dict`): any scan payload whose `schema_version` differs
from `AGENT_SCAN_WIRE_SCHEMA_VERSION` raises `ValueError`. Current tree value
is 10
([records module](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_48/src/sase/core/agent_scan_wire_records.py:28)).
Notably, the module docstring in the conversion function itself says unknown
keys are dropped "so a newer writer … never crashes an older reader" — but the
schema-version gate above it does exactly that crashing, so the tolerant-field
design is defeated by the intolerant version check.

Why the flip (`got 10, expected 9` then `got 9, expected 10`)? That symmetric
reversal is the fingerprint of **version skew between concurrently running
sase copies**, not a single bad upgrade:

- The 16:20 traceback loads code from the `sase_24` workspace checkout;
  post-restart tracebacks (16:42+) load from `/home/bryan/projects/github/...`.
  Two different checkouts served the TUI within the same hour.
- `sase version` reports host `0.17.1+1456 … .dirty` against
  `sase-core-rs 0.34.73`, i.e. a dirty dev tree where Python and Rust-core
  revisions move independently (the `sase-core-revision.txt` pin,
  currently `2457913…`, is exactly the mechanism that is supposed to keep them
  in lockstep — see `docs/rust_backend.md`).
- Stale scan artifacts are a second skew source: the scanner also rehydrates
  on-disk marker/index payloads, so a payload written by a newer (or older)
  sase and read after a checkout switch trips the same gate.

Confidence: high that the crash mechanism is the strict schema gate killing the
scan worker and hence the TUI; medium that the specific skew came from mixed
checkouts (`sase_24` vs `projects/github`) plus a mid-session upgrade, since I
did not capture the Rust-side writer version at 16:20. Either way the
robustness conclusion is identical: a read-path version difference must not be
fatal.

Contributing factor: no error boundary. The scan runs in a Textual worker whose
failure propagates to `app.py`'s unhandled-exception handler — there is
evidently no catch-and-degrade around the Agents-tab scan (contrast the stall
watchdog, which only observes and logs). One bad payload therefore kills every
tab, not just the agent list.

## 3. Rectification audit (what the operator did)

Observed recovery footprint, consistent with "restarted all affected agents":

- TUI relaunched after the 16:22 exit (new TUI activity resumes in logs by
  ~16:42 from the `projects/github` checkout; screenshot-export errors after
  that are benign convergence timeouts, a separate known flake).
- A burst of fresh artifact dirs under
  `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/25/` at
  16:21:43–16:27, and the live `sase agent list` shows this very research swarm
  (`research.2k.*` on muse/claude/grok/codex/gemini providers) `RUNNING` with
  1–3 min durations — i.e. the operator relaunched the affected work from
  stored prompts within minutes of the crash.
- `~/.sase/recent_dismissed_agent_groups/` shows dismissal-group snapshots at
  15:34/15:35/16:07 (the 16:07 group records 1 top-level agent, 6 refs, 4 DONE
  / 2 FAILED) — cleanup of the earlier 15:08 crash's fallout.

What it cost the operator: every step was manual and per-agent — discover the
TUI is dead (no signal distinguishes "TUI crashed" from "agents failed"),
restart the TUI from a shell, re-derive which agents were live, and
`agent restart` each by name (a command that **deletes the previous run's
artifacts**, keeping only the chat transcript, and asks for confirmation on
live agents — exactly the wrong defaults when you are bulk-recovering from a
platform crash rather than intentionally replacing one run). There is a
`--dry-run` preview but no bulk, no "restart all failed", and no session
restore.

## 4. Recovery-UX options for the TUI

Constraints any option must respect: single-turn agents (never block the TUI
on a gate), restart destroys artifacts today, and the Agents tab already owns
per-agent restart/kill/drain/revive plus dismissal-group records — the gap is
entirely *mass-failure* handling.

**Option A — Degraded scan mode (don't crash on skew).** On schema mismatch,
keep the TUI alive: render the last-known agent snapshot, mark it stale, and
show a banner naming both versions and the suspected cause (mixed checkout /
core drift). Downgrades a fatal crash to a readable warning. Small change
(try/except at the scan-worker boundary + banner widget), but alone it leaves
recovery just as manual.

**Option B — Crash-to-recovery screen.** A top-level exception boundary that,
instead of exiting, replaces the view with: what died, the log excerpt, and
one-key actions (Reload TUI, Restart failed agents, Copy diagnostics). Handles
*all* worker-fatal crashes, not just scan skew. More machinery (needs to work
when the app is half-dead), and Textual teardown semantics make "stay alive
after an unhandled exception" genuinely tricky.

**Option C — One-key bulk recovery in the Agents tab.** "Restart all failed /
all in session" with a single preview list and one confirmation, reusing the
existing `restart` planner per agent. Directly attacks the operator's actual
toil in §3. Risk: bulk-confirmation UX must stay honest about artifact deletion
(see Option E); otherwise it becomes a foot-gun.

**Option D — Health pill + diagnostics drawer.** Persistent status indicator
(host/core/schema versions, last scan error, stall state) with a drawer showing
`sase version`-equivalent info inside the TUI. Cheap, improves diagnosis ("am
I looking at skew?"), but recovers nothing by itself.

**Option E — Non-destructive restart + session restore.** A restart mode that
preserves the prior run's artifacts (or archives rather than deletes) and a
"reopen last session" action after a TUI restart that re-subscribes to
previously visible agents. Removes the scariest part of today's recovery, but
touches lifecycle invariants (artifact ownership, name registry) — the largest
change here.

## 5. Recommended solution

**Recommend Option A + Option C as one feature: a failure-recovery mode for
the Agents tab.** Concretely:

1. The scan worker catches wire-schema (and only wire-schema) mismatches and
   enters recovery mode instead of raising: last-known agent list stays
   visible, badged stale, with a banner stating got/expected versions and the
   likely cause (mixed checkout or core drift, with the two checkout paths when
   known).
2. The banner's primary action is **"Recover agents"**: one preview listing
   every non-terminal agent from the stale snapshot, one confirmation, then the
   existing per-agent restart planner runs over the set — with the confirmation
   text explicitly stating the artifact-deletion consequence (the Option E
   concern, surfaced rather than solved).
3. Secondary actions: "Reload TUI" and "Copy diagnostics" (versions + log
   tail), covering the immediate needs Options B/D serve for this failure class
   without building a general crash-screen framework.

Why this pair: A alone leaves the operator's toil untouched; C alone is
unreachable in exactly this incident (the TUI is dead, so no Agents tab exists
to host the bulk action). Together they convert today's outcome — silent death
followed by manual per-agent resurrection from a shell — into: TUI visibly
degraded but alive, cause stated, and recovery one confirmed action. B (general
crash screen) is the right fast-follow for non-scan fatals; E (safe restart)
is the right deeper fix for the lifecycle hazard but is too large to gate
recovery UX on.

Verification note: I confirmed the crash signature, the strict-gate code, the
schema-version constant, the relaunch footprint, and current per-agent restart
semantics (`restart --help`: deletes artifacts, keeps transcripts) in-session.
I did not reproduce the skew live (would require running two schema versions)
and did not inspect any peer swarm reports.
