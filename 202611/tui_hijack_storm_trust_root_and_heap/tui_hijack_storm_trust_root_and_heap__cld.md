# TUI Performance Regressions: Root Causes and a Safe Fix Order (cld)

Researcher: `cld` (one of five independent researchers). Date: 2026-11-16. Host: athena
(64 CPUs, 62 GB RAM). Installed TUI: editable checkout at `8254254e2f`.

## TL;DR

The TUI did not slow down for a single reason. Three separate problems are stacked on top
of each other. All three are measured, not guessed, and each has a narrow fix.

| #   | Problem                                                                                                                                                          | Since                                  | User-visible cost                                                                                                                                           | Fix size / risk                                     |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| A   | **Hijack-decision storm.** Every Agents footer refresh starts an O(archive) `find_named_agent` scan on the shared default thread pool. The cache key changes on every roster refresh, so results are never reused. | `d26b581253` (first run 2026-11-16 10:54 UTC) | Live TUI at **23 GB RSS + 24 GB swap 17 min after start**. 31 of 45 threads stuck in hijack decisions. 26% of wall time frozen. GC pauses up to 50 s. | Small, TUI-local, low risk. **Hotfix now.**         |
| B   | **Trust-identity off-by-one.** `AceApp.__init__` hits an O(projects²) config-merge scan through local-command trust enforcement.                                | `021cd73021` (2026-11-12)              | `app_construct_seconds` went from about **1.0 s to 5.0–6.3 s**. Every startup is about 4.5 s slower.                                                       | Small. Semantics-preserving memo is low risk.       |
| C   | **Chronic heap and roster-load costs.** About 18–21M live allocated blocks make every full GC take about 3 s. The roster loader calls an uncached project-alias lookup 303× per load. | Gradual (Aug→Nov)                      | 95% of ≥1.5 s hitches overlap a full GC. First agents load is about 4–5 s. Time to a usable Agents list went from ~5 s (Aug/mid-Oct) to ~11.6 s.            | Memo is small. Heap diet is medium and needs a census. |

**Recommendation:** fix in the order A → B → C1 (alias memo) → C2 (heap diet guided by the
existing census). This is surgical work, not a re-architecture: no new data model,
renderer, or process split. Only one piece of new instrumentation is worth adding: a
default-executor saturation gauge in the existing memory heartbeat. It would have
exposed problem A within minutes. Everything else can be diagnosed with telemetry the
TUI already writes.

---

## 1. What the user is feeling, quantified

### 1.1 Startup: real sessions only, weekly medians

Source: `~/.sase/logs/tui_startup.jsonl` (2,255 records since 2026-08-12). The filter is
`initial_tab == "agents"` and `index_row_count > 0`, which drops test and fixture
launches. Without that filter, the fixture TUIs (empty rosters, ~0.35 s) make late
September look misleadingly fast.

| Week of    | n   | pre-mount p50 | `app_construct` p50 | `app_module_import` p50 | on_mount→visible p50 | visible p90 | agents_ready p50 | index rows p50 |
| ---------- | --- | ------------- | ------------------- | ----------------------- | -------------------- | ----------- | ---------------- | -------------- |
| 2026-08-17 | 135 | 0.77          | –                   | –                       | 3.27                 | 4.3         | 4.05             | 644            |
| 2026-09-14 | 231 | 1.11          | 0.43                | 1.97                    | 6.99                 | 10.0        | 8.12             | 735            |
| 2026-10-12 | 59  | 1.44          | 0.53                | 2.04                    | 3.50                 | 8.7         | 4.96             | 379            |
| 2026-10-26 | 84  | 1.63          | 0.74                | 2.25                    | 5.74                 | 7.1         | 7.37             | 521            |
| 2026-11-02 | 51  | 1.61          | 0.73                | 2.09                    | 7.15                 | 9.0         | 9.05             | 704            |
| 2026-11-09 | 38  | **5.77**      | **5.02**            | 1.96                    | 7.70                 | 16.1        | **11.47**        | 605            |
| 2026-11-16 | 3   | 6.25          | 5.25                | 2.25                    | 5.36                 | 6.4         | 11.62            | 300            |

Notes:

- The `agents_ready_seconds` anchor is the `AceApp` init stamp. It does **not** include
  interpreter/CLI import (~0.2–0.8 s) or `from sase.ace.tui import AceApp` (~2.0 s).
  Real wall time from typing `sase tui` to a usable Agents list is therefore about
  **14 s** today, versus about **7 s** in mid-October.
- Grouped by `source_revision`, the step change is between `671ff5bde0` (11-11 17:45 UTC,
  construct 1.03 s) and `ea4121387b` (11-12 10:33 UTC, construct 6.21 s). Twelve commits
  sit in that range. Profiling (§3) pins the cost on the local-command trust enforcement
  commits.
- Post-mount time (`visible_ready`) mostly tracks roster size (`index_row_count`) and
  host load (`load1` of 10–37 on 64 cores in late Oct/Nov). It is not a single code step.
  §4.2 shows where that time goes.

### 1.2 Runtime: the stall watchdog and memory heartbeat

Source: `~/.sase/logs/tui_stalls.jsonl{,.1}`. It rotates quickly, so only about 6 h are
retained: 2026-11-16 00:23–06:20 local. That window happens to straddle the restart into
the hijack build, which gives a clean before/after comparison.

| Window                                                   | Rev          | RSS (GB)             | Swap (GB)          | Allocated blocks | ≥1.5 s hitches            | Share of wall frozen | Hitches within 30 s of a keypress | Worst gen-2 GC |
| -------------------------------------------------------- | ------------ | -------------------- | ------------------ | ---------------- | ------------------------- | -------------------- | --------------------------------- | -------------- |
| Pre-restart, 5.5 h (pid 88182, 12 h uptime)              | `082f2bc705` | 3.1–5.6              | 0.5–0.7            | 18–21 M          | 210 (698 s)               | 3.5%                 | 7 (20 s)                          | ~4 s           |
| Post-restart, 32 min (pid 88182 after exec, then 2180945) | `8254254e2f` | **20.9–35.1**        | **up to 24.2**     | **106–150 M**    | 72 (493 s)                | **25.7%**            | **25 (147 s)**                    | **50.6 s**     |

Live check at the time of writing: `free -g` showed 36 of 63 GB swap in use. Process
`sase tui` (pid 2180945) had `VmRSS` 23.4 GB and `VmSwap` 24.4 GB after 17 minutes of
uptime. **This is the acute problem, and it also degrades every agent on the host.**

---

## 2. Problem A: hijack-decision storm (acute, introduced today)

### 2.1 Evidence

I ran `py-spy dump --pid 2180945` three times, 3 s apart. All three samples were
identical: **31 of 45 threads** had this stack.

```
_find_named_dismissed_bundle  (sase/agent/names/_lookup_named.py:222)   ← json.load of every bundle
_find_named_agent_candidates  (sase/agent/names/_lookup_named.py:189)
find_named_agent              (sase/agent/names/_lookup_named.py:79)
_default_find_agent           (sase/agent/hijack/facts.py:421)
resolve_hijack_subject        (sase/agent/hijack/facts.py:100)
resolve_and_decide            (sase/agent/hijack/facts.py:414)
compute_hijack_decision       (sase/ace/tui/actions/agents/_hijack_decision.py:150)
_compute_hijack_decision_sync (sase/ace/tui/actions/agents/_hijack_decision_cache.py:85)
concurrent/futures/thread.py  (default asyncio executor worker)
```

The default executor on a 64-CPU host has `min(32, cpu+4) = 32` workers. Hijack decisions
fill 31 of them and an archive build fills the last one. **Every other `asyncio.to_thread`
in the TUI queues behind them.** That includes agent loads, the delta-load prep stage,
and telemetry writes. This explains why "full" agent loads in this process took 14–23 s,
almost all of it in `decode`, compared with 2.1 s for the same 131-agent roster at
startup (`tui_agent_loads.jsonl`, pid 2180945).

I measured the cost of one call offline:

| Call                                                                  | Wall time   | Peak RSS delta |
| --------------------------------------------------------------------- | ----------- | -------------- |
| `_find_named_dismissed_bundle("<miss>")`                              | 16.9 s      | (25 MB traced) |
| `find_named_agent("<miss>", include_dead=True)` (what hijack calls)   | **32–38 s** | **+2.2 GB**    |

`find_named_agent` makes two full passes:

- a raw `scan_agent_artifacts(projects_dir)` over **every** project's artifacts, with no
  index;
- on a miss, a fallback that `json.load`s **65,875 dismissed bundles (591 MB)**.

Thirty-one of these running at once explains the 20–35 GB RSS. It also explains the GC
census for this process: **207,837 `AgentArtifactRecordWire`** objects and 8.1M
survivors, two minutes after start.

### 2.2 Why it never converges

`src/sase/ace/tui/actions/agents/_hijack_decision_cache.py` has these behaviors:

- **Cache key `(row identity, roster_generation)`.** `bump_roster_generation` runs on every
  `_agents` assignment and every in-place status mutation, which means every refresh and
  delta poll. The key goes stale within seconds.
- **In-flight dedup uses the same key.** After each refresh, a new compute starts even
  though an older one for the same row is still running.
- **`_finish_hijack_decision` drops the result when the generation has moved**
  (`current_key != key`). A compute that takes longer than the refresh interval
  (32–38 s against an interval of a few seconds) is therefore never stored, and the
  cache never warms up.
- **Scheduling ignores the cheap gate.** `_apply_agent_footer_update` calls
  `_schedule_hijack_decision(current_agent)` before
  `cheap_hijack_ingress_available()` is consulted. Done, dismissed, named-proc, and bulk
  rows also trigger the full scan, and those are exactly the rows most likely to miss
  and fall through to the 65k-bundle scan.
- **Many trigger sites.** About 20 call sites go through
  `_refresh_agent_footer_bindings_only`: detail-panel updates, deck navigation, marking,
  and others. The trigger rate is therefore "every selection or panel change, plus every
  roster refresh".
- **Unbounded concurrency.** Work goes to the shared default executor.

This breaks a rule the `tui_perf` memory already captures in spirit ("off the event loop
is not off the pump"). It adds a new corollary: **off the event loop is not off the
default executor either.** Unbounded per-feature background work starves every other
`to_thread` caller.

### 2.3 Fix (hotfix-sized; all TUI-local)

In priority order. The first two alone stop the storm.

1. **Gate scheduling on the cheap check.** Call `_schedule_hijack_decision` only when
   `cheap_hijack_ingress_available(agent)` is true.
2. **Key on stable identity, single-flight per row.** Dedupe in-flight work by row
   identity alone. Key the cache on identity plus a small fingerprint of the
   decision-relevant fields: status, pid, workspace_num, and the `hijack_*` fields.
   Do not use the global roster generation. Store a finished result if the row identity
   is still present, even if the generation moved.
3. **Bound the concurrency.** Use one dedicated worker, or `asyncio.Semaphore(1)`, with
   latest-wins semantics: a newer request for a different row supersedes a queued one.
   Never use the default executor for this.
4. **Stop calling `find_named_agent` from the TUI.** The row already carries its
   artifacts dir and identity. Pass a `deps` finder (the `deps` hook already exists on
   `resolve_and_decide`) that resolves from the row or the in-memory roster in O(1).
   Keep the archive scan only for the CLI's `sase agent hijack --explain <name>`.
5. **Follow-up outside the TUI.** `find_named_agent`'s dismissed-bundle fallback should
   use the name registry or an index instead of `rglob("*.json")` plus `json.load` of
   591 MB. Any CLI caller pays 17 s today.

Expected result: RSS returns to the pre-restart baseline of about 4 GB, the executor is
free again, and hitches drop back to the pre-restart profile (§4). The hijack epic
`sase-1t2` is still in progress (latch phases `sase-1t2.8.x` touch the same TUI
surfaces). Coordinate the fix there, but do not let it wait for the epic.

Until the hotfix lands, any TUI restarted on `≥ d26b581253` will storm again. The safe
interim options are to quit the TUI when it is not in use, or to temporarily pin the
installed checkout to `082f2bc705` (the last steady build). The second option is a
global-install change, so it should go through a `/sase_gate`.

---

## 3. Problem B: trust-identity off-by-one makes construction O(projects²) (since 11-12)

### 3.1 Evidence: cProfile of `AceApp()` construction

I replicated `handle_ace_command` up to and including `AceApp(...)`, with session
registration stubbed out. Total 6.2 s:

```
AceApp.__init__                                   6.10 s
  init_late_startup_state → build_app_bindings    5.38 s
    _artifact_subtab_bindings → resolve_artifacts_subtabs → _build_artifacts_subtabs
      _load_workspace_provider_records ×10        5.32 s
        resolution_config → load_merged_config_for_local_path   4.92 s  (120 calls, 110 recursive)
          _trusted_yaml_loader → effective_local_layer → _evaluate_with_flag_on
            _project_identity_for → _project_identity ×10        3.77 s
              → load_merged_config_for_local_path per registered project
              → WorkspaceStore(...) → `git remote` subprocess (100 calls, 0.44 s)
        merge_config_sources ×121                 4.04 s
          sase_core_rs.axe_config_compose ×121    2.59 s
  init_agent_state → load_dismissed_agents        0.48 s
```

### 3.2 Root cause

`local_trust_enforcement._checkout_root_for_local_path()` probes `local_path.parent`.
For the canonical layout `<repo>/sase/sase.yml`, that directory is `<repo>/sase`.
`content_layout._is_project_root(<repo>/sase)` returns **True** because
`<repo>/sase/sase.yml` exists, and the legacy-layout check treats any directory that
contains a `sase.yml` as a project root. As a result:

- the "root" is `<repo>/sase`, so the fast primary-match branch of `_project_identity`
  never matches;
- it falls into the scan over **all** registered projects. For each one, the scan
  merges that project's config (each merge runs the Rust axe compose) and shells out to
  `git remote`;
- the artifacts discovery calls this once per project (10 projects), giving about
  10 × 11 = 121 full merges and 100 git subprocesses, synchronously, inside `__init__`.

I verified this for every registered project: in all 10 cases, enforcement root ≠
registered primary.

**Experiment.** I patched `_checkout_root_for_local_path` in-process to return
`<repo>` for `<repo>/sase/sase.yml`. Construction went from **6.9 s to 1.9 s**
(n = 2 each, same host, back to back).

### 3.3 A correctness issue hiding behind the perf issue (flag to the trust owners)

For the sase primary:

- **Enforcement** computes `checkout:v1:/…/sase-org/sase/sase`.
- **`sase config trust allow`** with no path argument, run from the repo root, computes
  `project:v1:/home/bryan/.sase/projects/gh_sase-org__sase:/…/sase-org/sase`.
- **`sase config trust allow <repo>/sase/sase.yml`**, the form the warning suggests,
  happens to compute the same wrong `checkout:v1:<repo>/sase`, because it runs the same
  `discover_project_root` over the file's parent.

So the two CLI spellings record different keys, and workspace checkouts
(`sase_<N>/sase/sase.yml`) never inherit project-scoped trust. That is consistent with
the "skipped (no-acknowledgment)" warning every command printed in this session.

**Safety implication:** correcting the root changes trust identity keys. Acknowledgments
already recorded under `checkout:v1:<repo>/sase` would stop matching unless the fix
includes a compatibility lookup. That is why I recommend splitting the perf fix from
the identity fix.

### 3.4 Fix options

| Option                                                                                                                                                                                                                                               | Startup win                                     | Risk                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **B1 (recommended first). Semantics-preserving memo.** Inside `_project_identity`, memoize the per-primary "registry membership" result (primary → set of checkout dirs). Key it on the registry file's `mtime_ns` plus the project-records token. The scan becomes O(P) once instead of O(P²). | ~6.9 → ~2.3 s (estimate: 1.9 s measured + ~0.4 s for one scan) | Very low. Identities are unchanged, and keying on mtime keeps newly created workspaces correct. |
| B2. Fix the root discovery (prefer `<repo>` when the probe dir is named `sase` and `<repo>/sase/sase.yml` exists), with a compat read of the old `checkout:v1:<repo>/sase` key.                                                                       | ~6.9 → 1.9 s (measured)                         | Medium. Changes trust keys and touches `discover_project_root` callers. Owner: trust epic (`sase-1sb`). |
| B3. Serve artifact sub-tab descriptors from a persisted last-known snapshot at construction, and reconcile on the existing daemon refresh thread (stale-while-revalidate across restarts).                                                              | Removes the remaining ~1.1 s discovery          | Medium. Keybindings are built from the descriptor list, so a late change needs a rebind.     |
| B4. A "non-executable" config read for sidecar-policy discovery that skips trust identity.                                                                                                                                                           | Large                                           | Higher. Contradicts the trust design's "one decoded snapshot is digested, filtered, merged" rule. Needs owner sign-off. |

Also memoize `_lower_macros_and_workflows()` per config token. It is 10 × 30 ms of
identical lower-layer merges per discovery pass.

---

## 4. Problem C: chronic costs, present before both regressions

### 4.1 Runtime freezes are mostly full-GC pauses on a large heap

In the steady-state 5.5 h window before the restart:

- **95%** of hitch episodes (197/207) had GC covering ≥50% of the freeze. 196 of them
  overlapped a **gen-2** collection. GC accounts for 77% of total frozen time
  (`gc_overlap_s` on `tui_hitch_recovered`).
- Gen-2 collections were p50 **3.1 s** and collected about 350k objects each, so there
  is substantial cyclic-garbage churn. Most were the TUI's own `idle` or `rss_backstop`
  collections from `gc_policy.py`. Policy `raised` is working as designed, but each
  pass costs about 3 s because the heap is huge: 18–21M allocated blocks, ~579k frozen.
- The stacks the watchdog blames (`aggregate_clan_runtime`, `_tool_run_chip_ticks`,
  Textual CSS matching) mostly mark **where an allocation tripped the GC**, not where
  the time actually went. Don't optimize those render paths first; they are not the
  bottleneck.
- Caveat: the user was idle overnight in this window (`last_keypress_age_s` ≈ 3.7 h for
  most hitches). Only 7 hitches landed within 30 s of a keypress, so the steady-state
  *felt* cost was modest. After the hijack build it was 25 hitches and 147 s in
  32 minutes.

The only census on disk (`SASE_TUI_GC_CENSUS=1`, pid 2180945) was taken during the storm,
so it overstates wire records. It still names the families that are retained in a TUI
process and worth auditing:

- agent-scan wire records (`AgentArtifactRecordWire`, `AgentMetaWire`,
  `AgentSessionTurnWire`, `FinalizerStatus*Wire`);
- 402k `PosixPath`;
- 27k `ArtifactReadEvent`, 23k `MemoryReadEvent`;
- 17k `BeadNote`, 16k `BeadTouch`, 14.5k `NotificationPlusOne`;
- 63k Textual `FIFOCache`;
- about 12k completion candidates.

This is the open question of the in-progress phase **`sase-1sl.4`** ("residual-leak
attribution"). Re-take the census **after** the hijack hotfix; any soak measured with
the storm active is contaminated.

### 4.2 First-load and background-load cost: one uncached O(projects) lookup per agent

I ran a cProfile of `_load_agents_with_load_state()`, the same loader the TUI uses
(312 index rows, 479 agents, 551 steps). The decode stage took 1.47 s:

| Hot path                                                                                                                                                                                                            | Time   | Share |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ----- |
| `Agent.get_artifacts_dir → resolve_agent_artifact_timestamp_path → _canonical_project_name → resolve_project_alias_ref → load_project_alias_map → list_project_records` (Rust). **303 calls per load**, 13,985 project records re-parsed. | 0.64 s | 44%   |
| `done_instruction_bundle_files → read_run_manifests → normalize_instruction_manifest` (Rust), 141 calls                                                                                                            | 0.29 s | 20%   |
| Patch parsing, workflow steps, running field                                                                                                                                                                        | ~0.4 s | 27%   |

**C1 fix:** memoize `load_project_alias_map()` per load, or per projects-dir token. This
is a pure function of the project records, so it is safe. It removes about 45% of decode
on **every** full load. Background full loads ran 354–1,381 times a day above the 2 s
slow-load threshold (`tui_agent_loads.jsonl`), so this pays off continuously, not just
at startup. Making the instruction-bundle file list lazy, so it is computed only when the
detail panel needs it, is a second, smaller win.

### 4.3 Lower-priority items (stable; not the "lately" regression)

- **Module import, ~2.0 s.** `-X importtime` shows ~1.36 s cumulative across ~3.5k
  modules. Most of the self time is many small `sase.ace.tui.*` mixin modules, and
  `sase.gate_turn` / `sase.notification_gates` pull in about 440 ms through
  `_agent_enter_action`. This has been flat since September; an import-budget phase
  (`sase-1qn.2`) already exists.
- **Monitor reconcile.** 2.7–11.7 s per run, logged as slow, in the background.
- **Delta-load "prep" of 2.3–2.9 s even for 2–8 changed agents.** Partly executor
  queueing; re-measure after fix A.
- The 2026-11-11 stall spike (372 stalls, one pid, sustained 15:00–24:00) had no TUI
  commits in range. It looks environmental (host load / agent swarm).

---

## 5. Options considered for the overall approach

| Approach                                                                                     | Verdict                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Targeted fixes on the measured hot paths (A → B1 → C1 → C2)**                              | **Recommended.** Each change is small, local, and individually verifiable against telemetry that already exists, and none needs a data-model change.                          |
| Tune GC harder (`gc.disable`, bigger thresholds, more freezing)                              | Not first. The heap is the cause; GC tuning only moves the pause around. `sase-1sl.3` already added the duty-cycle bound.                                                    |
| Move more loading into Rust or a separate process                                            | Not justified by the evidence. The problems are Python-side call patterns (O(P²), uncached O(P) per row, unbounded concurrency), not Python throughput.                       |
| Render-path micro-optimizations (row runtime chips, CSS)                                     | Defer. Those stacks are GC trip points (§4.1).                                                                                                                                |
| Bigger default executor                                                                      | Harmful. It would let the storm consume even more memory.                                                                                                                     |

## 6. Instrumentation: what is (and isn't) needed

Existing telemetry was enough to locate every root cause in this report:
`tui_startup.jsonl` (with `source_revision`), `tui_stalls.jsonl` (with `gc_overlap_s`),
memory heartbeats, `tui_agent_loads.jsonl`, `SASE_TUI_GC_CENSUS=1`, and `py-spy dump`.
**I do not recommend new diagnostic instrumentation**, with one exception, which is a
guardrail rather than a diagnostic:

- **Add a default-executor saturation gauge to the existing `tui_memory_heartbeat`**:
  busy workers, queued work items, and the oldest queued age. Problem A ran for over an
  hour with nothing in the logs naming it. A heartbeat showing `busy=32 queued=N` would
  have named it immediately. It costs one dict per 5-minute heartbeat.

Two low-cost operational tweaks:

- Increase rotation size or retention for `tui_stalls.jsonl`. It currently holds about
  6 h, so the Nov 11 spike's stacks were already gone when I looked.
- Run one census after fixes A and B to drive C2.

## 7. Recommended solution

**Do the work in four small, independently landable steps, in this order.**

1. **Hotfix A (today).** In `_hijack_decision_cache.py` and the footer apply path:
   - gate scheduling on `cheap_hijack_ingress_available`;
   - single-flight per row identity, cached on identity plus a decision-relevant row
     fingerprint, not the global roster generation;
   - one dedicated bounded worker with latest-wins semantics;
   - a row-based `deps` finder so the TUI never calls `find_named_agent`.

   Add a regression test: N refreshes with a slow fake decider must leave at most one
   decision in flight and must not use the default executor. **Verify:**
   `py-spy dump` shows ≤1 hijack thread; the heartbeat shows RSS ~4 GB; hitches within
   30 s of a keypress return to the pre-restart rate.
2. **B1 (this week).** Memoize registry membership in `_project_identity`, keyed by
   registry mtime and the project-records token, plus memoize
   `_lower_macros_and_workflows` per config token. Add a test that counts
   `merge_config_sources` calls during `AceApp()` construction with 10 fake projects and
   asserts O(P). **Verify:** `app_construct_seconds` p50 drops from ~5.2 s to ≤2.5 s in
   `tui_startup.jsonl`. **Separately,** file the trust-identity mismatch (§3.3) for the
   trust owners as B2, with a compat key.
3. **C1.** Memoize `load_project_alias_map` per load or per token. Make
   instruction-bundle files lazy. **Verify:** startup `disk.decode` drops by about 40%
   in `tui_agent_loads.jsonl`, and `visible_ready_seconds` drops accordingly.
4. **C2 (with `sase-1sl.4`).** With A fixed, take `SASE_TUI_GC_CENSUS=1` censuses at
   10 min and 2 h. Bound or evict the top retained families (wire records retained past
   apply, read-event and bead-note histories, completion catalogs). **Target:** gen-2
   pause < 1 s and allocated blocks < 8M.

Projected outcome once 1–3 land: time from `sase tui` to a usable Agents list goes from
about 14 s back to roughly 6–7 s. That is about 4.5 s from B, about 0.6 s from C1, and
the rest from the executor no longer queueing loads. The runtime memory and freeze
regression from today disappears. Step 4 is what makes the steady state feel fast
during long sessions.

Suggested durable lesson for the `tui_perf` memory (the lead decides; it would go
through `/sase_memory_write`): "Background work is not free just because it is off the
event loop. Selection-driven computes must be single-flight per row, keyed on stable
identity, bounded to a dedicated worker, and never O(archive)."

I deliberately did not file task beads. With five researchers on the same request,
the lead's synthesis should file them once, through `/sase_new_task`.

---

## Appendix: method and reproduction

All scripts live under `/tmp/cld_perf/` on athena. They are short Python files that read
the JSONL logs, plus profilers that run with the installed interpreter
`~/.local/share/uv/tools/sase/bin/python`.

- **Startup trend:** group `tui_startup.jsonl` by day, week, and `source_revision`.
  Real-session filter: `index_row_count > 0` and `initial_tab == "agents"`.
- **Construction profile:** `cProfile` around
  `AceApp(query="!!!", auto_start_axe=False, ...)` after
  `set_include_local_config(False)` and `install_process_feature_flags()`, with
  `register_ace_session` stubbed.
  - Unpatched: 6.25 s, 6.90 s, 6.94 s.
  - With `_checkout_root_for_local_path` patched to the canonical root: 1.87 s, 1.90 s.
- **Identity check:** `_project_identity(root, cfg)` for every registered project.
  All 10 returned `checkout:v1:<repo>/sase`, taking ~3.6 s each when run unguarded and
  ~0.4 s each inside the trust-evaluation guard.
- **Live process:** three `py-spy dump --pid 2180945` samples, each showing 31/45
  threads in `compute_hijack_decision`; `/proc/<pid>/status` showing `VmRSS` 23.4 GB
  and `VmSwap` 24.4 GB.
- **Lookup cost:** a fresh interpreter, `find_named_agent("<miss>", include_dead=True)`,
  measured at 32.1 s and 38.1 s, with peak RSS +2.19 GB from a `/proc/self/status`
  sampler. Dismissed bundles counted with `os.walk`: 65,875 files, 591 MB.
- **Stall attribution:** `tui_hitch_recovered.gc_overlap_s` and `gc_generations`, split
  at the 05:53 local restart. Keypress proximity from `last_keypress_age_s`.
- **Roster-load profile:** `cProfile` around `agent_loader._load_agents_with_load_state()`
  after one warm-up load.
- **Commit attribution:** `git log 671ff5bde0..ea4121387b` (trust: `021cd73021`,
  `ea4121387b`) and `git log 082f2bc705..8254254e2f` (hijack: `d26b581253`).
