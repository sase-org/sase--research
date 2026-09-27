# Why Goals aren't beads

_Research note · 2026-09-27 · project: sase_

**Question.** The [SASE Goals design](sase_goals_design/sase_goals_design.md) adds a new
`goal:` object with its own lifecycle, ledger, CLI, and tab. Beads already have a
lifecycle, git sync, evidence, a CLI, and TUI surfaces. Why not make a goal a kind of
bead?

**Sources.** The lead synthesis, all five design reports
([cdx](sase_goals_design/sase_goals_design__cdx.md),
[cld](sase_goals_design/sase_goals_design__cld.md),
[grk](sase_goals_design/sase_goals_design__grk.md),
[mus](sase_goals_design/sase_goals_design__mus.md),
[gem](sase_goals_design/sase_goals_design__gem.md)), the prior
[outcomes synthesis](goal_outcomes_and_verification/goal_outcomes_and_verification.md),
and the one report that argued _for_ bead-backed goals
([prior mus](goal_outcomes_and_verification/goal_outcomes_and_verification__mus.md)). I
checked the load-bearing facts against `sase-core` @ `f1ddeb5` and a live
`sase bead stats` run today.

---

## Bottom line

> **Reuse the beads _repository_. Don't reuse the beads _model_.**

A bead is **scheduled work**: something someone should do, sized, triaged, and closed
by the agent that does it. A goal is **verified intent**: something you want to be true,
claimed by an agent and settled by you. Turning goals into beads would give them the
wrong states, the wrong authority, the wrong read cost, and the wrong audience. The
design keeps everything about beads that is _infrastructure_ (repo, hidden clone, sync,
event-sourcing, fast path) and links goals to beads rather than subtyping one as the
other.

Every report in the design round kept goals separate from beads: cdx, cld, grk, and mus
rejected the idea explicitly, and gem treated beads as one input to a goal. Only the
earlier mus report proposed `task_type: goal`, and the prior synthesis rejected it.

---

## 1. The steelman: what beads would give you for free

The case for beads is real, and it is the case the prior mus report made:

| Beads already have… | So a goal bead would get… |
| --- | --- |
| An event-sourced store in a synced sidecar repo | Cross-machine visibility with no new transport |
| Lifecycle, resolutions (`done` / `canceled` / `superseded`) | A state machine for free |
| Append-only notes, `+1` evidence, artifact refs | An evidence trail |
| `sase bead` CLI, TUI bead touches and hint targets | Surfaces without a new tab |
| The `bead_action: close\|keep` finalizer contract | A ready-made "claim or keep open" decision |
| Precedent for new record kinds (`task_type`, flag beads) | A cheap extension point |

The biggest point in its favor: **no second work-item system.** Every future feature
wouldn't have to ask "bead or goal?"

---

## 2. Why it doesn't fit

### 2.1 Different nouns, different layers

Goals sit _above_ beads and cut across them. Some goals have no bead at all.

```text
 INTENT      ⌖ goal     "Tailnet dispatch mesh works on every machine"     ⌖ "Answer: which env var…"
                │ defines                                                     │
 DESIGN      ▤ plan                                                           │
                │                                                             │
 WORK        ◇ epic bead ── phase beads ── land bead                          │  (no bead)
                │                                                             │
 EXECUTION   ● planner · phase agents · lander                                ● one agent
```

About **310 distinct outcomes a week** run through SASE, and roughly **25 a day are
ad-hoc requests, most of them questions**. None of those answers is work anyone should
schedule. The synthesis puts it plainly: _Agents shows processes. Beads shows scheduled
work. Plans shows designs. Goals would show intent._ If goals were beads, the one view meant to show
scheduled work would also have to show intent.

### 2.2 The lifecycles don't line up

| | **Bead** | **Goal** |
| --- | --- | --- |
| Born | `sase bead create` or plan approval; shared at once | The host, at launch, as a **machine-local draft** |
| States | `open · claimed · ready · snoozed · in_progress · closed` | `draft · active · review · done · dropped` |
| The human gate | `ready` → **TaskTriage**: _should we do this?_ (before work) | `review` → **GoalVerify**: _did it happen?_ (after work) |
| "Done" means | An agent ran `sase bead close` | **You** pressed Verify, or opened an answer |
| Hierarchy | plan → phase; close never cascades, so children close first | Flat; spans beads, agents, plans, and bead-less answers |
| Required up front | reason; for tasks, `--size` and an immutable `task_type` | Nothing. The agent names it after launch. |

Three mismatches stand out:

- **No `review` state.** "Claimed, waiting on a human" is the heart of Goals, and beads
  have nothing like it.
- **A word collision.** A bead's `claimed` means _the runner reserved it_. A goal's
  _claim_ means _an agent says it's done_. Same word, opposite end of the lifecycle.
- **Drafts can't be shared yet.** A goal stays local until it's named, and an adopted
  draft never publishes at all. A bead is shared the moment it exists.

### 2.3 Authority is inverted

With beads, **agents close their own work**: a phase worker's bead, a land agent's
epic. With goals, **agents may only claim**. `verify`, `reject`, `drop`, `reopen`, and
`merge` are human-only verbs, and they are refused inside agent runs. To make goal beads
work, the bead mutation layer would need a per-type exception to its own authority
model, in the reducer that every bead operation depends on.

### 2.4 The read path scales with history, not with the inbox

The Goals inbox must cost **O(unsettled)**. Bead reads cost **O(everything ever
filed)**:

- `list_issues`, `show_issue`, `ready_issues`, and `stats` all call `read_store_issues`,
  which reduces **every** event stream and only then filters
  (`sase-core` `crates/sase_core/src/bead/read.rs:66-86`, `:159-171`).
- Today's store holds **6,479 beads, of which 6,015 (93%) are closed.**
- At ~310 outcomes a week, **one year of goals is ~16,000 records: about 2.5× everything
  the bead store has accumulated so far.** Every `sase bead list` would pay for them.

The goal ledger avoids this by design: a `live/` marker per unsettled goal, immutable
event files, and settled goals that are never opened. You could bolt an
unsettled-only index onto beads, but then you'd be building goal-specific storage
anyway, inside a shared store.

### 2.5 The work queue would fill up with things that aren't work

A task bead brings rituals that make sense for work and are noise for intent:

- `/sase_new_task` duplicate checks, a mandatory `--size`, and an immutable `task_type`;
- a **TaskTriage** gate each time one becomes `ready`;
- a place in `sase bead ready`, `list`, and `stats`, which every consumer would now have
  to filter.

Twenty-five answered questions a day would bury the ~260 ready tasks that really do
need triage. The feature exists to _reduce_ what you have to look at, not move the
noise to another tab.

### 2.6 Boundary and blast radius

Bead domain logic lives in `sase-core` (`rust-core-required`), so a goal subtype would
be a change to the core bead reducer, its wire, and every binding that reads it. A
Python-only "goal bead" shortcut would break the Rust boundary. Either way, a
goal-specific bug becomes a bead-store bug, and the bead store is what schedules all
other work.

---

## 3. What the design _does_ take from beads

Rejecting the model isn't rejecting the prior art. The design copies nearly every
mechanism that makes beads work:

| From beads | In Goals |
| --- | --- |
| The beads sidecar repo | A `goals/` directory **co-hosted in the beads repo**, split out only if contention is measured |
| Hidden host clone + `sidecar_auto_sync` | Same write lane, same sync tick |
| Event-sourced canonical state | Immutable events, but no in-place edits at all, so rebases never conflict |
| `bead_fast_path` | A Rust fast path for `sase goal list` |
| `bead_action: close\|keep` | `builtin@goal`: `claim\|keep_open` via `decide_goal_action` |
| "Agents never hand-edit bead status" | Status verbs are human-only |

And goals **link** to beads instead of absorbing them:

- `sase bead work` on a bead linked to one unsettled goal binds the agent to that goal.
- Epic phase and land agents resolve **epic bead → plan → `goal_id`**, so a whole epic
  is one goal with one claim, made by the land agent.

---

## 4. The cost of this choice

This decision isn't free. It buys:

- **A second lifecycle and reducer** in `sase-core`, with its own tests and doctor.
- **A second CLI noun** (`sase goal`) and **a new top-level tab**.
- **A permanent "bead or goal?" question** for future features. The answer is: _if you
  would schedule it, it's a bead; if you would verify it, it's a goal._

## 5. What would reopen it

Revisit bead-backed goals if the rollout metrics show that:

1. **Most goals map 1:1 to epics**, and answer-only or ad-hoc goals are rare. Then a
   goal is just an epic with a `review` state, and extending beads is cheaper.
2. **The bead store gains an unsettled-only hot read path** for its own reasons. That
   removes §2.4, though §2.1–§2.3 still stand.
