# Pomodoro ledger and daily roadmap: keep the log, cap the plan, stop capture from filling the day

- **Research date:** 2026-09-29
- **Question:** Should Bryan change how he tracks pomodoros, work, time, and the day's roadmap in the
  `## Pomodoros` section of his Bob daily notes (example: `~/bob/2026/20260929.md`)? The system should stay
  simple. More structure is fine only if it pays for itself.
- **Inputs:** five independent reports (`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`, in this directory) plus the
  lead researcher's own checks:
  - I re-measured the vault's daily notes and their git history.
  - I read the `bob` CLI source that reads the ledger (`task-status-hooks`, `capture`, Pomodoro section parsing)
    and the `block-id-prompt` Obsidian plugin.
  - I re-checked the newer outside citations against their primary sources.

---

## Bottom line

1. **Keep the log.** Every report agrees on this. The completed entries form an honest, low-friction time diary:
   - each entry has a time range and a `[t:: Nm]` duration, summed in the heading;
   - ALL-CAPS theme names;
   - 🍅 marks on the tasks that actually got attention;
   - short notes in the sub-bullets.

   Nothing about blocks being longer or shorter than 25 minutes needs fixing.
2. **The chaos is the *open* part of the section.** It has quietly become the whole active backlog.
   - A day's peak open queue grew steadily from a median of **3.5 task links in June** to **78 links across 23
     named entries today**.
   - A typical day actually gets through about **7 blocks, 3–4 themes, 5–8 task links and about 4.5–5 tracked
     hours**, so today's "plan" is roughly 10× what one day holds.
3. **Four mechanisms, working together, produce this.** The fourth is new in this consolidation:
   - **No exit.** "Migrate unfinished Pomodoro tasks" copies every leftover forward, every day.
   - **No selection.** "Review WIP + NEXT tasks and plan daily Pomodoros" was **last completed 2026-09-09**. The
     queue passed 10 entries that same week.
   - **Status coupling.** `bob task-status-hooks` makes the open ledger the source of truth for Next /
     In Progress. Removing a link from the ledger demotes its task, so there is a quiet reason to keep everything
     there.
   - **Capture puts new tasks straight into today.** `bob capture '@route:block-id …'` creates a Next task *and*
     links it into today's ledger. `#name` creates a new named future bucket when none matches.
     - **67 of the 74 task links queued today (91%) first entered a daily ledger on the day the task was
       created.**
     - So the queue is mostly not the result of choosing work for the day. Tasks landed there when they were
       captured and then got carried forward.
4. **Recommendation: "Ledger + closed daily list + one roadmap note".**
   - Keep the `## Pomodoros` heading, format and tooling exactly as they are.
   - Let the open part hold only today's commitments:
     - one `highlight::` outcome;
     - at most two more named themes;
     - `GTD`.
   - Put everything else in a single `roadmap.md` (Now / Next / Later).
   - Replace the three daily planning/migration chores with one 5-minute *pick*.
   - Capture tasks that aren't for today with `@route^id` instead of `@route:id`.
   - Add a short weekly review.
   - Run it as a two-week trial (2026-09-30 → 2026-10-13) with the pass/fail signals in §7.6.

The daily note gets shorter: about 20 lines in the Pomodoros section instead of about 110. The morning ritual gets
smaller. The only new structure is one note and one weekly habit.

---

## 1. The current system in one screen

**Ledger atom.** Each block is one checkbox line with its tasks as children:

```markdown
- [x] (**0830-0945** [t:: 75m]) — GOALS
	- 🍅 [[sase_goals#^epic-roadmap]]
		- Launched sase-1c1!
```

- Open, untimed buckets look like `- [ ] () — NAME`, with task links as children.
- The heading's Dataview expression sums `t` over **completed** tasks whose section subpath starts with
  `Pomodoros`.

**Tooling that reads or writes the ledger:**

| Tool | Behavior that matters for this decision |
|---|---|
| `bob capture` (`docs/capture.md`) | `@route:id` → new task at Next `[*]` **plus** a link under today's current or first open Pomodoro. `#name` targets a named open entry, or creates a new `- [ ] () — NAME` future entry. `@route^id` → an ordinary Ready task with a block ID and **no** ledger link. |
| `bob task-status-hooks` | Links under **open** entries in `## Pomodoros` are promoted to at least Next. Next tasks that can't be reached from there, or from the latest earlier daily note, reset to Ready. The same goes for In Progress tasks in area/project notes. It also deletes childless entries and de-duplicates links across open entries. It refuses to run when there is more than one open *timed* entry. |
| `block-id-prompt` plugin (Ctrl+Shift+Enter) | Inserts a task link under the single open timed entry, or else under the first open entry. It errors when there are several open timed entries. |
| `se` snippet / `_templates/schedule.md` | Inserts `(**HHMM-HHMM** [t:: 25m])` atoms from the current time. `+N` / `-N` capture adjusts the current block. |
| `dash.md` | Counts and lists WIP / NEXT / READY using the Tasks plugin, whose global filter is `#task`. |
| `gtd_daily.md` | Recurring morning chores. Includes "Migrate unfinished Pomodoro tasks", "Review READY tasks" and "Review WIP + NEXT tasks and plan daily Pomodoros". |

Two consequences follow for any redesign:

- **The heading name is load-bearing.** `bob` matches the heading `## Pomodoros` (`is_pomodoros_heading` in
  `src/native/pomodoro.rs`). So does the plugin (`/^##\s+Pomodoros(?:\s.*)?$/`), and capture, `bob pomodoro` and
  `tmux-pomodoro` all use that section.
- **Only open entries *inside* that section count as "today" for statuses.**

---

## 2. What the vault data shows

These are the lead's own measurements over `~/bob/2026/*.md` and every git revision of each daily note. They agree
with `__cld`'s figures to within rounding. They also settle the places where the reports disagreed.

### 2.1 Capacity is stable and plannable

| Metric | Jun 2 – Sep 28 (118 logged days) | Sep 1 – 28 |
|---|---|---|
| Tracked minutes/day | median **270**, mean 273 (p10 125, p90 405) | median **~300**, mean 289 |
| Completed blocks/day | 7.2 | 7.2 |
| Block length | median 30, mean 38; only **34%** exactly 25 min | median 35, mean 40 |
| Share of minutes in blocks ≥ 50 min | **54%** | 61% |
| Distinct themes/day (names began 2026-08-26) | — | median **4** (Sep 10–28: 3) |
| Distinct task links touched/day | median 8 | median 8 (🍅-marked: 6) |

`__cld` measured where the time goes from 2026-08-26 to 2026-09-28:

- `GTD` takes about **17%** of tracked time.
- Reactive themes (`SHIT`, `FIXES`, `RELAUNCH`, `RESTARTS`) take about **13%**.
- That leaves **about 5 of about 7 daily blocks** for planned work.

`__cdx`'s 320-min median came from the busier week of Sep 22–28, and `__grk`'s 300-min figure covers September.
All three numbers describe the same stable band.

### 2.2 The open queue grew about 20× while capacity stayed flat

Peak open state per day, rebuilt from git history:

| Period | Open named entries (median / max) | Open task links (median / max) |
|---|---|---|
| Jun | 1.5 / 5 | 3.5 / 10 |
| Jul | 2 / 3 | 11 / 29 |
| Aug 1–15 | 5 / 8 | 15 / 19 |
| Aug 16–31 | 6.5 / 9 | 19 / 29 |
| Sep 1–9 | 10 / 14 | 25 / 35 |
| Sep 10–20 | 14 / 20 | 42 / 48 |
| **Sep 21–29** | **23 / 24** | **63 / 78** |

**Correction to `__gem`:** the pattern did *not* start on 2026-09-25. End-of-day files hide the queue, because
migration cuts leftovers out of them. So "closed days are clean" is true (`__mus`, `__grk`) but misleading. The
git history shows a steady rise that began in July and sped up after the planning step lapsed.

### 2.3 How today's queue got there

For each of today's 74 distinct queued task links, I compared the task's `created::` date with the first day the
link appeared in any daily ledger revision:

- **67 of 74 (91%) entered the ledger on the day the task was created.** In other words, they were captured
  straight into the day.
- **Age of today's queued links.** The median has been carried for **8 days**; 45 have been carried for 7 days
  or more, and 27 for 14 days or more. `__cld` measured 9 / 49 / 30 with slightly different exclusions.

The open queue is best described as **a capture inbox that never drains**, not as a plan that got too ambitious.

### 2.4 The selection ritual stopped; the carry-forward ritual didn't

- **Planning and review.** From `done/gtd_daily_done.md`, "Review WIP + NEXT … plan daily Pomodoros" and "Review
  READY tasks" were last completed on **2026-09-09**. Their open instances are still scheduled for 2026-09-10.
- **Migration.** "Migrate unfinished Pomodoro tasks" kept being completed; the latest completion is 2026-09-28.
- **The daily note's `gtd_daily` checkbox.** It was completed on **25 of 31** August days, but only **7 of 29**
  September days, with 21 cancelled.

This is a correlation, not proof, but the mechanism is plain. If the copy step keeps running while the select step
has stopped, the list can only grow. A daily review of 70+ items is expensive enough that skipping it is the
natural response.

The lapse didn't cost hours. Tracked time was about the same before and after 09-09: a mean of 296 min/day in
Sep 1–9 and 285 min/day in Sep 10–28. The distinct task links touched per day fell from a median of 14 to 8.
That fits more churn and less selection, but it also fits longer and deeper sessions, so don't over-read it.

### 2.5 Status labels and intake

- **Status inflation.** There are **47 In Progress `[/]` and 29 Next `[*]` `#task` items** vault-wide, excluding
  `#ref`. The dash's WIP/NEXT chips no longer mean "what I'm doing". At about 5 closures a day, Little's Law
  implies an average active item waits about 15 days, which matches the measured queue ages.
- **Intake outpaces closure.** Counts of `sase*` and `bob*` tasks, including done archives:

  | Month | Created | Closed | Closed ÷ created |
  |---|---|---|---|
  | Jun | 251 | 248 | 0.99 |
  | Jul | 329 | 263 | 0.80 |
  | Aug | 564 | 400 | 0.71 |
  | Sep (to the 29th) | 315 | 148 | **0.47** |

  A daily cap alone cannot absorb this ratio. It needs a weekly prune, which the Obsidian setup no longer has: the
  zorg-era weekly review didn't carry over, and the only weekly repeating task in the vault is non-work.
- **Research reports are a notable inflow.** `__cld` counted 14 open "Read …" tasks and 172 unread `#ref` notes.

**Correction to `__mus` and `__gem`:** the placeholder lines `- [ ] () — NAME` do **not** inflate `dash.md` or
Tasks queries. They have no `#task` tag, and the Tasks global filter is `#task`. The real distortion is
indirect: `task-status-hooks` promotes every *linked* task under an open placeholder to Next.

---

## 3. Diagnosis

### 3.1 One list is doing four jobs

The open part of `## Pomodoros` is currently:

1. **Today's plan.** Cirillo calls this the *To Do Today* sheet.
2. **The inventory of active work.** Cirillo's *Activity Inventory*. `dash`, project notes and a would-be roadmap
   should hold this.
3. **The status source.** `task-status-hooks` reads Next / In Progress from it.
4. **The capture inbox.** `@route:id` and `#name` land new work in it.

Cirillo's own materials keep the To Do Today list, the Activity Inventory and the Records separate. The To Do
Today list is chosen at the start of each day. The Records sheet here, the completed ledger, is in good shape.
The other jobs have merged into one list. Because of jobs 3 and 4, the merge reinforces itself: new work enters
the list automatically, and taking work out of the list demotes it.

### 3.2 Why that feels chaotic

- **The next choice is always expensive.** Every glance re-selects from dozens of visible candidates (`__cdx`).
  The same GOALS links being copied across four consecutive blocks (`__gem`, `__mus`) is a symptom: the plan
  records categories, not the next action.
- **The day always ends "behind".** A list sized at about 10× capacity guarantees every day looks like a failure,
  even a 6-hour day. Shape Up's point applies here: a growing pile feels like being behind "even though we're
  not."
- **The planning fallacy goes unchecked.** People plan from an imagined scenario and underweight how past similar
  days went. The ledger already holds that record (about 5 hours, about 7 blocks, 3–4 themes). An uncapped list
  ignores it.
- **An unsorted pile doesn't relieve the mind the way a plan does.** Masicampo & Baumeister found that a
  *specific* plan for an unfinished goal removes its intrusive, distracting effects. A carried-forward heap of 78
  links is the opposite: a daily reminder of everything still open.
- **Too much work in progress.** Personal Kanban's two rules are *visualize* (the vault already does this, in
  `dash`) and *limit WIP* (missing). Leroy's attention-residue findings add a cost: dozens of half-started threads
  mean there is always residue.

### 3.3 What is *not* a problem

- **Variable block length.** Blocks are Flowtime-like focus sessions, and the evidence doesn't favor forced 25/5
  cycles (§4). The `+N`/`-N`, `se`, and doubled 50-minute blocks are fine as they are.
- **Several links per block.** A mean of about 2.2 links per completed block is what supervising parallel agents
  looks like. Recent fieldwork finds that developers concentrate supervisory effort in *planning* (Park et al.,
  2026). Willison names human review as the bottleneck. Planning a few **themes** and pushing them through review
  fits this work better than one task per pomodoro. The ALL-CAPS names already do that. There are simply too many
  of them open at once.
- **The word "Pomodoro."** It's a house label for a focus block. Renaming the heading would break `bob`, the
  plugin, capture and the tmux status (§1), so the name isn't worth changing.
- **Manual time math.** `__mus` flagged it, but `se`, capture `=X`, and `+N`/`-N` already write and adjust the
  ranges.

---

## 4. Outside evidence, weighed

| Finding | Source | What it implies here |
|---|---|---|
| Keep the inventory, the day's list and the records separate, and choose the day's list each morning | Cirillo, *The Pomodoro Technique* | Split the open queue from the inventory; keep the Records half (the ledger) as is |
| A **closed list**: draw a line under today's list; new work goes to tomorrow unless it's urgent | Forster, *Do It Tomorrow* | Cap the day and don't let capture reopen it |
| People underestimate duration even when they know their past record; tying forecasts to past cases reduces the bias | Buehler, Griffin & Ross 1994 (predicted 33.9 days vs. 55.5 actual; 29.7% finished on time) | Size the plan from the ledger's median, not from ambition |
| A specific plan eliminates the cognitive intrusion of unfinished goals | Masicampo & Baumeister 2011 | One concrete highlight beats a heap of links |
| Implementation intentions ("when X, I do Y") have a medium-to-large effect on goal attainment | Gollwitzer & Sheeran 2006 (94 tests, d ≈ .65) | Write the highlight as a result with a when |
| Ordinary daily planning helps on calm days; **contingency planning** stays effective on high-interruption days | Parke, Weinhardt, Brodsky, Tangirala & DeVoe 2018, *J. Appl. Psych.* 103:300–312 | Add a standing "if blocked → …" rule, because agent failures are routine |
| Limit WIP; lead time = WIP ÷ throughput | Benson & DeMaria Barry, *Personal Kanban*; Little's Law | Keep only a handful of themes active |
| Switching away from unfinished work leaves attention residue; switch costs rise with rule complexity | Leroy 2009; Rubinstein, Meyer & Evans 2001 | Group adjacent blocks by theme and keep few open threads |
| Fixed Pomodoro breaks vs. self-regulated breaks: no reliable performance difference, and self-chosen breaks gave better mood in the newest trial | Biwer et al. 2023 (N = 87); Smits, Wenzel & de Bruin 2025; Göksu, Wiradhany & de Bruin 2026 (N = 176); Albulescu et al. 2022 micro-break meta-analysis (vigor and fatigue benefits, no significant overall performance effect) | Keep variable blocks and take real breaks; don't adopt strict 25/5 |
| One daily **Highlight** of about 60–90 min; a short shutdown ritual; timeboxing a to-do list with about 15 minutes of planning | Knapp & Zeratsky, *Make Time*; Newport; Zao-Sanders (HBR 2018) | A single top line, plus a short daily pick |
| Roadmaps by confidence horizon (Now / Next / Later) instead of dates | Bastow (ProdPad); Shape Up's "bets, not backlogs" | One roadmap note with horizon headings |

**Caveats.**

- Most effects come from lab studies, student samples or experience-sampling studies. None is a trial of this
  exact workflow.
- The vault data is n = 1 and observational.
- The Ivy Lee "$25,000" story is folklore. The transferable idea is the short, ranked, closed list.

---

## 5. Where the reports disagreed, and how that is resolved

| Issue | Positions | Resolution | Why |
|---|---|---|---|
| Where today's plan lives | Separate `## Roadmap` section (`__cdx`, `__gem`); `### Roadmap` / `### Log` sub-sections (`__mus`); capped open entries inside `## Pomodoros` (`__cld`, `__grk`) | **Capped open entries inside `## Pomodoros`**, plus a one-line `highlight::` above the heading | (1) `task-status-hooks` promotes to Next only from open entries in the Pomodoros section, so a separate Roadmap section silently demotes today's picks. (2) Capture and `block-id-prompt` target open entries. (3) `__mus`'s sub-headings break the heading total, because Dataview's `meta(task.section).subpath` becomes `Log`, not `Pomodoros`. `__gem`'s "zero tooling impact" holds for the plugin and `se`, but not for statuses. |
| Where the backlog lives | `dash` / project notes (`__cdx`, `__grk`, `__gem`, `__mus`); a new `roadmap.md` (`__cld`) | **One `roadmap.md`** | Once statuses stop being inflated, `dash` READY is 200+ flat tasks, and picking from that is what lapsed. The themed buckets (`DECKS`, `QUEUE`, `SUDO`, `LATER` …) are the valuable grouping, so move them intact. The in-progress `bob#^better-roadmaps` task already asks for a roadmap / structure note. |
| Daily cap | 1 must-win + 2 + contingency (`__cdx`); 🎯 + ≤4 + GTD (`__cld`); 3 + GTD (`__grk`); 3–5 (`__gem`); ≤6, top 3 marked (`__mus`) | **1 highlight + ≤2 more themes + GTD; ≤ ~10 links; about 200 planned minutes** | Matches the measured 3–4 themes/day, and leaves about 30% for GTD and reactive work. The ~200-minute figure is `__cdx`'s 60–70%-of-median rule. |
| Rename the section | Optional (`__cdx`); cheap (`__mus`) | **Don't rename** | The heading is matched in `bob`, the plugin, capture and tmux. The rename isn't cheap, and nothing is gained. |
| Weekly review | 30 min (`__cld`); defer (`__grk`); 10-min calibration (`__cdx`) | **Yes, 25–50 min** | Closure ran at 0.47 of intake in September. Without a weekly prune, `roadmap.md` becomes the next junk drawer. The vault's own best practice caps a weekly review at 4 pomodoros. |
| Contingency plan | Only `__cdx` | **One standing rule**, written once in the pick ritual, not re-written daily | Parke et al. is the strongest evidence for high-interruption days, and the rule costs nothing to keep. |
| Leftovers at day end | Delete (`__cld`, `__gem`); carry only in-progress 🍅 (`__grk`); keep as plain lines (`__mus`) | **Cut them back into `roadmap.md#Now`** during the morning pick | Nothing is lost, the grouping survives, and it replaces the existing migrate step at the same time of day. |

---

## 6. Options considered

| Option | Verdict |
|---|---|
| A. Status quo, restart the daily review | ✗ The 70-item daily review is exactly what lapsed. The problem is the design, not willpower. |
| B. Strict Cirillo (25/5, one task per pomodoro, void on interrupt) | ✗ Fights the 54% of time spent in ≥50-minute blocks and the reality of agent supervision. Borrow only the three-sheet split. |
| C. Calendar time-blocking of the whole day | ✗ Brittle under agent interruptions, and already `@REJECTED` in `gtd_ideas.md`. The tooling also forbids more than one open timed entry. |
| D. External tracker or app | ✗ Duplicates `[t::]` + Dataview and loses the task links, capture, hooks and tmux integration. |
| E. Pure retrospective log, no plan | ◐ Simplest, but gives no daily compass, and the request asks for better planning. |
| F. Separate `## Roadmap` section above an untouched ledger | ◐ Good idea, wrong place for this tooling (§5). |
| **G. Capped open ledger + highlight line + `roadmap.md` + capture habit + weekly prune** | ✓ **Recommended.** Fewest new parts, and it fits the existing tools. |

---

## 7. Recommended solution

### 7.1 The rule

> **The daily note holds what you did and what you'll do *today*: one highlight, at most two other themes, and
> GTD. Everything else lives in `roadmap.md`. Nothing carries forward automatically, and capture doesn't add to
> today unless you mean today.**

### 7.2 Daily note shape

```markdown
- [*] #task [[gtd_daily]] [created::2026-09-30] ^gtd

highlight:: 🎯 Decide the goals-epic phase order and file its beads — [[sase_goals#^epic-roadmap]]

## Pomodoros (`= …unchanged formula…`)

- [x] (**0735-0810** [t:: 35m]) — GTD
	- 🍅 [[#^gtd]]
- [ ] (**0830-0920** [t:: 50m]) — GOALS
	- [[sase_goals#^epic-roadmap]]
	- [[bob#^better-roadmaps]]
- [ ] () — DECKS
	- [[sase#^card-blocks]]
	- [[sase#^p-key-for-decks]]
```

The rules:

- **The highlight line.**
  - Put it *above* the heading, so the ledger tooling ignores it.
  - Use a plain Dataview inline field (`highlight::`), so you can later query your highlight history.
  - Make it an **outcome with a finish condition**, not a project name.
  - Work it first. It usually takes 2–3 blocks.
- **Open entries.**
  - Keep at most **3 besides GTD**: the highlight's theme plus up to two others.
  - Keep **about 10 task links** in total.
  - Name themes as **today's intent** (`GOALS`, `DECKS`). Inventory labels such as `SASE`, `MISC`, `LATER` and
    `NEW FEATURES` belong in `roadmap.md`.
- **Times.** Fill them in when a block starts (`se`, or capture `=X`), as you do now. Keep one open timed entry
  at a time, which the tooling already requires.
- **Unplanned work.** Genuinely urgent work (relaunches, outages) gets its **own honestly named block when it
  happens** (`RELAUNCH`, `OPS`). It doesn't need a pre-staged bucket. This is Cirillo's "Unplanned & Urgent" and
  Forster's urgent exception.
- **Duplicate links.** Don't copy the same links into every block. Continue the theme; the 🍅 marks and a
  one-line note show what moved.

### 7.3 Rituals

**Morning pick (about 5 minutes).** This replaces three `gtd_daily` items:

- "Migrate unfinished Pomodoro tasks"
- "Review READY tasks", which moves to the weekly review
- "Review WIP + NEXT … plan daily Pomodoros"

Use one task in their place:

> `- [ ] #task Pick today: cut yesterday's open entries into [[roadmap#Now]]; write highlight::; pull ≤2 themes from [[roadmap#Now]]  [repeat:: every day when done]`

- **Standing contingency** (Parke et al.; write it once in the task or `gtd_daily`): *if the highlight is
  blocked on agents, work the next theme or GTD for one block, then reassess*. Don't pull more work in from the
  roadmap.
- **Optional:** write tomorrow's highlight the evening before. This is the vault's own idea `^z-241003-0b`, and it
  is Ivy Lee's night-before list, shrunk to one line.

**During the day.** When a theme finishes, pull the next one from `roadmap#Now`. Don't pre-stage the rest of the
backlog in the daily note.

**Weekly review (25–50 min; add `[repeat:: every week on <day>]`):**

1. **Re-rank `roadmap#Now`** to 5 themes or fewer. These are the week's bets.
2. **Prune.** Cancel, or push to Later, anything 3 or more weeks old that has no 🍅. About 27 of today's links
   would qualify.
3. **Review READY.** This moves here from the daily ritual.
4. **Set a research and reading budget.** Don't launch new research swarms beyond it until the reading queue
   drops.
5. **Look at three numbers:** weekly hours, how often the highlight got at least one 🍅, and created vs. closed.

### 7.4 The capture habit, the change most likely to keep the fix working

- **Not for today:** `@route^block-id` creates an ordinary Ready task with a block ID and **no ledger link**.
- **For today:** `@route:block-id`, optionally with `#THEME`, only when the task belongs to today's highlight or
  one of today's two themes. `=X` starts the block right away.
- **Future grouping:** avoid `#name` for grouping future work, because it creates new future buckets on the
  daily note. Group future work in `roadmap.md` during the weekly review instead.

### 7.5 One-time transition (about 30 minutes)

1. **Create `roadmap.md`.** Per the vault rule, give it `parent:` frontmatter (e.g. `[[gtd]]`) and `## Now`,
   `## Next` and `## Later` headings.
2. **Move today's buckets.** Cut today's open buckets into it **as-is**, in the same `NAME` + link-children shape.
   - Put at most 5 themes in Now.
   - The existing `LATER` bucket goes to Later.
   - Cancel anything you already know you won't do.
3. **Edit `gtd_daily.md`.** Make the swap in §7.3 and add the weekly review task.
4. **Edit `_templates/daily.md`.** Add an empty `highlight:: 🎯 ` line above `## Pomodoros`. Keep the single
   seeded `- [ ] () — GTD` entry.
5. **Expect a one-time drop in statuses.** Within a day or two, `task-status-hooks` will reset most of the 47
   `[/]` and 29 `[*]` tasks to Ready, because they'll no longer be reachable from the ledger. That is intended:
   Next goes back to meaning "today", and `roadmap.md` keeps the rest visible.

### 7.6 Two-week trial (2026-09-30 → 2026-10-13) and decision rule

| Signal | Today | Target |
|---|---|---|
| Peak open named entries on the daily note | 23 | **≤ 4** (GTD + 3) |
| Peak open task links on the daily note | 78 | **≤ ~10** |
| Morning pick completed | 7/29 days in Sep (`gtd_daily`) | **≥ 10 of 14** |
| Days where the highlight got at least one 🍅 | n/a | **≥ 80%** |
| `[/]` + `[*]` vault-wide | 76 | **≤ ~15** |
| Weekly closed ÷ created (sase/bob) | 0.47 (Sep) | **trending toward 1** |

- **Keep the change** if the pick stays under about 5–10 minutes, the next block is usually obvious, and
  nothing piles up on the daily note.
- **If the highlight hit rate is low**, make the highlight smaller or look at the reactive share. If
  `SHIT`/`FIXES`/`RELAUNCH` regularly takes more than about 15%, give it a standing `OPS` theme instead of letting
  it take over the highlight.
- **If the pick keeps lapsing**, shrink `gtd_daily` itself. The only required output is the `highlight::` line.
- **If `roadmap#Later` grows past about 50 items**, prune it hard.
- **If after two weeks the roadmap doesn't reduce the friction of choosing**, drop it and keep the capped ledger
  alone. That is `__grk`'s minimal variant.

### 7.7 Deliberately not built (yet)

- A second time tracker.
- A calendar overlay.
- Strict 25/5 cycles.
- Weekly day-themes.
- Pomodoro sub-sections for LATER (`bob#^pomodoro-sub-sections`); LATER belongs in `roadmap.md`.
- Embedded Tasks queries in the daily note.
- Renaming the heading.

**Optional tooling, only after the habit holds for two weeks.** These would be separate `bob-cli` / `bob-plugins`
work items:

1. **Show plan load** in `bob pomodoro` / `tmux-pomodoro`, e.g. `🎯 · 3/4`, and warn when the day has more than 4
   open entries or more than 10 links.
2. **A capture guard or config** that makes `@route:id` ask before adding to a day that is already at the cap.
3. **A Dataview line** on the daily note showing whether the highlight was touched and planned vs. completed
   entries, to track the hit rate over time.
4. **Only if the "this week" signal is missed:** have `task-status-hooks` treat `roadmap#Now` as a Next source.
   The default recommendation is to let Next mean *today*.

### 7.8 Risks

- **`roadmap.md` becomes the new pile.** The defenses are the Now cap and the weekly prune. At a September intake
  of about 2:1, those defenses aren't optional.
- **Less at-a-glance context in the daily note.** This is deliberate. If you miss it, add `![[roadmap#Now]]` at
  the bottom of the daily note. That shows the options without turning them into commitments.
- **Planning can't fix intake.** The research budget and the capture habit are the real levers on the created ÷
  closed ratio.

---

## Recommended solution (summary)

- **Keep `## Pomodoros` and the whole ledger toolchain unchanged.**
- **Treat the open part as a closed daily list:** one `highlight::` outcome, at most two more themes, and GTD
  (about 10 links, about 200 planned minutes).
- **Move everything else, intact, into one `roadmap.md`** (Now / Next / Later).
- **Replace migrate + review + plan with a 5-minute morning pick** that has a standing "if blocked" rule.
- **Capture non-today work with `@route^id`,** not `@route:id`.
- **Prune weekly.**
- **Trial it for two weeks against the signals in §7.6.**

This is simpler day to day than the current system, and the only new structure is one note and one weekly habit.

---

## Sources

**Local evidence (read-only):**

- `~/bob/2026/2026{06..09}*.md` and their git history
- `~/bob/_templates/daily.md` and `_templates/schedule.md`
- `~/bob/gtd_daily.md` and `done/gtd_daily_done.md`
- `~/bob/gtd.md` and `gtd_ideas.md` (`^z-241003-0b`, `^z-241109-0f`, `^z-241007-0n`, `^z-240410-93`)
- `~/bob/dash.md` and `.obsidian/plugins/obsidian-tasks-plugin/data.json`
- `~/bob/bob.md` (`^better-roadmaps`)
- The `bob-cli` repo: `README.md` (task-status-hooks), `docs/capture.md`, `src/native/task_status_hooks.rs`,
  `src/native/pomodoro.rs`
- The `bob-plugins` repo: `plugins/block-id-prompt/main.js` (`selectPomodoroInsertionTarget`,
  `POMODOROS_HEADING_RE`)

**Methods and research:**

1. Cirillo, F. *The Pomodoro Technique* (Activity Inventory / To Do Today / Records; "Unplanned & Urgent").
   <https://www.pomodorotechnique.com/>
2. Forster, M. *Do It Tomorrow* (closed lists).
   <http://markforster.squarespace.com/blog/2011/1/24/review-of-the-systems-do-it-tomorrow.html>
3. Buehler, R., Griffin, D., & Ross, M. (1994). Exploring the "planning fallacy." *JPSP* 67(3), 366–381.
   <https://doi.org/10.1037/0022-3514.67.3.366>
4. Masicampo, E. J., & Baumeister, R. F. (2011). Consider it done! *JPSP* 101, 667–683.
   <https://pubmed.ncbi.nlm.nih.gov/21688924/>
5. Gollwitzer, P. M., & Sheeran, P. (2006). Implementation intentions and goal achievement: a meta-analysis.
   *Adv. Exp. Soc. Psych.* 38, 69–119. <https://doi.org/10.1016/S0065-2601(06)38002-1>
6. Parke, M. R., Weinhardt, J. M., Brodsky, A., Tangirala, S., & DeVoe, S. E. (2018). When daily planning
   improves employee performance: the importance of planning type, engagement, and interruptions. *J. Appl.
   Psych.* 103(3), 300–312.
   <https://www.semanticscholar.org/paper/When-Daily-Planning-Improves-Employee-Performance:-Parke-Weinhardt/fa6ba765df268030b923aa47bb1ecf632d4731ec>;
   summary: <https://news.mccombs.utexas.edu/research/planning-for-idle-time-and-interruptions/>
7. Benson, J., & DeMaria Barry, T. *Personal Kanban*. <https://personalkanban.com/>; Little's Law in knowledge work
   (Kanban University, 2022):
   <https://kanban.university/wp-content/uploads/2022/09/Exploring-Littles-Law-KGS-2022.pdf>
8. Leroy, S. (2009). Attention residue. *OBHDP* 109(2), 168–181.
   <https://www.sciencedirect.com/science/article/abs/pii/S0749597809000399>
9. Rubinstein, J. S., Meyer, D. E., & Evans, J. E. (2001). Executive control of cognitive processes in task
   switching. <https://pubmed.ncbi.nlm.nih.gov/11518143/>
10. Biwer, F., et al. (2023). Comparing "Pomodoro" breaks and self-regulated breaks. *BJEP* 93(S2).
    <https://pubmed.ncbi.nlm.nih.gov/36859717/>
11. Smits, E., Wenzel, K., & de Bruin, A. (2025). Self-regulated, Pomodoro, and Flowtime break-taking.
    *Behavioral Sciences* 15(7):861. <https://www.mdpi.com/2076-328X/15/7/861>
12. Göksu, A., Wiradhany, W., & de Bruin, A. (2026). When to take a break. *Behavioral Sciences* 16(7):1158.
    <https://doi.org/10.3390/bs16071158>
13. Albulescu, P., et al. (2022). "Give me a break!" Micro-breaks meta-analysis. *PLOS ONE*.
    <https://doi.org/10.1371/journal.pone.0272460>
14. Park, Y. S., et al. (2026). *The Work Behind Delegation: A Framework for Supervising AI Coding Agents*.
    arXiv:2609.24234. <https://arxiv.org/abs/2609.24234>; Willison, S. (2025). Embracing the parallel coding
    agent lifestyle. <https://simonwillison.net/2025/Oct/5/parallel-coding-agents/>
15. Knapp, J., & Zeratsky, J. *Make Time*: the daily Highlight.
    <https://maketime.blog/article/choose-a-highlight-to-make-time-every-day/>
16. Newport, C. The shutdown ritual; time-block planning.
    <https://calnewport.com/drastically-reduce-stress-with-a-work-shutdown-ritual/>
17. Zao-Sanders, M. (2018). How timeboxing works. *HBR*.
    <https://hbr.org/2018/12/how-timeboxing-works-and-why-it-will-make-you-more-productive>
18. Singer, R. *Shape Up*: "Bets, Not Backlogs." <https://basecamp.com/shapeup/2.1-chapter-07>; Bastow, J.
    Now/Next/Later roadmaps. <https://www.prodpad.com/blog/invented-now-next-later-roadmap/>
19. The Ivy Lee method (popular account; the origin story is folklore). <https://jamesclear.com/ivy-lee>
20. Stubblebine, T. Interstitial journaling. <https://nesslabs.com/interstitial-journaling>
