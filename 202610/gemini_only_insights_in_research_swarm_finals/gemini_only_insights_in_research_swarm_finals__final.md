# Gemini-Only Insights That Reached Research-Swarm Finals

- **Date:** 2026-10-04
- **Lead synthesis of:** [cdx](gemini_only_insights_in_research_swarm_finals__cdx.md),
  [cld](gemini_only_insights_in_research_swarm_finals__cld.md),
  [grk](gemini_only_insights_in_research_swarm_finals__grk.md),
  [gem](gemini_only_insights_in_research_swarm_finals__gem.md), plus the lead's own peer-by-peer verification of every
  disputed case.
- **Question:** In which research swarms with a Gemini researcher (`__gem.md`) did Gemini contribute an insight that
  **no other researcher in that swarm had** and that the **consolidated final actually kept**?

## Bottom line

1. **Yes, in 17 of the 65 completed swarms Gemini joined.** In **12** of them a Gemini-only insight clearly shaped the
   final. In another **5**, a Gemini-only contribution was kept but is narrower, reworked, or secondary. In 23 more, only
   minor Gemini-only details survived. In 25, nothing Gemini-only reached the final.
2. **The strongest cases are discoveries made by running things:**
   - Antigravity's hard 10 s command cap, plus a working keep-alive escape from it;
   - `sase scheduler restart` being a live-verified no-op;
   - a stale `sase-core-revision.txt` pin behind master's largest CI failure cluster;
   - a second schema-skew channel through workspace `just _setup`;
   - the 10–30 s first-bead cost in a fresh workspace.

   Two UI rules also survived: an emptied active tab stays put (R11), and lag must not turn `,u` into a silent undo (R5).
3. **A final's "(gem)" credit is not proof of uniqueness, and missing credit is not proof of absence.**
   - **Over-credited:** at least nine finals credit Gemini for ideas a peer had first. Examples are the model catalog's
     "test tax", the Böckeler companion read, the "Run project tool…" palette entry, artifact tags, and −16 LUFS.
   - **Under-credited:** three Gemini-only findings were adopted with no credit at all. These are the stale core pin
     (master CI's largest cluster), the `v`/`view_files` key collision, and the per-`,j` cache miss.
4. **No single input report was right.** The four researchers named between 12 and 15 swarms each, and only 3 swarms
   appear on all four lists. Each report had false positives, mostly from trusting a final's attribution, and each
   missed real cases. cld's audit was closest to the verified result. Its only misses are `should_sase_become_sasos`,
   consolidated after cld took its inventory, and `commute_audio_from_markdown`, which cld rated minor-only.
5. **Gemini is a high-variance contributor.**
   - Its kept unique work is usually one sharp, checkable item per swarm. That item is typically a live probe result, a
     fact about its own Antigravity harness, a cross-repo pin chain, a UI edge case, or a name.
   - The same reports carry many of the leads' corrections: unmeasured percentages, invented details, and architecture
     proposals that were rejected.
6. **Its unique value falls as the swarm grows.** In 3-researcher swarms, 6 of 15 have a clear Gemini-only keep. With 4
   or 5 researchers, the rate is 6 of 49.

## Scope and method

**Corpus.** The research sidecar holds **69 historical `__gem.md` reports**. This swarm's own Gemini report is
excluded.
- **65** sit in a `<month>/<topic>/` directory with a consolidated final.
- **4** are loose drafts with no final, so they cannot qualify:
  - `202609/agents_tab_finalizers_decks_and_cards__gem.md`
  - `202609/deck_card_spread_paged_view_ux__gem.md`
  - `202609/sase_services_improvements_and_extensions__gem.md`
  - `202610/improving_research_swarm_architecture__gem.md`

`202610/should_sase_become_sasos/` was consolidated at 14:57 today. That was after cdx and cld took their inventories
(both counted 64 swarms), and it explains why neither of them covers it.

**Rules.**
- **Unique:** no peer researcher report in the same directory (`__cdx`, `__cld`, `__grk`, `__mus`) states the
  substance, even in different words.
- **Kept:** the final uses it constructively, as a finding, requirement, recommendation step, ranked option, or cited
  evidence. Ideas mentioned only to be rejected do not count.
- **Attribution:** the final's own credit lines were treated as leads to check, not as evidence.

**Verification.**
- Starting point: cld's 64-swarm classification. It was the only exhaustive grading.
- Every swarm that any of the four reports placed in a positive tier was re-checked. That is 27 swarms.
- Each check read the final, the Gemini report and every peer report through `sase artifact read`, and searched the
  peers for the idea's substance using several synonyms.
- The 15 minor-only swarms that no report disputed rely on cld's grading.
- 23 of the 25 "nothing unique" swarms appear on no report's positive list. The other 2,
  `artifact_hook_intent_matching` (gem) and `muse_live_reply_streaming` (cdx), were re-checked and found to be shared
  with a peer.

### How the four inputs compare with the verified result

| Report | Swarms claimed | Confirmed in tiers A/B | Credited for the wrong item | Not in tiers A/B on re-check | Missed |
| :--- | ---: | ---: | :--- | :--- | ---: |
| cdx | 8 strong + 5 limited | 9 | bead speedup (write-behind is shared) | article audio run, muse timer, usage-window timeout, apollo cache (all minor or shared) | 8 |
| cld | 12 clear + 3 qualified | 15 | — | — | 2 |
| grk | 12 | 8 | `P` key (grk itself was runner-up), "optional dilemma" | test tax, Böckeler, palette/waterfall, `//!` module roots | 9 |
| gem | 13 | 9 | `P` key; `:last` and −16 LUFS over-claimed | test tax, artifact tags, "also changed" links (shared); apollo cache (minor) | 8 |

The failures follow one pattern. The reports that trusted the final's attributions (grk, gem) over-counted, and the
report that demanded verbatim-equivalent peer absence (cdx) under-counted. The Gemini self-audit over-credited Gemini
in at least three swarms.

## Finals that credit the wrong researcher

These matter beyond this question, because anyone mining finals for "who found what" will be misled.

| Final | Credit in the final | Who actually had it first |
| :--- | :--- | :--- |
| `model_catalog_and_size_alias_maintenance` | "gem's 'test tax' point is the key insight" | cld §1.4/§5.4 (tests restate shipped values; derive expectations from data) and grk requirement 9 ("fan-out around the YAML") |
| `sase_paper_followup_reading_list` | "gem (Böckeler)" companion to pick #1 | cld (the final's guides/sensors × computational/inferential text follows cld's wording) |
| `sase_tool_tui_integration` | gem's quick-run palette entry | cdx, with the exact label "Run project tool…" (stage waterfall: cld) |
| `artifact_hook_intent_matching` | gem: artifact tags and unconditional lead registration, "Adopt those ideas" | cdx had every part, including `--file-hook-tag` and "the lead does not call `#research`"; grk had most |
| `deck_card_paging_ux` | gem proposes `P` | grk named `P` as runner-up with the same `p`/pick-deck rationale |
| `commute_audio_from_markdown` | gem's "−16 LUFS, −1.5 dBTP, pause lengths" adopted | −16 LUFS is cld's; only −1.5 dBTP and the pause lengths are Gemini's |
| `muse_live_reply_streaming` | gem: dismiss the timer on the first delta | mus had already sketched suspending the same `Live` timer |
| `bead_speedup_daemon_vs_direct_path` | gem's "optional dilemma" | cld had the substance; only the label is Gemini's |
| `tui_colon_command_line` | gem's `:last` / re-attach and capability table | cld and mus (re-attach); cld (capability content) |
| `sase_master_ci_repair_and_pypi_0_18_release` | *no credit*; the lead "re-inventoried" | **gem only**, with the exact SHA |
| `deck_card_paging_ux` | *no credit*; presented as the lead's key audit | **gem only** (`v` is `view_files`; mus called `v` free) |
| `unread_ack_reliability_and_tui_responsiveness` | *no credit* for the `,j` cache-miss consequence | **gem only** |

## What kind of insight survives

**Kept Gemini-only work falls into five kinds:**
- **Live probes of the running system:** the scheduler-restart PID test, the agy keep-alive run, first-bead latency,
  the `cargo check` ABI failure, and the 27 ms import.
- **Knowledge of its own Antigravity harness.** Gemini was the only researcher running on agy.
- **Cross-repo pin and build chains:** the stale core pin and the `_setup` fast-forward/rebuild.
- **UI edge cases that would surprise a user:** the focus latch, the double-press undo trap, the `v` collision, and
  linked-bead-first ranking.
- **Naming and collision search:** the `task` alias collision, `baste`, the graveyard namesakes, and Nokia 7210 SAS OS.

**Gemini's unique proposals were consistently rejected in two areas:**
- **Architecture:** the Catalog agent tab, runtime file leases, handoff capsules, a socket control plane, a FINAL
  Verification card, `%model auto` routing, and a separate goals sidecar.
- **Quantitative claims:**

| Gemini's claim | Swarm | What the lead found |
| :--- | :--- | :--- |
| >70% of the diff is tests | `model_catalog_and_size_alias_maintenance` | 42% |
| 21 getters | `sase_core_p1_guardrails` | 85 |
| 1.68 s spec build | `tui_colon_command_line` | about 0.4 s warm |
| 14 s check loop | `sase_core_agent_maintainability` | Gemini timed a `touch`, not an edit |
| ~35% savings from routing | `jev_sase_integration_assessment` | deferred as unsupported |
| 80% fewer conflicts | `multi_agent_collaboration_strategy` | unsourced |
| 64% GC share | `tui_freeze_gc_heap_bloat` | unmeasured |

The best finds and the heaviest corrections often sit in the same report:
- `core_schema_skew_outage_recovery_ux`: Gemini's timeline was "largely unreliable".
- `unread_ack_reliability_and_tui_responsiveness`: its root-cause theories were refuted.
- `bead_speedup_daemon_vs_direct_path`: its mutation latency was overruled.

**Swarm size.**

| Researchers (incl. gem) | Swarms | Clear (A) | Qualified (B) | A + B |
| :--- | ---: | ---: | ---: | ---: |
| 2 | 1 | 0 | 0 | 0 |
| 3 (gem, cld, mus) | 15 | 6 | 1 | 7 (47%) |
| 4 | 15 | 2 | 2 | 4 (27%) |
| 5 (gem, cdx, cld, grk, mus) | 34 | 4 | 2 | 6 (18%) |

The measure makes uniqueness easier with fewer peers, but the drop is steep. Once cdx and grk joined, most of Gemini's
finds were also made by someone else.

## Swarms with only minor Gemini-only keeps (23)

**Verified by the lead (8):**
- `model_catalog_and_size_alias_maintenance`: the manifest-typo / LSP-startup risk, and its `just check` validation
  mitigation.
- `sase_core_p1_guardrails`: the "filler docs" rationale (`//! Implementation of scanner`). The final uses it as its
  reason for module-root-only `//!`, but the decision itself was cld's.
- `sase_paper_followup_reading_list`: Böckeler's *Context Engineering for Coding Agents* (2026-02-05) as the
  context-side pointer.
- `usage_window_collector_hosting`: the hard 2.0 s `--version` timeout, raised to 4 s. The binary-identity cache is
  cld's.
- `apollo_upgrade_and_machine_bootstrap`: the 20 GiB is `~/.cache/sase/tmp`, not the uv cache. This corrects mus.
  Gemini's `rm -rf` cleanup was rejected.
- `article_paper_audio_workflow`: the only clean Trafilatura → `sase-listen` run (the Fowler article, 0 lint errors).
  It is one hedged sentence; the recommendation rests on cdx and grk.
- `sase_tool_tui_integration`: a deferred FINAL-deck link from a verdict receipt to its run. It is the remnant of
  Gemini's rejected Verification card.
- `memory_and_instruction_file_history`: extending "also changed in this commit" links to every memory note. This
  appears only in the disagreements row; the body spec is cld's and cdx's.

**From cld's grading, not disputed (15):**
- `agents_tab_node_finder`: a secondary rejection reason.
- `agy_usage_windows`: a live `403 UNSUPPORTED_CLIENT` probe.
- `apollo_agent_oom_wipeouts_root_cause`: exit-143/SIGTERM logs and `sar` data.
- `bead_attachment_audience`: "no egress bills".
- `bead_note_attachments`: bare `@name.ext` is a path only for known extensions.
- `jev_sase_integration_assessment`: unofficial Rust crates exist.
- `master_ci_red_why_and_how_to_stay_green`: KNOWN only if quarantined (low confidence).
- `pomodoro_ledger_and_daily_roadmap`: a link-rule audit.
- `prompt_next_word_prediction`: the module name `sase_core::prompt_prediction`.
- `research_swarm_improvement_roadmap`: beads and decision records on request, and a heading check.
- `sase_listen_what_you_get`: per-engine costs, `podcast:locked`, and the narration exclusion.
- `sase_tool_guarded_recipes_and_monitor_wrapping`: the v1 monitor-wrap scope.
- `toobig_split_beyond_python`: the Swift stored-properties rule.
- `tool_launch_directive`: a `%tool` → `%proc` error hint (low confidence).
- `agent_instructions_budgeted_router`: Antigravity also loading `GEMINI.md`, kept only as a verify-it follow-up.

## Swarms where nothing Gemini-only was kept (25)

**`202609/` (20):** `agent_data_card_blocks`, `agent_history_in_agents_tab`,
`agent_machine_tabs_and_cluster_semantics`, `agents_sidebar_node_rail_and_zoom`, `agents_tab_decks_and_cards`,
`agents_tab_finalizer_visibility`, `artifact_hook_intent_matching`, `goals_vs_structural_completion_notifications`,
`memory_bead_backlog_audit`, `multi_agent_collaboration_strategy`, `prompt_history_human_submissions_only`,
`prompt_recall_tabs_and_stash_trash`, `provider_wait_contract_early_exits`, `research_swarm_linker_agent`,
`routine_source_nav_sections`, `sase_goals_design`, `sase_goals_epic_roadmap`, `sase_goals_memory_end_state`,
`sase_tool_e3_e4_landing_criteria`, `sase_tool_e6_e8_go_no_go`.

**`202610/` (5):** `deck_and_pager_three_pane_splits`, `memory_history_tui_support`, `muse_live_reply_streaming`,
`openai_harness_engineering_vs_sase`, `tui_freeze_gc_heap_bloat`.

## Limits

- **Uniqueness is relative to the researcher reports, not the lead.** Where the lead re-measured or re-inventoried, it
  might have found the item without Gemini. The stale pin and the `v` collision are the cases most exposed to this.
- **Inclusion is judged from the final's text,** not from plans or landed code. As a side note, the `P` deck-cycle key
  did ship (`cycle_deck_view: "P"` in `default_config.yml`), but it is shared with grk.
- **The substantive/minor line is a judgment call.** The qualified tier exists to make those calls visible.
- **The 15 undisputed minor-only swarms were not re-verified** beyond cld's audit.

## Final list: research files where a Gemini-only insight reached the final

Paths are relative to the research repo root. Each Gemini source sits beside its final as `<topic>__gem.md`.

### A. Clear cases (12)

1. **[`202609/agent_long_command_early_exits/agent_long_command_early_exits.md`](../../202609/agent_long_command_early_exits/agent_long_command_early_exits.md)**
   (peers: cld, mus). The whole Antigravity failure mechanism:
   - `run_command` cannot block past 10 s (`WaitMsBeforeAsync` 500–10000 ms);
   - the tool text tells the model to end the turn;
   - print mode kills background tasks after a 5 s idle grace and exits 0.

   Gemini also demonstrated the escape live: keep calling tools (`manage_task status`) and the completion arrives in the
   same turn. The lead confirmed the mechanism in the agy 1.2.7 binary and adopted the keep-alive rule. Neither peer had
   any agy mechanism. This is the strongest case, because Gemini was the only researcher running on that harness.
2. **[`202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md`](../../202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md)**
   (peers: cld, mus). Several live-tested bugs:
   - `sase scheduler restart` is a no-op, because `delay=0.0` clears the stop marker before the host reads it ("gem: yes,
     a live-verified no-op. cld and mus missed it", §3.4). The peers had only the general 0.5 s race.
   - A child that survives SIGKILL is dropped from `_children` and relaunched beside itself ("gem Bug 9").
   - `proc start` on a disabled proc reports success.
   - The Services help omits `r`.
   - The final endorses `service.capture_env_names` as "the general form" of the env-capture fix, though its P0 action
     is a narrower `SASE_*` allow-list.
3. **[`202609/sase_master_ci_repair_and_pypi_0_18_release/sase_master_ci_repair_and_pypi_0_18_release.md`](../../202609/sase_master_ci_repair_and_pypi_0_18_release/sase_master_ci_repair_and_pypi_0_18_release.md)**
   (5 researchers). Commit `17d2beb76` needs three goal bindings that exist only in sase-core `33b0250`, while
   `sase-core-revision.txt` still pinned `cbe70f66`.
   - **In the final:** it became the largest Master Gate cluster (16 tests plus the lint head-blocker), the
     "cross-repo landing race" systemic cause, and the Wave 1 pin bump, using Gemini's SHA.
   - **Peers:** cld, grk and mus all said the pin was fine. grk: "Master Gate does **not** fail this check".
   - **Credit:** none in the final.
4. **[`202609/agents_dynamic_tabs/agents_dynamic_tabs.md`](../../202609/agents_dynamic_tabs/agents_dynamic_tabs.md)**
   (5 researchers). The focus latch: an emptied active tab stays selected until the user navigates away. It became
   requirement R11, "The place you are standing does not vanish under the cursor (gem)", and carries through to P3 and
   the tests. cld and cdx proposed the opposite: jump to the nearest surviving tab.
5. **[`202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md`](../../202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md)**
   (5 researchers). The second skew channel: each workspace's `just _setup` fast-forwards its linked sase-core and
   rebuilds `sase_core_rs`.
   - **What it explained:** the monitor failures.
   - **In the final:** "Confirmed, as a second channel … No single report stated both". It drives "respect the pin in
     both channels".
   - **Caveats:** the primary trigger is credited to cld, and Gemini's timeline was "largely unreliable".
6. **[`202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`](../../202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md)**
   (peers: cld, mus). The first bead command in a fresh workspace takes 10–30+ s because of the sidecar clone.
   - **In Gemini's report:** only one table row.
   - **In the final:** TL;DR item 2, §1.4 "new finding, extends gem", RA7, a Phase 0 fix, and bead `sase-17r`. The lead
     re-measured it (p50 22 s) and traced it to `--dissociate`.
   - **Not unique:** the "optional dilemma" and write-behind arguments, which cld had in substance.
7. **[`202609/unread_ack_reliability_and_tui_responsiveness/unread_ack_reliability_and_tui_responsiveness.md`](../../202609/unread_ack_reliability_and_tui_responsiveness/unread_ack_reliability_and_tui_responsiveness.md)**
   (5 researchers). Two Gemini-only findings:
   - **The `,u` double-press trap:** `,u` is a silent toggle, so a lag-induced double press restores all 27 unread
     markers. It became R5 (explicit, time-bound undo), and is credited to gem in the hypothesis table.
   - **The per-`,j` cache miss:** each `,j` changes `unread_ids`, so the next `,j` always misses the candidate cache.
     The final adopted remove-from-cached-list, without credit; grk's generation-counter fix would still miss.

   Gemini's root-cause theories for the incident itself were refuted.
8. **[`202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md`](../../202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md)**
   (peers: cld, mus). Bare `cargo check` fails because pyenv `python3` is 3.11 and `sase_core_py` needs abi3-py312.
   - **In the final:** "Real. `just fast` must wrap `check.sh`", a P0 item.
   - **Gemini-only:** the diagnosis. Routing through `check.sh` was already in cld and mus, and Gemini's own fix
     (`PYO3_PYTHON`) was not used.
9. **[`202609/tui_colon_command_line/tui_colon_command_line.md`](../../202609/tui_colon_command_line/tui_colon_command_line.md)**
   (peers: cld, mus). Two pieces were kept:
   - **The side-by-side doc peek** on terminals ≥140 columns ("This is gem's dual-pane card"), an optional P4 extra.
     Its content overlaps cld's signature line.
   - **Linked beads rank first:** a selected agent's or Patch's linked bead ranks first, credited "(gem)".

   `:last`/re-attach and the capability table are shared with peers.
10. **[`202609/sase_terminology_renames/sase_terminology_renames.md`](../../202609/sase_terminology_renames/sase_terminology_renames.md)**
    (peers: cld, mus). Sunset the `task` alias of `sase proc`, because "task" is now the bead-tier noun.
    - **In the final's table:** cld "not raised", mus "not raised", gem "Deprecate", resolved "**Agree**".
    - **Adopted as:** recommendation 6, behind a sunset flag.
11. **[`202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md`](../sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md)**
    (peers: cdx, cld, grk).
    - **`baste`:** Gemini's top pick, absent from every peer. It ranks #2 overall and is one of the three finalists
      (`handful`, `baste`, `crewrail`) carried into testing.
    - **Ten graveyard namesakes:** cohort, guild, chorus, gantry, rigor, plinth, consort, vise, rivet and plumb were
      disqualified as agent-tool namesakes. No peer found them.

    Gemini's "completely clean" claims were overturned.
12. **[`202610/should_sase_become_sasos/should_sase_become_sasos.md`](../should_sase_become_sasos/should_sase_become_sasos.md)**
    (peers: cdx, cld, grk). Nokia's 7210 SAS OS (Service Access Switch firmware) is a spoken `sasos` collision in
    networking. The lead confirmed it in Nokia's release-note titles and put it in the collision inventory credited to
    gem. Nothing else Gemini-only was kept.

### B. Qualified cases (5)

13. **[`202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md`](../../202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md)**
    (peers: cld, mus). Hermes approvals block a live in-memory process for up to 300 s, while sase gates are durable and
    need no running process. cld already had the durable-vs-blocking contrast but scored it as parity.
    - **In the final:** "Correct, and cld under-weighted it", and sase's HITL score rose from 7 to 8.
    - **Why qualified:** the edge table still reads "≈". This is an emphasis that changed a score, not a discovery.
14. **[`202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`](../../202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md)**
    (peers: cdx, grk, mus). A synced per-goal active partition, which the final keeps as `goals/live/<id>.json`. Any
    machine can rebuild its active list from it without replaying closed history. The peers kept hot indexes
    machine-local.
    - **Why qualified:** the final heavily adapts it. It rebuts Gemini's "zero merge conflicts" and atomic-move claims,
      and rejects Gemini's separate goals sidecar.
15. **[`202609/deck_card_paging_ux/deck_card_paging_ux.md`](../../202609/deck_card_paging_ux/deck_card_paging_ux.md)**
    (peers: cdx, grk, mus). Gemini's key audit found that `v` is already `view_files`; mus had called it free. That
    ruled out mus's recommended key.
    - **Why qualified:** the final presents this as its own audit, with no credit. The `P` key credited to Gemini is
      shared with grk's runner-up pick.
16. **[`202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`](../prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md)**
    (5 researchers). A ~27 ms first-mount import in `_refresh_dispatch_context_line`, plus treating the 8–9 mount-time
    warmers as a contention burst worth staggering. No peer mentions that function, and the peers who counted the
    warmers called them fine.
    - **In the final:** "Only gem", adopted as item 7 "Mount hygiene".
    - **Why qualified:** the lead rated it "Plausible … secondary hygiene, not a primary cause".
17. **[`202610/commute_audio_from_markdown/commute_audio_from_markdown.md`](../commute_audio_from_markdown/commute_audio_from_markdown.md)**
    (5 researchers). Concrete mastering and install details:
    - a −1.5 dBTP true-peak ceiling;
    - 0.6 s paragraph and 1.2 s chapter pauses;
    - the `static-ffmpeg` package under `uv` as a no-root ffmpeg route for apollo.

    **Why qualified:** these are details. −16 LUFS and the static-binary idea were cld's, and `static-ffmpeg` is offered
    beside a sudo-gated apt install, not as the default.
