---
create_time: 2026-10-15
updated_time: 2026-10-15
status: draft
tags:
  [
    research_swarm,
    tui,
    agent-clans,
    waves,
    agents-tab,
    epic,
    jump-panel,
    research-swarm,
  ]
---

# Agent-clan waves on the Agents tab

**Question.** Should SASE show dependency waves on every agent clan — epic,
research, and custom — in a way that is intuitive, reliable, and beautiful?
Today the Agents tab does not. Critique the request. Adjust requirements that
would make the feature noisy or surprising. Recommend a design.

**Researcher.** grk (`research.4j.grk`). Independent report. I did not locate,
open, read, or otherwise consult peer reports from this swarm.

**Evidence.** Live Agents-tab screenshot
`~/tmp/screenshots/20261015_124557.png` (epic clan `bob-cli-7v`, 8 members,
`Counts: 7 phases · 5 waves`); TUI clan/JUMP/roster code; Kahn layering in
`sase/sdd/plan_waves.py` and Rust `bead_build_epic_work_plan`;
`#research_swarm` wait graph in `sase-research-artifacts`.

## Bottom line

**Yes, build this — as a derived schedule view, not as a new clan kind.**

Waves already exist wherever clan members wait on each other. Epic bead-work
computes them up front as Kahn layers of `depends_on`. Research swarms and any
`%w` clan compute the same shape at runtime. The Agents tab currently shows
the *count* for epics (`7 phases · 5 waves`) and then throws the mapping away:
the tree sorts by status, the JUMP bar is a flat launch-order chip strip, and
the Summary lists phases in authored order with `after …` footnotes. A human
cannot see which members are allowed to run now.

**Do not invent `%wave`, wave nodes, or a second member sort.** The schedule is
already authored by `%wait` / epic `depends_on`. The missing product is a map
of that DAG onto chrome the Agents tab already has: the clan row, the sticky
JUMP legend, and a two-cell member chip.

Recommended v1, in priority order:

1. A pure in-memory wave layering helper that every clan can run.
2. A **wave timeline JUMP legend** for multi-wave clans (the beauty surface).
3. A compact `wK/N` chip on the clan row, plus a header strip when the clan is
   selected.
4. A dim `wN` chip on each direct member row, with the tree **kept** in
   status-priority order.

Hide all of that chrome when the clan has a single wave. Treat epic `.land` as
a **seal lane** after the numbered waves so the existing `5 waves` count stays
honest. Number JUMP targets in launch order, as today.

## Verdict on the idea

This is a good idea. I would build it with the adjustments below, rather than
a new directive, nested wave containers, or regrouping the agent tree.

### Why it is worth doing

The screenshot is the bug report. `bob-cli-7v` is an 8-agent epic clan whose
Summary already knows `5 waves`. The tree shows:

```
bob-cli-7v (RUNNING) [R2 W5 D1]
  .3      RUNNING
  .land   RUNNING
  .6 .7 .5 .4   WAITING
  .1      DONE
```

The JUMP bar shows `1 2 3> 4 5 6 7 .land` in launch order. Wave membership is
nowhere. Phase 3 is selected and in-flight; phases 4–7 are parked on
dependencies; `.land` is a separate runner. A reader has to reconstruct Kahn
layers from the Summary's `after dedupe, naming` lines. That is the opposite
of a map.

The same hole is worse for non-epic clans, because they do not even get the
count. `#research_swarm` with image, audio, and linker is a four-wave DAG:

```text
w1  cdx cld grk mus gem     (parallel researchers)
w2  final                   (waits on every researcher)
w3  image audio             (both wait on final; parallel)
w4  linker                  (waits on final, image, and audio)
```

Launch order is `cdx, cld, grk, mus, gem, final, image, linker, audio`. The
linker is launched *before* audio and waits *on* audio, so today's JUMP bar
puts the last wave in the middle of the third. That is the research-clan
version of the screenshot: the schedule exists, the chrome lies.

Custom clans already express the same DAG with `%w`. Supporting waves "for
agent clans in general" means **reading that DAG**, not adding a parallel
authoring system.

### Why the request as written is too broad

"Show the waves that exist in every agent clan" is right as a *capability*
and wrong as a *always-on visual*. Most user-defined clans are one parallel
wave. Drawing `WAVE 1` around five independent members is a TOC with one
heading. It also invites the wrong reading: people will think SASE has
invented a new grouping, or that queue admission is a wave.

A second overreach: treating waves as something the tree should *become*.
Direct clan members sort by status priority — Failed, Stopped, Running,
Queued, Waiting, Done — in every grouping mode (`docs/ace.md`). That is the
operational view: what needs a human. Wave order is the *schedule* view. The
JUMP panel is already the schedule-shaped roster (launch order, stable
numbers). Put the new map there. Keep the tree honest about fire.

## Requirement adjustments

Call these out as changes to the request, not as implementation details.

### A1. Waves are derived, never authored

**Change:** do not add `%wave`, `wave=` on `%clan`, or a persisted wave index
on the member.

The schedule is `%wait` / epic `depends_on`. A second authoring channel will
desync the first time someone presses `W` in the TUI or edits a wait. Wave
index is a projection of the live intra-clan wait graph (epic: of the loaded
plan). Recompute it in memory. Do not write it down.

### A2. Hide chrome when `wave_count < 2`

**Change:** "every clan" means every clan *can* show waves. Single-wave clans
keep today's look.

Compute waves always. Render the timeline, `wK/N` chip, member chips, and
roster group headers only when two or more waves (or a land seal plus at
least one phase wave) exist. A solo-lead research swarm and a four-member
parallel review clan stay visually quiet.

### A3. Do not make waves into sase nodes

**Change:** waves are grouping chrome, never nav items, fold targets, kill
targets, mark targets, or JUMP numbers.

A wave is not an agent clan, an agent session, or a workflow step. Introducing
wave rows into the Agents tree would steal `j`/`k` stops, confuse `x`/`d`/`N`,
and fight the glossary definition of a sase node. Group labels in the expanded
JUMP roster already exist for neighbor hoods (`MemberRosterEntry.group_label`);
reuse that pattern.

### A4. Keep JUMP numbers in launch order

**Change:** visual clusters follow wave order; the digit on a chip stays the
launch-order number documented today.

`docs/ace.md` promises clan JUMP numbers do not move when statuses change.
Renumbering by wave would also reshuffle when a wait is added or a late member
joins wave 1. Stable identity-tied numbers plus a timeline that may show
`4 1 7 │ 2 5 │ 3` is how labeled jumps work. For epics the happy case is
already monotonic (`1 2 3 │ 4 │ 5 │ 6 │ 7 │ ⚑.land`) because bead-work
launches phases in authored id order.

### A5. Epic `.land` is a seal lane, not wave N+1

**Change:** numbered waves on an epic clan are the plan's Kahn layers. `.land`
renders as a trailing **seal** cluster, so `Counts: 7 phases · 5 waves` and the
JUMP map agree.

`plan_phase_waves` and `EpicWorkPlan.waves` both exclude the land agent. Land
waits on every phase, so a naive wait-graph reconstruction would report six
waves for a five-wave epic. That would make the Summary look wrong the moment
the JUMP bar grew a `w6`. Give land a distinct `⚑` (or `.land`) cluster after
the numbered waves. Do not special-case research `.final` or `.linker` the
same way: those are ordinary members of the wait DAG, and research clans have
no competing "N waves" count.

### A6. Intra-clan waits layer; external waits do not

**Change:** generalize Kahn layering, but **do not** copy `plan_phase_waves`'
fail-closed rule for unknown ids.

`plan_phase_waves` returns `None` when a phase depends on an id outside the
set. Clan members routinely wait on extra-clan agents (`#research_swarm`'s
optional `wait=`), beads, hoods, time, and `%wait(for_epic=)` follows. Those
blockers explain why a row is `WAITING`; they must not destroy the clan's
wave map. Treat a wait on a name that is not a current direct clan member as
**external**: ignored for layering, still shown on the row's wait chip.

A cycle among clan members *does* make waves unavailable. Then show today's
flat legend plus a dim `waves unavailable` hint on the header, matching the
plan display's `waves unavailable` empty state.

### A7. Queue admission is not a wave

**Change:** document, in chrome copy and in the glossary, that a wave is a
dependency layer.

`docs/beads.md` already separates Kahn order from capacity: members of the
same wave may sit `QUEUED` behind `%q` while siblings run. The screenshot's
purple `WAITING` rows are dependency waits; blue `QUEUED` is a runner slot.
The timeline groups the former. Never draw a "wave" for `%queue` rank.

### A8. Do not regroup the Agents tree by wave in v1

**Change:** member rows stay status-sorted. Add a `wN` chip. Leave a
clan-local "sort by wave" toggle for a later iteration if the chips are not
enough.

Regrouping would hide a failed member under `w2` while the user is hunting
red rows. It would also fight `_sort_clan_member_units` and every test that
pins Failed → … → Done order. The collapsed *clan* row is the right tree
surface (A9).

### A9. The collapsed clan row is in scope

**Change:** the request said "agent clans on the Agents tab." Include the
collapsed container row, not only the expanded member list and JUMP bar.

A done research clan in the screenshot (`research.4i`) is a single line. That
is where a `w2/2` (or nothing, per A2) earns its keep. The expanded member
list is the ops view; the container chip is the at-a-glance view.

## Current state (what the screenshot actually shows)

Three independent orderings already exist for one clan. None is wave order.

| Surface | Order today | Wave signal |
| --- | --- | --- |
| Agents tree (direct members) | Status priority, then launch recency | None |
| JUMP `CLAN MEMBERS` | Chronological launch order; stable digits | None (flat chips `1…7 .land`) |
| Summary phase list | Authored phase id | Count only (`5 waves`); each phase has `after …` |
| Clan header | Member counts, runtime, tribes | None |
| Collapsed clan row | Status + `[R W D]` chip | None |

Other relevant facts:

- JUMP digits are an agent-relation jump target (`glossary:agent-relation-jump-target`).
  Caps at 100. In-flight chips already light with a tinted pill and `▶`/`◐`.
  The collapsed legend packs at most two rows and prefers in-flight when it
  overflows (`_collapsed_selection` in `_agent_jump_legend.py`).
- Expanded roster group headers already exist (`group_label`, used for
  neighbor hoods). Clan members pass `group_label=None`.
- Epic counts are produced by `plan_phase_waves` in the clan-summary script
  and in plan display (`Counts:` / gate `plan_wave_count`). The TUI does not
  keep the layered tuples, only the printed summary text.
- Epic launch itself uses a *different* Kahn pass in Rust
  (`bead_build_epic_work_plan`): open phases only, land aside, dual
  `%w(agent)` + `%w(bead=)` waits. That is the execution schedule. The
  authored-plan pass is the display schedule and includes already-closed
  phases, which is what a human wants on a live clan that has started to
  finish.
- Research tribe color is `#5FD7AF` (`∴`). Epic tribe is `#AF87FF` (`▲`).
  Clan identity chrome is orchid (`#D75FFF` / `#D75FFF`-family). Status
  already owns the rainbow. Wave chrome must not add a second rainbow.

## Domain: one algorithm, two overlays

### Shared kernel

Generalize `plan_phase_waves` into a name-agnostic helper:

```text
layer_dependency_waves(
    ids: ordered identifiers,          # launch order for stability
    deps: id -> set[id],               # only intra-set edges
) -> tuple[tuple[id, ...], ...] | None
```

Wave *k* is every remaining id whose intra-set deps are all in earlier
waves. Relative order inside a wave follows `ids` (launch / authored order).
Return `None` on a cycle. This is the same Kahn loop that already has tests
in `tests/sdd/test_plan_waves.py`.

Put it next to `sase/sdd/plan_waves.py` (or a tiny `sase/schedule/waves.py`
that both SDD and agent code import). **Do not put it in sase-core for v1.**
The rust-core litmus test is "would a CLI or editor need the same answer."
`sase agent list` does not show clan waves today. Epic *execution* waves
already live in Rust for `sase bead work`. This projection is presentation
plus any future `sase agent clan waves` printer; keep it a pure Python
function until a second process needs a byte-stable wire. TUI render paths
must stay in-memory (`tui_perf.md` rule 8): the helper consumes
`waiting_for` already hydrated on `Agent`.

### Overlay: generic clan (research, custom, chop, …)

For each direct clan member *M*:

- Intra-set deps = names in `M.waiting_for` that resolve to another **direct**
  member of this clan generation (full name or hood-relative suffix).
- Ignore `waiting_for_beads`, `waiting_for_hoods`, time waits, tribe waits,
  `%wait(for_epic=)` follows, and any agent name that is not a direct member.
- Nested sequential sessions are one member: the session row's waits, not
  its `--<suffix>` turns.
- Members with empty wait metadata layer as roots (wave 1) until hydration
  lands; the JUMP *numbers* do not move, only cluster membership might.

Worked research example (`#research_swarm` with all optionals):

| Member | Intra-clan waits | Wave |
| --- | --- | --- |
| `.cdx` `.cld` `.grk` `.mus` `.gem` | (none; optional `wait=` is external) | 1 |
| `.final` | all researchers | 2 |
| `.image` `.audio` | `.final` | 3 |
| `.linker` | `.final`, `.image`, `.audio` | 4 |

Default three-agent swarm is two waves (researchers, then `.final`). Chrome
appears. A lead-only dispatch is one wave. Chrome stays off.

### Overlay: epic clan

When the selected clan can resolve an authored plan (the same snapshot the
Summary already used) or a bead-work plan with phase assignments:

1. Run `plan_phase_waves` on the plan phases (stable, includes closed phases).
2. Map phase id `N` → member `<clan>.<N>` (existing bead-work naming).
3. Assign those members to numbered waves 1…W.
4. Place `<clan>.land` in the **seal** lane, never in wave W+1.
5. Any extra direct member (manual join, unexpected suffix) falls through to
   the generic overlay and is appended after the seal if it depends on
   everyone, or into the matching numbered wave if it only depends on a
   subset.

If the plan is missing, fall back to the generic overlay and **do not** print
a wave count that disagrees with the Summary. Prefer a dim `waves from waits`
hint over a lying `6 waves`.

Do not call `bead_build_epic_work_plan` from the TUI. It is a sqlite/Rust
launch planner, status-blind on open phases, and it would violate the
event-loop rules.

### Live vs launch-time

Waits can change after launch (`W` from the TUI, retry prompts). For generic
clans the projection is live: adding a wait can move a member to a later
wave. That is correct. For epic clans the numbered waves stay on the plan so
the Summary count and the JUMP clusters cannot drift; extra waits show up as
ordinary wait chips *inside* the planned wave.

A wave is **complete** when every member in it is `Done` (dismissed counts as
absent, not complete). A wave is **active** when any member is Running,
Starting, Queued, Waiting, or Failed. The **frontier** is the lowest-index
active wave. Failed members keep their wave open: dependents are still
parked, and the map should say so.

## Visual design

Status already uses the rainbow. Wave chrome uses **one accent, three
luminances**:

| State | Treatment |
| --- | --- |
| Complete wave | dim, same hue as the clan/tribe identity |
| Frontier / selected wave | full clan orchid (epic `#AF87FF`, research `#5FD7AF`, else clan `#D75FFF`) |
| Future wave | muted orchid, no gold |
| Seal (`.land`) | gold-dim `⚑`, matching the in-flight tint language already used for `▶` |

No per-wave hue. Five rainbow stripes next to Failed/Running/Waiting would be
unreadable and would fight tribe colors.

Display is **1-based** (`w1`…`w5`). Internally the helper can stay 0-based
like `PhaseAssignment.wave`.

### Hero: JUMP legend becomes a wave timeline

Today (from the screenshot, collapsed):

```text
JUMP · CLAN MEMBERS 1–8
  1 1   2 2   3 3▶   4 4   5 5   6 6   7 7   .land
```

Proposed, same epic, same digits, clustered by wave, land as seal:

```text
JUMP · WAVES 1–5 · SEAL · CLAN MEMBERS 1–8
  ①  1  2  3▶     ②  4     ③  5     ④  6  7     ⚑  .land
```

Each circled index is a **header cell**, not a jump target. Digits inside a
cluster are the existing launch-order numbers. The selected member keeps
today's `▶` / `❯` cursor on its chip (`3▶` above). In-flight lighting stays
per-chip.

When width is tight, collapse non-frontier clusters to a count and keep
in-flight chips expanded:

```text
JUMP · WAVES 1–5 · SEAL
  ①×2  ① 3▶     ②×1     ③×1     ④×2     ⚑ .land
```

Better: collapse only *complete* waves, always expand the frontier and any
other in-flight chip:

```text
  ①×1  ① 3▶     ② 4     ③ 5     ④ 6 7     ⚑ .land
```

(assuming `.1` done in w1, `.2` also done and folded into `①×1` or shown if
space remains). Prefer showing the selected member even if its wave is
complete.

This replaces the two-row packed grid **only when `wave_count >= 2`**.
Single-wave clans, session `SESSION TURNS`, and `NEIGHBORS` keep the current
`JumpLegendRenderable` packer. Implementation-wise, give the legend a
`clusters: tuple[WaveCluster, ...]` optional field; empty clusters mean
today's grid.

Title: `JUMP · WAVES 1–5 · CLAN MEMBERS 1–8`. Keep `CLAN MEMBERS` as the
section name so the glossary (jump targets are members) stays true. `WAVES`
is a qualifier, not a new roster.

`.` expanded roster: same digits, wave-then-launch display order, using the
existing dim group header:

```text
▸ ❖ CLAN MEMBERS · 8
  w1 · 3 members · frontier
  1  .1    agent  DONE     …
  2  .2    agent  DONE     …
  3  .3    agent  RUNNING  …
  w2 · 1 member · waiting
  4  .4    agent  WAITING  …
  …
  seal · land
  8  .land agent  RUNNING  …
```

`CLAN NEIGHBORS` still follows on the same number ladder, unclustered.

### Clan row chip

On the container, after the status count chip, before the orchid name:

```text
bob-cli (RUNNING) [R2 W5 D1] w3/5  bob-cli-7v
∴ research.4i (DONE) [D7] w2/2     research.4i
```

`wK/N` uses the frontier index *K* and the numbered-wave count *N* (seal
excluded for epics). Dim when the clan is all done (`w5/5`). Omit when
`N < 2` and there is no seal. This is the collapsed-clan tell and the
highest-leverage tree change: it does not reorder anyone.

### Member row chip

Two cells, after the tree guide, before the status parenthetical or
immediately after the hood suffix — pick one place and keep it for every
direct member:

```text
  w3  bob-cli (RUNNING)  bob-cli-7v.3     12m54s
  ⚑   bob-cli (RUNNING)  bob-cli-7v.land     22s
  w4  bob-cli (WAITING)  bob-cli-7v.6
```

Dim `wN` for complete waves; frontier `wN` in the clan accent. Do not draw a
contiguous rail down the gutter: status sort scatters a wave, so a rail would
be broken ticks and look like a bug.

### Header strip (selected clan)

Under `Members:` in the sticky CLAN header, only when chrome is on:

```text
Waves:  ①● ②● ③▶ ④○ ⑤○  ⚑
        3 done · frontier w3 · 2 running in w3+seal
```

Same widget as the JUMP timeline, smaller, no digit chips. This is the
"beautiful" glance when JUMP is narrowed or the user is reading the Summary.
Reuse, do not invent a third encoding.

### Summary card (epic only, v1.1)

Grouping the Summary's phase list by wave would make `5 waves` inspectable.
It is not required to ship the Agents-tab map. If it ships, use the same
headers (`w1 · no dependencies`, `w2 · after 1, 2`) and keep authored ordinals
on the phase titles so `#plan` copy/search still matches. Land stays out of
the phase list, as today.

## What I would not do

**Authored `%wave:2`.** Duplicates `%w`. Desyncs on retry. Teaches users to
maintain a schedule SASE can compute.

**Wave rows in the tree.** They are not sase nodes. Kill/dismiss/fold/`N`
would need a new cascade rule for a thing that is not a container.

**Regrouping members by wave as the default tree order.** Hides failures.
Breaks the documented status ladder. A later clan-local sort toggle is
enough if people ask.

**Painting every clan with a single `WAVE 1` banner.** Noise. A2.

**Calling reconstructed wait-graph layers "5 waves" on an epic that includes
land.** The Summary would disagree on day one.

**A feature-flag bead for v1.** This is presentation chrome over data the TUI
already has. A config escape hatch `ace.clan_waves: true` (default on) in
`default_config.yml` is enough if the JUMP packer needs a kill switch while
goldens settle. Follow `sase/memory/sase_flags.md` only if the old flat
legend must remain reachable as a compatibility branch after a release; I
would not bother unless the packer regresses in the wild.

**sase-core for v1.** No second consumer yet. Promote when `sase agent`
prints waves or the editor sidebar wants the same layering.

## Implementation sketch

Shared, test-first:

1. Lift `plan_phase_waves` to `layer_dependency_waves` with an
   `unknown_dep="reject"|"ignore"` switch. Plans keep `reject`. Clans pass
   `ignore` after the adapter has already dropped external names.
2. `clan_schedule(members) -> ClanSchedule` with
   `waves: tuple[tuple[Member, ...], ...] | None`, `seal: tuple[Member, ...]`,
   `source: "plan" | "waits" | "unavailable"`. Pure, O(members + edges), no
   I/O.
3. Epic adapter: if a `PlanDisplay` is already in the clan snapshot, map
   phases → members, land → seal. Else waits.
4. Generic adapter: intra-clan `waiting_for` only.

TUI, cheapest first:

5. Clan row `wK/N` + member `wN`/`⚑` chips. Incremental `patch_row`: a wait
   change on one member can reassign **sibling** wave chips, so recompute
   `ClanSchedule` for that clan and patch every direct member plus the
   container. Do not full-rebuild the Agents list (`tui_perf.md` rule 6).
6. Header strip, driven off the same `ClanSchedule` the chips use.
7. JUMP clustered legend + expanded `group_label` headers. New visual
   snapshots beside `test_ace_png_snapshots_agents_jump_panel.py` and
   `test_ace_png_snapshots_agents_clan_panel.py`. Host-independent: pin time,
   names, and waits in the fixture.
8. Overflow: complete-wave collapse-to-count, always show frontier and
   in-flight, always show the selected chip.

Glossary (memory task, not this turn): add **Clan wave** — a Kahn layer of an
agent clan's intra-clan wait graph, 1-based in the UI; epic numbered waves
follow the authored plan and exclude `.land`, which is a seal lane. Distinct
from queue admission and from an agent hood.

Config: optional `ace.clan_waves` default true. If added, update
`src/sase/default_config.yml` (keymap/config gotcha).

## Risks

- **JUMP packer.** The current two-row grid is width-sensitive and uniqueness-
  safe on truncated labels. Clustering is the one piece that can look ugly at
  80 columns. Ship the collapse-to-count rule with fixtures at 60/80/120
  cells, including a 14-member two-digit clan (the existing visual fixture).
- **Hydration flicker.** Members whose `waiting_for` lands after first paint
  can move between clusters. Digits stay put (A4), so the flicker is a chip
  sliding to another group, not a renumber. Still coalesce with the existing
  clan-enrichment pass; do not add a new refresh path (tui_perf rule 5).
- **Unknown waits (`?N`).** Names that look like members but are not in the
  generation are external. The orange `?N` chip on the clan row already
  covers stale targets; the timeline must not return `None` because of them.
- **Diamond DAGs.** JUMP digits will be non-monotonic inside the timeline.
  That is acceptable; teach it with the circled wave index, not by
  renumbering.
- **Retried epics.** Closed phases remain in their plan wave (complete). A
  relaunched phase keeps its suffix and its wave. Land stays the seal. The
  screenshot's "`.land` RUNNING while later phases WAITING" becomes a
  readable anomaly (seal in-flight, frontier still open) instead of a
  mystery.
- **Goldens.** JUMP and clan-panel PNG snapshots will move. That is expected;
  inspect every group from `just fix-tui-screenshots` before treating them as
  approved (`tui_screenshot.md`).

## Recommended solution

Ship a **derived clan-wave map** that every clan can compute and that only
multi-wave clans draw.

- **Kernel:** one Kahn helper; generic clans from intra-clan `%wait`; epic
  clans from the authored plan, with `.land` as a seal.
- **Beauty surface:** the sticky JUMP legend becomes a wave timeline of the
  existing member chips, with complete-wave collapse under width pressure.
- **Glance surface:** `wK/N` on the clan row; matching header strip when
  selected; `wN`/`⚑` on member rows.
- **Non-goals for v1:** `%wave`, wave nodes, tree regroup, sase-core, CLI
  columns, Summary regroup (nice follow-up).

That is the smallest design that makes the screenshot's `5 waves` *visible*,
makes a research swarm's linker sit in the last cluster instead of between
image and audio, and stays quiet for the boring parallel clan. It is
intuitive (the JUMP bar is already the clan map), reliable (one algorithm,
plan overlay, external waits ignored, numbers frozen), and beautiful (one
accent, a timeline, collapse-to-count — not a new rainbow and not a banner
around a single group).
