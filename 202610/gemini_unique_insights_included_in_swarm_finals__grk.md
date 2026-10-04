# Gemini unique insights that landed in research-swarm finals

**Researcher:** `grk` (independent swarm member)  
**Date:** 2026-10-04  
**Question:** Across research swarms in the research sidecar that produced a `__gem.md` report, did Gemini contribute unique insights the other swarm members did not, and did the lead actually include those insights in the consolidated final?

**Short answer:** Yes, in a minority of swarms. Gemini wrote 69 `__gem.md` reports. 65 of those swarms have a consolidated final. In **12 finals**, the lead adopted at least one finding that is both (a) attributed to Gemini / present only in the Gemini draft and (b) kept in the recommended design rather than mentioned in order to reject it. In most other swarms Gemini was a useful additional voter, a source of errors the lead corrected, or both.

This report does not consult peer reports from the current swarm (`research.3l.*`).

---

## Method

1. Opened the research sidecar with `sase repo open research`.
2. Inventoried every `*__gem.md` file and its sibling researcher drafts (`__cdx`, `__cld`, `__grk`, `__mus`) and finals (`<topic>.md` and/or `<topic>__final.md`).
3. Treated a **final** as the lead's consolidated report: the unsuffixed `<topic>.md` when it exists, otherwise `<topic>__final.md`. When both exist they are near-copies; citations below use the unsuffixed path.
4. Used `sase plan search` over `--kind research` for attribution language (`gem's`, `Only gem`, `gem is right`, `gem proposed`, contribution tables) and for distinctive phrases, to test whether a claim appears in any other swarm member's draft.
5. Used `sase artifact read` on the finals that survived that filter, and checked that the adopted text is in the recommendation / requirements / collision inventory, not only in a "rejected" column.

**Inclusion bar.** A hit requires all three:

- **Unique:** the insight is absent from the other researchers' drafts in that swarm (corpus search for the distinctive claim), or the lead explicitly marks it `Only gem` / `(gem)` against a disagreement table where peers took other positions.
- **Insight:** a concrete finding, mechanism, requirement, or design choice, not merely "Gemini participated."
- **Included:** the final keeps it in the recommended architecture, requirement list, reading list, or collision inventory. Credit followed by "reject," "wrong," "unsourced," or "do not copy" does not count.

**Out of scope.** Four `__gem.md` files have no consolidated final, including the in-flight file `202610/improving_research_swarm_architecture__gem.md` from this swarm (unread). Solo Gemini product mentions (`GEMINI.md`, Gemini TTS, Antigravity) are ignored unless they name researcher `gem`.

---

## Corpus

| Item | Count |
| --- | ---: |
| `__gem.md` reports | 69 |
| Swarms with a final | 65 |
| `__gem.md` with no final | 4 |
| Typical 5-way swarm (`cdx,cld,gem,grk,mus`) | 37 |
| Finals that mention `gem's` (any valence) | 42 topic stems |
| Finals that **adopted** a unique Gemini insight | **12** |

The four files without a final, so they cannot satisfy "included in the final," are:

- `202609/agents_tab_finalizers_decks_and_cards__gem.md` (loose file in `202609/`, not a topic directory)
- `202609/deck_card_spread_paged_view_ux__gem.md` (same)
- `202609/sase_services_improvements_and_extensions__gem.md` (same)
- `202610/improving_research_swarm_architecture__gem.md` (current swarm; unread)

---

## The 12 finals that kept a unique Gemini insight

Listed as the **final research file**, with the Gemini source beside it, and the unique contribution that survived synthesis.

### 1. `202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance.md`

- **Gemini source:** `model_catalog_and_size_alias_maintenance__gem.md`
- **Unique insight:** the **"test tax"**. Gemini's draft called out that historical catalog updates spend most of their diff in tests ("The Test Tax Trap"; Gemini said >70% tests). Peers split the cost differently (cld: docs 48%; mus: almost no tests pin pool strings). Corpus search for `test tax` hits only Gemini's draft and this final.
- **What the final kept:** the lead calls this "the key insight" and puts it first in the recommended fix order: *tests must derive expectations from data and assert rules, not slugs*. A manifest-only merge, without that, takes the Grok 4.7 commit from 19 files to 18. The recount is tests 42% / docs 37% / src 19% — Gemini's direction was right, the 70% figure was high.

### 2. `202609/deck_card_paging_ux/deck_card_paging_ux.md`

- **Gemini source:** `deck_card_paging_ux__gem.md`
- **Unique insight:** bind a single Agents-tab **`P`** to cycle the three layouts. The four drafts proposed four keys: grk `B`/`Shift+B`, cdx `(`/`)`, mus `v`, gem `P`.
- **What the final kept:** recommendation at a glance is "Bind **`P`** on the Agents tab to cycle the three layouts." The lead's key audit (printable, next to `p` pick-deck, unused as an Agents app action; `v` already `view_files`; `B`/`Shift+B` is one terminal key) is why Gemini's key won. Gemini's toast-on-every-change was dropped in favor of a persistent title badge.

### 3. `202609/tui_colon_command_line/tui_colon_command_line.md`

- **Gemini source:** `tui_colon_command_line__gem.md`
- **Unique insights** (lead's "main contribution" row for Gemini, and later design text):
  1. A **dual-pane "candidates + docs" card**.
  2. A **re-attach / `:last` flow**.
  3. A **shell-vs-TUI completion capability table** used as evidence that zsh cannot match TUI completion.
- **What the final kept:** on wide terminals the completion popup grows a right-hand **doc peek**, explicitly "gem's dual-pane card." Reopening the panel restores the transcript and covers `:last` / re-attach, even though the literal `:last` / `:palette` built-ins lost to cld's command set. The capability table is cited in the "why this beats a shell" argument. Geometry (centered modal) and in-process quick queries were rejected.

### 4. `202609/sase_core_p1_guardrails/sase_core_p1_guardrails.md`

- **Gemini source:** `sase_core_p1_guardrails__gem.md`
- **Unique insight:** limit the `//!` crate-doc rule to **module roots**, so agents are not pushed into filler such as `//! Implementation of scanner`. Phrase search for that filler example hits only Gemini's draft and this final. The lead's contribution table credits Gemini with exactly this limit.
- **What the final kept:** §2.5 "Why not every file. gem is right…" The adopted P1 docs rule is: gate `//!` on the 114 top-level module roots (already green), and drop `docs/MODULES.md`. Other Gemini P1 ideas (checked-in binding inventory, schema-version table, `*_parity.rs` rename as a gate) were not kept.

### 5. `202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md`

- **Gemini source:** `sase_services_post_landing_hardening__gem.md`
- **Unique insight:** a configurable environment passthrough, `service.capture_env_names`, plus proxies, CA bundles, and locale. Search for `capture_env_names` hits only Gemini's draft and this final.
- **What the final kept:** the live bug that `SASE_TMPDIR` and other `SASE_*` path overrides never reach the host (67 GiB unreaped on apollo) is fixed in the **general form Gemini specified**. The lead notes it needs a schema change because `service:` currently accepts only `procs`.

### 6. `202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`

- **Gemini source:** `bead_speedup_daemon_vs_direct_path__gem.md`
- **Unique insight:** the **"optional dilemma"** — if a beads daemon is optional, the direct path is the fallback forever, so it has to be fast anyway. That phrase lives in Gemini's draft and this final.
- **What the final kept:** the architecture is "fix the direct path first; treat any daemon as a later, optional, non-serving accelerator," with the dilemma cited as the reason the fallback must stay first-class. Gemini's `--async` for humans is called out as a separate durability decision, not v1.

### 7. `202609/agents_dynamic_tabs/agents_dynamic_tabs.md`

- **Gemini source:** `agents_dynamic_tabs__gem.md`
- **Unique insight:** an emptied active tab must not vanish under the cursor. The lead writes requirement **R11** as "An emptied active tab stays put… The place you are standing does not vanish under the cursor (gem)." That standing-cursor sentence appears only in this final as a Gemini attribution; peers lost on casing, `--tab` CLI, glyphs, and strip placement.
- **What the final kept:** R11 is in the adopted requirement set. If the last agent on the active tab is dismissed or moved, the tab stays selected with an empty state until the user navigates away.

### 8. `202609/sase_tool_tui_integration/sase_tool_tui_integration.md`

- **Gemini source:** `sase_tool_tui_integration__gem.md`
- **Unique insights the lead listed as kept from Gemini:** a **quick-run command-palette entry**, **stage bars** on the run card, and the split between a global Tools surface and a contextual agent card. Gemini's FINAL-deck Verification card, CALLS rename, persistent per-row verdict chips, and a fourth top-level tab were rejected.
- **What the final kept:** recommended Tools card includes a **stage waterfall**; §5.6 discoverability includes palette actions "Run project tool…" / "Open Tools pane" / stop-this-node's-live-run. The Admin Center Tools pane itself was also proposed by cld and grk, so only the palette entry and stage visualization are counted as Gemini-unique keepers.

### 9. `202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md`

- **Gemini source:** `sase_paper_followup_reading_list__gem.md`
- **Unique insight:** Birgitta Böckeler, *Harness engineering for coding agent users* (martinfowler.com, 2026-04-02), as the companion to OpenAI's harness-engineering post. The reconciliation table marks pick #1 as "cdx, cld" on the main list and **"gem (Böckeler)"** as the only companion. Search for `Böckeler` in this swarm hits Gemini's draft and the final / `__final` copy.
- **What the final kept:** the published #1 section has a **Companion** subsection for Böckeler, including the guides/sensors × computational/inferential taxonomy. Four other Gemini citations in that swarm were thrown out as invented authors or details; those do not count.

### 10. `202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md`

- **Gemini source:** `prompt_space_and_project_cycle_latency__gem.md`
- **Unique insight:** the disagreement table marks **Only gem** for a mount-time **worker storm** (8–9 thread workers) and a ~27 ms first-mount import in `_refresh_dispatch_context_line`. Search for `worker storm` hits Gemini's draft and this final pair. Gemini's ~350 ms projection for 50 MRU entries was too pessimistic and was not kept.
- **What the final kept:** recommended solution item **7, Mount hygiene** — stagger non-essential prompt warmers by one paint, and hoist those imports. The lead calls it secondary hygiene, and it is still in the epic's punch list.

### 11. `202610/commute_audio_from_markdown/commute_audio_from_markdown.md`

- **Gemini source:** `commute_audio_from_markdown__gem.md`
- **Unique insight:** get ffmpeg onto apollo without root via `uv run --with static-ffmpeg`. Search for `static-ffmpeg` hits Gemini's draft and the final pair. Gemini's `edge-tts` default and tailnet-only feed were rejected.
- **What the final kept:** the publish pipeline says apollo has no ffmpeg; install through a reviewed sudo gate **or** pull a static build with `static-ffmpeg` under `uv` ("gem's no-root route").

### 12. `202610/should_sase_become_sasos/should_sase_become_sasos__final.md`

- **Gemini source:** `should_sase_become_sasos__gem.md`
- **Unique insight:** **Nokia 7210 SAS OS** (Service Access Switch firmware) as a spoken collision with `sasos`. Search for `Nokia` / `7210 SAS` in this swarm hits Gemini's draft and this final. Several other Gemini collision claims were weakened or dropped (left-hand triple-strike, SAS v. World Programming as trademark, "FREE" domains, numeric scorecards).
- **What the final kept:** the collision inventory includes Nokia 7210 SAS OS, sourced as `gem`, with lead confirmation in Nokia release-note titles. It supports bottom-line point 2: `sasos` still reads as "SASE OS" / "SAS OS" and points back at networking.

---

## Pattern

When Gemini's unique work survived, it was usually one of:

- a **cost or constraint the others mis-counted** (test tax; optional-daemon dilemma; `//!` filler; mount-time worker storm);
- a **small, checkable design token** (`P` key; dual-pane doc peek; `static-ffmpeg`; `capture_env_names`; R11 empty-tab stay);
- a **sourced external fact** (Böckeler; Nokia 7210 SAS OS).

Gemini's unique *architecture* proposals in the same swarms were usually rejected: Catalog agent tab, 4-cell micro-rail, FINAL Verification card, CALLS rename, runtime file leases, handoff capsules, `%model auto` routing, GC threshold tweaks, first-seen tab casing, `:q`/`:w` built-ins.

---

## Near misses (credited, not included)

These finals name Gemini specifically and then reject, correct, or share the claim. They are **not** in the list above.

| Final | Gemini-unique material | Why it is not a hit |
| --- | --- | --- |
| `core_schema_skew_outage_recovery_ux.md` | Cross-clan argument and pre-flight gate "stand" | The shipped update probe (option A) is credited to cld/grk/cdx; Gemini's bulk `R`/`F` path is rejected |
| `agent_history_in_agents_tab.md` | Lightweight rows and harvester "hold up" | Catalog tab, `Tab` switch, and `agent_artifacts.db` path rejected; the lightweight list in the rec is credited to mus/grk |
| `agy_usage_windows.md` | `account`-scoped Gemini buckets render with no core change | Lead agrees the header looks clean, then chooses cld's honest `model_family` scoping |
| `tui_freeze_gc_heap_bloat.md` | Raise GC thresholds 0 and 1 | Measured: barely changes gen-2 cadence |
| `memory_history_tui_support.md` | Tombstone / agent-bridge framing; pane key proposals | `.` / `Tab` / split keys rejected; full pager port rejected |
| `prompt_next_word_prediction.md` | Static idiom prior, Kneser-Ney | "None in v1"; prior unmeasured |
| `multi_agent_collaboration_strategy.md` | Schema sketch, V1–V6 matrix, leases, capsules | Leases, capsules, auto-ack, newest-first truncation rejected |
| `sase_listen_what_you_get.md` | Kokoro as built-in; Telegram chapters; auto-publish | All three corrected |
| `sase_master_ci_repair_and_pypi_0_18_release.md` | Hand-ratchet master's pyproject window | Contradicts who-owns-the-window rules |
| `sase_rename_new_name_shortlist.md` | "Completely clean" name claims | Lead overturned most of them |
| `jev_sase_integration_assessment.md` | `%model auto` ~35% savings | Unsourced; deferred |
| `toobig_split_beyond_python.md` | 1500-line trigger; py≈rs/swift ratio | Confuses `#split_epic` output ceiling with a trigger; ratio unsourced |
| `research_swarm_improvement_roadmap.md` | Drop linker wait on the image agent | Contradicts a recorded Highlights-on-ADD decision |

Four finals with a Gemini draft **never name researcher `gem` in the body** (`openai_harness_engineering_vs_sase.md`, `pomodoro_ledger_and_daily_roadmap.md`, `tool_launch_directive.md`, `unread_ack_reliability_and_tui_responsiveness.md`). Without attribution or a distinctive Gemini-only phrase in the rec, they are not counted.

---

## Limits

- Inclusion is judged from the **lead's text**, not from later plans or landed code. A local plan that copied prompt-space item 7 is extra corroboration, not the criterion.
- Uniqueness is **phrase- and table-level** across the research corpus, not a full semantic diff of every paragraph in 65×4 drafts. A peer who said the same thing in very different words could be missed. The `Only gem` / `(gem)` / contribution-table cases are the most robust.
- `__final.md` copies are treated as the same swarm as `<topic>.md`.
- This file was written without reading `202610/improving_research_swarm_architecture__gem.md`, `202610/research_swarm_architecture_and_quality__cdx.md`, or any other current-swarm peer report.

---

## End list: research files and Gemini's unique kept contributions

| Final report | Gemini draft | Unique contribution the final kept |
| --- | --- | --- |
| `202609/model_catalog_and_size_alias_maintenance/model_catalog_and_size_alias_maintenance.md` | `…/model_catalog_and_size_alias_maintenance__gem.md` | Test tax: fix value-pinned tests first; a manifest alone almost does not help |
| `202609/deck_card_paging_ux/deck_card_paging_ux.md` | `…/deck_card_paging_ux__gem.md` | Agents-tab `P` cycles the three deck/card layouts |
| `202609/tui_colon_command_line/tui_colon_command_line.md` | `…/tui_colon_command_line__gem.md` | Dual-pane doc peek; re-attach via restored transcript; shell-vs-TUI capability table |
| `202609/sase_core_p1_guardrails/sase_core_p1_guardrails.md` | `…/sase_core_p1_guardrails__gem.md` | `//!` only on module roots, to avoid filler file docs |
| `202609/sase_services_post_landing_hardening/sase_services_post_landing_hardening.md` | `…/sase_services_post_landing_hardening__gem.md` | `service.capture_env_names` (and related) passthrough as the general env-currency fix |
| `202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md` | `…/bead_speedup_daemon_vs_direct_path__gem.md` | Optional-daemon dilemma: the direct path must stay fast |
| `202609/agents_dynamic_tabs/agents_dynamic_tabs.md` | `…/agents_dynamic_tabs__gem.md` | R11: emptied active tab stays put under the cursor |
| `202609/sase_tool_tui_integration/sase_tool_tui_integration.md` | `…/sase_tool_tui_integration__gem.md` | Palette "Run project tool…" entry; stage waterfall on the Runs card |
| `202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md` | `…/sase_paper_followup_reading_list__gem.md` | Böckeler *Harness engineering…* as companion to pick #1 |
| `202610/prompt_space_and_project_cycle_latency/prompt_space_and_project_cycle_latency.md` | `…/prompt_space_and_project_cycle_latency__gem.md` | Mount-time worker storm / hoist `_refresh_dispatch_context_line` imports (rec item 7) |
| `202610/commute_audio_from_markdown/commute_audio_from_markdown.md` | `…/commute_audio_from_markdown__gem.md` | `static-ffmpeg` no-root ffmpeg on apollo |
| `202610/should_sase_become_sasos/should_sase_become_sasos__final.md` | `…/should_sase_become_sasos__gem.md` | Nokia 7210 SAS OS as a spoken `sasos` collision |

**Recommendation for readers of this audit:** treat Gemini as a high-variance swarm member. The expected unique keep is **zero or one sharp, checkable item per swarm**, not a parallel architecture. Leads already extract that item when it is real; the rest of Gemini's unique volume in this corpus is correction fodder.
