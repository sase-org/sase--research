# A simpler daily roadmap for Pomodoros and work tracking

**Research date:** 2026-09-29  
**Question:** Should Bryan change how the `Pomodoros` section in daily Obsidian notes tracks work, time, and the day's roadmap?

## Executive conclusion

Yes, but only one structural change is warranted: **separate the short list of today's commitments from the chronological record of work actually done**.

The existing log is already valuable. It records exact start/end times, durations, project context, links to canonical tasks, interruptions, and occasional outcomes. That is useful behavioral evidence and is much better than reconstructing the day from memory. The problem appears when the same section is also asked to be the day's entire roadmap. In `20260929.md`, three completed rows sit above 22 open planning rows containing 77 prospective links. The result is not really a plan; it is a second view of the backlog, embedded inside the work log.

The recommended system therefore has only two layers:

1. A four-line `Roadmap`: one must-win outcome, up to two next outcomes, and one fallback/contingency.
2. The existing `Pomodoros` section as an append-only log of actual sessions—not a place to preload candidate work.

No new app, scoring system, or strict 25-minute regime is needed.

## What the current notes show

I reviewed the named example (`2026/20260929.md`) and the `Pomodoros` sections for September 22–28. This is a small observational sample, not a productivity experiment, but it is enough to identify the structural issue.

### The normal pattern is already coherent

Across September 22–28, the notes contain:

- 48 completed work-session rows;
- 2,245 logged minutes, or 37h25m total;
- a median of 320 logged minutes per day (5h20m);
- a median session length of 40 minutes, with sessions ranging from 10 to 195 minutes; and
- 5–10 completed rows per day.

These entries function well as a lightweight time diary. They also reveal that “Pomodoro” is being used as a broad label for focus/work sessions rather than the strict 25-minute technique. That is not inherently a problem; the recorded duration is more informative than the label.

### The September 29 pattern is qualitatively different

At the time inspected, `20260929.md` contained three completed rows totaling 115 minutes, one scheduled-but-incomplete 25-minute row, and 21 additional open category rows. The 22 open rows collectively exposed 77 links, including large `SASE`, `QUEUE`, `AUDIT MEMORY`, `GATES`, and `LATER` collections.

This creates three costs:

- **Selection cost:** the next action must be chosen again from dozens of visible candidates.
- **False commitment:** an unchecked row in a daily note visually implies “today,” even when its label is `LATER`.
- **Measurement ambiguity:** completed rows are historical facts, while unchecked rows mix scheduled work, options, categories, and backlog. One checkbox syntax is carrying several meanings.

The issue is therefore not insufficient tracking. It is insufficient separation between **inventory**, **commitment**, and **record**.

## What the research supports

### 1. Keep inventory separate from today's commitments

The official Pomodoro materials themselves use separate artifacts: an Activity Inventory for all tasks, a To-Do Today sheet for selected commitments, and Records for completed intervals. The stated workflow is to select from the inventory for today and use records to improve estimation ([official Pomodoro overview](https://www.pomodorotechnique.com/); [Activity Inventory](https://www.pomodorotechnique.com/solutions/pomodoro-activity-inventory-esheet/)).

The current project/task notes already serve as the inventory. Copying their contents into the daily note adds another queue without adding authority or clarity. The daily note should link to selected canonical tasks, not reproduce the choice set.

### 2. Plans help when they are specific, not merely comprehensive

In a meta-analysis of 94 independent tests, implementation intentions—plans that bind a concrete situation to an action—had a medium-to-large effect on goal attainment (`d = .65`) ([Gollwitzer & Sheeran, 2006](https://doi.org/10.1016/S0065-2601(06)38002-1)). Separate experiments found that unfulfilled goals produced intrusive thoughts and impaired performance on another task, while making specific, credible plans eliminated those interference effects ([Masicampo & Baumeister, 2011](https://pubmed.ncbi.nlm.nih.gov/21688924/)).

This does **not** imply that listing every open loop in today's note will quiet the mind. The active ingredient was a specific plan that participants meant to execute. A line such as “After breakfast, spend the first two focus units producing the epic-roadmap decision” is closer to that evidence than 77 links grouped under broad categories.

### 3. A daily plan should include disruption, not pretend it will not occur

A two-week experience-sampling study distinguished ordinary time-management planning (task lists, priorities, how/when) from contingency planning (anticipating interruptions and deciding how to respond). Ordinary planning was associated with engagement and performance when interruptions were low; its benefit weakened with many interruptions. Contingency planning was more robust under interruption ([Parke et al., 2018](https://pubmed.ncbi.nlm.nih.gov/29154579/)).

That maps closely to the notes, which repeatedly mention failed agents, relaunches, outages, waiting, and other operational surprises. A useful daily roadmap should reserve capacity and name a fallback such as “If the primary task is blocked on an agent, do GTD or the selected low-context task.” It should not schedule the full observed capacity as though the day were deterministic.

### 4. Use the work log as a reference class for future capacity

People commonly underestimate completion time by focusing on the imagined plan instead of relevant past experience; in one experiment, prompting people to connect estimates to past experience eliminated the optimistic bias ([Buehler, Griffin, & Ross, 1994](https://doi.org/10.1037/0022-3514.67.3.366)).

The existing logs provide exactly the missing reference class. The seven-day median is about 320 logged minutes. A conservative first capacity rule is to commit only 60–70% of that amount—about 190–225 minutes—and leave the rest for interruptions, coordination, recovery, and opportunistic work. This is a starting hypothesis, not a universal productivity ratio; two weeks of planned-versus-actual data should refine it.

### 5. Reduce needless switching, but do not fetishize one interval length

Laboratory experiments reliably find measurable switching costs when people alternate task rules, especially as rule complexity increases ([Rubinstein, Meyer, & Evans, 2001](https://pubmed.ncbi.nlm.nih.gov/11518143/)). This supports grouping adjacent sessions around the same outcome and limiting the number of active daily outcomes. It does not support popular claims that every software-context switch costs a fixed number of minutes.

Nor is 25 minutes a scientifically privileged focus duration. A meta-analysis of micro-breaks found benefits for vigor and fatigue, but no statistically significant overall performance effect; longer breaks were associated with larger performance benefits, and effects varied by task type ([Albulescu et al., 2022](https://doi.org/10.1371/journal.pone.0272460)). The practical conclusion is to keep real breaks and use the interval that fits the work. Bryan's own median session is 40 minutes and many entries are 50 minutes, so 25-minute units may help with initiation or chores while 50-minute units may better fit development work.

## Alternatives considered

### Leave the system unchanged

This preserves simplicity and the strong historical log, but leaves the daily note vulnerable to becoming a backlog dashboard. It is reasonable on days when only actual sessions are logged, but September 29 demonstrates that the system has no guardrail against option sprawl.

### Adopt strict Pomodoro (25/5, four rounds, long break)

This would make the name and behavior consistent, and scheduled breaks may improve well-being. It would also fight the observed work style: many productive sessions naturally run 40–90 minutes. There is insufficient evidence that strict 25-minute cuts would improve this particular workflow. Do not adopt this unless fatigue or failure to start is the primary problem.

### Time-block the entire day on a calendar

This can make commitments concrete, but it adds maintenance and becomes brittle in an interruption-heavy agent/software environment. Calendar blocking is appropriate for externally constrained appointments or a protected primary block, not for every candidate task.

### Add automatic activity tracking or richer analytics

This would increase measurement while leaving the selection problem untouched. The current manual log already supplies enough data to calibrate capacity. More telemetry is not warranted until a specific unanswered question emerges.

## Proposed format

Keep links pointing to the canonical tasks. Add one small section before the existing log:

```markdown
## Roadmap

- **Must win:** [[sase_goals#^epic-roadmap]] — finish <specific day's result>
- **Then:** [[bob#^better-roadmaps]] — decide <specific question>
- **Then:** [[sase_agent_history#^read-research]] — extract <specific output>
- **If blocked / low energy:** [[#^gtd]] for one focus unit

## Pomodoros (`= <existing duration formula>`)

- [x] (**0735-0800** [t:: 25m]) — GOALS
  - [[sase_goals#^epic-roadmap]] — <result or next action>
```

Operational rules:

1. **Plan in five minutes or less.** Choose one must-win result and zero to two “then” results. Each line needs a visible finish condition or next action, not just a project name.
2. **Plan only about 200 minutes initially.** That is four 50-minute units or eight 25-minute units, against the recent 320-minute median. The remaining capacity is deliberate flex, not failure.
3. **Append log rows only after starting or completing real work.** Do not create empty category rows in `Pomodoros`. A future scheduled block belongs in `Roadmap` or the calendar.
4. **Stay with one outcome across adjacent units when useful.** Reorder the roadmap explicitly if reality changes rather than sampling repeatedly from the backlog.
5. **Use one contingency.** For example: “If blocked on an agent, switch to GTD for one unit, then reassess.” This is enough; a full alternate day is another backlog.
6. **Close in two minutes.** Add the next concrete action to any unfinished must-win item. Do not roll a mass of unchecked rows forward.
7. **Review once a week for ten minutes.** Compare planned units with actual logged minutes, count must-win completion, and note the main source of unplanned work. Adjust planned capacity from observed history rather than adding categories.

The `Pomodoros` heading can remain for compatibility with the Dataview formula. If the terminology feels misleading, rename it later to `Work Sessions`, but update the section predicate in the duration formula and any cross-note queries at the same time.

## Two-week trial and decision rule

Run the proposed format for ten working days. Avoid changing any other tooling during the trial. At shutdown, record only three tiny observations:

- Did the must-win result finish? (`yes`, `partial`, or `no`)
- How many planned focus units versus actual logged minutes?
- What displaced the plan, if anything? (one short phrase)

Keep the change if morning planning remains under five minutes, the next task is usually obvious, and the daily roadmap stops accumulating rollover. If must-win completion is repeatedly low, shrink the finish condition or reduce committed units; do not add more candidates. If the roadmap provides no noticeable reduction in selection friction after ten days, remove it and retain the pure work log.

## Recommended solution

**Adopt the two-layer format for a two-week trial: a four-line `Roadmap` (one must-win, up to two next outcomes, one contingency) followed by the existing append-only `Pomodoros` work log. Keep the project notes as the sole backlog, preload no unchecked work-log rows, and initially commit about 200 of the historically typical 320 logged minutes. Use either 25- or 50-minute focus units according to the task, take real breaks, and recalibrate weekly from the log.**
