# Daily pomodoro planning: keep the ledger, close the list

**Researcher:** grk
**Date:** 2026-09-29
**Question:** Should the current approach to tracking pomodoros, work, time, and the day's roadmap in Bob daily notes change, and if so, how, while staying as simple as possible?

**Verdict:** Keep the Pomodoros section as a work log. Stop using it as a portable backlog. Plan the day as a **closed list of three named commitments** pulled from `dash`, then timebox them in place with the tooling that already exists. That is a smaller daily file than today's 21 untimed buckets, and it matches how much work a September day actually absorbs.

---

## 1. What the current system already is

The daily note (template `~/bob/_templates/daily.md`, example `~/bob/2026/20260929.md`) is a thin wrapper around one ledger:

```markdown
- [*] #task [[gtd_daily]] ... ^gtd

## Pomodoros (`= durationformat(... sum of completed task.t ...)`)

- [x] (**0735-0800** [t:: 25m]) — GOALS
	- 🍅 [[sase_goals#^epic-roadmap]]
	- 🍅 [[bob#^better-roadmaps]]
- [ ] () — SASE
	- [[sase#^recovery-panel]]
	- ...
```

Five layers sit on that ledger:

| Layer | Role |
|---|---|
| Named block (`— GOALS`) | Theme / intent for a stretch of time |
| Time range + `[t:: Nm]` | Actual minutes, summed in the heading |
| Checkbox | Closed vs still open |
| `🍅` task links | Which project tasks were in play |
| Nested plain bullets | Work log (launched agents, research notes, interruptions) |

Supporting machinery is already built:

- `gtd_daily` recurring ritual: migrate yesterday's unfinished pomodoros; review calendar, email, Keep; review `dash` WIP/NEXT/READY; "plan daily Pomodoros".
- `dash.md`: live WIP / NEXT / READY queries. This is the real next-action list.
- Templater snippet `_templates/schedule.md` (`se`): inserts N sequential `(**HHMM-HHMM** [t:: 25m])` atoms from now.
- Capture and keymaps (`@!`, `^^`, `<ctrl+enter>` close, tomato icons, `=N` increment): start, extend, and close blocks without leaving the note.
- Project notes already carry schedule logs and work logs (`🗓️`, `🛠️`). Daily tomatoes are pointers into that system.

Cirillo's original technique splits work across three sheets: an **Activity Inventory** (everything), a **To Do Today** sheet (today's subset), and an **Unplanned & Urgent** catch for interruptions, with one chosen task per 25-minute indivisible pomodoro ([Cirillo, *The Pomodoro Technique*](https://www.faasafety.gov/files/events/SO/SO15/2024/SO15134204/Cirillo_--_Pomodoro_Technique.pdf)). The Bob daily file currently performs all three jobs in one list.

---

## 2. What September actually looks like

Parsed every `~/bob/2026/202609*.md` Pomodoros section (29 days). Closed days are a clean log. Today's open file is the planning surface, and that is where the chaos lives.

### Throughput

| Metric (Sep 1–29) | Value |
|---|---|
| Completed blocks | 205 |
| Tracked time | 8,200 min ≈ **136.7 h** |
| Mean / median minutes per day | 283 / **300** (range 105–410) |
| Completed blocks per day | **7.1** |
| Unique theme names per day | **3.7** |
| Unique task-links touched per closed day | mean 9.6, median **9** (range 3–18) |
| August (comparison) | 250 blocks, 159 h, ~308 min/day |

A typical day already lands on **about four themes and nine task links in five hours**. That is the empirical capacity of the day. A plan with 21 buckets is several days of work wearing today's date.

### Duration: two natural atoms, plus a long tail

Completed-block durations are bimodal:

- **25–29 min:** 69 blocks (33.7% exactly 25m)
- **50–54 min:** 38 blocks
- **≥50 min:** 38% of all blocks
- **≤15 min:** 11%
- Mean 40 min, median 35 min
- Outliers exist: 115m, 125m, 195m (2026-09-24 TOOLS)

The 25-minute Cirillo atom is the default via `se`, and it is used. The 50-minute "double" is equally native. The long tail is a work log of flow and firefighting, not a timer failure. Forcing every block back to 25 minutes would fight the data.

Gaps between consecutive completed blocks: median 30 min. 61 of 175 positive gaps are ≤10 min (short breaks); 40 are >90 min (lunch / life). The day already has a pulse. It does not need an hour-by-hour Google Calendar overlay — an idea already marked `@REJECTED` in `gtd_ideas.md` as too much noise on `gcal`.

### Themes: a few do the work, several are junk drawers

Completed-block minutes by name (top):

| Theme | Minutes | Hours |
|---|---|---|
| GTD | 1,510 | 25.2 |
| SHIT | 795 | 13.2 |
| REMOTE | 675 | 11.2 |
| SASE | 590 | 9.8 |
| TOOL / TOOLS | 595 | 9.9 |
| BOB | 305 | 5.1 |
| GOALS | 280 | 4.7 |

`GTD` is both the morning ritual and a catch-all (2026-09-22 "GTD" blocks contain `sase#^clean-core` and `sase#^dot-separators`). `SHIT`, `MISC`, `SASE`, `LATER`, and `NEW FEATURES` name a taxonomy of the whole project, not an intention for the next two hours.

Consecutive same-name runs: median length **1**, mean 1.71, 60% of runs are a single block. Theme names often change every block even when the underlying task links persist.

Inside a block: mean **2.5** child bullets, **1.43** tomatoes. 15.6% of completed blocks carry three or more tomatoes. 17% carry none (prose / relaunch / "random sase shit"). Cirillo's rule is one chosen activity per pomodoro; the ledger currently lets several live tasks ride along.

### The parking lot is a planning act

| | Closed days (Sep 1–28) | Today (Sep 29, mid-day) |
|---|---|---|
| Untimed open buckets | **0** | **21** |
| Open timed block | 0 | 1 (GOALS 1235–1300) |
| Completed so far | — | 3 blocks, 115 min, 1 theme |

Yesterday (2026-09-28) ended as ten completed, named, timed blocks and nothing else. Today's 21 untimed buckets (`GOALS`, `GTD`, `SASE`, `DECKS`, `READ`, `MISC`, `FINAL`, `RENAME`, `BOB`, `TOOL`, `CLEANUP`, `REMOTE`, `SERVICE`, `NEW FEATURES`, `SUDO`, `FAST TESTS`, `QUEUE`, `SCHEDULE`, `AUDIT MEMORY`, `GATES`, `LATER`) were added as a plan. They are the remaining SASE/Bob inventory copied onto the day.

Closed days look orderly because unfinished buckets either get completed, get dropped, or get copied forward onto the live day. The feeling of chaos is the live day, where the ledger is asked to be inventory, roadmap, and log at once.

### The planning ritual is the part that slipped

`gtd_daily` checkbox on the daily note:

| Month | completed `[x]` | cancelled `[-]` | other |
|---|---|---|---|
| August | **25 / 31** | 6 | 0 |
| September | **7 / 29** | 21 | 1 in progress today |

The daily file's only explicit planning step — "Review WIP + NEXT and plan daily Pomodoros" — was cancelled most of September. The 21-bucket dump is what planning looks like when it happens without a size cap. The rest of the month, work was logged as it occurred, which is why closed days still show ~5 h of real work.

An older idea in `gtd_ideas.md` already named the missing piece: "Start creating day plan EVERY night" (`^z-241003-0b`), with a later hesitation about ticklers and `needs_attn`. Another: "Start writing down 3 top weekly priorities AND 3 top daily priorities" (`^z-241109-0f`), inspired by *The Productivity Project*. A third: cap the GTD pomodoro at 60 minutes (`^z-241007-0n`). The vault has been circling a short, capped daily plan for two years. The current file just never enforced the cap.

---

## 3. Diagnosis

The logging format is doing its job. The planning contract is not.

**Three jobs, one list.** Cirillo separates Activity Inventory / To Do Today / Unplanned & Urgent. GTD separates lists (next actions, by context) from the calendar (time-specific commitments). `dash` already is the inventory. The daily Pomodoros section is the calendar. Copying inventory onto the calendar recreates the "Main List" problem Laura Vanderkam warns about in *Off the Clock* / *Uptime*: working from the full list spends energy on items you have no intention of doing today (`lit/uptime.md`, `^uptime_themes`).

**No WIP limit.** Personal Kanban's second practice is "limit work-in-progress" (Benson & Barry, *Personal Kanban*). A personal WIP of 3 is the usual starting cap. September's completed days already average 3.7 themes. Today's 21 open buckets are a WIP of 21. The system visualizes work and then refuses to limit it.

**Migration without a filter.** Bullet Journal migration is a *filter*: at the boundary of a day or month you rewrite only what still deserves a slot; what you decline to migrate was never important enough (Carroll, *The Bullet Journal Method*). The `gtd_daily` line "Migrate unfinished Pomodoro tasks from yesterday" is copy-forward. Combined with a bulk dump of remaining project tomatoes, it grows a parking lot. Project notes and `dash` already retain those tasks. The daily file does not need to.

**Attention residue on unfinished companions.** Sophie Leroy's experiments show that switching away from an unfinished task leaves "attention residue" that degrades the next task; residue shrinks when the first task is finished or when a concrete plan for finishing it is formed (Leroy, 2009, *Organizational Behavior and Human Decision Processes*, 109(2), 168–181). A block with three live tomatoes is three unfinished goal structures in working memory. A 21-bucket open list is a page of Zeigarnik hooks.

**Planning fallacy on the live page.** People generate a future-scenario of the day and underweight how similar days actually went (Buehler, Griffin & Ross, 1994, *Journal of Personality and Social Psychology*, 67(3), 366–381; Kahneman & Tversky, 1979). Connecting the prediction to past completion times reduced the bias in Buehler's Study 4. September's past completion times say: ~5 hours, ~7 blocks, ~4 themes, ~9 links. A plan of 21 buckets ignores that base rate.

**Theme names after the fact.** On closed days, names often describe what happened (`RELAUNCH`, `SHIT`, `CAPTURE`) more than they constrain what will happen. That is fine for a log. It is a weak roadmap.

---

## 4. Methods mapped onto this vault

Each method below is evaluated against the existing ledger, `dash`, and September's capacity. None of them require a new app.

### Cirillo Pomodoro (keep the atom, drop the purity)

Keep: visible remaining time, record interruptions, 25-minute default via `se`, short breaks that already appear as 5–10 min gaps. Drop as mandatory: voiding a block that runs 35 or 50 minutes; one-task-or-void; four-pomodoro long-break ritual. The 50-minute double is a first-class citizen in this corpus. Cirillo's *useful* split is the three sheets. Implement that split with `dash` (inventory) vs daily (today) vs a single unplanned block when agents fail overnight.

### Ivy Lee's six (too many tasks, right shape)

The method associated with Ivy Lee and Bethlehem Steel (popular account: [James Clear](https://jamesclear.com/ivy-lee); Wikipedia notes the $25,000 anecdote is thinly sourced) is: the night before, list at most six tasks, rank them, work in order, do not start #2 until #1 is done, rewrite a fresh six tomorrow. The active ingredient is the **hard cap** and the **night-before decision**. Six *tasks* is still wide for this corpus (median 9 links/day already). Three *themes* with two links each lands on the observed nine.

### Make Time "Highlight" (too tight as a hard rule)

Knapp & Zeratsky: pick one Highlight for the day, then Laser / Energize / Reflect. Useful as a *first* line (`Today: GOALS`). Too tight as the only allowed work: relaunches, GTD, and a second project already take real hours (REMOTE 11h, GTD 25h this month). Use Highlight as the top of three, not as the whole day.

### Chris Bailey's three daily intentions (already in the vault)

`gtd_ideas.md` `^z-241109-0f` proposed three daily + three weekly priorities for work and personal life. September's 3.7 themes/day is the empirical vote for **three**. Adopt the daily half. Defer the weekly-themes experiment (`^z-240921-0f` / `uptime_themes`); it adds a second cadence before the daily cap is in place.

### Timeboxing (Zao-Sanders) and time blocking (Newport)

[HBR, Dec 2018](https://hbr.org/2018/12/how-timeboxing-works-and-why-it-will-make-you-more-productive): put the to-do list onto the calendar; one thing in the box; "15 minutes of planning to shape the next 15 hours." Newport's calendar blocking is the same family, with a shutdown ritual. The daily Pomodoros section **is** that calendar. Putting the same boxes on Google Calendar was already rejected. Do the 15-minute plan inside the existing GTD pomodoro (cap 25–50 min, per `^z-241007-0n`). Fill times with `se` when sitting down, because that is already how times get written.

Zao-Sanders distinguishes time-*blocking* (reserve focus) from time-*boxing* (reserve focus **and** accept "good enough" when the box ends). For agent-orchestration work, the box ending is a check-in ("did the swarm land?") more often than "the code is done." That matches how tomatoes already persist across several blocks.

### GTD daily review (restore, do not enlarge)

Allen: the calendar holds time-specific items; next-action lists hold the rest; the weekly review keeps the lists honest. The September failure is skipping the daily review (`gtd_daily` cancelled 21/29 days) and then compensating by pasting the lists onto the day. Completing `gtd_daily` as a 25-minute box, then writing three commitments, is the GTD-shaped fix. A weekly review already has a vault best-practice cap of four pomodoros (`gtd.md` `^z-240410-93`).

### Bullet Journal migration (filter, do not photocopy)

End of day: keep completed blocks (they are the log). Carry forward only tomatoes that still have `🍅` and are actually in progress. Delete unused untimed buckets. The tasks remain in `dash` / project notes. This also makes `bob#^pomodoro-sub-sections` (send groups to LATER) unnecessary as a daily-file feature; LATER belongs on the project note.

### Personal Kanban WIP = 3

Visualize (already), limit WIP (missing), pull (already, via tomatoes). Cap open untimed buckets at 3 (+ the GTD ritual). When one theme finishes, pull the next from `dash`. Do not pre-stage the pull of the entire backlog.

### Mark Forster closed lists

A closed list may not grow once the day starts, except for true unplanned-urgent items (failed overnight agents, a bee attack). That is the rule that makes a 3-item plan survivable. Interruptions become a new timed block with a honest name (`RELAUNCH`, `OPS`), which is already how 2026-09-28 0525–0630 and 2026-09-25 1840–2000 were logged.

---

## 5. Options (what a change could look like)

**A. Status quo.** Keep logging as-is; keep dumping remaining tomatoes onto today when planning happens. Cost: the live day's roadmap is unreadable; `gtd_daily` stays skippable; attention residue from a page of open buckets. Benefit: zero process change; closed days already look fine.

**B. Strict Cirillo.** 25-minute indivisible blocks, one tomato, void on interrupt, 5-min / 15–30-min breaks. Cost: fights the 50-minute double and the 10–15 minute ops slices that are real work. Benefit: cleaner estimates.

**C. Full calendar timeboxing on Google Calendar.** Already rejected in-vault. Would duplicate the daily ledger.

**D. New tracker (Toggl, Timing, a dedicated pomodoro app).** The `[t::]` field plus Dataview already produces a daily total. A second store would drift from the tomato links that make the log useful.

**E. Night-before six-item Ivy Lee list in a new heading, Pomodoros stay a pure log.** Better than A. Still allows six independent tasks, which is more switching than the 3.7-theme base rate.

**F. Closed list of three named commitments on the daily file, log as today, pull extras from `dash` only after a commitment finishes.** Matches capacity, uses existing tools, shrinks the live page. Small template change.

**G. One Highlight only.** Excellent first line, insufficient for a day that already spends hours on ops + GTD + a second project.

**F is the recommended option.** It is simpler than today's 21-bucket plan and leaves the ledger, query, keymaps, and `dash` in place.

---

## 6. Recommended solution

### The rule (one sentence)

**Today's daily file may contain at most three untimed named commitments plus GTD; times are filled when a block starts; unused buckets are deleted at close of day; everything else lives on `dash`.**

### Daily shape

```markdown
- [*] #task [[gtd_daily]] ... ^gtd

## Today
GOALS · BOB · DECKS

## Pomodoros (`= ...existing query...`)

- [ ] () — GTD
	- [[#^gtd]]
- [ ] () — GOALS
	- [[sase_goals#^epic-roadmap]]
- [ ] () — BOB
	- [[bob#^better-roadmaps]]
- [ ] () — DECKS
	- [[sase#^card-blocks]]
```

That is the entire plan. Four open checkboxes at the start of the day, not twenty-two.

When work starts, `se` (or the existing start-pomodoro capture) fills `(**HHMM-HHMM** [t:: 25m])`. If the work runs long, extend with `=N` / `\p` as today. If a second 25 is needed on the same theme, close and `se` again — or keep one 50-minute block. Both are already in the data; both are allowed.

### Operating rules

1. **Plan inside GTD, 25 minutes, once.** Restore `gtd_daily` as a real pomodoro (the Zao-Sanders 15/15, using the existing 25m atom). The output of that pomodoro is the `## Today` line and at most three untimed buckets. If GTD is not done by 50 minutes, stop and finish on the evening pass (`^z-241007-0n`). Cancelling `gtd_daily` is how the parking lot returns.

2. **Pull from `dash`, do not photocopy it.** WIP and NEXT already exist. The daily file gets the three you mean to advance. READY stays on `dash`.

3. **One primary tomato per timed block.** A second link may sit underneath as context (the same epic, a blocker you hit). A third is a smell: close the block or park the extra back to `dash`. This is the Leroy lever.

4. **Closed list after planning.** New work enters as a *new timed block* with a true name (`RELAUNCH`, `OPS`, `EMAIL`) when it is actually happening. It does not get pre-staged as `LATER` / `MISC` / `NEW FEATURES` on today's page.

5. **End of day is a filter.** Keep every completed timed block (the log is the point). Carry forward only in-progress tomatoes (`🍅` still on an unfinished commitment). Delete unused untimed buckets. Tomorrow's three are chosen fresh, Ivy Lee style, from `dash` plus whatever actually rolled.

6. **Name themes as today's intent.** `GOALS`, `DECKS`, `CAPTURE` earn their place. `SASE`, `SHIT`, `MISC`, `LATER`, `NEW FEATURES` are inventory labels; they belong on project notes. `GTD` means the ritual, not "whatever was in front of me."

7. **Keep flexible duration.** Default 25 via `se`. Doubles (50) are normal. A 10-minute ops slice is a real log entry. A 3-hour glued block is a log of flow; split it next time only if you want cleaner totals, not because Cirillo said so.

### Template change (small)

In `_templates/daily.md`, after the GTD task, add:

```markdown
## Today
<!-- three names, filled during gtd_daily -->

## Pomodoros (`= durationformat(...)`)

- [ ] () — GTD
	- [[#^gtd]]
```

Do not seed SASE/BOB/LATER buckets. Empty is the correct starting state; `gtd_daily` fills it.

Optional later (only if the cap holds for two weeks): a Dataview / Tasks query that **shows** WIP+NEXT without copying them, e.g. a collapsed callout under `## Today`. Showing is compatible with a closed list. Copying is not.

### What stays

- `[t::]` + heading total
- Tomato links into project notes
- Work-log nested bullets
- `se`, `@!`, `^^`, `<ctrl+enter>`, tomato icons
- `dash` as the live inventory
- Project-note schedule/work logs
- Overnight relaunch as its own timed block when it happens

### What does not get built

- Pomodoro sub-sections for LATER (`bob.md` `^` pomodoro sub-sections): the daily file should not be where LATER lives.
- Google Calendar ideal-day overlay.
- A second time tracker.
- Weekly day-themes, until the daily cap is habitual.
- Auto-migrating every unfinished bucket.

---

## 7. Why this is simpler, and why more complexity is unwarranted

Today's live file is complex because it is large. A four-checkbox plan plus a growing log is less to look at, less to migrate, and less to decide among. The heavy tooling (capture, tomatoes, Dataview, `dash`) stays; the missing piece is a **size rule**.

More structure (hour-by-hour GCal, strict 25s, a new app, weekly theme days, six ranked tasks, auto-collected work-log notes) would add moving parts before the WIP limit exists. September already produces 5 hours of tracked work on days when `gtd_daily` is cancelled. Output is not the bottleneck. Choosing, and then staying with the choice for a couple of blocks, is.

---

## 8. Two-week trial

Run F as written, 2026-09-30 through 2026-10-13. Success if all three hold:

| Signal | Pass |
|---|---|
| Open untimed buckets on the live daily file | ≤ 4 at any snapshot (GTD + 3) |
| `gtd_daily` completed (not cancelled) | ≥ 10 of 14 days |
| Unique completed theme names per day | median ≤ 5 (today's base rate is 3.7; room for ops) |

If the cap is painful because ops (relaunch, outages) eat the three slots, add a standing fourth name `OPS` rather than reopening the inventory. If GTD still gets cancelled, shrink `gtd_daily` itself (weather/pills/email can stay; the only required output is the `## Today` line). If three themes feel starved, the September median of nine links/day says the starvation is the point.

After two weeks, look at the closed daily files the way this report looked at September: minutes, theme count, tomatoes per block. The log will say whether the cap was real.

---

## 9. Sources

### This vault (primary evidence)

- Daily notes `~/bob/2026/20260901.md` … `20260929.md` (parsed for status, `[t::]`, theme names, tomatoes, links, gaps)
- `~/bob/_templates/daily.md`, `~/bob/_templates/schedule.md`
- `~/bob/gtd_daily.md`, `~/bob/gtd.md`, `~/bob/gtd_ideas.md`, `~/bob/dash.md`
- `~/bob/bob.md` (capture/pomodoro tooling and the better-roadmaps / sub-sections tasks)
- `~/bob/lit/uptime.md` (`uptime_themes`, daily list vs main list)
- `~/bob/pomodoro.md` (legacy zorg rollover inventory — a previous generation of the same parking-lot problem)

### Methods and research

- Francesco Cirillo, *The Pomodoro Technique* (core process, To Do Today vs Activity Inventory, indivisible 25, interruption apostrophes). PDF commonly circulated from the 2006 text: [FAA copy](https://www.faasafety.gov/files/events/SO/SO15/2024/SO15134204/Cirillo_--_Pomodoro_Technique.pdf).
- Sophie Leroy (2009). "Why is it so hard to do my work? The challenge of attention residue when switching between work tasks." *Organizational Behavior and Human Decision Processes* 109(2), 168–181. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0749597809000399).
- Roger Buehler, Dale Griffin & Michael Ross (1994). "Exploring the 'planning fallacy'." *Journal of Personality and Social Psychology* 67(3), 366–381. [APA record](https://psycnet.apa.org/record/1995-04284-001).
- Daniel Kahneman & Amos Tversky (1979). "Intuitive prediction: Biases and corrective procedures." The source of the term *planning fallacy*.
- Marc Zao-Sanders (2018). "How Timeboxing Works and Why It Will Make You More Productive." *Harvard Business Review*, 12 Dec 2018. [hbr.org](https://hbr.org/2018/12/how-timeboxing-works-and-why-it-will-make-you-more-productive). Follow-up: *Timeboxing* (Penguin, 2024); "15/15" planning window.
- Ivy Lee method, popular account: [James Clear](https://jamesclear.com/ivy-lee). Historical caution: the Schwab/$25,000 story is late and weakly sourced; the six-item closed list is the transferable idea.
- Ryder Carroll, *The Bullet Journal Method* — migration as a filter. [bulletjournal.com](https://bulletjournal.com).
- Jim Benson & Tonianne DeMaria Barry, *Personal Kanban* — visualize work, limit WIP.
- Jake Knapp & John Zeratsky, *Make Time* — one Highlight per day.
- Chris Bailey, *The Productivity Project* — three daily intentions (already cited in `gtd_ideas.md`).
- David Allen, *Getting Things Done* — calendar vs next-action lists; weekly review.
- Cal Newport, *Deep Work* / *Slow Productivity* — time blocking and obligation caps. Use the daily file as the block calendar; skip a second calendar.
- Mark Forster, *Do It Tomorrow* — closed lists.
- Gloria Mark, Daniela Gudith & Ulrich Klocke (2008). "The cost of interrupted work: more speed and stress." CHI 2008. Companion evidence that interrupted work feels faster and costs more.
- Bluma Zeigarnik (1927) — incomplete tasks remain more available in memory; the open 21-bucket page is a designed Zeigarnik field.

---

## 10. Direct answer

Change the **planning contract**. Keep the **log**.

The chaos is the live daily file doing inventory's job. September already shows the right size of a day: about five hours, seven blocks, four names, nine links. Write three of those names under `## Today` during a 25-minute GTD pomodoro, timebox them with `se` as you sit down, and let `dash` hold the rest. That is the smallest change that makes the roadmap for the day match the day you actually have.
