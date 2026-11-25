# SASE blog zettel album: gap analysis and recommended new records

Researcher: mus (5-researcher swarm, independent report).
Date: 2026-11-25. Sources: `~/bob/sase_blog_zettel.md` + all 29 zettel
records, `~/bob/sase_blog.md` / `sase_blog_contents.md` / `sase_blog_drafts.md` /
`sase_blog_annotations.md`, related Bob project notes, SASE concept docs
(`docs/concepts/*`), SASE memory webs (`decisions:*`, `glossary:*`), and the
SASE source tree. No peer swarm report was consulted.

## What the album looks like today

29 records, all still 🌱 Seed. Coverage by `section`:

| Section | Count | Records |
|---|---|---|
| 🪝 intro | 1 | what_came_before |
| 🧱 what | 3 | recursive_sase_improvement, sase_is_many_abstractions, why_a_tui |
| 📜 macros | 4 | agent_control_flow, layers_of_prompt_management, model_alias_pools, the_prompt_composer |
| 🤖 the_agent_cli | 2 | agent_cli_installs_and_updates, usage_limits_and_api_costs |
| 🧠 memory | 2 | memory, skills_should_be_procedural_memories |
| 🔁 turn | 3 | finalizers, microsoft_ceo_..., multi_provider_swarms |
| 🚦 gate | **0** | — empty |
| 🎨 plan (artifacts) | 5 | artifact_links, audited_artifact_reads, bead_lifecycle, beads_and_birds, repos_vs_directories |
| 💾 project (VCS) | 2 | host_owned_completion, monorepo_tools_are_trending |
| 🛠️ tools | **0** | — empty |
| 💥 fleet | **0** | — empty |
| ⚙️ automation | **0** | — empty |
| 🔌 plugins | **0** | — empty |
| 🔍 how_i_use_sase | **0** | — empty |
| 🎬 demos | **0** | — empty |
| 🛑 not_ready | 2 | ai_slop, sase_is_too_complex |
| 🔮 future | 5 | bob_task_events, evals, files_not_tracked_by_a_vcs, goals, memory_and_docs_are_the_same |
| 🏁 close | **0** | — empty |

Eight of eighteen sections are completely empty. The empties are not random:
they are the sections covering SASE's most distinctive machinery (gates,
fleet, automation, tools-as-control-plane) and the personal/narrative frame
(how_i_use, demos, close) that a launch post needs to land. A reader who only
reads the existing 29 seeds would conclude SASE is prompts + artifacts +
vaporware, and would never meet the ideas Bryan's own notes return to most
often: gates that don't block, one TUI for a tailnet fleet, the scheduler and
its chops, ToolRuns, stitches, memory webs, and the "motion isn't progress"
self-deprecation that the draft intro already promises
(`sase_blog_contents.md`: "~17K commits, ~2.9M lines, ~1 user").

Method note: every recommendation below is grounded in at least two of (a) a
SASE memory web or glossary term, (b) a concept/reference doc, (c) a Bob note
in Bryan's own words. Section assignments follow the album's existing
`section:` enum; claims are drafted as one-claim seeds in first person to
match the album's "one claim per record, in my own voice" summary.

## Section-by-section gaps

- **gate (0 records).** The richest gap. `decisions:gates-never-block` ("a gate
  never blocks an agent; continuation is the gate shell's follow-up, never a
  wait"), `glossary:sase-gate` / `gate-turn` (durable command-backed decision
  bundle; notifications are only the transport projection; plan/epic-plan /
  question / launch / triage kinds plus custom), and Bryan's own
  `~/bob/sase_gate.md` notes ("plan notifications are just a special type of
  cmd notification; questions are just prompting for cmd inputs; gates are
  generative just-in-time interfaces" per `sase_completion.md`). The album has
  `finalizers` (turn) and `host_owned_completion` (project) but nothing on the
  decision machinery connecting them.
- **tools (0 records).** `glossary:tool-run` (durable machine-local record:
  owner, lifecycle, exit/signal, fingerprints; failed stages carry failure
  signatures + triage verdicts without changing the outcome),
  `decisions:guarded-recipes` (agents run guarded recipes only inside
  `sase tool run`), `decisions:receipts-prove-before-they-skip`, and
  `decisions:triage-annotates-does-not-change-exit-codes`. The album talks
  about agent CLIs but never about how SASE executes and records non-LLM work.
- **fleet (0 records).** `~/bob/sase_remote.md` (one TUI across tailnet
  machines; `%dispatch` + auto-dispatch; machine hoods as bead assignees;
  sharing prompt history/PIW completions with the fleet), tailnet memory
  (athena/apollo/mac), and `docs/concepts/agents.md` (each agent gets its own
  isolated workspace checkout). The `why_a_tui` record already justifies the
  TUI by "agents need access to local files across my fleet" — the fleet half
  of that sentence has no record.
- **automation (0 records).** `docs/concepts/automation.md` (scheduler →
  routines → autonomy profile or gate checkpoint; mentors; plan approvals),
  the retired outline's "AXE and Lumberjacks and Chops (oh my)", `glossary`
  terms (routine/lumberjack, chop, proc, oneshot vs service proc, sase
  monitor), and `sase_memory` notes. Nothing in the album explains what runs
  while Bryan sleeps.
- **plugins (0 records).** `decisions:plugin-commands` (plugins may mount
  top-level `sase <name>` commands), `glossary:required-plugin`, and the
  retired outline's "Pluggable VCS / LLM Provider / LSP" trio. The album's
  `monorepo_tools_are_trending` gestures at VCS-adjacent work; the
  pluggability story itself is absent.
- **how_i_use_sase (0), demos (0), close (0).** Narrative frame is missing.
  Candidates from Bryan's notes: Bob-as-issue-tracker (`#sase` tag → bug
  bead; `sase_post_blog.md`, `bob_task_events` seed), the prompt-stash
  screenshots (`sase_blog.md` notes, 20260802), Telegram/mobile as the fleet
  remote (`sase_post_blog.md`, telegram post in `docs/blog/posts/`), VHS
  tapes under `demos/tapes/` + "alternations allow for vibe evals", and the
  closing "motion isn't progress" / "no weasels; just work" lines from the
  retired outline and `sase_blog_contents.md` stats.
- **Thin sections worth one more record each.** intro has the journey but no
  hook device (two cancelled annotations — closet diagram, SWE-transformation
  timeline — are revivable, see §Non-recommendations); turn has swarms and
  finalizers but nothing defining Turn < Session < Clan < Tribe < Hoods
  (`sase_clans_and_tribes.md`, `docs/concepts/agents.md`); memory has the
  anti-AGENTS.md stance but nothing on webs/strands or per-invocation
  instruction bundles; the_agent_cli has installs and costs but nothing on
  provider parity/sub-agent presentation (`sase_post_blog.md`: "clear
  representation of provider-specific sub-agents"); project has completion and
  monorepos but nothing on stitches (`sase_completion.md`: short
  alphanumeric IDs, every turn ends finalizer → stitch → patch/PR).

## Ranked recommendations

Ordered by (empty section first) × (distinctiveness to SASE) × (launch-post
load-bearing). Each item: proposed title — section — draft claim — why.

1. **A gate never blocks an agent** — `gate` — "When my agent needs me, it
   doesn't wait — it dies and leaves a gate behind that knows how to continue
   without it." Fills the emptiest load-bearing section with SASE's most
   distinctive decision (`decisions:gates-never-block`, `glossary:gate-turn`).
   Directly contradicts what every agent-harness reader assumes gates do.
2. **Plans and questions are just gates** — `gate` — "Plan approvals,
   questions, launch confirmations, and custom commands are all the same
   object: a durable command-backed decision bundle; the notification is only
   its transport." From `~/bob/sase_gate.md` notes + `glossary:sase-gate`
   kinds. Turns three seemingly separate features into one abstraction, the
   album's favorite move (`sase_is_many_abstractions`).
3. **One TUI for the whole fleet** — `fleet` — "I run one SASE TUI that sees
   agents on every machine I own across my tailnet, instead of one terminal
   per machine." From `sase_remote.md` + tailnet memory. Pays off the fleet
   clause already inside `why_a_tui`.
4. **The scheduler and its lumberjacks** — `automation` — "Repeatable work in
   SASE is a routine run by a scheduler; a lumberjack does the chopping."
   From `docs/concepts/automation.md` + retired "AXE and Lumberjacks and
   Chops" outline + `glossary` routine/chop terms. Gives `not_ready`/`future`
   sections something to point at.
5. **ToolRuns, not exit codes** — `tools` — "Every command SASE runs leaves a
   durable ToolRun record — owner, lifecycle, fingerprints — and triage
   annotates failures without ever changing the outcome." From
   `glossary:tool-run`, `decisions:guarded-recipes`,
   `decisions:triage-annotates-does-not-change-exit-codes`. The correctness
   story the launch post needs before claiming scale.
6. **Monitors own the long tail** — `automation` — "Anything that outlives a
   turn — a long command, a gate follow-up, a retry — is owned by a monitor,
   not held by an agent." From `glossary:sase-monitor`, gate/monitor turns,
   `decisions:single-turn-agents`. Pairs with #1 to explain how single-turn
   agents compose into long-lived work.
7. **Dispatch, don't SSH** — `fleet` — "I never SSH to run agents elsewhere; I
   `%dispatch` to a machine hood and the bead's assignee is the machine, not
   the agent." From `sase_remote.md` (auto-dispatch, machine-hood assignees,
   per-machine runner config). Concrete, demoable, unlike #3's panorama.
8. **Every agent gets its own workspace** — `project` — "Each running agent
   works in its own ephemeral checkout, so parallel agents never share working
   files and nothing I didn't commit can leak between them." From
   `docs/concepts/agents.md` + ephemeral `sase_<N>` workspace convention.
   Strengthens the thinnest load-bearing section (VCS, 2 records).
9. **Stitches are the unit of agent work** — `project` — "Every agent turn is
   supposed to end the same way: finalizer → stitch → patch/PR, sidecars
   included." From `sase_completion.md` project notes. Connects `finalizers`
   (turn) and `host_owned_completion` (project) into the through-line the
   post's 'What is SASE' arc is missing.
10. **Memory webs, not a bigger AGENTS.md** — `memory` — "Durable context in
    SASE is a web of small strand files — core memory inlined every turn,
    reference memory read on demand — not one ever-longer instruction file."
    From `decisions:memory-webs`, `sase_memory_webs.md`, per-invocation
    instruction bundles. The constructive counterpart to the existing
    complaint-record `memory`.
11. **Plugins mount top-level commands** — `plugins` — "A plugin can add a
    first-class `sase <name>` command, and VCS providers and agent CLIs are
    plugins too." From `decisions:plugin-commands` + retired "Pluggable"
    outline. Single record suffices to open the section.
12. **Turn < Session < Clan < Tribe (and hoods)** — `turn` — "A turn is one
    provider invocation; sessions chain turns, and clans, tribes, and hoods
    organize the agents doing them — including the non-LLM members like gate
    shells." From `sase_clans_and_tribes.md`, `docs/concepts/agents.md`,
    `glossary:agent-*` terms. The section is literally named this and has no
    record saying it.
13. **Motion isn't progress** — `close` — "~17K commits and ~2.9M lines for
    ~1 user: SASE is a prototype gone wild, and this post is the receipt, not
    the victory lap." From `sase_blog_contents.md` stats + retired "no
    weasels; just work" close. Gives the conclusion its honest landing; pairs
    with `sase_is_too_complex` in `not_ready`.
14. **How I actually use SASE: Bob is my issue tracker** — `how_i_use_sase` —
    "Tagging a task `#sase` in Obsidian files a bug bead; evidence flows back
    as sub-bullets." From `sase_post_blog.md` + existing `bob_task_events`
    (future) seed, reframed as present-tense practice. Opens the section with
    the most personal workflow.
15. **Demos are tapes, not screenshots** — `demos` — "Every SASE demo is a VHS
    tape under `demos/tapes/` — replayable, captioned, and honest about what
    the TUI actually did." From `demos/tapes/` + `sase_memory/demos.md`. Opens
    the section and doubles as an evals-adjacent honesty signal ("vibe
    evals" via alternations, per `sase_blog.md` notes).
16. **Size aliases are portability** — `macros` — "Prompts name a size like
    `@large`, not a vendor's model, so the same macro runs on whatever
    provider is ready." From `decisions:size-alias-effort-ladder`,
    `docs/concepts/providers.md`. Completes the existing `model_alias_pools`
    record with the alias half of the story.
17. **Legends outlive epics; goals outlive legends** — `future` — "No goal
    milestones: legends group epics, and a goal can outlive all of them."
    From `sase_blog.md` notes + `decisions:goal-ledger`. Gives `goals`
    (future) the hierarchy it gestures at.
18. **Sub-agents aren't called that here** — `the_agent_cli` — "Provider CLIs
    have sub-agents; SASE needs its own honest representation of them instead
    of borrowing the word." From `sase_blog.md` notes ("the term 'sub-agent'
    doesn't cut it") + `sase_post_blog.md` provider-sub-agent task. Small,
    funny, in-voice — good texture for the CLI section.

Honorable mentions (next wave, not ranked): the Vim-mode joke and
`tmux_ai_window` annotations both show completed conversion tasks in
`sase_blog_annotations.md` but have no corresponding zettel files on disk —
verify whether they were folded into `the_prompt_composer` / `what_came_before`
before creating duplicates. The SWE-transformation timeline and closet-diagram
annotations were explicitly cancelled; revive only as intro-hook illustrations,
not standalone claims.

## Non-recommendations (deliberately excluded)

- Hub-note-vs-structure-note quote (cancelled annotation; author already
  judged it non-blog).
- `reads`/`snips` sidecar-repo speculation (superseded by the
  files-not-tracked-by-VCS record per the annotations project).
- Anything requiring `docs/`, `mkdocs*`, or link-target changes — out of scope
  for album seeds.
- Duplicating the five `future` records' claims into present-tense sections;
  where overlap exists (#14 vs `bob_task_events`) the recommendation above
  reframes rather than repeats.

## Suggested next step

Create one seed per ranked item #1–#15 (the eight empty sections all get ≥1
record, and `project`/`turn`/`memory`/`macros` get their missing keystone),
then run the drafts project's wave review
(`sase_blog_drafts.md`: Wave 1 → Wave 7) before drafting, since each wave
reread is the project's own mechanism for spawning follow-up records.
