# Improving SASE Beads

Date: 2026-07-30
Supersedes: `202607/sase_beads_leverage_20260725/` (2026-07-25), which superseded
`202607/sase_beads_full_potential_consolidated/` (2026-07-14).

All figures below were measured directly against the live store, event streams, plan sidecar, source tree, and the
upstream checkout on 2026-07-30 (~15:00 EDT). No bead records were created, edited, closed, reopened, or removed during
this research.

## Headline

**Five days, ~70 bead-related commits, and the 2026-07-25 report's top-10 is mostly done.** `history`, appending
`note`, close resolutions, the descendant-close guard, `open`, `dep list/tree/rm`, `--format json` on
`list`/`show`/`search`, logical `plans:` design references, `doctor --fix-design-refs`, the pytest-store firewall, the
ACE bead detail pane, and a rewritten skill all shipped. Design-link resolution went from 31% to 90%. The leaked test
fixtures were purged. The engine got materially better.

**One recommendation was skipped, and it was the one everything else was waiting on.** R3 — narrowing the "Do NOT create
new beads" prohibition — is a two-sentence prompt edit that was never made. `bd/work_phase_bead` and `bd/next` still
forbid capture verbatim. Consequently the standing-backlog primitive (`--tier plan`) is still used by exactly **3 beads,
all closed, unchanged across 403 new beads in 5 days**.

**And a good fix quietly broke a command.** The 07-28 launch-preassignment change means beads now sit in `open` for a
median of **65 seconds** — the compile→launch window — and nothing else. `sase bead ready` returns "No issues ready" not
because the backlog is drained but because *a bead that is `open` is a bead being launched right now*. `#bd/next`, the
"what should I work on next?" xprompt, can no longer select anything.

So the shape of the gap has changed. It is no longer "beads lack a memory half." The memory half now exists and works.
It is: **nothing is allowed to write to it, and the read command that would drain it points at a status that no longer
means what it used to.**

## Snapshot (2026-07-30)

| Measure | 2026-07-14 | 2026-07-25 | **2026-07-30** |
|---|---:|---:|---:|
| Total beads | 1,479 | 2,014 | **2,417** |
| Open | 0 | 18–21 | **0** |
| In progress | 0 | 6–8 | **16** |
| Closed | 1,479 | ~1,990 | **2,401** |
| Growth rate | — | ~49/day | **~81/day** |
| `--tier plan` beads | n/a | 3 | **3** |
| Design links resolving | 8/228 (3.5%) | 104/334 (31%) | **352/391 (90%)** |
| Event streams / events | — | 343 / 7,971 | **418 / 10,729** |
| CLI verbs | 10 | 18 | **21** |
| Skill-documented verbs | 7 | 7 | **~17** |

Flow characteristics computed from the event streams (973 beads with a complete create→close lifecycle):

- Lead time (create → close): **p50 1.4 h, p90 6.3 h, max 84.3 h**
- Queue wait (create → first execution signal): **p50 3.0 min, p90 41.1 min**
- Reopened beads: **3**
- Stuck beads: **none** — all 16 `in_progress` beads are 1.2–1.6 h old, across 4 live epics

The store is healthy and moving fast. Nothing below is a fire.

## Scorecard: What Shipped Since 2026-07-25

| 07-25 rec | Status | Evidence |
|---|---|---|
| R1 Stop test writes to production store | **Done** | `sase.core.state_write_guard.pytest_path_is_sandboxed`; `289222b19`, `c95b361f1`, `3e0dbc723`. Fixtures `sase-97`, `9a`–`9d` purged |
| R2 Rewrite the `sase_beads` skill | **Mostly done** | 177 → 306 lines; ~17 of 21 verbs. Gaps: `%wait(bead=)`, `%id(…, bead=)`, `pages`, `onboard`, `--changespec` all absent |
| R3 Narrow the capture prohibition | **Not started** | `default_config.yml:941` and `:909` unchanged, verbatim |
| R4 Make `doctor` validate | **Partly done** | Now checks design refs + owner mismatch; misses 11 of 39 broken links, checks nothing in reverse; no hygiene chop |
| R5 `--tier plan` backlog + `ready` filters | **Not started** | 3 tier-plan beads (unchanged); `sase bead ready` still takes zero arguments |
| R6 ACE open-bead tree | **Done, differently** | Artifacts → Plans pane with full bead detail (`plans_detail.py`), status glyphs, plan preview — plus a `BeadEditModal` |
| R7 History + truthful close | **Done** | `history` (with `--lost-notes`/`--restore`), appending `note`, `done/canceled/superseded`, descendant-close guard, `open` |
| R8 `--json` + exit codes | **Partly done** | `list`/`show`/`search`/`work`/`pages refresh` have JSON. `ready`, `blocked`, `stats` have none. No schema, no exit-code contract |
| R9 `dep rm`/`list`/`tree`, CAS guards | **Mostly done** | All three `dep` verbs shipped (`87bc8f72f`, `786b6720e`, `793887cf8`). No `--if-status`/`--if-assignee` |
| R10 Exercise unused seams | **Not started** | `changespec`: **0**. `bug_id`: **0**. `xlarge`: 0. `xsmall`: 1. `actstat`/`bob-cli`: still no bead store |
| R11 Flow metrics | **Not started** | `sase bead stats` still takes zero arguments |

Also new since 07-25, in neither prior report's scope:

- **A dedicated `beads` sidecar repo.** Bead state split out of the plans sidecar into `sase/repos/beads` (`3dba997d0`,
  `73a75f94d`, `5cf149c1f`).
- **Bead pages.** 2,419 generated Markdown pages published to `github.com/sase-org/sase--beads`, with
  `sase bead pages refresh|url` and page URLs embedded in commit trailers (`SASE_BEAD=[sase-aj.3][1]` → a real
  browsable link). Beads became web-addressable artifacts.
- **Launch preassignment.** `sase bead work` now assigns every phase and land bead to `in_progress` under its exact
  agent name before any runner spawns (`1943e18a7`).
- **Phase-range closing.** `sase bead close <epic> -p 1-3` (`1f0296ade`).
- **Partial agent actor attribution** on events, starting 2026-07-27.

## New Findings

### N1 — `open` is now a 65-second transient, and `ready` has no input

`sase bead stats` reports 0 open. `sase bead ready` reports "No issues ready (all blocked or none open)."

This is not an empty backlog. Measured across the create → `epic_work_preclaimed` interval:

| Window | n | p50 | p90 | max |
|---|---:|---:|---:|---:|
| All time | 924 | 144 s | 558 s | 2,953 s |
| **Since 2026-07-28** | 167 | **65 s** | 163 s | 339 s |

Every bead in the store was created by `sase bead work` (377 plan beads, of which 374 are `epic` tier; 2,040 phase
beads). Since `1943e18a7`, that path assigns all of them to `in_progress` at the pre-spawn checkpoint. So a bead is
`open` only during the ~1-minute window between graph compilation and launch — and any agent that grabbed one from
`ready` would be racing the launcher for work already assigned to a named agent.

The consequence is that **`#bd/next` is dead**. `docs/xprompt.md:943` still advertises it as the "What should I work on
next?" helper; `default_config.yml:897` still tells the agent to run `sase bead ready`, claim, work, and close. It fails
safe — the prompt says "if there are no non-epic beads ready to work, terminate without doing anything" — so this is not
dangerous, just permanently inert.

Preassignment was the right call; it made epic launches recoverable. But it retired the queue model without anyone
deciding to, and `open` / `ready` / `#bd/next` are now three artifacts of a model that no longer runs.

### N2 — The capture prohibition survived, and is now the sole blocker

Verbatim, unchanged since the 07-25 report named this as recommendation #3:

- `src/sase/default_config.yml:941` (`bd/work_phase_bead`, run by **every** phase agent):
  *"Do NOT close the parent epic. Do NOT create new beads."*
- `src/sase/default_config.yml:909` (`bd/next`):
  *"IMPORTANT: Do NOT create any beads of your own."*

`bd/land_epic` routes discovered work to `/sase_plan`, not to a bead: *"If steps 1-2 uncover remaining work, use your
/sase_plan skill to plan it."* That produces a plan file, which is exactly the shadow backlog described in N6 — a
durable artifact with no queue, no dependency edges, and no `ready`.

The result is measurable and unambiguous: **`--tier plan` usage is 3 beads (`sase-26`, `sase-5s`, `sase-71`), all
closed, identical to the 07-25 snapshot, across 403 newly created beads.** Zero adoption in five days of very heavy use.

This matters more now than it did on 07-25 because every dependency has since shipped. The destination exists
(`--tier plan`), the promotion path exists (`update --tier epic` → `work`), the inbox view exists
(`list --tier plan --status open`), the honest-close semantics exist, the history is queryable, and the ACE pane will
render it. The only thing standing between all of that and a working backlog is one sentence in two prompts.

Precedent that the lever works: `close --reason` went 0 → 72 → **169** purely as a practice change, and close
resolutions reached 81% adoption within days of shipping.

### N3 — Bead pages are a major new surface that agents are never told about

`sase bead pages` generates deterministic Markdown pages into the beads sidecar and publishes them:

```
$ sase bead pages url sase-b8
https://github.com/sase-org/sase--beads/blob/main/pages/sase-b8/README.md
```

2,419 pages exist. Commit trailers now carry live links (`SASE_BEAD=[sase-aj.3][1]` → the hosted page). This is a
genuinely new capability class — beads are citable from PRs, notifications, chat, and other projects without CLI access.

But `pages` appears **0 times** in `src/sase/xprompts/skills/sase_beads.md`, and `sase bead onboard` predates it
entirely. The two surfaces an agent actually consults do not know the feature exists.

### N4 — `sase bead onboard` is now actively wrong

It is the only surface that covers the CLI broadly, and no agent is told it exists (0 skill mentions). It also now
misstates the storage model:

- Claims the source of truth is *"this checkout's sdd/beads/ event store"*. Since `3dba997d0`/`73a75f94d`, bead
  operations route to a **dedicated `beads` sidecar repo** (`sase/repos/beads`), which is not in the checkout.
- Every example uses retired `sdd/plans/202605/` paths.
- Omits `history`, `note`, `pages`, `close --resolution`, `work --dry-run`, `work --json`, `--size`, `--model`,
  `--changespec`, and the `--tier plan` backlog loop.

A stale doc is worse than a missing one: an agent that follows it will look in the wrong place for the store.

### N5 — Event actor attribution is 13–27%, which blocks flow metrics

Of 10,729 events, **10,211 are attributed to `bryanbugyi34@gmail.com`** — the store owner, not the acting agent. Agent
identity appears only from 2026-07-27 onward and only partially:

| Day | Events | Agent-attributed |
|---|---:|---:|
| 2026-07-25 | 395 | 0 (0%) |
| 2026-07-26 | 273 | 0 (0%) |
| 2026-07-27 | 946 | 254 (27%) |
| 2026-07-28 | 511 | 66 (13%) |
| 2026-07-29 | 442 | 98 (22%) |
| 2026-07-30 | 411 | 100 (24%) |

The 07-25 report's highest-ceiling item (R11, flow metrics) wanted "phase duration and defect rate **by size and model
role**." That is not computable from a stream where three quarters of the mutations say "the human." Attribution is the
prerequisite, not the metric.

### N6 — `doctor` under-reports broken plan links by 28%, and checks nothing in reverse

The logical-reference migration worked: 345 of 391 design refs now use the `plans:202607/foo.md` form, and **352 of 391
(90%) resolve**, up from 31%.

But of the **39 that do not resolve, `doctor` names only 28** (14 as "missing or malformed", 14 as "owner mismatch").
Eleven are silently invisible — and two of those are the interesting class:

```
sase-64  plans:202607/bead_work_from_plan_file.md      ← new logical form, target gone
sase-ap  plans:202607/agent_id_reference_syntax.md     ← new logical form, target gone
```

These are not legacy residue. They are correctly-formed modern references whose plan file was renamed or deleted after
the fact — a live regression class that will recur, and the check that would catch it does not exist.

The reverse direction is unchecked entirely: **59 of 478 plan files (12.3%) carry a `bead_id:` that is absent from the
store** (e.g. `202602/axe_lumberjacks.md → sase-0xd`, `202602/telegram_1.md → sase-70gx`). Any tool trusting plan
frontmatter to find a bead misses ~1 time in 8.

Separately: the two remaining pytest-path beads (`sase-8q`, `sase-8s`) are still in the store as closed residue and
still appear in every `doctor` run, permanently. They should be removed now that the firewall prevents recurrence.

Finally, `doctor` still leads with `WARNING: beads.db missing` on every invocation, which trains readers to ignore its
output.

### N7 — 301 beads hold recoverable lost note revisions; `--restore` has never been run

`sase bead history --lost-notes` reports **301 beads with dropped note revisions**. The recovery path shipped
(`b24e69c04`), is idempotent, prompts once, and appends provenance-tagged text through the same atomic path as `note`.
It has not been executed.

The leak itself is nearly closed — of the 301, only `sase-aq.4` carries a recent ID. Its history shows why:

```
14:19:04 · sase-aq.4              · issue_updated · notes     ← close --note
14:19:04 · bryanbugyi34@gmail.com · issue_closed  · resolution
14:19:43 · sase-aq.4              · issue_updated · notes
14:20:23 · bryanbugyi34@gmail.com · issue_updated · notes     ← owner-attributed overwrite
14:21:37 · sase-aq.4              · issue_updated · notes
```

A residual post-close write path still uses replacing semantics rather than appending. Worth finding, but small.

Historical note bookkeeping confirms the main fix landed: **1,451 notes still begin with `COMMIT`** — exactly the 07-25
count, frozen — while 254 notes added since then use the attributed append format. The `COMMIT:` overwrite stopped.

### N8 — Close hygiene is adopted at the default, not at the decision

Of 344 close events since 2026-07-26:

| Signal | Count | Share |
|---|---:|---:|
| Carries a resolution | 280 | 81% |
| Carries a close-time note | 157 | 46% |
| Carries a `--reason` | 92 | 27% |

Resolutions break down as **264 `done`, 16 `canceled`, 0 `superseded`**. Since `done` is the default, the 81% is mostly
the flag firing on its own. The genuinely informative signals — a verification note and an explicit reason — are at
46% and 27%.

This is fine and improving (`close --reason` more than doubled, 72 → 169). It is worth noting only because the 07-25
report treated `--reason` adoption as the proof that practice changes work. It still is; it is also still half-done.

### N9 — The ChangeSpec seam is now at literal zero, and TUI CRUD arrived against advice

`--changespec` and `--bug-id` are **0 and 0** across 2,417 beads. The four prior uses were test fixtures and were purged
with the rest. Both flags exist on `create`; neither exists on `update`, so a bead cannot be attached to a ChangeSpec
after the fact — which is exactly when you would know.

Separately, `src/sase/ace/tui/modals/bead_edit_modal.py` ships a title + description editor reachable from the Artifacts
Plans pane. Both prior reports anti-recommended TUI CRUD explicitly ("read and triage only"). The modal is narrow and
harmless in itself; the point is that the boundary moved without a decision. Either the anti-recommendation was wrong
(plausible — editing a title is not workflow) or the scope needs an explicit line before it grows.

### N10 — Destructive operations are unguarded

- `sase bead rm <id> ...` removes beads **and all their children** with no `--dry-run`, no preview, and no confirmation.
- `sase bead doctor --fix-design-refs` mutates after a confirmation prompt but performs no project-identity check.

Upstream hardened both of these surfaces in the last five days (`d1f67a91e` preserve forced-delete dry-runs;
`90c6f46f5` verify project identity before destructive `doctor --fix`). Given that `rm` is the documented cleanup path
for exactly the kind of residue in N6, a preview is cheap insurance.

### N11 — Shadow backlog: the epic tail shrank, the tale tail did not

YAML scan of 3,325 top-level plan files:

| `status:` | Count |
|---|---:|
| `done` | 2,839 |
| **`wip`** | **287** |
| none | 122 |
| `complete` (non-canonical) | 34 |
| `draft` / `handoff` / `pending` / `proposed` / `active` / others | 39 combined |

Non-`done` plans with no bead link: **279 tales, 14 epics**. The epic tail halved (30 → 14) — real progress, and the
remaining 14 are mostly stale `rust_backend_phase8_*` handoffs from 202604. The tale tail is flat and should stay that
way; beading every tale remains the wrong answer.

### N12 — Still single-project

`sase project list` shows three enabled projects with launch enabled. `sase` has 27 claims; `actstat` and `bob-cli` have
**0**, and neither has a bead store (`sdd/` does not exist in either checkout). Unchanged from 07-25. Still worth a
stated decision rather than continued drift.

## Upstream Delta (`gh:steveyegge/beads`)

Verified in the checkout at HEAD `0e069115a` (2026-07-30); **120 commits since 2026-07-25**, overwhelmingly Dolt
storage-class plumbing, proxied-server lifecycle, connection pooling, schema healing, and CI sharding. The
anti-recommendation stands with more force than ever: **do not follow this direction.**

Five small items transfer, all commit-verified:

1. `90c6f46f5` — *verify project identity before destructive `doctor --fix` operations*. Direct precedent for N10, and
   SASE shipped `--fix-design-refs` five days ago without it.
2. `d1f67a91e` — *preserve forced delete dry-runs and payload-blind previews*. The `rm` guard shape.
3. `ecb9e9273` — `bd schema`: **JSON Schema for `--json`/export output**. SASE now has JSON on four verbs with no
   published contract; this is the cheap way to make it dependable.
4. `13d2c8d6b` — *refuse overwriting a live foreign claim without `--force`*. The narrow, useful form of the CAS guard
   the 07-25 report wanted, now that SASE assigns beads to named agents at launch.
5. `920827971` — `WorkFilter.Statuses`: multi-status ready queries. Relevant only if N1 is resolved in favor of keeping
   `ready`.

## Ranked Recommendations

Ranking principle: **unblock the half that is built but forbidden, then repair the surfaces that now lie, then
instrument.** Everything in the top three is text; nothing in the top five crosses the Rust boundary.

### 1. Delete the capture prohibition and give discovered work a destination

The single highest-leverage change available, and it is a prompt edit. Every dependency shipped; only the prohibition
remains (N2).

- In `bd/work_phase_bead`, replace *"Do NOT create new beads"* with *"Do not create beads for yourself to work. Record
  discovered follow-up as a `PROPOSED FOLLOW-UP:` entry via `sase bead note <your-bead> "…"`."* The appending `note`
  command now exists, so this cannot clobber anything.
- In `bd/next`, apply the same narrowing.
- In `bd/land_epic` step 1 — which already runs `sase bead show` on every child — add: *"collect `PROPOSED FOLLOW-UP:`
  entries from child bead notes and file each as `sase bead create --tier plan …`, or record why not."*

Keep the guardrail intact: phase agents *propose*, the land agent *files*. Captured bead descriptions remain untrusted
agent content.

Success test, checkable in a week: `sase bead list --tier plan --status open` returns a non-empty set for the first time
in the store's history.

### 2. Decide what `open`, `ready`, and `#bd/next` mean after preassignment

N1 is a design decision that has been made accidentally. Make it deliberately. Two coherent options:

- **Retire the queue.** Drop `#bd/next` from `default_config.yml` and `docs/xprompt.md:943`, and make `sase bead ready`
  say so — *"no standing queue; epic work is preassigned at launch"* — rather than "all blocked or none open," which
  reads as a transient condition.
- **Rebuild the queue on the backlog.** Make `ready` mean *"`--tier plan` beads with no unresolved blockers"* — i.e.
  the standing backlog recommendation #1 will start filling — and exclude beads inside their launch window. Then
  `#bd/next` becomes meaningful again and `ready --type`/`--tier` filters (07-25 R5) become worth building.

Option 2 is the better end state and composes with #1, but it is only worth building *after* #1 demonstrates that
follow-ups actually get filed. Option 1 is correct and free today. Recommendation: ship option 1 now, revisit option 2
once the backlog is non-empty.

Either way, add the launch-window exclusion: a bead assigned to a named agent should never surface as available work.

### 3. Rewrite `sase bead onboard`, and close the last gaps in the skill

`onboard` is now actively wrong about where the store lives (N4) — that is a correctness bug in documentation, not a
polish item. Fix the source-of-truth paragraph, replace retired `sdd/plans/` examples, and add `history`, `note`,
`pages`, `close --resolution`, `work --dry-run/--json`, and the `--tier plan` backlog loop.

Then close the four remaining skill gaps (`src/sase/xprompts/skills/sase_beads.md`, regenerate per
`memory/generated_skills.md` — do not hand-edit provider copies):

- **`%wait(bead=<id>)` and `%id(<name>, bead=<id>)`** — still 0 mentions, still the two directives that make individual
  beads workable outside `sase bead work`. Also add them to `sase/memory/xprompts.md`, which today contains **zero**
  occurrences of the word "bead."
- **`sase bead pages url <id>`** — 0 mentions of a feature that produces the links now embedded in every commit trailer
  (N3).
- **The `--tier plan` backlog loop**, as a worked example, not a flag reference: capture → `list --tier plan --status
  open` → `dep add` → `update --tier epic` → `work`.
- **`onboard` itself**, so an agent knows to run it.

Add the contract test the 07-25 report proposed (documented verbs vs. the argparse surface); the skill drifted from 7/18
to ~17/21 verbs with nothing preventing regression.

### 4. Recover the 301 lost note revisions, and find the residual overwrite path

One confirmed command for the recovery half (N7):

```bash
sase bead history --lost-notes --restore
```

Idempotent, atomic, prompts once. 301 beads regain verification and handoff text that is currently invisible in every
surface — including the 2,419 published pages.

Then find the post-close writer that still replaces rather than appends (visible in `sase-aq.4` at
2026-07-29T14:20:23Z, owner-attributed). Small, and it is the last thing standing between the note field and being
genuinely append-only.

### 5. Finish `doctor`, then schedule it

`doctor` went from useless to useful; make it complete (N6), in detection-first order:

- Catch the **11 broken design refs it currently misses**, including the two live-regression cases (`sase-64`,
  `sase-ap`) where a well-formed `plans:` reference points at a deleted plan file.
- Check the **reverse direction**: 59 plan files carry a `bead_id:` absent from the store.
- Report **closed beads whose plan file is still `wip`**, and **`wip` epic plans older than N days with no bead** (14
  today).
- Add a **project-identity check before `--fix-design-refs` mutates** (upstream `90c6f46f5`).
- Stop leading every run with `WARNING: beads.db missing`, which trains readers to skip the output.
- Add a **projection/stream size early warning** — growth is now ~81 beads/day, up 65%.

Then run it as a chop. `bead_claim_checks` and `bead_store_refresh` already exist; a `bead_doctor_checks` chop turns
every one-time cleanup in this report into a standing regression guard. While there, `sase bead rm sase-8q sase-8s` to
clear the permanent pytest residue.

### 6. Attribute bead events to the acting agent

N5. Attribution is at 13–27% and only since 07-27; everything else says "bryanbugyi34@gmail.com". This is the
prerequisite for #7, and it also makes `history` far more useful today — the whole point of a timeline is knowing who
did what.

The infrastructure clearly exists (`sase-a1.land`, `sase-a1.6`, `sase-b4.land` appear as actors). This is about making
it the default path rather than the exception.

### 7. `sase bead stats --flow`

The highest-ceiling item, unchanged from 07-25 R11, now with better inputs — 10,729 events across 418 streams, and the
numbers in this report's Snapshot section were all computed from them with ~40 lines of Python. Ship: queue wait,
execution time, blocked time, lead time percentiles, reopen/retry rate, forced-closure count, WIP age, throughput, and
— once #6 lands — **phase duration and outcome by `--size` and by model**.

That last one is the payoff: it is the only way to empirically calibrate the five-size ladder, which is currently
guessed (1,896 of 2,417 beads carry no size at all; `xsmall` = 1, `xlarge` = 0).

### 8. Guard the destructive operations

N10, with fresh upstream precedent. `sase bead rm --dry-run` plus a confirmation when the removal set includes children;
project-identity verification on `doctor --fix-design-refs` (folded into #5). Small, and `rm` is the documented cleanup
path for exactly the residue this report identifies.

### 9. Complete the machine surface

`ready`, `blocked`, and `stats` still have no JSON (N-scorecard R8). Add it, then publish a schema for the JSON envelope
(upstream `ecb9e9273` is the model) and document an exit-code contract so a chop can branch without parsing prose. This
is a prerequisite for #5's chop and for anything scripting the backlog #1 creates.

### 10. Exercise the seams that have never been used

Practice, not product (N9, N12). Each is a designed integration with zero usage data, which is evidence of an untried
design rather than a bad one:

- **`--changespec` / `--bug-id`: 0 uses in 2,417 beads.** Try it on the next PR-backed epic. Also add both flags to
  `update` — you almost never know the ChangeSpec at `create` time, which may be the whole reason for the zero.
- **`xsmall` (1) and `xlarge` (0).** Both ends of the cost curve unexercised while 1,896 beads carry no size at all.
- **`actstat` / `bob-cli`.** Decide out loud whether either should run `sase bead init`, rather than letting
  single-project usage persist by drift.

### 11. Draw the line on TUI write access

N9. `BeadEditModal` edits titles and descriptions from the ACE Plans pane, against two prior reports' explicit
anti-recommendation. Either amend the guidance (defensible — metadata editing is not workflow) or state the boundary
before it grows into status transitions and closes. The concern was always that a second control plane emerges beside
`sase bead work`; a title editor is not that, but nothing currently prevents the next modal from being.

## Anti-Recommendations (reaffirmed)

- **No Dolt, daemons, leases, replicas, proxied servers, or federation.** 120 upstream commits in five days went almost
  entirely there. SASE's event-sourced store already solves what that machinery manages, and now does so across a
  dedicated sidecar with generated pages — further ahead than upstream's original design, not behind it.
- **No molecules, formulas, wisps, gates, or agent mail.**
- **No priority levels or label taxonomy.** Still no query the dependency graph and `search` cannot answer. Revisit only
  if recommendation #1 produces a backlog large enough to need triage — which would be a good problem.
- **No beading of tales.** 279 tale plans without beads is policy, not debt.
- **No new link types speculatively.** `discovered-from` never got built and, with `--tier plan` plus a
  `PROPOSED FOLLOW-UP:` note convention, may not need to be. Revisit after #1 has run for a few weeks.
- **No retention/compaction yet** — but the early warning in #5 matters more now: 2,417 beads and 10,729 events at
  ~81 beads/day is 65% faster growth than a week ago.

## Use Beads Better Starting Today

Zero feature work required:

1. **Run `sase bead history --lost-notes --restore` once.** 301 beads, one confirmation.
2. **File follow-ups as `--tier plan` beads by hand** until #1 lands, starting with the 14 orphaned `wip` epic plans.
3. **Use `sase bead pages url <id>`** when referencing a bead outside the terminal — PRs, notifications, other projects.
4. **Pass `--note` on every close.** At 46%, over half of completions record no evidence, and the ACE pane and published
   pages both render notes.
5. **Reserve `--resolution canceled|superseded` deliberately.** 0 `superseded` in 2,417 beads is implausible given how
   often plans get re-planned as `_1`/`_v2`.
6. **`sase bead work <plan> --dry-run` before every fan-in epic** — still the cheapest correctness check available.
7. **`sase bead history <id> --format full`** when picking up someone else's work; it now reveals the revision chain
   that `show` flattens.

## Sources

- **Live store, 2026-07-30 ~15:00 EDT.** `sase bead stats|ready|list|blocked|show|doctor|onboard|history|pages|--help`;
  direct analysis of `sase/repos/beads/issues.jsonl` (2,417 records) and `sase/repos/beads/events/streams/*.jsonl`
  (418 files, 10,729 events).
- **Plan sidecar scan.** YAML parse of 3,325 top-level plan files across `202602`–`202607` (`status`, `tier`,
  `bead_id`), cross-referenced against the store in both directions.
- **Source.** `src/sase/bead/` (`cli_location.py`, `workspace.py`, `claims.py`), `src/sase/main/parser_bead.py`,
  `src/sase/core/state_write_guard.py`, `src/sase/default_config.yml` (`bd/*` xprompts at 868–941, chops at 588–603),
  `src/sase/xprompts/skills/sase_beads.md`, `src/sase/ace/tui/modals/bead_edit_modal.py`,
  `src/sase/ace/tui/widgets/artifacts/plans_detail.py`.
- **Git history.** 438 commits on `master` since 2026-07-25; ~70 bead-related, cited individually above.
- **Docs.** `docs/beads.md` (764 lines, incl. a new "Bead Pages" section), `docs/xprompt.md`,
  `docs/troubleshooting/runner-slots.md`, `sase/memory/xprompts.md`, `sase/memory/generated_skills.md`.
- **Upstream.** `gh:steveyegge/beads` at HEAD `0e069115a` (2026-07-30), opened via `sase repo open`; verified commits
  `90c6f46f5`, `d1f67a91e`, `ecb9e9273`, `13d2c8d6b`, `920827971`.
- **Prior research.** `202607/sase_beads_leverage_20260725/` (2026-07-25),
  `202607/sase_beads_full_potential_consolidated/` (2026-07-14), `202603/sase_beads.md`,
  `202605/axe_open_bead_tree.md`.
- **Project inventory.** `sase project list`, `sase repo list`.
