# Pomodoro / day-roadmap tracking in Obsidian daily files — research (`__mus`)

## What I looked at

- Today's file `~/bob/2026/20260929.md` (mid-day state: 3 blocks done, 1 in progress, 22 open).
- The daily template `~/bob/_templates/daily.md` (seeds exactly one block: `- [ ] () — GTD`).
- Closed days 20260920–20260928 via read-only Dataview (`bob query`): every finished day ends with **0 open / 5–10 completed** Pomodoro blocks; today is the outlier at **22 open / 3 done**.
- `~/bob/dash.md` (task dashboard) and the section-header total formula.

| Day | Open blocks | Completed blocks |
| --- | --- | --- |
| 20260920–27 | 0 each day | 5–7 each day |
| 20260928 | 0 | 10 |
| 20260929 (mid-day) | 22 | 3 |

## How the current method actually works

1. **Morning brain-dump.** The whole backlog (~25 blocks on 09-29: GTD, SASE, DECKS, READ, MISC, FINAL, RENAME, BOB, TOOL, CLEANUP, REMOTE, SERVICE, NEW FEATURES, SUDO, FAST TESTS, QUEUE, SCHEDULE, AUDIT MEMORY, GATES, LATER) is pasted into the day as empty `- [ ] () — THEME` blocks carrying dozens of bead links.
2. **Intraday conversion.** As work happens, a block gets hand-typed times (`(**0735-0800** [t:: 25m])`), is checked off, and its bead links get outcome marks (`🍅` = worked, `~~struck~~` = finished) plus free-text notes (`Launched sase-1c1!`).
3. **Evening cleanup.** Unworked planned blocks are deleted, so closed days show 0 open. (Hand-summed 09-28: 65+25+25+25+35+25+10+60+25+25 = 320m ≈ 5h20m tracked.)

## Diagnosis: what is working vs. what is chaotic

**Working — keep:**
- The append-only completed log with outcome notes is the valuable artifact (e.g. 09-28's `Launched sase-1c1!`, RESEARCH links). It is a genuine "done list" and worth preserving.
- The header total formula works and only counts completed `[t::]` blocks, so empty planned blocks don't corrupt the total.
- Closed days are clean; the chaos is bounded to the current day.

**Chaotic — fix:**
1. **The daily file duplicates the backlog.** ~22 empty blocks restate what beads/sase_goals already track. Morning setup cost is high and the intraday file is a wall of unchecked boxes that must be scanned to find "what's next."
2. **Open planning blocks pollute task queries.** Every `- [ ]` line is a live task visible to the Tasks plugin and potentially the dash counts; 22 of them are scaffolding, not tasks.
3. **`🍅` marks beads, not pomodoros.** Blocks range 10–85m, so this is timeboxing mislabeled as pomodoros: no fixed 25m unit, no break rhythm, no per-pomodoro count. Fine in itself, but the label invites the wrong technique.
4. **Copy-paste intentions.** The same 3 GOALS links repeat verbatim across 4 consecutive blocks on 09-29 — the plan records categories, not the specific next action, so "what do I do right now" still requires re-deciding.
5. **Manual time math.** Every block hand-computes `END-START = [t:: Nm]`; small but repeated friction, occasionally inconsistent.
6. **No MIT / ordering.** ~20 equally-weighted blocks mean no statement of "these 3 matter today"; prioritization is re-done from scratch each glance.

## Options considered

- **A. Keep as-is.** Zero change cost, but keeps the morning-dump + evening-delete cycle and the 22-open-boxes intraday noise. Rejected as the status quo the request complains about.
- **B. Pomodoro purism (strict 25/5, count 🍅 per unit).** Adds the most structure and the most overhead (timer discipline, break logging); mismatched to observed 10–85m natural work rhythms and agent-driven work with long waits. Rejected.
- **C. External time tracker (Toggl etc.).** Best Serializable time data, but splits the system across tools and abandons the in-Obsidian log that already works. Rejected given the "keep it simple" constraint.
- **D. Plan/Log split (recommended).** Keep the completed-log half exactly as-is; replace the ~22 empty checkbox blocks with a short plain-link roadmap. Minimal change, removes all six problems above with no new tooling.

## Recommended solution: Plan/Log split

Keep two sections under `## Pomodoros`:

**1. `### Roadmap` — plain bullets, no checkboxes, no `()` scaffolding.**
- Max ~6 lines, ordered top = next. Top 3 are today's MITs, marked with `🎯`.
- Each line is one theme + its bead links, copied from the backlog, e.g.:
  ` - 🎯 GOALS — [[sase_goals#^epic-roadmap]] → next: <one concrete next action>`
- Because lines are not tasks, they never pollute task queries or dash counts, need no `[t::]` math, and deleting/reordering them is one keystroke.
- Everything not in the roadmap stays where it already lives (beads, sase_goals) — the daily file stops duplicating the backlog.

**2. `### Log` — the current completed-block format, unchanged.**
- ` - [x] (**START-END** [t:: Nm]) — THEME` with `🍅` / `~~struck~~` / free-text outcome notes.
- Workflow per block: pull the top roadmap line down into the log when starting work (fills in real times at finish), rather than pre-filling times in the morning.
- Keep the existing header total formula untouched — it already sums exactly this section's completed blocks.

**3. Rename the section header from "Pomodoros" to "Timeboxes" (optional, cheap).**
- Matches what is actually practiced (10–85m themed timeboxes, 🍅 per bead outcome) and stops inviting strict-pomodoro guilt. One-line template change; old links to `#Pomodoros` would need a redirect alias if referenced elsewhere.

**4. Five-minute evening shutdown (append to template).**
- `- [ ] EOD: total = ___ · MITs hit _/3 · carry-forward (top roadmap leftovers stay as plain lines tomorrow)`.
- Replaces today's delete-everything cleanup: leftovers are already plain text, so carrying them forward is copy-paste with no checkbox surgery.

**Migration cost:** edit `_templates/daily.md` once (~10 lines); convert today's 22 open blocks into ~6 roadmap lines by hand once. No plugin, query, or dashboard changes needed. If the roadmap still feels thin after a week, the warranted next complexity is per-block `⏱️ started::` timestamps (Tasks-plugin-native elapsed math) — not sooner.
