# Filling `sase_blog_zettel`: Gap Analysis & Ranked Recommendations for New Records

> **Target album:** `~/bob/sase_blog_zettel.md` (audited 2026-11-25)  
> **Scope:** Independent audit of all 18 album sections and 29 existing seed records against current `sase` `HEAD`, SASE's 31 architectural decision records, and Bryan's Bob vault (`sase_blog.md`, `sase_blog_contents.md`, `sase_blog_annotations.md`, `sase_post_blog.md`, project notes, and annotated references).  
> **Vault policy:** Read-only audit — nothing in `~/bob` was modified.

---

## 1. Executive Summary & Current Album Audit

As of **2026-11-25**, `~/bob/sase_blog_zettel.md` holds **29 zettels** — all at `🌱 Seed` status (only `skills_should_be_procedural_memories.md` currently has a `## Draft` paragraph) — distributed across **18 required `section` buckets**.

Cross-checking the album against your Bob notes and SASE `HEAD` (**17,235 commits**, **~3.39M lines** of tracked Python and Rust in `sase` alone, **7 built-in agent CLIs**, **13 plugin entry-point groups**, **12 gate kinds**, and **31 decision records**) reveals three high-leverage structural gaps:

1. **Eight of 18 sections have zero records.** The empty sections aren't minor footnotes — they include five core SASE abstractions (`gate`, `tools`, `fleet`, `automation`, `plugins`) and all three high-payoff reader sections (`how_i_use_sase`, `demos`, `close`).
2. **Four populated sections are missing their load-bearing central thesis.**
   - `🤖 Agent CLIs` (`the_agent_cli`) covers auto-updates and usage bars, but never makes the foundational claim that **SASE wraps agent CLIs instead of raw model APIs** (or that adapters normalize harnesses and survive outages).
   - `🔁 Turn < Session < Clan < Tribe` (`turn`) covers finalizers, multi-provider swarms, and the Satya Nadella quote (which belongs in `the_agent_cli`), but never explains **single-turn agents** or the **Session / Clan / Hood / Tribe** hierarchy named in the section's own title.
   - `🎨 Artifacts` (`plan`) has five strong records on beads, links, audited reads, and sidecar repos, yet **zero records on Plans, Epics, and Plan Decisions** — the literal `plan` key's namesake.
   - `💾 VCS` (`project`) covers host-owned completion and monorepo tools, but omits **ephemeral numbered workspaces (`sase_<N>`)** and **audited `sase repo open`**, the daily foundation that lets parallel agents run safely across multi-repo checkouts.
3. **Several of SASE's most original, share-worthy inventions aren't captured anywhere yet.** Most notably: **mechanical anti-slop defenses** (`sase footprint` feature-usage census + mandatory sunset feature-flag removal beads with `FlagTriage` gates), **reviewed `/sase_sudo` gates** without passwordless root, **`sase tool` guarded recipes + failure-triage witnesses + inline-then-escalate prepared completion**, the **multi-provider `#research_swarm` → `sase-listen` podcast → Bob highlights → epic loop**, and the **honest post-mortem of deleting the Git agent-import leg** (`agents-sync-publish-only`).

### Section-by-Section Coverage Matrix (Before & After)

| # | `section` Key | Album Label | Now | Key Gap Today | + Tier 1 (1–14) | + Tier 2 (15–23) | + Tier 3 (24–30) |
|---|---|---|---:|---|---:|---:|---:|
| 1 | `intro` | 🪝 Intro | 1 | Adequate (`what_came_before` + lede in spine) | 1 | 1 | 1 |
| 2 | `what` | 🧱 What is SASE? | 3 | Missing "optimal experience", "No Mayor", Rust core split | 3 | 5 | 6 |
| 3 | `macros` | 📜 Prompt language (macros) | 4 | Strong (alternations/"vibe evals" can fold into Notes) | 4 | 4 | 4 |
| 4 | `the_agent_cli` | 🤖 Agent CLIs | 2 | **Missing core thesis** (wrap CLIs, not APIs; outage retries) | 3 | 4 | 4 |
| 5 | `memory` | 🧠 Memory | 2 | Missing memory webs, per-invocation bundles, corpus-first | 2 | 3 | 3 |
| 6 | `turn` | 🔁 Turn < Session < Clan < Tribe | 3 | **Missing core theses** (single-turn; taxonomy; hijack) | 5 | 5 | 6 |
| 7 | `gate` | 🚦 Gates | **0** | **EMPTY** (plan-mode generalization; non-blocking; sudo) | **2** | 3 | 3 |
| 8 | `plan` | 🎨 Artifacts | 5 | **Missing Plans/Epics/Plan Decisions** | 6 | 6 | 6 |
| 9 | `project` | 💾 VCS | 2 | **Missing ephemeral numbered workspaces** | 3 | 3 | 3 |
| 10 | `tools` | 🛠️ Tools | **0** | **EMPTY** (ToolRuns, guards, triage witnesses, escalation) | **1** | 3 | 3 |
| 11 | `fleet` | 💥 Fleet | **0** | **EMPTY** (Tailscale `%dispatch`; delete-import post-mortem) | **1** | 1 | 2 |
| 12 | `automation` | ⚙️ Services | **0** | **EMPTY** (deterministic jobs propose, scheduler launches) | **1** | 1 | 1 |
| 13 | `plugins` | 🔌 Plugins | **0** | **EMPTY** (13 seams + GitHub topic catalog; Telegram plugin) | **1** | 1 | 2 |
| 14 | `how_i_use_sase` | 🔍 How I use SASE | **0** | **EMPTY** (research→podcast loop; different types of tokens) | **1** | 2 | 2 |
| 15 | `demos` | 🎬 The Demos | **0** | **EMPTY** (fan-out GIF; gate→epic waves clip) | **1** | 1 | 2 |
| 16 | `not_ready` | 🛑 Why SASE is still NOT ready? | 2 | Missing mechanical anti-slop (`footprint`/flags) & ~1-user honesty | 2 | 3 | 4 |
| 17 | `future` | 🔮 Future Work | 5 | Well-stocked (5 seeds already) | 5 | 5 | 5 |
| 18 | `close` | 🏁 Conclusion | **0** | **EMPTY** ("I'm out of tokens" + `type:poll`; "No weasels; just work") | **1** | 1 | 2 |
| | **Total** | | **29** | **8 empty sections** | **43** (+14) | **52** (+23) | **59** (+30) |

---

## 2. Editorial Guardrail: Avoid Turning the Launch Post Into a 60-Section Manual

Your own prior post-mortem (`ref/chat/blog00_launch_post_review_consolidated.md`) flagged a real trap: a 5,400-word, 20-section wall of reference tables buries the narrative before the core argument lands. Likewise, `sase_blog_zettel_album_guide` reminds you that **an album is a workbench of candidate claims, not a commitment to ship every record** — `✅ Ready` means usable material, and `⏭️ Later` / `✂️ Cut` exist for a reason.

To keep the album manageable while giving you full coverage across every section, the 30 recommendations at the end of this report are split into three strict cut-lines:

- **Tier 1 — Essential Load-Bearing Additions (Ranks 1–14):** The minimum viable set. Adding just these 14 brings the album to **43 records with zero empty sections** and fills every missing central thesis in populated sections. If you only want one crisp capture session before moving to drafting, stop right at Rank 14.
- **Tier 2 — High-Leverage Differentiators & Hard-Won Lessons (Ranks 15–23):** The nine claims that make experienced engineers stop scrolling and share the post (anti-slop antibodies, token economics, "optimal experience", "No Mayor", inline-then-escalate monitors with zero-turn host completion, witness-based failure triage, `/sase_sudo`, harness normalization & outage retries, memory webs & corpus-before-mechanism).
- **Tier 3 — Strong Optional Additions & `Later` Candidates (Ranks 24–30):** Great standalone stories (deleting Git agent-import, Telegram as a zero-UI mobile plugin, Python cockpit / Rust engine room, agent hijack, "No Weasels; Just Work", ~1-user rough edges, a second demo zettel). Capture whichever ones spark immediate prose and park the rest as `⏭️ Later` or fold them into existing `## Notes`.

---

## 3. Section-by-Section Gap Analysis

### Empty Sections (All 8 Must Receive At Least One Record or Be Removed)

1. **`gate` (`🚦 Gates`) — 0 records.**  
   This is arguably SASE's deepest original abstraction after macros. Your own note in `sase_blog.md` nails the hook: *"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"* In SASE `HEAD`, **12 gate kinds** — `plan`, `epic_plan`, `question`, `launch`, `hitl`, `sudo`, `task_triage`, `bead_snooze`, `flag_triage`, `bead_stale_cleanup`, `plugins_required`, and `custom` — share one hash-verified, command-backed protocol rendered identically across TUI, Telegram, mobile, and CLI (`docs/reference/automation/notification-gates.md`). Combined with your `sase_completion.md` framing (*"generative just-in-time interfaces"*) and the `gates-never-block` + `handoffs-end-through-host-completion` decision records, this section easily supports two load-bearing claims plus `/sase_sudo` as a showstopping security proof point.

2. **`tools` (`🛠️ Tools`) — 0 records.**  
   Readers will initially assume "Tools" means MCP or LLM tool-calling. SASE's `sase tool` control plane is something far more interesting and practical: a **project-owned catalog of expensive local commands** (`just check`, `just check-full`, `just test` in `sase/sase.yml`) where guarded recipes refuse raw agent runs (`guarded-recipes`), every run records pre/post repo and toolchain fingerprints plus CPU/RSS/pytest-worker demand (`record-before-admit`), per-host `max_concurrent` caps stop parallel agents from OOMing your machine, failure triage classifies failures as `NEW` / `KNOWN` / `FLAKY` / `UNKNOWN` using independent witnesses without faking exit codes (`triage-annotates-does-not-change-exit-codes`), and inline runs nearing a provider CLI's sync ceiling detach cleanly into a monitor under the same ToolRun ID — culminating in **zero-model-turn prepared host completion** (`sase final prepare` + `sase monitor start -p verify -f <ref>`).

3. **`fleet` (`💥 Fleet`) — 0 records.**  
   `%dispatch:<alias>` over a private Tailscale Serve loopback gateway (`sase_gateway` + `sase_federation_worker`) is a genuine differentiator against both single-machine tools (Gas Town, raw CLIs) and cloud-only sandboxes (Omnigent on Modal/Daytona). Two killer beats live here: (a) **controlling your own personal multi-machine fleet (`athena`, `apollo`, MacBook) from one TUI** with explicit bootstrap credentials ("tailnet membership is not authorization") and portable-source preflight, and (b) **the hard-won lesson of deleting the Git agent-import leg** (`agents-sync-publish-only`), cleanly splitting live RPC fleet control from publish-only Git history.

4. **`automation` (`⚙️ Services`) — 0 records.**  
   SASE's background layer separates the **Service Host** (`sase service` via systemd/launchd) from the **Scheduler / AXE** (`sase scheduler`, 9 default routines ticking on 2s–1h intervals). The central claim — echoing your own Gas Town critique in `sase_blog_0_legacy_notes.md` — is **interweaving deterministic code with LLM calls**: cheap deterministic job scripts watch files (`fs` triggers), commit thresholds (`git.commits_since`), and external trackers (`external_issue_mirror`), emitting validated JSON `proposed_launches` that the scheduler guards (`inhibit_if`), deduplicates (`once_per`), fans out (`for_each`), and recovers across interruptions. Examples like `refresh_docs` (every 25 commits), `toobig_split`, and `bead_task_triage` make this immediately concrete.

5. **`plugins` (`🔌 Plugins`) — 0 records.**  
   SASE defines **13 Python entry-point groups** (`sase_vcs`, `sase_workspace`, `sase_llm`, `sase_macros`, `sase_config`, `sase_artifact_refs`, `sase_file_hooks`, `sase_finalizers`, `sase_task_types`, `sase_dispatch`, `sase_commands`, `sase_pager_history`, `sase_plugin_manifest`). Keeping `sase-github`, `sase-telegram`, `sase-nvim`, `sase-research-artifacts`, and `sase-listen` outside core proves the abstractions aren't GitHub- or TUI-locked — and treating GitHub's `topic:sase--plugin` tag as the live plugin catalog (`sase plugin list`) is a wonderfully pragmatic zero-infra trick. `sase-telegram` also deserves its own beat showing how a plugin acted as a zero-UI mobile client while motivating the native mobile gateway.

6. **`how_i_use_sase` (`🔍 How I use SASE`) — 0 records.**  
   For a "prototype gone wild (~1 user)" post, this is the section that turns skepticism into fascination. Two workflows stand out far above generic "I write features with agents" descriptions:
   - Your **5-provider `#research_swarm` → durable `@research` report → `sase-listen` private podcast MP3 → Bob PDF highlights → next epic** loop (a workflow almost no one else on earth runs end-to-end).
   - **"Different types of tokens"** (which you explicitly flagged in both `sase_blog.md` and `sase_launch_post_outline.md`): routing architecture/planning to `@xlarge`/`@large` multi-provider pools descending the effort ladder (`size-alias-effort-ladder`), cross-pollinating planner and coder models across labs (`claude_coder`, `codex_coder`), and spending cheaper/idle tokens on background routines.

7. **`demos` (`🎬 The Demos`) — 0 records.**  
   You already have **5 scripted VHS tapes** in `demos/tapes/` (including `sase_ace_multi_model_fanout.tape`, `sase_ace_agents_observability.tape`, `sase_ace_prompt_input.tape`, `sase_ace_prompt_history_stash.tape`, `sase_ace_prs_pipeline.tape`) plus standout screenshots in `~/tmp/screenshots/` and `~/bob/img/`. Each `demos` zettel should anchor one concrete visual proof to a sharp claim (starting with multi-model fan-out and a Plan Gate → Approved Epic → Parallel Waves walkthrough).

8. **`close` (`🏁 Conclusion`) — 0 records.**  
   You already have two memorable, deeply authentic closing beats sitting in `sase_blog.md` and `sase_launch_post_outline.md`: **`"I need your help. I'm out of tokens."`** (paired with `type:poll` GitHub issues) and **`"No weasels; just work."`** (your signature sign-off, kept generous toward Steve Yegge/Gas Town). Both deserve their own seeds so the ending lands with real warmth and clarity.

### Load-Bearing Gaps in Populated Sections

- **`the_agent_cli` (currently 2 records):** Has `agent_cli_installs_and_updates` and `usage_limits_and_api_costs`, but lacks the foundational *"Wrap Agent CLIs, Not Model APIs"* claim and *"Adapters Normalize Harnesses — And Survive Provider Outages"* (which you marked *"Definitely mention this!"* in `sase_launch_post_outline.md`, with screenshot `~/tmp/screenshots/20260616_140429.png`).
- **`turn` (currently 3 records):** Has `finalizers`, `multi_provider_swarms`, and the misplaced Satya Nadella quote — missing BOTH *"Agents Are Single-Turn"* (`single-turn-agents` + `handoffs-end-through-host-completion`) and *"'Sub-Agent' Doesn't Cut It: Sessions, Clans, Hoods, and Tribes"* (your own `sase_blog.md` line 115!), plus `agent_hijack_and_recovery` as a standout UX win.
- **`plan` / `🎨 Artifacts` (currently 5 records):** Covers links, audited reads, beads, and repos-vs-directories, but completely skips **Plans, Epics, and Plan Decisions** (`docs/reference/work-units/plan-format.md`) — including the clever human-quote provenance verification (`requested` / `corrects`) for memory edits.
- **`project` / `💾 VCS` (currently 2 records):** Covers `host_owned_completion` and `monorepo_tools_are_trending`, but misses **Ephemeral Numbered Workspaces (`sase_<N>`) & Audited `sase repo open`** (`docs/reference/agents/workspaces.md`), the physical isolation layer beneath parallel agents and multi-repo changes.
- **`what` (currently 3 records):** Already strong (`recursive_sase_improvement`, `sase_is_many_abstractions`, `why_a_tui`), and gets dramatically sharper with your own *"Optimal Experience, Not Optimal Performance"* claim, *"No Mayor: Deterministic Plumbing Over Agent-Run Orchestration"* (Gas Town contrast), and *"Python for the Cockpit, Rust for the Engine Room"* (`rust-core-required`).
- **`memory` (currently 2 records):** `AGENTS.md Files are Not Enough` and `Skills should be Procedural Memories` are great hooks; adding *"Memory Webs, Per-Invocation Bundles, and No Retrieval Before Its Corpus"* shows what SASE actually built instead of vague RAG handwaving.
- **`not_ready` (currently 2 records):** `ai_slop` and `sase_is_too_complex` diagnose the disease; adding *"Fighting Slop Mechanically: Sunset Flags and `sase footprint`"* shows the actual cure you built (one of the coolest stories in the entire repo!), and *"Built for an Audience of One"* delivers the candid limitations list (`sase_blog.md` lines 91–92: Agents tab buggiest, security audit pending, ~1 user defaults).

---

## 4. Album Hygiene, Fold-Ins, and Deliberate Exclusions

### Quick Housekeeping Fixes on Existing Vault Files

1. **Re-home `microsoft_ceo_thinks_model_agnostic_architecture_is_good`:** Currently tagged `section: turn`, even though Satya Nadella's quote is about model-agnostic architecture owning your product. Moving it to `section: the_agent_cli` (or `section: what`) makes both sections cleaner.
2. **Sync `sase_blog_drafts.md`:** Does not yet include a draft task for `agent_cli_installs_and_updates` (created 2026-11-25) or waves for the 8 currently empty sections.
3. **Update stale numbers and headings in `sase_blog_contents.md`:** Still has the older 10-section outline and `~17K commits, ~2.9 million lines` — live `sase` `HEAD` is now **17,235 commits** and **~3.39M lines** of Python + Rust (in `sase` alone, excluding `sase-core` and plugins). Note that `sase_blog_contents.md`'s count of *"Claude, Codex, Muse, Grok, and three others"* (7 total: `agy`, `claude`, `codex`, `grok`, `muse`, `opencode`, `qwen`) is accurate.
4. **Decide `🎬 The Demos` placement at assembly time:** Creating 1–2 demo zettels now lets you script and polish the clips cleanly, but when pasting into `sase_blog_contents.md`, consider whether embedding each GIF inside its matching abstraction section (fan-out in `the_agent_cli`/`macros`, gate-to-epic in `gate`/`plan`) lands harder than clustering all media in a late `The Demos` section.

### Also Considered — Better Folded Into Existing `## Notes` or Parked as `⏭️ Later`

| Candidate Idea | Why Not Ranked in Top 30 | Better Home |
|---|---|---|
| **Patches & Stitches** (`patches.md`, `(2a)` proposals, hooks/mentors/comments, Scion "changesets" link) | `sase_blog.md ## Later Posts` already reserves a full deep-dive post for `ChangeSpec` / Patches. Explaining the full Patch schema in the intro post risks reference-table bloat. | Fold 2 sentences into `monorepo_tools_are_trending` or `host_owned_completion`, or add with `status: later`. |
| **Alternations as "Vibe Evals"** (`%{%m:opus \| %m:codex}`, screenshot `20260619_214831.png`) | `macros` already has 4 records. Alternations are a crisp paragraph rather than needing a 5th `macros` zettel right away. | Add to `agent_control_flow` or `layers_of_prompt_management` `## Notes` (promote only if it outgrows a paragraph). |
| **Mobile & Web Frontends** (`sase-android`, `sase_gateway`, artifact web browser) | `future` already has 5 seeds, and `## Later Posts` reserves `Mobile (and Web?)`. | Fold the native-app handoff into `telegram_as_mobile_plugin` (Rank 25) and `why_a_tui`, or park as `status: later`. |
| **Process & Cgroup Isolation** (systemd transient scopes, `OOMPolicy=continue`, code-swap lock, `agent_auto_restart`) | Great battle-tested plumbing, but operationally granular for an intro post. | Fold as proof bullets inside `scheduler_routines_and_jobs` (Rank 6) and `inline_then_escalate_monitors` (Rank 19). |
| **Cross-Artifact Decisions & Annotations** (`sase_art.md#^decisions`, `sase_post_blog.md:73`) | Natural closing beat for `plans_epics_and_plan_decisions` rather than duplicating `future`'s 5 seeds. | Fold as a forward-looking note on `plans_epics_and_plan_decisions` (Rank 10). |
| **Holds & Weighted Queues** (`%hold`, `%queue(w=..., capacity=...)`) | Niche control-flow detail for a launch post. | Fold a bullet into `agent_control_flow` `## Notes`. |

### Deliberately Excluded (Respecting Your Own Prior Decisions)

- **Cancelled in `sase_blog_annotations.md` (2026-11-22):** `finalizer_ideas` (`future`), `hub_note_vs_structure_note` (*"I don't think this needs to be in the blog, right?"*), `reads_and_snips` (superseded by `files_not_tracked_by_a_vcs`), `closet_diagram` and `swe_timeline` (illustrations/visual framing that belong in `## Notes`, not standalone claim zettels).
- **`AI broccoli` (`sase_blog.md:146`):** Still an unexpanded Google Keep reminder with no articulated claim yet; per `sase_blog_zettel_album_guide`, leave it out of the album until you state its one-sentence claim.

---

## 5. Sources Verified

- **Bob Vault (read-only):** `~/bob/sase_blog_zettel.md` and all 29 records in `~/bob/sase_blog_zettel/`; `~/bob/sase_blog.md`, `~/bob/sase_blog_contents.md`, `~/bob/sase_blog_drafts.md`, `~/bob/sase_blog_annotations.md`, `~/bob/sase_pre_blog.md`, `~/bob/sase_post_blog.md`, `~/bob/sase_blog_0_legacy_notes.md`, `~/bob/done/sase_blog_done.md`, `~/bob/sase.md`, `~/bob/sase_gate.md`, `~/bob/sase_art.md`, `~/bob/sase_completion.md`, `~/bob/sase_memory.md`, `~/bob/sase_goals.md`, `~/bob/sase_remote.md`, `~/bob/sase_better_plans.md`, `~/bob/sase_agent_recovery.md`, `~/bob/sase_toobig_symvision.md`.
- **Annotated Bob References:** `ref/notes/sase_blog_261116.md`, `ref/chat/sase_launch_post_outline.md`, `ref/chat/sase_launch_post_introduction.md`, `ref/chat/blog00_launch_post_review_consolidated.md`, `ref/chat/sase_blog_zettel_album_guide.md`, `ref/chat/sase_blog_zettel_section_schema.md`, `ref/chat/sase_blog_drafting_in_records.md`, `ref/blogs/introducing_omnigent_meta_harness_combine_control_and_share_your_agents.md`, `ref/blogs/the_ai_native_sdlc_playbook.md`, `ref/blogs/gas_town_emergency_user_manual.md`, `ref/blogs/redesigning_source_control.md`, `ref/blogs/solving_code_review_at_anthropic.md`, `ref/blogs/steve_kinney_agent_memory.md`, `ref/blogs/harness_for_rsi.md`, `ref/docs/gastown_readme.md`, `ref/papers/agentic_software_engineering.md`, `ref/papers/2026_goals_as_first_class_abstractions_in_human_ai_collaboration_automationxp26.md`.
- **SASE `HEAD` & Audited Memory:** `AGENTS.md` (31 decision records), `sase/sase.yml`, `sase memory read dispatch.md demos.md sase_flags.md`, `docs/reference/design-decisions.md`, `docs/reference/automation/{notification-gates,tools,monitors,scheduler,scheduler-default-routines,scheduler-jobs,sudo}.md`, `docs/reference/agents/{agent-sessions,agent-clans,agent-tribes,workspaces,hood-sync,agent-holds}.md`, `docs/reference/integrations/{plugins,remote-dispatch,mobile-gateway}.md`, `docs/reference/work-units/{plan-format,patches,goals}.md`, `docs/reference/providers/retry-and-fallback.md`, `docs/reference/memory/instruction-bundles.md`, `docs/reference/footprint.md`, `docs/reference/tui/machines-and-tools.md`, `demos/tapes/*.tape`, `docs/blog/posts/structured-agentic-software-engineering.md`.

---

## 6. Ranked List of Recommended New Records

### Quick-Scan Summary Table (Ranks 1–30)

| Rank | Tier | Section | Proposed Title (`stem`) | Core One-Sentence Claim (Shortened) |
|---:|---|---|---|---|
| **1** | T1 | 🚦 `gate` | Plan Mode Is Just One Kind of Gate (`plan_mode_is_a_gate`) | Plan mode is one instance of a deeper primitive: command-backed, hash-verified gates. |
| **2** | T1 | 🤖 `the_agent_cli` | Wrap Agent CLIs, Not Model APIs (`wrap_agent_clis_not_apis`) | Wrap existing coding CLIs to inherit lab velocity while owning the control plane above them. |
| **3** | T1 | 🔁 `turn` | Agents Are Single-Turn (`agents_are_single_turn`) | Every run is one turn; anything longer uses mechanical host continuation, never promises to resume. |
| **4** | T1 | 🔁 `turn` | "Sub-Agent" Doesn't Cut It (`turn_session_clan_tribe_taxonomy`) | "Sub-agent" collapses four distinct structures: sessions, clans, hoods, and tribes. |
| **5** | T1 | 🛠️ `tools` | Named Tools and Guarded ToolRuns (`named_tools_and_toolruns`) | Expensive commands need a guarded tool catalog with fingerprints, demand recording, and host concurrency caps. |
| **6** | T1 | ⚙️ `automation` | Deterministic Scripts Propose; The Scheduler Launches (`scheduler_routines_and_jobs`) | Cheap deterministic jobs watch repo/tracker state and emit launch proposals instead of always-on LLM loops. |
| **7** | T1 | 💥 `fleet` | One TUI Over a Private Tailscale Fleet (`tailnet_fleet_dispatch`) | `%dispatch:<machine>` runs your own multi-machine fleet over Tailscale from one TUI with explicit auth. |
| **8** | T1 | 🔌 `plugins` | Thirteen Seams and a GitHub-Topic Catalog (`pluggable_core_and_topic_catalog`) | Keep GitHub/Telegram/Neovim/commands out of core via entry points and `topic:sase--plugin` discovery. |
| **9** | T1 | 🔍 `how_i_use_sase` | Research Swarm → Podcast → Highlights → Epic (`research_swarm_to_podcast_loop`) | Fanning hard questions to 5 frontier labs, listening via `sase-listen`, and feeding highlights into epics. |
| **10** | T1 | 🎨 `plan` | Plans That Outlive the Chat (`plans_epics_and_plan_decisions`) | Version-controlled tales/epics with typed `decisions:` frontmatter stamped into archive and passed to coders. |
| **11** | T1 | 💾 `project` | Ephemeral Numbered Workspaces (`ephemeral_numbered_workspaces`) | Self-healing pooled `sase_<N>` clones with Git alternates, rescue snapshots, and audited `sase repo open`. |
| **12** | T1 | 🚦 `gate` | A Gate Never Blocks an Agent (`gates_never_block`) | Creating a gate stages the handoff and ends the LLM turn; a non-LLM `--gate` turn waits with zero slots. |
| **13** | T1 | 🎬 `demos` | Demo: Multi-Model Fan-Out (`demo_multi_model_fanout`) | One prompt fans out across competing frontier CLIs into isolated workspaces on one control screen. |
| **14** | T1 | 🏁 `close` | I Need Your Help — I'm Out of Tokens (`out_of_tokens_call_to_action`) | A ~1-user prototype opening its biggest design questions via `type:poll` GitHub issues to shape v2. |
| **15** | T2 | 🛑 `not_ready` | Fighting Slop Mechanically (`fighting_slop_mechanically`) | Sunset flag removal beads (`FlagTriage`), `toobig`/`symvision`, and `sase footprint` hunt down dead code. |
| **16** | T2 | 🔍 `how_i_use_sase` | Spending Different Types of Tokens (`different_types_of_tokens`) | Deliberate token tiers: effort-ladder pools, cross-lab planner/coder pairs, and idle-window routines. |
| **17** | T2 | 🧱 `what` | Optimal Experience, Not Optimal Performance (`optimal_experience_not_performance`) | SASE doesn't chase SWE-bench deltas; it optimizes the human experience of steering many agents at once. |
| **18** | T2 | 🧱 `what` | No Mayor: Deterministic Plumbing (`no_mayor_deterministic_plumbing`) | Push everything that *can* be deterministic into boring code (contrasting with Gas Town's LLM Mayor). |
| **19** | T2 | 🛠️ `tools` | Inline-Then-Escalate & Zero-Turn Completion (`inline_then_escalate_monitors`) | Runs nearing CLI timeouts detach into `--mon` monitors; green prepared checks commit with zero extra LLM turns. |
| **20** | T2 | 🛠️ `tools` | Triage Annotates; Never Changes Exit Codes (`failure_triage_witnesses`) | Witness-backed `NEW`/`KNOWN`/`FLAKY`/`UNKNOWN` triage lets agents skip known noise without faking green. |
| **21** | T2 | 🚦 `gate` | Reviewed Sudo Without Passwordless Root (`reviewed_sudo_gates`) | Hash-locked root command batches that refuse remote chat approval and authenticate via real `/dev/tty` PAM. |
| **22** | T2 | 🤖 `the_agent_cli` | Adapters Normalize Harnesses & Survive Outages (`adapter_normalization_and_outage_retries`) | Thin adapters enforce single-turn semantics and retry/fall back across outages without wiping workspaces. |
| **23** | T2 | 🧠 `memory` | Memory Webs & Corpus Before Mechanism (`memory_webs_and_corpus_first`) | Core notes + reference notes + keyword webs compiled per invocation; no RAG machinery ahead of a corpus. |
| **24** | T3 | 💥 `fleet` | Live Fleet Over RPC, History Over Git (`fleet_live_vs_publish_only_archive`) | Why I deleted Git agent-import: live control belongs on Rust RPC, Git sidecars should be publish-only. |
| **25** | T3 | 🔌 `plugins` | Telegram as a Zero-UI Mobile Frontend (`telegram_as_mobile_plugin`) | `sase-telegram` unlocked phone approvals early, proving transport-agnostic gates while motivating native mobile. |
| **26** | T3 | 🧱 `what` | Python Cockpit, Rust Engine Room (`rust_core_boundary`) | Shared deterministic domain logic lives in a required Rust core (`sase-core`) with zero Python fallback. |
| **27** | T3 | 🔁 `turn` | Agent Hijack & Recovery (`agent_hijack_and_recovery`) | Stop a meandering agent at a safe boundary without losing its edits; continue, escalate, or steer in place. |
| **28** | T3 | 🏁 `close` | No Weasels; Just Work (`no_weasels_just_work`) | After 17K commits, durable structure and honest human gates beat theatrical agent personas every time. |
| **29** | T3 | 🛑 `not_ready` | Built for an Audience of One (`audience_of_one_rough_edges`) | Candid rough edges: Agents tab buggiest, security audit pending, external contributor friction, Vim defaults. |
| **30** | T3 | 🎬 `demos` | Demo: Plan Gate → Epic → Parallel Waves (`demo_gate_to_epic_waves`) | Watching a plan with Plan Decisions expand into parallel waves makes the control plane click in 30 seconds. |

---

### Tier 1 — Essential Load-Bearing Additions (Ranks 1–14)

#### 1. Plan Mode Is Just One Kind of Gate
- **Stem:** `plan_mode_is_a_gate` · **Section:** `gate` (`🚦 Gates`) · **Why Tier 1:** Fills empty `gate` section with SASE's flagship insight.
- **Proposed `claim:`** Plan mode isn't a one-off feature — it's one instance of a deeper primitive: a command-backed, hash-verified gate that generalizes plans, questions, launch approvals, task triage, flag sunsets, and arbitrary agent-proposed actions into one generative just-in-time interface.
- **Why it earns a slot:** Directly pays off your own `sase_blog.md` quote (*"Plan mode is the canonical or best example of some deeper primitive. I know it. Interrupts?"*), shows the clean `(approve AND commit) OR reject OR feedback` boolean algebra, and unifies 12 real SASE gate kinds across TUI, Telegram, mobile, and CLI.
- **Evidence & `## Notes` seeds:** `sase_blog.md:100`, `sase_gate.md:39-42`, `sase_completion.md:44` (`^generative-jit-ux`), `docs/reference/automation/notification-gates.md:133-146`, and your CRP highlight in `ref/papers/agentic_software_engineering.md:44` (*"This is a LOT like gates!"*).

#### 2. Wrap Agent CLIs, Not Model APIs
- **Stem:** `wrap_agent_clis_not_apis` · **Section:** `the_agent_cli` (`🤖 Agent CLIs`) · **Why Tier 1:** Missing foundational thesis of `the_agent_cli`.
- **Proposed `claim:`** SASE wraps existing coding-agent CLIs (Claude Code, Codex, Antigravity, Grok, Muse, OpenCode, Qwen) instead of raw model APIs so you inherit every lab's auth, tools, and rapid harness progress while owning the durable control plane above them.
- **Why it earns a slot:** Right now `the_agent_cli` jumps straight to auto-updates and usage bars without telling readers *why* SASE is a meta-harness around CLIs rather than yet another API-calling agent loop. Honest trade-off paragraph (less control over token accounting/tool protocols, exposed to provider pricing/policy shifts) builds immediate credibility.
- **Evidence & `## Notes` seeds:** `docs/blog/posts/structured-agentic-software-engineering.md:74-124`, Matei Zaharia's Omnigent meta-harness highlight (`ref/blogs/introducing_omnigent_meta_harness_combine_control_and_share_your_agents.md:34,73`), and re-homed `microsoft_ceo_thinks_model_agnostic_architecture_is_good`.

#### 3. Agents Are Single-Turn
- **Stem:** `agents_are_single_turn` · **Section:** `turn` (`🔁 Turn < Session < Clan < Tribe`) · **Why Tier 1:** Missing foundational invariant behind turns, finalizers, gates, and monitors.
- **Proposed `claim:`** A SASE agent run is strictly one provider turn; anything that outlives a turn — waiting on a human, running a slow verification suite, or handing off to another model — happens through mechanical host continuation rather than trusting an agent to wait, sleep, or resume itself.
- **Why it earns a slot:** Without this invariant, `finalizers`, `gates`, and `monitors` look like arbitrary complexity. With it, the entire turn lifecycle clicks into place: staged handoffs settle through `/sase_final`, the host adopts the handoff, and native helpers simply return to their root.
- **Evidence & `## Notes` seeds:** Decision Records `single-turn-agents`, `handoffs-end-through-host-completion`, and `helpers-return-roots-declare` (`docs/reference/design-decisions.md`).

#### 4. "Sub-Agent" Doesn't Cut It: Sessions, Clans, Hoods, and Tribes
- **Stem:** `turn_session_clan_tribe_taxonomy` · **Section:** `turn` (`🔁 Turn < Session < Clan < Tribe`) · **Why Tier 1:** Explains the section's literal title and your own `sase_blog.md` thesis.
- **Proposed `claim:`** Calling every spawned agent a "sub-agent" collapses four distinct relationships: sequential chains (sessions), parallel groups (clans), shared-namespace lineage (hoods), and cross-cutting organizational labels (tribes).
- **Why it earns a slot:** Directly turns your `sase_blog.md:115` note (*"The term 'sub-agent' doesn't cut it when referring to agents that other agents run!"*) into the backbone of the `turn` section. Contrast the TUI ergonomics (`%wait:<clan>`, `#fork:<session>`, `@tribe` split panels, per-member model lanes) with flat terminal tabs or undifferentiated subagent lists.
- **Evidence & `## Notes` seeds:** `sase_blog.md:115`, `docs/reference/agents/{agent-sessions,agent-clans,agent-tribes}.md`, plus your Gas Town mapping note (Convoys/Crew vs Clans/Sessions/Tribes).

#### 5. Expensive Commands Are Named Tools, Not Ambient Shell Calls
- **Stem:** `named_tools_and_toolruns` · **Section:** `tools` (`🛠️ Tools`) · **Why Tier 1:** Fills empty `tools` section and disambiguates SASE Tools from MCP.
- **Proposed `claim:`** When ten agents run `just check` on the same workstation, shell commands stop being cheap side effects — they need a project-owned tool catalog that guards raw agent runs, records pre/post fingerprints and resource demand, and caps host-wide concurrency.
- **Why it earns a slot:** Immediately surprises readers who expect another MCP section. Shows real multi-agent systems engineering: `tools:` in `sase/sase.yml`, `tools/require_tool_run` refusing raw agent calls by habit (`guarded-recipes`), `record-before-admit`, `max_concurrent` FIFO admission slots, and `receipts-prove-before-they-skip`.
- **Evidence & `## Notes` seeds:** `docs/reference/automation/tools.md`, `sase/sase.yml:154-289`, Decision Records `record-before-admit`, `guarded-recipes`, `explicit-handoff-fails-closed`, `receipts-prove-before-they-skip`.

#### 6. Deterministic Scripts Propose; The Scheduler Launches
- **Stem:** `scheduler_routines_and_jobs` · **Section:** `automation` (`⚙️ Services`) · **Why Tier 1:** Fills empty `automation` section with SASE's clearest architectural contrast.
- **Proposed `claim:`** Background agent automation shouldn't be an always-on LLM burning tokens in a loop; in SASE, cheap deterministic job scripts watch files, commits, and trackers and emit structured launch proposals that the scheduler guards, deduplicates, and dispatches.
- **Why it earns a slot:** Captures the essence of the Service Host + Scheduler (AXE) + Routines + Jobs without drowning readers in config syntax. Concrete examples (`refresh_docs` every 25 commits, `toobig_split`, `bead_task_triage`, `external_issue_mirror`, `ci_watch`) show automation paying rent every day.
- **Evidence & `## Notes` seeds:** `docs/reference/automation/{scheduler,scheduler-default-routines,scheduler-jobs}.md`, `sase_blog_0_legacy_notes.md:9,15-17`, Anthropic's "superfans" highlight (`ref/blogs/redesigning_source_control.md:139`).

#### 7. One TUI Over a Private Tailscale Fleet
- **Stem:** `tailnet_fleet_dispatch` · **Section:** `fleet` (`💥 Fleet`) · **Why Tier 1:** Fills empty `fleet` section with SASE's distinct local-first distributed model.
- **Proposed `claim:`** When one laptop isn't enough compute, `%dispatch:<machine>` lets one TUI launch, observe, fork, and answer gates across your own machines over Tailscale — using explicit single-use bootstrap credentials and portable-source preflight instead of cloud sandbox lock-in.
- **Why it earns a slot:** Shows a pragmatic third path between "everything on one laptop" and "pay a hosted sandbox cloud": loopback `sase_gateway` behind Tailscale Serve, "tailnet membership is not authorization", clean-pushed-HEAD source preflight, host chips on unified Agents rows, and remote attention handling.
- **Evidence & `## Notes` seeds:** `docs/reference/integrations/remote-dispatch.md`, `sase/memory/dispatch.md`, `docs/reference/tui/machines-and-tools.md`, `sase_remote.md`, Omnigent cloud-sandbox contrast (`ref/blogs/introducing_omnigent_...md:52`).

#### 8. Keep Core Neutral: Thirteen Plugin Seams and a GitHub-Topic Catalog
- **Stem:** `pluggable_core_and_topic_catalog` · **Section:** `plugins` (`🔌 Plugins`) · **Why Tier 1:** Fills empty `plugins` section with two crisp architectural hooks.
- **Proposed `claim:`** SASE keeps GitHub, Telegram, Neovim, research workflows, and even top-level subcommands out of core through thirteen Python entry-point seams — and skips maintaining a central plugin registry by treating GitHub's `sase--plugin` topic as the live catalog.
- **Why it earns a slot:** Proves the architecture isn't coupled to GitHub (a deliberate choice shaped by Google's Piper/fig world!), showcases the real ecosystem (`sase-github`, `sase-telegram`, `sase-nvim`, `sase-research-artifacts`, `sase-listen` via `sase_commands`, `sase-spotify`), and highlights the scrappy `topic:sase--plugin` discovery + `plugins.required` install gates.
- **Evidence & `## Notes` seeds:** `docs/reference/integrations/plugins.md`, Decision Record `plugin-commands`, `sase/sase.yml:68-71`.

#### 9. The Research Swarm → Podcast → Highlights → Epic Loop
- **Stem:** `research_swarm_to_podcast_loop` · **Section:** `how_i_use_sase` (`🔍 How I use SASE`) · **Why Tier 1:** Fills empty `how_i_use_sase` section with your single most memorable real-world workflow.
- **Proposed `claim:`** My most unexpectedly valuable SASE workflow isn't writing code directly — it's fanning a hard question out to five competing frontier models, synthesizing one durable research report, turning it into a private podcast with `sase-listen`, and feeding my highlights straight into the next implementation plan.
- **Why it earns a slot:** Every reader will remember this workflow. In one tight story it ties together multi-provider clans (`#research_swarm`), durable `@research` artifacts, command plugins (`sase listen`), Bob/Obsidian annotations, and epic planning — proving SASE solves real cognitive bottlenecks, not just boilerplate coding.
- **Evidence & `## Notes` seeds:** `sase-research-artifacts`, `sase-listen`, `sase_blog_annotations.md`, `ref/chat/*.md` + `lib/chat/*.mp3` examples in Bob.

#### 10. Plans That Outlive the Chat — With Structured Plan Decisions
- **Stem:** `plans_epics_and_plan_decisions` · **Section:** `plan` (`🎨 Artifacts`) · **Why Tier 1:** Supplies the missing centerpiece of the `plan` section.
- **Proposed `claim:`** A plan trapped in a chat transcript disappears the moment the session closes; SASE turns plans into schema-validated, version-controlled Markdown artifacts (single-agent tales and multi-phase epics) with typed `decisions:` frontmatter whose human answers are stamped into the archive and handed mechanically to coders.
- **Why it earns a slot:** Right now `plan` talks around plans (links, audited reads, beads, repos-vs-directories) without explaining SASE plans themselves. Plan Decisions — including quote-verified `requested` / `corrects` provenance before an agent can edit project memory — are a standout design feature worth spotlighting (plus a nod to generalizing decisions to all artifact types).
- **Evidence & `## Notes` seeds:** `docs/reference/work-units/plan-format.md`, `sase_blog.md:141-143` (`img/20260824_141701.png` — agent reading 4 related plans), `ref/blogs/the_ai_native_sdlc_playbook.md:57,113`, `sase_art.md:28` (`^decisions`).

#### 11. Ephemeral Numbered Workspaces and Audited Repo Opens
- **Stem:** `ephemeral_numbered_workspaces` · **Section:** `project` (`💾 VCS`) · **Why Tier 1:** Missing foundational VCS isolation layer beneath parallel agents.
- **Proposed `claim:`** Parallel agents collide in a shared working tree and leak state across runs; SASE isolates every run in a pooled, self-healing numbered clone (`sase_10`, `sase_11`, …) backed by Git alternates, verified rescue snapshots before eviction, and audited `sase repo open` for linked and external repos.
- **Why it earns a slot:** Upgrades the "Boris Cherny manual git worktrees" baseline into an engineered pool: XDG-state layout (keeping `rg`/IDE searches fast), shared Git objects via alternates, self-healing dirty/rebased checkouts, fail-closed rescue snapshots so work is never silently clobbered, and one audited path for multi-repo work (`sase` + `sase-core` + GitHub external repos).
- **Evidence & `## Notes` seeds:** `docs/reference/agents/workspaces.md`, `AGENTS.md` §1.1.2 & §1.1.3.

#### 12. A Gate Never Blocks an Agent
- **Stem:** `gates_never_block` · **Section:** `gate` (`🚦 Gates`) · **Why Tier 1:** Essential architectural partner to Rank 1 that connects `gate`, `turn`, and `automation`.
- **Proposed `claim:`** Waiting on a human should never hold an LLM process or a runner slot open; in SASE, creating a gate stages the handoff, ends the turn cleanly through `/sase_final`, and becomes a non-LLM gate turn (`--gate`) that survives hours of async review before launching a successor.
- **Why it earns a slot:** Explains *why* SASE's gate UX feels fundamentally different from interactive CLI prompts: you can close your laptop, answer from Telegram three hours later, or survive a crash/failed gate command (with `resume`/`restart`/`cancel` recovery) without a hung agent process or wasted runner slot.
- **Evidence & `## Notes` seeds:** Decision Records `gates-never-block` & `handoffs-end-through-host-completion`, `docs/reference/automation/notification-gates.md:167-353`.

#### 13. Demo: One Prompt Fans Out Across Competing Frontier CLIs
- **Stem:** `demo_multi_model_fanout` · **Section:** `demos` (`🎬 The Demos`) · **Why Tier 1:** Fills empty `demos` section with proof assets you already recorded.
- **Proposed `claim:`** One prompt using alternations launches competing frontier CLIs into isolated workspaces, tracks them on one screen with live status and model badges, and lets you inspect, compare, or stop them together.
- **Why it earns a slot:** Gives skeptical readers visual proof in 15 seconds using assets already in the repo (`sase_ace_multi_model_fanout.tape` / `.gif`, `sase_ace_agents_observability.tape`, `~/tmp/screenshots/20260619_214831.png`). Works either inside `The Demos` or embedded inline at assembly time.
- **Evidence & `## Notes` seeds:** `demos/tapes/sase_ace_multi_model_fanout.tape`, `docs/images/blog/sase_ace_multi_model_fanout.gif`, `sase_blog.md:101`.

#### 14. I Need Your Help — I'm Out of Tokens
- **Stem:** `out_of_tokens_call_to_action` · **Section:** `close` (`🏁 Conclusion`) · **Why Tier 1:** Fills empty `close` section with your strongest, most human open-source CTA.
- **Proposed `claim:`** SASE is a ~1-user prototype that has already pushed past what one person's time and token budget can evaluate alone — so I'm opening its biggest design questions as `type:poll` GitHub issues and inviting people to break it, steal the ideas, or help shape v2.
- **Why it earns a slot:** Turns your own line from `sase_blog.md:132` (*"I need your help. I'm out of tokens."*) + `type:poll` issues into a funny, disarmingly honest closer that invites real community engagement without hype.
- **Evidence & `## Notes` seeds:** `sase_blog.md:132-133`, `ref/chat/sase_launch_post_outline.md:138` (*"Comment: Yes!"*).

---

### Tier 2 — High-Leverage Differentiators & Hard-Won Lessons (Ranks 15–23)

#### 15. Fighting Slop Mechanically: Sunset Flags and `sase footprint`
- **Stem:** `fighting_slop_mechanically` · **Section:** `not_ready` (`🛑 Why SASE is still NOT ready?`)
- **Proposed `claim:`** Noticing AI slop isn't enough to remove it — SASE had to build mechanical antibodies against its own bloat: mandatory sunset feature-flag beads whose `FlagTriage` gates force dead compatibility branches out of the tree, `toobig`/`symvision` structural checks, and `sase footprint`, a local privacy-preserving usage census that hunts down features even I stopped using.
- **Why it earns a slot:** Elevates `not_ready` from mere confession into one of the most original software-engineering lessons in the post. Almost everyone writing about vibe-coding bloat stops at "be more disciplined"; you actually built a local feature census (`map`, `cold`, `fading`, `agent-only`, `dead-paths`, `friction` → `#footprint_review` deletion beads) and typed flag-removal gates (`sase flag new`, date + release thresholds).
- **Evidence & `## Notes` seeds:** `docs/reference/footprint.md`, `sase/memory/sase_flags.md`, `sase/sase.yml:73-147`, `sase_toobig_symvision.md`, `sase_blog_zettel/ai_slop.md`.

#### 16. Spending Different Types of Tokens Deliberately
- **Stem:** `different_types_of_tokens` · **Section:** `how_i_use_sase` (`🔍 How I use SASE`)
- **Proposed `claim:`** Not all tokens are equal: I route deep design and planning to `@xlarge`/`@large` multi-provider pools descending the effort ladder, pair planners from one lab with coders from another, and burn cheaper or idle-window tokens on background maintenance routines like `refresh_docs` and `toobig_split`.
- **Why it earns a slot:** Explicitly flagged by you in `sase_blog.md:116` and annotated in `sase_launch_post_outline.md:79-84` (*"cleanup (routines) / plan/code / size model aliases?"*). Connects `model_alias_pools`, `usage_limits_and_api_costs`, `size-alias-effort-ladder`, and your Gas Town "Crew = `@large`/`@xlarge` + plans" realization (`gas_town_emergency_user_manual.md:76`).
- **Evidence & `## Notes` seeds:** `sase_blog.md:116`, `ref/chat/sase_launch_post_outline.md:79-84`, Decision Record `size-alias-effort-ladder`, `ref/blogs/gas_town_emergency_user_manual.md:76`.

#### 17. Optimal Experience, Not Optimal Performance
- **Stem:** `optimal_experience_not_performance` · **Section:** `what` (`🧱 What is SASE?`)
- **Proposed `claim:`** SASE doesn't claim to beat raw coding CLIs on SWE-bench; it optimizes the developer experience of steering, auditing, and composing many agents at once so you stay in control instead of babysitting terminal tabs.
- **Why it earns a slot:** Your single best framing inoculation against benchmark skepticism. Sets honest expectations right up front in `What is SASE?` and links back to the "pride / taking back control" opening.
- **Evidence & `## Notes` seeds:** `sase_blog.md:114`, `done/sase_blog_done.md:165`.

#### 18. No Mayor: Deterministic Plumbing Over Agent-Run Orchestration
- **Stem:** `no_mayor_deterministic_plumbing` · **Section:** `what` (`🧱 What is SASE?`)
- **Proposed `claim:`** Unlike orchestrators that put an LLM "Mayor" in charge of dispatching everything (Gas Town), SASE pushes every piece of coordination that *can* be deterministic — waits, queues, gates, finalizers, job triggers, and workspace claims — into boring code, reserving LLMs strictly for judgment and creation.
- **Why it earns a slot:** Gives SASE an instant, razor-sharp contrast against the best-known rival in readers' heads (Steve Yegge's Gas Town) while also weaving in your *"loop engineering vs. graph engineering"* note (`sase_blog.md:138`).
- **Evidence & `## Notes` seeds:** `sase_blog.md:90,138,162`, `sase_blog_0_legacy_notes.md:9`, `ref/docs/gastown_readme.md`, `ref/blogs/gas_town_emergency_user_manual.md`.

#### 19. Inline-Then-Escalate: Monitors and Zero-Model-Turn Prepared Completion
- **Stem:** `inline_then_escalate_monitors` · **Section:** `tools` (`🛠️ Tools`) *(bridges `tools` and `automation`)*
- **Proposed `claim:`** When a `sase tool run` approaches a provider CLI's synchronous kill ceiling, SASE detaches it under the same ToolRun ID into a non-LLM monitor turn (`--mon`) — and with prepared host completion (`sase final prepare`), a passing verification commits and closes the bead with zero extra LLM turns.
- **Why it earns a slot:** Solves two universal coding-agent annoyances in one clean mechanism: long test suites getting SIGKILLed by CLI timeouts, and paying for a whole extra frontier-model turn just to read "all tests passed" and run `git commit`.
- **Evidence & `## Notes` seeds:** `docs/reference/automation/tools.md:252-408`, `docs/reference/automation/monitors.md:13-44,312-395`, Decision Record `receipts-prove-before-they-skip`.

#### 20. Triage Annotates; It Never Changes an Exit Code
- **Stem:** `failure_triage_witnesses` · **Section:** `tools` (`🛠️ Tools`)
- **Proposed `claim:`** When ten agents share a fast-moving repo, a single pre-existing or flaky failure derails every run unless the tool plane tracks durable failure signatures with independent witnesses (`NEW`, `KNOWN`, `FLAKY`, `UNKNOWN`) — letting agents continue past known noise without ever faking a green exit code.
- **Why it earns a slot:** One of SASE's crispest engineering invariants (`triage-annotates-does-not-change-exit-codes`), directly paralleling Anthropic's "Pre-existing vs Important" review tags (`solving_code_review_at_anthropic.md:95`) and CI-strain writeup (`agentic_coding_is_straining_ci`).
- **Evidence & `## Notes` seeds:** Decision Record `triage-annotates-does-not-change-exit-codes`, `docs/reference/automation/tools.md:223-251`, `docs/reference/automation/monitors.md:594-600`, `sase/sase.yml:204-206` (`accept: [pass, no_new_failures]`).

#### 21. Reviewed Sudo Without Passwordless Root
- **Stem:** `reviewed_sudo_gates` · **Section:** `gate` (`🚦 Gates`)
- **Proposed `claim:`** Instead of handing coding agents passwordless `sudo` or banning privileged tasks entirely, `/sase_sudo` lets an agent propose a hash-locked batch of exact commands as a gate that refuses Telegram and mobile approval and requires a human at a real `/dev/tty` to authenticate through PAM.
- **Why it earns a slot:** Concrete, security-savvy, and immediately impressive to systems engineers. Rejects shells/`-c`/env-loader injection, snapshots executable SHA-256 on the target host (local or remote SSH), invalidates the sudo timestamp immediately afterward, and hands a redacted execution ledger to the successor turn.
- **Evidence & `## Notes` seeds:** `docs/reference/automation/sudo.md`, `sase.md:389-393` (`^sase-script`).

#### 22. Adapters Normalize Harnesses — And Survive Provider Outages
- **Stem:** `adapter_normalization_and_outage_retries` · **Section:** `the_agent_cli` (`🤖 Agent CLIs`)
- **Proposed `claim:`** Every agent CLI has different background primitives, sync ceilings, and cryptic failure modes; SASE's thin provider adapters enforce the single-turn contract, deliver frozen instruction bundles, and automatically retry or fall back through provider outages without wiping your workspace.
- **Why it earns a slot:** Pays off your explicit highlight in `sase_launch_post_outline.md:87-91` (*"retries through a provider outage — Comment: Definitely mention this!"*) with real proof (`~/tmp/screenshots/20260616_140429.png` surviving a <30m Claude outage) and explains the real engineering behind `adapters-normalize-harnesses`.
- **Evidence & `## Notes` seeds:** Decision Record `adapters-normalize-harnesses`, `docs/reference/providers/retry-and-fallback.md`, `sase_blog.md:173`, `ref/chat/sase_launch_post_outline.md:87-95`.

#### 23. Memory Webs, Per-Invocation Bundles, and No Retrieval Before Its Corpus
- **Stem:** `memory_webs_and_corpus_first` · **Section:** `memory` (`🧠 Memory`)
- **Proposed `claim:`** Rather than bolting vector RAG onto an empty folder or stuffing everything into one sprawling `AGENTS.md`, SASE organizes knowledge into core notes, on-demand reference notes, and keyword-addressed memory webs (`glossary:`, `decisions:`) compiled into frozen per-invocation bundles — refusing fancy retrieval until a real corpus proves it needs it.
- **Why it earns a slot:** Gives concrete substance to `AGENTS.md Files are Not Enough`! Shows the disciplined, token-level engineering behind SASE memory (`corpus-before-mechanism`, authored `[[links]]`, provider-cap compaction for Codex/Grok, readable committed `AGENTS.md` projection) and echoes your Steve Kinney highlights (*"Start flat. Move to graphs or hierarchies only when you observe specific failures"*).
- **Evidence & `## Notes` seeds:** Decision Records `memory-webs`, `webs-render-in-their-own-section`, `memory-links-are-authored`, `instructions-per-invocation`, `readable-agents-md`, `corpus-before-mechanism`; `docs/reference/memory/instruction-bundles.md`; `ref/blogs/steve_kinney_agent_memory.md:64,78,173`.

---

### Tier 3 — Strong Optional Additions & `Later` Candidates (Ranks 24–30)

#### 24. Live Fleet Over RPC, History Over Git (Why I Deleted Agent Import)
- **Stem:** `fleet_live_vs_publish_only_archive` · **Section:** `fleet` (`💥 Fleet`)
- **Proposed `claim:`** I tried using Git sidecars to sync live agent state between machines and ended up deleting the entire import leg: live fleet control belongs on a lightweight Rust HTTP gateway, while the hidden `agents` sidecar works far better as a publish-only durable archive.
- **Why it earns a slot:** Readers deeply respect honest architecture deletions. Captures Decision Record `agents-sync-publish-only` and explains the clean split between `sase_gateway` (live fleet) and `sase--agents` (browsable commit/session/prompt archive with content-addressed `files/objects/sha256/`).
- **Evidence & `## Notes` seeds:** Decision Record `agents-sync-publish-only`, `docs/reference/agents/hood-sync.md`.

#### 25. Telegram as a Zero-UI Mobile Frontend (And Why a Native App Still Matters)
- **Stem:** `telegram_as_mobile_plugin` · **Section:** `plugins` (`🔌 Plugins`)
- **Proposed `claim:`** Shipping `sase-telegram` as a plugin let me approve plans, answer questions, and launch agents from my phone months before building a native app — proving transport-agnostic gates work even as chat UI hits its limits.
- **Why it earns a slot:** Concretizes the plugin story with your favorite daily mobile integration while naturally setting up the Rust `sase_gateway` + `sase-android` native mobile direction (matching `sase_blog_0_legacy_notes.md:29-30`).
- **Evidence & `## Notes` seeds:** `docs/reference/integrations/{plugins,mobile-gateway}.md`, `docs/blog/posts/telegram-mobile-agents.md`, `sase_blog_0_legacy_notes.md:29-30`.

#### 26. Python for the Cockpit, Rust for the Engine Room
- **Stem:** `rust_core_boundary` · **Section:** `what` (`🧱 What is SASE?`)
- **Proposed `claim:`** Every frontend — the TUI, CLI, Macro LSP, mobile gateway, and future web app — needs identical domain behavior, so SASE pushes shared deterministic logic into a required Rust core (`sase-core`) with zero Python fallback while keeping UI and plugin glue in Python.
- **Why it earns a slot:** Paragraph 2 of `sase_blog_contents.md` explicitly calls out *"Python and Rust code"* — readers will immediately wonder why both languages exist. This one crisp record answers that question cleanly via `rust-core-required` and the litmus test from `AGENTS.md` §1.3.
- **Evidence & `## Notes` seeds:** Decision Record `rust-core-required`, `AGENTS.md` §1.3, `docs/contribute/rust-backend.md`.

#### 27. Agent Hijack: Stop a Runaway Agent Without Throwing Away Its Work
- **Stem:** `agent_hijack_and_recovery` · **Section:** `turn` (`🔁 Turn < Session < Clan < Tribe`)
- **Proposed `claim:`** Stopping a meandering or stuck agent shouldn't throw away twenty minutes of good edits; SASE's hijack freezes the turn at a safe boundary (latching rather than corrupting an active finalizer), holds its numbered workspace, and lets you continue, escalate to a stronger model, or steer with a fresh instruction.
- **Why it earns a slot:** Immediately relatable to anyone who has pressed `Ctrl-C` on an agent at minute 18 and regretted it. The latching-during-finalization detail shows genuine craft.
- **Evidence & `## Notes` seeds:** `docs/reference/agents/agent-sessions.md:232-315`, `docs/reference/agents/workspaces.md:432-441`, `sase_agent_recovery.md`.

#### 28. No Weasels; Just Work
- **Stem:** `no_weasels_just_work` · **Section:** `close` (`🏁 Conclusion`)
- **Proposed `claim:`** After 17,000 commits of chasing the missing operating layer for coding agents, the lesson isn't that SASE is the final answer — it's that durable structure, deterministic plumbing, and honest human gates beat theatrical agent personas every time.
- **Why it earns a slot:** Ties the closing paragraph back to the opening lede ("pride", "prototype gone wild") and lands the sign-off line you already liked in `sase_launch_post_outline.md:144-146` (*"I like this as long as I am sufficiently kind to Steve Yegge"*).
- **Evidence & `## Notes` seeds:** `sase_blog_0_legacy_notes.md:34`, `ref/chat/sase_launch_post_outline.md:144-148`.

#### 29. Built for an Audience of One (Rough Edges and Honest Limits)
- **Stem:** `audience_of_one_rough_edges` · **Section:** `not_ready` (`🛑 Why SASE is still NOT ready?`)
- **Proposed `claim:`** At ~1 user, SASE's rough edges are real: the Agents tab is still the buggiest part of the TUI, a full security audit and external-contributor onboarding aren't done yet, and half the defaults reflect one opinionated Vim/Linux/Tailscale workflow.
- **Why it earns a slot:** Gives readers a candid "don't expect a polished SaaS product yet" warning — directly fulfilling `sase_blog.md:91-92` (*"Mention that the agents tab is the buggiest part of the TUI!"*, *"Create list of limitations!"*) and `sase_blog.md:135` (your Vim-mode joke!).
- **Evidence & `## Notes` seeds:** `sase_blog.md:91-92,135`, `sase_pre_blog.md:52`, `sase.md:468` (`^fork-sase`).

#### 30. Demo: Plan Gate → Approved Epic → Parallel Waves
- **Stem:** `demo_gate_to_epic_waves` · **Section:** `demos` (`🎬 The Demos`)
- **Proposed `claim:`** Watching an agent propose a plan with Plan Decisions, yield cleanly at a gate without holding a runner slot, and expand into parallel dependency waves on approval makes SASE's control plane click faster than ten paragraphs of prose.
- **Why it earns a slot:** Pairs with `demo_multi_model_fanout` (Rank 13) so the demos cover both SASE's multi-provider launch story *and* its async plan/gate/epic control loop.
- **Evidence & `## Notes` seeds:** `demos/tapes/sase_ace_agents_observability.tape`, `sase_blog.md:141-143` (`img/20260824_141701.png`), `sase.md:355-357` (`img/20261026_175732.png`), `ref/chat/sase_launch_post_outline.md:111`.

---

### Optional Starter: Dry-Run `bob capture` Batch for Tier 1 (Ranks 1–14)

Preview without writing; edit any claim into your exact voice and drop `--dry-run` only for the records you want:

```bash
bob capture --dry-run --no-clip <<'EOF'
Plan Mode Is Just One Kind of Gate @sase_blog_zettel/^plan_mode_is_a_gate
- status:: seed
- claim:: Plan mode isn't a one-off feature — it's one instance of a deeper primitive: a command-backed, hash-verified gate that generalizes plans, questions, launch approvals, task triage, flag sunsets, and arbitrary agent-proposed actions into one generative just-in-time interface.
- section:: gate

Wrap Agent CLIs, Not Model APIs @sase_blog_zettel/^wrap_agent_clis_not_apis
- status:: seed
- claim:: SASE wraps existing coding-agent CLIs (Claude Code, Codex, Antigravity, Grok, Muse, OpenCode, Qwen) instead of raw model APIs so you inherit every lab's auth, tools, and rapid harness progress while owning the durable control plane above them.
- section:: the_agent_cli

Agents Are Single-Turn @sase_blog_zettel/^agents_are_single_turn
- status:: seed
- claim:: A SASE agent run is strictly one provider turn; anything that outlives a turn — waiting on a human, running a slow verification suite, or handing off to another model — happens through mechanical host continuation rather than trusting an agent to wait, sleep, or resume itself.
- section:: turn

"Sub-Agent" Doesn't Cut It: Sessions, Clans, Hoods, and Tribes @sase_blog_zettel/^turn_session_clan_tribe_taxonomy
- status:: seed
- claim:: Calling every spawned agent a "sub-agent" collapses four distinct relationships: sequential chains (sessions), parallel groups (clans), shared-namespace lineage (hoods), and cross-cutting organizational labels (tribes).
- section:: turn

Expensive Commands Are Named Tools, Not Ambient Shell Calls @sase_blog_zettel/^named_tools_and_toolruns
- status:: seed
- claim:: When ten agents run `just check` on the same workstation, shell commands stop being cheap side effects — they need a project-owned tool catalog that guards raw agent runs, records pre/post fingerprints and resource demand, and caps host-wide concurrency.
- section:: tools

Deterministic Scripts Propose; The Scheduler Launches @sase_blog_zettel/^scheduler_routines_and_jobs
- status:: seed
- claim:: Background agent automation shouldn't be an always-on LLM burning tokens in a loop; in SASE, cheap deterministic job scripts watch files, commits, and trackers and emit structured launch proposals that the scheduler guards, deduplicates, and dispatches.
- section:: automation

One TUI Over a Private Tailscale Fleet @sase_blog_zettel/^tailnet_fleet_dispatch
- status:: seed
- claim:: When one laptop isn't enough compute, `%dispatch:<machine>` lets one TUI launch, observe, fork, and answer gates across your own machines over Tailscale — using explicit single-use bootstrap credentials and portable-source preflight instead of cloud sandbox lock-in.
- section:: fleet

Keep Core Neutral: Thirteen Plugin Seams and a GitHub-Topic Catalog @sase_blog_zettel/^pluggable_core_and_topic_catalog
- status:: seed
- claim:: SASE keeps GitHub, Telegram, Neovim, research workflows, and even top-level subcommands out of core through thirteen Python entry-point seams — and skips maintaining a central plugin registry by treating GitHub's `sase--plugin` topic as the live catalog.
- section:: plugins

The Research Swarm -> Podcast -> Highlights -> Epic Loop @sase_blog_zettel/^research_swarm_to_podcast_loop
- status:: seed
- claim:: My most unexpectedly valuable SASE workflow isn't writing code directly — it's fanning a hard question out to five competing frontier models, synthesizing one durable research report, turning it into a private podcast with `sase-listen`, and feeding my highlights straight into the next implementation plan.
- section:: how_i_use_sase

Plans That Outlive the Chat — With Structured Plan Decisions @sase_blog_zettel/^plans_epics_and_plan_decisions
- status:: seed
- claim:: A plan trapped in a chat transcript disappears the moment the session closes; SASE turns plans into schema-validated, version-controlled Markdown artifacts (single-agent tales and multi-phase epics) with typed `decisions:` frontmatter whose human answers are stamped into the archive and handed mechanically to coders.
- section:: plan

Ephemeral Numbered Workspaces and Audited Repo Opens @sase_blog_zettel/^ephemeral_numbered_workspaces
- status:: seed
- claim:: Parallel agents collide in a shared working tree and leak state across runs; SASE isolates every run in a pooled, self-healing numbered clone (`sase_10`, `sase_11`, ...) backed by Git alternates, verified rescue snapshots before eviction, and audited `sase repo open` for linked and external repos.
- section:: project

A Gate Never Blocks an Agent @sase_blog_zettel/^gates_never_block
- status:: seed
- claim:: Waiting on a human should never hold an LLM process or a runner slot open; in SASE, creating a gate stages the handoff, ends the turn cleanly through `/sase_final`, and becomes a non-LLM gate turn (`--gate`) that survives hours of async review before launching a successor.
- section:: gate

Demo: One Prompt Fans Out Across Competing Frontier CLIs @sase_blog_zettel/^demo_multi_model_fanout
- status:: seed
- claim:: One prompt using alternations launches competing frontier CLIs into isolated workspaces, tracks them on one screen with live status and model badges, and lets you inspect, compare, or stop them together.
- section:: demos

I Need Your Help — I'm Out of Tokens @sase_blog_zettel/^out_of_tokens_call_to_action
- status:: seed
- claim:: SASE is a ~1-user prototype that has already pushed past what one person's time and token budget can evaluate alone — so I'm opening its biggest design questions as `type:poll` GitHub issues and inviting people to break it, steal the ideas, or help shape v2.
- section:: close
EOF
```
