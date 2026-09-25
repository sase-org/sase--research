# The 2026-09-25 Fleet-Wide Agent Failure: Audit and TUI Recovery UX (cld)

- **Date:** 2026-09-25, written 16:45–17:15 EDT. All times below are EDT (UTC−4) unless marked `Z`.
- **Researcher:** `research.2k.cld` (1 of 5 in a swarm). I did not read any peer report.
- **Scope:**
  1. Audit the failure that took down SASE agents on athena that afternoon.
  2. Audit the actions you took to recover.
  3. Explore TUI UX options that would make this class of failure easier to recover from.
  4. Recommend one.
- **Evidence:** local logs, artifacts, git reflogs, shell history, notifications, and transcripts on athena. The full index is in the Appendix.

---

## Bottom line

1. **Root cause: SASE ran a sase-core build its own Python did not understand.**
   - sase-core `2a0fc2a` (`feat(core)!: canonicalize agent-session contracts`, bead `sase-17m.8`) bumped several wire schemas. The agent-scan wire went from 9 to 10.
   - The sase-side mirror bump belonged to a later bead, `sase-17m.9`, which was still `IN_PROGRESS`.
   - At 15:02:44 a TUI-initiated dev update fast-forwarded the linked sase-core checkout to `origin/master` and rebuilt `sase_core_rs` from source.
   - It ignored the host's `sase-core-revision.txt` pin, which was still `c31b8cf`.
   - From 15:06:22, every Python path that parses an agent scan raised `ValueError: agent scan wire schema mismatch: got 10, expected 9`. That included the TUI, the `sase agent` CLI, scheduler chops, and agent runner bootstrap.
2. **Nothing between the build and the restart checked compatibility.**
   - The update's only post-install check is `import sase_core_rs`.
   - ACE restarted itself onto the skewed build at 15:07:48 and crashed 22 seconds later.
   - The recovery console was one of the first casualties: `sase tui` was unusable from 15:08 to 15:33.
3. **Blast radius:**
   - 9 agent launches died in bootstrap before any provider turn ran.
   - 1 agent (`sase-19o.1`) failed after its commit landed. Its agent publication hit a second core bug in the artifact-index migration.
   - 14 "Wait dependency can never self-resolve" notices fired.
   - 59 scheduler job failures were recorded across three axe digests.
   - The core fix was pushed at 16:09:18, so the outage lasted **about 63 minutes**. Primary-install processes (TUI, scheduler) recovered at about 15:32, when uncommitted mirror edits landed in the editable checkout.
4. **Your recovery worked, but it was manual, spread across many tools, and partly risky.**
   - You spent about 25 distinct actions across the TUI, zsh, tmux, raw git, `rm`, a CLI bead relaunch, and an out-of-band Claude Code session.
   - Two actions deserve scrutiny:
     - `rm -rf sase_14` at 15:37:52. The workspace ledger shows #14 had been re-claimed by the newly launched `0sc--plan` at 15:35:23.
     - `sbd work … -Y`. It wiped (and, for waiting members, killed) then relaunched 21 epic agents from their bead prompts instead of replaying the failed turns.
   - At least one casualty is still open: `0rv.w0.f0.w0` has been WAITING on a dependency that can never resolve.
5. **What made recovery hard:**
   - The failure had no single identity. One root cause surfaced as more than 80 separate recorded signals (10 agent-failure notices, 14 wait notices, 59 digest entries), plus toasts and a TUI crash.
   - There was no way to roll back.
   - There was no pause on admissions, so waits kept releasing agents into a broken runtime.
   - The existing retry primitives are per-agent (`R`, `,x`) or per-epic (`sase bead work`), not per-incident. `R` also changes agent identity, which breaks clan and bead waits.
6. **Recommendation: an Incident Recovery layer with four parts.**
   - **Safety net:** a pre-swap skew probe, last-known-good rollback, and a post-restart probe in the update flow.
   - **Safe mode:** the TUI starts in a degraded mode instead of crashing when core and Python disagree.
   - **Incident banner and Recovery panel:**
     - Failures are clustered by signature.
     - A preview-then-confirm **Replay affected** action replays bootstrap failures verbatim with the same name, workspace, and continuation checkpoint.
     - Invalidated waiters are re-armed.
     - The incident's notifications are resolved in one step.
   - **Admission circuit breaker:** new launches are parked automatically when bootstrap failures with the same signature pile up.
   - Build it in that order. Against today's timeline:
     - The safety net alone would have prevented the outage.
     - Safe mode plus rollback alone would have limited it to about 5 minutes.
     - The Recovery panel would have replaced about 20 manual steps with roughly 3 keystrokes.

---

## 1. Timeline

| Time | Event | Source |
|---|---|---|
| 14:55:11 | sase-core `2a0fc2a` "feat(core)!: canonicalize agent-session contracts" is committed. It is the `sase-17m.8` core-contract phase: breaking, with bumped schemas (agent scan 9→10, launch 1→2, cleanup 5→6, and more). | sase-core git log; `sase bead read sase-17m.8` |
| 14:57 | Agent `0rv.w0.f0` starts a monitored check. Its test run later fails with `agent scan wire schema mismatch: got 10, expected 9`. That was the first visible symptom, and it arrived through an agent's own monitor. | `0rv_w0_f0__mon_1` chat |
| 15:02:44 | You start **Update** from the TUI (`,U`). Dev-update fast-forwards `sase` 982209db9→136a3e948 and `sase-core` 96e42d9→**2a0fc2a**. The prebuilt consume misses (`commit-mismatch`), so `just rust-dev-install-uv-tool` rebuilds core from source in 292 s. | `~/.sase/logs/dev_update.jsonl` |
| 15:06:22 | First failure, in the scheduler chop `sidecar_auto_sync`. `bead_claim_checks` and `gate_shell_reclaim` follow. | axe digest `digest_20260925_150818.txt` |
| 15:07:42 | Update finishes. The only check is "Verify sase-core-rs imports", which passes. The toast reads "restarting ACE to load new code". | tui_toasts, dev_update.jsonl |
| 15:07:48 → 15:08:13 | ACE restarts via `os.execv` and the service host restarts under systemd. | tui_toasts; `journalctl --user -u sase.service` |
| 15:08:10 | **TUI crashes**: `WorkerFailed: ValueError('agent scan wire schema mismatch: got 10, expected 9')`. It exits at 15:09:22. | `~/.sase/logs/tui.log` |
| 15:09:36 | You run `sase update -y && sase agent index gc && ace --restart-service`. The update pulls core `7677abd` (still skewed) and restarts the scheduler. `sase agent index gc` crashes in preflight, so `ace` never runs. | `~/.zsh_history`; dev_update.jsonl (15:14:48 entry) |
| 15:10:00, 15:10:22 | `sase-18j.7` and `sase-18j.8` die at bootstrap the moment their `%w(bead=sase-18j.6)` wait resolves. Their dependents are flagged "can never self-resolve". | runs.jsonl; workflow logs; notifications |
| 15:12:07 – 15:15:27 | Five more bootstrap deaths: fork continuations `sase-19i.2--1`, `0rv.w0.f0--2`, `0s8--0`, plus `sase-19p.2` and `sase-17x.13.10.6`. The failed forks hold workspaces #42, #14 and #34. | `error_report.md` files; notifications |
| 15:16:27 | You open a **raw Claude Code session in the primary sase checkout**, paste the traceback, and ask for diagnose, fix, commit, then verify. Seven seconds later it reads "Python expects 9, Rust emits 10". | `~/.claude/projects/-home-bryan-projects-github-sase-org-sase/07f3c76a….jsonl` |
| 15:23:18 | `sase-19o.1` fails **after its commit landed**. `sase stitch create --resume` reports "primary commit succeeded, but agent publication failed … no such column: agent_session". This is a second core bug in the index migration. | `20260925135218/error_report.md` |
| ~15:32 | The fixer edits the Python mirror constants in the **editable primary checkout**, uncommitted. The TUI, CLI and chops now work again. The last chop failure is at 15:31:57. | fixer transcript; axe digest |
| 15:33:19 | You relaunch `ace`. It warns "Agent artifact index schema rebuild failed; using a bounded scan". | zsh history; tui_toasts; tui_startup.jsonl (`artifact_source: source_scan`) |
| 15:34:20, 15:34:28 | Two more bootstrap deaths: `sase-17d.12.2--6` and `sase-19i.1--1`. Both are fork continuations whose runner executed code from the **workspace's own checkout** (`sase_25/src/sase/...`), which still had the old mirror. | `error_report.md` tracebacks |
| 15:34:43 – 15:35:19 | TUI: "Killed 1 agent and dismissed 3 agents". This releases held workspaces #14, #25 and #34. Then "Dismiss cleanup failed: dismissed-agent artifact index sync failed". | tui_toasts; workspace_claims.jsonl |
| 15:35:16 → 15:35:23 | You launch `0sc`, a separate resilience plan. The launcher **claims workspace #14**. | tui_toasts; workspace_claims.jsonl |
| 15:35:28 – 15:36:15 | In tmux `sase_34`: `gst; gaa; gc -m "feat: Add Grok 4.7 support"; gg; gp`. This hand-salvages the dismissed `0s8` fork's work as `1cea18e00`. | zsh history; sase git log |
| 15:37:02 – 15:37:52 | In tmux `sase_14`: `gst; g; gcm; g; gg`, then **`rm -rf sase_14`**, while `0sc--plan` held that claim. | zsh history; workspace_claims.jsonl |
| 15:38:20 | Fixer commits and pushes core `6cb3517` "keep pre-contract artifact indexes and saved groups readable". | sase-core reflog |
| 15:40:17, 15:40:57 | Approvals for the `0se` and `0sf` plans fail: "operational workspace lease failed during preparation: fatal: Unable to create …index.lock". | tui_toasts; notifications |
| 15:41:20 | You run `rm -rf …/sase_25/.git/index.lock`. #25 was unclaimed at that moment. You re-approve, and `0se--0` / `0sf--0` launch at 15:41:42 / 15:42:13. | zsh history; claims |
| 15:43:02 | You run **`sbd work 18j 19i 19o 19p -Y`**, i.e. `sase -p bead work`. It kills waiting members (for example `sase-18j.9`, SIGTERM at 15:43:50) and relaunches 16 agents under the same names from fresh bead prompts. | zsh history; artifacts 154408–154945 |
| 15:49:58 | You run **`sbd work 17x.13.10 17d.12 -Y`**, which relaunches 5 more. `sase-17d.12.land` is SIGTERMed at 15:51:53. | zsh history; artifacts 155107–155213 |
| 15:54:52 / 15:57:31 | Core `2457913` (relationship batch fix) is committed, and the shared `.so` is reinstalled. | reflog; site-packages mtime |
| **16:09:18** | **Fix pushed:** sase `d86bcc3ac` "fix(core)!: speak the agent-session core contract". It bumps all mirrors and the pin to `2457913`. | sase reflog |
| 16:09:43 | ACE restarts (service host restarts at 16:09:55). Toasts: "Axe: 38 error(s) in the last hour", "Services unhealthy: host stopped". You mark 83, then 21, notifications read. | tui_toasts; journalctl |
| 16:16 – 16:25 | Normal work resumes: `0sh`, this research swarm, `0si`. | tui_toasts |
| 16:19 – 16:28 | Fixer follow-ups: core `a55e84e` (gateway fixtures) and `d64520b` (LSP). Full sase-core check is green; the full sase check is still running at 16:43. | fixer transcript |

**Outage windows**

| Scope | Start | End | Duration |
|---|---|---|---|
| TUI | 15:08:10 | 15:33:21 | 25 min |
| Scheduler chops | 15:06:22 | 15:31:57 | 26 min |
| Agent bootstrap (workspace-sourced runners) | ~15:10 | ~16:09, as workspaces picked up master | ~60 min |
| End to end, until the committed fix | 15:06 | 16:09 | ~63 min |

---

## 2. Root cause

### 2.1 Technical

- `src/sase/core/agent_scan_wire_conversion.py:486-490` rejects any scan payload whose `schema_version` differs from the Python mirror `AGENT_SCAN_WIRE_SCHEMA_VERSION`.
- The mirror sits in `agent_scan_wire_records.py`. It was 9 before `d86bcc3ac` and is 10 after.
- That conversion runs under almost everything that touches agents:
  - TUI startup and refresh
  - `sase agent list` and `sase agent index gc`
  - `find_named_agent`, which fork-wait resolution uses in `run_agent_directives.py:393`, so it sits in every `#fork:` continuation's bootstrap
  - the scheduler chops `sidecar_auto_sync`, `bead_claim_checks` and `gate_shell_reclaim`
- The fixer's commit message states the full breakage: TUI, `sase agent list`, launches rejected at launch-wire schema 1, session-parent resolution, relationship batches, hold armers, and fleet enrollment.

### 2.2 Why a half-landed breaking change reached the live machine

- **The epic's own ordering made a skew window inevitable.**
  - `sase-17m.8` (the core flip) blocks `sase-17m.9` ("Pin bump and agents sidecar session pages").
  - `.8` pushed a `feat(core)!` change to sase-core `master` at 14:55.
  - `.9` was still in progress at 15:02, and in fact through 16:40.
- **The dev install tracks core `master`, not the host's pin.**
  - `dev_update` runs `git merge --ff-only origin/master` in the linked sase-core checkout, then builds and installs that HEAD into the uv-tool venv.
  - `sase-core-revision.txt` pinned `c31b8cf` at every host revision from 982209db9 through 1cea18e00. `dev_update` never reads it; only CI and `tools/ratchet_core_revision` do.
  - So the pin, which exists precisely to encode "this sase speaks that core", did nothing locally.
- **Post-install verification is import-only.**
  - The step "Verify sase-core-rs imports in the uv-tool venv" passed.
  - A real skew probe exists, `tools/validate_sase_core_rs`, but it runs only from the Justfile `_setup`. It also hard-codes versions (scan `10` at around line 1122) instead of importing the mirror constants.
- **The restart is ungated.** The app-level update path restarts ACE whenever `result.code_changed` (`src/sase/ace/tui/actions/update_run.py:286-291`), and nothing probes the new process before it goes live.

### 2.3 Why it was fleet-wide rather than a few agents

- **Waits kept releasing agents into the broken runtime.**
  - `sase-18j.7`, `18j.8`, `19p.2` and `17x.13.10.6` each started the moment an upstream phase completed, and each died in bootstrap.
  - Each death then invalidated its own waiters.
- **Monitor continuations are launches too.** Every agent whose `just check` / `sase tool run check` monitor finished during the window forked a continuation, and every one died in `fork_wait_dependency`.
- **Some runners execute the workspace's checkout rather than the primary one** (the traceback paths under `sase_25/src/...`). So fixing the primary checkout at 15:32 did not fix agents in stale workspaces. Two more died at 15:34.

### 2.4 Secondary bug: artifact-index migration

- The new core created `idx_agent_artifacts_agent_session` before migrating the `agent_session` column. This produced `no such column: agent_session`.
- Effects:
  - `sase-19o.1`'s post-commit publication failed.
  - "Dismiss cleanup failed: dismissed-agent artifact index sync failed".
  - The TUI fell back to "bounded scan".
- The fixer reproduced it against a copy of your real index and fixed it in `6cb3517`.

### 2.5 Pre-existing, independent noise in the same window

These were not caused by the skew but got tangled up with it:

- The `0sa` transient Claude failure at 14:23 and the plans it spawned (`0sa.r0`, `0sb`, `0sc`).
- A stale `.git/index.lock` in `sase_25`, which already predated the incident: the `sase-17d.12.2` monitor at 15:20 noted "prepared completion unavailable: stale git index.lock".
- The `0s7` Grok 4.7 failure at 13:01.

An incident surface has to separate these from the main signature. You had to do that separation in your head.

---

## 3. Blast radius

| Category | Count | Members |
|---|---|---|
| Died in bootstrap (no provider turn spent) | 9 | `sase-18j.7`, `sase-18j.8`, `sase-19i.2--1` (#42), `sase-19p.2`, `0rv.w0.f0--2` (#14), `0s8--0` (#34), `sase-17x.13.10.6`, `sase-17d.12.2--6` (#25), `sase-19i.1--1` (#40) |
| Failed after commit (publication) | 1 | `sase-19o.1` |
| Waiters invalidated ("can never self-resolve") | 14 notices | dependents of `18j.7`, `19p.2`, `19i.2`, `19i.1`, `17d.12.2`, `19o.1`, `0s8`, `0rv.w0.f0` |
| Scheduler job failures | 59 digest entries (4 + 17 + 38) | `sidecar_auto_sync` ×40, `bead_claim_checks` ×13, `gate_shell_reclaim` ×2, plus prune/toobig entries |
| Relaunched by `sbd work` (killed/wiped, then relaunched under the same names) | 21 | `18j` ×4, `19i` ×7, `19o` ×2, `19p` ×3, `17x.13.10` ×2, `17d.12` ×3 |
| Workspaces held by failed runs | 5 | #14, #25, #34, #40, #42 |
| Notifications you cleared by hand | 104 | "Marked 83 notifications read" + "Marked 21 notifications read" |

**Note on "ERROR" transcripts.**
- About ten `…_main_ERROR` chats in this window read "Error running LLM provider command (exit code -15/143)". They are **not** failures: they are the mechanical SIGTERM after a monitor or plan handoff, as `0sc--plan` itself says in its transcript.
- They make any after-the-fact audit noisier. See §8.

---

## 4. Audit of your recovery actions

| # | Time | Action | Assessment |
|---|---|---|---|
| 1 | 15:02 | `,U` Update from the TUI | Reasonable. Nothing warned you that core `master` was ahead of the pin with a `feat!` change. **The update triggered the incident, but you are not at fault.** |
| 2 | 15:09 | `sase update -y && sase agent index gc && ace --restart-service` | Sensible reflex ("update again, clean up, restart"). It pulled another skewed core and restarted the scheduler onto it. Because `&&` short-circuited on the crashing `index gc`, the TUI was not relaunched. |
| 3 | 15:16 | Out-of-band Claude Code session in the primary checkout, with the traceback pasted | **This was the decisive action.** It went outside SASE, which was correct because SASE's own launch path was broken. Diagnosis took about 7 s. The fixer checked that `sase-17m.9` owned the same scope before touching it, reproduced the index bug on a copy of real data, and committed core fixes first. Cost: forward-fixing took 53 minutes to the committed sase fix, because no rollback existed. |
| 4 | ~15:32 → 16:09 | (Fixer) live edits in the editable primary checkout | They restored the TUI and chops 37 minutes before the commit. But for that period the fleet ran **uncommitted code from a dirty tree**. The fixer notes it accidentally ran a stash/pop mid-incident; it caused no harm, but it shows how fragile this was. |
| 5 | 15:33 | Relaunch `ace` | Correct, and worked, in bounded-scan mode. |
| 6 | 15:34 | Kill 1 / dismiss 3 failed agents | Correct triage, and it released the held workspaces. Side effect: #14 was released and re-claimed by your next launch 36 s later. |
| 7 | 15:35–15:36 | Hand-commit Grok 4.7 work from `sase_34` | Efficient salvage: the work was verified and only the continuation had died. It bypassed the host-owned finalizer path (stitch metadata, bead linkage, agent publication). The TUI offers no "salvage via finalizer" action, so a raw commit was the only fast option. |
| 8 | 15:37 | `gcm; gg; rm -rf sase_14` | **Riskiest action of the incident.** The claim ledger shows #14 had been claimed at 15:35:23 by `0sc--plan` (launcher preclaim plus retry-transfer), which then ran until about 15:46. The planner survived because its output goes to `~/.sase/plans`, and SASE later re-created `sase_14`. A coding agent there would have lost its tree. Nothing in the TUI showed you that #14 had changed hands. |
| 9 | 15:41 | `rm .git/index.lock` in `sase_25` | Safe in practice: #25 was released at 15:40:54 and re-claimed at 15:41:42. It still took shell spelunking to find, and removing a lock is only safe when no git process holds it. |
| 10 | 15:43, 15:49 | `sbd work 18j 19i 19o 19p -Y`, `sbd work 17x.13.10 17d.12 -Y` | Effective: all six epics were moving again within 10 minutes. The cost is detailed below. |
| 11 | 16:09–16:10 | Restart ACE; mark 104 notifications read; dismiss a pending-action notice | Necessary busywork. The signals never learned the incident was over. |

**Cost of action 10 (`sbd work -Y`):**

- It relaunched phases from the bead prompt rather than resuming the dead turn.
- `sase-17d.12.2` was on its sixth continuation (`--6`). The relaunch put it back at `--plan` in a fresh workspace (#46) with a different model.
- `sase-19i.2` repeated a full plan → monitor → continuation cycle (about 57 minutes) even though its dead fork already carried the monitor result.
- Waiting members were SIGTERMed and relaunched when re-arming their waits would have done. The runner's SIGTERM handler then crashed with `RuntimeError: reentrant call inside <_io.BufferedWriter name='<stderr>'>` (`runner_signals.py:48`).
- `-Y` skips the destructive-cleanup confirmation, as does the TUI beads-pane `w` path, which passes `yes_to_all=True`. So you never saw the list of what was killed and wiped.

**Things that went well and should be kept:**

- The failed-run workspace hold plus `error_report.md` preserved every traceback, and "Workspace #N is held" told you where the work was.
- The wait checker detected invalidated waiters within seconds.
- `sase bead work` retry semantics (forced same-name reuse, per-phase cleanup, launch rollback) gave you a working bulk relaunch without writing prompts.
- ACE's "bounded scan" fallback kept the TUI usable while the index was broken.

**Still open as of 16:50:**

- `0rv.w0.f0.w0` has been WAITING since 10:30 on `0rv.w0.f0`. That dependency's last attempt died at 15:13, its workspace was deleted at 15:37, and the waiter was flagged "can never self-resolve" at 15:14. Nobody has relaunched or killed it.
- `sase-17m.9` owns the same pin bump and mirror scope that `d86bcc3ac` shipped, and its chain was still running (`--mon-0` at 16:26, `--2` at 16:39). Check that it does not redo or conflict with the hotfix.
- **`sase core health` is red on current master** (085451924): "agent_launch_wire_schema_version() raised RuntimeError: unexpected schema version 2". `src/sase/core/health.py:198` hard-codes `!= 1`, and `d86bcc3ac` bumped launch to 2 without updating it. The only built-in health command now gives a false alarm, which matters because §7 builds on it.

---

## 5. Why recovery was hard: friction points and requirements

| # | Friction observed today | Requirement it implies |
|---|---|---|
| F1 | One root cause surfaced as more than 80 recorded signals: 10 agent-failure notices, 14 wait notices, 59 ungrouped digest entries (the 38-entry digest repeats the same traceback 36 times), plus a TUI crash and toasts. | **R1: Cluster failures into one incident per normalized signature**, with first-seen time, count, and correlation to the most recent update. |
| F2 | The TUI, the thing you recover *with*, crashed on the failure, as did `sase agent list` and `index gc`. You had to leave SASE to fix SASE. | **R2: The recovery surface must not depend on what broke.** A degraded or safe mode, plus a way to launch a fixer outside the SASE runner. |
| F3 | No rollback. The only path was a 53-minute forward fix under time pressure, with the fleet running uncommitted code. | **R3: Last-known-good rollback** of the editable checkouts plus the core build, one keystroke from the TUI and preferably automatic. |
| F4 | Waits and monitor continuations kept launching into the broken runtime. 9 failures and 14 invalidated waits accumulated after the first two. | **R4: Pause admission automatically** on a storm of same-signature bootstrap failures, park the launches, and resume them when healthy. |
| F5 | Recovery tools are per-agent (`R` allocates `.r0` names and demotes the clan) or per-epic (`sase bead work`). Neither preserves a dead continuation's context, and neither is per-incident. | **R5: Replay by recovery class.** Bootstrap failures replay verbatim under the same identity and workspace; post-commit failures resume finalization; invalidated waiters re-arm. |
| F6 | Destructive bulk cleanup (`-Y`, TUI `w`) ran without a preview. | **R6: Preview, then confirm**, for every bulk recovery action. |
| F7 | Held workspaces are invisible in the TUI (no "held" badge). Their claim can move to a new agent seconds after a dismiss. Lock removal and resets happen in raw shells. | **R7: Claim-aware workspace hygiene** in the TUI: inspect, salvage via finalizer, release, clear a verified-stale lock, and reset only when unclaimed. |
| F8 | 104 notifications marked read by hand; wait notices say "Kill and relaunch the waiter" but have no button. | **R8: Resolve the incident's signals together** and put actions on the notices themselves. |
| F9 | Agents met the breakage and worked around it. `sase-19o.3` at 16:00 wrote "The scan-schema mismatch is already on the base tree, so I'll stub the artifact scan in these tests…". | **R9: Tell running agents about known incidents**, or at least pause new starts, so infrastructure faults are not papered over inside feature diffs. |

---

## 6. UX options

Each option is scored against today's incident: what it would have changed, and at what cost.

### A. Incident banner and Recovery panel (clustering)

- **What it is:**
  - A persistent header banner appears when more than N failures share a normalized signature within a window. Normalization strips pids, paths, timestamps, workspace numbers and hashes, and keeps exception type, message and top frame.
  - The banner reads, for example: `⚠ Incident · 14m · ValueError: agent scan wire schema mismatch (got 10, expected 9) · 9 agents, 59 jobs · began 2m40s after update core 96e42d9→2a0fc2a`.
  - It opens a Recovery panel: an Admin Center tab or modal listing affected agents, jobs and held workspaces, grouped by recovery class, with one canonical traceback.
- **Today:** it would have turned more than 80 signals into one object and made the update correlation obvious. On its own it recovers nothing.
- **Cost:** medium. The signature and grouping logic belong in sase-core (see §7.6). Scheduler errors are already collected in `recent_errors.json`, and runner errors in `error_report.md` / `done.json`.

### B. Bulk "Replay affected" with recovery classes

- **What it is:** one action on an incident that, after a preview, does the following:
  - **Replays** launches that died before the provider spawned. The same `raw_xprompt.md`, the same name via forced reuse, the same clan and bead identity, the same continuation checkpoint, and the held workspace handed over if it is unchanged against `finalizer_baseline.json`.
  - **Resumes finalization** for runs that failed after commit (`sase stitch create --resume`).
  - **Re-arms** waiters invalidated by a dependency that is now replayed.
  - **Defers** anything ambiguous to "needs decision".
- **Today:**
  - It replaces two `sbd work -Y` commands, the kill/dismiss, and the hand-salvage.
  - It keeps `sase-17d.12.2` at turn 7 instead of turn 1, and avoids killing and relaunching 15 waiting agents.
  - The 9 bootstrap deaths cost zero provider tokens, so replaying them is idempotent and cheap.
- **Cost:** medium to high. The runner needs to record `failure_stage` (bootstrap / provider / finalize); today only the traceback implies it. The pieces already exist: forced reuse (`wipe_names_for_forced_reuse`, `%id:!`), retry lineage (`retry_of_timestamp` / `retried_as_timestamp` columns in the artifact index), and workspace transfer (`retry_transfer_from_pid`, `preserve_workspace`).

### C. Safe mode (degraded TUI)

- **What it is:**
  - If startup or refresh hits a skew-class error (wire or schema mismatch, `ImportError` of `sase_core_rs`, "uses a format this process does not understand"), ACE keeps running in a minimal mode instead of calling `_handle_exception` and exiting (`src/sase/ace/tui/app.py:364-383`).
  - It shows the error, a skew table (Python mirror vs. Rust-reported version per wire; installed core commit vs. pin), the last update receipt, and actions: **Roll back last update**, **Run health probe**, **Open fixer in tmux** (a provider CLI in the primary checkout with an incident brief pre-filled), and **Retry normal startup**.
- **Today:** the user would have stayed inside ACE. The 25-minute TUI outage becomes zero, and paired with option D the fleet outage becomes minutes.
- **Cost:** low to medium. Safe mode must be built from code paths that avoid the agent scan, reading only raw JSON/JSONL files.

### D. Update safety net: pre-swap probe, last-known-good, post-restart probe, rollback button

- **What it is:**
  - `dev_update` probes the new build against the host's mirrors *before* it becomes the live extension, and before ACE or the service host restarts. Options for the probe: a fixed `validate_sase_core_rs` that imports the mirror constants; a fixed `sase core health` that does the same; or both, run in a subprocess against the staged build.
  - On failure it keeps or reinstalls the previous build, reports "core update held back: agent scan v10 vs v9 (pin c31b8cf)", and does not restart.
  - It keeps the previous built artifact per core commit, so rollback takes seconds instead of a 292 s rebuild.
  - The Updates tab gains **Roll back last update**. `dev_update.jsonl` already records old→new SHAs per checkout.
  - Optionally: build at the host pin unless the probe passes for HEAD.
- **Today:** the 15:02 update would have reported "held back" at 15:07. No crash, no failed agents. **This is the highest-leverage single change for this failure class.**
- **Cost:** low to medium, and mostly Python install tooling. It is not domain logic.
- **Caveat:** probe *before* any new code touches durable state. Today's index migration shows that rolling back after the new core has migrated SQLite or archives can leave the reverse skew. The artifact index is rebuildable; saved-group archives (v3) are not.

### E. Admission circuit breaker ("fleet pause")

- **What it is:**
  - After K bootstrap failures with the same signature within M minutes (for example 3 in 10), the scheduler parks new admissions: wait-resolved starts, monitor continuations, bead-work launches, and optionally agent-spawning chops.
  - It shows `⏸ Admissions paused · incident #… · 6 parked` in the header and on each parked row (it can reuse `runner_capacity_blockers`).
  - It auto-resumes when the health probe goes green, or manually.
  - The TUI also gets a manual **Pause / Resume fleet** toggle for when you already know something is broken.
- **Today:**
  - Tripping on the third failure (15:12:07) would have prevented 6 of the 9 bootstrap deaths and all the "can never self-resolve" cascades from them. Resume would have started them with no restart at all.
  - It also answers F9 for new starts.
- **Cost:** medium. Admission is core queue logic (sase-core already resolves capacity at admission), and the pause needs a durable store with an explicit reason and owner.
- **Consistency with existing decisions:** parking a *launch* does not block a running agent, so it fits "A Gate Never Blocks An Agent" and "Agents Are Single-Turn".

### F. Claim-aware workspace hygiene actions

- **What it is:**
  - A "held" badge on failed rows and a Workspaces view showing claim owner, dirty-file count, `index.lock` presence and age, and whether a git process holds it.
  - Actions:
    - **Salvage**: run the host finalizer or stitch for the dead run instead of a raw `git commit`.
    - **Release.**
    - **Clear stale lock**: only if no git process holds it and the lock is older than N minutes.
    - **Reset workspace**: refused while claimed by a live agent.
- **Today:** it replaces the `rm -rf sase_14`, `rm index.lock` and tmux-commit steps, and would have blocked the #14 deletion by showing "#14 claimed by 0sc--plan (running)".
- **Cost:** medium. Some of this is already planned as `lease_index_lock_recovery` / `lease_git_lock_recovery`.

### G. Actionable, auto-resolving notifications

- **What it is:**
  - Wait notices get **Relaunch dependency**, **Re-arm** and **Kill waiter** buttons.
  - Axe digests are grouped by signature, with the traceback shown once and ×N.
  - All signals tagged with an incident id resolve together when it closes.
- **Today:** it saves the 104 manual mark-reads and makes the 38-entry digest readable.
- **Cost:** low. `ViewErrorReport` today just opens the file in `$EDITOR` (`_notification_handlers.py:54-89`).

### H. Guided "Recover" command in the TUI command line

- **What it is:** a `:recover` command that walks through a checklist: probe → roll back or wait for fix → replay → workspaces → resolve. It is a cheap front end over A–G.
- **Today:** helpful only once A–G exist.
- **Cost:** low. It is a nice-to-have alongside the panel.

### Comparison against today's incident

| Option | Prevents | Shortens outage | Cuts manual recovery | Cost | Depends on |
|---|---|---|---|---|---|
| D Update safety net | **Yes, for this class** | to 0 | all | L–M | fixed probe |
| C Safe mode | – | TUI 25→0 min; fleet to about 5 min with D's rollback | some | L–M | D (rollback) |
| E Circuit breaker | 6 of 9 deaths | – | high (resume = replay) | M | probe |
| A Incident banner/panel | – | faster diagnosis | medium | M | – |
| B Replay affected | – | – | **highest** (about 20 steps → 3) | M–H | A, failure_stage |
| F Workspace hygiene | the #14 near-miss | – | medium | M | – |
| G Actionable notices | – | – | low–medium | L | A |
| H `:recover` | – | – | low | L | A–G |

---

## 7. Recommendation: an Incident Recovery layer (D → C → A+B → E, with F and G folded in)

**Recommendation.** Build a single incident model with a Recovery panel, in four layers:

1. First, make updates unable to produce this outage (D).
2. Then make the TUI survive the next skew or infrastructure failure (C).
3. Then make recovery a preview-and-confirm replay of one incident instead of about 20 hand steps (A+B, with F and G folded in).
4. Finally, stop the fleet feeding a broken runtime (E).

**Why this order, and why not a single feature:**

- D is the cheapest change and would have prevented today outright. Its rollback half is also what makes C useful.
- A panel without C would have been unreachable today.
- A panel without B is a prettier list of failures.
- E has the biggest payoff but needs a trustworthy probe, and today's probe is itself broken (§4, open items).

### 7.1 Layer 0: update safety net (prevention; mostly outside the TUI)

1. **Fix the probe.**
   - Make `src/sase/core/health.py` and `tools/validate_sase_core_rs` compare against the imported mirror constants (`AGENT_SCAN_WIRE_SCHEMA_VERSION`, `AGENT_LAUNCH_WIRE_SCHEMA_VERSION`, and so on) instead of literals. They are red or brittle today.
   - Add an agent-scan round trip on a temp dir to `sase core health`. That is the exact call that failed.
2. **Stage, probe, swap.**
   - `dev_update` builds the new core, runs the probe in a subprocess against the staged artifact, and only then installs.
   - On probe failure it keeps the old build, marks the core outcome `held_back` with the skew diff, and suppresses the ACE and service restart.
   - The prebuild cache already keys artifacts by core commit (`rust_prebuild.reason: commit-mismatch`), so retaining the previous artifact is a small extension.
3. **Respect the pin by default.** The dev install may run core ahead of `sase-core-revision.txt` only when the probe passes. Otherwise it builds at the pin. This keeps the dogfooding benefit of tracking HEAD without the failure mode.
4. **Post-restart probe.** After `os.execv`, the new ACE runs the probe before first paint. On failure it enters safe mode (Layer 1) and offers rollback.
5. **Rollback.**
   - Record pre-update SHAs; `dev_update.jsonl` already has them.
   - **Roll back last update** resets the editable checkouts to those SHAs (fast-forward-safe, refusing a dirty tree), reinstalls the retained core artifact, and restarts.
   - Expose it in the Updates tab and in safe mode.

**Process fix** (not UX, but it caused today): a `feat(core)!` phase should not merge to core `master` until the host phase that bumps the pin is ready to land with it. Two ways to get there: an epic land step that pushes both together, or a core-side compatibility shim that keeps emitting the old schema until the pin moves. Layer 0 makes a violation harmless locally. It does not make it right.

### 7.2 Layer 1: TUI safe mode

- **Trigger:**
  - a skew-class exception during startup or refresh (a small allowlist of exception types and messages), or
  - a failed post-restart probe.
- **Screen:**
  - the error, once
  - a skew table (wire, Python mirror, Rust-reported, pin, installed core commit)
  - the last update receipt (old→new SHAs)
  - a list of recent failures read **directly from JSON/JSONL on disk**, with no `sase_core_rs` scan: `runs.jsonl`, `error_report.md`, `recent_errors.json`
- **Actions:**
  - **Roll back last update** (Layer 0)
  - **Run probe**
  - **Open fixer**: a tmux window in the primary checkout running your default provider CLI, with a pre-filled brief (signature, traceback, update diff, "fix forward or roll back; commit as soon as confident"). This is what you did by hand at 15:16, and it must not use the SASE runner, which may be the broken component.
  - **Pause fleet** (Layer 3)
  - **Retry normal startup**
- **Design constraint:**
  - Safe mode and the failure ledger it reads must not call into `sase_core_rs`.
  - This is a deliberate, narrow exception to "The Rust Core Is Required": presentation of raw failure records, not shared domain logic.
  - It should be recorded as a decision so it does not grow.

### 7.3 Layer 2: incident banner, Recovery panel, bulk replay

**Incident model (in sase-core):**

- `Incident { id, signature, first_seen, last_seen, state: active|mitigated|resolved, correlated_update, members[] }`.
- Each member is an agent run or a job run, carrying `failure_stage`, `recovery_class`, `held_workspace` and `replay_plan`.
- Inputs:
  - runner error facts (add `failure_stage` to `done.json` / `error_report`)
  - scheduler `recent_errors.json`
  - wait-check terminal-blocked facts
- One incident per normalized signature per window. Pre-existing unrelated failures (the `0sa` transient, the stale `index.lock`) cluster separately, so the panel does the "this one is unrelated" triage you did mentally.

**Banner:** one line under the header while any incident is active. It stays hidden for single failures, which keep today's per-agent notices (below the threshold, nothing changes).

**Recovery panel** (Admin Center tab plus a leader key; `,i` appears free in `default_config.yml` `leader_mode.keys`):

```
INCIDENT i-0925-a · ACTIVE 14m · ValueError: agent scan wire schema mismatch (got 10, expected 9)
first 15:06:22 (sidecar_auto_sync) · 2m40s after update sase 982209d→136a3e9, core 96e42d9→2a0fc2a
probe: ✗ agent_scan 10≠9  launch 2≠1      admissions: ⏸ paused 15:12 (3 same-signature bootstrap failures)

REPLAY VERBATIM · failed before provider start · same name / workspace / checkpoint     9
  sase-18j.7          wait on sase-18j.6 released → bootstrap        —
  sase-19i.2--1       fork: monitor result 1pbgzhry989h              ws #42 held · clean vs baseline
  sase-17d.12.2--6    fork: monitor result ty5tnr2qr22z              ws #25 held · index.lock (no git pid, 21m)
  …
RESUME FINALIZATION · commit landed, publication failed                              1
  sase-19o.1          stitch create --resume                          ws held
RE-ARM WAITERS · dependency will be replayed; no kill needed                         14
PARKED LAUNCHES · never started; start on resume                                      6
NEEDS DECISION                                                                        0
SCHEDULER JOBS · sidecar_auto_sync ×40 · bead_claim_checks ×13 · gate_shell_reclaim ×2 (self-heal on next tick)

[r] roll back update  [p] probe  [f] open fixer  [R] replay all (preview)  [w] workspaces  [z] resolve
```

**Replay semantics:**

- Replay is available only when the probe is green. Before that the action reads "Replay (waiting for health)" and can be armed to fire automatically on green.
- It **preserves identity**: forced same-name reuse, the same clan, bead and `agent_session`, and the same continuation checkpoint. The TUI's `R` does the opposite (`.r0` name, clan demoted), which is why you could not use it for epic phases today.
- A held workspace is handed to its replay when the tree matches the finalizer baseline plus the dead run's recorded delta. Otherwise the member moves to NEEDS DECISION.
- It never kills a live agent. Waiters are re-armed, not relaunched.
- Every bulk action shows the per-member plan first, fixing the `-Y` / TUI `w` no-preview gap.

**Workspaces sub-view (F):**

- held, claimed, dirty and lock status, with Salvage (host finalizer), Release, Clear verified-stale lock, and Reset (refused while claimed)
- a claim-owner column, so "#14 now belongs to 0sc--plan" is visible before any destructive action

**Resolve (G):**

- When the probe is green, the replays have launched and the signature has not recurred for T minutes, the incident flips to `resolved`.
- All its notifications (agent failures, wait notices, digests) resolve in one step, leaving one summary notice with a link to an incident report file. That report is also the audit trail this research had to reconstruct by hand.
- Wait notices outside incidents get **Relaunch dependency**, **Re-arm** and **Kill waiter** buttons.

### 7.4 Layer 3: admission circuit breaker

- **Auto-trip:** K=3 bootstrap-stage failures with one signature within M=10 min, or any single skew-class failure. **Manual trip:** Pause fleet from safe mode, the banner, or the bang-mode toggles (next to `toggle_axe`).
- **Parked admissions:** wait-resolved starts, monitor continuations, bead-work and TUI launches (with an explicit "launch anyway" override), and agent-spawning chops.
- **Not parked:** running agents, and chops the fix depends on.
- **Auto-resume on a green probe.** Parked launches start, in queue order, with no restart and no replay needed, because they never died.
- **Advertise the incident to running agents:** a short line in continuation prompts or `sase final` context, such as "Known incident i-0925-a: agent-scan schema skew; do not stub or work around it in your diff; report and stop if blocked". This addresses the `sase-19o.3` workaround behavior.

### 7.5 Counterfactual replay of today

| Layer present | What would have happened |
|---|---|
| 0 only | 15:07: "core update held back: agent scan v10 vs v9 (pin c31b8cf)". No restart onto the skew, no failures. `sase-17m.9` lands the mirrors later and the next update passes the probe. **Outage: 0.** |
| 1 + rollback, without the pre-swap probe | 15:08: ACE opens in safe mode instead of crashing. One keypress rolls back (seconds with a retained artifact, about 5 min with a rebuild). The fixer still runs, but not under outage pressure. **Outage: about 2–6 min, 2–3 bootstrap deaths.** |
| 2 + 3 without 0 or 1 | Breaker trips at 15:12 after 3 deaths, and 6 launches park. After the 16:09 fix, the probe goes green, parked launches start, and **Replay all** runs 3 verbatim replays, 1 finalization resume (`sase-19o.1`, whose failure came mid-run, so the breaker could not have parked it), and re-arms of the waiters those failures invalidated. One resolve clears all signals. **Manual recovery: about 3 keystrokes instead of about 20 actions across 6 tools**, and no epic phases restarted from scratch. |

### 7.6 Where the code goes (Rust core boundary)

- **sase-core (shared domain):**
  - signature normalization and incident clustering
  - recovery-class and replay-plan computation
  - the admission pause as a first-class admission blocker
  - the `Incident` wire type
  - Telegram and mobile need the same "Replay affected" and "Pause fleet", so by the litmus test in the core-boundary memory this is core logic.
- **sase (Python):**
  - runner `failure_stage` recording
  - `dev_update` stage/probe/swap/rollback (install tooling)
  - the core-independent failure ledger reader for safe mode
  - Textual banner, panel, modals and keybindings; update `src/sase/default_config.yml` for the new leader key per the gotchas memory
- **Probes:** the probe that gates updates must itself avoid new core behavior beyond the calls it is probing, and must import the Python mirror constants.

### 7.7 Suggested sequencing

| Order | Slice | Size | Unblocks |
|---|---|---|---|
| 1 | Fix `sase core health` / `validate_sase_core_rs` to use mirror constants, and add an agent-scan probe | small | everything |
| 2 | `dev_update` stage→probe→swap, retain last-known-good, suppress restart on failure, **Roll back last update** in the Updates tab | medium | C |
| 3 | Safe mode (skew allowlist, ledger view, rollback, open fixer, pause) | medium | – |
| 4 | Runner `failure_stage` plus core incident clustering; banner and read-only Recovery panel; grouped digests | medium | B, G |
| 5 | Replay-affected with preview (verbatim / finalize-resume / re-arm), plus the workspaces sub-view with claim-aware actions | large (epic) | – |
| 6 | Admission breaker plus agent incident advisory | medium | – |

**Acceptance test for the whole layer:**

- Replay today's incident in a sandbox: an editable host plus a linked core with a deliberate mirror bump and a queued epic.
- Assert: no ACE crash; a "held back" or safe-mode path; at most one incident object; a replay plan that matches §3; zero kills of waiting agents; a single resolve.

### 7.8 What not to build

- **Automatic timed retries of skew errors.**
  - The `llm_provider.retry.sase` block ("uses a format this process does not understand", `wait_times: [0]`) would not have helped: the pattern did not match, and an immediate retry fails again until the fix lands.
  - The runner only *prints* "retryable" (`run_agent_runner_errors.py:43`).
  - Infrastructure failures need park-until-healthy, not retry-after-N-seconds.
- **A generic "retry all failed agents" button without recovery classes.** It would have replayed `sase-19o.1` after its commit landed, and restarted epics from scratch exactly as `-Y` did.
- **Recovery that runs through the SASE agent runner.** On the day it is needed, that runner may be the broken part.

---

## 8. Other defects found during the audit

These are candidates for task beads; I did not file any.

1. **`sase core health` is false-red on master.** `src/sase/core/health.py:198` checks `version != 1` for the agent-launch wire, which `d86bcc3ac` bumped to 2. Line 150 hard-codes the commit-footer version the same way.
2. **The runner's SIGTERM handler re-enters stderr.** `src/sase/axe/runner_signals.py:48` raises `RuntimeError: reentrant call inside <_io.BufferedWriter name='<stderr>'>` when killed mid-write. Seen on `sase-18j.9` and `sase-17d.12.land`.
3. **Normal handoff terminations are saved as `…_main_ERROR` transcripts** with "Error running LLM provider command (exit code -15/143)". They read as failures to humans and agents: `0sc--plan` had to explain it, and this audit had to rule them out one by one.
4. **The app-level update path restarts ACE whenever code changed, even if the Rust build step failed** (`update_run.py:286-291`; `dev_update/execute.py:145-157` returns `changed=True` on reconcile failure). The Plugins-browser path, by contrast, restarts only on success.
5. **Wait-check "can never self-resolve" also fires on routine monitor failures** that already have a continuation. At 16:46 it fired for `sase-19p.2--mon-0` while `sase-19p.2--2` was launching. This dilutes the signal an incident view would rely on.
6. **Held workspaces are not visible in the TUI.** A dismiss releases the claim, and the launcher can reuse the workspace within seconds. Today that put a new planner in a workspace you were about to delete.
7. **`0rv.w0.f0.w0` is orphaned.** It has been WAITING since 10:30 on a dependency that cannot resolve.

---

## Appendix: evidence index

| Evidence | Path or command |
|---|---|
| Update runs (plans, commands, SHAs, restart) | `~/.sase/logs/dev_update.jsonl` (entries 15:07:42, 15:14:48) |
| TUI crash and stalls | `~/.sase/logs/tui.log` (15:08:10, 16:20:56, 16:43:39) |
| Toast timeline (user-visible actions) | `~/.sase/logs/tui_toasts.jsonl` |
| TUI startups and scan source | `~/.sase/logs/tui_startup.jsonl` |
| Agent run outcomes | `~/.sase/logs/runs.jsonl` |
| Workspace claim ledger | `~/.sase/logs/workspace_claims.jsonl` |
| Scheduler failure digests | `~/.sase/axe/error_digests/digest_20260925_{150818,151451,160958}.txt` |
| Failed-run reports | `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/25/{20260925151151,151300,151309,153407,153415,135218}/error_report.md` |
| Workflow logs of early deaths | `~/.sase/workflows/202609/gh_sase-org__sase_ace-run-{260924_190903,190904,190905,260925_084331,084741,140711}.txt` |
| Notifications | `sase notify list -j -l 200 --all` (wait_checks, axe, user-agent, gate, plan-archive) |
| Your shell actions | `~/.zsh_history` from 15:09:36 to 16:09:24 (aliases: `sbd`=`sase -p bead`, `ace`=`sase -p tui`, `gcm`=`git checkout master`, `gg`=`git pull`) |
| Fixer session | `~/.claude/projects/-home-bryan-projects-github-sase-org-sase/07f3c76a-7f3a-4835-aa58-44064a77f367.jsonl` |
| Fix commits | sase `d86bcc3ac`; sase-core `6cb3517`, `2457913`, `a55e84e`, `d64520b`; breaking change `2a0fc2a` |
| Pin history | `git show <rev>:sase-core-revision.txt` → `c31b8cf` through `1cea18e00`, `2457913` at `d86bcc3ac` |
| Bead context | `sase bead read sase-17m.8 sase-17m.9` (the `.8` core flip blocks the `.9` pin bump) |
| Service host restarts | `journalctl --user -u sase.service` (15:08:13, 16:09:55, 16:30:20) |
| Existing recovery primitives (code map) | `R` retry `_entry_relaunch.py:184-231`; `,x` bulk kill-and-edit `_marking_kill.py:81-246`; bead-work cleanup classes `cli_work_cleanup_targets.py:432-438`; TUI `w` passes `yes_to_all=True` `_artifacts_beads_common.py:210-224`; crash path `app.py:364-383`; probe `core/health.py:198` |
