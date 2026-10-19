# Splitting `~/bob/sase.md` into child project notes

*Researcher: cld · 2026-10-19 · Source: `~/bob/sase.md` (1,432 lines, modified 2026-10-19 13:00), read alongside its 27 open child and grandchild project notes and `done/sase_done.md`. Line numbers (`L123`) refer to that snapshot of `sase.md`. Nothing in the vault was edited.*

## TL;DR

- **`sase.md` has turned into a catch-all.** It holds **228 open tasks**: 3 `[ ]`, 7 next/WIP, and 218 `[?]`. It also has 79 Future Work bullets and 4 Requirements bullets. All 27 open child and grandchild notes together hold only about 100 open tasks, so the hub carries roughly 70% of the open SASE work. Most `[?]` tasks are waiting on a date, not on another task: `bob ready sase` shows only **10** with real dependencies.
- **Duplicates and drift:**
  - **1 exact duplicate**
  - **14 near-duplicate pairs, triples, or quadruples** to merge
  - **4 contradictions**
  - **~20 items that are already done or superseded**
  - **14 duplicates that cross into child notes** (§2)
- **Recommended split** (§3; every task's destination is in Appendix A):
  - Route **81 tasks into 17 existing children**.
  - Create **8 new children now**, covering 108 tasks.
  - Keep **4 optional children** (25 tasks) for later.
  - Move **8 non-SASE tasks out** of the SASE tree.
  - Leave **6 cross-cutting tasks** in the hub.
- **Biggest themes:**
  - TUI keymaps and decks (23)
  - Macro language (19)
  - Memory (16)
  - Artifacts (15)
  - The prompt input widget (PIW) (13)
  - Waits and queues (12)
  - Agent completion: finalizers, stitches, and PRs (12)
  - Community and outside contributors (12)

---

## 1. Inventory: what is in `sase.md` today

| Section | Count | Notes |
| --- | ---: | --- |
| `## Tasks` (open `[ ]`) | 3 | L20, L23 (reading refs), L27 (Codex credits reminder) |
| `### Next & In Progress` | 7 | 5 `[*]` next, 2 `[/]` WIP (PyPI release reliability E1, `sase project stats` epic) |
| `### Blocked` (`[?]`) | 218 | Mostly snoozed by the 🎲 schedule reroll. Only 11 carry `dependsOn`, and `bob ready` counts 10 as truly blocked |
| `### Done & Canceled` | 9 | Waiting for `bob task archive` |
| `## Future Work` | 79 bullets | Plain bullets, not tasks. 74 are dated June–July 2026 (50 June, 24 July); 5 are undated. Nothing newer has been added |
| `## Requirements` | 4 bullets | |

**Open-task profile (228):**

| Measure | Breakdown |
| --- | --- |
| Priority | medium 144 · high 33 · low 32 · lowest 1 · none 18 |
| Created | Jun 2 · Jul 23 · Aug 71 · Sep 65 · Oct (to the 19th) 66 · undated 1 |
| Source | 19 `#ref` reading/research tasks · 21 Google Keep captures (💡) |

October is on pace to be the busiest intake month so far.

**Structural observations**

1. **Existing children are thin.** 22 open children appear in the Sub-projects line. `bob projects list` shows most with 2–5 open tasks, all scheduled out. Several (`sase_better_tasks`, `sase_better_plans`, `sase_better_installs`, `sase_skill_bundles`, `sase_better_config`, `sase_projects`) have only 1–2 open tasks, while matching work sits in the hub.
2. **The hub's high-priority items are mostly not product work.**
   - 7 of the 9 reading refs are `high`.
   - 5 of the 8 personal/billing reminders (Codex/Claude resets, Grok → X subscription, Spotify) are `high`.
   - Product tasks are overwhelmingly `medium`.
3. **Future Work uses retired terms:**
   - `sdd/` (L1134 "Remove ALL references to SDD" is still open)
   - ChangeSpec (renamed to patch 2026-08-23)
   - xprompt (renamed to macro 2026-10-06)
   - lumberjack/chop (renamed 2026-09-23)
   - `~/memory/long/`
4. **Dangling link.** `[[sase_v19]]` (L757 and `sase_goals`) points to a note that does not exist.
5. **Formatting glitch.** L1342 fuses two bullets into one line, with a stray `ķ` and `createdJune 08, 2026`.

---

## 2. Duplicates, overlaps, and stale items

### 2.1 Exact duplicate

| Lines | Item | Action |
| --- | --- | --- |
| **L1355 = L1357** | "Materialize steps in workflow to enable replay starting at certain xprompt workflow steps?" (same highlight hash `e39a91…`) | Delete L1357 |

### 2.2 Near-duplicates inside `sase.md` (merge into one task)

| # | Lines | Why they're the same | Keep |
| --- | --- | --- | --- |
| 1 | **L282** "Always grill epics!" · **L1183** "Add a new 'Grill' option to tale/epic gate notifications!" | L282 links to `^grill`, and L1183's own sub-bullet reads "Always grill epics?!" | L1183 (fold L282 in as a sub-bullet) |
| 2 | **L244** "Migrate PIW next-word completion to co-pilot?!" · **FW L1391** "Add support for copilot… completion for the PIW!" | Same feature | L244 |
| 3 | **L918** "Remove support for hidden agents and old `.` keymap" · **FW L1372** "Get rid of 'hidden' agent support from agents tab?!" | Same removal | L918 (and see §2.3 for FW L1409) |
| 4 | **L664** "Sase needs a way to shut down all agents before a machine restart… restore with a single command" · **L1001** "Make all sase agents re-launch after a machine restart!" | Same outcome; L601's third bullet ("necessary for easy machine restarts") is related | One task, "agents survive machine restarts" |
| 5 | **L199** "Should sase run like claude code with the main agent(s) being the 'mayor(s)'… via an actual (optional) tmux session?" · **L1278** "Explore the option of using tmux instead of headless CLI agents?" | Same architecture question | L199 (it has the Gas Town bookmark) |
| 6 | **L119** #ref "Hermes Agent as a Fully Supported SASE Provider" · **L1275** "Add support for `hermes chat --oneshot` LLM provider?!" | Same provider (and see §2.5) | L119 |
| 7 | **L57** "Move agent instruction bundles from file deck to new memory deck!" · **L121** #ref "A MEMORY Deck for What an Agent Was Told and Looked Up" | Research plus implementation of the same deck; both block on `sase_pypi_releases` | Keep both, but make L57 `dependsOn` L121 |
| 8 | **L273** "Instruct agents to use 'wait for load' monitor?!" · **L825** "Add `cpu=<N>.<duration>` kwarg to `%wait`!" | L825's own sub-bullet says "Use [[sase#^wait-for-load]] instead?!" | Pick one and delete the other |
| 9 | **L740** "Configurable freshness notifications for macros, snippets, and memories!!!" · **L1035** "Add xprompt freshness labels to manage unused xprompts!" | L1035 is a subset of L740 | L740 |
| 10 | **L554** "Add new `%name` directive for ephemeral agent names!" · **L806** "Improve the way we overwrite agent names (e.g. `%n:`)!" | Same naming surface | Merge |
| 11 | **L1214** "Stabilized black feature as first use case of collaboration with SASE!" · **FW L1385** "Land black string wrapping feature using sase?!" | Same goal | L1214 |
| 12 | **L355** "The 'Statistics' tab should be powered by `sase stats` command?!" · **L46** (WIP) "Add new `sase project stats` command!" | sase master already has `a53f10f6a6 feat(stats): add sase stats project CLI` and `0f2052be6a feat(tui): migrate Statistics Projects tab to shared report`. The command shipped as `sase stats project` | Close L355 when L46 lands |
| 13 | **L98** "Add `,H` keymap for easy node collapse!" · **L450** "Make pressing `HH` collapse the last target/hint!" | Both are node-collapse keymaps | One collapse-keymap task |
| 14 | **Rename ideas ×4:** L126 (power/pow/po), L745 (bai), L1027 (sal), FW L1418 (sawi) | Four tasks for one decision. "sawi" was already canceled 2026-07-28, and "sasos" on 2026-10-04 | One "SASE rename candidates" task |

Two near-duplicates that aren't product work:

- **L27** "You have 2 resets and 62K credits for codex!" and **L59** "A full reset for Codex expires on the 22nd!" are both reminders about the same Codex account.
- **L528** "You have a claude code reset (expires 2026-10-22)" is the same kind of reminder.

Consolidate all three in one subscriptions note (§3.4).

### 2.3 Contradictions (decide, then delete the losing side)

| Topic | Conflict |
| --- | --- |
| **Hidden agents** | L918 and FW L1372 remove hidden agents. FW L1409 adds a "`%hide` agents keymap + TUI count of hidden agents". |
| **`/sase_run`** | FW L1338 "Create /sase_run xprompt skill!" (it now exists) vs. `sase_memory` "Remove `/sase_run` skill!" (high priority). |
| **chezmoi as a project** | L380 "Initialize chezmoi as sase project!" (open, high) vs. `done/sase_done` "Make `chezmoi` a sase-managed project!" (canceled 2026-10-09). chezmoi is now configured as a linked SASE repo ("home configuration"), so part of this may already be true. Its remaining sub-bullet (default to `#gh:dotfiles` instead of `#git:home`) interacts with L860 "Make `#research_swarm` work with `#git:home`! Or remove support for `#git:home` completely?!" |
| **`,X` keymap** | L1039 says `,X` kills and edits an in-flight agent. FW L1425 says `,X` re-launches failed agents. `done/sase_done` shows "Add `,X` keymap to kill/edit last launched agent!" done 2026-09-08 and "Re-launch failed sase agents!" done 2026-07-20. FW L1425 is obsolete. L1039 is mostly done; only the generalization from "last launched" to any selected in-flight agent may remain. |

### 2.4 Already done, superseded, or self-cancelled (close or delete)

Evidence-backed:

| Line | Item | Evidence |
| --- | --- | --- |
| FW L1333 | Dynamic agent families | `sase_dyn_agent_fam` ✅ in the Sub-projects line |
| FW L1335 | Use apollo to run agents on remote machines | `sase_remote` project and `%dispatch` (the `dispatch.md` memory) |
| FW L1338 | Create `/sase_run` skill | The skill exists today |
| FW L1340 | `^launch-hitl` approve agent launches | The LaunchApproval flow exists (`/sase_run` requests launches through LaunchApproval) |
| FW L1341 | Install codex and try sites | `sase_sites` ❌ canceled |
| FW L1343 | Sidecar/submodule approach for `sdd/` | Sidecar artifact repos shipped |
| FW L1347 | Migrate AGENTS.md files to single SASE.md | Superseded by decision `readable-agents-md` |
| FW L1348 | Migrate `xprompts/pylimit_split.yml` to Python | pylimit became `toobig` (done 2026-07-13) |
| FW L1352 | `^audio-artifacts` audio summaries | `sase-listen` exists |
| FW L1365 | Create `memory/pyvision.md` | `sase/memory/symvision.md` exists |
| FW L1390 | Research in subdirs with `_cld`/`_cdx` suffixes | In use (this report is `202610/…__cld.md`) |
| FW L1418 | Rename to sawi | Canceled 2026-07-28 in `done/sase_done` |
| FW L1425 | `^comma-big-x` relaunch failed agents with `,X` | Done (see §2.3) |
| Req L1430 | Read about Antigravity | `sase_anti_gravity` ✅ |
| L355 | Statistics tab powered by `sase stats` | Landed on master (§2.2 #12) |

Likely done, but verify first:

| Line | Item | Why I think it's done |
| --- | --- | --- |
| L1148 | Convert `tui_perf.md` into `tui.md` | `tui.md` exists, and "Make `tui_*.md` files referenced instead of inlined in tui.md!" was done 2026-10-06. Only the "tab/keymap expectations" part may remain |
| L1208 | Long-term `mac.md` memory with SSH instructions | The `tailnet.md` reference memory now covers mac SSH |
| L833 | Replace internal axe/lumberjack/chop references | The rename landed 2026-09-23; check for leftovers |
| FW L1342 | PR comment reading / mentors | Mentors exist (`/sase_patches`) |
| FW L1381 | "Wait" panel | L1075 talks about the wait panel as if it exists |
| L1270 | "BUG: Plans are lost when agents ask confirmation for memory changes" | Its own sub-bullet says "This wasn't actually a big deal", so cancel it |

### 2.5 Cross-note duplicates (`sase.md` ↔ child notes)

| `sase.md` | Child note | Same item |
| --- | --- | --- |
| L1105 "Migrate to `/sase_stitch` by defining a built-in `how_to_git_commit.md` memory" | `sase_memory` `^commit-to-stitch` | "Migrate `/sase_git_commit` to `/sase_stitch`!" |
| L119, L1275 (Hermes) | `sase_pre_blog` `^hermes-llm` | "Add support for hermes LLM provider!" |
| L117 (pi) | `sase_pre_blog` `^pi-llm` | "Add support for pi LLM provider!" |
| L295 "auto-link all research files that researchers read to final linked report" | `sase_art_links` | "Research lead in `#research_swarm` should be told to link to related research files!" |
| L1138 `%tag` directive + `tag_hooks` | `sase_post_blog` | "Add support for tagged artifact files!" |
| L213 annotations on artifact files / L229 `file:` decisions | `sase_post_blog` | "Artifact annotations should be auto-read when agents read the artifacts!" |
| L1066 project-local files / L1119 "store all artifacts locally" | `sase_post_blog` | "Allow projects to configure local sidecar repos again!" |
| L472 "Use new finalizer to enforce specific agent output vars" (and L289) | `sase_post_blog` `^auto-wait-for-vars` | "auto-wait for agent and validate that it sets a variable" |
| L162 bulk gate commands / L879 "beads specify the xprompt used to run them" | `sase_better_tasks` | "Each task type should be able to specify a set of prompts! (used to create sase gate launch commands)" |
| L1061 model alias pools in overrides · L945 `@xlarge[codex]` | `sase_usage` | "override model aliases until a usage window target is hit" · "auto-load-balancing model aliases" |
| L939 `/fleet` Telegram uptime | `sase_remote` | "The 'Machines' SAC tab should provide a much better version of `uptime`!" |
| L643 / L677 `max_running_agents` | `sase_remote` `^auto-dispatch` | "Should take max runner configuration on each machine into consideration!" |
| FW L1332 `^split-file` | `sase_post_blog` ref "Running toobig_split Beyond Python" · `sase_toobig_symvision` | Same toobig/split work |
| Req L1429 web page per agent | `sase_art` `^web-client` | "Add web client for browsing artifact pages!" |

Outside `sase.md` but worth fixing: `sase_pre_blog` lists **"Remove `branch_or_workspace_name` dependency!" twice** (its L18 and L25).

### 2.6 Overlapping families (not duplicates, but design each as one piece)

- **`<ctrl+k>` in the PIW is redefined three ways:**
  - L560: `K` behavior when the completion menu is visible
  - L948: first press triggers light-weight prompt-history completion
  - L1092: `#gh:sase` in the prompt uses the `project:sase` filter
- **Three config knobs for "run something on artifact files":**
  - L358 `commit_hooks.artifacts`
  - L795 `file_hooks` → `artifact_hooks` (works with `%tag`)
  - L1138 `%tag` + `tag_hooks`
- **Annotations and comments:**
  - L213 annotations on any artifact file
  - L229 decisions on every artifact type (its `file:` bullet: comments agents always see)
  - L565 comments in memory files that aren't rendered
  - L816 generalize `<foo>` into prompt annotations
  - FW L1367 annotations on screenshots
- **Agent-to-agent messaging:**
  - L1227 finalizer that checks for messages via a channel bead
  - L927 all live chats streamed to one message board
  - L112 "stream" bead as a memory stream
  - L195 a "log" available to all agents

  `sase_message_boards` was canceled ❌. Decide whether this is a revival before scattering it.
- **Failed-agent recovery:**
  - L91 Recovery/Relaunch panel
  - L405 prompt to restart when dismissing
  - L721 kill without dismissing
  - L1039 `,X` for in-flight agents
- **Waiting:**
  - L289 `%wait` on vars or artifacts
  - L426 plan-file `wait` field
  - L1179 `%clan` `wait` kwarg
  - L132 standalone procs in epic frontmatter, e.g. to wait for releases
  - FW L1416 `%wait` should see dismissed agents
- **`+` grammar:**
  - L657 `+sase@foo` rather than `+sase_foo`
  - L1235 `+` as the project-local macro separator
  - FW L1406 `+sase` shorthand
- **Skill bundles:**
  - L756 "Implement skill bundles using a memory web!"
  - L1281 "semantic memory files… for skill bundles" (its own sub-bullet: "No! Use `sase skills read`")
- **Capacity:** L643 project-local `max_running_agents` vs. L677 per-machine `max_running_agents` required by `sase init`.

---

## 3. Recommended project split

### Principles

1. **Reuse before you create.** 17 existing children are a natural home for 81 hub tasks, and several of them are nearly empty today.
2. **Create a new child only for a cohesive cluster** of about 8 or more tasks with a completion criterion that fits on one line. `_templates/new_project.md` treats the `#prj` line as a completion criterion, so each proposal below includes one.
3. **Get non-SASE items out of the SASE tree.**
4. **Keep the hub small.** It should hold the `>=1000 stars` goal, the Sub-projects roster, and a few cross-cutting tasks.

### 3.1 New children: create now (8 notes, 108 tasks)

Names follow the existing `sase_better_*` / `sase_*` convention. Where a predecessor project is closed (e.g. `sase_research` ✅, `sase_gate` ✅, `sase_better_chops` ✅), the `better_` prefix avoids reusing its name.

| New note | Proposed `#prj` completion criterion | Tasks | `sase.md` lines |
| --- | --- | ---: | --- |
| **`sase_better_tui`** | "TUI keymaps, decks, and panels are consistent, reversible, and discoverable." | 23 | 39★, 43★, 98, 157, 249, 333, 450, 515, 547, 587, 613, 618, 626, 734, 773, 918, 933, 1009, 1017, 1174, 1193, 1250, 1259 |
| **`sase_better_macros`** | "Macro syntax, directives, and built-in macros are consistent, composable, and self-documenting." | 19 | 317, 327, 439, 535, 542, 554, 570, 632, 657, 740, 806, 811, 816, 854, 951, 988, 1035, 1166, 1235 |
| **`sase_better_piw`** | "The PIW's completion, history, and editing make it the best place to write agent prompts." | 13 | 244, 498, 520, 560, 649, 839, 873, 948, 954, 960, 1050, 1092, 1144 |
| **`sase_waits_and_queues`** | "Agents can wait on agents, vars, artifacts, or load without holding a workspace, and capacity is configurable per machine and project." | 12 | 273, 289, 426, 504, 601, 643, 677, 825, 893, 957, 1075, 1179 |
| **`sase_completion`** | "Every agent turn, including plans and monitors, ends in a well-defined finalizer → stitch → patch/PR path, sidecars included." | 12 | Finalizers/messages: 129, 435, 472, 578, 713, 927, 1227 · Stitches/PRs: 178, 262, 685, 973, 1105 |
| **`sase_community`** | "An outside user can discover, install, learn, and contribute to SASE without my help." | 12 | 38★, 126, 169, 187, 491, 598, 692, 745, 845, 1027, 1198, 1214 |
| **`sase_better_research`** | "Research swarms are composable and cheap, and their outputs link and publish (refs, podcasts) automatically." | 9 | 67, 143, 218, 295, 299, 303, 482, 607, 860 |
| **`sase_agent_lifecycle`** | "Failed, killed, or interrupted agents, including after machine restarts, can be recovered in one action, and launches are fast." | 8 | 91, 405, 664, 721, 1001, 1039, 1100, 1265 |

★ = currently in Next & In Progress. You can leave those in the hub until they finish if you'd rather not move live work.

Notes on these choices:

- **`sase_better_tui`** is the biggest cluster. If it feels too large, split it later into decks and panels (39, 249, 515, 547, 587, 613, 626, 734, 773, 1009) and keymaps and navigation (the rest).
- **`sase_completion`** combines finalizers with stitches and PRs because both sit on the same accepted decision (`host-owned-completion`). It is also where the high-priority L129, "Evaluate the need for host-owned completion/commits", would revisit that decision. If you prefer two notes, split along the "·" in the table: `sase_finalizers` (7) and `sase_stitches` (5).
- **`sase_community`** directly serves the hub's star goal. I still recommend splitting it out because its tasks can be finished, while the hub goal is open-ended. The four rename tasks should become one task there.

### 3.2 Optional children: create later, or leave in the hub (4 notes, 25 tasks)

| Note | Tasks | Lines | If you don't create it |
| --- | ---: | --- | --- |
| `sase_reading` | 9 | 20, 148, 202, 254, 258, 371, 376, 494, 732 | Leave them in the hub. 7 of the 9 are high priority and fill the hub's Ready lane, which may be what you want |
| `sase_better_gates` | 7 | 162, 208, 282 (dup), 347, 751, 1161, 1183 | Move the epic/tale gate items (282, 751, 1183) to `sase_better_plans`; keep the rest in the hub |
| `sase_better_routines` | 6 | 392, 398, 508, 833, 930, 1246 | Keep in the hub (`sase_better_chops` ✅ is closed) |
| `sase_stats` | 3 | 46 (WIP), 353, 355 | Keep in the hub until the L46 epic lands, then close L355 and move or close L353 |

### 3.3 Fold into existing children (81 tasks)

| Existing note | +Tasks | `sase.md` lines | Comment |
| --- | ---: | --- | --- |
| `sase_memory` | 16 | 57, 86, 102, 112, 121, 195, 308, 420, 466, 565, 784, 852, 1022, 1148, 1208, 1240 | Design questions (112, 195) fit `sase_memory_plan`, and 784 "Do memory webs even need to exist?" fits `sase_memory_webs`. Moving L852 here turns its `dependsOn sase_memory__dynamic-agents-md` into a local link |
| `sase_art` | 15 | 80, 123, 204, 213, 229, 358, 670, 707, 795, 899, 1066, 1088, 1119, 1138, 1203 | `sase_art` would grow to about 25 tasks. Consider two grandchildren: **`sase_art_hooks`** (358, 795, 1138) and **`sase_art_sidecars`** (707, 1066, 1088, 1119, 1203) |
| `sase_better_tasks` | 9 | 322, 411, 699, 781, 879, 914, 942, 1044, 1111 | Its scope becomes "beads"; consider updating the `#prj` text |
| `sase_better_plans` | 7 | 74, 132, 224, 339, 983, 998, 1270 (cancel) | Revives a note with 1 open task |
| `sase_more_agent_clis` | 5 | 117, 119, 1031, 1275 (dup), 1285 | pi, Hermes, ACP, Muse Code |
| `sase_pypi_releases` | 5 | 40★, 44★, 152, 184, 1126 | This note has a canceled task, "Pull in tasks from [[sase]]!" (2026-10-19). This list is that pull-in, if you still want it |
| `sase_better_installs` | 4 | 137, 350, 459, 885 | Scope becomes "installs and portability": Telegram-optional machines, Docker, Windows, multi-user |
| `sase_skill_bundles` | 4 | 639, 756, 767, 1281 | Project-local skills plus bundle design |
| `sase_projects` | 3 | 380, 964, 1096 | Resolve the chezmoi contradiction (§2.3) on the way in |
| `sase_remote` | 2 | 939, 1080 | |
| `sase_usage` | 2 | 945, 1061 | L945 depends on L218 (`sase_better_research`) |
| `sase_polish_proc_lanes` | 2 | 593, 1219 | |
| `sase_better_config` | 2 | 906, 1054 | |
| `sase_better_glossary` | 2 | 921, 1299 | |
| `sase_monitor` | 1 | 582 | |
| `sase_agents_repo` | 1 | 1152 | |
| `sase_goals` | 1 | 654 | Eval framework, alongside "Use goals to drive evals" |

### 3.4 Move out of the SASE tree (8 tasks)

| Lines | Items | Suggested home |
| --- | --- | --- |
| 27, 59, 528, 488, 1292 | Codex/Claude reset reminders, Grok Heavy → X subscription, cap Muse Code at $20 | One `ai_subscriptions` (billing/usage) note under `[[dev]]`. These are high priority and time-sensitive (the resets expire 10-22) |
| 192 | Spotify playlist management with Abby | A personal-automation or home note |
| 748 | #ref Databricks NYC interview-prep pack | The job-search project (the `sase_blog` release already depends on `job_2026_apply_29`) |
| 924 | Try Opus with Blender | A personal AI-experiments note |

### 3.5 What stays in the hub (6 tasks plus the roster)

| Line | Task | Why it stays |
| --- | --- | --- |
| L23 | #ref "%auto Autonomy: Split Into Verifiable Epics" | Cross-cutting; "Athena is working on P0 safety tales". Becomes a child once the epics start |
| L53 | E2E test new agent history | Next; close soon |
| L199 | Mayor/tmux architecture question | Merge L1278 into it |
| L367 | Delete `local/continuation/checkpoints` directory | Small repo-wide cleanup |
| L1134 | Remove ALL references to "SDD" | Repo-wide; also drives the Future Work vocabulary cleanup |
| — | Sub-projects line | Regenerated by `bob projects sync` |

### 3.6 Future Work triage (79 bullets)

**Delete (18; already done, obsolete, or duplicate):** L1333, L1335, L1338, L1340, L1341, L1343, L1347, L1348, L1352, L1357, L1365, L1372, L1385, L1390, L1391, L1409, L1418, L1425 (plus Requirements L1430).

**Rewrite or drop alongside L1134 (stale vocabulary):**

- L1359 (ChangeSpec → patch)
- L1360 (`sdd/decisions/`; now the decisions memory web)
- L1363 (`sdd/tales/`)
- L1397 (web client display of `sdd` repos; rewrite as a `sase_art` web-client bullet)
- Requirements L1431 (ChangeSpec analogy) and L1432 (`sdd/events/` MVP)

**Live ideas: move each to its child's `## Future Work` section:**

| Destination | Future Work lines |
| --- | --- |
| `sase_better_tui` | 1361, 1380, 1382, 1386, 1389, 1399, 1401 |
| `sase_better_piw` | 1368, 1369, 1393, 1394 |
| `sase_better_macros` | 1355, 1376, 1383, 1404, 1406, 1414 |
| `sase_waits_and_queues` | 1381 (verify), 1416 |
| `sase_agent_lifecycle` | 1362, 1370, 1395, 1402, 1405 |
| `sase_completion` | 1342 (verify; also fix its formatting), 1353, 1373, 1396, 1421 |
| `sase_better_plans` | 1349, 1358, 1364, 1366, 1407, 1413 |
| `sase_art` | 1367, 1388, Requirements 1429 |
| `sase_toobig_symvision` | 1332, 1345, 1350 |
| `sase_memory` | 1346, 1374 |
| `sase_more_agent_clis` | 1410 |
| `sase_projects` / `sase_better_installs` | 1344, 1392, 1403, 1408, 1411 |
| `sase_remote` | 1400 |
| `sase_usage` | 1417 (`@smartest` predates the size-alias ladder) |
| `sase_better_vars` | 1377 |
| `sase_better_routines` or `sase_pypi_releases` | 1371 |
| `sase_community` | 1398, 1412 (stale outreach from July) |
| `sase_reading` | 1354 (PDL) |
| Hub | 1356 (fix `sase telemetry`) |
| Out of the SASE tree | 1384 (mac screenshot keymap) |

### 3.7 Migration mechanics and gotchas

- **Fix inbound block links when tasks move:**
  - `sase_pypi_releases`' BLOCKS line links to `[[sase#^memory-deck]]`, `^ref-agent-memory-deck-placement`, `^ref-hermes-agent-sase-provider`, and `^ref-pi-sase-provider-design`.
  - `sase_memory` links to `[[sase#^ref-agent-instructions-budgeted-router]]`.
  - Inside `sase.md`, L826 links to `[[sase#^wait-for-load]]` and L282 to `[[sase#^grill]]`.
- **Rewrite note-scoped ids.** `[id:: sase__…]` and `[dependsOn:: sase__…]` values carry the note name as a prefix, so moving a task changes it. These chains must move together or be rewritten:
  - L44 → L184 → L202: merge-queue primer → fence reassessment → Gas City comparison. L44/L184 go to `sase_pypi_releases` and L202 to reading, so this becomes a cross-note dependency.
  - L218 → L945: index swarms → `@xlarge[codex]` (`sase_better_research` → `sase_usage`).
  - L46 → L353: project stats → model attribution.
  - L371 → L732: Minions part 1 → part 2.
- **There's no move tool.** `bob task` offers `archive`, `reconcile`, and `reroll`. A `bob task move` command in bob-cli that rewrites ids, `dependsOn` values, and `[[note#^anchor]]` backlinks would make this split, and future ones, safe and mechanical. That's worth filing before moving 200+ tasks by hand.
- **Order of operations:**
  1. Run `bob task archive` so the 9 done/canceled tasks don't move.
  2. Create the new notes from `_templates/new_project.md` with `parent: "[[sase]]"`.
  3. Move the tasks.
  4. Run `bob projects sync` to regenerate the hub's Sub-projects line.
- **More Ready lanes.** `bob ready` caps each note's Ready lane; `sase` is at 3/5. Eight new children add eight lanes, so up to 40 more tasks could show as ready at once. Moving a task doesn't change its `scheduled` date, so nothing surfaces right away. If more lanes is more than you want, lower the cap on the new notes.
- **`[[sase_v19]]`.** Either create it as a view (a Tasks/Dataview query over tasks tagged for v0.19) rather than another place for tasks to live, or remove the two links.

---

## 4. Overall summary of the tasks in `sase.md`

`sase.md` is the root project note for SASE, with the completion criterion "sase has received >=1000 stars on GitHub!". In practice it collects nearly every SASE idea that isn't already in a child project. There are 228 open tasks plus 79 older Future Work bullets. Intake is speeding up: 66 tasks were created in the first 19 days of October alone.

**What the work is about** (bucket sizes from Appendix A):

| Theme | Open tasks |
| --- | ---: |
| TUI keymaps, decks, panels | 23 |
| Macro (xprompt) language and directives | 19 |
| Memory (instruction bundles, memory deck, webs, decisions) | 16 |
| Artifacts and sidecars (attachments, hooks, annotations, decisions) | 15 |
| Prompt input widget (completion, history) | 13 |
| Waits, queues, and capacity | 12 |
| Agent completion (finalizers, stitches, PRs, messaging) | 12 |
| Community and outside contributors (docs, gallery, rename, forks) | 12 |
| Beads | 9 |
| Research swarm and listen pipeline | 9 |
| Reading refs | 9 |
| Agent lifecycle and recovery | 8 |
| Plans and epics | 7 |
| Gates | 7 |
| Routines (jobs/chops) | 6 |
| Release/CI/merge queue | 5 |
| Providers (pi, Hermes, ACP, Muse) | 5 |
| Installs and portability | 4 |
| Skills | 4 |
| Stats | 3 |
| Small existing-child fold-ins (projects, remote, usage, procs, config, glossary, monitor, agents repo, goals) | 16 |
| Cross-cutting hub items | 6 |
| Not SASE work (billing reminders, Spotify, interview prep, Blender) | 8 |

**What it looks like:**

- Mostly medium-priority UX polish and feature ideas, often captured from Google Keep (21) or from reading (19 `#ref`).
- Only about 10 tasks are truly dependency-blocked. The rest are spread over the next 1–3 months by the 🎲 reroll.
- The active edge is small and concrete:
  - PyPI release reliability (E1 started on athena)
  - The merge-queue primer and reassessment
  - The `sase project stats` epic (its CLI and Statistics tab migration are already on master)
  - Deck keymap and scrollbar fixes
  - Replying to rrimps' PR #301
  - E2E testing of agent history
- A second wave is gated on `sase_pypi_releases`: the pi and Hermes providers and the memory deck.

**What's wrong with it today:** because it's a catch-all, problems pile up without being noticed:

- Duplicates (§2.1–2.2)
- Contradictions (hidden agents, `/sase_run`, chezmoi, `,X`)
- Retired vocabulary (`sdd`, ChangeSpec, xprompt, lumberjack)
- Already-finished ideas (~20, mostly in Future Work)
- High-priority personal reminders crowding a product backlog

**Recommendation:**

1. Fold 81 tasks into the 17 existing children; this revives several near-empty notes.
2. Create the 8 new children in §3.1.
3. Move the 8 personal items out.
4. Clean up Future Work against §3.6.

The hub drops from 228 open tasks to roughly 6 (or about 31 if you skip all four optional children), plus the Sub-projects roster. Every remaining SASE task then lives in a note with a completion criterion that can actually be met.

---

## Appendix A: every open task in `sase.md` with its recommended destination

Format: `L<line> [status] (priority, created) title`. Status `?` = scheduled/blocked, `*` = next, `/` = WIP, blank `[ ]` = open. NEW = create now (§3.1), OPT = optional child (§3.2), EXIST = fold into an existing child (§3.3), OUT = move out of SASE (§3.4), HUB = stays (§3.5).

### NEW · `sase_better_tui` (23)

- L39 [*] (-, 2026-10-19) Fix scrollbar and card focus for main data deck!
- L43 [*] (-, 2026-10-18) Fix `|` and `\` keymaps so they reverse their own operations!
- L98 [?] (medium, 2026-09-13) Add `,H` keymap for easy node collapse!
- L157 [?] (medium, 2026-09-12) Add support for bulk-copying with `%` keymap!
- L249 [?] (medium, 2026-10-06) Add Macros deck!
- L333 [?] (low, 2026-07-23) Hide sidecar repo commits / deltas in 1st level agent / family folds!
- L450 [?] (medium, 2026-08-23) Make pressing `HH` (on the agents tab) collapse the last target/hint!
- L515 [?] (medium, 2026-09-11) Show live sase tool output in the tools panel.
- L547 [?] (medium, 2026-08-23) Add much better folding to agent shell in agent metadata panel!
- L587 [?] (medium, 2026-08-28) Add support to sase notification tabs for custom grouping strategies!
- L613 [?] (medium, 2026-09-20) Add plan file to % panel!
- L618 [?] (medium, 2026-09-08) Make `,/` keymap search for any text in any panel on any tab in the TUI!
- L626 [?] (medium, 2026-10-02) Add support for pinning deck panels to specific agents!
- L734 [?] (medium, 2026-09-28) Rename "Main” deck to "IO"?
- L773 [?] (medium, 2026-08-18) Sort pre-xprocs above the corresponding agent shell!
- L918 [?] (medium, 2026-09-23) Remove support for hidden agents and old `.` keymap.
- L933 [?] (medium, 2026-09-09) `N` should trigger panel with options for:
- L1009 [?] (medium, 2026-08-17) Add support for a condensed version of the left pane in the Agents tab.
- L1017 [?] (medium, 2026-09-07) Add sase-mac-toasts to override TUI toasts and `bam`!
- L1174 [?] (medium, 2026-08-13) Add support for custom marks on any entry on any tab using `M` keymap that claim a key for the backtick keymap panel!
- L1193 [?] (medium, 2026-08-18) Implement a `,?` keymap that provides context-specific hints and keymaps for a selected entry in the TUI!
- L1250 [?] (medium, 2026-08-18) BUG: Expanding node with `l` keymap can re-sort node under hood agent group!
- L1259 [?] (medium, 2026-07-19) Add relative numbers to all the left panes on the main AAA tabs!

### NEW · `sase_better_macros` (19)

- L317 [?] (low, 2026-07-17) Stop using arguments with `%auto` everywhere!
- L327 [?] (low, 2026-07-28) Start linking to xprompt definitions from prompts/ files!
- L439 [?] (medium, 2026-08-08) Get rid of `skill: true` and `ref: true`!
- L535 [?] (medium, 2026-07-23) Factor out all internal markdown text using xprompts!
- L542 [?] (low, -) Add workflow best practices and adjust existing workflows accordingly!
- L554 [?] (high, 2026-10-07) Add new `%name` directive for ephemeral agent names!
- L570 [?] (medium, 2026-09-08) Xprompts should be able to subscribe to memory webs!
- L632 [?] (medium, 2026-08-28) Improve the `#coder` xprompt!
- L657 [?] (medium, 2026-09-23) Syntax for targeting patches should be `+sase@foo` NOT `+sase_foo`!
- L740 [?] (medium, 2026-10-01) Configurable freshness notifications for macros, snippets, and memories!!!
- L806 [?] (medium, 2026-07-19) Improve the way we overwrite agent names (e.g. `%n:`)!
- L811 [?] (medium, 2026-09-13) Xprompts should be able to bundle files that they reference.
- L816 [?] (medium, 2026-09-09) Generalize `<foo>` syntax into sase "annotations"!
- L854 [?] (low, 2026-07-31) Create macro query language that can be used to query for macros!
- L951 [?] (medium, 2026-09-21) Add support for multi-line alternations using `%{}` syntax!
- L988 [?] (medium, 2026-08-23) Migrate Bash/Python steps to xprocs!
- L1035 [?] (medium, 2026-07-30) Add xprompt freshness labels to manage unused xprompts!
- L1166 [?] (medium, 2026-08-08) Make it possible to invoke an xprompt by tag!
- L1235 [?] (medium, 2026-08-08) Use `+` instead of `/` as separator for project-local xprompts?!

### NEW · `sase_better_piw` (13)

- L244 [?] (medium, 2026-10-08) Migrate PIW next-word completion to co-pilot?!
- L498 [?] (medium, 2026-09-30) Add PIW diagnostic hints when snippet's contents are found but snippet was not used!
- L520 [?] (medium, 2026-09-08) Add support for `<` / `>` in PIW to trigger agent completion for `%w` / `#fork`!
- L560 [?] (medium, 2026-09-21) Add `<ctrl+k>` keymap that has `K` behavior when completion menu is visible!
- L649 [?] (medium, 2026-08-23) Fix `sase prompt search` command!
- L839 [?] (medium, 2026-09-06) Add support for sub-ordered lists (e.g. `a.`) to PIW!
- L873 [?] (low, 2026-08-09) Require definition from user when using `d` keymap to add word to dictionary from PIW!
- L948 [?] (medium, 2026-09-26) Make first `<ctrl+k>` in PIW trigger light-weight prompt history completion!
- L954 [?] (low, 2026-09-21) Add `<ctrl+t>` memory strand name / alias completion to PIW!
- L960 [?] (medium, 2026-10-02) Add sase-capture repo inspired by bob-mac-capture!
- L1050 [?] (low, 2026-07-30) Add placeholder input history!
- L1092 [?] (medium, 2026-08-15) Pressing `<ctrl+k>` in PIW containing `#gh:sase` should use `project:sase` filter!
- L1144 [?] (medium, 2026-07-28) Add plugin support for PIW completion sources!

### NEW · `sase_community` (12)

- L38 [*] (-, 2026-10-19) Reply to rrimps PR#301!
- L126 [?] (medium, 2026-10-18) SASE rename ideas: "power” (aka "pow"--like power user) or "po" (a nod to pi)
- L169 [?] (medium, 2026-08-10) Figure out a way to emulate an unprivileged user so I can fork sase and attempt to contribute externally!
- L187 [?] (medium, 2026-10-11) Sase needs a gallery?!
- L491 [?] (high, 2026-10-15) Read like all of https://diataxis.fr website!
- L598 [?] (high, 2026-10-12) Re-work documentation in sase.sh to bare-bone basics!
- L692 [?] (medium, 2026-08-10) Set up bugyi@sase.sh email!
- L745 [?] (medium, 2026-10-11) "sase” rename idea: "bai" (Better/Bugyi's AI)?
- L845 [?] (low, 2026-09-16) Add support for explicit chat shares!
- L1027 [?] (medium, 2026-09-08) Sase rename idea: "sal"
- L1198 [?] (medium, 2026-08-28) Add a Coverage Badge to the README.md file. 🔖
- L1214 [?] (medium, 2026-08-11) Stabilized black feature as first use case of collaboration with SASE!

### NEW · `sase_completion` (12)

- L129 [?] (high, 2026-10-18) Evaluate the need for host-owned completion/commits.
- L178 [?] (low, 2026-08-10) INSPIRATION: A stitch provides value over a commit in how we are able to link stitches with patches (potentially cross-repo)!
- L262 [?] (medium, 2026-08-06) Create new PR for every necessary sidecar repo when PR exists for main project!
- L435 [?] (medium, 2026-09-16) Migrate gates and monitors to finalizers.
- L472 [?] (medium, 2026-08-25) Use new finalizer to enforce specific agent output vars?!
- L578 [?] (medium, 2026-09-14) Start making agents finalize even when creating plans or launching monitors.
- L685 [?] (medium, 2026-08-08) A “stitch” might also refer to a PR description update?!
- L713 [?] (medium, 2026-07-20) Add `sase agent report` command and have agents use this at the end of every session!
- L927 [?] (medium, 2026-09-14) All live agent chats for a project should be streamed to the same message board?!
- L973 [?] (medium, 2026-08-10) Stitch Ideas!
- L1105 [?] (medium, 2026-08-11) Migrate to `/sase_stitch` by defining a built-in `how_to_git_commit.md` memory!
- L1227 [?] (medium, 2026-08-27) Add a new built-in finalizer that checks for agent messages which could be sent from humans or agents!

### NEW · `sase_waits_and_queues` (12)

- L273 [?] (medium, 2026-09-09) Instruct agents to use "wait for load" monitor?!
- L289 [?] (high, 2026-10-01) Add support to `%wait` for waiting for certain global vars and/or artifact files to exist!
- L426 [?] (low, 2026-08-19) Add support for optional `wait` field for plan files!
- L504 [?] (high, 2026-10-11) E2E test new `%hold` directive!
- L601 [?] (high, 2026-10-11) Stop allocating workspaces for all waiting/queued agents!
- L643 [?] (low, 2026-08-06) Add support for project-local `max_running_agents` sase config field!
- L677 [?] (medium, 2026-09-03) Start requiring (via `sase init`) `max_running_agents` be provided per-machine!
- L825 [?] (medium, 2026-09-08) Add `cpu=<N>.<duration>` kwarg to `%wait`!
- L893 [?] (medium, 2026-09-17) Add support for `%q:0` and show `c<inf_symbol>` in node!
- L957 [?] (medium, 2026-09-10) Show new `Queue:` field in metadata panel instead of using `Wait:` for this!
- L1075 [?] (medium, 2026-07-23) Move runner's override to wait panel!
- L1179 [?] (low, 2026-07-23) Add a `wait` kwarg to `%clan` that allows clans to wait for clans/agents/families!

### NEW · `sase_better_research` (9)

- L67 [?] (medium, 2026-10-11) Add support for "sase links” in research files that `bob ref create` renders into great links!
- L143 [?] (medium, 2026-10-08) Publish sase--research, bob-cli--research, articles, and papers to different AntennaPod feeds!
- L218 [?] (medium, 2026-10-04) Allow agent swarms to be indexed into via `#research_swarm[linker]` syntax!
- L295 [?] (medium, 2026-10-08) Figure out how to auto-link all research files that researchers read to final linked report!
- L299 [?] (low, 2026-10-03) Rename sase-listen to sase-talk!
- L303 [?] (medium, 2026-08-26) Fix `#review_research` xprompt!
- L482 [?] (high, 2026-10-14) Start using Muse Wonder for research.
- L607 [?] (medium, 2026-09-30) Get rid of `*_model` research swarm inputs.
- L860 [?] (medium, 2026-08-13) Make `#research_swarm` work with `#git:home`!

### NEW · `sase_agent_lifecycle` (8)

- L91 [?] (medium, 2026-09-10) Add "Recovery”/"Relaunch” panel that can be used to recover lots of failures!
- L405 [?] (medium, 2026-09-20) Always prompt to restart failed agents when dismissing!
- L664 [?] (medium, 2026-09-12) Sase needs a way to shut down all agents before a machine restart, for example!
- L721 [?] (low, 2026-08-23) Better failed agents!
- L1001 [?] (medium, 2026-08-23) Make all sase agents re-launch after a machine restart!
- L1039 [?] (medium, 2026-08-07) Add new `,X` keymap to kill and edit an “in-flight” sase agent!
- L1100 [?] (medium, 2026-07-31) All background tasks should be “detached”!
- L1265 [?] (medium, 2026-08-13) Speed up agent launches!

### OPT · `sase_reading` (9)

- L20 [ ] (high, 2026-10-10) #ref The best recent reading on agentic software engineering
- L148 [?] (high, 2026-10-07) #ref Introducing Omnigent: A Meta-Harness to Combine, Control and Share Your Agents
- L202 [?] (-, 2026-10-17) #ref Gas City vs. SASE: where Gas City is ahead, and what SASE should borrow
- L254 [?] (high, 2026-10-10) #ref Reality Is the Final Verifier: On Two Key Gaps in Agentic Software Engineering
- L258 [?] (high, 2026-10-11) #ref Astra for Coding: Why Are We Doing This Again?
- L371 [?] (high, 2026-10-11) #ref Minions: Stripe’s one-shot, end-to-end coding agents
- L376 [?] (high, 2026-10-10) #ref My AI Adoption Journey
- L494 [?] (high, 2026-10-07) #ref Understanding is the new bottleneck
- L732 [?] (-, 2026-10-11) #ref Minions: Stripe’s one-shot, end-to-end coding agents—Part 2

### OPT · `sase_better_gates` (7)

- L162 [?] (medium, 2026-08-18) Support registering bulk commands for gates!
- L208 [?] (medium, 2026-10-08) Enhance gates, which are "generative just-in-time interfaces"!
- L282 [?] (medium, 2026-09-05) Always [[sase#^grill]] epics!
- L347 [?] (high, 2026-10-17) Change status to `SUDOING` after approving sudo command?!
- L751 [?] (medium, 2026-09-12) Show an option just to commit for epic gates too!
- L1161 [?] (medium, 2026-08-07) Figure out how to invoke sase gate commands directly!
- L1183 [?] (medium, 2026-08-07) Add a new “Grill” option to tale/epic gate notifications!

### OPT · `sase_better_routines` (6)

- L392 [?] (medium, 2026-09-24) Run an agent periodically (with a sase routine) to triage beads!
- L398 [?] (medium, 2026-09-08) Add support for project-local routines and/or jobs!
- L508 [?] (medium, 2026-09-10) Chops should be able to define a set of xprompts!
- L833 [?] (medium, 2026-09-16) Replace internal axe/lumberjack/chop references!
- L930 [?] (medium, 2026-09-15) Give each "job” its own due time to fix issues in [[lumberjack_chop_scheduling_tradeoffs]]?!
- L1246 [?] (medium, 2026-07-31) Add a way to snooze chops!

### OPT · `sase_stats` (3)

- L46 [/] (-, 2026-10-16) Add new `sase project stats` command!
- L353 [?] (-, 2026-10-16) Add details about which models were used to create plans/commits!
- L355 [?] (high, 2026-10-16) The "Statistics” tab should be powered by `sase stats` command?!

### EXIST · `sase_memory` (16)

- L57 [?] (-, 2026-10-18) Move agent instruction bundles from file deck to new memory deck!
- L86 [?] (medium, 2026-09-20) Add create dates to decisions memory web roster in AGENTS.md!
- L102 [?] (medium, 2026-08-24) Memory should be artifacts!
- L112 [?] (low, 2026-08-03) Add new “stream” bead type that acts as memory stream for certain agents!
- L121 [?] (-, 2026-10-19) #ref A MEMORY Deck for What an Agent Was Told and Looked Up
- L195 [?] (high, 2026-10-17) Start making a "log" agailable to all sase agents?!
- L308 [?] (medium, 2026-08-19) Add `sase memory add / delete` commands!
- L420 [?] (medium, 2026-10-02) Migrate memory to sase--memory sidecar repo?!
- L466 [?] (low, 2026-07-30) Support “owned” memories that can be modified by specific agents hoods!
- L565 [?] (medium, 2026-10-06) Allow memory files to contain comments (which contain reasoning and/or links to conversations) that don't get rendered in the instructions?!
- L784 [?] (medium, 2026-08-25) Do memory webs even need to exist?
- L852 [?] (-, 2026-10-09) #ref Shrinking SASE's Agent Instruction Files to ≤100 Lines: A Budgeted Router, Not a Trim
- L1022 [?] (medium, 2026-07-10) Add support for searching community memories and importing into projects?!
- L1148 [?] (medium, 2026-08-01) Convert tui_perf.md into tui.md and add tab/keymap expectations!
- L1208 [?] (medium, 2026-08-18) Add long-term ~/sase/memory/mac.md file with SSH instructions!
- L1240 [?] (medium, 2026-08-10) Migrate `parent` in memory files to `ancestors` list!

### EXIST · `sase_art` (15)

- L80 [?] (medium, 2026-10-10) Rename "Files” sub-tab to "Attatchments”!
- L123 [?] (high, 2026-10-19) Start requiring a reason when artifacts are created with `sase artifact create`!
- L204 [?] (high, 2026-10-14) #ref What are the entries on the Artifacts → Files sub-tab?
- L213 [?] (medium, 2026-10-08) Agents and humans should both be able to leave annotations on any artifact file!
- L229 [?] (high, 2026-10-11) ALL artifact types should support "decisions”!
- L358 [?] (high, 2026-09-06) Add `commit_hooks.artifacts` to allow users to configure which files have `sase artifact create` run on them!
- L670 [?] (medium, 2026-09-07) Make it impossible for agents to directly read artifact/memory files!
- L707 [?] (medium, 2026-09-02) Should `sase--ux` be used as a new artifact repo?
- L795 [?] (medium, 2026-08-19) Change `file_hooks` config field to `artifact_hooks`!
- L899 [?] (medium, 2026-08-28) Migrate to using a single `sase read/show` command!
- L1066 [?] (medium, 2026-07-18) Add support for setting project-local files (remembered even if primary clone is deleted)?!
- L1088 [?] (medium, 2026-08-12) Stop auto cloning `beads` sidecar repo!
- L1119 [?] (medium, 2026-08-18) Support multiple pluggable “artifact / sidecar modes” for different orgs and use-cases!
- L1138 [?] (medium, 2026-08-18) Add support for `%tag` directive that works with new `tag_hooks` config field!
- L1203 [?] (medium, 2026-08-13) Re-create Google’s snipit and use to create new `snips` sidecar repo!

### EXIST · `sase_better_tasks` (9)

- L322 [?] (low, 2026-08-25) Stop showing "Repo” row in "Commits" table on bead pages!
- L411 [?] (medium, 2026-09-06) Add `sase bead diff [commit]` command!
- L699 [?] (medium, 2026-07-31) Link to all beads created by an agent from that agent’s page!
- L781 [?] (medium, 2026-10-10) Adding a note on a bead that belongs to a repository you don't have permissions to should result in an external bug being created and linked to that b
- L879 [?] (low, 2026-08-01) Add support to beads for specifying the xprompt that is used to run them!
- L914 [?] (medium, 2026-09-20) Add new "group” bead that can be used to link several beads together!
- L942 [?] (medium, 2026-09-14) Task beads should have a confidence level associated with them, which is determined by what level of model signed off on the bead.
- L1044 [?] (medium, 2026-08-18) Does snoozing beads actually work?!
- L1111 [?] (medium, 2026-08-11) Start grouping tasks and working them in groups of 20 with an xprompt swarm!

### EXIST · `sase_better_plans` (7)

- L74 [?] (medium, 2026-09-14) Allow an epic plan file to contain explicit epics!
- L132 [?] (medium, 2026-10-08) Add support to epic frontmatter for standalone procs (to wait for releases, for example)!
- L224 [?] (medium, 2026-09-18) Start launching epic lander agent in same family as agent that created epic!
- L339 [?] (low, 2026-08-17) Add support for configuring phases with `bead` (for task bead epics)!
- L983 [?] (medium, 2026-07-30) Add `sase plan work` command to support tales (should wrap `sase bead work` for epics)!
- L998 [?] (low, 2026-08-05) Unify all epic summary page content providers!
- L1270 [?] (medium, 2026-09-03) BUG: Plans are lost when agents ask confirmation for memory changes!

### EXIST · `sase_pypi_releases` (5)

- L40 [/] (-, 2026-10-18) #ref PyPI release reliability: the converged design and how to split the work
- L44 [*] (-, 2026-10-17) #ref How GitHub's native merge queue works
- L152 [?] (medium, 2026-09-09) Fix sase-core clippy issues with sase post-commit hook!
- L184 [?] (-, 2026-10-17) #ref Reassessing the merge-queue-fenced master plan: revised requirements and a four-epic delivery
- L1126 [?] (medium, 2026-08-21) Start making `just check-full` always run test suite!

### EXIST · `sase_more_agent_clis` (5)

- L117 [?] (-, 2026-10-19) #ref Adding pi as a fully supported SASE provider
- L119 [?] (-, 2026-10-19) #ref Hermes Agent as a Fully Supported SASE Provider
- L1031 [?] (medium, 2026-09-21) Add ACP support? See [[ref/chat/acp_provider_design]]!
- L1275 [?] (low, 2026-09-23) Add support for `hermes chat --oneshot` LLM provider?!
- L1285 [?] (low, 2026-08-07) Read Muse Code docs / skills for inspiration!

### EXIST · `sase_better_installs` (4)

- L137 [?] (high, 2026-10-10) I shouldn’t need to have Telegram installed on every machine!
- L350 [?] (high, 2026-10-16) Look into adding Docker support!
- L459 [?] (low, 2026-06-26) Give sase Windows support!
- L885 [?] (medium, 2026-09-02) Sase needs to support multiple different users on the same machine!

### EXIST · `sase_skill_bundles` (4)

- L639 [?] (high, 2026-09-22) Add support for `//skill` syntax for `/<project>_skill` skills specific to `<project>`!
- L756 [?] (medium, 2026-08-24) Implement skill bundles using a memory web!
- L767 [?] (low, 2026-08-09) Add support for project-local xprompt skills!
- L1281 [?] (low, 2026-07-30) Use new “semantic” memory files with `sase memory read` (and new `search` subcmd) for skill bundles!

### EXIST · `sase_projects` (3)

- L380 [?] (high, 2026-09-07) Initialize chezmoi as sase project!
- L964 [?] (medium, 2026-08-02) Make sure `sase init -a` handles sidecar repos properly!
- L1096 [?] (medium, 2026-07-31) Make any attempt to open linked repo as external fail with an error!

### EXIST · `sase_polish_proc_lanes` (2)

- L593 [?] (medium, 2026-09-09) BUG: Standalone procs can wait for agents to complete but don't show on the Agents tab.
- L1219 [?] (medium, 2026-08-18) Proc shells should have first-class support as sase artifacts!

### EXIST · `sase_better_config` (2)

- L906 [?] (low, 2026-08-10) Factor out the `build_and_run.md` file to a sase config field (like you did with the `glossary.md` file)!
- L1054 [?] (medium, 2026-08-10) Show all snippets on the Xprompt SASE admin center panel tab!

### EXIST · `sase_better_glossary` (2)

- L921 [?] (medium, 2026-09-23) Add "TUI header rows" to glossary!
- L1299 [?] (low, 2026-08-19) Migrate glossary to tier 3 memory!

### EXIST · `sase_remote` (2)

- L939 [?] (low, 2026-09-09) Add /fleet Telegram command that shows uptime of fleet!
- L1080 [?] (medium, 2026-08-08) The assignee of a bead should always be the machine hood!

### EXIST · `sase_usage` (2)

- L945 [?] (-, 2026-09-26) Make it possible to target provider contained in model alias using `@xlarge/codex` syntax!
- L1061 [?] (medium, 2026-08-19) Add support for model alias pools to overrides!

### EXIST · `sase_monitor` (1)

- L582 [?] (medium, 2026-08-13) Allow agents to escalate to smarter agents using the `sase monitor` command?!

### EXIST · `sase_goals` (1)

- L654 [?] (high, 2026-10-12) Create eval framework mentioned by [[ref/chat/agent_platform_and_devtools_job_openings]]!

### EXIST · `sase_agents_repo` (1)

- L1152 [?] (medium, 2026-08-03) Start publishing to agents sidecar repo when plans are approved.

### OUT (not sase product work) (8)

- L27 [ ] (high, 2026-09-30) You have 2 resets and 62K "credits” for codex!
- L59 [?] (high, 2026-09-06) A full reset for Codex expires on the 22nd!
- L192 [?] (high, 2026-10-17) Give agents access to my Spotify and have them manage my playlist with Abby.
- L488 [?] (high, 2026-10-16) Switch from Grok Heavy to $200 “X Subscription"?!
- L528 [?] (high, 2026-09-22) You have a claude code reset (expires: 2026-10-22)!
- L748 [?] (medium, 2026-10-10) #ref Interview-prep pack: Databricks NYC (Agent Quality and AI Platform)
- L924 [?] (low, 2026-09-23) Try Opus with Blender.
- L1292 [?] (low, 2026-08-07) Cap Muse Code at $20!

### HUB (stay in sase.md) (6)

- L23 [ ] (-, 2026-10-08) #ref %auto Autonomy: Split Into Verifiable Epics
- L53 [*] (-, 2026-10-13) E2E test new agent history!
- L199 [?] (medium, 2026-10-16) Should sase run like claude code with the main agent(s) being the “mayor(s)” that you have access to via an actual (optional) tmux session/window?! 🔖
- L367 [?] (high, 2026-10-12) Delete local/continuation/checkpoints directory in sase repo?!
- L1134 [?] (low, 2026-07-27) Remove ALL references to “SDD”!
- L1278 [?] (lowest, 2026-06-15) Explore the option of using tmux instead of headless CLI agents?
