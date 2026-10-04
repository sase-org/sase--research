# Where Gemini Added Something Nobody Else Did: An Audit of Every `__gem.md` Research Swarm

- **Date:** 2026-10-04
- **Author:** researcher cld (`research.3l.cld`), one of four independent researchers on this question
- **Question:** Across all research swarms that Gemini contributed to (`__gem.md` files), in which ones did Gemini provide an
  insight that **no other researcher in that swarm had**, and that **actually made it into the final consolidated report**?
- **Corpus:** the `research` sidecar at commit `49f4649` (2026-10-04): 69 `__gem.md` files in `202609/` and `202610/`.

## Bottom line

1. **Of the 69 Gemini reports, 64 belong to swarms with a consolidated final report.** The other 5 are loose drafts from
   abandoned or re-run swarms that were never consolidated, so nothing of theirs could have been included (see
   [Excluded reports](#excluded-gemini-reports-with-no-final)).
2. **In 15 of those 64 swarms (23%), a Gemini-only insight substantively shaped the final report.** 12 of them are
   clear-cut. The other 3 are real but qualified: the idea was heavily reworked, the impact is low, or the lead may have
   found it independently. These swarms are listed with details in the [final list](#final-list-research-files-where-gemini-only-insights-reached-the-final-report).
3. **In another 24 swarms (38%), the only Gemini-only material in the final was minor.** Examples are a supporting fact, a
   parameter value, a name, or a secondary reason.
4. **In 25 swarms (39%), Gemini contributed nothing unique to the final.** Everything of Gemini's that survived was also
   in at least one peer report, usually cld, and Gemini's distinctive positions were rejected.
5. **Gemini is a high-variance contributor.** In swarm after swarm, the same report that holds the swarm's one unique
   find also holds more lead corrections than any peer: unmeasured performance numbers, invented APIs, overstated
   claims. A Gemini-only claim is about as likely to be a lead correction as a lead adoption.
6. **Its wins cluster in five kinds of insight.**
   - Live probes of the running system.
   - First-hand knowledge of its own `agy`/Antigravity harness.
   - Tracing build and pin chains across repos.
   - Edge cases where the UI would surprise the user.
   - Naming.
7. **Gemini's unique value shrinks as the swarm grows.** In 3-researcher swarms (gem, cld, mus) it had a substantive
   unique contribution in 7 of 15. In 5-researcher swarms it managed only 5 of 34.

## Scope and method

**What counted as a swarm.** A swarm counted if a consolidated `<topic>.md` sits next to a `<topic>__gem.md` in a
`<YYYYMM>/<topic>/` directory. That gives 64 swarms: 48 in `202609` and 16 in `202610`. Newer swarms also carry a
`<topic>__final.md`. That file is the lead's pre-linking copy of the same text, so I treated the published `<topic>.md`
as "the final report". `__critique.md` (one swarm) is a critic, not a researcher, and was not treated as a peer.

**Peers.** The peers are the other researcher reports in the same directory: `__cdx`, `__cld`, `__grk`, `__mus`
(whichever exist). A Gemini idea counted as **unique** only if no peer stated its substance, even briefly. It counted
as **included** only if the final adopted it: as a finding, requirement, recommendation, cited evidence, or ranked
option. Ideas the final mentioned only to reject did not count.

**Process.**
1. Every final, Gemini, and peer report (338 files) was read once through `sase artifact read`, so every read is
   audited.
2. The 64 swarms were split across 12 parallel analysis passes, all using the same rubric:
   - read the final in full and list every mention of gem;
   - read the Gemini report in full;
   - for each Gemini idea present in the final, grep and read every peer for the same substance;
   - grade each surviving item for significance (substantive or minor) and confidence.
3. I then re-checked the key evidence for the headline cases myself against the source text:
   - the final's attribution lines;
   - the peer reports' absence of the idea, or a contrary claim.

   The cases I re-checked were `agents_dynamic_tabs`, `core_schema_skew_outage_recovery_ux`, `sase_terminology_renames`,
   `sase_vs_hermes_agent`, `unread_ack_reliability_and_tui_responsiveness`, `bead_speedup_daemon_vs_direct_path`,
   `sase_services_post_landing_hardening`, `sase_rename_new_name_shortlist`,
   `sase_master_ci_repair_and_pypi_0_18_release`, `sase_core_agent_maintainability`, `tui_colon_command_line` and
   `agent_long_command_early_exits`.

**Significance scale.**
- **Substantive:** the item creates or changes a root cause, requirement, recommended step, ranked option, scored
  verdict, or key fact.
- **Minor:** a supporting detail, parameter, name, or secondary reason.

## Results at a glance

| Verdict | Swarms | Share |
| :--- | ---: | ---: |
| Gemini-only insight substantively shaped the final (clear) | 12 | 19% |
| Gemini-only insight substantively shaped the final (qualified) | 3 | 5% |
| Only minor Gemini-only items reached the final | 24 | 38% |
| Nothing Gemini-only reached the final | 25 | 39% |
| **Total consolidated swarms with a `__gem.md`** | **64** | |

### Swarm size matters more than anything else

| Researchers in swarm (incl. gem) | Swarms | Substantive | Minor only | None |
| :--- | ---: | ---: | ---: | ---: |
| 2 (gem, cld) | 1 | 0 | 1 | 0 |
| 3 (gem, cld, mus) | 15 | **7 (47%)** | 5 | 3 |
| 4 | 14 | 3 (21%) | 4 | 7 |
| 5 (gem, cdx, cld, grk, mus) | 34 | 5 (15%) | 14 | 15 |

Uniqueness is easier with fewer peers, so the trend is partly built into the measure. Still, the gap is large. Once cdx
and grk joined the roster, most of what Gemini found was also found by someone else.

### By month

| Month | Swarms | Substantive | Minor only | None |
| :--- | ---: | ---: | ---: | ---: |
| `202609` | 48 | 13 | 15 | 20 |
| `202610` | 16 | 2 | 9 | 5 |

The `202610` drop mostly tracks swarm size. Every `202610` swarm has 4–5 researchers.

## The 15 swarms with a substantive Gemini-only contribution

Each entry gives the insight, how the final used it, and why it counts as Gemini-only. The paths are relative to the
research repo root, and each swarm's Gemini report sits beside its final as `<topic>__gem.md`.

### Clear cases (12)

**1. `202609/agent_long_command_early_exits/` (gem, cld, mus): Gemini explained its own harness**

- **What only Gemini had.** Gemini supplied the entire `agy` (Antigravity) failure mechanism:
  - `run_command` cannot block longer than 10 s;
  - the tool text tells the model to "end the turn" and not poll;
  - print mode kills background tasks after a 5 s idle grace and exits 0.

  So the directive "run synchronously" is impossible under `agy`, and no prompt wording can fix it.
- **More Gemini-only pieces.**
  - The second failure case, `research.24.gem`.
  - The `sase-15o` version-allowlist gap.
  - A live demonstration that polling `manage_task` status keeps the turn open: `research.25.gem` finished this way.
  - A concrete classifier fix.
- **How the final used it.** The lead confirmed the mechanism in the `agy` 1.2.7 binary's strings and credits gem by
  name in its findings table. The material forms the core of the final's agy repair plan.
- **Peer check.** cld and mus noted the `sase-14t.3` false completion but had none of the mechanism.

This is the strongest case in the corpus. Gemini knew something about its own runtime that the other models could not
see.

**2. `202609/core_schema_skew_outage_recovery_ux/` (5 researchers): a second root-cause channel**

- **What only Gemini had.** The Justfile `_setup` recipe fast-forwards each workspace's linked sase-core to
  `origin/master` and rebuilds `sase_core_rs` into that workspace's venv. That is a skew channel separate from the host
  `dev_update` path.
- **How the final used it.** It became one of the final's "Two independent skew channels. No single report stated
  both". The findings table credits it to gem alone ("Confirmed, as a second channel"). It drives the prevention
  recommendation to respect `sase-core-revision.txt` in **both** channels.
- **Peer check.**
  - cdx saw old workspaces failing `_setup` but blamed stale Python.
  - grk asserted the extension was global.
  - cld mentioned `_setup` only as the place the validator runs.

  The same final calls Gemini's incident timeline "largely unreliable".

**3. `202609/sase_master_ci_repair_and_pypi_0_18_release/` (5 researchers): the largest failure cluster**

- **What only Gemini had.** Commit `17d2beb76` requires three goal bindings that exist only in sase-core `33b0250`,
  while `sase-core-revision.txt` still pinned `cbe70f66`. The fix is to bump the pin.
- **How the final used it.** It became the final's largest Master Gate cluster: 16 tests plus the lint check that blocks
  everything behind it. It is the final's Wave 1 action, the "cross-repo landing race" systemic cause, and the
  corrected count of 13 missing bindings. The final adopts Gemini's exact SHA.
- **Peer check.** No peer mentions the goal bindings or `33b0250`. grk said outright that "Master Gate does **not** fail
  this check".
- **Caveat.** The final does not attribute this to gem, and the lead re-inventoried at HEAD, so it may also have
  confirmed it independently.

**4. `202609/sase_services_post_landing_hardening/` (gem, cld, mus): bugs found by live testing**

- **What only Gemini had.** Gemini verified live that `sase scheduler restart` is a no-op: `delay=0.0` clears the stop
  marker before the host reads it.
- **How the final used it.** The disagreements table reads "gem: yes, a live-verified no-op. cld and mus missed it." It
  is one of the final's top problems.
- **Other Gemini-only items adopted.**
  - A child that survives SIGKILL gets a second instance launched beside it (a P1 fix).
  - Bounded-log rotation.
  - A `status.json` staleness filter.
  - `proc start` reporting success on a disabled proc.
  - Undocumented `r` in the Services help.
  - Configurable environment passthrough, cited as "the general form" of the fix.

**5. `202609/bead_speedup_daemon_vs_direct_path/` (gem, cld, mus): the cost a daemon wouldn't fix**

- **What only Gemini had.** Gemini was first to flag that the first bead command in a fresh workspace takes 10–30+ s
  because of the sidecar clone.
- **How the final used it.** The lead traced it to clone-time repacking. It made it a bottom-line finding, §1.4 "First
  use in a fresh workspace (new finding, extends gem)", requirement RA7, a Phase 0 fix, and follow-up bead `sase-17r`.
- **A second, minor credit.** "Write-behind breaks single-turn completion (gem)" is also Gemini's, though cld had the
  related eviction argument.
- **The same report was also wrong.** Gemini's 1.8–4.5 s mutation-latency figure was overruled ("cld is right").

**6. `202609/unread_ack_reliability_and_tui_responsiveness/` (5 researchers): a UX trap**

- **What only Gemini had.** `,u` is a silent toggle. When the UI lags, a second press silently runs undo and restores
  all 27 unread markers, which looks exactly like "it didn't work".
- **How the final used it.** It became requirement R5: make undo explicit and time-bound.
- **A second Gemini-only item.** Each `,j` changes `unread_ids`, so the next `,j` always misses the candidate cache. The
  final adopted remove-from-cached-list instead of invalidation.
- **Peer check.** grk listed the cache key's contents but never drew the consequence.
- **The same report was also wrong.** Gemini's root-cause theories (collapsed clans, the `FAILED (…)` predicate,
  compaction shrinking the store) were refuted.

**7. `202609/agents_dynamic_tabs/` (5 researchers): the focus latch**

- **What only Gemini had.** If the last agent leaves the tab you are on, the tab stays selected with an empty state
  until you navigate away.
- **How the final used it.** Requirement R11: "The place you are standing does not vanish under the cursor (gem)". It
  carries through the catalog rules, phase P3, and tests.
- **Peer check.** cld proposed the opposite: switch to the nearest surviving tab.

**8. `202609/sase_vs_hermes_agent/` (gem, cld, mus): an asymmetry the others under-weighted**

- **What only Gemini had.** Hermes approvals pause in chat while the agent process stays alive in memory. sase gates
  are durable and use no running process.
- **How the final used it.** The final marks this "Correct, and cld under-weighted it". It reframed human approval as a
  sase advantage and raised that scorecard dimension (cld had rated it parity, "≈").
- **The same report was also the most corrected.** The final fixed its OpenClaw lineage, "no task graph", the DSPy/GEPA
  attribution, and its scores.

**9. `202609/sase_core_agent_maintainability/` (gem, cld, mus): a check that fails as written**

- **What only Gemini had.** On `PATH`, `python3` is pyenv 3.11, but `sase_core_py` needs abi3-py312. So a bare
  `cargo check --workspace` fails, and `just fast` must wrap `check.sh`.
- **How the final used it.** The findings table credits it to gem: "Real. `just fast` must wrap `check.sh`". It became
  a P0 item.
- **Minor extras.** The 800-line `view_file` read limit for agy, and the observation that `sase-15b` was already
  complete at a newer revision.
- **Rejected.** Gemini's "14 s loop", a `sase_types` crate first, and its top-3 file splits.

**10. `202609/sase_terminology_renames/` (gem, cld, mus): a vocabulary collision**

- **What only Gemini had.** Retire the `task` alias on `sase proc`, because "task" is now the bead-tier noun.
- **How the final used it.** The comparison table shows cld "not raised", mus "not raised", gem "Deprecate", resolved
  "**Agree**". It appears in §3.5, recommendation 6 ("Sunset `task` as an alias of `sase proc`, behind a sunset flag"),
  and the summary.
- **Minor extra.** neighbor → peer.
- **Rejected.** Gemini's larger renames: tribe, clan, stitch, and memory web.

**11. `202610/sase_rename_new_name_shortlist/` (gem, cdx, cld, grk): a finalist name**

- **What only Gemini had.** `baste`, which the final ranks **#2** ("Runners-up: `baste` (5) and `crewrail` (8)"). It is
  one of the three finalists carried into the decision test. No peer mentions it.
- **Minor extra.** Ten graveyard names no peer caught as already taken by agent tools: cohort, guild, chorus, gantry,
  rigor, plinth, consort, vise, rivet, and plumb.
- **Overturned.** Gemini's other picks and its "completely clean" claims.

**12. `202609/tui_colon_command_line/` (gem, cld, mus): the doc peek**

- **What only Gemini had.** A dual-pane "candidates + docs" completion card.
- **How the final used it.** It became the final's optional right-hand **doc peek** ("This is gem's dual-pane card").
  It appears in the recommended solution, phase P4, and the PNG golden states.
- **Minor extra.** Ranking the selected agent's or Patch's linked bead first, credited "(gem)".
- **Rejected or corrected.** Gemini's centered modal, its 1.68 s timing, and in-process queries.

### Qualified cases (3)

**13. `202609/goal_outcomes_and_verification/` (gem, cdx, grk, mus).**
- **What only Gemini had.** A synced per-goal `active/` partition that a fresh machine can list without replaying
  history.
- **How the final used it.** It survives as `goals/live/<id>.json`: settlement removes the hot file, and any machine
  rebuilds its active list from the synced directory.
- **Peer check.** grk and cdx kept their hot indexes machine-local.
- **Why qualified.** The final heavily reworks the design (snapshots, events, locking) and corrects Gemini's "zero
  merge conflicts" and atomic-move claims. Peer pieces could also have led the lead to it. Medium confidence.

**14. `202609/deck_card_paging_ux/` (gem, cdx, grk, mus).**
- **What only Gemini had.** Gemini's key audit found `v` is already bound to `view_files`.
- **How the final used it.** That knocks out mus's recommended key ("`v` is already `view_files` … should not be
  taken").
- **Why qualified.** The lead also ran its own key audit. Gemini's headline `P` key was credited to it, but grk listed
  `P` as runner-up with the same rationale, so `P` is shared.

**15. `202610/prompt_space_and_project_cycle_latency/` (5 researchers).**
- **What only Gemini had.** An ~8-thread warmer burst when the prompt bar mounts, plus a ~27 ms synchronous import in
  `_refresh_dispatch_context_line`.
- **How the final used it.** It is credited "Only gem" and adopted as Phase 1 step 7, "Mount hygiene".
- **Why qualified.** The lead rated it "Plausible", called it "secondary hygiene, not a primary cause", and estimated a
  few to tens of ms.

## What kind of insight Gemini uniquely contributes

1. **Live probes of the running system.** Gemini's most valuable unique finds often come from actually running
   something:
   - the scheduler restart no-op;
   - the agy keep-alive;
   - the first-use bead latency;
   - the `cargo check` ABI failure;
   - the 27 ms import;
   - the `403 UNSUPPORTED_CLIENT` endpoint probe;
   - the clean Trafilatura run on a Fowler article;
   - the exit-143 / SIGTERM agent logs.
2. **Knowledge of its own harness.** On the agy/Antigravity questions, Gemini is the only researcher running on that
   harness. That shows in `agent_long_command_early_exits` and the 800-line `view_file` limit. It also shows in the
   still-unverified claim that Antigravity loads both `AGENTS.md` and `GEMINI.md`, which `agent_instructions_budgeted_router`
   kept only as a follow-up to verify.
3. **Following build and pin chains across repos.** Examples are the stale core pin, the `_setup` second skew channel,
   and `sase-15b` already being done at a newer revision.
4. **Edge cases where the UI would surprise the user.** Examples are the focus latch, the double-press undo trap, the
   doc peek, the `v` key collision, and ranking the linked bead first.
5. **Naming and vocabulary.** Examples are the `task` alias collision, `baste`, the graveyard namesakes, and the
   `sase_core::prompt_prediction` module name.

## The other half of the picture: Gemini's unique claims are often the ones the lead corrects

Gemini's distinctive claims split sharply.

**Many were among the most heavily corrected inputs in their swarms.** Unmeasured or wrong quantitative claims recur:

| Gemini's claim | Swarm | What the lead found |
| :--- | :--- | :--- |
| "~35% savings" from model routing | `jev_sase_integration_assessment` | Deferred: no outcome corpus to support it |
| "80% fewer conflicts" from file leases | `multi_agent_collaboration_strategy` | Unsourced |
| "4× faster" | `prompt_history_human_submissions_only` | Rejected |
| "sub-millisecond" reads | `goal_outcomes_and_verification` | Rejected |
| "<1 ms / ~30 KB" | `sase_goals_design` | Unmeasured |
| "1.68 s" spec build | `tui_colon_command_line` | About 0.4 s warm |
| "14 s" check loop | `sase_core_agent_maintainability` | Gemini timed a `touch`, not an edit |
| "1.96% adoption crisis" | `sase_tool_guarded_recipes_and_monitor_wrapping` | A pre-guidance measurement window |
| "64%" GC share | `tui_freeze_gc_heap_bloat` | Unmeasured |
| ">70%" tests | `model_catalog_and_size_alias_maintenance` | Actually 42% |
| "21 getters" | `sase_core_p1_guardrails` | Actually 85 |

**Some finals contain more lead corrections of Gemini than adoptions.**
- `openai_harness_engineering_vs_sase` has five "Wrong/Rejected" rows against gem.
- `agents_tab_decks_and_cards` corrects it about 15 times.
- `sase_tool_e3_e4_landing_criteria` corrects it about a dozen times.
- `sase_core_p1_guardrails` corrects it about ten times.

**A final's explicit credit to gem is not proof of uniqueness.** In at least 11 swarms, the final credited gem for ideas
a peer also had:
- `memory_history_tui_support`: "tombstone and agent-bridge framing" (cdx, cld);
- `agent_history_in_agents_tab`: lightweight rows and harvester (cdx, cld);
- `sase_tool_tui_integration`: three credited ideas (cld, cdx);
- `prompt_history_human_submissions_only`: leaks and the prune command (cld, mus, grk, cdx);
- `artifact_hook_intent_matching`: tags and lead registration (cdx, grk);
- `model_catalog_and_size_alias_maintenance`: the "test tax" (cld, grk);
- `deck_card_paging_ux`: the `P` key (grk);
- `commute_audio_from_markdown`: the static ffmpeg route (cld);
- `research_swarm_improvement_roadmap`: the verifier tool (cdx);
- `provider_wait_contract_early_exits`: the agy failure chain (cld, mus);
- `sase_paper_followup_reading_list`: the harness-engineering companion (cld).

So you cannot get this answer by grepping finals for "gem". Each credit has to be checked against the peers.

**The good and the bad come in the same report.** The swarms with the best unique finds often have the most
corrections too:
- In `core_schema_skew_outage_recovery_ux`, Gemini's timeline was "largely unreliable".
- In `sase_vs_hermes_agent`, it was the most-corrected report.
- In `unread_ack_reliability_and_tui_responsiveness`, its root-cause theories were refuted.
- In `bead_speedup_daemon_vs_direct_path`, its mutation latency was wrong.

Gemini's value in a swarm is real but needs a verifying lead to separate it out.

## Swarms where only minor Gemini-only items reached the final (24)

One line each, in the same form as Part B of the final list below.

- `202609/agents_tab_node_finder`: a secondary reason for rejecting a JumpAllModal extension ("mixes Patch and Service
  hits"). The rejection itself was unanimous.
- `202609/agy_usage_windows`: a live `403 UNSUPPORTED_CLIENT` from the private REST endpoint, cited as supporting
  evidence.
- `202610/apollo_agent_oom_wipeouts_root_cause`: killed-agent logs showing exit 143 / SIGTERM (credited), and `sar`
  direct-reclaim data. Gemini missed the actual FLATTEN-query trigger.
- `202609/apollo_upgrade_and_machine_bootstrap`: `~/.cache/sase/tmp` as the 20 GB consumer, two disk-usage figures, and
  the suite-gate token formula.
- `202610/article_paper_audio_workflow`: the only tested Trafilatura → `sase-listen` run (Fowler article, 0 lint
  errors).
- `202609/bead_attachment_audience`: "no egress bills" as a reason to keep large files off public storage.
- `202609/bead_note_attachments`: treat bare `@name.ext` as a path only for known extensions (`@pytest.mark.asyncio`
  stays literal).
- `202610/commute_audio_from_markdown`: the −1.5 dBTP true-peak ceiling and 0.6 s / 1.2 s pause lengths, both
  explicitly adopted.
- `202610/jev_sase_integration_assessment`: unofficial Rust crates exist for Jev (count fact-checked by the lead).
- `202610/master_ci_red_why_and_how_to_stay_green`: KNOWN failures pass the landing gate only when on the reviewed
  quarantine list. Low confidence; this can be assembled from cld and grk.
- `202609/memory_and_instruction_file_history`: extend "also changed in this commit" sibling links to every memory
  note's band (credited in the disagreements table).
- `202609/model_catalog_and_size_alias_maintenance`: the rejected `sase dev model bump` option, and the
  manifest-typo/LSP-startup risk mitigation.
- `202609/pomodoro_ledger_and_daily_roadmap`: an audit of the `block-id-prompt` plugin's link rule, and "don't copy the
  same links into every block".
- `202609/prompt_next_word_prediction`: the module name `sase_core::prompt_prediction`.
- `202610/research_swarm_improvement_roadmap`: file beads and decision records from findings on request (an opt-in
  rank-10 item), and the heading check in the report checker.
- `202609/sase_core_p1_guardrails`: the "filler docs" argument for putting `//!` only at module roots.
- `202610/sase_listen_what_you_get`: per-engine episode costs, the `podcast:locked` feed tag, and the planned
  `_narration.md` inventory exclusion.
- `202609/sase_paper_followup_reading_list`: a pointer to Böckeler's *Context Engineering for Coding Agents*.
- `202609/sase_tool_guarded_recipes_and_monitor_wrapping`: the exact v1 monitor-wrap scope, which the lead framed as
  its own call.
- `202609/sase_tool_tui_integration`: a deferred FINAL-deck link from a verdict receipt to its run.
- `202610/toobig_split_beyond_python`: the Swift rule "stored properties stay in the primary declaration".
- `202609/tool_launch_directive`: a `%tool` raw-script error message pointing to `%proc`. Low confidence.
- `202609/usage_window_collector_hosting`: raise the agy/grok `--version` timeout from 2 s to 4 s, and note that reset
  countdowns are computed locally.
- `202610/agent_instructions_budgeted_router`: the unverified claim that Antigravity also loads `GEMINI.md`, kept only
  as a follow-up bead to verify.

## Swarms where nothing Gemini-only reached the final (25)

`202609/`:
- `agent_data_card_blocks`
- `agent_history_in_agents_tab`
- `agent_machine_tabs_and_cluster_semantics`
- `agents_sidebar_node_rail_and_zoom`
- `agents_tab_decks_and_cards`
- `agents_tab_finalizer_visibility`
- `artifact_hook_intent_matching`
- `goals_vs_structural_completion_notifications`
- `memory_bead_backlog_audit`
- `multi_agent_collaboration_strategy`
- `prompt_history_human_submissions_only`
- `prompt_recall_tabs_and_stash_trash`
- `provider_wait_contract_early_exits`
- `research_swarm_linker_agent`
- `routine_source_nav_sections`
- `sase_goals_design`
- `sase_goals_epic_roadmap`
- `sase_goals_memory_end_state`
- `sase_tool_e3_e4_landing_criteria`
- `sase_tool_e6_e8_go_no_go`

`202610/`:
- `deck_and_pager_three_pane_splits`
- `memory_history_tui_support`
- `muse_live_reply_streaming`
- `openai_harness_engineering_vs_sase`
- `tui_freeze_gc_heap_bloat`

In all 25, every Gemini idea in the final also appears in at least one peer report. Gemini's distinctive positions
were rejected or corrected.

Two borderline cases:
- In `muse_live_reply_streaming`, dismissing the console timer on the first delta is credited to gem alone, but mus had
  already sketched suspending the same timer.
- In `provider_wait_contract_early_exits`, the only Gemini-specific material is code-level precision on the classifier
  and an anecdote from its own run. mus states the substance of both.

## Excluded: Gemini reports with no final

These five `__gem.md` files sit loose at the month root. Their swarms were never consolidated, so nothing could have
been "included in the final". Git history shows what happened to each:
- Three were abandoned first attempts whose topics were re-run and consolidated within about 1–2 hours.
- One is a later follow-up swarm that was never consolidated.
- One is from a swarm committed today (2026-10-04) that has no consolidated report yet.

| Loose Gemini report | What happened |
| :--- | :--- |
| `202609/agents_tab_finalizers_decks_and_cards__gem.md` | Re-run and consolidated as `202609/agents_tab_finalizer_visibility/` |
| `202609/deck_card_spread_paged_view_ux__gem.md` | A later follow-up swarm to `202609/deck_card_paging_ux/` that was never consolidated |
| `202609/sase_services_improvements_and_extensions__gem.md` | Re-run and consolidated as `202609/sase_services_post_landing_hardening/` |
| `202610/improving_research_swarm_architecture__gem.md` | Re-run and consolidated as `202610/research_swarm_improvement_roadmap/` |
| `202610/sase_to_sasos_rename_evaluation__gem.md` | No consolidated report yet |

## Limitations

- **Independent rediscovery.** "Unique" means unique among the researcher reports. Where the lead verified something
  itself, the lead might have found it without Gemini. I flagged those cases with lower confidence: the stale pin, the
  `v` key, the `sar` data, and the `sase-listen` engine costs.
- **Judgment calls.** Substance matching and the substantive/minor line are judgments. The borderline items are
  labelled as such above.
- **What the denominator excludes.** It covers only swarms with a Gemini researcher. It does not measure whether
  Gemini's report helped indirectly, for example as a foil that sharpened the lead's reasoning. The finals sometimes
  use it that way.

## Final list: research files where Gemini-only insights reached the final report

### A. Substantive Gemini-only contributions (15)

1. **`202609/agent_long_command_early_exits/agent_long_command_early_exits.md`.** The whole agy (Antigravity)
   failure mechanism:
   - the 10 s blocking cap, the "end the turn" tool text, and the 5 s idle kill in print mode;
   - the second failure case, `research.24.gem`;
   - the `sase-15o` allowlist gap;
   - the live-demonstrated `manage_task` keep-alive escape;
   - the concrete classifier fix.

   Together these form the core of the final's agy repair plan.
2. **`202609/core_schema_skew_outage_recovery_ux/core_schema_skew_outage_recovery_ux.md`.** The second schema-skew
   channel: per-workspace `just _setup` fast-forwards and rebuilds the core. The final credits it to gem alone and
   makes it one of two root-cause channels, with a "respect the pin in both channels" fix.
3. **`202609/sase_master_ci_repair_and_pypi_0_18_release/sase_master_ci_repair_and_pypi_0_18_release.md`.** The stale
   `sase-core-revision.txt` pin: three goal bindings exist only in `33b0250`. This is the largest failure cluster (16
   tests plus the lint head-blocker), and its exact fix became the final's Wave 1.
4. **`202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md`.** The live-verified
   `sase scheduler restart` no-op ("cld and mus missed it"), the duplicate launch after a SIGKILL survivor (P1), and
   six smaller fixes.
5. **`202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`.** The 10–30 s first-use
   sidecar-clone cost in fresh workspaces. It became a bottom-line finding, RA7, a Phase 0 fix, and bead `sase-17r`.
   Also the write-behind vs single-turn argument (minor).
6. **`202609/unread_ack_reliability_and_tui_responsiveness/unread_ack_reliability_and_tui_responsiveness.md`.** The
   lag-induced `,u` double-press undo trap, which became R5 (explicit, time-bound undo). Also the guaranteed per-`,j`
   cache miss, which became remove-on-ack.
7. **`202609/agents_dynamic_tabs/agents_dynamic_tabs.md`.** The active-tab focus latch, which became R11 (credited
   "(gem)") and runs through the catalog rules, phase P3, and tests.
8. **`202609/sase_vs_hermes_agent/sase_vs_hermes_agent.md`.** Hermes approvals block a live process, while sase gates
   are durable and processless. "Correct, and cld under-weighted it", and the final rescored human approval as a sase
   advantage.
9. **`202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md`.** Bare `cargo check` fails because
   pyenv 3.11 doesn't meet abi3-py312, so `just fast` must wrap `check.sh` (a P0 item, credited to gem). Plus the
   800-line `view_file` limit (minor).
10. **`202609/sase_terminology_renames/sase_terminology_renames.md`.** Sunset the `task` alias on `sase proc`, because it
    collides with task beads. The final records "not raised" for both cld and mus and "Deprecate" for gem, answers
    "Agree", and adopts it as recommendation 6.
11. **`202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist.md`.** The name `baste`, ranked #2 and
    carried into the three-name finalist test. Plus ten graveyard namesakes no peer found (minor).
12. **`202609/tui_colon_command_line/tui_colon_command_line.md`.** The dual-pane "candidates + docs" card, which became
    the final's doc peek (P4, golden states). Plus ranking the linked bead first (minor).
13. **`202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`** (qualified). The synced per-goal hot
    partition, which became `goals/live/<id>.json` for fresh-machine active lists without replaying history. Heavily
    reworked by the lead.
14. **`202609/deck_card_paging_ux/deck_card_paging_ux.md`** (qualified). `v` is already `view_files`, which rules out
    mus's recommended key.
15. **`202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`** (qualified). The
    mount-time warmer burst and the ~27 ms dispatch-line import, adopted as Phase 1 "Mount hygiene" ("Only gem") but
    rated secondary.

### B. Minor-only Gemini-only contributions (24)

Each final's Gemini report sits beside it as `<topic>__gem.md`.

- `202609/agents_tab_node_finder/agents_tab_node_finder.md`: a secondary reason for rejecting a JumpAllModal extension.
- `202609/agy_usage_windows/agy_usage_windows.md`: the live `403 UNSUPPORTED_CLIENT` probe as evidence.
- `202610/apollo_agent_oom_wipeouts_root_cause/apollo_agent_oom_wipeouts_root_cause.md`: exit-143/SIGTERM confirmation
  from agent logs, and `sar` reclaim data.
- `202609/apollo_upgrade_and_machine_bootstrap/apollo_upgrade_and_machine_bootstrap.md`: `~/.cache/sase/tmp` as the
  20 GB consumer, disk figures, and the suite-gate token formula.
- `202610/article_paper_audio_workflow/article_paper_audio_workflow.md`: a tested Trafilatura → `sase-listen` run.
- `202609/bead_attachment_audience/bead_attachment_audience.md`: "no egress bills".
- `202609/bead_note_attachments/bead_note_attachments.md`: the known-extension rule for bare `@name.ext`.
- `202610/commute_audio_from_markdown/commute_audio_from_markdown.md`: a −1.5 dBTP ceiling and 0.6 s / 1.2 s pauses.
- `202610/jev_sase_integration_assessment/jev_sase_integration_assessment.md`: unofficial Jev Rust crates exist.
- `202610/master_ci_red_why_and_how_to_stay_green/master_ci_red_why_and_how_to_stay_green.md`: KNOWN only if
  quarantined (low confidence).
- `202609/memory_and_instruction_file_history/memory_and_instruction_file_history.md`: "also changed" links on every
  memory note.
- `202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance.md`: the rejected
  `sase dev model bump` option, and the LSP typo-risk mitigation.
- `202609/pomodoro_ledger_and_daily_roadmap/pomodoro_ledger_and_daily_roadmap.md`: the `block-id-prompt` link-rule
  audit, and no duplicated links.
- `202609/prompt_next_word_prediction/prompt_next_word_prediction.md`: the module name `sase_core::prompt_prediction`.
- `202610/research_swarm_improvement_roadmap/research_swarm_improvement_roadmap.md`: beads and decision records on
  request, and the heading check.
- `202609/sase_core_p1_guardrails/sase_core_p1_guardrails.md`: the "filler docs" rationale for module-root `//!`.
- `202610/sase_listen_what_you_get/sase_listen_what_you_get.md`: per-engine costs, `podcast:locked`, and the narration
  inventory exclusion.
- `202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md`: the Böckeler context-engineering
  pointer.
- `202609/sase_tool_guarded_recipes_and_monitor_wrapping/sase_tool_guarded_recipes_and_monitor_wrapping.md`: the exact
  v1 monitor-wrap scope.
- `202609/sase_tool_tui_integration/sase_tool_tui_integration.md`: the deferred receipt → run link.
- `202610/toobig_split_beyond_python/toobig_split_beyond_python.md`: the Swift stored-properties rule.
- `202609/tool_launch_directive/tool_launch_directive.md`: the `%tool` → `%proc` error message (low confidence).
- `202609/usage_window_collector_hosting/usage_window_collector_hosting.md`: the 2 s → 4 s version timeout, and local
  reset countdowns.
- `202610/agent_instructions_budgeted_router/agent_instructions_budgeted_router.md`: the `GEMINI.md` double-load claim,
  kept only as a verify-it follow-up.
