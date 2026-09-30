# Prompt history should record human requests, using origin

- **Researcher:** grk (independent swarm report)
- **Date:** 2026-09-30
- **Scope:** When a launched prompt is written to `~/.sase/prompt_history/`, and how
  that store is shown in the Prompts overlay. Evidence from the current tree plus
  `~/tmp/screenshots/20260930_062115.png`.

## Verdict

The goal is right. Prompt history is a recall tool for prompts a human submitted, the
same way shell history is a recall tool for commands a human typed. The implementation
should **not** special-case xprompt swarms and routines as two one-off exclusions. Those
are two instances of a taxonomy the code already has: `origin: typed | generated`.

**Recommended solution:** stop writing `origin=generated` rows; record the human
submitted prompt once on every human launch surface (including typed admission and
`%r:N`); default the History overlay and `sase prompt list` to typed rows, using the
existing Rust `looks_generated` heuristic only for legacy rows with no origin; add an
explicit prune for leftover generated rows. Keep user-authored `---` segments. Keep
short typed swarm triggers via `allow_short`.

The screenshot's highlighted row is generated **bead-work / epic-clan** text
(`#bd/work_phase_bead`, `%clan(sase-1d5, tribe=epic, …)`), which would still flood
History if the change only skipped swarm members and lumberjack chops.

---

## 1. What the screenshot actually shows

The Prompts overlay is on History, project-scoped to `sase`, `98 / 100 loaded`.

| Row (from the capture) | What it is | Should history keep it? |
| --- | --- | --- |
| `06:07` `#research_swarm` + `Can you help me review and relaunch the 1d5…` | Human invocation of an xprompt swarm | **Yes** — this is the request |
| `06:02` `#plan` / `#if_so_plan` with a question | Human (or human-looking) request | **Yes** if typed |
| Highlighted `02:58` preview starting `%sase` / `%id(sase-1d5.1, bead=sase-1d5.1)` / `%clan(sase-1d5, tribe=epic, summary_script=sase_clan_summary_epic)` / `#bd/work_phase_bead:sase-1d5.1` / `#plan` then many `---` segments | Rendered `sase bead work` / epic-clan multi-prompt | **No** |
| Same-timestamp cluster of `+sase` rows whose TAGS column is `+2` / `+3` / `+4` | Per-segment copies of that multi-prompt (`record_segments=True`); `+N` is the History tag-column overflow chip, not an xprompt name | **No** |

The highlighted preview is the body `launch_planned_bead_work_agents` writes as
`normalized_query = "\n---\n".join(normalized_segments)` with `origin="generated"`
(`src/sase/agent/launch_cwd_bead_work.py`, `src/sase/bead/cli_work_launch.py`). Default
`record_segments=True` then writes each clan member as its own row. After
`summarize_prompt_for_list` strips directives and xprompts, those member rows collapse
to a `+sase` preview and overflow as `+3` in the 16-column TAGS field
(`src/sase/ace/tui/modals/_prompt_history_rows.py`).

The 06:07 `#research_swarm` row has **no** same-timestamp member cluster under it. The
legacy CWD launch path already records `submitted_query` (the invocation) and does not
re-record swarm-expanded slots. Swarm-member clutter is real on the **typed-admission /
per-unit dispatch** path (`origin="generated"` per unit). The screenshot's dominant
clutter is bead-work fan-out, which the stated swarm+routine rule would miss.

---

## 2. Critique of the stated plan

### 2.1 What is already right

- History exists so a human can replay a request from the TUI widget or `sase run`.
  `docs/prompt.md` and `docs/ace.md` already describe it that way: prompts launched from
  the TUI or `sase run`, useful to replay, with a five-word floor for terse scraps.
- The swarm *invocation* belongs in history. `#research_swarm` is the thing the human
  will want to edit and resubmit. Member bodies are library text plus one shared
  argument payload.
- Routine (lumberjack / chop) launches are machine requests. They already stamp
  `origin="generated"` and already skip failed-launch stash recording when
  `is_chop_launch_env` is set. Successful recording is the remaining leak.
- `allow_short` for a bare swarm trigger is justified. `#research_swarm` is often under
  five words and is still a real request.

### 2.2 Where the stated rules are too narrow

**Adjustment 1 — treat every machine-generated launch the same way.**

The request names two sources (xprompt-swarm members, routine launches). The write sites
that already pass `origin="generated"` are:

| Surface | File | Typical prompt |
| --- | --- | --- |
| Typed-admission unit dispatch | `launch_admission_runtime.py` | One expanded slot, including swarm members |
| LaunchApproval dispatch | `launch_request_response.py` | The approved prompt, often already expanded |
| Axe chop / proposal | `chop_typed_admission.py`, `chop_proposal_launch.py` | Routine-authored agent prompt |
| `sase bead work` | `bead/cli_work_launch.py` | Joined `#bd/work_phase_bead` clan prompt (the screenshot) |
| Plan-approval follow-up | `plan_direct_approval_run.py` | Generated implement/review prompt |
| Agent restart | `_restart_execute.py` | Replay of a previous agent prompt |
| Anything inside `SASE_AGENT` | `_effective_prompt_origin` | Forced `generated` even if the caller passed `typed` |

A swarm-name check or a lumberjack-env check at the history layer will rot the first
time a new fan-out surface is added. Origin is already threaded through those sites.

**Adjustment 2 — save the submitted text once, even when fan-out is internal.**

Two human paths currently fail that test:

1. **Direct typed admission** (`%if` / `%proc` in `dispatch_direct_typed_launch`). The
   bundle stores `submitted_prompt`, then each unit calls
   `launch_agents_from_cwd(..., origin="generated")`. Nothing records the human query as
   `typed`. Skipping generated writes without adding a typed write here would *drop* the
   invocation.
2. **`%r:N` repeat** (`launch_repeat_branch_if_applicable`). There is no
   `add_or_update_prompt` on the original query. Each recursive slot records
   `spec.prompt` with the parent's origin, so a typed `%r:5` can write five near-copies
   (or one, if the rewritten texts collide).

The multi-prompt branch already does this correctly: it records `submitted_query` with
`allow_short=True` before spawning expanded segments.

**Adjustment 3 — keep user-authored `---` segments.**

`record_segments=True` is the right default when the human typed the separators. The
docs in `docs/xprompt.md` say each segment is saved so it can be reused from the picker.
The bug is applying that default to *machine-joined* multi-prompts (bead work) and to
*expanded* swarm bodies. Gate it on origin and on "did the submitted text contain `---`",
not on "did expansion produce multiple slots."

**Adjustment 4 — hide leftover generated rows; do not silently delete them.**

Stopping new writes leaves the current month's shard full of bead-work clones. Auto-delete
on upgrade is surprising (content-addressed IDs, `sase prompt` scripts). Default-hide is
the same pattern History already uses for cancelled rows (`Ctrl+X`). Offer
`sase prompt prune --origin generated` as an explicit cleanup.

**Adjustment 5 — trust `origin=typed` over the text heuristic.**

`sase_core::prompt_prediction::origin::looks_generated` is a solid legacy classifier
(`#bd/work_phase_bead`, `#bd/` plus `%id(`, leading `%wait(`, `%swarm(`, `%lead(`,
"SASE single-turn instructions for", `%id(` plus `clan=`). The screenshot row matches
several of those markers. A human who types `%id(worker, clan=research)` would also
match. Prediction already treats `origin="typed"` as typed regardless of markers
(`is_generated_row` in `corpus.rs`). History should do the same: hide `generated`; for
`origin=None` apply `looks_generated`; never hide `typed`.

**Adjustment 6 — skip generated placeholder and word-index contributions too.**

`add_or_update_prompt` records `<placeholder>` tags *before* the five-word floor, so
generated templates would still pollute completion if the only change is "don't append a
history row." `PromptWordIndex` currently tokenizes every loaded shard row with no origin
filter. Prediction already excludes generated rows; the word index and placeholder store
should follow.

---

## 3. Is this a good idea?

Yes. The store is already described as replayable human launches. Generated rows fight
that in four concrete ways:

1. **Recall.** The first 100 recency slots fill with clan/bead-work clones. Human prompts
   from earlier the same morning fall behind `+100 older`.
2. **Size.** Each bead-work or swarm-member body is a full template. Dedup is by exact
   text, so N members plus the joined multi-prompt are N+1 rows per tick.
3. **Prediction.** The next-word corpus was built to drop generated rows. History still
   *shows* them, which is why origin was added in the `prompt-origin` phase of
   `plans/202609/prompt_next_word_prediction.md` without changing the picker.
4. **Completion.** History-word ranking learns `#bd/work_phase_bead`, `%clan(`, and
   research-swarm boilerplate.

Agent-sidecar archives (`sase agent prompts`), chat transcripts, and launch records
already keep what actually ran. History does not need to be a second spawn log.

---

## 4. How recording works today

```
human TUI / sase run          origin="typed"
        │
        ├─ legacy CWD path
        │     expand swarms → if N>1: record submitted_query (allow_short)
        │                     then spawn expanded slots (no extra history writes)
        │     if 1 slot: record that slot's query
        │
        └─ typed admission (%if/%proc)
              expand → plan units → each unit launch origin="generated"
              submitted_prompt is on the bundle, not in history

sase bead work / chops / LaunchApproval units / plan follow-up / restart
        origin="generated" → add_or_update_prompt still writes the row
```

Choke point: `src/sase/history/prompt_store_mutations.py` `add_or_update_prompt` and
`record_failed_launch_prompt`. `_effective_prompt_origin` already upgrades `typed` to
`generated` when `SASE_AGENT` is set.

The History overlay (`prompts_modal.py`, `_prompt_history_rows.py`) has no origin
filter. `PromptHistoryRecord` does not even carry `origin` (`prompt_catalog.py`
`record_from_entry` / `to_entry` drop it). `sase prompt list` filters cancelled and
substring only. `sase prompt prune` accepts `--keep`, `--before`, `--cancelled`.

`allow_short` exists specifically so a bare xprompt-swarm trigger still records. That
flag stays on the **typed submitted query**, and goes away for generated writes.

---

## 5. Approaches considered

### A. Pattern-match swarm names and lumberjack env at the write site

Matches the request literally. Misses bead work (the screenshot), plan follow-ups,
restarts, LaunchApproval units, and the next fan-out surface. Couples history to
`#research_swarm` as a name, even though swarms are any xprompt whose body contains
`---`.

### B. UI filter only, keep writing generated rows

Reversible and immediately fixes the overlay. Leaves shard bloat, word-index pollution,
and placeholder pollution. Pagination still spends I/O on rows nobody will replay.

### C. A third origin (`swarm` / `routine` / `bead_work`)

Useful for badges, expensive for policy. Every write site has to pick the right subtype.
`typed` vs `generated` already answers "does this belong in History."

### D. Origin write policy + typed source-prompt once + default-hide leftover rows
**(recommended)**

One choke point (`origin=generated` does not persist). Human surfaces record the text
the human submitted, once. Existing clutter is hidden with the same toggle pattern as
cancelled rows. Optional prune is explicit.

---

## 6. Recommended solution

### 6.1 Policy (product)

Prompt history stores **human-authored launch text**.

| Event | Record? |
| --- | --- |
| TUI submit, `sase run`, `sase prompt run`, cancelled typed draft | Yes, `origin=typed` |
| `#research_swarm …` / any xprompt-swarm invocation the human submitted | Yes, the invocation text only |
| User-typed multi-prompt with `---` | Yes, the whole prompt and each user segment |
| Swarm-expanded member slots | No |
| Lumberjack / chop / job agent launches | No |
| `sase bead work`, epic-clan fan-out, `#bd/work_phase_bead` bundles | No |
| LaunchApproval / typed-admission *unit* dispatch | No |
| Plan-approval generated follow-up, agent restart | No |
| Launch from inside a SASE agent (`SASE_AGENT`) | No |
| Failed human launch (including short `#gh:foo`) | Yes, cancelled typed, as today |
| Failed generated launch | No (chops already skip; extend to all generated) |

### 6.2 Write path

In `add_or_update_prompt` and `record_failed_launch_prompt`, after
`_effective_prompt_origin`:

- If `effective_origin == "generated"`, return without writing placeholders, segments, or
  a shard row.
- Leave `origin=None` writes alone so tests and legacy callers stay explicit; audit
  production callers so new launch sites pass `typed` or `generated`.

Then close the two human-source gaps:

1. `dispatch_direct_typed_launch` (and the ACE durable `sase run` worker that uses it):
   `add_or_update_prompt(submitted_prompt, allow_short=True, origin="typed")` once,
   before unit dispatch. Use the unexpanded query, matching `submitted_query` on the
   legacy path.
2. `launch_repeat_branch_if_applicable`: record `query` once with the incoming origin
   before recursive slots. Recursive slot launches pass `origin="generated"` **or** the
   skip-generated rule plus "already recorded the parent" — the cleaner option is to
   pass `origin="generated"` on the recursive calls so they cannot double-write even if
   the skip rule is later relaxed.

Keep `launch_multi_prompt_branch`'s `submitted_query` recording. Add a regression test
that `#three_phase(login)` / a catalog swarm writes one history row (the invocation)
and zero expanded member texts.

Bead work already passes `origin="generated"`; the choke point drops both the joined
query and the segment copies.

### 6.3 Read path

- Add `origin` to `PromptHistoryRecord` (it is currently dropped).
- Default History overlay and `sase prompt list` to **typed-visible**: keep
  `origin="typed"`; keep `origin=None` unless `looks_generated(text)`; drop
  `origin="generated"`.
- Expose `looks_generated` through the existing `sase_core_rs` prompt-prediction module
  rather than copying the marker list into Python. The compiler already uses
  `is_generated_row`.
- Toggle in the overlay (new key, parallel to `Ctrl+X` for cancelled). Footer should
  say when generated rows are hidden, the way cancelled already does.
- `sase prompt list --origin all|typed|generated` for scripts. Default `typed`.
- `PromptWordIndex` and placeholder recording skip the same set as the overlay default.

### 6.4 Cleanup of existing shards

- `sase prompt prune --origin generated` intersecting the current `--keep` / `--before`
  floor so a recent typed prompt cannot disappear.
- Dry-run by default or require `--apply`, matching artifact prune. Do not run this
  automatically on upgrade.

### 6.5 Docs

- `docs/prompt.md`: origin is a *write policy*, not only a prediction hint.
- `docs/xprompt.md` multi-prompt rule: user-authored segments are stored; swarm-expanded
  slots are not.
- `docs/ace.md` History section: generated launches are omitted unless the toggle is on.

### 6.6 What stays out of this change

- Stash / Trash: still unsent human drafts. Failed *human* launches still stash.
- Canonical agents-sidecar prompt archive: still the published post-run corpus.
- `sase bead work` and lumberjack UX: they keep launching; they stop polluting History.
- Saving an expanded swarm the human produced with Ctrl+I in the prompt bar, then
  submitted: that text is `typed`. It is large, but it is what they submitted. A later
  polish can warn; it is not this bug.

---

## 7. Test plan (implementation, not this research)

- `add_or_update_prompt(..., origin="generated")` leaves the shard empty and does not
  call `record_prompt_placeholders`.
- Inside `SASE_AGENT=1`, `origin="typed"` is still coerced to generated and not written.
- `sase run '#research_swarm …'` writes one typed row; member bodies absent.
- User multi-prompt `Do A\n---\nDo B` writes three typed rows (whole + two segments), as
  today.
- `sase bead work` writes zero history rows.
- Chop launch with `SASE_JOB_NAME` / `SASE_CHOP_NAME` writes zero history rows.
- Direct typed admission records the unexpanded submitted prompt once.
- `%r:3` records the original query once.
- History page default omits a stored `origin=generated` fixture and a `origin=None`
  `#bd/work_phase_bead` fixture, and keeps a typed `#research_swarm` fixture.
- Word index built from a mixed shard does not contain `#bd/work_phase_bead` from the
  generated fixture.

---

## 8. Risks

- **Forgotten `origin=None` on a new launch site** would keep writing. Mitigate with a
  test that grep/imports every `add_or_update_prompt` / `launch_agents_from_cwd` caller
  and requires an explicit origin, plus the `SASE_AGENT` upgrade already in place.
- **Typed admission currently under-records.** Skipping generated without the new typed
  write would hide `%if`/`%proc` human launches. Land those two writes in the same
  change.
- **`looks_generated` false positives on legacy `origin=None` rows** that a human typed
  with `%id(..., clan=...)`. Rare, and the toggle brings them back. Do not apply the
  heuristic to `origin="typed"`.
- **People who today replay a bead-work member from History** lose that shortcut. The
  member prompt still lives on the agent; `sase bead work` is the supported replay.

---

## 9. Suggested landing shape

One medium feature, two tight PRs if split:

1. **Write policy + source-prompt once** (choke point, typed-admission write, `%r`
   write, swarm/bead/chop tests). This stops the bleeding.
2. **Read policy + prune + docs** (catalog `origin`, overlay/CLI default, word index,
   `prune --origin generated`). This clears the screenshot.

No feature flag is needed: the documented product already claims History is TUI/`sase
run` launches. The flag would hide a bug fix.

---

## 10. One-sentence recommendation

**Do not enumerate swarm members and routines. Stop persisting `origin=generated`,
record each human submitted prompt once, and default History to typed rows (with
`looks_generated` only for legacy unlabeled rows).**
