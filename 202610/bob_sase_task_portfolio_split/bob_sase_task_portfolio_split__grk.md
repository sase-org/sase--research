# Splitting child project notes out of `~/bob/sase.md`

- Researcher: `grk`
- Source note: `/home/bryan/bob/sase.md` (vault root, `parent: [[dev]]`, `type: [[project]]`, `status: wip`)
- Snapshot date: 2026-10-19
- Method: parsed every `#task` checkbox in `sase.md`; listed `## Future Work` / `## Requirements` bullets; inspected every `sase_*.md` project note in the vault root via `bob query` plus direct frontmatter reads; compared titles and keywords across parent and children. Peer swarm reports were not consulted.

## Executive recommendation

`sase.md` is still the catch-all inbox for SASE. It already *lists* 22 open child projects, but almost none of the 229 live tasks in the parent have been moved into those notes. The split that helps is:

1. **Deduplicate** a handful of true copies (inside the parent, against children, and in `## Future Work`).
2. **Route ~130 live tasks into existing open children** (`sase_art`, `sase_memory`, `sase_pypi_releases`, `sase_projects`, `sase_more_agent_clis`, `sase_pre_blog`, `sase_remote`, `sase_usage`, `sase_monitor`, `sase_polish_proc_lanes`, `sase_better_plans`, `sase_better_tasks`, `sase_better_vars`, `sase_better_config`, `sase_blog` / `sase_post_blog`, `sase_skill_bundles`, `sase_goals`).
3. **Create six new child notes** for clusters that no longer have a living home: `sase_tui`, `sase_macros`, `sase_listen`, `sase_rename`, `sase_finalizers`, `sase_recovery`.
4. **Eject ~8 personal/ops reminders** off the product note (quota resets, Spotify, Databricks CV, Blender).
5. **Leave ~20 items on `sase.md`**: the `#prj` umbrella, in-flight one-offs, and product-wide `#ref` reading.

Do not mint a new child for every theme. Several existing children are already the right home and are starved of the backlog that still sits on the parent. `sase_pypi_releases` even has a cancelled task *Pull in tasks from [[sase]]!* — the pull was attempted and abandoned; this pass should finish that job for real.

Target shape after the split: parent live-task count from **229 → ~25**, with children owning the rest.

---

## 1. File anatomy

Frontmatter:

| Field | Value |
| --- | --- |
| `parent` | `[[dev]]` |
| `type` | `[[project]]` |
| `template` | `[[new_project]]` |
| `status` | `wip` |
| `created` | 2026-06-01 |
| `done_tasks` | `[[done/sase_done]]` |
| `task_count` | 237 |
| `open_task_count` | 10 |

Parsed `#task` checkboxes: **238** (the extra one is the hidden `#prj` umbrella on line 12, which `task_count` excludes).

| Section | Checkbox | Count | Meaning |
| --- | --- | --- | --- |
| `#prj` umbrella (preamble) | `[ ]` | 1 | 1000 GitHub stars; lists every child |
| `## Tasks` (inbox) | `[ ]` | 3 | unscheduled / freshly kept |
| `### Next & In Progress` | `[*]` 5, `[/]` 2 | 7 | starred next + active |
| `### Blocked` | `[?]` | 218 | scheduled / waiting |
| `### Done & Canceled` | `[x]` | 9 | completed 2026-10-19 |
| **Total `#task`** | | **238** | |
| `## Future Work` | plain `-` bullets | 79 | **not** in `task_count` |
| `## Requirements` | plain `-` bullets | 4 | **not** in `task_count` |

`open_task_count: 10` matches the plugin convention of counting `[ ]` + `[*]` + `[/]` and excluding the hidden `#prj` (3 + 5 + 2 = 10). Blocked `[?]` tasks are live work that the frontmatter does not treat as "open."

Priority on all 238 `#task` rows: medium 145, high 33, low 32, unset 27, lowest 1.

Creation months (among dated tasks): 2026-10 (73), 2026-08 (73), 2026-09 (66), 2026-07 (22), 2026-06 (2). This is a four-month accumulation, not a weekend dump.

76 tasks have `^block-id`s. 24 are `#ref` reading tasks. 11 declare `[id:: ...]`. 11 declare `[dependsOn:: ...]`.

The `#prj` body already enumerates **60** child wikilinks:

- **22 open:** `sase_agents_repo`, `sase_art`, `sase_better_config`, `sase_better_glossary`, `sase_better_installs`, `sase_better_plans`, `sase_better_tasks`, `sase_better_vars`, `sase_blog`, `sase_goals`, `sase_memory`, `sase_monitor`, `sase_more_agent_clis`, `sase_pager`, `sase_polish_proc_lanes`, `sase_post_blog`, `sase_projects`, `sase_pypi_releases`, `sase_remote`, `sase_skill_bundles`, `sase_toobig_symvision`, `sase_usage`
- **32 done:** `sase_actstat`, `sase_agent_history`, `sase_anti_gravity`, `sase_better_chops`, `sase_better_llm_disable`, `sase_clans_and_tribes`, `sase_clean`, `sase_cleanup`, `sase_config`, `sase_decks`, `sase_dir_xprompts`, `sase_doctor`, `sase_dyn_agent_fam`, `sase_final_polish`, `sase_gate`, `sase_gate_shells`, `sase_grok_cli`, `sase_hoods`, `sase_if_and_proc`, `sase_install`, `sase_linked_repo_delta`, `sase_model`, `sase_model_panel`, `sase_onboard`, `sase_parallel_fams`, `sase_piw_multi_prompt`, `sase_plugin`, `sase_prompt_stash`, `sase_research`, `sase_sdd_repo`, `sase_size_models`, `sase_update`
- **6 canceled:** `sase_back_policy`, `sase_blog_blockers`, `sase_bug_bash`, `sase_message_boards`, `sase_setup`, `sase_sites`

Grandchildren also exist under `sase_art`, `sase_memory`, `sase_blog`, `sase_monitor`, `sase_prompt_stash`, `sase_dir_xprompts`, `sase_dyn_agent_fam`, `sase_clean`.

---

## 2. Existing child landscape (what is already split)

Every listed child note exists on disk as `~/bob/<name>.md` with `parent: [[sase]]` and `template: [[new_project]]`. Extra project notes not on the `#prj` roster: `sase_art_file`, `sase_art_links`, `sase_memory_plan`, `sase_memory_webs`, `sase_pre_blog`, `sase_monitor_gate` (done), and a few canceled art/memory grandchildren.

**Open children still carrying live work** (status `wip`, plus blocked `[?]` rows). `open_task_count` on these notes is often 0 because the plugin ignores `[?]`:

| Child | Frontmatter open | Live tasks (incl. `#prj` + blocked) | Ready to absorb from `sase.md`? |
| --- | --- | --- | --- |
| `sase_art` (+ `sase_art_file`, `sase_art_links`) | 0 / 0 / 0 | 11 + 2 + 5 | Yes — largest existing artifact backlog |
| `sase_memory` (+ plan/webs) | 2 | 11 + 4 + 3 | Yes |
| `sase_blog` / `sase_pre_blog` / `sase_post_blog` | 3 / 0 / 0 | 11 / 6 / 12 | Yes, with care (pre-blog already owns pi/hermes) |
| `sase_goals` | 4 | 5 | Yes for evals |
| `sase_pypi_releases` | 2 | 4 | Yes for merge-queue + remaining release work |
| `sase_remote` | 1 | 8 | Yes |
| `sase_monitor` | 0 | 5 | Yes |
| `sase_projects` | 0 | 2 | Yes (`sase project stats` is in progress on the parent) |
| `sase_more_agent_clis` | 0 | 2 | Yes — currently only GLM 5.3 |
| `sase_pager` | 0 | 3 | Small leftover |
| `sase_polish_proc_lanes` | 0 | 4 | Yes |
| `sase_better_{config,glossary,installs,plans,tasks,vars}` | 0 | 2–5 each | Yes, each is a thin leftover plus a matching parent cluster |
| `sase_agents_repo`, `sase_skill_bundles`, `sase_toobig_symvision`, `sase_usage` | 0 | 2–5 | Yes |

**Closed children that still have leftovers sitting on the parent.** Do not reopen these notes; send the leftovers to a *new* child or an open sibling:

| Closed child | Leftover still on `sase.md` | Send instead to |
| --- | --- | --- |
| `sase_decks` (AMP→decks, done 2026-10-04) | scrollbar, `\|`/`\` reverse, Macros deck, pin deck, rename Main→IO | **new `sase_tui`** |
| `sase_dir_xprompts` | ~20 xprompt/macro/`%` directive tasks | **new `sase_macros`** |
| `sase_research` (done 2026-10-06) | AntennaPod feeds, research auto-link, Muse Wonder, swarm `*_model` inputs | **new `sase_listen`** + `sase_art_links` / `sase_post_blog` |
| `sase_final_polish` | host-owned completion, migrate gates/monitors to finalizers, `%final` | **new `sase_finalizers`** |
| `sase_gate` / `sase_gate_shells` | bulk gate commands, generative JIT gates, invoke gates directly | `sase_finalizers` or a thin addendum on a new `sase_gates` — prefer **folding into `sase_finalizers`** |
| `sase_agent_history` (done 2026-10-18; its own E2E was cancelled) | `E2E test new agent history` still `[*]` on parent | Finish on parent, then drop |
| `sase_dyn_agent_fam` | Future Work still says "Add support for dynamic agent families" | Delete the Future Work bullet |
| `sase_message_boards` (canceled) | "stream live chats to the same message board" | Do not reopen; park on `sase_tui` or cancel |
| `sase_sites` (canceled) | gallery / web-client ideas | `sase_art` already has "Add web client for browsing artifact pages" |

---

## 3. Duplicates

No two `#task` titles in `sase.md` are exact string matches. Duplicates here are **semantic copies**, **cross-note copies**, and **Future Work copies of work that already shipped**.

### 3.1 Exact copies

| Duplicate | Where | Action |
| --- | --- | --- |
| "Materialize steps in workflow to enable replay starting at certain xprompt workflow steps?" | `sase.md` Future Work **L1355 and L1357**, identical wikilink + hash | Delete one |
| "Remove `branch_or_workspace_name` dependency!" | `sase_pre_blog.md` **L18 and L25**, identical body and schedule log | Delete one (child-note hygiene, not parent) |

### 3.2 Same work tracked twice (parent ↔ child)

| Parent (`sase.md`) | Child copy | Verdict |
| --- | --- | --- |
| L1105 Migrate to `/sase_stitch` via `how_to_git_commit.md` | `sase_memory.md` L62 Migrate `/sase_git_commit` to `/sase_stitch` | **Keep the child.** Drop the parent row (or turn it into a `dependsOn` pointer). |
| L117 `#ref` pi provider design; L119 `#ref` hermes provider | `sase_pre_blog.md` L33/L35 "Add support for pi/hermes LLM provider" (points at the same research notes) | **Keep implementation on `sase_pre_blog` (blog gate) and/or `sase_more_agent_clis`.** Move the `#ref` rows with them. Drop from parent. |
| L1275 `hermes chat --oneshot` | same hermes cluster | Fold into the hermes child task as a sub-bullet |
| L123 require a reason on `sase artifact create`; L358 `commit_hooks.artifacts` | `sase_art_links.md` L23 "Improve `sase artifact create`" | **Keep `sase_art_links` as the home.** Merge the two parent rows in as requirements. |
| L80 Rename Files sub-tab to "Attatchments"; L204 `#ref` artifacts files sub-tab | `sase_art.md` L70 files sub-tab sort/tree | Same feature surface. Move all three onto `sase_art`. |
| L57 memory deck + L121 `#ref` agent_memory_deck_placement | both `dependsOn` `sase_pypi_releases#^prj`; child `sase_memory` already owns "Generate AGENTS.md dynamically" | **One memory-deck task on `sase_memory`.** Parent L57 and L121 are the same idea. |
| L46 `sase project stats` (in progress) + L353 model-stats (blocked on it) + L355 Statistics tab ← `sase stats` | `sase_projects.md` only has "add projects from Projects tab" | Not a title duplicate; **move the stats trio onto `sase_projects`.** |
| L1126 `just check-full` always run tests | `sase_monitor.md` L19 "Give `just check-full` good output again" | Related, not identical. Keep both, both on `sase_monitor` / `sase_pypi_releases`. |
| L282 Always `sase#^grill` epics + L1183 Grill option on tale/epic gates | `sase_blog_blockers.md` cancelled grill task | Parent pair is one feature. Merge into a single `sase_better_plans` task. Do not revive the canceled blocker note. |
| L927 stream chats to a message board | `sase_message_boards` canceled `#prj` | Revival of a canceled project. Decide once; do not keep both a canceled child and a live parent task. |
| L654 eval framework | `sase_goals.md` evals FAQ `#ref` + `sase_post_blog.md` evals-through-goals `#ref` | Three evals threads. **Home: `sase_goals`.** |
| `sase_post_blog.md` "Fix remote machines" | `sase_remote.md` already owns fleet/remote work | Move the post-blog bullet onto `sase_remote` (or make it a dependency), do not grow a second remote project. |

### 3.3 Same idea, multiple parent rows

| Cluster | Rows | Action |
| --- | --- | --- |
| Product rename | L126 power/po, L745 bai, L1027 sal, Future Work L1418 sawi | **One `sase_rename` note**, four candidate names as bullets, not four tasks |
| Codex / Claude / Muse / Grok quota nag | L27 62K credits + 2 resets; L59 Codex reset expires the 22nd; L528 Claude Code reset expires 2026-10-22; L488 Grok Heavy → $200 X sub; L1292 Cap Muse $20 | These are calendar reminders, not product work. **Eject** to a personal ops note or Keep. `sase_usage` already covers the *product* usage-window work. |
| Collapse / kill keymaps | L98 `,H` node collapse; L450 `HH` collapse last hint; L1039 `,X` kill+edit in-flight; Future Work L1425 `,X` relaunch | `,H`/`HH` are one TUI cluster. `,X` on the parent and in Future Work is an **exact-idea duplicate** — keep the `#task`, delete the Future Work line. |
| Hidden agents | L918 remove hidden agents + `.` keymap; Future Work L1372 get rid of hidden agents; Future Work L1409 `%hide` agents | One decision on `sase_tui`. L918 and L1409 **conflict** (remove vs add). |
| tmux "mayor" vs tmux instead of headless | L199 vs L1278 | Related product-shape questions. One task on a recovery/UX note, or keep a single `#ref` on the parent. |
| Memory-as-artifact vs memory sidecar vs semantic memory vs community memories | L102, L420, L1281, L1022 | Related strategy questions for `sase_memory`. Do not split them across four children. |
| `%wait` family | L289 wait for vars/artifacts; L825 `cpu=` kwarg; L426 plan `wait` field; L1179 `%clan` wait kwarg; Future Work L1416 `%wait` sees dismissed agents | One `sase_monitor` / `sase_macros` design, several bullets. |
| PIW completion | L244 migrate next-word to copilot; L948 first `<ctrl+k>` light history; L560 `<ctrl+k>` has `K` behavior; Future Work L1391 copilot for PIW | One `sase_tui` task with sub-bullets. |
| Minions/Stripes parts 1 and 2 | L371, L732 | Sequence, not a duplicate. Keep both as `#ref` on `sase_more_agent_clis` or a reading child. |
| PyPI track 0 (done L1313) vs PyPI reliability design (in progress L40) | sequence | Keep L40, leave L1313 in Done. |

### 3.4 Future Work that has already shipped in a child

These bullets should be deleted or struck, not promoted to new `#task`s:

| Future Work | Already done in |
| --- | --- |
| L1333 Add support for dynamic agent families | `sase_dyn_agent_fam` (status done) |
| L1335 Use apollo to run agents on remote machines | `sase_remote` (open, but the capability exists) |
| L1338 Create `/sase_run` xprompt skill | skill exists; `sase_memory` now wants to *remove* it |
| L1340 Approve sase agent launches | `sase_gate` (done) |
| L1341 Install Codex and try sites | `sase_sites` canceled; Codex is in daily use |
| L1430 Read about Antigravity | `sase_anti_gravity` done |

### 3.5 Off-project items currently living as SASE tasks

These are not SASE product work:

- L192 Spotify + Abby playlist (Keep-linked, priority high)
- L748 Databricks NYC CV / interview prep `#ref`
- L924 Try Opus with Blender
- Future Work L1412 EMAIL woman about GitHub stars (the `#prj` already tracks 1000 stars)

Move them to a personal inbox (`gkeep_inbox`, `work_ideas`, or a `life.md` task note). Leaving them on `sase.md` distorts `open_task_count` and any child split.

---

## 4. Thematic inventory of what lives on `sase.md`

Live `#task` rows only (229). Counts are approximate because some tasks sit on a boundary.

| Theme | ~N | Examples | Natural home |
| --- | --- | --- | --- |
| TUI / PIW / keymaps / decks | 30 | scrollbar, reverse `\|` `\`, `,H`/`HH`/` ,X`/` ,?`, PIW completion, toasts, AAA relative numbers | **new `sase_tui`** |
| Macros / xprompts / `%` directives | 20 | Macros deck, `%auto`, `%tag`, `%q:0`, `%{}`, snippet freshness, xprompt-by-tag | **new `sase_macros`** |
| Memory / glossary / instruction files | 20 | memory deck, memory=artifacts, `sase memory add/delete`, webs, stitch skill, budgeted router | `sase_memory` |
| Artifacts / attachments / decisions | 12 | Files→Attachments, artifact create reason, annotations, artifact decisions, `sase--ux` | `sase_art` / `sase_art_links` |
| Beads / tasks / snooze | 12 | bead diff, group bead, stream bead, confidence, assignee=hood | `sase_better_tasks` |
| Plans / epics / grill / tales | 11 | explicit epics in a plan file, lander-in-family, `sase plan work` | `sase_better_plans` |
| PyPI / merge-queue / green master | 8 | reliability design (in progress), GitHub merge-queue primer, fence reassessment, clippy hook | `sase_pypi_releases` |
| Providers / CLIs / Muse / ACP | 9 | pi, hermes, ACP, Omnigent, Minions, Muse Wonder | `sase_more_agent_clis` (+ `sase_pre_blog` as the launch gate) |
| Monitors / waits / sudo / finalize-now | 10 | `%hold` E2E, wait-for-load, SUDOING, escalate via monitor | `sase_monitor` |
| Docs / blog / gallery / diataxis | 9 | sase.sh rewrite, coverage badge, gallery | `sase_blog` / `sase_post_blog` |
| Personal / quota nags | 8 | Codex/Claude resets, Spotify, Databricks CV, Blender | **eject** |
| Chops / jobs / xprocs | 6 | project-local routines, xprocs, job due times | `sase_polish_proc_lanes` |
| Projects / stats / init | 5 | `sase project stats` (in progress), Statistics tab, chezmoi project, `sase init -a` | `sase_projects` |
| Remote / fleet / Telegram | 4 | Telegram not on every machine, `/fleet`, restart drain+relaunch | `sase_remote` |
| Product rename | 3 | power/po, bai, sal | **new `sase_rename`** |
| Listen / audio | 2 | AntennaPod feeds, rename listen→talk | **new `sase_listen`** |
| Recovery / failed agents | 2+ | restart on dismiss, "Better failed agents", Recovery panel (counted under TUI above) | **new `sase_recovery`** |
| In-flight one-offs | 2 | rrimps PR#301, E2E agent history | stay on parent until done |
| Product-wide `#ref` | 2+ | agentic SE reading list, Reality Is the Final Verifier | stay on parent |
| Uncategorized leftover | ~45 | Docker, Windows, multi-user, snips sidecar, fork-as-stranger, stitch ideas, `sase-capture`, agent report, speed up launches, … | see split table below |

**Currently Next & In Progress (do not lose these in a move):**

| Line | Status | Task | Move with |
| --- | --- | --- | --- |
| 38 | `[*]` | Reply to rrimps PR#301 | stay (one-off) |
| 39 | `[*]` | Fix scrollbar and card focus for main data deck | `sase_tui` |
| 40 | `[/]` | PyPI release reliability design | `sase_pypi_releases` |
| 43 | `[*]` | Fix `\|` and `\` keymaps so they reverse | `sase_tui` |
| 44 | `[*]` | GitHub native merge-queue primer | `sase_pypi_releases` |
| 46 | `[/]` | `sase project stats` | `sase_projects` |
| 53 | `[*]` | E2E test new agent history | stay until done |

**Inbox `[ ]` rows:** agentic SE reading list (keep on parent); auto-autonomy epic roadmap (→ `sase_post_blog` / `sase_better_plans`); Codex 62K credits (eject).

**Recently done (9 on 2026-10-19):** local pager links, Mac sshd prompt `#ref`, Grok as third `#research_swarm` member, 11q.w0 wait `#ref`, PyPI track 0 leftover `#ref`, image-agent mermaid, **Release v0.18.0**, Google release-engineering `#ref`, research-swarm mermaid handoff. The v0.18.0 release is why several `#ref`s can now move onto `sase_pypi_releases` / be left in Done.

---

## 5. Recommended project split

### 5.1 Routing rules

- One live `#task` lives in **exactly one** project note. The parent keeps a wikilink to the child `#prj`, not a second copy of the task.
- `#ref` tasks travel with the work they inform.
- `dependsOn: sase_pypi_releases__prj` is a *blocker*, not a reason to store the task on the PyPI note. Memory-deck and pi/hermes stay with memory/providers and keep the dependency.
- Do not reopen canceled children (`sase_sites`, `sase_message_boards`, `sase_setup`, `sase_blog_blockers`) for leftovers.
- Do not reopen done children whose original `#prj` is complete (`sase_decks`, `sase_research`, `sase_final_polish`, `sase_gate`, `sase_dir_xprompts`). Mint a *new* note for the leftover cluster.
- New notes use the existing `[[new_project]]` template, `parent: [[sase]]`, and get a `#prj` completion criterion plus a `🧩 Sub-projects` line back on `sase.md`.

### 5.2 New child notes to create (6)

| New note | `#prj` criterion (draft) | Takes from `sase.md` | Why a new note |
| --- | --- | --- | --- |
| `sase_tui` | Deck, PIW, keymap, and Agents-tab chrome are pleasant enough to demo | ~30 tasks: scrollbar, reverse splits, `,H`/`HH`/` ,/`/` ,?`/`M` marks, PIW completion, toasts, AAA linenos, pin deck, rename Main→IO, condensed left pane, `l`-keymap resort bug | `sase_decks` closed after AMP migration; this is the leftover UX debt |
| `sase_macros` | Macros/xprompts/`%` directives are one coherent surface | ~20 tasks: Macros deck, `%auto`/`%tag`/`%q`/`%clan`/`%{}`, snippet freshness, xprompt-by-tag, project-local xprompt skills | `sase_dir_xprompts` closed; no current macros child |
| `sase_listen` | Research/articles/papers publish to distinct AntennaPod feeds; listen vs talk naming decided | L143 AntennaPod feeds; L299 rename listen→talk; Future Work audio summaries | `sase_research` closed; listen is already a plugin |
| `sase_rename` | Pick or reject a public name; stop accumulating one-off rename tasks | L126 power/po, L745 bai, L1027 sal, Future Work sawi; related research already exists (`sase_rename_new_name_shortlist`, `should_sase_become_sasesh.md`) | Four tasks, one decision |
| `sase_finalizers` | Host-owned completion is either reaffirmed or replaced; gates/monitors/finalizers have one story | L129 evaluate host-owned completion; L435 migrate gates/monitors to finalizers; L472 finalizer output vars; L1227 message-checking finalizer; L162 bulk gate cmds; L208 generative JIT gates; L1161 invoke gates directly; Future Work `%final` | `sase_final_polish` and `sase_gate` are done; this is the next architecture pass |
| `sase_recovery` | Failed/in-flight agents can be relaunched in bulk from one panel | L91 Recovery/Relaunch panel; L405 restart on dismiss; L721 better failed agents; L1039 `,X`; L1001 relaunch after machine restart (shared with `sase_remote`); Future Work retry explanation / RETRYING status | Spread across TUI, remote, and Future Work today |

Optional seventh, only if Docker + Windows + multi-user grow past three tasks: `sase_platforms`. Today that is three isolated items — park them on `sase_better_installs` instead of minting a note.

### 5.3 Move into existing children (do this first)

| Destination | Move these parent tasks (line numbers) | Notes |
| --- | --- | --- |
| `sase_pypi_releases` | 40, 44, 152, 184, 202, 1126 | Reliability design is already `[/]`. Merge-queue primer **blocks** the fence reassessment (L184). Clippy post-commit hook and `check-full` belong with green master. |
| `sase_projects` | 46, 353, 355, 380, 677, 964 | Stats command is `[/]` and already `BLOCKS` L353. Chezmoi-as-project is an instance of "projects work." |
| `sase_memory` | 57, 86, 102, 112, 121, 308, 420, 565, 570, 670, 756, 784, 852, 906, 921, 954, 1105, 1240, 1270, 1281, 1299 | Collapse L57+L121 to one memory-deck task. Drop L1105 in favor of the existing child stitch task. L1208 `mac.md` is remote/memory — prefer `sase_remote`. |
| `sase_art` / `sase_art_links` | 80, 123, 204, 213, 229, 358, 707, 795, 816, 1119, 1219 | Merge L123+L358 into `sase_art_links` ^artifact-create. L289 `%wait` for artifacts is monitor+artifact — put the wait half on `sase_monitor`, keep a link. |
| `sase_more_agent_clis` | 117, 119, 148, 371, 482, 732, 945, 1031, 1275, 1285 | Also add crush/OpenCode from that child's own Future Work. Keep `sase_pre_blog` pi/hermes as the *launch-blocking* copies; delete the parent `#ref`s once linked. |
| `sase_pre_blog` | (own duplicates only) | Dedup L18/L25. Do not add a third pi/hermes copy. |
| `sase_remote` | 137, 664, 939, 1001, 1208 | Telegram-not-everywhere cites a MacBook axe digest — that is fleet/config. |
| `sase_usage` | (none of the quota *nags*) | Product usage-window work already lives here. Do not dump Codex-reset calendar items onto it. |
| `sase_monitor` | 273, 289 (wait half), 347, 504, 578, 582, 593, 825, 1075 | `%hold` E2E is high priority. Standalone-proc Agents-tab bug is shared with `sase_polish_proc_lanes`. |
| `sase_polish_proc_lanes` | 398, 508, 773, 833, 930, 988 | axe/lumberjack/chop glossary rename is also `sase_better_glossary` — pick glossary as the *name* change, proc-lanes as the *runtime* change. |
| `sase_better_plans` | 23, 74, 132, 224, 282, 339, 426, 613, 751, 983, 1183 | Merge the two grill rows. Auto-autonomy roadmap depends on post-blog — keep that `dependsOn`. |
| `sase_better_tasks` | 322, 392, 411, 699, 781, 879, 914, 942, 1044, 1080, 1088, 1246 | Stream-bead (L112) can live here *or* on memory; I would keep it on memory because it is a memory stream. |
| `sase_better_vars` | 472, 554 | `%name` is a directive — if `sase_macros` exists, `%name` can go there instead. Either is fine; do not copy. |
| `sase_better_config` | 439, 643, 1066 | `skill: true`/`ref: true`, project-local `max_running_agents`, project-local files. |
| `sase_better_glossary` | 833 (names), 921, 1134 | TUI header rows, SDD removal, axe/chop terms. |
| `sase_blog` / `sase_post_blog` | 187, 258, 376, 491, 494, 598, 692, 1198 | Gallery might instead sit on `sase_art` (web client already there). `bugyi@sase.sh` is ops; keep with blog/launch. |
| `sase_skill_bundles` | 639, 756 (if not on memory), 1281 (if not on memory) | Pick **one** home for "skill bundles as a memory web." I would keep the web question on `sase_memory` and the `//skill` syntax on `sase_skill_bundles`. |
| `sase_goals` | 654 | Eval framework. The Databricks *product* blog `#ref` already lives on `sase_goals`; the Databricks *CV* `#ref` on the parent is personal. |
| `sase_toobig_symvision` | Future Work L1332 `#split_file` / 1000-line Rust files | Promote that bullet onto the existing child. |
| `sase_agents_repo` | L1152 publish to agents sidecar on plan approve | Fits "agents repo as the publication plane." |
| `sase_better_installs` | 350 Docker, 459 Windows | Small enough to live here. |

### 5.4 Stay on `sase.md`

Keep the parent as the **product umbrella + now/next + directional reading**, not as a 200-task inbox.

| Keep | Why |
| --- | --- |
| `#prj` 1000 GitHub stars | Umbrella completion criterion; already lists children |
| L38 Reply to rrimps PR#301 | One-off; will complete or cancel this week |
| L53 E2E test new agent history | Leftover of a done child; finish in place |
| L20 agentic SE reading list | Product-wide, `keeps:: 1` |
| L254 Reality Is the Final Verifier | Product-wide paper |
| A short "unsorted" blocked bucket of truly cross-cutting leftovers after the moves | Docker/Windows if not sent to installs; fork-as-stranger; stitch-ideas (or send stitch-ideas to a future `sase_stitch` only if that cluster grows past ~5) |

After routing, the leftover "misc" pile is still ~25–40 tasks (fork-as-stranger, stitch ideas, `sase-capture`, snips sidecar, multi-user, agent report, launch speed, workspace allocation, `sase read/show`, `sase prompt search`, black-as-collaboration-demo, …). **Do not create `sase_misc`.** Either:

- attach each leftover to the closest open child in a second pass, or
- keep a single `### Later` section on the parent capped at ~30, and refuse new tasks there without a child destination.

### 5.5 Eject from the SASE project tree

| Item | Destination |
| --- | --- |
| Codex credits / reset calendar (L27, L59) | personal ops / calendar, or a non-project `quotas.md` |
| Claude Code reset (L528) | same |
| Grok Heavy → X Subscription (L488) | same |
| Cap Muse $20 (L1292) | same |
| Spotify + Abby (L192) | personal / Keep |
| Databricks NYC CV (L748) | career notes — it is already a `#ref` to interview prep |
| Opus + Blender (L924) | personal |
| Future Work "EMAIL woman about GitHub stars" | the `#prj` already tracks stars |

`sase_usage` stays the home for *in-product* usage windows, alias load-balancing, and usage notifications.

### 5.6 Suggested execution order

1. **Hygiene (same day):** delete Future Work L1357 duplicate; delete `sase_pre_blog` duplicate; strike shipped Future Work (dyn families, `/sase_run` create, HITL approve, Antigravity); merge parent grill pair and memory-deck pair *in place*.
2. **Move in-flight work** so Next & In Progress does not stall: PyPI reliability + merge-queue primer → `sase_pypi_releases`; `sase project stats` → `sase_projects`; deck scrollbar + reverse keys → new `sase_tui` (create that note first).
3. **Bulk-route the big existing children:** `sase_memory`, `sase_art`, `sase_better_plans`, `sase_better_tasks`, `sase_monitor`, `sase_remote`, `sase_more_agent_clis`.
4. **Create the remaining five new notes** (`sase_macros`, `sase_listen`, `sase_rename`, `sase_finalizers`, `sase_recovery`) and move their clusters.
5. **Eject personal/quota rows.**
6. **Sweep Future Work:** promote still-wanted bullets onto the matching child as `#task`s; delete the rest. Goal: Future Work on `sase.md` empty or under ~10 true someday items.
7. Update the `#prj` sub-project line: add the six new notes; leave done/canceled children struck.

A practical batch size is the one already written on the parent (L1111): groups of ~20. That is six to eight move sessions, not one mega-edit.

---

## 6. Overall summary of the tasks in this file

`~/bob/sase.md` is the SASE product note. It is doing four jobs at once:

1. **Umbrella project** — "hit 1000 GitHub stars," with a roster of 60 children (22 still open).
2. **Active workbench** — 10 truly open rows (3 inbox, 7 next/wip), including the live PyPI reliability epic, `sase project stats`, two deck-keymap fixes, a merge-queue primer, an agent-history E2E, and a GitHub PR reply.
3. **Scheduled idea dump** — 218 blocked `#task`s, mostly medium priority, randomized out weeks to months. Themes: TUI chrome, macros/xprompts, memory, artifacts, beads, plans/epics, providers, monitors, docs, remote/fleet.
4. **Shadow backlog** — 79 Future Work bullets + 4 Requirements that are *not* tasks, including one exact duplicate and several items already completed in children.

Nine tasks were checked off on 2026-10-19, including **Release v0.18.0**. That release is the reason several provider and research `#ref`s are now unblocked *and* the reason they should leave the parent: they are follow-through, not umbrella work.

The file is not full of title-identical duplicates. It is full of **split-brain ownership**: the same idea lives as a parent `#task`, a child `#task`, and sometimes a Future Work bullet (`/sase_stitch`, pi/hermes, artifact create, grill, `,X`, hidden agents, memory deck). The highest-leverage split is ownership cleanup, not invention of twenty new notes.

**What "done" looks like for this research's goal:**

- `sase.md` holds the `#prj`, a short Now/Next, a short Later, and a handful of product-wide `#ref`s.
- Each live feature cluster has exactly one child note.
- Six new children exist for TUI, macros, listen, rename, finalizers, and recovery.
- Personal quota and career tasks are off the product note.
- Future Work is no longer a second, uncounted backlog.

Until that happens, the 22 "open" children on the `#prj` line are a table of contents for work that is still physically sitting in the parent.
