# SASE TUI Performance: Diagnosis and Recommended Fix Path

Researcher: mus (independent swarm report, `__mus` suffix).
Question: the TUI has slowed down noticeably, including startup. Find the
best/safest way to speed it up significantly.

Method: code inspection plus direct measurement in this checkout
(`sase_28`, `sase-core-revision.txt` `e9b1cf0`), corroborated against live
telemetry on this host (`~/.sase/logs/tui_startup.jsonl`,
`tui_agent_loads.jsonl`, `~/.sase/perf/tui_jk.jsonl`, `tui_trace.jsonl`).
All timings below were reproduced here unless marked as log evidence.

## TL;DR

Two uncached config/trust evaluation paths explain most of the slowdown, and
both are cheap to fix without behavior change:

1. **Startup construct does synchronous provider discovery** — `AceApp.__init__`
   spends ~5.2 s of the ~6.3 s `process_start_to_on_mount` window building
   keymap bindings, which resolves Artifacts subtabs, which loads and
   trust-evaluates merged config once per workspace.
2. **Every Agents load recomputes global config ~7 times** — per-agent
   workspace-retention enrichment calls `configured_held_claim_ttl_days()` →
   `load_merged_config()`, whose `local_config_snapshot()` (YAML read + full
   local-trust evaluation, ~0.4 s) runs *before* the merged-config cache is
   consulted. Warm-cache loads of 145 agents still take ~5 s; production logs
   show 11–23 s `decode` stages for ~131 rows.

Secondary: 11–15 s startup `monitor_reconcile` that settles nothing,
multi-second detail-header I/O per selection (j/k paint p95 434 ms vs the
16 ms target), and a 2–3 s `axe.collect` that opens zero files.

No new instrumentation is needed to start: the existing slow-stage logs and
`SASE_TUI_TRACE` spans already attribute every claim below.

## 1. Measured evidence

### 1.1 Startup split (log evidence, 5 recent startups, Agents tab)

From `tui_startup.jsonl` (latest record, pid 2180945):

| field | seconds |
|---|---|
| `interpreter_cli_import_seconds` | 0.20 |
| `app_module_import_seconds` | 1.68 |
| `app_construct_seconds` | **5.22** |
| `compose_seconds` | 0.01 |
| `process_start_to_on_mount_seconds` | 6.25 |
| `on_mount_to_first_paint_seconds` | 0.22 |
| `visible_ready_seconds` | 5.36 |
| `agents_ready_seconds` | 11.62 |

Construction dominates. Import (~2 s wall for `from sase.ace.tui import
AceApp`, measured with `time.perf_counter`) is real but secondary.

### 1.2 What construction spends (cProfile, fresh process)

`AceApp()` = 6.9 s cum, of which `init_late_startup_state` = 6.4 s →
`build_app_bindings` = 5.4 s → `_artifact_subtab_bindings` →
`resolve_artifacts_subtabs` → `_build_artifacts_subtabs` →
`load_project_provider_records` → `_load_workspace_provider_records` →
`resolution_config` → `load_merged_config_for_local_path` (176 calls) →
`merge_config_sources` + `effective_local_layer` (5.8 s cum) + Rust
`axe_config_compose` (3.2 s self). Chain verified frame by frame in
`src/sase/ace/tui/actions/_state_init_late.py:373`,
`src/sase/ace/tui/keymaps/bindings.py:39`,
`src/sase/ace/tui/artifact_tabs.py:89`,
`src/sase/ace/tui/_artifact_tab_discovery.py:42`.

Note the module already has async refresh machinery for later lookups
(daemon revalidation in `provider_source_token`); only the *first* lookup is
synchronous — and startup is always the first lookup.

### 1.3 Agent-load pipeline (cProfile, two back-to-back loads, 145 agents)

Cold (fresh process) `load_tiered_agents`: 10.7 s. Warm (same process,
caches hot): **5.1 s**. Warm-load attribution by cumulative time:

| frame | cum s | note |
|---|---|---|
| `enrich_agent_from_meta_wire` (1013 calls) | 3.74 | 81% of the load |
| → `build_done_agent_from_record` (311) | 3.06 | |
| → `load_agent_workspace_retention` (1038) | 2.98 | one small file read each; cheap |
| → `configured_held_claim_ttl_days` (**7 calls**) | 2.95 | only 7 agents need it — but each call costs 0.42 s |
| → `load_merged_config` → `local_config_snapshot` | 2.93 | snapshot runs **before** the merged-cache check (`src/sase/config/_sources.py:180` vs cache check after) |
| → `effective_local_layer` / `_project_identity` (7) | 2.72 | git/record-backed identity, uncached per call |
| → Rust `axe_config_compose` (77 calls) | 1.45 self | 11 local layers × 7 global loads |
| per-agent `load_project_alias_map` (315 calls) | 0.65 | `list_project_records` 322×, no per-load memo |
| per-agent `run_bundle_paths` (268 calls) | 0.25 | `done_instruction_bundle_files` |

The actual index query (`query_agent_artifact_index`) costs 0.3–0.4 s.
Everything else is repeated Python-side recompute. This matches production
`disk_substages`: `decode` 11–23 s and `provider` ~1 s for ~131 rows
(`tui_agent_loads.jsonl`, 2026-11-16), and `dismissed_snapshot` 1.8 s on one
startup load.

### 1.4 Interaction stalls (log evidence)

- `tui_jk.jsonl` (n=3171): paint p50 21 ms, **p95 435 ms**, max 552 s. Target
  per `sase/memory/tui_perf.md` is p95 < 16 ms.
- `tui_trace.jsonl`: `build_detail_header_summary` p50 530 ms, p95 18.6 s.
  Slowest lanes: `artifact_reads` 8.3 s, `memory_reads` 7.8 s,
  `agent_page_url` 6.5 s, `skill_uses` 2.3 s, `artifact_file_paths` ≤ 2.3 s.
  The 150 ms `DetailPanelDebouncer` coalesces bursts but each fired build
  still does seconds of lane I/O.
- `axe.collect`: 2.0–2.8 s per span with `file_opens: 0` —
  `collect_axe_status_snapshot` pays `load_axe_config` +
  `probe_orchestrator` + global runner counts, i.e. CPU/subprocess cost with
  no disk-read signature.
- `monitor_reconcile`: 11–15 s on startup with `settled: 0`
  (`_reconcile_dead_supervisors_for_tui` → full monitor-record scan + one
  `agent_meta.json` read per record). Pure overhead when nothing is dead.

### 1.5 Host-load caveat

All production timings were captured at `load1` 6–31 on a 64-core host with
other agents working. Wall-clock numbers inflate under contention; the
*shapes* (per-load recompute counts, 0-file-opens CPU, settled=0) do not.
A/B comparisons for any fix should use the existing benches
(`tests/perf/bench_agent_load_tiering.py`, `tests/perf/bench_tui_trace.py`,
`tests/ace/tui/bench_tui_jk*.py`) on a quiet host, not wall-clock log
deltas on a busy one.

## 2. Root causes, ranked

1. **Synchronous provider discovery inside `AceApp.__init__`** (~5 s).
   Keymap digit-shortcuts force `resolve_artifacts_subtabs()` before first
   paint. Safe because the async-refresh path already exists for every
   later lookup.
2. **Global config recompute per retained agent per load** (~3 s/load).
   `local_config_snapshot()` runs before the merged-cache lookup in
   `load_merged_config()` (`src/sase/config/_sources.py`), and
   `configured_held_claim_ttl_days()` is called per agent instead of once
   per load. Recurs on every full load: startup, `auto_refresh` broad
   loads, revalidates, launch/notification refreshes.
3. **Unmemoized `_project_identity`** (~0.4 s each): `list_project_records`
   plus a merged-config load per candidate project, per evaluation
   (`src/sase/config/local_trust_management.py:141`).
4. **Per-agent, per-load repeat reads**: project-alias map (322 record
   listings/load), instruction-bundle paths (268×), one retention-record
   file probe per agent (1038×, individually cheap, jointly visible).
5. **Startup `monitor_reconcile` (11–15 s, settles 0)** on the critical
   path to `agents_ready`.
6. **Detail-header lanes do seconds of I/O per selection** (artifact reads,
   memory reads, page URL, skill uses). Lane tracing exists
   (`build_detail_header_summary.*` spans); caching/streaming does not.
7. **`axe.collect` 2–3 s with zero file opens** every refresh that takes the
   axe surface — config load + orchestrator probe + global counts.
8. **Eager import closure** (~2 s): TUI startup imports `notification_gates`
   + `macro` + `gate_turn` through the agent-enter/metadata-search chain
   (`_core.py` self-import cost 1.3 s). Real but fourth-order next to 1–2.

Probable "lately" mechanism (inference, flagged as such): none of 1–4 is a
single recent regression. Costs scale with project count (more local
`sase.yml` layers × trust evaluations), archive size (more agents ×
per-agent enrichment), and newer TUI surface area (retention records added
2026-11-01 in `31a28d9618`; bead/K-card enrichments; clan/wave assembly).
Growth turned linear per-load waste into the dominant term.

## 3. Recommended solution

Do Phase 1 first — it is behavior-preserving, needs no new infrastructure,
and attacks the two biggest measured costs. Phase 2 removes startup's
synchronous discovery. Phase 3 addresses interaction stalls.

### Phase 1 — memoize the load path (biggest win, lowest risk)

a. **Hoist `configured_held_claim_ttl_days()` out of the per-agent loop.**
   Compute once per load (or per config token) and pass it into
   `load_agent_workspace_retention`/`enrich_agent_from_meta_wire`. Kills the
   7× global-config recompute inside every Agents load. Expected: warm
   `decode` −3 s.
b. **Check the merged-config cache before `local_config_snapshot()`.**
   Restructure `load_merged_config()` (`src/sase/config/_sources.py:180`)
   so a token-keyed fast path avoids the YAML read + trust evaluation when
   the merged entry is fresh; only compute the snapshot on miss. This fixes
   the general shape, not just the TTL caller (startup discovery benefits
   too). Cache key must keep the existing `(token, content_key, trust_key)`
   semantics — an over-broad key would serve stale rows (tui_perf rule 8);
   every `clear_config_cache()` caller must invalidate the new memo.
c. **Memoize `_project_identity(root, config_path)`** on `(root, mtime_ns,
   size)` with the same invalidation. Removes ~0.4 s per evaluation site.
d. **Per-load memo for `load_project_alias_map` and `run_bundle_paths`.**
   Thread a small load-scoped cache through
   `_load_agents_from_all_sources` instead of adding globals; frees ~0.9 s
   warm without any cross-load staleness risk.

Predicted effect: warm full load 5 s → ~1 s (index 0.4 s + decode ~0.5 s);
cold load −7 s; startup `agents_ready` 11–13 s → ~5–6 s even before Phase 2.

### Phase 2 — startup off the discovery path

e. **Defer Artifacts digit-shortcut bindings until after first paint.**
   Build `_app_bindings` with fixed tabs only in `init_late_startup_state`;
   schedule `resolve_artifacts_subtabs()` + `BindingsMap` update via the
   existing deferred-release path (`_release_startup_deferred_loads`) or one
   `call_after_refresh`. The provider-token daemon thread already keeps
   later lookups fresh, so this only changes *when* the first answer
   arrives, not how. Expected: `process_start_to_on_mount` 6.3 s → ~1 s;
   `visible_ready` then gates only on the (Phase-1-cheapened) Agents load.
   Fallback: if digit shortcuts must exist at first paint, serve the
   four fixed tabs synchronously and merge provider tabs when ready.
f. **Lazy-import the agent-enter/metadata-search chain** (the
   `notification_gates`/`macro`/`gate_turn` closure) out of
   `actions.agents._core` module import. Saves a fraction of the 1.7 s
   `app_module_import`; do it only if Phase 1–2 leave import on the
   critical path.

### Phase 3 — interaction stalls (after 1–2 land and re-measure)

g. **Idle-gate `monitor_reconcile`**: skip the startup pass when the roster
   signature shows no monitor rows, else defer past `visible_ready`; keep
   the backstop for correctness. Removes up to 15 s from `agents_ready`
   when nothing needs settling.
h. **Detail-header lanes async + cached**: resolve `artifact_reads`,
   `memory_reads`, `agent_page_url`, `skill_uses` off the pump with
   per-agent, mtime-keyed caches; paint header chrome immediately and fill
   lanes as they land (the `lanes=` parameter and per-lane spans already
   exist for exactly this). Target: j/k p95 back under 16 ms.
i. **Thin out `axe.collect`**: cache `load_axe_config`, skip
   `probe_orchestrator`/global counts on ticks whose tokens did not drift
   (the `refresh.auto_tick` + `axe.collect{file_opens}` spans verify
   quiet-tick behavior per the idle-host diet recipe).

### Explicitly not recommended

- New profiling/instrumentation infra: **unnecessary**. `tui_startup.jsonl`
  already splits import/construct/compose, `tui_agent_loads.jsonl` already
  splits disk/prep/apply + index/decode/provider/projections, and
  `SASE_TUI_TRACE=1` + `SASE_TUI_PERF=1` + the bench suite cover the rest.
  A single `py-spy` capture is the only optional extra, and only if Phase 1
  under-delivers after landing.
- Moving loader logic into `sase-core` (Rust): the measured waste is
  repeated *Python-side orchestration* (config/trust/identity/alias), not
  scan/decode throughput the index path already optimizes. A Rust move
  would cross the `rust_core_backend_boundary` for no attributed gain.
- Broadening the Tier-1 window or raising `AGENTS_LOAD_MIN_INTERVAL_S`:
  treats the symptom (load frequency) while each load stays 5–20 s; revisit
  only if token drift still causes broad loads after Phase 1.

## 4. Verification plan for the implementer

1. Baseline on a quiet host: `bench_agent_load_tiering.py` (real archive),
   one `SASE_TUI_TRACE=1` startup, `tui_jk` p95. Record
   `app_construct_seconds`, warm-load wall, `decode`/`provider` substages,
   `monitor_reconcile`, `axe.collect{file_opens}`, detail-header lane spans.
2. Land Phase 1; re-run identical captures. Expect warm load ~1 s,
   `agents_ready` roughly halved, no change in row contents (oracle:
   `_agent_load_tiering_oracle.py` / existing `bench_*_regression` checks).
3. Land Phase 2; expect `process_start_to_on_mount` ~1 s with identical
   first-paint tabs; digit shortcuts converge on deferred release.
4. Land Phase 3 per-lane with the trace spans as the gate (quiet tick:
   `surfaces_reloaded=0`, near-zero `axe_file_opens`; j/k p95 < 16 ms).
5. Run `just check` (per `lint_and_test.md` the implementer must read it
   before finishing, since TUI sources change). `just check-full` only if
   CI needs it.

## Appendix — files touched by the evidence

- Startup path: `src/sase/ace/tui/actions/_state_init_late.py:354-373`,
  `src/sase/ace/tui/keymaps/bindings.py:39-54`,
  `src/sase/ace/tui/artifact_tabs.py:89-128`,
  `src/sase/ace/tui/_artifact_tab_discovery.py:42-152`,
  `src/sase/ace/tui/actions/_startup_mount.py:23-96`,
  `src/sase/ace/tui/util/startup_clock.py`, `src/sase/main/ace_handler.py:213-282`.
- Load path: `src/sase/ace/tui/models/agent_loader.py:373-429,537-624`,
  `src/sase/ace/tui/models/_loaders/_meta_enrichment_wire.py:57`,
  `src/sase/ace/tui/models/agent_workspace_retention.py:30`,
  `src/sase/workspace_provider/retention_record.py:186`,
  `src/sase/config/_sources.py:180-236`, `src/sase/config/core.py:185`,
  `src/sase/config/local_trust_management.py:141`,
  `src/sase/config/local_trust_enforcement.py:196-580`,
  `src/sase/core/agent_identity_facade.py:44-170`,
  `src/sase/ace/tui/actions/agents/_loading_disk_support.py:246-366`,
  `src/sase/ace/tui/actions/agents/_loading_disk_full.py:347-437`.
- Interaction: `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header_summary.py:158`,
  `src/sase/ace/tui/util/debounce.py`, `src/sase/axe/status_collector.py:46`.
