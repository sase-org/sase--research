# Prompt history pollution: swarm children and routine launches

Researcher: mus (independent swarm report; conclusions my own).
Date: 2026-09-30. Subject: prompt history stores machine-generated prompts
that should never have been history rows (screenshot
`~/tmp/screenshots/20260930_062115.png`).

## What the screenshot shows

The History pane (`project:sase`, 98/100 loaded) is dominated by bursts of
identical short rows stamped at the same second:

- `09-30 01:58`, eight `+sase` rows (`+2`/`+3` chips); same pattern at
  `20:34` (eight rows), `17:26` (eight rows), `17:22` (three rows).
- One highlighted row (`#D75FFF +4`) whose preview is a fully machine-rendered
  swarm body: `%id(2, clan=sase-1d5, bead=sase-1d5.2) %model@small %auto
  %bd/work_phase_bead:sase-1d5.2 %plan ...` repeated for slots 2–7.

Nobody typed those rows. They are expanded xprompt-swarm / bead-work slot
prompts (`%id(...)`, `%model@`, `%auto`, `%bd/...` are runner-control
directives, never human input). The diagnosis below confirms the write path
that creates them and the gaps in the existing `typed`/`generated` origin
machinery (landed 2026-09-29, commit `eaa4aa4aa7`, `SASE_BEAD=[sase-1cj.2]`).

## How prompt history recording works today

- Writes funnel into `add_or_update_prompt()` in
  `src/sase/history/prompt_store_mutations.py`. Two behaviors matter:
  1. `record_segments=True` (the default) additionally stores every
     `---`-separated segment of a multi-prompt as its own row, inheriting the
     parent's origin (`_multi_prompt_segment_mutations`).
  2. `allow_short=True` bypasses the five-word minimum (`is_recordable_prompt`).
- Every launch branch (single, multi-prompt, repeat, alt-split, bead-work)
  calls `add_or_update_prompt` on success and `record_failed_launch_prompt` on
  failure. Multi-prompt and bead-work branches pass `allow_short=True`.
- `PromptEntry.origin` (`typed` | `generated` | legacy `None`) round-trips
  through shard I/O with typed-wins merge. Anything launched from inside a
  `SASE_AGENT` process is coerced to `generated` (`_effective_prompt_origin`).
- **But origin is currently write-only metadata for one consumer**: the
  next-word prediction corpus excludes `generated` rows
  (`prompt_prediction_rows.py`). No read surface filters on it:
  `load_prompt_record_page()` / `list_prompt_records()` /
  `get_prompts_for_fzf()` take no origin parameter, the TUI History pane loads
  `include_cancelled=True` with no origin filter, and `sase prompt
  list/search/select` show everything. Worse, `PromptHistoryRecord` (the
  catalog type every read surface consumes) does not even carry `origin` —
  `record_from_entry()`/`to_entry()` drop it — so display filtering is not
  currently plumbable without touching the catalog layer.
- Existing coverage: `tests/history/test_prompt_origin.py`, 9 tests, all
  passing (verified this session via `uv run pytest`).

## Root causes of the flood (three distinct leaks)

### Leak 1 (dominant): swarm expansion + segment recording

`launch_agents_from_cwd_impl` (`src/sase/agent/launch_cwd_agents.py`) expands
`---` segments *and* xprompt swarms (`expand_launch_segments` →
`expand_xprompt_swarms_with_metadata` in `src/sase/agent/xprompt_swarm.py`)
before dispatch. One typed line such as `#research_swarm ...` becomes N
machine-rendered slot prompts. Then:

- Multi-slot case: `launch_multi_prompt_branch` records the pre-expansion
  `submitted_query` (good) **and**, via the default `record_segments=True`,
  every expanded slot segment as its own row (bad). One user action writes
  N+1 rows — exactly the same-timestamp bursts in the screenshot.
- Single-slot case: worse. The single-agent path records `query`, which by
  then is `normalize_default_vcs_workflow(expanded_segments[0])` — the
  *expanded* text, not what the user typed. If a swarm/xprompt expands to one
  slot, history keeps the machine rendering and the human's literal invocation
  is lost entirely.

The `+sase`-only rows are explained by `allow_short=True` combined with
segment recording: short slot fragments that the five-word minimum would
otherwise reject are written anyway.

### Leak 2: `%r:N` repeat fan-out records children, drops the parent

`launch_repeat_branch_if_applicable` (`launch_cwd_fanout.py`) never records
the parent query; each recursive `recursive_launch(spec.prompt, ...
origin=origin)` flows into `launch_single_agent` → `add_or_update_prompt`,
so `%r:5` stores five `%i:`-decorated machine prompts and zero copies of the
replayable thing the user actually wrote. This is backwards: the parent is
the only row with replay value.

### Leak 3: routine launches via `sase run` are marked `typed`

In-process routine launches are already correct: chop proposal dispatch
(`axe/chop_proposal_launch.py`), chop typed admission
(`axe/chop_typed_admission.py`), admission runtime
(`agent/launch_admission_runtime.py`), and LaunchApproval response
(`agent/launch_request_response.py`) all pass `origin="generated"`, as do
bead-work (`bead/cli_work_launch.py`), restarts (`agent/_restart_execute.py`),
and plan-approval runs (`main/plan_direct_approval_run.py`).

The hole is out-of-process: `launch_query` (`main/query_handler/_launch.py`,
the `sase run` / `sase prompt run` entry point) hardcodes `origin="typed"`,
and `_effective_prompt_origin` only upgrades to `generated` on `SASE_AGENT`.
A routine (axe chop / lumberjack script) that shells out to `sase run`
inherits `SASE_CHOP_*` / `SASE_JOB_*` env (built by `build_chop_launch_env`
in `axe/chop_agents.py`) but never `SASE_AGENT` — so the routine's prompt is
stored as human-typed. The success path has no chop-env check at all (the
`is_chop_launch_env` guard exists only on the *failed*-launch path in
`launch_cwd_agents.py` / `launch_cwd_bead_work.py`, an inconsistency in its
own right: chop failures are skipped while chop successes are stored).

## Critique of the proposed plan

The three requirements (swarm children not stored; swarm invocation stored;
routine launches not stored) are directionally correct, but as stated they
conflate *don't store* with *store but hide*, and they miss the legacy-data
problem:

1. **"Don't store" vs "store as generated and hide" is a real trade-off, and
   the right answer differs per row type.** Expanded swarm *segments* have no
   replay value (re-running one slot of a clan run is meaningless, and the
   parent row replays the whole thing) — not storing them is strictly better
   and also saves N shard writes per swarm launch. Routine prompts are
   reproducible from the routine definition, and chop run logs already audit
   them — not storing is fine. But a blanket "never store generated rows"
   would also discard the only debugging trace for launches whose parent
   context is gone (e.g. detached/mobile launches). The origin column already
   exists for exactly this distinction; the plan should use both tools: skip
   writes for zero-value rows (swarm segments, repeat slots), keep
   store-as-`generated` for the rest, and hide `generated` on read surfaces.
2. **The plan as written does not fix the screenshot for existing rows.**
   Every flood row already on disk has `origin=None` (legacy) or inherited
   `typed` from the pre-expansion submit — a write-path-only fix leaves all
   98 rows exactly where they are. Any accepted plan needs a backfill or
   cleanup story (see recommendation 5).
3. **The parent-invocation requirement needs an expanded-text caveat.** "Save
   the swarm invocation" must mean the *pre-expansion submitted text*, which
   the multi-slot path already records but the single-slot path does not
   (Leak 1). Stating the requirement without this distinction will produce a
   fix that keeps storing machine text for single-slot swarms.
4. **`sase prompt run` replay upgrades generated rows to `typed`.**
   `launch_query` marks everything `typed`, and the typed-wins merge means
   replaying any generated row permanently promotes it. If generated rows
   remain replayable (they should — replay is legitimate), the replay path
   should preserve the stored origin instead of stamping `typed`.
5. **Routine scope needs a definition.** "Routines" in this codebase means axe
   chops/lumberjacks (`SASE_CHOP_*`/`SASE_JOB_*` env, `axe/lumberjack.py`,
   `axe/chop_runner*.py`). The requirement should say so explicitly, because
   the fix (env-based detection) keys off exactly those markers — and it
   should cover both in-process launches (already mostly `generated`) and
   `sase run` subprocesses of routine scripts (currently `typed`).

## Adjustments to the requirements (explicit)

- A1. Record the **pre-expansion submitted text** of a swarm/multi-prompt
  launch as `typed` (one row), and record **zero** expanded segment rows.
  (Strengthens requirement 2; makes requirement 1 a special case.)
- A2. Record the **parent** of a `%r:N` repeat launch as `typed` (one row),
  and record **zero** slot rows. (New; fixes Leak 2.)
- A3. Define "routines" as axe chop/lumberjack executions identified by
  chop env (`SASE_CHOP_LUMBERJACK`/`SASE_JOB_ROUTINE` and siblings); skip
  history writes for their launches entirely (success and failure alike —
  chop run logs own that audit trail). (Makes requirement 3 testable.)
- A4. Preserve stored origin across `sase prompt run/edit/select` replay
  instead of stamping `typed`. (New; prevents merge-promotion.)
- A5. Hide `generated` rows on all interactive read surfaces by default, with
  an opt-in to show them. (New; required for the fix to be visible.)

## Recommended solution

Ordered by leverage; items 1–3 fix the write path, item 4 makes it visible,
item 5 cleans up the existing flood:

1. **Stop recording expanded text.** In `launch_multi_prompt_branch` and
   `launch_planned_bead_work_agents`, pass `record_segments=False` and keep
   recording only `submitted_query`/`normalized_query`. In
   `launch_cwd_agents.py`, thread the pre-expansion submitted query into the
   single-agent path and record that instead of the expanded slot text (or
   equivalently, record submitted text once at the top of
   `launch_agents_from_cwd_impl` and remove per-branch success writes —
   failure writes stay per-branch since they need branch-specific text).
   In `launch_repeat_branch_if_applicable`, add one `add_or_update_prompt`
   for the parent query and pass a "don't record" signal (e.g.
   `origin`-preserving `record_prompt=False`, or a private entry point) down
   the recursive slot launches so slot rows are never written.
2. **Close the routine subprocess hole.** Extend `_effective_prompt_origin()`
   to return `"generated"` when chop/routine env markers are present in
   `os.environ` (same precedent as `SASE_AGENT`; reuse `is_chop_launch_env`
   semantics against the process env), so `sase run` from a routine script is
   marked correctly with no caller changes. With item 3 this becomes
   belt-and-braces, but it also fixes prediction-corpus pollution for any
   routine path missed by the audit. Then audit the remaining
   `origin="typed"` call sites (`_launch.py`, `_pending_launch.py`,
   `_prompt_bar_stash_store.py`, `_mobile_agent_launch.py` — the mobile one
   is genuinely human-driven and should stay `typed`) for routine reachability.
3. **Skip (don't just mark) zero-value writes.** For routine launches
   (A3) and swarm/repeat slot rows (items 1–2 where a flag is cleaner than
   restructuring), skip `add_or_update_prompt`/`record_failed_launch_prompt`
   entirely rather than writing `generated` rows nobody will read. Keep the
   existing `is_chop_launch_env` failure-path skip and extend the same guard
   to the success path so the two agree.
4. **Hide `generated` by default on read surfaces.** Plumb `origin` through
   `PromptHistoryRecord` (it is currently dropped by `record_from_entry`),
   add an origin filter to `list_prompt_records` /
   `load_prompt_record_page` / `get_prompts_for_fzf`, default it to
   hide-`generated` in the TUI History pane (a toggle next to the existing
   cancelled toggle), `sase prompt list/search/select`, and document it in
   `docs/prompt.md`. Prediction already excludes `generated`; this makes
   history display consistent with prediction.
5. **Backfill the existing flood.** Legacy flood rows carry `origin=None`, so
   item 4 alone will not hide them. Options in increasing order of
   aggressiveness: (a) document a `sase prompt prune` recipe; (b) ship a
   one-off heuristic migration marking rows whose text matches machine
   patterns (`%id(<n>, clan=`, `%bd/work_phase_bead:`, bare `+<tag>`-only
   short rows) as `generated`; (c) both — (b) with `--dry-run` preview,
   since content-addressed IDs make the marking reversible only via backup.
   I recommend (c): heuristics are high-precision here because humans
   essentially never type `%id(2, clan=...` bodies, and the screenshot's rows
   are exactly that shape.
6. **Tests.** Extend `tests/history/test_prompt_origin.py`: swarm parent
   records one `typed` row with no segment rows; single-slot swarm records
   submitted (not expanded) text; repeat records parent only; chop env forces
   `generated` through `launch_query`; replay preserves origin; catalog
   filters exclude `generated` by default. Add one launch-path test asserting
   `record_segments=False` on the swarm branches.

## What I verified vs inferred

- Verified by reading: all file/line claims above (launch branches, expansion
  path, catalog/pane filter absence, `PromptHistoryRecord` dropping origin,
  chop `generated` call sites, `launch_query` hardcoded `typed`).
- Verified by execution: `tests/history/test_prompt_origin.py` — 9 passed
  (`uv run pytest`, system python is too old for the repo and fails at
  collection with `SyntaxError`, which is environmental, not a regression).
- Inferred from the screenshot (not code-traced to a specific run): that the
  pictured bursts are swarm-segment rows. The inference is strong — identical
  timestamps, `+sase` short bodies, and the `#D75FFF` preview showing the
  expanded `%id(...)` swarm body — but I did not match the rows to shard
  entries on disk.
