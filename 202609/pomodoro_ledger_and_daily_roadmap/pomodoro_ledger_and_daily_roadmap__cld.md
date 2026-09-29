# Daily Pomodoro Tracking in Bob: What the Data Says and What to Change

- **Researcher:** cld
- **Date:** 2026-09-29
- **Question:** Should Bryan change how he tracks pomodoros, work, time, and the roadmap for his day in the
  "Pomodoros" section of his Obsidian daily notes?

**Evidence base.** I looked at three kinds of local evidence and then checked the outside claims:

- **Notes and templates.** Today's note (`~/bob/2026/20260929.md`), the daily template, `gtd_daily.md`,
  `dash.md` and the project notes the ledger links to.
- **The `bob` CLI's Pomodoro tooling.** `bob pomodoro`, `tmux-pomodoro`, `notify`, `capture-pomodoros`,
  `capture-pomodoro-name` and `task-status-hooks`.
- **Measurements.** Numbers taken from 119 daily notes (2026-06-02 → 2026-09-28) and from each note's git
  history in the vault repo. The git history shows what the open queue looked like during each day, not just
  its end-of-day state.
- **Outside sources.** Claims from the planning and productivity literature were checked against primary or
  publisher sources, listed at the end.

---

## TL;DR

1. **Your time log works. Keep it.** It has honest time ranges, `[t:: …]` totals, 🍅 marks on the tasks that
   actually got attention, and short interstitial sub-bullets. The capture and tmux tooling built around it is
   good. The log isn't the chaotic part.
2. **The chaos comes from the unfinished part of the section.** The open (`- [ ] ()`) entries have gradually
   become your **entire active backlog**:
   - In June a day's open queue peaked at a median of **3.5 task links** across **1–2 entries**. Today it holds
     **77 links across 22 named entries**. One of those entries is literally called `LATER` and holds 23 links.
   - Of today's 77 queued links, the median one has been carried forward for **9 days**. **30 have been
     carried for 14 days or more.**
   - Meanwhile your capacity has stayed flat at about **7 blocks, or about 4.5 tracked hours, per day**.
     Today's "plan" is roughly **10×** what one day can hold.
3. **Three structural causes:**
   - **One list does three jobs.** It is today's plan, the backlog, and, through `bob task-status-hooks`, the
     source of truth for which tasks count as Next or In Progress.
   - **Everything carries forward by default.** The daily *migrate* ritual moves every unfinished entry to the
     next day. The daily *select* ritual ("Review WIP + NEXT tasks and plan daily Pomodoros") was **last
     completed on 2026-09-09**. That is the same week the open queue went from ≤10 entries to 24.
   - **New tasks arrive faster than you close them.** In the `sase*`/`bob*` notes, September saw 315 tasks
     created and 148 closed.
4. **Recommendation: "Ledger + Closed List + Roadmap."**
   - Keep the ledger exactly as it is.
   - Cap today's open entries to capacity: one 🎯 Highlight, at most 4 other named sessions, and GTD.
   - Move everything else into a single `roadmap.md` with Now / Next / Later sections.
   - Replace "migrate unfinished" with a 5-minute *pick*.
   - Add a 30-minute weekly roadmap review.

   Your daily note gets **simpler** (about 100 Pomodoro lines → about 20), and three daily GTD rituals become
   one. The only new structure is one note and one weekly habit.

---

## 1. How the current system works

**Daily note layout.** The `_templates/daily.md` template creates a `## Pomodoros` heading. Its title contains
a Dataview expression that sums `t::` over completed tasks in the section. The template seeds one open entry:
`- [ ] () — GTD` linking to `[[#^gtd]]`.

**What an entry looks like.** Each ledger entry is a checkbox task:

- It has a time range and a duration: `(**0735-0800** [t:: 25m])`.
- It has an optional ALL-CAPS session name. Names started on 2026-08-26, driven by the `gtd#^name-poms` task
  and `bob capture-pomodoro-name`.
- Its child bullets are block links to tasks in project or area notes (`[[sase#^fix-v-key]]`).
  - A 🍅 prefix marks the tasks you actually worked on during that block.
  - `~~strike~~` marks links to tasks that are now done.
  - Sub-sub-bullets hold short log notes, e.g. "Launched `sase-1c1`!" or "RESEARCH: [[…]]".

**Tooling around the ledger:**

- `bob pomodoro` / `tmux-pomodoro` / `bob notify` show the current block's remaining time and notify you when it
  ends.
- `bob capture` can link new tasks straight into a named open Pomodoro (`@route:id#`).
- **`bob task-status-hooks` makes "the current Pomodoro ledger the source of truth for active task statuses".**
  - Tasks linked under open entries are promoted to at least Next `[*]`.
  - Tasks that aren't reachable from the ledger, or from yesterday's note, are reset to Ready `[ ]`.
  - The WIP / NEXT / READY chips on `dash.md` count those statuses.

**Daily rituals in `gtd_daily.md`:**

- "Migrate unfinished Pomodoro tasks from yesterday's daily file"
- "Review READY tasks"
- "Review WIP + NEXT tasks and plan daily Pomodoros"
- plus hygiene items: weather, email, calendar, Google Keep import.

**History.**

- Through May 2026 (the zorg era) you kept a separate `YYYYMMDD_poms` file. It had PLANNED and DONE sections,
  used 5-minute `p::` units, and tracked a running daily total (`p::7/77`).
- The Obsidian ledger started on 2026-05-28. It moved to the `[t:: Nm]` format in early June.
- The legacy zorg system had a weekly GTD review (`recur::Sa`). Nothing equivalent exists in the Obsidian
  setup; I found no weekly recurring review task.

---

## 2. What the data says

### 2.1 The time log is healthy and consistent

Measured over 2026-06-02 → 2026-09-28 (119 days, 851 completed blocks):

| Metric | Value |
|---|---|
| Tracked time per day | mean **271 min (4.5 h)**; median 270; p10 125; p90 405 |
| By month | Jun 4.3 h · Jul 3.8 h · Aug 5.1 h · Sep 4.8 h |
| By weekday | flat, from 246 min (Tue) to 298 (Fri); weekends ≈ weekdays |
| Completed blocks per day | mean **7.2** |
| Block length | median **30 min**, mean 38; only **34%** are exactly 25 min |
| Long blocks | **54%** of tracked minutes fall in blocks ≥ 50 min |
| Task links per completed block | mean **2.2** (1 → 326 blocks, 2 → 233, 3 → 141, 4+ → 130) |
| 🍅-marked tasks per block (since 07-12) | mean **1.5** |

Three things stand out.

- **Your blocks are variable-length focus sessions, not classic pomodoros.** In practice that is closer to
  Flowtime than to Cirillo's method, and it's fine; see §3.6.
- **A block usually covers about two tasks.** That's what supervising several agents at once looks like. Your
  named sessions, which group tasks by theme, fit that way of working better than one-task-per-pomodoro does.
- **Capacity is very stable.** That means you can plan against it.

### 2.2 Where the time goes

Since you started naming sessions (2026-08-26 → 2026-09-28): 160 tracked hours across **60 distinct session
names**.

| Bucket | Share of tracked time |
|---|---|
| `GTD` | **16.6%** (about 47 min/day) |
| Reactive: `SHIT`, `FIXES`, `RELAUNCH`, `RESTARTS`, `FIX` | **13.1%** |
| Everything else, spread over about 55 themes (top: `REMOTE` 7.0%, `SASE` 6.1%, `BOB` 3.8%, `TOOL` 3.7%, `GOALS` 3.3%) | about 70% |

About 30% of each day goes to GTD and reactive work, and that share is predictable. A realistic plan budgets
for it: of about 7 blocks, **about 5 are available for planned themes**.

### 2.3 The open queue grew about 20× while capacity stayed flat

I rebuilt the peak state of each day's open entries by walking every git revision of each daily note. The
end-of-day files don't show this, because migration cuts unfinished entries out of them.

| Period | Open entries per day (median / max) | Open task links (median / max) |
|---|---|---|
| Jun 01–30 | 1.5 / 5 | 3.5 / 10 |
| Jul 01–31 | 2 / 3 | 11 / 29 |
| Aug 01–15 | 5 / 8 | 15 / 19 |
| Aug 16–31 | 6.5 / 9 | 19 / 29 |
| Sep 01–10 | 10 / 14 | 25 / 35 |
| Sep 11–20 | 15 / 20 | 42.5 / 47 |
| **Sep 21–29** | **23 / 24** | **63 / 77** |

**How old today's queue is.** For each of today's 77 queued links, I found the first day it appeared in any
ledger. I excluded two block IDs, `^gtd` and `^read-research`, because they are reused across notes.

| Age | Count |
|---|---|
| Median | **9 days** |
| ≥ 7 days | **49 links** |
| ≥ 14 days | **30 links** |
| Oldest | `sase_memory#^feature-flags` (44 d), `sase_clean#^work-all-beads` (40 d), `sase#^bulk-gate-cmds` (38 d), `sase_memory#^review-sase-art` (32 d) |

### 2.4 The status labels have lost their meaning

Vault-wide status counts, excluding `#ref` reading-list items:

| Status | Count |
|---|---|
| In Progress `[/]` | **47** |
| Next `[*]` | **32** |
| Ready `[ ]` | 379 |
| Blocked `[?]` | 304 |

**All 47** In Progress tasks are linked from today's queue. Once 79 tasks are "active", the WIP
and NEXT chips on `dash.md` no longer tell you what you're actually doing.

Little's Law gives a check on this: average lead time = WIP ÷ throughput.

- September throughput is about 148 closures in 28 days, or roughly **5 per day**.
- About 79 active items (47 + 32) ÷ 5 per day ≈ **15 days** before an average active item finishes.
- The ages measured above match that estimate.

### 2.5 New tasks arrive faster than you close them

Tasks in `sase*.md` and `bob*.md` notes, counted by `created::` date and by `completion::` / `cancelled::` date:

| Month | Created | Closed | Closed ÷ created |
|---|---|---|---|
| Jun | 251 | 248 | 0.99 |
| Jul | 329 | 263 | 0.80 |
| Aug | 569 | 405 | 0.71 |
| Sep (to 29th) | 315 | 148 | **0.47** |

There are currently about **400** open `sase*`/`bob*` tasks.

One inflow is worth calling out: **research reports**.

- 14 open "Read [[ref/chat/…]]" / "Read and act on …" tasks. Twelve of them are Next or In Progress, and a
  whole `READ` entry sits in today's queue.
- **172** unread `#ref` notes.

Agents are producing research faster than you can read it.

### 2.6 The planning step stopped; the carry-forward step didn't

From `done/gtd_daily_done.md`:

- **"Review WIP + NEXT tasks and plan daily Pomodoros" and "Review READY tasks" were last completed on
  2026-09-09.** The open instances in `gtd_daily.md` are still scheduled for 2026-09-10.
- **"Migrate unfinished Pomodoro tasks" kept getting done.** The latest completion was 2026-09-28.

The peak number of open entries was ≤10 on every day before 09-09. It was 10–24 on every day after.

Correlation isn't proof, but the mechanism is plain. When the *select* step lapses and the *copy* step
continues, the list can only grow. And a daily review of 77 items is expensive enough that skipping it is the
natural response.

---

## 3. Diagnosis

### 3.1 One list is doing three jobs

The open part of `## Pomodoros` is currently:

1. **today's plan** (what Cirillo calls the *To Do Today* sheet);
2. **the backlog of active work** (his *Activity Inventory*); and
3. **the status source** for `task-status-hooks`, which decides what counts as Next or In Progress.

Cirillo's original method deliberately keeps these apart:

- **Activity Inventory:** everything that has come up.
- **To Do Today:** filled in at the start of each day by *choosing* from the inventory and prioritizing.
- **Records:** the log.

In his words: *"At the beginning of each day, choose the tasks you want to tackle from the Activity Inventory
Sheet, prioritize them, and write them down in the To Do Today Sheet."* [1]

Your Records sheet is in good shape. The To Do Today sheet and the Inventory have merged.

**Job 3 makes the merge stick.** Anything you remove from the ledger gets demoted to Ready. That gives you a
quiet incentive to keep everything you care about in the daily note, just so it stays visibly Next. I think
this is the main reason the list keeps growing, rather than a lack of discipline. It's an inference, but it
fits every data point above.

### 3.2 An open list that carries forward by default

Mark Forster's *Do It Tomorrow* rests on a **closed list**: *"A line is drawn at the bottom of the day's list so
that each day there is a finite amount of work to do."* New work goes to tomorrow's list unless it genuinely
has to happen today [3].

Your migration ritual does the opposite. Every unfinished item carries forward automatically, and nothing
forces a choice.

### 3.3 A plan at 10× capacity stops working as a plan

- **You always feel behind.** Ryan Singer, in *Shape Up*: *"Backlogs are a big weight we don't need to carry…
  The growing pile gives us a feeling like we're always behind even though we're not."* [4] A 22-entry queue
  guarantees that every day ends looking like a failure, even on a 7-hour day. I'd bet that feeling is most of
  what "chaotic" means here.
- **People underestimate how long work takes, even when past experience says otherwise.** In Buehler, Griffin
  & Ross's classic study, thesis students predicted 33.9 days and took 55.5. Only 29.7% finished by their own
  estimate [8]. A plan sized to your *measured* capacity (about 5 planned blocks) sidesteps the bias. A list
  sized to your ambitions doesn't.
- **An unsorted list doesn't give the relief a plan does.** Masicampo & Baumeister found that making a
  *specific plan* for an unfinished goal removes its intrusive, distracting effects [9]. A carried-forward pile
  of 77 links isn't a specific plan. Arguably it's the opposite: a daily reminder of everything still unfinished.

### 3.4 Too much work in progress

Personal Kanban has two rules: *visualize your work* and *limit your work in progress* [5]. You already have
the visualization (`dash.md`). What's missing is the limit.

As computed in §2.4, 79 active items at about 5 closures per day means a lead time of about 15 days. The only
ways to shorten it are to lower WIP or raise throughput. Of the two, WIP is the one you control directly.

Too much WIP also costs attention. Leroy's work on *attention residue* shows that switching away from an
unfinished task hurts performance on the next one [11]. Dozens of half-started threads mean there is always
residue.

### 3.5 Agent orchestration changes what a unit of work is, and your session names already reflect it

- Simon Willison describes running agents in parallel and puts the bottleneck on the human: *"the natural
  bottleneck on all of this is how fast I can review the results"*, and *"I can only focus on reviewing and
  landing one significant change at a time"* [15].
- Park et al. (2026) interviewed 19 developers about supervising coding agents. They found that developers
  concentrate their supervisory effort in *planning* and turn repeated guidance into reusable assets [15].

Your average of 2.2 links per block is that pattern: several agents moving at once, with your attention
cycling across them. So the right thing to plan is a small number of **themes or outcomes to push through
review**, not individual tasks. Your ALL-CAPS session names already are exactly that. The problem is that
there are 22 of them open at once and 60 distinct ones in a month.

### 3.6 Not problems: variable block length and logging granularity

- **On block length, the evidence is mixed.** Biwer et al. (2023, N = 87) found that fixed breaks improved mood
  and efficiency, with the same task completion as self-regulated breaks [2]. But Göksu, Wiradhany & de Bruin
  (2026, N = 176) found no performance difference, and self-regulated breaks produced *better* mood [2].
  Smits, Wenzel & de Bruin (2025) found no differences between Pomodoro, Flowtime and self-regulated breaks
  [14]. Your median block of 30 min, with long runs when things are flowing, is a defensible choice. There's
  no reason to force blocks back to 25 minutes.
- **Your 🍅 marks and sub-bullet notes are interstitial journaling done right.** That means writing a few lines
  each time you switch tasks about what you just did [12]. Keep them.

---

## 4. Options considered

| # | Option | What changes | Complexity | Fit for you | Verdict |
|---|---|---|---|---|---|
| A | **Status quo, but restart the daily review** | Nothing structural | Same | A 77-item daily review is exactly what lapsed | ✗ The problem is the design, not willpower |
| B | **Full Cirillo method** (estimates per activity, interruption marks `'`/`-`, records processing) [1] | Adds estimation and interruption tracking | Higher | Right structure, too much ceremony | ◐ Adopt only the inventory/today split |
| C | **Newport-style time-blocking** (every minute gets a job; re-plan when disrupted) [6] | A full daily timeline | Higher | Brittle when agents finish unpredictably and gates interrupt; about 13% of your time is reactive | ◐ Optional on meeting-heavy or deep-work days; Newport notes that reactive periods "can be blocked off like any other type of work" |
| D | **One long list** (Forster's Autofocus / FVP) [3] | Replace statuses with a single scanned list | Lower on paper | Clashes with the status hooks and ~400 open tasks | ◐ Borrow FVP's question, *"What do I want to do more than X?"*, to pick among today's few sessions |
| E | **Personal Kanban with a WIP limit** [5] | Cap In Progress `[/]` at about 5 | Low | `dash.md` already shows counts | ✓ Adopt as a guardrail |
| F | **Now/Next/Later roadmap + closed daily list + one Highlight** [3][7][13] | Backlog moves to one note; the daily list is capped and disposable | Lower day to day; one new note | Keeps your ledger, names and tooling | ✓✓ **Recommended** |
| G | **External planner app** | Leave Obsidian for planning | New tool | Throws away the capture, hooks and tmux integration you've built | ✗ |

---

## 5. Recommendation: Ledger + Closed List + Roadmap

The core rule: **the daily note holds what you *did* and what you *will do today*. Everything else lives in the
roadmap.**

### 5.1 Keep unchanged

- The ledger entry format: time range, `[t:: Nm]`, ALL-CAPS names, 🍅 marks, strikethrough, interstitial
  sub-bullets.
- The Dataview total in the heading.
- `bob pomodoro`, `tmux-pomodoro`, `notify`, `capture-pomodoro-name`.
- Variable block lengths. Use the timer as a check-in, not a rule.

### 5.2 Daily: a 5-minute pick and a closed list

Replace the three planning and migration rituals in `gtd_daily.md` with one:

> `- [ ] #task Pick today's 🎯 + ≤4 sessions from [[roadmap#Now]] [repeat:: every day when done]`

The rules:

1. **One 🎯 Highlight.** Pick the single outcome that would make today a win, and work it first.
   - *Make Time* suggests a Highlight of about 60–90 minutes [7]. For you that's roughly 2–3 blocks, e.g. "land
     the goals epic roadmap".
   - Record it as an inline field above the ledger, e.g. `🎯:: [[sase_goals#^epic-roadmap]]`. That lets you
     query your Highlight history later.
2. **At most 4 more named sessions, plus `GTD`.** This follows from your data: about 7 blocks, minus about 1 for
   GTD and about 1 for reactive work, leaves about 5 planned. Keep the total to **about 12 task links or
   fewer**. The Ivy Lee method's "six things, in order" works at the same scale [16].
3. **The list is closed.** New ideas and tasks captured during the day go to their project note or to
   `roadmap#Next`, not into today's open entries.
   - Exception: work that genuinely must happen today. Cirillo's "Unplanned & Urgent" section covers this [1].
     Append it to the *current* block, or add one extra entry.
   - Retarget `bob capture` shortcuts that link into future open Pomodoros so that they point at the roadmap
     instead.
4. **Nothing carries forward automatically.** At shutdown (about 2 minutes), delete the leftover open entries.
   The tasks aren't lost: they're still in their project notes and on the roadmap.
   - If one of them should be tomorrow's 🎯, write it on `roadmap#Now` as "tomorrow".
   - This is Newport's shutdown ritual in miniature: *"schedule shutdown, complete"* [6]. Masicampo & Baumeister
     suggest that parking unfinished work in a known place is what lets it stop nagging at you [9].

### 5.3 A single `roadmap.md`: Now / Next / Later

Now/Next/Later swaps dates for **time horizons that express confidence**. You commit only to what's directly
ahead [13]. You're already partway there: your themes are named, and your queue has a `LATER` entry.

Write the roadmap in **the same bullet shape as ledger entries**. Moving a theme between the roadmap and
today's plan is then a plain cut and paste:

```markdown
---
parent: "[[gtd]]"
---
# Roadmap

## Now   <!-- ≤ 5 themes; these are what you're landing this week -->
- GOALS
	- [[sase_goals#^epic-roadmap]]
	- [[bob#^better-roadmaps]]
- DECKS
	- [[sase#^card-blocks]]
	- [[sase#^p-key-for-decks]]
- QUEUE
	- [[sase#^q-weight]]
	- …

## Next  <!-- the next few themes; promote when a Now theme lands -->
- SUDO
	- [[sase#^sudo]]
- AUDIT MEMORY
	- …

## Later <!-- everything else; pruned weekly -->
- [[sase#^green-check-full]]
- …
```

This is also a cheap first answer to your open `bob#^better-roadmaps` task: a roadmap *is* a structure note
with horizon headings.

### 5.4 Weekly: a 30-minute roadmap review (the habit you're missing)

Add `[repeat:: every week on <day>]`. The review has five steps:

1. **Re-rank.** Promote from Next to Now until Now has 5 themes. Your Now themes are your bets for the week, in
   the Shape Up sense of choosing what to work on instead of grooming a backlog [4].
2. **Prune.** Cancel, or deliberately push to Later, anything that has sat 3+ weeks with no 🍅. Today, 30 items
   would qualify.
3. **Set a research budget.** Decide how many research reports you'll read this week, and don't launch new
   research swarms beyond that until the reading queue drops. The current reading backlog is 14 tasks plus 172
   unread refs.
4. **Check the WIP guardrail.** Is `[/]` at about 5 or fewer? If not, the plan was too wide.
5. **Look at the numbers.** Weekly hours, 🎯 hit rate, and created vs. closed.

### 5.5 What today's note would look like

```markdown
## Pomodoros (`= durationformat(…)`)
🎯:: [[sase_goals#^epic-roadmap]]

- [x] (**0735-0800** [t:: 25m]) — GOALS
	- 🍅 [[sase_goals#^epic-roadmap]]
	- 🍅 [[bob#^better-roadmaps]]
- [x] (**0830-0945** [t:: 75m]) — GOALS
	- …
- [ ] (**1235-1300** [t:: 25m]) — GOALS
	- [[sase_goals#^epic-roadmap]]
	- [[sase#^fix-telegram-leak]]
- [ ] () — DECKS
	- [[sase#^card-blocks]]
	- [[sase#^p-key-for-decks]]
- [ ] () — READ
	- [[sase#^harden-services]]
- [ ] () — GTD
	- [[#^gtd]]
```

That's about 20 lines instead of about 110. The other ~18 entries live on `roadmap.md`, one click away.

### 5.6 One-time transition (about 30 minutes)

1. Create `roadmap.md` with a `parent` frontmatter link, following the vault's new-note rule.
2. Cut today's open entries after the first 3–4 into it. Sort them into Now (≤5), Next and Later. The existing
   `LATER` entry moves over as-is.
3. While you're there, cancel anything you already know you won't do.
4. Edit `gtd_daily.md`:
   - Drop "Migrate unfinished Pomodoro tasks", "Review READY tasks" and "Review WIP + NEXT … plan".
   - Add the single *pick* task from §5.2.
   - Add the weekly review from §5.4.
5. Add the `🎯::` line to `_templates/daily.md`, under the Pomodoros heading.
6. **Expect a one-time status drop.** Within a day or two, `task-status-hooks` will reset most of today's ~47
   `[/]` and ~32 `[*]` tasks to Ready, because they'll no longer be reachable from the ledger. That's the point:
   Ready is what they really are. The roadmap keeps them visible.

### 5.7 Optional tooling, only after two weeks and only if the habit sticks

Ordered by how much each one strengthens the habit:

1. **Make `roadmap#Now` a Next source in `task-status-hooks`.** Tasks there get Next `[*]`. The daily ledger
   keeps driving In Progress `[/]`. This removes the incentive described in §3.1: you'll no longer need to keep
   something in the daily note just to keep it Next.
2. **Show plan load in `bob pomodoro` / `tmux-pomodoro`**, e.g. `🎯✓ · 3/5`. Warn when open entries or links go
   over the cap.
3. **A Dataview line on the daily note** showing planned vs. completed sessions and whether the 🎯 was touched.
   Over time this gives you a real plan hit rate.

The bob tooling lives in its own repos (bob-cli / bob-plugins), so these would be separate work items there.

### 5.8 How to tell whether it's working (a 2-week check, around 2026-10-13)

| Signal | Today | Target |
|---|---|---|
| Open task links in the day's plan at its peak | 77 | **≤ 12** |
| Open named entries | 22 | **≤ 5 + GTD** |
| `[/]` In Progress (non-ref) | 47 | **≤ 5–8** |
| Days where the 🎯 got ≥ 1 🍅 | n/a | **≥ 80%** |
| Planned sessions done ÷ planned | n/a (plan never finishable) | **≥ 70%** |
| Weekly created ÷ closed (sase/bob) | ≈ 2.1 (Sep) | trending toward **≈ 1** |
| GTD share of tracked time | 16.6% | **≤ 12%** (less migration churn) |

If the 🎯 hit rate is high but the roadmap's Now list never empties, your weekly bets are too big; shrink them.
If the hit rate is low, look at the reactive share. If `SHIT`/`FIXES`/`RELAUNCH` is regularly above about 15%,
give it its own daily session instead of letting it take over the Highlight.

### 5.9 Trade-offs and risks

- **The roadmap could become the next junk drawer.** The Now cap (≤5) and the weekly prune are the defenses. If
  Later grows past about 50 items, cancel aggressively. Shape Up's point is that an important idea will come
  back on its own [4].
- **Less at-a-glance visibility in the daily note.** This is deliberate. If you miss it, a transclusion of
  `![[roadmap#Now]]` at the bottom of the daily note shows the options without making them commitments.
- **Planning can't fix intake.** A created ÷ closed ratio of about 2 in September means the backlog will grow
  no matter how you plan the day. Holding the line comes down to the weekly prune and the research budget.
- **Simpler, with one new habit.** The daily ritual gets simpler (one pick instead of migrate + two reviews) and
  the note shorter. The only added structure is `roadmap.md` plus a 30-minute weekly slot. The zorg-era system
  had a weekly review that didn't carry over to Obsidian, and that missing weekly layer is what the daily list
  has been standing in for.

---

## Sources

1. Cirillo, F. *The Pomodoro Technique* (paper, 2006): To Do Today / Activity Inventory / Records sheets;
   "Unplanned & Urgent" section. <https://www.pomodorotechnique.com/>; copy of the paper:
   <https://www.northbaycounselling.com/wp-content/uploads/2022/05/Cirillo-Pomodoro-Technique.pdf>
2. Biwer, F., Wiradhany, W., oude Egbrink, M., & de Bruin, A. (2023). Understanding effort regulation: Comparing
   'Pomodoro' breaks and self-regulated breaks. *BJEP* 93(S2), 353–367 (N = 87).
   <https://pubmed.ncbi.nlm.nih.gov/36859717/>. Göksu, A., Wiradhany, W., & de Bruin, A. (2026). When to take a
   break… *Behavioral Sciences* 16(7):1158 (N = 176; no performance difference, better mood with self-regulated
   breaks). <https://pmc.ncbi.nlm.nih.gov/articles/PMC13405840/>
3. Forster, M. *Do It Tomorrow* (closed lists, "current initiative"); Final Version Perfected (2015; reposted
   2021). <http://markforster.squarespace.com/blog/2011/1/24/review-of-the-systems-do-it-tomorrow.html>;
   <http://markforster.squarespace.com/blog/2021/11/16/the-final-version-perfected-fvp-instructions-reposted.html>
4. Singer, R. *Shape Up* (Basecamp): "Bets, Not Backlogs"; appetites; six-week cycles and cool-down.
   <https://basecamp.com/shapeup/2.1-chapter-07>; <https://basecamp.com/shapeup/1.2-chapter-03>
5. Little's Law in knowledge work (Kanban University, 2022).
   <https://kanban.university/wp-content/uploads/2022/09/Exploring-Littles-Law-KGS-2022.pdf>. Benson, J. &
   DeMaria Barry, T. *Personal Kanban*: visualize work, limit WIP. <https://personalkanban.com/>
6. Newport, C. Time-block planning, "give every minute a job" and update the plan when knocked off it:
   <https://www.timeblockplanner.com/>; <https://calnewport.com/deep-habits-the-importance-of-planning-every-minute-of-your-work-day/>.
   Shutdown ritual ("schedule shutdown, complete"):
   <https://calnewport.com/drastically-reduce-stress-with-a-work-shutdown-ritual/>
7. Knapp, J. & Zeratsky, J. *Make Time*: one daily Highlight of about 60–90 minutes.
   <https://maketime.blog/article/choose-a-highlight-to-make-time-every-day/>
8. Buehler, R., Griffin, D., & Ross, M. (1994). Exploring the "planning fallacy". *JPSP* 67(3), 366–381.
   <https://web.mit.edu/curhan/www/docs/Articles/biases/67_J_Personality_and_Social_Psychology_366,_1994.pdf>.
   Kahneman & Tversky (1979) coined the term.
9. Masicampo, E. J., & Baumeister, R. F. (2011). Consider it done! Plan making can eliminate the cognitive
   effects of unfulfilled goals. *JPSP* 101, 667–683. <https://users.wfu.edu/masicaej/MasicampoBaumeister2011JPSP.pdf>
10. Gollwitzer, P. M., & Sheeran, P. (2006). Implementation intentions and goal achievement: a meta-analysis
    (94 tests, d = .65). *Adv. Exp. Soc. Psych.* 38, 69–119. <https://kops.uni-konstanz.de/handle/123456789/10973>.
    Background for "decide the *when* of the Highlight."
11. Leroy, S. (2009). Why is it so hard to do my work? The challenge of attention residue when switching between
    work tasks. *OBHDP* 109(2), 168–181. <https://ideas.repec.org/a/eee/jobhdp/v109y2009i2p168-181.html>
12. Stubblebine, T. (2017). Interstitial journaling:
    <https://betterhumans.pub/replace-your-to-do-list-with-interstitial-journaling-to-increase-productivity-4e43109d15ef>;
    Ness Labs: <https://nesslabs.com/interstitial-journaling>
13. Bastow, J. (ProdPad). Now/Next/Later roadmaps: time horizons instead of dates.
    <https://www.prodpad.com/blog/invented-now-next-later-roadmap/>
14. The Flowtime Technique (Urgent Pigeon, 2016): <https://medium.com/@UrgentPigeon/the-flowtime-technique-7685101bd191>;
    overview: <https://zapier.com/blog/flowtime-technique/>. Smits, Wenzel & de Bruin (2025), *Behavioral Sciences*
    15(7):861, found no productivity, completion or flow differences between Pomodoro, Flowtime and self-regulated
    breaks. *(Verified secondhand, through the verification pass.)*
15. Willison, S. (2025-10-05). Embracing the parallel coding agent lifestyle.
    <https://simonwillison.net/2025/Oct/5/parallel-coding-agents/>. Park, Y. S., et al. (2026-09-21). *The Work
    Behind Delegation: A Framework for Supervising AI Coding Agents* (arXiv preprint).
    <https://arxiv.org/abs/2609.24234>. Osmani, A. (2026-01-02), conductor vs. orchestrator:
    <https://addyosmani.com/blog/future-agentic-coding/>
16. The Ivy Lee method: six most important tasks, ranked, written the evening before. The 1918 origin story is
    unsourced folklore. <https://jamesclear.com/ivy-lee>

**How the local numbers were computed.** Python scripts parsed `## Pomodoros` sections from `~/bob/2026/2026MMDD.md`
files, plus every git revision of each file (`git log` / `git show` in the vault repo). Status and intake counts
come from `grep` over `#task` lines, excluding `_templates/`, `_conflicts/`, `.obsidian/` and `#ref` items;
done archives are included for created/closed counts. The numbers are approximate. For example, reused block
IDs (`^gtd`, `^read-research`) were excluded from the age statistics, and tasks without `created::` fields are
undercounted.
