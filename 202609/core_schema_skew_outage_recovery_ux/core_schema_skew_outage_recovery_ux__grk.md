# Agent-scan schema skew: fleet failure audit and TUI recovery UX

**Researcher:** `research.2k.grk` (independent swarm report)
**Date:** 2026-09-25
**Machine:** athena
**Window:** roughly 15:06–16:30 EDT (about 30–90 minutes before this report)
**Question:** What failed, what did the operator do to recover, and which TUI UX would make the next incident cheaper?

## Recommendation (up front)

Ship a **Fleet Incident Recovery** flow on the Agents tab, cloned from the existing Provider Drain modal (`ProviderDrainPromptModal` / `sase agent drain`).

When many agents fail with the same host-level error class — today, `ValueError: agent scan wire schema mismatch: got 10, expected 9` — the TUI should raise one confirmed recovery, not dozens of `ViewErrorReport` rows.

The confirmed action should:

1. Refuse to relaunch while Python and `sase_core_rs` still disagree on `AGENT_SCAN_WIRE_SCHEMA_VERSION`.
2. Dismiss the failed runs so held workspaces are released.
3. Relaunch stored prompts through `execute_agent_restart()` (same-name, fresh workspace clone).
4. Cluster the inbox into one incident and rewrite or warn on waiters that now point at dead artifact directories.

Pair that with an Update-panel **preflight** when an incoming core bump changes a wire schema: warn that running agents and workspace clones will die, and offer drain-then-apply.

In-place `R` retry is the wrong recovery for this class. Retry-in-place keeps the poisoned workspace clone and leaks another workspace. The operator already has the right primitive (`,x` / `sase agent restart`); it is just one-row or mark-gated, and it does not know about schema skew.

---

## 1. What actually failed

### 1.1 The poison pill

Every live consumer of `scan_agent_artifacts()` died on:

```text
ValueError: agent scan wire schema mismatch: got 10, expected 9
```

The call chain is deterministic:

1. Python `scan_agent_artifacts()` in `src/sase/core/agent_scan_facade.py` calls the Rust binding `sase_core_rs.scan_agent_artifacts`.
2. Rust returns a JSON-shaped dict whose `schema_version` is **10**.
3. Python `agent_scan_wire_from_dict()` in `src/sase/core/agent_scan_wire_conversion.py` compares that integer to `AGENT_SCAN_WIRE_SCHEMA_VERSION` and raises on inequality.

The check is exact equality, not a compatibility window. Tests pin that on purpose (`tests/test_core_agent_scan_wire_schema.py`: `test_scan_wire_rejects_stale_binding_schema`, `assert AGENT_SCAN_WIRE_SCHEMA_VERSION == 10`).

The conversion helper drops unknown keys so a *newer writer with extra fields* can still be read — but a version bump is treated as an incompatible shape change and crashes the caller.

### 1.2 Why Rust said 10 and Python said 9

This machine uses a **dev install**. `sase_core_rs` is built from the linked `sase-core` checkout. When that checkout fast-forwards to a core that serializes scan wire 10, every process whose Python still mirrors version 9 dies on the next scan.

The sase stitch that later fixed the mirrors says this in so many words. Commit `d86bcc3ac` (2026-09-25 16:09:18 -0400), subject `fix(core)!: speak the agent-session core contract`:

> sase-core's contract flip (2a0fc2a) serialized the canonical agent-session spellings and bumped every changed wire schema, but sase still mirrored the old versions. Dev installs build `sase_core_rs` from the linked sase-core checkout, so once that checkout fast-forwarded every sase process broke: `sase tui` and `sase agent list` died on "agent scan wire schema mismatch: got 10, expected 9", agent launches were rejected at schema 1, and session-parent resolution, relationship batches, hold armers, and fleet enrollment all failed.

The Python bump also moved artifact index 31→33, cleanup 5→6, launch/launch-plan 1→2, gate follow-up 1→2, saved-group archive 2→3, and fleet protocol 1→2. Scan wire 10 is the failure that hit the agent fleet first because **agent bootstrap scans on the way in** (`find_named_agent` → `scan_agent_artifacts` during `#fork` / wait resolution).

Workspace clones make it worse. A failed run's traceback is not from the host checkout; it is from the clone:

```text
File "/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_40/src/sase/core/agent_scan_wire_conversion.py", line 487, in agent_scan_wire_from_dict
ValueError: agent scan wire schema mismatch: got 10, expected 9
```

The clone's Python source is frozen at clone time. The native extension is the global `sase_core_rs`. After a core rebuild, **every already-cloned workspace is permanently poisoned** until it is discarded and a new clone is taken from a Python tree that mirrors schema 10.

### 1.3 This is a recurring class, not a one-off

The same mismatch already happened on this machine twelve days earlier:

| When (EDT) | Error | Follow-up stitch |
| --- | --- | --- |
| 2026-09-13 08:24–08:32 | `got 9, expected 8` | `654335d55` 09:55 `fix(agent-scan): mirror sase-core scan wire schema 9` |
| 2026-09-25 15:06–15:34 | `got 10, expected 9` | `d86bcc3ac` 16:09 `fix(core)!: speak the agent-session core contract` |

Same operator loop: core moves, fleet dies, operator restarts agents by hand, a stitch lands the Python mirror.

### 1.4 Blast radius on 2026-09-25

**Axe chops** (background jobs that scan artifacts) failed in a tight loop from 15:06:22 through at least 15:28. Digests:

- `~/.sase/axe/error_digests/digest_20260925_150818.txt` — 4 errors
- `~/.sase/axe/error_digests/digest_20260925_151451.txt` — 17 errors
- `~/.sase/axe/error_digests/digest_20260925_160958.txt` — **38 errors** (inbox toast at 16:09:59)

Jobs that crashed on the same `ValueError`:

- `sidecar_auto_sync` (every ~30s)
- `bead_claim_checks`
- `gate_shell_reclaim`
- `artifact_run_prune` (`protection_unavailable` because the scan that protects live runs could not run)
- `toobig_split[sase]` (`declarative job preflight failed`)

**Live agents** failed as soon as they scanned. Named examples from the inbox:

- `sase-18j.7`, `sase-18j.8` (long-running from 2026-09-24)
- `sase-19p.2`
- `sase-17x.13.10.6`
- several unnamed `ace(run)-260925_1511xx` / `_1534xx` successor/monitor shells

Each failure **held a workspace**: `#14`, `#25`, `#34`, `#40`, `#42`, plus `#0` for some project-root runs. The error report's recovery paragraph is:

> Workspace #N is held for this failed run. Inspect or commit its changes, then dismiss the failed agent in `sase tui` to release it.

That is a fleet-level leak. Retry without dismiss does not free the slot.

**Secondary damage** while the scan path was down:

- Plan archive failed at 15:40:16 and 15:40:54 (`OperationalLeaseError` / `fatal: Unable to crea[te index.lock]`). Toasts: `Gate execution failed` for `claude_oauth_refresh_retry.md` and `lease_index_lock_recovery.md`.
- `wait_checks` posted `Wait dependency can never self-resolve` at 15:10, 15:24, 15:35, and again at 16:46 after relaunch — waiters still named the **old** artifact directories.
- In-flight LLM processes were SIGTERM'd when workflows were killed (`exit code -15` / `143` in chat transcripts around 16:00–16:37).
- At 16:10:16, after the TUI restart: `Services unhealthy: host stopped`.

---

## 2. Timeline of the incident and the operator's recovery

Times are America/New_York (EDT). Sources: `~/.zsh_history`, `~/.sase/logs/tui_toasts.jsonl`, `sase notify list`, `sase agent list -a -j`, axe digests, git log, agent error reports.

| Time | What happened | Evidence |
| --- | --- | --- |
| 14:04 | Operator already fighting `index.lock` | `rm -rf …/sase_12/.git/index.lock` |
| 15:06:22 | First axe `sidecar_auto_sync` death on schema 10 vs 9 | digest_20260925_150818 |
| **15:09:36** | **Operator ran `sase update -y && sase agent index gc && ace --restart-service`** | zsh history. This is the moment a rebuilt `sase_core_rs` is guaranteed to be live while Python mirrors are still 9. |
| 15:10–15:34 | Named agents fail; workspaces held; wait-never-resolve notifications | inbox `ViewErrorReport` rows |
| 15:33:21 | TUI session `20260925T193321Z-1022431` is up (pid 1022431) | tui_toasts |
| 15:37–15:42 | Shell cleanup of a workspace and another `index.lock` | `rm -rf sase_14`; `rm -rf …/sase_25/.git/index.lock` |
| 15:38–15:42 | One-by-one `Killed workflow (PID …)` plus two fresh launches (`Started 1 agent(s)`) | tui_toasts. Also coder launches `0sd--0` / `0se--0` / `0sf--0` for header, oauth-retry, and lease-lock plans. |
| 15:40–15:41 | Approving those plans fails archive because of lease/`index.lock` | GateExecutionFailed + plan-archive notifications |
| 15:43, 16:03, 16:19, 16:29 | Repeated `↻ Restart available` — “Running SASE code changed on disk; restart from Update to load it.” | tui_toasts. Host Python is moving; the TUI process is stale. |
| 15:44–15:52 | Burst of replacement launches (`sase-18j.7`, `sase-19i.*`, `sase-19o.3--plan`, `sase-19p.2--plan`, `sase-17x.13.10.6--plan`, `sase-17d.12.*`) | `sase agent list -a`. These are the “restart all affected agents” the prompt asked about. |
| **16:09:18** | **Python mirrors land:** `d86bcc3ac` bumps scan wire 9→10 | git |
| **16:09:43** | TUI in-process restart (same pid 1022431, new session id) | tui_toasts `session_started_at=20:09:43Z` |
| 16:09:59 | `Axe: 38 error(s) in the last hour` | toast + digest_20260925_160958 |
| 16:10:14 | `Marked 83 notifications read` | operator clearing the inbox by hand |
| 16:10:16 | `Services unhealthy: host stopped` | service host did not come up with the TUI restart |
| 16:08–16:25 | More kill/launch pairs; at 16:25 `Started 7 agent(s)` (this research swarm) | tui_toasts |
| 16:42–16:43 | Two `No agents marked` warnings from other TUI pids | mark-gated bulk actions fired with an empty mark set |

Net operator procedure, reconstructed from artifacts rather than from a written runbook:

1. Notice the fleet is dead (error toasts, axe digest, agents flipping to FAILED).
2. Try a host update + service restart from the shell (`sase update -y && sase agent index gc && ace --restart-service`) — this *applied* the new core and made the mismatch total.
3. Kill stuck workflows one PID at a time from the Agents tab.
4. Relaunch replacements one or a few at a time (`Started 1 agent(s)` × N, then a 7-wide swarm later).
5. Remove leftover `index.lock` files from the shell.
6. Wait for a stitch that bumps Python mirrors (`d86bcc3ac`).
7. Restart ACE from the Update panel (`↻ Restart available` → Restart ACE).
8. Discover the service host is stopped; mark 83 notifications read.

There is **no** `sase revive-log` trail for this recovery (`sase revive-log --since -1d` currently crashes on naive-vs-aware datetime comparison in `iter_revive_events`, so even if revive events existed they are not queryable). Recovery was kill + relaunch, not `!R` revive of dismissed bundles.

---

## 3. What the TUI already gives the operator

The Agents tab is not empty of recovery tools. The problem is that none of them are *incident-shaped*.

### 3.1 Per-row

| Binding | Behavior | Fit for this incident |
| --- | --- | --- |
| `R` | Edit prompt and relaunch. Does **not** kill/dismiss. Allocates a retry name (`allocate_retry_name`) and leaves the FAILED row holding its workspace. | Wrong. New clone may still be taken from a skewed tree; old workspace stays held. |
| `x` | Kill/dismiss the focused row (or every marked row). | Necessary to release workspaces. Does not relaunch. |
| `,x` | Kill/dismiss focused **or marked** rows, then open a prompt stack for relaunch with `%id:!name` forced reuse. CLI twin: `sase agent restart NAME`. | Right primitive, wrong cardinality: one row, or a mark set the operator must build by hand. |
| `,X` | Kill-and-edit the session's last launched agent, ignoring marks. | Useful for a single botched launch, not a fleet. |
| `F` | Fork. | Starts more work on a dead host path. |

`R`'s own docstring is the giveaway: “Like `_kill_and_edit_agent` but without killing or dismissing the existing agent.” For schema skew, that is the failure mode.

### 3.2 Bulk, but mark-gated

- `m` marks the current row (or all top-level rows in a focused collapsed group) and advances.
- `u` clears marks.
- If any marks exist, `,x` and `x` act on the mark set.
- Empty mark set → toast **`No agents marked`**. That toast fired twice at 16:42–16:43 during this incident's aftermath.

There is **no** Agents-tab “mark all failed” / “mark all visible”. `mark_all_unread_done_agents_read` (`,u`) only flips unread chips. Plugin install has `*` mark-all; Projects has mark-all; Agents does not.

### 3.3 Cleanup panel (`X`) — closest existing bulk UI

`X` opens cleanup: `d`/`D`/`k`/`K`/`m`/`g`/`t`/`c`. Custom selector (`c`) already has:

- `f` filter failed
- `a` toggle all filtered
- `Enter` confirm

That is a low-keystroke path to **dismiss** every FAILED row. It does not relaunch, does not detect schema skew, and does not refuse to proceed while core/Python still disagree.

### 3.4 Filter bar

`status:FAILED` is a first-class Agents query (docs even use `#3 status:FAILED` as the saved-slot example). The header shows `filter: status:FAILED [n/m]`. Filtering does not select, mark, or recover. It only shrinks the roster so the operator can `m` through it.

### 3.5 Provider Drain — the pattern to copy

When a provider is hard-disabled, and `provider_drain` is on, the TUI already:

1. Plans off-thread via `plan_provider_drain()`.
2. Pushes `ProviderDrainPromptModal` with counts of movable vs left-alone.
3. Offers `r` relaunch all, `m` relaunch on a chosen model, `l` leave alone.
4. Submits a durable `agent.drain` proc, toasts `Relaunched N agent(s); M left alone`.

That is incident UX. Schema skew is the same shape: many agents stranded by one host cause. Drain is provider-keyed; this incident needs an **error-class** key.

`sase agent restart NAME` is the per-row engine drain already uses. It is one name. There is no `sase agent restart --failed --error schema-mismatch`.

### 3.6 Update panel Restart ACE

While imported git roots are stale, `,U` adds **Restart ACE** (`x`/`X`): “Running code changed on disk; restart after tracked procs finish.”

That reloads the TUI process. It does **not**:

- restart the service host (hence `Services unhealthy: host stopped` immediately after the 16:09 restart),
- dismiss failed agents,
- relaunch the fleet,
- detect that workspace clones still contain schema-9 Python.

The toast that drives the operator here (`↻ Restart available`) is easy to treat as “the fix.” Today it is only half a fix.

### 3.7 Notifications

Each failed agent posts `ViewErrorReport`. Axe posts a digest of the last hour. The operator marked **83** notifications read in one stroke at 16:10:14. That is the inbox saying “this was one incident” without the TUI grouping it as one.

### 3.8 Service health pill

Unhealthy host → `Services unhealthy: <reason>` toast and a red `SVC !` pill. After Restart ACE the host was `stopped`. The operator had already used `ace --restart-service` at 15:09; that flag is not part of Restart ACE.

---

## 4. Gaps this incident punched through

1. **No correlated-failure object.** 38 axe errors + a pile of agent `ViewErrorReport` rows + wait-never-resolve + plan-archive failures look like unrelated fires. They share one cause.
2. **No launch gate while schema-skewed.** Successor agents launched between 15:09 and 16:09 died on bootstrap (`#fork` → `find_named_agent` → scan). The TUI kept offering Launch.
3. **Retry-in-place is the highlighted FAILED action (`R`) and it cannot unpoison a workspace clone.**
4. **Bulk relaunch requires a mark set**, and the empty-set failure is a warning toast, not a “mark the failed ones for me?” prompt.
5. **Restart ACE ≠ restart the control plane.** TUI came back; service host did not; axe chops stayed dead until the host was up *and* Python matched Rust.
6. **Wait graph is not rewritten** when an agent is replaced. `wait_checks` then pages `Wait dependency can never self-resolve` against the corpse directory. That is still firing at 16:46 on `sase-19p.2`.
7. **Workspace holds are per-row.** Mass FAILED = mass held clones. Capacity and disk both suffer until dismiss.
8. **`index.lock` recovery is still a shell `rm`.** The operator did it twice, and plan archive still failed. A lease-lock plan was in flight (`lease_index_lock_recovery.md` / `lease_git_lock_recovery.md`) — that is product work, but the TUI has no lock-recovery action on the failed gate.
9. **`sase revive-log` is broken** (`TypeError: can't compare offset-naive and offset-aware datetimes` in `iter_revive_events`). Post-mortem of revive/retry is not available from the documented CLI.
10. **Dev-install core fast-forward has no TUI warning that it is a fleet-killing event.** The 15:09 shell one-liner is the kind of thing an Update-panel Everything / core rebuild should have refused or drained first.

---

## 5. UX options

### Option A — Mark-all-visible, then existing `,x`

Add `*` or `A` on the Agents tab: mark every row matching the current filter (so `status:FAILED` + mark-all + `,x`).

- **Pros:** Tiny. Reuses kill-and-edit. Matches Plugins/Projects.
- **Cons:** Operator must still know the query, still must have already unskewed Python, still gets a prompt stack of N editors, still leaves wait-graph and service-host and inbox as separate chores. Does not prevent the next core bump from repeating Sep 13 / Sep 25.

Worth doing as a stepping stone. Not sufficient.

### Option B — Cleanup `f` + relaunch

Extend the cleanup custom selector (already has `f` failed / `a` all) with a `r` “dismiss and restart” row that calls `execute_agent_restart` per target.

- **Pros:** The selector UI exists. Low new chrome.
- **Cons:** Cleanup is mentally “throw away,” not “recover.” Easy to dismiss without relaunch. No skew detector, no launch gate, no wait rewrite.

### Option C — Fleet Incident Recovery modal (Provider Drain analog)

Detect a cluster: ≥K FAILED rows in a time window sharing an error class (`schema_mismatch`, `sigterm`, `lease_lock`, …). Raise a modal on the Agents tab (and a sticky header chip).

Copy:

| Drain | Fleet incident |
| --- | --- |
| Cause = one provider hard-disable | Cause = one error class + optional schema pair |
| `r` relaunch movable | `r` recover (dismiss + `execute_agent_restart`) |
| `m` pick a model | `u` open Update if still skewed |
| `l` leave alone | `d` dismiss only / `l` leave alone |
| Durable proc + toast | Same, plus “blocked: python 9 / core 10” |

Refuse `r` while `AGENT_SCAN_WIRE_SCHEMA_VERSION` ≠ last successful Rust payload version (probe one `scan_agent_artifacts` in a doctor-style check). Point `u` at Restart ACE **and** service-host restart.

After recover: walk `waiting.json` waiters whose target artifact dir is a corpse; either retarget to the new same-name run or mark them `never-resolve` in the UI with a one-key kill.

Cluster inbox rows into one incident id so “Marked 83 notifications read” is not the recovery tool.

- **Pros:** Matches how this operator actually thinks (“everything died, restart the affected agents”). Reuses drain/restart code. Teaches the right primitive (dismiss+fresh clone) instead of `R`. Extends to the next error class for free.
- **Cons:** Real design work (clustering, probe, wait rewrite). Must not auto-fire on a single flaky agent.

### Option D — Update-panel preflight drain on wire-schema bump

When the incoming `sase-core` / host package changes `AGENT_SCAN_WIRE_SCHEMA_VERSION` (or index schema), the Update confirmation names the blast radius: “This rebuild will crash every running agent and every live workspace clone. Drain N agents, then apply, then Restart ACE + service host, then recover.”

The 15:09 shell line `sase update -y && sase agent index gc && ace --restart-service` is exactly this sequence **without** the drain and **without** the Python mirror. TUI Update should not be allowed to reproduce it silently. CLI `sase update -y` should print the same warning.

- **Pros:** Prevents the incident, which is better than recovering from it. This machine has now done it twice in twelve days.
- **Cons:** Does not help if core is rebuilt outside Update (editable linked checkout, `just rust-install` from an agent, chop). Still need Option C for the cases prevention misses.

### Option E — N−1 wire compatibility in Python

Accept `schema_version in {N, N-1}` and fill defaults. The conversion helper already drops unknown keys.

- **Pros:** A one-version lag in a workspace clone would survive.
- **Cons:** Core *removed* the `session` alias and flipped spellings in the same bump. N−1 would still break on renamed keys. Tests currently require hard equality. Buys time; does not replace recovery UX. Workspace clones that are *two* versions behind (or that miss a Python-only mirror stitch) still die.

### Option F — Pin or refresh the Rust binding per workspace

Clone `sase_core_rs` with the workspace, or refuse to import a global extension whose schema ≠ the clone's Python constant.

- **Pros:** Makes the mixed-binary cut impossible.
- **Cons:** Heavy (wheel per workspace, or a probe at agent start that fails closed with a *targeted* error instead of a scan crash mid-bootstrap). Complements C/D; does not give the operator a recover button.

### Option G — Colon command / command palette

`:recover failed`, `:drain schema`. There is prior research on a TUI colon line (`tui_colon_command_line`). Power-user friendly, invisible in a panic, and still needs the same backend as C.

### Option H — Doctor check + launch freeze

`sase doctor` probe: call Rust scan, compare `schema_version` to `AGENT_SCAN_WIRE_SCHEMA_VERSION`. On mismatch, freeze Launch, freeze axe chops that scan, and show the incident banner.

- **Pros:** Cheap safety latch. Stops the 15:10–16:09 “launch more, they die too” phase.
- **Cons:** Doctor is not where the operator is during the fire. Needs a TUI surface (C) to act.

---

## 6. Recommended solution

**Do C + D + H, in that order, with A as a same-week convenience.**

### Why C is the TUI answer

The operator's goal, stated in the prompt, was: a failure caused all sase agents to fail, and they had to restart all affected agents. The TUI made them do that as:

- many `x` kills,
- many 1-agent launches,
- a shell `sase update` that deepened the hole,
- Update-panel Restart ACE that brought the TUI back without the service host,
- `Marked 83 notifications read`,
- two `No agents marked` dead-ends.

Provider Drain already solved this UX for a different cause. Fleet Incident Recovery is the same modal, keyed on error class, with two extra predicates this incident proved are mandatory:

1. **Do not relaunch into a still-skewed runtime.** Probe Rust vs Python before `r`. If skewed, the only enabled action is `u` (Update / Restart ACE **and** service host). That is the difference between the 15:44 relaunch burst (still dying) and a post-16:09 relaunch (can live).
2. **Dismiss then restart, never `R`.** Schema-skewed workspace clones are radioactive. `execute_agent_restart()` already deletes the old run's artifacts (chat kept) and relaunches the stored prompt under the same name into a new clone. That is the correct engine. Surface it as `r` Recover N agents, not as “retry.”

The modal copy should say the cause in the operator's words, not the exception's:

> 12 agents failed because sase-core is speaking agent-scan schema 10 and these runs still speak 9. Retry keeps the old workspace and will fail again. Recover dismisses them and relaunches into fresh clones.

### Why D has to ride along

Without a preflight, the next linked `sase-core` fast-forward repeats Sep 13 and Sep 25. Update already knows how to drain tracked procs before Restart ACE. Extend that drain to **running agents** when the incoming core changes a wire schema constant. CLI `sase update -y` should not be a quieter path around it.

### Why H is the latch

A 20-line doctor/TUI probe (`got 10, expected 9`) would have frozen launches at 15:09 instead of letting `#fork` successors die for an hour. Put the probe on the Agents header next to `load:` / `SVC`. Red chip: `scan wire 10≠9` — click opens the incident modal.

### Why not E or F as the headline

N−1 compatibility and per-workspace binding pins are good hardening (especially F's fail-closed probe at agent start). They do not give the operator a way to restart the affected fleet, which is the UX the prompt asked for. They also would not have saved this bump: core dropped the `session` alias in the same flip.

### Concrete TUI shape

1. **Header chip** when probe fails or when ≥3 FAILED rows share an error class in the last hour: `INCIDENT 12 schema-skew`.
2. **Click / `!i` / footer action** opens the modal (do not steal `R`).
3. **Modal body:** cause, schema pair, counts (recoverable / held-workspace / waiter-never-resolve / skipped monitors), and whether recover is blocked on Update.
4. **Keys:** `r` recover, `d` dismiss only, `u` Update+service, `l` leave, `Enter` on the safe default (`u` if skewed, `r` if not).
5. **Durable proc** `agent.fleet_recover:<error_class>` so it shows in Procs, dedups, and survives TUI restart — same as `provider-drain:<provider>`.
6. **Inbox:** one `FleetIncident` notification with the digest path, instead of 38+ agent errors. Keep the per-agent reports as attached files.
7. **Wait repair pass** at the end of the proc: retarget same-name waits; toast the ones that cannot be retargeted.

### What this would have changed today

| Actual | With C+D+H |
| --- | --- |
| 15:09 `sase update -y` rebuilds core under a live fleet | Update/CLI preflight: drain or abort |
| 15:10–16:09 new launches die on `#fork` scan | Header chip + launch freeze |
| 15:38–16:25 one-by-one kill/launch | One modal, one `r` after 16:09 |
| 16:09 Restart ACE, host stopped, 83 notifications | Restart ACE+host as `u`; one incident notification |
| 16:42 `No agents marked` | Recover does not use the mark set |
| 16:46 wait-never-resolve still paging | Repair pass retargets or names the leftovers |
| Sep 13 repeat | Same chip, same modal, operator already knows `r` |

### Out of scope for the first cut (but keep the doors open)

- Colon `:recover failed` (G) as a binding onto the same proc.
- Mark-all-visible (A) for unrelated bulk work.
- N−1 schema (E) as a core hardening stitch, reviewed separately because of renamed keys.
- Fix `sase revive-log` tz comparison — small, do it, it is not the recovery UX.

---

## 7. Evidence index

| Item | Path / ref |
| --- | --- |
| Schema constant (now 10) | `src/sase/core/agent_scan_wire_records.py` |
| Hard mismatch raise | `src/sase/core/agent_scan_wire_conversion.py` ~486–490 |
| Rust scan call | `src/sase/core/agent_scan_facade.py` `scan_agent_artifacts` |
| Python mirror stitch | `d86bcc3ac` 2026-09-25 16:09:18 -0400 |
| Prior schema-9 mirror | `654335d55` 2026-09-13 09:55:37 -0400 |
| Sample agent error report | `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/25/20260925153415/error_report.md` |
| Axe digest (38) | `~/.sase/axe/error_digests/digest_20260925_160958.txt` |
| Operator update command | zsh history 15:09:36 `sase update -y && sase agent index gc && ace --restart-service` |
| TUI toasts | `~/.sase/logs/tui_toasts.jsonl` (pid 1022431) |
| Retry-without-dismiss | `src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py` `_retry_edit_agent` |
| Kill-and-edit / marks | `src/sase/ace/tui/actions/agents/_marking_kill.py`; docs `docs/ace.md` Agents actions / `,x` |
| Cleanup failed filter | `src/sase/ace/tui/modals/agent_cleanup_custom_modal.py` (`f`, `a`) |
| Provider drain analog | `docs/ace.md` § Provider-drain relaunch prompt; `src/sase/agent/_drain_types.py` |
| Restart ACE copy | `src/sase/ace/tui/update_panel_state.py`; `src/sase/ace/tui/actions/update_toast.py` |
| Held-workspace copy | `src/sase/axe/runner_reporting.py` |
| Revive-log tz bug | `src/sase/logs/run_log.py` `iter_revive_events` |
| Recurring mismatch (9 vs 8) | inbox 2026-09-13 08:24–08:32 |

---

## 8. Uncertainties

- The linked `sase-core` fast-forward that emitted schema 10 may have been the 15:09 `sase update -y`, an agent `just rust-install`, or a chop. The operator command at 15:09 is sufficient to *apply* it; I did not pin the first commit that landed in the linked checkout.
- `sase notify list` is capped; the 38-error axe digest plus the named `ViewErrorReport` rows are a lower bound on agent deaths, not a census.
- I did not read other swarm reports. Conclusions above are from logs, git, code, and the live agent list only.
- Whether Restart ACE is supposed to bounce the service host is a product question; empirically it did not, and the toast said `host stopped`.
