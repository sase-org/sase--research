# Splitting `~/bob/sase.md` Into Child Project Notes (+ Duplicates)

Researcher: **mus** · Date: 2026-10-19 · Source: `~/bob/sase.md` (read in full, 1432 lines)

## Method

Read the entire file (frontmatter, all four task sections, Future Work, Requirements).
Counted task lines by checkbox state, extracted and normalized all task titles to hunt
exact and near duplicates, and clustered tasks by theme. Cross-checked the 22 active
`[[sase_*]]` sub-projects already named in the `^prj` header so the recommended split
reuses them instead of inventing competing notes. Per the swarm rules I did not open
any peer report; filename listing of the output directory was used only to pick a
non-colliding filename.

## File census (observed, 2026-10-19)

| Section | Count |
|---|---|
| Open (`- [ ]`) | 4 (1 is the `^prj` goal header, 3 are real tasks) |
| Next / in-progress (`[*]` + `[/]`) | 7 (5 `[*]`, 2 `[/]`) |
| Blocked (`[?]`) | 218 |
| Done (`[x]`) | 9 |
| **Total task lines** | **238** (frontmatter says `task_count: 237` — off by one) |
| `#ref` reading/research tasks | 24 |
| Future Work bullets (unsectioned, mostly June dates) | 79 |
| Requirements bullets | 4 |

Shape of the file: a ~10-item live working set sitting on top of a ~218-item blocked
backlog, plus ~79 Future Work one-liners (mostly `created::2026-06-*`, no freshness
metadata) and 4 Requirements. The blocked section is where every child-project split
pays off; the Future Work section is the second-best candidate because its items have
no schedule/freshness fields and will rot silently.

## Duplicates and conflicts

### D1 (exact duplicate, highest confidence). Future Work contains the same bullet twice
- Line ~1355 and line ~1357 are byte-identical: "Materialize steps in workflow to enable replay starting at certain xprompt workflow steps? `[[ref/docs/gastown_readme#^h-476bb727cc72|...]]` `[created::2026-06-15]`". Delete one.

### D2 (near duplicate). Hidden-agent removal is tracked in two places
- Blocked: "Remove support for hidden agents and old `.` keymap."
- Future Work: "Get rid of 'hidden' agent support from agents tab?!"
Keep the blocked one (it has freshness metadata); delete or link the Future Work line.

### D3 (near duplicate). PIW AI-completion is tracked in two places
- Blocked: "Migrate PIW next-word completion to co-pilot?!"
- Future Work: "Add support for copilot or some other kind of AI that can be fed prior prompts and offer completion for the PIW!"
Same feature, different wording. Merge into one task.

### D4 (overlap, keep both but link). Epic grilling
- Blocked: "Always `[[sase#^grill]]` epics!" explicitly references…
- Blocked: "Add a new 'Grill' option to tale/epic gate notifications! `^grill`"
The first is policy ("always"), the second is the UI mechanism. Not a true dupe, but
they should live in the same child note and link to each other.

### D5 (keymap conflict, needs a decision). `,X` is claimed twice for different behaviors
- Blocked: "Add new `,X` keymap to kill and edit an 'in-flight' sase agent!"
- Future Work: "Add TUI support for re-launching failed SASE agents w/ new `,X` keymap! `^comma-big-x`"
One keymap, two behaviors (kill-and-edit vs relaunch-failed). Flag before both ship.

### D6 (cluster, not dupes — merge candidate). Four separate rename brainstorms
"SASE rename ideas: 'power'/'po'", "'bai' (Better/Bugyi's AI)?", "'sal'", "sawi/saw?"
plus done-adjacent "Rename sase-listen to sase-talk!". Five tasks, one decision. They
should become checklist items under a single rename note rather than five competing tasks.

### D7 (self-declared possible dupe). `%wait` CPU kwarg
"Add `cpu=<N>.<duration>` kwarg to `%wait`!" carries its own note: "Use
`[[sase#^wait-for-load]]` instead?!" — the author already suspects it duplicates
"Instruct agents to use 'wait for load' monitor?! `^wait-for-load`". Resolve by closing
one in favor of the other.

No other exact title duplicates were found (all 238 normalized titles are unique).

## Recommended project split

Principle: reuse the 22 active `[[sase_*]]` sub-projects from the `^prj` header where a
task plainly belongs; create a new child note only for a cluster with no home. Each
proposed child follows the existing convention (`parent: "[[sase]]"`,
`template: "[[new_project]]"`, `type: "[[project]]"`, moved tasks keep their block IDs
like `^grill` so existing `[[sase#^...]]` links keep working).

### A. Tasks that already have a home (move, don't create)
- **TUI decks/panels/keymaps** → `[[sase_decks]]`, `[[sase_pager]]`: scrollbar/card focus,
  `|` and `\` keymap reversal, `,H`/`HH`/`LL` collapse keymaps, `,/`, `,?`, `M`-marks,
  `N`-options, relative numbers `^aaa-rel-line`, condensed left pane, pinning deck
  panels, `Q`-weights Queue field, better folds, standalone-proc Agents-tab bug,
  `l`-expand re-sort bug. (~22 keymap tasks + panel tasks.)
- **Memory system** → `[[sase_memory]]` (has its own sub-projects): memory deck move,
  "Memory should be artifacts!", stream bead type, `sase memory add/delete`, owned
  memories, memory comments, migrate memory to sidecar, memory-web roster dates,
  "Do memory webs even need to exist?", budgeted-router ref, artifact/memory read
  prohibition. Note the open tension: "Memory should be artifacts!" vs "Make it
  impossible for agents to directly read artifact/memory files!" — keep both visible
  in the same note.
- **Beads/tasks model** → `[[sase_better_tasks]]`: group bead, bead xprompt binding,
  bead phases config, machine-hood assignee, confidence level, snoozing (D-bead
  overlaps with "Add a way to snooze chops!" — put chop-snooze here too or link it),
  `sase bead diff`, bead triage routine, lost-memory-plan bug.
- **Plans/epics** → `[[sase_better_plans]]`: explicit epics in plan files, `wait`
  frontmatter field, plan file in `%` panel, `sase plan work`, grill pair (D4),
  land-epic-in-family (+ Future Work "Don't allow phase/land epic agents to launch on
  wrong projects!"), epic summary providers, plan decisions/UX.
- **Macros/xprompts/skills** → `[[sase_skill_bundles]]`: skill bundles via memory web,
  project-local xprompt skills, `//skill` syntax, `+` vs `/` separator, xprompt
  freshness labels, invoke-by-tag, xprompt file bundling, builtin-md xprompts,
  `#review_research` fix, `#coder` improvement, macro query language, chop xprompt sets.
- **Agents/launch infra** → `[[sase_agents_repo]]`, `[[sase_monitor]]`,
  `[[sase_remote]]`, `[[sase_polish_proc_lanes]]`: stop allocating waiting-agent
  workspaces, restart/shutdown/restart-relaunch trio, agent speed, `%name` directive,
  name-overwrite, `%q:0`, agent report command, failed-agent handling, `sase agent`
  report, standalone-proc frontmatter, proc shells as artifacts.
- **Research swarm** → existing research project (not in the 22; tasks reference
  `#research_swarm`): index-swarms (+ dependent `target-alias-providers`), `#git:home`
  support, `*_model` input removal, auto-link research files, image-agent mermaid note.
- **Releases/CI** → `[[sase_pypi_releases]]`: PyPI reliability ref (in progress),
  `sase project stats` + model-stats chain, Statistics tab, auto-artifact hooks,
  sidecar-PR creation, merge-queue chain (primer → reassessment → gascity-borrow),
  clippy hook, `just check-full` behavior.
- **Docs/site/blog** → `[[sase_blog]]`, `[[sase_post_blog]]`: sase.sh bare-bones
  rewrite (`^re-work-documentation`), diataxis read, gallery idea, sase--ux artifact
  repo question, docs-backed memory.
- **Providers/models** → `[[sase_more_agent_clis]]`: pi + hermes provider refs, ACP
  (`^acp`), hermes one-shot, Muse Wonder, Grok→X-subscription, Codex/Cap cost items.
- **Goals/usage/stats** → `[[sase_goals]]`, `[[sase_usage]]`: eval framework, usage
  window items, stats command consumers.

### B. New child notes worth creating (no current home)
1. **`sase_rename`** — the 5 rename tasks (D6) + gallery + `bugyi@sase.sh` email +
   1000-stars goal linkage. This is launch/marketing, and it currently pollutes the
   engineering backlog.
2. **`sase_wait_sched`** — all `%wait`/`%hold`/`%clan`-wait/scheduling tasks
   (`%wait` var/file support, cpu kwarg/D7, `wait-for-load`, E2E `%hold`, `%clan`
   wait kwarg, scheduled-agents `^schedule-agents`, per-job due times). Scheduling
   semantics are scattered across ~10 tasks today.
3. **`sase_piw`** — the ~12 PIW tasks (diagnostic hints, `<>` completion, prompt
   history, both `<ctrl+k>` behaviors, sub-ordered lists, `d`-dictionary, `<ctrl+t>`
   strand completion, placeholder history, copilot pair/D3, vim-mode + PIW extras
   from Future Work). PIW is a coherent subsystem with no note of its own.
4. **`sase_annotations`** — artifact annotations + all-artifact-decisions + user
   notes on agents + `sase links` in research files + chat-share publishing.
   One "humans and agents comment on things" theme.
5. **`sase_fleet_ops`** — Telegram-without-install, chezmoi-as-project, mac SSH
   memory file, Docker support, multi-user support, sase-capture repo, toasts/mac
   plugin. Machine/fleet-specific work that is neither TUI nor core.
6. **`sase_subscriptions`** — Codex credits/resets ×2, Claude reset, Spotify
   playlist, AntennaPod feeds, sase-listen rename. Personal-ops items mixed into
   the engineering file; even if they stay in sase.md, grouping them unclutters
   triage. (Alternatively move to a non-sase note entirely — several are not
   SASE engineering at all.)

### C. Hygiene (do alongside any split)
- Delete one copy of the D1 duplicate; merge D2/D3; resolve D5 and D7 explicitly.
- Triage the 79 Future Work bullets: most are June one-liners with no freshness
  fields. Either promote the live ones into the sections above or accept they are a
  cold backlog and mark them as such — right now they look like tasks but don't
  participate in scheduling.
- Fix the `task_count` drift (238 observed vs 237 recorded) when items move.

## Overall summary

`~/bob/sase.md` is a healthy but overgrown project note: 238 tasks, of which only ~11
are live (4 open + 7 next/in-progress) and 218 sit blocked. Roughly two dozen are
`#ref` reading/research items forming several dependency chains (merge-queue →
gascity; PyPI reliability; provider designs). The blocked backlog clusters cleanly
into about ten themes — TUI/decks/keymaps, memory, beads, plans/epics,
macros/xprompts, agent launch infra, research swarm, releases, docs/site, and
providers — most of which already have a named `[[sase_*]]` sub-project ready to
receive them. Exact duplication is minimal (one byte-identical Future Work bullet,
two near-duplicate pairs, one keymap conflict on `,X`, one self-suspected `%wait`
overlap, and five rename brainstorms that should be one note). The recommended split
is: move themed tasks into the existing 22 sub-projects, create ~6 focused child
notes for the homeless clusters (rename/launch, wait-scheduling, PIW, annotations,
fleet-ops, subscriptions/personal-ops), and triage the 79 stale Future Work bullets.
After the split, `sase.md` should hold only the `^prj` goal, the live working set,
genuinely unclassifiable ideas, and links to the children.
