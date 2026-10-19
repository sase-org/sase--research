# SASE task portfolio: child projects, duplicates, and backlog cleanup

Independent review by **cdx**, 2026-10-19.

**Recommendation:** create five focused child project notes—agent recovery, prompt editing, TUI navigation, macro workflows, and completion contracts—while first moving much of the backlog into children that already exist. Keep `sase.md` as the portfolio and strategy note. The file needs ownership and status cleanup more than it needs another large layer of projects.

## Evidence and scope

The primary source is [Bryan's `sase.md`](/home/bryan/bob/sase.md), retrieved through read-only `bob query` access. I reviewed every task and top-level idea, including supporting work logs, dependency bullets, and the unchecked ideas under **Future Work** and **Requirements**. Schedule-history rows were counted and used to distinguish deferred work; their individual date-roll records were not analyzed as separate work items. I also queried root-level `sase*` notes for their project objectives and tasks to identify existing destinations. No vault files were modified. No other researcher’s report, transcript, summary, or findings were consulted.

References below use **one-based source line numbers** derived from Dataview's zero-based `line` field. Where available, block IDs are stronger locators and are preserved in the inventory. The note can change after this snapshot. Linked research documents and external websites were not read: a task linking to research is evidence of an interest or work item, not evidence that its proposed design is correct or unimplemented. This is a portfolio review, not an implementation audit.

| Source section | Checkbox tasks | Other list items | Interpretation |
| --- | ---: | ---: | --- |
| Project header | 1 | 1 | The ≥1,000 GitHub stars objective and the child-project index |
| Tasks | 3 | 12 | Two reference tasks and a Codex credit reminder |
| Next & In Progress | 7 | 9 | Five `[*]` rows and two `[/]` rows |
| Blocked | 218 | 1,028 | A mixture of scheduled backlog and dependency-blocked work |
| Done & Canceled | 9 | 10 | All nine checkbox rows currently use `[x]` |
| Future Work | 0 | 94 | **79 top-level ideas** plus 15 supporting bullets |
| Requirements | 0 | 4 | Four additional top-level ideas |
| **Total** | **238** | **1,158** | 1,396 list items; supporting bullets are not extra tasks |

There are **228 open task checkboxes excluding the parent project objective**, plus **83 top-level non-checkbox ideas**. The routing inventory below therefore covers **311 source entries**, before deduplication or retirement. It excludes the parent objective, the nine completed rows, and supporting bullets as separate work items. Those supporting bullets should travel with their parent entries.

The child index already contains **60 linked projects: 22 unstruck and 38 marked completed or canceled**. Creating a fresh memory, artifacts, providers, releases, or remote-work project would duplicate existing organizational structure.

Of the 218 rows under **Blocked**, **208 have a scheduled date and schedule log**; the other ten have explicit `DEPENDS ON` bullets. Thus “Blocked” mostly means deferred/scheduled in this note, rather than “cannot proceed because another deliverable is missing.” There are also **19 open `#ref` tasks** across the file. Eleven have an obvious delivery-project home; eight general reading tasks are routed to `sase_ref` in the inventory. Preserve their reading/action intent rather than treating them as eight new software features.

## Five worthwhile new child notes

These are ownership boundaries, not a commitment to implement every historical idea. Each note should separate its first deliverable from optional ideas and design decisions. Names are proposals; none appeared in the queried root-level SASE-note inventory.

| Proposed child | Why it deserves a separate note | Suggested first deliverable and boundary |
| --- | --- | --- |
| `sase_agent_recovery` | Failures, relaunching, restart survival, and preserving work recur throughout the file. L91, L405, L601, L664, L721, L1001, and L1039 form a coherent operator journey. | A user can stop, recover, and relaunch failed/interrupted work without losing the workspace, and can understand retries. Resolve live-agent kill/edit versus failed-agent relaunch before assigning `,X`. Queue residency and machine restart behavior are dependencies; provider integrations and ordinary deck layout belong elsewhere. |
| `sase_prompt_editor` | Completion, prompt history, snippet diagnostics, local editing, and input affordances are spread across unrelated dates. L244, L498, L520, L560, L948, L1092, and L1144 fit one editor experience. | Prompt composition has predictable history/completion controls and working search. Start with the current completion defects and conflicting `Ctrl+K` gestures. Treat AI completion and a separate Mac capture client (L960) as optional later work; macro execution semantics belong in the next project below. |
| `sase_tui_navigation` | Focus, scrolling, reversible keymaps, collapsing nodes, pinned panels, global search, marks, and hints describe a usability project beyond the completed deck migration. | Stabilize deck focus and reversible split operations first (L39/L43), then agree a coherent navigation/keymap scheme. Appearance, toast plugins, screenshots, and broader tab refinements remain a later backlog within the note, rather than blocking the first milestone. |
| `sase_macro_workflows` | Macro invocation, swarm selectors, reusable resources, syntax consistency, replay, and maintenance have no adequate existing open owner. | Make composing and reusing macros predictable: settle selectors and project-local syntax, document escape rules, and organize bundled resources. Workflow replay is a distinct later milestone; do not silently enlarge the first milestone to include it. Skill discovery remains in `sase_skill_bundles`, prompt UI in `sase_prompt_editor`, and process supervision in the existing proc/monitor projects. |
| `sase_completion_contracts` | The file repeatedly questions or extends finalization, handoffs, output variables, agent reports, and configurable follow-up behavior. L129, L435, L472, L578, L713, and L1421 should be considered together. | Document and verify what is preserved and declared on normal completion, plan/monitor handoff, and failure. Resolve the policy question at L129 before designing plugin finalizers. A finalizer's variable requirements belong here; variable storage/inheritance still belongs to `sase_better_vars`. General gate-interface experiments need not block this project. |

The first three have visible daily-use value. The latter two require more design reconciliation. Create the notes to establish ownership, but keep only one or two selected deliverables active at a time; moving scheduled tasks must not promote them to immediate work.

## Reuse existing children before creating more

The exact per-entry allocation appears in the inventory. These are the most valuable existing homes:

| Existing home | What should move out of `sase.md` | Boundary or caution |
| --- | --- | --- |
| `sase_memory` | Memory create/delete, ownership, comments, storage, read auditing, instruction routing, authoring structure, and memory-versus-artifact decisions | Cross-link artifact history and display work. Do not implement mutually exclusive storage/rendering ideas just because they share the same note. |
| `sase_skill_bundles` | L639/L756/L767/L1281: project-local skills, discovery, and alternative bundle representations | The note already exists. Memory-web versus semantic-search versus `sase skills read` are design alternatives for one outcome. |
| `sase_art`, `sase_art_file`, `sase_art_links` | Artifact annotations and decisions, research links, file capture/hooks, publication, history, and web browsing | The parent already has an artifact-history task and `^web-client`. Put file capture/attachments under `sase_art_file`, research/source relationships under `sase_art_links`, and cross-artifact behavior under `sase_art`. Audio/research automation can start as a named subsection; a new project is only justified if independently prioritized. |
| `sase_better_plans` | Nested epics, plan prerequisites, phase configuration, execution entry point, review/grill behavior, and plan feedback | Reference tasks describing a plan can be supporting material for an actionable task, rather than a second implementation obligation. |
| `sase_better_tasks` | Triage, bulk bead operations, task prompts, diff views, grouping, confidence, snoozing, assignment, and grouped execution | The existing “each task type specifies prompts” task overlaps L879's per-bead prompt selection; distinguish type defaults from per-item overrides. |
| `sase_projects` | Project statistics/model attribution, project-local limits and files, repository identity, contribution workflows, and stitch/PR ideas | Contribution support could become a later child if the fork pilot (L169) is chosen. Do not create that child solely for isolated repository cleanup. |
| `sase_polish_proc_lanes`, `sase_monitor` | Proc visibility/output and jobs; waiting for load/artifacts and monitor escalation | Proc/job scheduling and agent recovery must agree on waiting/restart state, but they own different user-facing outcomes. |
| `sase_pypi_releases` | Current release-reliability work, merge-queue reading and design, post-commit Clippy, and `check-full` behavior | L40 is already in progress. The completed v0.18.0 release is not proof that recurring release reliability is complete. |
| `sase_more_agent_clis` | pi, Hermes, ACP, Muse research, and the fakey macro | L117/L119 retain their release-project dependency. Adding one provider does not complete support for all providers. |
| `sase_usage` | Credit/reset reminders, spending caps, subscription decisions, model-pool overrides | The two Codex reminders may refer to the same allowance, but one records balance and one expiry; reconcile rather than discard the deadline. |
| `sase_remote`, `sase_better_installs` | Fleet notifications/Telegram placement and remote launch; Windows/Docker/onboarding and per-machine setup | Avoid turning portability or packaging into prerequisites for the recovery project's first local milestone. |
| `sase_better_config`, `sase_agents_repo`, `sase_better_vars`, `sase_better_glossary`, `sase_toobig_symvision` | Configuration navigation; naming; variables; terminology; code-structure work | Use named subsections for peripheral tasks. For example, `pyarch` is an exploratory companion to code-structure tooling, not automatically part of the current migration's completion gate. |
| `sase_blog`, `sase_ref` | Documentation, gallery, outreach, contributor demonstration; general reading | Keep reading tasks distinguishable from product implementation. The Black demonstration is a possible blog/use-case deliverable, not a SASE-core feature. |

The artifact and project notes are broad existing umbrellas. If one grows into an active multi-outcome project, extract a child then. Do not create separate new notes for every CLI command, keymap, provider, or renamed concept now.

## Duplicate and overlap register

### One exact duplicate

| Entries | Finding | Recommended disposition |
| --- | --- | --- |
| **L1355 and L1357** | Identical “Materialize steps in workflow to enable replay starting at certain xprompt workflow steps?” text, including the same reference link | Keep one canonical entry under `sase_macro_workflows`. These are plain bullets, not two open checkbox tasks. |

### Strong semantic duplicates and same-outcome pairs

| Entries | Confidence and distinction | Recommended disposition |
| --- | --- | --- |
| **L244 + L1391** | High: both request Copilot-style prompt-input completion; L1391 adds learning from previous prompts | Merge into one editor task, retaining prior-prompt context as a requirement. |
| **L918 + L1372** | High: both propose removing hidden-agent support | One decision/task, but resolve the contrary L1409 request first. |
| **L664–665 + L1001** | High: both request agent restoration after machine restart; the former explicitly adds orderly shutdown and a single restore command | One restart-survival outcome, with shutdown, persistence, and restore as acceptance cases. |
| **L282 + L1183–1184** | High: “always grill epics” is repeated inside the task to add a Grill option | Keep the gate capability and mandatory-versus-optional policy as separate sub-decisions in one planning entry. |
| **L199 + L1278** | High at the research-question level: both consider interactive tmux instead of headless agents; L199 additionally proposes a mayor-style hierarchy | One architecture investigation with two questions. Do not delete the hierarchy question. |
| **L57 + L121** | Same deliverable, different roles: a MEMORY deck task and a research-reference task about its placement, both blocked by releases | Keep one implementation entry and attach the reference/remaining reading action. Do not count the reference as a second deck feature. |
| **L119 + L1275** | Likely same provider effort: full Hermes support and a specific `hermes chat --oneshot` entry | One provider workstream with an explicit one-shot-mode requirement, subject to checking the linked design. |
| **L756 + L1281** | Same skill-bundle outcome, conflicting implementation proposals; L1281's child bullet itself questions `sase memory read` versus `sase skills read` | One design decision in the existing `sase_skill_bundles` note, preserving alternatives. |
| **L740 + L1035** | Partial duplicate: freshness notifications for macros/snippets/memories versus freshness labels for unused macros | One freshness capability with separate metadata/UI/notification requirements. No need for two independent projects. |
| **L126 + L745 + L1027 + L1418–1420** | One naming decision with several candidates: power/pow/po, bai, sal, sawi/saw | One parked naming entry in the parent, retaining all candidates and reasoning. |
| **L1214 + L1385** | Probable: both propose using SASE to land a Black feature; only L1385 explicitly identifies string wrapping | Confirm feature identity, then keep one contributor demonstration with its precise upstream target. |
| **L713–716 + L1353** | Partial overlap: end-of-session report and memory/skill survey | One reporting interface may serve both, but transcript titles and memory feedback are distinct outputs. |

A particularly clear cross-note duplicate is **L1105** (“Migrate to `/sase_stitch`…”) and **`sase_memory.md:L62`, `^commit-to-stitch`** (“Migrate `/sase_git_commit` to `/sase_stitch`”). Keep the existing memory task as the canonical owner and carry over the built-in-memory proposal from L1105. This is a confirmed cross-note match from the queried task text, not an inference from filenames.

### Conflicts, dependencies, and related work that should not be deleted as duplicates

- **Hidden agents:** L918/L1372 propose removal; L1409 proposes better `%hide` support and a hidden count. Record a decision before choosing a branch.
- **`,X` reuse:** L1039 means kill/edit an in-flight agent; L1425 means relaunch a failed agent. These may share a context-dependent interface, but they are different operations. Bulk recovery at L91 and restart-on-dismiss at L405 are further entry points, not redundant requirements.
- **`Ctrl+K` reuse:** L560 handles an already-visible completion menu, L948 invokes history, and L1092 adds a project filter. They can be phases of one interaction contract. Preserve all three cases.
- **Skill and memory representation:** L756/L1281, L784, L102, and L420 affect bundles, memory webs, artifact identity, and storage. They are related architectural choices, not interchangeable requests. L784 questions whether webs should exist while L756 proposes depending on them.
- **Annotations and decisions:** L213 asks for artifact annotations, L229 for typed decisions across artifact kinds, L1367 for screenshot annotations, and L1389 for agent notes. Share infrastructure if useful, but retain the distinct semantics and interfaces.
- **Provider and reading similarity:** pi (L117) and Hermes (L119) are different integrations. Stripe Minions Part 1 (L371) and Part 2 (L732) are different articles with an explicit ordering dependency; their very similar titles are not duplicates.
- **Project statistics:** L46 is the statistics command; L353 is model attribution and explicitly depends on it; L355 is a TUI consumer. Keep the sequence.
- **Swarm selectors and alias providers:** L218 enables indexed swarm targets; L945 depends on it. These are separate layers even though the proposed bracket syntax is shared.
- **Release work:** the checked-off v0.18.0 release at L1317 and in-progress reliability design at L40 have different completion criteria.
- **Source provenance versus explicit snapshotting:** L295 requests automatic research-source links, whereas L358 requests configurable artifact capture. Neither replaces the other.

## Status and relevance cleanup

Several entries are historical reminders or policy questions. Giving them their own project would make the portfolio less useful.

1. **Review apparently delivered ideas before activating them.** L1333's dynamic families overlaps a child marked completed; L1343's sidecar migration overlaps completed `sase_sdd_repo`; L1430's Antigravity reading sits alongside a completed provider migration. The current agent environment exposes `/sase_run`, while L1338 still asks to create it and `sase_memory.md:L42` asks to remove it. These are status-reconciliation candidates, not proof that every detail of each idea is finished. Preserve L1333's separate “family types” research detail if it remains useful.
2. **Do not reopen old canceled projects implicitly.** The index marks `sase_sites` and `sase_message_boards` canceled. L1341's “try sites” and L927's common chat board should remain explicit reconsideration decisions. Artifact-page web browsing at L1397/L1429 has an open home in `sase_art#^web-client`; it need not revive the canceled sites project.
3. **Separate completed subwork from unresolved work.** L721 already marks forking failed agents as DONE; its unresolved request is preserving/killing/recovering work. L482's log says Muse Wonder was added to model selection, but that alone does not establish whether research workflows use it. L1270 explicitly downplays the lost-plan issue. Reassess urgency rather than treating every old bug description as equally current.
4. **Time-sensitive reminders need review, not feature projects.** L27/L59 and L528 concern allowances or resets; L1292 is a spending cap. The stated October 22 deadlines are source-note claims, not independently verified account facts. Preserve the expiry information and review it in `sase_usage`.
5. **Move non-SASE outcomes out.** L192 (Spotify/Abby playlist), L748 (Databricks interview preparation), L924 (Opus with Blender), and L1344 (home configuration instructions) belong to the relevant personal/career/home note unless explicitly chosen as SASE demonstrations. Their ultimate destination names are intentionally unspecified because those areas were not reviewed.
6. **Treat speculative architecture as decisions.** Naming, interactive mayor/tmux sessions, shared message boards, a UX-artifact repo, removing memory webs, and redefining stitches are not ready implementation tasks. Retain the question marks and rejected alternatives. L1299 even says the author doubts the glossary-tier idea.
7. **Normalize malformed or dated captures on migration.** L1342 contains two run-together PR-comment/mentor ideas and a literal old creation-date fragment. L1374's nested “background task or axe tab” question may be attached to the wrong parent. “SDD,” “ChangeSpec,” “xprompt,” “chop,” and related old labels warrant interpretation before being converted into new work. The inventory preserves source wording rather than guessing a modern equivalent.

## How to preserve the task graph when reorganizing

This report recommends organization only; it does not move, close, reschedule, or create vault tasks.

- New Bob Markdown notes need `parent: "[[sase]]"` frontmatter. Give each real child a concrete `#prj` objective with its own note-local `^prj` block, consistent with existing notes. Let the parent retain the child index and strategic objective.
- Move the **entire task subtree**, including source links, schedule/priority metadata, work logs, dependencies, block IDs, and unresolved alternatives. Moving the title alone loses most of the note's accumulated context.
- Keep one canonical actionable task. Turn supporting research into an attached reference or a separately identifiable reading step only when reading remains an action. Convert only selected Future Work bullets to tasks; do not automatically activate all 83 ideas.
- Preserve the explicit chains: L44 → L184 → L202; L46 → L353; L218 → L945; L371 → L732. Also preserve the release-project blockers on L57/L117/L119/L121 and the dynamic-instructions blocker on L852. L23's dependency points into `done/sase_done`; verify whether it is satisfied rather than deleting it by assumption.
- Rewrite both outgoing and incoming block links when tasks change notes. For example, moving L46/L353 together to `sase_projects` can keep their mutual local links there, but external references to `sase#^sase-project-stats` must change. A local `[[#^...]]` reference that crosses the new boundary must become note-qualified. The completed header's many historical links are not new tasks to migrate.
- For merges, retain one block ID and update references to the retired ID. Check conflicting dates/priorities deliberately. Treat the two source entries as one outcome without losing a genuine dependency, expiry, or reading action.
- The first cleanup pass should preserve current statuses and dates. Decide scheduling after ownership is clear. This is particularly important because “Blocked” currently includes almost the entire scheduled backlog.

## Complete routing inventory

Every open task and every top-level Future Work/Requirements idea is listed once below. Counts are **before merging duplicates or retiring stale entries**. “Task” means a nonterminal checkbox; “Idea” means a plain bullet. Text is lightly normalized for readability (the `#task` marker and Google Keep shortcut are omitted); linked reference titles, block IDs, and line locators remain. The original task subtree is the migration unit.

| Destination | Open tasks | Plain-bullet ideas |
| --- | ---: | ---: |
| NEW: sase_agent_recovery | 11 | 8 |
| NEW: sase_prompt_editor | 14 | 6 |
| NEW: sase_tui_navigation | 23 | 7 |
| NEW: sase_macro_workflows | 21 | 11 |
| NEW: sase_completion_contracts | 7 | 4 |
| EXISTING: sase_memory | 17 | 4 |
| EXISTING: sase_skill_bundles | 4 | 0 |
| EXISTING: sase_better_glossary | 4 | 0 |
| EXISTING: sase_art (and its children) | 21 | 12 |
| EXISTING: sase_better_plans | 11 | 4 |
| EXISTING: sase_better_tasks | 11 | 0 |
| EXISTING: sase_projects | 16 | 5 |
| EXISTING: sase_polish_proc_lanes | 7 | 1 |
| EXISTING: sase_monitor | 5 | 0 |
| EXISTING: sase_pypi_releases | 5 | 0 |
| EXISTING: sase_more_agent_clis | 6 | 2 |
| EXISTING: sase_usage | 6 | 0 |
| EXISTING: sase_remote | 2 | 1 |
| EXISTING: sase_better_config | 2 | 0 |
| EXISTING: sase_blog | 6 | 3 |
| EXISTING: sase_better_installs | 4 | 2 |
| EXISTING: sase_better_vars | 0 | 1 |
| EXISTING: sase_agents_repo | 2 | 0 |
| EXISTING: sase_toobig_symvision | 1 | 3 |
| READING: sase_ref (reading queue, not a new delivery project) | 8 | 0 |
| OUTSIDE SASE: personal / career / home configuration | 3 | 1 |
| KEEP IN PARENT: strategy, small independent actions, or retirement review | 11 | 8 |
| **Total** | **228** | **83** |

### NEW: sase_agent_recovery

- **L91 · Task `[?]`** — Add "Recovery”/"Relaunch” panel that can be used to recover lots of failures!
- **L405 · Task `[?]`** — Always prompt to restart failed agents when dismissing!
- **L601 · Task `[?]`** · `^schedule-agents` — Stop allocating workspaces for all waiting/queued agents!
- **L664 · Task `[?]`** — Sase needs a way to shut down all agents before a machine restart, for example!
- **L721 · Task `[?]`** — Better failed agents!
- **L918 · Task `[?]`** — Remove support for hidden agents and old `.` keymap.
- **L1001 · Task `[?]`** — Make all sase agents re-launch after a machine restart!
- **L1039 · Task `[?]`** — Add new `,X` keymap to kill and edit an “in-flight” sase agent!
- **L1100 · Task `[?]`** — All background tasks should be “detached”!
- **L1265 · Task `[?]`** — Speed up agent launches!
- **L1270 · Task `[?]`** · `^fix-lost-memory-plan` — BUG: Plans are lost when agents ask confirmation for memory changes!
- **L1362 · Idea** — Start showing failed agents that were retried as agent child rows!
- **L1370 · Idea** — Stop clearing workspace when “code” agents ask questions!
- **L1372 · Idea** — Get rid of “hidden” agent support from agents tab?!
- **L1402 · Idea** — Start marking failed agents with retryable failures as RETRYING immediately!
- **L1405 · Idea** · `^retry-explain` — Add “RETRY EXPLANATION" section to metadata panel when an agent failure is retried!
- **L1409 · Idea** — Add ability to `%hide` agents using keymap + add TUI count of hidden agents!
- **L1416 · Idea** — Make the `%wait` directive see dismissed agents (so we don’t wait forever)!
- **L1425 · Idea** · `^comma-big-x` — Add TUI support for re-launching failed SASE agents w/ new `,X` keymap!

### NEW: sase_prompt_editor

- **L244 · Task `[?]`** — Migrate PIW next-word completion to co-pilot?!
- **L498 · Task `[?]`** — Add PIW diagnostic hints when snippet's contents are found but snippet was not used!
- **L520 · Task `[?]`** — Add support for `<` / `>` in PIW to trigger agent completion for `%w` / `#fork`!
- **L560 · Task `[?]`** — Add `<ctrl+k>` keymap that has `K` behavior when completion menu is visible!
- **L613 · Task `[?]`** — Add plan file to % panel!
- **L649 · Task `[?]`** — Fix `sase prompt search` command!
- **L839 · Task `[?]`** — Add support for sub-ordered lists (e.g. `a.`) to PIW!
- **L873 · Task `[?]`** — Require definition from user when using `d` keymap to add word to dictionary from PIW!
- **L948 · Task `[?]`** · `^light-prompt-history` — Make first `<ctrl+k>` in PIW trigger light-weight prompt history completion!
- **L954 · Task `[?]`** · `^web-piw-completion` — Add `<ctrl+t>` memory strand name / alias completion to PIW!
- **L960 · Task `[?]`** · `^capture` — Add sase-capture repo inspired by bob-mac-capture!
- **L1050 · Task `[?]`** — Add placeholder input history!
- **L1092 · Task `[?]`** — Pressing `<ctrl+k>` in PIW containing `#gh:sase` should use `project:sase` filter!
- **L1144 · Task `[?]`** — Add plugin support for PIW completion sources!
- **L1368 · Idea** — Start showing VCS xprompt workflow as a badge at the beginning of the prompt input widget?!
- **L1380 · Idea** — Start modifying the prompt when the `a`, `n`, `N`, or `w` keymaps are used!
- **L1382 · Idea** — Start adding agent name to toast immediately after hitting `<enter>` and to `Starting <N>` counter!
- **L1391 · Idea** — Add support for copilot or some other kind of AI that can be fed prior prompts and offer completion for the PIW!
- **L1393 · Idea** — Add extra option to `<enter>` PIW panel for saving the "current xprompt”!
- **L1394 · Idea** — Add vim-mode keymaps to ALL of the input boxes!

### NEW: sase_tui_navigation

- **L39 · Task `[*]`** · `^fix-main-deck` — Fix scrollbar and card focus for main data deck!
- **L43 · Task `[*]`** · `^fix-deck-keys` — Fix `|` and `\` keymaps so they reverse their own operations!
- **L53 · Task `[*]`** · `^e2e-test-agent-history` — E2E test new agent history!
- **L98 · Task `[?]`** · `^comma-big-h` — Add `,H` keymap for easy node collapse!
- **L157 · Task `[?]`** — Add support for bulk-copying with `%` keymap!
- **L333 · Task `[?]`** · `^fold-car-art` — Hide sidecar repo commits / deltas in 1st level agent / family folds!
- **L450 · Task `[?]`** · `^hh-keymap` — Make pressing `HH` (on the agents tab) collapse the last target/hint!
- **L547 · Task `[?]`** · `^better-folds` — Add much better folding to agent shell in agent metadata panel!
- **L587 · Task `[?]`** — Add support to sase notification tabs for custom grouping strategies!
- **L618 · Task `[?]`** — Make `,/` keymap search for any text in any panel on any tab in the TUI!
- **L626 · Task `[?]`** — Add support for pinning deck panels to specific agents!
- **L734 · Task `[?]`** — Rename "Main” deck to "IO"?
- **L773 · Task `[?]`** — Sort pre-xprocs above the corresponding agent shell!
- **L893 · Task `[?]`** — Add support for `%q:0` and show `c<inf_symbol>` in node!
- **L933 · Task `[?]`** — `N` should trigger panel with options for:
- **L957 · Task `[?]`** · `^q-weights-metadata` — Show new `Queue:` field in metadata panel instead of using `Wait:` for this!
- **L1009 · Task `[?]`** — Add support for a condensed version of the left pane in the Agents tab.
- **L1017 · Task `[?]`** · `^toasts` — Add sase-mac-toasts to override TUI toasts and `bam`!
- **L1075 · Task `[?]`** — Move runner's override to wait panel!
- **L1174 · Task `[?]`** — Add support for custom marks on any entry on any tab using `M` keymap that claim a key for the backtick keymap panel!
- **L1193 · Task `[?]`** — Implement a `,?` keymap that provides context-specific hints and keymaps for a selected entry in the TUI!
- **L1250 · Task `[?]`** — BUG: Expanding node with `l` keymap can re-sort node under hood agent group!
- **L1259 · Task `[?]`** · `^aaa-rel-line` — Add relative numbers to all the left panes on the main AAA tabs!
- **L1361 · Idea** — Figure out where “Activity:” metadata panel field came from!
- **L1367 · Idea** — Add support for annotations to screenshots!
- **L1381 · Idea** — Add “Wait” panel that has agent name selector and support for `%t`!
- **L1384 · Idea** — Make `<ctrl+shift+opt+s>` keymap use fixed screenshot selection!
- **L1386 · Idea** — Add support for a light colorscheme!
- **L1399 · Idea** — s/SLOW/INTERESTING/ TOOL CALLS?!
- **L1401 · Idea** — Show commits panel inline in PRs tab using `[`/`]` to switch between inner tabs?!

### NEW: sase_macro_workflows

- **L218 · Task `[?]`** · `^index-swarms` — Allow agent swarms to be indexed into via `#research_swarm[linker]` syntax!
- **L317 · Task `[?]`** — Stop using arguments with `%auto` everywhere!
- **L327 · Task `[?]`** — Start linking to xprompt definitions from prompts/ files!
- **L439 · Task `[?]`** — Get rid of `skill: true` and `ref: true`!
- **L508 · Task `[?]`** — Chops should be able to define a set of xprompts!
- **L535 · Task `[?]`** · `^builtin-md-xprompts` — Factor out all internal markdown text using xprompts!
- **L542 · Task `[?]`** — Add workflow best practices and adjust existing workflows accordingly!
- **L570 · Task `[?]`** — Xprompts should be able to subscribe to memory webs!
- **L607 · Task `[?]`** — Get rid of `*_model` research swarm inputs.
- **L632 · Task `[?]`** · `^improve-coder` — Improve the `#coder` xprompt!
- **L740 · Task `[?]`** — Configurable freshness notifications for macros, snippets, and memories!!!
- **L811 · Task `[?]`** — Xprompts should be able to bundle files that they reference.
- **L854 · Task `[?]`** — Create macro query language that can be used to query for macros!
- **L860 · Task `[?]`** — Make `#research_swarm` work with `#git:home`!
- **L945 · Task `[?]`** · `^target-alias-providers` — Make it possible to target provider contained in model alias using `@xlarge/codex` syntax!
- **L951 · Task `[?]`** · `^multi-line-alternations` — Add support for multi-line alternations using `%{}` syntax!
- **L1035 · Task `[?]`** — Add xprompt freshness labels to manage unused xprompts!
- **L1138 · Task `[?]`** — Add support for `%tag` directive that works with new `tag_hooks` config field!
- **L1166 · Task `[?]`** · `^xprompt-by-tag` — Make it possible to invoke an xprompt by tag!
- **L1179 · Task `[?]`** — Add a `wait` kwarg to `%clan` that allows clans to wait for clans/agents/families!
- **L1235 · Task `[?]`** — Use `+` instead of `/` as separator for project-local xprompts?!
- **L1348 · Idea** — Migrate xprompts/pylimit_split.yml to Python script?!
- **L1354 · Idea** — What _else_ can sase learn from PDL (https://github.com/IBM/prompt-declaration-language)?
- **L1355 · Idea** — Materialize steps in workflow to enable replay starting at certain xprompt workflow steps? [[ref/docs/gastown_readme#^h-476bb727cc72|🔖]]
- **L1357 · Idea** — Materialize steps in workflow to enable replay starting at certain xprompt workflow steps? [[ref/docs/gastown_readme#^h-476bb727cc72|🔖]]
- **L1369 · Idea** · `^vby-and-acet-snips` — Add `vby` (verify) and `acet` (sase ace --tmux) sase snippets.
- **L1376 · Idea** — Create a `sase xprompt fmt` command that acts as a custom formatter for xprompt markdown files?!
- **L1383 · Idea** — Decide on the best way to escape all of the things in sase xprompts!
- **L1404 · Idea** — Get rid of the concept of standalone xprompts and just append the prompt to the first agent in the xprompt?
- **L1406 · Idea** · `^plus-for-prjs` — Start using `+sase` (shorthand that is auto-replaced w/ `#gh:sase-org/sase`) to specify the VCS xprompt workflow!
- **L1414 · Idea** — Make it possible to broadcast much more data using `%clan` and `%n`!
- **L1417 · Idea** — Use `@smartest` for audit agents!

### NEW: sase_completion_contracts

- **L129 · Task `[?]`** — Evaluate the need for host-owned completion/commits.
- **L435 · Task `[?]`** — Migrate gates and monitors to finalizers.
- **L472 · Task `[?]`** · `^final-vars` — Use new finalizer to enforce specific agent output vars?!
- **L578 · Task `[?]`** — Start making agents finalize even when creating plans or launching monitors.
- **L713 · Task `[?]`** — Add `sase agent report` command and have agents use this at the end of every session!
- **L816 · Task `[?]`** — Generalize `<foo>` syntax into sase "annotations"!
- **L1227 · Task `[?]`** — Add a new built-in finalizer that checks for agent messages which could be sent from humans or agents!
- **L1349 · Idea** — Add plan/prompt commit functionality to the `sase plan approve` command!
- **L1353 · Idea** — Implement “agent survey” in finalizer that gets agent feedback about the memories/skills it used?!
- **L1363 · Idea** — Merge sdd/tales/ commits with the “code” agent’s commit!
- **L1421 · Idea** — I want to add better support for finalizer customization via a new `%final` directive.

### EXISTING: sase_memory

- **L86 · Task `[?]`** — Add create dates to decisions memory web roster in AGENTS.md!
- **L102 · Task `[?]`** · `^memory-artifacts` — Memory should be artifacts!
- **L112 · Task `[?]`** — Add new “stream” bead type that acts as memory stream for certain agents!
- **L195 · Task `[?]`** — Start making a "log" agailable to all sase agents?!
- **L308 · Task `[?]`** — Add `sase memory add / delete` commands!
- **L420 · Task `[?]`** — Migrate memory to sase--memory sidecar repo?!
- **L466 · Task `[?]`** — Support “owned” memories that can be modified by specific agents hoods!
- **L565 · Task `[?]`** — Allow memory files to contain comments (which contain reasoning and/or links to conversations) that don't get rendered in the instructions?!
- **L670 · Task `[?]`** — Make it impossible for agents to directly read artifact/memory files!
- **L784 · Task `[?]`** — Do memory webs even need to exist?
- **L852 · Task `[?]`** · `^ref-agent-instructions-budgeted-router` — #ref [[ref/chat/agent_instructions_budgeted_router|Shrinking SASE's Agent Instruction Files to ≤100 Lines: A Budgeted Router, Not a Trim]]
- **L899 · Task `[?]`** — Migrate to using a single `sase read/show` command!
- **L1022 · Task `[?]`** — Add support for searching community memories and importing into projects?!
- **L1105 · Task `[?]`** · `^stitch-skill` — Migrate to `/sase_stitch` by defining a built-in `how_to_git_commit.md` memory!
- **L1148 · Task `[?]`** — Convert tui_perf.md into tui.md and add tab/keymap expectations!
- **L1208 · Task `[?]`** — Add long-term ~/sase/memory/mac.md file with SSH instructions!
- **L1240 · Task `[?]`** — Migrate `parent` in memory files to `ancestors` list!
- **L1346 · Idea** — Add good ~/memory/long/bash.md file for writing bash scripts that use `bugyi.sh`!
- **L1347 · Idea** — Migrate AGENTS.md files to single SASE.md?!
- **L1365 · Idea** — Create memory/pyvision.md file!
- **L1374 · Idea** — Migrate all `/șase_<cmd>` skills to new long-term memory/sase_cmds.md hub note!

### EXISTING: sase_skill_bundles

- **L639 · Task `[?]`** · `^slash-slash-skill` — Add support for `//skill` syntax for `/<project>_skill` skills specific to `<project>`!
- **L756 · Task `[?]`** — Implement skill bundles using a memory web!
- **L767 · Task `[?]`** — Add support for project-local xprompt skills!
- **L1281 · Task `[?]`** — Use new “semantic” memory files with `sase memory read` (and new `search` subcmd) for skill bundles!

### EXISTING: sase_better_glossary

- **L833 · Task `[?]`** — Replace internal axe/lumberjack/chop references!
- **L921 · Task `[?]`** — Add "TUI header rows" to glossary!
- **L1134 · Task `[?]`** — Remove ALL references to “SDD”!
- **L1299 · Task `[?]`** — Migrate glossary to tier 3 memory!

### EXISTING: sase_art (and its children)

- **L57 · Task `[?]`** · `^memory-deck` — Move agent instruction bundles from file deck to new memory deck!
- **L67 · Task `[?]`** — Add support for "sase links” in research files that `bob ref create` renders into great links!
- **L80 · Task `[?]`** — Rename "Files” sub-tab to "Attatchments”!
- **L121 · Task `[?]`** · `^ref-agent-memory-deck-placement` — #ref [[ref/chat/agent_memory_deck_placement|A MEMORY Deck for What an Agent Was Told and Looked Up]]
- **L123 · Task `[?]`** — Start requiring a reason when artifacts are created with `sase artifact create`!
- **L143 · Task `[?]`** — Publish sase--research, bob-cli--research, articles, and papers to different AntennaPod feeds!
- **L204 · Task `[?]`** · `^ref-artifacts-files-subtab-explained` — #ref [[ref/chat/artifacts_files_subtab_explained|What are the entries on the Artifacts → Files sub-tab?]]
- **L213 · Task `[?]`** — Agents and humans should both be able to leave annotations on any artifact file!
- **L229 · Task `[?]`** · `^decisions` — ALL artifact types should support "decisions”!
- **L295 · Task `[?]`** — Figure out how to auto-link all research files that researchers read to final linked report!
- **L299 · Task `[?]`** — Rename sase-listen to sase-talk!
- **L303 · Task `[?]`** — Fix `#review_research` xprompt!
- **L358 · Task `[?]`** · `^auto-artifact` — Add `commit_hooks.artifacts` to allow users to configure which files have `sase artifact create` run on them!
- **L699 · Task `[?]`** — Link to all beads created by an agent from that agent’s page!
- **L707 · Task `[?]`** — Should `sase--ux` be used as a new artifact repo?
- **L795 · Task `[?]`** — Change `file_hooks` config field to `artifact_hooks`!
- **L845 · Task `[?]`** — Add support for explicit chat shares!
- **L1119 · Task `[?]`** — Support multiple pluggable “artifact / sidecar modes” for different orgs and use-cases!
- **L1152 · Task `[?]`** — Start publishing to agents sidecar repo when plans are approved.
- **L1203 · Task `[?]`** — Re-create Google’s snipit and use to create new `snips` sidecar repo!
- **L1219 · Task `[?]`** — Proc shells should have first-class support as sase artifacts!
- **L1343 · Idea** — Implement sidecar / submodule approach for sdd/ version-control!
- **L1352 · Idea** · `^audio-artifacts` — Generate audio summaries of content with sase?
- **L1360 · Idea** — Future work regarding new sdd/decisions/ directory: use lumberjack chop to check for changes in these files and update code based off of that?!
- **L1364 · Idea** — Start putting user feedback in “## User Feedback #`<N>`” section!
- **L1388 · Idea** — Start saving before and after versions of image files that are changed by agents and allow for a diff view.
- **L1389 · Idea** · `^user-note` — Add support for adding user notes to agents!
- **L1390 · Idea** — Start putting all research in subdir w/ `_cld` and `_cdx` suffices!
- **L1395 · Idea** — Start running `sase agent index gc` automatically!
- **L1397 · Idea** — Sase's web client should have a beautiful display of all (I.e. `#git` and `#gh`) active `sdd` repos!
- **L1429 · Idea** — The sase web client should be able to host a page per agent so we can always link to an agent (e.g. for ref notes)!
- **L1431 · Idea** — ChangeSpec are to PRs what beads are to bugs / GitHub Issues?!
- **L1432 · Idea** · `^8ff48a` — Implement sdd/events/ MVP!

### EXISTING: sase_better_plans

- **L23 · Task `[ ]`** · `^ref-auto-autonomy-epic-roadmap` — #ref [[ref/chat/auto_autonomy_epic_roadmap|%auto Autonomy: Split Into Verifiable Epics]]
- **L74 · Task `[?]`** — Allow an epic plan file to contain explicit epics!
- **L132 · Task `[?]`** — Add support to epic frontmatter for standalone procs (to wait for releases, for example)!
- **L224 · Task `[?]`** · `^land-epic-in-family` — Start launching epic lander agent in same family as agent that created epic!
- **L282 · Task `[?]`** — Always [[sase#^grill]] epics!
- **L339 · Task `[?]`** — Add support for configuring phases with `bead` (for task bead epics)!
- **L426 · Task `[?]`** — Add support for optional `wait` field for plan files!
- **L751 · Task `[?]`** — Show an option just to commit for epic gates too!
- **L983 · Task `[?]`** — Add `sase plan work` command to support tales (should wrap `sase bead work` for epics)!
- **L998 · Task `[?]`** — Unify all epic summary page content providers!
- **L1183 · Task `[?]`** · `^grill` — Add a new “Grill” option to tale/epic gate notifications!
- **L1358 · Idea** · `^fix-bad-phase-prjs` — Don’t allow phase/land epic agents to launch on wrong projects!
- **L1366 · Idea** — Make codex use `/sase_plan` later than it does? Maybe that effects its performance?
- **L1407 · Idea** · `^better_fback` — Make plan feedback way better (add feedback to stack as you scroll)!
- **L1413 · Idea** — Remove exception about smoke test agents in sase plan skill?

### EXISTING: sase_better_tasks

- **L162 · Task `[?]`** · `^bulk-gate-cmds` — Support registering bulk commands for gates!
- **L322 · Task `[?]`** — Stop showing "Repo” row in "Commits" table on bead pages!
- **L392 · Task `[?]`** · `^bead-triage-job` — Run an agent periodically (with a sase routine) to triage beads!
- **L411 · Task `[?]`** · `^bead-diff` — Add `sase bead diff [commit]` command!
- **L781 · Task `[?]`** — Adding a note on a bead that belongs to a repository you don't have permissions to should result in an external bug being created and linked to that bead.
- **L879 · Task `[?]`** — Add support to beads for specifying the xprompt that is used to run them!
- **L914 · Task `[?]`** — Add new "group” bead that can be used to link several beads together!
- **L942 · Task `[?]`** — Task beads should have a confidence level associated with them, which is determined by what level of model signed off on the bead.
- **L1044 · Task `[?]`** — Does snoozing beads actually work?!
- **L1080 · Task `[?]`** — The assignee of a bead should always be the machine hood!
- **L1111 · Task `[?]`** — Start grouping tasks and working them in groups of 20 with an xprompt swarm!

### EXISTING: sase_projects

- **L46 · Task `[/]`** · `^sase-project-stats` — Add new `sase project stats` command!
- **L169 · Task `[?]`** · `^fork-sase` — Figure out a way to emulate an unprivileged user so I can fork sase and attempt to contribute externally!
- **L178 · Task `[?]`** — INSPIRATION: A stitch provides value over a commit in how we are able to link stitches with patches (potentially cross-repo)!
- **L262 · Task `[?]`** — Create new PR for every necessary sidecar repo when PR exists for main project!
- **L353 · Task `[?]`** · `^project-model-stats` — Add details about which models were used to create plans/commits!
- **L355 · Task `[?]`** — The "Statistics” tab should be powered by `sase stats` command?!
- **L380 · Task `[?]`** · `^chezmoi` — Initialize chezmoi as sase project!
- **L643 · Task `[?]`** · `^prj-max-runners` — Add support for project-local `max_running_agents` sase config field!
- **L657 · Task `[?]`** — Syntax for targeting patches should be `+sase@foo` NOT `+sase_foo`!
- **L685 · Task `[?]`** — A “stitch” might also refer to a PR description update?!
- **L885 · Task `[?]`** — Sase needs to support multiple different users on the same machine!
- **L906 · Task `[?]`** — Factor out the `build_and_run.md` file to a sase config field (like you did with the `glossary.md` file)!
- **L973 · Task `[?]`** — Stitch Ideas!
- **L1066 · Task `[?]`** — Add support for setting project-local files (remembered even if primary clone is deleted)?!
- **L1088 · Task `[?]`** — Stop auto cloning `beads` sidecar repo!
- **L1096 · Task `[?]`** — Make any attempt to open linked repo as external fail with an error!
- **L1342 · Idea** — Implement PR comment reading!ķ- Create /sase_comments and add mentors to the agent panel (allow ,M review)! createdJune 08, 2026
- **L1373 · Idea** — ALL external repo writes should require the launch of new (parallel) agent family members?!
- **L1396 · Idea** — Add support for organizations to bare git repos?
- **L1408 · Idea** — Factor out linked repo clone cache to be general-purpose clone cache?
- **L1411 · Idea** — The `sase workspace open` command should require source (e.g. “sase” or “home”) for linked repos!

### EXISTING: sase_polish_proc_lanes

- **L347 · Task `[?]`** — Change status to `SUDOING` after approving sudo command?!
- **L398 · Task `[?]`** — Add support for project-local routines and/or jobs!
- **L515 · Task `[?]`** — Show live sase tool output in the tools panel.
- **L593 · Task `[?]`** — BUG: Standalone procs can wait for agents to complete but don't show on the Agents tab.
- **L930 · Task `[?]`** — Give each "job” its own due time to fix issues in [[lumberjack_chop_scheduling_tradeoffs]]?!
- **L988 · Task `[?]`** · `^xprocs` — Migrate Bash/Python steps to xprocs!
- **L1246 · Task `[?]`** — Add a way to snooze chops!
- **L1371 · Idea** — Start running "slow" tests as a chop!

### EXISTING: sase_monitor

- **L273 · Task `[?]`** · `^wait-for-load` — Instruct agents to use "wait for load" monitor?!
- **L289 · Task `[?]`** — Add support to `%wait` for waiting for certain global vars and/or artifact files to exist!
- **L504 · Task `[?]`** — E2E test new `%hold` directive!
- **L582 · Task `[?]`** — Allow agents to escalate to smarter agents using the `sase monitor` command?!
- **L825 · Task `[?]`** — Add `cpu=<N>.<duration>` kwarg to `%wait`!

### EXISTING: sase_pypi_releases

- **L40 · Task `[/]`** · `^ref-pypi-release-reliability-design-and` — #ref [[ref/chat/pypi_release_reliability_design_and_work_split|PyPI release reliability: the converged design and how to split the work]]
- **L44 · Task `[*]`** · `^ref-github-native-merge-queue-primer` — #ref [[ref/chat/github_native_merge_queue_primer|How GitHub's native merge queue works]]
- **L152 · Task `[?]`** — Fix sase-core clippy issues with sase post-commit hook!
- **L184 · Task `[?]`** · `^ref-merge-queue-fence-reassessment-and-epic` — #ref [[ref/chat/merge_queue_fence_reassessment_and_epic_split|Reassessing the merge-queue-fenced master plan: revised requirements and a four-epic delivery]]
- **L1126 · Task `[?]`** — Start making `just check-full` always run test suite!

### EXISTING: sase_more_agent_clis

- **L117 · Task `[?]`** · `^ref-pi-sase-provider-design` — #ref [[ref/chat/pi_sase_provider_design|Adding pi as a fully supported SASE provider]]
- **L119 · Task `[?]`** · `^ref-hermes-agent-sase-provider` — #ref [[ref/chat/hermes_agent_sase_provider|Hermes Agent as a Fully Supported SASE Provider]]
- **L482 · Task `[?]`** · `^muse-wonder` — Start using Muse Wonder for research.
- **L1031 · Task `[?]`** · `^acp` — Add ACP support? See [[ref/chat/acp_provider_design]]!
- **L1275 · Task `[?]`** — Add support for `hermes chat --oneshot` LLM provider?!
- **L1285 · Task `[?]`** — Read Muse Code docs / skills for inspiration!
- **L1410 · Idea** — Add `#m_fakey` xprompt for using `fakey` agent CLI!
- **L1430 · Idea** — Read about Antigravity (see https://antigravity.google/docs/cli-install)!

### EXISTING: sase_usage

- **L27 · Task `[ ]`** — You have 2 resets and 62K "credits” for codex!
- **L59 · Task `[?]`** — A full reset for Codex expires on the 22nd!
- **L488 · Task `[?]`** — Switch from Grok Heavy to $200 “X Subscription"?!
- **L528 · Task `[?]`** — You have a claude code reset (expires: 2026-10-22)!
- **L1061 · Task `[?]`** — Add support for model alias pools to overrides!
- **L1292 · Task `[?]`** — Cap Muse Code at $20!

### EXISTING: sase_remote

- **L137 · Task `[?]`** — I shouldn’t need to have Telegram installed on every machine!
- **L939 · Task `[?]`** — Add /fleet Telegram command that shows uptime of fleet!
- **L1335 · Idea** — Use apollo to get sase to run agents on remote machines!

### EXISTING: sase_better_config

- **L249 · Task `[?]`** — Add Macros deck!
- **L1054 · Task `[?]`** — Show all snippets on the Xprompt SASE admin center panel tab!

### EXISTING: sase_blog

- **L187 · Task `[?]`** — Sase needs a gallery?!
- **L491 · Task `[?]`** — Read like all of https://diataxis.fr website!
- **L598 · Task `[?]`** · `^re-work-documentation` — Re-work documentation in sase.sh to bare-bone basics!
- **L692 · Task `[?]`** — Set up bugyi@sase.sh email!
- **L1198 · Task `[?]`** — Add a Coverage Badge to the README.md file. [[#^h-8bacd7168c2b|🔖]]
- **L1214 · Task `[?]`** — Stabilized black feature as first use case of collaboration with SASE!
- **L1385 · Idea** — Land black string wrapping feature using sase?!
- **L1398 · Idea** — Use fable to improve docs!
- **L1412 · Idea** · `^email-gh-stars` — EMAIL: Woman back about getting sase GitHub stars!

### EXISTING: sase_better_installs

- **L350 · Task `[?]`** — Look into adding Docker support!
- **L459 · Task `[?]`** · `^windows` — Give sase Windows support!
- **L677 · Task `[?]`** — Start requiring (via `sase init`) `max_running_agents` be provided per-machine!
- **L964 · Task `[?]`** — Make sure `sase init -a` handles sidecar repos properly!
- **L1392 · Idea** — The `sase init` command should recommend installing sase-github?!
- **L1403 · Idea** — `sase init` should start prompting the user for recommended project sase.yml config fields!

### EXISTING: sase_better_vars

- **L1377 · Idea** · `^set-xprompt` — Add new `#set` xprompt that instructs agent to use `/sase_var`!

### EXISTING: sase_agents_repo

- **L554 · Task `[?]`** — Add new `%name` directive for ephemeral agent names!
- **L806 · Task `[?]`** · `^better-name-ow` — Improve the way we overwrite agent names (e.g. `%n:`)!

### EXISTING: sase_toobig_symvision

- **L367 · Task `[?]`** — Delete local/continuation/checkpoints directory in sase repo?!
- **L1332 · Idea** · `^split-file` — Factor out `#split_file` and split Rust files that are >=1000 lines!
- **L1345 · Idea** — Minimize number of methods in public_api_methods.txt!
- **L1350 · Idea** · `^pyarch` — Create `pyarch` script that lints architecture layer!

### READING: sase_ref (reading queue, not a new delivery project)

- **L20 · Task `[ ]`** · `^ref-agentic-software-engineering-reading` — #ref [[ref/chat/agentic_software_engineering_reading_list|The best recent reading on agentic software engineering]]
- **L148 · Task `[?]`** · `^ref-introducing-omnigent-meta-harness` — #ref [[ref/blogs/introducing_omnigent_meta_harness_combine_control_and_share_your_agents|Introducing Omnigent: A Meta-Harness to Combine, Control and Share Your Agents]]
- **L254 · Task `[?]`** · `^ref-reality-is-the-final-verifier-on` — #ref [[ref/papers/reality_is_the_final_verifier_on|Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering]]
- **L258 · Task `[?]`** · `^ref-astra-why` — #ref [[ref/blogs/astra_why|Astra for Coding: Why Are We Doing This Again?]]
- **L371 · Task `[?]`** · `^ref-minions-stripes-one-shot-end-to-end` — #ref [[ref/blogs/minions_stripes_one_shot_end_to_end_coding_agents|Minions: Stripe’s one-shot, end-to-end coding agents]]
- **L376 · Task `[?]`** · `^ref-my-ai-adoption-journey` — #ref [[ref/blogs/my_ai_adoption_journey|My AI Adoption Journey]]
- **L494 · Task `[?]`** · `^ref-understanding-is-the-new-bottleneck` — #ref [[ref/blogs/understanding_is_the_new_bottleneck|Understanding is the new bottleneck]]
- **L732 · Task `[?]`** · `^ref-minions-stripes-one-shot-end-to-end-2` — #ref [[ref/blogs/minions_stripes_one_shot_end_to_end_coding_agents_part_2|Minions: Stripe’s one-shot, end-to-end coding agents—Part 2]]

### OUTSIDE SASE: personal / career / home configuration

- **L192 · Task `[?]`** · `^spotify` — Give agents access to my Spotify and have them manage my playlist with Abby.
- **L748 · Task `[?]`** · `^ref-databricks-nyc-cv-and-role-pitches-2` — #ref [[ref/chat/databricks_nyc_cv_and_role_pitches_interview_prep|Interview-prep pack: Databricks NYC (Agent Quality and AI Platform)]]
- **L924 · Task `[?]`** — Try Opus with Blender.
- **L1344 · Idea** — Add `chezmoi apply` instruction to chezmoi AGENTS.md?!

### KEEP IN PARENT: strategy, small independent actions, or retirement review

- **L38 · Task `[*]`** · `^reply-rrimps-pr` — Reply to rrimps PR#301!
- **L126 · Task `[?]`** — SASE rename ideas: "power” (aka "pow"--like power user) or "po" (a nod to pi)
- **L199 · Task `[?]`** — Should sase run like claude code with the main agent(s) being the “mayor(s)” that you have access to via an actual (optional) tmux session/window?! [[ref/blogs/gas_town_emergency_user_manual#^h-d44f71098a5a|🔖]]
- **L202 · Task `[?]`** · `^ref-gascity-advantages-over-sase-and-what` — #ref [[ref/chat/gascity_advantages_over_sase_and_what_to_borrow|Gas City vs. SASE: where Gas City is ahead, and what SASE should borrow]]
- **L208 · Task `[?]`** · `^generative-jit-ux` — Enhance gates, which are "generative just-in-time interfaces"!
- **L654 · Task `[?]`** — Create eval framework mentioned by [[ref/chat/agent_platform_and_devtools_job_openings]]!
- **L745 · Task `[?]`** — "sase” rename idea: "bai" (Better/Bugyi's AI)?
- **L927 · Task `[?]`** — All live agent chats for a project should be streamed to the same message board?!
- **L1027 · Task `[?]`** — Sase rename idea: "sal"
- **L1161 · Task `[?]`** — Figure out how to invoke sase gate commands directly!
- **L1278 · Task `[?]`** — Explore the option of using tmux instead of headless CLI agents?
- **L1333 · Idea** · `^dyn-agent-fams` — Add support for dynamic agent families!
- **L1338 · Idea** — Create /sase_run xprompt skill!
- **L1340 · Idea** · `^launch-hitl` — Add a way for users to approve sase agent launches!
- **L1341 · Idea** — Install codex and try sites!
- **L1356 · Idea** — Fix `sase telemetry`!
- **L1359 · Idea** — Add keymap to merge ChangeSpec with PARENT!
- **L1400 · Idea** — Create new /show Telegram command!
- **L1418 · Idea** — Rename sase to sawi (pronounced sowwrry)?!

## Recommended project split

Adopt **five new child notes**: `sase_agent_recovery`, `sase_prompt_editor`, `sase_tui_navigation`, `sase_macro_workflows`, and `sase_completion_contracts`. Together they own **76 current open tasks and 36 plain-bullet ideas**, before deduplication. The first bounded milestones should be recovery without lost work, predictable prompt completion/history, and reliable deck focus/navigation. The macro and completion notes should initially collect design choices and dependencies rather than imply immediate implementation of all options.

Route **130 open tasks and 38 ideas** into the existing delivery children, using their existing artifact/memory substructure where appropriate. Move **eight general reading tasks** to the `sase_ref` reading queue and **three tasks plus one idea** to the relevant non-SASE areas. Retain **11 open tasks and eight ideas** in `sase.md` for small independent actions, strategy, and retirement review, in addition to its overall objective and child index. The two tmux entries and four naming entries are among the retained items that can then be consolidated further.

Do not create new general “memory,” “artifacts,” “providers,” “releases,” or “remote” notes. Those homes already exist. If a particular body of work is later selected—external-contributor support, a standalone capture client, or research/audio publication—it can become a bounded child of its assigned owner at that point.

## Overall summary

`sase.md` currently functions as a portfolio, an active task list, a scheduled backlog, a research-reading queue, and a historical idea archive. Its main themes are operator control and recovery; prompt/macro authoring; artifact and memory provenance; plans and task execution; repository/release discipline; and provider, fleet, and adoption improvements. The seven current Next & In Progress rows concern a PR reply, deck/focus/keymap fixes, release reliability, merge-queue reading, project statistics, and agent-history verification. They provide a better starting point for immediate work than the full 218-row Blocked section.

The most valuable cleanup is to establish one owner for each outcome, preserve the task graph, and distinguish deferred ideas from actual dependency blocks. Remove the exact replay duplicate, merge strong same-outcome repetitions, and explicitly resolve conflicting proposals rather than silently choosing one. Five new children plus reuse of the existing hierarchy can reduce the parent to a readable decision and coordination page without losing the source note's substantial context.
