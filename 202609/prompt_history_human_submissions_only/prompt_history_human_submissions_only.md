# Prompt history should record what a human submitted, and nothing a machine launched

**Type:** consolidated research report (lead researcher)
**Date:** 2026-09-30 · sase HEAD `63bde575f0`
**Inputs:** five independent reports in this directory (`__cdx`, `__cld`, `__grk`, `__mus`,
`__gem`), plus the lead's own checks against the live prompt store
(`~/.sase/prompt_history/*.json`), the screenshot, the sase checkout, and the linked
`sase-core` checkout.
**Question:** Prompt history stores too many prompts (screenshot
`~/tmp/screenshots/20260930_062115.png`). The proposal is to store only human requests,
with two named rules. Swarm member prompts are not stored, but the `#research_swarm`
invocation is. Routine-launched prompts are not stored. Is this a good idea, what
adjustments are justified, and how should it be built?

---

## Bottom line

1. **Yes, do it. The store is already mostly machine output.** Of the 100 newest rows (the
   History modal's first page), **79 are explicitly `origin=generated`**. Only 18 are
   `typed`, and one of those is a leak. Across the whole store, about **71% of the
   11,587 rows** are machine-shaped. That share has climbed month by month: 59% → 73% →
   80% for July → September.
2. **The two named rules are right, but they are examples of the rule, not the rule
   itself.** In the screenshot, the highlighted row and every `+2`/`+3`/`+4` burst come
   from **`sase bead work` epic fan-out**, which is neither a swarm nor a routine. That
   accounts for 65 of the 79 generated rows. Routine rows are also in the screenshot
   (the 05:39 and 18:36–18:37 `toobig` split jobs, 14 rows). The swarm rule is *already
   met* on the normal launch path: both of today's `#research_swarm` submissions are one
   `typed` row each, with no member rows. **Adjustment:** state one inclusion rule based
   on provenance: *record the canonical text a human submitted, once; record nothing a
   machine launched.* The swarm and routine rules then follow from it.
3. **Most of the plumbing exists, but nothing enforces it.** `PromptEntry.origin`
   (`typed | generated`, commit `eaa4aa4aa7`, 2026-09-29) is already passed by every
   in-tree launch site. Today only the next-word prediction corpus reads it. Both history
   writers still persist `generated` rows. They also learn `<placeholder>` tags from
   them, and failed generated launches get stashed.
4. **A gate on `origin` alone is not enough.** It fixes about 95% of new noise, but I
   verified seven paths where a human submission gets **rewritten, split, or dropped**
   before it is recorded. The worst two: `%if`/`%proc` typed admission and `%dispatch`
   remote launches never record the human root at all. The gate would also leave the
   store's history intact, which is roughly 8,100 legacy rows with no origin.
5. **Recommendation (§7):**
   - **Phase 1:** a central `generated` → no-op gate that runs before placeholders and
     stash, plus wider automation detection, and root recording for typed admission and
     remote dispatch. Phase 1 is one small PR.
   - **Phase 2:** an ingress-owned `history_text`, so each human launch records its
     canonical submitted text exactly once, plus a relaunch rule.
   - **Phase 3:** an explicit, previewed, backed-up `sase prompt prune --generated`, with
     a second heuristic tier for legacy rows.
   - Skip the read-side "show generated" toggle, the separate launch log, and a feature
     flag.

---

## 1. What the screenshot and the store actually show

I checked this myself against the live store, reading its shards read-only.

| Screenshot rows (project:sase, 98/100 loaded) | Store rows | Source | Keep? |
| --- | --- | --- | --- |
| 06:07 `#research_swarm(…):: …` | 1 `typed` | Human swarm invocation | **Yes**. Already correct |
| 06:02 "Can you help me review and relaunch…", 05:48 `#if_so_plan` | `typed` | Human | **Yes** |
| 05:39 ×2, 18:36–18:37 ×3 "Can you help me split `…` into multiple files?" | `generated` | Routine `toobig` split job (`%clan(toobig-6f, tribe=chop …)`) | No |
| Highlighted 01:58 row + 9 same-second rows; bursts at 20:34, 19:00, 18:30, 17:26, 17:22 | `generated` | `sase bead work <epic>`: one joined bundle + one row per ≥5-word phase segment | No |

- The 01:58 cluster is `260930_015851`. It has 10 rows: the 1,664-char `sase-1d5` bundle
  plus 9 phase segments. Across September's 79 generated rows, **ten bead-work bundles
  account for 65 rows** (10 bundles + 55 segment copies). The other 14 rows are routine
  jobs (`toobig`, `refresh_docs`).
- The `+sase` prompt text in these rows is the list summary. The TUI rewrites
  `#gh:gh_sase-org__sase` as `+sase` and strips `%directives` and xprompts. The
  `+2`/`+3`/`+4` values are the TAGS column's overflow chip.
- **One leak is recorded as `typed`**: `260930_065208` is the `sase-1d6.3` epic-phase
  prompt with a hand-appended `%w:0ub`. It came from a TUI edit-and-relaunch of a phase
  agent (§3, row 9).

Store-wide composition. A row counts as machine-shaped if `origin=generated`, or if it
has no origin and matches sase-core's `looks_generated` markers plus
`tribe=chop`/`%tribe:chop`/`%group:chop`:

| Shard | Machine-shaped | Share |
| --- | --- | --- |
| 2607 | 2,212 / 3,755 | 59% |
| 2608 | 2,958 / 4,048 | 73% |
| 2609 | 3,025 / 3,784 | 80% |
| **All** | **8,195 / 11,587** | **71%** (60% of characters) |

The reports' percentages differ (gem 63%, cld 55/73/80%) only because they used
different marker sets. The trend and the conclusion are the same in all of them. 848
of the heuristic-flagged rows contain human-sounding phrasing ("Can you…"). I pulled a
random sample of those, and every one was a template: a `toobig` split prompt or a
research-lead prompt. That suggests the heuristic's precision is high on this corpus,
though a sample is not proof; the prune's dry run is the real check.

## 2. How recording works today (verified)

- **Choke point.** Every write goes through `add_or_update_prompt` or
  `record_failed_launch_prompt` in `src/sase/history/prompt_store_mutations.py`
  (lines 36 and 89).
  - Both call `record_prompt_placeholders(text)` *first* (lines 69 and 116). Only after
    that do they apply the five-word threshold and origin.
  - `record_failed_launch_prompt` also stashes the text (line 142).
  - `_multi_prompt_segment_mutations` (line 145) adds one row per `---` segment of five
    words or more. It does **not** use `allow_short`. That corrects mus: the `+sase`
    rows are ordinary long segments shown through the list summary.
- **Origin.** `_effective_prompt_origin` (line 21) upgrades `typed` → `generated` when
  `SASE_AGENT` is set. The same check is duplicated in `launch_cwd_agents.py:65` and
  `launch_cwd_bead_work.py:74`. Origin is persisted and merged typed-wins. It is
  otherwise ignored. `PromptHistoryRecord` drops it, and the modal, `sase prompt
  list/search/stats`, the word index, and placeholder seeding all read every row.
- **Swarms.** `launch_agents_from_cwd_impl` captures `submitted_query` before swarm
  expansion (`launch_cwd_agents.py:111`). The multi-slot branch records only that text
  (`launch_cwd_fanout.py:88`; since `148d62494a`, 2026-05-21). A `#research_swarm(…)`
  invocation contains no `---`, so it produces exactly one row. **mus's "Leak 1"
  (expanded swarm slots recorded as segments) does not happen on this path.** The live
  store confirms it.
- **Audit homes for machine prompts already exist.** Each agent has `raw_xprompt.md`,
  revival inputs, and a chat transcript. Routines have chop/job run records, and there
  is the canonical agents archive. Prompt history never needs to double as a spawn log.

## 3. Leak inventory

"Verified" means I confirmed it in code at the cited lines, or in live data.

| # | Path | What gets recorded today | Found by | Fix (§7) |
| --- | --- | --- | --- | --- |
| 1 | Generated launches: bead work, epic/plan approval, LaunchApproval, restart, routine jobs, anything with `SASE_AGENT` set | Row written as `generated` | all | Gate |
| 2 | Bead-work bundle (`launch_cwd_bead_work.py:172`) | N+1 rows (bundle + every segment) | all | Gate |
| 3 | Failed generated launch (except chop env) | Cancelled row + **Stash** entry + placeholders | cdx, cld, grk | Gate before stash/placeholders |
| 4 | Generated templates' `<placeholder>` tags | Learned into the common placeholder store | cdx, grk | Gate before placeholders |
| 5 | TUI provider-guard remodel (`_launch_provider_guard.py:395,398`) | Expanded surviving swarm members, joined, recorded as **`typed`** whole + per segment | cld, gem | `history_text` |
| 6 | Swarm that expands to one slot, e.g. via static conditional segments (`launch_cwd_agents.py:198`) | The expanded member prompt, as `typed` | mus, gem | Record `submitted_query` |
| 7 | `%r:N` (`launch_cwd_fanout.py:121–190`) | N rewritten `%id:<base>.k` / `%wait:` slot rows, **no parent** | cld, grk, mus | Record parent once; slots `generated` |
| 8 | Force-reuse (`_launch.py:166`) | `rewritten_prompt` instead of the submitted text | cld | `history_text` |
| 9 | TUI retry / kill-and-edit / edit-and-relaunch of a member agent | Member prompt as `typed` (live row `260930_065208`) | cld (+ live evidence) | Relaunch rule |
| 10 | Direct typed admission `%if`/`%proc` when admission accepts it (`_launch.py:171`, `launch_admission_runtime.py:141`) | Root **never recorded**; units go in as `generated`. Once gated, the launch leaves no trace | cdx, grk | Record root at ingress |
| 11 | Remote `%dispatch` (`_launch.py:89` early return) | Root **never recorded** on the submitting machine (pre-existing; I did not trace what the target machine records) | cdx (flagged) | Record root at ingress |
| 12 | `sase run` from an agent's monitor, proc, or gate follow-up shell | **`typed`**. Monitor and proc supervisors scrub `SASE_AGENT` (`env_hygiene.scrub_agent_identity_env`; `monitor/supervise.py:208`). Gate commands inherit the approving process's env | **new (lead)**; cld raised as open question | Widen automation detection |
| 13 | `sase run` from a job script (`SASE_JOB_*`/`SASE_CHOP_*` env, no `SASE_AGENT`) | `typed` | cld, mus, gem | Widen automation detection |
| 14 | Launcher called without `origin` (plugins, future code) | Recorded, origin unknown | cld | Fail-closed default |

Rows 12–14 are **latent**. No live rows show them today: jobs request follow-up launches
through the runner, which already passes `generated`, and this machine has no custom job
scripts. They matter because they are exactly how the next automation surface will leak.

## 4. Critique of the plan

### What is right

- "One row = one thing a human asked for" is the right definition. Every consumer of
  history depends on it: Ctrl+K recall, `sase prompt run`, word completion, placeholder
  memory, and next-word prediction.
- Replaying generated rows is **hazardous**, not just noisy. Loading and submitting an
  epic bundle relaunches fixed `%id(sase-1d5.N)` names, `%w(bead=…)` waits, and
  `#bd/work_phase_bead` bindings.
- Keeping the `#research_swarm` invocation is right. It is the replayable intent, and
  the normal path already does it.

### Adjustments I recommend (requirement changes are flagged)

- **R1 — Generalize to provenance. _(Requirement change.)_** Replace the two exclusions
  with one inclusion rule:

  > Prompt history records the canonical text a human submitted through a human entry
  > point: the TUI prompt bar (including cancelled and failed submits), `sase run` or
  > `sase prompt run` from a terminal, and mobile/Telegram. It records that text once per
  > submission. Nothing launched by an agent, routine/job, monitor, gate, bead work,
  > plan/epic approval, LaunchApproval, or restart is recorded.

  Two exclusions would miss the screenshot's largest source (bead work) and leak again
  with the next fan-out surface. All five reports agree.
- **R2 — "Came through `sase run`" is not "human". _(Clarification.)_** Agents,
  monitors, and gate shells also call `sase run`. Classify by *who initiated* the launch,
  not by which executable or UI it went through (rows 12–13).
- **R3 — Record the submitted text, not what the pipeline turned it into. _(Requirement
  strengthening.)_** "Canonical" means after alias and project-tag canonicalization (so
  dedup and the `project:` filter keep working), and before swarm, repeat, alt,
  admission, provider-guard, or force-reuse rewriting (rows 5–8, 10–11). This is the
  precise form of "save the swarm invocation".
- **R4 — Relaunching a member agent is not a new request. _(Requirement addition.)_**
  When the TUI relaunch source is a swarm, clan, epic, or job member, record it as
  `generated`. When it is a standalone agent, keep recording it as `typed`; an unchanged
  relaunch only bumps `last_used`, which is harmless. This simplifies cld's rule by
  dropping its "unchanged" clause. Note that it would also drop your `%w:0ub` edit at
  06:52. That is consistent with your rule, but you should confirm you want it (see the
  open questions).
- **R5 — Keep user-authored `---` segment rows. _(No change.)_** A typed multi-prompt
  records the whole text plus each segment (for example the three typed rows at
  `260929_160251`). The segments are your own text and can be replayed individually.
- **R6 — A failed machine launch gets no Stash entry and no placeholder learning.
  _(Scope addition.)_** Stash is a per-user draft pile. Today only chop-env failures are
  exempt.
- **R7 — Cleaning up existing rows is in scope. _(Scope addition.)_** A write-side fix
  alone leaves about 8,100 legacy rows polluting search, the word index, and older pages.

### Adjustments I reject

- **Keep writing generated rows but hide them** (mus's store-and-hide split; the
  read-side-first framing in grk, gem, and mus). Nothing consumes those rows. The audit
  trail already lives elsewhere (§2), and this would violate
  `decisions:corpus-before-mechanism`. A hide filter would also have to be repeated in
  every consumer, and must run *before* pagination in the Rust filter wire (a sase-core
  change plus a pin bump). A prune fixes all consumers at once.
- **Keep the stored origin when a row is replayed** (mus A4). Replaying a row is a human
  submission, so recording it as `typed` is correct.
- **A third origin value** (`swarm`/`routine`/`bead_work`). This adds cost to every call
  site without improving the policy (grk agrees).
- **Text heuristics for new writes.** Heuristics belong only in the one-time legacy
  cleanup, where no provenance exists.
- **Performance claims** such as "4× faster parsing" (gem). These are unmeasured, and the
  case doesn't need them.

### Would I take a different approach?

I would keep the consensus core: gate on provenance at write time, with no text
heuristics. I would differ on two points:

1. **Clean the store rather than filter reads.** A one-time, explicit prune (with
   backup) plus a write gate leaves nothing to hide. That makes a show/hide toggle, the
   `PromptHistoryRecord.origin` plumbing, and the Rust filter-wire change unnecessary.
2. **Make the human entry point own the recorded text.** Today each pipeline branch
   (single, multi, repeat, alt, bead work) records whatever text it holds at that point,
   and that is how rows 5–11 arise. Instead, the ingress (`launch_query` and the mobile
   launcher) computes a canonical `history_text` and the pipeline records exactly that.
   This is a small step toward cld's "Option D" without the full refactor.

## 5. Options considered

| Option | Verdict |
| --- | --- |
| A. Literal exclusions: skip swarm members and routine env at the write site | **Reject.** Misses bead work (65/79 rows), plan/LaunchApproval/restart/monitor launches, and future surfaces |
| B. Read-side hide of `generated` + toggle, keep writing | **Reject as primary.** Store keeps growing ~4:1 noise; needs per-consumer filters + sase-core filter-wire change; toggle has no user |
| C. Separate "launch log" store for machine prompts | **Reject.** Duplicates agent artifacts, transcripts, job records; `corpus-before-mechanism` |
| D. Write gate: effective origin `generated` → no-op | **Adopt** (Phase 1) |
| E. Ingress-owned `history_text`, recorded once | **Adopt, scoped** (Phase 2): closes rows 5–11 without moving all recording out of the pipeline |
| F. Explicit prune of existing machine rows | **Adopt** (Phase 3), previewed and backed up |

## 6. Disagreements between the reports, resolved

| Question | Positions | Resolution |
| --- | --- | --- |
| Do swarm members leak on the normal path? | mus: yes, via segment recording | **No.** `submitted_query` has no `---`; live store shows one row per swarm. Swarm members leak only via rows 5, 6, 9 |
| Where do the short `+sase` rows come from? | mus: `allow_short` fragments | **The list summary.** Segment rows are ≥5 words; the display strips directives and the `#gh:` ref |
| Does the screenshot contain routine rows? | cld/grk: the flood is bead work, "neither swarm nor routine" | **Both.** The highlighted row and bursts are bead work. The 05:39 and 18:36–37 rows are `toobig` routine jobs |
| Legacy cleanup | cdx: explicit `generated` only, keep unknown rows; cld/gem/mus: heuristic too; grk: hide, prune optional | **Two tiers:** explicit `generated` rows (safe), then heuristic legacy rows shown in the dry run with counts and samples. Always back up; never touch text that is `typed` anywhere |
| Read-side filtering | grk/gem/mus: default-hide + toggle; cdx: hide explicit generated; cld: reject | **No toggle.** Gate + prune leaves nothing to hide (§4) |
| Launcher default `origin` | cld: default `generated`; grk: keep `None`, enforce with a test | **Default `generated` at the launcher entry points**, after checking linked plugins (sase-telegram, sase-github) for direct calls. `add_or_update_prompt` keeps `None` = record |
| Feature flag | cld: optional sunset; grk: none | **None.** Per the flag policy, no caller migrates and no old branch has to stay reachable. This is a correction of documented intent |
| Rust boundary | cdx: Python gate is fine; cld/grk: expose `looks_generated` from sase-core | **Both.** The two-line gate sits next to the Python-owned store and `is_recordable_prompt`. The legacy classifier stays in sase-core, is extended there, and is exposed through `sase_core_rs` |

## 7. Recommended solution

**Invariant:** *Prompt history records the canonical text a human submitted, once per
submission. Machine-originated launches never write a history row, a Stash entry, or a
placeholder.*

### Phase 1: stop the bleeding (one PR)

1. **Gate at the store.** In both `add_or_update_prompt` and
   `record_failed_launch_prompt`, resolve the effective origin first. If it is
   `generated`, return before `record_prompt_placeholders`, the threshold, any shard
   mutation, or `stash_failed_launch_prompt`. A generated reuse of text that is already
   typed therefore no longer bumps its `last_used`, so recency means "last human use".
2. **Use one automation detector.** Make a single `effective_prompt_origin()` helper and
   use it at all three current check sites. It upgrades `typed` → `generated` when any
   of these is set:
   - `SASE_AGENT`;
   - `SASE_JOB_*` or `SASE_CHOP_*` (reuse `is_chop_launch_env` against `os.environ`);
   - `SASE_MONITOR_ID`;
   - a new gate-command marker set by the gate command runner.

   Do **not** use `SASE_PROC_*`, because TUI submissions themselves run as durable
   `sase run` procs. If the audit finds further agent-started procs or oneshots that
   launch agents, add one `SASE_AUTOMATION=1` marker. The spawner would set it when its
   own env is automation, and `scrub_agent_identity_env` must preserve it. Set that
   marker at the automation roots (agent runner, job runner, monitor supervisor, gate
   runner), never on every proc, because the TUI's human submissions run as procs.
3. **Default the launcher entry points to not recording.** `launch_agents_from_cwd`,
   `launch_agent_from_cwd`, and `launch_planned_bead_work_agents` default to
   `origin="generated"`. Every in-tree human caller already passes `"typed"`: `sase run`,
   `_mobile_agent_launch.py`, and the TUI paths. First check the linked plugins
   (sase-telegram, sase-github) for direct launcher calls; one without an origin would
   otherwise silently stop recording human launches.
4. **Record the root for paths that bypass the pipeline.** These must land in the same
   PR as step 1, or `%if`/`%proc` launches disappear from history entirely:
   - direct typed admission (`_dispatch_direct_typed_launch_if_active`);
   - the remote-dispatch early return.

   In both, record the canonical submitted query once with
   `allow_short=True, origin="typed"`, on the same success/failure semantics as the
   legacy path.
5. **Docs and tests.** In `docs/prompt.md`, describe `origin` as a write policy, not a
   prediction hint. In `docs/xprompt.md`, say that segment recording applies to
   user-authored multi-prompts only. Rework `tests/history/test_prompt_origin.py` and the
   launch tests that currently expect generated rows (bead work, chop, epic).

### Phase 2: record the right text once

6. **Add an ingress-owned `history_text`.** `launch_query` and the mobile launcher
   compute the canonical submitted text and pass it down. The pipeline records that text
   instead of its branch-local `query`:
   - **provider guard:** keep the original prompt on `PendingLaunch` and send it in the
     `sase run` payload alongside `launch_units`;
   - **force-reuse:** record the pre-rewrite text;
   - **single-slot swarm:** record `submitted_query`, not `expanded_segments[0]`;
   - **`%r:N`:** record the parent once, the way the alt branch does, and recurse into
     the slots with `origin="generated"`.
7. **Add the relaunch rule (R4).** TUI retry, kill-and-edit, and edit-and-relaunch pass
   `origin="generated"` when the source agent carries clan, swarm/template-group, bead,
   or job metadata, and `"typed"` otherwise.

### Phase 3: clean the existing store (run by hand, after Phase 1)

8. **In sase-core:**
   - Add routine markers to `looks_generated` (`tribe=chop`, `%tribe:chop`,
     `%group:chop`). It currently misses 7 of September's 79 explicit generated rows and
     about 900 legacy routine rows.
   - Fix the doc comment that claims `%id(worker, tribe=quality)` matches. Do not
     broaden to every `tribe=`, because humans assign tribes by hand.
   - Expose `looks_generated` through `sase_core_rs` and move `sase-core-revision.txt`
     past that commit.
9. **Add `sase prompt prune --generated`** next to the existing predicates.
   - It removes rows with `origin=generated`. With `--heuristic`, it also removes
     `origin=None` rows that match `looks_generated`.
   - It never removes a text that is `typed` anywhere. Removal works by text across
     shards, so it must rely on the typed-wins merge in
     `load_prompt_history_for_write`, and it needs a test for that.
   - Dry run by default, showing counts and samples. It writes a shard backup before
     applying.
   - `sase prompt doctor` should report the counts.
   - Expected result on this machine: 79 explicit + about 8,100 heuristic rows out of
     11,587. The first History page goes from about 18 human rows to 100.
10. **Optional:** remove `<placeholder>` tags that only generated templates contributed
    from the common placeholder store, or reseed it from the pruned history.

### Not doing

- A read-side show/hide toggle, a separate launch log, a feature flag, or moving the
  history store into Rust as part of this change. If the store later moves into
  sase-core, the gate moves with it.

### Tests that matter

- Generated `add_or_update_prompt` and `record_failed_launch_prompt` write no shard, no
  placeholders, and no Stash entry, and don't bump an existing typed row.
- `typed` is coerced to generated under `SASE_AGENT`, `SASE_JOB_NAME`,
  `SASE_CHOP_NAME`, `SASE_MONITOR_ID`, and the gate marker.
- `#research_swarm(…)` records exactly one row. So do a single-slot swarm and a
  provider-guard-remodeled swarm; each records the invocation text.
- A bead-work launch with N segments records 0 rows (today it records N+1).
- A typed `---` multi-prompt still records the whole text plus its segments.
- `%r:3` records the parent once and no slot rows.
- `%if`/`%proc` direct admission and `%dispatch` each record the root once.
- A relaunch of a clan member records nothing. A relaunch of a standalone agent is
  recorded as typed.
- Prune dry-run and apply keep typed rows, keep a typed copy when a generated duplicate
  exists in another shard, and write a backup.

## Open questions for you

1. **Edited relaunches of member agents** (your `%w:0ub` edit at 06:52): should they
   stay out of history, as recommended, or count as typed because you edited them?
2. **LaunchApproval prompts you edit before approving:** keep them `generated`
   (recommended), or treat an edited approval as `typed`?
3. **The heuristic prune tier:** is it acceptable to delete about 8,100 legacy rows
   after a dry run and a backup, or should only the 79 explicitly generated rows go?

## Source reports

- `__cdx`: the clearest framing ("typed means user-submitted"). It found typed admission
  and remote dispatch as root-recording risks, and cautioned against destructive legacy
  guessing.
- `__cld`: the fullest write-site table. It found the provider-guard, `%r:N`,
  force-reuse, and relaunch leaks, the fail-closed default, the heuristic's chop-marker
  gap, and the Stash exemption gap.
- `__grk`: a good policy table and test plan. It also found typed admission and `%r:N`,
  and argued for trusting `typed` over heuristics.
- `__mus`: the routine subprocess hole and the single-slot swarm path. Its main claim,
  that swarm segments are recorded on the normal path, and its `allow_short` explanation
  are incorrect (§6).
- `__gem`: store-wide measurements, the provider-guard and single-slot leaks, and the
  prune proposal. Its performance numbers are unmeasured.
