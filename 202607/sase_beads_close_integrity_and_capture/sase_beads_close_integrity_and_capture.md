# SASE Beads: Close Integrity and Capture

Date: 2026-07-30

Consolidates two independent research reports produced the same day:

- [`__a`](sase_beads_close_integrity_and_capture__a.md) — architecture-forward (storage, concurrency, query, analytics).
- [`__b`](sase_beads_close_integrity_and_capture__b.md) — measurement-forward (five-day delta, adoption, doc rot).

Both supersede `202607/sase_beads_leverage_20260725/` (07-25) and `202607/sase_beads_full_potential_consolidated/`
(07-14). Every figure below was re-measured against the live store on 2026-07-30. No bead was created, edited, closed,
reopened, or removed during this research.

## Headline

The two source reports agree on the diagnosis of the *last* five days and disagree sharply on what to do next. `__b`
says the top of the backlog is prompt and documentation text; `__a` says it is storage, claiming, and event
architecture. Re-measurement supports `__b`'s ordering, and turns up a third thing neither report found that outranks
both:

**The close path is not idempotent. 323 of 977 closed beads (33%) carry more than one `issue_closed` event — one bead
carries seven.** 1,203 field writes land *after* a bead's first close, across 643 beads. 36% of recently-closed beads
were closed by more than one Git commit.

That single defect explains three symptoms the source reports each attributed to something else:

- **The 301 lost note revisions** (`__a`'s #1, `__b`'s N7) are not primarily a cross-clone merge artifact. The beads
  sidecar has **zero merge commits in 773** — its history is entirely linear. Notes are being lost to a close that
  re-runs and rewrites the whole `notes` string each time.
- **The commit churn** `__a` attributed to a per-epic Git hotspot is duplicate work, not contention. The largest event
  stream in the store is 175 lines; the median is ~26. There is no hot file.
- **Flow analytics are blocked harder than `__b` estimated.** Cycle time's terminal event is duplicated a third of the
  time *and* is 0% agent-attributed.

So the shape of the gap is: the engine got materially better in five days, but **the record it writes is not yet
trustworthy enough to measure, nothing is allowed to write to the backlog half, and the read command that would drain
that backlog now points at a status that no longer means what it used to.**

Nothing here is a fire. All 12 in-progress beads are live and moving; no bead is stuck.

## Verified state (2026-07-30)

| Measure | 07-14 | 07-25 | **07-30** | Note |
|---|---:|---:|---:|---|
| Total beads | 1,479 | 2,014 | **2,417** | ~81/day, up 65% |
| Open / claimed | 0 | 18–21 | **0 / 0** | see F2 |
| In progress | 0 | 6–8 | **12** | 4 live epics |
| Closed | 1,479 | ~1,990 | **2,405** | |
| Event streams / events | — | 343 / 7,971 | **418 / 10,736** | `__a` reported 421 streams; actual is 418 |
| `--tier plan` beads | n/a | 3 | **3** | all closed; unchanged across 403 new beads |
| Design links resolving | 8/228 (3.5%) | 104/334 (31%) | **352/391 (90%)** | `doctor` names only 28 of the 39 failures |
| Lost note revisions | — | — | **301** | `--restore` never run |
| `--changespec` / `--bug-id` | — | 4 (fixtures) | **0 / 0** | |
| Sizes recorded | — | — | **1,896 none, 202 S, 300 M, 18 L, 1 XS, 0 XL** | |
| Sidecar pack | — | — | **7.03 MiB** | 2,418 published pages |

Flow characteristics differ between the source reports because they measured different things. `__a` reports
create-to-close p50 = 65 min over 1,758 beads; `__b` reports lead time p50 = 1.4 h over 973 beads with a *complete*
lifecycle, plus queue wait p50 = 3.0 min separately. **`__b`'s figures are the ones to carry forward** — separating
queue wait from lead time is the distinction that makes the number mean anything, and `__a` concedes its own measure is
not execution time. Both are provisional until F1 and F3 below are fixed.

Since 07-25 the 07-25 report's top-10 largely shipped: `history` (with `--lost-notes`/`--restore`), appending `note`,
typed close resolutions, the descendant-close guard, `open`, all three `dep` verbs, JSON on four verbs, logical `plans:`
references, `doctor --fix-design-refs`, the pytest-store firewall, the ACE Plans pane, and a skill rewrite (7 → ~17 of
21 verbs). Also new and in neither prior report's scope: a **dedicated `beads` sidecar repo**, **2,418 published bead
pages** with URLs in commit trailers, **launch preassignment**, and **phase-range closing** (`close <epic> -p 1-3`).

## The three load-bearing findings

### F1 — Close is not idempotent, and it rewrites notes each time it re-runs

Measured across all 10,736 canonical events:

| Signal | Value |
|---|---:|
| Beads with >1 `issue_closed` event | **323 of 977 (33%)** |
| Maximum `issue_closed` events on one bead | **7** |
| `issue_updated` writes landing after first close | **1,203** across 643 beads |
| Post-close writers | 899 owner-attributed, 304 agent-attributed |
| Beads closed by >1 Git commit (recent window) | **80 of 225 (36%)** |
| Merge commits in the beads sidecar | **0 of 773** |

`sase-aq.4` — the one recent bead in the 301 lost-note set, and the case `__b` flagged as "a residual post-close write
path" — is the clean reproduction:

```text
14:19:04 · sase-aq.4              · issue_updated · notes      ← close --note, agent-attributed
14:19:04 · bryanbugyi34@gmail.com · issue_closed  · resolution ← same transaction, owner-attributed
14:19:43 · sase-aq.4              · issue_updated · notes
14:20:23 · bryanbugyi34@gmail.com · issue_updated · notes      ← replacing write, drops prior text
14:21:37 · sase-aq.4              · issue_updated · notes
```

Git shows three separate `chore(beads): close sase-aq.4` commits for that one completion, plus an `update`. Its
siblings `sase-aq.1` and `sase-aq.3` were each closed twice.

`__b` correctly spotted the symptom and sized it as "small". It is not small: it is a third of the store, it is the
mechanism behind the 301 lost notes, and it makes every close timestamp — the terminal event of every cycle-time
metric — unreliable. `__a` proposed the right durable remedy (append-only journal events) for the wrong reason
(cross-clone divergence, which the zero merge commits rule out) and at the wrong layer. The journal would preserve both
note writes but would still record three completions for one piece of work.

Fix the re-entrancy first. The journal is worth doing afterward, for handoff quality, not as an integrity patch.

### F2 — Preassignment retired the queue without anyone deciding to

Every bead in the store was created by `sase bead work` (377 plan beads, 2,040 phase). Since `1943e18a7`, that path
assigns all of them to `in_progress` at the pre-spawn checkpoint. So a bead is `open` only during the compile→launch
window — **median 65 seconds** since 07-28 (n=167; p90 163 s, max 339 s).

`sase bead ready` therefore reports "No issues ready (all blocked or none open)" not because the backlog drained, but
because *an `open` bead is a bead being launched right now*. Any agent claiming one would be racing the launcher for
work already assigned to a named agent.

Three artifacts of the retired model remain live: `sase bead ready` takes zero arguments and can never return anything;
`#bd/next` (`default_config.yml:897`) still tells agents to run it; and `docs/xprompt.md:943` still advertises it as the
"What should I work on next?" helper. It fails safe — the prompt terminates when nothing is ready — so this is inert,
not dangerous.

**This resolves the largest disagreement between the two reports.** `__a` ranks atomic `ready --claim` with
compare-and-set and a publication barrier as its #2, on the reasoning that "a check-then-act loop is the wrong primitive
for autonomous agents." That is true in the abstract, but the path it protects currently carries **zero traffic**, and
`__a` did not measure that. Hardening an unused code path is not the second-most-valuable thing available. The decision
to make first is what `open`/`ready`/`#bd/next` should *mean*; atomic claiming becomes worth building only if the answer
is "rebuild the queue," and only after F3 shows work actually arriving in it.

### F3 — Actor attribution is not partial, it is per-operation and absent on close

`__b` reported attribution at 13–27% by day. The per-operation breakdown is sharper and more actionable:

| Operation | Agent-attributed | Owner-attributed | Agent % |
|---|---:|---:|---:|
| `issue_updated` | 521 | 3,021 | **15%** |
| `issue_created` | 0 | 2,523 | **0%** |
| `dependency_added` | 0 | 1,971 | **0%** |
| `issue_closed` | 0 | 1,439 | **0%** |
| `epic_work_preclaimed` | 0 | 975 | **0%** |
| `ready_marked` | 0 | 239 | **0%** |
| `issue_removed` | 0 | 41 | **0%** |

Across 10,736 events there is **not one exception**: only `issue_updated` ever carries an agent actor, and 244 of those
521 come from just two agents (`sase-a1.land`, `sase-a1.6`).

The `sase-aq.4` trace above locates the bug exactly: within a *single* `close --note` transaction, the note's
`issue_updated` is agent-attributed and the `issue_closed` emitted in the same second is owner-attributed. The actor is
threaded through the note mutation and dropped by every other mutation. This is a narrow plumbing fix, not the
cultural "make it the default path" `__b` implied.

Until it lands, `__a`'s recommendation #6 (flow analytics broken out by model routing and agent) is not merely noisy —
it is **not computable**, because the close event carries no agent identity at all.

## Where the reports disagree, and what the evidence says

| Question | `__a` | `__b` | Verdict |
|---|---|---|---|
| Top priority | Append-only journal events (Rust boundary, medium-high effort) | Delete the capture prohibition (two-sentence prompt edit) | **`__b`, then F1 above both.** The journal is the right shape for a problem whose observed cause is re-entrancy. |
| Atomic `ready --claim` | Rank #2 | Not raised | **Defer.** The path has zero traffic (F2). Revisit only if the queue is rebuilt. |
| Per-epic Git hotspot | Rank #3, "High" effort re-architecture to content-addressed objects | Not raised | **Not supported.** 0 merge commits in 773; largest stream 175 lines. The real cost is commit *volume* (368 commits on 07-28) and duplicate work (F1), not file contention. |
| Event identity | "Independent additions should never need ordinal renumbering" | Not raised | **`__a` is right about the mechanism, wrong about the urgency.** `event_id` is literally `sase-aq:000029:issue_updated:...` — a per-stream ordinal. That is the coupling to fix *if* the store ever goes multi-writer. It is not today's problem. |
| Flow metrics | Rank #6, elaborate derivation list | Rank #7, prerequisite is attribution | **`__b` on sequencing** (attribution first), **`__a` on content** (queue vs. active vs. blocked time are the right decompositions). Add F1 as a second prerequisite. |
| Lost notes | Symptom of snapshot-shaped storage | Symptom of a residual write path; run `--restore` | **`__b`'s remedy, `__a`'s framing is a layer too high.** Run `--restore` (one idempotent command, 301 beads) *after* F1, so recovery is not immediately re-corrupted. |
| Size ladder | Cohort table shows `medium` p50 *faster* than `small` | 1,896 of 2,417 beads carry no size; `xlarge` = 0 | **Both, combined:** the ladder is simultaneously unexercised and, where exercised, non-predictive. It cannot be calibrated before F3. |
| Upstream `steveyegge/beads` | Dolt gives row-level merging; take the lesson, not the architecture | 120 commits in 5 days, almost all Dolt/server plumbing; do not follow | **Agree — do not follow.** Five small items transfer: `90c6f46f5` (project identity check before destructive `doctor --fix`), `d1f67a91e` (`rm` dry-run preview), `ecb9e9273` (`bd schema` — JSON Schema for machine output), `13d2c8d6b` (refuse overwriting a live foreign claim), `920827971` (multi-status ready queries). |

`__a`'s unique contributions worth keeping: the bead query corpus over the existing Rust query engine, typed completion
evidence, the flow-metric decomposition, and the small typed relation set. `__b`'s unique contributions worth keeping:
the capture prohibition, the `open`/`ready` semantic break, the documentation-correctness findings, the adoption
measurements, and the destructive-operation gaps.

## Confirmed, and neither report should be softened on these

- **The capture prohibition is verbatim intact.** `default_config.yml:941` (`bd/work_phase_bead`, run by *every* phase
  agent): *"Do NOT close the parent epic. Do NOT create new beads."* And `:909` (`bd/next`): *"IMPORTANT: Do NOT create
  any beads of your own."* Result: `--tier plan` usage is 3 beads (`sase-26`, `sase-5s`, `sase-71`), all closed,
  identical to the 07-25 snapshot, across 403 newly created beads. Every dependency it needed has shipped — the
  destination (`--tier plan`), the promotion path (`update --tier epic` → `work`), the inbox view, honest-close
  semantics, queryable history, the ACE pane. Only the sentence remains.
- **`sase bead onboard` is wrong about where the store lives.** It states the source of truth is *"this checkout's
  sdd/beads/ event store"*; since `3dba997d0`/`73a75f94d` bead operations route to the `beads` sidecar, which is not in
  the checkout. Its examples still use retired `sdd/plans/202605/` paths. An agent following it looks in the wrong place.
- **Three surfaces an agent consults do not mention key features.** `pages`: 0 mentions in
  `src/sase/xprompts/skills/sase_beads.md`. `onboard`: 0 mentions. The word "bead": **0 occurrences** in
  `sase/memory/xprompts.md`, which is the memory file governing the `%wait(bead=)` and `%id(…, bead=)` directives.
- **`ready`, `blocked`, and `stats` have no `--format json`** and take no arguments. No published JSON schema, no
  exit-code contract.
- **`--changespec` and `--bug-id` are 0 and 0 across 2,417 beads**, and neither flag exists on `update` — so a bead
  cannot be attached to a ChangeSpec after creation, which is exactly when you would know. That is a plausible
  explanation for the zero, not merely evidence of disuse.
- **`doctor` under-reports.** 39 design refs fail to resolve; `doctor` names 28 (14 malformed/missing, 14 owner
  mismatch). The 11 it misses include two live-regression cases (`sase-64`, `sase-ap`) where a correctly-formed modern
  `plans:` reference points at a deleted plan file. The reverse direction is unchecked: 59 of 478 plan files (12.3%)
  carry a `bead_id:` absent from the store. It also still leads every run with `WARNING: beads.db missing`, which trains
  readers to skip its output, and permanently reports two pytest-residue beads (`sase-8q`, `sase-8s`).
- **Destructive operations are unguarded.** `sase bead rm <id>` removes beads *and all children* with no `--dry-run`, no
  preview, no confirmation. `doctor --fix-design-refs` mutates after a prompt but performs no project-identity check.

## Anti-recommendations (both reports agree; reaffirmed)

- **No Dolt, daemon, server, replicas, leases, or federation.** The event-sourced Git-native store is the right
  strategic choice and is ahead of upstream's original design, not behind it.
- **No second workflow engine inside beads** — no molecules, formulas, wisps, gates, or agent mail. SASE already has
  plans, xprompts, agent lanes, waits, gates, notifications, tasks, and ChangeSpecs.
- **No priority levels or label taxonomy yet.** There is still no query the dependency graph and `search` cannot answer.
  Revisit only if recommendation 2 produces a backlog large enough to need triage — a good problem to have.
- **No beading of tales.** 279 non-`done` tale plans without beads is policy, not debt. The epic tail is the one that
  matters, and it halved (30 → 14).
- **No retention or compaction yet.** 7.03 MiB pack. But add the growth early-warning: 81 beads/day is 65% faster than
  a week ago.
- **No automatic semantic deduplication or autonomous priority rewriting.** Agents may propose; canonicalization stays
  reviewable.

## Ranked recommended improvements

Ranking principle: **make the record trustworthy, then unblock what is built but forbidden, then instrument, then
build.** Items 1–7 are the ones with evidence behind them today; 8–12 are the best of the forward-looking work and
should be sequenced after the measurement surface is honest.

**1. Make close-and-publish idempotent, then repair the historical duplicates.**
The highest-value change available and the one neither source report identified. A second close of an already-closed
bead should be a verified no-op, not a re-applied mutation; post-close `notes` writes must append rather than replace.
Then de-duplicate the 323 beads carrying multiple `issue_closed` events so close timestamps mean something, and run
`sase bead history --lost-notes --restore` (idempotent, one confirmation, 301 beads) *after* the fix rather than
before. Success test: a re-run of `sase bead close` on a closed bead produces no new event and no new commit; the
duplicate-close count stops growing. (F1; supersedes `__b` R4 and reframes `__a` R1.)

**2. Delete the capture prohibition and give discovered work a destination.**
A two-sentence prompt edit whose every dependency has already shipped. In `bd/work_phase_bead`, replace *"Do NOT create
new beads"* with *"Do not create beads for yourself to work. Record discovered follow-up as a `PROPOSED FOLLOW-UP:`
entry via `sase bead note <your-bead> '…'`."* Narrow `bd/next` the same way. In `bd/land_epic` step 1 — which already
runs `sase bead show` on every child — add: *"collect `PROPOSED FOLLOW-UP:` entries from child notes and file each as
`sase bead create --tier plan …`, or record why not."* Keep the guardrail: phase agents *propose*, the land agent
*files*. Precedent that the lever works: `close --reason` went 0 → 72 → 169 purely as a practice change. Success test,
checkable in a week: `sase bead list --tier plan --status open` is non-empty for the first time in the store's history.
(F2/N2.)

**3. Decide what `open`, `ready`, and `#bd/next` mean after preassignment.**
Make deliberately a decision that was made accidentally. Ship the cheap half now: drop `#bd/next` from
`default_config.yml` and `docs/xprompt.md:943`, and make `sase bead ready` say *"no standing queue; epic work is
preassigned at launch"* rather than "all blocked or none open," which reads as transient. Revisit the better end
state — `ready` meaning *"`--tier plan` beads with no unresolved blockers"* — once recommendation 2 has demonstrated
that follow-ups actually get filed. Either way, exclude launch-window beads: a bead assigned to a named agent should
never surface as available work. (F2.)

**4. Thread the acting agent through every mutation, not just `issue_updated`.**
Currently `issue_created`, `issue_closed`, `dependency_added`, `epic_work_preclaimed`, and `ready_marked` are 0%
agent-attributed across 10,736 events, while a single `close --note` transaction attributes its note event and not its
close event. Fix the mutation plumbing so the actor reaching `append_issue_note` reaches the rest. This is the
prerequisite for item 7 and it makes `history` immediately more useful — the point of a timeline is knowing who did
what. (F3.)

**5. Repair the documentation that is now wrong.**
`sase bead onboard` misstating the store location is a correctness bug, not polish. Fix the source-of-truth paragraph,
replace retired `sdd/plans/` examples, and add `history`, `note`, `pages`, `close --resolution`, `work --dry-run/--json`
and the `--tier plan` loop. Then close the skill gaps in `src/sase/xprompts/skills/sase_beads.md` (regenerate per
`memory/generated_skills.md`; do not hand-edit provider copies): `%wait(bead=<id>)` and `%id(<name>, bead=<id>)`,
`sase bead pages url <id>`, the `--tier plan` backlog loop as a worked example, and `onboard` itself. Add the word
"bead" to `sase/memory/xprompts.md`, which contains zero occurrences of it. Add the contract test comparing documented
verbs against the argparse surface — the skill drifted 7/18 → ~17/21 with nothing preventing regression.

**6. Finish `doctor`, guard the destructive paths, then schedule it as a chop.**
Detection first: catch the 11 broken design refs it misses (including `sase-64`/`sase-ap`, well-formed `plans:`
references to deleted files — a class that will recur); check the reverse direction (59 plan files with absent
`bead_id:`); report closed beads whose plan is still `wip` and `wip` epic plans with no bead (14 today); add a
projection/stream growth early warning. Stop leading with `WARNING: beads.db missing`. Add `sase bead rm --dry-run`
with confirmation when the removal set includes children, and a project-identity check before `--fix-design-refs`
mutates (upstream `d1f67a91e`, `90c6f46f5`). Then run it as a `bead_doctor_checks` chop alongside the existing
`bead_claim_checks` and `bead_store_refresh`, which turns every one-time cleanup in this report into a standing
regression guard. While there, `sase bead rm sase-8q sase-8s` to clear the permanent pytest residue.

**7. Complete the machine surface, then ship `sase bead stats --flow`.**
These are one item because the first gates the second and both gate the chop in item 6. Add `--format json` to `ready`,
`blocked`, and `stats`; publish a schema for the JSON envelope (upstream `ecb9e9273` is the model); document an
exit-code contract so a chop can branch without parsing prose. Then derive and expose queue wait, active time, blocked
time and blocker attribution, lead-time percentiles, reopen/retry rate, forced/canceled/superseded closure rate, WIP
age, throughput, and critical-path delay. The payoff is phase duration and outcome **by `--size` and by model** — the
only way to calibrate a five-size ladder that is currently guessed (1,896 of 2,417 beads carry no size; `xsmall` = 1,
`xlarge` = 0) and, on the visible cohort, non-predictive. Blocked on items 1 and 4; the numbers in this report were
computed from the existing streams with ~40 lines of Python, so the data is there once the events are honest.

**8. Build a bead query corpus and make `ready` a query-backed view.**
Generalize the existing Rust query parser/evaluator — currently hard-coded to ChangeSpec-oriented property keys — so
entity corpora can declare their own fields. Expose facts SASE already stores: status, type, tier, resolution,
owner/assignee/run, ancestry, timestamps, size, model, ready/blocked/blocks-count, `has:design`, `has:verification`.
Then `sase bead ready --type phase --parent sase-xy --sort criticality --explain`. Do **not** start with a label
taxonomy or custom statuses; the value is querying what already exists. Reuse the existing saved-query experience across
CLI, ACE, and mobile. (`__a` R4, unchanged in substance; deferred behind the measurement fixes rather than demoted.)

**9. Make completion evidence structurally distinguishable — start small.**
`close --note` text is not distinguishable from a progress or handoff note, so a land agent must parse prose to decide
whether verification happened. Begin with a typed entry kind on the close note (`verification`) carrying command, exit
status, and commit/artifact references, and give the land agent a compact per-phase evidence matrix. Record first, warn
second, require only for configured epic flows after adoption is measured. Do not build the full completion-certificate
schema `__a` specifies until the recording habit exists — close-time notes are at 46% and explicit `--reason` at 27%.

**10. Exercise the seams that have never been used.**
Practice, not product. Add `--changespec` and `--bug-id` to `update` (0 and 0 uses across 2,417 beads, and the flags
exist only on `create` — you rarely know the ChangeSpec at creation time), then try them on the next PR-backed epic.
Decide out loud whether `actstat` and `bob-cli` should run `sase bead init`, rather than letting single-project usage
persist by drift.

**11. Adopt first-class append-only journal events.**
The right durable shape — typed entries (`progress`, `handoff`, `decision`, `blocker`, `verification`) with content-
derived IDs, reduced into the `notes` projection, with corrections as new events. Ranked here rather than first because
the loss it prevents is currently produced by re-entrancy (item 1), not by concurrent divergence: the store has zero
merge commits. Do it for handoff quality and as the substrate for item 9, and design the entry identity alongside any
future event-ID work — `event_id` currently embeds a per-stream ordinal (`sase-aq:000029:…`), which is the real
obstacle to commutative appends if the store ever becomes multi-writer. (`__a` R1, re-motivated.)

**12. Draw the line on TUI write access.**
`src/sase/ace/tui/modals/bead_edit_modal.py` ships title and description editing from the ACE Plans pane, against both
prior reports' explicit "read and triage only" anti-recommendation. The modal is narrow and probably fine; the point is
that the boundary moved without a decision. Either amend the guidance — editing a title is not workflow — or state the
line before the next modal adds status transitions and closes.

### Deferred, with reasons

- **Storage re-architecture to content-addressed event objects** (`__a` R3): targets a conflict class not in evidence.
  Revisit if merge commits ever appear or a stream exceeds a few thousand events.
- **Atomic `ready --claim` with a publication barrier** (`__a` R2): protects a path with zero current traffic. Becomes
  item-3-dependent. Upstream `13d2c8d6b` (refuse overwriting a live foreign claim) is the cheap narrow form to take
  first if anything is taken at all.
- **Typed relation graph** (`__a` R7): `--tier plan` plus a `PROPOSED FOLLOW-UP:` note convention may cover the
  `discovered_from` case without new link types. Revisit a few weeks after item 2 ships. `superseded` is at 0 uses
  across 2,417 beads, which is implausible and worth fixing by practice before by schema.
- **Plan-revision binding and `sase bead reconcile`** (`__a` R8): good idea, blocked behind item 6 finishing the link
  checks it would build on.
- **Cross-project bead references** (`__a` R9): two of three enabled projects have no bead store and 0 claims. Premature.

## Use beads better starting today

Zero feature work required:

1. **Pass `--note` on every close.** At 46%, over half of completions record no evidence, and both the ACE pane and the
   2,418 published pages render notes.
2. **Use `sase bead pages url <id>`** when referencing a bead outside the terminal — PRs, notifications, other projects.
3. **File follow-ups as `--tier plan` beads by hand** until item 2 lands, starting with the 14 orphaned `wip` epic plans.
4. **Reserve `--resolution canceled|superseded` deliberately.** Zero `superseded` in 2,417 beads is not credible given
   how often plans get re-planned as `_1`/`_v2`.
5. **`sase bead work <plan> --dry-run` before every fan-in epic** — still the cheapest correctness check available.
6. **`sase bead history <id> --format full`** when picking up someone else's work; it reveals the revision chain `show`
   flattens — which, until item 1 lands, is the only place a clobbered note is visible.

Hold `sase bead history --lost-notes --restore` until item 1 ships. Running it now recovers 301 beads into a write path
that is still capable of losing them again.

## Sources

- **Live store, 2026-07-30.** `sase bead stats|ready|list|show|doctor|onboard|history|pages|--help`; direct analysis of
  `sase/repos/beads/issues.jsonl` (2,417 records) and `events/streams/*.jsonl` (418 files, 10,736 events), including
  per-operation actor breakdown, duplicate-close and post-close-write census, and stream size distribution.
- **Beads sidecar Git history.** 773 commits; merge-commit count, per-day commit volume, per-bead close-commit
  multiplicity, and files-changed profile.
- **Source.** `src/sase/default_config.yml` (`bd/*` xprompts at 868–941), `src/sase/bead/`,
  `src/sase/main/parser_bead.py`, `src/sase/xprompts/skills/sase_beads.md`,
  `src/sase/ace/tui/modals/bead_edit_modal.py`, `src/sase/ace/tui/widgets/artifacts/plans_detail.py`.
- **Docs and memory.** `docs/beads.md`, `docs/xprompt.md`, `sase/memory/xprompts.md`, `sase/memory/generated_skills.md`.
- **Upstream.** `gh:steveyegge/beads` at `0e069115a` (2026-07-30), opened via `sase repo open`; 120 commits since
  07-25, of which `90c6f46f5`, `d1f67a91e`, `ecb9e9273`, `13d2c8d6b`, `920827971` transfer.
- **Prior research.** The two source reports in this directory, plus `202607/sase_beads_leverage_20260725/`,
  `202607/sase_beads_full_potential_consolidated/`, `202603/sase_beads.md`, `202605/axe_open_bead_tree.md`.
- **External practice** (via `__a`): upstream Beads `ready`/`query`/`graph-links`/observability docs, GitHub issue
  fields and Project insights, Linear filters/relations/insights, Taskwarrior urgency, Temporal activity heartbeats.
