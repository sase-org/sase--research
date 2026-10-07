# 48-hour task-bead impact audit (sase)

- **Author:** research.3y.grk
- **Date:** 2026-10-07
- **Project:** sase (current project bead store)
- **Window:** 2026-10-05T16:27:43Z → 2026-10-07T16:27:43Z (48 hours before the audit clock)
- **Audit clock:** 2026-10-07T16:27:43Z UTC (host `date -u` was 2026-10-07 16:27:19 UTC)

This report ranks the **task beads** that were either **created** or **+1ed** in the last 48 hours by the impact of the work they represent. Plan, phase, and epic beads are out of scope except as context. Peer swarm reports from this same request were not opened.

## Method

1. **Created set.** `sase bead list --type task --since 48h --status all --format json -n 0` returned 11 task beads. Cross-checked against `issues.jsonl` with the same cutoff.
2. **+1 set.** Scanned `sase/repos/beads/events/streams/*.jsonl` for `operation == task_plus_one_recorded` with `timestamp >= cutoff`. That produced **17 +1 events** on **13 task beads**. Cross-checked against `plus_one_evidence` timestamps in `issues.jsonl` (same 13 IDs).
3. **Union.** 23 unique task beads. Audited `sase bead read <id> --format json` for every ID.
4. **Liveness checks on this tree** (sase `38f48d7575`, `sase-core-revision.txt` pin `26ec2d61`, `sase-core-rs>=0.35.0,<0.36.0`):
   - Confirmed `import sase.history.prompt_store_mutations` still raises the circular `ImportError` named by `sase-1h2`. Importing `sase.history.prompt_store` first succeeds.
   - `sase bead read sase-1h3` (full JSON, links on) of an epic whose child IDs contain `.` succeeded, so the linked-read half of `sase-1gs` is green here. `sase artifact link add` was not attempted (it would mutate).
   - Beads pane code already has one-pass `phases_by_parent` grouping and `on_refresh` → `_request_load(force=False)` (`7615e253d8`, phase `sase-1h8.6`, closed).
5. **Context reads.** Related epics `sase-1h8` (in progress; bead-store performance), `sase-zn` (ACE typing lag), `sase-j7` (parallel-lane flake class), plus closed epics `sase-1gu` / `sase-1h3` / `sase-1g4` that spawned several of the new tasks. Scaling numbers for `sase-1h5` / `sase-17r` come from `research:202610/bead_history_cost_and_lossless_archival/bead_history_cost_and_lossless_archival__final.md`.

### Ranking criteria (in order)

1. **Live product / operator breakage** on a path humans or agents take every day (launch, PyPI install, typed links, ACE UI, workspace prep).
2. **Blast radius and frequency** (every agent, every fresh workspace, every landing, every `just check`).
3. **Trajectory** (cost grows with the bead store, the TUI import graph, or unpublished core APIs).
4. **Independent corroboration** (lifetime `plus_one_count` and +1s inside the window). A +1 is append-only evidence from a distinct reporter, not a vote.
5. **Whether standalone remaining work is still on the task**, or already consumed by an in-progress epic (especially `sase-1h8`).

Size (XS–XL) is recorded as ROI context. It does not set rank.

## Census

| ID | Status | Type | Size | +1s (life / 48h) | In via | Title |
|---|---|---|---|---|---|---|
| sase-1gv | open | flag | small | 0 / 0 | created | Retire `grok_rules_delivery` |
| sase-1gw | open | flag | small | 0 / 0 | created | Retire `claude_helper_channel` |
| sase-1gx | ready | bug | medium | 0 / 0 | created | Read-only bead paths auto-init stores and commit |
| sase-1gy | ready | bug | medium | 0 / 0 | created | Perf-check recipes recreate in-tree `sdd/` |
| sase-1gz | ready | flake | large | 0 / 0 | created | sase-core `federation_worker` IPC flake |
| sase-1h0 | ready | bug | small | 0 / 0 | created | `InputItemModal` / `MacroItemModal` unreachable |
| sase-1h1 | ready | bug | large | 0 / 0 | created | TUI macro-arg detection ignores quoting |
| sase-1h2 | ready | bug | small | 0 / 0 | created | Cold import circular `ImportError` breaks LaunchApproval |
| sase-1h4 | open | flag | small | 0 / 0 | created | Retire `instruction_shadow_render` |
| sase-1h5 | ready | bug | small | 0 / 0 | created | Beads pane quadratic refresh / forced 10 s tick |
| sase-1h6 | ready | ci | small | 1 / 1 | both | `just symvision` red: private `_runs` module |
| sase-10d | ready | bug | small | 6 / 1 | +1 | Cut sase-core release and raise `sase-core-rs` floor |
| sase-13p | ready | ci | large | 13 / 1 | +1 | TUI app import budget (`test_app_import_budget`) |
| sase-14o | ready | ci | small | 15 / 1 | +1 | Absent-store tests see the host bead store |
| sase-15h | ready | flake | medium | 2 / 1 | +1 | sase-core `sudo_runner` ETXTBSY flake |
| sase-17r | ready | bug | medium | 2 / 1 | +1 | Fresh-workspace beads clone ~22 s p50 (`--dissociate`) |
| sase-18v | ready | ci | small | 2 / 1 | +1 | Snippet/restart CLI tests vs Rich-truncated tmp paths |
| sase-1br | ready | flake | large | 2 / 1 | +1 | `test_block_spread_bracket_top_aligns` scroll timeout |
| sase-1em | ready | flake | large | 1 / 1 | +1 | `test_registry_rebuild_keeps_live_identity_pending_claim` |
| sase-1f0 | ready | flake | large | 5 / 1 | +1 | `peak_tree_rss_kib == 0` in demand-run test |
| sase-1fy | ready | flake | large | 6 / 3 | +1 | `test_prompt_tab_focus_steal` FrontmatterPanel `NoMatches` |
| sase-1gp | ready | flake | large | 1 / 1 | +1 | `test_distinct_ace_apps_do_not_share_session_state` |
| sase-1gs | ready | bug | large | 4 / 3 | +1 | Artifact link add / linked bead read bead-id validation |

**23 task beads. None closed. 3 open (all sunset flags). 20 ready. 0 in_progress / claimed / snoozed.** `is_ready_to_work` is false on every envelope: they are waiting on TaskTriage, not on an assigned worker.

Window event mix in the bead store (582 events): 173 `link_added`, 168 `note_appended`, 57 `issue_created`, 51 `issue_closed`, 46 `epic_work_preclaimed`, 43 `dependency_added`, 20 `issue_updated`, **17 `task_plus_one_recorded`**, 5 `ready_marked`. The 11 new tasks are a small slice of 48-hour bead traffic; most mutation is notes, links, and epic lifecycle.

Clusters:

- **Bead-store scaling and isolation:** `sase-1h5`, `sase-17r`, `sase-1gx`, `sase-14o` (and in-progress epic `sase-1h8`, created 2026-10-06T22:59Z, outside this task ranking).
- **Master / landing CI tax:** `sase-13p`, `sase-1h6`, `sase-14o`, `sase-18v`, plus the flake pile (`sase-1fy`, `sase-1f0`, `sase-1em`, `sase-1br`, `sase-1gp`, `sase-1gz`, `sase-15h`).
- **Launch and artifact workflow:** `sase-1h2`, `sase-1gs`, `sase-10d`.
- **Named-type TUI leftover from closed epic `sase-1g4`:** `sase-1h1`, `sase-1h0`.
- **Instruction-migration sunset flags from `sase-1gu` / `sase-1h3`:** `sase-1gv`, `sase-1gw`, `sase-1h4`.

---

## Ranked list: 10 most impactful task beads

### 1. `sase-1h2` — Cold import of `prompt_store_mutations` breaks LaunchApproval dispatch

- **Type / size / status:** bug · small · ready · created 2026-10-06T15:11:20Z · +1s 0
- **Why this work is impactful:** An approved LaunchApproval can fail at dispatch with a circular `ImportError`, so the approved agents never start. The bead names a concrete failed gate (`launch-ac9ca583-8595-4bc8-90cd-42b631170bbe`) that blocked E1 (`sase-1gu`) acceptance probes requested through `/sase_run`. The same lazy import sits on `src/sase/agent/launch_cwd_agents.py:67` and `launch_cwd_bead_work.py:72`. Any `/sase_run` or bead-work launch whose process has not already imported `sase.history.prompt_store` can fail the same way.
- **Liveness:** Reproduced on this tree. `.venv/bin/python -c "import sase.history.prompt_store_mutations"` raises `ImportError: cannot import name 'add_or_update_prompt' from partially initialized module 'sase.history.prompt_store_mutations'`. Importing `prompt_store` first succeeds. Causal commit `ad7f3a19a3` belongs to closed epic `sase-1d8`; this is leftover production breakage, not in-epic debris.
- **ROI:** Small, localized cycle break between two history modules. Highest remaining *unfixed* operator-path defect in the set.

### 2. `sase-10d` — Cut a sase-core release and raise the published `sase-core-rs` floor

- **Type / size / status:** bug · small · ready · created 2026-09-13 · +1s 6 (1 in-window, 2026-10-06T12:33:50Z by `sase-1eq.12.land`)
- **Why this work is impactful:** Published `sase` is only as good as the `sase-core-rs` wheel PyPI will actually install. Notes on this bead record a period when **every published `sase` on PyPI was uninstallable** after a retention run deleted the `sase-core-rs` window frozen into `sase 0.17.1`. Later notes record a 0.35.0 ratchet, then the gap opening again. The in-window +1 at sase `312f17dc3f` / core `b19690e3` reports `tools/probe_core_floor --json --advisory` as `blocked_unpublished`, floor `0.35.0`, **95 missing capabilities**, with `load_macro_input_type_registry` first appearing at `af5df61` and no containing release tag. `pyproject.toml` on this tree still allows `sase-core-rs>=0.35.0,<0.36.0`.
- **Scope of remaining work:** Cut a core release that contains the current pin cohort, wait for a complete wheel+sdist, ratchet through `tools/ratchet_core_window`, and keep plugin / research-artifact floors in step. A sase PyPI release that ships against the source-built pin will pair users with a binding that is missing live APIs.
- **ROI:** Small mechanical publish-and-ratchet; release-blocking for the whole product.

### 3. `sase-1gs` — Typed artifact links (and linked bead reads) fail bead-id validation

- **Type / size / status:** bug · large · ready · created 2026-10-05T14:14:53Z (just outside the create window) · +1s 4 / 3 in-window
- **Why this work is impactful:** Filing and relating work is a daily agent path. `/sase_new_task` tells agents to record typed related links; this bead says `sase artifact link add` fails for *valid* bead refs with `bead id segment must contain only letters, digits, '-' and '_'`, and `sase bead read` needs `--no-links` to show a bead. Four independent land agents (`sase-1fs.land`, `sase-1gt.land`, `0x4`, `sase-1g4.land`) reproduced it on 2026-10-05/06. The creation reason is that three agents had already worked around it in prose the same day.
- **Liveness caveat:** On this tree, `sase bead read sase-1h3` with link expansion succeeded, so the *read* half looks repaired since the 0.36.5 / `fe2ef0e6` filing. `sase artifact link add` was not re-run. The bead is still `ready` with no close. Rank stays high because the associated work is restoring the typed-link contract every agent is instructed to use.
- **Location:** `sase-core` `validate_bead_id` (`crates/sase_core/src/artifact_ref/mod.rs`), reached from link add and the bead-read link renderer. Core-pin work, which is why size is large.

### 4. `sase-17r` — Fresh-workspace beads sidecar clone ~22 s p50

- **Type / size / status:** bug · medium · ready · created 2026-09-24 · +1s 2 / 1 in-window (2026-10-06T21:40:05Z, `research.3u.final`)
- **Why this work is impactful:** The first bead command in a fresh or re-prepared workspace blocks on `git clone --reference-if-able … --dissociate` of the beads sidecar. Original telemetry: 41 clones in 13 h on athena, **p50 22.2 s, p90 28.4 s, max 47.3 s**. A `sase bead ready` in one workspace spent 47.3 s of 50.1 s in this clone. The bytes are repeated loose copies of `issues.jsonl` (now ~20.8 MB per commit). Git's count-based auto-gc never fires. The 2026-10-06 +1 found the **host-owned hidden clone at 2,293 loose objects / 1.84 GiB loose plus 37 packs / 1.34 GiB**, above every `maybe_gc_sidecar_clone` threshold, still unpacked.
- **Overlap:** Epic `sase-1h8` phase `.3` (“Hidden-clone gc and bead push-log retention”) is already **closed**. This task’s remaining standalone value is verifying that the hidden clone actually packs in production and that `--dissociate` cost stays ~2 s. The work is still the highest-frequency launch-path tax in the set.
- **Trajectory:** Store growth (~88 beads/day in the 2026-10-06 scaling report) keeps writing new `issues.jsonl` blobs. Leaving this unattended makes every later agent slower.

### 5. `sase-1h5` — Beads pane refresh: 2.8 s today, ~48 s at 4× the store

- **Type / size / status:** bug · small · ready · created 2026-10-06T21:38:33Z · +1s 0
- **Why this work is impactful:** The ACE Artifacts → Beads pane is the human surface onto 7,034 beads / 949 epics. The 2026-10-06 scaling report measured `load_project_beads` 2.24 s + grouping 0.56 s ≈ **2.8 s per 10 s tick**, holding the GIL; grouping alone 3.41 s at 2× and 37.9 s at 4× (refresh ~48 s, longer than the interval). That is a live UI stall that grows as the store grows (2× ~ January 2027, 4× ~ mid-2027 in that report).
- **Partial land:** Commit `7615e253d8` (2026-10-06 22:35 −0400) and closed phase `sase-1h8.6` already replaced the nested `O(epics × issues)` scan with a one-pass `phases_by_parent` dict and stopped auto-refresh from forcing a reload. The remaining cost named on the bead — three full event-store replays per tick (list + ready + blocked) — is exactly the class `sase-1h8` is in the middle of removing (`.7` “one store read per CLI command” is already closed; `.8`–`.9` closed; `.11`–`.14` still in progress).
- **Rank rationale:** The *work* is among the most user-visible scaling fixes in the window. Much of the cheap TUI half is already on master; closing or retargeting this task onto the leftover three-replay / read-model work avoids double-launching beside `sase-1h8`.

### 6. `sase-14o` — Absent-store tests resolve the host bead store (15 +1s)

- **Type / size / status:** ci · small · ready · created 2026-09-20 · +1s **15** / 1 in-window (2026-10-06T22:08:52Z, `sase-1h3.land`)
- **Why this work is impactful:** Highest corroboration in the audit set. Two tests that claim “no bead store” still walk resolver candidate paths and find athena’s live store, so they fail **deterministically on every agent machine that has beads** and pass only in CI (no host store). Nodes: `tests/doctor/test_checks_beads.py::test_project_beads_skips_when_store_is_absent` (`OK` vs `SKIP`) and `tests/completion/test_candidates_project_providers.py::test_bead_candidates_without_a_store_returns_empty_list` (16 live candidates, first `bryan-1`). Later +1s add the sibling plan-archive leak `test_plan_candidates_emit_canonical_references`. They are outside `just test-scoped`, so `just check` stays green while `pytest tests/completion` and `pytest tests/doctor` stay red for every landing agent.
- **ROI:** Small isolation fix (monkeypatch the resolver, not just cwd / one helper). Fifteen independent landings have already paid the triage cost. Same underlying eagerness as `sase-1gx` (product-side auto-init).

### 7. `sase-13p` — TUI app import budget; +1ed today at the cap

- **Type / size / status:** ci · large · ready · created 2026-09-20 · +1s **13** / 1 in-window (2026-10-07T13:25:22Z, `sase-1h9.land`)
- **Why this work is impactful:** `tests/ace/tui/test_app_import_budget.py::test_tui_app_import_stays_under_startup_budget` is a deterministic master-red landing tax. The original filing was `assert 3292 < 3290`. Caps have been raised through 3400, 3485, 3530, and now **3570**; the in-window +1 is `assert 3570 < 3570` on master `5230c3080e`. This tree still has `_MAX_MODULE_COUNT = 3570` and a strict `<`. Every TUI epic that adds an eager import re-hits the same node. Thirteen +1s over 17 days is the second-highest corroboration in the set.
- **Why large:** The durable fix is import-graph discipline (deferral / TYPE_CHECKING), which is the same work several landings already did locally and then watched the count creep back. Raising the cap again treats the symptom. This is the ACE startup-cost ratchet; it is also a proxy for TUI import bloat that `sase-zn` cares about.

### 8. `sase-1h6` — `just symvision` red on master (`sase.instructions._runs`)

- **Type / size / status:** ci · small · ready · created 2026-10-06T22:07:14Z · +1s 1 (2026-10-06T23:39:36Z, `sase-1h8.3--1`)
- **Why this work is impactful:** `just symvision` / the `lint (symvision)` stage of `just check` fails on clean master. Five phases of epic `sase-1h3` plus the land agent saw the same `_runs` findings, triaged KNOWN / no owner. The blamed files (`v2_snapshot_io.py`, `overview_card.py`) each define a file-local `_runs()` helper; the trigger is the **private module** `src/sase/instructions/_runs.py` imported across `verify.py`, `coverage.py`, `doctor/checks_instructions.py`, and `main/instructions_handler.py` (introduced by E1 `sase-1gu` commit `08c8a56b36`, more sites in E2). Symvision matches the imported name against every private def of the same name.
- **ROI:** Rename the module to a public name and update import sites. That is the cheapest way to take a named KNOWN/no-owner failure off every governed check. Deterministic; `why_not_flake` cites identical failures at `9e4b9767d2` and `66d598d198`.

### 9. `sase-1h1` — TUI macro-arg detection disagrees with the binder and the LSP

- **Type / size / status:** bug · large · ready · created 2026-10-06T00:22:02Z · +1s 0
- **Why this work is impactful:** Closed epic `sase-1g4` just made named macro input types (`enum`, `bool`, `model`, plugin enums) a shared vocabulary across TUI, LSP, `sase macro show`, and the runtime binder. This leftover means the **prompt-bar value menus open for the wrong input, or not at all**, when an earlier argument is a quoted value containing `,` or `)`. Detection still splits on raw commas and stops at the first `)` (`_macro_arg_assist_detection.py`, logic from June–July 2026). Repro on master `abcfedc31d`: `#m:x,` correctly offers `env`; `#m:"a,b",` offers the wrong later input. Users editing real macros with quoted notes will see menus that the binder will reject.
- **Why large:** The TUI splitter has to be replaced with the same structural context sase-core already owns for the binder/LSP, which is a core-boundary change rather than a local string tweak.

### 10. `sase-1gx` — Read-only bead paths initialize stores and attempt SDD-init commits

- **Type / size / status:** bug · medium · ready · created 2026-10-05T22:17:13Z · +1s 0
- **Why this work is impactful:** `get_read_view()` → `get_project()` → `init_beads()` still calls `ensure_bare_git_sdd_initialized(root, commit=True, push=False)` for `BEADS_DIRNAME` stores. Display-only paths (attachment doctor, plan-archive doctor, any `get_read_view` lookup) can **write and commit generated SDD scaffolding into whatever checkout cwd resolves to**. That is a data-integrity footgun on a read API. It is the product-side twin of `sase-14o` (tests that cannot see “no store” because resolution is too eager). Filed as follow-up to the approved stray-root-`sdd` removal plan (`202610/remove_stray_root_sdd_dir.md`).
- **Desired end state (from the bead):** read-only resolution opens the existing store or reports unavailable. It never initializes and never commits.

---

## Rank 11–13 (just outside the ten)

These would replace #10 under a “corroboration-first” or “CI-noise-first” rubric.

- **`sase-1fy`** (flake, large, **6 +1s / 3 in-window**). `tests/ace/tui/widgets/test_prompt_tab_focus_steal.py` fails under xdist *and* serially, with `FrontmatterPanel.on_mount NoMatches('#frontmatter-raw')`, `DuplicateIds`, and AcePageGroup isolation leaks. Most in-window flake corroboration. Sibling of open epic `sase-j7` (process-global leak class) and closed `sase-pe`. High check-lane tax; no direct user path.
- **`sase-1f0`** (flake, large, **5 +1s / 1 in-window**). `test_foreground_run_records_context_usage_and_grant` asserts `peak_tree_rss_kib > 0` and sees 0 under parallel load (~1/10 serial). Sampler-vs-child-exit race. Recurring full-`just check` noise.
- **`sase-1h0`** (bug, small). `InputItemModal` / `MacroItemModal` have no production constructor since inline frontmatter editing (`7776f7a857`, 2026-07-10). Dead code every macro-input change still compiles and tests; crashes in it never reach users. Cheap cleanup, low user impact.

## The other ten, briefly

| ID | Why it ranks lower |
|---|---|
| sase-1gy | Hygiene: perf-check JSON recreates a gitignored in-tree `sdd/` after the tracked root dir was removed. Confuses leak guards. No user path. |
| sase-18v | Deterministic CLI tests that assert a full tmp path Rich truncates under long agent basetemps. Governed `just check` often passes (shorter basetemp). Two +1s. |
| sase-1em | One parallel-lane registry-rebuild flake; isolation passes. Related to closed `sase-u7`. One in-window +1. |
| sase-1br | Deck scroll-settle `wait_for` flake, ~1/6 isolated. Sibling of `sase-1a7`. Two +1s, low product blast. |
| sase-1gp | Config-center session test, one full-lane fail then serial pass. One +1. |
| sase-1gz | sase-core `federation_worker` IPC flake, one fail under parallel gate. Related to `sase-15h`. Newly filed, uncorroborated. |
| sase-15h | sase-core `sudo_runner` ETXTBSY (`fs::write` then exec while another thread forks). Classic fixture race. Two +1s, core-test only. |
| sase-1gv | Sunset flag for `grok_rules_delivery`. Remove-by 2027-01-03 / 0.19.0 after E1 watch or E3 cutover. Tracking bead, not current work. |
| sase-1gw | Same shape for `claude_helper_channel`. |
| sase-1h4 | Same shape for `instruction_shadow_render` (E2 shadow render). Remove-by 2027-01-04 / 0.19.0. |

The three flag beads are correctly `open` drafts. Their impact arrives when E3 cuts over instruction delivery or when the watch window expires. They should not be triaged as ready work this week.

## Cross-cutting observations

1. **An in-progress epic already owns the scaling cluster.** `sase-1h8` (“Bead store performance: remove replay waste, add a Rust read model, take `issues.jsonl` off the commit path”) was created 2026-10-06T22:59Z. Phases `.1`–`.9` are closed, including `.3` (hidden-clone gc, `sase-17r`) and `.6` (Beads pane refresh, `sase-1h5`). Phases `.10`–`.14` are still in progress. Ranking `sase-1h5` and `sase-17r` high describes the *work*; launching new task workers on top of those phases would duplicate it.
2. **Eager bead-store resolution is one bug in two costumes.** `sase-1gx` (read APIs init+commit) and `sase-14o` (tests cannot see “no store”) share a resolver that prefers a live host store over the caller’s isolation. Fixing the resolver once is more impactful than two separate test patches.
3. **Master-red CI in this window is mostly named and small.** `sase-1h6` (rename `_runs`) and `sase-14o` (isolate two tests) are both `small`. `sase-13p` is the exception: it is large because the import graph keeps growing into whatever cap is set.
4. **Flake corroboration is real and still lower-leverage than the product bugs.** `sase-1fy` (6) and `sase-1f0` (5) are noisy enough to own, and `sase-j7` is the epic that should absorb that class. They do not beat a broken LaunchApproval or a blocked PyPI floor.
5. **Nothing in the set is currently being worked as a task.** All 20 ready beads are waiting on triage. The only overlapping in-progress vehicle is epic `sase-1h8`.

## Recommended triage order (if launching from this set)

If the goal is maximum impact per launch, ignoring work already inside `sase-1h8`:

1. `sase-1h2` (LaunchApproval)
2. `sase-10d` (core release + floor) — needs a human publish step
3. Confirm `sase-1gs` link-add on current core; close or retarget
4. `sase-1h6` (symvision rename) — cheapest master-green
5. `sase-14o` (host-store test isolation), preferably with `sase-1gx` as the product half
6. `sase-1h1` (TUI quoting vs binder)
7. `sase-13p` only with a deferral plan, not another cap bump

Verify `sase-1h5` / `sase-17r` against closed `sase-1h8.6` / `sase-1h8.3` before creating parallel workers.

## Sources

- Bead store: `SASE_SDD_BEADS_DIR` events under `events/streams/*.jsonl` and projection `issues.jsonl` (7,067 issues, 1,111 tasks at scan time).
- Audited reads of all 23 task beads plus `sase-1h8..`, `sase-zn`, `sase-j7`, `sase-1gu`, `sase-1h3`, `sase-1g4`, `sase-k1`, `sase-u7`.
- Live reproduction: `sase-1h2` circular import; `sase-1gs` linked read of `sase-1h3`; Beads pane source at `src/sase/ace/tui/widgets/artifacts/beads_{data,pane}.py`; import-budget cap in `tests/ace/tui/test_app_import_budget.py`.
- `research:202610/bead_history_cost_and_lossless_archival/bead_history_cost_and_lossless_archival__final.md` (replay cost, Beads pane 2.8 s / 48 s at 4×, hidden-clone 1.84 GiB, ~88 beads/day).
- `pyproject.toml` `sase-core-rs>=0.35.0,<0.36.0`; `sase-core-revision.txt` `26ec2d61d9c60eede1596ae7d8c897e74dfb8141`.

## Caveats

- The 48-hour bound is wall-clock from the audit, not calendar-day `YYYY-MM-DD`. Beads created on 2026-10-05 before 16:27Z (e.g. `sase-1gs`, `sase-1gp`) enter only through in-window +1s.
- `sase bead list --since 48h` bounds **creation** time. +1s on older beads were recovered from the event log.
- I did not run `sase artifact link add` (mutation) or a full `just check`. CI-red claims for `sase-1h6` and `sase-13p` rest on bead evidence plus the current `_MAX_MODULE_COUNT = 3570` source.
- Impact is about the work the beads describe. Several high-rank items (`sase-1h5`, `sase-17r`) have already been absorbed by closed `sase-1h8` phases; remaining impact is verification plus the still-open read-model / `issues.jsonl` phases of that epic.
- Flag beads (`sase-1gv`, `sase-1gw`, `sase-1h4`) are sunset trackers with 2027-01 / 0.19.0 remove-by dates. They are in the census because they were created in-window.
