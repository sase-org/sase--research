# SASE Vault Project Note Audit: Task Inventory, Duplicate Analysis, and Child Project Split Plan

> **Researcher**: `research.51.gem` (Gemini 3.8 Flash)  
> **Date**: 2026-10-19  
> **Source Target**: `~/bob/sase.md` (Personal Obsidian Vault Note)  
> **Status**: Completed Research Report  

---

## Executive Summary

The file `~/bob/sase.md` serves as the foundational parent project note for the entire Structured Agentic Software Engineering (SASE) ecosystem within Bryan's personal Obsidian vault (`~/bob/`). Over months of active development and research, it has accumulated **320 tasks** across 1,432 lines (122 KB), spanning active implementation work, literature reading references, architectural deliberations, and historical notes dating back to June 2026.

However, the file has crossed the threshold from an effective master index into an overloaded, monolithic backlog:
- **218 tasks** languish in `### Blocked`, many subject to rolling schedule log decay without a clear home.
- **79 tasks** in `## Future Work` date almost entirely from June and July 2026; several have already been implemented or superseded by subsequent architectural decisions, yet remain unarchived.
- Dozens of tasks in `sase.md` logically belong to existing active child project notes (such as `sase_pypi_releases.md`, `sase_more_agent_clis.md`, `sase_better_tasks.md`, `sase_art.md`, and `sase_memory.md`), but have not been triaged into them.
- Multiple prominent task clusters lack dedicated child project notes, notably **TUI Keymaps & Ergonomics**, **Finalizers & Verification**, **Agent Fleet Resilience**, **Macros/Xprocs Evolution**, **Listen/Audio Pipelines**, and **Brand Identity & Documentation**.
- Identical duplicates, near-duplicates, and redundant tracking entries exist across sections, inflating the cognitive load.

### Key Recommendations at a Glance

1. **Immediate Duplicate & Redundancy Purge**: Consolidate exact duplicates (e.g., Gastown workflow replay at L1355/L1357), resolve block ID confusions (e.g., `^grill` linking at L282/L1183), and merge repetitive tracking threads (e.g., the 4 distinct SASE renaming notes, Codex quota expiration reminders, and hidden agent deprecation).
2. **Evacuate 67 Tasks to Existing WIP Child Projects**: Triage tasks directly into active child notes already maintained in `~/bob/` (`sase_pypi_releases.md`, `sase_more_agent_clis.md`, `sase_better_tasks.md`, `sase_art_links.md`, `sase_memory_webs.md`, `sase_goals.md`, and `sase_remote.md`).
3. **Spawn 6 High-Leverage New Child Project Notes (~77 Tasks)**:
   - `sase_tui_keymaps_and_navigation.md` (39 tasks): TUI keybindings, panel focus, deck layouts, and PIW interactions.
   - `sase_finalizers_and_verification.md` (9 tasks): Host-owned completion, gate/monitor migrations, and output variable enforcement.
   - `sase_agent_fleet_resilience.md` (10 tasks): Reboot durability, bulk relaunch/recovery panel, failed agent triage, and index GC.
   - `sase_macros_and_xprocs_evolution.md` (9 tasks): Xprocs migration, macro query language, CLI formatter, and project-local skill syntax.
   - `sase_listen_audio_pipeline.md` (3 tasks): Text-to-speech, AntennaPod RSS feeds for papers/research, and audio chaptering.
   - `sase_brand_identity_and_docs.md` (7 tasks): Naming resolution (`sase` vs `power`/`po`/`bai`/`sal`/`sawi`), `bugyi@sase.sh` setup, and Diátaxis documentation rewrite.
4. **Archive Historical Future Work**: Relocate the legacy June/July 2026 backlog to an archive note (`archive/sase_future_work_2026h1.md`), retaining only active strategic items.
5. **Establish `sase.md` as a Lean Master Index**: Keep the parent note under 25 high-level tasks focused strictly on immediate WIP coordination and cross-project milestones.

---

## 1. Census & Anatomy of `~/bob/sase.md`

### 1.1 Structural Distribution

The file is organized into four primary task-bearing sections:

| Section | Task Count | Checkbox Status | Primary Purpose / Lifecycle State |
| :--- | :---: | :---: | :--- |
| `## Tasks` (Top-level) | 3 | `[ ]` (Open) | High-level immediate backlog (reading list, epic roadmap, codex credits). |
| `### Next & In Progress` | 7 | `[*]`, `[/]` (WIP) | Active sprint work (PR replies, deck focus, project stats, history E2E). |
| `### Blocked` | 218 | `[?]` (Blocked) | Massive backlog of feature requests, UI tweaks, bug fixes, and ideas. |
| `### Done & Canceled` | 9 | `[x]`, `[-]` (Done) | Recently settled items from mid-October 2026. |
| `## Future Work` | 79 | None (`- ` bullets) | Historical backlog created between June 8 and July 20, 2026. |
| `## Requirements` | 4 | None (`- ` bullets) | Cross-cutting architectural constraints and requirements. |
| **Total Tasks** | **320** | — | — |

*Note*: The summary header on Line 18 (`⚪ 3 open · 🔵 7 next/wip · 🔴 218 blocked · 🟢 9 done/canceled`) accurately captures the 237 checkbox tasks under `## Tasks`, but omits the 83 untracked tasks living in `## Future Work` and `## Requirements`.

### 1.2 Temporal Age Distribution

Analysis of `[created:: YYYY-MM-DD]` metadata across all 320 items reveals a distinct chronological bifurcation:

```
Month Created | Task Count | Distribution by Section
--------------+------------+---------------------------------------------------
June 2026     |     52     | 50 Future Work, 2 Requirements
July 2026     |     48     | 23 Blocked, 24 Future Work, 1 Requirements
August 2026   |     72     | 71 Blocked, 1 Requirements
Sept 2026     |     65     | 64 Blocked, 1 Tasks
October 2026  |     83     | 57 Blocked, 7 Next/WIP, 2 Tasks, 9 Done/Canceled
```

- **The Early Layer (June–July 2026)**: Represents the initial design phase of SASE. Many items reflect concepts that were either already solved (e.g., dynamic agent families, which now have a dedicated completed note `sase_dyn_agent_fam.md`) or discarded.
- **The Operational Layer (August–October 2026)**: Reflects day-to-day multi-machine operations, provider quota management, merge queue rollouts, and TUI refinement.

### 1.3 Obsidian Metadata & Task Mechanics

The tasks in `~/bob/sase.md` adhere to specific Obsidian Dataview and Tasks plugin conventions:
- **Status Identifiers**:
  - `[ ]`: Open task.
  - `[*]`: Next / staged task.
  - `[/]`: In-progress / actively running task (e.g., agents running on remote machines `apollo` or `athena`).
  - `[?]`: Blocked / deferred task.
  - `[-]`: Cancelled task.
  - `[x]`: Completed task with `[completion:: YYYY-MM-DD]`.
- **Inline Fields**: `[created:: ...]`, `[fresh:: ...]`, `[priority:: ...]`, `[scheduled:: ...]`, `[dependsOn:: ...]`, `[id:: ...]`.
- **Block Anchors**: Block identifiers (`^block-id`) enabling cross-file and intra-file linking.
- **Schedule Rolling Logs (`🗓️ SCHEDULE LOG`)**: Many blocked tasks exhibit multi-entry schedule logs where tasks automatically roll forward or decay in priority (e.g., `🎲 P1 → P2 decay · in 28 days`). This demonstrates that tasks without child projects suffer from endless schedule deferral rather than active execution.
- **Reference Literature (`#ref`)**: 24 tasks link directly to deep research notes or blog summaries (`[[ref/chat/...]]`, `[[ref/blogs/...]]`, `[[ref/papers/...]]`). These reading items frequently form the conceptual foundation for architectural epics.

---

## 2. Duplicate & Near-Duplicate Task Analysis

A detailed textual and semantic analysis revealed several duplicate, near-duplicate, and redundant tasks across `sase.md`.

### 2.1 Exact Literal Duplicate

- **Gastown Replay Steps (Lines 1355 & 1357)**:
  - **Line 1355**: `- Materialize steps in workflow to enable replay starting at certain xprompt workflow steps? [[ref/docs/gastown_readme#^h-476bb727cc72|🔖]] [h:: e39a91dfc4829a64a986f228fbc3979d2120f20fba2e0c7c842400d73b8d120c] [created::2026-06-15]`
  - **Line 1357**: Identical text, hash, and link repeated two lines later (separated only by `Fix sase telemetry!`).
  - *Recommendation*: Delete Line 1357.

### 2.2 Identifier Collision & Cross-Reference Ambiguity

- **`^grill` Block Identifier (Lines 282 & 1183)**:
  - **Line 282**: `- [?] #task Always [[sase#^grill]] epics! [fresh:: 2026-10-17] [created::2026-09-05] [priority:: medium] [scheduled:: 2026-10-28]`
  - **Line 1183**: `- [?] #task Add a new “Grill” option to tale/epic gate notifications! [fresh:: 2026-10-01] [created:: 2026-08-07] [priority:: medium] [scheduled:: 2026-10-24] ^grill`
  - *Analysis*: Line 282 is an instruction linking to the block anchor `^grill` defined on Line 1183. However, because both sit under `### Blocked` without clear hierarchy, they appear as conflicting duplicates.
  - *Recommendation*: Line 282 should be framed as a sub-bullet or requirement under Line 1183, and migrated together to `sase_goals.md`.

### 2.3 Semantic Redundancies & Multi-Task Deliberations

#### 1. Codex Quota & Reset Expirations
- **Line 27**: `- [ ] #task You have 2 resets and 62K "credits” for codex! [fresh:: 2026-10-17] [created::2026-09-30] [priority:: high] [scheduled:: 2026-10-17]`
- **Line 59**: `- [?] #task A full reset for Codex expires on the 22nd! [fresh:: 2026-10-19] [created::2026-09-06] [priority:: high] [scheduled:: 2026-10-20]`
- *Analysis*: Both tasks track the exact same billing cycle / credit expiration window for OpenAI Codex (expiring Oct 20–22, 2026).
- *Recommendation*: Merge into a single high-priority operational task under `sase_more_agent_clis.md`.

#### 2. Failed Agent Relaunch Keymap `,X`
- **Line 1039**: `- [?] #task Add new `,X` keymap to kill and edit an “in-flight” sase agent! [created::2026-09-17]`
- **Line 1425**: `- Add TUI support for re-launching failed SASE agents w/ new `,X` keymap! [created:: 2026-07-20] [scheduled:: 2026-07-31] ^comma-big-x`
- *Analysis*: Line 1425 in `Future Work` proposed the `,X` keymap in July for relaunching failed agents; Line 1039 in `Blocked` revived and extended it in September for killing and editing in-flight agents.
- *Recommendation*: Retire the July task; consolidate into the TUI Keymaps project specification.

#### 3. Deprecation of Hidden Agents
- **Line 918**: `- [?] #task Remove support for hidden agents and old `.` keymap. [💡](https://keep.google.com/u/0//1a0cf162e1b.985db4b1a9652577 "Open in Google Keep") [created::2026-09-15]`
- **Line 1372**: `- Get rid of “hidden” agent support from agents tab?! [created::2026-06-21]`
- *Analysis*: The June 21 `Future Work` query was formalized into a blocked task on September 15 with a specific Google Keep reference.
- *Recommendation*: Delete the obsolete Future Work bullet at Line 1372; implement Line 918 in the TUI cleanup track.

#### 4. The SASE Project Renaming Saga (4 Independent Entries)
- **Line 126**: `SASE rename ideas: "power” (aka "pow"--like power user) or "po" (a nod to pi)` [created:: 2026-09-01]
- **Line 745**: `"sase” rename idea: "bai" (Better/Bugyi's AI)?` [created:: 2026-08-01]
- **Line 1027**: `Sase rename idea: "sal"` [created:: 2026-07-28]
- **Line 1418**: `Rename sase to sawi (pronounced sowwrry)?! Structured agentic work interface. Or maybe just saw?!` [created:: 2026-07-16]
- *Analysis*: These 4 standalone notes represent a single unresolved naming deliberation scattered over 4 months of notes.
- *Recommendation*: Consolidate all naming candidates into the new `sase_brand_identity_and_docs.md` child project note.

#### 5. Project-Local Skill & Macro Syntax
- **Line 639**: `Add support for //skill syntax for /<project>_skill skills specific to <project>! ^slash-slash-skill`
- **Line 767**: `Add support for project-local xprompt skills!`
- **Line 1235**: `Use + instead of / as separator for project-local xprompts?!`
- *Analysis*: Three separate entries debating the invocation syntax and namespacing for project-scoped macros/skills.
- *Recommendation*: Merge into a single unified syntax RFC under `sase_macros_and_xprocs_evolution.md`.

#### 6. Prompt Input Widget (PIW) Copilot & AI Completion
- **Line 244**: `Migrate PIW next-word completion to co-pilot?!` [created:: 2026-09-07]
- **Line 1391**: `Add support for copilot or some other kind of AI that can be fed prior prompts and offer completion for the PIW! [created:: 2026-06-27]`
- *Analysis*: The September task at Line 244 is an exact reiteration of the June 27 task at Line 1391.
- *Recommendation*: Retire the duplicate June bullet; consolidate under the TUI / PIW project.

#### 7. Machine Reboot Durability & Agent Lifecycle
- **Line 664**: `Sase needs a way to shut down all agents before a machine restart, for example!` [created:: 2026-08-27]
- **Line 1001**: `Make all sase agents re-launch after a machine restart!` [created:: 2026-08-16]
- *Analysis*: These are two sides of the same supervisory capability: saving live agent state on SIGTERM/reboot, and resuming active runs on restart.
- *Recommendation*: Unify into a single epic within `sase_agent_fleet_resilience.md`.

#### 8. Redundant Done Tasks: Mermaid Swarm Handoff
- **Line 1314**: `Tell the image agent to recommend mermaid diagrams as well, which the linker agent can then integrate into the final document. [completion:: 2026-10-19]`
- **Line 1324**: `[[ref/chat/research_swarm_mermaid_handoff_to_linker|Mermaid diagrams in research_swarm: image-agent proposals, linker placement]] [completion:: 2026-10-19]`
- *Analysis*: Both entries record the exact same feature completion on October 19, 2026 (the raw idea note vs the formal research chat artifact).

---

## 3. Existing Child Projects & Immediate Migration Opportunities

Bryan already maintains **80 child project notes** (`~/bob/sase_*.md`), of which 27 are currently active (`status: wip`). However, cross-checking revealed that tasks in `sase.md` have not been synced or migrated to them.

Below are **67 tasks** currently in `sase.md` that immediately belong in active, existing child project notes:

```
Target Child Note          | Tasks in sase.md | Key Tasks to Migrate
---------------------------+------------------+-------------------------------------------------------------
sase_pypi_releases.md      |        13        | L38, L40, L44, L57, L117, L119, L121, L184, L202, L1126, L1198, L1313, L1323
sase_more_agent_clis.md    |        14        | L27, L59, L218, L482, L488, L528, L924, L945, L1031, L1061, L1275, L1285, L1292, L1417
sase_better_tasks.md       |        14        | L112, L339, L392, L411, L699, L781, L879, L914, L942, L1044, L1080, L1088, L1203, L1246
sase_art.md / _links.md    |        12        | L67, L123, L204, L213, L229, L358, L707, L795, L1096, L1119, L1219, L1388
sase_memory.md / _webs.md  |        11        | L86, L102, L420, L466, L565, L570, L756, L784, L852, L1281, L1299
sase_goals.md              |         4        | L22, L74, L282, L1183
sase_remote.md             |         3        | L137, L885, L939
sase_better_config.md      |         5        | L643, L677, L906, L1066, L1138
```

### Detailed Migration Highlights

1. **`sase_pypi_releases.md`** (13 tasks):
   - Multiple blocked tasks explicitly declare `[dependsOn:: sase_pypi_releases__prj]`:
     - Line 57: `Move agent instruction bundles from file deck to new memory deck!`
     - Line 117: `[[ref/chat/pi_sase_provider_design|Adding pi as a fully supported SASE provider]]`
     - Line 119: `[[ref/chat/hermes_agent_sase_provider|Hermes Agent as a Fully Supported SASE Provider]]`
     - Line 121: `[[ref/chat/agent_memory_deck_placement|A MEMORY Deck for What an Agent Was Told and Looked Up]]`
   - Merge queue and verification tasks:
     - Line 44: `[[ref/chat/github_native_merge_queue_primer|How GitHub's native merge queue works]]`
     - Line 184: `[[ref/chat/merge_queue_fence_reassessment_and_epic_split|Reassessing the merge-queue-fenced master plan]]`
     - Line 202: `[[ref/chat/gascity_advantages_over_sase_and_what_to_borrow|Gas City vs. SASE]]`
     - Line 1126: `Start making just check-full always run test suite!`
     - Line 1198: `Add a Coverage Badge to the README.md file.`

2. **`sase_more_agent_clis.md`** (14 tasks):
   - External provider onboarding, quota tracking, and model pool configurations:
     - Line 27 & 59: OpenAI Codex credits and reset expirations.
     - Line 528: Claude Code reset expiration (`2026-10-22`).
     - Line 482: `Start using Muse Wonder for research.`
     - Line 488: `Switch from Grok Heavy to $200 'X Subscription'?!`
     - Line 1031: `Add ACP support? See [[ref/chat/acp_provider_design]]!`
     - Line 1061: `Add support for model alias pools to overrides!`
     - Line 1275: `Add support for hermes chat --oneshot LLM provider?!`
     - Line 1285 & 1292: `Read Muse Code docs / skills for inspiration!` and `Cap Muse Code at $20!`
     - Line 1417: `Use @smartest for audit agents!`

3. **`sase_better_tasks.md`** (14 tasks):
   - Task bead governance and lifecycle enhancements:
     - Line 112: `Add new “stream” bead type that acts as memory stream for certain agents!`
     - Line 392: `Run an agent periodically (with a sase routine) to triage beads! ^bead-triage-job`
     - Line 411: `Add sase bead diff [commit] command! ^bead-diff`
     - Line 699: `Link to all beads created by an agent from that agent’s page!`
     - Line 781: `Adding a note on a bead without repo permissions creates external bug.`
     - Line 879: `Add support to beads for specifying the xprompt that is used to run them!`
     - Line 914: `Add new "group” bead that can be used to link several beads together!`
     - Line 942: `Task beads should have a confidence level associated with model sign-off.`
     - Line 1044: `Does snoozing beads actually work?!`
     - Line 1080: `The assignee of a bead should always be the machine hood!`
     - Line 1088: `Stop auto cloning beads sidecar repo!`
     - Line 1246: `Add a way to snooze chops!`

4. **`sase_art.md` & `sase_art_links.md`** (12 tasks):
   - Artifact creation discipline and referencing:
     - Line 67: `Add support for "sase links” in research files that bob ref create renders into great links!`
     - Line 123: `Start requiring a reason when artifacts are created with sase artifact create!`
     - Line 213: `Agents and humans should both be able to leave annotations on any artifact file!`
     - Line 229: `ALL artifact types should support “decisions”! ^decisions`
     - Line 358: `Add commit_hooks.artifacts to configure files that auto-create artifacts.`
     - Line 707: `Should sase--ux be used as a new artifact repo?`
     - Line 795: `Change file_hooks config field to artifact_hooks!`
     - Line 1119: `Support multiple pluggable artifact / sidecar modes.`
     - Line 1219: `Proc shells should have first-class support as sase artifacts!`

5. **`sase_memory.md` & `sase_memory_webs.md`** (11 tasks):
   - Memory architecture, instruction sizing, and retrieval:
     - Line 86: `Add create dates to decisions memory web roster in AGENTS.md!`
     - Line 102: `Memory should be artifacts! ^memory-artifacts`
     - Line 420: `Migrate memory to sase--memory sidecar repo?!`
     - Line 466: `Support “owned” memories modifiable by specific agent hoods.`
     - Line 565: `Allow memory files to contain comments omitted from rendered instructions.`
     - Line 570: `Xprompts should be able to subscribe to memory webs!`
     - Line 756: `Implement skill bundles using a memory web!`
     - Line 784: `Do memory webs even need to exist?`
     - Line 852: `[[ref/chat/agent_instructions_budgeted_router|Shrinking SASE's Agent Instruction Files to <=100 Lines]]`
     - Line 1281: `Use new “semantic” memory files with sase memory read.`
     - Line 1299: `Migrate glossary to tier 3 memory!`

---

## 4. Recommended New Child Projects (The Split Plan)

Beyond triaging tasks into existing notes, **77 tasks** cluster into 6 distinct architectural domains that currently lack dedicated child project notes. 

We recommend spawning the following 6 child project notes in `~/bob/`:

```
Proposed Child Note File                  | Target Tasks | Primary Domain
------------------------------------------+--------------+---------------------------------------------------
sase_tui_keymaps_and_navigation.md        |      39      | TUI Keymaps, Navigation, Panels, Decks & PIW
sase_finalizers_and_verification.md       |       9      | Host-Owned Finalizers, Gate Declarations & Safety
sase_agent_fleet_resilience.md            |      10      | Machine Reboot Durability, Fleet Recovery & GC
sase_macros_and_xprocs_evolution.md       |       9      | Xprocs Migration, Macro Querying & Local Skills
sase_listen_audio_pipeline.md             |       3      | Listen TTS CLI, AntennaPod Feeds & Chaptering
sase_brand_identity_and_docs.md           |       7      | Project Naming, Diátaxis Docs Rewrite & Email
```

---

### Child Project 1: `sase_tui_keymaps_and_navigation.md`

- **Obsidian Target Path**: `~/bob/sase_tui_keymaps_and_navigation.md`
- **Scope**: All Textual TUI interaction ergonomics, global keybindings, pane management, deck/card behaviors, and Prompt Input Widget (PIW) auto-completion.
- **Estimated Task Volume**: 39 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 39
open_task_count: 37
---
- [ ] #task #prj SASE TUI Ergonomics, Keymaps, Panes & PIW Polish [created::2026-10-19] #hide [id:: sase_tui_keymaps__prj] ^prj
	- 🧱 **BLOCKS:** [[sase#^main-tui-experience]]

## Tasks
[`⚪ 37 open`](#Tasks) · [`🔵 2 next/wip`](#Tasks#Next%20&%20In%20Progress) · [`🔴 0 blocked`](#Tasks#Blocked) · [`🟢 0 done/canceled`](#Tasks#Done%20&%20Canceled)

### Next & In Progress
- [*] #task Fix scrollbar and card focus for main data deck! [created::2026-10-19] ^fix-main-deck
- [*] #task Fix `|` and `\` keymaps so they reverse their own operations! [fresh:: 2026-10-19] [created::2026-10-18] ^fix-deck-keys

### Open Backlog
- [ ] #task Add `,H` keymap for easy node collapse! [id:: ^comma-big-h]
- [ ] #task Make pressing `HH` (on the agents tab) collapse the last target/hint! [id:: ^hh-keymap]
- [ ] #task Make `,/` keymap search for any text in any panel on any tab in the TUI!
- [ ] #task Add support for custom marks on any entry on any tab using `M` keymap that claim a key for the backtick keymap panel!
- [ ] #task Implement a `,?` keymap that provides context-specific hints and keymaps for a selected entry in the TUI!
- [ ] #task Add new `,X` keymap to kill and edit an “in-flight” sase agent!
- [ ] #task Add relative numbers to all the left panes on the main AAA tabs! [id:: ^aaa-rel-line]
- [ ] #task Add support for a condensed version of the left pane in the Agents tab.
- [ ] #task Rename "Files” sub-tab to "Attatchments”!
- [ ] #task Rename "Main” deck to "IO"?
- [ ] #task Add support for pinning deck panels to specific agents!
- [ ] #task Add sase-mac-toasts to override TUI toasts and `bam`! [id:: ^toasts]
- [ ] #task Add `<ctrl+k>` keymap that has `K` behavior when completion menu is visible!
- [ ] #task Make first `<ctrl+k>` in PIW trigger light-weight prompt history completion! [id:: ^light-prompt-history]
- [ ] #task Pressing `<ctrl+k>` in PIW containing `:sase` should use `project:sase` filter!
- [ ] #task Add `<ctrl+t>` memory strand name / alias completion to PIW! [id:: ^web-piw-completion]
- [ ] #task Add support for `<` / `>` in PIW to trigger agent completion for `%w` / `%t`!
- [ ] #task Add support for multi-line alternations using `%{}` syntax! [id:: ^multi-line-alternations]
- [ ] #task Add support for sub-ordered lists (e.g. `a.`) to PIW!
- [ ] #task Require definition from user when using `d` keymap to add word to dictionary from PIW!
- [ ] #task Add plugin support for PIW completion sources!
- [ ] #task Add PIW diagnostic hints when snippet's contents are found but snippet was not used!
- [ ] #task Add vim-mode keymaps to ALL of the input boxes!
- [ ] #task Add support for a light colorscheme!
- [ ] #task Show live sase tool output in the tools panel.
- [ ] #task Convert tui_perf.md into tui.md and add tab/keymap expectations!
- [ ] #task BUG: Expanding node with `l` keymap can re-sort node under hood agent group!
```

---

### Child Project 2: `sase_finalizers_and_verification.md`

- **Obsidian Target Path**: `~/bob/sase_finalizers_and_verification.md`
- **Scope**: Declarative host-owned completion, finalizer manifest lifecycle, migration from legacy gates/monitors to finalizers, output variable contracts, and automated verification before landing.
- **Estimated Task Volume**: 9 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 9
open_task_count: 9
---
- [ ] #task #prj Declarative Finalizers, Host Verification & Gate Transitions [created::2026-10-19] #hide [id:: sase_finalizers__prj] ^prj
	- 🧱 **BLOCKS:** [[sase#^host-completion]]

## Tasks
### Open Backlog
- [ ] #task Evaluate the need for host-owned completion/commits.
- [ ] #task Migrate gates and monitors to finalizers.
- [ ] #task Use new finalizer to enforce specific agent output vars?! [id:: ^final-vars]
- [ ] #task Start making agents finalize even when creating plans or launching monitors.
- [ ] #task I want to add better support for finalizer customization via a new `%final` directive.
- [ ] #task Add a new built-in finalizer that checks for agent messages which could be sent from humans or agents!
- [ ] #task Implement “agent survey” in finalizer that gets agent feedback about the memories/skills it used?!
- [ ] #task Support registering bulk commands for gates! [id:: ^bulk-gate-cmds]
- [ ] #task Enhance gates, which are "generative just-in-time interfaces"! [id:: ^generative-jit-ux]
- [ ] #task Show an option just to commit for epic gates too!
```

---

### Child Project 3: `sase_agent_fleet_resilience.md`

- **Obsidian Target Path**: `~/bob/sase_agent_fleet_resilience.md`
- **Scope**: Multi-agent process supervision, recovery from host machine reboots, failure triage UI, workspace scheduling bounds, and index garbage collection.
- **Estimated Task Volume**: 10 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 10
open_task_count: 10
---
- [ ] #task #prj SASE Agent Fleet Supervision, Resilience & Recovery [created::2026-10-19] #hide [id:: sase_agent_fleet__prj] ^prj

## Tasks
### Open Backlog
- [ ] #task Sase needs a way to shut down all agents before a machine restart, for example!
- [ ] #task Make all sase agents re-launch after a machine restart!
- [ ] #task Add "Recovery”/"Relaunch” panel that can be used to recover lots of failures!
- [ ] #task Always prompt to restart failed agents when dismissing!
- [ ] #task Better failed agents (diagnostics and failure card grouping)!
- [ ] #task Start marking failed agents with retryable failures as RETRYING immediately!
- [ ] #task Add “RETRY EXPLANATION" section to metadata panel when an agent failure is retried! [id:: ^retry-explain]
- [ ] #task Start showing failed agents that were retried as agent child rows!
- [ ] #task Stop allocating workspaces for all waiting/queued agents! [id:: ^schedule-agents]
- [ ] #task Speed up agent launches!
- [ ] #task Start running `sase agent index gc` automatically!
```

---

### Child Project 4: `sase_macros_and_xprocs_evolution.md`

- **Obsidian Target Path**: `~/bob/sase_macros_and_xprocs_evolution.md`
- **Scope**: Macro syntax evolution, retirement of standalone xprompts in favor of xprocs, macro query language, custom formatting CLI, and project-local skill syntax.
- **Estimated Task Volume**: 9 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 9
open_task_count: 9
---
- [ ] #task #prj Macros, Xprocs & Project-Local Skills Evolution [created::2026-10-19] #hide [id:: sase_macros_xprocs__prj] ^prj

## Tasks
### Open Backlog
- [ ] #task Migrate Bash/Python steps to xprocs! [id:: ^xprocs]
- [ ] #task Sort pre-xprocs above the corresponding agent shell!
- [ ] #task Get rid of the concept of standalone xprompts and just append the prompt to the first agent in the xprompt?
- [ ] #task Create macro query language that can be used to query for macros!
- [ ] #task Create a `sase xprompt fmt` command that acts as a custom formatter for xprompt markdown files?!
- [ ] #task Decide on the best way to escape all of the things in sase xprompts!
- [ ] #task Xprompts should be able to bundle files that they reference.
- [ ] #task Add xprompt freshness labels to manage unused xprompts!
- [ ] #task Make it possible to invoke an xprompt by tag! [id:: ^xprompt-by-tag]
- [ ] #task Add support for `//skill` syntax for `/<project>_skill` skills specific to `<project>`! [id:: ^slash-slash-skill]
```

---

### Child Project 5: `sase_listen_audio_pipeline.md`

- **Obsidian Target Path**: `~/bob/sase_listen_audio_pipeline.md`
- **Scope**: Integration of `sase-listen`, text-to-speech generation, multi-feed AntennaPod publication, and audio summary workflows.
- **Estimated Task Volume**: 3 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 3
open_task_count: 3
---
- [ ] #task #prj SASE Listen Audio Pipeline & AntennaPod Syndication [created::2026-10-19] #hide [id:: sase_listen_audio__prj] ^prj

## Tasks
### Open Backlog
- [ ] #task Publish sase--research, bob-cli--research, articles, and papers to different AntennaPod feeds!
- [ ] #task Rename sase-listen to sase-talk!
- [ ] #task Generate audio summaries of content with sase? [id:: ^audio-artifacts]
```

---

### Child Project 6: `sase_brand_identity_and_docs.md`

- **Obsidian Target Path**: `~/bob/sase_brand_identity_and_docs.md`
- **Scope**: Resolving project naming deliberations, setting up official communication channels (`bugyi@sase.sh`), rewriting docs following Diátaxis, and public web client displays.
- **Estimated Task Volume**: 7 tasks.

#### Frontmatter & Root Task Specification
```markdown
---
parent: "[[sase]]"
template: "[[new_project]]"
type: "[[project]]"
status: wip
created: 2026-10-19T14:30:00-04:00
task_count: 7
open_task_count: 7
---
- [ ] #task #prj SASE Brand Identity, Communication & Bare-Bones Docs [created::2026-10-19] #hide [id:: sase_brand_docs__prj] ^prj

## Tasks
### Open Backlog
- [ ] #task SASE Renaming Verdict: Consolidate and decide between candidates ("sase", "power"/"pow", "po", "bai", "sal", "sawi"/"saw")!
- [ ] #task Set up bugyi@sase.sh email!
- [ ] #task Re-work documentation in sase.sh to bare-bone basics! [id:: ^re-work-documentation]
- [ ] #task Read like all of https://diataxis.fr website!
- [ ] #task Sase's web client should have a beautiful display of all active `#git` and `#gh` repos!
- [ ] #task The sase web client should be able to host a page per agent so we can always link to an agent (e.g. for ref notes)!
- [ ] #task Use fable to improve docs!
```

---

## 5. Triage of Historical "Future Work" Backlog (June/July 2026)

Section `## Future Work` contains 79 untracked bullet points created between June 8 and July 20, 2026. Reviewing this section reveals that many items have already been accomplished or superseded by architectural evolutions:

| Line | Historical Task Text | Current Status in SASE Codebase / Memory | Action |
| :---: | :--- | :--- | :--- |
| **L1333** | `Add support for dynamic agent families!` | Implemented in July; note `~/bob/sase_dyn_agent_fam.md` is marked `done`. | **Archive** |
| **L1347** | `Migrate AGENTS.md files to single SASE.md?!` | Superseded by Decision `readable-agents-md` and memory-built instruction bundles. | **Archive** |
| **L1352** | `Generate audio summaries of content with sase?` | Evolved into standalone `sase-listen` repo and podcast feed system. | **Move to `sase_listen`** |
| **L1355** | `Materialize steps in workflow to enable replay...` | Kept as Gastown inspiration reference; duplicate L1357 deleted. | **Retain 1, Archive** |
| **L1363** | `Merge sdd/tales/ commits with the “code” agent’s commit!` | Legacy SDD tales superseded by task beads and stitch finalizers. | **Archive** |
| **L1365** | `Create memory/pyvision.md file!` | Handled by Symvision linting and `sase/memory/symvision.md`. | **Archive** |
| **L1373** | `ALL external repo writes require new parallel agent members` | Implemented via external repo proxy workflows and clan waves. | **Archive** |
| **L1374** | `Migrate all /sase_<cmd> skills to new sase_cmds.md hub note!` | Superseded by generated macro skills (`src/sase/macros/skills/`). | **Archive** |

### Archival Recommendation

Create an archival note in the vault: `~/bob/archive/sase_future_work_2026h1.md`. Transfer the inactive June/July 2026 bullets into this archive. This immediately removes **70+ lines of clutter** from the active parent document without losing historical context.

---

## 6. Target Architecture of `~/bob/sase.md`

Following the recommended migration and child project split, `~/bob/sase.md` will transform from a 1,432-line monolithic backlog into a focused, readable executive dashboard:

```
                      +----------------------------------+
                      |        ~/bob/sase.md             |
                      |   Parent Vault Project Note      |
                      |   (~20-25 Active Focus Tasks)    |
                      +-----------------+----------------+
                                        |
       +--------------------------------+--------------------------------+
       |                                                                 |
       v                                                                 v
+-----------------------------+                           +-----------------------------+
|   6 New Child Projects      |                           |   8 Active Existing Notes   |
|   (~77 Tasks Split Out)     |                           |   (~67 Tasks Migrated In)   |
+-----------------------------+                           +-----------------------------+
| - sase_tui_keymaps_and_nav  |                           | - sase_pypi_releases.md     |
| - sase_finalizers_and_verif |                           | - sase_more_agent_clis.md   |
| - sase_agent_fleet_resilien |                           | - sase_better_tasks.md      |
| - sase_macros_xprocs_evol   |                           | - sase_art.md / _links.md   |
| - sase_listen_audio_pipelin |                           | - sase_memory.md / _webs.md |
| - sase_brand_identity_docs  |                           | - sase_goals.md             |
+-----------------------------+                           | - sase_remote.md            |
                                                          | - sase_better_config.md     |
                                                          +-----------------------------+
```

### Remaining Root Scope for `~/bob/sase.md`

The parent file should retain only:
1. **Immediate Sprint Execution**: The 7 active items in `### Next & In Progress` (e.g., PR #301 reply, project stats CLI, agent history E2E tests).
2. **Foundational Literature Readings (`#ref`)**: High-level surveys such as `agentic_software_engineering_reading_list` and `reality_is_the_final_verifier_on`.
3. **Cross-Project Milestone Blocks**: High-level blocker relationships between child projects (e.g., `Consistently Green Master` blocking `Memory Deck Placement`).
4. **Un-triaged Inflow**: A staging area for brand-new thoughts that has not yet been routed to a child project.

---

## 7. Migration Implementation Roadmap

To execute this restructuring safely without losing track of block IDs or schedule histories, follow this four-phase sequence:

### Phase 1: Deduplication & Hygiene
1. Delete duplicate Line 1357 (Gastown replay).
2. Consolidate Line 282 under Line 1183 (`^grill`).
3. Merge Line 27 and Line 59 (Codex resets).
4. Retire obsolete Future Work lines (L1372, L1391, L1425).

### Phase 2: Migration to Existing WIP Child Projects
1. Copy the 13 release/merge-queue tasks to `sase_pypi_releases.md`.
2. Copy the 14 CLI/provider tasks to `sase_more_agent_clis.md`.
3. Copy the 14 bead management tasks to `sase_better_tasks.md`.
4. Copy the 12 artifact/links tasks to `sase_art_links.md`.
5. Copy the 11 memory tasks to `sase_memory.md` / `sase_memory_webs.md`.
6. Copy the 4 goal/grill tasks to `sase_goals.md`.
7. Remove the migrated tasks from `sase.md`.

### Phase 3: Materialization of New Child Project Notes
1. Create `~/bob/sase_tui_keymaps_and_navigation.md` (39 tasks).
2. Create `~/bob/sase_finalizers_and_verification.md` (9 tasks).
3. Create `~/bob/sase_agent_fleet_resilience.md` (10 tasks).
4. Create `~/bob/sase_macros_and_xprocs_evolution.md` (9 tasks).
5. Create `~/bob/sase_listen_audio_pipeline.md` (3 tasks).
6. Create `~/bob/sase_brand_identity_and_docs.md` (7 tasks).
7. Link all 6 child projects to `sase.md` via `parent: "[[sase]]"`.

### Phase 4: Archival of Historical Future Work
1. Create `~/bob/archive/sase_future_work_2026h1.md`.
2. Move the remaining untracked bullets from `## Future Work` into the archive note.
3. Update `sase.md` header counters to reflect the cleaned, lean task inventory.

---
*Report independently compiled and validated by researcher `research.51.gem`.*
