# New Records for the SASE Blog Zettel Album

**Question.** Which new records should be added to the `sase_blog_zettel` album before
drafting the SASE launch post?

**Short answer.** The album has 29 seeds, but 8 of its 18 sections have no records:
🚦 Gates, 🛠️ Tools, 💥 Fleet, ⚙️ Services, 🔌 Plugins, 🔍 How I use SASE, 🎬 The Demos,
and 🏁 Conclusion. Two populated sections also lack the record their heading promises:
"What is SASE?" never defines *meta-harness*, and "Turn < Session < Clan < Tribe" has no
record that explains turns, sessions, clans, or tribes. For most of these gaps you
already wrote the idea down somewhere: in the `sase_blog` Notes list, in the abandoned
Wave 1–4 capture plan, in older `docs/blog/` drafts, or in SASE's own decision records.
The ranked list at the end gives 32 candidates. The top 14 fill every empty section and
both missing definitions.

---

## 1. What I read

- **The album.** `sase_blog_zettel.md` and all 29 records under `sase_blog_zettel/`.
- **Blog project notes.** `sase_blog.md`, which holds the long Notes list, Screenshots,
  and Later Posts. Also `sase_blog_contents.md`, `sase_blog_drafts.md` (Waves 1–7),
  `sase_blog_annotations.md`, `sase_blog_0_legacy_notes.md`, `why_sase.md`,
  `sase_pre_blog.md`, `sase_post_blog.md`, and `done/sase_blog_done.md`.
- **Annotations and earlier research.** `ref/notes/sase_blog_261116` (your 21 PDF
  highlights) and the abandoned "Paste-ready captures for SASE Blog Zettel Waves 1–4"
  research, which proposed 15 records. Only some of those were ever captured.
- **Other SASE notes in Bob.** The `sase.md` project list, the Notes and Future Work
  sections of about 15 `sase_*` project notes, `sase_ideas.md`, and the `goog_tools.md`
  entry about SASE's origin.
- **The SASE repo.**
  - The older blog drafts in `docs/blog/posts/`, especially
    `why-coding-agents-need-orchestration.md` ([00]) and the 2026-07-08 launch draft.
  - The `decisions` memory web: 31 records, of which I read 9 in full.
  - Glossary entries for gate, gate turn, clan, tribe, hood, hijack, routine, job,
    receipt, and goal.
  - `docs/reference/automation/tools.md` and the VHS tapes in `demos/tapes/`.
  - `git log`: 17,234 commits, the first on 2026-02-14 ("Add gai -> sase migration
    beads").
- **The research sidecar.** I counted reports by month: 1,770 Markdown reports in
  total, 758 of them from October 2026.
- **Your reference library** (`bob ref`). I listed your finished references from
  Oct–Nov 2026 and read your comments on 9 of them.
- **The web.** Two quick searches: "meta-harness" and Omnigent.

I did not open, search for, or read any other swarm member's report.

---

## 2. Where the album stands

| Section                  | Records | Gap                                                                    |
| ------------------------ | ------: | ---------------------------------------------------------------------- |
| 🪝 Intro                  |       1 | Origin story and stats caveat exist only in `sase_blog_contents`       |
| 🧱 What is SASE?          |       3 | Nothing defines "meta-harness" or compares SASE to Gas Town or Codex   |
| 📜 Macros                 |       4 | Fine; alternations, forks, and the Vim-mode joke are missing           |
| 🤖 Agent CLIs             |       2 | No resilience or outage story; no adapter story                        |
| 🧠 Memory                 |       2 | Has the "every wrong way" joke but not the evidence behind it          |
| 🔁 Turn < … < Tribe       |       3 | **No record explains turns, sessions, clans, or tribes**               |
| 🚦 Gates                  |   **0** | Empty                                                                  |
| 🎨 Artifacts              |       5 | Well covered                                                           |
| 💾 VCS                    |       2 | No workspaces or mentors story                                         |
| 🛠️ Tools                  |   **0** | Empty                                                                  |
| 💥 Fleet                  |   **0** | Empty                                                                  |
| ⚙️ Services               |   **0** | Empty                                                                  |
| 🔌 Plugins                |   **0** | Empty                                                                  |
| 🔍 How I use SASE         |   **0** | Empty                                                                  |
| 🎬 The Demos              |   **0** | Empty                                                                  |
| 🛑 Not ready              |       2 | No concrete limitations list; no naming record                         |
| 🔮 Future Work            |       5 | No mobile or web record, though it is in every old outline             |
| 🏁 Conclusion             |   **0** | Empty                                                                  |

Two things to note about this state:

- **The `^at-least-one-rec-in-sect` task is checked off, but 8 sections are still
  empty.** It was closed on 2026-11-24, and its sub-bullet "Create one task for every
  empty section!" is still unchecked. Either these sections were added after the task
  closed, or the check missed them. The recommendations below give every empty section
  at least one candidate. If a section still doesn't earn a record, the task's own
  fallback applies: remove the section.
- **One annotation was marked converted but has no record.** The task "Convert the
  'never let them disable Vim mode' joke annotation to a zettel (prompts)" was completed
  on 2026-11-21. Yet no record and no record note mentions Vim; `grep -ril vim
  sase_blog_zettel/` finds nothing. The other two annotations closed the same way did
  land: stashed prompts became a note on `layers_of_prompt_management`, and
  `tmux_ai_window` became a note on `what_came_before`. The Vim joke was lost.

---

## 3. Ideas you already wrote down that never became records

These candidates cost the least to add, because the claim is already in your words.

| Your note (source)                                                                                   | Where it would go  | Status                                                        |
| ---------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------- |
| "Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?" (`sase_blog` quotes) | 🚦 Gates            | Proposed as `^gates-plans-epics` in the Wave 1 captures; never captured |
| "Things that sase generalizes: Gates -> Plans -> Epics…" (`sase_blog` 2026-08-07)                     | 🚦 Gates / 🧱 What  | Never captured                                                |
| "I need your help. I'm out of tokens." + GitHub `type:poll` issues (`sase_blog` 2026-08-07)           | 🏁 Conclusion       | Proposed as `^need-your-help`; never captured                  |
| "Create list of limitations!" (2026-06-07) + "Mention that the agents tab is the buggiest part of the TUI!" (2026-06-18) | 🛑 Not ready         | Proposed as `^limitations`; never captured                     |
| "_I'm bad at naming things but I worry that indicates a deeper problem with the design_" + "Make jokes about why sase and xprompts are named the way they are" | 🛑 Not ready         | Proposed as `^naming`; never captured                          |
| "Break down gastown differences…" + "Many sections in the blog post should link to the analogous crazy term used by GasTown" (marked high priority) | 🧱 What             | Nothing about Gas Town in any record                          |
| "The term 'sub-agent' doesn't cut it when referring to agents that other agents run!" (2026-08-01)   | 🔁 Turn              | Never captured                                                |
| "Alternations allow for 'vibe evals'." (2026-06-21) + screenshot `20260619_214831.png`                | 📜 Macros / 🔮 Evals | Never captured                                                |
| "Sase does not claim optimal performance, but optimal experience!" (2026-07-16)                       | 🧱 What / 🏁 Close   | Never captured                                                |
| "Explain how you use the 'different types of tokens'!" (2026-08-03) + "AI era of scarcity" ([00] draft) | 🤖 Agent CLIs        | Never captured                                                |
| Retries got you through a Claude outage of under 30 minutes (screenshot `20260616_140429.png`)        | 🤖 Agent CLIs        | Never captured                                                |
| `%wait` example (`20260616_115015.png`); questions/retries example (`20260624_074728.png`)            | 🎬 Demos / 📜 Macros | Never captured                                                |
| "Mention loop engineering and graph engineering at some point!" (2026-08-11)                          | 📜 Macros            | Never captured; you finished "The Coming Loop" on 2026-10-16    |
| "Add AI broccoli section to blog." (Google Keep, 2026-09-10)                                         | 🛑 Not ready?        | Never captured; the Keep note holds the actual idea           |
| Vim-mode joke (annotation `^h-d32a08558083`)                                                         | 📜 Macros / 🏁 Close | Task marked done, but the joke appears nowhere                |
| Legacy outline: "Pluggable: VCS / Workspace Plugins, LLM Provider Plugins, LSP" and "sase-telegram: build motivation for mobile app" | 🔌 Plugins          | Never captured                                                |
| Legacy outline: "AXE and Lumberjacks and Chops (oh my)"                                              | ⚙️ Services          | Proposed as `^routines-jobs`; never captured                   |
| Legacy conclusion: "End with 'no weasels; just work'."                                               | 🏁 Conclusion       | Never captured                                                |

You deliberately cut five ideas on 2026-11-22: the closet diagram, the SWE timeline, the
hub-note quote, `reads`/`snips` (superseded by `files_not_tracked_by_a_vcs`), and the
separate finalizer-ideas record. I don't re-propose any of them. If you still want the
SWE timeline, it fits as a note on `what_came_before`.

---

## 4. Candidates by section

Each candidate has a suggested stem, a **draft claim** written to be rewritten in your
voice, and the evidence that supports it. Names follow current HEAD: macros, Patches,
prompt composer, gate turn (formerly gate shell), routine (formerly Lumberjack), job
(formerly Chop), and the sase scheduler (formerly AXE).

### 🚦 Gates (empty)

**A. Plan Mode Is a Gate** — `plan_mode_is_a_gate` (Tier 1)

- **Draft claim.** "Plan mode is one instance of a deeper primitive, the gate: a durable
  request for one human decision. Gates grow into plans, and plans grow into epics."
- **Why it belongs.** It is your own quote, and it explains why SASE has plans and epics
  at all.
- **Evidence.**
  - Your 2026-08-07 "Things that sase generalizes" list.
  - The glossary entry "Sase Gate": a gate is a bundle under
    `~/.sase/interaction_requests/`, and every surface answers the same bundle.
  - An option query such as `(approve AND commit) OR reject`.
- **Asset.** `img/20260824_141701.png` (an agent read 4 related plans while planning).

**B. A Gate Never Blocks an Agent** — `gates_never_block` (Tier 2)

- **Draft claim.** "Waiting on a human should cost nothing. When an agent opens a gate,
  its turn ends. The decision lives in a non-LLM gate turn that outlives the agent and
  runs whatever commands I pick."
- **Evidence.**
  - The decision record `gates-never-block`, which describes a real failure: a gate
    stayed pending on a `.response.lock`, and a later agent had to rebuild the state.
  - The same gate can be answered from the TUI, Telegram, mobile, or `sase gate`.
- **Fun detail.** Agents never run `sudo` or a global `just install`. They propose those
  commands as gates (`/sase_sudo`, and the decision record
  `global-install-is-human-only`). "My agents have to ask permission to reinstall
  themselves" is a good line.

### 🛠️ Tools (empty)

**C. Every Command Is a Record** — `every_command_is_a_record` (Tier 1)

- **Draft claim.** "Agents run tests constantly, so test runs should be data, not
  scrollback. `sase tool run` records every check as a ToolRun. Triage labels each
  failure NEW, KNOWN, FLAKY, or UNKNOWN, and never changes the exit code."
- **Evidence.**
  - `docs/reference/automation/tools.md`.
  - The decision records `guarded-recipes` (agents can't run guarded recipes raw) and
    `triage-annotates-does-not-change-exit-codes` ("KNOWN requires an independent
    witness").
- **Hook.** Agents inherit a red master all the time. They need to know which failures
  are theirs.

**D. Host Capacity Is the New CI Budget** — `host_capacity_is_the_ci_budget` (Tier 3;
could merge into C)

- **Draft claim.** "With ten agents on one machine, the bottleneck isn't how fast the
  tests run. It's the CPU they share."
- **Evidence.**
  - The decision records `two-speed-verification` and `check-full-is-explicit`: the full
    suite can use a quarter to half of the machine.
  - Holds and admission control.
  - You finished Anthropic's "Agentic coding is straining CI" on 2026-10-23.

### 💥 Fleet (empty)

**E. One Fleet, Three Machines** — `one_fleet_three_machines` (Tier 2)

- **Draft claim.** "My agents run on more machines than I do. A meta-harness should
  treat machines as a resource pool, the same way model aliases treat models."
- **Evidence.**
  - apollo, athena, and the Mac over Tailscale.
  - `%dispatch` to a remote machine.
  - The `sase-agents` repo syncs agent records across machines (publish-only, per the
    decision record `agents-sync-publish-only`).
  - The research report `waiting_on_remote_machine_agents`.
- **Keep it honest.** "Fix remote machines!" and "Wait for remote agents with `%wait`"
  are still open post-blog tasks. This record could close with "and it half works."

**F. Every Agent Gets Its Own Clone** — `every_agent_gets_a_clone` (Tier 3; Fleet or VCS)

- **Draft claim.** "Each agent works in its own full clone (`sase_<N>`), and the host,
  not the agent, owns the commit. That's why twenty agents don't trip over each other."
- **Note.** This is a natural companion to `host_owned_completion`. Wave 2 of the
  captures proposed it as `^vcs-workspaces`.

**G. Agent Hijack** — `agent_hijack` (Tier 3)

- **Draft claim.** "Sometimes I need to grab the wheel. A hijack stops an agent's turn
  but keeps its workspace, so I can continue with a different model."
- **Caveat.** "Fix agent hijacking!" is your top open SASE task (screenshot
  `img/20261115_083106.png`). This might belong under 🛑 Not ready as well.

### ⚙️ Services (empty)

**H. Agents on a Schedule** — `agents_on_a_schedule` (Tier 1)

- **Draft claim.** "The most useful agents are the ones I never prompt. The sase
  scheduler runs routines and jobs that check for agent CLI updates, split files that
  get too big, and audit recent commits."
- **Evidence.**
  - Glossary entries for routine and job.
  - The `toobig_split` routine, which `sase_is_too_complex` already mentions.
  - The community `bugyi-chops` plugin.
  - The legacy outline's "AXE and Lumberjacks and Chops (oh my)". The renames to
    scheduler, routines, and jobs are good material for the naming record (N).
- **Note.** `agent_cli_installs_and_updates` already describes one routine. This record
  gives the section the general claim that record depends on.

### 🔌 Plugins (empty)

**I. The Core Doesn't Know GitHub Exists** — `the_core_doesnt_know_github` (Tier 1)

- **Draft claim.** "GitHub, Telegram, Neovim, my research library, and even my podcast
  feed are plugins. SASE's core only knows about agents, turns, and artifacts."
- **Evidence.**
  - `sase plugin list`: github, listen, research, spotify, and telegram are built in;
    bugyi-chops is a community plugin.
  - The decision record `plugin-commands` (plugins can mount `sase <name>`).
  - The legacy outline's "Pluggable" section.
- **Sub-idea.** The record could name Telegram as the "pocket cockpit," which also sets
  up the mobile record (AA).

### 🔍 How I use SASE (empty)

**J. Research Swarms Are How I Decide** — `research_swarms` (Tier 1)

- **Draft claim.** "I don't make a hard decision about SASE without a research swarm.
  Five agents from five labs research it independently, and a lead synthesizes their
  reports."
- **Evidence.** The research sidecar holds 1,770 reports. October 2026 alone produced 758
  (139 in Aug, 415 in Sep). The `__cld` / `__cdx` / `__grk` / `__mus` / `__gem` naming
  convention shows the cross-lab swarm at a glance.
- **Meta hook.** The research behind this album was itself a five-lab swarm. This pairs
  with `multi_provider_swarms`: that record says *why*, this one shows *how often*.

**K. SASE Runs More Than My Code** — `more_than_code` (Tier 3)

- **Draft claim.** "SASE started as a coding tool. It now manages my crontabs, dotfiles,
  Obsidian vault, Gmail, and Spotify playlists, all through skills and gates."
- **Evidence.** The `crontab`, `sase_spotify`, `sase_gmail`, `bob_ref`, and `bob_query`
  skills, and chezmoi as a linked repo.
- **Note.** This is the present-tense half of `bob_task_events`, which is the future
  half.

**L. I Listen to My Research** — `i_listen_to_my_research` (Tier 3)

- **Draft claim.** "Many of my research reports become podcast episodes. `sase listen`
  turns Markdown into chaptered MP3s, which I listen to on walks."
- **Evidence.** `lib/chat/sase_launch_post_introduction.mp3` and
  `sase_launch_post_outline.mp3`, plus your own task to "transcribe your blog post into
  a podcast episode and listen to it."

### 🎬 The Demos (empty)

**M. Five Scripted Demos** — `the_demos` (Tier 2), or one record per demo

- **Draft claim.** "Every demo in this post is a scripted VHS tape in the repo. You can
  rerun it against HEAD."
- **The five tapes in `demos/tapes/`.**
  - agents observability
  - multi-model fan-out (the only one already in `docs/videos/`)
  - prompt history and stash
  - prompt input
  - PRs pipeline
- **Warning.** `demos/out/last_generated_date.txt` says 2026-09-15. The tape names
  still say `ace` and "prompt input," but the latest commit renamed it to "prompt
  composer." Regenerate the demos before this record is ✅ Ready.
- **Alternative.** One record per demo, each claiming what that demo proves, would make
  the section easier to walk.

### 🏁 Conclusion (empty)

**O. I Need Your Help: I'm Out of Tokens** — `i_need_your_help` (Tier 1)

- **Draft claim.** "SASE has about one user. I need your help, partly because I'm out of
  tokens."
- **The ask.** The GitHub `type:poll` issues you planned for the end of the post.
- **Optional.** The legacy closing line, "no weasels; just work."

**P. Optimal Experience, Not Optimal Performance** — `optimal_experience` (Tier 2;
works in What or Close)

- **Draft claim.** "SASE doesn't promise the best benchmark score. It promises the best
  experience of supervising many agents."
- **Why it matters.** This sets expectations before the 🛑 section and heads off the
  "where are your evals?" objection, which your `evals` record admits.

### 🧱 What is SASE? (add 2)

**Q. SASE Is a Meta-Harness** — `meta_harness` (Tier 1)

- **Draft claim.** "Claude Code, Codex, and the rest are harnesses around a model. SASE
  is a harness around those harnesses. It wraps agent CLIs, not models."
- **Why it's urgent.** "Meta-harness" appears in the second sentence of
  `sase_blog_contents`, with footnote `[2]: TODO: Link to Omnigent`. No record defines
  the term yet.
- **Context.**
  - The term is now in common use. Databricks open-sourced Omnigent as a "meta-harness"
    in June 2026; it wraps Claude Code, Codex, Pi, and custom agents.
  - Your library has the Omnigent post as *dropped*.
  - You finished "Harness Engineering: … A Source-Code Study of Eleven Systems" on
    2026-10-10.
  - The [00] draft already has a section titled "SASE Wraps Agents, Not Models."
- **Reading before drafting.**
  - [arXiv 2611.06946](https://arxiv.org/pdf/2611.06946), "Beyond the Agent Harness:
    Boundary Criteria for Software-Factory Orchestration — A Single-Operator Case
    Study." A *single-operator* case study is close to SASE's situation. It is not in
    your library, and I did not read its body.
  - The Meta-Harness paper (Lee et al., arXiv 2603.28052). It is a different thing from
    Omnigent, so don't conflate the two.

**R. Mayor vs. Cockpit: SASE and Gas Town** — `gas_town` (Tier 1)

- **Draft claim.** "Gas Town asks what a town of autonomous agents can do. SASE assumes
  agents can do the work and asks what the cockpit should look like for one engineer
  supervising them."
- **Evidence.**
  - You marked this high priority twice in your notes.
  - You finished "Gas Town Emergency User Manual" on 2026-10-19.
  - The legacy outline's claim that Gas Town's "fatal flaw" is that it can't mix LLM
    calls with deterministic code.
  - The [00] draft already has this section and a "Mayor vs cockpit" diagram brief.
- **Relation to `beads_and_birds`.** That record covers beads only. This one gives you
  the anchor for your planned term map ("link to the analogous crazy GasTown term").
- **Possible companion.** The [00] draft argues "The Codex App Is The Real Competitor."
  You also finished OpenAI's Symphony orchestration post. Consider a third record,
  "My real competitor is the Codex app," if you want an honest landscape paragraph.

### 🔁 Turn < Session < Clan < Tribe (add 2–3)

**S. Agents Are Single-Turn** — `agents_are_single_turn` (Tier 1)

- **Draft claim.** "A SASE agent is exactly one provider turn. Anything longer, like
  waiting, monitoring, planning, or asking me a question, is a handoff to a new turn,
  never an agent promising to resume."
- **Why first in its section.** `finalizers`, monitors, gates, and handoffs all follow
  from this rule.
- **Evidence.** The decision record `single-turn-agents` has a real reversal story:
  `feat(cli)!: make run detached-only` (2026-07-02), then
  `feat(cli)!: retire detached proc mode` (2026-08-15).
- **Supporting record.** `adapters-normalize-harnesses` explains the cost: Muse's "wake"
  is an invisible, unbounded keep-alive that SASE has to turn off.

**T. "Sub-agent" Doesn't Cut It** — `sub_agent_doesnt_cut_it` (Tier 1)

- **Draft claim.** "Agents that other agents launch aren't sub-agents. They're members
  of a session, a clan, or a tribe, and each word means something different."
- **Why.** Your section title promises this hierarchy, and no record explains it.
- **Evidence.**
  - Glossary entries for clan (a rootless container whose members run in waves derived
    from `%wait` edges), tribe (a user-facing label across clans), and hood (a shared
    name prefix).
  - Your note that "the agents tab is the buggiest part of the TUI."
- **Asset.** The agents observability demo.

**U. Forks, Not Multi-Turn Chats** — `forks_not_chats` (Tier 2)

- **Draft claim.** "SASE has no multi-turn agents. `#fork:<agent>` copies one agent's
  context into a new agent, so every unit of work keeps its own record and workspace."
- **Evidence.** The [00] draft's section "Forks Instead Of Multi-Turn Agents," and the
  `%wait` + `#fork` example.

### 🧠 Memory (add 1–2)

**V. Mechanism Follows Corpus** — `mechanism_follows_corpus` (Tier 1)

- **Draft claim.** "I built memory retrieval three times before anything needed it, and
  deleted all three. Now SASE ships no memory mechanism until a real corpus needs it."
- **Evidence.** The decision record `corpus-before-mechanism`, with dates and commits:
  - Keyword-triggered dynamic memory, built 2026-04-12 and removed 2026-05-31
    (`e8c2f14bb`).
  - Episode recall, built 2026-05-23 and removed 2026-06-15 (`37973b8b3`). That removal
    deleted a CLI family, a modal, a doctor check, and a docs page.
  - The `keywords:` metadata, removed 2026-07-13 (`21e1640ee`).
- **Why it's its own record.** It's the evidence behind your joke "I've implemented
  memory every wrong way possible." A note on `memory` would also work, but the claim is
  distinct and quotable.

**W. Decision Records Are Memory** — `decision_records` (Tier 2)

- **Draft claim.** "The most useful memory I give agents isn't facts. It's *why* we
  decided something and *what would change our mind*."
- **Evidence.** The `decisions` web has 31 immutable records, each with Claim, Why,
  Cost, and "Reopens when." Old records are superseded by new ones, never edited.
- **Note.** This would be a good companion to `memory_and_docs_are_the_same`.

### 🤖 Agent CLIs (add 1–3)

**X. An Outage Is a Non-Event** — `outages_are_non_events` (Tier 2)

- **Draft claim.** "When Claude went down for half an hour, my agents retried and moved
  on. One lab's outage shouldn't stop my work."
- **Evidence.**
  - Screenshot `~/tmp/screenshots/20260616_140429.png`.
  - `||` fallback chains in model aliases. The decision record
    `size-alias-effort-ladder` says every alias should reach more than one provider.
- **Pairing.** Makes the Satya Nadella record concrete.

**Y. Token Scarcity** — `token_scarcity` (Tier 3)

- **Draft claim.** "Cheap, unlimited inference is ending. A meta-harness has to put
  scarce reasoning where it matters."
- **Evidence.** The [00] draft's "Scarcity Is Coming For Our Robot Budgets" section
  (credited to The AI Daily Brief), and your note "Explain how you use the different
  types of tokens!"
- **Overlap.** Close to `usage_limits_and_api_costs`. Merge the two if they say the same
  thing.

**Z. Seven Harnesses, Seven Ideas About Waiting** — `adapters_normalize_harnesses`
(Tier 3)

- **Draft claim.** "Supporting seven agent CLIs means fighting seven private ideas about
  background work. SASE makes each one conform."
- **Evidence.** There are seven provider adapters: Claude, Codex, Muse, Grok, agy,
  OpenCode, and Qwen. The Muse "wake" story is in the decision record
  `adapters-normalize-harnesses`.

### 📜 Macros (add 1)

**AE. Alternations Are Vibe Evals** — `vibe_evals` (Tier 2)

- **Draft claim.** "`%{%m:codex | %m:claude}` runs the same prompt on two labs' models
  side by side. It's the cheapest eval I have."
- **Evidence.** Screenshot `20260619_214831.png`. It links to the `evals` record and
  gives that record its first evidence.

### 💾 VCS (add 1)

**AB. My Reviewers Were Too Noisy** — `mentors_too_noisy` (Tier 2)

- **Draft claim.** "Automated reviewers (mentors) hurt more than they helped, because
  an agent fixes every nit, and each fix means another commit and another review."
- **Evidence.** In "How the Claude Code team does code review," you highlighted "Noise
  costs more when the author is an agent…" and commented: "This feels like the problem I
  was having with mentors."
- **Fit.** This is an honest lesson that fits the 💾 VCS section.

### 🛑 Not ready (add 2)

**AC. A Prototype Gone Wild** — `limitations` (Tier 1)

- **Draft claim.** "SASE has about one user, and it shows."
- **Concrete limitations, all already in your notes.**
  - The Agents tab is the buggiest part of the TUI.
  - Agent hijacking is broken.
  - Remote machines are broken.
  - The security audit hasn't happened.
  - Unstable features aren't behind flags yet (`^put-all-unstable`).
  - The demos are stale.
  - About 17K commits and about 2.9M lines.

**N. Naming Things** — `naming_things` (Tier 2)

- **Draft claim.** "I'm bad at naming things, and I worry that points to a deeper
  problem with the design."
- **The rename history.**
  - gai → sase
  - xprompts → macros
  - ChangeSpec → Patches
  - AXE → sase scheduler
  - Lumberjacks → routines
  - Chops → jobs
  - gate shell → gate turn
  - prompt input widget → prompt composer, two days ago
- **Also.** The Secure Access Service Edge name collision (footnote `[1]` TODO), and
  that the name comes from Hassan et al.'s paper.

### 🔮 Future Work (add 1)

**AA. The Terminal Isn't the Only Window** — `mobile_and_web` (Tier 3)

- **Draft claim.** "Agent state should be shared across surfaces. The Rust core exists
  partly so that a phone app and a web client agree with the TUI."
- **Evidence.**
  - Mobile and web appear in every outline you've written: legacy item 9, Later Posts,
    and [09] "What's Next."
  - The decision record `rust-core-required` gives the litmus test.

### 🪝 Intro (add 1, optional)

**AD. From a LangGraph Loop to 17K Commits** — `origin_story` (Tier 3)

- **Draft claim.** "SASE started in October 2025 as a script that ran Gemini CLI in a
  LangGraph loop. After a migration in February it became sase, and it now has 17,234
  commits."
- **Evidence.** The `goog_tools.md` entry `z-251023-0u`, the first commit on 2026-02-14
  ("Add gai -> sase migration beads"), and the "Motion isn't progress" quote planned for
  the stats.
- **Sensitive.** It touches the open "why vs. that I left Google" decision in
  `^intro-v1`. Decide that before you seed this.

### Notes to add to existing records instead

These ideas don't need new records:

- **`model_alias_pools`.** Add the size-alias effort ladder (`@xlarge` → `@xsmall`): a
  model's first appearance runs at `xhigh` and drops one rung per reappearance.
- **`ai_slop`.** Add the canceled `sase_back_policy` project ("auto-deprecate backward
  compatibility") as the first slop category's example.
- **`layers_of_prompt_management`.** Its claim still says "prompt input widget." HEAD
  now says **prompt composer**.
- **`the_prompt_composer`.** Add the "loop vs. graph engineering" note and your "Goal
  number one / Goal number two" quote about the composer and LSP.
- **`goals`.** Add "No goal milestones; a legend is a group of epics" and "a goal should
  outlive an epic," if they didn't already land there.

---

## 5. Ranked recommendations

I ranked candidates by four tests, in order:

1. Does it fill an empty section or define a term the post depends on?
2. Does evidence already exist (a screenshot, a decision record, or a number)?
3. Did you already write the claim yourself?
4. Is it distinctive compared with other agent tools?

| #  | Record (stem)                                     | Section          | Why this rank                                                                     |
| -- | ------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------- |
| 1  | **Agents Are Single-Turn** (`agents_are_single_turn`) | 🔁 Turn           | Finalizers, gates, and monitors all depend on it; has a real reversal story       |
| 2  | **Plan Mode Is a Gate** (`plan_mode_is_a_gate`)     | 🚦 Gates          | Fills an empty section; your own quote; explains plans and epics                  |
| 3  | **SASE Is a Meta-Harness** (`meta_harness`)          | 🧱 What           | The intro's second sentence uses the term, and its footnote is a TODO             |
| 4  | **"Sub-agent" Doesn't Cut It** (`sub_agent_doesnt_cut_it`) | 🔁 Turn       | The section title promises this hierarchy, and no record explains it              |
| 5  | **I Need Your Help: I'm Out of Tokens** (`i_need_your_help`) | 🏁 Close      | Fills an empty section; your quote; the `type:poll` ask                           |
| 6  | **Research Swarms Are How I Decide** (`research_swarms`) | 🔍 How I use    | Fills an empty section; strong numbers (1,770 reports, 758 in October)            |
| 7  | **A Prototype Gone Wild** (`limitations`)            | 🛑 Not ready      | You asked for a limitations list on 2026-06-07; every item is in your notes       |
| 8  | **Agents on a Schedule** (`agents_on_a_schedule`)    | ⚙️ Services       | Fills an empty section; `toobig_split` and CLI-update routines are already cited  |
| 9  | **The Core Doesn't Know GitHub Exists** (`the_core_doesnt_know_github`) | 🔌 Plugins | Fills an empty section; six real plugins plus the `plugin-commands` decision |
| 10 | **Every Command Is a Record** (`every_command_is_a_record`) | 🛠️ Tools     | Fills an empty section; distinctive (triage never changes an exit code)           |
| 11 | **Mechanism Follows Corpus** (`mechanism_follows_corpus`) | 🧠 Memory     | Dated evidence for your "every wrong way" joke                                    |
| 12 | **Mayor vs. Cockpit** (`gas_town`)                   | 🧱 What           | You flagged it high priority twice; no record mentions Gas Town                   |
| 13 | **One Fleet, Three Machines** (`one_fleet_three_machines`) | 💥 Fleet       | Fills an empty section; honest about what's still broken                          |
| 14 | **Five Scripted Demos** (`the_demos`)                | 🎬 Demos          | Fills an empty section; the warning that demos are stale is useful on its own     |
| 15 | **A Gate Never Blocks an Agent** (`gates_never_block`) | 🚦 Gates        | A good second gate record; real failure story; the sudo-gate joke                 |
| 16 | **Naming Things** (`naming_things`)                  | 🛑 Not ready      | Your quote; a list of 8 renames; the name collision                               |
| 17 | **Alternations Are Vibe Evals** (`vibe_evals`)       | 📜 Macros         | Your note plus a screenshot; gives the `evals` record something concrete          |
| 18 | **Forks, Not Multi-Turn Chats** (`forks_not_chats`)  | 🔁 Turn           | Distinctive design choice; the prose exists in the [00] draft                     |
| 19 | **Decision Records Are Memory** (`decision_records`) | 🧠 Memory         | Distinctive; 31 real records to show                                              |
| 20 | **An Outage Is a Non-Event** (`outages_are_non_events`) | 🤖 Agent CLIs   | Screenshot proof; makes the Satya record concrete                                 |
| 21 | **My Reviewers Were Too Noisy** (`mentors_too_noisy`) | 💾 VCS           | Your own annotation; an honest lesson                                             |
| 22 | **Optimal Experience, Not Optimal Performance** (`optimal_experience`) | 🧱 What / 🏁 Close | Your positioning line; heads off benchmark objections                    |
| 23 | **Host Capacity Is the New CI Budget** (`host_capacity_is_the_ci_budget`) | 🛠️ Tools | Could merge into #10                                                        |
| 24 | **Every Agent Gets Its Own Clone** (`every_agent_gets_a_clone`) | 💾 VCS / 💥 Fleet | Pairs with `host_owned_completion`                                        |
| 25 | **Token Scarcity** (`token_scarcity`)                | 🤖 Agent CLIs     | Strong theme, but overlaps `usage_limits_and_api_costs`                           |
| 26 | **Seven Harnesses, Seven Ideas About Waiting** (`adapters_normalize_harnesses`) | 🤖 Agent CLIs | Good engineering story; may be too deep for a launch post             |
| 27 | **The Terminal Isn't the Only Window** (`mobile_and_web`) | 🔮 Future     | In every outline you've written, but Future already has 5 records                 |
| 28 | **SASE Runs More Than My Code** (`more_than_code`)   | 🔍 How I use      | Personal and relatable; overlaps `bob_task_events`                                |
| 29 | **I Listen to My Research** (`i_listen_to_my_research`) | 🔍 How I use / 🔌 Plugins | Charming detail; small claim                                       |
| 30 | **From a LangGraph Loop to 17K Commits** (`origin_story`) | 🪝 Intro       | Strong, but depends on the open "why vs. that I left Google" decision             |
| 31 | **Agent Hijack** (`agent_hijack`)                    | 💥 Fleet          | Good to demo once it's fixed; for now it's a limitation                           |
| 32 | **The Vim-Mode Joke** (recover it)                   | 📜 Macros / 🏁 Close | It was lost when its annotation task closed; at least add it as a note         |

If you only add a few, add **#1–#12**. That gives every section at least one candidate
except 💥 Fleet and 🎬 Demos, which #13 and #14 cover. It also gives both "What is SASE?"
and "Turn < … < Tribe" the definitions their headings promise. Before seeding #3, read
the Omnigent post (in your library as dropped) and arXiv 2611.06946 (not in your
library), so the "meta-harness" claim matches how the term is used now. Also resolve
"AI broccoli" from your Google Keep note; I couldn't see its contents, so it isn't
ranked.

Library check: 3 of 6 candidates already in your library (1 finished).

---

## Sources

**In your vault and repos**

- `~/bob/sase_blog_zettel.md` and its 29 records.
- `~/bob/sase_blog.md`, `sase_blog_contents.md`, `sase_blog_drafts.md`,
  `sase_blog_annotations.md`, `sase_blog_0_legacy_notes.md`, `why_sase.md`,
  `sase_pre_blog.md`, `sase_post_blog.md`, `done/sase_blog_done.md`,
  `ref/notes/sase_blog_261116.md`, and the Wave 1–4 captures research (status
  *abandoned*).
- `~/bob/sase.md`, `sase_ideas.md`, `goog_tools.md`, and the Notes sections of about 15
  `sase_*` project notes.
- In the sase repo:
  - `docs/blog/posts/why-coding-agents-need-orchestration.md` and
    `structured-agentic-software-engineering.md`.
  - `docs/reference/automation/tools.md`.
  - `demos/tapes/` and `demos/out/last_generated_date.txt`.
  - The `decisions` web: `single-turn-agents`, `adapters-normalize-harnesses`,
    `corpus-before-mechanism`, `rust-core-required`, `gates-never-block`,
    `size-alias-effort-ladder`, `triage-annotates-does-not-change-exit-codes`,
    `global-install-is-human-only`, and `check-full-is-explicit`.
  - The `glossary` web.
  - `git log`.
- The research sidecar: report counts by month folder.
- `bob ref`: finished external references, and your comments on "How the Claude Code
  team does code review," "The Log is the Agent," and others.

**Web**

- [Databricks — Introducing Omnigent: A Meta-Harness to Combine, Control and Share Your Agents](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)
- [omnigent-ai/omnigent on GitHub](https://github.com/omnigent-ai/omnigent)
- [MarkTechPost — Databricks open sources Omnigent](https://www.marktechpost.com/2026/06/13/databricks-open-sources-omnigent-a-meta-harness-that-composes-governs-and-shares-ai-agents-across-claude-code-codex-and-pi/)
- [MindStudio — What is a meta harness](https://www.mindstudio.ai/blog/what-is-meta-harness-ai-agents-omniagent)
- [Towards AI — What is a meta-harness in AI](https://pub.towardsai.net/what-is-a-meta-harness-in-ai-2af40e788c2e)
- [Beyond the Agent Harness: Boundary Criteria for Software-Factory Orchestration — A Single-Operator Case Study (arXiv 2611.06946)](https://arxiv.org/pdf/2611.06946)
- [Harness Engineering: Anatomy, Architecture, and Evolution of Coding Agents (arXiv 2609.00006)](https://arxiv.org/pdf/2609.00006)
- [SuperagenticAI/metaharness on GitHub](https://github.com/SuperagenticAI/metaharness), a different "metaharness" project, listed to avoid confusion.
