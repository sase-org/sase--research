# Prompt History Should Record Human Requests Only

Researcher: `cld` · 2026-09-30 · repo HEAD `84c9f3635b`

## TL;DR

- **Yes, this is a good idea, and the numbers make it urgent.** In the live store, **82 of
  the 100 rows** on the first page of the `Ctrl+K` history modal are machine-generated.
  Machine-generated rows are 55% of July's shard, 73% of August's, and **80% of
  September's** (77% of September's characters).
- **The screenshot's example is neither a swarm member nor a routine launch.** It is an
  epic launch through `sase bead work`, run by an agent after you asked it to "review and
  relaunch the 1d5, 1cx, … epic beads" at 06:02. Each epic launch writes **one row per
  phase plus one for the whole prompt** (5–12 rows). Your two bullet points would not
  remove it. **Adjustment:** replace "exclude swarms and routines" with a general rule:
  _record only text a human submitted_.
- **Most of the plumbing already exists.** Yesterday's `eaa4aa4aa7` (sase-1cj.2) added
  `PromptEntry.origin = typed | generated` and passes it from every launch site. Routine
  jobs, bead work, epic/plan approval, LaunchApproval, agent restarts, and anything
  launched from inside an agent are already tagged `generated`. But only the next-word
  prediction corpus uses the tag. The modal, `sase prompt list`, word completion, and
  placeholders all still show or ingest generated rows.
- **The swarm requirement is already mostly met.** Since `148d62494a` (2026-05-21), a
  swarm launch records only the trigger (`#research_swarm …`), not the expanded member
  prompts. The swarm-member rows in history leak in through three side doors: restarts,
  the provider-guard remodel path, and edit-and-relaunch.
- **Recommendation:** gate history writes on origin: `generated` rows are never written.
  Make "generated" the default for any launch caller that doesn't declare an origin.
  Close three leaks where one human request becomes several rows or rewritten rows. Add a
  one-time `sase prompt prune --generated` to clean out about 8,000 legacy rows. Details
  and phasing are in the last section.

## 1. What the Screenshot Actually Shows

The highlighted row (`09-30 01:58`, preview starting `%id(sase-1d5.1, bead=sase-1d5.1)
%clan(sase-1d5, tribe=epic, …) … #bd/work_phase_bead:sase-1d5.1 #plan --- …`) is the
multi-prompt produced by `sase bead work sase-1d5`. The store confirms it:

```
260930_015851 generated 1664  #gh:gh_sase-org__sase | %id(sase-1d5.1, bead=sase-1d5.1) | %clan(sase-1d5, …   <- whole multi-prompt
260930_015851 generated  178  … %id(sase-1d5.1, …) #bd/work_phase_bead:sase-1d5.1 #plan                          <- segment 1
260930_015851 generated  111  … %id(2, clan=sase-1d5, bead=sase-1d5.2) …                                        <- segment 2
… (8 more segment rows, through %id(land, clan=sase-1d5, …))
```

Two separate mechanisms combine here:

1. **Machine launches are written at all.** `launch_cwd_bead_work.py:172` calls
   `add_or_update_prompt(normalized_query, allow_short=True, origin=effective_origin)`.
2. **Every multi-prompt segment gets its own row.** `add_or_update_prompt` defaults to
   `record_segments=True`, so `_multi_prompt_segment_mutations`
   (`prompt_store_mutations.py:146`) adds a row for each segment of five words or more.
   An 11-phase epic therefore produces 12 rows. That is where the runs of `+2` / `+3` /
   `+4` rows at 01:58, 20:34, 19:00, 18:30, 17:26, and 17:22 come from.

The 06:22 `sase-1d6` rows come from the same source: an agent (the one you asked at 06:02)
ran `sase bead work`. They are correctly tagged `generated`, but nothing hides or skips
them.

## 2. Current State

### 2.1 Write sites and their origin today

| Launch surface                                                                  | Write site                                                                                           | Origin today                                    | Should record?              |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------- |
| TUI prompt bar submit (runs a durable `sase run` proc)                           | `main/query_handler/_launch.py:196-207` → `launch_cwd_*`                                             | `typed`                                         | **Yes**                     |
| `sase run` / `sase prompt run` (replay) from a terminal                          | same                                                                                                 | `typed`                                         | **Yes**                     |
| Mobile / Telegram                                                                | `integrations/_mobile_agent_launch.py:83`                                                            | `typed`                                         | **Yes**                     |
| TUI cancel, editor cancel, failed launch, quit-flush                             | `_prompt_bar_mount.py:171/174/579`, `_pending_launch.py:313`, `_prompt_bar_stash_store.py:154`       | `typed` (cancelled)                             | **Yes** (as cancelled)      |
| xprompt swarm trigger                                                            | `launch_cwd_fanout.py:88` (`submitted_query`, `allow_short=True`)                                    | inherits caller                                 | **Yes** (the trigger only)  |
| Routine jobs (chop proposals, typed admission)                                   | `axe/chop_proposal_launch.py:481/537`, `axe/chop_typed_admission.py:96`                              | `generated`                                     | No                          |
| `sase bead work` / epic launch / plan-approval epic                              | `bead/cli_work_launch.py:31/39` (plan approval runs `bead work` in a monitor)                         | `generated`                                     | No                          |
| Direct plan approval                                                             | `main/plan_direct_approval_run.py:481`                                                               | `generated`                                     | No                          |
| LaunchApproval (agent `/sase_run` requests)                                      | `agent/launch_request_response.py:177`, `agent/launch_admission_runtime.py:142`                      | `generated`                                     | No                          |
| `sase agent restart` / provider drain                                            | `agent/_restart_execute.py:80`                                                                       | `generated`                                     | No                          |
| Anything launched from inside an agent (`SASE_AGENT` set)                        | upgraded in `launch_cwd_agents.py:65`, `launch_cwd_bead_work.py:73`, `prompt_store_mutations.py:31`   | `generated`                                     | No                          |
| Job **script** that shells out to `sase run` (`SASE_JOB_NAME` in env, no `SASE_AGENT`) | `query_handler/_launch.py`                                                                      | **`typed`** (wrong)                             | No                          |
| Third-party / plugin callers of `launch_agents_from_cwd` with no `origin`        | `launch_cwd_*`                                                                                       | `None`, **recorded**                            | No (should fail closed)     |

In short, the classification is basically right already. The missing pieces are
(a) writes are not gated on it and (b) the default for an undeclared origin.

### 2.2 Readers ignore origin

None of the history readers filter on `origin`. Only the prediction corpus uses it, and
the actual exclusion happens in the Rust core (`sase_core::prompt_prediction::corpus::
is_generated_row`). Specifically:

- **Ctrl+K modal** (`modals/history_pane.py:235` → `load_prompt_record_page(...,
  include_cancelled=True)`) filters only on `cancelled`. The Rust filter wire
  (`core/prompt_history_filter_wire.py:66-83`) sends `index, canonical_text,
  display_text, segment_project_keys, segment_raw_refs`. It carries **no `origin`**.
- **`PromptHistoryRecord`** (`prompt_catalog.py:25-35`) has no `origin` field, so
  `sase prompt list/run/show/copy/export/search/stats` and the fzf picker cannot filter on
  it without schema work.
- **Word completion** (`prompt_word_index.py:118`) and the **placeholder seed**
  (`prompt_placeholders.py:334`) read every row. Tokens like `work_phase_bead`,
  `sase_clan_summary_epic`, and `%w(bead=…` therefore compete with your own vocabulary.

Nothing needs generated rows to be present:

- **Directive persistence** calls `rewrite_prompt_text_exact`. If no row matches, the
  rewrite just returns 0.
- **Restart and relaunch** write history but never read it.
- **Prediction** already discards generated rows.
- **The prompts themselves stay available elsewhere.** Every agent's prompt remains in its
  artifacts (`raw_xprompt.md`) and chat transcript. Agents with commits and approved
  planners are also in the canonical agents archive that `sase prompt search` already
  searches.

### 2.3 Measurements (`~/.sase/prompt_history/*.json`, 11,584 rows)

A row counts as "machine" if `origin == "generated"`, or if it has no origin and matches
the sase-core `looks_generated` markers (plus `tribe=chop` / `%tribe:chop`).

| Shard                         | Machine rows          | Machine share of text |
| ----------------------------- | --------------------- | --------------------- |
| 2607                          | 2,062 / 3,755 (55%)   | 40%                   |
| 2608                          | 2,958 / 4,048 (73%)   | 61%                   |
| 2609                          | 3,025 / 3,781 (80%)   | 77%                   |
| **First 100 rows (modal page 1)** | **82 / 100**      | —                     |

Since origins began being recorded (2026-09-29 07:45) there have been **79 `generated`
rows and 15 `typed` rows**. The trend is getting worse as more work runs through epics
and jobs.

Other noise sources in the data:

- **Epic phase segment rows**: 4,923 rows mention `work_phase_bead` or
  `sase_clan_summary_epic`.
- **Routine jobs**: 1,639 rows mention `toobig` and 659 are `chop` launches.
- **Swarm members**: 26 rows (`%id(final_2, clan=research.0m)`, `%id(gem,
  clan=research.27)`, …) come from relaunches.

## 3. Critique of the Plan

### 3.1 What's right

- The principle ("one row = one thing a human asked for") is the correct definition of
  prompt history. Everything the history is used for depends on it: replay, `Ctrl+K`
  recall, word completion, placeholder memory, next-word prediction.
- Replaying generated rows is actively **hazardous**, not just noisy. `^i: load` +
  submit on an epic row relaunches all its phases with fixed `%id(sase-1d5.N)` names
  (collisions or force-reuse), `%w(bead=…)` waits, and `#bd/work_phase_bead` bindings.
- Keeping the swarm trigger (`#research_swarm(…):: …`) is right. It is the replayable
  human intent, and `148d62494a` already built exactly that behavior.

### 3.2 Adjustments I'd make (clearly flagged)

**A1 — Generalize from two exclusions to one inclusion rule. _(Requirement change.)_**
The bullets name swarms and routines, but the largest source of noise, and the one in
your screenshot, is **agent-driven and bead-driven launches**: `sase bead work`, epic and
plan approval, LaunchApproval, restarts, and anything with `SASE_AGENT` set. Enumerating
exclusions will leak again with the next automation surface. Proposed rule:

> Prompt history records exactly the text a human submitted through a human-facing entry
> point (TUI prompt bar, `sase run` / `sase prompt run` from a terminal, mobile/Telegram),
> once per submission, including cancelled and failed submissions. Nothing else is
> recorded.

The swarm and routine rules then follow from it instead of being special cases.

**A2 — Record a human request as one row, as typed. _(Requirement change / bug fixes.)_**
Three paths turn one submission into rewritten or multiple rows:

- **`%r:N` repeat**. `launch_repeat_branch_if_applicable` (`launch_cwd_fanout.py:121`)
  never records the typed prompt. Each slot recurses into `launch_single_agent`, which
  records `%i:<base>.<k>\n%wait:<prev>\n…` (`repeat_launcher.py:190-196`). One `%r:3`
  submission therefore produces three machine-rewritten rows and none of the original.
  (The `%{a | b}` alt branch already does it right, recording once at
  `launch_cwd_fanout.py:257`.)
- **Provider-guard remodel**. `_launch_provider_guard.py:399-407` replaces
  `launch.prompt` with the expanded surviving units joined by `---`. That text is then
  recorded as `typed`, whole plus every segment. It is exactly the swarm-member leak the
  request describes.
- **Force-reuse rewrite**. `query_handler/_launch.py:166` records
  `force_reuse_plan.rewritten_prompt` rather than the submitted text.

**A3 — Relaunches are not new requests. _(Requirement clarification.)_**
`sase agent restart` is already `generated`. The TUI's edit-and-relaunch
(`_entry_relaunch.py:447`) goes through the normal prompt-bar path, so it is recorded as
`typed` even when you only bumped `%id(final)` to `%id(final_2)`. That is where the
`final_2` / `final_3` research-lead rows came from. Proposed rules:

- An unchanged relaunch is never recorded.
- An **edited** relaunch is recorded only if the source agent was itself a direct human
  launch. If the source agent was a swarm, epic, or routine member (a clan member, or one
  carrying swarm or job metadata), it is not recorded.

This is a judgment call. The simpler alternative, "edited relaunches are always typed",
is defensible but keeps a small trickle of swarm-member rows, which your requirement
rules out.

**A4 — Clean up what's already there. _(Scope addition.)_**
A write-side fix only helps new rows. With about 8,000 legacy rows (55–80% of each
shard), the modal would stay mostly noise for months, and word completion and
placeholders would stay polluted. A one-time, explicit, dry-run-first prune is needed.

**A5 — Generated failed launches should not go to the Prompt Stash either. _(Scope
addition.)_**
`record_failed_launch_prompt` also stashes the text. Routine jobs are already exempt
(`launch_cwd_agents.py:69-73`), but a failed `sase bead work` or LaunchApproval launch
would currently put a 1–2 KB machine multi-prompt into your stash. The stash is
explicitly a per-user draft pile.

**A6 — Keep typed multi-prompt segment rows (no change).**
When you type a `---` multi-prompt, sase records the whole prompt plus each segment
(e.g., three rows at `260929_160251`). Strictly, that breaks "one row per request". But
the segments are your own text and are individually replayable, so I'd keep them. If they
bother you later, the right fix is a display-level grouping, not dropping them.

### 3.3 Would I take a different approach?

**Only in framing.** Filter by **provenance at write time** (an allow-list of human entry
points), not by **text patterns**, and not by **hiding rows at read time**. The origin
tag already carries the provenance. Text heuristics (`#bd/`, `clan=`, `%wait(`) belong
only in the one-time legacy cleanup, where no provenance exists.

## 4. Options Considered

| Option                                                                                                   | Pros                                                                                                                                                                            | Cons                                                                                                                                                                                                                                                                                                                                                              | Verdict                         |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **A. Write-side gate on `origin`** (never persist `generated`)                                           | One choke point (`add_or_update_prompt` / `record_failed_launch_prompt`). Fixes every reader at once (modal, list, fzf, word index, placeholders, stats). Stops ~77% store growth. Tiny diff because origin is already threaded. | Loses local copies of generated prompts (they stay in agent artifacts and the archive). Relies on correct origin at every site, mitigated by flipping the default (below).                                                                                                                                                                                             | **Recommended**                 |
| **B. Read-side filter** (keep writing, hide `generated` by default, toggle to show)                      | Reversible. No data loss. Handles legacy rows with the heuristic.                                                                                                                 | Must add `origin` to `PromptHistoryRecord`, the catalog, **and the Rust filter wire** (crosses the sase-core boundary plus a pin bump). The filter must run *before* paging (the modal pages 100 at a time). Every other reader (word index, placeholders, fzf, list, stats, run selector) needs its own filter. The store keeps growing with ~4:1 noise. | Rejected as the primary mechanism |
| **C. Separate "launch log" store for generated prompts**                                                  | Keeps a local audit of machine launches.                                                                                                                                        | Duplicates what agent artifacts, chat transcripts, and the agents archive already hold. Violates `decisions:corpus-before-mechanism`: no consumer needs it.                                                                                                                                                                                                  | Rejected                        |
| **D. Move all recording to the human entry points** (pipeline never writes on success)                    | Cleanest architecture: opt-in by construction. Records the exact submitted text, so A2 is fixed for free.                                                                         | Larger refactor. Loses the "record after validation, before spawn" ordering. Needs its own canonicalization so the `project:` filter keeps working. Touches the delicate failed-launch/stash flow.                                                                                                                                                            | Good long-term shape; not needed now |

## 5. Recommended Solution

### Phase 1 — Stop writing machine prompts (small, high value)

1. **Gate at the store.** In `prompt_store_mutations.py`, after
   `_effective_prompt_origin(...)`, have both `add_or_update_prompt` and
   `record_failed_launch_prompt` **return early when the effective origin is
   `generated`**. Skip `record_prompt_placeholders` and the failed-launch stash as well
   (A5):

   ```python
   effective_origin = _effective_prompt_origin(origin)
   if effective_origin == "generated":
       return  # prompt history records human submissions only
   ```

   `rewrite_prompt_text_exact` and the maintenance paths are unaffected.

2. **Widen the automation signal.** Make `_effective_prompt_origin` treat
   `SASE_JOB_NAME` / `SASE_JOB_ROUTINE` (and the legacy `SASE_CHOP_*` aliases) in
   `os.environ` the same as `SASE_AGENT`. That closes the job-script → `sase run` leak.
   Replace the duplicated `SASE_AGENT` checks in `launch_cwd_agents.py:65` and
   `launch_cwd_bead_work.py:73` with that one helper.

3. **Fail closed for undeclared callers.** Change the default `origin` of
   `launch_agents_from_cwd`, `launch_agent_from_cwd`, and `launch_planned_bead_work_agents`
   from `None` to `"generated"`. Every in-tree human entry point already passes `"typed"`
   explicitly. Plugins and future automation then default to "not recorded" instead of
   "recorded with unknown origin". The low-level `add_or_update_prompt(text)` keeps
   `None` = record, so the existing history tests and the TUI cancel paths are
   unaffected.

4. **Docs and tests.** Update the `origin` paragraph in `docs/prompt.md`:
   "`generated` launches are not recorded; `origin` distinguishes typed rows from legacy
   rows". Rework `tests/history/test_prompt_origin.py` so it asserts generated writes are
   no-ops (and don't stash). Adjust the launch tests that expected generated rows
   (`test_launch_planned_bead_work.py`, the `test_axe_chop_*` launch tests,
   `test_cli_work_epic_*`). Add a test that a `sase run` under `SASE_JOB_NAME` records
   nothing.

A feature flag is optional. Nothing is deprecated and no caller has to migrate. If you
want a one-release escape hatch anyway, it would be a `sunset` flag whose Off branch keeps
writing generated rows. I'd skip it.

### Phase 2 — Record one row per human request, as typed (A2)

5. **`%r:N`**: record the submitted `query` once in `launch_repeat_branch_if_applicable`,
   exactly as the alt branch does. Recurse into the slots with `origin="generated"` so the
   rewritten slot prompts are never written.
6. **Provider-guard remodel**: keep the original submitted text on `PendingLaunch` (e.g.
   `history_prompt`) and send it in the `sase run` payload. `query_handler/_launch.py`
   passes it through as the text to record. The rewritten joined units are used only for
   dispatch.
7. **Force-reuse**: record the submitted text, not `force_reuse_plan.rewritten_prompt`.

Steps 6 and 7 share a mechanism: a `history_text` value that the entry point owns and the
pipeline records verbatim (after alias canonicalization). It is a small step toward
Option D without the full refactor.

### Phase 3 — Relaunch semantics (A3)

8. TUI edit-and-relaunch passes `origin="typed"` only when the submitted text differs from
   the source agent's prompt **and** the source agent is not a clan, swarm, epic, or job
   member (use the metadata already on the agent: clan, swarm-xprompt, bead, chop
   fields). Otherwise it passes `"generated"`. Unchanged relaunches are never recorded.

### Phase 4 — One-time legacy cleanup (A4)

9. **Expose the existing heuristic.** Expose `sase_core::prompt_prediction::looks_generated`
   through `sase_core_rs` and move the `sase-core-revision.txt` pin. Don't re-implement it
   in Python (`rust_core_backend_boundary`).
10. **Tighten the heuristic** while you're there. It misses routine rows shaped like
    `%id(chop.refresh_docs…, tribe=chop)` and `%id:toobig-6f.upload.0\n%clan(toobig-6f,
    tribe=chop…)`: 7 of September's 79 `generated` rows fail it. Add `tribe=chop` /
    `%tribe:chop` and `%clan(` markers. Separately, the comment in `origin.rs` says
    `%id(worker, tribe=quality)` counts as a clan-member prompt, but the code only checks
    `clan=`. Don't broaden it to all `tribe=`, since humans assign tribes by hand.
11. **Add `sase prompt prune --generated`.** It fits the existing `prune` predicates
    (`--keep`, `--before`, `--cancelled`, `--dry-run`, `--yes`) in
    `prompt_maintenance.py:292`. It removes rows with `origin == "generated"`, or with no
    origin where `looks_generated(text)`. It **never touches `typed` rows**, shows a
    dry-run count with samples by default, and backs up the shards first. Afterwards,
    invalidate the word-completion index and placeholder seed caches. Expected effect on
    this machine: about 8,000 of 11,584 rows removed, and the modal's first page goes from
    18 human rows to 100.

### Why this order

- Phase 1 alone fixes the screenshot and every new row going forward, in roughly a
  15-line production diff plus tests.
- Phase 2 makes the stored text trustworthy for replay.
- Phase 3 is a policy nuance.
- Phase 4 is a one-time cleanup that you run by hand, after a dry-run, once Phase 1 has
  stopped the bleeding.

### Open questions for you

- **LaunchApproval prompts you approve** (and possibly edit) are treated as `generated`.
  If you often want to re-run an agent-proposed prompt you edited during approval, treat
  an *edited* approval as `typed`, the same way as A3.
- **Gate follow-up shells and `/sase_monitor` commands that call `sase run`** should
  inherit an automation marker. I didn't verify that every such host sets `SASE_AGENT`
  or `SASE_JOB_*`. Audit them in Phase 1 step 2; consider a single `SASE_AUTOMATION=1`
  marker set by all automation hosts.
