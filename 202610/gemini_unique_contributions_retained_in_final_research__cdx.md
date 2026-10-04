# Gemini contributions that survived research-swarm synthesis

Independent retrospective by `research.3l.cdx` · 2026-10-04

## Finding

**Yes. There are eight well-supported final reports in which a distinctive Gemini contribution was retained, plus five narrower or qualified cases.** The clearest examples are the Antigravity lifecycle investigation, dynamic agent tabs, and services hardening. Gemini added an experimentally grounded mechanism or a concrete interaction rule, rather than simply another vote for the eventual recommendation.

This is a file-level audit of the research sidecar as inventoried at the start of this investigation. It establishes differences between available researcher reports and what the final text retained. It does not establish which model first thought of a concept outside the swarm, prove that the lead learned it exclusively from Gemini, or show that a proposal was subsequently implemented.

## Method and scope

- Inventory every Markdown file whose name ends in `__gem.md`, across the opened research sidecar. The starting inventory contains **69 Gemini files** and **64 organized topic directories with final reports**. Five additional Gemini files sit at month-directory level. In total, the audited read corpus contains **361 distinct files**, including **81 final-text variants** across those 64 topics.
- Resolve and read source artifacts through `sase artifact read research:<actual-relative-path> "<audit reason>"`. Work from those audited full-text outputs, not direct reads of sidecar artifact files.
- Compare Gemini against **all available independent researcher reports in its topic directory**, including `__mus.md` when present. A later critique is not treated as an independent original researcher. Inspect both the topic's unsuffixed published report and its `__final.md` synthesis when both exist; count them as one topic, not two successes.
- Screen final attribution, disagreement resolutions, substantive retained claims, and distinctive wording. Use lexical overlap only to generate candidates; evaluate the candidate's meaning against the peer reports. An attribution table is not itself proof of uniqueness.
- Count a strong match when the Gemini report contains a substantive claim or design refinement absent in equivalent form from the available peer reports, and the final uses it constructively. Exclude shared recommendations, refuted claims, and proposals appearing only in a rejection table. Separately label a package-specific recipe, a tentative performance explanation, and an optional alternative.

The corpus and conclusions concern historical report content. I did not rerun the old experiments or check whether the historical defects still exist. This swarm's contemporaneous `__cld.md`, `__grk.md`, and `__gem.md` reports were not read, requested, or used. Discovery and reading used a frozen allowlist of historical files.

## Eight strong matches

### 1. Antigravity's hard command limit and an experimentally tested escape

**Final:** [agent_long_command_early_exits.md](../202609/agent_long_command_early_exits/agent_long_command_early_exits.md)  
**Gemini:** [agent_long_command_early_exits__gem.md](../202609/agent_long_command_early_exits/agent_long_command_early_exits__gem.md)  
**Peers checked:** `__cld.md`, `__mus.md` in the same directory.

Gemini connected three specific Antigravity mechanisms: `run_command` cannot wait synchronously beyond 10,000 ms; the tool response tells the agent to end its turn and expect notification; print mode instead waits roughly five seconds after idle, kills background tasks, and can exit successfully. This explains why a model can obey its harness and still abandon a long command. Gemini also reported a `sleep 12` experiment showing that continued tool activity keeps the turn alive long enough to receive completion.

The peers discuss single-turn mismatches, missing guards, and monitor churn, but do not supply this exact Antigravity tool-schema/lifecycle chain or the tested keep-alive escape. The final's verification table singles out Gemini's hard-limit/lifecycle claim and marks it **“Confirmed in the agy 1.2.7 binary.”** Its §2.2 retains the experiment: **“gem demonstrated the in-harness escape”**, followed by the explanation that continued status/output calls preserve the turn. This is constructive explanatory evidence in the final, not merely a citation to a rejected proposal.

Keep the credit narrow. The text-classifier blind spot is shared with Claude. The lead corrects Gemini's claim that widening the version allowlist alone would restore robust detection, and its claim about deleted uncommitted work. Those are not successes being credited here.

### 2. Keeping an emptied active tab from disappearing under the cursor

**Final:** [agents_dynamic_tabs.md](../202609/agents_dynamic_tabs/agents_dynamic_tabs.md)  
**Gemini:** [agents_dynamic_tabs__gem.md](../202609/agents_dynamic_tabs/agents_dynamic_tabs__gem.md)  
**Peers checked:** `__cdx.md`, `__cld.md`, `__grk.md`, `__mus.md`.

Gemini proposes **focus latching**: if the last agent leaves the tab currently being viewed, keep that tab and an honest empty state until the user deliberately navigates away. Only then may the tab be pruned and the strip hidden. This resolves the conflict between occupancy-derived tabs and stable navigation.

Claude explicitly proposes switching to the nearest surviving tab when the last agent leaves. Codex distinguishes query-empty from truly empty tabs, without the active-tab lifetime rule. Grok favors occupancy-derived pruning; Muse retains empty enrolled machine tabs under a different policy. Those are not equivalent to Gemini's rule for any currently selected tab.

The final adopts it verbatim in substance as **R11, “An emptied active tab stays put”**, explaining: **“The place you are standing does not vanish under the cursor (gem).”** This is a particularly clean unique-and-adopted design refinement.

### 3. The precise write-behind failure caused by single-turn completion

**Final:** [bead_speedup_daemon_vs_direct_path.md](../202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md)  
**Gemini:** [bead_speedup_daemon_vs_direct_path__gem.md](../202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path__gem.md)  
**Peers checked:** `__cld.md`, `__mus.md`.

Gemini articulates a specific failure sequence: a daemon acknowledges a bead mutation, the agent declares completion and exits, a later push fails, and the ephemeral workspace can be reclaimed while the mutation remains unpublished. Its §2.2 ties acknowledgement timing directly to the single-turn completion contract and workspace lifetime.

Both peers already discuss publication contracts, durability, daemon tradeoffs, and caches. Claude even sketches a never-evicted machine outbox. Therefore **the unique contribution is the explicit acknowledgement → agent exit → delayed failure/eviction argument**, not discovering the publication invariant or recommending a fast direct path.

The final makes that argument a numbered reason against a read/write RPC daemon: **“Write-behind breaks single-turn completion (gem).”** It spells out the delayed push failure after the agent has exited and cites the published-before-success contract. The final rejects Gemini's proposed `beads.db` cache location and corrects its latency estimates; those broader proposals are not counted.

### 4. Services hardening: a verified no-op and two specific refinements

**Final:** [sase_services_post_landing_hardening.md](../202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md)  
**Gemini:** [sase_services_post_landing_hardening__gem.md](../202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening__gem.md)  
**Peers checked:** `__cld.md`, `__mus.md`.

This final contains several retained Gemini contributions, counted together as one successful topic:

1. **`sase scheduler restart` is specifically a no-op.** Gemini traces `delay=0.0`: the stop marker is written and cleared before the asynchronous host can observe it. Its live probe reports an unchanged PID. The final's adjudication table states **“gem: yes, a live-verified no-op. cld and mus missed it”**, and confirms the code path. §3.4 retains the live finding and uses it to motivate reliable restart acknowledgement. Muse notices a broader fixed-delay restart race; that does not duplicate this zero-delay defect. The final uses Claude's restart generation as the repair, so Gemini receives credit for the diagnosis, not the chosen transport.
2. **A stubborn child can be duplicated after failed SIGKILL.** Gemini identifies `_stop_child()` dropping an unreaped child from `_children`, allowing another instance to launch in the same reconcile pass. The final labels it **real but rare**, explains the D-state limitation, cites **“gem Bug 9”**, and requires tracking the child until reaped. The peers discuss shutdown blocking, detached-child ownership, and grace periods, but not this specific forget-and-respawn sequence.
3. **Configurable environment capture.** Gemini goes beyond the peers' existing environment/staleness concerns by proposing an explicit configurable capture list for proxies, CA bundles, and locale variables. §3.6 calls Gemini's `service.capture_env_names` the **“general form of this fix”** and notes the required schema change. The existing missing-`SASE_*` defect is shared; this credit is for the broader configurable solution.

The final does not accept Gemini's socket control plane, blanket severity claims, or healthcheck DSL. Its finding that `enable` preserves a stop is also corrected as expected behavior.

### 5. A wide-terminal documentation preview beside command completion

**Final:** [tui_colon_command_line.md](../202609/tui_colon_command_line/tui_colon_command_line.md)  
**Gemini:** [tui_colon_command_line__gem.md](../202609/tui_colon_command_line/tui_colon_command_line__gem.md)  
**Peers checked:** `__cld.md`, `__mus.md`.

Gemini supplies a **dual-pane completion card**: candidates on one side and a live rich documentation preview on the other. The other reports already advocate rich descriptions, contextual completion, and signature help; the distinctive addition is the separate side-by-side preview surface.

The final adopts it with a size condition: at **140 columns or wider**, highlighting a subcommand or option can open a right-hand **doc peek** containing its summary, arguments, choices, and defaults. It explicitly says **“This is gem's dual-pane card”** and collapses the preview to the signature line on narrower terminals. Gemini's centered overall modal is rejected, but this component is retained inside the selected bottom drawer.

This credits a proposed UI behavior in the research conclusion, not a claim that the preview has shipped.

### 6. A concrete successful article-to-audio extraction test

**Final:** [article_paper_audio_workflow.md](article_paper_audio_workflow/article_paper_audio_workflow.md), also retained in [its `__final.md` synthesis](article_paper_audio_workflow/article_paper_audio_workflow__final.md)  
**Gemini:** [article_paper_audio_workflow__gem.md](article_paper_audio_workflow/article_paper_audio_workflow__gem.md)  
**Peers checked:** `__cdx.md`, `__grk.md` — the two other researcher files available in this topic.

Gemini tests Trafilatura on Böckeler's Fowler-hosted harness-engineering article, then runs `sase-listen script` and lint. It reports a clean extraction, meaningful chapters, and zero lint errors. Its report gives 2,540 words, 14 chapters, a 0.4-second normalization, and a 17.1-minute dry-run estimate.

Codex supplies a different, mostly cautionary experiment covering Anthropic prose and academic-paper HTML; Grok surveys ingestion options and the reading list without the same successful normalization experiment. Gemini's unique contribution is **a concrete positive example on another source**, not introducing Trafilatura or inventing the articles-versus-papers distinction.

The final retains exactly the defensible portion: **“gem separately reported a successful Fowler extraction with meaningful chapters and zero lint errors.”** It uses that as support for Trafilatura as a starting point, while rejecting a guarantee that every article works. It does not repeat all Gemini's numerical claims. This is an attributed historical experiment, not independently reproduced evidence from this audit.

### 7. The workspace setup path independently advances the Rust core

**Final:** [core_schema_skew_outage_recovery_ux.md](../202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md)  
**Gemini:** [core_schema_skew_outage_recovery_ux__gem.md](../202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux__gem.md)  
**Peers checked:** `__cdx.md`, `__cld.md`, `__grk.md`, `__mus.md`.

Gemini identifies a second update channel: a workspace's `just _setup` fast-forwards its linked `sase-core` checkout to `origin/master`, rebuilds the extension, and can then fail wire-schema validation against that workspace's older Python reader. Thus fixing only the operator's TUI/global update path would leave monitored verification able to recreate skew.

The peers identify the global dev-update/schema mismatch and some report `_setup` failures. They do not explain this separate setup-driven fast-forward/rebuild mechanism. The final's verification table credits Gemini and marks it **“Confirmed, as a second channel.”** Its §1.2 explains the mechanism, separates monitor failures from ACE/bootstrap failures, and the repair scope explicitly covers both host updating and workspace `_setup` pin respect. This is narrower than claiming Gemini found the incident's primary trigger, which the final credits to Claude. The final also corrects substantial errors in Gemini's relaunch timeline.

### 8. Bare `cargo check` selects an interpreter below the binding's minimum

**Final:** [sase_core_agent_maintainability.md](../202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md)  
**Gemini:** [sase_core_agent_maintainability__gem.md](../202609/sase_core_agent_maintainability/sase_core_agent_maintainability__gem.md)  
**Peers checked:** `__cld.md`, `__mus.md`.

Gemini reproduces a specific type-checking trap: the default `python3` is 3.11, while the PyO3 binding requires `abi3-py312`, so bare `cargo check --workspace` fails in build configuration before checking the intended edit. It identifies the environment resolution performed by `scripts/check.sh` and the need for the fast loop to use that wrapper.

The final explicitly credits the interpreter-mismatch finding to Gemini and marks it confirmed. §4.1 records the 3.11-versus-3.12 mechanism; the recommended `just fast` is consequently routed through `check.sh`.

The credit is deliberately narrow. Claude separately reproduces a bare **`cargo test`** failure caused by `LD_LIBRARY_PATH`/libpython and already says the never-bare-cargo rule is load-bearing. Muse also recommends `just fast` and the script entry point. Those shared wrapper and fast-loop recommendations are not unique Gemini contributions. The distinct retained evidence is the **interpreter floor failure in `cargo check`**, not discovering that cargo generally needs a wrapper. The final rejects Gemini's 14-second real-edit timing estimate.

## Five limited cases

These are retained contributions, but weaker evidence of a major research advantage. Keeping their qualification prevents a long list of small alternatives from looking like decisive discoveries.

| Final report | Distinctive retained contribution | Why it is limited |
| --- | --- | --- |
| [commute_audio_from_markdown.md](commute_audio_from_markdown/commute_audio_from_markdown.md) | Gemini's concrete **`static-ffmpeg` package managed through `uv`** as a root-free acquisition route. The final explicitly offers it beside the system-package/sudo-gate route. | Claude already proposes installing FFmpeg or using a bundled static binary. Only the specific package and `uv` recipe are distinct; the general static-binary idea is shared. |
| [prompt_space_and_project_cycle_latency.md](prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md) | Gemini profiles roughly **27 ms of first-mount imports in `_refresh_dispatch_context_line`**, and proposes hoisting them and staggering nonessential warmers to reduce the simultaneous-worker burst. | The final labels this **“Only gem”**, **“Plausible”**, and **“secondary hygiene, not a primary cause.”** Grok also inventories catalog warmers; only the measured import stall and contention/staggering interpretation are distinct. The lead does not independently verify that interpretation. |
| [muse_live_reply_streaming.md](muse_live_reply_streaming/muse_live_reply_streaming.md) | Stop or dismiss the provider timer on the first reply delta, allowing **token-level console streaming** outside Rich `Live`. The final explicitly credits this to Gemini in Phase 3. | It is retained as a possible interactive-console alternative, not the selected default. The final chooses intact line-by-line streaming under the spinner and rejects Gemini's TUI diagnosis and paragraph-chunking fix. |
| [usage_window_collector_hosting.md](../202609/usage_window_collector_hosting/usage_window_collector_hosting.md) | Gemini points out the hard **2-second `agy`/`grok --version` probe deadline** and proposes a 4-second deadline plus version memoization. The final retains a binary-identity-keyed capability cache and the 4-second increase. | The constant is verified, but the lead cannot reproduce Gemini's claimed live false timeout. Claude already proposes capability caching; the distinct part is the specific 2-second defect and 4-second change. This is preventive hardening, not a confirmed production incident. |
| [apollo_upgrade_and_machine_bootstrap.md](../202609/apollo_upgrade_and_machine_bootstrap/apollo_upgrade_and_machine_bootstrap.md) | Gemini correctly identifies the roughly **20 GiB cache as `~/.cache/sase/tmp`**, correcting Muse's claim that it was the uv cache. The final's resolution retains that specific path. | Claude already knows the aggregate regenerable disk footprint. This is a narrow diagnostic correction. Gemini's blanket deletion commands and several upgrade/storage claims are rejected; the final substitutes managed cleanup. |

Available peers were checked for the first three: four each (`cdx`, `cld`, `grk`, `mus`); the last two have `cld` and `mus` peers. Their Gemini sources are the corresponding sibling `__gem.md` files. The finals retain these points in both unsuffixed and `__final.md` forms where both exist.

## Important exclusions and misleading credits

### A credit table can overstate uniqueness

- **Model catalog maintenance — exclude the “test tax” from the unique list.** The [final](../202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance.md) calls Gemini's test-tax observation “the key insight.” But [Claude's report](../202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance__cld.md) §1.4 already lists literal-value tests as churn and §5.4 proposes manifest-derived expectations and behavior/rule tests. [Grok's report](../202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance__grk.md) requirement 9 also replaces exact tuples with invariants. The final retains a good idea, but it is shared.
- **Follow-up reading list — exclude Böckeler as a unique Gemini find.** The [final's provenance table](../202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md) assigns Böckeler to Gemini as a secondary origin. However, [Claude's report](../202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list__cld.md) already recommends the same article as a companion and explains guides/sensors and computational/inferential controls. The substantive contribution is not unique, regardless of the table.
- **ToolRun TUI — exclude the quick-run palette as unique.** The [final](../202609/sase_tool_tui_integration/sase_tool_tui_integration.md) credits Gemini's quick-run palette entry among accepted pieces. [Codex's report](../202609/sase_tool_tui_integration/sase_tool_tui_integration__cdx.md) already explicitly adds **“Run project tool…”** to the command palette. Shared presence matters more than the final's attribution wording.

### A unique proposal may still fail the retention test

The finalizer Main-card/instance-block proposal, automatic dispatch from a machine tab, a persistent static developer-language prior for next-word completion, and a socket-based services control plane all attract discussion in finals. They are rejected, not accepted contributions. Similarly, the rename shortlist refutes most Gemini collision claims; the GC-freeze report rejects its proposed thresholds; and the research-swarm roadmap rejects its independent linker/publication proposal. These are not positive matches merely because the final mentions Gemini.

The Hermes comparison says Gemini correctly emphasized in-memory approval waiting, but Claude already contrasts durable records with blocking processes. I did not promote an emphasis difference into a clear unique conceptual contribution. Likewise, the Rust guardrail report accepts Gemini's warning about filler documentation, while Claude already proposes restricting the documentation gate to module roots. That is supporting rationale for a shared choice, not a strong unique policy discovery.

## Coverage ledger

“Not certified” means this audit did not establish a positive match under the above standard. It does **not** assert that every phrase is redundant or that Gemini was useless. The main findings are a conservative lower bound; absence of equivalently worded text is not sufficient to prove absence of an idea.

| Historical topic / published final | Result | Retained unique contribution established here |
| --- | --- | --- |
| [agent_data_card_blocks](../202609/agent_data_card_blocks/agent_data_card_blocks.md) | Not certified | — |
| [agent_history_in_agents_tab](../202609/agent_history_in_agents_tab/agent_history_in_agents_tab.md) | Not certified | — |
| [agent_long_command_early_exits](../202609/agent_long_command_early_exits/agent_long_command_early_exits.md) | Strong match | Antigravity hard limit, idle shutdown, and tested keep-alive escape. |
| [agent_machine_tabs_and_cluster_semantics](../202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md) | Not certified | — |
| [agents_dynamic_tabs](../202609/agents_dynamic_tabs/agents_dynamic_tabs.md) | Strong match | Keep an emptied active tab until the user leaves it. |
| [agents_sidebar_node_rail_and_zoom](../202609/agents_sidebar_node_rail_and_zoom/agents_sidebar_node_rail_and_zoom.md) | Not certified | — |
| [agents_tab_decks_and_cards](../202609/agents_tab_decks_and_cards/agents_tab_decks_and_cards.md) | Not certified | — |
| [agents_tab_finalizer_visibility](../202609/agents_tab_finalizer_visibility/agents_tab_finalizer_visibility.md) | Not certified | — |
| [agents_tab_node_finder](../202609/agents_tab_node_finder/agents_tab_node_finder.md) | Not certified | — |
| [agy_usage_windows](../202609/agy_usage_windows/agy_usage_windows.md) | Not certified | — |
| [apollo_upgrade_and_machine_bootstrap](../202609/apollo_upgrade_and_machine_bootstrap/apollo_upgrade_and_machine_bootstrap.md) | Limited match | Correct identification of the roughly 20 GiB SASE temp cache. |
| [artifact_hook_intent_matching](../202609/artifact_hook_intent_matching/artifact_hook_intent_matching.md) | Not certified | — |
| [bead_attachment_audience](../202609/bead_attachment_audience/bead_attachment_audience.md) | Not certified | — |
| [bead_note_attachments](../202609/bead_note_attachments/bead_note_attachments.md) | Not certified | — |
| [bead_speedup_daemon_vs_direct_path](../202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md) | Strong match | Acknowledgement → agent exit → delayed publication failure/eviction argument. |
| [core_schema_skew_outage_recovery_ux](../202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md) | Strong match | Workspace setup independently advances and rebuilds the Rust core. |
| [deck_card_paging_ux](../202609/deck_card_paging_ux/deck_card_paging_ux.md) | Not certified | — |
| [goal_outcomes_and_verification](../202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md) | Not certified | — |
| [goals_vs_structural_completion_notifications](../202609/goals_vs_structural_completion_notifications/goals_vs_structural_completion_notifications.md) | Not certified | — |
| [memory_and_instruction_file_history](../202609/memory_and_instruction_file_history/memory_and_instruction_file_history.md) | Not certified | — |
| [memory_bead_backlog_audit](../202609/memory_bead_backlog_audit/memory_bead_backlog_audit.md) | Not certified | — |
| [model_catalog_and_size_alias_maintenance](../202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance.md) | Not certified | — |
| [multi_agent_collaboration_strategy](../202609/multi_agent_collaboration_strategy/multi_agent_collaboration_strategy.md) | Not certified | — |
| [pomodoro_ledger_and_daily_roadmap](../202609/pomodoro_ledger_and_daily_roadmap/pomodoro_ledger_and_daily_roadmap.md) | Not certified | — |
| [prompt_history_human_submissions_only](../202609/prompt_history_human_submissions_only/prompt_history_human_submissions_only.md) | Not certified | — |
| [prompt_next_word_prediction](../202609/prompt_next_word_prediction/prompt_next_word_prediction.md) | Not certified | — |
| [prompt_recall_tabs_and_stash_trash](../202609/prompt_recall_tabs_and_stash_trash/prompt_recall_tabs_and_stash_trash.md) | Not certified | — |
| [provider_wait_contract_early_exits](../202609/provider_wait_contract_early_exits/provider_wait_contract_early_exits.md) | Not certified | — |
| [research_swarm_linker_agent](../202609/research_swarm_linker_agent/research_swarm_linker_agent.md) | Not certified | — |
| [routine_source_nav_sections](../202609/routine_source_nav_sections/routine_source_nav_sections.md) | Not certified | — |
| [sase_core_agent_maintainability](../202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md) | Strong match | Bare cargo check selects Python 3.11 below the abi3-py312 floor. |
| [sase_core_p1_guardrails](../202609/sase_core_p1_guardrails/sase_core_p1_guardrails.md) | Not certified | — |
| [sase_goals_design](../202609/sase_goals_design/sase_goals_design.md) | Not certified | — |
| [sase_goals_epic_roadmap](../202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md) | Not certified | — |
| [sase_goals_memory_end_state](../202609/sase_goals_memory_end_state/sase_goals_memory_end_state.md) | Not certified | — |
| [sase_master_ci_repair_and_pypi_0_18_release](../202609/sase_master_ci_repair_and_pypi_0_18_release/sase_master_ci_repair_and_pypi_0_18_release.md) | Not certified | — |
| [sase_paper_followup_reading_list](../202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md) | Not certified | — |
| [sase_services_post_landing_hardening](../202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md) | Strong match | Zero-delay restart no-op; unreaped-child duplication; configurable environment capture. |
| [sase_terminology_renames](../202609/sase_terminology_renames/sase_terminology_renames.md) | Not certified | — |
| [sase_tool_e3_e4_landing_criteria](../202609/sase_tool_e3_e4_landing_criteria/sase_tool_e3_e4_landing_criteria.md) | Not certified | — |
| [sase_tool_e6_e8_go_no_go](../202609/sase_tool_e6_e8_go_no_go/sase_tool_e6_e8_go_no_go.md) | Not certified | — |
| [sase_tool_guarded_recipes_and_monitor_wrapping](../202609/sase_tool_guarded_recipes_and_monitor_wrapping/sase_tool_guarded_recipes_and_monitor_wrapping.md) | Not certified | — |
| [sase_tool_tui_integration](../202609/sase_tool_tui_integration/sase_tool_tui_integration.md) | Not certified | — |
| [sase_vs_hermes_agent](../202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md) | Not certified | — |
| [tool_launch_directive](../202609/tool_launch_directive/tool_launch_directive.md) | Not certified | — |
| [tui_colon_command_line](../202609/tui_colon_command_line/tui_colon_command_line.md) | Strong match | Wide-terminal documentation preview beside completion candidates. |
| [unread_ack_reliability_and_tui_responsiveness](../202609/unread_ack_reliability_and_tui_responsiveness/unread_ack_reliability_and_tui_responsiveness.md) | Not certified | — |
| [usage_window_collector_hosting](../202609/usage_window_collector_hosting/usage_window_collector_hosting.md) | Limited match | Specific 2-second version-probe limit and 4-second hardening change; live failure unconfirmed. |
| [agent_instructions_budgeted_router](agent_instructions_budgeted_router/agent_instructions_budgeted_router.md) | Not certified | — |
| [apollo_agent_oom_wipeouts_root_cause](apollo_agent_oom_wipeouts_root_cause/apollo_agent_oom_wipeouts_root_cause.md) | Not certified | — |
| [article_paper_audio_workflow](article_paper_audio_workflow/article_paper_audio_workflow.md) | Strong match | Successful Fowler article extraction/chapter/lint experiment. |
| [commute_audio_from_markdown](commute_audio_from_markdown/commute_audio_from_markdown.md) | Limited match | Specific static-ffmpeg/uv acquisition recipe; broader idea shared. |
| [deck_and_pager_three_pane_splits](deck_and_pager_three_pane_splits/deck_and_pager_three_pane_splits.md) | Not certified | — |
| [jev_sase_integration_assessment](jev_sase_integration_assessment/jev_sase_integration_assessment.md) | Not certified | — |
| [master_ci_red_why_and_how_to_stay_green](master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md) | Not certified | — |
| [memory_history_tui_support](memory_history_tui_support/memory_history_tui_support.md) | Not certified | — |
| [muse_live_reply_streaming](muse_live_reply_streaming/muse_live_reply_streaming.md) | Limited match | Dismiss timer on first delta; retained as an optional console alternative. |
| [openai_harness_engineering_vs_sase](openai_harness_engineering_vs_sase/openai_harness_engineering_vs_sase.md) | Not certified | — |
| [prompt_space_and_project_cycle_latency](prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md) | Limited match | Measured import stall and warmer-staggering explanation; secondary and tentative. |
| [research_swarm_improvement_roadmap](research_swarm_improvement_roadmap/research_swarm_improvement_roadmap.md) | Not certified | — |
| [sase_listen_what_you_get](sase_listen_what_you_get/sase_listen_what_you_get.md) | Not certified | — |
| [sase_rename_new_name_shortlist](sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md) | Not certified | — |
| [toobig_split_beyond_python](toobig_split_beyond_python/toobig_split_beyond_python.md) | Not certified | — |
| [tui_freeze_gc_heap_bloat](tui_freeze_gc_heap_bloat/tui_freeze_gc_heap_bloat.md) | Not certified | — |

### Five loose Gemini files

These were read as well. A same-topic filename does not establish a same-dispatch source relationship, and no loose file is counted as an additional success.

| Loose source | Relationship / disposition |
| --- | --- |
| [agents_tab_finalizers_decks_and_cards__gem.md](../202609/agents_tab_finalizers_decks_and_cards__gem.md) | Names `research.a.gem`, matching the organized finalizer-visibility source's agent, but has a different body. It is treated as an alternate source variant, not another swarm. The distinctive Main-card and instance-block proposals are rejected in the final. |
| [deck_card_spread_paged_view_ux__gem.md](../202609/deck_card_spread_paged_view_ux__gem.md) | Names a `research.f` researcher, whereas the organized paging source names `research.2l.gem`. Similar subject matter is insufficient to certify that the organized final synthesizes this exact dispatch. No additional positive match certified. |
| [sase_services_improvements_and_extensions__gem.md](../202609/sase_services_improvements_and_extensions__gem.md) | Names `research.27.gem`, matching the organized hardening source's agent, but differs in content and lacks the scheduler no-op finding. The services result above is supported by the organized source actually named by its final. This loose variant does not independently support every credited services finding. |
| [improving_research_swarm_architecture__gem.md](improving_research_swarm_architecture__gem.md) | Similar subject to the organized improvement roadmap, but the loose report provides no explicit researcher ID and has a different body. No reliable additional final-to-dispatch pairing established. |
| [sase_to_sasos_rename_evaluation__gem.md](sase_to_sasos_rename_evaluation__gem.md) | No matching completed final synthesis in the frozen inventory. It cannot satisfy the final-retention condition on its own. |

## Limits of this result

This is a conservative content comparison, not a ranking of models. A distinctive experiment or useful refinement can coexist with serious errors elsewhere in the same Gemini report. The successful topics do not imply that every Gemini recommendation was accepted or that Gemini was the strongest researcher overall.

“Unique” is bounded by the available original reports in the matched topic. Missing, deleted, or unpaired reports could change the conclusion. Attribution to a researcher does not provide causal provenance of the lead's reasoning. Some finals include the lead's independent verification; that strengthens the retained claim, but does not prove the lead would have missed it without Gemini. Historical verification statements are reported as such, rather than rerun against current code.

The small recipe, optional alternative, and tentative performance cases should be kept separate from the substantive findings. I would use the eight strong topics as evidence that Gemini sometimes added value to synthesis, and use the five limited topics only with their stated qualification. I would not turn these counts into a model success rate or a decision about swarm defaults without a standardized contribution ledger and matched evaluation.

## Final research files with retained Gemini contributions

The eight strong matches:

- [202609/agent_long_command_early_exits/agent_long_command_early_exits.md](../202609/agent_long_command_early_exits/agent_long_command_early_exits.md) — Antigravity hard limit, idle shutdown, and tested keep-alive escape.
- [202609/agents_dynamic_tabs/agents_dynamic_tabs.md](../202609/agents_dynamic_tabs/agents_dynamic_tabs.md) — Keep an emptied active tab until the user leaves it.
- [202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md](../202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md) — Acknowledgement → agent exit → delayed publication failure/eviction argument.
- [202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md](../202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md) — Zero-delay restart no-op; unreaped-child duplication; configurable environment capture.
- [202609/tui_colon_command_line/tui_colon_command_line.md](../202609/tui_colon_command_line/tui_colon_command_line.md) — Wide-terminal documentation preview beside completion candidates.
- [202610/article_paper_audio_workflow/article_paper_audio_workflow.md](article_paper_audio_workflow/article_paper_audio_workflow.md) — Successful Fowler article extraction/chapter/lint experiment.
- [202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md](../202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md) — Workspace setup independently advances and rebuilds the Rust core.
- [202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md](../202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md) — Bare cargo check selects Python 3.11 below the abi3-py312 floor.

The five qualified matches:

- [202610/commute_audio_from_markdown/commute_audio_from_markdown.md](commute_audio_from_markdown/commute_audio_from_markdown.md) — Specific static-ffmpeg/uv acquisition recipe; broader idea shared.
- [202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md](prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md) — Measured import stall and warmer-staggering explanation; secondary and tentative.
- [202610/muse_live_reply_streaming/muse_live_reply_streaming.md](muse_live_reply_streaming/muse_live_reply_streaming.md) — Dismiss timer on first delta; retained as an optional console alternative.
- [202609/usage_window_collector_hosting/usage_window_collector_hosting.md](../202609/usage_window_collector_hosting/usage_window_collector_hosting.md) — Specific 2-second version-probe limit and 4-second hardening change; live failure unconfirmed.
- [202609/apollo_upgrade_and_machine_bootstrap/apollo_upgrade_and_machine_bootstrap.md](../202609/apollo_upgrade_and_machine_bootstrap/apollo_upgrade_and_machine_bootstrap.md) — Correct identification of the roughly 20 GiB SASE temp cache.
